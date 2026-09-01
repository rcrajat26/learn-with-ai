# 04 Modern Java — Streams — INTERNALS (§3.4)

**Target version: Java 21 LTS.** | **Part 3 of 5** | [Index](../00-index.md)
Previous: [Streams — internals pipeline](08-internals-pipeline.md) · Next: [Streams — internals parallel execution](10-internals-parallel-execution.md)

## Hierarchy — where `Spliterator` sits

Every stream, sequential or parallel, is driven by exactly one `Spliterator`. The pipeline (guide
08) wraps sinks around it; the terminal operation (`evaluate`) walks it; the parallel engine
(guide 10) recursively splits it. Nothing in `java.util.stream` traverses a collection directly —
every source, from `ArrayList` to `Files.lines`, is adapted into a `Spliterator` first, and the
whole story of "why does this parallelise well and that one doesn't" is the story of what each
type's `Spliterator` can and cannot report about itself.

| Family | Members | Splits by | Reports `SUBSIZED`? |
|---|---|---|---|
| Index-addressable | `ArrayList`, arrays (`Arrays.spliterator`) | index range, binary halving | Yes |
| Table-addressable | `HashMap`, `HashSet` | bucket-table range | No — `SIZED` only |
| Link-addressable | `LinkedList` | doubling batch pulled by traversal | No |
| Iterator-only | `Files.lines`, any hand-rolled `Iterator` source, most `Iterable`s without a custom spliterator | doubling batch pulled by traversal (same mechanism as `LinkedList`, different implementation class) | No |
| Hand-written | anything built on `AbstractSpliterator` / a custom class | whatever you implement | Only if you implement `trySplit` to report it |

This table is the spine of the whole file: everything below is either explaining one row of it in
depth, or explaining the interface every row implements.

---

## 1. The `Spliterator` interface

**Mental model.** A `Spliterator` is a *cursor with a size estimate and a can-I-be-cut-in-half
button*. `Iterator` gives you `hasNext`/`next` — pull one element, know nothing about how many
remain, and no way to hand half of yourself to another thread. `Spliterator` adds exactly three
things on top of that pull model: an estimate of how much is left (`estimateSize`), a way to
partition into two "spliterate"-able pieces (`trySplit`), and a self-description of what
guarantees the source makes (`characteristics`). Nothing more. It is not a data structure — it is
an adapter that a source hands over once, and it is consumed exactly once, whether sequentially or
in parallel.

**Why it exists.** Before Java 8, parallel decomposition over a `Collection` had no standard
vocabulary. Every hand-rolled parallel algorithm invented its own splitting scheme: "walk the
`ArrayList` by index range," "walk the `LinkedList` by counting nodes," "you can't split a plain
`Iterator` at all, so wrap it in a queue and have worker threads drain it." `Spliterator` (JEP
"Stream API," delivered in Java 8 alongside `java.util.stream`) standardises that vocabulary so
the Fork/Join-based parallel stream engine (guide 10) can drive *any* source — a collection, an
array, an I/O channel, a generator — through one interface, without knowing anything about the
concrete type underneath.

**When to reach for it, and when not.** You almost never implement `Spliterator` to consume a
stream — `Iterator` remains the right tool for ordinary sequential iteration, and every
`Collection.spliterator()` default method already gives you one built on the collection's
`Iterator` for free. You implement `Spliterator` directly only when you are **authoring a new
source** that must parallelise well: a custom collection, a bounded generator, a wrapper over an
external resource with a natural range decomposition. If your source has no natural way to report
size or split cheaply, do not fight it — `Spliterators.spliteratorUnknownSize` wrapping your
`Iterator` is the honest answer, and §6 of this file explains exactly what you give up by doing
that.

**How it works — the eight methods.** From `java.util.Spliterator<T>`, quoted and explained line
by line:

```java
public interface Spliterator<T> {
    boolean tryAdvance(Consumer<? super T> action);
    default void forEachRemaining(Consumer<? super T> action) {
        do { } while (tryAdvance(action));
    }
    Spliterator<T> trySplit();
    long estimateSize();
    default long getExactSizeIfKnown() {
        return (characteristics() & SIZED) == 0 ? -1L : estimateSize();
    }
    int characteristics();
    default boolean hasCharacteristics(int characteristics) {
        return (characteristics() & characteristics) == characteristics;
    }
    default Comparator<? super T> getComparator() {
        throw new IllegalStateException();
    }
}
```

- `tryAdvance(Consumer<? super T> action)` — if an element remains, apply `action` to it and
  return `true`; otherwise return `false` and do nothing. This is the fundamental single-step
  primitive; everything else is built in terms of it or replaces it with a bulk equivalent.
- `forEachRemaining(Consumer<? super T> action)` — the default implementation shown above is
  exactly "call `tryAdvance` in a loop until it returns `false`." Every concrete spliterator you
  will meet in the JDK **overrides** this with a bulk-traversal loop over its native structure
  (an index `for` loop for `ArraySpliterator`, a `while (node != null)` walk for `LinkedList`'s)
  because the default's per-element `Consumer` dispatch and loop-exit check cost real cycles at
  stream-scale volumes; the default exists only as a correctness fallback for a spliterator that
  implements nothing but `tryAdvance`.
- `trySplit()` — attempts to carve off a piece of this spliterator's remaining elements and return
  a new `Spliterator` covering that piece, leaving `this` covering the rest. Returns `null` if the
  spliterator cannot or should not be split further. Full treatment in §3.
- `estimateSize()` — the spliterator's best guess at how many elements `forEachRemaining` would
  encounter if called right now. It is a guess by contract, not a promise — a `Spliterator` over a
  `Stream.generate(...)` source rightly returns `Long.MAX_VALUE` here, meaning "unbounded, don't
  ask."
- `getExactSizeIfKnown()` — the default shown above is precisely the contract in code: if `SIZED`
  is not one of your reported characteristics, this returns `-1` regardless of what
  `estimateSize()` says, because `SIZED` is the only thing that promises `estimateSize()` is exact
  rather than a heuristic.
- `characteristics()` — an `int` bitmask, `OR`-ed together from the eight constants in §2. This is
  the self-description the whole pipeline (`AbstractPipeline`, guide 08) reads to decide which
  intermediate operations can be optimised away or skipped, and it is the input to
  `StreamOpFlag`'s combination logic.
- `hasCharacteristics(int characteristics)` — a convenience bitmask test; the default shown above
  is exactly `(characteristics() & characteristics) == characteristics`, i.e. "are *all* of these
  bits set," not "is any one of them set." Callers almost always call this rather than
  hand-rolling the mask arithmetic.
- `getComparator()` — throws `IllegalStateException` unless the spliterator reports `SORTED`; when
  it does report `SORTED`, this returns the `Comparator` that explains the order (or `null` if the
  natural ordering applies). `Stream.sorted()` reads this to decide whether it can skip sorting
  entirely (§7, characteristics-to-optimisation map).

**Example — QuizStakes.** A minimal, complete look at every method firing on a small, concrete
source: the 95,000 `DEP-301 CAPTURED` card deposits captured in one day, held as a plain
`ArrayList<CardDeposit>`.

```java
record CardDeposit(String depositId, java.math.BigDecimal amount, String statusCode) {}

List<CardDeposit> cardDeposits = loadCapturedCardDeposits(); // size 95_000, DEP-301 CAPTURED
Spliterator<CardDeposit> spliterator = cardDeposits.spliterator();

System.out.println(spliterator.estimateSize());              // 95000
System.out.println(spliterator.getExactSizeIfKnown());       // 95000 — SIZED is set, so this is exact
System.out.println(spliterator.characteristics());           // ORDERED | SIZED | SUBSIZED, as an int
System.out.println(spliterator.hasCharacteristics(
        Spliterator.SIZED | Spliterator.SUBSIZED));           // true

Spliterator<CardDeposit> prefixHalf = spliterator.trySplit(); // covers roughly indices 0..47_499
long total = 0;
if (prefixHalf != null) total += prefixHalf.estimateSize();  // ~47_500
total += spliterator.estimateSize();                          // ~47_500 remaining in the original
```

**The gotcha.** `tryAdvance` and `forEachRemaining` **consume** the spliterator — there is no
"peek" and no reset. Once you have called either, the elements you pulled are gone from this
spliterator forever; the only way to see them again is if you kept a reference to a `trySplit()`
result taken *before* you started pulling. This is the same one-shot discipline the stream
pipeline itself enforces (guide 08's `MSG_STREAM_LINKED`/`MSG_CONSUMED` discussion) — a
`Spliterator` is exactly as single-use as the `Stream` it backs, because it *is* the thing the
stream is backed by.

> **Definition:** `Spliterator<T>` is a single-use, splittable, self-describing element source —
> `Iterator` plus a size estimate, a partitioning operation, and a characteristics bitmask — and it
> is the one abstraction every stream source, sequential or parallel, is adapted into before the
> pipeline ever touches it.

---

## 2. The eight characteristics

**Mental model.** The characteristics bitmask is the spliterator's sworn testimony about the
*shape* of the data it will hand over — not the data's values, but properties like "will you ever
see the same reference twice," "is there a guaranteed order," "do I know exactly how many there
are." The pipeline never inspects the actual elements to decide whether it can skip a `distinct()`
or a `sorted()`; it reads this one `int` and trusts it completely. A spliterator that reports a
characteristic it does not actually honour is a silent correctness bug with no compiler check
anywhere in the chain.

**Why it exists.** Before this bitmask, a hand-written parallel algorithm had to know its source's
properties by convention baked into the algorithm itself — "I am writing code for sorted
`TreeSet`s specifically." `Spliterator` needed one machine-checkable vocabulary so that generic
stream operations (`distinct`, `sorted`, `toArray`, the parallel splitter) could ask "can I skip
this work" of *any* source, uniformly, without a type switch. The bitmask is that vocabulary and
it doubles as the mechanism that lets `StreamOpFlag` (guide 08) track how each intermediate
operation changes the shape of the data flowing downstream.

**When to reach for it, and when not.** Every source spliterator must set at least the
characteristics it genuinely has, and never more. There is no partial credit — reporting `SIZED`
when your `estimateSize()` is actually a guess is not "close enough," it corrupts every downstream
optimisation and every parallel-decomposition size calculation (guide 10) that trusts it.

**How it works — the bit values, source, and effect.**

| Characteristic | Hex | Meaning | Reported by (examples) | Optimisation it enables | Cleared by |
|---|---|---|---|---|---|
| `DISTINCT` | `0x01` | Every pairwise pair of encountered elements is `!x.equals(y)` | `HashSet`, `TreeSet`, keys of any `Map` | `distinct()` becomes a no-op and is elided entirely | `map`/`flatMap` (arbitrary function can reintroduce duplicates) |
| `SORTED` | `0x04` | Elements are encountered in the order defined by `getComparator()` (or natural order if `null`) | `TreeSet`, `TreeMap`'s key/entry sets, an already-`sorted()` stream | `sorted()` becomes a no-op — no sort pass runs — when the requested comparator matches | `map` (arbitrary function may not preserve ordering value), `unordered()` |
| `ORDERED` | `0x10` | Traversal follows a defined encounter order that traversal and splitting must respect | `List`s, arrays, `LinkedHashSet`/`LinkedHashMap`, `TreeSet` | `findFirst()`, `limit()`, `skip()`, `forEachOrdered()` are meaningful and stable; without it the pipeline may reorder freely for speed | `unordered()`, explicitly, and `Stream.of(...).parallel().unordered()`-style calls |
| `SIZED` | `0x40` | `estimateSize()` reports the *exact* remaining count, before traversal begins | any `Collection`-backed source, arrays | pre-sizing the buffer in `toArray()`/`collect(toList())`, exact `suggestTargetSize` decomposition math (guide 10) | `filter`, `flatMap`, `distinct` (post-operation count is not knowable in advance) |
| `NONNULL` | `0x100` | No encountered element is `null` | primitive streams' boxed views, sources documented never to hold `null` | lets some operations skip a null-check they would otherwise need | any operation whose function may itself introduce `null` results |
| `IMMUTABLE` | `0x400` | The source cannot be structurally modified — no element addition, removal, or replacement is possible for the life of this spliterator | `List.of(...)`, `Set.of(...)`, `Collections.unmodifiableList` wrappers *that are never mutated through another reference* | the pipeline can skip every fail-fast concurrent-modification check for this source | not clearable mid-pipeline — it is a property of the *source*, not of an intermediate stage |
| `CONCURRENT` | `0x1000` | The source itself tolerates concurrent structural modification without throwing, at the cost of weak consistency guarantees | `ConcurrentHashMap`, `ConcurrentLinkedQueue`, `CopyOnWriteArrayList` | the pipeline skips `ConcurrentModificationException` machinery for this source (it would be meaningless) | mutually exclusive with `IMMUTABLE` by construction — a source is one or the other, never both |
| `SUBSIZED` | `0x4000` | *If* this spliterator also reports `SIZED`, then every spliterator produced by `trySplit()` will *also* report an exact size — the size is knowable **recursively**, not just at the top | `ArrayList`, arrays | lets the parallel decomposition trust size-based cost estimates at every level of the split tree, not just the root | any split path that produces a sub-spliterator whose count is not knowable without re-scanning (bucket-table and batch-based splits) |

**D-135** — The eight spliterator characteristics

The eight `Spliterator` methods, for reference alongside the table above: `tryAdvance`,
`forEachRemaining`, `trySplit`, `estimateSize`, `getExactSizeIfKnown`, `characteristics`,
`hasCharacteristics`, `getComparator`.

**[NUM]** Verifying the bit arithmetic directly matters here because these values are not
sequential powers of two chosen for no reason — several are deliberately spaced to leave room in
the bit layout, and getting even one wrong when hand-rolling a spliterator silently corrupts a
mask combination elsewhere. In binary:

```
DISTINCT   = 0x0001 = 0b0000_0000_0000_0001
SORTED     = 0x0004 = 0b0000_0000_0000_0100
ORDERED    = 0x0010 = 0b0000_0000_0001_0000
SIZED      = 0x0040 = 0b0000_0000_0100_0000
NONNULL    = 0x0100 = 0b0000_0001_0000_0000
IMMUTABLE  = 0x0400 = 0b0000_0100_0000_0000
CONCURRENT = 0x1000 = 0b0001_0000_0000_0000
SUBSIZED   = 0x4000 = 0b0100_0000_0000_0000
```

`ArrayList.ArraySpliterator`'s `characteristics()` returns `ORDERED | SIZED | SUBSIZED`, which as
an `int` is `0x10 | 0x40 | 0x4000 = 0x4050`. Confirming this in `jshell` on this machine:

```
jshell> Spliterator.ORDERED | Spliterator.SIZED | Spliterator.SUBSIZED
$1 ==> 16464

jshell> Integer.toHexString(16464)
$2 ==> "4050"
```

**[RESEARCH]** These eight constants and their values are stable across every JDK release since
their introduction in Java 8 — re-verified against `java.util.Spliterator` at the **jdk-21+35**
tag; no constant has been renumbered or added since.

**Example — QuizStakes.** Composing a characteristics test the way `AbstractPipeline` actually
does, checking whether a source of stake reservations is safe for an unguarded `distinct()`-elide
optimisation:

```java
record StakeReservation(String reservationId, java.math.BigDecimal stake) {}

Set<StakeReservation> openReservations = loadOpenReservationSet(); // backed by a HashSet
Spliterator<StakeReservation> spliterator = openReservations.spliterator();

boolean canSkipDistinct = spliterator.hasCharacteristics(Spliterator.DISTINCT);
System.out.println(canSkipDistinct); // true — HashSet's spliterator reports DISTINCT
```

**The gotcha.** `hasCharacteristics` is an **all-of** test, not an any-of test — a common misread
of the javadoc. `spliterator.hasCharacteristics(Spliterator.SIZED | Spliterator.SUBSIZED)` returns
`true` only if *both* bits are set; it does not tell you "is at least one of these set." If you
want "is at least one set," you test the raw `characteristics() & mask != 0` yourself.

**Interview:** "Name the eight `Spliterator` characteristics and one optimisation each enables." —
walk the table above; the strongest answer pairs each characteristic with the specific stream
operation it lets the pipeline skip or short-circuit, not just a restatement of what the flag
means.

> **Definition:** The characteristics bitmask is a fixed set of eight `int` bit flags a spliterator
> reports about the shape of its elements and its own splitting behaviour, which the stream
> pipeline trusts unconditionally to decide which operations it can elide, short-circuit, or must
> perform in full.

---

## 3. `SIZED` versus `SUBSIZED`

**Mental model.** `SIZED` answers "do you know your own count." `SUBSIZED` answers a stronger,
recursive question: "if I split you, will the *pieces* also know their own count, and the pieces
of the pieces, all the way down." A spliterator can honestly know its own total while having no
idea how that total is distributed across the halves it would produce by splitting — that gap is
exactly what `SUBSIZED` exists to flag.

**Why it exists.** The parallel decomposition engine (guide 10) uses size estimates at *every*
level of the fork/join split tree to decide when to stop splitting (`suggestTargetSize`). If it
trusted `SIZED` alone, it would silently assume every sub-spliterator produced along the way also
reports an exact size — which is false for a source whose sub-ranges don't have a cheap size
computation. `SUBSIZED` is the honesty check that prevents that assumption from propagating
incorrectly.

**When to reach for it, and when not.** Report `SUBSIZED` only if you can prove every possible
`trySplit()` result, recursively, also reports an exact `estimateSize()` cheaply — "cheaply"
matters, because if computing a sub-range's exact size requires a linear scan of that sub-range,
you have destroyed the point of splitting in the first place. `ArrayList`'s index-range spliterator
gets this for free because subtracting two array indices is O(1) at any depth. A balanced-tree
spliterator generally cannot, because a subtree's element count is usually not cached at the node.

**How it works — the javadoc's own example, worked through.** `[PROVE]` The claim to prove: a
balanced binary search tree can honestly report `SIZED` but not `SUBSIZED`. Concretely: suppose a
`Spliterator` wraps a balanced tree of 94,999 `LedgerEntry` values (imagine an in-memory index
over a payment run's ledger rows, ordered by `entryId`). If the tree stores a `size` field at its
root — updated on every insert and remove — then before any splitting the spliterator can report
`estimateSize() == 94_999` and set `SIZED`, because that top-level count really is exact and known
without walking the tree. Now call `trySplit()`. A natural tree split hands the left subtree to
the new spliterator and keeps the right subtree in `this`. Does the left subtree's spliterator know
its own exact count? Only if *every node* also stores a subtree-size field, which a plain balanced
BST (unlike, say, an order-statistics tree) typically does not — subtree size is derivable only by
walking the subtree, an O(n) operation that would make every split pay for a full traversal of the
half it just carved off, defeating the purpose of splitting. So the honest report at every level
below the root is: "I know a size *estimate*" (`estimateSize()` may return a heuristic, e.g. half
of the parent's last known size) "but not an *exact* one," and hence `SIZED` is **not** re-declared
on the split-off pieces, and the root spliterator must not report `SUBSIZED` — because `SUBSIZED`
promises exactness recurses, and here it demonstrably does not.

**[SOURCE]** The JDK javadoc for `Spliterator.SUBSIZED` states the same example directly: *"a
Spliterator for a `Collection` would report `SIZED` but a Spliterator for a balanced binary tree
would report `SIZED` but not `SUBSIZED`, since it is common to know the size of the entire tree but
not the exact sizes of subtrees."* Every clause of that sentence maps onto the walk-through above:
"know the size of the entire tree" is the cached root-level `size` field; "not the exact sizes of
subtrees" is the absence of a subtree-size field at internal nodes.

**[RESEARCH]** Re-checked against `java.util.Spliterator`'s javadoc as shipped at the **jdk-21+35**
tag — the wording is unchanged from its Java 8 introduction; this is one of the oldest, most stable
sentences in the class.

**D-137** — `SIZED` but not `SUBSIZED`

![D-137 — `SIZED` but not `SUBSIZED`](../diagrams/D-137-sized-but-subsized.svg)

**D-137** — `SIZED` but not `SUBSIZED`

The left half of the diagram is `ArrayList`'s array-backed source: the total size is known and
every split's size is known too, so both flags are reported all the way down. The right half is
the balanced-tree case just proved above: the total is known (`SIZED`) but the subtree sizes are
not (`not SUBSIZED`), with the unknown subtree counts marked at each internal node — precisely the
javadoc's own framing, quoted above the diagram.

**Example — QuizStakes.** `ArrayList<CardDeposit>` versus a hypothetical balanced-tree index over
the same 95,000 deposits, side by side:

```java
List<CardDeposit> cardDeposits = loadCapturedCardDeposits(); // ArrayList, size 95_000
Spliterator<CardDeposit> arraySpliterator = cardDeposits.spliterator();
System.out.println(arraySpliterator.hasCharacteristics(Spliterator.SIZED));    // true
System.out.println(arraySpliterator.hasCharacteristics(Spliterator.SUBSIZED)); // true

Spliterator<CardDeposit> arrayLeft = arraySpliterator.trySplit();
System.out.println(arrayLeft.hasCharacteristics(Spliterator.SIZED));           // true — still exact
System.out.println(arrayLeft.getExactSizeIfKnown());                           // 47_500, exactly

// A balanced-tree index over the same 95_000 deposits, keyed by depositId:
DepositIndexTree depositIndex = DepositIndexTree.buildFrom(cardDeposits);
Spliterator<CardDeposit> treeSpliterator = depositIndex.spliterator();
System.out.println(treeSpliterator.hasCharacteristics(Spliterator.SIZED));     // true — root size cached
System.out.println(treeSpliterator.hasCharacteristics(Spliterator.SUBSIZED));  // false — subtree sizes unknown
```

**The gotcha.** `SIZED` without `SUBSIZED` is not a defect and not something to "fix" by forcing
`SUBSIZED` on — doing so when the promise is false corrupts every parallel size estimate that
trusts it recursively, which is a *worse* outcome than honestly reporting the weaker guarantee.
`SUBSIZED` is the harder property to earn, and most non-array-backed structures legitimately never
earn it.

**Interview:** "Give an example of `SIZED` but not `SUBSIZED`." — the balanced tree, and the
one-line reason is that root-level size is commonly cached, subtree size commonly is not.

> **Definition:** `SIZED` promises the top-level `estimateSize()` is exact; `SUBSIZED` is the
> stronger, recursive promise that every spliterator produced by splitting also reports an exact
> size — a promise only structures with O(1) sub-range size arithmetic, like index ranges, can
> honestly make.

---

## 4. `trySplit` returns the prefix

**Mental model.** Picture the remaining elements as one ribbon. `trySplit()` cuts the ribbon once,
hands you the piece from the start up to the cut, and keeps the piece from the cut to the end for
itself. It never hands you the tail and keeps the head — the direction of the cut is fixed by
contract, and that fixed direction is what lets an `ORDERED` stream stay correctly ordered across
recursive splitting without any coordination between the pieces.

**Why it exists.** A splitting operation needs a deterministic contract for *which half goes
where*, or an `ORDERED` source could not guarantee encounter order under parallel decomposition —
whichever piece happened to finish first would win, silently scrambling the sequence. Fixing "the
returned piece is always the prefix, the receiver keeps the suffix" gives the Fork/Join
recombination step (guide 10) a rule it can rely on unconditionally: concatenate results
left-to-right in the order the splits were taken, and an `ORDERED` source stays ordered with zero
extra bookkeeping.

**When to reach for it, and when not.** This governs anyone writing `trySplit()` by hand (§6):
your returned spliterator must cover the elements that come *first* in encounter order, and `this`
must be left covering what comes after. Get the direction backwards and the bug is silent for
sequential streams (nothing calls `trySplit` there) and only shows up under `.parallel()`, as
scrambled output on an operation the caller assumed was order-preserving.

**How it works.** `[SOURCE]` The relevant lines of `java.util.Spliterator`'s javadoc for
`trySplit()`, quoted, then explained:

> *"If this spliterator can be partitioned, returns a Spliterator covering elements, that will,
> upon return from this method, not be covered by this Spliterator. ... If this Spliterator is
> `ORDERED`, the returned Spliterator must cover a strict prefix of the elements."*

- "covering elements ... not be covered by this Spliterator" — the split is a **partition**, not a
  copy: after the call, the union of `this` and the returned spliterator's remaining elements
  equals what `this` covered before the call, with no overlap and no element dropped.
  `trySplit()` mutates `this` in place to reflect the smaller remaining range; it does not merely
  hand back a read-only view.
- "if this Spliterator is `ORDERED` ... must cover a strict prefix" — this is the direction rule:
  the *returned* spliterator gets the elements that come first; `this` keeps what comes after.
  "Strict prefix" rules out an implementation that returns, say, every other element interleaved —
  the cut must be a single contiguous boundary in encounter order.
- The method may return `null` at any time, for any reason the implementation chooses — typically
  because further splitting would produce pieces too small to be worth the fork/join overhead
  (guide 10's `LEAF_TARGET` machinery decides "worth it" from the caller's side; the spliterator
  itself may also refuse below some internal floor), or because the underlying structure has no
  cheap way to split further (a singly-linked list node with no length field, for instance, could
  refuse outright rather than pay for a counting pass).
- Repeated calls to `trySplit()` are expected to work — each call further shrinks `this` and hands
  back a new prefix piece — which is exactly the recursive halving the parallel engine relies on to
  build its split tree.

**D-136** — `trySplit` returns the prefix

![D-136 — `trySplit` returns the prefix](../diagrams/D-136-trysplit-returns-prefix.svg)

**D-136** — `trySplit` returns the prefix

The scenario: an `ArrayList` of 95,000 card deposits. Frame 1 shows one spliterator over the whole
index range, 0–94,999. Frame 2 calls `trySplit()`: the returned spliterator covers 0–47,499 (the
prefix), and the original spliterator, mutated in place, now covers only 47,500–94,999 — both
ranges labelled explicitly, matching the direction rule above. Frame 3 shows the recursion
continuing on each half, down to leaves below the target split size.

One consistency note on the diagram's own inset: D-136 works the `suggestTargetSize` arithmetic on
an illustrative **5-core** machine to make the doubling pattern easy to see at small numbers
(`LEAF_TARGET = 4 << 2 = 16`, target size 5,937), and the diagram says so on its face. That is a
deliberately smaller illustration, not this note set's default. Every other worked example in this
file and its siblings — including §8's `IteratorSpliterator` batch sizes and guide 10's
decomposition arithmetic — uses this set's **8-core convention**: `availableProcessors() == 8`,
common-pool parallelism `7`, effective width `8`, `LEAF_TARGET = 7 << 2 = 28`. The two numbers are
not a contradiction; they are two different machine sizes used for two different purposes, and the
8-core figures are the ones to carry forward into every other file.

**Example — QuizStakes.** `ArrayList`'s `trySplit()`, called explicitly, showing the prefix rule
and the in-place mutation of the original:

```java
List<CardDeposit> cardDeposits = loadCapturedCardDeposits(); // indices 0..94_999
Spliterator<CardDeposit> whole = cardDeposits.spliterator();
System.out.println(whole.estimateSize()); // 95_000

Spliterator<CardDeposit> prefix = whole.trySplit();
System.out.println(prefix.estimateSize()); // 47_500 — covers 0..47_499
System.out.println(whole.estimateSize());  // 47_500 — mutated in place, now covers 47_500..94_999

// Confirm the prefix really is the head, by encounter order:
List<CardDeposit> prefixElements = new ArrayList<>();
prefix.forEachRemaining(prefixElements::add);
System.out.println(prefixElements.get(0).depositId());                 // the first deposit captured
System.out.println(prefixElements.get(prefixElements.size() - 1).depositId()); // the 47,500th
```

**The gotcha.** `trySplit()` returning `null` does **not** mean "this spliterator is exhausted" —
it means "this spliterator declines to split further, but still has elements to traverse via
`tryAdvance`/`forEachRemaining`." Treating a `null` split result as "nothing left" is a real bug
class in hand-written parallel code: the correct response to `null` is to fall back to sequential
traversal of whatever `this` still covers, exactly as `ForkJoinTask`-based stream evaluation does
(guide 10).

**Interview:** "If `trySplit()` returns a piece, which half — the one it returns or the one it
keeps — comes first in the stream's encounter order?" — the *returned* piece is always the prefix;
`this` always keeps the suffix, by contract, whenever the source is `ORDERED`.

> **Definition:** `trySplit()` partitions a spliterator's remaining elements into two disjoint
> pieces, returning the piece covering the encounter-order **prefix** while mutating `this` in
> place to cover only the suffix — or returns `null` when it declines to split further.

---

## 5. Per-collection spliterators — `ArrayList`, `HashMap`, `LinkedList`, `Files.lines`

**Mental model.** Every collection's `spliterator()` is only as good as the data structure's own
shape for cutting itself in half. An array is a contiguous run of slots addressed by index — you
can bisect it with one subtraction. A hash table is a fixed-size bucket array with an unknown,
possibly lopsided, distribution of elements across buckets — you can bisect the *bucket range* in
one subtraction, but not the *element count* in each half. A linked list has no index at all — the
only way to know "the second half" is to have already walked to the middle, which is precisely the
cost splitting is supposed to avoid, so it settles for something weaker: pull a batch, hand it
off, don't promise anything about the remainder's shape.

**Why it exists.** `Collection.spliterator()` is a default method that must work for *every*
implementer, including ones with no efficient splitting story at all (a `PriorityQueue`, most
custom `Collection`s that never override it). Rather than force every collection to invent an
efficient split or fall back to nothing, the JDK gives each of its own concrete collections the
best splitting behaviour its internal structure actually supports, and gives everything else a
uniform, honest, batch-based fallback (§6) — never silently pretending a structure splits well when
it does not.

**When to reach for it, and when not.** This is not a choice you make per call site — it is a
property of *which collection you chose*, decided long before you ever call `.stream()`. The
practical takeaway is the opposite direction: if a hot path needs a stream to parallelise well,
this table is the argument for choosing `ArrayList` (or an array) over `LinkedList` as the backing
structure, independent of any other property of the two.

**How it works — `ArrayList`.** `[X-REF 02]` `ArrayList`'s `spliterator()` returns an internal
`ArrayListSpliterator` (constructed lazily against the backing array and a `fence`/`expectedModCount`
pair for fail-fast checks) that reports `ORDERED | SIZED | SUBSIZED`. `trySplit()` computes
`(origin + fence) >>> 1` and returns a new spliterator over `[origin, mid)`, leaving `this` covering
`[mid, fence)` — a single unsigned-shift midpoint calculation, O(1) regardless of how large the
range is. Because both halves are themselves contiguous index ranges, the same O(1) split applies
recursively at every depth, which is exactly why `SUBSIZED` is honestly earned here (§3). This
makes `ArrayList` — and arrays directly, via `Arrays.spliterator`, which uses the identical scheme
— **the ideal parallel-stream source**: cheap to split, exactly sized at every level, and the
elements it copies during `toArray()`-style collection sit in genuinely contiguous memory, which is
friendly to the CPU cache in ways a pointer-chasing structure never is. `ArrayList`'s full
collection-internals treatment — resizing, `modCount`, the growth factor — is guide 02's territory;
this file only needs the spliterator's own splitting behaviour.

**How it works — `HashMap`.** `[X-REF 02]` `HashMap`'s key/value/entry spliterators
(`HashMap.HashMapSpliterator` and its three subclasses) split over **ranges of the internal bucket
table**, not over element counts. `trySplit()` bisects the table-index range `[index, fence)` the
same way `ArrayList` bisects an element-index range, and reports `SIZED` (the map's total element
count is cached and known up front) but **not `SUBSIZED`** — because bisecting the bucket-index
range does not bisect the *element* count evenly. If 95,000 elements happen to cluster such that
70% land in the first half of the bucket table's index range (a real possibility with a poor or
adversarial hash distribution, and even under a good distribution the split is never guaranteed to
be exactly 50/50 the way an index-range split is), each half's actual population is genuinely
uneven — the spliterator does not know this in advance, and cannot report the sub-range's exact
size without walking it, exactly the situation §3 describes for the tree case. Map iteration order
itself, treeified buckets, and the resize/rehash mechanics are guide 02's territory; the
spliterator-relevant fact is narrower: bucket-range splitting means the *size estimate* is honest
about the whole but not about the halves.

**How it works — `LinkedList`.** `[NUM]` `[X-REF 02]` `LinkedList`'s spliterator
(`LinkedList.LLSpliterator`) has no index to bisect and no random access to a midpoint node, so it
falls back to a **doubling batch scheme**: the first `trySplit()` call walks forward from the
current position pulling elements into an array of `BATCH_UNIT` (`1 << 10` = **1,024**) elements,
returns a spliterator over that array as the split-off piece, and remembers a doubled batch size
for next time — up to a ceiling of `MAX_BATCH` (`1 << 25` = **33,554,432**). Because each split's
size is only known *after* the walk that produced it, `LinkedList`'s spliterator reports
`ORDERED | SIZED` (the list's overall `size` field is cached and exact) but **never `SUBSIZED`**,
and worse than `HashMap`'s case: producing each split piece costs an O(batch-size) linked
traversal, not an O(1) index calculation. `[X-REF 02]` This is precisely why `LinkedList` parallel
streams are close to worthless in practice — every split pays a linear-time cost proportional to
the very piece it is trying to carve off, which erases most of the benefit splitting exists to
provide; guide 02 covers `LinkedList`'s node structure and why it loses to `ArrayList` for nearly
every other access pattern too.

**How it works — `Files.lines`.** `Files.lines(Path)` returns a stream backed by a
`BufferedReader`'s line iterator, adapted into a spliterator via the exact same batching mechanism
described in §6 for `IteratorSpliterator` — `Files.lines` does not have its own bespoke spliterator
class; it is a textbook case of the generic iterator-adapter fallback. Every `trySplit()` call
reads a batch of lines by repeatedly calling the underlying `BufferedReader.readLine()`, which is a
**synchronized, sequential I/O operation** against one file handle — there is no way to read "the
second half of the file" without first reading through the first half (line boundaries are not
known until the bytes between them are scanned), so even though the *stream* nominally reports
splits, the actual work behind each split remains strictly serial I/O. Parallelising
`Files.lines(paymentRunFile).parallel()` therefore buys you parallel *processing* of each line once
read, but the *reading* itself never truly overlaps — the bottleneck is the sequential scan for
newline boundaries, not CPU work per line.

**Comparison table — the four sources side by side:**

| Source | Splits by | `SIZED`? | `SUBSIZED`? | Per-split cost | Parallel-worthy? |
|---|---|---|---|---|---|
| `ArrayList` / array | index-range halving | Yes | Yes | O(1) | Yes — the reference case |
| `HashMap` (keys/values/entries) | bucket-table range halving | Yes | No | O(1) to split, but halves are unevenly populated | Moderate — depends on distribution |
| `LinkedList` | doubling batch, pulled by traversal | Yes | No | O(batch size) — linear in the piece produced | Poor — splitting costs as much as the work it saves |
| `Files.lines` / any `Iterator`-only source | doubling batch, pulled by traversal (same mechanism as `LinkedList`, via `IteratorSpliterator`) | No (`Long.MAX_VALUE` until exhausted) | No | O(batch size), and for `Files.lines` specifically bottlenecked on serial I/O | Poor for the source read itself; fine for CPU-bound work done per element once batched |

**Example — QuizStakes.** The 95,000 card deposits as an `ArrayList` versus the same deposits
grouped into a `HashMap<String, List<CardDeposit>>` keyed by rail (`CARD`, effectively one key
here, but imagine keyed by `statusCode` across a day with several dispositions) versus a
`LinkedList` copy used to demonstrate the batching cost directly:

```java
List<CardDeposit> asArrayList = loadCapturedCardDeposits();      // 95_000 elements
Spliterator<CardDeposit> arraySplit = asArrayList.spliterator();
System.out.println(arraySplit.characteristics() ==
        (Spliterator.ORDERED | Spliterator.SIZED | Spliterator.SUBSIZED)); // true

Map<String, CardDeposit> byDepositId = asArrayList.stream()
        .collect(Collectors.toMap(CardDeposit::depositId, d -> d));
Spliterator<CardDeposit> mapValuesSplit = byDepositId.values().spliterator();
System.out.println(mapValuesSplit.hasCharacteristics(Spliterator.SIZED));    // true
System.out.println(mapValuesSplit.hasCharacteristics(Spliterator.SUBSIZED)); // false

LinkedList<CardDeposit> asLinkedList = new LinkedList<>(asArrayList);
Spliterator<CardDeposit> linkedSplit = asLinkedList.spliterator();
System.out.println(linkedSplit.hasCharacteristics(Spliterator.SUBSIZED));    // false

long start = System.nanoTime();
long arraySum = asArrayList.parallelStream()
        .map(CardDeposit::amount).mapToLong(java.math.BigDecimal::longValue).sum();
long arrayMillis = (System.nanoTime() - start) / 1_000_000;

start = System.nanoTime();
long linkedSum = asLinkedList.parallelStream()
        .map(CardDeposit::amount).mapToLong(java.math.BigDecimal::longValue).sum();
long linkedMillis = (System.nanoTime() - start) / 1_000_000;
// arrayMillis is reliably lower than linkedMillis at this volume — the split cost dominates
// LinkedList's parallel path, not the per-element work, which is identical in both loops.
```

**The gotcha.** "It's a `Collection`, so `.parallelStream()` will use my cores" is the trap —
`LinkedList.parallelStream()` compiles, runs, and produces correct results, but at 95,000 elements
the batching overhead routinely makes it **slower** than `LinkedList.stream()` run sequentially,
because every core assigned a split pays a linear walk to receive its share while an `ArrayList`
split is free. The fix is never "tune the parallelism" — it is "don't parallelise a `LinkedList`
stream; convert to `ArrayList` first if the volume justifies parallelism at all."

**Interview:** "Which `Collection` types parallelise best under `.parallelStream()`, and why?" —
`ArrayList` and arrays, because their spliterators split in O(1) and stay `SUBSIZED` at every
depth; anything requiring a batching fallback (`LinkedList`, plain `Iterator`-backed sources)
parallelises poorly because the split itself costs as much as the work it is trying to
distribute.

> **Definition:** A collection's spliterator inherits its splitting efficiency directly from the
> collection's own internal addressing scheme — index-addressable structures split for free,
> everything else pays a real cost to split, and that cost is the single biggest predictor of
> whether `.parallelStream()` on that collection is worth calling at all.

---

## 6. The `IteratorSpliterator` batching fallback

**Mental model.** When a source offers nothing but `hasNext`/`next` — no index, no bucket table,
no cached size — the JDK cannot invent a smarter split out of thin air, so it does the only honest
thing: pull a chunk of elements into a plain array via repeated `next()` calls, hand that array off
as a genuinely well-behaved (index-addressable!) split, and keep the *rest* of the iterator as an
unknown-sized remainder. Each subsequent split pulls a bigger chunk than the last. This is the
batching fallback, and it is the mechanism behind both `Spliterators.spliteratorUnknownSize` and
`LinkedList`'s own splitting (§5) — the same idea, applied wherever there is no cheaper option.

**Why it exists.** Without it, wrapping a bare `Iterator` in a stream (`StreamSupport.stream(...)`
over any `Iterable` that does not override `spliterator()`) would force `trySplit()` to always
return `null`, making every such stream permanently sequential even under `.parallel()`. Batching
gives these sources *some* parallel capability — the elements already pulled into a batch can be
processed on another thread while the iterator keeps producing more — without pretending the
source has a property (a known size, a cheap split) it does not have.

**How it works.** `[NUM]` `java.util.Spliterators.IteratorSpliterator<T>` — the class backing both
`Spliterators.spliteratorUnknownSize(Iterator, int)` and the ordinary `Iterable.spliterator()`
default method — holds a `batch` field, initially `0`. On the first `trySplit()` call, it computes
`n = (batch == 0) ? 1024 : batch`, doubles `batch` for next time (capped so the running batch never
exceeds `MAX_BATCH = 1 << 25` = 33,554,432), pulls up to `n` elements from the wrapped `Iterator`
into an `Object[]` via `hasNext()`/`next()`, and returns an `ArraySpliterator` over that array as
the split-off piece — an array spliterator, which is itself index-addressable and would report
`SIZED | SUBSIZED` **for that batch alone**. The spliterator wrapping the *original* iterator,
however, still reports `estimateSize() == Long.MAX_VALUE` until the underlying iterator is
exhausted, because there is no way to know how many elements remain without consuming them, and it
never reports `SUBSIZED`, because nothing about future batches is knowable in advance. This is the
exact mechanism `LinkedList.LLSpliterator` in §5 independently implements for the same reason — a
structure with no O(1) midpoint falls back to the same doubling-batch idea, whether or not it goes
through this specific class.

**D-138** — Why an `Iterator`-derived stream parallelises badly

![D-138 — Why an `Iterator`-derived stream parallelises badly](../diagrams/D-138a-iterator-derived-stream-parallelises.svg)

**D-138** — Why an `Iterator`-derived stream parallelises badly (frame 1 of 3)

![D-138 — Why an `Iterator`-derived stream parallelises badly](../diagrams/D-138b-iterator-derived-stream-parallelises.svg)

**D-138** — Why an `Iterator`-derived stream parallelises badly (frame 2 of 3)

![D-138 — Why an `Iterator`-derived stream parallelises badly](../diagrams/D-138c-iterator-derived-stream-parallelises.svg)

**D-138** — Why an `Iterator`-derived stream parallelises badly (frame 3 of 3)

The three frames walk `IteratorSpliterator`'s batching fallback end to end. Frame 1: the first
`trySplit()` pulls a batch of 1,024 elements into an array — the batch size written on the frame.
Frame 2: the next `trySplit()` doubles the batch to 2,048, then the one after to 4,096, and so on,
each size labelled. Frame 3: eventually the source is exhausted mid-batch and the tail remains
unsplittable, never having reported `SUBSIZED` at any point — `LinkedList` and `Files.lines` are
named on the frame as the two cases this file covers that hit exactly this mechanism.

**Example — QuizStakes.** `Files.lines` over a payment-run settlement file, and a hand-rolled
`Iterator` over the same 2.8M-per-day scale of stake reservations, both hitting the identical
batching path:

```java
Path paymentRunFile = Path.of("/data/payment-runs/2026-08-30-bank-withdrawals.csv");
try (Stream<String> lines = Files.lines(paymentRunFile)) {
    // Backed by BufferedReader's line iterator, adapted via the same batching
    // fallback as any other Iterator-only source. Splitting exists, but every
    // batch still comes from one sequential BufferedReader.readLine() cursor.
    long settledCount = lines.parallel()
            .filter(line -> line.contains("BDP-"))
            .count();
}

Iterator<StakeReservation> reservationFeed = openReservationFeed(); // a live cursor, no known size
Spliterator<StakeReservation> feedSpliterator =
        Spliterators.spliteratorUnknownSize(reservationFeed, Spliterator.ORDERED | Spliterator.NONNULL);
System.out.println(feedSpliterator.estimateSize()); // Long.MAX_VALUE — genuinely unknown

Spliterator<StakeReservation> firstBatch = feedSpliterator.trySplit();
System.out.println(firstBatch.estimateSize());  // 1024 — the first batch, exactly IteratorSpliterator's BATCH_UNIT
Spliterator<StakeReservation> secondBatch = feedSpliterator.trySplit();
System.out.println(secondBatch.estimateSize()); // 2048 — doubled
```

**The gotcha.** Reaching for `Spliterators.spliteratorUnknownSize` to "make my custom `Iterable`
parallel-friendly" hands you *some* splitting, but not the properties that actually make parallel
streams fast — `SIZED`, and especially `SUBSIZED`, never arrive this way, and the parallel engine's
`suggestTargetSize` decomposition (guide 10) degrades to guesswork against an unknown total size.
If a source can compute or cache its true count cheaply, expose that through a real `Spliterator`
implementation (§7) rather than accepting this fallback — the fallback is a safety net, not a
performance feature.

**Interview:** "Why does wrapping a plain `Iterator` in a parallel stream rarely help?" — because
the only splitting available is the doubling-batch fallback, which never reports `SUBSIZED` and
whose first several splits are tiny (1,024, then 2,048, …) relative to typical stream volumes,
so most of the elements are processed after the batch machinery has barely ramped up.

> **Definition:** `IteratorSpliterator` is the JDK's universal fallback for any source with no
> native splitting story — it turns `next()` calls into successively doubling array batches — and
> it is the shared mechanism behind both the generic `Iterator` adapter and `LinkedList`'s own
> spliterator, which is why both parallelise for the same structural reason and neither earns
> `SUBSIZED`.

---

## 7. Writing a spliterator that splits well

**Mental model.** A spliterator you write yourself has exactly the two options every built-in one
has: implement a real, structural `trySplit()` that costs O(1) or close to it and can honestly
report `SIZED | SUBSIZED` (the `ArrayList` path), or accept the generic batching fallback and get
whatever parallelism that buys you for free (the `LinkedList`/`IteratorSpliterator` path). The JDK
gives you a base class for each choice.

**Why it exists.** `AbstractSpliterator` exists so that authoring *a* spliterator — even a
mediocre one — is nearly free: extend it, implement `tryAdvance`, done, and you inherit a working
(if batching-based) `trySplit()` for nothing. It exists precisely so nobody is tempted to skip
`Spliterator` support entirely because writing the full interface by hand looked like too much
ceremony.

**When to reach for it, and when not.** Reach for `AbstractSpliterator` when your source is
correctness-first and parallelism is a nice-to-have — it gets you a spliterator with zero risk of
getting the interface contract wrong. Reach for implementing `Spliterator` directly, overriding
`trySplit()` yourself, only when you know your structure supports genuine O(1)-ish halving and you
specifically need `SIZED | SUBSIZED` to make parallel decomposition actually pay off; the effort is
only worth it when a profiled hot path justifies it.

**How it works — the base classes.** `[BUILD]` `java.util.Spliterators.AbstractSpliterator<T>` is
an abstract class holding `estimateSize` and the characteristics `int` as constructor parameters,
leaving only `tryAdvance` abstract; its inherited `trySplit()` implementation runs the exact
batching scheme from §6 — repeated `tryAdvance` calls collected into an array — so a subclass gets
splitting behaviour identical in spirit to `IteratorSpliterator`, not the structural halving of
`ArraySpliterator`. `Spliterators.AbstractIntSpliterator`, `AbstractLongSpliterator`, and
`AbstractDoubleSpliterator` are the primitive-specialised twins, used the same way but built around
`IntConsumer`/`LongConsumer`/`DoubleConsumer` to avoid boxing (§8 covers the primitive interfaces
themselves).

A spliterator that genuinely wants `SIZED | SUBSIZED` must **not** rely on `AbstractSpliterator`'s
inherited `trySplit()` — it must override `trySplit()` directly with real structural halving, the
way `ArraySpliterator` does. Below is a complete, hand-written spliterator over a fixed-size
circular buffer of settled `StakeReservation`s — a structure with genuine O(1) index arithmetic,
which earns the strong characteristics honestly.

```java
final class SettlementRingBufferSpliterator implements Spliterator<StakeReservation> {

    private final StakeReservation[] ring;
    private int fromInclusive;
    private int toExclusive; // logical range [fromInclusive, toExclusive), may wrap the ring physically

    SettlementRingBufferSpliterator(StakeReservation[] ring, int fromInclusive, int toExclusive) {
        this.ring = ring;
        this.fromInclusive = fromInclusive;
        this.toExclusive = toExclusive;
    }

    @Override
    public boolean tryAdvance(Consumer<? super StakeReservation> action) {
        if (fromInclusive >= toExclusive) return false;
        action.accept(ring[fromInclusive % ring.length]);
        fromInclusive++;
        return true;
    }

    @Override
    public void forEachRemaining(Consumer<? super StakeReservation> action) {
        for (int i = fromInclusive; i < toExclusive; i++) {
            action.accept(ring[i % ring.length]);
        }
        fromInclusive = toExclusive;
    }

    @Override
    public Spliterator<StakeReservation> trySplit() {
        int remaining = toExclusive - fromInclusive;
        if (remaining < 2) return null; // too small to be worth splitting
        int mid = fromInclusive + (remaining >>> 1);
        Spliterator<StakeReservation> prefix =
                new SettlementRingBufferSpliterator(ring, fromInclusive, mid);
        this.fromInclusive = mid; // this now covers only the suffix — matches §4's contract
        return prefix;
    }

    @Override
    public long estimateSize() {
        return toExclusive - fromInclusive;
    }

    @Override
    public int characteristics() {
        return ORDERED | SIZED | SUBSIZED | NONNULL;
    }
}
```

**[PROVE]** Why this earns `SIZED | SUBSIZED` honestly, unlike the balanced tree in §3: `estimateSize()`
is `toExclusive - fromInclusive`, a single subtraction over two `int` fields — exact, O(1), true at
construction. `trySplit()` computes `mid` by the identical unsigned-shift midpoint arithmetic
`ArraySpliterator` uses, and both the returned prefix piece and the mutated suffix (`this`) are
themselves instances of the same class with the same O(1) `estimateSize()` — so the proof is
inductive: if a `SettlementRingBufferSpliterator` of any size honestly reports its exact size, so
does every spliterator produced by splitting it, all the way to single-element leaves. That
recursive closure is exactly what `SUBSIZED` promises, and here it is mechanically guaranteed by
construction, not asserted.

**Example — QuizStakes, continued.** Confirming the split direction and characteristics hold under
actual use, over a ring buffer of 8 settled reservations for a small, checkable example:

```java
StakeReservation[] ring = settledReservationsRingBuffer(); // length 8, logically holds indices 0..7
Spliterator<StakeReservation> whole = new SettlementRingBufferSpliterator(ring, 0, 8);
System.out.println(whole.estimateSize()); // 8

Spliterator<StakeReservation> prefix = whole.trySplit();
System.out.println(prefix.estimateSize()); // 4 — indices 0..3
System.out.println(whole.estimateSize());  // 4 — mutated in place, now indices 4..7
System.out.println(whole.hasCharacteristics(Spliterator.SUBSIZED)); // true
```

**The gotcha.** The single most common mistake writing a custom `trySplit()` is forgetting to
mutate `this` — returning a prefix spliterator while leaving `fromInclusive`/`toExclusive` (or
equivalent state) untouched on the receiver silently **duplicates** every element in the prefix
range: both the returned spliterator and the original will traverse it. This produces no exception
and no crash — only doubled output under `.parallel()` that vanishes the moment you remove
`.parallel()`, which makes it exactly the kind of bug that survives code review and only shows up
in production once real concurrency is involved.

**Interview:** "Walk through how you'd make a custom data structure parallel-stream-friendly." —
name the two options (`AbstractSpliterator`'s batching inheritance versus a hand-rolled structural
`trySplit()`), name the condition for choosing the second (O(1) or near-O(1) halving available),
and name the specific bug to avoid (forgetting to mutate `this`'s remaining range).

> **Definition:** A spliterator "splits well" when `trySplit()` partitions in O(1)-or-near time,
> correctly returns the encounter-order prefix while shrinking `this` to the suffix, and both
> halves can honestly re-report `SIZED | SUBSIZED` — a property earned by the structure's own
> addressing scheme, never by declaring the flags and hoping.

---

### `Spliterator.OfInt` / `OfLong` / `OfDouble`

*(Supporting fact — no diagram, no sibling choice, a shape with no independent tradeoff of its
own: it exists purely so the primitive stream types avoid boxing, and it inherits every property
already proved above.)*

**Mechanism.** `Spliterator` declares three nested interfaces — `Spliterator.OfInt`,
`Spliterator.OfLong`, `Spliterator.OfDouble` — each extending `Spliterator.OfPrimitive<T, T_CONS,
T_SPLITR>` and, transitively, the boxed `Spliterator<Integer>` / `<Long>` / `<Double>`. Each adds
primitive-typed overloads: `boolean tryAdvance(IntConsumer)`, `void forEachRemaining(IntConsumer)`,
and `Spliterator.OfInt trySplit()` (a covariant return narrowing the boxed version). `IntStream`,
`LongStream`, and `DoubleStream` are built entirely on these — `IntStream.range(0, 2_800_000)`
returns a source backed by `Spliterator.OfInt`, and every intermediate/terminal operation in the
primitive stream types dispatches through the primitive `Consumer` overloads, never boxing an
`Integer`/`Long`/`Double` unless a `.boxed()` call explicitly asks for it. This is the same design
already covered end to end in guide streams/05 (primitive streams) — this file's contribution is
narrower: these are ordinary `Spliterator`s in every respect covered above (characteristics,
`trySplit` prefix semantics, `SIZED`/`SUBSIZED`), specialised only in their `Consumer` type to avoid
autoboxing on the hot path.

**Gotcha.** Calling the boxed `tryAdvance(Consumer<? super Integer>)` overload on a
`Spliterator.OfInt` still works — it is inherited from the boxed interface — but it silently boxes
every element on the way through, throwing away exactly the allocation savings the primitive
interface exists to provide. This is the same trap as calling `.stream().boxed()` unnecessarily on
an `IntStream`; the fix is the same discipline: stay on the primitive-typed method overloads for as
long as the pipeline permits.

> `Spliterator.OfInt`/`OfLong`/`OfDouble` are primitive-specialised `Spliterator`s used by
> `IntStream`/`LongStream`/`DoubleStream` to avoid boxing; they carry every characteristic and
> `trySplit` rule already established for the boxed interface.

---

### Late-binding spliterators and the concurrent-modification detection window

*(Supporting fact — no diagram, no independent sibling to choose against, but it does carry a
`**Pitfall:**` because the syllabus tags it `[X-REF 02]`-adjacent behaviour interview candidates
routinely get wrong.)*

**Mechanism.** A spliterator is **late-binding** when it does not commit to a specific view of its
source's elements until the first of `tryAdvance`, `forEachRemaining`, `trySplit`, or (per the
interface's own javadoc framing) a size query is invoked — not at the moment `spliterator()` was
called. `ArrayList`'s spliterator is late-binding: you may call `list.spliterator()`, then
structurally modify the list, and no exception fires yet, because nothing has bound to the list's
state. The moment you call `tryAdvance` (or `trySplit`, or `forEachRemaining`) for the first time,
the spliterator captures the list's current `modCount` as its `expectedModCount`; every subsequent
call compares the live `modCount` against that captured value and throws
`ConcurrentModificationException` the instant they diverge. `[X-REF 02]` This is the same
`modCount` fail-fast mechanism `ArrayList`'s own `Iterator` uses — guide 02 covers `modCount` and
the iterator's fail-fast checks in full; the spliterator-specific fact worth carrying here is
narrower: the detectable window opens at **first use**, not at creation, which is exactly why a
structural modification made *before* the first traversal call is invisible to the spliterator —
it simply becomes part of the data the spliterator binds to.

**Gotcha.**

**Pitfall:** assuming `list.spliterator()` "locks in" the list's contents at the moment it is
called, the way copying to an immutable list would.

```java
// Wrong — assumes the spliterator already reflects a frozen view of cardDeposits
List<CardDeposit> cardDeposits = new ArrayList<>(loadCapturedCardDeposits());
Spliterator<CardDeposit> spliterator = cardDeposits.spliterator();
cardDeposits.add(new CardDeposit("DEP-999999", java.math.BigDecimal.valueOf(65), "DEP-301"));
// No exception here — nothing has bound yet.
spliterator.forEachRemaining(d -> {}); // now binds, and now sees 95,001 elements, not 95,000
```

```java
// Right — bind first, then it is safe to reason about "the state at binding time"
List<CardDeposit> cardDeposits = new ArrayList<>(loadCapturedCardDeposits());
Spliterator<CardDeposit> spliterator = cardDeposits.spliterator();
spliterator.tryAdvance(d -> {}); // binds now, capturing modCount
// any structural modification to cardDeposits from this point on throws
// ConcurrentModificationException on the next traversal call, predictably
```

**Why people believe it:** most other "snapshot"-flavoured APIs in the collections framework
(`List.copyOf`, `new ArrayList<>(source)`) really do freeze state at the call site, so it is a
reasonable but wrong generalisation to assume `spliterator()` behaves the same way; late binding is
specifically a performance choice — capturing state eagerly would mean walking or copying the
source just to hand back a cursor, which the JDK is unwilling to pay for by default.

> Late-binding means a spliterator's view of its source is fixed at **first use**
> (`tryAdvance`/`forEachRemaining`/`trySplit`/a size query), not at creation, and the fail-fast
> `ConcurrentModificationException` window opens only from that first-use point forward.

---

### The characteristics-to-optimisation map, closing the loop

*(Supporting fact, tying together the table in §2 rather than introducing new mechanism —
`[PROVE]` is satisfied by the walk-through already given per characteristic in §2's table; this
closes the leaf with the two optimisation paths worth naming explicitly.)*

**Mechanism.** Two optimisations in `java.util.stream.ReferencePipeline` read characteristics
directly to skip work outright, and both were already named per-row in §2's table:

- `distinct()` checks whether the upstream spliterator already reports `DISTINCT` (via the
  `StreamOpFlag` machinery guide 08 covers in full) and, if so, the operation degenerates to a
  pass-through stage with no deduplication work performed at all — no `HashSet` is built, no
  `equals`/`hashCode` calls happen.
- `sorted()` with no explicit `Comparator` checks whether the upstream reports `SORTED` with a
  natural-order comparator (`getComparator() == null`, per the interface's own contract in §1) and,
  if so, similarly degenerates to a pass-through — no sort pass runs.

Both are genuine no-op eliminations, not merely "a faster path" — the operation is compiled out of
the pipeline's actual work at evaluation time. `SIZED`/`SUBSIZED` do not eliminate an operation the
same way; instead they feed `toArray()`'s pre-sizing and `suggestTargetSize`'s decomposition math
(guide 10), which is a cost reduction rather than a work elimination. `ORDERED` gates correctness,
not cost, for `findFirst`, `limit`, `skip`, and `forEachOrdered` — without it those operations
either behave differently (`findFirst` degrades to `findAny`-equivalent nondeterminism is *not*
what happens; rather, the pipeline is free to reorder for speed and an `ORDERED`-dependent operation
must not be relied upon to return a stable first element) or cost more to make deterministic under
parallel evaluation.

**Unverified:** the exact set of intermediate operations that clear each flag (for example,
whether `filter()` clears `SORTED` in every JDK 21 build, or only clears `SIZED`) is implemented in
`StreamOpFlag`'s per-operation flag masks, which this file states at the level the interview
question is actually asked (which flags exist, which optimisations they unlock, the general
direction operations clear them) rather than reproducing `StreamOpFlag`'s full combination table
line by line; the complete enumeration is `AbstractPipeline`/`StreamOpFlag` territory, covered in
guide 08.

> The characteristics bitmask is not descriptive metadata — `DISTINCT` and `SORTED` (with a
> natural-order comparator) can each eliminate their corresponding stream operation entirely at
> evaluation time, while `SIZED`/`SUBSIZED` reduce the cost of sizing and parallel decomposition
> without eliminating any operation outright.

## Open questions

- **Unverified:** the precise, complete per-operation `StreamOpFlag` clearing rules (exactly which
  flags `filter`, `map`, `flatMap`, `peek`, and `distinct` each clear or preserve in the JDK 21
  `ReferencePipeline` implementation) were not individually re-derived from source in this file —
  the general direction of each is stated where confidently known, and the exhaustive
  per-operation table is deferred to guide 08's `StreamOpFlag` treatment, which owns that
  mechanism.

---

## Pitfalls

### Assuming a `HashMap`-backed stream splits its elements evenly under `.parallelStream()`

**Wrong**

```java
Map<String, CardDeposit> byDepositId = loadCapturedCardDeposits().stream()
        .collect(Collectors.toMap(CardDeposit::depositId, d -> d));
// Assumed: 4 cores each get exactly 1/4 of the 95,000 entries, evenly.
long total = byDepositId.values().parallelStream()
        .mapToLong(d -> d.amount().longValue())
        .sum();
// Correct total, but timed on a real profiler, one worker thread's leaf task
// processes visibly more elements than another's, because the bucket-range
// split (§5) only bisects the table index range, not the element count.
```

**Right**

```java
// If even distribution across parallel workers actually matters for latency
// (not just correctness of the final sum), collect to an ArrayList first —
// its spliterator's index-range split is genuinely even at every level:
List<CardDeposit> evenlySplittable = new ArrayList<>(byDepositId.values());
long total = evenlySplittable.parallelStream()
        .mapToLong(d -> d.amount().longValue())
        .sum();
```

**Why people believe it:** "parallel" is read as "divides work evenly by definition," and for
`ArrayList` that intuition happens to be correct, so it generalises unexamined to every other
`Collection` — but `SIZED` only promises the *total* is known, never that a split bisects the
*population*, and only index-addressable structures make that stronger guarantee.

### Assuming `LinkedList.parallelStream()` is free parallelism

**Wrong**

```java
LinkedList<StakeReservation> reservations = new LinkedList<>(loadOpenReservations());
// Assumed: more cores, so this is at least as fast as the sequential version.
BigDecimal totalStaked = reservations.parallelStream()
        .map(StakeReservation::stake)
        .reduce(BigDecimal.ZERO, BigDecimal::add);
// Measured: slower than reservations.stream() at realistic volumes, because
// every trySplit() pays an O(batch-size) linked walk (§5) to produce a piece,
// and that cost is paid on the critical path before any parallel work starts.
```

**Right**

```java
// Convert to an index-addressable structure before parallelising:
List<StakeReservation> asArrayList = new ArrayList<>(loadOpenReservations());
BigDecimal totalStaked = asArrayList.parallelStream()
        .map(StakeReservation::stake)
        .reduce(BigDecimal.ZERO, BigDecimal::add);
```

**Why people believe it:** the API surface of `Collection.parallelStream()` is identical regardless
of the backing structure, so nothing at the call site signals that the cost model underneath is
wildly different; the only way to know is to have read §5's per-collection breakdown, or to have
profiled it and been surprised.

### Forgetting to mutate `this` inside a hand-written `trySplit()`

**Wrong**

```java
@Override
public Spliterator<StakeReservation> trySplit() {
    int remaining = toExclusive - fromInclusive;
    if (remaining < 2) return null;
    int mid = fromInclusive + (remaining >>> 1);
    // BUG: returns the prefix but never shrinks `this` — the range
    // [fromInclusive, mid) is now covered by BOTH spliterators.
    return new SettlementRingBufferSpliterator(ring, fromInclusive, mid);
}
```

**Right**

```java
@Override
public Spliterator<StakeReservation> trySplit() {
    int remaining = toExclusive - fromInclusive;
    if (remaining < 2) return null;
    int mid = fromInclusive + (remaining >>> 1);
    Spliterator<StakeReservation> prefix =
            new SettlementRingBufferSpliterator(ring, fromInclusive, mid);
    this.fromInclusive = mid; // shrink `this` to the suffix — the contract in §4
    return prefix;
}
```

**Why people believe it:** the interface's javadoc states the mutation requirement in prose
("elements ... will, upon return from this method, not be covered by this Spliterator"), not in
the method signature, so nothing in the compiler or the IDE flags a `trySplit()` that forgets it;
the bug is invisible under sequential streams and only manifests as duplicated output once
`.parallel()` actually invokes `trySplit()`.

---

## Cheat sheet

| Fact | Value / rule |
|---|---|
| Interface methods | `tryAdvance`, `forEachRemaining` (default: loop `tryAdvance`), `trySplit`, `estimateSize`, `getExactSizeIfKnown` (default: `-1` unless `SIZED`), `characteristics`, `hasCharacteristics` (all-of test), `getComparator` (throws unless `SORTED`) |
| `DISTINCT` | `0x01` — no duplicate elements |
| `SORTED` | `0x04` — encounter order matches `getComparator()` |
| `ORDERED` | `0x10` — defined encounter order exists |
| `SIZED` | `0x40` — `estimateSize()` is exact right now |
| `NONNULL` | `0x100` — no element is `null` |
| `IMMUTABLE` | `0x400` — source cannot be structurally modified |
| `CONCURRENT` | `0x1000` — source tolerates concurrent modification |
| `SUBSIZED` | `0x4000` — every split also reports exact size, recursively |
| `SIZED | SUBSIZED` combined | `ORDERED\|SIZED\|SUBSIZED` = `0x4050` (`ArrayList`) |
| `SIZED` but not `SUBSIZED` | balanced tree (javadoc's own example); `HashMap` |
| `trySplit()` direction | returned piece = prefix; `this` mutated to keep the suffix |
| `trySplit()` returns `null` | means "won't split further," not "exhausted" |
| `ArrayList` split | index-range halving, O(1), `ORDERED\|SIZED\|SUBSIZED` |
| `HashMap` split | bucket-table range halving, O(1) split but uneven population, `SIZED` only |
| `LinkedList` split | doubling batch (1,024 → 33,554,432 cap), O(batch) per split, never `SUBSIZED` |
| `Files.lines` split | same batching mechanism, serial `BufferedReader` I/O underneath |
| `IteratorSpliterator` batch sizes | `BATCH_UNIT = 1 << 10` = 1,024; doubles; `MAX_BATCH = 1 << 25` = 33,554,432 |
| Build-your-own base classes | `Spliterators.AbstractSpliterator<T>` (batching `trySplit`), plus `AbstractIntSpliterator`/`AbstractLongSpliterator`/`AbstractDoubleSpliterator` |
| Splits well requires | O(1)-ish `trySplit`, correct prefix/suffix mutation, honest `SIZED\|SUBSIZED` |
| Late binding | view fixes at first `tryAdvance`/`trySplit`/`forEachRemaining`/size query, not at `spliterator()` call |
| `distinct()`/`sorted()` elision | skipped entirely if upstream already reports `DISTINCT` / `SORTED` with matching comparator |
| Primitive spliterators | `Spliterator.OfInt`/`OfLong`/`OfDouble`, avoid boxing on `Consumer` calls |

---

## Self-test

**Q1.** What is the difference between what `SIZED` promises and what `SUBSIZED` promises?

<details><summary>Answer</summary>

`SIZED` promises that `estimateSize()` on *this* spliterator, right now, is exact — not a
heuristic. `SUBSIZED` is the stronger, recursive promise that if this spliterator is split via
`trySplit()`, the resulting pieces will *also* report an exact size, and so on at every depth. A
structure can honestly have the first property without the second — the balanced-tree example in
§3, where the whole tree's size is cached but subtree sizes are not.

</details>

**Q2.** `trySplit()` is called on a spliterator over an `ORDERED` source. Which half — the returned
spliterator or the original (`this`) — covers the elements that come first in encounter order?

<details><summary>Answer</summary>

The **returned** spliterator covers the prefix (the elements that come first). `this` is mutated in
place to cover only the suffix. This is fixed by the interface's own javadoc contract and is what
lets recursive parallel splitting preserve encounter order without any extra coordination.

</details>

**Q3.** Why does `ArrayList`'s spliterator parallelise well while `LinkedList`'s does not, given
that both implement the same interface?

<details><summary>Answer</summary>

`ArrayList`'s spliterator splits by index-range halving — a single unsigned-shift midpoint
calculation over two `int`s, O(1) regardless of range size, and the same O(1) cost applies
recursively at every depth, which is why it also earns `SUBSIZED`. `LinkedList` has no index to
bisect, so its spliterator falls back to a doubling-batch scheme: each `trySplit()` call must
physically walk forward through the list to collect the batch it hands off, an O(batch-size)
operation. At realistic volumes the cost of producing each split piece is comparable to or larger
than the work the split was meant to distribute, and `LinkedList`'s spliterator never earns
`SUBSIZED` either, since batch sizes are only known after the walk that produces them.

</details>

**Q4.** A `Spliterator` reports `DISTINCT`. What is the JDK actually promising, and what stream
operation can this let the pipeline skip entirely?

<details><summary>Answer</summary>

It promises that no two elements the spliterator will ever hand over are `.equals()` to each other.
If a `distinct()` call appears downstream and the upstream spliterator already reports `DISTINCT`
(and no intervening operation like `map`/`flatMap` has cleared the flag), the pipeline can skip the
deduplication work entirely — no `HashSet` is built, no `equals`/`hashCode` calls happen — because
the guarantee is already satisfied by construction.

</details>

**Q5.** Why does `HashMap`'s spliterator report `SIZED` but not `SUBSIZED`, even though it splits
over the bucket table in O(1), the same way `ArrayList` splits over its index range in O(1)?

<details><summary>Answer</summary>

Splitting the bucket-table index range in half is indeed O(1), same as `ArrayList`. But bisecting
the *table range* does not bisect the *element count* evenly — elements are distributed across
buckets according to hash values, which are not guaranteed (and in practice rarely happen) to split
50/50 across any given table-index midpoint. The map's overall element count is cached and known,
so `SIZED` is honest; but the split-off piece's actual population is not knowable without walking
it, so `SUBSIZED` cannot be honestly claimed.

</details>

**Q6.** What does `Spliterators.spliteratorUnknownSize` actually give you, and what does it not
give you, compared to a spliterator with a genuine structural split?

<details><summary>Answer</summary>

It gives you *some* splitting capability via the doubling-batch fallback (`IteratorSpliterator`):
the first `trySplit()` pulls a batch of 1,024 elements, the next doubles to 2,048, and so on up to
33,554,432, each returned as an array-backed (and therefore well-behaved) split piece. It does not
give you `SIZED` (the total remains `Long.MAX_VALUE` until the source is exhausted) or `SUBSIZED`
(future batch sizes are never knowable in advance), so the parallel engine's size-based
decomposition heuristics degrade to guesswork, and the early, small batches mean a lot of the
source may be processed before splitting has ramped up to a size that actually helps.

</details>

**Q7.** You write a custom `trySplit()` that computes the midpoint and constructs a new
spliterator over the prefix range, but the split-off elements show up twice in the final parallel
result. What is the most likely bug?

<details><summary>Answer</summary>

`trySplit()` returned the prefix piece but never mutated `this` to shrink its own range to the
suffix. Both the returned spliterator and the original now cover the overlapping prefix range, so
every element in that range is traversed twice — once by each spliterator — which shows up as
duplicated output specifically under `.parallel()`, since sequential execution never calls
`trySplit()` at all.

</details>

**Q8.** What does "late-binding" mean for a spliterator, and what is the practical consequence for
detecting concurrent modification?

<details><summary>Answer</summary>

A late-binding spliterator does not commit to a view of its source's state until the *first* call
to `tryAdvance`, `forEachRemaining`, `trySplit`, or a size query — not at the moment
`spliterator()` was called. The practical consequence is that structural modifications made to the
source *before* that first call are invisible to the spliterator and simply become part of the data
it binds to; only modifications made *after* the first call are detected (via a captured
`modCount` comparison) and throw `ConcurrentModificationException`.

</details>

**Q9.** Why is parallelising `Files.lines(path)` less effective than the presence of a working
`trySplit()` might suggest?

<details><summary>Answer</summary>

`Files.lines` is backed by a `BufferedReader`'s line iterator, adapted through the same
doubling-batch `IteratorSpliterator` mechanism as any other `Iterator`-only source. Each batch is
still produced by repeated, sequential `BufferedReader.readLine()` calls against one file handle —
line boundaries can only be found by scanning through the bytes between them, so there is no way to
"jump ahead" to read a later portion of the file without first reading through everything before
it. Splitting exists at the stream level, but the underlying I/O work it distributes is still
fundamentally serial.

</details>

**Q10.** Name one optimisation `SORTED` enables and state the exact condition under which it
applies.

<details><summary>Answer</summary>

If a `sorted()` call with no explicit `Comparator` argument appears in the pipeline, and the
upstream spliterator already reports `SORTED` with a natural-order comparator (i.e.
`getComparator()` returns `null`, per the interface's contract that `getComparator()` only throws
when `SORTED` is absent), the pipeline can skip the sort pass entirely as a no-op, because the
elements are already guaranteed to arrive in the requested order.

</details>

---

## Deferred

None.

---

**Leaves covered:** 3.4.1–3.4.14 (14 leaves)
**Leaves deferred:** none
**Diagrams included:** D-135, D-136, D-137, D-138
**Target version:** Java 21 LTS
**Lines:** 1264
