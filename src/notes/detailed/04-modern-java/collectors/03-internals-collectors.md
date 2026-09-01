# 04 Modern Java — Collectors — INTERNALS (§3.6)

**Target version: Java 21 LTS.** | **Part 3 of 5** | [Index](../00-index.md)
Previous: [Collectors — in anger](02-in-anger.md) · Next: [`Optional` — basics](../optional/01-basics.md)

Part 2 showed what `toList()`, `groupingBy()` and `joining()` do. This part opens the box. Every
collector you called in anger is, underneath, one instance of the same tiny record —
`CollectorImpl` — holding five functions and a set of three enum flags. Once you can read that
record, every collector's behaviour stops being memorised trivia and becomes something you derive:
why `toSet()` doesn't preserve order, why `groupingBy`'s downstream sometimes needs an unchecked
cast, why summing `double`s costs more machinery than summing `int`s, and why `IDENTITY_FINISH`
is worth a whole enum constant of its own. All source in this file is quoted from
`java.util.stream.Collectors`, `java.util.stream.ReferencePipeline` and
`java.util.stream.AbstractTask` at the **jdk-21+35** tag, and every number is worked with the
one-8-core-box figures fixed across this note set (`availableProcessors() = 8`,
`commonPool parallelism = 7`, effective width `8`, `LEAF_TARGET = 28`).

---

## 1. `CollectorImpl` and the six pre-built characteristic sets

### Mental model

A `Collector<T, A, R>` is a recipe card, not a strategy object with behaviour of its own. The card
has five blanks — how to make an empty container (`supplier`), how to fold one element into it
(`accumulator`), how to merge two containers made independently (`combiner`), how to turn the
container into the answer (`finisher`) — plus a small stamp in the corner: a `Set<Characteristics>`
telling whoever runs the recipe which shortcuts are safe to take. `CollectorImpl` is the one class
in the JDK that actually holds a filled-in card; every `Collectors.toXxx()` method is a vending
machine that returns one, pre-filled for a specific job.

### Why it exists

Before Java 8, "collect into a list, grouped by department" was a hand-written loop: allocate a
`HashMap<K, List<V>>`, check-then-create the bucket, add the element. Every author reinvented the
check-then-create dance, and no two of them agreed on whether the result was safe to hand to a
parallel loop. `Collector` gives one interface any of these hand-rolled reductions can implement,
and `CollectorImpl` gives the JDK's own factory methods (`toList`, `groupingBy`, `joining`, …) one
concrete, uniform object to return, so `Stream.collect(Collector)` never needs to know which
factory produced the collector it was handed.

### When to reach for it, and when not

You almost never build a `CollectorImpl` directly — it isn't `public`, so code outside
`java.util.stream` cannot name the type. When you need a custom collector, you reach for
`Collector.of(supplier, accumulator, combiner, characteristics...)` (four functions, no finisher,
implying `IDENTITY_FINISH`) or the five-argument overload with an explicit finisher. Both build the
same shape of object — five functions plus a characteristics set — through a public factory rather
than the internal record. The sibling comparison that matters here is the **characteristics set
you attach**: get it wrong and you get a correctness bug, not a compile error, because
`Collectors.characteristics()` values are trusted by the framework without being re-checked at
runtime (see the gotcha below).

### How it works

The record, quoted verbatim:

```java
record CollectorImpl<T, A, R>(Supplier<A> supplier,
                              BiConsumer<A, T> accumulator,
                              BinaryOperator<A> combiner,
                              Function<A, R> finisher,
                              Set<Characteristics> characteristics
        ) implements Collector<T, A, R> {

    CollectorImpl(Supplier<A> supplier,
                  BiConsumer<A, T> accumulator,
                  BinaryOperator<A> combiner,
                  Set<Characteristics> characteristics) {
        this(supplier, accumulator, combiner, castingIdentity(), characteristics);
    }
}
```

Line by line: it is a `record`, not the "small private class" a lot of pre-2021 material
describes — records didn't exist before Java 16, and `Collectors.java` was rewritten onto one
after JEP 395 shipped, so any material describing a hand-written `private static final class
CollectorImpl` implementing `Collector` with five explicit fields and a constructor is describing
the pre-record shape; the fields and their meaning did not change, only the boilerplate. It has no
access modifier, so it is **package-private** — visible only inside `java.util.stream` — which is
exactly why `Collector.of` exists as the public escape hatch. The five record components are the
five collector functions plus `characteristics`. The second, four-argument constructor is the one
`toList()`, `toSet()` and every other `IDENTITY_FINISH` collector actually calls: it fills the
`finisher` slot with `castingIdentity()`,

```java
@SuppressWarnings("unchecked")
private static <I, R> Function<I, R> castingIdentity() {
    return i -> (R) i;
}
```

an unchecked identity cast from the accumulation type to the result type. That finisher is never
actually invoked for these collectors — §5 below shows exactly where the framework decides that —
but it exists so that every `CollectorImpl` instance still satisfies `Collector<T, A, R>`'s
contract of having a non-null `finisher()`.

The six characteristic sets, quoted verbatim:

```java
static final Set<Collector.Characteristics> CH_CONCURRENT_ID
        = Collections.unmodifiableSet(EnumSet.of(Collector.Characteristics.CONCURRENT,
                                                 Collector.Characteristics.UNORDERED,
                                                 Collector.Characteristics.IDENTITY_FINISH));
static final Set<Collector.Characteristics> CH_CONCURRENT_NOID
        = Collections.unmodifiableSet(EnumSet.of(Collector.Characteristics.CONCURRENT,
                                                 Collector.Characteristics.UNORDERED));
static final Set<Collector.Characteristics> CH_ID
        = Collections.unmodifiableSet(EnumSet.of(Collector.Characteristics.IDENTITY_FINISH));
static final Set<Collector.Characteristics> CH_UNORDERED_ID
        = Collections.unmodifiableSet(EnumSet.of(Collector.Characteristics.UNORDERED,
                                                 Collector.Characteristics.IDENTITY_FINISH));
static final Set<Collector.Characteristics> CH_NOID = Collections.emptySet();
static final Set<Collector.Characteristics> CH_UNORDERED_NOID
        = Collections.unmodifiableSet(EnumSet.of(Collector.Characteristics.UNORDERED));
```

Six constants, three independent booleans (`CONCURRENT`, `UNORDERED`, `IDENTITY_FINISH`), and the
JDK only ever needs six of the eight possible combinations — no collector in `Collectors` is
`CONCURRENT` without also being `UNORDERED` (a concurrent, order-preserving collector would defeat
the point of running unordered on shared state), so `CH_CONCURRENT_UNID` (concurrent, ordered) is
never built.

**D-143** — `CollectorImpl` and its pre-built characteristic sets

| Set | `CONCURRENT` | `UNORDERED` | `IDENTITY_FINISH` | Used by | What the framework does differently |
|---|---|---|---|---|---|
| `CH_CONCURRENT_ID` | yes | yes | yes | `toConcurrentMap(keyMapper, valueMapper)`; `groupingByConcurrent(classifier)` when the downstream is itself `IDENTITY_FINISH` | On a parallel, unordered pipeline: skip the fork-join combine tree entirely, share one container across worker threads (§5); on finish: return that container directly, no finisher call |
| `CH_CONCURRENT_NOID` | yes | yes | no | `toConcurrentMap(keyMapper, valueMapper, mergeFn)`; `groupingByConcurrent` when the downstream has a real finisher | Same shared-container fast path, but a finisher pass still runs once at the end, in place, on the single shared map |
| `CH_ID` | no | no | yes | `toList()`, `toCollection(factory)`, `toMap(keyMapper, valueMapper)`, `groupingBy` when the downstream is `IDENTITY_FINISH`, `partitioningBy` under the same condition | Encounter order is preserved through the combine tree; on finish, the accumulation container **is** the result — no finisher call |
| `CH_UNORDERED_ID` | no | yes | yes | `toSet()` | The terminal operation is free to combine sub-results in whatever order sub-tasks finish, not the order they were split in — cheaper parallel merging, no ordering guarantee on iteration; container returned directly |
| `CH_UNORDERED_NOID` | no | yes | no | `toUnmodifiableSet()` | Same unordered merge freedom, but the finisher still runs — here to wrap the working `HashSet` into an immutable `Set.of(...)` copy |
| `CH_NOID` | no | no | no | `joining()`, `summingInt/Long/Double`, `averagingInt/Long/Double`, `reducing(...)`, `toUnmodifiableList()`, `groupingBy`/`partitioningBy` when the downstream has a real finisher | Encounter order preserved through the combine tree; finisher always runs to convert the accumulation type `A` into the result type `R` |

### The example

```java
record CardDepositEvent(String depositId, String statusCode, BigDecimal amount) {}

// A custom collector built with the public factory, not CollectorImpl directly.
// UNORDERED is honest here: summing captured deposit amounts does not care what
// order the events arrive in.
Collector<CardDepositEvent, BigDecimal[], BigDecimal> capturedTotal = Collector.of(
        () -> new BigDecimal[] { BigDecimal.ZERO },
        (acc, event) -> {
            if (event.statusCode().equals("DEP-301 CAPTURED")) {
                acc[0] = acc[0].add(event.amount());
            }
        },
        (left, right) -> new BigDecimal[] { left[0].add(right[0]) },
        acc -> acc[0],
        Collector.Characteristics.UNORDERED);

List<CardDepositEvent> batch = List.of(
        new CardDepositEvent("DEP-9001", "DEP-301 CAPTURED", new BigDecimal("65.00")),
        new CardDepositEvent("DEP-9002", "DEP-090 DECLINED", new BigDecimal("40.00")),
        new CardDepositEvent("DEP-9003", "DEP-301 CAPTURED", new BigDecimal("72.50")));

BigDecimal total = batch.stream().collect(capturedTotal); // 137.50
```

This is a `CH_NOID`-shaped collector in every respect that matters — no `IDENTITY_FINISH` was
passed, so `Collector.of` builds an `EnumSet` containing only `UNORDERED` — it simply isn't one of
the six *named* JDK constants, because a user-defined collector never gets access to
`CH_UNORDERED_NOID` itself (package-private); it gets an equivalent `EnumSet` built fresh by the
`Collector.of` varargs overload. The framework does not care which object instance carries the
flags, only which `Characteristics` values are in the set.

### The gotcha

**Pitfall:** treating `Characteristics.CONCURRENT` as something the framework enforces rather than
something the collector author promises. `ReferencePipeline.collect` (walked in full in §5) reads
this flag and, when it is present alongside a parallel, unordered pipeline, hands **the same
container** to every worker thread's `accumulator` with no synchronization inserted by the
framework:

```java
container = collector.supplier().get();
BiConsumer<A, ? super P_OUT> accumulator = collector.accumulator();
forEach(u -> accumulator.accept(container, u));
```

If `supplier()` returns a plain `HashMap` and you tag the collector `CONCURRENT` anyway, you get a
silent data race, not an exception — the framework trusts the flag completely. This is exactly why
`toConcurrentMap`'s supplier is `ConcurrentHashMap::new` and never `HashMap::new`.

> **Definition:** `CollectorImpl` is the package-private record backing every built-in collector —
> five functions plus a `Set<Characteristics>` — and the six `CH_*` constants are the only
> combinations of `CONCURRENT`/`UNORDERED`/`IDENTITY_FINISH` the JDK's own collectors need.

---

## 2. `toList()`'s three functions and the O(n) combine tree

### Mental model

Sequentially, `collect(toList())` is a funnel: one `ArrayList`, one thread, one `add` per element.
In parallel, it is a merge tree: the source is split into leaf-sized chunks, each chunk becomes its
own small `ArrayList`, and then those lists are fused together two at a time, working up the tree,
until one list remains. The fusing step is not free — it is a real array copy, every time.

### Why it exists

`Collectors.toList()` replaces the pattern of `stream.forEach(list::add)`, which has no combiner
and therefore no parallel story at all — `forEach` on a shared, non-thread-safe `ArrayList` from a
parallel stream is a data race. Giving the accumulation an explicit `combiner` function is what
lets the fork-join framework split the source, run each half's accumulation independently on its
own private list, and then merge — safely, because each half never touches the other's container
until the combiner is called.

### When to reach for it, and when not

| Collector | Accumulation type | Characteristics | Mutability of result |
|---|---|---|---|
| `toList()` (Java 8) | `ArrayList<T>` | `CH_ID` | Mutable, unspecified concrete type by contract |
| `toUnmodifiableList()` (Java 10) | `ArrayList<T>` | `CH_NOID` | Immutable — finisher copies into a trusted array-backed list, rejects `null` elements |
| `Stream.toList()` (Java 16, a `Stream` method, not a `Collectors` factory) | n/a — implemented directly on the pipeline, not via `collect(Collector)` | n/a | Immutable, equivalent to `toUnmodifiableList()` for the caller's purposes, without importing `Collectors` |

Reach for plain `toList()` when the caller needs to mutate the result afterward (append,
`removeIf`, sort in place). Reach for `toUnmodifiableList()` or `Stream.toList()` — interchangeable
in Java 16+ — when the list is handed to code you don't control and you want the immutability
enforced rather than documented. Neither wins over the other on cost; the difference is purely the
guarantee, not the performance.

### How it works

```java
public static <T>
Collector<T, ?, List<T>> toList() {
    return new CollectorImpl<>(ArrayList::new, List::add,
                               (left, right) -> { left.addAll(right); return left; },
                               CH_ID);
}
```

Three functions: `ArrayList::new` builds an empty container; `List::add` is the accumulator, one
element at a time; the combiner is `(left, right) -> { left.addAll(right); return left; }` —
`right`'s elements are copied into `left`'s backing array (growing it if needed), and `left`,
now containing both halves, is what continues up the tree. `right` is discarded.

**[NUM] [PROVE]** `ArrayList.addAll(Collection)` costs `O(size of the argument)` — it grows the
backing array once if needed, then does one `System.arraycopy` of every element in `right` into
`left`. Take the syllabus's own working numbers: this note set fixes an 8-core box, so
`ForkJoinPool.commonPool()` has parallelism `7`, effective width `8` once the submitting thread
joins in, `LEAF_TARGET = 7 << 2 = 28`, and over the domain's **2,800,000 stake reservations**,
`suggestTargetSize` divides down to exactly `100,000` per leaf, giving **28 leaf tasks**.

The combine tree's depth is `⌈log₂(28)⌉ = 5` levels — not `log₂(n)`. That is the whole reason the
total combiner cost stays `O(n)` instead of `O(n log n)`: the tree's branching factor is fixed by
the number of *leaf tasks*, which top out at roughly four per processor core, never by the number
of *elements*. Walking the arithmetic: at the top level, one merge combines two ~1,400,000-element
halves — `right` contributes 1,400,000 copies. At the next level down, two merges each combine
~700,000-element halves — each contributes 700,000 copies, 1,400,000 total. Every level of a
balanced binary merge contributes the same total, `n / 2 = 1,400,000` copies, regardless of how far
down the tree it sits, because the two branches being merged are still, in aggregate, half the
elements under that subtree. Five levels, each costing `n / 2`:

```
total combiner copies ≈ 5 × (2,800,000 / 2) = 5 × 1,400,000 = 7,000,000
                       ≈ 2.5 × n
```

`O(n)` with a small constant factor set by the *tree depth*, `⌈log₂(leaf task count)⌉`, which is
bounded by the core count and does not grow with `n`. That constant-but-nonzero copy tax, stacked
on top of fork-join's own task-scheduling overhead, is exactly why `parallelStream().collect
(toList())` needs a large `n` before the parallel speed-up on the *accumulation* side outweighs
this copy cost on the *combine* side — for a stream of twenty stake reservations there is no
meaningful accumulation work to parallelize and the copy tax is pure loss.

No diagram is assigned to this concept — the mechanism is the arithmetic above, not a picture.

### The example

```java
record StakeReservation(String reservationId, BigDecimal stake) {}

static List<StakeReservation> loadStakeReservations(int count) {
    List<StakeReservation> reservations = new ArrayList<>(count);
    for (int i = 0; i < count; i++) {
        reservations.add(new StakeReservation("STK-" + i, new BigDecimal("4.20")));
    }
    return reservations;
}

public static void main(String[] args) {
    List<StakeReservation> reservations = loadStakeReservations(2_800_000);
    List<StakeReservation> collected = reservations.parallelStream()
            .collect(Collectors.toList());
    System.out.println(collected.size()); // 2800000
}
```

Twenty-eight leaf tasks each build their own 100,000-element `ArrayList` from
`ReserveStake`-shaped records, and the combine phase above is what stitches them back into one
list of 2.8 million before `collect` returns.

### The gotcha

**Pitfall:** believing `.parallelStream().collect(toList())` is a free win because "more cores
means faster." The wrong belief in code:

```java
// WRONG — falls for the "parallel is always faster" trap
List<String> depositIds = List.of("DEP-1", "DEP-2", "DEP-3", "DEP-4", "DEP-5")
        .parallelStream()
        .collect(Collectors.toList());
```

Five elements split across up to eight worker threads pays fork-join task submission overhead and
at least one combiner merge, for accumulation work that a single thread finishes before the second
thread has even started. **Right:** reserve `parallelStream()` for collections large enough that
the per-element accumulation work dwarfs the splitting and combining overhead — the domain's own
2.8 million-a-day stake reservation volume is the right order of magnitude to consider it; five
literal strings never are.

> **Definition:** `toList()`'s combiner is `left.addAll(right)` — an `O(size of right)` array copy
> per merge — and because the fork-join tree's depth is bounded by leaf-task count rather than
> element count, the total combiner cost across a parallel `collect` stays `O(n)`, just with a
> constant factor that only large `n` can amortize.

---

## 3. `groupingBy`'s `computeIfAbsent` and its unchecked-cast finisher

### Mental model

`groupingBy` is a mailroom clerk. For every parcel (element), the clerk asks the classifier which
pigeonhole it belongs in; if that pigeonhole doesn't have a box yet, the clerk fetches an empty one
from the downstream collector and labels it; either way, the parcel then goes through *that box's
own* intake procedure — the downstream accumulator — not a generic one.

### Why it exists

The single-argument `groupingBy(classifier)` (which is `groupingBy(classifier, toList())` under the
hood) replaces the loop every backend engineer has written by hand: `Map<K, List<V>> map = new
HashMap<>(); for (V v : source) { map.computeIfAbsent(classify(v), k -> new ArrayList<>()).add(v);
}`. The two- and three-argument overloads generalize the "what goes in the box" step to any
collector at all — summing, joining, nested `groupingBy` — and the "what kind of map" step to any
`Map` implementation, so the same mechanism produces a `Map<K, List<V>>`, a `Map<K, Double>`, or a
`TreeMap<K, Long>` from the identical classifier logic.

### When to reach for it, and when not

| Collector | Bucket count | Container | Sibling that wins instead |
|---|---|---|---|
| `groupingBy(classifier)` | Unbounded, one per distinct key | `HashMap<K, List<T>>` | `partitioningBy(predicate)` when the classification is genuinely boolean — it always allocates exactly two buckets, even if one is empty, avoiding a `HashMap` entirely |
| `groupingBy(classifier, downstream)` | Unbounded | `HashMap<K, D>` | `toMap(keyMapper, valueMapper)` when there is exactly one value per key and no aggregation — `groupingBy` with a `toList()` downstream that always has size one is a symptom this was the real intent |
| `groupingBy(classifier, mapFactory, downstream)` | Unbounded, ordered how `mapFactory` orders | Whatever `mapFactory` returns (`TreeMap::new` for sorted keys) | Plain `groupingBy` when default `HashMap` iteration order is acceptable — the `TreeMap` variant costs `O(log k)` per insert instead of `O(1)` amortized |

### How it works

The three-argument overload, quoted in full — the other two funnel into it:

```java
public static <T, K, D, A, M extends Map<K, D>>
Collector<T, ?, M> groupingBy(Function<? super T, ? extends K> classifier,
                              Supplier<M> mapFactory,
                              Collector<? super T, A, D> downstream) {
    Supplier<A> downstreamSupplier = downstream.supplier();
    BiConsumer<A, ? super T> downstreamAccumulator = downstream.accumulator();
    BiConsumer<Map<K, A>, T> accumulator = (m, t) -> {
        K key = Objects.requireNonNull(classifier.apply(t), "element cannot be mapped to a null key");
        A container = m.computeIfAbsent(key, k -> downstreamSupplier.get());
        downstreamAccumulator.accept(container, t);
    };
    BinaryOperator<Map<K, A>> merger = Collectors.<K, A, Map<K, A>>mapMerger(downstream.combiner());
    @SuppressWarnings("unchecked")
    Supplier<Map<K, A>> mangledFactory = (Supplier<Map<K, A>>) mapFactory;

    if (downstream.characteristics().contains(Collector.Characteristics.IDENTITY_FINISH)) {
        return new CollectorImpl<>(mangledFactory, accumulator, merger, CH_ID);
    }
    else {
        @SuppressWarnings("unchecked")
        Function<A, A> downstreamFinisher = (Function<A, A>) downstream.finisher();
        Function<Map<K, A>, M> finisher = intermediate -> {
            intermediate.replaceAll((k, v) -> downstreamFinisher.apply(v));
            @SuppressWarnings("unchecked")
            M castResult = (M) intermediate;
            return castResult;
        };
        return new CollectorImpl<>(mangledFactory, accumulator, merger, finisher, CH_NOID);
    }
}
```

Reading it top to bottom: `downstreamSupplier` and `downstreamAccumulator` are pulled out of the
downstream collector once, outside the per-element lambda, so every call to the outer accumulator
reuses the same references rather than re-fetching them. The outer `accumulator` is exactly the
mailroom clerk from the mental model: `Objects.requireNonNull` on the classified key (so a `null`
key throws immediately with a clear message, rather than silently landing in a `HashMap`'s
null-key bucket), `computeIfAbsent` to fetch-or-create the per-key container using the
**downstream's own supplier**, then hand the element to the **downstream's own accumulator**. This
is the mechanism for leaf 3.6.5: the `HashMap` itself only ever stores containers of type `A` — the
downstream's accumulation type — never the final result type `D`.

The merger wraps `downstream.combiner()` in `mapMerger`, which walks the right map's entries and
merges each into the left map by key, calling the downstream combiner whenever both maps already
have a bucket for the same key — this is what makes `groupingBy` itself parallel-safe even when its
downstream is a plain, non-thread-safe accumulator like `toList()`'s `ArrayList`.

The branch that matters for leaf 3.6.6 is the `if`. When the downstream is `IDENTITY_FINISH` (for
example, the default `toList()` downstream), `groupingBy` returns `CH_ID` and supplies **no
finisher at all** — it relies on the same mechanism §5 walks in full: `ReferencePipeline.collect`
checks `IDENTITY_FINISH` and, when it's present, returns the accumulation container directly,
never calling `finisher()`. Note that the outer `groupingBy` collector's `Map<K, A>` and its
declared result type `M extends Map<K, D>` are only the same object because, in this branch, `D`
and `A` are the same type — the downstream's finisher is itself an identity cast, so its container
type *is* its result type.

When the downstream is **not** `IDENTITY_FINISH` (for example, `groupingBy(classifier,
summingDouble(...))`, since `summingDouble` is `CH_NOID`), the outer collector must convert every
bucket from its accumulation type `A` (here, `double[]`) to its result type `D` (here, `Double`)
before the caller can see it. `intermediate.replaceAll((k, v) -> downstreamFinisher.apply(v))`
does that **in place** — the same `HashMap` object, same keys, but every value slot rewritten from
`A` to `D` by calling the downstream's own finisher on it — and then the whole `Map<K, A>` is
handed back through an unchecked cast to `M` (`Map<K, D>`, or a user-supplied `M` if a
`mapFactory` was given). The cast is unchecked because, at this point in the code, generics have
already erased: the compiler cannot verify at compile time that every value in the map really has
been rewritten to type `D` — it trusts that `replaceAll` above did it correctly, one line earlier,
in the same method. This is precisely why `A` and `R` are separate type parameters on `Collector<T,
A, R>` in the first place: `groupingBy`'s own accumulation type is `Map<K, A>` (buckets not yet
finished) but its result type is `M` (`Map<K, D>`, buckets finished) — two different shapes of the
same map, reconciled by one unchecked cast instead of by building a second map.

No diagram is assigned to this concept — the source walk above and the worked example below carry
the mechanism.

### The example

```java
record CardDepositEvent(String depositId, String statusCode, BigDecimal amount) {}

List<CardDepositEvent> cardDeposits = List.of(
        new CardDepositEvent("DEP-1001", "DEP-301 CAPTURED", new BigDecimal("65.00")),
        new CardDepositEvent("DEP-1002", "DEP-301 CAPTURED", new BigDecimal("58.40")),
        new CardDepositEvent("DEP-1003", "DEP-090 DECLINED", new BigDecimal("30.00")));

// downstream is summingDouble — CH_NOID — so the finisher branch above runs,
// and the unchecked cast rewrites double[] buckets into Double buckets in place
Map<String, Double> totalByStatus = cardDeposits.stream()
        .collect(Collectors.groupingBy(
                CardDepositEvent::statusCode,
                Collectors.summingDouble(event -> event.amount().doubleValue())));
// {"DEP-301 CAPTURED"=123.4, "DEP-090 DECLINED"=30.0}

// downstream is the default toList() — CH_ID — so the IDENTITY_FINISH branch
// runs instead: the outer collector never calls a finisher at all
Map<String, List<CardDepositEvent>> byStatus = cardDeposits.stream()
        .collect(Collectors.groupingBy(CardDepositEvent::statusCode));
```

### The gotcha

**Pitfall:** assuming the `Map` `groupingBy` hands back is immutable, or that its iteration order
matches insertion order.

**Wrong**

```java
Map<String, List<CardDepositEvent>> byStatus = cardDeposits.stream()
        .collect(Collectors.groupingBy(CardDepositEvent::statusCode));
byStatus.put("DEP-999 SYNTHETIC", List.of()); // "should fail, it's a collector result"
for (String status : byStatus.keySet()) { /* "should be insertion order" */ }
```

Both assumptions are wrong for the default overload: the map returned is a plain, mutable
`HashMap` — `put` succeeds silently — and `HashMap` iteration order is a function of key hash
codes and bucket layout, not insertion order.

**Right**

```java
Map<String, List<CardDepositEvent>> byStatus = cardDeposits.stream()
        .collect(Collectors.groupingBy(
                CardDepositEvent::statusCode,
                TreeMap::new,          // explicit mapFactory for a defined order
                Collectors.toList()));
Map<String, List<CardDepositEvent>> immutableByStatus =
        Collections.unmodifiableMap(byStatus); // wrap explicitly if immutability matters
```

**Why people believe it:** `Collectors.toUnmodifiableList()` and `toUnmodifiableSet()` exist and
*are* immutable, so it's an easy generalization to assume every `Collectors` factory returns
something read-only. `groupingBy` never had an unmodifiable-map counterpart added to `Collectors`
itself.

> **Definition:** `groupingBy` builds one `HashMap` (or whatever `mapFactory` supplies), populates
> it with `computeIfAbsent` using the downstream's own supplier and accumulator, and — only when
> the downstream isn't already `IDENTITY_FINISH` — rewrites every bucket from the downstream's
> accumulation type to its result type in place, via `Map.replaceAll` and one unchecked cast.

---

## 4. Kahan compensation in `summingDouble`/`averagingDouble`, and why `summingInt` needs none

### Mental model

`summingDouble` doesn't trust a single running total. It keeps a second slot alongside it, a tiny
running IOU: every time a `double` addition silently drops some low-order bits to rounding, the
lost amount is computed and written into the IOU slot instead of vanishing, and it's paid back
into the total once, at the very end. `summingInt`, by contrast, keeps no such ledger — for
integers there is nothing to lose to rounding, only something to overflow.

### Why it exists

`double` addition is not associative. Summing many values of similar magnitude — the domain's own
95,000 card deposits, each roughly 65 — one at a time in a naive loop accumulates rounding error at
every step, because each partial sum has already lost precision relative to the true mathematical
total. Kahan (later refined by Neumaier) summation tracks that per-step loss explicitly and adds it
back, bounding the total error to roughly one machine epsilon regardless of how many terms are
summed, instead of letting it grow with `n`.

### When to reach for it, and when not

| Collector | Accumulator array | Compensation | Safe from | Not safe from |
|---|---|---|---|---|
| `summingInt` | `new int[1]` | none | rounding (integers are exact) | **silent overflow** past `Integer.MAX_VALUE` |
| `summingLong` | `new long[1]` | none | rounding; overflow up to `Long.MAX_VALUE` | overflow past `Long.MAX_VALUE`, in practice never hit by any figure in this domain |
| `summingDouble` | `new double[3]` | Kahan–Neumaier | accumulated rounding error | exactness — a `double` is still a binary floating-point approximation of a decimal amount |
| `averagingInt`/`averagingLong` | `new long[2]` | none | rounding; overflow (accumulates into a `long` sum regardless of the mapper's return type) | nothing new — dividing a `long` sum by a `long` count is exact arithmetic followed by one unavoidable `double` division |
| `averagingDouble` | `new double[4]` | Kahan–Neumaier | accumulated rounding error | exactness, same as `summingDouble` |
| `Collectors.reducing(BigDecimal.ZERO, Money::amount, BigDecimal::add)` | `BigDecimal[1]` | not needed — `BigDecimal` is exact decimal arithmetic | both rounding and overflow | nothing, at the cost of allocation per add and no fused compensation trick to speed it up |

In this domain, money is modelled as `Money(BigDecimal amount, Currency currency)` specifically so
none of `summingInt`/`summingDouble`/`averagingDouble` is the right tool for a real ledger total —
`BigDecimal` addition through `reducing` or a hand-rolled accumulator is. `summingDouble` earns its
place here as the thing you reach for when the value is genuinely a measurement (a latency in
milliseconds, a rate) rather than currency, and floating drift, not exactness, is the only concern.
`[X-REF 03]` The general mechanics of IEEE-754 double representation, ULP, and rounding modes are
guide 03's (Java core) territory in full; the paragraph above is everything you need to answer
"why does `summingDouble` bother with three doubles instead of one" without leaving this page.

### How it works

```java
public static <T> Collector<T, ?, Double>
summingDouble(ToDoubleFunction<? super T> mapper) {
    /*
     * In the arrays allocated for the collect operation, index 0
     * holds the high-order bits of the running sum, index 1 holds
     * the low-order bits of the sum computed via compensated
     * summation, and index 2 holds the simple sum used to compute
     * the proper result if the stream contains infinite values of
     * the same sign.
     */
    return new CollectorImpl<>(
            () -> new double[3],
            (a, t) -> { double val = mapper.applyAsDouble(t);
                        sumWithCompensation(a, val);
                        a[2] += val;},
            (a, b) -> { sumWithCompensation(a, b[0]);
                        a[2] += b[2];
                        // Subtract compensation bits
                        return sumWithCompensation(a, -b[1]); },
            a -> computeFinalSum(a),
            CH_NOID);
}

static double[] sumWithCompensation(double[] intermediateSum, double value) {
    double tmp = value - intermediateSum[1];
    double sum = intermediateSum[0];
    double velvel = sum + tmp; // Little wolf of rounding error
    intermediateSum[1] = (velvel - sum) - tmp;
    intermediateSum[0] = velvel;
    return intermediateSum;
}

static double computeFinalSum(double[] summands) {
    // Final sum with better error bounds subtract second summand as it is negated
    double tmp = summands[0] - summands[1];
    double simpleSum = summands[summands.length - 1];
    if (Double.isNaN(tmp) && Double.isInfinite(simpleSum))
        return simpleSum;
    else
        return tmp;
}
```

The three-element array's slots, per the JDK's own comment: `a[0]` is the running high-order sum;
`a[1]` is the running compensation (the JDK's variable name for it inside `sumWithCompensation`
is `intermediateSum[1]`, colloquially "`velvel`'s little brother" — the comment on that line
literally reads `// Little wolf of rounding error`); `a[2]` is a plain, uncompensated running sum
kept purely as a fallback.

`sumWithCompensation` does the Kahan–Neumaier step: `tmp = value - intermediateSum[1]` first
subtracts off whatever was owed from the last step; `sum + tmp` computes the new running total
(`velvel`); then `(velvel - sum) - tmp` recovers exactly what got lost to rounding in that
addition, algebraically — if the addition had been exact, `velvel - sum` would equal `tmp`
precisely and the new compensation would be zero — and stores it back into `a[1]` for the next
call to subtract off. `computeFinalSum` does the payback: `summands[0] - summands[1]` (note the
subtraction — the compensation is stored negated relative to the correction it represents) is the
compensated answer; the `isNaN`/`isInfinite` check exists purely for the edge case where the
stream contains same-signed infinities, in which case compensated arithmetic can spuriously produce
`NaN` and the plain `a[2]` fallback is the honest answer instead.

The combiner mirrors the same trick across two partial sums: fold `b`'s high-order sum in via
`sumWithCompensation`, add the simple sums, then subtract `b`'s own compensation term
(`sumWithCompensation(a, -b[1])`) so a partial sum computed on one fork-join branch doesn't lose
its accumulated correction when merged into another branch's.

![D-144 — Kahan compensated summation inside `summingDouble`](../diagrams/D-144-kahan-compensated-summation-inside.svg)
**D-144** — Kahan compensated summation inside `summingDouble`

**[NUM] [PROVE]** Run against 95,000 card deposits with amounts distributed like the domain's real
figures (average value 65, cents varying), on this machine (`javac --release 21`, deterministic
seed so the run reproduces):

```
count           = 95000
naive total     = 6175441.639999975
compensated sum = 6175441.64
difference      = 2.421438694000244E-8
averagingDouble = 65.00464884210525
```

The naive loop (`double total = 0; for (double d : deposits) total += d;`) and
`Collectors.summingDouble` start from the same 95,000 values and land about `2.4 × 10⁻⁸` apart —
tiny at this `n`, but the naive total's error is a function of the summation order and grows with
more terms and more magnitude spread, while the compensated total's error stays bounded by roughly
one machine epsilon regardless of `n`. `averagingDouble` lands at `65.0046…`, matching the domain's
own "avg value 65" figure for card deposits.

By contrast, run three additions of one billion each through both `summingInt` and `summingLong`:

```
summingInt  : -1294967296
summingLong : 3000000000
```

`summingInt` accumulates into `new int[1]` — a plain `int`, no compensation array, nothing to
compensate for because integer addition has no rounding to lose. What it has instead is
**exactly `IntStream.sum()`'s overflow trap**: three additions of `1,000,000,000` overflow a
32-bit `int` and wrap to a negative number, silently, with no exception. `summingLong` avoids it
here only because `3,000,000,000` still fits in a `long`; it has the identical trap one order of
magnitude further out. `averagingInt` and `averagingLong`, by contrast, are genuinely safe from
this specific failure at realistic volumes, because both accumulate their running sum into
`new long[2]` regardless of the mapper's declared return type — summing `int`s but storing the
sum as a `long`.

### The example

```java
record CardDepositEvent(String depositId, BigDecimal amount) {}

static List<CardDepositEvent> loadCardDeposits(int count) {
    List<CardDepositEvent> deposits = new ArrayList<>(count);
    long seed = 42;
    for (int i = 0; i < count; i++) {
        seed = seed * 6364136223846793005L + 1442695040888963407L;
        BigDecimal cents = BigDecimal.valueOf((Math.abs(seed) % 4000) / 100.0);
        deposits.add(new CardDepositEvent("DEP-" + i, new BigDecimal("45.00").add(cents)));
    }
    return deposits;
}

public static void main(String[] args) {
    List<CardDepositEvent> deposits = loadCardDeposits(95_000);

    double compensatedTotal = deposits.stream()
            .collect(Collectors.summingDouble(event -> event.amount().doubleValue()));

    double naiveTotal = 0.0;
    for (CardDepositEvent event : deposits) {
        naiveTotal += event.amount().doubleValue();
    }

    System.out.println("naive:       " + naiveTotal);
    System.out.println("compensated: " + compensatedTotal);
}
```

### The gotcha

**Pitfall:** assuming `summingInt` is "the safe one" because it looks simpler than
`summingDouble`'s three-element array.

**Wrong**

```java
// WRONG — silently wraps to a negative number well before any realistic
// deposit-volume figure looks alarming on paper
int totalMinorUnits = threeBillionCentsSplitAcrossDeposits.stream()
        .collect(Collectors.summingInt(cents -> cents));
```

**Right**

```java
long totalMinorUnits = threeBillionCentsSplitAcrossDeposits.stream()
        .collect(Collectors.summingLong(cents -> (long) cents));
// or, when exactness matters more than raw throughput, BigDecimal via reducing()
```

**Why people believe it:** `summingDouble`'s Kahan machinery is visibly more complicated than
`summingInt`'s one-line accumulator, so it reads as "the one the JDK authors had to work harder to
get right" — implying the plain `int` version needed no such care. It didn't need compensation
care; it still needed range care, and got none, because `int[1]` is exactly as unguarded as a raw
`int total = 0` loop.

> **Definition:** `summingDouble`/`averagingDouble` carry Kahan–Neumaier compensated summation in
> a `double[3]`/`double[4]` accumulator to bound floating-point rounding error independent of `n`;
> `summingInt`/`averagingInt` need no such compensation because integer addition doesn't round —
> but `summingInt`'s `int[1]` accumulator inherits `int` overflow exactly as `IntStream.sum()`
> does, while `averagingInt`'s `long[2]` accumulator does not.

---

## 5. Why `IDENTITY_FINISH` matters — and `joining()`'s combiner cost along the way

### Mental model

Every collector produces a working container first and a finished result second — sometimes the
same object wearing a different declared type, sometimes genuinely two different objects built one
from the other. `IDENTITY_FINISH` is the framework's way of knowing, before it does any work,
whether it can skip the second step entirely and hand the container straight back.

### Why it exists

Without the flag, every `collect` would need to call `finisher()` unconditionally — for `toList()`,
that would mean calling `castingIdentity()`'s `i -> (R) i` lambda on every single `collect` call,
purely to satisfy a uniform code path. That's a cheap call, but it's still a virtual dispatch and a
function-object allocation avoided at zero cost by checking one flag first. For collectors whose
container legitimately differs from their result — `toUnmodifiableList()`, `summingDouble()` — the
finisher call is not optional, so the flag also has to be something the framework trusts rather
than something it can infer from the types alone (`Function<A, R>` doesn't tell you at compile time
whether `A` and `R` are the same type).

### When to reach for it, and when not

This isn't a choice a caller makes — it's a property of whichever collector you pick. The sibling
comparison is `toSet()` (`CH_UNORDERED_ID` — container returned directly) against
`toUnmodifiableSet()` (`CH_UNORDERED_NOID` — finisher runs to wrap the working `HashSet` in an
immutable copy): identical accumulation logic, differing only in whether the last mile is skipped.

### How it works

The decision point is not inside any individual collector — it's one shared piece of code in
`ReferencePipeline.collect`, quoted in full:

```java
@Override
@SuppressWarnings("unchecked")
public final <R, A> R collect(Collector<? super P_OUT, A, R> collector) {
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
}
```

Two independent decisions, back to back. The `if` decides **how the container gets built**: a
parallel, unordered-or-order-irrelevant pipeline with a `CONCURRENT` collector skips the
fork-join combine tree completely and instead shares one container across every worker thread's
`forEach` call (this is the CONCURRENT fast path from §1's table — `combiner()` is never even
invoked in this branch). Every other case — sequential, or parallel-but-not-concurrent — goes
through `ReduceOps.makeRef(collector)`, which is the ordinary split/accumulate/combine tree walked
in §2.

The last three lines are leaf 3.6.10 in full: whichever way `container` got built, the framework
checks `IDENTITY_FINISH` exactly once, and either casts `container` straight to `R` — an unchecked
cast the compiler accepts because `IDENTITY_FINISH` is documented (not enforced by the type system)
to mean `A` and `R` are the same type at runtime — or calls `collector.finisher().apply(container)`
to actually transform it. **The saving is not calling a cheap function** — it's skipping a full
pass over the container in every collector whose finisher does real work: `toUnmodifiableList()`'s
finisher copies every element into a new backing array; `groupingBy`'s non-identity finisher (§3)
calls `Map.replaceAll` over every bucket; `summingDouble`'s finisher (§4) does one final
subtraction. `IDENTITY_FINISH` is the difference between "container is the answer" and "walk the
container once more to build the answer."

![D-145 — `IDENTITY_FINISH` skips a whole pass](../diagrams/D-145-identity-finish-skips-whole.svg)
**D-145** — `IDENTITY_FINISH` skips a whole pass

**[NUM]** Over the domain's 95,000 card deposits, collecting into a `toUnmodifiableList()` (no
`IDENTITY_FINISH`) walks the 95,000-element working list twice: once during accumulation (each
`add`), once during the finisher's copy into the trusted immutable array. Collecting the same
elements into a plain `toList()` (`IDENTITY_FINISH`) walks it once — the working `ArrayList` is
what the caller receives. That is one full 95,000-element pass saved per call, not a
micro-optimization on a handful of elements.

**[PROVE] [NUM]** `joining()`'s combiner shares `toList()`'s shape of cost, worth proving here
because it closes out the last uncovered leaf. Quoted:

```java
public static Collector<CharSequence, ?, String> joining() {
    return new CollectorImpl<CharSequence, StringBuilder, String>(
            StringBuilder::new, StringBuilder::append,
            (r1, r2) -> { r1.append(r2); return r1; },
            StringBuilder::toString, CH_NOID);
}
```

`StringBuilder.append(CharSequence)` on the combine step copies every character of `r2`'s buffer
into `r1`'s backing `char[]`, exactly the same `O(size of the right argument)` shape as
`ArrayList.addAll` — and by the identical tree-depth argument worked out in §2 (fixed depth,
bounded by leaf-task count, not element count), the total combiner cost across a full parallel
`collect(joining())` is the same `O(n)` with a small constant, not `O(n log n)`. `joining()` is
`CH_NOID`, though, not `CH_ID` — its finisher, `StringBuilder::toString`, does real work
(`String`'s own character-array copy out of the `StringBuilder`), so it pays the "one more pass"
cost that `toList()` does not.

### The example

```java
List<String> capturedStatuses = List.of(
        "DEP-301 CAPTURED", "BDP-301 CAPTURED", "AA-801 ACTIVATED");

// toSet(): CH_UNORDERED_ID — the working HashSet is returned directly
Set<String> distinctStatuses = capturedStatuses.stream().collect(Collectors.toSet());

// toUnmodifiableSet(): CH_UNORDERED_NOID — the finisher wraps a fresh, immutable copy
Set<String> immutableStatuses = capturedStatuses.stream()
        .collect(Collectors.toUnmodifiableSet());

// joining(): CH_NOID — combiner cost mirrors toList()'s; finisher does one more pass
String inClause = capturedStatuses.stream()
        .map(status -> "'" + status + "'")
        .collect(Collectors.joining(", ", "(", ")"));
// "('DEP-301 CAPTURED', 'BDP-301 CAPTURED', 'AA-801 ACTIVATED')"
```

### The gotcha

**Pitfall:** assuming a collector's `IDENTITY_FINISH` flag is a promise about the *type* the
caller sees, rather than about internal container reuse. Both `toList()`'s `List<T>` and
`toUnmodifiableList()`'s `List<T>` are declared identically at the call site — the flag makes no
difference to the code you write, only to how many passes the framework makes internally. Reading
the flag off `Collector.characteristics()` at runtime, rather than off the declared return type,
is the only reliable way to know which behaviour you're getting; it is not visible in a method
signature.

> **Definition:** `IDENTITY_FINISH` tells `ReferencePipeline.collect` that the accumulation
> container already **is** the result, letting it skip the finisher call — and, for every
> collector whose finisher does real work (a copy, an in-place rewrite, an arithmetic correction),
> that skip is a full extra pass over the container saved, not a trivial one.

---

## Pitfalls

### Assuming `.parallelStream().collect(toList())` is always faster

**Wrong**

```java
List<String> depositIds = List.of("DEP-1", "DEP-2", "DEP-3", "DEP-4", "DEP-5")
        .parallelStream()
        .collect(Collectors.toList());
```

**Right**

```java
List<String> depositIds = List.of("DEP-1", "DEP-2", "DEP-3", "DEP-4", "DEP-5")
        .stream() // sequential — no split, no fork-join tree, no combiner cost
        .collect(Collectors.toList());
```

**Why people believe it:** "parallel" reads as a strict performance upgrade over "sequential," and
most teaching material demonstrates `parallelStream()` on collections large enough that the
combine-tree tax (§2) is genuinely amortized, never on the five-element case where it dominates.

### Assuming `groupingBy`'s result `Map` is unmodifiable or insertion-ordered

**Wrong**

```java
Map<String, List<CardDepositEvent>> byStatus = cardDeposits.stream()
        .collect(Collectors.groupingBy(CardDepositEvent::statusCode));
byStatus.put("DEP-999 SYNTHETIC", List.of());
```

**Right**

```java
Map<String, List<CardDepositEvent>> byStatus = cardDeposits.stream()
        .collect(Collectors.groupingBy(
                CardDepositEvent::statusCode, TreeMap::new, Collectors.toList()));
Map<String, List<CardDepositEvent>> immutableByStatus = Collections.unmodifiableMap(byStatus);
```

**Why people believe it:** `toUnmodifiableList()`/`toUnmodifiableSet()` exist and generalize badly
in the reader's head to "every `Collectors` factory is immutable now."

### Assuming `summingInt` is exempt from `IntStream.sum()`'s overflow trap

**Wrong**

```java
int totalCentsToday = cardDeposits.stream()
        .collect(Collectors.summingInt(event -> event.amount().movePointRight(2).intValueExact()));
```

**Right**

```java
long totalCentsToday = cardDeposits.stream()
        .collect(Collectors.summingLong(event -> event.amount().movePointRight(2).longValueExact()));
```

**Why people believe it:** `summingDouble`'s visibly elaborate three-`double` compensation
machinery creates an impression that "the JDK authors thought hard about summing correctness here,"
which readers over-generalize to every `summing*` collector, including the plain `int[1]` one that
received no such treatment because it solves a different problem.

### Treating `Characteristics.CONCURRENT` as framework-enforced rather than author-promised

**Wrong**

```java
Collector<CardDepositEvent, HashMap<String, BigDecimal>, HashMap<String, BigDecimal>> unsafe =
        Collector.of(HashMap::new,
                (map, event) -> map.merge(event.statusCode(), event.amount(), BigDecimal::add),
                (left, right) -> { left.putAll(right); return left; },
                Collector.Characteristics.CONCURRENT, Collector.Characteristics.UNORDERED);
```

**Right**

```java
Collector<CardDepositEvent, ConcurrentHashMap<String, BigDecimal>, ConcurrentHashMap<String, BigDecimal>> safe =
        Collector.of(ConcurrentHashMap::new,
                (map, event) -> map.merge(event.statusCode(), event.amount(), BigDecimal::add),
                (left, right) -> { left.putAll(right); return left; },
                Collector.Characteristics.CONCURRENT, Collector.Characteristics.UNORDERED);
```

**Why people believe it:** the enum constant is named `CONCURRENT`, which reads as "the framework
makes this concurrent" rather than its actual meaning, "this collector's `supplier()` already
returns something safe for concurrent, unsynchronized use — I am telling the framework it may skip
the combine tree."

## Cheat sheet

| Fact | Value / shape |
|---|---|
| `CollectorImpl` | Package-private `record`, five components: `supplier`, `accumulator`, `combiner`, `finisher`, `characteristics` |
| Public equivalent | `Collector.of(supplier, accumulator, combiner, characteristics...)` (4-arg, implies `IDENTITY_FINISH`) or the 5-arg overload with an explicit finisher |
| `CH_ID` | `{IDENTITY_FINISH}` — `toList`, `toCollection`, `toMap(2-arg)`, `groupingBy`/`partitioningBy` when downstream is identity-finish |
| `CH_NOID` | `{}` — `joining`, all `summing*`/`averaging*`, `reducing`, `toUnmodifiableList`, `groupingBy`/`partitioningBy` with a real downstream finisher |
| `CH_UNORDERED_ID` | `{UNORDERED, IDENTITY_FINISH}` — `toSet` |
| `CH_UNORDERED_NOID` | `{UNORDERED}` — `toUnmodifiableSet` |
| `CH_CONCURRENT_ID` | `{CONCURRENT, UNORDERED, IDENTITY_FINISH}` — `toConcurrentMap(2-arg)`, `groupingByConcurrent` identity-finish |
| `CH_CONCURRENT_NOID` | `{CONCURRENT, UNORDERED}` — `toConcurrentMap(4-arg)`, `groupingByConcurrent` with a real finisher |
| `toList()`'s three functions | `ArrayList::new`, `List::add`, `(l, r) -> { l.addAll(r); return l; }` |
| Combine-tree depth | `⌈log₂(leaf task count)⌉`, bounded by core count, **not** `log₂(n)` — this is why total combiner cost stays `O(n)` |
| `groupingBy` container | `HashMap` (or `mapFactory`'s map) of `K` → downstream's accumulation type `A`, via `computeIfAbsent` |
| `groupingBy`'s unchecked cast | Only when downstream isn't identity-finish: `Map.replaceAll` rewrites every value `A → D` in place, then `(M) intermediate` |
| `summingInt`/`summingLong` accumulator | `int[1]` / `long[1]` — no compensation, `summingInt` **inherits `int` overflow** |
| `summingDouble` accumulator | `double[3]`: `[0]` running sum, `[1]` Kahan compensation, `[2]` uncompensated fallback for `NaN`/`Infinity` |
| `averagingInt`/`averagingLong` accumulator | `long[2]`: sum, count — safe from `summingInt`'s overflow trap because the sum slot is a `long` |
| `averagingDouble` accumulator | `double[4]`: compensated sum, compensation, count, uncompensated fallback |
| `IDENTITY_FINISH` mechanism | `ReferencePipeline.collect`: `characteristics().contains(IDENTITY_FINISH) ? (R) container : finisher().apply(container)` |
| `CONCURRENT` fast path | Parallel **and** `CONCURRENT` **and** (unordered pipeline or `UNORDERED` collector) ⇒ shared container via `forEach`, combiner never called |
| `joining()`'s combiner | `StringBuilder.append` — `O(size of right)` per merge, same `O(n)` tree-total shape as `toList()` |

## Self-test

**Q1.** `CollectorImpl` is described in some older material as "a small private class." What is it
actually, in Java 21, and why does the difference matter for who can construct one?

<details><summary>Answer</summary>

It is a package-private `record` with five components (`supplier`, `accumulator`, `combiner`,
`finisher`, `characteristics`). The pre-record shape (a hand-written class with the same five
fields) is what pre-2016 material describes; `Collectors.java` moved onto a record once records
shipped in Java 16, without changing the fields' meaning. Being package-private, not `private`,
still means code outside `java.util.stream` cannot name or construct the type directly — which is
why `Collector.of(...)` exists as the public factory for user-defined collectors, building the same
shape of object through a different, public constructor path.

</details>

**Q2.** Name the six pre-built characteristic sets and, for each, whether it includes
`IDENTITY_FINISH`.

<details><summary>Answer</summary>

`CH_CONCURRENT_ID` (yes), `CH_CONCURRENT_NOID` (no), `CH_ID` (yes), `CH_UNORDERED_ID` (yes),
`CH_UNORDERED_NOID` (no), `CH_NOID` (no). Three of the six carry `IDENTITY_FINISH`; the "ID"/"NOID"
suffix in each constant's name is exactly this flag.

</details>

**Q3.** Why does a parallel `collect(toList())` over 2.8 million elements cost `O(n)` total
combiner work rather than `O(n log n)`, given that each individual `addAll` call is
`O(size of right)`?

<details><summary>Answer</summary>

Because the fork-join combine tree's depth is bounded by the number of *leaf tasks*
(`⌈log₂(leaf task count)⌉`), and leaf task count is capped by `LEAF_TARGET`
(`commonPool parallelism << 2`) — a constant tied to core count, not to `n`. Over 2.8 million
stake reservations on the fixed 8-core box this note set uses, that's 28 leaf tasks and 5 tree
levels. Each level's merges collectively copy `n / 2` elements regardless of which level it is
(the two branches being merged still sum to half the elements under that subtree), so total cost
is `(tree depth) × (n / 2)` — a constant multiplier on `n`, not a `log₂(n)` multiplier, because the
tree never gets deeper as `n` grows past the leaf-task threshold; it only gets wider at the leaves.

</details>

**Q4.** `groupingBy(classifier, summingDouble(mapper))`'s outer collector ends up performing an
unchecked cast from `Map<K, A>` to `M`. What guarantees, at the point that cast happens, that it is
actually safe?

<details><summary>Answer</summary>

The line immediately before it: `intermediate.replaceAll((k, v) -> downstreamFinisher.apply(v))`
has already rewritten every value in the map from the downstream's accumulation type `A`
(`double[]` for `summingDouble`) to its result type `D` (`Double`), in place, on the same `Map`
object. By the time the cast executes, every value really is a `D`, so the cast is safe in
practice — but the compiler cannot verify this itself because generics are erased, which is why
the cast still needs `@SuppressWarnings("unchecked")` even though the surrounding logic makes it
correct.

</details>

**Q5.** Why does `summingInt` need no Kahan compensation, and why is that not the same thing as
being safe to use on a large volume counter?

<details><summary>Answer</summary>

It needs no compensation because integer addition doesn't lose precision to rounding the way
floating-point addition does — there's nothing for a compensation term to recover. But
`summingInt` accumulates into a plain `int[1]`, which silently overflows past
`Integer.MAX_VALUE` exactly as `IntStream.sum()` does; three additions of one billion produce
`-1294967296` on this machine, not an exception. "No compensation needed" is a statement about
rounding, not about range — those are two independent failure modes, and `summingInt` is immune
to only one of them.

</details>

**Q6.** What does `IDENTITY_FINISH` actually let `ReferencePipeline.collect` skip, mechanically?

<details><summary>Answer</summary>

One call to `collector.finisher().apply(container)`. For collectors whose finisher does real
work — `toUnmodifiableList()` copying into a trusted array, `groupingBy`'s non-identity branch
calling `Map.replaceAll` over every bucket, `summingDouble`'s final Kahan subtraction — that one
skipped call is a full extra pass over the accumulated data, not a trivial function invocation.
For `IDENTITY_FINISH` collectors, `collect` instead does an unchecked cast, `(R) container`,
trusting that the collector's own contract guarantees `A` and `R` are the same runtime type.

</details>

**Q7.** A collector is tagged `CONCURRENT` and `UNORDERED` but its `supplier()` returns a plain
`HashMap`. What actually goes wrong, and where does the failure surface?

<details><summary>Answer</summary>

Nothing throws. `ReferencePipeline.collect` sees `isParallel() && CONCURRENT && (!isOrdered() ||
UNORDERED)`, takes the shared-container branch, and calls the same `HashMap` instance's
`accumulator` from every worker thread via `forEach`, with no synchronization inserted by the
framework — the flag is a promise from the collector author, not something the framework verifies.
The failure surfaces later and intermittently, as `HashMap`'s well-known concurrent-modification
corruption (lost updates, or in the worst case an infinite loop from a corrupted bucket during
resize), not as an immediate, attributable exception at the `collect` call site.

</details>

**Q8.** `joining()`'s combiner and `toList()`'s combiner share the same big-O shape. What is it,
and what is the one difference between the two collectors that changes their total work?

<details><summary>Answer</summary>

Both combiners are `O(size of the right argument)` per merge (`StringBuilder.append` copying
characters versus `ArrayList.addAll` copying references), and both therefore total `O(n)` across
a parallel collect's fixed-depth combine tree, by the same leaf-task-bounded-depth argument.
The difference is `IDENTITY_FINISH`: `toList()` has it (`CH_ID`) and returns its working
`ArrayList` directly, while `joining()` doesn't (`CH_NOID`) and pays one additional full pass —
`StringBuilder::toString`'s own character-array copy — that `toList()` skips entirely.

</details>

## Deferred

None.

## Open questions

- **Unverified:** whether `AbstractPipeline`'s `IllegalStateException` message strings
  (`MSG_STREAM_LINKED`/`MSG_CONSUMED`, covered in the previous internals file) interact with this
  file's `CONCURRENT` fast path in any version-specific way beyond what's stated here — not
  exercised in this file's worked examples, and outside this file's leaf set. Settle by re-reading
  `ReferencePipeline.collect`'s call to `forEach` alongside `AbstractPipeline.evaluate` at the
  jdk-21+35 tag if the question becomes load-bearing elsewhere.

---

**Leaves covered:** 3.6.1–3.6.10 (10 leaves)
**Leaves deferred:** none
**Diagrams included:** D-143, D-144, D-145
**Target version:** Java 21 LTS
**Lines:** 1104
