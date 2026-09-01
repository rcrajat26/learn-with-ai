# 02 Java Collections — Immutability and views — INTERNALS (§3.12.9–3.12.12)

**Target version: Java 21 LTS.** | [Index](../00-index.md)
Previous: [immutable-collections/04b-internals-open-addressing-and-salt.md](04b-internals-open-addressing-and-salt.md) · Next: [immutable-collections/04c-internals-mutators-serialization-and-views.md](04c-internals-mutators-serialization-and-views.md)

All source citations are against `java.base/java/util/ImmutableCollections.java`
from `jdk-21.jdk/Contents/Home/lib/src.zip`, JDK 21.0.7+8-LTS-245. Bare `:NNN`
line numbers refer to that file. All transcripts are from that build on
macOS/aarch64 (Darwin 25.5.0).

`04b` established the storage layout: `SetN` and `MapN` hold one flat
`EXPAND_FACTOR * n`-slot array, resolve collisions by linear probing, and their
`probe` methods are **entirely salt-free**, so placement and lookup are
deterministic. This file picks up the field that *is* random —
`SALT32L`/`REVERSE` — and then covers the CDS interaction and null hostility.

---

## Concept 2 — `SALT32L`, `REVERSE`, and per-JVM-run iteration order

*Leaves 3.12.9, 3.12.10.*

### Mental model

Two runners on the same circular track of `2n` slots. The starting line is chosen
by a coin flip taken once when the class loads, and so is the direction of travel.
Both visit every occupied slot exactly once and report the same *set*; they report
it in different *orders*. That is `SetN` iteration across two JVM runs.

### Why it exists

`Set.of` and `Map.of` specify no iteration order. Historically,
unspecified-but-stable JDK behaviour gets depended on anyway: `HashMap`'s
pre-Java-8 order was "unspecified", and the Java 8 change to it broke a great deal
of code that had quietly relied on it. The Java 9 factories were designed to
foreclose that. Rather than being stable-and-unspecified, they are *actively
randomised per JVM run*, so order-dependent code fails visibly on some machine,
some day. This is one of very few JDK behaviours introduced specifically to break
code relying on an unspecified detail. The instability is the feature.

### When to reach for it, and when not

This is not a thing you choose — it is a property you must design around.

| Need | Use | Why |
|---|---|---|
| Guaranteed order, immutable | `List.of` | indexed storage; `ListN` has no salt |
| Insertion order, mutable | `LinkedHashSet` / `LinkedHashMap` | explicit linkage |
| Sorted order | `TreeSet` / `TreeMap` | comparator-defined |
| Membership only, order irrelevant | `Set.of` / `Map.of` | smallest footprint; order instability costs nothing |

### How it works — the static initialiser, `:52-87`

```java
    /**
     * A "salt" value used for randomizing iteration order. This is initialized once
     * and stays constant for the lifetime of the JVM. It need not be truly random, but
     * it needs to vary sufficiently from one run to the next so that iteration order
     * will vary between JVM runs.
     */
    private static final long SALT32L;

    /**
     * For set and map iteration, we will iterate in "reverse" stochastically,
     * decided at bootstrap time.
     */
    private static final boolean REVERSE;
    static {
        // to generate a reasonably random and well-mixed SALT, use an arbitrary
        // value (a slice of pi), multiply with a random seed, then pick
        // the mid 32-bits from the product. By picking a SALT value in the
        // [0 ... 0xFFFF_FFFFL == 2^32-1] range, we ensure that for any positive
        // int N, (SALT32L * N) >> 32 is a number in the [0 ... N-1] range. This
        // property will be used to avoid more expensive modulo-based
        // calculations.
        long color = 0x243F_6A88_85A3_08D3L; // slice of pi

        // When running with -Xshare:dump, the VM will supply a "random" seed that's
        // derived from the JVM build/version, so can we generate the exact same
        // CDS archive for the same JDK build. This makes it possible to verify the
        // consistency of the JDK build.
        long seed = CDS.getRandomSeedForDumping();
        if (seed == 0) {
          seed = System.nanoTime();
        }
        SALT32L = (int)((color * seed) >> 16) & 0xFFFF_FFFFL;
        // use the lowest bit to determine if we should reverse iteration
        REVERSE = (SALT32L & 1) == 0;
    }
```

- The javadoc at `:52-58` is the contract: initialised once, constant for the JVM
  lifetime, need not be cryptographically random, must vary run to run. Order is
  therefore **stable within one JVM and unstable across JVMs** — both halves
  matter.
- `color = 0x243F_6A88_85A3_08D3L` is the first 64 bits of pi's fractional part, a
  nothing-up-my-sleeve mixing constant.
- `seed = CDS.getRandomSeedForDumping()` — see leaf 3.12.11 below. At ordinary
  runtime this returns 0 and the seed becomes `System.nanoTime()`.
- `SALT32L = (int)((color * seed) >> 16) & 0xFFFF_FFFFL` — multiply, shift out the
  low 16 bits (the least-mixed in a 64-bit product), narrow to `int` to keep bits
  16–47, then mask back to a **non-negative** `long` in `[0, 2^32)`. The mask is
  what makes the range property in the comment hold.
- `REVERSE = (SALT32L & 1) == 0` — leaf 3.12.9's "low bit" claim, confirmed
  verbatim. One coin. Note the polarity: `REVERSE` is `true` when the low bit is
  **zero**, easy to get backwards.
- Both fields are `private static final` and are **not** in the `archivedObjects`
  array (`:91-117`). They are recomputed on every class initialisation.

The range trick is used at `:954-959`:

```java
            SetNIterator() {
                remaining = size;
                // pick a starting index in the [0 .. element.length-1] range
                // randomly based on SALT32L
                idx = (int) ((SALT32L * elements.length) >>> 32);
            }
```

`SALT32L` is in `[0, 2^32)` and `elements.length` is a positive `int`, so the
product's top 32 bits land in `[0, elements.length)`. Multiply-shift range
reduction: one `imul` and one shift, no division. **[NUM]** With
`SALT32L == 0x8000_0000` and `elements.length == 12`, the product is
`0x6_0000_0000` and `>>> 32` gives 6 — the midpoint, as expected.

The walk, `:966-990`:

```java
            @Override
            public E next() {
                if (remaining > 0) {
                    E element;
                    int idx = this.idx;
                    int len = elements.length;
                    // step to the next element; skip null elements
                    do {
                        if (REVERSE) {
                            if (++idx >= len) {
                                idx = 0;
                            }
                        } else {
                            if (--idx < 0) {
                                idx = len - 1;
                            }
                        }
                    } while ((element = elements[idx]) == null);
                    this.idx = idx;
                    remaining--;
                    return element;
                } else {
                    throw new NoSuchElementException();
                }
            }
```

- `REVERSE` picks `++idx` (ascending, wrapping at `len`) or `--idx` (descending,
  wrapping at `-1`). Confusingly, `REVERSE == true` gives the *ascending* walk.
- The `do/while` skips `null` slots; it terminates because `remaining > 0`
  guarantees an occupied slot somewhere on the circle.
- `remaining` decrements per element, so the iterator stops after exactly `size`
  elements regardless of where it started.

`MapNIterator` is the same shape with stride 2, `:1266-1290`: the constructor is
`idx = (int) ((SALT32L * (table.length >> 1)) >>> 32) << 1` — range-reduce over
pair slots, then double to land on an even (key) index — and `nextIndex()` does
`idx += 2` / `idx -= 2`, wrapping to `0` and `table.length - 2`.

**This is the whole of the salt's reach.** `SALT32L` appears at `:59`, `:71` (a
comment), `:84`, `:958` and `:1270`. `REVERSE` appears at `:65`, `:86`, `:840`,
`:843`, `:869`, `:884`, `:974` and `:1280`. Every usage site is inside an iterator
(`:840-884` are `Set12`'s and `Map1`/`Map2`'s iterators, which flip the order of
their two fixed fields). **Neither field appears in `SetN.probe`, `MapN.probe`,
either constructor, `contains`, `containsKey`, `get` or `hashCode`.** Placement and
lookup are entirely salt-free — which is why `04b`'s reflective table dump is
reproducible while the iteration order below is not.

### [PROVE] Two JVM runs, two orders

```java
import java.util.Map;
import java.util.Set;

public class OrderRun {
    public static void main(String[] args) {
        Set<String> s = Set.of("a", "b", "c", "d", "e", "f");
        Map<String, Integer> m = Map.of("a", 1, "b", 2, "c", 3, "d", 4, "e", 5, "f", 6);

        System.out.println("set iteration  : " + s);
        System.out.println("set again      : " + s);   // stable within one JVM
        System.out.println("map iteration  : " + m.keySet());
        // lookups are order-independent -- prove they agree regardless
        System.out.println("lookups        : "
                + s.contains("a") + s.contains("f") + s.contains("z")
                + " / " + m.get("c") + m.get("f"));
    }
}
```

Three consecutive invocations of the identical command line, same JDK, same
machine, nothing else changed:

```
$ java -cp out OrderRun
set iteration  : [d, e, f, a, b, c]
set again      : [d, e, f, a, b, c]
map iteration  : [d, e, f, a, b, c]
lookups        : truetruefalse / 36

$ java -cp out OrderRun
set iteration  : [e, f, a, b, c, d]
set again      : [e, f, a, b, c, d]
map iteration  : [e, f, a, b, c, d]
lookups        : truetruefalse / 36

$ java -cp out OrderRun
set iteration  : [f, e, d, c, b, a]
set again      : [f, e, d, c, b, a]
map iteration  : [f, e, d, c, b, a]
lookups        : truetruefalse / 36
```

Three separate facts come out of that.

1. **Across runs the order differs.** Runs 1 and 2 differ only in starting point —
   both ascending, so `REVERSE` was `true` in both and the salt's high bits chose
   different start slots. Run 3 is *descending*: `f, e, d, c, b, a`, i.e.
   `REVERSE == false`, i.e. `SALT32L`'s low bit was 1 that time. Because `REVERSE`
   is a single bit, a direction flip is a coin toss — expect two consecutive runs to
   agree on direction about half the time. Runs 1 and 2 are exactly that case, which
   is why this demonstration is worth running three times rather than two.
2. **Within one run the order is fixed.** `set iteration` and `set again` match in
   every run. `SALT32L` is `static final`, set once; a fresh `SetNIterator`
   recomputes the same start. Code that iterates twice in one process and compares
   will never catch this bug.
3. **Lookups are unaffected.** `truetruefalse / 36` in all three runs. Placement is
   salt-free, so `contains` and `get` are bit-for-bit reproducible while iteration
   is not. That is the practical dividing line.

**Pitfall:** *believing `Set.of`'s iteration order is stable because your tests
pass.* Symptom: green CI, then a failure in production or on a colleague's machine
— a mismatched golden file, a differently-ordered generated SQL `IN (…)` list, a
changed CSV column order, a log line that no longer matches a regex. The order is
stable for the whole of every test JVM's life, so no in-process test can find it.
Fix: if you need order, do not use `Set.of`/`Map.of` for it. Use `List.of`
(indexed, guaranteed, `ListN` has no salt), `LinkedHashSet`/`LinkedHashMap` for
insertion order, `TreeSet`/`TreeMap` for sorted order — and if you must consume a
`Set.of`, sort at the boundary with `set.stream().sorted().toList()`.

**Interview:** *"Why does `Set.of(...)` iterate differently every time I restart my
program?"* — `ImmutableCollections.SALT32L` is derived from `System.nanoTime()` in
a static initialiser and `REVERSE` from its low bit (`:66-87`), and the
`SetN`/`MapN` iterators use them to choose a starting slot and a direction. It is
deliberate, so nothing comes to depend on an unspecified order. Placement and
lookup are unaffected — `probe` uses no salt.

> **Definition.** `SALT32L` is a per-JVM 32-bit value derived once at
> `ImmutableCollections` class initialisation from `System.nanoTime()` (or, under
> `-Xshare:dump`, a build-derived CDS seed), and `REVERSE` is its low bit inverted;
> the `SetN` and `MapN` iterators — and only they — consume the two to pick a
> starting slot and a walk direction, making iteration order of `Set.of`/`Map.of`
> deliberately unstable across JVM runs while remaining stable within one and
> leaving element placement and lookup fully deterministic.

---

## Leaf 3.12.11 — the CDS/AOT interaction

*Supporting fact, `[RESEARCH]`-only. The syllabus statement needs correcting.*

The syllabus says: "the salt can come from the CDS archive so archived immutable
collections stay consistent." The source supports the first clause only in a
narrow, dump-time sense, and does not support the second at all.

`:80` reads `long seed = CDS.getRandomSeedForDumping();` and `:81-83` fall back to
`System.nanoTime()` when it returns 0. The javadoc on that native method,
`java.base/jdk/internal/misc/CDS.java:96-101`, is explicit:

```java
    /**
     * Returns a predictable "random" seed derived from the VM's build ID and version,
     * to be used by java.util.ImmutableCollections to ensure that archived
     * ImmutableCollections are always sorted the same order for the same VM build.
     */
    public static native long getRandomSeedForDumping();
```

And the comment above the call site, `:76-79`, scopes it: "When running with
`-Xshare:dump`, the VM will supply a 'random' seed that's derived from the JVM
build/version, so can we generate the exact same CDS archive for the same JDK
build. This makes it possible to verify the consistency of the JDK build."

The accurate statement:

- The seed is build-derived **only while dumping an archive** (`-Xshare:dump`). The
  purpose is **reproducible archive builds** — a JDK build-verification property,
  not a user-facing one.
- At ordinary runtime, including `-Xshare:on` with the default archive,
  `getRandomSeedForDumping()` returns 0 and the salt comes from `System.nanoTime()`.
  Loading a CDS archive does **not** restore a salt.
- `SALT32L` and `REVERSE` are not among `archivedObjects` (`:91-117`); only
  `EMPTY`, `EMPTY_LIST`, `EMPTY_LIST_NULLS`, `EMPTY_SET` and `EMPTY_MAP` are, and
  those are all empty, so their iteration order is trivially invariant.
- The syllabus's "so archived immutable collections stay consistent" is therefore
  **wrong as a runtime claim.** Archived immutable collections do not iterate
  consistently across runs; the salt their iterators consult is fresh every run.

**Observable check.** Same program under `-Xshare:on` (which forces archive use —
the JVM refuses to start if it cannot map it), three invocations:

```
$ java -Xshare:on -cp out OrderRun | head -1
set iteration  : [a, b, c, d, e, f]
$ java -Xshare:on -cp out OrderRun | head -1
set iteration  : [a, b, c, d, e, f]
$ java -Xshare:on -cp out OrderRun | head -1
set iteration  : [c, d, e, f, a, b]
```

Two runs agreed, the third did not — exactly a per-run `nanoTime` salt, and not
what you would see if the archive pinned the order.

**Unverified:** whether the Java 24+ AOT-cache work that generalises CDS changes
any of the above; this file targets Java 21 and only the 21.0.7 source was checked.
**Unverified:** whether any *non-empty* immutable collection is actually archived
in the default CDS archive — the only case where dump-time salt determinism could
have an observable effect. Both are in Open questions below.

> **Definition.** The CDS interaction is dump-time only:
> `CDS.getRandomSeedForDumping()` supplies a JDK-build-derived seed while
> `-Xshare:dump` runs so archives are reproducible for a given build, and returns 0
> at ordinary runtime so the salt falls back to `System.nanoTime()` — loading an
> archive does not pin iteration order.

---

## Leaf 3.12.12 — null hostility, and what "on some paths" actually means

The syllabus says `List.of(null)` NPEs, `Set.of(...).contains(null)` "NPEs on some
paths", and `Map.of(k, null)` NPEs. The measured behaviour, established across this
note set, is that **within `ImmutableCollections` null rejection is uniform, not
path-dependent.** Every product of `List.of`, `List.copyOf`, `Set.of`, `Set.copyOf`,
`Map.of` and `Map.copyOf` throws `NullPointerException` on a null query — including
the empty ones, `subList` views and Java 21 `reversed()` views. The `List` half of
that matrix lives in [`03c-null-queries-and-guava.md`](03c-null-queries-and-guava.md);
this file covers the `Set`/`Map` side and the mechanism.

What *does* vary is the **throw site**, and that is the only defensible reading of
"some paths":

| Path | Guard | Throw site |
|---|---|---|
| `SetN.contains` `:944` | explicit `Objects.requireNonNull(o)` | `Objects.requireNonNull` |
| `SetN(E... input)` `:923` | implicit, via `pe.hashCode()` in `probe` | `SetN.probe` |
| `MapN.containsKey` `:1207` | explicit `Objects.requireNonNull(o)` | `Objects.requireNonNull` |
| `MapN.get`, non-empty `:1242` | implicit, via `pk.hashCode()` in `probe` | `MapN.probe` |
| `MapN.get`, empty `:1238-1240` | explicit, then `return null` | `Objects.requireNonNull` |
| `MapN.containsValue` `:1213` | explicit `Objects.requireNonNull(o)` | `Objects.requireNonNull` |
| `MapN(Object... input)` `:1191`, `:1193` | explicit on key **and** value | `Objects.requireNonNull` |

`MapN.get` is the interesting row: on a **non-empty** map a null key NPEs *inside
`probe`*, because `get` calls `requireNonNull` only in its `size == 0` branch. Two
different frames for the same user-visible NPE. That, and nothing more, is the
"some paths". The `Set12` and `Map1`/`Map2` arities have their own guards and so
appear with their own frames.

Every throwing call below is wrapped, so the program runs to completion:

```java
import java.util.Arrays;
import java.util.Collections;
import java.util.HashSet;
import java.util.Map;
import java.util.Set;
import java.util.function.Supplier;
import java.util.stream.Stream;

public class NullHostility2 {

    /** Every call is wrapped, so the program always runs to completion. */
    static void probe(String label, Supplier<?> body) {
        try {
            System.out.printf("%-38s -> %s%n", label, body.get());
        } catch (Throwable t) {
            StackTraceElement top = t.getStackTrace()[0];
            System.out.printf("%-38s -> %s at %s.%s%n", label,
                    t.getClass().getSimpleName(), top.getClassName(), top.getMethodName());
        }
    }

    public static void main(String[] args) {
        probe("Set.of(a,b,c).contains(null)", () -> Set.of("a", "b", "c").contains(null));
        probe("Set.of().contains(null)", () -> Set.of().contains(null));
        probe("Map.of(a,1,b,2).get(null)", () -> Map.of("a", 1, "b", 2).get(null));
        probe("Map.of().get(null)", () -> Map.of().get(null));
        probe("Map.of(a,1).containsKey(null)", () -> Map.of("a", 1).containsKey(null));
        probe("Map.of(a,1).containsValue(null)", () -> Map.of("a", 1).containsValue(null));
        probe("Map.of(a,1).keySet().contains(null)", () -> Map.of("a", 1).keySet().contains(null));
        probe("Set.of(a, null)   [construction]", () -> Set.of("a", null));
        probe("Map.of(a, null)   [construction]", () -> Map.of("a", (Integer) null));
        // The lenient family, for contrast.
        probe("Stream.toList().contains(null)", () -> Stream.of("a").toList().contains(null));
        probe("Arrays.asList(a).contains(null)", () -> Arrays.asList("a").contains(null));
        probe("unmodifiableSet(HashSet).contains(null)",
                () -> Collections.unmodifiableSet(new HashSet<>(Set.of("a"))).contains(null));
    }
}
```

```
$ java -cp out NullHostility2
Set.of(a,b,c).contains(null)           -> NullPointerException at java.util.Objects.requireNonNull
Set.of().contains(null)                -> NullPointerException at java.util.Objects.requireNonNull
Map.of(a,1,b,2).get(null)              -> NullPointerException at java.util.ImmutableCollections$MapN.probe
Map.of().get(null)                     -> NullPointerException at java.util.Objects.requireNonNull
Map.of(a,1).containsKey(null)          -> NullPointerException at java.util.ImmutableCollections$Map1.containsKey
Map.of(a,1).containsValue(null)        -> NullPointerException at java.util.ImmutableCollections$Map1.containsValue
Map.of(a,1).keySet().contains(null)    -> NullPointerException at java.util.ImmutableCollections$Map1.containsKey
Set.of(a, null)   [construction]       -> NullPointerException at java.util.Objects.requireNonNull
Map.of(a, null)   [construction]       -> NullPointerException at java.util.Objects.requireNonNull
Stream.toList().contains(null)         -> false
Arrays.asList(a).contains(null)        -> false
unmodifiableSet(HashSet).contains(null) -> false
```

Nine NPEs, four distinct throw sites, zero `false` results from anything
`ImmutableCollections` produced — including `Set.of()`, which has nothing to
compare against and still refuses the question. The three `false` results are the
lenient family: `Stream.toList()` (a `ListN` with `allowNulls == true`, per `04`),
and the pre-Java-9 `Arrays.asList` / `Collections.unmodifiable*` wrappers, which
delegate to a null-tolerant backing collection.

The `List`-side mechanism, established in `03c` and worth restating because it is
what makes the syllabus's "some paths" *sound* plausible: `ListN` does not override
`contains`; `AbstractImmutableList.contains(o)` is `return indexOf(o) >= 0;`
(`:329-332`), and the guard is `if (!allowNulls && o == null) throw new
NullPointerException();` at `:722` (`lastIndexOf` at `:736`). That `allowNulls`
flag is the *only* lever in the class, and `Stream.toList()` is the only public API
that flips it.

**Pitfall:** *treating `Set.of(...)` / `Map.of(...)` as a drop-in replacement for
`HashSet` / `HashMap` in code that queries with possibly-null values.* Symptom: an
NPE from a `contains`/`get`/`containsKey` call that never threw before, often far
from the factory call and only on the path where the value happens to be absent.
Fix: null-guard at the boundary (`o != null && set.contains(o)`), or keep the
`HashSet`/`HashMap`. Do not reach for `Collections.unmodifiableSet` just to regain
null tolerance — that gives you a mutable-backing view, which `04c` covers.

> **Definition.** `ImmutableCollections` rejects null uniformly — at construction
> and on every query, across every arity, view and empty singleton — throwing
> `NullPointerException` either from an explicit `Objects.requireNonNull` or from
> the implicit `hashCode()` dereference inside `probe`; the syllabus's "on some
> paths" describes only the varying throw *site*, not varying leniency.

---

## Pitfalls

### Assuming `Set.of` iteration order is stable

**Wrong**

```java
Set<String> cols = Set.of("id", "name", "email", "createdAt");
String header = String.join(",", cols);   // "id,name,email,createdAt"? sometimes.
```

Three JVM runs of the equivalent program above printed `[d, e, f, a, b, c]`, then
`[e, f, a, b, c, d]`, then `[f, e, d, c, b, a]`. The third is not even the same
direction.

**Right**

```java
List<String> cols = List.of("id", "name", "email", "createdAt");
String header = String.join(",", cols);   // always "id,name,email,createdAt"
```

`List.of` produces `ListN`, which stores elements at their given indices and whose
iterator is a plain ascending index walk — no `SALT32L` anywhere in `ListN`. If a
`Set` is genuinely required, use `LinkedHashSet`, or sort at the boundary with
`set.stream().sorted().toList()`.

**Why people believe it:** `SALT32L` is `static final`, so within a single JVM the
order never moves. Every unit test, REPL session and debug run agrees with itself.
The instability is invisible to any observation made inside one process.

### Believing `SALT32L` randomises where elements are stored

**Wrong**

```java
// "Set.of placement is randomised, so I can't reason about probe order,
//  and it protects me from hash-collision DoS."
```

**Right**

```java
int idx = Math.floorMod(pe.hashCode(), elements.length);   // SetN.probe, :1014
```

No salt term. `04b`'s reflective dump is byte-identical across runs. `SALT32L` and
`REVERSE` appear only in iterator code (`:840`, `:843`, `:869`, `:884`, `:958`,
`:974`, `:1270`, `:1280`). And because placement is predictable from the public
`hashCode()` contract, `Set.of` has **no** collision-DoS resistance — with no
treeify fallback, forced collisions give `O(n)` lookups.

**Why people believe it:** the field's own javadoc calls it "a salt value used for
randomizing iteration order", and "salt" in every other context means hash
perturbation. Read the second half of the sentence.

### Expecting CDS / `-Xshare` to stabilise iteration order

**Wrong**

```
$ java -Xshare:on -cp out OrderRun   # "the archive pins the salt, so this is stable"
```

**Right**

Three `-Xshare:on` runs gave `[a..f]`, `[a..f]`, then `[c, d, e, f, a, b]`.
`CDS.getRandomSeedForDumping()` returns non-zero only under `-Xshare:dump`
(`:76-83`); at runtime the salt is `System.nanoTime()`.

**Why people believe it:** the source comment near the seed call does mention CDS,
and the archive genuinely does restore `EMPTY_SET` and `EMPTY_MAP` from
`archivedObjects`. Restoring empty singletons is not pinning a salt.

### Treating `Set.of(...).contains(x)` as null-safe

**Wrong**

```java
Set<String> allowed = Set.of("a", "b", "c", "d");
if (allowed.contains(request.getHeader("X-Mode"))) { /* NPE when header absent */ }
```

**Right**

```java
String mode = request.getHeader("X-Mode");
if (mode != null && allowed.contains(mode)) { /* safe */ }
```

**Why people believe it:** `HashSet.contains(null)` returns `false`, and so do
`Arrays.asList(...)` and `Collections.unmodifiableSet(...)` — as the transcript
above shows. The Java 9 factories broke with two decades of tolerance here.

---

## Cheat sheet

| Thing | Value / fact | Source |
|---|---|---|
| `SALT32L` | `(int)((pi_slice * seed) >> 16) & 0xFFFF_FFFFL`, in `[0, 2^32)` | `:84` |
| `SALT32L` seed | `CDS.getRandomSeedForDumping()`, else `System.nanoTime()` | `:80-83` |
| `REVERSE` | `(SALT32L & 1) == 0` — note: `true` means **ascending** | `:86`, `:974` |
| Salt consumers | `SetNIterator` `:958`/`:974`, `MapNIterator` `:1270`/`:1280`, `Set12`/`Map1`/`Map2` iterators `:840-884` | — |
| Salt in `probe`? | **No.** Placement and lookup fully deterministic | `:1013-1024`, `:1327-1338` |
| Iterator start | multiply-shift `(int)((SALT32L * len) >>> 32)`, no division | `:958` |
| `MapNIterator` start | same, over pair slots, then `<< 1` onto an even index | `:1270` |
| Order stability | stable within one JVM, unstable across runs, by design | `:52-58` |
| Measured, 3 runs | `[d,e,f,a,b,c]`, `[e,f,a,b,c,d]`, `[f,e,d,c,b,a]` — run 3 is a direction flip | — |
| Lookups across runs | identical in all runs; salt-free placement | — |
| CDS at runtime | no effect on order; build-derived seed only under `-Xshare:dump` | `CDS.java:96-101` |
| Measured, `-Xshare:on` | `[a..f]`, `[a..f]`, `[c,d,e,f,a,b]` — archive does not pin order | — |
| Archived from CDS | `EMPTY`, `EMPTY_LIST`, `EMPTY_LIST_NULLS`, `EMPTY_SET`, `EMPTY_MAP` — not the salt | `:91-117` |
| Null query | always NPE, every arity, including `Set.of()` / `Map.of()` | `:944`, `:1207` |
| Null throw site | `Objects.requireNonNull` (explicit) or `probe` (implicit `hashCode`) | `:944` vs `:1242` |
| `MapN.get(null)` | non-empty map → throws in `probe`; empty map → throws in `requireNonNull` | `:1242` vs `:1238-1240` |
| Null-tolerant siblings | `Stream.toList()`, `Arrays.asList`, `Collections.unmodifiable*` | — |
| Two empty lists | `EMPTY_LIST` (`allowNulls == false`) vs `EMPTY_LIST_NULLS` — `equals`, differ on `contains(null)` | `:105-106` |
| Introduced | Java 9; order randomisation added deliberately to break order-dependence | — |

---

## Self-test

**Q1.** Two JVM runs print `Set.of("a","b","c","d")` in different orders, but
`contains("c")` is `true` in both. Which mechanism causes each half?

<details><summary>Answer</summary>

Different orders: `SALT32L` comes from `System.nanoTime()` in the static
initialiser (`:66-87`), so it differs per run; `SetNIterator`'s constructor uses it
to pick a starting slot (`idx = (int)((SALT32L * elements.length) >>> 32)`, `:958`),
and `REVERSE = (SALT32L & 1) == 0` picks the direction (`:974`).

Same `contains`: `SetN.contains` calls `probe` (`:945`), whose home slot is
`Math.floorMod(pe.hashCode(), elements.length)` (`:1014`) — no salt term at all.
Placement in the constructor uses the same salt-free `probe`. So the table layout
is byte-identical across runs and lookup is fully deterministic. The randomisation
is confined to iterators.

</details>

**Q2.** `REVERSE` is `true`. Which way does `SetNIterator` walk, and what does that
tell you about `SALT32L`?

<details><summary>Answer</summary>

Ascending. `:974-982`: `if (REVERSE) { if (++idx >= len) idx = 0; } else { if
(--idx < 0) idx = len - 1; }`. The name is counterintuitive — `REVERSE == true`
increments. And `REVERSE = (SALT32L & 1) == 0` (`:86`), so `REVERSE == true` means
`SALT32L`'s low bit was **zero**. Two inversions to get wrong, and the reason the
three-run transcript is worth reading carefully: runs 1 and 2 were ascending
(`REVERSE == true`), run 3 descending.

</details>

**Q3.** Does `-Xshare:on` make `Set.of` iteration order reproducible?

<details><summary>Answer</summary>

No. `CDS.getRandomSeedForDumping()` (`:80`) returns a build-derived seed only while
`-Xshare:dump` runs; its javadoc (`CDS.java:96-101`) scopes it to making archives
reproducible for a given JDK build. At ordinary runtime it returns 0 and `:82`
falls back to `System.nanoTime()`. Measured: three `-Xshare:on` runs gave
`[a..f]`, `[a..f]`, `[c, d, e, f, a, b]`. What the archive does restore is
`archivedObjects` (`:91-117`) — `EMPTY`, `EMPTY_LIST`, `EMPTY_LIST_NULLS`,
`EMPTY_SET`, `EMPTY_MAP` — and `SALT32L` is not in it. The syllabus's claim that
archived immutable collections "stay consistent" at runtime is wrong.

</details>

**Q4.** Why does `Set.of()` throw on `contains(null)` instead of returning `false`?

<details><summary>Answer</summary>

`SetN.contains` is `Objects.requireNonNull(o); return size > 0 && probe(o) >= 0;`
(`:943-946`). The null check runs *before* the `size > 0` short-circuit, so the NPE
wins. `EMPTY_SET = new SetN<>()` (`:107`) also has `elements.length == 0`, and the
`size > 0` guard exists to stop `Math.floorMod(h, 0)` throwing
`ArithmeticException` — but it never gets the chance for a null argument. This is
one half of the two-canonical-empties story: `EMPTY_LIST` (`:105`,
`allowNulls == false`) and `EMPTY_LIST_NULLS` (`:106`) are `equals` yet disagree
about `contains(null)`.

</details>

**Q5.** `Map.of("a",1,"b",2).get(null)` and `Map.of().get(null)` both throw NPE.
From where, and why does it differ?

<details><summary>Answer</summary>

`MapN.get` (`:1235-1248`) calls `Objects.requireNonNull(o)` **only** inside its
`if (size == 0)` branch (`:1238-1240`). So:

- Empty map: the explicit `requireNonNull` fires — stack top is
  `java.util.Objects.requireNonNull`.
- Non-empty map: control skips that branch and reaches `probe(o)` at `:1242`, where
  `pk.hashCode()` dereferences the null — stack top is
  `java.util.ImmutableCollections$MapN.probe`.

Measured exactly that way in the transcript above. This asymmetry is the *only*
defensible reading of the syllabus's "NPEs on some paths": the leniency never
varies (9 of 9 queries threw), only the throw site does, across four distinct
frames.

</details>

**Q6.** A colleague says the salt makes `Set.of` resistant to hash-collision DoS. Right?

<details><summary>Answer</summary>

Wrong. Collision-DoS resistance requires perturbing *placement* — a per-process
secret mixed into the index computation, so an attacker cannot precompute colliding
keys. `SetN.probe` (`:1014`) and `MapN.probe` (`:1328`) use only
`Math.floorMod(hashCode(), len)` with no salt term, so placement is fully
predictable from the public `hashCode()` contract. An attacker who controls
`Set.of`/`Map.of` contents can force every key onto one home slot and make lookups
`O(n)`, and unlike `HashMap` there is no treeify fallback to bound it at
`O(log n)`. `SALT32L` randomises iteration order only, and its own javadoc says it
"need not be truly random" (`:52-58`) — which no security mechanism could say.

</details>

---

## Open questions

1. **AOT-cache behaviour past Java 21.** Whether the Java 24+ AOT-cache work that
   generalises CDS changes the seed handling in the static initialiser. Settled by
   diffing `:66-87` and `CDS.getRandomSeedForDumping`'s javadoc against a JDK 24+
   `src.zip`, and re-running the three-invocation order test under `-XX:AOTCache`.
2. **Whether any non-empty immutable collection is actually archived.**
   `archivedObjects` (`:91-117`) holds only empty singletons, whose order is
   trivially invariant, so dump-time salt determinism has no observable effect
   through that path. If the JDK archives non-empty `SetN`/`MapN` instances
   elsewhere (heap-archived module or `MethodHandle` data, say), their iteration
   order would still be recomputed per run from the fresh salt — so the consistency
   the `CDS.java` javadoc mentions is most likely about *dumped byte layout*, not
   runtime order. Settled by dumping an AppCDS archive with `-Xlog:cds+heap=debug`
   and looking for archived `ImmutableCollections$SetN` / `$MapN` instances.

---

**Leaves covered:** 3.12.9–3.12.12 (4 leaves)
**Leaves deferred:** none
**Diagrams included:** none
**Target version:** Java 21 LTS
**Lines:** 704
