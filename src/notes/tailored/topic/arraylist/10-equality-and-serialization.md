# ArrayList — 10 Equality and Serialization

**Target version: Java 21.** | [Map](00-map.md)
Assumes: subList and the shared-array views (file 09).
Previous: [09-sublist-and-aliasing.md](09-sublist-and-aliasing.md) · Next: [11-sorting-comparable-and-comparator.md](11-sorting-comparable-and-comparator.md)

## The cross-implementation `List` equality contract

Two `List`s are equal when they have the same size and equal elements in the
same order — full stop, independent of which class implements `List` on
either side. Picture walking both lists in lockstep and asking "same element
here?" at every position; the walk does not care whether either side is
array-backed or a chain of nodes.

The contract exists because `List` is meant to be a genuine abstraction over
"an ordered sequence you can index into." If equality depended on the
concrete class, a caller could never treat `List<E>` as an interface — a
comparison would silently break across a refactor from `ArrayList` to
`LinkedList`, or across an API boundary that hands back `List.of(...)`.
`List` earns this by specifying `equals` itself, rather than leaving each
class to invent its own rule the way an arbitrary user class can. `Set` does
the same for its own members — a `Set` is never equal to a `List` with the
same contents, because they specify different contracts and `Set` never
orders its comparison. This is the mechanism verified directly:

```java
List<String> arr  = new ArrayList<>(List.of("AO-100", "AO-400"));
List<String> link = new LinkedList<>(arr);
List<String> imm  = List.of("AO-100", "AO-400");
```

```
ArrayList.equals(LinkedList) = true ; hash equal = true ; equals(List.of) = true
```

**Insight:** `equals` tests `o instanceof List`, not `o.getClass() ==
getClass()`. That single choice is what makes cross-implementation equality
possible; a `getClass()` check would make it impossible by construction.

The tradeoff: cross-implementation equality is what makes `List` usable as a
real interface type in tests — build the expected value with `List.of(...)`
and compare it against whatever concrete list your code produced. The cost
is that `equals` cannot bail out early on a class mismatch; it must always be
prepared to walk elements, even when the two lists share nothing. **Interview:**
"does `List` equality care about the concrete class?" — no, only size and
element order; that deliberately breaks the usual "don't compare across
unrelated classes" advice because `List` specifies the contract itself.

```java
List<String> ledger = new ArrayList<>(List.of("AO-100", "AO-400"));
Set<String> asSet = new java.util.HashSet<>(ledger);
System.out.println(ledger.equals(asSet)); // false — Set specifies its own contract
```

> Two `List`s are equal exactly when they have the same size and equal
> elements in the same order; the implementing class never matters.

## The `equalsArrayList` fast path, and the `ConcurrentModificationException`

The real source branches on the *exact* runtime class of the argument:

```java
public boolean equals(Object o) {
    if (o == this) {
        return true;
    }
    if (!(o instanceof List)) {
        return false;
    }
    final int expectedModCount = modCount;
    // ArrayList can be subclassed and given arbitrary behavior, but we can
    // still deal with the common case where o is ArrayList precisely
    boolean equal = (o.getClass() == ArrayList.class)
        ? equalsArrayList((ArrayList<?>) o)
        : equalsRange((List<?>) o, 0, size);
    checkForComodification(expectedModCount);
    return equal;
}
```

Picture two branches after the `instanceof List` gate: a fast lane for "the
other side is precisely an `ArrayList`," and a general lane for everything
else, including an `ArrayList` subclass. Before the fast path, every
comparison — even `ArrayList` against `ArrayList` — paid for an `Iterator`
allocation and a virtual `next()` call per element; when both sides are known
plain arrays, you can index both directly instead.

This wins exactly when both sides are `ArrayList`; it loses (falls to the
general path) the moment either side is a subclass, a `LinkedList`, or an
immutable list, because the `o.getClass() == ArrayList.class` test is
exact-class, not `instanceof`-based. The source comment states why directly:
`ArrayList` "can be subclassed and given arbitrary behavior," so a subclass
cannot be trusted to behave like the base class's array-backed storage.

`equalsArrayList` walks two `Object[]` by index with `Objects.equals` per
slot, throwing `ConcurrentModificationException` up front if either array has
shrunk below the recorded size; `equalsRange` walks the other list's
`Iterator` instead. Both paths are O(n) — this is a constant-factor win, not
a complexity win. The array path skips per-element iterator dispatch; that is
the entire saving.

**Insight:** both `equals` and `hashCode` snapshot `modCount` before
comparing and call `checkForComodification` at the end, so **both can throw
`ConcurrentModificationException`.** `equalsRange` and `hashCodeRange` throw
it directly, too, if the range exceeds the live array (`to > es.length`).
Almost nobody expects a query method like `equals` to throw — most engineers
associate CME only with iteration.

```java
List<String> live = new ArrayList<>(List.of("AO-100", "AO-400", "AA-610"));
List<String> snapshot = List.of("AO-100", "AO-400", "AA-610");
// on another thread, mid-comparison: live.add("AA-700")
live.equals(snapshot); // may throw ConcurrentModificationException
```

The JDK does this on purpose: a `boolean` computed against a list that
mutated mid-comparison describes no state that ever actually existed;
failing loudly beats returning that. **Interview:** "can `List.equals`
throw?" — yes, `ConcurrentModificationException`, because it snapshots
`modCount` the same way iteration does.

> `ArrayList.equals` fast-paths an exact `ArrayList` argument by comparing
> backing arrays directly, falls back to an iterator walk otherwise, and can
> throw `ConcurrentModificationException` under concurrent mutation exactly
> like iteration can.

## `hashCode` as the 31-multiplier fold

The mental model is a running fold over the sequence, not a hash of the
array's memory: start at `1`, and for every element multiply the running
total by 31 and add that element's hash (`0` for `null`).

```java
int hashCodeRange(int from, int to) {
    final Object[] es = elementData;
    if (to > es.length) {
        throw new ConcurrentModificationException();
    }
    int hashCode = 1;
    for (int i = from; i < to; i++) {
        Object e = es[i];
        hashCode = 31 * hashCode + (e == null ? 0 : e.hashCode());
    }
    return hashCode;
}
```

This exists because the `List` interface's Javadoc *specifies* this exact
algorithm as the required hash contract — it is not an `ArrayList`-specific
implementation choice. That is precisely why an `ArrayList` and a
`LinkedList` holding the same elements in the same order produce equal hash
codes: both are required to compute the same fold, not merely required to be
internally consistent with their own `equals`.

`31` is an odd prime, which spreads bits well and avoids the loss you get
multiplying by an even number (an even multiplier always zeroes the low bit).
Practically, `31 * x` compiles to `(x << 5) - x`, a shift and a subtract —
a JIT-level detail, not something you write by hand.

The cost: this is O(n) per call and **not cached** on the instance (unlike
`String.hashCode`, which memoizes). Every call rewalks the whole list. The
consequence that bites: using a `List` as a `HashMap` key rehashes it on
every lookup, and a *mutable* list used as a key is a correctness bug, not
just slow — the key's hash changes out from under the map the moment anyone
mutates the list, and the entry becomes unreachable by its own original key.

The escape hatch: key on an immutable list (`List.of(...)`, which computes
the same fold but can never change under you), or better, key on a small
`record` of exactly the fields you actually need to distinguish — cheaper to
hash and impossible to mutate by construction.

> `List.hashCode()` is a specified 31-multiplier fold over element hashes,
> seeded at 1, computed fresh on every call — which is why cross-implementation
> equal lists always hash equal, and why a mutable list is unsafe as a map key.

## The custom serialized form

Picture what actually crosses the wire: not the array, but a **count**
followed by exactly that many **live** elements. `elementData` itself is
`transient` — the default serialization machinery never touches it — and
`ArrayList` supplies its own private `writeObject`/`readObject` hooks to
write and rebuild the list from that count-plus-elements form instead.

Before this design, the obvious approach — serialize the backing array as-is
— would write every reserved-but-unused slot too: a capacity-10 list holding
4 elements would put 10 array slots on the wire, 6 of them `null`, wasting
bytes and exposing the growth strategy (an implementation detail) as part of
the persisted format forever. Custom hooks let the list serialize only what
is semantically there:

```java
private void writeObject(ObjectOutputStream s) throws IOException {
    int expectedModCount = modCount;
    s.defaultWriteObject();
    s.writeInt(size);
    for (int i = 0; i < size; i++) s.writeObject(elementData[i]);
    if (modCount != expectedModCount) throw new ConcurrentModificationException();
}

private void readObject(ObjectInputStream s) throws IOException, ClassNotFoundException {
    s.defaultReadObject();
    s.readInt(); // ignored: a capacity hint from older serial forms
    if (size > 0) {
        SharedSecrets.getJavaObjectInputStreamAccess().checkArray(s, Object[].class, size);
        Object[] elements = new Object[size];
        for (int i = 0; i < size; i++) elements[i] = s.readObject();
        elementData = elements;
    } else {
        elementData = EMPTY_ELEMENTDATA;
    }
}
```

The cost/benefit is explicit: the wire format is smaller and independent of
whatever capacity happened to exist at write time, at the price of two
hand-written methods that must be kept consistent with each other and with
`size`/`elementData` if the class ever changes shape.

Details worth having cold: `serialVersionUID = 8683452581122892189L` is the
compatibility marker for this form. `writeObject` snapshots `modCount` first
and throws `ConcurrentModificationException` if the list changed mid-write —
the same reasoning as `equals`/`hashCode`. **Insight:** `readObject`'s
`checkArray` call is a deserialization-bomb guard — a hostile stream claiming
`size = Integer.MAX_VALUE` cannot force an allocation that large before the
check runs. A deserialized list's capacity equals its size (rebuilt from the
count, no spare slots), so a round trip is an implicit `trimToSize()`. The
hooks carry `@java.io.Serial` (Java 14+), letting the compiler verify the
signatures match what serialization expects.

`clone()`, for contrast in one line: it copies the array but not the
elements, so `a.clone().equals(a)` is `true` while `a.clone() == a` is
`false` — a shallow copy, not a serialization round trip.

**Version trap:** `equals`/`hashCode` are overridden directly on `ArrayList`
in JDK 21 (verified: lines 598 and 662 of `ArrayList.java`), but this was
**not true in JDK 8**, where `ArrayList` had no `equals`/`hashCode` of its
own and inherited `AbstractList`'s iterator-based versions — meaning the
`equalsArrayList` fast path did not exist yet. The verified bracket is
"absent in JDK 8, present in JDK 11 and later"; the exact minor version
between 9 and 11 was not separately confirmed. File 14 carries the full
version table.

> `ArrayList` serializes as an element count followed by only the live
> elements — never the backing array — because `elementData` is `transient`
> and `writeObject`/`readObject` rebuild the list from that compact form.

## Example: reconciling a day's ledger

`LedgerEntry` is a record (`id`, `movementId`, `position`, `direction`,
`amount`, `postedAt`), so its `equals` is compiler-generated and
field-by-field — exactly the value semantics list equality needs. Comparing
a rebuilt day's entries against the rail's own reconstruction exercises the
cross-implementation contract directly:

```java
List<LedgerEntry> fromOurLedger = rebuildFromLedger(businessDate);
List<LedgerEntry> fromRail = new LinkedList<>(railApi.fetchEntries(businessDate));
boolean reconciled = fromOurLedger.equals(fromRail); // true if same entries, same order
```

`Money` is never floating point, so this generated equality is exact — no
epsilon comparison hiding a mismatch, and exactly why records were chosen for
the domain's value types. A `Movement`'s 2-to-4 `entries` is the natural
serialization example: writing 10 array slots for 4 entries would be pure
waste, which is exactly what the transient-plus-custom-hooks design prevents.

## Pitfalls

### Assuming `ArrayList` can only equal another `ArrayList`

**Wrong** `if (arr.getClass() != other.getClass()) { /* skip comparison */ }`

**Right** `List.equals` compares by size and element order regardless of
implementing class; `arr.equals(List.of("AO-100"))` is `true`. Never gate a
`List` comparison on `getClass()`.

**Why people believe it:** most user-defined `equals` methods *do* check
`getClass()` as idiomatic style, so it feels natural to expect the JDK's own
collections to follow the same rule.

### Using a mutable `List` as a `HashMap` key

**Wrong**
```java
List<String> key = new ArrayList<>(List.of("AO-100", "AO-400"));
map.put(key, "cached-result");
key.add("AA-610");
map.get(key); // often null — the bucket no longer matches the new hash
```

**Right** Key on an immutable list (`List.copyOf(key)`) or a purpose-built
record, so the hash at insertion can never drift from the hash at lookup.

**Why people believe it:** `HashMap` never rejects the mutable key at
`put`-time; the bug is silent until the key mutates, far from the failure.

### Assuming `equals` cannot throw

**Wrong** `if (expected.equals(actual))` inside a loop while another thread
concurrently mutates `actual` — fails intermittently with
`ConcurrentModificationException` instead of `true`/`false`.

**Right** Treat `List.equals` like iteration: safe only when nothing else
can mutate either list mid-call. Synchronize or snapshot first.

**Why people believe it:** `equals` reads like a pure query method by
convention; nothing in `Object.equals`'s signature hints it might throw.

### Assuming serialization preserves capacity

**Wrong** Assuming a deserialized `new ArrayList<>(1000)` that held 1
element still has capacity 1000.

**Right** The serialized form only encodes the live count; capacity after a
round trip always equals size — an implicit `trimToSize()`.

**Why people believe it:** capacity feels like object state, and nothing in
the API signals it is deliberately dropped.

### Assuming `clone()` deep-copies

**Wrong** Mutating an element reached through `a.clone()` and expecting `a`
to be unaffected.

**Right** `clone()` copies the array, not the elements — a shallow copy,
sharing references. Records make this safe by being immutable; a mutable
element type would not be.

**Why people believe it:** "clone" reads as "independent copy" in everyday
language; the shallow/deep distinction is invisible at the call site.

## Cheat sheet

| Question | Answer |
|---|---|
| Does `ArrayList.equals(LinkedList)` work? | Yes — cross-implementation, by contract |
| What test picks the fast path? | `o.getClass() == ArrayList.class` (exact, not `instanceof`) |
| Does a subclass get the fast path? | No — falls to `equalsRange`'s iterator walk |
| Can `equals`/`hashCode` throw? | Yes, `ConcurrentModificationException`, via `checkForComodification` |
| `hashCode` formula | `hashCode = 31 * hashCode + (e==null?0:e.hashCode())`, seeded at 1 |
| Is `hashCode` cached? | No — recomputed on every call, O(n) |
| Safe as a `HashMap` key? | Only if immutable |
| What is `transient` on `ArrayList`? | `elementData` (the backing array) |
| What goes on the wire? | Element count, then only the live elements |
| Guard against a hostile size claim? | `checkArray` before allocating in `readObject` |
| Capacity after deserialize? | Equals size — implicit `trimToSize()` |
| `clone()` depth | Shallow — new array, shared element references |
| First introduced (`equals`/`hashCode` override) | Absent JDK 8, present JDK 11+ |

## Self-test

**Q1.** Why can `ArrayList.equals(someLinkedList)` return `true`?

<details><summary>Answer</summary>

Because `List.equals` is specified by the `List` interface itself to compare
by size and element order, independent of implementing class. `ArrayList`'s
override tests `o instanceof List`, not a class match, so any `List` — a
`LinkedList`, an immutable `List.of(...)`, another `ArrayList` — is eligible.

</details>

**Q2.** What exact condition selects `equalsArrayList` over `equalsRange`, and what does an `ArrayList` subclass get?

<details><summary>Answer</summary>

`o.getClass() == ArrayList.class` — an exact class match, not `instanceof
ArrayList`. A subclass of `ArrayList` fails this test and falls through to
`equalsRange`, which walks the other list's `Iterator` instead of comparing
backing arrays directly. The source comment explains this is because a
subclass "can be subclassed and given arbitrary behavior," so the array-based
shortcut cannot be trusted for it.

</details>

**Q3.** Under what circumstance can `list.equals(other)` throw an exception, and why does the JDK let it?

<details><summary>Answer</summary>

If either list is structurally mutated by another thread while the
comparison runs, `checkForComodification` detects the `modCount` mismatch
(or `equalsRange`/`hashCodeRange` detect a size/array-length mismatch
directly) and throws `ConcurrentModificationException`. The JDK accepts this
because a `boolean` computed against a list that changed mid-comparison
would describe a state that never coherently existed; failing loudly is
preferred to returning a meaningless answer.

</details>

**Q4.** Why do `ArrayList` and `LinkedList` with identical contents always produce equal hash codes?

<details><summary>Answer</summary>

Because `hashCode` for `List` is not an implementation's free choice — the
`List` contract specifies the exact 31-multiplier fold algorithm
(`hashCode = 31*hashCode + (e==null?0:e.hashCode())`, seeded at 1). Every
correct `List` implementation must compute this same fold, so any two lists
that are `equals` are also guaranteed `hashCode`-equal.

</details>

**Q5.** Why is a mutable `ArrayList` a bad `HashMap` key even if nothing throws?

<details><summary>Answer</summary>

`hashCode()` is recomputed fresh on every call and is never cached, so the
map computes the key's hash at `put` time and again at `get` time. If the
list is mutated between those two calls, the hash changes, the entry lands
in a different bucket than the map expects to search, and lookups
effectively lose the entry — silently, with no exception.

</details>

**Q6.** What exactly gets written when an `ArrayList` is serialized, why not the raw array, and what guards `readObject` against a hostile size?

<details><summary>Answer</summary>

The element count (`size`), then exactly that many live elements read
directly out of `elementData` — never the array itself, since capacity is
usually larger than `size` and serializing it would leak unused, mostly-null
slots into the format. Before allocating, `readObject` calls
`SharedSecrets.getJavaObjectInputStreamAccess().checkArray(s, Object[].class, size)`,
which stops a crafted stream from forcing a huge allocation purely from an
untrusted size value. One consequence: a deserialized list's capacity always
equals its size — a round trip is an implicit `trimToSize()`.

</details>

---

**Questions answered:** Q-22, Q-23
**Sets up:** Next: ordering — the backbone concepts sorting depends on, taught in place.
**Diagrams included:** none
**Target version:** Java 21
**Lines:** 435
