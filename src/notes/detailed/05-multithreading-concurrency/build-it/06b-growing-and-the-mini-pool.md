# 05 Multithreading and Concurrency — Growing the deque and the mini pool — BUILD IT (§4.6, leaves 4.6.3–4.6.4)

**Target version: Java 21 LTS.** | **Part 4 of 5** | [Index](../00-index.md)
Previous: [The work-stealing deque](06-work-stealing-deque.md) · Next: [Recursive tasks and tuning](06c-recursive-tasks-and-tuning.md)

File 1 built `WorkStealingDeque<T>` — plain-store owner end at `top`, CAS'd thief end at `base`,
one unavoidable CAS when exactly one task remains. This file grows that deque without dropping a
task mid-steal, then wires N of them into `MiniForkJoinPool`.

### Growing the deque without losing a steal

#### Mental model

The fixed-capacity deque from file 1 has a hard ceiling: `capacity` slots, no more. A worker
splitting `LedgerEntry` ranges recursively during a burst — 24k applications/day translated into
merge-sort-style task fan-out over `WithdrawalTransaction` batches — can push faster than it pops,
and a fixed array eventually has nowhere left to write. Growing means allocating a bigger array and
copying the live window `[base, top)` across. The mental picture: it's a house move happening while
someone at the old address is still allowed to knock on the door and ask "is anyone home?" — the
copy has to finish, and the old address has to correctly forward that knock, before the move counts
as done for a thief that started asking before the move.

#### Why it exists

Without growth, capacity has to be sized for the worst-case fan-out up front, which for a
recursive merge sort over the day's ~19.8M-row reconciliation batch means guessing a number that
is either wasteful (most workers never approach it) or wrong (the one pathological run that does
approach it corrupts nothing but throws `ArrayIndexOutOfBoundsException`-shaped failures from a
wrapped index colliding with live data). Growth trades a rare, amortized copy for never having to
guess.

#### When to reach for it, and when not

Grow in place — the technique below — when the deque is owner-private and only thieves read
concurrently, which is exactly this pool's shape. Do not use this technique for a queue with
multiple concurrent writers; growing a multi-producer structure safely needs a different
mechanism entirely (a lock, or a fully immutable persistent structure), because the invariant this
proof leans on — only the owner ever writes `top` or reassigns the array reference — would no
longer hold.

#### How it works — why a naive copy drops a steal

Naive attempt: allocate a new array, copy `tasks.get(i)` for `i` in `[base, top)` into the new
array's corresponding low slots, reassign the field, done. Walk through why this loses a task.

Say `base = 10`, `top = 14` (four live tasks, indices 10–13), old capacity 16. A thief calls
`steal()`, reads `b = base.get() = 10`, and is about to read `tasks.get(10 & 15)`. Right at that
instant the owner's `pushTop` triggers a grow: it allocates `newTasks`, copies slots 10–13 across,
and reassigns `this.tasks = newTasks`. The thief's `tasks.get(...)` call — if `tasks` was read as a
local *before* the reassignment but executed *after* — either reads from the old array (fine, the
data is still there, nothing was zeroed) or, if the field re-read happens mid-method some other
way, could observe a torn view. The actual failure mode is narrower and easier to get wrong in a
different way: a copy loop that **clears the old array's slots as it copies** — `newTasks.set(k,
old); old.set(oldIndex, null);` — so that a thief already inside `steal()`, holding a stale
reference to the *old* backing array object from before the grow, reads `null` where a live task
used to be and wrongly concludes the deque is empty, permanently losing that task rather than
retrying against a slot that would have found it.

The fix: never clear the old array, and never let a thief block on which array is "the" array —
let it operate against whichever array reference it captured, and treat a `null` read from a slot
inside `[base, top)` as "retry the whole `steal()`, do not report success or failure yet", not as
"the deque is empty".

```java
package quizstakes.forkjoin;

import java.util.concurrent.atomic.AtomicLong;
import java.util.concurrent.atomic.AtomicReferenceArray;

/**
 * Chase-Lev deque that grows in place. Continues from WorkStealingDeque in
 * 06-work-stealing-deque.md; same top/base roles, same single-CAS last-element rule.
 * Growth never clears the vacated array, so a thief holding a stale array reference
 * from before a grow still sees every task it is entitled to see.
 */
public final class GrowableWorkStealingDeque<T> {

    // Volatile: a grow reassigns this reference; thieves must see the new one promptly,
    // but a thief that already captured the old reference must still complete correctly.
    private volatile AtomicReferenceArray<T> tasks;
    private volatile int mask;

    private volatile int top = 0;
    private final AtomicLong base = new AtomicLong(0);

    public GrowableWorkStealingDeque(int initialCapacityPowerOfTwo) {
        this.tasks = new AtomicReferenceArray<>(initialCapacityPowerOfTwo);
        this.mask = initialCapacityPowerOfTwo - 1;
    }

    /** Owner-only. Grows if the deque is full, then pushes. */
    public void pushTop(T task) {
        int t = top;
        long b = base.get();
        AtomicReferenceArray<T> current = tasks;
        int currentMask = mask;
        if (t - b >= currentMask) { // one slot of headroom kept deliberately
            growTo(currentMask + 1, t, b);
            current = tasks;
            currentMask = mask;
        }
        current.set(t & currentMask, task);
        top = t + 1;
    }

    // Owner-only, never touches base, never clears the old array.
    private void growTo(int oldCapacity, int t, long b) {
        int newCapacity = oldCapacity * 2;
        AtomicReferenceArray<T> oldArr = tasks;
        AtomicReferenceArray<T> newArr = new AtomicReferenceArray<>(newCapacity);
        int newMask = newCapacity - 1;
        for (long i = b; i < t; i++) {
            // Deliberately NOT clearing oldArr here. A thief that captured `oldArr`
            // before this grow must still find every task it is entitled to steal.
            newArr.set((int) (i & newMask), oldArr.get((int) (i & (oldCapacity - 1))));
        }
        this.mask = newMask;
        this.tasks = newArr; // publish last: mask must be visible no later than the new array
    }

    /** Owner-only. Same three-way branch as the fixed-size version. */
    public T popTop() {
        int t = top - 1;
        top = t;
        long b = base.get();
        if (t < b) { top = t + 1; return null; }
        AtomicReferenceArray<T> current = tasks;
        T task = current.get(t & mask);
        if (t > b) return task;
        boolean won = base.compareAndSet(b, b + 1);
        top = b + 1;
        return won ? task : null;
    }

    /** Called by any thief. Retries internally against a stale array, never reports false-empty. */
    public T steal() {
        while (true) {
            long b = base.get();
            int t = top;
            if (b >= t) {
                return null; // genuinely empty, not a stale-array artifact
            }
            AtomicReferenceArray<T> snapshot = tasks; // one consistent view for this attempt
            int snapshotMask = mask;
            T task = snapshot.get((int) (b & snapshotMask));
            if (task == null) {
                // Could be: owner grew between our base/top read and this array read, and the
                // index no longer lines up in the (now-stale) mask, OR another thief is mid-CAS
                // on this exact slot. Either way, re-read base/top/mask and try again rather than
                // declaring the deque empty — the old array was never cleared, so the task is
                // still discoverable once we re-align mask and array to the same snapshot.
                continue;
            }
            if (!base.compareAndSet(b, b + 1)) {
                return null; // lost a genuine race for a real task; caller picks a new victim
            }
            return task;
        }
    }
}
```

**Insight:** the fix is not "synchronize the grow" — it is "make the old array's data outlive the
grow". Growth becomes safe not by adding a lock but by removing the one action (clearing the
vacated slots) that would have made a stale reference lie to its reader.

**Pitfall:** reusing the same array object and just extending its logical length (impossible in
Java — arrays are fixed-size — but the equivalent mistake is calling `System.arraycopy` into a
*resized view of the same reference* via reflection tricks, or pooling array objects and reusing
one that still has old task references sitting past the new `top`). Any path that lets a slot
`>= top` retain a stale, uncleared task reference risks a *duplicate* steal instead of a lost one —
the mirror-image bug. This implementation avoids it because `top` is only ever advanced past slots
the owner itself just wrote.

**Interview:** "how do you resize a work-stealing deque without losing a task mid-steal?" — copy
the live window into a new array without touching the old one, publish the new array and its mask
last, and make thief-side reads treat "found `null` inside `[base, top)`" as "retry", never as
"empty" — the old array's untouched data is the safety net that makes retrying correct.

> Growing a Chase-Lev deque is safe exactly because the grow never *removes* information from the
> array a concurrent thief might still be reading — it only ever adds a newer, bigger array
> alongside data that remains valid wherever it already was.

### `MiniForkJoinPool` — N workers, N deques, randomised stealing

#### Mental model

N worker threads, each owning exactly one `GrowableWorkStealingDeque<Runnable>`. A worker's loop
is: drain your own deque first (cheapest, no contention); when it's empty, pick a *different*
worker uniformly at random and try to steal from it; if that fails, try another random victim a
bounded number of times; if nothing turns up anywhere, back off briefly rather than spinning the
core at 100% for no work, then check again. This is deliberately not round-robin victim selection —
round-robin creates a predictable hot spot where every idle worker converges on victim 0 first,
turning N-1 idle workers into N-1 threads contending on one deque's `base` CAS.

#### Why it exists

A single shared queue serializes every dequeue across every worker. Static partitioning of the
`WithdrawalTransaction` merge-sort's initial ranges across N workers leaves a worker that drew a
denser or more skewed range running long after the others finished. Per-worker deques with
randomised stealing let idle capacity find work wherever it actually is, at the cost of only
occasional, load-proportional contention.

#### When to reach for it, and when not

This shape earns its keep when task counts vastly exceed worker counts and tasks fan out
recursively — the merge sort and the `HOUSE_REVENUE` parallel sum built in file 3 of this set both
qualify. It is the wrong shape for a small, fixed number of long-running, non-splitting jobs (four
`ledger-reconcile` batch jobs that each run for an hour) — there a plain fixed thread pool from
file 5 of this build-it set is simpler and stealing buys nothing because there is nothing left to
steal once each worker has its one job.

#### How it works

```java
package quizstakes.forkjoin;

import java.util.List;
import java.util.concurrent.ThreadLocalRandom;
import java.util.concurrent.atomic.AtomicInteger;
import java.util.concurrent.atomic.AtomicBoolean;

/**
 * Fixed-size work-stealing pool over GrowableWorkStealingDeque. Workers are named for
 * what they do: ledger-reconcile-0 .. ledger-reconcile-(N-1).
 */
public final class MiniForkJoinPool {

    private final GrowableWorkStealingDeque<Runnable>[] deques;
    private final Thread[] workers;
    private final AtomicBoolean shutdown = new AtomicBoolean(false);
    private final AtomicInteger idleCount = new AtomicInteger(0);
    private static final int STEAL_ATTEMPTS_BEFORE_BACKOFF = 8;
    private static final long PARK_NANOS_ON_IDLE = 200_000L; // 0.2 ms, order-of-magnitude only

    @SuppressWarnings("unchecked")
    public MiniForkJoinPool(int parallelism) {
        this.deques = new GrowableWorkStealingDeque[parallelism];
        this.workers = new Thread[parallelism];
        for (int i = 0; i < parallelism; i++) {
            deques[i] = new GrowableWorkStealingDeque<>(64);
        }
        for (int i = 0; i < parallelism; i++) {
            int workerIndex = i;
            workers[i] = new Thread(() -> workerLoop(workerIndex), "ledger-reconcile-" + i);
            workers[i].setDaemon(true);
        }
        for (Thread worker : workers) {
            worker.start();
        }
    }

    /** Submit from outside the pool (or re-entrantly from a worker) onto a chosen deque. */
    public void submit(Runnable task, int preferredWorker) {
        deques[preferredWorker % deques.length].pushTop(task);
    }

    /** Called by worker code itself when it forks a subtask — pushes to its own deque. */
    public void forkOnto(int workerIndex, Runnable task) {
        deques[workerIndex].pushTop(task);
    }

    // Set only inside workerLoop, for the lifetime of that worker thread. MiniRecursiveTask
    // reads this to find out which deque fork() should push onto and which worker join()
    // should help-execute from — it deliberately does not track this per-task, because a
    // stolen task keeps running compute() on whichever thread stole it, and any further
    // forks it makes belong on *that* thread's deque, not the deque it was originally pushed to.
    private static final ThreadLocal<Integer> CURRENT_WORKER_INDEX = new ThreadLocal<>();

    /** -1 if the calling thread is not a worker of any MiniForkJoinPool. */
    public static int currentWorkerIndexOrMinusOne() {
        Integer index = CURRENT_WORKER_INDEX.get();
        return index == null ? -1 : index;
    }

    private void workerLoop(int self) {
        CURRENT_WORKER_INDEX.set(self);
        GrowableWorkStealingDeque<Runnable> own = deques[self];
        while (!shutdown.get()) {
            Runnable task = own.popTop();
            if (task == null) {
                task = tryStealFromRandomVictim(self);
            }
            if (task != null) {
                task.run();
            } else {
                parkBriefly();
            }
        }
    }

    private Runnable tryStealFromRandomVictim(int self) {
        int n = deques.length;
        if (n <= 1) {
            return null; // no other deque exists to steal from
        }
        ThreadLocalRandom rnd = ThreadLocalRandom.current();
        for (int attempt = 0; attempt < STEAL_ATTEMPTS_BEFORE_BACKOFF; attempt++) {
            int victim = rnd.nextInt(n - 1);
            if (victim >= self) {
                victim++; // map [0, n-1) onto "any index except self"
            }
            Runnable stolen = deques[victim].steal();
            if (stolen != null) {
                return stolen;
            }
        }
        return null;
    }

    private void parkBriefly() {
        idleCount.incrementAndGet();
        try {
            java.util.concurrent.locks.LockSupport.parkNanos(PARK_NANOS_ON_IDLE);
        } finally {
            idleCount.decrementAndGet();
        }
    }

    /** True once every deque is empty and every worker is parked — a cheap, racy quiescence hint. */
    public boolean looksQuiescent() {
        if (idleCount.get() != workers.length) {
            return false;
        }
        for (GrowableWorkStealingDeque<Runnable> deque : deques) {
            if (!deque.isEmptyHint()) {
                return false;
            }
        }
        return true;
    }

    public void shutdown() {
        shutdown.set(true);
        for (Thread worker : workers) {
            worker.interrupt();
        }
    }

    public int parallelism() {
        return deques.length;
    }
}
```

`GrowableWorkStealingDeque` needs one addition to support `looksQuiescent()` — expose the same
cheap emptiness check the fixed-size version had:

```java
// add to GrowableWorkStealingDeque<T>
public boolean isEmptyHint() {
    return base.get() >= top;
}
```

**Random victim selection, not round-robin:** picking `victim = rnd.nextInt(n - 1)` and skipping
self by shifting is deliberately biased toward *not* re-checking the same victim every attempt in a
predictable order — with four `ledger-reconcile` workers idle simultaneously and round-robin victim
order, all four converge on worker 0 first on every single idle cycle, so worker 0's deque (if it
happens to have work) is CAS-contended by three thieves at once while workers 1–3 sit unexamined
until worker 0 fails. Randomising spreads that contention across all live deques instead of
concentrating it on whichever one happens to be first in iteration order.

**Bounded steal attempts, then park:** spinning forever on failed steals burns a core at 100%
CPU for no throughput, which matters directly at the 380k monthly-active-client, 1,200
stakes/sec-peak scale this pool exists to serve alongside — a `MiniForkJoinPool` that pegs cores
during a quiet reconciliation window starves the actual request-serving threads on the same box.
Parking for a fixed, small, order-of-magnitude interval and re-checking trades a small amount of
steal latency for giving the scheduler room to run something else.

**Pitfall:** sizing `parallelism` above the core count "to be safe". Work-stealing pools are
CPU-bound-task pools; oversizing them past `Runtime.getRuntime().availableProcessors()` only adds
context-switch overhead with no additional real parallelism, unlike an I/O-bound thread pool (file
5 of this set) where oversizing past core count is often correct.

**Interview:** "why randomised victim selection instead of round-robin in a work-stealing pool?" —
round-robin makes every simultaneously-idle worker converge on the same victim first, concentrating
exactly the contention the per-worker-deque design exists to avoid; randomisation spreads steal
attempts across victims so contention scales with how much work is actually available, not with
iteration order.

> **`MiniForkJoinPool`** is a fixed set of worker threads, each owning one growable work-stealing
> deque, where an idle worker steals from a uniformly random other worker's deque a bounded number
> of times before parking briefly, so idle capacity finds available work without a shared
> contention point.

## Pitfalls

### Clearing vacated slots during a grow, "to help the GC"

**Wrong**

```java
private void growToBroken(int oldCapacity, int t, long b) {
    AtomicReferenceArray<T> oldArr = tasks;
    AtomicReferenceArray<T> newArr = new AtomicReferenceArray<>(oldCapacity * 2);
    int newMask = oldCapacity * 2 - 1;
    for (long i = b; i < t; i++) {
        int oldIdx = (int) (i & (oldCapacity - 1));
        newArr.set((int) (i & newMask), oldArr.get(oldIdx));
        oldArr.set(oldIdx, null); // looks tidy, silently breaks a concurrent thief
    }
    this.mask = newMask;
    this.tasks = newArr;
}
```

A thief that read `tasks` into a local *before* the reassignment, then reads its target slot
*after* this loop clears it, gets `null` from a slot the (now-superseded) array legitimately held
data in moments earlier, and — depending on how the caller interprets a null read from inside
`[base, top)` — can wrongly conclude the deque is empty and give up on a task that was never
actually consumed by anyone.

**Right**

Never clear the old array. Let it become garbage naturally once no thief holds a reference to it —
the JVM's ordinary GC handles that without help, and the fixed `steal()` above treats a `null` read
inside `[base, top)` as "retry with a fresh snapshot," not as "empty."

**Why people believe it:** clearing a vacated reference looks like good hygiene — it is the
textbook advice for, say, `ArrayList.remove` avoiding memory leaks — but that advice assumes no
other thread still holds a reference to the slot being cleared, which is exactly the assumption a
concurrent thief violates here.

## Cheat sheet

| Concern | Fixed-size deque (file 1) | Growable deque (this file) |
|---|---|---|
| Backing storage | one `AtomicReferenceArray`, fixed | `volatile AtomicReferenceArray` reference, swapped on grow |
| Grow trigger | n/a | `top - base >= mask` inside `pushTop` |
| Old array on grow | n/a | left untouched, never cleared |
| Thief on stale array | n/a | retries via `steal()`'s loop, never reports false-empty |
| Victim selection in the pool | n/a | uniform random over all other workers, not round-robin |
| Idle behaviour | n/a | bounded steal attempts, then `parkNanos` |
| Sizing rule | n/a | parallelism ≈ core count, not oversized |

## Self-test

**Q1.** Why must the new array's `mask` field be published no later than the new array reference
itself, and what would break if the order were reversed?

<details><summary>Answer</summary>

A thief reads `mask` and `tasks` as two separate fields, not atomically as one struct. If the new,
larger `mask` became visible before the new `tasks` reference did, a thief could compute an index
using the new (larger) mask against the *old* (smaller) array, producing an index that either
aliases the wrong slot or exceeds the old array's bounds. Publishing the array first and the mask
second (as the code does, `this.mask = newMask; this.tasks = newArr;` — mask first, array
last) ensures a thief that observes the new array has also already observed the mask that fits it.

</details>

**Q2.** Why does `steal()` retry on a `null` read instead of treating it as "empty," while `popTop`
never needs an equivalent retry loop?

<details><summary>Answer</summary>

`popTop` runs only on the owner thread, the same thread that performs every grow, so it can never
observe a torn or stale view of its own array — there is no concurrency between the owner and
itself. A thief can observe a `null` slot inside `[base, top)` purely because of a grow racing with
its read of a stale array snapshot; retrying re-aligns its view of `tasks` and `mask` to a single
consistent pair before concluding anything.

</details>

**Q3.** Why is victim selection bounded to a fixed number of attempts (`STEAL_ATTEMPTS_BEFORE_BACKOFF`)
rather than looping until a steal succeeds?

<details><summary>Answer</summary>

If every deque is genuinely empty, an unbounded retry loop spins a core at 100% doing no useful
work and starving anything else scheduled on that core. A bounded number of attempts followed by a
short park lets the worker yield the core back to the scheduler while still checking back
frequently enough that real latency added to picking up new work stays in the sub-millisecond
range.

</details>

**Q4.** Two `ledger-reconcile` workers both go idle at the same instant and both randomly pick
worker 2 as their first victim. What happens, and is it a bug?

<details><summary>Answer</summary>

Both call `deques[2].steal()` concurrently; the underlying deque's single CAS on `base` (from file
1) arbitrates it exactly as designed — one succeeds, one's CAS fails and it moves on to its next
random victim in the same `for` loop iteration. This is expected, occasional contention, not a
bug; randomisation makes simultaneous convergence on the same victim rare rather than the default
case round-robin would produce.

</details>

**Q5.** Why does `MiniForkJoinPool` size `parallelism` near the core count instead of oversizing it
the way an I/O-bound `ThreadPoolExecutor` from file 5 typically is?

<details><summary>Answer</summary>

Work-stealing pools are built for CPU-bound, splittable computation (the merge sort, the
`HOUSE_REVENUE` sum) where a worker is expected to be actively computing whenever it holds a task,
not blocked waiting on I/O. Extra worker threads beyond the core count add context-switch overhead
without adding real parallel compute capacity, unlike the I/O-bound case where threads spend most
of their time blocked and oversizing recovers otherwise-idle cores.

</details>

**Q6.** What does `looksQuiescent()` actually guarantee, and what is the one thing it does not
guarantee?

<details><summary>Answer</summary>

It guarantees that, at the instant each check ran, every deque appeared empty and every worker
appeared parked — a useful heuristic for "probably done." It does not guarantee that a worker
won't wake up a moment later holding a task it just forked recursively (a task created between the
quiescence check and the caller acting on the result), because the check is deliberately racy and
uses no lock to freeze the whole pool's state at one instant.

</details>

---

**Leaves covered:** 4.6.3–4.6.4 (2 leaves)
**Leaves deferred:** none
**Diagrams included:** none
**Target version:** Java 21 LTS
**Lines:** 524
