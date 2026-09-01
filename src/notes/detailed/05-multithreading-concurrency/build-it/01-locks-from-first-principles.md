# 05 Multithreading and Concurrency — Locks from first principles: spinning — BUILD IT (§4.1, leaves 4.1.1–4.1.4)

**Target version: Java 21 LTS.** | **Part 4 of 5** | [Index](../00-index.md)
Previous: [Part 3 interview wrap-up](../92-interview-internals.md) · Next: [Queue locks and reentrancy](01b-queue-locks-and-reentrancy.md)

Every lock in this file — and its companion, [01b](01b-queue-locks-and-reentrancy.md) — guards the
same critical section: `FundsLedger.reserveStake`, the method that moves money from a client's
available balance into a `Reservation` whose `StakeSplit(bonusPortion, cashPortion)` must sum
exactly to the stake, with the bonus bucket never going negative. That invariant is the reason the
section needs a lock at all — two `settlement-ingest-N` threads racing to split the same stake
across bonus and cash can produce a `StakeSplit` that doesn't sum, or a bonus bucket that goes
below zero. Peak load on this path is 1,200 stake reservations/sec; settlements land separately at
up to 3,400/sec (burst) and are not this file's concern, but they explain why the ledger is
contended from two directions at once.

This file covers the three simplest, unqueued spin locks — a bare CAS loop, a coherence-aware
variant of it, and a fair ticket lock — plus the JMH harness that lets you measure spinning against
blocking honestly. [01b](01b-queue-locks-and-reentrancy.md) covers the two queue-based locks (CLH
and MCS), a backoff variant, a reentrant mutex, and the consolidated diff table against
`ReentrantLock` for every lock built across both files.

## Hierarchy before details

**D-199 — Five spin locks, compared**

| Lock | Where each waiter spins | Coherence traffic per acquisition | FIFO fair | Space per waiter | NUMA suitability | AQS derives from this? |
|---|---|---|---|---|---|---|
| TAS spin lock (4.1.1) | The single shared boolean's cache line | O(N) invalidations per release, N = waiters | No | O(1), no per-thread state | Poor — every waiter hammers one line | No |
| Test-and-test-and-set (4.1.3) | Same shared line, but read-only until it looks free | Lower than TAS: waiters only issue a bus/CAS operation when the line already looks unlocked | No | O(1) | Poor, but less traffic than TAS | No |
| Ticket lock (4.1.4) | The shared `nowServing` counter | O(N) invalidations per release — same as TAS, because every waiter still polls one line | Yes | O(1) | Poor | No |
| CLH (4.1.5, in [01b](01b-queue-locks-and-reentrancy.md)) | The **predecessor's** node, via an implicit queue (`prev` links) | O(1) per release — only the true successor's line is touched | Yes (queue order = arrival order) | O(1) per thread if the node is reused via `ThreadLocal` | Good on cache-coherent SMP; still needs a coherent `prev` read | **Yes** — AQS's javadoc names CLH explicitly |
| MCS (4.1.6, in [01b](01b-queue-locks-and-reentrancy.md)) | **Its own** node's flag, set by the predecessor on release | O(1) per release, and the write lands on a line the successor already owns | Yes | O(1) per thread, explicit node with a `next` pointer | Best — no shared line at all, only point-to-point node hand-off | No, but architecturally closer to AQS's node-per-waiter shape |
| Backoff (4.1.8, in [01b](01b-queue-locks-and-reentrancy.md)) | Same as TAS (it wraps a TAS lock) | Lower than plain TAS under contention — waiters retry less often | No | O(1) | Poor, but throughput improves under contention | No |

Read the table as a spectrum: TAS and the ticket lock are simple and unfair-to-the-bus; CLH and
MCS (in 01b) trade a small amount of bookkeeping for making each waiter spin on a *different*
line, which is the single change that makes lock-free scaling possible on real SMP hardware.
Backoff is an orthogonal fix to TAS's specific pathology (retry storms), not a queue-based design
at all. This file stays with the unqueued locks in the top three rows.

## SpinLock — a CAS loop and nothing else

### Mental model

A spin lock is a padlock with a webcam pointed at it. Every thread that wants in just keeps
checking the webcam feed as fast as it can. There's no queue, no doorman, no fairness — whoever
notices the padlock is open first, and successfully clicks the CAS to close it, gets in.

### Why it exists

Before intrinsic locks and `synchronized`, the only primitive available on real hardware was an
atomic read-modify-write instruction (CAS, or the older test-and-set). A spin lock is what you
get from applying that primitive with zero extra machinery: loop until you can flip a boolean
from false to true.

### When to reach for it, and when not

Reach for a spin lock only when the expected wait is shorter than the cost of a context switch —
sub-microsecond critical sections on a machine with spare cores. `ReservationExpiryIndex` inside
`FundsLedger` (an in-memory structure touched on every reservation) is exactly the kind of thing
people are tempted to guard this way, because the critical section is often just a map update.
Never reach for it when the critical section can block (I/O, a downstream call, anything that
can page fault or wait on another lock) — a spinning waiter burns a core the lock holder might
need to make progress, and on an oversubscribed system (more runnable threads than cores) that
turns into priority inversion: the holder gets preempted, and every spinner keeps burning CPU
achieving nothing until the scheduler gets back to the holder.

### How it works

`compareAndSet(false, true)` is the acquire; a plain `set(false)` is the release, because release
doesn't need to be atomic with respect to anything — only one thread (the holder) ever performs
it. `Thread.onSpinWait()` is a JEP 285 (Java 9) hint to the CPU that this is a busy-wait loop; on
x86 it compiles to a `PAUSE` instruction, which reduces the pipeline's speculative-execution
pressure and, on hyperthreaded cores, yields execution resources to the sibling logical core.

**Insight:** `onSpinWait()` changes nothing about correctness — it is pure microarchitectural
politeness. Removing it from the loop below still compiles and still works; it just wastes more
power and starves siblings harder.

```java
import java.util.concurrent.atomic.AtomicBoolean;

public final class SpinLock {
    private final AtomicBoolean locked = new AtomicBoolean(false);

    public void lock() {
        while (!locked.compareAndSet(false, true)) {
            Thread.onSpinWait();
        }
    }

    public void unlock() {
        locked.set(false);
    }
}
```

```java
// FundsLedger.reserveStake, guarded by SpinLock — the running example for this whole file.
public record StakeSplit(Money bonusPortion, Money cashPortion) {
    public StakeSplit {
        if (bonusPortion.amount().signum() < 0) {
            throw new IllegalArgumentException("bonus portion cannot go negative: " + bonusPortion);
        }
    }
}

public final class FundsLedger {
    private final SpinLock ledgerLock = new SpinLock();
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

**Pitfall:** wrapping the body in `try`/`finally` looks like AutoCloseable habit transferred from
`ReentrantLock`, but a raw `SpinLock` has no interrupt or timeout path to worry about — the
`finally` still matters, though, because an exception thrown by `bonusBalance.minus(...)` (e.g. an
arithmetic overflow) must not leave the lock held forever.

> **Definition.** A spin lock is a mutual-exclusion primitive that makes a blocked thread poll an
> atomic flag in a tight loop instead of yielding the CPU, trading throughput-under-contention for
> latency-under-low-contention.

## Measuring spin versus block (4.1.2)

This is not a report of measured numbers. It is a runnable JMH harness plus a statement of the
*expected shape*, explicitly labelled as such.

```java
import java.util.concurrent.TimeUnit;
import java.util.concurrent.locks.ReentrantLock;
import org.openjdk.jmh.annotations.*;
import org.openjdk.jmh.infra.Blackhole;

@State(Scope.Benchmark)
@BenchmarkMode(Mode.Throughput)
@OutputTimeUnit(TimeUnit.MICROSECONDS)
@Warmup(iterations = 5, time = 1)
@Measurement(iterations = 5, time = 1)
@Fork(1)
public class ReserveStakeLockBenchmark {

    private final SpinLock spinLock = new SpinLock();
    private final ReentrantLock reentrantLock = new ReentrantLock();
    private long bonusCents = 1_000_000L;

    // A stand-in for reserveStake's body: cheap arithmetic only, no I/O.
    private void criticalSection(long busyNanos, Blackhole blackhole) {
        long deadline = System.nanoTime() + busyNanos;
        long acc = bonusCents;
        while (System.nanoTime() < deadline) {
            acc = (acc * 31 + 7) % 1_000_000_007L;
        }
        bonusCents = acc;
        blackhole.consume(acc);
    }

    @Benchmark
    @Threads(1)
    public void spinLock100ns(Blackhole bh) { runSpin(100L, bh); }

    @Benchmark
    @Threads(2)
    public void spinLock100ns_2t(Blackhole bh) { runSpin(100L, bh); }

    @Benchmark
    @Threads(8)
    public void spinLock100ns_8t(Blackhole bh) { runSpin(100L, bh); }

    @Benchmark
    @Threads(64)
    public void spinLock100ns_64t(Blackhole bh) { runSpin(100L, bh); }

    @Benchmark
    @Threads(1)
    public void spinLock100us(Blackhole bh) { runSpin(100_000L, bh); }

    @Benchmark
    @Threads(8)
    public void spinLock100us_8t(Blackhole bh) { runSpin(100_000L, bh); }

    @Benchmark
    @Threads(64)
    public void spinLock100us_64t(Blackhole bh) { runSpin(100_000L, bh); }

    @Benchmark
    @Threads(1)
    public void reentrant100ns(Blackhole bh) { runReentrant(100L, bh); }

    @Benchmark
    @Threads(8)
    public void reentrant100ns_8t(Blackhole bh) { runReentrant(100L, bh); }

    @Benchmark
    @Threads(64)
    public void reentrant100ns_64t(Blackhole bh) { runReentrant(100L, bh); }

    @Benchmark
    @Threads(1)
    public void reentrant100us(Blackhole bh) { runReentrant(100_000L, bh); }

    @Benchmark
    @Threads(8)
    public void reentrant100us_8t(Blackhole bh) { runReentrant(100_000L, bh); }

    @Benchmark
    @Threads(64)
    public void reentrant100us_64t(Blackhole bh) { runReentrant(100_000L, bh); }

    private void runSpin(long nanos, Blackhole bh) {
        spinLock.lock();
        try {
            criticalSection(nanos, bh);
        } finally {
            spinLock.unlock();
        }
    }

    private void runReentrant(long nanos, Blackhole bh) {
        reentrantLock.lock();
        try {
            criticalSection(nanos, bh);
        } finally {
            reentrantLock.unlock();
        }
    }
}
```

**expected shape, not measured — run the harness above on your own hardware**

| Threads | 100 ns section | 100 µs section |
|---|---|---|
| 1 | Spin ≈ ReentrantLock. No contention, `lock()` returns on the first CAS either way; ReentrantLock's uncontended fast path (a single CAS in `sync.tryAcquire`) costs about the same as the spin loop's single CAS. | Same — no contention means the lock flavor barely matters versus the 100 µs of real work. |
| 2 | Spin likely wins narrowly. A 100 ns section means the loser waits ~100 ns; that is far cheaper than a park/unpark round trip, so spinning burns less wall time than blocking would. | Roughly even, trending toward ReentrantLock. 100 µs of contention is long enough that a blocked waiter's park/unpark cost is amortized against a much larger hold time. |
| 8 | Spin starts to lose. With 8 threads on a section this short, several spinners are active per release; they collectively burn CPU that could be running other `settlement-ingest-N` work, and cache-line ping-pong on the shared boolean adds real latency to every attempt. | ReentrantLock wins. Enough contention exists that blocked threads are better off surrendering the core; the JVM's adaptive spinning inside `ReentrantLock`'s park path (a short spin before parking) captures whatever benefit remains from short waits. |
| 64 | Spin loses badly, likely catastrophically once waiter count exceeds core count: spinners hold cores the lock holder needs to be *scheduled* on, so total throughput can fall below what a single thread alone would achieve. | ReentrantLock wins clearly. Most waiters are parked, consuming no CPU, and the OS scheduler decides who runs next instead of every core burning cycles polling. |

The crossover argument, stated once and directly: **spinning wins exactly while the expected wait
is shorter than a park/unpark round trip, and loses once waiters start outnumbering cores**,
because a spinning waiter occupies a core the lock holder may need to finish and release. Treat
the following as **order of magnitude only, explicitly not measured**: an uncontended CAS or
volatile read/write is on the order of a few nanoseconds; a full park/unpark round trip through
the OS scheduler is on the order of 1–10 microseconds; an involuntary context switch (the OS
preempting a thread) is in the same low-microsecond range, sometimes higher under load. These
numbers explain the crossover shape above without being a substitute for running the harness.

![Spin versus park: the crossover depends on how long you wait](../diagrams/D-201-spin-vs-park.svg)

**Interview:** "When would you ever write a spin lock instead of using `ReentrantLock`?" — when
the critical section's expected duration is provably shorter than a park/unpark round trip *and*
you have spare cores to burn, which in practice means deep inside a lock-free data structure's
own implementation, not application code.

## TestAndTestAndSetLock — read before you write

### Mental model

Instead of hammering the padlock's webcam with a "try to click it shut" request every single
frame, first just *look* at the feed. Only when it looks open do you actually attempt the click.

### Why it exists

A bare CAS loop issues a cache-coherence-protocol write-intent (or at least a contended
read-modify-write bus transaction) on *every* iteration, even while the lock is obviously still
held. On a cache-coherent multiprocessor, a CAS that fails still typically requires the
requesting core to acquire the cache line in exclusive/modified state (MESI "M"), which
invalidates every other core's copy of that line — including the lock holder's own copy, which it
needs to read/write on release. Every failed CAS from every spinner therefore adds coherence
traffic that competes with the actual lock holder's memory traffic.

### When to reach for it, and when not

Same regime as `SpinLock` — short sections, spare cores — but strictly preferred over a bare TAS
loop whenever more than one or two threads might contend, because the fix costs nothing. There is
no case where plain TAS beats TTAS on real cache-coherent hardware; TTAS is a strict improvement,
not a trade-off.

### How it works

The loop first does a plain (non-atomic, cache-friendly) read of the flag. A plain volatile read
only needs the cache line in Shared state, which every spinning core can hold simultaneously
without invalidating each other. Only when that read reports "unlocked" does the thread attempt
the actual CAS. Under contention, most iterations are cheap shared reads that hit each core's own
cached copy of the line; the (still O(N)) CAS storm only happens in the brief window right after a
release, when every spinner's shared read simultaneously reports "free" and they all race the CAS.

**Insight:** TTAS does not eliminate the invalidation storm on release — it still happens, and it
is still O(N) — it only removes the storm during the *steady-state wait*, while the lock is held
and no release is imminent. That is the entire coherence-traffic win, and it is why the D-199
column says "lower than TAS," not "none."

```java
import java.util.concurrent.atomic.AtomicBoolean;

public final class TestAndTestAndSetLock {
    private final AtomicBoolean locked = new AtomicBoolean(false);

    public void lock() {
        while (true) {
            while (locked.get()) {
                Thread.onSpinWait();
            }
            if (locked.compareAndSet(false, true)) {
                return;
            }
        }
    }

    public void unlock() {
        locked.set(false);
    }
}
```

> **Definition.** Test-and-test-and-set is a spin lock that separates the cheap, cache-friendly
> "does this look free" check from the expensive, coherence-traffic-generating CAS, issuing the
> CAS only when the check suggests it might succeed.

## TicketLock — fair, but one shared line

### Mental model

A deli counter. Every arriving thread takes a numbered ticket (`nextTicket`, incremented
atomically) and then just watches the "now serving" display (`nowServing`) until its number comes
up.

### Why it exists

Both TAS and TTAS are unfair: under contention, whichever spinner happens to win the CAS race
after a release gets in next, which can starve a thread indefinitely (the "convoy" or "lock
lottery" problem) and produces wildly variable tail latency. The ticket lock fixes fairness with
two counters instead of one flag.

### When to reach for it, and when not

Reach for it when strict FIFO ordering matters more than raw throughput — for example, if
`settlement-ingest-N` threads must process reservations in arrival order to preserve an audit
trail's chronology. Do not reach for it purely for performance: it still has every waiter spinning
on the same `nowServing` line, so it inherits TAS's O(N)-invalidations-per-release cost — CLH and
MCS (in [01b](01b-queue-locks-and-reentrancy.md)) strictly dominate it on scalability while also
being fair.

### How it works

`lock()` atomically fetches-and-increments `nextTicket` to get "my number," then spins reading
`nowServing` (a plain volatile read, so it's cache-friendly like TTAS's read phase) until it
equals that number. `unlock()` increments `nowServing`, which is the only write — and it
invalidates every waiter's cached copy of that one line, because every waiter reads the same
address. That single shared line is exactly why the lock still shows up as "poor" on NUMA in
D-199, despite being fair.

```java
import java.util.concurrent.atomic.AtomicInteger;

public final class TicketLock {
    private final AtomicInteger nextTicket = new AtomicInteger(0);
    private final AtomicInteger nowServing = new AtomicInteger(0);

    public void lock() {
        int myTicket = nextTicket.getAndIncrement();
        while (nowServing.get() != myTicket) {
            Thread.onSpinWait();
        }
    }

    public void unlock() {
        nowServing.incrementAndGet();
    }
}
```

**Pitfall:** assuming `nextTicket.getAndIncrement()` can never overflow. Under `int` wraparound
(after ~2^31 acquisitions — entirely plausible on a `FundsLedger` instance processing 1,200
reservations/sec continuously for years) tickets wrap to negative values and the equality check
`nowServing.get() != myTicket` still works correctly, because both counters wrap together and
equality is wraparound-safe; the bug would only appear if you replaced `!=` with `<` for some
other kind of ordering check.

> **Definition.** A ticket lock enforces strict FIFO acquisition order using two monotonically
> increasing counters, at the cost of every waiter still polling one shared cache line.

## Open questions

None for this file — every claim here is either a stable data-structure fact (spin locks, ticket
locks, cache-coherence mechanics) that the house rules say not to re-research, or an explicitly
labelled expected-shape/order-of-magnitude estimate in the 4.1.2 measurement leaf, not a fact
requiring a citation.

## Pitfalls

### Assuming a spin lock is always faster because "no syscall"

**Wrong**

```java
// "This avoids the park/unpark syscall overhead, so it must be faster."
SpinLock fastLock = new SpinLock();
// ...used to guard reserveStake under 64 concurrent settlement-ingest-N threads.
```

Under 64 threads hammering a lock that's held even briefly, this collapses: most cores spend their
time polling a boolean instead of making progress, and the lock holder itself may get preempted
while 63 other cores spin uselessly waiting for it to come back.

**Right**

```java
ReentrantLock ledgerLock = new ReentrantLock();
// Parks waiters past a few tens of contended attempts; scales to high thread counts because
// blocked threads consume no CPU.
```

**Why people believe it:** "no syscall" is true and *is* faster in the uncontended or
low-contention case (leaf 4.1.2's threads=1/2 rows) — the mistake is generalizing a narrow
low-contention win into an always-true rule without checking the thread count and section length
that actually apply.

### Believing the ticket lock's fairness is "free"

**Wrong**

```java
// "TicketLock is fair AND simple — strictly better than TAS, no downside."
TicketLock ledgerLock = new TicketLock();
```

**Right**

Fairness here costs the same coherence-traffic problem as plain TAS — every waiter still spins on
`nowServing`, so under high contention throughput suffers just as much as TAS, just with FIFO
ordering layered on top. CLH/MCS (in [01b](01b-queue-locks-and-reentrancy.md)) get fairness (by
queue order) *and* per-waiter cache lines; there is no reason to pick the ticket lock over CLH
once you're willing to build a queue-based lock at all.

```java
// see 01b-queue-locks-and-reentrancy.md
CLHLock ledgerLock = new CLHLock(); // fair by queue order, without the shared-line cost.
```

**Why people believe it:** "fair" and "scalable" sound like the same axis, but D-199 shows they're
orthogonal — the ticket lock buys fairness on the fairness axis while remaining exactly as poor as
TAS on the coherence-traffic axis.

### Trusting a JMH benchmark's absolute numbers across hardware

**Wrong**

```java
// "I ran ReserveStakeLockBenchmark once on my laptop and the 8-thread spin numbers were fine, so
// SpinLock is safe to ship for reserveStake in production."
```

**Right**

The 4.1.2 harness gives you a *shape* — where the crossover roughly falls — not a portable
absolute number. Core count, whether hyperthreading is enabled, NUMA topology, and even OS
scheduler tuning all shift exactly where the crossover in the expected-shape table lands. Run the
harness on the actual production instance type, at the actual expected thread count
(`settlement-ingest-N` pool size), before trusting any specific number from it.

**Why people believe it:** a benchmark producing concrete numbers feels authoritative, but a
microbenchmark's numbers are only meaningful relative to the hardware and load shape they were
measured under — exactly why this file labels its own table "expected shape, not measured" rather
than printing invented figures.

## Cheat sheet

| Lock | Fair | Spin location | Best for | Never use when |
|---|---|---|---|---|
| SpinLock (TAS) | No | Shared flag | Ultra-short section, few threads | Section can block, or threads ≥ cores |
| TestAndTestAndSetLock | No | Shared flag (read-only until free) | Same as TAS, strictly better | Same as TAS |
| TicketLock | Yes (FIFO) | Shared counter | Needs strict arrival order, low contention | High contention (shares TAS's traffic cost) |
| `Thread.onSpinWait()` | N/A | N/A | Any busy-wait loop — always add it, it's free | Never a substitute for backing off or blocking |
| park/unpark round trip | N/A | N/A | Reference point: ~1–10 µs, order of magnitude only | Never treat as a measured constant |

## Self-test

**Q1.** Why does `TestAndTestAndSetLock` read the flag before attempting the CAS, instead of just
looping on the CAS like `SpinLock`?

<details><summary>Answer</summary>

Because a failed CAS still typically forces the requesting core to pull the cache line into
exclusive/modified state, invalidating every other core's cached copy of that same line —
including the lock holder's. A plain read only needs the line in Shared state, which every core
can hold at once without invalidating anyone. By checking with a cheap shared read first and only
attempting the CAS when the read suggests it will succeed, TTAS removes the coherence-traffic cost
during the steady-state wait, leaving only the unavoidable release-time race where multiple
spinners see "free" simultaneously and briefly compete via CAS.

</details>

**Q2.** In the ticket lock, why is `nowServing.incrementAndGet()` in `unlock()` not itself a
fairness or correctness bug even though every waiter reads the same field?

<details><summary>Answer</summary>

Fairness comes from the *values*, not from avoiding contention on the field: every waiter compares
its own fixed ticket number against `nowServing`, so exactly one waiter's condition becomes true
per increment, in strict arrival order. The cost this table charges the ticket lock is
performance (every waiter's cache line for `nowServing` is invalidated on every release), not
correctness — the FIFO guarantee itself is sound.

</details>

**Q3.** Why does the 100 µs critical section favor `ReentrantLock` even at just 2 threads, while
the 100 ns section still favors the spin lock at 2 threads?

<details><summary>Answer</summary>

The comparison that matters is the *waiting* thread's expected wait against the cost of a
park/unpark round trip (order of magnitude 1–10 microseconds). At 100 ns of hold time, the waiter
expects to wait roughly 100 ns — far cheaper to spin through than to pay for a park and a later
unpark. At 100 µs of hold time, the waiter expects to wait roughly 100 µs — comparable to or
larger than the park/unpark cost, so parking (and freeing the core for other work in the
meantime) is no longer a bad trade even with only one other thread contending.

</details>

**Q4.** What does `Thread.onSpinWait()` actually change about correctness, and what does it
change about performance?

<details><summary>Answer</summary>

Nothing about correctness — every lock in this file compiles, behaves, and terminates identically
with or without it. On performance, it's a hint (JEP 285, Java 9) that the current loop iteration
is a busy-wait; on x86 it typically compiles to a `PAUSE` instruction, which reduces speculative
execution pressure in the busy-wait loop and, on a hyperthreaded core, can yield execution
resources to a sibling logical core doing real work. It's a power/throughput courtesy, not a
correctness mechanism.

</details>

**Q5.** Why does the `ReserveStakeLockBenchmark` harness use `Blackhole.consume(acc)` instead of
just letting `criticalSection` return `void`?

<details><summary>Answer</summary>

Without consuming the computed value, the JIT is free to prove that `acc`'s intermediate
arithmetic has no observable effect and eliminate the entire loop as dead code, which would make
the "critical section" cost effectively zero and invalidate the whole comparison between lock
flavors. `Blackhole.consume` gives the JIT an observable use for the value, forcing it to actually
execute the busy-work loop on every invocation.

</details>

**Q6.** State the crossover argument for spinning versus blocking in one sentence, and name the
one resource a spinning waiter consumes that a parked waiter does not.

<details><summary>Answer</summary>

Spinning wins exactly while the expected wait is shorter than a park/unpark round trip, and loses
once waiters start outnumbering cores, because a spinning waiter occupies a CPU core — a resource
a parked waiter releases entirely — that the lock holder itself may need in order to finish its
critical section and release the lock.

</details>

---

**Leaves covered:** 4.1.1–4.1.4 (4 leaves)
**Leaves deferred:** none
**Diagrams included:** D-199, D-201
**Target version:** Java 21 LTS
**Lines:** 450
