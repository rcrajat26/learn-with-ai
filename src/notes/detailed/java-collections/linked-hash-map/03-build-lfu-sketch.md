# 02 Java Collections — `LinkedHashMap` — INTERNALS (§4.6.3 An LFU sketch, and why LRU is the easy one)

**Target version: Java 21 LTS.** | [Index](../00-index.md)
Previous: [linked-hash-map/02a-build-lru-b-proof-and-cost.md](02a-build-lru-b-proof-and-cost.md) · Next: [linked-hash-map/03a-build-lfu-b-policy-comparison.md](03a-build-lfu-b-policy-comparison.md)

---

The previous two files built an LRU cache and proved it correct in about 150 lines, and the reason it was that easy is worth naming precisely: **recency is a total order maintained by a single move-to-end**, and a doubly-linked list does move-to-end in O(1). One structure, one operation, done.

Frequency is not a total order. **Frequency is a multiset**: many keys share a count, the counts change by one at a time, and "evict the least frequent" is a *minimum over a changing multiset*. No single list gives you that. The standard O(1) LFU therefore needs a list of lists — one doubly-linked list per frequency bucket, the buckets themselves in a doubly-linked list ordered by frequency, and a pointer to the minimum-frequency bucket. Three structures where LRU needed two, and every operation must keep all three consistent. That is the entire content of "why LRU is the easy one", and this file makes it concrete by building the cheaper variant of the same idea and getting its one subtle field exactly right.

**Code on this page.** Two labelled `java` blocks, two files, one block each, in order: `LfuCache.java` (the working cache) and `BuggyLfuCache.java` (the same class with one line removed), plus `LfuDemo.java` (the runnable proof) — three files in all, compiled together under `javac -Xlint:all`, zero warnings. Every printed line below is real output of `java LfuDemo`. The policy comparison against LRU, aging, and W-TinyLFU, with the head-to-head eviction transcript, continues in [03a-build-lfu-b-policy-comparison.md](03a-build-lfu-b-policy-comparison.md).

**No diagram on this page.** Three interlocking structures do not fit in one readable picture at this scale, and the `toString()` on `LfuCache` prints the buckets in ascending frequency, so the demo output *is* the picture — `LfuCache{f1=[B, C], f4=[A]} min=1` says everything a drawing would.

---

## §4.6.3a Frequency is a multiset, and that is the whole difficulty `[BUILD]`

### Mental model

For LRU, picture a queue: touch an entry and it goes to the back, so the front is always the victim. One arrow, one victim, no ambiguity — the order is *total*, because "more recently used than" never ties.

For LFU, picture a set of numbered bins. Bin 1 holds every key hit once, bin 2 every key hit twice, and so on. Touching a key means moving it from its bin to the next bin up. Evicting means reaching into the lowest **non-empty** bin — and "lowest non-empty" is the problem, because bins empty out as their last occupant is promoted, and scanning for the next non-empty bin is O(number of distinct counts).

So an LFU needs three things where LRU needed two: a value index, a count index, and a *bin* index — plus one integer, `minFrequency`, that remembers which bin is currently lowest so nobody has to scan for it. That integer is the entire O(1)-ness of the design, and it is the only part that is subtle.

### Why it exists

Because recency is a poor predictor for some workloads. A key hit ten times a second and a key hit once an hour look identical to LRU the instant after both are touched; frequency distinguishes them. LFU is the policy you want for a stable working set with a long tail — a dictionary, a set of hot product IDs, a compiled-query cache — where popularity is durable and access order is noisy.

### When to reach for it, and when not

Reach for LFU when popularity is *stable* over the cache's lifetime and you can accept that the policy never forgets. Reach for LRU when the working set drifts, when the code has to be reviewable by anyone, or when 40 bytes an entry matters. Reach for neither in production: W-TinyLFU, which is frequency for admission and recency for eviction, beats both on essentially every real trace ([03a-build-lfu-b-policy-comparison.md](03a-build-lfu-b-policy-comparison.md)).

### How it works — which design, and what "sketch" licenses

The syllabus says *sketch*, and there are two honest readings of that word. Both are O(1); neither is incomplete.

| Design | Structures | Per-entry cost | Lines | Trade |
|---|---|---|---|---|
| **A — pure list-of-lists** | a doubly-linked node list per frequency, the frequency buckets themselves doubly linked, `minBucket` pointer | one node + one bucket object per distinct count | ~190 | No boxing anywhere, no per-bucket hash set, best locality, and promotion is pure pointer surgery. The most code, and the most invariants to keep. |
| **B — frequency buckets in a map** | `Map<K,V>`, `Map<K,Integer>`, `Map<Integer, LinkedHashSet<K>>`, `int minFrequency` | 3 map entries + a `LinkedHashSet` node per entry, plus a boxed `Integer` count | ~120 | Materially shorter, reuses `LinkedHashSet` for the within-bucket recency tie-break, and every structure is a JDK collection you have already read the source of. Boxing on the count and the bucket key; worse locality. |

**This file takes Option B**, for two reasons that are about the reader, not the machine: the `LinkedHashSet` tie-break is a direct callback to the previous files in this folder (a `LinkedHashSet` is a `LinkedHashMap` with `PRESENT` values, so the bucket's insertion order costs nothing extra to reason about), and the shorter version makes the `minFrequency` argument — the actual subtlety — impossible to hide behind pointer surgery.

What Option A does differently, and why you would reach for it in real code: it keeps `int` frequencies inside bucket objects rather than boxed `Integer` map keys, so a promotion allocates nothing and compares nothing; it holds nodes in a linked list per bucket instead of a `LinkedHashSet`, saving a hash table per distinct count; and because each bucket knows its neighbour buckets, advancing `minFrequency` becomes "follow one pointer" rather than "arithmetic that must be proven correct". Option B pays for its brevity in allocation and indirection, not in asymptotics.

**Insight:** the within-bucket tie-break is free, and it is not a detail. `LinkedHashSet` iterates in insertion order, so the first key returned from the minimum bucket is the one that entered that count *earliest* — LFU with LRU as the tie-breaker. A `HashSet` there would evict an arbitrary member of the tied group and make the policy non-deterministic between JVM runs.

### The code

```java
// LfuCache.java
import java.util.HashMap;
import java.util.HashSet;
import java.util.LinkedHashSet;
import java.util.Map;
import java.util.Set;
import java.util.TreeMap;

/**
 * A fixed-capacity least-frequently-used cache. O(1) for get and put.
 * Three maps and one int: values, per-key hit counts, per-count key buckets in
 * insertion order (so ties inside a bucket break least-recently-added first),
 * and minFrequency, which always names a non-empty bucket when size > 0.
 * Not thread-safe.
 */
public final class LfuCache<K, V> {

    private final Map<K, V> values;
    private final Map<K, Integer> counts;
    private final Map<Integer, LinkedHashSet<K>> buckets;
    private final int capacity;
    private int minFrequency;

    public LfuCache(int capacity) {
        if (capacity < 1) {
            throw new IllegalArgumentException("capacity must be >= 1, was " + capacity);
        }
        this.capacity = capacity;
        this.values = HashMap.newHashMap(capacity);
        this.counts = HashMap.newHashMap(capacity);
        this.buckets = new HashMap<>();
        this.minFrequency = 0;
    }

    public V get(K key) {
        V value = values.get(key);
        if (value == null && !values.containsKey(key)) {
            return null;
        }
        touch(key);
        return value;
    }

    public V put(K key, V value) {
        if (values.containsKey(key)) {
            V old = values.put(key, value);
            touch(key);
            return old;
        }
        if (values.size() == capacity) {
            evict();
        }
        values.put(key, value);
        counts.put(key, 1);
        buckets.computeIfAbsent(1, f -> new LinkedHashSet<>()).add(key);
        minFrequency = 1;            // unconditional: the new key IS the new minimum
        return null;
    }

    /** Moves key from bucket f to bucket f+1, advancing minFrequency if bucket f emptied. */
    private void touch(K key) {
        int f = counts.get(key);
        counts.put(key, f + 1);
        LinkedHashSet<K> bucket = buckets.get(f);
        bucket.remove(key);
        if (bucket.isEmpty()) {
            buckets.remove(f);
            if (minFrequency == f) {
                minFrequency = f + 1;
            }
        }
        buckets.computeIfAbsent(f + 1, nf -> new LinkedHashSet<>()).add(key);
    }

    /** Drops the least-frequently-used key, oldest first within the tied bucket. */
    private void evict() {
        LinkedHashSet<K> bucket = buckets.get(minFrequency);
        K victim = bucket.iterator().next();
        bucket.remove(victim);
        if (bucket.isEmpty()) {
            buckets.remove(minFrequency);
        }
        values.remove(victim);
        counts.remove(victim);
    }

    public boolean containsKey(K key) {
        return values.containsKey(key);
    }

    public int size() {
        return values.size();
    }

    /** The hit count of a cached key, or 0 if absent. Exposed so the policy is testable. */
    public int frequency(K key) {
        return counts.getOrDefault(key, 0);
    }

    /** The current minimum frequency, or 0 when empty. Exposed so the invariant is testable. */
    public int minFrequency() {
        return minFrequency;
    }

    /** Cached keys, no defined order. Snapshot, not a live view. */
    public Set<K> keys() {
        return new HashSet<>(values.keySet());
    }

    /** Buckets in ascending frequency, so the structure is visible in demo output. */
    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder("LfuCache{");
        boolean first = true;
        for (Map.Entry<Integer, LinkedHashSet<K>> e : new TreeMap<>(buckets).entrySet()) {
            if (!first) {
                sb.append(", ");
            }
            first = false;
            sb.append('f').append(e.getKey()).append('=').append(e.getValue());
        }
        return sb.append("} min=").append(minFrequency).toString();
    }
}
```

Three details are decisions. `get` tests `value == null && !values.containsKey(key)` rather than `value == null`, so a key legitimately mapped to `null` is still a hit — the same distinction `HashMap.get` cannot make and `containsKey` exists for. Buckets are *deleted* when they empty rather than left behind as empty sets, which keeps `buckets` proportional to the number of distinct counts and makes `toString()` readable, at the cost of a `computeIfAbsent` allocation when a count comes back. And `frequency`/`minFrequency` are public because a policy you cannot read is a policy you cannot test — the same reason `LruCache` has `keys()`.

**Interview:** the expected answer to "now make it LFU" is exactly this — `Map<K,V>` plus `Map<K,Integer>` plus `Map<Integer, LinkedHashSet<K>>` plus a `minFrequency` field, all O(1) — followed immediately by "and `minFrequency` resets to 1 on every insertion". Candidates who name the three maps but not that last rule have not run their design.

### Definition

> An O(1) LFU cache is a value index, a count index, and a bucket index keyed by count, plus a remembered minimum count that is advanced on promotion and reset on insertion.

---

## §4.6.3b `minFrequency`, the only subtle part

### Mental model

`minFrequency` is a cached answer to a question that is expensive to ask: *which is the lowest non-empty bin?* Caching it is what makes eviction O(1). Keeping it true is therefore the whole correctness burden of the class, and there are exactly two events that can change the answer.

### How it works — the two rules

**Rule 1 — on a `touch` that empties the old bucket, `minFrequency++`.** If key `k` was in bucket *f* and *f* is now empty, and *f* was the minimum, then the new minimum is *f+1*: `k` itself just landed there, so *f+1* is provably non-empty, and no bucket between *f* and *f+1* exists. If *f* was **not** the minimum, some lower bucket is still occupied and `minFrequency` must not move — which is why the increment sits inside `if (minFrequency == f)`.

**Rule 2 — on an insertion, `minFrequency = 1`, unconditionally.** A new key enters with count 1, and 1 is the smallest count any key can have, so bucket 1 is non-empty and is the minimum. There is nothing to test. The temptation is to guard it — `if (values.size() == 1)`, or `if (minFrequency > 1)`, or to skip it entirely on the grounds that "the map already had a minimum" — and every guard is wrong, because the insertion has *created* a bucket below the previous minimum.

Skipping Rule 2 fails in two escalating ways. First `minFrequency` points at a bucket that is no longer the minimum, so eviction picks a *frequently* used key while a once-used key sits untouched — the policy is silently inverted for that victim. Then, once the stale bucket is emptied by its own eviction, `minFrequency` points at a bucket that has been deleted, `buckets.get(minFrequency)` returns `null`, and the next eviction throws `NullPointerException`. A wrong answer first, a crash later.

### The proof

`BuggyLfuCache` is `LfuCache` with Rule 2 guarded by `if (values.size() == 1)` — correct on the very first insertion, wrong on every later one — and nothing else changed.

```java
// BuggyLfuCache.java
import java.util.HashMap;
import java.util.LinkedHashSet;
import java.util.Map;

/** LfuCache with one line removed: minFrequency is not reset to 1 on insertion. */
final class BuggyLfuCache<K, V> {

    private final Map<K, V> values = new HashMap<>();
    private final Map<K, Integer> counts = new HashMap<>();
    private final Map<Integer, LinkedHashSet<K>> buckets = new HashMap<>();
    private final int capacity;
    private int minFrequency = 0;

    BuggyLfuCache(int capacity) {
        this.capacity = capacity;
    }

    V get(K key) {
        if (!values.containsKey(key)) {
            return null;
        }
        touch(key);
        return values.get(key);
    }

    void put(K key, V value) {
        if (values.containsKey(key)) {
            values.put(key, value);
            touch(key);
            return;
        }
        if (values.size() == capacity) {
            evict();
        }
        values.put(key, value);
        counts.put(key, 1);
        buckets.computeIfAbsent(1, f -> new LinkedHashSet<>()).add(key);
        if (values.size() == 1) {
            minFrequency = 1;       // BUG: only on the first insertion, not every insertion
        }
    }

    private void touch(K key) {
        int f = counts.get(key);
        counts.put(key, f + 1);
        LinkedHashSet<K> bucket = buckets.get(f);
        bucket.remove(key);
        if (bucket.isEmpty()) {
            buckets.remove(f);
            if (minFrequency == f) {
                minFrequency = f + 1;
            }
        }
        buckets.computeIfAbsent(f + 1, nf -> new LinkedHashSet<>()).add(key);
    }

    private void evict() {
        LinkedHashSet<K> bucket = buckets.get(minFrequency);
        K victim = bucket.iterator().next();
        bucket.remove(victim);
        if (bucket.isEmpty()) {
            buckets.remove(minFrequency);
        }
        values.remove(victim);
        counts.remove(victim);
    }

    java.util.Set<K> keys() {
        return new java.util.HashSet<>(values.keySet());
    }

    int minFrequency() {
        return minFrequency;
    }
}
```

```java
// LfuDemo.java
import java.util.ArrayList;
import java.util.List;
import java.util.Set;

public final class LfuDemo {

    public static void main(String[] args) {
        basics();
        minFrequencyProof();
    }

    private static void basics() {
        System.out.println("== 1. LfuCache, capacity 3: the three structures as they move ==");
        LfuCache<String, Integer> c = new LfuCache<>(3);
        c.put("A", 1);
        c.put("B", 2);
        c.put("C", 3);
        System.out.println("after put A,B,C : " + c);
        c.get("A");
        c.get("A");
        c.get("A");
        System.out.println("after 3x get(A) : " + c);
        c.get("B");
        System.out.println("after get(B)    : " + c);
        c.get("C");
        System.out.println("after get(C)    : " + c + "   <- bucket f1 emptied, min advanced 1 -> 2");
        c.put("D", 4);
        System.out.println("after put(D)    : " + c);
        System.out.println("evicted B?      : " + !c.containsKey("B") + "  frequencies A=" + c.frequency("A")
                + " C=" + c.frequency("C") + " D=" + c.frequency("D"));
    }

    private static void minFrequencyProof() {
        System.out.println();
        System.out.println("== 2. why minFrequency = 1 on insertion is unconditional ==");
        System.out.println("  sequence: put A,B,C; get A x3; get B; get C; put D; put E; put F");

        LfuCache<String, Integer> good = new LfuCache<>(3);
        BuggyLfuCache<String, Integer> bad = new BuggyLfuCache<>(3);
        for (String k : List.of("A", "B", "C")) {
            good.put(k, 1);
            bad.put(k, 1);
        }
        for (int i = 0; i < 3; i++) {
            good.get("A");
            bad.get("A");
        }
        good.get("B");
        bad.get("B");
        good.get("C");
        bad.get("C");
        good.put("D", 4);
        bad.put("D", 4);
        System.out.println("  after put(D)  correct: keys=" + sorted(good.keys()) + " min=" + good.minFrequency()
                + "   buggy: keys=" + sorted(bad.keys()) + " min=" + bad.minFrequency());
        good.put("E", 5);
        bad.put("E", 5);
        System.out.println("  after put(E)  correct: keys=" + sorted(good.keys()) + " min=" + good.minFrequency()
                + "   buggy: keys=" + sorted(bad.keys()) + " min=" + bad.minFrequency());
        System.out.println("  correct evicted D (count 1). buggy evicted C (count 2) and kept D - wrong victim.");
        good.put("F", 6);
        System.out.println("  after put(F)  correct: keys=" + sorted(good.keys()) + " min=" + good.minFrequency());
        try {
            bad.put("F", 6);
            System.out.println("  buggy put(F): no exception");
        } catch (RuntimeException e) {
            System.out.println("  buggy put(F): " + e.getClass().getName()
                    + " - minFrequency names a bucket that no longer exists");
        }
    }

    private static List<String> sorted(Set<String> keys) {
        List<String> out = new ArrayList<>(keys);
        out.sort(null);
        return out;
    }
}
```

```text
== 1. LfuCache, capacity 3: the three structures as they move ==
after put A,B,C : LfuCache{f1=[A, B, C]} min=1
after 3x get(A) : LfuCache{f1=[B, C], f4=[A]} min=1
after get(B)    : LfuCache{f1=[C], f2=[B], f4=[A]} min=1
after get(C)    : LfuCache{f2=[B, C], f4=[A]} min=2   <- bucket f1 emptied, min advanced 1 -> 2
after put(D)    : LfuCache{f1=[D], f2=[C], f4=[A]} min=1
evicted B?      : true  frequencies A=4 C=2 D=1

== 2. why minFrequency = 1 on insertion is unconditional ==
  sequence: put A,B,C; get A x3; get B; get C; put D; put E; put F
  after put(D)  correct: keys=[A, C, D] min=1   buggy: keys=[A, C, D] min=2
  after put(E)  correct: keys=[A, C, E] min=1   buggy: keys=[A, D, E] min=2
  correct evicted D (count 1). buggy evicted C (count 2) and kept D - wrong victim.
  after put(F)  correct: keys=[A, C, F] min=1
  buggy put(F): java.lang.NullPointerException - minFrequency names a bucket that no longer exists
```

Section 1 is Rule 1 in four lines. `get(B)` moves `B` out of bucket 1, but `C` is still there, so `min` stays 1 — the `if (minFrequency == f)` guard doing its job in the negative direction. `get(C)` empties bucket 1, so `min` advances to 2, and `put(D)` then evicts from bucket 2, taking `B` rather than `C` because `B` entered that bucket first. Note `A`, at count 4, was never a candidate: that is the policy working, and — as the next file shows — also the policy's disease.

Section 2 is Rule 2. Both caches agree at `put(D)` on membership and disagree on `min`: the correct cache says 1 (where `D` now sits), the buggy one still says 2. One operation later that disagreement becomes an eviction disagreement — the correct cache evicts `D`, which has been hit once, and the buggy cache evicts `C`, which has been hit twice, keeping the colder key. One operation after *that*, the buggy cache's `min = 2` names a bucket that its own eviction deleted, and `buckets.get(2)` returns `null`.

**Pitfall:** the buggy cache's `keys()` at `put(D)` is *identical* to the correct one's. A test that checks membership after each operation passes. Only `minFrequency` — internal state — is wrong at that point, which is precisely why it is exposed as a method. The visible failure arrives one operation later, on a different key, and looks like an eviction-order bug rather than a bookkeeping bug.

### The gotcha

`minFrequency` is never *decreased* by `touch`, only increased, and never *recomputed* by scanning. Both properties are load-bearing: a recomputing fallback (`buckets.keySet().stream().min(...)`) would paper over Rule 2 bugs while making eviction O(distinct counts), turning a wrong O(1) cache into a right O(n) one — and hiding the defect from every test.

### Definition

> `minFrequency` is a memoised minimum over the bucket keys, maintained by exactly two rules — increment when the minimum bucket empties on promotion, reset to 1 on every insertion — and never recomputed.

---

## Two supporting facts

**Neither cache here is thread-safe, and unlike LRU there is no cheap fix.** A `get` on this LFU mutates `counts`, two entries of `buckets`, and possibly `minFrequency` — four pieces of state, no two of which are atomic together — so a single lock around every method is the only correct answer, and it serialises *readers*. An LRU has at least the option of a striped or optimistic design because its read-path mutation touches one node's two pointers; an LFU's read path is a multi-map transaction. See [../concurrent-collections/01-thread-safety-and-wrappers.md](../concurrent-collections/01-thread-safety-and-wrappers.md).

**`counts` is redundant in Option A and not here.** With a list-of-lists, a node knows its own bucket and the bucket knows its frequency, so no separate count index exists. Option B needs `counts` because a key in a `LinkedHashSet` has no idea which set it is in — the price of using a hash set as the bucket. That is one extra map entry per cached key, and it is the clearest single illustration of Option B's cost.

---

## Pitfalls

### Guarding the `minFrequency = 1` reset

**Wrong**

```java
values.put(key, value);
counts.put(key, 1);
buckets.computeIfAbsent(1, f -> new LinkedHashSet<>()).add(key);
if (values.size() == 1) {           // or: if (minFrequency == 0), or nothing at all
    minFrequency = 1;
}
```

Output: the cache evicts a key with count 2 while keeping a key with count 1, then throws `NullPointerException` on a later eviction — `buggy: keys=[A, D, E] min=2` above, then `java.lang.NullPointerException`.

**Right**

```java
values.put(key, value);
counts.put(key, 1);
buckets.computeIfAbsent(1, f -> new LinkedHashSet<>()).add(key);
minFrequency = 1;                   // a new key has count 1, so 1 is the minimum. No condition.
```

**Why people believe it:** every other field update in the class is conditional — `minFrequency++` is guarded by `if (minFrequency == f)`, buckets are removed only `if (bucket.isEmpty())` — so an unconditional assignment looks like a missing check rather than a proof.

### Using a `HashSet` for the bucket instead of a `LinkedHashSet`

**Wrong**

```java
private final Map<Integer, HashSet<K>> buckets = new HashMap<>();

private void evict() {
    K victim = buckets.get(minFrequency).iterator().next();   // arbitrary member of the tied group
    buckets.get(minFrequency).remove(victim);
    values.remove(victim);
    counts.remove(victim);
}
```

Ties are the *common* case in LFU — most keys sit at low counts — so this decides most evictions by hash order, which varies with capacity, insertion history, and key identity hash. Two runs on the same trace evict different keys, and the cache's hit rate becomes irreproducible.

**Right**

```java
private final Map<Integer, LinkedHashSet<K>> buckets = new HashMap<>();

private void evict() {
    K victim = buckets.get(minFrequency).iterator().next();   // earliest to enter this count
    buckets.get(minFrequency).remove(victim);
    values.remove(victim);
    counts.remove(victim);
}
```

`LinkedHashSet` iterates in insertion order, so the tie-break is "least recently promoted into this count" — LFU with LRU underneath, deterministic and defensible.

**Why people believe it:** `Set` is the right *interface* for a bucket and `HashSet` is the reflex implementation; the ordering requirement is invisible until you ask which of two tied keys dies.

### Testing an LFU only on membership

**Wrong**

```java
cache.put("D", 4);
assertEquals(Set.of("A", "C", "D"), cache.keys());   // passes on the buggy cache too
```

**Right**

```java
cache.put("D", 4);
assertEquals(Set.of("A", "C", "D"), cache.keys());
assertEquals(1, cache.minFrequency());               // fails immediately on the buggy cache
assertEquals(1, cache.frequency("D"));
```

Assert the bookkeeping, not just the contents. The wrong-victim symptom appears one operation *after* the state goes bad, so a membership-only test blames the wrong operation.

**Why people believe it:** membership is the class's public contract, and asserting internal state feels like testing implementation details — until the implementation detail *is* the policy.

---

## Cheat sheet

| Item | Value |
|---|---|
| Why LRU is easy | recency is a total order; one move-to-end in O(1) |
| Why LFU is hard | frequency is a multiset; needs a minimum over changing counts |
| Option A | list-of-lists: node list per frequency + linked buckets + `minBucket` pointer |
| Option B (built here) | `Map<K,V>` + `Map<K,Integer>` + `Map<Integer, LinkedHashSet<K>>` + `int minFrequency` |
| `get` | `touch`: count *f* → *f+1*, move between buckets, maybe advance `min` — O(1) |
| `put` present | overwrite value, `touch` |
| `put` absent, full | `evict()` from bucket `minFrequency`, then insert |
| Eviction victim | first element of `buckets.get(minFrequency)` — earliest into that count |
| Tie-break | `LinkedHashSet` insertion order = LRU within the tied bucket |
| Rule 1 | `touch` empties the min bucket → `minFrequency++` |
| Rule 2 | insertion → `minFrequency = 1`, **unconditional** |
| Skipping Rule 2 | wrong victim first, `NullPointerException` later |
| Empty bucket | deleted from the map, never left as an empty set |
| `counts` map | needed only in Option B; Option A's nodes know their bucket |
| Thread safety | none, and no cheap fix — one `get` mutates three maps + an int |
| Never do | recompute `minFrequency` by scanning `buckets.keySet()` |

---

## Self-test

**Q1.** In one sentence each, why is LRU O(1) with one structure and LFU O(1) only with three?

<details><summary>Answer</summary>

LRU: recency is a total order whose only update is "move this entry to the end", which a doubly-linked list performs in O(1) given the node — so one list plus a hash index suffices. LFU: frequency is a multiset in which many keys tie, counts change one at a time, and eviction needs the minimum over that multiset — so you need a value index, a count index, and a bucket-per-count index, plus a remembered minimum, to avoid scanning for the lowest non-empty count.

</details>

**Q2.** State both `minFrequency` rules, and prove Rule 1's increment is exactly `+1`.

<details><summary>Answer</summary>

Rule 1: if a `touch` empties bucket *f* and `minFrequency == f`, then `minFrequency = f + 1`. Rule 2: on any insertion, `minFrequency = 1`, unconditionally. Rule 1's increment is exactly `+1` because the key that emptied bucket *f* was promoted into bucket *f+1*, so *f+1* is non-empty; and no bucket with a count strictly between *f* and *f+1* can exist, since counts are integers. If `minFrequency != f`, a lower bucket is still occupied and nothing changes.

</details>

**Q3.** Why is Rule 2 unconditional? Give the two failures that follow from guarding it.

<details><summary>Answer</summary>

Because a newly inserted key has count 1, and 1 is the minimum possible count, so bucket 1 is non-empty and is the minimum — there is nothing to test. Guarding it leaves `minFrequency` naming a higher bucket, so (1) eviction picks a more-frequently-used key while a count-1 key survives, silently inverting the policy for that victim, and (2) once that stale bucket is emptied by its own eviction and deleted, `buckets.get(minFrequency)` returns `null` and the next eviction throws `NullPointerException`.

</details>

**Q4.** Why `LinkedHashSet` rather than `HashSet` for a bucket, and what breaks with the wrong choice?

<details><summary>Answer</summary>

Ties are the common case in LFU, so the bucket's iteration order decides most evictions. `LinkedHashSet` iterates in insertion order, making the tie-break "earliest to enter this count" — LFU with LRU underneath, deterministic and reproducible. `HashSet` would evict an arbitrary tied member, varying with table capacity and identity hashes, so the same trace evicts different keys on different runs and the hit rate becomes irreproducible.

</details>

**Q5.** Why does `LfuCache.get` test `value == null && !values.containsKey(key)` instead of just `value == null`?

<details><summary>Answer</summary>

Because a key may be legitimately mapped to a `null` value, and `Map.get` cannot distinguish "absent" from "present with a null value". Testing only `value == null` would treat such a key as a miss, skip the `touch`, and return `null` without counting the access — so the key's frequency would never rise and it would be evicted first despite being hot. The `containsKey` follow-up costs a second lookup only on the null path.

</details>

**Q6.** Why is `counts` needed here but not in the pure list-of-lists design?

<details><summary>Answer</summary>

Because a key stored in a `LinkedHashSet` carries no reference back to the set it is in, so the promotion path has to look its current count up somewhere. In the list-of-lists design each entry is a node inside a bucket object, and the bucket object knows its own frequency, so the count is reachable from the node in one hop and no separate map exists. That extra map entry per cached key is the clearest single cost of Option B's brevity.

</details>

**Q7.** Why is a single lock a worse answer for LFU than for LRU?

<details><summary>Answer</summary>

Because an LFU `get` is a multi-map transaction: it writes `counts`, removes from one bucket, adds to another, may delete a bucket, and may advance `minFrequency`. No two of those are atomic together, so correctness requires holding one lock across all of them — which serialises every reader. An access-order LRU also mutates on read, but its read-path write is two pointers on one node, which leaves room for striping or optimistic schemes; an LFU leaves none.

</details>

---

**Leaves covered:** 4.6.3 (part 1 of 2, continued in 03a) (1 leaf)
**Leaves deferred:** none
**Diagrams included:** none new — the map-plus-linked-list structure (D-148) is embedded in [02-build-lru-by-hand.md](02-build-lru-by-hand.md)
**Target version:** Java 21 LTS
**Lines:** 583
