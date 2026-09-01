# 04 Modern Java — Collectors — BASICS (§1.10)

**Target version: Java 21 LTS.** | **Part 1 of 5** | [Index](../00-index.md)
Previous: [Streams — internals parallel execution](../streams/10-internals-parallel-execution.md) · Next: [Collectors — basics b](01-basics-b.md)

## Where this fits

Every terminal operation you have used so far — `forEach`, `count`, `reduce`, `toArray` — hands
back either nothing, a primitive, or an array. `collect(Collector)` is the terminal operation that
hands back an arbitrary mutable result: a `List`, a `Map`, a `String`, a running statistic, or a
value built by folding a downstream collector into another one. The mechanism underneath is always
the same fold with a mutable container, no matter what shape the result takes. `Collectors` is the
factory class that manufactures ready-made `Collector` instances for the shapes you need over and
over — grouping 95,000 card deposits by rail, building a lookup of `ClientId` to their most recent
`Money` balance, summing 2.8 million stake amounts — so that you almost never hand-write a
`Collector` yourself.

### The family, before the details

Thirty distinct static factory method names live on `java.util.stream.Collectors` in Java 21.
Grouping and partitioning (`groupingBy`, `groupingByConcurrent`, `partitioningBy`, `teeing`) are
covered in the next file in this set (`01-basics-b.md`); this file owns the other twenty-six —
the ones that turn a stream directly into a collection, a map, a string, or a statistic, plus the
four downstream adapters (`mapping`, `filtering`, `flatMapping`, `collectingAndThen`) that reshape
what a collector receives or returns.

**D-040** below is the map before the streets: every factory this file and its sibling cover, in
one table, so that when a numbered leaf mentions "the concurrent sibling" or "the unmodifiable
variant" you already know where it sits in the family.

| Factory | Version added | Result type | Mutability | Null policy | Characteristics | Parallel behaviour | Trap |
|---|---|---|---|---|---|---|---|
| `toList()` | 16 | `List<T>` (currently `ArrayList`) | Mutable, unspecified | Nulls allowed | `IDENTITY_FINISH` | Combiner concatenates | Casting the result to a concrete type — §1.10.5 |
| `toUnmodifiableList()` | 10 | `List<T>` | Immutable | **Nulls rejected**, `NullPointerException` | `IDENTITY_FINISH` | Combiner concatenates then wraps | Confusing with `List.copyOf` semantics |
| `toSet()` | 8 | `Set<T>` (currently `HashSet`) | Mutable, unspecified | Nulls allowed | `UNORDERED`, `IDENTITY_FINISH` | Combiner merges sets | No iteration-order guarantee |
| `toUnmodifiableSet()` | 10 | `Set<T>` | Immutable | Nulls rejected | `UNORDERED`, `IDENTITY_FINISH` | Combiner merges then wraps | Same as above, plus null rejection |
| `toCollection(Supplier)` | 8 | Caller-chosen | Whatever the supplier builds | Whatever the target collection allows | `IDENTITY_FINISH` | Combiner calls `addAll` | Supplier must build a **new** instance each call |
| `toMap(k,v)` | 8 | `Map<K,V>` (currently `HashMap`) | Mutable, unspecified | **Key or value null → `NullPointerException`** | `IDENTITY_FINISH` | Combiner calls `putAll` | Duplicate key → `IllegalStateException` — §1.10.7/1.10.8 |
| `toMap(k,v,merge)` | 8 | `Map<K,V>` | Mutable, unspecified | Null value still throws | `IDENTITY_FINISH` | Combiner calls `putAll` | Merge function silently hides data loss if written carelessly |
| `toMap(k,v,merge,mapFactory)` | 8 | Caller-chosen `Map` | Whatever the factory builds | Depends on target map | `IDENTITY_FINISH` | Combiner calls `putAll` | Factory must build a **new** instance each call |
| `toConcurrentMap(k,v)` | 8 | `ConcurrentMap<K,V>` (currently `ConcurrentHashMap`) | Mutable, thread-safe | **`ConcurrentHashMap` forbids null keys and values outright** | `CONCURRENT`, `UNORDERED`, `IDENTITY_FINISH` | True concurrent accumulation, no combiner needed | Iteration order is meaningless even by accident |
| `toConcurrentMap(k,v,merge)` | 8 | `ConcurrentMap<K,V>` | Mutable, thread-safe | Same | Same three | Same | Same |
| `toConcurrentMap(k,v,merge,mapFactory)` | 8 | Caller-chosen `ConcurrentMap` | Depends | Depends | Same three | Same | Factory must return a genuinely concurrent map |
| `toUnmodifiableMap(k,v)` | 10 | `Map<K,V>` | Immutable | Nulls rejected | `IDENTITY_FINISH` | Combiner then wraps | Duplicate key still throws |
| `toUnmodifiableMap(k,v,merge)` | 10 | `Map<K,V>` | Immutable | Nulls rejected | `IDENTITY_FINISH` | Combiner then wraps | Same |
| `joining()` | 8 | `String` | Immutable | Element `toString()` must not be null-unsafe | `IDENTITY_FINISH` | Combiner concatenates `StringBuilder`s | O(n²) risk if hand-rolled instead — not here |
| `joining(delim)` | 8 | `String` | Immutable | Same | `IDENTITY_FINISH` | Same | Delimiter appears between elements only |
| `joining(delim,prefix,suffix)` | 8 | `String` | Immutable | Same | `IDENTITY_FINISH` | Same | Prefix/suffix appear exactly once regardless of element count |
| `counting()` | 8 | `Long` | Immutable value | N/A | `IDENTITY_FINISH` | Combiner adds | Returns `Long`, not `long` — unboxing cost |
| `summingInt` | 8 | `Integer` | Immutable value | N/A | `IDENTITY_FINISH` | Combiner adds | **Silently overflows** — §1.10.12 |
| `summingLong` | 8 | `Long` | Immutable value | N/A | `IDENTITY_FINISH` | Combiner adds | Can still overflow at extreme scale, just later |
| `summingDouble` | 8 | `Double` | Immutable value | N/A | `IDENTITY_FINISH` | Combiner merges three-slot state | Kahan-compensated, not naive — §1.10.12 |
| `averagingInt` | 8 | `Double` | Immutable value | N/A | `IDENTITY_FINISH` | Combiner adds sum and count | Returns `Double` even for an `int` source |
| `averagingLong` | 8 | `Double` | Immutable value | N/A | `IDENTITY_FINISH` | Same | Same |
| `averagingDouble` | 8 | `Double` | Immutable value | N/A | `IDENTITY_FINISH` | Combiner merges Kahan state | Kahan-compensated — §1.10.12 |
| `summarizingInt` | 8 | `IntSummaryStatistics` | Mutable accumulator, effectively single-use | N/A | `IDENTITY_FINISH` | Combiner merges via `combine()` | One pass gets min/max/sum/avg/count together |
| `summarizingLong` | 8 | `LongSummaryStatistics` | Same | N/A | `IDENTITY_FINISH` | Same | Same |
| `summarizingDouble` | 8 | `DoubleSummaryStatistics` | Same | N/A | `IDENTITY_FINISH` | Same | Internally Kahan-compensated too |
| `minBy(cmp)` | 8 | `Optional<T>` | Immutable value | Empty stream → `Optional.empty()`, never null | `IDENTITY_FINISH` | Combiner picks the smaller | Empty-stream case is easy to forget |
| `maxBy(cmp)` | 8 | `Optional<T>` | Immutable value | Same | `IDENTITY_FINISH` | Combiner picks the larger | Same |
| `reducing(op)` | 8 | `Optional<T>` | Immutable value | Same as `minBy`/`maxBy` | `IDENTITY_FINISH` | Combiner applies `op` | Rarely the clearest choice — §1.10.14 |
| `reducing(identity,op)` | 8 | `T` | Immutable value | Depends on `identity` | `IDENTITY_FINISH` | Combiner applies `op` | No `Optional` wrapping, so an empty stream silently returns `identity` |
| `reducing(identity,mapper,op)` | 8 | `U` | Immutable value | Depends | `IDENTITY_FINISH` | Combiner applies `op` | Easy to confuse with `map(mapper).reduce(...)` |
| `mapping(fn,downstream)` | 8 | Whatever `downstream` returns | Whatever `downstream` returns | Delegates to `downstream` | Delegates | Delegates | Applying `fn` too early loses information needed downstream |
| `filtering(pred,downstream)` | **9** | Whatever `downstream` returns | Delegates | Delegates | Delegates | Delegates | Filtering *inside* a `groupingBy` keeps empty groups; filtering the stream first does not — §1.10.15 |
| `flatMapping(fn,downstream)` | **9** | Whatever `downstream` returns | Delegates | Delegates | Delegates | Delegates | Only needed as a *downstream* — stream-level work still uses `Stream.flatMap` |
| `collectingAndThen(downstream,finisher)` | 8 | Whatever `finisher` returns | Whatever `finisher` returns | Delegates | **Strips `IDENTITY_FINISH`** if present | Delegates | Cannot be used to build a `CONCURRENT` collector — the finisher forces a single-threaded step |

That table is 30 rows only if you count `groupingBy`, `groupingByConcurrent`, `partitioningBy` and
`teeing` — this file's sibling covers those four; the 26 rows above are this file's. The syllabus
figure for the whole class is **30 distinct factory method names across 54 overloads** in Java 21;
independent re-counting against the Java 21 javadoc during this file's research pass corroborated
the 30 names exactly (grouping the above 26 with the sibling file's `groupingBy`,
`groupingByConcurrent`, `partitioningBy`, `teeing`) but returned an inconsistent overload count on
a second pass — see **Unverified** at the end of §1.10.3 below and the `## Open questions` section.

---

### The `Collector<T, A, R>` contract

**Mental model.** A `Collector` is a recipe for a mutable, single-threaded (or thread-confined-per-
chunk) fold, packaged as five functions plus a small set of flags. Picture a worker at a table with
an empty tray (`supplier()`), a set of instructions for placing one item onto the tray
(`accumulator()`), a rule for merging two trays into one when two workers have been folding in
parallel (`combiner()`), and a rule for turning the finished tray into the thing you actually asked
for (`finisher()`). The `characteristics()` set tells the runtime shortcuts it is allowed to take —
skip the finisher, ignore encounter order, or run several workers against one shared tray instead
of many trays that get merged. `collect(Collector)` does nothing except drive exactly this protocol;
every named factory on `Collectors` is a pre-built instance of these five functions.

**Why it exists.** Before `Collector`, turning a stream (or, pre-Java-8, a loop) into a `List` or a
`Map` meant a hand-written accumulation: declare a mutable container outside the loop, mutate it
inside, and hope nobody reordered the two. `Stream.reduce` handles *immutable* folds cleanly — each
step returns a new value — but immutable accumulation into a `List` is `O(n²)` if done naively
(`list = concat(list, newElement)` copies every time) and awkward if done carefully (accumulating
into a persistent data structure the JDK does not ship). `Collector` exists to make *mutable*
reduction — accumulate into one container, mutating it in place — a first-class, composable,
parallel-safe operation instead of a manual side effect smuggled through `forEach`.

**When to reach for it, and when not.** Reach for a named `Collectors` factory whenever the shape
you want (a `List`, a `Map`, a `String`, a statistic) already has one — which is true for the
overwhelming majority of real code. Write a custom `Collector` (via `Collector.of(...)`) only when
none of the thirty names, combined with `mapping`/`filtering`/`flatMapping`/`collectingAndThen` as
downstream adapters, produces the shape you need — custom collectors are rare enough in application
code that seeing one in a review is worth a raised eyebrow. Reach for `Stream.reduce` instead of a
custom `Collector` when the result is a single immutable value with no intermediate mutable state
(§1.10.14 covers exactly this choice for `reducing`).

**How it works.** The interface, from `java.util.stream.Collector`:

```java
public interface Collector<T, A, R> {
    Supplier<A> supplier();
    BiConsumer<A, T> accumulator();
    BinaryOperator<A> combiner();
    Function<A, R> finisher();
    Set<Characteristics> characteristics();

    enum Characteristics {
        CONCURRENT,
        UNORDERED,
        IDENTITY_FINISH
    }
}
```

Three type parameters: `T` is the stream's element type, `A` is the mutable accumulation type (the
"tray" — often package-private, like the `int[1]` inside `summingInt`), `R` is the final result
type handed back to the caller. Reading the five methods in the order the runtime actually calls
them, for a **sequential** stream:

1. `supplier().get()` is called exactly once, producing one instance of `A`.
2. `accumulator().accept(container, element)` is called once per stream element, folding it into
   the same container instance returned by the supplier.
3. `combiner()` is **not called at all** on a purely sequential source with no split — there is
   only ever one container.
4. `finisher().apply(container)` is called exactly once at the end, unless `IDENTITY_FINISH` is
   present, in which case the runtime performs an unchecked cast of `A` to `R` and never calls
   `finisher()` at all — this is the one legal case where `A` and `R` are actually the same type at
   runtime and the finisher is allowed to be `Function.identity()`.

For a **parallel** stream, the spliterator splits the source into sub-ranges; each sub-range gets
its own `supplier()`-created container, folded independently by `accumulator()` on its own thread —
this is the step that requires the container to genuinely be thread-confined per sub-range, never
shared. The `ForkJoin` merge phase then calls `combiner()` pairwise to fold sub-results together,
finally applying `finisher()` once at the root. This is exactly the four-frame shape below.

**Insight:** `IDENTITY_FINISH` is not a convenience flag, it is a type-system escape hatch. Without
it, `finisher()` would be mandatory and every collector would need to allocate a second object at
the end even when the accumulator already *is* the result — as it is for `toList()`, where `A` and
`R` are both (in practice) `ArrayList<T>`.

The three `Characteristics` values, and what each one licenses:

| Characteristic | What it licenses | Example |
|---|---|---|
| `CONCURRENT` | The **same** accumulator instance may be shared and mutated by multiple threads without a combine step, provided the source is `UNORDERED` or the collector doesn't care about order | `toConcurrentMap` backed by `ConcurrentHashMap` |
| `UNORDERED` | The collector's result does not depend on encounter order, so the runtime may process elements in any order it finds convenient | `toSet()`, `groupingByConcurrent` |
| `IDENTITY_FINISH` | `finisher()` is `Function.identity()` and may be skipped — the accumulator's final state **is** the result, unchecked-cast from `A` to `R` | `toList()`, `toMap()`, `counting()` |

![D-039 — The `Collector` contract's five functions](../diagrams/D-039a-collector-contract-s-five.svg)
**D-039** — The `Collector` contract's five functions (frame 1 of 4: `supplier()`)

The scenario the diagram walks: `deposits.stream().collect(groupingBy(Deposit::rail,
counting()))` over a mixed stream of card and bank deposits. Frame 1 shows `supplier()` being
called — once for the outer `groupingBy` map container, and once per distinct rail key the first
time that key is seen, for the downstream `counting()` collector's own accumulator.

![D-039 — The `Collector` contract's five functions](../diagrams/D-039b-collector-contract-s-five.svg)
**D-039** — The `Collector` contract's five functions (frame 2 of 4: `accumulator()`)

Frame 2: each `Deposit` folds in — `accumulator()` looks up (or creates) the bucket for its rail
and folds the element into that bucket's downstream accumulator, incrementing the running count.

![D-039 — The `Collector` contract's five functions](../diagrams/D-039c-collector-contract-s-five.svg)
**D-039** — The `Collector` contract's five functions (frame 3 of 4: `combiner()`)

Frame 3: the parallel case. Two sub-ranges of the source spliterator produced two partial maps —
`{CARD: 41000, BANK: 2100}` and `{CARD: 54000, BANK: 4400}` — and `combiner()` merges them key-by-
key, summing the counts for keys present in both.

![D-039 — The `Collector` contract's five functions](../diagrams/D-039d-collector-contract-s-five.svg)
**D-039** — The `Collector` contract's five functions (frame 4 of 4: `finisher()`, with the
`IDENTITY_FINISH` skip path)

Frame 4: `finisher()` converts the accumulator's internal shape to the declared result type. For
`counting()` downstream, the finisher unboxes the internal `long[1]` into a `Long`. For the outer
`groupingBy`, the map accumulator already **is** the result — `IDENTITY_FINISH` is present, so the
finisher step is skipped entirely and the accumulator map is cast straight to the return type. The
legend in the corner lists `CONCURRENT`, `UNORDERED`, `IDENTITY_FINISH` as the three characteristics
in play across this pipeline: the outer `groupingBy` here is **not** `CONCURRENT` (this is the
sequential `groupingBy`, not `groupingByConcurrent`, so a real combine step is needed, as frame 3
shows), and the downstream `counting()` is `IDENTITY_FINISH`-eligible on its own but is wrapped by
`groupingBy`'s own accumulator regardless.

**Concrete example.** Building the collector by hand for "count deposits per rail" — the same
computation `groupingBy(Deposit::rail, counting())` performs, written out so every one of the five
functions is visible:

```java
record Deposit(ClientId clientId, Money amount, Rail rail, StatusCode status) {}

enum Rail { CARD, BANK }

// Hand-rolled equivalent of Collectors.groupingBy(Deposit::rail, Collectors.counting())
Collector<Deposit, Map<Rail, long[]>, Map<Rail, Long>> countByRail = Collector.of(
    HashMap::new,                                                  // supplier
    (Map<Rail, long[]> acc, Deposit d) ->
        acc.computeIfAbsent(d.rail(), r -> new long[1])[0]++,      // accumulator
    (Map<Rail, long[]> left, Map<Rail, long[]> right) -> {         // combiner
        right.forEach((rail, count) ->
            left.merge(rail, count, (a, b) -> new long[]{a[0] + b[0]}));
        return left;
    },
    acc -> acc.entrySet().stream()                                 // finisher
        .collect(Collectors.toMap(Map.Entry::getKey, e -> e.getValue()[0]))
    // no Characteristics.IDENTITY_FINISH — A (Map<Rail, long[]>) and R (Map<Rail, Long>) differ
);

List<Deposit> sample = List.of(
    new Deposit(new ClientId(UUID.randomUUID()), new Money(new BigDecimal("65.00"), Currency.getInstance("GBP")), Rail.CARD, new StatusCode("DEP", 3, 0, 1)),
    new Deposit(new ClientId(UUID.randomUUID()), new Money(new BigDecimal("480.00"), Currency.getInstance("GBP")), Rail.BANK, new StatusCode("BDP", 3, 0, 1)),
    new Deposit(new ClientId(UUID.randomUUID()), new Money(new BigDecimal("65.00"), Currency.getInstance("GBP")), Rail.CARD, new StatusCode("DEP", 3, 0, 1))
);

Map<Rail, Long> byRail = sample.stream().collect(countByRail);
// {CARD=2, BANK=1}
```

`Collector.of` here takes the four-argument overload (no explicit `Characteristics` vararg), so the
resulting collector's `characteristics()` set is empty — no `IDENTITY_FINISH`, meaning `finisher()`
genuinely runs. Compare that to `Collectors.groupingBy(Deposit::rail, Collectors.counting())`, which
the JDK ships with `IDENTITY_FINISH` present because its accumulator and result are both
`HashMap<Rail, Long>`-shaped by construction — the JDK's version needs no separate finisher step.

**The gotcha.** The accumulator instance handed to `accumulator()` and `combiner()` must never be
read or mutated from more than one thread **concurrently** — parallel streams guarantee each
sub-range's accumulator is thread-confined during accumulation and only touched by one thread at a
time during a `combiner()` call, but a hand-written `Collector` that stashes a reference to the
accumulator somewhere else (a field, a listener) breaks that guarantee silently, with no exception
— just a `Map` or `List` that occasionally has the wrong count on a busy box.

**Interview:** "Walk me through what `collect(Collectors.toList())` actually calls, in order, on a
sequential stream." Answer: `supplier().get()` once to build the `ArrayList`, `accumulator().accept`
once per element to call `list.add(element)`, no `combiner()` call because there is only one
container, and no `finisher()` call because `toList()` carries `IDENTITY_FINISH` — the `ArrayList`
built by the accumulator is unchecked-cast straight to the return type `List<T>`.

> A `Collector<T, A, R>` is a five-function, characteristic-tagged protocol for mutable reduction —
> `supplier` opens a container, `accumulator` folds one element in, `combiner` merges two
> containers for the parallel case, `finisher` converts the container to the result, and
> `IDENTITY_FINISH` licenses skipping that last step when the container already is the result.

**`[NUM]` — the class's size.** `Collectors` in Java 21 exposes 30 distinct static factory method
names. **Unverified:** the total overload count. The syllabus leaf states 54; a documentation-based
recount performed for this file corroborated the 30 names exactly but returned 63 as the overload
total on a second, independent count of the same javadoc page, and a hand-tally against the
per-method breakdown in that same recount does not itself sum to 63 either — the three attempts
(syllabus: 54, doc summary: 63, hand-tally of the doc summary's own breakdown: 47) disagree with
each other. The discrepancy is almost certainly a counting-methodology difference (does a method
with a `<T, K, U, A, M>` generic signature and a same-name-different-arity sibling count once or
per-arity; does `teeing`'s single six-argument signature count as one overload or is the merger
function's own generic arity being double-counted), not a disagreement about the actual API
surface, but this file cannot respons­ibly assert a specific overload total. Treat "dozens of
overloads across thirty factory names" as the safe interview-ready phrasing, and see
`## Open questions` for what would settle the exact figure.

---

### The `toX` family: `toList`, `toUnmodifiableList`, `toSet`, `toUnmodifiableSet`, `toCollection`

*Supporting fact.* Five collectors that fold a stream directly into a collection, differing only in
target type and mutability:

```java
List<Rail> rails = deposits.stream().map(Deposit::rail).collect(Collectors.toList());
List<Rail> frozenRails = deposits.stream().map(Deposit::rail).collect(Collectors.toUnmodifiableList());
Set<Rail> distinctRails = deposits.stream().map(Deposit::rail).collect(Collectors.toSet());
TreeSet<Rail> sortedRails = deposits.stream().map(Deposit::rail)
    .collect(Collectors.toCollection(TreeSet::new));
```

`toCollection` takes a `Supplier<C>` rather than a `Class` or a prototype instance, because the
supplier must be callable **once per accumulator created** — once per sequential run, or once per
sub-range in the parallel case — so it has to build a fresh, empty collection every time, never
return a shared one. `Stream.toList()` (Java 16, a method directly on `Stream`, distinct from the
`Collectors.toList()` collector) returns an already-unmodifiable list and is the shorter spelling
when you don't need a `Collector` for composition with `groupingBy` or `partitioningBy` — but
`Collectors.toList()` is what a `groupingBy(rail -> ..., toList())` downstream position requires,
since `Stream.toList()` is not itself a `Collector`.

**Pitfall:** assuming `Collectors.toList()` returns a specific, mutable, serializable type.

**Wrong**
```java
ArrayList<Rail> rails = (ArrayList<Rail>) deposits.stream()
    .map(Deposit::rail)
    .collect(Collectors.toList()); // compiles and runs today
rails.add(Rail.CARD); // and this "works", by accident, on every OpenJDK release so far
```

**Right**
```java
List<Rail> rails = new ArrayList<>(
    deposits.stream().map(Deposit::rail).collect(Collectors.toList()));
rails.add(Rail.CARD); // guaranteed mutable, because you built the ArrayList yourself
```

**Why people believe it:** the javadoc for `Collectors.toList()` has, at every JDK version through
21, described the returned type only as "a `List`" with "no guarantees ... on the type, mutability,
serializability, or thread-safety" — but the shipped OpenJDK implementation happens to return a
plain `ArrayList` in every release so far, and years of that happening to be true trains the wrong
mental model. `Collectors.toUnmodifiableList()` (Java 10) exists precisely so that code which wants
an immutability *guarantee* has a name for it instead of relying on the accident.

> `toList()`/`toSet()`/`toCollection()` fold a stream into a collection whose concrete type,
> mutability and thread-safety are contract-unspecified except where a `to*Unmodifiable*` or
> `toCollection(Supplier)` name states one explicitly.

---

### `toMap`

**Mental model.** `toMap` is `groupingBy`'s cousin for the case where each stream element maps to
**exactly one** key with **exactly one** value, not a bucket of values — think "build a lookup
table," not "build buckets." Concretely, it is `HashMap::new` as the supplier, and
`(map, element) -> map.merge(keyFn.apply(element), valueFn.apply(element), mergeFn)` as the
accumulator (the merge function defaults to "throw" when you use the two-argument overload, as the
next beat proves).

**Why it exists.** Before `toMap`, converting a `List<Deposit>` into a `Map<ClientId, Money>` meant
a `for` loop with a manually created `HashMap` and a manual `put` — fine until two elements shared
a key, at which point the loop's behaviour (silently overwrite? silently keep the first? throw?)
depended entirely on which line the author happened to write, with no compiler or reviewer
signalling the ambiguity. `toMap` forces that decision into the open: the two-argument form commits
to "this should never happen, and if it does, crash loudly," and the three-argument form makes the
resolution an explicit, named function.

**When to reach for it, and when not.** Reach for `toMap` when the source stream is known,
structurally, to produce at most one element per key — building an index by a natural or surrogate
key, for instance. Reach for `groupingBy` instead the moment "one key, one value" stops being true —
if two deposits can legitimately share a `ClientId` (they can: a client makes many deposits) and you
want **all** of them, not one merged value, `groupingBy(Deposit::clientId)` giving
`Map<ClientId, List<Deposit>>` is the correct sibling, not `toMap` with a merge function that quietly
throws away every deposit but one.

**How it works — the four overloads.**

| Overload | Signature shape | Duplicate-key behaviour | Backing map |
|---|---|---|---|
| `toMap(k, v)` | `(Function<T,K>, Function<T,V>)` | Throws `IllegalStateException` | `HashMap` |
| `toMap(k, v, merge)` | `(..., BinaryOperator<V>)` | Calls `merge` to combine | `HashMap` |
| `toMap(k, v, merge, mapFactory)` | `(..., Supplier<M>)` | Calls `merge` to combine | Caller's `Supplier<M>` |
| `toConcurrentMap(k, v[, merge[, mapFactory]])` | Same three shapes | Same, but see below | `ConcurrentHashMap` (or caller's `ConcurrentMap` factory) |

The accumulator for every non-concurrent overload is implemented in terms of `Map.merge`:

```java
(map, element) -> map.merge(keyMapper.apply(element), valueMapper.apply(element), mergeFunction)
```

— and for the two-argument overload, the `mergeFunction` the JDK supplies is:

```java
(u, v) -> { throw new IllegalStateException("Duplicate key " + u); }
```

`[SOURCE]` — this is the actual implementation shape in `java.util.stream.Collectors`; the message
text itself, `"Duplicate key %s (attempted merging values %s and %s)"`, is formatted with the
existing value, the existing value again, and the new value at the throw site, so the exception
message you see always names the key and both colliding values.

`[PROVE]` — walking why the *value*, not the key, is what triggers a `NullPointerException`:
`Map.merge(key, value, fn)`'s own contract, on every `Map` implementation including `HashMap`, is
specified to throw `NullPointerException` immediately if `value` is `null`, **before** it even
looks at whether `key` already has a mapping — `HashMap.merge`'s source begins with
`Objects.requireNonNull(remappingFunction)` and then, once it locates or fails to locate an existing
value, treats a `null` incoming value as invalid input regardless of collision. `HashMap.put(key,
null)`, by contrast, is perfectly legal — `put` has no null-value contract violation to trigger,
because `put` unconditionally overwrites, and overwriting with `null` is exactly as valid as
overwriting with anything else. `toMap` never calls `put`; it always calls `merge`, so it inherits
`merge`'s stricter null-value contract even on the very first occurrence of a key, with no
collision in sight. This is a `Collectors` design choice, not a general `Map` behaviour — `toMap`
chose `merge` as the single accumulation primitive because `merge` is the one `Map` method whose
signature already expresses "combine on collision," and inherited the null-value strictness that
comes bundled with that method.

![D-039 — The `Collector` contract's five functions](../diagrams/D-039a-collector-contract-s-five.svg)

*(D-039 is scoped to the generic five-function contract above and is not re-embedded here; `toMap`
is a named instance of that same contract with `HashMap::new` as `supplier()` and `map::merge` as
`accumulator()` — no separate diagram is assigned to this concept.)*

**Concrete example — the duplicate-key crash and the null-value crash, both against QuizStakes.**

```java
record Deposit(ClientId clientId, Money amount, Rail rail, StatusCode status) {}

List<Deposit> deposits = List.of(
    new Deposit(CLIENT_4471, new Money(new BigDecimal("65.00"), GBP), Rail.CARD, DEP_301_CAPTURED),
    new Deposit(CLIENT_4471, new Money(new BigDecimal("40.00"), GBP), Rail.CARD, DEP_301_CAPTURED),
    new Deposit(CLIENT_9002, new Money(new BigDecimal("480.00"), GBP), Rail.BANK, BDP_301_CAPTURED)
);

// CLIENT_4471 appears twice — this throws at the second occurrence:
Map<ClientId, Money> latestDeposit = deposits.stream()
    .collect(Collectors.toMap(Deposit::clientId, Deposit::amount));
// IllegalStateException: Duplicate key ClientId[value=...] (attempted merging values
//   Money[amount=65.00, currency=GBP] and Money[amount=40.00, currency=GBP])

// Fixed with an explicit merge policy — keep the larger deposit:
Map<ClientId, Money> largestDeposit = deposits.stream()
    .collect(Collectors.toMap(
        Deposit::clientId,
        Deposit::amount,
        (existing, incoming) -> existing.amount().compareTo(incoming.amount()) >= 0
            ? existing
            : incoming));
// {CLIENT_4471=Money[65.00, GBP], CLIENT_9002=Money[480.00, GBP]}

// A null Money value — e.g. a lookup that hasn't captured an amount yet — throws immediately,
// with no duplicate in sight:
record PendingDeposit(ClientId clientId, Money amount) {}
List<PendingDeposit> pending = List.of(new PendingDeposit(CLIENT_4471, null));
pending.stream().collect(Collectors.toMap(PendingDeposit::clientId, PendingDeposit::amount));
// NullPointerException — thrown by Map.merge's null-value check, on the very first element
```

**The gotcha.** Both crashes above are runtime-only — nothing in the type system stops either
`toMap` call from compiling. The two-argument overload is a correctness bet: it says "I have proven
to myself that this key is unique in this stream," and the exception is the JDK holding you to that
bet rather than silently corrupting the map.

**Pitfall:** reaching for `toMap` with a same-value merge function (`(a, b) -> a`) purely to
suppress the exception, without checking whether losing every value but one is actually correct.

**Wrong**
```java
Map<ClientId, Money> deposit = deposits.stream()
    .collect(Collectors.toMap(Deposit::clientId, Deposit::amount, (a, b) -> a));
// compiles, never throws, and silently drops every deposit after a client's first —
// a real production bug if the intent was "total per client"
```

**Right**
```java
Map<ClientId, Money> totalPerClient = deposits.stream()
    .collect(Collectors.groupingBy(
        Deposit::clientId,
        Collectors.reducing(Money.ZERO, Deposit::amount, Money::add)));
// every deposit is accounted for — groupingBy + a downstream fold, not a merge that discards data
```

**Why people believe it:** `(a, b) -> a` makes the compiler error disappear immediately, and the
happy-path test data usually has one deposit per client, so the silent data loss never shows up
until production traffic supplies a client with two.

**`toUnmodifiableMap` and `toConcurrentMap`.** *Supporting facts, three beats each.* `toUnmodifiableMap`
has two overloads (`(k,v)` and `(k,v,merge)` — there is no unmodifiable-plus-mapFactory overload,
because the whole point is that the caller does not get to choose the backing implementation).
Duplicate-key and null-value behaviour are identical to `toMap`'s two- and three-argument forms; the
only difference is that the result is wrapped unmodifiable before being returned, via the same
`collectingAndThen`-style finisher wrapping described in §1.10.16. `toConcurrentMap` has all four
of `toMap`'s overload shapes, backed by `ConcurrentHashMap` by default, and carries
`Characteristics.CONCURRENT` — meaning on a parallel, unordered-eligible stream the runtime may
skip building per-sub-range maps and combiner-merging them, instead having every thread accumulate
directly into one shared `ConcurrentHashMap`. **Pitfall:** assuming `toConcurrentMap`'s null
handling is looser than `toMap`'s because "concurrent" sounds more permissive — it is the opposite:
`ConcurrentHashMap` forbids null keys **and** null values outright at the `put`/`merge` level, so
`toConcurrentMap` fails faster and on more inputs (a null key, not just a null value) than the
`HashMap`-backed `toMap`.

> `toMap` builds a one-key-one-value lookup by folding every element through `Map.merge`; the
> two-argument overload's merge function is "throw on collision," which is why a duplicate key is
> an `IllegalStateException` and a null value is a `NullPointerException` even on a key seen once.

---

### `joining`

*Supporting fact.* Three overloads, all producing a `String`, all backed by a shared
`StringBuilder`-based accumulator so that concatenation cost is linear, not the quadratic cost of
repeated `String + String`:

```java
String rails = deposits.stream().map(d -> d.rail().name()).collect(Collectors.joining());
// "CARDCARDBANK"
String railsCsv = deposits.stream().map(d -> d.rail().name()).collect(Collectors.joining(", "));
// "CARD, CARD, BANK"
String railsReport = deposits.stream().map(d -> d.rail().name())
    .collect(Collectors.joining(", ", "Rails seen: [", "]"));
// "Rails seen: [CARD, CARD, BANK]"
```

`joining()` only accepts a `Stream<CharSequence>` (or a subtype, like `Stream<String>`) — there is
no primitive-friendly overload, because there is no meaningful "joining" of an `IntStream`. The
prefix and suffix appear exactly once regardless of element count, including zero elements — an
empty stream through the three-argument overload still produces `"Rails seen: []"`, not `""`.

**Pitfall:** calling `.map(Object::toString).collect(joining(", "))` on a stream of a custom type
that has not overridden `toString()` — the join succeeds and produces `Deposit@1a2b3c4d, ...`, a
plausible-looking bug that only surfaces when someone reads the output.

> `joining` accumulates a stream of `CharSequence` into one `String` via a shared `StringBuilder`,
> with delimiter, prefix and suffix all applied exactly once per collection, never per boundary
> that happens to exist.

---

### The summing / averaging / summarizing family, and Kahan summation

**Mental model.** These are single-purpose reducers: each one folds a stream of numbers (or a
stream of objects via an extractor function) into exactly one statistic — a sum, an average, or a
full five-number summary (`min`, `max`, `sum`, `count`, `average` together). Picture each as a tiny
fixed-size scratchpad — one `int[1]`, one `long[2]`, one `double[3]` — that gets folded into on every
element and read once at the end.

**Why it exists.** `IntStream.sum()` and `IntStream.average()` already exist as terminal operations
directly on the primitive stream types — but a `Collector` version is needed the moment summation
has to happen **alongside** another collection, most commonly as the downstream of a `groupingBy`.
`deposits.stream().collect(groupingBy(Deposit::rail, summingDouble(d ->
d.amount().amount().doubleValue())))` computes a per-rail total in one pass; doing the same with
`IntStream.sum()` would require grouping into `List`s first and then a second pass per group.

**When to reach for it, and when not.** Reach for `summingInt`/`summingLong`/`summingDouble` and
their `averaging*` and `summarizing*` counterparts specifically as **downstream** collectors inside
`groupingBy`/`partitioningBy`, or wherever a `Collector` (not a terminal operation) is required by
the API shape. When operating on a bare stream with no grouping involved, prefer the primitive
stream terminal operations directly — `deposits.stream().mapToDouble(...).sum()` — which are no
less correct and avoid manufacturing a `Collector` for no compositional reason. Reach for
`summarizingX` over separately calling `summingX` and `averagingX` and `counting()` when you need
more than one of those statistics from the same pass, since `summarizingX` computes all five in one
traversal.

**How it works — the accumulator shapes, verified against the Java 21 source.** `[RESEARCH]`
Re-verified against `java.util.stream.Collectors` at the `jdk-21+35` tag rather than assumed:

| Collector | Accumulator array | What the slots hold |
|---|---|---|
| `summingInt` | `new int[1]` | the running sum, **as an `int`** |
| `summingLong` | `new long[1]` | the running sum |
| `summingDouble` | `new double[3]` | Kahan: high-order sum, running compensation, simple (uncompensated) sum |
| `averagingInt` | `new long[2]` | running sum, running count |
| `averagingLong` | `new long[2]` | running sum, running count |
| `averagingDouble` | `new double[4]` | Kahan sum, compensation, count, simple sum |

`[NUM][PROVE]` — the consequence of `summingInt` using `int[1]` rather than the widened
accumulator its `average`/`long` siblings use: it has **exactly the same silent-overflow exposure
as `IntStream.sum()`**, and it is easy to assume otherwise because `averagingInt` widens to `long`
and readers generalize that widening to the whole summing/averaging family. Proved on this machine
(`javac --release 21`), folding three deposits of 1,000,000,000 each through both collectors:

```java
List<Integer> amounts = List.of(1_000_000_000, 1_000_000_000, 1_000_000_000);
int viaSummingInt = amounts.stream().collect(Collectors.summingInt(Integer::intValue));
long viaSummingLong = amounts.stream().collect(Collectors.summingLong(Integer::longValue));
System.out.println("summingInt : " + viaSummingInt);
System.out.println("summingLong: " + viaSummingLong);
```
```
summingInt : -1294967296
summingLong: 3000000000
expected   : 3000000000
```

`3,000,000,000` exceeds `Integer.MAX_VALUE` (`2,147,483,647`) by `852,516,353`; two's-complement
wraparound lands the `int` accumulator at `-1,294,967,296`, which is `3,000,000,000 - 2^32`
(`2^32 = 4,294,967,296`) — the arithmetic is a plain 32-bit wraparound, not a JDK bug.
`averagingInt` genuinely is safe from this specific failure, because its accumulator sums into a
`long[2]` slot even though the *input* elements are `int`-typed — that half of the syllabus claim
is correct; the half that generalizes it to `summingInt` is not.

`[RESEARCH][NUM]` — Kahan compensated summation, and why `summingDouble`/`averagingDouble` can
disagree with a naive loop. A naive running sum of `double`s accumulates floating-point rounding
error at every addition, because each intermediate sum is itself rounded to the nearest
representable `double`. Kahan summation tracks a second value — the compensation, `c` — that
carries forward the rounding error lost at each step, and subtracts it back in on the next
addition:

```java
double sum = 0.0, c = 0.0;
for (double x : values) {
    double y = x - c;          // correct the next value by the running error
    double t = sum + y;        // this addition may lose low-order bits of y
    c = (t - sum) - y;         // recover exactly what was lost
    sum = t;
}
```

This is why `summingDouble`'s accumulator needs **three** `double` slots, not one: the high-order
sum, the compensation, and (per the JDK's own implementation) a simple uncompensated sum kept
alongside for a sanity/fallback check that the JDK's own `Collectors` source performs internally.
The practical consequence: summing the same list of `double` deposit amounts with
`Collectors.summingDouble` and with a hand-written `for (double x : xs) sum += x;` loop can disagree
in the last one or two decimal digits, and `summingDouble`'s answer is the more accurate one — not
because the JDK is doing something exotic, but because it is doing the arithmetically careful thing
by default where a hand-rolled loop does the naive thing.

**Insight:** this is also the reason production money code never uses `summingDouble` at all —
`Money` in this domain is `BigDecimal`-backed specifically because *even* Kahan-compensated `double`
summation cannot represent `0.1` exactly, so it can never be made bit-exact for currency. Kahan
summation narrows the error, it does not eliminate it. `Collectors` has no `summingBigDecimal`;
summing `Money` correctly means `reducing(Money.ZERO, Deposit::amount, Money::add)` (§1.10.14),
trading a compensation trick for the exactness `BigDecimal` gives for free.

![D-039 — The `Collector` contract's five functions](../diagrams/D-039a-collector-contract-s-five.svg)

*(No diagram is separately assigned to this concept; D-039 remains scoped to the generic contract
and D-040 above already lists this family's rows in the inventory table.)*

**Concrete example — card deposits averaging 65, summed two ways.**

```java
List<Deposit> cardDeposits = /* 95,000/day in production; here, a representative sample */ List.of(
    new Deposit(CLIENT_4471, new Money(new BigDecimal("65.00"), GBP), Rail.CARD, DEP_301_CAPTURED),
    new Deposit(CLIENT_9002, new Money(new BigDecimal("64.50"), GBP), Rail.CARD, DEP_301_CAPTURED),
    new Deposit(CLIENT_2210, new Money(new BigDecimal("65.50"), GBP), Rail.CARD, DEP_301_CAPTURED)
);

double kahanTotal = cardDeposits.stream()
    .collect(Collectors.summingDouble(d -> d.amount().amount().doubleValue()));

double naiveTotal = 0.0;
for (Deposit d : cardDeposits) {
    naiveTotal += d.amount().amount().doubleValue();
}

DoubleSummaryStatistics stats = cardDeposits.stream()
    .collect(Collectors.summarizingDouble(d -> d.amount().amount().doubleValue()));

System.out.println(kahanTotal + " " + naiveTotal);   // 195.0 195.0 for this small, exact sample
System.out.println(stats);
// DoubleSummaryStatistics{count=3, sum=195.000000, min=64.500000, average=65.000000, max=65.500000}
```

This particular sample happens to sum exactly, because `64.50`, `65.00` and `65.50` are all exactly
representable in binary floating point at this precision — the divergence between Kahan and naive
summation only becomes visible at larger sample counts or with values (like `0.1`, `0.33`) that are
not exactly representable, which is exactly why the domain's own bonus rounding example
(`3.33` split as `0.33` bonus `+ 3.00` cash, never `0.34 + 3.00`) is worked with `BigDecimal` and
`RoundingMode.DOWN`, not `double`, elsewhere in this note set.

**The gotcha.** `averagingInt`/`averagingLong`/`averagingDouble` all return `Double`, never `Long`
or `BigDecimal`, regardless of the input element type — `averagingInt(Deposit::rail's ordinal)`
still hands back a boxed `Double`, so a caller expecting an integral average has to round or
truncate explicitly.

**Pitfall:** using `summingInt` on a value that can plausibly exceed roughly two billion in
aggregate — total ledger entry bytes, total stake volume in minor units — because "it's just a sum,
what could go wrong."

**Wrong**
```java
int totalPennies = deposits.stream()
    .collect(Collectors.summingInt(d -> d.amount().amount().movePointRight(2).intValueExact()));
// fine at low volume; wraps silently once the running total crosses ~21.4 million pennies (~£214,000)
```

**Right**
```java
long totalPennies = deposits.stream()
    .collect(Collectors.summingLong(d -> d.amount().amount().movePointRight(2).longValueExact()));
// or, for true currency correctness, avoid primitives altogether:
Money total = deposits.stream()
    .collect(Collectors.reducing(Money.ZERO, Deposit::amount, Money::add));
```

**Why people believe it:** `summingInt` reads as the obviously-correct name for "sum these `int`s,"
and small-scale manual testing (a handful of sample deposits) never gets anywhere near
`Integer.MAX_VALUE`, so the wraparound is invisible until the aggregate crosses roughly two billion
in production — at 95,000 card deposits per day averaging 65, in minor units that threshold arrives
in well under a year of retained running totals if one were (incorrectly) maintained this way.

> `summingInt`/`summingLong`/`summingDouble`/`averagingInt`/`averagingLong`/`averagingDouble`/
> `summarizingInt`/`summarizingLong`/`summarizingDouble` fold a numeric stream into one statistic
> each; the integer summers use plain (overflow-prone) arithmetic, the double summers use
> three-or-four-slot Kahan-compensated arithmetic for reduced (not eliminated) floating-point error,
> and none of the nine is a substitute for `BigDecimal` where currency exactness is required.

---

### `minBy` / `maxBy`

*Supporting fact.* Two collectors, each taking a `Comparator<T>` and returning `Optional<T>` — never
the raw element and never `null`:

```java
Optional<Deposit> largestCardDeposit = cardDeposits.stream()
    .collect(Collectors.maxBy(Comparator.comparing(d -> d.amount().amount())));
```

They exist as `Collector`s (rather than only as `Stream.min`/`Stream.max`, which already do the
same job as terminal operations) purely so they can be used as a **downstream** collector inside
`groupingBy` — "largest deposit per rail" is `groupingBy(Deposit::rail, maxBy(comparingByAmount))`,
one pass, whereas `Stream.max()` cannot be nested inside another collector's downstream slot.

**Pitfall:** calling `.get()` on the result without handling the empty-stream case, which for
`minBy`/`maxBy` means an empty *group* under `groupingBy`, not just an empty top-level stream — a
rail with zero deposits in a given window still produces a map entry whose value is
`Optional.empty()`, and `.get()` on that throws `NoSuchElementException` at a call site far from
where the empty group was created.

> `minBy`/`maxBy` fold a stream to its extreme element under a supplied `Comparator`, wrapped in
> `Optional` so an empty source (or an empty group, as a `groupingBy` downstream) is representable
> without a sentinel or a thrown exception at collection time.

---

### `reducing`

*Supporting fact.* Three overloads, all doing the same fold `Stream.reduce` already does, packaged
as a `Collector` so it can sit in a downstream position:

```java
Optional<Money> anyDeposit = deposits.stream().map(Deposit::amount)
    .collect(Collectors.reducing(Money::add));                       // reducing(op)
Money totalDeposits = deposits.stream().map(Deposit::amount)
    .collect(Collectors.reducing(Money.ZERO, Money::add));           // reducing(identity, op)
Money totalCardDeposits = deposits.stream()
    .collect(Collectors.reducing(Money.ZERO, Deposit::amount, Money::add)); // reducing(identity, mapper, op)
```

**Why it is the least-used of the thirty names:** at the top level of a stream pipeline,
`stream.map(mapper).reduce(identity, op)` says exactly the same thing with less ceremony and no
need to import `Collectors` at all — `reducing` earns its place **only** as a `groupingBy` or
`partitioningBy` downstream, where a plain `Stream.reduce` cannot be nested. `totalCardDeposits`
above, folding the total per rail via `groupingBy(Deposit::rail, reducing(Money.ZERO,
Deposit::amount, Money::add))`, is the shape where `reducing` is actually the right tool; the
single-collector, non-nested versions above exist mainly to be shown once for completeness.

**Pitfall:** reaching for the identity-less `reducing(op)` and forgetting it returns `Optional<T>`,
then calling `.get()` unguarded on a group that turned out to be empty — the exact same trap as
`minBy`/`maxBy` above, because `reducing(op)`'s accumulator is, in the JDK's own implementation,
built from the same "no identity, so wrap in `Optional`" shape as `minBy`/`maxBy`.

> `reducing` is `Stream.reduce` repackaged as a `Collector` so it can serve as a downstream fold
> inside `groupingBy`/`partitioningBy`; at the top level, plain `Stream.reduce` says the same thing
> more directly and is the clearer choice.

---

### Downstream collectors: `mapping`, `filtering`, `flatMapping`, `collectingAndThen`

**Mental model.** These four are not collectors in their own right — each one is an *adapter* that
takes another, "downstream" collector and changes what reaches it: `mapping` transforms each element
before it arrives, `filtering` drops elements before they arrive, `flatMapping` expands one element
into zero-or-more before they arrive, and `collectingAndThen` transforms the **result** after the
downstream collector has already finished. Picture a downstream collector as a machine at the end of
a conveyor belt; these four decorate the belt (or, for `collectingAndThen`, decorate the machine's
output chute) without changing the machine itself.

**Why they exist.** Without them, reshaping what a `groupingBy` downstream sees would require
writing that transformation into the upstream `.map()`/`.filter()` call — which is fine at the top
level, but a `groupingBy`'s grouping key and its downstream collector both need to see the
**original**, unmapped element (the key function needs the whole `Deposit` to read `.rail()`; a
downstream `mapping` can then narrow to just the amount for summing). A `.map()` placed before
`groupingBy` would strip the field the grouping key needs before the group even forms.

**When to reach for it, and when not.** Reach for `mapping`/`filtering`/`flatMapping` specifically
inside a `groupingBy`/`partitioningBy` downstream slot, or nested inside another downstream
collector — never at the top level of a plain stream, where `.map()`/`.filter()`/`.flatMap()` on
the stream itself say the same thing more directly and more efficiently (no intermediate `Collector`
machinery needed). Reach for `collectingAndThen` when a downstream collector's raw result needs one
more transformation applied only once, at the end — most commonly wrapping a mutable result
unmodifiable, or collapsing a collection down to a single derived value.

**How it works.**

`mapping(Function<T,U> mapper, Collector<U,A,R> downstream)` — builds a new collector whose
`accumulator` is `(acc, t) -> downstream.accumulator().accept(acc, mapper.apply(t))`; every other
function (`supplier`, `combiner`, `finisher`, `characteristics`) is inherited unchanged from
`downstream`.

`filtering(Predicate<T> predicate, Collector<T,A,R> downstream)` (**Java 9**) — builds a new
collector whose `accumulator` is `(acc, t) -> { if (predicate.test(t)) downstream.accumulator()
.accept(acc, t); }`. The distinction that matters: filtering **inside** a `groupingBy` downstream
still creates an entry for every key that appeared upstream, with an empty (or partially-filtered)
downstream result — filtering the stream **before** `groupingBy` removes the key entirely if every
one of its elements gets filtered out. "Which rails had zero *failed* deposits" needs the former;
filtering before grouping cannot answer it, because a rail with only successful deposits would
simply never appear as a key at all.

`flatMapping(Function<T, Stream<U>> mapper, Collector<U,A,R> downstream)` (**Java 9**) — the
accumulator becomes `(acc, t) -> mapper.apply(t).forEach(u -> downstream.accumulator().accept(acc,
u))`, letting one upstream element contribute zero, one, or many elements to the downstream
collector. This exists specifically because `Stream.flatMap` cannot be nested inside a
`groupingBy` downstream position — only a `Collector` can go there, and before Java 9 there was no
`Collector`-shaped equivalent of `flatMap`.

`collectingAndThen(Collector<T,A,R> downstream, Function<R,RR> finisher)` — wraps `downstream`,
keeping its `supplier`, `accumulator` and `combiner` unchanged, but composes a new `finisher`:
`downstream.finisher().andThen(finisher)`. Critically, its `characteristics()` are
`downstream.characteristics()` **with `IDENTITY_FINISH` removed** if it was present — because the
whole point of `collectingAndThen` is to run one more transformation after the downstream's own
finisher, so the "skip the finisher" shortcut can no longer apply.

**Concrete example — all four, against QuizStakes.**

```java
// mapping: total amount per rail, without needing groupingBy's key function to already be an amount
Map<Rail, Double> totalByRail = deposits.stream()
    .collect(Collectors.groupingBy(
        Deposit::rail,
        Collectors.mapping(d -> d.amount().amount().doubleValue(), Collectors.summingDouble(x -> x))));

// filtering: which rails have at least one *captured* deposit, keeping every rail key even if
// its captured-only bucket is empty
Map<Rail, List<Deposit>> capturedByRail = deposits.stream()
    .collect(Collectors.groupingBy(
        Deposit::rail,
        Collectors.filtering(d -> d.status().equals(DEP_301_CAPTURED), Collectors.toList())));

// flatMapping: every distinct StatusCode reached, per rail, given each Deposit might itself carry
// a small audit trail of prior statuses
record DepositWithHistory(Deposit current, List<StatusCode> history) {}
Map<Rail, Set<StatusCode>> statusesSeenByRail = depositsWithHistory.stream()
    .collect(Collectors.groupingBy(
        d -> d.current().rail(),
        Collectors.flatMapping(d -> d.history().stream(), Collectors.toSet())));

// collectingAndThen: an unmodifiable snapshot of the per-client deposit index
Map<ClientId, Money> latestDepositImmutable = deposits.stream()
    .collect(Collectors.collectingAndThen(
        Collectors.toMap(Deposit::clientId, Deposit::amount, (a, b) -> b),
        Collections::unmodifiableMap));

// collectingAndThen: collapse-to-a-single-value idiom — "the one deposit, or blow up if there
// wasn't exactly one" for a code path that has already asserted single-deposit invariants upstream
Deposit theOnlyDeposit = singleClientDeposits.stream()
    .collect(Collectors.collectingAndThen(
        Collectors.toList(),
        list -> {
            if (list.size() != 1) {
                throw new IllegalStateException("Expected exactly one deposit, found " + list.size());
            }
            return list.get(0);
        }));
```

**The gotcha.** `collectingAndThen`'s finisher runs exactly once, on the fully-combined result — it
is not a per-element hook and cannot be used to reject or transform individual elements the way
`filtering`/`mapping` can; reaching for `collectingAndThen` to do per-element work is a sign the
downstream collector, not the wrapper, is the piece that needs changing.

**Pitfall:** wrapping `toConcurrentMap` (or any `CONCURRENT` collector) with `collectingAndThen` and
expecting the `CONCURRENT` optimisation to still apply on a parallel stream.

**Wrong**
```java
Map<ClientId, Money> frozen = deposits.parallelStream()
    .collect(Collectors.collectingAndThen(
        Collectors.toConcurrentMap(Deposit::clientId, Deposit::amount),
        Collections::unmodifiableMap));
// works, but silently loses the CONCURRENT fast path — collectingAndThen strips
// Characteristics.IDENTITY_FINISH, and the runtime's decision to skip per-thread accumulator
// splitting depends on the full characteristics set including CONCURRENT + UNORDERED together
```

**Right**
```java
Map<ClientId, Money> mutable = deposits.parallelStream()
    .collect(Collectors.toConcurrentMap(Deposit::clientId, Deposit::amount));
Map<ClientId, Money> frozen = Collections.unmodifiableMap(mutable);
// same result, but the CONCURRENT collector runs at full speed, and the wrap happens once,
// outside the stream pipeline, where it obviously costs nothing extra
```

**Why people believe it:** `collectingAndThen` reads as a pure post-processing step with no
runtime-strategy implications, and for `IDENTITY_FINISH`-only collectors that intuition is close
enough to correct — it only breaks down for the `CONCURRENT` case, which is rare enough in
application code that the interaction is easy to have never hit before.

> `mapping`/`filtering`/`flatMapping` decorate what a downstream collector receives — transforming,
> dropping, or expanding elements before accumulation — while `collectingAndThen` decorates what a
> downstream collector returns, running one more transformation after its finisher and, in doing
> so, forfeiting `IDENTITY_FINISH` if the wrapped collector had it.

---

## Pitfalls

### Assuming `Collectors.toList()` guarantees a mutable `ArrayList`

**Wrong**
```java
ArrayList<Rail> rails = (ArrayList<Rail>) deposits.stream()
    .map(Deposit::rail).collect(Collectors.toList());
rails.add(Rail.CARD);
```

**Right**
```java
List<Rail> rails = new ArrayList<>(
    deposits.stream().map(Deposit::rail).collect(Collectors.toList()));
rails.add(Rail.CARD);
```

**Why people believe it:** every OpenJDK release to date happens to return a plain `ArrayList`,
even though the javadoc explicitly disclaims any guarantee about type or mutability.

### Treating `toMap`'s two-argument overload as safe for streams with any possible key repetition

**Wrong**
```java
Map<ClientId, Money> deposit = deposits.stream()
    .collect(Collectors.toMap(Deposit::clientId, Deposit::amount));
// throws IllegalStateException the moment a client has two deposits in the source
```

**Right**
```java
Map<ClientId, List<Money>> deposit = deposits.stream()
    .collect(Collectors.groupingBy(Deposit::clientId, Collectors.mapping(Deposit::amount, Collectors.toList())));
```

**Why people believe it:** in a test fixture with one deposit per client, the two-argument form
never throws, so the assumption that keys are unique never gets challenged until production data
supplies a repeat.

### Passing a `null` value into `toMap` and expecting `HashMap.put`'s permissiveness

**Wrong**
```java
Map<ClientId, Money> lookup = pendingDeposits.stream()
    .collect(Collectors.toMap(PendingDeposit::clientId, PendingDeposit::amount));
// NullPointerException the instant any amount is null, regardless of duplicate keys
```

**Right**
```java
Map<ClientId, Optional<Money>> lookup = pendingDeposits.stream()
    .collect(Collectors.toMap(
        PendingDeposit::clientId,
        d -> Optional.ofNullable(d.amount())));
```

**Why people believe it:** `HashMap.put(key, null)` is legal, and `toMap` reads like "just calls
`put`," so the null-hostility of the underlying `Map.merge` call is invisible until it throws.

### Using `summingInt` for a value that can plausibly exceed roughly two billion in aggregate

**Wrong**
```java
int totalPennies = deposits.stream()
    .collect(Collectors.summingInt(d -> d.amount().amount().movePointRight(2).intValueExact()));
```

**Right**
```java
long totalPennies = deposits.stream()
    .collect(Collectors.summingLong(d -> d.amount().amount().movePointRight(2).longValueExact()));
```

**Why people believe it:** `averagingInt` widens internally to `long`, and that fact generalizes,
incorrectly, to its `summingInt` sibling, which does not.

### Filtering upstream of `groupingBy` when the empty-group case matters

**Wrong**
```java
Map<Rail, List<Deposit>> capturedByRail = deposits.stream()
    .filter(d -> d.status().equals(DEP_301_CAPTURED))
    .collect(Collectors.groupingBy(Deposit::rail, Collectors.toList()));
// a rail with zero captured deposits simply never appears as a key
```

**Right**
```java
Map<Rail, List<Deposit>> capturedByRail = deposits.stream()
    .collect(Collectors.groupingBy(
        Deposit::rail,
        Collectors.filtering(d -> d.status().equals(DEP_301_CAPTURED), Collectors.toList())));
// every rail seen upstream still gets a key, possibly with an empty list
```

**Why people believe it:** both versions produce identical output whenever every group has at least
one surviving element, which is the overwhelmingly common case in ad hoc testing — the difference
only shows up for a group that becomes entirely empty after filtering.

---

## Cheat sheet

| Need | Collector | Result | Watch for |
|---|---|---|---|
| Plain list | `toList()` | `List<T>`, unspecified mutability | Don't cast, don't assume mutable |
| Immutable list | `toUnmodifiableList()` | `List<T>`, immutable | Nulls throw NPE |
| Plain set | `toSet()` | `Set<T>`, unspecified order | No order guarantee |
| Custom collection | `toCollection(Supplier)` | Caller's type | Supplier must be a fresh instance each call |
| One key → one value | `toMap(k,v)` | `Map<K,V>` | Duplicate key throws; null value throws |
| One key → one value, collisions resolved | `toMap(k,v,merge)` | `Map<K,V>` | Merge function must not silently drop needed data |
| Thread-safe map, parallel-friendly | `toConcurrentMap(...)` | `ConcurrentMap<K,V>` | Null key **and** value both forbidden |
| Immutable map | `toUnmodifiableMap(k,v[,merge])` | `Map<K,V>` | Same duplicate/null rules as `toMap` |
| Concatenate strings | `joining([delim[,prefix,suffix]])` | `String` | Prefix/suffix appear exactly once |
| Count | `counting()` | `Long` | Boxed, not primitive |
| Sum ints (overflow risk) | `summingInt` | `Integer` | Silently wraps past ~2.1B |
| Sum longs | `summingLong` | `Long` | Safe at realistic ledger volumes |
| Sum doubles, compensated | `summingDouble` | `Double` | Not a `BigDecimal` substitute |
| Average | `averagingInt/Long/Double` | `Double` | Always `Double`, even from `int` |
| Five-number summary | `summarizingInt/Long/Double` | `*SummaryStatistics` | One pass, five stats |
| Extreme element | `minBy`/`maxBy` | `Optional<T>` | Empty group → `Optional.empty()`, guard `.get()` |
| Fold to one value (downstream) | `reducing(...)` | `Optional<T>` or `T` | Prefer `Stream.reduce` at top level |
| Transform before accumulating | `mapping(fn, downstream)` | Delegates | Only useful nested (e.g. inside `groupingBy`) |
| Drop before accumulating, keep the key | `filtering(pred, downstream)` | Delegates | Java 9+; different from filtering upstream |
| Expand before accumulating | `flatMapping(fn, downstream)` | Delegates | Java 9+; downstream-only, `Stream.flatMap` for top level |
| Transform after accumulating | `collectingAndThen(downstream, fn)` | `fn`'s return type | Strips `IDENTITY_FINISH`; breaks `CONCURRENT` fast path |

---

## Self-test

**Q1.** Why does `collect(Collectors.toList())` never invoke `finisher()` on a sequential stream,
while a hand-written `Collector.of(...)` with the same accumulator and no explicit `Characteristics`
argument always does?

<details><summary>Answer</summary>

`Collectors.toList()` is built with `Characteristics.IDENTITY_FINISH` present, which licenses the
runtime to skip calling `finisher()` entirely and instead perform an unchecked cast from the
accumulation type `A` straight to the result type `R`. The four-argument `Collector.of(supplier,
accumulator, combiner, finisher)` overload used with no trailing `Characteristics...` vararg
produces a collector whose `characteristics()` set is empty — no `IDENTITY_FINISH` — so the runtime
is required to call `finisher()` even if, in that particular case, `A` and `R` happen to be the same
type. `IDENTITY_FINISH` is a declared licence, not something the runtime infers from the actual
types involved.

</details>

**Q2.** A stream of `Deposit` objects is guaranteed, by upstream invariants, to have at most one
deposit per `ClientId`. Which `toMap` overload should be used, and why is a merge function
unnecessary?

<details><summary>Answer</summary>

The two-argument overload, `toMap(Deposit::clientId, Deposit::amount)`. Because the invariant
guarantees no key collision, the two-argument form's built-in "throw on duplicate" merge function
will never actually fire — and if the invariant is ever violated by a future change, the exception
is exactly the loud failure that should happen, rather than silently picking one deposit via a
merge function that was only ever there to suppress a compiler error.

</details>

**Q3.** Why does `Collectors.toMap(k, v)` throw `NullPointerException` on a `null` value even when
every key in the source stream is unique — no duplicates anywhere?

<details><summary>Answer</summary>

Because `toMap`'s accumulator is implemented as `map.merge(key, value, mergeFn)` for every element,
not `map.put(key, value)`. `Map.merge`'s contract specifies an immediate `NullPointerException` if
the incoming `value` is `null`, checked before the method even looks at whether the key already has
an entry. `HashMap.put(key, null)` has no such check and would succeed. `toMap` inherited `merge`'s
null-value strictness as a side effect of choosing `merge` as its single accumulation primitive
(the same primitive that gives it its duplicate-collision behaviour), not because null values are
independently disallowed.

</details>

**Q4.** A colleague summed 95,000 card deposits' amounts (as `int` minor units) using
`Collectors.summingInt` and got a negative total. What happened, and what is the arithmetic?

<details><summary>Answer</summary>

The running total exceeded `Integer.MAX_VALUE` (2,147,483,647) and wrapped around via two's-
complement overflow, because `summingInt`'s accumulator is a plain `int[1]` with no overflow
checking — unlike `averagingInt`, which widens its internal sum to `long`. If the true total were,
say, 3,000,000,000 minor units, the wrapped value would be `3,000,000,000 - 2^32 =
3,000,000,000 - 4,294,967,296 = -1,294,967,296`, matching the sign and rough magnitude of a
"suspiciously negative total." The fix is `summingLong` (safe at realistic ledger volumes) or, for
true currency exactness, `reducing` over `Money`/`BigDecimal` values directly.

</details>

**Q5.** Why can `summingDouble` and a hand-written `for` loop that does `sum += x` disagree on the
same input, and which one is more likely to be right?

<details><summary>Answer</summary>

`Collectors.summingDouble`'s accumulator uses Kahan compensated summation internally — a `double[3]`
accumulator carrying a high-order sum, a running compensation term, and a simple sum — which
corrects for the rounding error lost at each floating-point addition. A naive loop's `sum += x`
accumulates that rounding error unchecked at every step. `summingDouble`'s answer is the more
accurate of the two, though neither is bit-exact for currency, which is why real money arithmetic
in this domain uses `BigDecimal` (via `reducing`) rather than `summingDouble` at all.

</details>

**Q6.** Given `groupingBy(Deposit::rail, filtering(d -> d.status().equals(DEP_301_CAPTURED),
toList()))` versus `.filter(d -> d.status().equals(DEP_301_CAPTURED)).collect(groupingBy(Deposit::rail,
toList()))` — describe an input on which these two produce genuinely different maps.

<details><summary>Answer</summary>

Any input where at least one rail's deposits are **all** non-captured — say every `BANK` deposit in
the batch is still `BDP-000` in-progress and none has reached `BDP-301 CAPTURED`. The
`groupingBy`-with-`filtering` version still produces a `BANK` key in the result map, mapped to an
empty list, because grouping happens on the unfiltered stream and filtering only affects what
reaches each group's downstream collector. The `.filter()`-before-`groupingBy` version never sees
any `BANK` element survive the filter, so `BANK` never becomes a key in the resulting map at all.

</details>

**Q7.** Why does `collectingAndThen(toConcurrentMap(...), Collections::unmodifiableMap)` forfeit
the performance benefit of `toConcurrentMap`'s `CONCURRENT` characteristic on a parallel stream?

<details><summary>Answer</summary>

`collectingAndThen` composes a new `finisher` on top of the wrapped collector but explicitly strips
`Characteristics.IDENTITY_FINISH` from the result if it was present, and more broadly changes the
combined collector's declared characteristics from what `toConcurrentMap` alone would report. The
runtime's decision to skip per-thread accumulator splitting and combine steps — accumulating every
thread directly into one shared map — depends on the collector's full characteristics set
(`CONCURRENT` together with the stream itself being safely treated as unordered); wrapping with
`collectingAndThen` changes that declared shape, so the fast path is not guaranteed to still apply
even though the wrapped collector still nominally has `toConcurrentMap`'s behaviour underneath.

</details>

---

## Deferred

None.

---

## Open questions

- **Unverified:** the exact total overload count across all 30 `Collectors` factory method names in
  Java 21. The syllabus leaf states 54; an independent documentation-based recount during this
  file's research pass produced 63, and a hand-tally of that same recount's own per-method
  breakdown produced 47 — three mutually inconsistent figures from two verification attempts. The
  30 distinct method *names* are solidly corroborated across all three attempts. What would settle
  it: running `javap -p java.util.stream.Collectors` (or reading the actual `.java` source file's
  method declarations) at the `jdk-21+35` tag and counting declared method signatures directly,
  rather than relying on a rendered javadoc page or a summarized recount of one.

---

**Leaves covered:** 1.10.1–1.10.16 (16 leaves)
**Leaves deferred:** none
**Diagrams included:** D-039 (all four frames), D-040
**Target version:** Java 21 LTS
**Lines:** 1143
