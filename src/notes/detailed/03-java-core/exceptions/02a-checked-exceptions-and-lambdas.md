# 03 Java Core — Checked exceptions meet lambdas — INTERMEDIATE (§2.6, 2.6.3–2.6.4)

**Target version: Java 21 LTS.** | **Part 2 of 5** | [Index](../00-index.md)
Previous: [Exceptions in practice — checked or unchecked](02-in-practice.md) · Next: [Designing an exception hierarchy](02b-designing-an-exception-hierarchy.md)

Two things, one collision. `java.util.function.Function<T, R>` was designed in 2014 with a method signature that declares no checked exception, and every method you have ever written that talks to a database, a filesystem, or a vendor over the network is allowed to throw one. Neither side is going to change. [02-in-practice.md](02-in-practice.md) opened this argument by naming the lambda problem as one of the three reasons modern practice leans unchecked; this file is where the argument gets finished — the exact compiler diagnostic, the four ways out, and the one workaround that does not fix the problem so much as hide the evidence.

Everything measured below is against **Oracle JDK 21.0.7 (21.0.7+8-LTS-245, macOS aarch64)**, compiled and run in a scratch directory under `/tmp/`.

---

## 1. The lambda problem, and its four workarounds (2.6.3)

`[BUILD]` `[X-REF 04]` The mental model: `Function<T, R>` is not lambda-hostile by accident — it is an ordinary interface with an ordinary method signature, and the catch-or-declare rule that has applied to every Java method since 1.0 applies to that signature exactly as written. A lambda does not get a signature of its own; it borrows the one on the functional interface it is assigned to. If that signature declares no checked exception, neither does the lambda body, and the compiler enforces it exactly as it would for a named method override.

### Why it exists

`java.util.function.Function<T, R>` was added in Java 8 (JEP 126, the `java.util.function` package that made the Streams API possible) with:

```java
@FunctionalInterface
public interface Function<T, R> {
    R apply(T t);
}
```

No `throws` clause. That was a design decision, not an oversight, and it was never revisited in Java 11, 17 or 21: a generic `throws E` on a functional interface would force every caller — including every method in `java.util.stream` that accepts one — to either declare `E` themselves or immediately handle it, and `E` would have to be a type parameter threaded through `Stream<T>`, `Optional<T>`, `Collectors`, and everything built on them. The JDK designers chose a `Function` that composes freely with `andThen`, `compose`, `Stream.map`, and every other combinator, over one that can carry a checked exception. The cost of that choice is this file.

### When to reach for it, and when not

There is no single right answer among the four workarounds — the right one depends on who is calling, and what they are allowed to see.

| Workaround | What the caller sees | Compiler still helps? | Composes with `Stream.map` / `Function.andThen`? | Verdict |
|---|---|---|---|---|
| **Wrap** (catch, rethrow unchecked) | An unchecked exception, undeclared | No — the throw is invisible in the signature | Yes, it is a plain `Function` | Right default. Use a *named* unchecked type, not bare `RuntimeException` |
| **Sneaky throw** | Nothing — the checked exception escapes with no declaration and cannot be caught by name | No — actively defeats it (§2) | Yes, it is a plain `Function` | Wrong almost everywhere. See §2 |
| **Custom functional interface** (`ThrowingFunction<T, R, E>`) | The checked exception, in the interface's own `apply` signature | Yes, in full | No — the JDK's own combinators want a plain `Function` | Right at your own API boundary; adapt at the edge where the JDK's shape is required |
| **`Result<T, E>`** (sealed, `Success`/`Failure`) | No exception at all — a value that might be a failure | Yes, via the compiler's exhaustive-`switch` check on the sealed hierarchy | Yes, a `Result` is an ordinary value `Function.map` can produce | Right when failure is a normal, expected outcome the caller must handle explicitly, not an exceptional one |

Recommendation: default to **wrap**, because it is the least code and the least surprising to a reader who has not seen your codebase before. Reach for the **custom functional interface** only when the exception type itself is part of what you want the compiler to enforce at a boundary you control end to end — for instance, an internal `AssessmentClient` interface used only inside `AccountActivation`, never handed to `Stream.map` directly. Reach for **`Result`** when a failure is a first-class, expected branch of the business logic — `AssessmentService` returning `WEALTH_REFERRED` is not exceptional, it is routine — and you want the type system to force every caller to look at it. Never reach for **sneaky throw** as a first choice; §2 explains why it survives at all.

### How it works — the diagnostic, and the anonymous-class control

The problem, on a real pipeline. `AccountActivation` needs to score the day's `AO-400` submissions — 7.2k/day steady, 24k peak — and `AssessmentService.scoreApplication` talks to a JDBC-backed rules store, so it declares `throws SQLException`:

```java
record Application(String id) {}
record Verdict(String status) {}

static Verdict scoreApplication(Application a) throws SQLException {
    if (a.id().equals("BAD")) {
        throw new SQLException("cannot reach AssessmentService for " + a.id());
    }
    return new Verdict("AO-400");
}
```

Wiring it into a stream the obvious way:

```java
Function<Application, Verdict> scorer = a -> scoreApplication(a);
apps.stream().map(scorer).forEach(System.out::println);
```

fails with, measured on JDK 21.0.7:

```
LambdaProblem.java:20: error: unreported exception SQLException; must be caught or declared to be thrown
        Function<Application, Verdict> scorer = a -> scoreApplication(a); // should not compile
                                                                     ^
1 error
```

The message points at the lambda body's *call site* (`scoreApplication(a)`), not at `Function.apply`'s signature — which is why it reads as confusing the first time. Nothing about the diagnostic tells you the interface is the reason; you have to already know `Function.apply` declares no `throws` to connect "unreported exception" to "assigned to a `Function`".

**Insight:** this is not a lambda-specific rule. It is the ordinary catch-or-declare rule from [01-basics.md](01-basics.md), applied to the target method the lambda is implementing — and it fires identically for an anonymous class, which has no special lambda machinery at all:

```java
Function<Application, Verdict> scorer = new Function<Application, Verdict>() {
    @Override
    public Verdict apply(Application a) {
        return scoreApplication(a); // should not compile
    }
};
```

Measured, same JDK:

```
AnonProblem.java:20: error: unreported exception SQLException; must be caught or declared to be thrown
                return scoreApplication(a); // should not compile
                                       ^
1 error
```

Identical diagnostic, identical column-for-column shape. The lambda and the anonymous class are implementing the exact same method, `Verdict apply(Application)` with no `throws`, and the compiler checks the exact same thing both times. Once this clicks, "lambdas can't throw checked exceptions" stops being a lambda fact and becomes an instance of a fact you already knew.

### Workaround 1 — wrap

Catch inside the lambda and rethrow unchecked, ideally as a domain type rather than a bare `RuntimeException`, so a caller further up can still catch it specifically if they choose to:

```java
static class AssessmentUncheckedException extends RuntimeException {
    AssessmentUncheckedException(String message, Throwable cause) {
        super(message, cause);
    }
}

static Function<Application, Verdict> wrapWorkaround() {
    return a -> {
        try {
            return scoreApplication(a);
        } catch (SQLException e) {
            throw new AssessmentUncheckedException("scoring failed for " + a.id(), e);
        }
    };
}
```

Measured running it over `List.of(new Application("A1"), new Application("BAD"))`:

```
Verdict[status=AO-400]
caught wrapped: java.sql.SQLException: cannot reach AssessmentService for BAD
```

`apps.stream().map(wrapWorkaround())` threw `AssessmentUncheckedException` on the second element, with the original `SQLException` intact as `getCause()`.

Cost: the checked-ness is gone at the type level. Nothing in `wrapWorkaround()`'s signature tells a caller that `AssessmentService` can fail — they find out at runtime, from the exception's own message and cause, or from documentation. That is a real loss of compiler help, and it is the same trade [02-in-practice.md](02-in-practice.md) already made when arguing for unchecked exceptions generally; this is that argument's sharpest instance.

The JDK's own precedent for exactly this shape is worth having, because it turns "wrap it" from a personal opinion into a pattern the platform itself endorses. `java.io.UncheckedIOException` was added in **Java 8**, specifically so that stream-returning I/O methods could report a failure without forcing `IOException` into every `Stream` combinator's signature. `BufferedReader.lines()` — also Java 8 — declares no `throws` clause at all, and if the underlying read fails during traversal, it throws `UncheckedIOException` wrapping the real `IOException`. Measured: closing a `BufferedReader` and then calling `.lines()` followed by `.forEach(System.out::println)` on it produced

```
UncheckedIOException wraps: java.io.IOException
```

with no checked exception ever declared anywhere in the call chain. `Files.lines(Path)` follows the same shape at the API-design level. This is the JDK doing workaround 1 to itself, at the exact boundary where a checked exception meets a `Stream`. [02e-resources-interrupts-and-testing.md](02e-resources-interrupts-and-testing.md) shows the same design move at a different site — a custom `AutoCloseable` whose `close()` is declared with no `throws` clause at all, so a caller in a try-with-resources block never has to catch anything from the close step; that file owns the construct, this section only notes the pattern is the same one.

### Workaround 2 — sneaky throw

Deferred in full to §2 below — it deserves the `[PROVE]`/`[TRAP]` treatment on its own, not a duplicate summary here.

### Workaround 3 — custom functional interface

A `@FunctionalInterface` whose method is allowed to declare `throws E`, generic in the exception type, plus a static adapter that lifts it into a plain `Function` for the places that need one:

```java
@FunctionalInterface
interface ThrowingFunction<T, R, E extends Exception> {
    R apply(T t) throws E;

    static <T, R, E extends Exception> Function<T, R> unchecked(ThrowingFunction<T, R, E> f) {
        return t -> {
            try {
                return f.apply(t);
            } catch (Exception e) {
                throw new AssessmentUncheckedException("scoring failed for " + t, e);
            }
        };
    }
}
```

Used at the boundary where the exception type still matters:

```java
ThrowingFunction<Application, Verdict, SQLException> scorer = Workarounds::scoreApplication;
List<Application> apps = List.of(new Application("A1"), new Application("A2"));
apps.stream().map(ThrowingFunction.unchecked(scorer)).forEach(System.out::println);
```

Measured:

```
Verdict[status=AO-400]
Verdict[status=AO-400]
```

`ThrowingFunction<Application, Verdict, SQLException> scorer = Workarounds::scoreApplication;` compiles directly — no lambda body, no try/catch — because `ThrowingFunction.apply` declares `throws E` and `E` is inferred as `SQLException`. The compiler is fully in the loop here: change `scoreApplication` to throw `IOException` instead and the assignment stops compiling, which is exactly the guarantee workaround 1 gave up.

Cost: it does not compose with the JDK's own combinators. `Stream.map` wants a `Function<? super T, ? extends R>`, not a `ThrowingFunction`, and `Function.andThen` is declared on `Function`, not on your interface — so the moment a `ThrowingFunction` needs to cross into `java.util.stream` territory, it goes through `ThrowingFunction.unchecked`, which is workaround 1 again, just localized to the crossing point. This workaround wins at your own API boundary — an internal client interface such as `AssessmentClient`, consumed only by code you also own — and stops the instant it needs to be handed to `Stream.map`, `Collectors.toMap`, or any other JDK combinator that was typed against `Function` in 2014.

### Workaround 4 — `Result` type

A sealed interface with two record implementations, `map`, and a terminal `orElseThrow` that lets the checked exception surface again exactly once, at the point the caller chooses to stop deferring it:

```java
sealed interface Result<T, E extends Exception> permits Success, Failure {
    <R> Result<R, E> map(Function<T, R> f);
    T orElseThrow() throws E;
}

record Success<T, E extends Exception>(T value) implements Result<T, E> {
    @Override
    public <R> Result<R, E> map(Function<T, R> f) {
        return new Success<>(f.apply(value));
    }
    @Override
    public T orElseThrow() {
        return value;
    }
}

record Failure<T, E extends Exception>(E error) implements Result<T, E> {
    @Override
    @SuppressWarnings("unchecked")
    public <R> Result<R, E> map(Function<T, R> f) {
        return (Result<R, E>) this;
    }
    @Override
    public T orElseThrow() throws E {
        throw error;
    }
}

static Result<Verdict, SQLException> scoreApplicationAsResult(Application a) {
    try {
        return new Success<>(scoreApplication(a));
    } catch (SQLException e) {
        return new Failure<>(e);
    }
}
```

Consumed with a pattern-matching `switch` (Java 21, exhaustive over the sealed hierarchy — no `default` needed and the compiler rejects a missing branch):

```java
for (Application a : apps) {
    Result<Verdict, SQLException> result = scoreApplicationAsResult(a);
    switch (result) {
        case Success<Verdict, SQLException> s -> System.out.println("ok: " + s.value());
        case Failure<Verdict, SQLException> f -> System.out.println("failed: " + f.error().getMessage());
    }
}
```

Measured over `List.of(new Application("A1"), new Application("BAD"))`:

```
ok: Verdict[status=AO-400]
failed: cannot reach AssessmentService for BAD
```

And the terminal escape hatch, `orElseThrow`, measured to actually rethrow the original `SQLException` rather than a wrapper:

```
orElseThrow rethrew: cannot reach AssessmentService for BAD
```

`sealed interface` and `record` are both **Java 17**; a `Result` shaped this way was not expressible before then without an abstract class and manual `instanceof` chains, which is part of why the pattern only became idiomatic recently.

Cost: it does not integrate with `try`/`catch` at all until `orElseThrow` is called, so a caller who actually wants exception-style control flow — early return out of several nested calls via a `throw`, for instance — has to call `orElseThrow` and re-enter try/catch anyway, which means the type is only a net win when the caller was going to inspect the outcome explicitly regardless. And every intermediate `map` stage has to decide whether to short-circuit on `Failure` (as `Failure.map` does above, returning itself unchanged) or transform the error too — that decision is invisible in the type signature and has to be verified by reading the implementation, unlike checked exceptions, where the compiler at least forces every layer to acknowledge the possibility. Note also, plainly: **Java has no built-in `Result` type.** `Optional<T>` collapses failure to the single case "absent, no reason," which is not the same problem — a rules-store failure and "no verdict yet" are not interchangeable, and `Optional` cannot express *why* something failed. This is a real gap in the standard library that the language has not closed, not a case where the reader has simply missed the built-in name.

[02c-cost-and-control-flow.md](02c-cost-and-control-flow.md) owns exceptions as control flow and stack-trace cost in full; the one line to carry here is that `Result` is partly a response to that cost — a `Failure` record is a plain heap allocation with no captured stack trace, so building one is far cheaper than constructing and throwing an exception when a rules-store rejection is routine and frequent rather than genuinely exceptional.

[build-it/02-myinteger-and-generics.md](../build-it/02-myinteger-and-generics.md) builds a `Result<T, E>` again for its own §4.4 exercise; the two are not duplicates — that file is building the type from first principles as a generics exercise, this one is choosing it as one of four competing answers to a specific, narrower problem.

### Decision, not survey

Default to **wrap** with a named unchecked type. Escalate to a **custom `ThrowingFunction`** only at a boundary you own end to end, where the exception type itself is part of the contract. Escalate to **`Result`** when the failure is a normal branch of business logic that every caller must explicitly acknowledge, not an exceptional interruption. Never reach for **sneaky throw** as a matter of course — it is covered next, and it is not really a fifth option so much as a way of pretending the problem was never there.

### The diagram

No diagram for this concept: the evidence is two quoted `javac` diagnostics that are identical modulo the target construct, plus four short, complete programs, and the decision table above is the clearer rendering of the trade-offs than a picture would be.

### A concrete example

Given above, in full, for all four workarounds — each one compiled and run on JDK 21.0.7 rather than sketched.

### The gotcha

**Interview:** "Why can't you throw a checked exception from a lambda passed to `Stream.map`?" The one-line answer: you're not implementing a method of your own, you're implementing `Function.apply`, which was declared in Java 8 with no `throws` clause, so the ordinary catch-or-declare rule from `javac`'s earliest days refuses it — same as it would for an anonymous class or a named override of the same method.

> **Definition.** A lambda's checked-exception surface is exactly the `throws` clause of the functional interface method it implements, not a property of the lambda syntax itself — so `Function<T, R>` declaring no `throws` means no lambda assigned to it may let a checked exception escape, and the four ways around that are: catch and rethrow unchecked, exploit generic erasure to throw unchecked without declaring it, declare a custom functional interface that is allowed to throw, or replace the exception with a value.

Guide 04 (Modern Java) owns lambdas, streams, `Optional`, and records as constructs in their own right — target types, `invokedynamic` desugaring, the Streams pipeline model. This file only owns the one collision between lambdas and the checked-exception rule; refer there for the rest.

---

## 2. Sneaky throws: erasure, `@SneakyThrows`, and the loaded gun (2.6.4)

`[PROVE]` `[TRAP]` The mental model: sneaky throw is not a trick that fools the JVM. The JVM does not check checked exceptions at all — it never has, at any point in its history. Checked exceptions are a `javac` bookkeeping rule, enforced once, at compile time, and gone forever the moment class files exist. Sneaky throw is a small piece of code that convinces `javac` to stop enforcing its own rule against itself, at exactly one call site, by giving it a type variable to infer instead of a fixed exception type to check.

### Why it exists

Framework authors occasionally need to invoke a piece of caller-supplied code reflectively or through a generic callback — a JUnit `@Test` method, a `Runnable`-shaped hook — and propagate *whatever it threw*, unchanged, without knowing its static type ahead of time and without wrapping it in something that changes its `getClass()`. `Method.invoke` already wraps everything in `InvocationTargetException`, which is exactly the wrapping such a framework wants to avoid. Sneaky throw exists to solve that one narrow problem. What it is overwhelmingly used for instead is skipping the catch-or-declare rule in ordinary application code that has no such excuse.

### How it works — the mechanism, worked through

The method:

```java
@SuppressWarnings("unchecked")
static <E extends Throwable> void sneakyThrow(Throwable t) throws E {
    throw (E) t;
}
```

Two things happen at the call site, and both matter.

**Inference.** Called as `SneakyThrow.<RuntimeException>sneakyThrow(someCheckedException)`, or even with no explicit type witness at all — `javac` infers `E` from context, and with nothing constraining it, it defaults to `RuntimeException`. The compiler now believes this call can throw `RuntimeException` and nothing else, because that is what `E` was inferred to be. Under the catch-or-declare rule, `RuntimeException` needs no declaration and no catch — so the caller compiles clean, holding no declared checked exception at all.

**Erasure.** `E`'s upper bound is `Throwable`, so at the bytecode level `E` is erased to `Throwable`, and `(E) t` is a cast to `Throwable` — which is unconditionally true for any `Throwable` and therefore requires no runtime check. `javap` confirms this is not merely "erasure makes the cast unnecessary" as a theoretical claim but that no cast instruction is emitted at all. Measured, `javap -v -p` on the compiled `sneakyThrow`:

```
static <E extends java.lang.Throwable> void sneakyThrow(java.lang.Throwable) throws E;
  descriptor: (Ljava/lang/Throwable;)V
  flags: (0x0008) ACC_STATIC
  Code:
    stack=1, locals=1, args_size=1
       0: aload_0
       1: athrow
```

Two instructions: load the argument, throw it. No `checkcast`. The unchecked cast in the source (`(E) t`) produces literally nothing in the bytecode, because `E` erases to `Throwable` and every reference type is already a `Throwable`-compatible `athrow` operand if it is a `Throwable` at all — the JVM's `athrow` instruction does not care what static exception type the verifier believed was in flight. So the "trick" is entirely a compile-time fiction: at runtime, `sneakyThrow` just throws whatever `Throwable` it was given, unconditionally, and always did.

**Insight:** notice what the class file's `Exceptions` attribute says for this method — measured, `javap -v` reports `Exceptions: throws java.lang.Throwable`. That is the *erased bound*, not the inferred `RuntimeException` from any particular call site. The `Exceptions` attribute is metadata `javac` writes for other compilers to read (and `javac` itself does, when checking calls against a separately-compiled class) — the JVM's verifier and interpreter ignore it entirely at execution time. So there are two different erasures happening: the *generic method's own declared bound* erases to `Throwable` in the class file, while the *specific call site*, inferring against no fixed target, is checked by `javac` against `RuntimeException` and never revisited once compilation finishes.

Now the method that actually uses it, which is the one whose behavior matters to a caller:

```java
static Verdict scoreApplicationSneaky(Application a) {
    if (a.id().equals("BAD")) {
        SneakyThrow.<RuntimeException>sneakyThrow(
            new SQLException("cannot reach AssessmentService for " + a.id()));
    }
    return new Verdict("AO-400");
}
```

`scoreApplicationSneaky` declares no `throws` clause — measured, its own `javap -v` entry has no `Exceptions` attribute at all — yet running it against `new Application("BAD")` and catching broadly:

```
caught as Exception: java.sql.SQLException: cannot reach AssessmentService for BAD
```

The real `SQLException`, not a wrapper, not `RuntimeException`, caught by its true runtime type through a `catch (Exception e)` block. `getClass()` reports `java.sql.SQLException` exactly. This is the entire trick: a method with no `throws` clause, verified by `javap` to have none, throwing a checked exception that the runtime enforces no differently than any other `Throwable`, because the runtime was never enforcing checked-ness in the first place.

**The sharpest demonstration — the caller cannot catch it by name.** A caller who knows (from documentation, from reading the source, from a stack trace) that `SQLException` is really what comes out, and tries to write the honest, specific catch:

```java
try {
    scoreApplicationSneaky(new Application("BAD"));
} catch (SQLException e) {
    System.out.println("caught: " + e);
}
```

does not compile. Measured on JDK 21.0.7:

```
CannotCatchByName.java:19: error: exception SQLException is never thrown in body of corresponding try statement
        } catch (SQLException e) { // should not compile: never thrown per signature
          ^
1 error
```

`javac` has already proved — correctly, by its own rules — that nothing in `scoreApplicationSneaky`'s *signature* can throw `SQLException`, so a `catch` for it is dead code and rejected outright. The only way to catch this exception by name at the call site is to widen the catch to `Exception` or `Throwable`, discard the compiler's help entirely, and use `instanceof` at runtime to recover what it actually was. This is the sharpest way to state the danger: sneaky throw does not just make a checked exception uncatchable *by accident* — it makes catching it *by name* a compile error, in the very frame that is best placed to handle it specifically.

**Escaping through a library frame that has no idea it exists.** The failure gets worse, not better, the further it travels. A stand-in for a framework loop — `List.forEach`, or equally a Spring `TaskExecutor`'s submission loop — that accepts a plain `Consumer<Application>` and has no `throws` anywhere in its own call chain:

```java
static void libraryForEach(List<Application> apps, Consumer<Application> body) {
    apps.forEach(body); // library frame: no throws clause anywhere in its call chain
}
```

Measured, calling it with a `Consumer` backed by `scoreApplicationSneaky`:

```
escaped library frame as: java.sql.SQLException: cannot reach AssessmentService for BAD
```

`List.forEach`'s own signature is `void forEach(Consumer<? super T> action)` — no `throws` — and it propagated a checked `SQLException` through itself without complaint, because `forEach` never checked what it was calling could throw; it just called `accept`, and the JVM propagated whatever came out. If this library frame were, for instance, a fixed thread pool's worker loop that catches `Throwable` around each task specifically so one bad task doesn't kill the worker, the sneaky-thrown `SQLException` is caught there — correctly, since it is a `Throwable` — but logged and handled as "an unexpected error," with no upstream code ever having declared or expected it, because nothing in any signature between the throw site and the catch site said it could happen.

### Lombok's `@SneakyThrows`

**Unverified — documentation claim, not measured on this machine.** Lombok is not installed in this environment, so the following is drawn from Lombok's own published documentation rather than a compiled and disassembled example. Lombok's `@SneakyThrows` annotation, applied to a method, is described as doing the equivalent transformation at the bytecode level during annotation processing: it wraps the method body so that any declared checked exception (or, with no argument, any `Exception`) is thrown via the same erasure trick, without adding it to the method's `throws` clause. The documentation states it does **not** add anything to the method's signature — the whole point of the annotation is that the method looks, to every caller and to `javac`, exactly as if it threw nothing checked. Which checked exception types it applies to by default, and the exact bytecode shape Lombok's annotation processor emits (whether it literally reuses a generic erasure trick identical to the hand-written one above, or a different javac-tree-rewriting approach at the AST level before bytecode generation), was not independently confirmed here and is recorded in Open questions below.

### The verdict

Sneaky throws has exactly one defensible use: inside a framework's own reflective invocation path, where the framework must propagate whatever a user-supplied method threw, unmodified, without knowing its static type in advance, and without wrapping it in something like `InvocationTargetException` that would change what a caller's `catch` block matches against. That is a real, narrow, and rare need — JUnit's internal method-invocation machinery is a commonly cited example of legitimate use.

Outside that one case, sneaky throws does something strictly worse than either wrapping or declaring: it makes a checked exception **uncatchable by name in the very code that should be handling it**, as the "exception is never thrown" compile error demonstrates directly, while leaving every caller further up the stack with no signature-level warning that failure is even possible. It does not remove the possibility of failure — `AssessmentService` still fails exactly as often — it removes every trace of that possibility from the type system, which is the opposite of what checked exceptions on a JDBC-backed call were trying to buy in the first place.

Static analysis tooling flags it by name: **Error Prone**'s `SneakyThrows` check and **PMD**'s `AvoidUncheckedExceptionsInSignatures`-adjacent rules exist specifically because the pattern is common enough, and dangerous enough, to warrant a named lint rule rather than leaving it to code review.

Worth naming the *legitimate* narrowing mechanism next to this illegitimate one, so the two are never confused: [01b-catch-multicatch-and-precise-rethrow.md](01b-catch-multicatch-and-precise-rethrow.md) owns precise rethrow, where a method catches a broad checked type, does nothing to it, and rethrows it — and the compiler, since Java 7, is able to narrow the effectively-final rethrown variable back down to the specific checked types the `try` block could actually produce, entirely through ordinary flow analysis, no inference-and-erasure trick required. Precise rethrow keeps every declared type honest; sneaky throw exists to make them dishonest.

### The diagram

No diagram for this concept: the evidence is a two-instruction `javap` listing with no cast, a quoted "never thrown" compile error, and a measured runtime propagation through three separate call sites, and the prose above walking each one in order is the clearer rendering than a picture would be.

### A concrete example

Given above, in full: the generic method, its `javap -v` disassembly, the caller that cannot catch it by name, and the escape through a library `forEach` frame.

### The gotcha

**Pitfall:** reaching for a sneaky throw specifically to get a checked exception through a `Stream` pipeline, believing it is a lighter-weight alternative to wrapping. Wrong belief: "the exception isn't really gone, it's just not declared, so nothing is really lost." Symptom: six months later, a caller several layers up adds a targeted `catch (SQLException e)` around the exact call that produces it — because a stack trace in production clearly shows `SQLException` — and it fails to compile with "exception is never thrown in body of corresponding try statement," at which point the only fix available *without touching the sneaky-throwing method* is to widen the catch to `Exception`, which now also silently swallows every other runtime failure in that block. Fix: use workaround 1 (wrap in a named unchecked type) instead — it costs one `try`/`catch` and an extra class, and in exchange the failure is visible in the type of exception thrown, catchable by that specific name, and self-documenting to the next reader, none of which sneaky throw offers.

> **Definition.** A generic method `<E extends Throwable> void sneakyThrow(Throwable t) throws E` throwing `(E) t` compiles a checked exception past `javac`'s catch-or-declare check because `E` is inferred as `RuntimeException` with no fixed target, and at the bytecode level `E` erases to its bound (`Throwable`), so the cast is unconditionally valid and compiles to zero instructions — `athrow` alone, no `checkcast` — meaning the runtime throws exactly what it was given, uncatchable by name at any call site the compiler has proven cannot see it coming.

Erasure in full — why a generic type parameter has no runtime representation at all, and every other consequence of that beyond this one trick — is [../generics/03-internals-erasure.md](../generics/03-internals-erasure.md); that file is a later batch and owns the mechanism end to end, this file only gives the one paragraph needed to follow the trick. Unchecked casts and `@SuppressWarnings("unchecked")` as their own topic — when the suppression is legitimate versus when it is hiding a real bug — is [../generics/02-in-anger.md](../generics/02-in-anger.md), also a later batch. The bytecode-level treatment of ordinary (non-generic) exception throwing and the `athrow` instruction in general is [03-internals-exception-mechanics.md](03-internals-exception-mechanics.md); this file's `javap` listing is the one instance of that mechanism worth seeing here, not a substitute for that file's fuller treatment.

---

## Pitfalls

### Reaching for a sneaky throw to get a checked exception through a stream

**Wrong**

```java
static Verdict scoreApplicationSneaky(Application a) {
    if (a.id().equals("BAD")) {
        SneakyThrow.<RuntimeException>sneakyThrow(
            new SQLException("cannot reach AssessmentService for " + a.id()));
    }
    return new Verdict("AO-400");
}

apps.stream().map(EscapeLibraryFrame::scoreApplicationSneaky).forEach(System.out::println);
```

Compiles clean and runs — until a caller writes `catch (SQLException e)` around the exact call that produces it, guided by a stack trace that plainly shows `SQLException`, and gets `error: exception SQLException is never thrown in body of corresponding try statement`. Measured on JDK 21.0.7 with exactly this shape.

**Right**

```java
static Function<Application, Verdict> wrapWorkaround() {
    return a -> {
        try {
            return scoreApplication(a);
        } catch (SQLException e) {
            throw new AssessmentUncheckedException("scoring failed for " + a.id(), e);
        }
    };
}

apps.stream().map(wrapWorkaround()).forEach(System.out::println);
```

`AssessmentUncheckedException` is catchable by name — because it is genuinely the type in flight, not a checked exception wearing an inferred `RuntimeException` mask — and `getCause()` still carries the original `SQLException` for anyone who needs the detail.

**Why people believe it:** the sneaky-thrown exception really is the original object — same class, same message, same stack trace — so it looks strictly better than wrapping, which changes the runtime type. What is missing from that comparison is that `javac`'s catch-or-declare check runs against the *declared* signature, not the runtime type, and the declared signature is exactly what the trick erased away.

### Treating `ThrowingFunction` as a drop-in replacement for `Function`

**Wrong**

```java
ThrowingFunction<Application, Verdict, SQLException> scorer = Workarounds::scoreApplication;
apps.stream().map(scorer).forEach(System.out::println);  // does not compile
```

`Stream.map` is declared as `<R> Stream<R> map(Function<? super T, ? extends R> mapper)` — it was typed against `java.util.function.Function` in Java 8 and has never been retrofitted with an overload for arbitrary functional interfaces, so a `ThrowingFunction` is simply the wrong type for that parameter.

**Right**

```java
apps.stream().map(ThrowingFunction.unchecked(scorer)).forEach(System.out::println);
```

`ThrowingFunction.unchecked` is the deliberate crossing point: it converts a checked-exception-aware interface into a plain `Function` exactly once, at the boundary where the JDK's combinator needs one, so the custom interface's benefit (compiler-checked exception types) is kept everywhere inside your own code and only given up at the point of unavoidable contact with `java.util.stream`.

**Why people believe it:** a `ThrowingFunction<T, R, E>` looks, structurally, like a strict superset of `Function<T, R>` — same shape, plus a `throws` clause — so it is easy to assume anywhere a `Function` is accepted, a `ThrowingFunction` should be too. Java's functional interfaces are matched by exact declared type for a method parameter, not by structural compatibility, so the superset intuition does not transfer.

### Assuming `Result<T, E>` replaces exception handling everywhere it appears

**Wrong**

```java
Result<Verdict, SQLException> result = scoreApplicationAsResult(a);
Verdict v = result.orElseThrow();  // compiles, but the checked exception is back
processVerdict(v);
```

written inside a method with no `throws SQLException` and no surrounding `try`/`catch` — which will not compile, correctly, because `orElseThrow` is declared `T orElseThrow() throws E`. The mistake is thinking `Result` has made the exception disappear rather than deferred it: it is still there, waiting at the one method that lets it out.

**Right**

Handle both branches explicitly with the exhaustive switch, and only reach for `orElseThrow` at a boundary that is prepared to declare or catch `SQLException`:

```java
switch (scoreApplicationAsResult(a)) {
    case Success<Verdict, SQLException> s -> processVerdict(s.value());
    case Failure<Verdict, SQLException> f -> logAssessmentFailure(a, f.error());
}
```

**Why people believe it:** `Result` genuinely does remove the *ceremony* of try/catch at every intermediate `map` stage, which reads as removing the exception itself. It only removes it from the stages that choose to short-circuit; the terminal `orElseThrow` puts the compiler's original catch-or-declare requirement right back, which is by design — `Result` is explicit deferral, not elimination.

---

## Cheat sheet

| Thing | Fact (Java 21 LTS) |
|---|---|
| `Function.apply` signature | `R apply(T t)`, no `throws`, unchanged since Java 8 |
| Root cause | ordinary catch-or-declare rule applied to the functional interface's method — not a lambda-specific rule |
| Anonymous class control | identical diagnostic, same column, same rule — proves it is not lambda syntax at fault |
| Measured diagnostic | `error: unreported exception SQLException; must be caught or declared to be thrown` |
| Workaround 1 — wrap | catch, rethrow as a named unchecked type; checked-ness lost from the signature |
| JDK's own precedent | `UncheckedIOException` (Java 8), `BufferedReader.lines()` / `Files.lines()` |
| Workaround 2 — sneaky throw | compiles past the check via inference + erasure; see below |
| Workaround 3 — custom interface | `ThrowingFunction<T, R, E extends Exception>`; compiler-checked, does not compose with `Stream.map` |
| Workaround 4 — `Result<T, E>` | sealed interface + records (Java 17+); no JDK built-in; `Optional` is not a substitute (no failure reason) |
| Sneaky-throw method | `<E extends Throwable> void sneakyThrow(Throwable t) throws E { throw (E) t; }` |
| Inference at call site | with no fixed target, `E` infers to `RuntimeException` — no declaration required |
| Erasure at the method | `E` erases to its bound, `Throwable`; measured bytecode is `aload_0; athrow` — **no `checkcast`** |
| Class-file `Exceptions` attribute, `sneakyThrow` itself | `throws java.lang.Throwable` (the erased bound) — present, not absent |
| Class-file `Exceptions` attribute, the calling method | **absent** — measured no `Exceptions` entry, so it declares nothing checked |
| Runtime behavior | throws the exact original object; `getClass()` reports the true checked type |
| Catching by name | **fails to compile**: `error: exception SQLException is never thrown in body of corresponding try statement` |
| Escaping a library frame | propagates unchanged through `List.forEach` and similar JDK combinators with no `throws` anywhere in the chain |
| Lombok `@SneakyThrows` | same effect via annotation processing — **Unverified** on this machine; documentation claim only |
| Defensible use | inside a framework's own reflective invocation path, propagating an unknown caller exception unwrapped |
| Tools that flag it | Error Prone's `SneakyThrows` check, PMD |

---

## Self-test

**Q1.** Why does `Function<T, R>` reject a lambda body that throws `SQLException`, and is this a lambda-specific rule?

<details><summary>Answer</summary>

It is not lambda-specific. `Function.apply` is declared `R apply(T t)` with no `throws` clause, a design decision made when `java.util.function` was added in Java 8 and never revisited. A lambda assigned to `Function<T, R>` is implementing that exact method, so it inherits that exact signature, and the ordinary catch-or-declare rule — the same rule that has applied to every method override since Java 1.0 — applies to the lambda body as if it were a named override. Measured proof that it is the signature and not the syntax: an anonymous class implementing `Function.apply` the long way, calling the same checked-throwing method, produces the identical compile error at the identical column as the lambda does — `error: unreported exception SQLException; must be caught or declared to be thrown` in both cases. The confusing part is that the message points at the call site inside the lambda body, not at `Function.apply`'s declaration, so nothing in the diagnostic itself tells you which interface's signature is the actual constraint.

</details>

**Q2.** Name the four workarounds for getting a checked-exception-throwing method into a `Function<T, R>`, and give one cost for each.

<details><summary>Answer</summary>

Wrap: catch the checked exception inside the lambda and rethrow it as an unchecked type. Cost: the checked-ness disappears from the signature, so nothing warns a caller further up that failure is possible; they find out from documentation or from a runtime exception message. Sneaky throw: use generic inference plus erasure to throw the checked exception with no unchecked wrapper and no declaration at all. Cost: the exception becomes uncatchable *by name* at any call site the compiler believes cannot produce it — worse than wrap, not better, because wrap at least gives you a real declared type to catch. Custom functional interface: declare a `ThrowingFunction<T, R, E extends Exception>` whose `apply` is allowed `throws E`. Cost: it does not compose with the JDK's own combinators — `Stream.map` and `Function.andThen` are typed against `java.util.function.Function`, so a `ThrowingFunction` needs an adapter (itself workaround 1, localized) the moment it crosses into `java.util.stream`. `Result<T, E>`: a sealed interface with `Success`/`Failure` records, consumed with a pattern-matching `switch`. Cost: it does not integrate with `try`/`catch` until a terminal `orElseThrow` is called, every intermediate `map` stage must decide whether to short-circuit on failure (invisible in the type signature), and there is no JDK built-in `Result` type to reach for — `Optional` is not a substitute because it cannot carry a failure reason.

</details>

**Q3.** Explain why a sneaky-thrown `SQLException` cannot be caught by name at the call site.

<details><summary>Answer</summary>

Because `javac` has already proved, from the calling method's declared signature, that no checked exception can escape it — and a `catch` clause naming an exception type that the compiler has determined cannot be thrown inside the corresponding `try` block is a compile error, not a warning. The sneaky-throwing method (`scoreApplicationSneaky` in this file's example) declares no `throws` clause at all — measured via `javap -v`, it has no `Exceptions` attribute — because the generic helper it calls, `sneakyThrow`, was invoked with `E` inferred as `RuntimeException` with no fixed target, and `RuntimeException` requires no declaration. So from `javac`'s point of view, wrapping the call in a `try` block with `catch (SQLException e)` around it is dead code: nothing in the visible signature can throw `SQLException`. Measured on JDK 21.0.7, attempting exactly that produces `error: exception SQLException is never thrown in body of corresponding try statement`. The only way to catch it by name is to know from outside the type system — a stack trace, the source of `sneakyThrow` itself — that it is really an `SQLException`, catch it as `Exception` or `Throwable`, and use `instanceof` at runtime, which gives up the compiler's help entirely rather than merely losing it, as wrapping does.

</details>

**Q4.** Walk the mechanism of `<E extends Throwable> void sneakyThrow(Throwable t) throws E { throw (E) t; }` in two steps, and say what each step contributes.

<details><summary>Answer</summary>

Step one is type inference at the call site. Called with no fixed target type constraining `E` — for instance `SneakyThrow.<RuntimeException>sneakyThrow(someSqlException)`, or with no explicit witness at all and `E` left to default — `javac` infers `E` as `RuntimeException`. Under that inference, the method's declared `throws E` becomes, from the caller's point of view, `throws RuntimeException`, which needs no declaration and no catch under the ordinary rule. That is the entire compile-time trick: nothing about it involves the actual exception object yet, only what type the compiler believes the call site is bound to. Step two is erasure at the method itself. `E`'s upper bound is `Throwable`, so at the bytecode level — where generic type parameters have no runtime representation — `E` erases to `Throwable`, and the cast `(E) t` becomes a cast to `Throwable`. Since every argument passed in is already statically a `Throwable`, that cast is unconditionally valid and the compiler emits it as nothing at all. Measured `javap -v -p` on the compiled method: `stack=1, locals=1, args_size=1` / `0: aload_0` / `1: athrow` — two instructions, no `checkcast` anywhere. So at runtime the method does exactly what `throw t;` on an unchecked reference would do: push the argument, throw it, unconditionally, regardless of what static type any caller believed was in flight.

</details>

**Q5.** What does the class file's `Exceptions` attribute say for `sneakyThrow` itself, versus for the method that calls it — and why are they different?

<details><summary>Answer</summary>

Measured on JDK 21.0.7: `sneakyThrow`'s own `Exceptions` attribute reads `throws java.lang.Throwable`, while the calling method (`scoreApplicationSneaky`) has **no** `Exceptions` attribute at all. They differ because they are erasures of two different things. `sneakyThrow` is a generic method whose type parameter `E` is bounded by `Throwable`; when `javac` writes the class file's `Exceptions` attribute for a generic method, it uses the *erased bound* of the type variable, because the `Exceptions` attribute (unlike the separate `Signature` attribute, which does preserve the full generic form as metadata) has no way to express a type variable — so `throws E` becomes `throws Throwable` in that attribute, independent of any specific call site. `scoreApplicationSneaky`, by contrast, is not generic at all from its own declaration's point of view; its `throws` clause is whatever `javac` determined it needed while type-checking its body, and because the one call to `sneakyThrow` inside it was checked with `E` inferred as `RuntimeException` — which needs no declaration — `javac` concluded the method declares nothing checked, and wrote no `Exceptions` attribute for it. The generic method's *class-file-level* declaration is the erased bound; the *calling* method's declaration is whatever the specific, already-resolved call sites required, and neither one is influenced by what actually gets thrown at runtime.

</details>

**Q6.** A framework's `TaskExecutor` loop calls user-supplied code through a sneaky throw, and the checked exception it throws escapes into `List.forEach`. What happens, and why doesn't `forEach` block it?

<details><summary>Answer</summary>

It propagates through cleanly, exactly as any unchecked exception would, because `List.forEach` never inspected what its `Consumer` argument could throw — it simply calls `accept` and lets the JVM's normal exception-propagation mechanism take over. `forEach`'s own signature, `void forEach(Consumer<? super T> action)`, declares no `throws` and has no code path that catches anything, so a `Throwable` escaping the `Consumer` unwinds straight through `forEach`'s frame and every frame above it, same as it would if the checked-ness had never existed. Measured with a stand-in library loop calling `scoreApplicationSneaky` through a `Consumer`: `escaped library frame as: java.sql.SQLException: cannot reach AssessmentService for BAD` — the exact checked type, propagated through a JDK method with no awareness of it. This is the sharpest cost of sneaky throw in a real system: the exception does not merely lose its declaration at the throwing method, it loses it at *every* frame between there and wherever something finally catches broadly enough to see it — and any of those frames could be a library boundary that treats "unexpected `Throwable`" differently from "expected, declared failure," for instance a thread-pool worker that catches `Throwable` around each task to avoid killing the worker thread, logging it as an unanticipated error even though, semantically, it was entirely anticipated by the code that produced it.

</details>

**Q7.** When is sneaky throw the right tool, and when is wrapping strictly better?

<details><summary>Answer</summary>

Sneaky throw is defensible in exactly one situation: inside a framework's own reflective or generic invocation path, where the framework must propagate whatever a caller-supplied piece of code threw, completely unmodified — same class, same message, same stack trace — without knowing its static type in advance, and specifically without wrapping it in something like `InvocationTargetException` that would change what type a caller's `catch` block needs to match. That need is real but narrow; JUnit's own internal test-invocation machinery is a commonly cited legitimate example. Everywhere else, wrapping is strictly better, for one concrete reason demonstrated in this file: wrapping produces a *real*, declared, catchable-by-name exception type, at the cost of changing the runtime class of the propagated failure — a cost that is visible and documentable. Sneaky throw preserves the original runtime class but makes it uncatchable by name at exactly the frame most likely to want to catch it specifically, which is a worse trade in ordinary application code: the failure is not merely undeclared, as wrapping's unchecked type also is, it is actively hostile to a caller who already knows, from a stack trace or from reading the source, what it really is and tries to write the correct, specific handler for it.

</details>

---

## Open questions

- **Unverified:** the exact bytecode shape Lombok's `@SneakyThrows` annotation processor emits, and the complete list of exception types it applies to by default versus when given an explicit type argument. Lombok is not installed on this machine; the claims above (no signature change, effect equivalent to the hand-written erasure trick) are drawn from Lombok's own published documentation, not from a compiled and disassembled example. What would settle it: install Lombok, annotate a method equivalent to `scoreApplicationSneaky` with `@SneakyThrows(SQLException.class)`, and run the identical `javap -v -p` and "never thrown" compile-error checks performed by hand in this file against the annotation-processed output.
- **Unverified:** whether Error Prone's `SneakyThrows` check and the relevant PMD rule were confirmed to exist and fire on this exact pattern by running them, or are cited from their published rule documentation. Not run in this environment. What would settle it: run Error Prone and PMD against `SneakyThrow.java` from this file's scratch directory and confirm both flag `sneakyThrow`'s definition or its call sites.

---

**Leaves covered:** 2.6.3, 2.6.4 (2 leaves)
**Leaves deferred:** none
**Diagrams included:** none
**Target version:** Java 21 LTS
**Lines:** 594
