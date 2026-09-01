# `ArrayList` — 02 Position in the collections map

**Target version: Java 21 LTS.** | [Map](00-map.md)
Assumes: the size-versus-capacity distinction and the four non-guarantees (file 01).
Previous: [01 What an `ArrayList` guarantees](01-what-an-array-list-guarantees.md) · Next: [03 The complete member surface](03-the-complete-member-surface.md)

File 01 fixed what an `ArrayList` promises in isolation — a positional index,
`O(1)` amortised append, no synchronisation, nulls allowed. None of that says
where `ArrayList` sits relative to everything else that also calls itself a
list, a collection, or an iterable, or why a method that hands you back a
`List<E>` can be lying to you about which concrete class you actually hold.
This file answers that: the two supertype spines `ArrayList` climbs, the one
marker interface that changes which algorithm the JDK picks for you, and the
six other types that could plausibly have been chosen instead.

## The map before the streets

Two chains meet at `ArrayList`. One is interfaces — the *contract* spine.
The other is abstract classes — the *implementation-sharing* spine. Every
member `ArrayList` exposes came down one of these two lines, and file 03 is
going to walk that lineage member by member. Here is the shape first.

![The spine is the one relationship that matters: every `ArrayList` is a `List`, and since 21 every `List` is a `SequencedCollection`.](diagrams/D-02-hierarchy-spine.svg)

Read it as two independent facts stacked on one class. `ArrayList` is a
`List`, and therefore (since Java 21) a `SequencedCollection`, and therefore a
`Collection`, and therefore an `Iterable` — that is what you can *do* with an
`ArrayList` through its declared type. Separately, `ArrayList extends
AbstractList extends AbstractCollection` — that is where the *code* backing
those methods actually lives, and it is almost entirely overridden. `Cloneable`
and `Serializable` hang off to the side as pure markers with zero members
each, and so does `RandomAccess`, which gets its own concept below because,
unlike the other two markers, code actually branches on it.

### The interface spine — `Iterable` → `Collection` → `SequencedCollection` → `List`

**Mental model.** Think of the interface spine as four widening promises, each
one a strict superset of what the one below it can do. `Iterable` promises
"you can hand me to a for-each loop." `Collection` promises "I have a size, I
can be searched and bulk-mutated." `SequencedCollection` promises "I have a
well-defined first and last, and you can address either end and get a
reversed view." `List` promises "every element also has a numeric position."
`ArrayList` sits at the narrow end holding all four promises simultaneously —
it is the only widely-used type in this file's sibling table for which every
one of the four is true and cheap.

**Why it exists.** Before Java 21 the JDK had first/last vocabulary
(`getFirst`, `addLast`, `removeFirst`) scattered independently across `Deque`
and `SortedSet`, with no shared name and no shared type. A method that wanted
"give me the first and last element, whatever ordered collection you are" had
nothing to declare as its parameter type. JEP 431 retrofitted
`SequencedCollection` as the missing rung between `Collection` and both
`List` and `Deque`, so `getFirst()`/`getLast()`/`reversed()` became one
vocabulary instead of two.

**When it applies, and when it does not.** Reach for `List` as a declared
type whenever position matters — you will call `get(i)`, `set(i, v)`, or rely
on iteration order matching insertion order. Reach for the bare `Collection`
interface when a caller only needs to iterate and count, and reach for `Set`
or `Map` instead of any of this spine when the domain concept has no natural
position at all — `GateSet`'s `gates: Map<GateType, Verdict?>` (Appendix C.6)
is keyed by gate type precisely because "the third gate" is not a meaningful
idea; forcing it into a `List` would manufacture an ordering the domain never
asked for.

**How it works.** `javap -protected` on JDK 21.0.7 gives the exact
contribution of each rung (packet §15). `Iterable` contributes three members —
`iterator()` abstract, `forEach` and `spliterator()` as defaults — and it is
`Iterable.iterator()` that the for-each loop desugars to, which is why
`for (LedgerEntry e : movement.entries())` is fail-fast: it is driven by an
`Iterator`, and file 04 covers what "fail-fast" costs. `Collection` adds 21
members, but on a live `ArrayList` call only three of its default bodies
ever run unmodified — `stream()`, `parallelStream()`, and
`toArray(IntFunction)` — because `ArrayList` overrides everything else
`Collection` declares, including `removeIf`. `stream()`'s default body is
`StreamSupport.stream(spliterator(), false)`, which is why `ArrayList`'s
spliterator characteristics (`ORDERED | SIZED | SUBSIZED`, file 03) matter to
every stream built over it. `SequencedCollection` adds seven members —
`reversed()` abstract, six default accessors — and `ArrayList` overrides all
six accessors with direct index arithmetic but leaves `reversed()` alone;
that one method runs `List`'s default and returns a
`java.util.ReverseOrderListView$Rand`, a live, write-through view, not a
copy. `List` itself contributes the positional contract — `get(int)`,
`set(int,E)`, `add(int,E)`, `remove(int)`, `indexOf`, `lastIndexOf`,
`listIterator`, `subList` — the specified `equals`/`hashCode` algorithms, and
thirteen static factories (`List.of()` through `List.of(E...)`,
`List.copyOf`).

**A minimal concrete demonstration.**

```java
// Movement.entries is declared List<LedgerEntry> (Appendix C.2) — never
// ArrayList<LedgerEntry>. The constructor below hands back an immutable
// list, and every caller that only knows the interface still compiles.
public List<LedgerEntry> postedEntries(Movement movement) {
    return List.copyOf(movement.entries());   // ImmutableCollections$ListN
}

// ProfileService merges transactions from two schemas (§7.3) and must
// return List<WithdrawalTransaction>, not ArrayList<...> — the merge step
// may itself change concrete type (sorted copy, filtered view) without
// breaking any of the eight callers that assembled the profile.
public List<WithdrawalTransaction> allWithdrawals(ClientId id) {
    List<WithdrawalTransaction> merged = new ArrayList<>(cardWithdrawals(id));
    merged.addAll(bankWithdrawals(id));
    merged.sort(Comparator.comparing(WithdrawalTransaction::postedAt));
    return merged;   // declared List<...> at the call site; concrete type is an implementation detail
}
```

**The gotcha.** `postedEntries` above returns something that is a `List` but
is not an `ArrayList` — calling code that does `(ArrayList<LedgerEntry>)
postedEntries(m)` throws `ClassCastException` at runtime with no compile-time
warning, because the declared return type was honestly `List<LedgerEntry>`
all along. Casting down from an interface to a concrete class is always a
smell; it means the caller wanted a guarantee the interface does not make.

> **`ArrayList` is one concrete answer to four separately-useful interface
> questions — iterable, collection, sequenced, positional — and the widening
> chain is why a method can accept an `ArrayList` argument as any of the
> four without the caller ever naming `ArrayList`.**

### The abstract-class spine — `AbstractCollection` → `AbstractList`

**Mental model.** Where the interface spine is about *what you can call*, the
abstract-class spine is about *whose code actually runs* when you call it.
Picture two increasingly complete "starter kits": `AbstractCollection` gives
you generic, iterator-driven implementations of everything above `iterator()`
and `size()`; `AbstractList` gives you generic, index-driven implementations
of everything above `get(int)` — plus one piece of mutable state neither
interface can express, `modCount`. `ArrayList` accepts the state and rejects
almost all of the generic code.

**Why it exists.** Before `AbstractList` existed, every `List` implementer —
array-backed, node-backed, or a thin wrapper — had to write its own
`equals`, `hashCode`, `indexOf`, and iterator from scratch, even though those
are mechanically identical for *any* correctly-implemented `get(int)` and
`size()`. `AbstractList` writes them once, in terms of the two abstract
primitives, so a minimal custom `List` needs only to supply `get` and `size`
to become fully functional, if slow.

**When it applies, and when it does not.** The generic, iterator-driven
implementations are the right choice for a brand-new `List` you are writing
from scratch and have not yet optimised — inherit from `AbstractList`, supply
`get(int)` and `size()`, and you have a correct (if `O(n)` in places) list
for free. They are the wrong choice the moment random access is cheap, which
is exactly `ArrayList`'s situation, and that is why `ArrayList` overrides
essentially the entire surface rather than inheriting it.

**How it works.** From packet §15: `AbstractList` declares 17 members plus
the `modCount` field, but `ArrayList` overrides every method on that list.
**The only things that survive from `AbstractList` into a live `ArrayList`
call are the `modCount` field itself, the `subListRangeCheck` helper, and the
inherited `SubList` superclass machinery** (file 03 walks `SubList`
directly). `modCount` is the single piece of state that makes fail-fast
iteration possible at all — every structural mutation increments it, every
iterator captures it at creation and compares on each `next()`/`remove()`.
`AbstractCollection` declares 15 members; `ArrayList` overrides all but two.
**`containsAll(Collection<?>)` and `toString()` are the only two
`AbstractCollection` bodies an `ArrayList` call ever actually executes.**
`containsAll`'s inherited body is `for (Object e : c) if (!contains(e)) return
false;` — a `contains` call per element of the argument, and `ArrayList.contains`
is itself `O(n)`, so `containsAll` on an `ArrayList` is **O(n·m)**, a real
trap the next section returns to when picking a sibling. `toString()` builds
`[a, b, c]` through the iterator and returns `"[]"` for an empty list.

**A minimal concrete demonstration.**

```java
List<Id> paidItemIds = new ArrayList<>(paymentRun.itemIds());
List<Id> flaggedForReview = fetchFlaggedIds();

// containsAll inherited from AbstractCollection: O(n·m) here, not O(n).
// n = paidItemIds.size(), m = flaggedForReview.size() — both can be in the
// thousands for a single PaymentRun (Appendix C.2), so this call is a
// quiet quadratic scan hiding behind one method name.
boolean anyFlaggedAlreadyPaid = paidItemIds.containsAll(flaggedForReview);
```

**The gotcha.** `containsAll` reads like a single membership test and is
actually `n` linear scans. Swap `paidItemIds` for a `HashSet<Id>` before the
call and the same line becomes `O(m)` — the fix is never inside `containsAll`,
it is choosing a structure whose `contains` is `O(1)` before you call it.

> **`AbstractList`/`AbstractCollection` exist to give a from-scratch `List`
> correct behaviour for free; `ArrayList` keeps only `modCount`,
> `subListRangeCheck`, `containsAll`, and `toString` from that inheritance —
> everything else is overridden for speed.**

## `RandomAccess` — the marker that changes which algorithm runs

**Mental model.** `RandomAccess` has zero members — packet §15 confirms it,
`javap` shows an empty interface body. It is a note taped to a class that
says "indexed `get(i)` on me costs the same regardless of `i`," nothing more.
It changes no compiler behaviour and no method signature; it only changes
what *other code that checks for it* decides to do.

**Why it exists.** Generic algorithms in `Collections` — binary search,
shuffle, reverse, rotate — can be written two ways: walk with `get(i)` in a
counted loop, or walk with an `Iterator`/`ListIterator`. The counted-loop
version is fast on an array-backed list and catastrophic on a node-backed
one; the iterator version is the reverse. `RandomAccess` lets one method body
pick the right strategy at runtime instead of forcing every caller to know
which concrete `List` they hold.

**When it applies, and when it does not.** `ArrayList` implements it;
`LinkedList` does not. `Collections.binarySearch`, `Collections.shuffle`,
`Collections.fill`, `Collections.reverse`, `Collections.copy`,
`Collections.indexOfSubList`, `Collections.rotate`, and the callers behind
`Collections.swap` all branch on `instanceof RandomAccess` (packet §15) to
choose the counted-index path when it is present and an iterator-pair path
when it is not. The same rule extends to your own code: any loop of the
shape `for (int i = 0; i < list.size(); i++) list.get(i)` should first ask
"is this list `RandomAccess`?" — file 05 proves the arithmetic behind why
that check matters, but the one-sentence mechanism is that array-backed
access hits contiguous cache lines while node-backed access chases a pointer
per step, and pointer chasing does not pipeline.

**How it works.** No diagram for this concept — the manifest assigns this
file exactly one diagram, D-02, already placed above; a marker interface with
zero members has no shape worth drawing beyond the spine it hangs off. The
mechanism is entirely in the *consuming* code, not in `ArrayList` itself:
`Collections.binarySearch`, for instance, is really two private methods,
`indexedBinarySearch` and `iteratorBinarySearch`, and the public entry point
picks between them with an `instanceof RandomAccess` test before doing any
comparisons. `ArrayList` pays nothing at runtime for implementing the
interface — no field, no method, no allocation — the entire cost of the
marker is paid by algorithms that check for it, and the entire benefit is
that they check at all.

**A minimal concrete demonstration.**

```java
static <T> void visitInOrder(List<T> list, Consumer<T> visitor) {
    if (list instanceof RandomAccess) {
        for (int i = 0, n = list.size(); i < n; i++) {
            visitor.accept(list.get(i));   // cheap here: ArrayList, PaymentRun.itemIds
        }
    } else {
        for (T element : list) {
            visitor.accept(element);        // required here: any node-backed List
        }
    }
}
```

The figures this pays for are measured, not guessed, and file 05 derives the
mechanism behind them: a 200 000-element `for-each` over an `ArrayList` runs
in 103 µs against 329 µs for the same walk over a `LinkedList` — **3.2×**
slower at identically `O(n)` — and reading the first 20 000 of 200 000
elements from a `LinkedList` with `get(i)` costs 352 ms, roughly **3 500×**
the cost of scanning the *entire* 200 000-element `ArrayList` (packet §16).
`RandomAccess` is the flag that tells generic code which side of that gap a
given list is on before it commits to a loop shape.

**The gotcha.** `Arrays.asList(arr)`, `Collections.unmodifiableList(list)`
(when wrapping an `ArrayList`), and `List.of(...)` all implement
`RandomAccess` too — the marker travels with array-backed storage, not with
mutability or with the `ArrayList` class name specifically. Checking
`instanceof ArrayList` where you mean "is index access cheap" both misses
these and wrongly excludes any future `RandomAccess`-backed `List`
implementation that is not literally `ArrayList`.

> **`RandomAccess` is a zero-member performance promise, not a behavioural
> one: named `Collections` algorithms and well-written generic code branch on
> it to choose a counted-index loop over an iterator loop, and an `ArrayList`
> pays nothing to advertise it.**

## The sibling family

**Mental model.** Six other types answer roughly the question "give me an
ordered collection of elements" and each earns its place by refusing to be
`ArrayList` in exactly one respect — thread-safety, mutability, or which end
gets the cheap operation. Knowing `ArrayList`'s spine only pays off once you
can say, for each sibling, the one sentence that would make you pick it
instead.

**Why it exists.** No single implementation can be simultaneously mutable,
immutable, thread-safe without locking, cheap at both ends, and array-backed
— those are conflicting design goals, so the JDK offers one type per
combination rather than one type with a dozen flags.

**When it applies, and when it does not.** This is the comparison itself —
see the table. The short version: pick `ArrayList` unless you specifically
need one of the other columns' single distinguishing job.

**How it works — the sibling comparison table.** Three or more things doing
a similar job get a table, not paragraphs:

| Type | Backing | Distinguishing job | Cost you pay for it |
|---|---|---|---|
| `ArrayList` | resizable `Object[]` | general-purpose, index-cheap, mutable | amortised `O(1)` append; `O(n)` insert/remove at front (file 05) |
| `LinkedList` | doubly-linked nodes | cheap insert/remove **given a `ListIterator` positioned there already** | `get(i)` is `O(n)` — 3 500× the cost of an `ArrayList` scan over the same range (packet §16); 6× the per-element memory overhead (24-byte `Node` versus a 4-byte compressed oop, packet §16) |
| `ArrayDeque` | circular array | insert/remove at **both ends**, no per-element node | not a `List` at all — no positional `get(i)`; rejects `null` (packet §18) |
| `Vector` | resizable `Object[]` | every method `synchronized` | doubling growth by default (not 1.5×, unlike `ArrayList`), and per-call lock overhead even single-threaded |
| `CopyOnWriteArrayList` | resizable `Object[]`, replaced wholesale on write | iterator is a **snapshot**, never throws `ConcurrentModificationException` | `O(n)` array copy on **every** mutation (packet §18) — fits read-mostly listener lists, not general concurrent use |
| `List.of(...)` / `List.copyOf(...)` | `ImmutableCollections$List12` or `$ListN` | structurally immutable, rejects `null` elements | any mutator throws `UnsupportedOperationException`; `List.of("x", null)` throws `NullPointerException` at construction (packet §16) |
| `Arrays.asList(arr)` | the caller's own `arr` | `set` writes through to `arr` | fixed-size — `add`/`remove` throw `UnsupportedOperationException`; **not** an `ArrayList` despite the name (packet §16) |

**A minimal concrete demonstration.** Three list-shaped fields from Appendix
C.2/C.6 resolve to three different answers, and none of them is "just use
`ArrayList` everywhere":

```java
// Movement.entries: "Immutable list" per Appendix C.6 — append-only means
// no mutation is ever legitimate, so the field itself should hold what
// List.copyOf hands back, not a plain ArrayList a caller could mutate.
record Movement(MovementId id, List<LedgerEntry> entries, MovementReason reason) {
    Movement {
        entries = List.copyOf(entries);   // ImmutableCollections$ListN — defensive and final
    }
}

// PaymentRun.itemIds: grows one item at a time as items are added to the
// run, is read back in bulk, and needs no special end- or thread-behaviour.
// A plain ArrayList<Id> is the correct, unglamorous choice.
List<Id> itemIds = new ArrayList<>();

// Reservation expiry index (Appendix C.6): "Priority queue by expiresAt" —
// the field is list-shaped in the sense that it holds many Reservations,
// but the access pattern is "give me the soonest expiry," not "give me
// element i," so the right structure is not List at all. Forcing it into
// an ArrayList would mean a linear scan for the minimum on every check;
// PriorityQueue makes that a log-time peek.
PriorityQueue<Reservation> expiryIndex =
    new PriorityQueue<>(Comparator.comparing(Reservation::expiresAt));
```

**The gotcha.** `Arrays.asList(arr).set(0, v)` succeeds and **mutates `arr`
itself** — the two are the same backing array, not a copy — while
`List.of("x").set(0, v)` throws `UnsupportedOperationException` because
`List.of` never exposes a backing array at all. Both are "a `List` you got
back from a factory method"; only reading the sibling table tells you which
failure mode you inherited.

> **The sibling family is not six variations on `ArrayList` — each one trades
> away exactly one of `ArrayList`'s properties (index cost, mutability,
> single-threaded assumption, or "is a `List` at all") to buy a property
> `ArrayList` cannot offer.**

## Pitfalls

### "It's a `List`, so it must support `add`"

**Wrong**
```java
List<Id> ids = Arrays.asList(paymentRun.itemIds().toArray(new Id[0]));
ids.add(newId);
// java.lang.UnsupportedOperationException
//     at java.base/java.util.AbstractList.add(AbstractList.java:155)
//     at java.base/java.util.AbstractList.add(AbstractList.java:113)
```

**Right**
```java
List<Id> ids = new ArrayList<>(List.of(paymentRun.itemIds().toArray(new Id[0])));
ids.add(newId);   // fine — genuine ArrayList, not Arrays$ArrayList
```

**Why people believe it:** `Arrays.asList` returns something typed `List<T>`
and answers `instanceof List` as `true`; nothing in the type system flags
that it is fixed-size until the throwing call happens at runtime.

### "`instanceof ArrayList` is how you check for fast indexing"

**Wrong**
```java
if (list instanceof ArrayList) {
    for (int i = 0; i < list.size(); i++) fast(list.get(i));
}
// misses List.of(...), Arrays.asList(...), Collections.unmodifiableList(arrayList) —
// all RandomAccess, none of them an ArrayList
```

**Right**
```java
if (list instanceof RandomAccess) {
    for (int i = 0; i < list.size(); i++) fast(list.get(i));
} else {
    for (T element : list) fast(element);
}
```

**Why people believe it:** `ArrayList` is the `RandomAccess` type most
engineers meet first, so the class name and the marker interface blur
together even though the marker is what every JDK algorithm actually checks.

### "`containsAll` is a fast membership check"

**Wrong**
```java
// paidItemIds: 40 000 elements. flaggedForReview: 3 000 elements.
// 120 000 000 equals() calls, silently, inside one method name.
boolean overlap = paidItemIds.containsAll(flaggedForReview);
```

**Right**
```java
Set<Id> paidSet = new HashSet<>(paidItemIds);
boolean overlap = paidSet.containsAll(flaggedForReview);   // O(m), each contains() is O(1)
```

**Why people believe it:** `containsAll` reads as a single verb with no size
parameter in the name, and the `Collection` interface documents *what* it
returns, not *how expensive* computing it is on the receiver's concrete type.

## Cheat sheet

| Question | Answer |
|---|---|
| Interface spine | `Iterable` → `Collection` → `SequencedCollection` (Java 21+) → `List` |
| Abstract-class spine | `AbstractCollection` → `AbstractList` → `ArrayList` |
| What survives from `AbstractList` at runtime | `modCount`, `subListRangeCheck`, inherited `SubList` machinery — everything else overridden |
| What survives from `AbstractCollection` at runtime | `containsAll` (O(n·m) trap), `toString()` only |
| `List` method `ArrayList` does **not** override | `reversed()` — runs `List`'s default, returns `ReverseOrderListView$Rand` |
| `Collection` defaults `ArrayList` does **not** override | `stream()`, `parallelStream()`, `toArray(IntFunction)` |
| `RandomAccess` member count | 0 — pure performance marker |
| Named `RandomAccess` consumers | `Collections.binarySearch`, `.shuffle`, `.fill`, `.reverse`, `.copy`, `.indexOfSubList`, `.rotate`, `.swap`'s callers |
| `LinkedList` for-each vs `ArrayList` for-each | 3.2× slower, same O(n) |
| `LinkedList.get(i)` first 20k of 200k vs full `ArrayList` scan | ~3 500× slower |
| Fixed-size, write-through | `Arrays.asList(arr)` |
| Structurally immutable, rejects `null` | `List.of(...)`, `List.copyOf(...)` |
| Cheap at both ends, not a `List` | `ArrayDeque` |
| Every method `synchronized`, doubling growth | `Vector` |
| Copies whole array per write, snapshot iterator | `CopyOnWriteArrayList` |

## Self-test

**Q1.** Name the four interfaces on `ArrayList`'s contract spine, in order from most general to most specific.

<details><summary>Answer</summary>

`Iterable` → `Collection` → `SequencedCollection` → `List`. `SequencedCollection` is new in Java 21 (JEP 431); before that, `List` sat directly on `Collection`.

</details>

**Q2.** `ArrayList` overrides nearly every method it inherits from `AbstractList` and `AbstractCollection`. Name the members that survive unoverridden, and what each is used for.

<details><summary>Answer</summary>

From `AbstractList`: the `modCount` field (fail-fast state), `subListRangeCheck`, and the inherited `SubList` superclass machinery. From `AbstractCollection`: `containsAll` (an `O(n·m)` scan via repeated `contains`) and `toString()` (builds `[a, b, c]` via the iterator).

</details>

**Q3.** Which `List` method does `ArrayList` inherit rather than override, and what type does calling it actually produce?

<details><summary>Answer</summary>

`reversed()`. It runs `List`'s default implementation and produces a `java.util.ReverseOrderListView$Rand` — a live, write-through view, not a copy or a new `ArrayList`.

</details>

**Q4.** What does `RandomAccess` guarantee behaviourally, and what does it actually promise?

<details><summary>Answer</summary>

Nothing behavioural — it has zero members. It is a performance promise: that `get(i)` costs the same for any `i`, which lets algorithms like `Collections.binarySearch` and `Collections.shuffle` pick a counted-index loop instead of an iterator loop when the flag is present.

</details>

**Q5.** Give two types other than `ArrayList` that also implement `RandomAccess`.

<details><summary>Answer</summary>

Any array-backed `List`: `Arrays.asList(arr)`, `List.of(...)`/`List.copyOf(...)`, and `Collections.unmodifiableList(arrayList)` (it wraps `UnmodifiableRandomAccessList` specifically when the backing list is `RandomAccess`).

</details>

**Q6.** `paidItemIds.containsAll(flaggedForReview)` is slow on two large `ArrayList`s. Why, and what is the fix?

<details><summary>Answer</summary>

`containsAll` is inherited from `AbstractCollection` as `for (Object e : c) if (!contains(e)) return false;`. `ArrayList.contains` is `O(n)`, so the whole call is `O(n·m)`. Fix: copy the receiver into a `HashSet` first so each `contains` check becomes `O(1)`.

</details>

**Q7.** Why does `Arrays.asList(arr).add(x)` throw but `Arrays.asList(arr).set(0, x)` succeeds and changes `arr`?

<details><summary>Answer</summary>

`Arrays.asList` wraps the caller's own array directly with no resize capability — `set` writes through to that array, but `add`/`remove` would require resizing an array the caller still owns, which the wrapper refuses by throwing `UnsupportedOperationException`.

</details>

**Q8.** Which sibling is the right choice for a structure that needs cheap insertion and removal at both the front and the back, and why is `ArrayList` the wrong choice for that same job?

<details><summary>Answer</summary>

`ArrayDeque` — a circular array with amortised `O(1)` at both ends and no per-element node overhead. `ArrayList` is `O(1)` amortised only at the back; `add(0, e)` on an `ArrayList` is `O(n)` because every existing element shifts (measured at 314 ms for 100 000 front-inserts versus under 1 ms for the same count of back-inserts, packet §16).

</details>

**Q9.** A reservation-expiry tracker needs to always know which open reservation expires soonest. Why is this not a `List` field at all?

<details><summary>Answer</summary>

The access pattern is "give me the minimum `expiresAt`," not "give me element `i`." A `List` (including `ArrayList`) would require an `O(n)` scan to find the minimum on every check; `PriorityQueue`, ordered by `expiresAt`, makes that a log-time operation and is the construct Appendix C.6 actually specifies for this field.

</details>

**Q10.** `Movement.entries` and `PaymentRun.itemIds` are both declared `List<...>` in Appendix C.2, yet the notes recommend two different concrete types for them. Which, and why?

<details><summary>Answer</summary>

`Movement.entries` should be backed by `List.copyOf(...)` (an `ImmutableCollections$ListN`) because entries are append-only and must never be mutated after the movement posts. `PaymentRun.itemIds` should be a plain `ArrayList<Id>` because it grows one item at a time with no immutability requirement and no special end-of-list behaviour.

</details>

---

**Questions answered:** Q-05, Q-06, Q-07
**Sets up:** Next: the complete member surface, and which of those supertypes each member came from.
**Diagrams included:** D-02
**Target version:** Java 21 LTS
**Lines:** 515
