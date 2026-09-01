# 02 Java Collections — `HashMap` — INTERNALS (§4.3 `MyHashMap<K,V>` — `MyHashSet`, `MyLinkedHashMap`, and a working LRU)

**Target version: Java 21 LTS.** | [Index](../00-index.md)
Previous: [hash-map/09-build-my-hash-map-d-views-and-iterator.md](09-build-my-hash-map-d-views-and-iterator.md) · Next: [hash-map/10a-build-my-hash-map-f-the-demo-harness.md](10a-build-my-hash-map-f-the-demo-harness.md)

---

`MyHashMap.java` is finished. This file spends it twice: once by wrapping it (`MyHashSet`, thirty-three lines) and once by extending it (`MyLinkedHashMap`, and then an LRU cache in fifteen more). Neither touches a single line of the map. That is the payoff for the seven-member extension surface introduced in [06a §2](06a-build-my-hash-map-a2-lazy-allocation-and-hooks.md), and it is the strongest argument in this whole build that the JDK's design is worth copying.

**How the code blocks assemble.** `MyHashSet.java` and `MyLinkedHashMap.java` are each a single block in this file. `LruCache.java` is the fourth file, also a single block below. `Demo.java` and `Bench.java` are in [10a](10a-build-my-hash-map-f-the-demo-harness.md) and [10b](10b-build-my-hash-map-g-diff-and-collision-dos.md).

This file has no diagram — D-147, the collision-DoS measurement, is in [10b](10b-build-my-hash-map-g-diff-and-collision-dos.md).

---

## 1. `MyHashSet<E>` — a map wearing a set's clothes

**Mental model.** A set is a map whose values you never look at. `HashSet` is not a distinct data structure; it is a `HashMap<E, Object>` where every value is the same shared sentinel, plus a façade that hides the second type parameter. Thirty-three lines, and one of them is the sentinel.

**Why it exists in this form.** Writing a separate open-addressed set would be faster and smaller — no `Node.value` field, so 4–8 bytes saved per element — but it would duplicate every line of the hash table, the resize, the treeification and the iterator. The JDK chose reuse, and `HashSet` has carried a wasted reference per element since 1.2 as the price. `ConcurrentHashMap.newKeySet()` makes the same trade for the same reason.

**When to reach for something else.** If elements are enums, `EnumSet` is a bitset and is orders of magnitude smaller and faster. If you need sorted iteration, `TreeSet`. If you need insertion order, `LinkedHashSet` — which is `HashSet`'s constructor delegating to a `LinkedHashMap`, the same trick one level up.

**How it works.** Every method is one line of delegation. Two are worth reading closely.

`add` returns `map.put(e, PRESENT) == null`. `put` returns the previous value, which is `null` exactly when the key was absent — so the boolean "did this change the set" falls out for free, with no extra lookup.

`remove` returns `map.remove(o) == PRESENT`. Reference equality against the sentinel, not `!= null`. Since `PRESENT` is the only value ever stored, the two are equivalent here; using `== PRESENT` documents the invariant and would catch a future bug where something else got stored.

```java
// MyHashSet.java
import java.util.AbstractSet;
import java.util.Collection;
import java.util.Iterator;
import java.util.Set;

public class MyHashSet<E> extends AbstractSet<E> implements Set<E> {

    private static final Object PRESENT = new Object();

    private final MyHashMap<E, Object> map;

    public MyHashSet() {
        map = new MyHashMap<>();
    }

    public MyHashSet(int initialCapacity) {
        map = new MyHashMap<>(initialCapacity);
    }

    public MyHashSet(Collection<? extends E> c) {
        map = new MyHashMap<>(Math.max((int) (c.size() / 0.75f) + 1, 16));
        for (E e : c) map.put(e, PRESENT);
    }

    @Override public Iterator<E> iterator()      { return map.keySet().iterator(); }
    @Override public int size()                  { return map.size(); }
    @Override public boolean isEmpty()           { return map.isEmpty(); }
    @Override public boolean contains(Object o)  { return map.containsKey(o); }
    @Override public boolean add(E e)            { return map.put(e, PRESENT) == null; }
    @Override public boolean remove(Object o)    { return map.remove(o) == PRESENT; }
    @Override public void clear()                { map.clear(); }
}
```

`iterator()` returns `map.keySet().iterator()` — the live `KeyIterator` from [file 09](09-build-my-hash-map-d-views-and-iterator.md), so `Iterator.remove`, fail-fast, `removeIf` and `stream()` all work with no further code. `equals`, `hashCode`, `toString`, `containsAll`, `retainAll` and `toArray` come from `AbstractSet` and `AbstractCollection`.

The collection constructor uses an explicit loop, not `addAll`. `java.util.HashSet`'s own constructor calls `addAll`, which calls the overridable `add` on a half-constructed object; JDK 21's `-Xlint:this-escape` flags it, and there is no reason to reproduce a thirty-year-old wart. The `Math.max((int)(c.size() / 0.75f) + 1, 16)` is the JDK's pre-sizing formula, kept verbatim — on JDK 19+ the equivalent for a plain map is `HashMap.newHashMap(n)`.

Real output, `Demo` section 11:

```
add(x)   -> true
add(x)   -> false
add(y)   -> true
contains(y)=true, size=2
remove(y)-> true, remove(z)-> false
set=[x], equals(Set.of("x"))=true
new MyHashSet<>(List.of(3,1,2,3,1)) = [1, 2, 3]
```

`set.equals(Set.of("x"))` being `true` is `AbstractSet.equals` doing its job across two unrelated implementations.

**Pitfall:** `PRESENT` is `private static final`, one instance for the entire JVM, shared by every `MyHashSet`. Making it non-static would allocate one dummy per set — harmless but pointless. Making it `null` would break `add`'s return value, because `put` returning `null` would no longer mean "absent".

**Interview:** *"How much memory does a `HashSet` waste compared to an ideal set?"* — One reference per element, the `Node.value` field that always points at the same sentinel: 4 bytes with compressed oops, 8 without. On 10 million elements that is 40 MB of pointers to one object. The JDK accepts it to avoid duplicating the entire hash table implementation.

> **Definition.** `MyHashSet` is a façade over a `MyHashMap<E, Object>` in which every mapping's value is a single shared sentinel, so set membership is key presence and every set operation is one map operation.

---

## 2. `MyLinkedHashMap<K,V>` — the `before`/`after` overlay

**Mental model.** Two data structures over one set of nodes. The hash table decides *where* an entry lives; a doubly linked list threaded through the same nodes decides *what order you see them in*. They are completely independent — a resize scrambles bucket positions and does not touch the list at all — and the only place they meet is the five overridden methods that keep the list in step.

**Why it exists.** `HashMap` iteration order is table order, which is stable within a run and meaningless across capacities. Three real needs break on that: reproducible output (serialising a config, generating a diff), a cache that must know which entry is oldest, and any API that promised "the order you put them in". `LinkedHashMap` solves all three by paying two references per entry.

**When not to use it.** Two extra references per entry is 8–16 bytes; on a 10-million-entry map that is 80–160 MB. If you only need order at read time, sorting the key set once at the end is cheaper. And if you need *sorted* order rather than *insertion* order, `TreeMap` is the right structure — `LinkedHashMap` gives you the order you wrote, not the order the keys compare in.

**How it works.** `Entry<K,V> extends MyHashMap.Node<K,V>` adds `before` and `after`. Two `head`/`tail` fields track the ends. Then five overrides, and that is the whole class apart from views.

| Override | What it adds | JDK 21 `LinkedHashMap.java` line |
|---|---|---|
| `newNode` | allocate an `Entry`, then `linkNodeAtEnd` | 280 |
| `replacementNode` | allocate an `Entry`, then `transferLinks` from the old one | 287 |
| `afterNodeInsertion(evict)` | if `evict` and `removeEldestEntry(head)`, remove the head | 322 |
| `afterNodeRemoval(e)` | unlink `e` from the doubly linked list | 308 |
| `afterNodeAccess(e)` | if `accessOrder`, move `e` to the tail and bump `modCount` | 336 |

**A version correction you will not find in most write-ups.** The private method that appends a new entry is called **`linkNodeAtEnd`** in JDK 21 — `/tmp/jdk21src/java.base/java/util/LinkedHashMap.java` line 236. It was called **`linkNodeLast`** from Java 8 through Java 17: verified at `/tmp/jdk8src/java/util/LinkedHashMap.java` line 222 and `/tmp/jdk17src/java.base/java/util/LinkedHashMap.java` line 223. The rename came with JDK 21's `SequencedMap` work (JEP 431), which added `putFirst`/`putLast` and a `putMode` field taking `PUT_NORM`, `PUT_FIRST` or `PUT_LAST` — so the method no longer always links at the end, and `linkNodeLast` had become a lie. Almost every blog post and interview answer still says `linkNodeLast`. Our build has no `SequencedMap` support, so ours always appends; we use the JDK 21 name because that is what the reader will find when they open the source.

```java
// MyLinkedHashMap.java
import java.util.AbstractCollection;
import java.util.AbstractSet;
import java.util.Collection;
import java.util.ConcurrentModificationException;
import java.util.Iterator;
import java.util.Map;
import java.util.NoSuchElementException;
import java.util.Objects;
import java.util.Set;

public class MyLinkedHashMap<K, V> extends MyHashMap<K, V> {

    static class Entry<K, V> extends MyHashMap.Node<K, V> {
        Entry<K, V> before, after;

        Entry(int hash, K key, V value, Node<K, V> next) {
            super(hash, key, value, next);
        }
    }

    Entry<K, V> head;
    Entry<K, V> tail;
    final boolean accessOrder;

    private Set<Map.Entry<K, V>> linkedEntrySet;
    private Set<K> linkedKeySet;
    private Collection<V> linkedValues;

    public MyLinkedHashMap() {
        super();
        this.accessOrder = false;
    }

    public MyLinkedHashMap(int initialCapacity, float loadFactor, boolean accessOrder) {
        super(initialCapacity, loadFactor);
        this.accessOrder = accessOrder;
    }

    private void linkNodeAtEnd(Entry<K, V> p) {
        Entry<K, V> last = tail;
        tail = p;
        if (last == null) {
            head = p;
        } else {
            p.before = last;
            last.after = p;
        }
    }

    private void transferLinks(Entry<K, V> src, Entry<K, V> dst) {
        Entry<K, V> b = dst.before = src.before;
        Entry<K, V> a = dst.after = src.after;
        if (b == null) head = dst; else b.after = dst;
        if (a == null) tail = dst; else a.before = dst;
    }

    @Override
    Node<K, V> newNode(int hash, K key, V value, Node<K, V> next) {
        Entry<K, V> p = new Entry<>(hash, key, value, next);
        linkNodeAtEnd(p);
        return p;
    }

    @Override
    Node<K, V> replacementNode(Node<K, V> p, Node<K, V> next) {
        Entry<K, V> q = (Entry<K, V>) p;
        Entry<K, V> t = new Entry<>(q.hash, q.key, q.value, next);
        transferLinks(q, t);
        return t;
    }

    @Override
    void afterNodeRemoval(Node<K, V> e) {
        Entry<K, V> p = (Entry<K, V>) e, b = p.before, a = p.after;
        p.before = p.after = null;
        if (b == null) head = a; else b.after = a;
        if (a == null) tail = b; else a.before = b;
    }

    @Override
    void afterNodeInsertion(boolean evict) {
        Entry<K, V> first = head;
        if (evict && first != null && removeEldestEntry(first)) {
            K key = first.key;
            removeNode(spread(key), key, null, false);
        }
    }

    @Override
    void afterNodeAccess(Node<K, V> e) {
        Entry<K, V> last = tail;
        if (accessOrder && last != e) {
            Entry<K, V> p = (Entry<K, V>) e, b = p.before, a = p.after;
            p.after = null;
            if (b == null) head = a; else b.after = a;
            if (a != null) a.before = b; else last = b;
            if (last == null) head = p;
            else {
                p.before = last;
                last.after = p;
            }
            tail = p;
            ++modCount;
        }
    }

    protected boolean removeEldestEntry(Map.Entry<K, V> eldest) {
        return false;
    }

    @Override
    public V get(Object key) {
        Node<K, V> e = getNode(key);
        if (e == null) return null;
        if (accessOrder) afterNodeAccess(e);
        return e.value;
    }

    @Override
    public V getOrDefault(Object key, V defaultValue) {
        Node<K, V> e = getNode(key);
        if (e == null) return defaultValue;
        if (accessOrder) afterNodeAccess(e);
        return e.value;
    }

    @Override
    public void clear() {
        super.clear();
        head = tail = null;
    }

    @Override
    public boolean containsValue(Object value) {
        for (Entry<K, V> e = head; e != null; e = e.after)
            if (Objects.equals(value, e.value)) return true;
        return false;
    }

    @Override
    public Set<Map.Entry<K, V>> entrySet() {
        Set<Map.Entry<K, V>> es = linkedEntrySet;
        return (es == null) ? (linkedEntrySet = new LinkedEntrySet()) : es;
    }

    @Override
    public Set<K> keySet() {
        Set<K> ks = linkedKeySet;
        return (ks == null) ? (linkedKeySet = new LinkedKeySet()) : ks;
    }

    @Override
    public Collection<V> values() {
        Collection<V> vs = linkedValues;
        return (vs == null) ? (linkedValues = new LinkedValues()) : vs;
    }

    final class LinkedEntrySet extends AbstractSet<Map.Entry<K, V>> {
        @Override public int size() { return size; }
        @Override public void clear() { MyLinkedHashMap.this.clear(); }
        @Override public Iterator<Map.Entry<K, V>> iterator() { return new LinkedEntryIterator(); }

        @Override public boolean contains(Object o) {
            if (!(o instanceof Map.Entry<?, ?> e)) return false;
            Node<K, V> candidate = getNode(e.getKey());
            return candidate != null && candidate.equals(o);
        }

        @Override public boolean remove(Object o) {
            if (!(o instanceof Map.Entry<?, ?> e)) return false;
            return removeNode(spread(e.getKey()), e.getKey(), e.getValue(), true) != null;
        }
    }

    final class LinkedKeySet extends AbstractSet<K> {
        @Override public int size() { return size; }
        @Override public void clear() { MyLinkedHashMap.this.clear(); }
        @Override public Iterator<K> iterator() { return new LinkedKeyIterator(); }
        @Override public boolean contains(Object o) { return containsKey(o); }
        @Override public boolean remove(Object o) {
            return removeNode(spread(o), o, null, false) != null;
        }
    }

    final class LinkedValues extends AbstractCollection<V> {
        @Override public int size() { return size; }
        @Override public void clear() { MyLinkedHashMap.this.clear(); }
        @Override public Iterator<V> iterator() { return new LinkedValueIterator(); }
        @Override public boolean contains(Object o) { return containsValue(o); }
    }

    abstract class LinkedHashIterator {
        Entry<K, V> next;
        Entry<K, V> current;
        int expectedModCount;

        LinkedHashIterator() {
            next = head;
            expectedModCount = modCount;
            current = null;
        }

        public final boolean hasNext() { return next != null; }

        final Entry<K, V> nextNode() {
            Entry<K, V> e = next;
            if (modCount != expectedModCount) throw new ConcurrentModificationException();
            if (e == null) throw new NoSuchElementException();
            current = e;
            next = e.after;
            return e;
        }

        public final void remove() {
            Entry<K, V> p = current;
            if (p == null) throw new IllegalStateException();
            if (modCount != expectedModCount) throw new ConcurrentModificationException();
            current = null;
            removeNode(p.hash, p.key, null, false);
            expectedModCount = modCount;
        }
    }

    final class LinkedKeyIterator extends LinkedHashIterator implements Iterator<K> {
        @Override public K next() { return nextNode().key; }
    }

    final class LinkedValueIterator extends LinkedHashIterator implements Iterator<V> {
        @Override public V next() { return nextNode().value; }
    }

    final class LinkedEntryIterator extends LinkedHashIterator implements Iterator<Map.Entry<K, V>> {
        @Override public Map.Entry<K, V> next() { return nextNode(); }
    }
}
```

Four observations that repay the reading.

*`LinkedHashIterator` is simpler than `HashIterator`.* No table index, no bin scan, no `SortedBin` case — just `next = e.after`. The overlay is a better traversal structure than the table, which is why `LinkedHashMap` iteration is O(size) while `HashMap` iteration is O(size + capacity). Iterating an almost-empty `HashMap` with a large table walks every empty slot; the linked version does not.

*`containsValue` walks the list, not the table.* Same O(n), better locality on a sparse table, and the JDK does the same (line 510).

*`afterNodeAccess` bumps `modCount`.* Moving a node changes iteration order, and an iterator that has already passed that node would otherwise return it twice. The JDK does this too, and it is the mechanism behind the next pitfall.

*Nothing here touches `putVal`, `getNode`, `removeNode`, `resize` or `treeifyBinAt`.* The subclass is 236 lines and the superclass is unmodified. That is the whole argument for cutting the seam in file 06a.

Real output, `Demo` sections 12 and 13:

```
MyLinkedHashMap  : [zebra, apple, mango, kiwi, fig]
java.util version: [zebra, apple, mango, kiwi, fig]
MyHashMap        : [zebra, apple, kiwi, fig, mango]  (hash order, not insertion order)
re-put existing key does not reorder: [zebra, apple, mango, kiwi, fig]
after remove(mango): [zebra, apple, kiwi, fig]
```
```
initial      : [a, b, c, d]
after get(a) : [b, c, d, a]
after get(c) : [b, d, a, c]
after put(b) : [d, a, c, b]  (put on an existing key also counts as access)
```

**Pitfall:** on an access-ordered map, `get` is a *structural* modification. Iterating one and calling `get` inside the loop throws `ConcurrentModificationException` — from a read. Insertion-ordered maps are unaffected, because `afterNodeAccess` returns immediately when `accessOrder` is false.

**Insight:** re-putting an existing key does **not** move it in insertion order, but it *does* in access order. Both fall out of one line: `putVal` calls `afterNodeAccess(e)` on the existing-key path, and `afterNodeAccess` checks `accessOrder` before doing anything. One flag, two documented behaviours, no branching in `HashMap` at all.

> **Definition.** `MyLinkedHashMap` threads a doubly linked list through the same `Node` objects the hash table holds, maintained entirely by overriding two node factories and three structural hooks, giving deterministic insertion or access order at a cost of two references per entry.

---

## 3. `removeEldestEntry`, and a working LRU cache

**Mental model.** An LRU cache is an access-ordered `LinkedHashMap` plus one method that answers "am I too big?". Access order guarantees the head is the least recently used entry; `afterNodeInsertion` offers it up after every insert; you say yes or no. Fifteen lines, and no eviction logic of your own.

**Why the hook is a `protected` method rather than a capacity field.** Because the eviction *policy* is the caller's, not the map's. Capacity-bounded is the common case, but "evict when total value size exceeds 100 MB" or "evict when the eldest is older than an hour" are the same hook with a different body. A `maxSize` field would have served the one case and blocked the others.

**When you would not do this.** For a production cache: Caffeine or Guava. `LinkedHashMap`-as-LRU has no concurrency (wrap it in `Collections.synchronizedMap` and every `get` takes the lock, because `get` writes), no TTL, no weight-based sizing, no statistics, and a strict-LRU policy that is measurably worse than Caffeine's W-TinyLFU on real workloads. It is the right answer for a bounded map inside one thread, and for an interview.

**How it works.** JDK line 604 — `removeEldestEntry` returns `false`, always. Override it. The javadoc's own example is exactly the four-line subclass below, and it has been there since 1.4.

`afterNodeInsertion` fires *after* the new entry is in place, so `size()` already includes it. That is why the test is `size() > capacity` and not `>=`: a capacity-3 cache reaches 4, evicts one, and settles at 3.

```java
// LruCache.java
import java.util.Map;

public final class LruCache<K, V> extends MyLinkedHashMap<K, V> {

    private final int capacity;

    public LruCache(int capacity) {
        super(16, 0.75f, true);
        this.capacity = capacity;
    }

    @Override
    protected boolean removeEldestEntry(Map.Entry<K, V> eldest) {
        return size() > capacity;
    }
}
```

`super(16, 0.75f, true)` — the third argument is `accessOrder`, and getting it wrong gives you an FIFO cache that looks like an LRU cache until a re-read pattern exposes it. This is the single most common mistake in hand-rolled `LinkedHashMap` caches.

Real output, `Demo` section 14:

```
filled to capacity : [k1, k2, k3]
touch k1           : [k2, k3, k1]
insert k4 (evicts) : [k3, k1, k4], size=3
insert k5 (evicts) : [k1, k4, k5]
get(k2) after evict: null
```

Read the third line carefully. `k1` was inserted *first* but survives, because the `get` moved it to the tail; `k2`, untouched since insertion, is evicted instead. That is the difference between LRU and FIFO, in one line of output.

**Pitfall:** `removeEldestEntry` must be side-effect free. It is called on every insertion, it is handed the live head entry, and modifying the map from inside it corrupts `afterNodeInsertion`'s in-flight state. Return a boolean; do nothing else.

**Interview:** *"Implement an LRU cache."* — `LinkedHashMap` with `accessOrder = true` and `removeEldestEntry` returning `size() > capacity`, **but** say the caveats unprompted: not thread-safe, `get` mutates so a synchronised wrapper serialises reads, and for production you would reach for Caffeine. If the interviewer wants the underlying structure, it is a hash map plus a doubly linked list, which is exactly what you just described.

> **Definition.** `removeEldestEntry` is a policy hook called by `afterNodeInsertion` after every genuine insertion, handed the head of the order list; returning `true` evicts that entry, which on an access-ordered map is the least recently used one.

---

## Pitfalls

### Building an "LRU" cache without `accessOrder = true`

**Wrong**

```java
class Fifo<K, V> extends MyLinkedHashMap<K, V> {
    Fifo() { super(); }                                     // accessOrder defaults to FALSE
    @Override protected boolean removeEldestEntry(Map.Entry<K, V> e) { return size() > 3; }
}
// fill k1,k2,k3 then get(k1) then put(k4) -> k1 is evicted despite being just read
```

**Right**

```java
class Lru<K, V> extends MyLinkedHashMap<K, V> {
    Lru() { super(16, 0.75f, true); }                       // access order
    @Override protected boolean removeEldestEntry(Map.Entry<K, V> e) { return size() > 3; }
}
// fill k1,k2,k3 then get(k1) then put(k4) -> k2 is evicted; k1 survives
```

**Why people believe it:** the no-arg constructor produces something that evicts, and eviction feels like the hard part. Without access order it is FIFO, and FIFO looks identical until a key is read a second time.

### Calling `get` while iterating an access-ordered map

**Wrong**

```java
MyLinkedHashMap<String, Integer> ao = new MyLinkedHashMap<>(16, 0.75f, true);
for (String k : List.of("a", "b", "c")) ao.put(k, 1);
for (String k : ao.keySet()) {
    Integer v = ao.get(k);          // ConcurrentModificationException -- from a READ
}
```

**Right**

```java
MyLinkedHashMap<String, Integer> ao = new MyLinkedHashMap<>(16, 0.75f, true);
for (String k : List.of("a", "b", "c")) ao.put(k, 1);
for (Map.Entry<String, Integer> e : ao.entrySet()) {
    Integer v = e.getValue();       // no access recorded, no modCount bump
}
```

**Why people believe it:** `get` is a read everywhere else in the Collections Framework. On an access-ordered `LinkedHashMap` it moves a node and bumps `modCount`, which is precisely what "access order" means.

### Assuming `LinkedHashMap` gives sorted order

**Wrong**

```java
MyLinkedHashMap<String, Integer> m = new MyLinkedHashMap<>();
for (String k : List.of("zebra", "apple", "mango")) m.put(k, k.length());
System.out.println(m.keySet());     // [zebra, apple, mango] -- NOT sorted
```

**Right**

```java
java.util.TreeMap<String, Integer> m = new java.util.TreeMap<>();
for (String k : List.of("zebra", "apple", "mango")) m.put(k, k.length());
System.out.println(m.keySet());     // [apple, mango, zebra]
```

**Why people believe it:** "linked" and "ordered" get conflated, and the output of a small `LinkedHashMap` built from already-sorted input looks sorted. It gives *encounter* order — the order you wrote — which is a different guarantee entirely.

---

## Cheat sheet

| Item | Rule | JDK 21 line |
|---|---|---|
| `HashSet` internals | `HashMap<E,Object>` with one shared `PRESENT` sentinel | — |
| Set memory overhead | one wasted reference per element (4 B compressed, 8 B not) | — |
| `add` return value | `map.put(e, PRESENT) == null` — free, no extra lookup | — |
| `LinkedHashMap.Entry` | `extends HashMap.Node`, adds `before` / `after` | LHM 205 |
| `head` / `tail` | eldest / youngest ends of the order list | LHM 218, 223 |
| `accessOrder` | `final boolean`; false = insertion order, true = access order | LHM 231 |
| Append method name | **`linkNodeAtEnd`** in JDK 21 | LHM 236 |
| Its old name | `linkNodeLast` in JDK 8–17; renamed for `SequencedMap` | JDK 8 LHM 222, JDK 17 LHM 223 |
| Overrides needed | `newNode`, `replacementNode`, 3 × `afterNode*` — five methods | LHM 280–336 |
| `get` on access order | structural: moves the node and bumps `modCount` | LHM 534 |
| Re-put an existing key | reorders under access order, **not** under insertion order | LHM 336 |
| `removeEldestEntry` | `protected`, returns `false`; called after every insertion | LHM 604 |
| LRU test | `size() > capacity` — `size` already counts the new entry | LHM 322 |
| Eviction suppressed when | `evict == false`, i.e. during bulk construction | LHM 322 |
| Iteration cost | `LinkedHashMap` O(size); `HashMap` O(size + capacity) | LHM 1003 |
| `LinkedHashSet` | `HashSet` delegating to a `LinkedHashMap` — the same trick again | — |
| Production LRU | Caffeine / Guava; this has no concurrency, TTL or weighting | — |

---

## Self-test

**Q1.** `MyHashSet.add` returns `map.put(e, PRESENT) == null`. Why is that correct, and what would break if values could be null?

<details><summary>Answer</summary>

`put` returns the previous value for the key, or `null` if there was no mapping. Since the only value ever stored is the non-null `PRESENT`, a `null` return means unambiguously "the key was absent", which is exactly `Set.add`'s "did this change the set". If the map could hold null values, a `null` return would be ambiguous — absent key or key mapped to null — and `add` would report `true` for an element that was already present. The invariant that makes the one-liner sound is "`PRESENT` is the only value, and it is not null".

</details>

**Q2.** `LinkedHashMap` overrides five methods on `HashMap` and no more. Name them and say what each keeps in step.

<details><summary>Answer</summary>

`newNode` — allocates a `LinkedHashMap.Entry` and appends it to the order list. `replacementNode` — allocates a replacement `Entry` and transfers the discarded node's `before`/`after` pointers to it, which is what keeps the list intact when a bin treeifies. `afterNodeInsertion(evict)` — offers the head entry to `removeEldestEntry` and evicts if told to. `afterNodeRemoval(e)` — unlinks `e` from the list. `afterNodeAccess(e)` — under access order, moves `e` to the tail. (It also overrides `get`, `containsValue`, `clear` and the three views, but those are behaviour on top of the hash table, not maintenance of it.)

</details>

**Q3.** The JDK 21 method that appends a new entry is not called `linkNodeLast`. What is it called, when did it change, and why?

<details><summary>Answer</summary>

It is `linkNodeAtEnd`, at `LinkedHashMap.java` line 236 in JDK 21. It was `linkNodeLast` in JDK 8 (line 222) and JDK 17 (line 223). The rename arrived with JEP 431's `SequencedMap`, which added `putFirst` and `putLast` and a `putMode` field; the method now consults `putMode` and may link at the *head* instead, so a name promising "last" was no longer accurate. Most write-ups and interview answers still say `linkNodeLast`, which is correct for JDK 8–17 and wrong for 21+.

</details>

**Q4.** Why does `afterNodeAccess` increment `modCount`, given that no entry was added or removed?

<details><summary>Answer</summary>

Because it changes iteration order, and an iterator mid-traversal has already committed to a position in the list. Move a node the iterator has passed to the tail and that node will be returned a second time; move one it has not reached to a position behind it and that node is skipped. Neither is a "concurrent modification" in the entry-count sense, but both produce wrong results, so `LinkedHashMap` counts reordering as structural. The visible consequence is that `get` on an access-ordered map throws `ConcurrentModificationException` if called during iteration.

</details>

**Q5.** An LRU cache with capacity 3 holds `[k1, k2, k3]` in access order. You call `get("k1")`, then `put("k4", v)`. Which key is evicted, and trace the mechanism.

<details><summary>Answer</summary>

`k2`. `get("k1")` calls `getNode`, finds the entry, sees `accessOrder == true` and calls `afterNodeAccess`, which unlinks `k1` and relinks it at the tail, leaving `[k2, k3, k1]`. `put("k4", v)` runs `putVal`, which inserts the node via `newNode` — appending `k4` to the tail, giving `[k2, k3, k1, k4]` — then bumps `size` to 4 and calls `afterNodeInsertion(true)`. That reads `head`, which is `k2`, and passes it to `removeEldestEntry`, which returns `size() > 3` — true. `removeNode` deletes `k2`, `afterNodeRemoval` unlinks it, and the list settles at `[k3, k1, k4]`.

</details>

**Q6.** Iterating a `LinkedHashMap` is O(size) but iterating a `HashMap` is O(size + capacity). Where does the difference come from, and when does it matter?

<details><summary>Answer</summary>

`HashIterator` scans the table slot by slot, so it visits every empty bucket as well as every entry. `LinkedHashIterator` follows `after` pointers and never touches the table. The difference is invisible on a well-loaded map, where capacity is about 1.3 × size, and it bites when a map is large-capacity and nearly empty — a map that once held a million entries and was `clear()`ed still has two million slots, and iterating it costs two million steps to yield nothing. That is the same retained-table behaviour noted in [file 07](07-build-my-hash-map-b-put-get-resize.md).

</details>

**Q7.** Why is `removeEldestEntry` a `protected` method returning `boolean` rather than a `maxSize` constructor argument?

<details><summary>Answer</summary>

Because the eviction policy belongs to the caller. Capacity-bounded is only the most common case; "evict when the summed value size exceeds a byte budget", "evict when the eldest entry's timestamp is older than an hour", or "never evict while a flag is set" are all the same hook with a different body, and a `maxSize` field would have served one and blocked the rest. The hook is handed the live eldest entry, so the decision can depend on the entry's key and value, not just on the count.

</details>

---

**Leaves covered:** 4.3.11, 4.3.12 (2 leaves)
**Leaves deferred:** none — 4.3.1–4.3.2 are in [06-build-my-hash-map.md](06-build-my-hash-map.md), 4.3.3 in [06a-build-my-hash-map-a2-lazy-allocation-and-hooks.md](06a-build-my-hash-map-a2-lazy-allocation-and-hooks.md), 4.3.4–4.3.6 in [07-build-my-hash-map-b-put-get-resize.md](07-build-my-hash-map-b-put-get-resize.md), 4.3.7–4.3.8 in [08-build-my-hash-map-c-treeify-and-defaults.md](08-build-my-hash-map-c-treeify-and-defaults.md), 4.3.9–4.3.10 in [09-build-my-hash-map-d-views-and-iterator.md](09-build-my-hash-map-d-views-and-iterator.md), 4.3.13–4.3.14 in [10b-build-my-hash-map-g-diff-and-collision-dos.md](10b-build-my-hash-map-g-diff-and-collision-dos.md)
**Diagrams included:** none new — the `put` trace (D-146, frames a–d) is embedded in [06a-build-my-hash-map-a2-lazy-allocation-and-hooks.md](06a-build-my-hash-map-a2-lazy-allocation-and-hooks.md), and the collision-DoS measurement (D-147) in [10b-build-my-hash-map-g-diff-and-collision-dos.md](10b-build-my-hash-map-g-diff-and-collision-dos.md)
**Target version:** Java 21 LTS
**Lines:** 599
