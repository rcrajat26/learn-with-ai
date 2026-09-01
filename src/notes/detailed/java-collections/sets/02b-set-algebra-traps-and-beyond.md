# 02 Java Collections — Sets — INTERMEDIATE (§2.12.4–2.12.10)

**Target version: Java 21 LTS.** | [Index](../00-index.md)
Previous: [sets/02-set-algebra.md](02-set-algebra.md) · Next: [sets/03-bitset.md](03-bitset.md)

## 0. Scope

[sets/02-set-algebra.md](02-set-algebra.md) covers the four core bulk
operations (`addAll`/`removeAll`/`retainAll`/`containsAll` as
union/difference/intersection/subset, §2.12.1–2.12.3), including the O(n·m)
`removeAll` trap and `AbstractSet.removeAll`'s size-based branching. This
file does not re-derive any of that — it assumes you already have the
mental model "bulk ops are set algebra, and the receiver gets mutated."

Two primary concepts, each grouping several closely-related leaves:

1. **Traps in bulk operations** (§2.12.4, §2.12.5, §2.12.9) — three ways
   the four core operations interact badly with mutation and immutability
   assumptions.
2. **Operations the JDK does and doesn't give you** (§2.12.6–§2.12.8,
   §2.12.10) — what exists beyond the four core ops, what's missing, and
   what runs at bitwise speed.

## 1. Traps in bulk operations (§2.12.4, §2.12.5, §2.12.9)

**Mental model:** every bulk operation on a *view* or on an *object whose
identity fields can change* is really an operation on whatever the view or
identity is backed by at the moment the operation runs, not at the moment
you formed a mental picture of the collection. The three traps below are
three different ways that gap between "what you think you're mutating"
and "what you're actually mutating" bites.

**Why each trap arises:** `keySet()` is not a copy — it is documented as a
live view, so mutating it is Documented Behavior, not a bug, and yet it
routinely surprises people who treat `Set<K> keys = map.keySet()` as a
snapshot. `removeAll` on an immutable collection surprises people in the
opposite direction — they expect *consistent* failure and instead get a
result that depends on the argument's contents. And the mutable-element
stranding trap surprises people who correctly reason about `equals`/
`hashCode` at insertion time but forget that a `HashSet` never re-evaluates
either after the bucket is chosen.

**When each applies:** §2.12.4 applies to *any* bulk mutator
(`retainAll`, `removeAll`, `clear`, `removeIf`) called on `keySet()`,
`values()`, or `entrySet()` of any `Map` — not just `HashMap`. §2.12.5
applies specifically to argument-dependent short-circuiting inside
mutator methods on immutable collections — it does not apply to `List`s
or `Set`s that are merely *unmodifiable wrappers* around a mutable
backing collection (those have their own, different behavior — see
below). §2.12.9 applies to any hash-based collection (`HashSet`,
`HashMap` keys, `LinkedHashSet`) whose elements are mutated in place after
insertion; it does not apply to `TreeSet`/`TreeMap` in the same way (there
the failure mode is a broken ordering invariant, not a lost bucket) and it
does not apply if the mutable field isn't part of `equals`/`hashCode`.

**No diagram for this concept** — the mechanism is fully expressed by the
runnable examples below; nothing here needs a picture beyond what
`02-set-algebra.md`'s existing diagrams (D-59, D-60) already show for the
core four operations.

### 2.12.4 — `retainAll` on a `keySet()` view mutates the map

`keySet()` returns a `Set<K>` that is a live window onto the map's own key
storage — the same field, no copy — and every bulk mutator
(`retainAll`/`removeAll`/`clear`/`removeIf`) on that view is forwarded to
the backing map's entry storage. Removing a key from the view removes the
whole mapping.

```java
Map<String, Integer> stock = new HashMap<>();
stock.put("bolt", 500);
stock.put("nut", 500);
stock.put("washer", 40);
stock.put("rivet", 0);

System.out.println("before: " + stock.size());   // before: 4

Set<String> keep = Set.of("bolt", "nut");
stock.keySet().retainAll(keep);

System.out.println("after: " + stock.size());    // after: 2
System.out.println(stock);                        // {bolt=500, nut=500}
```

The `washer` and `rivet` *entries* are gone, not just their keys sitting
in some detached set — because there never was a detached set. This is
the same live-view mechanism behind `values().removeIf(...)` deleting
entries by value and `entrySet().retainAll(...)` deleting by whole
mapping; `keySet()` is simply the most common entry point people reach
for without checking the Javadoc first.

**Insight:** treat any map-view bulk mutator as if you had called the
equivalent method on the map itself — because structurally, that is
exactly what happens.

### 2.12.5 — does `removeAll` on an immutable collection always throw?

**Unverified:** the exact per-implementation behavior below is reasoned
from the JDK's public class structure (`AbstractCollection`'s generic
`removeAll` algorithm versus each immutable-collection family's own
overrides), not from executing it against a specific JDK 21 build in this
session. Treat the claims here as a strong prior to verify, not a
guaranteed fact — see `## Open questions`.

The honest answer is **it depends on which immutable collection family
you're holding**, because "immutable" in the JDK is not one mechanism —
it is at least two different implementation strategies with different
`removeAll` consequences:

- **`List.of(...)` / `Set.of(...)` (`java.util.ImmutableCollections`).**
  These classes do not override `removeAll` at all — they inherit
  `AbstractCollection.removeAll`, whose algorithm iterates the receiver
  and calls `it.remove()` *only for elements that the argument actually
  contains*. If the argument shares nothing with the receiver (including
  the trivial case of an empty argument), `it.remove()` is never invoked,
  so the `UnsupportedOperationException` that the immutable iterator's
  `remove()` would throw never gets a chance to fire. The call quietly
  returns `false`.
- **`Collections.unmodifiableList(...)` / `unmodifiableSet(...)` (the
  wrapper classes).** These override `removeAll` directly to
  unconditionally throw `UnsupportedOperationException`, without
  inspecting the argument at all — there is no short-circuit, because the
  wrapper's whole job is to refuse every mutator call outright regardless
  of whether anything would change.

```java
List<Integer> a = List.of(1, 2, 3);
List<Integer> b = Collections.unmodifiableList(new ArrayList<>(a));

a.removeAll(List.of());          // no exception — nothing matched, no
                                  // mutator was ever invoked; returns false
System.out.println(a);           // [1, 2, 3]

a.removeAll(List.of(4, 5));      // no exception either — same reason
System.out.println(a);           // [1, 2, 3]

b.removeAll(List.of());          // throws UnsupportedOperationException
                                  // unconditionally — the wrapper never
                                  // even looks at the argument
```

**Pitfall:** it is tempting to conclude "immutable collections in Java
always throw on `removeAll`" or, having seen the `List.of(...)` case,
"immutable collections never throw when nothing would change." Neither
generalization is safe — the two families of immutable/unmodifiable
collections in the JDK arrive at different observable behavior for the
identical call shape, for unrelated implementation reasons (one never
reaches its blocking iterator; the other blocks unconditionally before
even looking at the argument). Never write defensive code that assumes a
specific one of these behaviors for an arbitrary `Collection` parameter
typed only as `List<T>` or `Set<T>` — check what concrete factory produced
it, or better, avoid depending on this behavior at all.

### 2.12.9 — mutating a set element after insertion strands it

This is the `Set` face of the same bug covered under mutable map keys
(`hash-map` internals; see the `D-16-mutable-key-stranding` diagram) —
identical mechanism, different container. A `HashSet` computes an
element's bucket index from its `hashCode()` *once*, at insertion. If a
field that feeds `hashCode()`/`equals()` changes afterward, the object
physically stays in its original bucket, but every future `contains`/
`remove` call recomputes the hash from the *current* field values and
looks in the wrong bucket.

```java
final class Point {
    int x, y;
    Point(int x, int y) { this.x = x; this.y = y; }

    @Override public boolean equals(Object o) {
        return o instanceof Point p && p.x == x && p.y == y;
    }
    @Override public int hashCode() { return Objects.hash(x, y); }
    @Override public String toString() { return "(" + x + "," + y + ")"; }
}

Set<Point> visited = new HashSet<>();
Point origin = new Point(0, 0);
visited.add(origin);

System.out.println(visited.contains(origin));   // true

origin.x = 7;                                     // mutate a hashCode() field
                                                   // in place, after insertion

System.out.println(visited.contains(origin));    // false  <-- same reference!
for (Point p : visited) {
    System.out.println("still physically here: " + p);   // still physically here: (7,0)
}
```

`origin` never left the set — iteration proves it is still there — but
`contains` on the exact same reference now returns `false`, because
`hashCode()` today (based on `x=7`) points at a different bucket than
`hashCode()` did at insertion time (based on `x=0`), and the object is
sitting in the bucket the *old* hash chose.

**Pitfall:** assuming that "the object is still in the set because I
never called `remove`" is safe to reason from. Presence-by-iteration and
findability-by-`contains`/`remove` are two different guarantees once an
element's identity fields are mutable, and only the first one survives
this bug. The fix is unchanged from the map-key version: never mutate a
field that participates in `equals`/`hashCode` while the object is a
member of a hash-based collection — remove it first, mutate, then
re-add, or use an immutable key/element type (a `record`, ideally).

> **Traps in bulk operations, boxed:** `keySet()`/`values()`/`entrySet()`
> forward bulk mutations to the backing map because they are views, not
> copies; `removeAll` on an immutable collection may or may not throw for
> a no-op argument because the JDK ships at least two different immutable/
> unmodifiable implementation strategies with different short-circuit
> behavior; and mutating a hash-based element's identity fields after
> insertion strands it in its original bucket, exactly as it does for map
> keys, because the hash is computed once at insertion and never
> recomputed by the collection itself.

## 2. Operations the JDK does and doesn't give you (§2.12.6–§2.12.8, §2.12.10)

**Mental model:** the four core bulk operations from
[sets/02-set-algebra.md](02-set-algebra.md) are eager, in-place mutators.
Everything in this section is either (a) a *read-only* operation with a
smarter-than-naive cost bound (`disjoint`), (b) something you must build
by hand from the core four because the JDK never shipped a dedicated
method for it (symmetric difference, multiset counting), or (c) a case
where the core four collapse into hardware-level bit operations because
of how the element type is represented (`EnumSet`).

**Why this gap exists:** the JDK's `Collection`/`Set` design intentionally
stayed minimal — four algebraic primitives plus a handful of predicates —
and left everything else (lazy views, multiplicity-aware collections,
richer set algebra) to either hand-rolled combinations of those primitives
or to third-party libraries, most commonly Guava.

**When each applies:** `disjoint` is for a yes/no overlap check, not for
computing the overlap itself. Symmetric difference is for "what's in
exactly one of the two sets" — genuinely different from union or from
either one-sided difference. Multiset/bag structures are for when
*how many* copies matter, which no JDK `Set` or `List`-as-set idiom
tracks. `EnumSet` bulk-op speed applies only between two `EnumSet`s of the
*same* enum type — mixing an `EnumSet<Day>` bulk op with a plain
`HashSet<Day>` argument falls back to the ordinary per-element path.

**No diagram for this concept** — each sub-item is a short, self-contained
mechanism better shown as code than as a picture.

### 2.12.6 — `Collections.disjoint(a, b)`

`Collections.disjoint` answers "do these two collections share *any*
element" without ever materializing the intersection. Its real
implementation is smarter than a naive O(n·m) double loop: it looks at
which argument is (or is close to) the smaller one, and — all else equal —
prefers to iterate whichever argument is backed by a `Set` (since `Set`
membership tests are typically O(1)), calling `contains` against the
other collection and stopping the instant it finds one shared element.

```java
Set<Integer> primes = Set.of(2, 3, 5, 7, 11);
List<Integer> sample = List.of(4, 6, 8, 9, 10, 12);

System.out.println(Collections.disjoint(primes, sample));  // true

List<Integer> withOnePrime = new ArrayList<>(sample);
withOnePrime.add(7);
System.out.println(Collections.disjoint(primes, withOnePrime)); // false
```

Cost bound: proportional to the size of whichever collection ends up
being iterated, times an O(1)-or-better `contains` on the other side —
not the product of both sizes, and it stops on the very first match.

### 2.12.7 — symmetric difference, built by hand and by Guava

Symmetric difference — "elements in exactly one of the two sets" — has no
dedicated method anywhere in the JDK `Collection` API. You build it from
the four core operations, either as `(a ∪ b) ∖ (a ∩ b)` or, equivalently
and without needing a throwaway intersection set, as the union of the two
one-sided differences:

```java
static <T> Set<T> symmetricDifference(Set<T> a, Set<T> b) {
    Set<T> onlyInA = new HashSet<>(a);
    onlyInA.removeAll(b);          // a ∖ b

    Set<T> onlyInB = new HashSet<>(b);
    onlyInB.removeAll(a);          // b ∖ a

    onlyInA.addAll(onlyInB);       // (a ∖ b) ∪ (b ∖ a)
    return onlyInA;
}

Set<Integer> a = Set.of(1, 2, 3, 4);
Set<Integer> b = Set.of(3, 4, 5, 6);
System.out.println(symmetricDifference(a, b));   // [1, 2, 5, 6]
```

Guava's `Sets.symmetricDifference(a, b)` computes the same mathematical
result but with a precise, testable behavioral difference: it returns a
**lazy, unmodifiable view**, not a new materialized `Set`. Nothing is
copied at call time; every read (`contains`, iteration, `size`) recomputes
against the live backing sets. Mutate `a` or `b` afterward and the view's
next read reflects the change — the hand-rolled version above is a
one-time snapshot that never changes again once built. Pick the hand-rolled
form when you want a stable, independent copy; pick Guava's when you want
the difference to always track two sets that keep changing.

### 2.12.8 — the JDK has no multiset/bag type

**Interview:** "why doesn't Java have a bag/multiset type in `java.util`"
is a genuinely common gap-check question, and the honest answer is that
the JDK's `Collection` contract is built around *boolean* membership
(present or absent) — nothing in `Set`, `List`-as-a-set idiom, or the four
bulk operations tracks *how many* logical copies of an element there are.

The idiomatic JDK-only substitute is `Map<T, Integer>`, hand-incrementing
counts:

```java
Map<String, Integer> counts = new HashMap<>();
for (String word : List.of("a", "b", "a", "c", "b", "a")) {
    counts.merge(word, 1, Integer::sum);
}
System.out.println(counts);   // {a=3, b=2, c=1}
```

When you actually need a real multiset type — with `add`, `count(elem)`,
`elementSet()`, and multiplicity-aware `Multisets.union`/`intersection`
helpers — Guava's `Multiset<E>` (e.g. `HashMultiset`, `TreeMultiset`) is
the standard answer; it is not part of the JDK and never has been.

### 2.12.10 — `EnumSet` bulk ops as single bitwise instructions

One paragraph, cross-reference only — `EnumSet` is covered in full in
[specialised-maps/01-enum-collections.md](../specialised-maps/01-enum-collections.md)
(§2.9) and internals in
[specialised-maps/02-internals-enum-map-set.md](../specialised-maps/02-internals-enum-map-set.md)
(§3.10). The one fact that belongs here: because every enum constant's
ordinal is a fixed bit position shared by *all* `EnumSet`s of that enum
type, `addAll`/`removeAll`/`retainAll` between two `EnumSet`s of the same
enum type compile down to a single `|=` / `&= ~` / `&=` over the backing
`long` (`RegularEnumSet`) or `long[]` (`JumboEnumSet`, for enums with more
than 64 constants) — no per-element loop, no hashing, no boxing. Mixing an
`EnumSet` bulk op with a non-`EnumSet` argument of the same enum type still
works correctly but falls back to the ordinary per-element iteration path,
since there is no shared bit encoding to exploit.

> **Operations the JDK does and doesn't give you, boxed:** `disjoint` is a
> read-only overlap test with a size-aware, first-match-stops cost bound,
> not a full intersection; symmetric difference has no JDK method and must
> be built from the core four (eagerly) or borrowed from Guava as a lazy
> recomputing view; multiset/bag semantics are entirely absent from the
> JDK — `Map<T,Integer>` is the manual substitute, Guava `Multiset` the
> real one; and `EnumSet` bulk operations between same-typed `EnumSet`s
> collapse to single bitwise instructions because both operands already
> share one bit-position encoding.

## Pitfalls

- **Wrong:** "`keySet()` gives me a snapshot of the map's keys I can
  filter safely." **Right:** it's a live view — `retainAll`/`removeAll`/
  `clear` on it deletes the corresponding entries from the map itself
  (§2.12.4).
- **Wrong:** "an immutable/unmodifiable collection's `removeAll` always
  throws `UnsupportedOperationException`, regardless of the argument."
  **Right:** it depends on the implementation family — `List.of(...)`-style
  immutable collections can silently no-op when the argument shares
  nothing with the receiver (their inherited `removeAll` never reaches the
  blocking mutator), while `Collections.unmodifiableList(...)`-style
  wrappers throw unconditionally, argument or no argument. **Unverified**
  against a live JDK 21 run in this note — confirm before relying on it
  (§2.12.5).
- **Wrong:** "the object is still in my `HashSet` because I only mutated a
  field, I never called `remove`." **Right:** it's still *present*
  (iteration finds it) but no longer *findable* by `contains`/`remove`
  once a `hashCode()`/`equals()` field changes after insertion — the same
  stranding bug that hits mutable map keys (§2.12.9).
- **Wrong:** "checking two collections for overlap means computing their
  intersection and checking if it's empty." **Right:** `Collections.disjoint`
  answers the yes/no question directly, stopping at the first shared
  element, without ever materializing an intersection set (§2.12.6).
- **Wrong:** "there must be a `Set.symmetricDifference` method somewhere
  in the JDK." **Right:** there isn't — build it from the four core ops,
  or use Guava's lazy view if you want it to track two live, changing sets
  (§2.12.7).

## Cheat sheet

| Leaf | Operation | JDK support | Cost / behavior | Trap? |
|---|---|---|---|---|
| 2.12.4 | `map.keySet().retainAll(s)` | Built in, live view | Forwards to backing map — deletes entries | `[TRAP]` |
| 2.12.5 | `immutableColl.removeAll(c)` | Built in, but not one behavior | `List.of(...)` family: may no-op silently; `unmodifiableXxx` wrappers: throw unconditionally | `[TRAP]`, **Unverified** |
| 2.12.6 | `Collections.disjoint(a, b)` | Built in | Iterates the (likely) smaller/Set-backed side, `contains` on the other, stops on first match | no |
| 2.12.7 | Symmetric difference | Not built in | Hand-build via `(a∪b)∖(a∩b)`, eager; Guava `Sets.symmetricDifference`, lazy view | no |
| 2.12.8 | Multiset/bag | Not built in | `Map<T,Integer>` manual counting; Guava `Multiset<E>` for the real thing | no |
| 2.12.9 | Mutate a set element's hash fields post-insertion | N/A — a misuse pattern | Element stranded in its original bucket; `contains` fails, iteration still finds it | `[TRAP]` |
| 2.12.10 | `EnumSet` bulk ops, same enum type | Built in | Single bitwise `\|=`/`&=~`/`&=` over backing `long`/`long[]` — see cross-ref file | no |

## Self-test

<details>
<summary>1. Why does calling `retainAll` on `map.keySet()` shrink `map.size()`?</summary>

`keySet()` returns a live view backed by the same storage as the map, not
a copy — any structural bulk mutation on the view (including `retainAll`)
is forwarded to the map, removing the corresponding entries entirely.
</details>

<details>
<summary>2. Does `List.of(1,2,3).removeAll(List.of())` throw?</summary>

No — because `AbstractCollection.removeAll`'s inherited algorithm only
calls the blocking `remove()` on elements the argument actually contains,
and an empty argument never matches anything, the blocking call is never
reached. This differs from `Collections.unmodifiableList(...)`, whose
`removeAll` is overridden to throw unconditionally regardless of the
argument. Treat the exact JDK 21 behavior here as unverified in this note
— see Open questions.
</details>

<details>
<summary>3. What cost bound does `Collections.disjoint` give you, and why isn't it O(n·m)?</summary>

It iterates whichever collection it judges cheaper to walk (favoring the
smaller one, and favoring a `Set`-backed argument when sizes are close),
calling `contains` on the other side and stopping at the first shared
element — cost is proportional to elements actually visited before a
match (or all of the iterated side, if disjoint), not the full cross
product of both sizes.
</details>

<details>
<summary>4. How would you compute the symmetric difference of two `Set`s using only JDK methods?</summary>

Copy `a`, `removeAll(b)` to get `a∖b`; copy `b`, `removeAll(a)` to get
`b∖a`; `addAll` one into the other. Equivalently, `(a∪b)∖(a∩b)` with three
bulk-op calls. There is no dedicated JDK method for this operation.
</details>

<details>
<summary>5. What's the practical difference between the hand-built symmetric difference above and Guava's `Sets.symmetricDifference`?</summary>

The hand-built version eagerly materializes a new, independent `Set` at
the moment you call it. Guava's version returns a lazy, unmodifiable view
that recomputes against the live backing sets on every read — mutate
either input afterward and the view's next `contains`/iteration reflects
the change; the hand-built copy never does.
</details>

<details>
<summary>6. Why is there no `Multiset` or `Bag` interface in `java.util`?</summary>

`Collection`'s membership model is boolean — present or absent — with no
notion of multiplicity built into any core interface. The JDK never added
one; `Map<T,Integer>` with manual counting is the JDK-only substitute, and
Guava's `Multiset<E>` is the standard third-party answer when multiplicity
actually needs to be tracked.
</details>

<details>
<summary>7. Describe the stranding bug for `Set` elements. Is the object still "in" the set afterward?</summary>

Yes, physically — iteration still walks past it. But mutating a field that
feeds `hashCode()`/`equals()` after insertion leaves the object in the
bucket its *original* hash chose, while `contains`/`remove` recompute the
hash from current field values and look in a different bucket, so lookups
by the same reference fail. Identical mechanism to the mutable-map-key
stranding bug.
</details>

<details>
<summary>8. Does `EnumSet.retainAll` between two `EnumSet<DayOfWeek>` instances loop over elements?</summary>

No — since both operands share the exact same bit-position encoding for
`DayOfWeek`'s constants, `retainAll` compiles to a single `&=` over the
backing `long` (or `long[]` for enums with over 64 constants). No
per-element loop, no hashing.
</details>

<details>
<summary>9. If you mix an `EnumSet<DayOfWeek>` bulk op with a `HashSet<DayOfWeek>` argument, do you still get the bitwise speedup?</summary>

No — the bitwise fast path only applies when both operands are `EnumSet`s
of the same enum type sharing the same bit encoding. A non-`EnumSet`
argument falls back to the ordinary per-element `contains`/iteration path,
though the result is still correct.
</details>

<details>
<summary>10. Why is it unsafe to assume all "immutable" `List`/`Set` implementations in the JDK behave identically under `removeAll`?</summary>

Because "immutable" covers at least two distinct implementation
strategies — `List.of(...)`/`Set.of(...)`'s `ImmutableCollections` family,
which inherits a generic algorithm that can silently no-op on a
non-matching argument, versus `Collections.unmodifiableXxx(...)` wrappers,
which override the mutator to throw unconditionally. The two families
give different observable behavior for the same call shape, for unrelated
implementation reasons.
</details>

## Open questions

- Whether `List.of(...)`/`Set.of(...)`'s inherited `removeAll` genuinely
  never invokes the blocking iterator `remove()` when the argument shares
  nothing with the receiver — as reasoned here from `AbstractCollection`'s
  published algorithm — versus whether some JDK 21 `ImmutableCollections`
  subclass overrides `removeAll` directly with different behavior, is not
  verified against a running JDK 21 build in this note. Confirm directly
  (e.g. `jshell` against your exact JDK 21 update) before relying on this
  distinction in production defensive code.

---

**Leaves covered:** 2.12.4–2.12.10 (7 leaves)
**Leaves deferred:** none
**Diagrams included:** none
**Target version:** Java 21 LTS
**Lines:** 516
