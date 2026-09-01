# 03 Java Core — `MyString` — the intern pool, and the diff against `java.lang.String` — BUILD IT (§4.1 — 4.1.4, 4.1.6)

**Target version: Java 21 LTS.** | **Part 4 of 5** | [Index](../00-index.md)
Previous: [MyString](01-mystring-and-mystringbuilder.md) · Next: [MyStringBuilder](01b-mystringbuilder.md)

A static map from a value to itself, and a table of everything the real thing does that yours does
not. Those two subjects belong together because they fail the same way: both are places where a
faithful-looking reimplementation is quietly not the thing it resembles. A `HashMap` keyed by
`MyString` looks exactly like "the string pool" as it is taught, and retains every key forever. A
class with `value`, `coder`, `hash` and `hashIsZero` looks exactly like `java.lang.String`'s field
set, and has none of its `@Stable`, its intrinsics, its constant-pool wiring or its serial form.

The `MyString` implementation itself, its defensive copy, its cached hash and its `coder`
arithmetic are in [the previous file](01-mystring-and-mystringbuilder.md); everything below assumes
that class.

Everything here was compiled and run on **Oracle JDK 21.0.7 (build 21.0.7+8-LTS-245), macOS
aarch64 (Apple silicon)**, compressed oops on. Every `console` block is real captured output.

---

## 4.1.4 `[PROVE]` A tiny intern pool, and the leak it creates without weak keys

**Why it exists.** QuizStakes writes ~19.8M ledger entries a day, each stamped with one of a few
dozen status-code strings. Storing 19.8M distinct instances of `AA-610 DOCUMENTS_UPLOADED` costs
19.8M × 80 bytes; storing one and sharing it costs 80 bytes. That is the whole case for interning,
and it is a good case — *for a bounded key set*.

**How it works.** A canonicalising map from a value to itself: look up, return the canonical
instance if present, otherwise install this one as canonical.

| Pool | Key held | Value held | Entry survives the caller dropping the key? |
|---|---|---|---|
| `HashMap<MyString, MyString>` | strongly | strongly | **yes, forever** |
| `WeakHashMap<MyString, MyString>` | weakly | **strongly** | **yes, forever** — the value resurrects its own key |
| `WeakHashMap<MyString, WeakReference<MyString>>` | weakly | weakly | no |

The middle row catches everyone who reached for `WeakHashMap` and stopped thinking. A
`WeakHashMap` entry holds its key weakly but its *value* strongly, so an entry whose value **is**
its key keeps a strong path to the key alive through the entry. The map is weak; the usage defeats
it.

All three, measured. The keys are per-request `IdempotencyKey` values — one per stake reservation,
36 characters of UUID, unbounded in number, exactly the wrong thing to intern.
`WeakPoolSelfValued` below is `StrongPool`'s body verbatim with `new WeakHashMap<>()` in place of
`new HashMap<>()`, which is the entire point of including it.

```java
import java.lang.ref.ReferenceQueue;
import java.lang.ref.WeakReference;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import java.util.WeakHashMap;

public final class InternPoolDemo {

    static final class StrongPool {
        private static final Map<MyString, MyString> POOL = new HashMap<>();

        static MyString intern(MyString candidate) {
            MyString existing = POOL.get(candidate);
            if (existing != null) {
                return existing;
            }
            POOL.put(candidate, candidate);
            return candidate;
        }
        static int size() {
            return POOL.size();
        }
    }

    static final class WeakPoolSelfValued {
        private static final Map<MyString, MyString> POOL = new WeakHashMap<>();

        static MyString intern(MyString candidate) {
            MyString existing = POOL.get(candidate);
            if (existing != null) {
                return existing;
            }
            POOL.put(candidate, candidate);
            return candidate;
        }
        static int size() {
            return POOL.size();
        }
    }

    static final class WeakPool {
        private static final Map<MyString, WeakReference<MyString>> POOL = new WeakHashMap<>();

        static MyString intern(MyString candidate) {
            WeakReference<MyString> holder = POOL.get(candidate);
            if (holder != null) {
                MyString existing = holder.get();
                if (existing != null) {
                    return existing;
                }
            }
            POOL.put(candidate, new WeakReference<>(candidate));
            return candidate;
        }
        static int size() {
            return POOL.size();
        }
    }

    private static final int KEYS = 200_000;

    private static long usedHeapAfterGc() {
        for (int i = 0; i < 3; i++) {
            System.gc();
            try {
                Thread.sleep(80);
            } catch (InterruptedException e) {
                Thread.currentThread().interrupt();
            }
        }
        Runtime runtime = Runtime.getRuntime();
        return runtime.totalMemory() - runtime.freeMemory();
    }

    public static void main(String[] args) {
        String which = args[0];
        System.out.println("pool under test: " + which);
        long empty = usedHeapAfterGc();

        List<MyString> idempotencyKeys = new ArrayList<>(KEYS);
        for (int i = 0; i < KEYS; i++) {
            MyString key = MyString.of(UUID.randomUUID().toString());
            idempotencyKeys.add(key);
            switch (which) {
                case "strong" -> StrongPool.intern(key);
                case "weak-self-valued" -> WeakPoolSelfValued.intern(key);
                case "weak" -> WeakPool.intern(key);
                default -> throw new IllegalArgumentException(which);
            }
        }
        System.out.println("pool size, 200,000 keys reachable : " + size(which));

        ReferenceQueue<MyString> clearedKeys = new ReferenceQueue<>();
        WeakReference<MyString> sampleKey =
                new WeakReference<>(idempotencyKeys.get(0), clearedKeys);
        idempotencyKeys.clear();
        idempotencyKeys = null;

        long dropped = usedHeapAfterGc();
        System.out.println("retained above empty baseline     : " + ((dropped - empty) / 1024) + " KiB");
        System.out.println("pool size after the collector ran : " + size(which));
        System.out.println("sample key cleared, enqueued      : " + (sampleKey.get() == null)
                + ", " + (clearedKeys.poll() == sampleKey));
    }

    private static int size(String which) {
        return switch (which) {
            case "strong" -> StrongPool.size();
            case "weak-self-valued" -> WeakPoolSelfValued.size();
            case "weak" -> WeakPool.size();
            default -> throw new IllegalArgumentException(which);
        };
    }
}
```

Run as `java -Xmx512m -cp classes InternPoolDemo <pool>`, one JVM per pool so the three cannot
retain each other's keys:

```console
pool under test: strong
pool size, 200,000 keys reachable : 200000
retained above empty baseline     : 31425 KiB
pool size after the collector ran : 200000
sample key cleared, enqueued      : false, false
pool under test: weak-self-valued
pool size, 200,000 keys reachable : 200000
retained above empty baseline     : 32988 KiB
pool size after the collector ran : 200000
sample key cleared, enqueued      : false, false
pool under test: weak
pool size, 200,000 keys reachable : 200000
retained above empty baseline     : 17413 KiB
pool size after the collector ran : 0
sample key cleared, enqueued      : true, true
```

Read the three runs against each other. The strong pool retains **31,425 KiB above baseline with
200,000 entries still in the map after the collector ran**: the caller dropped every reference and
nothing was freed, because a `static final HashMap` is reachable from its class's static field for
the lifetime of the defining class loader, and a class loaded by the application loader in a
normal deployment is never unloaded. The self-valued weak pool retains **32,988 KiB and 200,000
entries** — indistinguishable from the strong pool, which is why it is here. The correctly-weak
pool reports **0 entries** and, decisively, `sample key cleared, enqueued : true, true`.

Three honesty notes on that measurement:

- `System.gc()` is a **hint**, not a guarantee (`Runtime.gc` javadoc: "makes a best effort").
  The heap deltas alone prove nothing. The `ReferenceQueue` poll is the load-bearing evidence: a
  `WeakReference` is enqueued only after the collector has determined its referent is weakly
  reachable and cleared it. That happened, for that specific key.
- `totalMemory() - freeMemory()` is a coarse instrument — it includes collector state and whatever
  the young generation has not given back. The weak run's residual 17,413 KiB is mostly the
  `WeakHashMap`'s own 262,144-slot table array plus stale `Entry` objects not yet expunged:
  `size()` calls `expungeStaleEntries()`, and `size()` ran *after* that measurement, which is
  exactly why it then reported 0.
- Absolute figures are this machine and this heap size; the residual varies a few KiB run to run.
  The finding is the relative result: 200,000 surviving entries versus 0.

**Pitfall:** an unbounded intern pool is a memory leak with good intentions. Interning is correct
for a small bounded key set (the few dozen `AA-` and `AO-` status names) and wrong for per-request
values (idempotency keys, `RoundId`, session tokens). In review it does not look like a leak; it
looks like a cache.

> **An intern pool is a bounded-cardinality optimisation; applied to unbounded input it is
> retention with extra steps.**

`../strings/03b-internals-stringtable-and-interning.md` owns the real `StringTable` — a native
open-hash table of weak `oop` handles, sized by `-XX:StringTableSize`, swept by the collector,
which is not a `HashMap` and is unreachable from Java except through native `String.intern()`.

---

## 4.1.6 Diff vs `java.lang.String`

Verified against `java.base/java/lang/String.java` and `StringLatin1.java` extracted from
`$JAVA_HOME/lib/src.zip` on JDK 21.0.7.

| Dimension | `MyString` | `java.lang.String` (JDK 21) | Why the JDK bothers |
|---|---|---|---|
| Payload | `private final char[] value`, 2 B/char always | `@Stable private final byte[] value` + `private final byte coder`, 1 B/char for Latin-1 | JEP 254: most heap strings are Latin-1, so halving them is among the largest heap wins available without an API change |
| `@Stable` on the payload | absent | present on `value` | tells the JIT the field's non-default value never changes, so `value[i]` on a constant `String` folds to a constant at compile time; no Java-level construct can express this |
| Intrinsics, **verified present** | none | `@IntrinsicCandidate` on `String(String)`, and in `StringLatin1` on `equals(byte[],byte[])`, `compareTo`, `compareToUTF16`, `indexOfChar`, both `indexOf` overloads, both `inflate` overloads | SIMD-width comparison and search; the Java bodies are byte-at-a-time reference semantics the JIT replaces wholesale |
| Intrinsics, **verified absent** | none | `String.hashCode`, `String.equals`, `String.compareTo` carry **no** `@IntrinsicCandidate` themselves; `hashCode` delegates to `StringLatin1.hashCode`, which routes to `ArraysSupport.vectorizedHashCode(value, 0, len, 0, T_BOOLEAN)`, and `equals` delegates to the annotated `StringLatin1.equals` | the annotation sits on the leaf array routine, not the public method — an interview miss in both directions |
| `equals` fast path | `==`, `instanceof`, `Arrays.equals` | `==`, `instanceof`, `!COMPACT_STRINGS \|\| this.coder == aString.coder`, then `StringLatin1.equals` | the coder check rejects a Latin-1/UTF-16 pair in one comparison without touching the payload — differing coders can never be equal |
| Interning | `HashMap`-backed pool you write; leaks without weak keys | native `String.intern()` over the VM's `StringTable`: open-hash table of weak `oop` handles, `-XX:StringTableSize` buckets, swept by the collector | interning must survive class unloading and cooperate with GC; a Java-level `HashMap` does neither |
| Constant-pool integration | none | `CONSTANT_String_info` entries resolve through the `StringTable`, so every literal is interned before your code runs | literal identity (`"AA-801" == "AA-801"` is `true`) is a language-visible consequence |
| `Constable` / `ConstantDesc` | not implemented | `String implements Serializable, Comparable<String>, CharSequence, Constable, ConstantDesc`; `describeConstable()` returns `Optional.of(this)`, `resolveConstantDesc` returns `this` | a `String` is its own nominal descriptor, so `condy`, `MethodHandle` bootstraps and `invokedynamic` sites carry one as a live constant with no encode/decode step |
| Serialization | not `Serializable` | `serialVersionUID = -6849794470754667710L` from JDK 1.0.2; `serialPersistentFields` is an **empty** `ObjectStreamField[]`, because the protocol special-cases strings as `TC_STRING`/`TC_LONGSTRING` with a modified-UTF-8 body | the payload changed shape entirely in Java 9 and the serial form did not, because the serial form never referenced the fields |
| What `Serializable` would cost `MyString` | — | — | the default form would write the `char[]` element by element with no `TC_STRING` compaction, freeze `value`/`coder`/`hash` as a public contract, and — decisively — deserialization bypasses the constructor, so `readObject` would have to re-clone `value` by hand or a crafted stream hands you a `MyString` whose array the attacker still holds |
| Null policy | `MyString(null)` throws `NullPointerException` from `null.clone()`; `equals(null)` is `false` via the failing `instanceof`; `compareTo(null)` throws `NPE` on `other.value` | same shape: constructors throw `NPE`, `equals(null)` is `false`, `compareTo(null)` throws `NPE` per `Comparable` | `equals` must tolerate null and return false; `compareTo` must reject it — the asymmetry is contractual |
| Thread safety | safe: `value`/`coder` final, `hash`/`hashIsZero` a benign idempotent race | identical, with the reasoning written out in a comment above `hashCode` | a lock or `volatile` on the hash would cost every reader to save a rare recomputation |
| Allocation tricks | none: `toString()` copies the array every call, `subSequence` always copies | `String(String)` shares the callee's `value` array outright and is an intrinsic candidate; `substring(0, length())` returns `this`; `concat("")` returns `this`; `StringUTF16.compress` narrows and scans in one pass | the cheap identity returns are legal *only because* the type is immutable — immutability buys the whole optimisation family |
| API surface | 12 members | 100 public constructors and methods under 55 distinct names (counted by `grep -cE '^    public [a-zA-Z<].*\(' String.java`), including `format`, `join`, `split`, `strip`, `repeat`, `lines`, `chars`, `codePoints`, `formatted`, `translateEscapes`, `stripIndent`, the `regionMatches`/`indexOf`/`lastIndexOf`/`replace` families and the `Charset` constructors | `String` is the JDK's most-used type; every convenience omitted becomes a utility class in every codebase |
| Edge cases handled | empty string (hash 0 via `hashIsZero`), zero-hash content, `start == end`, high code units in `computeCoder` | all of those plus surrogate pairs, `codePointAt`/`codePointCount` over supplementary planes, locale-sensitive case mapping, `isBlank` over Unicode whitespace, malformed-input replacement in the `Charset` constructors | correctness at the boundary is most of what a 30-year-old library is |

`MyString` is **not** equivalent to `java.lang.String`. No working compact-strings split, no
`@Stable`, no intrinsics, no `StringTable`, no constant-pool integration, no serial form, and 12
members against 100. What it does have is the same immutability argument, the same hash recurrence
bit for bit, and the same benign-race cache — which is the part interviews ask about.

---

## Pitfalls

### Believing an intern pool over a strong `HashMap` is what `String.intern()` does

**Wrong**

```java
private static final Map<MyString, MyString> POOL = new HashMap<>();
```

```console
retained above empty baseline     : 31425 KiB
pool size after the collector ran : 200000
sample key cleared, enqueued      : false, false
```

`WeakHashMap<MyString, MyString>` does not fix it either — the value strongly references its own
key, so the entry resurrects it: `200000` entries, `false, false`.

**Right**

```java
private static final Map<MyString, WeakReference<MyString>> POOL = new WeakHashMap<>();
```

```console
pool size after the collector ran : 0
sample key cleared, enqueued      : true, true
```

And even that is not `String.intern()`: the real pool is the VM's native `StringTable`, weak `oop`
handles sized by `-XX:StringTableSize`, swept by the collector and wired into constant-pool
resolution so every literal is interned before your code runs.

**Why people believe it:** "the string pool" is universally taught as a map from string to string,
which is a fair mental model and a terrible implementation model. Nothing in the phrase hints at
weak references, and `WeakHashMap` looks like the whole answer until you notice which side of the
entry is weak.

### Believing `intern()` is free because it returns a reference

**Wrong**

```java
// "intern() just hands back a pointer, so canonicalise on the hot path"
public String canonicalStatusName(String rawFromWire) {
    return rawFromWire.intern();
}
```

Called once per stake reservation, that is 2.8M interns a day and 1,200/sec at peak. `intern()` is
a native call into the VM's `StringTable`: it hashes the string, takes the table lock or its
lock-free equivalent, probes the open-hash table, and may install a new weak handle. Timed against
1,024 distinct non-interned copies of `AA-610 DOCUMENTS_UPLOADED` whose content is already in the
table, 20,000,000 calls after a 2,000,000-call warm-up:

```java
public final class InternCostDemo {

    private static final int COPIES = 1024;
    private static final int WARMUP = 2_000_000;
    private static final int ITERATIONS = 20_000_000;

    static volatile Object sink;

    private static final String CANONICAL = "AA-610 DOCUMENTS_UPLOADED".intern();

    public static void main(String[] args) {
        String[] statusNames = new String[COPIES];
        for (int i = 0; i < COPIES; i++) {
            statusNames[i] = new String("AA-610 DOCUMENTS_UPLOADED".toCharArray());
        }
        System.out.println("copy is a distinct object, equal content: "
                + (statusNames[0] != CANONICAL) + ", " + statusNames[0].equals(CANONICAL));
        System.out.println("intern() returns the canonical instance  : "
                + (statusNames[0].intern() == CANONICAL));

        for (int i = 0; i < WARMUP; i++) {
            sink = statusNames[i & (COPIES - 1)].intern();
            sink = statusNames[i & (COPIES - 1)];
            sink = CANONICAL;
        }

        long t0 = System.nanoTime();
        for (int i = 0; i < ITERATIONS; i++) {
            sink = statusNames[i & (COPIES - 1)].intern();
        }
        long internNanos = System.nanoTime() - t0;

        t0 = System.nanoTime();
        for (int i = 0; i < ITERATIONS; i++) {
            sink = statusNames[i & (COPIES - 1)];
        }
        long arrayReadNanos = System.nanoTime() - t0;

        t0 = System.nanoTime();
        for (int i = 0; i < ITERATIONS; i++) {
            sink = CANONICAL;
        }
        long fieldReadNanos = System.nanoTime() - t0;

        System.out.printf("intern() per call                       : %.2f ns%n",
                internNanos / (double) ITERATIONS);
        System.out.printf("array read per call                     : %.2f ns%n",
                arrayReadNanos / (double) ITERATIONS);
        System.out.printf("static final field read per call        : %.2f ns%n",
                fieldReadNanos / (double) ITERATIONS);
        System.out.printf("intern() / field read                   : %.1fx%n",
                internNanos / (double) fieldReadNanos);
    }
}
```

```console
copy is a distinct object, equal content: true, true
intern() returns the canonical instance  : true
intern() per call                       : 65.42 ns
array read per call                     : 0.60 ns
static final field read per call        : 0.45 ns
intern() / field read                   : 146.3x
```

**Right**

```java
// resolve once, at the boundary, into a bounded lookup
private static final Map<String, String> CANONICAL_STATUS_NAMES =
        Stream.of("AA-500 SCREENING_IN_PROGRESS", "AA-610 DOCUMENTS_UPLOADED",
                  "AA-611 DOCUMENTS_VERIFIED", "AA-801 ACTIVATED")
              .collect(Collectors.toUnmodifiableMap(name -> name, name -> name));

public String canonicalStatusName(String rawFromWire) {
    String canonical = CANONICAL_STATUS_NAMES.get(rawFromWire);
    return canonical != null ? canonical : rawFromWire;
}
```

A bounded immutable map, one hash and one probe in Java, no VM lock, no weak-handle install, and
no risk of pinning an unbounded key set into a table the collector has to sweep every cycle.

Read the numbers honestly. 65.42 ns is the figure that matters and it sits inside the
61.81–65.33 ns band `../cost-model/02-master-cost-table.md` measured for `String.intern()` on this
machine. The two baselines at 0.60 ns and 0.45 ns are **below** a real field read's ~3 ns because
those loops are trivially hoistable — the JIT has almost nothing left to do once the `volatile`
store is the only side effect. They establish only the order of magnitude of the gap, not a
calibrated ratio. This is not JMH: no forking, no `Blackhole`, no dead-code guard beyond the
`volatile` sink, and whatever compilation state C2 happened to reach.

**Why people believe it:** the method returns a `String` reference and the javadoc describes it in
terms of a "pool of strings", which sounds like a map lookup you could do yourself. Nothing in the
signature says "native, VM-global table, participates in GC".

### Believing `MyString` can stand in where `java.lang.String` is expected

**Wrong**

```java
Map<CharSequence, String> statusDescriptions = new HashMap<>();
statusDescriptions.put("AA-610 DOCUMENTS_UPLOADED", "documents received, awaiting vendor");
// hash matches String's bit for bit, so the lookup must work
String description = statusDescriptions.get(MyString.of("AA-610 DOCUMENTS_UPLOADED"));
```

```console
map keyed on String, get(MyString)  : null
map keyed on String, get(String)    : documents received, awaiting vendor
hashes agree                        : true
MyString.equals(String)             : false
String.equals(MyString)             : false
Serializable.class.isInstance     : false
writeObject(MyString)               : NotSerializableException: MyString
converted at the boundary, get      : documents received, awaiting vendor
```

The hashes agree — both use the javadoc-specified `h = 31*h + c` recurrence — so the lookup finds
the right bucket and then fails `equals` in both directions. Matching hashes route you to the
entry; only `equals` retrieves it. The serialization line is the harder wall: `MyString` does not
implement `Serializable`, so any framework that writes it to a stream, a session store or a cache
fails at runtime. The type is `final`, so `lookupKey instanceof Serializable` is not even a false
answer — `javac` rejects it outright:

```console
DropInDemo.java:24: error: incompatible types: MyString cannot be converted to Serializable
                + (lookupKey instanceof Serializable));
                   ^
1 error
```

**Right**

```java
// convert at the boundary; MyString is an internal representation, not an interchange type
Map<CharSequence, String> statusDescriptions = new HashMap<>();
statusDescriptions.put(MyString.of("AA-610 DOCUMENTS_UPLOADED").toString(),
        "documents received, awaiting vendor");
String description = statusDescriptions.get("AA-610 DOCUMENTS_UPLOADED");
```

```console
converted at the boundary, get      : documents received, awaiting vendor
```

Either key everything on `MyString` or key everything on `String`, and cross the boundary with an
explicit `toString()`. Do not mix them in one map and rely on hash agreement.

**Why people believe it:** `MyString implements CharSequence`, its hash is bit-identical to
`String`'s, and `Map<CharSequence, V>.get(Object)` accepts any object, so the code compiles and
the mental model ("same characters, same hash, same key") is coherent right up to the
`equals` call. `CharSequence` deliberately leaves `equals` unspecified precisely so that no one is
entitled to that model.

---

## Cheat sheet

| Fact | Value |
|---|---|
| Intern pool that works | `WeakHashMap<K, WeakReference<K>>` — weak key **and** weak value |
| Intern pool that leaks | `HashMap<K,K>`, and `WeakHashMap<K,K>` equally |
| Why `WeakHashMap<K,K>` leaks | values are held strongly; the value *is* the key, so the entry resurrects it |
| Measured, 200,000 UUID keys dropped | strong 200000 entries / 31,425 KiB; self-valued weak 200000 / 32,988 KiB; weak 0 / 17,413 KiB |
| The load-bearing evidence | `ReferenceQueue` enqueue, not the heap delta — `System.gc()` is only a hint |
| `String.intern()` measured | 65.42 ns/call on this machine (cost table band 61.81–65.33 ns); not JMH |
| Real string pool | native VM `StringTable`, open hash, weak `oop` handles, `-XX:StringTableSize`, GC-swept |
| Literals | interned by `CONSTANT_String_info` resolution before your code runs — hence `"AA-801" == "AA-801"` |
| `@Stable` on `String.value` | present; lets the JIT constant-fold `value[i]` on a constant `String`. No Java equivalent |
| Intrinsics that exist | `String(String)`; `StringLatin1.equals`, `compareTo`, `compareToUTF16`, `indexOfChar`, both `indexOf`, both `inflate` |
| Intrinsics that do **not** exist | `String.hashCode`, `String.equals`, `String.compareTo` themselves |
| `String.equals` order | `==`, `instanceof`, coder check, `StringLatin1.equals` |
| `String.hashCode` route | `StringLatin1.hashCode` → `ArraysSupport.vectorizedHashCode(value, 0, len, 0, T_BOOLEAN)` |
| `String` serial form | `serialVersionUID = -6849794470754667710L`, **empty** `serialPersistentFields`, `TC_STRING`/`TC_LONGSTRING` |
| Why the serial form survived JEP 254 | it never referenced the fields; the protocol special-cases strings |
| `String` interfaces | `Serializable`, `Comparable<String>`, `CharSequence`, `Constable`, `ConstantDesc` |
| `String` identity returns | `substring(0, length())` → `this`; `concat("")` → `this`; legal only because immutable |
| API surface | `MyString` 12 members vs `String` 100 methods/constructors under 55 names |
| Drop-in reality | `MyString` is not `Serializable`, never `equals` a `String`, and `String.equals(MyString)` is false |

---

## Self-test

**Q1.** A `static final HashMap<MyString, MyString>` intern pool is fed one idempotency key per
stake reservation. What happens, and what is the measured evidence?

<details><summary>Answer</summary>

Every key is retained for the life of the defining class loader, which in a normal deployment is
forever. Measured over 200,000 UUID-shaped keys: after the caller dropped every reference and the
collector ran three times, the pool still reported 200,000 entries and 31,425 KiB above baseline,
and a `WeakReference` to a sample key was neither cleared nor enqueued. Interning is right for a
bounded key set — the few dozen `AA-` and `AO-` status names — and is retention with extra steps
for per-request values. The failure is invisible in review because it looks like a cache.

</details>

**Q2.** `WeakHashMap<MyString, MyString>` fixes that leak. True?

<details><summary>Answer</summary>

No. `WeakHashMap` holds its keys weakly but its **values** strongly, so an entry whose value *is*
its key keeps a strong path to that key alive through the entry and it is never collected.
Measured, it is indistinguishable from the plain `HashMap`: 200,000 surviving entries, 32,988 KiB
retained, sample key not cleared. The working shape is
`WeakHashMap<MyString, WeakReference<MyString>>` — weak on both sides — which measured 0 surviving
entries with the sample key cleared and enqueued on a `ReferenceQueue`. The enqueue is the proof;
`System.gc()` is only a hint, so heap numbers alone would establish nothing.

</details>

**Q3.** Is `String.hashCode` an intrinsic in JDK 21?

<details><summary>Answer</summary>

Not directly. `String.hashCode` carries no `@IntrinsicCandidate`; it delegates to
`StringLatin1.hashCode` or `StringUTF16.hashCode`, and `StringLatin1.hashCode` special-cases
lengths 0 and 1 then calls
`ArraysSupport.vectorizedHashCode(value, 0, value.length, 0, T_BOOLEAN)`. The annotation in this
area sits on the leaf array routines: in `StringLatin1` on `equals(byte[],byte[])`, `compareTo`,
`compareToUTF16`, `indexOfChar`, both `indexOf` overloads and both `inflate` overloads; in `String`
itself only on the copy constructor `String(String)`. `String.equals` and `String.compareTo` are
likewise not annotated themselves — they delegate to routines that are. Both the "everything on
`String` is an intrinsic" and the "nothing is" answers are wrong.

</details>

**Q4.** Why can a Java-level `HashMap` never be `String.intern()`, no matter how carefully you
write it?

<details><summary>Answer</summary>

Three reasons, in increasing order of finality. First, GC cooperation: the VM's `StringTable` holds
weak `oop` handles the collector sweeps every cycle, so an unreferenced interned string leaves the
table without any Java code running. The best a Java map can do is `WeakHashMap` plus a
`WeakReference` value, which only expunges lazily when you happen to touch the map. Second, class
unloading and lifetime: a `static final` map lives as long as its defining class loader, whereas
the `StringTable` is VM-global and must outlive and survive the unloading of any loader that
interned into it. Third, and decisively, constant-pool integration: `CONSTANT_String_info` entries
resolve *through* the `StringTable` during class linking, so every literal in every loaded class is
already interned before a line of your code executes. That is what makes
`"AA-801" == "AA-801"` true, and no Java-level map can put itself in the resolution path.

</details>

**Q5.** `String`'s payload changed from `char[]` to `byte[]` in Java 9, yet its
`serialVersionUID` never changed. How is that possible, and what would `Serializable` cost
`MyString`?

<details><summary>Answer</summary>

Because `String`'s serial form never referenced its fields. `serialPersistentFields` is an
**empty** `ObjectStreamField[]`, and the serialization protocol special-cases strings entirely:
they go on the wire as `TC_STRING` or `TC_LONGSTRING` with a modified-UTF-8 body, not as a field
dump. So JEP 254 could replace the payload wholesale without touching the
`serialVersionUID = -6849794470754667710L` that has been there since JDK 1.0.2. `MyString` gets
none of that. The default serial form would write the `char[]` element by element with no
compaction, and it would freeze `value`, `coder`, `hash` and `hashIsZero` as a public compatibility
contract. The security problem is the real one: deserialization bypasses the constructor, so the
defensive `source.clone()` never runs. Without a hand-written `readObject` that re-clones `value`,
a crafted stream hands you a `MyString` whose backing array the stream's author still holds — the
exact mutation the constructor exists to prevent.

</details>

**Q6.** What does `@Stable` on `String.value` buy, and why can you not write the equivalent in
`MyString`?

<details><summary>Answer</summary>

`@Stable` (a `jdk.internal.vm.annotation` marker, not a language feature) tells the JIT that once
the field holds a non-default value it will never change again — a stronger promise than `final`,
because it extends to the *elements* of an array the field points at. With it, `value[i]` read from
a `String` the JIT knows to be a constant folds to a compile-time constant, which is what lets
whole `String` operations on literals collapse to nothing. `MyString` cannot express it: the
annotation is internal to `java.base` and its guarantee is unchecked, so the JIT will only honour
it for code it trusts. `private final char[] value` gets you the final-field freeze at the end of
the constructor and nothing about the array's contents; the JIT must reload every element on every
access because, as far as it can prove, some other code could write into that array.

</details>

**Q7.** Both `MyString` and `String` hash `AA-610 DOCUMENTS_UPLOADED` to the same `int`. Does a
`HashMap` keyed on `String` therefore find a `MyString` lookup key?

<details><summary>Answer</summary>

No, and this is the sharpest way to see that hashing and equality are two separate contracts.
Matching hashes get the lookup to the right bucket; `equals` is what retrieves the entry, and
`MyString.equals(String)` is `false` (its `instanceof MyString` pattern fails) while
`String.equals(MyString)` is also `false` (its `instanceof String` fails). Measured:
`get(MyString.of("AA-610 DOCUMENTS_UPLOADED"))` on a map holding that `String` key returns `null`
while `hashes agree : true`. Both directions returning `false` is at least *symmetric* and
therefore contract-legal; a "helpful" `MyString.equals` that accepted `CharSequence` content would
be asymmetric and would corrupt the collection. Key everything on one type and cross the boundary
with an explicit `toString()`.

</details>

---

## Open questions

- none

---

**Leaves covered:** 4.1.4, 4.1.6 (2 leaves)
**Leaves deferred:** none
**Diagrams included:** none
**Target version:** Java 21 LTS
**Lines:** 624
