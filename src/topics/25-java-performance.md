# 25 — Java Performance Engineering

Scope: how to make a JVM service fast **on purpose** — define the number, measure it, find the layer
that owns the cost, and change the one thing that moves it. Guide 06 owns the runtime memory areas, the
GC generations, the OOM taxonomy and the jstack/jmap/MAT toolkit; guide 05 owns the memory model and
correctness of concurrency. This guide owns the *cost model*: what each mechanism charges you in
nanoseconds, and which of those charges shows up in your p99.

Performance interviews fail in one of two ways. The candidate reaches for a fix with no measurement
("I'd add a cache", "I'd pool the objects"), or the candidate can recite GC collectors but cannot say
what they would *look at first*. Everything below is arranged so that the answer to "what do you do"
is an ordered procedure with a named tool and a named piece of evidence at each step.

---

## 1. The performance method

### 1.1 Start with a number, not an adjective

"Slow" is not a bug report. A performance goal is a four-part statement:

> **p99 latency of `POST /wagers` under 500 rps sustained load must be ≤ 120 ms, measured at the load
> balancer, with ≤ 0.1% errors.**

Metric (p99 latency), workload (500 rps sustained), target (120 ms), measurement point (the LB). Without
the workload the target is meaningless — every system is fast at 1 rps. Without the measurement point
you will argue with someone whose number is different because it excludes queueing.

The three axes, and they trade against each other:

| Axis | Definition | Typical lever | What it costs |
|---|---|---|---|
| **Latency** | time for one operation, as a percentile | smaller batches, less queueing, lower-pause GC | throughput, CPU efficiency |
| **Throughput** | operations per second at acceptable latency | batching, bigger buffers, throughput GC | tail latency |
| **Footprint** | heap/RSS/CPU per instance | smaller caches, compact data, native image | latency and throughput headroom |

**Trap:** optimising throughput and reporting it as a latency win, or vice versa. Batching 50 writes into
one statement can triple throughput and *add* 40 ms to the p99 of the unlucky first request in each batch.
State which axis you moved.

### 1.2 Averages lie; percentiles are the contract

An average hides the shape of the distribution, and latency distributions are always right-skewed and
often multimodal (cache hit vs miss, GC pause vs no pause).

Worked example — 1000 requests, 990 at 10 ms, 10 at 2000 ms:

```text
mean = (990*10 + 10*2000) / 1000 = 29.9 ms     "the endpoint takes 30 ms"
p50  = 10 ms
p99  = ~2000 ms                                 1 in 100 users waits two seconds
```

The mean says 30 ms. Nobody experienced 30 ms.

**Percentile arithmetic that matters in interviews:** a page composed of 10 independent backend calls,
each with p99 = 100 ms, has a probability of `1 - 0.99^10 = 9.6%` of *at least one* call being in its
own tail. So a service p99 becomes a page p90. This is why fan-out amplifies tails and why the tail is
the thing you budget, not the mean. See `22-system-design.md` for the fan-out/hedging discussion and
`10-networking.md` for the per-hop latency budget.

**Trap:** averaging percentiles across instances or across time buckets. `avg(p99)` is not a percentile
of anything. Percentiles must be computed from merged histograms — this is exactly why Prometheus uses
`histogram_quantile()` over bucket counters rather than storing per-instance quantiles (guide 20).

**Trap:** quoting p99 from a 5-minute window during an incident review. At 500 rps a 5-minute window is
150,000 requests, so p99 covers 1,500 requests — statistically fine. At 2 rps it covers 6 requests, and
p99 is noise. Percentile confidence needs volume.

### 1.3 Coordinated omission

The most common way a load test lies. A closed-loop load generator with N threads issues a request,
**waits for the response**, then issues the next. When the server stalls for 1 s, the generator does not
send the requests it was supposed to send during that second — it simply sends fewer. The slow period is
under-sampled, so the recorded p99 is far better than reality.

```text
Intended: 1 request every 10 ms for 1000 ms  → 100 requests
Server stalls 500 ms mid-test.
Closed loop records: 50 fast requests + 1 request of 500 ms → p99 looks like ~500 ms
Truth (open loop):   50 fast + 50 requests that queued behind the stall,
                     with latencies 500, 490, 480 … 10 ms → p99 ≈ 500 ms, p50 ≈ 250 ms
```

The stall's cost is borne by every request that *should have been in flight*. Fixes: use an open-loop /
constant-rate generator (wrk2, Gatling with `constantUsersPerSec`, JMeter with a precise throughput
timer), or correct for it (HdrHistogram's `recordValueWithExpectedInterval`).

**Trap:** claiming "we load-tested to 5000 rps and p99 was 40 ms" from a closed-loop tool with a fixed
thread count. That tool measured the server's *service time*, not the client's *response time*, and the
two diverge exactly where you care.

### 1.4 The USE method as a first sweep

For each resource — CPU, memory, disk, network, and each software resource (thread pool, connection
pool, queue) — check three things:

| Check | Question | Where you read it |
|---|---|---|
| **Utilisation** | what fraction of time is it busy | `top`, container CPU throttle metric, pool active count |
| **Saturation** | is work queued waiting for it | run queue length, `LinkedBlockingQueue.size()`, pool queue depth, `iowait` |
| **Errors** | is it failing/rejecting | `RejectedExecutionException` count, connection timeouts, TCP retransmits |

Saturation is the signal that finds problems utilisation misses. A thread pool at 40% CPU with 8,000
tasks queued is not underutilised — it is saturated on something else (usually a downstream call or a
lock). Guide 11 has the Linux command set; guide 20 has the metric names.

### 1.5 Little's law — the arithmetic you should do out loud

`L = λ × W` — average concurrency = arrival rate × average residency time. Rearranged, it is the only
thread-pool sizing formula you need.

```text
Target: 500 rps. Each request spends 200 ms total, of which 190 ms is waiting on
Postgres and the payments API, 10 ms is CPU work.

Concurrency required: L = 500 × 0.200 s = 100 in-flight requests
  → need ~100 threads (IO-bound), and a DB pool that can sustain the DB share:
    DB concurrency = 500 × 0.150 s = 75 connections in flight.
CPU required:      500 × 0.010 s = 5 CPU-seconds/second = 5 cores busy.
```

Three conclusions fall out immediately: 100 threads is right and 500 is waste; a 20-connection Hikari
pool caps you at `20 / 0.150 = 133 rps` no matter how many threads you add; and you need ≥ 5 cores of
headroom, so a 2-core container cannot hit the target at any thread count.

**Trap:** "more threads = more throughput." Once the bottleneck resource is saturated, extra threads only
add queueing — latency rises, throughput is flat, and context-switch and cache-pollution cost makes
throughput *fall*. The formula tells you the ceiling; threads above it convert into latency.

### 1.6 Amdahl's and the universal scalability law

Amdahl: with `p` the parallelisable fraction, speedup on `n` cores is `1 / ((1-p) + p/n)`.

```text
p = 0.95, n = 16  → 1 / (0.05 + 0.0594) = 9.1x     (57% efficiency)
p = 0.95, n = 64  → 1 / (0.05 + 0.0148) = 15.4x    (24% efficiency)
p = 0.95, n = ∞   → 1 / 0.05 = 20x                 hard ceiling
```

A 5% serial section caps you at 20x forever. This is why one `synchronized` block on a hot path caps
the whole service, and why the *first* question about a scaling failure is "what is serial here" — a
global lock, a single-partition write, an `AtomicLong` counter, a shared `Random`.

The **universal scalability law** adds a coherency term (`κ`) for cross-core communication cost. Its
practical consequence is that real throughput curves have a *peak* and then decline — beyond some
concurrency, cache-line ping-pong and lock handoff cost more than the added parallelism buys. When your
throughput-vs-threads graph turns downward, you are seeing coherency, not saturation.

### 1.7 Measure, change one thing, measure again

The discipline, in order:

1. Reproduce with a load profile that resembles production (same key distribution — uniform keys hide
   hot-key and cache-miss behaviour).
2. Record a baseline with a percentile histogram, not a mean.
3. Profile to find *where* time goes. Do not guess.
4. Change **one** thing.
5. Re-measure with the same harness; keep the delta if it is outside run-to-run noise.

**Trap:** optimising without a profile. The intuition-to-reality hit rate on JVM bottlenecks is poor —
the cost is almost never where the code looks expensive. It is in serialisation, logging, reflection,
a missing index (guide 09), or a chatty N+1 (guide 08).

---

## 2. Benchmarking correctly

### 2.1 Why the naive loop is worthless

```java
long start = System.nanoTime();
for (int i = 0; i < 1_000_000; i++) { scoreWager(i); }   // measures almost nothing
System.out.println(System.nanoTime() - start);
```

Every one of these will corrupt the number:

- **Warmup / tiering.** The first few thousand iterations run interpreted, then C1, then C2. You measured
  a blend of three implementations weighted toward the slowest.
- **Dead-code elimination.** `scoreWager(i)`'s result is unused; C2 proves the call has no observable
  effect and deletes it. You time an empty loop.
- **Constant folding.** If the input is a constant or effectively-final field, C2 computes the answer at
  compile time and the loop body becomes a load.
- **Loop unrolling and hoisting.** Invariant computations move out of the loop; the loop is unrolled 8x,
  amortising the bounds check. Your per-op cost is not the per-op cost in real calling contexts.
- **On-stack replacement (OSR).** The long-running loop gets compiled *while executing*, so the frame is
  swapped mid-flight. OSR-compiled code is often worse than a normally compiled version, so you measure
  a shape production never runs.
- **Profile pollution.** One benchmark method that exercises three implementations of an interface makes
  the call site megamorphic; a separate JVM would have seen it monomorphic (§ 3.4).
- **`System.nanoTime()` granularity and cost.** ~20–30 ns per call on Linux; timing anything under
  ~100 ns per operation individually is measuring the clock.

### 2.2 JMH mechanics

JMH exists to defeat all of the above. The parts and what each defends against:

| Element | Mechanism | Defends against |
|---|---|---|
| `@Fork(n)` | runs each benchmark in a **fresh JVM**, n times | profile pollution, per-JVM luck, one-off layout |
| `@Warmup(iterations=)` | discarded iterations before measurement | tiering, OSR, allocation-profile settling |
| `@Measurement(iterations=)` | timed iterations, reported with error bars | run-to-run variance |
| `@State(Scope.*)` | holds inputs in objects JMH creates, not constants | constant folding |
| `Blackhole.consume(x)` | opaque sink the JIT cannot see through | dead-code elimination |
| returning a value | JMH implicitly blackholes the return | DCE, for single results |
| `@OperationsPerInvocation(n)` | divides the measured time by n | reporting per-batch time as per-op |
| `@CompilerControl` | forbid/force inlining of a method | measuring inlined-away work |
| `@Setup(Level.Invocation)` | per-invocation fixture | state carry-over (use sparingly, it is costly) |

```java
@BenchmarkMode(Mode.AverageTime)
@OutputTimeUnit(TimeUnit.NANOSECONDS)
@Warmup(iterations = 5, time = 1) @Measurement(iterations = 10, time = 1) @Fork(3)
@State(Scope.Benchmark)
public class WagerScoreBench {
    private List<Wager> wagers;                       // state, so not constant-folded
    @Setup public void setup() { wagers = TestData.wagers(1_000); }

    @Benchmark @OperationsPerInvocation(1_000)
    public void scoreAll(Blackhole bh) {
        for (Wager w : wagers) bh.consume(scoreWager(w));   // blackhole per element
    }
}
```

**Return value vs `Blackhole`:** return the single result when there is one — it is cheaper and JMH
handles it. Use a `Blackhole` when the loop produces many values, because returning only the last one
lets C2 eliminate the rest. Note a blackhole call is not free (~1–2 ns); for sub-nanosecond operations
prefer accumulating into a field and returning it.

**`Mode` choice:** `Throughput` (ops/s) for capacity questions, `AverageTime` for per-op cost,
`SampleTime` when you need the benchmark's *own* percentiles (the only mode that reports p99),
`SingleShotTime` for cold-start/warmup measurement.

### 2.3 JMH profilers

Run with `-prof`; these turn a number into an explanation:

| Profiler | Output | Use for |
|---|---|---|
| `-prof gc` | bytes allocated **per operation** (`gc.alloc.rate.norm`) | proving an allocation change; this number is deterministic and the best regression gate |
| `-prof perfasm` | hottest assembly with source mapping (Linux + perf) | verifying inlining, vectorisation, bounds-check removal |
| `-prof perfnorm` | hardware counters per op: cycles, instructions, cache misses, branch misses | distinguishing "more work" from "worse cache behaviour" |
| `-prof stack` | sampled stacks inside the benchmark | finding unexpected callees |
| `-prof jfr` | a JFR recording of the run | correlating with production JFR analysis |

`gc.alloc.rate.norm` is the single most useful JMH output for application code. "This change reduced
allocation from 464 B/op to 32 B/op" is a claim that reproduces; "it was 12% faster" often is not.

### 2.4 What a microbenchmark cannot tell you

A microbenchmark measures a method in an artificially favourable world: hot caches, one code path, no
competing threads, a monomorphic call site, and a JIT profile tuned to the benchmark alone. Production
has a cold instruction cache, a megamorphic profile, and GC running. So: use JMH to compare *two
implementations of the same small thing*, and use production profiling (§ 8) to decide *which small
thing matters*. A 3x win on 0.5% of the profile is 0.3%.

---

## 3. JIT compilation as a performance mechanism

Guide 06 § 5 covers the tier structure and warmup. Here: the optimisations, their budgets, and how you
lose them.

### 3.1 Tiering and the counters

HotSpot compiles a method when `invocations + backedges` crosses a threshold, scaled by compile-queue
length. Approximate defaults: C1 (tier 3, profiling) around 200 invocations, C2 (tier 4) around 5,000
invocations or 40,000 loop back-edges. A loop that runs long enough triggers **OSR**: the running frame
is replaced by compiled code mid-execution.

Consequences you should be able to state: a method called 100 times per request reaches C2 in seconds;
a method called once per nightly batch never leaves the interpreter, and optimising its bytecode is
pointless. Short-lived JVMs (Lambda, CLI tools, CI jobs) may never reach peak — that is the entire
motivation for AOT (§ 3.7).

### 3.2 Profile-guided optimisation

C1's tier-3 code collects a profile per bytecode: branch taken/not-taken counts, receiver types at each
virtual call site, null-seen flags, array types. C2 compiles *against that profile* and does things a
static compiler cannot:

- Prune branches never taken (an `if (debugEnabled)` that was always false compiles to an
  **uncommon trap** — a jump to deoptimisation, costing zero in the fast path).
- Devirtualise and inline virtual calls when the profile shows one or two receiver types.
- Assume no null, no exception, and a specific array type, guarded by a cheap check.

If an assumption is violated later, the code **deoptimises**: execution transfers back to the
interpreter, the frame is reconstructed, the profile is updated, and the method is recompiled. A method
that repeatedly deoptimises ("deoptimize/reprofile" storms) can be slower than never compiling.

**Trap:** thinking a rare-path code change is free. Adding a branch that is *rarely but not never* taken
converts a pruned uncommon trap into a real branch — and if it is taken during warmup, the whole method
recompiles with a worse profile.

### 3.3 Inlining and its budgets

Inlining is the enabling optimisation — escape analysis, constant propagation, lock elision and
vectorisation all work within one compiled unit, so anything not inlined is opaque.

| Flag | Default | Meaning |
|---|---|---|
| `MaxInlineSize` | 35 bytes of bytecode | any method this small is inlined even if not hot |
| `FreqInlineSize` | 325 bytes of bytecode | a *hot* method up to this size is inlined |
| `MaxInlineLevel` | 15 | maximum inlining depth |
| `MaxTrivialSize` | 6 bytes | always inlined (trivial accessors) |
| `InlineSmallCode` | ~2000 bytes native | do not inline an already-compiled method whose native code is bigger |

Practical reading: **keep hot methods small.** A 400-byte hot method is above `FreqInlineSize` and will
not be inlined into its caller, which also blocks escape analysis on objects it creates. Splitting a hot
method into a small fast path plus a large `@CompilerControl(DONT_INLINE)`-able slow path is a real
technique — it is exactly how the JDK writes `StringBuilder` and `HashMap` internals.

Inspect with `-XX:+UnlockDiagnosticVMOptions -XX:+PrintInlining` (and JITWatch to read it), where "too
big", "hot method too big", "callee is too large" and "already compiled into a big method" are the
messages that explain a missed optimisation.

### 3.4 Monomorphic, bimorphic, megamorphic

The single most interview-relevant JIT fact.

| Call site | Distinct receiver types seen | What C2 emits | Cost |
|---|---|---|---|
| **Monomorphic** | 1 | class-check guard + **inlined body** | ~free; enables all downstream optimisation |
| **Bimorphic** | 2 | two guards + both bodies inlined | cheap |
| **Polymorphic** | 3–4 (with `TypeProfileWidth`) | inline cache or vtable dispatch | a real call, no inlining |
| **Megamorphic** | many | vtable/itable dispatch | indirect branch, likely mispredicted, **no inlining at all** |

Interface dispatch is worse than class dispatch when megamorphic: `invokeinterface` needs an itable
scan, whereas `invokevirtual` is a fixed vtable offset.

The consequence engineers hit in real systems: a `Handler` interface with 12 implementations, dispatched
from one hot loop, produces a megamorphic site — so nothing inlines, and every object the handler
allocates escapes analysis. Fixes: split the loop by type so each site sees one implementation, or batch
by type before dispatch, or accept it and make the handler bodies coarse enough that dispatch cost is
amortised. Design guidance in `24-design-patterns-architecture.md` (Strategy) — the pattern is correct;
the cost is real and belongs in the trade-off sentence.

**Trap:** claiming `final` methods are faster. HotSpot devirtualises on the *observed profile* and on
class-hierarchy analysis, so a non-final method with one loaded implementation inlines just as well.
`final` helps documentation and CHA stability, not the dispatch cost you already had.

### 3.5 Escape analysis, scalar replacement, lock elision

C2 analyses whether an allocated object can be observed outside the compiled unit:

- **NoEscape** → **scalar replacement**: the object is never allocated at all; its fields become
  registers or stack slots. This is why "allocation-free" code is often the *same source* as allocating
  code, just successfully inlined.
- **ArgEscape** → passed to a method that does not store it; still allows **lock elision** and some
  stack allocation.
- **GlobalEscape** → stored to a field, returned, or thrown: real heap allocation, no elision.

Escape analysis requires inlining. So a hot loop calling a too-large method that creates an `Optional`
or an iterator will allocate; the identical code with a smaller callee will not. This is the mechanism
behind "the JIT makes small immutable objects free — sometimes."

**Lock elision** removes `synchronized` on an object proven thread-local (the classic
`StringBuffer`-inside-a-method case). **Lock coarsening** merges adjacent synchronized blocks on the same
object into one, reducing acquire/release pairs.

**Trap:** relying on escape analysis for a latency SLO. It is best-effort and silently disappears when
inlining fails after a code change, a new implementation loads, or a deopt occurs. Verify with
`-prof gc` (allocation per op) rather than assuming.

### 3.6 Observing compilation

```bash
java -XX:+PrintCompilation MyApp                # one line per compilation event
#  1234  345 %     4  com.qs.WagerScorer::score @ 12 (78 bytes)
#  '%' = OSR, '4' = tier, 's' = synchronized, '!' = has exception handlers,
#  'made not entrant' / 'made zombie' = deoptimisation
java -XX:+UnlockDiagnosticVMOptions -XX:+PrintInlining MyApp
java -XX:+UnlockDiagnosticVMOptions -XX:+LogCompilation -XX:LogFile=jit.log MyApp  # for JITWatch
```

Repeated "made not entrant" on a hot method is the fingerprint of a deopt storm. The code cache is
finite (`-XX:ReservedCodeCacheSize`, 240 MB default with tiered compilation); exhausting it makes the
JIT shut down and the whole service silently reverts toward interpreted speed — a real production
failure mode in very large apps and one that guide 06's table names as "code cache full".

### 3.7 Warmup, AOT, and native image

| Approach | Startup | Time to peak | Peak throughput | Cost |
|---|---|---|---|---|
| Plain JVM | slowest | seconds–minutes | highest | warmup penalty on every start |
| **AppCDS** (`-XX:SharedArchiveFile`) | −20–40% startup | unchanged | unchanged | build a class archive; almost free win |
| **AOT cache / Project Leyden** (JDK 24+ `-XX:AOTCache`) | much faster | shorter | near-JVM | training run required |
| **CRaC / checkpoint-restore** | ~ms (restores a warmed image) | already warm | JVM peak | must handle open resources at checkpoint; Linux-specific |
| **GraalVM native-image** | ~ms | immediate, flat | typically 10–30% below JVM peak | closed-world: reflection/proxies need config; no JIT reprofiling |

Choose by lifetime: long-lived services want the JIT (peak throughput matters, warmup is amortised);
serverless functions and CLI tools want native-image or CRaC (they may never reach peak). This is also
why a health check that goes green instantly is dangerous — traffic hits an interpreted JVM. Ramp with
readiness gates and small initial weights (guide 19 probes; guide 10 load balancing).

---

## 4. Allocation and GC as a latency source

Guide 06 covers generations, the collector list and the OOM taxonomy. Here: the cost model.

### 4.1 Allocation is cheap; collection is not free

Each thread owns a **TLAB** (thread-local allocation buffer) carved from Eden. Allocation is a pointer
bump plus a limit check — roughly 10 instructions, a few nanoseconds, no synchronisation. Object headers
are pre-zeroed in bulk when the TLAB is issued.

So the cost of allocation is not the `new`; it is:

1. **Young GC frequency** = allocation rate ÷ Eden size. Doubling allocation rate doubles GC count.
2. **Copy cost per young GC** ∝ *surviving* bytes (guide 06's generational hypothesis).
3. **Cache pollution** — a high allocation rate streams new memory through L1/L2 and evicts your working
   set, which shows up as slowness with no GC pause at all.
4. **Promotion**, if objects survive: old-gen pressure → mixed/full collections.

Allocation rate is the number to look at. `-Xlog:gc` plus arithmetic, or JFR's `TLABAllocation`, or
Micrometer's `jvm.gc.memory.allocated`:

```text
Young GC every 1.2 s, Eden 512 MB → ~427 MB/s allocated.
At 500 rps that is 854 KB per request. A JSON API request should be tens of KB.
→ the problem is a per-request allocation bug, not the collector.
```

**Trap:** "object pooling is faster." Almost always false on a modern JVM for ordinary objects. Pooling
converts cheap, cache-warm, young-gen-collected objects into long-lived old-gen objects that survive
minor GCs (so you pay copy cost), require card-table write barriers on every store into them (§ 4.3),
add a synchronised or CAS acquire/release, and reintroduce state-reset bugs. Pool only what is genuinely
expensive to construct or bounded by an external resource: threads, DB connections, sockets, large
`ByteBuffer`s (especially direct buffers), and heavyweight parsers.

**Trap:** treating `-XX:+UseStringDeduplication` as free. It dedupes identical `byte[]` backing arrays
*during GC*, so it adds GC work and a dedup table, and it does nothing for distinct strings. It helps a
narrow case: many duplicate long-lived strings. Interning by hand (`String.intern()`) is worse — it puts
entries in a native table that older JVMs collected poorly and serialises on a lock.

### 4.2 Humongous allocations

In G1, any object larger than **half a region** is *humongous* and is allocated directly into a
contiguous run of old-gen regions. Region size defaults to `heap/2048` clamped to 1–32 MB, so with a
4 GB heap regions are 2 MB and anything over 1 MB is humongous.

Consequences: humongous objects are not collected by ordinary young GCs (until later G1 versions
reclaim short-lived ones eagerly), they need contiguous regions so they can fail to allocate while the
heap has free space (fragmentation), and a stream of them triggers full GCs. A service that reads 4 MB
JSON payloads into `byte[]` is generating humongous garbage.

Fixes: stream instead of buffering whole payloads, chunk large arrays, or raise `-XX:G1HeapRegionSize`
so the objects fall under the threshold. Look for `Humongous Allocation` in the GC log cause field.

### 4.3 Write barriers and the card table — the cost you pay on every store

Generational collectors must find old→young references without scanning old gen. So every **reference
store** to a heap object executes a **write barrier**: G1's post-write barrier marks the 512-byte "card"
containing the field as dirty and, for cross-region references, enqueues an entry into a remembered-set
buffer. G1 also has a *pre*-write barrier for concurrent marking (SATB), making its barrier heavier
than Parallel GC's simple card mark.

This is a real, unavoidable tax measured in a few instructions per reference field write — which is why:

- Primitive arrays (`int[]`, `long[]`) cost nothing at store time; `Integer[]` and `List<Integer>` pay a
  barrier per element write.
- A large long-lived object mutated frequently (that pooled buffer, that cache entry) dirties cards and
  grows remembered sets, adding to every subsequent young-GC root-scan.
- Concurrent collectors trade barrier cost for pause time: ZGC uses **load** barriers (cost on read,
  which is more frequent) to relocate objects concurrently.

### 4.4 Safepoints and time-to-safepoint

A **safepoint** is a state in which all thread stacks are walkable, so GC and other VM operations can
run. Threads poll at method returns and loop back-edges; when the VM requests a safepoint, it must wait
for the *slowest* thread to reach one. That wait is **time-to-safepoint (TTSP)** and it is *not* counted
in the GC pause number in most tools — a 200 ms TTSP with a 5 ms GC looks like a 5 ms GC and a
mysterious 200 ms latency spike.

Classic TTSP causes:

- **Counted loops.** `for (int i = 0; i < n; i++)` over an `int` counter historically had its safepoint
  poll optimised away, so a loop over 100 M elements is one uninterruptible unit. Mitigated by loop strip
  mining (`-XX:+UseCountedLoopSafepoints`, on by default modern JDKs) which chunks the loop; a `long`
  counter keeps the poll.
- **Page faults inside the safepoint path** — swapping, or first-touch of a large heap. Use
  `-XX:+AlwaysPreTouch` so the pages are faulted in at startup, not during a pause.
- **Slow VM operations that piggyback on safepoints**: heap dumps, `jstack`, biased-lock revocation
  (historically), `Thread.getAllStackTraces`, deoptimisation, class redefinition by an APM agent.
- **Blocking in JNI/native** — the thread is already "in native" so it does not block the safepoint, but
  a thread doing long CPU-bound native work does.

Make TTSP visible, always:

```bash
-Xlog:safepoint                      # per-safepoint: reason, TTSP, and operation time
# or
-XX:+PrintSafepointStatistics -XX:PrintSafepointStatisticsCount=1   # older JDKs
```

**Trap:** blaming GC for every latency spike. `-Xlog:safepoint` regularly shows the pause was a
*non-GC* VM operation — a periodic heap-dump-on-schedule, a monitoring agent enumerating threads, or a
revoke storm. Reading the safepoint log distinguishes them in seconds.

### 4.5 Selecting a collector by SLO

| Collector | Pause behaviour | Throughput | Footprint/CPU | Choose when |
|---|---|---|---|---|
| **Serial** | long, single-threaded | low | smallest | 1-vCPU container, tiny heap, batch |
| **Parallel** | STW, scales with cores, tens of ms–seconds | **highest** | low overhead | batch/ETL where total time matters and pauses do not |
| **G1** (default) | soft target `MaxGCPauseMillis`, default 200 ms; typically 20–200 ms | good | moderate (remembered sets, SATB barriers) | general services; the default you should justify leaving |
| **ZGC** (generational, JDK 21+) | sub-millisecond, independent of heap size | ~5–15% below Parallel | higher CPU + ~heap overhead for barriers/relocation | strict tail-latency SLO, large heaps (10 GB–TB) |
| **Shenandoah** | ~1–10 ms, concurrent compaction | similar to ZGC | Brooks-pointer forwarding overhead | low pause on smaller heaps; strong in OpenJDK/RHEL builds |
| **Epsilon** | none (never collects) | n/a | n/a | testing allocation behaviour; short jobs that fit in heap |

The decision rule to say out loud: **"if my p99 budget is 100 ms and G1 pauses 150 ms, no application
tuning will fix it — that is a collector choice. If G1 pauses 15 ms and my p99 is 900 ms, the collector
is not the problem and switching it wastes a week."** Prove which case you are in from the GC log first.

Baseline flags worth defending in an interview:

```bash
-Xms4g -Xmx4g                       # equal: no resize pauses, deterministic footprint
-XX:MaxRAMPercentage=70             # in containers, instead of fixed -Xmx (guide 06 § 7)
-XX:+AlwaysPreTouch                 # pay page-fault cost at startup, not in a pause
-XX:+UseG1GC -XX:MaxGCPauseMillis=100
-Xlog:gc*,safepoint:file=/var/log/gc.log:time,uptime,level,tags:filecount=5,filesize=20M
-XX:+HeapDumpOnOutOfMemoryError -XX:+ExitOnOutOfMemoryError
```

### 4.6 Reading a G1 log line by line

```text
[12.345s][info][gc] GC(42) Pause Young (Normal) (G1 Evacuation Pause)
                     3891M->412M(4096M) 38.271ms
```

- `GC(42)` — sequence number; correlate with the safepoint log.
- `Pause Young (Normal)` — young evacuation. `(Concurrent Start)` means it also began a marking cycle;
  `(Mixed)` means old regions were included; `Pause Full` means G1 gave up on incremental collection.
- `(G1 Evacuation Pause)` — the cause. `(Humongous Allocation)`, `(G1 Periodic Collection)`,
  `(Metadata GC Threshold)`, `(System.gc())` each point somewhere different.
- `3891M->412M(4096M)` — heap before → after (total). **The "after" number after a full/old collection
  is the live set.** A monotonically rising post-collection floor is a leak (guide 06's leak workflow).
- `38.271ms` — the pause. Add `-Xlog:safepoint` to learn how much *more* time threads spent reaching it.

What to compute from the log, not eyeball:

```text
Allocation rate  = (heap_after[n-1] → heap_before[n]) / interval
GC overhead      = sum(pause) / wall time     ; >5% is a problem, >10% is the story
Promotion rate   = old-gen growth per young GC ; high = wrong tenuring or genuinely long-lived data
Live set         = heap after a full GC        ; heap should be ≥ 2–3x live set for G1 to breathe
```

`Pause Full (Allocation Failure)` or `to-space exhausted` means evacuation had nowhere to copy to:
the heap is too small, the allocation rate too high, or humongous fragmentation. `-XX:G1ReservePercent`
(default 10) exists for exactly this margin.

---

## 5. Memory layout and the hardware

### 5.1 What an object costs

On HotSpot 64-bit with compressed class pointers (the default):

| Part | Size | Note |
|---|---|---|
| Mark word | 8 bytes | identity hash, lock state, GC age/forwarding |
| Klass pointer | 4 bytes | 8 bytes if `-XX:-UseCompressedClassPointers` |
| Array length | 4 bytes | arrays only |
| Object alignment | pad to multiple of 8 | `ObjectAlignmentInBytes` |

So the header is **12 bytes** for an ordinary object, **16 bytes** for an array. `new Object()` is 16
bytes after alignment. An `Integer` is 12 + 4 (int value) = 16 bytes, *plus* the 4-byte reference that
points to it.

```text
int[1_000_000]            → 16 + 4,000,000                  ≈ 4.0 MB, contiguous
ArrayList<Integer> (1M)   → 4 MB of references
                            + 1M × 16 B Integer objects      ≈ 20 MB, scattered
```

Five times the memory and — worse — five times the *cache misses*, because iterating the list chases a
pointer to a random heap location per element while `int[]` streams sequentially and the prefetcher
keeps up. This is the honest answer to "why is `ArrayList<Integer>` slower than `int[]`": layout, not
boxing arithmetic. Fixes: primitive arrays, `IntStream`, or a primitive-collection library (Eclipse
Collections, fastutil, HPPC). Project Valhalla's value classes are the eventual language-level fix.

Fields are reordered by the JVM to pack by size (longs/doubles, then ints, then shorts, then bytes, then
references) and to align each type, so declaration order does not control layout, and superclass fields
precede subclass fields. Verify with **JOL**:

```java
System.out.println(ClassLayout.parseInstance(wager).toPrintable());   // offsets, sizes, gaps
System.out.println(GraphLayout.parseInstance(wager).toFootprint());   // deep retained footprint
```

### 5.2 Compressed oops and the 32 GB cliff

With `-XX:+UseCompressedOops` (default when heap ≤ 32 GB), references are stored as 32-bit values scaled
by the 8-byte object alignment: `2^32 × 8 = 32 GB` addressable. Above that, references become 8 bytes.

The counter-intuitive consequence: **raising `-Xmx` from 31 GB to 33 GB can reduce usable capacity**,
because every reference in the heap grows by 4 bytes — typically 10–20% more heap consumed for the same
object graph, plus worse cache density. So keep heaps under ~31 GB, or jump well past 32 GB so the extra
space outweighs the loss. Verify with `java -XX:+PrintFlagsFinal -version | grep -i compressedoops`.

### 5.3 Cache lines, sequential access, and the numbers

Memory is transferred in **64-byte cache lines**. A cache miss costs roughly 100 ns; an L1 hit ~1 ns. So
the difference between a data structure that touches 1 line per element and one that touches 1 line per
*field access* is two orders of magnitude, and it does not appear in your Big-O.

| Operation | Latency | Relative to L1 |
|---|---|---|
| L1 cache reference | ~1 ns | 1x |
| Branch mispredict | ~3–5 ns | ~4x |
| L2 cache reference | ~4 ns | 4x |
| L3 / last-level cache | ~15–30 ns | ~20x |
| Uncontended lock acquire (CAS) | ~15–25 ns | ~20x |
| Main memory reference | ~80–100 ns | ~100x |
| Object allocation (TLAB bump) | ~2–5 ns | ~3x |
| `System.nanoTime()` | ~20–30 ns | ~25x |
| Thread context switch | ~1–5 µs | ~2,000x |
| Uncontended `synchronized` (inflated monitor park/unpark) | ~1–10 µs | ~5,000x |
| Read 1 MB sequentially from memory | ~50–100 µs | — |
| NVMe SSD random read (4 KB) | ~20–100 µs | ~50,000x |
| Same-datacentre network round trip | ~0.2–0.5 ms | ~300,000x |
| Postgres simple indexed query (same AZ) | ~0.5–2 ms | — |
| HDD seek | ~5–10 ms | ~7,000,000x |
| Cross-region round trip (US-East ↔ EU-West) | ~70–90 ms | ~80,000,000x |

Memorise the shape: L1 1 ns, RAM 100 ns, SSD 100 µs, same-DC network 500 µs, cross-region 80 ms. The
practical rule that follows: **one avoided network call is worth roughly a million avoided cache
misses.** That is why guide 08's N+1 fix and guide 15's cache dominate any JIT-level tuning, and why
"optimise the algorithm" loses to "stop making 40 sequential round trips."

Also distinguish **bandwidth** from **latency**: a single thread pointer-chasing is latency-bound
(~10 M dependent loads/s) and adding threads helps; a scan over a 10 GB array is bandwidth-bound
(~10–30 GB/s per socket) and adding threads does not.

### 5.4 False sharing and `@Contended`

Two variables in the same 64-byte line, written by two different cores, force the line to ping-pong
between the cores' caches through the coherency protocol. Neither thread shares data logically; the
*hardware* shares the line. Throughput can drop by an order of magnitude with no lock in sight.

```java
// hidden false sharing: both counters land in the same cache line
class Stats { volatile long accepted; volatile long rejected; }
```

Fixes, in order of preference: don't share mutable state across threads; use `LongAdder` (which does
padded striping for you); or pad explicitly. `jdk.internal.vm.annotation.@Contended` inserts padding
(`-XX:ContendedPaddingWidth`, default 128 bytes — two lines, to defeat adjacent-line prefetching) but is
JDK-internal and needs `-XX:-RestrictContended` plus a module opening, so in application code manual
padding fields or `LongAdder` is the practical answer. `perf stat` rising cache-coherency events
(`HITM`) or `perfnorm`'s cache-miss counters are how you confirm it.

### 5.5 Branch prediction

A mispredicted branch discards ~15–20 pipeline stages (~3–5 ns). Predictable branches are nearly free.
This is why sorting an array before filtering it can make the *filter* faster, and why a branchless
formulation (`Math.max`, arithmetic masking, `Math.abs`) sometimes wins over an `if` on random data. It
is also why C2's uncommon-trap pruning is so valuable — a branch that never happens is not a branch.

Do not micro-optimise branches speculatively; this matters in tight numeric loops and effectively never
in a Spring service. Its interview value is explaining *why* a change that reduced instruction count made
things slower.

---

## 6. Concurrency performance

Correctness lives in `05-multithreading-concurrency.md`. This is the cost side.

### 6.1 The contention cost curve

`synchronized` proceeds through states in the mark word. Since biased locking was disabled by default in
**JDK 15** and removed in **JDK 18**, the ladder is:

1. **Thin/stack lock** — one CAS on the mark word to install a pointer to the lock record. ~20 ns
   uncontended.
2. **Inflated monitor** — under contention, an `ObjectMonitor` is allocated; losers spin adaptively, then
   `park()` into the OS. A park/unpark round trip is ~1–10 µs, plus a context switch and a cold cache on
   resume.

So contention is not a smooth curve: it is a **cliff** at the point where threads start parking. Below it
you pay tens of nanoseconds; above it, microseconds plus scheduler latency, which is 100–1000x. This is
Amdahl's serial fraction with a coherency penalty on top, which is why throughput can *decrease* as you
add threads to a contended lock.

What biased-locking removal changed: single-threaded uses of synchronized collections
(`Vector`, `Hashtable`, `Collections.synchronizedList`, `StringBuffer`) went from "free after bias" to
"one CAS per operation". Usually noise, occasionally a measurable regression in legacy code paths — the
fix is to use the unsynchronised type, not to re-enable bias.

### 6.2 Choosing a synchronisation mechanism

| Mechanism | Uncontended | Under heavy contention | Notes |
|---|---|---|---|
| `synchronized` | ~20 ns (one CAS) | parks; fair-ish by accident, JIT can elide/coarsen | simplest, biased-lock-free since 15; blocks virtual thread pinning pre-JDK 24 |
| `ReentrantLock` | ~20 ns | similar parking, but `tryLock(timeout)` and `lockInterruptibly` exist | optional fairness costs ~2–10x throughput; use only to prevent starvation |
| `ReentrantReadWriteLock` | ~30 ns | read-heavy scales; **write-starvation** and the read/write handoff itself contends | often *slower* than `synchronized` unless reads dominate heavily and hold long |
| `StampedLock` | ~10 ns optimistic read | best read-mostly option; optimistic read is a version-stamp check with no write | not reentrant, no condition support, must revalidate and fall back |
| CAS loop (`compareAndSet`) | ~15 ns | **degrades**: every failed CAS is a wasted coherency round trip | throughput can collapse under high contention; needs backoff |
| `LongAdder` | ~10 ns | scales near-linearly (striped cells, padded) | `sum()` is not atomic w.r.t. concurrent updates |
| Immutable + copy-on-write | read is free | writes O(n) | perfect for read-almost-always config |
| Partition/shard by key | ~20 ns | scales linearly | the real answer to most contention |

The ordering of preferred fixes for a contended hot path: **remove the shared state → shard it →
replace the lock with a lock-free/striped structure → shrink the critical section → only then tune the
lock type.** Changing the lock class is the last and weakest lever.

`LongAdder` vs `AtomicLong`, mechanism: `AtomicLong` is one memory location, so N threads incrementing
it serialise on one cache line and each increment costs a coherency transfer plus retries.
`LongAdder` keeps a `Cell[]` indexed by a thread-local probe, each cell padded to its own cache line, and
grows the array on collision. Writes scale; the read (`sum()`) walks the cells. Use `AtomicLong` when you
read as often as you write, `LongAdder` for write-heavy metrics — which is what Micrometer counters do
(guide 20).

### 6.3 Thread pool sizing

Two formulas, both from Little's law:

```text
CPU-bound:   threads ≈ cores (+1 to cover occasional page faults)
IO-bound:    threads = cores × targetUtilisation × (1 + waitTime/serviceTime)
             equivalently: threads = targetThroughput × latency   (Little's law)
```

Worked, for the earlier example: 500 rps, 200 ms latency → 100 threads. Cross-check against the CPU
figure: 500 × 10 ms CPU = 5 cores. If the container has 4 cores, the pool cannot deliver 500 rps and
adding threads only lengthens the queue.

Sizing errors and their signatures:

| Symptom | Likely cause |
|---|---|
| High latency, low CPU, deep queue | too few threads for an IO-bound workload, or a saturated downstream pool |
| High CPU, throughput below expectation, high context switches | too many threads (`vmstat 1` shows `cs` in the hundreds of thousands) |
| `RejectedExecutionException` bursts | bounded queue full — correct behaviour; the queue is a shock absorber, not storage |
| Latency grows without bound under load | unbounded queue: you traded rejection for infinite latency |
| Deadlock at low load | dependent tasks in the same fixed pool (task A waits for task B queued behind it) |

**Queue choice is a latency lever.** `SynchronousQueue` gives zero queueing (all latency is visible as
rejection or thread growth), a small `ArrayBlockingQueue` bounds the wait time
(`queueDepth × serviceTime`), and `LinkedBlockingQueue` unbounded converts overload into unbounded
latency and eventual OOM. Compute the implied wait: a 1,000-deep queue with 20 ms service and 100
threads adds `1000/100 × 20 ms = 200 ms` at the tail. See guide 05 § 9 for the submission order and
guide 22 for load shedding as the alternative to queueing.

### 6.4 Virtual threads' performance model

A virtual thread is a continuation mounted on a carrier (a ForkJoinPool platform thread). On a blocking
call the continuation *unmounts*, so the carrier is free. Cost per virtual thread is a few hundred bytes
of heap stack chunk vs ~1 MB of reserved platform stack, and creation is ~1 µs vs ~50–100 µs.

What that buys and does not buy:

- **Buys:** enormous *concurrency* for IO-bound work — 100,000 in-flight requests on 8 carriers. Little's
  law's thread count stops being a scarce resource, so thread-per-request code scales again.
- **Does not buy:** throughput on CPU-bound work. Total CPU is unchanged; carriers = cores by default.
- **Does not buy:** downstream capacity. Removing the thread-pool bound just moves the queue to the DB
  connection pool or the remote service. Add explicit `Semaphore` limits where the old pool size was
  your accidental rate limiter.

**Pinning** is the failure mode: if a virtual thread blocks while pinned to its carrier, the carrier is
consumed. Pre-JDK 24, a blocking call inside a `synchronized` block pinned; JEP 491 (JDK 24) fixed
synchronized so it no longer pins. Native frames (JNI) still pin. With few carriers, a handful of pinned
threads deadlocks throughput. Diagnose with `-Djdk.tracePinnedThreads=full` (older JDKs) or the JFR
`jdk.VirtualThreadPinned` event. Details and the API in `04-modern-java.md`.

---

## 7. Application-layer performance

This is where real service time actually goes, and it is the least glamorous section — which is why it
is the highest-yield one.

### 7.1 Strings

`String` is immutable and holds a `byte[]` with a coder flag (LATIN1 or UTF16 since JDK 9's compact
strings — ASCII strings cost 1 byte/char, not 2). Concatenation with `+` in a *single expression* is
compiled to an efficient form (`StringConcatFactory` invokedynamic, which sizes exactly once); `+=`
**inside a loop** creates a new builder and copies the whole accumulated string each iteration — O(n²).

```java
var sb = new StringBuilder(expectedLen);       // pre-size: avoids log2(n/16) array copies
for (var leg : wager.legs()) sb.append(leg.marketId()).append(':').append(leg.odds()).append(';');
```

`StringBuilder` starts at 16 chars and grows by `2n+2`, copying each time. Pre-sizing removes those
copies. `String.format` is ~10–50x slower than concatenation (it parses the format string and boxes
arguments) — fine in an error path, wrong in a hot loop.

### 7.2 Boxing

Autoboxing allocates (except the `Integer` cache, −128..127 — see `03-java-core.md`). A
`Map<Long, Integer>` counter incremented per event allocates a `Long` key and an `Integer` value per
update. `long` accumulators in an interface typed as `Number`, `Stream<Integer>` instead of `IntStream`,
and `List<Double>` in numeric code are the usual sources. Detection is direct: `-prof gc` in JMH or an
allocation flame graph showing `java.lang.Integer.valueOf`.

### 7.3 Streams vs loops

A stream pipeline costs: one `Stream` object per stage, one lambda instance (usually a cached singleton
if non-capturing — **capturing lambdas allocate per call**), a `Spliterator`, and megamorphic
`accept`/`apply` sites when many pipelines share the same call site. When the whole pipeline inlines,
C2's escape analysis removes most of it and streams match loops. When it does not inline — long
pipelines, megamorphic sites, `boxed()` in the middle — expect 1.5–3x.

Rules that hold up: use streams freely for anything that does IO or non-trivial work per element (the
overhead is invisible); prefer `IntStream`/`LongStream` over boxed streams; use a plain loop in a
verified hot inner loop; and never use `parallelStream()` for IO-bound or small workloads — it uses the
**common ForkJoinPool** (`cores − 1` threads) shared by the whole JVM, so one blocking parallel stream
starves every other. Rough threshold for parallel to pay off: ≥10,000 elements of CPU-bound,
splittable, non-blocking work over an array or `ArrayList` (a `LinkedList` splits terribly).

**Trap:** "streams are always slower." Untrue and unhelpful. The measurable claim is: stream overhead is
tens of nanoseconds per element, which matters only when per-element work is also tens of nanoseconds.

### 7.4 Optional, records, and small objects

`Optional` allocates unless escape analysis removes it — which it usually does for a locally created and
immediately consumed `Optional`, and usually does *not* for one returned across a non-inlined boundary.
So `Optional` in a return type is fine; `Optional` per element inside a hot loop over a million rows is
measurable. Never use `Optional` as a field type (it adds an indirection to every access and is not
serialisable).

### 7.5 Logging

Consistently among the top three items in real service flame graphs.

- **Unguarded argument construction.** `log.debug("wager " + wager + " scored " + score)` builds the
  string and calls `toString()` even when debug is off. Use parameterised logging
  (`log.debug("wager {} scored {}", wagerId, score)`) so formatting happens only if enabled, or a
  supplier form (`log.atDebug().addArgument(() -> expensive()).log("...")`).
- **Synchronous appenders.** Every log line does a blocking write; if the disk stalls or the container's
  stdout consumer is slow, request threads block *inside the logging call*. Use Logback's
  `AsyncAppender` or Log4j2's async loggers (LMAX Disruptor-based), and decide the overflow policy
  deliberately: `neverBlock=true`/discard protects latency and loses logs; blocking preserves logs and
  propagates the stall into your p99.
- **Stack traces.** Logging an exception writes 30–100 frames; at high error rates this alone saturates
  the appender.
- **Per-line cost.** A JSON-encoded log line with MDC is roughly 1–10 µs. At 500 rps × 10 lines that is
  5–50 ms of CPU per second — tolerable; at 50 lines per request in a loop it is the bottleneck.

Guide 20 covers structured logging and sampling policy.

### 7.6 Exceptions

Two costs. **Construction** fills in the stack trace (`fillInStackTrace`, a native walk) — O(depth), and
in a deep Spring stack that is 1–10 µs, one to three orders of magnitude more than a returned error
object. **Throwing/catching** itself is comparatively cheap, and for a hot throw site C2 may replace the
allocation with a pre-allocated exception with no stack trace at all (visible as a mysteriously
trace-less exception; controlled by `-XX:-OmitStackTraceInFastThrow`).

So: exceptions for exceptional conditions, return values (or a sealed `Result` type — see
`04-modern-java.md`) for expected outcomes like validation failures. Where a control-flow exception is
unavoidable, suppress the trace:

```java
final class WagerRejected extends RuntimeException {
    WagerRejected(String reason) { super(reason, null, false, false); }  // no writableStackTrace
}
```

### 7.7 Serialisation

Usually the largest single CPU consumer in a JSON microservice. Jackson's databind reflects over
accessors; `afterburner`/`blackbird` modules replace reflection with generated bytecode for a 20–40%
databind win. Bigger wins come from doing less: avoid re-serialising a payload you already have as bytes,
stream large responses instead of building a `String`, reuse `ObjectMapper` (it is thread-safe and its
construction is expensive — a new one per request is a classic bug), and reuse `ObjectReader`/
`ObjectWriter` for a fixed type since they cache the resolved serialiser.

For internal service-to-service traffic, a schema'd binary format (Protobuf, Avro) is typically 2–5x
faster and 30–60% smaller than JSON — the guide 12 gRPC discussion. Java's built-in
`Serializable` is slow, fragile, and a deserialisation-RCE vector (guide 13): do not use it.

### 7.8 Regex, collections sizing, and copying

- **`Pattern.compile` per call** is a parse plus NFA construction; hoist patterns to `static final`.
  `String.matches`, `String.split` (except its single-char fast path), and `replaceAll` all compile
  internally on every call. Catastrophic backtracking on nested quantifiers turns one request into 100%
  CPU forever — the ReDoS failure that guide 13 covers and that guide 06's 100%-CPU workflow finds.
- **`HashMap`/`ArrayList` sizing.** `HashMap` resizes at `capacity × 0.75`, rehashing everything; filling
  a default map with 10,000 entries performs ~9 resizes. Size it: `HashMap.newHashMap(10_000)` (JDK 19+)
  or `new HashMap<>((int)(10_000/0.75f)+1)`. Same for `ArrayList` (grows 1.5x) and `StringBuilder`.
  Internals in `02-java-collections.md`.
- **Defensive copying and DTO layers.** Entity → DTO → response DTO, each a fresh object plus copied
  collections, is 3 allocations and 3 traversals per item. For a 10,000-row export this dominates.
  Project directly into the target shape (a JPA constructor expression or a projection interface, guide
  08) rather than loading entities and mapping twice. Reflection-based mappers (older ModelMapper,
  Dozer) are 10–100x slower than generated ones (MapStruct) — pick a compile-time mapper.
- **`ThreadLocal` reuse** for expensive-but-not-thread-safe objects (`SimpleDateFormat` legacy code,
  `ObjectMapper` writers, `byte[]` scratch buffers) is legitimate pooling — but see guide 05 § 12 on
  leaks in pooled threads, and note it interacts badly with millions of virtual threads (prefer
  `ScopedValue` or per-call allocation there).

---

## 8. Profiling in production

### 8.1 Sampling vs instrumenting

| Approach | Mechanism | Overhead | Bias |
|---|---|---|---|
| **Instrumenting** (JProfiler/YourKit tracing, bytecode injection) | inject enter/exit probes into methods | 2–20x; changes inlining | huge — instrumented small methods stop being inlined, so cheap methods look expensive |
| **Safepoint-biased sampling** (`Thread.getAllStackTraces`, hprof, most pure-Java profilers) | sample at safepoints | low | **severe**: samples only land where safepoint polls exist, so hot loops without polls are invisible and the blame lands on the next method that yields |
| **`AsyncGetCallTrace` sampling** (async-profiler) | `SIGPROF`/perf timer interrupt → walk the stack from a signal handler, no safepoint needed | ~1% | minimal; sees interpreter, JIT'd and native frames |
| **JFR** (`jdk.ExecutionSample`) | in-JVM event engine, sampled + event-based | ~1–2% | small; method sampling is at safepoint-ish boundaries but event data (alloc, GC, IO, locks) is exact |
| **perf** (Linux) | kernel PMU sampling of the whole process | ~1% | sees kernel + native; needs `-XX:+PreserveFramePointer` and a JIT symbol map to name Java frames |

**Trap:** trusting a safepoint-biased profiler. It will confidently attribute time to the wrong method —
this is the documented reason async-profiler exists and why `hprof` was removed. If a profiler's answer
is surprising, check what sampling mechanism it uses before you act on it.

### 8.2 async-profiler and JFR in practice

```bash
# CPU flame graph, 60 s, attach to a running JVM, no restart
asprof -d 60 -e cpu -f /tmp/cpu.html <pid>
# where allocation comes from (bytes, not counts) — TLAB-based, ~free
asprof -d 60 -e alloc -f /tmp/alloc.html <pid>
# wall-clock: includes time blocked, essential for latency problems
asprof -d 60 -e wall -t -f /tmp/wall.html <pid>
# lock contention
asprof -d 60 -e lock -f /tmp/lock.html <pid>

# JFR: continuous, built in, low overhead
jcmd <pid> JFR.start name=prod settings=profile maxsize=512m filename=/tmp/rec.jfr
jcmd <pid> JFR.dump name=prod filename=/tmp/rec.jfr
jfr summary /tmp/rec.jfr                       # event counts — start here
jfr print --events jdk.ExecutionSample,jdk.ObjectAllocationSample /tmp/rec.jfr
jfr print --events jdk.GCPhasePause,jdk.SafepointBegin,jdk.JavaMonitorEnter /tmp/rec.jfr
```

JFR's advantage over async-profiler is the **event** data: exact GC phases, safepoint durations, monitor
blocked events with the blocking thread, socket read/write durations, thread parks, exception throw
counts, TLAB allocation sites. Its `default` settings profile costs ~1% and is safe to leave on
permanently; `profile` costs ~2% and is what you enable during an incident.

Use async-profiler when you want a fast, accurate flame graph including native frames; use JFR when you
want a timeline correlating CPU, GC, locks and IO. They are complements.

### 8.3 CPU vs wall-clock profiling

A **CPU** profile samples only threads on-CPU. If your p99 problem is *waiting* — on a lock, a socket, a
connection pool — a CPU profile shows a nearly idle JVM and tells you nothing. A **wall-clock** profile
samples all threads regardless of state, so blocked time appears.

The rule: **high CPU → CPU profile. High latency with low CPU → wall-clock profile.** Getting this
backwards is the single most common wasted afternoon in performance work.

### 8.4 Reading a flame graph

- The x-axis is **not time**. Frames are merged and sorted alphabetically; a flame graph is an aggregated
  histogram of stacks, so "the leftmost thing happened first" is wrong.
- **Width = fraction of samples** = cost. Read left-to-right for the widest *leaf* plateaus: those are
  where the CPU actually was.
- **Height = stack depth.** Tall is not expensive. A deep Spring/Netty stack is normal.
- Start at the bottom to identify the entry points, then walk up to the first frame where the width
  splits — that fork is your decision point.
- **Trap:** "the profiler shows the bottleneck, so fix the widest frame." The widest frame is often a
  framework entry point that legitimately encloses all the work (`DispatcherServlet.doDispatch` at 95%).
  You want the widest frame *you control and can remove*. Also check whether the flame graph accounts
  for only 5% of wall time — if so, the answer is not in it at all (see § 8.3).
- **Differential flame graphs** (`asprof --diff`, or diffing two collapsed-stack files) directly answer
  "what changed between v1.4 and v1.5" and are far more convincing than eyeballing two graphs.

### 8.5 Allocation profiling and continuous profiling

Allocation flame graphs answer "which line produced these 400 MB/s" — the fix for a GC problem is almost
always at an allocation site, not in a GC flag. async-profiler's `alloc` event hooks TLAB refill and
outside-TLAB allocation, so it samples by *bytes* (correctly weighting one big array against a million
small objects) at negligible cost. JFR's `ObjectAllocationSample` does the same.

Run **continuous profiling** in production (Pyroscope/Grafana Phlare, Datadog, or a JFR-always-on
setup with periodic dumps to object storage). The value is not live debugging — it is having a profile
from *before* the regression to diff against. This is the profiling analogue of always-on GC logs.

---

## 9. Diagnosing the classic shapes

Six signatures. Each is a hypothesis plus the evidence that confirms or kills it.

### 9.1 High CPU, low throughput

Evidence: `top` shows near-100% CPU; rps flat or falling. Candidates, in check order:

1. **GC threads are the CPU.** `top -H` shows `GC Thread#N`; `jstat -gcutil 1s` shows high GC time, or
   the GC log shows >10% overhead. → allocation or live-set problem (§ 4), not application CPU.
2. **JIT never warmed / code cache full.** Check `-XX:+PrintCompilation` for "made not entrant" storms
   and `jcmd VM.info` for code-cache usage.
3. **Real application hotspot.** CPU flame graph (§ 8.2): serialisation, regex, logging, crypto, a
   quadratic loop over a growing list.
4. **Lock convoy burning CPU in spins** — visible as `Unsafe.park` neighbours plus high context switches
   (`vmstat 1`, field `cs`).
5. **Container CPU throttling** masquerading as slowness: `container_cpu_cfs_throttled_seconds_total`
   rising means the cgroup quota is cutting you off mid-slice, producing sawtooth latency at *low*
   average CPU. Guide 19.

### 9.2 Latency spikes with flat CPU

The JVM is stalling, not computing. Three suspects, in order of frequency:

1. **GC / safepoint pause.** Correlate spike timestamps against `-Xlog:gc*,safepoint`. Do not skip
   safepoint: TTSP and non-GC VM operations are invisible in GC pause numbers (§ 4.4).
2. **Blocking on something external.** Wall-clock profile (§ 8.3), plus pool metrics: Hikari
   `hikaricp.connections.pending` > 0 means threads are waiting for a connection; HTTP client pool
   queueing; a downstream p99 (guide 20 tracing shows which span widened).
3. **Lock contention.** `jstack` × 3 with many `BLOCKED` threads on one monitor, or JFR
   `jdk.JavaMonitorEnter` events with durations and the blocking thread named.

Also check the box: page faults/swap (`vmstat`, `si/so` non-zero — never let a JVM swap), disk stalls in
the logging path, and DNS resolution timeouts (a 5 s spike is almost always a timeout, not computation;
guide 10).

### 9.3 Memory leak vs a legitimately large live set

Both look like "heap keeps filling". Distinguish by the **post-full-GC floor** over hours: monotonically
rising = leak; rising then plateauing at a new level = live set grew (bigger cache, more tenants, larger
working set) and the heap is simply undersized. Guide 06 § 6 has the full MAT workflow; the decision
above is the part candidates skip, and it changes the fix entirely (find the retaining reference vs
raise `-Xmx` / bound the cache).

### 9.4 Thread-pool starvation

Signature: requests time out, CPU is low, queue depth is high, and thread dumps show all pool threads in
the *same* frame. Causes: a downstream that stopped responding while your read timeout was infinite (a
missing timeout is the root cause of most starvation); dependent tasks in one pool; a blocking call
inside a reactive/`CompletableFuture` chain running on `ForkJoinPool.commonPool`; a synchronous call
inside a `parallelStream`. Fixes: bounded pools with explicit timeouts, bulkheads (separate pools per
downstream), and rejection over queueing. Guide 22's resilience section, guide 10's timeout arithmetic.

### 9.5 N+1 and connection-pool exhaustion masquerading as "the JVM is slow"

The most common false diagnosis in this whole guide. Symptoms of a slow JVM (high latency, threads
waiting) with a database root cause:

- **N+1**: one request issues 1 + N queries because a lazy association is iterated (guide 08). The JVM
  looks fine; latency scales with result-set size. Evidence: enable
  `spring.jpa.properties.hibernate.generate_statistics`, or count queries per request in a trace span
  (guide 20), or `pg_stat_statements` showing one query with a huge `calls` count.
- **Pool exhaustion**: `HikariPool-1 - Connection is not available, request timed out after 30000ms`.
  Evidence: `hikaricp.connections.pending`, and thread dumps parked in
  `HikariPool.getConnection`. Cause is either an undersized pool (Little's law again: pool ≥ rps × query
  time) or connections held for the length of a whole transaction that also does HTTP calls — never do
  a remote call inside a `@Transactional` block.
- **Missing index / bad plan.** `EXPLAIN (ANALYZE, BUFFERS)` and guide 09. A sequential scan appearing
  after a data-volume threshold produces a step change in latency with no code deploy.

### 9.6 "It's only slow in prod" checklist

| Difference | Effect |
|---|---|
| Data volume and distribution | plan flips to a seq scan; caches stop fitting; hot keys appear |
| Concurrency | lock contention, pool queueing, false sharing — all invisible at 1 rps |
| JIT profile | prod's polymorphic call sites vs the test's monomorphic ones |
| Heap and CPU limits | different `MaxRAMPercentage`, cgroup CPU quota, `ActiveProcessorCount` |
| GC settings and heap size | dev on defaults, prod tuned (or vice versa) |
| Network topology | cross-AZ hops, TLS handshakes, no local DB, proxy layers |
| Cache warmth | cold Redis/local cache after deploy → stampede (guide 15) |
| Neighbours | shared node CPU steal (`st` in `top`), noisy co-tenants |
| Logging level and appenders | DEBUG in prod, or synchronous appender on a slow volume |
| Agents | APM/instrumentation agent adding bytecode and safepoint operations |

---

## 10. Interview framing

### 10.1 "The p99 of POST /wagers went from 80 ms to 900 ms. What do you do?"

Do not name a fix. Narrate an ordered diagnostic script and say what each step would rule out.

1. **Scope it.** When did it start; is it all instances or one; all endpoints or one; correlated with a
   deploy, a config change, a traffic change, or a data-volume milestone. p50 vs p99 vs error rate — if
   p50 moved too, it is systemic work per request; if only p99 moved, suspect pauses, queueing or a
   tail-heavy dependency.
2. **Split the latency by layer.** Distributed trace (guide 20): how much of the 900 ms is in *our*
   service versus downstream spans. This one step eliminates most of the search space.
3. **If it is downstream** — DB (plan change, missing index, lock waits, pool exhaustion), cache (hit
   rate drop → stampede), or a remote service (its own p99, retries amplifying load, DNS/TLS).
4. **If it is in-process, check pauses before code.** GC log + safepoint log: GC overhead %, pause
   distribution, TTSP, live-set floor. A 700 ms pause explains a 900 ms p99 immediately.
5. **If pauses are clean, check queueing.** Thread-pool active/queue metrics, connection-pool pending,
   `RejectedExecution` counts. Compare against Little's law: has rps or per-request latency risen enough
   to exceed pool capacity?
6. **Now profile.** CPU flame graph if CPU is high; wall-clock if CPU is flat. Diff against a
   pre-regression profile if continuous profiling is in place.
7. **Form one hypothesis, make one change, verify against the same metric.** Then write down the
   evidence chain in the postmortem so the next person starts at step 3.

Say the cheap mitigation out loud too, because senior candidates separate *stop the bleeding* from *fix
the cause*: roll back the deploy, raise the pool bound, shed non-critical load, or turn off the feature
flag — then diagnose with the pressure off.

### 10.2 The traps a senior candidate is expected to avoid

- Reaching for a fix ("add a cache", "increase the heap", "switch to ZGC") before naming the evidence
  that would justify it.
- Confusing GC pause with time-to-safepoint, and `OutOfMemoryError` with OOMKilled (guide 06).
- Quoting means; ignoring coordinated omission in the load test that "proved" capacity.
- Proposing object pooling, `System.gc()`, `-XX:+UseStringDeduplication`, or "make everything final" as
  general performance advice.
- Adding threads to a saturated resource.
- Optimising a 0.5% frame because the microbenchmark showed 4x.
- Failing to state a number: the goal, the current value, and the expected delta.

### 10.3 Numbers to have memorised

Latency table in § 5.3. Beyond it: object header 12 B (16 B for arrays), compressed-oop cliff at 32 GB,
cache line 64 B, `MaxInlineSize` 35 / `FreqInlineSize` 325 bytecode bytes, HashMap load factor 0.75,
default G1 pause goal 200 ms, default `MaxRAMPercentage` 25%, G1 humongous threshold = half a region,
card size 512 B, JFR overhead ~1–2%, async-profiler overhead ~1%, and Little's law in the form
`threads = rps × latency`.

---

## Atomic concept checklist

- [ ] A performance goal is metric + workload + target + measurement point; "slow" is not a goal.
- [ ] Latency, throughput and footprint trade against each other; I state which axis a change moved.
- [ ] Means hide right-skewed latency distributions; the p99 is the user-facing contract.
- [ ] Ten fan-out calls at p99 = 100 ms give a 9.6% chance one is in its tail, so service p99 becomes page p90.
- [ ] `avg(p99)` is not a percentile; percentiles must come from merged histograms.
- [ ] Coordinated omission makes closed-loop load tests under-sample stalls and report a falsely good p99.
- [ ] The USE method checks utilisation, saturation and errors per resource, including software resources like pools.
- [ ] Little's law `L = λW` sizes thread pools and connection pools: threads = target rps × latency.
- [ ] A 20-connection pool with 150 ms queries caps throughput at 133 rps regardless of thread count.
- [ ] Amdahl: a 5% serial fraction caps speedup at 20x, so the first scaling question is "what is serial here".
- [ ] The universal scalability law explains throughput curves that peak and then decline: coherency cost.
- [ ] A naive `nanoTime` loop is invalidated by warmup, DCE, constant folding, unrolling, OSR and profile pollution.
- [ ] JMH's `@Fork` gives a fresh JIT profile, `@State` defeats constant folding, `Blackhole` defeats dead-code elimination.
- [ ] `@OperationsPerInvocation` is required when the benchmark body loops, or per-op numbers are wrong by that factor.
- [ ] `-prof gc`'s `gc.alloc.rate.norm` (bytes per op) is the most reproducible benchmark result.
- [ ] `SampleTime` is the only JMH mode that reports the benchmark's own percentiles.
- [ ] C2 compiles against C1's collected profile; violated assumptions cause deoptimisation and recompilation.
- [ ] Inlining budgets: 35 bytecode bytes always, 325 if hot, depth 15 — so hot methods must stay small.
- [ ] Monomorphic and bimorphic call sites inline; 3+ receivers go polymorphic and megamorphic sites do not inline at all.
- [ ] `final` does not make dispatch faster; HotSpot already devirtualises on profile and class-hierarchy analysis.
- [ ] Escape analysis with scalar replacement removes allocation entirely, but only inside an inlined unit — it is best-effort.
- [ ] Lock elision removes provably thread-local `synchronized`; lock coarsening merges adjacent blocks.
- [ ] "made not entrant" in `PrintCompilation` means deoptimisation; a full code cache silently reverts the app toward interpreted speed.
- [ ] AppCDS cuts startup cheaply; native-image and CRaC remove warmup at the cost of peak throughput or portability.
- [ ] TLAB allocation is a pointer bump costing a few nanoseconds; the real cost is GC frequency, copy cost and cache pollution.
- [ ] Allocation rate (MB/s), computed from the GC log, is the number that drives young-GC frequency.
- [ ] Object pooling usually loses on a modern JVM: promotion, write barriers, reset bugs; pool only threads, connections, sockets, big buffers.
- [ ] `UseStringDeduplication` adds GC work and helps only duplicate long-lived strings; `String.intern()` is worse.
- [ ] In G1 an object over half a region is humongous, goes straight to old gen, needs contiguous regions, and can fail while heap is free.
- [ ] Every reference store executes a GC write barrier that dirties a 512-byte card; primitive arrays avoid it entirely.
- [ ] ZGC uses load barriers instead, paying on reads to relocate concurrently.
- [ ] Time-to-safepoint is not counted in GC pause numbers; counted loops, page faults and VM operations produce invisible stalls.
- [ ] `-Xlog:safepoint` and `-XX:+AlwaysPreTouch` are the tools for TTSP problems.
- [ ] Collector choice is an SLO decision: Parallel for throughput, G1 as general default, ZGC/Shenandoah for sub-10 ms tails.
- [ ] Set `-Xms` = `-Xmx`, keep the heap 2–3x the live set, and read the post-full-GC number as the live set.
- [ ] `to-space exhausted` / `Pause Full (Allocation Failure)` means evacuation had nowhere to copy: heap too small or too fragmented.
- [ ] Object header is 12 bytes (16 for arrays) and objects align to 8, so `new Object()` is 16 bytes.
- [ ] `ArrayList<Integer>` costs ~5x `int[]` in memory and far more in cache misses because of pointer chasing.
- [ ] Compressed oops work up to 32 GB; crossing that cliff grows every reference to 8 bytes and can reduce usable capacity.
- [ ] A cache line is 64 bytes; L1 is ~1 ns and main memory ~100 ns, so layout beats instruction count.
- [ ] One avoided same-DC network round trip (~500 µs) is worth thousands of avoided cache misses.
- [ ] False sharing makes two unrelated variables in one cache line ping-pong between cores; `LongAdder` or padding fixes it.
- [ ] Biased locking was disabled in JDK 15 and removed in JDK 18, so every `synchronized` op now costs at least one CAS.
- [ ] Contention is a cliff, not a curve: tens of nanoseconds until threads park, then microseconds plus a context switch.
- [ ] Fix contention by removing or sharding shared state first; changing the lock class is the weakest lever.
- [ ] `LongAdder` beats `AtomicLong` for write-heavy counters via padded striped cells; `AtomicLong` wins when reads dominate.
- [ ] `StampedLock`'s optimistic read is a version-stamp check, the fastest read-mostly option, but it is not reentrant.
- [ ] CAS-loop throughput degrades under high contention because each failed CAS is a wasted coherency transfer.
- [ ] More threads past the bottleneck add queueing and context switches, so throughput flattens then falls.
- [ ] An unbounded queue converts overload into unbounded latency and eventual OOM; queue depth × service time is the implied wait.
- [ ] Virtual threads scale IO-bound concurrency, not CPU throughput, and just move the queue to the next bounded resource.
- [ ] Pinning consumes a carrier; JDK 24 removed `synchronized` pinning but native frames still pin.
- [ ] `+=` on a String in a loop is O(n²); pre-size `StringBuilder` to avoid repeated array copies.
- [ ] `String.format` is 10–50x concatenation; fine in error paths, wrong in hot loops.
- [ ] Stream overhead is tens of nanoseconds per element and disappears when the pipeline inlines; `parallelStream` shares the common ForkJoinPool.
- [ ] Unparameterised `log.debug("..." + obj)` builds the string even when disabled; synchronous appenders push disk stalls into request latency.
- [ ] Exception cost is stack-trace fill (O(depth), 1–10 µs), not the throw; suppress it with the four-arg constructor when used for control flow.
- [ ] Reuse `ObjectMapper`/`ObjectWriter`, add afterburner or a compile-time mapper, and never use Java `Serializable`.
- [ ] Hoist `Pattern.compile` to a static final field; `String.matches`/`split`/`replaceAll` compile on every call.
- [ ] Size `HashMap` with `HashMap.newHashMap(n)` to avoid rehashing at load factor 0.75.
- [ ] Instrumenting profilers distort inlining; safepoint-biased samplers blame the wrong method; `AsyncGetCallTrace` avoids both.
- [ ] JFR costs ~1–2% and adds exact event data (GC phases, safepoints, monitor blocks, allocation sites) that flame graphs lack.
- [ ] High CPU calls for a CPU profile; high latency with flat CPU calls for a wall-clock profile.
- [ ] A flame graph's x-axis is not time; width is cost, height is only depth, and the widest frame is often an unremovable framework entry point.
- [ ] Allocation flame graphs sample by bytes and point at the line to fix; GC flags rarely are the fix.
- [ ] Continuous profiling's real value is having a pre-regression profile to diff against.
- [ ] Rising post-full-GC floor means a leak; a new plateau means the live set grew and the heap is undersized.
- [ ] Thread-pool starvation is almost always a missing timeout on a downstream call; bulkheads and rejection are the fixes.
- [ ] N+1 queries and Hikari pool exhaustion are the most common causes of "the JVM is slow".
- [ ] Container CPU throttling produces sawtooth latency at low average CPU; check the cgroup throttle counter.
- [ ] The p99-regression script is: scope → split by layer via traces → pauses → queueing → profile → one change, re-measure.
- [ ] Mitigate first (roll back, raise a bound, shed load), then diagnose with the pressure off.
