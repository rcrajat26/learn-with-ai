# 01 — DSA Fundamentals

Mechanism-level notes on the data structures and patterns that carry ~90% of coding rounds.
The goal is not to memorize solutions but to know *why* each structure has the cost it has, so
you can derive the right one under pressure.

---

## 1. Complexity: Big-O, amortized, and what people get wrong

Big-O describes how cost grows as input grows, ignoring constants. `O(n)` and `O(100n)` are the
same class. That is a deliberate abstraction, and it is also why an `O(n log n)` sort can beat an
`O(n)` algorithm at realistic sizes.

The classes you must place instantly:

| Class | Name | Typical source |
|---|---|---|
| O(1) | constant | array index, hash lookup, stack push |
| O(log n) | logarithmic | binary search, balanced-tree descent, heap sift |
| O(n) | linear | single scan |
| O(n log n) | linearithmic | comparison sort, heapify-then-extract-all |
| O(n²) | quadratic | nested scan over all pairs |
| O(2ⁿ) | exponential | subset enumeration, naive recursion without memo |
| O(n!) | factorial | permutation enumeration |

**Space complexity counts the recursion stack.** A recursive DFS on a skewed tree of n nodes is
O(n) space even though you allocated nothing.

### Amortized analysis — the mechanism

`ArrayList.add` is O(1) *amortized*, not O(1) worst case. Mechanism: the backing array doubles when
full. Copying n elements costs O(n), but that cost is paid once per doubling. Over n appends, total
copy work is n/2 + n/4 + n/8 + … < n, so each append averages a constant. One individual append can
still be O(n).

**Trap:** "amortized O(1)" is not "O(1) with a bad constant". It means individual operations can be
linear; only the *sequence* averages out. If you are writing latency-sensitive code, the tail matters
and you pre-size the list.

The same argument gives amortized O(1) for HashMap insertion (resize doubles) and for the classic
two-stack queue (each element is moved between stacks at most once).

**Trap:** you cannot amortize across *different* structures or reset the structure between operations.
If something clears and refills, each refill pays afresh.

---

## 2. Arrays and strings

An array is a contiguous block. Index access is O(1) because the address is `base + i * elementSize` —
one multiply and one add, no search. Contiguity is also why arrays are cache-friendly: a cache line
fetch brings neighbours along, so linear scans of an array crush linear scans of a linked list even at
identical Big-O.

Insertion/deletion in the middle is O(n) because everything after the point must shift.

In Java, `String` is immutable and backed by a byte array (compact strings since Java 9: Latin-1
one byte per char, UTF-16 two bytes otherwise). Every concatenation allocates a new object.

**Trap:** building a string in a loop with `+` is O(n²) — each concat copies the whole accumulated
string. Use `StringBuilder`, which is an amortized-doubling char buffer. The compiler optimizes `+`
inside a single expression, not across loop iterations.

Common array techniques: prefix sums (turn range-sum queries into O(1) after O(n) preprocessing),
difference arrays (turn range updates into O(1)), in-place reversal, and the cyclic-rotation trick
(reverse whole, reverse parts).

---

## 3. Hashing

A hash table maps a key to a bucket index via `hash(key) mod capacity`. Average O(1) lookup because
you jump straight to a bucket. Worst case O(n) when everything collides into one bucket — which is
why Java's HashMap converts long collision chains into red-black trees (see guide 02).

What makes a good hash: uniform distribution, cheap to compute, and consistent with equality. The
hard contract: **equal objects must have equal hash codes**. The reverse need not hold.

**Trap:** using a mutable object as a key and then mutating a field that participates in `hashCode`.
The entry is now in the wrong bucket and is unreachable — `map.get(sameObject)` returns null while
the entry still occupies memory.

Interview uses of hashing: frequency counting, seen-set deduplication, complement lookup (two-sum),
grouping by a canonical key (anagrams keyed by sorted characters), and index maps for O(1)
"where did I last see this".

---

## 4. Two pointers and sliding window

**Two pointers** applies when the array is sorted or when you can meaningfully move from both ends.
Mechanism: each pointer only moves in one direction, so the total work is O(n) rather than the O(n²)
of examining all pairs. In sorted two-sum, if `a[l] + a[r] > target` then no pair using `r` can work
with any larger left index, so you can safely discard `r` — that discard is what buys the linearity.

**Sliding window** is two pointers where the right end expands and the left end contracts to restore
an invariant. Total work is O(n) because each index enters and leaves the window at most once.

Fixed window: move both ends together, maintain a running aggregate.
Variable window: expand right until the invariant breaks, then shrink left until it holds again.

**Trap:** sliding window silently breaks when the constraint is not monotonic. "Longest subarray with
sum ≤ k" works with all-positive numbers because adding an element can only increase the sum. Add
negatives and shrinking from the left no longer reliably fixes the violation — you need prefix sums
plus a hash map or a monotonic deque instead.

---

## 5. Stack and the monotonic stack

A stack is LIFO. Push/pop/peek are O(1). Its real role is remembering "pending" items whose fate
depends on something you have not seen yet: matching brackets, undo, expression evaluation, and the
call stack itself.

The **monotonic stack** is the pattern worth internalizing. You keep the stack sorted (increasing or
decreasing). When a new element violates the order, you pop — and each pop is the moment you *resolve*
an answer.

Next-greater-element: keep a decreasing stack of indices. When `a[i]` exceeds the top, `a[i]` is the
next greater element for that popped index. Every element is pushed once and popped once, so O(n)
despite the inner while loop.

This pattern solves: next greater/smaller in either direction, largest rectangle in a histogram,
trapping rain water, stock span, and "remove k digits to make the smallest number".

**Trap:** people see the nested `while` and call it O(n²). Count pushes, not loop iterations — the
amortized argument is the whole point.

In Java use `ArrayDeque` as your stack, not `java.util.Stack`. `Stack` extends `Vector`, is
synchronized on every call, and iterates bottom-to-top (the wrong order for a stack).

---

## 6. Queue and deque

FIFO. Enqueue and dequeue O(1). The essential use is BFS.

A **deque** allows O(1) at both ends and gives you the monotonic deque: a window-maximum structure.
For sliding window maximum, keep indices in decreasing value order; pop from the back anything smaller
than the incoming element (it can never be a maximum while the newer, larger element is in range), and
pop from the front anything that has fallen out of the window. Front is always the current max. O(n).

`ArrayDeque` is a circular buffer over an array — no per-node allocation, cache-friendly, and it is
the correct default for both stack and queue in Java.

**Trap:** `ArrayDeque` rejects `null`. It uses null as its empty-slot sentinel. `LinkedList` allows
null. If a null slips into a queue-based algorithm you get an NPE at insert time, not at read time.

---

## 7. Linked lists

A node holds a value and a pointer. Insert/delete at a known node is O(1) — just repoint. Access by
index is O(n) — you must walk. No contiguity means poor cache behaviour and ~16 bytes of object header
plus pointer overhead per element.

Three mechanisms carry nearly every linked-list question:

1. **Dummy head node.** Allocate a fake node before the real head so that deleting or inserting at the
   head needs no special case. This removes most off-by-one bugs.
2. **Fast/slow pointers (Floyd).** Slow moves one, fast moves two. If there is a cycle, they must meet
   because the gap closes by exactly one per step inside the loop. Fast reaching null means no cycle.
   Same technique finds the middle in one pass.
3. **Iterative reversal.** Three pointers — prev, curr, next — advance in lockstep. Learn this cold;
   it is a building block for palindrome check, reorder list, and k-group reversal.

**Trap:** in a cycle-detection meeting-point problem, the meeting point is not the cycle start. To find
the start, reset one pointer to head and advance both one step at a time; they meet at the entry. That
follows from the distance algebra, not from intuition.

---

## 8. Trees and BSTs

A binary tree node has up to two children. Height h determines cost of most operations. A balanced
tree has h = O(log n); a degenerate one (inserting sorted data into an unbalanced BST) has h = n and
every operation degrades to linear.

Traversals: preorder (root, left, right) for copying/serializing; inorder (left, root, right) which on
a BST yields sorted order; postorder (left, right, root) for deleting or for computing values that
depend on children; level-order via BFS queue.

**BST invariant:** everything in the left subtree is less than the node, everything in the right is
greater. Search, insert, delete are O(h).

**Trap:** validating a BST by comparing each node only to its immediate children is wrong. A node deep
in the left subtree can be larger than an ancestor while still satisfying its local parent check. You
must carry down a (min, max) bound range, or do an inorder traversal and verify it is strictly
increasing.

Self-balancing variants (AVL, red-black) perform rotations on insert/delete to keep h logarithmic.
Java's `TreeMap` is a red-black tree; you should know it guarantees O(log n) and gives you ordered
navigation (`floorKey`, `ceilingKey`, `subMap`).

---

## 9. BFS and DFS

Same skeleton, different container: BFS uses a queue, DFS uses a stack (explicit or the call stack).

**BFS explores by distance.** On an unweighted graph it therefore finds the shortest path — the first
time you reach a node is via the fewest edges. Process level by level by capturing `queue.size()`
before the inner loop. Space is O(width), which can be huge on a wide graph.

**DFS explores by depth.** It is the tool for connectivity, cycle detection, topological sort, and
backtracking. Space is O(depth). On deep graphs recursion risks `StackOverflowError`; convert to an
explicit stack.

Both need a `visited` set on graphs (trees do not need one, since there are no cycles).

**Trap:** marking visited at dequeue time in BFS instead of at enqueue time. The same node then gets
pushed multiple times before it is first processed, and the queue blows up on dense graphs. Mark when
you enqueue.

Multi-source BFS (seed the queue with all sources at distance 0) solves "nearest X to every cell" in
one pass — rotting oranges, walls and gates, 01-matrix.

---

## 10. Heaps and priority queues

A binary heap is a complete binary tree stored in an array. For index i: parent is `(i-1)/2`, children
are `2i+1` and `2i+2`. The heap property is that a parent compares ≤ (min-heap) to its children — it is
a *partial* order, not a sorted array.

- `peek` O(1) — root is the extreme.
- `offer` O(log n) — append at the end, sift up.
- `poll` O(log n) — swap root with last, shrink, sift down.
- `heapify` an existing array O(n), not O(n log n) — the bound comes from most nodes being near the
  bottom with short sift distances.

Uses: top-k (keep a size-k *min*-heap for the k largest — pop the smallest whenever size exceeds k,
giving O(n log k)), merge k sorted lists, running median with two heaps, Dijkstra's frontier,
scheduling by earliest deadline.

**Trap:** iterating a `PriorityQueue` does not give sorted order. Only repeated `poll()` does. Its
`toString` output looks random for the same reason.

---

## 11. Binary search and its variants

The core requires a monotonic predicate — some property that is false, false, …, true, true. Binary
search finds the boundary in O(log n).

Write it with the half-open convention to avoid infinite loops:

```java
int lo = 0, hi = n;           // hi exclusive
while (lo < hi) {
    int mid = lo + (hi - lo) / 2;   // avoids int overflow
    if (predicate(mid)) hi = mid;   // answer is mid or to the left
    else lo = mid + 1;              // answer is strictly right
}
return lo;                    // first index where predicate holds
```

**Trap:** `(lo + hi) / 2` overflows for large ints. Use `lo + (hi - lo) / 2`.

**Trap:** mixing `hi = mid` with `hi = n - 1` inclusive bounds. Pick one convention and never mix; the
infinite loop comes from a mid that never advances.

Variants: lower bound (first ≥ target), upper bound (first > target), search in a rotated sorted array
(one half is always sorted — decide which, then decide whether the target lies inside it), find peak
element, and **binary search on the answer** — when the answer is a number in a range and feasibility
is monotonic, e.g. "minimum capacity to ship packages in D days", "Koko eating bananas". Recognizing
"minimize the maximum" or "maximize the minimum" as a binary-search-on-answer signal is high-value.

Java's `Arrays.binarySearch` returns `-(insertionPoint) - 1` when absent, which is how you recover the
insertion point without a second pass.

---

## 12. Recursion

Every recursion needs a base case and a step that provably moves toward it. Each call frame holds
parameters and locals on the stack.

Think in terms of: what does this function *promise* to return for a subproblem? Trust the promise for
the smaller case, and only write the combination step. That is the whole trick to writing tree
recursion quickly.

**Tail recursion** is when the recursive call is the last operation. Many languages optimize it into a
loop; **the JVM does not**, so deep recursion in Java overflows regardless of tail position.

**Trap:** naive recursive Fibonacci is O(2ⁿ) because the call tree recomputes the same subproblems.
Adding a memo array collapses it to O(n). Recognizing overlapping subproblems is the bridge to DP.

Backtracking is recursion plus undo: choose, recurse, un-choose. The un-choose step is what lets you
reuse one mutable path buffer instead of copying at every level. Prune early — a good constraint check
before recursing is worth more than any micro-optimization. Canonical set: subsets, permutations,
combination sum, N-queens, word search, palindrome partitioning.

---

## 13. Dynamic programming (intro)

DP applies when a problem has **optimal substructure** (the optimum is built from optima of
subproblems) and **overlapping subproblems** (the same subproblem recurs).

Two forms:
- **Top-down memoization** — write the recursion, cache by state. Easier to derive; carries recursion
  depth cost.
- **Bottom-up tabulation** — fill a table in dependency order. No stack risk, and usually easier to
  space-optimize.

The real work is defining the **state**: what parameters uniquely identify a subproblem? Get that
right and the transition usually follows. Then find the recurrence, the base cases, and the iteration
order (every state must be computed before it is read).

Space optimization: if `dp[i]` only reads `dp[i-1]`, keep two rows, or one row updated in the correct
direction. In 0/1 knapsack you iterate capacity descending precisely so each item is used once;
ascending gives unbounded knapsack. That direction *is* the semantics.

Starter families: 1-D (climbing stairs, house robber, coin change), 2-D grid paths, string DP (edit
distance, LCS), interval DP, and subset/bitmask DP.

---

## 14. Greedy (intro)

Greedy takes the locally best choice and never reconsiders. It is correct only when an **exchange
argument** holds: any optimal solution can be transformed into the greedy one without getting worse.

Works: interval scheduling (sort by end time — earliest finish leaves the most room), Huffman coding,
fractional knapsack, minimum platforms.

Fails: 0/1 knapsack, coin change with arbitrary denominations (greedy on {1, 3, 4} for 6 gives 4+1+1 =
three coins, but 3+3 = two).

**Trap:** greedy that passes the sample cases is the most common wrong answer in interviews. If you
cannot articulate why the local choice is safe, say out loud that you are checking greedy validity and
then fall back to DP.

---

## 15. Graphs (intro)

Representations: adjacency list (`Map<Node, List<Node>>` or `List<List<Integer>>`) is O(V+E) space and
right for sparse graphs — the default. Adjacency matrix is O(V²) and right for dense graphs or O(1)
edge-existence checks.

Core algorithms and when they apply:

| Need | Algorithm | Cost |
|---|---|---|
| Shortest path, unweighted | BFS | O(V+E) |
| Shortest path, non-negative weights | Dijkstra (heap) | O(E log V) |
| Shortest path with negative edges | Bellman-Ford | O(VE) |
| All-pairs shortest paths | Floyd-Warshall | O(V³) |
| Ordering with dependencies | Topological sort (Kahn's or DFS) | O(V+E) |
| Connected components | DFS/BFS or union-find | O(V+E) |
| Minimum spanning tree | Kruskal (union-find) or Prim (heap) | O(E log E) |

**Trap:** Dijkstra is wrong with negative edge weights. It finalizes a node when popped, assuming no
cheaper path can appear later — negative edges break that assumption.

Cycle detection differs by direction: in a directed graph you need three colours (white/grey/black) or
a recursion-stack set, because revisiting a *finished* node is fine and only a back edge to a node
still on the stack is a cycle. In an undirected graph, any visited neighbour that is not your parent
is a cycle.

Kahn's algorithm doubles as cycle detection: if you process fewer than V nodes, a cycle exists.

---

## 16. Tries (intro)

A trie stores strings by character path. Each node holds up to 26 (or map-based) children plus an
`isEnd` flag. Insert and search are O(L) in the key length — independent of how many words are stored.

Wins over a hash set for: prefix queries, autocomplete, longest common prefix, and word-search-on-grid
where you prune the DFS the moment the accumulated path leaves the trie. That pruning is the reason
Word Search II is tractable.

Cost: memory. A dense child array per node is wasteful for sparse alphabets; use a `HashMap` per node
when the alphabet is large.

---

## 17. Union-find (disjoint set union)

Maintains disjoint sets with two operations: `find(x)` returns the set representative, `union(a,b)`
merges two sets.

Two optimizations make it near-constant:
- **Path compression** in `find`: point every node on the path directly at the root.
- **Union by rank/size**: attach the smaller tree under the larger, keeping depth low.

Together they give O(α(n)) amortized, where α is the inverse Ackermann function — under 5 for any
realistic n, so treat it as effectively constant.

```java
int find(int x) { return parent[x] == x ? x : (parent[x] = find(parent[x])); }
```

Uses: connected components on a stream of edges, Kruskal's MST, cycle detection in undirected graphs,
accounts merge, number of islands II, redundant connection.

**Trap:** union-find cannot delete edges or answer path queries. It only answers "same set?".

---

## 18. Pattern recognition signals

The fastest interview skill is mapping problem phrasing to structure.

| Signal in the problem | Reach for |
|---|---|
| Sorted array, find a pair/triple | Two pointers |
| Contiguous subarray/substring with a constraint | Sliding window |
| "Top k", "k largest/smallest", "k closest" | Heap of size k |
| "Kth smallest" in a sorted structure | Heap or binary search on value |
| Next greater/smaller, spans, histogram | Monotonic stack |
| Shortest path, unweighted, fewest steps | BFS |
| All paths, combinations, permutations, "generate all" | Backtracking |
| Count the ways, min/max cost, "can you reach" | DP |
| Overlapping intervals, merging, scheduling | Sort by start or end, then sweep |
| Prefix/autocomplete/dictionary matching | Trie |
| Dynamic connectivity, grouping | Union-find |
| Ordering with prerequisites | Topological sort |
| "In-place, O(1) extra space" on an array | Index-as-hash, swapping, or reversal |
| Cycle in a linked list or a functional mapping | Floyd fast/slow |
| Answer is a number, feasibility is monotonic | Binary search on the answer |
| Palindrome, expand from centre | Two pointers from each index |

**Trap:** anchoring on the first pattern that fits. Confirm the constraints support it — n = 10⁵ rules
out O(n²); n = 20 actively hints at bitmask/exponential; n = 10⁹ means the answer is math or binary
search, not iteration. Read the constraints *before* choosing.

---

## Atomic concept checklist

- [ ] Amortized O(1) means the sequence averages constant; a single operation can still be O(n) — ArrayList doubling is the canonical proof.
- [ ] Recursion stack counts toward space complexity.
- [ ] String `+` in a loop is O(n²); StringBuilder is amortized linear.
- [ ] Equal objects must have equal hash codes; mutating a key field after insertion strands the entry.
- [ ] Sliding window requires a monotonic constraint — negatives break "sum ≤ k".
- [ ] A monotonic stack is O(n) because each element is pushed and popped at most once, despite the inner while loop.
- [ ] `ArrayDeque` is the correct Java stack and queue; it forbids null, and `java.util.Stack` iterates in the wrong order.
- [ ] Fast/slow pointers meet inside a cycle; the meeting point is not the cycle start — reset one pointer to head to find it.
- [ ] Validating a BST needs min/max bounds propagated down, not local parent comparisons.
- [ ] BFS finds shortest paths on unweighted graphs; mark visited at enqueue time, not dequeue.
- [ ] `heapify` is O(n); `peek` is O(1); iterating a PriorityQueue does not yield sorted order.
- [ ] Use `lo + (hi - lo) / 2` and one fixed bound convention to avoid overflow and infinite loops.
- [ ] "Minimize the maximum" is the signature of binary search on the answer.
- [ ] The JVM does not optimize tail recursion.
- [ ] Backtracking = choose / recurse / un-choose; pruning beats micro-optimization.
- [ ] DP needs optimal substructure plus overlapping subproblems; defining the state is the real work.
- [ ] Knapsack capacity iteration direction distinguishes 0/1 from unbounded.
- [ ] Greedy needs an exchange argument; sort-by-end-time is the interval-scheduling one.
- [ ] Dijkstra breaks on negative weights; Bellman-Ford handles them.
- [ ] Directed-graph cycle detection needs the recursion stack, not just a visited set.
- [ ] Kahn's algorithm detects cycles by processing fewer than V nodes.
- [ ] Trie operations are O(key length), independent of dictionary size.
- [ ] Union-find with path compression and union by rank is effectively O(1); it cannot delete edges.
- [ ] Input constraints select the complexity class before you pick the pattern.