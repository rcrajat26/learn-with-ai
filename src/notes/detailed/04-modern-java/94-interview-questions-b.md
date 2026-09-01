# 04 Modern Java — The 95 questions, part B — INTERVIEW (§5.1)

**Target version: Java 21 LTS.** | **Part 5 of 5** | [Index](00-index.md)
Previous: [The 95 questions, part A — interview questions a](94-interview-questions-a.md) · Next: [The 95 questions, part C — interview questions c](94-interview-questions-c.md)

This file is thirty-two spoken answers, grouped by theme: reduction and parallel streams
(5.1.33–5.1.41), `Optional` (5.1.42–5.1.47), `var` (5.1.48–5.1.51), and records and `sealed`
(5.1.52–5.1.64). Every answer is written the way you would actually say it out loud in a loop —
mechanism first, example second, gotcha third — not a bullet list of API names. Where a question
has both a short and a long form, both are given and labelled.

---

## Reduction and parallel streams

### 5.1.33 "Why must a `reduce` combiner be associative?"

Because you do not control how the source gets split, and a non-associative combiner gives a
different answer depending on the split shape — which makes the result of a parallel reduction
non-deterministic in the one place determinism is non-negotiable.

Walk it through. `Stream.reduce(identity, accumulator, combiner)` on a **sequential** stream never
calls the combiner at all — the accumulator alone folds every element left to right, in order.
The combiner only exists for the **parallel** case: the pipeline's spliterator is split
recursively into a tree of sub-ranges, each leaf is reduced independently with the accumulator,
and the combiner merges sibling partial results back up the tree. The tree shape is decided by
`AbstractTask.suggestTargetSize` and the source's `trySplit()` behaviour — you never see it, and
it can differ between two runs on the same JVM if the common pool's other workers are busy.

Say the stream is 2,800,000 stake reservations and you want the total staked amount as a
`Money`. If the combiner is `+` (real addition), it does not matter whether the tree splits
`[0..1,400,000) + [1,400,000..2,800,000)` or four quarters combined pairwise — addition is
associative, so `(a+b)+c == a+(b+c)` for every grouping, and every possible split tree produces
the same total. Swap the combiner for something non-associative — say, "take the bonus portion
of whichever partial result has more entries" — and two different split trees can legitimately
pick different partials, because the intermediate merge order changed which partial "won". You
get a result that depends on `ForkJoinPool.commonPool()`'s current load, which is exactly the kind
of bug that reproduces on your machine and not on the pipeline's.

```java
// Sequential: no combiner call, order is fixed left-to-right.
BigDecimal totalStaked = reservations.stream()
        .map(Reservation::stakeAmount)
        .reduce(BigDecimal.ZERO, BigDecimal::add);

// Parallel: the combiner runs once per merge point in the split tree.
// BigDecimal::add is associative — safe regardless of split shape.
BigDecimal totalStakedParallel = reservations.parallelStream()
        .map(Reservation::stakeAmount)
        .reduce(BigDecimal.ZERO, BigDecimal::add, BigDecimal::add);
```

**Insight:** associativity is a mathematical property of the *operator*, not a property you can
retrofit by being careful with your data. `subtract` is not associative
(`(10-3)-2 != 10-(3-2)`), so `reduce(0, (a,b) -> a - b, (a,b) -> a - b)` is simply wrong the moment
the stream goes parallel, even though the identical accumulator on a sequential stream produces
the "obviously correct" left-to-right answer every time — because sequential never invokes the
combiner and never exposes the bug.

**The related trap on `int` reduction:** even a genuinely associative operator can *look* broken
under parallel execution once overflow enters the picture. `Collectors.summingInt` accumulates
into a boxed `int[1]` slot per JDK 21 source (`java.util.stream.Collectors`, verified at the
jdk-21+35 tag) — the running sum is a real `int`, with no compensation. Summing three
1,000,000,000-value reservations gives `-1294967296` from `summingInt` and `3000000000` from
`summingLong`, on the same data, because `int` silently wraps. This is not a combiner-associativity
bug — integer addition mod 2^32 is still associative — it is an *overflow* bug that a parallel
split tree does not create but does not hide either. `averagingInt` is safe on this specific axis
because it accumulates into a `long[2]` (sum, count), not an `int[]`; `summingInt` is not.

> **Definition:** a `reduce` combiner must satisfy `combiner.apply(a, b) == combiner.apply(b, a)`'s
> associative sibling — `combiner.apply(combiner.apply(a,b), c) == combiner.apply(a, combiner.apply(b,c))`
> — because a parallel pipeline decides the grouping of partial results at runtime, and only an
> associative operator guarantees every possible grouping yields the same answer.

**Interview:** the combiner only runs on parallel streams, to merge partial results from an
unpredictable split tree; if it is not associative, different split shapes produce different
answers, and split shape is not something you control or can rely on being stable.

### 5.1.34 "How does a parallel stream decide how many tasks to create?"

It does not pick a task count directly — it picks a **target leaf size**, then keeps splitting the
source spliterator in half until each leaf is at or below that size, and the leaf count falls out
of `dataSize / targetSize`.

The target size comes from `java.util.stream.AbstractTask`:

```java
private static final int LEAF_TARGET = ForkJoinPool.getCommonPoolParallelism() << 2;

/**
 * Default target of leaf tasks for parallel decomposition.
 * To allow load balancing, we over-partition, currently to approximately
 * four tasks per processor, which enables others to help out
 * if leaf tasks are uneven or some processors are otherwise busy.
 */
public static int getLeafTarget() {
    Thread t = Thread.currentThread();
    if (t instanceof ForkJoinWorkerThread) {
        return ((ForkJoinWorkerThread) t).getPool().getParallelism() << 2;
    } else {
        return LEAF_TARGET;
    }
}

public static long suggestTargetSize(long sizeEstimate) {
    long est = sizeEstimate / getLeafTarget();
    return est > 0L ? est : 1L;
}
```

Read it literally, not from folklore. `LEAF_TARGET` is the common pool's parallelism shifted left
by two — `parallelism × 4` — and the javadoc's own words are "we over-partition, currently to
approximately four tasks per processor, which enables others to help out if leaf tasks are uneven
or some processors are otherwise busy": deliberate over-decomposition so idle workers can steal
work from a straggler, not an attempt to hit exactly one task per core. `suggestTargetSize` is
**floored integer division, clamped to a minimum of 1** — `est > 0L ? est : 1L` — not "rounded up"
the way some material states it; a source with fewer than `getLeafTarget()` elements gets a target
size of exactly 1, meaning it splits all the way down to single elements.

`getLeafTarget()` is also **not pinned to the common pool**. When the calling thread is itself a
`ForkJoinWorkerThread`, it asks that worker's own pool for its parallelism instead of reading the
static `LEAF_TARGET` field. This is the actual mechanism behind "run the parallel stream in my
own custom pool" (5.1.37): the decomposition width follows whichever pool the terminal operation
is actually executing in, because the recursive splitting logic queries the current thread's pool
on every call, not a value baked in at stream-build time.

Worked arithmetic, using the fixed 8-core box these notes standardise on:
`Runtime.getRuntime().availableProcessors()` = **8**, so `ForkJoinPool.commonPool()`'s parallelism
is **7** (5.1.35 explains why), giving `LEAF_TARGET = 7 << 2 = 28`. Over the domain's
**2,800,000** daily stake reservations: `suggestTargetSize(2_800_000) = 2_800_000 / 28 =
100,000` exactly — a clean division, no flooring artifact — so the spliterator recursively halves
until each leaf holds **100,000** reservations, producing **28 leaf tasks**, each independently
reduced and then merged pairwise back up the recursion tree by the combiner from 5.1.33.

> **Definition:** a parallel stream does not choose a task count; it chooses a target leaf size —
> `sourceSize / (poolParallelism × 4)`, floored and clamped to at least 1 — and recursively splits
> the spliterator until every leaf is at or under that size.

**Interview:** the JDK over-partitions to about four leaf tasks per core so idle workers can steal
from a slow one — the actual number is `sourceSize / (parallelism × 4)`, floor-divided and never
less than 1, and it reads the *current* pool's parallelism, not always the common pool's.

### 5.1.35 "Which thread pool does a parallel stream use, and how big is it?"

`ForkJoinPool.commonPool()` by default, and its size is smaller than most people say — but the
thread that calls the terminal operation also does work, so the number that actually matters is
one bigger than the pool's own parallelism figure.

`ForkJoinPool.commonPool()`'s default parallelism is `Runtime.getRuntime().availableProcessors()
- 1`. On the 8-core box these notes use throughout, that is `8 - 1 = 7` — seven common-pool
worker threads. State only that number and you have told half the story. The thread that invokes
`.collect(...)` / `.reduce(...)` / any terminal operation does **not** block and wait idle; because
the whole `AbstractTask` fork/join scheme is built on `ForkJoinTask.invoke()`, the submitting
thread participates directly in the computation as an extra worker, executing tasks from the pool
the same way a `ForkJoinWorkerThread` would. So the **effective width is `parallelism + 1` = 8** —
exactly the core count on this box. Both halves are load-bearing: "commonPool has
`cores - 1` threads" is true and misleading in isolation; "the submitter joins in" is the fact that
brings the number back to the core count.

This has two consequences worth stating explicitly in an interview:

1. **Every parallel stream in the JVM shares this one pool**, unless it is running inside a
   custom `ForkJoinPool.submit(...)` (5.1.37). A `parallelStream()` call in `PaymentService` and
   one in `FundsLedger` compete for the same seven-worker pool at the same time.
2. The pool is sized once, at first use, from `Runtime.getRuntime().availableProcessors()` (or the
   `java.util.concurrent.ForkJoinPool.common.parallelism` system property if set) — it does not
   resize when the container's CPU quota changes at runtime, which matters on a cgroup-limited
   container where `availableProcessors()` may not reflect the actual quota depending on JDK and
   flag configuration.

```java
// Both parallel streams below draw from the same commonPool() —
// they are not two independent seven-worker pools.
CompletableFuture<Long> depositCount = CompletableFuture.supplyAsync(() ->
        cardDeposits.parallelStream().filter(d -> d.status() == DepositStatus.CAPTURED).count());
CompletableFuture<BigDecimal> ledgerTotal = CompletableFuture.supplyAsync(() ->
        ledgerEntries.parallelStream()
                .map(LedgerEntry::amount)
                .reduce(BigDecimal.ZERO, BigDecimal::add));
```

> **Definition:** a parallel stream's terminal operation runs on `ForkJoinPool.commonPool()`,
> sized to `availableProcessors() - 1` worker threads, plus the calling thread itself, which joins
> the computation rather than blocking — giving an effective concurrency equal to the core count.

**Interview:** the common `ForkJoinPool`, sized `cores - 1`, but the calling thread also
participates in the work rather than waiting, so the effective parallelism is the full core count,
not one less.

### 5.1.36 "What happens if I do blocking I/O inside a parallel stream?"

You starve a shared, application-wide resource, and every other parallel stream in the process
pays for it — not just the one doing the blocking call.

`ForkJoinPool.commonPool()` (5.1.35) is a fixed-size work-stealing pool with `cores - 1` worker
threads, shared by every `parallelStream()` call in the JVM, including ones library code makes
that you never see — `Files.list(...).parallel()` in some dependency, `Collectors.groupingBy`
inside a batch job. If a lambda inside a parallel stream's pipeline makes a blocking network call —
calling the identity vendor (p50 900ms, p99 38s per the domain's verified figures) synchronously
from inside a `.map()` over a batch of `DocumentVerification` records — that worker thread is
occupied for up to 38 seconds doing nothing but waiting on a socket. With only seven workers total,
a handful of concurrently-blocked leaf tasks can exhaust the entire pool. Every unrelated parallel
stream elsewhere in the process — a `BalanceView` aggregation, a `PaymentRun` total — queues behind
it, because there is no separate pool per call site; there is one common pool for the whole JVM.

```java
// Wrong: ties up a shared common-pool worker for the identity vendor's full round trip.
List<DocumentVerdict> verdicts = pendingVerifications.parallelStream()
        .map(v -> identityVendorClient.verifySync(v))   // blocking call, p99 38s
        .toList();
```

**Pitfall:** treating `parallelStream()` as a free concurrency primitive for I/O-bound work. It is
a CPU-bound decomposition tool built on a *fixed-size* pool sized to the core count, not an
elastic executor. The fix is to not run I/O inside it at all — dispatch the blocking calls to a
purpose-built executor (or, on Java 21+, virtual threads, which are cheap enough that blocking one
does not starve a shared resource — the mechanism detail of pinning and the virtual-thread
scheduler's own pool sizing is guide 05's territory) and keep the parallel stream itself doing only
CPU-bound transformation.

There is a narrow, documented escape hatch for genuinely unavoidable blocking inside a
`ForkJoinPool` task: `ForkJoinPool.ManagedBlocker`, which lets a blocked worker signal the pool to
temporarily spin up a compensating thread so the pool's target parallelism is maintained while the
call is in flight. It exists, it is real, and almost nobody reaches for it correctly — the default
answer in an interview is "don't block inside a parallel stream," with `ManagedBlocker` mentioned
as the exception that proves the rule, not as the recommended fix.

> **Definition:** blocking I/O inside a parallel stream's pipeline occupies a `commonPool()`
> worker for the full duration of the call, and because that pool is shared JVM-wide, it can
> starve every other parallel stream in the process, not just the caller.

**Interview:** it ties up a shared, fixed-size, JVM-wide pool for the duration of the blocking
call, so unrelated parallel streams elsewhere in the process stall too — parallel streams are for
CPU-bound work, not I/O.

### 5.1.37 "Can I give a parallel stream my own pool? Is that supported?"

You can, using an undocumented trick that exploits how `AbstractTask.getLeafTarget()` and the
fork/join scheme both key off "whichever pool the current thread belongs to" rather than a pool
reference baked into the stream — but it is explicitly **not a supported API**, and the JDK team
has said so on the record.

The trick:

```java
ForkJoinPool paymentReconciliationPool = new ForkJoinPool(4);
BigDecimal total = paymentReconciliationPool.submit(() ->
        ledgerEntries.parallelStream()
                .map(LedgerEntry::amount)
                .reduce(BigDecimal.ZERO, BigDecimal::add)
).join();
```

Because the whole computation runs as a `ForkJoinTask` submitted to `paymentReconciliationPool`,
the calling thread inside that lambda is a `ForkJoinWorkerThread` belonging to
`paymentReconciliationPool`, not the common pool. Every recursive split inside the stream's
`AbstractTask` machinery calls `Thread.currentThread()`, sees a `ForkJoinWorkerThread`, and asks
*that* pool for its parallelism (`getLeafTarget()`, 5.1.34) and forks its subtasks into *that*
pool rather than the common one. It works today because that is how the code is actually written.

**Pitfall:** treating this as a documented, guaranteed-stable feature. There is no public API on
`Stream` for "run this parallel stream on pool X" — the mechanism relies on undocumented internal
behaviour of `AbstractTask` and `ForkJoinTask.fork()`/`invoke()`, and Oracle engineers have stated
in public forum threads (the JDK bug database and mailing-list discussions referenced by the
syllabus's authority order) that this usage is unsupported and could change without notice in a
future release, precisely because it was never designed as a public contract — it is an
accident of implementation that happens to be reachable from outside `java.util.stream`. Ship it
in production and you are depending on private behaviour of `java.util.stream.AbstractTask`
staying the same across JDK upgrades.

> **Definition:** submitting the stream pipeline itself as a task to a custom `ForkJoinPool`
> redirects the internal decomposition logic to that pool, because it queries the current
> thread's own pool rather than a fixed reference — a real, working, but explicitly unsupported
> technique.

**Interview:** yes, by submitting the whole pipeline as a task to your own `ForkJoinPool` — it
works because the internals ask the current thread's pool, not a hardcoded one — but it is an
undocumented implementation detail, not a supported feature, and the JDK team has said so.

### 5.1.38 "When is a parallel stream faster? Give me the four conditions."

Four, and all four have to hold at once — parallel streams do not have a "usually helps" middle
ground; missing any one condition typically makes it a net loss once fork/join overhead is
counted.

1. **The data set is large enough that the per-element work outweighs decomposition overhead.**
   Forking tasks, stealing work, and merging combiners all cost real cycles. For a handful of
   elements — checking three `Restriction`s on a client — sequential wins outright; the classic
   framing is Doug Lea's `N × Q` model, where `N` is element count and `Q` is per-element cost, and
   parallel only pays off once `N × Q` clears the fork/join overhead by a healthy margin. The
   domain's **2,800,000** daily stake reservations clear this bar comfortably; a client's four
   active `Restriction`s do not.
2. **The source splits cheaply and evenly.** `ArrayList` and arrays have `IMMUTABLE`/`SIZED`
   spliterators that split by index in O(1) — cheap, even halves. `LinkedList` and most
   `Iterator`-backed sources split by walking nodes, which is itself O(n) per split (5.1.41) and
   can produce lopsided leaves.
3. **The per-element work is genuinely CPU-bound and independent** — no blocking I/O (5.1.36), no
   shared mutable state that forces synchronization or false sharing between worker threads. Two
   leaf tasks writing into the same non-thread-safe `ArrayList` (5.1.39) do not get faster by
   splitting; they get a data race.
4. **The common pool actually has spare capacity right now.** Since every parallel stream in the
   JVM shares one `commonPool()` (5.1.35), a parallel stream started while the pool is already
   saturated by other work does not get a dedicated performance boost — it queues behind whatever
   is already running, and can be *slower* than sequential once contention and context-switching
   are counted.

```java
// All four conditions plausibly hold: large N (2.8M), array-backed source (splits cheaply),
// pure CPU-bound arithmetic per element, and this runs as a standalone nightly reconciliation
// job with no other parallel-stream traffic on the common pool.
BigDecimal totalStaked = reservations.parallelStream()
        .filter(r -> r.status() == ReservationStatus.SETTLED)
        .map(Reservation::stakeAmount)
        .reduce(BigDecimal.ZERO, BigDecimal::add);
```

**Insight:** "parallel is faster for big collections" is the folklore version; the accurate claim
is a conjunction of four independent conditions, and interviewers who ask this question are
listening for whether you name all four or just the first one everybody remembers.

> **Definition:** a parallel stream beats its sequential twin only when the data is large relative
> to fork/join overhead, the source splits cheaply and evenly, the per-element work is CPU-bound
> and independent, and the shared common pool has spare capacity — all four, simultaneously.

**Interview:** large enough `N × Q` to amortise fork/join overhead, a source that splits cheaply
and evenly, CPU-bound independent work with no blocking or shared mutable state, and a common pool
that is not already busy with other parallel streams.

### 5.1.39 "Why is `parallelStream().forEach(list::add)` broken but `collect(toList())` fine?"

Because `forEach(list::add)` hands every worker thread a direct reference to the *same* mutable
`ArrayList` and lets them all call `add` on it concurrently, while `collect(toList())` gives each
worker its own private accumulator and only merges them together once, single-threaded, at the
end.

`ArrayList.add` is not thread-safe: it does a bounds/capacity check, conditionally grows the
backing array, writes the element, and increments `size` — none of it atomic, none of it
synchronized. When multiple `ForkJoinPool` worker threads call `list::add` concurrently from
different leaf tasks of the same parallel stream, you get lost updates, `ArrayIndexOutOfBounds`
from two threads racing a resize, or a `size` that undercounts — genuinely undefined behaviour,
not "usually works."

```java
// Wrong: forEach gives every worker a shared mutable target with zero coordination.
List<Reservation> settled = new ArrayList<>();
reservations.parallelStream()
        .filter(r -> r.status() == ReservationStatus.SETTLED)
        .forEach(settled::add);          // data race — corrupts settled under concurrent writers

// Right: collect(toList()) never exposes a shared mutable target to your code.
List<Reservation> settledSafe = reservations.parallelStream()
        .filter(r -> r.status() == ReservationStatus.SETTLED)
        .collect(Collectors.toList());
```

`collect` is built on the three-function contract — `supplier`, `accumulator`, `combiner` — and
the streams implementation is explicit about how it uses them under parallel execution: each leaf
task gets its own fresh container from `supplier`, accumulates into that private container with
`accumulator` (no cross-thread visibility needed, no synchronization needed — it is
thread-confined), and only the `combiner` step, which merges two already-complete containers
pairwise up the split tree, ever touches results your code did not privately own. You never see
two threads mutating the same list at the same time, because the collector's contract is
structured specifically to prevent it.

**Pitfall:** believing `forEach` is "just a loop" and therefore safe the way a sequential
`for`-loop appending to a list is safe. On a parallel stream, `forEach`'s ordering and thread
placement are unspecified by design — it exists precisely to let the runtime run the body
concurrently across workers — so any side effect inside it that touches shared mutable state
needs the same defensive thinking as any other multithreaded code. `forEachOrdered` fixes the
*ordering* half of this but does nothing for the *thread-safety* half; the fix here is a proper
collector, not `forEachOrdered`.

> **Definition:** `collect(toList())` is safe under parallel execution because each worker
> accumulates into its own private container and merging happens through an explicit combiner
> step, while `forEach(list::add)` hands every worker a shared mutable reference with no such
> isolation.

**Interview:** `collect` isolates each worker with its own accumulator and merges explicitly via
the combiner; `forEach(list::add)` lets every worker thread call `add` on the same list
concurrently, which is a straightforward data race.

### 5.1.40 "What is a `Spliterator` and what do its characteristics do?"

A `Spliterator` is the "splittable iterator" that every stream is built on top of: it can hand you
elements one at a time like an `Iterator`, but it can also — if `trySplit()` succeeds — cleave
itself in two, handing back a second `Spliterator` covering a disjoint prefix while shrinking
itself to the remainder. That single extra capability, `trySplit()`, is the entire mechanism that
makes `parallelStream()` possible: no `trySplit()`, no parallel decomposition, no matter what else
you call on the stream.

Its methods:

| Method | Job |
|---|---|
| `tryAdvance(Consumer)` | Sequentially process one element, return `false` when exhausted |
| `forEachRemaining(Consumer)` | Process everything left, sequentially — the default implementation just loops `tryAdvance` |
| `trySplit()` | Return a new `Spliterator` covering a prefix of the remaining elements, or `null` if it cannot split further |
| `estimateSize()` | Best-effort element count remaining, used by `suggestTargetSize` (5.1.34) |
| `characteristics()` | A bitmask describing guarantees the source makes, used by the pipeline to pick faster code paths |

The characteristics are what let the pipeline skip work it does not need to do:

| Characteristic | What it lets the runtime assume |
|---|---|
| `ORDERED` | Encounter order matters and must be preserved unless explicitly relaxed with `.unordered()` |
| `DISTINCT` | Every element is already unique — `Stream.distinct()` becomes a no-op |
| `SORTED` | Already in the comparator's order — `Stream.sorted()` becomes a no-op |
| `SIZED` | `estimateSize()` is an exact count, known up front |
| `SUBSIZED` | Every spliterator produced by `trySplit()` is also `SIZED` — critical for cheap, even splitting |
| `NONNULL` | No element is ever `null`, so null-checks can be skipped |
| `IMMUTABLE` | The source cannot structurally change during traversal — no `ConcurrentModificationException` possible |
| `CONCURRENT` | The source can be safely modified concurrently while traversed (its own thread-safety, not a stream guarantee) |

```java
Spliterator<Reservation> spliterator = reservations.spliterator();
System.out.println(spliterator.hasCharacteristics(Spliterator.SIZED));      // true for ArrayList
System.out.println(spliterator.hasCharacteristics(Spliterator.SUBSIZED));   // true for ArrayList
System.out.println(spliterator.estimateSize());                             // exact count, O(1)
```

**Insight:** `SIZED` + `SUBSIZED` together are what make `ArrayList`'s spliterator split so
cheaply — it can compute the midpoint index arithmetically and hand back two ranges whose sizes it
already knows exactly, with no traversal at all. A source that lacks `SUBSIZED` — where splitting
still happens but the resulting piece's size is only an estimate, or unknown — is the difference
between "instant, even splits" and "expensive, possibly lopsided splits" (5.1.41).

> **Definition:** a `Spliterator` is an iterator that can additionally partition itself via
> `trySplit()`, and its `characteristics()` bitmask tells the stream pipeline which safe
> optimisations — skipping `distinct`, skipping `sorted`, trusting `estimateSize()`, assuming no
> nulls — it is allowed to apply.

**Interview:** it is the splittable iterator every stream runs on — `trySplit()` is what makes
parallelism possible at all — and its characteristics bitmask (`SIZED`, `SUBSIZED`, `ORDERED`,
`DISTINCT`, `SORTED`, `NONNULL`, `IMMUTABLE`, `CONCURRENT`) tells the pipeline which stream stages
it can skip or optimise.

### 5.1.41 "Why does a `LinkedList` parallelises badly?"

Because its `Spliterator` cannot split in O(1) the way an array-backed source can — every split
has to physically walk the list to find the midpoint, which is O(n) work spent *before* any real
parallel work even starts, and it is missing the `SUBSIZED` characteristic that would make the
resulting pieces cheap to split further.

`ArrayList.spliterator()` is backed by an array with a known length; splitting it is arithmetic —
compute the midpoint index, hand back two ranges, no traversal. `LinkedList` has no random access:
finding the middle node of a sub-range means walking node-by-node from one end, which is O(n) for
that single split, and the recursive decomposition in `AbstractTask` calls `trySplit()`
repeatedly, at every level of the split tree, all the way down to `getLeafTarget()`-sized leaves
(5.1.34). Each of those splits repeats an O(n)-ish node walk over a shrinking but still
non-trivial range, so the total splitting overhead grows in a way an array's does not. On top of
that, `LinkedList`'s spliterator lacks `SUBSIZED`, so the runtime cannot even trust that the two
halves it gets back are evenly sized without checking, which undermines the even-splits condition
from 5.1.38.

```java
// Splits cheaply: O(1) midpoint arithmetic on an array-backed source.
new ArrayList<>(reservations).parallelStream()...

// Splits expensively: every trySplit() call walks nodes to find a midpoint.
new LinkedList<>(reservations).parallelStream()...
```

**Pitfall:** picking `LinkedList` because "streams are lazy anyway" or because insertion-heavy
code elsewhere in the same class made `LinkedList` feel like the safe general-purpose choice, then
reaching for `.parallelStream()` on it expecting the same speedup an `ArrayList` would give. The
fix is source shape, not stream tuning: convert to an array-backed collection before going
parallel, or avoid `LinkedList` for anything that will later be streamed in bulk.

> **Definition:** `LinkedList` parallelises badly because its spliterator has no random access,
> so every split costs an O(n) node walk instead of O(1) index arithmetic, and it lacks
> `SUBSIZED`, undermining the even, cheap splits that parallel decomposition depends on.

**Interview:** its spliterator can't jump to a midpoint — every split walks nodes, which is O(n)
work per split instead of an array's O(1) index arithmetic — and it is not `SUBSIZED`, so the
pieces it does produce aren't reliably even either.

---

## `Optional`

### 5.1.42 "What is `Optional` for, and where should it never appear?"

`Optional<T>` is a return-type wrapper whose entire purpose is to make "this method might have
nothing to give you" visible in the method signature, forcing the caller to handle absence at the
call site instead of discovering it three stack frames later as an NPE. It is a documentation
device with compile-time teeth, not a general-purpose "nullable" container.

It belongs on a method's **return type** when absence is a legitimate, expected outcome — looking
up a `Client` by `ClientId` that might not exist yet, or reading a `Restriction` that might have
already expired and been removed. It should **never** appear as: a field type (it is not
`Serializable` by design — 5.1.45 — and boxing every nullable field in `Optional` bloats every
instance for no benefit over a plain null-checked field), a method parameter type (callers already
have `null` for "nothing", and an `Optional` parameter just adds an extra unwrap step with no
new safety — `if (restriction == null)` and `if (restriction.isEmpty())` are equally
easy to forget), a collection element type (a `List<Optional<Bonus>>` is strictly worse than a
`List<Bonus>` that simply omits absent entries), or the type of anything you plan to serialize to
JSON, a database column, or across a wire boundary.

```java
// Right: absence in the return type, forces the caller to handle it.
public Optional<Restriction> findActiveRestriction(ClientId clientId, RestrictionType type) {
    return restrictions.stream()
            .filter(r -> r.clientId().equals(clientId) && r.type() == type
                    && r.status() == RestrictionStatus.ACTIVE)
            .findFirst();
}

// Wrong: Optional as a field — serialization-hostile and no clearer than a nullable field.
public record ClientProfile(ClientId id, Optional<Bonus> activeBonus) { }  // don't
```

> **Definition:** `Optional<T>` is a container reserved for return types where absence is a
> normal, expected outcome the caller must consciously handle — never a field, a parameter, or a
> collection element.

**Interview:** it exists to make "might be nothing" visible in a method's return type so callers
must handle absence explicitly — and it should never show up as a field, a parameter, or an
element type, because none of those get any real safety benefit from it and fields specifically
lose serializability.

### 5.1.43 "`orElse` vs `orElseGet` — show me the bug."

`orElse(T)` takes an already-computed value and **always evaluates its argument**, present or not,
because Java evaluates method arguments eagerly before the call happens. `orElseGet(Supplier<T>)`
takes a lazy supplier and only invokes it when the `Optional` is actually empty. Swap them where
the fallback is expensive or has a side effect, and you silently pay for — or silently trigger —
something you didn't need.

```java
// Bug: computeDefaultCoupon() runs on EVERY call, even when a coupon was already present,
// because orElse's argument is evaluated eagerly before orElse even looks inside the Optional.
public Coupon resolveCoupon(Optional<Coupon> suppliedCoupon) {
    return suppliedCoupon.orElse(computeDefaultCoupon());   // called unconditionally
}

private Coupon computeDefaultCoupon() {
    // Hits BonusService to look up the platform-wide default coupon — a real network call.
    return bonusService.lookupDefaultCoupon();
}
```

Trace it: `suppliedCoupon.orElse(computeDefaultCoupon())` — Java must produce the value of
`computeDefaultCoupon()` before it can call `orElse` at all, exactly like it must evaluate `b()`
before calling `a(b())`. The `Optional` never gets a say in whether that evaluation happens. If
`suppliedCoupon` is present nine times out of ten, you have made nine unnecessary calls to
`BonusService` for a value you throw away every time.

```java
// Fixed: the supplier only runs if suppliedCoupon.isEmpty() is true.
public Coupon resolveCoupon(Optional<Coupon> suppliedCoupon) {
    return suppliedCoupon.orElseGet(this::computeDefaultCoupon);
}
```

**Pitfall:** using `orElse(expensiveCall())` out of habit because it reads slightly shorter than
`orElseGet(() -> expensiveCall())`. The rule of thumb: if the fallback is a constant or a field
read (`orElse(Money.ZERO)`, `orElse(existingReservation)`), `orElse` is fine and arguably clearer.
The moment the fallback is a method call that does real work — a lookup, a computation, anything
with a side effect like a log statement or a metric increment — it has to be `orElseGet`, because
`orElse` cannot avoid running it.

> **Definition:** `orElse(T)` unconditionally evaluates its argument before the call happens;
> `orElseGet(Supplier<T>)` only invokes its supplier when the `Optional` is empty — use `orElseGet`
> whenever the fallback is not free.

**Interview:** `orElse`'s argument is evaluated eagerly no matter what, because Java evaluates
method arguments before the call — put an expensive or side-effecting call in there and it runs
every time; `orElseGet` only calls its supplier when the `Optional` is actually empty.

### 5.1.44 "Why is `isPresent()` + `get()` an anti-pattern?"

Because it reproduces exactly the null-check-then-dereference pattern `Optional` was invented to
replace, gets none of the functional-style safety the type offers, and — worse — the compiler
cannot stop you from separating the check from the use, so you can still write the equivalent of
a null-pointer bug with an `Optional` in your hand.

```java
// This is just "if (x != null) { use(x.get()) }" wearing an Optional costume.
Optional<Client> client = clientRepository.findById(clientId);
if (client.isPresent()) {
    processDeposit(client.get(), depositAmount);   // fine here...
}
// ...but nothing stops this a few lines later, after the check has scrolled off screen:
processWithdrawal(client.get(), withdrawalAmount);   // NoSuchElementException if empty
```

The functional methods exist precisely so the "check" and the "use" cannot be pulled apart:
`map`, `filter`, `ifPresent`, `ifPresentOrElse`, `orElse`, `orElseGet`, `orElseThrow` all take the
value and the handling logic as one atomic expression, so there is no window where a later line of
code can dereference an `Optional` that the earlier `isPresent()` check no longer guards.

```java
// Right: the presence check and the use are the same expression — impossible to pull apart.
clientRepository.findById(clientId)
        .ifPresentOrElse(
                client -> processDeposit(client, depositAmount),
                () -> notificationService.notifyClientNotFound(clientId));
```

**Pitfall:** `isPresent()` + `get()` is not merely "less idiomatic" — it is a genuine
maintenance hazard, because a refactor that moves the `get()` call away from its guarding
`isPresent()` (extracting a method, reordering statements) removes the safety with no compiler
warning, whereas the same refactor on `map`/`ifPresent` chains simply cannot happen because there
is nothing to move apart.

> **Definition:** `isPresent()` followed by `get()` re-implements a manual null check with extra
> ceremony, loses `Optional`'s guarantee that the check and the use cannot be separated, and should
> be replaced by `map`, `ifPresent`, `ifPresentOrElse`, or `orElseThrow`.

**Interview:** it re-creates the exact null-check-then-dereference shape `Optional` exists to
avoid, and unlike `map`/`ifPresent`, nothing stops a later refactor from moving the `get()` away
from the `isPresent()` that was guarding it.

### 5.1.45 "Why is `Optional` not `Serializable`?"

Deliberately — the JDK team designed it that way to actively discourage exactly the misuse in
5.1.42: putting `Optional` on a field. The javadoc for `Optional` states plainly that it is
intended primarily for use as a method return type, and that whether `Optional` should be
"used as a field" or in other roles is not a design goal — the type was scoped narrowly on
purpose. Making it non-`Serializable` gives that scoping decision actual teeth: an entity, a DTO,
or anything else that needs to serialize can not silently grow an `Optional`-typed field and
still work — you find out at serialization time (or, with many frameworks, at compile/config time)
rather than getting silent misuse that happens to work until someone tries to persist or transmit
the object.

```java
// Compiles, but blows up the moment something tries to serialize it —
// exactly the friction the JDK team intended.
public class ClientSnapshot implements Serializable {
    private final Optional<Bonus> activeBonus;   // NotSerializableException at serialize time
    // ...
}
```

**Insight:** this is one of the few places in the JDK where a type's *missing* interface is itself
a piece of API design communicating intent — the absence of `Serializable` is not an oversight to
work around with a custom `writeObject`, it is the JDK telling you the field placement is wrong.

> **Definition:** `Optional` does not implement `Serializable` by deliberate design, to discourage
> its use as a field on anything meant to be serialized — the javadoc is explicit that
> return-type use, not field use, is the intended role.

**Interview:** it is deliberate, not an oversight — the javadoc says `Optional` is meant for
return types, and making it non-`Serializable` enforces that by breaking anything that tries to
put it on a serializable field.

### 5.1.46 "What happens if `map`'s function returns null?"

You get an empty `Optional` back, not a `NullPointerException` — `Optional.map` wraps its
function's result the same way `Optional.ofNullable` does, precisely so that a mapper which
sometimes cannot produce a value doesn't force you to null-check inside the mapper itself.

```java
Optional<Client> client = clientRepository.findById(clientId);

// If lookupPrimaryInstrument returns null for a client with no saved instrument,
// map does NOT throw — it produces Optional.empty() transparently.
Optional<Instrument> instrument = client.map(Client::primaryInstrumentOrNull);
```

Internally, `Optional.map` is specified (and implemented) as: if this `Optional` is empty, return
`empty()` without calling the mapper at all; otherwise call the mapper and wrap its result with
`Optional.ofNullable(result)` — which itself returns `empty()` if `result` is `null`. So a chain
of `map` calls degrades gracefully at whichever step first returns `null`, and every subsequent
`map` in the chain is simply skipped because the `Optional` is already empty by the time it gets
there, exactly the same short-circuiting you'd get from an early `return Optional.empty()` in
imperative code, but without writing it.

```java
Optional<String> maskedCardSuffix = clientRepository.findById(clientId)
        .map(Client::primaryInstrumentOrNull)   // may yield null -> Optional.empty()
        .map(Instrument::cardNumberOrNull)      // skipped entirely once empty
        .map(cardNumber -> cardNumber.substring(cardNumber.length() - 4));
```

**Pitfall:** assuming `map` needs `Optional.ofNullable(...)` wrapped around every mapper's return
value by hand — `client.map(c -> Optional.ofNullable(c.primaryInstrumentOrNull()))` — which
instead produces the wrong shape entirely, an `Optional<Optional<Instrument>>`, because you did
the null-wrapping `map` already does for you, on top of it. That double-wrap is exactly what
`flatMap` exists to unwrap: if your mapper function itself returns an `Optional<U>` (not a plain
`U` that might be null), use `flatMap`, not `map`.

> **Definition:** `Optional.map` treats a `null` return from its function the same way
> `Optional.ofNullable` treats a `null` argument — it produces `Optional.empty()`, never an NPE,
> and short-circuits any further `map` calls chained after it.

**Interview:** it doesn't throw — `map` wraps the function's result with the same null-tolerant
logic as `ofNullable`, so a `null` return just becomes `Optional.empty()` and the rest of the
chain short-circuits.

### 5.1.47 "Is `Optional.empty() == Optional.empty()` true? Should you rely on it?"

Today, yes, it evaluates to `true` on every mainstream JVM — but no, you should never write code
that depends on it, because the javadoc does not promise it, and the moment you rely on reference
identity for `Optional` you have reintroduced the exact `==` vs `.equals()` trap `Optional`'s
value semantics exist to steer you away from.

`Optional.empty()` is implemented as a call to a static, pre-allocated singleton — `Optional.EMPTY`
— so every call to `empty()` really does hand back the identical object reference, and `==`
between two such references is `true` as an *implementation fact*. But `Optional`'s javadoc
specifies its contract in terms of `equals()`, not identity: two `Optional` instances are equal if
both are empty, or both hold values that are themselves equal. Nothing in that contract promises
singleton behaviour for the empty case — it happens to be implemented that way today, purely as an
allocation optimisation, and a future JDK release (or, in principle, a different JVM vendor
entirely) is free to change the internal representation without breaking any documented guarantee,
because identity was never part of the contract.

```java
Optional<Bonus> firstLookup = Optional.empty();
Optional<Bonus> secondLookup = Optional.empty();

System.out.println(firstLookup == secondLookup);       // true today — an implementation detail
System.out.println(firstLookup.equals(secondLookup));  // true, and this is the guaranteed contract
```

**Pitfall:** writing `someOptional == Optional.empty()` as a presence check, whether out of habit
from comparing to `null` or because it happened to work in a quick test. Use `isPresent()` /
`isEmpty()` for the presence check, and `equals()` if you ever need to compare two `Optional`
values for equality — never `==`.

> **Definition:** `Optional.empty() == Optional.empty()` is `true` today because `empty()` returns
> a shared singleton, but that is an unspecified implementation detail, not a documented guarantee
> — the contract is expressed through `equals()`, and only `equals()`/`isEmpty()`/`isPresent()`
> should be relied on.

**Interview:** yes today, because `empty()` returns a cached singleton, but the javadoc contract is
`equals()`-based, not identity-based, so that's an implementation detail you should never write
code that depends on — use `isEmpty()`/`isPresent()` instead.

---

## `var`

### 5.1.48 "What is `var`, and where can you not use it?"

`var` is **local variable type inference** (JEP 286, Java 10): the compiler infers the concrete
type of a local variable from its initializer expression at compile time and bakes that concrete
type into the bytecode, exactly as if you had written it out yourself. It is a source-level
convenience only — there is no `var` type at the bytecode level, and no dynamic typing is
involved anywhere.

It is restricted to a narrow set of declaration contexts, and every restriction traces back to the
same requirement: **the initializer alone must supply enough information for the compiler to pin
down a concrete type, with no help from context outside the declaration.**

| Context | `var` allowed? | Why |
|---|---|---|
| Local variable with initializer | Yes | `var reservation = new Reservation(...)` — the `new` expression's type is self-sufficient |
| Enhanced `for` loop variable | Yes | The element type comes from the iterated source |
| Traditional `for` loop index | Yes | `for (var i = 0; ...)` — `0`'s type is `int`, self-sufficient |
| Try-with-resources resource | Yes | Same rule as any local with an initializer |
| Field (instance or static) | No | Fields are part of a class's public/binary contract; inference would make that contract initializer-dependent |
| Method parameter | No | There is no initializer expression to infer from at the declaration site |
| Method return type | No | Same reason — no initializer to read |
| Local variable with no initializer | No | `var reservation;` has nothing to infer from |
| Local variable initialized to `null` | No | `var x = null;` — `null` carries no type information at all |
| Lambda expression target | No | 5.1.51 — a lambda has no type of its own without a functional-interface target |
| Array initializer shorthand | No | `var a = {1, 2, 3};` is illegal; must be `var a = new int[]{1, 2, 3};` |
| Catch clause parameter | No | Not permitted by the grammar — exception types must be written explicitly |

```java
// Legal:
var reservation = new Reservation(RoundId.random(), Money.of("4.20"));
for (var entry : ledgerEntries) { /* entry inferred as LedgerEntry */ }

// Illegal — each for a different reason from the table above:
// var count;                      // no initializer
// var bonus = null;               // null has no type
// private var clientId;           // field
// void settle(var reservation) {} // parameter
```

> **Definition:** `var` is compile-time local variable type inference — the compiler substitutes
> the initializer's concrete static type at compile time — restricted to local declarations,
> enhanced/traditional `for` loop variables, and try-with-resources resources, each requiring a
> self-sufficient initializer.

**Interview:** local variable type inference, purely compile-time — allowed only where the
initializer alone fully determines a type: locals with initializers, `for` loop variables,
try-with-resources — never fields, parameters, return types, or anything without a self-sufficient
initializer.

### 5.1.49 "Does `var` have a runtime cost?"

None. `var` is erased entirely during compilation — the class file produced from a `var`
declaration is byte-for-byte identical, at the level of local variable slots and instructions, to
the class file you'd get from writing the inferred type out explicitly. There is no wrapper type,
no boxing, no reflection, and no runtime type-inference step of any kind.

The compiler resolves `var`'s inferred type during the attribution phase of compilation — the same
phase that resolves any other expression's static type — and by the time bytecode generation
happens, the local variable table entry already carries the concrete type (`LReservation;`,
`I`, whatever it resolved to). `javap -v` on a class compiled with `var` shows exactly the same
`LocalVariableTable` entries you would get from the explicit-type version, because the distinction
between `var` and an explicit type exists only in the source file the javac front end reads — it
has already been fully resolved before the back end ever emits an instruction.

```bash
javac --release 21 WithVar.java WithoutVar.java
javap -v WithVar.class      # LocalVariableTable shows the concrete inferred type
javap -v WithoutVar.class   # identical entries, identical bytecode
```

**Pitfall:** confusing `var` with genuinely dynamic-typing constructs from other languages (or
with `Object`), and assuming there is a hidden dispatch or boxing cost analogous to, say,
autoboxing an `int` into `Integer`. There isn't — `var` never reaches the runtime at all.

> **Definition:** `var` costs nothing at runtime because it is resolved to a concrete type
> entirely during compilation, producing bytecode identical to writing the explicit type by hand.

**Interview:** zero — it's fully erased at compile time to the same concrete type and identical
bytecode you'd get writing the type out explicitly; there is no runtime inference step at all.

### 5.1.50 "What does `var list = new ArrayList<>()` infer?"

`ArrayList<Object>` — not a raw `ArrayList`, and not something magically inferred from how `list`
is used later in the method.

The diamond operator `<>` on `new ArrayList<>()` needs a **target type** to infer its type
argument against — normally that target comes from the left-hand side of an assignment, the way
`List<Restriction> restrictions = new ArrayList<>();` lets the diamond infer `<Restriction>` from
the declared `List<Restriction>` type. With `var` on the left-hand side, there is no declared type
to serve as that target — `var`'s own type has to come *from* the right-hand side, and the
right-hand side's diamond has nothing to look at *except* the (not yet known) left-hand type. Faced
with that circularity, the compiler falls back to the diamond's documented default: when no target
type is available, infer `Object`. So `var list = new ArrayList<>()` really does produce
`ArrayList<Object>`, and every later `list.add(someRestriction)` compiles — because `Object`
accepts anything — while giving you none of the type safety you'd get from a real
`ArrayList<Restriction>`, and every read back out requires a cast.

```java
var restrictions = new ArrayList<>();     // infers ArrayList<Object> — a trap, not a convenience
restrictions.add(new Restriction(...));    // compiles: any Object is accepted
restrictions.add("this compiles too");     // also compiles — no type safety at all

// Correct: give the diamond a real target, either by declaring the type explicitly...
List<Restriction> typedRestrictions = new ArrayList<>();
// ...or by naming it on var's right-hand side, which fixes the target for the diamond:
var alsoTypedRestrictions = new ArrayList<Restriction>();
```

**Pitfall:** this is exactly why the LVTI style guide's **G6** ("take care when using `var` with
diamond or generic methods") exists — `var` combined with an empty diamond silently degrades to
`Object`, with no compiler warning, and the bug surfaces later as a `ClassCastException` or a
confusing "cannot find symbol" on a method that only exists on the real element type.

> **Definition:** `var list = new ArrayList<>()` infers `ArrayList<Object>`, because `var` gives
> the diamond no target type to infer against and the diamond's documented fallback in that
> situation is `Object`.

**Interview:** `ArrayList<Object>` — the diamond needs a target type to infer its type argument,
`var` provides none on the left, so it falls back to `Object`; write the type argument explicitly
on the right (`new ArrayList<Restriction>()`) if you use `var` here.

### 5.1.51 "Why can't you write `var f = () -> 1;`?"

Because a lambda expression, on its own, does not have a type — it only becomes a concrete type
once the compiler knows *which functional interface* it is meant to implement, and that knowledge
normally comes from a target type supplied by the context the lambda appears in. `var` supplies no
such context: it needs the type of its initializer to already be known before it can be inferred,
which is exactly backwards from how lambda typing works.

Every lambda in Java is **poly expressional** — its meaning depends entirely on the target type it
is assigned into. `Supplier<Integer> f = () -> 1;` works because `Supplier<Integer>` is the
declared target, and the compiler checks the lambda body against that interface's single abstract
method. `Callable<Integer> g = () -> 1;` compiles too, with the exact same lambda body, because now
the target is `Callable`. The *same source text* `() -> 1` is a different concrete type depending
entirely on what it's being assigned to — it carries no type of its own to infer from. `var`
requires the initializer to be **self-sufficiently typed**, and a bare lambda fails that
requirement categorically, not just in this one case — it's the same failure mode as
`var x = null;`, just for a different reason (null carries no type at all; a lambda carries no
type until given a target).

```java
// Illegal — the compiler has nothing to check "() -> 1" against:
// var f = () -> 1;
//     error: lambda expression needs an explicit target-type

// Legal — give the lambda a real target, either via a declared type...
Supplier<Money> bonusCalculator = () -> Money.of("42");
// ...or by casting the lambda so the cast itself supplies the target:
var castCalculator = (Supplier<Money>) () -> Money.of("42");   // var now infers Supplier<Money>
```

The same rule blocks `var mr = String::toUpperCase;` (a bare method reference has no inherent
type either) and `var arr = {1, 2, 3};` (the shorthand array-initializer syntax is only legal when
the element type is already declared on the left, which `var` cannot provide).

> **Definition:** a lambda expression has no type of its own until matched against a target
> functional interface, and `var` requires the initializer to already carry a concrete,
> self-sufficient type — so a bare lambda and `var` are structurally incompatible.

**Interview:** a lambda has no type of its own — it only gets one from a target functional
interface supplied by context — and `var` needs the initializer's type known up front with no
outside context, so the two requirements are mutually exclusive; cast the lambda to give it a
target if you must combine them.

---

## Records and `sealed`

### 5.1.52 "What does a record generate for you?"

A record header like `record StakeSplit(Money bonusPortion, Money cashPortion) {}` expands, at
compile time, into a full class with all of the following generated automatically, with none of
it written by hand:

| Generated element | Shape |
|---|---|
| Private, final field per component | `private final Money bonusPortion; private final Money cashPortion;` |
| Canonical constructor | `public StakeSplit(Money bonusPortion, Money cashPortion) { this.bonusPortion = bonusPortion; this.cashPortion = cashPortion; }` |
| Accessor method per component | `public Money bonusPortion() { return bonusPortion; }` — **named after the component, no `get` prefix** |
| `equals(Object)` | `true` iff the other object is the same record type and every component is equal, via each component's own `equals` |
| `hashCode()` | Combines the hash of every component (5.1.60 has the actual bytecode mechanism) |
| `toString()` | `StakeSplit[bonusPortion=0.33, cashPortion=3.00]` — class name plus every component name and value |
| Implicit superclass | Every record implicitly extends `java.lang.Record`, and is implicitly `final` — a record can never be extended and can never extend anything else |

What it does **not** generate: setters (there are none — every field is `final`), a no-argument
constructor, or `Serializable` (a record has to opt into that explicitly with `implements
Serializable`, same as any other class).

```java
public record StakeSplit(Money bonusPortion, Money cashPortion) {
    // Nothing else needed — constructor, accessors, equals/hashCode/toString all generated.
}

StakeSplit split = new StakeSplit(Money.of("0.33"), Money.of("3.00"));
split.bonusPortion();   // Money.of("0.33") — accessor, not getBonusPortion()
split.toString();       // "StakeSplit[bonusPortion=0.33, cashPortion=3.00]"
```

> **Definition:** a record generates private final fields, a canonical constructor, one accessor
> per component named identically to the component, and component-based `equals`/`hashCode`/
> `toString` — nothing else, and nothing mutable.

**Interview:** private final fields, a canonical constructor, accessors named after the
components (not `getX`), and `equals`/`hashCode`/`toString` derived from every component — no
setters, and it's implicitly final.

### 5.1.53 "What is a compact constructor and what is it for?"

A compact constructor is a special constructor form, unique to records, that lets you validate or
normalize the incoming component values **without re-declaring the parameter list or writing the
field assignments yourself** — you write only the checks and any transformations, and the
compiler still emits the assignment of every parameter to its matching field automatically, right
after your compact constructor's body finishes.

```java
public record StakeSplit(Money bonusPortion, Money cashPortion) {
    public StakeSplit {   // note: no parameter list repeated, no parentheses after StakeSplit
        if (bonusPortion.amount().signum() < 0 || cashPortion.amount().signum() < 0) {
            throw new IllegalArgumentException(
                    "StakeSplit components must be non-negative: " + bonusPortion + ", " + cashPortion);
        }
        // Reassigning the PARAMETER, not the field — the compiler still assigns
        // this normalized value to the field afterwards.
        bonusPortion = bonusPortion.roundedDownToMinorUnit();
    }
}
```

It exists for exactly the case where you want validation or normalization to run **for every way
the record can be constructed**, in one place, without duplicating the field list a second time
the way a normal constructor would force you to. Every canonical-constructor invocation — direct
`new StakeSplit(...)`, deserialization (5.1.59), a record pattern's implicit reconstruction — goes
through the same compact constructor, so there is exactly one validation choke point, not one per
caller.

**Pitfall:** trying to assign the field directly inside the compact constructor —
`this.bonusPortion = bonusPortion.setScale(2);` — which fails to compile with `cannot assign a
value to final variable bonusPortion` (verified on this machine: `T.java:4: error: cannot assign
a value to final variable bonusPortion`). The reason is exactly what the diagnostic says: the
component field is `final`, and inside a compact constructor **the compiler emits the field
assignment for you automatically at the end** — your job is only to reassign the *parameter*
(`bonusPortion = ...`, no `this.`), and the parameter's final value, whatever you left it as, is
what gets written to the field.

> **Definition:** a compact constructor lets a record validate or normalize its component
> parameters without restating the parameter list, and the compiler still generates the field
> assignments automatically after the compact body runs — you may reassign the parameters, never
> the fields directly.

**Interview:** it's the record-only constructor form for validation and normalization that skips
re-declaring the parameter list — you can reassign the parameters, but never `this.field`
directly, because the compiler emits those field assignments itself right after your code runs.

### 5.1.54 "Are records immutable?"

Only shallowly, and that qualifier is the whole answer — every component field is `final` and can
never be reassigned after construction, but if a component's declared type is itself a mutable
class, the object that field points to can still be mutated through that reference, and the
record has no defense against it unless you build one yourself.

```java
public record ClientLimitSnapshot(ClientId clientId, List<LimitSet> limitHistory) {}

List<LimitSet> mutableHistory = new ArrayList<>();
mutableHistory.add(new LimitSet(500, 50, 2000));

ClientLimitSnapshot snapshot = new ClientLimitSnapshot(ClientId.random(), mutableHistory);
mutableHistory.add(new LimitSet(1000, 100, 5000));   // snapshot.limitHistory() now has TWO entries

snapshot.limitHistory().add(new LimitSet(2000, 200, 10000));   // and now three — the record itself
                                                                 // did nothing to stop this
```

The `limitHistory` field is `final` — you cannot write `snapshot.limitHistory = ...` — but `final`
only freezes the *reference*, not the object the reference points to. `ArrayList` is mutable, so
anyone holding either the original list or the record's returned reference can add, remove, or
clear elements, and every holder of the record sees the change, because there was never a copy.

> **Definition:** a record is immutable only at the level of its own fields — final, never
> reassigned — not at the level of what those fields point to; a mutable component type keeps the
> record's overall state mutable in practice.

**Interview:** shallowly only — the fields are final and can't be reassigned, but a mutable
component like a `List` can still be mutated through the reference the record hands back, both
before and after construction.

### 5.1.55 "Why is an array component in a record a bug?"

Because arrays break both halves of a record's generated identity contract — `equals` and
`hashCode` — by using reference identity instead of contents, so two records holding logically
identical arrays compare as unequal, and the same array reference can be mutated in place after
construction with the record providing no protection at all, silently violating the immutability
it otherwise promises.

```java
public record DocumentDigest(ClientId clientId, byte[] sha256) {}

byte[] hash1 = {1, 2, 3};
byte[] hash2 = {1, 2, 3};

DocumentDigest digestA = new DocumentDigest(ClientId.random(), hash1);
DocumentDigest digestB = new DocumentDigest(ClientId.random(), hash2);

digestA.equals(digestB);       // false, even with identical byte contents —
                                // record equals() calls Objects.equals on each field,
                                // and Objects.equals on two arrays is reference equality
digestA.sha256().length;       // 3 — looks fine until...
hash1[0] = 99;
digestA.sha256()[0];           // 99 — the array was never defensively copied; this mutated
                                // "immutable" state through the original reference
```

The generated `equals` calls `Objects.equals(this.sha256, other.sha256)` for the array component
exactly the same way it does for any other component — but `Object.equals` on an array (which is
what `Objects.equals` delegates to when neither array reference is `null`) is inherited straight
from `Object`, meaning **identity comparison**, not content comparison. Arrays never override
`equals`/`hashCode` to compare contents — that is what `Arrays.equals`/`Arrays.hashCode` exist for,
and the record's auto-generated methods do not know to call those instead.

**Pitfall:** reaching for a `byte[]` or `int[]` as a record component because "it's just a value
type field" and expecting record semantics to apply to it the way they apply to a `Money` or a
`ClientId`. The fix is either to swap the array for an immutable, content-comparing type
(`List<Byte>`, or a dedicated wrapper value type that itself implements `equals`/`hashCode` over
contents), or, if the array must stay for performance reasons, to hand-write `equals`, `hashCode`,
and `toString` overrides that call `Arrays.equals`/`Arrays.hashCode`/`Arrays.toString` explicitly
— at which point you've opted back out of most of what a record buys you.

> **Definition:** an array component is a bug in a record because the generated `equals`/
> `hashCode` inherit an array's reference-identity comparison rather than content comparison, and
> the array itself remains externally mutable with no defensive copy — silently breaking both
> value semantics and immutability.

**Interview:** arrays don't override `equals`/`hashCode`, so the record's generated methods
compare array components by reference, not contents — two records with identical byte arrays
compare unequal — and the array is also still mutable in place through the reference, breaking
the immutability the record otherwise promises.

### 5.1.56 "How do you make a record with a `List` component genuinely immutable?"

Defensively copy the incoming list into an unmodifiable collection inside a compact constructor —
`List.copyOf(...)` is the idiomatic choice — so that neither the caller's original list nor the
returned accessor value can be mutated to change the record's apparent state after construction.

```java
public record ClientLimitSnapshot(ClientId clientId, List<LimitSet> limitHistory) {
    public ClientLimitSnapshot {
        // Defensive copy on the way IN: mutating the caller's list afterwards
        // cannot affect this record's state.
        limitHistory = List.copyOf(limitHistory);
    }
    // No need to override limitHistory() separately — the accessor returns
    // the already-immutable field set by the compact constructor above.
}

List<LimitSet> mutableHistory = new ArrayList<>();
mutableHistory.add(new LimitSet(500, 50, 2000));
ClientLimitSnapshot snapshot = new ClientLimitSnapshot(ClientId.random(), mutableHistory);

mutableHistory.add(new LimitSet(1000, 100, 5000));   // does NOT affect snapshot — it copied on entry
snapshot.limitHistory().add(new LimitSet(2000, 200, 10000));   // throws UnsupportedOperationException
```

Two things have to both be true for this to actually close the hole, and it is easy to get half
of it: `List.copyOf` protects against mutation of the *original* list reaching the record (the
copy), and it also protects against mutation *through* the accessor, because `List.copyOf` returns
an unmodifiable list — calling `.add` on the returned reference throws
`UnsupportedOperationException` rather than silently succeeding. A defensive copy using
`new ArrayList<>(limitHistory)` alone would fix the first half but not the second — the copy would
still be a plain mutable `ArrayList`, and `snapshot.limitHistory().add(...)` would succeed and
corrupt the record's apparent immutability from the outside.

**Pitfall:** copying with `Collections.unmodifiableList(new ArrayList<>(limitHistory))` — a
correct but verbose two-step form that predates `List.copyOf` (Java 10) — or wrapping without
copying (`Collections.unmodifiableList(limitHistory)`, which still lets the *original* reference
mutate the wrapped list, since the wrapper is just a live view). `List.copyOf` does both jobs — a
real copy, and an unmodifiable view of that copy — in one call, and additionally throws
`NullPointerException` up front if any element is `null`, catching a different class of bug early.

> **Definition:** genuine immutability for a `List` component requires a compact-constructor
> defensive copy into an unmodifiable collection — `List.copyOf(...)` — protecting against both
> mutation of the caller's original reference and mutation through the record's own accessor.

**Interview:** defensively copy with `List.copyOf(...)` inside the compact constructor — that
protects against both the caller mutating their original list after the fact and someone mutating
through the record's accessor, since `List.copyOf` returns a real, unmodifiable copy, not a live
wrapper.

### 5.1.57 "Can you persist a record's `hashCode`?"

No — you should never write a record's `hashCode()` value to storage and expect to compare it
meaningfully against a freshly computed one later, including across JVM restarts, JDK upgrades,
or even (in principle) different runs of the same JDK version, because the JDK gives **no
stability guarantee whatsoever** for a record's generated `hashCode` algorithm.

The mechanism itself (5.1.60 has the full bytecode walk) is generated via an `invokedynamic`
bootstrap through `java.lang.runtime.ObjectMethods`, which builds the hash combination logic
dynamically based on the record's component list at class-load time. Nothing in the language
specification, the record feature's JEP, or the javadoc for `Record` promises that this generated
algorithm — the specific way component hashes get combined — is stable across JDK versions, or
even guaranteed identical between two separately-compiled class files of the exact same record
declaration on the exact same JDK build. Compare that to `Object.hashCode`'s own well-known
caveat, which every Java engineer already internalizes: hash codes are for in-memory data
structures (`HashMap` bucket placement) within a single run, never for persistence, never for
cross-process comparison, and records inherit that caveat with an even sharper edge, because the
*algorithm* itself is generated, not hand-written and stable-by-convention the way most manually
written `hashCode` overrides are.

```java
// Wrong: storing a computed hashCode expecting to compare against it after a JDK upgrade,
// or after moving the class to a differently-versioned service.
int storedDigest = stakeSplit.hashCode();
persistToAuditLog(reservationId, storedDigest);
// ... months later, on a JDK upgrade or a redeploy ...
if (recomputedStakeSplit.hashCode() == storedDigest) { /* NOT a safe integrity check */ }
```

**Pitfall:** reaching for `hashCode()` as a cheap stand-in for a real content digest or audit
fingerprint. If you need a stable, persistable fingerprint of a record's contents — for an audit
trail entry on a `LedgerEntry`, say — compute an explicit digest yourself (a real hash function
like SHA-256 over a canonical serialization of the fields), never rely on `Object`/`Record`-family
`hashCode()`.

> **Definition:** a record's generated `hashCode()` carries no cross-version or cross-run
> stability guarantee — it is produced by a dynamically bootstrapped algorithm with no documented
> stability contract — and must never be persisted as a fingerprint or compared across JVM/JDK
> boundaries.

**Interview:** no — the generated `hashCode` comes from a dynamically bootstrapped algorithm with
no documented stability guarantee across JDK versions or even separate compilations, so it's only
safe for in-memory use within one run, same as any other `hashCode`, and arguably less safe to
assume stable than a hand-written one.

### 5.1.58 "Can a record be a JPA entity? Why not?"

No — not as a genuine `@Entity`, and the reasons are structural, not a missing annotation JPA
providers just haven't added yet: JPA's entity contract requires exactly the things a record
refuses to provide.

- **JPA requires a no-argument constructor** (protected or public, per the spec) so the provider
  can instantiate the entity via reflection before populating fields — a record has no such
  constructor; it only ever has the canonical constructor requiring every component.
- **JPA requires mutable fields**, because lazy loading, dirty-checking, and the persistence
  context's managed-entity lifecycle all depend on the provider being able to set fields *after*
  construction — filling in a lazily-loaded association later, for instance. Every record field
  is `final`; there is no way for a provider to populate one after the canonical constructor has
  run.
- **JPA entities frequently need to be proxied** — Hibernate, for lazy-loading support, generates
  a runtime subclass of the entity to intercept field access. A record is implicitly `final`
  (5.1.52) and cannot be subclassed, so no proxy can be generated at all.
- **Entity equality is identity-based** (typically on a surrogate primary key, sometimes evolving
  across the object's lifecycle from "no id yet" to "assigned id"), while a record's generated
  `equals`/`hashCode` are **value-based across every component**, including exactly the mutable,
  provider-populated fields that JPA needs to change after construction — comparing two managed
  entities before and after a lazy field populates would give inconsistent results with a record's
  semantics, which is the opposite of what an entity's identity contract needs.

```java
// Will not work as a JPA @Entity — no no-arg constructor, no mutable fields, cannot be proxied.
public record Client(ClientId id, PersonId personId, AccountStatus status) {}

// The workable pattern: a record as an immutable DTO/projection layered
// OVER a genuine mutable JPA entity, never as the entity itself.
public record ClientSummary(ClientId id, AccountStatus status, BigDecimal cashAvailable) {
    public static ClientSummary from(ClientEntity entity) {
        return new ClientSummary(entity.getId(), entity.getStatus(), entity.getCashAvailable());
    }
}
```

**Insight:** this is not a gap current JPA implementations plan to close — it's a fundamental
mismatch between record semantics (immutable, value-based, final) and the entity lifecycle
contract (mutable, identity-based, proxyable) that predates records by well over a decade. Records
are a genuinely good fit for the read-side of a JPA-backed system — DTOs, query projections,
`record`-based constructor expressions in JPQL — just not for the managed entity itself.

> **Definition:** a record cannot be a JPA entity because entities require a no-arg constructor,
> mutable post-construction fields, subclass-based proxying, and identity-based equality — a
> record structurally provides none of the four.

**Interview:** no — JPA needs a no-arg constructor, mutable fields for lazy loading and
dirty-checking, a subclassable type for proxy generation, and identity-based equality, and a
record is the opposite of all four: canonical-constructor-only, all-final, implicitly final
itself, and value-based equals.

### 5.1.59 "How does record deserialization differ from ordinary Java serialization?"

Ordinary Java serialization reconstructs an object by allocating raw memory and setting fields
directly via reflection, bypassing every constructor entirely — that is precisely why
`readObject`/`writeObject` customization and `readResolve` exist, as escape hatches to inject logic
back into a process that otherwise runs no constructor at all. Record deserialization is
structurally different: it **calls the canonical constructor**, with the values read from the
stream passed in as ordinary constructor arguments — meaning any validation or normalization
inside a compact constructor (5.1.53) runs on every deserialization, not just on construction from
source code.

For an ordinary serializable class, the JVM does not call `new SomeClass(...)` during
deserialization at all — it uses a special mechanism to allocate the object's memory layout and
populate fields one at a time from the stream, silently reconstructing a possibly-invalid object
if the class's invariants were only ever enforced in a constructor. For a serializable record, the
specification requires the runtime to read each component's value from the stream and then invoke
the record's canonical constructor with those values — which means a `StakeSplit` object read back
off the wire is guaranteed to have passed through the same non-negative-amount check
(5.1.53's `IllegalArgumentException`) that a freshly-constructed one does. A malicious or corrupted
stream cannot smuggle an invariant-violating `StakeSplit` into the JVM the way it historically
could with a hand-rolled serializable class that only validated in its public constructor.

```java
public record StakeSplit(Money bonusPortion, Money cashPortion) implements Serializable {
    public StakeSplit {
        if (bonusPortion.amount().signum() < 0 || cashPortion.amount().signum() < 0) {
            throw new IllegalArgumentException("negative stake split component");
        }
    }
    // No readObject/writeObject needed — the canonical constructor above
    // is invoked automatically during deserialization, re-running this exact check.
}
```

Records also **cannot customize deserialization the way ordinary classes can** — `readObject`,
`readObjectNoData`, and `readResolve` are simply not honoured on a record (the specification
explicitly forbids most of the classic customization hooks for records, precisely because the
canonical-constructor path is meant to be the one and only reconstruction path, so validation
logic cannot be bypassed by a class-specific override the way it historically could be).
`writeObject` is similarly not customizable in the way it is for ordinary classes — a record's
serialized form is derived directly from its components.

> **Definition:** deserializing an ordinary class bypasses every constructor and populates fields
> via reflection, while deserializing a record reads each component's value from the stream and
> then invokes the canonical constructor with those values — so compact-constructor validation
> runs on every deserialization, and the classic `readObject`/`readResolve` customization hooks do
> not apply.

**Interview:** ordinary serialization skips constructors entirely and sets fields via reflection;
a record's deserialization actually calls the canonical constructor with the stream-read values,
so compact-constructor validation runs every time, and it closes off the classic
`readObject`/`readResolve` customization escape hatches on purpose.

### 5.1.60 "How are a record's `equals`/`hashCode`/`toString` actually implemented in bytecode?"

Not as ordinary compiled method bodies at all — each is a single `invokedynamic` instruction whose
call site is resolved lazily, on first invocation, by a bootstrap method in
`java.lang.runtime.ObjectMethods` that builds the actual comparison/hash/format logic dynamically
from the record's component list, described to the bootstrap via method handles rather than
generated as conventional bytecode instructions per component.

Compile a record and disassemble it:

```bash
javac --release 21 StakeSplit.java
javap -c -p StakeSplit.class
```

The relevant fragment of the output, for `record StakeSplit(Money bonusPortion, Money cashPortion)`:

```
public final boolean equals(java.lang.Object);
    0: aload_0
    1: aload_1
    2: invokedynamic #10,  0   // InvokeDynamic #0:equals:(LStakeSplit;Ljava/lang/Object;)Z
    7: ireturn

public final int hashCode();
    0: aload_0
    1: invokedynamic #16,  0   // InvokeDynamic #1:hashCode:(LStakeSplit;)I
    6: ireturn

public final java.lang.String toString();
    0: aload_0
    1: invokedynamic #18,  0   // InvokeDynamic #2:toString:(LStakeSplit;)Ljava/lang/String;
    6: areturn
```

Read that instruction by instruction: each generated method body is exactly two or three
instructions — load `this` (and, for `equals`, load the argument), execute one `invokedynamic`,
return. All three `invokedynamic` sites target the same bootstrap method,
`ObjectMethods::bootstrap`, differing only in the method name (`"equals"`, `"hashCode"`,
`"toString"`) baked into the constant pool entry the instruction points at. On first execution of
each method, the JVM resolves that call site by invoking the bootstrap, which is handed the
record's class, a descriptor string naming every component in declaration order, and a
`MethodHandle` per component's accessor — and it constructs, at that point, the actual
`CallSite` whose target implements the comparison/hashing/formatting logic across exactly those
components, using those method handles to read each one. Every subsequent call to `equals`,
`hashCode`, or `toString` on that record class reuses the already-linked call site — the
expensive bootstrap resolution happens once per method, lazily, not once per call.

**Insight:** this is the same `invokedynamic` linkage mechanism Java's own lambda expressions and
string concatenation (`invokedynamic` for `makeConcatWithConstants` since Java 9) are built on —
records are not a special case bolted onto the verifier; they reuse the general-purpose
"describe the behaviour with metadata, let a bootstrap synthesize the actual logic at first use"
pattern the JVM has had since `invokedynamic` landed for `String::+`, `equals`, `hashCode`, and
`toString` are simply new bootstrap consumers.

> **Definition:** a record's `equals`, `hashCode`, and `toString` are each one `invokedynamic`
> instruction, resolved lazily on first call by `ObjectMethods::bootstrap` into a call site whose
> target implements the component-based logic using method handles for each accessor — not
> ordinary hand-generated method bodies.

**Interview:** each is a single `invokedynamic` call to `ObjectMethods::bootstrap`, which
synthesizes the real component-based comparison/hash/format logic lazily on first call, using
method handles for the accessors — the same dynamic-linkage mechanism lambdas and string
concatenation use, not per-component instructions baked in at compile time.

### 5.1.61 "What does `sealed` do, and what must every permitted subtype declare?"

`sealed` closes a class or interface's hierarchy to an explicit, compiler-checked, finite list of
direct subtypes — anyone outside that list, in any module or package, cannot extend or implement
the sealed type, full stop. The `permits` clause names exactly who is allowed, and every one of
those permitted subtypes must itself declare one of three modifiers, because leaving a permitted
subtype's own extensibility unstated would defeat the entire point of closing the hierarchy.

```java
public sealed interface Verdict permits DocumentVerdict, ScreeningVerdict, ReviewVerdict, WealthVerdict {}

public record DocumentVerdict(VerdictOutcome outcome, String reason, Instant decidedAt) implements Verdict {}
```

Every permitted subtype must be declared `final`, `sealed`, or `non-sealed`:

| Modifier on the permitted subtype | Meaning |
|---|---|
| `final` | This branch of the hierarchy is now completely closed — no further subtypes at all |
| `sealed` | This branch continues to be closed, but has its own `permits` list one level down |
| `non-sealed` | This branch deliberately reopens to arbitrary, unbounded extension from here |

A record implicitly satisfies `final` (5.1.52) automatically, which is exactly why `DocumentVerdict`
above needs no explicit modifier — it is a record, and every record is final by construction. A
`class` or `abstract class` permitted subtype must pick one of the three explicitly, or the
compiler rejects the declaration.

The entire reason this matters beyond documentation: an **exhaustive `switch`** over a sealed
type's permitted subtypes needs no `default` branch, because the compiler can enumerate every
possible case from the `permits` list and verify at compile time that the switch covers all of
them — a genuinely closed, compiler-verified sum type, the closest Java gets to an algebraic data
type.

```java
String describe(Verdict verdict) {
    return switch (verdict) {
        case DocumentVerdict d -> "document: " + d.outcome();
        case ScreeningVerdict s -> "screening: " + s.outcome();
        case ReviewVerdict r -> "review: " + r.outcome();
        case WealthVerdict w -> "wealth: " + w.outcome();
        // no default needed — the compiler knows these four cases are exhaustive
    };
}
```

> **Definition:** `sealed` restricts a type's direct subtypes to an explicit `permits` list,
> checked by the compiler, and every listed subtype must itself be `final`, `sealed`, or
> `non-sealed` — closing the door, extending it further, or deliberately reopening it, with no
> fourth, unstated option.

**Interview:** `sealed` plus `permits` gives you a compiler-enforced, closed list of direct
subtypes instead of an open hierarchy anyone can extend, and every permitted subtype has to say
explicitly whether it closes further (`final`/`sealed`) or deliberately reopens (`non-sealed`) —
which is also what makes exhaustive `switch` over the hierarchy possible without a `default`.

### 5.1.62 "Can an anonymous class be a permitted subtype?"

No — an anonymous class cannot implement a sealed interface or extend a sealed class at all,
regardless of whether it is named in `permits`, because a `permits` clause requires naming actual,
declared types, and an anonymous class has no name to write there; the language simply forbids the
attempt outright rather than trying to accommodate it some other way.

```java
public sealed interface Verdict permits DocumentVerdict, ScreeningVerdict, ReviewVerdict, WealthVerdict {}

// Illegal — compile error, regardless of any permits list:
Verdict adHocVerdict = new Verdict() {   // error: local classes must not extend sealed classes/interfaces
    // ...
};
```

This is not a narrow technicality about `permits` syntax — it is a deliberate closure of the
whole loophole. If anonymous (or local) classes could implement a sealed interface, the "closed,
finite, compiler-enumerable set of subtypes" guarantee sealed types exist to provide (5.1.61)
would be trivially defeated: any code, anywhere, could produce a brand-new implementation of the
interface on the spot, invisible to the sealed type's own declaration and to any exhaustive
`switch` written against it, which would silently stop being exhaustive the moment such an
instance reached it at runtime. The compiler closes this off at the language level: local classes
and anonymous classes are barred from extending or implementing a sealed type, full stop, not just
from being listed in `permits`.

> **Definition:** anonymous (and local) classes cannot implement or extend a sealed type under
> any circumstances, because permitting them would let arbitrary code silently create new,
> unenumerable implementations, defeating the closed-hierarchy guarantee sealed types provide.

**Interview:** no — the language forbids anonymous and local classes from implementing a sealed
type entirely, because allowing it would let code anywhere produce an implementation invisible to
the `permits` list, silently breaking the exhaustiveness guarantee sealed hierarchies exist to
provide.

### 5.1.63 "What is the difference between `sealed` and `final`?"

`final` means zero subtypes are allowed, ever — the hierarchy ends at this class with nothing
beneath it. `sealed` means a **known, finite, non-zero** set of subtypes is allowed, each one
explicitly named — the hierarchy continues, but only along enumerated branches the compiler can
verify, not into unbounded, unknown territory.

| | `final` | `sealed` |
|---|---|---|
| Subtypes allowed | None | A specific, named, non-empty set via `permits` |
| Hierarchy | Ends here | Continues, but only through the named branches |
| Applies to | Classes and methods | Classes and interfaces only |
| Enables exhaustive `switch` without `default`? | Trivially — there is only one type | Yes — the compiler enumerates the `permits` list |
| Each subtype's own extensibility | N/A — there are no subtypes | Each permitted subtype must itself declare `final`, `sealed`, or `non-sealed` |

A record needs no `permits`-based reasoning because it is `final` — there is exactly one type in
its "hierarchy," itself. A `sealed interface Verdict` deliberately keeps multiple named shapes
alive (`DocumentVerdict`, `ScreeningVerdict`, `ReviewVerdict`, `WealthVerdict`) while still giving
the compiler the same exhaustiveness power `final` gives a single class — that is precisely the
gap `sealed` was introduced to close: before it, a hierarchy either had exactly one shape
(`final`) or an unbounded, unknowable number of shapes (an ordinary open `interface`), with
nothing expressing "several known shapes, and only those."

> **Definition:** `final` forbids any subtype at all; `sealed` permits a specific, compiler-checked,
> non-empty set of named subtypes — both close a hierarchy to unknown extension, but `sealed`
> keeps more than one shape alive on purpose.

**Interview:** `final` means no subtypes whatsoever; `sealed` means a specific, named, finite set
of subtypes the compiler can enumerate — both are closed to arbitrary outside extension, but
`sealed` deliberately keeps multiple known shapes in the hierarchy instead of collapsing to one.

### 5.1.64 "Sealed interface or enum — how do you choose?"

By whether the cases are pure, uniform constants or genuinely different shapes carrying different
data — `enum` for the former, a `sealed` hierarchy of records for the latter. The test is not
"how many cases are there" but "do the cases differ in what data they carry, not just in which
constant they are."

An `enum` is the right tool when every case is structurally identical — the same fields, if any,
just different values — and the cases really are a fixed, closed set of *named singleton
constants*. The domain's account lifecycle values (`PENDING_VERIFICATION`, `ACTIVE`, `DORMANT`,
`CLOSING`, `CLOSED`) are exactly this shape: each is just a label, none carries case-specific
extra data beyond what every other case also carries.

A `sealed` interface (typically implemented by records) is the right tool when the cases carry
**genuinely different data shapes** — an algebraic sum type, not a set of labeled constants. The
domain's `Verdict` hierarchy is exactly this shape: `DocumentVerdict` carries a document-check
outcome and reasoning from an identity vendor, `ScreeningVerdict` carries a watchlist match
result, `ReviewVerdict` carries a human reviewer's decision and identity — four cases that share
being "a verdict" conceptually but have no common useful field set beyond an outcome, because what
each one is *about* is different.

| | `enum` | `sealed` interface of records |
|---|---|---|
| Case shape | Identical across all cases | Can differ completely per case |
| Per-case data | Shared fields only, same for every constant | Each case can have its own distinct component list |
| Singleton-ness | Each constant is a single, fixed instance | Each case is a normal type — as many instances as you construct |
| Exhaustive `switch` | Yes, no `default` needed | Yes, no `default` needed, via `permits` |
| Adding a new case later | Add a constant | Add a new permitted record — but every existing exhaustive `switch` over the hierarchy now needs updating, which the compiler forces |

```java
// Right fit: uniform constants, no per-case data.
public enum RestrictionStatus { ACTIVE, LIFTED, EXPIRED }

// Right fit: genuinely different shapes per case.
public sealed interface Verdict permits DocumentVerdict, ScreeningVerdict, ReviewVerdict, WealthVerdict {}
public record DocumentVerdict(VerdictOutcome outcome, String reason, Instant decidedAt) implements Verdict {}
public record ScreeningVerdict(VerdictOutcome outcome, String matchedListName) implements Verdict {}
```

**Pitfall:** modeling genuinely different-shaped cases as one `enum` with an ever-growing set of
optional, mostly-null fields to cover every case's needs (`WEALTH_REFERRED` needing a referral
reason field that every other constant leaves null) — a shape that only an `enum` in name; a
sealed hierarchy expresses the same information with each case carrying exactly what it needs and
nothing more, plus compiler-checked exhaustiveness on pattern matching over the differing shapes.

> **Definition:** choose `enum` when every case is a uniform, data-identical named constant;
> choose a `sealed` hierarchy of records when the cases carry genuinely different data shapes —
> the deciding question is whether the cases differ only in *which* one they are, or also in
> *what they carry*.

**Interview:** `enum` when the cases are uniform, data-identical constants; a `sealed` interface
of records when the cases carry genuinely different data — the test is whether cases differ only
in identity or also in shape.

---

## Pitfalls

### Assuming `orElse` and `orElseGet` are interchangeable

**Wrong**

```java
public Coupon resolveCoupon(Optional<Coupon> suppliedCoupon) {
    return suppliedCoupon.orElse(bonusService.lookupDefaultCoupon());   // network call every time
}
```

**Right**

```java
public Coupon resolveCoupon(Optional<Coupon> suppliedCoupon) {
    return suppliedCoupon.orElseGet(bonusService::lookupDefaultCoupon);   // only on empty
}
```

**Why people believe it:** the two methods look like stylistic variants of the same call — same
return type, near-identical name, both "give me a fallback." Nothing in the method signature
signals the eager-vs-lazy evaluation difference; it only shows up as a performance or
side-effect bug under load.

### Believing `parallelStream()` is a free performance switch

**Wrong**

```java
List<Restriction> active = client.restrictions().parallelStream()
        .filter(r -> r.status() == RestrictionStatus.ACTIVE)
        .toList();   // four elements — fork/join overhead exceeds any benefit
```

**Right**

```java
List<Restriction> active = client.restrictions().stream()
        .filter(r -> r.status() == RestrictionStatus.ACTIVE)
        .toList();   // sequential — correct choice for a handful of elements
```

**Why people believe it:** the API surface is identical to `stream()` with one word added, and
demo-sized benchmarks over huge collections make it look like a strictly-better default, hiding
the four conditions from 5.1.38 that have to hold before it actually pays off.

### Reaching for `hashCode()` as a persisted content fingerprint

**Wrong**

```java
int digest = stakeSplit.hashCode();
auditLog.record(reservationId, digest);   // compared against a recomputed hashCode after redeploy
```

**Right**

```java
String digest = HexFormat.of().formatHex(
        MessageDigest.getInstance("SHA-256").digest(canonicalBytes(stakeSplit)));
auditLog.record(reservationId, digest);
```

**Why people believe it:** `hashCode()` looks like a ready-made, zero-effort fingerprint, and for
records specifically it feels doubly safe because it is "generated by the compiler" rather than
hand-written — but generated does not mean stable, and the generation mechanism (5.1.60) carries
no cross-version contract at all.

## Cheat sheet

| Question area | One-line answer |
|---|---|
| Reduce combiner | Must be associative — a parallel split tree merges partial results in an unpredictable grouping |
| Parallel stream task count | `sourceSize / (poolParallelism × 4)`, floored, min 1 — 8-core box: `2.8M / 28 = 100,000`-element leaves, 28 tasks |
| Parallel stream pool | `commonPool()`, size `cores - 1`, plus the calling thread joins in — effective width = core count |
| Blocking I/O in parallel stream | Starves the shared, JVM-wide common pool for every parallel stream, not just the caller |
| Custom pool for a parallel stream | `pool.submit(() -> stream...).join()` works but is explicitly unsupported, undocumented behaviour |
| Four conditions for parallel win | Large `N×Q`, cheap even splits, CPU-bound independent work, idle common pool |
| `forEach(list::add)` vs `collect(toList())` | `forEach` shares one mutable target across threads (race); `collect` isolates then merges |
| Spliterator | Splittable iterator; `trySplit()` enables parallelism; characteristics let stages skip work |
| `LinkedList` parallel | No random access — every split is an O(n) node walk, and not `SUBSIZED` |
| `Optional` scope | Return types only — never fields, params, or collection elements |
| `orElse` vs `orElseGet` | `orElse` always evaluates its argument; `orElseGet` only on empty |
| `isPresent()`+`get()` | Anti-pattern — recreates a null check with none of `Optional`'s atomicity guarantees |
| `Optional` not `Serializable` | Deliberate — javadoc scopes it to return types, not fields |
| `map` with a null-returning function | Produces `Optional.empty()`, not an NPE |
| `Optional.empty() == Optional.empty()` | `true` today (singleton), but unspecified — use `equals()`/`isEmpty()` |
| `var` scope | Locals with initializers, `for` loops, try-with-resources only — never fields/params/returns |
| `var` runtime cost | None — fully erased at compile time |
| `var list = new ArrayList<>()` | Infers `ArrayList<Object>` — diamond has no target type |
| `var f = () -> 1` | Illegal — a lambda has no type without a target functional interface |
| Record generates | Final fields, canonical constructor, named accessors, component-based equals/hashCode/toString |
| Compact constructor | Validates/normalizes parameters; compiler still assigns fields; cannot `this.field =` directly |
| Record immutability | Shallow only — mutable component types stay mutable through the reference |
| Array record component | `equals`/`hashCode` fall back to reference identity, not contents — a correctness bug |
| Genuinely-immutable `List` component | `List.copyOf(...)` in the compact constructor |
| Persisting record `hashCode` | Never — no cross-version/cross-run stability guarantee |
| Record as JPA entity | No — needs no-arg constructor, mutable fields, subclassing for proxies, none of which records provide |
| Record deserialization | Calls the canonical constructor with stream values — compact-constructor validation always runs |
| Record equals/hashCode/toString bytecode | Single `invokedynamic` per method, resolved lazily by `ObjectMethods::bootstrap` |
| `sealed` | Closes a hierarchy to an explicit `permits` list; every permitted type must be `final`/`sealed`/`non-sealed` |
| Anonymous class as permitted subtype | Never allowed, under any circumstances |
| `sealed` vs `final` | `final` = zero subtypes; `sealed` = a known, finite, named set of subtypes |
| `sealed` interface vs `enum` | `enum` for uniform constants; `sealed` records for genuinely different per-case data shapes |

## Self-test

**Q1.** A teammate benchmarks `reservations.parallelStream().reduce(BigDecimal.ZERO, BigDecimal::add, BigDecimal::add)` against a 12-element in-memory list and finds it slower than the sequential form. Is that a bug in the parallel stream implementation?

<details><summary>Answer</summary>

No — this is exactly the expected outcome of the four-conditions test in 5.1.38 failing on
condition one. Twelve elements means `N × Q` is tiny; the fork/join scheme still pays its full
overhead — spliterator splitting, task forking, worker scheduling, combiner merges across however
many leaves 12 elements produce — and that overhead dwarfs the actual arithmetic being done. There
is no bug: parallel streams are not "sequential streams but faster," they are a decomposition
strategy that only wins once the per-element work and the element count together clear the
overhead bar. The fix is not tuning the pool; it's using `.stream()` for small, in-memory
collections and reserving `.parallelStream()` for genuinely large sources like the domain's 2.8M
daily stake reservations.

</details>

**Q2.** Why does `reservations.parallelStream().map(r -> callDocumentVendor(r)).toList()` risk stalling unrelated code elsewhere in the same service, even code that never touches `reservations`?

<details><summary>Answer</summary>

Because `ForkJoinPool.commonPool()` is a single, JVM-wide, fixed-size pool (`cores - 1` workers)
shared by every parallel stream in the process (5.1.35), not a pool scoped to this one call. If
`callDocumentVendor` blocks on the identity vendor (p99 38s per the domain's verified figures),
each blocked leaf task occupies one of the pool's few worker threads for up to that long. With
only seven workers on an 8-core box, a small number of concurrently blocked calls can exhaust the
pool entirely, and any other parallel stream running anywhere else in the same JVM — a
`BalanceView` aggregation, a `PaymentRun` reconciliation — queues behind it, because there is
nowhere else for its tasks to run. The fix is to keep blocking I/O out of parallel-stream bodies
entirely and dispatch it elsewhere (a dedicated executor, or virtual threads).

</details>

**Q3.** A record `PaymentIntent(ClientId clientId, Money amount, Instant createdAt)` needs an audit-log entry whenever two `PaymentIntent` instances are compared and found unequal despite looking "the same" to a human reviewer. What is the most likely cause if `amount` is a `record Money(BigDecimal amount, Currency currency)`?

<details><summary>Answer</summary>

`BigDecimal.equals` compares scale as well as unscaled value — `BigDecimal.valueOf(65)` (scale 0)
and `new BigDecimal("65.00")` (scale 2) are numerically equal but not `.equals()`-equal, and since
`Money`'s generated `equals` delegates to `BigDecimal.equals` for its `amount` component (and a
record's generated `equals` uses each component's own `equals`, transitively), two `PaymentIntent`
values built from differently-scaled `BigDecimal`s for the same nominal amount will report as
unequal even though a human reading the printed values sees "65" and "65.00" as the same money.
This is not a record bug — it's `BigDecimal.equals`'s well-known scale-sensitivity surfacing
through the record's component-wise equals, and the fix is normalizing scale at construction
(a compact constructor on `Money` calling `.setScale(...)`, consistent with the rounding
discipline the domain's bonus rules already use) rather than anything to do with how records
generate `equals`.

</details>

**Q4.** Why does `Collectors.summingInt(Reservation::stakeAmountMinorUnits)` risk producing a wrong total over the domain's 2.8M daily stake reservations, while `Collectors.summingLong` on the same data does not?

<details><summary>Answer</summary>

`summingInt`'s accumulator, verified against `java.util.stream.Collectors` at the jdk-21+35 tag,
is a plain `int[1]` — the running total is a real 32-bit `int` with no compensation, so it wraps
silently once the sum exceeds `Integer.MAX_VALUE` (about 2.1 billion). `summingLong` accumulates
into a `long[1]`, which does not overflow at anywhere near this data volume. If stake amounts are
represented in minor units (cents) and volume is high enough — the domain's stake reservations
average 4.20 at 2.8M/day, which is well within `int` range on its own, but a running total across
a full year's ledger entries or a coarser unit is exactly the kind of aggregate where this bites —
`summingInt` is the wrong collector to reach for whenever the *sum* itself, not just each
individual value, might exceed `int` range. This is a distinct trap from `IntStream.sum()`'s
well-known overflow, but it is the same underlying mechanism.

</details>

**Q5.** A `sealed interface GateOutcome permits Passed, Referred, Failed {}` has three record implementations. A teammate adds a fourth case, `Skipped`, as a new record implementing `GateOutcome`, but forgets to add it to the `permits` clause. What happens?

<details><summary>Answer</summary>

The compiler rejects `Skipped`'s declaration outright — `implements GateOutcome` on a type not
named in `GateOutcome`'s `permits` clause is a compile error, not a runtime surprise. This is the
entire enforcement mechanism `sealed` provides: the permitted-subtypes list is checked at compile
time on both ends — a subtype cannot claim to implement a sealed interface unless it is listed,
and the interface's `permits` list cannot omit a type that does implement it either. The fix is
purely mechanical: add `Skipped` to the `permits` clause, at which point every existing exhaustive
`switch` over `GateOutcome` elsewhere in the codebase now also fails to compile until `Skipped` is
handled there too — which is precisely the safety net exhaustive switching over a sealed hierarchy
is supposed to provide when a new case is introduced.

</details>

**Q6.** Why is `Optional<List<Restriction>>` almost always the wrong return type for a method like `findRestrictionsForClient(ClientId id)`, compared to returning a plain `List<Restriction>`?

<details><summary>Answer</summary>

Because an empty collection already expresses "nothing found" without needing an extra wrapper —
`List.of()` and "no restrictions for this client" mean the same thing, and every caller already
knows how to check `.isEmpty()` or iterate zero times safely. Wrapping the whole collection in
`Optional` adds a second way to express the same absence (`Optional.empty()` vs. a non-empty
`Optional` holding an empty list, both of which some caller must now also handle) with no
corresponding benefit, and it pushes an extra unwrap (`.orElse(List.of())` or similar) onto every
call site for no real gain. `Optional` earns its place wrapping a *single, genuinely absent* value
— an individual `Restriction` that might not exist — not a collection, which has its own
built-in, unambiguous representation of absence: being empty.

</details>

**Q7.** `var settledCount = reservations.stream().filter(r -> r.status() == ReservationStatus.SETTLED).count();` — what type does `settledCount` get, and could this declaration have used `var` if `count()` were replaced with `.findFirst()`?

<details><summary>Answer</summary>

`settledCount` infers `long`, because `Stream.count()` is declared to return `long`, and that
return type is a fully self-sufficient, already-concrete type for `var` to copy — no diamond, no
lambda, nothing ambiguous about it. Replacing `.count()` with `.findFirst()` would still work with
`var`: `findFirst()` returns `Optional<Reservation>`, a concrete generic type with its type
argument already fixed by the stream's element type, so `var` would infer
`Optional<Reservation>` — also self-sufficient, for the same reason `new ArrayList<Reservation>()`
would be (as opposed to the bare-diamond case in 5.1.50, where the type argument itself is what's
missing).

</details>

**Q8.** A `record LedgerEntry(RoundId roundId, Position position, Money amount, Instant postedAt)` needs a derived, computed `boolean isCredit()` that other code will call like a component accessor. Can a record declare methods beyond what it auto-generates, and does adding one change anything about the automatically generated members?

<details><summary>Answer</summary>

Yes — a record body can declare additional instance methods, static methods, static fields, and
even additional constructors (as long as every non-canonical constructor ultimately delegates to
the canonical one via `this(...)`), exactly like an ordinary class body, and none of that changes
the auto-generated canonical constructor, accessors, `equals`, `hashCode`, or `toString` at all —
they are generated independently based purely on the component list in the record header. So
`public boolean isCredit() { return amount.amount().signum() > 0; }` inside `LedgerEntry`'s body
compiles fine, reads naturally like an accessor from the caller's side, but is not itself a
component — it does not participate in `equals`/`hashCode`/`toString`, and there is no way to make
it participate short of adding it as an actual header component (which would then require it to be
supplied at construction, unlike a derived value).

</details>

## Deferred

None.

## Open questions

None.

---

**Leaves covered:** 5.1.33–5.1.64 (32 leaves)
**Leaves deferred:** none
**Diagrams included:** none
**Target version:** Java 21 LTS
**Lines:** 1766
