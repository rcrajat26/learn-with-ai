# 02 Java Collections — `HashMap` — INTERNALS (§3.6 `HashMap` source walk — the cached views, `HashIterator`, `forEach`/`replaceAll` and the `afterNode*` hooks)

**Target version: Java 21 LTS.** | [Index](../00-index.md)
Previous: [hash-map/05a1-internals-e1b-iteration-order.md](05a1-internals-e1b-iteration-order.md) · Next: [hash-map/05c-internals-e4-hashtable-and-prime-modulus.md](05c-internals-e4-hashtable-and-prime-modulus.md)

---

## 3.6.43 — `keySet`/`values`/`entrySet` as cached views, and `HashIterator`'s table walk

### Mental model

A `HashMap` contains no `Set` and no `Collection`. It contains one array. When you call `map.keySet()`, nothing is copied and nothing is built — you get back a single small object whose only state is the implicit reference to the enclosing map, and whose `size()`, `contains()`, `iterator()` and `remove()` are all thin forwarders onto the same table.

Think of the three views as three differently-shaped windows cut into one wall. Each shows the same room from a different angle. There is exactly **one window of each shape per map**: it is cut on first request and left in place forever.

### Why it exists

The alternative — returning a fresh `HashSet` of the keys — costs an O(n) copy and a second table's worth of memory on every call, and gives you a snapshot that silently diverges from the map. The `Map` contract instead specifies live views, and the caching makes the idiom `map.keySet().size()` in a hot loop allocation-free after the first call.

### When to reach for it, and when not

Use the views for iteration, bulk removal (`retainAll`, `removeIf`) and membership tests. Do **not** hold one past the lifetime of the map — a view pins the whole map in the heap through its outer reference, so caching `bigMap.keySet()` in a long-lived field keeps every value alive too. When you want an independent snapshot, say so explicitly: `Set.copyOf(map.keySet())` or `new ArrayList<>(map.values())`. View-versus-copy in general is [`../immutable-collections/01-views-copies-snapshots.md`](../immutable-collections/01-views-copies-snapshots.md).

### How it works — the source

```java
    public Set<Map.Entry<K,V>> entrySet() {
        Set<Map.Entry<K,V>> es;
        return (es = entrySet) == null ? (entrySet = new EntrySet()) : es;
    }
```
— `java.base/java/util/HashMap.java`, JDK 21, line 1097. (leaf 3.6.43)

One expression. `(es = entrySet)` reads the field into a local *and* tests it in the same breath; if it is null the assignment `entrySet = new EntrySet()` both stores and yields the new view. The local `es` exists so the field is read once rather than twice — the same defensive-local idiom that appears throughout `HashMap`.

`keySet()` spells the identical logic out longhand:

```java
    public Set<K> keySet() {
        Set<K> ks = keySet;
        if (ks == null) {
            ks = new KeySet();
            keySet = ks;
        }
        return ks;
    }
```
— `java.base/java/util/HashMap.java`, JDK 21, line 911. `values()` at line 1039 is the same shape with `Values`. (leaf 3.6.43)

**Insight:** the field `entrySet` is declared in `HashMap`; the fields `keySet` and `values` are **not** — they are inherited from `AbstractMap`. The class comment says so in as many words:

```java
    /**
     * Holds cached entrySet(). Note that AbstractMap fields are used
     * for keySet() and values().
     */
    transient Set<Map.Entry<K,V>> entrySet;
```
— `java.base/java/util/HashMap.java`, JDK 21, line 394. (leaf 3.6.43)

`AbstractMap` caches `keySet` and `values` because it can implement both generically on top of `entrySet()`. It has no `entrySet` field because `entrySet()` is its one abstract method — so `HashMap` adds the third field itself. All three are `transient`: views are derived state, never serialised.

### The diagram

A picture of three boxes all pointing at one `Node[]` would help here, but this file ships no new diagrams — the table geometry is drawn in [05-internals-e-sizing-and-iteration.md](05-internals-e-sizing-and-iteration.md).

### Minimal concrete example — the views are cached, live, and write-through

```java
import java.util.*;

public class Views {
    public static void main(String[] args) {
        Map<String, Integer> map = new HashMap<>();
        map.put("a", 1);
        map.put("b", 2);

        System.out.println("keySet   identical: " + (map.keySet()   == map.keySet()));
        System.out.println("values   identical: " + (map.values()   == map.values()));
        System.out.println("entrySet identical: " + (map.entrySet() == map.entrySet()));

        map.keySet().remove("a");
        System.out.println("after keySet().remove(\"a\"): " + map);

        map.put("c", 3);
        for (Map.Entry<String, Integer> e : map.entrySet()) {
            e.setValue(e.getValue() * 10);
        }
        System.out.println("after setValue loop: " + map);

        try {
            map.keySet().add("z");
        } catch (UnsupportedOperationException ex) {
            System.out.println("keySet().add -> UnsupportedOperationException");
        }
    }
}
```

Real output, JDK 21.0.7+8-LTS-245, Apple M4 Pro (arm64):

```
keySet   identical: true
values   identical: true
entrySet identical: true
after keySet().remove("a"): {b=2}
after setValue loop: {b=20, c=30}
keySet().add -> UnsupportedOperationException
```

Three things fall out. Removal through a view is a real removal — the view is a handle on the map, not a copy. `entrySet().iterator()` hands out the actual `Node` objects, so `entry.setValue(v)` writes straight into the node's `value` field; **this is the only supported way to change a mapping while iterating**. And no view supports `add`, because a key without a value is not a mapping.

**Correction to a claim worth checking.** The caching is *not* a `HashMap` speciality. Calling `keySet()` twice on the *same* `Map.of(...)` instance also returns the identical object:

```java
Map<String,Integer> imm = Map.of("a", 1, "b", 2);
Set<String> i1 = imm.keySet(), i2 = imm.keySet();
System.out.println((i1 == i2) + "  " + i1.getClass().getName());
```

```
true  java.util.AbstractMap$1
```

`ImmutableCollections`' map types extend `AbstractMap` and inherit exactly the same cached `keySet` field, so the identity holds there too — verified by running it. What *is* `HashMap`-specific is the purpose-built `KeySet`/`Values`/`EntrySet` classes, which forward straight to the table instead of routing every operation through `entrySet().iterator()`.

### `HashIterator` — the table walk

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

        public final boolean hasNext() {
            return next != null;
        }

        final Node<K,V> nextNode() {
            Node<K,V>[] t;
            Node<K,V> e = next;
            if (modCount != expectedModCount)
                throw new ConcurrentModificationException();
            if (e == null)
                throw new NoSuchElementException();
            if ((next = (current = e).next) == null && (t = table) != null) {
                do {} while (index < t.length && (next = t[index++]) == null);
            }
            return e;
        }

        public final void remove() {
            Node<K,V> p = current;
            if (p == null)
                throw new IllegalStateException();
            if (modCount != expectedModCount)
                throw new ConcurrentModificationException();
            current = null;
            removeNode(p.hash, p.key, null, false, false);
            expectedModCount = modCount;
        }
    }
```
— `java.base/java/util/HashMap.java`, JDK 21, line 1581. (leaf 3.6.43)

Line by line, the parts that matter.

| Element | What it is doing |
|---|---|
| `next` | the node `nextNode()` will return on the following call — the iterator is always one step ahead, which is what makes `hasNext()` a null test |
| `current` | the node just returned, so `remove()` knows what to unlink; nulled after each `remove()` so a second `remove()` throws `IllegalStateException` |
| `expectedModCount` | snapshotted in the constructor, re-synced after every `remove()` — see [`../iteration/02-fail-fast-fail-safe.md`](../iteration/02-fail-fast-fail-safe.md) for `modCount` in general |
| `index` | the slot **after** the one the cursor is in, because `t[index++]` post-increments |
| `do {} while (...)` | the skip-empty-slots loop; the body is empty because the entire step is the side effect inside the condition |

That idiom — `do {} while (index < t.length && (next = t[index++]) == null);` — appears twice, verbatim, once in the constructor and once in `nextNode()`. It advances `index` until it lands on a non-null slot, storing that slot's head node into `next` as it goes. It stops on either of two conditions: `index` reached the end (leaving `next == null`, so `hasNext()` is false), or a non-null head was found.

`nextNode()` walks a bin before moving on: `(next = (current = e).next)` sets `current` to the node being returned and `next` to its chain successor. Only when that successor is null does it re-enter the slot-scanning loop. So the traversal is: for each slot in ascending index order, walk the bin front to back.

`remove()` calls `removeNode(p.hash, p.key, null, false, false)`. The fourth argument is `matchValue = false`; the fifth is `movable = false`. `movable = false` tells a tree bin **not** to relink its root to the front of the array slot — moving the root would rearrange nodes the iterator has not visited yet, in front of the cursor. Then `expectedModCount = modCount` re-syncs, which is why iterator removal is the one structural modification iteration tolerates.

### The gotcha — iteration is O(capacity + size), not O(size)

The constructor and `nextNode()` both scan slots, and there are `table.length` of them regardless of how many are occupied. A map that grew to a million entries and then had 999,997 of them removed still has a million-slot table — `HashMap` never shrinks (see [05a-internals-e1-removal-and-iteration-order.md](05a-internals-e1-removal-and-iteration-order.md)). Iterating it means reading roughly 2^21 array slots to yield three entries.

The arithmetic: 1,000,000 entries at load factor 0.75 forces the table past 2^20 = 1,048,576 slots (1,048,576 × 0.75 = 786,432 < 1,000,000), so it doubles to 2^21 = 2,097,152 slots. At 4 bytes per compressed-oops reference that is 2,097,152 × 4 = **8,388,608 bytes ≈ 8 MB of array**, all of it touched on every iteration, to visit three nodes.

```java
import java.util.*;

public class IterCost {
    static long walk(Map<Integer, Integer> m) {
        long sum = 0;
        for (Integer k : m.keySet()) sum += k;
        return sum;
    }

    public static void main(String[] args) {
        Map<Integer, Integer> shrunk = new HashMap<>();
        for (int i = 0; i < 1_000_000; i++) shrunk.put(i, i);
        for (int i = 3; i < 1_000_000; i++) shrunk.remove(i);

        Map<Integer, Integer> fresh = new HashMap<>();
        for (int i = 0; i < 3; i++) fresh.put(i, i);

        System.out.println("shrunk.size() = " + shrunk.size() + ", fresh.size() = " + fresh.size());

        for (int i = 0; i < 200; i++) { walk(shrunk); walk(fresh); }

        int reps = 2000;
        long t0 = System.nanoTime();
        for (int i = 0; i < reps; i++) walk(shrunk);
        long tShrunk = System.nanoTime() - t0;

        t0 = System.nanoTime();
        for (int i = 0; i < reps; i++) walk(fresh);
        long tFresh = System.nanoTime() - t0;

        System.out.printf("shrunk (3 entries, huge table): %,d ns per full iteration%n", tShrunk / reps);
        System.out.printf("fresh  (3 entries, 16 slots)  : %,d ns per full iteration%n", tFresh / reps);
        System.out.printf("ratio: %.0fx%n", (double) tShrunk / tFresh);
    }
}
```

Real output, JDK 21.0.7+8-LTS-245, Apple M4 Pro (arm64):

```
shrunk.size() = 3, fresh.size() = 3
shrunk (3 entries, huge table): 1,178,557 ns per full iteration
fresh  (3 entries, 16 slots)  : 64 ns per full iteration
ratio: 18379x
```

**Unverified:** the absolute figures are single-shot wall clock, not JMH, and the 18,379× ratio is specific to this machine and this table size. The *shape* — two maps of identical `size()` differing by four orders of magnitude in iteration cost — is the finding, and it is robust.

**Pitfall:** *"`map.clear()` makes iteration cheap again."* It does not. `clear()` nulls the slots and leaves the array at its grown length. Only `map = new HashMap<>()` returns you to a 16-slot table.

> **Definition.** `keySet()`, `values()` and `entrySet()` each return a single per-map, lazily created, cached view object that forwards every operation onto the map's own table; `HashIterator` traverses that table by scanning array slots in ascending index order and walking each bin front to back, making iteration cost proportional to capacity plus size rather than size alone.

---

## 3.6.44 — `forEach` and `replaceAll`, and their own `modCount` checks

### Mental model

`HashMap.forEach` is not sugar over the iterator. It is a second, independent traversal of the same table — a nested `for` loop written inline, with no iterator object, no cursor state, and no per-element `hasNext`/`next` call pair. The iterator exists because the `Iterable` contract demands an object; `forEach` does not need one, so it does not build one.

### Why it exists

Java 8 added `Map.forEach` as a default method implemented over `entrySet().iterator()`. `HashMap` overrides it because it can do better: it owns the table, so it can walk it directly and skip the iterator's allocation, its slot-cursor bookkeeping, and its per-element `modCount` comparison.

### When to reach for it, and when not

Reach for `forEach` when you are consuming every entry and want the cheapest walk. Do **not** reach for it when you need early exit (there is no `break`), when you need `iterator.remove()`, or when you want the failure to land on the offending step rather than at the end.

### How it works — the source

```java
    public void forEach(BiConsumer<? super K, ? super V> action) {
        Node<K,V>[] tab;
        if (action == null)
            throw new NullPointerException();
        if (size > 0 && (tab = table) != null) {
            int mc = modCount;
            for (Node<K,V> e : tab) {
                for (; e != null; e = e.next)
                    action.accept(e.key, e.value);
            }
            if (modCount != mc)
                throw new ConcurrentModificationException();
        }
    }
```
— `java.base/java/util/HashMap.java`, JDK 21, line 1421. (leaf 3.6.44)

```java
    @Override
    public void replaceAll(BiFunction<? super K, ? super V, ? extends V> function) {
        Node<K,V>[] tab;
        if (function == null)
            throw new NullPointerException();
        if (size > 0 && (tab = table) != null) {
            int mc = modCount;
            for (Node<K,V> e : tab) {
                for (; e != null; e = e.next) {
                    e.value = function.apply(e.key, e.value);
                }
            }
            if (modCount != mc)
                throw new ConcurrentModificationException();
        }
    }
```
— `java.base/java/util/HashMap.java`, JDK 21, line 1437. (leaf 3.6.44)

The two are the same skeleton. `if (action == null) throw new NullPointerException();` is the longhand of `Objects.requireNonNull`, placed **before** the table is touched so a null argument fails identically on an empty and a populated map. `if (size > 0 && (tab = table) != null)` skips everything for an empty or unallocated map — note that on an empty map the null check still runs but the `modCount` check never does.

The outer `for (Node<K,V> e : tab)` is an enhanced-for over the **array**, which compiles to an index loop with no iterator. The inner `for (; e != null; e = e.next)` reuses the same loop variable as the bin cursor. Two counters' worth of work per element, and `action.accept` is the only call.

`replaceAll` writes `e.value = function.apply(...)` straight into the node — no `put`, no `hash()`, no bin lookup, no `afterNodeAccess`.

### The diagram

None; the loop shape is fully carried by the eight lines of source above.

### The gotcha — `forEach` detects concurrent modification *late*

`HashIterator.nextNode()` compares `modCount` **before every element**. `forEach` snapshots `int mc = modCount` once and compares **after the entire loop has run**. That is not a cosmetic difference: an action that structurally modifies the map runs over the whole remaining table — reading a structure it has already invalidated — and only then throws.

```java
import java.util.*;

public class ForEachCme {
    public static void main(String[] args) {
        Map<String, Integer> m1 = new LinkedHashMap<>();
        for (String k : List.of("a", "b", "c", "d", "e")) m1.put(k, k.hashCode());

        System.out.println("--- forEach removing \"a\" on first visit ---");
        Map<String, Integer> forEachMap = new HashMap<>(m1);
        try {
            forEachMap.forEach((k, v) -> {
                System.out.println("  visited " + k);
                if (k.equals("a")) forEachMap.remove("a");
            });
            System.out.println("  no exception");
        } catch (ConcurrentModificationException e) {
            System.out.println("  ConcurrentModificationException AFTER the loop finished");
        }

        System.out.println("--- iterator removing \"a\" on first visit ---");
        Map<String, Integer> iterMap = new HashMap<>(m1);
        try {
            for (String k : iterMap.keySet()) {
                System.out.println("  visited " + k);
                if (k.equals("a")) iterMap.remove("a");
            }
            System.out.println("  no exception");
        } catch (ConcurrentModificationException e) {
            System.out.println("  ConcurrentModificationException on the NEXT next()");
        }
    }
}
```

Real output, JDK 21.0.7+8-LTS-245, Apple M4 Pro (arm64):

```
--- forEach removing "a" on first visit ---
  visited a
  visited b
  visited c
  visited d
  visited e
  ConcurrentModificationException AFTER the loop finished
--- iterator removing "a" on first visit ---
  visited a
  ConcurrentModificationException on the NEXT next()
```

Four extra actions executed under `forEach` before the exception landed. If the action had been "send an email" rather than "print", four emails went out on a map the JVM already considered corrupt. `forEach`'s check is a post-hoc audit, not a guard rail.

**Insight:** `replaceAll`'s own writes never trip its check, because assigning `e.value` is not a *structural* modification and does not touch `modCount` — the same reason `putVal`'s update path leaves `modCount` alone (see [02-internals-b-put-and-get.md](02-internals-b-put-and-get.md)). The check exists purely to catch a *function* that reaches out and modifies the map.

### Correction — `LinkedHashMap` overrides both, and that is why the access-order claim holds

A consequence worth verifying rather than assuming: does `replaceAll` disturb an access-order `LinkedHashMap`? `HashMap.replaceAll` calls no hook, so on that route it should not. But checking the source shows the route is not the one that runs — `LinkedHashMap` **overrides both methods**:

```java
    public void replaceAll(BiFunction<? super K, ? super V, ? extends V> function) {
        if (function == null)
            throw new NullPointerException();
        int mc = modCount;
        for (LinkedHashMap.Entry<K,V> e = head; e != null; e = e.after)
            e.value = function.apply(e.key, e.value);
        if (modCount != mc)
            throw new ConcurrentModificationException();
    }
```
— `java.base/java/util/LinkedHashMap.java`, JDK 21, line 991; `forEach` at line 981 is the same shape. (leaf 3.6.44)

It walks `head`/`after` rather than the table, and — the load-bearing detail — it also assigns `e.value` directly with **no** `afterNodeAccess`. So the conclusion "`replaceAll` does not reorder an access-order map" is true, but it is true *via `LinkedHashMap`'s own override*, not via `HashMap`'s implementation. Verified by running it:

```java
LinkedHashMap<String, Integer> lru = new LinkedHashMap<>(16, 0.75f, true);
lru.put("a", 1); lru.put("b", 2); lru.put("c", 3);
System.out.println("initial order        : " + lru.keySet());
lru.get("a");
System.out.println("after get(\"a\")       : " + lru.keySet());
lru.replaceAll((k, v) -> v * 10);
System.out.println("after replaceAll     : " + lru.keySet() + " -> " + lru);
lru.put("b", 99);
System.out.println("after put(\"b\", 99)   : " + lru.keySet());
```

```
initial order        : [a, b, c]
after get("a")       : [b, c, a]
after replaceAll     : [b, c, a] -> {b=20, c=30, a=10}
after put("b", 99)   : [c, a, b]
```

`get` reorders, `put` on an existing key reorders, `replaceAll` does not. More in [`../linked-hash-map/01-internals.md`](../linked-hash-map/01-internals.md).

### The three ways to walk a map — mechanism only

| | enhanced-for over `entrySet()` | `map.forEach(...)` | `keySet()` + `get(k)` |
|---|---|---|---|
| Objects allocated per walk | one `EntryIterator` (view itself is cached) | none | one `KeyIterator`, plus a lambda/capture if any |
| Per-element cost | `hasNext()` + `nextNode()`, one `modCount` compare, interface dispatch | one `accept` call, no cursor state | iterator step **plus a full `get()`**: `hash()`, mask, bin walk, `equals` |
| CME detected | before the very next element | only after the whole loop | before the next element (removal via `get` may also return stale `null`) |
| `entry.setValue` available | yes | no — the lambda receives `K` and `V`, not the `Node` | no |
| Early exit | `break` | no | `break` |

The complexity story for the three idioms lives in [`../iteration/01-basics-iteration.md`](../iteration/01-basics-iteration.md).

> **Definition.** `HashMap.forEach` and `replaceAll` bypass `HashIterator` and walk the bucket array with a nested loop, snapshotting `modCount` once at entry and validating it once at exit — so they are cheaper per element than iteration but report concurrent modification only after the traversal has already completed.

---

## 3.6.45 — the three `afterNode*` hooks

**Mechanism.** Three package-private methods with empty bodies:

```java
    // Callbacks to allow LinkedHashMap post-actions
    void afterNodeAccess(Node<K,V> p) { }
    void afterNodeInsertion(boolean evict) { }
    void afterNodeRemoval(Node<K,V> p) { }
```
— `java.base/java/util/HashMap.java`, JDK 21, lines 1941–1943. (leaf 3.6.45)

They are the whole notification half of `HashMap`'s extension surface. The allocation half is four more package-private factories — `newNode`, `replacementNode`, `newTreeNode`, `replacementTreeNode`. Seven methods, no `protected` API, no interface, no listener registry: that is everything `LinkedHashMap` needs to add insertion order, access order and LRU eviction without `HashMap` knowing it exists. `afterNodeAccess` fires from `putVal`'s existing-key update path and from `LinkedHashMap`'s own `get`/`getOrDefault` (lines 539 and 551 of `LinkedHashMap.java`); `afterNodeInsertion(evict)` fires at the end of `putVal`; `afterNodeRemoval` fires from `removeNode`.

**Gotcha.** They are not `final`, so they are virtual calls. On a program whose heap holds only `HashMap` instances the call site is monomorphic and HotSpot inlines an empty body to nothing; mix `HashMap` and `LinkedHashMap` through the same `Map` field and the site becomes bimorphic, which costs a type guard per call. **Unverified:** the specific inlining and guard behaviour is standard HotSpot CHA/profile-guided-inlining doctrine but was not measured here.

> **Definition.** `afterNodeAccess`, `afterNodeInsertion` and `afterNodeRemoval` are empty package-private callbacks on `HashMap` that exist solely so `LinkedHashMap` can maintain its doubly-linked entry list from inside `HashMap`'s unmodified `putVal`, `getNode` and `removeNode`.

---

## Pitfalls

### Assuming `map.forEach` fails fast on the offending element

**Wrong**

```java
Map<String, Integer> m = new HashMap<>(Map.of("a",1,"b",2,"c",3,"d",4,"e",5));
m.forEach((k, v) -> {
    audit(k);              // side effect
    if (v > 3) m.remove(k);
});
```
Output: `audit` runs for **all five** keys, then `ConcurrentModificationException` is thrown after the loop. Every side effect already happened, over a table the map itself considers invalid.

**Right**

```java
Map<String, Integer> m = new HashMap<>(Map.of("a",1,"b",2,"c",3,"d",4,"e",5));
for (Iterator<Map.Entry<String,Integer>> it = m.entrySet().iterator(); it.hasNext(); ) {
    Map.Entry<String,Integer> e = it.next();
    audit(e.getKey());
    if (e.getValue() > 3) it.remove();   // resyncs expectedModCount
}
```
`Iterator.remove()` calls `removeNode(..., movable = false)` and then sets `expectedModCount = modCount`, so the traversal stays legal. Or, if you only want the removal, `m.values().removeIf(v -> v > 3)`.

**Why people believe it:** `forEach` reads like an enhanced-for, and the enhanced-for over `entrySet()` *does* fail on the very next step. The two look identical at the call site and differ entirely in where the `modCount` comparison sits.

### Assuming an emptied `HashMap` iterates cheaply

**Wrong**

```java
Map<Integer,Integer> cache = new HashMap<>();
for (int i = 0; i < 1_000_000; i++) cache.put(i, i);
cache.clear();
cache.put(1, 1);
for (var e : cache.entrySet()) { /* one entry — surely instant */ }
```
`clear()` nulls 2,097,152 slots and leaves the array at that length. Every subsequent iteration reads all of them.

**Right**

```java
cache = new HashMap<>();   // fresh 16-slot table on first put
cache.put(1, 1);
```
Only a new map (or `new HashMap<>(oldMap)`) resets the capacity. `HashMap` has no shrink path.

**Why people believe it:** `size()` reports 0 or 1, and `size()` is the number people reason about. Iteration cost is governed by `table.length`, which is not exposed by any public method.

## Cheat sheet

| Item | Value / behaviour |
|---|---|
| `keySet()` / `values()` / `entrySet()` | one cached instance each per map; `==` across calls is `true` |
| Fields backing them | `keySet`, `values` from `AbstractMap`; `entrySet` declared in `HashMap` (line 396), all `transient` |
| Caching is not `HashMap`-only | `Map.of(...).keySet()` is cached too — `ImmutableCollections` maps extend `AbstractMap` (class prints `java.util.AbstractMap$1`) |
| View semantics | live, write-through, no `add`; `entry.setValue()` writes into the node |
| `HashIterator` fields | `next`, `current`, `expectedModCount`, `index` (index is one *past* the current slot) |
| Skip-empty idiom | `do {} while (index < t.length && (next = t[index++]) == null);` — in ctor and `nextNode()` |
| Iteration complexity | **O(capacity + size)**, not O(size); `HashMap` never shrinks; `clear()` does not shrink either |
| Measured: 3 entries in a 2^21 table vs a fresh 16-slot map | 1,178,557 ns vs 64 ns per full walk (M4 Pro, JDK 21.0.7, **Unverified**, not JMH) |
| `Iterator.remove()` | `removeNode(hash, key, null, false, false)` — `movable = false`, then resyncs `expectedModCount` |
| `forEach` / `replaceAll` CME | `mc = modCount` at entry, compared **once after** the loop |
| `HashIterator` CME | compared **before every** `nextNode()` |
| Null argument | both throw `NullPointerException` before touching the table |
| `replaceAll` writes | `e.value = f.apply(...)` direct — no `put`, no hash, no `afterNodeAccess` |
| `LinkedHashMap` overrides | `forEach` (line 981) and `replaceAll` (line 991) walk `head`/`after`; neither reorders an access-order map |
| The three hooks | `afterNodeAccess`, `afterNodeInsertion(boolean)`, `afterNodeRemoval` — empty, lines 1941–1943 |
| Full extension surface | 4 node factories + 3 `afterNode*` hooks, all package-private |

## Self-test

**Q1.** Is `map.keySet() == map.keySet()` true, and where is the field that makes it so?

<details><summary>Answer</summary>

True. `keySet()` reads the field `keySet`, creates a `HashMap.KeySet` only if it is null, stores it, and returns it. The field itself is **inherited from `AbstractMap`**, not declared in `HashMap` — the comment at `HashMap.java` line 394 states this explicitly, noting that `HashMap` declares only `entrySet` (line 396) because `AbstractMap` has no such field. All three are `transient`. The identity is not `HashMap`-specific: `Map.of(...)` caches its `keySet` the same way, through the same inherited field.

</details>

**Q2.** A `HashMap` grew to a million entries and then had all but three removed. `size()` returns 3. Why does iterating it take a millisecond?

<details><summary>Answer</summary>

`HashMap` never shrinks. The table is still 2^21 = 2,097,152 slots. `HashIterator`'s `do {} while (index < t.length && (next = t[index++]) == null);` scans slots linearly looking for non-null heads, so a full iteration reads all 2,097,152 references — about 8 MB at 4 bytes per compressed oop. Measured on this machine: 1,178,557 ns versus 64 ns for a freshly built three-entry map, an 18,379× difference at identical `size()`. Only a new map resets capacity; `clear()` does not.

</details>

**Q3.** Why does `HashIterator.remove()` pass `movable = false` to `removeNode`?

<details><summary>Answer</summary>

`movable = true` lets a `TreeNode` bin relink its root to the head of the array slot after a removal. That would rearrange nodes the iterator has not yet visited, placing them in front of the cursor — some would be visited twice, others skipped. `false` suppresses the relink so the traversal order the iterator has committed to stays intact.

</details>

**Q4.** An action passed to `map.forEach` removes a key on its first invocation. On a five-entry map, how many times does the action run before the `ConcurrentModificationException`?

<details><summary>Answer</summary>

Five. `forEach` snapshots `int mc = modCount` before the nested loop and compares `modCount != mc` only after the loop has fully completed, so all remaining entries are visited first. An enhanced-for over `entrySet()` throws on the very next `nextNode()`, after one visit. Verified output on JDK 21: `forEach` printed a, b, c, d, e then threw; the iterator printed a then threw.

</details>

**Q5.** `replaceAll` writes `e.value` directly and never touches `modCount`. Why does it check `modCount` at all?

<details><summary>Answer</summary>

Because the *function* can modify the map. Value replacement is not a structural modification — `putVal`'s update path does not bump `modCount` either — so `replaceAll`'s own writes can never trip the check. The check exists solely to detect a function that reaches out and calls `put` or `remove` on the map being traversed. It is a post-hoc audit: like `forEach`, it fires only after the whole table has been walked.

</details>

**Q6.** Does `replaceAll` reorder an access-order `LinkedHashMap`, and by what route?

<details><summary>Answer</summary>

No, and the route matters. `LinkedHashMap` **overrides** `replaceAll` (line 991) and `forEach` (line 981), walking `head`/`after` rather than the table, so `HashMap`'s implementation never runs. The override assigns `e.value` directly and calls no `afterNodeAccess`, so no reordering occurs. Verified: on `new LinkedHashMap<>(16, 0.75f, true)` holding a, b, c — `get("a")` gives `[b, c, a]`, `replaceAll` leaves it at `[b, c, a]`, then `put("b", 99)` gives `[c, a, b]`.

</details>

**Q7.** Why are `afterNodeAccess`, `afterNodeInsertion` and `afterNodeRemoval` empty rather than absent?

<details><summary>Answer</summary>

They are `HashMap`'s entire notification surface for subclassing, and `LinkedHashMap` is the only user. Together with four allocation factories (`newNode`, `replacementNode`, `newTreeNode`, `replacementTreeNode`) they let `LinkedHashMap` maintain a doubly-linked entry list and LRU eviction without a single change to `putVal`, `getNode` or `removeNode`. All seven are package-private — no `protected` API, no interface, no listener registry, so the extension point is invisible outside `java.util` and costs nothing on a plain `HashMap` once HotSpot inlines the empty bodies.

</details>

## Open questions

- **Hook call-site inlining.** The claim that a bimorphic `afterNodeAccess` call site costs a type guard is standard HotSpot doctrine but was not measured; a `-XX:+PrintInlining` run over a mixed `HashMap`/`LinkedHashMap` workload would confirm it.
- **Benchmark rigour.** The 18,379× iteration ratio is single-shot `System.nanoTime` wall clock with a warm-up loop, not JMH. A JMH rerun with `Blackhole` consumption and forked JVMs would firm up the figure; the order of magnitude is not in doubt.

---

**Leaves covered:** 3.6.43, 3.6.44, 3.6.45 (3 leaves)
**Leaves deferred:** none — 3.6.46 and 3.6.47 (the `Hashtable` contrast and the power-of-two decision) are in [05c-internals-e4-hashtable-and-prime-modulus.md](05c-internals-e4-hashtable-and-prime-modulus.md)
**Diagrams included:** none new — the sizing arithmetic (D-99) is embedded in [05-internals-e-sizing-and-iteration.md](05-internals-e-sizing-and-iteration.md)
**Target version:** Java 21 LTS
**Lines:** 594
