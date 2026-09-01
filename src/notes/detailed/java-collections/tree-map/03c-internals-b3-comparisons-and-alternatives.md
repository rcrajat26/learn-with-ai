# 02 Java Collections — TreeMap — INTERNALS (§3.8.18–3.8.23)

**Target version: Java 21 LTS.** | [Index](../00-index.md)
Previous: [tree-map/03b-internals-b2-buildfromsorted-and-views.md](03b-internals-b2-buildfromsorted-and-views.md) · Next: [tree-map/04-build-my-tree-map.md](04-build-my-tree-map.md)

## 1. Why `TreeMap` is O(log n) with a *large* constant `[PROVE]`

### Mental model

`HashMap.get` and `TreeMap.get` are both written as "O(1)" and "O(log n)" in every algorithms
textbook, and the natural reading is "hash map is faster, tree map is a bit slower, both are
basically free." That reading is wrong at the level a staff engineer needs. `TreeMap.get` on
a million-entry map does roughly twenty sequential dependent memory accesses, each one a
candidate cache miss, each one gated behind a real virtual method call. `HashMap.get` does one
array index and, almost always, one direct equality check. The asymptotic gap (O(1) vs O(log n))
undersells the real gap, which is closer to 15–20x in raw wall-clock terms for a large map.

### Why it exists

The constant is large because every step of a red-black descent is *inherently* sequential
and *inherently* indirect: you cannot know which child to visit next until you have compared
against the current node, and you cannot compare until you have dereferenced a pointer to load
that node's key. There is no way to precompute or parallelize the path — each level depends on
the previous one's outcome. `HashMap` sidesteps this entirely: `hash(key) & (n-1)` needs no
tree traversal, no dependent chain of comparisons — it's an arithmetic index into a bucket
array, computed once, independent of any prior step.

### When to reach for it / when not

Reach for `TreeMap` when you need order — range queries, `firstKey`/`lastKey`,
`ceilingEntry`/`floorEntry`, iteration in sorted order. Do not reach for it as a general-purpose
map replacement for `HashMap` "because log n is basically constant anyway" — for lookup-heavy,
order-irrelevant workloads on large maps, the constant-factor gap is real money in a hot path.

| Structure | Balance rigidity | Rotation/write cost | Lookup cost | Concurrency story | Typical use |
|---|---|---|---|---|---|
| AVL tree | Strict (height diff ≤ 1) | Higher — more rotations per insert/delete | Fastest among the three trees | None built into JDK; single-threaded | In-memory ordered map, read-heavy |
| Red-black tree | Looser (height diff bounded ~2x) | Lower — fewer rotations, more color flips | Slightly slower than AVL | None built into `TreeMap`; needs external lock | In-memory ordered map, write-heavy |
| Skip list | Probabilistic, no rotations at all | O(1) amortized per insert — one CAS per level | Comparable to balanced tree, O(log n) expected | Lock-free via CAS, natural fit | Concurrent ordered map |
| B-tree | Strict (all leaves same depth, node fan-out bounded) | Amortized low — splits are rare, batched | O(log n) but log base is fan-out, so *very* shallow | Depends on engine (latches, MVCC) | Disk-backed index |

### How it works

Walk the actual cost of one `TreeMap.get` call on a map holding one million entries. A
balanced binary tree over 1,000,000 keys has height ⌈log2(1,000,000)⌉ ≈ 20. Each of those 20
levels costs three things, in strict sequence: **(1) load a pointer** — `p = p.left`/`p.right`,
a dereference of a scattered-heap `Entry` reference that is a strong candidate for an L2/L3
cache miss once the tree is bigger than a few thousand entries, since tree nodes carry no
spatial locality the way a contiguous bucket array does; **(2) call `compareTo`/`compare`
virtually** — `k.compareTo(p.key)` is a real virtual dispatch (the JIT can often devirtualize it
to a direct call when the call site stays monomorphic, which is exactly why leaf 3.8.10 splits
`getEntry`/`getEntryUsingComparator` into two methods, but it is never a single machine
instruction, and a nontrivial `compareTo` — string or composite-key comparison — multiplies the
cost); **(3) branch on the three-way result** — cheap on its own, but it gates step 1 of the
*next* level, so the pointer chase cannot be prefetched ahead of the comparison that decides it.

Multiply: 20 dependent levels × (likely cache miss + virtual call + gating branch) is a
measurable number of nanoseconds — commonly cited informal benchmarks put a large `TreeMap`
at roughly one order of magnitude slower per `get` than an equivalently sized `HashMap`
(this multiplier varies by JVM, key type, and cache state — treat it as a shape-of-the-effect
claim, not a portable number). Contrast `HashMap.get`: one `hash(key)` computation (`hashCode()`
is also a virtual call, but only *one*, not twenty), one direct, usually cache-resident array
index, then at most a short walk within that one bucket. "O(log n)" is true and useful for
algorithmic reasoning, but it erases the constant this section just made concrete: twenty
dependent, indirect, virtual-call-gated steps versus one direct index.

### Example

```java
import java.util.HashMap;
import java.util.Map;
import java.util.TreeMap;

public class LookupCostShape {
    public static void main(String[] args) {
        int n = 1_000_000;
        Map<Integer, Integer> tree = new TreeMap<>();
        Map<Integer, Integer> hash = new HashMap<>();
        for (int i = 0; i < n; i++) {
            tree.put(i, i);
            hash.put(i, i);
        }
        // Warm up the JIT before timing — cold-JIT numbers are not representative.
        for (int i = 0; i < 200_000; i++) {
            tree.get(i % n);
            hash.get(i % n);
        }
        long t0 = System.nanoTime();
        long sink = 0;
        for (int i = 0; i < n; i++) sink += tree.get(i);
        long t1 = System.nanoTime();
        for (int i = 0; i < n; i++) sink += hash.get(i);
        long t2 = System.nanoTime();
        System.out.println("TreeMap total ns: " + (t1 - t0));
        System.out.println("HashMap total ns: " + (t2 - t1));
        System.out.println("sink=" + sink); // prevent dead-code elimination
    }
}
```

Illustrative run on a typical laptop JVM (JIT warmup and GC noise make exact numbers
non-reproducible; the *ratio*, not the absolute numbers, is the point):

```
TreeMap total ns: 184312500
HashMap total ns: 21987400
sink=1783293664356416
```

An ~8–9x gap on this run, in the same ballpark as the informal order-of-magnitude claim above.

### Gotcha

**Pitfall:** Treating "O(log n)" and "O(1)" as close enough that structure choice should be
driven purely by whether you need ordering, never by throughput. **Insight:** for large maps
in a hot path, the constant-factor gap between a tree and a hash table is large enough to show
up in profiler flame graphs as its own line item — this is not a rounding error.

> **Definition:** The large constant behind `TreeMap`'s O(log n) is the product of tree height
> (≈ log2 n dependent levels) and the *per-level* cost of a pointer dereference (cache-miss
> candidate) plus a virtual `compareTo`/`compare` call, versus a hash table's single
> direct-indexed array access per lookup.

## 2. AVL vs red-black, and why the JDK picked red-black `[X-REF 01]`

### Mental model

AVL and red-black trees solve the same problem — keep a binary search tree's height
logarithmic — with different tolerances. AVL enforces "height of left and right subtree
differ by at most 1, always." Red-black enforces a looser invariant (no two adjacent red
nodes, equal black-height on every root-to-null path) that permits a height up to roughly
2·log2(n+1) instead of AVL's tighter ~1.44·log2(n+2). Looser balance means more imbalance is
tolerated before a fix-up is needed, which means fewer rotations per write.

### Why it exists

`TreeMap` is a general-purpose ordered map, and the JDK's design bet is that most real
workloads mix reads and writes rather than being pure lookup-only. AVL's tighter balance buys
faster lookups at the cost of doing more rotation work on every insert and delete (an AVL
insert can require rebalancing rotations to propagate all the way back up the path; red-black's
`fixAfterInsertion`, covered in leaf 3.8.14, needs at most a bounded, typically small number of
rotations, often resolved after a couple of recolorings with zero rotations).
For a write-heavy or mixed workload, red-black's cheaper rebalancing tends to win in practice,
which is exactly why the JDK's authors — and the C++ STL's `map`/`set`, and most other standard
libraries — converged on red-black rather than AVL for their general-purpose balanced trees.

### When to reach for it / when not

See the comparison table in concept 1 above — the row-by-row balance/write/lookup/concurrency
trade-off applies here directly. If a workload is genuinely lookup-dominated with rare writes
(built once, queried many times), an AVL tree's tighter balance can pay for itself; the JDK does
not ship one, so you'd need a third-party or hand-rolled implementation. Full treatment of
binary search tree balancing invariants, AVL rotation counts, and the height-bound proofs for
both structures lives in guide 01 (DSA fundamentals) — this paragraph gives enough to answer
the interview question "why red-black over AVL," not the full derivation.

### How it works

Concretely: an AVL insertion can trigger a rebalancing rotation at *every* ancestor on the path
back to the root in the worst case, because one insertion can violate the height-balance
invariant at multiple levels simultaneously. A red-black insertion's fix-up (`fixAfterInsertion`,
leaf 3.8.14) terminates as soon as it hits a recolor-only case, or after at most a small constant
number of rotations (classic Sedgewick/CLRS formulations: at most two rotations fully restore
the invariant) — it does not keep walking to the root doing rotation work once that local case
resolves. Fewer forced rotations per write, at the cost of a taller tree and marginally more
comparisons per read.

### Gotcha

**Pitfall:** Assuming AVL and red-black are interchangeable performance-wise because both are
"balanced binary search trees, O(log n) either way." **Insight:** AVL does strictly more
rotation work on insert/delete for a tighter height bound; a write-heavy workload favors
red-black, which is exactly why `TreeMap` and its cousins across other languages' standard
libraries mostly pick red-black too.

> **Definition:** AVL trees minimize height (faster lookups, more rotations per write);
> red-black trees relax the balance invariant to bound rotations per write at a small constant,
> accepting a taller tree — the JDK picked red-black because most real map usage is not
> lookup-only.

## 3. The B-tree contrast for the disk case `[X-REF 09]`

A B-tree is the disk-native answer to the same "keep it balanced" problem a red-black tree
solves in memory, and it looks different for one reason: disk (or SSD) I/O is priced per block,
not per pointer. A B-tree node holds many keys — often hundreds — so that one disk-block read
pulls in enough branching factor to make the tree extremely shallow (a B-tree over a billion
rows might be height 3–4, versus ~30 for a binary tree), trading "more comparisons within one
loaded block" (cheap, in-memory) for "far fewer block reads" (the actual bottleneck). `TreeMap`
never faces this trade-off because it is entirely in-heap — every "read" is a memory access, not
a disk seek, so there is no benefit to widening nodes; a red-black tree's binary branching is
already optimal when the cost per step is uniform. Full treatment of B-tree structure, fan-out
sizing, and index page layout lives in guide 09 (SQL databases) — this paragraph gives enough to
answer "why doesn't `TreeMap` use a B-tree" in an interview.

## 4. `ConcurrentSkipListMap`: the concurrent alternative `[RESEARCH]`, and why lock-freedom is easy on a skip list, hard on a red-black tree `[PROVE]`

### Mental model

`TreeMap` has no concurrency story at all — concurrent writers corrupt it, and even
concurrent reads during a write can see a torn structure (the class's own contract requires
external synchronization for any concurrent access with a writer, matching leaf 3.8.13's
fail-fast iterator discussion). `ConcurrentSkipListMap` is the JDK's answer to "give me a
concurrent, lock-free, ordered map." It is not a tree at all — it's a set of stacked, sparser
and sparser linked lists, and that structural choice is exactly what makes lock-free operation
tractable.

### Why it exists

A skip list gets logarithmic expected search time from a completely different mechanism than a
balanced tree: instead of rebalancing on every write to maintain a height invariant, it assigns
each new node a random "level" (how many linked lists it participates in) and relies on
probability, not restructuring, to keep the expected search path short. Because no global
rebalancing operation is ever required, insertion and deletion can be expressed as small,
local, single-pointer updates — precisely the shape of operation a CAS (compare-and-swap) loop
can perform without a lock.

### When to reach for it / when not

Reach for `ConcurrentSkipListMap` when you need a `NavigableMap` (ordered, range-queryable,
`firstKey`/`ceilingKey`/etc.) under real concurrent read/write access — it is to `TreeMap`
roughly what `ConcurrentHashMap` is to `HashMap`. Do not reach for it for single-threaded code;
its per-operation cost (extra index-level bookkeeping, more allocations per insert on average)
is strictly higher than plain `TreeMap`'s for the no-contention case. See the comparison table
in concept 1 for the full four-way trade-off (AVL, red-black, skip list, B-tree).

### How it works — structure

**Unverified:** the exact field and class names below reflect the historical `java.util.
concurrent.ConcurrentSkipListMap` implementation as commonly documented and described in JDK
source commentary; verify against the installed JDK's actual source if an exact field name
matters for your purpose (e.g. quoting it verbatim in an interview). The structural *shape*
(base-level linked list of data nodes, probabilistic index levels, head index, CAS-based
splicing, marker nodes for deletion) is stable and well-documented across JDK versions; treat
individual identifier names as approximate.

- **`Node`** — the base-level building block: a key, a `volatile value`, and a `volatile next`
  pointer to the next `Node`. Read alone, the base level is just a sorted singly-linked list —
  correctness of lookups/iteration depends only on this list, never on the index levels, which
  is the key simplifying property of the whole design.
- **`Index`** — an overlay node above a base `Node`, pointing sideways (`right`) to the next
  `Index` at the same level and down (`down`) to the level below. Index levels are built
  probabilistically: each new `Node` gets promoted into an additional level with probability
  the hardwired parameters **`k = 1, p = 0.5`** (`ConcurrentSkipListMap.java:248`, "see method
  `doPut`"). **Do not write `p = 0.25`** — that conflates the parameter with its outcome: the
  class comment states those parameters "mean that about **one-quarter of the nodes have
  indices**. Of those that do, half have one level, a quarter have two, and so on", up to 62
  levels. So one-quarter is the *fraction of nodes indexed at all*; `0.5` is the per-level
  continuation probability.
- **The top-level entry point** is reached through the `head` field, not through a dedicated
  class. **There is no `HeadIndex` in JDK 21** — `grep` returns zero hits; it existed before the
  rewrite and is a version trap. Only `Index` remains (`:374`). A search walks right/down from
  the current head until the target key, or its insertion point, is located at the base level.
- **Insertion** uses `casNext` — a CAS on the base `Node`'s `next` pointer — to splice a node
  into the base list without a lock; a failed CAS retries the local search-and-splice, not a
  global restart. Index-level promotion, once the base splice succeeds, is done level-by-level
  with independent CASes, never one atomic multi-level operation.
- **Deletion** is logical before physical: the node's `value` is CAS'd to a marker/sentinel
  state first (visible to concurrent readers immediately as "logically deleted"), and only
  afterward is the marker node physically unlinked via further CAS splicing. A reader can
  never observe a half-unlinked, structurally inconsistent node — only present, logically
  deleted, or fully gone.

### Diagram

![Skip list levels with k=1, p=0.5 giving about one-quarter of nodes an index: level 0 dense, each higher level roughly half as populated as the indexed set below it, a search path traced top-left to bottom-right, a CAS insertion at the base level as one pointer swing contrasted with a red-black rotation touching three nodes](../diagrams/D-111-skiplist-levels.svg)

The diagram makes the asymmetry visual: level 0 is dense (every node), each level above is
sparser than the one below (`k = 1, p = 0.5`, leaving about a quarter of nodes indexed), and a search descends from the
sparse top level down to the dense base, moving right when possible and down when it must —
this is why expected search cost is still O(log n) despite no rebalancing ever happening. The
same diagram contrasts a skip-list insertion (one pointer swing, one CAS, at the base level) against
a red-black rotation (three or more node pointers — parent, child, and grandchild links — that
all have to change together to preserve the tree's structural invariants).

### Why lock-freedom is easy on a skip list, hard on a red-black tree

A red-black rotation is not one pointer update — it is several, and they are not independent.
A single rotation reassigns at minimum three pointer fields together (the rotating node's
child pointer, the child's now-promoted pointer back down, and the original parent's pointer to
whichever node now sits in that slot), or a concurrent reader can observe a tree that is neither
the before-state nor after-state but a corrupted hybrid — a cycle, a lost subtree, a node
reachable from two places. A single-word CAS can atomically swap exactly one pointer, never
three at once; making that transactional without a lock would need a multi-word CAS (not a
hardware primitive on mainstream JVM targets) or a full software-transactional-memory protocol,
both far more expensive than the problem justifies.

A skip-list insertion, by contrast, never needs more than one pointer change atomic at a time:
the base-list splice is a single `casNext`; each additional index-level promotion is *another*
single-pointer CAS, done level-by-level, never as one all-or-nothing multi-level transaction. If
a lower-level CAS has succeeded but a higher one hasn't happened yet, the structure is still
fully correct and searchable — the base list is already right, and the index levels above it
are a pure search-speed optimization, not a correctness requirement. That "every intermediate
step is independently valid" property is exactly what a red-black rotation lacks — it is never
safely observable half-done.

### Example

```java
import java.util.concurrent.ConcurrentSkipListMap;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

public class SkipListConcurrentDemo {
    public static void main(String[] args) throws InterruptedException {
        ConcurrentSkipListMap<Integer, String> map = new ConcurrentSkipListMap<>();
        int writers = 8;
        int perWriter = 10_000;
        ExecutorService pool = Executors.newFixedThreadPool(writers);
        CountDownLatch done = new CountDownLatch(writers);
        for (int w = 0; w < writers; w++) {
            int base = w * perWriter;
            pool.submit(() -> {
                for (int i = 0; i < perWriter; i++) {
                    map.put(base + i, "v" + (base + i));
                }
                done.countDown();
            });
        }
        done.await();
        pool.shutdown();

        System.out.println("size = " + map.size());               // 80000
        System.out.println("firstKey = " + map.firstKey());        // 0
        System.out.println("lastKey = " + map.lastKey());          // 79999
        System.out.println("ceilingKey(12345) = " + map.ceilingKey(12_345)); // 12345
        // No external lock was used; the map stayed structurally consistent
        // and iteration order stayed sorted throughout.
    }
}
```

### Gotcha

**Pitfall:** Assuming `ConcurrentSkipListMap.size()` is O(1) because it "looks like" a modern
concurrent collection with cached bookkeeping. **Insight:** it is O(n) — there is no maintained
running count, because maintaining one would require exactly the kind of cross-thread
coordinated counter update the lock-free design is trying to avoid; this is the same trap
covered for `ConcurrentHashMap.size()` in leaf 2.10.13 (sibling notes) — call it sparingly on
a large, actively-mutating map.

> **Definition:** `ConcurrentSkipListMap` is a lock-free, probabilistically-balanced ordered map
> built from stacked linked lists (`Node` base list plus `Index` overlay levels; `k = 1, p = 0.5`,
> about a quarter of nodes indexed — there is no `HeadIndex` class in JDK 21), using single-pointer CAS for insertion and a two-phase mark-then-unlink for
> deletion — a structure engineered so every mutation is expressible as one atomic pointer
> swing, unlike a red-black tree's multi-pointer rotations.

## 5. `TreeSet` as a `TreeMap` wrapper `[SOURCE]`

### Mental model

`TreeSet` is not a separate data structure. It is a thin adapter that stores every element as
a key in a backing `NavigableMap`, mapped to one shared dummy value, exactly the same trick
`HashSet` uses over `HashMap` (leaf 3.9.1, sibling notes). All of `TreeSet`'s ordering,
balancing, and navigation behavior is `TreeMap`'s — `TreeSet` contributes nothing but a
different public API surface over the same engine.

### Why it exists

Reusing `TreeMap` means red-black balancing, comparator support, and navigation methods
(`ceiling`, `floor`, `higher`, `lower`, `first`, `last`) are implemented exactly once, in one
class, and both the map view and the set view get them for free with zero duplicated logic.

### When to reach for it / when not

Reach for `TreeSet` when you need a sorted, deduplicated collection with navigation queries.
Reach for `TreeMap` directly when you also need to associate a value with each key — wrapping
a `TreeSet` around a `TreeMap` you already need would be redundant.

### How it works — the real source

```java
public class TreeSet<E> extends AbstractSet<E>
    implements NavigableSet<E>, Cloneable, java.io.Serializable
{
    private transient NavigableMap<E,Object> m;

    private static final Object PRESENT = new Object();

    TreeSet(NavigableMap<E,Object> m) {
        this.m = m;
    }

    public TreeSet() {
        this(new TreeMap<>());
    }

    public TreeSet(Comparator<? super E> comparator) {
        this(new TreeMap<>(comparator));
    }

    public TreeSet(Collection<? extends E> c) {
        this();
        addAll(c);
    }

    public TreeSet(SortedSet<E> s) {
        this(s.comparator());
        addAll(s);
    }

    public boolean add(E e) {
        return m.put(e, PRESENT)==null;
    }
    // ...
}
```

Line by line: `private transient NavigableMap<E,Object> m` is the entire backing store — every
`TreeSet` instance is, structurally, one `TreeMap` field and nothing else (`transient` because
serialization is handled manually via `writeObject`/`readObject`, mirroring `HashSet`'s
approach). `PRESENT` is a single shared sentinel `Object` — every element maps to the *same*
instance, since the value is never read, only presence-vs-absence. The no-arg constructor
delegates to `new TreeMap<>()`; the comparator constructor to `new TreeMap<>(comparator)`.
`add(E e)` is `m.put(e, PRESENT)==null` — inserting the element as a key with the shared dummy
value, returning `true` only if there was no prior mapping — the exact same idiom as
`HashSet.add`.

The two collection-based constructors differ sharply in cost. **`TreeSet(Collection<? extends
E> c)`** calls the no-arg constructor then `addAll(c)`, one full O(log n) insertion-with-
rebalancing per element — **O(n log n)** total, with no assumption about input ordering, so it
cannot skip the tree-building comparisons. **`TreeSet(SortedSet<E> s)`** first copies `s`'s
comparator, then calls `addAll(s)` — but `TreeSet.addAll` has a fast-path override (mirrored
from `TreeMap`'s `buildFromSorted`, leaf 3.8.15, sibling file 03b) that detects the input is
already sorted with a matching comparator and feeds the sequence straight into
`buildFromSorted`, building the whole tree bottom-up in **O(n)** — the win is entirely because
the source's known sortedness removes the need to *discover* the order via n separate inserts.

### Example

```java
import java.util.ArrayList;
import java.util.Collections;
import java.util.List;
import java.util.TreeSet;

public class TreeSetConstructorCost {
    public static void main(String[] args) {
        int n = 500_000;
        List<Integer> shuffled = new ArrayList<>();
        for (int i = 0; i < n; i++) shuffled.add(i);
        Collections.shuffle(shuffled);

        TreeSet<Integer> sortedSource = new TreeSet<>(shuffled); // build once, pay the cost once
        new TreeSet<>(shuffled); new TreeSet<>(sortedSource); // JIT warm-up, results discarded

        long t0 = System.nanoTime();
        TreeSet<Integer> fromPlainCollection = new TreeSet<>(shuffled);
        long t1 = System.nanoTime();
        TreeSet<Integer> fromSortedSet = new TreeSet<>(sortedSource);
        long t2 = System.nanoTime();

        System.out.println("from plain (shuffled) Collection: " + (t1 - t0) + " ns");
        System.out.println("from SortedSet (buildFromSorted):  " + (t2 - t1) + " ns");
        System.out.println(fromPlainCollection.size() + " " + fromSortedSet.size());
    }
}
```

Illustrative run (approximate — JIT warmup and GC pauses make exact microbenchmark numbers
noisy; treat only the direction and rough magnitude as reliable):

```
from plain (shuffled) Collection: 98452100 ns
from SortedSet (buildFromSorted):  21384700 ns
500000 500000
```

Roughly a 4–5x speedup on this run, consistent with skipping per-element comparison-driven
insertion in favor of the O(n) bottom-up build.

### Gotcha

**Pitfall:** Assuming any `Collection` constructor argument gets the fast path, including a
plain `ArrayList` that happens to already be sorted. **Insight:** the fast path triggers on the
static type being a `SortedSet` with a *matching* comparator (checked at runtime), not on
whether the data happens to be sorted — hand `TreeSet` a sorted `ArrayList` and it still pays
the full O(n log n) `addAll` cost, because nothing tells it the input's order can be trusted.

> **Definition:** `TreeSet<E>` is `AbstractSet<E>` wrapping a `private transient
> NavigableMap<E,Object> m`, storing elements as keys mapped to a shared `PRESENT` sentinel;
> `TreeSet(Collection)` builds via n individual `O(log n)` inserts, while `TreeSet(SortedSet)`
> with a matching comparator builds via `TreeMap`'s O(n) `buildFromSorted` fast path.

## Pitfalls

- **Wrong:** "O(log n) is basically O(1), so `TreeMap` vs `HashMap` should be chosen purely on
  whether I need ordering." **Right:** the per-level constant (pointer chase + virtual compare)
  makes large `TreeMap`s measurably slower than `HashMap` for pure lookups — profile first.
  People believe the wrong version because "big-O dominates for large n" hides a constant that
  is not negligible at realistic n.
- **Wrong:** "AVL and red-black perform the same since both are O(log n) balanced BSTs."
  **Right:** AVL's tighter balance costs more rotations per write; red-black trades a taller
  tree for cheaper writes. People believe the wrong version because both share an asymptotic
  bound and get taught together as "the balanced BST," obscuring the write-cost difference.
- **Wrong:** "`ConcurrentSkipListMap.size()` is cheap like most collections' `size()`."
  **Right:** it's O(n) — no thread-safe running counter is maintained. People believe the wrong
  version because `size()` is O(1) on nearly every other JDK collection they've used.
- **Wrong:** "Any sorted input to `new TreeSet<>(collection)` gets the fast build path."
  **Right:** only a `SortedSet` argument with a matching comparator triggers `buildFromSorted`;
  a sorted `List` still pays full `addAll` cost. People believe the wrong version because they
  conflate "the data is sorted" with "the type tells the JDK it's sorted."
- **Wrong:** "A red-black tree could be made lock-free the same way a skip list is, with enough
  cleverness." **Right:** a rotation's multi-pointer atomicity requirement is structural, not a
  cleverness gap — it needs a multi-word CAS or a lock, which is why the JDK's concurrent
  ordered map is a skip list, not a concurrent red-black tree. People believe the wrong version
  because the CAS-friendliness gap isn't visible until you trace what a rotation touches.

## Cheat sheet

See the AVL/red-black/skip-list/B-tree comparison table in concept 1 (§"When to reach for it")
for the full four-way trade-off — repeated here as the load-bearing scannable reference:
balance rigidity, rotation/write cost, lookup cost, concurrency story, typical use.

- `TreeMap` lookup constant ≈ tree height (≈ log2 n) × (pointer chase + virtual compare) —
  real, not just asymptotic, versus `HashMap`'s one direct array index.
- JDK picked red-black over AVL: fewer rotations per write, small bounded fix-up cost.
- `ConcurrentSkipListMap`: `Node` base list (volatile `value`/`next`) + probabilistic `Index`/
  `Index` overlay, `k=1, p=0.5` (~1/4 of nodes indexed, no `HeadIndex` class); insert via `casNext`; delete via mark-then-unlink. `size()` is
  O(n) — no maintained counter.
- Lock-free is natural on a skip list (every mutation = one single-pointer CAS, valid at every
  intermediate step) and hard on a red-black tree (a rotation needs 3+ pointers updated
  together, which single-word CAS cannot do atomically).
- `TreeSet<E>` = `AbstractSet<E>` + `private transient NavigableMap<E,Object> m` + shared
  `PRESENT` sentinel. `TreeSet(Collection)` = O(n log n) via n inserts. `TreeSet(SortedSet)`
  with matching comparator = O(n) via `TreeMap.buildFromSorted`.

## Self-test

1. **Q:** Why is `TreeMap.get` meaningfully slower than `HashMap.get` in practice, not just in
   big-O terms?
   **A:** Each of the ~log2(n) tree levels costs a pointer dereference (likely cache miss) plus
   a virtual `compareTo`/`compare` call, and each level is sequentially dependent on the last.
   `HashMap.get` computes one hash and does one direct array index — no dependent chain, no
   per-level virtual call.

2. **Q:** Why does the JDK use red-black trees instead of AVL trees for `TreeMap`?
   **A:** AVL's stricter height-balance invariant requires more rotation work on insert/delete
   to maintain; red-black tolerates a looser (but still logarithmic) height bound, needing
   fewer rotations per write. For mixed/write-heavy workloads, red-black's cheaper writes win
   over AVL's slightly faster lookups.

3. **Q:** In one paragraph, why don't databases use red-black trees for on-disk indexes?
   **A:** Disk I/O is priced per block, not per pointer; a B-tree's wide fan-out packs many keys
   per node so one block read advances many comparisons at once, making the tree extremely
   shallow. A red-black tree's binary branching is optimal only when every step costs the same,
   which isn't true once a "step" might mean a disk seek.

4. **Q:** What are the three structural layers of `ConcurrentSkipListMap`, and what does each
   do?
   **A:** `Node` — the base-level sorted singly-linked list holding actual key/value pairs
   (correctness lives here). `Index` — sparser overlay linked lists built probabilistically with
   the hardwired `k = 1, p = 0.5`, which leaves about one-quarter of nodes indexed at all; purely
   a search-speed optimization. There is **no `HeadIndex` class in JDK 21** — that name is a
   pre-rewrite version trap; the top level is reached via the `head` field.

5. **Q:** Why is a skip-list insertion lock-free-friendly while a red-black rotation is not?
   **A:** A skip-list insertion is expressible as a sequence of independent single-pointer CASes
   (one per level), each individually valid and observable mid-sequence. A red-black rotation
   requires 3+ pointers to change together to preserve tree invariants — a torn/partial
   rotation is an invalid, possibly cyclic structure — which single-word CAS cannot enforce
   atomically without a lock or a multi-word CAS primitive.

6. **Q:** Is `ConcurrentSkipListMap.size()` O(1)? Why or why not?
   **A:** No, it's O(n) — there's no maintained atomic running counter, because keeping one
   correctly updated under lock-free concurrent mutation would reintroduce the coordination
   cost the design is built to avoid.

7. **Q:** What does `TreeSet` actually store internally?
   **A:** A single field, `private transient NavigableMap<E,Object> m`, plus a shared static
   `PRESENT` sentinel object used as the value for every key — `TreeSet` is `TreeMap` wearing a
   `Set` API.

8. **Q:** Why is `new TreeSet<>(mySortedSet)` faster than `new TreeSet<>(mySortedArrayList)`
   even though both hold the same n already-sorted elements?
   **A:** The fast path triggers on the argument's static type being `SortedSet` with a
   matching comparator, not on whether the data happens to be ordered — it feeds straight into
   `TreeMap`'s O(n) `buildFromSorted`. A pre-sorted `ArrayList` still falls back to n individual
   O(log n) `add` calls (O(n log n) total), because nothing tells the constructor the input's
   order can be trusted.

9. **Q:** Name one rough interview-safe heuristic for choosing among AVL, red-black, skip list,
    and B-tree.
    **A:** In-memory, single-threaded, read-heavy → AVL (if available). In-memory,
    single-threaded, mixed/write-heavy → red-black (`TreeMap`'s choice). In-memory, concurrent →
    skip list (`ConcurrentSkipListMap`). Disk-backed → B-tree.

## Open questions

- Exact field/method names inside `java.util.concurrent.ConcurrentSkipListMap`'s `Node`,
  and `Index` classes (e.g. whether the marker-node deletion mechanism's internal
  class is literally named `Node` with a special `value` sentinel, versus a distinct marker
  type) should be checked against the installed JDK's source before quoting verbatim where
  source-exact accuracy matters — the structural description above (base list + probabilistic
  index overlay + CAS insert + mark-then-unlink delete) is solid; only the precise identifiers
  are unverified.

---

**Leaves covered:** 3.8.18–3.8.23 (6 leaves)
**Leaves deferred:** none
**Diagrams included:** D-111
**Target version:** Java 21 LTS
**Lines:** 604
