# 05 Multithreading and Concurrency — The pool consolidated diff — BUILD IT (§4.5, leaf 4.5.9)

**Target version: Java 21 LTS.** | **Part 4 of 5** | [Index](../00-index.md)
Previous: [Context propagation and completion](05d-context-propagation-and-completion.md) · Next: [The work-stealing deque](06-work-stealing-deque.md)

---

Across `05-a-thread-pool-from-scratch.md` through `05d-context-propagation-and-completion.md`,
`MiniThreadPool` grew from v1 (fixed workers over a `BlockingQueue`) through v5 (hooks and a named
`ThreadFactory`) into something that behaves like `ThreadPoolExecutor` for the cases this note set
exercised: submission, core/max sizing, `keepAliveTime`, rejection, hooks, context propagation, and
completion ordering. What it deliberately never built is the subject of this file — the mechanisms
`ThreadPoolExecutor` carries for correctness under adversarial conditions, monitoring at scale, and
graceful shutdown that a teaching pool has no pressure to earn.

## The consolidated diff

| Mechanism | `MiniThreadPool` (this note set) | `java.util.concurrent.ThreadPoolExecutor` | Why the real one needs it |
|---|---|---|---|
| **`Worker` as its own lock (AQS trick)** | `Worker` is a plain `Runnable`; no lock semantics of its own | `Worker` extends `AbstractQueuedSynchronizer` and implements `Runnable`, using AQS's exclusive-acquire state as a per-worker "is this thread currently running a task" flag | Interrupt safety during `shutdown()`. `interruptIdleWorkers()` must interrupt only workers that are *idle*, waiting on `workQueue.take()`, never one mid-task — interrupting a worker while it's inside `task.run()` could corrupt whatever the task was doing (e.g. abort a `FundsLedger.reserveStake` call partway through). `Worker` implementing AQS lets `runWorker` call `w.lock()` (acquire) around each task and `tryLock()` from `interruptIdleWorkers()` — a worker that's mid-task holds the lock, so `tryLock()` fails and that worker is skipped |
| **`interruptIdleWorkers()`** | not implemented — `shutdown()` (where present) would need to interrupt every worker indiscriminately | selectively interrupts only workers not currently holding their own AQS lock, i.e. only ones blocked in `getTask()`'s `take()`/`poll()` | Lets `getTask()`'s blocked workers wake up and notice the new run state without disturbing workers actively running a task — the difference between graceful and destructive shutdown |
| **Double-check after enqueue** | `execute()` re-reads `ctl` after a successful `workQueue.offer(task)` and calls `addWorker(null, false)` if `workerCountOf(recheck) == 0` (built in v3/v4) | identical structure — `ThreadPoolExecutor.execute()`'s step 2 performs the same re-check | Between the `offer` succeeding and any worker existing to drain it, every worker could have retired via `keepAliveTime` or a concurrent `shutdown()` — without the re-check, a queued task could sit forever with nobody polling |
| **`purge()`** | not implemented | removes cancelled `Future`s from the work queue proactively, since a `FutureTask` whose `cancel()` was called still occupies a queue slot until polled | Prevents unbounded queue growth in a workload that submits-then-cancels heavily — e.g. speculative settlement retries superseded before they run |
| **`remove(Runnable)`** | not implemented | removes a specific not-yet-started task from the queue directly | Lets a caller retract one submission (a settlement task for a stake that was voided before its turn) without waiting for `purge()`'s cancelled-future sweep |
| **`DelayedWorkQueue`** (used by `ScheduledThreadPoolExecutor`) | `MiniThreadPool` uses a plain `BlockingQueue<Runnable>`, no delay semantics at all | a binary-heap-backed queue ordering `ScheduledFutureTask`s by trigger time, with a dedicated "leader" thread optimization (`leader` field on the queue) so only one waiting thread pays the full timed-park cost while others wait on a plain `Condition.await()` | Needed only when the pool is also a *scheduler* — one-shot and periodic delayed execution — which is out of `MiniThreadPool`'s scope; §4.5 built a work queue, not a delay queue |
| **`allowCoreThreadTimeOut`** | not implemented — `corePoolSize` workers always `workQueue.take()` (block forever), never time out | a boolean flag that, when set, makes *core* workers use the same `poll(keepAliveTime, ...)` path above-core workers already use, so even core workers can retire during idle periods | Lets a pool shrink to zero threads entirely during quiet periods (overnight, between settlement bursts) rather than always parking `corePoolSize` threads doing nothing |
| **`prestartCoreThread()` / `prestartAllCoreThreads()`** | not implemented — workers are created lazily, one per `execute()` call, up to `corePoolSize` | eagerly creates and starts core workers before any task arrives, so the pool is "warm" the instant the first task is submitted | Avoids the first burst of traffic (e.g. the opening seconds of a settlement window) paying thread-creation latency on the critical path; useful specifically when start-up cost matters more than deferred resource use |
| **Monitoring surface** (`getPoolSize`, `getActiveCount`, `getLargestPoolSize`, `getTaskCount`, `getCompletedTaskCount`, `getQueue()`) | only what was needed for the proofs in this note set (`getPoolSize()` was invoked in `05c`) | a full read-only accounting API: current/active/largest-ever worker counts, and *approximate* lifetime task counts read via a volatile snapshot, explicitly documented as best-effort under concurrent modification | Operability — a dashboard tracking the settlement pool's saturation (`getActiveCount()` vs `getMaximumPoolSize()`) or largest-ever burst size (`getLargestPoolSize()`) needs these without stopping the pool to inspect it |
| **Termination protocol (`SHUTDOWN` → `STOP` → `TIDYING` → `TERMINATED`)** | `MiniThreadPool`'s `ctl` packing (built in v3) has `RUNNING`, `SHUTDOWN`, `STOP`, `TERMINATED` — no `TIDYING` | a fifth state, `TIDYING`, sits between the last worker exiting and `TERMINATED`: exactly one thread CASes into `TIDYING`, calls the overridable `terminated()` hook, then CASes to `TERMINATED`, and `awaitTermination()`/`isTerminated()` only report true after that hook has run | `TIDYING` guarantees `terminated()` — a hook for releasing pool-wide resources (closing a metrics registry, deregistering from a JMX bean) — runs exactly once, by exactly one thread, strictly after every worker has fully exited, never racing another worker's own cleanup |
| **`RejectedExecutionException` after shutdown** | `AbortPolicy` (built in v4) throws this from `execute()`'s reject path whenever `addWorker` fails or the queue rejects, including post-shutdown | identical semantics — any `execute()` call after `shutdown()`/`shutdownNow()` either silently queues (if still draining and space exists) or is rejected through the configured `RejectedExecutionHandler` | `MiniThreadPool` already matches this behaviour; listed here for completeness of the diff rather than as a gap |

### The `Worker`-as-AQS trick, walked

The one entry above that's genuinely surprising on first read deserves the walk-through the table
can't fit. `ThreadPoolExecutor.Worker` declares:

```java
private final class Worker
    extends AbstractQueuedSynchronizer
    implements Runnable {

    Worker(Runnable firstTask) {
        setState(-1); // inhibit interrupts until runWorker() calls unlock() below
        this.firstTask = firstTask;
        this.thread = getThreadFactory().newThread(this);
    }

    protected boolean isHeldExclusively() { return getState() != 0; }

    protected boolean tryAcquire(int unused) {
        if (compareAndSetState(0, 1)) {
            setExclusiveOwnerThread(Thread.currentThread());
            return true;
        }
        return false;
    }

    protected boolean tryRelease(int unused) {
        setExclusiveOwnerThread(null);
        setState(0);
        return true;
    }

    void lock()  { acquire(1); }
    boolean tryLock() { return tryAcquire(1); }
    void unlock() { release(1); }
    boolean isLocked() { return isHeldExclusively(); }
}
```

`Worker` doesn't protect any shared *data* the way a normal AQS-based lock does — there's no
critical section of memory it's guarding. It's repurposing AQS purely as an **interruptibility
flag with atomic test-and-set semantics**: `lock()` (acquire) is called by `runWorker` around each
task, meaning "this worker is currently busy, don't interrupt me for shutdown purposes right now."
`tryLock()` (non-blocking `tryAcquire`) is what `interruptIdleWorkers()` calls on every worker in
the pool: if `tryLock()` succeeds, this worker was idle (unlocked) and is now safely lockable, so
`interruptIdleWorkers()` interrupts its thread and then unlocks it again; if `tryLock()` fails, the
worker is mid-task and is skipped entirely. `setState(-1)` in the constructor is a small but
deliberate detail: state `0` means "unlocked, interruptible," state `1` means "locked, busy," and
state `-1` is neither — it's a third value specifically chosen so `tryAcquire(1)` (which only
succeeds against state `0`) cannot succeed until `runWorker()` calls `unlock()` once at start-up,
preventing a race where a `shutdown()` racing the very first `newThread()` call could interrupt a
worker before it's even begun its loop.

**Insight:** this is the reason `ThreadPoolExecutor` doesn't just use a plain `boolean busy` flag
guarded by `synchronized` for the same purpose — AQS gives it CAS-based `tryAcquire` for free,
meaning `interruptIdleWorkers()` scanning every worker in the pool never blocks waiting for a
worker's own monitor; a `synchronized` flag would force the interrupting thread to either block on
a busy worker's lock or accept a `synchronized` block granular enough to race, whereas
`tryAcquire`'s non-blocking CAS either succeeds instantly or fails instantly with no waiting either
way.

**Interview:** "why does `ThreadPoolExecutor.Worker` extend `AbstractQueuedSynchronizer`?" — the
one-line answer that actually lands: not to protect data, but to get a lock-free, non-reentrant,
interruptible "is this worker currently running a task" flag, so `shutdown()` can interrupt exactly
the idle workers and never one mid-task, without ever blocking the thread doing the interrupting.

**Pitfall:** assuming `Worker`'s lock is reentrant, the way `ReentrantLock` is — it deliberately
isn't. `tryAcquire` always starts from `compareAndSetState(0, 1)`, with no check for
"does the current thread already hold this." A worker calling `w.lock()` twice without an
intervening `unlock()` would simply deadlock against itself; `runWorker`'s single lock/unlock pair
per task is written knowing that, and no code path ever tries to re-acquire.

### What a production pool needs that a teaching pool omits

`MiniThreadPool` proved every mechanism above by building it, which is the point of a teaching
pool — but production-grade would additionally need, at minimum: **graceful drain with a bounded
wait** (`awaitTermination(timeout, unit)` with a real deadline, not an unbounded block); **backpressure
signalling upstream** rather than an unbounded queue silently growing (`ApplicationGateway` needs
to know the settlement pool is saturated *before* `1,200 stake reservations/sec` peak arrives, not
after `AbortPolicy` starts throwing); **per-pool metrics wired to the monitoring stack**
(`getActiveCount()`/`getQueue().size()` exported as gauges, not just available via a getter);
**a `terminated()` override** that actually releases whatever pool-scoped resources exist (closing
a `MeterRegistry` binding, deregistering an MBean); and **exhaustive testing of the rejection path
under real load**, since `AbortPolicy` throwing `RejectedExecutionException` for the stake-settlement
pool is a `LedgerImbalanceException`-adjacent event that needs an alert, not a stack trace nobody
reads.

---

## Pitfalls

### Assuming `Worker.lock()` protects the task's own data

**Wrong**

```java
// "Worker extends AQS, so surely locking it protects the task's fields from concurrent access"
worker.lock();
sharedSettlementBuffer.append(result); // still needs its own synchronization — AQS state here
worker.unlock();                        // has nothing to do with sharedSettlementBuffer's safety
```

**Right**

```java
// Worker's AQS state is purely an interruptibility flag for shutdown bookkeeping.
// Data shared across tasks/threads still needs its own lock, regardless of Worker's state.
synchronized (sharedSettlementBuffer) {
    sharedSettlementBuffer.append(result);
}
```

**Why people believe it:** seeing `extends AbstractQueuedSynchronizer` on a class triggers the
reflex "this class protects some shared state," which is true for every other AQS-based class in
`java.util.concurrent` (`ReentrantLock`, `Semaphore`, `CountDownLatch`) but not here — `Worker`'s
only use of AQS is as an atomic interruptibility flag, with zero data behind it.

### Assuming `interruptIdleWorkers()` interrupts every worker unconditionally

**Wrong**

```java
private void interruptIdleWorkersNaively() {
    for (Worker w : workers) {
        w.thread.interrupt(); // interrupts workers mid-task too — corrupts in-flight work
    }
}
```

**Right**

```java
private void interruptIdleWorkers() {
    for (Worker w : workers) {
        if (w.tryLock()) {           // only succeeds if the worker is currently idle
            try {
                w.thread.interrupt();
            } finally {
                w.unlock();
            }
        }
    }
}
```

**Why people believe it:** "interrupt idle workers" sounds like it should just mean "interrupt the
workers," and it's easy to skip the `tryLock()` gate as an unnecessary complication rather than the
entire mechanism that makes the method's name true.

## Cheat sheet

| If you need... | Reach for |
|---|---|
| Interrupt-safe selective shutdown of idle-only workers | `Worker`-as-AQS + `interruptIdleWorkers()` |
| Guaranteed-once cleanup after the last worker exits | the `TIDYING` state + `terminated()` hook |
| Delayed / periodic task ordering | `DelayedWorkQueue`, not a plain `BlockingQueue` |
| A pool that shrinks to zero threads when idle | `allowCoreThreadTimeOut(true)` |
| Zero cold-start latency on the first burst | `prestartCoreThread()` / `prestartAllCoreThreads()` |
| Retracting a specific not-yet-run task | `remove(Runnable)` |
| Sweeping cancelled-but-still-queued futures | `purge()` |
| Live saturation visibility | `getActiveCount()`, `getPoolSize()`, `getQueue().size()`, `getLargestPoolSize()` |
| Rejecting after shutdown vs. mid-shutdown draining | `RejectedExecutionException` via the configured handler — `MiniThreadPool` already matches this |

## Self-test

**Q1.** Why does `ThreadPoolExecutor.Worker` extend `AbstractQueuedSynchronizer` when it has no
shared data to protect?

<details><summary>Answer</summary>

It repurposes AQS's atomic, non-blocking `tryAcquire`/`tryRelease` machinery purely as an
interruptibility flag: `lock()` marks a worker "busy" around each task, and `tryLock()` — called by
`interruptIdleWorkers()` — succeeds only against an idle (unlocked) worker, letting shutdown
interrupt exactly the workers safely blocked in `getTask()` and skip any worker mid-task, all
without the interrupting thread ever blocking.

</details>

**Q2.** Why is `Worker`'s lock deliberately non-reentrant, unlike `ReentrantLock`?

<details><summary>Answer</summary>

`tryAcquire` always starts from `compareAndSetState(0, 1)` with no check for "does the current
thread already hold this" — there is exactly one lock/unlock pair per task in `runWorker`, and
nothing in the design ever needs a worker to re-acquire its own lock while already holding it.
Adding reentrancy would only add complexity for a case that never occurs, and a naive re-lock
attempt would simply deadlock the worker against itself, which the design accepts as fine since it
never happens.

</details>

**Q3.** What does `setState(-1)` in `Worker`'s constructor prevent?

<details><summary>Answer</summary>

It prevents a race between a `shutdown()` call and a brand-new worker thread that hasn't started
running yet. State `0` means unlocked/interruptible and state `1` means locked/busy; `-1` is a
third value that `tryAcquire(1)` (which only succeeds against state `0`) cannot acquire, so the
worker is neither "idle" nor "busy" until `runWorker()` explicitly calls `unlock()` once at
start-up — closing the window where a concurrent shutdown could interrupt a worker thread before
its run loop has even begun.

</details>

**Q4.** What guarantee does the `TIDYING` state provide that `SHUTDOWN`/`STOP`/`TERMINATED` alone
would not?

<details><summary>Answer</summary>

It guarantees the `terminated()` cleanup hook runs exactly once, by exactly one thread, strictly
after every worker has fully exited. Without a distinct `TIDYING` state, multiple workers finishing
around the same time could race to be "the one" that runs cleanup, or `terminated()` could run
before every worker has actually stopped; `TIDYING` is a dedicated CAS-guarded waypoint exactly one
thread transitions into before calling the hook and then moving on to `TERMINATED`.

</details>

**Q5.** Why does `ScheduledThreadPoolExecutor` need `DelayedWorkQueue` instead of the plain
`BlockingQueue<Runnable>` `MiniThreadPool` uses?

<details><summary>Answer</summary>

A scheduler's queue must order tasks by trigger time, not by arrival (FIFO) order, so it needs a
priority structure — `DelayedWorkQueue` is backed by a binary heap keyed on each
`ScheduledFutureTask`'s next execution time, plus a "leader" thread optimization so only one
waiting thread pays the full timed-park cost while others wait on a plain condition. A plain FIFO
`BlockingQueue` has no notion of "not yet due" at all.

</details>

**Q6.** What's the practical effect of `allowCoreThreadTimeOut(true)` on a pool during a quiet
period, and what does `MiniThreadPool` do instead?

<details><summary>Answer</summary>

With the flag set, even the `corePoolSize` workers use the timed `poll(keepAliveTime, ...)` path
instead of blocking forever on `take()`, so the pool can shrink all the way to zero live threads
when there's no work — useful overnight or between settlement bursts. `MiniThreadPool` as built
never enables this: its core workers always call `workQueue.take()`, so `corePoolSize` threads
remain parked indefinitely even with an empty queue.

</details>

**Q7.** Why would `prestartAllCoreThreads()` matter specifically for a burst-shaped workload like
the settlement pool's `3,400 settlements/sec` peaks?

<details><summary>Answer</summary>

Without prestarting, the first `corePoolSize` tasks submitted after a quiet period each pay the
cost of `addWorker` creating and starting a brand-new thread on the critical path of that
submission. If the settlement burst's opening moment is exactly when thread-creation latency is
least tolerable, prestarting all core threads before the burst arrives means every core worker is
already parked on `workQueue.take()`, ready to pick up work with zero creation latency.

</details>

**Q8.** Name two things a production version of `MiniThreadPool` needs that were out of scope for
this note set, and why each matters.

<details><summary>Answer</summary>

Any two of: a bounded `awaitTermination(timeout, unit)` for graceful shutdown rather than an
unbounded wait, so a stuck task can't block the entire shutdown sequence forever; upstream
backpressure signalling so `ApplicationGateway` learns the settlement pool is saturated before
`AbortPolicy` starts throwing, rather than discovering it via a wave of
`RejectedExecutionException`s; live metrics (active count, queue depth) wired to the monitoring
stack rather than merely available via a getter someone has to remember to poll; or a `terminated()`
override that actually releases pool-scoped resources like a metrics registry binding.

</details>

---

**Leaves covered:** 4.5.9 (1 leaf)
**Leaves deferred:** none
**Diagrams included:** none
**Target version:** Java 21 LTS
**Lines:** 309
