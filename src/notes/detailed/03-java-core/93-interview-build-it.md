# 03 Java Core — Part 4 interview wrap-up — BUILD IT (§4.1–§4.8)

**Target version: Java 21 LTS.** | **Part 4 of 5** | [Index](00-index.md)
Previous: [Part 3 interview wrap-up](92-interview-internals.md) · Next: [The 80 questions, 1–16](94-interview-questions-and-drills.md)

## Summary table

| Section | What you build | The mechanism it proves | Where it is written |
|---|---|---|---|
| §4.1 | `MyString` — immutable char/byte-backed string with lazy hash caching and an intern pool | The `hash`/`hashIsZero` pair solves the "0 is both the default int and a legal hash" ambiguity without `volatile`; interning needs both weak keys and weak values or it never collects | [MyString and MyStringBuilder](build-it/01-mystring-and-mystringbuilder.md), [Intern pool and diff](build-it/01a-mystring-intern-pool-and-diff.md) |
| §4.2 | `MyStringBuilder` — growable `char[]` buffer | `2 * old + 2` growth gives amortised O(1) append even though any single triggering append copies up to ~n chars; the `+2` guarantees forward progress from capacity 0 | [MyStringBuilder](build-it/01b-mystringbuilder.md), [Cost and diff](build-it/01c-mystringbuilder-cost-and-diff.md) |
| §4.3 | `MyInteger` — reimplementation of `Integer.valueOf`'s cache | A fixed `[-128,127]` array plus a tunable upper bound reproduces `IntegerCache`; the cache only saves allocation when the box escapes, because C2 scalar-replaces non-escaping boxes anyway | [MyInteger and generics](build-it/02-myinteger-and-generics.md) |
| §4.4 | Generic constructs — typesafe heterogeneous container, generic stack, self-bounded builder, super type token, wildcard `copy`, generic varargs | `Class<T>` tokens buy runtime type safety only if `type.cast()` runs at the write site; array covariance and generic-varargs heap pollution are the same erasure hole from two directions; PECS is a direct reading of use-site variance | [Generic containers](build-it/02a-generic-containers.md), [Typesafe container and stack](build-it/02b-typesafe-container-and-generic-stack.md), [Builders, tokens, varargs](build-it/02c-generic-builders-tokens-and-varargs.md), [Wildcard copy and diff](build-it/02d-wildcard-copy-varargs-and-diff.md) |
| §4.5 | Enum builds — bonus-lifecycle state machine, enum singleton, `values()` cache, strategy enum, persisted status code | `EnumMap`-backed transition tables never return null on an illegal edge; an `enum` is the only singleton the JDK special-cases against reflection and serialization; `values()` clones on every call | [Enums, exceptions, resources](build-it/03-enums-exceptions-resources.md), [State machine and singleton](build-it/03a-enum-state-machine-and-singleton.md), [values() cache and diff](build-it/03b-enum-values-cache-and-diff.md), [Strategy enum](build-it/03f-strategy-enum.md), [Enum singleton](build-it/03g-enum-singleton.md), [Persisted-code enum](build-it/03k-persisted-code-enum.md) |
| §4.6 | Exception and resource builds — checked/unchecked hierarchy, stackless exceptions, `AutoCloseable`/`finally`, `Cleaner`, checked-exception crossing | `fillInStackTrace` cost is depth-dependent, never a flat ratio; a bare multi-resource `finally` closes only up to the first failure and destroys the primary; `try`-with-resources attaches later failures as suppressed, in reverse-declaration order | [Exception hierarchy and stackless](build-it/03c-exception-hierarchy-and-stackless.md), [AutoCloseable and finally](build-it/03d-autocloseable-and-finally.md), [Checked crossing, cleaner, diff](build-it/03e-checked-crossing-cleaner-and-diff.md), [Stackless exception](build-it/03h-stackless-exception.md), [finally-return harness](build-it/03i-finally-return-harness.md), [Cleaner and diff](build-it/03j-cleaner-and-diff.md), [finally destroys the primary](build-it/03l-finally-destroys-the-primary.md), [Exception context and null policy](build-it/03m-exception-context-and-null-policy.md), [Exception boundaries and serialization](build-it/03n-exception-boundaries-and-serialization.md) |
| §4.7 | Value-object and money builds — `Money`, `MoneyMinor`, rounding-bias experiment, defensive copying, deep copy, `Clock` injection | `BigDecimal.equals` includes scale so it disagrees with `compareTo`; a `record`'s canonical constructor is the only place that reliably runs on every construction path, including deserialization; `Clock` as a constructor parameter is what turns a 30-day boundary into a deterministic test | [Value objects and money](build-it/04-value-objects-and-money.md), [Defensive copying and collections](build-it/04a-defensive-copying-and-collections.md), [Deep copy and Clock injection](build-it/04b-deep-copy-and-clock-injection.md), [Allocation and rounding bias](build-it/04c-allocation-and-rounding-bias.md), [Value object diff](build-it/04d-value-object-diff.md), [Rounding bias experiment](build-it/04e-rounding-bias-experiment.md), [Clock injection](build-it/04f-clock-injection.md) |
| §4.8 | Diagnostic harnesses — puzzlers, construction trap, init order, class-init deadlock, constant inlining, inner-class retention, pass-by-value, overload resolution, `SimpleDateFormat` race, DST | Fifteen classic gotchas plus six from-scratch harnesses, each with real captured JVM output, not folklore: a class-init deadlock that never shows up as a JMX monitor cycle, a `this$0` retention leak of 10,002:1, `0.1+0.2`'s exact printed digits | [Diagnostic harnesses](build-it/05-diagnostic-harnesses.md), [Construction and init harnesses](build-it/05a-construction-and-init-harnesses.md), [Inlining and retention harnesses](build-it/05b-inlining-and-retention-harnesses.md), [Dispatch and value harnesses](build-it/05c-dispatch-and-value-harnesses.md), [Concurrency and time harnesses](build-it/05d-concurrency-and-time-harnesses.md), [Class-init deadlock](build-it/05e-class-init-deadlock.md), [Puzzler harness, part two](build-it/05f-puzzler-harness-part-two.md), [Class initialization order](build-it/05g-class-initialization-order.md), [Inner-class retention](build-it/05h-inner-class-retention.md), [DST harness](build-it/05i-dst-harness.md), [Overload resolution harness](build-it/05j-overload-resolution-harness.md) |

## What each build measured

| Build | The measurement | The figure it reported | File |
|---|---|---|---|
| `HashProbe` hash-cache counter | Recomputations of `hashCode()` over 1,000,000 calls on a zero-hash key, with and without `hashIsZero` | 1,000,000 loops without the flag vs 2 with it | [build-it/01-mystring-and-mystringbuilder.md](build-it/01-mystring-and-mystringbuilder.md) |
| `LayoutHarness` object layout | Heap footprint of `MyString` vs `String` over the same 18-char payload | `new MyString(char[18])` = 80 B, `new String(char[18])` = 64 B | [build-it/01-mystring-and-mystringbuilder.md](build-it/01-mystring-and-mystringbuilder.md) |
| `InternPoolDemo` | Retained heap and post-GC pool size for three intern-pool shapes over 200,000 keys | strong pool 200,000 survive GC / 31,425 KiB; weak-self-valued 200,000 survive / 32,988 KiB; weak-key-and-value 0 survive / 17,413 KiB | [build-it/01a-mystring-intern-pool-and-diff.md](build-it/01a-mystring-intern-pool-and-diff.md) |
| `InternCostDemo` | Cost of `String.intern()` vs an array read and a static-final field read | 65.42 ns/call vs 0.60 ns and 0.45 ns — 146.3x the field read | [build-it/01a-mystring-intern-pool-and-diff.md](build-it/01a-mystring-intern-pool-and-diff.md) |
| Growth-trace harness | Reallocations and total chars copied appending 1,000,000 single chars from capacity 16 | 16 reallocations, final capacity 1,179,646, 1,179,598 chars copied = 1.1796n (bound is 2n) | [build-it/01b-mystringbuilder.md](build-it/01b-mystringbuilder.md) |
| Four-variant append benchmark | ns/char for `MyStringBuilder`, `StringBuilder`, `String +=`, and one `+` expression | 1.04, 0.82, 147.53, 14.98 ns respectively; `+=` is 179x `StringBuilder`'s per-char cost at n=4,000 | [build-it/01c-mystringbuilder-cost-and-diff.md](build-it/01c-mystringbuilder-cost-and-diff.md) |
| `AllocationHarness` | Bytes/objects allocated boxing 2,800,000 reservations, cache on/off, escaping/non-escaping | cache off, non-escaping: 3,014,640 B / 188,415 objects (default JIT); cache off, escaping: 44,800,000 B / 2,800,000 objects in both JIT modes | [build-it/02-myinteger-and-generics.md](build-it/02-myinteger-and-generics.md) |
| `BoundaryProof` | `==` identity at the cache edges `-129..129` | `==` true for `-128..127`, false at `-129` and `128` | [build-it/02-myinteger-and-generics.md](build-it/02-myinteger-and-generics.md) |
| `values()` clone cost | Bytes/iteration for a live `values()` call vs a cached `List` | 40.00 bytes/iter uncached vs 0.00 bytes/iter cached; 2.8M/day naive cost = 112 MB/day | [build-it/03b-enum-values-cache-and-diff.md](build-it/03b-enum-values-cache-and-diff.md) |
| `DepthHarness` stackless-exception benchmark | `new`+capture and throw+catch cost, normal vs stackless, at depths 1/100/500 | construction 10.97x/26.1x/6.42x, throw+catch 11.15x/1.47x/1.40x at depths 1/100/500 respectively; capture ≈15 ns/frame, unwind ≈36.5 ns/frame | [build-it/03h-stackless-exception.md](build-it/03h-stackless-exception.md) |
| `finally`-return harness | 12 cases of value/exception loss through `finally` | all 12 outcomes captured; `-Xlint:finally` fires on 7 of the 12 and misses the mutation cases entirely | [build-it/03i-finally-return-harness.md](build-it/03i-finally-return-harness.md) |
| `DeepCopy` vs `SerialCopy` | Time and bytes to deep-copy a `PaymentRun` graph with a shared node and a cycle | hand-written 0.466 ms / 287,959 B per copy vs serialization 2.432 ms / 3,557,572 B — 5.2x time, 12.4x bytes | [build-it/04b-deep-copy-and-clock-injection.md](build-it/04b-deep-copy-and-clock-injection.md) |
| Rounding-bias experiment, run A (engineered halves) | Cumulative drift over 1,000,000 roundings under `HALF_UP`, `HALF_EVEN`, `DOWN` | `HALF_UP` +5,000.0000 major units, `HALF_EVEN` +0.8800, `DOWN` -5,000.0000 | [build-it/04e-rounding-bias-experiment.md](build-it/04e-rounding-bias-experiment.md) |
| Rounding-bias experiment, run B (realistic stakes) | Same drift, uniform [1.00,9.99] stakes, priced against 2.8M reservations/day | `HALF_UP` vs `DOWN` costs 13,993.56/day; `HALF_EVEN` vs `DOWN` costs 12,596.08/day | [build-it/04e-rounding-bias-experiment.md](build-it/04e-rounding-bias-experiment.md) |
| `LedgerAuditRace` | Correct/wrong/threw counts, shared `SimpleDateFormat` vs five safe alternatives, 6,400,000 ops | shared no-lock: 3,506,620 correct, 2,873,198 silently wrong, 20,182 threw; every alternative: 6,400,000 correct, 0 threw | [build-it/05d-concurrency-and-time-harnesses.md](build-it/05d-concurrency-and-time-harnesses.md) |
| Inner-class retention histogram | Bytes pinned by one `PaymentRun$WindowSignOff` registry entry | 240,064 bytes retained by a 24-byte holder — 10,002.7:1 | [build-it/05h-inner-class-retention.md](build-it/05h-inner-class-retention.md) |

## Interview Q&As

### Implement `Integer.valueOf`'s cache — where do you put the boundary, and how do you make it tunable without breaking JLS §5.1.7?

I'd back it with a plain array sized to the window and a static initializer. The low end is fixed at `-128` because JLS §5.1.7 mandates that `-128..127` must always be cached — that's not implementation freedom. The high end is what the real JDK makes tunable through `-XX:AutoBoxCacheMax` and the `java.lang.Integer.IntegerCache.high` property, so I mirror that with `Math.max(configuredHigh, 127)` — you can only raise the ceiling, never lower it below the mandated floor, and an unparseable value is silently ignored rather than blowing up the cache's static init.

```java
static final int LOW = -128;
static final int HIGH;
private static final MyInteger[] CACHE;
static {
    int h = 127;
    String configured = System.getProperty("quizstakes.MyInteger.cache.high");
    if (configured != null) {
        try { h = Math.max(Integer.parseInt(configured), 127); }
        catch (NumberFormatException ignored) { /* keep default */ }
    }
    HIGH = h;
    CACHE = new MyInteger[(HIGH - LOW) + 1];
    for (int i = 0, v = LOW; i < CACHE.length; i++, v++) CACHE[i] = new MyInteger(v);
}
static MyInteger valueOf(int v) {
    return (v >= LOW && v <= HIGH) ? CACHE[v - LOW] : new MyInteger(v);
}
```

The measurement that surprised me building this: the cache only pays for itself when the box *escapes*. In `build-it/02-myinteger-and-generics.md`'s `AllocationHarness`, boxing 2.8M reservations that never leave a method allocated 3,014,640 bytes with the cache off under default JIT settings — not the naive 44,800,000 bytes — because C2's escape analysis scalar-replaces the non-escaping boxes; only 188,415 of 2.8M actually survived as real objects. Turn escape analysis off (`-XX:-DoEscapeAnalysis`) and the cache-off cost jumps to the full 44,800,000 bytes across 2,800,000 objects, matching the naive arithmetic exactly. So the interview answer isn't "the cache saves allocation" — it's "the cache saves allocation for boxes the JIT can't already prove don't escape," which for QuizStakes means anything stored in a `List<Integer>`, used as a map key, or returned across a method boundary.

### Write an exception that skips stack-trace capture — when is that right?

Route the `fillInStackTrace` protected constructor: `super(message, cause, enableSuppression, writableStackTrace)` with `writableStackTrace=false`. That sets the internal `stackTrace` field to `null` instead of `Throwable.UNASSIGNED_STACK`, which makes `fillInStackTrace()` a no-op — `getOurStackTrace()` returns the shared empty `StackTraceElement[0]` forever, and the frame walk in `<init>` never happens.

```java
class StacklessInsufficientFundsException extends RuntimeException {
    StacklessInsufficientFundsException(String message) {
        super(message, null, false, false);
    }
}
```

The gain is real but depth-dependent, and I'd never quote a single number without the depth attached — the exact measurement, from `build-it/03h-stackless-exception.md`'s `DepthHarness` on JDK 21.0.7: throw+catch, normal vs stackless, is **11.15x at depth 1**, drops to **1.47x at depth 100**, and **1.40x at depth 500**. The reason it compresses: capture costs roughly 15 ns per frame, but *unwinding* the frames to reach the catch block costs roughly 36.5 ns per frame regardless of whether you captured them, and stackless only removes the capture cost — the unwind cost is unavoidable and dominates as depth grows. So it's right for a genuinely hot, shallow, expected-failure path — a single-frame validation exception thrown at 1,200/sec peak costs 0.033% of one core either way, which is the actual QuizStakes verdict in that file: not justified below roughly a million throws per second per core. It's wrong to reach for reflexively; the pattern I'd actually steal is the JDK's own `ScopedMemoryAccess.ScopedAccessError` — stackless on the hot internal path, with a `Supplier<RuntimeException>` that materializes a fully-traced exception only at the public boundary where a human will read it.

The JVM flags back this up: `-XX:+PrintFlagsFinal -version` on this build confirms `MaxJavaStackTraceDepth = 1024` (the depth-500 measurement above is comfortably inside that cap, so nothing was silently truncated), `OmitStackTraceInFastThrow = true` (C2's own hot-throw optimization — a different mechanism from a hand-written stackless constructor; it kicks in automatically when the same exception type is thrown from the same site more than a threshold number of times, and replaces the thrown object with a preallocated one that has no stack trace at all), and `StackTraceInThrowable = true` (the global kill switch; flipping it off would make every exception behave like the stackless variant, JVM-wide — a deployment lever, not something you'd want per-exception-type in normal operation).

### The `MyString` field set and hash caching — what does it look like and why do you need two fields, not one?

```java
private final char[] value;
private final byte coder;
private int hash;
private boolean hashIsZero;
```
`hashCode()` computes lazily and caches into `hash`, but `0` is both the uninitialized-field default and a perfectly legal hash result — a coupon code like `NQZ48OHT` genuinely hashes to zero. If you only had `hash`, you couldn't tell "never computed" from "computed and it's zero," and you'd recompute on every call for that string forever. The second boolean breaks the tie:

```java
public int hashCode() {
    int h = hash;
    if (h == 0 && !hashIsZero) {
        for (char c : value) h = 31 * h + c;
        if (h == 0) hashIsZero = true; else hash = h;
    }
    return h;
}
```
Measured effect in `build-it/01-mystring-and-mystringbuilder.md`'s `HashProbe`: without the flag, a zero-hash key recomputes its hash on every one of 1,000,000 calls; with the flag, both a zero-hash key and a normal key together cost 2 total computations. Neither field is `volatile`, and no lock is taken — the four-step race argument is: every racing thread reads the same `final`, unshared `value` array so they compute the same result; JLS §17.7 makes `int`/`boolean` field reads and writes atomic; at most one of the two fields is written per call (never both in the same branch); and the write is idempotent, so a race costs redundant work, never a wrong answer. That's the same argument `java.lang.String`'s own source carries for its identical `hash`/`hashIsZero` pair.

### `2 * old + 2` and the amortised argument — walk me through why appending is still O(1) amortised when one call copies almost the whole buffer.

The growth rule, straight from the code:
```java
private int newCapacity(int minCapacity) {
    int preferred = (value.length << 1) + 2;
    if (preferred < 0) preferred = Integer.MAX_VALUE - 8;
    int chosen = Math.max(preferred, minCapacity);
    if (chosen < 0) throw new OutOfMemoryError("Required length exceeds implementation limit");
    return chosen;
}
```
The `+2` matters because capacity `0` is reachable (`new StringBuilder(0)`) and `2*0` would never grow — the additive term guarantees strict forward progress from any starting capacity, including 0 and 1. The amortised proof: each reallocation copies roughly double what the previous one copied, so if the *last* grow before reaching length n copies C characters, the sum of every earlier copy is `C + C/2 + C/4 + ... < 2C`, and `C ≤ n` because that grow happened while the buffer was still shorter than n. Total copying across the whole run is bounded by roughly `2n`, independent of how many times you grew — so the *average* cost per append is O(1), even though the single append that triggers the 16th reallocation individually copies 589,822 characters, which is very much not O(1) for that one call. The measured trace in `build-it/01b-mystringbuilder.md` appending 1,000,000 chars from a default capacity-16 builder took exactly 16 reallocations, copied 1,179,598 characters total — a ratio of 1.1796n, comfortably under the 2n worst case, because the run stops 69% of the way through the final doubling window rather than right after it. QuizStakes-scale version of the same lesson: 2.8M settlement audit lines a day at ~120 chars each means 3 grows per line from the default builder, 240 bytes of pointless copying per line, 672 MB/day — `new StringBuilder(128)` makes that zero.

### `Result<T,E>` versus a checked exception — when do you reach for which?

A checked exception forces every caller to acknowledge failure at compile time, but it can't say anything about the *shape* of the failure beyond the exception type, and it doesn't compose — you can't `.map()` or `.flatMap()` a `throws` clause. `Result<T,E>` (built alongside `Either` in `build-it/02a-generic-containers.md`) makes failure an ordinary value: it's the only one of the options a caller cannot silently forget exists at the call site as a raw ignorable checked exception can be swallowed by a blanket catch, and it's the only one that composes with `flatMap` across a pipeline of operations that can each fail differently. The trade-off from `build-it/03e-checked-crossing-cleaner-and-diff.md`'s crossing problem: when a checked exception has to cross a functional-interface boundary like `Function<T,R>`, you either lose the exception's type entirely (`uncheckedBare`), preserve it through a purpose-built interface (`CheckedFunction<T,R,E extends Exception>` with `R apply(T) throws E`), or refuse to throw at all and return an `Attempt<T,R>`/`Result<T,E>` that never aborts the pipeline. My ranked order for QuizStakes code: declare the checked exception if the immediate caller has a genuine non-exceptional continuation; wrap in a purpose-made unchecked type if it doesn't; reach for `Result<T,E>` when the operation is mine to design and failure is a routine outcome, not an exceptional one; and never sneaky-throw in application code — that's for framework plumbing only, and even there it should be rare.

### The enum state machine and why an enum is the best singleton — what does the transition table look like, and what makes `enum` special as a singleton?

The bonus lifecycle in `build-it/03a-enum-state-machine-and-singleton.md` is `BonusState { GRANTED, ACTIVE, CONSUMED, EXPIRED, CLAWED_BACK }` driven by `Event { FIRST_DEPOSIT_CAPTURED, STAKE_CONSUMED_BALANCE, EXPIRY_ELAPSED, CLAWBACK_ORDERED }`, backed by a `Map<BonusState, Map<Event, BonusState>>` built as nested `EnumMap`s inside a `static {}` block — it has to be a static block, not a field initializer, because the table references the enum constants and a field initializer above the constants would see them unassigned.
```java
BonusState transition(Event event) {
    BonusState next = TABLE.get(this).get(event);
    if (next == null) throw new IllegalTransitionException(this, event);
    return next;
}
```
It never silently stays put on an illegal edge — it throws. `EXPIRED` and `CLAWED_BACK` are terminal (empty inner maps, not absent keys), and `CONSUMED → CLAWED_BACK` is deliberately legal because a clawback after the stake settled still needs to claw back any *unspent* bonus and post the shortfall to `PROMOTIONAL_EXPENSE`.

On the singleton question, `enum` is the only Java singleton idiom the JDK special-cases at three separate points, all shown with real captured attacks in `build-it/03g-enum-singleton.md`: reflection — `Constructor.newInstance` checks the `ACC_ENUM` class-file flag and throws `IllegalArgumentException: Cannot reflectively create enum objects` before it ever calls the constructor; serialization — an enum constant is written as a `TC_ENUM` tag carrying only its `name()`, and `Enum` itself overrides `readObject` to throw, so there's no instance to substitute a `readResolve` for; cloning — `Enum.clone()` is `protected final`, so overriding it is a compile error, not a runtime guard. The one thing that still breaks it, and every other singleton idiom equally: a second class loader defining the same class produces a second, distinct singleton instance, because type identity in the JVM is the pair `(loader, name)`, not just the name.

### `AutoCloseable`/`finally` and suppression — what's the exact contract, and what breaks it?

`AutoCloseable.close()` is documented as "not required to be idempotent," unlike `Closeable.close()` which is required to be. Try-with-resources honors that: it calls `close()` at most once per resource per JLS §14.20.3. The bug in `build-it/03d-autocloseable-and-finally.md` is a naive writer with no idempotence guard, closed once explicitly and once by TWR — it posted the same batch of ledger rows twice, running total going from 44,000 to 88,000 minor units. Fix is `AtomicBoolean closed` guarded by `compareAndSet`, since a plain or even `volatile boolean` check-then-act isn't atomic under concurrent close.

Suppression is the mechanism that keeps a second failure from erasing the first. With two resources declared in a `try (...)`, closed in reverse declaration order: if the body throws and then a `close()` also throws, the body's exception is the one the caller sees, and the close failure is attached via `getSuppressed()` — not discarded. If *both* closes throw, both show up as suppressed, in close order. But this is TWR-specific machinery; a hand-rolled `finally { export.close(); writer.close(); }` gets none of it. `build-it/03l-finally-destroys-the-primary.md` captures exactly that: an `InsufficientFundsException` already in flight, then `export.close()` throws `RestrictedActionException` — the `finally` block completes abruptly, so per JLS §14.20.2 the finally's reason wins and the original exception is discarded with zero trace, `getSuppressed().length == 0`, and `writer.close()` never even runs because the first close threw before reaching the second line. The rule generalizes: whatever a `finally` (or a `catch` block) throws or returns unconditionally overrides whatever the `try` was doing, silently.

### `Money` as `BigDecimal` versus minor-unit `long` — which do you ship, and what's the trap in `BigDecimal.equals`?

`build-it/04-value-objects-and-money.md` builds both: `Money(BigDecimal amount, Currency currency)` and `MoneyMinor(long units, Currency currency)`. The trap is that `BigDecimal.equals` compares `(unscaledValue, scale)`, not numeric value — `new BigDecimal("2.00").equals(new BigDecimal("2.0"))` is `false`, while `compareTo` on the same pair returns `0`. That makes a record's auto-generated `equals` unsafe unless you close off the scale ambiguity somewhere else, which is exactly what `Money`'s compact constructor does: it rejects any `BigDecimal` whose scale doesn't equal `currency.getDefaultFractionDigits()`, so two `Money` values that are numerically equal are always represented identically, and the generated `equals` becomes trustworthy. Footprint-wise `Money` measures at 64 bytes (24-byte record shell plus a 40-byte `BigDecimal`) against `MoneyMinor`'s exact 24 bytes (12-byte header, 8-byte long, 4-byte currency reference). What I'd actually ship for QuizStakes: `Money(BigDecimal, Currency)` in the domain layer, where scale-enforced decimal arithmetic reads naturally, and minor-unit `BIGINT` in the ledger table, where exact integer arithmetic and compact storage matter more than readability. The bonus-split rounding rule rides on the same discipline: a stake of 3.33 splits as 0.33 bonus + 3.00 cash because the bonus portion always rounds *down* to the minor unit — rounding the other way gives 0.34 + 3.00 = 3.34, which is 0.01 more than the stake and literally creates money. The `StakeSplit` invariant enforces the sum matches the stake exactly, and constructing the wrong-direction split throws `IllegalArgumentException` at the boundary rather than downstream.

### Why inject `Clock` instead of calling `Instant.now()` directly, and how does that interact with the 30-day bonus expiry?

Because `Instant.now()` baked into a method body makes the method's output depend on wall-clock time, which means you cannot write a deterministic test for a boundary like "expires exactly 30 days after grant" without sleeping for 30 days or manipulating the system clock. `build-it/04f-clock-injection.md`'s fix is to take `Clock` as a constructor parameter and call `clock.instant()` everywhere `Instant.now()` would otherwise appear:
```java
private final Clock clock;
BonusExpiryService(FundsLedger ledger, Clock clock) { this.ledger = ledger; this.clock = clock; }
static BonusExpiryService production(FundsLedger ledger) {
    return new BonusExpiryService(ledger, Clock.systemUTC());
}
public boolean expireIfDue(Bonus bonus) {
    Instant expiresAt = bonus.grantedAt.plus(EXPIRY_DAYS, ChronoUnit.DAYS);
    return !clock.instant().isBefore(expiresAt) && doExpire(bonus);
}
```
Tests wire in `Clock.fixed(now, ZoneOffset.UTC)` and probe the boundary at `EXPIRES_AT.minusNanos(1)` (not yet expired) and exactly `EXPIRES_AT` (expired) — proving the window is half-open, `[grantedAt, grantedAt + 30 days)`. The file also shows why swapping in a static mock of `Instant.now()` is the worse alternative even though it produces the same test result: it couples every test to the exact call site inside the production method (breaking silently if the code is refactored to call `Instant.now()` somewhere else), whereas the constructor parameter is visible in the type signature and testable without any mocking framework at all. The same pattern would apply to the 14-day coupon validity window off `registeredAt`.

### The class-init deadlock harness — how do you actually prove a deadlock that no JMX API can see?

Two classes, `BonusService` and `FundsLedger`, each reference the other's static state from inside their own `<clinit>`. Start them concurrently from two threads synchronized on a `CyclicBarrier` so they enter class initialization at effectively the same instant: each thread acquires its own class's initialization lock first, then blocks trying to acquire the other's — classic lock-ordering deadlock, except the locks are the JVM's internal per-class initialization locks, which `ThreadMXBean.findDeadlockedThreads()` and `findMonitorDeadlockedThreads()` both return `null` for, because those APIs only see `synchronized`/`java.util.concurrent` locks, not class-init locks. The captured evidence in `build-it/05e-class-init-deadlock.md`: after 3 seconds, both threads report `state=RUNNABLE`, both are still `alive=true`, and the JMX deadlock finders find nothing — "two live threads, neither making progress, and no monitor cycle to find." The load-bearing evidence only shows up in a `jstack`/`jcmd Thread.print` dump, which annotates each thread with `- waiting on the Class initialization monitor for <the other class>` even while the JVM reports it as `RUNNABLE`. The fix is the same one that fixes every other cyclic-static-dependency problem: break the cycle, typically with the lazy holder-class idiom, so at most one direction of the dependency actually triggers class initialization eagerly.

## Predict the output

### Puzzle 1 — the coder byte and the zero-hash coupon

```java
import java.util.Arrays;

public class HashProbePuzzle {
    static final class MyString {
        private final char[] value;
        private int hash;
        private boolean hashIsZero;
        MyString(String s) { this.value = s.toCharArray(); }
        @Override public int hashCode() {
            int h = hash;
            if (h == 0 && !hashIsZero) {
                for (char c : value) h = 31 * h + c;
                if (h == 0) hashIsZero = true; else hash = h;
            }
            return h;
        }
    }

    public static void main(String[] args) {
        MyString coupon = new MyString("NQZ48OHT");
        int loopsWithoutFlag = 0;
        for (int i = 0; i < 1_000_000; i++) {
            // simulate a build with no hashIsZero flag: force recompute every call
            int h = 0;
            for (char c : "NQZ48OHT".toCharArray()) h = 31 * h + c;
            loopsWithoutFlag++;
        }
        int firstCall = coupon.hashCode();
        int secondCall = coupon.hashCode();
        System.out.println("coupon NQZ48OHT, String.hashCode : " + "NQZ48OHT".hashCode());
        System.out.println("coupon NQZ48OHT, MyString.hashCode: " + firstCall);
        System.out.println("no flag, zero-hash coupon, hash loops run : " + loopsWithoutFlag);
        System.out.println("with flag, both keys, hash loops run      : 2");
    }
}
```

**Output**
```
coupon NQZ48OHT, String.hashCode : 0
coupon NQZ48OHT, MyString.hashCode: 0
no flag, zero-hash coupon, hash loops run : 1000000
with flag, both keys, hash loops run      : 2
```

**Why**: `NQZ48OHT` is a real coupon code whose `String.hashCode()` (the standard `s[0]*31^(n-1) + ... + s[n-1]` polynomial) happens to land on exactly zero. Without the `hashIsZero` flag, `hash == 0` is indistinguishable from "never computed," so every call recomputes it — captured verbatim in `build-it/01-mystring-and-mystringbuilder.md`'s `HashProbe` as 1,000,000 recomputations. With the flag, the first call computes and sets `hashIsZero = true`; every subsequent call short-circuits on `!hashIsZero` being false, so across both a zero-hash key and a normal key the total work is 2 computations, not 2,000,000.

### Puzzle 2 — MyInteger cache boundary

```java
public class BoundaryPuzzle {
    static final class MyInteger {
        static final int LOW = -128, HIGH = 127;
        private static final MyInteger[] CACHE = new MyInteger[HIGH - LOW + 1];
        static { for (int i = 0, v = LOW; i < CACHE.length; i++, v++) CACHE[i] = new MyInteger(v); }
        final int value;
        private MyInteger(int value) { this.value = value; }
        static MyInteger valueOf(int v) {
            return (v >= LOW && v <= HIGH) ? CACHE[v - LOW] : new MyInteger(v);
        }
    }

    public static void main(String[] args) {
        int[] probes = { -129, -128, 0, 126, 127, 128, 129 };
        for (int p : probes) {
            boolean same = MyInteger.valueOf(p) == MyInteger.valueOf(p);
            System.out.printf("openReservations=%4d  ==  %-5b%n", p, same);
        }
    }
}
```

**Output**
```
openReservations=-129  ==  false
openReservations=-128  ==  true
openReservations=   0  ==  true
openReservations= 126  ==  true
openReservations= 127  ==  true
openReservations= 128  ==  false
openReservations= 129  ==  false
```

**Why**: `LOW=-128` is the JLS §5.1.7-mandated floor, `HIGH=127` is the default ceiling. Every call to `valueOf` inside `[-128,127]` returns the exact same cached `MyInteger` instance from `CACHE[v - LOW]`, so `==` is `true`. Outside that window, every call to `valueOf` allocates a fresh instance — two separate calls with the same value produce two separate objects, so `==` is `false` even though `.equals()` would still agree. This is the exact boundary captured in `build-it/02-myinteger-and-generics.md`'s `BoundaryProof`.

### Puzzle 3 — pass-by-value, mutate versus reassign

```java
public class PassByValuePuzzle {
    static final class PaymentRun {
        String id; String status; int count; double total;
        PaymentRun(String id, String status, int count, double total) {
            this.id = id; this.status = status; this.count = count; this.total = total;
        }
        @Override public String toString() {
            return "PaymentRun[" + id + ", status=" + status + ", count=" + count + ", total=" + total + "]";
        }
    }

    static void mutate(PaymentRun r) {
        r.status = "SUBMITTED"; r.count = 2; r.total = 440.00;
    }

    static void reassign(PaymentRun r) {
        r = new PaymentRun("PR-9002", "PENDING_VERIFICATION", 1, 999.99);
    }

    public static void main(String[] args) {
        PaymentRun run = new PaymentRun("PR-9001", "PENDING_VERIFICATION", 1, 180.00);
        System.out.println("before:  " + run);
        mutate(run);
        System.out.println("after mutate:   " + run);

        PaymentRun run2 = new PaymentRun("PR-9001", "PENDING_VERIFICATION", 1, 180.00);
        reassign(run2);
        System.out.println("after reassign: " + run2);
    }
}
```

**Output**
```
before:  PaymentRun[PR-9001, status=PENDING_VERIFICATION, count=1, total=180.0]
after mutate:   PaymentRun[PR-9001, status=SUBMITTED, count=2, total=440.0]
after reassign: PaymentRun[PR-9001, status=PENDING_VERIFICATION, count=1, total=180.0]
```

**Why**: Java passes the object *reference* by value. `mutate` receives a copy of the reference but that copy still points at the caller's object, so writes through it (`r.status = ...`) are visible after the call. `reassign` writes a *new* object into its own local copy of the reference (`r = new PaymentRun(...)`) — that only overwrites the local variable's slot in `reassign`'s stack frame; the caller's `run2` variable still points at the original object. This is the confirmed sole content of `build-it/05c-dispatch-and-value-harnesses.md`'s `PassByValueHarness`, whose captured output matches this reduced snippet exactly for both cases.

### Puzzle 4 — the illegal forward reference

```java
public final class RestrictionSourceMisordered {
    private final String name;
    private RestrictionSourceMisordered(String name) { this.name = name; }

    private static final java.util.List<RestrictionSourceMisordered> VALUES =
            java.util.List.of(SYSTEM_ONBOARDING, ADMIN, CLIENT);

    public static final RestrictionSourceMisordered SYSTEM_ONBOARDING = new RestrictionSourceMisordered("SYSTEM_ONBOARDING");
    public static final RestrictionSourceMisordered ADMIN             = new RestrictionSourceMisordered("ADMIN");
    public static final RestrictionSourceMisordered CLIENT            = new RestrictionSourceMisordered("CLIENT");

    public static java.util.List<RestrictionSourceMisordered> values() { return VALUES; }
}
```

**Output**
```
RestrictionSourceMisordered.java:6: error: illegal forward reference
            java.util.List.of(SYSTEM_ONBOARDING, ADMIN, CLIENT);
                              ^
RestrictionSourceMisordered.java:6: error: illegal forward reference
            java.util.List.of(SYSTEM_ONBOARDING, ADMIN, CLIENT);
                                                  ^
RestrictionSourceMisordered.java:6: error: illegal forward reference
            java.util.List.of(SYSTEM_ONBOARDING, ADMIN, CLIENT);
                                                         ^
3 errors
```

**Why**: `VALUES` is a `static final` field initializer that textually precedes the three constant fields it reads. JLS §8.3.3 forbids a static field's initializer from reading another static field of the same class by simple name if that field is declared later in the same class and the reference isn't inside a method or constructor body — javac flags all three reads as illegal forward references, at compile time, not as a runtime `NullPointerException`. This is captured verbatim in `build-it/03a-enum-state-machine-and-singleton.md`; note the class shown is a hand-rolled pre-`enum`-style constant class (this exact ordering mistake is a compile error there too), which is why the compiler catches it directly — hiding the same forward reference behind a static factory method instead compiles cleanly but fails later at class-init time with `ExceptionInInitializerError` caused by a `NullPointerException` from `List.of` rejecting the nulls it silently received.

### Puzzle 5 — DST spring-forward gap and idempotency key collision

```java
import java.time.*;

public class DstGapPuzzle {
    public static void main(String[] args) {
        ZoneId london = ZoneId.of("Europe/London");
        LocalDateTime insideGap = LocalDateTime.of(2026, 3, 29, 1, 30);

        ZonedDateTime zoned = ZonedDateTime.of(insideGap, london);
        System.out.println("ZonedDateTime.of(label,zone)   " + zoned
                + "  instant=" + zoned.toInstant());

        String key1 = "PaymentRun:" + insideGap;
        String key2 = "PaymentRun:" + insideGap;
        System.out.println("local key, 1st occurrence      " + key1);
        System.out.println("local key, 2nd occurrence      " + key2);
        System.out.println("keys equal, duplicate payout   " + key1.equals(key2));
    }
}
```

**Output**
```
ZonedDateTime.of(label,zone)   2026-03-29T02:30+01:00[Europe/London]  instant=2026-03-29T01:30:00Z
local key, 1st occurrence      PaymentRun:2026-03-29T01:30
local key, 2nd occurrence      PaymentRun:2026-03-29T01:30
keys equal, duplicate payout   true
```

**Why**: `2026-03-29T01:30` never exists on the Europe/London clock — the clocks jump from 01:00 to 02:00 for British Summer Time. `ZonedDateTime.of(LocalDateTime, ZoneId)` doesn't throw for a gap; it silently rolls the local time forward by the gap length (30 minutes here, landing on `02:30+01:00`) and resolves to a real, single `Instant`. The `build-it/05i-dst-harness.md` payoff is the idempotency-key trap this enables: if a payment run's dedupe key is built from the *local* label string rather than the resolved `Instant`, two runs that both nominally target `01:30` produce identical keys and collide as duplicates — even though building the key from the resolved instant instead would correctly distinguish them. `getValidOffsets()` for a label inside the gap returns an empty list (size 0), which is the honest signal to check for before trusting a local time near a DST transition.

---

**Leaves covered:** none — Part 4 wrap-up over §4.1–§4.8, whose leaves are owned by the files linked in the summary table
**Leaves deferred:** none
**Diagrams included:** none
**Target version:** Java 21 LTS
**Lines:** 375
