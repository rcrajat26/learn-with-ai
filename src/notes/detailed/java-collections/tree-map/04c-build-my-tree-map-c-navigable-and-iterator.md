# 02 Java Collections — TreeMap — INTERNALS (§4.6.1, part 4 of 6)

**Target version: Java 21 LTS.** | [Index](../00-index.md)
Previous: [tree-map/04b2-build-my-tree-map-b2-fixafterdeletion-cd-and-demo.md](04b2-build-my-tree-map-b2-fixafterdeletion-cd-and-demo.md) · Next: [tree-map/04c2-build-my-tree-map-c2-iterator.md](04c2-build-my-tree-map-c2-iterator.md)

Parts 1-3 built `MyTreeMap`'s shell, fields, rotations, `put` with
`fixAfterInsertion`, `remove`/`deleteEntry` with the full
`fixAfterDeletion`, and the static `successor(Entry<K,V> t)` helper. Every
one of those methods answers "is this key here, and what's its value."
This file answers a different question: "what key is *near* this one, in
sorted order, whether or not it's actually present." Those are the six
`NavigableMap` entry accessors — `firstEntry`, `lastEntry`, `floorEntry`,
`ceilingEntry`, `lowerEntry`, `higherEntry` — added as further methods on
the same `MyTreeMap<K,V>` class body. The iterator that walks the whole
tree in order is a related but separate concern and is deferred to the next
file, `tree-map/04c2-build-my-tree-map-c2-iterator.md`; nothing below
builds an `Iterator`.

## Return type: internal `Entry<K,V>`, not a snapshot wrapper

**Decision:** these six methods return the class's own internal
`Entry<K,V>` (defined in part 1) directly, not a `SimpleEntry`-style
immutable copy. The real `java.util.TreeMap` returns a defensive
`AbstractMap.SimpleImmutableEntry<>` snapshot — precisely so a caller can't
call `setValue` on the returned entry and silently mutate live tree state
outside of `put`/`remove`'s bookkeeping (size, modCount, rebalancing).
That fidelity detail matters for the real class's public contract, but
this build-it series already established (`04-build-my-tree-map.md`) that
`Entry<K,V>` here is `static final class Entry` with **package-visible**
mutable fields and no snapshot wrapper anywhere in the class — `get`,
`getEntry`, `deleteEntry`, and everything else in parts 1-3 hand back or
operate on live `Entry` objects. Introducing a snapshot type solely for
these six methods would make this the only place in the whole build with
two different entry representations in flight, which is a bigger
consistency cost than the fidelity gap it buys. If this were a
publicly-shipped class instead of a study exercise, the JDK's
`SimpleImmutableEntry` wrapping would be the right call; noted here and in
the pitfalls section, then set aside.

## firstEntry / lastEntry

**Mechanism:** `firstEntry` walks `left` from `root` until it runs out of
left children; `lastEntry` walks `right` the same way. Both are the same
"run off the edge of the tree" walk that `successor`/`predecessor` already
use internally, just starting from `root` instead of from an arbitrary
node.

**Gotcha:** an empty tree (`root == null`) must return `null`, not throw —
these are the entry-returning cousins of `firstKey`/`lastKey`, which *do*
throw `NoSuchElementException` on empty maps. Mixing the two contracts up
(throwing from `firstEntry`, or silently returning `null` from `firstKey`)
is a real, easy-to-make mistake because the JDK deliberately gives the
`Entry`-returning and `K`-returning members of the same pair different
empty-map behavior.

```java
    static <K,V> Entry<K,V> getFirstEntry(Entry<K,V> root) {
        Entry<K,V> p = root;
        if (p != null) {
            while (p.left != null) {
                p = p.left;
            }
        }
        return p;
    }

    static <K,V> Entry<K,V> getLastEntry(Entry<K,V> root) {
        Entry<K,V> p = root;
        if (p != null) {
            while (p.right != null) {
                p = p.right;
            }
        }
        return p;
    }

    public Entry<K,V> firstEntry() {
        return getFirstEntry(root);
    }

    public Entry<K,V> lastEntry() {
        return getLastEntry(root);
    }
```

> **Boxed definition — firstEntry/lastEntry.** The leftmost/rightmost node
> reachable from `root` by following only `left`/only `right` pointers,
> returned as `null` (never a thrown exception) when the tree is empty.
> O(log n) — height of the tree, same bound as any other rooted walk.

## floorEntry / ceilingEntry / lowerEntry / higherEntry

**Mental model:** all four are one algorithm with the comparison direction
and tie-breaking flipped. Walking down from `root`, at every node you know
immediately whether that node itself could be the answer (a single
`compare` call), and if not, which subtree to descend into next. The trick
is that "not the answer, keep going" doesn't mean "forget this node" — for
`floorEntry`/`lowerEntry` every node you pass that's still `<=`/`<` the
target key is a *candidate* answer, and the deepest, rightmost such
candidate on the path is the true answer once the walk falls off the
bottom of the tree. This is exactly the "last known valid answer" shape of
classic binary search on a sorted array — you don't stop at the first
comparison that goes your way, you remember it and keep narrowing, because
a later, better candidate might still be found deeper in. The tree's
sortedness guarantees that whichever candidate survives to the end of the
walk is the closest one.

**Why it exists as its own algorithm:** `NavigableMap`'s contract requires
these four lookups to run in O(log n) with a single descent. A tempting
shortcut — call `getEntry(key)`, and if it's a hit use it, otherwise call
`successor`/`predecessor` once to step to the neighboring key — looks
correct on the surface and is the wrong simplification (see Pitfalls
below): it silently does a full second O(log n) walk even when the first
one already told you enough to answer directly, and it gets absent-key
edge cases wrong at the boundaries. The real `java.util.TreeMap` never
does this; `getFloorEntry`/`getCeilingEntry`/`getLowerEntry`/
`getHigherEntry` are each their own single-descent private methods.

**When to reach for each of the four** — the four differ only in the
comparison operator against the target key, and whether an exact match on
the target key itself counts:

| Method | Relation to key | Exact match on `key` counts? | On absent key, direction of search |
|---|---|---|---|
| `floorEntry(key)` | `<= key`, greatest such | yes | search downward from key |
| `ceilingEntry(key)` | `>= key`, least such | yes | search upward from key |
| `lowerEntry(key)` | `< key`, greatest such | no — strict | search downward from key |
| `higherEntry(key)` | `> key`, least such | no — strict | search upward from key |

Present key: `floorEntry`/`ceilingEntry` on a key that's in the map both
return that exact entry (since `<=`/`>=` include equality); `lowerEntry`/
`higherEntry` skip past it to the true strict neighbor. Absent key below
the map's minimum: `floorEntry`/`lowerEntry` return `null` (nothing is
`<=`/`<` a value smaller than everything present); `ceilingEntry`/
`higherEntry` return the minimum entry. Symmetric at the maximum end.

**How it works — the real descent algorithm.** Take `getFloorEntry` as the
representative case (the other three are the same shape with the compared
operator and branch direction mirrored):

```java
    final Entry<K,V> getFloorEntry(K key) {
        Entry<K,V> p = root;
        while (p != null) {
            int cmp = compare(key, p.key);
            if (cmp > 0) {
                if (p.right != null) {
                    p = p.right;
                } else {
                    return p;
                }
            } else if (cmp < 0) {
                if (p.left != null) {
                    p = p.left;
                } else {
                    Entry<K,V> parent = p.parent;
                    Entry<K,V> ch = p;
                    while (parent != null && ch == parent.left) {
                        ch = parent;
                        parent = parent.parent;
                    }
                    return parent;
                }
            } else {
                return p;
            }
        }
        return null;
    }

    final Entry<K,V> getCeilingEntry(K key) {
        Entry<K,V> p = root;
        while (p != null) {
            int cmp = compare(key, p.key);
            if (cmp < 0) {
                if (p.left != null) {
                    p = p.left;
                } else {
                    return p;
                }
            } else if (cmp > 0) {
                if (p.right != null) {
                    p = p.right;
                } else {
                    Entry<K,V> parent = p.parent;
                    Entry<K,V> ch = p;
                    while (parent != null && ch == parent.right) {
                        ch = parent;
                        parent = parent.parent;
                    }
                    return parent;
                }
            } else {
                return p;
            }
        }
        return null;
    }

    final Entry<K,V> getLowerEntry(K key) {
        Entry<K,V> p = root;
        while (p != null) {
            int cmp = compare(key, p.key);
            if (cmp > 0) {
                if (p.right != null) {
                    p = p.right;
                } else {
                    return p;
                }
            } else {
                if (p.left != null) {
                    p = p.left;
                } else {
                    Entry<K,V> parent = p.parent;
                    Entry<K,V> ch = p;
                    while (parent != null && ch == parent.left) {
                        ch = parent;
                        parent = parent.parent;
                    }
                    return parent;
                }
            }
        }
        return null;
    }

    final Entry<K,V> getHigherEntry(K key) {
        Entry<K,V> p = root;
        while (p != null) {
            int cmp = compare(key, p.key);
            if (cmp < 0) {
                if (p.left != null) {
                    p = p.left;
                } else {
                    return p;
                }
            } else {
                if (p.right != null) {
                    p = p.right;
                } else {
                    Entry<K,V> parent = p.parent;
                    Entry<K,V> ch = p;
                    while (parent != null && ch == parent.right) {
                        ch = parent;
                        parent = parent.parent;
                    }
                    return parent;
                }
            }
        }
        return null;
    }

    public Entry<K,V> floorEntry(K key) {
        return getFloorEntry(key);
    }

    public Entry<K,V> ceilingEntry(K key) {
        return getCeilingEntry(key);
    }

    public Entry<K,V> lowerEntry(K key) {
        return getLowerEntry(key);
    }

    public Entry<K,V> higherEntry(K key) {
        return getHigherEntry(key);
    }
```

Read `getFloorEntry` as two separate jobs stitched together. While `cmp >
0` (the current node is `< key`, a valid floor candidate) the walk goes
right looking for something even closer, but if there's no right child the
current node *is* the answer immediately — no candidate-tracking variable
needed, because going right was always trying to improve on a node that's
already a valid answer. While `cmp < 0` (current node is `> key`, not a
valid floor candidate) the walk goes left hunting for something small
enough, but if there's no left child, the current node itself is not
usable — the answer, if any, is the nearest *ancestor* on the walk that
this node hangs off as a right descendant, which the `parent`-climbing
loop finds by walking up while the child pointer used to get here was
`.left` (i.e., undoing every left turn until a right turn, or the root, is
found). `cmp == 0` is the trivial exact-match return. `getCeilingEntry` is
the mirror image (swap left/right, swap the climb condition to `.right`).
`getLowerEntry`/`getHigherEntry` are `getFloorEntry`/`getCeilingEntry`
with the `cmp == 0` branch folded into the "not yet close enough, keep
going" side instead of returning immediately — that's the entire
difference between inclusive and strict.

No diagram — this is a description of control flow through an existing
tree shape, not a new structural relationship; the rotation and
deletion-case diagrams from earlier parts already show every tree shape
these methods walk over.

**Demo** (hand-traced, not compiled — output shown is worked by hand
against the algorithm above, not from running `javac`). Build the tree by
inserting `10, 5, 15, 3, 7, 12, 20` into an empty `MyTreeMap<Integer,
String>` via `put`, using the values `"a".."g"` in insertion order. After
red-black rebalancing (parts 1-2) the resulting shape is:

```
              10(B)
            /      \
          5(B)      15(B)
         /   \      /    \
       3(R)  7(R) 12(R)  20(R)
```

```java
MyTreeMap<Integer,String> m = new MyTreeMap<>();
m.put(10, "a"); m.put(5, "b"); m.put(15, "c"); m.put(3, "d");
m.put(7, "e");  m.put(12, "f"); m.put(20, "g");

System.out.println(m.floorEntry(7));    // 7=e   (present key, exact match)
System.out.println(m.floorEntry(9));    // 7=e   (absent, nearest below)
System.out.println(m.floorEntry(2));    // null  (below the minimum, 3)
System.out.println(m.ceilingEntry(7));  // 7=e   (present key, exact match)
System.out.println(m.ceilingEntry(9));  // 10=a  (absent, nearest above)
System.out.println(m.ceilingEntry(21)); // null  (above the maximum, 20)
System.out.println(m.lowerEntry(7));    // 5=b   (present key, strict, skips 7)
System.out.println(m.lowerEntry(9));    // 7=e   (absent, nearest strictly below)
System.out.println(m.lowerEntry(3));    // null  (3 is the minimum, nothing strictly below)
System.out.println(m.higherEntry(7));   // 10=a  (present key, strict, skips 7)
System.out.println(m.higherEntry(9));   // 10=a  (absent, nearest strictly above)
System.out.println(m.higherEntry(20));  // null  (20 is the maximum, nothing strictly above)
```

Trace `floorEntry(9)` against `getFloorEntry` to see the candidate-climb
happen: start at `10` (`cmp = compare(9,10) < 0`, not a candidate, go
left, since `10.left = 5` exists); at `5` (`cmp = compare(9,5) > 0`,
candidate, go right, since `5.right = 7` exists); at `7` (`cmp =
compare(9,7) > 0`, candidate, want to go right, but `7.right == null`) —
return `7` immediately, because a node with `cmp > 0` and no right child is
already the best candidate reachable, no parent-climb needed. Now trace
`ceilingEntry(9)`: start at `10` (`cmp < 0`, candidate, go left since `10.left`
exists); at `5` (`cmp > 0`, not a candidate, want to go right, but
`5.right = 7` exists, so go right); at `7` (`cmp > 0`, not a candidate, want
to go right, but `7.right == null`) — fall into the parent-climb: `ch = 7`,
`parent = 5`; is `ch == parent.right`? Yes (`5.right == 7`), so keep
climbing: `ch = 5`, `parent = 10`; is `ch == parent.right`? No, `5 ==
10.left`, stop climbing — return `parent`, which is `10`. Matches the
expected `10=a`.

## Pitfalls

**Wrong — "getEntry then step once":**

```java
    // WRONG: looks reasonable, is not what the JDK does, and breaks on
    // absent keys past the tree's edges.
    public Entry<K,V> floorEntryWrong(K key) {
        Entry<K,V> e = getEntry(key);
        if (e != null) {
            return e;                 // exact hit — fine so far
        }
        // No exact match: try to find "the entry that would be just
        // below key" by starting from the nearest thing getEntry found...
        // except getEntry returns null on a miss, so there is no node to
        // start stepping from. The only fix is a second, different
        // descent to find an insertion point, then decide whether to
        // step via successor/predecessor from there — which is either a
        // second full O(log n) walk bolted onto the first one (double
        // the work getFloorEntry needs), or, if implemented carelessly
        // by calling successor(getEntry(key)) directly, simply wrong,
        // because getEntry(key) is null and successor(null) is undefined.
        return null; // <-- silently wrong for every absent key
    }
```

Calling `floorEntryWrong(9)` on the demo tree returns `null` instead of the
correct `7=e` — the method never even attempts the "closest key below"
search once the exact-match path fails, because there is no live `Entry`
node to anchor a `successor`/`predecessor` step from. Patching it to run a
*second* descent to find an insertion point, then call `successor` or
`predecessor` once, would fix the answer but still cost two O(log n)
passes instead of one, and is easy to get backwards (calling `successor`
where `predecessor` was needed, or vice versa) since the mapping from
"floor" to "step direction" is not the same for all four methods and none
of the four benefit from the extra pass.

**Right:** the single-descent `getFloorEntry`/`getCeilingEntry`/
`getLowerEntry`/`getHigherEntry` shown above — one O(log n) walk, tracking
the best-so-far candidate implicitly via the parent-climb, with no second
pass and no dependency on `getEntry` succeeding.

## Cheat sheet

| Method | Relation | Present key `k` | Absent key below min | Absent key above max |
|---|---|---|---|---|
| `firstEntry()` | leftmost | — | — (empty tree → `null`) | — |
| `lastEntry()` | rightmost | — | — (empty tree → `null`) | — |
| `floorEntry(k)` | `<= k`, max | returns entry for `k` | `null` | max entry |
| `ceilingEntry(k)` | `>= k`, min | returns entry for `k` | min entry | `null` |
| `lowerEntry(k)` | `< k`, max | returns predecessor of `k` | `null` | max entry |
| `higherEntry(k)` | `> k`, min | returns successor of `k` | min entry | `null` |

All six: O(log n) (height of the red-black tree), single descent, return
the live internal `Entry<K,V>` (this build's choice, see above) or `null`
on an empty/exhausted result — never throw.

## Self-test

1. **Q:** Why do `floorEntry`/`ceilingEntry` return the exact entry for a
   present key, but `lowerEntry`/`higherEntry` don't?
   <details><summary>Answer</summary>`floor`/`ceiling` use `<=`/`>=`,
   which include equality; `lower`/`higher` use strict `<`/`>`, which
   exclude the key itself by definition.</details>

2. **Q:** What does `firstEntry()` return on an empty `MyTreeMap`, and how
   does that differ from `firstKey()`'s contract?
   <details><summary>Answer</summary>`firstEntry()` returns `null`;
   `firstKey()` (not implemented in this file, but present in the real
   `NavigableMap`/`SortedMap` API) throws `NoSuchElementException` on an
   empty map instead. The `Entry`-returning and `K`-returning members of
   the pair deliberately disagree on empty-map behavior.</details>

3. **Q:** In `getFloorEntry`, when `cmp > 0` at node `p` and `p.right ==
   null`, why is `p` returned immediately with no parent-climb, while the
   `cmp < 0` branch with `p.left == null` needs a parent-climb loop?
   <details><summary>Answer</summary>When `cmp > 0`, `p` is already `<
   key` — a valid floor candidate — and going right was only an attempt
   to find something even closer; no right child means `p` is the best
   reachable answer, no need to look further. When `cmp < 0`, `p` is `>
   key` — not usable — so the answer, if any, must be an ancestor; the
   climb undoes left turns until a right turn (or the root) is
   found.</details>

4. **Q:** Why is `floorEntry(key)` on a key strictly smaller than every key
   in the map guaranteed to return `null`?
   <details><summary>Answer</summary>No node in the tree is `<= key`, so
   there is no valid floor candidate anywhere on the descent; the walk's
   parent-climb runs out at the root without ever having set `cmp > 0`,
   so it falls through to the trailing `return null;`.</details>

5. **Q:** What is wrong with implementing `floorEntry` as `getEntry(key) !=
   null ? getEntry(key) : predecessor-step-from-somewhere`?
   <details><summary>Answer</summary>On a miss, `getEntry(key)` returns
   `null`, giving no live node to step a predecessor from without a
   second, separate descent to find an insertion point — doubling the
   work a single-descent algorithm needs, and easy to get the step
   direction (successor vs. predecessor) backwards per method.</details>

6. **Q:** Why do these six methods return the internal `Entry<K,V>`
   directly instead of a `SimpleImmutableEntry` snapshot, unlike the real
   `java.util.TreeMap`?
   <details><summary>Answer</summary>This build's `Entry<K,V>` already has
   package-visible mutable fields with no snapshot wrapper used anywhere
   else in the class (parts 1-3); introducing one only here would make
   this the sole place in the whole build with two entry representations
   in flight, at the cost of the JDK's defensive-copy guarantee against
   external mutation via `setValue`.</details>

7. **Q:** Trace `lowerEntry(3)` on the demo tree (`10,5,15,3,7,12,20`).
   Why is the result `null`?
   <details><summary>Answer</summary>`3` is the minimum key in the tree.
   `getLowerEntry` only ever returns a node with `cmp > 0` (strictly `<
   key`) or an ancestor found via the parent-climb after a `cmp <= 0`
   dead end; since nothing in the tree is strictly less than `3`, no
   candidate is ever produced and the walk falls through to `return
   null;`.</details>

8. **Q:** Does `ceilingEntry(key)` ever need to look at `key`'s subtree
   more than once?
   <details><summary>Answer</summary>No — it is a single top-to-bottom
   descent; each node is visited at most once, and the parent-climb (when
   needed) revisits ancestors already on the path just walked, not new
   nodes, keeping the whole operation O(log n).</details>

---

**Leaves covered:** 4.6.1 (part 4 of 6) (1 leaf, shared across 6 files)
**Leaves deferred:** none — the iterator continues in 04c2, then 04d
**Diagrams included:** none
**Target version:** Java 21 LTS
**Lines:** 475
