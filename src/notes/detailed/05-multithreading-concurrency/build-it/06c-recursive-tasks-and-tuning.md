# 05 Multithreading and Concurrency — Recursive tasks and tuning — BUILD IT (§4.6, leaves 4.6.5–4.6.6)

**Target version: Java 21 LTS.** | **Part 4 of 5** | [Index](../00-index.md)
Previous: [Growing the deque and the mini pool](06b-growing-and-the-mini-pool.md) · Next: [The fork/join consolidated diff](06d-forkjoin-consolidated-diff.md)

Files 1–2 built `GrowableWorkStealingDeque<T>` and `MiniForkJoinPool`, N workers each owning one
deque with randomised victim stealing. This file adds the task abstraction workers actually run —
`MiniRecursiveTask<V>` — and tunes it on a parallel merge sort and a parallel sum.

### `MiniRecursiveTask<V>` — fork, compute, join, and the deadlock this pool must not have

#### Mental model

A recursive task is a promise that knows how to split itself in half if the work is still too big,
and knows how to produce a plain value once it's small enough to just compute directly. `fork()`
hands one half to the pool (pushed onto the calling worker's own deque, cheap, no CAS) while the
caller keeps computing the other half itself on the same thread — so a single logical "compute this
whole range" call turns into a tree of tasks, most of which never leave the worker that created
them, with only the tasks that overflow into idle time actually getting stolen.

#### Why it exists

Handing every subtask to a shared executor via `submit()` and blocking on the returned `Future`
works, but it has a specific failure mode once recursion goes deep: a pool sized to, say, 8 threads
running a merge sort that recurses to hundreds of subtasks can deadlock if every worker thread ends
up blocked inside `Future.get()` waiting for a subtask that itself needs a worker thread to run on,
and no worker thread is free because they're all blocked waiting. `MiniRecursiveTask.join()` avoids
this by making the *calling* thread available to execute other pending work while it waits, instead
of merely blocking.

#### When to reach for it, and when not

Reach for it when a computation decomposes recursively and each leaf is pure, CPU-bound work with
no I/O and no locks held across the fork/join boundary — merge-sorting `WithdrawalTransaction`
batches or summing `LedgerEntry` amounts split by range both qualify. Do not reach for it when
subtasks block on I/O (a `CardPayments` PSP call per subtask) — blocking a worker thread on network
I/O inside `compute()` starves the fixed-size pool of the very threads needed to make progress on
sibling tasks; that shape wants virtual threads or an I/O-bound executor instead, not fork/join.

#### How it works — the help-by-executing trick

```java
package quizstakes.forkjoin;

import java.util.concurrent.atomic.AtomicReference;

/**
 * A single-shot recursive task. Runs on MiniForkJoinPool workers (06b). compute() must
 * be pure and CPU-bound: no blocking I/O, no locks held across fork()/join().
 */
public abstract class MiniRecursiveTask<V> implements Runnable {

    private static final Object NOT_DONE = new Object();

    private final AtomicReference<Object> result = new AtomicReference<>(NOT_DONE);
    private volatile RuntimeException failure;
    private final MiniForkJoinPool pool;

    protected MiniRecursiveTask(MiniForkJoinPool pool) {
        this.pool = pool;
    }

    protected abstract V compute();

    @Override
    public final void run() {
        try {
            V value = compute();
            result.set(value == null ? NULL_SENTINEL : value);
        } catch (RuntimeException e) {
            failure = e;
            result.set(FAILED_SENTINEL);
        }
        synchronized (this) {
            this.notifyAll(); // wakes any joiner that fell through to a blocking wait
        }
    }

    private static final Object NULL_SENTINEL = new Object();
    private static final Object FAILED_SENTINEL = new Object();

    /**
     * Pushes this task onto whichever worker's deque is currently running compute() — not
     * necessarily the deque this task's ancestor was originally pushed to, since a stolen
     * task's own further forks belong to the thread that stole it, not its original owner.
     */
    public final void fork() {
        int workerIndex = MiniForkJoinPool.currentWorkerIndexOrMinusOne();
        if (workerIndex < 0) {
            throw new IllegalStateException("fork() called outside a MiniForkJoinPool worker");
        }
        pool.forkOnto(workerIndex, this);
    }

    /**
     * Blocks the calling thread until this task's result is available — but "blocks" here
     * means "keeps executing other work from the calling worker's own pool while waiting,"
     * not "parks and does nothing." This is the trick that prevents the classic fork/join
     * deadlock: a fixed pool of N workers can safely have far more than N tasks in flight
     * because a worker waiting on join() is never truly idle.
     */
    @SuppressWarnings("unchecked")
    public final V join() {
        int workerIndex = MiniForkJoinPool.currentWorkerIndexOrMinusOne();
        if (workerIndex >= 0) {
            helpUntilDone(workerIndex);
        } else {
            blockUntilDone(); // called from outside any worker (e.g. the submitting thread)
        }
        if (failure != null) {
            throw failure;
        }
        Object value = result.get();
        return value == NULL_SENTINEL ? null : (V) value;
    }

    private void helpUntilDone(int workerIndex) {
        while (result.get() == NOT_DONE) {
            Runnable other = pool.stealOrDrainForHelper(workerIndex);
            if (other != null) {
                other.run(); // execute someone else's pending work while we wait
            } else {
                // Nothing to help with right now; a short bounded wait, not a spin.
                synchronized (this) {
                    if (result.get() == NOT_DONE) {
                        try {
                            this.wait(1); // 1ms upper bound — re-check the loop condition
                        } catch (InterruptedException e) {
                            Thread.currentThread().interrupt();
                            return;
                        }
                    }
                }
            }
        }
    }

    private void blockUntilDone() {
        synchronized (this) {
            while (result.get() == NOT_DONE) {
                try {
                    this.wait();
                } catch (InterruptedException e) {
                    Thread.currentThread().interrupt();
                    return;
                }
            }
        }
    }
}
```

`MiniForkJoinPool` needs one small addition so a joining worker can help rather than merely spin —
drain its own deque first (cheapest), then try a steal, exactly like the idle path already does:

```java
// add to MiniForkJoinPool
Runnable stealOrDrainForHelper(int workerIndex) {
    Runnable own = deques[workerIndex].popTop();
    if (own != null) {
        return own;
    }
    return tryStealFromRandomVictim(workerIndex);
}
```

**[PROVE] why help-by-executing avoids the deadlock a naive `join()` would have.** Consider a
naive `join()` that simply does `synchronized (this) { while (!done) wait(); }` with nothing else,
on a pool sized to exactly 2 workers. Worker A computes a merge-sort node that forks its left half
(runs on worker A itself, recursively, first) and its right half (pushed to A's deque, available
for worker B to steal). Suppose recursion goes three levels deep before any base case is reached,
and every one of those levels calls `join()` on its right-hand fork before returning. With a naive
`join()`, worker A blocks on the level-1 join waiting for worker B (or a steal) to finish the
level-1 right subtree. If that right subtree itself recurses and its *own* left branch runs
directly on whichever worker picked it up, and that worker in turn calls a naive `join()` waiting
on a task that was pushed onto worker A's deque (because it can't find idle capacity elsewhere) —
and worker A is itself blocked, not looping, not draining its own deque — then that pushed task
sits forever, and both workers are mutually stuck. With only 2 real OS threads and no thread doing
anything but waiting, the two `join()` calls form a cycle where each side's progress depends on
work that only the other, blocked side could execute. `helpUntilDone()` breaks this: while worker A
"waits" on a `join()`, it is still calling `stealOrDrainForHelper`, which drains its own deque
first — so any task sitting on A's own deque (exactly the case that starved the naive version) gets
executed by A itself, not left for someone else. The deadlock cycle above cannot form because no
call to `join()` ever removes a worker from the pool of threads still capable of making progress.

**Insight:** the fix is not "add more threads" — it's making every blocked-looking thread still be
an active worker. A fixed-size pool with help-by-executing behaves, for scheduling purposes, as if
it had unbounded threads for the purpose of avoiding this specific deadlock, without actually
paying for unbounded OS threads.

**Pitfall:** calling `join()` from a thread that is not a pool worker (e.g. the thread that
originally submitted the top-level task) and expecting it to help. `join()` correctly detects
`currentWorkerIndexOrMinusOne() < 0` and falls back to `blockUntilDone()` — a plain wait — because
a non-worker thread has no deque of its own to drain and nothing meaningful to "help" with; this is
safe (no deadlock, since the outermost caller isn't itself required by any other task) but does
mean the top-level submission should be a thin wrapper, not called recursively from inside
`compute()`.

**Interview:** "how does `ForkJoinPool.join()` avoid deadlocking a fixed-size pool?" — a joining
worker doesn't block outright; it keeps pulling and running other pending tasks (its own deque
first, then stealing) until the task it's joining on completes, so the worker never actually leaves
the pool of threads capable of making progress.

> **`MiniRecursiveTask<V>.join()`** blocks logically but not physically — the calling worker
> thread keeps executing other available tasks while waiting, which is what lets a fixed-size pool
> safely run a task tree far deeper than its thread count without deadlocking.

### Parallel merge sort and parallel sum — tuning the sequential threshold

#### Mental model

Every recursive task pays a fixed overhead per split: an object allocation, a `fork()` push, a
`join()` wait loop. Below some range size, that overhead exceeds the cost of just sorting or
summing the range directly, single-threaded, right there. The sequential threshold is the range
size below which a task stops splitting and falls back to plain sequential code — get it too low
and overhead dominates; get it too high and you never generate enough parallel tasks to use the
available cores.

```java
package quizstakes.forkjoin;

import java.util.Arrays;
import java.util.Comparator;

/** Parallel merge sort over WithdrawalTransaction, ordered by requestedAt. */
public final class WithdrawalMergeSortTask extends MiniRecursiveTask<Void> {

    public record WithdrawalTransaction(String id, java.time.Instant requestedAt, java.math.BigDecimal amount) {}

    private static final Comparator<WithdrawalTransaction> BY_REQUESTED_AT =
            Comparator.comparing(WithdrawalTransaction::requestedAt);

    private final WithdrawalTransaction[] data;
    private final WithdrawalTransaction[] scratch;
    private final int lo;
    private final int hi; // exclusive
    private final int sequentialThreshold;

    private final MiniForkJoinPool pool;

    public WithdrawalMergeSortTask(MiniForkJoinPool pool, WithdrawalTransaction[] data, int sequentialThreshold) {
        this(pool, data, new WithdrawalTransaction[data.length], 0, data.length, sequentialThreshold);
    }

    private WithdrawalMergeSortTask(MiniForkJoinPool pool, WithdrawalTransaction[] data,
                                     WithdrawalTransaction[] scratch,
                                     int lo, int hi, int sequentialThreshold) {
        super(pool);
        this.pool = pool;
        this.data = data;
        this.scratch = scratch;
        this.lo = lo;
        this.hi = hi;
        this.sequentialThreshold = sequentialThreshold;
    }

    @Override
    protected Void compute() {
        int size = hi - lo;
        if (size <= sequentialThreshold) {
            Arrays.sort(data, lo, hi, BY_REQUESTED_AT); // plain sequential fallback
            return null;
        }
        int mid = lo + size / 2;
        WithdrawalMergeSortTask left = new WithdrawalMergeSortTask(pool, data, scratch, lo, mid, sequentialThreshold);
        WithdrawalMergeSortTask right = new WithdrawalMergeSortTask(pool, data, scratch, mid, hi, sequentialThreshold);
        left.fork();          // left half runs on some worker via stealing
        right.compute();      // right half runs on this thread directly, no allocation-of-a-frame overhead
        left.join();          // help-by-executing until the left half is actually done
        merge(lo, mid, hi);
        return null;
    }

    private void merge(int lo, int mid, int hi) {
        System.arraycopy(data, lo, scratch, lo, hi - lo);
        int i = lo, j = mid, k = lo;
        while (i < mid && j < hi) {
            data[k++] = BY_REQUESTED_AT.compare(scratch[i], scratch[j]) <= 0 ? scratch[i++] : scratch[j++];
        }
        while (i < mid) data[k++] = scratch[i++];
        while (j < hi) data[k++] = scratch[j++];
    }
}
```

Note the asymmetry deliberately kept from the JDK's own `RecursiveAction` idiom: `left.fork()` then
`right.compute()` directly (not `right.fork()` too), then `left.join()`. Forking both halves and
joining both would cost two pushes and two joins; computing the right half inline costs neither —
the calling thread was going to do *some* work anyway, so let it do useful work instead of pure
task-management overhead.

```java
/** Parallel sum of LedgerEntry amounts filtered to HOUSE_REVENUE, over one day's ~19.8M rows. */
public final class HouseRevenueSumTask extends MiniRecursiveTask<java.math.BigDecimal> {

    public record LedgerEntry(String position, java.math.BigDecimal amount) {}

    private final MiniForkJoinPool pool;
    private final LedgerEntry[] entries;
    private final int lo;
    private final int hi;
    private final int sequentialThreshold;

    public HouseRevenueSumTask(MiniForkJoinPool pool, LedgerEntry[] entries, int lo, int hi, int sequentialThreshold) {
        super(pool);
        this.pool = pool;
        this.entries = entries;
        this.lo = lo;
        this.hi = hi;
        this.sequentialThreshold = sequentialThreshold;
    }

    @Override
    protected java.math.BigDecimal compute() {
        int size = hi - lo;
        if (size <= sequentialThreshold) {
            java.math.BigDecimal sum = java.math.BigDecimal.ZERO;
            for (int i = lo; i < hi; i++) {
                if ("HOUSE_REVENUE".equals(entries[i].position())) {
                    sum = sum.add(entries[i].amount());
                }
            }
            return sum;
        }
        int mid = lo + size / 2;
        HouseRevenueSumTask left = new HouseRevenueSumTask(pool, entries, lo, mid, sequentialThreshold);
        HouseRevenueSumTask right = new HouseRevenueSumTask(pool, entries, mid, hi, sequentialThreshold);
        left.fork();
        java.math.BigDecimal rightSum = right.compute();
        java.math.BigDecimal leftSum = left.join();
        return leftSum.add(rightSum);
    }
}
```

#### [NUM] Finding the threshold

Start from the fixed per-task overhead, not a guess. Measured order-of-magnitude on typical
hardware: allocating a task object plus one `fork()` push plus one `join()` poll cycle costs on the
order of low hundreds of nanoseconds when the deque isn't contended. Summing one `LedgerEntry`
(a `String.equals` plus a `BigDecimal.add`) costs on the order of tens of nanoseconds. For the
per-task overhead to be under, say, 1% of the useful work a leaf does, a leaf needs to do at least
roughly `100x` the overhead in useful work: `100 * 300ns / 30ns per element ≈ 1,000` elements as a
rough floor. That gives a starting threshold, not a final one — the actual measurement loop:

```java
public final class ThresholdSweep {

    public static void main(String[] args) {
        LedgerEntry[] entries = LedgerFixtures.generateOneDayHouseRevenueSample(19_800_000);
        int[] thresholds = {100, 1_000, 5_000, 20_000, 100_000, 500_000};
        MiniForkJoinPool pool = new MiniForkJoinPool(Runtime.getRuntime().availableProcessors());
        for (int threshold : thresholds) {
            long start = System.nanoTime();
            HouseRevenueSumTask root = new HouseRevenueSumTask(pool, entries, 0, entries.length, threshold);
            pool.submit(root, 0);
            java.math.BigDecimal result = root.join();
            long elapsedMs = (System.nanoTime() - start) / 1_000_000;
            System.out.printf("threshold=%,d  elapsedMs=%d  result=%s%n", threshold, elapsedMs, result);
        }
        pool.shutdown();
    }
}
```

Reading the sweep: at `threshold=100` the run is dominated by task-management overhead — millions
of tiny tasks, most of the wall-clock time spent pushing, stealing, and joining rather than adding
`BigDecimal`s. At `threshold=500_000` the tree barely splits at all on an 8-core box (fewer leaves
than cores), leaving several cores idle throughout. The sweet spot for this shape of workload —
cheap per-element work, tens of millions of elements, 8 cores — lands in the low thousands to tens
of thousands range, because that's where the leaf count comfortably exceeds the core count (giving
the scheduler slack to rebalance if one core's leaves finish early) while each leaf still does
enough real work to amortise its `fork`/`join` cost to well under 1%.

**Pitfall:** picking a threshold once on a laptop and shipping it. The right threshold depends on
the ratio of per-element work to fork/join overhead, which changes if the per-element work changes
(summing a `BigDecimal` versus, say, running a `Verdict` classification per entry is a very
different ratio) — the sweep above is the reusable tool, not the specific numbers it produced on
one run.

**Interview:** "how do you pick a sequential threshold for a fork/join task?" — estimate fork/join
overhead in nanoseconds, estimate per-element leaf work in nanoseconds, pick a threshold where
leaf work is roughly two orders of magnitude larger than the overhead, then confirm with an actual
sweep across threshold values on the real workload rather than trusting the estimate alone.

> **The sequential threshold** is the range size below which a recursive task stops splitting and
> runs a plain sequential loop instead, chosen so that per-task fork/join overhead stays a small
> fraction of the useful work each leaf performs.

## Pitfalls

### Forking both halves and joining both, out of a sense of symmetry

**Wrong**

```java
protected Void compute() {
    if (hi - lo <= sequentialThreshold) { Arrays.sort(data, lo, hi, BY_REQUESTED_AT); return null; }
    int mid = lo + (hi - lo) / 2;
    WithdrawalMergeSortTask left = new WithdrawalMergeSortTask(data, scratch, lo, mid, sequentialThreshold);
    WithdrawalMergeSortTask right = new WithdrawalMergeSortTask(data, scratch, mid, hi, sequentialThreshold);
    left.fork();
    right.fork();  // wasteful: this thread now has nothing to do but wait
    left.join();
    right.join();
    merge(lo, mid, hi);
    return null;
}
```

This still works, but every level of recursion pays two `fork()` pushes and two `join()` waits
instead of one of each, and the calling thread does zero useful compute at that level — it becomes
pure task-management overhead, measurably slower on the threshold sweep above.

**Right**

`left.fork(); right.compute(); left.join();` — one fork, one join, and the calling thread computes
the right half directly instead of idling.

**Why people believe it:** `fork()`/`join()` looks symmetric in the API, so forking both halves
looks like the "complete" pattern — but the JDK's own `RecursiveAction` documentation and every
real `ForkJoinTask` subclass in `java.util` follow the fork-one-compute-other pattern specifically
to avoid this waste.

## Cheat sheet

| Concept | What it does | Cost if misused |
|---|---|---|
| `fork()` | pushes `this` onto the calling worker's own deque | called off-worker → `IllegalStateException` |
| `join()` on a worker | helps execute other pending work while waiting | naive block-only join risks deadlock on deep recursion |
| `join()` off-worker | plain blocking wait | safe only because nothing else depends on this thread |
| `left.fork(); right.compute(); left.join();` | one fork, one join, caller does real work | forking both halves wastes the caller's own cycles |
| Sequential threshold too low | thousands of tiny tasks, overhead-dominated | wall-clock time worse than single-threaded |
| Sequential threshold too high | too few leaves to fill available cores | cores sit idle, no parallel speedup |

## Self-test

**Q1.** Why does `join()` behave differently depending on whether the calling thread is a pool
worker or not?

<details><summary>Answer</summary>

A pool worker has its own deque and can make real progress on other pending tasks while
"waiting," which is what prevents deadlock when many joins are nested deeply on a fixed-size pool.
A non-worker thread (e.g. the original submitter) has no deque to drain and nothing meaningful to
execute, so it falls back to a plain blocking wait — safe here because the outer submission is not
itself something any pool worker is blocked waiting on.

</details>

**Q2.** Walk through why a naive, block-only `join()` can deadlock a 2-worker pool but
`helpUntilDone()` cannot.

<details><summary>Answer</summary>

With a naive join, a worker blocked waiting for a task never executes anything else, so if that
worker itself happens to be the only one holding a task some other blocked thread needs, no thread
is left free to run it — a cycle of mutual waiting with no thread making progress. `helpUntilDone()`
keeps the "waiting" worker actively draining its own deque and stealing from others, so a task that
naive-join would have left stranded still gets picked up and executed by the very thread that's
nominally "blocked" on something else.

</details>

**Q3.** In the merge sort, why is `right.compute()` called directly instead of `right.fork()`
followed by `right.join()`?

<details><summary>Answer</summary>

The calling thread has nothing else useful to do at that point in its own call stack besides
process the right half somehow — forking it would just push it onto its own deque and then likely
immediately pop it right back off (since nothing else displaced it), paying push/steal-check/join
overhead for no benefit over calling `compute()` directly inline.

</details>

**Q4.** What happens to correctness, not just performance, if the sequential threshold in
`HouseRevenueSumTask` is set to a number larger than the whole input array?

<details><summary>Answer</summary>

The very first `compute()` call takes the `size <= sequentialThreshold` branch and sums the entire
array in a single sequential loop, on a single thread. The result is still correct — a fork/join
task with a very high threshold degrades gracefully to sequential execution, it just gets none of
the parallel speedup the tree structure exists to provide.

</details>

**Q5.** Why does the threshold sweep vary the threshold on a fixed 19.8M-row input rather than
varying the input size on a fixed threshold?

<details><summary>Answer</summary>

The question being answered is "at what leaf size does per-task overhead stop mattering for this
workload," which is a property of the ratio between fixed overhead and per-element work, not of
total input size — sweeping the threshold on a realistic fixed input size directly measures where
that ratio crosses the point of diminishing returns, whereas varying input size at a fixed
threshold would only show that bigger inputs parallelize better, which is already expected.

</details>

**Q6.** Why must `compute()` be free of blocking I/O for `MiniRecursiveTask` to be safe on a
fixed-size pool, given that `join()` already handles blocking safely?

<details><summary>Answer</summary>

`join()`'s help-by-executing trick only rescues a worker that is waiting on another `compute()`
call it can substitute real work for. Blocking I/O inside `compute()` itself (say, a `CardPayments`
network call) has no substitute task to run in its place — the worker thread is simply gone from
the pool of available compute capacity until the I/O completes, with nothing in this design able to
route other pending work onto it in the meantime.

</details>

---

**Leaves covered:** 4.6.5–4.6.6 (2 leaves)
**Leaves deferred:** none
**Diagrams included:** none
**Target version:** Java 21 LTS
**Lines:** 521
