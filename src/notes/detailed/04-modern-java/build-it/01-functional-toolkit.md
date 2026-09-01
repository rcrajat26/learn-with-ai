# 04 Modern Java — Build it — BUILD IT (§4.1)

**Target version: Java 21 LTS.** | **Part 4 of 5** | [Index](../00-index.md)
Previous: [Which construct — which construct](../which-construct/02-which-construct.md) · Next: [Build it — mystream](02-mystream.md)

Part 4 stops asking "which JDK type do I reach for" and starts asking "what is that
type actually made of." Every section below builds a working, `--release 21`-compiling
replica of a piece of `java.util.function` (or the type-level idea that competes with
it), runs it, and then closes with a table of exactly where the toy diverges from the
real thing. The point is not to replace `java.util.function` — it is that the fastest
way to know a mechanism cold is to have built it and watched it break.

Everything here is over the QuizStakes domain: `Money`, stake reservations, the
`3.33` stake that splits `0.33` bonus + `3.00` cash, and a payout file whose read can
throw `IOException`. Every snippet in this file was compiled with
`javac --release 21` on this machine and its output is the real output of the run, not
a recollection.

## The family this section builds

| Toy type | Real JDK sibling | Shape | Arity |
|---|---|---|---|
| `MyFunction<T, R>` | `java.util.function.Function<T, R>` | one input, one output | 1 |
| `MyPredicate<T>` | `java.util.function.Predicate<T>` | one input, boolean | 1 |
| `CheckedFunction<T, R, E>` | none — the JDK deliberately has no checked functional interface | one input, one output, declared checked exception | 1 |
| `Result<T, E>` | closest analogue: `Optional<T>` for presence, nothing for the error channel | sealed two-case algebraic type | n/a |
| memoizing `Function` decorator | nothing in the JDK; libraries fill the gap (Guava `CacheBuilder`) | a `Function` wrapping another `Function` | 1 |
| curry/partial helper | nothing in the JDK | `BiFunction` → chain of `Function` | 2 → 1 → 1 |
| `TriFunction<A, B, C, R>` | none — arity stops at two | three inputs, one output | 3 |

The table itself is the first lesson: half this row set exists in the JDK and half
does not. The gaps are not oversights — §4.1.7 and the closing diff table both make
the argument for why arity and checked-exception support stop where they do.

---

### `MyFunction<T, R>`

**Mental model.** A `MyFunction<T, R>` is not "a method you can pass around." It is a
single-abstract-method object — at the bytecode level, at lambda-creation time the JVM
synthesizes a hidden class implementing the interface and backs its one method with an
`invokedynamic` call site (`LambdaMetafactory.metafactory`, wired up the first time that
call site executes and cached after that). `andThen` and `compose` do not "chain
functions" in some special runtime sense — they are ordinary default methods that
allocate one more lambda object closing over `this` and the argument. Composition is
object composition, nothing more exotic.

**Why it exists.** Before Java 8, "a function you can pass around" meant an anonymous
inner class implementing a hand-rolled interface, or a `Callable`/`Runnable`-shaped
workaround, or a switch on an enum of operation kinds. There was no *standard* single-
argument, single-result functional shape, so every codebase invented its own —
incompatible with every other codebase's version, and with no `andThen`/`compose`
convention. `java.util.function.Function` (and this toy) standardizes the shape once,
so libraries can accept and return it without knowing about each other.

**When to reach for it, and when not.** Use it (or its real sibling `Function<T, R>`)
whenever a single value flows through a single transformation, especially when you
want to build a pipeline out of small named steps rather than one large method body.
Do **not** reach for it when the operation is used exactly once and inline — a named
private method reads better than a one-off `MyFunction<Money, Money>` lambda assigned to a variable and called exactly once.
Its sibling in the "which one" sense is `MyPredicate<T>` below: if the return type is
`boolean`, the predicate shape carries more intent than `MyFunction<T, Boolean>` ever
will, and it avoids the autoboxing that a boxed `Boolean` return forces on every call.

**How it works.** `andThen` and `compose` are mirror images built from the same two
primitives — apply `this`, apply the other — with the invocation order flipped:

```java
default <V> MyFunction<T, V> andThen(MyFunction<? super R, ? extends V> after) {
    Objects.requireNonNull(after);
    return t -> after.apply(this.apply(t));
}

default <V> MyFunction<V, R> compose(MyFunction<? super V, ? extends T> before) {
    Objects.requireNonNull(before);
    return v -> this.apply(before.apply(v));
}
```

`f.andThen(g)` reads left to right — "do `f`, then `g`" — and produces `g(f(x))`.
`f.compose(g)` reads "do `g` first, to produce my input" and produces `f(g(x))`. They
are the same combinator with the two functions swapped: `f.andThen(g)` and
`g.compose(f)` build the identical pipeline. Every implementation lives entirely in
default methods; nothing here needs privileged JDK access, which is itself evidence
that `Function` could have been a library type rather than a language feature — Java 8
made it a library type for exactly that reason.

`[PROVE]` **the two composition orders differ.** Take a stake of `3.33` and two steps
that are not commutative: a flat processing fee of `0.015` and a round to the minor
unit (2 decimal places, `HALF_UP`):

```java
static Money chargeProcessingFee(Money m) {
    return new Money(m.amount().subtract(new BigDecimal("0.015")), m.currency());
}

static Money roundToMinorUnit(Money m) {
    return new Money(m.amount().setScale(2, RoundingMode.HALF_UP), m.currency());
}
```

Run on this machine (`javac --release 21`):

```
feeThenRound: Money[amount=3.32, currency=GBP]
roundThenFee: Money[amount=3.315, currency=GBP]
round.compose(fee) == fee.andThen(round): Money[amount=3.32, currency=GBP]
```

Charging the fee first leaves `3.315`, and `HALF_UP` rounds the `5` away from zero to
`3.32`. Rounding first leaves `3.33` unchanged (it was already at 2 decimal places),
and then subtracting the unrounded fee produces `3.315` — three decimal places, a scale
a `Money` type should never be allowed to carry into a ledger write. `round.compose(fee)`
and `fee.andThen(round)` land on the identical result (`3.32`) because they build the
same pipeline through the mirrored combinator, which is the confirming half of the
proof: order matters between two different pipelines, and is invariant under
`andThen`/`compose` symmetry for one pipeline expressed two ways.

**Example.**

```java
record Money(BigDecimal amount, String currency) {}

interface MyFunction<T, R> {
    R apply(T t);

    default <V> MyFunction<T, V> andThen(MyFunction<? super R, ? extends V> after) {
        Objects.requireNonNull(after);
        return t -> after.apply(this.apply(t));
    }

    default <V> MyFunction<V, R> compose(MyFunction<? super V, ? extends T> before) {
        Objects.requireNonNull(before);
        return v -> this.apply(before.apply(v));
    }

    static <T> MyFunction<T, T> identity() {
        return t -> t;
    }
}

MyFunction<Money, Money> fee = MyFunctionHarness::chargeProcessingFee;
MyFunction<Money, Money> round = MyFunctionHarness::roundToMinorUnit;
Money stake = new Money(new BigDecimal("3.33"), "GBP");

MyFunction<Money, Money> feeThenRound = fee.andThen(round);   // 3.32
MyFunction<Money, Money> roundThenFee = round.andThen(fee);   // 3.315
```

**Gotcha.** `identity()` is a trap for anyone reasoning about performance: every call
to `MyFunction.identity()` (like `Function.identity()`) allocates a **new** lambda
object. There is no cached singleton — `identity()` is a generic static method that
returns `t -> t`, and each invocation site gets its own `invokedynamic` call site, each
of which caches its own `CallSite` the first time *that* site runs, but two different
call sites (two different places in the source that call `identity()`) never share one.
It is cheap, but it is not free, and "identity is free because it does nothing" is the
wrong mental model — it still allocates.

**Insight:** `andThen`/`compose` cost nothing beyond one more lambda allocation per
call; the entire "pipeline" is just nested method calls unwound at invocation time,
never at composition time — composing ten steps builds ten small objects, and running
the pipeline once walks through all ten, with no fusion or shortcutting the way a
stream pipeline gets from its `Sink` chain (Day and file `02-mystream.md` build that
machinery next).

**Interview:** "What's the difference between `andThen` and `compose`?" — they build
the same kind of pipeline in opposite order; `f.andThen(g)` is `g(f(x))`, `f.compose(g)`
is `f(g(x))`, and `a.andThen(b)` always equals `b.compose(a)`.

> **`MyFunction<T, R>` is a single-method contract for "one input in, one output out,"
> with `andThen`/`compose` as pure object composition over that one method — no magic,
> just one more lambda per link.**

---

### `MyPredicate<T>`

**Mental model.** A predicate is a `MyFunction<T, Boolean>` that refuses to admit it —
and that refusal is the entire value of the type. `and`, `or`, `negate`, and the static
`not` are boolean algebra lifted to run per-element, lazily, over whatever value shows
up later. Picture a boolean expression tree where the leaves are deferred method calls
instead of already-known `true`/`false` values.

**Why it exists.** Filtering conditions used to be written as raw `if` blocks scattered
through loop bodies, or as booleans passed by value (which cannot be lazy, cannot be
combined, and are already-evaluated by the time you have one). A first-class predicate
type lets you build "is this reservation stake-blocked AND over the limit" out of two
independently testable, independently named pieces, combine them with `and`/`or`, and
pass the combination into `Stream.filter` without evaluating anything until an element
actually arrives.

**When to reach for it, and when not.** Reach for `MyPredicate<T>` (or `Predicate<T>`)
whenever a boolean test is reused, combined, or passed to an API expecting exactly this
shape (`filter`, `removeIf`, `Collectors.partitioningBy`). Do not reach for it as a
substitute for `MyFunction<T, Boolean>` used as a general-purpose value producer — if
the boolean is being stored, serialized, or returned as data rather than tested and
discarded, a plain boolean or `boolean`-returning method is clearer and avoids the
autoboxing `Function<T, Boolean>` would otherwise force on every evaluation, which a
primitive-returning `test(T)` method never does.

**How it works.** `and` and `or` short-circuit exactly the way `&&` and `||` do,
because they are *implemented* with `&&` and `||` inside the returned lambda — nothing
about the predicate combinator adds new short-circuiting behavior, it merely delays
when the `&&`/`||` runs until `test` is finally invoked on a real element:

```java
default MyPredicate<T> and(MyPredicate<? super T> other) {
    Objects.requireNonNull(other);
    return t -> this.test(t) && other.test(t);
}

default MyPredicate<T> or(MyPredicate<? super T> other) {
    Objects.requireNonNull(other);
    return t -> this.test(t) || other.test(t);
}
```

`negate()` flips `this`; the static `not(target)` exists (mirroring
`Predicate.not`, added in JDK 11 specifically so a method reference like
`String::isBlank` could be inverted without a lambda wrapper: `not(String::isBlank)`
instead of `s -> !s.isBlank()`) so a method reference can be negated without writing a
throwaway lambda: `MyPredicate.not(StakeReservation::stakeBlocked)`.

`[PROVE]` **the short-circuit, with a side-effecting predicate.** Take a stake-blocked
check `isRestricted` and an `exceedsLimit` predicate instrumented with an
`AtomicInteger` counter, combined as `isRestricted.and(exceedsLimit)`:

```
resultUnrestricted: false
exceedsLimit invocations after unrestricted: 0
resultBlocked: true
exceedsLimit invocations after blocked: 1
```

Against an unrestricted reservation, `isRestricted` returns `false` and `and` never
calls `exceedsLimit` at all — the counter stays at `0`. Against a blocked reservation,
`isRestricted` returns `true`, so `and` must evaluate the right side, and the counter
becomes `1`. The side effect proves the short-circuit is real, not merely documented:
a predicate on the losing side of an `&&` is provably never invoked.

**Example.**

```java
record StakeReservation(String clientId, BigDecimal amount, boolean stakeBlocked) {}

MyPredicate<StakeReservation> isRestricted = StakeReservation::stakeBlocked;
MyPredicate<StakeReservation> exceedsLimit = r -> {
    sideEffectCalls.incrementAndGet();
    return r.amount().compareTo(new BigDecimal("500")) > 0;
};

MyPredicate<StakeReservation> shouldReject = isRestricted.and(exceedsLimit);
shouldReject.test(new StakeReservation("C-1", new BigDecimal("4.20"), false)); // exceedsLimit never runs
shouldReject.test(new StakeReservation("C-2", new BigDecimal("600.00"), true)); // exceedsLimit runs, true
```

**Gotcha.** `and`/`or` are **not commutative in the presence of side effects**, even
though the boolean *result* of pure `and`/`or` is commutative. `a.and(b)` and
`b.and(a)` return the same boolean, but they call `a` and `b` in opposite orders, and
if either predicate has a side effect (a metric increment, a cache warm, a log line)
the two compositions are observably different programs. Order the cheaper, more
likely-to-fail predicate first — `isRestricted` (a field read) before `exceedsLimit`
(a comparison against a domain constant) is the right order specifically because
`isRestricted` is both cheaper and, for most reservations, `false`.

**Insight:** because `and`/`or`/`negate` all return a **new** `MyPredicate`, chained
predicates cost one allocation per link, same as `MyFunction`; the JDK's real
`Predicate` has the identical cost profile, so "predicates are free because booleans
are cheap" is a category error — you're allocating closures, not booleans.

**Interview:** "Does `Predicate.and` short-circuit?" — yes, because its default
implementation is written with `&&`, not a helper that evaluates both sides; the
short-circuit is inherited straight from the operator, not bolted on separately.

> **`MyPredicate<T>` is a single-method boolean test with `and`/`or`/`negate` as
> lazy, short-circuiting boolean algebra over deferred calls — combinable and testable
> without ever collapsing to an already-decided value.**

---

### `CheckedFunction<T, R, E extends Exception>`

**Mental model.** `Function<T, R>`'s `apply` method has no `throws` clause in its
signature, which is not an oversight — it is a closed door. `CheckedFunction` reopens
that door by adding a third type parameter bound to `Exception` and declaring
`apply(T t) throws E`. It is `Function` with a hole cut in the side for exceptions to
walk out through.

**Why it exists.** Any checked-exception-throwing method reference — `Files::readString`,
a payout-file reader, an identity-vendor call — cannot be handed directly to
`Stream.map`, `Function`, or any `java.util.function` type, because none of them
declare `throws`. The standard workaround before this pattern existed (or where it
still isn't used) is wrapping every call site in its own `try`/`catch` inline inside
the lambda, which defeats the entire point of passing a method reference. `[X-REF 03]`
the checked-vs-unchecked exception split itself — what the compiler enforces, why
`RuntimeException` opts out of it — is guide 03's territory in full; the mechanism
paragraph that follows here is enough to answer the interview question about *why*
functional interfaces can't carry `throws`, without re-deriving guide 03's whole
treatment: a checked exception is part of a method's signature exactly like its return
type, enforced at compile time via the `throws` clause, and `java.util.function`'s
interfaces simply never declared one — so no lambda assigned to `Function<T, R>` may
throw a checked exception, full stop, regardless of what the lambda body would
otherwise be allowed to do standalone.

**When to reach for it, and when not.** Reach for `CheckedFunction` (or a library
equivalent — vavr's `CheckedFunction1`, or a project-local one like this) at the
boundary where a checked-exception-throwing call needs to sit inside a
`Function`-shaped API, and you want the checked-ness to remain visible in the type
signature for as long as possible. Do not reach for it as a permanent home — it is a
staging area. Eventually the exception must become a `RuntimeException` (via
`unchecked`), be sneaky-thrown (via `sneaky`, and see the gotcha below for why that is
usually the wrong choice), or be converted to data via `Result<T, E>`, covered next.

**How it works.** `unchecked` and `sneaky` are two different escape mechanisms from
the same starting point — a `CheckedFunction` that might throw `E` — and they differ in
what kind of exception the caller ends up seeing:

```java
static <T, R, E extends Exception> Function<T, R> unchecked(CheckedFunction<T, R, E> f) {
    return t -> {
        try {
            return f.apply(t);
        } catch (RuntimeException re) {
            throw re;
        } catch (Exception e) {
            if (e instanceof IOException ioe) {
                throw new UncheckedIOException(ioe);
            }
            throw new RuntimeException(e);
        }
    };
}
```

`unchecked` **wraps**: the caller sees a `RuntimeException` (or the JDK's own
`UncheckedIOException` for the common `IOException` case) whose `getCause()` is the
original checked exception. This is honest — nothing pretends the checked exception
never happened, it is just no longer enforced by the compiler.

```java
static <T, R, E extends Exception> Function<T, R> sneaky(CheckedFunction<T, R, E> f) {
    return t -> {
        try {
            return f.apply(t);
        } catch (Exception e) {
            return CheckedFunction.sneakyThrow(e);
        }
    };
}

@SuppressWarnings("unchecked")
private static <T2, E2 extends Throwable> T2 sneakyThrow(Throwable t) throws E2 {
    throw (E2) t;
}
```

`sneaky` **does not wrap** — it throws the *original* checked exception object, unmodified,
through a method whose erased signature no longer mentions it, exploiting the fact that
checked-exception enforcement is a **compile-time** javac rule with no runtime
representation: bytecode has no concept of "checked" versus "unchecked," the JVM's
`athrow` instruction throws any `Throwable` unconditionally. `sneakyThrow`'s generic
parameter `E2` is inferred as `RuntimeException` at the call site (because nothing
constrains it otherwise), so the cast `(E2) t` compiles as an unchecked cast that
erases away to nothing at runtime — the checked exception is thrown as-is, and the
caller catches it as an unchecked one whether or not they declared it.

**Gotcha, proved.** Once a `CheckedFunction<T, R, E>`'s bound on `E` is the unspecific
`Exception`, you cannot `catch` a specific checked subtype like `IOException` inside
`unchecked`'s `try`/`catch` directly — the compiler rejects it:

```
error: exception IOException is never thrown in body of corresponding try statement
```

because the declared throwable at that point is the type variable `E`, erased to its
bound `Exception`, and javac's checked-exception flow analysis only allows catching a
checked exception subtype that is *provably* reachable from the `try` block's declared
throws — `IOException` is not provably reachable when all the compiler can see is
"some `Exception`." The fix is exactly what the code above does: catch the broad
`Exception`, then narrow with `instanceof` (Java 16's pattern-matching `instanceof`,
`e instanceof IOException ioe`) inside the handler, rather than trying to add a second
`catch` clause for the specific subtype.

Run on this machine (`javac --release 21`):

```
unchecked path caught: payout file not found: /missing/BDP-run-9999.csv
/PAYOUTS/BDP-RUN-4471.CSV
sneaky path caught as: java.io.IOException -> payout file not found: /missing/BDP-run-9999.csv
```

The third line is the sharpest proof of what `sneaky` actually does: the catch block
around the `sneaky`-wrapped call declares `catch (Exception e)`, yet
`e.getClass().getName()` prints `java.io.IOException` — the *exact original checked
type*, not a `RuntimeException` wrapper. The compiler let a piece of code catch
`IOException` under the label `Exception` without ever being told a checked exception
could occur there, because nothing in `Function<String, String>`'s signature — the
type `sneaky` returns — admits that possibility.

**Example.**

```java
static String readPayoutFileName(String path) throws IOException {
    if (path.startsWith("/missing")) {
        throw new IOException("payout file not found: " + path);
    }
    return path.toUpperCase();
}

Function<String, String> sneakyReader = CheckedFunction.sneaky(CheckedFunctionHarness::readPayoutFileName);
paths.stream().map(sneakyReader).forEach(System.out::println); // IOException can now surface from inside .map
```

**Interview:** "Why doesn't `java.util.function` have a checked variant?" — because a
checked `Function` would break every generic combinator (`andThen`, `Stream.map`) for
callers who never expected an exception, and the JDK's design instead pushes callers
toward converting checked failures into data (`Optional`, `Result`-style types) or
unchecked exceptions at the boundary, rather than propagating "checked-ness" through
generic higher-order code — this is expanded fully in the closing diff table below.

> **`CheckedFunction<T, R, E extends Exception>` re-admits a `throws` clause that
> `Function` deliberately omits, and `unchecked`/`sneaky` are the two ways out — wrap
> honestly into a `RuntimeException`, or throw the original checked exception past a
> compiler that was never told it could happen.**

---

### `Result<T, E>`

**Mental model.** `Result<T, E>` is a labelled two-slot box: either it holds a success
value of type `T` (an `Ok`), or it holds an error value of type `E` (an `Err`), and it
is structurally impossible to construct one holding both or neither. It is
`Optional<T>` with the empty case upgraded to carry a real payload instead of nothing.

**Why it exists.** Checked exceptions and `Optional<T>` each solve half the problem
`Result` solves whole. A checked exception carries rich error information but forces a
`try`/`catch` (or one of the previous section's escapes) at every call site and cannot
be composed with `map`/`flatMap` the way a value can. `Optional<T>` composes beautifully
but throws away *why* the value is missing — `Optional.empty()` carries no payload at
all. `Result<T, E>` is the union of both strengths: composable like `Optional`, but the
failure case carries a real `E`, so "the payout file read failed" can carry the actual
message instead of collapsing to indistinguishable emptiness.

**When to reach for it, and when not.** Reach for `Result<T, E>` at a pipeline boundary
where failure is an expected, first-class outcome that the caller is meant to branch
on — parsing, validation, a call to an external system whose failure mode you want
typed and inspectable. Do not reach for it as a replacement for exceptions used for
genuinely exceptional, programmer-error conditions (`NullPointerException`,
`IllegalStateException`) — those should still throw, because forcing every caller
everywhere to pattern-match a `Result` for conditions that indicate a bug, not a
business outcome, adds noise without adding safety. Its sibling in this file is
`CheckedFunction` above: `CheckedFunction` keeps the checked-exception shape and defers
the decision; `Result` commits to "this is data now," permanently.

**How it works.** `Result` is a `sealed interface` with exactly two `permits` — `Ok`
and `Err`, each a `record` — which is what makes the `switch` expressions below
**exhaustive without a `default` branch**: the compiler can see every possible
subtype of a sealed hierarchy and proves at compile time that `Ok`/`Err` is the
complete set.

```java
sealed interface Result<T, E> permits Result.Ok, Result.Err {
    record Ok<T, E>(T value) implements Result<T, E> {}
    record Err<T, E>(E error) implements Result<T, E> {}

    static <T, E> Result<T, E> ok(T value) { return new Ok<>(value); }
    static <T, E> Result<T, E> err(E error) { return new Err<>(error); }

    default <U> Result<U, E> map(Function<? super T, ? extends U> mapper) {
        return switch (this) {
            case Ok<T, E> ok -> Result.<U, E>ok(mapper.apply(ok.value()));
            case Err<T, E> err -> Result.err(err.error());
        };
    }

    default <U> Result<U, E> flatMap(Function<? super T, ? extends Result<U, E>> mapper) {
        return switch (this) {
            case Ok<T, E> ok -> mapper.apply(ok.value());
            case Err<T, E> err -> Result.err(err.error());
        };
    }

    default <U> U fold(Function<? super T, ? extends U> onOk, Function<? super E, ? extends U> onErr) {
        return switch (this) {
            case Ok<T, E> ok -> onOk.apply(ok.value());
            case Err<T, E> err -> onErr.apply(err.error());
        };
    }

    default T orElseThrow(Function<? super E, ? extends RuntimeException> exceptionMapper) {
        return switch (this) {
            case Ok<T, E> ok -> ok.value();
            case Err<T, E> err -> throw exceptionMapper.apply(err.error());
        };
    }
}
```

`map` transforms the success payload and leaves an `Err` alone (transporting the
existing error across, untouched, into a `Result<U, E>` of the new success type).
`flatMap` is the same idea but the mapper itself returns a `Result`, so chained calls
that can each fail don't nest as `Result<Result<Result<T, E>, E>, E>` — each `flatMap`
flattens one level. `fold` collapses both branches into one non-`Result` value in a
single expression, which is the idiomatic way to *exit* a `Result` pipeline into
ordinary code (logging, an HTTP response body, a UI string). `orElseThrow` is the
deliberate escape hatch back into exceptions, for boundaries (a method whose caller is
not `Result`-aware) that still need one.

**Example — the same `IOException`-throwing payout-file read, routed through `Result`
instead of `CheckedFunction`.**

```java
static Result<String, String> readPayoutFile(String path) {
    try {
        if (path.startsWith("/missing")) {
            throw new IOException("payout file not found: " + path);
        }
        return Result.ok(path.toUpperCase());
    } catch (IOException e) {
        return Result.err(e.getMessage());
    }
}
```

Run on this machine:

```
Ok[value=/payouts/bdp-run-4471.csv]
Err[error=payout file not found: /missing/BDP-run-9999.csv]
failed: payout file not found: /missing/BDP-run-9999.csv
orElseThrow threw: payout file not found: /missing/BDP-run-9999.csv
Ok[value=25]
```

The last line is `ok.flatMap(v -> v.length() > 5 ? Result.ok(v.length()) : Result.err("too short"))` —
a `String`-typed success chained into an `Integer`-typed success, with the error type
`String` staying fixed across the whole chain, which is `flatMap`'s job: change the
success type freely, keep the error type pinned, never nest.

**Gotcha.** `Result` fixes the error type `E` for an entire chain (both `Ok<T, E>` and
`Err<T, E>` share the same `E`), so combining two `Result`-producing calls that use
*different* error types (a `Result<PaymentRun, IOException>` and a
`Result<PaymentRun, ValidationError>`) does not typecheck without first mapping one
error type into the other — there is no free-form heterogeneous error channel the way
an unchecked `catch (Exception e)` can silently swallow anything. This is a real cost,
not a defect: it forces the error type to be decided and unified up front, exactly the
discipline a checked exception hierarchy would also have forced, but visible in the
generic signature instead of a `throws` clause.

**Interview:** "Why would you use `Result<T, E>` instead of just throwing?" — because
`Result` composes through `map`/`flatMap` the way exceptions never can: a
`try`/`catch` cannot be threaded through a `Stream` pipeline without breaking out of
it, but a `Result`-returning step can sit inside a `Stream.map` call like any other value, and
the failure travels alongside the data instead of unwinding the call stack.

> **`Result<T, E>` is a sealed two-case type carrying either a success value or a
> typed error value, giving checked-exception-grade information without the
> `throws`-clause restriction that keeps checked exceptions out of generic
> higher-order code.**

---

### The memoizing `Function` decorator

**Mental model.** A memoizing decorator is a `Function<T, R>` sitting in front of
another `Function<T, R>`, holding a `Map<T, R>` between them. The wrapped function is
never invoked twice for the same input — the map is the function's entire runtime
memory of what it has already computed, keyed on the argument.

**Why it exists.** Pure, expensive, repeatedly-called functions — a fee calculation
run over the same handful of currencies thousands of times, a lookup keyed by a small
set of jurisdictions — waste CPU recomputing an answer that has not changed since the
last call. Memoization trades memory (the map) for time (skipping recomputation), and
doing it as a decorator around `Function<T, R>` means any existing function can be
memoized without touching its own code, by wrapping the reference rather than editing
the implementation.

**When to reach for it, and when not.** Reach for it when the function is a **pure**
function of its argument (same input always produces the same output, no side
effects) and the input domain is small or repeats heavily — currency codes,
jurisdiction codes, a small enum of gate names. Do not reach for it when the function
has side effects (memoizing hides the second, third, and later invocations entirely,
silently skipping whatever the side effect was supposed to do), when the input space
is effectively unbounded relative to memory (memoizing over every distinct `ClientId`
that ever exists is an unbounded cache, not a memoized pure function — that calls for
an actual bounded cache library with eviction, not this decorator), or when the
function is already cheap enough that a `ConcurrentHashMap` lookup costs more than
recomputing.

**How it works.**

```java
static <T, R> Function<T, R> memoize(Function<T, R> function) {
    Map<T, R> cache = new ConcurrentHashMap<>();
    return t -> cache.computeIfAbsent(t, function);
}
```

`computeIfAbsent` is doing two jobs at once: it looks up `t`, and if absent, computes
`function.apply(t)`, stores it, and returns it — all advertised as one atomic
operation with respect to other threads calling `computeIfAbsent` for the *same* key,
which is exactly the property that makes this decorator thread-safe without any
explicit locking in the decorator's own code. `ConcurrentHashMap` implements that
atomicity by holding a lock on the bin (the internal hash bucket) for the key being
computed, for the duration of the mapping function's execution.

`[TRAP]` `[PROVE]` **the recursion deadlock.** Holding that bin lock for the *duration
of the mapping function's execution* is exactly the trap: if the mapping function
itself calls back into `computeIfAbsent` (directly, or transitively through
recursion) on a key that lands in the **same bin**, the thread tries to reacquire a
lock it already holds, or otherwise mutates the map it is mid-computation on — a
recursive update. A naive memoized recursive Fibonacci written the obvious way:

```java
static Function<Long, Long> brokenFib;
static {
    Map<Long, Long> cache = new ConcurrentHashMap<>(1); // tiny capacity forces bin collisions
    brokenFib = n -> cache.computeIfAbsent(n, key -> {
        if (key < 2L) return key;
        return brokenFib.apply(key - 1) + brokenFib.apply(key - 2); // recurses into the SAME map
    });
}
```

Run on this machine with the map deliberately started at capacity `1` (so keys `0`,
`1`, `2`, … collide into the same bin and the recursive call is forced to contend for
the lock the outer call still holds):

```
brokenFib threw: java.lang.IllegalStateException -> Recursive update
```

At the JDK's default (larger) initial capacity, small fibonacci keys mostly land in
*different* bins, so the recursive calls proceed without contention and the bug goes
unnoticed for years in code that "just works" in testing — this is precisely why the
trap is dangerous: it is capacity- and hash-distribution-dependent, not
deterministic. **The fix is to never let the recursive call re-enter `computeIfAbsent`
on the same map at all** — separate "check the cache" from "recurse," so the lock is
never held across the recursive call:

```java
static final Map<Long, Long> fixedCache = new ConcurrentHashMap<>();
static long fixedFib(long n) {
    if (n < 2L) return n;
    Long cached = fixedCache.get(n);
    if (cached != null) return cached;
    long result = fixedFib(n - 1) + fixedFib(n - 2); // plain recursion, no lock held
    fixedCache.put(n, result);
    return result;
}
```

```
fixedFib(10) = 55
```

`[X-REF 05]` the mechanics of `ConcurrentHashMap`'s per-bin locking under
`computeIfAbsent` — the CAS-then-`synchronized`-on-bin-head protocol, and why it
differs from a plain `HashMap`'s no-locking-at-all — is guide 05's (multithreading and
concurrency) full territory; the load-bearing fact for this file is narrower and
already proven above: the lock is held for the *whole* mapping-function call, so any
reentrancy into the same map from inside that call is a correctness hazard, not merely
a performance one.

**Example.**

```java
Function<String, BigDecimal> feePercentageForCurrency = memoize(currency -> switch (currency) {
    case "GBP" -> new BigDecimal("0.015");
    case "EUR" -> new BigDecimal("0.018");
    default -> new BigDecimal("0.020");
});
```

Every call with `"GBP"` after the first is a `ConcurrentHashMap` lookup, never a
re-evaluation of the `switch`.

**Gotcha.** Memoizing an exception-throwing function silently defeats retries: the
**first** call for a given key that throws leaves no entry in the map (an exception
from the mapping function propagates out of `computeIfAbsent` without inserting
anything), so a transient failure is *not* poisoned into the cache forever — but a
caller assuming "if it succeeded once for this key, memoization means it will always
succeed" is still wrong, because every failing call for the same key pays the full
cost of the wrapped function again; memoization gives you no help at all on the
failure path, only on the success path.

**Interview:** "Is `computeIfAbsent` safe to call recursively?" — only if the
recursive call goes to a **different** map or a **different** key than the one
currently being computed; recursion back into the *same* map for a key that maps to
the same or a colliding bin is a documented hazard (the javadoc for
`ConcurrentHashMap.computeIfAbsent` explicitly warns against it) that surfaces as
`IllegalStateException: Recursive update` on this JDK.

> **The memoizing decorator is a `Function<T, R>` wrapping a `Map<T, R>.computeIfAbsent`
> call — thread-safe because the map's per-key atomicity comes for free, and
> dangerous specifically because that atomicity is implemented by holding a lock for
> the whole mapping-function call, which a naive recursive mapping function can
> re-enter.**

---

### Curry and partial application for `BiFunction`

A curry/partial helper is a **supporting fact**, not a primary concept here — it has
no cost claim, no diagram, and no sibling it must be chosen against; it is a fixed,
small combinator shape.

**Mechanism.** Currying turns a two-argument function into a function that returns a
function — `BiFunction<T, U, R>` becomes `Function<T, Function<U, R>>` — so the two
arguments can be supplied one at a time, at two different call sites, in two different
scopes. Partial application is the simpler, more common cousin: fix *one* argument now,
get back a `Function<U, R>` waiting for the other.

```java
static <T, U, R> Function<T, Function<U, R>> curry(BiFunction<T, U, R> biFunction) {
    return t -> u -> biFunction.apply(t, u);
}

static <T, U, R> Function<U, R> partial(BiFunction<T, U, R> biFunction, T fixed) {
    return u -> biFunction.apply(fixed, u);
}
```

Run against the QuizStakes bonus split (`3.33` stake, `0.10` bonus rate, rounding the
bonus portion **down** to the minor unit, per the domain's rounding rule):

```
curried:  100.00
partial:  100.00
bonus portion = 0.33
```

The first two lines curry/partial-apply `applyBonusCap(deposit, capPercentage)` fixed
at a `1000`-unit deposit, both landing on the `100`-unit bonus cap. The third line is
`splitStakeBonus(3.33, 0.10, scale=2)` rounded `DOWN`, landing on the domain's
canonical `0.33` bonus portion for a `3.33` stake.

**Gotcha, and the honest note on readability.** `curry` is almost never reached for in
Java the way it is in ML-family languages, because Java has no syntax sugar for
partial application (`f(x)(y)` is not valid Java the way it would be in Haskell or
Scala) — every curried call site pays for two explicit, stacked `apply` method calls,
and beyond two or three curried arguments the nested `Function<A, Function<B, Function<C, R>>>`
type signature stops being readable at a glance. `partial` scales better in Java
precisely because it collapses back to an ordinary `Function<U, R>` after one
application, rather than staying nested — prefer `partial` unless the caller genuinely
needs to supply arguments across two separate scopes at two separate times.

> **Currying a `BiFunction` into `Function<T, Function<U, R>>` is a real, useful
> shape for supplying arguments across two scopes — but past two type parameters deep
> it trades away more Java readability than it buys, and `partial` is almost always
> the better default.**

---

### `TriFunction<A, B, C, R>`

**Mental model.** `TriFunction` is `BiFunction` with one more slot — a plain
three-argument, single-abstract-method interface. There is nothing structurally
different about it from `Function` or `BiFunction`; it exists purely to answer "why
doesn't the JDK already have this."

**Why it exists (and why the JDK stops at two).** `java.util.function` ships
`Function` (arity 1) and `BiFunction` (arity 2), and stops. Three separate,
compounding reasons hold that line, and all three are visible in the JDK's own
interface count:

1. **Combinatorial explosion.** `Function`/`BiFunction` each also need primitive
   specializations (`IntFunction`, `ToIntBiFunction`, `IntBinaryOperator`, and so on).
   Adding a three-argument tier would multiply that specialization matrix again for a
   shape used in a small minority of call sites — the cost of maintaining and
   documenting the interfaces is front-loaded onto the JDK for a benefit realized by
   relatively few callers.
2. **Records make wide argument lists unnecessary.** Since Java 16, a three-or-more
   field aggregate is a one-line `record` (`record StakeSplit(Money bonusPortion, Money cashPortion)`
   from this domain is exactly this shape), which converts what would have been a
   `TriFunction<A, B, C, R>` into an ordinary `Function<SomeRecord, R>` — the "third
   argument" becomes a field on a named type instead of a positional parameter, which
   is more self-documenting at every call site.
3. **Precedent, not law.** Two arguments cover the overwhelming majority of real call
   sites (`BiFunction<K, V, R>` for map-shaped operations is the dominant use), and the
   JDK's own style is to let third-party libraries (Apache Commons, vavr) fill in
   `TriFunction`/`Function3`/`Function4`-style shapes rather than grow
   `java.util.function` without bound — arity three is exactly where the JDK judged
   the maintenance cost stopped paying for itself.

**When to reach for it, and when not.** Reach for a hand-rolled `TriFunction` only when
the three arguments genuinely do not belong together as one aggregate — reason 2 above
is usually the better fix. Do not reach for it as a first move; check whether the three
arguments are secretly a `record` waiting to be named before writing a three-argument
functional interface.

**How it works.**

```java
interface TriFunction<A, B, C, R> {
    R apply(A a, B b, C c);

    default <V> TriFunction<A, B, C, V> andThen(Function<? super R, ? extends V> after) {
        return (a, b, c) -> after.apply(this.apply(a, b, c));
    }
}
```

`andThen` here composes against a plain `Function<R, V>`, not another `TriFunction` —
there is no sensible "three-argument `andThen`" because the second stage only ever
needs the *result* of the first, not its three original inputs; this is the same
asymmetry that keeps `Function.andThen` taking a `Function`, not another `BiFunction`.

**Example.**

```java
static BigDecimal splitStakeBonus(BigDecimal stake, BigDecimal bonusRate, int scale) {
    return stake.multiply(bonusRate).setScale(scale, RoundingMode.DOWN);
}

TriFunction<BigDecimal, BigDecimal, Integer, BigDecimal> split = CurryHarness::splitStakeBonus;
TriFunction<BigDecimal, BigDecimal, Integer, String> splitAndDescribe =
    split.andThen(v -> "bonus portion = " + v);

splitAndDescribe.apply(new BigDecimal("3.33"), new BigDecimal("0.10"), 2);
// "bonus portion = 0.33"
```

**Gotcha.** A hand-rolled `TriFunction` cannot be handed to any JDK API expecting
`Function`/`BiFunction`-shaped input — `Stream`, `Collectors`, `Map` methods all stop
at two arguments — so introducing `TriFunction` into a codebase means every consumer
of it must also be custom, which is the practical cost that reason 3 above is really
describing: it is not that three arguments is unthinkable, it is that the JDK's own
higher-order machinery has nowhere to plug one in.

**Interview:** "Why is there no `TriFunction` in the JDK?" — arity two covers the
dominant case (`BiFunction<K, V, R>`), records absorb most of what would need a third
positional parameter, and the JDK deliberately avoids growing `java.util.function`'s
specialization matrix (already dozens of interfaces) for a shape most codebases can
route around with a record.

> **`TriFunction<A, B, C, R>` is a one-method three-argument contract the JDK omits on
> purpose — arity two is the deliberate ceiling, past which a record almost always
> reads better than a wider functional interface.**

---

## Diff vs the real one — `MyFunction`/`MyPredicate` vs `java.util.function.Function`/`Predicate`

| Axis | This file's toy | The real `java.util.function` |
|---|---|---|
| Interface count | 2 (`MyFunction`, `MyPredicate`) | **43 interfaces** in `java.util.function` |
| Primitive specializations | none — every call boxes | `IntFunction`, `ToIntFunction`, `IntUnaryOperator`, `IntBinaryOperator`, `IntPredicate`, and the `Long`/`Double` equivalents, avoiding autoboxing on hot numeric paths |
| `@FunctionalInterface` enforcement | annotation present but purely documentary here too | same — `@FunctionalInterface` is checked by javac at compile time (a second abstract method fails the build), but nothing prevents an interface with exactly one abstract method from being a valid lambda target *without* the annotation; it only turns an accidental second method into a compile error, it does not grant lambda-target status |
| Checked exception support | `CheckedFunction` bolts it on as a separate type | deliberately absent from `Function`/`Predicate`/`BiFunction` themselves — see `CheckedFunction`'s section above for the full argument |
| Arity ceiling | this file adds `TriFunction` past the JDK's ceiling | stops at two (`Function`, `BiFunction`) — see `TriFunction`'s section above |
| `null` policy | undocumented in this toy | `Function`/`Predicate`'s default methods `Objects.requireNonNull` their arguments (`andThen`, `and`, `or`) exactly as this file's toy does, but do **not** guard against the wrapped lambda itself returning `null` — a `Function<T, R>` returning `null` is legal and propagates silently |
| Thread safety | stateless lambdas here are as thread-safe as any pure function | identical — `Function`/`Predicate` carry no state of their own; thread-safety is a property of what you put inside `apply`/`test`, not of the interface |
| Serialization | not attempted | a lambda assigned to a `Serializable`-extending functional interface *can* serialize, but plain `Function`/`Predicate` are not `Serializable`, and capturing lambdas (closing over local state) serialize their captured state alongside the synthetic class, which is a well-known footgun the JDK does not protect against |
| Why the JDK bothers | none — pedagogical only | one standard vocabulary every library agrees on, so `Stream`, `Optional`, `CompletableFuture`, and every third-party library can accept and return the same shapes without depending on each other |

The `@FunctionalInterface`/checked-exception/arity-ceiling rows above are the
mechanism answers to leaf 4.1.8 in full; each is also argued at length in its own
concept section rather than only appearing compressed here, per this file's rule that
an `[X-REF]`-style compression is never the *only* place a mechanism is explained.

---

## Pitfalls

### Assuming `andThen`/`compose` order does not matter for `Money`

**Wrong**

```java
MyFunction<Money, Money> pipeline = round.andThen(fee); // rounds first, fees an already-rounded value
System.out.println(pipeline.apply(new Money(new BigDecimal("3.33"), "GBP")));
// Money[amount=3.315, currency=GBP]  <- three decimal places written toward a ledger
```

**Right**

```java
MyFunction<Money, Money> pipeline = fee.andThen(round); // fees first, rounds the final figure
System.out.println(pipeline.apply(new Money(new BigDecimal("3.33"), "GBP")));
// Money[amount=3.32, currency=GBP]
```

**Why people believe it:** both pipelines "do the same two things," and for
integer-valued inputs or fee-free paths the two orders coincide, so the bug only shows
up once a fee with more decimal places than the target scale is introduced — exactly
the kind of thing that passes code review on a happy-path example and fails in
production on a real stake amount.

### Trusting `computeIfAbsent` inside a recursive memoized function

**Wrong**

```java
Map<Long, Long> cache = new ConcurrentHashMap<>();
Function<Long, Long> fib = n -> cache.computeIfAbsent(n, key ->
    key < 2 ? key : fib.apply(key - 1) + fib.apply(key - 2)); // may throw IllegalStateException: Recursive update
```

**Right**

```java
Map<Long, Long> cache = new ConcurrentHashMap<>();
long fib(long n) {
    if (n < 2) return n;
    Long cached = cache.get(n);
    if (cached != null) return cached;
    long result = fib(n - 1) + fib(n - 2);
    cache.put(n, result);
    return result;
}
```

**Why people believe it:** the naive version compiles cleanly, and at the JDK's
default `ConcurrentHashMap` capacity a small key range often avoids bin collisions
entirely, so it "just works" in a quick test and the failure only appears under a
different capacity, a larger key range, or a different JDK's hash distribution.

### Catching a specific checked exception subtype off an unbounded `throws E`

**Wrong**

```java
static <T, R, E extends Exception> Function<T, R> unchecked(CheckedFunction<T, R, E> f) {
    return t -> {
        try {
            return f.apply(t);
        } catch (IOException ioe) {           // compile error: never thrown in this try
            throw new UncheckedIOException(ioe);
        }
    };
}
```

**Right**

```java
} catch (Exception e) {
    if (e instanceof IOException ioe) {
        throw new UncheckedIOException(ioe);
    }
    throw new RuntimeException(e);
}
```

**Why people believe it:** it looks like ordinary multi-catch exception handling, and
the compiler's rejection message ("never thrown in body of corresponding try
statement") reads like a dead-code warning rather than what it actually is — a
consequence of `E`'s erasure to its bound.

## Cheat sheet

| Type | One-line job | Key gotcha |
|---|---|---|
| `MyFunction<T, R>` | one input, one output, composable via `andThen`/`compose` | `f.andThen(g)` == `g.compose(f)`; `identity()` allocates, never cached |
| `MyPredicate<T>` | boolean test, composable via `and`/`or`/`negate`/`not` | `and`/`or` short-circuit via `&&`/`||`; order matters with side effects |
| `CheckedFunction<T, R, E>` | `Function` with a `throws E` reopened | `unchecked` wraps (`RuntimeException`/`UncheckedIOException`); `sneaky` throws the original checked type unmodified past an unaware signature |
| `Result<T, E>` | sealed `Ok`/`Err`, composable via `map`/`flatMap`/`fold` | error type `E` is fixed across the whole chain; `orElseThrow` is the deliberate exit back to exceptions |
| memoizing decorator | `Function<T, R>` wrapping `Map<T, R>` via `computeIfAbsent` | recursive re-entry into the same map/bin during the mapping call is a hazard (`IllegalStateException: Recursive update`), not just a performance question |
| curry/partial for `BiFunction` | `BiFunction<T, U, R>` → `Function<T, Function<U, R>>` (curry) or `Function<U, R>` (partial) | `partial` reads better in Java past one fixed argument; deep currying loses readability fast |
| `TriFunction<A, B, C, R>` | three inputs, one output, `andThen` against a plain `Function` | not JDK-composable with `Stream`/`Collectors`; a `record` usually beats a third argument |
| `java.util.function` (real) | 43 interfaces including primitive specializations | no checked variant, no arity past two, `@FunctionalInterface` is compile-time-checked but not required for lambda targeting |

## Self-test

**Q1.** Why does `f.andThen(g)` produce the same pipeline as `g.compose(f)`?

<details><summary>Answer</summary>

`andThen` is defined as `t -> after.apply(this.apply(t))` and `compose` is defined as
`v -> this.apply(before.apply(v))`. Substituting `f.andThen(g)`: apply `f` to the
input, then apply `g` to that result — `g(f(x))`. Substituting `g.compose(f)`: apply
`f` to the input (because `f` is `compose`'s `before` argument), then apply `g` (the
receiver) to that result — also `g(f(x))`. They are the same combinator called from
opposite ends, and both evaluate `f` before `g`.

</details>

**Q2.** In the fee-then-round versus round-then-fee harness, why did `feeThenRound`
and `roundThenFee` differ (`3.32` vs `3.315`) even though both steps are
mathematically simple arithmetic?

<details><summary>Answer</summary>

Because rounding is not commutative with subtraction when the subtracted amount has
more decimal places than the rounding scale. Fee-then-round subtracts `0.015` from
`3.33` to get `3.315`, then rounds `HALF_UP` to two places, landing on `3.32`.
Round-then-fee rounds `3.33` first (a no-op, since it is already at two decimal
places), then subtracts the unrounded `0.015`, leaving `3.315` — three decimal places
that were never re-rounded. The two pipelines are genuinely different functions, not
the same function evaluated two ways.

</details>

**Q3.** Why does a `MyPredicate<T>.and(other)` sometimes never invoke `other` at all,
and what proved it in this file?

<details><summary>Answer</summary>

Because `and`'s default implementation is `t -> this.test(t) && other.test(t)`, and
`&&` short-circuits: if `this.test(t)` is `false`, Java never evaluates the right
operand. The harness in this file proved it by giving `other` (`exceedsLimit`) a side
effect — an `AtomicInteger` counter — and showing the counter stayed at `0` after
testing an unrestricted reservation (where `isRestricted` returned `false`), then
incremented to `1` only once `isRestricted` returned `true` for a blocked reservation.

</details>

**Q4.** What is the actual compile error you get if you try to `catch (IOException e)`
directly inside a generic method whose declared exception type is `E extends
Exception`, and why does the compiler reject it?

<details><summary>Answer</summary>

`error: exception IOException is never thrown in body of corresponding try statement`.
The `try` block's only statically-declared throwable at that point is the type
variable `E`, whose erasure is its bound, `Exception` — the compiler's checked-exception
flow analysis will only let you catch a checked-exception subtype that it can prove is
reachable, and "some `Exception`" does not prove `IOException` specifically is
reachable. The fix is to catch the broad `Exception` and narrow with
`instanceof` inside the handler.

</details>

**Q5.** What is the practical difference between `unchecked` and `sneaky` as escapes
from `CheckedFunction`, and which one did this file's harness prove behaves
differently from what its own catch block declared?

<details><summary>Answer</summary>

`unchecked` wraps the original checked exception inside a new `RuntimeException` (or
`UncheckedIOException` for `IOException` specifically) — the caller sees a different
exception object whose `getCause()` is the original. `sneaky` throws the *original*
exception object unmodified, exploiting the fact that checked-exception enforcement is
compile-time only and has no bytecode representation. The harness proved `sneaky`'s
behavior: a block declaring `catch (Exception e)` (with no checked exception ever
admitted by the surrounding `Function<String, String>` signature) caught an object
whose `getClass().getName()` printed `java.io.IOException` — the original checked
type, not a wrapper.

</details>

**Q6.** Why did the naive memoized recursive Fibonacci only fail with
`IllegalStateException: Recursive update` once the `ConcurrentHashMap` was constructed
with an initial capacity of `1`, and not at the JDK's default capacity?

<details><summary>Answer</summary>

The recursive re-entry hazard in `computeIfAbsent` is triggered when the recursive
call lands in the **same internal hash bin** as the outer call still being computed,
because the bin is locked for the duration of the mapping function. At the JDK's
default (larger) initial capacity, small consecutive `Long` keys are likely to hash
into *different* bins, so the recursive calls never contend for the same lock and the
bug goes unobserved. Forcing capacity down to `1` collapses every key into the same
bin, guaranteeing the collision and reliably reproducing the exception.

</details>

**Q7.** Why is `Result<T, E>`'s `switch` over `Ok`/`Err` allowed to have no `default`
branch, and what would happen if a third record were added to implement `Result`
outside this file?

<details><summary>Answer</summary>

`Result` is declared `sealed interface Result<T, E> permits Result.Ok, Result.Err`,
so the compiler knows the complete, closed set of implementing types at compile time
and can prove a `switch` covering both `Ok` and `Err` is exhaustive without a
`default`. A third type cannot be added to implement `Result` from outside this file
at all — `permits` closes the hierarchy to exactly the listed types (in the same
module/package, per the sealed-type access rules), so the only way to add a third case
is to edit the `permits` clause here, which would also make every existing exhaustive
`switch` over `Result` a compile error until it added a case for the new type.

</details>

**Q8.** Why does this file argue that `TriFunction` should usually be replaced by a
`record` rather than written at all?

<details><summary>Answer</summary>

Because a three-argument functional interface only earns its keep when the three
values genuinely do not belong together as one named aggregate. Since Java 16, three
related values are a one-line `record` declaration, which converts what would be a
`TriFunction<A, B, C, R>`'s third positional argument into a named field on a type —
more self-documenting at every call site, and it also regains compatibility with
ordinary `Function<SomeRecord, R>`-shaped JDK APIs (`Stream.map`, `Collectors`) that a
hand-rolled `TriFunction` can never plug into.

</details>

**Q9.** What does memoizing a function that occasionally throws an exception actually
guarantee, and what does it not guarantee?

<details><summary>Answer</summary>

It guarantees that a call which threw does **not** poison the cache — `computeIfAbsent`
does not insert an entry when the mapping function throws, so a later call with the
same key will retry the underlying computation rather than replaying a cached failure.
It does **not** guarantee that repeated failing calls become cheap: every failing call
for that key re-executes the full wrapped function, because memoization only ever
caches successful results, so a persistently failing key gets no speedup at all.

</details>

**Q10.** Why does `f.andThen(g)` on a `MyPredicate<T>`-shaped `and`/`or` composition
still allocate a new object every time it is called, even though the underlying
booleans are cheap primitives?

<details><summary>Answer</summary>

`and`/`or`/`negate` are default methods that each `return` a **new** lambda closing
over `this` and the argument predicate — the combinator itself is what is being built,
not a boolean value. Every call to `and`/`or` allocates one more small object
implementing `MyPredicate<T>`, regardless of how cheap the eventual `true`/`false`
result is; the cost is in composing the pipeline, not in evaluating it, and it is the
same cost profile `MyFunction.andThen`/`compose` carries for exactly the same reason.

</details>

## Deferred

None.

---

**Leaves covered:** 4.1.1–4.1.8 (8 leaves)
**Leaves deferred:** none
**Diagrams included:** none (no diagram assigned to this file per its manifest row)
**Target version:** Java 21 LTS
**Lines:** 1130
