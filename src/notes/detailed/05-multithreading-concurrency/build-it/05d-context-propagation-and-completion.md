# 05 Multithreading and Concurrency — Context propagation and completion — BUILD IT (§4.5, leaves 4.5.7–4.5.8)

**Target version: Java 21 LTS.** | **Part 4 of 5** | [Index](../00-index.md)
Previous: [Hooks and thread factories](05c-hooks-and-thread-factories.md) · Next: [The pool consolidated diff](05e-pool-consolidated-diff.md)

---

## A context-propagating `Executor` decorator

### Mental model

A pool worker thread is a taxi, not a car you own — it picks up a fare (a task), drops it off,
and picks up the next one, with no memory of the previous passenger. Anything the *submitting*
thread had in its own head — which HTTP request this is, which trace id ties the logs together —
does not ride along with the task automatically, because `Runnable.run()` carries no arguments
beyond what the lambda closed over. `ApplicationGateway` sets an MDC trace id on the thread that
received the incoming request; the moment that request's work is handed to
`settlementPool.execute(...)`, the trace id is gone unless something explicitly carries it across.

### Why it exists

Before a decorator like this existed as a pattern, propagating context meant every call site that
submitted to an executor had to remember, by hand, to read the trace id, close over it in the
lambda, and re-install it inside the lambda body — an easy thing to forget once, and a `grep`
nightmare to audit for consistently. A single `Executor` wrapper that does the capture-install-clear
dance for every task, once, removes the burden from every call site.

### When to reach for it, and when not

Reach for it whenever tasks submitted to a pool need to see request-scoped state that lives in a
`ThreadLocal` (or `MDC`, which is `ThreadLocal`-backed) — logging correlation, per-request feature
flags, an interceptor-set locale. Don't reach for it when the context is small, immutable, and can
just be passed as a constructor argument or method parameter to the task instead — an explicit
parameter is strictly clearer than an implicit thread-local trip, and should be preferred whenever
the call site controls how the task is constructed. The decorator earns its keep specifically when
the context must flow through code the caller doesn't control (a library's logging statements
inside the task body that read MDC directly) or across many call sites uniformly.

### The mechanism

Capture happens on the *submitting* thread, at `execute()` time — that's the only point at which
the correct context is guaranteed to be current. Install happens on the *worker* thread,
immediately before `task.run()`. Clear happens on the worker thread in a `finally`, restoring
whatever the worker's MDC held before this task, not simply removing the key outright.

```java
public final class ContextPropagatingExecutor implements Executor {

    private final Executor delegate;

    public ContextPropagatingExecutor(Executor delegate) {
        this.delegate = Objects.requireNonNull(delegate, "delegate");
    }

    @Override
    public void execute(Runnable task) {
        String traceId = MDC.get("traceId");
        Map<String, String> capturedContext = MDC.getCopyOfContextMap();
        delegate.execute(() -> runWithContext(task, traceId, capturedContext));
    }

    private static void runWithContext(Runnable task, String traceId,
                                        Map<String, String> capturedContext) {
        Map<String, String> priorContext = MDC.getCopyOfContextMap();
        try {
            if (capturedContext != null) {
                MDC.setContextMap(capturedContext);
            } else {
                MDC.clear();
            }
            if (traceId != null) {
                MDC.put("traceId", traceId);
            }
            task.run();
        } finally {
            if (priorContext != null) {
                MDC.setContextMap(priorContext);
            } else {
                MDC.clear();
            }
        }
    }
}
```

A minimal `MDC` stand-in, since the real one is a logging-framework class, not a JDK class — the
shape is what matters, and this mirrors SLF4J's `MDC` API exactly:

```java
public final class MDC {

    private static final ThreadLocal<Map<String, String>> CONTEXT = new ThreadLocal<>();

    private MDC() {}

    public static String get(String key) {
        Map<String, String> map = CONTEXT.get();
        return map == null ? null : map.get(key);
    }

    public static void put(String key, String value) {
        CONTEXT.get() == null
            ? CONTEXT.set(new HashMap<>(Map.of(key, value)))
            : CONTEXT.get().put(key, value);
    }

    public static Map<String, String> getCopyOfContextMap() {
        Map<String, String> map = CONTEXT.get();
        return map == null ? null : new HashMap<>(map);
    }

    public static void setContextMap(Map<String, String> contextMap) {
        CONTEXT.set(new HashMap<>(contextMap));
    }

    public static void clear() {
        CONTEXT.remove();
    }
}
```

Wired around the settlement pool:

```java
Executor rawSettlementPool = new MiniThreadPool(
    8, 24, 60L, TimeUnit.SECONDS,
    new LinkedBlockingQueue<>(2_000),
    new NamedThreadFactory("settlement-ingest"),
    new AbortPolicy());

Executor settlementPool = new ContextPropagatingExecutor(rawSettlementPool);

// on the ApplicationGateway's request-handling thread:
MDC.put("traceId", requestTraceId);
settlementPool.execute(() -> ledger.reserveStake(clientId, stakeAmount, roundId));
// the settlement task's logging statements now emit the same traceId as the request that queued it
```

### The gotcha

`MDC.getCopyOfContextMap()` must be called on the *submitting* thread, inside `execute()`, before
the lambda that runs later on the worker thread. Reading `MDC.get(...)` *inside* the inner lambda
instead of capturing it outside would read the worker thread's MDC state at the moment the worker
gets around to running it — which is either empty (if this is the worker's first task) or, far more
dangerously, whatever the *previous* task on that worker left behind, since `ThreadLocal` state
persists on a pool thread between tasks by design. Capturing must happen at submission time on the
submitting thread; installing and clearing happen at execution time on the worker thread — three
distinct moments, easy to collapse into one by accident.

**Pitfall:** the `finally` that restores `priorContext` is not optional, and the reason is worth
stating precisely: a pool thread outlives any single task, so a context left installed after a
task finishes leaks into whichever task the *same worker thread* picks up next — which may belong
to an entirely different client, request, or trace. This is a correctness and security bug, not
merely a memory leak: the next settlement task processed by that worker would log under the wrong
`traceId`, and worse, if the context carried anything more sensitive than a trace id — an
authenticated `ClientId`, a compliance flag, an authorization decision cached per-request — a
worker that skips the clear step hands one client's context to the code processing a different
client's task. `ThreadPoolExecutor` reuses threads precisely to avoid the cost of spawning one per
task; that reuse is exactly what turns a missing `finally` into cross-request contamination instead
of a contained, single-task mistake.

**Insight:** restoring to `priorContext` — not to "empty" — matters the moment executors nest or a
task itself submits more work to the same or another pool. If worker thread `settlement-ingest-3`
is, unusually, already inside some outer context when it's asked to run a task (rare for a leaf
pool, common for a decorator stacked on another decorator), blindly clearing at the end would erase
state that thread owned before this decorator ever touched it, rather than returning the thread to
exactly the state it was in beforehand.

> A context-propagating executor captures the submitting thread's `ThreadLocal`-backed state at
> submission time, installs it on the worker thread immediately before the task runs, and restores
> the worker's prior state — not empty state — in a `finally`, because pool threads outlive
> individual tasks and any context left behind leaks into whichever unrelated task the same thread
> picks up next.

## A `CompletionService` from scratch

### Why it exists

`Future.get()` on a specific future blocks until *that* future completes — fine when you're waiting
on one task, wrong when you've fired off twenty settlement lookups and want to process whichever
finishes first, in whatever order they actually complete, rather than in submission order. Polling
every future in a loop (`for (Future<T> f : futures) if (f.isDone()) ...`) busy-waits and wastes
CPU. A `CompletionService` inverts the problem: instead of you asking each future "are you done
yet?", each task, when it finishes, pushes itself onto a queue you block on.

### The mechanism

Wrap every submitted task in a `FutureTask` subclass whose `done()` hook — called by `FutureTask`
itself, on whichever thread finishes running the task — enqueues the completed future onto a shared
`BlockingQueue<Future<V>>`. `take()`/`poll()` on the service then just delegate to that queue.

```java
public final class MiniCompletionService<V> {

    private final Executor executor;
    private final BlockingQueue<Future<V>> completionQueue;

    public MiniCompletionService(Executor executor) {
        this(executor, new LinkedBlockingQueue<>());
    }

    public MiniCompletionService(Executor executor, BlockingQueue<Future<V>> completionQueue) {
        this.executor = Objects.requireNonNull(executor, "executor");
        this.completionQueue = Objects.requireNonNull(completionQueue, "completionQueue");
    }

    public Future<V> submit(Callable<V> task) {
        QueueingFuture future = new QueueingFuture(task);
        executor.execute(future);
        return future;
    }

    public Future<V> take() throws InterruptedException {
        return completionQueue.take();
    }

    public Future<V> poll() {
        return completionQueue.poll();
    }

    public Future<V> poll(long timeout, TimeUnit unit) throws InterruptedException {
        return completionQueue.poll(timeout, unit);
    }

    private final class QueueingFuture extends FutureTask<V> {

        QueueingFuture(Callable<V> task) {
            super(task);
        }

        @Override
        protected void done() {
            completionQueue.add(this);
        }
    }
}
```

Used to settle whichever of a batch of round lookups against the Quiz Engine finishes first, rather
than waiting on them in submission order:

```java
MiniCompletionService<SettlementResult> completions = new MiniCompletionService<>(settlementPool);

List<RoundId> pendingRounds = List.of(roundA, roundB, roundC, roundD);
for (RoundId round : pendingRounds) {
    completions.submit(() -> quizEngine.settleStake(round));
}

for (int i = 0; i < pendingRounds.size(); i++) {
    Future<SettlementResult> completed = completions.take(); // blocks until ANY task finishes
    try {
        SettlementResult result = completed.get();
        ledger.applySettlement(result);
    } catch (ExecutionException e) {
        System.err.println("settlement failed: " + e.getCause());
    }
}
```

Because `take()` returns futures in *completion* order rather than *submission* order, `roundC`'s
settlement (say it's the fastest round to resolve against the Quiz Engine) gets applied to the
ledger the moment it's ready, instead of waiting behind `roundA` and `roundB` if either of those is
still in flight — exactly the ordering `Future.get()` on a fixed list cannot give you without
manual polling.

### The gotcha

`done()` is called by `FutureTask` internally, from whichever thread calls `set(V)` or
`setException(Throwable)` — normally the worker thread that ran the task, but if `cancel(true)` is
called on the future from some other thread, `done()` fires from *that* cancelling thread instead.
`QueueingFuture.done()` only ever enqueues `this`, which is safe either way since the queue is
thread-safe, but any override that assumes `done()` always runs on the pool's own worker threads
(to touch thread-local state, say) would be wrong.

**Pitfall:** calling `take()` more times than tasks were submitted blocks forever with no timeout
and no error — there is nothing distinguishing "no task has completed yet" from "there are no more
tasks coming." A `MiniCompletionService`, like the real `ExecutorCompletionService`, has no notion
of how many submissions to expect; the caller must track that itself (the loop above bounds it with
`pendingRounds.size()`), or use `poll(timeout, unit)` and treat a `null` as "nothing new yet,"
never as "done."

**Interview:** "how would you process the fastest of N parallel calls first?" — the tempting wrong
answer is "loop over the futures and check `isDone()`," which busy-waits; the right answer names
`CompletionService` (or `MiniCompletionService` here) specifically, and the one-line mechanism:
each task enqueues its own completed future via a `done()` hook, so `take()` is a blocking pop off
a queue rather than a poll over a list.

> A `CompletionService` decouples *submitting* tasks to an executor from *consuming* their results
> in completion order, by wrapping each task so it pushes its own finished `Future` onto a shared
> queue the instant it's done, rather than requiring the caller to poll or wait on futures in
> submission order.

---

## Pitfalls

### Reading MDC inside the submitted lambda instead of capturing it in `execute()`

**Wrong**

```java
@Override
public void execute(Runnable task) {
    delegate.execute(() -> {
        String traceId = MDC.get("traceId"); // reads the WORKER thread's MDC, not the caller's
        MDC.put("traceId", traceId);
        task.run();
    });
}
```

**Right**

```java
@Override
public void execute(Runnable task) {
    String traceId = MDC.get("traceId"); // captured on the SUBMITTING thread, right now
    delegate.execute(() -> runWithContext(task, traceId, MDC.getCopyOfContextMap()));
}
```

**Why people believe it:** the lambda body reads visually like "the code that will eventually run,"
so it's natural to assume any statement inside it executes in the caller's context — but the lambda
is only a recipe; it doesn't execute until a worker thread picks it up, on which thread `MDC.get`
means something entirely different.

### Clearing MDC to empty instead of restoring the prior context

**Wrong**

```java
try {
    MDC.setContextMap(capturedContext);
    task.run();
} finally {
    MDC.clear(); // wipes whatever this worker thread had BEFORE this task, not just this task's context
}
```

**Right**

```java
Map<String, String> priorContext = MDC.getCopyOfContextMap();
try {
    MDC.setContextMap(capturedContext);
    task.run();
} finally {
    if (priorContext != null) MDC.setContextMap(priorContext); else MDC.clear();
}
```

**Why people believe it:** for the common case — a plain worker pool where every task goes through
the same decorator and nothing is nested — clearing to empty and restoring the true prior state
produce identical results, so the bug only shows up once decorators stack or a task itself
resubmits work, which is easy to never test.

## Cheat sheet

| Concern | `ContextPropagatingExecutor` | `MiniCompletionService` |
|---|---|---|
| Capture point | submitting thread, inside `execute()`, before handing to delegate | n/a |
| Install point | worker thread, immediately before `task.run()` | n/a — `FutureTask` handles execution |
| Clear point | worker thread, `finally`, restores prior state (not empty) | n/a |
| Core data structure | `ThreadLocal`-backed `MDC` map | `BlockingQueue<Future<V>>` |
| The hook that does the work | none — plain wrapping lambda | `FutureTask.done()`, overridden |
| Blocking call | none itself — delegates to underlying executor | `take()` blocks until any task completes |
| Non-blocking call | n/a | `poll()` returns `null` immediately if nothing's done |
| Ordering delivered | preserves the task's original submission semantics | completion order, not submission order |
| Biggest correctness risk | leaking one task's context into the next task on a reused worker | caller losing track of how many completions to expect |

## Self-test

**Q1.** Why must `MDC.getCopyOfContextMap()` be called inside `execute()`, on the thread calling
`execute()`, rather than inside the lambda passed to the delegate executor?

<details><summary>Answer</summary>

`execute()` runs synchronously on the submitting thread the instant it's called, so that is the
only point at which the caller's actual context (the trace id `ApplicationGateway` set for this
request) is guaranteed to be current. The lambda passed to the delegate executor doesn't run until
some worker thread later dequeues and executes it — by then the calling thread has moved on, and
reading MDC from inside the lambda would read the worker thread's own state instead, which is
either unrelated or leftover from a previous task.

</details>

**Q2.** A pool worker thread runs task A (which installs client X's trace id via the decorator),
then, without a `finally`-based restore, runs task B for client Y. What does task B's logging show,
and why is this worse than a plain memory leak?

<details><summary>Answer</summary>

Task B's logging would show client X's trace id (or whatever context task A left installed),
because the `ThreadLocal` state persists on the reused worker thread between tasks. This is worse
than a memory leak because it is a correctness and potential security defect: log lines meant to
trace client Y's request would be attributed to client X, and if the propagated context carried
anything more sensitive than a trace id (an authenticated identity, a cached authorization
decision), task B's code could act under client X's context by mistake.

</details>

**Q3.** Why does the `finally` block restore `priorContext` rather than simply calling `MDC.clear()`?

<details><summary>Answer</summary>

`MDC.clear()` assumes the worker thread had no context before this task started, which is true only
in the simplest case. If executors are nested or a task resubmits work such that the worker thread
already carried some context before this particular task's context was installed, blindly clearing
would erase that pre-existing state instead of returning the thread to exactly what it held before.
Capturing `priorContext` before installing the new context and restoring it afterward handles both
cases correctly.

</details>

**Q4.** What does `QueueingFuture.done()` do, and on which thread does it typically run?

<details><summary>Answer</summary>

`done()` calls `completionQueue.add(this)`, pushing the just-completed `FutureTask` onto the shared
`BlockingQueue<Future<V>>` that `take()`/`poll()` read from. `FutureTask` calls `done()` internally
from whichever thread transitions the future to a terminal state — normally the pool worker thread
that finished running the task's `Callable`, but if the future is cancelled from another thread via
`cancel(true)`, `done()` fires on that cancelling thread instead.

</details>

**Q5.** Why does `take()` on a `MiniCompletionService` return futures in completion order rather
than submission order, and what's the mechanism that makes that true?

<details><summary>Answer</summary>

Each submitted task is wrapped in a `QueueingFuture` whose `done()` override enqueues itself onto
`completionQueue` the instant it finishes — not when it was submitted, but when it actually
completes. Since `BlockingQueue` preserves insertion order and insertion here happens at completion
time, whichever task finishes first is inserted first, so `take()`'s FIFO pop naturally yields
completion order regardless of what order the tasks were originally submitted in.

</details>

**Q6.** If a caller calls `completionQueue.take()` (via the service's `take()`) one more time than
the number of tasks it submitted, what happens?

<details><summary>Answer</summary>

The call blocks indefinitely — `take()` on an empty `BlockingQueue` waits for an element to become
available, and since no more tasks were submitted, none ever will be. There is nothing in
`MiniCompletionService` (matching the real `ExecutorCompletionService`) that tracks how many
submissions were made versus how many completions were consumed; the caller is entirely responsible
for bounding its own consumption loop, typically by counting submissions.

</details>

**Q7.** Why is it acceptable for `QueueingFuture` to not override `run()` at all, relying entirely
on `FutureTask`'s own `run()` and only overriding `done()`?

<details><summary>Answer</summary>

`FutureTask.run()` already does exactly what's needed — it invokes the wrapped `Callable`, captures
either the result or the thrown exception, transitions the future's internal state to a terminal
state, and then calls `done()` as its very last step. `QueueingFuture` only needs to add behaviour
at that last step (enqueue itself), so overriding `done()` alone is sufficient; overriding `run()`
as well would mean re-implementing `FutureTask`'s result-capturing logic for no benefit.

</details>

---

**Leaves covered:** 4.5.7–4.5.8 (2 leaves)
**Leaves deferred:** none
**Diagrams included:** none
**Target version:** Java 21 LTS
**Lines:** 473
