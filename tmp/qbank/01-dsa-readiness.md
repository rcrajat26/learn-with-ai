# 01 — DSA Readiness

**What this decides:** whether Phase 1 (Weeks 1–4) runs as written, compresses,
or needs extra runway. Also whether data-structure *internals* (asked directly
in interviews) need dedicated study.

Three parts: (A) timed problems, (B) complexity analysis, (C) DS internals quiz.

---

## Part A — Timed problems `[OPEN-EDITOR]`

Editor allowed, no search, no AI. Java preferred. "Solved" = runs correctly on
the listed cases including edge cases. Attempt all five even after failures —
each probes a different pattern.

### A1 [Easy — 15 min] Pair sum
Given `int[] nums` and `int target`, return indices of two numbers summing to
`target`. Exactly one solution exists. Follow-up (say aloud): complexity of
your solution; can you do O(n)?
- **Cases:** `[2,7,11,15], 9 → [0,1]`; `[3,3], 6 → [0,1]`.
- **Score 1:** O(n) hashmap solution, clean, first try. **0.5:** O(n²) works,
  or O(n) after fumbling. **0:** not working in 15 min.

### A2 [Easy — 15 min] Balanced brackets
Given a string of `()[]{}`, return whether it's valid (proper nesting/order).
- **Cases:** `"()[]{}" → true`; `"(]" → false`; `"([)]" → false`; `"" → true`; `"(" → false`.
- **Score 1:** stack solution, handles all cases. **0.5:** right idea, missed
  an edge case (empty, leftover opener). **0:** no stack insight or not working.

### A3 [Easy/Medium — 20 min] First bad version (binary search)
You have `boolean isBad(int v)` over versions `1..n`; all versions after the
first bad one are bad. Find the first bad version minimizing calls to `isBad`.
Implement with a stub `isBad`.
- **Cases:** n=10, first bad=4; n=1, first bad=1; first bad=n.
- **Score 1:** correct binary search, no off-by-one, no overflow
  (`lo + (hi-lo)/2`), terminates. **0.5:** works after off-by-one debugging.
  **0:** linear scan or infinite loop.

### A4 [Medium — 25 min] Longest substring without repeating characters
Return its length. Explain your approach aloud before coding.
- **Cases:** `"abcabcbb" → 3`; `"bbbbb" → 1`; `"pwwkew" → 3`; `"" → 0`.
- **Score 1:** O(n) sliding window with set/map, correct. **0.5:** O(n²)
  correct, or O(n) with debugging. **0:** not working in 25 min.

### A5 [Medium — 25 min] Level-order traversal
Given a binary tree (build a small `TreeNode` yourself), return values level
by level (`List<List<Integer>>`).
- **Cases:** `[3,9,20,null,null,15,7] → [[3],[9,20],[15,7]]`; empty tree; single node.
- **Score 1:** BFS with queue, correct level separation. **0.5:** DFS-with-depth
  variant working, or BFS with fumbles. **0:** can't traverse.

**Part A placement:**
- 0–1 solved → DSA track exactly as planned (true beginner pacing).
- 2–3 solved → as planned; Week 1 can move faster.
- 4 solved → compress Weeks 1–2 into one week.
- 5 solved incl. A4 clean → compress Weeks 1–3; start at Week 3–4 material;
  the "DSA beginner" assumption in the plan is wrong for you.

---

## Part B — Complexity analysis (predict-output style, 15 min total)

State time AND space complexity. No partial credit for time-only.

### B1 [L1]
```java
for (int i = 0; i < n; i++)
    for (int j = i; j < n; j++)
        sum += a[i] * a[j];
```
**Answer:** O(n²) time (triangular ≈ n²/2), O(1) space.

### B2 [L2]
```java
for (int i = 1; i < n; i *= 2)
    for (int j = 0; j < n; j++)
        work(i, j);   // O(1)
```
**Answer:** O(n log n) time, O(1) space.

### B3 [L2] String concatenation in a loop
```java
String s = "";
for (int i = 0; i < n; i++) s += a[i];
```
**Answer:** O(n²) time — each `+=` copies the whole string. Fix:
`StringBuilder` → O(n). Must name the copy as the reason.

### B4 [L3] Recursion
```java
int f(int n) { return n <= 1 ? 1 : f(n-1) + f(n-1); }
```
**Answer:** O(2ⁿ) time, O(n) space (max recursion depth, not 2ⁿ frames live
at once). The space part is the discriminator.

### B5 [L3] Amortized
"Adding n elements to an `ArrayList` — total cost, and why is `add` called
O(1)?" **Answer:** doubling growth → total copies ≈ 2n → O(n) total, O(1)
amortized per add. Must use/paraphrase "amortized" with the doubling argument.

### B6 [L3] Hash map worst case
"`HashMap.get` is O(1) — when is that false, and what does Java 8+ do about
it?" **Answer:** adversarial/colliding keys degrade a bucket to O(n) list;
Java 8 treeifies buckets ≥ 8 entries → O(log n). Bonus: requires `Comparable`
keys or falls back to identity ordering.

---

## Part C — Data-structure internals (explain-back, 20 min)

### C1 [L2] How does a HashMap work internally?
**Strong answer:** array of buckets; `hashCode()` → spread → index via
`(n-1) & hash`; collisions → linked list → red-black tree ≥ 8; resize at
load factor 0.75 (rehash cost); why capacity is a power of two.
**Red flags:** "it hashes the key and finds it" with no bucket/collision story.

### C2 [L2] ArrayList vs LinkedList — when does LinkedList actually win?
**Strong answer:** almost never in practice — cache locality makes ArrayList
faster even for many "LinkedList-shaped" workloads; LinkedList wins only for
O(1) removal *via an iterator you already hold* / head-tail ops (and even then
`ArrayDeque` usually beats it). Knows get(i) is O(n) on LinkedList.
**Red flags:** the textbook "LinkedList for frequent inserts" answer with no
cache-locality caveat scores 0.5 max.

### C3 [L2] Heap / PriorityQueue
"How is a binary heap stored, what are the complexities of peek / offer /
poll, and why can't you efficiently find an arbitrary element?"
**Strong answer:** array-backed complete tree, parent/child index math;
peek O(1), offer/poll O(log n) via sift-up/down; only the heap *property*
(parent ≤ children) is maintained, not full order → arbitrary search O(n).

### C4 [L3] Choose the structure (rapid fire — one line each)
1. LRU cache backing structure → `LinkedHashMap` (access-order) or HashMap + doubly-linked list.
2. Top-K frequent items from a stream → HashMap counts + size-K min-heap.
3. "Give me the smallest element ≥ x" repeatedly, with inserts → `TreeMap`/`TreeSet` (`ceiling`).
4. Check-if-word-exists over 1M dictionary words with prefix search → Trie (HashSet if no prefix requirement).
5. Sliding-window maximum → monotonic deque.
**Score:** 1 if ≥ 4 correct, 0.5 if 3, else 0. (5/5 including justification
suggests prior pattern exposure — note it.)

### C5 [L4] Discriminator
"Your service keeps a `HashSet<Order>` and orders 'disappear' from it after
a status update. What happened?"
**Strong answer:** `Order` is mutable and `hashCode()` depends on mutated
state — the object now lives in the wrong bucket; `contains` hashes the new
state, looks in a different bucket, misses. Fixes: immutable keys / identity-
based hash / remove-mutate-reinsert. This connects DS internals to real bugs —
full credit requires the wrong-bucket mechanism.

---

## Breadth checklist (rate 0–3)

- [CORE] Big-O of all common collection ops (HashMap, TreeMap, ArrayList, ArrayDeque, PriorityQueue)
- [CORE] Recursion with confidence (write + trace call stack)
- [CORE] Binary search on a rotated/answer-space variant (concept)
- Two pointers / sliding window as named patterns
- BFS vs DFS — when each, iterative forms
- Stack-based problems (monotonic stack — heard of it?)
- Union-Find (heard of it? used it?)
- Basic DP (memoization vs tabulation — concept)
- Sorting algorithm you could implement cold (name which)
- Bit manipulation basics (XOR trick, checking/setting a bit)
