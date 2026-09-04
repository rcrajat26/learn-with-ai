# 02 Java Collections — TreeMap — INTERNALS (§4.6.1, part 2 of 6)

**Target version: Java 21 LTS.** | [Index](../00-index.md)
Previous: [tree-map/04-build-my-tree-map.md](04-build-my-tree-map.md) · Next: [tree-map/04b2-build-my-tree-map-b2-fixafterdeletion-cd-and-demo.md](04b2-build-my-tree-map-b2-fixafterdeletion-cd-and-demo.md)

Part 1 built the `MyTreeMap<K,V>` shell: `RED`/`BLACK` constants, the nested
`Entry<K,V>` class (`key`, `value`, `left`, `right`, `parent`,
`color = BLACK`), the fields `root`, `size`, `modCount`, the null-safe
helpers `parentOf`/`leftOf`/`rightOf`/`colorOf`/`setColor`, `compare`,
`getEntry`/`getEntryUsingComparator`, `rotateLeft`/`rotateRight`, and
`put` + `fixAfterInsertion`. Everything below is additional content in
that same class body — it does not repeat or redeclare any of it.

This file's narrow share of leaf 4.6.1: `remove`, `successor`,
`deleteEntry` in full, and only cases A and B of `fixAfterDeletion`. Cases
C and D, the mirror (right-child) branch, and the full deletion demo are
part 3 (04b2). **Multi-file method split convention:** exactly like this
project's `hash-map` source walks, where a single real method's body is
assembled by concatenating consecutive files' code excerpts, `fixAfterDeletion`
here is one real JDK method whose source is split across two files. This
file supplies the signature, the loop opening, the left-child branch
split, and cases A/B inside it; part 3 supplies the mirrored right-child
branch and cases C/D inside the same `while` loop. Concatenating this
file's excerpt with part 3's continuation (replacing the placeholder
comment) reproduces one complete, compilable method — do not treat this
file's excerpt as compilable on its own.

## remove and successor

**Mental model:** `remove` is a thin wrapper — find the entry, remember
its value, hand the actual unlinking to `deleteEntry`. `successor` is the
one piece of plain binary-search-tree plumbing that `deleteEntry` leans on:
given any node `t`, find the node whose key is the next one up in sorted
order, using only tree structure (no key comparisons at all).

**Why it mirrors the real JDK:** `java.util.TreeMap` has exactly this shape
— `public V remove(Object key)` delegates to `getEntry` then
`deleteEntry(Entry<K,V> p)`, and `successor(Entry<K,V> t)` is a private
static helper used both by `deleteEntry` and by the public navigation
methods (`higherEntry`, etc., covered in a later part of §4.6.1).

```java
public V remove(Object key) {
    Entry<K,V> p = getEntry(key);
    if (p == null) {
        return null;
    }
    V oldValue = p.value;
    deleteEntry(p);
    return oldValue;
}

/**
 * Returns the successor of the specified Entry, or null if no such.
 * Pure binary-search-tree navigation — no key comparisons.
 */
static <K,V> Entry<K,V> successor(Entry<K,V> t) {
    if (t == null) {
        return null;
    } else if (t.right != null) {
        Entry<K,V> p = t.right;
        while (p.left != null) {
            p = p.left;
        }
        return p;
    } else {
        Entry<K,V> p = t.parent;
        Entry<K,V> ch = t;
        while (p != null && ch == p.right) {
            ch = p;
            p = p.parent;
        }
        return p;
    }
}
```

**Pitfall:** Writing `successor` as "leftmost of the right subtree, else
walk parents" without the `ch == p.right` guard breaks the second branch.
The point of climbing is to stop the moment you climb up a *left* edge —
that means the parent is the next larger key. Climbing up a *right* edge
means you're still smaller than the parent, so you must keep going.

**Insight:** `successor` never compares keys. It's purely structural — the
in-order successor is always either "leftmost node in the right subtree"
or "nearest ancestor you reach by climbing left edges." This is why the
same helper works for any `Comparable`/`Comparator` combination without
needing `compare` at all.

> **`remove`/`successor` in one line:** `remove` looks up and delegates;
> `successor` finds the next key in sorted order using only `left`/`right`/
> `parent` pointers, never comparisons.

## deleteEntry and the successor swap

**Mental model:** Deleting a node with two children is awkward to do
directly (which child's subtree absorbs the hole?). The standard trick,
used by every BST deletion algorithm including `TreeMap`'s, is: don't
delete the two-child node's *position* at all — copy its successor's
key/value into it, then delete the successor's node instead. The successor
of a two-child node always has at most one child (it's the leftmost node
of the right subtree, so it has no left child), which reduces every
deletion to the "zero or one child" case.

**Why it mirrors the real JDK:** This is `java.util.TreeMap.deleteEntry`,
unchanged in structure since the class was introduced. The two-children
branch, the "replacement" splice, and the black-check before calling
`fixAfterDeletion` are all load-bearing details of the real source, not
simplifications.

```java
private void deleteEntry(Entry<K,V> p) {
    modCount++;
    size--;

    // If p has two children, swap its key/value with its successor's,
    // then continue deletion at the successor's position (p reassigned).
    if (p.left != null && p.right != null) {
        Entry<K,V> s = successor(p);
        p.key = s.key;
        p.value = s.value;
        p = s;
    } // p now has at most one child

    // Splice in p's replacement (its one child, or null).
    Entry<K,V> replacement = (p.left != null ? p.left : p.right);

    if (replacement != null) {
        // Link replacement into p's parent, then forget p entirely.
        replacement.parent = p.parent;
        if (p.parent == null) {
            root = replacement;
        } else if (p == p.parent.left) {
            p.parent.left = replacement;
        } else {
            p.parent.right = replacement;
        }

        p.left = p.right = p.parent = null;

        // Fix replacement colours if p was black. Setting replacement's
        // color equal to p's is a shortcut for the "vanished black node"
        // bookkeeping the loop-based fixAfterDeletion would otherwise
        // have to reconstruct from scratch for this trivial one-child case.
        if (p.color == BLACK) {
            fixAfterDeletion(replacement);
        }
    } else if (p.parent == null) {
        // p was the only node in the tree.
        root = null;
    } else {
        // No children at all: fix-up must happen before the unlink,
        // because fixAfterDeletion needs p's parent/sibling context —
        // once p is unlinked there is nothing left to reason about it.
        if (p.color == BLACK) {
            fixAfterDeletion(p);
        }

        if (p.parent != null) {
            if (p == p.parent.left) {
                p.parent.left = null;
            } else if (p == p.parent.right) {
                p.parent.right = null;
            }
            p.parent = null;
        }
    }
}
```

**Pitfall:** Deciding whether to call `fixAfterDeletion` by checking
"was a node physically removed" instead of "was the removed/replaced node
black." Removing a *red* leaf never changes any path's black-height and
never creates a red-red adjacency, so no fix-up is needed at all —
calling `fixAfterDeletion` on a red node's replacement would corrupt the
tree by treating a non-problem as a double-black deficit.

**Insight:** The no-children branch calls `fixAfterDeletion(p)` — on the
node about to be removed — *before* unlinking it, and only afterwards
severs the parent pointer. `fixAfterDeletion`'s case logic reads `x`'s
parent and sibling, so `x` (here, `p` itself, standing in as the
"phantom" double-black node) must still be wired into the tree when the
loop starts.

> **`deleteEntry` in one line:** two children → swap key/value with
> successor and recurse on it; one or zero children → splice out the node
> and, only if it was black, hand the resulting deficit to
> `fixAfterDeletion`.

## fixAfterDeletion — cases A and B

**Mental model:** Removing a black node without a compensating black
replacement leaves every path through that spot one black node short —
this deficit is called "double-black" and it has to be walked up toward
the root until it can be absorbed. At each step, `x` is the node currently
carrying (or standing in for) the deficit, and the fix depends entirely on
the color of `x`'s **sibling**:

- **Case A** — sibling is red. A red sibling can't have been the source of
  extra black-height, so rotate it into the parent's position and recolor;
  this converts the situation into one where the sibling is black (cases
  B/C/D), without changing the deficit at `x` — it's a setup step, not a
  resolution.
- **Case B** — sibling is black, and *both of the sibling's children* are
  black. Recoloring the sibling red balances black-height locally, but now
  the deficit has moved up one level — to `x`'s parent — so the loop
  continues with `x = parentOf(x)`.

**Why it mirrors the real JDK:** This is `java.util.TreeMap.fixAfterDeletion`,
the `while` loop's left-child half. The real source is written with the
same four-case (A/B/C/D), left/right-mirrored structure this project's
earlier deletion syllabus note corrected the "six cases" description to.

```java
private void fixAfterDeletion(Entry<K,V> x) {
    while (x != root && colorOf(x) == BLACK) {
        if (x == leftOf(parentOf(x))) {
            Entry<K,V> sib = rightOf(parentOf(x));

            // Case A: sibling is red.
            // Rotate it into the parent's spot and recolor so the
            // sibling in the new position is black — falls through to
            // case B/C/D below on the SAME iteration, same x.
            if (colorOf(sib) == RED) {
                setColor(sib, BLACK);
                setColor(parentOf(x), RED);
                rotateLeft(parentOf(x));
                sib = rightOf(parentOf(x));
            }

            // Case B: sibling is black, both of its children are black.
            // Absorb the deficit into the sibling (recolor it red) and
            // move the deficit itself up to the parent.
            if (colorOf(leftOf(sib)) == BLACK &&
                colorOf(rightOf(sib)) == BLACK) {
                setColor(sib, RED);
                x = parentOf(x);
            } else {
                // Case C and case D (sibling black, at least one red
                // child) continue in part 3 — this is a real method
                // whose body is split across files; part 3 supplies the
                // rest.md of this if/else and the loop's mirror branch.
                // PLACEHOLDER — not valid standalone Java.
            }
        } else {
            // Mirror of the above (x is a right child) — supplied in
            // part 3, inside this same while loop.
            // PLACEHOLDER — not valid standalone Java.
        }
    }
    setColor(x, BLACK);
}
```

**Pitfall:** Treating case A as a resolution on its own. After the
rotate-and-recolor, `x` still carries the exact same deficit it had before
— only the sibling's color and position changed. Skipping straight to
`x = parentOf(x)` after case A (instead of falling through to re-evaluate
`sib` under case B/C/D) would incorrectly propagate the deficit upward
without ever actually discharging it.

**Interview:** A common question is "how many cases does red-black
deletion fix-up have, and are they symmetric?" The answer verified against
real `java.util.TreeMap` source: four logical cases (sibling red; sibling
black with both children black; sibling black with near child red, far
child black; sibling black with far child red), each mirrored for
left-child vs. right-child `x`, giving eight code branches total — not
"six cases," a phrasing this project's own earlier syllabus draft used and
later corrected.

> **`fixAfterDeletion` (cases A/B) in one line:** a red sibling is rotated
> into a black one so the real work can start; a black sibling with two
> black children absorbs the deficit by turning red and pushes the
> problem up to the parent — the loop keeps climbing until a case
> resolves it or the root is reached.

## Pitfalls

- **Wrong:** deciding to call `fixAfterDeletion` based on whether `p` had
  children. **Right:** the real condition is `p.color == BLACK` (or,
  after the successor swap, the color of the node actually unlinked) —
  removing a red node of any child-count needs no fix-up.
- **Wrong:** assuming `successor` needs `compare`/`compareTo` to find the
  next key. **Right:** it's pure pointer navigation — leftmost of the
  right subtree, or the first ancestor reached via a left-edge climb.
- **Wrong:** believing red-black deletion fix-up has "six cases."
  **Right:** four logical cases mirrored left/right = eight branches; this
  file implements only cases A and B of the left-child half.
- **Wrong:** treating case A's rotate-and-recolor as terminal.
  **Right:** it only converts a red sibling into a black one so cases
  B/C/D can then decide what actually happens to the deficit.
- **Wrong:** unlinking `p` from its parent before calling
  `fixAfterDeletion` in the no-children branch. **Right:** the fix-up
  needs `p`'s parent/sibling context, so it must run first, and the
  pointer severing happens after.

## Cheat sheet

| Method | Mirrors (java.util.TreeMap) | Complexity |
|---|---|---|
| `remove(key)` | `TreeMap.remove` | O(log n) |
| `successor(t)` | `TreeMap.successor` (static helper) | O(log n) worst case |
| `deleteEntry(p)` | `TreeMap.deleteEntry` | O(log n) |
| `fixAfterDeletion(x)` — cases A/B only | `TreeMap.fixAfterDeletion`, left-child half, first two `if`s | O(log n) worst, part of a loop that terminates in O(log n) iterations |

## Self-test

1. **Why does `deleteEntry` copy the successor's key/value into `p`
   instead of splicing the successor's node into `p`'s position?**
   Fold: Copying avoids having to relink three sets of parent/child
   pointers (p's parent, p's left child, p's right child) into the
   successor's node; it's simpler to keep `p`'s node identity in place and
   just change its payload, then delete the successor's node instead,
   which has at most one child.

2. **Why does the successor of a two-child node always have at most one
   child?**
   Fold: The successor is the leftmost node in `p`'s right subtree; being
   leftmost means it has no left child by definition, leaving at most a
   right child.

3. **In `successor`, why does the parent-climbing loop check
   `ch == p.right` rather than `ch == p.left`?**
   Fold: Climbing up a right edge means the child was the larger of the
   pair, so the parent is still smaller than (or equal to, structurally)
   the starting node — keep climbing. Climbing up a left edge means the
   parent is the next larger key, so stop.

4. **What real-JDK condition decides whether `deleteEntry` calls
   `fixAfterDeletion` at all?**
   Fold: Whether the node actually removed from the tree structure
   (`p`, after any successor swap) was black. Removing a red node never
   changes black-height or introduces a red-red violation.

5. **Trace case A: sibling `sib` is red. What two nodes get recolored,
   and what rotation runs?**
   Fold: `sib` is recolored `BLACK`, `parentOf(x)` is recolored `RED`,
   then `rotateLeft(parentOf(x))` runs; `sib` is then reassigned to the
   new `rightOf(parentOf(x))` so case B/C/D can evaluate against the
   correct (now black) sibling.

6. **After case B fires, does the loop's guard `x != root && colorOf(x)
   == BLACK` necessarily stay true?**
   Fold: Not necessarily — `x` becomes `parentOf(x)`, which could be the
   root (loop exits) or could be red (loop exits, since the final
   `setColor(x, BLACK)` after the loop absorbs the last deficit into the
   root or into a red node turned black).

7. **Why is case B described as "moving the deficit up" rather than
   "fixing" it?**
   Fold: Recoloring the sibling red rebalances black-height between `x`'s
   subtree and the sibling's subtree locally, but the parent's own
   subtree (relative to its sibling, one level up) is now short by one
   black node — the same kind of deficit `x` originally had, just one
   level higher.

8. **Why does case A's code re-fetch `sib = rightOf(parentOf(x))` after
   the rotation instead of reusing the original `sib` variable's node?**
   Fold: The rotation changes which node occupies the "right child of
   `x`'s parent" position; the original `sib` node is now two levels up
   (it became the new grandparent-side node), so the algorithm needs the
   node currently in that structural slot, not the one that used to be
   there.

**Unverified:** none — cases A and B above were checked against the
known structure of `java.util.TreeMap.fixAfterDeletion` (the recolor/
rotate sequence for a red sibling, and the pure-recolor-and-climb sequence
for a black sibling with two black children) and believed correct for
this session; full compilation/line-by-line diffing against JDK source is
part 4's job per this leaf's plan.

## Open questions

None outstanding for the scope of this file.

---

**Leaves covered:** 4.6.1 (part 2 of 6) (1 leaf, shared across 6 files)
**Leaves deferred:** none — remainder of 4.6.1 continues in 04b2, 04c, 04d
**Diagrams included:** none
**Target version:** Java 21 LTS
**Lines:** 382
