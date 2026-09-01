# 02 Java Collections — `HashMap` — INTERNALS (§3.6 `HashMap` source walk — `resize()`'s four jobs and the threshold arithmetic)

**Target version: Java 21 LTS.** | [Index](../00-index.md)
Previous: [hash-map/02b-internals-b2-bincount-and-treeifybin.md](02b-internals-b2-bincount-and-treeifybin.md) · Next: [hash-map/03a-internals-c1-lo-hi-split.md](03a-internals-c1-lo-hi-split.md)

---

## `resize()` — four jobs behind one name

### Mental model

Do not read `resize()` as "grow the table". Read it as: **"whatever state this map is in, hand me a correctly sized `Node[]` and leave `threshold` consistent with it."** That framing is the only one that survives contact with the source, because the method has four callers wanting four different things:

| Job | Triggered by | Entry state | What `resize()` does |
|---|---|---|---|
| (a) Allocate the first table | first `put` on `new HashMap<>()` | `table == null`, `threshold == 0` | `newCap = 16`, `newThr = 12` |
| (b) Allocate at a requested capacity | first `put` on `new HashMap<>(1000)` | `table == null`, `threshold == 1024` | `newCap = oldThr = 1024`, then recompute `newThr` |
| (c) Double an existing table | `++size > threshold` in `putVal` (line 631) | `table != null` | `newCap = oldCap << 1`, transfer all entries |
| (d) Relieve a long bin in a small table | `treeifyBin` (line 761) when `tab.length < 64` | `table != null` | same as (c) — spreading beats treeifying |

Jobs (a) and (b) allocate nothing to transfer. Jobs (c) and (d) run the transfer loop. That is why the whole back half of the method is guarded by `if (oldTab != null)`.

Job (b) is the *decode* half of the overloaded `threshold` field (declared at line 421) — see [`01-internals-a-constants-and-hash.md`](01-internals-a-constants-and-hash.md), which owns the encode side: `tableSizeFor` stashing the rounded-up capacity into `threshold` before any table exists. Job (d) is the `resize()` call inside `treeifyBin` — see [`02b-internals-b2-bincount-and-treeifybin.md`](02b-internals-b2-bincount-and-treeifybin.md).

This file covers the sizing half of the method. The transfer loop — the lo/hi split, why one bit decides, and order preservation — is the next file, [`03a-internals-c1-lo-hi-split.md`](03a-internals-c1-lo-hi-split.md).

### Why it exists

Java 7 split this across two methods: `resize(int newCapacity)` for the sizing decision and `transfer(Entry[], boolean)` for moving entries. Java 8 fused them into one `final Node<K,V>[] resize()` that takes no arguments and returns the new table.

The fusion is what makes the whole Java 8 rewrite possible. The transfer optimisation needs to know `oldCap`, and only the sizing half knows it; passing `newCapacity` in, as Java 7 did, threw that away. **That signature change alone — `resize(int)` + `transfer(...)` → `resize()` — is the cleanest one-line answer to "what changed in Java 8's `HashMap`?"**

### When it runs, and when it does not

It runs on `size` crossing `threshold`, and on `treeifyBin` finding a table shorter than `MIN_TREEIFY_CAPACITY`. It never runs on `remove`.

**`HashMap` never shrinks.** A map that peaks at a million entries and then has 999,999 removed still holds a `Node[2097152]` array — 8 MB of pointers on a 64-bit JVM with compressed oops, all of it null. There is no `trimToSize()`. The escape hatch is `new HashMap<>(old)` and dropping the old reference. The sibling that does the right thing here is nothing in `java.util` — you do it by hand, and if you find yourself doing it often the shape you actually want is a bounded cache (`LinkedHashMap` with `removeEldestEntry`) rather than a map you periodically rebuild.

It also does not run eagerly at construction. `new HashMap<>(1000)` allocates **no table at all** — it only records a capacity, and the first `put` calls `resize()` to do job (b):

```
after new HashMap<>(1000): table=null  threshold=1024
after first put:            table.length=1024  threshold=768
after new HashMap<>():      table=null  threshold=0
after first put:            table.length=16  threshold=12
```

(Real output, JDK 21, reading `table` and `threshold` by reflection.) Note `threshold` holding **1024** — a capacity — between construction and the first `put`, then becoming **768** — a real threshold, `(int)(1024 * 0.75f)` — once the table exists. One `int` field, two meanings, disambiguated by whether `table` is null.

### Mechanism: the capacity and threshold arithmetic

```java
    final Node<K,V>[] resize() {
        Node<K,V>[] oldTab = table;
        int oldCap = (oldTab == null) ? 0 : oldTab.length;
        int oldThr = threshold;
        int newCap, newThr = 0;
        if (oldCap > 0) {
            if (oldCap >= MAXIMUM_CAPACITY) {
                threshold = Integer.MAX_VALUE;
                return oldTab;
            }
            else if ((newCap = oldCap << 1) < MAXIMUM_CAPACITY &&
                     oldCap >= DEFAULT_INITIAL_CAPACITY)
                newThr = oldThr << 1; // double threshold
        }
        else if (oldThr > 0) // initial capacity was placed in threshold
            newCap = oldThr;
        else {               // zero initial threshold signifies using defaults
            newCap = DEFAULT_INITIAL_CAPACITY;
            newThr = (int)(DEFAULT_LOAD_FACTOR * DEFAULT_INITIAL_CAPACITY);
        }
        if (newThr == 0) {
            float ft = (float)newCap * loadFactor;
            newThr = (newCap < MAXIMUM_CAPACITY && ft < (float)MAXIMUM_CAPACITY ?
                      (int)ft : Integer.MAX_VALUE);
        }
        threshold = newThr;
        @SuppressWarnings({"rawtypes","unchecked"})
        Node<K,V>[] newTab = (Node<K,V>[])new Node[newCap];
        table = newTab;
```

— `java.base/java/util/HashMap.java`, JDK 21, lines 683–711. The method continues with the transfer loop, quoted in the next file. (leaf 3.6.23)

Line by line:

- `oldCap = (oldTab == null) ? 0 : oldTab.length` — capacity is *never* stored in a field. It is always `table.length`, and `0` stands for "no table yet". This is the branch selector for jobs (a)/(b) versus (c)/(d).
- `int newCap, newThr = 0;` — `newThr` is deliberately left at the sentinel `0`, meaning "not yet decided". Two of the four paths decide it; the `if (newThr == 0)` block downstream is the fallback for the other two. `newCap` gets no initialiser because every reachable path assigns it — the compiler's definite-assignment analysis is load-bearing here.
- `oldCap >= MAXIMUM_CAPACITY` → `threshold = Integer.MAX_VALUE; return oldTab;`. `MAXIMUM_CAPACITY` is `1 << 30` (line 245). The map **stops resizing forever** and returns the same array it was handed. Nothing throws; nothing is lost. Every subsequent `put` just makes bins longer, and past `TREEIFY_THRESHOLD` in a bin, trees deeper. At `1 << 30` bins × 0.75 that is ~805 million entries, so this is an interview answer rather than an operational concern, and the answer is: *`HashMap` degrades silently, it does not fail*. Lookups drift from O(1) toward O(log n) per bin, which is precisely the guarantee treeification exists to hold at the far end.
- `(newCap = oldCap << 1) < MAXIMUM_CAPACITY && oldCap >= DEFAULT_INITIAL_CAPACITY` — note the assignment inside the condition. `newCap` is set to the doubled capacity **whether or not the rest of the condition holds**, because `&&` evaluates left to right and the left operand *is* the assignment. The right-hand clause gates only the *threshold* shortcut. This trips people who read it as "if the guard fails, `newCap` is unset".
- `newThr = oldThr << 1` — the shortcut, and the subject of the next section.
- `else if (oldThr > 0) newCap = oldThr;` — job (b). The constructor put `tableSizeFor(initialCapacity)` into `threshold`. Here it is read back out as a *capacity*, and `newThr` stays at the sentinel so the block below recomputes a real threshold from it. This is the line that turns 1024-as-capacity into 1024-as-capacity-and-768-as-threshold in the output above.
- `else { newCap = 16; newThr = (int)(0.75f * 16); }` — job (a). `DEFAULT_INITIAL_CAPACITY` is `1 << 4` = 16 (line 238), `DEFAULT_LOAD_FACTOR` is `0.75f` (line 250), so `newThr = 12`. Both operands are compile-time constants, so javac folds this to `12`.
- `if (newThr == 0) { float ft = (float)newCap * loadFactor; ... }` — the catch-all for job (b) and for small-table (c)/(d). The `ft < (float)MAXIMUM_CAPACITY` clause is the overflow guard: a large `newCap` times a large `loadFactor` can exceed what an `int` holds, so the result saturates at `Integer.MAX_VALUE` instead of wrapping negative. That matters because a negative threshold makes `++size > threshold` true on every single `put`, and the map would try to resize forever. Load factors above 1.0 are legal — `new HashMap<>(1 << 29, 4.0f)` is the shape that reaches this.
- `threshold = newThr;` then allocate `new Node[newCap]` and publish it to `table`. **The field is assigned before the transfer loop runs.** A reader inside a concurrent resize can therefore observe a table that is allocated but not yet populated. That is the seed of the story in [`03b-internals-c2-concurrent-resize-and-tree-split.md`](03b-internals-c2-concurrent-resize-and-tree-split.md).
- `@SuppressWarnings({"rawtypes","unchecked"})` on a local variable declaration — the array of a generic type cannot be created directly, so the JDK creates `new Node[newCap]` raw and casts. Every generic collection backed by an array does some version of this.

### The `oldCap >= 16` guard on threshold doubling — proved

`newThr = oldThr << 1` looks like it should always be right: doubling the capacity should double the threshold. It is not always right, because `threshold` is an `int` truncated from a `float` product, and **truncation does not commute with doubling**.

`(int)(cap * lf)` discards the fractional part. Doubling the *already truncated* value doubles the discarded fraction along with it, so in general

```
2 * (int)(cap * lf)  ≤  (int)(2 * cap * lf)
```

with strict inequality whenever `cap * lf` had a fractional part of 0.5 or more. Iterate that from a tiny capacity and the threshold drifts permanently below where the load factor says it should be — the map would resize earlier and earlier relative to its own contract. Above capacity 16 the products are large enough (and, for the default `0.75f`, exact at every power of two) that the shortcut and the recomputation agree, so the JDK takes the cheap shift there and pays for the float multiply only in the small-table regime.

Run it rather than trust it:

```java
import java.lang.reflect.Field;
import java.util.HashMap;

public class ThresholdDrift {
    static final Field TABLE, THRESHOLD;
    static {
        try {
            TABLE = HashMap.class.getDeclaredField("table"); TABLE.setAccessible(true);
            THRESHOLD = HashMap.class.getDeclaredField("threshold"); THRESHOLD.setAccessible(true);
        } catch (ReflectiveOperationException e) { throw new ExceptionInInitializerError(e); }
    }
    static int cap(HashMap<?,?> m) throws Exception {
        Object[] t = (Object[]) TABLE.get(m);
        return t == null ? 0 : t.length;
    }
    static int thr(HashMap<?,?> m) throws Exception { return THRESHOLD.getInt(m); }

    static void trace(float lf) throws Exception {
        System.out.println("loadFactor = " + lf + ", initialCapacity = 4");
        HashMap<Integer,Integer> m = new HashMap<>(4, lf);
        int prevCap = 0, prevThr = 0;
        for (int i = 0; i < 40 && cap(m) < 64; i++) {
            m.put(i, i);
            int c = cap(m), t = thr(m);
            if (c != prevCap) {
                System.out.printf("  cap %2d -> %2d : threshold now %2d | oldThr<<1 = %2d "
                                + "| (int)(newCap*lf) = %2d | shortcut taken? %s%n",
                        prevCap, c, t, prevThr << 1, (int)(c * lf),
                        prevCap >= 16 ? "yes (oldCap >= 16)" : "no  (oldCap < 16)");
                prevCap = c; prevThr = t;
            }
        }
    }
    public static void main(String[] a) throws Exception { trace(0.75f); trace(0.7f); }
}
```

`java --add-opens java.base/java.util=ALL-UNNAMED ThresholdDrift.java` on JDK 21. Real output:

```
loadFactor = 0.75, initialCapacity = 4
  cap  0 ->  4 : threshold now  3 | oldThr<<1 =  0 | (int)(newCap*lf) =  3 | shortcut taken? no  (oldCap < 16)
  cap  4 ->  8 : threshold now  6 | oldThr<<1 =  6 | (int)(newCap*lf) =  6 | shortcut taken? no  (oldCap < 16)
  cap  8 -> 16 : threshold now 12 | oldThr<<1 = 12 | (int)(newCap*lf) = 12 | shortcut taken? no  (oldCap < 16)
  cap 16 -> 32 : threshold now 24 | oldThr<<1 = 24 | (int)(newCap*lf) = 24 | shortcut taken? yes (oldCap >= 16)
  cap 32 -> 64 : threshold now 48 | oldThr<<1 = 48 | (int)(newCap*lf) = 48 | shortcut taken? yes (oldCap >= 16)
loadFactor = 0.7, initialCapacity = 4
  cap  0 ->  4 : threshold now  2 | oldThr<<1 =  0 | (int)(newCap*lf) =  2 | shortcut taken? no  (oldCap < 16)
  cap  4 ->  8 : threshold now  5 | oldThr<<1 =  4 | (int)(newCap*lf) =  5 | shortcut taken? no  (oldCap < 16)
  cap  8 -> 16 : threshold now 11 | oldThr<<1 = 10 | (int)(newCap*lf) = 11 | shortcut taken? no  (oldCap < 16)
  cap 16 -> 32 : threshold now 22 | oldThr<<1 = 22 | (int)(newCap*lf) = 22 | shortcut taken? yes (oldCap >= 16)
  cap 32 -> 64 : threshold now 44 | oldThr<<1 = 44 | (int)(newCap*lf) = 44 | shortcut taken? yes (oldCap >= 16)
```

Read the `0.7f` block, which is where the two columns diverge:

| Transition | `oldThr << 1` would give | `(int)(newCap * 0.7f)` gives | Map actually uses | Guard |
|---|---|---|---|---|
| 4 → 8 | 4 | 5 | **5** | skipped, `oldCap < 16` |
| 8 → 16 | 10 | 11 | **11** | skipped, `oldCap < 16` |
| 16 → 32 | 22 | 22 | **22** | taken, and both agree |
| 32 → 64 | 44 | 44 | **44** | taken, and both agree |

The two rows where they disagree are exactly the two rows where the guard is false. And at `16 → 32` they **reconverge at 22** — which is the real evidence for why 16 is the cut-off, not an arbitrary "big enough to bother" threshold. Once the product is large, truncation error stops mattering relative to the value, and the shift becomes safe. With the default `0.75f` the two columns agree at every step, so the guard costs nothing in the common case and buys correctness in the uncommon one.

**Insight:** the guard has nothing to do with performance and everything to do with float truncation error compounding across successive doublings. 16 is the smallest capacity at which the JDK is willing to trust the shift.

**Interview:** *"Why is the threshold-doubling shortcut guarded by `oldCap >= DEFAULT_INITIAL_CAPACITY`?"* — Because `threshold` is a truncated float product, and doubling a truncated value compounds the truncation error; below capacity 16 the JDK recomputes from `(float)newCap * loadFactor` instead. Demonstrate with load factor `0.7f`: at capacity 4 the shift gives 4, the correct value is 5.

> **`resize()`** is `HashMap`'s single table-provisioning routine: it picks a new capacity and a threshold consistent with it for whichever of four states the map is in — no table, requested capacity, doubling, or relieving a crowded small table — allocates the array, publishes it to `table`, and then rehomes any existing entries.

---

## Version notes

`resize()`'s shape is essentially identical across the LTS releases — same body, same constants, same guards, differing only in surrounding javadoc and therefore line offsets:

| JDK | `resize()` at line | Signature |
|---|---|---|
| 7 | — | `void resize(int newCapacity)` + `void transfer(Entry[], boolean)` |
| 8 | 677 | `final Node<K,V>[] resize()` |
| 17 | 675 | `final Node<K,V>[] resize()` |
| 21 | 683 | `final Node<K,V>[] resize()` |

All three JDK 8/17/21 line numbers verified directly in the sources. The break is at Java 7, which had no `resize()` of this shape at all: it took the target capacity as an argument, delegated the move to `transfer`, recomputed the bucket index per node, and could re-invoke `hashCode()` mid-transfer.

---

## Pitfalls

### Expecting a `HashMap` to shrink after mass removal

**Wrong**

```java
Map<Integer,Integer> m = new HashMap<>();
for (int i = 0; i < 1_000_000; i++) m.put(i, i);
m.keySet().removeIf(k -> k > 0);
System.out.println(m.size());   // 1 — but the Node[2097152] array is still allocated
```

**Right**

```java
Map<Integer,Integer> m = new HashMap<>();
for (int i = 0; i < 1_000_000; i++) m.put(i, i);
m.keySet().removeIf(k -> k > 0);
m = new HashMap<>(m);           // fresh table sized for the survivors
```

**Why people believe it:** `ArrayList` has `trimToSize()`, and growable structures are usually assumed symmetric. But `resize()` is only ever reached from the growth path — `remove` decrements `size` and never consults `threshold`.

### Reading `(newCap = oldCap << 1) < MAXIMUM_CAPACITY && oldCap >= 16` as gating `newCap`

**Wrong** — "if the old capacity is under 16 the condition is false, so `newCap` is never assigned. What capacity does an 8-slot table double to?"

**Right** — the assignment `newCap = oldCap << 1` is the *left operand* of `&&`, so it always evaluates. The conjunction gates only the body, `newThr = oldThr << 1`. A capacity-8 table still doubles to 16; it just derives its new threshold from `(float)16 * loadFactor` instead of shifting. The `ThresholdDrift` output above shows exactly that: `cap 8 -> 16` with the shortcut marked "no".

**Why people believe it:** assignment-inside-condition is rare in application code, so the eye reads the whole parenthesised expression as a pure test.

### Assuming `new HashMap<>(1000)` allocates 1000 buckets up front

**Wrong**

```java
Map<String,String> m = new HashMap<>(1000);
// belief: 1000 (or 1024) buckets now exist and no resize can occur before 750 entries
```

Immediately after construction `table` is `null` and `threshold` is `1024`. Nothing is allocated. If the map is never written to, it costs one object header and a few fields — which is the point.

**Right**

```java
Map<String,String> m = new HashMap<>(1000);
m.put("first", "value");        // NOW resize() runs job (b): table.length becomes 1024,
                                // and threshold becomes (int)(1024 * 0.75f) = 768
```

**Why people believe it:** the parameter is named `initialCapacity` and `ArrayList(int)` really does allocate immediately. `HashMap` defers, and stores the requested capacity in the `threshold` field in the meantime — the same field that will later hold a genuine threshold.

---

## Cheat sheet

| Fact | Value / rule |
|---|---|
| Signature, JDK 8/17/21 | `final Node<K,V>[] resize()` — no args, returns the new table |
| Line numbers | JDK 8 : 677 · JDK 17 : 675 · JDK 21 : 683 |
| Java 7 equivalent | `resize(int newCapacity)` + `transfer(Entry[], boolean)` |
| Four jobs | first table · constructor-requested capacity · double · relieve `treeifyBin` |
| Callers | `putVal` (line 631) on `++size > threshold`; `treeifyBin` (line 761) when `tab.length < 64` |
| Capacity storage | none — capacity *is* `table.length`; `oldCap == 0` means no table |
| `DEFAULT_INITIAL_CAPACITY` | `1 << 4` = 16 (line 238) |
| `MAXIMUM_CAPACITY` | `1 << 30` (line 245) |
| `DEFAULT_LOAD_FACTOR` | `0.75f` (line 250) |
| `threshold` field | line 421; holds a *capacity* while `table == null`, a threshold after |
| Default first table | cap 16, threshold 12 |
| `new HashMap<>(1000)` | `table == null`, `threshold == 1024`; first put → cap 1024, threshold 768 |
| Threshold shortcut | `newThr = oldThr << 1`, only when `oldCap >= 16` |
| Why the guard | float truncation drift: lf 0.7f, cap 4→8 shift gives 4, correct is 5; 8→16 gives 10 vs 11; reconverges at 16→32 = 22 |
| At `MAXIMUM_CAPACITY` | `threshold = Integer.MAX_VALUE; return oldTab;` — never resizes again, nothing throws |
| `newThr` overflow guard | `ft < (float)MAXIMUM_CAPACITY` else `Integer.MAX_VALUE` (prevents a negative threshold) |
| Publication order | `threshold` set, array allocated, `table` assigned — all *before* the transfer loop |
| Shrinking | never; `remove` does not resize. Rebuild with `new HashMap<>(old)` |
| Rehashing on resize | none — `Node.hash` is `final` and cached; no user code runs |

---

## Self-test

**Q1.** `resize()` takes no arguments. How does it know whether it is allocating a first table or doubling an existing one?

<details><summary>Answer</summary>

From `oldCap = (oldTab == null) ? 0 : oldTab.length`. Capacity is not a field — it is always `table.length`, and `null` means no table yet. `oldCap == 0` takes the allocation path, which then chooses between the constructor-requested capacity (`oldThr > 0`, where the constructor stashed `tableSizeFor(initialCapacity)` in `threshold`) and the default 16. `oldCap > 0` takes the doubling path.

</details>

**Q2.** Why does the threshold-doubling shortcut require `oldCap >= DEFAULT_INITIAL_CAPACITY`?

<details><summary>Answer</summary>

`threshold` is `(int)(cap * loadFactor)`, a truncation. Doubling an already truncated value doubles the discarded fraction, so it drifts below the correct value, and the drift compounds across successive resizes. With load factor `0.7f` and capacity 4, `threshold` is `(int)2.8 = 2`; `2 << 1 = 4`, but the correct value for capacity 8 is `(int)5.6 = 5`. At 8 → 16 the shift would give 10 against a correct 11. From capacity 16 upward the two agree — verified empirically: 16 → 32 gives 22 by both routes — so the cheap shift is safe there and the JDK pays for the float multiply only below 16.

</details>

**Q3.** What happens when a `HashMap` reaches `MAXIMUM_CAPACITY`?

<details><summary>Answer</summary>

`resize()` sets `threshold = Integer.MAX_VALUE` and returns the existing table unchanged. `size > threshold` is then effectively never true again, so the map never resizes and never throws — it accumulates longer chains and deeper trees, and lookups degrade from O(1) toward O(log n) per bin. `MAXIMUM_CAPACITY` is `1 << 30`, so at the default load factor that is roughly 805 million entries.

</details>

**Q4.** What does `new HashMap<>(1000)` allocate, and what is in `threshold` immediately afterwards?

<details><summary>Answer</summary>

It allocates no table at all — `table` is `null`. `threshold` holds **1024**, which is `tableSizeFor(1000)`: a *capacity*, not a threshold. The field is overloaded, disambiguated by whether `table` is null. On the first `put`, `resize()` takes the `else if (oldThr > 0) newCap = oldThr;` branch, allocates `Node[1024]`, and — because `newThr` is still the sentinel `0` — recomputes `threshold = (int)(1024 * 0.75f) = 768`.

</details>

**Q5.** Why is the `ft < (float)MAXIMUM_CAPACITY` clause there, given that `newCap` is already capped at `MAXIMUM_CAPACITY`?

<details><summary>Answer</summary>

Because `loadFactor` is not capped. Load factors above 1.0 are legal, so `newCap * loadFactor` can exceed `Integer.MAX_VALUE` even when `newCap` itself is in range — `new HashMap<>(1 << 29, 4.0f)` gets there. Without the guard the `(int)` cast could produce a negative threshold, which would make `++size > threshold` true on every single `put` and send the map into a resize on each insertion. The guard saturates at `Integer.MAX_VALUE` instead.

</details>

**Q6.** A million entries were inserted and all but one removed. How much memory does the table still hold, and how do you reclaim it?

<details><summary>Answer</summary>

The `Node[]` is still 2,097,152 slots — the capacity reached at peak — which is about 8 MB of references with compressed oops, nearly all null. `HashMap` has no shrink path: `resize()` is reached only from `putVal` and `treeifyBin`, never from `remove`, and there is no `trimToSize()`. Reclaim it by rebuilding: `m = new HashMap<>(m)`, which sizes a fresh table for the surviving entry count and lets the old array become garbage.

</details>

---

**Leaves covered:** 3.6.23 (1 leaf)
**Leaves deferred:** none — 3.6.24, 3.6.25 and 3.6.26 are in [03a-internals-c1-lo-hi-split.md](03a-internals-c1-lo-hi-split.md)
**Diagrams included:** none new — the lo/hi split (D-92) and the one-bit proof (D-93) are embedded in [03a-internals-c1-lo-hi-split.md](03a-internals-c1-lo-hi-split.md)
**Target version:** Java 21 LTS
**Lines:** 339
