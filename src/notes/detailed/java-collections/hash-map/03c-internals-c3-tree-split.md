# 02 Java Collections — `HashMap` — INTERNALS (§3.6 `HashMap` source walk — `TreeNode.split` and `untreeify`)

**Target version: Java 21 LTS.** | [Index](../00-index.md)
Previous: [hash-map/03b-internals-c2-concurrent-resize-and-tree-split.md](03b-internals-c2-concurrent-resize-and-tree-split.md) · Next: [hash-map/04-internals-d-treeify.md](04-internals-d-treeify.md)

The resize walk so far has moved plain linked bins. One bin shape is left: a treeified one. This file finishes `resize()` by walking the only method that handles it — `TreeNode.split` — and the `untreeify` it calls, and corrects a widely repeated claim about when a tree bin reverts to a list.

---

## `TreeNode.split` — how a treeified bin survives a resize

### Mental model first

A treeified bin is two data structures wearing one set of nodes: a red-black tree **and** a doubly-linked list threaded through the same `TreeNode`s via `next`/`prev`. `split` ignores the tree entirely. It walks the **list**, deals each node into a lo pile or a hi pile exactly as the plain-bin path does, counts the piles, and only then asks per pile: is this still big enough to deserve a tree? That is why splitting a tree bin is a linear pass and not a tree traversal — the list overlay exists precisely so this method can be cheap.

Think of it as sorting a deck that also happens to be filed in a card index. You do not consult the index to deal the cards; you deal them off the top, and only afterwards decide whether each half is worth re-indexing.

### Why it exists

`resize()` has to move every bin, and a treeified bin cannot simply be pointer-shuffled the way a list can: the tree's ordering invariants are over hash-then-comparable order and say nothing about the new index bit, so the tree must be partitioned. Rebuilding two trees from scratch would be O(n log n) unconditionally, on every resize, for every tree bin. `split` avoids that whenever it can — and it uses the resize as the natural moment to shed trees that have shrunk below the point of being worth their memory.

### When it runs, and when it does not

Only from `resize()`, and only for a bin whose head is a `TreeNode`. It is not a public path, it is not reachable from `put`, and — with one important exception covered below — it is the path that shrinks trees back to lists. The sibling operation it must be understood against is `treeifyBin`, which goes the other way on the `put` path; see [04-internals-d-treeify.md](04-internals-d-treeify.md).

### The source

```java
        final void split(HashMap<K,V> map, Node<K,V>[] tab, int index, int bit) {
            TreeNode<K,V> b = this;
            // Relink into lo and hi lists, preserving order
            TreeNode<K,V> loHead = null, loTail = null;
            TreeNode<K,V> hiHead = null, hiTail = null;
            int lc = 0, hc = 0;
            for (TreeNode<K,V> e = b, next; e != null; e = next) {
                next = (TreeNode<K,V>)e.next;
                e.next = null;
                if ((e.hash & bit) == 0) {
                    if ((e.prev = loTail) == null)
                        loHead = e;
                    else
                        loTail.next = e;
                    loTail = e;
                    ++lc;
                }
                else {
                    if ((e.prev = hiTail) == null)
                        hiHead = e;
                    else
                        hiTail.next = e;
                    hiTail = e;
                    ++hc;
                }
            }

            if (loHead != null) {
                if (lc <= UNTREEIFY_THRESHOLD)
                    tab[index] = loHead.untreeify(map);
                else {
                    tab[index] = loHead;
                    if (hiHead != null) // (else is already treeified)
                        loHead.treeify(tab);
                }
            }
            if (hiHead != null) {
                if (hc <= UNTREEIFY_THRESHOLD)
                    tab[index + bit] = hiHead.untreeify(map);
                else {
                    tab[index + bit] = hiHead;
                    if (loHead != null)
                        hiHead.treeify(tab);
                }
            }
        }
```
— `java.base/java/util/HashMap.java`, JDK 21, line 2297. Javadoc above the method omitted rather than elided. (leaf 3.6.29)

**Version note, verified:** this method is byte-for-byte identical in JDK 8, at `java/util/HashMap.java` line 2138 — `diff` of the two 51-line extracts reports no differences. Nothing about `split` has changed between 8 and 21. Any claim you read that "tree splitting was reworked in Java 9/11/17" is wrong.

Line by line:

- `TreeNode<K,V> b = this` — the bin head, which for a treeified bin is also the head of the `next` list. `moveRootToFront` (line 1988) keeps the tree root at the list head, so `tab[index]` and the list agree on where the bin starts.
- Four head/tail locals and two counters. **Tail** insertion, like the plain path — order within each half is preserved, which the source comment states outright.
- `for (TreeNode<K,V> e = b, next; e != null; e = next)` — **walks `next`, not `left`/`right`.** The linked-list overlay that `treeifyBin` built survives inside the treeified bin exactly so this can happen. `TreeNode` inherits `next` from `HashMap.Node` via `LinkedHashMap.Entry`; the inheritance chain is in [04-internals-d-treeify.md](04-internals-d-treeify.md).
- `next = (TreeNode<K,V>)e.next; e.next = null;` — save the successor, then **sever**. Both halves are rebuilt from scratch rather than spliced out of the original, which is why no stale `next` can survive into a half it does not belong in.
- `if ((e.hash & bit) == 0)` — **the same splitting rule as the plain-bin path**, where `bit` is `oldCap`. One rule, two node types: a node's new index is either `index` or `index + oldCap`, decided by the single bit the capacity doubling just exposed.
- `if ((e.prev = loTail) == null) loHead = e; else loTail.next = e;` — sets `prev` and detects "list is empty" in the same expression. `TreeNode` maintains `prev` as well as `next` because `removeTreeNode` needs to unlink from the list in O(1).
- `loTail = e; ++lc;` — advance the tail and count.

Then the two symmetric decisions:

- `if (lc <= UNTREEIFY_THRESHOLD) tab[index] = loHead.untreeify(map);` — `UNTREEIFY_THRESHOLD` is `6` (line 267). Note the `<=`: a half of exactly **6 untreeifies**, a half of **7 stays a tree**. Against `TREEIFY_THRESHOLD = 8` (line 260) tested with `>=`, that leaves a hysteresis band of 7 — a bin cannot flip back and forth on a single insertion. The full argument is leaf 3.6.34 in [04b-internals-d2-poisson-and-hysteresis.md](04b-internals-d2-poisson-and-hysteresis.md).
- `else { tab[index] = loHead; if (hiHead != null) loHead.treeify(tab); }` — otherwise the half stays a tree, and is re-treeified **only if the bin actually split**.

### `untreeify`

```java
        final Node<K,V> untreeify(HashMap<K,V> map) {
            Node<K,V> hd = null, tl = null;
            for (Node<K,V> q = this; q != null; q = q.next) {
                Node<K,V> p = map.replacementNode(q, null);
                if (tl == null)
                    hd = p;
                else
                    tl.next = p;
                tl = p;
            }
            return hd;
        }
```
— `java.base/java/util/HashMap.java`, JDK 21, line 2117. (leaf 3.6.29)

Nine lines of body. It walks the `next` chain and builds a brand-new chain of plain nodes, tail-inserted, so order is preserved. The `TreeNode`s themselves are dropped and become garbage — 56 bytes per entry collapsing to 32.

`map.replacementNode(q, null)` (line 1913) is the piece worth pausing on: it is an **overridable hook**, not a constructor call. `HashMap` returns a `Node`; `LinkedHashMap` overrides it to return a `LinkedHashMap.Entry` so its access/insertion-ordering links survive the downgrade from tree to list. Without the hook, untreeifying a `LinkedHashMap` bin would silently destroy its iteration order.

### The subtlest line: `if (hiHead != null) // (else is already treeified)`

Work it through rather than taking the comment's word for it.

Suppose **every** node in the bin went to the lo half — `hc == 0`, so `hiHead == null`. Then no node moved out of the tree. The set of nodes is unchanged, every hash is unchanged, and every red-black invariant that held before the split still holds after it. Furthermore `tab[index]` already points at the correct root: `loHead` is the old bin head, and `moveRootToFront` guarantees the old bin head *is* the tree root. Re-treeifying would rebuild, at O(n log n), a tree identical to the one already there.

The guard therefore reads: *only re-treeify a half if the other half is non-empty*, i.e. only if the bin genuinely split. The `lc <= 6` branch above it is unaffected — if the whole bin is 6 or fewer nodes it untreeifies regardless of whether it split, because that is the shrink path, not the rebuild path.

**Insight:** the guard is not an optimisation bolted on afterwards; it is the reason `split` is cheap in the common case. Most tree bins at a resize either stay whole (no work) or shed a small half (an `untreeify`, which is O(n) not O(n log n)). The full double rebuild is the rare branch.

**Interview:** *"In `TreeNode.split`, why is the `treeify` call guarded by `hiHead != null`?"* — because if nothing went to the hi half the tree was never partitioned, so its structure is still valid and rebuilding it is pure waste. Almost nobody notices this line.

### Watching it happen

```java
import java.lang.reflect.Field;
import java.util.HashMap;

public class SplitDemo {

    /** Key whose hash we control exactly, so we can steer bins. */
    record Key(String name, int h) {
        @Override public int hashCode() { return h; }
        @Override public String toString() { return name; }
    }

    static Object[] table(HashMap<?, ?> m) throws Exception {
        Field f = HashMap.class.getDeclaredField("table");
        f.setAccessible(true);
        return (Object[]) f.get(m);
    }

    static void report(String label, HashMap<Key, String> m) throws Exception {
        Object[] tab = table(m);
        System.out.println(label + " capacity=" + tab.length + " size=" + m.size());
        for (int i = 0; i < tab.length; i++) {
            if (tab[i] == null) continue;
            String cls = tab[i].getClass().getSimpleName();
            if (chainLength(tab[i]) == 1) continue;   // skip the padding singletons
            System.out.println("  bin " + i + ": head is " + cls + ", " + chainLength(tab[i]) + " nodes");
        }
    }

    static int chainLength(Object head) throws Exception {
        // TreeNode extends LinkedHashMap.Entry extends HashMap.Node; walk up to find 'next'
        Class<?> c = head.getClass();
        Field f = null;
        while (c != null && f == null) {
            try { f = c.getDeclaredField("next"); } catch (NoSuchFieldException e) { c = c.getSuperclass(); }
        }
        f.setAccessible(true);
        int n = 0;
        for (Object q = head; q != null; q = f.get(q)) n++;
        return n;
    }

    public static void main(String[] args) throws Exception {
        // Capacity 64 (>= MIN_TREEIFY_CAPACITY), so treeifyBin really treeifies.
        HashMap<Key, String> m = new HashMap<>(64, 0.75f);

        // 13 keys all landing in bin 0 at capacity 64: the spread is h ^ (h >>> 16),
        // and multiples of 64 with a zero high half keep (spread & 63) == 0.
        // The split bit at the 64 -> 128 resize is 64:
        // 6 keys have bit 64 clear (lo half), 7 have it set (hi half).
        for (int i = 0; i < 6; i++)  m.put(new Key("lo" + i, i * 128), "v");
        for (int i = 0; i < 7; i++)  m.put(new Key("hi" + i, 64 + i * 128), "v");
        report("After 13 colliding puts:", m);

        // Force the 64 -> 128 resize by filling past the threshold of 48.
        for (int i = 0; m.size() < 49; i++) m.put(new Key("pad" + i, 1000 + i * 7), "v");
        report("After resize to 128:", m);
    }
}
```

Run with `java --add-opens java.base/java.util=ALL-UNNAMED SplitDemo`. Real output, JDK 21.0.7:

```
After 13 colliding puts: capacity=64 size=13
  bin 0: head is TreeNode, 13 nodes
After resize to 128: capacity=128 size=49
  bin 0: head is Node, 6 nodes
  bin 64: head is TreeNode, 7 nodes
```

Both halves came out of the same `split` call on the same tree. `lc == 6` satisfied `6 <= 6` and untreeified to plain `Node`s; `hc == 7` failed it and stayed a `TreeNode` tree, re-treeified because `loHead != null`. That is the `<=` boundary, observed rather than asserted — and it is the cleanest one-run demonstration of `UNTREEIFY_THRESHOLD` you can produce.

### Correction: `split` is not the only untreeify path

The syllabus for this leaf states that a plain `remove()` does not shrink a tree back to a list. **The source contradicts that**, and the source wins. There are three `untreeify` call sites in JDK 21 — lines 2212, 2326, 2335 — and the first is inside `removeTreeNode`:

```java
            if (root == null
                || (movable
                    && (root.right == null
                        || (rl = root.left) == null
                        || rl.left == null))) {
                tab[index] = first.untreeify(map);  // too small
                return;
            }
```
— `java.base/java/util/HashMap.java`, JDK 21, lines 2207–2213. (leaf 3.6.29, correction)

Read the test carefully: it is **structural, not a count**. It fires when the tree is shallow enough that the root has no right child, or no left child, or its left child has no left child. `UNTREEIFY_THRESHOLD` does not appear in it. `movable` is false only when `HashMap` is being used as the backing store for something that must not relocate bins mid-operation, so in ordinary use the guard is live.

Measured on JDK 21.0.7, removing from a 13-node treeified bin one key at a time, the bin stays a `TreeNode` tree all the way down to **4 nodes** and untreeifies on the removal that leaves **3**:

```
13 nodes in bin 0: TreeNode
  after remove -> 12 nodes left in bin 0: TreeNode
  after remove -> 11 nodes left in bin 0: TreeNode
  after remove -> 10 nodes left in bin 0: TreeNode
  after remove -> 9 nodes left in bin 0: TreeNode
  after remove -> 8 nodes left in bin 0: TreeNode
  after remove -> 7 nodes left in bin 0: TreeNode
  after remove -> 6 nodes left in bin 0: TreeNode
  after remove -> 5 nodes left in bin 0: TreeNode
  after remove -> 4 nodes left in bin 0: TreeNode
  after remove -> 3 nodes left in bin 0: Node
```

Note the two rows that matter: at **6 nodes remaining** the bin is still a `TreeNode` tree, which directly falsifies the "drops below 6 and reverts" folklore.

So the corrected fact — which is the memory fact that actually matters — is: **a bin that treeified stays a tree, at 56 bytes per entry instead of 32, for any size from 4 upward, until the map next resizes.** Removal shrinks it only at the very bottom of the tree's depth, and never at the `UNTREEIFY_THRESHOLD` of 6. The number 6 is consulted exclusively by `split`.

### Cost, with its trade

`split` is O(n) in the bin for the partition pass, **plus** O(n log n) for each half that re-treeifies — **but** it re-treeifies only when the bin actually split, **and** it skips that work entirely for any half of 6 or fewer, which given the Poisson distribution of bin sizes is the overwhelmingly common case. The price paid for that is standing overhead: every `TreeNode` carries `parent`, `left`, `right`, `prev` and `red` on top of a plain `Node`'s four fields, and the `next`/`prev` list must be maintained on every tree insertion and removal purely so `split` and `removeTreeNode` can be linear. That is 24 extra bytes per entry, always, to make a rare operation cheap — a deliberate trade, and the right one only because tree bins are rare to begin with.

> **Definition.** `TreeNode.split` partitions a treeified bin across a capacity doubling by walking its linked-list overlay with the same `(hash & oldCap) == 0` rule the plain path uses, then per half either untreeifies it (`count <= 6`) or re-treeifies it — the latter only when the bin genuinely split.

---

## Pitfalls

### Believing a tree bin untreeifies once it drops below 6 entries

**Wrong**

```java
// "UNTREEIFY_THRESHOLD is 6, so removing down to 5 gives me the memory back."
for (int i = 12; i >= 5; i--) map.remove(keys[i]);
// Measured on JDK 21.0.7: at 6 nodes left the bin is STILL a TreeNode tree,
// and at 5 nodes left it is still a TreeNode tree. It flips at 3.
```

**Right**

```java
// UNTREEIFY_THRESHOLD is read only by split(), i.e. only during a resize.
// To actually reclaim the memory from a map that has shed most of its entries,
// rebuild it — the copy constructor lays every surviving entry into fresh bins:
map = new HashMap<>(map);
```

**Why people believe it:** `UNTREEIFY_THRESHOLD = 6` sits seven lines under `TREEIFY_THRESHOLD = 8` in the source, and the symmetry invites the reading "8 up on insert, 6 down on remove". Only the "8 up" half is a `put`-path rule. The `remove` path uses a completely different, structural test at line 2207 that never looks at a count.

### Assuming `split` traverses the red-black tree

**Wrong**

```java
// Mental model: "splitting a tree bin means an in-order walk, then two rebuilds."
// Cost you would predict: O(n log n) every time a tree bin is resized.
```

**Right**

```java
// Actual: one linear pass over the next-chain, and a rebuild only for a half
// that both stayed a tree AND actually split:
//   for (TreeNode<K,V> e = b, next; e != null; e = next)            // list, not tree
//   if (hiHead != null) loHead.treeify(tab);                       // guarded
```

**Why people believe it:** "it's a tree, so you traverse the tree" is the obvious inference, and the `next`/`prev` overlay is invisible unless you have read `treeifyBin`. The overlay is maintained at real cost specifically so this traversal never has to happen.

### Expecting a `LinkedHashMap` to lose its ordering when a bin untreeifies

**Wrong**

```java
// "untreeify builds new Node objects, so LinkedHashMap's before/after links are lost."
Node<K,V> p = new Node<>(q.hash, q.key, q.value, null);   // what it does NOT do
```

**Right**

```java
Node<K,V> p = map.replacementNode(q, null);   // line 2120 — an overridable hook
// HashMap returns a Node; LinkedHashMap overrides it to return a LinkedHashMap.Entry
// and re-links it into the access/insertion order list.
```

**Why people believe it:** `untreeify` reads like a straightforward list rebuild, and the single call that makes it subclass-aware is easy to skim past. Every node-creation site in `HashMap` goes through one of these hooks for exactly this reason.

## Cheat sheet

| Thing | Value / fact | JDK 21 line |
|---|---|---|
| `split` | 51 lines; **byte-for-byte identical** in JDK 8 (line 2138) and 21 | 2297 |
| Callers of `split` | `resize()` only, and only for a `TreeNode`-headed bin | 683 |
| `split` traversal | Walks `next` (the list overlay), never `left`/`right` | 2303 |
| `split` rule | `(e.hash & bit) == 0`, `bit == oldCap` — same as the plain path | 2306 |
| Sever-then-relink | `e.next = null` on every node before dealing it into a half | 2305 |
| Insertion order in halves | Tail insertion; original order preserved (per source comment) | 2299 |
| `TREEIFY_THRESHOLD` | 8, tested `>=`, on the `put` path | 260 |
| `UNTREEIFY_THRESHOLD` | 6, tested `<=`, **only inside `split`** | 267 |
| Boundary | half of 6 → untreeify; half of 7 → stays a tree | 2325, 2334 |
| Hysteresis band | 7 — see leaf 3.6.34 for the full argument | — |
| Re-treeify guard | `if (hiHead != null)` — skip if the bin did not actually split | 2329 |
| `untreeify` | Rebuilds via `map.replacementNode`, a `LinkedHashMap` hook | 2117, 1913 |
| `untreeify` call sites | Three: `removeTreeNode` 2212, `split` 2326 and 2335 | — |
| `remove` untreeify trigger | **Structural**, not count-based; measured to fire at 3 nodes left | 2207 |
| Tree bin at 6 nodes after removes | Still a `TreeNode` tree — measured, JDK 21.0.7 | — |
| `moveRootToFront` | Keeps the tree root at the bin head, so `split` can start at `tab[index]` | 1988 |
| `TreeNode` vs `Node` size | 56 bytes vs 32 bytes per entry (64-bit, compressed oops) | — |
| `split` cost | O(n) partition + O(n log n) per half that both stayed a tree and split | — |
| Reclaiming tree memory | `new HashMap<>(map)`, or wait for the next resize | — |

## Self-test

**Q1.** Why does `split` walk `next` rather than traversing the red-black tree?

<details><summary>Answer</summary>

Because the tree's ordering says nothing about the split bit, so a tree traversal buys nothing — every node has to be visited and classified regardless. `treeifyBin` keeps the doubly-linked `next`/`prev` overlay alive inside a treeified bin precisely so that `split` (and `removeTreeNode`) can be a linear pass. That overlay is the reason `TreeNode` inherits `next` through `LinkedHashMap.Entry` from `HashMap.Node`.

</details>

**Q2.** A tree bin of 13 nodes splits 6/7. What is in each destination bin afterwards, and how much work was done?

<details><summary>Answer</summary>

`lc == 6` satisfies `6 <= UNTREEIFY_THRESHOLD`, so `tab[index]` gets a plain `Node` chain of 6 from `untreeify`. `hc == 7` fails it, so `tab[index + bit]` keeps `TreeNode`s and, because `loHead != null` (the bin really split), is re-treeified. Work: one O(13) partition pass, one O(6) untreeify, one O(7 log 7) treeify. This is the verified `SplitDemo` output above.

</details>

**Q3.** Under what condition does `split` skip `treeify` on a half that stays a tree, and why is that safe?

<details><summary>Answer</summary>

When the other half is empty — `hiHead == null` for the lo branch, `loHead == null` for the hi branch. If no node crossed over, the node set and all the hashes are unchanged, so every red-black invariant still holds, and `tab[index]` already points at the valid root because `moveRootToFront` keeps the root at the list head. Rebuilding would be O(n log n) for a bit-identical result.

</details>

**Q4.** True or false: a treeified bin reverts to a linked list as soon as it drops below 6 entries.

<details><summary>Answer</summary>

False, and this is a misreading rather than a version trap — `split` is identical in JDK 8 and 21. `UNTREEIFY_THRESHOLD = 6` is consulted **only** inside `split`, i.e. only during a resize. On the `remove` path, `removeTreeNode` has its own *structural* check (line 2207: root missing a right child, or missing a left child, or the left child missing a left child), which on JDK 21.0.7 was measured to fire only when 3 nodes remain. At 6 nodes remaining the bin was still a `TreeNode` tree. Between 4 and 7 nodes a bin that treeified stays a tree at 56 bytes per entry until the map resizes.

</details>

**Q5.** Why is `untreeify` written as `map.replacementNode(q, null)` rather than `new Node<>(...)`?

<details><summary>Answer</summary>

Because it is an overridable hook. `HashMap.replacementNode` (line 1913) returns a plain `Node`; `LinkedHashMap` overrides it to return a `LinkedHashMap.Entry` and re-link it into the access/insertion-order list. A hard-coded `new Node<>` would silently destroy a `LinkedHashMap`'s iteration order the first time one of its bins untreeified.

</details>

**Q6.** What does `e.next = null` at the top of the partition loop protect against?

<details><summary>Answer</summary>

It severs each node from the original chain before it is dealt into a half, so both halves are built from scratch with fresh links rather than spliced out of the existing chain. Without it, the last node placed into a half would still carry a `next` pointing at a node that went to the *other* half, splicing the two destination bins together.

</details>

**Q7.** You have a `HashMap` that peaked at a million entries with several treeified bins, and has since had 95% of its entries removed. Memory has not come back. Why, and what do you do?

<details><summary>Answer</summary>

Two reasons compound. First, `HashMap` never shrinks its table array — capacity only ever grows, so a table sized for a million entries stays allocated. Second, a bin that treeified stays a tree at 56 bytes per entry down to about 3 nodes, and only a resize consults `UNTREEIFY_THRESHOLD` — and no resize will happen, because the map is shrinking, not growing. The fix is to rebuild: `map = new HashMap<>(map)` sizes a fresh table to the surviving entry count and lays every entry into a plain bin.

</details>

**Q8.** Given `TREEIFY_THRESHOLD = 8` tested with `>=` and `UNTREEIFY_THRESHOLD = 6` tested with `<=`, what is the band in which a bin's shape is stable, and why does the asymmetry exist?

<details><summary>Answer</summary>

A bin treeifies at 8 or more and a half untreeifies at 6 or fewer, so 7 is the stable band: a bin at 7 will neither treeify on the put path nor untreeify on a split. That gap is hysteresis — without it, a bin hovering at the threshold could convert back and forth on alternating insert/resize cycles, paying an O(n log n) rebuild each time. The full derivation is leaf 3.6.34 in `04b-internals-d2-poisson-and-hysteresis.md`.

</details>

## Open questions

- The measured `remove`-path untreeify point (3 nodes remaining) is a consequence of the structural test at line 2207 for one particular removal order, on JDK 21.0.7. Other removal orders produce differently shaped trees and could plausibly trip the test at 4 or 5 nodes remaining. The claim this file rests on — "a treeified bin stays a tree well above `UNTREEIFY_THRESHOLD`, which the `remove` path never reads" — holds for any order, since the constant does not appear in `removeTreeNode` at all. Pinning the exact worst-case bound would need an exhaustive search over removal permutations.

---

**Leaves covered:** 3.6.29 (1 leaf)
**Leaves deferred:** none
**Diagrams included:** none new — the treeified bin itself (D-91) and the inheritance chain (D-96) are embedded in [04-internals-d-treeify.md](04-internals-d-treeify.md)
**Target version:** Java 21 LTS
**Lines:** 413
