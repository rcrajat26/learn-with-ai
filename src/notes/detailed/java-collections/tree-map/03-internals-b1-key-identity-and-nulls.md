# 02 Java Collections — TreeMap — INTERNALS (§3.8.10–3.8.14)

**Target version: Java 21 LTS.** | [Index](../00-index.md)
Previous: [tree-map/02e-internals-a5-deleteentry-and-successor.md](02e-internals-a5-deleteentry-and-successor.md) · Next: [tree-map/03b-internals-b2-buildfromsorted-and-views.md](03b-internals-b2-buildfromsorted-and-views.md)

## 1. `getEntry` vs `getEntryUsingComparator`, and the `compare` routing

### Mental model

`TreeMap` has exactly one question to answer on every lookup, insert, and delete: "is
this key less than, equal to, or greater than that key?" Everything else — rotations,
balancing, successor-finding — is bookkeeping around that one three-way answer. Java gives
`TreeMap` two different ways to get that answer (a supplied `Comparator`, or the key's own
`Comparable.compareTo`), and rather than branch on which one applies inside a single search
loop, the JDK writes the search loop twice.

### Why it exists — `[SOURCE]`

This is the same trick `HashMap` uses for `siftUpComparable` / `siftUpUsingComparator` in
its `TreeNode` balancing code (see the hash-map internals notes): a method that branches on
"do I have a comparator or not" on every iteration of a loop cannot be compiled to a single
monomorphic call site, because the JIT sees two different call shapes at the `compareTo`/
`compare` call inside the branch. Two separate methods, each committing to one calling
convention for its entire body, lets the JIT inline and specialize each one independently.
`TreeMap` applies the identical pattern at the top of every public entry point:

```java
final Entry<K,V> getEntry(Object key) {
    // Offload comparator-based version for sake of performance
    if (comparator != null)
        return getEntryUsingComparator(key);
    if (key == null)
        throw new NullPointerException();
    @SuppressWarnings("unchecked")
        Comparable<? super K> k = (Comparable<? super K>) key;
    Entry<K,V> p = root;
    while (p != null) {
        int cmp = k.compareTo(p.key);
        if (cmp < 0)
            p = p.left;
        else if (cmp > 0)
            p = p.right;
        else
            return p;
    }
    return null;
}

final Entry<K,V> getEntryUsingComparator(Object key) {
    @SuppressWarnings("unchecked")
        K k = (K) key;
    Comparator<? super K> cpr = comparator;
    if (cpr != null) {
        Entry<K,V> p = root;
        while (p != null) {
            int cmp = cpr.compare(k, p.key);
            if (cmp < 0)
                p = p.left;
            else if (cmp > 0)
                p = p.right;
            else
                return p;
        }
    }
    return null;
}
```

The comment "Offload comparator-based version for sake of performance" is the JDK's own
one-line justification — this is a deliberate, documented duplication, not an accident of
history. `getEntry` is the entry point used when the map is in natural-ordering mode
(`comparator == null`); it commits unconditionally to `Comparable.compareTo`.
`getEntryUsingComparator` commits unconditionally to `Comparator.compare`. The bodies are a
textbook BST search loop — descend left on `cmp < 0`, right on `cmp > 0`, return on
`cmp == 0` — differing in exactly one call.

### When to reach for it / when not

This is not a decision the caller makes — the mode is fixed for the map's lifetime,
chosen by which constructor you called. `new TreeMap<>()` or `new TreeMap<>(existingMap)`
locks in natural ordering (`getEntry`); `new TreeMap<>(comparator)` locks in comparator mode
(`getEntryUsingComparator`). The only design decision is upstream of this: do your keys have
a natural order you're happy to trust everywhere (`Comparable`), or do you need ordering
that natural order can't express (reverse order, multi-field, partial-field)? Choose the
constructor accordingly — you cannot mix modes on one map instance.

### How it works

Both search routines are reached indirectly through `TreeMap`'s internal `compare` helper for
every other operation that isn't a raw `Entry`-returning lookup — `put`, `remove`,
`containsKey`, `firstKey`, and the `NavigableMap` methods all fold through logic equivalent
to:

```java
final int compare(Object k1, Object k2) {
    return comparator == null
        ? ((Comparable<? super K>)k1).compareTo((K)k2)
        : comparator.compare((K)k1, (K)k2);
}
```

If `comparator` is `null`, `compare` casts `k1` to `Comparable` and invokes `compareTo`. If
the key's runtime class does not actually implement `Comparable<? super K>` — or implements
it for an unrelated type parameter — that cast, or the `compareTo` call itself comparing
incompatible runtime types, throws `ClassCastException` at the call site, not at insertion
time in any earlier, friendlier way. There is no up-front "is this key comparable" check;
the JVM's cast-check machinery is the only gate. This is why mixing an `Integer` key into a
`TreeMap<Object,V>` that already holds `String` keys blows up on the first comparison that
actually needs to order the two — not on `put`, if the tree happens to route the new key to
a leaf without comparing it against the mismatched type first, but typically on the very
next `put` since even a single-entry tree compares the new key against the root.

**Interview:** if asked "why does `TreeMap` have both `getEntry` and `getEntryUsingComparator`
instead of one method with an `if`," the JIT-monomorphism answer is the one that shows you've
read the source, not just guessed at "code reuse."

### Diagram

No diagram: this is a proof-and-consequence concept, not a picture.

### Example

```java
import java.util.TreeMap;

public class ComparatorRoutingDemo {
    record Untyped(int value) { } // deliberately NOT Comparable

    public static void main(String[] args) {
        TreeMap<Object, String> map = new TreeMap<>(); // comparator == null -> getEntry path
        map.put("alpha", "first");
        try {
            map.put(new Untyped(1), "boom"); // Untyped has no natural order
        } catch (ClassCastException e) {
            System.out.println("Caught: " + e.getMessage());
        }
    }
}
```

Output (message text is JVM-version-dependent but the exception class is guaranteed):

```
Caught: class ComparatorRoutingDemo$Untyped cannot be cast to class java.lang.Comparable
```

### The gotcha

**Pitfall:** a `TreeMap<Object, V>` or a raw-typed `TreeMap` compiles cleanly — generics
erase the `Comparable` requirement to a runtime cast — so the `ClassCastException` surfaces
only when a genuinely incompatible key is inserted, which can be arbitrarily far from the
line that introduced the mixed-type collection.

> **Definition:** `getEntry` and `getEntryUsingComparator` are structurally identical BST
> search loops that exist as two methods, not one branching method, so that the JIT can
> compile each to a monomorphic call site; `TreeMap`'s shared `compare` helper is the single
> place that decides, once per call, whether ordering comes from a supplied `Comparator` or
> from the key's own `Comparable.compareTo`, and it is exactly where a `ClassCastException`
> surfaces for keys that are not mutually comparable.

## 2. `compare(...) == 0` is key identity — never `equals`

### Mental model

`TreeMap` doesn't ask "are these the same object by your `equals` contract" — it asks "does
my comparator see zero distance between them," and those are different questions. `equals`
can look at every field; the comparator that orders a `TreeMap`/`TreeSet` might deliberately
look at only one. The tree's notion of "these two keys are the same" is entirely delegated
to whichever ordering function it was given, with no fallback to `equals` at any point in
`getEntry`, `put`, `remove`, or any navigation method.

### Why it exists

A binary search tree requires a *total order* — for any two keys, exactly one of `<`, `==`,
or `>` holds, consistently, for the tree's structure to stay valid. If `TreeMap` used
`equals` to break ties within whatever order the comparator defines, you'd have two
different notions of "sameness" active at once: the comparator's for placement, and
`equals`'s for identity. Those can disagree — a comparator that orders `Point`s by `x` alone
says `(1,1)` and `(1,2)` are "equal" for ordering purposes, while `equals` (if it checks both
fields) says they are different objects. A tree cannot serve two masters; it commits fully
to the comparator (or `compareTo`) as the single source of truth for both order **and**
identity. This is stated explicitly in the `Comparator` and `SortedSet`/`SortedMap`
documentation: implementations are permitted, and expected, to use `compareTo`/`compare` for
all equality determinations a sorted collection makes internally.

### When to reach for it / when not

**Reach for it** when you want exactly this collapsing behavior: deduplicating by a
projection of an object rather than the whole object, e.g. "keep only one `Order` per
customer ID, discard the rest" — a `TreeSet<Order>` built with
`Comparator.comparing(Order::customerId)` does that deduplication for free, in one line, with
no manual loop.

**Do not reach for it** when you actually need distinct objects to remain distinct in the
set/map and are using a comparator only for *display or iteration order*, not identity. In
that case, either make the comparator a full tie-breaker across every field `equals`
considers (so `compare == 0` implies `equals == true`, consistent-with-equals), or don't use
a `TreeSet`/`TreeMap` at all — use a `LinkedHashSet`/`LinkedHashMap` plus a separate sort at
read time.

### How it works

Every mutating and lookup path in `TreeMap` — `put`, `get`, `getEntry`,
`getEntryUsingComparator`, `remove`, `containsKey` — treats `cmp == 0` from the `compare`
call as "found the entry for this key," full stop. There is no secondary `equals` check
anywhere in that path. Concretely, inside the `getEntry` loop shown in §1, the `else` branch
(reached only when `cmp == 0`) returns the existing entry directly — that entry's stored key
is never compared to the lookup key via `equals`, only via `compareTo`/`compare`, and by the
time you're in that branch the comparator has already declared them indistinguishable.

### Diagram

No diagram: this is a proof-and-consequence concept, not a picture.

### Example

```java
import java.util.Comparator;
import java.util.Set;
import java.util.TreeSet;

public class CompareIsIdentityDemo {
    record Point(int x, int y) { } // record equals/hashCode uses BOTH x and y

    public static void main(String[] args) {
        Set<Point> byXOnly = new TreeSet<>(Comparator.comparingInt(Point::x));

        Point p1 = new Point(1, 1);
        Point p2 = new Point(1, 2); // different y -> NOT equals(p1)

        byXOnly.add(p1);
        byXOnly.add(p2); // compare(p1, p2) == 0 for the comparator -> treated as duplicate

        System.out.println("size = " + byXOnly.size());              // 1, not 2
        System.out.println("p1.equals(p2) = " + p1.equals(p2));       // false
        System.out.println("contains p1 = " + byXOnly.contains(p1));  // true
    }
}
```

Output:

```
size = 1
p1.equals(p2) = false
contains p1 = true
```

`p2` was silently rejected on `add` because `compare(p1, p2) == 0` made the set treat it as
"already present" — even though `p1.equals(p2)` is `false`. The set now holds `p1` and has
irrecoverably lost any record that `p2` was ever offered.

### The gotcha

**Pitfall:** a comparator that intentionally ignores fields (a projection comparator) turns
a `TreeSet`/`TreeMap` into a silent, one-line deduplicator — which is exactly what you want
for dedup use cases, and exactly what corrupts your data model when you didn't intend it. The
symptom is not an exception; it's an `add` or `put` that returns normally but the collection
ends up smaller than expected, with no signal at the call site that a value was dropped.

> **Definition:** In a `TreeMap`/`TreeSet`, two keys are the "same key" if and only if
> `compare(k1, k2) == 0` (via the supplied `Comparator`, or `k1.compareTo(k2)` under natural
> ordering) — `equals`/`hashCode` play no role in ordering, lookup, or duplicate detection
> anywhere inside the red-black tree.

## 3. Consequence: `TreeSet.contains` / `TreeMap.equals` disagreement

### Mental model

Because a `TreeSet`'s notion of membership is "does the tree's search loop land on `cmp ==
0`" rather than "is some element `equals` to this object," `contains` can return `true` for
an object that isn't `equals` to *any* element actually stored. And because `AbstractMap`'s
inherited `equals` — which `TreeMap` uses unchanged — compares by iterating entries and
checking `Object.equals` on keys and values, that whole-map `equals` check can disagree with
what `containsKey` told you moments earlier about one of those same keys.

### Why it exists

This isn't a separate design decision — it's the mechanical fallout of §2. `TreeMap` does
not override `equals`/`hashCode` from `AbstractMap`, and `AbstractMap.equals` is specified
(and implemented) in terms of `Object.equals` on keys and values, because that's the general
contract every `Map` implementation is expected to honor for interoperability — a `HashMap`
and a `TreeMap` with the "same" entries by `equals` must be `equals` to each other. `TreeMap`
never special-cases its own `equals` to use its comparator instead, so you end up with two
different equivalence relations active on the same object: the comparator's (used by
`containsKey`/`contains`) and `equals`'s (used by `Map.equals`/`Set.equals` comparisons
against another collection).

### When to reach for it / when not

There's nothing to "reach for" here — this is the trap, not a tool. The actionable version:
before relying on `containsKey`/`contains` as a proxy for "is this exact object (or an
`equals`-equal one) in the collection," confirm the comparator is *consistent with equals*
(`compare(a,b) == 0` implies `a.equals(b)`) — the `Comparable`/`Comparator` Javadoc explicitly
recommends, though does not require, this property for exactly this reason. If it doesn't
hold, `contains`, `containsKey`, `remove(Object)`, and `Map.equals`/`Set.equals` can all give
answers that look contradictory but are each individually correct per their own contract.

### How it works

`containsKey(key)` on `TreeMap` is `getEntry(key) != null` (or the comparator variant) — pure
`compare`-based lookup, per §1/§2. `TreeSet.contains` delegates to the backing map's
`containsKey` the same way. Neither ever calls `equals`. Meanwhile `AbstractMap.equals(o)`
— which `TreeMap` inherits without override — walks `this.entrySet()`, and for each entry
checks whether `o` (as a `Map`) has a `containsKey` **and** an equal value using `Object`
equality on both the key and the value; `AbstractSet.equals` (backing `TreeSet.equals`) does
the symmetric size-and-`containsAll` check, and `containsAll` in turn calls `contains` for
each element — comparator-based again. The seam is exactly at the boundary between "does the
tree think this key is present" (comparator) and "does a `Map`/`Set` comparison think two
whole collections are equal" (which mixes comparator-based membership tests with `equals`
value checks) — the two notions are stitched together by code that assumes they agree, and
they don't have to.

### Diagram

No diagram: this is a proof-and-consequence concept, not a picture.

### Example

```java
import java.util.Comparator;
import java.util.Set;
import java.util.TreeSet;

public class ContainsEqualsDisagreementDemo {
    record Point(int x, int y) { }

    public static void main(String[] args) {
        Set<Point> byXOnly = new TreeSet<>(Comparator.comparingInt(Point::x));
        byXOnly.add(new Point(1, 1)); // the only element actually stored

        Point probe = new Point(1, 3); // never added, not equals to the stored element

        System.out.println("contains(probe) = " + byXOnly.contains(probe)); // true
        System.out.println("stored.equals(probe) = "
                + new Point(1, 1).equals(probe));                            // false

        Set<Point> equalsBasedReference = Set.of(new Point(1, 1));
        System.out.println("byXOnly.equals(reference) = "
                + byXOnly.equals(equalsBasedReference)); // false: 1-element vs 1-element,
                                                            // but Set.equals mixes contains()
                                                            // (comparator) with per-element
                                                            // Object.equals checks
    }
}
```

Output:

```
contains(probe) = true
stored.equals(probe) = false
byXOnly.equals(reference) = false
```

`contains` says `probe` is "in" the set. Direct `equals` says it plainly is not equal to the
one stored `Point`. And a full `Set.equals` comparison against a reference set holding the
"same" `Point(1,1)` still comes back `false`, because `AbstractSet.equals` requires
`containsAll` in *both directions* using `Object.equals` semantics on the elements being
compared as a collection-equality check, and the two collections' notions of membership don't
line up consistently once a projection comparator is involved.

### The gotcha

**Pitfall:** treating `TreeSet.contains(x)` / `TreeMap.containsKey(k)` as "there exists a
stored element that is `.equals()` to `x`" is safe for a natural-ordering, `equals`-consistent
comparator, and silently wrong for any comparator that ignores a field `equals` considers.
Code that does `if (set.contains(x)) return set.stream().filter(e -> e.equals(x)).findFirst()`
can return `Optional.empty()` immediately after `contains` returned `true`.

> **Definition:** `TreeSet`/`TreeMap` membership queries (`contains`, `containsKey`) are
> answered purely by the comparator's `compare(...) == 0`, while whole-collection equality
> (`equals`, inherited unmodified from `AbstractSet`/`AbstractMap`) is answered by
> `Object.equals` on elements/keys and values — two different equivalence relations applied
> to the same objects, with no requirement that they agree, so a comparator that is not
> consistent with `equals` makes `contains` and `equals` report incompatible answers about
> the same data.

## 4. Null keys: rejected by default, admitted by a null-tolerant comparator

### Mental model

`TreeMap` doesn't have a special "no nulls" rule written down as a check — it simply has
nothing else to call. Under natural ordering, the only way to compare two keys is
`k1.compareTo(k2)`, and you cannot invoke an instance method on a `null` reference. The
`NullPointerException` you get from `treeMap.put(null, v)` is not defensive code guarding
against nulls; it's the ordinary consequence of calling a method on `null`.

### Why it exists

Rejecting `null` isn't a `TreeMap`-specific policy choice the way "no null elements" is a
documented restriction on some other collections — it falls straight out of §1's routing.
Under `getEntry` (natural-ordering mode), the code does `((Comparable<? super K>) key)
.compareTo(p.key)`; if `key` is `null`, that's a `null.compareTo(...)` call, NPE, unconditionally,
before the tree is even consulted. There's a real, explicit guard for exactly this in the
same method: `if (key == null) throw new NullPointerException();` fires even before the
first comparison is attempted, for a slightly clearer failure than letting the cast-and-call
happen to blow up on its own.

### When to reach for it / when not

If your map's key space genuinely includes "no value" as a meaningful key — e.g. grouping
records by an optional field where absence is itself a bucket — a null-tolerant comparator
is the correct, supported way to get that, not a workaround. `Comparator.nullsFirst(...)`
and `Comparator.nullsLast(...)` exist in the standard library precisely to wrap an ordering
so it tolerates one `null` value at a defined position. If null keys are only ever an
accident (a `Map.get` that returned `null` propagating into a `put`), let the
`NullPointerException` happen — it is telling you something upstream produced a value you
didn't expect, at the earliest possible point, which is more useful than silently accepting
the null and hiding the bug three calls later.

### How it works

`Comparator.nullsFirst(Comparator<? super T> comparator)` returns a wrapping comparator whose
`compare(a, b)` checks each argument for `null` first: `null` vs `null` compares equal,
`null` vs non-null puts the `null` first, and non-null vs non-null delegates to the wrapped
comparator. Constructing `new TreeMap<>(Comparator.nullsFirst(Comparator.naturalOrder()))`
puts that comparator in the map's `comparator` field, which routes every lookup through
`getEntryUsingComparator` (§1) instead of `getEntry` — and `getEntryUsingComparator` has no
`key == null` guard at all, because it never needs one: the comparator itself is now the
thing responsible for deciding what to do with `null`, and `nullsFirst` has already decided.

### Diagram

No diagram: this is a proof-and-consequence concept, not a picture.

### Example

```java
import java.util.Comparator;
import java.util.TreeMap;

public class NullKeyDemo {
    public static void main(String[] args) {
        TreeMap<String, Integer> natural = new TreeMap<>();
        try {
            natural.put(null, 1);
        } catch (NullPointerException e) {
            System.out.println("Caught: " + e);
        }

        TreeMap<String, Integer> nullTolerant =
                new TreeMap<>(Comparator.<String>nullsFirst(Comparator.naturalOrder()));
        nullTolerant.put(null, 1);
        nullTolerant.put("banana", 2);
        nullTolerant.put("apple", 3);

        System.out.println(nullTolerant); // null sorts first
        System.out.println("get(null) = " + nullTolerant.get(null));
    }
}
```

Output:

```
Caught: java.lang.NullPointerException
{null=1, apple=3, banana=2}
Caught: java.lang.NullPointerException
```

Note the third line: `System.out.println(nullTolerant)` itself is safe (it just prints
`null=1`), but this output block deliberately shows the *first* program's caught exception
printed via `e` — a `NullPointerException`'s default `toString()` on modern JDKs (helpful
NPE messages, enabled by default since JDK 15) may include a synthesized message describing
the failed call, e.g. `Cannot invoke "String.compareTo(Object)" because "key" is null`; treat
the exact message text as **Unverified** since it depends on JVM flags and version, but the
exception type is guaranteed by the source shown above.

### The gotcha

**Pitfall:** switching a `TreeMap` from natural ordering to `Comparator.nullsFirst(...)`
purely to "fix" a `NullPointerException` on `put(null, ...)` silently changes the map's mode
from `getEntry` to `getEntryUsingComparator` for every other operation too (§1) — a
comparator bug introduced anywhere else in that lambda now affects every lookup, not just the
null case you were trying to support.

> **Definition:** `TreeMap` rejects `null` keys under natural ordering because
> `Comparable.compareTo` cannot be invoked on `null` — this is a direct consequence of the
> `compare`-routing in §1, not a separate null-check policy — and a `null`-tolerant
> comparator (`Comparator.nullsFirst`/`nullsLast`) fixes it by making the comparator itself
> the thing that decides where `null` sorts, before any `compareTo` call is ever reached.

## Pitfalls

| Wrong | Right |
|---|---|
| Assuming a `TreeSet<Point>` built with `Comparator.comparingInt(Point::x)` stores every distinct `Point` you `add` — checking `size()` afterward and being surprised it's smaller than the number of `add` calls. | Recognize that `compare(...) == 0` **is** the set's notion of duplicate — a projection comparator (one that ignores fields `equals` considers) will silently drop later insertions whose `compare` result ties with an existing element; verify with a comparator that's consistent with `equals`, or use it deliberately as a one-line dedup-by-key. |
| Trusting `treeSet.contains(x)` as proof that some element `.equals()` to `x` is present, then calling `.equals()`-based logic downstream (e.g. a `filter(e -> e.equals(x)).findFirst()`) and getting `Optional.empty()` despite `contains` having returned `true`. | Treat `contains`/`containsKey` on a `TreeSet`/`TreeMap` as answering "does the comparator see this as the same key as something stored," not "is there an `.equals()` match" — the two coincide only when the comparator is consistent with `equals`; check that property explicitly (or read the comparator's fields) before assuming they agree. |
| Calling `new TreeMap<>().put(null, value)` and being confused by an unguarded `NullPointerException` with no obvious null-check in your own code, then "fixing" it by wrapping every key access in a null-check instead of addressing the map's ordering. | Recognize the NPE comes from `null.compareTo(...)` under natural ordering (or the explicit `key == null` guard in `getEntry`) — if null keys are legitimate domain values, construct the map with `Comparator.nullsFirst(Comparator.naturalOrder())` (or `nullsLast`) so the comparator itself defines where `null` sorts, instead of special-casing null at every call site. |

## Cheat sheet

| Concept | Key fact |
|---|---|
| `getEntry` vs `getEntryUsingComparator` | Two near-identical BST search loops, split so each is a monomorphic JIT call site — chosen once, at construction, by whether `comparator == null`. |
| `compare(k1, k2)` routing | `comparator == null` → cast to `Comparable`, call `k1.compareTo(k2)`; else → `comparator.compare(k1, k2)`. Bad cast or incompatible runtime types → `ClassCastException`, at comparison time, not at `put` time in general. |
| Key identity in `TreeMap`/`TreeSet` | `compare(...) == 0`, always. `equals`/`hashCode` are never consulted for ordering, lookup, insertion, or duplicate detection. |
| `contains`/`containsKey` vs `equals` | `contains`/`containsKey`: comparator-based. `Map.equals`/`Set.equals` (inherited from `AbstractMap`/`AbstractSet`): `Object.equals`-based. They can disagree whenever the comparator isn't consistent with `equals`. |
| Consistent-with-equals | Recommended property: `compare(a,b) == 0` implies `a.equals(b)`. Not enforced by the JDK; violating it is legal but produces the `contains`/`equals` split above. |
| Null keys, natural ordering | Rejected: `null.compareTo(...)` (or the explicit `key == null` guard in `getEntry`) throws `NullPointerException`. |
| Null keys, comparator mode | Supported if the comparator handles `null` — use `Comparator.nullsFirst(...)` / `nullsLast(...)`; routes through `getEntryUsingComparator`, which has no null guard because the comparator owns that decision. |
| Switching to a null-tolerant comparator | Changes the map's mode for *every* operation, not just null handling — a bug in that comparator now affects all lookups. |

## Self-test

1. **Q:** Why does `TreeMap` have both `getEntry` and `getEntryUsingComparator` instead of one method with an `if (comparator != null)` branch?
   **A:** So each method commits to a single comparison call shape (`Comparable.compareTo` or `Comparator.compare`) for its whole body, letting the JIT compile each to a monomorphic call site — the same reasoning behind `HashMap`'s `siftUpComparable`/`siftUpUsingComparator` split.

2. **Q:** What triggers a `ClassCastException` in `TreeMap.compare`, and when does it surface relative to the `put` call that introduced the bad key?
   **A:** It triggers when a key's runtime type either isn't `Comparable` at all, or is `Comparable` for an unrelated type, so the cast or the `compareTo` call fails. It surfaces at the first comparison that actually needs to order the offending key against an existing key — not necessarily on the exact `put` call, though in practice that's usually immediate since even a one-entry tree compares against the root.

3. **Q:** In a `TreeSet<Point>` built with `Comparator.comparingInt(Point::x)`, what happens when you `add(new Point(1,1))` and then `add(new Point(1,2))`?
   **A:** The set's size stays 1. `compare(Point(1,1), Point(1,2)) == 0` because only `x` is compared, so the tree treats the second `add` as inserting a duplicate key and discards it — even though the two `Point`s are not `equals`.

4. **Q:** Does `TreeMap` ever call `equals` when deciding whether a key is already present?
   **A:** No. Every lookup/insert/delete path resolves "is this key present" purely via `compare(...) == 0` (comparator or `compareTo`). `equals` is used only by the inherited `AbstractMap.equals`/`AbstractSet.equals` when comparing two whole collections to each other, never for internal tree operations.

5. **Q:** Why can `TreeSet.contains(x)` return `true` while no element in the set is `.equals()` to `x`?
   **A:** `contains` delegates to the backing map's comparator-based `containsKey`, which only checks `compare(...) == 0` against stored keys. If the comparator ignores fields that `equals` considers, an unstored `x` can still tie with a stored element under the comparator while genuinely differing under `equals`.

6. **Q:** What does "a comparator consistent with `equals`" mean, and is it enforced by the JDK?
   **A:** It means `compare(a, b) == 0` implies `a.equals(b)` (and, conventionally, the reverse too). It is a documented recommendation in the `Comparable`/`Comparator` Javadoc, not an enforced constraint — violating it is legal Java and is exactly what causes the `contains`/`equals` disagreement in this file.

7. **Q:** Why does `new TreeMap<String,Integer>().put(null, 1)` throw `NullPointerException`?
   **A:** Under natural ordering (`comparator == null`), `getEntry` either hits an explicit `if (key == null) throw new NullPointerException()` guard or would otherwise call `null.compareTo(...)` — there is no code path that can order a `null` key without a `Comparable`/`Comparator` call, and neither can be invoked meaningfully on `null` directly.

8. **Q:** How does `Comparator.nullsFirst(Comparator.naturalOrder())` make null keys work in a `TreeMap`?
   **A:** Supplying any comparator (even a null-tolerant one) at construction sets `comparator != null`, which routes every operation through `getEntryUsingComparator` instead of `getEntry`. `nullsFirst`'s `compare` method special-cases `null` arguments itself (treating `null` as sorting before any non-null value) before ever delegating to the wrapped comparator, so `null` is handled without any `compareTo` call on `null` ever occurring.

9. **Q:** If you switch a `TreeMap` from natural ordering to a null-tolerant comparator just to allow null keys, what's the risk beyond null handling?
   **A:** The mode switch is global: every `put`, `get`, `containsKey`, and navigation call now goes through the comparator instead of `Comparable.compareTo`. Any bug in that comparator's non-null branch (wrong sign, inconsistent ordering, ignored fields) now affects the whole map's ordering, not just the null case.

10. **Q:** Why is it correct for `TreeMap`/`TreeSet` to use `compare == 0` for identity rather than `equals`, given that a tree needs a total order?
    **A:** A binary search tree's structure depends on a single, consistent three-way comparison for every pair of keys. If ordering came from the comparator but identity/duplicate-detection came from `equals`, the tree would need two independently-defined equivalence relations that could contradict each other about which subtree a key belongs in — which breaks the total-order invariant the tree relies on for correctness. Committing fully to the comparator for both order and identity is the only way to keep the invariant consistent, at the cost of surprising results when the comparator disagrees with `equals`.

---

**Leaves covered:** 3.8.10–3.8.14 (5 leaves)
**Leaves deferred:** none
**Diagrams included:** none
**Target version:** Java 21 LTS
**Lines:** 543
