# 05 Multithreading and Concurrency — Hooks and thread factories — BUILD IT (§4.5, leaves 4.5.5–4.5.6)

**Target version: Java 21 LTS.** | **Part 4 of 5** | [Index](../00-index.md)
Previous: [Packed ctl and rejection](05b-packed-ctl-and-rejection.md) · Next: [Context propagation and completion](05d-context-propagation-and-completion.md)

---

`MiniThreadPool` so far: v1 is a fixed crew of workers pulling from a `BlockingQueue<Runnable>`,
each wrapping `task.run()` in a try/catch so one bad task can't kill its worker thread; v2 adds
`submit()` returning a hand-rolled `Future`. v3 packs run-state and worker count into one 32-bit
`ctl` so both can be read and CAS'd together; v4 adds `corePoolSize`/`maximumPoolSize`,
`keepAliveTime` for above-core workers, and four `RejectionPolicy` implementations for when both
the queue and max workers are exhausted. This file adds v5: lifecycle hooks around every task, and
a real `ThreadFactory` in place of `Executors.defaultThreadFactory()`.

## v5 — `beforeExecute` / `afterExecute` hooks

### Why it exists

`ThreadPoolExecutor` exposes two protected extension points — `beforeExecute(Thread, Runnable)`
and `afterExecute(Runnable, Throwable)` — that run around every task on the worker thread itself.
Without them, adding cross-cutting behaviour (timing every settlement task, logging which worker
ran what, resetting `ThreadLocal` state between tasks) means editing `Worker.run()` directly for
every new concern. Hooks let a subclass or a caller bolt behaviour on without touching the loop
that must stay correct.

### The mechanism

`Worker.run()` already isolates `task.run()` in its own try/catch so a thrown exception can't
propagate out of the loop and kill the thread (v1's whole point). The hooks slot into that same
try/catch: `beforeExecute` runs immediately before `task.run()`, and `afterExecute` runs in a
`finally`-equivalent position so it fires whether the task completed normally or threw.

```java
protected void beforeExecute(Thread worker, Runnable task) {
    // no-op by default — override or set a BiConsumer to observe every task start
}

protected void afterExecute(Runnable task, Throwable thrown) {
    // no-op by default — thrown is null on normal completion
}
```

`Worker.run()` becomes:

```java
public void run() {
    Runnable task = firstTask;
    firstTask = null;
    try {
        while (task != null || (task = getTask()) != null) {
            Throwable thrown = null;
            try {
                beforeExecute(thread, task);
                task.run();
            } catch (RuntimeException e) {
                thrown = e;
            } catch (Error e) {
                thrown = e;
                throw e; // Errors are not swallowed — see the Pitfall below
            } finally {
                try {
                    afterExecute(task, thrown);
                } catch (RuntimeException hookFailure) {
                    System.err.println(thread.getName() + " afterExecute hook failed: "
                        + hookFailure);
                }
                task = null;
            }
        }
    } finally {
        workers.remove(this);
        decrementWorkerCount();
    }
}
```

Two things earn their keep here. First, `afterExecute` is called from its own nested try/catch —
a badly written hook must not be able to do what a badly written task already can't: kill the
worker. Second, `Error` is deliberately rethrown after `afterExecute` runs, not swallowed by the
outer catch — `OutOfMemoryError` or `StackOverflowError` signal a JVM-level problem the pool has
no business hiding, unlike an ordinary `RuntimeException` from application code such as a failed
`FundsLedger.reserveStake` call.

### What happens without the try/catch — proved

Delete the try/catch around `task.run()` and feed the pool a settlement task that throws:

```java
BlockingQueue<Runnable> queue = new LinkedBlockingQueue<>(64);
MiniThreadPool brokenPool = new MiniThreadPool(2, 2, 0L, TimeUnit.NANOSECONDS, queue,
    new NamedThreadFactory("settlement-ingest"), new AbortPolicy());

brokenPool.execute(() -> {
    throw new LedgerImbalanceException("stake 4.20 split 0.42/3.78 does not sum to reservation");
});

Thread.sleep(200);
System.out.println("pool worker count after failing task: " + brokenPool.getPoolSize());
```

Without the try/catch, `task.run()` throws straight out of `Worker.run()`. Because `Worker`
implements `Runnable` and is handed to a raw `new Thread(worker).start()`, the uncaught exception
propagates all the way to the thread's `UncaughtExceptionHandler` (the JVM default: print a stack
trace to `System.err`), and the thread terminates — permanently. `getPoolSize()` immediately after
shows one fewer live worker than were started, and it never recovers: nothing re-adds a worker to
replace the one that died, because `Worker.run()`'s `finally` block — the block that calls
`workers.remove(this)` and `decrementWorkerCount()` — never runs either, since the exception
propagated *before* reaching that `finally`... except it did run, because `finally` always runs on
the way out. The pool's bookkeeping is consistent (`ctl`'s worker count drops correctly), but the
thread is gone and nothing spawns a replacement until the next `execute()` call notices
`workerCountOf(ctl.get()) < corePoolSize` and calls `addWorker`. Between the crash and that next
call, capacity is silently reduced — and if every core worker crashes in a burst (a bug shared
across settlement tasks), the pool can reach zero live workers while `execute()` keeps queuing
tasks nobody is left to drain, until the queue itself fills and starts rejecting.

**Interview:** "does a task throwing an exception kill the pool?" — no, but the naive answer stops
there. The precise answer: it kills *that worker thread*, not the pool, because
`ThreadPoolExecutor.runWorker` (and this `Worker.run()`) wraps every task individually; the pool
self-heals by lazily replacing the dead worker on the next submission that finds the count below
core, but there's a window where capacity is degraded and, for a hot core, that window is where
queued tasks back up.

**Pitfall:** assuming `afterExecute(task, thrown)` receiving a non-null `thrown` means the pool
"handled" the exception the way a top-level `try/catch` in caller code would — it did not. The
default `afterExecute` is a no-op; if nobody overrides it to log or alert, an exception thrown from
`execute()`-submitted work (as opposed to `submit()`, which stashes it in the `Future`) is reported
only via `System.err` inside the wrapping catch above, with no return value or exception ever
reaching whoever called `execute()`. Silent task failure is the default for fire-and-forget
submission, hooks or not — `submit()` is the escape hatch precisely because it surfaces the
`Throwable` when the caller calls `Future.get()`.

**Insight:** the reason `beforeExecute`/`afterExecute` live on the pool rather than being wrapped
around each `Runnable` at submission time is thread identity — `beforeExecute` receives the actual
worker `Thread`, letting an override rename it per-task (`Thread.currentThread().setName(...)`) or
read/clear a `ThreadLocal` that's scoped to the worker rather than the task, something a decorator
around the `Runnable` itself cannot see.

> `beforeExecute`/`afterExecute` are worker-thread-side extension points invoked immediately before
> and after every task, isolated from the task's own exception handling so a broken hook — like a
> broken task — cannot terminate the thread that runs it.

## A `ThreadFactory` with named threads, daemon flag, and an uncaught-exception handler

### Why it exists

`Executors.defaultThreadFactory()` produces threads named `pool-N-thread-M` — useless in a
`jstack` dump when three pools are running and a thread is stuck. Production pools always supply a
custom `ThreadFactory` for three things a default factory doesn't give you: a recognisable name
prefix, an explicit daemon/non-daemon choice, and an `UncaughtExceptionHandler` that fires for
whatever *does* still manage to escape a worker (an `Error`, or any exception thrown outside the
`beforeExecute`/`task.run()`/`afterExecute` sandwich, such as inside `Worker.run()`'s own
bookkeeping).

```java
public final class NamedThreadFactory implements ThreadFactory {

    private final String namePrefix;
    private final boolean daemon;
    private final Thread.UncaughtExceptionHandler exceptionHandler;
    private final AtomicInteger sequence = new AtomicInteger(1);

    public NamedThreadFactory(String namePrefix) {
        this(namePrefix, false, NamedThreadFactory::logUncaught);
    }

    public NamedThreadFactory(String namePrefix, boolean daemon,
                               Thread.UncaughtExceptionHandler exceptionHandler) {
        this.namePrefix = Objects.requireNonNull(namePrefix, "namePrefix");
        this.daemon = daemon;
        this.exceptionHandler = Objects.requireNonNull(exceptionHandler, "exceptionHandler");
    }

    @Override
    public Thread newThread(Runnable r) {
        Thread thread = new Thread(r, namePrefix + "-" + sequence.getAndIncrement());
        thread.setDaemon(daemon);
        thread.setUncaughtExceptionHandler(exceptionHandler);
        // Priority is deliberately left at Thread.NORM_PRIORITY — see the gotcha below.
        return thread;
    }

    private static void logUncaught(Thread thread, Throwable thrown) {
        System.err.println("[" + thread.getName() + "] uncaught: " + thrown);
    }
}
```

Wired into the settlement pool:

```java
ThreadFactory settlementThreads = new NamedThreadFactory("settlement-ingest", false,
    (thread, thrown) -> System.err.println(
        thread.getName() + " crashed handling a stake settlement: " + thrown));

MiniThreadPool settlementPool = new MiniThreadPool(
    8, 24, 60L, TimeUnit.SECONDS,
    new LinkedBlockingQueue<>(2_000),
    settlementThreads,
    new AbortPolicy());
```

Threads created this way are named `settlement-ingest-1`, `settlement-ingest-2`, …,
`settlement-ingest-N` — exactly what shows up in a `jstack` dump or a profiler's thread list when
diagnosing which pool a stuck thread belongs to during a 3,400/sec settlement burst.

### The gotcha

`AtomicInteger sequence` must be a field on the *factory*, not on the pool or a `static` shared
across factories — each `NamedThreadFactory` instance owns its own numbering, so two pools built
with two separate `NamedThreadFactory("settlement-ingest")` calls both start at `-1` and collide on
names. A single factory instance handed to one pool, as above, is what keeps numbering monotonic
and gap-free for that pool's whole lifetime (workers that retire via `keepAliveTime` don't recycle
their number — a new worker started later gets the next sequence value, not the dead one's).

**Pitfall:** setting `daemon = true` on a pool that runs financial work is a common
copy-paste mistake — daemon threads are killed mid-task the instant the JVM decides no non-daemon
thread is left running, with no chance for `afterExecute`, no chance for a `finally` block in the
task, nothing. A settlement task blocked inside `FundsLedger.reserveStake` when the last
non-daemon thread exits is simply abandoned, potentially after having reserved funds but before
recording the reservation — exactly the kind of half-done state `LedgerImbalanceException` exists
to catch, except nothing raises it because the thread never gets to the `catch` block. Worker
pools that do real work should be non-daemon and shut down explicitly; daemon is for
best-effort background chores (a metrics flusher) where losing the last unit of work at JVM exit
is acceptable.

**Interview:** "why would you ever write a custom `ThreadFactory`?" — the honest three reasons, in
order of how often they come up: naming for diagnosability, an explicit `UncaughtExceptionHandler`
so failures aren't only visible via `System.err`, and controlling daemon status so pool threads
don't either leak the JVM open forever or get killed mid-transaction.

> A `ThreadFactory` is the single seam `ThreadPoolExecutor` (and `MiniThreadPool`) exposes for
> controlling how its worker threads are constructed — name, daemon status, priority, thread
> group, and uncaught-exception handling — without touching the pool's submission or scheduling
> logic at all.

---

## Pitfalls

### Assuming a thrown task exception kills the whole pool

**Wrong**

```java
executor.execute(() -> { throw new LedgerImbalanceException("stake split mismatch"); });
// "the pool is probably dead now, better restart it"
executor.shutdown();
executor = Executors.newFixedThreadPool(8, settlementThreads);
```

**Right**

```java
executor.execute(() -> { throw new LedgerImbalanceException("stake split mismatch"); });
// the pool is fine — only that one worker thread died and was silently replaced
// on the next submission; verify with getPoolSize()/getActiveCount(), don't restart
```

**Why people believe it:** an uncaught exception from a plain `Runnable` run directly (not inside a
pool) does bring down that thread and, if it's the main thread, the whole program looks "dead" —
so the instinct transfers, incorrectly, to pool-submitted work where each task's thread is isolated
and disposable by design.

### Assuming `afterExecute`'s `thrown` parameter is non-null only for `execute()`-submitted Errors

**Wrong**

```java
protected void afterExecute(Runnable task, Throwable thrown) {
    if (thrown != null) alertOnCall(thrown); // "only fires for execute(), submit() catches its own"
}
```

**Right**

```java
protected void afterExecute(Runnable task, Throwable thrown) {
    // fires for BOTH execute() and submit()-wrapped tasks that threw — a FutureTask-wrapping
    // Runnable still runs task.run() inside the same try/catch, it just also stashes the
    // exception for Future.get() to rethrow later. Handle both, or filter explicitly:
    if (thrown != null) {
        alertOnCall(thrown);
    } else if (task instanceof MiniFuture<?> future && future.isCompletedExceptionally()) {
        alertOnCall(future.exceptionNow());
    }
}
```

**Why people believe it:** `submit()`'s `Future.get()` rethrowing the exception feels like "the
exception was handled there," so it's easy to assume `afterExecute` never sees it — but the hook
runs at the worker-thread level around `task.run()` regardless of whether that `Runnable` happens
to be a plain lambda or a `Future`-wrapping adapter; the wrapping only changes what happens to the
`Throwable` afterward, not whether the hook observes the task completing.

## Cheat sheet

| Extension point | Runs where | Runs when | Can it kill the worker? | Default behaviour |
|---|---|---|---|---|
| `beforeExecute(thread, task)` | worker thread, before `task.run()` | every task | a thrown `RuntimeException` here is caught alongside the task's own | no-op |
| `afterExecute(task, thrown)` | worker thread, after `task.run()` | every task, success or failure | wrapped in its own try/catch | no-op |
| `ThreadFactory.newThread(r)` | pool thread creation | once per worker, on `addWorker` | n/a — runs before the worker loop starts | `Executors.defaultThreadFactory()` |
| `UncaughtExceptionHandler` | JVM's uncaught-exception path | only for exceptions that escape the worker's own try/catch entirely | already terminal — thread is exiting | print stack trace to `System.err` |
| task's own `RuntimeException` | inside worker's try/catch around `task.run()` | per task | no — caught, worker continues | logged, swallowed for `execute()`; captured for `Future` on `submit()` |
| task's own `Error` | inside worker's try/catch, rethrown after `afterExecute` | per task | yes — deliberately, propagates to `UncaughtExceptionHandler` | thread dies, pool self-heals lazily |

## Self-test

**Q1.** A task submitted via `pool.execute(task)` throws a `RuntimeException`. What happens to the
worker thread that ran it, and what happens to the pool overall?

<details><summary>Answer</summary>

The worker thread survives — `Worker.run()`'s try/catch around `task.run()` catches the
`RuntimeException`, logs it, and the `while` loop continues to `getTask()` for the next task. The
pool overall is unaffected: worker count, `ctl`, and the queue are untouched. Nothing about the
pool's state changes because of the failed task; only that one submission's work is lost (silently,
for `execute()` — surfaced via `Future.get()` for `submit()`).

</details>

**Q2.** Why does `Worker.run()` rethrow `Error` after calling `afterExecute`, instead of catching
and swallowing it the same way it does `RuntimeException`?

<details><summary>Answer</summary>

An `Error` (like `OutOfMemoryError` or `StackOverflowError`) signals the JVM itself is in trouble,
not that application code made a recoverable mistake. Swallowing it would let the worker loop
continue trying to process more tasks in a JVM that may already be unable to allocate memory or
grow the stack, likely producing a worse failure later with less diagnostic information. Rethrowing
lets the thread die and its `UncaughtExceptionHandler` report the real problem immediately.

</details>

**Q3.** Two pools are each built with their own `new NamedThreadFactory("settlement-ingest")`.
What thread names does each pool produce, and why doesn't the second pool continue numbering from
where the first left off?

<details><summary>Answer</summary>

Both pools' threads are named `settlement-ingest-1`, `settlement-ingest-2`, … starting from 1,
because each `NamedThreadFactory` instance owns its own `AtomicInteger sequence` field — it is not
static or shared. The two factories are entirely separate objects with independently initialized
counters, so there is naming overlap across the two pools (both have a thread named
`settlement-ingest-1`) even though within each single pool the names are unique and monotonic.

</details>

**Q4.** Why should the settlement pool's `ThreadFactory` set `daemon = false`, and what specifically
goes wrong if it's set to `true`?

<details><summary>Answer</summary>

Daemon threads are terminated by the JVM the instant no non-daemon thread remains running, with no
guarantee any in-flight task reaches a stopping point — no `finally` block, no `afterExecute` hook,
nothing. A settlement task killed mid-`FundsLedger.reserveStake` call could leave funds reserved
without the corresponding ledger entry recorded, which is exactly the double-entry imbalance
`LedgerImbalanceException` exists to prevent, except no exception is ever thrown because the thread
is simply gone. Non-daemon threads keep the JVM alive until `shutdown()` is called and drains
properly.

</details>

**Q5.** What does `beforeExecute` receive that a decorator wrapped around the submitted `Runnable`
at submission time cannot see, and why does that matter?

<details><summary>Answer</summary>

`beforeExecute(Thread worker, Runnable task)` receives the actual worker `Thread` object executing
the task. A decorator wrapped around the `Runnable` before submission only ever sees the task
itself — it has no reference to whichever worker thread eventually picks it up, since that
assignment happens later, inside the pool. This matters for anything scoped to the *thread* rather
than the *task*: renaming the thread per-task for diagnostics, or reading/clearing a `ThreadLocal`
that's meant to be worker-scoped rather than submission-scoped.

</details>

**Q6.** If `afterExecute` itself throws a `RuntimeException`, what happens to the worker thread?

<details><summary>Answer</summary>

Nothing fatal — `afterExecute` is called from inside its own nested try/catch in `Worker.run()`,
so a broken hook is treated the same way a broken task is: the exception is logged and swallowed,
`task` is set to `null`, and the outer `while` loop proceeds to `getTask()` for the next task. A
misbehaving hook, like a misbehaving task, cannot terminate the worker.

</details>

**Q7.** Why is `sequence` on `NamedThreadFactory` an `AtomicInteger` rather than a plain `int`?

<details><summary>Answer</summary>

`newThread` can be called from multiple threads concurrently — `addWorker` is invoked from any
caller thread racing to submit work during a burst, and multiple `addWorker` calls can be in
flight at once when the pool is ramping up toward `maximumPoolSize`. A plain `int++` is a
read-modify-write with no atomicity guarantee, so two concurrent `newThread` calls could both read
the same value and produce two threads with the identical name. `AtomicInteger.getAndIncrement()`
makes the read-and-bump a single atomic step.

</details>

---

**Leaves covered:** 4.5.5–4.5.6 (2 leaves)
**Leaves deferred:** none
**Diagrams included:** none
**Target version:** Java 21 LTS
**Lines:** 408
