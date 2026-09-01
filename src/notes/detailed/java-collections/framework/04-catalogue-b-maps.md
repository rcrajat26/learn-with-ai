# 02 Java Collections — The framework itself — BASICS (§1.4 Every concrete implementation: the Map catalogue)

**Target version: Java 21 LTS.** | [Index](../00-index.md)
Previous: [framework/03-catalogue-a-lists-and-sets.md](03-catalogue-a-lists-and-sets.md) · Next: [framework/05-catalogue-c-queues-and-specials.md](05-catalogue-c-queues-and-specials.md)

## Hierarchy before details

Every `Map` implementation in this file sits somewhere under the `Map` root, and several additionally implement `SequencedMap`, `SortedMap`, or `NavigableMap`. See the full picture before the per-class detail below:

![The full java.util interface hierarchy in Java 21 — the Map root, SequencedMap, SortedMap and NavigableMap tiers that every class in this catalogue sits under](../diagrams/D-03-interface-hierarchy-java21.svg)

`HashMap` implements bare `Map`. `LinkedHashMap` additionally implements `SequencedMap` (Java 21). `TreeMap` implements `NavigableMap` (hence `SortedMap`, hence `Map`). `Hashtable` implements `Map` but predates the Collections Framework by three years and was retrofitted onto it in Java 1.2. `ConcurrentHashMap` implements `ConcurrentMap`. `ConcurrentSkipListMap` implements `ConcurrentNavigableMap`.

## The master attribute grid

This table is the spine of the file — every class below is one row.

| Class | Backing structure | Ordering guarantee | Null keys | Null values | Thread safety | Iterator | Default / initial capacity | Pick when | Avoid when |
|---|---|---|---|---|---|---|---|---|---|
| `HashMap` | bucket array of list/tree bins | none | 1 allowed | many allowed | none | fail-fast | 16, load factor 0.75 | default general-purpose map | you need order or concurrency |
| `LinkedHashMap` | `HashMap` + doubly-linked overlay | insertion or access order | 1 allowed | many allowed | none | fail-fast | 16, load factor 0.75 | need iteration order or LRU | order not needed (pure overhead) |
| `TreeMap` | red-black tree | key sort order (`Comparable`/`Comparator`) | none | many allowed | none | fail-fast | n/a (tree, no capacity) | need sorted iteration / range queries | O(1) lookup matters more than order |
| `Hashtable` | bucket array, `Entry[]` | none | none at all | none at all | synchronized (every method) | `Enumeration` (not fail-fast) + fail-fast `Iterator` on views | 11, load factor 0.75, grows `2n+1` | legacy code requiring `Enumeration` API | anything new — use `ConcurrentHashMap` |
| `Dictionary` | abstract, no state of its own | n/a | n/a | n/a | n/a | `Enumeration` | n/a | never — retained only as `Hashtable`'s superclass | always for new code |
| `Properties` | `Hashtable<Object,Object>` | none | none | none | synchronized (inherited) | `Enumeration` / `Iterator` | 11 (inherited) | config key-value pairs, `.properties` files | anywhere you'd reach for a typed map |
| `EnumMap` | `Object[]` indexed by ordinal | enum declaration (ordinal) order | none | `NULL` sentinel allows null | none | fail-fast, ordinal order | size of enum universe | key type is a single `enum` | keys aren't from one enum type |
| `IdentityHashMap` | single flat `Object[]`, linear probing | none | 1 allowed | many allowed | none | fail-fast | 32 slots (16 entries) | reference-equality semantics, e.g. serialization graphs | ordinary `equals`/`hashCode` semantics are wanted |
| `WeakHashMap` | `HashMap`-like table of weak-referenced keys | none | 1 allowed | many allowed | none | fail-fast | 16, load factor 0.75 | key-scoped caches, listener registries | value should outlive an unreferenced key |
| `ConcurrentHashMap` | bucket array, per-bin CAS/`synchronized` | none | none | none | thread-safe, lock striping | weakly consistent | 16 (resized in powers of two) | concurrent read/write map, default in new code | strict null semantics needed, or sorted iteration |
| `ConcurrentSkipListMap` | lock-free skip list | key sort order | none | none | thread-safe, lock-free | weakly consistent | n/a (skip list) | concurrent map that must also be sorted/navigable | plain concurrent map suffices (skip list has higher constant factors) |

### Primary concepts

## `HashMap`

**Mental model.** Picture an array of buckets, each bucket a short linked list (or, once it gets crowded, a small red-black tree). Hashing a key picks the bucket in O(1); walking the (usually tiny) bucket finds the exact entry.

**Why it exists.** Before hash tables, associative lookup meant linear scans or maintaining a sorted structure just to find one value by key. `HashMap` trades ordering for near-constant-time lookup, insert, and delete — the right trade for the overwhelming majority of key-value use cases.

**When to reach for it, and when not.** Default choice for any map with no ordering or concurrency requirement. Not when you need predictable iteration order (`LinkedHashMap`), sorted keys (`TreeMap`), or safe concurrent mutation (`ConcurrentHashMap` — `HashMap` under concurrent modification can corrupt its bucket list into a cycle, an infinite loop bug that shipped in production systems before Java 8's fix reduced but did not eliminate the risk).

**How it works.** `[X-REF]` The bucket array, `hash()` spreading function, `putVal` insertion path, treeification at bin size 8, and resize-triggered untreeify at bin size 6 are covered mechanism-by-mechanism with real constants in `../hash-map/01-internals-a-constants-and-hash.md` through `../hash-map/05-internals-e-sizing-and-iteration.md`. In one paragraph: a key's `hashCode()` is spread (XORed with its own upper 16 bits) to reduce collision clustering from poor hash functions, masked against `(capacity - 1)` to pick a bucket index, and the bucket is walked or treeified for the actual entry lookup; the table doubles when size exceeds `capacity * loadFactor`.

No new diagram is assigned to this concept in this file — the mechanism diagrams live with the internals guide linked above.

**Example.**

```java
Map<String, Integer> wordCounts = new HashMap<>();
wordCounts.put("staff", 1);
wordCounts.put(null, 99);              // the one permitted null key
wordCounts.merge("staff", 1, Integer::sum);
System.out.println(wordCounts.get(null));   // 99
System.out.println(wordCounts.get("staff")); // 2
```

**Gotcha.** Mutating a key's fields after insertion (when `hashCode()` depends on them) makes the entry unreachable by `get` — it is still in the table, in the bucket its *old* hash pointed to, but a fresh lookup computes the *new* hash and looks in the wrong bucket entirely.

> **Definition.** `HashMap` is an unordered `Map` backed by an array of hash buckets, giving amortised O(1) get/put at the cost of no iteration-order guarantee and one permitted null key.

## `LinkedHashMap`

**Mental model.** A `HashMap` with a hidden doubly-linked list threaded through every entry, so hash-bucket lookup speed is kept while iteration follows a predictable path — either the order entries were inserted, or (in access-order mode) the order they were last touched.

**Why it exists.** `HashMap`'s iteration order is an implementation artifact (bucket index, not insertion order) and can change across resizes. Anything that needs "the order the caller cares about" plus hash-speed lookup — reproducible test output, a simple LRU cache — needed a structure combining both properties.

**When to reach for it, and when not.** Reach for it for insertion-order iteration (e.g. deterministic JSON key order) or to build an LRU cache via access-order mode plus `removeEldestEntry` override. Skip it when order genuinely does not matter — the linked-list overlay is pure memory and pointer-maintenance overhead over plain `HashMap`, and skip it when sort order (not insertion/access order) is required — that is `TreeMap`'s job.

**How it works.** `[X-REF]` The `before`/`after` fields on each entry and the `afterNodeAccess`/`afterNodeInsertion`/`afterNodeRemoval` hooks that `HashMap` calls but only `LinkedHashMap` overrides are walked in `../linked-hash-map/01-internals.md`. In one paragraph: every entry gains `before` and `after` references forming a doubly-linked list rooted at a `head`/`tail` pair; insertion order mode links each new entry at the tail, access order mode additionally re-splices an entry to the tail on every `get`, and `removeEldestEntry` (always `false` by default, overridable) is checked after every insertion to support bounded LRU caches without extra library code.

```java
Map<String, String> lru = new LinkedHashMap<>(16, 0.75f, true) { // access order
    @Override
    protected boolean removeEldestEntry(Map.Entry<String, String> eldest) {
        return size() > 3;
    }
};
lru.put("a", "1"); lru.put("b", "2"); lru.put("c", "3");
lru.get("a");           // "a" moves to the most-recently-used end
lru.put("d", "4");      // evicts "b", the new eldest
System.out.println(lru.keySet()); // [c, a, d]
```

**Gotcha.** The three-argument constructor's boolean is easy to miss — `new LinkedHashMap<>(16, 0.75f)` (two-arg) silently gives insertion order, not access order, and a from-scratch LRU cache built on it simply never evicts what you expect.

> **Definition.** `LinkedHashMap` is a `HashMap` with a maintained doubly-linked traversal order — insertion order by default, access order on request — used wherever deterministic iteration or LRU eviction is required.

## `TreeMap`

**Mental model.** A self-balancing binary search tree (red-black) where the tree's in-order walk *is* the sorted key sequence — there is no separate step to sort, the structure keeps itself sorted as you mutate it.

**Why it exists.** Neither `HashMap` nor `LinkedHashMap` can answer "give me all keys between X and Y" or "what's the next key after this one" without a full scan. A balanced BST answers both in O(log n) by construction, which is exactly what `NavigableMap` (`floorKey`, `ceilingEntry`, `headMap`, `subMap`, `descendingMap`, ...) exposes.

**When to reach for it, and when not.** Reach for it for sorted iteration, range queries, or nearest-key lookups — a rate table keyed by timestamp, a price ladder. Not when you only need O(1) point lookups with no ordering need, since red-black tree operations cost O(log n) against `HashMap`'s amortised O(1), and not when keys have no natural or supplied ordering (`TreeMap` throws `ClassCastException` on insert if a key is neither `Comparable` nor covered by a supplied `Comparator`, and throws `NullPointerException` on any null key — there is no fallback bucket for an unorderable value).

**How it works.** `[X-REF]` Red-black rebalancing (rotations, recoloring, the five invariants) and the full navigation API are covered in `../tree-map/01-navigable-api.md` and `../tree-map/02-internals-a-red-black.md`. In one paragraph: every insertion walks down by comparator result to find its leaf position, inserts colored red, then rebalances upward with rotations and recolors to restore the invariant that no root-to-leaf path is more than twice as long as any other, which is what keeps `get`/`put`/`remove` at guaranteed O(log n) even in adversarial insertion orders (unlike an unbalanced BST, which degrades to a linked list on sorted input).

```java
NavigableMap<Integer, String> priceLadder = new TreeMap<>();
priceLadder.put(100, "bid-100");
priceLadder.put(105, "bid-105");
priceLadder.put(110, "bid-110");
System.out.println(priceLadder.floorKey(107));   // 105 — nearest key <= 107
System.out.println(priceLadder.headMap(105, true)); // {100=bid-100, 105=bid-105}
```

**Gotcha.** A `Comparator` that is inconsistent with `equals` (returns 0 for objects that are not `.equals()`) silently causes `TreeMap` to treat those two objects as the same key — one overwrites the other, and `containsKey` reports `true` for keys that would fail an `equals` check — because `TreeMap` uses comparison, never `equals`, to test key identity.

> **Definition.** `TreeMap` is a `NavigableMap` backed by a red-black tree, giving guaranteed O(log n) operations with keys always iterated in sorted order, and it categorically rejects null keys.

## Supporting facts

**`Hashtable`.** `[NUM]` Legacy (Java 1.0, retrofitted to implement `Map` in 1.2), every public method `synchronized` on the instance monitor — coarse-grained, one lock for the whole table, no read/write striping. Default capacity is **11** (not 16), and on resize it grows to `2 * oldCapacity + 1` (not doubling): starting at 11, the next capacities are 23, 47, 95, ... An odd capacity was originally chosen so the modulo-based index calculation (`hash % capacity`, not `HashMap`'s power-of-two `hash & (capacity - 1)` mask) spreads more evenly across odd-numbered table sizes. It permits **no null keys and no null values** — `put(null, x)` and `put(x, null)` both throw `NullPointerException` immediately, unlike `HashMap`'s one-null-key tolerance. It exposes both a modern `Iterator` (via `keySet()`/`entrySet()`, fail-fast) and the original `Enumeration`-based `keys()`/`elements()` (not fail-fast — no `ConcurrentModificationException`, silently undefined behavior under concurrent structural change instead). `contains(Object)` on `Hashtable` means "contains this **value**" — a naming collision with the now-standard `containsKey`/`containsValue` split that trips up anyone reading old code expecting `contains` to mean `containsKey`.
**Pitfall:** the folklore claim "the only difference between `Hashtable` and `HashMap` is synchronization" is false — see `[VERSION-TRAP]` below for the full enumeration.

> **Definition.** `Hashtable` is a legacy, fully synchronized `Map` implementation from Java 1.0 with odd-capacity `2n+1` growth, no null tolerance at all, and a dual `Enumeration`/`Iterator` view API.

**`[VERSION-TRAP]` What "just synchronization" misses.** What used to be believed: `Hashtable` = `HashMap` + `synchronized`. What is actually true in 21, enumerated: (1) null policy — `Hashtable` rejects both null keys and null values, `HashMap` allows one null key and unlimited null values; (2) growth — `Hashtable` grows `2n+1`, `HashMap` doubles; (3) initial capacity — 11 vs 16; (4) indexing — `Hashtable` uses `hash % capacity` (modulo), `HashMap` uses `hash & (capacity - 1)` (bitmask, which is why `HashMap` requires power-of-two capacities and `Hashtable` does not); (5) view API — `Hashtable` retains `Enumeration`-based `keys()`/`elements()` that predate `Iterator` and are not fail-fast; (6) `contains(Object)` means `containsValue` on `Hashtable`, an ambiguity `HashMap` does not carry (it has no bare `contains`). None of these six are "just" synchronization, and interviewers who ask this question are checking for exactly this list, not the top-line answer.

**`Dictionary`.** `[RESEARCH]` The abstract superclass `Hashtable` extends, predating the Collections Framework (Java 1.0) and never implementing the `Map` interface itself — it declares `get`, `put`, `remove`, `keys`, `elements`, `size`, `isEmpty` as abstract methods with no concrete storage of its own. Its javadoc explicitly documents it as effectively obsolete: "NOTE: This class is obsolete. New implementations should implement the Map interface, rather than extending this class." Verified against the Java 21 javadoc for `java.util.Dictionary`; no subsequent JDK release has added a second production subclass beside `Hashtable`.
**Pitfall:** seeing `Dictionary` in an old codebase and assuming it's a modern generic mapping type worth extending — it exists purely so `Hashtable` has a superclass, and no new class should ever extend it.

> **Definition.** `Dictionary<K,V>` is the abstract, pre-Collections-Framework parent of `Hashtable`, retained for binary compatibility and explicitly marked obsolete for any new use.

**`Properties`.** `[RESEARCH]` `[TRAP]` Declared as `public class Properties extends Hashtable<Object,Object>` — verified against the Java 21 source, the class predates generics (Java 5) and was retrofitted with the widest possible type parameters rather than `<String,String>`, because doing so would have broken the pre-existing raw-type API. It adds `getProperty(String)` / `getProperty(String, String default)` and `setProperty(String, String)` as the type-safe entry points, layered on top of the inherited raw `Object`-keyed `Hashtable` storage, plus `load`/`store` for `.properties` file I/O.
**Pitfall:** calling the inherited `put(Object, Object)` instead of `setProperty(String, String)` compiles fine — the generics say `Object`, so any object is legal — but silently inserts a non-`String` value that `getProperty` (which internally casts to `String`) will either miss (because `load`/`store` only round-trip `String` values) or throw `ClassCastException` on later. The fix: always use `setProperty`/`getProperty`, never the inherited raw `put`/`get`, and treat `Properties` as `Map<String,String>` in practice even though the compiler will not enforce it.

> **Definition.** `Properties` is a `Hashtable<Object,Object>` for configuration key-value pairs, exposing `String`-safe `getProperty`/`setProperty` wrappers over generically-unsafe inherited storage.

**`EnumMap`.** `[RESEARCH]` Backed by an `Object[] vals` array sized to the enum's universe and indexed directly by `ordinal()` — no hashing, no buckets. A `keyUniverse` array of all enum constants (obtained once via `getUniverse`, essentially `Enum.values()`) is cached and shared across lookups. Iteration walks `vals` in ordinal order, i.e. declaration order of the enum constants — this is a genuine, useful ordering guarantee, not an implementation accident. Null values are supported internally via a private `NULL` sentinel object substituted in and out transparently; null keys are rejected outright (`ordinal()` on `null` cannot be taken) with `NullPointerException`. Verified against Java 21 `java.util.EnumMap` source.
**Pitfall:** assuming `EnumMap` behaves like a hash map with enum keys and is therefore interchangeable with `HashMap<SomeEnum, V>` — it is faster and more memory-compact (no hash buckets, one flat array) specifically *because* it commits to a single enum's ordinals, so it cannot hold keys from more than one enum type, unlike a `HashMap` which could (unsafely) mix them.

> **Definition.** `EnumMap` is an ordinal-indexed flat-array `Map` for a single enum type, iterating in declaration order with no hashing overhead.

**`IdentityHashMap`.** Uses reference equality (`==`) instead of `.equals()`/`.hashCode()` for both key comparison and its own hash computation (`System.identityHashCode`), backed by a single flat array with keys and values interleaved at adjacent indices (`array[2i]` = key, `array[2i+1]` = value) and linear probing on collision rather than chaining. Default table holds 32 slots for roughly 16 entries at 2x overallocation. It deliberately violates the general `Map` contract, which specifies `.equals()`-based comparison — its javadoc says so explicitly, warning it is intended for niche uses like topology-preserving object graph traversal (e.g. serialization, deep-copy visited-sets) where two `.equals()`-but-distinct objects must be tracked as separate keys.
**Pitfall:** two `String`s built as `new String("x")` that are `.equals()` but not `==` are treated as *different* keys in an `IdentityHashMap` — code migrated from `HashMap` assuming equals-based dedup will silently retain duplicate-looking entries.

> **Definition.** `IdentityHashMap` is a flat linear-probed array map using `==` reference identity in place of `.equals()`/`.hashCode()`, by contract-violating design.

**`WeakHashMap`.** Wraps each key in a `WeakReference` registered against an internal `ReferenceQueue`; when the garbage collector determines a key is only weakly reachable (no strong references remain outside the map), it clears the reference and enqueues it. The map itself calls `expungeStaleEntries()` at the start of most operations (`size`, `get`, `put`, ...) to drain that queue and physically remove the now-dead entries — so a `WeakHashMap` can shrink between operations with no explicit `remove` call from user code.
**Pitfall:** storing a value that (directly or transitively) holds a strong reference back to its own key defeats the entire mechanism — the key stays strongly reachable through the value it's mapped to, the weak reference never clears, and the "self-cleaning cache" leaks exactly like a `HashMap` would.

> **Definition.** `WeakHashMap` is a hash map whose keys are held via `WeakReference`, automatically expunging entries once their key becomes otherwise unreachable — an automatic, key-scoped cache.

**`ConcurrentHashMap`.** `[X-REF]` Full bin-level CAS/lock mechanics, the `sizeCtl` resize coordination field, and `KeySetView` are walked in `../concurrent-collections/02-internals-chm-a.md` and `../concurrent-collections/03-internals-chm-b.md`. In one paragraph: reads are lock-free (volatile reads of bin heads), writes CAS an empty bin's head directly or fall back to a synchronized block scoped to just that one bin's first node — never a table-wide lock — so unrelated bins never contend, and it forbids null keys and null values entirely because a null return from `get` would be ambiguous between "absent" and "mapped to null" under concurrent mutation with no way to disambiguate via a second check (`containsKey`) without a race window; `keySet()` returns a `KeySetView` supporting `newKeySet()`-style set-from-map construction.

> **Definition.** `ConcurrentHashMap` is a thread-safe `Map` using per-bin locking/CAS instead of a table-wide lock, at the cost of forbidding nulls and only weakly-consistent iteration.

**`ConcurrentSkipListMap`.** `[X-REF]` Full skip-list level/pointer mechanics are out of scope for this catalogue file; there is no internals guide dedicated to skip lists in this note set beyond the concurrent-collections files linked above for `ConcurrentHashMap` — treat the skip list mechanism itself (probabilistic leveled linked lists giving expected O(log n) search) as background knowledge assumed at this tier. In one paragraph relevant to the choice here: it is the concurrent analogue of `TreeMap` — a lock-free, leveled linked-list structure giving expected O(log n) operations plus full `ConcurrentNavigableMap` support (`floorKey`, `subMap`, `descendingMap`) under concurrent mutation without ever taking a table-wide lock, at the cost of higher per-operation constant factors than `ConcurrentHashMap` from the extra level pointers.

> **Definition.** `ConcurrentSkipListMap` is a lock-free, sorted `ConcurrentNavigableMap` backed by a skip list, the concurrent counterpart to `TreeMap`.

## Pitfalls

### Assuming `Hashtable` differs from `HashMap` only by synchronization

**Wrong**
```java
Hashtable<String, String> ht = new Hashtable<>();
ht.put(null, "x"); // assumed to behave like HashMap's tolerated null key
```
Output: `NullPointerException` — not the silent success a `HashMap` user would expect.

**Right**
```java
Map<String, String> safe = new ConcurrentHashMap<>(); // modern concurrent choice
// or, if Hashtable's exact null-rejecting legacy semantics are genuinely required:
Hashtable<String, String> ht = new Hashtable<>();
ht.put("key", "x"); // never pass null to either key or value
```

**Why people believe it:** the two classes share nearly identical method signatures and both predate/postdate the framework confusingly, so the difference that gets remembered is the headline one (synchronized vs not) and the other five differences (null policy, growth factor, capacity, indexing, view API) get quietly dropped.

### Calling `put` on a `Properties` instance

**Wrong**
```java
Properties config = new Properties();
config.put("retries", 3);           // compiles: Object, Object — but 3 is an Integer
config.load(inputStream);
config.store(outputStream, null);   // throws ClassCastException internally on "retries"
```

**Right**
```java
Properties config = new Properties();
config.setProperty("retries", "3"); // String, String — the type-safe, correct API
int retries = Integer.parseInt(config.getProperty("retries", "1"));
```

**Why people believe it:** `Properties` is-a `Hashtable<Object,Object>`, so `put` compiles for any object without a warning; nothing at the call site signals that the class's real contract (`String` keys and values only) is narrower than its declared generics.

## Cheat sheet

| Need | Reach for |
|---|---|
| Default general-purpose map | `HashMap` |
| Predictable iteration order | `LinkedHashMap` (insertion order) |
| LRU cache | `LinkedHashMap` (access order + `removeEldestEntry`) |
| Sorted keys / range queries | `TreeMap` |
| Legacy `Enumeration`-based API required | `Hashtable` |
| `.properties` file config | `Properties`, via `setProperty`/`getProperty` only |
| Single-enum-type keys, fastest possible | `EnumMap` |
| Reference-equality (`==`) keying | `IdentityHashMap` |
| Auto-expiring cache keyed on live objects | `WeakHashMap` |
| Concurrent map, no ordering | `ConcurrentHashMap` |
| Concurrent map, sorted/navigable | `ConcurrentSkipListMap` |
| `Hashtable` growth formula | `2n+1`, initial capacity 11 |
| `HashMap` growth formula | doubling, initial capacity 16 |
| Nulls allowed | `HashMap` (1 key), `LinkedHashMap` (1 key), `IdentityHashMap` (1 key), `WeakHashMap` (1 key), `EnumMap` (values only, via sentinel) |
| Nulls forbidden entirely | `TreeMap`, `Hashtable`, `Properties`, `ConcurrentHashMap`, `ConcurrentSkipListMap` |

## Self-test

**Q1.** Name three differences between `Hashtable` and `HashMap` beyond synchronization.

<details><summary>Answer</summary>

Any three of: null policy (Hashtable rejects both null keys and values entirely, HashMap allows one null key and unlimited null values); growth formula (`2n+1` vs doubling); default/initial capacity (11 vs 16); indexing (modulo vs bitmask, hence Hashtable has no power-of-two capacity requirement); the retained `Enumeration`-based `keys()`/`elements()` view API (not fail-fast); `contains(Object)` on Hashtable meaning `containsValue`, an ambiguity HashMap doesn't have.

</details>

**Q2.** Why does calling `put` on a `Properties` object compile even for non-`String` values, and what breaks as a result?

<details><summary>Answer</summary>

`Properties extends Hashtable<Object,Object>`, so the inherited `put(Object,Object)` accepts anything — the generics predate generics-aware design and were widened to `Object` rather than `String` to preserve binary compatibility with pre-Java-5 code. A non-`String` value stored this way passes `put` silently but breaks `store()` (which only round-trips `String` values) and can throw `ClassCastException` from `getProperty`, which casts internally to `String`. Fix: always use `setProperty`/`getProperty`.

</details>

**Q3.** A `LinkedHashMap` built with `new LinkedHashMap<>(16, 0.75f)` is used to implement an LRU cache with an overridden `removeEldestEntry`, but eviction never seems to track recency correctly. What's wrong?

<details><summary>Answer</summary>

The two-argument constructor defaults to insertion-order mode, not access-order mode — `get` calls never move an entry to the end of the internal linked list. The three-argument constructor `new LinkedHashMap<>(16, 0.75f, true)` is required to get access-order behaviour, which is what an LRU cache actually needs.

</details>

**Q4.** Why can't `EnumMap` hold keys from two different enum types, and why is that a feature rather than a limitation?

<details><summary>Answer</summary>

`EnumMap` is backed by a single flat `Object[]` sized and indexed by one enum type's `ordinal()` values, with a cached `keyUniverse` for that one type. Committing to a single enum type is exactly what lets it skip hashing and bucket chaining entirely — it's a feature because it buys the speed and compactness gain; a `HashMap<Enum<?>, V>` could mix enum types but pays full hashing overhead to do so.

</details>

**Q5.** Under what circumstance does a `WeakHashMap` fail to actually free an entry even though nothing outside the map appears to reference the key?

<details><summary>Answer</summary>

When the value stored against that key holds a strong reference back to the key itself (directly, or transitively through other objects). The key remains strongly reachable via that path, so the garbage collector never clears the `WeakReference`, and the entry is never expunged — the cache leaks exactly like a plain `HashMap` would.

</details>

**Q6.** Why does `ConcurrentHashMap` forbid null values, when `HashMap` allows them freely?

<details><summary>Answer</summary>

In a single-threaded `HashMap`, a null return from `get` is disambiguated from "absent" by a follow-up `containsKey` check. Under concurrent mutation, another thread could remove or insert between the `get` and the `containsKey` check, so that disambiguation is unreliable — there's no atomic way to tell "mapped to null" from "not present" without a data race window. Forbidding null values (and null keys, for consistency) removes the ambiguity at the API level entirely.

</details>

**Q7.** `IdentityHashMap` is described as violating the `Map` contract "by design." What specifically does it violate, and why is that useful?

<details><summary>Answer</summary>

The general `Map` contract requires key comparison via `.equals()`/`.hashCode()`; `IdentityHashMap` uses `==` reference identity and `System.identityHashCode` instead, so two distinct-but-`.equals()`-equal objects are treated as different keys. This is useful for tasks like object-graph traversal (serialization, deep copy) where the algorithm must track which specific object instances it has already visited, regardless of whether unrelated instances happen to be logically equal.

</details>

**Q8.** Why does `TreeMap` throw `NullPointerException` on `put(null, value)` while `HashMap` tolerates one null key?

<details><summary>Answer</summary>

`TreeMap` must compare every key against existing keys (via `Comparable.compareTo` or a supplied `Comparator`) to find its correct position in the tree — calling `compareTo` on `null`, or passing `null` into a `Comparator` that doesn't explicitly handle it, throws immediately. `HashMap` has no such comparison requirement; it special-cases the null key to a fixed bucket index (0) instead.

</details>

## Open questions

None — all `[RESEARCH]`-tagged claims in this file were checked against Java 21 javadoc/source (`Hashtable` growth and capacity, `Dictionary`'s obsolete status, `Properties`' generics, `EnumMap`'s internals) and confirmed.

---

**Leaves covered:** 1.4.14–1.4.24 (11 leaves)
**Leaves deferred:** none
**Diagrams included:** D-03 (re-embedded from its canonical home; no new diagram assigned to this file)
**Target version:** Java 21 LTS
**Lines:**      289
