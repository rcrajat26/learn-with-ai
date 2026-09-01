# 05 Multithreading and Concurrency — A thread pool from scratch — BUILD IT (§4.5, leaves 4.5.1–4.5.2)

**Target version: Java 21 LTS.** | **Part 4 of 5** | [Index](../00-index.md)
Previous: [The non-blocking consolidated diff](04f-non-blocking-consolidated-diff.md) · Next: [Packed ctl and rejection](05b-packed-ctl-and-rejection.md)

This file starts a `MiniThreadPool` that grows across three files in this section. Here: v1 (N
workers over one queue, clean shutdown) and v2 (a `submit` that returns your own `Future`). The
sibling file [`05b`](05b-packed-ctl-and-rejection.md) adds v3 (packed `ctl`) and v4 (sizing plus
rejection). The class name `MiniThreadPool` and every field introduced here — `workQueue`,
`workers`, `POISON_PILL` — stay fixed for the rest of the arc; later files only add fields, never
rename these.

The stake-settlement service needs a bounded worker pool: at 3,400 settlements/sec burst, an
unbounded `new Thread(task).start()` per settlement would fork tens of thousands of OS threads and
fall over on context-switch overhead alone. A pool caps concurrency to what the machine can
actually run and reuses threads instead of paying thread-creation cost per task.

## v1 — N workers, one queue, poison-pill shutdown

### Mental model

A `ThreadPoolExecutor`-style pool is nothing but a **shared mailbox and a fixed crew of readers**.
Every worker thread runs the same loop forever: pull a task off the queue, run it, pull the next
one. `execute(Runnable)` never runs the task itself — it only drops an envelope in the mailbox.
The pool's entire job is keeping that mailbox thread-safe and knowing when to tell the crew to go
home.

### Why it exists

Before pools, the obvious move was `new Thread(task).start()` per unit of work. Two costs: OS
thread creation (kernel stack allocation, scheduler registration) is not free, and there is no cap
— 1,200 stake reservations/sec each spawning a thread means 1,200 live threads competing for 8
cores, most of them blocked on `FundsLedger.reserveStake`'s downstream lock. A pool decouples
"how much work exists" from "how many threads exist."

### When to reach for it, and when not

Reach for a hand-rolled pool only to learn the mechanism — production code uses
`Executors.newFixedThreadPool` (JDK-backed `ThreadPoolExecutor`) or, on Java 21+, virtual threads
via `Executors.newVirtualThreadPerTaskExecutor()` for I/O-bound work like the settlement pool's
downstream ledger calls. A hand-rolled pool loses the JDK's tuned rejection policies, its
monitoring hooks, and forty years of edge-case fixes. It earns its keep exactly once: understanding
what `ThreadPoolExecutor` does under the hood.

### How it works

Three fields: a `BlockingQueue<Runnable>` as the mailbox, a fixed array of worker `Thread`s, and a
sentinel `Runnable` — the poison pill — that means "stop, don't run me." `execute` offers a task to
the queue. Each worker's run loop takes a task; if the task **is** the poison pill (identity
check), the worker exits its loop and terminates; otherwise it runs the task and loops. `shutdown()`
enqueues one poison pill per worker, guaranteeing each worker sees exactly one and none starve
waiting on a pill meant for a sibling.

![D-206 — The mini ThreadPoolExecutor, version by version](../diagrams/D-206-mini-threadpoolexecutor.svg)

**D-206** — The mini `ThreadPoolExecutor`, version by version. This file covers frames 1 (N
workers over one `BlockingQueue`) and 2 (`submit` and the `Future` state machine). Frames 3–5 —
packed `ctl`, core/max sizing with the four rejection policies, and `beforeExecute`/`afterExecute`
— arrive in the sibling files `05b` and `05c`.

### Code

```java
public class MiniThreadPool {

    private static final Runnable POISON_PILL = () -> { };

    private final BlockingQueue<Runnable> workQueue;
    private final Thread[] workers;
    private volatile boolean shutdownRequested = false;

    public MiniThreadPool(int poolSize, int queueCapacity) {
        this.workQueue = new LinkedBlockingQueue<>(queueCapacity);
        this.workers = new Thread[poolSize];
        for (int i = 0; i < poolSize; i++) {
            workers[i] = new Thread(this::workerLoop, "settlement-ingest-" + (i + 1));
            workers[i].start();
        }
    }

    public void execute(Runnable task) {
        if (shutdownRequested) {
            throw new RejectedExecutionException(
                "MiniThreadPool has been shut down, task rejected: " + task);
        }
        try {
            workQueue.put(task);
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
            throw new RejectedExecutionException("Interrupted while enqueueing task", e);
        }
    }

    private void workerLoop() {
        while (true) {
            Runnable task;
            try {
                task = workQueue.take();
            } catch (InterruptedException e) {
                Thread.currentThread().interrupt();
                return;
            }
            if (task == POISON_PILL) {
                return;
            }
            try {
                task.run();
            } catch (RuntimeException e) {
                System.err.println(Thread.currentThread().getName() + " task failed: " + e);
            }
        }
    }

    public void shutdown() {
        shutdownRequested = true;
        for (int i = 0; i < workers.length; i++) {
            workQueue.add(POISON_PILL);
        }
    }

    public void awaitTermination() throws InterruptedException {
        for (Thread worker : workers) {
            worker.join();
        }
    }
}
```

Usage against the settlement domain — a burst of `SettleStake` calls submitted as fire-and-forget
work:

```java
MiniThreadPool pool = new MiniThreadPool(8, 500);
for (Reservation reservation : pendingSettlements) {
    pool.execute(() -> fundsLedger.reserveStake(reservation.stakeId(), reservation.amount()));
}
pool.shutdown();
pool.awaitTermination();
```

### The invariant

Exactly one poison pill is consumed per worker, and workers never run a task after consuming
theirs. This holds because `shutdown()` enqueues exactly `workers.length` pills and every worker
loop terminates on the first pill it dequeues — there is no path back into the loop after the
`return`. `LinkedBlockingQueue` is FIFO, but that FIFO order is irrelevant to correctness here:
even if pills interleaved arbitrarily with tasks, each worker still stops after its own first pill,
and the count of pills equals the count of workers, so none is left waiting forever and none sees
two.

### The cost

Poison pills are simple but blunt: a pill occupies a queue slot like any task, so on a
bounded queue near capacity, `shutdown()` can itself block in `workQueue.add` if you use `put`
semantics — here `add` throws `IllegalStateException` on a full queue instead, which is arguably
worse for a shutdown path. The real `ThreadPoolExecutor` avoids this entirely: it does not use a
sentinel value, it inspects run state directly (see `05b`) and interrupts idle workers out of
`take()`.

**Pitfall:** calling `shutdown()` twice enqueues `2 * workers.length` pills, but only
`workers.length` workers exist to consume them — the surplus pills sit in the queue forever
(harmless here, since nothing polls a dead queue, but it is dead weight and a symptom of not
tracking shutdown state per-call). Guard with the `shutdownRequested` flag before enqueueing, not
just before accepting new work.

**Insight:** `shutdown()` here is "wait for in-flight and queued work to drain then stop" — the
JDK's `shutdown()` — not `shutdownNow()`, which interrupts running workers and drains the queue
without running its contents. This implementation only builds the graceful variant; leaves 4.5.3
onward add run-state tracking that makes an interrupt-based `shutdownNow()` possible.

### Diff vs the real one

| Aspect | `MiniThreadPool` v1 | `ThreadPoolExecutor` |
|---|---|---|
| Shutdown signal | Poison pill per worker | Packed `ctl` run-state bits (`SHUTDOWN`, `STOP`) |
| Worker exit | Identity check on dequeued task | `getTask()` returns `null` when state demands exit |
| Idle timeout | None — workers block forever on `take()` | `keepAliveTime` via `poll(timeout)` when `allowCoreThreadTimeOut` or above core |
| Queue full behavior | `put` blocks caller indefinitely | Configurable rejection policy (v4) |
| Task failure | Swallowed, logged | Propagated to `afterExecute` hook, `Future` gets exception |
| Worker naming | Manual `"settlement-ingest-" + i` | `ThreadFactory` abstraction |

## v2 — `submit(Callable<T>)` and your own `Future`

### Mental model

`execute` is a one-way message: drop it and forget it. `submit` needs a **receipt** — a handle the
caller keeps that will eventually hold either the task's result or the reason it failed. That
receipt is a `Future`: a box that starts empty, gets filled exactly once by the worker thread, and
lets any other thread block until the box is filled.

### Why it exists

`SettleStake` settlement tasks are fire-and-forget, but reconciliation jobs are not: a job that
computes the day's `HOUSE_REVENUE` delta from settled stakes needs the actual `BigDecimal` result
back, and needs to know if the computation threw (a `LedgerImbalanceException`, say) rather than
silently vanishing the way v1's `execute` would swallow it.

### When to reach for it, and when not

`submit` when the caller needs the result or needs to detect failure. `execute` when the task's
side effect (writing to the ledger, sending a notification) is the entire point and nobody is
waiting on a return value. Blocking on `future.get()` from many callers concentrates backpressure
in the caller instead of the pool — for a burst of 3,400 settlements/sec, blocking each caller
defeats the purpose of pooling; prefer `execute` plus an async completion signal (that mechanism
is `CompletableFuture`, out of scope here) unless the call site genuinely needs the value
synchronously.

### How it works

`MiniFuture<T>` holds a state field (`PENDING`, `COMPLETED`, `FAILED`, `CANCELLED`), a result slot,
an exception slot, and uses the object's own monitor for `wait`/`notifyAll`. The worker, after
running the wrapped `Callable`, calls `complete(result)` or `completeExceptionally(ex)` — both
synchronized, both transition state exactly once and call `notifyAll()`. `get()` synchronizes,
loops on `while (state == PENDING) wait()` to survive spurious wakeups, then either returns the
result or rethrows the stored exception wrapped in `ExecutionException`, matching the real
`Future` contract.

```java
public final class MiniFuture<T> implements Future<T> {

    private enum State { PENDING, COMPLETED, FAILED, CANCELLED }

    private final Object lock = new Object();
    private State state = State.PENDING;
    private T result;
    private Throwable failure;
    private volatile Thread runnerThread;

    void bindRunner(Thread thread) {
        this.runnerThread = thread;
    }

    void complete(T value) {
        synchronized (lock) {
            if (state != State.PENDING) return;
            state = State.COMPLETED;
            this.result = value;
            lock.notifyAll();
        }
    }

    void completeExceptionally(Throwable ex) {
        synchronized (lock) {
            if (state != State.PENDING) return;
            state = State.FAILED;
            this.failure = ex;
            lock.notifyAll();
        }
    }

    @Override
    public boolean cancel(boolean mayInterruptIfRunning) {
        synchronized (lock) {
            if (state != State.PENDING) return false;
            state = State.CANCELLED;
            lock.notifyAll();
        }
        if (mayInterruptIfRunning && runnerThread != null) {
            runnerThread.interrupt();
        }
        return true;
    }

    @Override
    public boolean isCancelled() {
        synchronized (lock) {
            return state == State.CANCELLED;
        }
    }

    @Override
    public boolean isDone() {
        synchronized (lock) {
            return state != State.PENDING;
        }
    }

    @Override
    public T get() throws InterruptedException, ExecutionException {
        synchronized (lock) {
            while (state == State.PENDING) {
                lock.wait();
            }
            return resolve();
        }
    }

    @Override
    public T get(long timeout, TimeUnit unit)
            throws InterruptedException, ExecutionException, TimeoutException {
        long deadlineNanos = System.nanoTime() + unit.toNanos(timeout);
        synchronized (lock) {
            while (state == State.PENDING) {
                long remainingNanos = deadlineNanos - System.nanoTime();
                if (remainingNanos <= 0) {
                    throw new TimeoutException("MiniFuture timed out after " + timeout + " " + unit);
                }
                TimeUnit.NANOSECONDS.timedWait(lock, remainingNanos);
            }
            return resolve();
        }
    }

    private T resolve() throws ExecutionException {
        if (state == State.CANCELLED) {
            throw new CancellationException("Task was cancelled");
        }
        if (state == State.FAILED) {
            throw new ExecutionException(failure);
        }
        return result;
    }
}
```

`submit` on `MiniThreadPool` wraps the `Callable` in a `Runnable` that drives the `MiniFuture`:

```java
public <T> Future<T> submit(Callable<T> task) {
    if (shutdownRequested) {
        throw new RejectedExecutionException("MiniThreadPool has been shut down, task rejected");
    }
    MiniFuture<T> future = new MiniFuture<>();
    Runnable wrapper = () -> {
        future.bindRunner(Thread.currentThread());
        try {
            T value = task.call();
            future.complete(value);
        } catch (Throwable t) {
            future.completeExceptionally(t);
        }
    };
    execute(wrapper);
    return future;
}
```

Domain usage — settling a stake and getting the resulting ledger position back:

```java
Future<Money> houseRevenueDelta = pool.submit(() ->
    fundsLedger.settleStake(reservation.stakeId(), Verdict.won()));

try {
    Money delta = houseRevenueDelta.get(5, TimeUnit.SECONDS);
    System.out.println("HOUSE_REVENUE moved by " + delta);
} catch (ExecutionException e) {
    System.err.println("Settlement failed: " + e.getCause());
} catch (TimeoutException e) {
    System.err.println("Settlement did not complete within 5s");
}
```

### The invariant

`state` moves `PENDING → {COMPLETED | FAILED | CANCELLED}` exactly once, and every mutation of
`state`, `result`, and `failure` happens under the same monitor (`lock`) that guards the
`wait`/`notifyAll` pair. The `state != State.PENDING` guard at the top of `complete`,
`completeExceptionally`, and `cancel` makes the transition idempotent-safe: whichever of a racing
worker-completion and a caller-cancellation gets the monitor first wins, and the loser's write is
silently dropped rather than corrupting an already-resolved future. `get()`'s `while` loop (not
`if`) is required because `wait()` may return without a corresponding `notifyAll()` — the JLS
permits spurious wakeup, so re-checking the condition after every wake is not defensive
programming, it is the only correct implementation.

### The cost

One `Object` monitor per future means every `get()` call and every `complete()` call contends on
the same lock even though they touch disjoint memory in the common case (one writer, one or more
readers). At settlement volumes this is fine — one future per task, short hold times — but it is
strictly more expensive than the JDK's `CompletableFuture`, which uses a lock-free CAS-based
completion stack (a `Completion` linked list swapped in with `VarHandle.compareAndSet`) precisely
to avoid parking every waiter on a single monitor under contention.

**Pitfall:** forgetting `bindRunner` before starting the task means `cancel(true)` has no thread
to interrupt — `mayInterruptIfRunning` silently becomes a no-op. The real `FutureTask` has the
same hazard window (between `Future` creation and the runner actually starting); it closes it by
setting the runner field from inside `run()` before calling `call()`, which is exactly the
ordering used above.

**Interview:** "Why does `get()` loop on `wait()` instead of using `if`?" — spurious wakeup is
allowed by the JLS; a `wait()` can return with no corresponding `notify()`. Looping on the
condition, not the wakeup, is the only implementation that is correct under that guarantee.

> A `Future` is a synchronized box that starts empty, is filled exactly once by whichever thread
> finishes (or cancels) it first, and blocks every reader on that one filling.

### Diff vs the real one

| Aspect | `MiniFuture<T>` | JDK `FutureTask<T>` |
|---|---|---|
| Completion signalling | `synchronized` + `wait`/`notifyAll` | CAS on a packed `state` int (`NEW`, `COMPLETING`, `NORMAL`, `EXCEPTIONAL`, `CANCELLED`, `INTERRUPTING`, `INTERRUPTED`) |
| Waiter tracking | Implicit — JVM monitor wait-set | Explicit `WaitNode` treiber stack, lock-free push |
| Cancellation states | One `CANCELLED` | Splits into `CANCELLED` and `INTERRUPTING`/`INTERRUPTED` to sequence the interrupt correctly |
| Result storage | Plain field under the monitor | Plain field, but published via a `state` release fence (`Unsafe`/`VarHandle`), not a monitor |
| Timeout wait | `TimeUnit.NANOSECONDS.timedWait` | `LockSupport.parkNanos` on the waiting thread |

## Pitfalls

### Assuming `execute` after `shutdown()` silently queues the task

**Wrong**
```java
pool.shutdown();
pool.execute(() -> fundsLedger.reserveStake(stakeId, amount)); // hope it still runs
```
This throws `RejectedExecutionException` immediately in v1 — there is no silent queueing path,
which is correct, but a caller who does not read the flag first gets an unchecked exception at an
unexpected call site.

**Right**
```java
if (!pool.isShutdown()) {
    pool.execute(() -> fundsLedger.reserveStake(stakeId, amount));
} else {
    deadLetterQueue.add(reservation);
}
```
Check shutdown state (expose an `isShutdown()` accessor) before submitting, and route rejected
work to an explicit fallback rather than letting the exception surface deep in a settlement
pipeline.

**Why people believe it:** `execute` "looks like" `workQueue.put`, and a queue with capacity left
looks like it should accept more items regardless of pool state — the shutdown check is a
pool-level policy layered on top of a queue-level capacity check, and it is easy to reason about
only the queue.

### Assuming `future.get()` rethrows the original exception type

**Wrong**
```java
try {
    future.get();
} catch (LedgerImbalanceException e) { // never matches — compile error, in fact
    ...
}
```

**Right**
```java
try {
    future.get();
} catch (ExecutionException e) {
    if (e.getCause() instanceof LedgerImbalanceException imbalance) {
        handleImbalance(imbalance);
    }
}
```

**Why people believe it:** the task's own `catch` blocks would see the real exception type
directly; wrapping only happens because the exception crosses a thread boundary through the
future, and `Future.get()`'s contract wraps every task failure in `ExecutionException` specifically
so the caller can distinguish "the task threw" from "waiting for the task threw" (an
`InterruptedException` on the caller's own thread).

## Cheat sheet

| Concept | Key fact |
|---|---|
| Poison pill | Sentinel `Runnable`, one per worker, identity-checked in the loop |
| `execute` | Fire-and-forget; blocks on `put` if queue full; throws after shutdown |
| `submit` | Wraps `Callable` + `MiniFuture`, returns `Future<T>` |
| `MiniFuture` state | `PENDING → COMPLETED/FAILED/CANCELLED`, exactly once |
| `get()` | `while (state == PENDING) wait()` — never `if`, spurious wakeup |
| Exception surfacing | Always `ExecutionException`, real cause in `getCause()` |
| `cancel(true)` | Only interrupts if `bindRunner` ran before cancellation raced it |
| Shutdown here | Graceful only (drains queue) — no `shutdownNow()` yet |

## Self-test

**Q1.** Why does the worker loop check `task == POISON_PILL` with `==` and not `.equals()`?

<details><summary>Answer</summary>

The poison pill is a single shared sentinel instance created once as a `static final` field.
Identity comparison is both sufficient (no other `Runnable` in the system is ever that exact
instance) and correct — `equals()` on an arbitrary lambda `Runnable` is reference equality anyway
since lambdas don't override it, but using `==` makes the intent explicit and avoids a null-check
subtlety if `equals` were ever overridden upstream.

</details>

**Q2.** What happens if `shutdown()` is called while the queue is completely full of real tasks
and uses `workQueue.add(POISON_PILL)`?

<details><summary>Answer</summary>

`add` on a full bounded queue throws `IllegalStateException` immediately (it does not block, unlike
`put`). `shutdown()` in this implementation would throw and leave some workers without a pill,
so they'd block on `take()` forever after draining the real tasks. A production-grade shutdown
would use `put` (accepting a possible block) or drain space first — this is a documented cost, not
silently fixed, and is exactly the kind of edge the real `ThreadPoolExecutor` avoids by using
run-state bits instead of a queue-occupying sentinel.

</details>

**Q3.** Two callers both call `future.cancel(true)` and `future.complete(x)` concurrently (one is
the worker finishing, one is a caller giving up). Which one wins, and why is that safe?

<details><summary>Answer</summary>

Whichever acquires the `lock` monitor first wins — both `cancel` and `complete` start with
`synchronized (lock)` and both check `state != State.PENDING` before mutating. The loser's branch
sees a non-`PENDING` state and returns/no-ops without touching `result` or `failure`. This is safe
because the check-then-act is atomic under the same monitor: there is no window where both could
observe `PENDING` and both proceed to mutate.

</details>

**Q4.** Why does `get()` need a `while` loop around `wait()` instead of a single `if` check?

<details><summary>Answer</summary>

The JLS permits spurious wakeup: `wait()` can return without any thread having called `notify` or
`notifyAll`. An `if` would let a spuriously-woken thread fall through and read a still-`PENDING`
`result`/`failure`, giving wrong or null data. The `while` re-checks the actual condition every
time the thread wakes, regardless of why it woke, which is the only construct the JLS's guarantee
makes safe.

</details>

**Q5.** Why does `submit` wrap the caller's `Callable` in a new `Runnable` rather than adapting
`MiniThreadPool` to accept `Callable` directly in its queue?

<details><summary>Answer</summary>

The queue's contract is `BlockingQueue<Runnable>` — a single homogeneous type keeps the worker
loop simple (one `run()` call, no type dispatch). The wrapper closure captures both the
`Callable` and the `MiniFuture`, so the worker loop never needs to know a `Future` exists; it just
runs a `Runnable` like any other task. This is the same pattern `FutureTask` uses: it *implements*
`Runnable` while wrapping a `Callable` internally.

</details>

**Q6.** What real bug does swallowing exceptions in v1's `execute` path (catch, log, continue) create
for a caller who used `submit` and is blocked in `get()`, if the underlying task throws?

<details><summary>Answer</summary>

Trick question for `submit` specifically: `submit`'s wrapper `Runnable` catches `Throwable` and
routes it into `completeExceptionally`, so it never reaches the worker loop's own catch-and-log —
the exception is fully captured and surfaced through the future. The v1 catch-and-log path only
matters for plain `execute` calls, where a thrown exception is genuinely lost with no receipt for
the caller to inspect.

</details>

**Q7.** Why is `runnerThread` declared `volatile` in `MiniFuture`?

<details><summary>Answer</summary>

`cancel(true)` reads `runnerThread` outside the `lock` monitor (after releasing it, to avoid
calling `interrupt()` while holding the future's lock) — that read happens on a different thread
than the write in `bindRunner`. Without `volatile`, there is no happens-before edge guaranteeing
the interrupting thread ever observes the written reference at all, and it could read a stale
`null` forever on some JMM-legal reordering.

</details>

**Q8.** In the domain usage example, why does calling `houseRevenueDelta.get(5, TimeUnit.SECONDS)`
from the main thread not block the pool's other workers from continuing to settle other stakes?

<details><summary>Answer</summary>

`get()` blocks only the calling thread on that specific `MiniFuture`'s monitor — it never touches
`workQueue` or any other worker's state. The pool's other seven `settlement-ingest-N` threads keep
pulling and running unrelated tasks from the shared queue entirely independently; blocking is a
property of the caller-future relationship, not the pool.

</details>

---

**Leaves covered:** 4.5.1–4.5.2 (2 leaves)
**Leaves deferred:** none
**Diagrams included:** D-206
**Target version:** Java 21 LTS
**Lines:** 578
