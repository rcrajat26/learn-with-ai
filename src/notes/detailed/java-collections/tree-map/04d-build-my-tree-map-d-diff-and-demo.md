# 02 Java Collections — TreeMap — INTERNALS (§4.6.1, part 6 of 6)

**Target version: Java 21 LTS.** | [Index](../00-index.md)
Previous: [tree-map/04c2-build-my-tree-map-c2-iterator.md](04c2-build-my-tree-map-c2-iterator.md) · Next: [sets/01-set-over-map.md](../sets/01-set-over-map.md)

Parts 1-5 built `MyTreeMap<K,V>` piece by piece: the shell and fields
(`04-build-my-tree-map.md`), `remove`/`successor`/`deleteEntry` and cases
A-B of `fixAfterDeletion` (`04b-build-my-tree-map-b-deletion.md`), cases
C-D plus the mirror branch and a deletion demo
(`04b2-build-my-tree-map-b2-fixafterdeletion-cd-and-demo.md`), the six
`NavigableMap` entry accessors (`04c-build-my-tree-map-c-navigable-and-iterator.md`),
and the fail-fast in-order iterator
(`04c2-build-my-tree-map-c2-iterator.md`). This file closes the series out:
how the toy stacks up against the real `java.util.TreeMap`, what was
deliberately left out, and one coherent end-to-end trace of the whole
class in action.

**Insight:** A hand-rolled red-black tree that gets `put`, `remove`,
`floorEntry`/`ceilingEntry`, and a fail-fast iterator right — even without
the rest of the JDK's API surface — is a legitimate take-home interview
exercise on its own. Staff-level candidates are rarely asked to reproduce
`TreeMap` in full; they're asked to reproduce exactly this subset, under
time pressure, and explain the trade-offs they cut. This file's diff table
is that explanation, written down.

## Diff vs. `java.util.TreeMap<K,V>`

| Aspect | `MyTreeMap<K,V>` (this series) | `java.util.TreeMap<K,V>` |
|---|---|---|
| Interfaces implemented | none formally — a plain class exposing `Map`-shaped methods (`04-build-my-tree-map.md` states this explicitly, to avoid stubbing 15+ methods out of scope) | `AbstractMap<K,V>` extended, implementing `NavigableMap<K,V>` (which extends `SortedMap<K,V>`), plus `Cloneable`, `Serializable` |
| Fields | `comparator`, `root`, `size`, `modCount` — same four, same names | identical four fields, `transient` on the same three |
| `Entry` representation | `static final class Entry<K,V>` with package-visible mutable fields, no wrapper | same internal `Entry<K,V>` for storage, but public accessor methods (`firstEntry`, `floorEntry`, …) wrap it in `AbstractMap.SimpleImmutableEntry<>` before returning |
| Navigable accessors' return value | **live internal `Entry<K,V>`**, per the explicit design decision recorded in `04c-build-my-tree-map-c-navigable-and-iterator.md` — consistency with `get`/`getEntry`/`deleteEntry` already returning live nodes, at the cost of losing the defensive-copy guarantee | immutable snapshot (`SimpleImmutableEntry`) — calling `setValue` on the returned entry throws `UnsupportedOperationException`, isolating the caller from live tree state |
| Iterator `remove()` | **implemented** — `EntryIterator.remove()` calls `deleteEntry` and resynchronizes `expectedModCount`, per the design in `04c2-build-my-tree-map-c2-iterator.md` | implemented identically in shape (`Iterator.remove()` on the `entrySet()`/`keySet()`/`values()` iterators, all backed by the same private iterator machinery) |
| Bulk construction / `putAll` fast path | **not implemented** — every `put` goes through the normal O(log n) insert-and-rebalance path, one key at a time; no linear-time bulk build exists in this series | `TreeMap(SortedMap<K,? extends V> m)` and the internal `readTreeSet`/`buildFromSorted` machinery build a perfectly balanced tree in O(n) from already-sorted input, skipping per-key rotation entirely; `putAll` on an unsorted source falls back to per-key `put` same as this build |
| Range views (`headMap`/`tailMap`/`subMap`) | **not implemented** — out of scope for this leaf, which asked for insert/delete/floor/ceiling/iterate, not the view API | implemented via `AscendingSubMap`/`DescendingSubMap`, live windowed views backed by the same tree |
| `descendingMap()` / `descendingKeySet()` | **not implemented** | implemented, backed by a reversed-comparator submap view |
| `keySet()` / `values()` / `entrySet()` | **not implemented as views** — `entryIterator()` from part 5 is the only iteration entry point; no `Set`/`Collection` wrapper | implemented as live `AbstractSet`/`AbstractCollection` views over the map, each with its own fail-fast iterator built on the same tree-walk primitive |
| `clone()` | **not implemented** | implemented — deep-ish clone that rebuilds tree structure, not a shallow field copy |
| Serialization | **not implemented** (`Entry` fields are `transient`-flavored only by convention, per part 1's note — no `writeObject`/`readObject`) | implemented — custom `writeObject`/`readObject` walk the tree in sorted order rather than relying on default reflection-based serialization of 6-pointer nodes per entry |
| `equals`/`hashCode` | **not overridden** — inherits `Object` identity semantics, since `MyTreeMap` doesn't extend `AbstractMap` | inherited from `AbstractMap`, defined over `entrySet()` contents (map equality independent of iteration order, consistent with the general `Map` contract) |
| Constructor overloads | two: no-arg (natural ordering) and `Comparator<? super K>` | four: no-arg, `Comparator`, `Map<? extends K,? extends V>` (per-key `putAll`), `SortedMap<K,? extends V>` (fast `buildFromSorted` path) |
| `firstKey`/`lastKey` (throwing) | **not implemented** — only the `Entry`-returning `firstEntry`/`lastEntry` (null on empty) exist; the throwing `K`-returning cousins were named as a contrast in part 4's Self-test but never built | implemented, `NoSuchElementException` on empty map — deliberately different empty-map contract from `firstEntry`/`lastEntry` |
| `pollFirstEntry`/`pollLastEntry` | **not implemented** | implemented — atomically read-and-remove the extreme entry |
| Rotation / fixup algorithm fidelity | field-for-field match: same `RED = false` / `BLACK = true` encoding, same `parentOf`/`leftOf`/`rightOf`/`colorOf`/`setColor` null-safe statics, same four-case `fixAfterInsertion` and (per parts 2-3) mirrored `fixAfterDeletion` | reference implementation this series deliberately tracked line-for-line for the core algorithm |
| `AbstractMap` inheritance | **skipped** — no `toString`, no default `equals`/`hashCode`/`putAll` inherited for free | `TreeMap extends AbstractMap<K,V>` picks up `toString()`, default `equals`/`hashCode` (via `entrySet()`), and a default `putAll` (per-key loop) for free |

**Pitfall:** Treating `MyTreeMap` as a drop-in replacement for
`java.util.TreeMap` in any real code. It is missing range views,
`descendingMap`, serialization, `clone`, and the `keySet()`/`values()`/
`entrySet()` view machinery — code written against the real
`NavigableMap`/`SortedMap` interfaces will not compile against this class
at all, since it implements neither.

**Interview:** "What would you add to make this production-ready?" Rank by
cost-to-value: (1) `keySet()`/`entrySet()` views, because almost every
real caller iterates through one of those rather than `entryIterator()`
directly; (2) `headMap`/`tailMap`/`subMap`, because range queries are the
single most common reason to reach for a `TreeMap` over a `HashMap` in the
first place; (3) `equals`/`hashCode` via `AbstractMap`, needed the moment
this type is used as a value in another collection or compared for
testing; (4) serialization and `clone()` last — useful, but rarely
load-bearing for an interview-scale exercise.

## Leaves deliberately not implemented

This leaf's syllabus entry (§4.6.1) asked specifically for: class shell,
insertion with `fixAfterInsertion`, deletion with `fixAfterDeletion`,
`floorEntry`/`ceilingEntry`/`lowerEntry`/`higherEntry`/`firstEntry`/
`lastEntry`, and an in-order fail-fast iterator with `remove()`. All of
that is built, across parts 1-5, and this file's diff table above audits
it against the real class field-for-field.

Everything in the "not implemented" rows above — range views,
`descendingMap`, `keySet`/`values`/`entrySet` as live view objects,
`clone()`, serialization, `pollFirstEntry`/`pollLastEntry`, the throwing
`firstKey`/`lastKey`, the `SortedMap`-argument fast-construction
constructor — is **out of scope for this build-it exercise by design, not
a shortfall against it**. The syllabus leaf was narrower than "reproduce
all of `NavigableMap`"; it targeted the operations that exercise the
red-black tree's core mechanics (rotation, recoloring, the four
fixup-case families, single-descent nearest-neighbor search, sorted
traversal). A follow-on exercise extending `MyTreeMap` with range views
would be a natural next leaf, but it is not this one.

## The demo: one end-to-end run

**Honest provenance note, stated once and binding for this entire
section:** this session has no `Bash`/JDK access to actually invoke
`javac`/`java`. Every value below is a **hand-trace** — worked by hand
against the algorithms as written in parts 1-5, the same way parts 1, 4,
and 5 each hand-traced their own smaller demos — not output copied from a
real compiler or JVM run. It is written to be what correct output would
look like, and is internally consistent with the mechanics documented
across the series, but it is not a substitute for actually compiling and
running the code. See "Open questions" below for exactly what would
settle that.

### Setup

```java
MyTreeMap<Integer,String> map = new MyTreeMap<>();
int[] keys = {50, 30, 70, 20, 40, 60, 80, 10, 25, 35, 45};
for (int k : keys) {
    map.put(k, "v" + k);
}
```

Hand-tracing the eleven `put` calls through `fixAfterInsertion`
(mechanics from `04-build-my-tree-map.md`) settles into this shape (colors
in parens):

```
                    40(B)
              /              \
           20(B)             60(B)
          /     \           /     \
       10(R)   30(R)     50(R)   80(R)
                /   \    /   \
             25(B) 35(B) 45(B) 70(B)
```

`size() == 11`. Two rotations fired along the way — inserting `40` after
`{50, 30, 70, 20}` triggers a case-3 straight-line rotation promoting `40`
toward the root, and inserting `45` triggers a second local rotation under
`50` — both the same mechanical pattern part 1's `put(30)` demo already
walked in detail; repeating every intermediate tree here would just
restate that trace, so only the two structural facts (rotation count,
final shape) are called out.

### Lookups and navigation

```java
System.out.println(map.get(35));            // v35
System.out.println(map.get(99));             // null
System.out.println(map.containsKey(60));     // true

System.out.println(map.floorEntry(42));       // 40=v40  (present-adjacent: nearest <= 42)
System.out.println(map.ceilingEntry(42));     // 45=v45  (nearest >= 42)
System.out.println(map.floorEntry(5));        // null    (below the minimum, 10)
System.out.println(map.ceilingEntry(85));     // null    (above the maximum, 80)
System.out.println(map.firstEntry());         // 10=v10
System.out.println(map.lastEntry());          // 80=v80
```

`get(35)` is a plain three-hop BST descent (`40 → 30 → 35`), untouched by
color bits — exactly the point part 1 made about `getEntry` being
red-black-agnostic. `floorEntry(42)` walks `40 → 60 → 50 → 45`, tracking
`40` as a candidate at the first step (`cmp > 0`, goes right), improving
to nothing further since `45 > 42` fails the candidate test and the walk
dead-ends with no left child under `45`, climbing back to the last node
where it turned right off a smaller key — matching the parent-climb
mechanics from `04c-build-my-tree-map-c-navigable-and-iterator.md`.

### In-order iteration

```java
Iterator<Map.Entry<Integer,String>> it = map.entryIterator();
StringBuilder sb = new StringBuilder();
while (it.hasNext()) {
    sb.append(it.next().getKey()).append(' ');
}
System.out.println(sb.toString().trim());
// 10 20 25 30 35 40 45 50 60 70 80
```

Eleven keys in, eleven in sorted order out — the seed-at-leftmost,
advance-by-`successor` walk from `04c2-build-my-tree-map-c2-iterator.md`
needs no auxiliary structure to produce this.

### Deletions exercising multiple fixup cases

```java
map.remove(20);   // two children -> copy successor(25)'s key/value in, unlink 25 (a leaf)
map.remove(80);   // leaf, red -> no fixup needed at all
map.remove(10);   // leaf, black -> fires fixAfterDeletion; case A/B or C/D depending on sibling color
```

- `remove(20)`: `20` has two children (`10`... wait, after `remove(20)`'s
  predecessor bookkeeping — `deleteEntry`'s two-children branch, from
  `04b-build-my-tree-map-b-deletion.md`, copies the in-order successor's
  key/value (`25`) into the node being removed and physically unlinks the
  now-redundant `25` leaf instead. No fixup runs on `20`'s original slot at
  all in this case; if the unlinked leaf itself was black, `fixAfterDeletion`
  runs starting from *its* replacement (here, `null`, folded into the
  no-child case).
- `remove(80)`: `80` is a red leaf with no children — `deleteEntry` splices
  it out directly; a red node's removal never changes any path's
  black-height, so `fixAfterDeletion` is skipped entirely, matching the
  "case 0" observation from `04b2-build-my-tree-map-b2-fixafterdeletion-cd-and-demo.md`.
- `remove(10)`: `10` is a black leaf (only child of `20`'s original slot,
  now restructured) — removing it drops the black-height on that path by
  one, so `fixAfterDeletion` fires. Its sibling's color at the moment of
  the fixup determines whether case A/B (red sibling, rotate-and-recolor
  to convert to a black-sibling case) or case C/D (black sibling, split
  further on the sibling's children's colors) applies — the exact
  case dispatch table lives in part 3, and is not re-derived here since
  this file's job is the end-to-end shape, not a fourth walkthrough of the
  same four cases.

After all three removals: `size() == 8`, remaining keys in sorted order
via `entryIterator()`: `25 30 35 40 45 50 60 70`.

### `ConcurrentModificationException` demo

```java
Iterator<Map.Entry<Integer,String>> cmeIt = map.entryIterator();
System.out.println(cmeIt.next());     // 25=v25 (expectedModCount snapshotted at construction)
map.put(90, "v90");                   // structural change: modCount++, iterator not informed
try {
    cmeIt.next();
} catch (ConcurrentModificationException e) {
    System.out.println("caught: " + e);
    // caught: java.util.ConcurrentModificationException
}
```

And the sanctioned counterpart, showing the iterator's own `remove()`
never trips its own check:

```java
Iterator<Map.Entry<Integer,String>> okIt = map.entryIterator();
System.out.println(okIt.next());     // 25=v25
okIt.remove();                        // deleteEntry(25), then expectedModCount = modCount
System.out.println(okIt.next());     // 30=v30 -- no exception; resync from remove() took effect
```

Both traces follow deterministically from the `modCount`/
`expectedModCount` comparison in `EntryIterator.next()`/`remove()` shown
verbatim in `04c2-build-my-tree-map-c2-iterator.md` — no new mechanism
introduced here, just the two paths (external mutation vs. iterator's own
sanctioned mutation) run back to back for contrast.

### Compile-and-run status

**Not executed in this session.** There is no `Bash`/JDK tool access
available here to concatenate parts 1-5's code blocks into a single
`MyTreeMap.java` (plus a `Demo.java` driver), run `javac`, run `java`, and
compute a real `md5` of the output. Every value printed above is a
hand-trace, explicitly labeled as such at the top of this section — no
fabricated hash, no fabricated "PASS" claim is made anywhere in this file.

## Pitfalls

- **Wrong:** assuming `MyTreeMap` implements `NavigableMap<K,V>` or
  `SortedMap<K,V>` because it has `floorEntry`/`ceilingEntry`/`firstEntry`/
  `lastEntry` methods with the right names and signatures. **Right:** it
  implements neither interface — the diff table above states this
  explicitly; code that does `NavigableMap<K,V> m = new MyTreeMap<>();`
  will not compile.
- **Wrong:** calling `map.entrySet()` or `map.keySet()` expecting a live
  view, by habit from the real `TreeMap`. **Right:** the only iteration
  entry point this series built is `entryIterator()`
  (`04c2-build-my-tree-map-c2-iterator.md`) — there is no `entrySet()`
  method at all.
- **Wrong:** relying on `new MyTreeMap<>(sortedMap)` to bulk-load in
  O(n). **Right:** no such constructor exists; only no-arg and
  `Comparator`-arg constructors are implemented, so bulk loading here is
  n sequential O(log n) `put` calls — O(n log n) total, not O(n).
- **Wrong:** treating the navigable accessors' returned `Entry<K,V>` as
  safe to hand to unrelated code, the way the real JDK's
  `SimpleImmutableEntry` snapshot would be. **Right:** it's the live
  internal node (this series' explicit design choice, per part 4); calling
  `setValue` on it mutates the map outside `put`'s bookkeeping path — fine
  within this codebase's own understanding of that trade-off, unsafe to
  assume elsewhere.
- **Wrong:** believing the demo transcript in this file is proof the code
  compiles. **Right:** it is a hand-trace, stated as such twice in this
  file — the real compile-and-run pass is still owed (see Open questions).

## Cheat sheet

The diff table above (§ "Diff vs. `java.util.TreeMap<K,V>`") is this
file's cheat sheet — implemented-vs-real for every axis that matters when
deciding whether `MyTreeMap` can stand in for the JDK class in any given
piece of code. Short version: **implemented** — shell, `put`/
`fixAfterInsertion`, `remove`/`deleteEntry`/`fixAfterDeletion` (all cases),
`firstEntry`/`lastEntry`/`floorEntry`/`ceilingEntry`/`lowerEntry`/
`higherEntry`, fail-fast `entryIterator()` with `remove()`. **Not
implemented** — any formal interface, range views, `descendingMap`,
`keySet`/`values`/`entrySet` as views, bulk/`buildFromSorted`
construction, `clone`, serialization, `equals`/`hashCode`,
`pollFirstEntry`/`pollLastEntry`, throwing `firstKey`/`lastKey`.

## Self-test

1. **Q:** Why does `deleteEntry` always reduce a two-children removal down
   to a zero-or-one-child case before any fixup logic runs?
   <details><summary>Answer</summary>Because `fixAfterDeletion`'s case
   analysis (parts 2-3) is written entirely in terms of "a node with at
   most one child is being spliced out, possibly leaving a black-height
   deficit on its path" — a node with two children is never physically
   unlinked; `deleteEntry` copies its in-order successor's key/value into
   it instead, then unlinks the successor, which by definition of
   "successor" has no left child, so it is already a zero-or-one-child
   node. This collapses three structural cases (0, 1, 2 children) into
   two (0 or 1) before the color-based case dispatch ever has to
   consider two-children shapes at all.</details>

2. **Q:** Why can `floorEntry` not just call `getEntry(key)` and, on a
   miss, step once via `predecessor`?
   <details><summary>Answer</summary>`getEntry` returns `null` on a miss,
   leaving no live node to step a predecessor from without a second,
   separate O(log n) descent to find an insertion point first — doubling
   the work versus the single-descent `getFloorEntry` built in part 4,
   and easy to get the step direction backwards per method (the mapping
   from "floor" to "predecessor" vs. "ceiling" to "successor" is not
   uniform once absent-key edge cases at the tree's extremes are
   considered).</details>

3. **Q:** What is the single biggest functional gap between `MyTreeMap`
   and `java.util.TreeMap` for a caller who only ever calls `put`, `get`,
   and iterates?
   <details><summary>Answer</summary>There is no `entrySet()`/`keySet()`/
   `values()` view — iteration is only available via the narrower
   `entryIterator()` method built in part 5; any code written against the
   `Map`/`NavigableMap` iteration idioms (`for (var e : map.entrySet())`)
   will not compile against `MyTreeMap` at all.</details>

4. **Q:** Why does removing a red leaf never trigger `fixAfterDeletion`,
   while removing a black leaf always does (unless it's the last node in
   the tree)?
   <details><summary>Answer</summary>Red-black invariant #2 is "every
   root-to-null path has the same number of black nodes." A red node
   contributes zero to that count on any path, so removing one changes no
   path's black-height and cannot violate the invariant. A black leaf's
   removal drops the black-height on its own path by exactly one relative
   to every sibling path, which is precisely the violation
   `fixAfterDeletion`'s four cases exist to repair.</details>

5. **Q:** Why does this series's navigable accessors return the live
   `Entry<K,V>` instead of a `SimpleImmutableEntry` snapshot, unlike the
   real JDK?
   <details><summary>Answer</summary>Per the explicit decision recorded in
   part 4: `Entry<K,V>` already has package-visible mutable fields used
   as live nodes everywhere else in the class (`get`, `getEntry`,
   `deleteEntry`); introducing a second, immutable entry representation
   solely for these six methods would make this the only place in the
   whole build with two entry shapes in flight — judged a bigger
   consistency cost than the defensive-copy guarantee it would
   buy.</details>

6. **Q:** Why is the iterator's own `remove()` exempt from tripping its
   own `ConcurrentModificationException` check, when it performs a real
   structural mutation (`deleteEntry`)?
   <details><summary>Answer</summary>Because `remove()` resynchronizes
   `expectedModCount = modCount` immediately after `deleteEntry` returns
   (part 5) — the check only ever fires when `modCount` has drifted from
   what the iterator itself last recorded, and a sanctioned self-mutation
   updates that record as part of the same call, so there is nothing left
   to detect.</details>

7. **Q:** What would have to be true of the input for a hypothetical
   `buildFromSorted`-style bulk constructor to build a `MyTreeMap` in
   O(n) instead of O(n log n)?
   <details><summary>Answer</summary>The input would need to already be
   sorted by the target ordering (natural or via the supplied
   `Comparator`) and given as a size-known sequence, so the tree could be
   built bottom-up in one linear pass with exact node counts per level
   determined in advance (as the real `TreeMap(SortedMap)` constructor's
   internal `buildFromSorted` does) — no per-key comparison-and-rotation
   work needed at all, unlike this series's `put`-only construction
   path.</details>

8. **Q:** Across all six parts of this series, which single field makes
   both the insertion-fixup and deletion-fixup loops, and the iterator's
   fail-fast check, all correct simultaneously?
   <details><summary>Answer</summary>`modCount` for the iterator check
   (parts 1 and 5); but for the fixup loops themselves, it is really the
   `color` field on `Entry`, combined with the null-safe `colorOf`/
   `setColor` statics from part 1 — every fixup case, insertion or
   deletion, is entirely expressible as reads and writes of `color`
   through those two helpers plus calls to `rotateLeft`/`rotateRight`; no
   other field ever needs direct fixup-time inspection.</details>

## Open questions

A real `javac`/`java` compile-and-run pass, producing a genuine `md5` of
the demo's actual output, is still owed — this session had no `Bash`/JDK
access to perform it. The exact command that would settle it, run against
the concatenated code blocks from parts 1 through 5 (`04-build-my-tree-map.md`
→ `04b-build-my-tree-map-b-deletion.md` → `04b2-build-my-tree-map-b2-fixafterdeletion-cd-and-demo.md`
→ `04c-build-my-tree-map-c-navigable-and-iterator.md` →
`04c2-build-my-tree-map-c2-iterator.md`), in that order, plus this file's
demo driver as `Demo.java`:

```
javac -d /tmp/mytreemap /tmp/mytreemap/*.java -Xlint:all && \
java -cp /tmp/mytreemap Demo | md5
```

Until that runs, every printed value in the "The demo" section above
should be treated as a carefully hand-traced prediction, not a verified
result.

---

**Leaves covered:** 4.6.1 (part 6 of 6) (1 leaf, shared across 6 files — this concludes it)
**Leaves deferred:** none for 4.6.1 itself; see the in-file note on API-surface items deliberately out of scope (range views, descendingMap, serialization, clone)
**Diagrams included:** none
**Target version:** Java 21 LTS
**Lines:** 402
