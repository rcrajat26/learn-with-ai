# ArrayList — 03 The Complete Surface

**Target version: Java 21.** | [Map](00-map.md)
Assumes: the type graph (file 02).
Previous: [02-where-it-sits.md](02-where-it-sits.md) · Next: [04-creating-and-obtaining.md](04-creating-and-obtaining.md)

File 02 drew the type graph: `ArrayList extends AbstractList<E> implements
List<E>, RandomAccess, Cloneable, Serializable`, with `List` itself extending
`SequencedCollection` since Java 21. A type graph tells you *what ArrayList is
related to*. It does not tell you *where each of its forty-odd public members
actually comes from*, and that second question is the one interviewers ask when
they say "what does ArrayList actually override?" This file answers it with a
single table, because a member surface is a set of related things, and a set of
related things gets a table before it gets prose.

Every public and protected member falls into exactly one of four buckets, and
those four buckets are the four primary concepts this file teaches:

1. **Declared in `ArrayList` itself, with no supertype declaration at all** —
   the two capacity-management methods that exist only because this
   implementation is array-backed.
2. **Overridden from `AbstractList` or `AbstractCollection`** — the largest
   bucket, and the reason ArrayList exists: turning generic, iterator-based
   implementations into direct array operations.
3. **Inherited and not overridden** — the quiet bucket, and the one most notes
   skip. What ArrayList did *not* bother to specialise, and why that is
   sometimes a performance trap.
4. **Default methods ArrayList chose to override** — including six brand-new
   in Java 21 that arrive through `SequencedCollection`.

The table below is organised into seven finer-grained groups (A through G) so
that lineage — which type declares a member, and which type ArrayList is
overriding — is visible at a glance. The four concepts above are how those
seven groups collapse into the shape worth remembering.

## The complete member table

| Member | Declared in | Since | Returns | Complexity | Notes |
|---|---|---|---|---|---|
| `trimToSize()` | ArrayList | 1.2 | `void` | O(n) (copy) | Shrinks `elementData` to `size`. Bumps `modCount`. |
| `ensureCapacity(int)` | ArrayList | 1.2 | `void` | O(n) worst case | No-op if already large enough. Bumps `modCount` only when it grows. |
| `iterator()` | ArrayList (overrides AbstractList) | 1.2 | `Iterator<E>` | O(1) to obtain | Fail-fast; `Itr` reads `elementData` directly, not through `get`. |
| `listIterator()` | ArrayList (overrides AbstractList) | 1.2 | `ListIterator<E>` | O(1) to obtain | Overridden even though `AbstractList` already implements it, to skip the `get`/`set` indirection. |
| `listIterator(int)` | ArrayList (overrides AbstractList) | 1.2 | `ListIterator<E>` | O(1) to obtain | Same reason. |
| `subList(int,int)` | ArrayList (overrides AbstractList) | 1.2 | `List<E>` | O(1) to obtain | Returns `ArrayList$SubList`, a live view over the parent's array — see file 07. |
| `indexOf(Object)` | ArrayList (overrides AbstractList) | 1.2 | `int` | O(n) | Linear scan using `equals`, `null`-aware. |
| `lastIndexOf(Object)` | ArrayList (overrides AbstractList) | 1.2 | `int` | O(n) | Same scan, from the tail. |
| `clear()` | ArrayList (overrides AbstractList) | 1.2 | `void` | O(n) (nulls slots) | Does **not** shrink the array — capacity survives. |
| `addAll(int,Collection)` | ArrayList (overrides AbstractList) | 1.2 | `boolean` | O(n + m) | One `arraycopy` shift, not m individual shifts. |
| `removeRange(int,int)` | ArrayList (overrides AbstractList) | 1.2 (protected) | `void` | O(n) | Protected; the mechanism `clear()` and `subList().clear()` both call into. |
| `equals(Object)` | ArrayList (overrides AbstractList) | 21 | `boolean` | O(n) | Only in JDK 21+ — see the version trap below. |
| `hashCode()` | ArrayList (overrides AbstractList) | 21 | `int` | O(n) | Same version trap. |
| `add(E)` | ArrayList (overrides AbstractList) | 1.2 | `boolean` | amortised O(1) | Grows only when the backing array is full. |
| `add(int,E)` | ArrayList (overrides AbstractList) | 1.2 | `void` | O(n-index) | Shift cost dominates; growth is the same amortised story on top. |
| `set(int,E)` | ArrayList (overrides AbstractList) | 1.2 | `E` | O(1) | Does not touch `modCount`. |
| `remove(int)` | ArrayList (overrides AbstractList) | 1.2 | `E` | O(n-index) | Index form — see the overload collision below. |
| `get(int)` | ArrayList (overrides AbstractList) | 1.2 | `E` | O(1) | The reason `RandomAccess` is a true claim here. |
| `isEmpty()` | ArrayList (overrides AbstractCollection) | 1.2 | `boolean` | O(1) | `size == 0`, not an iterator check. |
| `contains(Object)` | ArrayList (overrides AbstractCollection) | 1.2 | `boolean` | O(n) | Delegates to `indexOf`. |
| `toArray()` | ArrayList (overrides AbstractCollection) | 1.2 | `Object[]` | O(n) (copy) | `Arrays.copyOf`, always `Object[]` regardless of `E`. |
| `toArray(T[])` | ArrayList (overrides AbstractCollection) | 1.2 | `T[]` | O(n) (copy) | Reuses the argument array if it is large enough; `ArrayStoreException` on element-type mismatch. |
| `remove(Object)` | ArrayList (overrides AbstractCollection) | 1.2 | `boolean` | O(n) | Value form — see the overload collision below. |
| `addAll(Collection)` | ArrayList (overrides AbstractCollection) | 1.2 | `boolean` | O(n + m) | One growth check for the whole batch, not one per element. |
| `removeAll(Collection)` | ArrayList (overrides AbstractCollection) | 1.2 | `boolean` | O(n · contains) | Single-pass compaction via `batchRemove`; O(n) if the argument is a `HashSet`. |
| `retainAll(Collection)` | ArrayList (overrides AbstractCollection) | 1.2 | `boolean` | O(n · contains) | Same `batchRemove` machinery, complemented. |
| `size()` | ArrayList (overrides AbstractCollection) | 1.2 | `int` | O(1) | Abstract in `AbstractCollection`; ArrayList supplies the field read. |
| `forEach(Consumer)` | ArrayList (overrides Iterable default) | 1.2 | `void` | O(n) | Direct array walk with a `modCount` check per element, not an `Iterator` allocation. |
| `spliterator()` | ArrayList (overrides Iterable/Collection/List default) | 1.4 (8 for the override) | `Spliterator<E>` | O(1) to obtain | `ArrayListSpliterator`, `RandomAccess`-aware, splits cheaply — this is what `stream()` rides on. |
| `removeIf(Predicate)` | ArrayList (overrides Collection default) | 8 | `boolean` | O(n) | Bitset mark-then-compact, not O(n²) per-match removal. |
| `replaceAll(UnaryOperator)` | ArrayList (overrides List default) | 8 | `void` | O(n) | In-place array write. |
| `sort(Comparator)` | ArrayList (overrides List default) | 8 | `void` | O(n log n) | TimSort over the backing array; increments `modCount` once. |
| `getFirst()` | ArrayList (overrides SequencedCollection via List) | 21 | `E` | O(1) | `get(0)`; throws `NoSuchElementException` if empty. |
| `getLast()` | ArrayList (overrides SequencedCollection via List) | 21 | `E` | O(1) | `get(size-1)`. |
| `addFirst(E)` | ArrayList (overrides SequencedCollection via List) | 21 | `void` | O(n) | Literally `add(0, e)` — full shift every call. |
| `addLast(E)` | ArrayList (overrides SequencedCollection via List) | 21 | `void` | amortised O(1) | Literally `add(e)` — the asymmetry with `addFirst` is real and worth a row of its own. |
| `removeFirst()` | ArrayList (overrides SequencedCollection via List) | 21 | `E` | O(n) | `remove(0)` — full shift. |
| `removeLast()` | ArrayList (overrides SequencedCollection via List) | 21 | `E` | O(1) | `remove(size-1)` — no shift at all. |
| `clone()` | ArrayList (overrides Object) | 1.2 | `Object` | O(n) (copy) | Shallow — new array, same element references. Resets the clone's `modCount` to 0. |

Inherited and **not** overridden — the surface ArrayList leaves exactly as the
abstract classes wrote it:

| Member | Declared in | Since | Returns | Complexity | Notes |
|---|---|---|---|---|---|
| `containsAll(Collection)` | AbstractCollection | 1.2 | `boolean` | O(n · m) | One `contains` call per element of the argument — O(n) each, so O(n·m) total. Pass a `HashSet` to the *argument* side to make each `contains` O(1). |
| `toString()` | AbstractCollection | 1.2 | `String` | O(n) | Builds through the iterator, not through direct array indexing. |
| `reversed()` | List (default, since 21) | 21 | `List<E>` | O(1) to obtain | Returns `ReverseOrderListView` — a **view**, not a copy. |
| `stream()` | Collection (default) | 8 | `Stream<E>` | O(1) to obtain | Built on `spliterator()`, which *is* overridden, so this inherits the fast split for free. |
| `parallelStream()` | Collection (default) | 8 | `Stream<E>` | O(1) to obtain | Same story. |
| `toArray(IntFunction)` | Collection (default) | 11 | `T[]` | O(n) (copy) | The generator-argument overload; delegates internally to `toArray(T[])`. |

### Reading the groups

**Group A — capacity, ArrayList's own.** `trimToSize` and `ensureCapacity` are
the entire set of members with zero supertype declaration. That is the surface
signature of "this is the array-backed implementation" — nothing generic above
it has an array to trim or a capacity to pre-size.

**Groups B and C — the overrides of `AbstractList` and `AbstractCollection`.**
This is most of the table, and the reason ArrayList exists at all: the generic
versions in the abstract classes go through `get`/`set`/the iterator; the
ArrayList versions go straight at `elementData` with `arraycopy` or a bare
array write.

**Group D — overriding an interface default.** `forEach`, `spliterator`,
`removeIf`, `replaceAll`, `sort` all have a working default somewhere up the
interface chain. ArrayList overrides every one of them for a direct-array
implementation, so relying on the default's iterator-based fallback never
happens here.

**Group E — the Java 21 `SequencedCollection` overrides.** Six methods, all
`@since 21` in the real source, all overriding a default that arrived through
`List extends SequencedCollection`. `addFirst`/`removeFirst` are full-shift
O(n); `addLast`/`removeLast` are the same as `add`/`remove(size-1)`, so O(1)
amortised and O(1) exactly. That asymmetry is the single most interview-ready
row in the table.

**Group F — overriding `Object`.** Just `clone()`. Shallow copy, and a detail
almost nobody checks: the clone starts life with `modCount = 0`, independent of
whatever the source list's `modCount` had reached.

**Group G — inherited and not overridden.** The quiet bucket. `containsAll`
keeps AbstractCollection's O(n·m) shape; `toString` still walks through an
iterator; `reversed()` is a Java 21 default that ArrayList never bothered to
specialise into a copy; `stream()`/`parallelStream()`/`toArray(IntFunction)`
ride on whatever `spliterator()` or `toArray(T[])` already do.

## Reading the table

- **The `remove` overload collision is real and it bites.** `remove(int)`
  comes from `AbstractList`; `remove(Object)` comes from `AbstractCollection`.
  On a `List<Integer>` the two calls look identical to the eye and pick
  different behaviour. Verified: given `[10, 20, 30]`, `list.remove(1)` returns
  `[10, 30]` by **index** — it drops `20`, the element *at* position 1.
  `list.remove(Integer.valueOf(20))` also returns `[10, 30]`, but by **value**
  — it drops the boxed `Integer` equal to `20`. The two calls happen to agree
  here only because the value at index 1 is 20; change either input and they
  diverge. File 07 covers the resolution mechanism.
- ArrayList overrides almost everything the two abstract superclasses provide,
  because the generic versions go through `get`/`set`/the iterator and the
  array-backed versions go straight at `elementData` — that is the entire
  performance case for choosing ArrayList over a hand-rolled `AbstractList`.
- The two capacity methods with no supertype declaration are the cleanest
  one-line answer to "what does ArrayList add beyond being a List": a capacity
  concept, full stop.
- **Version trap:** `equals`/`hashCode` are overridden in ArrayList as of JDK
  21 (also true in JDK 11 through 17) but were **not** overridden in JDK 8 —
  there, both were inherited straight from `AbstractList`. An interviewer who
  learned this class from an 8-era book may state the old fact with
  confidence. File 14 has the full differential source reading.

## The four concepts, in depth

### The declared-in-ArrayList set

**Mental model.** Picture ArrayList as `AbstractList` plus exactly one extra
knob: a spare-capacity dial. Every other member either specialises something
the abstract classes already promised, or arrives free from an interface.
`trimToSize` and `ensureCapacity` are the dial itself — turn it down to release
memory, turn it up to avoid repeated growth.

**Why it exists.** `List` as a contract has no notion of "how much room is
reserved beyond the live elements" — that is an implementation detail of being
array-backed. Only a class that owns an array can expose a knob for its slack.

**When it applies, and when it does not.** `ensureCapacity` pays off before a
bulk load with a known approximate size — reserve once, avoid N incremental
grows. `trimToSize` pays off after a list has shrunk permanently. Neither
matters for `LinkedList`, which has no array and no capacity concept — the
sibling this pair loses to when the backing structure is not an array.

**How it works.** `ensureCapacity(int minCapacity)` compares `minCapacity`
against `elementData.length` and, if larger, grows to exactly `minCapacity`
rather than the usual 1.5× preferred growth (file 06 has the arithmetic).
`trimToSize` replaces `elementData` with `Arrays.copyOf(elementData, size)`,
or the shared `EMPTY_ELEMENTDATA` sentinel when `size == 0`. Both bump
`modCount`, since both structurally touch the backing array.

**Demonstration.**

```java
List<Restriction> restrictions = new ArrayList<>();
restrictions.ensureCapacity(38_000); // a day's worth of applied restrictions, pre-sized once
// ... load 38,000 Restriction rows without a single intermediate grow() call ...
List<Restriction> lifted = restrictions.stream()
        .filter(r -> r.state() == RestrictionState.LIFTED)
        .toList();
restrictions.removeIf(r -> r.state() == RestrictionState.LIFTED);
restrictions.trimToSize(); // release the slack now that most rows are gone
```

**The gotcha.** `ensureCapacity` is not sticky in the way people expect: a
single `add` beyond the reserved capacity grows the array again using the
*normal* 1.5× rule, not another exact reservation. It buys you one grow-free
run up to the requested size, not a permanent ceiling.

> `trimToSize` and `ensureCapacity` are the only two ArrayList members with no
> declaration anywhere above `ArrayList` — the entire visible surface of "this
> List is backed by an array."

### The overridden-from-AbstractList/AbstractCollection set

**Mental model.** `AbstractList` and `AbstractCollection` are written to work
for *any* random-access-ish or any collection-ish structure, so their default
implementations go through `get`, `set`, and `iterator()`. ArrayList overrides
most of that surface to go through `elementData` directly — same contract,
cheaper mechanism.

**Why it exists.** Without these overrides, ArrayList would technically
satisfy `List` by inheriting `AbstractList`'s generic implementations, but
every operation would pay for an iterator or repeated `get` calls it does not
need, since the data is already a contiguous array.

**When it applies, and when it does not.** This is universal for ArrayList —
there is no configuration where the generic, iterator-based version wins
instead. The sibling this pair loses to is `LinkedList`, whose own overrides
of the same abstract members go through node-hopping, which is why `get(int)`
is O(1) on one and O(n) on the other despite an identical `List` contract.

**How it works.** ArrayList's `indexOf(Object)` is a flat `for` loop over
`elementData[0..size)` calling `equals` (or a null check) directly — no
iterator object allocated. `addAll(int, Collection)` is the sharper example:
rather than inserting each element one at a time (the naive generic approach,
O(n) shifts per insertion, O(n·m) total), ArrayList computes the whole
insertion window once and performs a single `System.arraycopy` to open a gap
of size `m`, then copies the new elements in — O(n + m) total.

**Demonstration.**

```java
Movement movement = new Movement(
        movementId, idempotencyKey,
        List.of(stakeReserved, stakeWon), MovementReason.STAKE_SETTLED, postedAt);
List<LedgerEntry> ledger = new ArrayList<>(List.of(movement.entries().get(0)));
ledger.addAll(1, List.of(movement.entries().get(1))); // one arraycopy, not one insert per entry
int idx = ledger.indexOf(movement.entries().get(1));  // straight array scan, no Iterator object
```

**The gotcha.** `contains`, `indexOf`, and `remove(Object)` are all O(n) —
overriding the generic version made them *faster per element*, not
*asymptotically* faster. A hot lookup path over a large ArrayList is still a
linear scan; reach for a `Map` or `Set` if that scan runs often.

> Every override in this bucket keeps the exact contract `AbstractList` or
> `AbstractCollection` specifies and replaces only the mechanism — iterator or
> repeated indexed access, swapped for direct `elementData` reads, writes, and
> `arraycopy`.

### The inherited-and-not-overridden set

**Mental model.** Not every member of `AbstractCollection` or a `List` default
earns a specialised ArrayList version. Some are left exactly as written
upstream, either because the generic version is already close to optimal, or
because specialising them was never worth the code.

**Why it exists.** `containsAll` illustrates the honest reason: writing an
array-backed specialisation of "does this collection contain every element of
that one" gains nothing over the generic `for (Object o : c) if (!contains(o))
return false` — both are O(n·m) unless the caller changes the *shape* of the
argument.

**When it applies, and when it does not.** `containsAll` against a `List`
argument is O(n·m); against a `HashSet` argument each `contains` becomes O(1),
so the whole operation drops to O(n). ArrayList did nothing here — the caller
controls the cost by choosing the argument's type, and that is the actual
escape hatch, not a hidden optimisation inside ArrayList.

**How it works.** `stream()`/`parallelStream()` are the more subtle case: both
are `Collection` defaults that build a `Stream` from whatever `spliterator()`
returns. ArrayList never touches `stream()` itself, but it *does* override
`spliterator()` to return an `ArrayListSpliterator` that splits a contiguous
array cheaply and is `RandomAccess`-aware. The inherited default gets the fast
spliterator underneath it for free — the optimisation lives one layer down
from where people look for it.

**Demonstration.**

```java
List<Restriction> restrictions = loadTodaysRestrictions(); // ~38,000 rows
Set<RestrictionKey> alreadyApplied = new HashSet<>(existingKeys);
boolean allKnown = restrictions.stream()
        .map(Restriction::key)
        .collect(Collectors.toSet())
        .containsAll(alreadyApplied);              // HashSet target: O(n), not O(n*m)
long parallelCount = restrictions.parallelStream()  // rides ArrayList's overridden spliterator
        .filter(r -> r.state() == RestrictionState.APPLIED)
        .count();
```

**The gotcha.** It is easy to assume `stream()` must be overridden because
ArrayList "obviously" streams efficiently — it is not overridden; only
`spliterator()` is, and the efficiency comes entirely from that one layer.

> Members ArrayList leaves untouched are not an oversight — they are the
> honest boundary of where an array-backed specialisation would have changed
> nothing, or where the real optimisation is one method away (`spliterator`)
> rather than in the inherited member itself.

### The default methods that arrive from interfaces

**Mental model.** Two waves of interface defaults land on ArrayList: the
Java 8 wave (`forEach`, `spliterator`, `removeIf`, `replaceAll`, `sort`) and
the Java 21 wave (`getFirst`, `getLast`, `addFirst`, `addLast`, `removeFirst`,
`removeLast`, plus the un-overridden `reversed()`), the second arriving
through `List extends SequencedCollection`. ArrayList overrides every member
of both waves except `reversed()`.

**Why it exists.** Interface defaults let `List` grow new capability —
bulk removal by predicate in 8, first/last access in 21 — without breaking
every existing implementation. The default gives every `List` a working, if
generic, implementation on day one; overriding is optional, not required.

**When it applies, and when it does not.** Overriding pays off exactly where
the array-backed mechanism beats the generic default: `removeIf`'s
bitset-and-compact beats a per-match `remove` call; `addLast` as literally
`add(E)` is amortised O(1); but `addFirst` as literally `add(0, E)` is a full
O(n) shift no override can avoid, because inserting at the front of a
contiguous array always means moving everything after it. Where the front is
the hot end, that is the signal to reach for `LinkedList` or a `Deque`
implementation instead — the alternative this concept loses to.

**How it works.** `getFirst()`/`getLast()` are `get(0)`/`get(size-1)` with a
`NoSuchElementException` on empty instead of an `IndexOutOfBoundsException` —
a deliberate contract difference from raw `get`. `addFirst(E)` is exactly
`add(0, e)`; `addLast(E)` is exactly `add(e)`; `removeFirst()` is `remove(0)`;
`removeLast()` is `remove(size - 1)`. `reversed()` is the one member of this
wave ArrayList does **not** override — it uses `List`'s default, returning a
`ReverseOrderListView`, a live view rather than a reversed copy.

**Demonstration.**

```java
List<LedgerEntry> movementEntries = new ArrayList<>(movement.entries());
LedgerEntry earliest = movementEntries.getFirst();       // O(1), throws if empty
LedgerEntry latest = movementEntries.getLast();          // O(1)
movementEntries.addLast(newSettlementEntry);             // amortised O(1) — same as add(e)
movementEntries.addFirst(correctionEntry);               // O(n) — full shift, same as add(0, e)
List<LedgerEntry> newestFirst = movementEntries.reversed(); // a VIEW, not a copy
```

**The gotcha.** `addFirst`/`addLast` read as a symmetric pair from their
names alone. Their costs are not symmetric — one is a full shift, the other is
the same amortised-O(1) cost as a normal `add`. Treating them as
interchangeable in a hot loop is a real performance bug, not a style nit.

> Interface defaults give `List` a working baseline for every method in both
> waves; ArrayList overrides every one of them except `reversed()`, and the
> only wave-21 pair with genuinely different costs is `addFirst`/`addLast`.

## Pitfalls

### Assuming `remove(1)` and `remove(Integer.valueOf(1))` do the same thing on a `List<Integer>`

**Wrong**

```java
List<Integer> restrictionCounts = new ArrayList<>(List.of(10, 20, 30));
restrictionCounts.remove(1); // looks like "remove the value 1"
System.out.println(restrictionCounts); // [10, 30] — index 1 was dropped, not the value 1
```

**Right**

```java
restrictionCounts.remove(Integer.valueOf(1)); // explicit boxing forces the Object overload
// or, without a cast: restrictionCounts.removeIf(v -> v == 1);
```

**Why people believe it:** autoboxing quietly makes `int` and `Integer`
interchangeable everywhere else in Java, so it is natural to assume `remove`
picks whichever overload "matches the value" rather than resolving strictly by
the static argument type — `int` binds to `remove(int)`, only a boxed
`Integer` binds to `remove(Object)`.

### Assuming `containsAll` is cheap because the collection is small

**Wrong**

```java
List<RestrictionKey> applied = loadAppliedKeys(); // 38,000 rows
List<RestrictionKey> toCheck = loadPendingKeys();  // a List, not a Set
boolean allPresent = applied.containsAll(toCheck);  // O(n * m): 38,000 * m linear scans
```

**Right**

```java
Set<RestrictionKey> appliedSet = new HashSet<>(applied);
boolean allPresent = appliedSet.containsAll(toCheck); // each contains() is O(1) on the target set
```

**Why people believe it:** `containsAll` is inherited unmodified from
`AbstractCollection`, so nothing about ArrayList's specialisations gives any
hint that this particular member is still doing an O(n) `contains` scan per
element of the argument.

### Assuming `stream()` is ArrayList's own optimisation

**Wrong belief:** "ArrayList must override `stream()` for it to be fast."

**Right:** `stream()` is an unmodified `Collection` default. The speed comes
entirely from ArrayList's override of `spliterator()`, which the default
`stream()` builds on. Check `spliterator()`, not `stream()`, when reasoning
about stream performance on a specific `Collection` implementation.

**Why people believe it:** the performance really does come from ArrayList,
just one indirection layer away from the method name people look at first.

### Assuming `clone()` is a deep copy

**Wrong**

```java
List<Money> balances = new ArrayList<>(List.of(cashAvailable, cashReserved));
@SuppressWarnings("unchecked")
List<Money> copy = (List<Money>) ((ArrayList<Money>) balances).clone();
// copy is a different ArrayList, but copy.get(0) == balances.get(0) — same Money reference
```

**Right:** treat `clone()` as "a new array with the same element references."
For genuinely independent elements, build a new list mapping each element
through its own copy constructor or a defensive-copy factory.

**Why people believe it:** `Money`, `LedgerEntry`, and similar record types in
this domain are immutable, so a shallow copy behaves identically to a deep one
for them — the distinction only surfaces with mutable element types, and by
then the habit is already formed.

## Cheat sheet

| Group | Members | Lineage | Complexity headline |
|---|---|---|---|
| A | `trimToSize`, `ensureCapacity` | ArrayList only | O(n) copy |
| B | `iterator`, `listIterator`, `subList`, `indexOf`, `lastIndexOf`, `clear`, `addAll(int,·)`, `removeRange`, `equals`, `hashCode`, `add`, `set`, `remove(int)`, `get` | overrides AbstractList | O(1) or O(n), array-direct |
| C | `isEmpty`, `contains`, `toArray()/(T[])`, `remove(Object)`, `addAll`, `removeAll`, `retainAll`, `size` | overrides AbstractCollection | O(1) or O(n), array-direct |
| D | `forEach`, `spliterator`, `removeIf`, `replaceAll`, `sort` | overrides an interface default (Java 8) | O(n) or O(n log n) |
| E | `getFirst/Last`, `addFirst/Last`, `removeFirst/Last` | overrides SequencedCollection via List (Java 21) | O(1) except `addFirst`/`removeFirst` = O(n) |
| F | `clone` | overrides Object | O(n), shallow |
| G | `containsAll`, `toString`, `reversed`, `stream`, `parallelStream`, `toArray(IntFunction)` | inherited, not overridden | O(n·m) for `containsAll`; O(1) to obtain the rest |

| Trap | One-line fix |
|---|---|
| `remove(int)` vs `remove(Object)` | Box with `Integer.valueOf(...)` for value removal |
| `containsAll` O(n·m) | Convert the target side to a `HashSet` |
| `stream()` "must be overridden" | It isn't — `spliterator()` is |
| `clone()` "must be deep" | It's shallow — new array, same references |
| `equals`/`hashCode` "always overridden" | Only since JDK 11; not in JDK 8 |
| `addFirst` vs `addLast` cost | `addFirst` = O(n) shift; `addLast` = amortised O(1) |

## Self-test

**Q1.** Which two ArrayList members have no declaration in any supertype at all, and why only those two?

<details><summary>Answer</summary>

`trimToSize()` and `ensureCapacity(int)`. Nothing above ArrayList in the type
graph — not `AbstractList`, not `AbstractCollection`, not `List` — has a
concept of a backing array or reserved capacity, since that is purely an
implementation detail of being array-backed rather than part of the `List`
contract.

</details>

**Q2.** `List<Integer> l = new ArrayList<>(List.of(10, 20, 30)); l.remove(1);` — what does `l` contain afterward, and why?

<details><summary>Answer</summary>

`[10, 30]`. The literal `1` is an `int`, which binds to the `remove(int index)`
overload declared in `AbstractList`, not `remove(Object o)` declared in
`AbstractCollection`. It removes the element at index 1, which happens to be
`20` — but it is removing by position, not by value.

</details>

**Q3.** Is `containsAll` faster on ArrayList than the generic `AbstractCollection` version?

<details><summary>Answer</summary>

No — ArrayList inherits `containsAll` unmodified from `AbstractCollection`.
It is still O(n·m): one `contains` call per element of the argument, each of
which is itself O(n) on an ArrayList target. The only way to make it fast is
to change the *target*'s type to something with O(1) `contains`, such as a
`HashSet`.

</details>

**Q4.** Does ArrayList override `stream()`? If the answer is no, where does its performance actually come from?

<details><summary>Answer</summary>

No, `stream()` is an unmodified `Collection` default. ArrayList overrides
`spliterator()` instead, returning an `ArrayListSpliterator` that splits a
contiguous array cheaply and is `RandomAccess`-aware. The default `stream()`
builds its `Stream` from that overridden spliterator, so the speed is real but
lives one layer below the method most people inspect.

</details>

**Q5.** `clone()` on an `ArrayList<Money>` — deep or shallow copy, and what happens to `modCount`?

<details><summary>Answer</summary>

Shallow: a new backing array is allocated, but each slot holds the same
element references as the original. `modCount` on the clone is reset to `0`,
independent of whatever value the source list's `modCount` had reached.

</details>

**Q6.** Name the six Java 21 members ArrayList overrides through `SequencedCollection`, and the one default it does *not* override.

<details><summary>Answer</summary>

Overridden: `getFirst`, `getLast`, `addFirst`, `addLast`, `removeFirst`,
`removeLast` — all `@since 21` in the real source. Not overridden: `reversed()`,
which stays the `List` default returning a `ReverseOrderListView` — a live
view over the original list, not a copy.

</details>

**Q7.** Why is `addFirst` O(n) while `addLast` is amortised O(1), given that both are new Java 21 members on the same class?

<details><summary>Answer</summary>

`addFirst(E)` is literally `add(0, e)`: inserting at the front of a contiguous
array requires shifting every existing element one slot to the right, an O(n)
`arraycopy`. `addLast(E)` is literally `add(e)`: appending at the end never
shifts anything, and only occasionally triggers a `grow()`, giving the usual
amortised O(1) of a normal `add`.

</details>

**Q8.** Were `equals` and `hashCode` always overridden in ArrayList? What is the verified version bracket?

<details><summary>Answer</summary>

No. In JDK 8 both are inherited unmodified from `AbstractList`. They are
overridden starting in JDK 11 (with an `equalsArrayList` fast path when both
sides are exactly `ArrayList`) and remain overridden through JDK 21. Treat
"ArrayList overrides equals/hashCode" as true for 11+ and false for 8.

</details>

---

**Questions answered:** Q-07, Q-08
**Sets up:** Next: every way to construct one, and why an initial capacity of zero behaves differently from no argument at all.
**Diagrams included:** none
**Target version:** Java 21
**Lines:** 549
