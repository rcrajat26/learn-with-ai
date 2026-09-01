# 03 Java Core — The archived cache — BASICS (§1.9, 1.9.5)

**Target version: Java 21 LTS.** | **Part 1 of 5** | [Index](../00-index.md)
Previous: [The wrapper caches](01a-the-wrapper-caches.md) · Next: [Cache coverage and reference equality](01b-cache-coverage-and-reference-equality.md)

[`01a-the-wrapper-caches.md`](01a-the-wrapper-caches.md) left one question open. It quoted
`IntegerCache`'s static initialiser building 256 `Integer` objects in a loop, and said the loop is
"the only place these objects are made *when they are made in Java at all*". On a default JDK 21
JVM they usually are not made in Java at all. They arrive pre-built, memory-mapped out of the CDS
archive, and the loop never runs.

This is the single most version-stale corner of a very well-trodden interview topic. Every blog post
written against JDK 8 says the cache is built in a static block at startup, and on JDK 21 that
answer is true about the *code* and wrong about the *behaviour*. This file owns that gap.

What it does not own: the coverage table of which wrapper caches what is
[`01b-cache-coverage-and-reference-equality.md`](01b-cache-coverage-and-reference-equality.md), and
the three-path flowchart `D-102` plus the line-by-line walk of the whole initialiser belong to
[`03-internals-boxing.md`](03-internals-boxing.md).

---

## 1. The cache can be mapped from the CDS archive instead of built (1.9.5)

`[SOURCE]` `[RESEARCH]` The 256 `Integer` objects covering −128..127 are identical on every JVM
start, on every machine, forever. Nothing about them depends on your program, your classpath, your
arguments or the time of day. Building them at every startup is pure repeated work — so modern
HotSpot builds them once, at JDK build time, and ships the finished object graph inside the **CDS
archive**: a memory-mappable file of pre-parsed class metadata and pre-constructed heap objects. At
startup the VM maps that region in, fixes up the pointers for this process, and hands
`IntegerCache` a fully-populated array. The static initialiser still runs. It just finds the array
already there and skips constructing one.

### Why it exists

Startup, and only startup. Allocating 256 small objects is trivial in isolation, and nobody archived
`IntegerCache` because that one loop was slow. It is one of a *set*. Measured on JDK 21.0.7,
`java -Xlog:cds+heap=info -version` resolves **15** archived heap subgraphs on a plain startup, five
of which are wrapper caches:

| Archived subgraph | What it holds |
|---|---|
| `java.lang.Integer$IntegerCache` | the 256 boxed `int` values |
| `java.lang.Long$LongCache` | the 256 boxed `long` values |
| `java.lang.Byte$ByteCache` | all 256 boxed `byte` values |
| `java.lang.Short$ShortCache` | the 256 boxed `short` values |
| `java.lang.Character$CharacterCache` | the 128 boxed `char` values, `0..127` |
| `java.util.ImmutableCollections` | the empty-collection singletons |
| `jdk.internal.module.ArchivedModuleGraph` | the resolved boot module graph |

plus `java.util.jar.Attributes$Name`, `sun.util.locale.BaseLocale`, `java.lang.ModuleLayer`,
`java.lang.module.Configuration`, `jdk.internal.math.FDBigInteger`,
`jdk.internal.loader.ArchivedClassLoaders`, `jdk.internal.module.ArchivedBootLayer` and
`java.lang.Module$ArchivedData`. The wrapper caches are the small, boring members of a list whose
aggregate — a resolved module graph, a set of class loaders — is genuinely worth milliseconds.

**An archived subgraph is a different kind of thing from a lazily-built one**, in three ways worth
holding separately:

1. **Identity is established before your code runs.** With the construction loop, the identity of
   `Integer.valueOf(42)` is decided the first time something calls it. With the archive, those 256
   objects already exist, at addresses fixed up during VM bring-up, before `main` is entered. Nothing
   your program does can be "early enough" to be before them.
2. **The objects live in a mapped region, not in Eden.** The construction loop allocates 256 objects
   in the young generation like any other allocation, and they get promoted out on the first
   collection. The archived objects are materialised into the archive's own mapped heap region. They
   do not pressure the nursery at the exact moment the JVM is trying to start quickly, and the
   underlying pages can be shared across JVMs on the same host — which matters when you run many
   short-lived processes rather than one long-lived server.
3. **The mapping is per-JVM-start, not per-application.** The archive is produced once when the JDK
   is built (or by an explicit dump run) and consumed by every JVM launched from that JDK. The cost
   of building it is not paid by your process at all.

**Insight:** point 1 is the one with teeth. Every other lazy-holder cache in the JDK can, in
principle, be influenced by code that runs before its first use. `IntegerCache` cannot, because the
JDK boxes an `int` inside its own startup path — measured, its subgraph is materialised at `0.015s`
with the `(early)` marker, before `main`. So "configure it before first use" is not a strategy that
exists for this class, which is why every knob for it is a command-line flag.

**When it applies:** by default. `-Xshare:auto` is the default mode and the default CDS archive
ships with the JDK, so on an out-of-the-box `java` command it applies. **When it does not:** under
`-Xshare:off`, and — the non-obvious case — when you have widened the cache with
`-XX:AutoBoxCacheMax`, because the archived array is then the wrong size. Both are measured below.

### The mechanism

The CDS half of the `IntegerCache` static initialiser, quoted from JDK 21.0.7. The `high`-computing
half that precedes it is quoted and read in
[`01a-the-wrapper-caches.md`](01a-the-wrapper-caches.md); this excerpt picks up immediately after
`high = h;`.

```java
        // Load IntegerCache.archivedCache from archive, if possible
        CDS.initializeFromArchive(IntegerCache.class);
        int size = (high - low) + 1;

        // Use the archived cache if it exists and is large enough
        if (archivedCache == null || size > archivedCache.length) {
            Integer[] c = new Integer[size];
            int j = low;
            for(int i = 0; i < c.length; i++) {
                c[i] = new Integer(j++);
            }
            archivedCache = c;
        }
        cache = archivedCache;
```

- `CDS.initializeFromArchive(IntegerCache.class)` — `jdk.internal.misc.CDS`, a native method. It asks
  the VM whether it holds an archived heap subgraph registered for this class; if so, the VM
  materialises the subgraph and **writes the class's archived fields directly**, from outside Java
  code. This call is on the **trunk**: it happens unconditionally, on every path, in every
  configuration, including `-Xshare:off` and including a widened cache. It is *not* one of three
  alternative branches, which is the detail most write-ups get wrong. The archive is always
  consulted; the `if` that follows decides only whether to *keep* what the consultation produced.
- `int size = (high - low) + 1` — the size the cache is *supposed* to be, given whatever `high` the
  previous half computed. At the defaults, 256.
- `archivedCache == null` — the "no archive" case. `initializeFromArchive` left the field alone,
  because the VM had nothing registered (or CDS is off entirely), so the field holds its default
  `null`.
- `size > archivedCache.length` — the "archive too small" case. Note the direction of the comparison:
  an archived array *larger* than needed would still be accepted, but a smaller one is rejected.
  Together with the `null` check this reads: construct only if the archive gave us nothing usable.
- The loop body is the same construction code as ever, and it assigns its result *into*
  `archivedCache` — so after the `if`, that field always holds a usable array regardless of which
  path ran.
- `cache = archivedCache` — the single assignment to the `@Stable static final` field. From
  `Integer.valueOf`'s point of view the two paths are completely indistinguishable: it reads
  `cache[i + 128]` and neither knows nor cares who allocated the element.

**`archivedCache` is the only non-`final` field in the class, and the asymmetry with `cache` is the
whole story of who writes what.** `low`, `high` and `cache` are all `static final`, assigned in Java,
exactly once, inside `<clinit>` — which is precisely the shape the compiler and the JIT are entitled
to reason about: `low` folds to a compile-time constant, and `cache` carries `@Stable` so C2 may
treat its elements as constants after initialisation. `archivedCache` cannot join them, because the
JVM assigns it natively, bypassing Java assignment entirely. A `final` field mutated from outside
Java is a lie to every optimisation built on `final`. So the JDK splits the roles: the field the VM
touches is deliberately non-`final` and package-private-by-default within the nest, and the field the
compiler is allowed to trust is a separate `final` one assigned from it in ordinary Java at the end of
the block. Reading `archivedCache` in the source tells you "the VM may have written this"; reading
`cache` tells you "this is settled". The `final` and `@Stable` semantics being leaned on are
[`../classes-and-initialization/04-internals-final-and-constant-folding.md`](../classes-and-initialization/04-internals-final-and-constant-folding.md).

Measured, `java -Xlog:cds+heap=info` on JDK 21.0.7 with the default `-Xshare:auto`:

```
[0.008s][info][cds,heap] Patching native pointers in heap region
[0.009s][info][cds,heap] resolve subgraph java.lang.Integer$IntegerCache
[0.009s][info][cds,heap] resolve subgraph java.lang.Long$LongCache
[0.009s][info][cds,heap] resolve subgraph java.lang.Byte$ByteCache
[0.009s][info][cds,heap] resolve subgraph java.lang.Short$ShortCache
[0.009s][info][cds,heap] resolve subgraph java.lang.Character$CharacterCache
[0.015s][info][cds,heap] init subgraph java.lang.Integer$IntegerCache
[0.015s][info][cds,heap] initialize_from_archived_subgraph java.lang.Integer$IntegerCache 0x000000c800036b28 (early)
[0.022s][info][cds,heap] init subgraph java.lang.Long$LongCache
[0.022s][info][cds,heap] initialize_from_archived_subgraph java.lang.Long$LongCache 0x000000c800039a30
```

Line by line:

- `Patching native pointers in heap region` — the mapped archive heap region being fixed up for this
  process's addresses. The archive was written at JDK build time and cannot know where this process
  will map it, so pointers inside the region are relocated first. This happens once, for the whole
  region, before any subgraph is used.
- `resolve subgraph java.lang.Integer$IntegerCache` and its four siblings — the VM registering that
  it holds an archived subgraph rooted at each of those classes. All five land within a millisecond
  of each other, at `0.009s`, and none of them is *used* yet. Resolution is bookkeeping.
- `init subgraph java.lang.Integer$IntegerCache` at `0.015s` — six milliseconds later, and this is
  the first line caused by anything actually running: `IntegerCache`'s `<clinit>` has been entered
  and has reached `CDS.initializeFromArchive`.
- `initialize_from_archived_subgraph java.lang.Integer$IntegerCache 0x000000c800036b28 (early)` — the
  materialisation, with the address of the subgraph root. This is the native call writing
  `archivedCache`. When control returns to Java, the field is non-`null` and 256 long, the `if` is
  false, and the loop does not run.
- The `Long$LongCache` pair at `0.022s`, seven milliseconds after `Integer`'s, shows the same
  sequence happening independently and later — each subgraph is materialised on its own class's first
  initialisation, not all at once.
- The `(early)` marker appears on the `Integer$IntegerCache` line and **not** on `Long$LongCache`.
  **Unverified:** the reading that fits the observation is that it distinguishes subgraphs
  materialised during early VM bring-up, before the JVM is fully up, from those materialised on
  ordinary first use — `Integer` boxing happens inside the JDK's own startup path, `Long` boxing does
  not. That is consistent across runs but was not confirmed against HotSpot source; see
  `## Open questions`.

Two controls, both measured on JDK 21.0.7:

| Run | `cds,heap` lines mentioning `IntegerCache` | Array origin | `valueOf(127)` / `(128)` shared |
|---|---|---|---|
| default (`-Xshare:auto`) | 3 — `resolve subgraph`, `init subgraph`, `initialize_from_archived_subgraph` with the `(early)` marker | **mapped from the archive** | true / false |
| `-Xshare:on` | 3 — the same three lines | mapped from the archive | true / false |
| `-Xshare:off` | **0 — no `cds,heap` lines at all** | constructed by the loop | true / false |
| `-XX:AutoBoxCacheMax=1000` | 3 — `initialize_from_archived_subgraph` **still fires** | archive consulted, then **rebuilt** | true / **true** |

The fourth column is the important one for keeping the two axes separate: the array's *origin* moves
across all four rows and the *semantics* move only in the last row, and they move for a completely
different reason — the range, not the archive.

**Insight:** read the fourth row again. Raising `AutoBoxCacheMax` does not skip the archive. The
subgraph is still resolved, still materialised, still relocated — at full cost — and then
`size > archivedCache.length` throws the result away. `[NUM]` With `high = 1000`,
`size = (1000 − (−128)) + 1 = 1000 + 128 + 1 = 1129`, and the archived array's length is **256**;
`1129 > 256` is true, so the branch allocates a 1129-element array and runs 1129 constructors.
**Raising the flag silently costs you the archived cache, and you pay for it twice**: you map 256
objects that become immediately-dead archived garbage, and you construct 1129 replacements. A flag
reached for to *reduce* allocation adds startup allocation before it removes any, and pins 1129
objects for the JVM's lifetime instead of 256.

`Long`, `Byte`, `Short` and `Character` have archived subgraphs of their own, visible in the log
above; `Boolean` has none, because it has no cache class at all — only two eagerly-constructed
`public static final` fields. Measured: zero `cds,heap` lines match `Boolean` on a default startup.
The full coverage table, wrapper by wrapper, is
[`01b-cache-coverage-and-reference-equality.md`](01b-cache-coverage-and-reference-equality.md).

**Version framing.** This is a **Java 21** observation, and it is the shape of the interview answer.
`CDS.initializeFromArchive` and the `archivedCache` field are not in JDK 8's `IntegerCache`; there
the static block is unconditionally the loop, which is what the material most candidates studied
describes. So "the cache is built in a static block when `IntegerCache` initialises" is
**true but incomplete** on 21: the static block does run, and on a default JVM it builds nothing. The
strong answer states the JDK 8 shape, then the 21 addition, then notes that neither changes which
values are shared.

### Diagram

No diagram of its own. The three-path decision — archive usable, archive too small, no archive — is
**D-102**, and it belongs to [`03-internals-boxing.md`](03-internals-boxing.md) alongside the
line-by-line walk of the complete initialiser.

### A concrete example

`InternalPlatforms` boxes status phase numbers as it builds its status-code lookup. By the time that
code runs, `IntegerCache` is long since initialised — there is no API to call and nothing to observe
from inside the process. The evidence is the log.

```java
public final class ArchivedCacheProbe {

    // Boxing any small int forces IntegerCache's <clinit>, and with it either the
    // archive mapping or the 256-iteration construction loop.
    static Integer phaseOf(String statusCode) {
        return Integer.valueOf(statusCode.charAt(3) - '0');   // "AA-801" -> 8
    }

    public static void main(String[] args) {
        System.out.println(phaseOf("AA-801"));                       // 8
        System.out.println(phaseOf("AO-400"));                       // 4
        System.out.println(phaseOf("AA-801") == phaseOf("AO-400"));  // false: 8 and 4
        System.out.println(phaseOf("AA-801") == phaseOf("AA-800"));  // true: both 8, both cached
    }
}
```

Run it two ways:

```
java -Xlog:cds+heap=info ArchivedCacheProbe          # 3 IntegerCache lines; array mapped
java -Xshare:off -Xlog:cds+heap=info ArchivedCacheProbe   # 0 cds,heap lines; array constructed
```

Measured: the four printed results are byte-for-byte identical in both runs. That is the entire
point — the mechanism is invisible to program semantics and visible only in startup work.

### The gotcha

The archive is a *startup* optimisation with **no** semantic content whatsoever. `-Xshare:off` does
not change which values are shared, does not change `==`, does not change the range, does not change
`identityHashCode` stability within a run. Measured on JDK 21.0.7, `-Xshare:off` gives exactly the
default answers: 127 shared true, 128 shared false, 1000 shared false. Anyone reasoning "the cache
comes from CDS, so maybe `==` behaves differently under `-Xshare:off`" has the model inverted: the
two paths produce arrays that are element-for-element equivalent, and the only difference is who
allocated the elements and when. The flag that *does* change semantics is `-XX:AutoBoxCacheMax`, and
it changes them by moving `high`, not by touching the archive.

> **Definition.** In Java 21, `IntegerCache`'s static initialiser calls `CDS.initializeFromArchive`
> unconditionally, letting the VM populate the non-`final` `archivedCache` field from a memory-mapped
> archived heap subgraph; the 256-object construction loop runs only when that field is `null` or the
> archived array is shorter than the requested `size`, and which path ran is unobservable from
> program semantics.

**Interview:** *"Could CDS explain a wrapper `==` result you did not expect?"* No. CDS decides who
allocated the cached objects and when, not which values are cached — that is `low` and `high`.
Measured on JDK 21.0.7, `-Xshare:off` gives the default answers unchanged: 127 shared, 128 not, 1000
not. The flag that can explain a surprising result is `-XX:AutoBoxCacheMax` (or the equivalent `-D`
property), because it raises `high`; and the real answer is that `==` on wrappers is a reference
comparison and should not be there at all.

---

## 2. Three facts that hang off the archived cache

**`-Xshare` has three modes, and only one of them is a behaviour change you can observe.**
`-Xshare:auto` is the default: use the archive if it can be mapped, fall back silently if it cannot.
`-Xshare:on` requires it — measured on JDK 21.0.7, it produced the same three `IntegerCache` log
lines as the default. `-Xshare:off` disables CDS entirely, and measured, prints no `cds,heap` lines
at all. The gotcha is that `auto` failing back is *silent*, so an environment where the archive
cannot be mapped looks identical to one where it can, except in the log.

> **Definition.** `-Xshare:auto` (default) uses the CDS archive opportunistically, `-Xshare:on`
> requires it, `-Xshare:off` disables it; none of the three changes which wrapper values are shared.

**The archived objects are ordinary objects once mapped.** They are reachable, they answer
`identityHashCode`, they can be synchronised on (which is why `synchronized (STAKE_LOCK)` on a boxed
`Integer` is a real `monitorenter` on a process-wide shared object, and a genuine concurrency bug —
see the value-based-class discussion in
[`../objects-equality-and-lifecycle/01-basics.md`](../objects-equality-and-lifecycle/01-basics.md)).
The gotcha: "it came from a read-only archive region" does not make a cached `Integer` safe to lock
on, and does not make it immune to being used as a monitor by someone else's library.

> **Definition.** A materialised archived object is an ordinary heap object with an ordinary identity;
> the archive changes its provenance, not its semantics.

**`Boolean` is the wrapper with no archived subgraph, because it has no cache class.** `Integer`,
`Long`, `Byte`, `Short` and `Character` each have a private static nested cache class with an
`archivedCache` field, and each appears in the `resolve subgraph` list. `Boolean` has two eagerly
constructed `public static final` fields instead, and `Float` and `Double` have no cache of any kind.
Measured: zero `cds,heap` lines match `Boolean` on a default startup. The gotcha is assuming the
five-line log list is exhaustive of wrapper caching — it is exhaustive of wrapper *archiving*, which
is not the same claim. The coverage table is
[`01b-cache-coverage-and-reference-equality.md`](01b-cache-coverage-and-reference-equality.md).

> **Definition.** Exactly five wrappers have archived cache subgraphs — `Integer`, `Long`, `Byte`,
> `Short`, `Character` — and `Boolean`, `Float` and `Double` have none.

**Interview:** *"In Java 21, where does `IntegerCache.cache` come from?"* On a default JVM, from the
CDS archive: the static initialiser calls `CDS.initializeFromArchive(IntegerCache.class)`
unconditionally, the VM materialises an archived heap subgraph and natively writes the non-`final`
`archivedCache` field, and the 256-iteration construction loop is skipped because the field is
non-`null` and long enough. Under `-Xshare:off`, or with `-XX:AutoBoxCacheMax` raised so the archived
256 entries are too few, the loop runs instead. Either way the shared values and the `==` behaviour
are identical — the archive is a startup optimisation, not a semantic one.

---

## Pitfalls

### Assuming `IntegerCache` initialises when your class loads, so `-Xshare` or the range can be set later

**Wrong**

```java
// "We set the property from code before anything boxes, so the range widens."
public final class LedgerBootstrap {
    static {
        System.setProperty("java.lang.Integer.IntegerCache.high", "1000");
    }
    public static void main(String[] args) {
        System.out.println(Integer.valueOf(1000) == Integer.valueOf(1000));  // expected true
    }
}
```

This cannot work, for two independent reasons, both measured.

`IntegerCache` reads a **saved** property through `jdk.internal.misc.VM.getSavedProperty`, captured
during VM initialisation and then removed from the public table — `System.setProperty` writes to a
different table entirely. The evidence that the two tables are genuinely separate: measured on
JDK 21.0.7, `System.getProperty("java.lang.Integer.IntegerCache.high")` returns `null` even when the
property **was** supplied on the command line as `-Djava.lang.Integer.IntegerCache.high=1000`, and
that run's cache *was* widened. So the property the library reads is not the property your code can
see or write.

And `IntegerCache` has already initialised long before `main`. Measured with
`-Xlog:cds+heap=info`, its `initialize_from_archived_subgraph` line carries the `(early)` marker and
fires during VM bring-up, at `0.015s`, before the application's own static initialisers run.

**Right**

```
# The range and the archive are both launch-time decisions, full stop.
java -XX:AutoBoxCacheMax=1000 -jar funds-ledger.jar
# equivalently, and measured identical:
java -Djava.lang.Integer.IntegerCache.high=1000 -jar funds-ledger.jar
# and CDS likewise:
java -Xshare:off -jar funds-ledger.jar
```

Both range forms are measured to make `Integer.valueOf(1000) == Integer.valueOf(1000)` true. No
in-process call can change either fact retroactively, because both were consumed before your first
line of code ran.

**Why people believe it:** the holder-class idiom really is lazy, so "initialises on first use" is
correct in general, and the inference "therefore after my code starts" feels sound. It fails here
because `Integer` boxing is one of the very first things the JDK itself does — the class whose lazy
initialisation you are reasoning about was triggered by the JVM, not by you.

### Raising `-XX:AutoBoxCacheMax` and silently losing the archive

**Wrong**

```
# "The archive gives us fast startup, and a bigger cache gives us fewer allocations.
#  Both are optimisations, so both together must be better."
java -XX:AutoBoxCacheMax=1000 -Xlog:cds+heap=info -jar funds-ledger.jar
```

Measured on JDK 21.0.7, that run still prints all three `IntegerCache` lines, including
`initialize_from_archived_subgraph`. The archive was consulted, relocated and materialised in full.
Then the Java code discarded it:

```java
int size = (high - low) + 1;                                  // (1000 - (-128)) + 1 = 1129
if (archivedCache == null || size > archivedCache.length) {    // 1129 > 256 -> true
    // 1129 constructors run here; the mapped 256 become dead
}
```

So the run pays the archive cost *and* the construction cost, allocates 1129 `Integer` objects
instead of 0, pins them for the JVM's lifetime, and — separately — changes `==` for every value in
128..1000.

**Right**

```java
// Leave the cache range alone. Remove the boxing instead: it is the only change that
// reduces allocation without changing semantics or startup behaviour.
static long reservedTotalMinorUnits(int[] reservationMinorUnits) {
    long total = 0L;                              // no Integer objects at any value
    for (int minorUnits : reservationMinorUnits) {
        total += minorUnits;
    }
    return total;
}
```

Zero allocation at every magnitude, archive intact, `==` semantics unchanged. The escape hatches in
full are [`01g-the-cost-of-boxing.md`](01g-the-cost-of-boxing.md).

**Why people believe it:** both settings are labelled optimisations, they live in different
subsystems, and neither documents the other. The interaction is only visible if you read the `if`
condition in `IntegerCache`'s static block and happen to know the archived array's length is 256, and
the log line that *looks* like confirmation the archive worked — `initialize_from_archived_subgraph`
— is printed on exactly the run where the archive is about to be thrown away.

### Toggling `-Xshare` while chasing a wrapper identity bug

**Wrong**

```
# "The == result is weird, and the cache comes from CDS on this JVM,
#  so let me take CDS out of the picture and see if the behaviour changes."
java -Xshare:off -jar funds-ledger.jar
```

Measured on JDK 21.0.7, `-Xshare:off` produces exactly the default answers:

```
saved property visible? null
127  shared: true
128  shared: false
1000 shared: false
```

Nothing moved. Two hours of bisecting JVM flags have been spent on an axis that carries no semantics,
while the actual cause — a `==` on two `Integer` references — is untouched, and if the environment
also sets `-XX:AutoBoxCacheMax` the real variable is still in play and still hidden.

**Right**

```java
// Isolate the semantics, not the provenance. Print the two things that can actually differ:
// the effective range, probed, and the comparison itself.
static void diagnose(int value) {
    Integer left = Integer.valueOf(value);
    Integer right = Integer.valueOf(value);
    System.out.println(value + " shared: " + (left == right)
            + "  equal: " + left.equals(right)
            + "  identity: " + System.identityHashCode(left)
            + "/" + System.identityHashCode(right));
}
// Then fix the call site: Objects.equals(left, right), or compare unboxed ints.
```

**Why people believe it:** "the cache is loaded from the archive" sounds like a statement about
*what the cache contains*, and a reader who has just learned it reasonably suspects the archive of
being able to change identities. It cannot: the archived array and the constructed array are
element-for-element equivalent, and the only observable difference between the two paths is in the
`cds,heap` log.

---

## Cheat sheet

| Thing | Fact (Java 21 LTS) |
|---|---|
| Who builds `IntegerCache.cache` on a default JDK 21 JVM | the CDS archive, not the construction loop |
| The call | `CDS.initializeFromArchive(IntegerCache.class)`, `jdk.internal.misc.CDS`, native |
| When it is called | **unconditionally**, on every path, in every configuration |
| What it writes | the `archivedCache` field, natively, from outside Java code |
| Why `archivedCache` is not `final` | the VM assigns it; a `final` field written natively would break `final`-based optimisation |
| Which field is `final` | `cache`, assigned once in Java at the end of the block, and `@Stable` |
| Construct-instead-of-map test | `archivedCache == null` or `size > archivedCache.length` |
| Archived array length | 256 |
| Larger archived array | would be accepted (the test is `>`, not `!=`) |
| Default archive mode | `-Xshare:auto` |
| `-Xshare:auto` / `on` / `off` | opportunistic / required / disabled |
| `-Xshare:off` log lines | **zero** `cds,heap` lines |
| `-Xshare:off` semantics | unchanged: 127 shared true, 128 false, 1000 false (measured) |
| `-Xshare:on` measured | same 3 `IntegerCache` log lines as the default |
| Log flag | `-Xlog:cds+heap=info` |
| The three `IntegerCache` log lines | `resolve subgraph`, `init subgraph`, `initialize_from_archived_subgraph` |
| Region fixup line | `Patching native pointers in heap region`, once, before any subgraph is used |
| `(early)` marker | on `Integer$IntegerCache`, absent on `Long$LongCache` — reading unverified |
| Archived subgraphs on a plain startup | **15** measured, of which 5 are wrapper caches |
| Wrapper caches archived | `Integer`, `Long`, `Byte`, `Short`, `Character` |
| Wrappers not archived | `Boolean` (no cache class), `Float`, `Double` (no cache at all) |
| `-XX:AutoBoxCacheMax=1000` and the archive | archive still materialised, then discarded |
| Why discarded | `size = (1000 - (-128)) + 1 = 1129`; `1129 > 256` |
| Net effect of widening | archive cost paid, 1129 objects constructed, 1129 pinned, `==` changed |
| Semantic content of the archive | none — startup only |
| Flag that does change semantics | `-XX:AutoBoxCacheMax` / `-Djava.lang.Integer.IntegerCache.high` |
| JDK 8 shape | no CDS call, no `archivedCache`; the static block is unconditionally the loop |
| Interview one-liner | "built in a static block" is true about the code, incomplete about the behaviour |

---

## Self-test

**Q1.** In Java 21, is the `IntegerCache` array built by a loop or loaded from the CDS archive? What is your evidence?

<details><summary>Answer</summary>

Both are possible, and on a default JVM it is loaded from the archive. The static block calls
`CDS.initializeFromArchive(IntegerCache.class)` unconditionally, which lets the VM natively populate
the non-`final` `archivedCache` field from an archived heap subgraph; the construction loop runs only
if `archivedCache == null || size > archivedCache.length`. Evidence, measured on JDK 21.0.7:
`java -Xlog:cds+heap=info` prints `resolve subgraph java.lang.Integer$IntegerCache`, then
`init subgraph java.lang.Integer$IntegerCache`, then
`initialize_from_archived_subgraph java.lang.Integer$IntegerCache 0x000000c800036b28 (early)`. The
control is `-Xshare:off`, which prints no `cds,heap` lines at all and there the loop builds the array.
So "it is built in a static block" is true about the code and incomplete about the behaviour: the
block runs, and on a default JVM it builds nothing.

</details>

**Q2.** Why is `archivedCache` the only non-`final` field in `IntegerCache`?

<details><summary>Answer</summary>

Because the JVM writes it from outside Java code. `CDS.initializeFromArchive` is a native call that
materialises the archived subgraph and assigns the class's archived field directly, bypassing Java
assignment. A `final` field mutated that way would break every guarantee the compiler and JIT draw
from `final` — constant folding of `low`, and the `@Stable` treatment of `cache`'s elements as
effectively constant after initialisation. So the JDK splits the roles: the field the VM touches is
left non-`final`, and the field the compiler is allowed to trust is a separate `final` field, `cache`,
assigned exactly once in ordinary Java at the end of the static block from whichever array won.

</details>

**Q3.** `CDS.initializeFromArchive` is one of three branches in the static block. True or false?

<details><summary>Answer</summary>

False, and this is the most common misreading. The call sits on the trunk: it executes
unconditionally, on every path and in every configuration, including `-Xshare:off` and including a
run with a widened cache. What follows it is a single `if` with two disjunct conditions —
`archivedCache == null` (the archive gave us nothing) or `size > archivedCache.length` (the archive
gave us something too small) — whose body constructs the array. So the structure is "always consult,
then decide whether to keep", not "choose one of three paths". The measured consequence is the
interesting one: with `-XX:AutoBoxCacheMax=1000`, `initialize_from_archived_subgraph` still fires and
the archived 256 objects are still mapped, and then discarded.

</details>

**Q4.** What exactly does `-XX:AutoBoxCacheMax=1000` cost you at startup, with the arithmetic?

<details><summary>Answer</summary>

It costs you the archived cache, and you pay twice. `high` becomes 1000, so
`size = (high - low) + 1 = (1000 - (-128)) + 1 = 1129`. The archived array's length is 256. The test
`size > archivedCache.length` is `1129 > 256`, true, so the `if` body runs: a 1129-element
`Integer[]` is allocated and 1129 constructors execute. Meanwhile the archive was still consulted in
full — measured, `initialize_from_archived_subgraph java.lang.Integer$IntegerCache` still appears in
`-Xlog:cds+heap=info` — so the mapping and pointer relocation were paid for and the 256 mapped
objects become immediately-dead archived garbage. Net: startup allocation goes up, 1129 objects are
pinned for the JVM's lifetime instead of 256, and separately `==` changes for every value in
128..1000. A flag reached for to reduce allocation increases it before it reduces anything.

</details>

**Q5.** A colleague is debugging a wrapper `==` bug and asks whether `-Xshare:off` might change the behaviour. What do you tell them?

<details><summary>Answer</summary>

No, and here is why the question is the wrong axis. CDS decides *who allocated* the 256 cached
objects and *when* — the archive's mapped region during VM bring-up, or the construction loop in
`<clinit>`. It does not decide *which values are cached*; that is `low` and `high`, and `high` is
moved only by `-XX:AutoBoxCacheMax` or the equivalent `-D` property. Measured on JDK 21.0.7,
`-Xshare:off` gives exactly the default answers: 127 shared true, 128 shared false, 1000 shared
false. The two arrays are element-for-element equivalent and the only observable difference is in the
`cds,heap` log. The flag worth checking in their environment is `-XX:AutoBoxCacheMax`, and the actual
fix is at the call site — `Objects.equals`, or compare unboxed `int` values.

</details>

**Q6.** Name three ways an archived heap subgraph differs from an array built lazily in a static block.

<details><summary>Answer</summary>

First, identity timing: the archived objects exist, at relocated addresses, before `main` is entered
— measured, `IntegerCache`'s materialisation fires at `0.015s` with the `(early)` marker, during VM
bring-up — so no application code can run early enough to precede them, which is why setting the
range from a static initialiser cannot work. Second, memory provenance: they are materialised into
the archive's mapped heap region rather than allocated in Eden, so they do not pressure the nursery
during startup and the pages can be shared between JVMs on the same host. Third, cost attribution:
the archive is produced once when the JDK is built and consumed by every launch, so the construction
cost is not paid by your process at all — whereas the lazy loop pays it on every single start.

</details>

**Q7.** Which wrappers have archived cache subgraphs, and which do not?

<details><summary>Answer</summary>

Five have them: `Integer`, `Long`, `Byte`, `Short` and `Character`, each with a private static nested
cache class holding an `archivedCache` field, and each appearing as a `resolve subgraph` line on a
default JDK 21.0.7 startup. `Boolean` does not, because it has no cache class at all — just
`public static final Boolean TRUE` and `FALSE`, eagerly constructed, so there is nothing to archive
and measured, zero `cds,heap` lines mention `Boolean`. `Float` and `Double` have no cache of any kind
and therefore nothing archived. Note the log list is exhaustive of wrapper *archiving*, not of
wrapper *caching* — `Boolean` still shares its two instances. The coverage table is in the
reference-equality file.

</details>

---

## Open questions

- The meaning of the `(early)` marker on the `initialize_from_archived_subgraph` line is unverified.
  What is established: it appears on `java.lang.Integer$IntegerCache` and not on
  `java.lang.Long$LongCache`, reproducibly across runs on JDK 21.0.7. The reading offered here — that
  it distinguishes subgraphs materialised during early VM bring-up from those materialised on ordinary
  first use — fits the observation and the timestamps but was not confirmed against source. Reading
  `heapShared.cpp` for the code that emits the `(early)` suffix would settle it.
- The archived array's length is treated here as exactly 256, inferred from the fact that
  `-XX:AutoBoxCacheMax=1000` (`size` 1129) rebuilds while the default (`size` 256) does not, which
  brackets it at 256. It was not read directly out of the archive. Dumping the archive with
  `-Xshare:dump -Xlog:cds+heap=debug`, or reflecting on `archivedCache` at runtime with
  `--add-opens java.base/java.lang=ALL-UNNAMED`, would settle it exactly.

---

**Leaves covered:** 1.9.5 (1 leaf)
**Leaves deferred:** none
**Diagrams included:** none
**Target version:** Java 21 LTS
**Lines:** 646
