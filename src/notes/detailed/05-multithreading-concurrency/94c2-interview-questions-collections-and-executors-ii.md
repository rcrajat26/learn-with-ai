# 05 Multithreading and Concurrency — Interview questions: collections and executors II — INTERVIEW (§5.1, questions 5.1.77–5.1.91)

**Target version: Java 21 LTS.** | **Part 5 of 5** | [Index](00-index.md)
Previous: [Interview questions: collections and executors](94c-interview-questions-collections-and-executors.md) · Next: [Interview questions: liveness and Loom](94d-interview-questions-liveness-and-loom.md)

---

### 5.1.77 Why does an exception in a task submitted with `submit` vanish?

`submit(Runnable)` and `submit(Callable)` don't propagate the exception to anywhere visible unless you go looking for it — they capture it inside the returned `Future` and only rethrow it (wrapped in `ExecutionException`) when you call `future.get()`.
If a `WithdrawalTransaction` processing task submitted via `pool.submit(task)` throws `LedgerImbalanceException` and nobody ever calls `.get()` on the returned `Future`, the exception is stored, the worker thread survives (`ThreadPoolExecutor`'s worker loop catches `Throwable` around task execution specifically so one failing task doesn't kill the thread), and the failure is never logged, never surfaces anywhere — it's as if the task silently succeeded.
This is different from `execute(Runnable)`, which has no `Future` to swallow the exception into — an uncaught exception there propagates to the worker's `UncaughtExceptionHandler`, which at least gets logged by default.

**Follow-up:**

"How do you make sure you actually see the failure?" — either always call `future.get()` (even just to check, discarding the value) and handle `ExecutionException`, or wrap the task body in its own try/catch that logs before rethrowing, or supply a custom `ThreadPoolExecutor` that overrides `afterExecute(Runnable, Throwable)` to inspect `Future`-wrapped exceptions even when nobody calls `get()`.

The same swallow-by-default shape recurs with `ScheduledExecutorService` (5.1.78) and with `CompletableFuture` chains (5.1.88) — across all three, the JDK's design choice is that a future-shaped API stores failure rather than propagating it, on the theory that a caller who never checks the future didn't want to be notified synchronously, which is a defensible design for a library but a dangerous default for application code that forgets to opt in.

**Pitfall:**

Submitting fire-and-forget tasks via `submit()` for their exception-swallowing side effect, then being surprised weeks later that a whole class of `WithdrawalTransaction` failures never appeared in any log — `submit()` was never "quieter" than `execute()`, it just requires you to opt in to seeing the failure.

**Insight:**

The fix pattern generalizes across the whole family: whenever an API hands back a value-holding wrapper instead of running your callback immediately, assume failure is stored inside that wrapper until proven otherwise, and make unwrapping it a mandatory step rather than an optional one.

**Interview:**

Interviewers use this to probe whether a candidate treats `Future` as a value they must actively unwrap, versus assuming any submitted task's failure automatically surfaces somewhere — naming `afterExecute` as an alternative defense is a strong signal of having actually operated one of these pools in production.

### 5.1.78 Why does an exception in a scheduled task stop all future runs?

`ScheduledThreadPoolExecutor`'s `scheduleAtFixedRate`/`scheduleWithFixedDelay` work by having the *same* internal task re-arm itself for its next run after each execution completes — but if the task body throws an uncaught exception, the executor's scheduling loop treats that as the task being done, permanently, and it is silently **not** rescheduled.
There's no retry, no backoff, no notification — the periodic job that was supposed to sweep expired `Bonus` records every hour just stops running forever after the first uncaught exception, and because it's a scheduled task (not a one-off `submit`), nobody is sitting there calling `.get()` to notice.
This is arguably the single most dangerous silent-failure mode among the executor family, because "the periodic job used to run and now doesn't" produces no error at the moment of failure — only a slow-building symptom days later (expired bonuses that were never clawed back).

**Follow-up:**

"How do you defend against it?" — wrap the entire task body in a try/catch that logs and swallows every `Throwable` before returning, so the scheduling loop always sees a normal return and keeps rearming — the task's own code must guarantee it never lets an exception escape.

Because the internal re-arming logic treats an uncaught exception identically to "the task decided it's finished," there is no distinction in the executor's own behavior between a task that legitimately completed all its scheduled work and one that crashed on its very first run — both simply stop being resubmitted, which is exactly why silent failure here is so easy to miss until someone notices the expected side effect stopped happening.

**Pitfall:**

Assuming a periodic task that "usually just works" will keep retrying itself if a transient failure happens — one bad run permanently ends the entire schedule; there is no exponential-backoff-and-retry behavior built into the class.

**Insight:**

Spring's `@Scheduled` methods inherit this exact same failure mode when backed by a `ThreadPoolTaskScheduler` — an uncaught exception in a `@Scheduled` method silently ends that method's future invocations too, which is why production Spring services almost always wrap scheduled method bodies in their own try/catch regardless of the framework.

**Interview:**

This question rewards candidates who volunteer the fix (wrap the task body defensively) before being asked, since the danger of silent schedule death is the kind of production lesson that's hard to guess without having been burned by it.

### 5.1.79 `scheduleAtFixedRate` versus `scheduleWithFixedDelay`

`scheduleAtFixedRate(task, initialDelay, period, unit)` schedules successive runs at `initialDelay`, `initialDelay + period`, `initialDelay + 2×period`, … measured from the **start** of the first run — if a single execution overruns the period, the next run fires immediately after the overrunning one finishes (no gap), and the executor does not run runs concurrently or try to "catch up" with a backlog of skipped ticks.
`scheduleWithFixedDelay(task, initialDelay, delay, unit)` instead measures the delay from the **end** of one execution to the start of the next — so the gap between successive runs is always at least `delay`, regardless of how long any individual run took.

Concretely: a `Bonus` expiry sweep scheduled every 60 minutes with `scheduleAtFixedRate` that occasionally takes 65 minutes to run (a slow day scanning a larger backlog) will fire its next run **immediately**, with zero rest between them, because the fixed-rate schedule is trying to hit 60-minute-apart start times regardless of overrun.
The same sweep scheduled with `scheduleWithFixedDelay` always gets a full 60-minute rest after each run finishes, no matter how long the run took — the total cycle time stretches to accommodate slow runs instead of compressing the gap.

**Follow-up:**

"Which do you pick for a job whose runtime is unpredictable and could be long?" — `scheduleWithFixedDelay`, because it guarantees breathing room between runs and can't pile up back-to-back executions the way fixed-rate can after an overrun.

A useful way to keep the two straight under pressure: fixed-rate cares about wall-clock start times lining up on a schedule, so it can compress the gap to zero after an overrun; fixed-delay cares about a minimum rest between runs, so it can never compress below that floor no matter how long any single run took.

**Pitfall:**

Picking `scheduleAtFixedRate` for a task with variable duration expecting it to "skip" a run if the previous one overran into the next scheduled slot — it never skips; it just runs back-to-back with no delay, which can starve the pool if the task is slow often enough.

**Interview:**

A quick, confident answer naming which one measures from start versus end of the previous run is usually enough; interviewers dig deeper only if the first answer is vague about which timing anchor each variant uses.

### 5.1.80 What is a bounded queue for, and what does an unbounded one convert overload into?

A bounded queue is the mechanism that gives a thread pool **backpressure** — it caps how much work can sit waiting before the pool is forced to either grow (toward `maximumPoolSize`) or reject, both of which are visible, actionable signals to the rest of the system that it's overloaded.
An unbounded queue removes that signal entirely: instead of the system saying "I'm full, back off" at some defined point, it silently accepts unlimited work and converts a *throughput* problem (not enough workers to keep up) into a *memory* problem (an ever-growing queue of pending `WithdrawalTransaction` objects sitting in heap).
This is the same failure shape as 5.1.72's `newFixedThreadPool` critique, generalized: overload that would have been a clean, immediate rejection under a bounded queue instead becomes a slow-building latency and memory problem under an unbounded one — work submitted now might not run for hours, and by the time it does the request that triggered it may have already timed out client-side, so the work executes anyway, wastefully, against a caller who's no longer listening.

**Follow-up:**

"Is a bounded queue ever wrong?" — yes, for strictly ordered, must-not-drop work with no acceptable rejection path (e.g., ledger writes that must all eventually apply) — there, an unbounded queue is a deliberate choice paired with independent monitoring of queue depth as the overload signal instead of relying on rejection.

**Pitfall:**

Treating "bounded queue" as always synonymous with "good" and "unbounded" as always synonymous with "bad" — a bounded queue that's sized too small for legitimate burst traffic just moves the pain earlier, causing spurious rejections or `CallerRunsPolicy` throttling during load spikes the system could have absorbed with a slightly larger, still-bounded buffer.

**Interview:**

Expect this framed as asking why a pool would ever want to reject work instead of just queueing it — the expected answer reframes rejection as a deliberate, visible signal rather than a failure to be avoided at all costs.

### 5.1.81 What is `SynchronousQueue` and where is it used?

`SynchronousQueue` is a `BlockingQueue` with **zero capacity** — it holds no elements at all; every `put` must be matched by a concurrent `take` (or vice versa) or the caller blocks until a match arrives.
It's not really a queue for storing things, it's a rendezvous/handoff point between exactly one producer and one consumer at a time.
Its main production use is inside `Executors.newCachedThreadPool()` (5.1.73) — precisely because it has no capacity, a task offered to it either finds an idle worker waiting to `take` it immediately, or the offer fails instantly, which is what forces the pool to spin up a new worker on every burst rather than queueing.
It's also useful directly as a synchronous handoff primitive — e.g., handing a freshly-verified `WithdrawalTransaction` from a validation thread straight to a dedicated execution thread with a guarantee that no transaction ever sits buffered between the two.

**Follow-up:**

"Is `SynchronousQueue` fair?" — it has a fair mode (constructor argument `true`) that serves waiting threads FIFO via an internal wait queue; the default unfair mode uses a Treiber-stack-like LIFO handoff for higher throughput under contention, at the cost of possible starvation of a long-waiting thread.

**Pitfall:**

Assuming `SynchronousQueue` can be used as a general-purpose bounded queue with "capacity 0" for a `ThreadPoolExecutor` with `core > 0` — because every offer needs an immediately-waiting taker, a pool that isn't already saturated with idle workers will reject far more aggressively than an actual small bounded queue would, which is rarely the intended behavior outside the specific `newCachedThreadPool` use case.

**Interview:**

This is often a quick factual check nested inside a larger `newCachedThreadPool` discussion (5.1.73) rather than asked standalone — the expected answer connects the zero-capacity property directly to why the cached pool spins up threads so eagerly.

### 5.1.82 How does the producer–consumer pattern shut down cleanly?

The two ingredients are a **poison pill** and a bounded blocking queue that both sides agree on.
Producers keep calling `queue.put(withdrawalTransaction)` (blocking if the queue is full — that's the backpressure); when a producer is done for good, it places a sentinel value (a poison pill — a specific well-known object, or a distinguished subclass, that consumers recognize as "no more work is coming") onto the queue instead of a real task.
Consumers loop on `queue.take()`, and on seeing the poison pill, they stop pulling and, if there are multiple consumers, **re-enqueue the same pill** before terminating so the next consumer also sees it and shuts down in turn — one pill per producer-shutdown event, forwarded until every consumer has seen it and exited.

```java
record PoisonPill() implements WithdrawalTransaction {}

void consumerLoop(BlockingQueue<WithdrawalTransaction> queue) throws InterruptedException {
    while (true) {
        WithdrawalTransaction next = queue.take();
        if (next instanceof PoisonPill) {
            queue.put(next); // forward the pill so sibling consumers also see it
            return;
        }
        process(next);
    }
}
```

This avoids the two broken alternatives: an `isRunning` flag checked in the consumer loop can leave a consumer permanently blocked inside `queue.take()` if the queue is empty when the flag flips (nothing wakes it up), and calling `Thread.interrupt()` on every consumer works but requires every consumer to correctly propagate `InterruptedException` out of whatever it's doing, which is easy to get wrong if the task body swallows the interrupt.

**Follow-up:**

"What if you're using an `ExecutorService` instead of raw consumer threads?" — then shutdown is exactly the two-phase pattern from 5.1.76 (`shutdown()` then bounded `awaitTermination` then `shutdownNow()`), and the poison-pill pattern is specifically for hand-rolled producer/consumer threads that don't go through an executor at all.

**Pitfall:**

Forgetting that a single poison pill only guarantees one consumer sees it directly — without the forward-and-requeue step, every consumer after the first to consume the pill blocks forever in `queue.take()` with no producer left to wake it and no pill left to see.

**Interview:**

This question tests whether a candidate can design a clean shutdown protocol from first principles rather than reaching for `Thread.stop()` or a raw boolean flag — the poison-pill pattern and its multi-consumer forwarding detail is the signal of prior hands-on experience.

### 5.1.83 `thenApply` versus `thenCompose` versus `thenCombine`

| Method | Shape | Use when |
|---|---|---|
| `thenApply(Function<T,R>)` | `CompletableFuture<T>` → `CompletableFuture<R>`, function returns a plain `R` | Transforming a result in place, e.g. mapping a raw ledger row to a `Money` |
| `thenCompose(Function<T, CompletableFuture<R>>)` | `CompletableFuture<T>` → `CompletableFuture<R>`, function returns *another* `CompletableFuture` | Chaining a dependent async call, e.g. "having settled the stake, now async-fetch the updated wallet" |
| `thenCombine(CompletionStage<U>, BiFunction<T,U,R>)` | Two independent `CompletableFuture`s → one `CompletableFuture<R>` | Joining two futures that ran concurrently and don't depend on each other, e.g. combining a PSP authorize result with an identity-vendor screening result |

The trap is reaching for `thenApply` when the function you want to run is itself asynchronous — `thenApply(id -> fetchWalletAsync(id))` doesn't give you `CompletableFuture<Wallet>`, it gives you `CompletableFuture<CompletableFuture<Wallet>>`, a nested future that nobody downstream is expecting and that silently "completes" once the outer future resolves while the inner one is still running.
`thenCompose` is the "flatMap" of futures specifically to avoid that nesting — it unwraps the inner future automatically.
`thenCombine` is for genuinely independent work that you want to run in parallel and then join, not for anything with a data dependency between the two futures.

```java
// broken: thenApply on an async-returning lambda double-nests the future
CompletableFuture<CompletableFuture<Wallet>> nested =
        settleStakeAsync(reservation)
                .thenApply(settled -> fetchWalletAsync(settled.clientId()));

// fixed: thenCompose flattens the inner future into the chain
CompletableFuture<Wallet> wallet =
        settleStakeAsync(reservation)
                .thenCompose(settled -> fetchWalletAsync(settled.clientId()));
```

The broken version compiles cleanly — the compiler infers the nested generic type without complaint — and the bug only shows up when calling code tries to treat `nested` as a `Wallet` future and instead gets back a future of a future, forcing an awkward extra `.thenCompose(Function.identity())` just to unwrap what should never have nested in the first place.

**Follow-up:**

"What does `thenApply` return if the upstream future completed exceptionally?" — it doesn't run the function at all; the exception propagates through unchanged to the resulting future, which is why exception handling has to be attached separately via `exceptionally`/`handle` (5.1.88), not inline in a `thenApply` chain.

All three methods also come in an `Async` variant (`thenApplyAsync`, `thenComposeAsync`, `thenCombineAsync`), and the same rule from 5.1.85 about always supplying an explicit executor applies uniformly across the whole family, not just to the plain, non-`Async` versions shown here.

**Pitfall:**

Using `thenApply` with a lambda that returns a `CompletableFuture` — the double-nesting compiles fine (the compiler infers `CompletableFuture<CompletableFuture<Wallet>>`) and the bug only surfaces when calling code tries to treat the result as a `Wallet` and gets a future instead.

**Interview:**

Interviewers frequently probe the double-nesting trap directly by asking what type an expression has after a `thenApply` call wraps an async-returning lambda — spotting the nested `CompletableFuture<CompletableFuture<R>>` immediately, without needing a hint, is the strong-signal answer.

### 5.1.84 Which thread runs a non-async `CompletableFuture` callback?

It depends entirely on *timing*, and that's the trap.
`thenApply`/`thenAccept`/`thenRun` (the non-`Async` variants) run on whichever thread completes the preceding stage — **if** the preceding stage is already complete by the time you attach the callback, the callback runs immediately, synchronously, on the calling thread (the thread that called `thenApply`, not any pool thread at all).
**If** the preceding stage is still pending, the callback instead runs later on whatever thread eventually calls `complete()` on it — which, for a future returned by `supplyAsync`, is a `ForkJoinPool.commonPool()` worker thread by default.
So the exact same line of code, `future.thenApply(this::processResult)`, might execute on the main thread, a request-handling thread, or a common-pool worker, depending purely on a race between "did the upstream finish yet." This non-determinism is precisely why relying on non-async variants for anything thread-sensitive (holding a lock, assuming a particular `ThreadLocal` context) is fragile.

**Follow-up:**

"How do you make the execution thread deterministic?" — use the `Async` variant with an explicit executor, `thenApplyAsync(fn, executor)`, which guarantees the callback always runs on a thread from that executor regardless of completion timing.

**Insight:**

This is the same class of surprise as "which thread runs a `synchronized` static initializer" — code that "usually" runs on one thread and occasionally runs on another is a debugging trap precisely because the common case masks the race.

**Pitfall:**

Writing test code that asserts a specific thread name or `ThreadLocal` value inside a non-async `thenApply` callback, and having the test pass locally (because the future happened to still be pending) and fail in CI (because timing shifted and the future had already completed) — the fix is either forcing the async variant or asserting on data, never on which thread happened to run the callback.

**Interview:**

This is one of the more subtle `CompletableFuture` questions, and a good answer volunteers the race-condition framing (it depends whether the upstream has already completed) before the interviewer has to pull it out with a follow-up.

### 5.1.85 Why should you always pass an executor to `CompletableFuture`?

Because every `*Async` method without an explicit executor argument defaults to `ForkJoinPool.commonPool()` (5.1.91) — a single JVM-wide pool shared by every other unrelated use of parallel streams, `CompletableFuture` chains, and any library code that also defaults to the common pool.
If a `CompletableFuture` chain processing card-PSP payout callbacks blocks inside a stage (e.g., a blocking JDBC call to persist a `WithdrawalTransaction` status), it ties up a common-pool worker for the duration of that blocking call — and because the common pool's parallelism is fixed at `availableProcessors() - 1` (on an 8-core box, 7 workers), a handful of chains blocking simultaneously can starve the entire shared pool for every other unrelated task in the JVM that also happens to route through it, including totally unrelated parallel-stream operations elsewhere in the same process.
Passing your own dedicated executor — sized deliberately per 5.1.75, for the actual downstream latency profile of PSP calls — isolates that blocking behavior to a pool that only your subsystem depends on.

**Follow-up:**

"Does this matter if none of your stages ever block?" — less critically, but it's still good hygiene, because you don't control what every future library or downstream call you compose with does, and the common pool's fixed small size means even brief blocking under load has an outsized effect.

The advice generalizes past `CompletableFuture` specifically — any API in the JDK or a library that silently defaults to a shared, unconfigurable thread pool deserves the same scrutiny, because the failure mode is always the same shape: unrelated code paths that happen to share the same default pool can starve each other in ways neither one's author could have anticipated.

**Pitfall:**

Defaulting to the no-executor `*Async` overloads because it's less code to write, then debugging a mysterious slowdown in an unrelated parallel `Stream.parallel()` call that turns out to share the same starved common pool.

**Interview:**

Interviewers use this to see whether the candidate connects `CompletableFuture` usage to broader thread-pool hygiene rather than treating it as an isolated API quirk — tying the answer back to the shared common-pool risk in 5.1.91 is the connection they're listening for.

### 5.1.86 How do you get the results out of `allOf`?

`CompletableFuture.allOf(futures...)` returns `CompletableFuture<Void>` — deliberately, because the input futures can have different generic types (`CompletableFuture<Money>`, `CompletableFuture<ScreeningVerdict>`, …), and there's no single type parameter that could hold "all of these results" generically.
`allOf` only tells you *when* every future has completed; it does not collect their values.
To actually get the results, you keep references to the original futures and call `.join()` (non-blocking by this point, since `allOf` already completed) on each one individually, typically inside the `thenRun`/`thenApply` attached after `allOf`:

```java
CompletableFuture<ScreeningVerdict> screening = screenAsync(clientId);
CompletableFuture<DocumentVerdict> documents = verifyDocumentsAsync(clientId);

CompletableFuture<ReviewCase> combined = CompletableFuture
        .allOf(screening, documents)
        .thenApply(v -> new ReviewCase(screening.join(), documents.join()));
```

Calling `.join()` here is safe and non-blocking in practice because `allOf`'s completion already guarantees both `screening` and `documents` are done — but it's still worth knowing `.join()` (unlike `.get()`) throws an unchecked `CompletionException` rather than a checked `ExecutionException`, which matters for how you structure the surrounding error handling.

**Follow-up:**

"What does `anyOf` give you instead?" — `CompletableFuture<Object>` completed with the value of whichever input future finishes first — the type erasure to `Object` is the same problem as `allOf`'s `Void`, just manifesting differently because at least one value exists but its static type is lost.

**Pitfall:**

Calling `.get()` instead of `.join()` inside the `thenApply` after `allOf` and being forced to handle a checked `InterruptedException`/`ExecutionException` pair for no benefit — since `allOf` has already guaranteed completion, `.join()`'s unchecked `CompletionException` is both sufficient and less intrusive to the surrounding lambda's checked-exception signature.

**Interview:**

A strong answer explains *why* `allOf` can't just return the results directly (heterogeneous generic types across the input futures) rather than only describing the join-afterward workaround as a memorized recipe.

### 5.1.87 Does `CompletableFuture.cancel(true)` interrupt the running task?

No.
Unlike `Future` returned from a `ThreadPoolExecutor`, where `cancel(true)` does interrupt the worker thread currently running the task, `CompletableFuture` has no built-in notion of "the thread currently executing this stage" that it can reach into and interrupt — `cancel()` on a `CompletableFuture` only transitions the future itself into a completed-exceptionally state (with `CancellationException`), so anyone calling `.get()`/`.join()` on it immediately sees the cancellation.
But if the stage's work is running inside, say, `supplyAsync(() -> callPspAuthorize(...), executor)`, that PSP call keeps running to completion on its worker thread regardless — cancellation never reaches it.
The `true`/`false` argument to `cancel` is a historical leftover from the `Future` interface `CompletableFuture` implements; it's accepted but has **no effect** on `CompletableFuture`'s own cancellation semantics.

**Follow-up:**

"So how do you actually stop in-flight work?" — you have to build cooperative cancellation yourself, typically by having the task body poll a shared `volatile boolean`/`AtomicBoolean` cancellation flag, or by using the underlying async call's own cancellation mechanism if the PSP client library exposes one (e.g., cancelling the underlying `HttpClient` request).

The same true/false-ignored behavior applies to interrupting the underlying thread for any `CompletableFuture` created via `supplyAsync`/`runAsync` — there is no path from `cancel()` back to the specific worker thread executing the stage, because `CompletableFuture` was designed around composable callbacks, not around thread lifecycle management.

**Pitfall:**

Calling `future.cancel(true)` on a `CompletableFuture` wrapping a slow PSP call, and assuming — because the method signature looks identical to `ExecutorService`'s `Future` — that the in-flight network call actually stops; it doesn't, and the call runs to completion, wasting the work and possibly still mutating state the caller thought it had cancelled.

**Insight:**

This mirrors the same lesson `ManagedBlocker` (5.1.90) teaches from the opposite direction — the JDK does not automatically extend cooperative cancellation or compensation into arbitrary async code; anything beyond a future's own bookkeeping state has to be built by the caller explicitly.

**Interview:**

This is a fast factual check with an unambiguous right answer — the interviewer is mainly listening for confident correctness and, ideally, the explanation of why (`CompletableFuture` has no thread handle to interrupt), not just the bare no.

### 5.1.88 Why do exceptions in a `CompletableFuture` chain disappear?

They don't disappear from the future itself — a `CompletableFuture` that completes exceptionally carries that exception forward through the chain, skipping every subsequent `thenApply`/`thenAccept`/`thenRun` stage (none of them run) until it hits a stage that's actually designed to observe exceptions.
The "disappearing" happens when nobody ever calls a method that surfaces it: if the terminal stage of the chain is `thenAccept(this::logResult)` and you never attach `.exceptionally(...)`, `.handle(...)`, or eventually call `.get()`/`.join()` on some future further downstream, the exception is stored inside the future object and simply never observed by anything — no log line, no stack trace, nothing, exactly like 5.1.77's `submit()` case but one level more subtle because it can silently skip several chained stages first.

```java
screenClientAsync(clientId)
        .thenApply(ScreeningVerdict::outcome)
        .thenAccept(outcome -> notificationService.publish(outcome))
        .exceptionally(ex -> {
            log.error("Screening chain failed for {}", clientId, ex);
            return null;
        });
```

Without that final `.exceptionally`, a screening-service timeout partway through the chain means `notificationService.publish` never runs, and — critically — nothing ever logs *why*.

**Follow-up:**

"What's the difference between `exceptionally` and `handle`?" — `exceptionally` only runs on the failure path and must return a replacement value of the same type; `handle(BiFunction<T, Throwable, R>)` runs on **both** the success and failure path, receiving whichever of `(result, null)` or `(null, exception)` applies, which is useful when you need unified cleanup logic regardless of outcome.

**Pitfall:**

Attaching `.exceptionally(...)` to an intermediate stage in the middle of a long chain and assuming it protects every stage after it — `exceptionally` only catches an exception from the stage(s) *before* it in the chain; a fresh exception thrown by a stage attached *after* the `exceptionally` call still propagates unguarded past it.

**Interview:**

This one is commonly paired with 5.1.77 as a two-part question asking where else an exception can silently disappear in the executor family, so having both the `submit()` case and the `CompletableFuture` chain case ready together is worth more than either alone.

### 5.1.89 What is work stealing and why LIFO local / FIFO steal?

`ForkJoinPool` gives each worker thread its own double-ended work queue (deque) of tasks.
A worker pushes and pops its *own* new tasks from the **head** of its own deque — LIFO — because the task it just forked is the one most likely to still have hot data in that core's cache, and depth-first LIFO processing on recursive fork/join work naturally processes the smallest, most-recently-split subtasks first, which keeps the recursion from ballooning memory with a huge backlog of not-yet-processed large tasks.
When a worker's own deque runs empty, it becomes a **thief**: it picks another worker's deque at random and steals from the **tail** — FIFO relative to that queue — deliberately taking the *oldest*, typically *largest* remaining task rather than competing with the queue's owner for the same end of the deque.
Stealing from the opposite end than the owner uses serves two purposes at once: it minimizes lock/CAS contention between the owner (popping its own head) and thieves (popping others' tails), and it steals the biggest available chunk of work, which is the most efficient unit to steal since it amortizes the steal's overhead over more actual work.

**Follow-up:**

"Why does this matter for a divide-and-conquer settlement-batch computation?" — splitting a batch of settlements recursively in half repeatedly produces exactly this shape: many small local tasks near the bottom of the recursion (handled LIFO, cache-friendly) and a few large top-level chunks that idle workers can usefully steal without needing to also steal many small ones.

**Pitfall:**

Assuming work stealing means idle workers steal from the front of another worker's deque, matching how they'd pop their own — thieves always take from the tail, specifically to avoid contending with the owner's head-side pops and to grab the largest, not the smallest, available chunk.

**Insight:**

This is the same head/tail-opposite-ends trick used by many other lock-free deque designs outside fork/join specifically because it minimizes the number of CAS retries needed when the owner and a thief happen to touch the deque at nearly the same instant.

**Interview:**

Interviewers listen for the two-sided answer — why LIFO locally (cache locality, bounded local backlog) and why FIFO for stealing (minimize contention, steal the biggest available chunk) — rather than only naming the work-stealing term without explaining either half.

### 5.1.90 Why must you not block in a fork/join task, and what is `ManagedBlocker`?

`ForkJoinPool`'s parallelism is fixed at pool-creation time (for the common pool, `availableProcessors() - 1`), and unlike `ThreadPoolExecutor`, it has no mechanism that automatically compensates when a worker blocks on I/O or a lock — if a fork/join task calls a blocking operation directly, that worker is simply unavailable to run or steal any other task for the duration, silently shrinking the pool's effective parallelism by one for as long as the block lasts.
With enough blocked tasks, the pool's usable parallelism can degrade to a fraction of its nominal size, or in the worst case (a task blocking waiting for a result that itself depends on a fork/join task that never gets a worker) deadlock entirely.

`ManagedBlocker` is the escape hatch: it's an interface (`isReleasable()` / `block()`) you implement around a blocking call and submit via `ForkJoinPool.managedBlock(blocker)`.
It tells the pool "I'm about to block — please compensate," and the pool responds by temporarily spinning up an extra worker thread (beyond its normal parallelism target) to keep the actual CPU-bound work moving while this one thread sits blocked, then retiring that extra thread once the block ends and `isReleasable()` reports true.

```java
class PspAuthorizeBlocker implements ForkJoinPool.ManagedBlocker {
    private final CompletableFuture<AuthResult> pending;
    private volatile AuthResult result;

    PspAuthorizeBlocker(CompletableFuture<AuthResult> pending) {
        this.pending = pending;
    }

    @Override
    public boolean block() throws InterruptedException {
        try {
            result = pending.get(11, TimeUnit.SECONDS); // PSP p99
        } catch (ExecutionException | TimeoutException e) {
            throw new InterruptedException(e.getMessage());
        }
        return true;
    }

    @Override
    public boolean isReleasable() {
        return result != null || pending.isDone();
    }
}
```

**Follow-up:**

"Would you actually recommend fork/join for PSP calls at all?" — no; a virtual-thread-per-call or a dedicated bounded executor (5.1.75) fits I/O-bound work far better than fork/join, which is purpose-built for CPU-bound divide-and-conquer — `ManagedBlocker` exists for the rare case where blocking inside fork/join is unavoidable, not as a general recommendation to mix the two styles.

**Pitfall:**

Assuming any blocking call anywhere inside fork/join automatically triggers `ManagedBlocker`-style compensation — compensation only happens for code explicitly wrapped and submitted through `ForkJoinPool.managedBlock(...)`; a raw blocking call made directly inside a `RecursiveTask`/`RecursiveAction` gets no automatic help and simply eats one worker's capacity for the duration.

**Interview:**

This is one of the more advanced questions in the set, and most interviewers are satisfied if a candidate correctly identifies that blocking silently shrinks effective parallelism, even without reciting the full `ManagedBlocker` interface from memory.

### 5.1.91 How many threads does `ForkJoinPool.commonPool()` have and who else uses it?

Its target parallelism defaults to `Runtime.getRuntime().availableProcessors() - 1` — on the 8-core box used for this domain's sizing elsewhere, that's 7 worker threads, deliberately one less than core count so the thread that submits work to the common pool (often the main thread, which itself counts as a participant in fork/join computations) isn't competing with a full complement of dedicated workers.
**Unverified:** the pool's `maximumPoolSize` for absorbing bursts beyond that parallelism is documented in some sources as `parallelism + DEFAULT_COMMON_MAX_SPARES` where `DEFAULT_COMMON_MAX_SPARES = 256`, giving a ceiling around 263 threads on an 8-core box — this could not be confirmed against JDK source during this pass, so treat the specific ceiling number as unverified even though `DEFAULT_COMMON_MAX_SPARES = 256` itself is a real named constant.

The common pool is **shared JVM-wide**, silently, by more callers than most engineers expect: every `Stream.parallel()` operation without an explicit executor, every `CompletableFuture.*Async` call without an explicit executor argument (5.1.85), and any direct `ForkJoinTask` submitted without constructing a private `ForkJoinPool`.
That sharing is exactly why 5.1.85's advice to pass an explicit executor to `CompletableFuture` matters — a blocking `CompletableFuture` stage and an unrelated parallel stream computation elsewhere in the same process can starve each other through this one shared pool, and neither call site looks like it has anything to do with the other.

**Follow-up:**

"How do you avoid the common pool entirely for a specific subsystem?" — construct a private `new ForkJoinPool(parallelism)` and either submit directly to it or run parallel-stream operations inside `pool.submit(() -> stream.parallel()....)`, which confines that stream's fork/join work to the private pool instead of the shared default.

The same shared-pool caution applies to `Stream.parallel()` calls made from application code that has no idea a `CompletableFuture` chain elsewhere in the same JVM is also routing through the common pool by default — both compete for the same fixed 7-worker (on this domain's 8-core box) budget with no coordination between them whatsoever.

**Pitfall:**

Assuming `ForkJoinPool.commonPool()` is "free" isolated parallelism because nobody explicitly configured it — it is a shared, JVM-wide, fixed-size resource that every unconfigured parallel stream and async future call quietly competes for.

**Interview:**

A well-prepared answer states the parallelism formula, names at least one hidden caller (parallel streams or unconfigured `CompletableFuture.*Async`), and flags the `maximumPoolSize` ceiling as something worth double-checking rather than asserting with false confidence.

**Insight:**

The `-1` in the parallelism formula is a small but real reminder that the common pool was designed around the assumption that the thread submitting the top-level task participates in the computation itself — a design borrowed from fork/join's original divide-and-conquer use case, where the caller of `invoke()` is expected to help do work while waiting, not the request-handling or scheduled-task use cases that lean on it indirectly today via streams and futures.

---

**Leaves covered:** 5.1.77–5.1.91 (15 questions)
**Leaves deferred:** none
**Diagrams included:** none
**Target version:** Java 21 LTS
**Lines:** 421

## Open questions

- 5.1.91: the common pool's `maximumPoolSize = parallelism + DEFAULT_COMMON_MAX_SPARES (256)` ceiling is a widely cited default that could not be confirmed against JDK 21 source in this pass; `DEFAULT_COMMON_MAX_SPARES = 256` itself is a real constant, but the resulting ceiling arithmetic is marked unverified.
