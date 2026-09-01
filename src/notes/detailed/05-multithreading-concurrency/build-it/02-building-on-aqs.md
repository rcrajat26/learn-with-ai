# 05 Multithreading and Concurrency — Building on AQS — BUILD IT (§4.2, leaves 4.2.1–4.2.4)

**Target version: Java 21 LTS.** | **Part 4 of 5** | [Index](../00-index.md)
Previous: [Queue locks and reentrancy](01b-queue-locks-and-reentrancy.md) · Next: [AQS fairness and conditions](02b-aqs-fairness-and-conditions.md)

`AbstractQueuedSynchronizer` (AQS) is the base class the JDK itself built `ReentrantLock`,
`Semaphore`, `CountDownLatch`, and `ReentrantReadWriteLock` on top of. [01b](01b-queue-locks-and-reentrancy.md)
built a CLH-style queue lock by hand; AQS *is* that same idea — a FIFO wait queue of parked
threads — packaged as a reusable superclass. Instead of writing the enqueue/park/unpark dance
yourself for every new synchronizer, you subclass AQS, hold exactly one `int` (or `long`, via
`AbstractQueuedLongSynchronizer`) of state, and override a handful of template methods that decide
whether an acquire or release should succeed. AQS owns the hard part — the queue, the parking, the
memory ordering — and your subclass owns only the *meaning* of `state`.

All four synchronizers in this file guard or gate the same critical section this whole Part 4 has
used: `FundsLedger.reserveStake`, where a `StakeSplit(bonusPortion, cashPortion)` must sum exactly
to the stake and the bonus bucket must never go negative, under `settlement-ingest-N` threads
pushing 1,200 reservations/sec against it while settlements land separately at up to 3,400/sec
(burst).

I read the `jdk-21-ga` tag of `openjdk/jdk`'s
`src/java.base/share/classes/java/util/concurrent/locks/AbstractQueuedSynchronizer.java` (via
`raw.githubusercontent.com` — `openjdk.org` itself returns HTTP 403 in this environment) for the
claims below about template-method contracts and default behavior.

## Hierarchy before details

**D-202 — one base class, four meanings of `state`**

| Class (this file) | What `state` means | Template methods overridden | Mode | Mirrors |
|---|---|---|---|---|
| `SimpleMutex` (4.2.1) | 0 = unlocked, 1 = locked | `tryAcquire`, `tryRelease`, `isHeldExclusively` | Exclusive | The non-reentrant core of `ReentrantLock` |
| `CountingSemaphore` (4.2.2) | Remaining permits | `tryAcquireShared`, `tryReleaseShared` | Shared | `java.util.concurrent.Semaphore` |
| `OneShotLatch` (4.2.3) | 0 = closed, 1 = open | `tryAcquireShared`, `tryReleaseShared` | Shared | `java.util.concurrent.CountDownLatch` (a `CountDownLatch(1)`, specifically) |
| Reentrant mutex (4.2.4) | Hold count (0 = free) | `tryAcquire`, `tryRelease`, `isHeldExclusively` | Exclusive | `ReentrantLock`'s non-fair `Sync` |

The javadoc for AQS's five core template methods — `tryAcquire`, `tryRelease`, `tryAcquireShared`,
`tryReleaseShared`, `isHeldExclusively` — states plainly: "Each of these methods by default throws
`UnsupportedOperationException`." You override only the ones your mode needs; an exclusive-mode
class never touches the shared pair and vice versa. AQS itself never interprets `state` — it only
CASes it via `getState()`/`setState()`/`compareAndSetState()` and calls back into whichever
template methods you provided.

**Insight:** the shared-mode return convention is the one detail every one of `CountingSemaphore`
and `OneShotLatch` depends on and neither javadoc-skims correctly on a first read. Per the AQS
source: `tryAcquireShared` returns "a negative value on failure; zero if acquisition in shared mode
succeeded but no subsequent shared-mode acquire can succeed; and a positive value if acquisition in
shared mode succeeded and subsequent shared-mode acquires might also succeed." That third case is
why a released latch or a semaphore with permits to spare can let a whole chain of waiters through
one after another without each one re-querying the lock from scratch — AQS propagates the release
to the next queued node itself.

![A 25-line AQS mutex, its reentrant variant, and the shared-mode latch](../diagrams/D-202-aqs-mutex-in-25-lines.svg)

## SimpleMutex — a non-reentrant lock in ~25 lines

### Mental model

A single-bit turnstile: `state` is 0 or 1, nothing else. Acquire CASes it from 0 to 1; release
just sets it back to 0, because only the thread that holds it is ever allowed to call release.

### Why it exists

[01b](01b-queue-locks-and-reentrancy.md)'s CLH and MCS locks build the queue by hand, node by
node. `SimpleMutex` shows the other half of the story: once you have AQS's queue for free, a full
mutual-exclusion lock is a five-line `tryAcquire` and a two-line `tryRelease`. This is the shape
`ReentrantLock`'s non-fair `Sync` starts from before it adds reentrancy.

### When to reach for it, and when not

Never ship `SimpleMutex` itself — `java.util.concurrent.locks.ReentrantLock` already exists,
is reentrant, is fair-or-unfair by constructor argument, and is battle-tested. Build it only to
understand what `ReentrantLock` is doing underneath. Reach for the *real* `ReentrantLock` whenever
you need an exclusive lock with `tryLock`, timeouts, `Condition`s, or reentrancy — none of which
`SimpleMutex` has.

### How it works

`tryAcquire` does exactly one `compareAndSetState(0, 1)`; on success it calls
`setExclusiveOwnerThread(Thread.currentThread())`, a method AQS does not define itself — it is
inherited from `AbstractOwnableSynchronizer`, the superclass AQS extends purely to hold "who owns
this exclusively," so tools like thread dumps and deadlock detectors can report ownership without
every synchronizer reinventing an owner field. `tryRelease` clears the owner and sets `state` back
to 0 with `setState(0)` — a plain write is sufficient because only the release-calling thread
(guaranteed by the exclusive-mode contract) ever writes it, and `setState` itself does a volatile
store, giving every subsequent `tryAcquire`'s CAS a happens-before edge to publish whatever the
critical section wrote.

```java
import java.util.concurrent.locks.AbstractQueuedSynchronizer;
import java.util.concurrent.locks.Lock;
import java.util.concurrent.locks.Condition;

public final class SimpleMutex implements Lock {

    private static final class Sync extends AbstractQueuedSynchronizer {
        @Override
        protected boolean tryAcquire(int acquires) {
            if (compareAndSetState(0, 1)) {
                setExclusiveOwnerThread(Thread.currentThread());
                return true;
            }
            return false;
        }

        @Override
        protected boolean tryRelease(int releases) {
            if (getState() == 0 || Thread.currentThread() != getExclusiveOwnerThread()) {
                throw new IllegalMonitorStateException("release by non-owner");
            }
            setExclusiveOwnerThread(null);
            setState(0);
            return true;
        }

        @Override
        protected boolean isHeldExclusively() {
            return getState() == 1 && Thread.currentThread() == getExclusiveOwnerThread();
        }
    }

    private final Sync sync = new Sync();

    @Override
    public void lock() {
        sync.acquire(1);
    }

    @Override
    public void unlock() {
        sync.release(1);
    }

    @Override
    public void lockInterruptibly() throws InterruptedException {
        sync.acquireInterruptibly(1);
    }

    @Override
    public boolean tryLock() {
        return sync.tryAcquire(1);
    }

    @Override
    public Condition newCondition() {
        throw new UnsupportedOperationException("no Condition support in this build");
    }
}
```

```java
// FundsLedger.reserveStake, guarded by SimpleMutex.
public final class FundsLedger {
    private final SimpleMutex ledgerLock = new SimpleMutex();
    private Money bonusBalance;
    private Money cashBalance;

    public StakeSplit reserveStake(Money stake) {
        ledgerLock.lock();
        try {
            Money bonusPortion = bonusBalance.min(stake);
            Money cashPortion = stake.minus(bonusPortion);
            bonusBalance = bonusBalance.minus(bonusPortion);
            cashBalance = cashBalance.minus(cashPortion);
            return new StakeSplit(bonusPortion, cashPortion);
        } finally {
            ledgerLock.unlock();
        }
    }
}
```

**Pitfall:** calling `sync.release(1)` from a thread that never acquired is not a fast silent
no-op — `tryRelease`'s explicit owner check throws `IllegalMonitorStateException`, matching the
contract AQS documents: "This exception must be thrown in a consistent fashion for synchronization
to work correctly." Skipping that check (returning `true` unconditionally) would let a foreign
thread "release" a lock it never held, corrupting `state` for the real owner.

**Diff vs the real one.** `ReentrantLock`'s actual `Sync` differs from `SimpleMutex` on: bounds/state
checks (real one supports reentrant re-acquire, `SimpleMutex` does not — a second `lock()` call
from the owner would deadlock against itself); fairness (real one offers `NonfairSync` and
`FairSync`, `SimpleMutex` is unfair-only, same as `tryAcquire`'s bare CAS); cancellation (real one's
`lockInterruptibly`/`tryLock(timeout)` are fully supported via AQS's `acquireInterruptibly` and
`tryAcquireNanos` — `SimpleMutex` exposes `lockInterruptibly` but never exercises a timeout path);
`Condition` support (real one returns a working `ConditionObject` per `newCondition()` call,
`SimpleMutex` throws); serialization (real `ReentrantLock` is `Serializable`, restoring an unlocked
state on deserialize; `SimpleMutex` was never made `Serializable` here). The JDK bothers with all of
this because a lock used across a whole application must survive reentrant self-acquire, honor
interruption for responsive cancellation, and support waiting on a condition — `SimpleMutex`
intentionally strips those to show the minimal exclusive-mode skeleton.

> **Definition.** `SimpleMutex` is a non-reentrant exclusive lock built on `AbstractQueuedSynchronizer`
> whose entire state is a single 0/1 flag CASed by `tryAcquire` and cleared by `tryRelease`.

## CountingSemaphore — shared mode with a CAS loop

### Mental model

A parking garage with a fixed number of spaces, tracked as one integer. Each car (thread) that
enters decrements the count; each car that leaves increments it. Multiple cars can be "in" at
once — that is the entire difference from `SimpleMutex`: shared mode is exclusive mode with a
counter instead of a flag.

### Why it exists

`FundsLedger.reserveStake` itself needs exclusive access, but the *connection pool* in front of it
does not — the established anchor for this domain is `Semaphore(20)` guarding a bounded pool of
database connections used to persist each reservation. Up to 20 `settlement-ingest-N` threads may
hold a connection simultaneously; the 21st must wait until one is returned. That is a counting
resource limit, not mutual exclusion, and AQS's shared mode exists specifically so more than one
waiter can be released by a single `release()` call without each of them separately winning a CAS
race against the others.

### When to reach for it, and when not

Reach for a semaphore whenever the resource has a fixed capacity greater than one — connection
pools, in-flight-request caps, bulkheads. Do not reach for it when the true requirement is mutual
exclusion (capacity of exactly one and never more) — use `SimpleMutex`/`ReentrantLock` instead, both
because the intent reads more clearly and because exclusive mode in `ReentrantLock` additionally
tracks an owner thread for diagnostics, which a semaphore permit does not.

### How it works

`tryAcquireShared` decrements `state` and returns the result; per the AQS return contract, a
negative return means "no permits left, park," and a return of zero or more means "acquired,
continue." `tryReleaseShared` must return `true` only if that specific release could unblock a
waiter — the real `Semaphore` implementation guards this with a CAS loop rather than a plain
`getAndAdd`, because two `release()` calls from two different threads racing on the same underlying
`AtomicInteger`-backed `state` must not lose an increment. AQS calls `tryAcquireShared` for every
acquire attempt (including the one made by a thread it is about to park) and calls
`tryReleaseShared` on every `releaseShared`, propagating success to the next queued shared waiter
per the three-way return contract described above.

```java
import java.util.concurrent.locks.AbstractQueuedSynchronizer;

public final class CountingSemaphore {

    private static final class Sync extends AbstractQueuedSynchronizer {
        Sync(int permits) {
            setState(permits);
        }

        @Override
        protected int tryAcquireShared(int acquires) {
            for (;;) {
                int available = getState();
                int remaining = available - acquires;
                if (remaining < 0 || compareAndSetState(available, remaining)) {
                    return remaining;
                }
            }
        }

        @Override
        protected boolean tryReleaseShared(int releases) {
            for (;;) {
                int current = getState();
                int next = current + releases;
                if (next < current) {
                    throw new Error("permit count overflow");
                }
                if (compareAndSetState(current, next)) {
                    return true;
                }
            }
        }
    }

    private final Sync sync;

    public CountingSemaphore(int permits) {
        if (permits < 0) {
            throw new IllegalArgumentException("permits cannot be negative: " + permits);
        }
        sync = new Sync(permits);
    }

    public void acquire() throws InterruptedException {
        sync.acquireSharedInterruptibly(1);
    }

    public void release() {
        sync.releaseShared(1);
    }

    public int availablePermits() {
        return sync.getState();
    }
}
```

```java
// The connection-pool anchor: Semaphore(20) guarding reservation persistence for reserveStake.
public final class ReservationPersistenceGate {
    private final CountingSemaphore poolPermits = new CountingSemaphore(20);
    private final ConnectionPool pool;

    public void persist(Reservation reservation) throws InterruptedException {
        poolPermits.acquire();
        try {
            Connection connection = pool.borrow();
            try {
                connection.save(reservation);
            } finally {
                pool.giveBack(connection);
            }
        } finally {
            poolPermits.release();
        }
    }
}
```

**Pitfall:** returning `available - acquires` from `tryAcquireShared` even when it goes negative
looks wasteful ("why not clamp and fail fast?"), but the negative value *is* the contract — AQS
reads the sign of the return, not the magnitude, to decide whether to park the caller. Clamping to
some sentinel like `-1` instead of the true deficit would still work for a single-permit acquire,
but this implementation supports multi-permit `acquireShared(n)` calls too, where the actual
negative magnitude has no further meaning to AQS but is harmless to report accurately.

**Diff vs the real one.** `java.util.concurrent.Semaphore` differs from `CountingSemaphore` on:
bounds/state checks (real one validates against `Integer.MIN_VALUE` overflow on `release` with a
dedicated `Error`, matching the check kept here); fairness (real `Semaphore` offers a `FairSync`
variant via a boolean constructor argument that adds a `hasQueuedPredecessors()` check before the
CAS — `CountingSemaphore` is unfair-only); cancellation (real one supports `tryAcquire(timeout)` via
`tryAcquireSharedNanos`; not exposed here); serialization (real `Semaphore` is `Serializable`);
`Spliterator`/iteration (real `Semaphore` exposes `getQueuedThreads()`/`hasQueuedThreads()` for
monitoring — omitted here for brevity, not because it's hard); null policy (permits are primitive
`int`s, so there is no null policy to speak of on either side). The JDK bothers with the fair
variant because a connection pool under sustained overload without fairness can let some threads
wait indefinitely while others repeatedly jump the queue — an acceptable throughput trade for most
pools, but not for every workload, hence the constructor flag rather than a hardcoded choice.

> **Definition.** A counting semaphore built on AQS is `state` holding "permits remaining,"
> acquired via a CAS-loop decrement in `tryAcquireShared` and released via a CAS-loop increment in
> `tryReleaseShared`, with AQS's shared-mode propagation letting one release wake more than one
> waiter when enough permits become available at once.

## OneShotLatch — exactly how CountDownLatch(1) works

### Mental model

A gate that starts closed and, the instant someone opens it, stays open forever. Every thread that
was waiting, and every thread that asks afterward, walks straight through.

### Why it exists

The QuizStakes load-testing harness for the 1,200-reservations/sec target needs a start gate: spin
up every `settlement-ingest-N` worker thread, have each one block until a single "go" signal, then
release them all at once so the measured window doesn't include thread-startup jitter. That is a
one-time, one-directional state transition — closed to open, never back — which is a strictly
simpler shape than a semaphore's up-and-down counter.

### When to reach for it, and when not

Reach for a one-shot latch for exactly this "wait for N things to finish, or wait for a single
signal" shape — start gates, "all workers ready," "shutdown initiated." Never reach for it when the
gate needs to close again (a semaphore or a fresh latch per round is what `CyclicBarrier` and
repeated `CountDownLatch` instances are for); a `OneShotLatch`, like the real `CountDownLatch`, has
no reset.

### How it works

`state` is 0 (closed) or 1 (open). `tryAcquireShared` returns `1` if `state` is already `1`
(matching the AQS contract's "positive: this and further shared acquires can succeed," which
matters because a latch, once open, must let every future caller through without re-parking
anyone) and `-1` otherwise (park). `tryReleaseShared` unconditionally sets `state` to `1` via CAS
and returns `true` exactly once — the first successful transition — so `releaseShared` only ever
triggers AQS's queue-unparking walk on the one call that actually flips the gate; a second call to
`open()` after the gate is already open is a correctly-behaved no-op, mirroring `CountDownLatch`
whose internal count cannot go negative.

```java
import java.util.concurrent.locks.AbstractQueuedSynchronizer;

public final class OneShotLatch {

    private static final class Sync extends AbstractQueuedSynchronizer {
        @Override
        protected int tryAcquireShared(int ignored) {
            return getState() == 1 ? 1 : -1;
        }

        @Override
        protected boolean tryReleaseShared(int ignored) {
            return compareAndSetState(0, 1);
        }
    }

    private final Sync sync = new Sync();

    public void await() throws InterruptedException {
        sync.acquireSharedInterruptibly(1);
    }

    public void open() {
        sync.releaseShared(1);
    }

    public boolean isOpen() {
        return sync.getState() == 1;
    }
}
```

```java
// The start-gate anchor for the 1,200-reservations/sec load test.
public final class ReservationLoadTest {
    private final OneShotLatch startGate = new OneShotLatch();

    public void run(int workerCount, FundsLedger ledger, Money stakePerReservation)
            throws InterruptedException {
        for (int i = 0; i < workerCount; i++) {
            Thread worker = new Thread(() -> {
                try {
                    startGate.await();
                } catch (InterruptedException e) {
                    Thread.currentThread().interrupt();
                    return;
                }
                ledger.reserveStake(stakePerReservation);
            }, "settlement-ingest-" + i);
            worker.start();
        }
        // All workers are now parked on startGate.await(); flip it to release them together.
        startGate.open();
    }
}
```

**Pitfall:** implementing `tryReleaseShared` as `setState(1); return true;` instead of a CAS looks
equivalent for a single caller, but if two threads race to call `open()` concurrently, the plain
write formulation would return `true` from *both* calls, and AQS would attempt to propagate the
release twice — harmless here because opening an already-open gate is idempotent, but it is the
kind of "happens to work" shortcut that breaks the moment `tryReleaseShared`'s return value is
relied on to mean "this specific call was the one that changed state," as it is in the real
`CountDownLatch`'s multi-count version.

**Diff vs the real one.** `java.util.concurrent.CountDownLatch` differs from `OneShotLatch` on:
bounds/state checks (real `CountDownLatch(int count)` supports counting down from any starting
value, decrementing `state` toward zero rather than a bare 0/1 flip — `OneShotLatch` is the
`count == 1` special case only); intrinsics (real one's `tryReleaseShared` loops with CAS
decrementing toward zero and returns `true` only on the transition that reaches exactly zero, the
same "return true exactly once" discipline `OneShotLatch` uses for its 0→1 transition); cancellation
(both support `await(timeout)` via `tryAcquireSharedNanos` — omitted from this build for brevity but
mechanically identical); serialization and `Spliterator` (real `CountDownLatch` is not `Serializable`
and has no iteration support either — this is one axis where the real class matches the toy exactly);
null policy (no object arguments on either side, so nothing to violate). The JDK bothers with the
general countdown because "wait for N independent things to finish" (N inbound event acknowledgments,
N worker completions) is common enough to deserve one class, whereas a bare open/closed gate is
`new CountDownLatch(1)` — the JDK didn't ship a separate one-shot class because the general one
degenerates to it for free.

> **Definition.** `OneShotLatch` is a single-transition gate built on AQS shared mode where
> `state` is 0 until the one `tryReleaseShared` call that CASes it to 1, after which every past and
> future `tryAcquireShared` call succeeds immediately.

## The reentrant variant — hold count, owner, and foreign release

### Mental model

The same turnstile as `SimpleMutex`, except the owner is allowed to walk through it again without
it locking behind them — the turnstile just counts how many times they've walked through, and
requires that many walk-backs before it locks again for everyone else.

### Why it exists

A plain `SimpleMutex` deadlocks the instant the owning thread calls `lock()` twice — for example,
if `reserveStake` itself, while holding `ledgerLock`, ever called a second ledger method that also
tried to acquire the same lock (a realistic shape once audit logging or a compliance check is added
inline to the reservation path). Reentrancy is what makes a lock usable as a general-purpose
`synchronized` replacement rather than a single-acquisition-only primitive.

### When to reach for it, and when not

Reach for reentrancy whenever the same thread might legitimately re-enter the guarded section
through a different call path — which in practice is "almost always," which is exactly why
`ReentrantLock` defaults to it and `SimpleMutex` had to be a separate, deliberately restricted
class to demonstrate the non-reentrant shape at all. There is no downside to reentrancy for a
single-threaded re-entry pattern; the only cost is one extra `==` comparison and one extra `int`
increment per acquire, both negligible next to the CAS itself.

### How it works

`tryAcquire` first checks whether `state == 0` (free) and CASes it to `acquires`; if instead the
*current* thread already owns it (`getExclusiveOwnerThread() == Thread.currentThread()`), it
increments `state` by `acquires` without any CAS at all — safe because only the owning thread ever
observes or mutates `state` while it is non-zero and it already holds exclusive rights. `tryRelease`
decrements `state` by `releases`; only when the result reaches exactly `0` does it clear the owner
and report `true` to AQS (meaning "fully released, wake the next waiter") — a partial decrement
(hold count still positive) returns `false`, telling AQS the lock is still held and no one should be
unparked yet. Any release attempt by a thread that is not the current owner throws
`IllegalMonitorStateException`, which is the exact behavior AQS's javadoc calls out by name:
"This exception must be thrown in a consistent fashion for synchronization to work correctly."

```java
import java.util.concurrent.locks.AbstractQueuedSynchronizer;
import java.util.concurrent.locks.Lock;
import java.util.concurrent.locks.Condition;

public final class ReentrantMutex implements Lock {

    private static final class Sync extends AbstractQueuedSynchronizer {
        @Override
        protected boolean tryAcquire(int acquires) {
            Thread current = Thread.currentThread();
            int state = getState();
            if (state == 0) {
                if (compareAndSetState(0, acquires)) {
                    setExclusiveOwnerThread(current);
                    return true;
                }
                return false;
            }
            if (current == getExclusiveOwnerThread()) {
                int next = state + acquires;
                if (next < 0) {
                    throw new Error("hold count overflow");
                }
                setState(next);
                return true;
            }
            return false;
        }

        @Override
        protected boolean tryRelease(int releases) {
            if (Thread.currentThread() != getExclusiveOwnerThread()) {
                throw new IllegalMonitorStateException("release by non-owner");
            }
            int next = getState() - releases;
            boolean fullyReleased = (next == 0);
            if (fullyReleased) {
                setExclusiveOwnerThread(null);
            }
            setState(next);
            return fullyReleased;
        }

        @Override
        protected boolean isHeldExclusively() {
            return getExclusiveOwnerThread() == Thread.currentThread();
        }

        int currentHoldCount() {
            return isHeldExclusively() ? getState() : 0;
        }
    }

    private final Sync sync = new Sync();

    @Override
    public void lock() {
        sync.acquire(1);
    }

    @Override
    public void unlock() {
        sync.release(1);
    }

    @Override
    public void lockInterruptibly() throws InterruptedException {
        sync.acquireInterruptibly(1);
    }

    @Override
    public boolean tryLock() {
        return sync.tryAcquire(1);
    }

    @Override
    public Condition newCondition() {
        throw new UnsupportedOperationException("no Condition support in this build");
    }

    public int getHoldCount() {
        return sync.currentHoldCount();
    }
}
```

```java
// Reentrant re-entry: reserveStake calls a compliance check that itself re-acquires ledgerLock.
public final class FundsLedger {
    private final ReentrantMutex ledgerLock = new ReentrantMutex();
    private Money bonusBalance;
    private Money cashBalance;

    public StakeSplit reserveStake(Money stake) {
        ledgerLock.lock();
        try {
            recordLedgerTouch();               // re-enters the same lock, same thread
            Money bonusPortion = bonusBalance.min(stake);
            Money cashPortion = stake.minus(bonusPortion);
            bonusBalance = bonusBalance.minus(bonusPortion);
            cashBalance = cashBalance.minus(cashPortion);
            return new StakeSplit(bonusPortion, cashPortion);
        } finally {
            ledgerLock.unlock();
        }
    }

    private void recordLedgerTouch() {
        ledgerLock.lock();          // hold count 1 -> 2, no CAS, no parking
        try {
            // audit bookkeeping against the same ledger instance
        } finally {
            ledgerLock.unlock();    // hold count 2 -> 1, tryRelease returns false, no wake
        }
    }
}
```

**Pitfall:** calling `unlock()` one fewer time than `lock()` was called (an unbalanced
try/finally, or an early `return` inside a nested acquire that skips its matching release) leaves
`state` permanently above zero with the thread believing it fully released. Every subsequent
`tryAcquire` from *other* threads correctly fails forever, and the lock looks identically "stuck"
whether the bug is a genuine deadlock or a leaked hold count — always pair each `lock()` with
exactly one `finally { unlock(); }`, never conditionally skipped.

**Diff vs the real one.** This is one of the four leaves — the fully consolidated table against
`ReentrantLock`'s real fair and non-fair `Sync` classes, spanning all the axes (bounds/state checks,
intrinsics, memory ordering, cancellation, fairness, serialization, `Spliterator`/iteration, null
policy, allocation strategy, and why the JDK bothers) is leaf 4.2.7 and lives in the next file,
[02b-aqs-fairness-and-conditions.md](02b-aqs-fairness-and-conditions.md), which closes §4.2. In
short here: this class is unfair-only, has no `Condition` support, and has no serialization
support, all three of which the next file's table walks in full alongside the fairness mechanics
(`hasQueuedPredecessors()`) this file deliberately left out.

> **Definition.** A reentrant AQS mutex stores the owning thread's hold count in `state`, lets
> that same thread re-acquire without contention by comparing `getExclusiveOwnerThread()` against
> `Thread.currentThread()`, and only reports a full release back to AQS when the hold count reaches
> exactly zero.

## Open questions

None outstanding. The shared-mode return-value contract and the default-`UnsupportedOperationException`
behavior of the five template methods were confirmed against the `jdk-21-ga` tag of
`AbstractQueuedSynchronizer.java`, and `setExclusiveOwnerThread`'s origin in `AbstractOwnableSynchronizer`
was confirmed from the same read.

## Pitfalls

### Believing `tryAcquireShared`'s return value is a boolean in disguise

**Wrong**

```java
@Override
protected int tryAcquireShared(int acquires) {
    return getState() > 0 ? 1 : -1;   // "1 for true, -1 for false" — looks boolean-ish
}
```

This happens to work for a strict single-permit gate, but it silently drops the "zero means
succeeded, but do not propagate further" case, which matters the moment more than one permit or a
counting resource is involved — `CountingSemaphore.tryAcquireShared` above deliberately returns the
true remaining count, not a clamped sentinel, so AQS's propagation logic sees an accurate signal.

**Right**

```java
@Override
protected int tryAcquireShared(int acquires) {
    for (;;) {
        int available = getState();
        int remaining = available - acquires;
        if (remaining < 0 || compareAndSetState(available, remaining)) {
            return remaining;   // negative = failed, 0 = succeeded/no more, positive = succeeded/more available
        }
    }
}
```

**Why people believe it:** the AQS javadoc's three-way contract reads like an afterthought next to
the much more familiar boolean `tryAcquire`, and a single-permit latch or mutex genuinely never
exercises the "positive means keep propagating" branch — so it is easy to internalize a two-value
mental model from `OneShotLatch`-shaped code and carry it, wrongly, into a real counting semaphore.

### Assuming a CAS loop is unnecessary because "only one thread releases at a time"

**Wrong**

```java
@Override
protected boolean tryReleaseShared(int releases) {
    setState(getState() + releases);   // not atomic: read-then-write across two separate calls
    return true;
}
```

Under the connection-pool anchor's real traffic — up to 20 concurrent holders, each releasing
independently the instant their query finishes — two `release()` calls can interleave between the
`getState()` read and the `setState()` write, and one increment is lost forever, permanently
shrinking the effective pool size by one permit per lost race.

**Right**

```java
@Override
protected boolean tryReleaseShared(int releases) {
    for (;;) {
        int current = getState();
        int next = current + releases;
        if (compareAndSetState(current, next)) {
            return true;
        }
    }
}
```

**Why people believe it:** `tryAcquireShared` and `tryReleaseShared` are documented to "be
internally thread-safe," and it's tempting to read "internally" as "AQS handles it for me" rather
than "you must make your own body of this method safe against concurrent calls" — AQS synchronizes
the queue, never your `state`-derived business logic.

### Forgetting that reentrant `tryAcquire`'s fast path skips the CAS entirely

**Wrong**

```java
if (current == getExclusiveOwnerThread()) {
    compareAndSetState(state, state + acquires);   // unnecessary CAS on the owner's own re-entry
    return true;
}
```

Not a correctness bug — the CAS will succeed, since only the owner mutates `state` while it holds
the lock — but it is a needless atomic instruction on the hottest path (self re-entry), adding
cache-coherence cost for zero benefit.

**Right**

```java
if (current == getExclusiveOwnerThread()) {
    setState(state + acquires);   // no other thread can be racing this write
    return true;
}
```

**Why people believe it:** every other write to `state` in this file goes through a CAS, so it
feels inconsistent — even unsafe — to use a plain `setState` anywhere. The safety argument is
specific to this one branch: exclusivity has already been established, so the write has no
concurrent writer to race against, unlike the initial 0→acquires transition or any shared-mode
release.

## Cheat sheet

| Class | `state` meaning | Mode | Template methods | Return-value convention | Mirrors |
|---|---|---|---|---|---|
| `SimpleMutex` | 0/1 | Exclusive | `tryAcquire`, `tryRelease`, `isHeldExclusively` | boolean: acquired? released fully? | `ReentrantLock` core (non-reentrant slice) |
| `CountingSemaphore` | permits remaining | Shared | `tryAcquireShared`, `tryReleaseShared` | int: negative fail, 0/+ succeed (propagate if +) | `Semaphore` |
| `OneShotLatch` | 0 closed / 1 open | Shared | `tryAcquireShared`, `tryReleaseShared` | int: -1 closed, 1 open; boolean: true only on 0→1 | `CountDownLatch(1)` |
| Reentrant mutex | hold count | Exclusive | `tryAcquire`, `tryRelease`, `isHeldExclusively` | boolean: acquired?; release true only at count 0 | `ReentrantLock.Sync` |
| All four | — | — | Never override: leave default `UnsupportedOperationException` on unused-mode methods | — | AQS javadoc, `jdk-21-ga` |

## Self-test

**Q1.** Why does `CountingSemaphore.tryAcquireShared` return the raw `remaining` value — which can
be a large negative number — instead of clamping to `-1` on failure?

<details><summary>Answer</summary>

AQS's contract only inspects the *sign* of the return to decide whether to park the caller, so a
clamp to `-1` would not break single-permit acquires. But this method also serves multi-permit
`acquireShared(n)` calls, where the true deficit is meaningful information about how far short the
available permits are — returning the accurate value costs nothing extra and keeps the method
honest about what actually happened, rather than encoding a partial truth that would need
re-deriving elsewhere if multi-permit support were ever added on top.

</details>

**Q2.** In `OneShotLatch`, why must `tryReleaseShared` use `compareAndSetState(0, 1)` and return
its result, rather than always returning `true` after an unconditional `setState(1)`?

<details><summary>Answer</summary>

`tryReleaseShared`'s return value tells AQS whether *this specific call* is the one that should
trigger propagation to waiting threads. If two threads call `open()` concurrently, only one of them
should be credited with the transition; returning `true` unconditionally from both would have AQS
attempt to propagate a release twice for what is logically one state change. The CAS guarantees
exactly one caller observes `compareAndSetState(0, 1)` succeed, matching the discipline the real
`CountDownLatch` needs for its general N-count case, where firing the wake-up exactly once (on the
transition to zero) is not optional — it's the same reason `CountingSemaphore.tryReleaseShared`
loops rather than trusting a single racy read-then-write.

</details>

**Q3.** Why does the reentrant mutex's `tryAcquire` skip the CAS entirely when the current thread
already owns the lock, while `SimpleMutex`'s `tryAcquire` always CASes?

<details><summary>Answer</summary>

`SimpleMutex` never distinguishes "the owner is re-entering" from "some other thread is trying to
acquire" — it has no concept of an owner re-entering at all, so every attempt, including a
self-re-entry, must go through the same CAS race against all other threads (and will simply fail,
since `state` is already 1). The reentrant mutex, by contrast, has already established — by
checking `getExclusiveOwnerThread() == Thread.currentThread()` — that no other thread can currently
be racing this particular write, because exclusivity was already granted to this thread. A plain
`setState` is therefore safe and cheaper, avoiding an unnecessary atomic instruction on the hottest
re-entry path.

</details>

**Q4.** A thread calls `ledgerLock.unlock()` on the reentrant mutex without ever having called
`lock()`. What happens, and which line causes it?

<details><summary>Answer</summary>

`tryRelease` checks `Thread.currentThread() != getExclusiveOwnerThread()` before touching `state`
at all. Since this thread never acquired the lock, `getExclusiveOwnerThread()` is either `null` or
some other thread, so the check is true and the method throws `IllegalMonitorStateException`
immediately — the AQS javadoc's own guidance ("this exception must be thrown in a consistent
fashion for synchronization to work correctly") is exactly why this check exists rather than
silently doing nothing or, worse, decrementing `state` into a corrupted negative hold count.

</details>

**Q5.** Why can `CountingSemaphore`'s `tryReleaseShared` use `state = state + releases` freely
(no upper bound check against the original permit count), while a real bounded pool would want to
guard against over-release?

<details><summary>Answer</summary>

AQS's `Sync` has no idea what the "correct" maximum permit count is meant to be — it only knows
the current `int`. The overflow guard in the implementation above only protects against wrapping
past `Integer.MAX_VALUE`, not against a caller calling `release()` more times than `acquire()`,
which is a caller-discipline bug, not something the synchronizer can detect on its own without
also tracking the original capacity and comparing against it on every release — a cost the real
`Semaphore` also does not pay for the same reason.

</details>

**Q6.** Why does `OneShotLatch.tryAcquireShared` return `1` rather than `0` when the gate is
already open?

<details><summary>Answer</summary>

Per AQS's own contract, a positive return means "succeeded, and subsequent shared acquires might
also succeed" — exactly the case for an already-open latch, where every future `await()` call
should also succeed without parking. Returning `0` would tell AQS "succeeded, but do not assume
later acquires will," which would be technically harmless for a latch that never re-closes, but
`1` is the semantically correct signal and matches how the real `CountDownLatch` (whose count
cannot go back up) reports success once it reaches zero.

</details>

**Q7.** What would go wrong if `SimpleMutex.tryRelease` used `state == 0` as its *only* guard,
omitting the owner check?

<details><summary>Answer</summary>

Any thread — not just the one holding the lock — could call `unlock()` while the lock is held and
successfully flip `state` back to 0, even though the true owner is still inside its critical
section. A different thread could then acquire the lock and enter the same critical section
concurrently with the original owner, defeating the entire purpose of mutual exclusion. The owner
check via `getExclusiveOwnerThread()` is what makes release a privilege of the acquiring thread
alone.

</details>

---

**Leaves covered:** 4.2.1–4.2.4 (4 leaves)
**Leaves deferred:** none
**Diagrams included:** D-202
**Target version:** Java 21 LTS
**Lines:** 450
