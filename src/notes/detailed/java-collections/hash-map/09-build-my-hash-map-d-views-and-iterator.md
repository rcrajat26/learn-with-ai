# 02 Java Collections — `HashMap` — INTERNALS (§4.3 `MyHashMap<K,V>` — live views and the fail-fast iterator)

**Target version: Java 21 LTS.** | [Index](../00-index.md)
Previous: [hash-map/08-build-my-hash-map-c-treeify-and-defaults.md](08-build-my-hash-map-c-treeify-and-defaults.md) · Next: [hash-map/10-build-my-hash-map-e-set-linked-and-diff.md](10-build-my-hash-map-e-set-linked-and-diff.md)

---

`keySet()`, `values()` and `entrySet()` return no data. They return three small objects that hold a reference to the map and forward every question to it. That single design decision is why `map.keySet().remove(k)` deletes from the map, why the views cost nothing to create, and why iterating one while writing to the map throws. This file finishes `MyHashMap.java`.

**How the code blocks assemble.** `MyHashMap.java` is the concatenation, in order, of every code block labelled `// MyHashMap.java` in [06](06-build-my-hash-map.md), [06a](06a-build-my-hash-map-a2-lazy-allocation-and-hooks.md), [07](07-build-my-hash-map-b-put-get-resize.md) and [08](08-build-my-hash-map-c-treeify-and-defaults.md), followed by every such block in this file. **The last block in this file closes the class**; after appending it you have a complete, compilable `MyHashMap.java`.

This file has no diagram — the `put` trace (D-146, frames a–d) is embedded in [06a](06a-build-my-hash-map-a2-lazy-allocation-and-hooks.md), and there is no separate picture for the views because the mechanism is one field and one back-reference.

---

## 1. `containsValue` — a supporting fact first

Three beats, since it is not a primary concept.

**Mechanism.** Walk the whole table, walk each bin, compare. There is no index on values and there never will be — a `HashMap` hashes keys only, so `containsValue` is O(n) and unavoidably so. JDK 21 line 882. Our version adds one thing the JDK's does not need: a bin whose head is a `SortedBin` is not itself an entry, so the walk starts at `head.next` rather than at `head`.

**Gotcha.** `AbstractMap.containsValue` would work correctly but allocates: it iterates `entrySet()`, which means an `EntryIterator` object and a `Map.Entry` reference per element. Overriding it with a direct array walk removes the allocation. This is the one `AbstractMap` method we override purely for cost.

```java
// MyHashMap.java
    @Override
    public boolean containsValue(Object value) {
        Node<K, V>[] tab = table;
        if (tab == null || size == 0) return false;
        for (Node<K, V> head : tab) {
            Node<K, V> start = (head instanceof SortedBin<K, V> b) ? b.next : head;
            for (Node<K, V> p = start; p != null; p = p.next) {
                if (p.value == value || (value != null && value.equals(p.value))) return true;
            }
        }
        return false;
    }
```

> **Definition.** `containsValue` is an unindexed linear scan of every bin in the table, O(n) by construction, and the reason a value-keyed lookup requires a second map.

---

## 2. Live views

**Mental model.** A view is a lens, not a copy. `map.keySet()` allocates one object whose entire state is the implicit reference to the enclosing map; `size()` asks the map, `contains` asks the map, `remove` asks the map, and `iterator()` returns an iterator over the map's table that yields only the key half of each node. Nothing is copied, so nothing can go stale — and nothing can be modified independently either.

**Why it exists.** The alternative, returning a fresh `HashSet` of the keys, is O(n) time and O(n) memory per call, and it silently decouples: `for (String k : new HashSet<>(map.keySet())) map.remove(k);` is a completely different program from the same loop over the live view. The Collections Framework chose views everywhere — `Arrays.asList`, `List.subList`, `Map.keySet` — and made the aliasing explicit in the javadoc rather than hiding it behind a copy.

**When to reach for a copy instead.** Exactly when you need to iterate and structurally modify. `new ArrayList<>(map.keySet())` then `remove` in a loop is the correct idiom, and it is the honest cost: you are paying O(n) memory to buy the right to mutate. The cheaper alternatives are `Iterator.remove()` (one element at a time, no copy) and `removeIf` (bulk, no copy) — both of which work *through* the view.

**How it works.** Three inner classes, each about ten lines, each extending the matching `AbstractCollection` skeleton so that `stream()`, `forEach`, `removeIf`, `toArray`, `containsAll` and the rest come free. Each caches its instance in a field, because `AbstractMap`'s cache fields are package-private in `java.util` and unreachable from here — the divergence flagged in [06 §1](06-build-my-hash-map.md).

Note what each view can and cannot do:

| View | `add` | `remove` | `contains` cost | Why |
|---|---|---|---|---|
| `keySet()` | **unsupported** | yes → `removeNode` | O(1) | a key with no value is not a mapping |
| `values()` | **unsupported** | inherited, O(n) scan via the iterator | O(n) | values are not indexed, and duplicates make removal ambiguous |
| `entrySet()` | **unsupported** | yes → `removeNode` with value match | O(1) | adding would need a key *and* a value, which is `put` |

`add` is unsupported on all three because `AbstractCollection.add` throws `UnsupportedOperationException` and none of them override it. That is deliberate, not an oversight: there is no coherent meaning for "add a key to the key set".

```java
// MyHashMap.java
    @Override
    public Set<Map.Entry<K, V>> entrySet() {
        Set<Map.Entry<K, V>> es = entrySetView;
        return (es == null) ? (entrySetView = new EntrySet()) : es;
    }

    @Override
    public Set<K> keySet() {
        Set<K> ks = keySetView;
        return (ks == null) ? (keySetView = new KeySet()) : ks;
    }

    @Override
    public Collection<V> values() {
        Collection<V> vs = valuesView;
        return (vs == null) ? (valuesView = new Values()) : vs;
    }

    final class EntrySet extends AbstractSet<Map.Entry<K, V>> {
        @Override public int size() { return size; }
        @Override public void clear() { MyHashMap.this.clear(); }
        @Override public Iterator<Map.Entry<K, V>> iterator() { return new EntryIterator(); }

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

    final class KeySet extends AbstractSet<K> {
        @Override public int size() { return size; }
        @Override public void clear() { MyHashMap.this.clear(); }
        @Override public Iterator<K> iterator() { return new KeyIterator(); }
        @Override public boolean contains(Object o) { return containsKey(o); }
        @Override public boolean remove(Object o) {
            return removeNode(spread(o), o, null, false) != null;
        }
    }

    final class Values extends AbstractCollection<V> {
        @Override public int size() { return size; }
        @Override public void clear() { MyHashMap.this.clear(); }
        @Override public Iterator<V> iterator() { return new ValueIterator(); }
        @Override public boolean contains(Object o) { return containsValue(o); }
    }
```

The caching is not a micro-optimisation, it is a correctness convenience: `map.keySet() == map.keySet()` is `true`, so code that stores the view in a field and code that calls the accessor twice see the same object. The JDK does the same at lines 911, 1039 and 1097.

`EntrySet.remove` passes `matchValue = true`, so removing `Map.entry("a", 99)` from a map where `a` maps to 1 does nothing — correct, because that entry is not in the set. `KeySet.remove` passes `false`, because a key set does not know about values.

**`Map.Entry.setValue` writes through.** The entries the iterator yields are the live `Node` objects, so `e.setValue(100)` mutates the map. That is specified behaviour, and it is the only sanctioned way to modify values during iteration. Real output, `Demo` section 9:

```
keySet   = [a, b, c, d]
values   = [0, 1, 2, 3]
entrySet = [a=0, b=1, c=2, d=3]
after keySet().remove("a")   : map={b=1, c=2, d=3}, size=3
after entrySet().removeIf(v==2): map={b=1, d=3}
entry.setValue(100) writes through: map={b=100, d=3}
iterator.remove() : map={d=3}, size=1
```

`removeIf` on the entry set works with no extra code: `Collection.removeIf`'s default implementation drives `iterator()` and calls `Iterator.remove()`, which is why implementing one iterator correctly gets you bulk removal for free.

**Pitfall:** `values().remove(x)` compiles and works, but removes only the *first* matching entry encountered in table order, and which one that is depends on the hash distribution. If several keys map to the same value, you have written a non-deterministic program. `entrySet().removeIf(e -> x.equals(e.getValue()))` removes all of them and says so.

**Insight:** the JDK's `HashMap` overrides `keySet().forEach`, `values().forEach`, `entrySet().forEach` and `entrySet().spliterator()` with direct table walks (lines 911–1180), skipping the iterator entirely. We inherit the `AbstractCollection` versions, which allocate an iterator. It is a real cost on hot bulk paths and a deliberate omission here: it adds no mechanism you have not already seen.

**Interview:** *"How do you remove entries from a map while iterating it?"* — Three ways, and only three: `Iterator.remove()` on a view's iterator, `Collection.removeIf` on a view (which is the same thing in a loop), or iterate a copy. Anything else throws.

> **Definition.** A collection view is a stateless adapter object that holds only a reference to its backing map and translates every `Collection` operation into a map operation, so it aliases rather than copies — reads reflect later writes, removals write through, and additions are unsupported.

---

## 3. `HashIterator` — bin-by-bin traversal, fail-fast

**Mental model.** The iterator holds two cursors: `index`, the next table slot to examine, and `next`, the node to return. Advancing means "step along the current chain; if the chain ended, scan forward through the table for the next non-empty slot". That is why `HashMap` iteration order is neither insertion order nor sorted order — it is *table order*, an artefact of capacity and hash values, and it changes when the map resizes.

**Why fail-fast exists.** `HashMap` is not thread-safe and never pretends to be. But the common failure is not two threads — it is one thread modifying the map inside a loop over it, which corrupts the iterator's cursors in ways that produce wrong answers, skipped entries or infinite loops rather than a crash. `modCount` turns that class of bug from a silent wrong result into an immediate exception with a stack trace pointing at the offending line. The javadoc is careful: fail-fast behaviour "cannot be guaranteed" and must be used "only to detect bugs", not for correctness.

**When it does not fire.** Value replacement (`put` on an existing key, `Entry.setValue`) is not structural, so it does not bump `modCount` and does not throw. Neither does a modification made *through* the iterator, because `Iterator.remove` resynchronises `expectedModCount` afterwards. And a single-element map can survive one illegal `remove` undetected, because `hasNext()` returns `false` before `nextNode()` gets a chance to check — the JDK acknowledges this in the `ConcurrentModificationException` javadoc.

**How it works.** JDK line 1581. One abstract inner class holding the cursors and the `modCount` snapshot, three trivial final subclasses that differ only in what `next()` projects out of the node.

Our `advance` carries the one `SortedBin` accommodation in the whole traversal path: a bin head that is a `SortedBin` is a container, not an entry, so the walk starts at `head.next`. Everything after that is an ordinary chain, because `SortedBin.relink()` keeps its items and overflow wired together — the design decision from [08 §2](08-build-my-hash-map-c-treeify-and-defaults.md) paying off.

```java
// MyHashMap.java
    abstract class HashIterator {
        Node<K, V> next;
        Node<K, V> current;
        int expectedModCount;
        int index;

        HashIterator() {
            expectedModCount = modCount;
            current = next = null;
            index = 0;
            Node<K, V>[] t = table;
            if (t != null && size > 0) advance(t);
        }

        private void advance(Node<K, V>[] t) {
            while (index < t.length) {
                Node<K, V> head = t[index++];
                if (head == null) continue;
                next = (head instanceof SortedBin<K, V> b) ? b.next : head;
                if (next != null) return;
            }
            next = null;
        }

        public final boolean hasNext() { return next != null; }

        final Node<K, V> nextNode() {
            if (modCount != expectedModCount) throw new ConcurrentModificationException();
            Node<K, V> e = next;
            if (e == null) throw new NoSuchElementException();
            current = e;
            next = e.next;
            if (next == null) {
                Node<K, V>[] t = table;
                if (t != null) advance(t);
            }
            return e;
        }

        public final void remove() {
            Node<K, V> p = current;
            if (p == null) throw new IllegalStateException();
            if (modCount != expectedModCount) throw new ConcurrentModificationException();
            current = null;
            removeNode(p.hash, p.key, null, false);
            expectedModCount = modCount;
        }
    }

    final class KeyIterator extends HashIterator implements Iterator<K> {
        @Override public K next() { return nextNode().key; }
    }

    final class ValueIterator extends HashIterator implements Iterator<V> {
        @Override public V next() { return nextNode().value; }
    }

    final class EntryIterator extends HashIterator implements Iterator<Map.Entry<K, V>> {
        @Override public Map.Entry<K, V> next() { return nextNode(); }
    }
}
```

That closing brace is the end of `MyHashMap.java`.

Four details that are easy to get wrong and are load-bearing.

*The constructor pre-advances.* `hasNext()` must be answerable before `next()` is called, so the constructor already positions `next` at the first entry. `if (t != null && size > 0)` skips the whole scan for an empty map, which matters when someone iterates a large-capacity empty map in a loop.

*`nextNode` advances eagerly.* After returning node `e`, it immediately positions `next` at the following entry — possibly scanning forward several empty slots to find it. This is why `hasNext()` is a null check and costs nothing: the work was done in the previous `next()`.

*`current = null` before the removal.* `Iterator.remove()` clears `current` first, so calling `remove()` twice in a row throws `IllegalStateException` rather than removing the wrong element or corrupting the map.

*`expectedModCount = modCount` after the removal.* This resynchronisation is the entire reason `Iterator.remove` is legal during iteration while `map.remove` is not. Mechanically they do the same thing; only the iterator tells itself about it.

*`advance` is `private`.* An inner class constructor calling a non-private method would trigger `-Xlint:this-escape`. Private methods cannot be overridden, so the lint is satisfied and the code is genuinely safe.

Real output, `Demo` section 10:

```
structural put during iteration -> ConcurrentModificationException
iterator.remove() during iteration is fine: {1=1, 3=3}
```

**Pitfall:** the exception is thrown by `next()`, not by the `put` that caused it. The stack trace points at your loop header, not at the offending write, and if the write was several frames deep inside a helper method the trace does not mention it at all. Read `ConcurrentModificationException` as "something modified this map during this loop" and go looking.

**Insight:** `modCount` is a plain `int` with no synchronisation, and it wraps. Two threads can interleave such that a thread performs exactly 2³² structural modifications between an iterator's snapshot and its check and the counter comes back to the same value. That is not a realistic failure mode; it is why the javadoc says fail-fast is best-effort and must not be relied on for correctness.

**Interview:** *"Why is `HashMap` iteration order unpredictable?"* — Because it is table order: slot 0 upward, chain order within each slot. It is fully deterministic for a given capacity and set of hash codes — the demo prints the same order every run — **but** it changes when the map resizes and it differs between JDK versions and key types, so depending on it is a bug waiting for a capacity change. If you need a stable order, `LinkedHashMap` (file 10) or `TreeMap`.

> **Definition.** `HashIterator` is a two-cursor traversal — a table index and a node pointer — that walks bins in ascending slot order and chains in link order, pre-advancing so `hasNext()` is a null test, and comparing a `modCount` snapshot on every step so that any structural modification not made through the iterator itself is reported as a `ConcurrentModificationException`.

---

## Pitfalls

### Removing from a map inside a for-each over its key set

**Wrong**

```java
MyHashMap<Integer, Integer> m = new MyHashMap<>();
for (int i = 0; i < 5; i++) m.put(i, i);
for (Integer k : m.keySet()) {
    if (k % 2 == 0) m.remove(k);        // ConcurrentModificationException
}
```

**Right**

```java
MyHashMap<Integer, Integer> m = new MyHashMap<>();
for (int i = 0; i < 5; i++) m.put(i, i);
m.keySet().removeIf(k -> k % 2 == 0);   // or an explicit Iterator with it.remove()
System.out.println(m);                  // {1=1, 3=3}
```

**Why people believe it:** the loop reads like a filter, and `m.remove(k)` is obviously legal outside a loop. Nothing in the syntax hints that the for-each is holding an iterator with a snapshot.

### Expecting `values().remove(v)` to remove every matching entry

**Wrong**

```java
MyHashMap<String, Integer> m = new MyHashMap<>();
m.put("a", 1); m.put("b", 1); m.put("c", 2);
m.values().remove(1);
System.out.println(m.size());   // 2, not 1 -- one of a/b survived, and which one depends on hashing
```

**Right**

```java
MyHashMap<String, Integer> m = new MyHashMap<>();
m.put("a", 1); m.put("b", 1); m.put("c", 2);
m.values().removeIf(v -> v == 1);
System.out.println(m);          // {c=2}
```

**Why people believe it:** `Collection.remove(Object)` is specified to remove "a single instance", but the word "single" is easy to skim past when the collection is a view and the mental model is "delete this value from the map".

### Treating a view as a snapshot

**Wrong**

```java
MyHashMap<String, Integer> m = new MyHashMap<>();
m.put("a", 1);
Set<String> keysBefore = m.keySet();
m.put("b", 2);
System.out.println(keysBefore);       // [a, b] -- not a snapshot
```

**Right**

```java
MyHashMap<String, Integer> m = new MyHashMap<>();
m.put("a", 1);
Set<String> keysBefore = new java.util.HashSet<>(m.keySet());   // explicit copy
m.put("b", 2);
System.out.println(keysBefore);       // [a]
```

**Why people believe it:** the variable name and the assignment both suggest a value was captured. What was captured is a reference to a lens over a mutable object — the same class of surprise as storing a `List.subList` result.

---

## Cheat sheet

| Item | Rule | JDK 21 line |
|---|---|---|
| `keySet` / `values` / `entrySet` | live views; one cached instance each; O(1) to obtain | 911, 1039, 1097 |
| Same object every call | `map.keySet() == map.keySet()` is `true` | 911 |
| `add` on any view | `UnsupportedOperationException` | — |
| `keySet().remove(k)` | removes the mapping, value ignored | 911 |
| `entrySet().remove(e)` | removes only if key **and** value match | 1097 |
| `values().remove(v)` | removes **one** arbitrary matching entry | — |
| `Entry.setValue(v)` | writes through to the map; not structural | 281 |
| `containsValue` | O(n) table scan; no value index exists | 882 |
| Iteration order | table order: slot 0 upward, chain order within a slot | 1581 |
| Iteration is deterministic | for a fixed capacity and key set — but capacity changes | 1581 |
| Iterator cursors | `index` (next slot) and `next` (next node), pre-advanced | 1581 |
| `hasNext()` | `next != null`; the scan happened in the previous `next()` | 1581 |
| Fail-fast check | `modCount != expectedModCount` in `nextNode` and `remove` | 1581 |
| `Iterator.remove()` | legal; resynchronises `expectedModCount` afterwards | 1581 |
| Double `remove()` | `IllegalStateException` — `current` was nulled | 1581 |
| Not structural | `put` on an existing key, `Entry.setValue` — no exception | 631 |
| Fail-fast guarantee | none; best-effort bug detection only | javadoc |
| Bulk removal | `removeIf` on a view — drives the same iterator | — |
| JDK optimisation we skip | direct-table `forEach` and `spliterator` on all three views | 1421 |

---

## Self-test

**Q1.** Why does `Iterator.remove()` not throw where `map.remove()` in the same loop does?

<details><summary>Answer</summary>

Both bump `modCount` — the removal itself is identical, `removeNode` in both cases. The difference is one line at the end of `Iterator.remove()`: `expectedModCount = modCount`. The iterator knows about its own removal and resynchronises its snapshot, so the next `nextNode()` check passes. A direct `map.remove()` leaves the iterator's snapshot stale, and the next step throws. Fail-fast detects *unexpected* modification, not modification.

</details>

**Q2.** `hasNext()` is a single null check. Where did the work go?

<details><summary>Answer</summary>

Into the previous `next()`. `nextNode()` returns the current node and then immediately positions `next` at the following entry — walking `e.next`, and if the chain has ended, scanning forward through the table for the next non-empty slot. The constructor does the same pre-advance for the first element. So the potentially expensive part (scanning past empty slots in a sparse table) always happens inside `next()`, and `hasNext()` is free. That matters because `hasNext()` is called once per loop iteration plus once at the end.

</details>

**Q3.** Your map's `entrySet()` iterator yields a `Map.Entry`. Is it safe to keep that reference after the loop moves on?

<details><summary>Answer</summary>

For `HashMap` and this build, yes in the narrow sense — the object yielded is the live `Node`, and it stays valid until that entry is removed. But it is a bad idea: the javadoc says entries are only valid for the duration of the iteration, and other implementations reuse a single mutable `Entry` object per iterator. `EnumMap` and several third-party maps do exactly that, so code that hoards entries works on `HashMap` and breaks on the first map that recycles. Copy what you need, or use `Map.entry(k, v)` to snapshot.

</details>

**Q4.** Why is `advance` declared `private` inside `HashIterator`?

<details><summary>Answer</summary>

Because the constructor calls it, and JDK 21's `-Xlint:this-escape` warns when a constructor invokes a method that a subclass could override — the subclass's override would run against a partially initialised object. `HashIterator` has three subclasses (`KeyIterator`, `ValueIterator`, `EntryIterator`), so the hazard is not hypothetical. A `private` method cannot be overridden, so the call is provably safe and the lint is silent. Making it `final` would also work; `private` says more clearly that nothing outside should touch it.

</details>

**Q5.** `map.values().remove(1)` on a map with two keys mapped to 1. What happens, and what should you have written?

<details><summary>Answer</summary>

Exactly one of the two entries is removed, and which one depends on the keys' hash codes and the table capacity — it is deterministic for a given map state but arbitrary from the caller's point of view. `Collection.remove(Object)` removes a single instance, and `AbstractCollection`'s implementation stops at the first iterator hit. If you meant "all entries with this value", write `map.values().removeIf(v -> v == 1)` or `map.entrySet().removeIf(e -> e.getValue() == 1)`.

</details>

**Q6.** A bin has been converted to a `SortedBin`. What does the iterator have to do differently, and why is it only one line?

<details><summary>Answer</summary>

It has to start the chain at `head.next` rather than at `head`, because a `SortedBin` is a container occupying the bin-head slot and is not itself an entry — it has a `null` key and a `null` value. That is the only difference, because `SortedBin.relink()` keeps every item and every overflow node wired into a single `next` chain hanging off the bin. So the iterator, `containsValue` and `resize` all traverse a sorted bin as an ordinary chain. Only the four operations that need key-based lookup (`getNode`, `putVal`, `removeNode` and the treeify guard) branch on the bin type.

</details>

**Q7.** Iterating a `HashMap` twice with no modification in between gives the same order. Is it safe to rely on that?

<details><summary>Answer</summary>

No. It is deterministic for a fixed capacity and a fixed set of hash codes, so within one run of one program it is stable — which is exactly what makes the dependency easy to introduce and hard to catch. It changes the moment the map resizes, it changes if a key type's `hashCode` changes, and it has changed between JDK versions (the Java 8 treeify work altered within-bin order for long bins). If order matters, say so in the type: `LinkedHashMap` for insertion or access order, `TreeMap` for sorted order.

</details>

---

**Leaves covered:** 4.3.9, 4.3.10 (2 leaves)
**Leaves deferred:** none — 4.3.1–4.3.2 are in [06-build-my-hash-map.md](06-build-my-hash-map.md), 4.3.3 in [06a-build-my-hash-map-a2-lazy-allocation-and-hooks.md](06a-build-my-hash-map-a2-lazy-allocation-and-hooks.md), 4.3.4–4.3.6 in [07-build-my-hash-map-b-put-get-resize.md](07-build-my-hash-map-b-put-get-resize.md), 4.3.7–4.3.8 in [08-build-my-hash-map-c-treeify-and-defaults.md](08-build-my-hash-map-c-treeify-and-defaults.md), 4.3.11–4.3.12 in [10-build-my-hash-map-e-set-linked-and-diff.md](10-build-my-hash-map-e-set-linked-and-diff.md), 4.3.13–4.3.14 in [10b-build-my-hash-map-g-diff-and-collision-dos.md](10b-build-my-hash-map-g-diff-and-collision-dos.md)
**Diagrams included:** none new — the `put` trace (D-146, frames a–d) is embedded in [06a-build-my-hash-map-a2-lazy-allocation-and-hooks.md](06a-build-my-hash-map-a2-lazy-allocation-and-hooks.md)
**Target version:** Java 21 LTS
**Lines:** 418
