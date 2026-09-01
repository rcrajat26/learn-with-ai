# 02 Java Collections — TreeMap — INTERNALS (§3.8.16–3.8.17)

**Target version: Java 21 LTS.** | [Index](../00-index.md)
Previous: [tree-map/03b-internals-b2-buildfromsorted.md](03b-internals-b2-buildfromsorted.md) · Next: [tree-map/03c-internals-b3-comparisons-and-alternatives.md](03c-internals-b3-comparisons-and-alternatives.md)

## 1. `NavigableSubMap`, `AscendingSubMap`, `DescendingSubMap`, and `inRange` (§3.8.16)

### Mental model

A submap is a window, not a copy. `map.subMap(20, 50)` does not allocate a new
tree and does not copy any entries. It returns a thin object that holds a
reference to the *same* backing `TreeMap`, plus a pair of bounds (`lo`, `hi`)
and two inclusive flags. Every read or write you issue through that window is
translated into an operation on the parent's tree, with one extra step
inserted first: a boundary check. Move the window, and you see a different
slice of the same tree. Mutate through the window, and the parent tree
changes — there is only ever one tree.

### Why it exists

If a submap were a plain delegate with no bounds-checking layer, a caller
could do `map.subMap(20, 50).put(999, v)` and silently poke a key far outside
the window into the parent tree — a mutation the caller asked the *view* to
perform, but which the view had no business allowing, because it breaks the
contract that "everything you see and do through this view stays inside
`[20, 50)`". `NavigableSubMap` exists specifically to be the layer that
intercepts every accessor and mutator and rejects anything that would violate
that contract. Without it, `subMap` would be nothing more than confusing
`TreeMap` with a note attached, not an actual `SortedMap`/`NavigableMap`.

### When to reach for it / when not

Reach for `subMap`/`headMap`/`tailMap` when you need **windowed access** to a
live, mutating tree: sliding windows over a timestamp-keyed map, tiered price
bands, paginating through a sorted keyspace, or bulk-clearing a range with
`submap.clear()`. `tree-map/01-navigable-api.md` covers the call shapes for
these use cases in more depth — this file is about what happens underneath
once you've made the call. The defining property is that the view stays
*live*: further inserts into the parent that land inside the window
immediately become visible through the view, and vice versa.

Reach instead for a fresh copy — `new TreeMap<>(map.subMap(20, 50))` — when
you need a **snapshot** that must not change when the parent changes later,
or when you plan to hand the range to another thread and don't want to think
about concurrent structural modification of the parent tree while that
thread iterates. A copy costs O(k log k) up front (k = range size) but then
lives an independent life; a view costs nothing to create but is only ever as
stable as the parent tree underneath it.

### How it works — source

`TreeMap` implements range views with an abstract package-private base class
and two concrete subclasses, structured roughly as follows (region-cited to
`java.util.TreeMap`'s inner classes; exact line numbers vary by build):

```java
// java.util.TreeMap, inner class region — abstract base for all range views
abstract static class NavigableSubMap<K,V> extends AbstractMap<K,V>
        implements NavigableMap<K,V>, java.io.Serializable {

    final TreeMap<K,V> m;   // the one and only backing tree

    final K lo, hi;         // range bounds (may be absent — see fromStart/toEnd)
    final boolean fromStart, toEnd;
    final boolean loInclusive, hiInclusive;

    NavigableSubMap(TreeMap<K,V> m,
                     boolean fromStart, K lo, boolean loInclusive,
                     boolean toEnd,     K hi, boolean hiInclusive) {
        // ... validates lo <= hi under m.comparator when both bounds present
        this.m = m;
        this.fromStart = fromStart; this.lo = lo; this.loInclusive = loInclusive;
        this.toEnd     = toEnd;     this.hi = hi; this.hiInclusive = hiInclusive;
    }

    // -- range predicates, the load-bearing methods of this whole class --

    boolean tooLow(Object key) {
        if (!fromStart) {
            int c = m.compare(key, lo);
            if (c < 0 || (c == 0 && !loInclusive)) return true;
        }
        return false;
    }

    boolean tooHigh(Object key) {
        if (!toEnd) {
            int c = m.compare(key, hi);
            if (c > 0 || (c == 0 && !hiInclusive)) return true;
        }
        return false;
    }

    boolean inRange(Object key) {
        return !tooLow(key) && !tooHigh(key);
    }

    // variant used by absolute-bound methods (headMap/tailMap semantics)
    boolean inRange(Object key, boolean inclusive) {
        return inclusive ? inRange(key) : inRangeExclusive(key);
    }
    // ...
}
```

`AscendingSubMap` and `DescendingSubMap` both extend `NavigableSubMap`. They
do **not** duplicate the bounds logic above — `tooLow`/`tooHigh`/`inRange`
live once, in the base class, and both subclasses inherit them unchanged.
What differs between the two subclasses is iteration direction and which end
of the range `firstKey()`/`lastKey()` resolve to: `AscendingSubMap.firstKey()`
walks toward `lo`, `DescendingSubMap.firstKey()` walks toward `hi`, because
"first" means "first in this view's iteration order," not "smallest key."

Every mutator and most accessors on a submap route through `inRange` before
touching the parent tree. `put`, for instance, is structured as:

```java
// AscendingSubMap<K,V>
public V put(K key, V value) {
    if (!inRange(key))
        throw new IllegalArgumentException("key out of range");
    return m.put(key, value);
}
```

That is the entire contract in one line: check the bound, then — and only
then — delegate to the *same* `TreeMap.put` that a direct caller would use.
There is no separate insertion path for submap writes; the view is a gate in
front of the parent's ordinary `put`, not a different implementation of
`put`.

### Diagram

![TreeMap range views are range-restricted: subMap(20,50) as a bracket on the key axis, a put(60,v) through the view rejected by inRange with IllegalArgumentException, a put(30,v) accepted through into the parent tree](../diagrams/D-37-treemap-range-view-inrange.svg)

The bracket spans `[20, 50)` on the key axis. A write aimed at key 60 never
reaches the parent tree — `inRange` intercepts it at the view boundary and
throws. A write aimed at key 30 passes the same check and lands in the parent
tree exactly where an ordinary `TreeMap.put(30, v)` would have put it; the
view contributes nothing to *where* the entry goes, only to *whether* the
call is allowed to happen at all.

### Example — a rejected and an accepted write

```java
import java.util.NavigableMap;
import java.util.TreeMap;

public class SubMapRangeDemo {
    public static void main(String[] args) {
        TreeMap<Integer, String> map = new TreeMap<>();
        map.put(10, "a");
        map.put(20, "b");
        map.put(40, "c");
        map.put(60, "d");

        NavigableMap<Integer, String> window = map.subMap(20, 50); // [20, 50)

        try {
            window.put(60, "x"); // 60 is outside [20, 50)
        } catch (IllegalArgumentException e) {
            System.out.println("rejected: " + e.getMessage());
            // rejected: key out of range
        }

        window.put(30, "x"); // 30 is inside [20, 50) — accepted
        System.out.println(map.get(30));      // x  — visible in the parent
        System.out.println(map.containsKey(60)); // true — the rejected write never happened
    }
}
```

The accepted write at key 30 is visible through `map` immediately afterward,
because `window` and `map` share the same tree — there was never a copy to
go stale.

### The gotcha

**Pitfall:** the natural but wrong assumption is that a write outside the
range either gets silently dropped or auto-expands the window to fit. It
does neither: `put` on an out-of-range key throws `IllegalArgumentException`
unconditionally, every time, with no configuration to soften it. Code that
expects "the map just grows to include what I inserted" will crash the first
time it inserts near a range boundary in production data, even though it
worked fine in a happy-path test with data safely inside the window.

**Insight:** the second gotcha is quieter — a submap's own `size()` is *not*
cached the way `TreeMap.size()` is. The parent's `size()` is a field
maintained incrementally on every structural change, so it's O(1). A
submap has no equivalent field, because the set of entries "in range" shifts
every time the parent tree changes underneath it; caching a count would mean
invalidating it on every parent mutation, which is exactly as expensive as
not caching it. So `submap.size()` walks the range and counts, an O(k)
operation where k is the number of entries currently in the window. Calling
it in a loop, once per iteration, silently turns an O(n) traversal into
O(n·k).

**Interview:** "why does `TreeMap.size()` cost O(1) but `subMap.size()` cost
O(k)?" is a direct probe of whether the candidate understands that the view
shares the parent's tree rather than owning its own bookkeeping.

> **Definition — `NavigableSubMap`:** the abstract, package-private base
> class backing every `TreeMap` range view. It holds a reference to the
> parent `TreeMap`, a low bound and high bound with independent inclusive
> flags, and the shared `tooLow`/`tooHigh`/`inRange` predicates that every
> submap accessor and mutator must pass before touching the parent tree.
> `AscendingSubMap` and `DescendingSubMap` extend it, differing only in
> iteration direction and which bound resolves to "first."

## 2. Memory per entry: 40 bytes vs `HashMap`'s 32 (§3.8.17)

### Mental model

Every extra pointer a red-black tree node needs beyond a hash bin is a real,
payable cost per entry — not a free abstraction. `TreeMap.Entry` carries a
`parent` reference that `HashMap.Node` has no equivalent for, plus a `color`
bit that has no `HashMap` equivalent either. Those aren't implementation
details that vanish at runtime; they occupy actual bytes, in every single
entry, for the lifetime of the map. At a million entries, that difference is
measured in tens of megabytes, not counted in the abstract.

### Why it exists

The `parent` pointer and the `color` bit are not incidental — they are the
mechanism a red-black tree uses to buy its O(log n) worst-case guarantee.
Fixup after insertion and deletion (`tree-map/02c-internals-a3-fixafterinsertion.md`,
`tree-map/02d-internals-a4-fixafterdeletion.md`) walks *up* the tree from the
touched node, and rotations need to relink a node's parent's parent — none of
that is possible without a `parent` reference, and none of the rotation and
recoloring logic that keeps the tree balanced is expressible without a colour
bit per node. A hash bin has no analogous invariant to maintain, so
`HashMap.Node` has no analogous field. The 8-byte difference (`parent` +
`color`, padding aside) is the balance guarantee's line item on the memory
bill.

### When to prefer which

Purely on the memory axis: prefer `HashMap` when no ordering guarantee is
needed and memory is under real pressure — the flat 25% per-entry surcharge
of `TreeMap` compounds linearly with entry count and is pure overhead if
nothing ever calls a range or ordered-iteration method. Prefer `TreeMap` when
range queries, floor/ceiling lookups, or sorted iteration are actually load-
bearing in the design; the 25% memory surcharge is, in practice, usually the
*smaller* of the two costs `TreeMap` imposes relative to `HashMap` — the
larger constant-factor cost is per-operation CPU time from O(log n)
comparator calls plus pointer chasing versus `HashMap`'s O(1) hash-and-probe,
which is developed in full in `03c-internals-b3-comparisons-and-alternatives.md`,
the next file in this series. Don't pick `TreeMap` for the memory profile —
pick it for the ordering, and pay both costs knowingly.

### How it works — the arithmetic `[NUM]`

`TreeMap.Entry<K,V>` declares these fields:

```java
static final class Entry<K,V> implements Map.Entry<K,V> {
    K key;
    V value;
    Entry<K,V> left;
    Entry<K,V> right;
    Entry<K,V> parent;
    boolean color = BLACK;
    // ...
}
```

On 64-bit HotSpot with compressed oops enabled (the default for heaps under
~32 GB, which covers the overwhelming majority of real JVM deployments), an
ordinary object reference is compressed to 4 bytes, and the object header is
12 bytes (an 8-byte mark word plus a 4-byte compressed klass pointer). Field
by field:

| Field | Type | Size (compressed oops) |
|---|---|---|
| object header | — | 12 |
| `key` | reference | 4 |
| `value` | reference | 4 |
| `left` | reference | 4 |
| `right` | reference | 4 |
| `parent` | reference | 4 |
| `color` | `boolean` | 1 |
| **subtotal** | | **33** |
| padding to 8-byte alignment | | 7 |
| **total** | | **40** |

Worked as arithmetic: `12` (header) `+ 5 × 4` (five references: key, value,
left, right, parent) `= 12 + 20 = 32`, `+ 1` (the `color` boolean) `= 33`,
rounded up to the next multiple of 8 for HotSpot's object-alignment
requirement `= 40`. The 7 bytes between 33 and 40 are pure padding — they
hold no data, they exist only because HotSpot lays out every object on an
8-byte boundary.

Now `HashMap.Node<K,V>`:

```java
static class Node<K,V> implements Map.Entry<K,V> {
    final int hash;
    final K key;
    V value;
    Node<K,V> next;
    // ...
}
```

`12` (header) `+ 4` (`int hash`) `+ 4 × 3` (three references: key, value,
`next`) `= 12 + 4 + 12 = 28`, rounded up to the next multiple of 8 `= 32`.
Four bytes of padding between 28 and 32.

| Class | Header | Fields | Raw subtotal | Padded total |
|---|---|---|---|---|
| `TreeMap.Entry` | 12 | 4 refs × 4 + `parent`(4) + `color`(1) = 21 | 33 | **40** |
| `HashMap.Node` | 12 | `hash`(4) + 3 refs × 4 = 16 | 28 | **32** |

These are field-by-field calculated sizes, derived from HotSpot's known
object layout rules (12-byte header, 4-byte compressed references, 8-byte
alignment) — **not** numbers obtained by running `Runtime.totalMemory()`,
an instrumentation agent, or any other measurement tool against a live heap.
Plain Java gives no supported API for reading a single object's retained
size directly; `Runtime.totalMemory()`/`freeMemory()` measure heap-wide
totals contaminated by GC timing, JIT-compiled code, and other live objects,
and cannot isolate one object's byte count. The only trustworthy way to get
a per-object number is exactly what's shown above: read the field list from
source and apply the layout rules by hand (or use a real instrumentation
tool such as JOL — Java Object Layout — outside plain Java, which this note
does not claim to have done).

### Diagram

![TreeMap.Entry (40 bytes: 12-byte header + 5 refs + colour byte + padding) vs HashMap.Node (32 bytes)](../diagrams/D-110-entry-vs-node-layout.svg)

The two layouts stacked side by side make the shape of the difference
obvious: `TreeMap.Entry` has two extra structural fields relative to
`HashMap.Node` — `left`/`right`/`parent` (three references, needed for tree
navigation) against `HashMap.Node`'s single `next` (one reference, needed for
bucket chaining) — plus the `color` byte with no `HashMap` counterpart at
all. The padding block in each layout is the same mechanical consequence of
8-byte alignment, not an independent cost either class controls.

### Example — the calculation, not a benchmark

```
TreeMap.Entry<K,V>:  12 (header) + 4*5 (key,value,left,right,parent) + 1 (color)
                   = 12 + 20 + 1 = 33  -> aligned to 40   (7 bytes padding)

HashMap.Node<K,V>:   12 (header) + 4   (hash)            + 4*3 (key,value,next)
                   = 12 + 4 + 12       = 28  -> aligned to 32   (4 bytes padding)

Surcharge: 40 / 32 = 1.25  ->  TreeMap.Entry costs 25% more per entry, before
counting the key and value objects themselves (identical in both maps) and
before counting any per-operation CPU overhead.
```

At one million entries, `40 − 32 = 8` bytes × 1,000,000 = roughly 7.6 MiB of
pure per-entry overhead attributable to the extra `parent` reference and
`color` byte (plus the padding each layout separately rounds up to) — on top
of whatever the keys and values themselves cost, which is identical between
the two maps.

### The gotcha

**Pitfall:** assuming a `TreeMap` costs the same per entry as a `HashMap`
because "they're both just maps holding the same key/value pairs." They
aren't the same cost — 40 bytes versus 32 bytes per entry is a flat 25%
surcharge, and that's *before* the larger constant-factor cost of every
lookup and insertion doing comparator calls and rotation bookkeeping instead
of a single hash-and-probe. Sizing a `TreeMap`-backed cache using
`HashMap`-derived capacity-planning numbers will under-provision by a
quarter on entry overhead alone, and that's the smaller of the two costs
being underestimated.

**Interview:** "does `TreeMap` use more memory per entry than `HashMap`, and
if so, why?" is testing whether the candidate can name the specific field
(`parent`, plus the `color` bit) responsible, not just recite "trees use more
memory than hash tables" as folklore.

> **Definition — per-entry memory overhead:** the object-layout cost of
> holding one key/value pair, exclusive of the key and value objects
> themselves. For `TreeMap.Entry`, on 64-bit HotSpot with compressed oops,
> that cost is 40 bytes (12-byte header + 5 compressed references + 1
> `color` byte, rounded up to an 8-byte boundary). For `HashMap.Node` under
> the same JVM settings, it is 32 bytes (12-byte header + 4-byte `hash` +
> 3 compressed references, rounded up to an 8-byte boundary) — a 25%
> surcharge for `TreeMap`, paid for the `parent` pointer and `color` bit
> that red-black balancing requires and hash chaining does not.

## Pitfalls

| Wrong belief | Why people believe it | Reality |
|---|---|---|
| A submap `put` outside the range is silently ignored | Some collection views (e.g., unmodifiable wrappers) fail quietly in ad hoc code, so developers generalize "out of range = no-op" | It throws `IllegalArgumentException` unconditionally — every out-of-range mutator call fails loudly |
| A submap's window auto-expands to fit an inserted key | `ArrayList`/`HashMap` grow to fit new data, so "collections just grow" feels like a universal rule | The bounds are fixed at the moment the view was created; only `clone`-style re-creation with new bounds changes them |
| `submap.size()` is O(1) like `map.size()` | `TreeMap.size()` is a cached field, and callers assume all `Map.size()` calls share that property | `submap.size()` walks the range every call — no cached count exists for a view whose in-range set shifts with the parent |
| `TreeMap` and `HashMap` cost the same per entry | Both are "just maps holding key/value pairs" from the API surface | `TreeMap.Entry` is 40 bytes, `HashMap.Node` is 32 bytes — a fixed 25% surcharge from the `parent` pointer and `color` bit |
| The 40/32 byte figures were measured with a profiler in this note | Benchmarked-sounding numbers are often assumed to come from instrumentation | They are calculated field-by-field from HotSpot's known header/reference/alignment rules — plain Java has no API to measure a single object's size directly |

## Cheat sheet

| Aspect | `NavigableSubMap` views (§3.8.16) | Entry memory (§3.8.17) |
|---|---|---|
| What it is | Shared-tree window with bounds + inclusive flags | Per-entry object layout cost |
| Core mechanism | `tooLow`/`tooHigh`/`inRange`, checked before every mutator/accessor | Field layout: header + refs + flags, aligned to 8 bytes |
| Base class | `NavigableSubMap` (abstract, package-private) | `TreeMap.Entry` vs `HashMap.Node` |
| Concrete forms | `AscendingSubMap`, `DescendingSubMap` | N/A |
| Out-of-range write | `IllegalArgumentException`, every time | N/A |
| `size()` cost | O(k) — not cached | N/A |
| Memory cost | N/A | 40 bytes (`TreeMap`) vs 32 bytes (`HashMap`) — 25% surcharge |
| Extra fields responsible | N/A | `parent` reference + `color` byte |
| Use when | Windowed, live access to a range | Choosing map type under memory pressure |
| Avoid when | Need an independent snapshot | Ordering/range queries are required regardless of memory cost |

## Self-test

1. **Q: What does `map.subMap(20, 50).put(60, v)` do, and why?**
   A: It throws `IllegalArgumentException`. `AscendingSubMap.put` calls
   `inRange(60)` before delegating to the parent's `put`; 60 fails both
   `tooLow` (false, since 60 ≥ 20) and `tooHigh` (true, since 60 ≥ 50 and the
   upper bound is exclusive), so `inRange` returns false and the mutator
   rejects the call before it ever reaches the parent tree.

2. **Q: Does a submap own its own set of `Entry` objects?**
   A: No. It shares the parent `TreeMap`'s tree entirely; the view is
   nothing but a `TreeMap` reference plus bounds plus the `inRange` checks.
   There is exactly one tree and one set of `Entry` objects, regardless of
   how many submap views exist over it.

3. **Q: Why is `submap.size()` more expensive than `map.size()`?**
   A: `TreeMap.size()` reads an incrementally maintained field, O(1). A
   submap has no such field — the count of entries currently inside its
   bounds changes every time the parent tree's structure changes, so there
   is nothing stable to cache; `submap.size()` walks the range and counts,
   O(k).

4. **Q: What distinguishes `AscendingSubMap` from `DescendingSubMap`?**
   A: Not the bounds logic — both inherit `tooLow`/`tooHigh`/`inRange`
   unchanged from `NavigableSubMap`. They differ in iteration direction and
   in which end of the range resolves to `firstKey()`/`lastKey()`.

5. **Q: Compute `TreeMap.Entry`'s size on 64-bit HotSpot with compressed
   oops, showing the arithmetic.**
   A: 12 (header) + 4×5 (key, value, left, right, parent) + 1 (color) =
   12 + 20 + 1 = 33, rounded up to the next multiple of 8 = 40 bytes.

6. **Q: Compute `HashMap.Node`'s size the same way.**
   A: 12 (header) + 4 (hash) + 4×3 (key, value, next) = 12 + 4 + 12 = 28,
   rounded up to the next multiple of 8 = 32 bytes.

7. **Q: What is the exact percentage surcharge `TreeMap.Entry` pays over
   `HashMap.Node`, and which two fields are responsible?**
   A: 40 / 32 = 1.25, a 25% surcharge, attributable to the `parent`
   reference (4 bytes) and the `color` boolean (1 byte) — fields `HashMap`
   has no equivalent for, since hash chaining needs only a single `next`
   pointer and no balance-colour bit.

8. **Q: Why can't `Runtime.totalMemory()` be used to verify the 40-vs-32
   figures directly?**
   A: It reports heap-wide totals, contaminated by GC state, JIT-compiled
   code, and every other live object on the heap; it cannot isolate the
   retained size of a single object. The only way to get a trustworthy
   per-object number in plain Java is to apply HotSpot's known layout rules
   field-by-field, as done above (or use a dedicated instrumentation tool
   such as JOL outside plain Java).

9. **Q: If memory were the only consideration, when would `TreeMap` still
   be justified over `HashMap`?**
   A: Rarely on memory grounds alone — the 25% surcharge is a real, fixed
   cost with no memory-side compensation. `TreeMap` is justified when
   ordering, range queries, or floor/ceiling-style navigation are actually
   needed; the memory surcharge is accepted as a smaller side effect of that
   requirement, not chosen for its own sake.

10. **Q: True or false: inserting through a submap uses a different
    insertion algorithm than inserting directly into the parent `TreeMap`.**
    A: False. The submap's `put` performs exactly one extra step — the
    `inRange` check — and then calls the parent's ordinary `put`. There is
    no separate insertion algorithm for submap writes.

---

**Leaves covered:** 3.8.16, 3.8.17 (2 leaves)
**Leaves deferred:** none
**Diagrams included:** D-37, D-110
**Target version:** Java 21 LTS
**Lines:** 483
