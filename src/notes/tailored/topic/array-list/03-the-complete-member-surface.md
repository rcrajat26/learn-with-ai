# `ArrayList` — 03 The complete member surface

**Target version: Java 21 LTS.** | [Map](00-map.md)
Assumes: the hierarchy spine and the meaning of RandomAccess (file 02).
Previous: [02 Position in the collections map](02-position-in-the-collections-map.md) · Next: [04 Constructors and factories](04-constructors-and-factories.md)

`ArrayList` looks like one class with one API. It is really the bottom rung of a
seven-rung ladder — `Iterable`, `Collection`, `SequencedCollection`, `List`,
`AbstractCollection`, `AbstractList`, `ArrayList` — and every method the reader
calls on a `List<E>` variable resolves to whichever rung last supplied a body.
Knowing which rung supplied *this* body is not trivia: it tells the reader the
cost before they read a single line of source, and it tells them which calls
are optional operations a different `List` might refuse — Q-08, Q-09, Q-10.

![Roughly fifty callable members; `ArrayList` freshly declares only `trimToSize` and `ensureCapacity`. Everything else is an override or an inherited default.](diagrams/D-03-who-declares-what.svg)

## The complete member table

`Declared in` names the type whose bytecode actually runs for that call on a
plain `new ArrayList<>()`. A member `ArrayList` overrides is attributed to
`ArrayList`, with the overridden declaration named in `Notes`; a member no type
below the interface layer overrides is attributed to the interface or abstract
class that supplies it, tagged `(default)` where that supply is a Java 8+
default method rather than a required override. Groups appear in override
order: `ArrayList` first (the rung the reader actually calls into most often),
then the two abstract classes, then the three interfaces, then the three
zero-member markers.

### `ArrayList` (41 members + 3 constructors — every fresh declaration or override)

| Member | Declared in | Since | Returns | Complexity | Notes |
|---|---|---|---|---|---|
| `ArrayList()` | ArrayList | 1.2 | `ArrayList<E>` | O(1) — no array allocated yet | Constructors are file 04's subject; this row only places them in the lineage. |
| `ArrayList(int)` | ArrayList | 1.2 | `ArrayList<E>` | O(n) — allocates an `n`-slot backing array | — |
| `ArrayList(Collection<? extends E>)` | ArrayList | 1.2 | `ArrayList<E>` | O(n) — copies the argument via its `toArray()` | — |
| `add(E)` | ArrayList | 1.2 | `boolean` | O(1) amortised — one array write, occasional `grow()` copy | Overrides `AbstractList.add(E)`, which is itself `add(size(), e); return true;` — index-agnostic and slower. |
| `add(int, E)` | ArrayList | 1.2 | `void` | O(n) — one `System.arraycopy` shifts the tail | Overrides `AbstractList.add(int,E)`; the operation `addFirst` secretly calls. |
| `addAll(Collection<? extends E>)` | ArrayList | 1.2 | `boolean` | O(n+m) — one exactly-sized `grow`, one `arraycopy` of the argument's array | Overrides `AbstractCollection.addAll`, which adds one element at a time through an iterator. |
| `addAll(int, Collection<? extends E>)` | ArrayList | 1.2 | `boolean` | O(n+m) — same, plus a tail shift for the insertion point | Overrides `AbstractList.addAll(int,Collection)`. |
| `addFirst(E)` | ArrayList | 21 | `void` | O(n) — literally `add(0, element)`, full tail shift | Overrides `SequencedCollection.addFirst`'s default. The name promises `Deque`-style O(1); it is not. |
| `addLast(E)` | ArrayList | 21 | `void` | O(1) amortised — literally `add(element)` | Overrides `SequencedCollection.addLast`'s default. |
| `clear()` | ArrayList | 1.2 | `void` | O(n) — nulls every slot | Overrides `AbstractList.clear()` (which calls `removeRange`). Does **not** touch `elementData`; capacity survives `clear()`. |
| `clone()` | ArrayList | 1.2 | `Object` | O(n) — `Arrays.copyOf(elementData, size)` | Overrides `Object.clone()`. Shallow; resets `modCount` to 0. |
| `contains(Object)` | ArrayList | 1.2 | `boolean` | O(n) — `indexOf(o) >= 0`, one `equals` per slot until match | Overrides `AbstractCollection.contains`, which does the same scan through an `Iterator` instead of an array index. |
| `ensureCapacity(int)` | ArrayList | 1.2 | `void` | O(n) worst case — may trigger one array copy | Fresh declaration — no ancestor to override. |
| `equals(Object)` | ArrayList | 1.2 | `boolean` | O(n) — element-by-element `Objects.equals`, with a `getClass()`-matched fast path between two `ArrayList`s | Overrides `AbstractList.equals`, which always drives an iterator, never indexes an array. |
| `forEach(Consumer<? super E>)` | ArrayList | 8 | `void` | O(n) — one `action.accept` per element; `modCount` checked once at the end | Overrides `Iterable.forEach`'s default. |
| `get(int)` | ArrayList | 1.2 | `E` | O(1) — one `Objects.checkIndex` bounds check + one array read | Overrides `AbstractList.get(int)`, which is `abstract` — there is no generic body to beat. |
| `getFirst()` | ArrayList | 21 | `E` | O(1) — bounds check + `elementData(0)` | Overrides `SequencedCollection.getFirst`'s default; throws `NoSuchElementException` on empty. |
| `getLast()` | ArrayList | 21 | `E` | O(1) — bounds check + `elementData(size-1)` | Overrides `SequencedCollection.getLast`'s default. |
| `hashCode()` | ArrayList | 1.2 | `int` | O(n) — `31 * hash + e.hashCode()` over every element | Overrides `AbstractList.hashCode`, same formula, driven through an iterator instead of an index loop. |
| `indexOf(Object)` | ArrayList | 1.2 | `int` | O(n) — linear scan, one `equals` (or `== null`) per slot | Overrides `AbstractList.indexOf`, iterator-driven. |
| `isEmpty()` | ArrayList | 1.2 | `boolean` | O(1) — `size == 0` | Overrides `AbstractCollection.isEmpty`, same test, expressed against `size()` instead of the field. |
| `iterator()` | ArrayList | 1.2 | `Iterator<E>` | O(1) — allocates an `Itr` | Overrides `AbstractList.iterator()`; `AbstractList`'s own is a generic index-cursor `Itr` that calls `get(int)` per step instead of touching the array directly. |
| `lastIndexOf(Object)` | ArrayList | 1.2 | `int` | O(n) — linear scan from the end | Overrides `AbstractList.lastIndexOf`. |
| `listIterator()` | ArrayList | 1.2 | `ListIterator<E>` | O(1) | Overrides `AbstractList.listIterator()`. |
| `listIterator(int)` | ArrayList | 1.2 | `ListIterator<E>` | O(1) | Overrides `AbstractList.listIterator(int)`. |
| `remove(int)` | ArrayList | 1.2 | `E` | O(n) — `fastRemove` shifts the tail via `System.arraycopy` | Overrides `AbstractList.remove(int)`. |
| `remove(Object)` | ArrayList | 1.2 | `boolean` | O(n) — linear scan to find, then `fastRemove`'s O(n) shift | Overrides `AbstractCollection.remove(Object)`, iterator-driven equivalent. |
| `removeAll(Collection<?>)` | ArrayList | 1.2 | `boolean` | O(n·m) worst case, O(n) if the argument is a hash-backed `Set` | Overrides `AbstractCollection.removeAll` — same asymptotic shape, `ArrayList`'s `batchRemove` just does the compaction with one `arraycopy` instead of per-element `Iterator.remove()`. |
| `removeFirst()` | ArrayList | 21 | `E` | O(n) — `fastRemove(es, 0)`, full tail shift | Overrides `SequencedCollection.removeFirst`'s default. |
| `removeIf(Predicate<? super E>)` | ArrayList | 8 | `boolean` | O(n) — a mark pass calling the predicate on every element, then a compaction pass | Overrides `Collection.removeIf`'s default, which removes through the iterator one call at a time. |
| `removeLast()` | ArrayList | 21 | `E` | O(1) — `fastRemove(es, size-1)`, no shift needed | Overrides `SequencedCollection.removeLast`'s default. The one `SequencedCollection` accessor that is genuinely cheap. |
| `removeRange(int, int)` *(protected)* | ArrayList | 1.2 | `void` | O(n) — `shiftTailOverGap` slides the surviving tail down | Overrides `AbstractList.removeRange`, which is concrete but loop-based — it walks a `ListIterator` calling `remove()` per element, so `AbstractList`'s version is O(n·k) where `ArrayList`'s single `arraycopy` is O(n). |
| `replaceAll(UnaryOperator<E>)` | ArrayList | 8 | `void` | O(n) — one `operator.apply` per element in place | Overrides `List.replaceAll`'s default. |
| `retainAll(Collection<?>)` | ArrayList | 1.2 | `boolean` | O(n·m) worst case, O(n) if the argument is a hash-backed `Set` | Overrides `AbstractCollection.retainAll`; same `batchRemove` engine as `removeAll`. |
| `set(int, E)` | ArrayList | 1.2 | `E` | O(1) — bounds check + one array write | Overrides `AbstractList.set(int,E)`. |
| `size()` | ArrayList | 1.2 | `int` | O(1) — returns the field | Overrides `AbstractCollection.size()`, which is `abstract`. |
| `sort(Comparator<? super E>)` | ArrayList | 8 | `void` | O(n log n) — TimSort sorts the backing array directly, no copy | Overrides `List.sort`'s default, which would sort a boxed snapshot and write it back through `set`. |
| `spliterator()` | ArrayList | 8 | `Spliterator<E>` | O(1) — wraps the array, `ORDERED\|SIZED\|SUBSIZED` | Overrides both `Collection.spliterator`'s and `Iterable.spliterator`'s defaults, which build a generic iterator-backed spliterator with none of those characteristics. |
| `subList(int, int)` | ArrayList | 1.2 | `List<E>` | O(1) — allocates a `SubList` view, no copy | Overrides `AbstractList.subList`, which returns a generic `AbstractList`-backed sublist instead of a `RandomAccess` one. |
| `toArray()` | ArrayList | 1.2 | `Object[]` | O(n) — `Arrays.copyOf(elementData, size)` | Overrides `AbstractCollection.toArray()`, which builds the array through an iterator. |
| `toArray(T[])` | ArrayList | 1.2 | `T[]` | O(n) — `arraycopy` or `Arrays.copyOf` depending on `a.length` | Overrides `AbstractCollection.toArray(T[])`, iterator-driven equivalent. |
| `trimToSize()` | ArrayList | 1.2 | `void` | O(n) — reallocates to exactly `size` | Fresh declaration — no ancestor to override. |

### `java.util.AbstractList` (2 live members reach an `ArrayList` call)

| Member | Declared in | Since | Returns | Complexity | Notes |
|---|---|---|---|---|---|
| `modCount` *(protected field)* | AbstractList | 1.2 | `int` | O(1) to read or bump | The single piece of state that makes fail-fast iteration possible; every structural mutator above increments it. |
| `AbstractList()` *(protected constructor)* | AbstractList | 1.2 | `AbstractList<E>` | O(1) | Every `ArrayList` constructor chains through this `super()` call before touching `elementData`. |

`AbstractList` contributes generic, index-based implementations of nearly
everything on top of an abstract `get(int)`/`size()` pair — `add`, `set`,
`remove(int)`, `indexOf`, `lastIndexOf`, `clear`, `addAll(int, …)`, the
iterators, `subList`, `equals`, `hashCode`, `removeRange`. `ArrayList`
overrides every one of them for array-specific speed, so nothing here survives
into a live `ArrayList` call except `modCount` itself and the inherited
constructor. A hand-rolled `List` that only implements `get(int)` and `size()`
gets a fully working, if slower, list for free — that is the entire point of
`AbstractList` existing.

### `java.util.AbstractCollection` (3 live members reach an `ArrayList` call)

| Member | Declared in | Since | Returns | Complexity | Notes |
|---|---|---|---|---|---|
| `AbstractCollection()` *(protected constructor)* | AbstractCollection | 1.2 | `AbstractCollection<E>` | O(1) | Chained through by `AbstractList()`. |
| `containsAll(Collection<?>)` | AbstractCollection *(concrete, unoverridden)* | 1.2 | `boolean` | O(n·m) — `for (Object e : c) if (!contains(e)) return false;`, and `ArrayList` does **not** override it | See the `containsAll` primary concept below — this is the row that matters most in this table. |
| `toString()` | AbstractCollection *(concrete, unoverridden)* | 1.2 | `String` | O(n) — builds `"[a, b, c]"` by driving an iterator once | Returns `"[]"` for an empty list. |

`AbstractCollection` contributes generic implementations of nearly every
`Collection` method — `isEmpty`, `contains`, both `toArray` overloads, `add`,
`remove(Object)`, `addAll`, `removeAll`, `retainAll`, `clear` — on top of an
abstract `iterator()`/`size()` pair. `ArrayList` overrides every one of those
for speed. `containsAll` and `toString` are the **only two members a live
`ArrayList` call actually reaches here**; everything else in this abstract
class is dead code from `ArrayList`'s point of view, present only for other
`Collection` implementors that don't override it.

### `java.util.List` (2 live members + 13 static factories)

| Member | Declared in | Since | Returns | Complexity | Notes |
|---|---|---|---|---|---|
| `reversed()` | List *(default)* | 21 | `List<E>` | O(1) to obtain the view; O(1) per subsequent element access, but every write goes through to this list | The one `SequencedCollection`-family member `ArrayList` does **not** override. Runtime class `java.util.ReverseOrderListView$Rand` (measured). |
| `of()` … `of(E, …, E)` *(11 overloads, arity 0–10)* | List *(static factory)* | 9 | `List<E>` | O(k) — copies `k` arguments into an immutable backing array | Rejects `null` elements with `NullPointerException`. |
| `of(E...)` | List *(static factory)* | 9 | `List<E>` | O(k) | Same rejection rule; used past 10 elements. |
| `copyOf(Collection<? extends E>)` | List *(static factory)* | 9 | `List<E>` | O(n) — copies the argument once into an immutable list | Runtime class `ImmutableCollections$List12` or `$ListN` depending on size (measured). |

`List` contributes the positional contract — `get(int)`, `set(int,E)`,
`add(int,E)`, `remove(int)`, `indexOf`, `lastIndexOf`, `listIterator`,
`subList` — and the specified `equals`/`hashCode` algorithms. Every one of
those is already an `ArrayList` row above, because `ArrayList` (via
`AbstractList`) overrides all of them; `List`'s own declarations of them are
`abstract` and contribute no runnable body. What `List` contributes that
*does* survive unshadowed is `reversed()`'s default and the thirteen static
factories, which are not `ArrayList` members at all — they are ways to get a
`List` that is not an `ArrayList`, the subject of file 04.

### `java.util.SequencedCollection` (0 live members reach an `ArrayList` call)

`SequencedCollection` (JEP 431, new in Java 21) declares `reversed()` as
`abstract` and gives default bodies to `addFirst`, `addLast`, `getFirst`,
`getLast`, `removeFirst`, `removeLast`. Every one of those seven signatures
already appears in the table above — the six accessors as `ArrayList`
overrides (with direct index arithmetic), and `reversed()` as `List`'s
concrete default. `SequencedCollection`'s contribution is real — it is what
gives `ArrayList`, `Deque` and `LinkedHashSet` a shared first/last vocabulary
that previously existed only on `Deque` and `SortedSet` — but it supplies no
row of its own here because nothing calls its raw defaults on an `ArrayList`.

### `java.util.Collection` (3 live members reach an `ArrayList` call)

| Member | Declared in | Since | Returns | Complexity | Notes |
|---|---|---|---|---|---|
| `stream()` | Collection *(default)* | 8 | `Stream<E>` | O(1) to obtain; `StreamSupport.stream(spliterator(), false)` | Not overridden by `ArrayList` — which is exactly why `ArrayList`'s `ORDERED\|SIZED\|SUBSIZED` spliterator characteristics matter to every stream built over it. |
| `parallelStream()` | Collection *(default)* | 8 | `Stream<E>` | O(1) to obtain; same spliterator, `parallel = true` | Not overridden. |
| `toArray(IntFunction<T[]>)` | Collection *(default)* | 11 | `T[]` | O(n) — `generator.apply(size())` then one `arraycopy` | Not overridden. |

`Collection` re-declares `containsAll` (already attributed to
`AbstractCollection`'s concrete body above) and contributes `removeIf`,
`spliterator()`, `stream()`, `parallelStream()`, and `toArray(IntFunction)` as
defaults. `ArrayList` overrides `removeIf` and `spliterator()` for speed;
`stream()`, `parallelStream()` and `toArray(IntFunction)` are the three
defaults it leaves alone, so those three bodies are the ones that actually run.

### `java.lang.Iterable` (0 live members reach an `ArrayList` call)

`Iterable` declares `iterator()` as `abstract` and gives default bodies to
`forEach(Consumer)` and `spliterator()`. `ArrayList` overrides all three
(`iterator()` via `AbstractList`, `forEach` and `spliterator()` directly), so
none of `Iterable`'s own bodies run on an `ArrayList`. Its contribution is
still foundational: `for (X x : list)` desugars to an `Iterator`-driven
`while` loop calling exactly the `iterator()` row above, which is why a
for-each loop is fail-fast and an index loop (`for (int i = 0; …)`) is not —
the index loop never calls `iterator()` at all.

### `RandomAccess`, `Cloneable`, `Serializable` — 0 members each

Three pure markers, contributing behaviour with no method to attribute.
`RandomAccess` is a **performance** promise, not a behavioural one — that
`for (int i=0; i<n; i++) list.get(i)` beats the iterator form — and the named
consumers that branch on it are `Collections.binarySearch`,
`Collections.reverse`, `Collections.shuffle`, `Collections.fill`,
`Collections.copy`, `Collections.indexOfSubList`, `Collections.rotate`, and
`Collections.swap`'s callers (file 02 covers the marker itself in full).
`Cloneable` is what stops `Object.clone()`'s `super.clone()` call from
throwing `CloneNotSupportedException` inside `ArrayList.clone()`.
`Serializable` is what lets `writeObject`/`readObject` run at all.

## Primary concepts

### Member lineage: where a call actually terminates

**Mental model.** Picture `ArrayList`'s public surface as a lookup, not a flat
list. Every call the reader writes — `list.get(3)`, `list.stream()`,
`list.reversed()` — walks the seven-rung ladder from `ArrayList` upward until
it finds the first rung that supplies a body, and stops there. Most calls
never leave rung one; a few climb all the way to `Collection` or `Iterable`
before finding a home.

**Why it exists.** The Collections Framework put shared, index-agnostic
implementations in `AbstractList` and `AbstractCollection` so that anyone
writing a new `List` only has to implement `get(int)` and `size()` to get a
fully working (if slow) collection for free. `ArrayList` is that same
framework's fastest tenant: it overrides everything it can do faster with a
raw array, and leaves everything else alone.

**When it applies, and when it does not.** Lineage is what lets the reader
predict cost *without* reading source: an override always buys array-specific
speed over the generic ancestor version; an inherited, unoverridden default is
generic, index-agnostic, and pays for that generality every time it runs. The
alternative to reasoning this way is memorising per-method complexity as
isolated facts, which does not transfer to the next unfamiliar `List`
implementation the reader meets in an interview.

**How it works, at this file's depth.** The table above is the resolution of
every member in `javap -protected` output for all eight types on JDK 21.0.7:
a signature present in `ArrayList`'s own listing is an `ArrayList` row; a
signature present in an ancestor's listing and not shadowed anywhere below it
is that ancestor's row. Sixty-three distinct members resolve this way, and
forty-one of them terminate at `ArrayList` itself — of those forty-one, only
`trimToSize()` and `ensureCapacity(int)` have no ancestor to override at all.

**The diagram** for this concept is the one already embedded at the top of
this file; there is no second diagram, re-read it with the table in mind.

**A minimal concrete demonstration**, using the measured runtime classes from
this topic's growth-and-timing packet:

```java
String[] instrumentIds = {"AA-610", "AA-620"};
List<String> plain = new ArrayList<>(List.of(instrumentIds));
List<String> flipped = plain.reversed();

System.out.println(plain.getClass());
System.out.println(flipped.getClass());
// java.util.ArrayList
// java.util.ReverseOrderListView$Rand
```

`plain.getClass()` is `ArrayList` because every method that produced it
resolved to an `ArrayList` row. `flipped.getClass()` is not `ArrayList` at
all — `reversed()` resolved to `List`'s default, which returns a *different*
runtime type. A reader who assumes every `List<E>`-typed value obtained from
an `ArrayList` is itself an `ArrayList` will be wrong the moment `reversed()`
enters the chain.

**The gotcha.** `addFirst(E)` and `getFirst()` look, from the method name
alone, like the same family as `ArrayDeque`'s O(1) ends. They are not — both
resolve to `ArrayList` rows, but `addFirst` is literally `add(0, element)`
(O(n), full tail shift) while `removeLast()` is genuinely O(1). The
`SequencedCollection` retrofit gave `ArrayList` the *vocabulary* of a deque,
not new performance; the lineage table is what exposes that the six accessors
did not all get the same treatment.

> **Definition.** A member's declaring type is whichever class or interface in
> the seven-rung ladder — `ArrayList`, `AbstractList`, `AbstractCollection`,
> `List`, `SequencedCollection`, `Collection`, `Iterable` — supplies the body
> that actually executes for that call on a plain `ArrayList` instance; an
> override always displaces its ancestor's declaration in that resolution.

### The `AbstractCollection` trap: `containsAll` and `toString`

**Mental model.** `containsAll` is what a `Collection` implementation gets for
free when it has told the framework nothing more than "I can answer
`contains(x)`": ask the same question once per element of the argument, and
fail on the first `no`. It is the naive nested-loop membership check, wearing
a `List` method's name.

**Why it exists.** `AbstractCollection` cannot assume anything about the
concrete storage below it — it might be backed by an array, a linked chain, or
a hash table — so the only algorithm it can offer that works for *all* of them
is one built entirely out of `contains` and `iterator`. That algorithm is
correct for every `Collection` in existence. It is fast only for the ones
whose own `contains` is fast.

**When it applies, and when it does not.** `containsAll` is fine, unmodified,
against a `HashSet`-backed argument checked from a `HashSet`-backed receiver —
both sides are O(1) per lookup. It is fine against a small `c` on any
receiver. It becomes a genuine performance trap specifically when the
*receiver* is an `ArrayList` (or any `List`, since none of them beat O(n)
`contains`) and `c` is large, because every one of its `m` elements pays the
receiver's full O(n) scan.

**How it works, at this file's depth.** `AbstractCollection.containsAll(c)`
is `for (Object e : c) if (!contains(e)) return false; return true;` and
`ArrayList` does not override it — it is one of only two `AbstractCollection`
members (with `toString`) that a live `ArrayList` call actually reaches.
`contains(e)` on that receiving `ArrayList` is itself O(n) (the row two groups
above), so the whole call is O(n·m).

**The diagram** does not repeat here — it is the `AbstractCollection` group's
`containsAll` row above, the whole reason the table carries a `Notes` column.

**A minimal concrete demonstration**, grounded on `ClientRestrictions`'
`38k/day applied and lifted` restriction-record volume (Appendix A.5):

```java
public record RestrictionKey(RestrictionType type, RestrictionSource source) {}

List<RestrictionKey> activeToday = new ArrayList<>(fetchActiveRestrictions());
List<RestrictionKey> justLifted = fetchLiftedThisBatch();

// O(n·m): for every one of ~38,000 lifted keys, scans activeToday end to end.
boolean anyStillActive = activeToday.containsAll(justLifted);

// O(n): build the lookup set once, then one contains() per lifted key.
Set<RestrictionKey> activeLookup = new HashSet<>(activeToday);
boolean sameAnswer = justLifted.stream().allMatch(activeLookup::contains);
```

The two lines compute the same boolean. The first pays `contains`'s O(n) cost
once per element of `justLifted`; on a batch sized against 38,000 daily
restriction applications and liftings, that quadratic-shaped cost is the
difference between a job that finishes and one that does not.

**The gotcha.** `containsAll` sits on the same `List<E>` type as `get(int)`
and `add(E)`, both O(1)-per-call `ArrayList` overrides. Nothing about reading
the call site — `list.containsAll(other)` — signals that this particular
method skipped `ArrayList`'s override entirely and fell through two rungs to
`AbstractCollection`'s generic body.

> **Definition.** `containsAll` and `toString` are the only two
> `AbstractCollection` members an `ArrayList` call ever actually executes;
> every other `AbstractCollection` method is shadowed by a faster `ArrayList`
> override.

### Optional operations and `UnsupportedOperationException`

**Mental model.** The `Collection`/`List` interfaces describe two kinds of
methods: the ones every implementation must support (`size`, `get`, `iterator`
family), and the *optional operations* — the structural mutators (`add`,
`remove`, `set`, `clear`, and their bulk forms) — that an implementation is
permitted to refuse outright by throwing `UnsupportedOperationException`
instead of doing the work.

**Why it exists.** Without this escape hatch, every immutable or fixed-size
view the JDK wants to hand back as a plain `List<E>` — `List.of(...)`,
`Arrays.asList(arr)`, `Collections.unmodifiableList(list)`,
`stream().toList()` — would need its own separate interface, and every caller
would need to know which interface it was holding before calling a mutator.
The exception *is* the mechanism that lets one interface type serve both fully
mutable and deliberately restricted implementations honestly.

**When it applies, and when it does not.** A plain `new ArrayList<>()`
supports every optional operation in the table above — none of its own rows
throw `UnsupportedOperationException`. The restriction only shows up when a
`List<E>`-typed reference actually points at a different runtime class:
`List.of(...)` and `stream().toList()` are fully immutable (every mutator
throws); `Arrays.asList(arr)` is fixed-size only (`set` works and writes
through to `arr`, but `add`/`remove` throw);
`Collections.unmodifiableList(list)` is an unmodifiable *view* over a list
that can still change underneath it. `list.subList(...)` and `list.reversed()`
are the opposite case worth naming here too — both stay fully mutable and
write-through, so neither throws.

**How it works, at this file's depth.** `AbstractList`'s own default bodies
for `add(int,E)`, `set(int,E)` and `remove(int)` are, absent an override,
exactly `throw new UnsupportedOperationException();` — that is where the
exception is *declared* to come from for any `List` implementor (including
`ArrayList`'s own ancestor) that does not supply a working body. `ArrayList`
overrides all three, so it never throws them itself; the JDK's fixed-size and
immutable list implementations (`Arrays$ArrayList`, `ImmutableCollections$*`,
`Collections$UnmodifiableList`) are the ones that either inherit that default
or throw explicitly from their own overrides.

**The diagram** does not repeat here; the runtime-class facts it draws on are
already established for `List`'s factories and `reversed()` in the table.

**A minimal concrete demonstration**, using `LedgerEntry` from the append-only
ledger (`Appendix C.2` — `LedgerEntry` has no setters, ever, by its own
invariant):

```java
public record LedgerEntry(
        UUID id,
        UUID movementId,
        PositionRef position,
        Direction direction,
        Money amount,
        Instant postedAt) {}

List<LedgerEntry> snapshot = List.of(
        new LedgerEntry(id1, movementId, cashAvailable, Direction.DEBIT, stakeAmount, now),
        new LedgerEntry(id2, movementId, bonusReserved, Direction.CREDIT, stakeAmount, now));

snapshot.add(new LedgerEntry(id3, movementId, cashAvailable, Direction.CREDIT, refund, now));
// java.lang.UnsupportedOperationException

List<LedgerEntry> mutable = new ArrayList<>(snapshot);
mutable.add(new LedgerEntry(id3, movementId, cashAvailable, Direction.CREDIT, refund, now));
// succeeds — a plain ArrayList supports every optional operation
```

`List.of(...)` returning an immutable snapshot is a good match for
`LedgerEntry`'s own append-only invariant; copying it into a fresh
`ArrayList` when the caller genuinely needs to keep accumulating entries
before a single `Movement` post is the fix, not fighting the exception.

**The gotcha.** `Arrays.asList(arr)` is fixed-size, not immutable —
`.set(0, v)` succeeds (and, measured, mutates `arr` itself), but `.add(v)`
throws `UnsupportedOperationException`. Treating every `UnsupportedOperation
Exception` site as "this list is immutable" leads to a wrong diagnosis on a
fixed-size list, where the real fix is a size change, not a mutability change.

> **Definition.** An optional operation is any `Collection`/`List` member the
> interface contract permits an implementation to refuse via
> `UnsupportedOperationException`; `ArrayList` implements every optional
> operation it declares, but a `List<E>`-typed reference obtained from
> elsewhere is not guaranteed to be an `ArrayList`.

---

## Pitfalls

### `addFirst(E)` and `getFirst()` look like `Deque` operations, so people assume `Deque`-level cost

**Wrong**
```java
List<LedgerEntry> queue = new ArrayList<>();
for (int i = 0; i < 100_000; i++) queue.addFirst(makeEntry(i));
// measured on JDK 21.0.7: 100,000 add(0, e) calls take ~314 ms,
// against < 1 ms for 100,000 add(e) calls
```

**Right**
```java
Deque<LedgerEntry> queue = new ArrayDeque<>();
for (int i = 0; i < 100_000; i++) queue.addFirst(makeEntry(i));
// ArrayDeque: amortised O(1) at both ends, circular array, no shift
```

**Why people believe it:** `addFirst`/`getFirst`/`removeFirst`/`addLast`/
`getLast`/`removeLast` arrived on `ArrayList` via the `SequencedCollection`
retrofit (JEP 431, Java 21) with exactly the names `Deque` has used for
decades. The retrofit gave `List` implementations the *vocabulary*; it did not
change what the backing array can do cheaply.

### Calling `list.containsAll(other)` on two `ArrayList`s and assuming it is as fast as any other `List` method

**Wrong**
```java
List<RestrictionKey> active = fetchAllActiveRestrictions(); // ArrayList, tens of thousands
List<RestrictionKey> batch  = fetchTodaysLiftedKeys();       // ArrayList, thousands
if (active.containsAll(batch)) { /* O(n·m): every batch key scans all of active */ }
```

**Right**
```java
Set<RestrictionKey> activeLookup = new HashSet<>(active); // one O(n) copy
if (activeLookup.containsAll(batch)) { /* O(m) now, one O(1) contains per key */ }
```

**Why people believe it:** `containsAll` reads like any other `List` method
and sits right next to `contains`, `indexOf`, and `get` in the same interface.
Nothing about the call site signals that it is the one member that falls all
the way through to `AbstractCollection`'s unoverridden, iterator-and-`contains`
generic implementation.

### Assuming a `List<E>` you did not construct yourself is a mutable `ArrayList`

**Wrong**
```java
List<LedgerEntry> entries = movement.entries(); // returns List.of(...) internally
entries.add(correctionEntry); // UnsupportedOperationException, at 2 a.m., in production
```

**Right**
```java
List<LedgerEntry> mutableCopy = new ArrayList<>(movement.entries());
mutableCopy.add(correctionEntry); // fine — this one really is an ArrayList
```

**Why people believe it:** the reference type is `List<E>` either way, and the
IDE, the method signature, and every call site look identical for an
`ArrayList` and an immutable `List.of(...)` snapshot. Only the runtime class —
which the member table's lineage makes predictable, not the static type —
decides whether the mutator throws.

## Cheat sheet

| Group | Live rows on `ArrayList` | What survives unshadowed |
|---|---|---|
| `ArrayList` | 41 + 3 ctors | Everything — this is what the reader calls into by default. |
| `AbstractList` | 2 | `modCount` field, the protected no-arg constructor. |
| `AbstractCollection` | 3 | `containsAll` (O(n·m) trap), `toString`, the protected constructor. |
| `List` | 14 (`reversed()` + 13 factories) | `reversed()`'s default; the static factories are not `ArrayList` members at all. |
| `SequencedCollection` | 0 | All seven signatures resolve elsewhere (six to `ArrayList`, one to `List`). |
| `Collection` | 3 | `stream()`, `parallelStream()`, `toArray(IntFunction)`. |
| `Iterable` | 0 | All three resolve to `ArrayList` overrides; the for-each desugaring is the visible effect. |
| `RandomAccess` / `Cloneable` / `Serializable` | 0 each | Pure markers — see file 02 for `RandomAccess`'s consumers. |

| Fast fact | Value |
|---|---|
| Freshly declared, no ancestor at all | `trimToSize()`, `ensureCapacity(int)` |
| Named-but-not-cheap | `addFirst(E)` — O(n), not O(1) |
| Genuinely cheap `SequencedCollection` accessor | `removeLast()` — O(1) |
| `SequencedCollection` member `ArrayList` does not override | `reversed()` |
| Only two live `AbstractCollection` members | `containsAll`, `toString` |
| Only three live `Collection` defaults | `stream()`, `parallelStream()`, `toArray(IntFunction)` |
| Where `UnsupportedOperationException` for list mutators is declared | `AbstractList`'s default `add`/`set`/`remove(int)` bodies |

## Self-test

**Q1.** `list.get(3)` and `list.reversed().get(3)` on the same `ArrayList` — do
both calls resolve to the same declaring type?

<details><summary>Answer</summary>

No. `list.get(3)` resolves to the `ArrayList` row for `get(int)` — one bounds
check, one array read, O(1). `list.reversed()` first resolves to `List`'s
default (`ArrayList` does not override `reversed()`), returning a
`ReverseOrderListView$Rand`; `.get(3)` on *that* object runs whatever
`ReverseOrderListView`'s own `get(int)` does, not `ArrayList`'s. They are
different declaring types even though the second expression started from the
same `ArrayList` instance.

</details>

**Q2.** Why does `ArrayList` override `add(E)`, `add(int,E)`, `get(int)`, and
almost every other `AbstractList`/`AbstractCollection` method, but *not*
`stream()`, `parallelStream()`, or `toArray(IntFunction<T[]>)`?

<details><summary>Answer</summary>

The overridden methods all have an array-specific fast path that beats the
generic, iterator-driven ancestor implementation — a direct index write versus
an `Iterator.next()`/`set` cycle, for instance. `stream()` and
`parallelStream()` are `StreamSupport.stream(spliterator(), false/true)`,
and `ArrayList` already supplies a fast, `ORDERED|SIZED|SUBSIZED` spliterator
(itself an override); there is nothing left to speed up by also overriding
`stream()` — it would just call the same fast spliterator through an extra
layer of indirection with no complexity change. `toArray(IntFunction)` is
`generator.apply(size())` then an `arraycopy`, which is already the same
shape `ArrayList`'s own `toArray()` uses; overriding it would not change its
asymptotic cost.

</details>

**Q3.** A batch job runs `activeRestrictions.containsAll(todaysLiftedKeys)`
where both are `ArrayList<RestrictionKey>`, against the `38k/day applied and
lifted` restriction volume from Appendix A.5. Name the declaring type this
call resolves to, and the complexity.

<details><summary>Answer</summary>

`AbstractCollection` — `ArrayList` does not override `containsAll`. The body
is `for (Object e : c) if (!contains(e)) return false;`, and `contains` on the
`ArrayList` receiver is itself O(n), so the whole call is O(n·m): for every
one of the up-to-38,000 lifted keys, a full linear scan of the active
restriction list. Converting the receiver to a `HashSet<RestrictionKey>` first
drops this to O(n+m).

</details>

**Q4.** Which six `ArrayList` methods arrived with `@since 21`, and what did
they change about `ArrayList`'s performance?

<details><summary>Answer</summary>

`getFirst()`, `getLast()`, `addFirst(E)`, `addLast(E)`, `removeFirst()`,
`removeLast()` — the `SequencedCollection` retrofit (JEP 431). None of them
changed `ArrayList`'s performance. `getFirst`/`getLast`/`removeLast` were
always achievable in O(1) with existing methods (`get(0)`, `get(size()-1)`,
`remove(size()-1)`); `addFirst`/`removeFirst` were always O(n) and remain O(n)
— they are literally `add(0, e)` and `fastRemove(es, 0)`. The retrofit added
vocabulary, not new capability.

</details>

**Q5.** `new ArrayList<>().add("x")` never throws
`UnsupportedOperationException`. Name one JDK-supplied `List<String>` that
would throw for the identical call, and say whether it is immutable or merely
fixed-size.

<details><summary>Answer</summary>

`List.of("a", "b")` is fully immutable — `add` throws, and so would `set`.
`Arrays.asList(new String[]{"a","b"})` is the fixed-size alternative — `add`
throws `UnsupportedOperationException`, but `set(0, "x")` succeeds and writes
through to the backing array. The distinguishing test is whether `set` works;
if it does, the list is fixed-size, not immutable.

</details>

**Q6.** Why does `AbstractCollection` bother declaring `containsAll` and
`toString` at all, if `ArrayList` never gets any speed benefit from them being
there?

<details><summary>Answer</summary>

`ArrayList` is not the only `Collection` implementation. `AbstractCollection`
has to supply a correct, working `containsAll` and `toString` for *every*
implementor that does not override them — a custom `Collection` backed by,
say, a linked structure or an external system gets a functioning
`containsAll`/`toString` for free the moment it implements `iterator()`,
`size()`, and `contains()`. `ArrayList` happens not to need the speed benefit
of overriding them (its own `contains` is already the dominant cost either
way), so it leaves them alone — that omission is itself informative, not an
oversight.

</details>

---

**Questions answered:** Q-08, Q-09, Q-10
**Sets up:** Next: how you get one — the three constructors, the copy paths, and the factories that give you something else entirely.
**Diagrams included:** D-03
**Target version:** Java 21 LTS
**Lines:** 600
