# 03 Java Core — Resources, interrupts and testing in practice — INTERMEDIATE (§2.6.17–2.6.23)

**Target version: Java 21 LTS.** | **Part 2 of 5** | [Index](../00-index.md)
Previous: [Logging discipline and API boundaries](02d-logging-and-api-boundaries.md) · Next: [Exception mechanics — the exception table](03-internals-exception-mechanics.md)

Five things that only show up once the mechanics of `01c` and `01e` are load-bearing in real code rather than demonstration snippets: a `try`-with-resources block with more than one moving part, a resource type whose author has to decide what `close()` promises, a thread that has to decide what an `InterruptedException` means for *it*, a validation strategy that has to decide how many errors to report at once, and a test that has to decide what to assert about a thrown exception besides "one was thrown." None of these are new syntax. All five are places experienced engineers get the *decision* wrong even when they get the mechanism right.

Measured claims are against **Oracle JDK 21.0.7 (21.0.7+8-LTS-245, macOS aarch64)**. JUnit 5 and `jakarta.validation` are not installed on this machine; wherever their APIs appear below, the code is a **documentation check** — verified against the JUnit 5 Jupiter API javadoc and the Jakarta Bean Validation 3.0 specification as reproduced in widely mirrored primary documentation, not compiled here — and is called out as such at the point it appears.

---

## 1. `try`-with-resources in practice: multiple resources, a null resource, an idempotent `close()` (2.6.17)

### Mental model

`01c` establishes the mechanism: declare several resources in one `try`, they close in reverse order, all before any `catch`. This concept is about the three shapes that mechanism runs into once it is doing real work — a batch job with two resources whose lifetimes genuinely nest, a factory that can hand back `null` instead of a resource, and a `close()` method that a production incident calls twice.

### Why it exists

Nobody designs a resource-handling bug on purpose. Multiple-resource declarations, null resources and double-`close()` calls are not corner cases invented for an exam — they are what a `PaymentRun` batch job actually does: it opens a `LedgerConnection` and a `PaymentRunFileWriter` together, a lookup that is supposed to hand back a live connection occasionally hands back `null` because of a caching bug upstream, and a `close()` gets called once by the `try`-with-resources block and once more by a `Cleaner`-based backstop (`../objects-equality-and-lifecycle/03a-finalization-cleanup-and-leaks.md`) registered as insurance against a caller that forgets to use `try`-with-resources at all.

### When to reach for one `try` versus nesting

Reach for one `try` with a semicolon-separated resource list — the default, and correct in the overwhelming majority of cases — whenever the resources are independent enough that "close whichever ones finished constructing, in reverse order" (`01c` concept 1) is exactly the policy you want. That is true of `LedgerConnection` and `PaymentRunFileWriter` in the ordinary `PaymentRun` case: the writer depends on the connection being open while it runs, so declaring the connection first and the writer second gives the correct reverse-close order for free.

Nest two `try`-with-resources statements instead when a resource's *construction* genuinely depends on a value only obtainable from a resource already open **and** the first resource must be closed under a different policy than "close it when the block exits" — for instance, a `LedgerConnection` that is checked out from a pool and must be returned to the pool (not physically closed) only after every downstream write using it has both succeeded and been durably flushed, so its release has to be the very last statement of an outer block, conditioned on the inner block's outcome, rather than an automatic close at the inner block's end:

```java
try (LedgerConnection ledger = pool.checkOut()) {
    PaymentRunId runId = ledger.beginRun();
    try (PaymentRunFileWriter file = new PaymentRunFileWriter(runId)) {
        file.writeBatch(ledger.pendingWithdrawals(runId));
    }
    ledger.commitRun(runId);   // only reached if the inner block closed cleanly
}
```

A single flat `try` with both resources declared together cannot express "commit after the inner resource has closed and only if it closed without throwing" — the flat form's `finally`-equivalent runs both closes unconditionally, in reverse order, with no seam to insert `commitRun` in between. That seam is the entire reason to nest.

### How it works — the null resource

`01c`'s supporting-fact section on effectively-final resources already measured the mechanism: any resource expression that is a variable reference, not a `new` expression, gets a compiler-emitted `ifnull` guard around the close call, so `close()` is never invoked on a `null` resource and the `try` statement's own cleanup step completes without incident. What that supporting fact does not spell out, and what matters in practice, is that a null resource is not "handled" by this guard — it is a bug the guard merely keeps from throwing a *second* time. The body almost always dereferences the resource, and a `null` resource used inside the body throws `NullPointerException` from the body itself, before the guarded close ever runs.

Measured on JDK 21.0.7, a factory returning `null` where a live `LedgerConnection` was expected:

```java
static LedgerConnection openLedger() {
    return null; // simulates a caching bug upstream
}

public static void main(String[] args) {
    LedgerConnection nullLocal = openLedger();
    try (LedgerConnection ledger = nullLocal) {
        System.out.println("body: about to call debit on possibly-null ledger");
        ledger.debit();
        System.out.println("body: never reached");
    } catch (NullPointerException e) {
        System.out.println("caught NPE: " + e.getMessage());
    }
    System.out.println("completed normally after guarded null close");
}
```

printed:

```
body: about to call debit on possibly-null ledger
caught NPE: Cannot invoke "NullResource$LedgerConnection.debit()" because "<local2>" is null
completed normally after guarded null close
```

`javap` confirms the shape: the body's `invokevirtual LedgerConnection.debit:()V` runs and throws before the `ifnull` guard at the close site is ever reached at all — that guard exists purely to protect the *close step itself* from an NPE, on the path where the body somehow completed (or threw something the guard's exception handling can still route around) without ever touching the null reference. Both halves of the claim are now measured: the close is genuinely guarded (`01c`'s finding), and the guard buys nothing for a body that dereferences the resource, which is the normal case.

**The fix is not a null-tolerant resource.** Do not write `LedgerConnection` to treat a `null` internal handle as a legal, do-nothing state — that turns a caching bug into a silent no-op that looks like a successful debit never happened. Fail at the boundary instead:

```java
LedgerConnection ledger = Objects.requireNonNull(
    ledgerPool.checkOut(runId), () -> "no ledger connection available for run " + runId);
try (ledger) {
    ledger.debit(accountId, amount);
}
```

`02b-designing-an-exception-hierarchy.md` owns `Objects.requireNonNull` and fail-fast as a general discipline; this is that discipline applied at the specific point a resource enters a `try`-with-resources block, which is exactly where a `null` is most easily missed because the construct's own null handling looks, at a glance, like it is doing something protective.

### How it works — the idempotent `close()`

`close()` gets called more than once in real code for three unrelated reasons, all of which show up in `PaymentRun` code specifically: a hand-written cleanup path in a `catch` block that also calls `close()` before the `try`-with-resources block's own implicit close runs on the same object (possible when the resource is stored in an outer variable, as `01c`'s pitfall on scope shows); a `Cleaner` registered as a garbage-collection-time backstop (`../objects-equality-and-lifecycle/03a-finalization-cleanup-and-leaks.md`) that runs `close()` again if the object is ever collected while still open; and a framework — a connection-pool wrapper, a Spring `DisposableBean` callback — that closes what application code has already closed, because the framework has no visibility into whether the application got there first.

Two idempotent forms, and which to use when. The single-threaded form, a `boolean` flag:

```java
private boolean closed = false;

@Override
public void close() {
    if (closed) {
        return;
    }
    closed = true;
    releaseUnderlyingHandle();
}
```

Measured, three calls against this shape and against a non-idempotent `close()` that has no guard at all:

```
NonIdempotent.close() call #1 -- releasing again
NonIdempotent.close() call #2 -- releasing again
NonIdempotent total effect count: 2
Idempotent.close() actually releasing
Idempotent.close() no-op (already closed)
Idempotent.close() no-op (already closed)
Idempotent actual release count: 1
```

The `boolean` form is correct for a resource that is only ever closed from a single thread — the ordinary case for a `try`-with-resources local variable. It is **not** correct if two threads can call `close()` concurrently: a plain `boolean` read-then-write is not atomic, so two threads racing through `if (closed) return; closed = true;` can both observe `closed == false` and both run `releaseUnderlyingHandle()`. The concurrent-safe form uses `AtomicBoolean.compareAndSet`:

```java
private final AtomicBoolean closeAttempted = new AtomicBoolean(false);

@Override
public void close() {
    if (!closeAttempted.compareAndSet(false, true)) {
        return;
    }
    releaseUnderlyingHandle();
}
```

`compareAndSet(false, true)` atomically checks-and-sets in one hardware operation; exactly one caller among any number of concurrent callers observes it return `true` and proceeds to the real release, and every other caller observes `false` and returns immediately. Use the plain `boolean` when the resource's contract guarantees single-threaded access (the common case, and the cheaper one — no atomic, no memory fence); use `AtomicBoolean` when the resource can plausibly be closed from more than one thread, which a pooled connection or a `Cleaner`-backed resource genuinely can, since the `Cleaner`'s cleanup thread and the application's own `try`-with-resources close can race.

The asymmetry worth knowing cold: `Closeable`'s javadoc states its `close()` contract in these exact words, quoted from the JDK 21 source —

> "Closes this stream and releases any system resources associated with it. If the stream is already closed then invoking this method has no effect."

`AutoCloseable`'s javadoc, by contrast, says the opposite about its own narrower interface, also quoted verbatim —

> "Note that unlike the close method of Closeable, this close method is not required to be idempotent. In other words, calling this close method more than once may have some visible side effect, unlike Closeable.close which is required to have no effect if called more than once. However, implementers of this interface are strongly encouraged to make their close methods idempotent."

So `Closeable` (which `Closeable extends AutoCloseable`, `01c` concept 1's self-test Q7) *mandates* idempotence as part of its contract; `AutoCloseable` *recommends* it but explicitly declines to require it, because the interface is meant to be implementable by things — a lock-like resource whose second release should legitimately be an error, for instance — where idempotence would hide a real caller bug. `LedgerConnection` and `PaymentRunFileWriter` implement `AutoCloseable` directly, not `Closeable`, so idempotence is this file's design choice, not a language-enforced obligation — and the choice, for exactly the double-close reasons above, should be to make it idempotent anyway.

### Diagram

No diagram for this concept: the null-resource evidence is one measured NPE stack line plus one `javap` fact already established in `01c`, and the idempotence evidence is a four-line print comparison — both are clearer as the quoted output above than as a picture of the same four lines.

### The gotcha

**Pitfall:** treating the null-resource guard as proof that a `null` factory result is "safely handled." It is not — see the fix above, `Objects.requireNonNull` at the point the resource is obtained, not a defensive null check woven into the resource type itself.

> **Definition.** A `try`-with-resources block guards a non-`new`-expression resource's close against `null` with a compiler-emitted `ifnull` check, but a `null` resource almost always throws from the *body* first; idempotence is a property the resource author chooses to provide — mandatory for `Closeable`, merely recommended for `AutoCloseable` — using a plain `boolean` flag under single-threaded access and `AtomicBoolean.compareAndSet` under concurrent access.

---

## 2. Custom `AutoCloseable`: declaring `close()` without `throws` (2.6.18)

`[BUILD]`

### Mental model

`AutoCloseable.close()` is declared `void close() throws Exception`. An overriding implementation is free to **narrow** that `throws` clause — to a specific checked exception type, or to nothing at all — because Java's override rules permit a subtype to declare a narrower (or absent) checked-exception clause than the method it overrides, never a broader one. Every resource type author therefore makes one of three choices, and the choice determines what every single caller's `try`-with-resources block is forced to write.

### Why it exists

If `LedgerConnection.close()` were left at the interface's own `throws Exception`, every caller doing `try (LedgerConnection ledger = new LedgerConnection(connectionId)) { ledger.debit(accountId, amount); }` with no attached `catch` would fail to compile — `javac` requires a checked exception from an implicit close call to be caught or declared, exactly as it would for an explicit method call (measured below). Multiply that by every call site across the payments codebase, and the interface's maximal generality becomes a tax paid at every single use. Narrowing the `throws` clause is the resource author paying that tax once, in one place, instead of every caller paying it everywhere.

### When to reach for it, and when not

Reach for a no-`throws` `close()` whenever the resource's own close operation can be made to never propagate a checked failure — which, for the overwhelming majority of application-level resource types (a ledger handle, a batch file writer wrapping a controlled write path), it can, provided the author is willing to decide what to do with a close failure *inside* `close()` rather than handing it to the caller. Reach for a narrower checked type (`throws IOException`, as `Closeable` does) when the resource genuinely wraps I/O whose failure the caller needs to see and react to specifically — a network-backed stream where "the flush at close time failed" is itself operationally significant to the caller, not just to the resource's own internals. Never leave it at the interface's own `throws Exception` for a concrete type; that is only correct for a generic method that is itself forwarding an unknown `AutoCloseable`'s close.

### How it works — the three signatures, measured

All three compile as overrides of `AutoCloseable.close()`, because narrowing is legal in every direction shown:

| Declared `close()` | What the caller must write | Compiles with no `catch`? |
|---|---|---|
| `void close() throws Exception` | `catch (Exception e)` or declare `throws Exception` on the enclosing method | No |
| `void close() throws IOException` | `catch (IOException e)` or declare `throws IOException` | No |
| `void close()` | Nothing — no `catch`, no `throws` needed | Yes |

Measured on JDK 21.0.7, a resource type declaring `throws Exception` used with no attached `catch`:

```java
static class WideClose implements AutoCloseable {
    @Override public void close() throws Exception { }
}

static void callerNoCatch() {
    try (WideClose w = new WideClose()) {
        System.out.println("body");
    }
}
```

fails to compile:

```
SigFail.java:6: error: unreported exception Exception; must be caught or declared to be thrown
        try (WideClose w = new WideClose()) {
                       ^
  exception thrown from implicit call to close() on resource variable 'w'
1 error
```

The compiler's own diagnostic names the mechanism precisely: the *implicit* close call at the end of the `try`-with-resources block is treated exactly like an explicit method call for checked-exception purposes. The identical three-resource caller with `IoClose implements AutoCloseable { public void close() throws IOException { } }` requires `catch (IOException e)` instead, and with `NarrowClose implements AutoCloseable { public void close() { } }` requires nothing — measured, all three compile and run cleanly once each caller matches its resource's declared `throws` clause, and the narrow-`close()` caller compiles with no `catch` at all.

### Diagram

No diagram for this concept: the evidence is one compile failure and a three-row table, and a picture of "does it compile" adds nothing to the table.

### A concrete example — `LedgerConnection`, compiled

The honest cost of narrowing `close()` to no `throws`: the resource author has taken on the obligation to *handle* a close failure internally, since there is no longer a checked exception to hand the caller. "Handle" here means log at `WARN` and increment a metric, never silently discard — a close failure on a `LedgerConnection` in production, however rare, means a handle may have leaked, and an on-call engineer needs to be able to find that in the logs even though no exception propagated. Measured, compiles and runs on JDK 21.0.7:

```java
import java.util.concurrent.atomic.AtomicBoolean;

public class LedgerConnection implements AutoCloseable {

    private enum State { OPEN, CLOSED }

    private State state = State.OPEN;
    private final AtomicBoolean closeAttempted = new AtomicBoolean(false);
    private final String connectionId;

    public LedgerConnection(String connectionId) {
        this.connectionId = connectionId;
    }

    public void debit(String accountId, java.math.BigDecimal amount) {
        if (state == State.CLOSED) {
            throw new IllegalStateException(
                "LedgerConnection " + connectionId + " is closed");
        }
        System.out.println("debit " + amount + " from " + accountId + " on " + connectionId);
    }

    @Override
    public void close() {
        if (!closeAttempted.compareAndSet(false, true)) {
            System.out.println("close: " + connectionId + " already closed, no-op");
            return;
        }
        state = State.CLOSED;
        try {
            releaseUnderlyingHandle();
        } catch (RuntimeException underlyingFailure) {
            // Policy: a close failure here does not propagate. Log at WARN and
            // increment a metric so it is diagnosable, rather than silently
            // discarded, and rely on the connection pool's own reaper to
            // eventually reclaim a handle this call failed to release cleanly.
            System.out.println("WARN: close failed for " + connectionId
                + ", handle leaked until connection pool reaper reclaims it: "
                + underlyingFailure.getMessage());
        }
    }

    private void releaseUnderlyingHandle() {
        System.out.println("close: " + connectionId + " releasing underlying handle");
    }
}
```

Measured output for `new LedgerConnection("conn-771")` used in a `try`-with-resources block with a `debit` call, then closed twice more explicitly afterward:

```
debit 42.00 from client-4821 on conn-771
close: conn-771 releasing underlying handle
close: conn-771 already closed, no-op
close: conn-771 already closed, no-op
```

No `catch` clause appears anywhere at any of the three call sites, which is the entire point: `close()` declares no `throws`, so callers write plain `try (LedgerConnection ledger = new LedgerConnection("conn-771")) { ledger.debit("client-4821", amount); }` and move on. The cost is fully inside `close()` — the `catch (RuntimeException underlyingFailure)` block is where a real implementation would call `log.warn("close failed for {}", connectionId, underlyingFailure)` (`02d-logging-and-api-boundaries.md` owns the logging call shape) and increment a counter such as `ledger.connection.close.failed`, never silently swallow it. Swallowing it with no trace at all — no log line, no metric — would be the exact failure `01e` concept 1 already names: a `catch` block that neither rethrows nor logs is swallowing, and narrowing `close()`'s `throws` clause does not exempt the implementer from that rule; it just moves where the rule has to be honored, from every caller to this one method.

### The gotcha

**Interview:** "Why would you ever declare `close()` without `throws`, given the interface allows `throws Exception`?" One-line answer: because every caller's `try`-with-resources block otherwise has to catch or declare `Exception`, and narrowing that obligation once in the resource type is strictly better than paying it at every call site — at the cost of the resource author now owning what happens when the underlying close operation actually fails.

> **Definition.** `AutoCloseable.close()` is declared `throws Exception`; an implementation may narrow the clause to a specific checked type or to nothing at all, and the caller's obligation at every `try`-with-resources site — catch it, declare it, or write nothing — is fixed entirely by that declared clause, which is why the resource author's choice of `throws` clause is a caller-facing API decision, not an implementation detail.

---

## 3. `Thread.interrupt` and the `InterruptedException` protocol as exception design (2.6.19)

`[X-REF 05]`

### Mental model

`01e` concept 2 already establishes the mechanics: interruption is a per-thread boolean, a blocking method clears it the instant it converts it into a thrown `InterruptedException`. The design lesson sitting underneath that mechanism, restated here as exception design rather than as a concurrency fact: **`InterruptedException` is not a failure report — it is a transfer of a cancellation obligation from the platform to the catching code.** Most exceptions say "something went wrong, here is what and where." `InterruptedException` says "someone asked this thread to stop; it is now your job to make that happen." Treating it like an ordinary failure — logging it and continuing — is not merely a missed log line, it is declining a responsibility the exception was handed to you specifically to discharge. That framing generalizes past this one exception: a well-designed exception type can encode "you must now do X" rather than merely "X went wrong," and a caller who forgets that distinction handles the exception correctly by every syntactic measure while still getting the design wrong.

### The self-contained mechanism, restated for design purposes

A blocking call such as `Thread.sleep`, `Object.wait`, or `BlockingQueue.take` polls the calling thread's interrupt flag while parked; if `Thread.interrupt()` has set that flag, the blocking call throws `InterruptedException` and, as part of throwing, clears the flag back to `false`. So the moment code enters a `catch (InterruptedException e)` block, the one durable record that cancellation was requested is already gone unless that block puts it back. There are exactly two structurally correct responses to that fact, chosen by the enclosing method's own signature rather than by taste: **propagate** it, by adding `throws InterruptedException` to the enclosing method and not catching it at all (or catching only to add context before rethrowing it as itself), which is correct whenever the signature is free to declare it; or **restore-and-return**, `Thread.currentThread().interrupt()` followed by `return` or `break`, which is the only option inside a `Runnable.run()` or any other signature that cannot add a checked `throws` clause. A third response — catch and continue with neither restore nor propagate — is correct in essentially no application code, and only in a narrowly documented "runs to completion regardless of interruption, reports afterward" cleanup path, which still restores the flag before returning.

**QuizStakes frame.** A `PaymentRun` worker's inner loop calls `queue.take()` waiting for the next batched withdrawal. It runs as a `Runnable` submitted to an `ExecutorService`, so `run()`'s signature cannot declare `throws InterruptedException` — restore-and-return is the only structurally available choice. `Thread.currentThread().interrupt(); return;` in the `catch` block both stops the worker immediately and leaves the flag set, so the executor's own shutdown bookkeeping (and any later code that checks `isInterrupted()` on that thread before it is returned to a pool) sees the truth. An empty `catch` here is measured, in `01e`, to leave `isInterrupted()` reading `false` immediately afterward — the shutdown request becomes invisible to everything downstream.

| Response | When | Consequence of getting it wrong |
|---|---|---|
| Propagate | Signature already declares `throws InterruptedException` | N/A if done — this is the easy case |
| Restore-and-return | `Runnable`, `Callable` whose contract forbids it, any signature that cannot add the `throws` | Skipping the restore makes the cancellation invisible to every later check of the flag |
| Absorb (never propagate or restore) | Only when the current method **is** the cancellation boundary and documents that it runs to completion regardless | Used outside that narrow case, it silently defeats graceful shutdown |

The full protocol — including how it interacts with try-with-resources cleanup during cancellation, how to write a test asserting a method restores the flag, and the memory-model guarantees `interrupt()` does and does not carry — belongs to **guide 05 (Concurrency)**; this concept is the exception-design framing that motivates the protocol, not the protocol's full treatment.

### Diagram

No diagram for this concept: the mechanism is one boolean and one clearing event, already stated as a single sentence, and `01e` already carries the one measurement (`isInterrupted()` reading `false` after a swallow) that would anchor a picture — repeating it as a figure here would only restate that file's evidence.

### The gotcha

**Insight:** the "transfer of obligation" framing is what makes the restore-and-return idiom make sense as something other than a magic incantation. `Thread.currentThread().interrupt()` is not "logging that an interrupt happened" — it is handing the obligation back onto the thread's own flag because *this* method, by virtue of its signature, cannot discharge the obligation itself (it cannot throw the checked exception onward), so the next piece of code in a position to check the flag inherits it instead.

> **Definition.** `InterruptedException` reports that a per-thread cancellation flag was observed set during a blocking call, and clears that flag as part of being thrown — so it functions as a transferred obligation to cancel, not a failure report, and the catching code must either propagate the checked exception (when the signature allows) or restore the flag via `Thread.currentThread().interrupt()` before returning (when it does not), with silent absorption legitimate only at a documented cancellation boundary.

---

## 4. Assertions versus exceptions versus validation frameworks (2.6.22)

`[X-REF 07]`

### Mental model

Three tools that all look like "a check that can stop execution," aimed at three different failures: `assert` checks a bug in *your own code's* reasoning, an exception checks a violated contract at a *boundary* your code doesn't control, and `jakarta.validation` checks a *batch* of constraints on a piece of untrusted input all at once, because the caller on the other side of that boundary needs every problem reported together rather than one at a time.

### Why each exists, side by side

| Tool | Checks | Enabled | Failure carries | Reports |
|---|---|---|---|---|
| `assert` | An internal invariant — "this can only be false if my own code has a bug" | Only with `-ea` (off by default) | An `AssertionError`, unchecked, not meant to be caught | One violation, the first one hit |
| Exception (`Objects.requireNonNull`, range checks) | A contract at a public boundary — "the caller violated the method's precondition" | Always, in every build | A specific checked or unchecked exception type, part of the API | One violation, the first one hit — fail-fast (`02b`) |
| `jakarta.validation` | A declared set of constraints on a structured input, evaluated together | Always, whenever the provider runs (`@Valid` triggers it) | `ConstraintViolationException` carrying a `Set<ConstraintViolation<T>>` | Every violation on the object, in one pass |

### When to reach for each, and when not

Reach for `assert` only for a check whose failure means *your own code* has a bug, never for validating a public method's arguments — because `assert` is compiled in but silently inert without `-ea`, it can never be relied on to run in production, so using it as an argument check means the check simply does not exist in a default deployment. Reach for a plain exception — `Objects.requireNonNull`, an explicit range check throwing `IllegalArgumentException` — at any public method boundary where a single violated precondition should stop execution immediately; `02b-designing-an-exception-hierarchy.md` owns `Objects.requireNonNull` and fail-fast as a discipline in full, and this is that discipline's normal home. Reach for `jakarta.validation` specifically when the boundary is a structured, multi-field piece of input — a request body — and the caller on the other side needs to fix more than one thing per round trip; it is the wrong tool for a single scalar precondition inside a method body, where the annotation machinery and provider lookup cost far more than a one-line `if`.

**Proving `assert` is inert by default.** Measured on JDK 21.0.7, a method that asserts a precondition rather than checking it, called with an argument that violates it:

```java
static int reserve(int available, int requested) {
    assert requested <= available
        : "invariant violated: requested " + requested + " > available " + available;
    return available - requested;
}
```

Run with no flags:

```
about to call with requested > available
returned normally, result=-40 (assertion did not fire)
```

The same class, run with `-ea`:

```
about to call with requested > available
Exception in thread "main" java.lang.AssertionError: invariant violated: requested 50 > available 10
	at EaDemo.reserve(EaDemo.java:3)
	at EaDemo.main(EaDemo.java:8)
```

Identical bytecode, identical inputs; the only difference is the `-ea` flag, and the default run silently returns a nonsensical negative balance instead of stopping. `assert` has been part of the language since **Java 1.4** (JSR 41), and it has been disabled by default in every release since — the flag is what makes it a development- and test-time tool rather than a production safety net.

### How `jakarta.validation` works, and its architectural point

`jakarta.validation` (the package renamed from `javax.validation` at the **Jakarta EE 9** transition — the older package name is the version-stale form to avoid printing) is a declarative constraint system: annotations such as `@NotNull`, `@DecimalMin`, `@Size`, and `@Valid` (for nested objects) are placed directly on fields or parameters, and a provider — Hibernate Validator is the reference implementation — evaluates them and reports failures as a `jakarta.validation.ConstraintViolationException`, whose `getConstraintViolations()` method returns a `Set<ConstraintViolation<?>>`, one entry per failed constraint, each carrying the failing property path and the violated constraint's message. **Unverified:** the exact `ConstraintViolationException` constructor signatures and whether `getConstraintViolations()` is generically typed to the validated bean's type or to a wildcard were not confirmed against a locally installed copy of the specification jar — the shape described here (a `Set` of violations, one exception for the whole failed validation pass) is the well-documented architectural behavior, but the precise API surface should be checked against the Jakarta Bean Validation 3.0 specification or the `jakarta.validation-api` jar before being reproduced verbatim in production code.

The architectural point worth having ready in an interview: **`jakarta.validation` collects every violation before reporting, where a fail-fast exception reports only the first.** Frame it on the QuizStakes onboarding payload — personal details, address, employment and income, captured together at `AO-140 WEALTH_PENDING` and earlier stages. A prospect who mistypes their postcode, leaves an income field blank, and submits a date of birth that fails the age check deserves all three problems back in one HTTP 400 body, not three separate round trips each surfacing one error at a time the way a chain of `Objects.requireNonNull` calls would. `02d-logging-and-api-boundaries.md` owns the REST error contract that consumes exactly this kind of violation set — a `ConstraintViolationException` caught by a controller advice and mapped to a 400 response body listing every violation is the natural pairing with that file's boundary-translation rules.

### Diagram

No diagram for this concept: it is entirely a three-way decision, and the table above with its "when" column is the whole decision surface — a diagram would just redraw the same three rows.

### The gotcha

**Pitfall:** using `assert` to validate a public method's arguments because it reads like a lightweight precondition check. It compiles, it looks defensive, and it passes every test run with `-ea` on (which most build tools enable for test execution) — then ships to production, where `-ea` is off, and the check silently never runs.

> **Definition.** `assert` is a disabled-by-default internal-invariant check meant only for bugs in your own code; a thrown exception is the always-on boundary check for a single violated precondition, reporting the first failure; `jakarta.validation` is a declarative, provider-evaluated constraint system for structured input that reports every violation in one `ConstraintViolationException`, which is what a form-shaped HTTP 400 body needs and a fail-fast exception cannot give it.

---

## 5. Testing exceptions: `assertThrows`, message versus type (2.6.23)

`[X-REF 16]`

### Mental model

`org.junit.jupiter.api.Assertions.assertThrows` does not just confirm an exception was thrown — it **returns the thrown exception itself**, typed to the class you asked for. That return value is the entire point of the API and the part people skip past: once you have the actual exception object in hand, you can assert on its fields — the structured data `02b-designing-an-exception-hierarchy.md` argues every domain exception should carry — instead of pattern-matching against a message string that was only ever meant for a human to read.

### Why it exists, and the stale forms it replaced

Before JUnit 5, the two ways to test for an expected exception were `@Test(expected = InsufficientFundsException.class)`, which cannot assert anything about the exception beyond its type, and the `ExpectedException` `@Rule`, which required a field-level rule declaration and configured the expectation *before* the code under test ran rather than capturing the exception afterward for inspection. Both are stale forms specific to JUnit 4; `assertThrows`, added in **JUnit 5** (the Jupiter API), replaced both by executing the code inside a lambda, catching the expected type, and handing it back as a plain return value that ordinary assertion calls can then inspect.

### When to reach for `assertThrows`, and what not to write instead

Reach for `assertThrows` for every test whose point is "this code must throw X under these conditions" — which is most negative-path tests in a codebase with a real exception hierarchy (`02b`). Do not write the legacy `try { codeUnderTest(); fail("expected exception"); } catch (InsufficientFundsException e) { assertOnFields(e); }` shape in new code — `assertThrows` is a direct, more concise replacement for exactly that pattern, and the manual form has a sharp-edged failure mode: if `codeUnderTest()` fails to throw, `fail()` itself throws `AssertionError`, which the `catch` clause below it — if written broadly as `catch (Exception e)` rather than the specific expected type — silently catches and passes, turning "the code didn't throw" into a green test.

### How it works — the assertion, verified against the documented API

**Documentation check** — JUnit 5 is not installed on this machine; the signatures below are as documented in the JUnit 5 Jupiter API javadoc for `org.junit.jupiter.api.Assertions`, not compiled here.

```java
import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;

class InsufficientFundsExceptionTest {

    @Test
    void reserveStakeThrowsWhenStakeableIsShort() {
        Wallet wallet = Wallet.of(Money.of("3.00"), Money.of("0.00"));

        InsufficientFundsException thrown = assertThrows(
            InsufficientFundsException.class,
            () -> StakeReservationService.reserveStake(wallet, Money.of("4.20")));

        assertEquals(Money.of("3.00"), thrown.available());
        assertEquals(Money.of("4.20"), thrown.required());
    }
}
```

The brittle, message-asserting alternative to avoid:

```java
// Brittle: breaks the moment anyone rewords the message for a log line.
assertEquals("insufficient funds: available 3.00, required 4.20", thrown.getMessage());
```

`assertThrows(Class<T> expectedType, Executable executable)` returns `T`, the caught exception, typed exactly to `expectedType` — which is what makes `thrown.available()` and `thrown.required()` (structured fields, `02b`'s subject) callable directly with no cast. Asserting on those fields survives a message rewording that changes nothing about the exception's actual data; asserting on `getMessage()` breaks the moment anyone touches the wording, which is a wording that `02d-logging-and-api-boundaries.md` treats as something a REST boundary or a log line is free to reformat.

### `assertThrows` versus `assertThrowsExactly`, and the rest of the table

| Form | Matches | Correct when |
|---|---|---|
| `assertThrows(InsufficientFundsException.class, executable)` | The declared type or any subclass | The usual case — a caller testing "this contract is violated" generally doesn't care whether a more specific subtype was thrown instead |
| `assertThrowsExactly(InsufficientFundsException.class, executable)` | Exactly that type, not a subclass | A test whose whole point is that this exact type is thrown and not a more specific one — for example, guarding against an accidental future subclass silently changing which exception a caller's `catch` clause matches |
| `try { codeUnderTest(); fail("expected exception"); } catch (InsufficientFundsException e) { assertOnFields(e); }` (JUnit 4 era) | Manual, and unsafe if the `catch` type is too broad | Never in new code — `assertThrows` replaced this shape entirely |

The `assertThrows` versus `assertThrowsExactly` choice is usually a non-issue — testing for the declared supertype is right almost always, because a caller of the production code under test typically catches the supertype too, and a subclass satisfying that contract is not a regression. It becomes the wrong choice only when the test's actual purpose is to pin down *which exact type* the production code commits to throwing — for instance, verifying that a refactor did not accidentally start throwing a more specific subclass that some other caller's `catch (ExactType e)` no longer matches, silently changing that caller's behavior.

Also worth asserting explicitly, both documented and checkable on the returned exception object without any special assertion method: the **cause chain**, with `assertEquals(expectedCause, thrown.getCause())` or `assertInstanceOf(LedgerImbalanceException.class, thrown.getCause())`, when the test is verifying that a lower-level exception was correctly wrapped (`01a-throwable-api-and-chaining.md` owns the chaining mechanics); and **`getSuppressed()`**, when the code under test is a `try`-with-resources block whose `close()` is expected to fail alongside the body — `assertEquals(1, thrown.getSuppressed().length)` followed by an assertion on `thrown.getSuppressed()[0]`'s type, which is the test-side counterpart of `01c` concept 2's measured suppression behavior.

### Diagram

No diagram for this concept: the difference between the four assertion shapes in the table is entirely about which exceptions are caught and which fields are then inspected, which the table already states more precisely than a picture could.

### The gotcha

**Pitfall:** asserting on `getMessage()` because it is the first thing visible in a debugger when the exception is caught, rather than reaching for the structured fields the exception was designed to carry.

> **Definition.** `assertThrows` executes a lambda, catches the first exception matching (or assignable to) the expected type, fails the test if none is thrown or a different type escapes, and returns the caught exception so the test can assert on its fields, its cause chain, or its suppressed exceptions — replacing JUnit 4's `@Test(expected = InsufficientFundsException.class)` and `ExpectedException` rule, neither of which hands back the exception object for inspection.

---

## Pitfalls

### Treating a null-resource guard as a safe way to skip a null check

**Wrong**

```java
LedgerConnection ledger = ledgerPool.checkOut(runId);   // can return null on a pool miss
try (ledger) {
    ledger.debit(accountId, amount);   // NPE here, not "handled" by the try
}
```

Measured: the body's own dereference throws `NullPointerException` — `Cannot invoke "LedgerConnection.debit()" because "<local2>" is null` — before the compiler's `ifnull` guard around the close step ever runs. The guard prevents a second exception from the close, not the first one from the body.

**Right**

```java
LedgerConnection ledger = Objects.requireNonNull(
    ledgerPool.checkOut(runId), () -> "no ledger connection available for run " + runId);
try (ledger) {
    ledger.debit(accountId, amount);
}
```

The failure now names the actual cause — no connection available for a specific run — at the point it happens, instead of surfacing as an opaque NPE inside `debit()`.

**Why people believe it:** `try`-with-resources is documented as null-safe on the close side, and it is easy to round that up to "null-safe" without the qualifier, especially since the guard genuinely does prevent a crash on the close path in the rare case a body somehow avoids touching the resource at all.

### Shipping a non-idempotent `close()` on a resource a `Cleaner` also manages

**Wrong**

```java
@Override
public void close() {
    releaseUnderlyingHandle();   // no guard — a second call releases again
}
```

Measured: called twice, this prints "releasing again" both times with no error — which looks harmless in a log until "releasing again" means double-freeing a native handle or double-decrementing a pool's checked-out count, at which point the second call corrupts real state rather than merely wasting a call.

**Right**

```java
private final AtomicBoolean closeAttempted = new AtomicBoolean(false);

@Override
public void close() {
    if (!closeAttempted.compareAndSet(false, true)) {
        return;
    }
    releaseUnderlyingHandle();
}
```

Measured: three calls produce exactly one "actually releasing" line and two "no-op" lines. Use `AtomicBoolean` specifically when a `Cleaner` thread or a pool's own reaper might call `close()` concurrently with the application's own `try`-with-resources close; a plain `boolean` is only safe under guaranteed single-threaded access.

**Why people believe it:** the success path of a resource type is tested with exactly one `close()` call, so a missing idempotence guard produces no visible symptom until a second caller — a framework, a backstop, a hand-written cleanup path — calls `close()` again, which is precisely the scenario most unit tests never construct.

### Asserting a message string instead of an exception's fields

**Wrong**

```java
InsufficientFundsException thrown = assertThrows(InsufficientFundsException.class,
    () -> StakeReservationService.reserveStake(wallet, Money.of("4.20")));
assertEquals("insufficient funds: available 3.00, required 4.20", thrown.getMessage());
```

The test is now coupled to exact wording. Someone reformats the message for a log line — adds a round ID, changes "insufficient funds" to "stake exceeds stakeable balance" — and every test asserting the old wording fails, with no actual regression in the exception's behavior.

**Right**

```java
InsufficientFundsException thrown = assertThrows(InsufficientFundsException.class,
    () -> StakeReservationService.reserveStake(wallet, Money.of("4.20")));
assertEquals(Money.of("3.00"), thrown.available());
assertEquals(Money.of("4.20"), thrown.required());
```

The assertion now depends only on the exception's actual data, which is `02b`'s "data as fields" discipline applied at the test-writing layer.

**Why people believe it:** `getMessage()` is the first thing a debugger or a failed assertion's diff shows, and asserting on it feels like verifying "the right thing happened" — until the message is edited for readability and the test breaks for a reason that has nothing to do with correctness.

---

## Cheat sheet

| Thing | Fact (Java 21 LTS) |
|---|---|
| Multiple resources, one `try` | Correct default — reverse-order close (`01c`) is the right policy for independent resources |
| Nest two `try`-with-resources instead | Only when a later action (a commit) must run after the inner resource closes *and* the outer resource's release policy differs from an automatic close |
| Null resource, variable-reference form | Compiler `ifnull` guard around the close call; body dereference throws first — measured `Cannot invoke "LedgerConnection.debit()" because "<local2>" is null` |
| Fix for a null resource | `Objects.requireNonNull` on the factory result, not a null-tolerant resource type |
| Idempotent `close()`, single-threaded | `boolean closed` flag, check-then-set |
| Idempotent `close()`, concurrent | `AtomicBoolean.compareAndSet(false, true)` |
| `Closeable.close()` idempotence | Mandatory by javadoc: "If the stream is already closed then invoking this method has no effect" |
| `AutoCloseable.close()` idempotence | Recommended, not required: "this close method is not required to be idempotent"; "implementers of this interface are strongly encouraged to make their close methods idempotent" |
| `close()` signature choices | `throws Exception` (interface default) / `throws IOException` (`Closeable`'s narrowing) / no `throws` (recommended for domain resources) |
| No-`throws` caller obligation | None — no `catch`, no `throws`, compiles as-is |
| `throws Exception` caller obligation | `catch (Exception e)` or declare `throws Exception`; measured compile error otherwise: "unreported exception Exception; must be caught or declared to be thrown" |
| `InterruptedException` design framing | Not a failure report — a transferred obligation to cancel |
| Correct responses to `InterruptedException` | Propagate (signature allows `throws`) or restore-and-return (`Runnable`/`Callable` cannot) |
| Wrong response | Catch and continue with neither — makes cancellation invisible (measured: `isInterrupted()` reads `false` after an empty catch, `01e`) |
| `assert` | Off by default; requires `-ea`; never a production check. Measured: identical code returns a wrong result silently without `-ea`, throws `AssertionError` with it |
| `assert` since | Java 1.4 (JSR 41) |
| Exception at a public boundary | Always-on; reports the first violated precondition; fail-fast (`02b`) |
| `jakarta.validation` | Declarative, provider-evaluated; `ConstraintViolationException` carries every violation in one `Set` |
| Package rename | `javax.validation` → `jakarta.validation` at the Jakarta EE 9 transition — the `javax` form is stale |
| Architectural reason to prefer it for forms | Reports every violation at once, which is what a form-shaped HTTP 400 needs |
| `assertThrows` | Returns the caught exception, typed — assert on its fields, not its message |
| `assertThrows` replaced | JUnit 4's `@Test(expected = InsufficientFundsException.class)` and the `ExpectedException` rule |
| `assertThrows` vs `assertThrowsExactly` | Supertype match (usual) vs exact-type match (pinning down the precise type deliberately) |
| Legacy `try`/`fail`/`catch` | Unsafe if the `catch` type is broad enough to also catch `fail()`'s own `AssertionError` |
| Asserting the cause chain | `assertEquals(expectedCause, thrown.getCause())` or `assertInstanceOf` on `thrown.getCause()` |
| Asserting suppressed exceptions | `thrown.getSuppressed()` — the test-side counterpart of `01c`'s measured suppression behavior |

---

## Self-test

**Q1.** Two resources, `ledger` and `file`, with `file` depending on `ledger` staying open while it writes. Should they be declared in one `try` or nested? What would force nesting instead?

<details><summary>Answer</summary>

One `try`, declared `ledger` then `file`, is correct and the default: `01c`'s reverse-close-order rule closes `file` before `ledger`, which respects the dependency automatically, and every resource whose constructor completed is closed regardless of what else throws. Nesting is only needed when some action must run *after* the inner resource's block closes and *before* the outer resource is released, and that action's execution must be conditioned on the inner block completing without throwing — for example, checking a `LedgerConnection` out of a pool, writing a `PaymentRunFileWriter` inside it, and only committing the run on the connection after the writer closed cleanly. A flat single-`try` declaration has no seam to insert that commit between the writer's close and the connection's release, because both closes happen automatically, unconditionally, and in immediate succession as part of the same implicit cleanup step.

</details>

**Q2.** A factory returns `null` instead of a live `LedgerConnection`, and that null is used as a `try`-with-resources resource. What actually happens, measured, and why is "the compiler guards against null resources" not the whole story?

<details><summary>Answer</summary>

Measured on JDK 21.0.7: the body's own dereference of the resource — `ledger.debit()` — throws `NullPointerException` with the message `Cannot invoke "LedgerConnection.debit()" because "<local2>" is null`, and that happens before the guarded close step is ever reached. The compiler does emit an `ifnull` guard around the implicit close call for any resource that is a variable reference rather than a `new` expression (established in `01c`'s effectively-final-resource measurements), so the close step itself completes without an NPE if it is ever reached — but the guard's protection is for the close operation only. In the overwhelming majority of real code, the body dereferences the resource before the close step runs at all, so the guard never gets a chance to matter, and the real failure is an NPE from the body. The fix is `Objects.requireNonNull` on the factory's result at the point the resource is obtained, converting a confusing downstream NPE into a message naming the actual missing dependency (a specific run's missing connection), not weakening the resource type to tolerate `null` internally.

</details>

**Q3.** Why declare `close()` with no `throws` clause, and what obligation does that create?

<details><summary>Answer</summary>

Because `AutoCloseable.close()` is declared `throws Exception`, and every caller's `try`-with-resources block is forced to either catch that checked type or declare it further up the call stack — measured, a resource type left at `throws Exception` and used with no `catch` fails to compile with `unreported exception Exception; must be caught or declared to be thrown`, naming "the implicit call to close() on resource variable" as the source. Narrowing `close()` to no `throws` clause at all — legal because overriding rules permit narrowing a checked-exception clause to nothing — removes that obligation from every caller, all at once, in exchange for the resource author taking on the obligation to *handle* a close failure internally rather than propagating it: log at `WARN`, increment a metric, and never silently discard it, because a swallowed close failure with no trace at all is exactly the empty-catch pattern `01e` names as illegitimate, just relocated from every caller into this one method.

</details>

**Q4.** What is the single behavioral difference `Closeable`'s javadoc states between `Closeable.close()` and `AutoCloseable.close()` regarding repeated calls?

<details><summary>Answer</summary>

`Closeable.close()` is *required* to be idempotent — its own javadoc states "If the stream is already closed then invoking this method has no effect" — while `AutoCloseable.close()` is explicitly *not* required to be, per its own javadoc: "this close method is not required to be idempotent. In other words, calling this close method more than once may have some visible side effect, unlike Closeable.close which is required to have no effect if called more than once," though implementers are "strongly encouraged to make their close methods idempotent" anyway. Since `Closeable extends AutoCloseable`, every `Closeable` inherits the stricter, mandatory contract; a type that implements `AutoCloseable` directly (as `LedgerConnection` and `PaymentRunFileWriter` do) is under no such platform-enforced obligation and has to choose idempotence deliberately, which is the reason concept 1's `boolean`/`AtomicBoolean` guard is a design decision rather than a language requirement.

</details>

**Q5.** A `PaymentRun` worker runs as a `Runnable` on an `ExecutorService` and blocks on `queue.take()`. Why is "restore and return" the only correct response to `InterruptedException` here, rather than "propagate it"?

<details><summary>Answer</summary>

Because `Runnable.run()`'s signature is fixed by the interface and cannot declare `throws InterruptedException`, so there is no checked-exception path available to hand the obligation onward — propagation, which is the preferred response whenever a signature allows it, is simply not an option here. The only structurally correct alternative is `Thread.currentThread().interrupt()` followed by `return` (or `break` out of the loop): this restores the per-thread flag that `queue.take()` cleared the instant it threw, so any code that checks `isInterrupted()` afterward — including the executor's own shutdown machinery, or a health check on the worker thread before it's returned to a pool — still sees the truth that cancellation was requested. Catching and continuing with neither response is measured, in `01e`, to leave `isInterrupted()` reading `false` immediately afterward, making the shutdown request invisible to everything downstream — which is the practical cost of treating `InterruptedException` as an ordinary logged failure instead of a transferred obligation. The concurrency-level detail of how this interacts with executor shutdown and memory-model guarantees is guide 05's territory.

</details>

**Q6.** Why is `assert` unsuitable as a public method's argument check, and what does the same code do differently with and without `-ea`?

<details><summary>Answer</summary>

Because `assert` is disabled by default — it must be explicitly enabled with the `-ea` JVM flag, and without that flag the assertion is never evaluated at all, regardless of whether its condition would have failed. Measured on JDK 21.0.7: a method asserting `requested <= available` and called with `requested` greater than `available` returns silently with a nonsensical negative result (`result=-40`) when run with no flags, and throws `AssertionError: invariant violated: requested 50 > available 10` when run with `-ea` against the identical class file and identical inputs. Since production JVMs virtually never run with `-ea` (it is a development/test convenience, not a deployment flag), using `assert` for a public method's precondition means the check simply does not exist in production — the correct tool for that boundary is a thrown exception (`Objects.requireNonNull`, an explicit range check), which runs unconditionally in every build. `assert`'s legitimate use is confined to an internal invariant whose violation would mean a bug in your own code's logic, never an external caller's input.

</details>

**Q7.** How does `jakarta.validation`'s error-reporting shape differ architecturally from a fail-fast exception, and why does that difference matter for the QuizStakes onboarding form?

<details><summary>Answer</summary>

A fail-fast exception — `Objects.requireNonNull`, an explicit range check — reports exactly one violation: the first precondition it happens to hit, after which execution stops. `jakarta.validation` evaluates every declared constraint on the object being validated and reports the complete set of failures together in one `ConstraintViolationException`, whose violations are exposed as a `Set` (one entry per failed constraint, each naming the failing property). For a single scalar precondition inside a method body, fail-fast's single-violation behavior is exactly right and cheaper. For the QuizStakes onboarding payload — personal details, address, employment and income, captured together on the path to `AO-140 WEALTH_PENDING` — a client who mistyped their postcode, left an income field blank, and failed the age check deserves all three problems back in the same HTTP 400 response, not one round trip per mistake. Fail-fast validation of that same payload would report only the first field it happened to check, forcing the client through multiple submit-and-fail cycles to discover the rest — this is the concrete reason the two tools solve different problems rather than one being a "better" version of the other.

</details>

**Q8.** `assertThrows` is called and the assertion below it checks `thrown.getMessage()` against a literal string. What is wrong with that, and what should be asserted instead?

<details><summary>Answer</summary>

The test is now coupled to exact wording that carries no contractual guarantee — a message string exists for a human reading a log or a stack trace, not as part of the exception's tested contract, so rewording it (adding a round ID, changing "insufficient funds" to something clearer) breaks the test with no actual behavioral regression. `assertThrows` returns the caught exception typed to the expected class specifically so the test can assert on its structured fields instead — `02b`'s "data as fields" discipline applied at the test layer. For `InsufficientFundsException`, the right assertions are `assertEquals(Money.of("3.00"), thrown.available())` and `assertEquals(Money.of("4.20"), thrown.required())` rather than any comparison against `getMessage()`'s literal text; those fields are the exception's actual, stable contract, and a test built on them survives any amount of message rewording.

</details>

---

## Open questions

- **Unverified:** the exact `ConstraintViolationException` constructor signatures and whether `getConstraintViolations()` is typed to the validated bean's own type parameter or to a wildcard bound. `jakarta.validation` is not installed on this machine, so this was checked against the well-documented architectural shape (a `Set` of violations, one exception per failed validation pass, package renamed from `javax.validation` at Jakarta EE 9) rather than against the `jakarta.validation-api` jar or the Jakarta Bean Validation 3.0 specification text directly. What would settle it: the `jakarta.validation-api` jar's javadoc, or the specification PDF's `ConstraintViolationException` section.
- **Unverified:** the exact `assertThrows` and `assertThrowsExactly` method signatures (parameter order, whether an optional failure-message argument exists in an overload, the exact `Executable` functional-interface name). JUnit 5 is not installed on this machine; the shapes used above match the widely documented Jupiter `Assertions` API but were not compiled against the actual `junit-jupiter-api` jar. What would settle it: the `junit-jupiter-api` javadoc for `org.junit.jupiter.api.Assertions`, or a local Maven/Gradle build with the dependency resolved.

---

**Leaves covered:** 2.6.17, 2.6.18, 2.6.19, 2.6.22, 2.6.23 (5 leaves)
**Leaves deferred:** none
**Diagrams included:** none
**Target version:** Java 21 LTS
**Lines:** 655 
