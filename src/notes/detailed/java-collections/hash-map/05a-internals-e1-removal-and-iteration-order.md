# 02 Java Collections — `HashMap` — INTERNALS (§3.6 `HashMap` source walk — `removeNode`, `clear()`, and why a map never gives the array back)

**Target version: Java 21 LTS.** | [Index](../00-index.md)
Previous: [hash-map/05-internals-e-sizing-and-iteration.md](05-internals-e-sizing-and-iteration.md) · Next: [hash-map/05a1-internals-e1b-iteration-order.md](05a1-internals-e1b-iteration-order.md)

A `HashMap`'s table array is the one piece of state the public API can never shrink. This
file is about what that costs, and about the gap between "the map is empty" and "the memory
is back". Iteration order — the other consequence of the same array — is in
[05a1-internals-e1b-iteration-order.md](05a1-internals-e1b-iteration-order.md).

All measurements on this page were run on JDK 21.0.7+8-LTS-245 (macOS, aarch64).

---

## `removeNode` — removal unlinks a node, and never shrinks the table

**Mental model.** The table is a **high-water mark**, not a working set. It grows to fit the
largest number of entries the map has ever *simultaneously* held, and it never gives that
array back for the lifetime of the map object. `remove` unlinks one node from one chain.
`clear` writes `null` into every slot. Neither touches `table.length`. The only way to
reclaim the array is to stop referencing the map.

**Why it exists this way.** Shrinking would mean allocating a smaller array and rehashing
every surviving entry — the full cost of `resize()`, paid on a `remove()` the caller expects
to be O(1) — and a workload oscillating around a threshold would thrash between two
capacities, rehashing on alternate calls. The design keeps removal unconditionally cheap and
pushes the memory decision onto the caller. The cost: the caller has no API to express it.

**When it bites.** Peak size much larger than steady-state size, with the map outliving the
peak — caches, session maps, pooled per-request accumulators. It does not bite when the map
refills to roughly the same size each cycle; there, keeping the table beats reallocating it.
The sibling that wins where `HashMap` loses is a bounded cache (Caffeine, or a
`LinkedHashMap` with `removeEldestEntry`), which never lets the high-water mark form.

**Mechanism — the source.**

```java
    final Node<K,V> removeNode(int hash, Object key, Object value,
                               boolean matchValue, boolean movable) {
        Node<K,V>[] tab; Node<K,V> p; int n, index;
        if ((tab = table) != null && (n = tab.length) > 0 &&
            (p = tab[index = (n - 1) & hash]) != null) {
            Node<K,V> node = null, e; K k; V v;
            if (p.hash == hash &&
                ((k = p.key) == key || (key != null && key.equals(k))))
                node = p;
            else if ((e = p.next) != null) {
                if (p instanceof TreeNode)
                    node = ((TreeNode<K,V>)p).getTreeNode(hash, key);
                else {
                    do {
                        if (e.hash == hash &&
                            ((k = e.key) == key ||
                             (key != null && key.equals(k)))) {
                            node = e;
                            break;
                        }
                        p = e;
                    } while ((e = e.next) != null);
                }
            }
            if (node != null && (!matchValue || (v = node.value) == value ||
                                 (value != null && value.equals(v)))) {
                if (node instanceof TreeNode)
                    ((TreeNode<K,V>)node).removeTreeNode(this, tab, movable);
                else if (node == p)
                    tab[index] = node.next;
                else
                    p.next = node.next;
                ++modCount;
                --size;
                afterNodeRemoval(node);
                return node;
            }
        }
        return null;
    }
```
— `java.base/java/util/HashMap.java`, JDK 21, line 819. (leaf 3.6.41)

Four things to pull out of it.

**The search half is `getNode` duplicated, with one addition.** The loop keeps `p` as the
**predecessor** of the found node (`p = e;` at the bottom of the `do`/`while`), because a
singly-linked chain cannot unlink a node without one. That extra carried field is the whole
reason this is a near-copy of `getNode` rather than a call to it — on the hottest path in the
class, returning both node and predecessor would need an allocation or an out-parameter.

**The unlink is a three-way branch, and it is three lines.** `removeTreeNode` for a tree bin;
`tab[index] = node.next` when the victim is the bin head; `p.next = node.next` otherwise.
Exactly one array write, and only in the head case. Note what is absent: no length check, no
compaction, no reallocation. `tab.length` is never written, only read once for indexing.

**`matchValue` separates `remove(key)` from `remove(key, value)`.** `remove(Object)` passes
`false` and deletes on a key match alone; the two-argument `Map.remove(key, value)` passes
`true` and additionally requires
`(v = node.value) == value || (value != null && value.equals(v))` — identity-before-`equals`,
the same shape as the key comparison a few lines up, and for the same reason: the `==`
short-circuit avoids a virtual call when the caller passes the very object it got out of the
map.

**The nodes really do become garbage.** This is the half that "removal never shrinks" tends
to swallow. Each unlinked `Node` — 32 bytes with compressed oops (12-byte header, `int hash`,
three references, padded to 8) — is unreachable the moment the chain is spliced, and its key
and value go with it if nothing else holds them. Removal frees per-entry memory. What it
never frees is the `Node[]` array.

**Diagram.** None on this page. A picture of one chain before and after the splice would
help; the equivalent chain surgery is drawn in
[03-internals-c-resize.md](03-internals-c-resize.md).

**Supporting fact — `movable`.** `remove()` passes `true`; `HashIterator.remove()` passes
`false`. The flag reaches `removeTreeNode`, telling it whether it may call `moveRootToFront`.
An iterator forbids it because the iterator holds a cursor inside the bin's linked overlay,
and relinking the tree root to the head of that chain would move a node the iterator has
*already returned* back in front of the cursor, producing a duplicate. That single flag is
where the class comment's remark about the tree root sometimes not being the bin head comes
from. See [04-internals-d-treeify.md](04-internals-d-treeify.md).

**Supporting fact — `reinitialize()`.** The class *can* drop its table:

```java
    void reinitialize() {
        table = null;
        entrySet = null;
        keySet = null;
        values = null;
        modCount = 0;
        threshold = 0;
        size = 0;
    }
```
— `java.base/java/util/HashMap.java`, JDK 21, line 1930. (leaf 3.6.41)

It is the only method in the class that assigns `table = null`, and it is package-private.
It has exactly two call sites: `clone()` at line 1472 (on the freshly cloned result, before
`putMapEntries` refills it) and `readObject()` at line 1529. No public API path reaches it.
The capability exists; it is simply not exposed.

## `clear()` — what it frees and what it keeps

```java
    public void clear() {
        Node<K,V>[] tab;
        modCount++;
        if ((tab = table) != null && size > 0) {
            size = 0;
            for (int i = 0; i < tab.length; ++i)
                tab[i] = null;
        }
    }
```
— `java.base/java/util/HashMap.java`, JDK 21, line 864. (leaf 3.6.41)

`size = 0`, then a `null`-fill of the existing array. `table` is not reassigned; `threshold`
is not touched. `clear()` is **O(capacity), not O(size)** — clearing an empty map that once
held ten million entries still walks 16 million slots.

### The arithmetic, worked  `[NUM]`

The syllabus phrases this as "10M entries still owns a 16M-slot array". The number is right,
but the derivation is the point, because the jump from 13.3M to 16.7M is `tableSizeFor`.

- 10,000,000 entries at load factor 0.75 need `threshold >= 10,000,000`, so
  `capacity >= ceil(10,000,000 / 0.75) = 13,333,334`.
- `tableSizeFor` rounds up to the next power of two: **`1 << 24` = 16,777,216**.
  (`1 << 23` = 8,388,608 gives threshold 6,291,456 — far too small.)
- Resulting `threshold = 16,777,216 × 0.75 = 12,582,912`.
- Array cost with compressed oops (the default on heaps below 32 GB): 16,777,216 × 4 bytes
  = **67,108,864 bytes = 64 MiB**, plus a 16-byte array header. Above 32 GB, or with
  `-XX:-UseCompressedOops`, 8 bytes per reference = **134,217,728 bytes = 128 MiB**.
- Entries at peak: 10,000,000 × 32 bytes = 320,000,000 bytes ≈ **305 MiB**. The array is
  therefore 64 / (64 + 305) ≈ **17%** of the map's own footprint, before counting the key and
  value objects themselves.
- After `clear()`: the 305 MiB of nodes is garbage, the **64 MiB array is retained**,
  `size == 0`, `table.length == 16,777,216`, `threshold == 12,582,912`.

**Proof.** Ten million entries needs a large heap, so this runs at *n* = 2,000,000, where the
same arithmetic gives `capacity = ceil(2,000,000 / 0.75) = 2,666,667 → 1 << 22 = 4,194,304`
and an array of 4,194,304 × 4 = 16,777,216 bytes = 16 MiB.

```java
import java.lang.reflect.Field;
import java.util.HashMap;
import java.util.Map;

public class ClearRetention {

    static int tableLength(Map<?, ?> map) throws Exception {
        Field f = HashMap.class.getDeclaredField("table");
        f.setAccessible(true);
        Object[] tab = (Object[]) f.get(map);
        return tab == null ? -1 : tab.length;
    }

    static int threshold(Map<?, ?> map) throws Exception {
        Field f = HashMap.class.getDeclaredField("threshold");
        f.setAccessible(true);
        return f.getInt(map);
    }

    static long nonNullSlots(Map<?, ?> map) throws Exception {
        Field f = HashMap.class.getDeclaredField("table");
        f.setAccessible(true);
        Object[] tab = (Object[]) f.get(map);
        if (tab == null) return 0;
        long c = 0;
        for (Object o : tab) if (o != null) c++;
        return c;
    }

    public static void main(String[] args) throws Exception {
        final int n = 2_000_000;
        Map<Integer, Integer> map = new HashMap<>();
        for (int i = 0; i < n; i++) map.put(i, i);

        System.out.println("n inserted       = " + n);
        System.out.println("size             = " + map.size());
        System.out.println("table.length     = " + tableLength(map));
        System.out.println("threshold        = " + threshold(map));
        System.out.println("occupied slots   = " + nonNullSlots(map));
        System.out.println("array bytes @4   = " + (long) tableLength(map) * 4);

        map.clear();

        System.out.println("--- after clear() ---");
        System.out.println("size             = " + map.size());
        System.out.println("table.length     = " + tableLength(map));
        System.out.println("threshold        = " + threshold(map));
        System.out.println("occupied slots   = " + nonNullSlots(map));
        System.out.println("array bytes @4   = " + (long) tableLength(map) * 4);
    }
}
```

Run with `java -Xmx2g --add-opens java.base/java.util=ALL-UNNAMED ClearRetention`. Real
output, JDK 21.0.7:

```
n inserted       = 2000000
size             = 2000000
table.length     = 4194304
threshold        = 3145728
occupied slots   = 2000000
array bytes @4   = 16777216
--- after clear() ---
size             = 0
table.length     = 4194304
threshold        = 3145728
occupied slots   = 0
array bytes @4   = 16777216
```

`size` went to zero. `table.length` and `threshold` did not move. Sixteen mebibytes of
`Node[]`, every slot `null`, still reachable from the map reference.

**Pitfall:** *"`map.clear()` releases the map's memory."*
**Symptom:** a long-lived cache or session map that is dutifully cleared every cycle and
still shows tens of megabytes retained in a heap dump, with the dominator being a
`java.util.HashMap$Node[]` that is entirely `null`.
**Fix:** when peak size greatly exceeds steady-state size, *replace* the map —
`map = new HashMap<>()`, or `HashMap.newHashMap(expectedSteadyState)` to presize it — rather
than clearing it. The honest counter-case: if the map refills to the same size next cycle,
`clear()` is the better call, because it avoids reallocating the array and rehashing every
entry back in. The rule is about the peak-to-steady ratio, not about `clear()` being wrong.
For spotting the retained `Node[]` in a heap dump, see
[../cost-and-memory/04-observability.md](../cost-and-memory/04-observability.md).

### Who offers a trim, and who does not

| Type | Shrinks on remove? | Shrinks on `clear()`? | Explicit trim API? | How to actually reclaim |
|---|---|---|---|---|
| `HashMap` | No | No — nulls slots, keeps array | None | Drop the reference; build a new map (`HashMap.newHashMap(n)`) |
| `ArrayList` | No | No — nulls slots, keeps array | `trimToSize()` (`ArrayList.java`, JDK 21, line 199) | Call `trimToSize()`; it `Arrays.copyOf`s down to `size`, or swaps in `EMPTY_ELEMENTDATA` when empty |
| `ArrayDeque` | No | No | None — no `trimToSize` in the class | Drop the reference; build a new deque |
| `StringBuilder` | n/a | n/a | `trimToSize()` (inherited from `AbstractStringBuilder`) | Call `trimToSize()` |

**Insight:** the JDK hands a trim method to the array-backed *sequence* types that already
expose a capacity notion in their own API (`ArrayList`'s `int` constructor and
`ensureCapacity`, `StringBuilder`'s the same) and to nothing else. Hash-based containers hide
capacity entirely — it is a derived quantity, not a property you set — so there is no coherent
place to hang a `trimToSize()` that would not also have to specify a rehash. The absence is a
design consequence, not an oversight.

**Interview:** "A service holds a `HashMap` cache that spikes to 10 million entries once a
day and holds a thousand the rest of the time. What is wrong?" — The table is sized for the
spike for the lifetime of the object, so 64 MiB of `Node[]` is retained 23 hours a day, and
every iteration of the near-empty map scans 16.7 million slots. Replace the map after the
spike instead of clearing it.

> **`removeNode`** unlinks the matching node from its bin — splicing the chain, or delegating
> to `removeTreeNode` — decrements `size`, bumps `modCount`, and returns it: freeing the node
> but never the table array, which `HashMap` retains at its high-water capacity for the life
> of the map, `clear()` included.

### Version note

Diffed directly against `/tmp/jdk8src/java/util/HashMap.java`: `removeNode` (JDK 8 line 813,
JDK 21 line 819) and `clear()` (JDK 8 line 858, JDK 21 line 864) are **byte-for-byte
identical**. Nothing about removal or clearing has changed since Java 8. The one behaviour
worth version-tagging here is `HashMap.newHashMap(int)`, the presizing factory that removes
the `/0.75` arithmetic from caller code — **new in Java 19**; on Java 17 and earlier write
`new HashMap<>((int) (n / 0.75f) + 1)`. See
[05-internals-e-sizing-and-iteration.md](05-internals-e-sizing-and-iteration.md).

---

## Pitfalls

### Assuming `clear()` releases the map's memory

**Wrong**
```java
Map<Long, byte[]> cache = new HashMap<>();
for (long i = 0; i < 2_000_000; i++) cache.put(i, new byte[0]);
cache.clear();
System.out.println(cache.size());   // 0
// ...but a heap dump still shows a live java.util.HashMap$Node[4194304] — 16 MiB of nulls
```

**Right**
```java
Map<Long, byte[]> cache = new HashMap<>();
for (long i = 0; i < 2_000_000; i++) cache.put(i, new byte[0]);
cache = HashMap.newHashMap(1_000);   // old 16 MiB table becomes garbage; new one holds 2048 slots
```
Reassigning drops the only reference to the oversized `Node[]`, so the GC can take it.
`HashMap.newHashMap(n)` (Java 19+) presizes for *n* mappings without the `/0.75` arithmetic.

**Why people believe it:** `clear()` reads as "empty this and give the memory back", and the
sibling collection `ArrayList` really does have a method that hands the array back
(`trimToSize()`) — so the capability feels like it must be there somewhere. It is:
`reinitialize()`, which is package-private and reachable only from `clone()` and
`readObject()`.

### Assuming removal frees nothing

**Wrong**
```java
// "HashMap never shrinks, so removing entries is pointless for memory."
Map<Integer, byte[]> m = new HashMap<>();
for (int i = 0; i < 100_000; i++) m.put(i, new byte[1024]);
// leaving the entries in place "because removing won't help anyway"
```

**Right**
```java
Map<Integer, byte[]> m = new HashMap<>();
for (int i = 0; i < 100_000; i++) m.put(i, new byte[1024]);
m.keySet().removeIf(k -> k % 2 == 0);
// 50,000 Nodes (32 bytes each = 1.6 MB) plus 50,000 byte[1024] payloads (51 MB) are now garbage.
// Only the Node[131072] array — 512 KiB — is retained.
```

**Why people believe it:** "never shrinks" is a statement about `table.length`, and it gets
overread as a statement about the whole map. The payload is almost always far larger than the
array: here 51 MB of values against 512 KiB of table.

---

## Cheat sheet

| Question | Answer |
|---|---|
| Does `remove` shrink the table? | Never. `tab.length` is read once for indexing and never written. |
| Does `clear()` shrink the table? | No. Sets `size = 0`, nulls every slot, keeps the array and `threshold`. |
| Cost of `clear()` | O(capacity), not O(size). |
| Does removal free anything? | Yes — the `Node` (32 bytes, compressed oops) plus key/value if otherwise unreachable. |
| Only method that nulls `table` | `reinitialize()`, line 1930, package-private; call sites `clone()` 1472 and `readObject()` 1529. |
| Table for 10M entries @ 0.75 | `ceil(10M/0.75) = 13,333,334 → 1<<24 = 16,777,216` slots; 64 MiB @ 4-byte oops, 128 MiB @ 8; threshold 12,582,912. |
| Measured at n = 2,000,000 | `table.length = 4,194,304`, `threshold = 3,145,728`, unchanged by `clear()`. |
| How to reclaim | Drop the reference; `map = HashMap.newHashMap(expected)` (Java 19+). |
| `matchValue` | `false` for `remove(k)`, `true` for `remove(k, v)`; value compared `==` then `equals`. |
| `movable` | `true` from `remove()`, `false` from `HashIterator.remove()` — blocks `moveRootToFront`. |
| Why `p` is carried in the loop | Predecessor is required to splice a singly-linked chain; `getNode` cannot supply it. |
| Trim APIs in the JDK | `ArrayList.trimToSize()`, `StringBuilder.trimToSize()`. Not `HashMap`, not `ArrayDeque`. |
| Changed since JDK 8? | `removeNode` (813→819) and `clear()` (858→864): byte-for-byte identical. |

---

## Self-test

**Q1.** A map peaked at 10,000,000 entries. Exactly how large is its table array, and how did you get there?

<details><summary>Answer</summary>

Load factor 0.75 requires `capacity >= ceil(10,000,000 / 0.75) = 13,333,334`. `tableSizeFor`
rounds up to the next power of two, giving `1 << 24 = 16,777,216` slots (`1 << 23` would give
threshold 6,291,456, too small). With compressed oops that array is 16,777,216 × 4 =
67,108,864 bytes = 64 MiB plus a 16-byte header; without compressed oops, 128 MiB.
`threshold` is 12,582,912.

</details>

**Q2.** You call `clear()` on that map. What is freed, what is retained, and what is the cost of the call?

<details><summary>Answer</summary>

Freed: the 10,000,000 `Node` objects (≈305 MiB at 32 bytes each) and any keys and values they
solely referenced. Retained: the 64 MiB `Node[16777216]`, plus `threshold == 12,582,912`.
`size` becomes 0. The call is O(capacity) — it writes `null` into all 16,777,216 slots — so it
is slower than clearing a map that never grew.

</details>

**Q3.** Why is `removeNode`'s search loop a near-copy of `getNode` rather than a call to it?

<details><summary>Answer</summary>

`removeNode` needs the *predecessor* `p` of the found node, because unlinking from a singly
linked chain requires it (`p.next = node.next`). `getNode` returns only the node. Returning
both would need an allocation or an out-parameter on the hottest path in the class, so the
loop is duplicated with `p = e;` carried along.

</details>

**Q4.** `HashIterator.remove()` passes `movable = false`. What breaks if it passed `true`?

<details><summary>Answer</summary>

`true` lets `removeTreeNode` call `moveRootToFront`, which relinks the current red-black tree
root to the head of the bin's linked overlay. The iterator holds a cursor inside that
overlay, so a node it had already returned could be moved back in front of the cursor and
returned a second time.

</details>

**Q5.** `reinitialize()` sets `table = null`. Why can you not use it to reclaim memory?

<details><summary>Answer</summary>

It is package-private, and no public API path reaches it. Its only two call sites are
`clone()` (line 1472), which calls it on the *clone* before refilling it via `putMapEntries`,
and `readObject()` (line 1529), which calls it before deserialising entries. From outside
`java.util` you would need reflection with `--add-opens`, which is not a production answer;
reassigning the map reference is.

</details>

**Q6.** Which of `HashMap`, `ArrayList`, `ArrayDeque`, `StringBuilder` can be told to give their backing array back, and what is the pattern?

<details><summary>Answer</summary>

`ArrayList.trimToSize()` (JDK 21, `ArrayList.java` line 199) and `StringBuilder.trimToSize()`
can. `HashMap` and `ArrayDeque` cannot — no such method exists. The pattern: the JDK exposes a
trim only on array-backed *sequence* types, which already expose capacity in their API
(constructor argument, `ensureCapacity`). Hash-based containers treat capacity as a derived
internal quantity, so a public trim would have to specify a rehash; instead you drop the
reference and build a new container.

</details>

**Q7.** A map cycles: fill to ~50,000 entries, process, empty, repeat, every second, for the process's lifetime. Should you `clear()` it or replace it?

<details><summary>Answer</summary>

`clear()`. The peak-to-steady ratio is 1 — the map refills to the same size next cycle, so
retaining the table is exactly what you want: no reallocation, no rehash, and no allocation
pressure once per second. Replacing the map would throw away a correctly sized array and pay
the full growth sequence again on every cycle. The retention problem is about a *large peak
followed by a small steady state*, not about `clear()` as such.

</details>

---

**Leaves covered:** 3.6.41 (1 leaf)
**Leaves deferred:** none — 3.6.42 (iteration order) is in [05a1-internals-e1b-iteration-order.md](05a1-internals-e1b-iteration-order.md)
**Diagrams included:** none new — the sizing arithmetic (D-99) is embedded in [05-internals-e-sizing-and-iteration.md](05-internals-e-sizing-and-iteration.md)
**Target version:** Java 21 LTS
**Lines:** 471
