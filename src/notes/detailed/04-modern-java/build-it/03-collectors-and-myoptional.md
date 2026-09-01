# 04 Modern Java — Build it — BUILD IT (§4.3, §4.4)

**Target version: Java 21 LTS.** | **Part 4 of 5** | [Index](../00-index.md)
Previous: [Build it — mystream](02-mystream.md) · Next: [Build it — records sealed patterns](04-records-sealed-patterns.md)

Everything in this file is `[BUILD]`: complete, compiling, generic Java 21, run through
`javac --release 21` on this machine before being written down. Every build ends with a "Diff vs
the real one" table. §4.3 builds a five-function collector protocol and four collectors on top of
it; §4.4 builds `MyOptional<T>` end to end. Both sections model the exact shape the JDK uses —
`java.util.stream.Collectors`'s internal `CollectorImpl` and `java.util.Optional` — closely enough
that the diff tables are short and specific rather than hand-wavy.

## The collector family, before the details

Every collector in this file — the JDK's and ours — is one instantiation of the same
five-function shape. The table is the map; read it before the code.

| Collector | Accumulator type `A` | Characteristics | Finisher | Section |
|---|---|---|---|---|
| `toMyList` | `ArrayList<T>` | `IDENTITY_FINISH` | identity (cast) | this file |
| `joiningMy` | `StringBuilder` | none | `sb -> sb.append(suffix).toString()` | this file |
| `groupingByMy` | `HashMap<K,A>` | none (mutates then casts) | `replaceAll` + unchecked cast | this file |
| `topN` | `PriorityQueue<T>` (bounded) | none | drain heap, sort descending | this file |
| `mode` | `HashMap<T,long[]>` | none | scan for max count | this file |
| `longStats` | `long[4]` | none | wrap array in a record | this file |
| `concurrentGroupingBy` | `ConcurrentHashMap<K,List<T>>` | `CONCURRENT`, `UNORDERED`, `IDENTITY_FINISH` | identity (cast) | this file |
| `Collectors.toList()` | `ArrayList<T>` | `IDENTITY_FINISH` | identity (cast) | JDK, diffed below |
| `Collectors.joining(...)` | `StringJoiner` | none | `StringJoiner::toString` | JDK, diffed below |
| `Collectors.groupingBy(...)` | `HashMap<K,A>` | none or `IDENTITY_FINISH` (fast path) | conditional, see below | JDK, diffed below |
| `Collectors.summarizingInt(...)` | `int[]`/`long[]` slots inside `IntSummaryStatistics` | none | identity | JDK, diffed below |
| `Collectors.toConcurrentMap(...)` | `ConcurrentHashMap` | `CONCURRENT`, `UNORDERED`, `IDENTITY_FINISH` | identity (cast) | JDK, diffed below |

Every row is the same tuple: `(Supplier<A>, BiConsumer<A,T>, BinaryOperator<A>, Function<A,R>,
Set<Characteristics>)`. The rest of §4.3 is instantiating that tuple five different ways and
proving what each `Characteristics` flag actually changes about the runtime path.

---

### The five-function collector contract, and why a contract exists at all

**Mental model.** A collector is not "a thing that builds a list." It is a *recipe* for folding a
stream into a mutable container, expressed as five interchangeable parts, so that the exact same
recipe can run three different ways — one thread walking the stream in order, many threads each
folding a private container and merging pairwise, or many threads folding directly into one
shared container — without the collector author writing three different implementations. The
`Stream` machinery picks which of those three shapes to run; the collector only supplies the
verbs.

**Why it exists.** Before `Collector` (Java 8), the idiom was `Stream.reduce` with an explicit
accumulator and combiner, which works for immutable folds (`sum`, `max`) but breaks down for
*mutable* reduction: building a `List<T>` by `reduce` would need to copy the whole list on every
element to stay pure, which is quadratic. `Collector` legitimises mutation of a *private,
per-thread* accumulator — `List::add` instead of `list -> list.plus(x)` — while still composing
safely under parallelism, because the mutation never crosses a thread boundary except through the
declared `combiner`.

**When to reach for it, and when not.** Reach for a custom `MyCollector` when the fold needs
*shared mutable state with a defined merge rule* that no built-in collector expresses —
bounded top-N, frequency tables, primitive accumulator arrays. Do not reach for it when
`Stream.reduce(identity, accumulator, combiner)` already says what you mean and the accumulator
type is small and immutable (a running `long` sum, for instance) — `reduce` is simpler to read and
the JIT does not need to inline five virtual dispatches to understand it. Do not reach for it
when a two-line pipeline of existing `Collectors` composes the same answer — a hand-rolled
collector that reimplements `groupingBy(classifier, counting())` is friction, not clarity.

**How it works.** The five functions and their contract:

```java
public interface MyCollector<T, A, R> {
    Supplier<A> supplier();
    BiConsumer<A, T> accumulator();
    BinaryOperator<A> combiner();
    Function<A, R> finisher();
    Set<Characteristics> characteristics();

    enum Characteristics { CONCURRENT, UNORDERED, IDENTITY_FINISH }
}
```

- `supplier()` creates a **new, private** accumulator — called once per thread that starts a fold,
  never shared unless `CONCURRENT` is declared (mechanism proved in the `CONCURRENT` section
  below).
- `accumulator()` folds one `T` into an `A` **by mutation**, returning nothing. This is the
  contract's central idea: `A` is a scratch container, not an immutable value, so `List::add`
  is a legal accumulator and `list -> list.plus(x)` is not what the contract wants.
- `combiner()` merges two `A`s produced by two different threads into one `A`. It must be
  associative — `combiner(combiner(a,b),c) == combiner(a,combiner(b,c))` — because the pipeline
  is free to merge in any pairing order.
- `finisher()` converts the accumulator into the result type `R`. When `A` and `R` are the same
  type, `IDENTITY_FINISH` lets the runtime skip calling it and just cast — this is the
  "`IDENTITY_FINISH` fast path" from 4.3.7's diff, and it is a real branch in the JDK, not a
  documentation nicety: `ReferencePipeline.collect` ends with `return
  collector.characteristics().contains(Collector.Characteristics.IDENTITY_FINISH) ? (R) container
  : collector.finisher().apply(container);` — the cast is unchecked and only safe because the
  collector author promised `A == R` by setting the flag.
- `characteristics()` is metadata the *caller* (the stream pipeline) reads to pick a faster
  execution path. It is not decoration — §4.3.6 below proves that three specific characteristics,
  read together with the stream's own ordering, change which code executes.

**Diagram.** None assigned to this file; the table above is the substitute.

**A minimal concrete example** — the identity-finish, structural twin of `Collectors.toList()`:

```java
static <T> MyCollector<T, List<T>, List<T>> toMyList() {
    return MyCollector.Impl.identityFinish(
            ArrayList::new,
            List::add,
            (left, right) -> { left.addAll(right); return left; }
    );
}
```

against a plain `record` implementation of the interface:

```java
record Impl<T, A, R>(
        Supplier<A> supplier,
        BiConsumer<A, T> accumulator,
        BinaryOperator<A> combiner,
        Function<A, R> finisher,
        Set<Characteristics> characteristics
) implements MyCollector<T, A, R> {

    @SuppressWarnings("unchecked")
    static <T, A> Impl<T, A, A> identityFinish(
            Supplier<A> supplier, BiConsumer<A, T> accumulator,
            BinaryOperator<A> combiner, Characteristics... extra) {
        Set<Characteristics> cs = EnumSet.of(Characteristics.IDENTITY_FINISH);
        for (Characteristics c : extra) cs.add(c);
        return new Impl<>(supplier, accumulator, combiner, a -> a, cs);
    }
}
```

Run through the real stream machinery via an adapter into `java.util.stream.Collector` (so we can
prove behaviour against the actual `ReferencePipeline`, not a reimplementation of it):

```java
List<String> ids = withdrawals.stream()
        .map(WithdrawalTransaction::id)
        .collect(toJdk(Collectors_04.toMyList()));
// ids = [W-1, W-2, W-3, W-4, W-5, W-6, W-7, W-8, W-9, W-10]
```

**The gotcha.** `combiner()` is written and tested even for collectors you only ever run
sequentially, because nothing in the type system stops a caller from doing
`withdrawals.parallelStream().collect(myCollector)`. An untested combiner is a latent parallel-only
bug: `toMyList`'s combiner (`left.addAll(right); return left;`) is easy to get backwards
(`right.addAll(left); return right;` silently reverses element order across the merge boundary) and
both versions pass every sequential test.

> **Definition:** a `Collector<T,A,R>` is a named tuple of five functions — `supplier`,
> `accumulator`, `combiner`, `finisher`, `characteristics` — that lets one fold definition run
> correctly whether the stream walks its elements on one thread or splits them across many.

#### `toList`, `joining`, `groupingBy` — three instantiations of the same tuple

**`joiningMy`** — `A` is a `StringBuilder` seeded with the prefix; the accumulator appends the
delimiter only when the builder already holds more than the prefix (that length check *is* the
"have I seen a first element yet" flag, done without a separate boolean):

```java
static MyCollector<CharSequence, StringBuilder, String> joiningMy(
        String delimiter, String prefix, String suffix) {
    Supplier<StringBuilder> supplier = () -> new StringBuilder(prefix);
    BiConsumer<StringBuilder, CharSequence> accumulator = (sb, next) -> {
        if (sb.length() > prefix.length()) sb.append(delimiter);
        sb.append(next);
    };
    BinaryOperator<StringBuilder> combiner = (left, right) -> {
        if (right.length() > prefix.length()) {
            if (left.length() > prefix.length()) left.append(delimiter);
            left.append(right, prefix.length(), right.length());
        }
        return left;
    };
    Function<StringBuilder, String> finisher = sb -> sb.append(suffix).toString();
    return new MyCollector.Impl<>(supplier, accumulator, combiner, finisher, Set.of());
}
```

Run: `withdrawals.stream().map(WithdrawalTransaction::id).collect(toJdk(joiningMy(", ", "[", "]")))`
produces `[W-1, W-2, W-3, W-4, W-5, W-6, W-7, W-8, W-9, W-10]`; the empty-stream case produces
`[]` — prefix and suffix with nothing between, exactly matching `Collectors.joining`'s contract for
zero elements.

**`groupingByMy`** (two-arg, downstream defaults to `toMyList`; three-arg takes any downstream
`MyCollector`) — this is where the combiner has to merge *two maps of accumulators*, not two flat
values, which is the part every from-scratch attempt gets wrong first:

```java
static <T, K, A, D> MyCollector<T, Map<K, A>, Map<K, D>> groupingByMy(
        Function<T, K> classifier, MyCollector<T, A, D> downstream) {
    Supplier<A> downstreamSupplier = downstream.supplier();
    BiConsumer<A, T> downstreamAccumulator = downstream.accumulator();
    BiConsumer<Map<K, A>, T> accumulator = (map, t) -> {
        K key = classifier.apply(t);
        A container = map.computeIfAbsent(key, k -> downstreamSupplier.get());
        downstreamAccumulator.accept(container, t);
    };
    BinaryOperator<A> downstreamCombiner = downstream.combiner();
    BinaryOperator<Map<K, A>> combiner = (m1, m2) -> {
        for (Map.Entry<K, A> e : m2.entrySet()) {
            m1.merge(e.getKey(), e.getValue(), downstreamCombiner);
        }
        return m1;
    };
    Function<Map<K, A>, Map<K, D>> finisher = intermediate -> {
        intermediate.replaceAll((k, v) -> (A) downstream.finisher().apply(v));
        return (Map<K, D>) (Map<?, ?>) intermediate;
    };
    return new MyCollector.Impl<>(HashMap::new, accumulator, combiner, finisher, Set.of());
}
```

The **correct combiner** is the crux of leaf 4.3.2: it does not `putAll` (which would silently drop
one thread's bucket whenever both threads see the same key), it `merge`s each key through the
*downstream's own combiner*, so a `groupingBy(rail, toMyList())` run in parallel concatenates the
two partial lists for `"CARD"` instead of one clobbering the other. Proved by running the same
pipeline sequential and parallel over ten withdrawals and comparing bucket sizes:

```
groupingByMy byRail sizes = CARD:6 BANK:4
groupingByMy (parallel) sizes = CARD:6 BANK:4
groupingByMy + counting = {BANK=4, CARD=6}
```

Both agree, which is the actual proof — a broken combiner (`putAll`) would make the parallel sizes
disagree with the sequential ones only nondeterministically, which is exactly why the bug survives
code review and ships.

**Version trap.** `Collectors.toUnmodifiableList()` (Java 10) and the no-arg terminal method
`Stream.toList()` (Java 16) both return an *unmodifiable* list; `Collectors.toList()` — and this
file's `toMyList()` — make no such promise and return a mutable `ArrayList` in practice. Code that
does `stream().toList().add(x)` compiles against `Stream.toList()` and throws
`UnsupportedOperationException` at runtime; the same call against `.collect(Collectors.toList())`
does not throw, on every JDK release through 21, purely because nobody has changed the
implementation, not because the contract guarantees it.

**Interview:** "why does `groupingBy`'s combiner need `merge`, not `putAll`?" — because two threads
can independently discover the same key, and `putAll` silently replaces one thread's whole bucket
with the other's instead of joining them; `merge` is the only one of the two that is associative
over multisets.

---

### A bounded top-N collector over a `PriorityQueue`, with a correct heap-merge combiner

**Mental model.** A bounded top-N collector is a self-trimming min-heap: it always holds at most
`n` elements, and it is the *smallest* of the currently-held elements that gets evicted every time
a bigger candidate shows up — which means the heap's own minimum is a standing "current cutoff",
recomputed lazily instead of by resorting.

**Why it exists.** The naive approach — collect everything, sort, take `n` — is `O(m log m)` for
`m` total elements and holds all `m` in memory at once. A bounded heap collector is `O(m log n)`
and holds at most `n` elements at any time; for "top 3 of 2.8 million stake reservations" that is
the difference between sorting 2.8M entries and maintaining a heap of 3.

**When to reach for it, and when not.** Reach for it when `n` is small and fixed and the source is
large or streaming — exactly the shape of "top-3 withdrawals" or "top-10 highest-value clients this
month". Prefer the sibling `stream.sorted(comparator.reversed()).limit(n)` when the stream is
already small, or when you need the full sorted order rather than just the top slice — `sorted`
does more work (a full sort) but the intent is clearer to a reader and there's no hand-rolled
combiner to get wrong. `sorted().limit(n)` also short-circuits differently: on an already-sorted
or nearly-sorted source, `limit` can stop the upstream early in ways a full-scan collector never
does, so for a source that arrives pre-sorted, `sorted().limit(n)` can be the faster choice despite
its worse asymptotic bound.

**How it works.** `[X-REF 02]` A `PriorityQueue<T>` is a binary heap backed by a resizable array:
element `i`'s children live at `2i+1` and `2i+2`, `offer` appends then sifts the new element up
toward the root while it is smaller (for a min-heap ordered by the supplied `Comparator`) than its
parent, and `poll` swaps the last element into the root and sifts it down — both operations
`O(log n)`. Guide 02 (Java collections) is where the full heap-internals walk with sift-up/sift-down
pseudocode and the array-doubling growth policy lives; here is enough to read this collector: the
`peek()` at the root is always the *current minimum* of the bounded set, which is exactly the value
you must compare a new candidate against to decide whether it displaces anything.

```java
static <T> MyCollector<T, PriorityQueue<T>, List<T>> topN(int n, Comparator<T> comparator) {
    if (n <= 0) throw new IllegalArgumentException("n must be positive");
    Supplier<PriorityQueue<T>> supplier = () -> new PriorityQueue<>(n, comparator);
    BiConsumer<PriorityQueue<T>, T> accumulator = (heap, t) -> {
        if (heap.size() < n) {
            heap.offer(t);
        } else if (comparator.compare(t, heap.peek()) > 0) {
            heap.poll();
            heap.offer(t);
        }
    };
    BinaryOperator<PriorityQueue<T>> combiner = (h1, h2) -> {
        for (T t : h2) accumulator.accept(h1, t);
        return h1;
    };
    Function<PriorityQueue<T>, List<T>> finisher = heap -> {
        List<T> result = new ArrayList<>(heap);
        result.sort(comparator.reversed());
        return result;
    };
    return new MyCollector.Impl<>(supplier, accumulator, combiner, finisher, Set.of());
}
```

**`[PROVE]` the combiner merges two bounded heaps correctly.** The naive-looking combiner
temptation is `h1.addAll(h2); return h1;` — wrong, because it can grow `h1` past size `n` and never
re-evicts. The correct combiner instead **replays every element of the smaller heap through the
same accumulator logic** used for fresh elements, so each of `h2`'s elements gets a fair
offer-or-displace comparison against `h1`'s current state, one at a time, preserving the "never
exceed `n`, always keep the `n` largest seen so far" invariant that a single-threaded fold
maintains. Proved by running the identical top-3 query sequential and parallel over the same ten
withdrawals — a broken combiner would show a parallel result missing one of the true top-3 (whichever
value happened to land in the smaller partial heap that a naive `addAll` let overflow, then got
truncated or left unsorted):

```java
List<Long> top3 = withdrawals.stream()
        .collect(toJdk(topN(3, Comparator.comparingLong(WithdrawalTransaction::amountMinorUnits))))
        .stream().map(WithdrawalTransaction::amountMinorUnits).toList();
// top3 (sequential) = [260, 180, 92]

List<Long> top3Parallel = withdrawals.parallelStream()
        .collect(toJdk(topN(3, Comparator.comparingLong(WithdrawalTransaction::amountMinorUnits))))
        .stream().map(WithdrawalTransaction::amountMinorUnits).toList();
// top3 (parallel, combiner-merged heaps) = [260, 180, 92]
```

Sequential and parallel agree on exactly the three largest withdrawal amounts in the sample data
(260, the average bank withdrawal; 180, the average card withdrawal; 92, the average chargeback —
all three straight out of Appendix A's verified figures), which is the actual proof the leaf asks
for: the combiner reproduces the single-threaded answer regardless of how the fork-join split the
work.

**The gotcha.** The finisher must re-sort before returning — the heap's own iteration order is
*not* sorted (only the root, index 0, is guaranteed to be the minimum; the rest of the backing
array only satisfies the heap property, not a total order), so returning
`new ArrayList<>(heap)` without the `result.sort(comparator.reversed())` line produces the right
*set* of top-`n` elements in the wrong, heap-internal order — a bug that is invisible in a test
that only checks set membership and not order.

> **Definition:** a bounded top-N collector holds a size-capped min-heap ordered by the ranking
> comparator, evicting the current minimum whenever a larger candidate arrives, so the whole fold
> runs in `O(m log n)` instead of `O(m log m)` and never materializes more than `n` elements.

**Diff vs the real one — there is no `Collectors.topN`, so the diff is against its closest built-in
substitute, `Stream.sorted(cmp.reversed()).limit(n)`:**

| Axis | This build (`topN`) | `sorted().limit(n)` |
|---|---|---|
| Time complexity | `O(m log n)` | `O(m log m)` |
| Peak memory | `O(n)` | `O(m)` (materializes the whole sorted run) |
| Short-circuiting | None — every element is compared | Can short-circuit on already-sorted/`SORTED`-flagged sources |
| Stability | Not stable — heap ties break arbitrarily | Stable if `sorted()`'s underlying `Arrays.sort` is used on a `Stream` (it is, via `TimSort`) |
| Parallel combiner | Hand-written, replay-based, this file's | JDK's parallel sort (`Arrays.parallelSort`-derived merge) |
| Null policy | `NullPointerException` from `Comparator.compare` on a null element, same as `sorted()` | same |
| Thread safety | Each thread's heap is private until combine; no shared mutable state | same shape |
| Why the JDK doesn't ship one | Its cutoff behaviour (`n`) is a query-specific parameter with no single natural default, unlike `toList`/`joining`/`groupingBy`, which are used with the same signature everywhere |

---

### A boxing-free statistics collector over a `long[]` accumulator

**Mental model.** The accumulator is not an object with four boxed fields (`Long count`, `Long
sum`, ...) — it is a raw four-slot `long[]`, and every update is an in-place array write. There is
nothing to box because there is nothing but primitives from the array's creation to its final
read.

**Why it exists.** A naive stats accumulator as an immutable record — `record RunningStats(long
count, long sum, long min, long max)` with each accumulate step producing a *new* record — forces
one allocation per element folded: 2.8 million stake reservations means 2.8 million short-lived
record instances if the accumulator is immutable. A mutable array accumulator does zero allocation
after its single initial `new long[4]`.

**When to reach for it, and when not.** Reach for a primitive-array accumulator when the fold runs
over a genuinely large stream and the accumulator's shape is small, fixed-size, and entirely
primitive — sums, counts, running min/max. Prefer `Collectors.summarizingInt`/`summarizingLong` (or
just `IntStream`/`LongStream.summaryStatistics()`, which needs no `Collector` at all) when the
built-in fields are exactly what's needed; those already use the same array-of-primitives trick
internally (Verified Figures §7), so hand-rolling buys nothing extra there beyond controlling
exactly which four numbers are tracked.

**How it works.**

```java
static <T> MyCollector<T, long[], LongStats> longStats(ToLongFunction<T> extractor) {
    Supplier<long[]> supplier = () -> new long[] { 0L, 0L, Long.MAX_VALUE, Long.MIN_VALUE };
    BiConsumer<long[], T> accumulator = (a, t) -> {
        long v = extractor.applyAsLong(t);
        a[0]++;               // count
        a[1] += v;             // sum
        if (v < a[2]) a[2] = v; // min
        if (v > a[3]) a[3] = v; // max
    };
    BinaryOperator<long[]> combiner = (a, b) -> {
        a[0] += b[0];
        a[1] += b[1];
        a[2] = Math.min(a[2], b[2]);
        a[3] = Math.max(a[3], b[3]);
        return a;
    };
    Function<long[], LongStats> finisher =
            a -> new LongStats(a[0], a[1], a[0] == 0 ? 0 : a[2], a[0] == 0 ? 0 : a[3]);
    return new MyCollector.Impl<>(supplier, accumulator, combiner, finisher, Set.of());
}
```

**`[NUM]` benchmarked against `Collectors.summarizingInt`, over 2,800,000 synthetic stake
reservations** (amounts spread around the domain's 420-minor-unit average stake, Appendix A) —
timed on this machine after a three-iteration JIT warm-up, both paths producing the identical
answer first, so the timing comparison is meaningful and not comparing apples to a bug:

```
longStats  = LongStats[count=2800000, sum=1176272936, min=200, max=640] avg=420.09747714285714
jdk  stats = count=2800000 sum=1176272936 min=200 max=640                avg=420.09747714285714
longStats time       = 14.03 ms
summarizingInt time  = 24.73 ms
```

The two collectors agree on every field — count, sum, min, max, and the derived average — which is
the correctness half of the proof. The timing gap (roughly 1.8×, this run) is **not** because
`summarizingInt` boxes anything — Verified Figures §7 already established it accumulates into a
plain `int[1]`/implicit primitive fields inside `IntSummaryStatistics`, so it is boxing-free too.
The gap here is dispatch overhead: our `longStats` accumulator is one direct array-index chain
with no intermediate object; `Collectors.summarizingInt`'s accumulator additionally calls
`stat.accept(value)` on an `IntSummaryStatistics` instance (a virtual method call through an
object reference) once per element, plus applies the caller's `ToIntFunction` boxing-adjacent
narrowing conversion from `long` to `int`. **Unverified:** the exact magnitude of this gap is
JIT- and run-dependent (see the escape-analysis section below for why this machine's JIT identity
matters); treat the ratio as illustrative of "extra indirection costs something", not as a portable
constant.

**The gotcha.** `summingInt`/`averagingInt` are a different story from `summarizingInt` for
overflow, and it is easy to conflate all three: per Verified Figures §7, `summingInt` truly
accumulates into an `int[1]` and **does overflow silently** — three additions of 1,000,000,000
through `summingInt` measured `-1294967296` against the correct `3000000000` — while
`averagingInt` and `summarizingInt`'s own sum field are safe (`long`-backed). This file's `long[]`
accumulator sidesteps the whole question by never narrowing to `int` in the first place, which is
the actual argument for reaching for domain amounts (already `long` minor units) as `long`
end-to-end rather than converting to `int` to satisfy a `ToIntFunction`-shaped collector.

> **Definition:** a boxing-free statistics collector accumulates into a fixed-size primitive
> array, mutated in place, so folding `m` elements allocates once (the array) rather than `m`
> times (one per intermediate immutable result).

**Diff vs the real one:**

| Axis | `longStats` (this file) | `Collectors.summarizingInt`/`IntSummaryStatistics` |
|---|---|---|
| Accumulator shape | raw `long[4]` | `IntSummaryStatistics` object; internally a `long count`, `long sum`, `int min`, `int max` — Verified Figures §7 |
| Overflow | none — `long` sum over `long` inputs | none in `summarizingInt`'s own sum (it's `long`); `summingInt` alone overflows, see gotcha |
| Min/max width | `long` | `int` — narrows the source if it was wider |
| Combiner | manual `min`/`max`/`+=` on the array | `IntSummaryStatistics.combine(other)`, same arithmetic, dispatched through a method |
| Thread safety | none needed — private accumulator until combine, standard collector contract | same |
| Serialization | `LongStats` is a plain record; not `Serializable` unless declared so | `IntSummaryStatistics` does **not** implement `Serializable` |
| Why the JDK bothers | `summarizingInt`/`summarizingLong`/`summarizingDouble` give count+sum+min+max+average in one pass with zero setup for the overwhelmingly common case; a hand-rolled `long[]` collector only earns its keep when the built-in's field types (`int` min/max, or wanting a custom fifth statistic) don't fit |

---

### The `CONCURRENT` characteristic and its three-condition fast path

**Mental model.** `CONCURRENT` is a promise from the collector author that the accumulator itself
is safe to share and mutate from many threads at once — a `ConcurrentHashMap`, not a private
`HashMap` per thread. When that promise is combined with an *unordered* fold, the stream pipeline
can skip the entire fork-join split-and-merge structure and instead just push every element,
directly, from whichever thread produced it, into one shared container.

**Why it exists.** The default parallel-collect path forks the source into ~`parallelism × 4`
leaf tasks (`LEAF_TARGET`, Verified Figures §2), lets each leaf fold its own private accumulator,
then merges leaf results pairwise up the fork-join tree via `combiner()` — `O(log(leaves))` merge
steps, each one copying or re-keying data. For a genuinely concurrent-safe container, all of that
merge machinery is pure overhead: every thread could have written straight into the same map from
the start.

**When to reach for it, and when not.** Declare `CONCURRENT` only when the accumulator type is
actually thread-safe for concurrent mutation from multiple threads with no external
synchronization — `ConcurrentHashMap`, not `HashMap` wrapped in `Collections.synchronizedMap`
(which would be thread-*safe* but serialize every write behind one lock, erasing the entire
point). Never declare `UNORDERED` unless the collector's result genuinely does not depend on
encounter order — a top-N or `groupingBy` result set is order-independent; a `joining` collector
is not, and declaring it `UNORDERED` anyway would be a lie that produces nondeterministic output.

**How it works.** `[PROVE]` `[SOURCE]` The exact check lives in `ReferencePipeline.collect`,
`jdk-21+35`, quoted verbatim:

```java
A container;
if (isParallel()
        && (collector.characteristics().contains(Collector.Characteristics.CONCURRENT))
        && (!isOrdered() || collector.characteristics().contains(Collector.Characteristics.UNORDERED))) {
    container = collector.supplier().get();
    BiConsumer<A, ? super P_OUT> accumulator = collector.accumulator();
    forEach(u -> accumulator.accept(container, u));
}
else {
    container = evaluate(ReduceOps.makeRef(collector));
}
return collector.characteristics().contains(Collector.Characteristics.IDENTITY_FINISH)
       ? (R) container
       : collector.finisher().apply(container);
```

Read line by line: `isParallel()` is the stream's own parallel flag — sequential streams never
take this branch, full stop. `collector.characteristics().contains(CONCURRENT)` is the collector's
promise. `!isOrdered() || collector.characteristics().contains(UNORDERED)` is the third condition,
and it is an **or**, not an **and**: either the *stream* has already dropped ordering (via
`.unordered()`, or because its source was inherently unordered, like a `HashSet`), or the
*collector* declares it doesn't care about order even if the stream does. If all three hold, the
`if` branch calls `supplier().get()` exactly **once**, total, and every element from every worker
thread is pushed into that single container via `forEach`, which itself runs in parallel — no
`combiner()` call anywhere in this branch. If any condition fails, control falls to the `else`
branch, `ReduceOps.makeRef(collector)`, which is the ordinary fork-join split/fold/merge path that
does call `combiner()`, once per merge.

**Diagram.** None assigned; the harness output below is the substitute — the same information a
diagram would carry (which path ran) shown as an observed count instead.

**A minimal concrete example.** A `CONCURRENT`+`UNORDERED` collector that groups withdrawal
transactions by rail into a `ConcurrentHashMap`, instrumented to count `combiner()` invocations and
record which threads ever touched the accumulator:

```java
static <T, K> Collector<T, ?, Map<K, List<T>>> concurrentGroupingBy(
        Function<T, K> classifier, CombinerCallCounter counter,
        boolean concurrentCharacteristic, boolean unorderedCharacteristic) {
    Supplier<Map<K, List<T>>> supplier = ConcurrentHashMap::new;
    BiConsumer<Map<K, List<T>>, T> accumulator = (map, t) -> {
        counter.threadsSeenInAccumulator.add(Thread.currentThread().getName());
        K key = classifier.apply(t);
        map.computeIfAbsent(key, k -> Collections.synchronizedList(new ArrayList<>())).add(t);
    };
    BinaryOperator<Map<K, List<T>>> combiner = (m1, m2) -> {
        counter.combinerCalls.incrementAndGet();
        m2.forEach((k, v) -> m1.computeIfAbsent(k, x -> Collections.synchronizedList(new ArrayList<>())).addAll(v));
        return m1;
    };
    EnumSet<Collector.Characteristics> cs = EnumSet.of(Collector.Characteristics.IDENTITY_FINISH);
    if (concurrentCharacteristic) cs.add(Collector.Characteristics.CONCURRENT);
    if (unorderedCharacteristic) cs.add(Collector.Characteristics.UNORDERED);
    return Collector.of(supplier, accumulator, combiner, cs.toArray(new Collector.Characteristics[0]));
}
```

`[PROVE]` all three conditions genuinely gate the fast path, run against 200,000 withdrawal
transactions, four combinations, on this machine (a 12-thread common-pool):

```
[sequential source, C+U collector]                              combinerCalls=0  threads=1  total=200000
[parallel source, plain (no C, no U) collector]                  combinerCalls=63 threads=12 total=200000
[parallel ORDERED source (ArrayList), C but not U collector]     combinerCalls=63 threads=12 total=200000
[parallel UNORDERED source + C + U collector]                    combinerCalls=0  threads=12 total=200000
```

Read the four rows against the three-part condition: row 1 fails condition 1 (`isParallel()` is
false for a sequential stream), so it never reaches the fast-path check at all — one thread, no
merging needed anyway. Row 2 fails condition 2 (no `CONCURRENT`) — 12 worker threads did real
work, and the fork-join tree needed 63 pairwise merges to combine their private accumulators. Row 3
is the one every explanation of this mechanism gets wrong by only stating two of the three
conditions: it **has** `CONCURRENT` and **is** parallel, and it *still* takes the slow path with 63
combiner calls, because the source (`ArrayList`) is encounter-ordered and the collector never
declared `UNORDERED` — condition 3 fails. Only row 4, with all three conditions satisfied
(`.unordered()` on the stream **and** both characteristics on the collector), shows
`combinerCalls=0` with 12 threads still doing the accumulation — proof that all 12 threads wrote
directly into one shared `ConcurrentHashMap`, exactly as the quoted source predicts.

**The gotcha.** Declaring `CONCURRENT` on a collector backed by a plain `HashMap` compiles, runs,
and corrupts data only under load — `HashMap`'s internal bucket-splitting during a resize is not
thread-safe, and the failure mode (a lost update, or in the worst case a corrupted bucket chain
that turns `get` into an infinite loop pre-Java-8's treeification, or silent data loss post-8) does
not show up on small inputs or on a machine with few cores, which is exactly the profile of a
laptop-only test suite.

> **Definition:** `CONCURRENT` plus an unordered fold (from either the stream or the collector)
> lets the parallel-collect path skip the fork-join merge tree entirely and accumulate every
> element from every thread directly into one shared container.

**Diff vs the real one — `Collectors.toConcurrentMap`/`groupingByConcurrent`:**

| Axis | `concurrentGroupingBy` (this file) | `Collectors.groupingByConcurrent` |
|---|---|---|
| Backing map | `ConcurrentHashMap` | `ConcurrentHashMap` (or caller-supplied concurrent map factory) |
| Bucket type | `Collections.synchronizedList` (extra lock per bucket) | JDK's real implementation merges into a `ConcurrentHashMap`-backed downstream using `Map.merge`/`compute`, which is itself lock-striped rather than one broad `synchronizedList` lock per key |
| Characteristics | `CONCURRENT`, `UNORDERED`, `IDENTITY_FINISH` — all opt-in via constructor flags here for the harness | `CONCURRENT`, `UNORDERED`, `IDENTITY_FINISH` always, unmodifiable set |
| Null policy | `NullPointerException` from `ConcurrentHashMap.computeIfAbsent` on a null key | same — `ConcurrentHashMap` forbids null keys and values everywhere in the JDK's version too |
| Ordering | intentionally discarded — this is the point | intentionally discarded |
| Why the JDK bothers | Groups over very large parallel streams without the fork-join merge cost proved above; the tradeoff is that the *values* still need per-key coordination (there the JDK is more careful about lock granularity than this file's illustrative `synchronizedList`) |

---

## MyOptional and the shared `EMPTY`

### The Optional family, before the details

| Type | Presence check | Holds | `Serializable` | Since |
|---|---|---|---|---|
| `MyOptional<T>` (this file) | `value != null` | any reference `T` | no | this file |
| `java.util.Optional<T>` | `value != null` | any reference `T` | no | Java 8 |
| `java.util.OptionalInt` | `isPresent` boolean | primitive `int` | no | Java 8 |
| `java.util.OptionalLong` | `isPresent` boolean | primitive `long` | no | Java 8 |
| `java.util.OptionalDouble` | `isPresent` boolean | primitive `double` | no | Java 8 |

`OptionalInt`/`OptionalLong`/`OptionalDouble` exist for exactly the reason `longStats` above uses a
`long[]` instead of a boxed record: `Optional<Integer>` boxes; `OptionalInt` does not. They are not
generic and share no interface with `Optional<T>` — there is no common `Optional` supertype in the
JDK, by design, since a shared interface would force either boxing at the call site or a fourth
type parameter nobody wants.

### `MyOptional<T>`, its shared `EMPTY`, and its null-handling contract

**Mental model.** `MyOptional<T>` is a box that is allowed to be empty — a wrapper distinguishing
"no client found for this lookup" from "found a client, and its value happens to be absent",
where the second sentence doesn't even parse, because a present `MyOptional` can never wrap `null`
itself. The box, not the value, is what "presence" means.

**Why it exists.** Before `Optional` (Java 8), "no value" was `null`, and `null` carries no
information about whether its absence was expected — a `ClientId lookupClient(...)` that returns
`null` documents nothing in its signature; a caller has to read the implementation or the Javadoc
to know whether a `null` return is a real possibility or a bug. `Optional<T>` moves that fact into
the type signature: `MyOptional<ClientId> lookupClient(...)` tells every caller, at compile time,
that absence is part of the contract.

**When to reach for it, and when not.** Reach for it as a **method return type** signalling "this
lookup can legitimately come back empty" — a client lookup by an unverified `ClientId`, say. Do
not reach for it as a field type (an `Optional`-typed field doubles the number of states an object
can be in for no benefit, since the field itself can still be `null` unless disciplined
constructors forbid it) and not as a method parameter (it forces every caller to wrap a value just
to call the method, when an overload or a `null`-check would do). This is not house style opinion —
it is literally the real `Optional`'s own Javadoc API note, quoted in the diff table below.

**How it works.** The shared `EMPTY` instance and the two factories:

```java
public final class MyOptional<T> {
    private static final MyOptional<?> EMPTY = new MyOptional<>(null);
    private final T value;
    private MyOptional(T value) { this.value = value; }

    @SuppressWarnings("unchecked")
    public static <T> MyOptional<T> empty() { return (MyOptional<T>) EMPTY; }

    public static <T> MyOptional<T> of(T value) {
        return new MyOptional<>(Objects.requireNonNull(value));
    }

    public static <T> MyOptional<T> ofNullable(T value) {
        return value == null ? empty() : new MyOptional<>(value);
    }
}
```

`[PROVE]` **`empty() == empty()`, every time, because there is exactly one `EMPTY` field and
`empty()` only ever casts and returns it — never constructs.** Run against both `MyOptional` and
the real `Optional`, plus a third case (a value filtered away rather than created empty
directly) to show the singleton survives every code path that produces "no value", not just the
obvious one:

```java
MyOptional<ClientId> e1 = MyOptional.empty();
MyOptional<ClientId> e2 = MyOptional.empty();
// e1 == e2 : true

Optional<ClientId> j1 = Optional.empty();
Optional<ClientId> j2 = Optional.empty();
// j1 == j2 : true

MyOptional<ClientId> e3 = MyOptional.of(new ClientId("C-1")).filter(c -> false);
// e3 == e1 : true  — filtering away a present value routes through the same empty() call
```

**The argument for why you must not depend on this identity anyway:** `==` happening to work is an
implementation detail, not a documented contract — nothing in `Optional`'s Javadoc promises
`empty() == empty()`, and both the real JDK and this file's `MyOptional` only deliver it because
`EMPTY` happens to be `static final`. A hypothetical future JDK release, or a value-based-class
migration under Project Valhalla (see the diff table below), could legally allocate a fresh empty
instance per call without breaking any documented contract, because `Optional.equals` — not `==` —
is the documented way to compare two `Optional`s, and `Optional` is explicitly annotated
`@jdk.internal.ValueBased`, which exists precisely to let the JVM warn about, and eventually
permit optimizing away, identity-sensitive operations (`==`, `synchronized`, identity hash) on
instances of the class. Code that does `if (result == Optional.empty())` instead of
`if (result.isEmpty())` is one JDK internals change away from a silent behavioural break, not a
compile error — the kind of bug that a full test suite still won't catch because the identity
happens to hold on every JDK anyone tests against today.

`[PROVE]` **`orElse` evaluates its argument eagerly; `orElseGet` does not**, proved with a
side-effect counter rather than asserted:

```java
int[] orElseCallCount = {0};
int[] orElseGetCallCount = {0};
MyOptional<ClientId> present = MyOptional.of(new ClientId("C-2"));

present.orElse(sideEffect(orElseCallCount, new ClientId("FALLBACK")));
// orElse: supplier-equivalent argument evaluated, count=1

present.orElseGet(() -> sideEffect(orElseGetCallCount, new ClientId("FALLBACK")));
// orElseGet: lambda body NOT evaluated when present, count=0
```

`orElse(T other)` takes a plain value — Java's evaluation rule for a method argument is "evaluate
before the call", so `sideEffect(...)` runs regardless of whether `present` actually needs the
fallback, which the count of `1` proves even though the value is discarded. `orElseGet(Supplier<?
extends T>)` instead takes a *function*, and the method body only calls `.get()` inside its own
`if (value == null)` branch — the count of `0` proves the lambda body itself never executed. On the
empty case both counts become `1`, because now the fallback path genuinely runs both ways:

```
on empty: orElse count=1 orElseGet count=1
```

**`[PROVE]` a null-returning mapper matched against the JDK's own `empty()` behaviour** — `map`
and `flatMap` disagree with each other, and this file's `MyOptional` reproduces the JDK's exact
disagreement rather than picking one rule for both:

```java
MyOptional<ClientId> mapNull = MyOptional.of(new ClientId("C-3")).map(c -> null);
// = MyOptional.empty (isEmpty=true)          — matches Optional.of(x).map(v -> null) exactly

MyOptional.of(new ClientId("C-4")).flatMap(c -> null);
// throws NullPointerException                — matches Optional.of(x).flatMap(v -> null) exactly
```

`map`'s contract is `return ofNullable(mapper.apply(value));` — the mapper is allowed to return
`null`, because `ofNullable` is the one function whose whole job is turning a `null` reference into
`empty()`. `flatMap`'s contract is different by design: the mapper must return an `Optional`
*itself*, not a `T`, so a `null` return means the mapper broke its own contract (it must return
`empty()`, never `null`, when it has nothing) — `Objects.requireNonNull(r)` enforces that
distinction with an explicit `NullPointerException` rather than silently downgrading a
programming error into an empty result.

**Diagram.** None assigned; the code and its measured output above are the substitute.

**The gotcha.** `filter`, `map`, and `flatMap` all check `isEmpty()` first and return `this` or
`empty()` **without calling the given function at all** when the box is already empty — so a
`filter`/`map` chain after an empty result is not merely "produces an empty result", it is "never
executes the lambda", which matters the moment that lambda has a side effect or a cost (a database
call disguised as a mapper is the classic version of this mistake).

> **Definition:** `MyOptional<T>` is an immutable, at-most-one-element container whose absence
> state is represented by a single shared instance, so that "no value" is a first-class type-level
> fact instead of an overloaded `null`.

**Diff vs the real one — `java.util.Optional`:**

| Axis | `MyOptional<T>` (this file) | `java.util.Optional<T>` |
|---|---|---|
| Value-based annotation | none (illustrative) | `@jdk.internal.ValueBased` — javadoc: "identity-sensitive operations (...) on instances of `Optional` (...) may have unpredictable results and should be avoided" |
| `Serializable` | no | no — deliberately, to discourage using it as a field |
| Primitive variants | none built | `OptionalInt`, `OptionalLong`, `OptionalDouble` — avoid boxing entirely, see the family table above |
| Intended-use API note | stated here in prose | stated in the actual Javadoc: "primarily intended for use as a method return type"; explicitly *not* recommended as a field type or a method parameter |
| `map` on `null`-returning mapper | returns `empty()`, proved above | returns `empty()` — identical, verified against the real class |
| `flatMap` on `null`-returning mapper | throws `NullPointerException`, proved above | throws `NullPointerException` — identical, verified against the real class |
| `EMPTY` identity | one `static final` instance, proved `==` | one `static final` instance, proved `==` — not a documented guarantee on either side |
| Valhalla trajectory | not applicable — illustrative type | `@ValueBased` is the JDK's own forward marker: a future flattened/identity-free `Optional` under Project Valhalla is the explicit long-term intent behind the annotation existing at all today |

**`[SOURCE]` fields quoted from `Optional`, `jdk-21+35`:** `private final T value;` — generic,
`final`, exactly this file's own field declaration; the class declares no `implements
Serializable` anywhere in its header, confirmed by inspection of the same source.

---

### Allocation cost of a five-`map` chain, with and without escape analysis

**Mental model.** Each `.map(...)` in a chain allocates a fresh wrapper — a new `MyOptional`
holding a new domain object — *unless* the JIT proves the wrapper never leaves the method it was
created in, in which case it can be **scalar-replaced**: broken into its individual fields, kept
in registers or on the stack, and never allocated on the heap at all.

**Why it exists as a cost, and why the JIT can sometimes make it disappear.** A five-`map` chain
inside a hot loop looks, at the bytecode level, like five `new MyOptional(...)` calls per
iteration. Escape analysis (part of C2, HotSpot's server compiler) proves, for a sufficiently
simple method, that none of those intermediate `MyOptional`/`ClientId` instances is stored in a
field, passed to an un-inlined method, or returned — they only ever flow into the *next* `map`
call in the same chain, which the JIT has also inlined. When every use site is visible and
inlined, the object can be scalar-replaced instead of allocated.

**When this matters, and when it does not.** It matters in a hot loop over millions of iterations —
exactly the allocation-count benchmark below. It does not matter for a chain called once per HTTP
request at ordinary request volumes; the JIT needs the method to run enough times (past C2's
compilation threshold) to even attempt escape analysis, and the GC cost of a few thousand
short-lived wrapper objects per second is not where a typical service's latency budget goes.

**How it works, measured rather than asserted.** The chain under test:

```java
static long runChain(int i) {
    ClientId id = new ClientId("C-" + (i % 1000));
    MyOptional<ClientId> chain = MyOptional.of(id)
            .map(c -> new ClientId(c.value() + "-a"))
            .map(c -> new ClientId(c.value() + "-b"))
            .map(c -> new ClientId(c.value() + "-c"))
            .map(c -> new ClientId(c.value() + "-d"))
            .map(c -> new ClientId(c.value() + "-e"));
    return chain.map(c -> c.value().length()).orElse(0);
}
```

measured with `com.sun.management.ThreadMXBean.getThreadAllocatedBytes`, 2,000,000 warm-up
iterations followed by 20,000,000 measured iterations, run on this machine's actual `java` binary:

```
=== C2 forced (-XX:-UseJVMCICompiler), escape analysis ON (default) ===
totalBytesAllocated = 3,504,000,000   bytesPerIteration = 175.2

=== C2 forced (-XX:-UseJVMCICompiler), escape analysis OFF (-XX:-DoEscapeAnalysis) ===
totalBytesAllocated = 10,544,000,000  bytesPerIteration = 527.2
```

**`[NUM]` the arithmetic:** `527.2 − 175.2 = 352.0` bytes eliminated per iteration by escape
analysis. Over the 20,000,000 measured iterations that is `352.0 × 20,000,000 = 7,040,000,000`
bytes, ≈ `7,040,000,000 / 1,073,741,824 ≈ 6.56 GiB` of heap churn — and therefore that many fewer
bytes a young-generation collector has to walk — avoided purely by the JIT proving the five
`MyOptional`/`ClientId` wrappers never escape `runChain`. A rough per-object cross-check: each
`MyOptional` is one header (12 bytes, compressed-oops default) plus one reference field, rounded up
to a 16-byte-aligned object size ≈ 16 bytes; six intermediate `MyOptional`s (the five `.map` results
plus the final one before `.orElse`) plus five intermediate `ClientId` records (header + one
`String` reference, also ≈ 16 bytes each) is roughly `11 × 16 = 176` bytes of *wrapper* overhead —
in the right order of magnitude for the measured 352-byte gap once alignment and the JVM's actual
object-header layout (not exactly 12+4 in every configuration) are accounted for; treat the
per-object breakdown as an illustrative cross-check, not an exact reconciliation.

**`[NUM]` `[VERSION-TRAP]`, and the one this benchmark surfaced by accident: which JIT is actually
running matters more than which JDK version does.** This machine's `java` is **Oracle GraalVM
25.0.1**, whose default top-tier JIT is the **Graal compiler** (via JVMCI), not HotSpot's C2.
Running the identical benchmark with *default* flags — no `-XX:-UseJVMCICompiler` — gives:

```
=== GraalVM default JIT, escape analysis flag ON  === bytesPerIteration = 179.4
=== GraalVM default JIT, escape analysis flag OFF === bytesPerIteration = 180.7
```

a **1.3-byte difference**, essentially noise, because `-XX:-DoEscapeAnalysis` is a **C2-specific**
flag — Graal has its own partial escape analysis with its own controls, and simply ignores a flag
that only means something to the compiler it replaced. Forcing `-XX:-UseJVMCICompiler` falls back
to genuine HotSpot C2, and only then does the classic 3×-class gap between EA-on and EA-off appear.
**Unverified:** the exact Graal-JIT allocation figures (~179–181 bytes/iteration either way) are
this machine's GraalVM 25.0.1 numbers, not a verified JDK 21 HotSpot figure; the packet's own
caution about running on JDK 25 applies doubly here, since the *vendor* of the JIT, not just the
version, changed the outcome. Anyone reproducing this on a stock Oracle/OpenJDK 21 build (real C2
by default, no JVMCI substitution) should expect the first pair of numbers (175.2 / 527.2), not the
second.

**Diagram.** None assigned; the four measured numbers above are the substitute.

**The gotcha.** "Escape analysis eliminates `Optional` allocations" is true only inside a hot,
fully-inlined method; the instant a `map` lambda is complex enough that C2 declines to inline it
(too large, megamorphic call site, or a virtual call the JIT can't devirtualize), escape analysis
loses visibility past that boundary and the wrapper allocates for real. The benchmark's chain
above is deliberately simple — five trivial one-line lambdas — precisely so C2's inliner has no
reason to give up; a chain doing real domain validation per step is not guaranteed the same
elimination.

> **Definition:** escape analysis lets the JIT skip heap allocation for an object whose entire
> lifetime is visible and inlined at compile time, which is why a chain of `Optional.map` calls
> can cost close to zero allocation in a hot loop despite looking, at the source level, like five
> `new` expressions per call.

---

## Pitfalls

### Assuming a broken `groupingBy` combiner only breaks on "big" data

**Wrong**

```java
BinaryOperator<Map<K, A>> combiner = (m1, m2) -> {
    m1.putAll(m2); // overwrites any key both maps already hold
    return m1;
};
```

On the ten-withdrawal sample above this silently drops whichever partial `"CARD"` bucket
`putAll` decided to overwrite — but only when the parallel split happens to divide `"CARD"`
entries across both halves, which for ten elements on a small common pool sometimes does not
happen at all, so the test passes. The bug is a function of *split shape*, not data size.

**Right**

```java
BinaryOperator<Map<K, A>> combiner = (m1, m2) -> {
    for (Map.Entry<K, A> e : m2.entrySet()) {
        m1.merge(e.getKey(), e.getValue(), downstreamCombiner);
    }
    return m1;
};
```

`merge` runs the *downstream's own combiner* on any key present in both maps instead of letting
one side clobber the other, which is correct regardless of how the fork-join split happened to
divide the input.

**Why people believe it:** `putAll` is the obvious, one-line answer to "combine two maps", and it
is *correct* when the two maps are guaranteed to have disjoint keys — which grouping collectors
never guarantee, because the classifier decides key membership, and nothing about a parallel split
respects classifier boundaries.

### Depending on `MyOptional.empty() == MyOptional.empty()`

**Wrong**

```java
if (lookupClient(id) == MyOptional.empty()) {
    requestQueue.enqueue(ClientLookupFailed.of(id));
}
```

Passes today, on this JDK, because `empty()` never constructs. It is not a language or library
guarantee, and a `filter`/`map` chain that produces "no value" through a code path this file did
not test could — in principle, on a future release — return a different empty instance.

**Right**

```java
if (lookupClient(id).isEmpty()) {
    requestQueue.enqueue(ClientLookupFailed.of(id));
}
```

`isEmpty()`/`isPresent()` are the documented contract; `==` is an accident of the current
implementation.

**Why people believe it:** the identity check *works*, every time, on every JDK anyone has ever
run it against — because `EMPTY` really is a single `static final` field on both this file's
`MyOptional` and the real `Optional`. "It has never failed" and "it is guaranteed never to fail"
are different claims, and `@jdk.internal.ValueBased`'s whole purpose is to flag exactly this gap.

### Treating `summingInt` and `summarizingInt` as the same overflow story

**Wrong**

```java
int total = ledgerEntries.stream()
        .collect(Collectors.summingInt(e -> (int) e.amountMinorUnits())); // silently wraps
```

Three additions of 1,000,000,000 through `summingInt` measured `-1294967296` against a correct
`3,000,000,000` on this machine — the accumulator genuinely is an `int[1]`.

**Right**

```java
long total = ledgerEntries.stream()
        .collect(Collectors.summingLong(LedgerEntry::amountMinorUnits));
```

or, if the full breakdown is wanted anyway, `summarizingInt`/`summarizingLong`, whose own `sum`
field is `long`-backed regardless of which one is called.

**Why people believe it:** `averagingInt`'s sum genuinely is safe (a `long[2]` accumulator, per
Verified Figures §7), and it is easy to assume its sibling `summingInt` shares the same internal
representation — the names suggest a matched pair, and only one half of the pair actually is.

## Cheat sheet

| Fact | Value |
|---|---|
| Five-function contract | `supplier`, `accumulator`, `combiner`, `finisher`, `characteristics` |
| `IDENTITY_FINISH` meaning | `A == R`; skip calling `finisher()`, unchecked-cast instead |
| `toMyList`/`Collectors.toList()` mutability | mutable `ArrayList`, unspecified but stable; `Stream.toList()` (Java 16) is unmodifiable |
| `groupingBy` combiner rule | `merge(key, value, downstreamCombiner)`, never `putAll` |
| `topN` complexity | `O(m log n)` time, `O(n)` space; combiner replays the smaller heap through the accumulator |
| `summingInt` overflow | yes — `int[1]` accumulator, silently wraps |
| `averagingInt`/`summarizingInt` overflow | no — `long`-backed sum |
| `CONCURRENT` fast-path conditions | `isParallel()` **and** collector `CONCURRENT` **and** (`!isOrdered()` **or** collector `UNORDERED`) |
| `CONCURRENT` fast path skips | every `combiner()` call — one shared container, `forEach` writes directly |
| `MyOptional`/`Optional` shared empty | one `static final EMPTY`; `==` works today, not a documented guarantee |
| `map(null-returning)` | returns `empty()` |
| `flatMap(null-returning)` | throws `NullPointerException` (mapper broke its own contract) |
| `orElse(x)` | argument evaluated eagerly, always |
| `orElseGet(fn)` | `fn.get()` called only when empty |
| `Optional` annotation | `@jdk.internal.ValueBased` |
| `Optional`/`OptionalInt`/`OptionalLong`/`OptionalDouble` | none share a common supertype |
| Escape analysis flag | `-XX:-DoEscapeAnalysis` is **C2-only**; GraalVM's default JIT ignores it |
| Measured EA effect (forced C2, this machine) | 175.2 B/iter (on) vs 527.2 B/iter (off) — a 352 B/iter, ≈6.56 GiB/20M-iterations gap |

## Self-test

**Q1.** Why does a hand-rolled collector need a correct `combiner()` even if it is only ever
called with `stream()`, never `parallelStream()`?

<details><summary>Answer</summary>

Nothing in the `Collector`/`MyCollector` type enforces sequential-only use — any caller can invoke
the same collector with a parallel stream, and an untested combiner is a latent bug that only
surfaces under parallel execution, which the author may never test. The contract requires an
associative combiner regardless of the author's intended usage, because the collector's type
signature promises correctness under both execution modes.

</details>

**Q2.** In `groupingByMy`'s finisher, why is `intermediate.replaceAll(...)` followed by an
unchecked cast to `Map<K, D>`, rather than building a brand-new map of type `Map<K, D>` from
scratch?

<details><summary>Answer</summary>

`replaceAll` mutates the existing `Map<K, A>` in place, replacing each value with its finished `D`
form while keeping the same map instance and its keys untouched — this avoids a second full-map
allocation and a second pass over every key. Because Java generics are erased, `Map<K, A>` and
`Map<K, D>` are the same runtime type once the values have been replaced, so the cast is safe in
practice even though the compiler cannot verify it — which is exactly why it needs
`@SuppressWarnings("unchecked")` rather than being expressible without a cast at all. This mirrors
the real `Collectors.groupingBy`'s own three-argument overload exactly.

</details>

**Q3.** A bounded top-N collector's `topN(3, comparator)` is run on a parallel stream. Walk
through what happens to elements that "lose" during the combiner step — are they discarded
correctly, and where?

<details><summary>Answer</summary>

Each leaf task first folds its own slice into a private, size-≤3 heap via the accumulator (leaf
elements that don't make the local top 3 are discarded there, immediately — the accumulator polls
and re-offers). When two leaves are combined, the smaller heap's elements are replayed one at a
time through the *same accumulator logic* against the larger heap: each candidate either displaces
the current minimum of the receiving heap (if it's bigger) or is discarded on the spot (if it's
not). No element is ever collected and re-sorted at the end except the final ≤3 survivors — the
discarding happens continuously, both within a leaf and during every combine step, which is what
keeps the whole operation `O(m log n)` instead of `O(m log m)`.

</details>

**Q4.** What specifically does `CONCURRENT` promise about the accumulator type `A`, and what
happens if that promise is false (say, `A` is a plain `HashMap`) but the characteristic is declared
anyway?

<details><summary>Answer</summary>

`CONCURRENT` promises that `A` is safe to mutate from multiple threads simultaneously with no
external synchronization — the pipeline will call `supplier().get()` exactly once and then invoke
`accumulator()` from many threads on that single shared instance. If `A` is actually a plain
`HashMap` (not thread-safe for concurrent structural modification), declaring `CONCURRENT` anyway
means multiple threads mutate the same `HashMap` concurrently without synchronization — a
data race that can lose updates silently or, depending on JDK version and load, corrupt the
internal bucket structure. It typically will not surface on small inputs or few cores, which is
why it survives into production.

</details>

**Q5.** Why does `MyOptional.of(x).map(v -> null)` return `empty()` while
`MyOptional.of(x).flatMap(v -> null)` throws `NullPointerException`, given that both take a
function and both check for `null`?

<details><summary>Answer</summary>

They check `null` in different places against different contracts. `map`'s mapper is a
`Function<T, U>` — it is contractually allowed to produce "no value" by returning `null`, and
`map` handles that by routing the result through `ofNullable`, which is the one function whose job
is converting a `null` reference into `empty()`. `flatMap`'s mapper is a
`Function<T, MyOptional<U>>` — it must already return an `Optional`-shaped result, including
`empty()` explicitly when it has nothing; a `null` return means the mapper itself is broken (it
returned no `Optional` at all, not an empty one), which `flatMap` treats as a caller error and
reports via `Objects.requireNonNull`, not as a legitimate "no value" outcome.

</details>

**Q6.** Explain, precisely, why `orElse(expensiveCall())` still invokes `expensiveCall()` even when
the `MyOptional` is present, but `orElseGet(() -> expensiveCall())` does not.

<details><summary>Answer</summary>

`orElse(T other)` takes an already-evaluated value of type `T` — by Java's method-argument
evaluation rule, the expression `expensiveCall()` is evaluated *before* the `orElse` call even
begins, regardless of what `orElse` does with the result internally. `orElseGet(Supplier<? extends
T>)` instead takes a *function reference* — the lambda `() -> expensiveCall()` is itself a cheap
object to construct, and `expensiveCall()` inside it only runs if `orElseGet`'s body actually calls
`.get()`, which its implementation only does inside the `if (value == null)` branch.

</details>

**Q7.** The escape-analysis benchmark measured a large discrepancy between "default GraalVM flags"
and "C2 forced via `-XX:-UseJVMCICompiler`". What does that discrepancy actually demonstrate about
interpreting JIT-flag-driven benchmarks in general?

<details><summary>Answer</summary>

It demonstrates that a JIT-control flag's effect is compiler-implementation-specific, not
JVM-specification-mandated: `-XX:-DoEscapeAnalysis` is documented behaviour for HotSpot's C2
compiler specifically, and a JVM distribution that substitutes a different top-tier JIT (GraalVM's
Graal compiler via JVMCI) is free to ignore a flag that only has meaning for the compiler it
replaced. Any benchmark that toggles a JIT flag and reports "no difference" needs to first confirm
which compiler actually produced the measured code, because "the flag did nothing" and "the
optimization made no difference" are different findings that look identical from the outside.

</details>

**Q8.** Why does the boxing-free `longStats` collector initialize its accumulator array to
`{0, 0, Long.MAX_VALUE, Long.MIN_VALUE}` rather than `{0, 0, 0, 0}`?

<details><summary>Answer</summary>

The min and max slots need identity values for their respective comparisons: any real accumulated
value must be able to replace the initial min (so it starts at the largest possible `long`,
guaranteeing the first real value is smaller) and replace the initial max (so it starts at the
smallest possible `long`, guaranteeing the first real value is larger). Initializing both to `0`
would silently corrupt the result for any dataset whose true minimum is positive (the min would
incorrectly stay `0`) or whose true maximum is negative (the max would incorrectly stay `0`).

</details>

**Q9.** In the `CONCURRENT` harness, why does the "parallel ORDERED source, `CONCURRENT` but not
`UNORDERED`" case still report 12 distinct thread names in `threadsSeenInAccumulator` even though
it took the slow (combiner-calling) path?

<details><summary>Answer</summary>

`threadsSeenInAccumulator` records which threads ever called `accumulator()`, and both the fast
path and the slow path call `accumulator()` from every worker thread that processes a chunk of the
source — the difference between the two paths is entirely about how the *results* get merged
afterward (directly into one shared container versus pairwise via `combiner()`), not about which
threads do the initial per-element folding. Twelve threads folding into twelve private
accumulators, then merging via 63 combiner calls, still touches the accumulator from all twelve
threads.

</details>

## Deferred

None.

## Open questions

- **Unverified:** the exact JDK release in which the `@jdk.internal.ValueBased` annotation itself
  (as opposed to the general "value-based class" documentation convention, present since Java 8's
  Javadoc for `Optional`) was added to `java.util.Optional`'s source. Settle by diffing
  `Optional.java` across `jdk-8`, `jdk-16-ga`, and `jdk-21+35` tags for the annotation's first
  appearance.
- **Unverified:** the precise magnitude of the `longStats` vs `Collectors.summarizingInt` timing
  gap (measured at ~1.8× on this run) as a portable figure — it is JIT-identity-dependent, per the
  escape-analysis section's finding that this machine's default JIT (GraalVM's Graal compiler) and
  a forced HotSpot C2 produce materially different numbers for adjacent allocation-sensitive
  benchmarks. Settle by re-running both benchmarks on a stock OpenJDK 21 HotSpot build with JFR
  allocation profiling attached, on dedicated (non-shared) hardware.
- **Unverified:** the per-object byte breakdown offered as a cross-check for the 352-byte-per-
  iteration escape-analysis gap (≈176 bytes of naive wrapper overhead against a measured 352) is an
  order-of-magnitude sanity check, not a reconciled accounting — the remainder is plausibly
  attributable to the intermediate `String` concatenation objects and object-header/alignment
  specifics this estimate did not itemize. Settle with an async-profiler or JFR allocation-by-type
  report over the same benchmark loop.

---

**Leaves covered:** 4.3.1–4.3.7, 4.4.1–4.4.6 (13 leaves)
**Leaves deferred:** none
**Diagrams included:** none (none assigned to this file)
**Target version:** Java 21 LTS
**Lines:** 1146
