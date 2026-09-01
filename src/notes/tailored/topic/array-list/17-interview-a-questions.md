# `ArrayList` — 17 Interview A: questions 1 to 19

**Target version: Java 21 LTS.** | [Map](00-map.md)
Assumes: files 01 through 16 in full — this file only recalls.
Previous: [16 Prove it — build and measure](16-prove-it-build-and-measure.md) · Next: [18 Interview B — questions 20 to 38](18-interview-b-questions.md)

This file introduces nothing new. It is the set replayed as a loop would run
it — the first nineteen questions, in the order difficulty builds, each
answered the way you'd say it in the room, not the way you'd write it in a
note. Where a real interviewer pushes past a thirty-second answer, the
cross-link names the file that owns the depth.

## The set, before the streets

| File | Teaches | One thing to remember |
|---|---|---|
| 01 | The `List` positional contract and ArrayList's four non-guarantees | Order, index, duplicates — nothing about threads, sortedness, or guaranteed CME |
| 02 | The interface spine, abstract-class spine, `RandomAccess`, the sibling family | `RandomAccess` is a zero-member performance promise, not a behavioural one |
| 03 | The complete member surface and which supertype declares each member | `containsAll`/`toString` are the only two `AbstractCollection` bodies that ever run |
| 04 | The three constructors and nine call-site expressions that all look like `List<X>` | Only five of the nine hand you a real, mutable `ArrayList` |
| 05 | `elementData`/`size`/`modCount`, the two empty sentinels, `grow`'s arithmetic | Capacity is `elementData.length` — no field, no accessor, ever |
| 06 | `add`, `add(int,E)`, `remove(int)`, `remove(Object)`, statement by statement | The trailing `null` after `fastRemove` is what lets the object be collected |
| 07 | `removeIf`'s bitset, `batchRemove`'s shared engine, the exception-safety repair | `removeAll(aList)` is O(n·m); `removeAll(aSet)` is O(n) |
| 08 | Iteration, fail-fast, `SubList`, view semantics | `hasNext()` checks `cursor != size`, never `modCount` |
| 09 | The lazy spliterator and Java serialization | Spliterator is `ORDERED\|SIZED\|SUBSIZED` — why it parallelises cheaply |
| 10 | Cost and memory, precisely | Every cost claim carries a named cause, not a bare number |
| 11 | Choosing `ArrayList` against its alternatives | The choice is a table, not a feeling |
| 12 | Failure modes actually seen in production | CME is a bug detector you got lucky with, not a safety net |
| 13 | Version history and the stale claims interviewers repeat | `ArrayList` has never doubled — 1.5×, every released JDK |
| 14 | Ordering, `equals`/`hashCode`, comparators | `List.equals` is positional — `ArrayList` can equal a `LinkedList` |
| 15 | Streams, arrays, generics interop | `toArray()` always returns `Object[]` |
| 16 | Building and measuring the claims yourself | Every number in this set was run, not recalled |
| 17 | This file — questions 1 to 19 | The table above is the whole set's map before the streets |
| 18 | Questions 20 to 38 — cost, choice, failure, versions, ordering, interop | Picks up where this file's `Sets up` line points |
| 19 | Eight predict-the-output puzzles | Can you trace the mechanism, not just recite it |

---

### Q1. What does `ArrayList` actually guarantee, and what does it explicitly not?

**Say this.** A positional contract: every element has a stable index from
zero to `size() minus one`, iteration matches insertion order, and
duplicates — even value-identical ones — are always legal, since `add` never
compares the incoming element to anything already there. Past that it
guarantees nothing about threads, nothing about detecting concurrent
structural change, and nothing about staying sorted — each is a separate,
opt-in mechanism.

**The mechanism.** The contract lives on `List` itself — `get`, `set`,
`add(int,E)`, `remove(int)`, and the specified `equals`/`hashCode`, position
by position. `ArrayList` adds nothing to it, it just implements it over a
plain array.

**Follow-up they will ask.** "Is it thread-safe?" No synchronization exists
anywhere in the class — two threads racing inside `add` can corrupt the
array or lose an element with no exception guaranteed either way; opt in via
`Collections.synchronizedList` or `CopyOnWriteArrayList`.

---

### Q2. Does `ArrayList` allow `null` elements?

**Say this.** Yes, anywhere, any number of times, with no special-casing in
`add`, `get`, or `remove` — a slot is just a reference. `List.of(...)` is
the deliberate contrast: it rejects `null` at construction so "absent" can
never be confused with "present and null." `HashMap` draws a third line —
one `null` key, unlimited `null` values.

**The mechanism.** `List.of("x", null)` throws `NullPointerException` from
the factory call itself, before any list exists — refactoring `new
ArrayList<>(List.of(x, null))` down to plain `List.of(x, null)` moves the
failure upstream of where the `null` is used.

**Follow-up they will ask.** "Why would you want one?" When "not yet known"
is a real state — an unmatched bank credit with no attributed client ID —
an immutable snapshot could never have been built with that field unset.

---

### Q3. What's the difference between `size()` and capacity?

**Say this.** `size()` is content — part of the `List` contract, specified
and callable. Capacity is implementation — literally `elementData.length` —
and has no accessor anywhere on the class; you cannot ask a live `ArrayList`
its capacity without reflection or a heap dump. Capacity exists so the
array can over-allocate on purpose and most `add` calls avoid paying for a
copy.

**The mechanism.** No `capacity` field exists. `elementData` is
package-private only so `Itr`/`SubList` can read it without a synthetic
accessor — internal access, not a public one.

**Follow-up they will ask.** "Do `new ArrayList<>()` and `new
ArrayList<>(0)` start the same?" Both report `size() == 0`, but they're two
different sentinel objects underneath (Q11), so they grow differently from
the first `add`.

---

### Q4. Walk me through where `ArrayList` sits in the collections hierarchy.

**Say this.** Two independent chains meet here. The interface chain —
`Iterable` → `Collection` → (since Java 21) `SequencedCollection` → `List` —
widens what you can call. The implementation chain — `AbstractCollection` →
`AbstractList` → `ArrayList` — supplies generic bodies `ArrayList` mostly
throws away for array-specific speed. Which chain a method came from tells
you its cost before reading source.

**The mechanism.** Of everything `AbstractList`/`AbstractCollection`
declare, only `modCount`, `subListRangeCheck`, `containsAll`, and `toString`
survive unoverridden into a live call.

**Follow-up they will ask.** "What did `SequencedCollection` add?" JEP 431
gave `getFirst`/`getLast`/`addFirst`/`addLast`/`removeFirst`/`removeLast`/
`reversed()` a shared home — before it, first/last vocabulary lived
separately on `Deque` and `SortedSet` with no common type to name.

---

### Q5. What does `RandomAccess` actually buy you?

**Say this.** Nothing behavioural — zero members. It's a flag saying
"indexed `get(i)` costs the same regardless of `i`," and only *consuming*
code changes behaviour when it checks for it. `ArrayList` implements it;
`LinkedList` doesn't.

**The mechanism.** `Collections.binarySearch`, `.reverse`, `.shuffle`,
`.fill`, `.copy`, `.indexOfSubList`, `.rotate`, and `.swap`'s callers all
branch on `instanceof RandomAccess` — `binarySearch` is literally two
private methods, and the public entry point picks one before comparing
anything.

**Follow-up they will ask.** "So `instanceof ArrayList` works too?" No —
`List.of(...)`, `Arrays.asList(arr)`, and
`Collections.unmodifiableList(anArrayList)` are all `RandomAccess` too and
none is an `ArrayList`; the marker travels with array-backed storage, not
the class name.

---

### Q6. When would you reach for `LinkedList`, `ArrayDeque`, `Vector`, or `CopyOnWriteArrayList` instead?

**Say this.** Each trades away one `ArrayList` strength for something it
can't offer. `LinkedList` trades index-cheap access for cheap insertion
given an already-positioned iterator. `ArrayDeque` trades away being a
`List` at all to get amortised O(1) at both ends with no per-element node.
`Vector` keeps `ArrayList`'s shape but synchronizes every method and
doubles instead of growing 1.5×. `CopyOnWriteArrayList` copies the whole
array per write for a snapshot iterator that never throws CME — fine for a
rarely-written listener list, wrong for anything write-heavy.

**The mechanism.** File 02's sibling table is the reference; pick
`ArrayList` unless one specific column from another row is what you need.

**Follow-up they will ask.** "A real example?" `Movement.entries` wants
`List.copyOf(...)` — append-only; `PaymentRun.itemIds` wants a plain
`ArrayList<Id>`; a reservation-expiry tracker wants `PriorityQueue`, not a
`List` at all, because the access pattern is "give me the soonest."

---

### Q7. Why can `list.containsAll(other)` be a hidden performance trap?

**Say this.** `containsAll` and `toString` are the only two
`AbstractCollection` methods `ArrayList` never overrides, so the call falls
through to the generic body: one `contains` per element of the argument.
`ArrayList.contains` is itself O(n), so the whole call is O(n·m), and
nothing at the call site signals that — it sits next to `get(int)`, an O(1)
override, in the same interface.

**The mechanism.** `AbstractCollection.containsAll(c)` is `for (Object e :
c) if (!contains(e)) return false;` — correct for every `Collection`, fast
only for the ones whose own `contains` is fast.

**Follow-up they will ask.** "The fix?" Copy the receiver into a `HashSet`
first — the same boolean answer drops to O(n+m), because each `contains`
becomes O(1). The fix is never inside `containsAll`.

---

### Q8. What's an "optional operation," and when have you hit `UnsupportedOperationException`?

**Say this.** `Collection`/`List` split methods into ones every
implementation must genuinely support and structural mutators an
implementation may refuse via `UnsupportedOperationException`. A plain
`ArrayList` supports every optional operation; the exception shows up when
a `List<X>` reference actually points at `List.of(...)`, `stream().toList()`,
or `Arrays.asList(arr)`.

**The mechanism.** `AbstractList`'s default `add(int,E)`/`set(int,E)`/
`remove(int)` bodies are, absent an override, exactly `throw new
UnsupportedOperationException();` — `ArrayList` overrides all three.

**Follow-up they will ask.** "Is `Arrays.asList(arr)` immutable?" No —
fixed-size: `set(0, v)` succeeds and writes through to `arr`, but
`add`/`remove` throw because the array can't change length.

---

### Q9. Walk me through the three constructors — what capacity does each leave you with?

**Say this.** `ArrayList()` defers everything, pointing at a sentinel until
the first `add` jumps to 10. `ArrayList(int)` allocates exactly that many
slots immediately, no rounding, and throws `IllegalArgumentException` on
negative input. `ArrayList(Collection)` copies — or, in one case, adopts —
the source, sized to exactly `c.size()`.

**The mechanism.** The no-arg constructor assigns
`DEFAULTCAPACITY_EMPTY_ELEMENTDATA`, a sentinel `grow` checks by identity to
decide whether an empty list still owes itself the free jump to 10.

**Follow-up they will ask.** "Does `new ArrayList<>(c)` always copy?" No —
when `c.getClass() == ArrayList.class` exactly, an exact-class test, the
constructor adopts `c.toArray()`'s array outright since it's known fresh.
Any other source, including a subclass, copies.

---

### Q10. What's the difference between `List.of(...)`, `Arrays.asList(...)`, `stream().toList()`, and `Collectors.toList()`?

**Say this.** All four type-check as `List<X>` and behave nothing alike.
`List.of(...)` and `stream().toList()` are fully immutable — every mutator
throws, and `List.of` also rejects `null`. `Arrays.asList(arr)` is
fixed-size and write-through: `set` mutates `arr` itself, `add`/`remove`
throw. `Collectors.toList()` gives a genuinely mutable `ArrayList` — but as
a documented implementation detail, not a contract.

**The mechanism.** `stream().toList()` returns `ImmutableCollections$ListN`;
`Collectors.toList()` returns `java.util.ArrayList`; `Arrays.asList(arr)`
returns `Arrays$ArrayList`, wrapping the exact array passed in.

**Follow-up they will ask.** "How do you guarantee `ArrayList` from a
collect?" `.collect(Collectors.toCollection(ArrayList::new))` — that call
site is the actual contract.

---

### Q11. What are the two "empty" sentinel arrays, and why does `ArrayList` need both?

**Say this.** `EMPTY_ELEMENTDATA` and `DEFAULTCAPACITY_EMPTY_ELEMENTDATA`
are two distinct, value-equal, identity-distinct heap objects encoding one
bit: was this list default-constructed, or given an explicit empty
capacity? Java 7 made the no-arg constructor lazy; Java 8 split the
sentinel so laziness didn't also break the old "grows to 10" behaviour.

**The mechanism.** Only two call sites read the identity, both `==`/`!=`:
`grow(int)` and `ensureCapacity(int)`. The only way to hit the
`new Object[Math.max(10, minCapacity)]` branch is being exactly a fresh
`new ArrayList<>()` on its first element.

**Follow-up they will ask.** "Does `new ArrayList<>(0)` grow to 10 too?"
No — it grows to 1, following the 1.5× recurrence from a lower floor,
because it holds plain `EMPTY_ELEMENTDATA`; `new ArrayList<>(List.of())`
behaves the same way.

---

### Q12. Does `ArrayList` double its capacity when it grows?

**Say this.** No — the most common stale belief about this class, untrue in
every released JDK including Java 8. Growth is `oldCapacity + (oldCapacity
>> 1)`, a nominal 1.5×. `Vector` is the type that genuinely doubles, when
`capacityIncrement` is zero — easy to conflate since `ArrayList` replaced
it.

**The mechanism.** `grow` computes the minimum growth needed and the
preferred (amortising) growth, and `ArraysSupport.newLength` takes
`Math.max` of the two — which is also what rescues capacity 0 and 1 from
stalling, since `oldCapacity >> 1` is zero at both.

**Follow-up they will ask.** "Why 1.5× not 2×?" Copies-per-element across
all resizes is bounded by `f/(f-1)`: 3 at 1.5×, 2 at 2.0× — doubling copies
fewer times, at up to 100% wasted capacity versus 50%.

---

### Q13. What is `SOFT_MAX_ARRAY_LENGTH`, and is it a hard cap?

**Say this.** `Integer.MAX_VALUE - 8`, and it's soft — it clamps only
speculative growth. When the caller's actual minimum demands more, a
cold-path method, `hugeLength`, deliberately exceeds it, throwing
`OutOfMemoryError` only on genuine overflow. The real ceiling is
`Integer.MAX_VALUE` elements, because `size` is `int`.

**The mechanism.** Both the constant and the growth methods live on
`jdk.internal.util.ArraysSupport`, shared across every JDK collection that
grows an array — not on `ArrayList` at all.

**Follow-up they will ask.** "Isn't there `ArrayList.MAX_ARRAY_SIZE`?"
Version trap — it existed as `ArrayList`'s own field through JDK 12,
replaced by `ArraysSupport` starting JDK 13. It's gone in Java 21.

---

### Q14. Walk me through `remove(int)` — what happens to the slot the last element used to occupy?

**Say this.** It bounds-checks, saves the value, and delegates to
`fastRemove`, which shifts everything after the index one slot left with a
single `arraycopy`, then explicitly nulls the now-unused trailing slot.
That's not cosmetic: without it, the array still holds a live reference the
GC can see, so the removed object leaks until the array is replaced.

**The mechanism.** One statement does two jobs: `es[size = newSize] =
null;` — assigns the smaller size, then uses that value to index the
null-write.

**Follow-up they will ask.** "Same cost regardless of index?" No — O(size
minus index): index 0 shifts everything, the last index shifts nothing and
degenerates to a single null-store, exactly `removeLast()`'s fast path.

---

### Q15. Why is `add(E)` internally split into two methods?

**Say this.** `add(E)` sits on the hottest possible path, and the JIT's
fast tier, C1, only inlines a call site if the callee's bytecode is small
enough. The public `add(E)` stays a tiny increment-plus-delegate so it
stays inlinable in a hot loop; the heavier grow-capable logic lives off
that path in a private helper.

**The mechanism.** The source comment names the number: bytecode under 35,
`-XX:MaxInlineSize`'s default on this build.

**Follow-up they will ask.** "Does `add(int, E)` get the same split?" No —
it already needs a bounds check and an inline `arraycopy`, so there's no
cheap sub-path worth carving out.

---

### Q16. Is `addFirst(E)` O(1)? Does `clear()` give memory back?

**Say this.** Neither does what the name suggests. `addFirst(E)`, from the
Java 21 `SequencedCollection` retrofit, is literally `add(0, element)` — a
full tail shift, O(size), every call; the retrofit added vocabulary, not
performance. `clear()` nulls every slot for GC purposes but never
reassigns `elementData` — capacity is fully retained; `trimToSize()` is the
only way to shrink it back.

**The mechanism.** `addFirst` is a one-line delegation. `clear()`'s loop
walks and nulls, and stops — it never touches `elementData.length`.

**Follow-up they will ask.** "What for cheap front-insertion?" `ArrayDeque`
— a circular array, amortised O(1) at both ends, no per-element node.

---

### Q17. Why do `get(3)` and `add(3, "x")` throw exceptions with different message formats on the same one-element list?

**Say this.** Two different bounds checks. `get`/`set`/`remove(int)` go
through `Objects.checkIndex(index, size)`, producing "Index N out of
bounds for length N." `add(int, E)`/`addAll(int, ...)` go through
`ArrayList`'s own `rangeCheckForAdd`, producing "Index: N, Size: N."

**The mechanism.** `add(int, E)` must legally accept `index == size` —
that's how you append by position — while `get`/`set`/`remove(int)` must
reject it; `rangeCheckForAdd` is deliberately one comparison wider.

**Follow-up they will ask.** "Which runs first, the bounds check or
`modCount++`?" The bounds check — `rangeCheckForAdd` runs before
`modCount++`, so a rejected call never counts as a structural change.

---

### Q18. How does `removeIf` avoid corrupting the list while still calling your predicate?

**Say this.** Two passes. The first calls your predicate on every element
in range and marks matches into a `long[]` bitset, `deathRow`, without
moving anything; only after a `modCount` check does a second pass compact
survivors down. That split is what lets your predicate safely call
`list.get`/`contains` on the list it's filtering, since nothing has moved
yet.

**The mechanism.** One `long` per 64 candidates. The predicate runs on
every element regardless of matches already found — no short-circuit,
since the method can't know how many need marking until the whole range is
visited.

**Follow-up they will ask.** "What if the predicate mutates the list?" The
`modCount` check sits between the passes; a mutating predicate throws CME
before any compaction happens.

---

### Q19. What's the one method behind `removeAll`/`retainAll`, and why can `removeAll(aList)` be much slower than `removeAll(aSet)`?

**Say this.** Both call the same method, `batchRemove`, with one boolean
flipped. Cost comes entirely from calling `contains` on the argument, once
per receiver element — and that cost belongs to the argument's type. A
`List` argument makes it O(n·m); a `HashSet` argument makes it O(n). Same
two lines, same answer, very different cost.

**The mechanism.** If `contains` throws mid-scan, a `catch (Throwable)`
slides the still-unexamined tail back to the write cursor before
rethrowing, and `finally` always fixes `modCount` and closes the gap — a
consistency guarantee, not an atomic rollback.

**Follow-up they will ask.** "Does `removeIf` give the same guarantee on a
throwing predicate?" No — it has no `catch`; an uncaught throw there
propagates with the list untouched, since it happens before either pass
writes back.

---

## Pitfalls

### "Is `ArrayList` thread-safe?" — "No." — and stopping there

**Wrong:** answering "No" and stopping.

**Right:** "No — no synchronization anywhere, so two threads racing inside
`add` can corrupt the array or lose an element with no exception guaranteed
either way. `Collections.synchronizedList` gives a whole-object lock but its
iterator still isn't synchronized; `CopyOnWriteArrayList` fits a read-mostly
workload wanting a snapshot iterator instead."

**Why people believe it:** the negative is a true, complete sentence that
answers the literal question — but a guarantee question is almost always
also asking what you do about the gap.

### "How does it grow?" — "It doubles." — and moving on

**Wrong:** "It doubles in size each time."

**Right:** "Roughly 1.5× — `oldCapacity + (oldCapacity >> 1)` — true in
every released JDK including Java 8. `Vector` is the one that actually
doubles. The 1.5× factor bounds copies-per-element at 3 across all resizes,
versus 2 for doubling, at the cost of higher peak wasted capacity."

**Why people believe it:** `Vector` really does double by default, and
"growable array doubles" is generic computer-science folklore nobody
corrects because the wrong answer still compiles and runs.

## Cheat sheet

| Question | One-line answer |
|---|---|
| Thread-safe? | No — opt in via `synchronizedList` or `CopyOnWriteArrayList` |
| Allows `null`? | Yes, anywhere, any count — `List.of` rejects it |
| `size()` vs capacity | Contract vs `elementData.length`, no accessor |
| Hierarchy | `Iterable→Collection→SequencedCollection→List`; `AbstractCollection→AbstractList→ArrayList` |
| `RandomAccess` | Zero members — a performance promise, algorithms branch on it |
| `containsAll` cost | O(n·m) — never overridden by `ArrayList` |
| Optional operations | Structural mutators may throw `UnsupportedOperationException` |
| Three constructors | `()` sentinel→10; `(int)` exactly `n`; `(Collection)` copies or adopts |
| Collection ctor fast path | Adopts only when `c.getClass()==ArrayList.class` |
| `List.of`/`Arrays.asList`/`Collectors.toList()` | immutable / fixed-size write-through / mutable, not contractual |
| Two sentinels | `DEFAULTCAPACITY_EMPTY_ELEMENTDATA`(→10) vs `EMPTY_ELEMENTDATA`(→1) |
| Growth factor | 1.5×, never 2×, every released JDK |
| `SOFT_MAX_ARRAY_LENGTH` | `Integer.MAX_VALUE-8`, soft, speculative-growth only |
| Real element ceiling | `Integer.MAX_VALUE` — `size` is `int` |
| `remove(int)` trailing slot | Nulled — else the object leaks |
| `add(E)` split | Kept under C1's 35-byte inline budget |
| `addFirst(E)` | `add(0,e)` — O(n), not O(1) |
| `clear()` | Nulls slots, capacity survives |
| OOB messages | `checkIndex` vs `rangeCheckForAdd` — different strings |
| `removeIf` | Mark into `long[]` bitset, `modCount` check, compact |
| `removeAll`/`retainAll` | Both `batchRemove`; cost is the argument's `contains` |

## Self-test

**Q1.** Two `LedgerEntry` objects have identical amount, position, and
direction. Does adding both succeed?

<details><summary>Answer</summary>

Yes. `add` never compares the incoming element to what's already there —
duplicates are always legal.

</details>

**Q2.** `new ArrayList<>()` and `new ArrayList<>(0)` both report `size() ==
0`. Identical internally?

<details><summary>Answer</summary>

No — two different sentinel objects, `DEFAULTCAPACITY_EMPTY_ELEMENTDATA`
versus `EMPTY_ELEMENTDATA`, which changes the first `add`'s target capacity:
10 versus 1.

</details>

**Q3.** Why is `list.containsAll(other)` sometimes a quiet quadratic scan?

<details><summary>Answer</summary>

`ArrayList` never overrides `containsAll`; the inherited body calls
`contains` once per argument element, and `ArrayList.contains` is O(n),
making the whole call O(n·m).

</details>

**Q4.** True or false: `ArrayList` doubles its backing array every time it
grows.

<details><summary>Answer</summary>

False. It grows by `oldCapacity + (oldCapacity >> 1)`, roughly 1.5×, in
every released JDK. `Vector` is the type that genuinely doubles.

</details>

**Q5.** After `remove(int)` runs, why does the trailing slot get set to
`null` instead of left alone?

<details><summary>Answer</summary>

Without it, the array still holds a live reference the GC can see even
though `size` no longer counts it — the removed object can't be collected
until the array is replaced.

</details>

**Q6.** Is `addFirst(E)` an O(1) operation?

<details><summary>Answer</summary>

No — it's `add(0, element)`, a full tail shift, O(size), on every call. The
Java 21 retrofit added the name, not the performance.

</details>

**Q7.** `restrictions.removeAll(reversibleKeysAsList)` and `removeAll(...AsSet)`
return the same boolean. Same cost?

<details><summary>Answer</summary>

No — both route through `batchRemove`, whose cost is dominated by
`c.contains`: O(n·m) for a `List` argument, O(n) for a `HashSet` argument.

</details>

---

**Questions answered:** Q-46 (first half)
**Sets up:** Next: the remaining nineteen questions — cost, choice, failure, versions, ordering, interop.
**Diagrams included:** none
**Target version:** Java 21 LTS
**Lines:** 538
