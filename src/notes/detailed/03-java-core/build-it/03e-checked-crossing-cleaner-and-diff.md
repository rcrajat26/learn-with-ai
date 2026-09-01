# 03 Java Core — Exception builds: `CheckedFunction`, the `unchecked` adapter, and sneaky-throw — BUILD IT (§4.6 (4.6.5, 4.6.6))

**Target version: Java 21 LTS.** | **Part 4 of 5** | [Index](../00-index.md)
Previous: [The finally-return harness](03i-finally-return-harness.md) · Next: [The Cleaner-based holder and the §4.6 diff table](03j-cleaner-and-diff.md)

---

## Where this picks up

[`02a-generic-containers.md`](02a-generic-containers.md) established the problem and its four
escapes: `reserveStake` declares `throws InsufficientFundsException`, `java.util.function.Function`
declares `R apply(T t)` with no `throws` clause, so `stakes.stream().map(request ->
reserveStake(request))` does not compile — and the diagnostic names the lambda body, not the stream.
That file pasted the real `javac` error, embedded **D-133**, built `Result<T,E>`, and handed
workarounds **3** (a custom functional interface) and **2** (sneaky-throw) forward to this file. This
file builds both, runs both, and argues one of them down.

The domain exceptions are the ones built in
[`03c-exception-hierarchy-and-stackless.md`](03c-exception-hierarchy-and-stackless.md) —
`InsufficientFundsException` over an abstract checked root carrying a `StatusCode`-shaped error code
and an immutable structured context map. Everything below uses a **trimmed**
`InsufficientFundsException` with the same name and the same typed accessors (`shortfall()`,
`stakeable()`) so this file compiles standalone. The layering question — which escape belongs in
which layer — is
[`../exceptions/02a-checked-exceptions-and-lambdas.md`](../exceptions/02a-checked-exceptions-and-lambdas.md);
lambdas, streams and `java.util.function` themselves are guide 04's (Modern Java).

---

## §4.6.5 `[BUILD]` `CheckedFunction<T, R, E extends Exception>` and the `unchecked` adapter

### The shape

Two interfaces, one difference:

| | SAM | `throws` on the SAM | Accepted by `Stream.map` |
|---|---|---|---|
| `java.util.function.Function<T,R>` | `R apply(T t)` | none | yes |
| `CheckedFunction<T,R,E extends Exception>` | `R apply(T input) throws E` | `E` | **no** |

**Insight:** what blocks you is the *type of the lambda target*, not the lambda and not the stream.
A lambda compiles into a method implementing the functional interface's single abstract method, and
JLS 15.27.3 requires the body to throw no checked exception the SAM's `throws` clause does not
permit. `Function.apply` permits none. Give the SAM a `throws E` and the lambda conforms at once.

That fixes the **declaration** problem and moves the **handling** problem one layer out, into
whatever turns a `CheckedFunction` back into a `Function` — which is why this is a workaround and not
a solution. The adapter must do *something* with `E`, and every available something has a cost.

### Why the type parameter, and not `throws Exception`

The obvious simplification is `interface LossyCheckedFunction<T,R> { R apply(T) throws Exception; }`
— one fewer type parameter, same compile fix, and it costs you the exception's identity. With
`E extends Exception` the compiler **infers** `E` at the call site from the method reference's own
`throws` clause, so an adapter can declare a parameter typed in terms of `E` and the caller's lambda
receives the precise checked type with its accessors intact. Compile the same call against the
`throws Exception` variant and the lift lambda receives a bare `Exception`:

```java
static Function<StakeRequest, StakeSplit> build() {
    return unchecked(ReserveDemo::reserveStake,
                     e -> new StakeReservationException(e));
}
```

```console
LossyAdapter.java:24: error: incompatible types: Exception cannot be converted to InsufficientFundsException
                         e -> new StakeReservationException(e));
                                                            ^
Note: Some messages have been simplified; recompile with -Xdiags:verbose to get full output
1 error
```

`StakeReservationException`'s constructor wants an `InsufficientFundsException`. Under the inferred
`E` it gets one; under `throws Exception` the type is gone and the only repair is a cast the
compiler cannot check. **That is the whole argument for the third type parameter.**

### The interface

```java
/** The one thing java.util.function.Function will not give you: a throws clause on the SAM.
 *  E is a type parameter, not Exception, so the call site infers the precise thrown type. */
@FunctionalInterface
interface CheckedFunction<T, R, E extends Exception> {
    R apply(T input) throws E;
}
```

Three deliberate choices. `E extends Exception`, not `extends Throwable` — an adapter that swallows
`Error` is a bug factory, and the bound keeps `OutOfMemoryError` out of the type. No `default`
methods: `andThen` would have to decide whose `E` survives when two differ, and that belongs to the
composing code. And `@FunctionalInterface` makes the SAM count compiler-enforced, not conventional.

### The adapters

```java
import java.util.function.Function;

/** Purpose-made unchecked wrapper. Keeps the checked type reachable through getCause()
 *  AND through a typed accessor, so no caller has to instanceof-chain blindly. */
class StakeReservationException extends RuntimeException {
    private static final long serialVersionUID = 1L;
    private final InsufficientFundsException reason;
    StakeReservationException(InsufficientFundsException reason) {
        super(reason.getMessage(), reason);
        this.reason = reason;
    }
    InsufficientFundsException reason() { return reason; }
}

record Attempt<T, R>(T input, R value, Exception failure) {
    static <T, R> Attempt<T, R> ok(T input, R value) { return new Attempt<>(input, value, null); }
    static <T, R> Attempt<T, R> failed(T input, Exception failure) { return new Attempt<>(input, null, failure); }
    boolean ok() { return failure == null; }
}

final class CheckedFunctions {

    private CheckedFunctions() {}

    /** Adapter 1a: wrap into a bare RuntimeException. Compiles, loses the type. */
    static <T, R, E extends Exception> Function<T, R> uncheckedBare(CheckedFunction<T, R, E> f) {
        return input -> {
            try {
                return f.apply(input);
            } catch (RuntimeException e) {
                throw e;
            } catch (Exception e) {
                throw new RuntimeException(e);
            }
        };
    }

    /** Adapter 1b: wrap through a caller-supplied lift. E is INFERRED, so the lift lambda
     *  receives the precise checked type and can call its typed accessors with no cast. */
    static <T, R, E extends Exception> Function<T, R> unchecked(
            CheckedFunction<T, R, E> f,
            Function<? super E, ? extends RuntimeException> lift) {
        return input -> {
            try {
                return f.apply(input);
            } catch (RuntimeException e) {
                throw e;
            } catch (Exception e) {
                @SuppressWarnings("unchecked") E precise = (E) e;
                throw lift.apply(precise);
            }
        };
    }

    /** Adapter 2: collect instead of throwing. The traversal always completes. */
    static <T, R, E extends Exception> Function<T, Attempt<T, R>> attempting(CheckedFunction<T, R, E> f) {
        return input -> {
            try {
                return Attempt.ok(input, f.apply(input));
            } catch (Exception e) {
                return Attempt.failed(input, e);
            }
        };
    }
}
```

**Gotcha, and it is the reason all three adapters say `catch (Exception e)`:** you cannot catch a
type variable. `catch (E e)` is a compile error, because JLS 14.20 requires the catch parameter's
type to be a class type and `E` is not one:

```console
CatchTypeVariable.java:5: error: unexpected type
        } catch (E e) {
                 ^
  required: class
  found:    type parameter E
```

So adapter 1b catches `Exception`, rethrows any `RuntimeException` untouched (a
`NullPointerException` from inside `reserveStake` is not the domain failure and must not be lifted),
and casts the remainder to `E`. That cast is unchecked and erasure deletes it, so it cannot fail —
safe *only because* `E` was inferred from the SAM, so no other checked type can reach it. The one way
to break that is to sneak-throw a different checked exception through `reserveStake`, §4.6.6's
problem and one more reason not to.

### Run it

```java
/** Genuinely checked. Bonus takes min(BONUS_AVAILABLE, 10% of stake), rounded DOWN;
 *  cash covers the remainder. Stakeable = cash available + bonus available. */
static StakeSplit reserveStake(StakeRequest request) throws InsufficientFundsException {
    Money cash = CASH_AVAILABLE.get(request.clientId());
    Money stakeable = new Money(cash.amount().add(BONUS_AVAILABLE.amount()), Money.GBP);
    if (stakeable.lessThan(request.stake())) {
        throw new InsufficientFundsException(request.clientId(), request.stake(), stakeable);
    }
    BigDecimal tenPercent = request.stake().amount()
            .multiply(new BigDecimal("0.10")).setScale(2, RoundingMode.DOWN);
    BigDecimal bonusLeg = tenPercent.min(BONUS_AVAILABLE.amount());
    BigDecimal cashLeg = request.stake().amount().subtract(bonusLeg);
    return new StakeSplit(new Money(bonusLeg, Money.GBP), new Money(cashLeg, Money.GBP));
}

public static void main(String[] args) {
    List<StakeRequest> batch = List.of(
            new StakeRequest(ClientId.of("client-A"), Money.gbp("3.33"), 1L),
            new StakeRequest(ClientId.of("client-A"), Money.gbp("4.20"), 2L),
            new StakeRequest(ClientId.of("client-B"), Money.gbp("9.99"), 3L),
            new StakeRequest(ClientId.of("client-A"), Money.gbp("1.00"), 4L));

    System.out.println("== the lambda now compiles: CheckedFunction has a throws clause ==");
    CheckedFunction<StakeRequest, StakeSplit, InsufficientFundsException> reserve =
            ReserveDemo::reserveStake;
    System.out.println("SAM target accepted; direct call: " + attempt(reserve, batch.get(0)));

    System.out.println();
    System.out.println("== adapter 1b: unchecked + lift - E inferred, typed accessor in the lift ==");
    Function<StakeRequest, StakeSplit> lifted =
            CheckedFunctions.unchecked(reserve, e -> new StakeReservationException(e));
    try {
        List<StakeSplit> splits = batch.stream().map(lifted).toList();
        System.out.println("unreachable: " + splits);
    } catch (StakeReservationException e) {
        System.out.println("caught by NAME: " + e.getClass().getSimpleName());
        System.out.println("  typed reason:  " + e.reason().getClass().getSimpleName());
        System.out.println("  shortfall:     " + e.reason().shortfall());
        System.out.println("  frames:        " + e.getStackTrace().length
                           + ", top = " + e.getStackTrace()[0]);
    }

    System.out.println();
    System.out.println("== the traversal is half-done: nothing before row 3 was returned ==");
    List<StakeSplit> partial = new ArrayList<>();
    try {
        batch.stream().map(lifted).forEach(partial::add);
    } catch (StakeReservationException e) {
        System.out.println("aborted at row 3; partial holds " + partial.size()
                           + " reservations that were computed and then discarded by the caller");
    }

    System.out.println();
    System.out.println("== adapter 2: attempting over a CheckedFunction - 7,000 rows, no abort ==");
    List<StakeRequest> paymentRun = new ArrayList<>(7000);
    for (int i = 0; i < 7000; i++) {
        paymentRun.add(new StakeRequest(
                ClientId.of(i % 500 == 0 ? "client-B" : "client-A"), Money.gbp("4.20"), i));
    }
    Map<Boolean, List<Attempt<StakeRequest, StakeSplit>>> partitioned = paymentRun.stream()
            .map(CheckedFunctions.attempting(ReserveDemo::reserveStake))
            .collect(Collectors.partitioningBy(Attempt::ok));
    System.out.println("succeeded: " + partitioned.get(true).size());
    System.out.println("failed:    " + partitioned.get(false).size());
    System.out.println("first failure row " + partitioned.get(false).get(0).input().roundSequence()
                       + " -> " + partitioned.get(false).get(0).failure().getMessage());

    System.out.println();
    System.out.println("== parallel: which thread does the failure arrive from? ==");
    System.out.println("caller thread = " + Thread.currentThread().getName());
    List<StakeRequest> lateFailure = new ArrayList<>(7000);
    for (int i = 0; i < 7000; i++) {
        lateFailure.add(new StakeRequest(
                ClientId.of(i == 6999 ? "client-B" : "client-A"), Money.gbp("4.20"), i));
    }
    try {
        lateFailure.parallelStream().map(lifted).forEach(s -> {});
    } catch (StakeReservationException e) {
        System.out.println("captured on   = " + e.reason().capturedOn());
        System.out.println("rethrown into = " + Thread.currentThread().getName());
    }
}

static String attempt(CheckedFunction<StakeRequest, StakeSplit, InsufficientFundsException> f,
                      StakeRequest r) {
    try {
        return f.apply(r).toString();
    } catch (InsufficientFundsException e) {
        return "rejected: " + e.getMessage();
    }
}
```

Real output, Oracle JDK 21.0.7 (build 21.0.7+8-LTS-245), macOS aarch64:

```console
== the lambda now compiles: CheckedFunction has a throws clause ==
SAM target accepted; direct call: split[bonus=GBP 0.33, cash=GBP 3.00]

== adapter 1b: unchecked + lift - E inferred, typed accessor in the lift ==
caught by NAME: StakeReservationException
  typed reason:  InsufficientFundsException
  shortfall:     GBP 7.49
  frames:        12, top = ReserveDemo.lambda$main$0(ReserveDemo.java:48)

== the traversal is half-done: nothing before row 3 was returned ==
aborted at row 3; partial holds 2 reservations that were computed and then discarded by the caller

== adapter 2: attempting over a CheckedFunction - 7,000 rows, no abort ==
succeeded: 6986
failed:    14
first failure row 0 -> DOMAIN-901 INSUFFICIENT_FUNDS shortfall=GBP 1.70 stakeable=GBP 2.50 client=8b8575e4

== parallel: which thread does the failure arrive from? ==
caller thread = main
captured on   = ForkJoinPool.commonPool-worker-9
rethrown into = main
```

Line 2 is the canonical rounding split — a stake of **3.33** becomes **0.33 bonus + 3.00 cash** —
and `shortfall:  GBP 7.49` is the typed accessor working through the inferred `E`, no cast, no regex
over a message.

### Which unchecked type, and it matters

`uncheckedBare` and `unchecked` (adapters 1a and 1b) differ only in what the caller can catch:

```console
thrown type:  java.lang.RuntimeException
message:      InsufficientFundsException: DOMAIN-901 INSUFFICIENT_FUNDS shortfall=GBP 7.49 stakeable=GBP 2.50 client=8b8575e4
cause type:   InsufficientFundsException
shortfall reachable only by cast: GBP 7.49
thrown type:  StakeReservationException
shortfall reachable by accessor: GBP 7.49
```

A bare `RuntimeException` is catchable, but only as `RuntimeException` — which every other bug in the
pipeline also is. The handler has to `getCause()`, `instanceof`, then cast, with no compiler help
when a second checked type starts arriving. **Ship the purpose-made wrapper:** eight lines, and it
buys `catch (StakeReservationException e)` plus `e.reason().shortfall()`. The JDK sets exactly this
precedent with `UncheckedIOException` wrapping `IOException`.

### Three routes, compared

| | `unchecked(CheckedFunction, lift)` | `attempting(CheckedFunction)` | `Result<T,E>` (order 6) |
|---|---|---|---|
| Return type of the mapped stage | `R` — pipeline unchanged | `Attempt<T,R>` — one extra unwrap | `Result<R,E>` — one extra unwrap |
| Failure channel | thrown, unchecked | value, per element | value, per element |
| Traversal on first failure | **aborts**, partially applied | completes all 7,000 rows | completes |
| Which element failed | lost unless the wrapper carries it | `Attempt.input()`, always | only if `E` carries it |
| Compiler forces handling | no | no (ignoring `Attempt` compiles) | no (ignoring `Result` compiles) |
| Retains the checked type | yes, through `E` and the wrapper | yes, in `failure()` | yes, as `E` |
| Needs the callee rewritten | no — takes any `throws E` method | no | **yes** — signature changes |
| Stack trace | one extra frame at the adapter | preserved on the stored exception | none captured |

**What I would ship.** Adapter 1b with a purpose-made wrapper for a **request-scoped** operation
where the first failure should abort the request anyway — one stake reservation behind an HTTP call,
where 400-and-explain is the whole response. Adapter 2 for anything **batch**: the `PaymentRun` of 7k
bank withdrawals, the 6.5k/day bank-deposit file, any nightly reconciliation. `Result` when the
operation is *yours to design* and failure is an ordinary outcome — it is the only one of the three
the caller cannot forget exists at the type level, and the only one that composes with `flatMap`.

### What the adapter costs

**The compiler's obligation on the caller is gone.** Before the adapter, `javac` told every caller
of `reserveStake` that reservation can fail. After it, nobody is told — the difference between a
handler written at design time and one written after the incident report.

**The stack trace gains a frame that is not where the failure happened.**

```console
StakeReservationException: DOMAIN-901 INSUFFICIENT_FUNDS shortfall=GBP 7.49 stakeable=GBP 2.50 client=8b8575e4
	at CheckedFunctions.lambda$unchecked$1(CheckedFunctions.java:50)
	at java.base/java.util.stream.ReferencePipeline$3$1.accept(ReferencePipeline.java:197)
	at java.base/java.util.AbstractList$RandomAccessSpliterator.forEachRemaining(AbstractList.java:722)
	at java.base/java.util.stream.AbstractPipeline.copyInto(AbstractPipeline.java:509)
	at java.base/java.util.stream.AbstractPipeline.wrapAndCopyInto(AbstractPipeline.java:499)
	at java.base/java.util.stream.AbstractPipeline.evaluate(AbstractPipeline.java:575)
	at java.base/java.util.stream.AbstractPipeline.evaluateToArrayNode(AbstractPipeline.java:260)
	at java.base/java.util.stream.ReferencePipeline.toArray(ReferencePipeline.java:616)
	at java.base/java.util.stream.ReferencePipeline.toArray(ReferencePipeline.java:622)
	at java.base/java.util.stream.ReferencePipeline.toList(ReferencePipeline.java:627)
	at TraceDemo.main(TraceDemo.java:12)
Caused by: InsufficientFundsException: DOMAIN-901 INSUFFICIENT_FUNDS shortfall=GBP 7.49 stakeable=GBP 2.50 client=8b8575e4
	at ReserveDemo.reserveStake(ReserveDemo.java:24)
	at CheckedFunctions.lambda$unchecked$1(CheckedFunctions.java:45)
	... 10 more
```

The top frame is `CheckedFunctions.lambda$unchecked$1:50` — the adapter's `throw`. The actual
failure is `ReserveDemo.reserveStake:24`, eleven lines down under `Caused by:`; the trailing
`10 more` is the JVM folding frames shared with the enclosing trace. On-call reads the first line,
and the first line is the adapter. Keeping the cause chain is what makes this survivable, which is
why `super(reason.getMessage(), reason)` passes `reason` as the cause rather than stringifying it.
[`../exceptions/03b-internals-stack-trace-capture.md`](../exceptions/03b-internals-stack-trace-capture.md)
owns `fillInStackTrace` and the lazy `backtrace`.

**A throwing pipeline leaves the traversal half-done, with no partial result.** The `forEach` run
above added 2 reservations to `partial` before row 3 threw, and `toList()` on the same data returned
nothing at all. For a `PaymentRun` of 7k bank withdrawals that is a correctness problem, not an
aesthetic one: the rows before the failure were computed, some may already have written ledger
entries in a non-transactional step, and the caller has no list to reconcile against. Adapter 2
exists precisely so the traversal cannot end in that state.

**On a parallel stream the exception surfaces from an arbitrary worker.** The captured run shows
`captured on = ForkJoinPool.commonPool-worker-9`, `rethrown into = main` — the
`InsufficientFundsException` recorded `Thread.currentThread().getName()` at construction on a
common-pool worker, and `ForkJoinTask` rethrew it into the submitter. It is not stable across runs;
three consecutive runs of identical code reported `captured on` as
`ForkJoinPool.commonPool-worker-6`, then `main`, then `ForkJoinPool.commonPool-worker-3`.

Two consequences for diagnosis. Any per-thread context — an MDC, a request id in a `ThreadLocal` —
is populated on the submitter and absent on the worker, so the failure's log line loses its
correlation id. And with `main` itself a legal answer (the common pool uses the caller as a worker),
a bug that only appears on a real worker reproduces intermittently. Both disappear under adapter 2,
because the exception comes back as a value beside its `input()` rather than as an unwind across a
thread boundary.

> A `CheckedFunction<T,R,E>` makes a checked exception *declarable* across a functional-interface
> boundary; the adapter that converts it back to a `Function` is where you choose what the exception
> *becomes*, and there is no choice there that preserves the compiler's obligation on the caller.

### Diff vs the real one

The nearest real things are `java.util.function.Function` and the JDK's own crossings of this
boundary, chiefly `UncheckedIOException`.

| Axis | This build | The JDK | Why |
|---|---|---|---|
| Edge cases | `RuntimeException` rethrown untouched; `Error` excluded by the `E extends Exception` bound; a sneak-thrown foreign checked type would reach the `(E)` cast and be lifted wrongly | `Function` has no failure channel at all, so no edge cases to get wrong; `UncheckedIOException` accepts only `IOException` in its constructor, enforced at compile time | the JDK narrows the wrapper's constructor instead of generifying the adapter — fewer type parameters, one exception type |
| Intrinsics | none; the adapter is one `invokeinterface` inside a lambda body | none either — `Function.apply` is an ordinary interface call, but `LambdaMetafactory` spins the implementation class so the JIT sees a monomorphic call site per capture | both rely on C2 inlining, not on an intrinsic |
| Serialization | `CheckedFunction` is not `Serializable`; `StakeReservationException` declares `serialVersionUID = 1L` but its `reason` field is only serializable if the trimmed exception's context values are | `java.util.function` interfaces are not `Serializable` either (you cast to `Serializable & Function` to force it); `UncheckedIOException` has a `readObject` that **rejects** a null or non-`IOException` cause | the JDK defends the invariant across deserialization; this build does not, and would need the same `readObject` guard to |
| Null policy | undefined — `f.apply(null)` is the callee's problem, and `lift` returning `null` throws `NullPointerException` at the `throw` with no useful message | `Objects.requireNonNull` on every `Function` argument in the JDK's own combinators (`andThen`, `compose`) | a production adapter should `requireNonNull` both arguments in the factory, not in the returned lambda, so the failure names the caller |
| Thread safety | the returned `Function` is stateless and safe to share; adapter 2 is safe under a parallel stream because it returns a value instead of mutating a sink | `Function` carries no state contract; `Collectors.partitioningBy` supplies the thread-safe accumulation | the reason adapter 2 returns `Attempt` rather than writing into a shared failure list — a shared `ArrayList` sink under `parallelStream` is a data race |
| Allocation tricks | one `StakeReservationException` per failure (with a full stack capture); one `Attempt` record per **element** in adapter 2 — 7,000 allocations for 7,000 rows | the JDK avoids the per-element box entirely by having no failure channel; `IntStream` and friends exist to avoid exactly this kind of per-element wrapper | adapter 2's cost is honest and bounded: one small record per row. At 2.8M stake reservations/day it is not free, and that is the trade for never aborting mid-batch |
| Why the JDK bothers | it does not — there is deliberately no `CheckedFunction` in `java.util.function` | the JDK's position is that a functional interface's `throws` clause is part of its contract, and adding a third type parameter to `Function` would have infected every generic signature that mentions it | so the workaround has to be yours. The JDK's answer for its own crossings is the narrow wrapper (`UncheckedIOException`), which is why the purpose-made wrapper above is the shape to copy |

---

## §4.6.6 `[PROVE]` A sneaky-throw utility, and the argument against it

### The shape

Two instructions of bytecode, and the entire checked-exception system stops applying:

```java
final class SneakyThrow {

    private SneakyThrow() {}

    /** The canonical Java 21 form. E is a type variable bounded by Throwable, the cast is
     *  unchecked, and erasure deletes it - so the throw is never checked against anything. */
    @SuppressWarnings("unchecked")
    static <E extends Throwable> void sneakyThrow(Throwable t) throws E {
        throw (E) t;
    }
}
```

**How it works, in order.** `E` is bounded by `Throwable`, so `throw (E) t;` type-checks; the cast is
unchecked, which is what `@SuppressWarnings` is for. At the **call site** `sneakyThrow` takes no
explicit type argument and its `void` result constrains nothing, so JLS 18.1.3 leaves `E` with only
its bound, and JLS 18.4 resolves such a variable in a `throws` position to **`RuntimeException`** —
a specific rule about `throws`-clause inference, not a general default. `javac` therefore sees a call
that throws only `RuntimeException`: no `throws` clause, no `catch`. Erasure then removes the cast,
and at runtime the `athrow` throws whatever object it was handed.

### Prove it runs

```java
/** Signature declares NOTHING. No throws clause, no unchecked wrapper, no cast. */
static StakeSplit reserveStakeSneakily(StakeRequest request) {
    Money stakeable = Money.gbp("2.50");
    if (stakeable.lessThan(request.stake())) {
        SneakyThrow.sneakyThrow(
                new InsufficientFundsException(request.clientId(), request.stake(), stakeable));
    }
    return new StakeSplit(Money.gbp("0.00"), request.stake());
}

public static void main(String[] args) {
    StakeRequest request = new StakeRequest(ClientId.of("client-B"), Money.gbp("9.99"), 3L);
    System.out.println("signature of reserveStakeSneakily declares: (no throws clause)");
    try {
        System.out.println(reserveStakeSneakily(request));
    } catch (Exception e) {
        System.out.println("arrived as: " + e.getClass().getName());
        System.out.println("is it checked? " + !(e instanceof RuntimeException));
        System.out.println("message:    " + e.getMessage());
        if (e instanceof InsufficientFundsException ife) {
            System.out.println("shortfall (after instanceof, the only route left): " + ife.shortfall());
        }
    }
}
```

```console
signature of reserveStakeSneakily declares: (no throws clause)
arrived as: InsufficientFundsException
is it checked? true
message:    DOMAIN-901 INSUFFICIENT_FUNDS shortfall=GBP 7.49 stakeable=GBP 2.50 client=8b8575e4
shortfall (after instanceof, the only route left): GBP 7.49
```

A checked `InsufficientFundsException` left a method that declares nothing, unwrapped, with its
context and typed accessors intact. No `ClassCastException`, no `UndeclaredThrowableException`.

### `[BYTECODE]` Read the method

```console
$ javap -v -p SneakyThrow
  static <E extends java.lang.Throwable> void sneakyThrow(java.lang.Throwable) throws E;
    descriptor: (Ljava/lang/Throwable;)V
    flags: (0x0008) ACC_STATIC
    Code:
      stack=1, locals=1, args_size=1
         0: aload_0
         1: athrow
      LineNumberTable:
        line 9: 0
    Exceptions:
      throws java.lang.Throwable
    Signature: #17                          // <E:Ljava/lang/Throwable;>(Ljava/lang/Throwable;)V^TE;
```

Instruction by instruction, and there are only two: `0: aload_0` pushes the `Throwable` parameter,
`1: athrow` throws it.

**There is no `checkcast`.** That is the whole trick, visible rather than argued. `(E) t` erases to
`(Throwable) t`, the operand is already statically `Throwable`, so `javac` emits nothing for the cast
and there is no runtime check to fail. Note too that the `descriptor` is `(Ljava/lang/Throwable;)V`
with no trace of `E`, and the `Exceptions` attribute records only the erasure,
`throws java.lang.Throwable`; the generic truth lives solely in the `Signature` attribute, where
`^TE` is the thrown type variable. The JVM reads the descriptor and never enforces `throws` at all —
JVMS 4.7.5 makes `Exceptions` informational. **Checked exceptions are a `javac` rule, not a JVM
rule**, and the `Signature`/`descriptor` split above is where you can see it. Erasure itself is
[`../generics/03-internals-erasure.md`](../generics/03-internals-erasure.md).

The call site is equally bare:

```console
  static StakeSplit reserveStakeSneakily(StakeRequest);
    Code:
      30: invokespecial #31                 // Method InsufficientFundsException."<init>":(LClientId;LMoney;LMoney;)V
      33: invokestatic  #34                 // Method SneakyThrow.sneakyThrow:(Ljava/lang/Throwable;)V
      36: new           #40                 // class StakeSplit
```

Instructions 0 to 29 are the ordinary balance check and the exception's argument construction.
`33: invokestatic` is a plain static call returning `void`: no `checkcast`, no exception table entry,
and fall-through code laid out at `36` as though `sneakyThrow` returns normally, which it never does.
Nothing in the caller's bytecode records that a checked exception can leave.

### The argument against

#### 1. A caller cannot catch it by type. This is the decisive cost.

```java
final class SneakyCatch {
    static void settle(StakeRequest request) {
        try {
            SneakyDemo.reserveStakeSneakily(request);
        } catch (InsufficientFundsException e) {
            System.out.println("offer a smaller stake: " + e.shortfall());
        }
    }
}
```

```console
SneakyCatch.java:5: error: exception InsufficientFundsException is never thrown in body of corresponding try statement
        } catch (InsufficientFundsException e) {
          ^
1 error
```

JLS 11.2.3 makes it an error to catch a checked exception type the try block cannot throw, and
"cannot throw" is decided from declared signatures — which say nothing. So the exception **exists at
runtime and is uncatchable by name at compile time**, and the only handler that compiles is
`catch (Exception e)` plus an `instanceof`, exactly as the demo above had to write it. Work that
through: the exception hierarchy in order 15 made `InsufficientFundsException` and
`RestrictedActionException` separate types precisely so a caller could write two catch clauses with
two recoveries — offer a smaller stake for one, surface `STAKE_BLOCKED` for the other. Sneaky-throw
collapses both into one broad catch plus a manual dispatch chain the compiler cannot check for
exhaustiveness, and that broad catch also swallows the `NullPointerException` from the bug three
frames down. The technique does not merely weaken the type system; it forces a second defect on
every caller.

#### 2. It defeats the tooling, not just the compiler.

Everything that reasons about declared exceptions reads the `throws` clause: `@throws` Javadoc, IDE
inspections for unhandled checked exceptions, SpotBugs and Error Prone rules over exception flow,
and any generated client stub that maps declared exceptions to error responses. All of them see a
method that cannot fail. The `Exceptions` attribute on `reserveStakeSneakily` records nothing at all
— the only entry anywhere is `throws java.lang.Throwable` on `sneakyThrow` itself, verified above,
which no tool attributes to the caller. The loss is not that the compiler stops nagging; it is that
every automated reader of the codebase is now wrong about this method.

#### 3. It is invisible at the call site, which is worse than a wrap.

Adapter 1b also removes the compiler's obligation — but it leaves evidence. A reader can see
`StakeReservationException` in the wrapper type, in the Javadoc, in the trace's first line, and can
grep for it. Sneaky-throw leaves nothing: the signature is clean, the bytecode has no exception
table entry, and the only textual trace is the word `sneakyThrow` inside the callee's body, which
the caller never reads. A wrap is a lie you can find; this is a lie you cannot.

#### 4. Where it is used anyway, honestly.

It is not a fringe trick. Lombok's `@SneakyThrows` is this pattern with a compile-time source
rewrite, and it is widely used; several bytecode and mocking libraries carry an internal equivalent.
What makes those uses defensible is a **closed boundary plus a stated contract**: the framework owns
both the throw and the handler around it, so no application programmer is ever the caller who needs
`catch (SpecificType e)`, and the annotation is opt-in at the site that does the hiding, so the
hiding is visible in the source a reader is already looking at. The narrow legitimate case is
rethrowing a `Throwable` harvested from another thread or from reflection, where the static type is
unknown and wrapping would obscure something already correct.

None of that transfers to application code. In `PaymentService` or `FundsLedger` the boundary is
open — any teammate becomes the caller next quarter without reading the callee — and the contract
lives in a comment nobody is obliged to read. A trick whose safety depends on nobody being surprised
is not safe in code many people edit.

### Recommendation, ranked

1. **Declare the exception.** The only option that keeps `catch (InsufficientFundsException e)`
   legal and the tooling correct, and it costs one `throws` clause. Do this unless a
   functional-interface boundary makes it impossible.
2. **Wrap it in a purpose-made unchecked type.** `StakeReservationException`, adapter 1b, cause
   chained, typed accessor. Where a SAM boundary blocks option 1 and the failure aborts the request.
3. **Return `Result<T,E>`.** Order 6's type, when the operation is yours to design and failure is an
   ordinary outcome — a `Verdict`, a rejected stake, a `GateSet` that does not hold.
4. **Sneaky-throw.** Last, and in application code, not at all.

**Is there a case where it is least-bad?** One, narrowly: rethrowing a `Throwable` you already hold
whose static type you do not know — recovered from a `Future`, a reflective invocation target, or a
worker thread — from a frame that cannot declare it, where wrapping would add a meaningless frame to
an exception that was already correct. That is a two-line utility at a framework seam, called once.
Every other use, including annotating a service method to avoid typing `throws`, buys keystrokes
with the caller's ability to handle the failure.

> Sneaky-throw works because checked exceptions are enforced by `javac` and not by the JVM; it is a
> bad trade because the *catch* rule is also enforced by `javac`, so the exception that escapes is
> one nobody downstream is permitted to name.

### Diff vs the real one

The real comparators are Lombok's `@SneakyThrows` and the JDK's own rethrow helpers, chiefly
`ForkJoinTask.rethrow`.

| Axis | This build | The real one | Why |
|---|---|---|---|
| Edge cases | accepts any `Throwable`, including `Error` and `null` — `sneakyThrow(null)` throws `NullPointerException` from the `athrow`, which is confusing but not silent | **Unverified:** Lombok's `@SneakyThrows` restricts the *declared* set to the types you list on the annotation, and generates the throw only for those; `ForkJoinTask.rethrow` handles the `Error` / `RuntimeException` / wrap split explicitly | narrowing the accepted type is the cheap defence this build skips; a production version should reject `Error` |
| Intrinsics | none — `aload_0`, `athrow`, verified above | none either; there is nothing to intrinsify. Lombok's version is not a call at all: the annotation processor inlines a `try`/`catch`/rethrow into the method body at compile time | Lombok's inlining means there is no `sneakyThrow` frame in the trace; this build adds one |
| Serialization | irrelevant — `SneakyThrow` is a stateless final utility with a private constructor and is never instantiated | same | no state, no serial form, on either side |
| Null policy | none. `null` in, `NullPointerException` out from the wrong place | Lombok cannot produce a null throwable because it generates the `catch` parameter | this build should `Objects.requireNonNull(t)`; the omission is the honest gap |
| Thread safety | fully safe: no state, no synchronisation, reentrant | same | statelessness is the whole reason both are safe |
| Allocation tricks | zero allocation — it rethrows an existing object rather than wrapping. This is its one genuine advantage over option 2: no wrapper instance, no second stack capture | Lombok likewise allocates nothing; `ForkJoinTask` does allocate when it has to wrap | the saving is one small object per failure, which at 140 chargebacks/day is worth nothing and at 1,200 stake reservations/sec is still worth nothing next to the diagnosis cost |
| Why the JDK bothers | the JDK does not expose a public `sneakyThrow` at all | the pattern exists only because JLS 18.4's `throws`-inference rule makes it expressible; it was never a design goal, and no JEP has proposed blessing it | its absence from the public API is itself the JDK's opinion on it |

The section-wide §4.6 diff table (leaf 4.6.9) and the `Cleaner`-based holder (leaf 4.6.7) are in
[`03j-cleaner-and-diff.md`](03j-cleaner-and-diff.md).

---

## Pitfalls

### Believing a checked exception can be declared on a lambda passed to `Function`

**Wrong**

```java
static List<StakeSplit> reserveAll(List<StakeRequest> batch) throws InsufficientFundsException {
    return batch.stream()
                .map(request -> ReserveDemo.reserveStake(request))
                .toList();
}
```

```console
BlockedLambda.java:6: error: unreported exception InsufficientFundsException; must be caught or declared to be thrown
                    .map(request -> ReserveDemo.reserveStake(request))
                                                            ^
1 error
```

The enclosing method declares `throws InsufficientFundsException` and it changes nothing.

**Right**

```java
static List<StakeSplit> reserveAll(List<StakeRequest> batch) {
    return batch.stream()
                .map(CheckedFunctions.unchecked(ReserveDemo::reserveStake,
                                                StakeReservationException::new))
                .toList();
}
```

The lambda body compiles into a method implementing `Function.apply`, whose `throws` clause is
empty; JLS 15.27.3 checks the body against *that* clause, not the enclosing method's.

**Why people believe it:** `throws` on an enclosing method covers every ordinary statement inside it,
including a nested block or a `for` body. A lambda looks like a block and is not one — it is a
separate method with its own signature, and that is the single fact this pitfall turns on.

### Believing sneaky-throw is caught by `catch (TheCheckedType e)`

**Wrong**

```java
try {
    SneakyDemo.reserveStakeSneakily(request);
} catch (InsufficientFundsException e) {
    System.out.println("offer a smaller stake: " + e.shortfall());
}
```

```console
SneakyCatch.java:5: error: exception InsufficientFundsException is never thrown in body of corresponding try statement
        } catch (InsufficientFundsException e) {
          ^
1 error
```

The exception is genuinely thrown at runtime and the catch clause is still a compile error.

**Right**

```java
try {
    SneakyDemo.reserveStakeSneakily(request);
} catch (Exception e) {
    if (e instanceof InsufficientFundsException ife) {
        System.out.println("offer a smaller stake: " + ife.shortfall());
    } else {
        throw e instanceof RuntimeException re ? re : new IllegalStateException(e);
    }
}
```

Better still: do not sneak-throw. Declare it, or wrap it in `StakeReservationException`.

**Why people believe it:** "the object really is an `InsufficientFundsException` at runtime, and
`catch` matches on the runtime type" — both halves true. The missing half is JLS 11.2.3: catching a
checked type the try block cannot *statically* throw is an error, and sneaky-throw's mechanism is
precisely making the throw statically invisible.

### Believing a stream that throws mid-pipeline leaves nothing half-done

**Wrong**

```java
List<StakeSplit> partial = new ArrayList<>();
batch.stream().map(lifted).forEach(partial::add);
// assumed: either all four rows land in partial, or none do
```

```console
aborted at row 3; partial holds 2 reservations that were computed and then discarded by the caller
```

Rows 1 and 2 were reserved and added, then row 3 threw. No rollback, no partial result handed back —
the caller sees only the exception, and `partial` survives only because it was the caller's own list.

**Right**

```java
Map<Boolean, List<Attempt<StakeRequest, StakeSplit>>> partitioned = paymentRun.stream()
        .map(CheckedFunctions.attempting(ReserveDemo::reserveStake))
        .collect(Collectors.partitioningBy(Attempt::ok));
```

```console
succeeded: 6986
failed:    14
```

Every one of the 7,000 rows is accounted for, each failure paired with its `input()`, and the
traversal cannot end in an unknown state.

**Why people believe it:** `toList()` returning nothing looks atomic, and terminal operations feel
transactional because they hand back one value. They are not: `map` is applied element by element and
each application's side effects have already happened when a later element throws. For a `PaymentRun`
this is the difference between a reconcilable batch and an incident.

---

## Cheat sheet

| Thing | Value |
|---|---|
| Why the lambda is blocked | `Function.apply` has no `throws`; JLS 15.27.3 checks the body against the SAM, not the enclosing method |
| The interface | `interface CheckedFunction<T,R,E extends Exception> { R apply(T) throws E; }` — bound `Exception`, never `Throwable` |
| Why three type parameters | `E` is inferred at the call site, so the adapter's lift gets the precise type |
| `catch (E e)` | compile error — "required: class, found: type parameter E" (JLS 14.20) |
| Adapter shapes | `uncheckedBare` (loses type), `unchecked` + lift (ship this), `attempting` (collects) |
| Which wrapper | purpose-made, cause-chained, with a typed accessor — the `UncheckedIOException` shape |
| 7k-row `PaymentRun` | `attempting`, partition on `Attempt::ok` — traversal always completes |
| Parallel stream | exception constructed on an arbitrary common-pool worker (`main` is legal), rethrown into the submitter; per-thread MDC is lost |
| Sneaky-throw form | `static <E extends Throwable> void sneakyThrow(Throwable t) throws E { throw (E) t; }` |
| Why the call site needs nothing | unconstrained `E` in a `throws` position infers `RuntimeException` (JLS 18.4) |
| Its bytecode | `aload_0; athrow` — **no `checkcast`**, descriptor `(Ljava/lang/Throwable;)V` |
| Enforced by | `javac` only; JVMS 4.7.5 makes `Exceptions` informational |
| Where `E` survives | only the `Signature` attribute: `<E:Ljava/lang/Throwable;>(Ljava/lang/Throwable;)V^TE;` |
| Decisive cost | `catch (InsufficientFundsException e)` is a **compile error** (JLS 11.2.3) |
| Ranked fix | declare it > purpose-made unchecked wrapper > `Result<T,E>` > sneaky-throw (never, in app code) |

---

## Self-test

**Q1.** Why does `CheckedFunction` take three type parameters instead of declaring `throws Exception`?

<details><summary>Answer</summary>

So the checked exception's identity survives into the adapter. With `E extends Exception` the
compiler infers `E` from the method reference's own `throws` clause — for `ReserveDemo::reserveStake`
that is `InsufficientFundsException`. The adapter can then declare a parameter in terms of `E`, such
as `Function<? super E, ? extends RuntimeException> lift`, and the caller's lift lambda receives an
`InsufficientFundsException` with `shortfall()` and `stakeable()` available, no cast. Under
`throws Exception` the lift receives a bare `Exception`, and passing it to a constructor wanting the
specific type fails with "incompatible types: Exception cannot be converted to
InsufficientFundsException" — repairable only by an unchecked cast, which is exactly the guarantee
the type parameter was buying.

</details>

**Q2.** Why is the adapter's catch clause `catch (Exception e)` plus an unchecked cast to `E`, not
`catch (E e)`?

<details><summary>Answer</summary>

`catch (E e)` does not compile. JLS 14.20 requires the catch parameter's type to be a class type and
a type variable is not one: `javac` says "unexpected type / required: class / found: type parameter
E". So the adapter catches `Exception`, rethrows any `RuntimeException` untouched (so an unrelated
`NullPointerException` is not lifted as a domain failure), and casts the remainder to `E`. That cast
is unchecked and erasure deletes it, so it cannot throw — sound only because `E` was inferred from
the SAM, meaning no other checked type can arrive. A sneak-thrown foreign checked exception inside
the callee would violate that, which is one more reason not to use one.

</details>

**Q3.** Why does `throw (E) t;` inside `sneakyThrow` let a checked exception escape a method that
declares nothing?

<details><summary>Answer</summary>

Two independent facts compose. At the call site `sneakyThrow` takes no explicit type argument and
its `void` result constrains nothing, so `E` is an unconstrained inference variable bounded by
`Throwable`, and JLS 18.4 resolves such a variable in a `throws` position to `RuntimeException` —
`javac` therefore believes the call can throw only that, and requires neither a `throws` clause nor a
`catch`. Second, erasure removes the cast: `(E) t` erases to `(Throwable) t`, the operand is already
`Throwable`, so no `checkcast` is emitted and the bytecode is `aload_0; athrow`. At runtime `athrow`
throws whatever it was handed, and the JVM never checks `throws` anyway (JVMS 4.7.5 makes the
`Exceptions` attribute informational).

</details>

**Q4.** The exception really is an `InsufficientFundsException` at runtime, and `catch` matches on
runtime type. So why is `catch (InsufficientFundsException e)` around a sneaky-throwing call a
compile error?

<details><summary>Answer</summary>

JLS 11.2.3 makes it an error to catch a checked exception type the corresponding try block cannot
throw, and "cannot throw" is computed from declared signatures — which, after sneaky-throw, mention
nothing. `javac` reports "exception InsufficientFundsException is never thrown in body of
corresponding try statement". That is the decisive cost: the exception exists at runtime but is
uncatchable by name at compile time, so the only handler that compiles is `catch (Exception e)` with
an `instanceof` dispatch — which also swallows every unrelated `RuntimeException`, making the broad
catch it forces on you a defect in its own right.

</details>

**Q5.** On a parallel stream, where is the exception constructed and where does it surface, and why
does that matter for diagnosis?

<details><summary>Answer</summary>

On whichever `ForkJoinPool.commonPool` worker processed the failing element — the captured runs show
`-worker-9`, `-worker-6`, `-worker-3` and `main` across runs of identical code, because the common
pool uses the submitting thread as a worker too. `ForkJoinTask` then rethrows into the submitter, so
the `catch` runs on `main` either way. Two diagnostic consequences: any per-thread context (an MDC, a
request id in a `ThreadLocal`) was populated on the submitter and is absent on the worker, so the
failure's log line loses its correlation id; and because `main` is a legal answer, a bug that only
manifests on a real worker reproduces intermittently. Both go away with adapter 2, where the
exception travels back as a value beside its `input()` instead of unwinding across a thread
boundary.

</details>

---

## Open questions

- **Unverified:** the per-row Lombok claims in §4.6.6's diff table (that `@SneakyThrows` inlines a
  `try`/`catch`/rethrow rather than calling a helper, and that it narrows the accepted type to the
  annotation's listed classes). Settled by decompiling a `@SneakyThrows`-annotated class with
  `javap -c` against a current Lombok release; no Lombok jar was available on this machine.
- **Unverified:** whether any JDK-internal class uses the `sneakyThrow` type-variable idiom itself
  (as opposed to `Unsafe.throwException` or an explicit `Error`/`RuntimeException`/wrap split as in
  `ForkJoinTask.rethrow`). Settled by grepping the OpenJDK 21 `src/java.base` tree for a
  `<E extends Throwable>` method whose body is a bare `throw (E)` cast; no local source checkout was
  available for this file.

---

**Leaves covered:** 4.6.5, 4.6.6 (2 leaves)
**Leaves deferred:** none
**Diagrams included:** none
**Target version:** Java 21 LTS
**Lines:** 897
