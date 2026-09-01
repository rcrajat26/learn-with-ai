# 05 Multithreading and Concurrency — A striped counter, measured — BUILD IT (§4.4, leaves 4.4.7–4.4.8)

**Target version: Java 21 LTS.** | **Part 4 of 5** | [Index](../00-index.md)
Previous: [The Michael–Scott queue](04c-michael-scott-queue.md) · Next: [A copy-on-write list and a mini CHM](04e-cow-list-and-mini-chm.md)

## 4.4.7 A mini `Striped64` — `[BUILD]`

### Mental model

A single `AtomicLong` settlement counter is one cashier with a line behind them: every one of the
3,400 stake settlements/sec that land in the same burst window queues on the same cache line,
fighting over the same CAS. `Striped64`'s idea is to open more cashiers — a small array of
independent counting cells — and let each thread pick a cashier by a cheap hash of itself, so
contention drops from "everyone against one cell" to "everyone against `NCPU` cells". `sum()`
becomes: walk every cashier's till and add it up. Nobody locks the tills; the till totals are just
allowed to be momentarily stale between two reads.

### Why it exists

Before `LongAdder` (JDK 8), a hot counter under high contention meant either a single
`AtomicLong` — correct, but every thread's CAS fails and retries when two threads land in the same
window, degrading to worse-than-linear scaling as core count rises — or a `synchronized` block,
which serializes completely. Doug Lea's `Striped64` (the package-private base class behind
`LongAdder`/`DoubleAdder`/`LongAccumulator`) trades a single point of truth for many, accepting
eventual consistency on read in exchange for near-linear write scaling.

### When to reach for it, and when not

Reach for striping when the access pattern is dominated by writes to a value that is read rarely
and does not need to be exact at every instant — a request counter, a settlement-throughput gauge,
a metrics tally. Do not reach for it when the counter is read far more often than written (the
per-read cost of walking every cell dominates), when you need the current value as part of a
compare-and-decide operation (`AtomicLong.compareAndSet` for a semaphore-like permit count has no
striped equivalent — you cannot CAS across cells atomically), or when memory is tight and `NCPU`
padded cells per counter is not affordable across thousands of counters.

### How it works

Two fields hold the value: `base`, used directly while there is no contention (the fast path, one
CAS, no array at all), and `cells`, a lazily-allocated `Cell[]` sized to a power of two, grown up to
`Runtime.getRuntime().availableProcessors()`. Each thread hashes to a slot via a **per-thread
probe** — a pseudo-random int stashed on the thread (the real JDK uses `Thread.threadLocalRandomProbe`;
this mini version keeps its own `ThreadLocal<int[]>` so the class is self-contained) — and updates
`cells[probe & (cells.length - 1)]` with a CAS. On a CAS miss the probe is rehashed (not the same
cell retried blindly) so two threads that collided once do not keep colliding. Growth only happens
under proven contention: a miss on an already-allocated table, while holding a `cellsBusy` CAS flag
that acts as a spinlock solely around the resize, never around the counting itself.

Each `Cell` is padded to its own cache line. The JDK's real `@jdk.internal.vm.annotation.Contended`
is a JVM-internal annotation not usable from application code without `-XX:-RestrictContended`; this
mini version fakes the effect with explicit `long` padding fields, which is the portable technique
everyone used before `@Contended` existed and still the one you reach for outside the JDK itself.

```java
import java.util.concurrent.atomic.AtomicLongFieldUpdater;
import java.util.concurrent.atomic.AtomicReferenceFieldUpdater;
import java.util.function.IntUnaryOperator;

/**
 * A striped, eventually-consistent counter for the stake-settlement pipeline
 * (2.8M/day, 3,400/sec burst). Mirrors the shape of {@code java.util.concurrent.atomic.Striped64}.
 */
public class MiniStriped64 {

    /** One cache-line-padded counting cell. */
    static final class Cell {
        volatile long value;
        // Padding: a plain long field is 8 bytes; six of them plus the header and the
        // volatile value field push this object past a 64-byte cache line, so two Cells
        // never share a line and never false-share under concurrent CAS.
        long p1, p2, p3, p4, p5, p6;

        Cell(long initial) {
            this.value = initial;
        }

        boolean cas(long expect, long update) {
            return VALUE.compareAndSet(this, expect, update);
        }

        private static final java.lang.invoke.VarHandle VALUE;
        static {
            try {
                VALUE = java.lang.invoke.MethodHandles.lookup()
                        .findVarHandle(Cell.class, "value", long.class);
            } catch (ReflectiveOperationException e) {
                throw new ExceptionInInitializerError(e);
            }
        }
    }

    private static final int NCPU = Runtime.getRuntime().availableProcessors();

    private volatile long base;
    private volatile Cell[] cells;
    /** Spinlock flag guarding table creation and resize only, never per-increment updates. */
    private volatile int cellsBusy;

    private static final java.lang.invoke.VarHandle BASE;
    private static final java.lang.invoke.VarHandle CELLS_BUSY;
    static {
        try {
            var lookup = java.lang.invoke.MethodHandles.lookup();
            BASE = lookup.findVarHandle(MiniStriped64.class, "base", long.class);
            CELLS_BUSY = lookup.findVarHandle(MiniStriped64.class, "cellsBusy", int.class);
        } catch (ReflectiveOperationException e) {
            throw new ExceptionInInitializerError(e);
        }
    }

    /** Per-thread hash probe, rehashed on collision. Analogue of Thread.threadLocalRandomProbe. */
    private final ThreadLocal<int[]> probe = ThreadLocal.withInitial(() -> {
        int seed = (int) (Thread.currentThread().threadId() * 0x9E3779B9L);
        return new int[] { seed == 0 ? 1 : seed };
    });

    private static int rehash(int probe) {
        probe ^= probe << 13;
        probe ^= probe >>> 17;
        probe ^= probe << 5;
        return probe;
    }

    /** Records one settled stake (or a batched settlement amount) against the counter. */
    public void add(long delta) {
        Cell[] cs = cells;
        long b = base;
        if (cs == null) {
            // Fast, uncontended path: try the shared base directly.
            if (BASE.compareAndSet(this, b, b + delta)) {
                return;
            }
        }
        boolean uncontended = true;
        Cell c;
        int h = probe.get()[0];
        if (cs == null
                || (c = cs[h & (cs.length - 1)]) == null
                || !(uncontended = c.cas(c.value, c.value + delta))) {
            longAccumulateSlowPath(delta, h, cs == null || uncontended);
        }
    }

    /** Handles table creation, growth, and the retry loop after a first miss. */
    private void longAccumulateSlowPath(long delta, int h, boolean wasUncontended) {
        for (;;) {
            Cell[] cs = cells;
            int n;
            if (cs != null && (n = cs.length) > 0) {
                Cell c = cs[(n - 1) & h];
                if (c == null) {
                    if (cellsBusy == 0 && CELLS_BUSY.compareAndSet(this, 0, 1)) {
                        try {
                            if (cells == cs && cs[(n - 1) & h] == null) {
                                cs[(n - 1) & h] = new Cell(delta);
                                return;
                            }
                        } finally {
                            cellsBusy = 0;
                        }
                        continue;
                    }
                    wasUncontended = true;
                } else if (!wasUncontended) {
                    wasUncontended = true;
                } else if (c.cas(c.value, c.value + delta)) {
                    return;
                } else if (n >= NCPU || cells != cs) {
                    // Already at the CPU-count cap, or another thread already resized:
                    // stop growing, just rehash and retry a different cell.
                } else if (cellsBusy == 0 && CELLS_BUSY.compareAndSet(this, 0, 1)) {
                    try {
                        if (cells == cs) {
                            Cell[] grown = new Cell[n << 1];
                            System.arraycopy(cs, 0, grown, 0, n);
                            cells = grown;
                        }
                    } finally {
                        cellsBusy = 0;
                    }
                    continue;
                }
                h = rehash(h);
                probe.get()[0] = h;
            } else if (cellsBusy == 0 && cells == cs && CELLS_BUSY.compareAndSet(this, 0, 1)) {
                try {
                    if (cells == cs) {
                        Cell[] table = new Cell[2];
                        table[h & 1] = new Cell(delta);
                        cells = table;
                        return;
                    }
                } finally {
                    cellsBusy = 0;
                }
            } else if (BASE.compareAndSet(this, base, base + delta)) {
                // Table install lost the race; fall back to base for this attempt.
                return;
            }
        }
    }

    /**
     * A racy read: sums base plus every cell's current value with no synchronization
     * against concurrent adds. Correct as a monitoring/reporting read, never as a
     * decision input (never gate a withdrawal on this number).
     */
    public long sum() {
        long total = base;
        Cell[] cs = cells;
        if (cs != null) {
            for (Cell c : cs) {
                if (c != null) {
                    total += c.value;
                }
            }
        }
        return total;
    }
}
```

`sum()` is racy by design: a `Cell` written after it is read and a `Cell` written before it is read
can both land inside the same call, and the read of `base` and the reads of each `cell.value` are
not a single atomic snapshot. For a settlement counter that only needs "roughly how many settled in
the last second for the dashboard", that is the entire point — exactness would cost the striping
back.

**Insight:** the reason this scales where `AtomicLong` does not is not "more atomics" — it is
**fewer threads sharing each atomic**. CAS cost under contention is dominated by cache-line
ping-pong (MESI invalidation traffic between cores), not by the instruction itself; splitting one
hot line into `NCPU` cold-ish lines removes almost all of that traffic, at the cost of `sum()` now
doing `NCPU` reads instead of one.

**Pitfall:** treating `sum()` as linearizable and using it to decide whether to open the next
payment-run batch ("wait until exactly 3,400 have settled"). It never gives an exact instantaneous
total under concurrent writers — use it for metrics and alarms, and use a real `Ledger` read (with
its own consistency guarantees) for anything that gates money movement.

> A striped counter trades a single exact atomic for many approximate ones: writes scale with the
> number of independent cells contended threads spread across, and `sum()` pays for that scaling by
> becoming a racy, non-linearizable snapshot.

## 4.4.8 Measuring it against `AtomicLong` and `LongAdder` — `[NUM]` `[BUILD]`

### Mental model

The claim "striping is faster under contention" is falsifiable — measure it. JMH exists exactly to
stop "I benchmarked it with `System.nanoTime()` around a for-loop" from producing garbage numbers:
it warms up the JIT, forks a fresh JVM per trial to avoid one benchmark's compiled code polluting
another's, and consumes the counter's result via a `Blackhole` so the JIT cannot prove the whole
loop is dead code and delete it.

### Why it exists

A hand-rolled loop-and-`System.nanoTime()` microbenchmark is wrong in at least four ways that JMH's
harness exists to fix: no JIT warm-up (you measure the interpreter, not steady-state compiled code),
dead-code elimination (an unused result can be optimized away entirely), constant-folding across
loop iterations that would never happen in real call sites, and no isolation between benchmark
methods sharing one JVM's JIT profile. `Striped64`-vs-`AtomicLong` is the textbook case where every
one of those mistakes would flatter the wrong implementation.

### When to reach for it, and when not

Reach for a real JMH harness whenever a design decision hinges on a throughput or latency number —
"is `LongAdder` worth the memory over `AtomicLong` here" is exactly that kind of decision. Do not
reach for it to settle questions that do not turn on nanosecond-scale differences (algorithmic
complexity, correctness, readability), and do not trust a benchmark run on a laptop with other load,
inconsistent core-pinning, or turbo-boost still enabled — variance at that scale swamps the signal.

```java
import org.openjdk.jmh.annotations.*;
import org.openjdk.jmh.infra.Blackhole;

import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicLong;
import java.util.concurrent.atomic.LongAdder;

/**
 * Compares three ways of tallying settled stakes under concurrent writers:
 * AtomicLong (one CAS target), LongAdder (the real striped counter), and
 * MiniStriped64 (this file's teaching version).
 *
 * Run as: java -jar benchmarks.jar SettlementCounterBenchmark
 */
@BenchmarkMode(Mode.Throughput)
@OutputTimeUnit(TimeUnit.MILLISECONDS)
@State(Scope.Benchmark)
@Warmup(iterations = 5, time = 1, timeUnit = TimeUnit.SECONDS)
@Measurement(iterations = 5, time = 1, timeUnit = TimeUnit.SECONDS)
@Fork(2)
public class SettlementCounterBenchmark {

    private final AtomicLong atomicSettlements = new AtomicLong();
    private final LongAdder adderSettlements = new LongAdder();
    private final MiniStriped64 stripedSettlements = new MiniStriped64();

    @Param({"1", "4", "16", "64"})
    public int threadCount;

    @Benchmark
    @Threads(1)
    public void atomicLong_1(Blackhole bh) {
        bh.consume(atomicSettlements.incrementAndGet());
    }

    @Benchmark
    @Threads(4)
    public void atomicLong_4(Blackhole bh) {
        bh.consume(atomicSettlements.incrementAndGet());
    }

    @Benchmark
    @Threads(16)
    public void atomicLong_16(Blackhole bh) {
        bh.consume(atomicSettlements.incrementAndGet());
    }

    @Benchmark
    @Threads(64)
    public void atomicLong_64(Blackhole bh) {
        bh.consume(atomicSettlements.incrementAndGet());
    }

    @Benchmark
    @Threads(1)
    public void longAdder_1(Blackhole bh) {
        adderSettlements.increment();
        bh.consume(adderSettlements.sum());
    }

    @Benchmark
    @Threads(4)
    public void longAdder_4(Blackhole bh) {
        adderSettlements.increment();
        bh.consume(adderSettlements.sum());
    }

    @Benchmark
    @Threads(16)
    public void longAdder_16(Blackhole bh) {
        adderSettlements.increment();
        bh.consume(adderSettlements.sum());
    }

    @Benchmark
    @Threads(64)
    public void longAdder_64(Blackhole bh) {
        adderSettlements.increment();
        bh.consume(adderSettlements.sum());
    }

    @Benchmark
    @Threads(1)
    public void miniStriped64_1(Blackhole bh) {
        stripedSettlements.add(1L);
        bh.consume(stripedSettlements.sum());
    }

    @Benchmark
    @Threads(4)
    public void miniStriped64_4(Blackhole bh) {
        stripedSettlements.add(1L);
        bh.consume(stripedSettlements.sum());
    }

    @Benchmark
    @Threads(16)
    public void miniStriped64_16(Blackhole bh) {
        stripedSettlements.add(1L);
        bh.consume(stripedSettlements.sum());
    }

    @Benchmark
    @Threads(64)
    public void miniStriped64_64(Blackhole bh) {
        stripedSettlements.add(1L);
        bh.consume(stripedSettlements.sum());
    }
}
```

`@Fork(2)` runs each benchmark in two fresh JVMs so one method's JIT profile cannot bleed into the
next's; `Blackhole.consume` forces the JIT to treat every `sum()` result as observably used so the
increment can never be proven dead and dropped.

**No absolute numbers are asserted here** — machine, JVM build, core topology and background load
all move the actual figures, and this note set's research protocol bars presenting benchmark
results as measured constants that were not actually captured on a controlled box. What is stable
across machines is the **shape**:

| Threads | `AtomicLong` vs 1-thread baseline | `LongAdder` vs 1-thread baseline | `MiniStriped64` vs 1-thread baseline |
|---|---|---|---|
| 1 | baseline | roughly at parity with `AtomicLong` (no contention to stripe away) | roughly at parity, fast path only touches `base` |
| 4 | measurable falloff begins — CAS retries start appearing | stays close to linear | stays close to linear, one cell per core is enough to avoid most collisions |
| 16 | falloff compounds — cache-line ping-pong dominates, throughput can fall **below** the 4-thread number | continues scaling, though sub-linearly as internal cell count saturates at `NCPU` | tracks `LongAdder`'s shape closely; small constant-factor gap from the `ThreadLocal` probe lookup this mini version uses instead of a `Thread` field |
| 64 | worst regime: most threads spend most of their time retrying a failed CAS, not making progress | plateaus once cell count is capped at `NCPU` — no further table growth to absorb more threads | plateaus at the same point, same reason |

The order-of-magnitude story: `AtomicLong` throughput **degrades** as thread count rises past core
count, `LongAdder` and `MiniStriped64` **plateau** rather than degrade, and the crossover point
where striping wins is typically single digits of contending threads, not the 64 shown here — 64 is
included to show the plateau, not to claim it is the interesting regime.

**Interview:** "why doesn't `LongAdder` just always beat `AtomicLong`?" — because at low or zero
contention `LongAdder`'s fast path degenerates to the same single CAS on `base` that `AtomicLong`
does, plus a `ThreadLocal`/array-null check that `AtomicLong` skips entirely, so it is a wash or a
slight loss at thread count 1, and the win only appears once contention is real.

## Pitfalls

### Assuming `LongAdder.sum()` is a cheap, exact read

**Wrong**
```java
LongAdder settlementsToday = new LongAdder();
// ... 3,400/sec of settlementsToday.increment() from many settlement-ingest threads ...
if (settlementsToday.sum() == expectedBatchSize) {
    closePaymentRun(); // may never fire, or fire on a stale read
}
```
Under concurrent increments, `sum()` walks every internal cell with no synchronization against
writers; two calls a microsecond apart can return values that are not even monotonically ordered
relative to real time, and an exact-equality gate can miss the target value entirely if two
increments land between reads.

**Right**
```java
long total = settlementsToday.sum();
if (total >= expectedBatchSize) {
    closePaymentRun(); // threshold check, not equality, and only for reporting-grade decisions
}
```
Use `>=` for threshold checks, and reserve exact-count decisions for a source that actually offers
a consistent snapshot (a `Ledger` read inside a transaction), never a striped counter.

**Why people believe it:** `AtomicLong.get()` really is a linearizable, exact read, and `LongAdder`
looks like a drop-in replacement with the same `.sum()`/`.get()`-shaped API, so the mental model of
"just swap the type" silently drops the consistency guarantee along with the contention cost.

### Assuming striping always wins

**Wrong**
```java
// "LongAdder is strictly faster, so replace every AtomicLong in the codebase"
private final LongAdder sequenceNumber = new LongAdder(); // used single-threaded per request
```
On a single-threaded or low-contention path, `LongAdder` carries extra indirection (the `cells`
null-check, the `ThreadLocal` probe lookup) for no benefit, and every `LongAdder` instance is
strictly larger than an `AtomicLong` — one padded `Cell` array's worth of memory that may never be
allocated but whose class metadata and fast-path code still cost something.

**Right**
```java
private final AtomicLong sequenceNumber = new AtomicLong(); // single writer, exact read needed
```
Keep `AtomicLong` where contention is low or where an exact linearizable read is required (a
sequence number, a permit count gating admission); reach for `LongAdder`/`MiniStriped64` only where
both are true: high write contention, and reads that can tolerate an approximate snapshot.

**Why people believe it:** benchmark posts online show `LongAdder` beating `AtomicLong` by 10-100x
under heavy contention, and that headline number gets generalized to "always use `LongAdder`"
without carrying forward the "under heavy contention" qualifier.

## Cheat sheet

| Aspect | `AtomicLong` | `LongAdder` / `MiniStriped64` |
|---|---|---|
| Write path, no contention | 1 CAS | 1 CAS on `base` (same cost) |
| Write path, high contention | 1 CAS, retries under contention, throughput degrades | 1 CAS on a per-thread cell, throughput plateaus |
| Read (`get()`/`sum()`) | exact, linearizable, O(1) | racy, non-linearizable, O(number of cells) |
| Memory | one `long` | `base` + up to `NCPU` padded `Cell`s, allocated lazily |
| Use for | exact counts, CAS-based decisions, permits | hot write-mostly tallies, metrics, throughput counters |
| Underlying JDK class | `AtomicLong` (`java.util.concurrent.atomic`) | `Striped64` → `LongAdder` |
| Padding technique | n/a | `@Contended` in the JDK; explicit `long` fields here |

## Self-test

**Q1.** Why does `MiniStriped64.add` try `base` first instead of going straight to the cell array?

<details><summary>Answer</summary>

Because under no or low contention there is no benefit to striping — a single `CAS` on `base` is
cheaper than allocating a cell array and hashing to a slot. The array is only created lazily, the
first time a CAS on `base` actually fails, which is the signal that contention is real.

</details>

**Q2.** Why is `sum()` racy, and why is that acceptable for this counter but not for a wallet
balance read?

<details><summary>Answer</summary>

`sum()` reads `base` and every `Cell.value` with no coordination against concurrent writers, so
increments landing during the read may or may not be included, and there is no single instant in
time the returned total corresponds to. It is acceptable for a monitoring counter because an
approximate "roughly how many settled" answer is the actual requirement; a wallet balance backs a
decision about whether money can move, which needs a linearizable read from the ledger, not an
approximate walk of independent cells.

</details>

**Q3.** What does growing the cell array up to `NCPU` and no further actually buy?

<details><summary>Answer</summary>

Beyond one cell per core, there cannot be true concurrent contention on more cells than there are
cores actually executing at once, so more cells would only add memory and `sum()` cost without
reducing CAS collisions further. Capping at `NCPU` is the point past which striping stops paying for
itself.

</details>

**Q4.** Why does a CAS miss trigger a probe rehash rather than a retry on the same cell?

<details><summary>Answer</summary>

If two threads collided on a cell once, retrying the same cell with the same probe means they are
likely to collide again on the next attempt too, since nothing has changed about which slot they
hash to. Rehashing moves the retrying thread to a different slot, which spreads out threads that
happened to start in the same bucket.

</details>

**Q5.** Why is `@jdk.internal.vm.annotation.Contended` not simply used here instead of manual
padding fields?

<details><summary>Answer</summary>

`@Contended` is a JVM-internal annotation restricted to the bootclasspath by default; application
code needs `-XX:-RestrictContended` to make it effective, which is not a flag you can assume in an
arbitrary deployment. Manual padding fields achieve the same cache-line isolation portably, at the
cost of being more verbose and dependent on the JVM not reordering/eliminating the unused fields
(which HotSpot does not do for instance fields that are genuinely laid out).

</details>

**Q6.** In the benchmark, why does `@Fork(2)` matter for comparing `AtomicLong` against
`LongAdder`?

<details><summary>Answer</summary>

Running multiple benchmark methods in the same JVM process risks one method's JIT compilation
history (inlining decisions, branch predictor warm state, generated machine code for shared call
sites) contaminating the measurement of the next method. Forking a fresh JVM per set of iterations
isolates each benchmark's steady-state behavior from the others.

</details>

**Q7.** Why does the benchmark pass every result through `Blackhole.consume` instead of just
calling `increment()`/`incrementAndGet()` and discarding the return value?

<details><summary>Answer</summary>

If the JIT can prove a computed value is never observed, it is free to eliminate the surrounding
code as dead — including, in principle, folding away the loop that calls the counter method
entirely. `Blackhole.consume` gives the JIT an observable use for the value so the benchmarked work
cannot be legally optimized away.

</details>

**Q8.** At thread count 1, why might `LongAdder` be marginally slower than `AtomicLong` rather than
identical?

<details><summary>Answer</summary>

Even on the fast, no-contention path, `LongAdder`'s `add` still performs the null check on `cells`
and (in this mini version) a `ThreadLocal` lookup for the probe before falling through to the same
single CAS on `base` that `AtomicLong` performs directly — that extra branch and lookup is a small
but real constant-factor cost `AtomicLong` does not pay.

</details>

---

**Leaves covered:** 4.4.7, 4.4.8 (2 leaves)
**Leaves deferred:** none
**Diagrams included:** none
**Target version:** Java 21 LTS
**Lines:** 579
