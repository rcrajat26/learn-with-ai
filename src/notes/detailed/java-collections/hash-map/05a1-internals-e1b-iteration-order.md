# 02 Java Collections — `HashMap` — INTERNALS (§3.6 `HashMap` source walk — iteration order)

**Target version: Java 21 LTS.** | [Index](../00-index.md)
Previous: [hash-map/05a-internals-e1-removal-and-iteration-order.md](05a-internals-e1-removal-and-iteration-order.md) · Next: [hash-map/05b-internals-e2-views-hooks-and-hashtable.md](05b-internals-e2-views-hooks-and-hashtable.md)

The previous file showed that a `HashMap`'s table array can only ever grow. This one is
about the other consequence of that array: because a key's position in it is a function of
its length, every growth event reshuffles the order in which you see your entries.

All measurements on this page were run on JDK 21.0.7+8-LTS-245 (macOS, aarch64).

---

## Iteration order — deterministic, unspecified, and changed by resize

**Mental model.** `HashMap` iteration is neither "random" nor "insertion order". It is
**array-scan order**: walk slots `0, 1, 2, …` in ascending index, and within each occupied
slot follow the `next` chain to its end. That is the entire algorithm. Everything surprising
about it follows from one fact — a key's slot is `hash & (capacity - 1)`, a function of the
*capacity*, and the capacity changes.

**Why it exists.** There is no ordering machinery because ordering costs memory on every
entry, forever, for a guarantee most callers do not need. Scanning the table is the cheapest
possible traversal: no auxiliary structure, no extra field per node, O(capacity + size).
Insertion order would require a second linked list threaded through every entry — which is
precisely what `LinkedHashMap` is, at two extra references (+16 bytes with compressed oops)
per node.

**When to reach for it, and when not.** Iterate a `HashMap` when you need to visit every
entry and genuinely do not care in what sequence — aggregation, bulk validation, building a
`Set` of values. Do not iterate one when the *order* is part of the output: a serialised
payload, a rendered list, a log line someone will diff, anything you assert on in a test. The
siblings that win there are `LinkedHashMap` (encounter order, +16 bytes/entry) and `TreeMap`
(sorted order, O(log n) per operation instead of O(1)). That is the trade in one line: O(1)
lookup, **but** no ordering guarantee at all, **and** the escape hatch costs either memory or
asymptotics.

**Mechanism — the source.** The whole of iteration order is nine lines of constructor:

```java
    abstract class HashIterator {
        Node<K,V> next;        // next entry to return
        Node<K,V> current;     // current entry
        int expectedModCount;  // for fast-fail
        int index;             // current slot

        HashIterator() {
            expectedModCount = modCount;
            Node<K,V>[] t = table;
            current = next = null;
            index = 0;
            if (t != null && size > 0) { // advance to first entry
                do {} while (index < t.length && (next = t[index++]) == null);
            }
        }
```
— `java.base/java/util/HashMap.java`, JDK 21, line 1581. (leaf 3.6.42)

and one line inside `nextNode()` that repeats the same slot scan whenever a chain runs out:

```java
            if ((next = (current = e).next) == null && (t = table) != null) {
                do {} while (index < t.length && (next = t[index++]) == null);
            }
```
— `java.base/java/util/HashMap.java`, JDK 21, line 1608 (inside `nextNode()`, which begins at
line 1601). (leaf 3.6.42)

`index` only ever increases; there is no ordering state anywhere in the class. Note the cost
shape this implies: the scan visits *every* slot, occupied or not, so iterating a map of 3
entries in a table of 16,777,216 costs 16.7 million array reads. The high-water table that
retained memory in
[05a-internals-e1-removal-and-iteration-order.md](05a-internals-e1-removal-and-iteration-order.md)
also makes iteration slow long after the spike is over.

### Three properties, usually collapsed into one wrong sentence

**(1) Deterministic.** For a fixed sequence of operations on a fixed JDK build, the order is
reproducible run after run. `HashMap` has no per-JVM randomisation of any kind — `hash()`
(line 336) is a pure function of `key.hashCode()`. Contrast the immutable collections:
`Set.of` and `Map.of` mix a `SALT32L` value derived from `System.nanoTime()` at class
initialisation, so their iteration order deliberately differs **on every JVM run**. See
[../immutable-collections/04-internals-immutable-collections.md](../immutable-collections/04-internals-immutable-collections.md).
Two map families in `java.util`, one reproducible and one deliberately not — that contrast is
the most useful thing on this page, because it shows the JDK enforcing at runtime the very
non-guarantee that `HashMap` only documents.

**(2) Unspecified.** From the class javadoc:

> This class makes no guarantees as to the order of the map; in particular, it does not
> guarantee that the order will remain constant over time.

— `java.base/java/util/HashMap.java`, JDK 21, lines 45–47 (class javadoc). (leaf 3.6.42)

Deterministic is not the same as guaranteed. The JDK may change the algorithm in any release,
and did: Java 7 transferred bins with head insertion and so reversed each chain on every
resize; Java 8 replaced that with the tail-appending lo/hi split. Same map, same insertions,
different order across those two versions.

**(3) Changes on resize.** When capacity doubles, a key's slot becomes either `j` or
`j + oldCap`, so keys that shared a slot interleave differently and the scan visits them in a
new order. This is the property worth proving.

```java
import java.util.HashMap;
import java.util.Map;

public class OrderReshuffle {
    public static void main(String[] args) {
        String[] keys = {
            "alpha", "bravo", "charlie", "delta", "echo", "foxtrot", "golf",
            "hotel", "india", "juliet", "kilo", "lima", "mike", "november",
            "oscar", "papa", "quebec", "romeo", "sierra", "tango"
        };
        Map<String, Integer> map = new HashMap<>();
        for (int i = 0; i < keys.length; i++) {
            map.put(keys[i], i);
            System.out.printf("put #%-2d size=%2d -> %s%n", i + 1, map.size(), map.keySet());
        }
    }
}
```

Real output, JDK 21.0.7:

```
put #1  size= 1 -> [alpha]
put #2  size= 2 -> [bravo, alpha]
put #3  size= 3 -> [bravo, alpha, charlie]
put #4  size= 4 -> [bravo, alpha, delta, charlie]
put #5  size= 5 -> [bravo, alpha, delta, echo, charlie]
put #6  size= 6 -> [bravo, foxtrot, alpha, delta, echo, charlie]
put #7  size= 7 -> [bravo, golf, foxtrot, alpha, delta, echo, charlie]
put #8  size= 8 -> [bravo, golf, foxtrot, alpha, delta, hotel, echo, charlie]
put #9  size= 9 -> [bravo, golf, foxtrot, alpha, delta, hotel, echo, india, charlie]
put #10 size=10 -> [bravo, golf, juliet, foxtrot, alpha, delta, hotel, echo, india, charlie]
put #11 size=11 -> [bravo, golf, juliet, kilo, foxtrot, alpha, delta, hotel, echo, india, charlie]
put #12 size=12 -> [bravo, golf, juliet, kilo, lima, foxtrot, alpha, delta, hotel, echo, india, charlie]
put #13 size=13 -> [lima, foxtrot, mike, delta, echo, india, bravo, golf, juliet, kilo, alpha, hotel, charlie]
put #14 size=14 -> [november, lima, foxtrot, mike, delta, echo, india, bravo, golf, juliet, kilo, alpha, hotel, charlie]
put #15 size=15 -> [november, oscar, lima, foxtrot, mike, delta, echo, india, bravo, golf, juliet, kilo, alpha, hotel, charlie]
put #16 size=16 -> [november, oscar, lima, foxtrot, mike, delta, echo, india, bravo, golf, juliet, kilo, papa, alpha, hotel, charlie]
put #17 size=17 -> [november, oscar, lima, foxtrot, mike, delta, echo, india, quebec, bravo, golf, juliet, kilo, papa, alpha, hotel, charlie]
put #18 size=18 -> [romeo, november, oscar, lima, foxtrot, mike, delta, echo, india, quebec, bravo, golf, juliet, kilo, papa, alpha, hotel, charlie]
put #19 size=19 -> [romeo, november, oscar, lima, foxtrot, mike, sierra, delta, echo, india, quebec, bravo, golf, juliet, kilo, papa, alpha, hotel, charlie]
put #20 size=20 -> [romeo, november, oscar, lima, foxtrot, mike, sierra, delta, echo, india, quebec, bravo, golf, juliet, kilo, papa, alpha, hotel, charlie, tango]
```

**Put #13 is the reshuffle.** Up to #12 each new key is spliced into an otherwise stable order
and `bravo` leads throughout. At #13, `++size > threshold` (13 > 12) with capacity 16, so
`resize()` doubles the table to 32 and the order goes from `[bravo, golf, juliet, …]` to
`[lima, foxtrot, mike, …]`, with `bravo` now seventh. Nothing was removed, and the caller
reordered nothing — the same twelve keys simply landed in different slots of a longer array.
That one transcript is the whole leaf.

**Diagram.** None on this page. A slot-by-slot before/after of that capacity-16 → 32 step
would be the picture; the equivalent split diagram already exists in
[03a-internals-c1-lo-hi-split.md](03a-internals-c1-lo-hi-split.md).

**Pitfall:** *"`HashMap` iteration order is stable, so I can rely on it."*
**Symptoms, two real ones.** (a) A unit test asserts on `map.toString()` or on
`new ArrayList<>(map.keySet())` and passes green for a year, until a colleague adds a
thirteenth entry and the resize reshuffles everything — a test failure with no code change in
the class under test. (b) Two nodes of a distributed system serialise the same logical map to
JSON, one on JDK 8 and one on JDK 21, or one presized and one grown; the key orders differ,
and a downstream HMAC over the serialised body fails to verify.
**Fix:** `LinkedHashMap` for encounter order (+2 references per entry for the `before`/`after`
pointers — see [../linked-hash-map/01-internals.md](../linked-hash-map/01-internals.md)),
`TreeMap` for sorted order, or an explicit sort at the boundary (`new TreeMap<>(map)`, or a
`LinkedHashMap` collector over a sorted stream).

### Within a bin, order is chain order

Since Java 8 the lo/hi split appends with tail insertion, so *relative* order within a bin
survives a resize (leaf 3.6.26,
[03a-internals-c1-lo-hi-split.md](03a-internals-c1-lo-hi-split.md)). Java 7's head-insertion
transfer reversed each bin on every resize. So "the order changed on resize" was true in both
eras, for different reasons — in Java 7 the bins reversed *as well as* re-scattered.

### A treeified bin iterates in neither tree order nor insertion order

`HashIterator` walks `next`, and the linked overlay survives treeification, so iteration stays
linear even over a red-black bin. But the overlay is no longer insertion-ordered:
`putTreeVal` splices a new node next to its tree *parent* rather than at the tail, and
`moveRootToFront` hauls the current root to the head of the bin's chain. Measured on JDK
21.0.7 in [04-internals-d-treeify.md](04-internals-d-treeify.md): inserting keys 0..8 into a
single treeified bin iterates `3 0 1 2 4 5 6 7 8`. The corrected rule: **insertion order up to
treeification, thereafter splice order with the current root pulled to the front — never
sorted.**

### `Integer` keys look sorted, and that is where the false belief is born

`Integer.hashCode()` returns the value itself; `hash()` spreads it as `h ^ (h >>> 16)`, which
is the identity for any non-negative value below 65,536; and for a value below the capacity,
`hash & (n - 1)` equals the value. So the key *is* its own slot index, and array-scan order
*is* ascending numeric order. The illusion holds until a value reaches the capacity or goes
negative.

```java
import java.util.HashMap;
import java.util.Map;

public class IntegerIllusion {

    static int spread(Object key) {
        int h = key.hashCode();
        return h ^ (h >>> 16);
    }

    public static void main(String[] args) {
        Map<Integer, String> map = new HashMap<>();
        for (int i = 0; i <= 9; i++) map.put(i, "v" + i);
        System.out.println("0..9 (capacity 16)      : " + map.keySet());

        map.put(100, "v100");
        System.out.println("after put(100)          : " + map.keySet());

        map.put(-1, "v-1");
        System.out.println("after put(-1)           : " + map.keySet());

        System.out.println();
        System.out.printf("slot of 100 in cap 16   : %d  (spread=%d)%n", spread(100) & 15, spread(100));
        System.out.printf("slot of -1  in cap 16   : %d  (spread=%d)%n", spread(-1) & 15, spread(-1));

        Map<Integer, String> big = new HashMap<>();
        for (int i = 0; i <= 20; i++) big.put(i, "v" + i);
        System.out.println();
        System.out.println("0..20 (resized to 64)   : " + big.keySet());
    }
}
```

Real output, JDK 21.0.7:

```
0..9 (capacity 16)      : [0, 1, 2, 3, 4, 5, 6, 7, 8, 9]
after put(100)          : [0, 1, 2, 3, 4, 100, 5, 6, 7, 8, 9]
after put(-1)           : [0, -1, 1, 2, 3, 4, 100, 5, 6, 7, 8, 9]

slot of 100 in cap 16   : 4  (spread=100)
slot of -1  in cap 16   : 0  (spread=-65536)

0..20 (resized to 64)   : [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20]
```

`100 & 15 == 4`, so `100` lands in slot 4 *behind* the key `4` and prints between `4` and `5`.
`-1` spreads to `-1 ^ 0xFFFF == 0xFFFF0000 == -65536`, and `-65536 & 15 == 0`, so it lands in
slot 0 behind `0`. Note the last line: `0..20` still prints sorted, because after the resize
to capacity 64 every key is still below the capacity. The illusion survives growth and dies
only on range — which is exactly why it survives long enough to become a belief.

**Pitfall:** *"the order is random, so it is safe to rely on it being unpredictable."*
**Symptom:** `HashMap` used as a poor man's shuffle, or a security argument that an attacker
cannot know which bin a key lands in. Both fail: `HashMap` has no per-JVM salt, so given the
keys and the capacity the slot of every key is computable in one line,
`(h ^ (h >>> 16)) & (n - 1)`, which is exactly the primitive an algorithmic-complexity
attacker needs. **Fix:** `Collections.shuffle` with a `SecureRandom` for shuffling; for the
adversarial case see
[04c-internals-d3-collision-dos.md](04c-internals-d3-collision-dos.md).

**Interview:** "Is `HashMap` iteration order random?" — No. It is deterministic array-scan
order, reproducible for a given insertion sequence and capacity; it is *unspecified*, which is
a different claim; and it changes when the table resizes.

> **`HashMap` iteration order** is ascending table-slot order, and within each slot the bin's
> `next`-chain order — fully determined by the keys' hashes and the current capacity,
> reproducible across runs, guaranteed by nothing, and altered by every resize.

### Version note — JDK 8 vs JDK 21

Diffed directly against `/tmp/jdk8src/java/util/HashMap.java`:

| Member | JDK 8 line | JDK 21 line | Difference |
|---|---|---|---|
| `HashIterator` ctor + `nextNode()` | 1421 | 1581 | **Byte-for-byte identical.** |
| `HashIterator.remove()` | 1454 | 1614 | Differs. JDK 8 recomputes `hash(key)`; JDK 21 reuses the node's cached `p.hash`. Same behaviour, one fewer hash call per removal. |
| `removeNode` | 813 | 819 | Byte-for-byte identical (covered in [05a](05a-internals-e1-removal-and-iteration-order.md)). |
| `clear()` | 858 | 864 | Byte-for-byte identical (covered in [05a](05a-internals-e1-removal-and-iteration-order.md)). |

So the iteration mechanism itself has not changed since Java 8. The version trap on this page
is Java **7** versus Java 8 — head-insertion transfer versus the tail-appending lo/hi split —
not 8 versus 21.

---

## Pitfalls

### Assuming `HashMap` iteration order is insertion order

**Wrong**
```java
Map<String, Integer> m = new HashMap<>();
for (String k : List.of("alpha","bravo","charlie","delta","echo","foxtrot",
                        "golf","hotel","india","juliet","kilo","lima","mike")) {
    m.put(k, k.length());
}
System.out.println(m.keySet());
// [lima, foxtrot, mike, delta, echo, india, bravo, golf, juliet, kilo, alpha, hotel, charlie]
```
Twelve keys iterate in one order; the thirteenth triggers a resize and the whole order
changes.

**Right**
```java
Map<String, Integer> m = new LinkedHashMap<>();
for (String k : List.of("alpha","bravo","charlie","delta","echo","foxtrot",
                        "golf","hotel","india","juliet","kilo","lima","mike")) {
    m.put(k, k.length());
}
System.out.println(m.keySet());
// [alpha, bravo, charlie, delta, echo, foxtrot, golf, hotel, india, juliet, kilo, lima, mike]
```
`LinkedHashMap` maintains an explicit doubly-linked list across all entries, so iteration is
insertion order by contract and is unaffected by resize. Cost: two extra references per entry.

**Why people believe it:** small maps of small `Integer` keys, and maps that never cross a
threshold, do iterate in a stable and often sorted-looking order — for long enough that it
reads as a guarantee.

### Assuming `HashMap` order is unpredictable enough to be a shuffle

**Wrong**
```java
Map<String, Integer> bag = new HashMap<>();
for (int i = 0; i < 10; i++) bag.put("player" + i, i);
List<String> drawOrder = new ArrayList<>(bag.keySet());  // "randomised"
// Identical on every run, on every machine, on every JVM start.
```

**Right**
```java
List<String> drawOrder = new ArrayList<>(bag.keySet());
Collections.shuffle(drawOrder, new SecureRandom());
```

**Why people believe it:** the order *looks* scrambled relative to insertion, and the javadoc
says "no guarantees" — which people read as "arbitrary at runtime" rather than "arbitrary
across releases". `Set.of`/`Map.of` really do vary per JVM run via `SALT32L`; `HashMap` never
does.

---

## Cheat sheet

| Question | Answer |
|---|---|
| Iteration order | Ascending slot index, then each bin's `next`-chain order. `index` only increases. |
| Where it lives | `HashIterator` ctor (line 1581) + the slot scan in `nextNode()` (line 1608). Nine lines total. |
| Cost of iteration | O(capacity + size) — every slot is visited, occupied or not. |
| Deterministic? | Yes, per JDK build. `hash()` (line 336) is pure; no salt anywhere in `HashMap`. |
| Guaranteed? | No. Javadoc lines 45–47: "makes no guarantees as to the order… not… constant over time." |
| Randomised per JVM run? | Not `HashMap`. `Set.of`/`Map.of` are, via `SALT32L` from `System.nanoTime()`. |
| When does order change? | On every resize. First one at the 13th insert with defaults (capacity 16, threshold 12). |
| What resize does to a slot | Key moves to `j` or `j + oldCap`; keys that shared a slot now interleave differently. |
| Order inside a plain bin | Chain order. Tail-append since Java 8, so relative order survives a resize. |
| Order inside a treeified bin | Insertion order until treeify, then splice order with the root pulled to the head. Never sorted. |
| Java 7 vs 8 | Java 7 head-insertion transfer reversed every bin on resize; Java 8 tail-appends. |
| Why small `Integer` keys look sorted | `hashCode()` is the value; spread is identity below 65,536; `v & (n-1) == v` below capacity. |
| Where the illusion breaks | Key ≥ capacity (`100` → slot 4) or negative (`-1` → spread `-65536` → slot 0). |
| Need order? | `LinkedHashMap` (encounter, +2 refs/entry), `TreeMap` (sorted, O(log n)), or sort at the boundary. |
| Changed since JDK 8? | `HashIterator` ctor and `nextNode()`: identical. Only `remove()` differs (cached `p.hash`). |

---

## Self-test

**Q1.** Describe `HashMap` iteration order in one sentence, precisely enough that someone could reimplement it.

<details><summary>Answer</summary>

Scan the table array from index 0 upward; at each non-`null` slot, emit every node along its
`next` chain in chain order before advancing to the next slot. That is exactly what the
`HashIterator` constructor and the two-line slot scan inside `nextNode()` do; `index` is
monotonically increasing and there is no other ordering state.

</details>

**Q2.** Given `new HashMap<>()` and thirteen distinct `String` keys inserted one at a time, at which insertion does the order change wholesale, and why?

<details><summary>Answer</summary>

The thirteenth. Default capacity 16 and load factor 0.75 give `threshold = 12`; `putVal`
resizes when `++size > threshold`, i.e. when size reaches 13. Doubling to capacity 32 changes
`hash & (n - 1)` for roughly half the keys — each moves from slot `j` to either `j` or
`j + 16` — so the ascending-slot scan visits them in a different order.

</details>

**Q3.** `HashMap` iteration is deterministic; `Set.of(...)` iteration is not. Explain the difference and why the JDK does it.

<details><summary>Answer</summary>

`HashMap.hash()` is a pure function of `key.hashCode()` with no randomisation, so the same
insertions on the same JDK build always produce the same order. The immutable collections mix
a per-JVM `SALT32L` derived from `System.nanoTime()` at class initialisation, deliberately
varying iteration order between runs so callers cannot accidentally come to depend on it.
`HashMap` is deterministic but *unspecified*; `Set.of`/`Map.of` enforce the unspecification at
runtime.

</details>

**Q4.** A map of `Integer` keys 0..9 iterates `[0,1,…,9]`. Is that sorted order? What breaks it?

<details><summary>Answer</summary>

No — it is a coincidence of array-scan order. `Integer.hashCode()` returns the value, the
spread `h ^ (h >>> 16)` is the identity for any non-negative value below 65,536, and
`v & (capacity - 1) == v` whenever `v < capacity`, so key `v` sits in slot `v`. It breaks as
soon as a key is ≥ capacity (`100` in a capacity-16 table lands in slot 4 and prints between
4 and 5) or negative (`-1` spreads to `-65536`, slot 0, printing right after `0`). It does
*not* break merely on resize: `0..20` in a capacity-64 table still prints sorted.

</details>

**Q5.** Two services serialise the same logical `HashMap` to JSON and a downstream signature check fails. Diagnose and fix.

<details><summary>Answer</summary>

The two maps have different capacities — different presizing, a different insertion history,
or different JDK generations — so their array-scan orders differ, and the JSON key order
differs even though the maps are `equals()`. Fix by imposing order at the boundary: serialise
from a `TreeMap<>(map)` or a `LinkedHashMap` built over a sorted stream, or use a canonical
JSON form. Never sign a serialisation whose field order comes from a `HashMap`.

</details>

**Q6.** Does a treeified bin iterate in sorted order? In insertion order?

<details><summary>Answer</summary>

Neither. `HashIterator` walks the linked `next` overlay, which survives treeification, so
iteration is linear rather than a tree traversal — but the overlay is no longer insertion
order, because `putTreeVal` splices each new node next to its tree parent and
`moveRootToFront` moves the current root to the head of the chain. Measured on JDK 21.0.7,
keys 0..8 in one treeified bin iterate `3 0 1 2 4 5 6 7 8`.

</details>

**Q7.** Why is iterating a nearly empty map that once held ten million entries slow?

<details><summary>Answer</summary>

Iteration is O(capacity + size), not O(size): the scan advances `index` past every slot,
`null` or not. The table never shrinks, so it is still `1 << 24 = 16,777,216` slots, and
walking it costs 16.7 million array reads regardless of how few entries remain. Same root
cause as the memory retention in
[05a-internals-e1-removal-and-iteration-order.md](05a-internals-e1-removal-and-iteration-order.md),
and the same fix: replace the map rather than clearing it.

</details>

**Q8.** Is it safe to treat `HashMap` order as unpredictable — for a shuffle, or as a defence against an attacker choosing colliding keys?

<details><summary>Answer</summary>

No, on both counts. The order is fully determined by the keys and the capacity, with no
per-JVM salt, so it is identical on every run and every machine; as a shuffle it produces the
same "random" sequence forever. And an attacker who knows the key type can compute
`(h ^ (h >>> 16)) & (n - 1)` for any candidate key and deliberately drive them all into one
bin. Use `Collections.shuffle` with a `SecureRandom` for the first, and see
[04c-internals-d3-collision-dos.md](04c-internals-d3-collision-dos.md) for the second.

</details>

---

**Leaves covered:** 3.6.42 (1 leaf)
**Leaves deferred:** none
**Diagrams included:** none new — the sizing arithmetic (D-99) is embedded in [05-internals-e-sizing-and-iteration.md](05-internals-e-sizing-and-iteration.md)
**Target version:** Java 21 LTS
**Lines:** 471
