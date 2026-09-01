# 02 Java Collections — TreeMap — INTERNALS (§4.6.1, part 1 of 6)

**Target version: Java 21 LTS.** | [Index](../00-index.md)
Previous: [tree-map/03c-internals-b3-comparisons-and-alternatives.md](03c-internals-b3-comparisons-and-alternatives.md) · Next: [tree-map/04b-build-my-tree-map-b-deletion.md](04b-build-my-tree-map-b-deletion.md)

## Series map

This is **part 1 of 6** of a build-it series that hand-writes `MyTreeMap<K,V>`
from scratch: this file (class shell, `compare()`, `getEntry`, rotations,
`put`+`fixAfterInsertion`) → `04b` (`remove`/`deleteEntry`/successor, plus
`fixAfterDeletion` cases A–B) → `04b2` (cases C–D, the mirror branch, the
deletion demo) → `04c` (`floorEntry`/`ceilingEntry`/`firstEntry`/`lastEntry`)
→ `04c2` (the in-order `Iterator`) → `04d` (diff vs the real `TreeMap`, the
compile-and-run proof).

**The complete, compiling `MyTreeMap<K,V>` is the concatenation of all six
parts' code blocks, in that order.** Typing out only this file gives a class
that can construct, `put`, and `get` — nothing more. Every code block below
is written exactly as it will appear inside the eventual class body.

## Mental model: what we're building, and in what order

A `TreeMap` is a sorted map backed by a classic CLRS-style red-black tree
with parent pointers — no "leaning" convention. The build order mirrors how
you'd actually construct one under interview pressure:

1. **Shell first** — fields, `Entry`, constructors — nothing else compiles
   without them.
2. **Read path second** — `compare()` and `getEntry` — insertion is "read
   path, then mutate," and you can't debug a mutator if the search it
   depends on is untested.
3. **Rotation primitives third** — `rotateLeft`/`rotateRight` — both
   insertion-fixup and deletion-fixup (part 2) are built entirely from
   these two pointer-surgery operations; get them right once and every
   fixup case becomes "call rotate, flip colors."
4. **`put` and `fixAfterInsertion` last** — safe only because it is itself
   just a sequence of calls to steps 2 and 3.

**Insight:** Every red-black operation decomposes into "walk with
`compare`," "splice with `rotateLeft`/`rotateRight`," and "recolor a
constant number of nodes." Name which of the three a line is doing, and you
can debug it without re-deriving the algorithm.

### The class shell and fields

We implement a **reasonable subset of `Map<K,V>`**, not the full interface.
Formally declaring `implements Map<K,V>` would force stubbing 15+ methods
(`keySet`, `values`, `entrySet`, `putAll`, …) — most belong to parts 2–4, and
a few (bulk view methods) are out of scope for the whole series. So
`MyTreeMap<K,V>` is a plain class here; part 4's diff notes which
`Map<K,V>` methods the real `java.util.TreeMap` has that we never implement.

Unlike the outer map, the nested `Entry<K,V>` DOES implement `Map.Entry<K,V>`,
matching `java.util.TreeMap.Entry` (see the excerpt in
[02b](02b-internals-a2-entry-and-rotations.md)) — three small methods bought
so part 5's `EntryIterator` can return the real `Map.Entry<K,V>`. Needs
`import java.util.Map;` when assembled standalone.

```java
public class MyTreeMap<K,V> {

    /** Null if natural ordering (K must implement Comparable<? super K>). */
    private final Comparator<? super K> comparator;

    private transient Entry<K,V> root;
    private transient int size = 0;
    private transient int modCount = 0;

    private static final boolean RED   = false;
    private static final boolean BLACK = true;

    static final class Entry<K,V> implements Map.Entry<K,V> {
        K key;
        V value;
        Entry<K,V> left;
        Entry<K,V> right;
        Entry<K,V> parent;
        boolean color = BLACK;

        Entry(K key, V value, Entry<K,V> parent) {
            this.key = key;
            this.value = value;
            this.parent = parent;
        }

        @Override
        public K getKey() {
            return key;
        }

        @Override
        public V getValue() {
            return value;
        }

        @Override
        public V setValue(V value) {
            V old = this.value;
            this.value = value;
            return old;
        }

        @Override
        public String toString() {
            return key + "=" + value;
        }
    }

    public MyTreeMap() {
        this.comparator = null;
    }

    public MyTreeMap(Comparator<? super K> comparator) {
        this.comparator = comparator;
    }
}
```

This mirrors `java.util.TreeMap`'s field block almost verbatim: the real
class has exactly these four fields (`comparator`, `root`, `size`,
`modCount`), all `transient` except `comparator`, because the real class is
`Serializable` and writes its own `writeObject`/`readObject` walking the
tree in sorted order rather than letting default serialization chase 6
pointers per node. We don't implement `Serializable`, so `transient` here
is a nod to fidelity, not a functional requirement.

`Entry.color` defaulting to `BLACK` is deliberate and matches the JDK: a
brand-new `Entry` is field-initialized `BLACK`, and `put` explicitly flips
it to `RED` inside `fixAfterInsertion` before doing anything else — "not
yet colored" and "colored red" stay two separate, auditable steps.

**Pitfall:** An `enum Color { RED, BLACK }` instead of `boolean` constants
would work identically and reads better, but we match the JDK's
`private static final boolean RED = false;` / `BLACK = true;` on purpose —
it's the detail most likely to trip you up diffing against JDK source later
(part 4 does exactly this) since the encoding is easy to misremember as
`RED = true`.

### compare() and getEntry

```java
    @SuppressWarnings("unchecked")
    final int compare(Object k1, Object k2) {
        return comparator == null
            ? ((Comparable<? super K>) k1).compareTo((K) k2)
            : comparator.compare((K) k1, (K) k2);
    }

    final Entry<K,V> getEntry(Object key) {
        if (comparator != null) {
            return getEntryUsingComparator(key);
        }
        Objects.requireNonNull(key, "key");
        @SuppressWarnings("unchecked")
        Comparable<? super K> k = (Comparable<? super K>) key;
        Entry<K,V> p = root;
        while (p != null) {
            int cmp = k.compareTo(p.key);
            if (cmp < 0) {
                p = p.left;
            } else if (cmp > 0) {
                p = p.right;
            } else {
                return p;
            }
        }
        return null;
    }

    final Entry<K,V> getEntryUsingComparator(Object key) {
        @SuppressWarnings("unchecked")
        K k = (K) key;
        Comparator<? super K> cpr = comparator;
        Entry<K,V> p = root;
        while (p != null) {
            int cmp = cpr.compare(k, p.key);
            if (cmp < 0) {
                p = p.left;
            } else if (cmp > 0) {
                p = p.right;
            } else {
                return p;
            }
        }
        return null;
    }

    public V get(Object key) {
        Entry<K,V> p = getEntry(key);
        return (p == null) ? null : p.value;
    }

    public boolean containsKey(Object key) {
        return getEntry(key) != null;
    }

    public int size() {
        return size;
    }

    public boolean isEmpty() {
        return size == 0;
    }
```

`getEntry` is exactly the BST search from a plain binary search tree —
red-black-ness never enters into *finding* a key, only into *where new
nodes land*. Colors and rotations are purely a maintenance concern for
`put`/`remove`, invisible to `get`.

The split into `getEntry` (natural ordering) and `getEntryUsingComparator`
(explicit `Comparator`) mirrors the real JDK's split of the same two
methods: the natural-ordering path avoids a per-iteration null check on
`comparator`, and the comparator path avoids an unchecked cast to
`Comparable` that would be wrong if `K` doesn't implement it.

**Interview:** Why does `TreeMap` need `compare()` as a single choke point
instead of inlining ordering logic everywhere? Every method that orders two
keys — `put`, `getEntry`, `remove`, `floorKey`, the iterator's successor
walk — must apply the same rule (natural order vs. comparator), or the
tree's invariant silently breaks. One method, reused everywhere, guarantees it.

### rotateLeft / rotateRight

```java
    private void rotateLeft(Entry<K,V> p) {
        if (p != null) {
            Entry<K,V> r = p.right;
            p.right = r.left;
            if (r.left != null) {
                r.left.parent = p;
            }
            r.parent = p.parent;
            if (p.parent == null) {
                root = r;
            } else if (p.parent.left == p) {
                p.parent.left = r;
            } else {
                p.parent.right = r;
            }
            r.left = p;
            p.parent = r;
        }
    }

    private void rotateRight(Entry<K,V> p) {
        if (p != null) {
            Entry<K,V> l = p.left;
            p.left = l.right;
            if (l.right != null) {
                l.right.parent = p;
            }
            l.parent = p.parent;
            if (p.parent == null) {
                root = l;
            } else if (p.parent.right == p) {
                p.parent.right = l;
            } else {
                p.parent.left = l;
            }
            l.right = p;
            p.parent = l;
        }
    }
```

A left rotation at `p` promotes `p`'s right child `r` to take `p`'s old
position; `p` becomes `r`'s new left child, and `r`'s old left subtree
(sorting between `p` and `r`) becomes `p`'s new right subtree. Six pointer
writes, always in the same order: reparent the orphaned middle subtree,
reparent the promoted node into the grandparent's slot, reparent the
grandparent's slot to point at the promoted node, then link the promoted
and demoted nodes to each other. `rotateRight` mirrors it with
`left`/`right` swapped — every red-black fixup case comes in mirrored
left/right pairs for exactly this reason.

This mirrors `java.util.TreeMap.rotateLeft`/`rotateRight` field-for-field,
including the `if (p != null)` guard, which the JDK keeps even though
every call site in `fixAfterInsertion`/`fixAfterDeletion` already knows
`p` is non-null by construction — defensive symmetry, not dead code.

**Pitfall:** The single most common rotation bug is forgetting the
`p.parent.left == p` check and always writing `p.parent.right = r` (or vice
versa) — this silently corrupts the tree whenever `p` happens to be a left
child. It doesn't throw; it surfaces operations later as a `getEntry` that
returns `null` for a key you know you inserted.

### put and fixAfterInsertion

```java
    public V put(K key, V value) {
        Entry<K,V> t = root;
        if (t == null) {
            compare(key, key); // type-check key eagerly, same as the real JDK
            root = new Entry<>(key, value, null);
            size = 1;
            modCount++;
            return null;
        }
        int cmp;
        Entry<K,V> parent;
        Comparator<? super K> cpr = comparator;
        if (cpr != null) {
            do {
                parent = t;
                cmp = cpr.compare(key, t.key);
                if (cmp < 0) {
                    t = t.left;
                } else if (cmp > 0) {
                    t = t.right;
                } else {
                    return t.setValue(value);
                }
            } while (t != null);
        } else {
            Objects.requireNonNull(key, "key");
            @SuppressWarnings("unchecked")
            Comparable<? super K> k = (Comparable<? super K>) key;
            do {
                parent = t;
                cmp = k.compareTo(t.key);
                if (cmp < 0) {
                    t = t.left;
                } else if (cmp > 0) {
                    t = t.right;
                } else {
                    return t.setValue(value);
                }
            } while (t != null);
        }
        Entry<K,V> e = new Entry<>(key, value, parent);
        if (cmp < 0) {
            parent.left = e;
        } else {
            parent.right = e;
        }
        fixAfterInsertion(e);
        size++;
        modCount++;
        return null;
    }

    private static <K,V> Entry<K,V> parentOf(Entry<K,V> p) {
        return (p == null) ? null : p.parent;
    }

    private static <K,V> boolean colorOf(Entry<K,V> p) {
        return (p == null) ? BLACK : p.color;
    }

    private static <K,V> void setColor(Entry<K,V> p, boolean c) {
        if (p != null) {
            p.color = c;
        }
    }

    private static <K,V> Entry<K,V> leftOf(Entry<K,V> p) {
        return (p == null) ? null : p.left;
    }

    private static <K,V> Entry<K,V> rightOf(Entry<K,V> p) {
        return (p == null) ? null : p.right;
    }

    private void fixAfterInsertion(Entry<K,V> x) {
        x.color = RED;

        while (x != null && x != root && x.parent.color == RED) {
            if (parentOf(x) == leftOf(parentOf(parentOf(x)))) {
                Entry<K,V> y = rightOf(parentOf(parentOf(x)));
                if (colorOf(y) == RED) {
                    // Case 1: uncle is red -> recolor parent, uncle, grandparent;
                    // push the "problem" up to the grandparent and keep looping.
                    setColor(parentOf(x), BLACK);
                    setColor(y, BLACK);
                    setColor(parentOf(parentOf(x)), RED);
                    x = parentOf(parentOf(x));
                } else {
                    if (x == rightOf(parentOf(x))) {
                        // Case 2: uncle is black, x is a "zigzag" (right) child ->
                        // rotate at parent first to turn it into case 3.
                        x = parentOf(x);
                        rotateLeft(x);
                    }
                    // Case 3: uncle is black, x is a "straight" (left) child ->
                    // recolor and rotate at the grandparent. This terminates the loop.
                    setColor(parentOf(x), BLACK);
                    setColor(parentOf(parentOf(x)), RED);
                    if (parentOf(parentOf(x)) != null) {
                        rotateRight(parentOf(parentOf(x)));
                    }
                }
            } else {
                // Mirror image: parent is a right child of the grandparent.
                Entry<K,V> y = leftOf(parentOf(parentOf(x)));
                if (colorOf(y) == RED) {
                    setColor(parentOf(x), BLACK);
                    setColor(y, BLACK);
                    setColor(parentOf(parentOf(x)), RED);
                    x = parentOf(parentOf(x));
                } else {
                    if (x == leftOf(parentOf(x))) {
                        x = parentOf(x);
                        rotateRight(x);
                    }
                    setColor(parentOf(x), BLACK);
                    setColor(parentOf(parentOf(x)), RED);
                    if (parentOf(parentOf(x)) != null) {
                        rotateLeft(parentOf(parentOf(x)));
                    }
                }
            }
        }
        root.color = BLACK;
    }
```

`put` is an ordinary BST insert — walk down with `compare`, remember the
last non-null node as `parent`, and hang the new `Entry` off its `left` or
`right` slot depending on the last comparison. The new node stays at its
field-initialized `BLACK` until `fixAfterInsertion`'s first line,
`x.color = RED;`. Every leaf starts red because a red leaf never changes
black-height on any path, so it can't by itself violate equal-black-height
— only "no red node has a red parent," which is exactly what the loop
condition (`x.parent.color == RED`) checks for.

The four cases inside the loop, restated in plain terms:

| Case | Condition | Action |
|---|---|---|
| 1 — red uncle | `colorOf(uncle) == RED` | Recolor parent and uncle `BLACK`, grandparent `RED`; move `x` up to grandparent and keep looping. No rotation. |
| 2 — black uncle, zigzag | uncle black, `x` is the "inner" grandchild | Rotate at parent to convert into case 3, then fall through. |
| 3 — black uncle, straight line | uncle black, `x` is the "outer" grandchild | Recolor parent `BLACK`, grandparent `RED`; rotate at grandparent. Loop terminates (parent is now black). |
| 4 — exit | `x == root` or `x.parent` black | `root.color = BLACK;` unconditionally — case 1 can recolor the root `RED`. |

Case 1 is the only one that loops more than once in general — a chain of
red uncles can push the fixup to the root, which is why the final
`root.color = BLACK;` line exists outside the loop: it corrects a root left
`RED` by a case-1 recolor. Cases 2 and 3 always terminate the loop on the
same iteration, since rotating at the grandparent and recoloring it `RED`
and the (former) parent `BLACK` removes the red-red adjacency without
creating a new one further up.

**Insight:** `parentOf`, `leftOf`, `rightOf`, and `colorOf` exist because
`Entry` fields are plain Java references with no null-safe (`?.`) access.
`x.parent.color` on a null `x.parent` — routine here, since `x` can be the
root or a grandparent lookup can walk off the top of the tree — would NPE.
Each helper is a one-line "if null, return the sentinel that keeps the
algorithm correct": `null` parent, `null` child, or `BLACK` color (a
nonexistent uncle is conventionally black).

**Pitfall:** It's easy to write `fixAfterInsertion` correctly and still
forget `modCount++` in `put`. A structural-modification counter not bumped
on every structural change means the `ConcurrentModificationException`
guard (part 3's iterator) silently stops catching concurrent mutation.
`put`'s `modCount++` sits next to `size++` — treat them as one pair.

### A demo: put and print, exercising red-uncle recolor and one rotation

```java
    void printTree() {
        printTree(root, 0);
    }

    private void printTree(Entry<K,V> node, int depth) {
        if (node == null) {
            return;
        }
        printTree(node.right, depth + 1);
        System.out.println("  ".repeat(depth) + node.key
            + (node.color == RED ? "(R)" : "(B)"));
        printTree(node.left, depth + 1);
    }

    public static void main(String[] args) {
        MyTreeMap<Integer,String> map = new MyTreeMap<>();
        int[] keys = {10, 20, 30, 15, 25, 5, 1};
        for (int k : keys) {
            map.put(k, "v" + k);
            System.out.println("after put(" + k + "):");
            map.printTree();
            System.out.println();
        }
    }
```

`printTree` walks right-subtree, node, left-subtree, so the printed output
reads top-to-bottom as *descending key order*, rotated 90 degrees — a
common trick for eyeballing a small tree's shape in a terminal without
drawing boxes. Running the demo, the two most interesting intermediate
states and the final one are:

```
after put(30):
  30(R)
20(B)
  10(R)

after put(15):
  30(B)
20(B)
    15(R)
  10(B)

after put(1):
  30(B)
    25(R)
20(B)
    15(B)
  10(R)
    5(B)
      1(R)
```

Trace the two interesting steps:

- **`put(30)`** inserts as the right child of `20`, which is red — case 3
  (black uncle, straight line: `20`'s left child doesn't exist yet, so the
  uncle is `null`/black, and `30` is a right child of a right child). The
  fixup recolors `20` black and `10` red, then rotates left at the old root
  `10`, promoting `20` to root — the one-rotation case this leaf asks for.
- **`put(15)`** inserts as the right child of `10`, red, with uncle `30`
  also red — case 1, red-uncle recolor: `10` and `30` flip black, `20`
  (grandparent and root) flips red, then the trailing
  `root.color = BLACK;` flips it straight back. `put(1)` later repeats the
  same case-1 pattern one level down, with `5`/`15` as the red-uncle pair
  and `10` as the grandparent that ends up recolored red and, unlike the
  root, *stays* red.

No zigzag (case 2) fires in this sequence — every rotation needed here
happened to be straight-line. Case 2 only differs from case 3 by one extra
normalizing rotation; a sequence that triggers it is left as an exercise.

## Pitfalls

- **Wrong:** `if (x.parent.color == RED)` as the only loop guard.
  **Right:** `x != null && x != root && x.parent.color == RED` — the
  root's `parent` is `null`, and dereferencing it NPEs.
- **Wrong:** `parentOf(x).parent` for the uncle lookup. **Right:**
  `rightOf(parentOf(parentOf(x)))` (or `leftOf(...)` mirrored) — the
  grandparent can itself be `null` partway through the loop.
- **Wrong:** Dropping the trailing `root.color = BLACK;`. **Right:** keep
  it unconditional — case 1 can leave the root red if the chain reaches the top.
- **Wrong:** `p.color = c` instead of `setColor(p, c)` "since we already
  know `p` isn't null here." **Right:** always route through
  `setColor`/`colorOf` — the moment "always" is wrong, you get a silently
  corrupt tree instead of a loud NPE.
- **Wrong:** Bumping `modCount` in `put`'s existing-key branch
  (`return t.setValue(value);`). **Right:** leave it untouched — `setValue`
  on an existing key isn't a structural modification; only the new-node
  branch bumps both `size` and `modCount`.

## Cheat sheet

| Method | Mirrors (java.util.TreeMap) | Complexity |
|---|---|---|
| `compare(k1, k2)` | `TreeMap.compare` | O(1) + comparator/`compareTo` cost |
| `getEntry` / `getEntryUsingComparator` | same names | O(log n) |
| `rotateLeft(p)` / `rotateRight(p)` | same names | O(1) |
| `put(key, value)` | `TreeMap.put` | O(log n) |
| `fixAfterInsertion(x)` | `TreeMap.fixAfterInsertion` | O(log n) worst, O(1) amortized |
| `parentOf`/`leftOf`/`rightOf`/`colorOf`/`setColor` | same private null-safe statics | O(1) |

## Self-test

1. **Why does a newly inserted `Entry` start red rather than black?**
   Fold: A red leaf changes nothing about black-height on any root-to-null
   path, so it can't violate equal-black-height by itself — only "no red
   node has a red parent," which is exactly what `fixAfterInsertion` fixes.

2. **What does `colorOf(null)` return, and why does that matter for the
   uncle lookup?**
   Fold: `BLACK` — a nonexistent node (external leaf) is conventionally
   black, so "uncle doesn't exist" and "uncle is genuinely black" take the
   same code path with no special-casing.

3. **Why a separate `getEntryUsingComparator` instead of one `getEntry`
   checking `comparator != null` inside the loop?**
   Fold: The natural-ordering path avoids a per-iteration null check, and
   avoids ever casting to `Comparable` when a `Comparator` is in play,
   which would be wrong if `K` doesn't implement `Comparable` at all.

4. **In case 3 (black uncle, straight line), why does the loop always
   terminate on that same iteration?**
   Fold: The rotation plus recolor removes the red-red adjacency between
   `x` and its parent without creating a new one further up — `x` is never
   reassigned in case 3, and its parent is now black, so the guard fails.

5. **Trace `fixAfterInsertion` for inserting `1` into
   `{10, 20, 30, 15, 25, 5}`. Which case fires, and what gets recolored?**
   Fold: `1` lands as the left child of `5` (red), with uncle `15` also
   red — case 1. `5` and `15` flip `BLACK`; grandparent `10` flips `RED`
   and, since it isn't the root, stays red after the loop exits.

6. **Why does `rotateLeft`/`rotateRight` still guard with
   `if (p != null)` when every call site in `fixAfterInsertion` already
   knows `p` is non-null?**
   Fold: Defensive symmetry matching the real JDK — costs nothing where
   `p` is provably non-null, and protects `fixAfterDeletion` (part 2),
   whose call sites need more careful null reasoning.

**Unverified:** The case ordering above is written from first-principles
knowledge of the CLRS/JDK algorithm and believed correct and terminating
for all inputs; it hasn't been checked line-by-line against actual
`java.util.TreeMap` source in this session (part 4's job). The demo trace
was hand-verified by manual simulation, not by compiling the code.

---

**Leaves covered:** 4.6.1 (part 1 of 6) (1 leaf, shared across 6 files)
**Leaves deferred:** none — remainder of 4.6.1 continues in 04b, 04c, 04d
**Diagrams included:** none
**Target version:** Java 21 LTS
**Lines:** 614
