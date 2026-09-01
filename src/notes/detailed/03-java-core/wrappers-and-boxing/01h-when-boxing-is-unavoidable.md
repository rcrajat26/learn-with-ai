# 03 Java Core — When boxing is unavoidable — BASICS (§1.9, 1.9.20)

**Target version: Java 21 LTS.** | **Part 1 of 5** | [Index](../00-index.md)
Previous: [The cost of boxing](01g-the-cost-of-boxing.md) · Next: [Boxing internals](03-internals-boxing.md)

The previous file priced boxing. This one answers the question that follows immediately: when you
cannot avoid paying, and what the platform gives you when you can. The two questions have the same
answer, because they have the same single cause.

## 1. Boxing is forced by exactly one thing (1.9.20)

`[X-REF 02]` There is one root cause, not four. **A generic type argument can never be a primitive,
because generics are erased to reference types.** Every case in the syllabus leaf — collections,
generics generally, `Optional`, nullable columns — is that one fact wearing a different hat. A
`List<E>` needs `E` to be a reference type. `Optional<T>` needs `T` to be a reference type. A
nullable value needs a reference because `null` is a reference value and there is no `int` that means
absent. Once you see the four cases as one cause with four faces, the escape hatches stop being a
list to memorise: each of them is a **hand-written primitive specialisation of a generic API**, and
you can predict which ones exist and which ones cannot.

That prediction is the payoff. If a JDK API is generic and performance-sensitive, look for the
`Int`/`Long`/`Double` twin. If there is no twin, there is a reason, and the reason is almost always
that the operation needs a reference to work at all.

### Why it exists

Java shipped in 1995 with no generics and eight primitive types that are not objects. `Vector` held
`Object`. When generics arrived in Java 5 (JSR 14, 2004), the constraint that decided everything was
**binary compatibility with the existing pre-generics library**: `java.util.Vector` had to remain the
same class file, callable from unchanged code, whether or not the caller used the new type syntax.
The chosen mechanism was **erasure** — the compiler checks types, then throws the type argument away
and compiles the class as though it were the pre-generics version.

Erasure replaces a type variable with **its leftmost bound, or `Object` when it has none**, and casts
at the use sites. A primitive type is not a subtype of `Object` and cannot be a bound, so it cannot
be a type argument — `List<int>` was never on the table, not as a policy decision about performance
but as a consequence of the compatibility decision. The erasure chapter of this topic works through
the rewrite and the signature it produces; take the one-sentence version here.

What the JDK has done ever since is hand-write specialisations. `int[]` was always there. Java 8 added
`IntStream`, `LongStream`, `DoubleStream`, `OptionalInt`, `OptionalLong`, `OptionalDouble`,
`IntSummaryStatistics`, and about forty primitive functional interfaces. That is the whole strategy,
and it is why there are **exactly three** primitive stream types and not eight: each one is a separate
hand-written class hierarchy, and the JDK authors triaged to the three widths that carry real
numerical work.

**Insight:** every primitive escape hatch in the JDK is a hand-written copy of a generic API, because
erasure left no other option. That is also why the coverage is ragged — `IntStream` exists,
`CharStream` does not, `IntStream.groupingBy` does not. Nobody wrote it.

Project Valhalla is the intended end of this: value classes with no identity, and eventually generics
over them, which would let a single `List<int>` exist with a flat layout. It is not in Java 21;
[`03f-internals-monitors-and-valhalla.md`](03f-internals-monitors-and-valhalla.md) covers what it
changes and what it breaks.

### The mechanism

#### Case 1 — collections

Every JDK collection is generic, so every element and every key and value is a reference.

```java
// forced: the type argument must be a reference type
Map<String, Integer> reservedMinorUnitsByPosition = new HashMap<>();
reservedMinorUnitsByPosition.put("CLIENT_BONUS_RESERVED", 33);
reservedMinorUnitsByPosition.put("CLIENT_CASH_RESERVED", 300);

List<Long> settledLedgerEntryIds = new ArrayList<>();
```

`reservedMinorUnitsByPosition.put("CLIENT_BONUS_RESERVED", 33)` compiles to
`Integer.valueOf(33)` followed by the interface call — you can see it in the bytecode in
[`03c-internals-boxing-bytecode.md`](03c-internals-boxing-bytecode.md). There is no version of
`HashMap` that stores an `int`. The 33 above happens to be inside the wrapper cache, so no allocation
occurs; the 300 is outside it, so one 16-byte `Integer` is allocated. That asymmetry is
[`01a-the-wrapper-caches.md`](01a-the-wrapper-caches.md)'s subject.

#### Case 2 — generics generally

Anything with a type parameter has the same constraint. A `Reservation<T>`-shaped API, a
`Comparator<Integer>`, a `Function<Integer, Money>`: all reference-only.

```java
Comparator<Integer> byStakeMinorUnits = Comparator.naturalOrder();
Function<Integer, Money> toMoney =
        minorUnits -> new Money(BigDecimal.valueOf(minorUnits, 2), Currency.getInstance("GBP"));
```

This is the one case where the JDK's specialisation coverage is genuinely good, because
`java.util.function` was written from scratch in Java 8 with the problem in view. The primitive
variants exist precisely to keep the box out of a lambda that runs 2.8M times a day:

```java
IntFunction<Money> toMoneyFast =
        minorUnits -> new Money(BigDecimal.valueOf(minorUnits, 2), Currency.getInstance("GBP"));
IntPredicate isAboveDailyStakeCap = minorUnits -> minorUnits > 100_00;
ToLongFunction<Reservation> reservedMinorUnits = Reservation::minorUnits;
IntUnaryOperator bonusPortion = stake -> stake / 10;   // 10% of stake, rounded down
```

Note what each signature does: `IntFunction<R>` takes an `int` and returns a reference, so it removes
the argument box only. `ToLongFunction<T>` takes a reference and returns a `long`, so it removes the
return box only. `IntUnaryOperator` is primitive on both sides. There is no combination that removes
a box that was never there — the specialisation is per-position, and you pick the one whose primitive
side matches the hot side.

#### Case 3 — `Optional`

`Optional<T>` is generic, so `Optional<Integer>` is two objects: the `Optional` and the `Integer`.
`OptionalInt` is one object, holding an `int` field and a `boolean`.

The thing that actually matters is not the object count. It is that **`OptionalInt` cannot express
"present but null", because that state does not exist in its representation.** Where the only two
states you need are absent and present-with-a-number, `OptionalInt` is a strict improvement. Where
you genuinely have three states — the row is missing, the row is present with SQL NULL, the row is
present with a value — `OptionalInt` cannot model it and reaching for it forces you to smuggle the
third state somewhere else, usually into a sentinel. That is the failure in the second pitfall below.

Measured on JDK 21.0.7 with `javap`, `OptionalInt`'s entire surface is: `empty`, `of(int)`,
`getAsInt`, `isPresent`, `isEmpty`, `ifPresent(IntConsumer)`, `ifPresentOrElse`, `stream()`,
`orElse(int)`, `orElseGet(IntSupplier)`, `orElseThrow()`, `orElseThrow(Supplier)`, plus `equals`,
`hashCode`, `toString`. **There is no `map`, no `flatMap`, and no `filter`.** `stream()` is there —
added in Java 9, confirmed present in 21 — and is the standard bridge: `optionalInt.stream()` gives
you an `IntStream`, and `.boxed()` from there gives you a `Stream<Integer>` when you need the
reference world back.

**Interview:** *"When can you not avoid boxing?"* Whenever the value has to live in a generic type —
a collection, an `Optional`, a `Comparator`, a type parameter of your own — because erasure means a
type argument is always a reference type; and whenever `null` is a legitimate value, because no
primitive has a spare bit pattern that means absent.

#### Case 4 — nullable columns and the wire

A nullable `retry_count` on a document-verification row, a nullable `bonus_amount` on a ledger
projection, a JSON field that may be absent from a request body. Here the box is not overhead. **The
box is carrying information: the nullness is the point.** Removing it does not make the code faster,
it loses data.

This is the distinction worth taking out of this file. In cases 1 to 3 the box is a **cost** imposed
by erasure, and eliminating it is a pure win when a hatch applies. In case 4 the box is a
**representation choice**: `Integer` is the correct Java type for a column declared nullable, and
`int` is the correct type for a column declared `NOT NULL`. Choosing `int` for a nullable column is
not an optimisation, it is a modelling error, and the JDBC API will punish it silently:

```java
// WRONG for a nullable column: getInt maps SQL NULL to 0
int bonusMinorUnits = rs.getInt("bonus_amount");

// right, three acceptable forms
Integer bonusMinorUnits = (Integer) rs.getObject("bonus_amount");

int raw = rs.getInt("bonus_amount");
Integer bonus = rs.wasNull() ? null : raw;

// or: make the column NOT NULL DEFAULT 0 and keep the primitive honestly
```

`ResultSet.getInt` is specified to return 0 when the column value is SQL NULL — that is JDBC's
contract, not a driver quirk — so a NULL bonus and a genuine zero bonus arrive as the same `int`. In
this domain those are different facts: a client with no bonus grant and a client whose bonus is fully
consumed are in different states, and a report that conflates them is wrong.

For the mapping layer, guide **08 Spring Data JPA** covers entity field types against column
nullability and what happens when a `@Column(nullable = false)` disagrees with an `Integer` field;
guide **09 SQL databases** covers NULL semantics, three-valued logic, and why `NOT NULL DEFAULT 0` is
often the better schema. For the wire form — absent field versus `null` field versus zero, and
`Optional` in a DTO — guide **12 API design** is the place.

#### The escape hatches

| Generic form | Primitive form | What it saves | Where it stops working |
|---|---|---|---|
| `List<Integer>` | `int[]` | 20 → 4 bytes per element, measured (56,000,376 → 11,200,712 bytes at 2.8M, exactly 5.00×) | no `List` API, no growth, no `null`, no `remove`; you hand-manage capacity and a logical length |
| `List<Integer>` (growable) | `IntArrayList` (Eclipse Collections), `IntArrayList` (fastutil), `IntArrayList` (HPPC) | same 5× plus growth and a list API | a third-party dependency, a shading question, an API your reviewers must learn |
| `Stream<Integer>` | `IntStream` / `LongStream` / `DoubleStream` | measured 256 bytes **total** for `Arrays.stream(int[]).asLongStream().sum()`, independent of array length | no `groupingBy`, no `Collectors`, no `distinct` by extracted key, no `sorted(Comparator)`; only three widths exist |
| `Optional<Integer>` | `OptionalInt` | two objects → one; no cache dependence | no `map`, no `flatMap`, no `filter`; cannot represent present-but-null; `stream()` is the only bridge out |
| `Function<Integer, R>` | `IntFunction<R>` | the argument box in a hot lambda | only removes the primitive-side box; no variant for every arity and width combination |
| `Function<T, Long>` | `ToLongFunction<T>` | the return box | same |
| `Map<Integer, V>`, dense keys | `V[]` or `long[]` indexed by the key | measured 69.49 → 8 bytes per entry (see § 2) | requires a dense, bounded, non-negative key space and a known maximum |
| `Map<SomeEnum, V>` | `EnumMap` / `EnumSet` | array-backed, ordinal-indexed, no hashing, no boxing of the key | keys must be one enum type; see [`../enums/03c-internals-enumset-enummap.md`](../enums/03c-internals-enumset-enummap.md) |
| `Map<Integer, V>`, sparse keys | `Int2ObjectOpenHashMap` (fastutil), `IntObjectHashMap` (Eclipse Collections) | removes the key box and the per-entry `Node` | dependency; different iteration and `null`-handling semantics from `java.util` |
| `stream().reduce(0, Integer::sum)` | `Collectors.summingInt`, `IntStream.sum()`, `IntStream.summaryStatistics()` | measured 16.0 bytes per element → measured 216 bytes per call for `summaryStatistics()` over 2.8M | `summingInt` still returns a boxed `Integer` at the end — one box, not 2.8M |

Read the right-hand column as seriously as the middle one. Two rows in that table cost you a
dependency, four cost you API surface you may need, and one (`int[]`) costs you the ability to say
"absent". [`01g-the-cost-of-boxing.md`](01g-the-cost-of-boxing.md) derives the byte figures in the
middle column; they are not re-derived here.

### Diagram

No diagram for this concept: the material is a decision table and four independent forcing cases, and
the table above is already the clearer rendering of both.

### A concrete example

One computation, written three times. The domain is the daily stake-reservation roll-up: 2.8M
reservations a day, average value 4.20, held as minor units so the arithmetic stays integral. All
three versions are complete; the allocation figures after each were measured on JDK 21.0.7 with
`com.sun.management.ThreadMXBean.getThreadAllocatedBytes` over the same 2,800,000 inputs.

**Version 1 — the natural boxed form.**

```java
final class StakeReservationRollup {

    /** 2.8M reservations for one day, minor units, as they arrive from a JPA projection. */
    static long totalBoxed(List<Integer> stakeMinorUnits) {
        return stakeMinorUnits.stream()
                              .reduce(0, Integer::sum);
    }
}
```

Measured: **44,812,568 bytes** allocated for the reduction alone over 2.8M elements —
**16.004 bytes per element**, which is one 16-byte `Integer` per `Integer::sum` call. The 0.004
residue is the stream plumbing. The `List<Integer>` itself cost a further 56,000,376 bytes to hold,
measured, versus 11,200,712 for the equivalent `int[]`. Note that `reduce(0, Integer::sum)` boxes the
**accumulator**, and the accumulator leaves the wrapper cache on the second iteration and never comes
back, so the cache buys nothing at all here.

**Version 2 — the primitive form.**

```java
final class StakeReservationRollup {

    static IntSummaryStatistics summariseFast(int[] stakeMinorUnits) {
        return Arrays.stream(stakeMinorUnits).summaryStatistics();
    }

    static long totalFast(int[] stakeMinorUnits) {
        return Arrays.stream(stakeMinorUnits).asLongStream().sum();
    }
}
```

Measured, warmed to C2 and averaged over 100 calls on the same 2.8M array:
`summaryStatistics()` allocates **216 bytes per call**; `asLongStream().sum()` allocates **256 bytes
per call**. Both figures are **independent of array length** — they are the spliterator, the sink
chain and the one result object, and the traversal itself allocates nothing. That is the cleanest
single argument for a primitive stream: not "5× less memory", but *constant* allocation where the
boxed form is linear. `asLongStream()` is there for a reason — 2.8M reservations averaging 4.20 is
1,176,000,000 minor units, comfortably inside `int`, but a month is not, and `IntStream.sum()` returns
an `int` that overflows silently.

**Version 3 — where the primitive form stops being worth it.**

Now aggregate per client instead of globally. `IntStream` has no `groupingBy`, so the honest boxed
version is:

```java
final class StakeReservationRollup {

    /** clientIdIndex[i] and stakeMinorUnits[i] describe reservation i. */
    static Map<Integer, Integer> perClientBoxed(int[] clientIdIndex, int[] stakeMinorUnits) {
        return IntStream.range(0, stakeMinorUnits.length)
                        .boxed()
                        .collect(Collectors.groupingBy(
                                i -> clientIdIndex[i],
                                Collectors.summingInt(i -> stakeMinorUnits[i])));
    }
}
```

Measured over 2.8M reservations across 379,772 distinct clients: **166,081,984 bytes**, or **59.3
bytes per element**. The `.boxed()` is unavoidable — `Collectors` is a generic API and
`groupingBy` needs a reference key for the `HashMap` — so the primitive stream buys nothing past the
`boxed()` call, and the result map itself carries a boxed key and a boxed value per group.

The primitive answer only exists because the key space is dense and bounded: 380k monthly active
clients, mapped once to a contiguous index.

```java
final class StakeReservationRollup {

    /**
     * Requires clientIdIndex values in [0, clientCount). The mapping from ClientId to
     * a dense index is built once per day and reused; that is the price of this version.
     */
    static long[] perClientDense(int[] clientIdIndex, int[] stakeMinorUnits, int clientCount) {
        long[] totals = new long[clientCount];
        for (int i = 0; i < stakeMinorUnits.length; i++) {
            totals[clientIdIndex[i]] += stakeMinorUnits[i];
        }
        return totals;
    }
}
```

Measured with `clientCount = 380_000`: **3,040,016 bytes**, which is exactly
`380_000 × 8 + 16` — the `long[]` payload plus its 16-byte header, and nothing else. Against
166,081,984 that is a 54.6× reduction, and the loop is a linear scan with no hashing.

But look at what version 3-dense actually requires: a dense index, built and maintained somewhere
else, plus a reverse mapping to turn indices back into `ClientId`s for output, plus a decision about
what happens when a new client appears mid-day. If you have that structure already, take the
54.6×. If you do not, building it to save a one-off report's allocation is the wrong trade, and the
correct answer is either a primitive-keyed third-party map (which keeps the `int` key and drops the
`Node`) or simply accepting the box. Both are defensible; inventing a dense index for a report that
runs once a day is not.

### The gotcha

Two symmetrical mistakes, and the second is much more expensive than the first.

The small one: reaching for a primitive collection library at a few hundred elements. A
`Map<RestrictionKey, Integer>` of restriction counts for one client has at most ten entries; a
fastutil dependency buys nothing measurable and costs a shading question and an unfamiliar API in
every future review. Worse, small counts are inside the wrapper cache, so they allocate nothing at
all — measured, a 1,000,000-element `List<Integer>` of values all under 128 costs 4,000,040 bytes,
**4.00004 bytes per element, identical to `int[]`**, because only the references are new.

The large one, in the other direction: `Map<Integer, Integer>` as a 2.8M-entry index. Every entry is
two boxes plus a `HashMap.Node`, and the measured cost is in § 2 below. This is the shape that
actually shows up in a heap dump as the top retainer, and it is usually a cache someone added to a
service that was never sized against the 2.8M/day figure.

> **Definition.** Boxing is unavoidable exactly where the value must occupy a generic type argument
> or must be able to be `null`; every JDK escape hatch (`int[]`, `IntStream`, `OptionalInt`, the
> primitive functional interfaces) is a hand-written specialisation that exists only for the cases
> where neither of those is true.

## 2. Boxed keys in a hash table (`[X-REF 02]`)

`[X-REF 02]` A `HashMap<Integer, V>` does not store an `int` anywhere. Each entry is a
`HashMap.Node` object — 12-byte header, 4-byte cached `hash`, 4-byte `key` reference, 4-byte `value`
reference, 4-byte `next` reference, 28 bytes rounded up to **32** — plus the boxed key, plus a boxed
value if `V` is a wrapper, plus a 4-byte slot in the backing table. Three objects and a table slot
per logical `int` → `int` pair.

### Why it exists

`HashMap` predates generics and was written against `Object`. Its node has to hold references
because it holds anything; there is no specialisation path in the JDK for a primitive-keyed map,
because writing one means writing the whole class again for each width, and nobody did. This is the
single largest gap in the JDK's specialisation coverage and the main reason the third-party primitive
collection libraries exist at all.

### The mechanism

`Integer.hashCode()` **returns the value itself** — measured on JDK 21.0.7,
`Integer.valueOf(-7).hashCode() = -7` and `Integer.valueOf(1).hashCode() = 1`. That means sequential
integer keys produce sequential hash codes, which is why `HashMap` applies its own spreading step
(`h ^ (h >>> 16)`) before masking to the table index: without it, keys differing only in their high
16 bits would collide in every table smaller than 65,536 buckets. Guide **02 Java collections** owns
the spreading function, the treeify threshold, and the resize protocol; the point here is only that
the key's box is on the allocation path and its `hashCode` is free.

Measured on JDK 21.0.7, a `HashMap<Integer, Integer>` presized to 4,194,304 buckets and filled with
2,800,000 entries (keys 0 to 2,799,999, values 100 to 999) allocated **194,578,848 bytes** —
**69.49 bytes per entry**. The decomposition:

| Component | Count | Bytes each | Total |
|---|---|---|---|
| backing `Object[]` table | 4,194,304 slots + header | 4 | 16,777,232 |
| `HashMap.Node` | 2,800,000 | 32 | 89,600,000 |
| key `Integer` (all outside the cache) | 2,800,000 | 16 | 44,800,000 |
| value `Integer` (values 100–999) | ~2,713,000 | 16 | ~43,408,000 |
| value `Integer`, cached (values 100–127) | ~87,000 | 0 | 0 |
| **derived total** | | | **~194,585,232** |

That derived figure lands within 0.004% of the measured 194,578,848, and the reason the cached-value
row is there at all is that roughly 28 of the 900 possible values (100 through 127) fall inside
`IntegerCache`, so about 3.1% of the value boxes are shared instances and cost nothing. The
arithmetic only closes if you account for them, which is a good sign that the decomposition is real
rather than fitted.

**Insight:** the box is the cheapest part of that 69.49 bytes. Two 16-byte wrappers are 32 of it; the
`Node` is another 32, and the table slot is 4. So eliminating only the boxing — with a
`Reference2IntMap`, say — halves the cost at best, while replacing the hash table with an array
indexed by a dense key removes all three at once. Reach past the box to the container.

Against that: two parallel `int[]`s cost 8 bytes per entry, and a `long[]` indexed by a dense key
costs 8. The array-backed answer when the key space is a dense enum rather than an `int` is
`EnumMap` and `EnumSet` — ordinal-indexed arrays and bit vectors, no hashing, no boxing of the key at
all, which is why `Set<Restriction>` modelled as an `EnumSet<RestrictionType>` is both smaller and
faster than any `HashSet` you could write. See
[`../enums/03c-internals-enumset-enummap.md`](../enums/03c-internals-enumset-enummap.md).

### Diagram

No diagram for this concept: the evidence is the byte-decomposition table above, which is already the
picture.

### A concrete example

```java
final class DailyReservationIndex {

    /** Boxed: 69.49 measured bytes per entry at 2.8M entries. */
    static Map<Integer, Integer> boxedIndex(int[] stakeMinorUnits) {
        Map<Integer, Integer> byReservationOrdinal = new HashMap<>(4_194_304);
        for (int i = 0; i < stakeMinorUnits.length; i++) {
            byReservationOrdinal.put(i, stakeMinorUnits[i]);
        }
        return byReservationOrdinal;
    }

    /** Dense key: 4 measured bytes per entry, and no hashing. */
    static int[] denseIndex(int[] stakeMinorUnits) {
        return stakeMinorUnits.clone();
    }

    /** The honest middle: an EnumMap where the key space really is an enum. */
    static EnumMap<RestrictionType, Integer> activeRestrictionCounts(List<Restriction> restrictions) {
        EnumMap<RestrictionType, Integer> counts = new EnumMap<>(RestrictionType.class);
        for (Restriction restriction : restrictions) {
            counts.merge(restriction.type(), 1, Integer::sum);
        }
        return counts;
    }
}
```

The third method still boxes its values, and that is correct: there are ten `RestrictionType`
constants, the counts are single digits and therefore inside the wrapper cache, and the `EnumMap`'s
array is ten slots long. Nothing here is worth optimising, and a `Reference2IntMap` would make it
worse to read for zero measurable gain.

### The gotcha

`Map<Integer, Integer>` is the shape people reach for when the key is "an id". If the id is a
`ClientId` wrapping a `UUID`, boxing is not your problem — you are storing a reference either way.
If the id is genuinely an `int` and the map is large, the 69.49 bytes per entry is the number to put
in the design document, because 2.8M entries is 194 MB and services get OOM-killed over less.

**Interview:** *"What would you use instead of `List<Integer>` for a million values?"* An `int[]` if
the size is known and no element can be absent — measured 4 bytes per element against 20, exactly 5×.
If it must grow, a primitive list from Eclipse Collections or fastutil. If I only need to reduce over
it, `Arrays.stream(int[])` and a primitive terminal operation, which allocates a measured constant
216 to 256 bytes regardless of length. And I would say what I give up: `null`, the `List` API, and
`Collectors`.

> **Definition.** A boxed key in a `HashMap` costs a measured 69.49 bytes per `int` → `int` entry on
> JDK 21.0.7 — a 32-byte `Node`, two 16-byte wrappers, and a table slot — which is why a dense key
> space belongs in an array and a dense enum key space belongs in an `EnumMap`.

## 3. The decision: three questions, not a rule

The escape hatches are not a style guide. Ask three questions in order, and stop at the first one
that answers.

| Question | Answer | What follows |
|---|---|---|
| 1. Is `null` a legitimate value? | yes | Keep the box. It is carrying information, not overhead. No hatch applies. `int[]` plus a sentinel is a bug, not an optimisation. |
| | no | Continue. |
| 2. How many elements, and how hot? | fewer than a few thousand, or cold | Keep the plain collection. At 1M cached values the measured cost is 4.00004 bytes per element — the same as `int[]`. Readability wins. |
| | millions, or in a per-request path | Continue. |
| 3. What do you actually do with it? | reduce, sum, min/max, statistics | `Arrays.stream(int[])` and a primitive terminal: measured 216–256 bytes total, constant in length. |
| | random access by dense index | `int[]` / `long[]`: measured 4 and 8 bytes per element. |
| | group, sort by comparator, `distinct` by key | You are boxing again. Choose deliberately between a primitive-keyed third-party map and accepting the box, and write down which. |

Two things that are not on that list, deliberately. **Escape analysis** already deletes boxes that do
not escape their method — measured, a non-escaping two-box method allocated **0 bytes** per iteration
by default on JDK 21.0.7, and 32 bytes per iteration with `-XX:-DoEscapeAnalysis`. So a box in a
short private method that never leaves is very often free, and optimising it by hand is wasted work;
[`03d-internals-escape-analysis.md`](03d-internals-escape-analysis.md) shows exactly where it fails.
And **`null`-safety**: the moment you keep the box, you own the unboxing NPE, which is
[`01c-unboxing-null.md`](01c-unboxing-null.md)'s subject.

That closes the BASICS tier for wrappers and boxing. From here the internals files stop building the
model and go to the source: [`03-internals-boxing.md`](03-internals-boxing.md) walks
`Integer.valueOf` line by line with `IntegerCache`'s full field set,
[`03a-internals-cache-configuration-and-cds.md`](03a-internals-cache-configuration-and-cds.md) traces
the cache-fill path and the archived-subgraph decision,
[`03c-internals-boxing-bytecode.md`](03c-internals-boxing-bytecode.md) reads the
`invokestatic`/`invokevirtual` pair instruction by instruction,
[`03d-internals-escape-analysis.md`](03d-internals-escape-analysis.md) covers scalar replacement and
the shapes that defeat it, [`03e-internals-wrapper-memory.md`](03e-internals-wrapper-memory.md) does
the 16-byte and 24-byte arithmetic against the object header, and
[`03f-internals-monitors-and-valhalla.md`](03f-internals-monitors-and-valhalla.md) explains why
`synchronized` on a cached box is a correctness bug and what Valhalla replaces all of this with.

## Pitfalls

### Reading a nullable column with `getInt`

**Wrong**

```java
// bonus_amount is declared NULL-able: a client with no bonus grant has no row value
static int bonusMinorUnits(ResultSet rs) throws SQLException {
    return rs.getInt("bonus_amount");
}
// client with no bonus grant     -> 0
// client whose bonus is consumed -> 0
// indistinguishable
```

`ResultSet.getInt` is specified to return 0 when the column value is SQL NULL. No exception, no
warning, no log line. The bug surfaces weeks later as a reconciliation break, because
`PROMOTIONAL_EXPENSE` reversals were computed against a bonus of zero that was really absent.

**Right**

```java
static Integer bonusMinorUnits(ResultSet rs) throws SQLException {
    return (Integer) rs.getObject("bonus_amount");     // null stays null
}

// or, keeping the primitive read and asking explicitly
static Integer bonusMinorUnitsChecked(ResultSet rs) throws SQLException {
    int value = rs.getInt("bonus_amount");
    return rs.wasNull() ? null : value;
}
```

`getObject` returns `null` for SQL NULL, so the box carries the nullness. `wasNull()` is the other
sanctioned form and must be called immediately after the getter, before any other column read. The
third option is a schema change: `NOT NULL DEFAULT 0` makes `int` the honest type. Guide **09 SQL
databases** covers when that is the right call.

**Why people believe it:** the primitive getters are the ones you learn first, the column is an
integer column, and `getInt` returns `int`, so it looks like the matching accessor. Nothing in the
signature hints that NULL has been silently folded into a value, and the default value for `int` is
0 everywhere else in Java, so 0 feels like "no value" rather than a real datum.

### Replacing `List<Integer>` with `int[]` where an element can be absent

**Wrong**

```java
// retry_count per document requirement; a requirement never attempted has no count
static int[] retryCounts(List<DocumentRequirement> requirements) {
    int[] counts = new int[requirements.size()];
    for (int i = 0; i < counts.length; i++) {
        Integer attempted = requirements.get(i).retryCount();
        counts[i] = (attempted == null) ? -1 : attempted;   // -1 means "never attempted"
    }
    return counts;
}
```

The sentinel is the bug. `-1` is not in the domain of retry counts today, so this works — until
someone computes `sum(counts)` for a dashboard, or a later change makes `-1` mean "reset by an
operator", or the same idiom gets copied to `bonus_amount` where negative values are a real
clawback. A sentinel is an undocumented second type crammed into the first one's bit patterns.

**Right**

```java
// keep the box: nullness is information here
static List<Integer> retryCounts(List<DocumentRequirement> requirements) {
    return requirements.stream().map(DocumentRequirement::retryCount).toList();
}

// or, if the array really is required for size reasons, carry presence separately
record RetryCounts(int[] counts, BitSet attempted) {
    OptionalInt countFor(int index) {
        return attempted.get(index) ? OptionalInt.of(counts[index]) : OptionalInt.empty();
    }
}
```

The second form is the honest primitive version: `int[]` for the values, a `BitSet` for presence,
1 bit per element instead of 16 bytes, and `OptionalInt` at the boundary because now there really are
only two states. Note that `toList()` on a `Stream<Integer>` produces an immutable list and permits
`null` elements from `map`, which is what you want here.

**Why people believe it:** "avoid boxing" is repeated as a rule without its precondition. The
precondition is that the value cannot be absent. Once absence is possible, `int[]` is not a cheaper
representation of the same information — it is a lossy one, and the sentinel is the loss made
visible.

### Adding a primitive-collections dependency for a few hundred values

**Wrong**

```java
// ten RestrictionType constants, single-digit counts, one client
Object2IntOpenHashMap<RestrictionType> counts = new Object2IntOpenHashMap<>();
for (Restriction restriction : clientRestrictions) {
    counts.addTo(restriction.type(), 1);
}
```

A new dependency, a shading decision in the shaded artifact, an API nobody on the team has seen, and
`addTo` semantics that a reviewer has to look up — to save at most ten boxes that were never
allocated in the first place.

**Right**

```java
EnumMap<RestrictionType, Integer> counts = new EnumMap<>(RestrictionType.class);
for (Restriction restriction : clientRestrictions) {
    counts.merge(restriction.type(), 1, Integer::sum);
}
```

An `EnumMap` is a ten-slot array indexed by ordinal, the keys are the enum constants themselves, and
every count is a single-digit `Integer` that comes straight from `IntegerCache` — so this allocates
the array and nothing else. Measured evidence that small values are free: a 1,000,000-element
`List<Integer>` where every value is under 128 costs **4,000,040 bytes, 4.00004 per element**,
identical to an `int[]` of the same length, because only the references are new.

**Why people believe it:** the measured 5× figure for `List<Integer>` versus `int[]` is real and
memorable, and it gets applied without the second measured fact next to it — that the 5× only
materialises for values outside the cache, at a scale where 16 bytes per element is a number anyone
cares about. At 300 elements the whole difference is under 5 KB.

### Reaching for `OptionalInt` when the value has three states

**Wrong**

```java
// the row may be missing; if present, bonus_amount may itself be SQL NULL
static OptionalInt bonusMinorUnits(long ledgerEntryId) {
    Integer value = repository.findBonusAmount(ledgerEntryId);   // null for both cases
    return value == null ? OptionalInt.empty() : OptionalInt.of(value);
}
```

`OptionalInt.empty()` now means two different things, and the caller cannot tell "no such ledger
entry" from "ledger entry exists, bonus not applicable". The distinction matters: the first is a
lookup failure worth logging, the second is a normal state.

**Right**

```java
sealed interface BonusLookup {
    record NoSuchEntry(long ledgerEntryId) implements BonusLookup {}
    record NotApplicable(long ledgerEntryId) implements BonusLookup {}
    record Amount(long ledgerEntryId, int minorUnits) implements BonusLookup {}
}

static BonusLookup bonusMinorUnits(long ledgerEntryId) {
    if (!repository.exists(ledgerEntryId)) {
        return new BonusLookup.NoSuchEntry(ledgerEntryId);
    }
    Integer value = repository.findBonusAmount(ledgerEntryId);
    return value == null
            ? new BonusLookup.NotApplicable(ledgerEntryId)
            : new BonusLookup.Amount(ledgerEntryId, value);
}
```

Three states get three cases, and a pattern-matching `switch` over the sealed interface makes the
caller handle all of them. `OptionalInt` stays for the two-state case where it is a strict
improvement — `IntStream.max()`, an index search, a parsed count with a real default.

**Why people believe it:** `OptionalInt` is presented as the primitive-friendly `Optional`, and it is,
but the specialisation quietly removed a state as well as a box. `Optional<Integer>` has three
representable outcomes (empty, present-with-`null` if you are careless enough to construct it, and
present-with-a-value) where `OptionalInt` has two, and the missing one is exactly the one nullable
columns produce.

## Cheat sheet

| Thing | Fact (Java 21 LTS) |
|---|---|
| Root cause of all forced boxing | erasure: a type argument is always a reference type |
| Erasure rule | type variable → leftmost bound, or `Object`; a primitive can be neither |
| Why no `List<int>` | Java 5 generics chose erasure for binary compatibility with pre-generics `java.util` |
| Forced case 1 | collections — every JDK collection is generic |
| Forced case 2 | generics generally — `Comparator<Integer>`, `Function<Integer, R>`, your own `T` |
| Forced case 3 | `Optional<T>` |
| Forced case 4 | nullable columns and absent wire fields — here the box carries information |
| Primitive stream types | exactly three: `IntStream`, `LongStream`, `DoubleStream` |
| `OptionalInt` surface | no `map`, no `flatMap`, no `filter`; has `stream()` since Java 9 |
| `OptionalInt` limitation | cannot represent present-but-null; only two states exist |
| `ResultSet.getInt` on SQL NULL | returns **0**, silently; use `getObject` or `wasNull()` |
| `int[]` vs `List<Integer>`, 2.8M | 11,200,712 vs 56,000,376 bytes measured — exactly **5.00×** |
| `List<Integer>` per element | 20 bytes = 4-byte compressed reference + 16-byte `Integer` |
| `List<Long>` per element | 28 bytes = 4-byte reference + 24-byte `Long` |
| `List<Integer>` of cached values | measured **4.00004** bytes per element — same as `int[]` |
| Boxed accumulator | measured **24 bytes per iteration**; cache never helps, the total leaves it |
| `stream().reduce(0, Integer::sum)` | measured **16.004** bytes per element over 2.8M |
| `Arrays.stream(int[]).asLongStream().sum()` | measured **256 bytes per call**, constant in length |
| `Arrays.stream(int[]).summaryStatistics()` | measured **216 bytes per call**, constant in length |
| `HashMap<Integer, Integer>` per entry | measured **69.49 bytes** at 2.8M entries |
| `HashMap.Node` size | 12 header + 4 hash + 4 key + 4 value + 4 next = 28 → **32** bytes |
| `long[]` indexed by dense key | measured 3,040,016 bytes for 380,000 slots = 8 per entry + 16 header |
| `Integer.hashCode()` | returns the value itself; `HashMap` spreads with `h ^ (h >>> 16)` |
| Dense enum key | `EnumMap` / `EnumSet` — ordinal-indexed array, no hashing, no key box |
| Argument-side hatch | `IntFunction<R>`, `IntPredicate`, `IntUnaryOperator` |
| Return-side hatch | `ToLongFunction<T>`, `ToIntFunction<T>`, `ToDoubleFunction<T>` |
| `IntStream` gaps | no `groupingBy`, no `Collectors`, no `sorted(Comparator)`, no `distinct` by key |
| Third-party primitive collections | fastutil, Eclipse Collections, HPPC — cost: dependency, shading, unfamiliar API |
| Escape analysis, non-escaping box | measured **0 bytes** per iteration by default; 32 with `-XX:-DoEscapeAnalysis` |
| Decision question 1 | can the value be `null`? If yes, keep the box, full stop |
| Decision question 2 | how many, and how hot? Under a few thousand: keep the collection |
| Decision question 3 | what operation? Reduce → primitive stream; dense index → array; group → accept the box |
| Valhalla | value classes; would remove the need for hand-written specialisation. Not in 21 |

## Self-test

**Q1.** Why can you not write `List<int>` in Java 21, and is that a performance decision?

<details><summary>Answer</summary>

No, it is a compatibility decision whose performance consequences we live with. Generics arrived in
Java 5 and had to be binary-compatible with the pre-generics `java.util`, so the same class file for
`Vector` or `ArrayList` had to serve callers that used type arguments and callers that did not. The
mechanism chosen was erasure: the compiler type-checks with the type argument, then replaces each
type variable with its leftmost bound — or `Object` when it has none — and inserts casts at the use
sites. A primitive type is not a subtype of `Object` and cannot be a bound, so it cannot appear as a
type argument. Everything downstream follows: collections box, `Optional` boxes, `Comparator<Integer>`
boxes, and the JDK's answer has been to hand-write primitive specialisations (`int[]`, `IntStream`,
`OptionalInt`, the primitive functional interfaces) case by case. Project Valhalla is the attempt to
fix the root cause rather than keep hand-writing copies.

</details>

**Q2.** A colleague replaces `List<Integer> retryCounts` with `int[] retryCounts`, encoding "never
attempted" as `-1`. What is wrong with that?

<details><summary>Answer</summary>

The nullness was information, and `int` has no bit pattern that means absent, so the change is lossy
rather than cheaper. `-1` is now an undocumented second type crammed into the first one's value
range: any `sum`, `min`, or `average` over the array is wrong; any later change that makes `-1` a
legitimate retry count silently breaks the encoding; and the idiom gets copied to fields like
`bonus_amount` where negative values are real clawbacks. The rule "avoid boxing" has a precondition —
the value cannot be absent — and this case violates it. If the array is genuinely required for size
reasons, carry presence separately: an `int[]` plus a `BitSet`, one bit per element instead of 16
bytes, and hand out an `OptionalInt` at the boundary where there really are only two states.

</details>

**Q3.** What does `Arrays.stream(int[]).asLongStream().sum()` allocate over a 2.8M-element array, and
why is that the strongest argument for primitive streams?

<details><summary>Answer</summary>

Measured on JDK 21.0.7, warmed to C2 and averaged over 100 calls: **256 bytes per call**, and
`summaryStatistics()` on the same array is 216 bytes per call. Both are **independent of array
length** — the allocation is the spliterator, the sink chain, and the one result object; the
traversal itself allocates nothing. Compare the boxed equivalent, `list.stream().reduce(0,
Integer::sum)`, which measured 44,812,568 bytes over the same 2.8M elements, or 16.004 bytes per
element. The point is not the ratio, which depends on length; it is that the primitive form is
**constant** where the boxed form is **linear**. That is what makes it safe to run on a path that
handles 2.8M reservations a day. The `asLongStream()` matters separately: `IntStream.sum()` returns an
`int` and overflows silently once you aggregate more than a day.

</details>

**Q4.** How much does one entry of a `HashMap<Integer, Integer>` cost, and where does the number come
from?

<details><summary>Answer</summary>

Measured on JDK 21.0.7 with `getThreadAllocatedBytes`, a map presized to 4,194,304 buckets and filled
with 2,800,000 entries allocated 194,578,848 bytes — **69.49 bytes per entry**. It decomposes as: a
4-byte compressed reference per table slot (4,194,304 slots plus a 16-byte array header, 16,777,232
bytes, and note that is the presized table, not the entry count); a `HashMap.Node` per entry at 32
bytes (12-byte header, 4-byte cached hash, 4-byte key reference, 4-byte value reference, 4-byte
`next` reference, 28 rounded up to a multiple of 8); a 16-byte `Integer` for the key; and a 16-byte
`Integer` for the value except where the value falls inside `IntegerCache`. In the measured run the
values ranged 100 to 999, so about 28 of 900 possible values were cached, roughly 87,000 of 2.8M
entries, and the derived total closes to within 0.004% of the measurement only if you account for
them. Three objects and a table slot per logical `int` → `int` pair.

</details>

**Q5.** When is boxing *not* a cost to be eliminated?

<details><summary>Answer</summary>

When `null` is a legitimate value — that is, when the box is the representation rather than the
overhead. A nullable `retry_count` or `bonus_amount` column, an absent JSON field, a lookup that may
find nothing: in all of those, `Integer` is the correct Java type for a nullable column and `int` is
the correct type for a `NOT NULL` column, and choosing `int` for the nullable one is a modelling
error, not an optimisation. JDBC punishes it silently — `ResultSet.getInt` is specified to return 0
for SQL NULL, so an absent bonus and a genuine zero bonus arrive identical. Use `getObject` into an
`Integer`, or `getInt` immediately followed by `wasNull()`, or change the schema to `NOT NULL DEFAULT
0` and keep the primitive honestly. Two other cases where the box costs nothing worth chasing: values
inside `IntegerCache`, where a measured 1M-element `List<Integer>` costs 4.00004 bytes per element,
identical to `int[]`; and boxes that do not escape their method, which escape analysis deletes
outright — measured 0 bytes per iteration by default.

</details>

**Q6.** `IntStream` has no `groupingBy`. What do you do when you need a per-client total over 2.8M
reservations?

<details><summary>Answer</summary>

You accept that you are boxing again, and then choose deliberately. `Collectors` is a generic API and
`groupingBy` needs a reference key for its `HashMap`, so the pipeline has to go through `.boxed()`
and the primitive stream buys nothing past that call. Measured over 2.8M reservations across 379,772
clients, an `IntStream.range` pipeline through `boxed()` into `groupingBy` with a `summingInt`
downstream allocated
166,081,984 bytes, 59.3 per element. The primitive alternative only exists if the key space is dense
and bounded: map each `ClientId` to a contiguous index once, then accumulate into a
`long[clientCount]`, which measured 3,040,016 bytes for 380,000 clients — exactly the payload plus a
16-byte header, a 54.6× reduction with no hashing at all. But that requires the index, a reverse
mapping for output, and a policy for clients appearing mid-day. If you already have that structure,
take it. If not, the honest choices are a primitive-keyed third-party map (fastutil's
`Int2LongOpenHashMap`, Eclipse Collections' equivalent), which drops the key box and the `Node`, or
simply paying for the boxes and writing down that you decided to.

</details>

**Q7.** Name three JDK escape hatches and, for each, the thing it takes away.

<details><summary>Answer</summary>

`int[]` instead of `List<Integer>`: takes 20 bytes per element down to 4, measured exactly 5.00× at
2.8M elements — and takes away `null`, the entire `List` API, and automatic growth, so you hand-manage
capacity and a logical length. `IntStream` instead of `Stream<Integer>`: makes allocation constant
rather than linear, a measured 216 to 256 bytes per traversal — and takes away `Collectors`,
`groupingBy`, `sorted(Comparator)` and `distinct` by an extracted key, and only exists for three
widths. `OptionalInt` instead of `Optional<Integer>`: two objects become one — and takes away `map`,
`flatMap`, `filter`, and, most importantly, the ability to represent present-but-null, so it cannot
model a nullable column that may also be missing. A fourth if pressed: `EnumMap`/`EnumSet` instead of
`HashMap`/`HashSet` with enum keys, which becomes an ordinal-indexed array or a bit vector with no
hashing and no key box — and takes away the ability to mix key types or use `null` keys.

</details>

**Q8.** Why are there exactly three primitive stream types rather than eight?

<details><summary>Answer</summary>

Because each one is a hand-written copy. Erasure means the JDK cannot express a generic stream over a
primitive, so `IntStream`, `LongStream` and `DoubleStream` are three separate interface hierarchies
with three separate pipeline implementations, three sets of spliterators, three sets of functional
interfaces, and three `SummaryStatistics` classes. That is a large amount of duplicated code to
maintain, so the Java 8 authors triaged to the three widths that carry real numerical work.
`boolean`, `byte`, `short` and `char` streams do not exist, and the standard workaround is to use
`IntStream` and cast at the boundary — which is exactly what `String.chars()` does, returning an
`IntStream` of UTF-16 code units. The same triage explains the ragged coverage everywhere else: there
is no primitive-keyed map in `java.util` at all, which is the entire reason fastutil, Eclipse
Collections and HPPC exist.

</details>

## Open questions

- `ResultSet.getInt` returning 0 for SQL NULL is stated here from the JDBC specification and javadoc,
  not measured in this run — this file's measurements were all taken against in-memory data
  structures, with no database in the environment. What would settle it: running the snippet against
  a real driver (for example H2 or PostgreSQL) with a nullable column and asserting both the returned
  `0` and `wasNull() == true`.
- The third-party primitive collection figures are not quantified anywhere in this file, only their
  qualitative benefit (no key box, no `HashMap.Node`) and their costs. No fastutil, Eclipse
  Collections or HPPC artifact was on the classpath in this environment. What would settle it: the
  same `getThreadAllocatedBytes` harness run against `Int2IntOpenHashMap` at 2,800,000 entries, for a
  direct comparison with the measured 69.49 bytes per entry for `HashMap<Integer, Integer>`.
- The claim that `Collectors.summingInt` boxes only its final result, not each element, follows from
  its `IntSummaryStatistics`-style accumulator being a mutable primitive holder, but the per-element
  allocation was not isolated from the surrounding `groupingBy` in the 59.3-bytes-per-element
  measurement. What would settle it: a `summingInt` collector measured on its own against a
  `reducing(0, Integer::sum)` collector over the same 2.8M input.

---

**Leaves covered:** 1.9.20 (1 leaf)
**Leaves deferred:** none
**Diagrams included:** none
**Target version:** Java 21 LTS
**Lines:** 851
