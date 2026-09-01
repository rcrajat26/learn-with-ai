# 02 Java Collections — Cost and memory — INTERNALS (§3.15.13–3.15.24 Memory footprint arithmetic: per-collection footprints, measuring, the future)

**Target version: Java 21 LTS.** | [Index](../00-index.md)
Previous: [cost-and-memory/02-internals-memory-headers.md](02-internals-memory-headers.md) · Next: [cost-and-memory/04-observability.md](04-observability.md)

This file takes the object header (12 bytes compressed, 16 for arrays) and the two node shapes already priced in [02-internals-memory-headers.md](02-internals-memory-headers.md) — `HashMap.Node` at 32 bytes, `LinkedHashMap.Entry` at 40, `HashMap.TreeNode` at 56 — and finishes the ladder: every remaining collection's per-element cost, the cost of collections that hold nothing, the trap of multiplying that empty cost by a million keys, how to actually measure any of these numbers instead of guessing, and the two JDK features (compact headers, Valhalla) that are about to move every figure in this file. All byte figures below assume 64-bit HotSpot with compressed oops and compressed class pointers (the JVM default under a 32 GB heap) — a JVM without compressed oops roughly doubles every reference-sized field.

## Hierarchy before details

**D-139 — the node size ladder.**

| Structure | Fields (beyond header) | Raw bytes | Aligned bytes |
|---|---|---|---|
| `HashMap.Node` | hash(int), key(ref), value(ref), next(ref) | 12 header + 4 + 4 + 4 + 4 = 28 | 32 |
| `LinkedHashMap.Entry` | + before(ref), after(ref) on top of `HashMap.Node` | 28 + 4 + 4 = 36 | 40 |
| `HashMap.TreeNode` | + parent, left, right, prev(refs), red(boolean) on top of `LinkedHashMap.Entry` | 36 + 4+4+4 + 1 = 49 | 56 |
| `TreeMap.Entry` | left, right, parent(refs), key, value(refs), color(boolean) | 12 header + 4×5 + 1 = 33 | 40 |
| `LinkedList.Node` | prev(ref), item(ref), next(ref) | 12 header + 4×3 = 24 | 24 |
| `ArrayDeque` slot | one reference per array element | 4 | 4 |
| `EnumMap` slot | one reference per array element (universe-sized) | 4 | 4 |

Read this table as the map, not the streets: every arithmetic step below cites one of these rows, adds the boxed-payload cost on top, and rounds to an 8-byte alignment boundary.

## 3.15.13 `LinkedList.Node` `[NUM]`

Picture a doubly linked chain: each carriage has a coupling to the one behind, a coupling to the one ahead, and the cargo itself — three references, nothing else.

**Mechanism.** `Node<E>` holds `prev`, `item`, `next` — three reference fields, no hash, no color bit. Header 12 bytes + 3 × 4 bytes (compressed refs) = 24 bytes, already 8-byte aligned, so no padding is added. Compare this to `HashMap.Node`'s 32 bytes: the map node carries a cached `int hash` that the list node has no use for, and the list gets that back as pure savings — until you count the element. A `LinkedList<Integer>` node holding a boxed `Integer` costs 24 (node) + 16 (boxed `Integer`: 12 header + 4 int, padded to 16) = 40 bytes per element, plus the 24-byte fixed cost of the empty `LinkedList` object itself (`size` int, `first`/`last` refs).

**Gotcha.** People price `LinkedList` against `ArrayList` by node count and forget the boxed element is paid twice as expensive as an unboxed slot in an array-backed structure — an `ArrayList<Integer>` pays 4 bytes of array slot + the same 16-byte box, so the list's *only* extra cost is the 24-byte node wrapper, not the element itself.

> `LinkedList.Node` is a 24-byte three-reference carriage; the element's own boxing cost rides on top of it exactly as it would in any other collection.

## 3.15.14 `TreeMap.Entry` `[NUM]`

**Mechanism.** `TreeMap.Entry<K,V>` is a red-black tree node: `left`, `right`, `parent` (3 refs), `key`, `value` (2 refs), and a `boolean color`. Raw: 12 (header) + 5×4 (refs) + 1 (boolean) = 33 bytes, padded up to the next 8-byte boundary = 40 bytes. This sits between `HashMap.Node` (32, no tree pointers) and `HashMap.TreeNode` (56, which additionally carries a `prev` link and the `LinkedHashMap` before/after pair it inherits through `LinkedHashMap.Entry`).

**Gotcha.** A `TreeMap<Integer,Integer>` is not "a `HashMap` with sorting" cost-wise — it is 8 bytes heavier per entry than `HashMap` before you've even counted the two boxed `Integer` payloads, because every entry is permanently a tree node, whereas `HashMap` only pays 56-byte `TreeNode` cost on buckets that have actually treeified (≥8 collisions in a bucket with a table ≥64, per the treeification threshold covered in `02-internals-memory-headers.md`).

> `TreeMap.Entry` is a fixed 40-byte three-pointer-plus-color node — every entry, not just colliding ones, since the whole map is one tree.

## 3.15.15 `ArrayDeque` slot `[NUM]`

**Mechanism.** `ArrayDeque` is backed by a single circular `Object[]`, no per-element node at all — 4 bytes per compressed reference slot, full stop. The catch is that the array is deliberately over-allocated: HotSpot's implementation forces capacity to the next power of two above `(size + 1)`, and it always keeps at least one slot empty so that `head == tail` can mean "empty" unambiguously (if a full array let head equal tail, empty and full would be indistinguishable).

**Gotcha.** A deque holding 15 elements does not occupy a 15-slot array; it needs `head != tail` room, so it rounds up to a 16-slot power-of-two array with one slot permanently wasted as the sentinel gap, i.e. 16×4 = 64 bytes of slot cost for 15 elements' worth of references — one slot (4 bytes) is pure bookkeeping overhead, not a lot in absolute terms but a real deviation from "slots = elements."

> `ArrayDeque` pays 4 bytes per array slot plus one structurally wasted slot to keep the empty/full states distinguishable — no per-element node at all.

## 3.15.16 `EnumMap` `[NUM]`

**Mechanism.** `EnumMap` backs onto a `vals[]` array sized to the *entire enum's ordinal range* (`universe.length`), not to the number of keys actually present — 4 bytes per enum constant in the type, whether that slot holds a value or `null`. See `../specialised-maps/01-enum-collections.md` for the ordinal-indexing mechanism this depends on.

**Gotcha.** An `EnumMap` over a 200-constant enum with 2 keys populated still allocates a 200-slot array: 200 × 4 = 800 bytes of slot cost (plus the parallel `keyUniverse` reference the map shares with the enum's own static array) to represent 2 entries — the map is not sized by occupancy, it is sized by the type.

> `EnumMap` allocates one 4-byte slot per enum constant in the domain, regardless of how many of those constants are actually keys.

## 3.15.17 `EnumSet` (Regular) `[NUM]`

**Mechanism.** `RegularEnumSet` (used when the enum has ≤64 constants) stores membership as a single `long elements` bitmask field — one object, one `long` (8 bytes of payload), covering up to 64 members via bit-per-ordinal. Total instance size: 12 (header) + 8 (long, already aligned) = 20 bytes, which the allocator rounds to 24. `JumboEnumSet` takes over above 64 constants with a `long[]` sized to `ceil(universe/64)` words instead of one scalar.

**Gotcha.** Adding a 65th distinct constant to an enum silently switches every `EnumSet.noneOf(SomeEnum.class)` call for that type from `RegularEnumSet` to `JumboEnumSet` — same API, same call site, a different backing shape and a per-add masking calculation over an array instead of a scalar. See `../specialised-maps/01-enum-collections.md` for the ordinal-bit mapping.

> A `RegularEnumSet` is one 24-byte object holding an 8-byte bitmask, so up to 64 enum members cost the same fixed 24 bytes regardless of how many are actually in the set.

## 3.15.18 `BitSet` vs `HashSet<Integer>` `[NUM]` `[PROVE]`

Picture the same 1,000,000-element domain represented two ways: a wall of 1,000,000 individual light switches (`HashSet<Integer>`, one node object per switch) versus a single ribbon of 1,000,000 bits (`BitSet`, no per-bit object at all). See `../sets/03-bitset.md` for the `BitSet` API surface this backs.

**Proof, step by step.**

`BitSet` cost per element in the domain: backing store is `long[]`, one bit per element, 64 elements per 8-byte word → 8/64 = 0.125 bytes per element, plus a fixed ~24-byte object overhead for the `BitSet` instance itself (header + `words` ref + `wordsInUse` int, negligible when amortized over a million elements).

`HashSet<Integer>` cost per element actually present:
- `HashMap.Node` (a `HashSet` is backed by a `HashMap<E,Object>`, value always the shared `PRESENT` sentinel): 32 bytes.
- Boxed `Integer` key: 12 (header) + 4 (int) = 16, padded to 16 bytes. (Values outside `Integer.IntegerCache`'s -128..127 range are not cached, so this is a fresh allocation per element.)
- Array slot reference in the table itself: 4 bytes.
- Sum: 32 + 16 + 4 = 52 bytes per element.

Ratio: 52 / 0.125 = **416×**, in the same neighborhood as the 400× figure this leaf names — the exact multiple depends on load factor and whether the `Integer` was cache-hit, but the order of magnitude is stable.

**Gotcha.** This ratio only holds when the domain is dense and bounded (you know the universe size up front) — a `BitSet` over a sparse domain (say, 1,000 set bits scattered across a range of 2^31) is a *worse* trade than `HashSet<Integer>`, because `BitSet` pays for every bit in the range whether set or not, while `HashSet` pays only for members present.

> A `BitSet` costs one-eighth of a byte per element in its domain; a `HashSet<Integer>` costs roughly 52 bytes per element actually present — a ~400× gap that only pays off when the domain is dense.

## 3.15.19 `ConcurrentHashMap` overhead vs `HashMap` `[NUM]`

**Mechanism.** `ConcurrentHashMap.Node` has the same four-field shape as `HashMap.Node` (hash, key, value, next) and the same 32-byte size — concurrency doesn't tax the per-entry node. The overhead lives elsewhere: under contended `size()`/counting operations, `ConcurrentHashMap` lazily allocates a `CounterCell[]` array, where each `CounterCell` is `@Contended`-annotated to force cache-line padding (128 bytes of padding on either side of the `value` field with `-XX:-RestrictContended` off, i.e. a `CounterCell` instance can occupy roughly 128–192 bytes once JVM padding is applied) specifically to prevent false sharing between threads incrementing different cells. See `../concurrent-collections/03-internals-chm-b.md` for when `CounterCell[]` actually gets allocated (only under detected CAS contention on the base counter, not on every map).

**Gotcha.** An uncontended `ConcurrentHashMap` with light single-thread traffic never allocates `CounterCell[]` at all — it accumulates size in a single `baseCount` field — so "CHM is heavier than HashMap" is only true once contention actually triggers the striped counter array; the steady-state per-entry cost is identical to `HashMap`.

> `ConcurrentHashMap`'s node is exactly as heavy as `HashMap`'s (32 bytes); the extra cost is a lazily-allocated, deliberately cache-padded `CounterCell[]` that only appears under real counter contention.

## 3.15.20 Empty-collection cost `[NUM]` `[PROVE]`

Picture three jars bought before a single item is dropped in — an empty `ArrayList`, an empty `HashMap`, and an `ArrayList` pre-sized for 1,000 items that arrive later. None of them are actually empty in byte terms.

**Proof, step by step.**

`new ArrayList<>()`: fields are `elementData` (ref), `size` (int), plus the inherited `modCount` (int) from `AbstractList`. 12 (header) + 4 + 4 + 4 = 24 bytes. Crucially, `elementData` does **not** point to a fresh array — it points to the static shared `DEFAULTCAPACITY_EMPTY_ELEMENTDATA` array, so there is no separate array allocation at all until the first `add()`. Total: 24 bytes, full stop.

`new HashMap<>()`: no `table` array is allocated at construction (`table` stays `null` until the first `put()` triggers `resize()`). Fields: `table` (ref), `entrySet` (ref), `size` (int), `modCount` (int), `threshold` (int), `loadFactor` (float), plus the inherited `keySet`/`values` refs from `AbstractMap`. 12 (header) + 4×8 (six refs, two ints, one float — all 4 bytes compressed/primitive) = 12 + 32 = 44, padded to 48 bytes.

`new ArrayList<>(1000)`: the constructor *does* eagerly allocate `new Object[1000]` this time. Array cost: 16-byte array header (12 base + 4 length word, since array headers carry a length field the ordinary object header doesn't) + 1000 × 4 (compressed ref slots) = 16 + 4000 = 4016 bytes, plus the 24-byte `ArrayList` shell itself = 24 + 4016 = **4040 bytes total**, of which 4016 bytes are pure headroom for elements that don't exist yet.

**Gotcha.** `new ArrayList<>(1000)` looks like a performance win (avoids resize-copies) but it is a real, immediate 4 KB allocation whether or not you ever add 1000 elements — sizing collections defensively "just in case" is a memory commitment, not a free hint.

> An empty no-arg `ArrayList` costs 24 bytes because it shares a static empty array; an empty no-arg `HashMap` costs 48 bytes because it defers the table but carries more scalar bookkeeping fields; a capacity-hinted `ArrayList` pays for its backing array immediately, not lazily.

## 3.15.21 The map-of-empty-lists trap `[NUM]` `[TRAP]`

**Pitfall:** the multimap idiom — `map.computeIfAbsent(k, x -> new ArrayList<>()).add(v)`, covered as an API pattern in `../utilities/04-map-default-methods.md` — looks free because each call site is one line. Priced per key, for a map with one million distinct keys each holding exactly one value, it is not.

**Mechanism, step by step, per key:**
- `HashMap.Node` for the outer map: 32 bytes (from D-139).
- The boxed key itself (assume an `Integer` outside the cache range, or any other small boxed type): ~16 bytes.
- The `ArrayList` object created by `computeIfAbsent`: 24 bytes (per 3.15.20) — but it is no longer holding the shared empty array, because the very next call is `.add(v)`, which forces `ensureCapacity` to allocate a **real** backing array sized to `DEFAULT_CAPACITY = 10`, not to 1: 16 (array header) + 10 × 4 (ref slots) = 56 bytes, even though only one slot is used.
- The boxed value: ~16 bytes.
- **Per-key total: 32 + 16 + 24 + 56 + 16 = 144 bytes**, to represent one key mapped to one value.
- **At one million keys: ~144,000,000 bytes ≈ 137 MiB**, almost entirely spent on an oversized 10-slot array holding one element, times a million.

**Alternatives priced side by side:**

| Approach | Per-key cost | 1M-key total | What you give up |
|---|---|---|---|
| `Map<K, List<V>>` via `computeIfAbsent` | 144 B (32 Node + 16 key + 24 List + 56 array-of-10 + 16 value) | ~137 MiB | nothing — this is the naive baseline |
| Flat `Map<K, V>` (no list at all, singleton case) | 48 B (32 Node + 16 value; key already counted once) | ~46 MiB | can't hold more than one value per key without a schema change later |
| `Map<K, Object>` sentinel (single value stored raw, promote to `List` only when a 2nd value arrives) | 48 B for singleton keys, 144 B only for multi-value keys | ~46 MiB if singletons dominate | call sites must `instanceof`-check and promote, extra branching complexity |
| Guava `ArrayListMultimap<K,V>` | same `HashMap<K, Collection<V>>` shape internally, plus Guava's own wrapper `Collection` view objects per key | ≥144 B, typically a bit more | pulls in a dependency for what is structurally the same trap, just hidden behind a nicer API |

**Insight:** the fix is rarely "use a different collection" — it's asking whether the value is *usually* singleton. If most keys map to exactly one value and only a minority fan out, a sentinel-then-promote scheme (or simply `Map<K, V>` with an explicit "collision" escape hatch) turns a 144-byte-per-key structure into a 48-byte one for the common case, a ~3× reduction at a million-key scale that shows up directly as reduced GC pressure, not just reduced footprint.

> `computeIfAbsent(k, () -> new ArrayList<>())` for a singleton value costs roughly 144 bytes — 32 for the outer node, 24 for the `ArrayList` shell, and 56 for a 10-slot array holding one element — three times the 48 bytes a flat `Map<K,V>` would cost for the same singleton fact.

## 3.15.22 Measuring it: JOL `[X-REF 06]`

**Mechanism.** Every number in this file so far is arithmetic from field layout rules; JOL (Java Object Layout, `org.openjdk.jol:jol-core`) measures the *actual* layout HotSpot chose, which is the only way to confirm compressed-oops assumptions, padding decisions, and alignment on your actual JVM. `ClassLayout.parseInstance(o).toPrintable()` prints one object's field offsets and padding; `GraphLayout.parseInstance(o).totalSize()` walks the full retained object graph (an object plus everything it references) and sums real bytes, which is what you want for "how much does this whole `HashMap` actually cost," not just the header object.

**Example.**

```java
import org.openjdk.jol.info.ClassLayout;
import org.openjdk.jol.info.GraphLayout;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

public final class FootprintProbe {

    public static void main(String[] args) {
        HashMap<Integer, String> emptyMap = new HashMap<>();
        System.out.println(ClassLayout.parseInstance(emptyMap).toPrintable());
        System.out.println("Empty HashMap retained size: "
                + GraphLayout.parseInstance(emptyMap).totalSize() + " bytes");

        Map<Integer, List<Integer>> multimap = new HashMap<>();
        for (int key = 0; key < 1000; key++) {
            multimap.computeIfAbsent(key, k -> new ArrayList<>()).add(key);
        }
        System.out.println("1000-key map-of-singleton-lists retained size: "
                + GraphLayout.parseInstance(multimap).totalSize() + " bytes");
        System.out.println("Bytes per key: "
                + (GraphLayout.parseInstance(multimap).totalSize() / 1000.0));
    }
}
```

Running this with `-Djol.magicFieldOffset=true` on the classpath (Maven: add `org.openjdk.jol:jol-core` as a dependency) prints exact per-field offsets for the empty map and a real retained-size figure for the multimap trap from 3.15.21, on your exact JVM build, with your exact heap flags — not the generic arithmetic this file uses.

**Gotcha.** `GraphLayout.parseInstance(root).totalSize()` walks the object graph reachable *only* from the given root — if two structures share a substructure (interned strings, cached boxed `Integer`s in [-128,127], the shared empty-array constants from 3.15.20), measuring them separately double-counts the shared part; `GraphLayout` supports passing multiple roots specifically to detect and de-duplicate that sharing.

**Why `Runtime.freeMemory()` deltas lie.** The common home-grown alternative — read `Runtime.getRuntime().freeMemory()`, allocate the structure, read it again, subtract — fails for three independent reasons: (1) GC can run between the two reads, reclaiming unrelated garbage and making the delta *negative* or artificially small; (2) allocations happen out of thread-local allocation buffers (TLABs) that are claimed from the heap in large chunks ahead of actual object creation, so a single small allocation may show zero delta (it fit in already-claimed TLAB space) or a large delta (it triggered a fresh TLAB claim); (3) anything else running on the JVM — a background compiler thread, a finalizer, string interning from earlier code — allocates in the same window and pollutes the reading. JOL avoids all three by inspecting the object's actual layout metadata rather than inferring size from heap occupancy before and after.

> JOL's `ClassLayout` reports one object's real field layout and `GraphLayout.totalSize()` sums an entire reachable graph, both from HotSpot's own metadata; `Runtime.freeMemory()` deltas are unreliable because GC timing, TLAB claiming, and concurrent allocation all happen invisibly between the two reads.

## 3.15.23 Compact object headers and Lilliput `[RESEARCH]` `[NUM]`

**Mechanism.** Project Lilliput's header-compaction work shipped in two stages: JEP 450 introduced `-XX:+UnlockExperimentalVMOptions -XX:+UseCompactObjectHeaders` as an experimental flag in JDK 24, and JEP 519 promoted it to a supported product feature in JDK 25, droppable via the plain `-XX:+UseCompactObjectHeaders` flag with no experimental-unlock required. The change folds the klass pointer into the mark word instead of storing them as two separate fields, shrinking the ordinary object header from 96–128 bits (12–16 bytes depending on array-ness) down to 64 bits (8 bytes) uniformly.

**What shifts.** Every non-array object figure in this file and in `02-internals-memory-headers.md` drops by 4 bytes once compact headers are active: `HashMap.Node` goes from 32 to 28 (then re-aligns, likely staying 32 in practice depending on field packing, or dropping to 24 if the freed 4 bytes let a field repack), `LinkedList.Node` from 24 toward 20/24, the empty `ArrayList` from 24 toward 20. Publicly reported results (per JAVAPRO and InfoQ coverage of production rollouts, including Amazon's internal testing) show roughly 22% heap savings and about 8% CPU time reduction on SPECjbb2015-style workloads — the CPU win comes from fewer GC cycles needed at the same live-data size, not from cheaper per-object access.

**Gotcha.** This is a JVM-wide flag, not a per-collection opt-in — you cannot apply it selectively to just the `HashMap`-heavy part of an application, and array headers (which already carry a length word) are affected differently than scalar object headers, so the ladder in D-139 should be re-measured with JOL (3.15.22) rather than hand-recomputed once you're running JDK 25 with the flag enabled.

> Compact object headers shrink every ordinary object's header from 12–16 bytes to 8, moving from experimental (`-XX:+UseCompactObjectHeaders`, JDK 24, JEP 450) to a supported product default-off flag (JDK 25, JEP 519) — every byte figure in this file is a JDK-24-and-earlier baseline that this flag revises downward.

## 3.15.24 Value classes and Valhalla `[RESEARCH]`

**Mechanism.** The structural reason boxed collections are expensive at all — a `List<Integer>` paying a 16-byte object plus a 12-byte header for every int, instead of storing the int inline — is that generics require reference types, and Java has had no way to make a reference-shaped type behave like a primitive. Project Valhalla's value classes are the intended fix: a value class has no object identity, which lets the JVM "flatten" it directly into an array or a field instead of allocating a separate heap object and storing a pointer to it, eliminating the per-element header and pointer-indirection cost this entire file has been pricing.

**Current status.** JEP 401 ("Value Classes and Objects") is a preview feature, requiring `--enable-preview` at both compile and run time; as of the most recent public reporting it is targeted at JDK 28 (projected March 2027), not JDK 25 or JDK 26. It migrates several existing JDK "value-based classes" (including boxed primitive wrappers like `Integer`) toward value-class semantics and adds scalarization/flattening for qualifying array and field storage. Brian Goetz has publicly cautioned that the feature exiting preview entirely by JDK 29 would be an optimistic timeline, meaning boxed-collection costs priced throughout this file remain the realistic planning baseline for the near term.

**Unverified:** the exact final JDK version where value classes exit preview status is not yet fixed as of this writing — treat JDK 28 as the current preview target, not a committed non-preview ship date.

> Value classes aim to let boxed elements flatten into arrays without per-element headers or pointer indirection, but as a JEP 401 preview feature currently targeting JDK 28, the boxed-cost arithmetic throughout this file remains the number to plan against for Java 21 and its near-term successors.

## Pitfalls

### "An empty collection costs nothing until I put something in it"

**Wrong**
```java
Map<String, List<Integer>> cache = new HashMap<>();
for (int i = 0; i < 1_000_000; i++) {
    cache.computeIfAbsent("key" + i, k -> new ArrayList<>()).add(i);
}
// ~137 MB resident for 1,000,000 single-element lists — see 3.15.21
```

**Right**
```java
Map<String, Integer> singletons = new HashMap<>();
for (int i = 0; i < 1_000_000; i++) {
    singletons.put("key" + i, i);
}
// ~46 MB for the same 1,000,000 facts when each key truly has one value
```

**Why people believe it:** the `ArrayList()` constructor genuinely is free (shared empty array, 3.15.20) and the JavaDoc for `computeIfAbsent` never mentions that the very next `.add()` call forces a 10-element array allocation — the two facts individually are both true and both misleading in combination.

### "A `TreeMap` costs the same per entry as a `HashMap`, just sorted"

**Wrong**
```java
TreeMap<Integer, Integer> sorted = new TreeMap<>();
for (int i = 0; i < 1_000_000; i++) sorted.put(i, i);
// Entry cost: 40 bytes each, not 32 — 8 MB heavier than a HashMap of the same size
```

**Right**
```java
// If you don't need range queries or ordered iteration every time,
// sort a HashMap's entries on the rare occasions you do need order:
HashMap<Integer, Integer> unsorted = new HashMap<>();
for (int i = 0; i < 1_000_000; i++) unsorted.put(i, i);
List<Integer> orderedKeys = unsorted.keySet().stream().sorted().toList();
```

**Why people believe it:** `TreeMap` and `HashMap` share the `Map` interface and a "node with key and value" mental model, so the extra `left`/`right`/`parent`/`color` fields needed for the red-black tree are invisible unless you've counted `TreeMap.Entry`'s fields explicitly (3.15.14).

### "`BitSet` is a legacy curiosity, `HashSet<Integer>` is the modern idiomatic choice"

**Wrong**
```java
Set<Integer> flags = new HashSet<>();
for (int i = 0; i < 1_000_000; i++) if (isEven(i)) flags.add(i);
// ~26 MB for 500,000 members over a known 1,000,000-wide domain
```

**Right**
```java
BitSet flags = new BitSet(1_000_000);
for (int i = 0; i < 1_000_000; i++) if (isEven(i)) flags.set(i);
// ~125 KB for the same 500,000 members — see ../sets/03-bitset.md
```

**Why people believe it:** `BitSet` predates generics and has an awkward `int`-only API, which reads as "old and clunky" even though its bit-per-element storage remains roughly 400× denser than a boxed `Integer` set (3.15.18) whenever the domain is known and dense.

## Cheat sheet

| Structure | Fixed/empty cost | Per-element cost | Notes |
|---|---|---|---|
| `ArrayList` (no-arg) | 24 B | 4 B/slot + boxing if applicable | shares static empty array until first add |
| `ArrayList(n)` | 24 + 16 + 4n B | same | array allocated immediately |
| `HashMap` (no-arg) | 48 B | 32 B/entry (`Node`) + 2 boxed payloads | table allocated lazily on first `put` |
| `LinkedHashMap` | 48 B (+ head/tail refs) | 40 B/entry | +8 B over `HashMap` for before/after links |
| `TreeMap` | ~40 B shell | 40 B/entry (`Entry`) | every entry is a tree node, always |
| `LinkedList` | 24 B | 24 B/node + boxing | node cost cheaper than `HashMap.Node`, boxing cost identical |
| `ArrayDeque` | ~24 B shell | 4 B/slot, power-of-two sized, 1 slot wasted | no per-element node |
| `EnumMap` | 4 B × universe size | 0 extra per populated key | sized by type, not occupancy |
| `EnumSet` (≤64 members) | 24 B total | 0 extra per member | single `long` bitmask |
| `BitSet` | ~24 B shell | 0.125 B/element in domain | dense-domain only |
| `HashSet<Integer>` | 48 B | ~52 B/element present | 32 (Node) + 16 (box) + 4 (slot) |
| `ConcurrentHashMap` | ~48 B + lazy `CounterCell[]` | 32 B/entry (same as `HashMap`) | counter array only under contention |
| Map-of-singleton-`ArrayList` | — | ~144 B/key | vs. ~48 B/key for a flat `Map<K,V>` |

## Self-test

**Q1.** Why does `new ArrayList<>()` cost only 24 bytes while `new ArrayList<>(1000)` costs over 4000 bytes, even though neither has had an element added yet?

<details><summary>Answer</summary>

The no-arg constructor points `elementData` at a shared static `DEFAULTCAPACITY_EMPTY_ELEMENTDATA` array — no new array is allocated, so the cost is just the 24-byte object shell. The capacity constructor eagerly allocates a real `Object[1000]`, which costs a 16-byte array header plus 1000 × 4 bytes of reference slots (4016 bytes) immediately, regardless of whether elements are ever added.

</details>

**Q2.** Work out why a `TreeMap.Entry` (40 bytes) is smaller than a `HashMap.TreeNode` (56 bytes) even though both represent a red-black tree node.

<details><summary>Answer</summary>

`TreeMap.Entry` only carries what a standalone red-black tree needs: `left`, `right`, `parent` (3 refs), `key`, `value` (2 refs), and a `color` boolean — 33 bytes raw, 40 aligned. `HashMap.TreeNode` additionally inherits the `LinkedHashMap.Entry` before/after links (because `TreeNode` extends `LinkedHashMap.Entry`, reused for its doubly-linked bin-traversal order) plus its own `prev` pointer for bin-list untreeification, on top of the same `parent`/`left`/`right`/`red` fields — more inherited fields push it to 56.

</details>

**Q3.** A `HashSet<Integer>` and a `BitSet` both represent membership over the integers 0–999,999. When does the `HashSet` actually win on memory?

<details><summary>Answer</summary>

When the set is sparse relative to the domain — the `BitSet` always pays for all 1,000,000 bit-positions (125,000 bytes) regardless of how many are set, while the `HashSet` pays only ~52 bytes per member actually present. Below roughly 125,000/52 ≈ 2,400 members, the `HashSet` is cheaper; above that, the `BitSet` wins, and by 500,000 members the `BitSet` is roughly 400× cheaper.

</details>

**Q4.** Why does `map.computeIfAbsent(k, () -> new ArrayList<>()).add(v)` allocate a 10-slot backing array even when the caller only ever adds one element per key?

<details><summary>Answer</summary>

`computeIfAbsent` only supplies the empty `ArrayList` (24 bytes, sharing the static empty array). The very next call, `.add(v)`, is what actually grows the list — and `ArrayList`'s growth logic on first insertion resizes from the shared empty array to `DEFAULT_CAPACITY = 10`, not to 1, because the constructor has no way to know only one element is coming. That 10-slot array (56 bytes) is paid in full even though 9 of its slots stay `null` forever.

</details>

**Q5.** Give two independent reasons `Runtime.getRuntime().freeMemory()` deltas are unreliable for measuring an object's size, and name the JOL API that avoids both.

<details><summary>Answer</summary>

(1) Garbage collection can run between the "before" and "after" reads, reclaiming unrelated garbage and shifting free memory independently of the allocation being measured. (2) Allocations are served out of per-thread TLABs claimed from the heap in bulk ahead of actual object creation, so a small allocation may show no delta (served from already-claimed TLAB space) or a large one (triggered a fresh TLAB claim) with no relationship to the object's real size. `GraphLayout.parseInstance(o).totalSize()` avoids both by reading HotSpot's own layout metadata for the reachable graph instead of inferring size from heap occupancy snapshots.

</details>

**Q6.** Under compact object headers (JEP 519, JDK 25), what changes about the D-139 ladder, and what does not?

<details><summary>Answer</summary>

Every ordinary (non-array) object's header shrinks from 12–16 bytes down to 8 bytes, because the klass pointer is folded into the mark word — this shifts scalar-node figures like `HashMap.Node`, `LinkedList.Node`, and the empty `ArrayList`/`HashMap` shells downward by up to 4 bytes each (subject to re-alignment). Array headers, which carry an additional length word, are affected differently and should be re-measured with JOL rather than assumed to shrink by the same fixed amount. The flag is JVM-wide, not selectable per collection.

</details>

**Q7.** Why does a `LinkedList<Integer>` cost more per element than an `ArrayList<Integer>`, and by how much?

<details><summary>Answer</summary>

Both pay the same 16-byte boxed-`Integer` cost per element. `ArrayList` additionally pays only a 4-byte array slot per element, while `LinkedList` pays a full 24-byte `Node` object (three references: prev, item, next) per element — a 20-byte-per-element gap on top of identical boxing costs.

</details>

**Q8.** Why might a `ConcurrentHashMap` under light, single-threaded use cost exactly the same per entry as a plain `HashMap`, while the same map under heavy multi-threaded contention costs measurably more?

<details><summary>Answer</summary>

`ConcurrentHashMap.Node` has the identical 32-byte four-field shape as `HashMap.Node`, so per-entry cost is unchanged in either case. The extra cost only appears when CAS contention is detected on the shared `baseCount` field during concurrent size-tracking, which triggers lazy allocation of a `CounterCell[]` array whose cells are `@Contended`-padded to whole cache lines specifically to avoid false sharing — a cost that simply never materializes without real contention.

</details>

---

**Leaves covered:** 3.15.13–3.15.24 (12 leaves)
**Leaves deferred:** none
**Diagrams included:** D-139 (rendered as a Markdown table)
**Target version:** Java 21 LTS
**Lines:** 350
