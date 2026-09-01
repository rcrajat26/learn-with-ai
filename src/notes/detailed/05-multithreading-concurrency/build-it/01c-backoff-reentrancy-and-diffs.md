# 05 Multithreading and Concurrency — Backoff, reentrancy and the diff table — BUILD IT (§4.1, leaves 4.1.8–4.1.10)

**Target version: Java 21 LTS.** | **Part 4 of 5** | [Index](../00-index.md)
Previous: [Queue locks: CLH and MCS](01b-queue-locks-and-reentrancy.md) · Next: [Building on AQS](02-building-on-aqs.md)

This file closes out §4.1, continuing from
[01-locks-from-first-principles.md](01-locks-from-first-principles.md) (`SpinLock`,
`TestAndTestAndSetLock`, `TicketLock`, the spin-versus-block JMH harness) and
[01b-queue-locks-and-reentrancy.md](01b-queue-locks-and-reentrancy.md) (`CLHLock`, `MCSLock`, and
the CLH-versus-MCS comparison that explains AQS's lineage). Every lock across all three files
guards the same critical section: `FundsLedger.reserveStake`, which must produce a
`StakeSplit(bonusPortion, cashPortion)` that sums exactly to the stake, with the bonus bucket never
going negative, under up to 1,200 stake reservations/sec from `settlement-ingest-N` threads.

Two things remain: a pragmatic fix for TAS's thundering-herd retry pathology (`BackoffLock`), and
reentrancy — none of the seven locks built so far tolerate a thread re-acquiring a lock it already
holds. The file ends with the consolidated diff table §4.1.10 asks for, covering every lock built
across all three files against `ReentrantLock`.

## BackoffLock — don't retry immediately, retry later

### Mental model

A busy phone line. Redialing the instant a call drops just re-joins the same jam; waiting a random
short interval before redialing (and a longer one if that also fails) spreads retries out so
they stop colliding.

### Why it exists

Plain TAS's failure mode under contention isn't just coherence traffic — it's a *thundering herd*:
the instant the lock is released, every spinner's next CAS attempt fires near-simultaneously, so
only one succeeds and the rest immediately retry and collide again. Exponential randomized backoff
breaks that synchronization.

### When to reach for it, and when not

Reach for it as a cheap retrofit onto an existing TAS-style lock when you observe throughput
collapsing under moderate contention (say, several `settlement-ingest-N` threads racing on
`reserveStake` during a burst) and cannot restructure to CLH/MCS. Don't reach for it as a
substitute for CLH/MCS ([01b](01b-queue-locks-and-reentrancy.md)) when you *can* restructure —
backoff trades some acquisition latency (the sleep) for throughput, whereas CLH/MCS get both
fairness-adjacent behavior and no wasted retries at once. That trade-off — latency paid by every
waiter versus the throughput regained by avoiding collisions — is the whole reason to reach for it
at all: it is a strictly worse fairness story than a ticket lock ([01](01-locks-from-first-principles.md)),
traded for strictly better behavior under moderate contention than plain TAS.

### How it works

Each failed CAS attempt increases a per-thread backoff window (typically by doubling it, capped at
some maximum), and the thread parks itself for a random duration inside that window before
retrying. The randomization is what prevents every backed-off thread from waking up and retrying
in lockstep again.

```java
import java.util.concurrent.ThreadLocalRandom;
import java.util.concurrent.atomic.AtomicBoolean;

public final class BackoffLock {
    private final AtomicBoolean locked = new AtomicBoolean(false);
    private final long minDelayNanos;
    private final long maxDelayNanos;

    public BackoffLock(long minDelayNanos, long maxDelayNanos) {
        this.minDelayNanos = minDelayNanos;
        this.maxDelayNanos = maxDelayNanos;
    }

    public void lock() {
        long delay = minDelayNanos;
        while (!locked.compareAndSet(false, true)) {
            long sleepNanos = ThreadLocalRandom.current().nextLong(delay);
            parkNanos(sleepNanos);
            delay = Math.min(delay * 2, maxDelayNanos);
        }
    }

    public void unlock() {
        locked.set(false);
    }

    private static void parkNanos(long nanos) {
        long deadline = System.nanoTime() + nanos;
        while (System.nanoTime() < deadline) {
            Thread.onSpinWait();
        }
    }
}
```

**Pitfall:** using a fixed doubling schedule with no randomness, on the theory that deterministic
backoff is "simpler and just as good." A fixed schedule keeps every backed-off thread synchronized
with every other one: if two threads both fail a CAS at the same moment, a purely deterministic
schedule has them both wake up and retry at the same moment again, recreating the exact
thundering-herd collision backoff exists to avoid. The randomization inside each window (via
`ThreadLocalRandom.current().nextLong(delay)` above) is what actually breaks the synchronization —
dropping it turns `BackoffLock` back into a slower version of plain `SpinLock` with the same
collision pathology, minus the constant CAS traffic.

**Pitfall:** using `LockSupport.parkNanos` for the backoff sleep and assuming it always sleeps the
full duration. `parkNanos` can return early (spurious wakeups are explicitly permitted by its
contract), so a naive implementation that treats one `parkNanos` call as guaranteeing the full
delay elapsed can retry sooner than intended — usually harmless here since the CAS loop simply
retries, but worth knowing before reusing this pattern somewhere the sleep length is load-bearing.

> **Definition.** A backoff lock is a spin lock whose retry interval grows (typically
> exponentially) and is randomized on each failed attempt, trading a small amount of acquisition
> latency for avoiding synchronized retry storms under contention.

## A reentrant mutex on AtomicReference\<Thread\> (4.1.9)

### Mental model

A single doorman who remembers your face. If you're already inside and you walk up to the door
again, he waves you through without re-checking — but he also keeps a tally of how many times
you've walked through, so he knows how many times you have to walk *out* before the door is
truly unlocked for everyone else.

### Why it exists

None of the locks built across all three files are reentrant by default: a thread that already
holds `SpinLock` and calls `lock()` again (say, `reserveStake` calling into another ledger method
that also takes the lock) deadlocks against itself. `synchronized` and `ReentrantLock` both solve
this by tracking *which* thread holds the lock and how many times.

### When to reach for it, and when not

Build this only to understand the mechanism — production code takes `ReentrantLock` or
`synchronized`, both of which already do this correctly and additionally support conditions,
interruptible acquisition, and fairness modes (4.1.10, below).

### How it works

An `AtomicReference<Thread>` holds the current owner (or `null`). `lock()` first checks — with a
plain, non-atomic read — whether the calling thread already *is* the owner; if so, it just
increments the hold count and returns, no CAS needed. Otherwise it spins on
`owner.compareAndSet(null, currentThread)` until it wins, then sets the hold count to 1. `unlock()`
decrements the hold count and only clears `owner` back to `null` when the count reaches zero.

**Insight:** the hold count is a plain `int`, not an `AtomicInteger`, and that is deliberate, not
an oversight — precisely because of the ownership check. Once a thread has established (via the
atomic CAS) that it is the sole owner, every subsequent read and write of the count happens
exclusively from that one thread until it releases ownership; no other thread's `lock()` call can
even reach the count-touching code path without first successfully becoming the owner itself,
which cannot happen while the current owner still holds it. Only the owner ever touches the field,
so there is no race to guard against — the mutual exclusion the CAS already provides for `owner`
transitively protects the plain `int` too.

```java
import java.util.concurrent.atomic.AtomicReference;

public final class ReentrantSpinMutex {
    private final AtomicReference<Thread> owner = new AtomicReference<>(null);
    private int holdCount = 0; // touched only by the current owner — see Insight above.

    public void lock() {
        Thread current = Thread.currentThread();
        if (owner.get() == current) {
            holdCount++;
            return;
        }
        while (!owner.compareAndSet(null, current)) {
            Thread.onSpinWait();
        }
        holdCount = 1;
    }

    public void unlock() {
        if (owner.get() != Thread.currentThread()) {
            throw new IllegalMonitorStateException("unlock() called by a non-owner thread");
        }
        holdCount--;
        if (holdCount == 0) {
            owner.set(null);
        }
    }
}
```

```java
// reserveStake calling a second ledger method that also needs the lock — the reentrancy this
// buys. With SpinLock (01-locks-from-first-principles.md) this would deadlock the calling
// settlement-ingest-N thread against itself; with ReentrantSpinMutex it does not.
public final class FundsLedgerReentrant {
    private final ReentrantSpinMutex ledgerLock = new ReentrantSpinMutex();
    private Money bonusBalance;
    private Money cashBalance;

    public StakeSplit reserveStake(Money stake) {
        ledgerLock.lock();
        try {
            recordAuditTrail(stake); // also takes ledgerLock — reentrant, so no self-deadlock.
            Money bonusPortion = bonusBalance.min(stake);
            Money cashPortion = stake.minus(bonusPortion);
            bonusBalance = bonusBalance.minus(bonusPortion);
            cashBalance = cashBalance.minus(cashPortion);
            return new StakeSplit(bonusPortion, cashPortion);
        } finally {
            ledgerLock.unlock();
        }
    }

    private void recordAuditTrail(Money stake) {
        ledgerLock.lock();
        try {
            // audit bookkeeping under the same ledger lock
        } finally {
            ledgerLock.unlock();
        }
    }
}
```

**Pitfall:** the ownership check `owner.get() == current` in `lock()` is fine for correctness here
because `AtomicReference.get()` has volatile semantics — but it's easy to "simplify" this by
replacing `AtomicReference<Thread>` with a plain field for a supposed performance win, at which
point the ownership check loses its happens-before guarantee entirely and a thread can observe a
stale owner across cores.

> **Definition.** A reentrant mutex tracks both *which* thread owns it and *how many times* that
> thread has acquired it, allowing the owning thread to re-acquire without blocking while still
> requiring one `unlock()` per `lock()` before another thread can proceed.

## Diff vs the real one (4.1.10)

Every lock compared here was built across three files: TAS, TTAS, ticket lock, and the JMH
measurement harness in [01](01-locks-from-first-principles.md); CLH and MCS in
[01b](01b-queue-locks-and-reentrancy.md); `BackoffLock` and the reentrant mutex in this file.

| Lock built | Blocks (parks) vs. spins when contended | Cancellation (interrupt/timeout) | Fairness mode | Condition variable support | Instrumentation (`isLocked`, `getQueueLength`, …) | Monitor-dump visibility (jstack/JFR) |
|---|---|---|---|---|---|---|
| `SpinLock` (TAS, [01](01-locks-from-first-principles.md)) | Always spins | None — `lock()` cannot be interrupted or timed out | None (unfair) | None | None | Invisible — a spinning thread shows as `RUNNABLE`, not "waiting for a lock," so a stuck spin lock looks like a hot loop in a stack dump, not a deadlock |
| `TestAndTestAndSetLock` ([01](01-locks-from-first-principles.md)) | Always spins | None | None | None | None | Same as `SpinLock` |
| `TicketLock` ([01](01-locks-from-first-principles.md)) | Always spins | None | Strict FIFO (this is its *only* fairness option — cannot be configured) | None | None | Same as `SpinLock` |
| `CLHLock` / `MCSLock` ([01b](01b-queue-locks-and-reentrancy.md)) | Always spins | None (real CLH/MCS have no notion of abandoning a queue position safely, per 4.1.7) | Strict FIFO by queue order | None | None | Same as `SpinLock`; queue position is invisible to any external tool |
| `BackoffLock` (this file) | Spins, with sleeps between attempts | None | None (unfair; backoff timing can accidentally favor recently-failed threads or starve them further) | None | None | Same as `SpinLock`, plus the sleeps show up as brief `TIMED_WAITING` blips that don't reflect true lock semantics |
| `ReentrantSpinMutex` (this file) | Always spins | None | None | None | Reentrancy count is inspectable only by adding your own getter | Same as `SpinLock` |
| **`java.util.concurrent.locks.ReentrantLock`** | **Blocks** — parks via `LockSupport.park()` after a brief optimistic spin, so it costs near-zero CPU while waiting long-term | **Full** — `lockInterruptibly()` and `tryLock(timeout, unit)` both exist and correctly abandon the attempt, splicing the cancelled node out of the AQS queue (the exact capability CLH's `prev` links enable, per 4.1.7) | **Configurable** — constructor takes a `fair` boolean; fair mode enforces FIFO (at a throughput cost), unfair (default) mode allows barging for higher throughput | **Full** — `newCondition()` gives `await`/`signal`/`signalAll`, each with its own wait queue | **Full** — `isLocked()`, `isHeldByCurrentThread()`, `getHoldCount()`, `getQueueLength()`, `hasQueuedThreads()` all exist | **Visible** — `jstack` reports the exact `ReentrantLock` instance a thread is `WAITING`/`TIMED_WAITING` on, and which thread owns it, because parked threads are properly registered with the JVM's own monitor/lock bookkeeping |

The short version: everything across all three files is *mechanism*, not *product*. `ReentrantLock`
is the product, and it is built from a CLH-shaped queue with parking, cancellation, fairness,
conditions, and instrumentation layered on top of exactly the ideas in 4.1.1–4.1.9. **Why the JDK
bothers** building all of that on top of a "simple" queue: application code cannot tolerate a
lock that burns CPU while blocked (spinning locks don't scale past the core count), cannot
tolerate a lock that can't be interrupted (an app that needs to shut down or time out a stuck
acquisition would hang forever), and cannot be debugged in production without instrumentation that
shows *who is waiting on what* — none of which any lock built across these three files provides on
its own.

## Pitfalls

### Believing a reentrant lock never needs to worry about the wrong thread unlocking it

**Wrong**

```java
// A pooled worker thread acquires the mutex, but a *different* pooled thread ends up running the
// cleanup block due to a mis-scoped try/finally across an async boundary.
ledgerLock.lock();
CompletableFuture.runAsync(() -> {
    // ... work happens here, possibly on a different thread ...
    ledgerLock.unlock(); // wrong thread calling unlock()
});
```

**Right**

`ReentrantSpinMutex.unlock()` above explicitly checks `owner.get() != Thread.currentThread()` and
throws `IllegalMonitorStateException` rather than silently clearing `owner` for whichever thread
happens to call it. Never split `lock()`/`unlock()` across an asynchronous boundary — the pairing
must happen on the same thread, in the same stack frame's `try`/`finally`, exactly as
`recordAuditTrail` and `reserveStake` do above.

**Why people believe it:** the reentrant mutex's ownership tracking makes it *feel* safer than a
raw `SpinLock`, so it's tempting to assume it also tolerates being unlocked from an arbitrary
thread — but ownership tracking exists to detect that misuse, not to permit it.

### Assuming `ReentrantLock`'s default (unfair) mode is a compromise you should "fix" to fair

**Wrong**

```java
// "Fair seems more correct — let's always use fair mode."
ReentrantLock ledgerLock = new ReentrantLock(true);
```

**Right**

Fair mode enforces strict FIFO, which is exactly the `TicketLock`/CLH/MCS fairness story — and it
costs real throughput, because it forbids barging (a thread arriving right as the lock frees up
must still queue behind everyone already waiting, even if it could acquire instantly). The
unfair default lets a freshly-arriving thread grab the lock immediately if it happens to be free,
which is measurably faster under most workloads and is why it is the default. Reach for fair mode
only when starvation of a specific caller is an observed, measured problem — not by default.

```java
ReentrantLock ledgerLock = new ReentrantLock(); // unfair (default) — barging allowed, faster.
```

**Why people believe it:** "fair" sounds unambiguously better than "unfair," but the diff table's
fairness column is a genuine trade-off axis, not a correctness axis — every lock in this three-file
set that is fair (ticket, CLH, MCS) pays for it with either shared-line contention or, in
`ReentrantLock`'s fair mode, forbidding barging.

## Cheat sheet

| Lock | Fair | Spin location | Best for | Never use when |
|---|---|---|---|---|
| BackoffLock | No | Shared flag, delayed retry | Retrofitting TAS under moderate contention | Can restructure to CLH/MCS instead |
| ReentrantSpinMutex | No | Shared reference | Learning reentrancy mechanics only | Any production code — use `ReentrantLock` |
| `ReentrantLock` (real) | Configurable | N/A — parks | Production default whenever a lock is needed | Sub-microsecond sections with cores to spare |
| `ReentrantLock(true)` (fair) | Yes (FIFO) | N/A — parks | Observed starvation of a specific caller | Default choice — costs barging throughput |

## Self-test

**Q1.** Why does `ReentrantSpinMutex`'s `holdCount` field not need to be an `AtomicInteger`?

<details><summary>Answer</summary>

Because only the thread that currently owns the lock (as established by winning the CAS on
`owner`) ever reads or writes `holdCount`. No other thread's `lock()` call can reach the
count-touching branch until it too becomes the owner, which cannot happen while the current owner
still holds the `AtomicReference`. The exclusivity the atomic reference already guarantees for
`owner` transitively protects the plain `int`, since there is never a window where two threads
both believe they're the owner simultaneously.

</details>

**Q2.** Why does `BackoffLock` deliberately randomize its retry delay instead of using a fixed
doubling schedule with no randomness?

<details><summary>Answer</summary>

A fixed schedule keeps every backed-off thread synchronized with each other: if two threads both
fail a CAS at the same moment, a purely deterministic doubling schedule has them both wake up and
retry at the same moment again, recreating the exact thundering-herd collision backoff exists to
avoid. Randomizing the delay within the current window spreads retries out in time so collisions
become progressively less likely as the window (and its random spread) grows.

</details>

**Q3.** The consolidated diff table says none of the seven locks built across these three files
support "instrumentation" the way `ReentrantLock` does. Concretely, what does that cost an on-call
engineer debugging a stuck `reserveStake` call in production?

<details><summary>Answer</summary>

With `ReentrantLock`, a `jstack` or JFR-based dump would show the blocked `settlement-ingest-N`
thread as `WAITING`/`TIMED_WAITING` on a named lock object, and identify exactly which thread
currently owns it — turning "why is this thread stuck" into a direct answer. With any of the
spin-based locks built across these three files, a stuck thread shows up as `RUNNABLE`,
indistinguishable from a thread doing legitimate CPU-bound work; the dump gives no indication it's
actually spinning on a lock, let alone which other thread holds it, so diagnosing the stall
requires reasoning about the code rather than reading it off a stack dump.

</details>

**Q4.** Why is `ReentrantLock`'s default construction unfair, and when should you actually reach
for the fair constructor?

<details><summary>Answer</summary>

Unfair (barging) mode lets a thread that arrives right as the lock becomes free acquire it
immediately, without first checking whether other threads are already queued — this is measurably
faster under most real workloads because it avoids unnecessary parking and waking. Fair mode
enforces strict FIFO order, exactly like the ticket lock or CLH/MCS, at the cost of forbidding that
barging. Reach for fair mode only when you have observed actual starvation of some specific caller
under the default policy — not preemptively, since "fair" is a throughput trade-off, not a
correctness improvement.

</details>

**Q5.** Two `settlement-ingest-N` threads each acquire `ledgerLock`, and thread A's cleanup runs on
a different thread than the one that called `lock()`, via a mis-scoped `CompletableFuture.runAsync`.
What does `ReentrantSpinMutex.unlock()` do, and why is that the right behavior rather than a bug?

<details><summary>Answer</summary>

`unlock()` checks `owner.get() != Thread.currentThread()` and throws
`IllegalMonitorStateException` instead of clearing ownership. This is correct, not overly strict:
`lock()`/`unlock()` pairing is defined per-thread, and allowing any thread to release a lock it
doesn't hold would let a completely unrelated thread free the lock while the true owner is still
mid-critical-section, reintroducing exactly the race the lock exists to prevent. The fix is
application-level — never split a lock/unlock pair across an asynchronous boundary — not a
relaxation of the mutex's ownership check.

</details>

---

**Leaves covered:** 4.1.8–4.1.10 (3 leaves)
**Leaves deferred:** none
**Diagrams included:** none
**Target version:** Java 21 LTS
**Lines:** 400
