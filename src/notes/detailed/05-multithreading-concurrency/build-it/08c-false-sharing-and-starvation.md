# 05 Multithreading and Concurrency — The false-sharing and starvation harnesses — BUILD IT (§4.8, leaves 4.8.5–4.8.6)

**Target version: Java 21 LTS.** | **Part 4 of 5** | [Index](../00-index.md)
Previous: [The deadlock and livelock harnesses](08b-deadlock-and-livelock.md) · Next: [The ThreadLocal leak and pinning harnesses](08d-threadlocal-leak-and-pinning.md)

Two failure modes with no shared symptom at all: one is a silent throughput cliff with correct
output, the other is a silent permanent hang the JVM's own tooling cannot see. Both live on the
stake-settlement path — the first inside the counters that track per-worker settlement volume,
the second inside the pool that runs the settlement batches themselves.

## 4.8.5 — The false-sharing harness

### What it demonstrates

Two threads writing to **logically independent** memory locations can still contend as if they
were writing the same location, purely because those locations sit on the same CPU cache line.
Every write invalidates the whole line in the other core's cache, forcing a reload before its
next write — the cores end up serialising on cache-coherence traffic despite touching disjoint
data. Separating the two locations by enough padding to land them on different cache lines
(64 bytes on essentially every current x86-64 and aarch64 part) removes the false dependency
entirely.

### The runnable code

```java
package quizstakes.concurrency.harness;

import java.util.concurrent.CountDownLatch;
import java.util.concurrent.TimeUnit;

/**
 * Two settlement-throughput counters, one per worker, written by two
 * different threads at high frequency. Case A places them adjacent in an
 * array (same cache line). Case B pads each counter to its own cache line.
 */
public final class FalseSharingHarness {

    private static final long ITERATIONS = 500_000_000L;

    // --- Case A: adjacent longs, same 64-byte cache line -----------------
    static final class AdjacentCounters {
        volatile long settlementCountWorkerA;
        volatile long settlementCountWorkerB; // sits right after A in memory
    }

    // --- Case B: each counter padded onto its own cache line -------------
    static final class PaddedCounterA {
        // 7 longs (56 bytes) of padding + the 8-byte field itself = 64 bytes
        long p1, p2, p3, p4, p5, p6, p7;
        volatile long settlementCountWorkerA;
    }

    static final class PaddedCounterB {
        long p1, p2, p3, p4, p5, p6, p7;
        volatile long settlementCountWorkerB;
    }

    public static void main(String[] args) throws InterruptedException {
        long adjacentMillis = runAdjacent();
        long paddedMillis = runPadded();

        System.out.println("adjacent (false sharing): " + adjacentMillis + " ms");
        System.out.println("padded   (no false sharing): " + paddedMillis + " ms");
        System.out.printf("ratio: %.1fx%n", (double) adjacentMillis / paddedMillis);
    }

    private static long runAdjacent() throws InterruptedException {
        AdjacentCounters counters = new AdjacentCounters();
        CountDownLatch startGate = new CountDownLatch(1);
        CountDownLatch doneLatch = new CountDownLatch(2);

        Thread settlementWorkerA = new Thread(() -> {
            await(startGate);
            for (long i = 0; i < ITERATIONS; i++) {
                counters.settlementCountWorkerA = i;
            }
            doneLatch.countDown();
        }, "settlement-worker-a");

        Thread settlementWorkerB = new Thread(() -> {
            await(startGate);
            for (long i = 0; i < ITERATIONS; i++) {
                counters.settlementCountWorkerB = i;
            }
            doneLatch.countDown();
        }, "settlement-worker-b");

        long start = System.nanoTime();
        settlementWorkerA.start();
        settlementWorkerB.start();
        startGate.countDown();
        doneLatch.await();
        return (System.nanoTime() - start) / 1_000_000;
    }

    private static long runPadded() throws InterruptedException {
        PaddedCounterA counterA = new PaddedCounterA();
        PaddedCounterB counterB = new PaddedCounterB();
        CountDownLatch startGate = new CountDownLatch(1);
        CountDownLatch doneLatch = new CountDownLatch(2);

        Thread settlementWorkerA = new Thread(() -> {
            await(startGate);
            for (long i = 0; i < ITERATIONS; i++) {
                counterA.settlementCountWorkerA = i;
            }
            doneLatch.countDown();
        }, "settlement-worker-a");

        Thread settlementWorkerB = new Thread(() -> {
            await(startGate);
            for (long i = 0; i < ITERATIONS; i++) {
                counterB.settlementCountWorkerB = i;
            }
            doneLatch.countDown();
        }, "settlement-worker-b");

        long start = System.nanoTime();
        settlementWorkerA.start();
        settlementWorkerB.start();
        startGate.countDown();
        doneLatch.await();
        return (System.nanoTime() - start) / 1_000_000;
    }

    private static void await(CountDownLatch latch) {
        try {
            latch.await();
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
        }
    }
}
```

### What you actually observe when you run it

Order-of-magnitude, never a measured absolute (this ratio is highly sensitive to core topology —
same-socket vs. cross-CCX/cross-socket cores, and to whether the two threads land on cores that
share an L2/L3 level): the adjacent-counters case runs on the order of **2×–8× slower** than the
padded case for the same number of writes. On a machine where the scheduler happens to place
both threads on the same physical core's sibling hardware threads, or where the cache topology
otherwise minimizes cross-core invalidation cost, the ratio narrows; on typical multi-socket or
multi-CCX server hardware it widens. The shape that matters for the interview answer is
**"a small integer multiplier, driven entirely by cache-line placement, with zero change to the
actual work being done."**

**Insight:** both fields in `AdjacentCounters` are individually correct — no data race, no torn
write, no lost update. Each thread only ever writes its own field. The slowdown is pure hardware
mechanics: writing `settlementCountWorkerA` invalidates the entire 64-byte line for every other
core caching it, including the part of the line holding `settlementCountWorkerB`, forcing
`settlementWorkerB`'s next write to first re-fetch ownership of that line (the MESI
Invalid→Exclusive/Modified transition) — and vice versa, every single iteration. This is
"correct" code that is nonetheless pathologically slow, which is precisely why it survives code
review and only shows up as an unexplained throughput ceiling under load.

**Pitfall:** believing a throughput regression must be a synchronization or GC problem because
the code has "no locks, no contention." False sharing produces exactly this profile — CPU-bound,
lock-free, individually correct — and only shows up in a hardware performance counter (cache-miss
rate, or a tool like `perf c2c` on Linux) rather than anywhere Java-level profiling tools
naturally look.

### The fix

Shown inline above as `PaddedCounterA`/`PaddedCounterB` — pad each hot field with enough unused
`long` fields that it, and nothing else contended, lands within its own 64-byte cache line. Java
21's own `java.util.concurrent.atomic.Striped64`/`LongAdder` internals use the equivalent
technique via `@jdk.internal.vm.annotation.Contended` (a JDK-internal annotation not available to
application code without `-XX:-RestrictContended`, which is why hand-rolled manual padding, as
above, remains the portable application-level technique).

### Why the fix works

`[NUM]` — the arithmetic: a `long` is 8 bytes; a typical cache line is 64 bytes; object header
overhead on a compressed-oops 64-bit JVM is typically 12–16 bytes before the first field. Placing
7 padding `long` fields (56 bytes) before the hot field pushes that field's *offset within the
object* forward by 56 bytes; combined with each `PaddedCounterA`/`PaddedCounterB` instance being a
**separate object** (not adjacent fields in one object, as `AdjacentCounters` was), the two hot
fields end up in memory locations that cannot possibly share a 64-byte line, because they are not
even in the same allocation. Once the two counters are guaranteed to be on different cache lines,
writing one produces no coherence traffic that touches the other's line, and each thread's writes
proceed at the speed of its own private cache line — the 2×–8× penalty disappears because its
cause (forced cross-core line invalidation on every write) is structurally removed.

> **Definition:** False sharing is a performance defect where independent variables suffer
> cache-coherence contention because they occupy the same cache line, causing writes by one
> thread to invalidate the line for another thread's unrelated variable — correctness is
> unaffected; only throughput degrades.

**Interview:** "Two threads write to different fields with no shared logical state, but
throughput doesn't scale with cores — what's happening?" — likely false sharing; check whether
the fields are adjacent in memory (same object, same cache line) and pad or separate them onto
distinct cache lines.

---

## 4.8.6 — The thread-pool starvation harness

### What it demonstrates

A single-thread executor whose one worker thread is given a task that itself submits a second
task to the *same* pool and then blocks waiting for that second task's result. Because the pool
has exactly one thread, and that thread is now blocked waiting on `Future.get()`, the second task
can never be dequeued and run — the pool is permanently, silently deadlocked, and none of the
JVM's deadlock tooling sees it, because there is no lock-ownership cycle: the blocking is on a
`Future`, and the thread that would complete it is simply sitting unscheduled in the pool's work
queue forever.

### The runnable code

```java
package quizstakes.concurrency.harness;

import java.util.concurrent.ExecutionException;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.Future;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.TimeoutException;

/**
 * BROKEN: a single-thread settlement-run executor where a settlement batch
 * submits a follow-up task (compute an audit checksum) to the SAME pool and
 * blocks on its result. The pool's only thread is now waiting on work it
 * cannot itself dequeue -- permanent, silent starvation.
 */
public final class StarvationHarness {

    public static void main(String[] args) throws InterruptedException {
        ExecutorService stakeSettlementPool = Executors.newSingleThreadExecutor(r -> {
            Thread t = new Thread(r, "stake-settlement-pool-0");
            return t;
        });

        Future<Integer> outerBatchFuture = stakeSettlementPool.submit(() -> {
            System.out.println(Thread.currentThread().getName() + ": running settlement batch");

            // BROKEN: submits to the SAME single-thread pool and blocks on it
            Future<Integer> checksumFuture = stakeSettlementPool.submit(() -> {
                System.out.println(Thread.currentThread().getName() + ": computing audit checksum");
                return 42;
            });

            try {
                // This blocks forever: the only worker thread is THIS thread,
                // and it cannot service checksumFuture while parked here.
                return checksumFuture.get(5, TimeUnit.SECONDS);
            } catch (TimeoutException e) {
                System.out.println(Thread.currentThread().getName()
                        + ": timed out waiting on checksum -- pool is starved");
                return -1;
            } catch (ExecutionException | InterruptedException e) {
                throw new RuntimeException(e);
            }
        });

        try {
            Integer result = outerBatchFuture.get(10, TimeUnit.SECONDS);
            System.out.println("outer batch result: " + result);
        } catch (TimeoutException e) {
            System.out.println("outer batch never completed -- pool starvation confirmed");
        } catch (ExecutionException | InterruptedException e) {
            throw new RuntimeException(e);
        } finally {
            stakeSettlementPool.shutdownNow();
        }
        // Observed: "computing an audit checksum" line NEVER prints.
        // outerBatchFuture times out after 5s (from the inner checksumFuture.get
        // timeout, if present) or 10s (from the outer get) -- either way, the
        // second task never ran.
    }
}
```

### What you actually observe when you run it

`"stake-settlement-pool-0: running settlement batch"` prints once, immediately.
`"stake-settlement-pool-0: computing audit checksum"` **never prints** — the checksum task sits
in the pool's internal queue forever, because the pool's single worker thread is the same thread
that is blocked inside `checksumFuture.get(...)`. After 5 seconds the inner timeout fires and the
outer task returns `-1`; without that inner timeout (a bare `checksumFuture.get()`), the outer
task — and the whole pool — hangs indefinitely, and `stakeSettlementPool.shutdownNow()` is the
only way out, because `shutdown()` alone would wait for the (never-completing) task to finish.

**Why this is invisible to the deadlock detector, specifically:** `ThreadMXBean
.findDeadlockedThreads()` walks a graph of **monitor and ownable-synchronizer** ownership. A
`Future.get()` block is implemented via a park on the `Future`'s internal completion signal
(`AbstractQueuedSynchronizer`-backed in `FutureTask`), not a lock held by another thread waiting
on this one — there is exactly one thread involved, and it is waiting on a **task**, not on
another **thread**. No ownership edge points back at the waiting thread, so there is no cycle for
the detector to find. `jstack` will show the single worker thread `WAITING` inside
`FutureTask.awaitDone`, which is a real diagnostic clue, but nothing automatically raises an
alarm the way a lock-cycle-based watchdog does for §4.8.3's deadlock.

**Pitfall:** assuming any executor-based design is deadlock-proof because "there are no explicit
locks." Submitting work back into the same bounded-thread pool and blocking on its result is a
structural deadlock risk that has nothing to do with `synchronized` or `ReentrantLock` — it is a
resource-exhaustion deadlock on the pool's own thread capacity, and it gets worse, not better,
the smaller the pool: a `newFixedThreadPool(1)` starves on the very first nested submit-and-wait;
a larger pool merely raises the number of concurrently nested submit-and-waits needed to exhaust
it.

### The fix

```java
package quizstakes.concurrency.harness;

import java.util.concurrent.CompletableFuture;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

public final class StarvationHarnessFixed {

    public static void main(String[] args) {
        // FIX 1: separate pools for work that can nest -- the settlement pool
        // never blocks waiting on the audit pool, and vice versa.
        ExecutorService stakeSettlementPool = Executors.newSingleThreadExecutor(r ->
                new Thread(r, "stake-settlement-pool-0"));
        ExecutorService auditChecksumPool = Executors.newSingleThreadExecutor(r ->
                new Thread(r, "audit-checksum-pool-0"));

        CompletableFuture<Integer> outerBatch = CompletableFuture.supplyAsync(() -> {
            System.out.println(Thread.currentThread().getName() + ": running settlement batch");
            return 0;
        }, stakeSettlementPool).thenComposeAsync(ignored ->
                // FIX 2: compose asynchronously instead of blocking with .get() --
                // no thread ever parks waiting for another task on its own pool.
                CompletableFuture.supplyAsync(() -> {
                    System.out.println(Thread.currentThread().getName() + ": computing audit checksum");
                    return 42;
                }, auditChecksumPool), stakeSettlementPool);

        outerBatch.thenAccept(result ->
                        System.out.println("outer batch result: " + result))
                .join();

        stakeSettlementPool.shutdown();
        auditChecksumPool.shutdown();
        // Observed: both lines print, result prints, no timeout, no hang.
    }
}
```

### Why the fix works

The starvation's structural cause is **one pool serving two roles that can each need the other's
thread capacity at the same time**: the same worker is both "the thing running the outer task"
and "the only thing that could run the inner task," and it cannot be both simultaneously if the
first blocks waiting on the second. Fix 1 removes the cause directly — giving the nested work a
*separate* pool means the settlement pool's thread is never the thread the checksum task is
waiting on, so there is no capacity conflict regardless of how the outer task waits. Fix 2 is a
second, independent line of defence worth understanding on its own: `thenComposeAsync` never
blocks any thread on a `Future` at all — it registers a continuation that runs when the inner
stage completes, so even reusing a single pool for both stages (with a pool of size ≥ 2, since
one thread would still be needed to dispatch the continuation while the other runs the inner
task) would not exhibit this specific hang, because no thread is ever parked inside a blocking
`get()` holding a pool slot hostage.

> **Definition:** Thread-pool starvation (of this shape) occurs when a task submitted to a
> bounded pool depends — directly, by blocking on a `Future`, or indirectly — on another task
> queued in the *same* pool, and the pool has no free thread to run that dependency; the JVM's
> deadlock detector cannot see it because no lock-ownership cycle exists, only a task-scheduling
> dependency the pool itself has no visibility into.

**Interview:** "Why is submitting a task to a single-thread executor and blocking on its result
from within another task on that same executor dangerous?" — it can permanently starve the pool:
the one thread is occupied waiting on work it alone could execute, and no deadlock detector
catches it because the block is on a `Future`, not a lock held by another thread.

## Pitfalls

### Blaming a throughput cliff on GC or lock contention before checking cache-line layout

**Wrong**

```java
// profiler shows: high CPU, no locks held, no GC pauses -- "must be something in the JIT"
```

**Right**

```java
// Check field layout of hot per-thread counters first: are two frequently-written
// fields adjacent in the same object, or in an array? Pad or separate them.
```

**Why people believe it:** false sharing produces a profile — high CPU, zero contention visible
at the Java level, correct output — that does not match any of the failure signatures developers
are trained to look for first (deadlock, lock contention, GC pauses), so it is checked last, if
at all.

### Assuming any hang inside an `ExecutorService`-based pipeline is a deadlock the JVM will report

**Wrong**

```java
// "if there were a deadlock, jstack / our monitoring would have flagged it"
```

**Right**

```java
// Check thread state for WAITING inside FutureTask.awaitDone with no
// corresponding lock-owner edge -- that pattern is pool starvation, not a
// lock deadlock, and needs a dedicated design fix (separate pools, or
// non-blocking composition), not a watchdog.
```

**Why people believe it:** `ThreadMXBean.findDeadlockedThreads()` covers monitor and
ownable-synchronizer cycles reliably enough that "no deadlock detected" gets over-generalised to
"nothing is stuck," when a same-pool submit-and-block hang produces no such cycle at all.

## Cheat sheet

| Aspect | False sharing | Pool starvation |
|---|---|---|
| Correctness affected | no | yes — task never runs |
| Symptom | throughput cliff, high CPU, correct results | permanent hang on one `Future.get()` |
| Detected by `ThreadMXBean` deadlock check | n/a — not a deadlock at all | no — no lock cycle |
| Root cause | independent fields sharing a 64-byte cache line | nested submit-and-block on the same bounded pool |
| Fix | pad/separate fields onto distinct cache lines | separate pools, or non-blocking composition (`thenComposeAsync`) |
| Typical ratio/shape | 2×–8× slower, order-of-magnitude | 0 → ∞ (task simply never executes) |

## Self-test

**Q1.** Why does false sharing not show up as a `synchronized`/lock-contention symptom in a
profiler?

<details><summary>Answer</summary>

Because there is no lock at all — each thread writes only its own field, with no synchronization
primitive involved. The contention is entirely at the hardware cache-coherence level (MESI
invalidation traffic between cores), which Java-level lock-contention profiling does not observe;
it requires a hardware performance-counter tool (e.g. `perf c2c`) to see directly.

</details>

**Q2.** Why does making each counter its own object (rather than padding fields within one shared
object) matter for the fix?

<details><summary>Answer</summary>

Padding fields within the same object only guarantees relative offset separation; if the whole
object still fits inside adjacent cache lines in an unfortunate way, or if array elements of that
object type are packed tightly, false sharing could still occur across instances. Making each
counter a separate heap allocation, combined with sufficient padding, ensures the allocator is
extremely unlikely to place the two hot fields within 64 bytes of each other, regardless of how
either object's internal layout is arranged.

</details>

**Q3.** What is the arithmetic behind choosing 7 padding `long` fields ahead of the hot field?

<details><summary>Answer</summary>

A cache line is 64 bytes. A `long` field is 8 bytes. 7 padding longs contribute 56 bytes; combined
with an 8-byte header contribution already present in a typical compressed-oops object layout (or
simply the field's own preceding offset within the object), this is enough to push the hot field
past the boundary of whatever line an adjacent object's hot field might share, without needing to
reason exactly about the JVM's specific header size, since the two fields are in different objects
entirely.

</details>

**Q4.** Why does `Future.get()` blocking not register as a lock-ownership cycle to
`ThreadMXBean.findDeadlockedThreads()`?

<details><summary>Answer</summary>

`Future.get()` parks the calling thread on the task's own completion signal (an
`AbstractQueuedSynchronizer`-based mechanism internal to `FutureTask`), not on a lock held by
another, specific thread. The detector looks for cycles of threads mutually waiting on each
other's held locks; here there is exactly one thread, waiting on a task with no owning thread to
form a cycle with, so no cycle exists to detect.

</details>

**Q5.** Why does increasing the pool size from 1 to, say, 4 not eliminate the starvation risk in
general, only raise the bar?

<details><summary>Answer</summary>

The structural cause — a task blocking on a `Future` for another task queued in the same
bounded pool — is a function of how many concurrently blocked "outer" tasks there are relative to
pool size, not whether the pool has exactly one thread. With 4 threads, the pool starves once 4
outer tasks are simultaneously blocked waiting on inner tasks that can no longer be scheduled;
the fix is architectural (separate pools or non-blocking composition), not a pool-size tuning
parameter.

</details>

**Q6.** Why does `thenComposeAsync` avoid the starvation that a direct `.get()` call causes, even
if it still used the very same single-thread pool for both stages?

<details><summary>Answer</summary>

`thenComposeAsync` never blocks the calling thread waiting for the inner stage; it registers a
callback to run once the inner `CompletableFuture` completes and returns immediately, freeing the
worker thread to go back to the pool's queue. No thread ever sits parked holding a pool slot
hostage while waiting for another queued task, which is the exact condition that starved the
`.get()`-based version.

</details>

**Q7.** How would you actually confirm false sharing versus another cause of a throughput cliff,
in a real investigation?

<details><summary>Answer</summary>

Check whether the hot fields are laid out adjacently in memory (same object or tightly packed
array), and if a hardware profiling tool is available, look for elevated cache-coherence
invalidation events (e.g. `perf c2c` on Linux, or vendor-specific tools) correlated with the
threads' core placement; then re-test after padding the fields apart and confirm the throughput
recovers with no other code change.

</details>

---

**Leaves covered:** 4.8.5–4.8.6 (2 leaves)
**Leaves deferred:** none
**Diagrams included:** none
**Target version:** Java 21 LTS
**Lines:** 524
