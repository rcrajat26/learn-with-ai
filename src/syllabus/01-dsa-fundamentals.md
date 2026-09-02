# Syllabus — 01 DSA Fundamentals

**Target version: Java 21 LTS** for every API, constant and library-implementation claim. Java 22–25
deltas are marked inline with their version (Java 25 became the next LTS on 2025-09-16). Claims that
are widely repeated but version-stale or notation-stale are marked `[VERSION-TRAP]`.

Scope note: this is the *algorithms and data structures* bible. Where a structure's Java library
implementation is the subject, guide 02 owns the source walk and this file owns the algorithmic
model — those leaves carry `[X-REF 02]` and the bible states the mechanism in a paragraph before
pointing across.

Tag legend:

| Tag | Meaning for the write pass |
|---|---|
| `[PROVE]` | the bible must work the argument through, not state the result |
| `[SOURCE]` | must quote real source (JDK, a paper, or a spec) and explain every line |
| `[BUILD]` | must ship complete, compiling, generic Java 21 code |
| `[TRAP]` | must carry a `**Trap:**` marker — wrong belief, symptom, fix |
| `[RESEARCH]` | leaf exists because of the research phase; re-verify against the cited source before writing |
| `[VERSION-TRAP]` | widely-repeated claim that is stale; state what is true now and what used to be true |
| `[X-REF nn]` | one-paragraph mechanism here, full treatment in guide nn |
| `[NUM]` | must state the number / byte arithmetic / recurrence explicitly |
| `[DRILL]` | must ship a self-test the reader can run without looking at the answer |

---

# PART 1 — BASICS

## §1.1 Why complexity analysis exists at all

1.1.1 The question analysis answers: not "how fast is this program" but "how does the cost of this
      procedure change when the input grows", which is the only question whose answer survives a
      hardware change.
1.1.2 Wall-clock timing as the naive alternative, and the four things that make it non-portable:
      CPU, compiler, JIT warm-up, and input instance.
1.1.3 What the abstraction buys: you can rank two algorithms before writing either one.
1.1.4 What the abstraction costs: constants and lower-order terms are discarded, so a "worse" class
      can win at real sizes. `[TRAP]`
1.1.5 The three quantities always in play: time, auxiliary space, and number of a distinguished
      expensive operation (comparisons, swaps, I/O, network calls).
1.1.6 Why interviews test this: the ability to reject an approach before implementing it is the
      actual on-the-job skill being probed.
1.1.7 The historical arc: Knuth's *TAOCP* analytical framing → Aho/Hopcroft/Ullman → CLRS as the
      canonical curriculum. `[RESEARCH]`
1.1.8 Where the notation came from: Bachmann/Landau in analytic number theory; Knuth's 1976 note
      imported O/Ω/Θ into computer science. `[RESEARCH]`
1.1.9 Analysis is *not* benchmarking and benchmarking is *not* analysis — you need both, and each
      answers a question the other cannot.
1.1.10 The four inputs an algorithm question always hides: input size bound, value range, whether
       mutation is allowed, and whether the input is already ordered.

*(10 leaves)*

## §1.2 The machine model the analysis assumes

1.2.1 The RAM (random-access machine) model: unit-cost arithmetic, unit-cost memory access,
      unbounded but word-sized integers.
1.2.2 The word-RAM refinement: a word is `w` bits, `w ≥ log n`, so an index fits in a word — this is
      what makes "array index is O(1)" a definition, not a measurement. `[NUM]`
1.2.3 Where the model lies: memory access is not unit cost on real hardware (registers → L1 → L2 →
      L3 → DRAM), which is the entire explanation for array-vs-linked-list constant factors.
      `[X-REF 06]`
1.2.4 The external-memory / cache-oblivious model in one paragraph: cost counted in block transfers
      of size B, which is why B-trees exist and binary search trees do not run databases.
      `[X-REF 09]` `[RESEARCH]`
1.2.5 Unit-cost arithmetic on bignums is false — `BigInteger.multiply` is not O(1). `[TRAP]`
      `[X-REF 03]`
1.2.6 Model choice changes the answer: comparison model (Ω(n log n) sorting) vs word-RAM with
      integer keys (radix sort in O(nk)) — the lower bound is a property of the model, not of
      sorting. `[PROVE]`
1.2.7 The decision-tree model, defined: comparisons are the only inspection, leaves are outputs.
1.2.8 The cell-probe model in one line, for completeness, as the model in which most data-structure
      lower bounds are actually proved. `[RESEARCH]`
1.2.9 JVM-specific model corrections: bounds-checked array access, GC-managed allocation, safepoints,
      and JIT-inlined intrinsics. `[X-REF 06]`

*(9 leaves)*

## §1.3 Asymptotic notation, exactly

1.3.1 `O(g)` — upper bound: ∃c>0, n₀ such that f(n) ≤ c·g(n) for all n ≥ n₀. State the quantifiers.
      `[NUM]`
1.3.2 `Ω(g)` — lower bound: f(n) ≥ c·g(n) eventually.
1.3.3 `Θ(g)` — tight: both simultaneously.
1.3.4 `o(g)` (little-oh) — strictly smaller: f/g → 0. `ω(g)` — strictly larger.
1.3.5 The set-membership reading (`f ∈ O(g)`) vs the abuse-of-notation equals reading (`f = O(g)`),
      and why `O(n) = O(n²)` is meaningless while `O(n) ⊆ O(n²)` is true. `[TRAP]`
1.3.6 **Big-O is not worst case.** The notation bounds a *function*; which function (best, average,
      worst) is a separate choice. "O is worst case, Ω is best case, Θ is average" is the single most
      common misconception in the field. `[TRAP]` `[RESEARCH]` `[VERSION-TRAP]`
1.3.7 Consequence: it is correct and useful to say "insertion sort is Ω(n) in the best case" and
      "Θ(n²) in the worst case".
1.3.8 Why practitioners say O when they mean Θ, and when that sloppiness actually bites (claiming an
      O(n²) algorithm is "not O(n log n)" — it might be). `[TRAP]`
1.3.9 Tight vs loose bounds: every O(n) algorithm is also O(n³); a bound is a claim, tightness is a
      stronger claim.
1.3.10 Dropping constants and lower-order terms: 3n² + 5n + 7 ∈ Θ(n²) — prove it by exhibiting c and
       n₀. `[PROVE]` `[NUM]`
1.3.11 Multi-variable asymptotics: O(V+E), O(n·m), O(n·k) — and why you may not simplify O(V+E) to
       O(E) without stating the connectivity assumption. `[TRAP]`
1.3.12 Log bases are irrelevant to the class (log₂n = ln n / ln 2 is a constant factor) but *are*
       relevant to the constant. `[PROVE]`
1.3.13 `log(n!) = Θ(n log n)` via Stirling — the identity behind the sorting lower bound. `[PROVE]`
       `[NUM]`
1.3.14 The growth-rate ordering with proofs of the non-obvious pairs: 1 ≺ log log n ≺ log n ≺
       (log n)^k ≺ n^ε ≺ n ≺ n log n ≺ n² ≺ n³ ≺ 2ⁿ ≺ 3ⁿ ≺ n! ≺ nⁿ. `[PROVE]`
1.3.15 `n^(1/log n)`, `log*n` (iterated log), and `α(n)` (inverse Ackermann) — the three sub-log
       functions that show up in real bounds. `[NUM]`
1.3.16 Polynomial vs pseudo-polynomial vs exponential, defined by *bit length of the input*, not by
       the numeric value — the definition that makes knapsack "exponential". `[PROVE]` `[RESEARCH]`
1.3.17 Common algebra: sum rule (max dominates), product rule (nested loops multiply), transitivity,
       and why O(f) + O(g) = O(max(f,g)).
1.3.18 Amortized, average-case, expected, and worst-case are four different claims — the 4-way table
       with an example algorithm in each cell. `[TRAP]`
1.3.19 Expected vs average: randomization over the *algorithm's* coins (quicksort with random pivot)
       vs a distribution over *inputs* (average-case quicksort). `[PROVE]` `[TRAP]`
1.3.20 Smoothed analysis in one paragraph, as the modern answer to "why does simplex work".
       `[RESEARCH]`
1.3.21 Competitive ratio for online algorithms in one paragraph — the frame in which LRU and
       paging are analysed. `[X-REF 15]` `[RESEARCH]`
1.3.22 Galactic algorithms: bounds that win asymptotically and lose at every realizable n
       (Coppersmith–Winograd matrix multiply, Chazelle triangulation). `[RESEARCH]`
1.3.23 How to state a complexity in an interview: "time Θ(n log n), auxiliary space Θ(n), dominated
       by the sort" — the three-part sentence.

*(23 leaves)*

## §1.4 The growth ladder, with the n it implies

1.4.1 The class table: name, canonical source, an example algorithm, and the largest n that fits a
      1-second budget at ~10⁸ simple operations. `[NUM]`
1.4.2 O(1): array index, hash lookup, stack push, bit trick, arithmetic.
1.4.3 O(log n): binary search, balanced-tree descent, heap sift, binary lifting, `Integer`
      bit-length loops.
1.4.4 O(log log n): interpolation search on uniform data, van Emde Boas priority queue.
      `[RESEARCH]`
1.4.5 O(√n): trial division primality, sqrt decomposition, Mo's algorithm block size.
1.4.6 O(n): single scan, Kadane, counting sort (with k ≤ n), heapify, quickselect expected.
1.4.7 O(n log log n): sieve of Eratosthenes. `[NUM]` `[RESEARCH]`
1.4.8 O(n log n): comparison sort, sort-then-scan, divide-and-conquer merges, Dijkstra on sparse
      graphs with a binary heap.
1.4.9 O(n log² n) and O(n √n): the classes produced by nesting a log/sqrt structure inside a loop.
1.4.10 O(n²): all-pairs scan, insertion/selection/bubble sort, Floyd–Warshall on a small graph's
       inner two loops, simple DP over two indices.
1.4.11 O(n² log n) and O(n³): matrix multiply, Floyd–Warshall, interval DP.
1.4.12 O(n·2ⁿ) and O(2ⁿ): bitmask DP over subsets vs subset enumeration.
1.4.13 O(n!): permutation enumeration, brute-force TSP, N-queens without pruning.
1.4.14 O(nⁿ) and Ackermann-scale: where they come from and why you will never run one.
1.4.15 The n→algorithm-class inverse table: n ≤ 10 (n! / n·2ⁿ), n ≤ 20–25 (2ⁿ bitmask), n ≤ 100 (n³),
       n ≤ 1 000 (n²), n ≤ 10⁵ (n log n), n ≤ 10⁶–10⁷ (n), n ≥ 10⁹ (O(log n), math, or binary search
       on the answer). `[NUM]` `[DRILL]`
1.4.16 Reading the constraint block *first* — the constraints are the problem-setter telling you the
       intended complexity. `[TRAP]`
1.4.17 Value-range constraints (`0 ≤ a[i] ≤ 10⁴`) as the signal for counting sort, bucketing, or a
       frequency array instead of a map.
1.4.18 Sum-of-n constraints across test cases ("the sum of n over all queries ≤ 2·10⁵") and what they
       permit. `[RESEARCH]`
1.4.19 Practical JVM throughput numbers for sizing: ~10⁸–10⁹ simple int ops/sec, ~10⁷ HashMap ops/sec,
       ~10⁶ allocations/sec, and why boxed collections cost an order of magnitude. `[NUM]`
1.4.20 Latency ladder for context: L1 ~1 ns, L2 ~4 ns, L3 ~40 ns, DRAM ~100 ns, SSD ~100 µs,
       network RTT ~0.5 ms same-DC. `[NUM]` `[X-REF 10]`

*(20 leaves)*

## §1.5 Recurrences

1.5.1 Why recurrences: recursive algorithm cost is defined recursively, so the closed form must be
      derived, not read off.
1.5.2 Writing the recurrence from code: T(n) = (number of recursive calls)·T(subproblem size) +
      (non-recursive work).
1.5.3 The substitution method: guess the form, prove by induction, and where the induction fails if
      the guess is wrong. `[PROVE]`
1.5.4 The recursion-tree method: level count, per-level cost, geometric-series collapse. `[PROVE]`
1.5.5 The master theorem, all three cases, with `a`, `b`, `f(n)`, and the comparison against
      `n^(log_b a)`. `[NUM]` `[PROVE]`
1.5.6 The master theorem's regularity condition in case 3, and a concrete recurrence it excludes.
      `[TRAP]`
1.5.7 The gap cases the master theorem cannot handle (T(n) = 2T(n/2) + n/log n) and the
      Akra–Bazzi method that can. `[RESEARCH]`
1.5.8 CLRS 4th-edition "continuous master theorem" framing and the new material on solving
      recurrences. `[RESEARCH]`
1.5.9 T(n) = T(n−1) + O(1) → Θ(n): linear recursion (linked-list walk).
1.5.10 T(n) = T(n−1) + O(n) → Θ(n²): quicksort worst case, insertion-sort recursion. `[PROVE]`
1.5.11 T(n) = 2T(n−1) + O(1) → Θ(2ⁿ): subset enumeration, naive Fibonacci, Towers of Hanoi.
1.5.12 T(n) = T(n/2) + O(1) → Θ(log n): binary search. `[PROVE]`
1.5.13 T(n) = T(n/2) + O(n) → Θ(n): quickselect on a perfect pivot, "binary search that scans".
       `[PROVE]`
1.5.14 T(n) = 2T(n/2) + O(1) → Θ(n): tree traversal, heapify's shape.
1.5.15 T(n) = 2T(n/2) + O(n) → Θ(n log n): merge sort, the canonical divide-and-conquer.
1.5.16 T(n) = 2T(n/2) + O(n log n) → Θ(n log² n).
1.5.17 T(n) = 7T(n/2) + O(n²) → Θ(n^log₂7) = Θ(n^2.807): Strassen. `[NUM]`
1.5.18 T(n) = T(n/5) + T(7n/10) + O(n) → Θ(n): median of medians — why the fractions sum below 1.
       `[PROVE]`
1.5.19 T(n) = √n·T(√n) + O(n) and other unusual shapes worth recognising. `[RESEARCH]`
1.5.20 Fibonacci-shaped recurrences and the golden-ratio bound: naive fib is Θ(φⁿ) ≈ Θ(1.618ⁿ), not
       Θ(2ⁿ). `[PROVE]` `[TRAP]` `[NUM]`
1.5.21 The recurrence for the *space* of a recursive algorithm, which is the max depth, not the sum.
1.5.22 Generating-function and characteristic-root methods in one paragraph each, for linear
       recurrences with constant coefficients. `[RESEARCH]`
1.5.23 Matrix exponentiation as the O(log n) evaluator of any linear recurrence. `[BUILD]`
1.5.24 The recurrence cheat table: 12 shapes → closed forms, memorised. `[DRILL]`

*(24 leaves)*

## §1.6 Amortized analysis

1.6.1 The definition: the worst-case average over a *sequence* of operations, with no probability
      involved.
1.6.2 Amortized ≠ average-case: no distribution is assumed; the guarantee holds for any sequence.
      `[PROVE]` `[TRAP]`
1.6.3 Amortized ≠ "O(1) with a bad constant": a single operation genuinely can be Θ(n). `[TRAP]`
1.6.4 **Aggregate method**: total cost of n operations / n. `[PROVE]`
1.6.5 **Accounting (banker's) method**: prepaid credit stored on elements; the invariant "credit
      never goes negative" is the proof obligation. `[PROVE]`
1.6.6 **Potential (physicist's) method**: Φ maps a structure state to a number;
      ĉᵢ = cᵢ + Φ(Dᵢ) − Φ(Dᵢ₋₁); require Φ(Dₙ) ≥ Φ(D₀). `[PROVE]` `[NUM]` `[RESEARCH]`
1.6.7 All three applied to the same object — the dynamic table — so the reader sees they agree.
      `[PROVE]` `[RESEARCH]`
1.6.8 Amortized O(1) `ArrayList.add`: the doubling series n/2 + n/4 + … < n. `[PROVE]` `[NUM]`
      `[X-REF 02]`
1.6.9 Amortized O(1) two-stack queue: each element is moved between stacks at most once. `[PROVE]`
1.6.10 Amortized O(1) monotonic stack: each index is pushed once and popped once, so the inner
       `while` is not a multiplier. `[PROVE]`
1.6.11 Amortized O(1) hash-table insertion under resize doubling. `[PROVE]`
1.6.12 Amortized O(α(n)) union-find with path compression + union by rank. `[PROVE]`
1.6.13 Amortized O(1) incrementing a binary counter — the cleanest accounting-method example.
       `[PROVE]` `[NUM]`
1.6.14 Amortized O(log n) splay-tree operations via the potential method. `[RESEARCH]`
1.6.15 **You may not amortize across structures**, and clearing/refilling resets the analysis.
       `[TRAP]`
1.6.16 **You may not amortize when the adversary chooses the operation mix**: alternating
       `add`/`remove` at a resize boundary breaks a table that doubles at full and halves at half.
       The fix — hysteresis (grow at 1.0, shrink at 0.25). `[PROVE]` `[TRAP]` `[NUM]`
1.6.17 Amortization and tail latency: an amortized bound is worthless for a p99 SLO; pre-size, or
       use an incremental/de-amortized structure. `[TRAP]` `[X-REF 20]`
1.6.18 De-amortization in one paragraph: incremental rehashing, background resize, ConcurrentHashMap's
       cooperative transfer. `[X-REF 02]` `[RESEARCH]`

*(18 leaves)*

## §1.7 Space complexity

1.7.1 Input space vs auxiliary space vs total space, and which one the phrase "O(1) space" means.
      `[TRAP]`
1.7.2 The recursion stack counts: DFS on a skewed tree of n nodes is Θ(n) auxiliary space even with
      zero allocation. `[TRAP]`
1.7.3 Output space is conventionally excluded (generating all subsets is "O(n) space" despite 2ⁿ
      output). State the convention explicitly. `[TRAP]`
1.7.4 In-place, defined: O(1) auxiliary beyond the input, allowing O(log n) for recursion in the
      loose definition — and which definition each canonical algorithm satisfies.
1.7.5 The time–space trade-off as a design axis: memoization, prefix sums, precomputed tables,
      sparse tables, bitsets.
1.7.6 Space-optimizing DP: full table → two rows → one row; when the one-row form requires reversing
      the iteration direction. `[PROVE]`
1.7.7 Streaming/one-pass constraints: what you can compute in O(1) space over a stream (sum, max,
      Kadane, reservoir sample, majority) and what you cannot (median, exact distinct count).
      `[PROVE]`
1.7.8 Sublinear-space approximations: HyperLogLog, Count-Min Sketch, Bloom filter — one paragraph
      each, with their error parameters. `[X-REF 22]` `[RESEARCH]`
1.7.9 JVM footprint arithmetic for DSA: 12-byte object header + 4-byte compressed klass alignment,
      16-byte array header, 8-byte alignment, `Integer` = 16 B, `Long` = 24 B, a node with two
      references ≈ 32 B. `[NUM]` `[X-REF 06]` `[RESEARCH]`
1.7.10 `int[1_000_000]` = ~4 MB vs `Integer[1_000_000]` = ~4 MB of refs + 16 MB of boxes = ~20 MB.
       `[NUM]` `[PROVE]`
1.7.11 `boolean[]` is one byte per element; `BitSet` is one bit — 8× and 64× against
       `HashSet<Integer>`. `[NUM]` `[X-REF 02]`
1.7.12 Default JVM thread stack (~512 KB–1 MB) and the recursion depth it buys (~10⁴ frames), plus
       `-Xss` as the escape hatch. `[NUM]` `[X-REF 06]`

*(12 leaves)*

## §1.8 Arrays and dynamic arrays

1.8.1 Contiguity as the defining property; address arithmetic `base + i·elementSize` is why indexing
      is O(1). `[NUM]`
1.8.2 Row-major layout for 2-D arrays, and why `a[i][j]` loops beat `a[j][i]` loops on the same data.
      `[PROVE]` `[NUM]`
1.8.3 Java's `int[][]` is an array of references (jagged), not a contiguous 2-D block — the
      cache-locality consequence and the flat-array-with-index-math alternative. `[TRAP]`
1.8.4 Cache lines (typically 64 B = 16 ints) and hardware prefetch as the mechanism behind the
      "arrays crush linked lists at equal Big-O" claim. `[NUM]` `[X-REF 06]`
1.8.5 Fixed length: `array.length` is final; there is no resize.
1.8.6 Insert/delete in the middle is Θ(n) — the shift.
1.8.7 Delete-by-swap-with-last as the O(1) unordered removal, and what it costs (order).
1.8.8 The dynamic array (growable array): capacity vs size, the growth policy, `ensureCapacity`,
      `trimToSize`. `[X-REF 02]`
1.8.9 Growth factor choice: 2× vs 1.5× (Java's `ArrayList` uses 1.5×, `Vector` 2×) and the
      memory-reuse argument for 1.5×. `[NUM]` `[PROVE]` `[X-REF 02]`
1.8.10 Java array specifics: default initialization (0/false/null), bounds checking and
       `ArrayIndexOutOfBoundsException`, covariance and `ArrayStoreException`. `[X-REF 03]`
1.8.11 `System.arraycopy` / `Arrays.copyOf` as intrinsics, and why a hand-written copy loop is
       slower. `[SOURCE]`
1.8.12 `Arrays.fill`, `Arrays.setAll`, `Arrays.copyOfRange`, `Arrays.equals`, `Arrays.mismatch`,
       `Arrays.compare`, `Arrays.deepToString`, `Arrays.stream`, `Arrays.asList`. `[X-REF 02]`
1.8.13 `Arrays.toString` vs printing an array directly (identity hash garbage). `[TRAP]`
1.8.14 2-D array idioms: `new int[m][n]`, `new int[m][]`, `int[][] grid = {{…}}`,
       `Arrays.fill` on each row (`Arrays.fill(grid, row)` aliases one row into every slot). `[TRAP]`
1.8.15 Direction vectors `{{0,1},{1,0},{0,-1},{-1,0}}` and the 8-neighbour variant, as the standard
       grid-traversal idiom.
1.8.16 Coordinate flattening `id = r * cols + c` and the inverse, for union-find and visited sets on
       grids. `[NUM]`
1.8.17 Sentinels and padding rows as bounds-check elimination.
1.8.18 The techniques inventory this file must cover in full later: prefix sums, difference arrays,
       in-place reversal, cyclic rotation by three reversals, Dutch national flag, cyclic sort,
       index-as-hash, two pointers, sliding window, Kadane, Boyer–Moore majority.

*(18 leaves)*

## §1.9 Strings

1.9.1 A string as an immutable array of code units, and the four levels: byte, code unit, code point,
      grapheme cluster. `[X-REF 03]`
1.9.2 Java `String` internals: `byte[] value` + `byte coder`; compact strings (JEP 254, Java 9)
      store Latin-1 as 1 byte/char and everything else as UTF-16 2 bytes/char. `[NUM]` `[X-REF 03]`
1.9.3 `charAt` is O(1) on the code-unit index; `codePointAt` and surrogate pairs mean "the i-th
      character" is not `charAt(i)` for non-BMP text. `[TRAP]`
1.9.4 Immutability consequences: every concatenation allocates; `substring` since Java 7 copies
      (Θ(k)), and before Java 7 shared the array (Θ(1) but leak-prone). `[VERSION-TRAP]` `[NUM]`
1.9.5 **String building in a loop with `+` is Θ(n²)**; `StringBuilder` is amortized linear. The
      compiler fuses `+` within one expression only. `[TRAP]` `[PROVE]`
1.9.6 `StringBuilder` internals: `char[]`/`byte[]` with doubling-plus-2 growth, `setLength`,
      `deleteCharAt`, `insert`, `reverse`, `ensureCapacity`, and the `StringBuffer` synchronized
      twin. `[NUM]` `[X-REF 03]`
1.9.7 `String.hashCode` = `s[0]·31^(n−1) + … + s[n−1]`, cached in the `hash` field with a
      `hashIsZero` flag (Java 13+). `[SOURCE]` `[NUM]` `[X-REF 02]`
1.9.8 The interning pool and why `==` on strings sometimes works. `[TRAP]` `[X-REF 03]`
1.9.9 `char` arithmetic: `c - 'a'` for the 26-slot frequency array, `Character.isLetterOrDigit`,
      `Character.toLowerCase`, `Character.getNumericValue`, `Character.isEmoji` (Java 21).
      `[RESEARCH]`
1.9.10 `toCharArray` (copy) vs `charAt` in a loop (no copy) — the allocation trade-off.
1.9.11 Frequency representations: `int[26]`, `int[128]`, `HashMap<Character,Integer>`, and a 26-bit
       mask in a single `int`. When each is right. `[NUM]`
1.9.12 Canonical-key grouping: sorted characters, or a count signature, for anagram bucketing.
       `[PROVE]`
1.9.13 Palindrome checks: two pointers, expand-from-centre (2n−1 centres), and the DP table.
1.9.14 Subsequence vs substring vs subarray — the definitional distinction that changes the whole
       problem class. `[TRAP]`
1.9.15 `split`, `replaceAll`, `matches` are regex-backed and therefore not O(n); `String.split(" ")`
       vs `split("\\s+")` vs `StringTokenizer`. `[TRAP]`
1.9.16 Catastrophic regex backtracking (ReDoS): nested quantifiers `(a+)+`, the Stack Overflow 2016
       and Cloudflare 2019 outages, and the fixes (possessive quantifiers, atomic groups,
       de-ambiguation). `[TRAP]` `[RESEARCH]` `[X-REF 13]`
1.9.17 `String.join`, `String.repeat` (11), `String.strip` vs `trim` (11), `isBlank`, `lines`,
       `chars()`, `formatted` (15), text blocks (15). `[X-REF 04]`
1.9.18 `String.compareTo` is UTF-16 code-unit order, not locale order; `Collator` for human-visible
       sorting. `[TRAP]` `[X-REF 02]`
1.9.19 String algorithm inventory owed later: KMP, Z-function, Rabin–Karp rolling hash, Manacher,
       Aho–Corasick, suffix array, suffix automaton, Lyndon factorization. `[RESEARCH]`

*(19 leaves)*

## §1.10 Hashing

1.10.1 The mechanism: `index = hash(key) mod capacity`, then resolve collisions inside that bucket.
1.10.2 What a good hash function needs: uniformity, avalanche (one input bit flips ~half the output
       bits), speed, determinism, and consistency with equality.
1.10.3 The hard contract: **equal objects must have equal hash codes**; the converse need not hold.
       `[PROVE]` `[X-REF 02]`
1.10.4 Why the converse cannot hold: pigeonhole — an infinite key space into 2³² codes. `[PROVE]`
1.10.5 Expected O(1) under the simple uniform hashing assumption; the assumption is doing the work.
       `[PROVE]`
1.10.6 Worst case Θ(n) per operation when every key collides — and Θ(log n) in Java 8+ once a bin
       treeifies. `[X-REF 02]`
1.10.7 Load factor α = n/m; the expected chain length is α, which is why 0.75 is the default.
       `[NUM]` `[X-REF 02]`
1.10.8 Collision resolution families: separate chaining, open addressing (linear probing, quadratic
       probing, double hashing), Robin Hood hashing, cuckoo hashing, hopscotch hashing. `[RESEARCH]`
1.10.9 Power-of-two capacity + bit masking vs prime capacity + modulus — the two design schools and
       why Java picked masking plus a high-bit spread. `[PROVE]` `[X-REF 02]`
1.10.10 Multiplicative hashing, Fibonacci hashing (`⌊2⁶⁴/φ⌋`), and MurmurHash's finalizer as the
        practical avalanche functions. `[NUM]` `[RESEARCH]`
1.10.11 Universal hashing and 2-independent families — the theoretical answer to adversarial input.
        `[PROVE]` `[RESEARCH]`
1.10.12 Hash-flooding DoS: CVE-2011-4858 (Tomcat form parameters), VU#903934, the 28C3 disclosure;
        the O(n²) table-construction attack and the SipHash / random-seed mitigations. `[RESEARCH]`
        `[X-REF 13]`
1.10.13 **The mutable-key trap**: mutate a field used by `hashCode` after insertion and the entry is
        stranded — `get` returns null while iteration still shows it and memory still holds it.
        `[TRAP]` `[X-REF 02]`
1.10.14 Hash sets vs sorted structures: no ordering, no range queries, no predecessor/successor — the
        three capabilities you give up for O(1).
1.10.15 Hashing use inventory: frequency counting, seen-set dedup, complement lookup (two-sum),
        canonical-key grouping, index maps ("where did I last see this"), memo keys, visited sets,
        rolling-hash substring matching, consistent hashing. `[X-REF 22]`
1.10.16 Composite keys: a record, a `List`, `long` packing of two ints (`(long) a << 32 | (b &
        0xFFFFFFFFL)`), or string concatenation — and the correctness/perf ordering of the four.
        `[NUM]` `[TRAP]`
1.10.17 `Objects.hash(...)` allocates a varargs array; the `31 * h + f` loop does not. `[NUM]`
        `[X-REF 02]`
1.10.18 `HashMap` sizing to avoid resize: `new HashMap<>((int)(n / 0.75f) + 1)` or Java 19+
        `HashMap.newHashMap(n)`. `[NUM]` `[TRAP]` `[X-REF 02]`
1.10.19 `int[]` and other arrays as map keys silently use identity `hashCode` — use
        `Arrays.hashCode`, a `List<Integer>`, or a record. `[TRAP]`
1.10.20 Perfect hashing and minimal perfect hashing in one paragraph, for static key sets.
        `[RESEARCH]`
1.10.21 Consistent hashing and rendezvous hashing named here, owned by 22. `[X-REF 22]`

*(21 leaves)*

## §1.11 Linked lists

1.11.1 Node = payload + pointer(s); the structure is defined by reachability, not by layout.
1.11.2 Singly, doubly, circular, and the sentinel/header variants — the four shapes and what each
       buys.
1.11.3 O(1) insert/delete *at a known node*; Θ(n) to find that node. The distinction people collapse.
       `[TRAP]`
1.11.4 O(n) index access; no random access, therefore no binary search.
1.11.5 Memory overhead per element in Java: 16-byte header + 4/8-byte payload ref + 4/8-byte next ref
       → ~24–40 B for one `Integer`. `[NUM]` `[PROVE]`
1.11.6 Cache behaviour: pointer chasing defeats prefetch, which is why `ArrayList` beats
       `LinkedList` on insert-in-middle despite the Big-O. `[PROVE]` `[X-REF 02]`
1.11.7 **Dummy/sentinel head**: eliminates the head special case in every insert/delete.
1.11.8 **Fast/slow (Floyd tortoise-and-hare)**: cycle detection, middle finding, k-from-end, and the
       "meet inside the loop" argument. `[PROVE]`
1.11.9 The cycle-start derivation: meeting point is *not* the entry; reset one pointer to head and
       advance both by one. Prove with the distance algebra (L = μ + kλ). `[PROVE]` `[TRAP]` `[NUM]`
1.11.10 Cycle *length* and Brent's algorithm as the faster alternative to Floyd. `[RESEARCH]`
1.11.11 **Iterative reversal**: prev/curr/next in lockstep; the recursive form and its Θ(n) stack.
        `[PROVE]`
1.11.12 Reversal building blocks: palindrome check, reorder list, k-group reversal, add two numbers,
        swap pairs, rotate list.
1.11.13 Merge two sorted lists, and merge k lists via heap or divide-and-conquer.
1.11.14 Intersection of two lists: length-difference alignment, or the two-pointer switch trick.
        `[PROVE]`
1.11.15 Copy a list with random pointers: hash map, or the interleave-and-split O(1)-space trick.
1.11.16 Sorting a linked list: merge sort is the right answer (O(1) extra if bottom-up); quicksort is
        not. `[PROVE]`
1.11.17 Skip lists as the "linked list with binary search" answer, previewed here. `[X-REF 02]`
1.11.18 XOR linked lists and unrolled linked lists as the two classic space tricks (and why neither
        works in Java). `[RESEARCH]`
1.11.19 Java: `LinkedList` implements both `List` and `Deque`; `node(int)` walks from the nearer end;
        `LinkedList` is almost never the right production choice. `[TRAP]` `[X-REF 02]`
1.11.20 Interview convention: `ListNode` with a public `next`, no generics, mutation allowed unless
        stated.

*(20 leaves)*

## §1.12 Stacks

1.12.1 LIFO, with push/pop/peek/isEmpty all O(1).
1.12.2 The two implementations: growable array (amortized O(1), cache-friendly) and linked nodes
       (true O(1), per-node allocation).
1.12.3 The stack's real job: hold pending items whose resolution depends on something not yet seen.
1.12.4 The call stack as a stack — frames, locals, return addresses. `[X-REF 06]`
1.12.5 Balanced-bracket matching, and the generalisation to any nesting grammar.
1.12.6 Expression evaluation: infix → postfix (shunting-yard), postfix evaluation, prefix, and
       operator precedence/associativity handling. `[RESEARCH]`
1.12.7 Undo/redo as two stacks; browser history; backtracking state.
1.12.8 Iterative DFS with an explicit stack, and the push-order reversal needed to match recursive
       order. `[TRAP]`
1.12.9 Min-stack / max-stack: the auxiliary-stack design and the single-stack encoded-delta design.
       `[PROVE]` `[BUILD]`
1.12.10 Stack with O(1) `getMiddle`, and stack-of-stacks (set of plates) as the two structural
        variants asked about.
1.12.11 **Monotonic stack**, the pattern: maintain sorted order; a violation triggers pops, and each
        pop is where an answer is *resolved*.
1.12.12 Next-greater-element with a decreasing stack of indices; why the inner `while` is amortized
        O(1). `[PROVE]` `[TRAP]`
1.12.13 The four directional variants (next/previous × greater/smaller) and the single template that
        generates all four by flipping the comparison and the scan direction. `[DRILL]`
1.12.14 Monotonic-stack problem family: largest rectangle in histogram, maximal rectangle,
        trapping rain water, stock span, daily temperatures, remove k digits, sum of subarray
        minimums, 132-pattern, car fleet, asteroid collision.
1.12.15 The "previous smaller / next smaller" span decomposition that makes sum-of-subarray-minimums
        O(n), and the tie-breaking rule that avoids double counting. `[PROVE]` `[TRAP]`
1.12.16 Java: use `ArrayDeque` as the stack. `java.util.Stack` extends `Vector`, synchronizes every
        call, and iterates bottom-to-top (wrong order); `ArrayDeque` forbids null. `[TRAP]`
        `[X-REF 02]`
1.12.17 `Deque` naming map for stack use: `push`≡`addFirst`, `pop`≡`removeFirst`, `peek`≡`peekFirst`.
        `[X-REF 02]`
1.12.18 Queue-from-two-stacks and stack-from-two-queues, with the amortized argument for the former.
        `[PROVE]` `[BUILD]`

*(18 leaves)*

## §1.13 Queues and deques

1.13.1 FIFO; enqueue/dequeue/peek O(1).
1.13.2 The circular-buffer implementation: head, tail, size, and the wrap arithmetic. `[NUM]`
1.13.3 Full-vs-empty ambiguity in a circular buffer and the three fixes (keep a size field, keep one
       slot empty, keep a generation bit). `[TRAP]` `[PROVE]`
1.13.4 The queue's defining use: BFS, level-order traversal, and anything processed in arrival order.
1.13.5 Level-by-level BFS via a captured `queue.size()` before the inner loop. `[TRAP]`
1.13.6 Deque: O(1) at both ends; it subsumes both stack and queue.
1.13.7 **Monotonic deque** as the sliding-window extremum structure: maintain decreasing values,
       pop from the back what can never be the max, pop from the front what has left the window.
       `[PROVE]`
1.13.8 Sliding-window maximum in O(n) with the deque; and why a heap gives O(n log k) instead.
       `[PROVE]`
1.13.9 The deque-of-indices convention (store indices, not values, so expiry is checkable).
       `[TRAP]`
1.13.10 Monotonic-deque family: sliding window maximum/minimum, shortest subarray with sum ≥ k,
        longest subarray with |max−min| ≤ limit, jump game VI, constrained subsequence sum.
1.13.11 0-1 BFS with a deque (push-front for weight-0 edges, push-back for weight-1) as
        Dijkstra-without-a-heap. `[PROVE]` `[RESEARCH]`
1.13.12 `ArrayDeque` mechanics in Java 21: circular `Object[]`, default capacity `16 + 1 = 17`, no
        power-of-two requirement since JDK 9, forbids null. `[VERSION-TRAP]` `[NUM]` `[X-REF 02]`
1.13.13 `LinkedList` as a `Deque` allows null; `ArrayDeque` does not (null is the empty sentinel).
        The NPE arrives at insert, not at read. `[TRAP]`
1.13.14 Priority queue as a *different* structure with a queue-shaped API — forward reference to
        §1.16. `[TRAP]`
1.13.15 Blocking and concurrent queue variants named here, owned by 05. `[X-REF 05]`
1.13.16 Minimum-queue (queue supporting O(1) min) via two monotonic stacks or a monotonic deque.
        `[RESEARCH]` `[BUILD]`

*(16 leaves)*

## §1.14 Trees — vocabulary and traversal

1.14.1 Vocabulary, stated once and used consistently: root, parent, child, sibling, leaf, internal
       node, edge, path, depth (edges from root), height (edges to deepest leaf), level, subtree,
       ancestor, descendant, degree, forest.
1.14.2 Depth vs height off-by-one conventions, and the convention this file fixes. `[TRAP]`
1.14.3 Tree definition as a connected acyclic graph with n−1 edges, and the equivalence of the three
       characterisations. `[PROVE]`
1.14.4 Binary tree; k-ary tree; the shape taxonomy — full, complete, perfect, balanced, degenerate.
       The definitions people mix up. `[TRAP]`
1.14.5 A perfect binary tree of height h has 2^(h+1) − 1 nodes; n nodes give height ≥ ⌊log₂n⌋.
       `[PROVE]` `[NUM]`
1.14.6 In a full binary tree, #leaves = #internal + 1. `[PROVE]`
1.14.7 Number of distinct binary trees on n nodes = Catalan(n) = C(2n,n)/(n+1). `[NUM]` `[RESEARCH]`
1.14.8 Height h dominates cost: balanced h = Θ(log n), degenerate h = n and every operation goes
       linear.
1.14.9 Array representation of a complete tree: parent `(i−1)/2`, children `2i+1`/`2i+2` (0-based)
       or `i/2`, `2i`/`2i+1` (1-based). `[NUM]`
1.14.10 Preorder (root, left, right) — copying, serialization, prefix expressions.
1.14.11 Inorder (left, root, right) — sorted order on a BST.
1.14.12 Postorder (left, right, root) — deletion, and any value computed from children.
1.14.13 Level-order (BFS) — width, per-level aggregates, shortest path in a tree.
1.14.14 Reverse/zigzag/spiral level order, and boundary/vertical/diagonal traversals as the
       less-common orders that still appear. `[RESEARCH]`
1.14.15 Iterative preorder (one stack), iterative inorder (stack + go-left loop), iterative postorder
       (two stacks, or one stack with a `lastVisited` pointer). `[BUILD]`
1.14.16 **Morris traversal**: O(1) space inorder via threaded links, and how the thread is unwound.
       `[PROVE]` `[BUILD]` `[RESEARCH]`
1.14.17 Traversal reconstruction: preorder + inorder determines the tree; postorder + inorder does;
       preorder + postorder does **not** (unless full). `[PROVE]` `[TRAP]`
1.14.18 Serialization with null markers makes preorder alone sufficient. `[BUILD]`
1.14.19 Recursive "promise" framing: define what the function returns for a subtree, trust it for
       children, write only the combine step. The single most transferable tree skill.
1.14.20 Return-vs-mutate designs: returning a value up (height, sum) vs threading a mutable
       accumulator or field down.
1.14.21 The DFS-on-tree needs no visited set (no cycles) — a graph DFS does. `[TRAP]`
1.14.22 Classic tree problems by mechanism: height/diameter, balanced check, LCA, path sum, max path
       sum, invert, symmetric check, subtree check, flatten, right-side view, count complete-tree
       nodes in O(log²n), sum of left leaves, distribute coins.
1.14.23 Diameter via "height returns to parent, answer updates globally" — the two-value trick and
       why one return value is not enough. `[PROVE]`
1.14.24 LCA in a binary tree (bottom-up return) vs in a BST (descend by value) vs with parent
       pointers (two-list intersection). `[PROVE]`
1.14.25 N-ary and general trees: children lists, and the same traversals.
1.14.26 Threaded binary trees, and the parent-pointer representation.
1.14.27 Tree DP framing: what any per-subtree accumulation looks like, previewed for §3.12.
1.14.28 Euler tour / flattening a tree into an array, previewed for LCA-by-RMQ. `[RESEARCH]`

*(28 leaves)*

## §1.15 Binary search trees

1.15.1 **The BST invariant**: every key in the left subtree < node < every key in the right subtree —
       stated over subtrees, not over children. `[TRAP]`
1.15.2 Search, insert as O(h) descents.
1.15.3 Delete, all three cases: leaf, one child, two children (replace with inorder successor or
       predecessor). `[PROVE]`
1.15.4 Hibbard deletion's asymmetry: always taking the successor skews the tree to √n expected height
       over many random delete/insert cycles. `[RESEARCH]` `[TRAP]`
1.15.5 Inorder traversal yields sorted order — the property behind half the BST problems. `[PROVE]`
1.15.6 Predecessor/successor with and without parent pointers.
1.15.7 Min/max by walking to the extreme.
1.15.8 Kth smallest: inorder with a counter, or subtree-size augmentation for O(log n). `[PROVE]`
1.15.9 Range query `[lo, hi]` and range sum via pruned traversal.
1.15.10 **Validating a BST**: propagate (min, max) bounds down, or verify inorder is strictly
        increasing. Comparing against immediate children only is wrong. `[TRAP]` `[PROVE]`
1.15.11 The `null` bound representation problem: use `Long` bounds or nullable bounds, not
        `Integer.MIN_VALUE` (which a node can legitimately hold). `[TRAP]`
1.15.12 Random insertion order gives expected height Θ(log n); sorted insertion gives h = n.
        `[PROVE]` `[NUM]`
1.15.13 Building a balanced BST from a sorted array (mid as root, recurse) in O(n). `[BUILD]`
1.15.14 Balanced-BST families named here, mechanised in §3.5: AVL, red-black, treap, splay, scapegoat,
        AA-tree, B-tree, weight-balanced.
1.15.15 Java's `TreeMap`/`TreeSet` are red-black trees: O(log n) guaranteed, ordered navigation
        (`firstKey`, `lastKey`, `floorKey`, `ceilingKey`, `higherKey`, `lowerKey`, `headMap`,
        `tailMap`, `subMap`, `descendingMap`, `pollFirstEntry`). `[X-REF 02]`
1.15.16 The navigable-API use cases: time-series "last value at or before t", tier/range lookup,
       sliding-window rate limiter, leaderboard, 1-D nearest neighbour. `[X-REF 02]`
1.15.17 `TreeMap` uses `compareTo`/`Comparator`, not `equals` — two keys are "the same" iff
       `compare == 0`. `[TRAP]` `[X-REF 02]`
1.15.18 `TreeMap` rejects null keys; `HashMap` allows one. `[TRAP]`
1.15.19 When a BST beats a hash table: ordering, range scans, predecessor/successor, and iteration
       in sorted order. When it loses: point lookups, and constant factors.
1.15.20 BST vs sorted array vs heap vs hash table — the 4-way capability table.
1.15.21 Multiset via `TreeMap<K,Integer>` counts, and the "decrement or remove" idiom that keeps it
       correct. `[TRAP]`
1.15.22 BST problem family: convert sorted list/array to BST, recover a BST with two swapped nodes,
       BST iterator (controlled inorder), closest value, two-sum in a BST, delete a range, merge two
       BSTs, count smaller after self.

*(22 leaves)*

## §1.16 Heaps and priority queues

1.16.1 The abstract priority queue: insert, find-min, delete-min (and optionally decrease-key,
       merge, delete).
1.16.2 The binary heap as a complete binary tree in an array — no pointers, no wasted slots.
1.16.3 Index arithmetic (0-based): parent `(i−1)/2`, left `2i+1`, right `2i+2`; leaves start at
       `n/2`. `[NUM]`
1.16.4 The heap property is a *partial* order: a heap is not sorted, and the second-smallest can be
       either child. `[TRAP]`
1.16.5 `peek` O(1); `offer` O(log n) via `siftUp`; `poll` O(log n) via swap-last-then-`siftDown`.
1.16.6 `siftUp` and `siftDown` as the only two primitives, with their loop invariants. `[PROVE]`
1.16.7 **`heapify` is O(n), not O(n log n)** — the Σ (n/2^(h+1))·h = O(n) argument. `[PROVE]` `[NUM]`
1.16.8 Building by n inserts is O(n log n); bottom-up heapify is O(n). Both produce valid heaps; they
       are not the same heap. `[PROVE]` `[TRAP]`
1.16.9 Heapsort: heapify then extract-max in place — O(n log n) worst case, O(1) space, not stable,
       and worse cache behaviour than quicksort. `[PROVE]`
1.16.10 `decrease-key` and why `PriorityQueue` cannot do it in O(log n) (no handle) — the lazy-deletion
        workaround used in Dijkstra. `[TRAP]` `[PROVE]`
1.16.11 Indexed/handle-based priority queue as the structure that *can* decrease-key. `[BUILD]`
1.16.12 `remove(Object)` and `contains` on a binary heap are O(n) — the linear scan. `[TRAP]`
        `[RESEARCH]`
1.16.13 d-ary heaps: shallower tree, cheaper decrease-key, costlier delete-min; the log_d n vs d·log_d n
        trade-off. `[NUM]` `[PROVE]`
1.16.14 Heap variants and what each buys: binomial (O(log n) merge), Fibonacci (O(1) amortized
        decrease-key, and why nobody uses it), pairing, leftist, skew, randomized meldable heap.
        `[RESEARCH]`
1.16.15 Top-k with a size-k heap: **min-heap for the k largest**, max-heap for the k smallest;
        O(n log k) time, O(k) space. `[PROVE]` `[TRAP]`
1.16.16 Top-k alternatives: full sort O(n log n), quickselect O(n) expected, and when each wins.
        `[PROVE]`
1.16.17 K-way merge with a heap of k heads: O(N log k). `[PROVE]`
1.16.18 Two-heaps (running median): max-heap for the lower half, min-heap for the upper, size
        invariant |lo| − |hi| ∈ {0,1}, rebalance after each insert. `[PROVE]` `[BUILD]`
1.16.19 Scheduling with a heap: earliest deadline first, meeting rooms II, task scheduler, CPU
        interval scheduling, minimum-cost merges (Huffman).
1.16.20 Dijkstra's frontier and Prim's frontier as heaps. `[X-REF §2.18]`
1.16.21 Lazy deletion vs eager deletion in heap-based algorithms, and the "stale entry" check
        (`if (d > dist[u]) continue;`). `[TRAP]`
1.16.22 Java `PriorityQueue`: min-heap by default, default capacity 11, forbids null, unbounded,
        `Comparator` supplied at construction; **iteration and `toString` are not sorted** — only
        repeated `poll` is. `[NUM]` `[TRAP]` `[X-REF 02]`
1.16.23 Max-heap in Java: `Comparator.reverseOrder()`, `(a,b) -> b - a` (overflow-unsafe), or
        `Comparator.comparingInt(...).reversed()`. `[TRAP]`
1.16.24 `PriorityQueue` is not stable — equal-priority order is unspecified; add a sequence number to
        make it stable. `[TRAP]` `[PROVE]`
1.16.25 `PriorityQueue` sizing and growth (`< 64 ? 2n+2 : 1.5n`). `[NUM]` `[X-REF 02]`

*(25 leaves)*

## §1.17 Graphs — vocabulary and representation

1.17.1 Vocabulary: vertex, edge, directed/undirected, weighted/unweighted, adjacent, degree,
       in-degree, out-degree, walk, trail, path, cycle, simple graph, multigraph, self-loop.
1.17.2 Connectivity vocabulary: connected, connected component, strongly connected, weakly connected,
       bridge, articulation point, biconnected.
1.17.3 Special classes: tree, forest, DAG, bipartite, complete, planar, regular, sparse vs dense.
1.17.4 Handshake lemma: Σ deg(v) = 2|E|. `[PROVE]`
1.17.5 Edge bounds: a simple undirected graph has |E| ≤ n(n−1)/2; a tree has exactly n−1; a DAG can
       have up to n(n−1)/2. `[NUM]` `[PROVE]`
1.17.6 Adjacency list: `List<List<Integer>>` or `Map<V,List<V>>`, O(V+E) space, O(deg(v)) neighbour
       scan, O(deg(v)) edge-existence test. The default.
1.17.7 Adjacency matrix: `boolean[V][V]` / `int[V][V]`, O(V²) space, O(1) edge test, O(V) neighbour
       scan. Right for dense graphs, Floyd–Warshall, and small V.
1.17.8 Edge list: `int[][] edges`, the natural input format, and the right form for Kruskal and
       Bellman–Ford.
1.17.9 Compressed sparse row (CSR / flattened adjacency with a head array) as the cache-friendly
       production form. `[NUM]` `[BUILD]`
1.17.10 Implicit graphs: grids, word ladders, state machines, board positions — the graph you never
        materialise. Recognising them is a large fraction of graph problems.
1.17.11 Grid-as-graph conventions: 4 vs 8 neighbours, bounds checks, visited as `boolean[][]` or
        in-place marking. `[TRAP]`
1.17.12 The representation decision table: V, E, density, operations needed → representation.
1.17.13 Converting between representations, and the cost of each conversion.
1.17.14 Self-loops and parallel edges: which algorithms break on them, and the input-sanitising
        checklist. `[TRAP]`
1.17.15 0-indexed vs 1-indexed vertex labels, and the off-by-one this causes when the input is
        1-indexed. `[TRAP]`
1.17.16 Graph inputs with non-integer vertices: interning to indices with a `HashMap<String,Integer>`
        so you can use arrays.
1.17.17 Java's absent graph library: why you hand-roll, and what JGraphT/Guava `Graph` provide if
        you may use them. `[RESEARCH]`

*(17 leaves)*

## §1.18 Sorting — the basics

1.18.1 Why sorting is the most reused subroutine: it enables binary search, two pointers, greedy by
       key, dedup, grouping, and sweep-line.
1.18.2 The properties that classify a sort: comparison vs non-comparison, stable vs unstable,
       in-place vs out-of-place, adaptive vs non-adaptive, online vs offline, internal vs external.
1.18.3 **Stability defined**: equal keys retain input order — and the two places it matters
       (multi-key sorting by successive passes, and preserving a prior order). `[PROVE]`
1.18.4 Bubble sort: O(n²), O(n) adaptive best case with an early-exit flag, stable. Why it is only
       ever a teaching device.
1.18.5 Selection sort: O(n²) always, unstable, exactly n−1 swaps — the minimum-writes property that
       is its only virtue. `[NUM]` `[PROVE]`
1.18.6 Insertion sort: O(n²) worst, O(n) on nearly-sorted input, stable, in-place, online, and the
       fastest option below ~32–64 elements — which is why every real sort ends in it. `[NUM]`
       `[PROVE]`
1.18.7 Binary insertion sort: O(n log n) comparisons but still O(n²) moves. `[PROVE]` `[TRAP]`
1.18.8 Shell sort: gap sequences, and its status as the best simple sub-quadratic sort.
       `[RESEARCH]`
1.18.9 Merge sort: divide, recurse, merge; O(n log n) always, stable, Θ(n) extra space; the
       bottom-up/iterative variant; natural merge sort. `[PROVE]`
1.18.10 The merge step in detail, including the tie rule (`<=` takes from the left run) that makes it
        stable. `[PROVE]` `[TRAP]`
1.18.11 Quicksort: partition then recurse; O(n log n) expected, O(n²) worst, in-place, unstable.
1.18.12 Partition schemes: Lomuto (simple, poor on duplicates), Hoare (fewer swaps, subtle bounds),
        three-way / Dutch national flag (linear on many duplicates). `[PROVE]` `[TRAP]`
1.18.13 Pivot choice: last element (adversarially quadratic), random, median-of-three,
        median-of-medians (worst-case linear partition), ninther. `[PROVE]`
1.18.14 Tail-recursion elimination on the larger side to bound stack depth at O(log n). `[PROVE]`
1.18.15 Heapsort recap as the third O(n log n) in-place option. `[X-REF §1.16]`
1.18.16 The comparison-sorting lower bound Ω(n log n) via the decision tree: n! leaves, height ≥
        log₂(n!) = Θ(n log n). `[PROVE]` `[NUM]`
1.18.17 Non-comparison sorts and the assumptions that buy linearity: counting sort O(n+k), radix
        sort O(d·(n+k)) LSD and MSD, bucket sort O(n) expected on uniform input, pigeonhole sort.
        `[PROVE]`
1.18.18 Counting sort's stability requirement (the prefix-sum placement pass) and why radix sort
        depends on it. `[PROVE]` `[TRAP]`
1.18.19 Radix sort on negative numbers, floats, and strings — the encoding fixes. `[TRAP]`
1.18.20 External merge sort: k-way merge over runs, the memory/passes arithmetic. `[NUM]` `[X-REF 22]`
1.18.21 The master sorting comparison table: time (best/avg/worst), space, stable, in-place,
        adaptive, and the one-line "use it when".
1.18.22 Java: `Arrays.sort(primitives)` = dual-pivot quicksort (unstable, O(n²) adversarial);
        `Arrays.sort(Object[])`/`List.sort` = TimSort (stable, O(n) on sorted input, O(n/2) extra
        space). `[X-REF 02]`
1.18.23 The consequence for interviews: sorting `int[]` is DoS-able and unstable; boxing to
        `Integer[]` buys stability and adversarial safety at a memory cost. `[TRAP]` `[RESEARCH]`
1.18.24 `Arrays.parallelSort` and its `MIN_ARRAY_SORT_GRAN = 8192` threshold. `[NUM]` `[X-REF 02]`
1.18.25 `IllegalArgumentException: Comparison method violates its general contract!` — what TimSort
        detected, and the four usual causes (subtraction overflow, non-transitive comparator,
        mutating the sort key mid-sort, null-unsafe key). `[TRAP]` `[X-REF 02]`
1.18.26 Sorting by multiple keys: `Comparator.comparing(...).thenComparing(...)`, and
        `reversed()` reversing the whole chain built so far. `[TRAP]` `[X-REF 02]`
1.18.27 Never `return a - b` in a comparator — overflow. `Integer.compare` instead. `[PROVE]`
        `[TRAP]`
1.18.28 Sorting a `List<int[]>` by `Comparator.comparingInt(a -> a[0])` — the interval-problem
        workhorse.
1.18.29 Partial sorting: "sort only the first k" via a heap or `nth_element`-style quickselect.
        `[PROVE]`
1.18.30 Selection: kth smallest via sort O(n log n), heap O(n log k), quickselect O(n) expected,
        median-of-medians O(n) worst. `[PROVE]`
1.18.31 Sorting network / bitonic sort in one paragraph, as the parallel-hardware answer.
        `[RESEARCH]`
1.18.32 Counting inversions via merge sort — the canonical "sorting computes something else"
        problem. `[PROVE]`

*(32 leaves)*

## §1.19 Binary search

1.19.1 The precondition is not "sorted array" but **a monotonic predicate** — false…false,
       true…true. Everything else follows.
1.19.2 The invariant formulation: maintain "answer ∈ [lo, hi)" and shrink it. `[PROVE]`
1.19.3 The half-open template (`hi = n`, `while (lo < hi)`, `hi = mid` / `lo = mid + 1`, return
       `lo`) and why it cannot loop forever. `[PROVE]` `[BUILD]`
1.19.4 The closed template (`hi = n − 1`, `while (lo <= hi)`) and the `mid` that must advance.
1.19.5 **Never mix conventions.** The infinite loop is always a `mid` that fails to move a bound.
       `[TRAP]`
1.19.6 **`(lo + hi) / 2` overflows** for arrays ≥ 2³⁰ elements; use `lo + (hi − lo) / 2` or
       `(lo + hi) >>> 1`. Bloch's 2006 Google Research post, the bug in Bentley's *Programming
       Pearls* proof, and the same bug in the JDK's own `binarySearch`. `[TRAP]` `[NUM]`
       `[RESEARCH]` `[SOURCE]`
1.19.7 Lower bound (first index with `a[i] >= target`) and upper bound (first with `a[i] > target`),
       and how `upper − lower` gives the count of equal elements. `[PROVE]`
1.19.8 Exact search built out of lower bound, rather than as its own loop.
1.19.9 Predicate-based binary search: pass a `IntPredicate`, search the boundary — the form that
       generalises to every variant. `[BUILD]`
1.19.10 Binary search on a rotated sorted array: one half is always sorted; decide which, then
        decide whether the target lies inside it. With duplicates the bound degrades to O(n).
        `[PROVE]` `[TRAP]`
1.19.11 Find the minimum in a rotated array, and find the rotation count.
1.19.12 Peak element / bitonic array: compare with the neighbour, keep the rising side. The predicate
        is monotonic even though the array is not sorted. `[PROVE]`
1.19.13 Search in a 2-D matrix: fully sorted (treat as 1-D, index math) vs row-and-column sorted
        (staircase from the top-right in O(m+n), not binary search). `[TRAP]` `[PROVE]`
1.19.14 **Binary search on the answer**: when the answer is a number in a known range and
        feasibility is monotonic. The signature phrasings — "minimize the maximum", "maximize the
        minimum", "smallest k such that", "can we do it in D days".
1.19.15 The canonical set: Koko eating bananas, ship packages in D days, split array largest sum,
        minimum time to complete trips, magnetic force between balls, kth smallest in a
        multiplication table, median of two sorted arrays (the O(log(m+n)) partition version),
        aggressive cows.
1.19.16 Binary search on a real interval: fixed iteration count (~100) instead of an epsilon
        comparison, and why epsilon loops hang. `[TRAP]` `[NUM]`
1.19.17 Ternary search for unimodal functions, and why binary search on the derivative is usually
        better. `[RESEARCH]`
1.19.18 Exponential (galloping) search on an unbounded or unknown-length input: double until you
        overshoot, then binary search the O(log i) window. `[PROVE]`
1.19.19 Interpolation search: O(log log n) on uniform data, O(n) on adversarial. `[RESEARCH]`
1.19.20 Fractional cascading and binary search over multiple sorted lists, in one paragraph.
        `[RESEARCH]`
1.19.21 Branchless / bit-by-bit binary search, and why the sorted-array binary search is
        cache-hostile at large n. `[RESEARCH]` `[X-REF 06]`
1.19.22 Java: `Arrays.binarySearch` / `Collections.binarySearch` return `-(insertionPoint) - 1` when
        absent — how to recover the insertion point in one pass. `[NUM]` `[TRAP]`
1.19.23 `Collections.binarySearch` on a non-`RandomAccess` list uses an iterator-based algorithm
        above `BINARYSEARCH_THRESHOLD = 5000`. `[NUM]` `[X-REF 02]`
1.19.24 `binarySearch` on an unsorted input is silently wrong, not an error. `[TRAP]`
1.19.25 `TreeMap.floorKey`/`ceilingKey` and `NavigableSet` as the "binary search over a mutable
        collection" answer. `[X-REF 02]`
1.19.26 Binary search over a prefix-sum array (which is monotonic when values are non-negative) — the
        bridge from §2.4. `[PROVE]`
1.19.27 Binary lifting as binary search on a tree/functional graph, previewed for LCA. `[RESEARCH]`

*(27 leaves)*

## §1.20 Recursion

1.20.1 The two obligations: a base case, and a step that provably decreases toward it. `[PROVE]`
1.20.2 The stack frame: parameters, locals, return address, saved registers. `[X-REF 06]`
1.20.3 The "promise" (contract) framing: state what the function returns for any valid input, then
       write only the combine step.
1.20.4 The recursion tree as the analysis object: branching factor, depth, work per node.
1.20.5 Head vs tail recursion; direct vs indirect vs mutual recursion.
1.20.6 **The JVM does not eliminate tail calls** — a tail-recursive Java method still overflows.
       `[TRAP]` `[PROVE]`
1.20.7 `StackOverflowError` in practice: default ~512 KB–1 MB stack, ~10 000–20 000 frames, `-Xss`
       to raise it, and why raising it is a band-aid. `[NUM]` `[X-REF 06]`
1.20.8 Converting recursion to iteration: an explicit stack of frame records, and the
       "where do I resume" state variable that makes postorder awkward. `[BUILD]`
1.20.9 Trampolining and continuation-passing as the functional conversions. `[RESEARCH]`
1.20.10 Recursion vs iteration decision: readability and tree shape vs stack safety and constant
        factor.
1.20.11 **Naive recursive Fibonacci is Θ(φⁿ)** because the call tree recomputes subproblems; a memo
        collapses it to Θ(n). Recognising overlapping subproblems is the bridge to DP. `[PROVE]`
        `[TRAP]` `[NUM]`
1.20.12 Divide and conquer as a recursion shape: merge sort, quicksort, binary search, closest pair,
        Karatsuba, Strassen, FFT, maximum subarray D&C, counting inversions.
1.20.13 Decrease and conquer (one subproblem) vs divide and conquer (several).
1.20.14 **Backtracking = choose / recurse / un-choose.** The un-choose is what lets one mutable path
        buffer serve every level. `[PROVE]`
1.20.15 Why you copy at the leaf (`new ArrayList<>(path)`) and not at every level. `[TRAP]` `[NUM]`
1.20.16 Pruning as the dominant optimization: a constraint checked before recursing beats any
        micro-optimization. `[PROVE]`
1.20.17 The three pruning kinds: feasibility (can't work), bound (can't beat the best so far), and
        symmetry/dedup (already tried an equivalent branch).
1.20.18 Duplicate handling in backtracking: sort, then `if (i > start && a[i] == a[i-1]) continue;`
        — and why the `i > start` guard is the whole trick. `[PROVE]` `[TRAP]`
1.20.19 Combinations vs permutations vs subsets: the three loop/index shapes, and the `start` vs
        `used[]` distinction. `[TRAP]`
1.20.20 The canonical backtracking set: subsets, subsets II, permutations, permutations II,
        combination sum I/II/III, N-queens, sudoku solver, word search, palindrome partitioning,
        letter combinations of a phone number, restore IP addresses, generate parentheses,
        expression add operators, word break II, partition to k equal-sum subsets.
1.20.21 Complexity of backtracking: O(branching^depth × work-per-leaf), and how to state it for
        subsets (O(n·2ⁿ)) and permutations (O(n·n!)). `[NUM]` `[PROVE]`
1.20.22 Iterative subset generation with bitmasks as the loop-free alternative. `[BUILD]`
1.20.23 Recursion on strings: substring allocation vs index passing (the accidental O(n²)). `[TRAP]`
1.20.24 Global mutable state in recursion (fields, arrays of size 1, `AtomicInteger`) and when each
        is acceptable.
1.20.25 Memoization mechanics: array vs `HashMap`, sentinel for "not computed" (−1 vs `null` vs a
        separate `boolean[]`), and the bug when 0 or −1 is a legal answer. `[TRAP]`

*(25 leaves)*

## §1.21 The Java 21 toolkit for algorithm work

1.21.1 The eight types that cover almost every coding round: `int[]`, `char[]`, `ArrayList`,
       `ArrayDeque`, `HashMap`, `HashSet`, `PriorityQueue`, `TreeMap`. `[X-REF 02]`
1.21.2 Primitive arrays over collections in hot loops — the boxing and indirection argument.
       `[NUM]`
1.21.3 `int` vs `long` overflow discipline: `Integer.MAX_VALUE = 2_147_483_647` (~2.1·10⁹), so a
       sum of 10⁵ values up to 10⁵ overflows. `[NUM]` `[TRAP]`
1.21.4 `Math.addExact`/`multiplyExact`/`subtractExact` (throw on overflow), `Math.floorDiv`,
       `Math.floorMod` (correct for negatives, unlike `%`), `Math.abs(Integer.MIN_VALUE)` returning
       itself, `Math.clamp` (Java 21), `Math.toIntExact`. `[TRAP]` `[NUM]` `[RESEARCH]`
1.21.5 `%` on negatives is remainder, not modulus: `-1 % 5 == -1`. Use `((a % m) + m) % m` or
       `Math.floorMod`. `[TRAP]`
1.21.6 Integer division truncates toward zero; `(lo + hi) / 2` on negatives rounds the wrong way for
       a binary search over a signed range. `[TRAP]` `[PROVE]`
1.21.7 `Integer.MIN_VALUE` special cases: negation, `abs`, and `-x` in a comparator.
1.21.8 Bit utilities: `Integer.bitCount`, `highestOneBit`, `lowestOneBit`, `numberOfLeadingZeros`,
       `numberOfTrailingZeros`, `reverse`, `toBinaryString`, `Long.*` equivalents. `[NUM]`
1.21.9 `Integer.compare`, `Long.compare`, `Double.compare` — and why `Double.compare` is required
       for NaN and −0.0. `[TRAP]` `[X-REF 02]`
1.21.10 Boxing traps in algorithm code: `list.remove(int)` vs `list.remove(Object)`, `==` on
        `Integer` beyond the −128..127 cache, unboxing NPE from `map.get(missing)`. `[TRAP]`
        `[X-REF 03]`
1.21.11 The counting idioms: `map.merge(k, 1, Integer::sum)`,
        `map.computeIfAbsent(k, x -> new ArrayList<>()).add(v)`, `getOrDefault`.
        `[X-REF 02]`
1.21.12 Records as immutable tuples for states, coordinates, and memo keys —
        `record Point(int r, int c) {}` gives `equals`/`hashCode` for free. `[X-REF 04]`
1.21.13 Pattern-matching `switch` and sealed interfaces for expression trees and state machines.
        `[X-REF 04]`
1.21.14 Streams in algorithm code: where they are fine (input parsing, one-shot aggregation) and
        where they are not (hot inner loops, index-dependent logic). `[X-REF 04]`
1.21.15 `Arrays.stream(a).max().getAsInt()`, `IntStream.range`, `Collectors.groupingBy`,
        `Collectors.counting`, `boxed().toList()`. `[X-REF 04]`
1.21.16 Sequenced collections (Java 21, JEP 431): `getFirst`/`getLast`/`reversed` on `List`,
        `LinkedHashMap`, `TreeMap` — and what they replace. `[RESEARCH]` `[X-REF 02]`
1.21.17 Fast I/O when input size demands it: `BufferedReader` + `StringTokenizer` vs `Scanner`
        (~10× difference), and `StringBuilder` for output. `[NUM]`
1.21.18 `var` in algorithm code: acceptable for obvious constructors, harmful for `var lo = 0`
        when you meant `long`. `[TRAP]`
1.21.19 `assert` and defensive checks in interview code: what to include and what to say instead.
1.21.20 What *not* to reach for: `Vector`, `Stack`, `Hashtable`, `LinkedList`, `Collections.sort` on
        an `int[]` (doesn't compile), `Arrays.asList(int[])` (a one-element list). `[TRAP]`
        `[X-REF 02]`
1.21.21 Java 22–25 deltas relevant to algorithm work: nothing added to the collection or algorithm
        surface; `Stream.gather`/`Gatherer` (Java 24) is the adjacent addition; Java 25 is the new
        LTS (2025-09-16). `[RESEARCH]` `[X-REF 04]`

*(21 leaves)*

---

**PART 1 total: 425 leaves**

---

# PART 2 — INTERMEDIATE

## §2.1 The master cost table

2.1.1 One table: every operation × every structure, with **amortised** and **worst-case** in
      separate columns and a third column for "expected" where randomization is involved.
2.1.2 Rows for the linear structures: `get(i)`, `set(i)`, `insert(end)`, `insert(0)`, `insert(i)`,
      `delete(0)`, `delete(i)`, `delete(value)`, `search`, `min`, `max`, `iterate all`,
      `concatenate`, `split`.
2.1.3 Structures as columns: static array, dynamic array, singly-linked list, doubly-linked list,
      circular buffer, stack, queue, deque, binary heap, unsorted array, sorted array, BST
      (balanced), BST (degenerate), hash table, trie, skip list, union-find, Fenwick tree, segment
      tree, sparse table.
2.1.4 Map/set rows: `insert`, `lookup`, `delete`, `contains-value`, `min`, `max`, `predecessor`,
      `successor`, `range [a,b]`, `kth`, `ordered iteration`.
2.1.5 Graph-algorithm cost table: BFS, DFS, Dijkstra (binary heap / Fibonacci heap / array),
      Bellman–Ford, SPFA, Floyd–Warshall, Johnson, Kahn, Tarjan SCC, Kosaraju, Kruskal, Prim,
      Borůvka, Hierholzer, Hopcroft–Karp, Dinic. `[NUM]`
2.1.6 Sorting cost table (best/average/worst/space/stable/in-place/adaptive) for the 12 named sorts.
2.1.7 String-algorithm cost table: naive, KMP, Z, Rabin–Karp, Boyer–Moore, Aho–Corasick, suffix
      array construction, suffix automaton, Manacher. `[NUM]`
2.1.8 The amortised-vs-worst distinction spelled out in this table's own terms, with the three
      canonical rows (dynamic array append, hash insert, union-find find). `[PROVE]`
2.1.9 Expected-vs-worst rows: quickselect, quicksort, skip list, hash table, treap. `[PROVE]`
2.1.10 Constant factors that invert the table: array scan vs linked-list hop below ~1000 elements;
       `HashMap` vs `int[]` frequency array; `TreeMap` vs sorted `int[]` + binary search. `[PROVE]`
2.1.11 What is measurable and what is not: writing a JMH benchmark for two of these rows, and the
       dead-code/blackhole/warm-up pitfalls. `[X-REF 06]`
2.1.12 The "cost of a bad choice" table: which wrong structure turns which problem from n log n into
       n², with the specific problem for each.

*(12 leaves)*

## §2.2 Two pointers

2.2.1 The precondition: sorted input, or a monotone relationship that makes a discarded region
      provably useless.
2.2.2 The linearity argument: each pointer moves in one direction only, so total moves ≤ 2n.
      `[PROVE]`
2.2.3 Opposite-ends form: sorted two-sum, container with most water, trapping rain water (two-pointer
      version), valid palindrome, reverse in place, 3-sum inner loop.
2.2.4 The 3-sum discard argument: if `a[l] + a[r] > target`, no pair using `r` can work with a larger
      `l`, so `r--` is safe. This is the whole proof of correctness. `[PROVE]`
2.2.5 Same-direction (slow/fast writer) form: remove duplicates in place, move zeroes, remove
      element, partition by predicate, merge sorted array from the back. `[PROVE]`
2.2.6 The write-index idiom (`k` as the position of the next kept element) and why writing from the
      back avoids overwrite when merging in place. `[TRAP]`
2.2.7 Two pointers across two arrays: merge, intersection, union, "smallest common element",
      "find the median of two sorted arrays" (the linear version).
2.2.8 Fast/slow on a functional graph: cycle detection in an array-as-mapping (find the duplicate
      number in O(1) space). `[PROVE]`
2.2.9 Expand-from-centre as a two-pointer variant: longest palindromic substring in O(n²) with 2n−1
      centres. `[NUM]`
2.2.10 3-sum, 4-sum, k-sum generalisation: sort, fix k−2 indices, two-pointer the rest → O(n^(k−1)).
       `[PROVE]` `[NUM]`
2.2.11 Duplicate skipping in k-sum, and where the skip must go to avoid missing valid triples.
       `[TRAP]`
2.2.12 **Two pointers fails when the array is unsorted and sorting destroys the required indices** —
       return values vs return indices changes the whole approach. `[TRAP]`
2.2.13 Two pointers vs sliding window vs binary search: the decision rule.
2.2.14 The canonical problem set with the discard argument stated for each. `[DRILL]`

*(14 leaves)*

## §2.3 Sliding window

2.3.1 Definition: a contiguous range `[l, r]`, with `r` expanding and `l` contracting to restore an
      invariant.
2.3.2 The linearity argument: each index enters once and leaves once, so O(n) despite the nested
      loop. `[PROVE]`
2.3.3 Fixed-size window: advance both ends together, maintain a running aggregate; the add-new /
      remove-old pair.
2.3.4 Variable-size window, "longest valid": expand always, shrink while invalid, record the answer
      after shrinking. `[BUILD]`
2.3.5 Variable-size window, "shortest valid": expand until valid, then shrink while still valid,
      recording each time. The two templates are not interchangeable. `[TRAP]` `[BUILD]`
2.3.6 The "at most k" → "exactly k" transformation: `exactly(k) = atMost(k) − atMost(k−1)`.
      `[PROVE]`
2.3.7 The non-shrinking window trick (window only grows; the answer is `r − l + 1` at the end) —
      why it works for "longest" problems. `[PROVE]` `[RESEARCH]`
2.3.8 Window state representations: running sum, running product, `int[26]`/`int[128]` counts,
      `HashMap<Character,Integer>`, a distinct-count integer, a monotonic deque, a `TreeMap`.
2.3.9 The distinct-count maintenance idiom: increment/decrement counts and adjust a `distinct`
      counter only on 0↔1 transitions. `[TRAP]`
2.3.10 **The monotonicity precondition.** "Longest subarray with sum ≤ k" works with positive values
       because extending can only increase the sum. Add negatives and shrinking from the left no
       longer reliably restores validity — you need prefix sums + a hash map, or a monotonic deque.
       `[TRAP]` `[PROVE]`
2.3.11 The prefix-sum + hash-map replacement for windows over arbitrary-sign values: subarray sum
       equals k, count of subarrays with sum divisible by k, longest subarray with sum 0. `[PROVE]`
2.3.12 Prefix-sum + monotonic-deque for "shortest subarray with sum ≥ k" over arbitrary signs.
       `[PROVE]`
2.3.13 Windows over a stream (no random access) and the O(k) memory bound.
2.3.14 The canonical set: longest substring without repeating characters, longest repeating character
       replacement, minimum window substring, permutation in string, find all anagrams, max
       consecutive ones III, fruit into baskets, subarrays with k different integers, sliding window
       maximum, minimum size subarray sum, maximum average subarray, longest subarray with absolute
       diff ≤ limit, count number of nice subarrays.
2.3.15 Two-window and multi-window variants (max sum of two non-overlapping subarrays).
2.3.16 The window-invariant statement discipline: write the invariant as a comment before coding —
       the single practice that prevents most sliding-window bugs.

*(16 leaves)*

## §2.4 Prefix sums, difference arrays, and precomputation

2.4.1 Prefix sums: `p[0] = 0`, `p[i+1] = p[i] + a[i]`; range sum `[l, r] = p[r+1] − p[l]`. The
      off-by-one that the extra leading zero removes. `[NUM]` `[TRAP]`
2.4.2 Θ(n) preprocessing buys Θ(1) queries — the archetypal time–space trade.
2.4.3 Overflow: prefix sums of `int` must be `long`. `[TRAP]` `[NUM]`
2.4.4 Prefix XOR, prefix product (and the zero problem), prefix max (not invertible, so not a
      prefix trick — needs a sparse table). `[TRAP]`
2.4.5 2-D prefix sums (integral image): `S[i][j]` and the four-term inclusion–exclusion query.
      `[NUM]` `[PROVE]` `[BUILD]`
2.4.6 Difference arrays: range update in O(1), then one prefix pass to materialise. `[PROVE]`
      `[BUILD]`
2.4.7 2-D difference arrays for rectangle updates (the four-corner ±1 trick). `[NUM]`
2.4.8 The sweep-line / event-count form of a difference array: `+1` at start, `−1` at end, prefix
      to get concurrency — the "minimum meeting rooms" and "car pooling" solution. `[PROVE]`
2.4.9 Prefix sums + hash map for subarray-sum problems (the §2.3.11 family), including the
      "seen prefix count" map initialised with `{0: 1}` and why that initialisation is required.
      `[TRAP]` `[PROVE]`
2.4.10 Prefix remainders for divisibility: `(p[j] − p[i]) % k == 0` ⟺ equal remainders; the negative
       remainder fix. `[PROVE]` `[TRAP]`
2.4.11 Prefix parity/bitmask for "substring with even counts of every vowel" — mask as the key.
       `[PROVE]`
2.4.12 Suffix sums, suffix max/min, and the "prefix from left, suffix from right, combine" pattern
       (product of array except self, trapping rain water, best time to buy and sell).
2.4.13 When prefix sums stop working: updates. That is exactly the gap Fenwick and segment trees
       fill. `[X-REF §3.14]`
2.4.14 The update/query cost table: static prefix sums O(1)/O(n)-rebuild, Fenwick O(log n)/O(log n),
       segment tree O(log n)/O(log n), sqrt decomposition O(1)/O(√n), sparse table O(1) query but
       immutable. `[NUM]`
2.4.15 Other precomputations worth the pass: factorials and inverse factorials mod p, powers of two,
       sieve-based smallest prime factor, digit sums, `log2` table, binomial table, direction arrays.

*(15 leaves)*

## §2.5 Intervals and sweep line

2.5.1 The interval representation choice: `int[]{start, end}`, a record, or two parallel arrays; and
      closed vs half-open conventions. `[TRAP]`
2.5.2 **Sort by start** for merging and inserting; **sort by end** for maximum non-overlapping
      selection. The choice of sort key *is* the algorithm. `[PROVE]`
2.5.3 Merge intervals: sort by start, then extend-or-push. `[PROVE]` `[BUILD]`
2.5.4 Insert interval without a full sort (three-phase scan: before, overlapping, after).
2.5.5 Interval intersection of two sorted lists via two pointers: `max(starts)`, `min(ends)`,
      advance the one that ends first. `[PROVE]`
2.5.6 Overlap test in one expression: `a.start < b.end && b.start < a.end` (half-open) — and the
      closed-interval variant. `[NUM]` `[TRAP]`
2.5.7 Non-overlapping maximum count / minimum removals: greedy by earliest end, with the exchange
      argument. `[PROVE]`
2.5.8 Minimum number of platforms / meeting rooms II: heap of end times, or the ±1 sweep. Both are
      O(n log n) and the sweep is simpler. `[PROVE]`
2.5.9 Employee free time / merge k interval lists via a heap.
2.5.10 Interval covering / minimum number of taps or arrows: greedy by reach.
2.5.11 Sweep-line generalisation: events sorted by coordinate, a running structure updated per
       event; tie-breaking rules at equal coordinates (close before open, or the reverse, depending
       on whether touching counts as overlap). `[TRAP]` `[PROVE]`
2.5.12 The skyline problem: sweep with a multiset/heap of active heights. `[BUILD]`
2.5.13 Rectangle area union via sweep + segment tree, named as the escalation path. `[X-REF §3.14]`
2.5.14 Interval scheduling with weights is *not* greedy — it is DP (weighted interval scheduling with
       binary search on the previous compatible interval). `[TRAP]` `[PROVE]`
2.5.15 Calendar / booking structures: `TreeMap<Integer,Integer>` with `floorEntry`/`ceilingEntry` for
       O(log n) book-if-free. `[X-REF 02]`
2.5.16 Interval trees and segment trees for interval stabbing queries, named here.
2.5.17 The canonical set: merge intervals, insert interval, non-overlapping intervals, meeting rooms
       I/II, minimum arrows to burst balloons, car pooling, my calendar I/II/III, skyline, employee
       free time, interval list intersections, video stitching, minimum taps to water a garden.

*(17 leaves)*

## §2.6 In-place array techniques

2.6.1 The "O(1) extra space" signal: the interviewer is asking for index-as-hash, swapping,
      reversal, or two pointers.
2.6.2 **Cyclic sort**: when values are a permutation of `1..n` (or `0..n−1`), place each value at its
      index by swapping; O(n) with at most n swaps. `[PROVE]` `[BUILD]`
2.6.3 The cyclic-sort family: missing number, find all missing numbers, duplicate number, find all
      duplicates, first missing positive, set mismatch, "k missing positive numbers".
2.6.4 The `while` (not `if`) in the swap loop, and why an `if` leaves the array unsorted. `[TRAP]`
      `[PROVE]`
2.6.5 **Index-as-hash by sign marking**: negate `a[|a[i]| − 1]` to record presence; requires
      positive values and destroys them. `[PROVE]` `[TRAP]`
2.6.6 Index-as-hash by adding `n`: encode two pieces of information in one slot with `a[i] % n` and
      `a[i] / n`. `[NUM]` `[PROVE]`
2.6.7 Reversal: whole-then-parts rotation (`reverse(0,n)`, `reverse(0,k)`, `reverse(k,n)`) — O(n)
      time, O(1) space, and the proof that it composes to a rotation. `[PROVE]` `[BUILD]`
2.6.8 Juggling / GCD-cycle rotation as the alternative, with the `gcd(n,k)` cycle count. `[NUM]`
      `[PROVE]`
2.6.9 **Dutch national flag** (three-way partition): `low`, `mid`, `high`, and the invariant that
      makes the single pass correct — including why the `high` swap does not advance `mid`.
      `[PROVE]` `[TRAP]` `[BUILD]`
2.6.10 Sort colors, partition array by parity, move zeroes, and segregate positives/negatives as the
       partition family.
2.6.11 Matrix in place: transpose then reverse rows = rotate 90° clockwise; the layer-by-layer
       four-way swap alternative. `[PROVE]` `[BUILD]`
2.6.12 Set matrix zeroes in O(1) space using the first row and column as the marker store, and the
       ordering that makes it correct. `[PROVE]` `[TRAP]`
2.6.13 Spiral matrix traversal and generation via four moving boundaries.
2.6.14 Next permutation: find the pivot from the right, find the successor, swap, reverse the suffix
       — with the proof that this yields the lexicographic next. `[PROVE]` `[BUILD]`
2.6.15 Kth permutation via factorial number system, as the O(n²) direct construction. `[NUM]`
2.6.16 In-place merge of two sorted halves: the Shell/gap method O(n log n), and why the naive
       rotate-based merge is O(n²). `[PROVE]` `[RESEARCH]`
2.6.17 Kadane's algorithm: `cur = max(a[i], cur + a[i])`, `best = max(best, cur)`; the DP reading and
       the all-negatives edge case. `[PROVE]` `[TRAP]`
2.6.18 Kadane variants: maximum product subarray (track min and max), circular subarray maximum
       (total − minimum subarray, with the all-negative exception), maximum sum with one deletion.
       `[PROVE]` `[TRAP]`
2.6.19 **Boyer–Moore majority vote**: candidate + count, O(1) space; the pairing-cancellation proof,
       and the required verification pass when a majority is not guaranteed. `[PROVE]` `[TRAP]`
2.6.20 The generalised Boyer–Moore for elements appearing more than n/k times, with k−1 candidates.
       `[PROVE]` `[RESEARCH]`
2.6.21 Bit-manipulation in-place tricks: XOR swap (and why never to use it), single number via XOR,
       two single numbers via the lowest set bit split, single number among triples via bit counts
       mod 3. `[PROVE]`
2.6.22 In-place linked-list equivalents: reversal, reorder, partition — cross-reference to §1.11.
2.6.23 When "in-place" is actually forbidden: the input is shared, immutable, or must be preserved
       for the caller. Say it out loud before mutating. `[TRAP]`

*(23 leaves)*

## §2.7 Binary search applied

2.7.1 Recognition drill: five problem statements, decide in one sentence each whether a monotonic
      predicate exists. `[DRILL]`
2.7.2 Constructing the predicate for "minimum capacity to ship packages in D days": `feasible(c)` =
      greedy simulation, monotone in `c`. `[PROVE]` `[BUILD]`
2.7.3 The search-space bounds derivation: `lo = max(weights)`, `hi = sum(weights)` — and why sloppy
      bounds are the usual bug. `[TRAP]`
2.7.4 Split-array-largest-sum and its equivalence to the shipping problem. `[PROVE]`
2.7.5 Koko eating bananas, minimum time to complete trips, minimum speed to arrive on time,
      magnetic force between balls (maximize the minimum), and the "maximize the minimum" mirror
      template. `[BUILD]`
2.7.6 Kth smallest element in a sorted matrix / multiplication table / pair distance: binary search
      on the *value*, count-with-a-linear-pass as the predicate. `[PROVE]`
2.7.7 Median of two sorted arrays in O(log(min(m,n))) by binary searching the partition point, with
      the four boundary values and the ±∞ sentinels. `[PROVE]` `[BUILD]` `[TRAP]`
2.7.8 Binary search on a monotonic function over reals: fixed 100 iterations, and the precision
      arithmetic. `[NUM]`
2.7.9 Binary search inside DP: longest increasing subsequence in O(n log n) via the tails array —
      and the fact that the tails array is not itself an LIS. `[PROVE]` `[TRAP]` `[BUILD]`
2.7.10 Binary search inside greedy: weighted interval scheduling, "russian doll envelopes".
2.7.11 Parallel binary search and binary search on the answer with an offline structure, named for
       completeness. `[RESEARCH]`
2.7.12 The failure mode: binary searching a predicate that is not monotone yields a silently wrong
       answer, never an error. Test the predicate at three points before trusting it. `[TRAP]`

*(12 leaves)*

## §2.8 Sorting applied, and selection

2.8.1 "Sort first" as a default move, and the O(n log n) floor it imposes on the whole solution —
      state the cost before committing. `[TRAP]`
2.8.2 Sort-enabled patterns: two pointers, binary search, greedy by key, dedup, grouping,
      sweep-line, and "sorted order is the answer" (largest number, meeting order).
2.8.3 Custom comparators for non-obvious orders: largest-number-from-digits (`(a+b) vs (b+a)`),
      boomerang/queue reconstruction, "sort by frequency then value". `[PROVE]`
2.8.4 The comparator must be a total order: transitivity failures are what trigger TimSort's
      contract exception. `[PROVE]` `[X-REF 02]`
2.8.5 Counting sort applied when the value range is small (ages, characters, grades, bucketed
      scores) — the "0 ≤ a[i] ≤ 100" constraint as the signal. `[BUILD]`
2.8.6 Bucket sort applied to top-k-frequent: buckets indexed by frequency give O(n) instead of
      O(n log k). `[PROVE]` `[BUILD]`
2.8.7 Radix sort applied to "maximum gap" and to sorting fixed-width keys. `[PROVE]`
2.8.8 Pancake sort / sort with a restricted operation, as the "sorting under constraints" family.
2.8.9 Wiggle sort and its O(n) three-way-partition-plus-virtual-index solution. `[RESEARCH]`
2.8.10 **Quickselect**: partition, recurse into one side only; T(n) = T(n/2) + O(n) → O(n) expected,
       O(n²) worst without random pivoting. `[PROVE]` `[BUILD]`
2.8.11 **Median of medians**: groups of 5, recurse on the medians, guaranteed 30/70 split, T(n) =
       T(n/5) + T(7n/10) + O(n) → O(n) worst case — and why the constant makes it theoretical.
       `[PROVE]` `[NUM]`
2.8.12 The four ways to get the kth element, with the choice rule: sort, heap of size k, quickselect,
       counting/bucket. `[PROVE]`
2.8.13 Order statistics beyond the median: k closest points, k closest to a value, kth largest in a
       stream (heap, because the input is not re-readable). `[PROVE]`
2.8.14 Counting inversions (merge sort), "count of smaller numbers after self" (BIT or merge sort),
       and "reverse pairs" as the sorting-computes-something-else family.
2.8.15 Merge-sort-based algorithms on linked lists and on external data. `[X-REF 22]`
2.8.16 Sorting stability applied: sorting by secondary key first, then primary — and why the reverse
       order is wrong. `[PROVE]` `[TRAP]`
2.8.17 Sorting a `Map` by value into a `LinkedHashMap`, and the "top n by count" idiom. `[BUILD]`
2.8.18 When *not* to sort: when an O(n) pass suffices (max, min, majority, Kadane), when the input is
       a stream, when indices must be preserved, when partial order is enough. `[TRAP]`

*(18 leaves)*

## §2.9 Tree techniques

2.9.1 The four recursion shapes: return a value up, pass state down, do both, and use a mutable
      field for a global answer.
2.9.2 Height, depth, size, and diameter as the four accumulations everything else is built from.
2.9.3 Balanced-tree check: return height, use −1 as the "unbalanced" sentinel to keep it one pass.
      `[PROVE]` `[BUILD]`
2.9.4 Path-sum family: root-to-leaf exists, all root-to-leaf paths, count of any-downward paths with
      a target sum via a prefix-sum map on the current path. `[PROVE]` `[BUILD]`
2.9.5 Maximum path sum (any node to any node): the "return the best single branch, update the global
      with both branches" split. `[PROVE]` `[TRAP]`
2.9.6 The "two return values" pattern via a record or an `int[2]`, and when it beats a field.
2.9.7 LCA variants: binary tree, BST, with parent pointers, k nodes, and the "distance between two
      nodes = d(a) + d(b) − 2·d(lca)" identity. `[PROVE]` `[NUM]`
2.9.8 Binary lifting for LCA: `up[k][v]` table in O(n log n), queries in O(log n). `[BUILD]`
      `[RESEARCH]`
2.9.9 Euler tour + sparse table for O(1) LCA queries, named with its cost. `[RESEARCH]`
2.9.10 Subtree aggregation via Euler tour intervals (`tin`/`tout`) so a subtree becomes a contiguous
       range — the bridge to Fenwick/segment trees on trees. `[PROVE]` `[RESEARCH]`
2.9.11 Serialization: preorder with null markers, level-order with markers, and the parenthesis
       encoding. `[BUILD]`
2.9.12 Construction from traversals: preorder+inorder with an index map for O(n). `[BUILD]`
2.9.13 BST-specific: validate, kth smallest, range sum, closest value, two-sum, iterator, recover
       from two swaps, trim to a range, insert/delete.
2.9.14 Complete-tree node count in O(log² n) by comparing left and right heights. `[PROVE]`
2.9.15 Tree DP: rob the house tree, binary tree cameras, distribute coins, longest univalue path,
       tree diameter, count good nodes — the "combine children's states" frame. `[X-REF §3.12]`
2.9.16 Rerooting technique (compute an answer for every root in O(n)) named with its shape.
       `[RESEARCH]`
2.9.17 N-ary tree traversals and the "clone a graph vs clone a tree" distinction.
2.9.18 Converting a tree problem to a graph problem (add parent edges) when the question asks about
       distance in both directions. `[PROVE]`
2.9.19 Heavy-light decomposition and centroid decomposition, named with their cost and use.
       `[RESEARCH]`
2.9.20 Trees as a special case: every DP-on-tree is a DAG DP; every tree traversal is a DFS without
       a visited set.

*(20 leaves)*

## §2.10 BFS and DFS as patterns

2.10.1 The shared skeleton, differing only in container: BFS queue, DFS stack (explicit or the call
       stack). `[PROVE]`
2.10.2 **BFS explores by distance**, so on an unweighted graph the first arrival at a node is via
       the fewest edges — the shortest-path property. `[PROVE]`
2.10.3 Level-by-level BFS via captured `size()`, and the distance-array alternative. `[TRAP]`
2.10.4 BFS space is O(width), which can be Θ(V) on a wide or dense graph. `[NUM]`
2.10.5 **Mark visited at enqueue, not at dequeue** — otherwise a node is enqueued once per incoming
       edge and the queue blows up. `[TRAP]` `[PROVE]`
2.10.6 **Multi-source BFS**: seed the queue with all sources at distance 0 to get "nearest source for
       every cell" in one pass. Rotting oranges, walls and gates, 01-matrix, shortest bridge.
       `[PROVE]`
2.10.7 Bidirectional BFS: search from both ends, meet in the middle; branching factor b^(d/2) + b^(d/2)
       instead of b^d. Word ladder as the canonical use. `[PROVE]` `[NUM]`
2.10.8 0-1 BFS with a deque for edge weights in {0,1}. `[PROVE]`
2.10.9 BFS on implicit graphs: word ladder, open the lock, minimum genetic mutation, jump game IV,
       sliding puzzle, minimum knight moves — the "state as vertex" reframing.
2.10.10 State-space BFS where the state is richer than the position: (cell, keys-collected bitmask),
        (cell, remaining obstacle removals), (cell, parity of steps). The visited set must key on the
        *full* state. `[TRAP]` `[PROVE]`
2.10.11 **DFS explores by depth**, and is the tool for connectivity, cycle detection, topological
        order, backtracking, and any "all paths" enumeration.
2.10.12 DFS space is O(depth); on a 10⁵-node path graph, recursion overflows — convert to an explicit
        stack. `[TRAP]` `[NUM]`
2.10.13 Flood fill / connected components on a grid, with in-place marking as the visited set.
2.10.14 Number-of-islands family: islands, max area, island perimeter, surrounded regions, number of
        closed islands, number of distinct islands (canonical shape hashing), making a large island.
2.10.15 Cycle detection, directed: three-colour (white/grey/black) or a recursion-stack set; a back
        edge to a *grey* node is a cycle, a revisit of a *black* node is not. `[TRAP]` `[PROVE]`
2.10.16 Cycle detection, undirected: any visited neighbour other than the parent — plus the
        parallel-edge caveat that makes "parent by vertex" wrong and "parent by edge id" right.
        `[TRAP]` `[PROVE]`
2.10.17 All-paths enumeration on a DAG (no visited set needed) vs on a general graph (path-local
        visited, restored on backtrack). `[TRAP]`
2.10.18 Bipartite check / graph 2-colouring by BFS or DFS, and the odd-cycle equivalence. `[PROVE]`
2.10.19 Iterative deepening DFS as the memory-cheap BFS substitute. `[RESEARCH]`
2.10.20 Best-first search and A* in one paragraph: a heuristic-ordered priority queue, admissibility
        and consistency as the correctness conditions. `[PROVE]` `[RESEARCH]`
2.10.21 Trees need no visited set; graphs do; grids can use in-place marking. The three-case rule.
2.10.22 Choosing BFS or DFS: shortest path and level structure → BFS; existence, enumeration,
        ordering, and low memory on deep graphs → DFS.

*(22 leaves)*

## §2.11 Heap and top-k patterns

2.11.1 Top-k elements: min-heap of size k, `O(n log k)`; the "which polarity" reasoning restated as a
       rule. `[PROVE]` `[TRAP]`
2.11.2 K closest points to the origin / k closest to a value: heap, sort, or quickselect — the choice
       rule by whether the input is a stream. `[PROVE]`
2.11.3 Kth largest in a stream: a size-k min-heap is the only option, because past elements are gone.
       `[PROVE]`
2.11.4 Top-k frequent elements: heap O(n log k) vs bucket-by-frequency O(n). `[PROVE]`
2.11.5 K-way merge: merge k sorted lists/arrays/iterators with a heap of heads, O(N log k).
       `[BUILD]`
2.11.6 Smallest range covering elements from k lists, and "find k pairs with smallest sums" as
       k-way-merge in disguise.
2.11.7 Two-heaps: running median, IPO/maximize capital, sliding window median (heap + lazy deletion,
       or two `TreeMap`s). `[PROVE]` `[BUILD]`
2.11.8 Sliding-window median with lazy deletion: the "delayed removal" hash map and the size
       bookkeeping it forces. `[TRAP]` `[RESEARCH]`
2.11.9 Scheduling with heaps: task scheduler, reorganize string, minimum number of refuelling stops,
       course schedule III, single-threaded CPU, meeting rooms II.
2.11.10 Cost-merging with heaps: minimum cost to connect sticks, Huffman coding, last stone weight.
        `[PROVE]`
2.11.11 Heap + hash map for "priority queue with update" (task scheduler with priorities), and why
        the indexed heap is the clean answer. `[BUILD]`
2.11.12 `PriorityQueue` of `int[]` vs of a record vs of an index with an external key array — the
        three encodings and their allocation cost. `[NUM]`
2.11.13 Deciding heap vs sort vs quickselect vs bucket vs `TreeMap`: the decision table. `[DRILL]`

*(13 leaves)*

## §2.12 Backtracking, systematically

2.12.1 The template, written once: `if (goal) record; for (choice : choices) { if (!valid) continue;
       apply; recurse; undo; }`. `[BUILD]`
2.12.2 The four axes that distinguish every backtracking problem: order matters or not, reuse allowed
       or not, duplicates in input or not, and whether the answer is one solution or all.
2.12.3 The 2×2 table: subsets (order-insensitive, no reuse) / combinations (fixed size) /
       permutations (order matters) / combinations with repetition — and the loop shape for each.
       `[DRILL]`
2.12.4 `start` index for combinations vs `used[]` for permutations, and why swapping `start` into a
       permutation loop silently produces combinations. `[TRAP]`
2.12.5 Duplicate handling: sort + `if (i > start && a[i] == a[i-1]) continue;` for combinations;
       `if (used[i] || (i > 0 && a[i] == a[i-1] && !used[i-1])) continue;` for permutations. Prove
       each. `[PROVE]` `[TRAP]`
2.12.6 Pruning by feasibility: break out of the loop when `a[i] > remaining` on sorted input.
       `[PROVE]`
2.12.7 Pruning by bound (branch and bound): keep the best-so-far and abandon branches that cannot
       beat it. `[PROVE]`
2.12.8 Pruning by symmetry: fixing the first queen to the left half, canonical-form dedup.
2.12.9 N-queens: the three conflict sets (column, `r+c` diagonal, `r−c` anti-diagonal) as boolean
       arrays or bitmasks, and the O(1) conflict check. `[NUM]` `[BUILD]`
2.12.10 Sudoku solver: the 27 constraint sets, box index `(r/3)*3 + c/3`, and the
        most-constrained-cell heuristic. `[NUM]` `[BUILD]`
2.12.11 Word search on a grid: DFS with in-place marking and restoration; Word Search II with a trie
        so the DFS dies the moment the prefix leaves the dictionary. `[PROVE]` `[BUILD]`
2.12.12 Palindrome partitioning with a precomputed `isPal[i][j]` table to make the validity check
        O(1). `[PROVE]`
2.12.13 Partition to k equal-sum subsets: the sort-descending, skip-duplicate-buckets, and
        fail-fast-on-first-item pruning set. `[RESEARCH]`
2.12.14 Generate parentheses via the open/close counter invariant rather than generate-and-filter.
        `[PROVE]`
2.12.15 Expression add operators / restore IP addresses: string-position recursion with leading-zero
        and overflow guards. `[TRAP]`
2.12.16 Backtracking vs DFS vs DP: backtracking enumerates, DP counts or optimizes; when the question
        says "count the ways", stop backtracking and write the recurrence. `[TRAP]`
2.12.17 Memoized backtracking (word break, matchsticks to square) — when the state is small enough
        for a memo, backtracking becomes DP. `[PROVE]`
2.12.18 Complexity statements for the canonical set: subsets O(n·2ⁿ), permutations O(n·n!),
        combination sum O(n^(target/min)), N-queens O(n!), sudoku exponential. `[NUM]`
2.12.19 Iterative alternatives: bitmask subset enumeration, `next_permutation` loops, and BFS-layered
        generation. `[BUILD]`

*(19 leaves)*

## §2.13 Dynamic programming

2.13.1 The two required properties: **optimal substructure** (an optimal solution is composed of
       optimal sub-solutions) and **overlapping subproblems** (the same subproblem recurs).
       `[PROVE]`
2.13.2 Optimal substructure fails: longest *simple* path in a general graph — and why that kills DP
       there. `[PROVE]` `[TRAP]`
2.13.3 DP vs divide and conquer vs greedy: overlapping vs disjoint subproblems; provable local choice
       vs enumerated choices.
2.13.4 The five-step procedure, in order: define the state, define the recurrence, define the base
       cases, decide the iteration order, decide the answer's location.
2.13.5 **Defining the state is the work.** "What parameters uniquely identify a subproblem, and
       nothing more" — plus the test that a state is sufficient (the future depends only on it).
       `[PROVE]`
2.13.6 The SRTBOT framing (Subproblem, Relate, Topological order, Base, Original, Time) as an
       explicit checklist. `[RESEARCH]`
2.13.7 **Top-down memoization**: write the recursion, cache by state. Easier to derive, carries
       recursion depth, computes only reachable states.
2.13.8 **Bottom-up tabulation**: fill in dependency order. No stack risk, easier to space-optimize,
       computes every state whether needed or not.
2.13.9 The conversion recipe between the two forms, and the cases where only one is practical.
       `[PROVE]`
2.13.10 Memo key encodings: `int[n]`, `int[n][m]`, `int[n][1<<k]`, `HashMap<Long,Integer>` with
        packed keys, `HashMap<Record,Integer>`. `[NUM]`
2.13.11 The "not computed" sentinel bug: −1 as a sentinel when −1 is a valid answer. `[TRAP]`
2.13.12 Iteration-order derivation: every state must be computed before it is read; how to read the
        order off the recurrence's index deltas. `[PROVE]`
2.13.13 Space optimization: full table → rolling two rows → one row; and the direction reversal that
        the one-row form requires. `[PROVE]`
2.13.14 **0/1 vs unbounded knapsack is the capacity loop direction**: descending reuses each item
        once, ascending reuses it many times. The direction *is* the semantics. `[PROVE]` `[TRAP]`
2.13.15 Reconstructing the solution, not just the value: a parent/choice table, or re-deriving by
        walking the DP table backwards. `[BUILD]`
2.13.16 Counting DP vs optimizing DP vs feasibility DP — the three answer types and the operator each
        uses (`+`, `min`/`max`, `||`).
2.13.17 The 1-D family: climbing stairs, house robber I/II, min cost climbing stairs, decode ways,
        coin change (min coins), coin change II (count ways), word break, jump game, integer break,
        perfect squares, LIS, maximum subarray, delete and earn, longest arithmetic subsequence.
2.13.18 The knapsack family: 0/1, unbounded, bounded (binary splitting), subset sum, partition equal
        subset sum, target sum, last stone weight II, ones and zeroes (2-D capacity). `[PROVE]`
2.13.19 The grid family: unique paths I/II, minimum path sum, triangle, maximal square, dungeon game,
        cherry pickup, count paths with obstacles, minimum falling path.
2.13.20 The two-sequence/string family: LCS, edit distance (with the three operations as three
        transitions), longest common substring, shortest common supersequence, distinct
        subsequences, interleaving string, regular-expression matching, wildcard matching, palindromic
        subsequence, minimum insertions to make a palindrome. `[PROVE]`
2.13.21 Edit distance's three-way recurrence and the one-cell-per-operation reading. `[PROVE]`
       `[BUILD]`
2.13.22 The interval family: matrix chain multiplication, burst balloons, minimum cost to cut a
        stick, palindrome partitioning II, strange printer, remove boxes — with the "iterate by
        interval length" order. `[PROVE]`
2.13.23 The bitmask/subset family: travelling salesman, shortest path visiting all nodes, partition
        to k subsets, assignment problem, "number of ways to wear different hats", counting bits
        over subsets. `[NUM]`
2.13.24 Submask enumeration (`for (int s = m; s > 0; s = (s - 1) & m)`) and its total O(3ⁿ) cost over
        all masks. `[PROVE]` `[NUM]` `[RESEARCH]`
2.13.25 The digit-DP family: count numbers with a property up to N, with the (position, tight, state)
        signature. `[RESEARCH]` `[BUILD]`
2.13.26 The tree-DP family, cross-referenced to §2.9.15.
2.13.27 The DAG-DP family: longest path in a DAG, counting paths, longest increasing path in a matrix
        (memoized DFS). `[PROVE]`
2.13.28 The state-machine family: best time to buy and sell stock I–IV and with cooldown/fee, as one
        template with a state count. `[PROVE]` `[BUILD]`
2.13.29 The probability/expectation family: knight probability, new 21 game, soup servings.
2.13.30 The game-theory family: stone game I–III, predict the winner, Nim — minimax DP and the
        Sprague–Grundy theorem named. `[RESEARCH]`
2.13.31 Pseudo-polynomial complexity: knapsack's O(nW) is exponential in the *bit length* of W, which
        is why knapsack is NP-hard and the DP is not a contradiction. `[PROVE]` `[TRAP]`
2.13.32 DP optimizations named with their preconditions: divide-and-conquer optimization (monotone
        opt), Knuth optimization (quadrangle inequality), convex hull trick / Li Chao tree,
        monotonic-deque optimization, matrix exponentiation for linear recurrences, SOS DP.
        `[RESEARCH]`
2.13.33 The DP debugging procedure: print the table, check base cases, check one hand-computed cell,
        check the answer's location. `[DRILL]`
2.13.34 Recognising DP from phrasing: "count the number of ways", "minimum/maximum cost", "is it
        possible to reach", "longest/shortest subsequence" — and the anti-signal (a greedy proof
        exists, or the state space is too big).

*(34 leaves)*

## §2.14 Greedy

2.14.1 Definition: commit to the locally best choice, never reconsider.
2.14.2 The correctness obligation: greedy is correct **only** with a proof. Two proof techniques —
       the **exchange argument** and the **greedy-stays-ahead** induction. `[PROVE]`
2.14.3 The exchange argument, worked: interval scheduling by earliest end time. Take any optimal
       solution, swap its first interval for the greedy one, show it is no worse. `[PROVE]`
2.14.4 Greedy-stays-ahead, worked: Dijkstra's frontier, or the coin-change-with-canonical-denominations
       argument. `[PROVE]`
2.14.5 The matroid connection: greedy is optimal on exactly the matroids, which is why Kruskal works.
       `[PROVE]` `[RESEARCH]`
2.14.6 Where greedy provably works: interval scheduling (earliest end), fractional knapsack (value
       density), Huffman coding, Kruskal and Prim MST, Dijkstra, minimum platforms, gas station,
       jump game (furthest reach), task assignment by sorting, minimum arrows, candy distribution,
       job sequencing with deadlines.
2.14.7 Where greedy provably fails, with the counterexample for each: 0/1 knapsack, coin change on
       {1,3,4} for 6 (4+1+1 = 3 coins vs 3+3 = 2), longest path, TSP, set cover (though greedy is a
       ln n approximation). `[PROVE]` `[NUM]`
2.14.8 **Greedy that passes the samples is the most common wrong answer in interviews.** Say out loud
       that you are checking validity, try to construct a counterexample, and fall back to DP.
       `[TRAP]`
2.14.9 The "sort by what" question as the whole of most greedy problems, with the five common keys:
       end time, start time, ratio/density, deadline, and a pairwise-comparison order. `[PROVE]`
2.14.10 Pairwise-exchange-derived comparators: "sort by `a+b` vs `b+a`", "sort by
        `min(a.deadline, b.deadline)`", "boats to save people". `[PROVE]`
2.14.11 Greedy with a heap: the "regret" pattern — take greedily, then undo the worst choice when it
        becomes infeasible (course schedule III, IPO, maximum performance of a team). `[PROVE]`
2.14.12 Greedy on strings: remove k digits (monotonic stack), smallest subsequence of distinct
        characters, reorganize string, partition labels.
2.14.13 Greedy + binary search hybrids, and greedy as a *feasibility predicate* inside binary search
        on the answer (§2.7.2). `[PROVE]`
2.14.14 Approximation guarantees in one paragraph: set cover ln n, vertex cover 2×, TSP with the
        triangle inequality 2× (and Christofides 1.5×). `[NUM]` `[RESEARCH]`
2.14.15 Greedy vs DP decision procedure, stated as three questions.

*(15 leaves)*

## §2.15 Graph algorithms

2.15.1 The selection table: need → algorithm → cost → precondition. Unweighted shortest path (BFS,
       O(V+E)); non-negative weights (Dijkstra, O(E log V)); negative weights (Bellman–Ford, O(VE));
       all pairs (Floyd–Warshall O(V³), Johnson O(VE log V)); dependency order (Kahn/DFS, O(V+E));
       components (DFS/BFS/DSU); MST (Kruskal O(E log E), Prim O(E log V)); max flow (Dinic
       O(V²E)); matching (Hopcroft–Karp O(E√V)). `[NUM]`
2.15.2 **Topological sort, Kahn's algorithm**: in-degree array, queue of zero-in-degree vertices,
       decrement on removal. `[PROVE]` `[BUILD]`
2.15.3 **Kahn doubles as cycle detection**: if fewer than V vertices are emitted, a cycle exists.
       `[PROVE]`
2.15.4 Topological sort by DFS: push on post-visit, reverse the list. Why the reversal is required.
       `[PROVE]`
2.15.5 Lexicographically smallest topological order via a priority queue instead of a queue.
2.15.6 Unique-topological-order test (the order is unique iff it forms a Hamiltonian path in the
       DAG). `[PROVE]` `[RESEARCH]`
2.15.7 Topological-sort problem family: course schedule I/II, alien dictionary, minimum height trees
       (peel leaves), parallel courses, sequence reconstruction, sort items by groups.
2.15.8 DAG longest/shortest path in O(V+E) by processing in topological order — including negative
       weights, which Dijkstra cannot do. `[PROVE]`
2.15.9 **Dijkstra**: the frontier heap, the `dist[]` array, the finalize-on-pop rule, and the stale-
       entry skip. `[PROVE]` `[BUILD]`
2.15.10 **Dijkstra is wrong with negative edges** — it finalizes a vertex on pop, assuming no cheaper
        path can appear. Show the three-vertex counterexample. `[TRAP]` `[PROVE]`
2.15.11 Dijkstra complexity by frontier: binary heap O((V+E) log V), Fibonacci heap O(E + V log V),
        array O(V²) (better on dense graphs), bucket/dial queue O(E + VC) for small integer weights.
        `[NUM]` `[PROVE]`
2.15.12 Dijkstra variants: k-shortest paths, path with maximum probability, minimum effort path,
        cheapest flight within k stops (why plain Dijkstra needs a state extension), network delay
        time, swim in rising water, path with minimum maximum edge.
2.15.13 State-extended Dijkstra: `dist[node][extraState]` for fuel, stops, discounts, or parity.
        `[PROVE]` `[TRAP]`
2.15.14 **Bellman–Ford**: V−1 rounds of relaxing every edge; the Vth round detecting a negative
        cycle. Why V−1 rounds suffice. `[PROVE]` `[BUILD]`
2.15.15 Bellman–Ford applications: currency arbitrage, negative-cycle detection, constraint systems
        (difference constraints), and the early-exit optimization.
2.15.16 SPFA (queue-based Bellman–Ford) and its O(VE) worst case despite good average behaviour.
        `[RESEARCH]`
2.15.17 **Floyd–Warshall**: the three nested loops with `k` **outermost**, and why the loop order is
        the correctness condition, not a style choice. `[PROVE]` `[TRAP]` `[BUILD]`
2.15.18 Floyd–Warshall extensions: transitive closure, minimax path, negative-cycle detection on the
        diagonal, path reconstruction via a `next[][]` matrix.
2.15.19 Johnson's algorithm: reweight with Bellman–Ford potentials, then run Dijkstra from each
        vertex. `[PROVE]` `[RESEARCH]`
2.15.20 **MST, Kruskal**: sort edges, union-find to reject cycles. `[PROVE]` `[BUILD]`
2.15.21 **MST, Prim**: grow one tree with a heap-ordered frontier. `[PROVE]` `[BUILD]`
2.15.22 The **cut property** and the **cycle property** as the two lemmas that prove both. `[PROVE]`
2.15.23 MST uniqueness, minimum bottleneck spanning tree, second-best MST, Borůvka's algorithm, and
        maximum spanning tree by negating weights. `[RESEARCH]`
2.15.24 MST problem family: connecting cities with minimum cost, min cost to connect all points
        (complete graph → Prim beats Kruskal), optimize water distribution, critical and
        pseudo-critical edges.
2.15.25 **SCC, Tarjan**: one DFS, `low`-link values, an on-stack flag. `[PROVE]` `[BUILD]`
        `[RESEARCH]`
2.15.26 **SCC, Kosaraju**: DFS for finish order, transpose, DFS again. `[PROVE]` `[BUILD]`
2.15.27 The condensation graph is a DAG — the fact that makes SCC useful. `[PROVE]`
2.15.28 Bridges and articulation points via `low`-link, with the strict-vs-non-strict inequality that
        distinguishes them, and the root special case. `[PROVE]` `[TRAP]` `[RESEARCH]`
2.15.29 Critical connections in a network as the bridge-finding problem in interview clothing.
2.15.30 Eulerian path and circuit: the degree conditions (directed and undirected) and Hierholzer's
        algorithm. Reconstruct itinerary as the canonical problem. `[PROVE]` `[BUILD]`
2.15.31 Hamiltonian path as NP-complete, and the bitmask DP that solves it for n ≤ 20. `[PROVE]`
2.15.32 2-SAT via implication graph + SCC, named with its shape. `[RESEARCH]`
2.15.33 Max flow: the Ford–Fulkerson framework, residual graphs, augmenting paths, Edmonds–Karp
        O(VE²), Dinic O(V²E), and the **max-flow min-cut theorem**. `[PROVE]` `[RESEARCH]`
2.15.34 Bipartite matching via max flow, König's theorem, Hopcroft–Karp, and the Hungarian algorithm
        for the assignment problem. `[RESEARCH]`
2.15.35 Minimum vertex cover / maximum independent set on bipartite graphs via matching. `[PROVE]`
        `[RESEARCH]`
2.15.36 Graph colouring: greedy bound Δ+1, 2-colouring as bipartiteness, and 3-colouring as
        NP-complete. `[PROVE]`
2.15.37 Grid-graph specialisations: BFS/DFS on grids, and when the grid structure permits an O(mn)
        DP instead of a graph search. `[PROVE]`
2.15.38 Functional graphs (each node has exactly one out-edge): cycle finding, "the tortoise and hare
        on an array", and rho-shaped structure. `[PROVE]`
2.15.39 Graph problems that are really something else: "course schedule" (topo), "clone graph"
        (traversal + map), "evaluate division" (weighted union-find or DFS), "accounts merge"
        (DSU), "redundant connection" (DSU), "network delay" (Dijkstra), "cheapest flights"
        (Bellman–Ford by rounds). `[DRILL]`

*(39 leaves)*

## §2.16 Union-find (disjoint set union)

2.16.1 The abstract operations: `find(x)` → representative, `union(a,b)` → merge, `connected(a,b)`.
2.16.2 The forest-of-parent-pointers representation, and the naive O(n) worst case without
       optimizations. `[PROVE]`
2.16.3 **Path compression** in `find`: point every node on the path at the root. Recursive
       one-liner and the iterative two-pass form. `[BUILD]`
2.16.4 Path halving and path splitting as the cheaper single-pass variants. `[RESEARCH]`
2.16.5 **Union by rank** and **union by size**: attach the smaller tree beneath the larger. Why they
       differ and why either bounds height at O(log n) alone. `[PROVE]`
2.16.6 Both together give O(α(n)) amortized, α = inverse Ackermann < 5 for any n ≤ 2^65536 — treat as
       effectively constant, but know it is not O(1). `[PROVE]` `[NUM]` `[TRAP]`
2.16.7 Tarjan's lower bound: Θ(α(n)) is optimal for this problem in the pointer-machine model.
       `[PROVE]` `[RESEARCH]`
2.16.8 Component-count maintenance (decrement on a successful union) as the free extra.
2.16.9 Size-per-component maintenance, and "largest component size" queries.
2.16.10 **Union-find cannot delete edges** and cannot answer path queries — it answers "same set?"
        only. `[TRAP]`
2.16.11 Offline dynamic connectivity by processing deletions in reverse; and the link-cut tree /
        Euler-tour tree as the real answers. `[RESEARCH]`
2.16.12 Weighted / potential union-find: store a value along the parent edge for "evaluate division"
        and "equations possible". `[PROVE]` `[BUILD]`
2.16.13 Union-find on a grid with coordinate flattening and virtual nodes (the "surrounded regions"
        and "number of islands II" technique). `[BUILD]`
2.16.14 Bipartiteness/parity union-find (nodes doubled, or a parity field) for "possible bipartition"
        and "satisfiability of equality equations". `[PROVE]`
2.16.15 Union-find problem family: number of connected components, redundant connection I/II,
        accounts merge, most stones removed, satisfiability of equality equations, number of islands
        II, smallest string with swaps, minimize malware spread, longest consecutive sequence (the
        DSU solution), regions cut by slashes, checking existence of edge-length-limited paths.
2.16.16 Kruskal's MST as the flagship application. `[X-REF §2.15.20]`
2.16.17 Union-find vs BFS/DFS for connectivity: DSU wins on a *stream* of edges and on repeated
        queries; DFS wins when you need the actual components or paths. `[PROVE]`

*(17 leaves)*

## §2.17 Tries

2.17.1 The structure: a tree whose edges are labelled by characters; a node's identity is the path
       from the root.
2.17.2 Node representations: `TrieNode[26]` dense array vs `HashMap<Character,TrieNode>` vs a sorted
       small array — and the alphabet-size decision rule. `[NUM]`
2.17.3 `isEnd` (or a count/value field) as the "a word terminates here" marker, and why a separate
       terminator character is the alternative.
2.17.4 Insert, search, and `startsWith` are all Θ(L) in the key length — **independent of the number
       of stored words**. `[PROVE]`
2.17.5 The comparison against a hash set: hash set is O(L) too (hashing reads the whole key), so the
       trie's win is *prefix* operations, not point lookups. `[TRAP]` `[PROVE]`
2.17.6 Memory cost: 26 references × 4–8 bytes per node = 104–208 B per node before payload; the
       arithmetic for a 10⁵-word dictionary. `[NUM]` `[PROVE]`
2.17.7 Deletion: reference counting or a recursive prune, and the "shared prefix" hazard. `[TRAP]`
2.17.8 Applications: autocomplete, spell check, longest common prefix, word break, replace words,
       IP routing (longest prefix match), T9 prediction, dictionary compression.
2.17.9 **Trie-pruned DFS**: Word Search II walks the grid and the trie together, so a dead prefix
       kills the branch immediately. This is the reason the problem is tractable. `[PROVE]` `[BUILD]`
2.17.10 Trie with counts for "count words with prefix" and "sum of prefix scores".
2.17.11 **Binary / bitwise trie** over the 32 bits of an int: maximum XOR pair in O(32n), maximum XOR
        with a query, count pairs with XOR < k. `[PROVE]` `[BUILD]`
2.17.12 Compressed trie / radix tree / PATRICIA trie: collapse single-child chains; the memory win
        and the split-on-insert complexity. `[RESEARCH]`
2.17.13 Ternary search tree and DAWG/directed acyclic word graph as the two space-optimized cousins.
        `[RESEARCH]`
2.17.14 Suffix trie → suffix tree → suffix array, as the escalation for substring queries.
        `[X-REF §3.15]`
2.17.15 Aho–Corasick as "a trie plus KMP failure links" for multi-pattern matching. `[X-REF §3.15]`
2.17.16 Trie problem family: implement trie, design add-and-search-words (with `.` wildcards), word
        break, replace words, longest word in dictionary, stream of characters, maximum XOR,
        concatenated words, palindrome pairs, camelcase matching.

*(16 leaves)*

## §2.18 Bit manipulation

2.18.1 The operators: `&`, `|`, `^`, `~`, `<<`, `>>` (arithmetic), `>>>` (logical) — and the one that
       does not exist (`<<<`).
2.18.2 Two's complement: `-x == ~x + 1`; the asymmetric range `[-2³¹, 2³¹−1]`. `[NUM]` `[PROVE]`
2.18.3 `>>` vs `>>>` on negative numbers, and why `>>>` is required for `(lo + hi) >>> 1`. `[TRAP]`
2.18.4 Shift counts are taken mod 32 for `int` and mod 64 for `long`: `1 << 32 == 1`. `[TRAP]`
       `[NUM]`
2.18.5 `1 << 31` overflows to `Integer.MIN_VALUE`; use `1L << 31` for a 32-bit mask. `[TRAP]`
2.18.6 The five one-liners: test bit `(x >> i) & 1`, set `x | (1 << i)`, clear `x & ~(1 << i)`,
       toggle `x ^ (1 << i)`, extract lowest set bit `x & -x`. `[NUM]`
2.18.7 Clear the lowest set bit `x & (x − 1)`; Brian Kernighan's popcount loop and its O(popcount)
       cost. `[PROVE]`
2.18.8 Power-of-two test `x > 0 && (x & (x − 1)) == 0`. `[PROVE]`
2.18.9 Round up to the next power of two: the shift-or cascade, or
       `Integer.highestOneBit`/`numberOfLeadingZeros`. `[NUM]` `[BUILD]`
2.18.10 XOR properties: `x^x = 0`, `x^0 = x`, commutative, associative, self-inverse — the basis of
        every "find the single number" trick. `[PROVE]`
2.18.11 Single number I (XOR all), II (bit counts mod 3, or the two-mask automaton), III (XOR then
        split by the lowest set bit). `[PROVE]`
2.18.12 Missing number by XOR of indices and values. `[PROVE]`
2.18.13 XOR prefix arrays and "count subarrays with XOR = k". `[PROVE]`
2.18.14 Bitmask as a set: subset enumeration `for (int m = 0; m < (1<<n); m++)`, membership,
        union/intersection/difference, cardinality via `Integer.bitCount`. `[BUILD]`
2.18.15 Submask enumeration and the O(3ⁿ) total. `[PROVE]` `[NUM]`
2.18.16 Gray code construction `i ^ (i >> 1)` and its adjacency property. `[PROVE]`
2.18.17 Bit tricks for arithmetic: `x << 1` doubling, `x >> 1` halving (and the negative-rounding
        difference from `/2`), `x & 1` parity, swapping without a temp (and why not to). `[TRAP]`
2.18.18 `Integer` utilities restated as the answer to most of the above: `bitCount`, `reverse`,
        `highestOneBit`, `lowestOneBit`, `numberOfLeadingZeros`, `numberOfTrailingZeros`,
        `rotateLeft`, `toBinaryString`, `parseInt(s, 2)`. `[X-REF 03]`
2.18.19 `BitSet` when the universe exceeds 64 bits: one bit per element, `and`/`or`/`xor`/`andNot`,
        `cardinality`, `nextSetBit`, `stream()`. `[NUM]` `[X-REF 02]`
2.18.20 Sieve on a `BitSet` or a `long[]` as the memory-efficient form. `[NUM]`
2.18.21 Bitboards and the 64-bit-board pattern (chess, N-queens, sudoku) as the "bitmask as
        accelerator" family.
2.18.22 Bit-manipulation problem family: number of 1 bits, counting bits 0..n (DP on `i>>1`),
        reverse bits, single number I–III, missing number, sum of two integers without `+`, maximum
        XOR, bitwise AND of a number range, subsets via bitmask, Gray code, UTF-8 validation,
        divide two integers without division.
2.18.23 When bit tricks are the wrong answer: readability, and the fact that the JIT already emits
        the fast form for `/2` and `%2` on unsigned-safe values. `[TRAP]` `[X-REF 06]`

*(23 leaves)*

## §2.19 Math and number theory for algorithm rounds

2.19.1 GCD by the Euclidean algorithm, its O(log min(a,b)) bound, and `lcm(a,b) = a/g*b` (divide
       first to avoid overflow). `[PROVE]` `[NUM]` `[TRAP]`
2.19.2 Extended Euclid, Bézout coefficients, and the modular inverse. `[PROVE]` `[BUILD]`
2.19.3 Modular arithmetic rules, `1_000_000_007` as the conventional modulus, and the "mod after
       every operation" discipline; `(a - b + MOD) % MOD` for subtraction. `[NUM]` `[TRAP]`
2.19.4 Fast modular exponentiation by squaring, O(log e). `[PROVE]` `[BUILD]`
2.19.5 Fermat's little theorem for inverses when the modulus is prime; Euler's theorem otherwise.
       `[PROVE]`
2.19.6 Primality: trial division to √n, the 6k±1 optimization, Miller–Rabin (deterministic bases for
       64-bit), and Fermat pseudoprimes. `[NUM]` `[RESEARCH]`
2.19.7 Sieve of Eratosthenes O(n log log n), the linear sieve, and the smallest-prime-factor sieve
       for O(log n) factorization. `[PROVE]` `[NUM]` `[BUILD]`
2.19.8 Integer factorization: trial division, Pollard's rho, and the divisor-pairing √n bound.
       `[RESEARCH]`
2.19.9 Divisor and totient functions, and counting divisors from the prime factorization. `[PROVE]`
2.19.10 Combinatorics: nCr by Pascal's triangle DP, by factorials with modular inverse, and the
        multiplicative form that avoids overflow. `[NUM]` `[BUILD]`
2.19.11 Catalan numbers and the problems they count (balanced parens, BST shapes, triangulations,
        Dyck paths). `[NUM]` `[PROVE]`
2.19.12 Inclusion–exclusion and the pigeonhole principle, each with the problem type it solves.
        `[PROVE]`
2.19.13 Stars and bars for "count the ways to distribute". `[PROVE]`
2.19.14 Chinese remainder theorem in one paragraph. `[RESEARCH]`
2.19.15 Base conversion, digit extraction, digit sum, and palindromic-number handling.
2.19.16 Integer square root without floating point (binary search or Newton), and why
        `(int)Math.sqrt(n)` is unsafe at the boundary. `[TRAP]` `[PROVE]`
2.19.17 Floating-point hazards in algorithm code: `0.1 + 0.2 != 0.3`, epsilon comparison, NaN
        ordering, and the "use integers or `BigDecimal`" rule. `[TRAP]` `[X-REF 03]`
2.19.18 `BigInteger`/`BigDecimal` when the problem demands exactness, and their non-constant
        arithmetic cost. `[X-REF 03]`
2.19.19 Matrix exponentiation for linear recurrences and for counting paths of fixed length.
        `[BUILD]`
2.19.20 Geometry minimum: cross product sign for orientation, dot product for projection, distance
        without `sqrt`, convex hull by Andrew's monotone chain O(n log n), line intersection, point
        in polygon, closest pair of points by divide and conquer O(n log n). `[PROVE]` `[RESEARCH]`
2.19.21 Random and probabilistic tools: `Random`/`ThreadLocalRandom`, Fisher–Yates shuffle (and the
        biased loop that everyone writes instead), reservoir sampling, random pick with weights via
        prefix sums + binary search. `[PROVE]` `[TRAP]` `[BUILD]`
2.19.22 Rejection sampling ("implement rand10 from rand7") and the expected-iteration arithmetic.
        `[PROVE]` `[NUM]`
2.19.23 Randomized algorithms in the interview: randomized quickselect, treap, skip list, Karger's
        min cut, Monte Carlo vs Las Vegas. `[PROVE]`
2.19.24 The math problem family: happy number, reverse integer with overflow, palindrome number,
        excel column, roman numerals, pow(x,n), sqrt(x), divide two integers, fraction to recurring
        decimal, count primes, ugly numbers, nth digit, angle of a clock.

*(24 leaves)*

## §2.20 Design-a-structure questions

2.20.1 The genre: an API is specified, and the answer is a *composition* of two structures where
       each covers the other's weak operation.
2.20.2 **LRU cache**: `HashMap` + doubly-linked list, O(1) get and put; the `LinkedHashMap` +
       `removeEldestEntry` shortcut and its `accessOrder` flag. `[BUILD]` `[X-REF 02]` `[X-REF 15]`
2.20.3 **LFU cache**: frequency buckets of linked lists, `minFreq` tracking, O(1) amortized.
       `[BUILD]`
2.20.4 **Insert/delete/getRandom in O(1)**: `ArrayList` + index `HashMap`, with swap-with-last on
       removal; the duplicates-allowed variant. `[BUILD]` `[PROVE]`
2.20.5 **Min stack** / max stack / min queue. `[BUILD]`
2.20.6 **Stack using queues** and **queue using stacks**, with the amortized argument. `[BUILD]`
2.20.7 **Median finder** (two heaps) and its sliding-window variant. `[BUILD]`
2.20.8 **Trie-based** autocomplete and search-suggestions-system. `[BUILD]`
2.20.9 **Hit counter** / rate limiter: circular buffer of buckets, or a `TreeMap`/deque of
       timestamps; fixed window vs sliding window vs token bucket. `[X-REF 22]`
2.20.10 **Time-based key-value store**: `HashMap<String, List<(t, v)>>` + binary search on t.
        `[BUILD]`
2.20.11 **Snapshot array**: per-index list of (snapId, value) + binary search. `[BUILD]`
2.20.12 **Range module** / **my calendar**: `TreeMap<Integer,Integer>` of disjoint intervals.
        `[BUILD]`
2.20.13 **Skiplist** and **randomized set** as the randomized designs. `[BUILD]`
2.20.14 **Iterator design**: peeking iterator, flatten nested list, flatten 2-D vector, BST iterator,
        zigzag iterator — the "lazy, O(h) space" contract. `[BUILD]`
2.20.15 **Tic-tac-toe / game state** design with O(1) win checks via row/col/diagonal counters.
2.20.16 **Twitter feed** (heap merge of k timelines) and **leaderboard** (`TreeMap` or
        Fenwick by score) as the two that bridge into system design. `[X-REF 22]`
2.20.17 **Word dictionary with wildcards**, **stream of characters**, **first unique number** as the
        trie/deque/linked-hash composites.
2.20.18 Bloom filter as the probabilistic membership structure: k hashes, m bits, the false-positive
        formula `(1 − e^(−kn/m))^k`, and the no-deletion limitation. `[NUM]` `[PROVE]` `[X-REF 22]`
2.20.19 The composition catalogue: which pair of structures covers which weakness — a table of
        "need X in O(1) and Y in O(log n)" → the combination.
2.20.20 How to answer the genre: restate the API, state the target complexity per operation, name the
        weakness of the obvious single structure, then compose.

*(20 leaves)*

## §2.21 Pattern recognition and problem-solving procedure

2.21.1 The signal table (carried forward from the current guide and extended): sorted array + pair →
       two pointers; contiguous subarray with a constraint → sliding window; "top k" → size-k heap;
       "kth smallest" → heap or binary search on value; next greater/smaller/span/histogram →
       monotonic stack; window extremum → monotonic deque; unweighted shortest path → BFS;
       "generate all" → backtracking; "count the ways"/"min cost"/"can you reach" → DP; overlapping
       intervals → sort + sweep; prefix/autocomplete → trie; dynamic connectivity → union-find;
       prerequisites → topological sort; "in-place O(1) space" → index-as-hash/swap/reverse; cycle
       in a list or a functional mapping → Floyd; "answer is a number, feasibility monotonic" →
       binary search on the answer; palindrome → expand from centre; "values in 1..n" → cyclic sort;
       "XOR"/"odd one out" → bit tricks; "k lists" → k-way merge; "median of a stream" → two heaps;
       "range sum with updates" → Fenwick/segment tree.
2.21.2 The constraint table: n and the complexity it permits (§1.4.15 restated as a decision step).
2.21.3 **Trap: anchoring on the first pattern that fits.** Confirm the constraints support it before
       coding. `[TRAP]`
2.21.4 The seven-step procedure: clarify → examples (including edge cases) → brute force with its
       complexity → identify the waste → apply the pattern → state the new complexity → code →
       test by hand.
2.21.5 Why brute force first is not a waste: it fixes the semantics, gives a baseline, and is the
       fallback if the optimization fails. `[TRAP]`
2.21.6 The "identify the waste" step as the actual optimization move: recomputation → memo/prefix;
       rescanning → two pointers/window; re-sorting → one sort; re-searching → hash/index map;
       re-deriving order → sort once; unbounded search → pruning or monotonicity.
2.21.7 Clarifying questions worth asking every time: input size, value range, duplicates, sortedness,
       mutability, empty/single-element input, and what to return when there is no answer.
2.21.8 Edge-case checklist: empty, one element, all equal, all distinct, already sorted, reverse
       sorted, negatives, zeros, overflow boundary, maximum size. `[DRILL]`
2.21.9 Stating complexity out loud, for time and auxiliary space, before writing code.
2.21.10 Testing by hand: pick the smallest input that exercises the interesting branch, trace it,
        and check the returned value — not the printed trace. `[DRILL]`
2.21.11 What to do when stuck: shrink the problem, solve n=1 and n=2, look for the invariant,
        consider the reverse direction, consider sorting, consider what a hash map would buy.
2.21.12 The "two solutions" answer shape: the O(n²) you can write in two minutes, and the O(n) you
        argue toward — offering both is a stronger signal than jumping to one.
2.21.13 Problem-family index: for each of the ~25 patterns, the 5–10 canonical problems, so the
        reader can self-test coverage. `[DRILL]`

*(13 leaves)*

## §2.22 Java-specific pitfalls in coding rounds

2.22.1 `int` overflow in sums, products, and midpoints — the four places it bites and the `long`
       discipline. `[TRAP]` `[NUM]`
2.22.2 `a - b` in comparators. `[TRAP]`
2.22.3 `Integer` `==` comparison beyond the cache; `equals` or `intValue` instead. `[TRAP]`
       `[X-REF 03]`
2.22.4 `list.remove(int)` vs `list.remove(Object)` on a `List<Integer>`. `[TRAP]` `[X-REF 02]`
2.22.5 `map.get` returning `null` and auto-unboxing to an NPE. `[TRAP]`
2.22.6 `HashMap` iteration order is unspecified and changes with capacity — never rely on it.
       `[TRAP]`
2.22.7 `HashSet<int[]>` never deduplicates (identity `hashCode`); use `List<Integer>`, a record, or a
       string key. `[TRAP]`
2.22.8 `PriorityQueue` iteration is not sorted. `[TRAP]`
2.22.9 `ArrayDeque` forbids null; `LinkedList` does not. `[TRAP]`
2.22.10 `Arrays.asList(intArray)` gives a one-element `List<int[]>`. `[TRAP]` `[X-REF 02]`
2.22.11 `Arrays.fill(grid, row)` aliases one array into every row. `[TRAP]`
2.22.12 `String.substring` is O(k) since Java 7 — an inner-loop substring makes the solution O(n²).
        `[TRAP]` `[VERSION-TRAP]`
2.22.13 `String +=` in a loop. `[TRAP]`
2.22.14 `split`/`replaceAll`/`matches` are regex-backed. `[TRAP]`
2.22.15 `char` + `int` promotes to `int`; `'a' + 1` is `98`, not `'b'`. `[TRAP]`
2.22.16 `%` on negatives. `[TRAP]`
2.22.17 `Math.abs(Integer.MIN_VALUE)` is negative. `[TRAP]`
2.22.18 `Arrays.sort(int[])` is unstable and adversarially quadratic; `Arrays.sort(Integer[])` is
        stable TimSort. `[TRAP]`
2.22.19 Modifying a collection while iterating → `ConcurrentModificationException`; the four legal
        alternatives. `[TRAP]` `[X-REF 02]`
2.22.20 Deep recursion → `StackOverflowError` at ~10⁴ frames. `[TRAP]`
2.22.21 Allocation inside a hot loop (new `int[]`, boxing, `substring`) as the constant-factor killer
        that turns an accepted solution into a TLE. `[NUM]`
2.22.22 `Scanner` vs `BufferedReader` for large input. `[NUM]`
2.22.23 `static` mutable state across test cases — the "works locally, fails on the second test"
        bug. `[TRAP]`
2.22.24 Returning `int` where the answer needs `long`, and the signature you should have asked about.
        `[TRAP]`

*(24 leaves)*

---

**PART 2 total: 426 leaves**

---

# PART 3 — UNDER THE HOOD

## §3.1 Amortization, proved four ways

3.1.1 The dynamic table formalised: `size`, `capacity`, growth factor g, and the cost model
      (1 per write, `capacity` per reallocation). `[NUM]`
3.1.2 Aggregate proof for g = 2: total copy cost over n appends is 1 + 2 + 4 + … + 2^⌊log n⌋ < 2n,
      so amortized ≤ 3. `[PROVE]` `[NUM]`
3.1.3 Accounting proof: charge 3 per append — 1 to write, 1 to eventually copy this element, 1 to
      copy an older element. Show the credit invariant never goes negative. `[PROVE]` `[NUM]`
3.1.4 Potential proof: Φ = 2·size − capacity; verify Φ ≥ 0 after every doubling and that ĉ = 3.
      `[PROVE]` `[NUM]`
3.1.5 The general growth factor g: amortized copy cost per element is g/(g−1), so g = 2 → 2,
      g = 1.5 → 3, g = 1.1 → 11. `[PROVE]` `[NUM]`
3.1.6 The memory-reuse argument for g < 2: with g = 2 the freed blocks can never be coalesced into
      the next request; with g ≤ φ ≈ 1.618 they can. This is why `ArrayList` uses 1.5×.
      `[PROVE]` `[RESEARCH]`
3.1.7 Growth policies across languages, for contrast: Java `ArrayList` 1.5× (`oldCapacity +
      (oldCapacity >> 1)`), Java `Vector` 2× (or `capacityIncrement`), C++ `std::vector` 2× (libstdc++)
      / 1.5× (MSVC), Python `list` ~1.125× with a floor, Go `slice` 2× below 256 then 1.25×.
      `[NUM]` `[RESEARCH]`
3.1.8 Shrink policy and the thrashing proof: shrinking at half-full makes alternating add/remove
      Θ(n) per operation; shrinking at quarter-full restores amortized O(1). Prove with the
      potential function Φ = |2·size − capacity| (grow phase) / capacity/2 − size (shrink phase).
      `[PROVE]` `[NUM]`
3.1.9 Java's `ArrayList` never shrinks automatically — `remove` does not reduce capacity;
      `trimToSize` is manual. The leak shape this produces. `[TRAP]` `[X-REF 02]`
3.1.10 `ArraysSupport.newLength` and `SOFT_MAX_ARRAY_LENGTH = Integer.MAX_VALUE - 8` as the real
       ceiling, plus the `OutOfMemoryError: Requested array size exceeds VM limit`. `[SOURCE]`
       `[NUM]` `[X-REF 02]`
3.1.11 The binary-counter potential proof, in full, as the cleanest example of the method. `[PROVE]`
3.1.12 Union-find's amortized bound sketched here and proved in §3.11.
3.1.13 De-amortization: incremental resize (copy k old elements per new insert), and the bound it
       trades for (2× memory during the transition). `[PROVE]` `[RESEARCH]`
3.1.14 Why amortized bounds are unacceptable for a p99 latency SLO, and the three fixes: pre-size,
       de-amortize, or use a structure with worst-case bounds. `[X-REF 20]`

*(14 leaves)*

## §3.2 Hash table internals

3.2.1 The three components: hash function, compression to an index, collision resolution.
3.2.2 **Separate chaining**: expected chain length α; expected successful search 1 + α/2, expected
      unsuccessful 1 + α. `[PROVE]` `[NUM]`
3.2.3 The longest chain under uniform hashing is Θ(log n / log log n) with high probability — the
      balls-into-bins result behind Java's treeify threshold. `[PROVE]` `[NUM]` `[RESEARCH]`
3.2.4 The Poisson model for bin occupancy at α = 0.75, and the probability of a bin reaching 8
      (~6·10⁻⁸) — quoted from the `HashMap` javadoc's own table. `[SOURCE]` `[NUM]` `[X-REF 02]`
3.2.5 **Open addressing**: linear probing, quadratic probing, double hashing — the probe sequences
      and the load-factor ceilings each tolerates. `[NUM]`
3.2.6 Linear probing's clustering, and Knuth's expected-probe formulas ½(1 + 1/(1−α)²) for
      unsuccessful search. `[PROVE]` `[NUM]` `[RESEARCH]`
3.2.7 Cache behaviour: linear probing is the fastest in practice despite the worse theory, because
      probes stay in one cache line. `[PROVE]` `[X-REF 06]`
3.2.8 Deletion under open addressing: tombstones vs backward-shift deletion, and the "lookup breaks
      after delete" bug when tombstones are omitted. `[TRAP]` `[PROVE]`
3.2.9 Robin Hood hashing: displace the richer probe, bounding variance. `[RESEARCH]`
3.2.10 Cuckoo hashing: two tables, two hash functions, worst-case O(1) lookup, amortized O(1) insert
       with a rebuild on a cycle. `[PROVE]` `[RESEARCH]`
3.2.11 Hopscotch hashing and Swiss-table/SIMD probing as the modern designs. `[RESEARCH]`
3.2.12 Java's `HashMap`, precisely: `DEFAULT_INITIAL_CAPACITY = 16`, `DEFAULT_LOAD_FACTOR = 0.75f`,
       `TREEIFY_THRESHOLD = 8`, `UNTREEIFY_THRESHOLD = 6`, `MIN_TREEIFY_CAPACITY = 64`,
       `MAXIMUM_CAPACITY = 1 << 30`. `[NUM]` `[SOURCE]` `[X-REF 02]`
3.2.13 The `hash()` spread `h ^ (h >>> 16)` and why masking alone would discard the high bits.
       `[SOURCE]` `[PROVE]` `[X-REF 02]`
3.2.14 Power-of-two capacity, `tableSizeFor`, and index `= hash & (n − 1)`. `[SOURCE]` `[NUM]`
3.2.15 The lo/hi resize split: an element either stays at index `i` or moves to `i + oldCap`, decided
       by one bit — so resize is O(n) with no rehashing. `[SOURCE]` `[PROVE]` `[X-REF 02]`
3.2.16 Treeification into a red-black bin, `comparableClassFor`, and the O(log n) worst case it
       buys. `[X-REF 02]`
3.2.17 The Java 7 concurrent-resize infinite loop (list reversal during transfer) and why Java 8's
       order-preserving split removed it — still not thread-safe. `[TRAP]` `[X-REF 05]`
3.2.18 Hash-flooding: the O(n²) construction attack, CVE-2011-4858 and VU#903934, and the
       mitigations (randomized seeds, SipHash, treeified bins, parameter-count limits). `[RESEARCH]`
       `[X-REF 13]`
3.2.19 Randomized/universal hashing as the principled defence, and why Java chose treeification
       instead (hash codes are part of the public contract and cannot be randomized). `[PROVE]`
       `[RESEARCH]`
3.2.20 Set-from-map: `HashSet` is a `HashMap` with a `PRESENT` dummy value — the memory consequence.
       `[NUM]` `[X-REF 02]`
3.2.21 Ordered hash maps: `LinkedHashMap`'s `before`/`after` overlay, `accessOrder`, and
       `removeEldestEntry` as the LRU hook. `[X-REF 02]` `[X-REF 15]`
3.2.22 Open-addressing in the JDK: `IdentityHashMap`'s interleaved key/value flat array with linear
       probing, `DEFAULT_CAPACITY = 32`. `[NUM]` `[X-REF 02]`
3.2.23 Rolling hashes as a different use of the same idea: polynomial hashing, the base and modulus
       choice, and collision probability 1/M per comparison. `[PROVE]` `[NUM]`
3.2.24 Double hashing for rolling hashes (two moduli) to make adversarial collisions impractical.
       `[RESEARCH]`
3.2.25 Hashing for memo keys: packing two ints into a long vs a record vs string concatenation — the
       cost comparison. `[NUM]`
3.2.26 What a hash table cannot do, restated as a design consequence: no order, no range, no
       predecessor, no bounded worst case without treeification.

*(26 leaves)*

## §3.3 Binary heap internals

3.3.1 The complete-tree-in-an-array representation, and why it wastes no space and needs no
      pointers. `[NUM]`
3.3.2 The index-arithmetic derivation for 0-based and 1-based layouts. `[PROVE]` `[NUM]`
3.3.3 `siftUp`: the loop, the "hole" optimization (move the hole, write the value once), and the
      invariant it preserves. `[SOURCE]` `[PROVE]`
3.3.4 `siftDown`: the loop, the choose-the-smaller-child step, and the invariant. `[SOURCE]`
      `[PROVE]`
3.3.5 Exact comparison counts: `siftUp` ≤ ⌊log₂n⌋, `siftDown` ≤ 2⌊log₂n⌋ — the factor of 2 that
      makes bottom-up construction cheaper than top-down. `[PROVE]` `[NUM]`
3.3.6 **`heapify` is Θ(n)**: Σ_{h=0}^{log n} (n/2^(h+1))·h = n·Σ h/2^(h+1) = n·1 = Θ(n), using
      Σ h/2^h = 2. Show the series. `[PROVE]` `[NUM]`
3.3.7 Bottom-up `siftDown` from index `(n >>> 1) - 1` down to 0 — the exact loop bound. `[SOURCE]`
      `[NUM]`
3.3.8 Average-case insertion is O(1), not O(log n): a random element ends up near the bottom.
      `[PROVE]` `[RESEARCH]`
3.3.9 The number of leaves is ⌈n/2⌉ and the height is ⌊log₂n⌋ — the two facts every heap proof uses.
      `[PROVE]` `[NUM]`
3.3.10 `poll` mechanics: move the last element to the root, shrink, `siftDown`; and why moving the
       *last* element (not a child) preserves completeness. `[PROVE]`
3.3.11 `removeAt(i)` and Java's `forgetMeNot` fix-up: when an element sifts *up* during a removal it
       can be missed by an in-progress iteration, so `PriorityQueue` records it. `[SOURCE]`
       `[TRAP]` `[X-REF 02]`
3.3.12 `PriorityQueue` growth: `DEFAULT_INITIAL_CAPACITY = 11`, then `< 64 ? 2n + 2 : 1.5n`.
       `[SOURCE]` `[NUM]` `[X-REF 02]`
3.3.13 Java's duplicated `siftUp`/`siftDown` pair (`siftUpComparable` and `siftUpUsingComparator`) as
       a deliberate monomorphisation for the JIT. `[SOURCE]` `[X-REF 06]`
3.3.14 Heapsort in detail: the in-place extract loop, why it is not stable, and why it loses to
       quicksort on real hardware (poor locality, 2 comparisons per level). `[PROVE]`
       `[X-REF 06]`
3.3.15 Bottom-up heapsort / Wegener's variant, which reduces comparisons to ~n log n. `[RESEARCH]`
3.3.16 d-ary heap analysis: height log_d n, `siftUp` O(log_d n), `siftDown` O(d·log_d n); optimal
       d ≈ 4 in practice for Dijkstra. `[PROVE]` `[NUM]` `[RESEARCH]`
3.3.17 Binomial heap: forest of binomial trees, O(log n) merge, and the binary-counter analogy.
       `[PROVE]` `[RESEARCH]`
3.3.18 Fibonacci heap: lazy consolidation, O(1) amortized insert and decrease-key, O(log n)
       delete-min, the potential function Φ = #trees + 2·#marked, and why the constants make it
       theoretical. `[PROVE]` `[RESEARCH]`
3.3.19 Pairing heap as the practical near-Fibonacci alternative. `[RESEARCH]`
3.3.20 Leftist and skew heaps: mergeable heaps with a simple invariant. `[RESEARCH]`
3.3.21 The mergeable-heap comparison table: insert, find-min, delete-min, decrease-key, merge for
       binary, binomial, Fibonacci, pairing, leftist. `[NUM]`
3.3.22 Indexed priority queue internals: `heap[]`, `pos[]`, `key[]`, and the three-array invariant
       that makes decrease-key O(log n). `[PROVE]` `[BUILD]`
3.3.23 Why `PriorityQueue.remove(Object)` is O(n) and what the indexed version fixes. `[PROVE]`
3.3.24 Heap vs balanced BST vs sorted array for a priority queue: the capability/cost table.

*(24 leaves)*

## §3.4 Balanced search trees

3.4.1 The problem: unbalanced BSTs degrade to O(n), and sorted insertion is the common case, not the
      adversarial one. `[PROVE]`
3.4.2 Rotations: left and right, the pointer rewiring, and the proof that a rotation preserves the
      BST invariant while changing height. `[PROVE]` `[BUILD]`
3.4.3 **AVL trees**: balance factor ∈ {−1,0,1}, the four rebalance cases (LL, LR, RL, RR),
      O(1) rotations per insert, O(log n) per delete. `[PROVE]` `[BUILD]`
3.4.4 AVL height bound: h ≤ 1.44 log₂(n+2) − 0.328, derived from the Fibonacci-shaped minimum-node
      recurrence N(h) = N(h−1) + N(h−2) + 1. `[PROVE]` `[NUM]`
3.4.5 **Red-black trees**: the five invariants (root black, leaves black-nil, no red-red, equal black
      height on all paths, every node red or black). `[NUM]`
3.4.6 Red-black height bound: h ≤ 2 log₂(n+1). `[PROVE]` `[NUM]`
3.4.7 `fixAfterInsertion`: the three cases (red uncle → recolour; black uncle triangle → rotate;
      black uncle line → rotate + recolour), with the case analysis. `[SOURCE]` `[PROVE]`
      `[X-REF 02]`
3.4.8 `fixAfterDeletion`: the four cases and the "double black" concept. `[SOURCE]` `[PROVE]`
3.4.9 AVL vs red-black: AVL is more rigidly balanced (faster lookups), red-black does fewer
      rotations (faster updates) — which is why `TreeMap` and `std::map` chose red-black and
      databases' in-memory indexes often choose AVL. `[PROVE]`
3.4.10 The 2-3 tree / 2-3-4 tree equivalence: a red-black tree *is* a 2-3-4 tree with red edges as
       "glue". This is the intuition that makes the case analysis memorable. `[PROVE]` `[RESEARCH]`
3.4.11 Left-leaning red-black trees (Sedgewick) as the simplified implementation. `[RESEARCH]`
3.4.12 **Treap**: BST on key, heap on a random priority; expected O(log n) with no rebalancing
       logic; split and merge as primitives. `[PROVE]` `[BUILD]`
3.4.13 **Splay tree**: move-to-root on access, O(log n) amortized (not worst case), and the
       potential-function proof; self-adjusting behaviour on skewed access patterns. `[PROVE]`
       `[RESEARCH]`
3.4.14 **Skip list**: probabilistic levels with p = 1/2, expected O(log n) search, expected 2n
       pointers, and why it is easier to make concurrent than a tree. `[PROVE]` `[NUM]` `[BUILD]`
3.4.15 Skip-list level distribution and the expected-height derivation. `[PROVE]` `[NUM]`
3.4.16 Scapegoat trees and weight-balanced trees, named for completeness. `[RESEARCH]`
3.4.17 **B-tree and B+ tree**: order/fanout, node = disk page, height log_B n, and why databases and
       filesystems use them instead of binary trees. `[PROVE]` `[NUM]` `[X-REF 09]`
3.4.18 B+ tree leaf linkage for range scans, and the fanout arithmetic for a 4 KB page with 8-byte
       keys (~200–500 children, so 3 levels indexes ~10⁸ rows). `[NUM]` `[PROVE]` `[X-REF 09]`
3.4.19 LSM trees vs B-trees in one paragraph, as the write-optimized alternative. `[X-REF 09]`
3.4.20 Order-statistic trees: augment with subtree size for O(log n) `kth` and `rank`. `[BUILD]`
3.4.21 Interval trees: augment with subtree max-endpoint for O(log n) stabbing queries. `[BUILD]`
3.4.22 The augmentation recipe: a value computable from a node's own fields plus its children's
       augmentations can be maintained through rotations in O(1). `[PROVE]`
3.4.23 `TreeMap` internals as the concrete instance: `Entry<K,V>` with `left`/`right`/`parent`/
       `color`, `getEntry`, `successor`, `buildFromSorted` (O(n) construction from sorted input),
       and the range-view classes. `[SOURCE]` `[X-REF 02]`
3.4.24 `TreeMap` memory: ~40 bytes per entry vs `HashMap`'s ~36 — and why the ordered API is worth
       it. `[NUM]` `[X-REF 02]`
3.4.25 `ConcurrentSkipListMap` as the concurrent ordered map, and why a lock-free red-black tree does
       not exist in the JDK. `[X-REF 05]`
3.4.26 The balanced-tree comparison table: worst-case vs amortized vs expected, rotations per update,
       implementation size, concurrency friendliness.

*(26 leaves)*

## §3.5 Sorting internals

3.5.1 **TimSort**: run detection (ascending and strictly-descending, the latter reversed in place),
      `MIN_MERGE = 32`, `minRunLength` computation, binary insertion sort to extend short runs,
      the merge stack, galloping merge, O(n) best case, O(n log n) worst, O(n/2) extra space.
      `[NUM]` `[SOURCE]` `[PROVE]`
3.5.2 The `minRunLength` derivation: pick a run length in [16,32] such that `n/minRun` is close to a
      power of two, so the merge tree is balanced. `[PROVE]` `[NUM]`
3.5.3 The merge-stack invariants (`runLen[i-3] > runLen[i-2] + runLen[i-1]` and
      `runLen[i-2] > runLen[i-1]`) and `mergeCollapse`. `[SOURCE]` `[PROVE]`
3.5.4 The de Gouw et al. formal-verification result: the invariant was insufficient, producing an
      `ArrayIndexOutOfBoundsException`; the JDK enlarged the stack rather than fixing the invariant.
      `[RESEARCH]` `[PROVE]`
3.5.5 Galloping (exponential search) in the merge, and the `MIN_GALLOP = 7` adaptive threshold.
      `[NUM]` `[SOURCE]`
3.5.6 `IllegalArgumentException: Comparison method violates its general contract!` — the exact
      detection point, the four causes, and `-Djava.util.Arrays.useLegacyMergeSort=true` as the
      band-aid. `[TRAP]` `[RESEARCH]` `[X-REF 02]`
3.5.7 **Dual-pivot quicksort** for primitives: two pivots partition into three regions, fewer
      cache misses than single-pivot, ~5% fewer comparisons in practice. `[PROVE]` `[RESEARCH]`
3.5.8 Java 14+ `DualPivotQuicksort` structure: insertion sort below `MAX_INSERTION_SORT_SIZE`,
      counting sort for `byte`/`char`/`short`, merge-sort fallback on detected structure, and a
      heapsort fallback at `MAX_RECURSION_DEPTH`. `[NUM]` `[SOURCE]` `[RESEARCH]`
3.5.9 The introsort idea generalised: quicksort + depth limit + heapsort fallback = O(n log n) worst
      case with quicksort's constants. `[PROVE]`
3.5.10 Why Java splits object and primitive sorting: stability is meaningless for primitives, and
       object comparisons are expensive so minimising comparisons wins. `[PROVE]` `[X-REF 02]`
3.5.11 Quicksort's expected-O(n log n) proof by the indicator-variable/harmonic-sum argument.
       `[PROVE]` `[NUM]`
3.5.12 Quicksort's adversarial input: median-of-three killer sequences, and the historical
       `Arrays.sort(int[])` DoS. `[RESEARCH]` `[TRAP]`
3.5.13 Quicksort on many duplicates: why Lomuto degrades to O(n²) and three-way partitioning fixes
       it. `[PROVE]`
3.5.14 Merge sort's exact comparison count (n log n − n + 1 in the best case) and its optimality
       margin against the information-theoretic bound. `[NUM]` `[PROVE]`
3.5.15 In-place merge sort and block merge sort (WikiSort/GrailSort) in one paragraph.
       `[RESEARCH]`
3.5.16 The decision-tree lower bound, in full: any comparison sort's tree has ≥ n! leaves, so its
       height is ≥ ⌈log₂ n!⌉ = Θ(n log n); with Stirling, ≥ n log₂n − 1.44n. `[PROVE]` `[NUM]`
3.5.17 The lower bound for finding the maximum (n−1 comparisons) and for finding both max and min
       (⌈3n/2⌉ − 2 via pairing). `[PROVE]` `[NUM]`
3.5.18 The second-largest lower bound n + ⌈log₂n⌉ − 2 via the tournament argument. `[PROVE]` `[NUM]`
3.5.19 The selection lower bound and why median-of-medians' constant is ~10n comparisons. `[NUM]`
       `[RESEARCH]`
3.5.20 Counting sort correctness: the prefix-sum placement pass, iterating the input *backwards* for
       stability. `[PROVE]` `[TRAP]`
3.5.21 Radix sort correctness by induction on digit position, requiring a stable per-digit sort.
       `[PROVE]`
3.5.22 LSD vs MSD radix, and the O(nk) vs comparison-sort trade at realistic k. `[PROVE]` `[NUM]`
3.5.23 Bucket sort's expected O(n) under the uniformity assumption, and its O(n²) worst case.
       `[PROVE]`
3.5.24 `Arrays.parallelSort`: the fork/join merge-sort structure and `MIN_ARRAY_SORT_GRAN = 8192`.
       `[NUM]` `[X-REF 02]` `[X-REF 05]`
3.5.25 External merge sort: k-way merge with a heap, the passes formula ⌈log_k(N/M)⌉, and the I/O
       cost model. `[NUM]` `[PROVE]` `[X-REF 22]`
3.5.26 Sorting-algorithm selection in a library: what a general-purpose sort must guarantee
       (worst-case bound, stability where promised, no pathological input) and how each JDK choice
       satisfies it.

*(26 leaves)*

## §3.6 Selection and order statistics

3.6.1 Quickselect: the partition-and-recurse-one-side algorithm; T(n) = T(n/2) + O(n) with a good
      pivot. `[PROVE]` `[BUILD]`
3.6.2 The expected-linear proof by the same indicator argument as quicksort, giving ~4n comparisons
      with random pivots. `[PROVE]` `[NUM]`
3.6.3 The O(n²) worst case, and randomization as the fix; the "randomize the input or the pivot"
      equivalence. `[PROVE]`
3.6.4 **Median of medians**: groups of 5, median of each, recurse for the median of medians, use it
      as the pivot; the ≥3n/10 guarantee on each side, giving T(n) ≤ T(n/5) + T(7n/10) + O(n) →
      O(n). Show why 5 works and 3 does not. `[PROVE]` `[NUM]`
3.6.5 Introselect: quickselect with a median-of-medians fallback (`nth_element`'s strategy).
      `[RESEARCH]`
3.6.6 Selection in two sorted arrays in O(log(m+n)). `[PROVE]`
3.6.7 Selection from a stream: the size-k heap, and the impossibility of exact median in O(1) space.
      `[PROVE]`
3.6.8 Approximate quantiles: t-digest, GK sketch, and reservoir sampling, in one paragraph each.
      `[X-REF 20]` `[RESEARCH]`
3.6.9 Partial sorting and the "sort the top k only" cost O(n + k log k). `[PROVE]`
3.6.10 The k-th smallest in a sorted matrix by binary search on value, with the O(n) counting step —
       and why the heap solution is O(k log k). `[PROVE]`

*(10 leaves)*

## §3.7 Binary search, formally

3.7.1 The loop invariant for the half-open form: `lo ≤ answer ≤ hi` and `predicate(lo−1) = false`,
      `predicate(hi) = true`. `[PROVE]`
3.7.2 Termination: `hi − lo` strictly decreases every iteration. Prove it for both branches.
      `[PROVE]`
3.7.3 Correctness on exit: `lo == hi` and the invariant pins the answer. `[PROVE]`
3.7.4 The exact iteration count ⌈log₂(n+1)⌉, and the comparison-count optimality via the
      decision-tree bound. `[PROVE]` `[NUM]`
3.7.5 The overflow bug: `(lo + hi)` exceeds `Integer.MAX_VALUE` at n ≥ 2³⁰; `lo + (hi − lo)/2` and
      `(lo + hi) >>> 1` are both correct for non-negative bounds, and only the first is correct when
      bounds can be negative. `[PROVE]` `[NUM]` `[TRAP]`
3.7.6 Bloch's 2006 write-up, the bug in Bentley's *Programming Pearls* (proved correct and tested
      for nine years), and the same bug in `java.util.Arrays.binarySearch` — quoted. `[SOURCE]`
      `[RESEARCH]`
3.7.7 `Arrays.binarySearch` source: the loop, the `midVal` comparison, and the
      `-(low + 1)` return. `[SOURCE]` `[NUM]`
3.7.8 `Collections.binarySearch` and the `RandomAccess`/`BINARYSEARCH_THRESHOLD = 5000` branch.
      `[SOURCE]` `[NUM]` `[X-REF 02]`
3.7.9 Binary search's cache behaviour: Θ(log n) cache misses, all to unrelated lines; the
      B-tree/Eytzinger layout as the cache-friendly alternative. `[PROVE]` `[RESEARCH]`
      `[X-REF 06]`
3.7.10 Branchless binary search and the `cmov`-based inner loop. `[RESEARCH]`
3.7.11 Interpolation search's O(log log n) expected bound under uniformity, and its O(n) worst case.
       `[PROVE]` `[RESEARCH]`
3.7.12 Exponential search's O(log i) bound where i is the answer's index. `[PROVE]`
3.7.13 Binary search on a monotone predicate over an implicit domain — the formal statement that
       unifies every "binary search on the answer" problem. `[PROVE]`
3.7.14 The floating-point form: why an epsilon loop can fail to terminate (representable-gap
       underflow) and why a fixed 100 iterations halves the interval to 2⁻¹⁰⁰ of its width.
       `[PROVE]` `[NUM]` `[TRAP]`

*(14 leaves)*

## §3.8 Graph traversal theory

3.8.1 BFS correctness: the queue holds vertices in non-decreasing distance order, so the first pop of
      a vertex is at its true distance. Prove by induction on the level. `[PROVE]`
3.8.2 The BFS tree, and the fact that every non-tree edge joins vertices whose levels differ by at
      most 1 (undirected). `[PROVE]`
3.8.3 BFS complexity Θ(V+E) with an adjacency list, Θ(V²) with a matrix. `[PROVE]` `[NUM]`
3.8.4 DFS's parenthesis theorem: discovery/finish intervals are either nested or disjoint. `[PROVE]`
3.8.5 White-path theorem: v is a descendant of u in the DFS forest iff at time `d[u]` there is an
      all-white path u→v. `[PROVE]`
3.8.6 Edge classification in a directed DFS: tree, back, forward, cross — and the `d`/`f` comparisons
      that identify each. `[PROVE]` `[NUM]`
3.8.7 In an undirected DFS only tree and back edges exist. `[PROVE]`
3.8.8 **A directed graph is acyclic iff its DFS produces no back edge.** `[PROVE]`
3.8.9 Topological order = reverse finish order; prove that every edge (u,v) implies `f[u] > f[v]` in
      a DAG. `[PROVE]`
3.8.10 Kahn's correctness and its equivalence to the DFS order; and the fact that neither produces a
       canonical order. `[PROVE]`
3.8.11 `low`-link definition, and the bridge condition `low[v] > disc[u]` vs the articulation-point
       condition `low[v] >= disc[u]`, plus the root's child-count special case. `[PROVE]` `[TRAP]`
3.8.12 **Tarjan's SCC**: one DFS, the on-stack flag, and why `low[v] == disc[v]` identifies a root.
       `[PROVE]` `[RESEARCH]`
3.8.13 **Kosaraju's SCC**: why the second pass on the transpose in decreasing finish order isolates
       components. `[PROVE]`
3.8.14 The condensation DAG and its topological order as a by-product of Tarjan (components are
       emitted in reverse topological order). `[PROVE]` `[RESEARCH]`
3.8.15 Biconnected components and the block-cut tree, named with their cost. `[RESEARCH]`
3.8.16 Eulerian conditions: undirected — connected and 0 or 2 odd-degree vertices; directed —
       connected and in-degree = out-degree everywhere (or one +1/−1 pair). `[PROVE]` `[NUM]`
3.8.17 Hierholzer's algorithm and why the naive greedy walk gets stuck. `[PROVE]`
3.8.18 Bipartiteness ⟺ no odd cycle ⟺ 2-colourable. `[PROVE]`
3.8.19 Iterative DFS: the exact state a frame must carry (vertex + child index) to reproduce the
       recursive order, and why the naive "push all neighbours" version is a different traversal.
       `[PROVE]` `[TRAP]` `[BUILD]`
3.8.20 BFS/DFS on implicit and infinite graphs: the visited set becomes the memory bound, and
       iterative deepening as the trade.
3.8.21 Bidirectional search's correctness condition (stop when the frontiers touch, but the answer
       needs a final relaxation pass for weighted graphs). `[TRAP]` `[PROVE]`

*(21 leaves)*

## §3.9 Shortest-path and MST theory

3.9.1 The shortest-path optimality substructure: every prefix of a shortest path is a shortest path.
      `[PROVE]`
3.9.2 Why negative cycles make "shortest path" undefined, and why negative *edges* alone do not.
      `[PROVE]`
3.9.3 The relaxation operation as the single primitive underneath BFS, Dijkstra, Bellman–Ford, and
      DAG-DP. `[PROVE]`
3.9.4 **Dijkstra's correctness**: when v is popped, `dist[v]` is final — because all remaining
      frontier distances are ≥ `dist[v]` and edges are non-negative. Prove by contradiction.
      `[PROVE]`
3.9.5 The exact step where the proof uses non-negativity, and the three-vertex counterexample with a
      negative edge. `[PROVE]` `[TRAP]`
3.9.6 Dijkstra with lazy deletion: the heap may hold O(E) entries, so the bound is O(E log E) =
      O(E log V); with decrease-key it is O(E log V) with O(V) heap size. `[PROVE]` `[NUM]`
3.9.7 Dijkstra with a Fibonacci heap: O(E + V log V), and why nobody uses it. `[NUM]` `[RESEARCH]`
3.9.8 Dijkstra with an array frontier: O(V²), which beats the heap when E = Θ(V²). `[PROVE]`
      `[NUM]`
3.9.9 Dial's algorithm / bucket queue for small integer weights: O(E + VC). `[RESEARCH]`
3.9.10 0-1 BFS correctness: the deque maintains the two-value distance order that a heap would.
       `[PROVE]`
3.9.11 **Bellman–Ford correctness**: after k rounds, `dist[v]` is correct for all paths using ≤ k
       edges; a shortest path uses ≤ V−1 edges. `[PROVE]` `[NUM]`
3.9.12 Negative-cycle detection: a successful relaxation in round V proves a negative cycle; tracing
       the cycle via parent pointers. `[PROVE]`
3.9.13 SPFA and its O(VE) worst case; the "small label first / large label last" heuristics.
       `[RESEARCH]`
3.9.14 **Floyd–Warshall as DP over the intermediate-vertex set**: `d^k[i][j] = min(d^(k-1)[i][j],
       d^(k-1)[i][k] + d^(k-1)[k][j])`, which is why `k` must be the outer loop. Prove that the
       in-place version is still correct. `[PROVE]` `[TRAP]` `[NUM]`
3.9.15 Floyd–Warshall variants: transitive closure (boolean semiring), minimax/maximin path (min-max
       semiring), counting paths (counting semiring) — the algebraic-path-problem generalisation.
       `[PROVE]` `[RESEARCH]`
3.9.16 Johnson's reweighting: `w'(u,v) = w(u,v) + h(u) − h(v)` preserves shortest paths and makes all
       weights non-negative. Prove both claims. `[PROVE]` `[RESEARCH]`
3.9.17 A*'s admissibility (h never overestimates) and consistency (h(u) ≤ w(u,v) + h(v)) conditions,
       and what breaks without each. `[PROVE]` `[RESEARCH]`
3.9.18 **MST cut property**: the minimum-weight edge crossing any cut is in some MST. `[PROVE]`
3.9.19 **MST cycle property**: the maximum-weight edge on any cycle is in no MST. `[PROVE]`
3.9.20 Kruskal's correctness from the cut property; Prim's from the same. `[PROVE]`
3.9.21 MST uniqueness iff all edge weights are distinct (sufficient, not necessary). `[PROVE]`
       `[TRAP]`
3.9.22 Minimum bottleneck spanning tree ⊆ MST, but not conversely. `[PROVE]` `[RESEARCH]`
3.9.23 Borůvka's algorithm and its O(E log V) with a parallel-friendly structure. `[RESEARCH]`
3.9.24 MST cost breakdown: Kruskal O(E log E) dominated by the sort; Prim O(E log V) with a heap,
       O(V²) with an array — so Prim wins on dense graphs. `[PROVE]` `[NUM]`
3.9.25 Max-flow min-cut theorem, and the Ford–Fulkerson termination condition (integral capacities);
       the irrational-capacity non-termination example. `[PROVE]` `[RESEARCH]`
3.9.26 Edmonds–Karp's O(VE²) bound from the shortest-augmenting-path argument; Dinic's O(V²E) from
       level graphs and blocking flows. `[PROVE]` `[RESEARCH]`
3.9.27 König's theorem and the matching/vertex-cover duality on bipartite graphs. `[PROVE]`
       `[RESEARCH]`

*(27 leaves)*

## §3.10 Union-find internals

3.10.1 The parent array, `find` as a walk to the fixed point, and the naive O(n) height.
3.10.2 Union by rank: the height bound — a tree of rank r has ≥ 2^r nodes, so rank ≤ log₂n.
       `[PROVE]` `[NUM]`
3.10.3 Path compression alone gives O(log n) amortized; union by rank alone gives O(log n) worst
       case; together they give O(α(n)) amortized. `[PROVE]` `[RESEARCH]`
3.10.4 Ackermann's function and its inverse: α(n) ≤ 4 for n < 2^2^2^2^16. `[NUM]` `[PROVE]`
3.10.5 The Tarjan/Van Leeuwen result and the matching Ω(α(n)) lower bound in the pointer-machine
       model. `[PROVE]` `[RESEARCH]`
3.10.6 The potential-function sketch of the O(α(n)) proof (rank buckets / level argument), stated at
       a level a reader can follow. `[PROVE]`
3.10.7 The recursive `find` one-liner `parent[x] == x ? x : (parent[x] = find(parent[x]))` and its
       O(log n) stack depth — the iterative two-pass version for safety. `[TRAP]` `[BUILD]`
3.10.8 Path halving `parent[x] = parent[parent[x]]` in a single pass, and its identical asymptotics.
       `[PROVE]` `[RESEARCH]`
3.10.9 Union by size vs union by rank: size gives a slightly better constant and enables
       component-size queries for free. `[PROVE]`
3.10.10 Rank stored in a negative parent slot, as the one-array implementation trick. `[BUILD]`
3.10.11 Weighted/potential DSU: maintaining `weight[x]` = value relative to the parent, and how path
        compression must accumulate it. `[PROVE]` `[BUILD]`
3.10.12 Parity/bipartite DSU: doubling the node set, or an XOR weight. `[PROVE]`
3.10.13 Rollback/persistent DSU (union by rank only, no compression, with an undo stack) for offline
        dynamic connectivity. `[PROVE]` `[RESEARCH]`
3.10.14 DSU on a tree (small-to-large merging) and DSU-on-tree/`sack` technique, named.
        `[RESEARCH]`
3.10.15 What DSU fundamentally cannot do: deletions, path queries, and directed reachability — and
        the structures that can (link-cut trees, Euler-tour trees). `[RESEARCH]`

*(15 leaves)*

## §3.11 DP theory

3.11.1 DP as a DAG of subproblems: the recurrence defines edges, and any topological order of that
       DAG is a valid fill order. This single framing explains "iteration order". `[PROVE]`
3.11.2 Time = (#states) × (transition cost per state) — the formula that makes complexity mechanical.
       `[PROVE]` `[NUM]`
3.11.3 Space = (#live states), which is what enables rolling arrays. `[PROVE]`
3.11.4 Optimal-substructure proof obligation, worked for shortest paths (holds) and longest simple
       paths (fails). `[PROVE]`
3.11.5 The principle of optimality (Bellman) stated formally. `[RESEARCH]`
3.11.6 Memoization = lazy evaluation of the DAG; tabulation = eager evaluation. The equivalence
       proof. `[PROVE]`
3.11.7 When memoization is strictly better: sparse reachable state space (e.g. `coinChange` with
       huge amount but few reachable states). `[PROVE]`
3.11.8 When tabulation is strictly better: deep recursion, and space optimization. `[PROVE]`
3.11.9 **Pseudo-polynomial**, precisely: knapsack's O(nW) is polynomial in the *value* W but
       exponential in the log₂W bits used to write it, so it does not contradict NP-hardness.
       `[PROVE]` `[NUM]` `[TRAP]`
3.11.10 Subset-sum's FPTAS by value rounding, as the practical consequence. `[RESEARCH]`
3.11.11 The 0/1-knapsack one-row proof: iterating capacity descending reads only the previous
        iteration's values, so each item is used at most once; ascending reads the current
        iteration's, permitting reuse. `[PROVE]` `[NUM]`
3.11.12 LIS in O(n log n): the `tails` array invariant (`tails[i]` = smallest tail of an increasing
        subsequence of length i+1), why it is sorted, and why its contents are not an LIS.
        `[PROVE]` `[TRAP]`
3.11.13 Patience sorting as the LIS algorithm's origin, and the Dilworth/Erdős–Szekeres connection.
        `[RESEARCH]`
3.11.14 Edit distance's correctness by induction on i+j, and the alignment reconstruction.
        `[PROVE]`
3.11.15 Hirschberg's algorithm: LCS/edit-distance alignment in O(n) space via divide and conquer.
        `[PROVE]` `[RESEARCH]`
3.11.16 Interval DP's O(n³) shape, and the length-ascending order requirement. `[PROVE]`
3.11.17 Bitmask DP: 2ⁿ states, n transitions → O(n·2ⁿ); the TSP instance and its 2^20·20 feasibility
        arithmetic. `[NUM]` `[PROVE]`
3.11.18 Submask-sum DP (SOS DP) in O(n·2ⁿ) and the Σ over submasks O(3ⁿ) bound. `[PROVE]` `[NUM]`
        `[RESEARCH]`
3.11.19 Digit DP's state signature (position, tight, leading-zero, carried property) and the
        counting argument. `[PROVE]` `[RESEARCH]`
3.11.20 Divide-and-conquer DP optimization: the monotone-optimum condition and the O(n log n) per
        layer bound. `[PROVE]` `[RESEARCH]`
3.11.21 Knuth optimization: the quadrangle inequality / totally-monotone condition and the O(n²)
        result. `[PROVE]` `[RESEARCH]`
3.11.22 Convex hull trick and Li Chao tree: DP transitions as line queries. `[RESEARCH]`
3.11.23 Monotonic-deque DP optimization for sliding-window transitions (`dp[i] = max(dp[j]) + a[i]`
        over a window). `[PROVE]`
3.11.24 Matrix-exponentiation DP for linear recurrences with a fixed transition, O(k³ log n).
        `[PROVE]` `[NUM]`
3.11.25 DP on trees as DP on the DFS post-order; rerooting as two passes. `[PROVE]`
3.11.26 DP on DAGs: memoized DFS as the natural implementation, and why a visited set is not enough
        (you must cache the *value*). `[TRAP]`
3.11.27 Expectation DP and the linearity-of-expectation shortcut. `[PROVE]`
3.11.28 Minimax/game DP: the alternating min/max, and the Sprague–Grundy theorem for sums of
        impartial games. `[PROVE]` `[RESEARCH]`
3.11.29 Profile/broken-profile DP for tiling problems, named with its state shape. `[RESEARCH]`
3.11.30 The DP-state-design failure modes: a state that is insufficient (the future depends on more
        than it), a state that is redundant (blowing up the space), and a state that is unbounded.
        `[TRAP]`

*(30 leaves)*

## §3.12 Greedy theory

3.12.1 The exchange argument as a proof template: assume an optimal solution differing from greedy at
       the first index, exchange, show no loss, induct. `[PROVE]`
3.12.2 The greedy-stays-ahead template: define a measure, show greedy dominates any solution after
       every step. `[PROVE]`
3.12.3 The cut/structural template: prove the greedy choice is in *some* optimal solution.
       `[PROVE]`
3.12.4 Matroids: the ground set, independence axioms (downward closure and the exchange property),
       and the theorem that greedy is optimal on a weighted matroid. `[PROVE]` `[RESEARCH]`
3.12.5 The graphic matroid instance: Kruskal is the matroid greedy algorithm. `[PROVE]`
3.12.6 Non-matroid structures where greedy still works, via a different argument (Huffman by an
       exchange argument, EDF scheduling by an exchange argument). `[PROVE]`
3.12.7 Huffman's optimality proof: the two least-frequent symbols are siblings at maximum depth.
       `[PROVE]`
3.12.8 Fractional-vs-0/1 knapsack: LP relaxation is integral for the fractional case, which is
       exactly why greedy works there and not for 0/1. `[PROVE]` `[RESEARCH]`
3.12.9 Interval scheduling by earliest end, proved; and the four wrong keys (earliest start,
       shortest duration, fewest conflicts, latest end) each with a counterexample. `[PROVE]`
       `[TRAP]`
3.12.10 EDF/EDD scheduling optimality (minimising maximum lateness) by the exchange argument.
        `[PROVE]` `[RESEARCH]`
3.12.11 The "regret/exchange heap" greedy pattern's correctness argument. `[PROVE]`
3.12.12 Approximation ratios and their proofs: greedy set cover ≤ H_n ≈ ln n + 1, 2-approximate
        vertex cover by maximal matching, 2-approximate metric TSP by MST doubling. `[PROVE]`
        `[NUM]` `[RESEARCH]`
3.12.13 Online/competitive greedy: LRU is k-competitive for paging; the ski-rental 2-competitive
        bound. `[PROVE]` `[RESEARCH]` `[X-REF 15]`
3.12.14 The greedy failure diagnostic: if you cannot state which of the three templates applies,
        greedy is a guess. `[TRAP]`

*(14 leaves)*

## §3.13 Range-query structures

3.13.1 The problem taxonomy: static vs dynamic, invertible vs idempotent aggregate, point vs range
       update, point vs range query — the 2×2×2 that selects the structure. `[NUM]`
3.13.2 Prefix sums: O(n) build, O(1) query, no updates; requires an invertible operation. `[PROVE]`
3.13.3 **Sqrt decomposition**: blocks of size √n, O(1) point update, O(√n) query; the block-boundary
       arithmetic. `[PROVE]` `[NUM]` `[BUILD]`
3.13.4 **Fenwick tree (binary indexed tree)**: the `i & -i` lowbit structure, `update` and `query`
       loops, O(log n) both, 1-indexed requirement. `[PROVE]` `[NUM]` `[BUILD]`
3.13.5 Why Fenwick is smaller and faster than a segment tree, and what it cannot do (non-invertible
       aggregates like min without extra work). `[PROVE]` `[TRAP]`
3.13.6 Fenwick O(n) construction, range update via a difference-array Fenwick, and 2-D Fenwick.
       `[PROVE]` `[BUILD]`
3.13.7 Fenwick for "count of smaller elements after self" via coordinate compression. `[BUILD]`
3.13.8 **Segment tree**: the recursive structure, 4n array sizing, build O(n), query and point update
       O(log n), and the merge function as the only problem-specific part. `[PROVE]` `[NUM]`
       `[BUILD]`
3.13.9 Iterative bottom-up segment tree, and the 2n-size variant. `[BUILD]` `[RESEARCH]`
3.13.10 **Lazy propagation** for range updates: the pending-update field, `push`, and the
        composition requirement on updates. `[PROVE]` `[BUILD]`
3.13.11 Segment tree beats, persistent segment trees, and merge-sort trees, named with their use.
        `[RESEARCH]`
3.13.12 **Sparse table**: O(n log n) build, O(1) query, immutable, and the idempotency requirement
        (works for min/max/gcd, not for sum). `[PROVE]` `[NUM]` `[BUILD]`
3.13.13 The `log` table and the `k = 31 - Integer.numberOfLeadingZeros(len)` trick. `[NUM]`
3.13.14 RMQ in O(n)/O(1) via the Fischer–Heun / block decomposition, and the LCA↔RMQ equivalence.
        `[PROVE]` `[RESEARCH]`
3.13.15 Mo's algorithm for offline range queries: sort by (block of l, r), O((n+q)√n). `[PROVE]`
        `[RESEARCH]`
3.13.16 Wavelet trees and merge-sort trees for range-kth queries, named. `[RESEARCH]`
3.13.17 The structure-selection table: 8 query/update combinations → the right structure and its
        cost. `[DRILL]`
3.13.18 What the JDK offers instead: nothing. `TreeMap` + `subMap` gives O(log n + k) range
        iteration, not O(log n) range aggregation — the gap that forces hand-rolling.
        `[TRAP]` `[X-REF 02]`

*(18 leaves)*

## §3.14 String algorithm internals

3.14.1 Naive matching: O(nm) worst case, and the input that triggers it (`aaaa…a` vs `aaa…ab`).
       `[PROVE]` `[NUM]`
3.14.2 **KMP**: the failure/prefix function π[i] = length of the longest proper prefix of `p[0..i]`
       that is also a suffix; its O(m) construction and the two-pointer matching loop. `[PROVE]`
       `[BUILD]`
3.14.3 The π-function's amortized-O(m) construction proof (the fallback pointer only decreases).
       `[PROVE]`
3.14.4 KMP applications beyond search: shortest palindromic extension, period detection
       (`n − π[n−1]` is the smallest period), string compression, "repeated substring pattern".
       `[PROVE]` `[NUM]`
3.14.5 **Z-function**: Z[i] = length of the longest common prefix of `s` and `s[i..]`; the
       [l,r] box maintenance and the O(n) proof. `[PROVE]` `[BUILD]`
3.14.6 Z-function ↔ prefix-function conversion, and which is easier to derive under pressure.
3.14.7 **Rabin–Karp**: the polynomial rolling hash, the O(1) roll, the expected-O(n+m) bound, and
       the verification step that makes it correct despite collisions. `[PROVE]` `[BUILD]`
3.14.8 Rolling-hash parameter choice: base > alphabet size, a large prime modulus, `long`
       arithmetic, and the anti-hash tests that break base 31 / mod 2⁶⁴. `[NUM]` `[TRAP]`
       `[RESEARCH]`
3.14.9 Rabin–Karp applications: longest duplicate substring (binary search + rolling hash), repeated
       DNA sequences, distinct substring counting, 2-D pattern matching. `[PROVE]`
3.14.10 **Boyer–Moore**: bad-character and good-suffix heuristics, sublinear average behaviour, and
        the Boyer–Moore–Horspool simplification. `[RESEARCH]`
3.14.11 **Manacher's algorithm**: all palindromic substrings in O(n) via the centre/radius array and
        the mirror reuse; the odd/even unification by interleaving separators. `[PROVE]` `[BUILD]`
        `[RESEARCH]`
3.14.12 **Aho–Corasick**: a trie plus failure links (BFS-constructed) plus output links; O(Σ|pᵢ| +
        n + matches) multi-pattern matching. `[PROVE]` `[BUILD]` `[RESEARCH]`
3.14.13 **Suffix array**: definition, O(n log² n) doubling construction, O(n log n) with radix sort,
        DC3/SA-IS in O(n); the LCP array via Kasai's algorithm. `[PROVE]` `[NUM]` `[RESEARCH]`
3.14.14 Suffix array + LCP applications: longest repeated substring, longest common substring of k
        strings, distinct substring count, pattern search in O(m log n). `[PROVE]`
3.14.15 Suffix tree and suffix automaton in one paragraph each, with Ukkonen's O(n) construction
        named. `[RESEARCH]`
3.14.16 Lyndon factorization and Booth's algorithm for the least rotation. `[RESEARCH]`
3.14.17 The string-algorithm selection table: single pattern (KMP/Z/Rabin–Karp), many patterns
        (Aho–Corasick), many queries on one text (suffix array/automaton), palindromes (Manacher),
        approximate (edit-distance DP). `[DRILL]`
3.14.18 `String.indexOf` in the JDK is the naive O(nm) algorithm with an intrinsic fast path — not
        KMP. State the consequence. `[SOURCE]` `[TRAP]` `[RESEARCH]`
3.14.19 `java.util.regex` is a backtracking engine, so it is not linear; `Pattern` compilation cost,
        and the ReDoS consequence. `[TRAP]` `[X-REF 13]`
3.14.20 Unicode correctness in string algorithms: code units vs code points vs grapheme clusters, and
        the algorithms that silently break on surrogate pairs. `[TRAP]` `[X-REF 03]`

*(20 leaves)*

## §3.15 Trie internals

3.15.1 Memory layout: `TrieNode[26]` = 16-byte header + 16-byte array header + 26×4 bytes = ~136 B
       per node under compressed oops. `[NUM]` `[PROVE]`
3.15.2 The `HashMap<Character,TrieNode>` alternative: ~48 B per entry, so it wins only below ~4
       children per node. Show the crossover arithmetic. `[NUM]` `[PROVE]`
3.15.3 A flat-array trie (`int[][] next` or `int[nodes][26]`) as the allocation-free implementation
       competitive programmers use. `[BUILD]`
3.15.4 Node count bound: at most Σ|wᵢ| + 1 nodes, and far fewer with shared prefixes; the arithmetic
       for an English dictionary. `[NUM]`
3.15.5 Compressed trie / radix tree: collapse single-child chains; the split-on-insert operation and
       the O(|alphabet|)-free space win. `[PROVE]` `[RESEARCH]`
3.15.6 PATRICIA trie / bitwise radix tree, and its use in IP routing tables. `[RESEARCH]`
3.15.7 DAWG / DAFSA: minimise the trie by merging equivalent suffixes; the space win and the loss of
       per-word payloads. `[RESEARCH]`
3.15.8 Ternary search tree: 3 pointers per node instead of 26, O(log|Σ| · L) lookups. `[RESEARCH]`
3.15.9 Deletion by reference counting vs recursive pruning, and the shared-prefix hazard. `[PROVE]`
       `[TRAP]`
3.15.10 Binary trie over 32-bit integers: the maximum-XOR walk, and why greedy bit-by-bit is optimal.
        `[PROVE]`
3.15.11 Persistent tries for "maximum XOR in a range". `[RESEARCH]`
3.15.12 Trie vs hash set vs sorted array + binary search vs a Bloom filter: the capability/cost
        table for dictionary membership and prefix queries.

*(12 leaves)*

## §3.16 Memory, cache, and the JVM's effect on algorithm cost

3.16.1 Object layout: 12-byte header (8-byte mark + 4-byte compressed klass), field alignment,
       8-byte object alignment, and the padding arithmetic. `[NUM]` `[RESEARCH]` `[X-REF 06]`
3.16.2 Array layout: 16-byte header (12 + 4-byte length), then elements. `[NUM]`
3.16.3 The footprint table: `int[n]` = 16 + 4n, `long[n]` = 16 + 8n, `Integer` = 16 B,
       `Long` = 24 B, `Integer[n]` = 16 + 4n + 16n, a two-ref node = 32 B, `HashMap.Node` = 32 B,
       `TreeMap.Entry` = 40 B. `[NUM]` `[PROVE]`
3.16.4 The worked example: a `HashMap<Integer,Integer>` with 10⁶ entries ≈ 32 MB of nodes + 8 MB of
       table + 32 MB of boxes ≈ 72 MB, vs `int[10⁶]` = 4 MB. `[NUM]` `[PROVE]`
3.16.5 Compressed oops on/off at the 32 GB heap boundary, and the 33% footprint jump. `[NUM]`
       `[X-REF 06]`
3.16.6 Project Lilliput's 8-byte (and 4-byte) header, as the forward-looking change. `[RESEARCH]`
3.16.7 Cache lines (64 B), spatial and temporal locality, and hardware prefetch — the three reasons
       array algorithms beat pointer algorithms at equal Big-O. `[PROVE]` `[NUM]`
3.16.8 The measured crossover: `ArrayList` insert-in-middle beats `LinkedList` up to ~10⁴ elements
       because `System.arraycopy` moves 64 bytes per cycle while a node hop costs a cache miss.
       `[PROVE]` `[RESEARCH]` `[X-REF 02]`
3.16.9 Row-major vs column-major traversal of a 2-D array: the measured factor, and the
       cache-line-per-row arithmetic. `[NUM]` `[PROVE]`
3.16.10 Cache-oblivious algorithms in one paragraph: recursive layouts, van Emde Boas layout, and
        why binary search on a sorted array is cache-pessimal. `[RESEARCH]`
3.16.11 False sharing in parallel algorithms, and `@Contended`. `[X-REF 05]`
3.16.12 Allocation cost: TLAB bump-pointer allocation is cheap, but GC pressure from per-iteration
        allocation is not; the escape-analysis/scalar-replacement caveat. `[X-REF 06]`
3.16.13 Boxing in a hot loop: the allocation, the indirection, and the `Integer` cache's partial
        rescue. `[NUM]` `[X-REF 03]`
3.16.14 Bounds-check elimination: when the JIT removes it (counted loops over `a.length`) and when it
        cannot. `[X-REF 06]`
3.16.15 JIT warm-up and why a microbenchmark without warm-up reports the interpreter's numbers; JMH's
        `@Warmup`, `@Fork`, `Blackhole`. `[X-REF 06]`
3.16.16 Branch prediction: why sorting the input before a branchy loop can make the loop faster, and
        the branchless rewrite. `[PROVE]` `[RESEARCH]`
3.16.17 SIMD/auto-vectorization and the Vector API (still incubating through Java 25) for array
        algorithms. `[RESEARCH]` `[X-REF 04]`
3.16.18 The practical rule: when two algorithms are within a log factor, measure — the constants
        decide. `[TRAP]`

*(18 leaves)*

## §3.17 Recursion at the machine level

3.17.1 The stack frame's contents and the per-frame cost (~40–100 bytes in HotSpot depending on
       locals). `[NUM]` `[X-REF 06]`
3.17.2 Default thread stack size by platform (~512 KB–1 MB on 64-bit Linux), the resulting frame
       budget, and `-Xss` / `Thread(ThreadGroup, Runnable, String, long stackSize)`. `[NUM]`
       `[RESEARCH]`
3.17.3 `StackOverflowError` as an `Error`, not an `Exception`; catching it is unreliable because the
       stack is already exhausted. `[TRAP]` `[X-REF 03]`
3.17.4 Virtual threads (Java 21) have growable stacks — the recursion-depth consequence and the
       caveats. `[RESEARCH]` `[X-REF 04]`
3.17.5 Why HotSpot does not implement tail-call elimination: stack-walking security (`getCallerClass`)
       and stack traces depend on frames. `[PROVE]` `[RESEARCH]`
3.17.6 Manual tail-call elimination: rewrite as a `while` loop with parameter reassignment.
       `[BUILD]`
3.17.7 Trampolining with a `Supplier`-returning step function. `[BUILD]`
3.17.8 Explicit-stack conversion of a two-recursive-call function, with the resume-state variable.
       `[BUILD]`
3.17.9 Recursion depth for the canonical algorithms: DFS O(V), quicksort O(log n) with the
       larger-side loop / O(n) without, merge sort O(log n), backtracking O(depth), Morris O(1).
       `[NUM]`
3.17.10 The "recursion is slower than iteration" claim, tested: call overhead vs the JIT's inlining
        of shallow recursion. `[TRAP]` `[X-REF 06]`
3.17.11 Memoization's interaction with recursion depth: a memo does not shorten the *first* descent.
        `[TRAP]`
3.17.12 The safe-recursion checklist for production Java: bound the depth, or convert to iteration,
        or run on a thread with an explicit stack size.

*(12 leaves)*

## §3.18 Concurrency and parallelism of algorithms

3.18.1 What parallelises well: divide-and-conquer with independent halves (merge sort, quicksort
       partitions), map/filter/reduce over disjoint ranges, matrix multiply.
3.18.2 What does not: inherently sequential scans with carried state (Kadane, prefix sums naively),
       DFS ordering, greedy with a global structure.
3.18.3 Parallel prefix sum (scan) in O(log n) depth — the counterexample to "prefix sums are
       sequential". `[PROVE]` `[RESEARCH]`
3.18.4 Work and depth (span) as the parallel cost model; Brent's theorem and the work-span bound.
       `[PROVE]` `[RESEARCH]`
3.18.5 Amdahl's law and the serial-fraction ceiling. `[NUM]` `[X-REF 05]`
3.18.6 Fork/join and work stealing: `RecursiveTask`, the sequential-threshold decision, and
       `Arrays.parallelSort`'s 8192. `[NUM]` `[X-REF 05]`
3.18.7 Parallel streams: when they help (large, CPU-bound, splittable source) and when they hurt
       (small n, `LinkedList` source, I/O-bound, shared mutable accumulator). `[X-REF 04]`
3.18.8 `Spliterator` characteristics that determine splittability (`SIZED`, `SUBSIZED`, `ORDERED`).
       `[X-REF 02]`
3.18.9 Concurrent data structures for algorithm work: `ConcurrentHashMap` for memoization,
       `LongAdder` for counters, `ConcurrentLinkedQueue` for a parallel BFS frontier. `[X-REF 05]`
3.18.10 Parallel BFS by level (frontier swap) and its correctness argument. `[PROVE]`
3.18.11 Lock-free structures relevant here: Treiber stack, Michael–Scott queue, and skip lists as the
        reason `ConcurrentSkipListMap` exists rather than a concurrent red-black tree. `[X-REF 05]`
3.18.12 Memoization under concurrency: `computeIfAbsent` recursion is illegal on
        `ConcurrentHashMap` (and can deadlock or corrupt on `HashMap`). `[TRAP]` `[X-REF 05]`
3.18.13 The single-threaded-until-proven rule for interview code, and how to answer "how would you
        parallelise this".

*(13 leaves)*

## §3.19 Complexity theory, the working subset

3.19.1 Decision problems, languages, and why complexity classes are defined over them.
3.19.2 P, NP, co-NP, EXP, PSPACE, R — and the containments known and conjectured. `[RESEARCH]`
3.19.3 NP defined two ways (nondeterministic polynomial time; polynomial-time verifiable
       certificates) and their equivalence. `[PROVE]`
3.19.4 Polynomial-time reductions, NP-hardness, NP-completeness, and Cook–Levin. `[PROVE]`
3.19.5 The canonical NP-complete list you should recognise: SAT, 3-SAT, clique, independent set,
       vertex cover, Hamiltonian path/cycle, TSP (decision), subset sum, partition, knapsack
       (decision), graph colouring, set cover, bin packing.
3.19.6 Problems in P that look hard: 2-SAT, bipartite matching, linear programming, primality
       (AKS), MST, max flow.
3.19.7 Problems of unknown status: graph isomorphism, integer factorization. `[RESEARCH]`
3.19.8 **NP-hard ≠ exponential-only**: pseudo-polynomial DP, FPT algorithms, approximation schemes,
       and heuristics all attack NP-hard problems in practice. `[TRAP]`
3.19.9 Approximation classes: PTAS, FPTAS, APX, and inapproximability results (set cover's ln n
       lower bound). `[RESEARCH]`
3.19.10 Fixed-parameter tractability: O(f(k)·poly(n)) — vertex cover in O(2^k·n), and why "n is huge
        but k is small" is the practical escape. `[PROVE]` `[RESEARCH]`
3.19.11 Halting-problem undecidability in one paragraph, as the outer boundary. `[PROVE]`
3.19.12 Space classes and Savitch's theorem in one line. `[RESEARCH]`
3.19.13 What to say in an interview when a problem is NP-hard: name the reduction, state the
        exponential exact algorithm and its feasible n, then offer the heuristic or approximation.
3.19.14 Lower bounds you can state: comparison sorting Ω(n log n), finding the max n−1, element
        distinctness Ω(n log n) in the comparison model, and the 3SUM conjecture. `[PROVE]`
        `[RESEARCH]`

*(14 leaves)*

## §3.20 Failure modes and production incidents

3.20.1 **Algorithmic complexity attacks** as a class: the attacker chooses inputs that hit your worst
       case. `[X-REF 13]`
3.20.2 Hash-flooding: CVE-2011-4858 (Tomcat), VU#903934, the multi-language 2011 wave, and the
       mitigations. `[RESEARCH]`
3.20.3 ReDoS: the Stack Overflow 2016 outage (a 20 000-space comment line) and the Cloudflare 2019
       global outage (a backtracking regex driving CPU to 100%). `[RESEARCH]`
3.20.4 Quicksort DoS on `Arrays.sort(int[])` with a crafted array. `[RESEARCH]`
3.20.5 Unbounded-memoization and unbounded-cache OOM: the memo that is never evicted. `[X-REF 15]`
3.20.6 `StackOverflowError` from unbounded recursion on user-controlled depth (deeply nested JSON,
       deeply nested regex groups). `[RESEARCH]`
3.20.7 Accidental O(n²): `String +=` in a loop, `list.contains` in a loop, `substring` in a loop,
       `removeAll` with a `List` argument, `LinkedList.get(i)` in a for loop. `[TRAP]`
       `[X-REF 02]`
3.20.8 Accidental O(n²) in a database context: N+1 queries as the same shape one layer out.
       `[X-REF 08]`
3.20.9 The unsorted-`binarySearch` silent wrong answer. `[TRAP]`
3.20.10 The non-transitive comparator: TimSort's exception in production, and the sorted-order
        corruption it prevented. `[X-REF 02]`
3.20.11 Mutable keys stranding map entries — the memory leak that also loses data. `[TRAP]`
3.20.12 Integer overflow in a size/index/sum calculation: the negative array size, the wrapped
        counter, and the `(lo+hi)/2` binary-search bug at scale. `[TRAP]`
3.20.13 Floating-point accumulation error in a running total, and Kahan summation. `[PROVE]`
        `[RESEARCH]`
3.20.14 Off-by-one and fencepost errors as the highest-frequency algorithm bug, with the three
        standard defences (half-open intervals, sentinel, hand-trace n=1 and n=2). `[DRILL]`
3.20.15 The "works on the sample, fails on the hidden test" taxonomy: overflow, empty input, single
        element, duplicates, negative values, maximum n, and unsorted assumptions. `[DRILL]`
3.20.16 The tail-latency consequence of amortized structures in a request path. `[X-REF 20]`
3.20.17 Cache-miss-driven regressions: the same algorithm 10× slower after a data-structure change
        with identical Big-O. `[X-REF 06]`
3.20.18 The mitigation checklist: bound every input, randomize or treeify hash structures, cap
        recursion, pre-size collections, prefer worst-case-bounded structures on the request path.

*(18 leaves)*

## §3.21 Measuring and inspecting algorithms at runtime

3.21.1 The measurement hierarchy: asymptotic analysis → operation counting → microbenchmark →
       production profile. Each answers a different question.
3.21.2 Operation counting as the cheapest empirical check: instrument the comparison/swap counter and
       verify it matches the predicted curve. `[BUILD]` `[DRILL]`
3.21.3 The doubling experiment: run at n, 2n, 4n; the ratio of times identifies the exponent
       (`log₂(T(2n)/T(n))`). `[PROVE]` `[NUM]` `[DRILL]`
3.21.4 JMH: `@Benchmark`, `@State`, `@Warmup`, `@Measurement`, `@Fork`, `Blackhole`, and
       `@OperationsPerInvocation`. `[X-REF 06]`
3.21.5 Microbenchmark pitfalls: dead-code elimination, constant folding, loop unrolling of the
       benchmark itself, on-stack replacement, and profile pollution. `[TRAP]` `[X-REF 06]`
3.21.6 `System.nanoTime` vs `currentTimeMillis`, and the granularity trap. `[X-REF 03]`
3.21.7 Profilers: async-profiler flame graphs, JFR, and what a hot algorithm looks like in each.
       `[X-REF 06]`
3.21.8 Heap inspection for data-structure footprint: `jmap -histo`, Eclipse MAT dominator tree, JOL
       (`ClassLayout.parseInstance(x).toPrintable()`, `GraphLayout.parseInstance(x).totalSize()`).
       `[X-REF 06]` `[RESEARCH]`
3.21.9 Detecting an accidental O(n²) in production: latency vs input-size scatter, or a flame graph
       dominated by a nested loop. `[X-REF 20]`
3.21.10 Property-based testing for algorithm correctness: compare the optimized implementation
        against the brute force on random inputs — the single highest-value verification technique.
        `[BUILD]` `[DRILL]` `[X-REF 16]`
3.21.11 Metamorphic and invariant testing: the sorted output is a permutation of the input; the heap
        property holds after every operation. `[BUILD]` `[X-REF 16]`
3.21.12 Fuzzing for the adversarial input that triggers the worst case. `[X-REF 16]`
3.21.13 Assertion-based invariant checks compiled out in production (`assert` + `-ea`).
3.21.14 Visualising a structure for debugging: printing a tree by level, printing a DP table, and
        printing a graph as an adjacency dump. `[BUILD]`

*(14 leaves)*

## §3.22 Version history of the algorithms in the JDK

3.22.1 Java 1.2: the Collections Framework; `Collections.sort` as a merge sort.
3.22.2 Java 1.4/5: `Arrays.sort` for primitives as a tuned single-pivot quicksort.
3.22.3 Java 7: **TimSort** replaces merge sort for objects; **dual-pivot quicksort** replaces
       single-pivot for primitives; `String.substring` stops sharing the backing array.
       `[VERSION-TRAP]` `[RESEARCH]`
3.22.4 Java 8: `HashMap` treeification (`TREEIFY_THRESHOLD = 8`), the order-preserving lo/hi resize
       split, `Collections.sort` delegating to `List.sort`, streams and `Spliterator`. `[X-REF 02]`
3.22.5 Java 8: `ConcurrentHashMap` rewritten from segments to per-bin CAS. `[VERSION-TRAP]`
       `[X-REF 05]`
3.22.6 Java 9: compact strings (`byte[]` + coder); `ArrayDeque` drops the power-of-two capacity
       requirement; `List.of`/`Set.of`/`Map.of`. `[VERSION-TRAP]` `[X-REF 02]`
3.22.7 Java 11: `Collection.toArray(IntFunction)`, `String.repeat`/`strip`/`isBlank`/`lines`.
3.22.8 Java 13: `String.hashCode`'s `hashIsZero` flag. `[X-REF 02]`
3.22.9 Java 14: `DualPivotQuicksort` rewrite — insertion sort for tiny arrays, counting sort for
       `byte`/`char`/`short`, structure detection, heapsort depth fallback. `[RESEARCH]`
3.22.10 Java 16: `Stream.toList()`; records finalised.
3.22.11 Java 17: sealed types; `Map.Entry.copyOf`; the pseudo-random-number-generator interfaces
        (`RandomGenerator`). `[RESEARCH]`
3.22.12 Java 19: `HashMap.newHashMap(n)` and friends, removing the `/0.75f` arithmetic. `[NUM]`
        `[X-REF 02]`
3.22.13 Java 21: sequenced collections (JEP 431); `Math.clamp`; `Character.isEmoji`; virtual threads
        (growable stacks). `[RESEARCH]`
3.22.14 Java 22–25: no new collection or algorithm types; `Stream.gather`/`Gatherer` (24) as the
        adjacent addition; Vector API still incubating; Java 25 is the current LTS (2025-09-16).
        `[RESEARCH]`
3.22.15 The compatibility lesson: every one of these changes was invisible to correct code and broke
        code that depended on unspecified behaviour (iteration order, sort stability, `substring`
        aliasing). `[TRAP]`

*(15 leaves)*

---

**PART 3 total: 401 leaves**

---

# PART 4 — BUILD IT

Every leaf in this part is `[BUILD]`: complete, compiling, generic Java 21, followed by a
**Diff vs the real one** table (bounds checks, intrinsics, null policy, `modCount`/fail-fast,
serialization, `Spliterator`, allocation tricks, and why the real implementation bothers). Where
there is no JDK counterpart, the diff table compares against the canonical reference implementation
named in the leaf.

## §4.1 Linear structures

4.1.1 `DynamicArray<E>` — `Object[]`, size, 1.5× growth via `oldCapacity + (oldCapacity >> 1)`,
      `ensureCapacity`, `trimToSize`, `add`, `add(int,E)`, `remove(int)`, `set`, `get`,
      `indexOf`, `iterator`. Diff vs `java.util.ArrayList`.
4.1.2 The same class with an explicit operation counter, to run the §3.21.3 doubling experiment
      against the amortization proof. Diff vs the proof's prediction.
4.1.3 `SinglyLinkedList<E>` with a dummy head — `addFirst`, `addLast`, `remove`, `reverse`,
      `middle`, `hasCycle`, `iterator`. Diff vs `java.util.LinkedList`.
4.1.4 `DoublyLinkedList<E>` with head and tail sentinels, used later as the LRU's backbone.
      Diff vs `LinkedList`.
4.1.5 `ArrayStack<E>` on a growable array. Diff vs `ArrayDeque`-as-stack and `java.util.Stack`.
4.1.6 `LinkedStack<E>`. Diff vs `ArrayStack` on allocation and locality.
4.1.7 `CircularQueue<E>` — fixed capacity, head/tail/size, the full-vs-empty resolution.
      Diff vs `ArrayBlockingQueue`.
4.1.8 `CircularDeque<E>` with growth, mirroring `ArrayDeque`'s `inc`/`dec`/`sub` helpers and its
      `16 + 1` initial capacity. Diff vs `java.util.ArrayDeque` (including the Java 21 non-power-of-two
      design).
4.1.9 `MinStack` — the auxiliary-stack version and the single-stack encoded-delta version, both.
      Diff vs each other on space.
4.1.10 `MinQueue` — O(1) minimum over a queue via two monotonic stacks. Diff vs the monotonic-deque
       version.
4.1.11 `QueueUsingTwoStacks` with the amortized-O(1) transfer. Diff vs `ArrayDeque`.
4.1.12 `StackUsingTwoQueues` (both the costly-push and costly-pop variants). Diff vs each other.

*(12 leaves)*

## §4.2 Hashing

4.2.1 `ChainedHashMap<K,V>` — bucket array, singly-linked nodes, `hash()` spread `h ^ (h >>> 16)`,
      power-of-two capacity, `DEFAULT_CAPACITY = 16`, `LOAD_FACTOR = 0.75f`, resize with the lo/hi
      split, `get`/`put`/`remove`/`containsKey`/`size`/`entrySet`. Diff vs `java.util.HashMap`
      (treeification, `MIN_TREEIFY_CAPACITY`, `Node`/`TreeNode`, `afterNode*` hooks, fail-fast
      iterators, serialization, null-key handling).
4.2.2 The same map with **open addressing and linear probing**, including tombstone deletion and
      the α = 0.5 resize threshold. Diff vs the chained version and vs `IdentityHashMap`.
4.2.3 `HashSet<E>` as a wrapper over 4.2.1 with a `PRESENT` sentinel. Diff vs `java.util.HashSet`.
4.2.4 `RollingHash` — polynomial hash with `long` arithmetic, two moduli, `hashOf(l, r)` in O(1)
      after O(n) prefix precomputation. Diff vs `String.hashCode` and vs Rabin–Karp's incremental
      form.
4.2.5 `BloomFilter` — `long[]` bit array, k derived hashes from two base hashes, `add`/`mightContain`,
      the m and k sizing formulas from a target false-positive rate. Diff vs Guava's
      `BloomFilter`.
4.2.6 `CountMinSketch` — d×w counters, `add`/`estimate`, the ε/δ sizing. Diff vs a real
      `HashMap` frequency count on space and accuracy.
4.2.7 `LinearProbingCounter` — an `int`-keyed `int` counter map with no boxing, as the
      competitive-programming primitive. Diff vs `HashMap<Integer,Integer>` on footprint and
      throughput.

*(7 leaves)*

## §4.3 Heaps

4.3.1 `BinaryHeap<E>` — array-backed, `Comparator`, `siftUp`/`siftDown` with the hole
      optimization, `offer`/`poll`/`peek`/`size`, O(n) `heapify` constructor, growth `< 64 ? 2n+2 :
      1.5n`. Diff vs `java.util.PriorityQueue` (the `forgetMeNot` removal fix-up, the duplicated
      comparator/comparable sift methods, `Spliterator`, serialization).
4.3.2 `IndexedPriorityQueue` — `heap[]`, `pos[]`, `key[]`, supporting `decreaseKey`, `contains`,
      and `remove` in O(log n). Diff vs `PriorityQueue` (which cannot do any of the three in
      better than O(n)).
4.3.3 `Heapsort` in place, with the descending-comparator max-heap trick. Diff vs
      `Arrays.sort(int[])`.
4.3.4 `DAryHeap` parameterised on d, with the `siftDown` child loop. Diff vs the binary heap on
      Dijkstra.
4.3.5 `MedianFinder` — two heaps with the size invariant, `addNum`/`findMedian`. Diff vs a
      `TreeMap`-based order-statistic solution.
4.3.6 `SlidingWindowMedian` — two `TreeSet`s of indices, or two heaps with lazy deletion. Diff vs
      each other on complexity and code size.
4.3.7 `KWayMerge` over `k` iterators with a heap of heads. Diff vs `Stream.concat().sorted()`.
4.3.8 `TopKFrequent` in O(n) by bucketing on frequency. Diff vs the heap solution.

*(8 leaves)*

## §4.4 Trees

4.4.1 `BST<K,V>` — recursive and iterative `put`/`get`/`remove` (all three delete cases),
      `min`/`max`/`floor`/`ceiling`, `size` augmentation, `kthSmallest`, `rank`, inorder iterator.
      Diff vs `TreeMap`.
4.4.2 `AVLTree<K,V>` — height field, balance factor, the four rotation cases, insert and delete
      rebalancing. Diff vs `TreeMap`'s red-black policy (rotation counts, lookup depth).
4.4.3 `RedBlackTree<K,V>` — the five invariants, `fixAfterInsertion`, `fixAfterDeletion`, and an
      invariant-checking `assertInvariants()` method. Diff vs `java.util.TreeMap` source.
4.4.4 `Treap<K,V>` — random priorities, `split`/`merge`, insert and delete built from them.
      Diff vs the AVL tree on code size and guarantees.
4.4.5 `SkipList<K,V>` — probabilistic levels with p = 0.5, `MAX_LEVEL`, `get`/`put`/`remove`,
      `randomLevel()`. Diff vs `ConcurrentSkipListMap`.
4.4.6 `OrderStatisticTree` — subtree sizes on top of 4.4.2, giving `select(k)` and `rank(key)`.
      Diff vs `TreeMap` (which cannot do either in O(log n)).
4.4.7 `IntervalTree` — max-endpoint augmentation, `stabbingQuery`, `overlapQuery`. Diff vs a
      sorted-interval + binary-search approach.
4.4.8 `IterativeTraversals` — preorder (one stack), inorder (stack + left-descent), postorder
      (two-stack and single-stack `lastVisited` versions), level order. Diff vs the recursive
      versions on stack usage.
4.4.9 `MorrisTraversal` — O(1)-space inorder and preorder via threading, with the unthreading step.
      Diff vs the stack-based iterator.
4.4.10 `TreeCodec` — preorder serialize/deserialize with null markers, and the level-order variant.
       Diff vs `java.io.Serializable` on a tree of records.
4.4.11 `TreeBuilder` — construct from preorder+inorder in O(n) with an index map; and from a sorted
       array. Diff vs the O(n²) naive index-scan version.
4.4.12 `BinaryLiftingLCA` — `up[LOG][n]` table, `depth[]`, `lca(u,v)`, `kthAncestor`, `distance`.
       Diff vs the Euler-tour + sparse-table O(1)-query version.
4.4.13 `Trie` — dense `TrieNode[26]`, `insert`/`search`/`startsWith`/`delete`/`countWordsWithPrefix`.
       Diff vs a `HashMap`-per-node trie and vs `HashSet<String>`.
4.4.14 `WildcardTrie` — `.`-matching search via DFS over children. Diff vs a regex-based
       dictionary.
4.4.15 `BinaryXorTrie` — 32-level bitwise trie for maximum-XOR queries, with counts for deletion.
       Diff vs the O(n²) pairwise scan.
4.4.16 `AhoCorasick` — trie + BFS-built failure links + output links, `findAll`. Diff vs running
       KMP once per pattern.

*(16 leaves)*

## §4.5 Range-query structures

4.5.1 `PrefixSums` (1-D and 2-D) with the four-term rectangle query. Diff vs recomputing.
4.5.2 `DifferenceArray` (1-D and 2-D) with the materialise pass. Diff vs a Fenwick range update.
4.5.3 `FenwickTree` — `update`, `prefixQuery`, `rangeQuery`, O(n) build, and the
      `lowerBound(target)` descent. Diff vs a segment tree (size, constant factor, capability).
4.5.4 `FenwickTree2D`. Diff vs a 2-D segment tree.
4.5.5 `SegmentTree` — generic over a monoid (identity + associative merge), `build`, point `update`,
      `query`, in a `4n` array. Diff vs `FenwickTree` and vs `TreeMap`.
4.5.6 `LazySegmentTree` — range assign and range add with `push`/`pull`. Diff vs the point-update
      tree.
4.5.7 `SparseTable` — O(n log n) build, O(1) idempotent query, with the
      `31 - numberOfLeadingZeros` log trick. Diff vs the segment tree (immutability for O(1)).
4.5.8 `SqrtDecomposition` — block sums with O(1) update and O(√n) query. Diff vs Fenwick.
4.5.9 `DisjointSetUnion` — path compression (iterative two-pass) + union by size, `find`, `union`,
      `connected`, `componentCount`, `componentSize`. Diff vs a Guava/JGraphT equivalent and vs
      BFS-based connectivity.
4.5.10 `WeightedDSU` — potential/weight along parent edges, for "evaluate division". Diff vs a
       DFS-per-query solution.
4.5.11 `ParityDSU` — bipartiteness checking. Diff vs BFS 2-colouring.

*(11 leaves)*

## §4.6 Sorting and selection

4.6.1 `InsertionSort` (with the binary-insertion variant). Diff vs `DualPivotQuicksort`'s small-array
      path.
4.6.2 `SelectionSort` and `BubbleSort` with the early-exit flag, kept for the write-count and
      adaptivity arguments. Diff vs each other.
4.6.3 `MergeSort` — top-down with a reused scratch array, and bottom-up iterative. Diff vs
      `TimSort` (run detection, galloping, `MIN_MERGE`).
4.6.4 `QuickSort` — Lomuto, Hoare, and three-way (Dutch national flag) partitions; random pivot;
      tail-loop on the larger side; insertion-sort cutoff at 32. Diff vs
      `DualPivotQuicksort` (two pivots, counting sort for narrow types, heapsort depth fallback).
4.6.5 `HeapSort`. Diff vs `QuickSort` on locality.
4.6.6 `CountingSort` — with the stable backward placement pass. Diff vs
      `DualPivotQuicksort`'s counting-sort path for `byte`/`char`/`short`.
4.6.7 `RadixSort` — LSD over 8-bit digits with negative-number handling. Diff vs `Arrays.sort`.
4.6.8 `BucketSort` for uniformly distributed doubles. Diff vs `Arrays.sort(double[])`.
4.6.9 `QuickSelect` — random pivot, iterative loop version. Diff vs `Arrays.sort` + index, and vs a
      size-k heap.
4.6.10 `MedianOfMedians` deterministic selection. Diff vs `QuickSelect` on constants.
4.6.11 `CountInversions` via merge sort. Diff vs the Fenwick-tree solution.
4.6.12 `ExternalMergeSort` over files with a k-way heap merge. Diff vs an in-memory sort.
4.6.13 `SortByValue` — map → `LinkedHashMap` ordered by value. Diff vs a `TreeMap` keyed by value.
4.6.14 `TimSortLite` — run detection + `minRunLength` + merge stack with the collapse invariants,
       as a readable subset. Diff vs the real `java.util.TimSort` (galloping, `MIN_GALLOP`,
       stack sizing after the de Gouw fix).

*(14 leaves)*

## §4.7 Searching and array patterns

4.7.1 `BinarySearch` — the half-open template, `lowerBound`, `upperBound`, `equalRange`, and a
      predicate-based `firstTrue`. Diff vs `Arrays.binarySearch` (including its return encoding).
4.7.2 `BinarySearchOnAnswer` — a generic `firstFeasible(lo, hi, IntPredicate)` plus the shipping,
      Koko, and split-array instantiations. Diff vs a linear scan of the answer space.
4.7.3 `RotatedArraySearch` — with and without duplicates. Diff vs sorting first.
4.7.4 `MedianOfTwoSortedArrays` in O(log min(m,n)). Diff vs the O(m+n) merge.
4.7.5 `ExponentialSearch` on an unbounded reader. Diff vs plain binary search.
4.7.6 `TwoPointers` — sorted two-sum, three-sum with duplicate skipping, container with most water,
      remove duplicates in place. Diff vs the O(n²)/O(n³) brute force.
4.7.7 `SlidingWindow` — both templates (longest-valid and shortest-valid) as reusable methods, plus
      minimum-window-substring and longest-substring-without-repeats. Diff vs the O(n²) scan.
4.7.8 `MonotonicStack` — a generic `nextGreater`/`previousSmaller` utility over an `int[]`, plus
      largest-rectangle-in-histogram and trapping-rain-water built on it. Diff vs the O(n²) scan
      and vs the two-pointer rain-water solution.
4.7.9 `MonotonicDeque` — sliding-window maximum, and the shortest-subarray-with-sum-≥-k variant.
      Diff vs the heap solution.
4.7.10 `CyclicSort` — first missing positive, find all duplicates. Diff vs the `HashSet` solution
       on space.
4.7.11 `DutchNationalFlag` — sort colors. Diff vs counting sort.
4.7.12 `ArrayRotation` — three-reversal and juggling/GCD-cycle versions. Diff vs the O(n)-extra-space
       copy.
4.7.13 `NextPermutation`. Diff vs generating all permutations.
4.7.14 `Kadane` — maximum subarray, maximum product subarray, circular maximum subarray. Diff vs
       the O(n²) prefix scan and vs the divide-and-conquer version.
4.7.15 `BoyerMooreMajority` — with the verification pass and the n/3 generalisation. Diff vs a
       frequency map.
4.7.16 `MatrixOps` — rotate 90° in place, spiral traversal, set-zeroes in O(1) space, transpose.
       Diff vs copying into a new matrix.
4.7.17 `ReservoirSampling` and `FisherYatesShuffle` (with the biased version shown and rejected).
       Diff vs `Collections.shuffle`.
4.7.18 `WeightedRandomPicker` — prefix sums + binary search. Diff vs a rejection-sampling version.

*(18 leaves)*

## §4.8 Graphs

4.8.1 `Graph` — adjacency list, adjacency matrix, and CSR representations behind one interface,
      with builders from an edge list. Diff vs JGraphT and Guava `Graph`.
4.8.2 `Bfs` — distances, parents, path reconstruction, and multi-source seeding. Diff vs a
      library BFS.
4.8.3 `Dfs` — recursive and explicit-stack, with discovery/finish times and edge classification.
      Diff vs the recursive version's stack limits.
4.8.4 `TopologicalSort` — Kahn with in-degrees (and cycle reporting) and the DFS post-order version.
      Diff vs each other on order determinism.
4.8.5 `Dijkstra` — binary-heap frontier with lazy deletion and the stale-entry skip; an
      `IndexedPriorityQueue` variant; an O(V²) array variant. Diff of the three on complexity.
4.8.6 `BellmanFord` — V−1 rounds, early exit, negative-cycle detection and cycle extraction.
      Diff vs Dijkstra.
4.8.7 `FloydWarshall` — with `next[][]` path reconstruction and negative-cycle detection on the
      diagonal. Diff vs running Dijkstra V times.
4.8.8 `Kruskal` — edge sort + DSU. Diff vs `Prim`.
4.8.9 `Prim` — heap frontier and the O(V²) dense variant. Diff vs `Kruskal` on dense input.
4.8.10 `TarjanScc` and `KosarajuScc`, plus the condensation-graph builder. Diff of the two.
4.8.11 `BridgesAndArticulationPoints` — one DFS with `low`-link, both outputs. Diff vs
       remove-an-edge-and-recheck-connectivity.
4.8.12 `Hierholzer` — Eulerian path/circuit with the degree precondition checks. Diff vs a
       backtracking search.
4.8.13 `ZeroOneBfs` with a deque. Diff vs Dijkstra on a 0/1-weighted graph.
4.8.14 `BidirectionalBfs` on an implicit word-ladder graph. Diff vs single-source BFS on node count.
4.8.15 `AStar` on a grid with the Manhattan heuristic. Diff vs Dijkstra on expanded nodes.
4.8.16 `GridSearch` — flood fill, island counting, and shortest path on a grid with a
       state-extended visited set (keys/obstacle-removals). Diff vs a general graph search on the
       same input.
4.8.17 `Hopcroft Karp` bipartite matching (or Kuhn's algorithm as the simpler version). Diff vs a
       max-flow formulation.
4.8.18 `Dinic` max flow with level graphs. Diff vs Edmonds–Karp.

*(18 leaves)*

## §4.9 Dynamic programming and recursion

4.9.1 `Fib` in five forms — naive, memoized, tabulated, two-variable, and matrix exponentiation —
      with the measured operation counts of each. Diff table across all five.
4.9.2 `CoinChange` — min coins and count-ways, top-down and bottom-up, with the 1-D loop-direction
      contrast against 4.9.3.
4.9.3 `Knapsack` — 0/1 and unbounded, full table then one row, with the reconstruction of the chosen
      items. Diff of the two loop directions.
4.9.4 `Lis` — O(n²) DP and O(n log n) tails-array with `Arrays.binarySearch`, plus actual-subsequence
      reconstruction. Diff of the two.
4.9.5 `EditDistance` — full table, one-row optimization, and Hirschberg's O(n)-space alignment.
      Diff of the three.
4.9.6 `Lcs` — table, reconstruction, and the space-optimized length-only version. Diff vs
      `EditDistance` (same table, different transitions).
4.9.7 `MatrixChainOrder` — interval DP with the parenthesisation output. Diff vs a greedy heuristic.
4.9.8 `BurstBalloons` — the reversed-thinking interval DP. Diff vs backtracking.
4.9.9 `TspBitmask` — `dp[1<<n][n]`, with the 2^20 feasibility arithmetic. Diff vs brute-force
      permutations.
4.9.10 `DigitDp` — count numbers ≤ N with a digit property, with the (pos, tight, state) memo.
       Diff vs iterating every number.
4.9.11 `TreeDp` — house-robber-on-a-tree and tree diameter with one DFS each. Diff vs the
       recompute-per-node version.
4.9.12 `StockDp` — buy/sell I–IV plus cooldown and fee, as one state-machine template. Diff vs the
       four separate solutions.
4.9.13 `Backtracking` — subsets, subsets-with-duplicates, permutations, permutations-with-duplicates,
       combination sum, from one template. Diff of the five loop shapes.
4.9.14 `NQueens` with three boolean conflict arrays, and the bitmask version. Diff of the two.
4.9.15 `SudokuSolver` with the 27 constraint sets and the most-constrained-cell heuristic. Diff vs
       plain left-to-right backtracking on node count.
4.9.16 `WordSearchII` — grid DFS driven by a trie. Diff vs one DFS per word.
4.9.17 `RecursionToIteration` — the same tree traversal as recursion, explicit stack, trampoline,
       and manual tail-call loop. Diff of the four on stack usage.
4.9.18 `Memoizer<K,V>` — a reusable memo wrapper around a recursive function, and why the
       `ConcurrentHashMap.computeIfAbsent` version is illegal. Diff vs a hand-rolled `HashMap` memo.

*(18 leaves)*

## §4.10 Strings

4.10.1 `Kmp` — the π-array builder plus `search` returning all match positions, and the
       period/`repeatedSubstringPattern` application. Diff vs `String.indexOf`.
4.10.2 `ZFunction` with the `search` application via `pattern + ' ' + text`. Diff vs `Kmp`.
4.10.3 `RabinKarp` — rolling hash with two moduli and the verification step. Diff vs `Kmp` on
       worst-case guarantees.
4.10.4 `Manacher` — all palindromic radii in O(n), plus longest-palindromic-substring and
       count-palindromic-substrings on top. Diff vs the O(n²) expand-from-centre version.
4.10.5 `SuffixArray` — O(n log² n) doubling construction plus Kasai's LCP array, with
       longest-repeated-substring and distinct-substring-count applications. Diff vs a suffix tree.
4.10.6 `StringBuilderIdioms` — reverse, palindrome check, run-length encode/decode, and the
       O(n²)-to-O(n) contrast against `String +=`. Diff vs `String` concatenation, measured.
4.10.7 `AnagramGrouping` — sorted-key and count-signature versions. Diff of the two on complexity
       (O(n·k log k) vs O(n·k)).

*(7 leaves)*

## §4.11 Designed structures

4.11.1 `LruCache<K,V>` — `HashMap` + doubly-linked list with sentinels, O(1) `get`/`put`. Diff vs
       `LinkedHashMap` with `accessOrder` + `removeEldestEntry`, and vs Caffeine (TinyLFU,
       expiry, weak keys, statistics).
4.11.2 `LfuCache<K,V>` — frequency buckets, `minFreq`, O(1) amortized. Diff vs `LruCache`.
4.11.3 `RandomizedSet<E>` — `ArrayList` + index map, swap-with-last removal, O(1) `getRandom`;
       and the multiset variant. Diff vs `HashSet` (which cannot do `getRandom` in O(1)).
4.11.4 `TimeMap` — `HashMap<String, ArrayList<Entry>>` + binary search on the timestamp. Diff vs a
       `TreeMap<Integer,V>` per key.
4.11.5 `SnapshotArray` — per-index (snapId, value) history + binary search. Diff vs copying the
       whole array per snapshot.
4.11.6 `RangeModule` — `TreeMap` of disjoint intervals with `addRange`/`removeRange`/`queryRange`.
       Diff vs a boolean array.
4.11.7 `RateLimiter` — fixed window, sliding-window log (deque of timestamps), and token bucket.
       Diff of the three on memory and burst behaviour. `[X-REF 22]`
4.11.8 `HitCounter` — circular buffer of second-buckets. Diff vs the deque-of-timestamps version.
4.11.9 `Iterators` — `PeekingIterator`, `NestedIterator` (flatten a nested list lazily),
       `BstIterator` (controlled inorder, O(h) space), `ZigzagIterator`. Diff vs eager flattening.
4.11.10 `Leaderboard` — `TreeMap` by score and the Fenwick-by-score variant for rank queries.
        Diff of the two.
4.11.11 `MedianOfStream` cross-referenced to 4.3.5, and `FirstUniqueNumber` (`LinkedHashMap` +
        queue). Diff vs rescanning.

*(11 leaves)*

## §4.12 Verification harness

4.12.1 `BruteForceOracle` — a JUnit 5 property test that runs the optimized implementation against
        a deliberately naive one on random inputs, with a shrinking failure reporter. Diff vs
        example-based unit tests. `[X-REF 16]`
4.12.2 `InvariantChecker` — assert the heap property, the BST invariant, the red-black invariants,
        and the DSU rank bound after every operation in a randomized test. `[X-REF 16]`
4.12.3 `ComplexityProbe` — the doubling experiment as a runnable class that prints the inferred
        exponent for a supplied `IntConsumer` workload. Diff vs a JMH benchmark.
4.12.4 `AdversarialInputs` — generators for the quicksort killer sequence, the hash-collision key
        set (`"Aa"`/`"BB"` style), and the catastrophic-backtracking regex input. Diff vs random
        inputs on what they detect. `[X-REF 13]`
4.12.5 `Jmh` — one benchmark class comparing `ArrayList` vs `LinkedList` insert-in-middle across
        sizes, with `@Fork`, `@Warmup`, and a `Blackhole`, plus the interpretation of the result.
        `[X-REF 06]`

*(5 leaves)*

---

**PART 4 total: 145 leaves**

---

# PART 5 — INTERVIEW & RETENTION

## §5.1 The questions, with the answer shape

5.1.1 "What is Big-O, and what is the difference between O, Θ, and Ω?" — including the
      not-worst-case correction.
5.1.2 "What is amortized complexity, and how is it different from average case?"
5.1.3 "Prove that `ArrayList.add` is amortized O(1)." — all three methods, pick one.
5.1.4 "Why 1.5× and not 2× growth?"
5.1.5 "Does space complexity include the recursion stack?"
5.1.6 "What is the complexity of building a string in a loop with `+`?"
5.1.7 "How does a hash table achieve O(1), and when does it not?"
5.1.8 "What is the `equals`/`hashCode` contract, and what breaks if you violate it?"
5.1.9 "Can two unequal objects share a hash code? Can two equal objects differ?"
5.1.10 "What happens if you mutate a key after putting it in a map?"
5.1.11 "Why does `HashMap` treeify, and at what threshold?"
5.1.12 "What is a hash-collision DoS and how did the JDK respond?"
5.1.13 "`ArrayList` vs `LinkedList` — when would you actually use `LinkedList`?"
5.1.14 "Why is `ArrayDeque` the right stack in Java?"
5.1.15 "How do you detect a cycle in a linked list, and how do you find its start?"
5.1.16 "Reverse a linked list iteratively — and then in groups of k."
5.1.17 "How do you find the middle of a linked list in one pass?"
5.1.18 "Why is a monotonic stack O(n) when it has a nested `while`?"
5.1.19 "Solve largest-rectangle-in-histogram and explain the stack invariant."
5.1.20 "What is the sliding-window pattern, and when does it break?"
5.1.21 "Longest substring without repeating characters — and then minimum window substring."
5.1.22 "How do you handle a subarray-sum problem when values can be negative?"
5.1.23 "Explain the two-pointer discard argument in sorted two-sum."
5.1.24 "Solve three-sum and justify the complexity."
5.1.25 "Write binary search and explain why it terminates."
5.1.26 "What is wrong with `(lo + hi) / 2`?"
5.1.27 "Write lower-bound and upper-bound, and explain the difference."
5.1.28 "Search a rotated sorted array — what changes with duplicates?"
5.1.29 "Find the median of two sorted arrays in logarithmic time."
5.1.30 "What is binary search on the answer? Give two examples."
5.1.31 "How do you validate a BST?"
5.1.32 "What is a balanced tree, and how does a red-black tree stay balanced?"
5.1.33 "AVL vs red-black — which would you pick and why?"
5.1.34 "Why is `TreeMap` O(log n) and `HashMap` O(1)? When would you still choose `TreeMap`?"
5.1.35 "Find the LCA in a binary tree, and then in a BST."
5.1.36 "Compute the diameter of a binary tree."
5.1.37 "Serialize and deserialize a binary tree."
5.1.38 "Do an inorder traversal in O(1) space."
5.1.39 "How does a binary heap work? Why is `heapify` O(n)?"
5.1.40 "Which heap polarity do you use for the k largest elements, and why?"
5.1.41 "Find the kth largest element — give three approaches and pick one."
5.1.42 "Design a running-median structure."
5.1.43 "Merge k sorted lists."
5.1.44 "Why isn't `PriorityQueue` iteration sorted?"
5.1.45 "BFS vs DFS — when do you use each?"
5.1.46 "Why does BFS give the shortest path on an unweighted graph?"
5.1.47 "Where do you mark a node visited in BFS, and why?"
5.1.48 "Detect a cycle in a directed graph, and then in an undirected one."
5.1.49 "Explain topological sort, both algorithms, and how it detects cycles."
5.1.50 "Explain Dijkstra and prove why it needs non-negative weights."
5.1.51 "What do you use when weights can be negative?"
5.1.52 "Why must `k` be the outer loop in Floyd–Warshall?"
5.1.53 "Explain Kruskal and Prim, and when each wins."
5.1.54 "What is the cut property?"
5.1.55 "Explain union-find with both optimizations, and state the complexity honestly."
5.1.56 "What can union-find not do?"
5.1.57 "How does a trie work, and when does it beat a hash set?"
5.1.58 "Why is Word Search II tractable?"
5.1.59 "How much memory does a trie for 100 000 English words use?"
5.1.60 "What is dynamic programming? What are the two required properties?"
5.1.61 "Memoization vs tabulation — pick one and justify."
5.1.62 "Solve coin change both ways and explain the loop direction."
5.1.63 "Why does the 0/1-knapsack inner loop go descending?"
5.1.64 "Knapsack is O(nW) — so why is it NP-hard?"
5.1.65 "Explain edit distance's recurrence."
5.1.66 "Solve LIS in O(n log n) and explain why the tails array is sorted."
5.1.67 "How do you reconstruct the actual solution from a DP table?"
5.1.68 "When is greedy correct? Prove it for interval scheduling."
5.1.69 "Give me a problem where greedy fails and DP works."
5.1.70 "Sort by end time or start time — which and why?"
5.1.71 "Which sort does Java use, and why two different ones?"
5.1.72 "What is stability, and when does it matter?"
5.1.73 "Prove the Ω(n log n) comparison-sorting lower bound."
5.1.74 "When can you sort in linear time?"
5.1.75 "Why does `Collections.sort` sometimes throw 'Comparison method violates its general
       contract'?"
5.1.76 "Explain quickselect and its worst case. How do you make it worst-case linear?"
5.1.77 "Design an LRU cache." — and the follow-up "without `LinkedHashMap`".
5.1.78 "Design a structure with O(1) insert, delete, and getRandom."
5.1.79 "Design a rate limiter." `[X-REF 22]`
5.1.80 "Design an autocomplete."
5.1.81 "How would you find the top k elements of a stream of a billion numbers?"
5.1.82 "How do you compute range sums with updates?"
5.1.83 "Explain Fenwick vs segment tree."
5.1.84 "Explain KMP's failure function."
5.1.85 "How do you find all palindromic substrings in linear time?"
5.1.86 "What is a rolling hash, and how do you make it collision-resistant?"
5.1.87 "Count the bits set in an integer — three ways."
5.1.88 "Find the single number when every other element appears twice; then thrice."
5.1.89 "Enumerate all subsets, iteratively and recursively."
5.1.90 "Explain backtracking's undo step and why you copy at the leaf."
5.1.91 "How do you handle duplicates in permutations?"
5.1.92 "What is the complexity of generating all subsets, and of all permutations?"
5.1.93 "Why does deep recursion crash in Java but not in Scheme?"
5.1.94 "Given n ≤ 20, what complexity class is the intended solution?"
5.1.95 "The constraint says n ≤ 10⁹ — what does that tell you?"
5.1.96 "How would you verify your algorithm is correct without the judge?"
5.1.97 "How would you find an accidental O(n²) in a production service?"
5.1.98 "Your solution passes but times out. What do you look at first?"
5.1.99 "This problem is NP-hard. What do you do?"
5.1.100 "Walk me from the brute force to the optimal solution and state every complexity along the
        way."

*(100 leaves)*

## §5.2 The trap index

5.2.1 One consolidated table of every `**Trap:**` in the file: the wrong belief, the symptom, the
      fix — usable as a pre-interview scan.
5.2.2 The notation-stale table: "O is worst case", "Θ is average case", "amortized means fast",
      "O(1) means fast", "log base matters", "constants never matter".
5.2.3 The version-stale table: `String.substring` sharing (pre-Java 7), `Collections.sort` as merge
      sort (pre-7), `ArrayDeque` power-of-two capacity (pre-9), `ConcurrentHashMap` segments
      (pre-8), "`HashMap` rehashes on resize" (pre-8).
5.2.4 The five most expensive real-world algorithm mistakes: unbounded memo/cache, mutable map key,
      accidental O(n²) via `contains`/`substring`/`+=`, unsorted `binarySearch`, and an amortized
      structure on a p99-sensitive path.
5.2.5 The seven off-by-one hotspots: binary-search bounds, prefix-sum indices, window boundaries,
      `mid` in a rotated array, level-order `size()` capture, 0- vs 1-indexed Fenwick, and inclusive
      vs exclusive interval ends.
5.2.6 The overflow hotspot list: `(lo+hi)/2`, prefix sums, `a-b` comparators, `1<<31`, factorials,
      `Math.abs(MIN_VALUE)`, product accumulation.

*(6 leaves)*

## §5.3 Drills and retention

5.3.1 The numbers drill: recite every constant with its value — 16, 0.75, 8, 6, 64, 1<<30, 1.5×,
      11, 17, 32 (`MIN_MERGE`), 7 (`MIN_GALLOP`), 5000, 8192, 10⁹+7, 26, 64 B cache line, 12 B
      header, α(n) < 5. `[DRILL]`
5.3.2 The recurrence drill: 12 recurrences → closed forms, from memory. `[DRILL]`
5.3.3 The cost drill: state amortized and worst case for 25 named operations. `[DRILL]`
5.3.4 The constraint drill: 10 values of n → the intended complexity class. `[DRILL]`
5.3.5 The pattern drill: 25 problem statements → the pattern, in one word each. `[DRILL]`
5.3.6 The proof drill: state in three sentences each — amortized `ArrayList.add`, `heapify` O(n),
      the sorting lower bound, Dijkstra's finalize-on-pop, the cut property, the knapsack loop
      direction, the monotonic-stack amortization, union-find's α(n). `[DRILL]`
5.3.7 The trap drill: 20 code snippets, say what each prints or throws and why. `[DRILL]`
5.3.8 The implementation drill: write from memory, in 10 minutes each — binary search, quickselect,
      DSU, a binary heap, Kahn's algorithm, Dijkstra, KMP, the sliding-window template. `[DRILL]`
5.3.9 The complexity-derivation drill: given five unfamiliar code snippets, derive time and space.
      `[DRILL]`
5.3.10 The spaced-repetition schedule for this file: day 1 read Parts 1–2, day 2 read Part 3,
       day 3 checklist, day 5 numbers + recurrence drills, day 7 implement three Part 4 structures
       from memory, day 14 the pattern and proof drills, day 21 the full implementation drill,
       then weekly.
5.3.11 The daily practice protocol: two problems a day, one from a pattern you know and one from a
       pattern you do not, always stating complexity before coding and always writing the brute
       force first.
5.3.12 The "explain it out loud" rule: if you cannot state the mechanism in one sentence without
       looking, you do not know it yet.
5.3.13 `## Atomic concept checklist` — every one of the 24 existing checklist lines from the current
       guide preserved verbatim in substance, plus one flat line per new concept in this syllabus.

*(13 leaves)*

---

**PART 5 total: 119 leaves**

---

## Leaf counts

| Part | Leaves |
|---|---|
| PART 1 — Basics | 425 |
| PART 2 — Intermediate | 426 |
| PART 3 — Under the hood | 401 |
| PART 4 — Build it | 145 |
| PART 5 — Interview & retention | 119 |
| **Total** | **1516** |

Leaves carrying `[RESEARCH]`: **131**.
Leaves carrying `[VERSION-TRAP]`: **9** (1.3.6, 1.9.4, 1.13.12, 2.22.12, 3.22.3, 3.22.5, 3.22.6,
5.2.2, 5.2.3).
Leaves carrying `[PROVE]`: **~250**. `[SOURCE]`: **~30**. `[BUILD]`: **145** (all of Part 4) plus
~35 build-tagged leaves inside Parts 1–3. `[TRAP]`: **~150**. `[DRILL]`: **~25**.

Target version stated: **Java 21 LTS**, with Java 22–25 deltas marked inline (§3.22.14, §1.21.21).

---

## Sources consulted

| Source | What it contributed |
|---|---|
| https://cp-algorithms.com/ | The single largest source of leaves this syllabus would otherwise have missed: the full algorithm inventory by area. Directly produced §2.19 (binary exponentiation, extended Euclid, linear sieve, Montgomery multiplication, CRT), §3.13 (sparse table, sqrt decomposition, sqrt tree, Mo's algorithm, treap, randomized heap), §3.14 (Z-function, Manacher, Aho–Corasick, suffix automaton, Lyndon factorization), §3.8/§3.9 (bridges online, strong orientation, D'Esopo–Pape, 0-1 BFS, Prüfer code, Kirchhoff, second-best MST, Stoer–Wagner, MPM, push-relabel, Kuhn, Hungarian, 2-SAT, heavy-light and centroid decomposition), and §2.19.20 (Minkowski sum, Pick's theorem, monotone chain, Delaunay, half-plane intersection) |
| https://ocw.mit.edu/courses/6-006-introduction-to-algorithms-spring-2020/video_galleries/lecture-videos/ | The 21-lecture ordering, which set Part 1's sequence (dynamic arrays before hashing before sorting before trees before heaps before graph search before DP), plus the **SRTBOT** DP framing (§2.13.6), the "APSP and Johnson" pairing (§3.9.16), and the P/NP/EXP/R complexity lecture that became §3.19 |
| https://research.google/blog/extra-extra-read-all-about-it-nearly-all-binary-searches-and-mergesorts-are-broken/ | Bloch's 2006 post: the 2³⁰-element overflow threshold, the bug in Bentley's *Programming Pearls* proof, and the same bug in the JDK's own `binarySearch` — §1.19.6, §3.7.5–3.7.6 |
| https://ocw.mit.edu/courses/6-046j-design-and-analysis-of-algorithms-spring-2012/83b82d45beb3776da72b7f3e1b3f42df_MIT6_046JS12_lec11.pdf and https://cs.uwaterloo.ca/~r5olivei/courses/2021-fall-cs466/lecture01.pdf | The three amortization methods with the potential-function definition ĉᵢ = cᵢ + Φ(Dᵢ) − Φ(Dᵢ₋₁), the dynamic-table worked example, and the correction that this is CLRS **chapter 17**, not 16 — §1.6.4–1.6.7, §3.1 |
| https://builtin.com/software-engineering-perspectives/big-o-vs-big-theta and https://www.geeksforgeeks.org/dsa/difference-between-big-oh-big-omega-and-big-theta/ | The explicit statement that there is **no** one-to-one relationship between O/Ω/Θ and worst/best/average case — the single most important correction in Part 1 (§1.3.6–1.3.8) |
| https://www.designgurus.io/blog/grokking-the-coding-interview-patterns | The 20-pattern list, which added Island/matrix traversal, Bitwise XOR, Cyclic Sort, K-way Merge, Two Heaps, and Monotonic Stack as *named* patterns rather than incidental techniques — §2.6, §2.11, §2.18, §2.21.1 |
| https://medium.com/hackernoon/14-patterns-to-ace-any-coding-interview-question-c5bb3357f6ed | The original 14-pattern taxonomy, cross-checked against the 20 above; confirmed "in-place reversal of a linked list" and "modified binary search" as distinct named patterns — §1.11.11, §1.19 |
| https://neetcode.io/practice/practice/neetcode150 (via search summary) | The 18-category problem-count distribution (Graphs 19, DP 23, Trees 15, Linked List 11), used to weight Part 2's section sizes and to confirm "Advanced Graphs", "Intervals", and "Math & Geometry" as first-class categories — §2.5, §2.15, §2.19 |
| https://github.com/thepranaygupta/Data-Structures-and-Algorithms/blob/main/SYLLABUS.md | A curriculum checklist run against the leaf list; it surfaced square-root decomposition, Huffman encoding, cyclic sort as a named topic, Newton's square-root method, matrix exponentiation, A*, and the "solving linear vs divide-and-conquer recurrence relations" split — §1.5, §2.19, §3.13.3 |
| https://www.bigocheatsheet.com/ | The structure × operation complexity matrix that §2.1 must exceed; it also supplied the skip-list and B-tree rows and the Θ-vs-O column convention that §1.3.5 corrects |
| https://interviewing.io/sorting-interview-questions | The senior-level sorting expectations: quickselect for order statistics rather than a full sort, non-comparison sorts "when the problem fits", language-implementation awareness (Java dual-pivot for primitives), and the five named common mistakes — §2.8.1, §2.8.12, §3.5.10 |
| https://www.kb.cert.org/vuls/id/903934 and https://www.cvedetails.com/cve/CVE-2011-4858/ | The hash-flooding advisory and the Tomcat CVE: the O(n²) table-construction attack, the affected versions, and the "insufficiently randomized hash functions" framing — §1.10.12, §3.2.18, §3.20.2 |
| https://arxiv.org/pdf/2406.11618 (ReDoS SoK) and https://www.sonarsource.com/blog/crafting-regexes-to-avoid-stack-overflows/ | The Stack Overflow 2016 (~20 000 whitespace characters) and Cloudflare 2019 (global CPU to 100%) incidents, the `(a+)+`/`(a*)*`/`(a|aa)+` catastrophic patterns, and the possessive-quantifier/atomic-group fixes — §1.9.16, §3.20.3 |
| https://www.oracle.com/java/technologies/javase/21all-relnotes.html and https://www.oracle.com/java/technologies/javase/25all-relnotes.html | `Math.clamp` with its four overloads and the `clamp(long,int,int)` narrowing form, `Character.isEmoji`, sequenced collections, and the confirmation that Java 22–25 added nothing to the algorithm/collection surface beyond `Gatherer` (24); Java 25 LTS dated 2025-09-16 — §1.21.4, §1.21.21, §3.22.13–3.22.14 |
| https://en.wikipedia.org/wiki/Timsort | Run detection, `MIN_MERGE = 32`, `minRunLength`, galloping, the merge-stack invariants, and the de Gouw et al. verification result — §3.5.1–3.5.5 |
| https://shipilev.net/jvm/objects-inside-out/ | The 12-byte header (8 mark + 4 compressed klass), 16-byte array header, 8-byte alignment, `Integer` = 16 B, `Long` = 24 B, and the compressed-oops 32 GB boundary — §1.7.9, §3.16.1–3.16.5 |
| https://leetcode.com/discuss/study-guide/1437879/dynamic-programming-patterns/ and https://aman.ai/code/dp/ | The DP pattern taxonomy that §2.13 is organised around: 1-D, 2-D grid, knapsack, LIS/LCS, interval, bitmask, digit, tree, state-machine, minimax, probability — and the confirmation that digit DP and SOS DP are named patterns worth leaves |
| https://www.geeksforgeeks.org/blogs/top-algorithms-and-data-structures-for-competitive-programming/ and https://www.codechef.com/roadmap/data-structures-and-algorithms | Completeness probes; they added segment trees, binary indexed trees, square-root decomposition, meet-in-the-middle, inclusion–exclusion, game theory, and bitmasking as topics the current guide omits entirely |

Searches that returned nothing usable: the CLRS 4th-edition table-of-contents query returned only
PDF mirrors and bookseller pages, so the CLRS chapter mapping in §1.1.7 and §1.5.8 is tagged
`[RESEARCH]` and must be verified against the MIT Press page before the write pass states chapter
numbers (the amortization search already corrected one such number from 16 to 17). The
`roadmap.sh/datastructures-and-algorithms` fetch returned only page chrome, not the roadmap nodes,
so nothing was taken from it. Several `[RESEARCH]` leaves — Hibbard-deletion's √n result (§1.15.4),
Knuth's linear-probing probe formula (§3.2.6), the average-O(1) heap insert (§3.3.8), Brent's
cycle algorithm (§1.11.10), the `String.indexOf` intrinsic (§3.14.18), and the JVM per-frame byte
cost (§3.17.1) — rest on recall and named primary sources not yet fetched; the write pass must
confirm each against its source before publishing the number.

---

## Gaps vs the current guide

`src/topics/01-dsa-fundamentals.md` is 459 lines across 18 sections plus a 24-line atomic concept
checklist. Every concept in it maps to a leaf below and **nothing is dropped**. The current guide is
a breadth-first orientation: it names the right things and states the right traps, but it asserts
rather than proves, contains no source, no implementations, no master cost table, and no memory
arithmetic.

| Syllabus area | Present in `src/topics/01-dsa-fundamentals.md` | Missing | Shallow |
|---|---|---|---|
| §1.1 why analysis exists | — | all 10 leaves | — |
| §1.2 machine model | — | all 9 leaves (RAM, word-RAM, cache model, decision tree, cell probe) | — |
| §1.3 asymptotic notation (23) | the 7-class table, "constants ignored", the O(n log n)-beats-O(n) remark | Ω/Θ/o/ω, the **not-worst-case** correction, quantifier definitions, growth-ordering proofs, log(n!), multi-variable, pseudo-polynomial, expected vs average, competitive ratio, galactic algorithms | one table + two sentences |
| §1.4 growth ladder (20) | the class table's "typical source" column | the n-per-class inverse table, throughput numbers, latency ladder, sum-of-n constraints, O(√n)/O(n log log n)/O(log log n) | the table exists; the *decision* use of it does not |
| §1.5 recurrences (24) | **absent entirely** | all 24 leaves — master theorem, Akra–Bazzi, recursion trees, the 12-shape cheat table, the φⁿ Fibonacci correction | — |
| §1.6 amortization (18) | the doubling series, two traps, three examples | **all three formal methods**, the potential function, the g/(g−1) generalisation, the shrink-thrashing proof, de-amortization, tail-latency | the aggregate intuition only |
| §1.7 space complexity (12) | "recursion stack counts" | in-place definitions, streaming limits, sketches, **all byte arithmetic**, stack-depth budget, output-space convention | one sentence |
| §1.8 arrays (18) | address arithmetic, cache-friendliness, O(n) shift, prefix sums/difference arrays/reversal named | row-major, jagged `int[][]`, growth factors, `System.arraycopy`, direction vectors, flattening, `Arrays` surface, the `Arrays.fill(grid,row)` trap | techniques named in one line, not taught |
| §1.9 strings (19) | compact strings, immutability, the O(n²) `+` trap | code point vs grapheme, `substring` version change, `StringBuilder` internals, `hashCode` caching, frequency representations, regex/ReDoS, the whole string-algorithm inventory | three sentences |
| §1.10 hashing (21) | bucket index, average/worst case, the contract, the mutable-key trap, five uses | avalanche, load-factor math, all six collision-resolution families, universal hashing, hash DoS, composite keys, sizing, the array-key trap | good for its length; no numbers |
| §1.11 linked lists (20) | the three mechanisms, the cycle-start trap, memory overhead | shapes taxonomy, Brent, merge/sort/copy-with-random-pointer, the cache proof, the distance algebra worked | the strongest existing section; still ~1/3 |
| §1.12 stacks (18) | LIFO, monotonic stack, next-greater, the amortization trap, the `ArrayDeque` advice | shunting-yard, min-stack, the four directional variants, the span decomposition and its tie rule, queue-from-two-stacks | monotonic stack is well covered; the rest is one paragraph |
| §1.13 queues/deques (16) | FIFO, monotonic deque, sliding-window max, the null trap | circular-buffer full/empty, 0-1 BFS, the indices convention, the Java 21 `ArrayDeque` correction, min-queue | one paragraph |
| §1.14 trees (28) | four traversals, height-dominates-cost | **all vocabulary and shape definitions**, the counting identities, iterative and Morris traversals, reconstruction rules, the promise framing, Euler tour, 20+ problem mechanisms | traversal list only |
| §1.15 BSTs (22) | the invariant, O(h), the validation trap, `TreeMap` navigation | delete's three cases, Hibbard skew, kth/rank, range queries, the `Integer.MIN_VALUE` bound trap, the capability table, multiset idiom | invariant + one trap |
| §1.16 heaps (25) | index arithmetic, the four costs, O(n) heapify asserted, five uses, the iteration trap | the partial-order framing, sift invariants, **the heapify proof**, decrease-key, `remove` O(n), d-ary, all heap variants, stability, max-heap idioms, growth | strong for its length; every claim unproved |
| §1.17 graphs (17) | adjacency list vs matrix, the algorithm/cost table | full vocabulary, handshake lemma, edge bounds, CSR, implicit graphs, grid conventions, the 1-indexing trap, interning | two sentences + one table |
| §1.18 sorting (32) | **absent as a topic** — sorting appears only inside the complexity table and the greedy section | all 32 leaves: every algorithm, stability, the lower-bound proof, non-comparison sorts, Java's two sorts, the comparator traps | — |
| §1.19 binary search (27) | the half-open template, the overflow trap, the mixing trap, lower/upper bound, rotated array, peak, binary-search-on-answer, the `Arrays.binarySearch` encoding | the invariant/termination proof, Bloch's history, 2-D search, real-interval search, exponential/interpolation/ternary search, the canonical BSOA problem set, cache behaviour | the second-strongest existing section |
| §1.20 recursion (25) | base case + step, the promise framing, tail recursion, the Fibonacci trap, backtracking's choose/recurse/un-choose, pruning, the canonical set | the Θ(φⁿ) correction, stack-frame cost and depth budget, iteration conversion, trampolining, duplicate-handling proofs, complexity statements, the memo-sentinel trap | good framing, no mechanism |
| §1.21 Java toolkit (21) | the `ArrayDeque`-over-`Stack` advice | all overflow/`Math`/bit/boxing/record/fast-IO leaves | one paragraph inside §5 |
| §2.1 master cost table (12) | — | **the master table does not exist**; costs are stated per section and are not comparable | — |
| §2.2 two pointers (14) | the mechanism, the discard argument for two-sum | same-direction form, k-sum generalisation, the write-index idiom, functional-graph cycles, the sorting-destroys-indices trap | one paragraph |
| §2.3 sliding window (16) | fixed vs variable, the linearity argument, the monotonicity trap | the two distinct templates, at-most→exactly, state representations, the distinct-count idiom, the prefix-sum replacement, the 13-problem set | one paragraph; the trap is excellent and survives |
| §2.4 prefix sums (15) | named in one line inside §2 | 2-D, difference arrays, sweep counts, remainder/parity tricks, the `{0:1}` initialisation, the update/query table | one clause |
| §2.5 intervals (17) | one row in the pattern table | all 17 leaves | — |
| §2.6 in-place techniques (23) | "index-as-hash, swapping, or reversal" in one pattern-table row | cyclic sort, sign marking, DNF, next permutation, Kadane, Boyer–Moore, matrix in-place, the rotation proofs | one table cell |
| §2.7 binary search applied (12) | two example problems named | predicate construction, bounds derivation, median of two arrays, LIS-by-binary-search, the non-monotone failure mode | two examples |
| §2.8 sorting/selection applied (18) | — | all 18 leaves including quickselect and median-of-medians | — |
| §2.9 tree techniques (20) | — | all 20 leaves | — |
| §2.10 BFS/DFS patterns (22) | same-skeleton framing, the distance property, the enqueue-marking trap, multi-source BFS, cycle-detection colours | bidirectional BFS, 0-1 BFS, state-space BFS, the island family, the parallel-edge trap, all-paths, bipartite, A*, iterative-deepening | a strong section at ~1/4 depth |
| §2.11 heap patterns (13) | top-k, k-way merge, two-heaps named | the polarity rule proved, lazy deletion, the scheduling family, the encoding comparison, the decision table | one sentence each |
| §2.12 backtracking (19) | choose/recurse/un-choose, pruning, the canonical set | the 2×2 taxonomy, `start` vs `used[]`, both duplicate-skip proofs, the three pruning kinds, N-queens/sudoku mechanics, complexity statements | one paragraph |
| §2.13 DP (34) | the two properties, both forms, "the state is the work", space optimization, the knapsack direction, five starter families | all 12 families enumerated, SRTBOT, reconstruction, the memo-key encodings, pseudo-polynomiality, every DP optimization, the debugging procedure | a good intro; ~1/6 of the leaves |
| §2.14 greedy (15) | the exchange argument named, works/fails lists, the sample-passing trap | the three proof templates worked, matroids, the "sort by what" analysis, the regret-heap pattern, approximation ratios, the four wrong interval keys | one paragraph; the trap survives |
| §2.15 graph algorithms (39) | the 7-row need/algorithm/cost table, the Dijkstra-negative trap, directed vs undirected cycle detection, Kahn-as-cycle-detector | every algorithm's mechanism and proof, state-extended Dijkstra, SCC, bridges, Euler, flow, matching, the 39-leaf problem-family index | a table and three traps |
| §2.16 union-find (17) | both optimizations, α(n), the `find` one-liner, six uses, the no-deletion trap | the height proof, path halving, weighted/parity DSU, grid flattening, rollback DSU, the DSU-vs-DFS decision | the third-strongest existing section |
| §2.17 tries (16) | node shape, O(L), prefix wins, the Word Search II pruning, the memory caveat | the hash-set comparison corrected, memory arithmetic, deletion, XOR tries, compressed/radix/DAWG, the problem family | one paragraph |
| §2.18 bit manipulation (23) | — | all 23 leaves | — |
| §2.19 math/number theory (24) | — | all 24 leaves | — |
| §2.20 design-a-structure (20) | — | all 20 leaves | — |
| §2.21 pattern recognition (13) | **the 16-row signal table and the constraint-anchoring trap — the guide's best section** | the seven-step procedure, the waste-identification step, clarifying questions, the edge-case checklist, the problem-family index; the table itself gains ~6 rows | the table survives verbatim and is extended |
| §2.22 Java pitfalls (24) | the `ArrayDeque`/`Stack` and `String +=` traps | the other 22 | two of 24 |
| §3.1 amortization proofs (14) | — | all 14 | — |
| §3.2 hash internals (26) | "Java converts long chains to red-black trees (see 02)" | every constant, the spread function, the lo/hi split, the Poisson table, open addressing, the Java 7 loop, hash DoS, rolling hashes | one clause + a cross-reference |
| §3.3 heap internals (24) | index arithmetic, the four costs, O(n) heapify claim | sift invariants, comparison counts, the heapify series, `forgetMeNot`, growth, d-ary, all variants, the indexed PQ | claims without mechanism |
| §3.4 balanced trees (26) | "AVL, red-black perform rotations"; `TreeMap` is red-black | rotations, both height bounds, the fix-up case analyses, 2-3-4 equivalence, treap, splay, skip list, B-tree, augmentation, footprint | one sentence |
| §3.5 sorting internals (26) | — | all 26 leaves | — |
| §3.6 selection (10) | — | all 10 | — |
| §3.7 binary search formally (14) | the two traps | the invariant/termination/exit proofs, iteration count, Bloch's post, both JDK sources, cache behaviour, the float-loop non-termination | traps without proofs |
| §3.8 traversal theory (21) | the colour scheme, the undirected-parent rule | the parenthesis and white-path theorems, edge classification, the acyclicity theorem, Tarjan, Kosaraju, low-link, Euler conditions, iterative-DFS ordering | two rules |
| §3.9 shortest path/MST theory (27) | the Dijkstra-negative trap; algorithm names and costs | every correctness proof, the cut and cycle properties, frontier trade-offs, Johnson, A* conditions, max-flow min-cut, König | names and costs only |
| §3.10 union-find internals (15) | α(n) stated | the rank/height proof, the α proof sketch, Tarjan's lower bound, path halving, weighted/parity/rollback variants | one sentence |
| §3.11 DP theory (30) | optimal substructure and overlapping subproblems named | the DAG framing, the states×transition formula, pseudo-polynomiality, the one-row proof, the LIS-tails proof, Hirschberg, every optimization | two definitions |
| §3.12 greedy theory (14) | the exchange argument named | all three templates worked, matroids, Huffman's proof, the LP-relaxation explanation, approximation proofs, competitive analysis | a name |
| §3.13 range queries (18) | — | all 18 leaves (Fenwick, segment tree, lazy propagation, sparse table, sqrt decomposition, Mo's) | — |
| §3.14 string internals (20) | — | all 20 leaves (KMP, Z, Rabin–Karp, Manacher, Aho–Corasick, suffix array, and the `String.indexOf`/regex facts) | — |
| §3.15 trie internals (12) | "a dense child array is wasteful; use a HashMap for large alphabets" | the memory arithmetic and crossover, flat-array tries, compressed/PATRICIA/DAWG/TST, deletion, XOR tries | one sentence |
| §3.16 memory/cache/JVM (18) | "cache line fetch brings neighbours along" | every byte figure, the 72 MB worked example, compressed oops, Lilliput, the measured crossover, row-major, allocation, bounds-check elimination, branch prediction, SIMD | one clause |
| §3.17 recursion internals (12) | "the JVM does not optimize tail recursion" | frame cost, depth budget, `-Xss`, virtual threads, why HotSpot cannot TCO, trampolining, the depth table | one sentence |
| §3.18 concurrency of algorithms (13) | — | all 13 leaves | — |
| §3.19 complexity theory (14) | — | all 14 leaves | — |
| §3.20 failure modes (18) | — | all 18 leaves | — |
| §3.21 measurement (14) | — | all 14 leaves | — |
| §3.22 JDK version history (15) | — | all 15 leaves | — |
| PART 4 build it (145) | **nothing** — the guide contains two snippets: the binary-search template and the one-line DSU `find` | all 145, though the two existing snippets survive inside 4.7.1 and 4.5.9 | — |
| §5.1 interview questions (100) | — | all 100 | — |
| §5.2 trap index (6) | 20 inline `**Trap:**` markers, all of which survive and expand | the consolidated index, the notation-stale table, the version-stale table, the top-five, the off-by-one and overflow hotspot lists | — |
| §5.3 drills (13) | the 24-line atomic concept checklist, every line of which survives | all 12 drills and the review schedule | — |

Summary: of **1516** leaves, roughly **160** are present in the current guide at any depth, **60** of
those at a depth the bible should keep and expand (the pattern-signal table, the sliding-window
monotonicity trap, the cycle-start trap, the BST-validation trap, the BFS enqueue-marking trap, the
monotonic-stack amortization trap, the binary-search convention traps, the knapsack direction, the
Dijkstra negativity trap, the union-find capability limit), and **1356** are missing outright.

The three structural gaps the write pass must close first, because everything else leans on them:
**sorting has no section at all** (§1.18, §2.8, §3.5, §3.6 — 86 leaves), **recurrences have no
section at all** (§1.5 — 24 leaves), and **there is no master cost table** (§2.1). No claim in the
current guide is factually wrong for Java 21; the only correction owed is that the guide's
`ArrayDeque` description ("a circular buffer over an array") is right while the widely-repeated
power-of-two-capacity claim it stops just short of is stale — §1.13.12 carries that as a
`[VERSION-TRAP]` so the bible states it correctly rather than inheriting it.
