# Day 1 — DSA-D: Big O Fundamentals + Two Sum / Valid Anagram / Contains Duplicate + Java Collections

> Complete daily reference for Senior IC and Staff / Tech Lead tracks.
> Tier tags: `[BOTH]` `[SENIOR IC]` `[STAFF]`.

---

## § 0. Day Header

- **Day:** 1 of 140
- **Week:** 1 of 28 ("Java + Big O + Arrays I")
- **Day type:** DSA-D (DSA-heavy)
- **Time budget (per plan):** 1h theory + 2h DSA + 1h Java Collections refresh = 4h. **Elaboration here exceeds the time budget on purpose** — this is the reference, not the daily worksheet. Read what you need today; return for the rest.

### Why this day matters [BOTH]

Day 1 is load-bearing for the next 140. Three things you build here:

1. **Big O fluency** — without it you can't compare any two solutions, and every later interview round ends with "what's the complexity?" If you can't answer in ≤ 5 seconds, you sound junior regardless of how good your code is.
2. **The hashmap-complement pattern** — Two Sum is the canonical instance. This pattern recurs in 3Sum (Day 7), 4Sum, Subarray Sum Equals K, Two Sum II (sorted), Two Sum III (data-structure design). The pattern is "for each element, ask whether its complement was seen before."
3. **Java Collections internalization** — Spring services move data through these structures by the millions of ops/sec. Knowing the complexity table cold is not optional.

### Prerequisites [BOTH]

- Basic Java syntax (loops, classes, methods, generics signatures you can read).
- Familiarity with running a Java program locally (JDK 21 installed, an IDE).
- If any of these is missing, backfill before Day 1.

### Forward setup [BOTH]

What today enables in the rest of the plan:

| Concept introduced today | Used in (day) |
|---|---|
| Hashmap-complement pattern | Day 2 (Group Anagrams), Day 7 (3Sum), Day 41+ (Subarray Sum Equals K), Day 51 (combination problems use HashMap memoization) |
| Big O / amortized analysis | Every day; explicit again Day 7 (CTCI second pass), Day 21 (recursion depth) |
| `HashMap` internals | Day 2 (`equals/hashCode`), Day 8 (Streams), Day 80 (L1/L2 cache + locking) |
| Java Collections complexity table | Every DSA-D and JSD-D day |
| `equals/hashCode` preview | Day 2 (full contract) |
| PriorityQueue semantics | Day 46 (heap problems), Day 47 (caching strategies HLD) |

### Reader prerequisites checklist [BOTH]

- [ ] JDK 21 installed (`java --version` returns 21.x)
- [ ] IDE configured (IntelliJ IDEA Community is the default for this plan)
- [ ] Local Maven workspace where you can run a quick `Main` class
- [ ] LeetCode account, NeetCode bookmark
- [ ] A `progress.md` file you'll maintain across days
- [ ] An `architecture-notes/` folder for the weekly blog reads

---

## § 1. Table of Contents

1. [Theory — Big O Fundamentals](#theory-bigo)
2. [Theory — Java Collections (ArrayList, HashMap, HashSet, Deque, PriorityQueue)](#theory-collections)
3. [Problem — Two Sum (LC 1)](#problem-twosum)
4. [Problem — Valid Anagram (LC 242)](#problem-anagram)
5. [Problem — Contains Duplicate (LC 217)](#problem-duplicate)
6. [Cross-References](#cross-ref)
7. [Cheatsheet](#cheatsheet)
8. [Self-Assessment Checklist](#self-assess)
9. [Glossary](#glossary)
10. [References](#references)

---

<a id="theory-bigo"></a>
## § 2.A — Theory: Big O Fundamentals

### 2.A.1 Origin & Motivation [BOTH]

Big O notation was borrowed from analytic number theory by computer scientists in the 1970s — Donald Knuth's 1976 essay *"Big Omicron and Big Omega and Big Theta"* (ACM SIGACT News, vol. 8, no. 2) formalized its use in algorithm analysis. The original mathematical concept comes from Paul Bachmann (1894) and Edmund Landau (1909) — hence "Landau notation" as a synonym.

**The problem it solves:** before Big O, you compared algorithms by *measuring* them — wall-clock seconds on a specific machine with specific inputs. That measurement is useless across machines, useless across input sizes, and useless when the JIT compiler hasn't warmed up. Big O abstracts the machine and the input distribution away and asks one question: **how does cost grow with input size?**

**What it replaced:** ad-hoc instruction counting ("this algorithm does ~5n³ multiplications"). That counting is correct but coefficient-heavy and platform-bound. Big O is the coefficient-free, platform-independent layer on top.

**Why this matters for your interview:** every problem ends with a complexity question. Every system design ends with a capacity question. Every code review involves "is this fast enough at scale?" Big O is the language of all three.

### 2.A.2 Intuition [BOTH]

Big O is the answer to "what does cost look like when n is very large?"

A real-world analogue: if you can sort 100 photos by hand in 5 minutes, how long for 10,000 photos? Hand-sort is O(n²) — each photo gets compared with many others. The answer isn't "500 minutes" (linear extrapolation); it's much worse — about 833× more work, around 70 hours. Big O lets you predict that without doing the experiment.

The 30-second pitch: **Big O describes the shape of the cost-vs-input-size curve as inputs get large.** Constants and small terms vanish; only the dominant growth function survives.

### 2.A.3 Formal Definition [BOTH]

For functions f(n) and g(n) defined on positive integers:

> **f(n) = O(g(n))** if there exist positive constants c and n₀ such that 0 ≤ f(n) ≤ c·g(n) for all n ≥ n₀.

Informally: g(n) is an **upper bound** on f(n)'s growth rate (up to a constant factor, for sufficiently large n).

Related notations:

- **Big Omega (Ω):** f(n) = Ω(g(n)) means g is a **lower bound** — f grows at least this fast.
- **Big Theta (Θ):** f(n) = Θ(g(n)) means g is a **tight bound** — f grows at exactly this rate, sandwiched between two constant multiples of g.
- **Little o (o):** f(n) = o(g(n)) means f grows **strictly slower** than g (the ratio → 0).
- **Little omega (ω):** f(n) = ω(g(n)) means f grows **strictly faster** than g.

In interview contexts, "O(n)" almost always means tight worst-case bound — interviewers use Big O loosely where Θ would be technically correct.

### 2.A.4 Mechanics — How It Actually Works [BOTH]

To compute Big O of an algorithm:

1. **Count operations as a function of input size n.** Don't worry about constants.
2. **Identify the dominant term** — the one that grows fastest as n increases.
3. **Drop constants and lower-order terms.** `5n² + 100n + 7` becomes `O(n²)`.
4. **For nested constructs:** multiply (a loop of n inside a loop of n is n²).
5. **For sequential constructs:** add (then drop lower-order).
6. **For recursion:** write the recurrence relation, solve it (master theorem or substitution).

**Worked example — analyze this code:**

```java
void analyze(int n) {
    for (int i = 0; i < n; i++) {            // n iterations
        for (int j = 0; j < n; j++) {        // n iterations each
            System.out.println(i + j);        // O(1) work
        }
    }
    for (int k = 0; k < n; k++) {            // n more iterations
        System.out.println(k);                // O(1) work
    }
}
```

Total work = n·n·1 + n·1 = n² + n = **O(n²)**.

**Worked example — the master theorem.** For a recurrence T(n) = aT(n/b) + f(n):

- Compare f(n) with n^(log_b a).
- If f(n) is smaller → T(n) = Θ(n^(log_b a)). (Example: merge sort, T(n) = 2T(n/2) + n → Θ(n log n).)
- If f(n) is larger (by a polynomial factor) → T(n) = Θ(f(n)).
- If they're the same → T(n) = Θ(f(n) · log n).

Merge sort: a = 2, b = 2, f(n) = n. n^(log_2 2) = n. They match → Θ(n log n).

Binary search: T(n) = T(n/2) + O(1). a = 1, b = 2, f(n) = 1. n^(log_2 1) = 1. They match → Θ(log n).

### 2.A.5 Complexity / Cost Model [BOTH]

#### The growth ordering (memorize)

```
O(1)  <  O(log n)  <  O(√n)  <  O(n)  <  O(n log n)  <  O(n²)  <  O(n³)  <  O(2ⁿ)  <  O(n!)
```

#### Concrete numbers at n = 10⁶ (assume 10⁹ ops/sec, ~1 ns/op)

| Complexity | Ops at n=10⁶ | Wall time |
|---|---|---|
| `O(1)` | 1 | ~1 ns |
| `O(log n)` | ~20 | ~20 ns |
| `O(√n)` | 1,000 | ~1 μs |
| `O(n)` | 10⁶ | ~1 ms |
| `O(n log n)` | ~2·10⁷ | ~20 ms |
| `O(n²)` | 10¹² | ~16 minutes — **unacceptable** |
| `O(n³)` | 10¹⁸ | ~30 years — unrunnable |
| `O(2ⁿ)` | overflows at n ≈ 30 | — |
| `O(n!)` | overflows at n ≈ 12 | — |

#### The interview "n → complexity" rule of thumb

| n up to | Acceptable complexity |
|---|---|
| 10 | O(n!), O(2ⁿ) — backtracking fine |
| 25 | O(2ⁿ) — subsets fine |
| 1,000 | O(n²) ok |
| 10⁵ | O(n log n) |
| 10⁶ | O(n) |
| 10⁹ | O(log n) or O(1) |

Reading the constraint block on a LeetCode problem **immediately tells you the target complexity**. n ≤ 10⁵? You need O(n log n) or better. n ≤ 20? Backtracking is the expected shape.

#### Constant-factor discussion

Big O hides constants. Sometimes constants matter:

- An `O(n)` linear scan over `int[]` is ~10× faster than an `O(n)` scan over `List<Integer>` due to cache locality and boxing. Same Big O, very different real-time.
- Hash table operations are `O(1)` but with a much larger constant than array indexing. Below n ≈ 10–20, a linear scan over an array beats a HashMap lookup.
- Recursion has a fixed per-call overhead (~10 ns for a stack frame on the JVM). Iterative O(n) often beats recursive O(n) by 2–3× wall time despite identical Big O.

For interview answers, default to Big O. Mention constants only if the interviewer asks.

### 2.A.6 Implementation Walkthrough [BOTH]

Big O isn't code, but the *analysis* technique is. Here's the procedure applied to ten progressively trickier snippets:

```java
// Snippet 1
for (int i = 0; i < n; i++) sum += arr[i];
// Loop body O(1); loop runs n times → O(n) time, O(1) space.

// Snippet 2
for (int i = 0; i < n; i++)
    for (int j = 0; j < n; j++) count++;
// Nested n × n → O(n²) time, O(1) space.

// Snippet 3
for (int i = 0; i < n; i++)
    for (int j = i; j < n; j++) count++;
// Inner runs (n-i) times. Total = n + (n-1) + ... + 1 = n(n+1)/2 → O(n²).
// Triangular but still quadratic — coefficient ½ drops.

// Snippet 4
for (int i = 1; i < n; i *= 2) count++;
// i doubles each step; loop runs log₂ n times → O(log n).

// Snippet 5
for (int i = 0; i < n; i++)
    for (int j = 1; j < n; j *= 2) count++;
// Outer n × inner log n → O(n log n).

// Snippet 6
int fib(int n) {
    if (n <= 1) return n;
    return fib(n-1) + fib(n-2);
}
// T(n) = T(n-1) + T(n-2) + O(1). Bounded above by 2^n.
// Tight bound: O(φⁿ) where φ ≈ 1.618. Standard answer: O(2ⁿ) time, O(n) space (recursion depth).

// Snippet 7
boolean[] seen = new boolean[n];
for (int x : arr) seen[x] = true;
// O(n) time, O(n) space (allocation of `seen`).

// Snippet 8
List<List<Integer>> result = new ArrayList<>();
for (int i = 0; i < n; i++) {
    List<Integer> sub = new ArrayList<>(result);
    result.add(sub);
}
// Each iteration copies all current entries.
// Total work: 0 + 1 + 2 + ... + (n-1) = n(n-1)/2 → O(n²) time AND O(n²) space.

// Snippet 9
for (int i = n; i > 0; i /= 2)
    for (int j = 0; j < i; j++) count++;
// i = n, n/2, n/4, ..., 1. Inner runs i times.
// Total = n + n/2 + n/4 + ... = 2n → O(n).

// Snippet 10
void rec(int n) {
    if (n == 0) return;
    rec(n - 1);
    rec(n - 1);
}
// Two branches, depth n → O(2ⁿ) time. Recursion stack depth n → O(n) space.
```

### 2.A.7 Edge Cases & Pitfalls [BOTH]

| Pitfall | Reality |
|---|---|
| `s = s + c` in a loop | **O(n²)** — String is immutable; each `+` allocates. Use StringBuilder. |
| `list.remove(0)` on ArrayList | **O(n)** — shifts all elements. LinkedList.removeFirst() is O(1). |
| `list.contains(x)` on ArrayList | **O(n)** — linear scan. Use HashSet for membership. |
| `PriorityQueue.contains(x)` | **O(n)** — heap is not sorted linearly. |
| `Arrays.sort(int[])` | Dual-pivot Quicksort. O(n log n) average, O(n²) worst (very rare adversarial). |
| `Arrays.sort(Object[])` | TimSort. O(n log n) worst case. |
| Recursion depth | Counts toward space — O(depth). |
| `Collections.sort` on LinkedList | Allocates an array internally; not faster than sorting an ArrayList. |
| Auto-unboxing in hot loop | Allocations dominate. `int[]` beats `List<Integer>` by 5–10×. |
| Mistaking average for worst | HashMap is O(1) average, O(log n) worst (post-Java-8) — clarify in interviews. |

### 2.A.8 Internals — One Layer Deeper [STAFF]

#### Amortized analysis [STAFF]

Some operations are usually cheap but occasionally expensive. **Amortized cost** is the average cost across a sequence, charged so that no operation in the sequence is "unfairly" punished.

**Canonical example: `ArrayList.add`.** Backed by an `Object[]`. Most adds are O(1). When the array is full, allocate a new array (1.5× larger in Java's `ArrayList`, 2× in some C++ vectors), copy all elements, then add — O(n).

**Amortized accounting:** charge each `add` a fixed "tax" — say 3 cents:
- 1 cent pays for the actual insertion at the back.
- 2 cents go into a savings account.
- When you need to grow and copy n elements, the savings account has enough to pay for the copy.

So even though some individual `add`s are O(n), the **amortized cost per add is O(1)**.

**Three techniques for amortized analysis** (from CLRS Ch 17):

1. **Aggregate method:** total cost of n operations, divided by n.
2. **Accounting method:** assign costs to operations such that some "save up" credit for expensive ones (the savings analogy above).
3. **Potential method:** define a potential function Φ on the data structure state; amortized cost = actual cost + ΔΦ.

For interviews, the aggregate method is enough. **"ArrayList.add is amortized O(1) because doubling means expensive copies happen exponentially less often. Total cost over n adds is at most 2n, so per-add is constant."**

#### Why we drop constants [STAFF]

Two reasons:

1. **Machine independence.** A constant of 5 on a 2 GHz machine is 10 ns; on a 4 GHz machine it's 5 ns. The constant depends on the machine; the function doesn't.
2. **Operation choice.** "5n operations" could mean 5 cache hits or 5 cache misses — 100× difference. Constants are model-dependent; the growth function isn't.

When constants DO matter in practice: cache-conscious code, branch prediction, allocation cost, sequential vs random memory access. These are usually measured, not analyzed asymptotically.

#### Lower bounds and the sorting barrier [STAFF]

For *comparison-based* sorting, the lower bound is Ω(n log n). Proof sketch: a comparison sort is a decision tree; n! permutations means the tree has at least n! leaves; tree depth = log₂(n!) ≈ n log n.

**You can beat n log n** if you don't compare keys directly:
- **Counting sort:** O(n + k) where k is the range of values. Great for small k.
- **Radix sort:** O(d · (n + k)) where d is digit count.
- **Bucket sort:** O(n) average for uniformly distributed input.

This matters for Top K Frequent (Day 2) — bucket sort beats heap there.

#### Recurrences and the master theorem (deeper form) [STAFF]

For T(n) = a · T(n/b) + f(n) where a ≥ 1, b > 1:

- Compare f(n) with n^(log_b a).
- **Case 1:** if f(n) = O(n^(log_b a - ε)) for some ε > 0 → T(n) = Θ(n^(log_b a)).
- **Case 2:** if f(n) = Θ(n^(log_b a)) → T(n) = Θ(n^(log_b a) · log n).
- **Case 3:** if f(n) = Ω(n^(log_b a + ε)) AND regularity condition holds → T(n) = Θ(f(n)).

Strassen's matrix multiplication: T(n) = 7T(n/2) + n². log_2 7 ≈ 2.807. n² is smaller → T(n) = Θ(n^2.807). This is the famous "Strassen beats n³" result.

### 2.A.9 Real-World Failure Case Studies [STAFF]

#### Case 1: Apple goto fail (2014)

Not a Big O failure per se, but a great cautionary tale about reading code carefully — which is what Big O analysis fundamentally is. A duplicated `goto fail;` bypassed signature verification in iOS TLS. Code reviewers missed it. Lesson: trace the control flow, don't skim. https://en.wikipedia.org/wiki/SSL/TLS_implementation_flaws#Apple_goto_fail

#### Case 2: Cloudflare's regex CPU exhaustion (July 2 2019)

A single regex with catastrophic backtracking caused 100% CPU across Cloudflare's edge. The regex was O(2ⁿ) in the worst case despite looking innocent. Outage: 27 minutes, global. **Lesson:** regex engines do backtracking — analyze the worst-case behavior, not the average. https://blog.cloudflare.com/details-of-the-cloudflare-outage-on-july-2-2019/

#### Case 3: Knight Capital (August 2012)

$440M lost in 45 minutes due to a deployment glitch that reactivated dead code. Not a complexity bug, but: the dead code did O(unbounded) order placement. Lesson: O(unbounded) ops without circuit breakers will eventually destroy your business. https://en.wikipedia.org/wiki/Knight_Capital_Group#2012_stock_trading_disruption

#### Case 4: Java HashMap DoS (2011 / pre-Java-8)

Multiple frameworks (Tomcat, Jetty, several web frameworks in PHP/Python/Java) accepted POST parameters into a HashMap. Attackers crafted parameter names that all hashed to the same bucket → O(n²) processing per request → trivial DoS with a single malicious POST. Java 7 mitigated this by randomizing the hash; Java 8's bucket treeification (JEP 180) bounded the worst case at O(log n). https://www.ocert.org/advisories/ocert-2011-003.html

This is the most directly relevant case to today's content. **Always know your worst case.**

### 2.A.10 Alternatives — When NOT to use Big O alone [BOTH + STAFF extension]

[BOTH] Big O is the default, but it isn't the whole answer:

- **For latency-critical systems:** measure p50/p95/p99 wall-clock, don't just compute Big O. The constant matters.
- **For memory-bound workloads:** Big O for time might be optimal but cache behaviour matters more (see "mechanical sympathy").
- **For very small n:** the constant dominates; an O(n²) algorithm with a tiny constant can beat O(n log n).

[STAFF] **Three-axis answer template:** "It depends on three things: input size, constant factors, and the operation mix. For n ≤ 30, I might use the O(n²) algorithm because the constant is smaller and the code is simpler. For n in the millions, the O(n) algorithm wins by orders of magnitude. The decision should be data-driven — what's the actual input distribution?"

### 2.A.11 Connection to the Three Portfolio Projects [BOTH]

- **Project 1 (URL Shortener, Weeks 5–10):** redirect-path latency budget is ~100 ms p99. Every operation in the hot path needs to be O(1) — DynamoDB GetItem, ElastiCache hit. Big O of the request handler is the latency budget.
- **Project 2 (Event Pipeline, Weeks 9–19):** consumer throughput is per-message O(1) when ideal. N+1 queries on Day 55 will turn it into O(n²) under load — Big O of one logical operation matters even at single-machine scale.
- **Project 3 (Multi-region Service, Weeks 18–24):** capacity planning is Big O in disguise — "if QPS doubles, do we add resources linearly (O(n)) or quadratically (O(n²))?" The Day 115 capacity plan is essentially a Big O statement about your architecture.

### 2.A.12 Connection to the Real World [STAFF]

Big O thinking shows up in production all the time:

- **Stripe API design:** every Stripe endpoint has documented "computational complexity" implicit in pagination defaults. Idempotency keys are an O(1) memory cost per request — Stripe accepts this for stronger guarantees. https://stripe.com/blog/idempotency
- **Cassandra read paths:** O(log n) per SSTable, but with potentially many SSTables → tunable trade-off via compaction. Knowing the Big O of compaction (O(n log n) merge sort) tells you when to schedule it.
- **Postgres query planner:** chooses between Seq Scan (O(n)), Index Scan (O(log n + k)), and Bitmap Scan (O(n) but cache-friendly) based on cost estimates. EXPLAIN ANALYZE is basically Big O made concrete.
- **AWS DynamoDB:** advertises O(1) GetItem regardless of table size. This guarantee is what lets DDB scale linearly with partitions.

### 2.A.13 Common Misconceptions [BOTH]

1. **"Big O is the actual runtime."** No — it's the growth function, not the timing. Two O(n) algorithms can differ by 100× in real time.
2. **"O(n²) is always bad."** No — for n ≤ 1000, O(n²) is ~1 ms. Many production code paths run with small n; readability beats asymptotic optimality.
3. **"O(1) is always best."** Not if the constant is huge. A 10 ms O(1) hash lookup loses to a 100 μs O(log n) binary search for n ≤ 10⁶.
4. **"Recursive and iterative have the same complexity."** True for asymptotic, false for constant. Recursion's per-call overhead matters; tail-call optimization is absent on the JVM.
5. **"Amortized O(1) means worst-case O(1)."** No — amortized averages over a sequence. A single operation can still be O(n). Real-time systems need worst-case bounds, not amortized.

### 2.A.14 Interview Framing [BOTH]

**How to introduce Big O in an interview answer:**

After explaining your approach but before coding, state the complexity:
> "This is O(n) time because we do one pass through the array, and O(n) space because the hash map can hold up to n entries."

After coding, confirm:
> "Let me verify the complexity. Outer loop is n iterations, the inner work is O(1) average, so total is O(n). Space is O(n) for the map. Should I think about an O(1)-space solution if memory is constrained?"

**Signal you give by handling Big O well:** you understand your own code's behaviour at scale. **Anti-signals:** stating O(1) when you mean O(n); confusing time and space; refusing to discuss constants when asked.

### 2.A.15 Further Reading [BOTH]

- CTCI Ch VI ("Big O") — the standard interview-focused intro
- Abdul Bari Big O — https://www.youtube.com/watch?v=A03oI0znAoc (clearest video intro)
- Big-O cheatsheet — https://www.bigocheatsheet.com/
- CLRS (Cormen, Leiserson, Rivest, Stein) Ch 3 (Asymptotic Notation) — the formal reference
- CLRS Ch 17 (Amortized Analysis) — for the deeper accounting/potential methods
- Knuth's 1976 essay "Big Omicron and Big Omega and Big Theta" — historical foundation

---

<a id="theory-collections"></a>
## § 2.B — Theory: Java Collections (ArrayList, HashMap, HashSet, Deque, PriorityQueue)

### 2.B.1 Origin & Motivation [BOTH]

The Java Collections Framework (JCF) shipped in Java 1.2 (December 1998). Before it, you used `Vector`, `Hashtable`, `Stack`, and `Properties` — all synchronized, all `Object`-typed, all clunky. Joshua Bloch led the JCF design, modeled loosely on Doug Lea's `collections` package and on the C++ STL.

Goals of the JCF:

- **Unified interface hierarchy** — write code against `List`, run on any implementation.
- **Performance** — pick the implementation that fits your access pattern.
- **No accidental thread-safety** — the legacy synchronized collections were slow; JCF made unsynchronized the default and offered `Collections.synchronizedX` and (later) `ConcurrentX` for explicit concurrency.

The JCF made Java's standard library competitive with the C++ STL. Without it, the language would not have survived the 2000s.

### 2.B.2 Intuition [BOTH]

Five questions decide which collection you reach for:

1. **Do I need ordered access by index?** → `List`
2. **Do I need fast membership checks?** → `Set` or `Map`
3. **Do I need to process by FIFO or LIFO order?** → `Queue` / `Deque`
4. **Do I need to repeatedly pull out the min or max?** → `PriorityQueue`
5. **Is this shared across threads?** → `Concurrent*` variants

Within each category, the variant choice is driven by **insertion order, sorted order, or no order**.

### 2.B.3 Formal Definition [BOTH]

The hierarchy (abridged):

```
Iterable<T>
  └ Collection<T>
       ├ List<T>          — ordered, allows duplicates, indexed access
       │    ├ ArrayList
       │    ├ LinkedList   (also implements Deque)
       │    ├ Vector       (legacy, synchronized)
       │    └ Stack        (legacy, synchronized)
       ├ Set<T>            — no duplicates
       │    ├ HashSet
       │    ├ LinkedHashSet
       │    └ TreeSet      (SortedSet/NavigableSet)
       └ Queue<T>
            └ Deque<T>     — double-ended queue
                 ├ ArrayDeque
                 ├ LinkedList
                 └ ConcurrentLinkedDeque

Map<K,V>                   (separate hierarchy, NOT a Collection)
  ├ HashMap
  ├ LinkedHashMap
  ├ TreeMap                (SortedMap/NavigableMap)
  ├ ConcurrentHashMap
  └ Hashtable              (legacy, synchronized)
```

Contracts every implementer must satisfy:

- `Collection.add(e)` returns true if the collection was modified.
- `Set.add(e)` returns false if `e` is already present (no duplicates).
- `Map.put(k,v)` returns the previous value or null.
- All iterators on non-concurrent collections are fail-fast (best-effort).

### 2.B.4 Mechanics — How It Actually Works [BOTH]

#### `ArrayList`

- Backed by an internal `Object[]` called `elementData`.
- Default initial capacity: 10.
- Growth: when full, `newCap = oldCap + (oldCap >> 1)` (i.e., 1.5×). NOT 2× like Vector.
- `add(e)` writes at index `size`; increments `size`; resizes if needed.
- `get(i)` is a direct array access — O(1).
- `add(i, e)` and `remove(i)` use `System.arraycopy` to shift elements — O(n).
- Iteration order = insertion order.

#### `HashMap`

- Backed by `Node<K,V>[] table` — an array of buckets.
- Default capacity: 16 (must be a power of 2).
- Default load factor: 0.75. Resizes (doubles) when `size > capacity × loadFactor`.
- Bucket is a linked list (or red-black tree once treeified).
- `put`:
  1. Compute `hash = spread(key.hashCode())` where `spread(h) = h ^ (h >>> 16)`.
  2. Compute index = `hash & (capacity - 1)` (works because capacity is power of 2).
  3. Walk the bucket; if a node has equal key, replace value; else append.
  4. If bucket size ≥ 8 AND capacity ≥ 64 → treeify the bucket (red-black tree).
  5. Possibly resize.
- `get`: similar walk; equal key returns value, else null.
- Allows one null key (stored at bucket 0) and null values.

#### `HashSet`

- Backed by a `HashMap<E, Object>` where every value is a sentinel `PRESENT`.
- All HashMap rules apply.
- `add(e)` returns false if e was already present — golden idiom for dedup.

#### `ArrayDeque`

- Backed by a circular array. Two pointers: head and tail.
- All push/pop/peek operations on either end are O(1) amortized.
- Resizes by doubling when full.
- Faster than `LinkedList` for stack/queue use cases because of cache locality.

#### `PriorityQueue`

- Backed by an array representing a binary min-heap.
- Children of index `i` are at `2i+1` and `2i+2`; parent at `(i-1)/2`.
- `offer(e)`: append at end (index `size`), then "sift up" — swap with parent while smaller. O(log n).
- `poll()`: take root (index 0), move last element to root, "sift down". O(log n).
- `peek()`: return index 0. O(1).
- **`contains(e)` is O(n)** — heap is not sorted linearly. Iteration is also not sorted.
- Min-heap by default. For max-heap: `new PriorityQueue<>(Comparator.reverseOrder())`.

### 2.B.5 Complexity / Cost Model [BOTH]

| Op | ArrayList | LinkedList | HashMap | HashSet | TreeMap | ArrayDeque | PriorityQueue |
|---|---|---|---|---|---|---|---|
| `add` end | O(1) amort. | O(1) | O(1) avg | O(1) avg | O(log n) | O(1) amort. | O(log n) |
| `add` index 0 | O(n) | O(1) | — | — | — | O(1) addFirst | — |
| `get(i)` | O(1) | O(n) | O(1) avg | (contains) O(1) | O(log n) | peek O(1) | peek O(1) |
| `remove(i)` | O(n) | O(1) given node | O(1) avg | O(1) avg | O(log n) | O(1) ends | poll O(log n) |
| `contains` | O(n) | O(n) | O(1) avg key | O(1) avg | O(log n) | O(n) | **O(n)** |
| Order | insertion | insertion | none | none | sorted | insertion | heap order |

**Concrete cost at n = 10⁶ (rough numbers):**

- ArrayList.add at end: ~10 ns amortized.
- ArrayList.get(i): ~5 ns (cache hit).
- HashMap.get: ~30–50 ns (hash + lookup + chain traversal of length ~1).
- TreeMap.get: ~100–300 ns (20 cache-missing tree traversals).
- PriorityQueue.offer/poll: ~100–300 ns (heap log depth).

Constants matter for hot loops.

### 2.B.6 Implementation Walkthrough [BOTH]

```java
import java.util.*;

public class CollectionsCookbook {
    public static void main(String[] args) {
        // === List ===
        List<Integer> list = new ArrayList<>();
        list.add(1); list.add(2); list.add(3);   // [1, 2, 3]
        list.set(1, 20);                          // [1, 20, 3]
        list.remove(Integer.valueOf(20));         // by value
        list.remove(0);                           // by index
        // List<Integer> → int[]
        int[] arr = list.stream().mapToInt(Integer::intValue).toArray();

        // === Set ===
        Set<Integer> set = new HashSet<>();
        boolean wasNew = set.add(5);              // true
        wasNew = set.add(5);                      // false — golden dedup idiom
        set.contains(5);                          // true

        // === Map ===
        Map<String, Integer> counts = new HashMap<>();
        counts.merge("apple", 1, Integer::sum);   // counts = {apple=1}
        counts.merge("apple", 1, Integer::sum);   // counts = {apple=2}

        // computeIfAbsent for grouping
        Map<String, List<Integer>> groups = new HashMap<>();
        groups.computeIfAbsent("primes", k -> new ArrayList<>()).add(2);
        groups.computeIfAbsent("primes", k -> new ArrayList<>()).add(3);

        // === Deque ===
        Deque<Integer> stack = new ArrayDeque<>();
        stack.push(1); stack.push(2); stack.push(3);
        stack.peek();                              // 3
        stack.pop();                               // 3

        Deque<Integer> queue = new ArrayDeque<>();
        queue.offer(1); queue.offer(2);
        queue.poll();                              // 1 (FIFO)

        // === PriorityQueue (min-heap) ===
        PriorityQueue<Integer> minHeap = new PriorityQueue<>();
        minHeap.offer(3); minHeap.offer(1); minHeap.offer(2);
        minHeap.poll();                            // 1
        minHeap.poll();                            // 2

        // Max-heap via reverse comparator
        PriorityQueue<Integer> maxHeap = new PriorityQueue<>(Comparator.reverseOrder());

        // Custom comparator on int[]
        PriorityQueue<int[]> pq = new PriorityQueue<>(
            (a, b) -> Integer.compare(a[0], b[0])    // NOT a[0] - b[0] (overflow)
        );
    }
}
```

### 2.B.7 Edge Cases & Pitfalls [BOTH]

| Pitfall | What happens |
|---|---|
| `list.remove(1)` where list is `List<Integer>` | Removes index 1, not value 1. Use `Integer.valueOf(1)` for value. |
| `Arrays.asList(new int[]{1,2,3})` | Returns `List<int[]>` of size 1 (not `List<Integer>` of size 3). |
| `Arrays.asList(...)` add/remove | Throws `UnsupportedOperationException` — list is fixed-size. |
| `List.of(...)` mutation | Throws `UnsupportedOperationException` — immutable. |
| `HashMap.put(null, v)` | Allowed (one null key). |
| `ConcurrentHashMap.put(null, v)` | Throws NPE (null forbidden). |
| Modifying list during for-each | `ConcurrentModificationException`. Use `Iterator.remove()` or `removeIf`. |
| `Comparator a - b` | Overflows for large ints. Use `Integer.compare(a, b)`. |
| Heap iteration | NOT sorted — only `poll()` returns sorted order. |
| HashMap iteration order | Undefined. Use `LinkedHashMap` for insertion order. |
| Putting mutable object in HashSet then mutating | Object becomes "lost" — wrong bucket. |
| `Stack<T>` | Legacy. Synchronized. Slow. Use `ArrayDeque` as a stack. |

### 2.B.8 Internals — One Layer Deeper [STAFF]

#### Why HashMap capacity is a power of 2 [STAFF]

Bucket index = `hash & (capacity - 1)`. The bitwise AND is **3–10× faster than modulo** because modulo requires a CPU integer division (multi-cycle on most architectures). The AND works as a modulo only when capacity is a power of 2 — for non-powers, `& (cap-1)` doesn't equal `% cap`.

If you pass `new HashMap<>(17)`, Java rounds up to the next power of 2 (32). Initial capacity isn't honored literally.

#### The hash spread function [STAFF]

```java
static final int hash(Object key) {
    int h;
    return (key == null) ? 0 : (h = key.hashCode()) ^ (h >>> 16);
}
```

XOR-ing the high 16 bits into the low 16 mixes information from both halves of the hash code. Without this, **bucket index only uses low bits** (because of the `& (cap-1)` mask), and many `hashCode()` implementations have poor low-bit distribution.

Example: `Integer.hashCode()` returns the int itself. Without spread, keys 16, 32, 48, 64 all hash to bucket 0 (when cap=16). After spread: the high bits of these values get mixed in, distributing them across buckets.

This is one of the smartest one-line optimizations in the JDK. If asked "what's clever about HashMap's hash function?" — this.

#### Resize: the doubling trick [STAFF]

When capacity doubles from `cap` to `2*cap`, each entry's new index is **either the same (i) or i + cap**. This is because adding one more high bit to the bucket mask either flips it (entry moves) or doesn't (entry stays).

```
Old mask (cap=16):   ...0 0 0 1 1 1 1
New mask (cap=32):   ...0 0 1 1 1 1 1

For each entry's hash, the new bit (bit 4) is either 0 → stays at i,
                                             or 1 → moves to i + 16.
```

Java 8+ exploits this: resize splits each bucket's list into a "low" list (stays at i) and a "high" list (moves to i + cap) in a single pass, without rehashing every entry. This is the resize optimization most candidates don't know about.

#### Bucket treeification (JEP 180) [STAFF]

When a bucket reaches 8 entries AND the table capacity is ≥ 64, the linked-list bucket is converted to a red-black tree. Lookup in that bucket becomes O(log n) instead of O(n).

The capacity-64 threshold is a safeguard: on a small map, treeify wastes memory; better to resize the whole table.

This change bounded HashMap worst-case lookup at O(log n) — historically (pre-Java-8) it was O(n) and exploited by adversarial inputs (see Real-World Failure Case 4 above).

JEP 180: https://openjdk.org/jeps/180

#### Why HashMap is unsafe for concurrent access [STAFF]

Without synchronization, two threads calling `put` simultaneously can:

- Overwrite each other's linked-list pointers (corruption).
- In pre-Java-8 HashMap, concurrent resize created cyclic linked lists, causing `get()` to spin at 100% CPU — a famous production-killer.
- Java 8+ fixes the cycle bug (resize is single-pass) but corruption is still possible.

Use `ConcurrentHashMap` for concurrent access. Day 80 will revisit when we look at L1/L2 caches and locking.

#### ArrayDeque vs LinkedList [STAFF]

Both implement `Deque`. ArrayDeque wins for almost every workload:

- **Cache locality:** circular array is contiguous; LinkedList nodes are scattered.
- **Allocation:** ArrayDeque allocates one big array; LinkedList allocates a Node per element (24 bytes overhead each).
- **Speed:** ArrayDeque is 2–10× faster for push/pop in benchmarks.

LinkedList wins only if you need O(1) middle insertion **and** already hold the node — rare in practice.

#### PriorityQueue internals [STAFF]

Array-backed binary heap. Storage layout:

```
Index:    0  1  2  3  4  5  6
Element: 10 15 20 25 30 35 40
              ↑↑          ↑↑
        children of 0  children of 1
```

Sift-up cost is O(log n) — the depth of the heap is ⌈log₂(n+1)⌉. Heap construction from an unsorted array is O(n) (not O(n log n)) using `heapify` — but Java's PriorityQueue uses a different constructor that's O(n log n).

`contains(e)` is O(n) because heap order doesn't help you find arbitrary elements. Same for `remove(Object)`.

### 2.B.9 Real-World Failure Case Studies [STAFF]

#### Case 1: The 2011 HashMap DoS (covered above)

Same incident as in §2.A.9, but worth re-stating: attackers crafted POST keys that all hashed to the same bucket → O(n²) per request. Tomcat, Jetty, Apache Geronimo all affected. Mitigation: Java 7 added hash randomization; Java 8 treeified buckets. https://www.ocert.org/advisories/ocert-2011-003.html

#### Case 2: GC pause from giant HashMap [STAFF]

A common production issue: a service caches "everything" in a `HashMap<String, ExpensiveObject>` that grows to 50M entries. Resize allocates a new array of 100M+ references — this triggers a major GC pause that can be 10+ seconds.

**Lesson:** size your HashMaps. `new HashMap<>(expectedSize / loadFactor + 1)` avoids most resizes.

#### Case 3: LinkedList everywhere (a real anti-pattern) [STAFF]

A senior engineer once told a junior "LinkedList has O(1) insertion." The junior used `LinkedList` for every list in their service. Performance dropped by 5× due to cache misses on iteration. Lesson: **theoretical complexity isn't real-world performance.** Always prefer ArrayList unless you've measured.

#### Case 4: `synchronized` Vector / Hashtable hot spot [STAFF]

A legacy Spring service uses `Hashtable` (synchronized by default). Every read acquires the lock. Under 1000 concurrent threads, the lock becomes the bottleneck — throughput drops 100×. Fix: replace with `ConcurrentHashMap`. Lesson: never use the legacy synchronized collections.

### 2.B.10 Alternatives — When NOT to use [BOTH + STAFF extension]

| Default | When to switch |
|---|---|
| `ArrayList` | LinkedList: never in 2026. Use ArrayDeque if you need Deque semantics. |
| `HashMap` | `ConcurrentHashMap` if multi-threaded. `LinkedHashMap` if you need insertion order or LRU. `TreeMap` if sorted by key. `EnumMap` if keys are enums. |
| `HashSet` | `LinkedHashSet` for insertion order. `TreeSet` for sorted. `EnumSet` for enums (extremely fast bitmap-based). |
| `ArrayDeque` | `ConcurrentLinkedDeque` if multi-threaded and you need a deque. |
| `PriorityQueue` | `TreeMap` if you need both min-extraction and ordered iteration. `IndexMinPriorityQueue` (not in JDK) if you need O(log n) decrease-key. |
| Standard JCF | Eclipse Collections / fastutil — primitive maps avoid boxing, 5–10× faster. Use when measured-needed. |

[STAFF] **3-axis trade-off for "which Map?"**: there are three axes — **ordering need, concurrency need, key type**. For unordered, single-threaded, arbitrary keys: HashMap. Add ordering need → LinkedHashMap or TreeMap. Add concurrency → ConcurrentHashMap. Restrict to enums → EnumMap. The default is HashMap; deviations need justification.

### 2.B.11 Connection to the Three Portfolio Projects [BOTH]

- **Project 1 (URL Shortener):** the in-memory rate limiter (Day 39) uses a `ConcurrentHashMap<String, TokenBucket>`. The cache layer uses `ConcurrentHashMap` as L1 cache before falling through to ElastiCache.
- **Project 2 (Event Pipeline):** the idempotency check (Day 54) uses a `HashSet<String>` of recently-seen idempotency keys, behind a `LinkedHashMap` LRU eviction. The consumer's deduplication batch builder uses `HashMap`.
- **Project 3 (Multi-region):** feature flag service backed by `ConcurrentHashMap<String, FlagDefinition>`. Hot reload via atomic reference swap.

### 2.B.12 Connection to the Real World [STAFF]

- **Kafka client offsets**: stored client-side in a `ConcurrentHashMap<TopicPartition, OffsetAndMetadata>`.
- **Spring's bean factory**: `DefaultListableBeanFactory` uses several maps (`beanDefinitionMap`, `singletonObjects`) — all `ConcurrentHashMap` for thread safety during startup.
- **Hibernate's L1 cache**: a `Map<EntityKey, Object>` per Session — drives the L1 hit on Day 80.
- **Tomcat/Netty connection registries**: ConcurrentHashMap keyed by connection ID.

Every Java backend service touches these structures millions of times per second. Cost matters.

### 2.B.13 Common Misconceptions [BOTH]

1. **"LinkedList has O(1) insertion so it's faster."** No — cache misses kill it. ArrayList wins for nearly every real workload.
2. **"HashMap is O(1)."** Average O(1). Worst case O(log n) post-Java-8 (was O(n) pre-Java-8).
3. **"`Hashtable` and `HashMap` are the same thing."** No — Hashtable is synchronized, null-hostile, legacy. Never use.
4. **"`ConcurrentHashMap.size()` is exact."** No — it's a snapshot; weakly consistent under concurrent mutation.
5. **"Iteration order on HashMap is consistent."** No — implementation-defined and unstable across JVM versions.
6. **"`PriorityQueue` iteration is sorted."** No — only `poll()` returns heap order.
7. **"`Stack` is a Java idiom."** No — `Stack` is legacy (extends Vector). Use `ArrayDeque`.

### 2.B.14 Interview Framing [BOTH]

**How to talk about collections in interviews:**

- When choosing a data structure, **lead with constraints**: "Given we need fast lookup by key, no ordering, and single-threaded access, HashMap is the right default."
- When discussing complexity, distinguish average vs worst: "HashMap.get is average O(1), worst case O(log n) post-Java-8."
- When asked "ArrayList or LinkedList?": "ArrayList, almost always — cache locality beats theoretical O(1) insertion in real workloads."
- When asked "HashMap or ConcurrentHashMap?": "HashMap unless I have concurrent writes. ConcurrentHashMap has a cost — null-hostility and slightly higher per-op constant — so I only pay it when I need thread safety."

**Anti-signals (avoid):**

- Naming `Hashtable`, `Vector`, or `Stack` as a deliberate choice.
- Saying "O(1)" without distinguishing average vs worst.
- Picking LinkedList without justification.
- Forgetting that `Map` is not a `Collection`.

### 2.B.15 Further Reading [BOTH]

- Oracle Collections tutorial — https://docs.oracle.com/javase/tutorial/collections/
- HashMap Javadoc (Java 21) — https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/util/HashMap.html
- ConcurrentHashMap Javadoc — https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/util/concurrent/ConcurrentHashMap.html
- JEP 180 (HashMap treeification) — https://openjdk.org/jeps/180
- Baeldung Java Collections — https://www.baeldung.com/java-collections
- Effective Java Items 28–34 (Generics) — relevant context for typed collections
- *Java Performance* (Oaks, O'Reilly) Ch 12 — collection performance

---

<a id="problem-twosum"></a>
## § 3.A — Problem: Two Sum

### 3.A.1 Problem Statement [BOTH]

Given an array of integers `nums` and a target integer `target`, return the indices `i` and `j` (with `i ≠ j`) such that `nums[i] + nums[j] == target`. You may assume exactly one solution exists, and you can't use the same element twice.

- **LeetCode:** https://leetcode.com/problems/two-sum/ (LC 1)
- **NeetCode:** https://neetcode.io/problems/two-integer-sum
- **Frequency:** Among the most-asked problems at every FAANG. Amazon, Google, Meta, Microsoft commonly use as a warmup or screening question.
- **Difficulty:** Easy.

### 3.A.2 Clarifying Questions [BOTH]

Before coding:

1. **"Can the same index be used twice?"** No — i ≠ j. (Otherwise `[3], target=6` returns `[0,0]` — usually disallowed.)
2. **"Is exactly one solution guaranteed?"** Yes per problem statement; in real interviews, clarify.
3. **"Should I return indices or values?"** Indices per LC1; for Two Sum II (sorted) we return 1-indexed values.
4. **"Can the array be empty or have one element?"** Implicitly no (one solution exists requires ≥2).
5. **"Are there duplicates? Can `nums[i] == nums[j]`?"** Yes — `[3,3], target=6` is valid.
6. **"Are values bounded? Negative numbers allowed?"** Per LC: `-10^9 ≤ nums[i] ≤ 10^9`. Negative numbers allowed.
7. **"Sorted or unsorted?"** Unsorted (sorted variant is Two Sum II — different problem).

Each clarification matters because the data structure choice depends on it.

### 3.A.3 Brute Force [BOTH]

```java
public int[] twoSum(int[] nums, int target) {
    for (int i = 0; i < nums.length; i++) {
        for (int j = i + 1; j < nums.length; j++) {
            if (nums[i] + nums[j] == target) {
                return new int[]{i, j};
            }
        }
    }
    return new int[]{};   // never reached given guarantee
}
```

- **Time:** O(n²) — nested pair enumeration.
- **Space:** O(1) — no auxiliary structure.
- **Why suboptimal:** for n = 10⁴, n² = 10⁸ — at the edge of acceptable. For n = 10⁵+, this fails.

### 3.A.4 Intermediate Improvements [BOTH]

**Sort + binary search:**

```java
public int[] twoSumSortBinSearch(int[] nums, int target) {
    // Pair each value with its original index
    int[][] indexed = new int[nums.length][2];
    for (int i = 0; i < nums.length; i++) {
        indexed[i] = new int[]{nums[i], i};
    }
    Arrays.sort(indexed, (a, b) -> Integer.compare(a[0], b[0]));
    int[] sorted = new int[nums.length];
    for (int i = 0; i < nums.length; i++) sorted[i] = indexed[i][0];

    for (int i = 0; i < nums.length; i++) {
        int need = target - sorted[i];
        int lo = i + 1, hi = nums.length - 1;
        while (lo <= hi) {
            int mid = (lo + hi) >>> 1;
            if (sorted[mid] == need) {
                return new int[]{indexed[i][1], indexed[mid][1]};
            } else if (sorted[mid] < need) lo = mid + 1;
            else hi = mid - 1;
        }
    }
    return new int[]{};
}
```

- **Time:** O(n log n) — sort dominates.
- **Space:** O(n) — index pairing.
- **Insight:** sorting + binary search beats brute force, but the hashmap solution beats it again.

### 3.A.5 Optimal Solution(s) [BOTH]

#### Optimal 1 — One-pass hashmap (the canonical answer)

```java
public int[] twoSum(int[] nums, int target) {
    Map<Integer, Integer> seen = new HashMap<>();   // value → index
    for (int i = 0; i < nums.length; i++) {
        int complement = target - nums[i];          // what we need
        if (seen.containsKey(complement)) {
            return new int[]{seen.get(complement), i};
        }
        seen.put(nums[i], i);                       // record for future
    }
    return new int[]{};
}
```

Line-by-line commentary:

- `seen` maps **value → first-seen index**. We need indices in the answer.
- `complement = target - nums[i]` — for each element, ask "what value would complete the pair?"
- `containsKey` check is O(1) average.
- We check BEFORE inserting — this prevents `[3, 2, 4], target = 6` from matching `3+3`. Index-pair correctness depends on this ordering.
- Insert is unconditional; if a duplicate value appears later, we overwrite — but we'd have returned already if the earlier value paired with anything.

#### Optimal 2 — Two-pass hashmap (slightly more readable, same complexity)

```java
public int[] twoSumTwoPass(int[] nums, int target) {
    Map<Integer, Integer> map = new HashMap<>();
    for (int i = 0; i < nums.length; i++) map.put(nums[i], i);
    for (int i = 0; i < nums.length; i++) {
        int complement = target - nums[i];
        if (map.containsKey(complement) && map.get(complement) != i) {
            return new int[]{i, map.get(complement)};
        }
    }
    return new int[]{};
}
```

Pass 1 fills the map; pass 2 queries. **Slightly worse** because `[3,3], target=6` requires the `map.get(complement) != i` check — and the map only retains the *last* index for duplicate values.

The one-pass version is preferred.

### 3.A.6 Worked Trace [BOTH]

Input: `nums = [2, 7, 11, 15], target = 9`.

| i | nums[i] | complement | seen before? | Action | seen after |
|---|---|---|---|---|---|
| 0 | 2 | 7 | No | put 2→0 | {2: 0} |
| 1 | 7 | 2 | **Yes (index 0)** | return [0, 1] | — |

Result: `[0, 1]`.

Input: `nums = [3, 3], target = 6`.

| i | nums[i] | complement | seen? | Action | seen after |
|---|---|---|---|---|---|
| 0 | 3 | 3 | No | put 3→0 | {3: 0} |
| 1 | 3 | 3 | **Yes** | return [0, 1] | — |

The check-before-insert ordering is what makes this work — at i=0 we don't yet have 3 in the map.

### 3.A.7 Complexity Analysis [BOTH]

- **Time: O(n).** Single pass, each iteration does a constant number of HashMap operations. HashMap ops are O(1) average, O(log n) worst-case post-Java-8 (treeified bucket). So strictly O(n log n) worst-case, but typically reported O(n) because average dominates.
- **Space: O(n).** The map can hold up to n - 1 entries before we find the match.
- **No output array allocation counts** — we return a fixed 2-element array.

Compared to brute force: time goes from O(n²) to O(n), at the cost of O(n) space. **Time-space trade.**

### 3.A.8 Edge Cases [BOTH]

| Case | Behaviour |
|---|---|
| `[3, 3], target = 6` | Returns `[0, 1]` — check-before-insert handles duplicates. |
| `[1, -1], target = 0` | Returns `[0, 1]` — negative complements work. |
| Very large `target` causing overflow | `complement = target - nums[i]` can overflow if both are near Integer extremes. For LeetCode constraints (10⁹), within int range. For safety, use `long complement = (long)target - nums[i]`. |
| All distinct, no match | Loop completes, returns empty (problem guarantees one match). |
| `null` input | Problem guarantees non-null; defensive code can check. |
| `nums.length < 2` | Problem guarantees ≥ 2; defensive code can return early. |

### 3.A.9 Common Bugs [BOTH]

1. **Insert before check:** `seen.put(nums[i], i); if (seen.containsKey(complement)) ...` — fails on `[3], target=6` returning `[0,0]`.
2. **Return wrong order:** when the complement was the earlier element, the correct order is `[seen.get(complement), i]`. Swapping them is technically correct but inconsistent with most expected outputs.
3. **Integer overflow:** mostly irrelevant within LC constraints; consider `long` for general code.
4. **`nums[i] == complement` confusion:** when looking for two of the same value, the check-before-insert order is essential.
5. **Using `int[]` as map key:** doesn't work — `int[].hashCode()` is identity-based. Use `Integer` (autoboxed) or wrap.

### 3.A.10 Pattern Recognition [BOTH]

**Signal:** "find a pair / triple / quadruple of elements that sum to target" → hashmap of complements.

**Related problems:**

- LC 1 — Two Sum (this).
- LC 167 — Two Sum II (sorted) — use two pointers, O(1) extra space.
- LC 170 — Two Sum III (data structure design) — `add` and `find` API.
- LC 15 — 3Sum — fix one, two-pointer the rest after sort. (Day 7)
- LC 18 — 4Sum — fix two, two-pointer the rest.
- LC 560 — Subarray Sum Equals K — prefix sums + hashmap of complements.
- LC 454 — 4Sum II (across 4 arrays) — hashmap of pair sums.
- LC 1 vs LC 167: indices vs values → hashmap vs two-pointer.

### 3.A.11 Multi-Solution Comparison Table [BOTH]

| Approach | Time | Space | When to pick |
|---|---|---|---|
| Brute force (nested loop) | O(n²) | O(1) | n ≤ 1000 and code simplicity matters more than speed. |
| Sort + binary search | O(n log n) | O(n) | Memory-tight but you have time budget. |
| Sort + two pointers | O(n log n) | O(1) extra | When values are returned (not indices). |
| **Hashmap, one-pass** | **O(n)** | **O(n)** | Default optimal. Returns indices. |
| Hashmap, two-pass | O(n) | O(n) | Slightly more readable; less robust to duplicates. |

### 3.A.12 Follow-Up Questions [BOTH]

**Q1: What if the array is sorted?**
> Switch to two pointers — `left=0, right=n-1`. If `nums[left] + nums[right] < target`, increment left; if greater, decrement right; if equal, return. **O(n) time, O(1) space.** This is exactly Two Sum II.

**Q2: What if there can be multiple solutions and I need all of them?**
> Modify to not return early. Iterate, on each match append `(seen.get(complement), i)` to a result list. Be careful with duplicates: if `[3,2,3,4], target=6`, do you return `[0,2]` and `[2,0]`? Sort each pair or use a Set of canonical pairs.

**Q3: What if values are doubles, not ints?**
> The hashmap approach still works, but **double equality is fragile**. Use `BigDecimal` or scale by 10⁶ and use integer arithmetic. For approximate matches, bucket nearby values.

**Q4: What if the array doesn't fit in memory?**
> External sort (O(n log n) disk I/O) and use two pointers on the sorted file. Or partition by `hash(value) % R` across R machines; each machine processes its partition (joining `value` with `target - value` requires inter-machine shuffle).

**Q5: What if the array is a stream (no random access)?**
> Maintain a sliding-window hashmap (if "within last K elements") or process in batches. For unbounded streams looking for "any matching pair," a Bloom filter can approximate.

### 3.A.13 Scale-Up Addendum [STAFF]

**Stream variant.** For an infinite stream "report each Two Sum pair as you see them," maintain a hashmap of seen values → first index. Memory grows linearly with distinct values — bounded only by alphabet. For "within the last K elements," use a `LinkedHashMap` with eviction policy. For "approximate" answers on a stream with bounded memory, a **Bloom filter** says "complement might exist" with no false negatives but possible false positives — confirm with a slower path.

**Distributed variant.** Shard by `hash(value) % R` across R workers. For each `nums[i]`, the complement `target - nums[i]` may live on a different shard. Two patterns:

1. **Replicate the smaller dataset:** if one input is small, broadcast it to all workers ("map-side join").
2. **Shuffle by key:** each worker emits `(value, i)` and `(target - value, i)` keyed by hash; reducer joins.

This is the classic **hash join** pattern from databases. Two Sum at scale is literally a self-join on the array.

**Memory-bounded variant.** External hash join: split input into k partitions on disk; for each partition, build the hashmap and scan; merge results. O(n) disk I/O.

**Latency-bounded variant.** For interactive query at scale, pre-index the dataset. Build a `Map<value, List<index>>` once; queries are O(1).

### 3.A.14 Real-World Analogue [STAFF]

The Two Sum pattern is **the hash join algorithm** in database query execution. Postgres's `Hash Join` node:

1. Build a hash table on one input ("build side") — like our `seen` map.
2. Probe the other input ("probe side") and check the hash table — like our `containsKey` check.

For multi-key joins (`a.x = b.y AND a.p = b.q`), the hash key is a tuple. Postgres EXPLAIN ANALYZE will literally show "Hash Join" — when you see it, you're looking at Two Sum at scale.

Other instances:
- **Sales-data fraud detection:** "find two transactions in a 1-minute window that sum to a flagged amount."
- **Matchmaking systems:** "find two users whose Elo ratings sum to the target."
- **Network routing:** "find two AS paths whose latencies sum to ≤ budget."

### 3.A.15 Trade-Off Drill [STAFF]

**Q: Hashmap vs sort + two-pointer — when which?**
> Three axes: **memory pressure, output requirement, sorted-ness of input**.
> - Hashmap: O(n) time, O(n) space. Wins for indices and when memory is plentiful.
> - Sort + two-pointer: O(n log n) time, O(1) extra space, but **destroys position** — can only return values.
> - If the input is already sorted, two-pointer is O(n) — Hash and two-pointer tie on time, but two-pointer wins on space.
> Lean toward hashmap for Two Sum (indices). Lean toward two-pointer for 3Sum, 4Sum where positions don't matter and we already pay for the sort.

**Q: Bloom filter vs hashmap for "any pair" on a stream?**
> Three axes: **accuracy requirement, memory budget, false-positive tolerance**.
> - Hashmap: exact, O(distinct values) memory.
> - Bloom filter: approximate, O(1) memory after sizing, possible false positives ("complement might be present"), no false negatives.
> - If pair-existence is the answer (not the indices), Bloom is fine. If you need the actual pair, Bloom is a pre-filter before the slow path.

### 3.A.16 Junior vs Senior vs Staff Lens [BOTH]

**Junior says wrong:**
- Writes brute force, gets it working, calls it done.
- Inserts into the map before checking — fails on `[3], target=6`.
- Doesn't ask any clarifying questions before coding.
- Says "O(1)" for HashMap without distinguishing average vs worst.
- Uses `==` on boxed Integer in the hashmap lookup (works for cache range, fails for large values).

**Senior IC says right:**
- States approach before coding: "I'll use a hashmap; complement-pattern; O(n) time and space."
- Writes the one-pass version with check-before-insert.
- Names the trade-off: "Brute force is O(n²); I'm trading O(n) space for O(n) time."
- Verifies edge cases: duplicates, negative numbers.

**Staff candidate adds:**
- Connects to the broader pattern: "This is the hash join — same shape as database hash joins."
- Discusses scale-up unprompted: "At 10⁹ inputs you'd shard by hash and do a shuffle."
- Mentions related streaming algorithms (Bloom filter for memory-bound).
- Articulates the 3-axis trade-off when asked "why not sort?"
- Calls out the HashMap collision-DoS history as a relevant security note for adversarial inputs.

### 3.A.17 Interview Communication Script [BOTH]

Verbalize roughly like this:

> "Let me make sure I understand. We have an unsorted array of ints and a target sum. We want indices of two elements that sum to target. Exactly one solution; can't reuse the same index. Negative values OK, duplicates OK.
>
> Brute force is nested loops, O(n²) time, O(1) space — works for small n.
>
> For better, I'll use a hashmap. As I iterate, for each `nums[i]`, the complement is `target - nums[i]`. If the complement was seen before, we have our pair. Otherwise, record this index.
>
> Crucially, I check **before** inserting — that way `[3, 3], target = 6` finds the pair at iteration 1, not erroneously at iteration 0.
>
> Time O(n), space O(n). Let me code it.
>
> [writes code]
>
> Let me trace on `[2, 7, 11, 15], target = 9`: i=0, complement=7, not seen, put 2→0. i=1, complement=2, seen at index 0, return `[0, 1]`. Correct.
>
> Edge cases: duplicates handled by check-before-insert order; negatives work because the algorithm doesn't care about sign; overflow is possible for adversarial inputs near `Integer.MIN/MAX` so I'd use `long` for the complement in production code.
>
> Anything else you'd like me to optimize? If memory is tight, I can switch to sort + two-pointer at O(n log n) time, O(1) space, but I'd lose original indices."

---

<a id="problem-anagram"></a>
## § 3.B — Problem: Valid Anagram

### 3.B.1 Problem Statement [BOTH]

Given two strings `s` and `t`, return true if `t` is an anagram of `s`. An anagram is a rearrangement using exactly the same letters in the same counts.

- **LeetCode:** https://leetcode.com/problems/valid-anagram/ (LC 242)
- **NeetCode:** https://neetcode.io/problems/is-anagram
- **Frequency:** common warmup at Amazon, Microsoft, Google, Bloomberg.
- **Difficulty:** Easy.

### 3.B.2 Clarifying Questions [BOTH]

1. **"Case sensitive?"** Usually yes. Confirm.
2. **"What's the alphabet?"** ASCII lowercase? Full Unicode? This determines the data structure.
3. **"Are whitespace and punctuation significant?"** Usually yes. Clarify.
4. **"Can the strings be empty?"** Two empty strings → trivially anagrams (true).
5. **"Different lengths?"** Different lengths → not anagrams; can shortcut.

### 3.B.3 Brute Force [BOTH]

```java
public boolean isAnagramBrute(String s, String t) {
    if (s.length() != t.length()) return false;
    List<Character> tChars = new ArrayList<>();
    for (char c : t.toCharArray()) tChars.add(c);
    for (char c : s.toCharArray()) {
        int idx = tChars.indexOf(c);
        if (idx == -1) return false;
        tChars.remove(idx);
    }
    return tChars.isEmpty();
}
```

- **Time:** O(n²) — `indexOf` and `remove` are both O(n).
- **Space:** O(n) — the ArrayList copy.
- **Why suboptimal:** quadratic. Fine for tiny strings, fails at scale.

### 3.B.4 Intermediate Improvements [BOTH]

**Sort both, compare:**

```java
public boolean isAnagramSort(String s, String t) {
    if (s.length() != t.length()) return false;
    char[] a = s.toCharArray();
    char[] b = t.toCharArray();
    Arrays.sort(a);
    Arrays.sort(b);
    return Arrays.equals(a, b);
}
```

- **Time:** O(n log n).
- **Space:** O(n) for the char arrays.
- **Wins:** simple, alphabet-agnostic.

### 3.B.5 Optimal Solution(s) [BOTH]

#### Optimal 1 — Frequency count (fixed-alphabet O(n))

```java
public boolean isAnagram(String s, String t) {
    if (s.length() != t.length()) return false;
    int[] count = new int[26];                   // ASCII lowercase
    for (int i = 0; i < s.length(); i++) {
        count[s.charAt(i) - 'a']++;
        count[t.charAt(i) - 'a']--;
    }
    for (int c : count) if (c != 0) return false;
    return true;
}
```

Increment for `s`, decrement for `t`. If they're anagrams, all counters return to zero. Single pass.

#### Optimal 2 — HashMap counter (for arbitrary alphabets / Unicode)

```java
public boolean isAnagramUnicode(String s, String t) {
    if (s.length() != t.length()) return false;
    Map<Integer, Integer> count = new HashMap<>();
    s.codePoints().forEach(cp -> count.merge(cp, 1, Integer::sum));
    t.codePoints().forEach(cp -> count.merge(cp, -1, Integer::sum));
    return count.values().stream().allMatch(v -> v == 0);
}
```

`codePoints()` handles supplementary characters (emoji, rare CJK) that `char` (16-bit) can't.

### 3.B.6 Worked Trace [BOTH]

Input: `s = "anagram", t = "nagaram"`.

Initial count array (positions a, b, ..., z, all zero).

| i | s.charAt(i) | t.charAt(i) | Update | a | g | m | n | r |
|---|---|---|---|---|---|---|---|---|
| 0 | a | n | +a, -n | 1 | 0 | 0 | -1 | 0 |
| 1 | n | a | +n, -a | 0 | 0 | 0 | 0 | 0 |
| 2 | a | g | +a, -g | 1 | -1 | 0 | 0 | 0 |
| 3 | g | a | +g, -a | 0 | 0 | 0 | 0 | 0 |
| 4 | r | r | +r, -r | 0 | 0 | 0 | 0 | 0 |
| 5 | a | a | +a, -a | 0 | 0 | 0 | 0 | 0 |
| 6 | m | m | +m, -m | 0 | 0 | 0 | 0 | 0 |

Final: all zeros → true.

### 3.B.7 Complexity Analysis [BOTH]

- **Time: O(n)** — single pass through both strings.
- **Space: O(1)** for the fixed-26 case (constant alphabet); O(k) for the HashMap variant where k is distinct characters.
- For Unicode, "constant alphabet" is technically 1,114,112 code points — but for most strings k « 1M, so we report O(k).

### 3.B.8 Edge Cases [BOTH]

| Case | Behaviour |
|---|---|
| `"" vs ""` | length match, empty count → true. |
| Different lengths | Early return false. |
| `"aa" vs "ab"` | counts: a→1, b→-1 → return false. |
| Unicode `"café"` | `char[]` approach fails on combining accents; use code points + normalization (NFC). |
| Emoji or supplementary characters | `char` is 16-bit and can't represent code points > 0xFFFF; use `codePoints()`. |
| Case sensitivity | `"Listen" vs "Silent"` → false unless normalized to lowercase. |
| Whitespace differences | `"a b" vs "ab"` → false unless whitespace stripped. |

### 3.B.9 Common Bugs [BOTH]

1. **Skip length check** → an O(n) algorithm runs to completion only to return false.
2. **`char[26]` for uppercase too** → array overflow or wrong index. Sanitize input.
3. **Forgetting Unicode normalization** → `"café"` in NFC vs NFD have different code points.
4. **Mutating the input string** — Strings are immutable in Java, but `toCharArray()` returns a copy you might assume is shared.
5. **Index arithmetic with non-lowercase** — `'A' - 'a'` is negative; array index out of bounds.

### 3.B.10 Pattern Recognition [BOTH]

**Signal:** "do two collections have the same multiset of elements?" → frequency count.

**Related problems:**

- LC 49 — Group Anagrams (Day 2) — frequency-count signature as map key.
- LC 438 — Find All Anagrams in a String — sliding window + frequency count.
- LC 567 — Permutation in String — sliding window + frequency count.
- LC 383 — Ransom Note — sub-multiset check.
- LC 1002 — Find Common Characters — multi-string frequency intersection.

### 3.B.11 Multi-Solution Comparison Table [BOTH]

| Approach | Time | Space | When |
|---|---|---|---|
| Brute force (remove-by-search) | O(n²) | O(n) | Never. |
| Sort + compare | O(n log n) | O(n) | Alphabet-agnostic, simple. |
| Frequency count (int[26]) | O(n) | O(1) | Fixed small alphabet. |
| Frequency count (HashMap) | O(n) | O(k) | Arbitrary alphabet / Unicode. |

### 3.B.12 Follow-Up Questions [BOTH]

**Q1: What if the input is Unicode?**
> Use `codePoints()` to handle surrogate pairs. Normalize via `Normalizer.normalize(s, Form.NFC)` to canonicalize composed characters.

**Q2: What if you need to compare many strings for anagram-equivalence?**
> Precompute a canonical signature per string (sorted, or count-based) and put into a `Map<Signature, List<String>>`. That's exactly Group Anagrams, Day 2.

**Q3: How would you check "is t an anagram of any substring of s"?**
> Sliding window of size t.length() over s, maintain a frequency count, compare after each shift. O(n) time. LC 438.

**Q4: What if we want to detect anagrams ignoring whitespace and case?**
> Normalize first: `s.toLowerCase().replaceAll("\\s", "")`. Then standard frequency count.

**Q5: How would you parallelize for very long strings?**
> Split into chunks, count per chunk, sum the count vectors. Communicative + associative aggregation → trivially parallelizable.

### 3.B.13 Scale-Up Addendum [STAFF]

**Stream variant.** Maintain a running frequency count as characters arrive. The "is this stream so far an anagram of T?" check is O(1) after each arrival if you maintain a `mismatchCount` (how many characters have non-zero net diff).

**Distributed variant.** Split both strings across workers. Each worker counts its chunk. Reducer sums count vectors. Trivially parallelizable. (This is the canonical map-reduce shape — word count for strings.)

**Memory-bounded variant.** Already O(1) or O(k) — well within reach for any realistic alphabet. For pathological inputs (billions of distinct Unicode code points), a Count-Min Sketch could approximate the counts in sub-linear space, but in practice this is never needed.

### 3.B.14 Real-World Analogue [STAFF]

- **Database equality checks across denormalized data:** "are these two JSON blobs equivalent ignoring key order?" — sort keys (analogous to sorting the characters) then compare.
- **Cryptographic permutation tests:** "is this output a permutation of these inputs?" — count-based check.
- **Email spam detection:** Bayesian classifiers use word-frequency vectors per document; anagram-like signature matching is a primitive.
- **DNA sequence analysis:** k-mer frequency profiles are a real-world descendant of frequency-count anagram checks.

### 3.B.15 Trade-Off Drill [STAFF]

**Q: Sort vs frequency count — when which?**
> Three axes: **alphabet size, memory pressure, code clarity**.
> - Sort: O(n log n) time, O(n) space (for char array copy), alphabet-agnostic, **one-line conceptually clear**.
> - Frequency count: O(n) time, O(1)-O(k) space.
> - For small fixed alphabet, frequency count wins on both axes.
> - For arbitrary Unicode strings where k can be large, sort and count are roughly equivalent on space; sort wins on simplicity.
> - **Default: lead with frequency count for the canonical lowercase case, switch to sort if alphabet is unbounded or you're under time pressure.**

**Q: HashMap counter vs `int[26]`?**
> Three axes: **alphabet bound, allocation cost, code generality**.
> - `int[26]`: zero per-element allocation cost (primitive array), cache-friendly.
> - HashMap: boxed Integer values, ~32 bytes per distinct char.
> - For ASCII lowercase: `int[26]` wins by 10-20× on real-world wall time.
> - For arbitrary keys: HashMap is the only choice.

### 3.B.16 Junior vs Senior vs Staff Lens [BOTH]

**Junior says wrong:**
- Sorts both, calls it done — misses the O(n) trade.
- Uses `int[26]` without asking about alphabet → wrong on Unicode.
- Skips the length check → does extra work.

**Senior IC says right:**
- Asks clarifying question about alphabet.
- Names both approaches (sort vs count) and picks based on the answer.
- Implements with length-check short-circuit.

**Staff candidate adds:**
- Mentions Unicode normalization (NFC vs NFD) for "café" issue.
- Connects to Group Anagrams (canonical-form signature for hashing).
- Discusses parallelism for huge strings (chunked frequency counting).

### 3.B.17 Interview Communication Script [BOTH]

> "Quick clarification — case-sensitive? Whitespace significant? Alphabet? Lowercase ASCII. Got it.
>
> Brute force: for each char in s, find and remove from t. O(n²).
>
> Better: sort both, compare. O(n log n).
>
> Best: frequency count. Increment a count[26] for each char in s, decrement for each char in t. If they're anagrams, all counters return to zero. O(n) time, O(1) space.
>
> [code]
>
> Trace on `anagram`, `nagaram`: every counter zeroes out → true. Edge case `"a"` vs `"b"`: a:1, b:-1 → return false. Length mismatch shortcut prevents wasted work.
>
> If the alphabet were Unicode I'd switch to a HashMap keyed by code point, and possibly Normalizer.normalize to handle composed-vs-decomposed forms."

---

<a id="problem-duplicate"></a>
## § 3.C — Problem: Contains Duplicate

### 3.C.1 Problem Statement [BOTH]

Given an integer array `nums`, return true if any value appears at least twice.

- **LeetCode:** https://leetcode.com/problems/contains-duplicate/ (LC 217)
- **NeetCode:** https://neetcode.io/problems/duplicate-integer
- **Frequency:** the lightest warm-up problem at most companies; almost always followed by Two Sum or Group Anagrams in the same round.
- **Difficulty:** Easy.

### 3.C.2 Clarifying Questions [BOTH]

1. **"Empty array?"** Returns false (no duplicates possible).
2. **"Single element?"** Returns false.
3. **"Any value bounds?"** For LC: standard int range.
4. **"Can the array be modified?"** Often relevant for the sort-based approach.
5. **"Memory constraint?"** Determines sort vs HashSet choice.

### 3.C.3 Brute Force [BOTH]

```java
public boolean containsDuplicateBrute(int[] nums) {
    for (int i = 0; i < nums.length; i++) {
        for (int j = i + 1; j < nums.length; j++) {
            if (nums[i] == nums[j]) return true;
        }
    }
    return false;
}
```

- **Time:** O(n²). **Space:** O(1).
- **When acceptable:** n ≤ 1000 in non-hot code.

### 3.C.4 Intermediate Improvements [BOTH]

**Sort, scan adjacent:**

```java
public boolean containsDuplicateSort(int[] nums) {
    int[] copy = nums.clone();
    Arrays.sort(copy);
    for (int i = 1; i < copy.length; i++) {
        if (copy[i] == copy[i - 1]) return true;
    }
    return false;
}
```

- **Time:** O(n log n). **Space:** O(n) for the clone (O(log n) for in-place sort).
- **Wins:** O(1) auxiliary if input may be mutated.

### 3.C.5 Optimal Solution(s) [BOTH]

```java
public boolean containsDuplicate(int[] nums) {
    Set<Integer> seen = new HashSet<>();
    for (int n : nums) {
        if (!seen.add(n)) return true;
    }
    return false;
}
```

The idiom: `set.add(x)` returns `false` if `x` was already present. One operation does both "contains" and "add."

- **Time:** O(n) average. **Space:** O(n).

### 3.C.6 Worked Trace [BOTH]

Input: `nums = [1, 2, 3, 1]`.

| n | seen before? | add returns | seen after | Return? |
|---|---|---|---|---|
| 1 | No | true | {1} | continue |
| 2 | No | true | {1, 2} | continue |
| 3 | No | true | {1, 2, 3} | continue |
| 1 | **Yes** | false | — | **return true** |

### 3.C.7 Complexity Analysis [BOTH]

- **Time: O(n) average.** Each HashSet operation is O(1) average. Worst case O(n × log n) post-Java-8 due to treeified buckets, but in practice O(n).
- **Space: O(n).** The set holds up to n entries before a duplicate is found.

### 3.C.8 Edge Cases [BOTH]

| Case | Behaviour |
|---|---|
| Empty array | False (no duplicates possible). |
| Single element | False. |
| All distinct | False after full scan. |
| All identical | True on iteration 2. |
| Min/max values | HashSet handles fine; no overflow. |
| Very large n with all distinct | O(n) memory; consider sort if memory-tight. |

### 3.C.9 Common Bugs [BOTH]

1. **Using `contains` + `add` separately** — two map operations instead of one. Functionally correct but wasteful.
2. **Boxing every int** — unavoidable with `HashSet<Integer>`. For value-bounded ints, `BitSet` is faster.
3. **Off-by-one in sort variant** — `for (int i = 1; ...)` not `i = 0`.

### 3.C.10 Pattern Recognition [BOTH]

**Signal:** "membership check in a loop" → HashSet. The pattern is universal across:

- LC 217 — Contains Duplicate.
- LC 219 — Contains Duplicate II (within distance k).
- LC 220 — Contains Duplicate III (within distance k AND value diff ≤ t) — TreeSet.
- LC 1 — Two Sum (variant: complement set).
- LC 202 — Happy Number (cycle detection via Set).

### 3.C.11 Multi-Solution Comparison Table [BOTH]

| Approach | Time | Space | When |
|---|---|---|---|
| Brute force (nested loop) | O(n²) | O(1) | n ≤ 1000. |
| Sort + adjacent scan | O(n log n) | O(1) if mutable | Memory-tight. |
| HashSet | O(n) | O(n) | Default. |
| BitSet (for bounded values) | O(n) | O(M) bits | Values in known range. |

### 3.C.12 Follow-Up Questions [BOTH]

**Q1: What if values are bounded (e.g., 0 ≤ x ≤ 10⁶)?**
> Use `BitSet`. Each value indexes a bit. Set bit; if it was already set, return true. Memory: M/8 bytes where M = value range. Faster than HashSet for dense ranges.

**Q2: How would you detect duplicates with values within distance k?**
> LC 219. Sliding-window HashSet of size k. As you advance, remove the falling-out element.

**Q3: How would you detect approximate duplicates on a stream?**
> Bloom filter. Returns "definitely not seen" or "probably seen." Confirm with a slower path. Used in URL-deduplication for crawlers and email spam filters.

**Q4: How would you find ALL duplicates?**
> Continue the loop, accumulate into a result set. O(n) time, O(n) space.

**Q5: How would you count duplicates?**
> Replace HashSet with `Map<Integer, Integer>` frequency count. Return sum of `(count - 1)` for each entry with count > 1.

### 3.C.13 Scale-Up Addendum [STAFF]

**Stream variant.** Bloom filter for memory-bounded probabilistic duplicate detection. HyperLogLog if you want to count *distinct* values (different problem, related primitive).

**Distributed variant.** Hash-partition by value across R workers. Each worker maintains its own HashSet for its partition. Workers report duplicates locally. The merge is trivial (OR across workers).

**Memory-bounded variant.** Sort + adjacent scan is O(1) auxiliary (if input may be sorted in-place). External merge sort for inputs larger than memory.

### 3.C.14 Real-World Analogue [STAFF]

- **URL deduplication in web crawlers:** Bloom filter as a pre-filter, exact set for confirmation. Google's crawler.
- **Email spam fingerprinting:** Bloom filters to check "have I seen this email signature?"
- **Database primary key constraint enforcement:** insert into a unique index → conceptually "contains duplicate" check at every write.
- **Idempotency key checks in distributed systems:** Project 2 Day 54 will literally use this pattern — "have I seen this idempotency key?" The set is backed by Postgres unique constraint or DDB conditional write.

### 3.C.15 Trade-Off Drill [STAFF]

**Q: HashSet vs BitSet vs sort?**
> Three axes: **value range, mutability of input, latency requirement**.
> - HashSet: general-purpose, O(n) time and space.
> - BitSet: requires bounded values; 10× faster than HashSet for dense integer ranges; cache-friendly.
> - Sort: O(n log n) but O(1) extra if in-place. Wins on memory.
> Lean toward HashSet for default; BitSet when you've measured the gain and value range is bounded.

**Q: Exact duplicate detection vs Bloom filter on a stream?**
> Three axes: **accuracy, memory budget, downstream cost of false positive**.
> - Exact (HashSet/database): grows with distinct values; reliable.
> - Bloom: bounded memory; false positives possible.
> - If downstream confirmation is cheap (DB lookup), Bloom + confirm is the right combo. If confirmation is expensive, go exact.

### 3.C.16 Junior vs Senior vs Staff Lens [BOTH]

**Junior says wrong:**
- Writes nested-loop brute force.
- Uses `seen.contains(n)` then `seen.add(n)` — two operations instead of one.

**Senior IC says right:**
- Uses `set.add(n)` returning false on dup.
- States complexity correctly with average/worst distinction.

**Staff candidate adds:**
- Suggests BitSet for bounded ranges.
- Mentions Bloom filter for streams.
- Connects to real-world: URL dedup, idempotency keys in distributed systems.

### 3.C.17 Interview Communication Script [BOTH]

> "Duplicate detection — classic HashSet pattern. As I iterate, `set.add(n)` returns false if `n` was already present. That gives me the answer in one operation per element.
>
> O(n) average time, O(n) space.
>
> Edge cases: empty array → false (loop doesn't execute). All distinct → false after full scan. Two identical values → true on the second occurrence.
>
> Alternatives: sort + scan adjacent (O(n log n), O(1) aux); or BitSet if values are in a known range (cache-friendly, smaller memory). Bloom filter if this were a memory-bounded stream.
>
> Default: HashSet."

---

<a id="cross-ref"></a>
## § 6. Cross-References

### 6.1 Callbacks to Prior Days [BOTH]

None — Day 1 is the start of the plan.

### 6.2 Foreshadow Forward Days [BOTH]

| Concept introduced today | Where it's used |
|---|---|
| Hashmap complement pattern (Two Sum) | Day 2: Group Anagrams (canonical-form key); Day 7: 3Sum (extension); Day 41+: Subarray Sum Equals K (prefix-sum complement) |
| Frequency count (Anagram) | Day 2: Top K Frequent (frequency map); Day 56: Trie (per-node count); LC 438/567 sliding-window variants |
| HashSet dedup (Contains Duplicate) | Day 2: Group Anagrams (uses HashMap, same hashing); Day 26: Linked-list cycle detection (alternative to Floyd's); Day 54: Idempotency keys in Project 2 |
| Big O analysis | Every day. Explicit second pass Day 7 (CTCI Big O re-read) |
| HashMap internals (preview) | Day 2: `equals/hashCode` contract; Day 80: L1/L2 cache + locking; Day 87: DDIA Ch 5 replication (consistent hashing relies on hash distribution) |
| Java Collections complexity | Every DSA/JSD day |
| `PriorityQueue` semantics | Day 46: Heap problems; Day 47: cache eviction (LFU); Day 116: distributed cache HLD |

### 6.3 Project Integration Map [BOTH]

| Project | Day | How today's content lands |
|---|---|---|
| Project 1 (URL Shortener) | Day 24 onward | Lambda handler uses HashMap for in-memory caching; rate-limit token bucket uses ConcurrentHashMap (Day 39). |
| Project 2 (Event Pipeline) | Day 44 onward | Idempotency check (Day 54) literally uses HashSet pattern from Contains Duplicate. Consumer service uses HashMap throughout. |
| Project 3 (Multi-region) | Day 89 onward | Feature flag service uses ConcurrentHashMap. Atomic snapshot reload pattern. |

---

<a id="cheatsheet"></a>
## § 7. Cheatsheet

### Big O reference (one card)

```
O(1) < O(log n) < O(√n) < O(n) < O(n log n) < O(n²) < O(2ⁿ) < O(n!)
```

| n up to | Acceptable |
|---|---|
| 10 | O(n!) |
| 25 | O(2ⁿ) |
| 1k | O(n²) |
| 10⁵ | O(n log n) |
| 10⁶ | O(n) |
| 10⁹ | O(log n) / O(1) |

### Collections decision tree

```
Index access, mostly reads ........ ArrayList
Stack / Queue / Deque ............. ArrayDeque
Min/Max repeatedly ................ PriorityQueue
Key→Value, no order ............... HashMap
Key→Value, insertion order ........ LinkedHashMap
Key→Value, sorted by key .......... TreeMap
Set membership, no order .......... HashSet
Set membership, sorted ............ TreeSet
Concurrent map .................... ConcurrentHashMap
```

### Pattern → recipe

| Signal | Pattern |
|---|---|
| Find pair sums to target | Hashmap of complements (Two Sum) |
| Compare multisets | Frequency count (Valid Anagram) |
| Dup detection | HashSet + add() returns false (Contains Duplicate) |
| Group by canonical form | `Map<Signature, List<T>>` + computeIfAbsent (Day 2 preview) |
| Top K | Heap or bucket sort (Day 2 preview) |

### Idioms

```java
// Frequency count
map.merge(key, 1, Integer::sum);

// Group-by
map.computeIfAbsent(key, k -> new ArrayList<>()).add(value);

// Dedup
if (!set.add(x)) { /* duplicate */ }

// Safe int comparator
new PriorityQueue<int[]>((a, b) -> Integer.compare(a[0], b[0]));

// Length-prefix framing (Day 4 preview)
String framed = s.length() + "#" + s;
```

### Trade-off articulation [STAFF]

The 3-axis template:

> "There are three things I'd think about: [X], [Y], [Z]. If we're optimizing for X, then A. If Y, then B. In this case I'd lean toward C because [reason] — but I'd validate with [measurement / load test]."

---

<a id="self-assess"></a>
## § 8. Self-Assessment Checklist

### Mechanical fluency

- [ ] Two Sum solved from scratch in ≤ 5 minutes.
- [ ] Valid Anagram solved from scratch in ≤ 5 minutes.
- [ ] Contains Duplicate solved from scratch in ≤ 3 minutes.
- [ ] Can hand-trace any of the three on a small example.

### Knowledge

- [ ] Can explain Big O on a whiteboard with growth ordering and n-table.
- [ ] Can derive `ArrayList.add` amortized O(1) using the doubling argument.
- [ ] Can recite the Collections complexity table without looking.
- [ ] Can explain why HashMap capacity is a power of 2 (mask vs modulo).
- [ ] Can explain the hash spread function and why XOR high bits.
- [ ] Can explain bucket treeification (≥ 8 entries AND cap ≥ 64).
- [ ] Can pick HashMap vs LinkedHashMap vs TreeMap with justification.

### Trade-off articulation (verbalize each) [STAFF]

- [ ] Two Sum: hashmap vs sort+two-pointer (3-axis).
- [ ] Valid Anagram: sort vs frequency count (3-axis).
- [ ] Contains Duplicate: HashSet vs BitSet vs sort (3-axis).
- [ ] HashMap vs ConcurrentHashMap (3-axis).
- [ ] ArrayList vs LinkedList (why ArrayList wins in 2026).

### Behavioral

- [ ] Tracker started (`progress.md` initialized).
- [ ] Running totals on Day 1 — DSA problems solved: 3 / target 160.
- [ ] STAR stories drafted today: 0 / target 20.

### Confidence ratings (1–5)

- Big O: __
- Collections complexity table: __
- HashMap internals (hash, resize, treeify): __
- HashSet/HashMap distinction: __
- PriorityQueue semantics: __
- Two Sum from scratch: __
- Valid Anagram from scratch: __
- Contains Duplicate from scratch: __

---

<a id="glossary"></a>
## § 9. Glossary

- **Amortized analysis:** averaging cost over a sequence of operations; lets us call `ArrayList.add` "O(1) amortized" despite occasional O(n) resize.
- **Big Θ (theta):** tight asymptotic bound — function grows exactly this fast, sandwiched between two constant multiples of the bound.
- **Big Ω (omega):** asymptotic lower bound — function grows at least this fast.
- **Big O:** asymptotic upper bound — function grows at most this fast (ignoring constants).
- **Bloom filter:** probabilistic set with no false negatives but possible false positives; fixed memory regardless of cardinality.
- **Bucket sort:** O(n) sorting when input distributes uniformly into a bounded number of buckets.
- **Cache locality:** the property of accessing memory in a contiguous pattern that hits CPU cache lines; explains why ArrayList beats LinkedList in practice.
- **CAS:** Compare-And-Swap, an atomic CPU primitive used by ConcurrentHashMap for lock-free updates.
- **Comparison sort:** sorting algorithm that only inspects element ordering via comparisons; lower bound Ω(n log n).
- **Complement pattern:** "for each element, ask if its complement was seen before" — Two Sum and family.
- **Count-Min Sketch:** sub-linear-space probabilistic frequency estimator (used in trending-topic systems).
- **DoS (Denial of Service):** attack where adversarial input causes a system to consume disproportionate resources; the 2011 HashMap collision attack is a classic example.
- **Erasure (type erasure):** Java's generic types are erased to their bound at runtime; `List<Integer>` and `List<String>` share a Class object.
- **Fail-fast iterator:** detects structural modification during iteration and throws ConcurrentModificationException; best-effort, not a thread-safety guarantee.
- **Hash join:** database operation analogous to Two Sum at scale — build a hash table on one input, probe with the other.
- **HashSet:** Set implementation backed by a HashMap with sentinel values; O(1) average membership.
- **HashMap:** Map implementation backed by an array of buckets with linked-list / red-black-tree chaining; O(1) average put/get, O(log n) worst (post-Java-8).
- **HyperLogLog:** sub-linear-space cardinality (distinct count) estimator.
- **JCF:** Java Collections Framework (Java 1.2, 1998).
- **Load factor:** ratio of size to capacity that triggers HashMap resize (default 0.75).
- **Master theorem:** formula for solving divide-and-conquer recurrences of the form T(n) = aT(n/b) + f(n).
- **Modulo (`& (cap-1)`):** bitwise mask that computes index when capacity is a power of 2; faster than `% cap`.
- **Power-of-2 capacity:** HashMap design choice enabling the mask trick above.
- **Spread function:** HashMap's `(h ^ (h >>> 16))` mixing of high bits into low bits to reduce bucket collisions.
- **TimSort:** stable hybrid sort (merge sort + insertion sort) used by `Arrays.sort(Object[])` and `List.sort`.
- **Treeification:** HashMap's conversion of a linked-list bucket to a red-black tree when bucket size reaches 8 and capacity ≥ 64 (JEP 180).

---

<a id="references"></a>
## § 10. References

### Big O

- CTCI Ch VI (book — Cracking the Coding Interview)
- Abdul Bari Big O — https://www.youtube.com/watch?v=A03oI0znAoc
- Big-O cheatsheet — https://www.bigocheatsheet.com/
- CLRS Ch 3 (Asymptotic Notation), Ch 17 (Amortized Analysis), Ch 4 (Master Theorem)
- Knuth 1976 "Big Omicron and Big Omega and Big Theta" — historical
- Cloudflare 2019 outage postmortem (regex CPU exhaustion) — https://blog.cloudflare.com/details-of-the-cloudflare-outage-on-july-2-2019/

### Java Collections internals

- Oracle Collections tutorial — https://docs.oracle.com/javase/tutorial/collections/
- HashMap Javadoc (Java 21) — https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/util/HashMap.html
- ConcurrentHashMap Javadoc (Java 21) — https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/util/concurrent/ConcurrentHashMap.html
- JEP 180 (HashMap treeification) — https://openjdk.org/jeps/180
- Baeldung Java Collections — https://www.baeldung.com/java-collections
- *Effective Java* (Bloch) Items 17, 28–34
- *Java Concurrency in Practice* (Goetz) Ch 5 (Building Blocks)
- *Java Performance* (Oaks) Ch 12 (Collections Performance)
- 2011 HashMap DoS advisory — https://www.ocert.org/advisories/ocert-2011-003.html

### Problems

- LC 1 Two Sum — https://leetcode.com/problems/two-sum/
- LC 242 Valid Anagram — https://leetcode.com/problems/valid-anagram/
- LC 217 Contains Duplicate — https://leetcode.com/problems/contains-duplicate/
- NeetCode Roadmap — https://neetcode.io/roadmap

### Real-world & engineering context [STAFF]

- Stripe idempotency keys — https://stripe.com/blog/idempotency
- Knight Capital incident (2012) — https://en.wikipedia.org/wiki/Knight_Capital_Group#2012_stock_trading_disruption
- Apple goto-fail (2014) — https://en.wikipedia.org/wiki/SSL/TLS_implementation_flaws#Apple_goto_fail
- Postgres EXPLAIN (Hash Join reference) — https://www.postgresql.org/docs/current/using-explain.html

---

**End of Day 1.**

**Senior IC coverage:** Day 1 fully equips a Senior IC candidate: Big O fluency at interview depth, three canonical hashmap-pattern problems solved with brute-force progression and edge-case discussion, and a complete Java Collections complexity table. Read tier `[BOTH]` and `[SENIOR IC]` sections; the `[STAFF]` extensions are optional.

**Staff / Tech Lead coverage:** Day 1 also delivers the Staff-bar extensions: HashMap internals (hash spread, resize doubling trick, treeification), amortized analysis with three accounting techniques, real-world failure case studies (Cloudflare regex DoS, HashMap collision DoS), and a 3-axis trade-off drill on every problem. Connection to database hash joins, streaming variants (Bloom, HyperLogLog), and distributed shape (hash-partition shuffle) are surfaced where natural.

**Suggested target reading time:**
- Senior IC track: ~3 hours.
- Staff track: ~5 hours (read the [STAFF] sections in addition).

**Anything deferred:** `equals/hashCode` contract gets its full treatment Day 2 (it's the dedicated topic there). PECS / generics deferred to Day 3. JVM bytecode / JIT escape analysis touched only in Big O constants discussion — deeper JVM internals appear Day 36 (concurrency primitives) and Day 76 (JVM memory model).
