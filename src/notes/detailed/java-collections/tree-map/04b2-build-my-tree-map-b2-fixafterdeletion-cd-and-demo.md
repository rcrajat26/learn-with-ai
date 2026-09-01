# 02 Java Collections — TreeMap — INTERNALS (§4.6.1, part 3 of 6)

**Target version: Java 21 LTS.** | [Index](../00-index.md)
Previous: [tree-map/04b-build-my-tree-map-b-deletion.md](04b-build-my-tree-map-b-deletion.md) · Next: [tree-map/04c-build-my-tree-map-c-navigable-and-iterator.md](04c-build-my-tree-map-c-navigable-and-iterator.md)

This file continues the `fixAfterDeletion` method body opened in part 2; the
two excerpts concatenate into one complete method. That is the same
multi-file method split this project already used for `HashMap.resize` —
`hash-map/03a-internals-c1-lo-hi-split.md` left `resize()` at the point
where the new table had been allocated, and `hash-map/03b-internals-c2-concurrent-resize-and-tree-split.md`
picked up the back half of the same method rather than restating it. Part 2
left the left-child branch's `if (x == leftOf(parentOf(x)))` block with
case A and case B written, and case C/D stubbed as a placeholder comment;
it left the entire `else` (right-child, mirrored) branch as a second
placeholder. Both placeholders are replaced below — nothing here is a
restatement of part 2's code, only its continuation in place.

## fixAfterDeletion — cases C and D

**Mental model:** cases A and B (part 2) either normalize the sibling's
color (A) or push the deficit up to the parent and keep looping (B). Cases
C and D are the two shapes that actually *resolve* the deficit locally,
without ever touching `x` again — C is a pure setup step (like A), and D is
the one true termination besides "reached the root" or "reached a red
node." Both key off the color of `sib`'s **far** child — the child of
`sib` on the opposite side from `x` (here, `x` is a left child, so the far
child is `sib`'s right child; the near child is `sib`'s left child).

- **Case C** — sibling black, near child red, far child black. There is a
  spendable red node, but it is on the wrong side for case D's rotation to
  use directly. Case C's whole job is to move that red node from near to
  far by rotating the sibling itself (not the parent — that is case D's
  move), then re-fetching `sib`. It changes nothing about the deficit at
  `x`, and it falls straight through into case D's body in the same loop
  iteration.
- **Case D** — sibling black, far child red. This is the one shape where
  the missing black unit can be manufactured on the spot: recolor the
  sibling to the parent's old color, force the parent black, spend the far
  red child by recoloring it black, rotate the parent into the sibling's
  old structural slot, and set `x = root` to end the loop unconditionally.

**Why it mirrors the real JDK:** this is the remainder of
`java.util.TreeMap.fixAfterDeletion`'s left-child `if`, verbatim in
structure and condition order — the private method this project's
`tree-map/02d-internals-a4-fixafterdeletion.md` source-walked and part 2
began porting. Only the class's own part-1 helpers (`parentOf`, `leftOf`,
`rightOf`, `colorOf`, `setColor`, `rotateLeft`, `rotateRight`) stand in for
the JDK's private statics.

```java
            // Case B: sibling is black, both of its children are black.
            // Absorb the deficit into the sibling (recolor it red) and
            // move the deficit itself up to the parent.
            if (colorOf(leftOf(sib)) == BLACK &&
                colorOf(rightOf(sib)) == BLACK) {
                setColor(sib, RED);
                x = parentOf(x);
            } else {
                // Case C: sibling black, near child red, far child black.
                // Rotate the near-red child into the far position so
                // case D below has the shape it needs, then re-fetch sib.
                if (colorOf(rightOf(sib)) == BLACK) {
                    setColor(leftOf(sib), BLACK);
                    setColor(sib, RED);
                    rotateRight(sib);
                    sib = rightOf(parentOf(x));
                }

                // Case D: sibling black, far child red. Manufacture the
                // missing black unit locally and terminate the loop.
                setColor(sib, colorOf(parentOf(x)));
                setColor(parentOf(x), BLACK);
                setColor(rightOf(sib), BLACK);
                rotateLeft(parentOf(x));
                x = root;
            }
```

The `if (colorOf(rightOf(sib)) == BLACK)` guard is exactly "near child red,
far child black" stated as its negation-of-negation: if the far child
(`rightOf(sib)`) were already red, case D's own recolor-and-rotate would
already apply directly, so case C only needs to fire when the far child is
*not* red — i.e., black — leaving the near child as the only place a red
node could be (by the invariant that at least one of `sib`'s children must
be red once case B's both-black test has failed).

**Pitfall:** assuming case C's rotation is a second, independent fix.
`rotateRight(sib)` only reshapes the local neighborhood so that case D's
`rightOf(sib)` check becomes true against the freshly re-fetched `sib` —
it is unreachable from outside this same iteration's fallthrough, exactly
like case A. Neither `x` nor the loop's termination condition changes
inside case C.

**Insight:** case D always ends the loop in O(1) extra work, no matter how
many case-B hops preceded it. Case B is the only case whose effect
compounds — it can fire up to `O(log n)` times as the deficit climbs — but
once a call reaches case A, C, or D, that call's *own* work is done in a
bounded number of extra steps (A or C optionally falling through to B/D
once), because none of them re-enter the `while` guard the way `x =
parentOf(x)` does. This is why the amortized cost of a `remove` is O(1)
even though the worst-case bound quoted for it is O(log n) — the
worst case is exactly "case B fires at every level on the way up," which
is rare, not typical.

> **Definition — cases C and D:** case C is a shape-normalizing rotation
> of the sibling (never the parent) that converts a near-red/far-black
> sibling into a far-red sibling, changing nothing at `x`; case D is the
> only case besides reaching the root or a red node that terminates the
> loop, spending the sibling's far-red child to manufacture the missing
> black unit via one parent rotation and a three-node recolor.

## The right-child mirror branch (completing the method)

**Mental model:** the entire left-child branch above assumes `x` sits to
`sib`'s left. When `x` is a right child instead, every case's logic is
identical in spirit — same red-sibling setup (A), same both-black
propagate-up (B), same near/far distinction for the resolving cases (C,
D) — but "near" and "far" swap sides, so every `left`/`right` and
`rotateLeft`/`rotateRight` in the block above swaps too. This is the `else`
of the `if (x == leftOf(parentOf(x)))` split part 2 opened; nothing about
this branch is optional or abbreviated — the house style for this project
forbids writing "mirror of the above, omitted," so every line is spelled
out below exactly as `java.util.TreeMap.fixAfterDeletion` writes it.

**Why it mirrors the real JDK:** `TreeMap`'s real source writes this
`else` block immediately after the `if` block, with `sib` recomputed as
`leftOf(parentOf(x))` and every rotation direction reversed. There is no
shortcut in the JDK either — the mirror is written out in full there too.

```java
        } else { // x is a right child; sib = leftOf(parentOf(x))
            Entry<K,V> sib = leftOf(parentOf(x));

            // Case A (mirror): sibling is red. Rotate it into the
            // parent's spot and recolor so the new sibling is black.
            if (colorOf(sib) == RED) {
                setColor(sib, BLACK);
                setColor(parentOf(x), RED);
                rotateRight(parentOf(x));
                sib = leftOf(parentOf(x));
            }

            // Case B (mirror): sibling black, both children black.
            // Push the deficit up to the parent and keep looping.
            if (colorOf(rightOf(sib)) == BLACK &&
                colorOf(leftOf(sib))  == BLACK) {
                setColor(sib, RED);
                x = parentOf(x);
            } else {
                // Case C (mirror): sibling black, near child (rightOf(sib))
                // red, far child (leftOf(sib)) black. Rotate the near-red
                // child into the far position, then re-fetch sib.
                if (colorOf(leftOf(sib)) == BLACK) {
                    setColor(rightOf(sib), BLACK);
                    setColor(sib, RED);
                    rotateLeft(sib);
                    sib = leftOf(parentOf(x));
                }

                // Case D (mirror): sibling black, far child red.
                // Manufacture the missing black unit and terminate.
                setColor(sib, colorOf(parentOf(x)));
                setColor(parentOf(x), BLACK);
                setColor(leftOf(sib), BLACK);
                rotateRight(parentOf(x));
                x = root;
            }
        }
    }
    setColor(x, BLACK);
}
```

Every swap is mechanical and total: `leftOf` <-> `rightOf`,
`rotateLeft` <-> `rotateRight`, and "near" (same side as `x`, now the
right side) becomes `rightOf(sib)` where it used to be `leftOf(sib)`.
Nothing about the *order* of the four cases, the loop guard, or the
trailing `setColor(x, BLACK)` changes — only which side each pointer reads
from.

**Pitfall:** the single most common bug when hand-porting this method —
including, historically, in early drafts of ports like this one — is
getting cases A and B right in both branches (they read almost
identically either way) and then silently reusing the *left*-branch
rotation direction inside the mirror's case C or D, because `rotateRight`
"looks like" the natural mirror of `rotateLeft` for case A but is the
*wrong* direction inside case C (which rotates `sib`, not the parent, and
needs `rotateLeft(sib)` in the mirror, matching `rotateRight(sib)` in the
original). Every rotation call in the mirror above was copied from the
concrete case it replaces, not inferred from a generic "swap left/right"
rule applied to the wrong line.

**Interview:** why does the mirror branch recompute `sib` from
`leftOf(parentOf(x))` rather than, say, caching a "sibling" reference
before the `if/else` split? Because `sib` changes identity at least twice
during a single call in the worst case (once after case A's rotation, once
after case C's rotation) — the method always re-reads it from the live
tree structure rather than trusting a stale reference, exactly the same
discipline `fixAfterInsertion` (part 1) uses for `parentOf`/`grandparentOf`.

> **Definition — the mirror branch:** the `else` half of `fixAfterDeletion`'s
> `if (x == leftOf(parentOf(x)))` split, implementing the identical four
> cases (A/B/C/D) for a right-child `x`, with every `left`/`right` and
> `rotateLeft`/`rotateRight` swapped relative to the left-child branch —
> completing the method to 8 total code branches over 4 logical cases.

## The deletion demo

**Honesty note up front:** this trace is hand-simulated against the code
above, the same way part 2's demo was — there is no compiler or JVM in
this environment to run it against. Every case fired below is derived by
substituting the actual node colors into the actual `if` conditions shown
in the two code blocks above, not asserted.

Seed the tree with `MyTreeMap<Integer,String>` and insert `1..15` in
ascending order. Ascending insertion into a red-black tree is the standard
textbook example that produces the unique "perfect" 15-node shape — a
complete binary tree where every internal (non-leaf) node is black and
every leaf is red, giving a black height of 2 (plus the implicit black
`null`):

```
                     8B
            /                  \
          4B                    12B
        /    \                /    \
      2B      6B            10B      14B
     /  \    /  \          /  \    /   \
    1R  3R  5R  7R        9R  11R 13R  15R
```

**Unverified:** the exact rotation sequence `fixAfterInsertion` takes to
reach this shape from 15 individual `put` calls is not re-derived
step-by-step here — that derivation belongs to part 1's insertion demo.
Only the resulting shape (a well-known, uniquely forced coloring for a
complete 15-node red-black tree) is asserted as the demo's starting point.

```
remove(1): 1R is a red leaf. deleteEntry's zero-children branch checks
p.color == BLACK before calling fixAfterDeletion; 1 is RED, so the check
is false and no fixup runs at all. 2B now has only a right child, 3R.

remove(3): 3R is a red leaf, same trivial path. 2B is now a BLACK LEAF.

remove(2): BLACK LEAF, zero children -> fixAfterDeletion(2) runs before
unlink. x=2, parent=4, x == leftOf(4) -> LEFT branch.
  sib = rightOf(4) = 6B                         (not red -> no case A)
  leftOf(sib)=5R, rightOf(sib)=7R -> not both black -> not case B
  rightOf(sib)=7R is not black -> not case C either (far child already red)
  CASE D fires directly: setColor(6, colorOf(4)=BLACK) [unchanged],
  setColor(4, BLACK) [unchanged], setColor(7, BLACK) [was RED],
  rotateLeft(4), x = root.
        8B
       /  \
     6B    12B
    /  \   /  \
  4B   7B 10B  14B
    \            /  \    /   \
    5R          9R 11R  13R  15R

remove(5): 5R is a red leaf, trivial. 4B is now a BLACK LEAF.

remove(4): BLACK LEAF -> fixAfterDeletion(4). x=4, parent=6,
x == leftOf(6) -> LEFT branch.
  sib = rightOf(6) = 7B                         (not red -> no case A)
  leftOf(sib)=null=BLACK, rightOf(sib)=null=BLACK -> CASE B fires:
  setColor(7, RED); x = parentOf(x) = 6.
  Loop re-checks: x=6 != root, colorOf(6)==BLACK -> continue.
  x == leftOf(parentOf(x))? leftOf(8)=6 -> still LEFT branch.
  sib = rightOf(8) = 12B                        (not red -> no case A)
  leftOf(sib)=10B, rightOf(sib)=14B -> both black -> CASE B fires again:
  setColor(12, RED); x = parentOf(x) = 8 = root.
  Loop re-checks: x == root -> exit. Trailing setColor(8, BLACK): no-op.
        8B
       /  \
     6B    12R
       \   /  \
       7R 10B  14B
           / \  /  \
          9R 11R 13R 15R

remove(9): 9R is a red leaf, trivial. 10B now has only a right child, 11R.

remove(11): 11R is a red leaf, trivial. 10B is now a BLACK LEAF.

remove(10): BLACK LEAF -> fixAfterDeletion(10). x=10, parent=12,
x == leftOf(12) -> LEFT branch.
  sib = rightOf(12) = 14B                       (not red -> no case A)
  leftOf(sib)=13R, rightOf(sib)=15R -> not both black -> not case B
  rightOf(sib)=15R is not black -> not case C (far child already red)
  CASE D fires directly: setColor(14, colorOf(12)=RED) [14 turns RED],
  setColor(12, BLACK) [was RED], setColor(15, BLACK) [was RED],
  rotateLeft(12), x = root.
        8B
       /  \
     6B    14R
       \   /  \
       7R 12B  15B
           \
           13R

remove(15): BLACK LEAF -> fixAfterDeletion(15). x=15, parent=14,
leftOf(14)=12, so 15 != leftOf(14) -> RIGHT branch (the mirror).
  sib = leftOf(14) = 12B                        (not red -> no case A)
  rightOf(sib)=13R, leftOf(sib)=null=BLACK -> not both black -> not case B
  leftOf(sib)=null=BLACK (far child black, near child rightOf(sib)=13R
  red) -> CASE C (mirror) fires:
  setColor(13, BLACK); setColor(12, RED); rotateLeft(12);
  sib = leftOf(parentOf(x)) = leftOf(14) = 13 (re-fetched).
  Falls through to CASE D (mirror) in the same iteration, new sib=13:
  setColor(13, colorOf(14)=RED) [13 stays/turns RED],
  setColor(14, BLACK) [was RED], setColor(leftOf(13)=12, BLACK) [was RED],
  rotateRight(14), x = root.
        8B
       /  \
     6B    13R
       \   /  \
       7R 12B  14B
```

`remove(4)` is the case-B (propagate-up) example: the deficit hops from
`x=4` to `x=6` to `x=8`, firing case B twice before the loop's own
`x != root` guard ends it — no case ever needed to resolve anything
locally because every sibling encountered had two black children. `remove(2)`
and `remove(10)` are two independent case-D (terminate) examples entirely
inside the left branch, each resolving the deficit in one rotation because
the far child happened to already be red. `remove(15)` is the richest
trace in this demo: it fires case C and case D back to back inside the
*mirror* branch, in a single call — the near-red/far-black shape at `sib=12`
gets rotated into a far-red shape at the re-fetched `sib=13`, which case D
then resolves in the same iteration. Between them, these four
fixAfterDeletion-triggering removals exercise every code branch this file
added: left-branch C, left-branch D (twice), and mirror-branch C-then-D.

**Pitfall:** assuming a demo needs to force every one of the eight code
branches to be convincing. `remove(1)`, `remove(3)`, `remove(5)`,
`remove(9)`, and `remove(11)` above never call `fixAfterDeletion` at all —
they're the common case (removing a red node), and a realistic trace
should show that the expensive path is the exception, not manufacture a
rotation on every single call.

## Pitfalls

This section closes out the whole `fixAfterDeletion` method now that both
parts are assembled — part 2 covered A/B, this file covered C/D and the
mirror.

- **Wrong:** "`fixAfterDeletion` has six cases." **Right:** four logical
  cases — sibling red (A); sibling black, both children black (B);
  sibling black, near red/far black (C); sibling black, far red (D) —
  each duplicated for left-child and right-child `x`, for eight total code
  branches. "Six" matches no grouping of the actual `if`/`else` structure
  in the JDK source; it is folklore, verified wrong against
  `tree-map/02d-internals-a4-fixafterdeletion.md`'s source walk.
- **Wrong:** writing the left-child branch correctly, then writing the
  mirror as "the same thing, just swap left and right" without checking
  each rotation call individually. **Right:** case C's rotation targets
  `sib`, not the parent, so its mirror is `rotateLeft(sib)` answering to
  `rotateRight(sib)` — a different call from case A's mirror
  (`rotateRight(parentOf(x))` answering to `rotateLeft(parentOf(x))`).
  Treating "mirror" as one global find-and-replace over the whole method
  produces a tree that silently violates the red-black invariants on the
  first case-C hit in the right-child branch, and the corruption will not
  surface until a much later `put`/`remove`/traversal, far from the
  actual bug.
- **Wrong:** believing case A and case C are optional "shortcuts" that a
  simpler implementation could skip. **Right:** both are the only way to
  convert a shape the loop cannot resolve (red sibling; near-red/far-black
  sibling) into a shape it can (black sibling; far-red sibling) — removing
  either one leaves real, reachable trees that the remaining cases cannot
  correctly repair.
- **Wrong:** assuming case D always operates on the *original* `sib` from
  the top of the loop iteration. **Right:** whenever case A or case C ran
  first, `sib` was reassigned to a freshly re-fetched node before case D
  reads it — case D's `colorOf(parentOf(x))`, `rightOf(sib)`/`leftOf(sib)`
  reads must all resolve against the live tree at the point case D
  executes, not against whatever `sib` pointed to when the iteration began.
- **Wrong:** treating `x = root` in case D as meaning "the loop just
  happened to reach the root." **Right:** it is an unconditional
  termination idiom — the very next check of `x != root` is false by
  construction, ending the loop regardless of where the actual tree root
  is, because case D has already fully discharged the deficit.

## Cheat sheet

| Case | Sibling | Sibling's children | Action | Terminates loop? |
|---|---|---|---|---|
| A | red | n/a | recolor sib/parent, rotate parent toward `x`'s side, re-fetch `sib` | no — falls through to B/C/D same iteration |
| B | black | both black | recolor `sib` red, `x = parentOf(x)` | no — may repeat, up to O(log n) times |
| C | black | near red, far black | recolor near child + `sib`, rotate `sib` away from `x`'s side, re-fetch `sib` | no — falls through to D same iteration |
| D | black | far red | recolor `sib`/parent/far child, rotate parent toward `x`'s side, `x = root` | yes — unconditionally |

Left-child branch reads: near = `leftOf(sib)`, far = `rightOf(sib)`,
`rotateLeft(parentOf(x))` (A, D), `rotateRight(sib)` (C). Right-child
(mirror) branch swaps every one of those: near = `rightOf(sib)`, far =
`leftOf(sib)`, `rotateRight(parentOf(x))` (A, D), `rotateLeft(sib)` (C).

## Self-test

1. **Why does case C rotate `sib` itself, while case A and case D both
   rotate `parentOf(x)`?**
   Fold: case A and D both need to promote a node into the *parent's*
   structural slot (the red sibling in A, the black-far-red sibling in
   D), so they rotate around the parent. Case C only needs to reshuffle
   which of `sib`'s own two children sits on the near vs. far side — a
   purely local reshaping of the sibling's own subtree — so it rotates
   around `sib`, one level lower.

2. **In the left-child branch's case C, why does the guard read
   `colorOf(rightOf(sib)) == BLACK` rather than directly checking
   `colorOf(leftOf(sib)) == RED`?**
   Fold: by the time this line runs, case B's both-black test has already
   failed, so at least one of `sib`'s two children is known to be red —
   checking that the far child (`rightOf(sib)`) is black is sufficient to
   conclude the near child must be the red one, without a redundant
   explicit check.

3. **What is the one line that differs between case A's rotation and case
   C's rotation in the left-child branch, and why is copying case A's
   rotation direction into case C's mirror a live bug rather than a
   cosmetic one?**
   Fold: case A rotates `parentOf(x)`; case C rotates `sib`. In the
   mirror branch, case A's rotation is `rotateRight(parentOf(x))` while
   case C's is `rotateLeft(sib)` — different node, different direction.
   Confusing the two rotates the wrong node in the wrong direction,
   silently producing an invalid red-black tree that passes no visible
   check until a much later operation.

4. **Why does case D set `x = root` instead of, say, `break`-ing out of
   the loop directly?**
   Fold: they are behaviorally identical here (both end the loop
   immediately), but `x = root` is the JDK's chosen idiom because it keeps
   the loop's single exit condition (`x != root && colorOf(x) == BLACK`)
   as the only place execution can leave the loop, rather than adding a
   second exit path that a future maintainer could miss.

5. **Trace: `x` is a right child, `sib` is black, `sib`'s left child is
   red, `sib`'s right child is black. Which case fires, and what happens
   to `sib` afterward?**
   Fold: for a right-child `x`, near = `rightOf(sib)` and far =
   `leftOf(sib)`. Here the far child is red and the near child is black —
   that is case D's shape directly (far red), not case C. Case D fires:
   `sib` takes the parent's old color, the parent is forced black, the
   far (left) child is forced black, `rotateRight(parentOf(x))` runs, and
   `x = root` ends the loop.

6. **Why does `remove(4)` in this file's demo fire case B twice instead of
   once?**
   Fold: after the first case-B recolor, the new `x` (the old parent, `6`)
   is still black and still not the root, so the `while` guard stays true
   and the loop body runs again with a freshly computed `sib` at the new
   level — case B can repeat at every ancestor level until it hits a red
   node or the root, which is exactly what bounds it at O(log n).

7. **In `remove(15)`'s trace, why does case D's `setColor(sib,
   colorOf(parentOf(x)))` recolor the re-fetched `sib` (node 13) RED
   rather than BLACK?**
   Fold: at the moment case D runs, `parentOf(x)` (node 14) is colored
   RED — it was recolored RED earlier by the case-D fix during
   `remove(10)`. Case D always copies the parent's *current* color onto
   `sib`, whatever that color happens to be, so that anything above the
   local neighborhood keeps seeing the same black-height; it does not
   hardcode BLACK.

8. **How many total code branches does the complete `fixAfterDeletion`
   method have, counting both files, and how many of them can actually
   terminate the `while` loop on their own?**
   Fold: eight code branches (four logical cases times two mirrors). Only
   two of the eight — case D in each branch — terminate the loop
   unconditionally by themselves; case B in either branch can also end
   the loop, but only conditionally, when the freshly reassigned `x`
   happens to be the root or a red node.

## Open questions

**Unverified:** the exact `fixAfterInsertion` rotation sequence that turns
15 individual ascending `put` calls into this file's seed tree is asserted
by well-known red-black tree structure, not re-derived step by step here
— see part 1 (`04-build-my-tree-map.md`) for the insertion-side trace this
would need. The deletion trace itself (every case fired in the demo above)
was hand-simulated against this file's and part 2's code, not compiled and
executed — no Java toolchain is available in this environment.

---

**Leaves covered:** 4.6.1 (part 3 of 6) (1 leaf, shared across 6 files)
**Leaves deferred:** none — remainder of 4.6.1 continues in 04c, 04d
**Diagrams included:** none
**Target version:** Java 21 LTS
**Lines:** 490
