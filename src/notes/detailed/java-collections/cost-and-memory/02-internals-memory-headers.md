# 02 Java Collections — Cost and memory — INTERNALS (§3.15.1–3.15.12 Memory footprint arithmetic: headers, boxing, node sizes)

**Target version: Java 21 LTS.** | [Index](../00-index.md)
Previous: [cost-and-memory/01-master-cost-table.md](01-master-cost-table.md) · Next: [cost-and-memory/03-internals-memory-collections.md](03-internals-memory-collections.md)

Every byte figure in this file is arithmetic, not folklore — it falls straight out of the object header size, the reference width, and the alignment quantum the JVM is running with, and it moves the instant any of those three change; the goal here is to teach you the arithmetic so you can re-derive any number for any flag combination, not to memorize a table of constants that stops being true on the next JVM you deploy to.

## Hierarchy before details

Every byte figure below assumes this exact baseline. Change any one flag and every downstream figure in this file shifts — the table tells you which way.

| Assumption | Default value (Java 21, heap < 32 GB, 64-bit JVM) | Controlling flag | If it changes |
|---|---|---|---|
| Object header (mark word + class word) | 12 bytes | `-XX:+UseCompressedClassPointers` (on by default) | Off → 16-byte header (8 mark + 8 class); every object grows by 4 B |
| Compressed ordinary object pointers (oops) | on, 4-byte references | `-XX:+UseCompressedOops`, auto-disabled above the heap cliff (§3.15.4) | Off, or heap over the cliff → 8-byte references; every reference-holding field doubles |
| Object alignment quantum | 8 bytes | `-XX:ObjectAlignmentInBytes` (power of two, 8–256) | Larger alignment rounds more objects up further, and raises the compressed-oops heap cliff (§3.15.4) |
| Compact object headers | off (JDK 21 does not have the feature) | `-XX:+UseCompactObjectHeaders` (JDK 24 experimental, JDK 25 product via JEP 519) | On, JDK 25+ → 8-byte header instead of 12; every object shrinks by 4 B, sometimes 8 after alignment absorbs it |

**Insight:** three numbers — 12, 4, 8 — reconstruct almost every figure in this file. Object header 12, reference width 4, alignment quantum 8. `-XX:+UseCompactObjectHeaders` (JEP 519, product in JDK 25) turns the first number into 8; watch for it — teams that benchmark memory on JDK 25 and extrapolate to a JDK 21 production fleet will see numbers that do not reproduce.

## 3.15.1 Object header: mark word + compressed class word `[NUM]` `[SOURCE]` `[RESEARCH]`

Picture a plain `Object` with zero fields. It still occupies memory — 12 bytes of it, before a single field is stored. The mark word is 8 bytes and carries identity hash code, GC age bits, and the biased/thin/fat lock state; the class word is a compressed pointer to the `Klass` metadata for the object's type, 4 bytes when `-XX:+UseCompressedClassPointers` is on (the default). 8 + 4 = 12 bytes of pure bookkeeping before any payload.

Without compressed class pointers (rare, forced when class metadata exceeds what a 32-bit compressed pointer can address, e.g. very large `-XX:CompressedClassSpaceSize`), the class word widens to 8 bytes and the header becomes 16 bytes.

**Gotcha:** an empty `Object` therefore rounds to 16 bytes, not 12 — 12 is not itself 8-byte aligned, so the JVM pads it to the next multiple of 8. You never observe a bare 12-byte object on the heap; you observe 16.

**Unverified:** the mark word's exact bit layout differs slightly between HotSpot lock-mode revisions (biased locking was removed in JDK 15+, changing bit assignments) — treat "8 bytes, opaque bit-packed" as the stable fact and the internal bit map as implementation detail that has moved before and can move again.

> The object header is the price of admission for every Java object: 12 bytes of mark word and class word before the first field, rounded to 16 on an otherwise-empty object.

## 3.15.2 Array header = object header + 4-byte length `[NUM]` `[RESEARCH]`

An array is an object that also needs to know how many elements it holds, so its header carries one more 4-byte int than a plain object's: 12 (mark + class) + 4 (length) = 16 bytes, and 16 is already 8-byte aligned, so no padding is added before the element data begins.

**Gotcha:** this 16-byte figure is why `new int[0]` is not free — it is a real 16-byte allocation holding zero elements, and every `ArrayList`, `HashMap` bucket table, and `StringBuilder` backing array pays this fixed cost regardless of how many slots it holds.

> An array's header is the object header plus a 4-byte length field, 16 bytes total, before any element storage.

## 3.15.3 8-byte object alignment `[NUM]`

Every object's total size — header plus fields plus any array payload — is rounded up to the nearest multiple of the alignment quantum, 8 bytes by default. This is why an object that is logically "13 bytes" of header-plus-field never appears at that size; it appears at 16.

`-XX:ObjectAlignmentInBytes` can raise this to 16, 32, up to 256 (must be a power of two); doing so wastes more padding per object on average but extends how much heap compressed oops can address (§3.15.4) — the trade-off is memory density per object against memory density per reference.

**Gotcha:** rounding is per-object, not per-field — you cannot "save" the padding by packing more objects together; each object independently rounds up, so many small objects compound the waste far worse than one large object does.

> Every object's footprint is rounded up to the nearest multiple of the alignment quantum (8 bytes by default), independently, per object.

## 3.15.4 Compressed oops: 4-byte references below the heap cliff `[NUM]` `[X-REF 06]`

**Mental model.** A 64-bit JVM has 64-bit addresses, so a naive reference would cost 8 bytes everywhere — in every object field, every array slot, every `HashMap.Node`. Compressed oops instead store a reference as a 32-bit *offset from the heap base, scaled by the alignment quantum* — since every object address is a multiple of 8 (the alignment), the low 3 bits of any address are always zero, so you can shift them off, store only the remaining bits in 32 bits, and shift back on dereference. This is the same trick as storing a file offset in disk blocks instead of bytes.

**Why it exists.** 8-byte references on every object field would inflate reference-heavy structures (every collection is reference-heavy) by roughly 30–50% for no correctness benefit on any heap that fits in 32 bits' worth of addressable, alignment-scaled space. Sun/Oracle shipped this as a default-on optimization starting in JDK 6u23 / JDK 7.

**When to reach for it, and when not.** You do not "reach for" compressed oops — it is on by default and you actively disable it (`-XX:-UseCompressedOops`) only when a heap must exceed the cliff. The decision is really about heap sizing: stay under the cliff if you can, because compressed oops are a straightforward win with no downside below it.

**How it works.** With the default 8-byte alignment, a 32-bit compressed reference can address 2^32 distinct 8-byte-aligned slots = 2^32 × 8 bytes = 2^35 bytes = 32 GiB of heap. Raise `-XX:ObjectAlignmentInBytes` to 16 and the same 32 bits address 2^32 × 16 = 64 GiB; the addressable heap under compression scales linearly with the alignment quantum. This is the real relationship the leaf asks you to get right: **the cliff is not a fixed 32 GB, it is `2^32 × ObjectAlignmentInBytes`**, and 32 GB is only the figure at the *default* 8-byte alignment.

Cross the addressable limit for the current alignment (or explicitly disable the flag) and the JVM falls back to full 8-byte references everywhere. This produces the well-known "cliff": a heap configured at, say, 34 GB can hold *fewer* effective objects than one configured at 31 GB, because every reference in every object doubled in size the moment compression turned off — you paid more RAM to get less usable heap. Practitioners generally avoid the 32–48 GB range entirely: below 32 GB you get compression, above roughly 48 GB the doubled reference overhead is dwarfed by heap sizeso it is worth it again, and the range in between takes the compression loss without the size to justify it.

![Object and array header layout: 12-byte header (8 mark + 4 class) plus 8-byte alignment padding; Integer at 16 B and Long at 24 B laid out field by field; the shift to 8-byte header under -XX:+UseCompactObjectHeaders and how it moves every downstream figure](../diagrams/D-137-object-array-header-layout.svg)

**Example.**
```java
public final class CompressedOopsMath {

    private static final long DEFAULT_ALIGNMENT_BYTES = 8L;

    public static long addressableHeapBytes(long alignmentBytes) {
        // 32-bit compressed reference * alignment quantum = addressable span
        return (1L << 32) * alignmentBytes;
    }

    public static void main(String[] args) {
        long defaultCliffBytes = addressableHeapBytes(DEFAULT_ALIGNMENT_BYTES);
        long doubledAlignmentCliffBytes = addressableHeapBytes(16L);
        System.out.printf(
            "Default (8-byte align) cliff: %d GiB%n",
            defaultCliffBytes / (1L << 30));
        System.out.printf(
            "16-byte align cliff: %d GiB%n",
            doubledAlignmentCliffBytes / (1L << 30));
    }
}
```

**Gotcha:** the cliff is a function of `ObjectAlignmentInBytes`, not a hardcoded JVM constant — teams that raise object alignment for other reasons (rare, but done to reduce false sharing) silently move their own cliff and often do not realize it.

**Escape hatch:** if you must exceed the cliff, raising `-XX:ObjectAlignmentInBytes` before raising `-XX:-UseCompressedOops` outright keeps references at 4 bytes for a larger heap, at the cost of more padding waste per small object — the right choice depends on whether your workload is dominated by many small objects (padding-sensitive) or reference density (compression-sensitive).

> Compressed oops store references as 32-bit offsets scaled by the alignment quantum, addressing `2^32 × ObjectAlignmentInBytes` bytes of heap — 32 GiB at the 8-byte default — beyond which the JVM falls back to full 8-byte references.

## 3.15.5 `Integer` = 16 bytes, `Long` = 24 bytes `[NUM]` `[RESEARCH]`

**Mental model.** Picture the boxed wrapper as a 12-byte header wrapped around a single primitive field, then rounded to alignment — the box is mostly box.

**Why it exists.** Java's generics erase to `Object`, so every generic collection (`List<Integer>`, `Map<K,Integer>`) needs a heap object to stand in for a primitive; boxing is the mechanism, and its cost is this arithmetic.

**When to reach for it, and when not.** You do not choose boxing directly in generic collection code — the compiler inserts it — but you choose it indirectly every time you pick `ArrayList<Integer>` over `int[]` or a primitive-specialized structure.

**How it works.**
`Integer`: 12-byte header + 4-byte `int value` field = 16 bytes exactly, already aligned, no padding needed.
`Long`: 12-byte header + 8-byte `long value` field. The 8-byte `long` field needs to start at an 8-byte-aligned offset, but the header is only 12 bytes, so the JVM inserts 4 bytes of padding before the field: 12 + 4 (pad) + 8 (value) = 24 bytes.

**Example.**
```java
import java.lang.reflect.Field;

public final class BoxedSizeMath {

    public static long integerBytes() {
        // header(12) + int field(4) = 16, already 8-aligned
        return 12L + 4L;
    }

    public static long longBytes() {
        // header(12) + padding(4) to align the 8-byte field + long field(8) = 24
        return 12L + 4L + 8L;
    }

    public static void main(String[] args) {
        System.out.println("Integer: " + integerBytes() + " bytes");
        System.out.println("Long: " + longBytes() + " bytes");
    }
}
```

**Gotcha:** `Integer` looks like it should be cheaper than `Long` by 4 bytes (the field-size difference) but is actually cheaper by 8, because `Long`'s field alignment forces an extra 4 bytes of padding that `Integer` never needs — the field-alignment tax is invisible until you work the arithmetic.

**Escape hatch:** primitive arrays (`int[]`, `long[]`) or a library like Eclipse Collections / fastutil's primitive-specialized maps and lists avoid the per-element header entirely, at the cost of losing `null`, generics interop, and boxed-object identity semantics. See `../contracts/04-generics-and-boxing.md` for the `Integer` cache (`-128..127`) and where the boxing blow-up compounds across a whole collection.

> A boxed `Integer` costs 16 bytes (12-byte header + 4-byte value, no padding); a boxed `Long` costs 24 bytes (12-byte header + 4-byte alignment padding + 8-byte value) — not the 4-byte difference the field sizes alone would suggest.

## 3.15.6 `int[1_000_000]` ≈ 4.0 MB `[NUM]` `[PROVE]`

Work it step by step: array header is 16 bytes (§3.15.2), then 1,000,000 elements at 4 bytes each (primitive `int`, no boxing, no per-element header — this is the whole point of primitive arrays) = 4,000,000 bytes of payload. Total = 16 + 4,000,000 = 4,000,016 bytes, which rounds to the next multiple of 8 → 4,000,016 is already a multiple of 8, so no further padding. In round terms, ≈ 4.0 MB (mebibyte-ish; strictly 4,000,016 / 1,048,576 ≈ 3.81 MiB, but engineers commonly say "4 MB" loosely against 4,000,000 decimal bytes — be precise about which base you're quoting).

**Gotcha:** this is the *entire* cost — no per-element overhead exists for a primitive array, which is exactly why it is the escape hatch cited throughout this file.

> A million-element `int[]` costs its 16-byte array header plus 4 bytes per element, ≈ 3.81 MiB (4,000,016 bytes) — flat, with zero per-element overhead.

## 3.15.7 `ArrayList<Integer>` with 1,000,000 entries ≈ 20 MB, a 5× blow-up `[NUM]` `[PROVE]`

Work it step by step, building on §3.15.6 and §3.15.5:

1. `ArrayList` object itself: header (16, an empty-ish small object) + `size` field (4) + `elementData` reference field (4, compressed) + `modCount` field inherited from `AbstractList` (4) ≈ 16 + 4 + 4 + 4 = 28, rounds to 24 or 32 depending on exact field layout — take 24 bytes as the commonly measured JOL figure for the list shell itself.
2. Backing `Object[]` array holding 1,000,000 compressed references: array header (16) + 1,000,000 × 4-byte references = 16 + 4,000,000 = 4,000,016 bytes.
3. 1,000,000 boxed `Integer` objects at 16 bytes each (§3.15.5) = 16,000,000 bytes.

Total ≈ 24 + 4,000,016 + 16,000,000 = 20,000,040 bytes ≈ 19.07 MiB, call it ~20 MB.

Compare to the primitive `int[1_000_000]` at ≈ 4.0 MB (§3.15.6): `20,000,040 / 4,000,016 ≈ 5.0×`. The blow-up is not from the `ArrayList` shell (negligible) or even the reference array (same order of magnitude as the primitive array) — it is almost entirely the 1,000,000 individual 16-byte `Integer` boxes, which is 16 MB of the 20 MB total, 80% of the footprint, for data that a primitive array stores as pure payload.

**Escape hatch:** an `IntArrayList` (Eclipse Collections, fastutil, Trove) stores primitives directly and reproduces the ≈4 MB figure while still offering list-like operations — at the cost of losing generic `List<Integer>` interop and needing library-specific APIs at call sites. See `../contracts/04-generics-and-boxing.md`.

> A million-entry `ArrayList<Integer>` costs ≈ 20 MB against a primitive `int[]`'s ≈ 4 MB for the same data — a 5× blow-up driven almost entirely by 1,000,000 individually-boxed 16-byte `Integer` objects.

## 3.15.8 `ArrayList` capacity slack: ~25% average waste `[NUM]` `[PROVE]`

`ArrayList` grows by 1.5× when it fills (`newCapacity = oldCapacity + (oldCapacity >> 1)`, see `../array-list/01-internals-a-growth.md` for the full growth sequence and its `Arrays.copyOf` cost). Consider a list that has just triggered growth: capacity was `C`, is now `1.5C`, and the list is holding somewhere between `C+1` and `1.5C` live elements before it grows again. Averaged uniformly across that range, the expected number of allocated-but-unused slots is `(1.5C - C) / 2 = 0.25C` — a quarter of the *pre-growth* capacity, or equivalently the list is, on average, running at about 1/1.25 ≈ 80% utilization, i.e. ~25% of its allocated backing-array capacity is unused slack, if it is never explicitly shrunk.

**Escape hatch:** call `trimToSize()` once the list's final size is known and it will not grow further; the cost is an `Arrays.copyOf` at trim time and the loss of headroom for any future `add` (which forces an immediate reallocation instead of amortized growth).

> An `ArrayList` that is never `trimToSize()`d runs, on average, about 25% over its live-element footprint in unused backing-array capacity, a direct consequence of 1.5× growth.

## 3.15.9–3.15.12 The node-size ladder: `Node` → `TreeNode`

These four leaves are siblings describing the same field-by-field construction applied to progressively richer node types — exactly the kind of 3+-sibling set that belongs in one table, not four separate paragraphs.

| Type | Fields beyond header | Field-by-field bytes | Raw total | Aligned total |
|---|---|---|---|---|
| `HashMap.Node` | `int hash`(4) + `K key`(4) + `V value`(4) + `Node<K,V> next`(4) | 12 + 4+4+4+4 = 28 | 28 | **32** |
| `LinkedHashMap.Entry` | `Node` fields + `Entry<K,V> before`(4) + `Entry<K,V> after`(4) | 32 (aligned Node) + 4+4 = 40 | 40 | **40** |
| `HashMap.TreeNode` | `LinkedHashMap.Entry` fields + `TreeNode<K,V> parent`(4) + `left`(4) + `right`(4) + `prev`(4) + `boolean red`(1) | 40 + 4+4+4+4+1 = 57 | 57 | **56 or 64**\* |

\* `boolean` occupies a full byte in the JVM's field layout but the JVM packs it against existing padding where it can; JOL measurements on Java 21 commonly report 56 bytes for `TreeNode` (the `red` boolean fits inside otherwise-wasted alignment slack) rather than the naively-summed 57 rounded to 64 — this is the one figure in this ladder where field-layout packing (HotSpot reorders fields to minimize padding) beats a purely additive calculation, so treat 56 as the reliably-measured figure and verify with JOL if you need certainty on a specific JVM build.

## 3.15.9 `HashMap.Node` = 32 bytes `[NUM]` `[PROVE]`

Quote the real field declaration (`java.util.HashMap`, Java 21 source):

```java
static class Node<K,V> implements Map.Entry<K,V> {
    final int hash;
    final K key;
    V value;
    Node<K,V> next;
    // constructor and accessor methods omitted from this excerpt only —
    // no other member of the class is elided
}
```

Work the arithmetic: 12-byte object header + 4-byte `int hash` + 4-byte `K key` reference (compressed) + 4-byte `V value` reference (compressed) + 4-byte `Node next` reference (compressed) = 12 + 4 + 4 + 4 + 4 = 28 bytes raw, rounded up to the next multiple of 8 = **32 bytes**.

**Gotcha:** this is the cost of *one bucket entry's plumbing*, before the key and value objects it points to are counted at all — those are separate heap allocations, sized separately (§3.15.10).

> `HashMap.Node` costs 32 bytes: a 12-byte header plus four 4-byte fields (hash, key ref, value ref, next ref), 28 bytes raw rounded to 32.

## 3.15.10 `HashMap<Integer,Integer>` per entry ≈ 69 bytes for 8 bytes of data `[NUM]` `[PROVE]`

**Mental model.** Look at one key-value pair sitting in a `HashMap<Integer,Integer>` and ask: how much of what's actually allocated is the two `int`s you meant to store, versus the machinery around them?

**Why it exists.** A hash map needs the `Node` to link key, value, and collision chain; it needs the key and value themselves as separate objects because generics erase to references, not primitives; and it needs an amortized share of the bucket-table array itself, which is sized larger than the entry count to keep collision chains short.

**When to reach for it, and when not.** Reach for `HashMap<Integer,Integer>` when the API surface (arbitrary key types, null handling, `Map` interface) is worth the overhead; reach for a primitive-specialized map (fastutil's `Int2IntOpenHashMap`, Eclipse Collections' `IntIntHashMap`) when you are storing millions of int-to-int pairs and the 8.6× multiplier below is a real memory-budget problem, not a rounding error.

**How it works — the four components, worked step by step:**

1. **`Node`**: 32 bytes (§3.15.9).
2. **Key `Integer`**: 16 bytes (§3.15.5).
3. **Value `Integer`**: 16 bytes (§3.15.5).
4. **Amortized table-slot share**: `HashMap`'s backing `Node[]` table is resized to keep load factor ≤ 0.75 (default), meaning the table has roughly `entryCount / 0.75 ≈ 1.33 × entryCount` slots for `entryCount` entries. Each slot is one compressed reference, 4 bytes. Amortized per entry: `4 bytes × (1 / 0.75) = 4 × 1.3333 ≈ 5.33 bytes`.

Sum: 32 + 16 + 16 + 5.33 ≈ **69.3 bytes**, commonly rounded to "69 bytes."

Of that 69 bytes, the actual `int` data being stored is 4 (key's int value) + 4 (value's int value) = 8 bytes. Ratio: `69.3 / 8 ≈ 8.66×` — engineers commonly round this to "~8.6×" or loosely "~69 bytes to store 8."

![69 bytes to store 8: one HashMap<Integer,Integer> entry decomposed into 32 B Node + 16 B key Integer + 16 B value Integer + ~5.3 B amortised table slot at load factor 0.75, with the 8 actual data bytes highlighted inside the total and the ~8.6× ratio called out](../diagrams/D-138-69-bytes-to-store-8.svg)

**Example.**
```java
public final class HashMapEntryOverheadMath {

    private static final int NODE_BYTES = 32;
    private static final int BOXED_INTEGER_BYTES = 16;
    private static final double LOAD_FACTOR = 0.75;
    private static final int TABLE_SLOT_BYTES = 4;

    public static double amortizedTableSlotBytes() {
        return TABLE_SLOT_BYTES / LOAD_FACTOR;
    }

    public static double perEntryOverheadBytes() {
        return NODE_BYTES
            + BOXED_INTEGER_BYTES  // key
            + BOXED_INTEGER_BYTES  // value
            + amortizedTableSlotBytes();
    }

    public static void main(String[] args) {
        double overhead = perEntryOverheadBytes();
        int actualDataBytes = 8; // two raw ints
        System.out.printf("Per-entry overhead: %.2f bytes%n", overhead);
        System.out.printf("Ratio to actual data: %.2fx%n", overhead / actualDataBytes);
    }
}
```

**Gotcha:** the 5.33-byte table-slot figure is an *average*, not a per-entry constant — a table that just resized and is sparsely filled costs more per live entry than this average; a table right before its next resize costs closer to the raw 4 bytes.

**Escape hatch:** primitive-specialized maps (fastutil `Int2IntOpenHashMap`, Eclipse Collections `IntIntHashMap`) store keys and values as parallel primitive arrays with open addressing, eliminating `Node`, both boxed `Integer`s, and the reference-width table slot — typical overhead drops to single-digit bytes per entry — at the cost of losing `Map<Integer,Integer>` interface compatibility and `null` key/value support.

> A `HashMap<Integer,Integer>` entry costs approximately 69 bytes (32-byte `Node` + 16-byte key + 16-byte value + ~5.3-byte amortized table slot) to store 8 bytes of actual `int` data — roughly an 8.6× overhead multiplier.

## 3.15.11 `LinkedHashMap.Entry` = 40 bytes `[NUM]`

`LinkedHashMap.Entry<K,V>` extends `HashMap.Node<K,V>` and adds two more reference fields to maintain the insertion/access-order doubly-linked list:

```java
static class Entry<K,V> extends HashMap.Node<K,V> {
    Entry<K,V> before, after;
    Entry(int hash, K key, V value, Node<K,V> next) {
        super(hash, key, value, next);
    }
}
```

Arithmetic: 32-byte aligned `Node` base + 4-byte `before` reference + 4-byte `after` reference = 32 + 4 + 4 = 40 bytes, already 8-aligned, no further padding.

**Gotcha:** this 40-byte figure is *per entry*, on top of the same amortized table-slot share computed in §3.15.10 — `LinkedHashMap`'s total per-entry overhead is therefore higher than plain `HashMap`'s by exactly these 8 bytes, for the ordering guarantee.

> `LinkedHashMap.Entry` costs 40 bytes: the 32-byte `HashMap.Node` base plus two 4-byte `before`/`after` references for the ordering linked list.

## 3.15.12 `HashMap.TreeNode` = 56 bytes; treeified bins cost memory `[NUM]` `[PROVE]`

**Mental model.** Once a single bucket's collision chain grows past the treeify threshold (8 entries, and the table has at least 64 buckets — see `../hash-map/04-internals-d-treeify.md` for the exact trigger and the full inheritance chain), `HashMap` converts that bucket's linked list into a small red-black tree to bound worst-case lookup at O(log n) instead of O(n). Each node in that tree needs to be a `TreeNode`, which is a *strictly heavier* object than the `Node` it replaces.

**Why it exists.** A pathological hash collision attack (many keys hashing into one bucket) turns a hash map's O(1) average lookup into O(n) worst case; the tree structure caps the damage, at a fixed memory cost per treeified node.

**When to reach for it, and when not.** You do not opt into this — `HashMap` treeifies automatically. What you control is whether you get there at all: a well-distributed `hashCode()` and adequate initial capacity keep bins short and treeification rare. If you are seeing frequent treeify events in profiling, that is a signal about your key's hash quality, not a feature to lean on.

**How it works.** `TreeNode<K,V>` extends `LinkedHashMap.Entry<K,V>` (yes — `HashMap.TreeNode` inherits from `LinkedHashMap.Entry`, not directly from `HashMap.Node`; see `../hash-map/04-internals-d-treeify.md` for why the JDK authors chose that inheritance chain, reusing the `before`/`after` links for `TreeNode`'s own linked-list bookkeeping during untreeify):

```java
static final class TreeNode<K,V> extends LinkedHashMap.Entry<K,V> {
    TreeNode<K,V> parent;
    TreeNode<K,V> left;
    TreeNode<K,V> right;
    TreeNode<K,V> prev;
    boolean red;
}
```

Work the arithmetic: 40-byte aligned `LinkedHashMap.Entry` base + 4-byte `parent` + 4-byte `left` + 4-byte `right` + 4-byte `prev` + 1-byte `red` = 40 + 4+4+4+4+1 = 57 bytes raw. A naive alignment rounding would push this to 64, but HotSpot's field-layout packing places the single `boolean` into padding space left over from the base class layout rather than allocating a fresh 8-byte block for it alone; JOL measurements on Java 21 report **56 bytes** as the reliably observed figure.

**Gotcha:** 56 bytes is 24 bytes — 75% — heavier than the plain 32-byte `Node` it replaces, and this cost is paid per node in the treeified bin, not once per bucket; a bucket with 12 treeified entries costs `12 × 56 = 672` bytes of node overhead alone versus `12 × 32 = 384` bytes had it stayed a linked list — treeification is a correctness and worst-case-latency safeguard, not a memory optimization.

**Escape hatch:** the real fix for frequent treeification is almost always a better `hashCode()` implementation or a larger initial capacity, not avoiding `HashMap`; if you are deliberately building adversarial-input-resistant maps at scale, that is a design decision to surface explicitly (e.g. `java.util.HashMap`'s own hash-spreading via `(h = key.hashCode()) ^ (h >>> 16)` already defends the common case, per `../hash-map/04-internals-d-treeify.md`).

> `HashMap.TreeNode` costs 56 bytes as reliably measured (57 bytes raw, absorbed by field-layout packing rather than rounding to 64) — 24 bytes heavier than the plain `Node` it replaces once a bin treeifies.

## Pitfalls

### "A `HashMap<Integer,Integer>` with a million entries takes about the same memory as an `int[2_000_000]`"

**Wrong**
```java
import java.util.HashMap;
import java.util.Map;

public final class WrongHashMapSizeAssumption {

    public static Map<Integer, Integer> buildMillionEntryMap() {
        Map<Integer, Integer> map = new HashMap<>();
        for (int i = 0; i < 1_000_000; i++) {
            map.put(i, i * 2);
            // Assumed cost: ~8 MB (like two int[1_000_000] arrays).
            // Actual cost: ~69 MB (69 bytes/entry x 1,000,000, per section 3.15.10).
        }
        return map;
    }
}
```

**Right**
```java
import java.util.HashMap;
import java.util.Map;

public final class RightHashMapSizeExpectation {

    public static Map<Integer, Integer> buildMillionEntryMapSizedUpFront() {
        // Pre-size to avoid resize-driven table churn; the per-entry
        // overhead (~69 B, section 3.15.10) is unavoidable in a plain
        // HashMap<Integer,Integer> -- if that budget matters, switch to
        // a primitive-specialized map (fastutil Int2IntOpenHashMap,
        // Eclipse Collections IntIntHashMap) instead of tuning this one.
        int expectedEntries = 1_000_000;
        int initialCapacity = (int) (expectedEntries / 0.75) + 1;
        return new HashMap<>(initialCapacity);
    }
}
```

**Why people believe it:** the mental shortcut "a map is like two arrays, one for keys and one for values" is true for the *shape* of the data but ignores that generic collections store boxed references, not primitives, and that every entry drags a `Node` and a fractional table slot along with it.

### "`-XX:+UseCompactObjectHeaders` is available and safe to flip on in our JDK 21 production fleet"

**Wrong**
```java
public final class WrongCompactHeaderAssumption {

    public static String jvmFlagToTry() {
        // Assumed: works on our JDK 21 LTS fleet today.
        // Actual: the flag does not exist on JDK 21 at all -- it landed
        // experimental in JDK 24 (JEP 450) and became a JDK 25 product
        // feature (JEP 519). Setting it on JDK 21 is simply ignored/unrecognized.
        return "-XX:+UseCompactObjectHeaders";
    }
}
```

**Right**
```java
public final class RightCompactHeaderPlanning {

    public static String jvmVersionRequirementNote() {
        return "UseCompactObjectHeaders requires JDK 24 (experimental, "
            + "needs -XX:+UnlockExperimentalVMOptions) or JDK 25+ (product, "
            + "JEP 519). On JDK 21 LTS, plan the 12-byte header baseline "
            + "from section 3.15.1 as the figure that applies; treat the "
            + "8-byte header as a future-JDK migration benefit, not a "
            + "current one.";
    }
}
```

**Why people believe it:** JVM flags are usually forward-compatible in spirit, so engineers assume a memory-saving flag they read about applies to whatever JDK LTS they are already running, without checking which JEP shipped it and on which release.

### "Boxed `Integer` and `Long` differ in size by exactly their primitive-field size difference (4 bytes)"

**Wrong**
```java
public final class WrongBoxedSizeDelta {

    public static int assumedDeltaBytes() {
        // Assumed: Long is 4 bytes bigger than Integer (8-byte long field
        // vs 4-byte int field). Actual delta is 8 bytes, not 4 -- see
        // section 3.15.5: Long needs 4 bytes of alignment padding that
        // Integer does not.
        return 4;
    }
}
```

**Right**
```java
public final class RightBoxedSizeDelta {

    public static int actualDeltaBytes() {
        int integerBytes = 16; // 12 header + 4 int field
        int longBytes = 24;    // 12 header + 4 padding + 8 long field
        return longBytes - integerBytes; // 8, not 4
    }
}
```

**Why people believe it:** it is natural to reason field-size-to-field-size and forget that alignment padding is itself a function of field size — a wider field can force padding that a narrower field never needed.

## Cheat sheet

| Object | Bytes | Arithmetic |
|---|---|---|
| Empty `Object` | 16 | 12 header, rounded to 16 |
| Array header (any type) | 16 | 12 header + 4 length |
| `Integer` | 16 | 12 header + 4 int, no padding |
| `Long` | 24 | 12 header + 4 pad + 8 long |
| `int[1_000_000]` | ~4.0 MB (4,000,016 B) | 16 + 1,000,000×4 |
| `ArrayList<Integer>` × 1,000,000 | ~20 MB | shell + ref array + 1,000,000×16 B `Integer` |
| `ArrayList` average slack (never trimmed) | ~25% of live footprint | (1.5C − C)/2 over pre-growth C |
| `HashMap.Node` | 32 | 12 + hash(4) + key ref(4) + value ref(4) + next ref(4) = 28 → 32 |
| `HashMap<Integer,Integer>` entry (amortized) | ~69 | 32 (Node) + 16 (key) + 16 (value) + ~5.33 (table slot / 0.75) |
| `LinkedHashMap.Entry` | 40 | 32 (Node) + before(4) + after(4) |
| `HashMap.TreeNode` | 56 | 57 raw (40 + parent/left/right/prev + red), packed to 56 |

| Flag | Effect on the baseline |
|---|---|
| `-XX:-UseCompressedClassPointers` | Header 12 → 16 bytes |
| `-XX:-UseCompressedOops` (or heap over the cliff) | Every reference 4 → 8 bytes |
| `-XX:ObjectAlignmentInBytes=N` | Rounding quantum 8 → N; compressed-oops cliff scales to `2^32 × N` |
| `-XX:+UseCompactObjectHeaders` (JDK 24 experimental / JDK 25 product) | Header 12 → 8 bytes |

## Self-test

**Q1.** Why does an empty `Object` measure 16 bytes on the heap instead of the 12-byte header figure quoted in section 3.15.1?

<details><summary>Answer</summary>

The 12-byte header (8-byte mark word + 4-byte compressed class word) is not itself a multiple of the 8-byte object alignment quantum, so the JVM pads it up to the next multiple of 8, which is 16. You never observe a bare 12-byte object; every object's total footprint is rounded to an alignment multiple.

</details>

**Q2.** State the exact relationship between the compressed-oops heap cliff and `-XX:ObjectAlignmentInBytes`, and compute the cliff at 16-byte alignment.

<details><summary>Answer</summary>

The addressable heap under compressed oops is `2^32 × ObjectAlignmentInBytes` bytes, because a 32-bit compressed reference addresses that many alignment-quantum-sized slots. At the default 8-byte alignment this is `2^32 × 8 = 2^35` bytes = 32 GiB. At 16-byte alignment it doubles to `2^32 × 16 = 2^36` bytes = 64 GiB. The cliff is not a fixed 32 GB constant — it scales linearly with the alignment quantum.

</details>

**Q3.** Work out why `Long` costs 24 bytes when its only field is 4 bytes wider than `Integer`'s.

<details><summary>Answer</summary>

`Integer` is 12 (header) + 4 (`int` field) = 16 bytes, already aligned. `Long`'s `long` field is 8 bytes and must start at an 8-byte-aligned offset; since the header is only 12 bytes, the JVM inserts 4 bytes of padding before the field: 12 + 4 (padding) + 8 (field) = 24 bytes. The delta is 8 bytes, not the 4-byte field-size difference, because the wider field forces alignment padding that the narrower field never needed.

</details>

**Q4.** Decompose the ~69-byte cost of one `HashMap<Integer,Integer>` entry into its four components and state what fraction is the actual data.

<details><summary>Answer</summary>

32 bytes (`Node`) + 16 bytes (boxed key `Integer`) + 16 bytes (boxed value `Integer`) + ~5.33 bytes (amortized table slot, `4 bytes ÷ 0.75` load factor) ≈ 69.3 bytes. The actual `int` data stored is 8 bytes (4 for the key's int value, 4 for the value's int value), so the data is roughly `8 / 69.3 ≈ 11.5%` of the total footprint — an overhead multiplier of about 8.6×.

</details>

**Q5.** Why is `HashMap.TreeNode` 56 bytes and not the 64 bytes a naive field-sum-then-round calculation would predict?

<details><summary>Answer</summary>

Summing fields gives 40 (aligned `LinkedHashMap.Entry` base) + 4+4+4+4 (parent/left/right/prev references) + 1 (`red` boolean) = 57 bytes raw, which a naive "round to next multiple of 8" would push to 64. But HotSpot's field-layout algorithm packs the single trailing `boolean` into padding space already present in the class's layout rather than allocating a fresh 8-byte block just for it, so JOL measurements on Java 21 report 56 bytes as the reliably observed figure.

</details>

**Q6.** An `ArrayList<Integer>` holding 1,000,000 elements measures roughly 20 MB. Break down where that 5× blow-up over a primitive `int[1_000_000]` (~4 MB) comes from.

<details><summary>Answer</summary>

The `ArrayList` shell itself is negligible (~24 bytes). The backing `Object[]` of 1,000,000 compressed references costs about the same as the primitive array's payload (~4,000,016 bytes). The dominant cost is 1,000,000 individually-boxed `Integer` objects at 16 bytes each = 16,000,000 bytes, which is 80% of the ~20 MB total. The blow-up is almost entirely the per-element boxing overhead, not the list or array structure.

</details>

**Q7.** What does `-XX:+UseCompactObjectHeaders` change, and on which JDK versions is it available, experimental versus product?

<details><summary>Answer</summary>

It shrinks the object header from 12 bytes to 8 bytes on 64-bit platforms, shifting every downstream header-dependent figure in this file down by up to 4 bytes (sometimes absorbed entirely by alignment). It shipped experimental in JDK 24 via JEP 450 (requires `-XX:+UnlockExperimentalVMOptions`) and became a stable product feature in JDK 25 via JEP 519. It does not exist at all on JDK 21 LTS.

</details>

**Q8.** Why does `LinkedHashMap.Entry` cost 40 bytes and not 32 + 8 = 40 via a different-looking calculation — i.e., confirm it inherits from `HashMap.Node` rather than being built independently.

<details><summary>Answer</summary>

`LinkedHashMap.Entry<K,V>` literally extends `HashMap.Node<K,V>`, adding two 4-byte reference fields (`before`, `after`) for the ordering doubly-linked list. Its size is the aligned `Node` size (32 bytes) plus those two fields: 32 + 4 + 4 = 40, which is already a multiple of 8, so no extra padding is needed. It is not computed independently from raw field sums of a flat class — it is base-plus-increment, matching the actual inheritance chain in the JDK source.

</details>

**Q9.** What is the average capacity slack of an `ArrayList` that is never `trimToSize()`d, and why is it not simply "50% at worst"?

<details><summary>Answer</summary>

On average about 25% of the allocated backing-array capacity is unused, not 50%. Growth is 1.5×: a list that has just grown from capacity `C` to `1.5C` holds somewhere between `C+1` and `1.5C` elements before the next growth. The worst case right after growth is close to `C` unused out of `1.5C` allocated (~33%), and the best case right before the next growth is near 0% unused; averaged uniformly across that range the expected slack is `(1.5C − C)/2 = 0.25C`, i.e. about 25% of the pre-growth capacity, not a flat 50%.

</details>

---

**Leaves covered:** 3.15.1–3.15.12 (12 leaves)
**Leaves deferred:** none
**Diagrams included:** D-137, D-138
**Target version:** Java 21 LTS
**Lines:** 515
