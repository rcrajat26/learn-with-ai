# `ArrayList` — 14 Backbone: ordering, equality and comparators

**Target version: Java 21 LTS.** | [Map](00-map.md)
Assumes: the member surface, including where sort, equals and hashCode are declared (file 03), and the modCount protocol (file 08).
Previous: [13 Version history and stale claims](13-version-history-and-stale-claims.md) · Next: [15 Interoperation — streams, arrays and generics](15-interoperation-streams-arrays-and-generics.md)

File 03 named `sort`/`replaceAll` as `List` defaults `ArrayList` overrides,
and named `equals`/`hashCode` as declared on `AbstractList`. This file is what
those names were pointing at: what `Comparable`/`Comparator` actually
promise, what `list.sort(c)` runs underneath, and what `list.equals(o)`
checks — all variations on one theme, a `List` handing your objects to
specified machinery whose correctness depends on obligations your objects
owe it, not on anything the list enforces.

## The map before the streets

| Machinery | Contract owner | Called by | Breaks how |
|---|---|---|---|
| `Comparable.compareTo` | The element type | `list.sort(null)`, `Collections.sort`, `TreeMap`/`TreeSet` | Wrong order, or `IllegalArgumentException` from TimSort |
| `Comparator.compare` | Whoever builds it | `list.sort(c)`, `Collections.sort(list, c)` | Same, at any call site using it |
| `Object.equals`/`hashCode` | The element type | `list.equals`, `contains`, `indexOf`, `HashMap`/`HashSet` | Wrong membership, unfindable map entries, lying `List.equals` |

`compareTo` and `equals` are two **independent** contracts on the same object — a `List` never assumes one implies the other (Q-36).

---

## Q-36 — The `Comparable` contract, and consistency with `equals`

**Mental model.** `Comparable` is a type saying "I have a built-in order, ask me to compare myself against a sibling" — a promise the class makes once, not a policy swappable per call (that is `Comparator`, Q-37).

**Why it exists.** Before `Comparable` (Java 1.2), sorting application objects
meant a bespoke sort function per type; it gives `Collections.sort`/
`Arrays.sort` one method to call for any conforming type, and lets
`TreeSet`/`TreeMap` order keys without a supplied comparator.

**When it applies.** Implement it when a type has one obvious canonical
order — `LedgerEntry` by `postedAt` is plausible. Skip it when several orders
are equally valid (`WithdrawalTransaction` by amount, by state, or by run) —
that belongs at the call site as a `Comparator`, not baked into the class.

**How it works — the contract.** For `x.compareTo(y)`: **antisymmetric**
(`sgn(x.compareTo(y)) == -sgn(y.compareTo(x))`, implying `x.compareTo(y)`
throws exactly when `y.compareTo(x)` throws); **transitive** (`x>y>0 &&
y>z>0 ⟹ x>z>0`); **substitutable when tied** (`x.compareTo(y)==0 ⟹
sgn(x.compareTo(z)) == sgn(y.compareTo(z))` for every `z`). Must throw
`NullPointerException` on a `null` argument; may throw `ClassCastException`
on an incomparable type.

**Consistent with `equals` is recommended, not required** — the Javadoc's own
phrase. The JDK's counter-example is `BigDecimal`: `"1.0"` and `"1.00"`
`compareTo` to `0` but are not `equals` (differing scale). In a `List`,
`contains` uses `equals`, so both survive as distinct entries; in a
`TreeSet`, membership uses `compareTo`, so inserting the second is a
silently dropped no-op. **Insight:** not a bug in either collection — the
documented consequence of the two contracts being allowed to disagree.

**The QuizStakes trap.** Appendix C.1 gives `Money` as `amount: Decimal` +
`currency: Currency`, with **value equality** — `equals` must compare both
fields, since 100 GBP and 100 EUR are never the same value. A `compareTo`
written only against `amount` is exactly the `BigDecimal` hazard, and it is
worse here: ordering amounts across currencies without a conversion rate is
not merely inconsistent, it is meaningless. Correct shape — compare only
within a currency, throw otherwise:

```java
public record Money(BigDecimal amount, Currency currency) implements Comparable<Money> {
    @Override
    public int compareTo(Money other) {
        if (!currency.equals(other.currency)) {
            throw new IllegalArgumentException(
                "cannot compare " + currency + " to " + other.currency);
        }
        return amount.compareTo(other.amount);
    }
}
```

Where a deterministic cross-currency order is genuinely needed (a mixed-
currency payout file), make currency the primary sort key so amounts are never
compared across it — `Comparator.comparing(Money::currency)
.thenComparing(Money::amount)` from Q-37, never a raw `compareTo`.

**Where each method looks.** `list.sort(null)`/`Collections.sort(list)` use
`compareTo` — every element must be `Comparable` or CCE fires. `contains`/
`indexOf`/`equals` use `equals`, never `compareTo`. Confusing the two is the
most common ordering bug: with the `Money` record above, `list.contains(eur)`
is `true` (equals compares currency too), while `gbp.compareTo(eur)` throws —
a `contains` check "should" find it by `compareTo`'s logic, but `contains`
never asks `compareTo`.

**The gotcha.** A `compareTo` returning `0` for objects that are not `equals`
is legal, but only a `List` tolerates the gap; `TreeSet`/`TreeMap` require
consistency with `equals` as a correctness condition, because `compareTo` is
their sole notion of "the same element" — noted here in one line, out of scope
otherwise.

> `Comparable.compareTo` defines a total order a type carries on itself —
> antisymmetric, transitive, substitutable for tied elements — and it is only
> *recommended*, not required, to agree with that type's `equals`.

---

## Q-37 — `Comparator` composition, and what `list.sort(c)` runs

**Mental model.** Where `Comparable` is a type's built-in order, `Comparator`
is an order supplied from outside — a strategy object, often a lambda, since
it is a functional interface. The list never needs to know how the comparator
decides, only that `compare(a,b)` returns negative, zero, or positive.

**Why it exists.** Not every useful order is a type's natural one, and a type
may have several competing orders. Java 8 added `comparing`/`thenComparing`/
`reversed` so these strategies compose instead of each combination needing a
hand-rolled `compare` body.

**When it applies.** Whenever the order is a property of the *use*, not the
type — the §14.3 reconciliation report needs `LedgerEntry` by `postedAt` then
`id`, but nothing about `LedgerEntry` says that is *the* order.

**How it works — delegation, not equality.** `Comparator.comparing(f)`
returns a comparator whose body is `f(a).compareTo(f(b))` — the extracted key
must itself be `Comparable`. `.thenComparing(next)` wraps it: run the first,
delegate to `next` only if it returned `0`. `.reversed()` wraps it to negate.
This is a **chain of delegating calls with a `!= 0` short-circuit**, like an
`||` chain — the first nonzero result wins and later comparators are never
invoked: `Comparator.comparing(LedgerEntry::postedAt)
.thenComparing(LedgerEntry::id)` (call it `byPostedThenId`) runs
`postedAt.compareTo` first and only falls through to `id.compareTo` on a tie.

**Factories, as supporting facts:** `naturalOrder()`/`reverseOrder()` are the
identity/reverse wrapper around a type's own `compareTo`. `nullsFirst(c)`/
`nullsLast(c)` **wrap a comparator, not a key extractor** —
`Comparator.comparing(LedgerEntry::postedAt)` alone still throws
`NullPointerException` on a `null` `postedAt`, because `nullsFirst` needs to
wrap the comparator applied to the extracted key:
`Comparator.comparing(LedgerEntry::postedAt,
Comparator.nullsFirst(Comparator.naturalOrder()))`. `comparingInt`/`Long`/
`Double` exist to avoid boxing: `comparing` on an `int` key autoboxes into an
`Integer` on every `compare` call just so `compareTo` can run, and a sort does
O(n log n) comparisons — O(n log n) throwaway boxes; the primitive
specializations compare directly and allocate none.

**Never `a - b`.** `Integer.MIN_VALUE - 1` overflows and flips sign, so the
comparator is not antisymmetric for some pair; TimSort only detects the break
when its merge invariant fails, by which point the offending comparison is
gone. Use `Integer.compare(a,b)`. `Double` has its own trap even without
overflow: `<`/`>` report `false` for every comparison touching `NaN`, and
treat `-0.0`/`0.0` as equal, where the spec requires `Double.compare` to
order `NaN` greatest and `-0.0` before `0.0`.

### What `list.sort(c)` actually runs

Quoted from `ArrayList.java`, JDK 21.0.7, lines 1802–1809:

```java
@Override
@SuppressWarnings("unchecked")
public void sort(Comparator<? super E> c) {
    final int expectedModCount = modCount;
    Arrays.sort((E[]) elementData, 0, size, c);
    if (modCount != expectedModCount)
        throw new ConcurrentModificationException();
    modCount++;
}
```

![`sort` hands the backing array straight to TimSort. A broken comparator is detected by the sort, not by the list.](diagrams/D-18-sort-call-chain.svg)

Six things this does. **(1)** `modCount` snapshotted before — file-08's
fail-fast pattern. **(2)** The array itself is passed, unchecked cast to
`E[]` — no copy; only `[0, size)` is touched, trailing nulls from file 06 left
alone. **(3)** `Arrays.sort(T[], int, int, Comparator)` runs **TimSort**.
**(4)** A comparator that reentrantly mutates the list bumps `modCount`
mid-sort; the post-sort check catches it as CME, thrown after the corrupted
`Arrays.sort` call already returned. **(5)** `modCount++` at the end makes
`sort` a structural modification for every live iterator even though size
never changed. **(6)** A `null` comparator means natural order; CCE fires at
the first comparison if elements aren't `Comparable`, not before the sort
starts.

**The algorithm, at this depth.** TimSort is stable, adaptive, natural
mergesort: it detects existing ascending/descending runs, extends short runs
with binary insertion sort, merges with galloping. Worst case O(n log n),
**best case O(n) on already-sorted or reverse-sorted input** (one run,
nothing to merge), and up to O(n) temporary merge space worst case.
**Insight:** "sorts in place" describes the list's visible state, not what
the algorithm allocates to get there.

**Pitfall:** TimSort's response to an inconsistent comparator is
`java.lang.IllegalArgumentException: Comparison method violates its general
contract!` — from the **sort**, not the list, not the comparator itself, and
only **sometimes**, because detection is a merge-invariant check that trips
depending on that input's run structure, not a check run against every pair
up front. An `a - b` comparator can pass every small-fixture test and throw
for the first time against production data large enough to overflow.

**Stability decides the composition style.** Because TimSort is stable,
`list.sort(comparing(id))` then `list.sort(comparing(postedAt))` produces the
same order as one call to `byPostedThenId` — the second sort never disturbs
id-order among ties. Prefer the single composed comparator: one pass, intent
explicit. Sorting the §14.3 report's `List<LedgerEntry>` with
`entries.sort(byPostedThenId)` places two same-`postedAt` entries in `id`
order deterministically, rather than leaving the tie to TimSort's incidental
handling.

> `Comparator` composes as a chain of delegating `compare` calls that
> short-circuits on the first nonzero result, and `list.sort(c)` runs that
> chain through TimSort directly against the backing array, bracketed by the
> same `modCount` check that guards every other structural mutation.

---

## Q-38 — `List.equals`/`hashCode`, and `ArrayList`'s faster private paths

**Mental model.** `List.equals` is a **shape** check — two lists are equal if
they are the same kind of sequence (same size, same elements, same order),
regardless of which class built either one. `List.hashCode` is the matching
promise that shape-equal lists always hash the same.

**Why it exists.** `Object.equals`/`hashCode` default to identity, useless
for "does this list of items match that list." The framework specifies `List`
to override both structurally so any two conforming implementations are
interchangeable by value.

**When it applies.** Uniformly across every `List` implementation — that
uniformity is the point — but never across kinds: `equals` requires the other
object be a `List`, so `new ArrayList<>(List.of("a")).equals(Set.of("a"))` is
`false` regardless of content.

**How it works — the specified algorithm.** `List.equals(o)` holds iff `o` is
a `List`, sizes match, and every corresponding pair satisfies
`Objects.equals`. That is why **an `ArrayList` can equal a `LinkedList`**
holding the same elements — required by spec, not accident, which is why the
implementation tests `instanceof List`, not `getClass() == ArrayList.class`.
`List.hashCode()` is specified as exactly this loop, starting from `1`:
`hashCode = 31 * hashCode + (e == null ? 0 : e.hashCode())`.

`ArrayList` changes nothing observable, only takes two private fast paths.
Quoted from `ArrayList.java`, lines 598–690:

```java
public boolean equals(Object o) {
    if (o == this) return true;
    if (!(o instanceof List)) return false;
    final int expectedModCount = modCount;
    // ArrayList can be subclassed and given arbitrary behavior, but we can
    // still deal with the common case where o is ArrayList precisely
    boolean equal = (o.getClass() == ArrayList.class)
        ? equalsArrayList((ArrayList<?>) o)
        : equalsRange((List<?>) o, 0, size);
    checkForComodification(expectedModCount);
    return equal;
}

boolean equalsRange(List<?> other, int from, int to) {
    final Object[] es = elementData;
    if (to > es.length) throw new ConcurrentModificationException();
    var oit = other.iterator();
    for (; from < to; from++) {
        if (!oit.hasNext() || !Objects.equals(es[from], oit.next())) return false;
    }
    return !oit.hasNext();
}

private boolean equalsArrayList(ArrayList<?> other) {
    final int otherModCount = other.modCount;
    final int s = size;
    boolean equal;
    if (equal = (s == other.size)) {
        final Object[] otherEs = other.elementData;
        final Object[] es = elementData;
        if (s > es.length || s > otherEs.length) throw new ConcurrentModificationException();
        for (int i = 0; i < s; i++) {
            if (!Objects.equals(es[i], otherEs[i])) { equal = false; break; }
        }
    }
    other.checkForComodification(otherModCount);
    return equal;
}
```

`equalsRange` drives the *other* list's iterator — the general path, works
against any `List`. `equalsArrayList` is taken only when `o.getClass() ==
ArrayList.class` exactly: it indexes **two arrays directly**, `es[i]` against
`otherEs[i]`, skipping both sides' iterator machinery — "`ArrayList` can be
subclassed and given arbitrary behavior, but we can still deal with the
common case where `o` is `ArrayList` precisely," per the source comment.
`hashCode()`/`hashCodeRange` follow the identical shape: snapshot `modCount`,
run the specified `31 * hashCode + (e == null ? 0 : e.hashCode())` loop from
`1`, check `modCount` again — no divergence from spec, only the same
fail-fast wrapping. A `hashCode()` that throws
`ConcurrentModificationException` is genuinely surprising, and lethal for a
`HashMap` key: the map computes `hashCode()` to place and again to look up an
entry, and a CME mid-lookup corrupts what looked like a simple read.
`equalsRange`/`hashCodeRange` also throw CME directly if `to > es.length` —
a concurrent shrink of the backing array caught before it reads past the
live length.

**The more basic hazard beneath the CME: a mutable list as a map key.**
Independent of concurrency, `hashCode()` is a pure function of current
contents. Mutate a `List<LedgerEntry>` used as a `HashMap` key after
insertion, and its hash changes while the bucket it already occupies does
not move — the entry becomes unfindable. Use `List.copyOf(list)` to fix
contents at the point of copy before using a list this way.

**Empty and null cases.** `hashCode()` of an empty list is `1` (the seed,
loop never runs); a `null` element contributes `0`; `equals(null)` is `false`
via the `instanceof List` test alone.

**The element's own contract is what the list's rests on.** A `LedgerEntry`
record gets `equals`/`hashCode` generated from every component; a hand-written
`equals` omitting a field — a `WithdrawalTransaction.equals` comparing `id`
and `amount` but forgetting `state` — silently breaks `contains`, `indexOf`,
`remove(Object)`. Recall file 06's asymmetry: `fastRemove` calls
`o.equals(es[i])` for the caller-supplied `o`, so the **argument's** `equals`
decides the match, not the stored element's.

```java
List<WithdrawalTransaction> asArrayList = new ArrayList<>(List.of(
    new WithdrawalTransaction("wt-1", "acct-9", "250.00"),
    new WithdrawalTransaction("wt-2", "acct-9", "75.00")));
List<WithdrawalTransaction> asLinkedList = new LinkedList<>(asArrayList);

asArrayList.equals(asLinkedList);                                // true
asArrayList.hashCode() == asLinkedList.hashCode();                // true
asArrayList.equals(new HashSet<>(asArrayList));                   // false — not a List
```

**The gotcha.** Expecting `equals` to distinguish an `ArrayList` from a
`LinkedList`, or asserting `!list.getClass().equals(other.getClass())`
implies inequality, is testing `Object.equals`'s identity behavior, which
`List` deliberately does not have.

> `List.equals`/`hashCode` are specified structurally — same size, same
> elements in order, and the `31 * hash + e.hashCode()` accumulation — so any
> two `List` implementations with the same contents are interchangeable by
> value; `ArrayList` only takes a faster private path to the identical
> result when the other side is provably another `ArrayList`.

---

## Pitfalls

### "My comparator works, I tested it"

**Wrong**
```java
Comparator<Integer> byRawSubtraction = (a, b) -> a - b; // passes on small fixtures
```
On data with values near `Integer.MIN_VALUE`/`MAX_VALUE` this throws
`IllegalArgumentException: Comparison method violates its general contract!`
from inside `Arrays.sort`, or silently misorders elements.

**Right**
```java
Comparator<Integer> byCompare = Integer::compare;
```
Never subtracts, so it cannot overflow, and it satisfies antisymmetry for
every representable `int` pair.

**Why people believe it:** small hand-built fixtures never contain a pair
whose difference overflows `int`.

### "`nullsFirst` protects `comparing` from a null key"

**Wrong**
```java
Comparator.nullsFirst(Comparator.comparing(LedgerEntry::postedAt));
```
Still throws `NullPointerException` on a `null` `postedAt` — `nullsFirst`
wraps the *outer* comparator, but the NPE fires inside `comparing`'s key
extraction, before `nullsFirst` gets a value to inspect.

**Right**
```java
Comparator.comparing(LedgerEntry::postedAt,
    Comparator.nullsFirst(Comparator.naturalOrder()));
```
Here `nullsFirst` wraps the comparator applied to the *extracted key*, so it
intercepts the `null` before any `compareTo` call.

**Why people believe it:** both compile and read left-to-right as "null safe,
then compare"; the difference is only in the parenthesis nesting.

## Cheat sheet

| Question | Answer |
|---|---|
| `compareTo` must satisfy | Antisymmetric, transitive, substitutable for ties; NPE on null |
| Must agree with `equals` | Recommended, not required (`BigDecimal` is the counter-example) |
| Uses `compareTo` vs `equals` | `sort(null)`/`TreeSet`/`TreeMap` use `compareTo`; `contains`/`indexOf`/`HashMap` use `equals` |
| `comparing(f).thenComparing(g)` | `f(a).compareTo(f(b))`, delegating to `g` only on a `0` tie |
| `nullsFirst(c)` wraps | A comparator, not a key extractor — apply at the key site |
| `comparingInt`/etc. exist because | Avoid one autobox per `compare` call |
| Never in a comparator | `a - b` — use `Integer.compare`/`Double.compare` |
| `list.sort(c)` runs | `Arrays.sort(elementData, 0, size, c)` — TimSort, on the array itself, bumps `modCount` always |
| TimSort best / worst | O(n) already-sorted / O(n log n); O(n) temp space worst case |
| Broken comparator's failure | `IllegalArgumentException`, from the sort, only sometimes |
| `List.equals`/`hashCode` spec | Same `List`-ness/size/pairwise `Objects.equals`; `1`, then `31*hash + e.hashCode()` |
| `ArrayList`'s fast path | `equalsArrayList` indexes arrays directly when `getClass() == ArrayList.class` |
| Can `equals`/`hashCode` throw CME | Yes — both snapshot and recheck `modCount` |
| Empty list `hashCode()` | `1` |

## Self-test

**Q1.** Two `Money` values, 100 GBP and 100 EUR, use a `compareTo` comparing
only `amount`. What does it report, and why is that wrong?

<details><summary>Answer</summary>

It reports `0` — the `BigDecimal` amounts are equal, currency is never
consulted. Wrong because `Money.equals` (value equality per Appendix C.1)
treats them as unequal, so `compareTo` disagrees with `equals`; worse, it is
comparing two incommensurable quantities as if on the same scale.

</details>

**Q2.** What does `list.sort(c)` pass to `Arrays.sort`, and what does that
imply about the trailing slots beyond `size`?

<details><summary>Answer</summary>

The backing array itself, `(E[]) elementData`, via an unchecked cast, bounded
by `0` and `size`. Only `[0, size)` is reordered or read; trailing `null`
slots from `size` to `elementData.length - 1` are never touched.

</details>

**Q3.** Why does `list.sort(c)` bump `modCount` even though size never
changes?

<details><summary>Answer</summary>

`modCount` tracks structural modification in the fail-fast sense from file
08, and a full reordering invalidates a live iterator's position assumptions
just as thoroughly as an insertion, even though `size()` is unaffected.

</details>

**Q4.** `new ArrayList<>(List.of("a","b")).equals(new LinkedList<>(List.of(
"a","b")))` — true or false, and which spec clause decides it?

<details><summary>Answer</summary>

`true`. `List.equals` requires only that the other object be a `List`
(satisfied via `instanceof List`), sizes match, and every corresponding pair
is `Objects.equals` — it never inspects the concrete class.

</details>

**Q5.** A `List<LedgerEntry>` is used unmodified as a `HashMap` key, then
mutated after insertion. What breaks?

<details><summary>Answer</summary>

The map placed the entry using the hash computed at insertion time; after
mutation the key's live `hashCode()` reflects the new contents while the
map's bucket placement still reflects the old one, so a later lookup with an
equal-by-value key checks the wrong bucket and the entry becomes permanently
unfindable.

</details>

---

**Questions answered:** Q-36, Q-37, Q-38
**Sets up:** Next: how ArrayList composes with the rest of the platform — streams, arrays, generics, and the wire.
**Diagrams included:** D-18
**Target version:** Java 21 LTS
**Lines:** 469
