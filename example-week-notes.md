# Week 1 — Java + Big O + Arrays I (Staff-Bar Notes)

> **Theme:** Build the DSA + Java foundation that every later week stands on. Get fluent with Big O reasoning, Java Collections internals (not just API), hashmap-pattern problems, and the `equals/hashCode` contract — and start practicing trade-off articulation, the highest-leverage Staff interview skill.
>
> **Schedule:** 5 study days × 4 hrs = 20 hrs (4 DSA-D + 1 Review-D).
> **End-of-week deliverable:**
> - 9 LeetCode problems solved + 4 re-done from scratch on Day 5
> - Big O + Collections complexity tables memorized
> - `equals/hashCode` contract + PECS internalized
> - 25 candidate behavioral stories brainstormed → 15 picked → 5 written in full STAR
> - 1 engineering blog dissected with the 7-question template
> - Java traps appendix internalized

---

## Table of Contents

1. [Day 1 — Big O + Two Sum / Anagram / Duplicate + Collections (deep)](#day-1)
2. [Day 2 — Group Anagrams + Top K Frequent + equals/hashCode contract](#day-2)
3. [Day 3 — Product Except Self + Valid Sudoku + Generics & PECS](#day-3)
4. [Day 4 — Encode/Decode Strings + Longest Consecutive + First Blog Read](#day-4)
5. [Day 5 — Review + Behavioral Story Brainstorm + STAR Rubric](#day-5)
6. [Sidebar A — HashMap & ConcurrentHashMap Internals (deep)](#hashmap-internals)
7. [Appendix — Java Traps for the Staff Round](#java-traps)
8. [Week Cheatsheet](#cheatsheet)
9. [Week Checklist](#checklist)
10. [Consolidated Reference Links](#references)

---

<a id="day-1"></a>
## Day 1 — DSA-D: Big O + 3 Problems + Java Collections

**Time budget:** 1h Big O theory + 2h DSA + 1h Java Collections.

### Part A — Big O Fundamentals

#### A1. Why Big O exists

Performance is a function of input size. Wall-clock time depends on machine, JIT state, GC, OS scheduler — none of those are stable. Big O abstracts those away and asks: **as n grows, how does cost grow?** That's the question that survives across machines and across decades. Without it, you have no shared vocabulary for "this scales" vs "this doesn't."

It is:
- **Asymptotic** — about behavior as n → ∞, not at small n. A faster algorithm on n=10 may lose on n=10⁶.
- **Upper-bound** — worst-case ceiling. (Big Ω is the lower bound; Big Θ is tight.)
- **Coefficient-free** — `5n` and `n` are both `O(n)`. Constants are machine-dependent and pruned.
- **Lower-order-term-free** — `n² + n + log n` is `O(n²)`. The dominant term wins as n grows.

#### A2. The complexity classes you must recognize on sight

| Notation | Name | Example | Mental model |
|---|---|---|---|
| `O(1)` | Constant | HashMap `get`, array index | Single step regardless of n |
| `O(log n)` | Logarithmic | Binary search, balanced BST lookup | Halve the search space each step |
| `O(√n)` | Sub-linear | Trial division up to √n | Rare but appears in number theory |
| `O(n)` | Linear | One pass over an array | One unit of work per element |
| `O(n log n)` | Linearithmic | Merge sort, heap sort, `Collections.sort` | **Comparison-sort lower bound** |
| `O(n²)` | Quadratic | Bubble sort, nested loop | All pairs |
| `O(n³)` | Cubic | Naive matrix multiply | All triples |
| `O(2ⁿ)` | Exponential | Subsets without memoization, naive Fibonacci | Branching factor 2 per level |
| `O(n!)` | Factorial | Naive permutations, brute-force TSP | All orderings |

**Growth ordering (memorize):**
`O(1) < O(log n) < O(√n) < O(n) < O(n log n) < O(n²) < O(n³) < O(2ⁿ) < O(n!)`

**Concrete numbers at n = 10⁶ (assume 10⁹ simple ops/sec, ~1ns/op):**

| Complexity | Operations | Wall time |
|---|---|---|
| `log₂(n)` | ~20 | 20 ns |
| `√n` | 1,000 | 1 μs |
| `n` | 10⁶ | 1 ms |
| `n log n` | ~2×10⁷ | 20 ms |
| `n²` | 10¹² | ~16 min — **unacceptable** |
| `2ⁿ` | unrunnable past n ≈ 30 | — |

#### A3. The interview "n → complexity" rule of thumb

Given input size n, the typical max acceptable complexity is:

| n up to | Acceptable |
|---|---|
| 10 | `O(n!)`, `O(2ⁿ)` (backtracking ok) |
| 20–25 | `O(2ⁿ)` (subset enumeration) |
| 1,000 | `O(n²)` |
| 10⁵ | `O(n log n)` |
| 10⁶ | `O(n)` |
| 10⁹ | `O(log n)` or `O(1)` |

Reading the constraint section of a LeetCode problem **immediately tells you the target complexity**. Constraint says n ≤ 10⁵? You need O(n log n) or better. n ≤ 20? Backtracking is expected.

#### A4. Amortized analysis

Most operations are cheap; some are expensive. Amortized cost averages cost over a sequence.

**Canonical example — `ArrayList.add()`:**
- Backed by an internal array. Most `add`s are O(1).
- When the array is full, Java allocates a new one (grows by 1.5× — `newCap = oldCap + (oldCap >> 1)`) and copies → O(n).
- **Why is amortized O(1)?** Because the expensive copies happen exponentially rarely. Cost of n inserts = n + n/2 + n/4 + ... ≤ 2n total = O(n). Per insert = O(1).

If interviewer asks "what's the cost of `ArrayList.add()`?" — answer **amortized O(1)**, not O(n). Then explain why.

**Other amortized examples:**
- `HashMap.put` — average O(1), occasionally O(n) on rehash. Amortized O(1).
- Building a heap by repeated insertion vs `heapify` — `heapify` is O(n), repeated `offer` is O(n log n).

#### A5. Space complexity — don't forget it

For every algorithm, state TWO complexities: time AND space.

- Iteration uses O(1) extra space (a few variables).
- Recursion uses O(depth) extra space (each call has a stack frame).
- Building a hashmap of n elements uses O(n) space.
- **The output array doesn't count** by convention (you must return it).

For Java specifically: even a primitive `int` allocation is ~16 bytes once boxed to `Integer`. A `HashMap<Integer, Integer>` with n entries takes roughly 48–64 bytes/entry. Cache locality matters; that's why `int[]` crushes `List<Integer>` in tight loops.

#### A6. Common analysis traps

| Trap | Reality |
|---|---|
| `s = s + c` in a loop | **O(n²)** — `String` is immutable; each `+` allocates and copies. Use `StringBuilder`. |
| `list.remove(0)` on `ArrayList` | **O(n)** — shifts all elements. `LinkedList.removeFirst()` is O(1). |
| `list.contains(x)` on `ArrayList` | **O(n)** — linear scan. Use `HashSet` if you do this in a loop. |
| `set.contains` in a hot path | Average O(1). Worst case O(log n) post-Java-8 (treeified buckets). |
| `PriorityQueue.contains(x)` | **O(n)** — heap is not sorted linearly. |
| Recursion depth | Counts toward space — O(depth). |
| `Arrays.sort(int[])` | Dual-pivot Quicksort — O(n log n) average, O(n²) worst (rare). |
| `Arrays.sort(Object[])` | TimSort — O(n log n) worst case. |

#### A7. Drill — analyze these 10 snippets on paper

For each: time + space.

```java
// 1
for (int i = 0; i < n; i++) sum += arr[i];
// → O(n) time, O(1) space

// 2
for (int i = 0; i < n; i++)
    for (int j = 0; j < n; j++) count++;
// → O(n²) time, O(1) space

// 3
for (int i = 0; i < n; i++)
    for (int j = i; j < n; j++) count++;
// → O(n²) time — n + (n-1) + ... + 1 = n(n+1)/2

// 4
for (int i = 1; i < n; i *= 2) count++;
// → O(log n) time

// 5
for (int i = 0; i < n; i++)
    for (int j = 1; j < n; j *= 2) count++;
// → O(n log n) time

// 6
int fib(int n) {
    if (n <= 1) return n;
    return fib(n-1) + fib(n-2);
}
// → O(2ⁿ) time, O(n) space (max recursion depth = n)

// 7
boolean[] seen = new boolean[n];
for (int x : arr) seen[x] = true;
// → O(n) time, O(n) space

// 8
List<List<Integer>> result = new ArrayList<>();
for (int i = 0; i < n; i++) {
    List<Integer> sub = new ArrayList<>(result);
    result.add(sub);
}
// → O(n²) time (copies grow), O(n²) space

// 9
for (int i = n; i > 0; i /= 2)
    for (int j = 0; j < i; j++) count++;
// → O(n) time — n + n/2 + n/4 + ... = 2n

// 10
void rec(int n) {
    if (n == 0) return;
    rec(n - 1);
    rec(n - 1);
}
// → O(2ⁿ) time (two branches × n depth), O(n) space (stack depth)
```

**References:**
- CTCI Ch VI ("Big O") — do it once carefully
- Abdul Bari Big O — https://www.youtube.com/watch?v=A03oI0znAoc
- Big-O cheatsheet — https://www.bigocheatsheet.com/

---

### Part B — DSA Problems (2 hrs)

#### Problem 1: Two Sum (LC 1, Easy)

- **LeetCode:** https://leetcode.com/problems/two-sum/
- **NeetCode:** https://neetcode.io/problems/two-integer-sum

**Statement.** Given `int[] nums` and `int target`, return indices `i, j` (i ≠ j) such that `nums[i] + nums[j] == target`. Exactly one solution.

**Brute force (O(n²) time, O(1) space):**
```java
public int[] twoSum(int[] nums, int target) {
    for (int i = 0; i < nums.length; i++)
        for (int j = i + 1; j < nums.length; j++)
            if (nums[i] + nums[j] == target) return new int[]{i, j};
    return new int[]{};
}
```

**Optimal — hashmap of complements (O(n) time, O(n) space):**
```java
public int[] twoSum(int[] nums, int target) {
    Map<Integer, Integer> seen = new HashMap<>();  // value → index
    for (int i = 0; i < nums.length; i++) {
        int complement = target - nums[i];
        if (seen.containsKey(complement))
            return new int[]{seen.get(complement), i};
        seen.put(nums[i], i);
    }
    return new int[]{};
}
```

**Walk-through.** `nums = [2,7,11,15], target = 9`:
- i=0: complement=7, not seen → store {2→0}
- i=1: complement=2, seen at 0 → return `[0,1]` ✓

**Complexity.** Time O(n) — single pass, each map op O(1) average. Space O(n) — map holds up to n entries.

**Edge cases.**
- Duplicates: `[3,3], target=6` → handled because we check *before* inserting.
- Negative numbers: addition works regardless.
- No solution exists: problem guarantees one; otherwise return empty.

**Trade-off drill.**

*Q: When sort + two-pointer instead of hashmap?*
There are three things I'd weigh: **memory, output requirements, sorted-ness**. Sort + two-pointer is O(n log n) time, O(1) extra space — wins when memory is tight or input is already sorted. Hashmap is O(n) time, O(n) space. But two-pointer returns **values**, not original indices, because sorting destroys position. Two Sum asks for indices → hashmap. 3Sum / 4Sum ask for value triples/quads → sort + two-pointer (Day 7 will revisit).

*Q: What if the array is sorted to begin with?*
Switch to two-pointer with `left=0, right=n-1`. If sum too small, `left++`; too large, `right--`. O(n) time, O(1) space. This is "Two Sum II" (LC 167) — preview it.

**Scale-up addendum.** At 10⁹ elements that don't fit in RAM: emit `(target - nums[i], i)` and `(nums[i], i)` to a distributed hash join (Spark, Flink). For a **stream** with unbounded length looking for any matching pair, use a sliding-window LinkedHashMap with TTL — full hash of the stream is impossible. This pattern (hash-join with complement key) recurs in MapReduce-style design questions.

**Foreshadow.** The complement pattern generalizes: 3Sum (Day 7) fixes one element and runs two-pointer on the rest. Subarray Sum Equals K (later) uses prefix-sum complements. Internalize it now.

**Junior says wrong, Staff says right:**
- Junior writes hashmap; Staff says "HashMap if we need indices; sort + two-pointer if we only need values and memory matters. What size of n?"
- Junior shows only the optimal; Staff narrates progression — "brute is O(n²), here's the O(n) trade."
- Junior tests on the happy path; Staff states assumptions out loud ("I'm assuming exactly one solution and one usage of each index").

---

#### Problem 2: Valid Anagram (LC 242, Easy)

- **LeetCode:** https://leetcode.com/problems/valid-anagram/
- **NeetCode:** https://neetcode.io/problems/is-anagram

**Statement.** Return true if `t` is an anagram of `s`.

**Brute force — sort both (O(n log n) time, O(n) space):**
```java
public boolean isAnagram(String s, String t) {
    if (s.length() != t.length()) return false;
    char[] a = s.toCharArray();
    char[] b = t.toCharArray();
    Arrays.sort(a);
    Arrays.sort(b);
    return Arrays.equals(a, b);
}
```

**Optimal — frequency count (O(n) time, O(1) space for fixed-alphabet):**
```java
public boolean isAnagram(String s, String t) {
    if (s.length() != t.length()) return false;
    int[] count = new int[26];
    for (int i = 0; i < s.length(); i++) {
        count[s.charAt(i) - 'a']++;
        count[t.charAt(i) - 'a']--;
    }
    for (int c : count) if (c != 0) return false;
    return true;
}
```

**Complexity.** Time O(n). Space O(1) for ASCII lowercase (fixed 26); O(k) for general alphabet where k = distinct chars.

**Edge cases.**
- Different lengths → instant false.
- Empty strings → both empty → true.
- Unicode (e.g., emoji, combining characters) → `char[26]` breaks; switch to `HashMap<Integer, Integer>` keyed by code point. Real Unicode also has *normalization forms* (NFC vs NFD) — "café" can be one of two byte sequences. Mention this if interviewer probes.

**Trade-off drill.**

*Q: Sort vs frequency count — when is sort actually better?*
Three axes: **alphabet size, memory pressure, code clarity**. Sort is O(n log n) but uses O(log n) stack space (or O(n) for object sort) and is dead-simple to write under pressure. Frequency count is O(n) but only "O(1) space" when alphabet is small and fixed. For huge Unicode strings with mostly-unique characters, the frequency map is essentially O(n) anyway — sort wins on memory and readability.

*Q: What if the input is two arbitrary `List<T>` instead of strings?*
Use `Map<T, Integer>` with `merge(t, 1, Integer::sum)`. Equality relies on `T.equals/hashCode` — which is exactly why Day 2's contract matters.

**Scale-up addendum.** As a **streaming** comparison of two infinite streams, you can't store either. You'd hash both with a commutative streaming hash (e.g., XOR of `hash(char_count_signature)` per chunk) and compare digests — a probabilistic check. For exact answers on huge files, use external counting sort (bucket per character, on disk).

**Junior says wrong, Staff says right:**
- Junior uses `String.toCharArray()` + sort and shrugs. Staff says "if alphabet is small and fixed I'd count; if Unicode and arbitrary I'd hash-count or sort — depends on input."
- Junior assumes ASCII. Staff asks "is this ASCII, Unicode, case-sensitive, whitespace-significant?"

---

#### Problem 3: Contains Duplicate (LC 217, Easy)

- **LeetCode:** https://leetcode.com/problems/contains-duplicate/
- **NeetCode:** https://neetcode.io/problems/duplicate-integer

**Statement.** Return true iff any value appears ≥ 2 times.

**Optimal (O(n) time, O(n) space):**
```java
public boolean containsDuplicate(int[] nums) {
    Set<Integer> seen = new HashSet<>();
    for (int n : nums) {
        if (!seen.add(n)) return true;  // add returns false if present
    }
    return false;
}
```

**Idiom.** `set.add(x)` returns `false` if the element was already present. Cleaner than `contains(x) + add(x)`.

**Complexity.** Time O(n). Space O(n).

**Edge cases.**
- Empty / single element → false.
- All same → true after iteration 2.
- Negative numbers / large ints → HashSet handles fine.

**Trade-off drill.**

*Q: Sort vs HashSet for duplicate detection?*
Sort: O(n log n) time, O(1) or O(n) extra space depending on whether in-place sort is acceptable. HashSet: O(n) time, O(n) space. **Sort wins when memory is tight and we don't mind mutating input.** HashSet wins for speed.

*Q: What if values are bounded integers (say 0..10⁶)?*
Use a `BitSet` or `boolean[]` indexed by value — O(n) time, O(M) space where M is the value range. Sometimes M < n × 32 bits (Java reference overhead), so BitSet is actually cheaper than HashSet.

**Scale-up addendum.** Distributed duplicate detection across petabytes: each shard hashes its values and emits to a reducer keyed by `hash(value) % R`; the reducer checks for collisions and verifies. For **approximate** answers on a stream, a Bloom filter says "definitely no dup" or "probably dup, go check" — useful for filtering before an expensive exact check. **HyperLogLog** estimates *cardinality* (count of distinct values) in O(1) memory with ~2% error — different problem but a related streaming primitive.

**Junior says wrong, Staff says right:**
- Junior writes a nested loop. Staff jumps to HashSet and explains why.
- Junior never mentions Bloom filter. Staff brings it up unprompted when interviewer says "now imagine this is a stream."

---

### Part C — Java Collections (1 hr)

The Collections Framework is your daily toolkit and the most-asked Java topic. You must know **defaults, complexity, and when to pick what** — not just the API.

#### C1. The hierarchy

```
                       Iterable
                          │
                      Collection
        ┌─────────────────┼─────────────────┐
       List              Set              Queue / Deque
       │                  │                 │
   ArrayList          HashSet           ArrayDeque
   LinkedList         LinkedHashSet     PriorityQueue
   Vector (legacy)    TreeSet           LinkedList (Deque too)
   Stack  (legacy)

  Map (separate hierarchy)
   ├── HashMap
   ├── LinkedHashMap
   ├── TreeMap
   ├── ConcurrentHashMap
   └── Hashtable (legacy)
```

#### C2. Complexity table (memorize cold)

| Op | ArrayList | LinkedList | HashMap | HashSet | TreeMap | ArrayDeque | PriorityQueue |
|---|---|---|---|---|---|---|---|
| `add` end | O(1) amort. | O(1) | O(1) avg | O(1) avg | O(log n) | O(1) amort. | O(log n) |
| `add` index 0 | O(n) | O(1) | — | — | — | O(1) addFirst | — |
| `get(i)` | O(1) | O(n) | O(1) avg | (contains) O(1) | O(log n) | peek O(1) | peek O(1) |
| `remove(i)` | O(n) | O(1) given node | O(1) avg | O(1) avg | O(log n) | O(1) ends | poll O(log n) |
| `contains` | O(n) | O(n) | O(1) avg | O(1) avg | O(log n) | O(n) | **O(n)** |
| Order | insertion | insertion | none | none | sorted key | insertion | heap |

**Caveat.** HashMap worst case is O(log n) post-Java-8 thanks to bucket treeification (≥ 8 entries in a bucket and capacity ≥ 64 → linked list converts to red-black tree). Pre-Java-8 it was O(n). See [Sidebar A](#hashmap-internals) for the deep dive.

#### C3. `ArrayList`

- Backed by `Object[]`. Default capacity 10. Grows **by 50%** (`oldCap + (oldCap >> 1)`). (Vector grows by 100% — one of many reasons to skip it.)
- `add(E)`: amortized O(1). `add(int, E)`: O(n).
- `get/set(int)`: O(1).
- `remove(int)`: O(n).
- **Iterator semantics:** fail-fast. Modifying the list during iteration (except via `Iterator.remove()`) throws `ConcurrentModificationException` (a best-effort check on `modCount`, NOT a thread-safety guarantee).
- **The autoboxing trap:** `list.remove(1)` removes index 1 (calls `remove(int)`). `list.remove(Integer.valueOf(1))` removes the value 1 (calls `remove(Object)`). [See Appendix.](#java-traps)

```java
List<Integer> list = new ArrayList<>();
list.add(1); list.add(2); list.add(3);
list.set(1, 20);                                // [1, 20, 3]
list.remove(Integer.valueOf(20));               // by value
list.remove(0);                                 // by index
int[] arr = list.stream().mapToInt(Integer::intValue).toArray();
```

#### C4. `HashMap` — shallow API view (deep dive in Sidebar A)

- Default capacity 16, load factor 0.75 → resize at size > 12.
- Allows one `null` key and `null` values.
- Not thread-safe; concurrent modification can corrupt.

#### C5. `HashSet`

- Internally a HashMap mapping every key to a sentinel `PRESENT`. All HashMap rules apply.
- `add()` returns false if element already present (golden idiom).

#### C6. `Deque` — always `ArrayDeque`, never `Stack`

- `Stack` extends `Vector` (synchronized, slow, legacy).
- `Deque<E> stack = new ArrayDeque<>();` is the modern idiom.
- As stack: `push / pop / peek`. As queue: `offer / poll / peek`. As deque: `addFirst/Last`, `pollFirst/Last`, `peekFirst/Last`.
- All end-of-deque ops O(1).

#### C7. `PriorityQueue`

- Binary min-heap on an array. Max-heap: `new PriorityQueue<>(Comparator.reverseOrder())`.
- `offer`: O(log n). `poll`: O(log n). `peek`: O(1). **`contains`: O(n)** — common gotcha.
- Iteration order is NOT sorted; only `poll` returns heap order.

```java
PriorityQueue<int[]> pq = new PriorityQueue<>(
    (a, b) -> Integer.compare(a[0], b[0])     // NOT a[0] - b[0] (overflow)
);
```

**The overflow trap.** `(a, b) -> a - b` overflows for `Integer.MIN_VALUE` and large diffs. Always `Integer.compare`. [See Appendix.](#java-traps)

#### C8. Choosing the right collection

| Need | Pick |
|---|---|
| Indexed access, mostly reads | `ArrayList` |
| Frequent front/back ops, queue, stack | `ArrayDeque` |
| Min/max repeatedly | `PriorityQueue` |
| Key → value, fastest, unordered | `HashMap` |
| Key → value, insertion order (LRU base) | `LinkedHashMap` |
| Key → value, sorted by key | `TreeMap` |
| Set membership, unordered | `HashSet` |
| Set membership, sorted | `TreeSet` |
| Concurrent map | `ConcurrentHashMap` |
| Read-mostly, write-rare, concurrent | `CopyOnWriteArrayList` |

**Why `LinkedList` is almost never the answer in 2026.** In theory O(1) middle insertion. In practice, cache misses on every node traversal kill it. `ArrayList` wins for nearly every real workload. The only good reason to pick `LinkedList` is when you need `Deque` semantics — and `ArrayDeque` does that better anyway.

**Reference:**
- Oracle Collections tutorial — https://docs.oracle.com/javase/tutorial/collections/
- Baeldung Collections — https://www.baeldung.com/java-collections

---

<a id="day-2"></a>
## Day 2 — DSA-D: Group Anagrams + Top K Frequent + equals/hashCode

**Time budget:** 3h DSA + 1h Java contract deep dive.

### Part A — Problems

#### Problem 4: Group Anagrams (LC 49, Medium)

- **LeetCode:** https://leetcode.com/problems/group-anagrams/
- **NeetCode:** https://neetcode.io/problems/anagram-groups

**Statement.** Group strings that are anagrams of one another.

**Brute force (O(n² · k)).** Compare every pair with anagram check. Too slow.

**Approach 1 — Sorted-string key (O(n · k log k)):**
```java
public List<List<String>> groupAnagrams(String[] strs) {
    Map<String, List<String>> groups = new HashMap<>();
    for (String s : strs) {
        char[] chars = s.toCharArray();
        Arrays.sort(chars);
        String key = new String(chars);
        groups.computeIfAbsent(key, k -> new ArrayList<>()).add(s);
    }
    return new ArrayList<>(groups.values());
}
```

**Approach 2 — Char-count signature key (O(n · k), lowercase-only):**
```java
public List<List<String>> groupAnagrams(String[] strs) {
    Map<String, List<String>> groups = new HashMap<>();
    for (String s : strs) {
        int[] count = new int[26];
        for (char c : s.toCharArray()) count[c - 'a']++;
        StringBuilder sb = new StringBuilder();
        for (int c : count) { sb.append(c).append('#'); }
        groups.computeIfAbsent(sb.toString(), k -> new ArrayList<>()).add(s);
    }
    return new ArrayList<>(groups.values());
}
```

**Key insight.** Find a **canonical form** that's identical for all anagrams; key the map on it. This canonical-form trick is its own pattern — appears in "isomorphic strings," "valid permutation," many others.

**Idiom — `computeIfAbsent`.** Replaces:
```java
if (!map.containsKey(k)) map.put(k, new ArrayList<>());
map.get(k).add(v);
```
with:
```java
map.computeIfAbsent(k, key -> new ArrayList<>()).add(v);
```
Use it everywhere. Avoids double-lookup and is harder to mis-type.

**Edge cases.** Empty input → empty list. Single empty string → one group containing `""`.

**Trade-off drill.**

*Q: Sorting key vs char-count key — when which?*
Three axes: **alphabet size, key collision risk, code simplicity**. Char-count is O(k) per string vs O(k log k) — wins for long words. But it only works for fixed small alphabets (extend by hashing the count vector for Unicode). Sorted key works for any alphabet trivially. For interview default, lead with sorted-key (universally correct, easier to explain) and offer char-count as the optimization.

*Q: How would you parallelize?*
Sharding by hash of the canonical key — same anagram class lands on same shard. Standard MapReduce shape: map produces `(key, original)`, reducer groups.

**Scale-up addendum.** Billions of strings: distribute by `hash(canonicalKey) % R` reducers. Memory per node bounded. Tail latency dominated by the largest group ("celebrity anagram class") — same dynamic as celebrity fan-out in News Feed (Day 101 will revisit). For a streaming variant ("group last N strings"), use a `LinkedHashMap<key, List<String>>` with eviction.

**Junior says wrong, Staff says right:**
- Junior picks sorted key, doesn't mention char-count. Staff offers both and picks based on input.
- Junior uses `containsKey + get + put` instead of `computeIfAbsent`. Staff knows the idiom.
- Junior never asks alphabet. Staff: "Is it ASCII lowercase? Then char-count is O(n·k)."

---

#### Problem 5: Top K Frequent Elements (LC 347, Medium)

- **LeetCode:** https://leetcode.com/problems/top-k-frequent-elements/
- **NeetCode:** https://neetcode.io/problems/top-k-elements-in-list

**Statement.** Return the `k` most frequent elements in any order.

**Brute force.** Sort the (value, freq) pairs by freq descending, take first k. O(n log n).

**Approach 1 — Min-heap of size k (O(n log k)):**
```java
public int[] topKFrequent(int[] nums, int k) {
    Map<Integer, Integer> freq = new HashMap<>();
    for (int n : nums) freq.merge(n, 1, Integer::sum);

    PriorityQueue<int[]> heap = new PriorityQueue<>(
        (a, b) -> Integer.compare(a[1], b[1])
    );
    for (Map.Entry<Integer, Integer> e : freq.entrySet()) {
        heap.offer(new int[]{e.getKey(), e.getValue()});
        if (heap.size() > k) heap.poll();
    }
    int[] result = new int[k];
    for (int i = 0; i < k; i++) result[i] = heap.poll()[0];
    return result;
}
```

**Approach 2 — Bucket sort (O(n) — optimal):**
```java
public int[] topKFrequent(int[] nums, int k) {
    Map<Integer, Integer> freq = new HashMap<>();
    for (int n : nums) freq.merge(n, 1, Integer::sum);

    List<Integer>[] buckets = new List[nums.length + 1];
    for (var e : freq.entrySet()) {
        int f = e.getValue();
        if (buckets[f] == null) buckets[f] = new ArrayList<>();
        buckets[f].add(e.getKey());
    }
    int[] result = new int[k];
    int idx = 0;
    for (int i = buckets.length - 1; i >= 0 && idx < k; i--) {
        if (buckets[i] != null)
            for (int n : buckets[i]) {
                result[idx++] = n;
                if (idx == k) break;
            }
    }
    return result;
}
```

**Why bucket sort works.** Frequency is bounded by `nums.length`. Use frequency as an array index. No sorting needed. O(n) time, O(n) space.

**Idiom — `merge`.** `freq.merge(n, 1, Integer::sum)` replaces `freq.put(n, freq.getOrDefault(n, 0) + 1)`. Cleaner, single lookup.

**Edge cases.**
- All distinct → bucket 1 has everything; pick any k.
- k = n → return all.
- Negative numbers → fine; we don't index by value, we index by frequency.

**Trade-off drill.**

*Q: Heap vs bucket sort — when each?*
Three axes: **frequency boundedness, k vs n, code complexity**. Bucket sort needs frequency bounded by n (true here). Heap is general-purpose — works when "weight" is any double. For k << n, heap of size k uses O(k) memory; bucket uses O(n). Lead with heap (interviewer expects it), then offer bucket as O(n) optimization.

*Q: What if k changes frequently (top-K stream)?*
Online top-K = "approximate top-K" problem. Tools: **Count-Min Sketch** (probabilistic frequency estimator, sub-linear space, slight overcount) + **min-heap of size k** maintained as the sketch updates. Used at Twitter / X for trending topics. Misra-Gries is another deterministic streaming top-K algorithm. *Staff-level reference.*

**Scale-up addendum.** Across distributed shards: each shard computes its local top-(c·k) (with c ≥ 2 for safety), ships to a reducer that merges and takes global top-k. Loose lower bound for guarantees but works in practice. For exact answers across shards you need full frequency counts joined, which is O(distinct values).

**Junior says wrong, Staff says right:**
- Junior writes heap, says O(n log k), done. Staff offers bucket sort O(n).
- Junior never names Count-Min Sketch. Staff brings it up when interviewer says "stream."
- Junior uses `(a,b) -> a[1] - b[1]`. Staff uses `Integer.compare(a[1], b[1])` to avoid overflow.

---

### Part B — `equals()` and `hashCode()` contract (1 hr)

The most-asked Java interview topic. Violations silently corrupt every hash-based collection — and every Spring service uses hashmaps everywhere.

#### B1. The contract (from `Object` Javadoc)

**`equals(Object o)` must be:**
1. **Reflexive:** `x.equals(x)` is true.
2. **Symmetric:** `x.equals(y) ⇔ y.equals(x)`.
3. **Transitive:** `x.equals(y) && y.equals(z) → x.equals(z)`.
4. **Consistent:** repeated calls return the same result if neither object is mutated.
5. **Null-safe:** `x.equals(null)` is false (never throws).

**`hashCode()` rules:**
1. Consistent within a JVM run for an unchanged object.
2. **`a.equals(b) → a.hashCode() == b.hashCode()`** (mandatory).
3. Unequal objects *may* share a hash (collision allowed, but rare is better).

**The bottom line:**
- **Override both, or neither.**
- **If you override `equals`, you MUST override `hashCode`.**

#### B2. What goes wrong if you forget `hashCode`

```java
class Point {
    int x, y;
    Point(int x, int y) { this.x = x; this.y = y; }
    @Override public boolean equals(Object o) {
        return o instanceof Point p && x == p.x && y == p.y;
    }
    // Forgot hashCode!
}

Set<Point> set = new HashSet<>();
set.add(new Point(1, 2));
set.contains(new Point(1, 2));  // → FALSE
```

Why false? `HashSet.contains` computes `hashCode()` to find the bucket. Without override, you inherit `Object.hashCode()` which is identity-based (typically a pseudo-random hash per instance). Two `Point(1,2)` instances hash to different buckets; lookup never finds the equal entry.

#### B3. Canonical implementations

**Records (Java 16+) — preferred when applicable:**
```java
record Point(int x, int y) {}
// equals, hashCode, toString, accessors auto-generated. Immutable. Final.
```

Records are the right answer for value objects 90% of the time. The other 10%: when you need inheritance, mutability, custom serialization, or framework annotations on setters (some old Spring patterns).

**Manual implementation:**
```java
final class Point {
    private final int x, y;

    Point(int x, int y) { this.x = x; this.y = y; }

    @Override
    public boolean equals(Object o) {
        if (this == o) return true;                     // identity fast path
        if (!(o instanceof Point p)) return false;
        return x == p.x && y == p.y;
    }

    @Override
    public int hashCode() {
        return Objects.hash(x, y);
    }
}
```

`Objects.hash(...)` does the standard "multiply by 31" hash but allocates a varargs array — fine for non-hot code. For hot loops:
```java
@Override public int hashCode() {
    int h = Integer.hashCode(x);
    h = 31 * h + Integer.hashCode(y);
    return h;
}
```

**Why 31?** Odd prime. `31 * h` can be compiled by the JIT as `(h << 5) - h`. Tradition from `String.hashCode`. Any odd prime works.

#### B4. Practice — custom HashMap key

```java
class Coord {
    final int row, col;
    Coord(int r, int c) { this.row = r; this.col = c; }
    @Override public boolean equals(Object o) {
        return o instanceof Coord c && c.row == row && c.col == col;
    }
    @Override public int hashCode() { return Objects.hash(row, col); }
}

Map<Coord, String> grid = new HashMap<>();
grid.put(new Coord(1, 2), "A");
System.out.println(grid.get(new Coord(1, 2)));   // "A"
```

**Verify the contract** by commenting out `hashCode` — `get(new Coord(1,2))` returns null even though an equal key was inserted.

#### B5. The mutable-key trap

```java
class MutablePoint {
    int x, y;
    // equals/hashCode use x, y
}

MutablePoint p = new MutablePoint(1, 2);
Set<MutablePoint> set = new HashSet<>();
set.add(p);
p.x = 99;                  // hashCode is now different
set.contains(p);           // → FALSE (looks in wrong bucket)
```

**Rule.** Hash-based collections work correctly only if the hash never changes after insertion. **Use immutable keys** — records, or `final` fields used in `equals/hashCode`.

#### B6. Inheritance and `equals` symmetry

Subclasses break `equals` symmetry easily. If `Point extends ColoredPoint`, comparing a `Point(1,2)` to a `ColoredPoint(1,2,RED)`:
- `point.equals(coloredPoint)` may return true (same x, y).
- `coloredPoint.equals(point)` returns false (color mismatch).

This violates symmetry. **Workarounds:** prefer composition over inheritance (records do this for you); or use `getClass() == o.getClass()` instead of `instanceof` (loses Liskov substitutability but preserves symmetry). Effective Java Item 10 has the full discussion.

**References:**
- Effective Java Item 10 — "Obey the general contract when overriding equals"
- Effective Java Item 11 — "Always override hashCode when you override equals"
- Baeldung — https://www.baeldung.com/java-equals-hashcode-contracts

---

<a id="day-3"></a>
## Day 3 — DSA-D: Product Except Self + Valid Sudoku + Generics (PECS)

**Time budget:** 3h DSA + 1h Java generics.

### Part A — Problems

#### Problem 6: Product of Array Except Self (LC 238, Medium)

- **LeetCode:** https://leetcode.com/problems/product-of-array-except-self/
- **NeetCode:** https://neetcode.io/problems/products-of-array-discluding-self

**Statement.** Return `int[] ans` where `ans[i] = product of nums[j] for j != i`. **Constraints:** O(n) time, **no division**.

**Why no division?** Without it the problem is trivial (totalProduct / nums[i]). The constraint forces the *left × right products* pattern, which is the real lesson — and avoids the division-by-zero special-case.

**Optimal — prefix × suffix in two passes (O(n) time, O(1) extra space):**
```java
public int[] productExceptSelf(int[] nums) {
    int n = nums.length;
    int[] ans = new int[n];

    // Pass 1: ans[i] = product of all elements LEFT of i.
    ans[0] = 1;
    for (int i = 1; i < n; i++)
        ans[i] = ans[i - 1] * nums[i - 1];

    // Pass 2: multiply by product of elements RIGHT of i (rolling).
    int right = 1;
    for (int i = n - 1; i >= 0; i--) {
        ans[i] *= right;
        right *= nums[i];
    }
    return ans;
}
```

**Mental picture.** `nums = [1, 2, 3, 4]`:
```
prefix:  [1, 1, 2, 6]    // 1, 1, 1*2, 1*2*3
suffix:  [24,12, 4, 1]   // 2*3*4, 3*4, 4, 1
ans:     [24,12, 8, 6]   // product
```

The output array doesn't count toward "extra space" by problem convention.

**Edge cases.**
- One zero in the input → only that index has non-zero product.
- Two or more zeros → all outputs are zero.
- The algorithm handles both naturally.

**Trade-off drill.**

*Q: With division allowed — how do you handle zeros?*
Count zeros. If 0 zeros: divide total by each element. If 1 zero: only that index is `totalProductExcludingTheZero`; others are 0. If ≥ 2 zeros: all outputs are 0. **Division is faster** in practice (one pass to compute product, one to fill ans), but the zero handling is awkward. The constraint avoids it.

*Q: What if elements are very large and products overflow int?*
Switch to `long`. For arbitrary precision, `BigInteger` — way slower (object allocation per op). Always ask "what's the value range?" upfront.

**Scale-up addendum.** Distributed: split array into k segments, each computes its segment product, broadcast a vector of segment products, each worker computes prefix/suffix products over segments. Becomes a MapReduce. For a **stream**, you can't compute "product except self" meaningfully without seeing all elements first — it's inherently batch.

**Junior says wrong, Staff says right:**
- Junior asks "why no division?" with confusion. Staff says "because of zeros — the constraint forces the prefix/suffix pattern."
- Junior uses two arrays (prefix and suffix), uses O(n) extra space. Staff uses one rolling variable for suffix.

---

#### Problem 7: Valid Sudoku (LC 36, Medium)

- **LeetCode:** https://leetcode.com/problems/valid-sudoku/
- **NeetCode:** https://neetcode.io/problems/valid-sudoku

**Statement.** Check if a 9×9 board with `.` for empties is a valid Sudoku state (each row, column, 3×3 box has digits 1–9 without repetition; empty cells ignored; we don't need to verify it's solvable).

**Approach 1 — Composite string keys, one set:**
```java
public boolean isValidSudoku(char[][] board) {
    Set<String> seen = new HashSet<>();
    for (int r = 0; r < 9; r++)
        for (int c = 0; c < 9; c++) {
            char v = board[r][c];
            if (v == '.') continue;
            int box = (r / 3) * 3 + (c / 3);
            if (!seen.add(v + "@row" + r) ||
                !seen.add(v + "@col" + c) ||
                !seen.add(v + "@box" + box)) return false;
        }
    return true;
}
```

**Approach 2 — Bitmasks (faster, more compact):**
```java
public boolean isValidSudoku(char[][] board) {
    int[] rows = new int[9], cols = new int[9], boxes = new int[9];
    for (int r = 0; r < 9; r++)
        for (int c = 0; c < 9; c++) {
            if (board[r][c] == '.') continue;
            int bit = 1 << (board[r][c] - '0');
            int box = (r / 3) * 3 + (c / 3);
            if ((rows[r] & bit) != 0 ||
                (cols[c] & bit) != 0 ||
                (boxes[box] & bit) != 0) return false;
            rows[r] |= bit; cols[c] |= bit; boxes[box] |= bit;
        }
    return true;
}
```

**Box index formula.** `box = (row / 3) * 3 + (col / 3)`. Sketch a 9×9 grid; verify rows 0–2 cols 0–2 → box 0, rows 0–2 cols 3–5 → box 1, etc.

**Complexity.** O(1) both — the board is fixed 81 cells. Asymptotic analysis isn't really meaningful, but the constant is small.

**Edge cases.** All empty (`.`s) → valid. The trickiest bug is the box index formula; verify on paper.

**Trade-off drill.**

*Q: String keys vs bitmasks?*
String keys: easier to read, slower (allocations per cell), no overflow risk. Bitmask: faster (single int op), trickier to debug, requires bit-fluency. For 81 cells, performance is irrelevant — pick the one you write correctly under pressure. For 1000×1000 grids the bitmask version is meaningfully faster.

*Q: How would you extend this to "is this Sudoku solvable from here"?*
Different problem — that's backtracking (LC 37). Mention it but don't solve.

**Scale-up addendum.** For a generic N×N grid (where N is a perfect square), the same algorithm extends; box index becomes `(r / √N) * √N + (c / √N)`. For massive grids (10K × 10K, hypothetical generalized Sudoku), parallelize per row/col/box independently.

**Junior says wrong, Staff says right:**
- Junior writes three separate `Set[9]` arrays. Staff uses a single set with composite keys (cleaner) or bitmasks (faster).
- Junior gets the box formula wrong and doesn't notice. Staff derives it on paper before coding.

---

### Part B — Generics & PECS (1 hr)

Generics give compile-time type safety with no runtime cast — but Java's implementation has corners (type erasure, wildcards) that interviewers probe.

#### B1. Basic generics

```java
class Box<T> {
    private T value;
    public void set(T v) { value = v; }
    public T get() { return value; }
}

Box<Integer> b = new Box<>();   // diamond operator since Java 7
b.set(42);
int n = b.get();                // no cast needed
```

#### B2. Type erasure — the foundation pitfall

At runtime, `Box<Integer>` and `Box<String>` are the **same class** — `Box`. Type parameters are erased to their bound (default `Object`). Consequences:

- `new T[10]` — compile error. Can't construct generic arrays.
- `o instanceof Box<Integer>` — compile error. Type info isn't there at runtime.
- `Box<Integer>` and `Box<String>` have the **same `Class` object**.
- Method overloading on `List<Integer>` vs `List<String>` is impossible — erases to the same signature.

**Workaround for "instanceof generic":** carry a `Class<T>` token explicitly:
```java
class Repo<T> {
    private final Class<T> type;
    Repo(Class<T> type) { this.type = type; }
}
new Repo<>(String.class);
```

#### B3. Bounded type parameters

```java
public static <T extends Comparable<T>> T max(List<T> list) {
    T best = list.get(0);
    for (T x : list) if (x.compareTo(best) > 0) best = x;
    return best;
}

max(List.of(3, 1, 4, 1, 5));          // Integer is Comparable<Integer>
max(List.of("b", "a"));               // String is Comparable<String>
```

**Multiple bounds:** `<T extends Number & Comparable<T>>` — class first, interfaces after.

#### B4. Wildcards

| Form | Meaning | Use |
|---|---|---|
| `List<?>` | Unknown element type | Read-only as `Object` |
| `List<? extends T>` | Some subtype of T | **Producer** — read T out |
| `List<? super T>` | Some supertype of T | **Consumer** — write T in |

**Why wildcards?** Because generics are **invariant**: `List<Integer>` is NOT a subtype of `List<Number>` even though `Integer` is a subtype of `Number`. Wildcards let you express variance.

#### B5. PECS — Producer Extends, Consumer Super (Effective Java Item 31)

**Producer:** "I read T's out."
```java
public static double sum(List<? extends Number> nums) {
    double total = 0;
    for (Number n : nums) total += n.doubleValue();
    return total;
}

sum(List.of(1, 2, 3));                    // List<Integer> ✓
sum(List.of(1.0, 2.0));                   // List<Double> ✓
sum(List.<Number>of(1, 2.0));             // List<Number> ✓
```

If `nums` had type `List<Number>` instead, only `List<Number>` would be acceptable — `List<Integer>` would be rejected.

**Consumer:** "I write T's in."
```java
public static void addOnes(List<? super Integer> dst) {
    for (int i = 0; i < 5; i++) dst.add(i);   // can write Integer
    // Integer x = dst.get(0);                // ERROR — only readable as Object
}

addOnes(new ArrayList<Integer>());
addOnes(new ArrayList<Number>());
addOnes(new ArrayList<Object>());
```

**Both:** exact `List<T>` — no wildcard.

**The canonical copy method:**
```java
public static <T> void copy(List<? super T> dst, List<? extends T> src) {
    for (T x : src) dst.add(x);
}
```
`src` is a producer (read); `dst` is a consumer (write). PECS.

**Real example — `Stack<E>` API:**
```java
public void pushAll(Iterable<? extends E> src) { ... }   // producer
public void popAll(Collection<? super E> dst) { ... }    // consumer
```
This lets a `Stack<Number>.pushAll` accept an `Iterable<Integer>`, and `popAll` write into a `Collection<Object>`. Without PECS, both fail to compile.

**References:**
- Effective Java Item 31 — "Use bounded wildcards to increase API flexibility"
- Oracle Generics tutorial — https://docs.oracle.com/javase/tutorial/java/generics/

---

<a id="day-4"></a>
## Day 4 — DSA-D: Encode/Decode + Longest Consecutive + First Blog Read

**Time budget:** 3h DSA + 1h architecture blog dissection.

### Part A — Problems

#### Problem 8: Encode and Decode Strings (LC 271, Medium — LC Premium)

- **Free mirror:** https://neetcode.io/problems/string-encode-and-decode
- **LintCode 659:** https://www.lintcode.com/problem/659/

**Statement.** Design `encode(List<String>) → String` and `decode(String) → List<String>`. Strings may contain ANY Unicode character including delimiters.

**Naive (wrong) approach.** Join with `","`. Breaks because content may contain `,`. Try `" "`? Content may contain ` `. There is no "safe" delimiter for arbitrary Unicode.

**Correct — length-prefix framing:** encode each string as `<length>#<content>`.

```java
public class Codec {
    public String encode(List<String> strs) {
        StringBuilder sb = new StringBuilder();
        for (String s : strs)
            sb.append(s.length()).append('#').append(s);
        return sb.toString();
    }

    public List<String> decode(String s) {
        List<String> out = new ArrayList<>();
        int i = 0;
        while (i < s.length()) {
            int hash = s.indexOf('#', i);
            int len = Integer.parseInt(s.substring(i, hash));
            out.add(s.substring(hash + 1, hash + 1 + len));
            i = hash + 1 + len;
        }
        return out;
    }
}
```

**Walk-through.** Encoding `["hi", "#world"]` → `"2#hi6##world"`. Decoder reads "2", takes next 2 chars after `#` → "hi", advances; reads "6", takes next 6 chars → "#world". The `#` inside content is harmless because we use the **count** to skip, never search.

**Why this matters far beyond LeetCode.** Length-prefix framing is **how real binary protocols work.** TCP is a byte stream — it doesn't know "messages." Application protocols frame messages with either:
- Length prefix (HTTP/2, Kafka wire protocol, Protobuf-on-wire, most binary RPCs).
- Delimiter with escaping (text protocols like HTTP/1.1 with `\r\n\r\n`, costlier).

Without framing, "where does one message end and the next begin" is unanswerable. This problem teaches a real systems pattern.

**Edge cases.** Empty list → `""`. Empty string in list → `"0#"`. Multi-digit lengths (e.g., 12345-char string → `"12345#..."`).

**Trade-off drill.**

*Q: Length-prefix vs delimiter-with-escaping?*
Three axes: **encoder simplicity, decoder simplicity, length-knowability**. Length-prefix needs the length up front — easy for in-memory strings, awkward for streams (chunked encoding solves this). Delimiter is streaming-friendly but requires escape sequences (= slower, larger payloads).

*Q: What if the protocol needs to be self-synchronizing (recover from corruption)?*
Length-prefix fails — once you mis-parse a length, you're permanently desynced. Delimiters with escape can resync at the next delimiter. Real protocols often combine both — length-prefixed frames with a sync marker every N frames (e.g., GStreamer, MPEG-TS).

**Scale-up addendum.** For huge payloads, length-prefix at message granularity isn't enough — you also chunk *within* a message (HTTP chunked transfer, Kafka batch records). Each chunk has its own header. For zero-copy parsing, length-prefix wins (you know exactly where the next message starts without scanning) — gRPC and Cap'n Proto exploit this.

**Junior says wrong, Staff says right:**
- Junior tries "join with rare unicode" — Staff knows that's never safe.
- Junior doesn't connect the problem to real protocols. Staff says "this is how HTTP/2 frames work."
- Junior uses `+` for string building (O(n²)). Staff uses `StringBuilder`.

---

#### Problem 9: Longest Consecutive Sequence (LC 128, Medium)

- **LeetCode:** https://leetcode.com/problems/longest-consecutive-sequence/
- **NeetCode:** https://neetcode.io/problems/longest-consecutive-sequence

**Statement.** Given `int[] nums`, return length of the longest sequence of consecutive integers. **Must run O(n).**

**Example.** `[100, 4, 200, 1, 3, 2]` → 4 (sequence `[1,2,3,4]`).

**Naive O(n log n).** Sort, scan. Easy but violates the constraint.

**Optimal O(n) — HashSet + "count only from run starts":**
```java
public int longestConsecutive(int[] nums) {
    Set<Integer> set = new HashSet<>();
    for (int n : nums) set.add(n);

    int longest = 0;
    for (int n : set) {
        // Only count from run starts
        if (!set.contains(n - 1)) {
            int current = n;
            int length = 1;
            while (set.contains(current + 1)) {
                current++;
                length++;
            }
            longest = Math.max(longest, length);
        }
    }
    return longest;
}
```

**Why is this O(n)?** The inner `while` loop runs at most n iterations in total **across all outer iterations** — because each element is counted only when its run starts. Without the `set.contains(n-1)` check, you'd count the same run from every starting position → O(n²). The check is the magic.

**Edge cases.** Empty → 0. All duplicates → 1. Negative numbers → fine.

**Trade-off drill.**

*Q: HashSet approach vs Union-Find?*
Union-Find is the alternative O(n α(n)) approach: for each `n` in nums, union `n` with `n-1` and `n+1` if they exist. Track max component size. Same complexity, but Union-Find shines when **the elements arrive in a stream** — you can union them online without needing all values up front. **For a batch input, the HashSet approach is simpler.**

*Q: Sort + scan — when is it actually acceptable?*
If n is small (≤ 10⁵) and the constraint isn't O(n), sort + scan is fine and dead-simple to write. For interview, lead with sort solution if you blank, then optimize to HashSet.

**Scale-up addendum.** For a **stream** with insertion only, Union-Find on intervals is the right tool — each new element either starts a new interval, extends one, or merges two. For arbitrary inserts and deletes, use a `TreeMap<Integer, Integer>` mapping interval-start → interval-end. This generalizes to "interval scheduling" problems.

**Junior says wrong, Staff says right:**
- Junior writes O(n²) (counts from every start). Staff knows the `set.contains(n-1)` trick.
- Junior can't explain WHY it's O(n). Staff: "each element is the inner-loop's `current` at most once, so total inner work is O(n)."
- Junior doesn't mention Union-Find. Staff offers it when interviewer says "stream."

---

### Part B — Architecture Judgment: First Blog Read (1 hr)

The Staff signal is *judgment*, and judgment is built by reading real architecture decisions, not tutorials. Habit-form this NOW.

#### Pick ONE blog this week:

1. **Netflix — "Tuning Tomcat for a High-Throughput, Fail-Fast System"**
   https://netflixtechblog.com/tuning-tomcat-for-a-high-throughput-fail-fast-system-e4d7b2fc163f
   Why: real tuning story; introduces queue-vs-thread-pool trade-offs you'll see again in Day 60 (HikariCP).

2. **Discord — "How Discord Stores Billions of Messages"**
   https://discord.com/blog/how-discord-stores-billions-of-messages
   Why: clear migration narrative (MongoDB → Cassandra), shows *why* they picked the new system. Foreshadows DDIA Ch 3 (storage) and Cassandra's LSM-tree story (Day 77).

3. **Uber — "Domain-Oriented Microservice Architecture" (DOMA)**
   https://www.uber.com/blog/microservice-architecture/
   Why: Staff-level org-and-tech decision. Counters the "all microservices, all the time" reflex.

#### The 7-question dissection template

For every blog, write ~1 page answering:

1. **What was the problem?** (Concrete numbers — "old system handled X QPS, we needed Y.")
2. **What was the previous solution?** Why did it stop working?
3. **What decision did they make?**
4. **What alternatives did they consider?** Why rejected?
5. **What trade-offs did they accept?** (What got worse so something else could get better.)
6. **What did they measure to know it worked?**
7. **What would I have done differently — and why?**

**Question 7 is the Staff-level one.** If you can't form an opinion, you haven't engaged deeply enough.

#### Storage convention

`architecture-notes/YYYY-MM-DD-title.md`. By Week 28 you'll have ~25 notes — a personal reference + concrete interview ammo ("when I read about Discord's Cassandra migration, what struck me was …").

---

<a id="day-5"></a>
## Day 5 — Review-D: Re-do + Behavioral + Reflection

**Time budget:** 1.5h DSA review + 1.5h behavioral + 1h reflection.

### Part A — DSA Review (1.5 hrs)

**Activity:** Pick 4 problems from Days 1–4. Re-solve from scratch, **timed**, **without peeking** at prior solutions.

| Problem | Target time |
|---|---|
| Two Sum | ≤ 5 min |
| Valid Anagram | ≤ 5 min |
| Contains Duplicate | ≤ 3 min |
| Group Anagrams | ≤ 12 min |
| Top K Frequent | ≤ 15 min |
| Product Except Self | ≤ 12 min |
| Valid Sudoku | ≤ 15 min |
| Encode/Decode Strings | ≤ 15 min |
| Longest Consecutive | ≤ 15 min |

**Grading:**
- ✅ Correct + within target → move on.
- ⚠️ Correct but slow → re-do once more next week.
- ❌ Stuck or buggy → re-do tomorrow morning before anything else. **Note the specific stuck point** ("forgot the `set.contains(n-1)` trick").

**The 80/20 of re-do.** Don't re-do what you nailed. Spaced repetition wins; concentrate on weak spots.

### Part B — Behavioral: 25 → 15 → 5 STAR (1.5 hrs)

#### Step 1: Brainstorm 25 (30 min)

Open a doc. Brainstorm everything from your 6-year career — every project, escalation, time you led, time you failed. **Quantity first.** Some sparks:

- Times you led (any size)
- Times you made a hard call
- Times you disagreed with manager/peer
- Times you helped someone (junior, peer, cross-team)
- Times you broke something and recovered
- Times you simplified / deleted code or process
- Times you sped something up (specific %)
- Times you negotiated scope
- Times you started something nobody asked you to
- Times you missed a deadline
- Times you adopted/rejected a new tech
- Times you led an on-call incident
- Times you mentored someone
- Times you presented to leadership

#### Step 2: Pick top 15 (15 min)

Prioritize by:
- **Concreteness** — you remember specific numbers ("p99: 800ms → 120ms").
- **Range** — covers different Amazon LPs.
- **Staff signal** — leadership, judgment, influence beats heads-down wins.

Tag each story (#1–#15).

#### Step 3: Write 5 in full STAR (45 min)

**STAR template:**
- **Situation** (1–2 sentences) — context, with a number.
- **Task** (1 sentence) — YOUR specific responsibility.
- **Action** (3–5 sentences) — what YOU did. First-person. Specific decisions. Use "I" not "we."
- **Result** (2–3 sentences) — measurable outcome. NUMBERS.

**Tag each with 2 Amazon LPs.** The 16 LPs:

> Customer Obsession · Ownership · Invent & Simplify · Are Right A Lot · Learn & Be Curious · Hire & Develop the Best · Insist on Highest Standards · Think Big · Bias for Action · Frugality · Earn Trust · Dive Deep · Have Backbone Disagree & Commit · Deliver Results · Strive to be Earth's Best Employer · Success & Scale Bring Broad Responsibility

**Staff-priority LPs (from the plan):** Ownership, Bias for Action, Think Big, Earn Trust, Are Right A Lot, Have Backbone Disagree & Commit, Deliver Results, Hire & Develop the Best, Insist on Highest Standards, Invent & Simplify.

**Each story tellable in 2.5 min spoken. Time yourself.**

**Example skeleton:**
```
Title: The legacy migration nobody wanted to own
Tags: Ownership · Bias for Action

S: In Q3 2024 our team inherited a 12-year-old Java service failing 5% of
   requests at peak. No one knew the code.
T: I was tech lead on a different project but had capacity. Manager said
   "look at it" — vague scope.
A: I owned a 4-week investigation. Wired up X-Ray (existed but unconfigured).
   Found 3 downstream calls with no timeouts — one slow downstream stalled
   the whole thread pool. Added Resilience4j timeouts + circuit breakers,
   deployed behind a feature flag, A/B'd for a week, rolled out fully.
R: Error rate 5% → 0.04%. p99 4.2s → 380ms. Zero added headcount. My
   investigation doc became the template our team uses for inherited
   services.
```

#### STAR self-grading rubric (apply to each of your 5)

| Dimension | What "passing" looks like | What's wrong with junior STAR |
|---|---|---|
| **Specific numbers** | "p99: 800ms → 120ms", "saved $48K/yr" | "improved performance significantly" |
| **First-person** | "I designed", "I decided", "I convinced" | "we built", "the team did" |
| **Decision under uncertainty** | Explicit alternatives considered | Linear narrative with one obvious choice |
| **Failure owned** (for failure stories) | What YOU did wrong + what you learned | Blaming others or circumstance |
| **Staff-shaped contribution** | Leadership, influence, judgment | Heads-down coding work only |
| **2.5-minute deliverable** | Times out clean | Rambles past 4 minutes |
| **LP-mappable** | 2 LPs you can defend if asked "why this LP?" | LPs slapped on without justification |
| **Failure mode handled** | "What if it had failed?" answerable | "It just worked" |

**File store:** `behavioral/stories.md`, one heading per story, with the rubric checkboxes.

**Anti-patterns (from plan's Staff anti-patterns):**
- "We" everywhere — interviewers want YOUR contribution.
- No metrics in result.
- No tradeoffs / alternatives mentioned.
- Story is just "I worked hard and it went well."

### Part C — Reflection (1 hr)

**End-of-week journal** — answer these 5 prompts in writing (use these every week for consistency):

1. **What's the strongest thing I did this week?**
2. **What confused me?** (Specific concept or problem.)
3. **What pattern keeps coming up that I haven't internalized?**
4. **Confidence ratings (1–5):** Big O · Collections · equals/hashCode · PECS · hashmap-pattern problems.
5. **One thing to change next week.**

**Tracker row:**

| Day | Type | Topics | Problems | Confidence | Notes |
|---|---|---|---|---|---|
| 1 | DSA-D | Big O, Two Sum, Anagram, Dup, Collections | 3 | / | |
| 2 | DSA-D | Group Anagrams, Top K, equals/hashCode | 2 | / | |
| 3 | DSA-D | Product Self, Sudoku, Generics PECS | 2 | / | |
| 4 | DSA-D | Encode/Decode, Longest Consecutive, Blog | 2 | / | |
| 5 | Review-D | Re-do, behavioral | 4 (re-do) | / | |

---

<a id="hashmap-internals"></a>
## Sidebar A — HashMap & ConcurrentHashMap Internals (Deep)

The Java Map deep dive. Asked at every Java-heavy company at Staff level. The shallow view from Day 1 Part C is necessary but not sufficient.

### S.A1. HashMap data structure

- An array of "buckets" (called `Node<K,V>[] table`).
- Each bucket is either:
  - `null` (no entries hash here),
  - a **linked list** of `Node<K,V>` (≤ 7 entries),
  - a **red-black tree** of `TreeNode<K,V>` (≥ 8 entries, *and* table capacity ≥ 64; otherwise resize instead of treeify).

### S.A2. Defaults

- Initial capacity: 16 (always a power of 2).
- Load factor: 0.75. Resizes when `size > capacity × loadFactor` → at size > 12 initially.
- Resize doubles capacity.
- TREEIFY_THRESHOLD = 8.
- UNTREEIFY_THRESHOLD = 6.
- MIN_TREEIFY_CAPACITY = 64.

### S.A3. The hash spread function

```java
static final int hash(Object key) {
    int h;
    return (key == null) ? 0 : (h = key.hashCode()) ^ (h >>> 16);
}
```

**Why XOR the upper 16 bits down?** Bucket index is computed as `hash & (capacity - 1)` — this is a mask that **only uses the low bits**. Many real-world `hashCode()` implementations have poor low-bit distribution (e.g., `Integer.hashCode()` returns the int itself — low bits collide for `16, 32, 48, …`). Mixing high bits into low bits via XOR spreads the variability and reduces bucket collisions.

This is one of the smartest 1-line optimizations in the JDK. If asked "what's special about HashMap's hash function?" — this is the answer.

### S.A4. Why capacity is a power of 2

Bucket index = `hash & (capacity - 1)`. This is a bitwise mask that's **far faster than `hash % capacity`** (modulo requires a division on most architectures). It only works because capacity is a power of 2 — for non-powers, `& (cap-1)` doesn't equal `% cap`.

This is why setting capacity to 17 doesn't actually produce capacity 17 — HashMap rounds up to the next power of 2 (32).

### S.A5. Resize mechanics — the clever bit

When the table doubles from `cap` to `2*cap`, each existing entry's new bucket index is **either the same as before, or the same plus `cap`**. This is because adding one more high bit to the mask either flips it (entry moves) or doesn't (entry stays).

```
Old mask: ...0 0 0 1 1 1 1   (cap = 16, so mask = 0x0F, 4 bits used)
New mask: ...0 0 1 1 1 1 1   (cap = 32, so mask = 0x1F, 5 bits used)

For each entry, the new bit (bit 4) is either 0 → stays at index i,
                                       or 1 → moves to index i + 16.
```

This means resize doesn't fully rehash — it splits each bucket into two ("kept" and "moved") linked lists in one pass. Java 8 implements this exactly. Significantly faster than full rehash.

### S.A6. Bucket treeification

When a bucket gets ≥ 8 entries AND table capacity ≥ 64, the bucket linked list converts to a red-black tree. Lookup in that bucket becomes O(log n) instead of O(n). The capacity-64 check prevents premature treeification on a small map — if capacity < 64, resize the table instead (cheaper than treeification).

**This is the JEP 180 change** (Java 8). It guards against adversarial inputs and badly-written `hashCode` functions. https://openjdk.org/jeps/180

### S.A7. Why HashMap is unsafe for concurrent use

Without external synchronization, two threads calling `put` simultaneously can:
- Corrupt the linked-list structure (one thread's link gets overwritten).
- In pre-Java-8 HashMap, a concurrent resize could create a **cyclic linked list**, causing `get` to spin forever in 100% CPU. (Famous production-killer.)
- In Java-8+, the cycle bug is fixed (resize is single-pass), but corruption is still possible.

**Always use `ConcurrentHashMap` for concurrent access.**

### S.A8. ConcurrentHashMap internals

**Pre-Java 8 (segments):** the map is divided into 16 (default) "segments," each is essentially a separate `HashMap` with its own lock. Reads are lock-free; writes lock only the relevant segment. Lock striping = N writers can write in parallel as long as they hit different segments.

**Java 8+ (per-bucket):** segments removed. Each *bucket* is a CAS / `synchronized` lock target. Reads are still lock-free (volatile reads). Writes:
- Empty bucket → CAS to insert (no lock).
- Non-empty bucket → `synchronized` on the bucket head node.

This is finer-grained than segments and avoids the segment array overhead for sparse maps.

**API differences from HashMap:**
- `null` keys and values are NOT allowed (because `get` returning null is ambiguous: "absent" vs "present-with-null").
- `size()` is O(n) and only weakly consistent (counts may be off under concurrent modification).
- Iteration is weakly consistent — sees state at some point but may miss / repeat entries.

**When to use what:**

| Need | Pick |
|---|---|
| Single-threaded map | `HashMap` |
| Concurrent reads + writes | `ConcurrentHashMap` |
| Concurrent reads + synchronized writes around a `HashMap` | `Collections.synchronizedMap(new HashMap<>())` — coarse-grained, slow |
| Read-mostly, infrequent writes | `Collections.unmodifiableMap(map)` (immutable after build) or `ConcurrentHashMap` |
| Legacy code wants `Hashtable`? | Replace with `ConcurrentHashMap`. Hashtable is fully synchronized + null-hostile + slow. |

### S.A9. The `modCount` / fail-fast iterator

`HashMap` (and most non-concurrent collections) tracks a `modCount` field — incremented on every structural modification. Iterators capture the value at creation; if it changes during iteration, the next `next()` call throws `ConcurrentModificationException`.

**This is best-effort, NOT a thread-safety guarantee:**
- It's a tripwire to catch bugs in single-threaded code (e.g., calling `list.remove` inside a `for-each`).
- In multi-threaded code, race conditions can defeat the check — fail-fast may miss real corruption.
- The exception name is misleading — it doesn't mean "another thread modified"; it means "you modified during iteration."

### S.A10. Tuning HashMap in real code

If you know your final size, **size the map up front** to avoid resizes:
```java
// Want to hold 1000 entries. Load factor 0.75. So initial capacity should be:
//   ceil(1000 / 0.75) = 1334 → next power of 2 = 2048.
Map<String, String> m = new HashMap<>(2048);
```

Or use the helper (Java 19+):
```java
Map<String, String> m = HashMap.newHashMap(1000);
```

For latency-critical code, **avoid map.get / map.put inside the hottest loops** — even amortized O(1) is dozens of nanoseconds with allocation. Consider primitive maps (Eclipse Collections, fastutil) when you've measured a real bottleneck.

---

<a id="java-traps"></a>
## Appendix — Java Traps for the Staff Round

Each of these has bitten production code at major companies. Memorize.

### T1. `Integer` cache & autoboxing `==` footgun

`Integer.valueOf(int)` caches instances in `[-128, 127]`. So:
```java
Integer a = 100, b = 100;
Integer c = 200, d = 200;
a == b;        // true  — same cached instance
c == d;        // false — different instances
a.equals(b);   // true
c.equals(d);   // true
```

**Rule:** never use `==` on boxed types. Always `equals`.

JVM flag `-XX:AutoBoxCacheMax=N` can extend the cache, but don't rely on it.

### T2. Auto-unboxing NullPointerException

```java
Integer x = null;
int y = x;     // NullPointerException on the unbox
```

**Rule:** if a value can be `null`, use `Integer`, not `int`. Or guard with `Optional`.

### T3. `list.remove(int)` vs `list.remove(Object)`

```java
List<Integer> list = new ArrayList<>(List.of(1, 2, 3));
list.remove(1);                       // removes INDEX 1 → list is [1, 3]
list.remove(Integer.valueOf(1));      // removes VALUE 1 → list is [2, 3]
```

Pre-existing Java warts because of autoboxing + overload resolution. **Always be explicit with `Integer.valueOf(...)` when removing by value from `List<Integer>`.**

### T4. `Arrays.asList(int[])` doesn't do what you think

```java
int[] a = {1, 2, 3};
List<int[]> l = Arrays.asList(a);     // ← single-element list of int[]!
```

`Arrays.asList` takes a varargs. `int[]` is one object (not unwrapped to `Integer[]`). For primitives, use `Arrays.stream(a).boxed().toList()` or `IntStream.of(a).boxed().toList()`.

Also: `Arrays.asList(arr)` returns a **fixed-size** list backed by the array. `list.add(x)` throws `UnsupportedOperationException`. To get a mutable list: `new ArrayList<>(Arrays.asList(arr))`.

### T5. `List.of(...)` is immutable

Since Java 9. Trying to add/remove throws `UnsupportedOperationException`. Same for `Set.of`, `Map.of`. Also: **null-hostile** — `List.of(null)` throws NPE.

To get a mutable list from `List.of`: `new ArrayList<>(List.of(1,2,3))`.

### T6. Array equality

```java
int[] a = {1, 2, 3};
int[] b = {1, 2, 3};
a.equals(b);          // false — identity equality on arrays
Arrays.equals(a, b);  // true  — content equality
```

For nested arrays: `Arrays.deepEquals(a, b)`. For hashing: `Arrays.hashCode(a)` / `Arrays.deepHashCode(a)`.

### T7. `String` immutability + interning

Every `+` on String creates a new object. In a loop: O(n²). Use `StringBuilder`.

String literals are interned in a JVM-wide pool. `"abc" == "abc"` is true (same interned reference). But `new String("abc") == "abc"` is false (new instance). `s.intern()` forces interning — almost never needed in modern code.

### T8. Comparator overflow

```java
Comparator<Integer> bad  = (a, b) -> a - b;             // overflows for big values
Comparator<Integer> good = Integer::compare;            // safe
Comparator<int[]> bad2  = (a, b) -> a[0] - b[0];        // also overflows
Comparator<int[]> good2 = (a, b) -> Integer.compare(a[0], b[0]);
```

`Integer.MIN_VALUE - 1` overflows positive. Real bug in real code.

### T9. `HashMap` allows null key + value; `ConcurrentHashMap` doesn't

```java
new HashMap<String, String>().put(null, "x");           // OK
new ConcurrentHashMap<String, String>().put(null, "x"); // NullPointerException
```

CHM forbids nulls because `get(k)` returning null is ambiguous under concurrent mutation (absent vs present-with-null).

### T10. `Comparable` vs `Comparator`

- `Comparable<T>`: natural ordering, defined inside class via `compareTo`.
- `Comparator<T>`: external ordering, passed to sort/PQ.
- `compareTo` must be **consistent with `equals`** (else `TreeSet`/`TreeMap` will surprise you — they use `compareTo`, not `equals`).

```java
// String example: case-insensitive Comparator does NOT match equals
Comparator<String> ci = String.CASE_INSENSITIVE_ORDER;
"FOO".compareTo("foo");                  // not 0 — natural order is case-sensitive
ci.compare("FOO", "foo");                // 0   — but "FOO".equals("foo") is false
new TreeSet<>(ci);                       // will treat "FOO" and "foo" as equal — surprising
```

### T11. `var` in Java 10+

```java
var list = new ArrayList<String>();      // ArrayList<String>
var m = new HashMap<String, Integer>();  // HashMap<String, Integer>
```

`var` is type inference, not dynamic typing. Works for locals only. Don't use when type isn't obvious from RHS.

### T12. Pattern matching for `instanceof` (Java 16+)

```java
if (o instanceof Point p) {     // p in scope inside the if
    return p.x + p.y;
}
```

Eliminates the redundant cast. Always prefer this form.

### T13. `Optional` is for return types, not fields

`Optional` is meant for return values to signal "may be absent." It's:
- **NOT** Serializable.
- **NOT** intended for fields (use nullable + `@Nullable`).
- **NOT** intended for method parameters (use overloads).

Storing `Optional` in a field is a code smell.

### T14. `Stream` is single-use

```java
Stream<Integer> s = List.of(1,2,3).stream();
s.count();
s.count();    // IllegalStateException — stream already operated on
```

Don't store streams in variables you reuse. Build them fresh.

### T15. `HashMap` iteration order is undefined

Don't rely on it. Don't rely on `HashSet` order. Don't rely on `entrySet()` order. If you need order: `LinkedHashMap` (insertion) or `TreeMap` (sorted by key).

---

<a id="cheatsheet"></a>
## Week Cheatsheet

### Big O reference

```
O(1)  <  O(log n)  <  O(√n)  <  O(n)  <  O(n log n)  <  O(n²)  <  O(2ⁿ)  <  O(n!)
```

Target complexity by n:
- n ≤ 25 → O(2ⁿ) ok
- n ≤ 1000 → O(n²) ok
- n ≤ 10⁵ → O(n log n)
- n ≤ 10⁶ → O(n)
- n ≤ 10⁹ → O(log n) or O(1)

### Collections decision tree

```
Need indexed access?           → ArrayList
Need front/back O(1) queue?    → ArrayDeque
Need min/max repeatedly?       → PriorityQueue
Need K→V, fastest, unordered?  → HashMap
Need K→V, insertion order?     → LinkedHashMap
Need K→V, sorted by key?       → TreeMap
Need set membership, unorder?  → HashSet
Need set membership, sorted?   → TreeSet
Concurrent map?                → ConcurrentHashMap
```

### Pattern → recipe

| Signal in problem | Pattern |
|---|---|
| "Find pair sums to target" | Hashmap of complements |
| "Group by property" | `Map<K, List<V>>` + `computeIfAbsent` |
| "Count frequencies" | `Map.merge(k, 1, Integer::sum)` |
| "Top K" | Heap of size K (or bucket sort if frequency bounded) |
| "Duplicate detection" | `HashSet` + `add()` returns false on dup |
| "Canonical form match" (anagrams etc) | Sort or count → key |
| "Longest consecutive" | HashSet + "only start from run-start" |
| "First non-repeating" | `LinkedHashMap` (insertion order) |

### Idioms introduced this week

```java
// Frequency count
map.merge(key, 1, Integer::sum);

// Group-by
map.computeIfAbsent(key, k -> new ArrayList<>()).add(value);

// Dup detection
if (!set.add(x)) { /* x was already present */ }

// Safe min-heap on int[]
new PriorityQueue<int[]>((a, b) -> Integer.compare(a[0], b[0]));

// Sudoku box index
int box = (row / 3) * 3 + (col / 3);

// Length-prefix framing
String framed = s.length() + "#" + s;

// Pattern-match instanceof
if (o instanceof Point p) { ... }
```

### Trade-off articulation template

For any "which tool / approach?" question, use the 3-axis template:

> "There are three things I'd think about: [X], [Y], and [Z]. If we're optimizing for X, then [A]. If Y matters more, [B]. In this case I'd lean toward [C] because [reason from problem statement] — but I'd want to validate that assumption."

Practice phrases:
- "It depends — what's the input size?"
- "I'd start simple. Here's the simplest thing that could work; here's when I'd evolve it."
- "I'd be wrong if [condition] — let me check."

### equals/hashCode rules

1. Override both, or neither.
2. `a.equals(b) → a.hashCode() == b.hashCode()`.
3. Use records for value objects.
4. Don't mutate fields used in hashCode after insertion.

### PECS

- Producer Extends — `List<? extends T>` for read-only.
- Consumer Super — `List<? super T>` for write-only.
- Exact `List<T>` for both.

---

<a id="checklist"></a>
## Week Checklist

### Knowledge (can you explain on a whiteboard?)

- [ ] Big O — all complexity classes with examples
- [ ] Amortized O(1) for `ArrayList.add` — explain why
- [ ] Collections complexity table — memorized
- [ ] equals/hashCode contract + what breaks if you forget hashCode
- [ ] PECS — when `? extends T` vs `? super T`
- [ ] Why HashMap default capacity = 16 (power of 2) and load factor = 0.75
- [ ] HashMap hash spread function — why XOR high bits into low
- [ ] HashMap resize: how entries move (same index OR same + oldCap)
- [ ] When bucket treeifies (≥8 entries AND cap ≥ 64)
- [ ] ConcurrentHashMap: pre-J8 segments vs J8+ per-bucket
- [ ] Why `ConcurrentHashMap` rejects null keys/values
- [ ] At least 5 Java traps from the appendix

### Problems (within target time)

- [ ] Two Sum (≤ 5 min)
- [ ] Valid Anagram (≤ 5 min)
- [ ] Contains Duplicate (≤ 3 min)
- [ ] Group Anagrams (≤ 12 min)
- [ ] Top K Frequent (≤ 15 min)
- [ ] Product Except Self (≤ 12 min)
- [ ] Valid Sudoku (≤ 15 min)
- [ ] Encode/Decode Strings (≤ 15 min)
- [ ] Longest Consecutive Sequence (≤ 15 min)
- [ ] 4 re-dos on Day 5 from scratch

### Trade-off drills practiced (verbalize each)

- [ ] Two Sum: hashmap vs two-pointer
- [ ] Anagram: sort vs frequency count
- [ ] Dup: sort vs HashSet vs BitSet
- [ ] Group Anagrams: sorted-key vs count-key
- [ ] Top K: heap vs bucket sort vs Count-Min Sketch (streaming)
- [ ] Product Except Self: with vs without division
- [ ] Sudoku: string keys vs bitmasks
- [ ] Encode/Decode: length-prefix vs delimiter-with-escape
- [ ] Longest Consecutive: HashSet vs Union-Find

### Behavioral

- [ ] 25 stories brainstormed
- [ ] Top 15 picked + tagged with LPs
- [ ] 5 full STARs written
- [ ] Self-graded against the rubric (8 dimensions per story)
- [ ] Running total recorded: **5 / 20** target stories

### Architecture judgment

- [ ] 1 blog dissected with 7-question template
- [ ] Filed at `architecture-notes/YYYY-MM-DD-title.md`

### Reflection

- [ ] 5 reflection prompts answered
- [ ] Tracker row filled
- [ ] Identified 1 thing to change for Week 2

---

<a id="references"></a>
## Consolidated Reference Links

**Big O**
- CTCI Ch VI (book)
- Abdul Bari Big O — https://www.youtube.com/watch?v=A03oI0znAoc
- Big-O cheatsheet — https://www.bigocheatsheet.com/

**Java Collections / internals**
- Oracle tutorial — https://docs.oracle.com/javase/tutorial/collections/
- Baeldung Java Collections — https://www.baeldung.com/java-collections
- JEP 180 (HashMap treeification) — https://openjdk.org/jeps/180
- HashMap Javadoc — https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/util/HashMap.html
- ConcurrentHashMap Javadoc — https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/util/concurrent/ConcurrentHashMap.html

**equals / hashCode**
- Effective Java Items 10–11 (book)
- Baeldung — https://www.baeldung.com/java-equals-hashcode-contracts

**Generics / PECS**
- Effective Java Item 31 (book)
- Oracle tutorial — https://docs.oracle.com/javase/tutorial/java/generics/

**Java traps**
- Effective Java (Bloch) — overall
- "Java Puzzlers" (Bloch & Gafter) — for the autoboxing / overload traps

**LeetCode problems**
- Two Sum — https://leetcode.com/problems/two-sum/
- Valid Anagram — https://leetcode.com/problems/valid-anagram/
- Contains Duplicate — https://leetcode.com/problems/contains-duplicate/
- Group Anagrams — https://leetcode.com/problems/group-anagrams/
- Top K Frequent — https://leetcode.com/problems/top-k-frequent-elements/
- Product Except Self — https://leetcode.com/problems/product-of-array-except-self/
- Valid Sudoku — https://leetcode.com/problems/valid-sudoku/
- Encode/Decode Strings (free) — https://neetcode.io/problems/string-encode-and-decode
- Longest Consecutive — https://leetcode.com/problems/longest-consecutive-sequence/

**NeetCode Roadmap** — https://neetcode.io/roadmap

**Engineering blogs (pick 1)**
- Netflix Tomcat tuning — https://netflixtechblog.com/tuning-tomcat-for-a-high-throughput-fail-fast-system-e4d7b2fc163f
- Discord billions of messages — https://discord.com/blog/how-discord-stores-billions-of-messages
- Uber DOMA — https://www.uber.com/blog/microservice-architecture/

**Behavioral**
- Amazon Leadership Principles (official) — https://www.amazon.jobs/content/en/our-workplace/leadership-principles

---

**End of Week 1.** Next: Week 2 — Two Pointers + Java Streams. Trigger with the generic prompt when ready.
