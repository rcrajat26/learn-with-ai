# 05 Multithreading and Concurrency — CompletableFuture — BASICS (§1.21, leaves 1.21.15–1.21.27)

**Target version: Java 21 LTS.** | **Part 1 of 5** | [Index](../00-index.md)
Previous: [CompletableFuture — composition](01a-basics-composition.md) · Next: [Fork/join](../fork-join/01-basics.md)

The composition file showed how to chain `AssessmentService` stages together. This file covers
what happens when you forget to hand those stages an executor, what a timeout actually does to
the work it times out, why cancelling a `CompletableFuture` is mostly theatre, and the two Java 9
methods that let you hand a future to a caller you don't trust.

---

### The common-pool trap and the parallelism < 2 fallback

**Mental model.** Every `*Async` overload without an explicit `Executor` argument —
`thenApplyAsync(fn)`, `supplyAsync(fn)`, `runAsync(task)` — does not spin up a thread just for you.
It reaches into one JVM-wide, shared bucket of worker threads: `ForkJoinPool.commonPool()`, which
also runs every parallel stream (`.parallelStream()`) in the entire process, including libraries
you didn't write. One shared elevator serves every floor of the building — your task waits behind
whatever anyone else put in there first.

**Why it exists.** `CompletableFuture` needed a default executor so the one-argument overloads
would work without ceremony, and `ForkJoinPool.commonPool()` was already sitting in the JDK since
Java 8's `Stream` API — reusing it avoided a second global pool.

**When to reach for it, and when not.** The no-executor overloads are fine for short, pure CPU-bound
transforms with no blocking — `thenApply(x -> x.total())` style work. The moment a stage makes a
network call — fetching a `Wallet`, calling `ScreeningService`, hitting the card PSP — it must run
on an executor you own, sized for that call's blocking profile, never on the common pool.
`AssessmentService` owns a dedicated `ExecutorService`, and every `*Async` stage in the
affordability chain names it explicitly.

**How it works.** The no-executor `*Async` methods delegate through `CompletableFuture.asyncPool`
to `ForkJoinPool.commonPool()`, a work-stealing pool sized once at class-init to
`availableProcessors() − 1` (or the `...common.parallelism` system property). On an 8-core box
that's 7 threads shared by every unannotated `*Async` call and every parallel stream in the JVM —
no per-caller isolation, no back-pressure. `[NUM]` `[SOURCE]` `[RESEARCH]` But on a container capped
at one vCPU, `availableProcessors() − 1 = 0`, and `0 < 2` — below the minimum parallelism the pool
needs to run tasks on pooled workers at all. The javadoc documents the fallback explicitly:

> "\[Async methods] use the `ForkJoinPool.commonPool()` (unless it does not support a parallelism
> level of at least 2, in which case, a new `Thread` is created to run each task)."

Verified against the Java 21 `CompletableFuture` javadoc; the sentence is unchanged through Java 25.
On that one-vCPU container, every no-executor `*Async` call then creates and starts a brand-new,
non-pooled `Thread` for that one task and discards it on completion — no reuse, no bound, no
queueing, so a burst of calls becomes an unbounded thread flood rather than a bounded queue with
backpressure.

**Insight:** the shared pool means one library's badly-behaved blocking task can starve a
completely unrelated feature's async chain — a mysterious latency spike with no stack trace
pointing at your code, because the thread that should run your continuation is parked inside
someone else's `Thread.sleep()`. The parallelism-0 fallback compounds this on small containers: a
common Kubernetes request/limit of one vCPU triggers it silently, with no log line.

```java
// Deliberately using the no-executor overload — do not ship this.
CompletableFuture<ScreeningVerdict> screeningFuture =
    CompletableFuture.supplyAsync(() -> screeningService.checkWatchlist(clientId));
// On an 8-core host this competes with every parallel stream in the process for
// commonPool's 7 worker threads. On a 1-vCPU container, commonPool's parallelism is
// 0, so this instead spins up a fresh, unpooled Thread per call.
```

**Pitfall:** the belief is "the no-executor overloads are basically free, they run in the
background"; the symptom is unrelated features slowing down under load with no obvious culprit on
larger hosts, and an unbounded number of live threads (visible in `jstack`) on single-vCPU
containers; the fix is to pass an explicit, bounded executor to every `*Async` call that does I/O,
reserving the no-executor form for genuinely CPU-only, non-blocking transforms.

**Interview:** "What thread pool backs `supplyAsync(fn)` if you don't pass one, and what happens on
a single-core container?" — `ForkJoinPool.commonPool()`, sized `availableProcessors() − 1`, shared
with parallel streams; when that computes to below 2 (a 1-vCPU container), the documented fallback
is a brand-new unpooled `Thread` per task instead of a pool slot at all.

> `ForkJoinPool.commonPool()` is the JVM's one shared, unconfigurable default executor for
> no-argument `*Async` calls; when it can't offer parallelism of at least 2 it silently swaps to a
> new `Thread` per task — either way, treat it as a resource you don't control.

---

### Timeouts that do not cancel

**Mental model.** `orTimeout` and `completeOnTimeout` are stopwatches sitting next to the future,
not off switches wired into the work. When the clock runs out, the stopwatch declares the race
over and writes down a result — but the runner (the thread actually executing your `Supplier` or
downstream call) keeps running until it finishes on its own.

**Why it exists.** Before Java 9, timing out a `CompletableFuture` required a manual race against a
`ScheduledExecutorService`-backed delay future. `orTimeout(long, TimeUnit)` and
`completeOnTimeout(T, long, TimeUnit)`, added in Java 9, replaced that boilerplate — but only for
the future's own completion state, not for the underlying computation.

**When to reach for it, and when not.** Reach for `orTimeout` when the caller of the future just
needs to stop waiting and move on — render a fallback screen, return a degraded response. Do not
reach for it believing it frees the connection, socket, or thread the timed-out call was using;
for that you need the call itself to be cancellable — an `HttpClient` request with its own timeout,
a JDBC statement with `setQueryTimeout`, or a client library that honours interruption.

**How it works.** `orTimeout(timeout, unit)` schedules a delayed action (via
`CompletableFuture.delayedExecutor`, internally) that calls `completeExceptionally(new
TimeoutException())` on this future if it is not already complete by the deadline.
`completeOnTimeout(value, timeout, unit)` does the same but calls `complete(value)` instead. Neither
method touches the `Supplier`, `Function`, or downstream I/O call that is still executing on
whatever thread picked it up — that thread runs to completion (or throws on its own), and its
result, when it eventually arrives, is simply discarded because the future is already complete.
`[RESEARCH]` — confirmed against the Java 21 javadoc for both methods; behaviour is unchanged
through Java 25.

The watchlist provider in the affordability chain is exactly this trap: p50 1.4 s but p99 25 s,
against a 30 s hard timeout at the provider itself. An `orTimeout(3, SECONDS)` placed defensively in
front of that call to keep the assessment UI responsive does not free up the outbound HTTP
connection or the watchlist provider's own worker slot — that call keeps running against the
provider's real 30 s ceiling regardless of what the caller decided at 3 s.

```java
CompletableFuture<ScreeningVerdict> screening =
    CompletableFuture.supplyAsync(() -> screeningService.checkWatchlist(clientId), assessmentExecutor)
        .orTimeout(3, TimeUnit.SECONDS);
// checkWatchlist() keeps running on assessmentExecutor, still holding its socket,
// until the watchlist provider itself answers or times out at 30s — orTimeout at 3s
// only stops the caller from waiting, not the call itself.
```

**Pitfall:** the belief is "orTimeout cancels the slow call for me"; the symptom is thread-pool
starvation under load — timed-out calls pile up still running, consuming `assessmentExecutor`
threads and outbound connections long after the caller moved on; the fix is to set a real timeout
on the underlying I/O client (`HttpClient.Builder.timeout()`, JDBC's query timeout) so the work
itself stops, and treat `orTimeout` purely as the caller's patience limit, not a cancellation
mechanism.

**Interview:** "Does `orTimeout` cancel the running task?" — no; it only completes the future
exceptionally at the deadline, the underlying computation keeps running to completion or failure on
its own thread, and only a timeout configured on the actual I/O call stops the work itself.

> `orTimeout`/`completeOnTimeout` bound how long the *caller* waits on the future; they do not bound
> how long the *work* runs — those are two independent clocks.

---

### `cancel(boolean)` ignores its argument

**Mental model.** `Future.cancel(boolean mayInterruptIfRunning)` on a plain `FutureTask` is a real
lever: pass `true` and, if the task is running, its thread gets `Thread.interrupt()`ed. On a
`CompletableFuture` the same method exists, takes the same boolean, and does nothing with it — it
is a lever connected to nothing.

**Why it exists.** `CompletableFuture` implements `Future` for interoperability with code that
expects one, but its execution model differs: it doesn't own the thread running its async stage the
way a `FutureTask` owns its worker — that stage may be one link in a chain running on several
different executors over its lifetime. There is no single thread to interrupt.

**When to reach for it, and when not.** `cancel(...)` is useful purely as a way to make a
`CompletableFuture` complete exceptionally from the outside — for example, to make a
`get()`-blocked caller wake up with a `CancellationException` when a request is abandoned. Never
reach for it expecting the in-flight `Supplier` or downstream call to actually stop; for real
cancellation of the work itself you need cooperative interruption checks inside the task, or a
cancellable client call, wired independently.

**How it works.** `[PROVE]` — walking the contract directly: `cancel(boolean)` on a
`CompletableFuture`, if not already complete, calls the equivalent of
`completeExceptionally(new CancellationException())` and returns `isCancelled()`. The javadoc states
the parameter's fate explicitly:

> "Parameters: `mayInterruptIfRunning` — this value has no effect in this implementation because
> interrupts are not used to control processing."

`[SOURCE]` — quoted verbatim from the Java 21 `CompletableFuture#cancel` javadoc, unchanged through
Java 25, so not version-scoped. Proof it's a design choice, not an omission: pass `true` or `false`
and the outcome is identical — the future transitions to completed-exceptionally with
`CancellationException`, chained dependents also complete exceptionally (wrapped in
`CompletionException`), and the thread actually running the work, if any, is never touched and
never observes an `InterruptedException`.

```java
CompletableFuture<Wallet> walletFuture =
    CompletableFuture.supplyAsync(() -> walletClient.fetchBlocking(accountId), assessmentExecutor);

boolean cancelledTrue = walletFuture.cancel(true);   // identical outcome to cancel(false)
// fetchBlocking(accountId) keeps running to completion; its result is discarded once
// walletFuture is already CancellationException-complete.
```

**Pitfall:** the belief is "`cancel(true)` interrupts the running task, same as `FutureTask`"; the
symptom is a blocking call (a socket read, a `Thread.sleep`, a lock wait) that never gets
interrupted and keeps a pool thread pinned even after the caller has "cancelled" the future; the
fix is to treat `CompletableFuture.cancel` purely as "mark this future done, exceptionally" and
build actual interruptibility into the task body if you need it, e.g. checking
`Thread.currentThread().isInterrupted()` in a loop, or using a cancellable HTTP client call.

**Interview:** "Does `cancel(true)` interrupt the thread running a `CompletableFuture`'s task?" —
no, never; the boolean argument is accepted for `Future` interface compatibility only and has no
effect, unlike `FutureTask` where it genuinely interrupts.

> `CompletableFuture.cancel(boolean)` always behaves like `cancel(false)` — it only completes the
> future with `CancellationException`; it never interrupts the thread doing the work.

---

### `minimalCompletionStage()` and `copy()`

**Mental model.** Both methods answer the same question — "how do I hand this future to a caller
who must not be able to finish it for me?" — with two different levels of restriction.
`minimalCompletionStage()` hands over a stripped-down view that supports only chaining, nothing
else. `copy()` hands over a full, independent `CompletableFuture` that mirrors this one's outcome
but cannot be completed on its own and cannot leak completion back upstream.

**Why it exists.** A raw `CompletableFuture<T>` is both a producer API (`complete`,
`completeExceptionally`, `cancel`) and a consumer API (`thenApply`, `get`, `join`). Handing the same
object to a downstream caller also hands them the ability to forge the result — call
`complete(fakeValue)` before the real work finishes. Java 9 added these two methods precisely to
let a producer keep the producer half to itself.

**When to reach for it, and when not.** `minimalCompletionStage()` when the caller only needs to
chain and should never call `get()`/`join()`/`cancel()` directly. `copy()` when the caller needs a
genuine `CompletableFuture<T>` — perhaps to satisfy an API demanding that concrete type — but must
not be able to complete the original. Skip both when the future never leaves the creating method.

**How it works.** `minimalCompletionStage()` returns a `CompletionStage<T>` (technically a minimal
`CompletableFuture` internally, but exposed only through the `CompletionStage` interface) that
completes normally or exceptionally in lockstep with the original, but whose `toCompletableFuture()`
result throws `UnsupportedOperationException` on `get`, `getNow`, `complete`, and `cancel` — the
javadoc calls this a `CompletionStage` "with no publicly accessible completion methods". `copy()`
returns a genuine, independent `CompletableFuture<T>` that also completes in lockstep, but calling
`complete`/`cancel` on the copy has no effect on the original — only the reverse direction (original
→ copy) propagates. `[RESEARCH]` — verified against the Java 21 javadoc; both methods are unchanged
through Java 25.

```java
public CompletionStage<WealthVerdict> assessAffordability(ClientId clientId) {
    CompletableFuture<WealthVerdict> internal =
        CompletableFuture.supplyAsync(() -> assessmentService.scoreWealth(clientId), assessmentExecutor);
    return internal.minimalCompletionStage(); // chain-only view, no complete()/cancel() reachable
}

public CompletableFuture<WealthVerdict> assessAffordabilityDefensiveCopy(ClientId clientId) {
    CompletableFuture<WealthVerdict> internal =
        CompletableFuture.supplyAsync(() -> assessmentService.scoreWealth(clientId), assessmentExecutor);
    return internal.copy(); // real CompletableFuture, but inert — only `internal` decides the outcome
}
```

**Pitfall:** the belief is "returning `CompletableFuture<T>` from a public API is harmless because
callers will just read the result"; the symptom is a caller calling `.complete(wrongVerdict)` on
your future from three layers away, silently corrupting the affordability decision before the real
`scoreWealth` call finishes; the fix is to return `CompletionStage<T>` (or `copy()` when the
concrete type is unavoidable) from any API boundary you don't fully trust.

**Interview:** "How do you give a caller a future they can observe but not complete?" —
`minimalCompletionStage()` for chain-only access, or `copy()` when they need a real
`CompletableFuture` object but must not be able to finish the original.

> `minimalCompletionStage()` strips completion methods from the view entirely; `copy()` keeps the
> full `CompletableFuture` API but detaches it so completing the copy never completes the original.

---

## Supporting facts

**Manual completion — `complete`, `completeExceptionally`, `completeAsync`×2 (Java 9),
`obtrudeValue`, `obtrudeException`.** `complete(value)`/`completeExceptionally(ex)` finish a future
exactly once from outside any chained stage — the mechanism `AssessmentService` uses when a webhook
callback, not a polled response, delivers the answer. `completeAsync(supplier[, executor])` (Java 9)
does the same but runs the supplier asynchronously instead of completing with a value already held.
`obtrudeValue`/`obtrudeException` overwrite an *already-completed* future's result, breaking the
"complete exactly once" contract. **Gotcha:** obtruding does not un-run any dependent stage that
already fired side effects off the old result — it only changes what `get()` returns from then on,
so these exist solely as a last-resort recovery hatch, never for normal flow control. `[RESEARCH]`
— unchanged since Java 9 through the Java 25 javadocs.

> `obtrudeValue`/`obtrudeException` retroactively rewrite a future's already-delivered result; they
> exist for emergency correction, not everyday completion.

**Query and inspection — `isDone`, `isCancelled`, `isCompletedExceptionally`, `getNow(fallback)`,
`getNumberOfDependents`, plus the inherited Java 19 `state`/`resultNow`/`exceptionNow`.** `isDone()`
covers normal, exceptional, and cancelled completion alike; `isCompletedExceptionally()` is what
distinguishes success from failure. `getNow(fallback)` returns the value if already complete, or
`fallback` without blocking. `getNumberOfDependents()` is a debugging snapshot, not something to
branch on — it races with concurrent chaining. **Gotcha:** `resultNow()` (Java 19) throws
`IllegalStateException` if called before completion — it is `getNow`'s "I already know this is
done" cousin, not a safe non-blocking peek.

> `getNow(fallback)` never blocks and never throws; `resultNow()` never blocks but throws if the
> future isn't already done — pick based on whether "not yet done" is an error in your context.

**`CompletableFuture.AsynchronousCompletionTask`.** A zero-method marker interface implemented
internally by every task `CompletableFuture` submits for an `*Async` call. **Gotcha:** it exists so
profilers and monitoring tools can identify "this task on the pool belongs to a `CompletableFuture`
async stage" without parsing stack traces — application code never implements or checks it.
`[SOURCE]` `[RESEARCH]` — present unchanged from Java 8 through Java 25, predating the Java 9
additions above.

> `AsynchronousCompletionTask` is a tagging interface for tooling, not an application-facing API.

**`CompletionStage` in signatures, `CompletableFuture` only when the caller must complete it.**
Accept and return `CompletionStage<T>` by default — it exposes chaining (`thenApply`,
`thenCompose`, `exceptionally`) without `complete`, `cancel`, or blocking `get`/`join`. Return
`CompletableFuture<T>` only when the caller genuinely needs those powers — a webhook-driven future,
or interop with an API that demands the concrete class.

> `CompletionStage` is the narrow, safe surface to publish; `CompletableFuture` is the wide,
> dangerous one — default to the narrow one at every API boundary.

**Where `CompletableFuture` stops being the right tool.** `[X-REF 04]` Virtual threads (Java 21,
JEP 444) remove the original reason chains existed: avoiding one blocked platform thread per
pending call. A straight-line, blocking `assessmentService.scoreWealth(clientId)` call on its own
virtual thread costs nothing extra to park, and structured concurrency (JEP 505 → 525 → 533, still
preview through Java 21–25) gives that code the same fan-out/fan-in shape as `thenCombine` without
the callback-chain readability cost or the executor-plumbing burden this file just walked through.
The honest 2026 answer: prefer blocking code plus structured concurrency for new request-scoped
fan-out; reach for `CompletableFuture` chains when threading through an existing reactive/callback
library, or where the JDK API itself only exposes `CompletableFuture` (`HttpClient.sendAsync`). See
guide 04 for the full structured-concurrency walkthrough.

---

## Subclassing to inherit an executor `[BUILD]`

Overriding `defaultExecutor()` and `newIncompleteFuture()` makes an entire chain — every `*Async`
call with no explicit executor, and every stage created by `thenApply`/`thenCompose` internally —
inherit one executor by construction, closing the common-pool trap at the type level instead of by
discipline.

```java
public final class AssessmentFuture<T> extends CompletableFuture<T> {

    private final Executor assessmentExecutor;

    public AssessmentFuture(Executor assessmentExecutor) {
        this.assessmentExecutor = assessmentExecutor;
    }

    @Override
    public Executor defaultExecutor() {
        return assessmentExecutor;
    }

    @Override
    public <U> CompletableFuture<U> newIncompleteFuture() {
        return new AssessmentFuture<>(assessmentExecutor);
    }

    public static <T> AssessmentFuture<T> supplyOn(Supplier<T> supplier, Executor assessmentExecutor) {
        AssessmentFuture<T> future = new AssessmentFuture<>(assessmentExecutor);
        assessmentExecutor.execute(() -> {
            try {
                future.complete(supplier.get());
            } catch (Throwable t) {
                future.completeExceptionally(t);
            }
        });
        return future;
    }
}
```

`defaultExecutor()` is what every no-argument `*Async` overload calls internally instead of
reaching for `ForkJoinPool.commonPool()`. `newIncompleteFuture()` is the factory every combinator
uses to create the *next* stage — overriding it means chaining further `*Async` calls off an
`AssessmentFuture` uses `assessmentExecutor` at every link with no executor argument repeated.
`[RESEARCH]` — both hooks are Java 9 additions, unchanged through Java 25.

---

## The worked composition — affordability assessment `[BUILD]`

Six stages, one shared `assessmentExecutor` named explicitly at every stage, and an `orTimeout`
placed against the watchlist provider's own 30 s ceiling (p50 1.4 s, p99 25 s) rather than against
some arbitrary shorter number, since the provider itself is already the slowest link.

```java
public CompletionStage<AffordabilityResult> assess(ClientId clientId, AccountId accountId,
                                                     ExecutorService assessmentExecutor) {
    CompletableFuture<Client> clientFuture =
        CompletableFuture.supplyAsync(() -> assessmentService.lookupClient(clientId), assessmentExecutor);
    CompletableFuture<Wallet> walletFuture = clientFuture.thenComposeAsync(
        client -> CompletableFuture.supplyAsync(() -> assessmentService.fetchWallet(accountId), assessmentExecutor),
        assessmentExecutor);
    CompletableFuture<LimitSet> limitsFuture = walletFuture.thenCombineAsync(
        clientFuture,
        (wallet, client) -> assessmentService.combineLimits(wallet, client),
        assessmentExecutor);
    CompletableFuture<ScreeningVerdict> screeningFuture =
        CompletableFuture.supplyAsync(() -> assessmentService.checkWatchlist(clientId), assessmentExecutor)
            .orTimeout(30, TimeUnit.SECONDS); // matches the watchlist provider's own 30s ceiling
    CompletableFuture<AffordabilityResult> resultFuture = limitsFuture.thenCombineAsync(
        screeningFuture,
        (limits, verdict) -> assessmentService.render(limits, verdict),
        assessmentExecutor);
    return resultFuture
        .exceptionallyAsync(ex -> assessmentService.renderConservativeFallback(clientId, ex), assessmentExecutor)
        .minimalCompletionStage();
}
```

`clientFuture` looks up the `Client`; `walletFuture` composes onto it to fetch the `Wallet`;
`limitsFuture` combines wallet and client into a `LimitSet`; `screeningFuture` runs independently
with `orTimeout(30, SECONDS)` against the watchlist provider's documented ceiling — tight enough to
bound worst case, loose enough that its own p99 of 25 s does not spuriously trip it; `resultFuture`
combines limits and verdict into the render; `exceptionallyAsync` recovers any stage's failure —
including a timed-out screening call — into a conservative fallback; and `minimalCompletionStage()`
gives the caller a chain-only view, per the API-boundary rule above.

**Interview:** "Why put `orTimeout` at exactly 30 s here and not something smaller?" — 30 s is the
watchlist provider's own documented timeout; setting a caller-side timeout shorter than that just
manufactures spurious failures against a dependency whose p99 (25 s) already approaches that
ceiling, while setting it longer defeats the purpose of having a caller-side bound at all.

---

## Pitfalls

### Assuming `supplyAsync(fn)` runs on a private thread just for this call

**Wrong**
```java
CompletableFuture<Wallet> f = CompletableFuture.supplyAsync(() -> walletClient.fetch(accountId));
// Looks isolated. It's actually queued onto ForkJoinPool.commonPool() —
// the same pool every parallel stream in this JVM is also using.
```

**Right**
```java
CompletableFuture<Wallet> f =
    CompletableFuture.supplyAsync(() -> walletClient.fetch(accountId), assessmentExecutor);
// Runs on a pool sized and owned for this workload, isolated from unrelated code.
```

**Why people believe it:** the method name is `supplyAsync`, singular and self-contained-sounding,
and the no-executor overload compiles and works fine in a quick test with no contention to reveal
the shared pool.

### Assuming `cancel(true)` stops the in-flight call

**Wrong**
```java
CompletableFuture<ScreeningVerdict> f =
    CompletableFuture.supplyAsync(() -> screeningService.checkWatchlist(clientId), assessmentExecutor);
f.cancel(true); // "true means interrupt it, right?"
// checkWatchlist(clientId) keeps running to completion on assessmentExecutor regardless.
```

**Right**
```java
CompletableFuture<ScreeningVerdict> f =
    CompletableFuture.supplyAsync(() -> screeningService.checkWatchlistInterruptible(clientId), assessmentExecutor);
f.cancel(true); // still ignored by CompletableFuture...
// ...so checkWatchlistInterruptible() must poll Thread.currentThread().isInterrupted()
// or use a client with its own cancellable/timeout-bound call to actually stop.
```

**Why people believe it:** `cancel(boolean mayInterruptIfRunning)` is copied verbatim from
`Future`, where `FutureTask` genuinely honours the flag — the method signature gives no hint that
`CompletableFuture`'s implementation of it is inert.

---

## Cheat sheet

| Thing | One-line fact |
|---|---|
| No-executor `*Async` | Runs on `ForkJoinPool.commonPool()`, shared JVM-wide with parallel streams |
| commonPool parallelism < 2 | Falls back to a brand-new `Thread` per task, no pooling |
| `orTimeout(t, u)` | Fails the future with `TimeoutException`; underlying work keeps running |
| `completeOnTimeout(v, t, u)` | Completes the future with `v`; underlying work keeps running |
| `cancel(boolean)` | Argument ignored always; only sets `CancellationException`, never interrupts |
| `minimalCompletionStage()` | `CompletionStage` view with no completion methods reachable |
| `copy()` | Independent `CompletableFuture`; completing it never completes the original |
| `obtrudeValue`/`obtrudeException` | Overwrites an already-completed result — recovery only |
| `getNow(fallback)` | Non-blocking peek; returns `fallback` if not yet done |
| `resultNow()` | Throws `IllegalStateException` if not yet done — not a safe peek |
| `AsynchronousCompletionTask` | Marker interface for tooling; no application use |
| `CompletionStage` vs `CompletableFuture` | Accept/return the stage; return the future only if the caller must complete it |
| Virtual threads + structured concurrency | The 2026 default for new request-scoped fan-out; keep chains for callback-based APIs |

---

## Self-test

**Q1.** Why does a `supplyAsync(fn)` call with no executor argument risk starving unrelated code
elsewhere in the same JVM?

<details><summary>Answer</summary>

Because it schedules onto `ForkJoinPool.commonPool()`, a single JVM-wide pool also used by every
`parallelStream()` call in the process. A blocking task there occupies one of a small, fixed number
of worker threads, leaving fewer for every other consumer of the same pool.

</details>

**Q2.** On a container with exactly one vCPU, what happens when code calls
`CompletableFuture.supplyAsync(fn)` with no executor, and why?

<details><summary>Answer</summary>

`availableProcessors() − 1` computes to `0`, below the documented minimum parallelism of 2 that
`commonPool()` needs to use pooled workers at all. The documented fallback creates a brand-new,
unpooled `Thread` per call instead — under load, an unbounded thread flood, not a bounded queue.

</details>

**Q3.** Does `orTimeout(3, TimeUnit.SECONDS)` stop the supplier that's still running past the
3-second mark?

<details><summary>Answer</summary>

No. It only completes the `CompletableFuture` exceptionally with a `TimeoutException` at the
deadline. The supplier or downstream call that's still executing keeps running on its own thread
until it finishes or fails on its own; its eventual result is simply discarded because the future
is already complete.

</details>

**Q4.** What is the practical difference between calling `cancel(true)` and `cancel(false)` on a
`CompletableFuture`?

<details><summary>Answer</summary>

None. The javadoc states `mayInterruptIfRunning` "has no effect in this implementation because
interrupts are not used to control processing." Both calls complete the future with a
`CancellationException` if not already done, and never interrupt the running task.

</details>

**Q5.** When would you choose `minimalCompletionStage()` over `copy()` when handing a future to a
caller?

<details><summary>Answer</summary>

Choose `minimalCompletionStage()` when the caller only needs to chain further work and should never
see `get()`, `join()`, `complete()`, or `cancel()` at all. Choose `copy()` when the caller
specifically needs a concrete `CompletableFuture<T>` object — to satisfy an API demanding that
type — while still being unable to complete or cancel the original.

</details>

**Q6.** Why is `obtrudeValue` dangerous to use as a normal completion mechanism?

<details><summary>Answer</summary>

It overwrites the result of a future that has *already completed*, breaking the "complete exactly
once" guarantee. Any dependent stage that already fired side effects off the old result stays
fired; obtruding only changes what future `get()`/`join()` calls see, creating an inconsistency
between what happened and what the future now reports. It exists as an emergency hatch only.

</details>

**Q7.** In the affordability chain, why is `orTimeout(30, TimeUnit.SECONDS)` placed against the
watchlist call specifically, rather than a smaller number like 3 seconds?

<details><summary>Answer</summary>

30 s matches the watchlist provider's own documented timeout. Its p99 is already 25 s, so a shorter
caller-side timeout would routinely trip on legitimate slow calls; a longer one defeats the point
of bounding the wait at all. The bound should track the dependency's real worst case.

</details>

**Q8.** What does overriding `newIncompleteFuture()` accomplish that overriding only
`defaultExecutor()` does not?

<details><summary>Answer</summary>

`defaultExecutor()` only governs which executor no-argument `*Async` calls on *this* future use.
`newIncompleteFuture()` is the factory every combinator uses to create the *next* stage in a chain.
Overriding both means every stage produced by chaining off the original also carries the custom
executor, without overriding every combinator individually.

</details>

**Q9.** Is `getNumberOfDependents()` safe to use for making a scheduling or retry decision?

<details><summary>Answer</summary>

Not reliably — it's a point-in-time snapshot that races with concurrent calls chaining new
dependents onto the same future. It's useful for debugging and monitoring ("roughly how many stages
are waiting on this"), not as a value to branch production logic on.

</details>

**Q10.** In 2026, when does a Java team reach for `CompletableFuture` chains instead of blocking
code plus structured concurrency on virtual threads?

<details><summary>Answer</summary>

When threading through an existing reactive or callback-based library that already speaks
`CompletableFuture`, or when a JDK API being called only exposes an async, `CompletableFuture`-based
entry point (such as `HttpClient.sendAsync`). For new request-scoped fan-out/fan-in logic with no
such constraint, straight-line blocking code on virtual threads with structured concurrency is
simpler to read and debug.

</details>

---

**Leaves covered:** 1.21.15–1.21.27 (13 leaves)
**Leaves deferred:** none
**Diagrams included:** none
**Target version:** Java 21 LTS
**Lines:** 600
