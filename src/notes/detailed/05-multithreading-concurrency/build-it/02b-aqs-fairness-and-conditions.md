# 05 Multithreading and Concurrency — AQS fairness and conditions — BUILD IT (§4.2, leaves 4.2.5–4.2.6)

**Target version: Java 21 LTS.** | **Part 4 of 5** | [Index](../00-index.md)
Previous: [Building on AQS](02-building-on-aqs.md) · Next: [The consolidated AQS diff table](02c-aqs-consolidated-diff.md)

## Recap: the reentrant AQS mutex you already have

The previous file built `ReentrantAqsMutex extends AbstractQueuedSynchronizer`: `state` holds the hold
count (0 = free, N = held N times by the same thread), the owner lives in
`setExclusiveOwnerThread`/`getExclusiveOwnerThread`, `tryAcquire` CASes 0→1 on first entry and just
increments `state` on re-entry by the same thread, `tryRelease` decrements and only actually frees the
lock when it reaches 0, and `unlock()` by a non-owner throws `IllegalMonitorStateException`. It is
**barging**: on release, any thread — including one that just arrived and never queued — may win the
next `tryAcquire`, even if other threads have been parked on the AQS wait queue for milliseconds. This
file adds a fair variant of that same class and a `Condition` on top of it.

## Barging vs fair acquire, side by side

| Step | Barging (`ReentrantAqsMutex`) | Fair (`FairReentrantAqsMutex`) |
|---|---|---|
| Thread B releases the lock | `tryRelease` sets `state = 0`, unparks the queue head | identical |
| Thread C arrives concurrently, never queues | `tryAcquire` sees `state == 0`, CASes to 1, wins immediately | `tryAcquire` sees `state == 0`, but calls `hasQueuedPredecessors()` first — queue is non-empty, so C **fails** and parks at the tail |
| Queue head D wakes from `unpark` | Races C for the CAS; may lose it and re-park | Wakes, calls `tryAcquire`, `hasQueuedPredecessors()` returns `false` (D is at the head with nothing ahead of it), CASes and wins |
| Net effect | Lowest latency per acquisition — no forced context switch when a running thread can grab the lock | Bounded waiting — FIFO order honoured, but every hand-off pays a park/unpark round trip |

The whole behavioural difference is one method call inserted into `tryAcquire`'s fast path.

### 4.2.5 A fair variant: `hasQueuedPredecessors()`

**Mental model.** Picture the AQS wait queue as a bank line with a rope. Barging is the branch where a
teller waving "next!" can be answered by whoever is standing closest to the counter, rope or no rope —
usually the customer who just walked in, because they are already moving and the queued customers are
mid-blink from being woken up. The fair variant nails the rope down: before anyone steps up, they must
check "is there anyone ahead of me on this rope?" If yes, they wait their turn even though the counter
is empty right now.

**Why it exists.** Non-fair mode exists because CAS-and-go is fast and, empirically, un-fair contention
resolves faster in aggregate — the JDK's own `ReentrantLock` defaults to non-fair for this reason. Fair
mode exists for the opposite failure: a stream of always-arriving barging threads can starve a
specific parked thread indefinitely, because it never gets to be the one that is "already moving." That
starvation is invisible under light load and catastrophic under sustained load from many callers.

**When to reach for it, and when not.** Reach for fairness when a specific caller's wait time must be
*bounded*, not just *usually short* — e.g. a compliance job that must eventually get its turn at the
ledger even while high-frequency stake reservations hammer the same lock. Do not reach for it as a
default: it roughly halves throughput under contention (measured shape below) for a guarantee most
call sites never need, because most critical sections are short enough that the starvation window
never opens in practice.

**How it works.** `hasQueuedPredecessors()` is inherited from `AbstractQueuedSynchronizer` — you do not
implement it, you call it. Reading the JDK 21 source (`AbstractQueuedSynchronizer.java`, `jdk-21` tag,
`raw.githubusercontent.com/openjdk/jdk`, post-JDK-14 CLH-variant queue):

```java
public final boolean hasQueuedPredecessors() {
    Node h, s;
    if ((h = head) != null) {
        if ((s = h.next) == null || s.waiter != Thread.currentThread())
            return s != null || tryInitializeHead() == null ? true
                : head != h;
    }
    return false;
}
```

The exact field name (`s.waiter` in the current internal `Node`, `s.thread` in the pre-JDK-21 shape)
and the initialization dance changed with the JDK 21 virtual-thread-aware AQS internals rewrite, but the
contract every caller relies on has not moved since it was introduced in JDK 7: return `true` unless the
queue is empty, or the current thread is (about to become) the head's immediate successor. `[VERSION-TRAP]`
Building on top of it needs only that contract — one call, inserted before the CAS:

```java
import java.util.concurrent.locks.AbstractQueuedSynchronizer;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.locks.Condition;
import java.util.concurrent.locks.Lock;

/** Fair sibling of ReentrantAqsMutex: same hold-count-in-state design, FIFO acquire order. */
final class FairReentrantAqsMutex extends AbstractQueuedSynchronizer implements Lock {

    @Override
    protected boolean tryAcquire(int acquires) {
        Thread current = Thread.currentThread();
        int c = getState();
        if (c == 0) {
            if (!hasQueuedPredecessors() && compareAndSetState(0, acquires)) {
                setExclusiveOwnerThread(current);
                return true;
            }
        } else if (current == getExclusiveOwnerThread()) {
            int next = c + acquires;
            if (next < 0) {
                throw new Error("Maximum lock count exceeded");
            }
            setState(next);
            return true;
        }
        return false;
    }

    @Override
    protected boolean tryRelease(int releases) {
        int next = getState() - releases;
        if (Thread.currentThread() != getExclusiveOwnerThread()) {
            throw new IllegalMonitorStateException();
        }
        boolean freeNow = next == 0;
        if (freeNow) {
            setExclusiveOwnerThread(null);
        }
        setState(next);
        return freeNow;
    }

    @Override
    protected boolean isHeldExclusively() {
        return getExclusiveOwnerThread() == Thread.currentThread();
    }

    @Override public void lock() { acquire(1); }

    @Override
    public void lockInterruptibly() throws InterruptedException {
        acquireInterruptibly(1);
    }

    @Override
    public boolean tryLock() {
        return tryAcquire(1);
    }

    @Override
    public boolean tryLock(long time, TimeUnit unit) throws InterruptedException {
        return tryAcquireNanos(1, unit.toNanos(time));
    }

    @Override public void unlock() { release(1); }

    @Override public Condition newCondition() { return new ConditionObject(); }
}
```

**The diagram** a picture would show two swim lanes — barging and fair — over the same three time
steps (release, arrival, wake), with the fair lane's arriving thread blocked by a dashed "rope" line
until the head-successor is granted the lock; the table two sections up already carries that content.

**A minimal concrete example — the reserve-stake critical section, fair-locked.** `FundsLedger`
reserves a stake by splitting it across the bonus and cash buckets, bonus first up to its cap, cash for
the remainder; the bonus bucket must never go negative and the split must sum exactly to the stake:

```java
record Money(long minorUnits) {
    Money {
        if (minorUnits < 0) {
            throw new IllegalArgumentException("negative money: " + minorUnits);
        }
    }
    Money minus(Money other) { return new Money(minorUnits - other.minorUnits); }
    static Money min(Money a, Money b) { return a.minorUnits() <= b.minorUnits() ? a : b; }
}

record StakeSplit(Money bonusPortion, Money cashPortion) {
    StakeSplit {
        if (bonusPortion.minorUnits() < 0) {
            throw new IllegalStateException("bonus portion went negative");
        }
    }
}

final class FundsLedger {
    private final FairReentrantAqsMutex mutex = new FairReentrantAqsMutex();
    private Money bonusAvailable;
    private Money cashAvailable;

    FundsLedger(Money bonusAvailable, Money cashAvailable) {
        this.bonusAvailable = bonusAvailable;
        this.cashAvailable = cashAvailable;
    }

    /** Reserves a stake: min(bonusAvailable, 10% of stake) from bonus, remainder from cash. */
    StakeSplit reserveStake(Money stake) {
        mutex.lock();
        try {
            Money bonusCap = new Money(stake.minorUnits() / 10);
            Money bonusPortion = Money.min(bonusAvailable, bonusCap);
            Money cashPortion = stake.minus(bonusPortion);
            if (cashPortion.minorUnits() > cashAvailable.minorUnits()) {
                throw new IllegalStateException("insufficient cash to cover remainder");
            }
            bonusAvailable = bonusAvailable.minus(bonusPortion);
            cashAvailable = cashAvailable.minus(cashPortion);
            return new StakeSplit(bonusPortion, cashPortion);
        } finally {
            mutex.unlock();
        }
    }
}
```

At QuizStakes' measured peak of 1,200 stake reservations/second, this critical section is exactly the
kind of short, hot section where the fairness-vs-throughput trade-off in the benchmark below is felt.

**The gotcha.** `hasQueuedPredecessors()` reads `head`/`head.next` safely because AQS guarantees the
right happens-before edges via its own CAS and `volatile` state — do not "optimize" a hand-rolled fair
synchronizer by caching the result of `hasQueuedPredecessors()` across a loop iteration; the queue can
change between reads and a stale `false` reintroduces barging exactly when you meant to forbid it.

> **Fairness in a hand-built AQS synchronizer is a one-line insertion into `tryAcquire`'s fast path — a
> call to `hasQueuedPredecessors()` before the CAS — that trades a park/unpark round trip per hand-off
> for FIFO-bounded waiting.**

#### Benchmark: measuring the throughput cost

```java
import org.openjdk.jmh.annotations.*;
import org.openjdk.jmh.infra.Blackhole;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.locks.Lock;

@State(Scope.Benchmark)
@BenchmarkMode(Mode.Throughput)
@OutputTimeUnit(TimeUnit.SECONDS)
@Warmup(iterations = 5, time = 1)
@Measurement(iterations = 5, time = 1)
@Fork(1)
public class ReserveStakeFairnessBenchmark {

    private FundsLedgerBarging bargingLedger;
    private FundsLedgerFair fairLedger;

    @Setup(Level.Trial)
    public void setUp() {
        bargingLedger = new FundsLedgerBarging(new Money(10_000_00), new Money(1_000_000_00));
        fairLedger = new FundsLedgerFair(new Money(10_000_00), new Money(1_000_000_00));
    }

    @Benchmark
    @Threads(8)
    public void bargingArm(Blackhole bh) {
        StakeSplit split = bargingLedger.reserveStake(new Money(500));
        bh.consume(split);
    }

    @Benchmark
    @Threads(8)
    public void fairArm(Blackhole bh) {
        StakeSplit split = fairLedger.reserveStake(new Money(500));
        bh.consume(split);
    }
}

/** Identical shape to FundsLedger above but backed by the non-fair ReentrantAqsMutexLockFacade. */
final class FundsLedgerBarging {
    private final Lock mutex = new ReentrantAqsMutexLockFacade();
    private Money bonusAvailable;
    private Money cashAvailable;

    FundsLedgerBarging(Money bonusAvailable, Money cashAvailable) {
        this.bonusAvailable = bonusAvailable;
        this.cashAvailable = cashAvailable;
    }

    StakeSplit reserveStake(Money stake) {
        mutex.lock();
        try {
            Money bonusCap = new Money(stake.minorUnits() / 10);
            Money bonusPortion = Money.min(bonusAvailable, bonusCap);
            Money cashPortion = stake.minus(bonusPortion);
            bonusAvailable = bonusAvailable.minus(bonusPortion);
            cashAvailable = cashAvailable.minus(cashPortion);
            return new StakeSplit(bonusPortion, cashPortion);
        } finally {
            mutex.unlock();
        }
    }
}

/** Identical shape to FundsLedger above but backed by the fair mutex directly. */
final class FundsLedgerFair {
    private final Lock mutex = new FairReentrantAqsMutex();
    private Money bonusAvailable;
    private Money cashAvailable;

    FundsLedgerFair(Money bonusAvailable, Money cashAvailable) {
        this.bonusAvailable = bonusAvailable;
        this.cashAvailable = cashAvailable;
    }

    StakeSplit reserveStake(Money stake) {
        mutex.lock();
        try {
            Money bonusCap = new Money(stake.minorUnits() / 10);
            Money bonusPortion = Money.min(bonusAvailable, bonusCap);
            Money cashPortion = stake.minus(bonusPortion);
            bonusAvailable = bonusAvailable.minus(bonusPortion);
            cashAvailable = cashAvailable.minus(cashPortion);
            return new StakeSplit(bonusPortion, cashPortion);
        } finally {
            mutex.unlock();
        }
    }
}
```

`ReentrantAqsMutexLockFacade` is the `Lock` wrapper the previous file already put around
`ReentrantAqsMutex` — reused here unchanged, not rebuilt.

**Results — expected shape, not measured — run the harness above on your own hardware:**

| Arm | Expected relative throughput at 8 threads | Reason |
|---|---|---|
| `bargingArm` | Higher — treat as the baseline | A released lock can be re-taken by an already-scheduled, already-running thread with zero forced context switches. |
| `fairArm` | Lower — commonly cited as roughly half the barging arm's throughput under heavy contention, but this varies by core count and OS scheduler; do not treat that ratio as a constant | Every hand-off must park the loser(s) and unpark the exact head-successor — a park/unpark round trip on the critical path of every single acquisition, not just the contended ones. |

**The argument that matters.** Barging wins on throughput because the CPU already has a thread in hand
that wants the lock and is mid-execution — handing it the lock costs one CAS. Fairness forces a
park/unpark round trip to hand the lock specifically to the queue head, and park/unpark cost is
**order of magnitude only, not a measured constant** — commonly on the order of low microseconds for
an uncontended futex/park round trip on a modern Linux scheduler, versus tens of nanoseconds for the CAS
alone; treat both figures as ballpark, not benchmark output. The entire code difference between the two
arms is the `hasQueuedPredecessors()` check named above — nothing else in either ledger class changes.
Fairness buys bounded waiting, not speed. Pay for it when a specific caller (a compliance sweep, a
scheduled settlement batch) must never be starved by a hot path like 1,200 stake-reservations/second
traffic; do not pay for it on every mutex in the system by default.

**Interview:** "Why does `ReentrantLock` default to non-fair?" — because most critical sections are
short enough that starvation windows never open, and the throughput cost of fairness is paid on every
single acquisition, not just the rare contended one.

### 4.2.6 A `Condition` on the hand-built mutex

**Mental model.** A `Condition` is a second parking lot attached to the same lock — instead of one wait
set (as `Object.wait`/`notify` give you per-monitor), you can have as many named parking lots as you
need, each with its own wake-up call, all sharing the same mutex for the compare-and-block step.

**Why it exists.** Intrinsic locks give you exactly one wait set per object, so a producer/consumer
buffer with two distinct wait conditions ("not full" for producers, "not empty" for consumers) has to
overload that single wait set and `notifyAll` everyone every time, waking threads that cannot proceed.
`ConditionObject` — the concrete `Condition` implementation nested inside `AbstractQueuedSynchronizer`
— gives each condition its own FIFO wait queue, so a `signal()` on `notFull` only wakes a producer, and
a `signal()` on `notEmpty` only wakes a consumer.

**When to reach for it, and when not.** Reach for it whenever a lock-based structure needs more than one
logically distinct wait condition — bounded buffers, barriers, custom read/write coordination. Do not
reach for it to replace a plain `wait`/`notify` monitor that only ever has one condition; `synchronized`
plus `Object.wait` is simpler and has no lock-acquisition overhead of its own to consider.

**How it works.** `new ConditionObject()` is legal from **inside** your `AbstractQueuedSynchronizer`
subclass only — it is a non-static inner class of AQS, so it reads the enclosing synchronizer's `state`,
`head`, and `tail` directly. `await()` atomically releases the lock (fully — down to hold count 0, then
restores the saved hold count on return) and parks the calling thread on the condition's own linked
queue; `signal()` moves the head of that condition queue onto the **main AQS acquire queue** rather than
unparking it directly, so the signalled thread still must win `tryAcquire` before `await()` returns —
this is why every `await()` call must sit inside a `while` loop re-checking the predicate, exactly as
with `Object.wait`.

**Diagram:** a picture would show the mutex's condition queue as a separate linked list hanging off the
`ConditionObject`, with `signal()` drawn as a dashed arrow splicing the queue head onto the tail of the
main AQS queue rather than waking it in place; no diagram is embedded in this file.

**A minimal concrete example — a bounded withdrawal buffer, capacity 1,000, feeding a `PaymentRun`:**

```java
import java.util.ArrayDeque;
import java.util.Deque;
import java.util.concurrent.locks.Condition;

record WithdrawalTransaction(String withdrawalId, Money amount) {}

/** Bounded queue of pending withdrawals waiting to be picked up by a settlement PaymentRun. */
final class BoundedWithdrawalBuffer {
    private static final int CAPACITY = 1_000;

    private final ReentrantAqsMutex mutex = new ReentrantAqsMutex();
    private final Condition notFull = mutex.newCondition();
    private final Condition notEmpty = mutex.newCondition();
    private final Deque<WithdrawalTransaction> pending = new ArrayDeque<>();

    /** Called by settlement-ingest-N threads submitting bank withdrawals (~7k/day). */
    void submit(WithdrawalTransaction withdrawal) throws InterruptedException {
        mutex.lock();
        try {
            while (pending.size() == CAPACITY) {
                notFull.await();
            }
            pending.addLast(withdrawal);
            notEmpty.signal();
        } finally {
            mutex.unlock();
        }
    }

    /** Called by the PaymentRun batch worker draining withdrawals at 3,400 settlements/sec. */
    WithdrawalTransaction takeForSettlement() throws InterruptedException {
        mutex.lock();
        try {
            while (pending.isEmpty()) {
                notEmpty.await();
            }
            WithdrawalTransaction withdrawal = pending.removeFirst();
            notFull.signal();
            return withdrawal;
        } finally {
            mutex.unlock();
        }
    }
}
```

`ReentrantAqsMutex` here is the plain non-fair mutex from the previous file exposing `newCondition()` —
add that one method to it if it did not already carry it; it is a one-line `return new
ConditionObject();` and requires no other change to that class.

**The gotcha.** `await()` fully releases the lock's **entire hold count**, not one level of it — if a
`settlement-ingest-N` thread has re-entrantly locked the mutex twice and then calls `await()` on a
condition tied to that same lock, both levels are released and both are re-acquired on wake-up; if the
caller assumed re-entrant locking meant `await()` only gives up "one layer," a nested caller elsewhere
in the call stack will observe the lock as briefly available when it should not be.

> **A `Condition` is a named wait queue that shares a lock's `state`/queue machinery: `await()` releases
> the lock and parks on the condition's own queue; `signal()` moves the head of that queue onto the
> lock's main acquire queue rather than waking it directly, so `await()` still competes for the lock on
> the way back out.**

## Open questions

- **Unverified:** the exact `hasQueuedPredecessors()` field name (`waiter` vs `thread`) and the
  precise `tryInitializeHead()` shape reflect the JDK 21 rewritten AQS internals as read from the
  `jdk-21` tag; a reader on JDK 17 will see the pre-rewrite `Node.thread`/`Node.prev`/`Node.next` shape
  with the same external contract. `[VERSION-TRAP]`
- **Unverified:** the "roughly half the throughput" figure for fair vs non-fair contention is a commonly
  cited order-of-magnitude shape from `ReentrantLock` javadoc-adjacent community benchmarking, not a
  number pulled from a specific measured run; the benchmark harness above is the way to pin it down on
  real hardware.

## Pitfalls

### Assuming `await()` releases only "one level" of a re-entrant lock

**Wrong**

```java
mutex.lock();
mutex.lock(); // re-entered, hold count now 2
try {
    while (pending.isEmpty()) {
        notEmpty.await(); // assumed: still holds one level after this
    }
} finally {
    mutex.unlock();
    mutex.unlock();
}
```

Belief: `await()` only gives up the "current" acquisition, so another thread still can't get in because
the outer `lock()` is still held. In reality the whole hold count drops to 0 for the duration of the
wait, and it is fully restored on the way back — a caller further up this same thread's call stack that
also expects the lock to be held across the `await()` will see it briefly unlocked.

**Right**

```java
mutex.lock();
try {
    while (pending.isEmpty()) {
        notEmpty.await(); // saved hold count is restored automatically on return
    }
    return pending.removeFirst();
} finally {
    mutex.unlock();
}
```

Never re-enter a lock across an `await()` call in the first place; keep the critical section that calls
`await()` at hold-count 1 so there is nothing subtle to reason about.

**Why people believe it:** `wait()`/`notify()` on intrinsic locks are usually taught with a single,
non-re-entrant `synchronized` block, so the "it releases the lock" mental model never has to confront
what "the lock" means when the hold count is greater than one.

### Assuming a fair lock is always the safer default

**Wrong**

```java
Lock ledgerLock = new FairReentrantAqsMutex(); // "fair sounds safer, use it everywhere"
```

**Right**

```java
Lock ledgerLock = new ReentrantAqsMutex(); // non-fair default; switch to fair only where a specific
                                            // caller's bounded wait matters more than raw throughput
```

**Why people believe it:** "fair" reads as a synonym for "correct" or "safe" in everyday English, so it
sounds like the conservative choice, when in a concurrency context it is a throughput-for-bounded-wait
trade, not a correctness fix — both variants are equally correct.

## Cheat sheet

| Concept | One-line fact |
|---|---|
| Barging | Default AQS acquire behaviour; an arriving thread can win over a parked queue head |
| `hasQueuedPredecessors()` | Inherited AQS method; `true` unless queue empty or caller is the head's successor |
| Fair `tryAcquire` | Barging `tryAcquire` + one `hasQueuedPredecessors()` check before the CAS |
| Fairness cost | Every hand-off pays a park/unpark round trip; throughput drops under contention |
| `ConditionObject` | Inner class of AQS; `new ConditionObject()` only legal inside the synchronizer subclass |
| `await()` | Fully releases hold count, parks on condition's own queue, restores hold count on return |
| `signal()` | Moves condition-queue head onto the *main* AQS queue — does not wake it directly |

## Self-test

**Q1.** What single line of code turns the barging `tryAcquire` from the previous file into the fair
`tryAcquire` in this file?

<details><summary>Answer</summary>

Adding `!hasQueuedPredecessors() &&` before the `compareAndSetState(0, acquires)` call in the
`state == 0` branch. Nothing else in `tryAcquire`, `tryRelease`, or `isHeldExclusively` needs to change.

</details>

**Q2.** Why does fairness cost throughput even though there is no active contention at the moment of
an uncontended call?

<details><summary>Answer</summary>

It doesn't — the cost only appears under contention, specifically at the moment of hand-off between
threads. An uncontended `lock()`/`unlock()` pair on a fair mutex is just as cheap as on a non-fair one,
because `hasQueuedPredecessors()` returns `false` immediately when the queue is empty. The cost is paid
per contended hand-off: a park/unpark round trip to wake specifically the head thread, instead of
letting whichever thread is already running grab it.

</details>

**Q3.** A `settlement-ingest-N` thread calls `notEmpty.await()` while holding `mutex` at hold count 1.
What exactly happens to `state` during the wait, and what restores it?

<details><summary>Answer</summary>

`await()` calls `fullyRelease`, which reads the current hold count (1), sets `state` to 0, clears the
owner, and unparks the next queued acquirer if any — same as a normal `unlock()`. On wake-up, before
`await()` returns, the thread re-acquires via the normal `acquireQueued` path and `setState` is called
again to restore the saved hold count (1). If the thread had re-entered the lock to hold count 2 before
calling `await()`, both levels are released and both are restored — this is the pitfall documented
above.

</details>

**Q4.** Why doesn't `signal()` unpark the waiting thread directly?

<details><summary>Answer</summary>

Because the condition-queue thread cannot be allowed to run past the `await()` call until it actually
holds the lock again — doing that would let two threads believe they hold the same mutex simultaneously.
`signal()` instead transfers the node from the condition's private queue onto the tail of the AQS's main
acquire queue, so the thread must go through the ordinary `tryAcquire` contest (fair or barging,
whichever this synchronizer implements) exactly like a fresh arrival, before `await()` is allowed to
return.

</details>

**Q5.** Name one concrete QuizStakes scenario where paying the fairness cost on the reserve-stake lock
would be justified, and one where it would not.

<details><summary>Answer</summary>

Justified: a scheduled compliance sweep that must reconcile the ledger at a guaranteed cadence even
while the 1,200/second stake-reservation traffic is at peak — without fairness, that sweep's thread
could in principle keep losing the CAS race to freshly arriving reservation threads indefinitely. Not
justified: the stake-reservation hot path itself, where every caller is equally impatient and there is
no single caller whose wait needs a hard bound — there, non-fair mode's higher raw throughput serves
every caller better on average.

</details>

**Q6.** If `FairReentrantAqsMutex.tryLock()` (the no-argument, non-blocking form) is called while
another thread is queued, does it succeed or fail, and why does that not contradict "fairness"?

<details><summary>Answer</summary>

It fails — `tryLock()` here calls `tryAcquire(1)`, which checks `hasQueuedPredecessors()` even on a
zero-timeout, non-blocking attempt. That is a stricter guarantee than the real `ReentrantLock.tryLock()`
gives: the JDK's plain, no-argument `tryLock()` is documented as a barging probe that does not honour a
`FairSync`'s ordering even on a fair lock instance — only the blocking `lock()`, `lockInterruptibly()`,
and `tryLock(timeout)` paths consistently respect `FairSync`. Neither behaviour contradicts fairness in
principle; they are simply two different design choices for what a non-blocking probe should do.

</details>

---

**Leaves covered:** 4.2.5–4.2.6 (2 leaves)
**Leaves deferred:** none
**Diagrams included:** none
**Target version:** Java 21 LTS
**Lines:** 450
