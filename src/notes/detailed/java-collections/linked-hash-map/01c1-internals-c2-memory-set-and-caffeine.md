# 02 Java Collections — `LinkedHashMap` — INTERNALS (§3.7 `LinkedHashMap` source walk — the overlay's bytes, `LinkedHashSet`, and why a real cache is not this class)

**Target version: Java 21 LTS.** | [Index](../00-index.md)
Previous: [linked-hash-map/01c-internals-c-sequenced-and-caching.md](01c-internals-c-sequenced-and-caching.md) · Next: [linked-hash-map/02-build-lru-by-hand.md](02-build-lru-by-hand.md)

---

The previous file was about what `LinkedHashMap` can *say* in Java 21. This one is about what it *costs* — and the answer arrives in two currencies. There is a memory bill, eight bytes an entry, which is small, easy to compute, and almost never the reason a design fails. And there is a concurrency bill that is not a number at all but a structural property: an access-order `LinkedHashMap` mutates on read, and that single fact is why it cannot be scaled by wrapping it in a lock, and why every production cache in the Java ecosystem is built on something else.

`LinkedHashSet` sits between the two as a footnote worth reading, because its implementation is the shortest interesting thing in `java.util`: a class with no fields that gets its entire behaviour from which constructor it calls.

---

## 1. The cost of the overlay: 8 bytes per entry

### Mental model

`LinkedHashMap.Entry` is a `HashMap.Node` with two more references welded on. That is the entire storage story, and it prices exactly.

```java
    static class Entry<K,V> extends HashMap.Node<K,V> {
        Entry<K,V> before, after;
        Entry(int hash, K key, V value, Node<K,V> next) {
            super(hash, key, value, next);
        }
    }
```

— `java.base/java/util/LinkedHashMap.java`, JDK 21, line 205. (leaf 3.7.15)

### Why it exists

A `HashMap` node knows only its bucket successor (`next`). That is enough to find a key and no help at all in answering "what came before this?" — bucket chains are ordered by hash collision, not by anything a caller cares about. The `before`/`after` pair is a second, independent linkage threaded through the same node objects: one set of nodes, two topologies. The alternative designs both cost more. A separate parallel list would need its own node objects (another 24–32 B each plus a back-pointer), and re-deriving order from the table on demand is impossible, because the table has no order to derive.

### When to reach for it, and when not

Pay the 8 bytes when you need deterministic iteration or LRU recency. Do not pay it for a map you only ever look keys up in — `HashMap` is the sibling that wins here, and it wins on both currencies at once: no per-entry overlay, and no write on read. At the other end, if the ordering you want is *sorted* rather than *encounter*, `TreeMap` charges far more per entry (`TreeNode` carries left, right, parent and a colour bit) and buys you range queries the overlay cannot express.

### The arithmetic [NUM]

All figures assume a 64-bit HotSpot JVM with **compressed oops** (the default below a 32 GB heap) and 8-byte object alignment.

| | Fields | Raw | Aligned |
|---|---|---|---|
| `HashMap.Node` | 12 B header (8 mark + 4 compressed klass) + 4 `hash` + 4 `key` + 4 `value` + 4 `next` | 28 B | **32 B** |
| `LinkedHashMap.Entry` | the above + 4 `before` + 4 `after` | 36 B | **40 B** |

`32 → 40` is **+8 bytes per entry, a 25% surcharge on the node**, in exchange for encounter order.

Be honest about the alignment, because the naive story is wrong in an interesting way. `Node` at 28 raw bytes was padded to 32, so it already carried 4 bytes of slack. Adding two 4-byte references consumes that slack plus 4 new bytes, giving 36 raw → 40 aligned. Only *one* of the two references was "free" in the padding, and yet the marginal object size grows by the full 8 bytes because 36 aligns up to 40. So the "4 bytes were already there" observation is true and changes nothing about the bill. Full byte ladder, including the `TreeNode` rung, in [`../cost-and-memory/02-internals-memory-headers.md`](../cost-and-memory/02-internals-memory-headers.md).

**With uncompressed oops** — heaps above 32 GB, or `-XX:-UseCompressedOops` — every reference is 8 bytes and the klass word is 8. `Node` becomes 16 + 4 + 8 + 8 + 8 = 44 → 48 B; `Entry` becomes 44 + 16 = 60 → 64 B. The overlay costs **16 bytes**, not 8. State the oop assumption every time you quote a byte figure.

### Scaling it for a cache

At 1,000,000 entries the overlay costs `1_000_000 × 8 B = 8 MB` more than a `HashMap` — before counting keys, values, or the bucket array. Whether that matters is entirely a function of what you are caching:

| Cached value | Bytes/entry excluding overlay | Overlay share |
|---|---|---|
| 200-byte domain object + a 40-byte `String` key + 32 B node | 272 B | `8 / 280` ≈ **2.9%** |
| Boxed `Integer` value (16 B) + boxed `Integer` key (16 B) + 32 B node | 64 B | `8 / 72` ≈ **11%** |
| Counted against the node alone | 32 B | `8 / 32` = **25%** |

For a cache of fat objects the ordering overlay is noise — you would never notice 8 MB next to 272 MB of payload. For a cache of small boxed primitives it is a real double-digit tax, and the right response is usually a primitive-specialised map (Eclipse Collections, `fastutil`) rather than a different ordering strategy. Note what the three rows really show: the fraction is not a property of `LinkedHashMap`, it is a property of your values, so "is the overlay expensive?" has no answer until someone names the payload.

### The cost that is not memory

There is a second bill and it is the one that actually decides architectures. On an **access-order** map, `afterNodeAccess` runs on every `get` that finds a key, and it performs the full unlink-and-relink: six reference writes plus a `++modCount`. The mechanism, and the `get`-versus-`containsKey` asymmetry that follows from it, are in [`01a-internals-a2-hooks-and-access-order.md`](01a-internals-a2-hooks-and-access-order.md).

**Insight:** an access-order `LinkedHashMap` is a data structure that **mutates on read**. That single fact is why it cannot be made concurrent by wrapping — §3 below — and it is a structural property, not a tuning parameter. The 8 bytes are the advertised price; this is the one that shows up in production.

**Interview:** *"How much does `LinkedHashMap` cost over `HashMap`?"* — 8 bytes per entry with compressed oops, 16 without, a 25% surcharge on the node itself; and in access-order mode, six reference writes plus a `modCount` bump on every successful `get`, which is what actually rules it out of concurrent use.

### Definition

> The encounter-order overlay costs 8 bytes per entry with compressed oops (32 B `Node` → 40 B `Entry`, +25%), 16 bytes without, plus — in access-order mode only — six reference writes and a `modCount` bump on every successful `get`.

---

## `LinkedHashSet` — set over map, with a dummy `boolean` (leaf 3.7.16)

`LinkedHashSet extends HashSet<E> implements SequencedSet<E>` (line 123) and adds **no fields at all**. It is more than the four constructors people remember: there is also a `spliterator` override, the `@since 19` factory at line 221, a package-private `map()` accessor at 229, and the seven `SequencedSet` members it must supply — `addFirst`, `addLast`, `getFirst`, `getLast`, `removeFirst`, `removeLast`, `reversed` at lines 241–306 — every one of which forwards straight to the backing map. No ordering logic is implemented in this class. The four constructors are where the whole decision is made:

```java
    public LinkedHashSet(int initialCapacity, float loadFactor) {
        super(initialCapacity, loadFactor, true);
    }

    public LinkedHashSet(int initialCapacity) {
        super(initialCapacity, .75f, true);
    }

    public LinkedHashSet() {
        super(16, .75f, true);
    }

    public LinkedHashSet(Collection<? extends E> c) {
        super(HashMap.calculateHashMapCapacity(Math.max(c.size(), 12)), .75f, true);
        addAll(c);
    }
```

— `java.base/java/util/LinkedHashSet.java`, JDK 21, lines 142, 158, 166 and 180. (leaf 3.7.16)

Every one calls the same three-argument `super`, and that constructor is package-private with a single purpose:

```java
    HashSet(int initialCapacity, float loadFactor, boolean dummy) {
        map = new LinkedHashMap<>(initialCapacity, loadFactor);
    }
```

— `java.base/java/util/HashSet.java`, JDK 21, line 170; its javadoc names the parameter "`dummy` — ignored (distinguishes this constructor from other int, float constructor.)". (leaf 3.7.16)

**Insight:** the `boolean` carries no information. It is not a flag; it exists solely to give the constructor a signature distinct from `HashSet(int, float)`, because Java has no other way to overload on intent. That trick is the entire reason `LinkedHashSet` needs no state of its own — the ordering lives in the backing map, chosen once at construction. The set-over-map pattern itself is §3.9, [`../sets/01-set-over-map.md`](../sets/01-set-over-map.md).

The `Collection` constructor's `Math.max(c.size(), 12)` floor means `new LinkedHashSet<>(List.of("a"))` sizes its table for 12 elements rather than 1. Checked against `HashSet`'s own `Collection` constructor at line 119, which is `map = HashMap.newHashMap(Math.max(c.size(), 12))`: the same floor, reached by a different spelling, so the two **do not differ**. See the first pitfall below for the measured table sizes.

> `LinkedHashSet` is `HashSet` constructed against a `LinkedHashMap`, selected by a package-private constructor whose third parameter is a signature-disambiguating dummy — which is why the class has no fields of its own and no ordering logic.

---

## 3. Why a real cache uses Caffeine (leaf 3.7.17) [X-REF 15]

### Mental model

`LinkedHashMap` + `removeEldestEntry` is a queue that remembers *when* you touched something. A real cache is a queue that remembers *how often*. That is the whole difference, and everything else — the concurrency story, the feature list — follows from it.

### Why the difference exists: LRU is scan-vulnerable

`LinkedHashMap` + `removeEldestEntry` implements exactly LRU, and LRU has one catastrophic failure mode. A single sequential pass over a large cold key set — a nightly report, a crawler, a `SELECT *` warming loop — evicts the entire hot working set, because every cold key it touches is by definition more recently used than every hot key it displaces. Hit rate goes to near zero and stays there until the hot set is faulted back in one miss at a time. LRU cannot resist this, because recency is all it knows. The demonstration is short and deterministic:

```java
static class Lru<K, V> extends LinkedHashMap<K, V> {
    private final int cap;
    Lru(int cap) { super(16, 0.75f, true); this.cap = cap; }
    @Override protected boolean removeEldestEntry(Map.Entry<K, V> e) { return size() > cap; }
}

int cap = 100, hot = 100, cold = 1000;
var cache = new Lru<Integer, Integer>(cap);
for (int i = 0; i < hot; i++) cache.put(i, i);              // hot set resident

int hits = 0, probes = 0;
for (int round = 0; round < 10; round++)                     // steady state
    for (int i = 0; i < hot; i++) { probes++; if (cache.get(i) != null) hits++; }
System.out.printf("steady state: %d/%d hits = %.0f%%%n", hits, probes, 100.0 * hits / probes);

for (int i = 1000; i < 1000 + cold; i++) cache.put(i, i);    // ONE cold sequential scan

int rHits = 0, rProbes = 0;
for (int i = 0; i < hot; i++) { rProbes++; if (cache.get(i) != null) rHits++; }
System.out.printf("after one %d-key scan: %d/%d hits = %.0f%%%n",
                  cold, rHits, rProbes, 100.0 * rHits / rProbes);
System.out.println("cache size still " + cache.size() + ", but holds only cold keys");
```

Real output, JDK 21.0.7:

```
steady state: 1000/1000 hits = 100%
after one 1000-key scan: 0/100 hits = 0%
cache size still 100, but holds only cold keys
```

100% to 0% from one loop that nobody thought of as a cache operation. The cache is still full, still the right size, still reporting healthy occupancy — and holding nothing anyone will ask for again.

### The mechanism Caffeine substitutes

Caffeine's answer is **W-TinyLFU**: a small admission window in front of a large main region, with a frequency-based doorman between them. Frequencies are estimated in a 4-bit count-min sketch (Caffeine's design notes give roughly 8 bytes of sketch per cache entry) that is periodically halved so old popularity decays. When the window is full and an entry wants into the main region, TinyLFU compares that candidate's estimated frequency against the frequency of the entry the main region would have to evict, and **admits only the winner**. The 1000-key scan above therefore never gets past the door: each scanned key has an estimated frequency of one and loses to any hot resident. Decisions stay O(1) — the sketch is an array lookup, not a search. Frequency *and* recency, rather than recency alone. The admission window exists precisely so that a genuine burst of new-but-soon-hot keys is not rejected on arrival.

The concurrency difference is structural rather than incidental, and it follows directly from §1. `LinkedHashMap`'s recency information *is* a doubly-linked list mutated on every read — `get` relinks a node and bumps `modCount` ([`01b-internals-b-lru-and-sequenced.md`](01b-internals-b-lru-and-sequenced.md)). Two threads reading *different* keys still write the same `head`/`tail` fields, so correctness demands a single global lock, which is why `Collections.synchronizedMap(new LinkedHashMap<>(16, 0.75f, true))` serialises **readers** and not just writers. Caffeine breaks that coupling by decoupling recording from applying: reads are appended to striped per-thread ring buffers and replayed onto the policy asynchronously under a try-lock, so a reader that loses the race simply drops its record rather than blocking. The policy is slightly stale; readers never contend. That trade — approximate policy state for uncontended reads — is the design decision, and `LinkedHashMap` cannot make it, because its policy state and its iteration order are the same list.

### Choosing between the four

| | `LinkedHashMap` + `removeEldestEntry` | `synchronizedMap(...)` wrapper | `ConcurrentHashMap` + manual eviction | Caffeine |
|---|---|---|---|---|
| Eviction policy | exact LRU | exact LRU | whatever you write | W-TinyLFU (+ optional size/weight/time) |
| Scan resistance | none | none | none, unless you build it | yes, by admission filter |
| Read concurrency | none (not thread-safe) | serialised — one reader at a time | full | full; reads recorded to ring buffers |
| Expiry after write / after access | no | no | hand-rolled, usually with a timer thread | both, built in |
| Weight-based bounds | no | no | hand-rolled | yes (`maximumWeight` + `Weigher`) |
| Async / refresh loading | no | no | hand-rolled | `AsyncLoadingCache`, `refreshAfterWrite` |
| Statistics | no | no | hand-rolled | `recordStats()` — hit rate, load time, evictions |
| Dependency cost | zero, in the JDK | zero, in the JDK | zero, in the JDK | one third-party jar |
| Lines of your code | ~10 | ~11 | 100+ | ~5 |

Be fair to `LinkedHashMap`. It is in the JDK, it is ten lines, it has no dependencies to audit or upgrade, it is trivially readable in review, and its policy is *exact* rather than probabilistic — no sketch, no sampling, no staleness. For a small bounded cache with a known, non-scanning access pattern — single-threaded, or already inside a lock you hold for other reasons — it is the right answer, and reaching for a caching library is over-engineering. The moment you need concurrent readers, expiry, or resistance to an access pattern you do not control, the ten lines stop being a saving.

**Pitfall:** the wrong belief is *"a cache is a bounded map, so a bounded map is a cache"*. Symptom: the 100%-to-0% collapse above, triggered by a batch job that nobody classified as cache traffic, showing up as a latency spike in an unrelated service. Fix: before choosing an eviction policy, ask whether any workload can scan the key space; if one can, exact LRU is disqualified regardless of how it is implemented.

**[RESEARCH] notes.** W-TinyLFU is the algorithm Caffeine documents itself as using; the project wiki's Efficiency page names "the Window TinyLfu policy", describes the admission-window / main-region split, and specifies the 4-bit `CountMinSketch` at ~8 bytes per entry. Maven coordinates: `com.github.ben-manes.caffeine:caffeine`, latest release **3.2.4** as listed on Maven Central when this file was written (2026-08). No Caffeine code is compiled or benchmarked in these notes.

### Definition

> A real cache differs from `LinkedHashMap` + `removeEldestEntry` in two structural ways, not a list of features: its eviction admits on frequency as well as recency, so a scan cannot flush the hot set; and it records reads without mutating shared order, so readers do not contend.

Full treatment — cache topologies, write policies, stampede control, distributed invalidation — in guide 15 (caching).

---

## Pitfalls

### Assuming `new LinkedHashSet<>(smallCollection)` sizes for the collection

**Wrong**

```java
var one = new LinkedHashSet<>(List.of("a"));   // "one element, so a tiny table"
System.out.println("table length = " + tableLength(one));
```
```
table length = 16
```

**Right**

```java
var sized = LinkedHashSet.<String>newLinkedHashSet(1);   // @since 19
sized.add("a");
System.out.println("table length = " + tableLength(sized));
```
```
table length = 2
```

The `Collection` constructor is `super(HashMap.calculateHashMapCapacity(Math.max(c.size(), 12)), .75f, true)`. The `Math.max(..., 12)` floor means any collection of 12 or fewer elements is sized as if it had 12, giving a 16-slot table. `newLinkedHashSet(n)` applies no floor. `tableLength` here is reflection into `HashSet.map` then `HashMap.table`, run with `--add-opens java.base/java.util=ALL-UNNAMED`; measured on JDK 21.0.7.

**Why people believe it:** the javadoc says "an initial capacity sufficient to hold the elements in the specified collection", which is true and silent about the floor. Worth knowing it is not a `LinkedHashSet` quirk: `new HashSet<>(List.of("a"))` also reports `table length = 16`, because `HashSet(Collection)` uses `HashMap.newHashMap(Math.max(c.size(), 12))` — the same floor, spelled differently.

### Treating a bounded `LinkedHashMap` as a production cache

**Wrong**

```java
Map<Integer, Integer> cache =
    Collections.synchronizedMap(new Lru<>(100));   // "now it's thread-safe, so it's a cache"
```

Correct, and it does not scale. `get` calls `afterNodeAccess`, which relinks the node and bumps `modCount`, so two threads reading different keys contend on the same monitor. Read throughput is flat in the number of cores. And the exact-LRU policy underneath is still scan-vulnerable — the 100% → 0% collapse above happens under the lock just as cheerfully as without it.

**Right**

Either accept the constraint and keep it single-threaded behind a component that already owns a lock:

```java
// single-threaded ownership: no wrapper, no contention, exact policy, zero dependencies
private final Map<Integer, Integer> cache = new Lru<>(100);
```

or move to a cache designed for concurrency and unpredictable access patterns (Caffeine), and stop hand-rolling eviction.

**Why people believe it:** `Collections.synchronizedMap` genuinely does make the map thread-*safe*, and "thread-safe" is heard as "concurrent". Safety is about correctness under contention; concurrency is about throughput under contention. A single global monitor delivers the first and forecloses the second.

---

## Cheat sheet

| Fact | Value |
|---|---|
| `Entry` size, compressed oops | `Node` 28→32 B; `Entry` 36→40 B; overlay **+8 B/entry, +25%** |
| `Entry` size, uncompressed oops | `Node` 44→48 B; `Entry` 60→64 B; overlay **+16 B/entry** |
| Where the 8 B goes | `before` (4) + `after` (4); 4 B came from `Node`'s padding, but 36 aligns up to 40 anyway |
| 1 M entries | +8 MB over `HashMap`, before keys and values |
| Overlay share, 200 B values | ~2.9% — noise |
| Overlay share, boxed `Integer` values | ~11% — real; use a primitive-specialised map |
| Access-order read cost | 6 reference writes + `++modCount` per successful `get` — mutates on read |
| `LinkedHashSet` | `extends HashSet` `implements SequencedSet`; **no fields**; every ctor calls `HashSet(int, float, boolean dummy)`, which builds a `LinkedHashMap` |
| The `dummy` boolean | carries no information; exists only to disambiguate from `HashSet(int, float)` |
| `LinkedHashSet` members | 4 ctors, `spliterator`, `newLinkedHashSet` (221), pkg-private `map()` (229), 7 `SequencedSet` forwarders (241–306) |
| `LinkedHashSet(Collection)` sizing | `calculateHashMapCapacity(Math.max(c.size(), 12))` → 16-slot table for 1 element; **same floor** as `HashSet(Collection)` |
| Sized factory, no floor | `LinkedHashSet.newLinkedHashSet(n)` / `LinkedHashMap.newLinkedHashMap(n)` — both `@since 19` |
| `LinkedHashMap` cache policy | exact LRU — **scan-vulnerable**; one 1000-key scan took a 100-entry cache from 100% to 0% hit rate |
| Caffeine policy | W-TinyLFU: admission window + 4-bit count-min sketch (~8 B/entry) with periodic halving, O(1) |
| Why Caffeine scales reads | reads go to striped per-thread ring buffers, replayed async under try-lock; no shared list write |
| Why `synchronizedMap` does not | access-order `get` writes `head`/`tail`, so one monitor serialises readers |
| When `LinkedHashMap` is right | small bounded cache, known non-scanning pattern, single-threaded or already locked, zero dependencies |
| Caffeine coordinates | `com.github.ben-manes.caffeine:caffeine` 3.2.4 (Maven Central, 2026-08 — perishable) |

---

## Self-test

**Q1.** Give the byte arithmetic for the encounter-order overlay, and say when the number changes.

<details><summary>Answer</summary>

With compressed oops: `HashMap.Node` = 12 B header (8 mark + 4 klass) + 4 hash + 4 key + 4 value + 4 next = 28 raw, aligned to 32. `LinkedHashMap.Entry` adds `before` + `after` = 36 raw, aligned to 40. Overlay = **+8 B per entry, +25% on the node**. Only 4 of those 8 bytes went into `Node`'s existing padding, but 36 still aligns up to 40, so the marginal cost is the full 8. Without compressed oops (heap > 32 GB or `-XX:-UseCompressedOops`) references and the klass word are 8 B: `Node` 44→48, `Entry` 60→64, overlay **+16 B**.

</details>

**Q2.** A colleague says "`LinkedHashMap` costs 25% more memory than `HashMap`". What is wrong with the sentence?

<details><summary>Answer</summary>

The 25% is the surcharge on the *node object*, not on the map. Total per-entry cost includes the key and the value, which usually dominate. For 200-byte values with 40-byte `String` keys the overlay is about 2.9% of the entry; for boxed `Integer` keys and values it is about 11%; against the bare node it is 25%. The fraction is a property of the payload, not of `LinkedHashMap`, so the claim is unanswerable until someone names what is being stored. In absolute terms the number is stable and easy: 8 MB per million entries.

</details>

**Q3.** Which of `LinkedHashMap`'s two costs actually rules it out of production caches, and why?

<details><summary>Answer</summary>

Not the memory — 8 MB per million entries is rarely decisive. The disqualifying cost is that in access-order mode it **mutates on read**: `get` calls `afterNodeAccess`, which performs six reference writes to relink the node and bumps `modCount`. Because recency is stored as a shared doubly-linked list, two threads reading *different* keys still write the same `head`/`tail` fields, so any thread-safe wrapper must serialise readers as well as writers. The structure cannot express "many concurrent readers".

</details>

**Q4.** `LinkedHashSet` declares no fields and implements no ordering logic. How does it get insertion-order iteration, and what else is actually in the class?

<details><summary>Answer</summary>

Every `LinkedHashSet` constructor calls `super(initialCapacity, loadFactor, true)` — a package-private `HashSet(int, float, boolean dummy)` whose body is `map = new LinkedHashMap<>(initialCapacity, loadFactor)`. The `boolean` carries no information; its javadoc says "ignored (distinguishes this constructor from other int, float constructor.)". It exists purely to give the constructor a signature distinct from `HashSet(int, float)`. The ordering lives entirely in the backing map, chosen once at construction. Beyond the four constructors the class holds a `spliterator` override, `newLinkedHashSet(int)` (line 221), a package-private `map()` (229), and the seven `SequencedSet` members at 241–306 (`addFirst`, `addLast`, `getFirst`, `getLast`, `removeFirst`, `removeLast`, `reversed`) — all pure forwarding.

</details>

**Q5.** Why does `new LinkedHashSet<>(List.of("a"))` allocate a 16-slot table, and does `HashSet` behave differently?

<details><summary>Answer</summary>

The `Collection` constructor is `super(HashMap.calculateHashMapCapacity(Math.max(c.size(), 12)), .75f, true)`. The `Math.max(..., 12)` floor treats any collection of 12 or fewer elements as 12, and `calculateHashMapCapacity(12)` = `ceil(12 / 0.75)` = 16. `HashSet` does **not** differ: its `Collection` constructor is `map = HashMap.newHashMap(Math.max(c.size(), 12))` — the same floor, spelled differently, and it also reports a 16-slot table. To size for one element use `LinkedHashSet.newLinkedHashSet(1)`, which applies no floor and yields a 2-slot table (both verified by reflection on JDK 21.0.7).

</details>

**Q6.** Explain scan vulnerability, and what W-TinyLFU does instead.

<details><summary>Answer</summary>

Exact LRU evicts on recency alone, so one sequential pass over a key set larger than the cache flushes the entire hot working set: every cold key touched is more recently used than every hot key it displaces. Measured: a 100-entry access-order `LinkedHashMap` cache at 100% hit rate dropped to 0% after a single 1000-key scan, while still reporting `size() == 100`. W-TinyLFU puts a small admission window in front of a large main region and a frequency estimator between them — a 4-bit count-min sketch (~8 B per entry) that is periodically halved so popularity decays. A candidate is admitted to the main region only if its estimated frequency beats that of the entry it would evict, so each scanned key (frequency 1) loses to any hot resident and is rejected at the door. Decisions remain O(1).

</details>

**Q7.** Under what circumstances is `LinkedHashMap` + `removeEldestEntry` the *right* choice over a caching library?

<details><summary>Answer</summary>

When the cache is small and bounded, the access pattern is known and cannot scan the key space, and access is single-threaded or already inside a lock the surrounding component holds for other reasons. Then you get: an exact rather than probabilistic policy, ten lines of readable code, zero dependencies to audit or upgrade, and no new failure modes. Adding a caching library there is over-engineering. What flips the decision is needing concurrent readers, expiry (after-write or after-access), weight-based bounds, async/refresh loading, statistics, or resistance to a workload you do not control.

</details>

**Q8.** Why is `Collections.synchronizedMap(new LinkedHashMap<>(16, 0.75f, true))` correct but not a fix?

<details><summary>Answer</summary>

It is genuinely thread-*safe* — every operation holds the single monitor, so the linked list is never observed half-relinked. It is not *concurrent*: because `get` mutates the list, readers must take the same monitor as writers, so read throughput does not scale with cores. It also does nothing about the policy — the underlying exact LRU is still scan-vulnerable, and the 100%-to-0% collapse happens under the lock exactly as it does without one. Safety and scalability are different properties; the wrapper buys the first and forecloses the second. Caffeine avoids the trade by recording reads into striped per-thread ring buffers and replaying them onto the policy asynchronously, accepting slightly stale policy state in exchange for uncontended reads.

</details>

---

## Open questions

- **Caffeine's hit-rate claims.** The Caffeine wiki states that W-TinyLFU achieves hit rates within 99% of the theoretical optimum (Belady's algorithm) on its trace workloads. That is the project's own benchmark result on its own traces, reported here as an attributed claim and **not independently reproduced** for these notes. No comparative hit-rate or throughput figures are published here, and none should be quoted from this file without a named trace and machine. The one measured hit-rate figure on the page (100% → 0% under a scan) is a property of exact LRU on a synthetic workload, not a benchmark of any library.
- **Caffeine version.** `com.github.ben-manes.caffeine:caffeine` **3.2.4** was the latest release listed on Maven Central at the time of writing (2026-08); the versions table on the fetched page rendered incompletely, so the coordinate is sourced but the version is perishable. Re-check before pinning.

---

**Leaves covered:** 3.7.15, 3.7.16, 3.7.17 (3 leaves)
**Leaves deferred:** none
**Diagrams included:** none new — the reversed view (D-103) is embedded in [01c-internals-c-sequenced-and-caching.md](01c-internals-c-sequenced-and-caching.md)
**Target version:** Java 21 LTS
**Lines:** 361
