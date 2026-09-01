# 05 Multithreading and Concurrency — The two-lock queue and timed operations — BUILD IT (§4.3, leaves 4.3.3–4.3.4)

**Target version: Java 21 LTS.** | **Part 4 of 5** | [Index](../00-index.md)
Previous: [Bounded blocking queue: the monitor and condition versions](03-bounded-blocking-queue.md) · Next: [drainTo and the SPSC ring](03c-drainto-and-the-spsc-ring.md)

## Where we left off

The previous file built the bounded queue of `WithdrawalTransaction`s (capacity 1,000, feeding a
`PaymentRun`) twice: version 1 with `synchronized` + `wait`/`notifyAll` over an array ring buffer, and
version 2 with a single `ReentrantLock` and two `Condition`s — `notFull` and `notEmpty` — each waited
on with the mandatory `while (!conditionHolds()) condition.await();` loop, and each signalled with a
targeted `signal()` rather than a `signalAll()`, because only one waiter can ever make progress from a
single put or take and waking the rest would just be a thundering herd that goes straight back to
sleep. Both versions share one structural property this file is about to break: **one lock guards the
whole queue**, so a `settlement-ingest` producer thread pushing a `WithdrawalTransaction` and a
`PaymentRun` consumer thread pulling one off contend for the *same* lock even though they touch opposite
ends of the buffer.

## Version 3 vs version 2, before the code

| | Version 2 (single lock) | Version 3 (two locks) |
|---|---|---|
| What each lock guards | Everything: head, tail, count, both conditions | `putLock` guards tail-side state (`last`, `notFull`); `takeLock` guards head-side state (`head`, `notEmpty`) |
| Who contends with whom | Every producer vs every consumer vs every other producer/consumer | Producers contend only with other producers (`putLock`); consumers contend only with other consumers (`takeLock`). A producer and a consumer never block each other directly |
| What `count` must be | An `int` read and written only under the one lock — plain `int` is fine | Read and written by **both** sides without a shared lock — must be an `AtomicInteger` |
| New obligation this split creates | None — one lock already serializes everything | **Cascading signal**: a `put` that transitions the queue from empty to non-empty must wake a *taker*, and the taker, after removing one element, must check whether the queue is still non-empty and if so signal the *next* taker — because the putting thread holds `putLock`, not `takeLock`, and cannot itself call `notEmpty.signal()` correctly without briefly acquiring `takeLock` |

**Insight:** the two-lock split is only safe because `count` is the sole piece of state both sides need
to agree on, and `AtomicInteger` gives that agreement without either lock. Everything else — the
`Node` at the head, the `Node` at the tail — is touched by exactly one side under exactly one lock, by
construction of a singly linked list where the producer only ever appends and the consumer only ever
removes from the front.

## 4.3.3 — the two-lock queue

**Mental model first.** Picture the array-backed version 2 queue as a single shared warehouse floor
with one door guard checking everyone in and out. Version 3 replaces it with a loading dock (linked
list) that has two separate doors — a receiving door at the back and a shipping door at the front —
each with its own guard. A truck arriving to drop off cargo never has to wait behind a truck picking
cargo up, because they use different doors entirely. The only shared thing between the two doors is a
digital counter on the wall — visible from both doors, updated atomically — that says how much cargo
is currently on the floor.

**Why it exists.** Under high `settlement-ingest` throughput — 7,000 bank withdrawals a day is a mild
average, but batch submission windows spike far above the smooth rate — a single lock forces every
producer and every consumer through one serialization point even though a put and a take never touch
the same memory location on a linked structure. That's throughput left on the table for no correctness
reason. `LinkedBlockingQueue` exists in the JDK specifically because `ArrayBlockingQueue`'s single-lock
design (which is what versions 1 and 2 mirror) doesn't scale under mixed producer/consumer load, and a
linked list — unlike a fixed array — has a natural head/tail split that a single element never crosses
in the same operation.

**When to reach for it, and when not.** Reach for the two-lock shape when producers and consumers are
both numerous and you've measured lock contention on a single-lock bounded queue as the bottleneck —
this is a real optimization, not a default. Do not reach for it when the queue is low-traffic (a single
lock's overhead is noise there), when you need `O(1)` random access or a fixed memory footprint (a
`Node`-per-element linked list allocates on every put and produces GC churn an array never does — this
is `ArrayBlockingQueue`'s standing advantage over `LinkedBlockingQueue`, not something this version
fixes), or when strict FIFO fairness across *all* waiters (not just same-side waiters) matters, since
splitting the lock also splits the fairness domain.

**How it works.** Two `ReentrantLock`s, `putLock` and `takeLock`, each with its own single `Condition`
— `notFull` on `putLock`, `notEmpty` on `takeLock`. `count` is an `AtomicInteger`, read via `.get()`,
mutated via `getAndIncrement()` / `getAndDecrement()`. The list is singly linked, `head` and `last`
pointers, both touched only under their respective lock — `last` under `putLock`, `head` under
`takeLock`. The subtle part is the cascading signal: when `put` increments `count` from 0 to 1, it must
tell a waiting taker that there's now something to take — but `put` holds `putLock`, and `notEmpty` is a
condition on `takeLock`. So `put`, still outside its own lock (after releasing `putLock`), briefly
acquires `takeLock` purely to call `notEmpty.signal()`. Symmetrically, `take`, after removing an
element and decrementing `count` from capacity down to `capacity - 1`, must wake a waiting *putter* by
briefly acquiring `putLock` to call `notFull.signal()`. And inside `take` itself: after removing one
element, if `count.get() > 0` still holds (there's more for another consumer), `take` re-signals its
own `notEmpty` before releasing `takeLock` — that's the cascade that lets multiple queued takers drain
the queue one at a time without every one of them having to be individually woken by a producer.

**The diagram.** A picture here would show two lock icons, `putLock` on the tail end and `takeLock` on
the head end of a horizontal chain of `Node` boxes, with a small shared `AtomicInteger` counter drawn
floating above both, and two thin cross-arrows — one from `put`'s exit path into `takeLock`'s
`notEmpty`, one from `take`'s exit path into `putLock`'s `notFull` — labelled "signal, not owned."

```java
package com.quizstakes.payments.queue;

import java.util.concurrent.atomic.AtomicInteger;
import java.util.concurrent.locks.Condition;
import java.util.concurrent.locks.ReentrantLock;

/**
 * A bounded FIFO queue of WithdrawalTransactions feeding a PaymentRun, mirroring
 * LinkedBlockingQueue's two-lock design: putLock/takeLock split producer and
 * consumer contention onto separate locks over a singly linked list.
 */
public final class TwoLockWithdrawalQueue {

    private static final class Node {
        WithdrawalTransaction item;
        Node next;
        Node(WithdrawalTransaction item) {
            this.item = item;
        }
    }

    private final int capacity;
    private final AtomicInteger count = new AtomicInteger(0);

    private Node head;
    private Node last;

    private final ReentrantLock takeLock = new ReentrantLock();
    private final Condition notEmpty = takeLock.newCondition();

    private final ReentrantLock putLock = new ReentrantLock();
    private final Condition notFull = putLock.newCondition();

    public TwoLockWithdrawalQueue(int capacity) {
        if (capacity <= 0) {
            throw new IllegalArgumentException("capacity must be positive");
        }
        this.capacity = capacity;
        this.head = new Node(null);
        this.last = this.head;
    }

    public void put(WithdrawalTransaction withdrawal) throws InterruptedException {
        if (withdrawal == null) {
            throw new NullPointerException("withdrawal");
        }
        int previousCount;
        putLock.lockInterruptibly();
        try {
            while (count.get() == capacity) {
                notFull.await();
            }
            enqueue(withdrawal);
            previousCount = count.getAndIncrement();
            if (previousCount + 1 < capacity) {
                notFull.signal();
            }
        } finally {
            putLock.unlock();
        }
        if (previousCount == 0) {
            signalNotEmpty();
        }
    }

    public WithdrawalTransaction take() throws InterruptedException {
        WithdrawalTransaction withdrawal;
        int previousCount;
        takeLock.lockInterruptibly();
        try {
            while (count.get() == 0) {
                notEmpty.await();
            }
            withdrawal = dequeue();
            previousCount = count.getAndDecrement();
            if (previousCount > 1) {
                notEmpty.signal();
            }
        } finally {
            takeLock.unlock();
        }
        if (previousCount == capacity) {
            signalNotFull();
        }
        return withdrawal;
    }

    private void enqueue(WithdrawalTransaction withdrawal) {
        last.next = new Node(withdrawal);
        last = last.next;
    }

    private WithdrawalTransaction dequeue() {
        Node first = head.next;
        head.next = null;
        head = first;
        WithdrawalTransaction withdrawal = first.item;
        first.item = null;
        return withdrawal;
    }

    private void signalNotEmpty() {
        takeLock.lock();
        try {
            notEmpty.signal();
        } finally {
            takeLock.unlock();
        }
    }

    private void signalNotFull() {
        putLock.lock();
        try {
            notFull.signal();
        } finally {
            putLock.unlock();
        }
    }

    public int size() {
        return count.get();
    }
}
```

**The gotcha.** It is tempting to signal `notEmpty` while still holding `putLock` — but `notEmpty` is a
`Condition` created *from* `takeLock`, and calling `signal()` on a condition from any lock other than
the one that created it throws `IllegalMonitorStateException`. The cross-signal must release its own
lock's grip on the state it needed (nothing left to guard at that point — `withdrawal` is already
enqueued) and separately acquire the *other* lock just to make the call. **Pitfall:** a version that
tries to fold `signalNotEmpty()` inside the `putLock` block, hoping to "save a lock acquisition,"
crashes immediately on the first successful transition from empty to non-empty — the fix is exactly
the structure above, where the cross-signal happens strictly after `putLock.unlock()` in the `finally`
has already run.

**Interview:** "Why does `LinkedBlockingQueue` need `count` to be atomic when `ArrayBlockingQueue`
doesn't?" — because `ArrayBlockingQueue` has one lock guarding every read and write of `count`, while
`LinkedBlockingQueue` has two, so `count` is the only variable crossing the lock boundary and needs its
own concurrency-safe home.

> The two-lock queue splits a bounded FIFO's put-side and take-side critical sections onto independent
> locks over a linked list, trading a single `AtomicInteger` handoff and a cross-lock cascading signal
> for producer/consumer lock contention that no longer exists.

### Diff vs the real `LinkedBlockingQueue`

**Unverified:** the exact field names and the presence of `fullyLock()`/`fullyUnlock()` below are
stated from memory of the JDK source and were not re-verified against a fetched copy of
`LinkedBlockingQueue.java` in this session — treat the mechanism claims as reliable and the identifier
spelling as approximate.

| Aspect | This build | The real `LinkedBlockingQueue` |
|---|---|---|
| Bounds/state checks | `capacity <= 0` rejected in constructor; null rejected in `put` | Same, plus rejects `Integer.MAX_VALUE`-adjacent overflow paths in bulk constructors |
| Cascading signal | Manual: `put`/`take` cross-acquire the other lock once on a 0→1 or capacity→capacity-1 transition | Same shape — `signalNotEmpty()`/`signalNotFull()` helper methods, same cross-lock acquire pattern |
| `size()`/multi-field ops | `count.get()`, no `fullyLock` | Real class provides `fullyLock()`/`fullyUnlock()` (acquires both locks in fixed order) for operations touching both ends at once, e.g. `remove(Object)`, `toString()`, iteration snapshot |
| Serialization, `Spliterator` | Not implemented here | `LinkedBlockingQueue` implements `Serializable` and provides a late-binding, weakly consistent `Spliterator` |
| Why the JDK bothers | Demonstrates the split | Real workloads (thread pool work queues, `LinkedBlockingQueue`-backed pipelines) run with high producer *and* consumer counts, where single-lock contention is measurable — order-of-magnitude, a park/unpark round trip is thousands of nanoseconds, so avoiding one contended lock per element under load is a real win, not a micro-optimization |

## 4.3.4 — timed `offer`/`poll` with a correct `awaitNanos` deadline loop

**Mental model first.** A blocking `put`/`take` is a guest willing to wait at the door forever. A timed
`offer`/`poll` is the same guest, but now checking their watch — they'll wait, but if the door hasn't
opened by a fixed clock time, they leave. The subtlety is entirely in how "checking their watch" is
implemented: check it once against an unmoving deadline, or naively reset the same waiting budget every
time you're disturbed and end up waiting far longer than you meant to.

**Why it exists.** A `settlement-ingest` producer trying to `offer` a `WithdrawalTransaction` onto a
full queue, or a `PaymentRun` worker trying to `poll` an empty one, sometimes needs a bound on how long
it will wait rather than blocking indefinitely — the standing example in this queue's domain is the
30 s watchlist provider timeout: if a downstream compliance screen for a withdrawal hasn't returned
within its budget, the caller must not be stuck in `take()` forever waiting for work that assumes the
screen succeeded. Before `Condition` offered `awaitNanos`, the only tool was `Object.wait(long millis)`,
which has the exact same remaining-time trap described below, just with milliseconds and no return
value at all — the caller had no way to know whether the wait ended because of a timeout or a spurious
wakeup.

**When to reach for it, and when not.** Reach for timed `offer`/`poll` whenever a caller has an SLA it
must not blow through waiting on a queue — request-handling paths, anything gated by an external
timeout like the watchlist provider's own 30 s ceiling. Do not reach for it as a substitute for correct
shutdown signalling: a poison pill or `interrupt()` is the right way to make a consumer thread exit
cleanly (§4.3, `queues/01`, `[X-REF]` day covering poison pills); a timed poll that simply returns
`null` on timeout still needs the caller to decide what "no work arrived" means, and looping a timed
poll purely to simulate cancellation is worse than calling `interrupt()` directly.

**How it works.** `Condition.awaitNanos(long nanosTimeout)` returns `long` — an *estimate* of the
remaining time in nanoseconds, or a value `<= 0` if it timed out. Like plain `await()`, it can return
early due to a spurious wakeup, and unlike a fixed-budget sleep, calling it again with the *original*
timeout on every loop iteration is the trap: each spin resets the clock, so an unlucky sequence of
spurious wakeups can make the effective wait balloon to many multiples of the requested timeout, or in
the worst case never actually expire under sustained spurious signalling. The correct form computes an
absolute deadline once with `System.nanoTime()`, then on every loop iteration re-derives the *remaining*
time from that fixed deadline and feeds `awaitNanos` its own returned remaining-nanos value, looping
while `count.get() == capacity` (or `== 0` for poll) and remaining time is still positive. `[TRAP]`

**The diagram.** A picture here would show two timelines stacked: the wrong version's timeline
restarting a full-length bar at every spurious wakeup tick mark, versus the right version's timeline
showing one fixed-length bar from start to `deadline`, with each spin only consuming from what's left.

```java
package com.quizstakes.payments.queue;

import java.util.concurrent.TimeUnit;

// Continuation of TwoLockWithdrawalQueue: timed offer/poll.
public final class TimedWithdrawalQueueOps {

    // WRONG — re-passes the original timeout on every loop iteration.
    // A spurious wakeup, or a signal for a condition that's still false
    // (another thread grabbed the last slot first), resets the budget
    // instead of consuming it: this can wait far longer than 30 seconds.
    public static WithdrawalTransaction pollWrong(
            TwoLockWithdrawalQueueInternals q, long timeout, TimeUnit unit)
            throws InterruptedException {
        long nanosTimeout = unit.toNanos(timeout);
        q.takeLock().lockInterruptibly();
        try {
            while (q.count().get() == 0) {
                if (nanosTimeout <= 0) {
                    return null;
                }
                // BUG: always awaits the full original budget again.
                q.notEmpty().awaitNanos(nanosTimeout);
            }
            return q.dequeueForTest();
        } finally {
            q.takeLock().unlock();
        }
    }

    // RIGHT — one fixed deadline, computed once from System.nanoTime(),
    // and awaitNanos is fed its own returned remaining-time estimate.
    public static WithdrawalTransaction pollRight(
            TwoLockWithdrawalQueueInternals q, long timeout, TimeUnit unit)
            throws InterruptedException {
        long remainingNanos = unit.toNanos(timeout);
        long deadline = System.nanoTime() + remainingNanos;
        q.takeLock().lockInterruptibly();
        try {
            while (q.count().get() == 0) {
                if (remainingNanos <= 0L) {
                    return null;
                }
                remainingNanos = q.notEmpty().awaitNanos(remainingNanos);
            }
            WithdrawalTransaction withdrawal = q.dequeueForTest();
            int previousCount = q.count().getAndDecrement();
            if (previousCount > 1) {
                q.notEmpty().signal();
            }
            if (previousCount == q.capacity()) {
                q.signalNotFullForTest();
            }
            return withdrawal;
        } finally {
            q.takeLock().unlock();
            // Overflow-safe deadline check for any caller-side retry wrapper:
            // never write `System.nanoTime() > deadline` — nanoTime can wrap.
            boolean expired = System.nanoTime() - deadline >= 0;
            assert expired || remainingNanos > 0
                : "loop exited without timing out or finding an item";
        }
    }
}
```

**Pitfall:** `pollWrong` looks correct in every manual test, because manual tests don't produce the
adversarial sequence of near-simultaneous spurious wakeups and lost races that production concurrency
does at 7,000 withdrawals/day peak-batched load. The symptom in production is a `poll` call that was
meant to bound wait time to the 30 s watchlist timeout instead blocking for minutes, because every
spurious return re-armed a fresh 30-second budget. **Why people believe `pollWrong` is fine:** the
JavaDoc for `awaitNanos` says it returns an estimate of remaining time, and it's easy to read "pass the
timeout, get told if you're late" as sufficient, missing that the *loop* is what needs the estimate fed
back in, not the single call.

**Interview:** "What's wrong with `if (!condition.await(timeout, unit)) return null;` used directly as
the wait?" — it treats a single `await` call as sufficient, but `await` can return `true` (not timed
out) on a spurious wakeup with the predicate still false, so the very next check must re-verify the
predicate in a loop — and once it's a loop, the timeout budget must be tracked against a fixed
deadline, not reissued whole on every pass. `[VERSION-TRAP]`: this shape is unchanged Java 22–25 — no
JEP has altered `Condition.awaitNanos`'s remaining-time contract or the JLS's permission for spurious
wakeups.

> A correct timed wait computes its deadline once with `System.nanoTime()`, loops while the predicate
> is false and time remains, and on each iteration feeds the primitive its own last-returned remaining
> time rather than the original timeout — never checked with `>`, always with the overflow-safe
> `System.nanoTime() - deadline >= 0`.

### Diff vs the real `LinkedBlockingQueue.offer`/`poll(timeout, unit)`

| Aspect | This build | The real `LinkedBlockingQueue` |
|---|---|---|
| Deadline basis | `System.nanoTime()` once, `awaitNanos` fed the returned remainder | Identical pattern — the JDK's own timed `poll`/`offer` use exactly this deadline-and-remainder loop internally |
| Cancellation | `lockInterruptibly()` propagates `InterruptedException` out of the timed call | Same — timed `poll`/`offer` are declared to throw `InterruptedException` |
| Memory ordering | `AtomicInteger` (volatile CAS) for `count`; `Condition` await/signal for happens-before on enqueue/dequeue | Same primitives, same ordering guarantees |
| Fairness | Non-fair `ReentrantLock`s (default) | Non-fair by default; the real class offers no fairness constructor parameter — bounded queues generally accept fairness must be handled by the caller if needed |
| Null policy | Rejects `null` in `put`, would need the same guard added to a full `offer` | Rejects `null` uniformly across all insertion methods, throwing `NullPointerException` |

The full consolidated diff table across every version built in §4.3 lands in
`03d-queue-consolidated-diff.md`.

## Open questions

- **Unverified:** field and helper-method names (`fullyLock`/`fullyUnlock`, exact `Node` shape) in the
  real `LinkedBlockingQueue` were stated from recollection rather than a freshly fetched copy of
  `LinkedBlockingQueue.java` at the `jdk-21` tag in this session. The mechanism-level claims (two locks,
  atomic count, cascading signal, deadline-based timed wait) are standard and stable across JDK major
  versions, but exact identifiers should be re-checked against `raw.githubusercontent.com`'s
  `openjdk/jdk` mirror at tag `jdk-21-ga` before treating them as quotable source text.

## Pitfalls

### Signalling `notEmpty` while still holding `putLock`

**Wrong**

```java
public void put(WithdrawalTransaction withdrawal) throws InterruptedException {
    putLock.lockInterruptibly();
    try {
        while (count.get() == capacity) {
            notFull.await();
        }
        enqueue(withdrawal);
        count.getAndIncrement();
        notEmpty.signal(); // IllegalMonitorStateException: notEmpty belongs to takeLock
    } finally {
        putLock.unlock();
    }
}
```

**Right**

```java
// See put() above: release putLock first, then separately
// acquire takeLock only to call notEmpty.signal(), only when
// the 0-to-1 transition actually happened.
```

**Why people believe it:** in the single-lock version 2, signalling any condition from inside the one
held lock is exactly correct, so the two-lock split's requirement to signal a condition from a
*different* lock than the one just released reads like an arbitrary extra step rather than a hard
requirement — until `IllegalMonitorStateException` at runtime makes the ownership rule concrete.

### Re-arming the original timeout on every `awaitNanos` loop iteration

**Wrong**

```java
long nanosTimeout = unit.toNanos(timeout);
while (count.get() == 0) {
    if (nanosTimeout <= 0) return null;
    notEmpty.awaitNanos(nanosTimeout); // always waits up to the full budget again
}
```

**Right**

```java
long remaining = unit.toNanos(timeout);
long deadline = System.nanoTime() + remaining;
while (count.get() == 0) {
    if (remaining <= 0L) return null;
    remaining = notEmpty.awaitNanos(remaining);
}
```

**Why people believe it:** the variable is already named for the timeout, and passing "the timeout" to
a method literally called `awaitNanos(timeout)` looks self-evidently correct — the bug only shows up
under repeated spurious wakeups or repeated false-predicate signals, which don't appear in a quick
manual test.

## Cheat sheet

| Fact | Value |
|---|---|
| Locks in version 3 | `putLock` (tail side), `takeLock` (head side) |
| Shared state needing atomicity | `count` — `AtomicInteger` |
| Signal on 0→1 transition | `put` cross-acquires `takeLock`, calls `notEmpty.signal()` |
| Signal on capacity→capacity-1 transition | `take` cross-acquires `putLock`, calls `notFull.signal()` |
| Cascading signal inside `take` | If `count` after decrement still `> 0`, re-signal own `notEmpty` for the next waiter |
| Deadline basis | `System.nanoTime()`, computed once |
| Correct comparison | `System.nanoTime() - deadline >= 0` (overflow-safe) — never `>` |
| What `awaitNanos` returns | Remaining nanos estimate, or `<= 0` if timed out |
| Loop input on each spin | The *last returned* remaining value, never the original timeout |
| Worked domain example | Timed `poll` bounded by the 30 s watchlist provider timeout |

## Self-test

**Q1.** Why must `count` be an `AtomicInteger` in the two-lock version but a plain `int` was fine in
the single-lock version?

<details><summary>Answer</summary>

In the single-lock version, every read and write of `count` happens under the one lock that also
guards the buffer, so the lock's happens-before edges already make plain-`int` access safe and
consistent. In the two-lock version, `put` (under `putLock`) and `take` (under `takeLock`) both need to
read and update `count` without sharing a lock, so `count` is the one piece of state crossing the lock
boundary — it needs its own concurrency-safe implementation, which `AtomicInteger` provides via CAS and
volatile semantics.

</details>

**Q2.** A `put` call transitions the queue from 3 items to 4, out of a capacity of 1,000. Does it need
to signal anything?

<details><summary>Answer</summary>

No cross-lock signal is needed for `notEmpty` (the queue was already non-empty before this put, so any
waiting taker was already signalled or never needed signalling), and no `notFull` signal applies either
since that's what `put` itself would wait on, not signal. The only signal `put` performs is `notFull`
signalled *by a taker*, and `notEmpty` signalled *by put* only on the 0→1 transition — 3→4 is neither,
so this particular `put` cross-signals nothing.

</details>

**Q3.** Why can't `put` call `notEmpty.signal()` directly while still holding `putLock`?

<details><summary>Answer</summary>

`notEmpty` is a `Condition` object created by `takeLock.newCondition()`, and the JLS/`Condition`
contract requires the calling thread to hold the lock that condition was created from before calling
`await`, `signal`, or `signalAll` on it — calling it while holding a different lock (`putLock`) throws
`IllegalMonitorStateException`. `put` must release `putLock` and separately acquire `takeLock` purely
to make the cross-signal call.

</details>

**Q4.** What specifically goes wrong with `if (!notEmpty.await(timeout, unit)) return null;` used as
the entire wait, with no surrounding loop?

<details><summary>Answer</summary>

`await(timeout, unit)` can return `true` (meaning "not timed out") on a spurious wakeup even though the
predicate the caller actually cares about — the queue being non-empty — is still false, for example
because another consumer grabbed the last item first. Treating a `true` return as "the item is there"
without re-checking the predicate in a loop is the same lost-update class of bug that a plain
`if (empty) wait();` has instead of `while (empty) wait();`.

</details>

**Q5.** Given a 30-second timed `poll` and a sequence of five spurious wakeups spaced 2 seconds apart,
compare the total wait time under the wrong deadline handling versus the right one.

<details><summary>Answer</summary>

Under the wrong handling, each spurious wakeup causes `awaitNanos` to be reinvoked with the *original*
30-second budget, so five wakeups at 2-second intervals produce roughly five separate near-30-second
waits chained together — on the order of 2 or 3 minutes total before the loop can even reach a real
timeout, far exceeding the intended 30 s SLA. Under the right handling, the fixed deadline means each
`awaitNanos` call only gets what's left of the original 30 seconds, so the total wait across all five
wakeups is still bounded by 30 seconds from the initial call, regardless of how many spurious
wakeups occur in between.

</details>

**Q6.** Why does the two-lock design help throughput specifically for a `settlement-ingest` producer
and a `PaymentRun` consumer running concurrently, but not for two producers running concurrently?

<details><summary>Answer</summary>

Two producers both call `put`, which both need `putLock` — they still serialize against each other,
exactly as they would under the single-lock version. The throughput win is specifically between a
producer and a consumer, who under the single-lock version contended for the one shared lock despite
touching opposite ends of the queue; under the two-lock version they acquire different locks
(`putLock` vs `takeLock`) and no longer block each other for that part of the operation, only briefly
crossing over for the cascading signal on an empty-to-non-empty or full-to-non-full transition.

</details>

**Q7.** What is the order-of-magnitude cost this design change is trying to avoid, and how is that
figure qualified?

<details><summary>Answer</summary>

It is trying to avoid unnecessary contended-lock acquisitions that force a thread to park and later be
unparked by the OS scheduler — a park/unpark round trip costs on the order of low microseconds to
occasionally much more under scheduler pressure, an order-of-magnitude figure only, not a measured
number for any specific JVM or hardware in this note set; the real fix is architectural (splitting the
lock) rather than trying to shave a constant off any single wait.

</details>

**Q8.** Why is `System.nanoTime() - deadline >= 0` the correct comparison instead of
`System.nanoTime() > deadline`?

<details><summary>Answer</summary>

`System.nanoTime()`'s absolute value can wrap around the `long` range over a long-running JVM, and a
direct `>` comparison breaks exactly at that wraparound because a wrapped, numerically smaller
`nanoTime()` would incorrectly compare as "not yet past deadline" or vice versa depending on which side
wrapped. Subtracting and comparing to zero is wraparound-safe because two's-complement subtraction of
two nearby wrapped values still produces the correct signed difference, which is the same trick
`System.nanoTime()`'s own JavaDoc recommends for any deadline comparison.

</details>

---

**Leaves covered:** 4.3.3–4.3.4 (2 leaves)
**Leaves deferred:** none
**Diagrams included:** none
**Target version:** Java 21 LTS
**Lines:** 450
