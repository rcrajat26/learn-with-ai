# 02 Java Collections — Specialised maps and sets — INTERNALS (§3.11.4–3.11.7)

**Target version: Java 21 LTS.** | [Index](../00-index.md)
Previous: [specialised-maps/04-internals-identity-weak.md](04-internals-identity-weak.md) · Next: [specialised-maps/04b-internals-weak-hash-map.md](04b-internals-weak-hash-map.md)

This file continues `IdentityHashMap` internals: the sizing constants and the "one null slot always" rule, the `NULL_KEY` sentinel, the documented `Map`-contract violation, and the real use cases. The flat interleaved table, the identity-hash scramble, the probe loops and `closeDeletion` are in the previous file, [04-internals-identity-weak.md](04-internals-identity-weak.md), which is also where the D-117 diagram sequence lives. `WeakHashMap` internals are in the next file, [04b-internals-weak-hash-map.md](04b-internals-weak-hash-map.md).

Every source citation below is a line number in `java.base/java/util/IdentityHashMap.java` from the JDK 21 source bundle (with one file named explicitly for `Collections.java`). Every number and transcript is real output from programs compiled and run on JDK 21; nothing is reconstructed from memory.

Two terms are used throughout and must not be conflated: **capacity** is the number of mappings the table has room for, and **`table.length`** is always `2 * capacity`, because a key at even index `i` is paired with its value at `i+1`.

---

## Sizing constants and the "one null slot always" rule (3.11.4)  `[NUM]` `[RESEARCH]`

### 1. Mental model

Three numbers bracket the table, and a fourth rule — "the table can never be completely full" — sits on top of them. The fourth rule is not a tuning choice. It is a *correctness* requirement, because `get`'s only exit besides a hit is finding `null`. A full table turns `get` on an absent key into an infinite loop.

### 2. Why it exists

`HashMap` can run at load factor 1.0 or above; a chain simply gets longer. Open addressing cannot. Beyond about 2/3 occupancy, linear-probe run lengths blow up superlinearly, and at 100% occupancy the algorithm has no termination condition at all. So the constants are tighter than `HashMap`'s and the ceiling is hard.

### 3. When to reach for it, and when not

Set `expectedMaxSize` when you know it: growth copies and rehashes the whole table, and `capacity()` pre-sizes with the 2/3 headroom already folded in, so `new IdentityHashMap<>(n)` for exactly `n` mappings does not resize. Do not set it wildly high "to be safe" — iteration and `clear()` are O(`table.length`), so an over-sized map makes every traversal slower and holds `8 * capacity` bytes of table forever.

### 4. How it works

The three constants, `:154-179`:

```java
    private static final int DEFAULT_CAPACITY = 32;
```
`:154-158` explains the number: "The value 32 corresponds to the (specified) expected maximum size of 21, given a load factor of 2/3." Arithmetic: `2/3 * 32 = 21.33`, floor 21. So a default map holds 21 mappings and resizes on the 22nd `put`.

```java
    private static final int MINIMUM_CAPACITY = 4;
```
`:162-167`: "The value 4 corresponds to an expected maximum size of 2, given a load factor of 2/3." `2/3 * 4 = 2.67`, floor 2.

```java
    private static final int MAXIMUM_CAPACITY = 1 << 29;
```
And `:170-178`, the important part — this is the "one null slot always" rule, stated in the source:

```
     * MUST be a power of two <= 1<<29.
     *
     * In fact, the map can hold no more than MAXIMUM_CAPACITY-1 items
     * because it has to have at least one slot with the key == null
     * in order to avoid infinite loops in get(), put(), remove()
```

`1 << 29 = 536,870,912`. `table.length` would then be `2 * (1<<29) = 1,073,741,824` — exactly `Integer.MAX_VALUE / 2` rounded to a power of two, so `2 * capacity` never overflows `int`. That is why the exponent is 29 and not 30.

Enforcement is in `resize`, `:472-484`:

```java
    private boolean resize(int newCapacity) {
        int newLength = newCapacity * 2;

        Object[] oldTable = table;
        int oldLength = oldTable.length;
        if (oldLength == 2 * MAXIMUM_CAPACITY) { // can't expand any further
            if (size == MAXIMUM_CAPACITY - 1)
                throw new IllegalStateException("Capacity exhausted.");
            return false;
        }
        if (oldLength >= newLength)
            return false;
```

- Already at max length and already holding `MAXIMUM_CAPACITY - 1` mappings → throw. One more mapping would fill the last `null` slot and hang the next failed lookup, so the class refuses.
- Already at max length but not yet full → `return false`, and `put`'s short-circuit falls through and inserts into the current table. This is the only path by which `size` legally exceeds the 2/3 threshold.
- `oldLength >= newLength` → `return false`. This is what makes `resize` idempotent and lets `putAll` call `resize(capacity(n))` speculatively (`:519-520`) without shrinking anything.

The rehash loop, `:486-502`:

```java
        Object[] newTable = new Object[newLength];

        for (int j = 0; j < oldLength; j += 2) {
            Object key = oldTable[j];
            if (key != null) {
                Object value = oldTable[j+1];
                oldTable[j] = null;
                oldTable[j+1] = null;
                int i = hash(key, newLength);
                while (newTable[i] != null)
                    i = nextKeyIndex(i, newLength);
                newTable[i] = key;
                newTable[i + 1] = value;
            }
        }
        table = newTable;
        return true;
```

`j += 2` skips values. The old slots are nulled as they are copied — the old array is garbage immediately after, and nulling early lets the collector reclaim keys sooner if the old array is somehow still reachable. Note the probe here needs no `closeDeletion` and no `item == k` check: the destination is a fresh table and no key can already be present.

**The growth factor is one doubling, not two.** `put` calls `resize(len)` at `:455`, passing the current **table length** as the new **capacity**; `resize` then computes `newLength = newCapacity * 2` at `:474`. So capacity goes `c → 2c` and `table.length` goes `2c → 4c`. Reading `resize(len)` as "grow to length `len`" makes it look like 4x growth. It is not. (Corroborated by the measured `64 -> 128` below.)

`capacity(expectedMaxSize)`, `:248-254`, is the constructor's sizing function:

```java
    private static int capacity(int expectedMaxSize) {
        return
            (expectedMaxSize > MAXIMUM_CAPACITY / 3) ? MAXIMUM_CAPACITY :
            (expectedMaxSize <= 2 * MINIMUM_CAPACITY / 3) ? MINIMUM_CAPACITY :
            Integer.highestOneBit(expectedMaxSize + (expectedMaxSize << 1));
    }
```

Its javadoc (`:241-246`) promises "the smallest power of two ... that is greater than `(3 * expectedMaxSize)/2`", while the code computes `highestOneBit(3e)` — the *largest* power of two **not exceeding** `3e`. These agree: if `3e ∈ [2^k, 2^{k+1})` then `1.5e ∈ [2^{k-1}, 2^k)`, so the smallest power of two greater than `1.5e` is `2^k`, which is what `highestOneBit(3e)` returns. Row 51's finding 4 — recorded so nobody "corrects" one against the other. `e + (e << 1)` is again `3e` as add-plus-shift.

The threshold test itself lives in `put` and is walked line by line in the previous file, but the arithmetic is a 3.11.4 claim so it is restated here in full. `:452-456`:

```java
            final int s = size + 1;
            // Use optimized form of 3 * s.
            // Next capacity is len, 2 * current capacity.
            if (s + (s << 1) > len && resize(len))
                continue retryAfterResize;
```

`s` is `size + 1` — the **post-insert** size. `s + (s << 1)` is `s + 2s = 3s`. So the test is `3 * (size + 1) > table.length`, and with `table.length = 2 * capacity` that is "resize when the post-insert size would exceed 2/3 of capacity". **The syllabus's `size*3 > len` is wrong at the boundary**, off by exactly one insert; the measured transcript below settles it.

**Insight:** `hash(x, length)` is passed `table.length`, not capacity, so the mask window is `2 * capacity` wide and the even-index constraint halves it back to `capacity` distinct home slots. That is why the load factor is 2/3 *of capacity* and equivalently 1/3 *of `table.length`* — the two phrasings sound contradictory and are the same number.

### 5. Diagram

No diagram in the manifest for the sizing constants; the numbers are the picture, tabulated below. The D-117 sequence belongs to `closeDeletion` and lives in the previous file.

### 6. Concrete example — the numbers, run  `[NUM]`

Mirroring `capacity()` in user code and checking each result against the real reflected `table.length`:

```java
import java.lang.reflect.Field;
import java.util.IdentityHashMap;

public class Cap {
    static final int MINIMUM_CAPACITY = 4;
    static final int MAXIMUM_CAPACITY = 1 << 29;

    // Mirror of IdentityHashMap.capacity(int) — IdentityHashMap.java:248-254
    static int capacity(int expectedMaxSize) {
        return (expectedMaxSize > MAXIMUM_CAPACITY / 3) ? MAXIMUM_CAPACITY
             : (expectedMaxSize <= 2 * MINIMUM_CAPACITY / 3) ? MINIMUM_CAPACITY
             : Integer.highestOneBit(expectedMaxSize + (expectedMaxSize << 1));
    }

    static int tableLen(IdentityHashMap<?, ?> m) throws Exception {
        Field f = IdentityHashMap.class.getDeclaredField("table");
        f.setAccessible(true);
        return ((Object[]) f.get(m)).length;
    }

    public static void main(String[] args) throws Exception {
        System.out.println("expectedMaxSize | 3e | highestOneBit(3e) | capacity() | table.length | max mappings");
        for (int e : new int[] {0, 1, 2, 3, 4, 5, 10, 21, 22, 42, 43, 100, 1000}) {
            int cap = capacity(e);
            int len = tableLen(new IdentityHashMap<>(e));
            int maxFit = 0;
            while (3 * (maxFit + 1) <= len) maxFit++;
            System.out.printf("%15d | %4d | %17d | %10d | %12d | %d%n",
                    e, 3 * e, Integer.highestOneBit(3 * e), cap, len, maxFit);
        }
        System.out.println("MAXIMUM_CAPACITY = 1 << 29 = " + (1 << 29));
        System.out.println("max table.length = " + (2L * (1 << 29)) + " slots");
        System.out.println("max mappings     = MAXIMUM_CAPACITY - 1 = " + ((1 << 29) - 1));
        System.out.println("table heap, 4-byte refs = " + (2L * (1 << 29) * 4 / (1024 * 1024)) + " MiB");
        System.out.println("table heap, 8-byte refs = " + (2L * (1 << 29) * 8 / (1024 * 1024)) + " MiB");
        System.out.println("capacity(1<<29/3 + 1) = " + capacity(MAXIMUM_CAPACITY / 3 + 1));
        System.out.println("capacity(0) = " + capacity(0) + ", capacity(2) = " + capacity(2)
                + ", capacity(3) = " + capacity(3)
                + "  (2*MINIMUM_CAPACITY/3 = " + (2 * MINIMUM_CAPACITY / 3) + ")");
    }
}
```

```
$ javac -Xlint:all -d out Cap.java
$ java --add-opens java.base/java.util=ALL-UNNAMED -cp out Cap
expectedMaxSize | 3e | highestOneBit(3e) | capacity() | table.length | max mappings
              0 |    0 |                 0 |          4 |            8 | 2
              1 |    3 |                 2 |          4 |            8 | 2
              2 |    6 |                 4 |          4 |            8 | 2
              3 |    9 |                 8 |          8 |           16 | 5
              4 |   12 |                 8 |          8 |           16 | 5
              5 |   15 |                 8 |          8 |           16 | 5
             10 |   30 |                16 |         16 |           32 | 10
             21 |   63 |                32 |         32 |           64 | 21
             22 |   66 |                64 |         64 |          128 | 42
             42 |  126 |                64 |         64 |          128 | 42
             43 |  129 |               128 |        128 |          256 | 85
            100 |  300 |               256 |        256 |          512 | 170
           1000 | 3000 |              2048 |       2048 |         4096 | 1365
MAXIMUM_CAPACITY = 1 << 29 = 536870912
max table.length = 1073741824 slots
max mappings     = MAXIMUM_CAPACITY - 1 = 536870911
table heap, 4-byte refs = 4096 MiB
table heap, 8-byte refs = 8192 MiB
capacity(1<<29/3 + 1) = 536870912
capacity(0) = 4, capacity(2) = 4, capacity(3) = 8  (2*MINIMUM_CAPACITY/3 = 2)
```

`capacity(1<<29/3 + 1)` returning `536870912` is the first ternary clamping to `MAXIMUM_CAPACITY`, and `max table.length = 1073741824` is `2 * (1<<29)`.

Thirteen inputs, all three columns agreeing: the mirrored `capacity()`, the actual reflected `table.length`, and `table.length == 2 * capacity` in every row. Read row `21`: `capacity(21) = 32`, `table.length = 64`, and exactly 21 mappings fit — the `DEFAULT_CAPACITY` javadoc's claim at `:154-158`, confirmed independently. Row `22` jumps to capacity 64, so `new IdentityHashMap<>(22)` holds 42 without resizing. Rows `0`, `1`, `2` all clamp to `MINIMUM_CAPACITY` via the middle ternary, since `2 * MINIMUM_CAPACITY / 3` is 2 in integer arithmetic.

And the resize boundary, watched live by reflecting on `table` after every `put`:

```
=== the resize boundary: which put grows a len=64 table? ===
put #22 grew table.length 64 -> 128 (size after = 22)
3*s > len check: s=22 -> 22+(22<<1)=66 > 64 ? true   s=21 -> 63 > 64 ? false
```

**The 22nd `put`, not the 23rd, and certainly not the 43rd.** With `size = 21` and a 22nd insert pending, `s = 22`, `3s = 66 > 64` → resize. Had the test been the syllabus's `size * 3 > len`, it would read `63 > 64` → false, and the resize would have been deferred one insert. Note also `64 -> 128`, a single doubling of `table.length`, confirming that `resize(len)` grows capacity `32 → 64` rather than to `len` itself.

**Per-mapping heap arithmetic** `[NUM]`, with compressed oops (4-byte references, heaps under 32 GiB):

- `IdentityHashMap`: `table.length = 2 * capacity` slots × 4 B = `8 * capacity` bytes. Max mappings ≈ `(2/3) * capacity`. Per mapping: `8 * capacity / (0.667 * capacity) = 12 B`. Plus a 16-byte `IdentityHashMap` object and a 16-byte array header, amortised to nothing.
- `HashMap`: `Node[]` of `capacity` slots × 4 B, plus one `Node` per mapping — 12 B header + 4 B `hash` + 4 B `key` + 4 B `value` + 4 B `next` = 28 B, padded to **32 B**. At load factor 0.75: `4 / 0.75 = 5.3 B` of table + 32 B of node = **~37 B** per mapping.
- Ratio: **~3.1x**. That is the number to quote, not a timing. `IdentityHashMap`'s memory win is arithmetic and certain; its speed win is workload-dependent and the javadoc only claims it "for many Java implementations and operation mixes" (`:133-135`).

**On the `IllegalStateException("Capacity exhausted.")` demo:** it is not runnable. Reaching it requires `size == MAXIMUM_CAPACITY - 1 = 536,870,911` live mappings and a 1,073,741,824-slot `Object[]` — 4 GiB of table with compressed oops, 8 GiB without, before counting a half-billion live key objects. No demo is offered here rather than a fabricated transcript. The path is verified by reading `:478-482`.

**Unverified:** which JDK release introduced `put`'s `retryAfterResize` labelled loop and the `s + (s << 1)` forward-looking threshold. The class is `@since 1.4` (`:147`) and the constants' javadoc has clearly been stable a long time, but only the JDK 21 source was available here; the JDK 8 and JDK 11 sources were not checked, so no claim is made about when the current `put` shape landed. Recorded in `## Open questions`.

### 7. The gotcha

**Pitfall:** passing the *table length* you want to the constructor. Symptom: `new IdentityHashMap<>(64)` when you meant "64 slots" gives you capacity 64, `table.length` 128, and room for 42 mappings — twice the memory you budgeted. Fix: the constructor argument is `expectedMaxSize` — the number of *mappings* — and the class already adds the 2/3 headroom.

### 8. Definition

> `DEFAULT_CAPACITY = 32`, `MINIMUM_CAPACITY = 4` and `MAXIMUM_CAPACITY = 1 << 29` bracket the capacity; `table.length` is always `2 * capacity`; the effective load factor is 2/3 of capacity, enforced forward-looking as `3 * (size + 1) > table.length`; and the map can never exceed `MAXIMUM_CAPACITY - 1` mappings because at least one `null` key slot must remain or `get`, `put` and `remove` would loop forever.

---

## `NULL_KEY`, `maskNull`, `unmaskNull` (3.11.5)

A supporting fact — three lines of mechanism, one gotcha, one definition. No diagram, no analogy.

**Mechanism.** `null` cannot be stored as a key, because `null` in a key slot *means* "empty". So `null` is swapped for a private sentinel object on the way in and swapped back on the way out. `:198-215`:

```java
    /**
     * Value representing null keys inside tables.
     */
    static final Object NULL_KEY = new Object();

    /**
     * Use NULL_KEY for key if it is null.
     */
    private static Object maskNull(Object key) {
        return (key == null ? NULL_KEY : key);
    }

    /**
     * Returns internal representation of null key back to caller as null.
     */
    static final Object unmaskNull(Object key) {
        return (key == NULL_KEY ? null : key);
    }
```

`NULL_KEY` is a plain `new Object()` — it needs no behaviour, only a unique identity, which is exactly what this map compares. It is `static final`, so one instance is shared by every `IdentityHashMap` in the JVM; that is safe precisely because a user can never obtain a reference to it. `maskNull` is `private` (only `get`/`put`/`remove`/`containsKey` call it); `unmaskNull` is package-private because the nested iterator and entry classes need it when handing keys back out. Both are `==` comparisons — no `equals`, consistent with the rest of the class.

**`null` never reaches `hash()`.** `System.identityHashCode(null)` is defined to be `0`, so a naive reading predicts the `null` key always lands at slot 0. It does not: `maskNull` substitutes `NULL_KEY` *before* the index is computed, and `NULL_KEY` gets a normal identity hash like any other object. The `null` key therefore has no special position in the table.

**Round-tripping a `null` key, run:**

```
=== NULL_KEY sentinel: a null key round-trips ===
hash(null, 64) would be 0 because identityHashCode(null) = 0 -- but null never reaches hash(): maskNull replaces it with NULL_KEY first.
occupied slot = 20, stored key object class = java.lang.Object, stored key == null ? false  (that object is NULL_KEY)
get(null)         = value-for-null
containsKey(null) = true
keySet() first    = null
size              = 1
```

The stored key is a `java.lang.Object` that is *not* `null` — that is `NULL_KEY` — yet `keySet()` hands back `null`, because the iterator applies `unmaskNull`. And it sits at slot 20 of 64, not slot 0, confirming the sentinel is hashed like any other object. The literal `20` is run-specific — `NULL_KEY`'s identity hash is whatever the JVM assigned it; the load-bearing fact is that it is not `0`.

**Pitfall:** assuming `IdentityHashMap` rejects a `null` key like `Hashtable` or `Map.of` do. Symptom: defensive `Objects.requireNonNull` that rejects input the map handles fine, or a `NullPointerException` expectation in a test that never fires. Fix: `:65-67` — "This class provides all of the optional map operations, and permits `null` values and the `null` key." Both. `null` values need no sentinel at all, because emptiness is decided by the *key* slot; note `containsValue` at `:388-390` checks `tab[i] == value && tab[i - 1] != null`, testing the key slot to distinguish "value is null" from "slot is empty".

> `NULL_KEY` is a private `static final Object` sentinel substituted for a `null` key by `maskNull` on every entry path and reversed by `unmaskNull` on every exit path, so that a `null` key slot can unambiguously mean "empty" while `null` remains a legal key.

---

## The documented `Map`-contract violation (3.11.6)

### 1. Mental model

Every other `Map` in `java.util` promises that `equals`-equal keys are the same key. `IdentityHashMap` breaks that promise deliberately, and — unusually for the JDK — says so in bold in its own class javadoc. It is not a bug that leaked into the docs; the violation *is* the feature, and the javadoc is where the JDK authors ask you to be sure you want it.

### 2. Why it exists

Some algorithms need to distinguish two objects that are `equals` to each other. Cycle detection is the canonical case: if a graph contains two distinct-but-equal nodes, an `equals`-based "seen" set merges them, and the traversal either terminates early with the wrong answer or, in a deep-copy, produces a structurally different graph. No amount of care with `equals` fixes this from the outside, because the semantics you need are `==`, and `Map` mandates `equals`. So the JDK provides one map that mandates `==` and labels it clearly.

### 3. When to reach for it, and when not

Reach for it when reference identity is the *specification*, not an optimisation. Do not reach for it as a fast `HashMap` — the moment a key arrives from deserialisation, a proxy, a string literal versus a runtime-built string, or an autoboxing cache boundary, lookups silently miss. And never expose an `IdentityHashMap` through a `Map`-typed API: callers will pass an `equals`-equal key and get `null`, with nothing in the signature to warn them.

### 4. How it works — the javadoc, verbatim

`:45-50`, the paragraph that justifies the class:

```
 * <p><b>This class is <i>not</i> a general-purpose {@code Map}
 * implementation!  While this class implements the {@code Map} interface, it
 * intentionally violates {@code Map's} general contract, which mandates the
 * use of the {@code equals} method when comparing objects.  This class is
 * designed for use only in the rare cases wherein reference-equality
 * semantics are required.</b>
```

"Intentionally violates". "Only in the rare cases". The `<b>` is in the source.

The violation is scoped and re-declared where it bites. On `equals`, `:650-654`:

```
     * <p><b>Owing to the reference-equality-based semantics of this map it is
     * possible that the symmetry and transitivity requirements of the
     * {@code Object.equals} contract may be violated if this map is compared
     * to a normal map.  However, the {@code Object.equals} contract is
     * guaranteed to hold among {@code IdentityHashMap} instances.</b>
```

And on `hashCode`, `:692-697`, the matching admission that `m1.equals(m2) ⇒ m1.hashCode() == m2.hashCode()` holds only among `IdentityHashMap` instances.

The implementation makes the scoping concrete, `:660-679`:

```java
    public boolean equals(Object o) {
        if (o == this) {
            return true;
        } else if (o instanceof IdentityHashMap<?, ?> m) {
            if (m.size() != size)
                return false;

            Object[] tab = m.table;
            for (int i = 0; i < tab.length; i+=2) {
                Object k = tab[i];
                if (k != null && !containsMapping(k, tab[i + 1]))
                    return false;
            }
            return true;
        } else if (o instanceof Map<?, ?> m) {
            return entrySet().equals(m.entrySet());
        } else {
            return false;  // o is not a Map
        }
    }
```

- `o == this` short-circuits, so reflexivity always holds.
- The `IdentityHashMap` branch reaches straight into `m.table` (possible because `table` is package-private) and checks every mapping with `containsMapping`, which is identity-based on both key and value. Within this branch equality is a genuine equivalence relation — hence the javadoc's guarantee "among `IdentityHashMap` instances".
- The general `Map` branch delegates to `entrySet().equals(...)`, and `IdentityHashMap`'s entry set compares entries by reference. That is where symmetry and transitivity go.
- Java 21 idiom worth noting: both branches use `instanceof` pattern matching with a binding variable, so there is no cast.

### 5. Diagram

No diagram; the program below is clearer than any picture of it.

### 6. Concrete example — the violation, run

```java
import java.util.IdentityHashMap;
import java.util.List;
import java.util.Map;

public class Violation {
    public static void main(String[] args) {
        String s1 = new String("k");
        String s2 = new String("k");

        Map<String, Integer> hm = new java.util.HashMap<>();
        Map<String, Integer> ihm = new IdentityHashMap<>();
        hm.put(s1, 1);  hm.put(s2, 2);
        ihm.put(s1, 1); ihm.put(s2, 2);
        System.out.println("s1.equals(s2) = " + s1.equals(s2) + ", s1 == s2 = " + (s1 == s2));
        System.out.println("HashMap         size=" + hm.size()
                + " get(s1)=" + hm.get(s1) + " get(s2)=" + hm.get(s2));
        System.out.println("IdentityHashMap size=" + ihm.size()
                + " get(s1)=" + ihm.get(s1) + " get(s2)=" + ihm.get(s2));
        System.out.println("get(\"k\") on IdentityHashMap = " + ihm.get("k"));

        Map<String, Integer> h1 = new java.util.HashMap<>();
        h1.put(s1, 1);
        Map<String, Integer> h2 = new java.util.HashMap<>();
        h2.put(s2, 1);
        Map<String, Integer> id = new IdentityHashMap<>();
        id.put(s1, 1);
        System.out.println("all three print the same: " + List.of(h1, h2, id));
        System.out.println("h1.equals(h2) = " + h1.equals(h2));
        System.out.println("h1.equals(id) = " + h1.equals(id));
        System.out.println("h2.equals(id) = " + h2.equals(id));
        System.out.println("h1.hashCode() = " + h1.hashCode() + ", id.hashCode() = " + id.hashCode());
    }
}
```

```
$ javac -Xlint:all -d out Violation.java
$ java -cp out Violation
s1.equals(s2) = true, s1 == s2 = false
HashMap         size=1 get(s1)=2 get(s2)=2
IdentityHashMap size=2 get(s1)=1 get(s2)=2
get("k") on IdentityHashMap = null
all three print the same: [{k=1}, {k=1}, {k=1}]
h1.equals(h2) = true
h1.equals(id) = true
h2.equals(id) = false
h1.hashCode() = 106, id.hashCode() = 490528984
```

**On that last number:** `106` is deterministic — `AbstractMap.hashCode` sums `"k".hashCode() ^ Integer.valueOf(1).hashCode()`. `490528984` is **not**: `IdentityHashMap.hashCode` (`:703-712`) sums identity hashes, so it changes between runs (a second run of the same program printed `1340971164`). The load-bearing fact is that the two differ, not what either is.

Three things to take from that. The `HashMap` collapsed two `equals`-equal keys to one mapping of size 1; the `IdentityHashMap` kept both, size 2. `ihm.get("k")` is `null` — the interned literal is a *third* object, so a perfectly reasonable-looking lookup misses.

And the last four lines are the **transitivity** violation the javadoc warns about at `:650-654`, with real output: `h1.equals(h2)` is `true` and `h1.equals(id)` is `true`, but `h2.equals(id)` is `false`. All three maps print identically as `{k=1}`. The `hashCode`s differ too — a deterministic `106` versus a run-specific identity sum — so an `IdentityHashMap` and an `equals`-equal `HashMap` can never be safely used as keys in the same hash-based collection.

**A note on which half of the javadoc's warning actually manifests.** The javadoc names both symmetry and transitivity. Transitivity is the one demonstrated above and it reproduces reliably. An **asymmetry** demo was attempted and did *not* reproduce for the obvious two-map shapes: with the same key reference on both sides, both directions return `true` (`HashMap` inherits `AbstractMap.equals`, which does `id.get(key)` and hits; `IdentityHashMap`'s `Map` branch delegates to `entrySet().equals`, and the entry compares equal by reference on both key and value). With `equals`-but-not-`==` keys and equal sizes, both directions return `false`. So the honest statement is: the javadoc reserves the right to break symmetry, but transitivity is the violation you will actually hit.

### 7. The gotcha

**Pitfall:** using `IdentityHashMap` with boxed primitives, strings or enums as keys. Symptom: lookups work in tests and miss in production. Fix: understand the caches. `Integer.valueOf` caches only `-128..127` by default (`-XX:AutoBoxCacheMax` moves the top), so `map.put(1000, x); map.get(1000)` misses while `map.put(100, x); map.get(100)` hits — the ugliest kind of bug, correct for small values and wrong for large. String literals are interned and identical; strings from `substring`, concatenation at runtime, or JSON parsing are not. Enums are singletons and are genuinely safe, but then `EnumMap` is strictly better.

### 8. Definition

> `IdentityHashMap` deliberately and documentedly violates the `Map` contract by using `==` where `Map` mandates `equals`; the `Object.equals` contract holds among `IdentityHashMap` instances only, and comparing one to a normal `Map` can break symmetry, transitivity and the `equals`/`hashCode` agreement.

---

## Use cases, and `newSetFromMap` (3.11.7)

### 1. Mental model

Almost every legitimate use of this class is one question asked repeatedly: **"have I seen this exact object before?"** Graph traversal marks. Serialization node tables. Deep-copy back-references. Proxy registries. In every case the answer must be about the *object*, not about its value, and in every case you want a set rather than a map. `Collections.newSetFromMap` gives you the set.

### 2. Why it exists

There is no `IdentityHashSet` in `java.util`, and there never has been. Rather than add one, JDK 6 added `Collections.newSetFromMap(Map<E, Boolean>)` — a generic adapter that turns any `Map` into the `Set` of its keys. `newSetFromMap(new IdentityHashMap<>())` is the identity set; `newSetFromMap(new WeakHashMap<>())` is the weak set, and is the example the javadoc itself gives.

### 3. When to reach for it, and when not

| Task | Right tool | Why the alternatives lose |
|---|---|---|
| "seen this object?" during graph walk | `newSetFromMap(new IdentityHashMap<>())` | `HashSet` merges `equals`-equal distinct nodes; also calls user `equals`/`hashCode`, which on a cyclic graph can recurse forever |
| serialization / deep-copy back-reference table | `IdentityHashMap<Object, Integer>` (object → id) | needs the *object* → handle mapping; two equal objects must get different handles |
| proxy registry (target → proxy) | `IdentityHashMap` | a proxy must be per-instance |
| memoising a pure function of a value | `HashMap` | value semantics are exactly what you want |
| keys are enums | `EnumMap` | O(1) array indexing, no hashing at all |
| keys must not pin memory | `WeakHashMap` (next file) | `IdentityHashMap` holds strong references and leaks if used as a cache |

The row that matters most: **`HashSet` cannot do cycle detection on a value-equal graph, and it can hang on a cyclic one.** A `Node.equals` that recurses into `next` will stack-overflow on a cycle. `IdentityHashMap` never calls user code on a key — only `System.identityHashCode` and `==` — so it is immune.

### 4. How it works

`Collections.java:5903-5907`:

```java
    public static <E> Set<E> newSetFromMap(Map<E, Boolean> map) {
        if (! map.isEmpty()) // implicit null check
            throw new IllegalArgumentException("Map is non-empty");
        return new SetFromMap<>(map);
    }
```

- The backing map must be empty, checked eagerly — otherwise pre-existing mappings with a `false` value would appear as set members with no way to reason about them. `map.isEmpty()` also serves as the null check, hence the comment.
- `Map<E, Boolean>` fixes the value type; `SetFromMap.add` stores `Boolean.TRUE`.
- `SetFromMap` (`Collections.java:5912-5922`) keeps `m` and caches `m.keySet()` into `s`, then delegates every read to `s` and every write to `m`. So the set inherits the backing map's equality semantics wholesale — including the contract violation. That is the point.

### 5. Diagram

No diagram in the manifest for the use cases.

### 6. Concrete example — identity set vs `HashSet` on a value-equal graph

```java
import java.util.ArrayDeque;
import java.util.Collections;
import java.util.Deque;
import java.util.HashSet;
import java.util.IdentityHashMap;
import java.util.Map;
import java.util.Set;

public class Walk {

    static final class Node {
        final String label;
        Node next;
        Node(String label) { this.label = label; }
        @Override public boolean equals(Object o) {
            return o instanceof Node n && label.equals(n.label);
        }
        @Override public int hashCode() { return label.hashCode(); }
        @Override public String toString() {
            return "Node(" + label + ")@" + Integer.toHexString(System.identityHashCode(this));
        }
    }

    static int walk(Node start, Set<Node> seen) {
        Deque<Node> stack = new ArrayDeque<>();
        stack.push(start);
        int visited = 0;
        while (!stack.isEmpty()) {
            Node n = stack.pop();
            if (!seen.add(n)) continue;
            visited++;
            if (n.next != null) stack.push(n.next);
        }
        return visited;
    }

    public static void main(String[] args) {
        Node a = new Node("x");
        Node b = new Node("y");
        Node aPrime = new Node("x");   // equals(a), but a different object
        a.next = b;
        b.next = aPrime;

        System.out.println("a      = " + a);
        System.out.println("aPrime = " + aPrime);
        System.out.println("a.equals(aPrime) = " + a.equals(aPrime) + ", a == aPrime = " + (a == aPrime));
        System.out.println("identity set : " + walk(a, Collections.newSetFromMap(new IdentityHashMap<>())));
        System.out.println("HashSet      : " + walk(a, new HashSet<>()));

        Set<Node> seen = Collections.newSetFromMap(new IdentityHashMap<>());
        System.out.println("add(a)      = " + seen.add(a));
        System.out.println("add(a)      = " + seen.add(a));
        System.out.println("add(aPrime) = " + seen.add(aPrime));
        System.out.println("size        = " + seen.size());
        System.out.println("contains(new Node(\"x\")) = " + seen.contains(new Node("x")));

        Map<String, Boolean> dirty = new IdentityHashMap<>();
        dirty.put("seed", Boolean.TRUE);
        try {
            Collections.newSetFromMap(dirty);
        } catch (IllegalArgumentException e) {
            System.out.println("caught: " + e.getClass().getSimpleName() + ": " + e.getMessage());
        }
    }
}
```

```
$ javac -Xlint:all -d out Walk.java
$ java -cp out Walk
a      = Node(x)@15db9742
aPrime = Node(x)@266474c2
a.equals(aPrime) = true, a == aPrime = false
identity set : 3
HashSet      : 2
add(a)      = true
add(a)      = false
add(aPrime) = true
size        = 2
contains(new Node("x")) = false
caught: IllegalArgumentException: Map is non-empty
```

Three distinct objects in the chain. The identity set visits all three. The `HashSet` visits two — it decided `aPrime` was already seen because it is `equals` to `a`, and silently dropped a node. In a deep-copy that is a wrong-shaped output graph; in a cycle detector it is a false positive.

The second block shows the set is a real `Set`: `add` is idempotent per *reference*, `add(aPrime)` succeeds even though `aPrime.equals(a)`, and `contains` on a fresh-but-equal object is `false`. The last line shows `newSetFromMap` rejecting a non-empty backing map — deliberately inside a `try`/`catch`, printing the caught exception as the lesson, so the program still runs to completion.

### 7. The gotcha

**Pitfall:** using `newSetFromMap(new IdentityHashMap<>())` as a long-lived cache of "objects I have processed". Symptom: a slow memory leak — the identity set holds *strong* references, so every object you ever marked stays reachable forever. Fix: scope the set to the traversal (a local variable, not a field), or use `newSetFromMap(new WeakHashMap<>())` if the membership must outlive the objects' other references. Note the two are not interchangeable: `WeakHashMap` uses `equals`, so a weak set is not an identity set. There is no `WeakIdentityHashMap` in `java.util`; `sun.misc` and various libraries provide one, and rolling your own means subclassing `WeakReference` with `==`-based `equals`.

### 8. Definition

> `IdentityHashMap` — usually as `Collections.newSetFromMap(new IdentityHashMap<>())` — is the JDK's answer to "have I seen this exact object?", which is why the javadoc names topology-preserving graph transformations and proxy registries as its two intended uses; it is not a faster `HashMap` and not a cache.

---

## Pitfalls

### Assuming `table.length` is the capacity

**Wrong**

```java
IdentityHashMap<Object, Object> m = new IdentityHashMap<>();
// "table.length is 64, load factor 2/3, so it grows at put 43"
for (int i = 1; i <= 43; i++) m.put(new Object(), i);
```

Reflection on `table` shows the growth at `put #22`, not `#43`:

```
put #22 grew table.length 64 -> 128 (size after = 22)
```

**Right**

```java
// table.length == 2 * capacity. The threshold test in put() is
// 3 * (size + 1) > table.length, i.e. (size + 1) > (2/3) * capacity.
// Default capacity 32 -> 21 mappings fit -> the 22nd put resizes.
IdentityHashMap<Object, Object> m = new IdentityHashMap<>(1000); // expectedMaxSize, in MAPPINGS
```

**Why people believe it:** in `HashMap` the table length *is* the capacity, and every article about hash-map load factors is written about `HashMap`. `IdentityHashMap` doubles the array to interleave values, and the doubling is invisible from the public API.

### Believing the threshold is `size * 3 > len`

**Wrong**

```java
// predicted: resize when 3 * size exceeds table.length
boolean willResizeOnNextPut = 3 * m.size() > tableLength;   // off by one insert
```

```
3*s > len check: s=22 -> 22+(22<<1)=66 > 64 ? true   s=21 -> 63 > 64 ? false
```

At `size == 21` on a 64-slot table, `3 * 21 = 63` is not `> 64`, so this predicate says "no resize" — but the next `put` does resize.

**Right**

```java
// IdentityHashMap.java:452-456 — forward-looking on the POST-insert size
int s = m.size() + 1;
boolean willResizeOnNextPut = s + (s << 1) > tableLength;   // 3 * (size + 1)
```

**Why people believe it:** the source comment says "Use optimized form of 3 * s", and readers carry away "3 * size" without noticing that `s` was defined as `size + 1` on the line above.

### Expecting the `null` key at slot 0

**Wrong**

```java
// identityHashCode(null) == 0, and hash(0, 64) == 0, so the null key must be at slot 0
IdentityHashMap<String, String> m = new IdentityHashMap<>();
m.put(null, "v");
// assert tableOf(m)[0] != null;   // fails
```

```
occupied slot = 20, stored key object class = java.lang.Object, stored key == null ? false
```

**Right**

```java
// maskNull() runs BEFORE hash(), so the index is hash(NULL_KEY, len) —
// NULL_KEY is an ordinary object with an ordinary identity hash.
System.out.println(m.get(null));          // v
System.out.println(m.containsKey(null));  // true
```

**Why people believe it:** `System.identityHashCode(null)` really is specified as `0`, and the reasoning is sound right up to the point where you notice that `null` is replaced before `hash` is ever called.

### Using boxed integers or runtime-built strings as keys

**Wrong**

```java
IdentityHashMap<Integer, String> m = new IdentityHashMap<>();
m.put(100, "small");
m.put(1000, "large");
System.out.println(m.get(100));    // small   -- Integer cache -128..127
System.out.println(m.get(1000));   // null    -- a different box each time
```

**Right**

```java
Map<Integer, String> m = new HashMap<>();   // value semantics, so use a value map
```

**Why people believe it:** the small-value case works, and `-128..127` covers most test data. The failure only appears with production-sized numbers.

---

## Cheat sheet

| Item | Value / form | Source |
|---|---|---|
| `DEFAULT_CAPACITY` | 32 → `table.length` 64 → 21 mappings | `:160`, `:154-158` |
| `MINIMUM_CAPACITY` | 4 → `table.length` 8 → 2 mappings | `:168`, `:162-167` |
| `MAXIMUM_CAPACITY` | `1 << 29` = 536,870,912; max mappings `MAXIMUM_CAPACITY - 1` | `:179`, `:170-178` |
| Why `1 << 29` | so `table.length = 2 * capacity` = 1,073,741,824 fits in `int` | derived |
| `table.length` | always `2 * capacity`, always a power of two | `:266` |
| Load factor | 2/3 **of capacity** = 1/3 of `table.length`; not configurable | `:154-158` |
| Resize test | `s = size + 1; s + (s << 1) > len` → `3 * (size + 1) > table.length` | `:452-455` |
| First resize | default map: the **22nd** `put` (not the 23rd, not the 43rd) | measured |
| Growth | `resize(len)` takes the *length* as the new *capacity*; `newLength = newCapacity * 2` → one doubling each | `:455`, `:474` |
| `capacity(e)` | `Integer.highestOneBit(e + (e << 1))` = `highestOneBit(3e)`, clamped to `[4, 1<<29]` | `:248-254` |
| `capacity()` javadoc | "smallest power of two > 1.5e" — same function as `highestOneBit(3e)` | `:241-246` |
| One-null-slot rule | a full table would hang `get`/`put`/`remove`; guarded by `IllegalStateException("Capacity exhausted.")` | `:175-178`, `:478-482` |
| `resize` returns `false` | at max length and not yet full → `put` inserts anyway, exceeding the threshold | `:478-484` |
| Rehash loop | `j += 2`, nulls old slots as it copies, no `closeDeletion` needed | `:486-502` |
| Iteration / `clear` cost | O(`table.length`), not O(`size`) | `:86-89`, `:633-639` |
| Per-mapping heap | ~12 B vs `HashMap`'s ~37 B (4-byte refs) — ~3.1x | derived |
| Null key | allowed, via `static final Object NULL_KEY = new Object()` | `:198-201` |
| `maskNull` / `unmaskNull` | `private` in, package-private out; both `==` comparisons | `:206-215` |
| Null key's slot | `hash(NULL_KEY, len)` — ordinary, **not** slot 0 | measured (slot 20 of 64, run-specific) |
| Null value | allowed; emptiness decided by the key slot (`tab[i-1] != null`) | `:388-390` |
| Contract | **intentional** `Map`-contract violation; `equals` holds only among `IdentityHashMap`s | `:45-50`, `:650-654` |
| What breaks | transitivity, demonstrably; `hashCode` agreement too; symmetry is reserved but did not reproduce | measured |
| `equals` dispatch | `o == this` → `IdentityHashMap` fast path reading `m.table` → generic `entrySet().equals` | `:660-679` |
| Identity set | `Collections.newSetFromMap(new IdentityHashMap<>())`; backing map must be empty | `Collections.java:5903-5907` |
| Intended uses | object-graph transformation / node tables, proxy registries | `:56-63` |
| Not for | caches (holds strong refs), boxed primitives, runtime-built strings, enums (use `EnumMap`) | — |
| Reflection flag | `--add-opens java.base/java.util=ALL-UNNAMED` | — |

---

## Self-test

**Q1.** On a default `new IdentityHashMap<>()`, which `put` grows the table, and show the arithmetic.

<details><summary>Answer</summary>

The 22nd. `DEFAULT_CAPACITY = 32` so `table.length = 64`. `put` computes `s = size + 1` and tests `s + (s << 1) > len`, i.e. `3s > 64`. Before the 22nd insert `size = 21`, so `s = 22` and `3 * 22 = 66 > 64` → resize. Before the 21st, `s = 21` and `3 * 21 = 63`, not `> 64` → no resize. Measured output: `put #22 grew table.length 64 -> 128 (size after = 22)`. Note two common wrong answers: the 23rd (from misreading the test as `3 * size > len`) and the 43rd (from treating `table.length` as the capacity). The `DEFAULT_CAPACITY` javadoc at `:154-158` independently confirms 21 mappings: "The value 32 corresponds to the (specified) expected maximum size of 21, given a load factor of 2/3."

</details>

**Q2.** Why can an `IdentityHashMap` never hold `MAXIMUM_CAPACITY` mappings, and what happens if you try?

<details><summary>Answer</summary>

Because `get`, `put` and `remove` all use "found a `null` key slot" as their only termination condition besides a hit. If every key slot were occupied, a lookup for an absent key would circle the table forever. The source states this at `:170-178`: the map "can hold no more than MAXIMUM_CAPACITY-1 items because it has to have at least one slot with the key == null in order to avoid infinite loops in get(), put(), remove()". It is enforced in `resize` at `:478-482`: if the table is already at maximum length and `size == MAXIMUM_CAPACITY - 1`, it throws `IllegalStateException("Capacity exhausted.")`. Reaching that state needs ~537 million live mappings and a 4 GiB table, so it is a read-the-source fact, not a runnable demo.

</details>

**Q3.** `put` calls `resize(len)` and `resize` computes `newLength = newCapacity * 2`. Does capacity double or quadruple?

<details><summary>Answer</summary>

It doubles, once. The confusion is a naming mismatch: `put` at `:455` passes `len`, which is the current `table.length` and therefore equals `2 * capacity`, into a parameter named `newCapacity`. `resize` at `:474` then computes `newLength = newCapacity * 2 = 4 * oldCapacity = 2 * oldLength`. So capacity goes `32 → 64` and `table.length` goes `64 → 128`. Measured: `put #22 grew table.length 64 -> 128`. Reading `resize(len)` as "resize to length `len`" and then also applying the internal `* 2` is what produces the bogus 4x answer.

</details>

**Q4.** `IdentityHashMap` permits a `null` key. How, given that a `null` key slot means "empty" — and which slot does the `null` key land in?

<details><summary>Answer</summary>

Via a sentinel. `static final Object NULL_KEY = new Object()` at `:201`; `maskNull(key)` returns `NULL_KEY` when `key == null` and is called first in every entry path; `unmaskNull(key)` reverses it on every exit path, including in the iterators — which is why `keySet().iterator().next()` returns `null` even though the array slot holds an `Object`. `NULL_KEY` needs no behaviour, only a unique identity, which is precisely what this map compares, so a bare `new Object()` suffices. It is unreachable from user code, so sharing one static instance across all instances is safe.

As for the slot: **not slot 0.** `System.identityHashCode(null)` is `0`, so `hash(null, 64)` would be `0` — but `null` never reaches `hash()`, because `maskNull` substitutes `NULL_KEY` first, and `NULL_KEY` has an ordinary identity hash. Measured: the `null` key landed at slot 20 of 64. Null *values* need no machinery at all, because emptiness is decided by the key slot — see `containsValue` at `:388-390` testing `tab[i - 1] != null`.

</details>

**Q5.** Which part of the `equals` contract does `IdentityHashMap` actually break, and how would you demonstrate it in five lines?

<details><summary>Answer</summary>

**Transitivity**, demonstrably. Take `s1 = new String("k")` and `s2 = new String("k")` — `equals` but not `==`. Build `h1 = HashMap{s1 → 1}`, `h2 = HashMap{s2 → 1}`, `id = IdentityHashMap{s1 → 1}`. All three print `{k=1}`. Then `h1.equals(h2)` is `true`, `h1.equals(id)` is `true`, but `h2.equals(id)` is `false` — because `IdentityHashMap`'s generic `Map` branch (`:674-675`) compares entry sets by reference, and `s2` is not `s1`. `h1.hashCode()` is a deterministic `106` while `id.hashCode()` sums identity hashes and so varies between runs (`490528984`, then `1340971164`), which means the `equals`/`hashCode` agreement breaks too.

The javadoc at `:650-654` reserves the right to break *symmetry* as well, but that did not reproduce for the obvious two-map shapes: with the same key reference on both sides both directions return `true`, and with `equals`-not-`==` keys at equal sizes both return `false`. Reflexivity always holds, because `equals` starts with `if (o == this) return true` at `:661-662`. And the contract is fully honoured *among* `IdentityHashMap` instances, via the dedicated branch at `:663-673` that reads the other map's `table` directly.

</details>

**Q6.** Give a concrete case where a `HashSet` cannot substitute for `Collections.newSetFromMap(new IdentityHashMap<>())`.

<details><summary>Answer</summary>

Traversing a graph that contains two distinct nodes which are `equals` to each other. Real output from the chain `a → b → aPrime` where `aPrime.equals(a)` but `aPrime != a`: the identity set visits 3 nodes, the `HashSet` visits 2 — it decided `aPrime` was already seen and dropped it. In a deep-copy that yields a structurally wrong output graph; in a cycle detector it is a false positive. A second, sharper case: if the node's `equals`/`hashCode` recurse into neighbours, calling them on a *cyclic* graph stack-overflows. `IdentityHashMap` never invokes user code on a key — only `System.identityHashCode` and `==` — so it is immune. This is why the javadoc names "topology-preserving object graph transformations" as the typical use at `:56-60`.

</details>

**Q7.** Why does `Collections.newSetFromMap` insist the backing map be empty?

<details><summary>Answer</summary>

`Collections.java:5904-5905`: `if (! map.isEmpty()) throw new IllegalArgumentException("Map is non-empty");`. `SetFromMap` represents membership as "the key is present, mapped to `Boolean.TRUE`". A pre-existing mapping — especially one whose value is `Boolean.FALSE` or `null` — would appear as a set member with semantics nobody can reason about, and `SetFromMap` has no way to normalise it without an O(n) scan the constructor is not entitled to perform. The check also doubles as the null check on `map`, which is why the source comments it `// implicit null check`. Measured: `caught: IllegalArgumentException: Map is non-empty`.

</details>

**Q8.** Roughly how much heap does an `IdentityHashMap` mapping cost versus a `HashMap` mapping, and show the arithmetic?

<details><summary>Answer</summary>

About 12 bytes versus about 37, so roughly 3.1x cheaper, with 4-byte compressed-oop references. `IdentityHashMap`: the table is `2 * capacity` slots × 4 B = `8 * capacity` bytes, and at the 2/3 load factor it holds about `0.667 * capacity` mappings, giving `8 / 0.667 = 12 B` per mapping — and there is no per-entry object at all. `HashMap`: a `Node` is a 12-byte header plus `int hash`, `K key`, `V value`, `Node next` = 28 B, padded to 32 B; plus the `Node[]` slot at `4 / 0.75 = 5.3 B` per mapping; total ~37 B. Quote the ratio, not timings — the memory win is arithmetic and certain, whereas the *speed* win is workload-dependent and the javadoc only claims it "for many Java implementations and operation mixes" at `:133-135`.

</details>

---

## Open questions

- **Unverified:** which JDK release introduced `put`'s `retryAfterResize` labelled-loop form and the `s + (s << 1)` forward-looking threshold. The class is `@since 1.4` (`:147`) and the constants' javadoc has clearly been stable a long time, but only the JDK 21 source was available here; the JDK 8 and JDK 11 sources were not checked, so no claim is made about when the current `put` shape landed. Settling it needs a diff of `IdentityHashMap.java` across `jdk8u`, `jdk11u` and `jdk21u`.

---

**Leaves covered:** 3.11.4–3.11.7 (4 leaves)
**Leaves deferred:** none
**Diagrams included:** none
**Target version:** Java 21 LTS
**Lines:** 800
