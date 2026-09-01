# 03 Java Core — Enum-shaped builds: the `values()` cache and the diff against the generated enum — BUILD IT (§4.5.6, §4.5.7)

**Target version: Java 21 LTS.** | **Part 4 of 5** | [Index](../00-index.md)
Previous: [The enum state machine and the enum singleton](03a-enum-state-machine-and-singleton.md) · Next: [Exception builds — a domain hierarchy and a stackless exception](03c-exception-hierarchy-and-stackless.md)

---

## 4.5.6 A `values()` caching helper, and the allocation it saves `[BUILD]` `[NUM]` `[BYTECODE]` `[PROVE]`

`BonusState.values()` looks like a field read. It is a **memory allocation**: every call
manufactures a new five-element array on the heap and copies five references into it. Call it once
per stake reservation and QuizStakes allocates 2.8M arrays a day to ask a question whose answer
never changes.

The reason is ownership. Java arrays are mutable with no read-only mode. The constants live in one
`private static final` array called `$VALUES`, and if `values()` returned that reference, any
caller in the process could write `$VALUES[4] = null` and corrupt the enum for every other caller
in the JVM. So `values()` hands out a `clone()` instead, on every single call.

### The mechanism, then the bytecode `[BYTECODE]`

`values()` is neither a method you wrote nor a method on `java.lang.Enum`. The compiler generates
it into each enum class, along with `valueOf(String)`, a private synthetic `$values()` factory, the
`$VALUES` field, and a `<clinit>` constructing every constant in declaration order.
`../enums/03-internals-enums.md` and `../enums/03a-internals-enum-members.md` own that desugaring
in full. What matters here is one line: `values()`' body is `return (BonusState[]) $VALUES.clone();`.

The enum, exactly as file 11 declared it:

```java
public enum BonusState {
    GRANTED,
    ACTIVE,
    CONSUMED,
    EXPIRED,
    CLAWED_BACK
}
```

```bash
javac BonusState.java
javap -c -p BonusState.class
```

```text
public static BonusState[] values();
  Code:
     0: getstatic     #19                 // Field $VALUES:[LBonusState;
     3: invokevirtual #23                 // Method "[LBonusState;".clone:()Ljava/lang/Object;
     6: checkcast     #24                 // class "[LBonusState;"
     9: areturn
```

Four instructions, read one at a time:

| Offset | Instruction | What it does |
|---|---|---|
| 0 | `getstatic $VALUES` | pushes the one shared array reference — this part *is* a field read |
| 3 | `invokevirtual clone()` | **allocates** a new `BonusState[5]` and copies five references into it |
| 6 | `checkcast [LBonusState;` | `Object[] clone()` is typed `Object`, so the cast narrows it back |
| 9 | `areturn` | returns the copy |

Offset 3 is the whole cost. And the field it clones:

```text
private static final BonusState[] $VALUES;
  descriptor: [LBonusState;
  flags: (0x101a) ACC_PRIVATE, ACC_STATIC, ACC_FINAL, ACC_SYNTHETIC
```

`ACC_SYNTHETIC` means "not in the source": invisible to source code, skipped by tools that filter
synthetics. `ACC_PRIVATE` means no other class can reach it even with the right type. Note the
asymmetry — `$VALUES` is flagged synthetic, `values()` is **not**: its flags are
`(0x0009) ACC_PUBLIC, ACC_STATIC`, because the JLS makes it an *implicitly declared* member of the
enum's public API rather than scaffolding. That is why `Class.getMethod("values")` finds it.

> **`values()` is a public static method the compiler writes into every enum whose entire body is
> a defensive `clone()` of the one private synthetic `$VALUES` array — so it is an allocation site,
> not a field read.**

### The helper

Cache the array once, and never let it out. The safe accessor is `List.of(VALUES)`: a `List.of`
list has no write path at all — no `set`, no `add`, no backing array a caller can reach.

```java
import java.util.List;

/**
 * The values() caching helper for BonusState.
 * Holds one array for the lifetime of the class and never hands it out.
 */
public final class BonusStates {

    /** The single defensive copy. Never escapes this class. */
    private static final BonusState[] VALUES = BonusState.values();

    /** The shipping accessor: a List view that cannot be written through. */
    public static final List<BonusState> ALL = List.of(VALUES);

    private BonusStates() {
    }

    /** Allocation-free indexed read, for ordinal-keyed hot paths. */
    public static BonusState byOrdinal(int ordinal) {
        return VALUES[ordinal];
    }

    public static int count() {
        return VALUES.length;
    }

    /**
     * The alternative accessor: a fresh copy per call. Identical cost to
     * BonusState.values() itself, so it buys nothing but symmetry.
     */
    public static BonusState[] copy() {
        return VALUES.clone();
    }

    /**
     * The trap, exposed deliberately so the hazard demo can exercise it.
     * Shipping this re-creates exactly what values()' clone prevents.
     */
    static BonusState[] leakyValues() {
        return VALUES;
    }
}
```

**Ship `ALL`, not `copy()`.** `copy()` allocates exactly what `values()` allocates — it removes
the hazard and keeps the cost. `ALL` removes both: `List.of` copies into its own private storage
once at class-init, so it is immune even to later damage through `VALUES`, and iterating it
allocates nothing. Use `byOrdinal` only where an ordinal is already in hand, and never as an excuse
to persist one (see the reorder proof in §4.5.7).

### The hazard, demonstrated

`leakyValues()` is what a careless cache ships. Here is what it costs.

```java
public final class ValuesHazardDemo {

    public static void main(String[] args) {
        System.out.println("--- BonusState.values() clones, so damage does not stick ---");
        BonusState[] first = BonusState.values();
        System.out.println("first  identityHashCode = " + System.identityHashCode(first));
        BonusState[] second = BonusState.values();
        System.out.println("second identityHashCode = " + System.identityHashCode(second));
        System.out.println("first == second ? " + (first == second));
        first[4] = null;
        System.out.println("after nulling first[4], BonusState.values()[4] = " + BonusState.values()[4]);

        System.out.println();
        System.out.println("--- the cached array, handed out, does stick ---");
        BonusState[] leaked = BonusStates.leakyValues();
        System.out.println("leaked identityHashCode  = " + System.identityHashCode(leaked));
        System.out.println("leaked again identityHash = " + System.identityHashCode(BonusStates.leakyValues()));
        leaked[4] = null;
        leaked[0] = BonusState.CLAWED_BACK;
        System.out.println("a caller nulled slot 4 and overwrote slot 0");
        BonusState[] nextReader = BonusStates.leakyValues();
        System.out.println("next reader sees slot 4 = " + nextReader[4]);
        System.out.println("next reader sees slot 0 = " + nextReader[0]);
        try {
            System.out.println("clawback narration = " + BonusStateNarrator.narrate(nextReader[4]));
        } catch (NullPointerException e) {
            System.out.println("narrating slot 4 threw " + e.getClass().getName());
        }

        System.out.println();
        System.out.println("--- the List view refuses the same write ---");
        try {
            BonusStates.ALL.set(4, null);
        } catch (UnsupportedOperationException e) {
            System.out.println("BonusStates.ALL.set(4, null) threw " + e.getClass().getName());
        }
        System.out.println("BonusStates.ALL = " + BonusStates.ALL);
        System.out.println("BonusStates.byOrdinal(4) = " + BonusStates.byOrdinal(4));
    }
}
```

Real output, JDK 21.0.7:

```console
--- BonusState.values() clones, so damage does not stick ---
first  identityHashCode = 366712642
second identityHashCode = 692404036
first == second ? false
after nulling first[4], BonusState.values()[4] = CLAWED_BACK

--- the cached array, handed out, does stick ---
leaked identityHashCode  = 1627674070
leaked again identityHash = 1627674070
a caller nulled slot 4 and overwrote slot 0
next reader sees slot 4 = null
next reader sees slot 0 = CLAWED_BACK
narrating slot 4 threw java.lang.NullPointerException

--- the List view refuses the same write ---
BonusStates.ALL.set(4, null) threw java.lang.UnsupportedOperationException
BonusStates.ALL = [GRANTED, ACTIVE, CONSUMED, EXPIRED, CLAWED_BACK]
BonusStates.byOrdinal(4) = null
```

Two distinct identity hashes from two `values()` calls prove the clone without reading a single
instruction; one identity hash from two `leakyValues()` calls proves there is none.

**Insight:** the last line. `BonusStates.byOrdinal(4)` returns `null` — the class's *own*
supposedly-safe accessor is broken, because it and `leakyValues()` read the same array. One leaked
reference poisoned the cache JVM-wide, with no exception at the point of damage and a
`NullPointerException` somewhere unrelated later. `ALL` survived only because `List.of` took its
own copy at class-init, before the vandalism.

**Pitfall:** `private static final` on an array field protects the *reference*, not the
*contents*. `final` stops `VALUES = somethingElse`; nothing stops `VALUES[4] = null`. This is the
same trap `../immutability-and-design/02-immutability.md` covers for defensive copying in general.

### The measurement `[NUM]`

The house harness: `com.sun.management.ThreadMXBean.getThreadAllocatedBytes` deltas over a large
loop after a warm-up. `../cost-model/02-master-cost-table.md` owns the canonical harness — this is
the same shape, scoped to one question. **This is not JMH**: no forking, no `Blackhole`, no
dead-code guard beyond the `volatile` sink, and whatever JIT state happens to obtain. The
allocation counts are exact; the nanosecond figures are within-run comparisons only.

```java
import com.sun.management.ThreadMXBean;
import java.lang.management.ManagementFactory;

/**
 * Allocation accounting for BonusState.values() versus the cached List.
 * Not JMH: no forking, no Blackhole, no dead-code guard beyond the volatile sink.
 */
public final class ValuesAllocationHarness {

    private static final int WARMUP = 200_000;
    private static final int ITERATIONS = 2_800_000;

    /** volatile sink so the result cannot be folded away as dead. */
    private static volatile int sink;

    private static final ThreadMXBean BEAN =
            (ThreadMXBean) ManagementFactory.getThreadMXBean();

    private static long allocated() {
        return BEAN.getThreadAllocatedBytes(Thread.currentThread().threadId());
    }

    /** One stake reservation's worth of work: scan the states for the stakeable ones. */
    private static int scanWithValues() {
        int stakeable = 0;
        for (BonusState state : BonusState.values()) {
            if (state == BonusState.GRANTED || state == BonusState.ACTIVE) {
                stakeable++;
            }
        }
        return stakeable;
    }

    private static int scanWithCache() {
        int stakeable = 0;
        for (int i = 0; i < BonusStates.ALL.size(); i++) {
            BonusState state = BonusStates.ALL.get(i);
            if (state == BonusState.GRANTED || state == BonusState.ACTIVE) {
                stakeable++;
            }
        }
        return stakeable;
    }

    /** The escaping shape: the array outlives the call, so it must be heap-allocated. */
    private static BonusState[] escapingValues() {
        return BonusState.values();
    }

    public static void main(String[] args) {
        System.out.println("thread allocation counting supported: "
                + BEAN.isThreadAllocatedMemoryEnabled());

        for (int i = 0; i < WARMUP; i++) {
            sink += scanWithValues();
            sink += scanWithCache();
            sink += escapingValues().length;
        }

        long base = allocated();
        long clock = System.nanoTime();
        for (int i = 0; i < ITERATIONS; i++) {
            sink += scanWithValues();
        }
        long withValuesNanos = System.nanoTime() - clock;
        long withValues = allocated() - base;

        base = allocated();
        clock = System.nanoTime();
        for (int i = 0; i < ITERATIONS; i++) {
            sink += scanWithCache();
        }
        long withCacheNanos = System.nanoTime() - clock;
        long withCache = allocated() - base;

        base = allocated();
        clock = System.nanoTime();
        for (int i = 0; i < ITERATIONS; i++) {
            sink += escapingValues().length;
        }
        long escapingNanos = System.nanoTime() - clock;
        long escaping = allocated() - base;

        report("non-escaping values() loop", withValues, withValuesNanos);
        report("cached List loop          ", withCache, withCacheNanos);
        report("escaping values() return  ", escaping, escapingNanos);
        System.out.println("sink = " + sink);
    }

    private static void report(String label, long bytes, long nanos) {
        System.out.printf("%s : %,15d bytes, %6.2f bytes/iter, %5d ms, %6.2f ns/iter%n",
                label, bytes, (double) bytes / ITERATIONS,
                nanos / 1_000_000, (double) nanos / ITERATIONS);
    }
}
```

Oracle JDK 21.0.7 (build 21.0.7+8-LTS-245), macOS aarch64, compressed oops on:

```console
=== default JIT ===
thread allocation counting supported: true
non-escaping values() loop :     112,000,000 bytes,  40.00 bytes/iter,    22 ms,   8.07 ns/iter
cached List loop           :               0 bytes,   0.00 bytes/iter,     6 ms,   2.18 ns/iter
escaping values() return   :       3,276,760 bytes,   1.17 bytes/iter,     6 ms,   2.43 ns/iter
sink = 27000000

=== -XX:-DoEscapeAnalysis ===
thread allocation counting supported: true
non-escaping values() loop :     112,000,000 bytes,  40.00 bytes/iter,    26 ms,   9.31 ns/iter
cached List loop           :               0 bytes,   0.00 bytes/iter,     5 ms,   2.14 ns/iter
escaping values() return   :     112,000,000 bytes,  40.00 bytes/iter,    20 ms,   7.17 ns/iter
```

**The byte arithmetic, derived then confirmed.** A `BonusState[5]` under compressed oops is a
16-byte array header (8-byte mark word + 4-byte compressed klass pointer + 4-byte length) plus 5
element slots at 4 bytes each:

```text
16 + (5 x 4) = 36 bytes, aligned up to the 8-byte boundary = 40 bytes
```

The harness reports **40.00 bytes/iteration**, so the derivation is measured, not guessed. The
cached loop reports **0.00** exactly: `List.of(VALUES)` iterated by index allocates nothing, not
even an `Iterator`.

**Scaled to the domain.** QuizStakes takes 2.8M stake reservations a day. One `values()` call per
reservation:

```text
2,800,000 x 40 bytes = 112,000,000 bytes = 112 MB/day
```

The harness ran exactly 2,800,000 iterations, and its total is `112,000,000` bytes — the domain
arithmetic and the measurement are the same number, checked against each other rather than
asserted.

**Now the honest part.** 112 MB/day is not 112 MB of heap. Every array dies before the next
reservation starts, so this is pure young-generation churn: it inflates the eden allocation rate
and shortens the interval between young collections, while costing the copying collector almost
nothing per object because each one is already unreachable when the collector arrives. Heap
occupancy does not grow. The cache buys fewer young collections, not a smaller live set — and
against QuizStakes' ~19.8M ledger entries a day, 112 MB is noise. **Cache `values()` inside a
genuinely hot loop, not as a reflex.**

The two configurations disagree in the opposite direction to the usual story. The *escaping*
shape — `escapingValues().length` — is the one C2 optimised away under the default JIT: 1.17
bytes/iteration, a 97% reduction, because after inlining the only consumer is `arraylength`, a
compile-time constant, so the whole `clone()` is dead code and is deleted. Disable escape analysis
and it pays the full 40 bytes. The *non-escaping* scan loop, the shape escape analysis exists for,
paid the full 40.00 bytes/iteration in **both** configurations. Allocation elimination for
`values()` is therefore dead-code elimination of an unused clone rather than scalar replacement of
a used one — so **the cache saves most exactly where the array is actually read**, which is the
common case in real code.

**Unverified:** why C2 declined to scalar-replace the array in `scanWithValues()`, where the clone
is provably non-escaping and fully consumed inside the method. `-XX:+PrintEscapeAnalysis` on a
fastdebug build, or the C2 IR dump, would settle it. Guide 06 owns escape-analysis diagnostics.

### Version note — who does *not* call `values()`

| Construct | Calls `values()` per operation? | Evidence |
|---|---|---|
| `for (BonusState s : BonusState.values())` | yes, one 40-byte array per loop entry | harness above |
| `switch` over an enum | **no** per-dispatch call; one call in the synthetic `$SwitchMap` holder's `<clinit>`, once ever | `javap` of `BonusStateNarrator$1` in §4.5.7 |
| `EnumSet.of(GRANTED, ACTIVE)`, `new EnumMap<>(BonusState.class)` | no; both go to `SharedSecrets` → `Class.getEnumConstantsShared()`, which caches the array in a `Class` field and returns it **uncloned** | `EnumSet.getUniverse` line 408, `EnumMap` line 750, `Class.getEnumConstantsShared` line 4000 |
| `Enum.valueOf(Class, String)` | no; uses `Class.enumConstantDirectory()`, a cached name→constant `HashMap` | `Enum.valueOf`, JDK 21 source |
| `Class.getEnumConstants()` | yes — it is `getEnumConstantsShared().clone()`, so the public reflective form clones like `values()` does | `Class.java` line 3988 |

The punchline of the leaf: **the JDK already wrote your cache.**
`Class.getEnumConstantsShared()` is `BonusStates.VALUES` with JDK-internal visibility, used
uncloned by internal callers while the public `getEnumConstants()` clones. Behaviour is unchanged
across Java 8, 11, 17 and 21; only the `SharedSecrets`/`JavaLangAccess` plumbing has moved.

### Diff vs the real one — the cache helper

| Axis | `BonusStates` | `Class.getEnumConstantsShared()` |
|---|---|---|
| Edge cases | one enum type, hard-coded; `byOrdinal` throws `ArrayIndexOutOfBoundsException` on a stale ordinal | any `Class`; returns `null` for a non-enum instead of throwing, and swallows five reflective exception types for "enum-like" classes that fail the spec |
| Intrinsics | none | none; the win comes from `@Stable`-adjacent caching plus the JIT constant-folding a `static final` universe |
| Serialization | `BonusStates` is a non-instantiable utility class, never serialized | the cache is a `transient volatile` field, rebuilt per JVM |
| Null policy | `VALUES` can be nulled through `leakyValues()`; `ALL` cannot | the shared array is package-private and JDK callers are trusted not to write it — the same bargain, enforced by module boundaries rather than by copying |
| Thread safety | safe by final-field publication in `<clinit>`; the JVM guarantees class init happens once under a lock | `enumConstants` is `volatile`; a benign race can compute the array twice, and either result is correct |
| Allocation tricks | `List.of(VALUES)` for zero-allocation iteration; `byOrdinal` for zero-allocation lookup | zero-allocation for internal callers; `getEnumConstants()` still clones for external ones |
| Why the JDK bothers | — | `EnumSet` and `EnumMap` need the universe on nearly every construction; cloning a five-element array per `EnumSet.of` would make the ordinal-bitset design pointless |

---

## 4.5.7 Diff vs the compiler's generated enum — the §4.5 table `[SOURCE]` `[BYTECODE]` `[PROVE]`

Files 10 and 11 built the pre-Java-5 typesafe class with `readResolve` (4.5.1), the code-carrying
`ActivationStatus` (`AA-610` / `AA-611` / `AA-650` / `AA-801`) with its tolerant `fromCode` (4.5.2),
the per-constant-body strategy enum (4.5.3), the `BonusState` transition table (4.5.4), and the
enum singleton under four attacks (4.5.5). This is the section-wide accounting: what `enum` gives
you that none of the hand-rolled versions can. Capture 1 — `$VALUES` and the `values()` clone — is
in §4.5.6 above; two more follow, because three rows below are only believable with evidence.

### Capture 2 — `$SwitchMap`, the synthetic `int[]` in the *switching* class `[BYTECODE]`

```java
public final class BonusStateNarrator {

    /** Java 21 exhaustive switch expression, no default. */
    public static String narrate(BonusState state) {
        return switch (state) {
            case GRANTED -> "bonus granted, awaiting first deposit";
            case ACTIVE -> "bonus stakeable, drawn before cash";
            case CONSUMED -> "bonus fully staked";
            case EXPIRED -> "unspent bonus reversed to PROMOTIONAL_EXPENSE";
            case CLAWED_BACK -> "bonus withdrawn by compliance";
        };
    }
}
```

```text
public static java.lang.String narrate(BonusState);
  Code:
     0: getstatic     #7                  // Field BonusStateNarrator$1.$SwitchMap$BonusState:[I
     3: aload_0
     4: invokevirtual #13                 // Method BonusState.ordinal:()I
     7: iaload
     8: tableswitch   { // 1 to 5
                   1: 54
                   2: 59
                   3: 64
                   4: 69
                   5: 74
             default: 44
        }
    44: new           #31                 // class java/lang/MatchException
```

The dispatch loads the map, calls `ordinal()`, indexes the map, and `tableswitch`es on the
*mapped* integer — never on the ordinal itself. `default: 44` throws `MatchException`: the switch
is exhaustive with no source `default`, so 44 is reachable only if the enum changed after
compilation.

The map lives in a generated holder class, `BonusStateNarrator$1`:

```text
class BonusStateNarrator$1 {
  static final int[] $SwitchMap$BonusState;

  static {};
    Code:
       0: invokestatic  #1                  // Method BonusState.values:()[LBonusState;
       3: arraylength
       4: newarray       int
       6: putstatic     #7                  // Field $SwitchMap$BonusState:[I
       9: getstatic     #7                  // Field $SwitchMap$BonusState:[I
      12: getstatic     #13                 // Field BonusState.GRANTED:LBonusState;
      15: invokevirtual #17                 // Method BonusState.ordinal:()I
      18: iconst_1
      19: iastore
      20: goto          24
      23: astore_0
    Exception table:
       from    to  target type
           9    20    23   Class java/lang/NoSuchFieldError
```

Read it: size the `int[]` from `values().length` **at runtime**, then for each case label look up
that constant's *current* `ordinal()` and store the *compile-time* case index there. Each store is
individually wrapped in a `catch NoSuchFieldError` that discards the error, so a constant deleted
since compilation leaves a `0` in the slot, routing to `default` rather than crashing class init.
This is the only place in the enum machinery that calls `values()`, and it runs once ever.

`../enums/03b-internals-guarantees-and-switch.md` owns `$SwitchMap` in full.

### The proof that `$SwitchMap` earns its keep `[PROVE]`

Compile the enum and the narrator together, then recompile **only** the enum with `CLAWED_BACK`
moved to the front, and run the old narrator class against the new enum class.

```bash
javac -d v1 BonusState.java BonusStateNarrator.java ReorderProbe.java
java -cp v1 ReorderProbe
javac -d v2 v2/BonusState.java     # CLAWED_BACK declared first
java -cp v2:v1 ReorderProbe        # new enum, ORIGINAL narrator
```

```console
=== v1 as compiled ===
declared order = [GRANTED, ACTIVE, CONSUMED, EXPIRED, CLAWED_BACK]
ordinal 0  GRANTED      -> bonus granted, awaiting first deposit
ordinal 1  ACTIVE       -> bonus stakeable, drawn before cash
ordinal 2  CONSUMED     -> bonus fully staked
ordinal 3  EXPIRED      -> unspent bonus reversed to PROMOTIONAL_EXPENSE
ordinal 4  CLAWED_BACK  -> bonus withdrawn by compliance
a row persisted as ordinal 4 now reads back as CLAWED_BACK

=== enum recompiled, CLAWED_BACK first, narrator NOT recompiled ===
declared order = [CLAWED_BACK, GRANTED, ACTIVE, CONSUMED, EXPIRED]
ordinal 0  CLAWED_BACK  -> bonus withdrawn by compliance
ordinal 1  GRANTED      -> bonus granted, awaiting first deposit
ordinal 2  ACTIVE       -> bonus stakeable, drawn before cash
ordinal 3  CONSUMED     -> bonus fully staked
ordinal 4  EXPIRED      -> unspent bonus reversed to PROMOTIONAL_EXPENSE
a row persisted as ordinal 4 now reads back as EXPIRED
```

Every ordinal changed. Every narration stayed correct. A `tableswitch` on the raw ordinal would
have told a clawed-back bonus it was `GRANTED` and awaiting a first deposit. That is what
`$SwitchMap` buys, and the hand-rolled `int` constants of the pre-Java-5 pattern buy nothing of
the kind — an `int` case label is baked into the caller's class file and silently reinterpreted.

Now read the last line of each run. `$SwitchMap` fixed the *compiled switch* and did nothing for
the ordinal someone stored in a database column: ordinal 4 meant `CLAWED_BACK` on Monday and
`EXPIRED` on Tuesday, with no error anywhere. Persist the **name**, or a code you declared yourself
— which is why file 10's `ActivationStatus` carries `AA-610` rather than leaning on `ordinal()`.

### Capture 3 — constructor injection of name and ordinal `[BYTECODE]`

`ActivationStatus` from file 10 declares a one-argument constructor taking the persisted code.
The class file does not have one.

```text
private ActivationStatus(java.lang.String);
  descriptor: (Ljava/lang/String;ILjava/lang/String;)V
  flags: (0x0002) ACC_PRIVATE
  Code:
    stack=3, locals=4, args_size=4
       0: aload_0
       1: aload_1
       2: iload_2
       3: invokespecial #31                 // Method java/lang/Enum."<init>":(Ljava/lang/String;I)V
       6: aload_0
       7: aload_3
       8: putfield      #35                 // Field code:Ljava/lang/String;
      11: return
  MethodParameters:
    Name                           Flags
    <no name>                      synthetic
    <no name>                      synthetic
    <no name>
  Signature: #110                         // (Ljava/lang/String;)V
```

Field by field. The **declaration line** says one parameter — javap rendering the `Signature`
attribute, the source-level view. The **descriptor** says three: `(String, int, String)`, and
`args_size=4` counts `this` plus those three. The body loads `aload_1` (the injected name) and
`iload_2` (the injected ordinal), passes both to `Enum.<init>(String, int)`, then stores the code
from `aload_3`. `MethodParameters` flags the first two `synthetic` so tooling can hide them.
`ACC_PRIVATE` is nowhere in the source: the JLS makes an enum constructor implicitly private, which
is what makes `new ActivationStatus("AA-999")` a compile error and closes the constant set.

**Correction to a widely repeated claim.** You will read that you "cannot declare a constructor
matching the generated two-argument signature". Tested on 21.0.7, that is false, because javac
injects into *every* declared constructor, including the colliding one:

```text
private ClashingActivationStatus(java.lang.String);
  descriptor: (Ljava/lang/String;ILjava/lang/String;)V
private ClashingActivationStatus(java.lang.String, int, java.lang.String);
  descriptor: (Ljava/lang/String;ILjava/lang/String;ILjava/lang/String;)V
```

Both compiled, and the second's descriptor gained its own injected pair — so no source-level
signature can ever collide with a generated one. What injection *does* break is reflection, since
the descriptor is what `Class` sees:

```console
declared constructor: private ActivationStatus(java.lang.String,int,java.lang.String)
getDeclaredConstructor(String) threw NoSuchMethodException: ActivationStatus.<init>(java.lang.String)
getDeclaredConstructor(String,int,String) found: private ActivationStatus(java.lang.String,int,java.lang.String)
newInstance threw IllegalArgumentException: Cannot reflectively create enum objects
```

Asking for the constructor you wrote fails; asking for the injected shape succeeds, and
`Constructor.newInstance` refuses anyway from `acquireConstructorAccessor` — file 11 covers that
refusal as the reflection attack on the enum singleton (4.5.5). The `private` is not negotiable
either: an explicit `public` gives `error: modifier public not allowed here`.

### The §4.5 diff table

Every row verified against JDK 21.0.7 source (`src.zip`), the JLS, or `javap`/runtime output
captured above. "Hand-rolled" means the pre-Java-5 typesafe class of 4.5.1.

| Axis / feature | What the generated enum does | What hand-rolled loses |
|---|---|---|
| `$VALUES` | `private static final` + `ACC_SYNTHETIC` array; `values()` returns `$VALUES.clone()`, 40 bytes per call for 5 constants | you write and expose the array yourself; forget the clone and any caller can corrupt the universe process-wide (demonstrated above) |
| `$SwitchMap` | synthetic `static final int[]` in a generated holder inside the **switching** class, built from live `ordinal()` values at holder class-init, each store guarded by `catch NoSuchFieldError` | `int` case labels are constant-folded into the caller; reorder the constants and already-compiled callers silently mis-dispatch |
| `java.lang.Enum` superclass | `private final String name` and `private final int ordinal`, exposed by `final name()` / `final ordinal()`; also `final getDeclaringClass()` and a deprecated-for-removal `final finalize()` that does nothing | you re-declare name and ordinal, and nothing stops a subclass overriding the accessors |
| Constructor injection | every declared constructor gains two leading synthetic parameters `(String name, int ordinal)`, passed straight to `super`; the constructor is implicitly `private` and `MethodParameters` marks the pair synthetic | nothing injected; `private` must be remembered, and one non-private constructor reopens the set |
| `values()` / `valueOf(String)` | generated `public static`; `values()` is **not** `ACC_SYNTHETIC` (it is an implicitly declared API member); `Enum.valueOf` reads a cached name→constant map and throws `IllegalArgumentException: No enum constant BonusState.CLAWBACK_ORDERED` on an unknown name, `NullPointerException("Name is null")` on `null` | both written by hand; a hand-rolled lookup typically returns `null` for an unknown name, so the failure surfaces later and elsewhere |
| `equals` / `hashCode` | `public final boolean equals(Object other) { return this==other; }`; `public final int hashCode()` returns a lazily memoised `System.identityHashCode` cached in an `@Stable private int hash` field. Both `final`, so `==` and `equals` can never disagree | overridable; a well-meant value-based `equals` breaks the singleton contract and `EnumMap`'s assumptions |
| `compareTo` | `public final int compareTo(E o)`, `self.ordinal - other.ordinal`, with a `ClassCastException` if the declaring classes differ — natural order is declaration order, permanently | `Comparable` by hand, and nothing stops an inconsistent-with-`equals` ordering |
| `clone()` | `protected final Object clone() throws CloneNotSupportedException { throw new CloneNotSupportedException(); }` — `final` so it cannot be re-enabled, `protected` so it is not even callable from outside | `Cloneable` must be actively avoided; a subclass or a stray `implements Cloneable` manufactures a second instance |
| Serialization | serialized **by name**: the wire carries a `TC_ENUM` record whose payload is the constant name, `74 000b CLAWED_BACK` in the capture below. `Enum.readObject` and `readObjectNoData` both throw `InvalidObjectException("can't deserialize enum")`; the JLS forbids declaring `writeObject`, `readObject`, `readResolve` or `writeReplace` on an enum; no `serialVersionUID` needed | must hand-write `readResolve` to re-canonicalise, or deserialization produces a duplicate instance — 4.5.1's whole reason for existing |
| Null policy | a `switch` over a `null` enum throws `NullPointerException` at `invokevirtual ordinal()`; `EnumMap` rejects a `null` key with `NullPointerException`; `valueOf(null)` throws `NullPointerException` | whatever you wrote; `null` typically flows on and fails downstream |
| Thread safety | constants are constructed in `<clinit>` under the JVM's class-initialisation lock and published as `static final`, so every constant is safely published with no synchronisation at any call site | correct only if you get the static-initialiser and final-field publication right by hand |
| Allocation tricks | `EnumSet` → `RegularEnumSet` with a single `private long elements` bitset, set by `elements \|= (1L << ordinal())`, so a whole set of ≤64 constants is 8 bytes; `EnumMap` → a flat `Object[] vals` indexed by `ordinal()`, no hashing, no `Entry` objects; the universe cached uncloned in `Class.enumConstants` | `HashSet`/`HashMap` with hashing, `Node` allocation per entry, and no ordinal-indexed shortcut available |
| Per-constant bodies | a constant with a body compiles to an anonymous subclass, so `getClass()` is `BonusExpiryPolicy$1`, **not** the enum class — `getDeclaringClass()` is what you want; and this is why the enum class is `final` only when no constant has a body | ordinary subclassing, with no guarantee the set stays closed |
| Closed set | the compiler enforces it: no `extends`, no reachable constructor, no reflective instantiation, so a `switch` expression over an enum can be exhaustive with **no `default`** in Java 21 (`error: the switch expression does not cover all possible input values` otherwise) and gets a `MatchException` branch for post-compilation drift | no exhaustiveness anywhere; every `switch` needs a `default` that nobody keeps up to date |
| Why the JDK bothers | one language feature buys identity semantics, safe publication, name-stable serialization, bitset-backed collections, exhaustiveness checking, and reorder-tolerant dispatch — each of which the hand-rolled pattern gets wrong in a different, silent way | — |

Runtime evidence for the serialization, per-constant-body and collection rows:

```console
valueOf("CLAWED_BACK") = CLAWED_BACK
valueOf("CLAWBACK_ORDERED") threw java.lang.IllegalArgumentException: No enum constant BonusState.CLAWBACK_ORDERED
CLAWED_BACK.compareTo(GRANTED) = 4
CLAWED_BACK.hashCode() stable across calls ? true
EnumSet impl = RegularEnumSet, contents = [GRANTED, ACTIVE]
EnumMap impl = EnumMap, contents = {EXPIRED=reversed to PROMOTIONAL_EXPENSE}
THIRTY_DAY_STANDARD.getClass() = EnumGuaranteesDemo$BonusExpiryPolicy
NEVER_EXPIRES.getClass()       = EnumGuaranteesDemo$BonusExpiryPolicy$1
NEVER_EXPIRES.getDeclaringClass() = EnumGuaranteesDemo$BonusExpiryPolicy
serialized bytes = 74
wire tail (hex)  = 00120000787074000b434c415745445f4241434b
wire tail (text) = CLAWED_BACK
deserialized == BonusState.CLAWED_BACK ? true
```

`74` is `TC_STRING`, `000b` is length 11, then the eleven bytes of `CLAWED_BACK`. No `readResolve`
anywhere, and the round trip still returns the identical instance.

**Interview:** "What does the compiler generate for an `enum`?" — `$VALUES` (private static final
synthetic array), `values()` returning `$VALUES.clone()`, `valueOf(String)`, a private `$values()`
factory, a `<clinit>` constructing each constant with its name and ordinal, `extends Enum<E>`,
two extra leading parameters injected into every constructor, an anonymous subclass per
constant-with-a-body, and — in each *switching* class, not in the enum — a `$SwitchMap` `int[]`.

**Unverified:** which release introduced the memoising `@Stable private int hash` field in
`Enum.hashCode` (JDK 21.0.7's `src.zip` has it; earlier JDKs delegated to `super.hashCode()`). The
OpenJDK changeset history for `Enum.java` would settle it.

---

## Pitfalls

### Treating `values()` as a field read

**Wrong**

```java
// per stake reservation, 2.8M times a day
for (BonusState state : BonusState.values()) {
    if (state == bonus.state()) { applyPolicy(state); }
}
```

Measured on 21.0.7: `40.00 bytes/iter`, `112,000,000 bytes` over 2.8M iterations — 112 MB/day of
eden churn to answer a question with a constant answer.

**Right**

```java
for (int i = 0; i < BonusStates.ALL.size(); i++) {
    BonusState state = BonusStates.ALL.get(i);
    if (state == bonus.state()) { applyPolicy(state); }
}
```

Measured: `0.00 bytes/iter`. Better still, if the question is "which state is this", do not scan at
all — `switch` on it, which allocates nothing and never calls `values()`.

**Why people believe it:** `values()` reads like an accessor for a constant, `BonusState` has
exactly five constants that can never change, and no JDK javadoc or IDE hint says the word
"clone". The four-instruction body is the only place the truth is written down.

### Caching `values()` and then handing out the array

**Wrong**

```java
public final class BonusStates {
    private static final BonusState[] VALUES = BonusState.values();
    public static BonusState[] all() { return VALUES; }   // no clone
}
```

```console
a caller nulled slot 4 and overwrote slot 0
next reader sees slot 4 = null
next reader sees slot 0 = CLAWED_BACK
narrating slot 4 threw java.lang.NullPointerException
BonusStates.byOrdinal(4) = null
```

One caller's write poisoned the universe for every other caller in the JVM, including the class's
own `byOrdinal`, with the `NullPointerException` surfacing far from the damage.

**Right**

```java
public static final List<BonusState> ALL = List.of(VALUES);
```

`List.of` copies once at class-init into private storage with no write path, so `set` throws
`UnsupportedOperationException` and iteration allocates nothing.

**Why people believe it:** `private static final` looks total. It freezes the reference; array
*contents* are never final in Java, and no compiler warning marks the difference.

### Persisting `ordinal()` because `$SwitchMap` "handles reordering"

**Wrong**

```java
// bonus_state SMALLINT NOT NULL
statement.setInt(1, bonus.state().ordinal());
BonusState restored = BonusState.values()[resultSet.getInt("bonus_state")];
```

Reorder the enum, redeploy, and every stored row shifts meaning. From the reorder probe:

```console
a row persisted as ordinal 4 now reads back as CLAWED_BACK   # before
a row persisted as ordinal 4 now reads back as EXPIRED       # after
```

A clawed-back bonus becomes a merely-expired one. No exception, no log line, a compliance defect.

**Right**

```java
statement.setString(1, bonus.state().name());
BonusState restored = BonusState.valueOf(resultSet.getString("bonus_state"));
```

`name()` is stable across reordering, and `valueOf` throws
`IllegalArgumentException: No enum constant BonusState.X` loudly if a constant is renamed or
removed. Where a shorter column matters, declare your own code the way `ActivationStatus` declares
`AA-801`, and never let the ordinal out of the JVM.

**Why people believe it:** `$SwitchMap` genuinely does make reordering safe, and the reorder probe
above shows five correct narrations after a full reshuffle. The protection covers compiled
`switch` sites inside the JVM. It cannot reach an integer already written to a database.

---

## Cheat sheet

| Fact | Value |
|---|---|
| `values()` body | `return (BonusState[]) $VALUES.clone();` — 4 instructions, 1 allocation |
| Flags | `$VALUES` is `ACC_PRIVATE, STATIC, FINAL, SYNTHETIC`; `values()` is `PUBLIC, STATIC`, **not** synthetic |
| `BonusState[5]` size | 16-byte header + 5 x 4 = 36 → aligned **40 bytes** |
| Measured | 40.00 bytes/call; 2.8M/day = 112,000,000 bytes = **112 MB/day**; cached `List` = **0.00** |
| Safe accessor | `List.of(VALUES)` — no write path. Not the bare array |
| Skips `values()` | `switch` (per dispatch), `EnumSet`, `EnumMap`, `Enum.valueOf`. `Class.getEnumConstants()` does not — it clones |
| `$SwitchMap` lives in | the **switching** class's synthetic holder, e.g. `BonusStateNarrator$1` |
| `$SwitchMap` maps | live `ordinal()` → compile-time case index; `catch NoSuchFieldError` per store |
| Injected constructor | `(String name, int ordinal, <declared params>)`, implicitly `private` |
| Reflection | `getDeclaredConstructor(String)` fails; `newInstance` throws `IllegalArgumentException: Cannot reflectively create enum objects` |
| `final` on `Enum` | `name`, `ordinal`, `name()`, `ordinal()`, `equals`, `hashCode`, `compareTo`, `clone`, `getDeclaringClass`, `finalize` |
| `clone()` | `protected final`, throws `CloneNotSupportedException` |
| Serialization | by name (`TC_STRING` + name on the wire); `readObject` throws `InvalidObjectException`; no `readResolve` needed or allowed |
| `EnumSet` ≤64 constants | `RegularEnumSet`, one `private long elements`; `EnumMap` = `Object[] vals` by `ordinal()` |
| Per-constant body | anonymous subclass; `getClass()` is `Enclosing$Enum$1`, use `getDeclaringClass()` |
| Java 21 exhaustive `switch` | no `default` needed; `MatchException` branch generated |
| Persist | `name()` or your own code (`AA-801`). Never `ordinal()` |

---

## Self-test

**Q1.** Derive the byte cost of one `BonusState.values()` call under compressed oops, then say
what it comes to per day at QuizStakes volume.

<details><summary>Answer</summary>

An array object header is 16 bytes: an 8-byte mark word, a 4-byte compressed klass pointer, and a
4-byte length field. Five elements at 4 bytes each under compressed oops is 20 bytes. 16 + 20 = 36,
aligned up to the 8-byte boundary gives 40 bytes. The harness measured exactly 40.00
bytes/iteration on 21.0.7, so the derivation is confirmed rather than assumed. At 2.8M stake
reservations a day with one call each: 2,800,000 x 40 = 112,000,000 bytes = 112 MB/day. The
harness's own total over 2,800,000 iterations was 112,000,000 bytes.

</details>

**Q2.** Under the default JIT, which of the two harness shapes had its allocation eliminated, and
why is that the opposite of what you would guess?

<details><summary>Answer</summary>

The *escaping* one. `escapingValues().length` dropped from 40.00 to 1.17 bytes/iteration under the
default JIT, because after inlining the only consumer is `arraylength`, which C2 constant-folds
from `$VALUES`, so the whole `clone()` is dead code and gets deleted — that is dead-code
elimination, not scalar replacement. The non-escaping `scanWithValues()` loop, the shape escape
analysis exists for, paid the full 40.00 bytes in both the default and `-XX:-DoEscapeAnalysis`
runs. Why C2 declined to scalar-replace it is an open question in this note. The practical
consequence: the cache helps most exactly where the array is genuinely read.

</details>

**Q3.** A colleague reorders `BonusState` so `CLAWED_BACK` comes first and redeploys only the enum
jar. What breaks and what does not?

<details><summary>Answer</summary>

Compiled `switch` sites do not break. Each switching class holds a synthetic
`$SwitchMap$BonusState` `int[]` built at *its* class-init from the enum's live `ordinal()` values,
so it re-derives the mapping against the new ordering. The reorder probe shows all five narrations
still correct after the reshuffle. What breaks is anything that persisted an ordinal: a row stored
as ordinal 4 meant `CLAWED_BACK` before and reads back as `EXPIRED` after, with no exception. Also
at risk: any `int` case label or ordinal-keyed external protocol. Persist `name()` or an explicit
code like `AA-801`.

</details>

**Q4.** Why can you not write `new ActivationStatus("AA-999")`, and what does the constructor's
bytecode descriptor actually say?

<details><summary>Answer</summary>

Two independent reasons. At the language level the JLS makes every enum constructor implicitly
`private` — `javap` shows `ACC_PRIVATE` on a constructor declared with no modifier, and writing
`public` explicitly gives `error: modifier public not allowed here`. At the reflective level,
`Constructor.newInstance` on an enum throws
`IllegalArgumentException: Cannot reflectively create enum objects` from
`acquireConstructorAccessor`. The descriptor is `(Ljava/lang/String;ILjava/lang/String;)V` even
though the source declares one parameter: javac injects a leading name and ordinal and passes them
to `Enum.<init>(String, int)`. The declaration line javap prints comes from the `Signature`
attribute, and `MethodParameters` flags the injected pair as synthetic. Consequently
`getDeclaredConstructor(String.class)` throws `NoSuchMethodException`.

</details>

**Q5.** An enum needs no `readResolve`, but the hand-rolled typesafe class of 4.5.1 does. What is
the mechanical difference?

<details><summary>Answer</summary>

Enums are serialized by name, not by field state: the stream carries a `TC_ENUM` record whose
payload is the constant's name, and deserialization resolves that name back to the existing
constant, so identity is preserved by construction. The captured wire bytes end
`74 000b 434c415745445f4241434b` — `TC_STRING`, length 11, `CLAWED_BACK` — and the round trip
returns `back == BonusState.CLAWED_BACK`. `Enum.readObject` and `readObjectNoData` both throw
`InvalidObjectException("can't deserialize enum")` so the default field-by-field path can never
run, and the JLS forbids declaring `writeObject`, `readObject`, `readResolve` or `writeReplace` on
an enum. A hand-rolled class gets ordinary field-based serialization, which builds a brand-new
instance, so it must supply `readResolve` to swap that instance for the canonical one.

</details>

**Q6.** Does `EnumSet.of(BonusState.GRANTED, BonusState.ACTIVE)` pay the `values()` clone?

<details><summary>Answer</summary>

No. `EnumSet.getUniverse` goes through `SharedSecrets.getJavaLangAccess().getEnumConstantsShared(elementType)`,
and `Class.getEnumConstantsShared()` caches the universe in a `transient volatile T[] enumConstants`
field and returns it **uncloned**. It does invoke `values()` reflectively, but only on the first
call for that `Class`, ever. The public `Class.getEnumConstants()` is the cloning wrapper —
`getEnumConstantsShared().clone()`. `EnumMap`'s constructor uses the same shared path. In other
words the JDK already ships the cache this leaf builds; `BonusStates.VALUES` is
`Class.enumConstants` with `private` visibility instead of package-private.

</details>

---

## Open questions

- Why C2 did not scalar-replace the non-escaping `BonusState[]` inside
  `ValuesAllocationHarness.scanWithValues()`, where the clone is fully consumed within the method,
  while it did eliminate the array in the escaping `escapingValues().length` shape. A fastdebug
  build with `-XX:+PrintEscapeAnalysis`, or a C2 IR dump, would settle it. Guide 06 owns
  escape-analysis tooling.
- Which JDK release introduced the memoising `@Stable private int hash` field behind
  `Enum.hashCode()`. It is present in 21.0.7's `src.zip`; earlier JDKs delegated to
  `super.hashCode()`. The OpenJDK changeset history for `java/lang/Enum.java` would settle it.

---

**Leaves covered:** 4.5.6, 4.5.7 (2 leaves)
**Leaves deferred:** none
**Diagrams included:** none
**Target version:** Java 21 LTS
**Lines:** 900
