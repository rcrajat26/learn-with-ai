# ArrayList — 11 Sorting, Comparable and Comparator

**Target version: Java 21.** | [Map](00-map.md)
Assumes: equality and hashing (file 10).
Previous: [10-equality-and-serialization.md](10-equality-and-serialization.md) · Next: [12-cost-and-memory.md](12-cost-and-memory.md)

### `Comparable` versus `Comparator`

**Mental model.** `Comparable` is a property of the *type*: the element class
declares "I have exactly one natural order," `compareTo(T)`. `Comparator` is a
property of the *call site*: a separate object declaring "here is *an*
order" — there can be as many `Comparator`s for a type as there are reasons
to sort it.

**Why both exist.** A type with one genuinely obvious order — `Integer`,
`String`, a timestamp id — should say so once, in the class. Most sorting
needs are call-site needs instead: today a `PaymentRun`'s items by amount,
tomorrow by age. Baking either into the class is arbitrary and wrong for the
other caller, so `Comparator` lets ordering live outside the type, as data.

**When each applies.** The real question is never "which is better" — it is
"does this type have a single, uncontested, canonical order, and do I own the
class":

| Situation | Choose |
|---|---|
| You own the class, and there is one obviously-correct order | `Comparable` |
| You do not own the class (JDK type, library type) | `Comparator` |
| The type has no single correct order (see `Money` below) | `Comparator`, scoped to the caller's context |
| You need more than one order for the same type | `Comparator` for each; `Comparable` can hold at most one |
| The order is a sorting-time decision, not a type-level fact | `Comparator` |

**The shared contract.** Both `compareTo(T)` and `compare(T,T)` return
negative/zero/positive for precedes/ties/follows. Both must be
**antisymmetric** (`sgn(compare(a,b)) == -sgn(compare(b,a))`) and
**transitive** (`compare(a,b)>0 && compare(b,c)>0` implies `compare(a,c)>0`).
Consistency with `equals` — `compare(a,b)==0` implies `a.equals(b)` — is
**recommended, not required** by the Javadoc. **Pitfall:** a `compareTo`
that returns 0 for objects that are not `equals` is legal, but silently
breaks `TreeSet`/`TreeMap`, whose uniqueness is defined by `compareTo`, not
`equals` — such a `TreeSet<T>` collapses distinct elements into one.

**The modern `Comparator` factory API.** This is what production code
actually writes, not a hand-rolled anonymous class:

```java
Comparator<LedgerEntry> byPostedTime =
    Comparator.comparingLong(LedgerEntry::postedAt);
Comparator<LedgerEntry> byTimeThenDirection =
    Comparator.comparingLong(LedgerEntry::postedAt)
               .thenComparing(LedgerEntry::direction);
Comparator<LedgerEntry> newestFirst = byPostedTime.reversed();
Comparator<PaymentRun> byOptionalSignOff =
    Comparator.comparing(PaymentRun::signedOffBy,
        Comparator.nullsFirst(Comparator.naturalOrder()));
```

`comparingInt` / `comparingLong` / `comparingDouble` exist as separate
overloads from the generic `comparing` for a real reason: the generic form
takes a `Function<T,U>` where `U extends Comparable`, forcing the primitive
key (`long postedAt`) to be **boxed into a `Long`** on every comparison just
to get a `Comparable` to call `compareTo` on. The primitive overloads take an
`IntFunction`/`ToLongFunction`/`ToDoubleFunction`, extract the primitive
directly, and compare with `Integer.compare`/`Long.compare`/`Double.compare`
— no boxing per comparison across an `n log n`-comparison sort.
`thenComparing` chains a tiebreaker; `reversed()` flips the whole chain;
`nullsFirst`/`nullsLast` push `null` to one end instead of throwing;
`naturalOrder()`/`reverseOrder()` hand back `Comparable`-based comparators
without writing one.

**Verified run**, sorting four `LedgerEntry` records by posting time then by
direction as a tiebreaker:

```
Comparator.comparingLong(LedgerEntry::postedAt).thenComparing(LedgerEntry::direction)
over entries E5,E1,E3,E2  ->  sorted ids [E3, E1, E5, E2]
```

**Interview:** "When would you implement `Comparable` over a `Comparator`?"
— only when you own the type and there is one order any caller would expect
by default; anything context-dependent, or any type you don't own, is a
`Comparator`.

> **`Comparable` is one canonical order owned by the type; `Comparator` is any
> number of orders owned by the caller.**

### `List.sort` and the `modCount` bump

**Mental model.** `List` declares `sort` as a `default` method (since Java 8)
that would otherwise dump the list into an `Object[]` via `toArray()`, sort
that, and copy back through `ListIterator.set`. `ArrayList` overrides it
because that round-trip is pure waste when the list already *is* an array —
it reaches directly into its own backing array instead.

**How it works.** `ArrayList.sort` calls
`Arrays.sort(elementData, 0, size, c)` — sorting only the live range,
never the spare capacity beyond `size` — and then does one thing that
surprises people:

```
modCount before sort=0  after sort=1
modCount after set()  = unchanged   (set is NOT structural)
modCount after add()  = incremented (add IS structural)
```

**Insight:** the usual heuristic taught for `modCount` is "structural change
means the size changed." Sorting does not touch `size` at all — yet it still
bumps `modCount`. The heuristic is wrong; the real rule is "does this
invalidate an in-progress iterator's assumptions about element positions,"
and reordering every element does exactly that just as thoroughly as
inserting one would. `set()` doesn't bump `modCount` because replacing a
value at a fixed index doesn't move anything else; `sort()` moves everything.

A sort triggered mid-iteration over the same list throws
`ConcurrentModificationException`, exactly like a mid-iteration `add` would,
for the same underlying reason — see the Pitfalls section for the full
example.

`sort(null)` means "use the elements' natural ordering" — it delegates to
`Arrays.sort(elementData, 0, size, null)`, which routes to the `Comparable`
path. If the element type does not implement `Comparable`, this fails, but
**not at compile time**:

```
sort(null) on a non-Comparable element type  ->  java.lang.ClassCastException
```

**Pitfall:** `List<E>.sort(Comparator<? super E>)` accepts `null` in its
signature regardless of what `E` is, and generic erasure means the compiler
has no way to check `E extends Comparable<? super E>` at the call site. The
failure only appears at runtime, inside `Arrays.sort`, when it tries to cast
an element to `Comparable` and finds it isn't one.

> **`sort` is structural because it reorders, not because it resizes — it
> bumps `modCount` even though `size` never changes.**

### TimSort and stability

**Mental model.** `Arrays.sort` on an `Object[]` — which is what
`ArrayList.sort` calls — does not use quicksort. It uses **TimSort**, a
merge sort variant that detects existing runs of ordered elements and merges
them, and it is **stable**: two elements that compare equal keep their
original relative order.

**Why stability matters here.** Primitive sorts (`int[]`, `long[]`, …) have
no notion of "the same value, but a different object with other fields" —
every `5` is interchangeable, so stability is meaningless and a dual-pivot
quicksort, faster and in-place, is used instead. Object sorts differ: two
`LedgerEntry` records can compare equal on one key (`direction`) while
differing on everything else (`postedAt`, `amount`). Losing relative order on
a tie would be a silent correctness bug, not just an aesthetic one.

**Demonstrated concretely.** Sort ledger entries by `postedAt`, then sort the
*result* again by `direction` alone: because the second sort is stable, every
group sharing the same `direction` keeps the `postedAt` order it already
had. That is also *why* `thenComparing` beats "sort twice" — both are correct
because of stability, but `thenComparing` does it in one `O(n log n)` pass.

```java
List<LedgerEntry> byDirectionThenTime = new ArrayList<>(entries);
byDirectionThenTime.sort(Comparator.comparingLong(LedgerEntry::postedAt));
byDirectionThenTime.sort(Comparator.comparing(LedgerEntry::direction));
// equivalent in outcome, but two O(n log n) passes, to:
byDirectionThenTime.sort(
    Comparator.comparing(LedgerEntry::direction)
               .thenComparingLong(LedgerEntry::postedAt));
```

**Costs, with their causes:**

| Case | Cost | Why |
|---|---|---|
| General case | `O(n log n)` comparisons | Merge sort structure |
| Already-sorted or reverse-sorted input | `O(n)` | TimSort detects the existing run and skips merging within it |
| Extra space, worst case | `O(n/2)` | The merge step needs a temporary buffer for one side of the merge |

Contrast with `Arrays.sort(int[])`, which uses a dual-pivot quicksort:
in-place, no merge buffer, no stability to preserve — because stability buys
nothing for primitives, the algorithm that wins is the one with less
overhead, not the one with a guarantee nobody needed.

> **TimSort is the stable, run-aware merge sort `ArrayList.sort` relies on
> precisely because object elements can tie on the sort key while differing
> everywhere else.**

### The comparator contract and its detection

**Mental model.** TimSort's merge step relies on the comparator behaving
consistently across the whole sort — every comparison result has to be
compatible with every other, or the merge invariants it maintains internally
stop holding.

**Why detection exists.** When those invariants are violated in a way
TimSort's internal bookkeeping happens to notice, it throws
`IllegalArgumentException: Comparison method violates its general contract!`
rather than silently producing a wrong order.

**Be precise about what this guarantees — very little.** A verified run on
21.0.7 used a comparator that unconditionally returned `1` (blatantly
non-antisymmetric) over 40 elements, and it **did not throw**. The exception
is real for some broken comparators, but only fires when the actual run
structure TimSort builds happens to exercise the check; it is not a validator
you can rely on to catch a bad comparator in testing. Absence of the
exception is not evidence the comparator is correct.

**Real-world causes, most common first.** Subtraction overflow — see the
Pitfalls section for the full `Money` example, fixed by `Long.compare`/
`Integer.compare` or the `comparingLong`/`comparingInt` factories, never raw
subtraction. A comparator reading mutable state that changes mid-sort — the
relative order of any two elements must stay fixed for the sort's duration,
or the violation is real even without the exception. Inconsistent `null`
handling — sometimes treating `null` as smallest, sometimes throwing NPE,
instead of using `Comparator.nullsFirst`/`nullsLast` uniformly.

**Interview:** "How would you catch a bad comparator?" — not by relying on
`IllegalArgumentException`; write it with the safe primitives or factory
methods so the bug class is structurally impossible, and unit-test
antisymmetry/transitivity directly if the comparator is nontrivial.

> **The contract-violation exception is a sometimes-fired side effect of
> TimSort's internals, not a correctness check you can depend on.**

### Supporting facts

`Collections.sort(list)` has delegated to `list.sort(null)` since Java 8 —
not a different algorithm, just an older-looking call; harmless but nothing
`list.sort(null)` doesn't already do.

`list.sort(comparator)` versus `list.stream().sorted(comparator).toList()`:
the first sorts **in place**, mutating the existing `ArrayList` and returning
`void`; the second allocates a **new** list and leaves the original
untouched. Pick based on whether other holders of the reference should see
the reordering.

`Collections.binarySearch(list, key)` requires the list already be sorted
**by the same ordering the search assumes**. Feed it a list sorted by a
different key and it returns a nonsense index silently, no exception. It also
branches on `RandomAccess` (file 01): index-based search for a `RandomAccess`
list, an iterator-based walk otherwise, because jumping to an arbitrary index
on a linked structure is itself `O(n)`.

## Pitfalls

### Comparing `Money` amounts by subtracting `long`s

**Wrong**
```java
Comparator<Money> byAmount = (a, b) ->
    (int) (a.amount().unscaledValue().longValue()
         - b.amount().unscaledValue().longValue());
// two amounts far enough apart flip sign on overflow -> wrong order,
// and it can violate the comparator contract with no exception at all
```

**Right**
```java
Comparator<Money> byAmount =
    Comparator.comparingLong(m -> m.amount().unscaledValue().longValue());
```

**Why people believe it:** subtraction "obviously" gives negative/zero/positive,
and it works in every manual test with small numbers.

### Assuming `sort(null)` fails at compile time for a non-`Comparable` element

**Wrong**
```java
List<Restriction> restrictions = new ArrayList<>(...);
restrictions.sort(null); // compiles fine, Restriction isn't Comparable
// java.lang.ClassCastException at runtime
```

**Right**: either implement `Comparable` on the type if it truly has one
canonical order, or pass an explicit `Comparator`.

**Why people believe it:** generics look like they'd catch this, but erasure
removes the type information `sort(null)` would need to check ahead of time.

### Sorting a list while iterating over it

**Wrong**
```java
for (LedgerEntry e : entries) {
    entries.sort(Comparator.comparingLong(LedgerEntry::postedAt));
}
// java.util.ConcurrentModificationException
```

**Right:** sort before the loop starts, or iterate over a separate sorted
copy (`entries.stream().sorted(...).toList()`) if the original order must
stay live elsewhere.

**Why people believe it:** `sort` doesn't change `size`, so it doesn't look
"structural" the way `add`/`remove` obviously are.

### Treating `compareTo` returning 0 as the same signal as `equals`

**Wrong**
```java
Set<LedgerEntry> byTime = new TreeSet<>(
    Comparator.comparingLong(LedgerEntry::postedAt));
byTime.add(entry1);
byTime.add(entry2); // different entry, same postedAt -> silently dropped
```

**Right:** if a `TreeSet`/`TreeMap` needs true per-element uniqueness, make
the comparator consistent with `equals`, or use a `HashSet` instead.

**Why people believe it:** `compareTo == 0` reads like "equal," and the
Javadoc's "recommended, not required" nuance is easy to skip past.

### Trusting `IllegalArgumentException` to catch a bad comparator

**Wrong**: shipping a comparator with a subtle contract violation because a
manual test run didn't throw.

**Right:** write comparators with the safe primitive-comparing factories, and
unit-test contract properties directly rather than relying on TimSort.

**Why people believe it:** the exception message is explicit, so its absence
feels like a clean bill of health.

## Cheat sheet

| Question | Answer |
|---|---|
| One canonical order, own the type | `Comparable<T>`, `compareTo(T)` |
| Any other ordering need | `Comparator<T>`, `compare(T,T)` |
| Avoid boxing in a numeric key comparator | `comparingInt`/`comparingLong`/`comparingDouble` |
| Chain a tiebreaker | `thenComparing(...)` |
| Flip an order | `.reversed()` |
| Handle `null` keys | `Comparator.nullsFirst`/`nullsLast` |
| `ArrayList.sort` bumps `modCount`? | Yes — reordering invalidates iterators even though `size` is unchanged |
| `sort(null)` on non-`Comparable` element | `ClassCastException` at runtime, not a compile error |
| Underlying algorithm for `Object[]` | TimSort — stable, run-aware merge sort |
| Underlying algorithm for `int[]` etc. | Dual-pivot quicksort — no stability needed |
| Worst-case time / already-sorted time | `O(n log n)` / `O(n)` |
| Worst-case extra space | `O(n/2)` for the merge buffer |
| Does the contract-violation exception always fire on a bad comparator? | No — verified it can silently not fire |
| `Collections.sort(list)` vs `list.sort(null)` | Same call since Java 8 |
| In-place sort vs new sorted list | `list.sort(c)` mutates; `stream().sorted(c).toList()` allocates |
| `binarySearch` precondition | List must already be sorted by the same ordering used to search |

## Self-test

**Q1.** Why does `ArrayList.sort` increment `modCount` even though it never
changes `size`?

<details><summary>Answer</summary>

Because the real definition of "structural" is "invalidates an in-progress
iterator's assumptions," not "changes size." Sorting reorders every element
in place, which is exactly as disruptive to a live iteration as an insert or
removal would be, even though the element count never moves. `modCount`
tracks that disruption, not the size.

</details>

**Q2.** You have a `List<Restriction>` and call `list.sort(null)`. It compiles.
What happens at runtime if `Restriction` does not implement `Comparable`, and
why didn't the compiler catch it?

<details><summary>Answer</summary>

It throws `ClassCastException` at runtime — verified on 21.0.7. The compiler
can't catch it because `sort(Comparator<? super E>)` accepts `null`
regardless of `E`, and erasure removes the type information needed to check
`E extends Comparable` at the call site. The cast only happens inside
`Arrays.sort` when it tries to invoke `compareTo`.

</details>

**Q3.** Why does `Comparator.comparingLong` exist as a separate method from
the generic `Comparator.comparing`, instead of everyone just using `comparing`
with a `Long`-returning function?

<details><summary>Answer</summary>

`comparing` takes a function returning a `Comparable`, boxing a `long` key
into a `Long` on every comparison of an `O(n log n)` sort just to call
`compareTo`. `comparingLong` takes a `ToLongFunction`, extracts the primitive
directly, and compares with `Long.compare` — no boxing.

</details>

**Q4.** Two `LedgerEntry` sorts are run back to back: first by `postedAt`,
then by `direction`. Why does the `postedAt` order survive within each
`direction` group, and what does that depend on?

<details><summary>Answer</summary>

It depends on TimSort being stable: when the second sort finds two entries
that compare equal on `direction`, it does not reorder them relative to each
other, so whatever relative order they had going in — established by the
first sort's `postedAt` ordering — is preserved. If the underlying sort were
not stable, ties on `direction` could be shuffled arbitrarily.

</details>

**Q5.** A comparator that always returns `1` was tested on 40 elements and did
not throw `IllegalArgumentException: Comparison method violates its general
contract!`. Does that mean the comparator is safe to ship?

<details><summary>Answer</summary>

No. The exception fires only when TimSort's internal merge invariants happen
to be violated in a way its bookkeeping checks — it depends on the specific
run structure the input produces, not on whether the comparator is broken.
Verified: exactly this comparator over 40 elements did not throw, despite
being obviously non-antisymmetric. Absence of the exception is not evidence
of correctness.

</details>

**Q6.** Why is `Money` in this codebase deliberately not made `Comparable`,
even though amounts clearly have numeric values?

<details><summary>Answer</summary>

Because comparing amounts across different currencies is meaningless — 100
USD and 100 EUR have no single correct ordering without an exchange rate and
a point in time. Making `Money` `Comparable` would force a fake "natural"
order onto values that don't have one. A `Comparator<Money>` scoped to a
single known currency, chosen by the caller who knows that context, is
correct where a type-level `Comparable` would be a bug.

</details>

**Q7.** What is the difference in effect between `list.sort(comparator)` and
`list.stream().sorted(comparator).toList()`?

<details><summary>Answer</summary>

`list.sort(comparator)` sorts in place: it mutates the existing `ArrayList`
and returns `void`, so every other reference to that same list sees the new
order. `stream().sorted(comparator).toList()` leaves the original list
completely untouched and returns a new, separate list holding the sorted
result. The choice depends on whether the mutation is acceptable.

</details>

---

**Questions answered:** Q-24, Q-31
**Sets up:** Next: the full cost model and the memory arithmetic, now that every mechanism behind a number has been explained.
**Diagrams included:** none
**Target version:** Java 21
**Lines:** 448
