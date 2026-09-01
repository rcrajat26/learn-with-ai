# 05 Multithreading and Concurrency — The fork/join consolidated diff — BUILD IT (§4.6, leaf 4.6.7)

**Target version: Java 21 LTS.** | **Part 4 of 5** | [Index](../00-index.md)
Previous: [Recursive tasks and tuning](06c-recursive-tasks-and-tuning.md) · Next: [Structured concurrency from scratch](07-structured-concurrency-from-scratch.md)

Files 1–3 built `GrowableWorkStealingDeque<T>`, `MiniForkJoinPool`, and `MiniRecursiveTask<V>` —
per-worker Chase-Lev deques, randomised stealing, and help-by-executing joins. This file is the
diff against the real `java.util.concurrent.ForkJoinPool`: everything the teaching version leaves
out, and why each omission is the correct call for a teaching pool but not for a production one.

### Diff table: `MiniForkJoinPool` vs `ForkJoinPool`

| Concern | `MiniForkJoinPool` (this build) | Real `ForkJoinPool` | Why the real one needs it |
|---|---|---|---|
| Control state | `AtomicBoolean shutdown` + `AtomicInteger idleCount`, two separate fields | one packed 64-bit `ctl` field: active-thread count, total-thread count, a Treiber-stack pointer to the top idle worker, and a version-stamp all bit-sliced together, updated with a single CAS | one field means one CAS commits "wake a parked worker and update both thread counts" atomically; two separate fields (as this build has) can't be updated together without a lock or a wider race window than the real pool tolerates at scale |
| Idle worker wakeup | `LockSupport.parkNanos` fixed interval, no explicit wake | idle workers push themselves onto a lock-free Treiber stack encoded in `ctl`; a worker that publishes new work pops and unparks exactly one idle worker directly | targeted unpark avoids waking every idle worker on every new task (a "thundering herd") when only one of them is needed |
| Blocking inside `compute()` | not supported — the pitfall notes this explicitly; a worker blocked on I/O is a lost core with no recovery | `ManagedBlocker` interface: a task that must block declares it via `ForkJoinPool.managedBlock(blocker)`, and the pool **compensates** by temporarily starting an extra worker thread so blocking a compute thread doesn't shrink the effective pool | real workloads occasionally must block (e.g. a `CardPayments` PSP call issued from inside a fork/join task); compensation is what makes that survivable instead of a silent throughput cliff |
| Compensation accounting | none | tracked in `ctl`'s thread-count bits; compensating threads are bounded and reclaimed once the block ends, avoiding unbounded thread growth | uncontrolled compensation would let a burst of blocking tasks spawn unbounded OS threads, defeating the point of a fixed-size pool |
| Task completion style | single-shot `MiniRecursiveTask<V>`: exactly one `compute()`, one result, one set of joiners | `RecursiveTask`/`RecursiveAction` (this build's shape) **and** `CountedCompleter`: a completion-driven style where a task explicitly calls `tryComplete()`/`onCompletion()` and a parent only fires once all children have checked in, without any thread ever blocking in `join()` at all | `CountedCompleter` avoids the `join()` wait/help-loop entirely for workloads structured as a fan-out/fan-in DAG rather than strict left-recurse-then-join-right trees, which matters when join depth would otherwise be large |
| Submission path | `submit(task, workerIndex)` — caller picks a target deque directly, always a worker deque | separate **submission queues** distinct from **worker queues**: external (non-worker) callers push into a small set of submission queues; only workers push/pop/steal on worker queues | separating the two avoids external threads directly contending on the same deques workers steal from, and lets the pool apply different admission/backpressure policy to external submissions |
| Helping a stuck join | `helpUntilDone()`: drain own deque, then random-steal, then a bounded `wait(1)` | `helpJoin()`: walks the actual dependency chain — if task A joins task B, and B is itself unforked or stealable, the joining worker preferentially executes tasks that unblock *this specific join* rather than any random available task | targeted helping resolves the exact dependency faster under contention than helping with arbitrary unrelated work, and also lets the pool detect true deadlock-shaped cycles rather than just spinning |
| Common pool | none — every `MiniForkJoinPool` is explicitly constructed | `ForkJoinPool.commonPool()`: a shared, lazily-initialized, JVM-wide pool sized to `availableProcessors() - 1`, backing `Stream.parallel()`, `CompletableFuture`'s async stages with no explicit executor, and `Arrays.parallelSort` | gives every unrelated part of an application a shared, reasonably-sized default instead of each library silently spinning up its own pool |
| Worker thread identity | `Thread`, plain, named `ledger-reconcile-N` | `ForkJoinWorkerThread`, a `Thread` subclass carrying its own `WorkQueue`; a separate `InnocuousForkJoinWorkerThread` variant strips the thread's context `ClassLoader`, thread-local state, and permissions for use inside the common pool specifically, since common-pool tasks may come from code the pool itself doesn't fully trust | isolating the common pool's worker identity limits what a task running on a shared, JVM-wide pool can observe or corrupt via thread-locals or class-loader tricks left over from an unrelated caller |
| Exception handling | `volatile RuntimeException failure`, rethrown synchronously from `join()` on the joining thread | same idea, but exceptions are captured per-task and rethrown wrapped in the *joining* thread's own stack trace context on every `join()`/`get()` call, with cancellation propagated to sibling/child tasks via `completeExceptionally` semantics on `CountedCompleter` chains | rethrowing with the joiner's own stack context (rather than just re-throwing the worker's original exception object) keeps stack traces attribution-correct across a task tree that may span dozens of stolen hops |
| Quiescence detection | `looksQuiescent()`: a racy, one-shot check of idle-worker count and per-deque emptiness | built into `ctl`'s active-thread-count bits plus a scan of every worker queue; `awaitQuiescence(timeout, unit)` is a supported, documented blocking API used by callers that need to know a whole pool has drained | a documented, race-audited quiescence primitive is required for callers (e.g. shutting down a batch reconciliation run cleanly) who need a real guarantee, not a best-effort hint |
| Deque implementation | `GrowableWorkStealingDeque<T>` over `AtomicReferenceArray`, `volatile int top`, `AtomicLong base` | `WorkQueue` uses raw `Unsafe`/`VarHandle` access into a plain `Object[]` with explicit acquire/release fences chosen per-field, avoiding the blanket cost of a full `AtomicReferenceArray` or a `volatile` `top` on the fast path | shaving a few nanoseconds per push/pop matters at the real pool's scale (the common pool backs `Stream.parallel()` calls across an entire JVM); this build trades that for code a reader can follow without a `VarHandle` primer |

### What a production pool needs that a teaching one omits

Five gaps matter most, in the order a production incident would surface them:

1. **No compensation for blocking work.** The single biggest correctness gap. If any
   `MiniRecursiveTask.compute()` in this build ever blocks on I/O — a `CardPayments` authorize
   call, a `DocumentVerification` vendor round-trip — the worker thread is gone from the pool's
   compute capacity until it returns, with nothing able to substitute another worker in its place.
   `ManagedBlocker` exists specifically to make blocking safe inside a fork/join pool; without it,
   the only safe rule for this build is the one stated in file 3: **never block inside `compute()`.**

2. **No submission/worker queue separation.** `submit()` in this build pushes straight onto a
   worker's own deque from any calling thread, including non-worker threads. Under concurrent
   external submission from several unrelated call sites, that turns an external caller into a
   second writer contending with the deque's owner — the whole design of file 1's single-CAS proof
   assumes exactly one writer at the `top` end. A production pool needs a genuinely separate
   submission path.

3. **No targeted wakeup.** Every idle worker in this build polls at a fixed interval rather than
   being woken precisely when work appears; that's acceptable at this pool's scale but wastes
   wake-and-recheck cycles at the tens-of-thousands-of-tasks-per-second scale the real common pool
   operates at across a whole JVM's `Stream.parallel()` traffic.

4. **No `CountedCompleter`-style completion.** Every task tree in this build is join-shaped
   (`fork` then `join`), which caps how deep task trees can nest before the help-by-executing
   machinery becomes the bottleneck. A DAG-shaped computation with wide fan-out and no natural
   left/right split — say, fanning a `PaymentRun`'s batch of withdrawals out to N independent
   verification steps that must all complete before the batch is released — is better served by
   completion callbacks than by blocking joins.

5. **No isolation for shared-pool workers.** `MiniForkJoinPool` is always explicitly constructed
   and privately owned by whoever built it, so worker identity isolation is a non-issue. The moment
   a pool is shared JVM-wide — as `commonPool()` is — a task written by one part of the codebase
   can observe thread-locals or a `ClassLoader` left behind by a completely unrelated task that ran
   on the same worker thread earlier, which is exactly what `InnocuousForkJoinWorkerThread` exists
   to prevent.

**Insight:** almost every item in this diff table traces back to one design fact this build shares
with the real pool — a fixed number of worker threads means every blocking or contended point is
now a shared, exhaustible resource, and each row above is a specific policy for protecting that
resource under a specific way it can be exhausted (blocking I/O, submission contention, wasted
wakeups, deep join chains, cross-task interference).

**Interview:** "what does `ForkJoinPool` do that a naive work-stealing pool doesn't?" — compensates
for blocking tasks via `ManagedBlocker` so blocking doesn't shrink effective parallelism, separates
external submission from worker-owned queues, wakes idle workers precisely via a Treiber stack
packed into one `ctl` field, and offers `CountedCompleter` for DAG-shaped task graphs that don't fit
the fork-then-join tree shape.

> **`ForkJoinPool`** is this build's same core idea — per-worker work-stealing deques with
> randomised victim selection and help-by-executing joins — hardened with compensation for
> blocking work, separated submission and worker queues, targeted wakeup, and a completion-based
> task style for graphs that don't decompose as simple binary trees.

## Pitfalls

### Assuming `ForkJoinPool.commonPool()` is safe to block inside, because "it's just a big thread pool"

**Wrong**

```java
// BROKEN: submitted to the common pool, blocks on a PSP call
ForkJoinPool.commonPool().submit(() -> {
    HttpResponse<String> response = cardPaymentsClient.authorize(request); // blocks up to p99 11s
    return response;
});
```

The common pool defaults to `availableProcessors() - 1` worker threads, shared across every
`Stream.parallel()` call and every `CompletableFuture` async stage in the entire JVM with no
explicit executor. Blocking one of its threads for up to the PSP's documented p99 of 11 seconds
takes that thread away from every unrelated parallel stream or future in the process for that
whole window — on an 8-core box, three or four such blocked submissions can visibly stall unrelated
`Stream.parallel()` calls that have nothing to do with `CardPayments` at all.

**Right**

```java
ForkJoinPool.ManagedBlocker blocker = new ForkJoinPool.ManagedBlocker() {
    private volatile HttpResponse<String> response;
    public boolean block() throws InterruptedException {
        response = cardPaymentsClient.authorize(request);
        return true;
    }
    public boolean isReleasable() {
        return response != null;
    }
};
ForkJoinPool.managedBlock(blocker);
```

Or, more simply for I/O-bound work: don't use the common pool for it at all — route it through a
dedicated I/O executor (file 5 of this build-it set) or a virtual-thread-per-task executor, and
reserve fork/join pools for CPU-bound, splittable compute the way this build's merge sort and
`HOUSE_REVENUE` sum use it.

**Why people believe it:** `ForkJoinPool` is a `java.util.concurrent.ExecutorService`, and every
other `ExecutorService` in the JDK tolerates blocking tasks just fine (that's the entire point of a
thread-pool-per-blocking-call design) — but `ForkJoinPool` is the one executor in the standard
library whose whole throughput model assumes tasks don't block, which is precisely why it alone
ships a `ManagedBlocker` escape hatch that no other `ExecutorService` needs.

## Cheat sheet

| If you need... | Reach for |
|---|---|
| CPU-bound recursive decomposition, no blocking | this build's `MiniRecursiveTask` shape, or real `RecursiveTask`/`RecursiveAction` |
| A task tree that occasionally must block | `ManagedBlocker` + `ForkJoinPool.managedBlock` |
| Wide fan-out/fan-in with no natural binary split | `CountedCompleter` |
| A JVM-wide default pool for parallel streams | `ForkJoinPool.commonPool()` — but never block inside it |
| Isolating a task from another task's thread-locals on a shared pool | rely on `InnocuousForkJoinWorkerThread` (common pool only) or use a privately-owned pool |
| A documented "is the whole pool drained" check | `awaitQuiescence(timeout, unit)`, not a hand-rolled racy hint |
| External, non-worker submission at scale | a pool with true submission-queue/worker-queue separation, not a shared deque |

## Self-test

**Q1.** Why is `ctl` a single packed field in the real `ForkJoinPool` instead of separate counters
the way this build uses `AtomicBoolean shutdown` and `AtomicInteger idleCount`?

<details><summary>Answer</summary>

Packing active-thread count, total-thread count, and the idle-worker stack pointer into one 64-bit
field lets the pool update all three together with a single CAS — for example, "pop the top idle
worker off the stack and increment the active count" happens as one atomic step. Separate fields
would need either a lock around updating them together or would risk a window where one field
reflects the update and the other hasn't yet, which this build's simpler, coarser synchronization
tolerates but a JVM-wide shared pool under heavy contention cannot.

</details>

**Q2.** What specific problem does `ManagedBlocker` solve that this build's `MiniForkJoinPool`
has no answer for?

<details><summary>Answer</summary>

If a task blocks on I/O inside `compute()`, the worker thread running it is unavailable to the pool
until the I/O completes, shrinking effective parallelism for the duration. `ManagedBlocker` lets the
pool detect this and temporarily start a compensating worker thread so the fixed-size pool's actual
compute capacity doesn't shrink just because one thread is legitimately blocked — this build has no
such mechanism and its own house rule is simply "never block inside compute()."

</details>

**Q3.** Why does the real pool separate submission queues from worker queues, when this build lets
`submit()` push directly onto a worker's own deque?

<details><summary>Answer</summary>

A worker's deque in the Chase-Lev design (file 1) assumes exactly one writer at the `top` end — the
owning worker itself. An external, non-worker thread pushing directly onto that same deque
introduces a second concurrent writer at the very end the single-CAS proof assumed was
single-writer, reopening races the proof explicitly ruled out. Separate submission queues keep
external callers from ever becoming a second writer on a worker-owned structure.

</details>

**Q4.** What does `CountedCompleter` avoid that plain `fork`/`join` (this build's shape) cannot,
and for what kind of task graph does that matter?

<details><summary>Answer</summary>

`CountedCompleter` avoids blocking joins entirely — completion propagates via callbacks
(`onCompletion`) once a task's pending-child count reaches zero, rather than a thread sitting in
`join()`'s help-loop waiting on a specific child. This matters for wide fan-out/fan-in DAGs (many
independent children feeding one parent) where the fork-then-join tree shape this build assumes
doesn't naturally fit, and where deep join-chain depth would otherwise stress the help-by-executing
machinery.

</details>

**Q5.** Why does `InnocuousForkJoinWorkerThread` exist only for the common pool and not for a
privately constructed `ForkJoinPool` (or this build's `MiniForkJoinPool`)?

<details><summary>Answer</summary>

A privately constructed pool is owned by one part of the codebase that controls what tasks run on
it, so cross-task interference via thread-locals or class loaders is a self-inflicted problem at
worst. The common pool runs tasks submitted from arbitrary, mutually unrelated parts of an entire
JVM process, so a worker thread's leftover state from one caller's task could otherwise leak into
or be exploited by a completely unrelated caller's task that happens to run on the same
reused thread later.

</details>

**Q6.** This build's `looksQuiescent()` is described as "racy." What concretely can go wrong if a
caller treats it as a hard guarantee rather than a hint?

<details><summary>Answer</summary>

Between the moment `looksQuiescent()` finishes checking every deque and idle count and the moment
the caller acts on a `true` result, a worker that was mid-`compute()` (not idle, not yet reflected
in the check) can fork a brand-new task, making the pool non-quiescent again immediately after the
check reported otherwise. The real pool's `awaitQuiescence` is built to survive exactly this by
polling under its own accounting rather than exposing a single racy snapshot as if it were final.

</details>

---

**Leaves covered:** 4.6.7 (1 leaf)
**Leaves deferred:** none
**Diagrams included:** none
**Target version:** Java 21 LTS
**Lines:** 231
