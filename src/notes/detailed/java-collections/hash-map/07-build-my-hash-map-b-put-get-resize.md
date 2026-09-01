# 02 Java Collections — `HashMap` — INTERNALS (§4.3 `MyHashMap<K,V>` — `put`, `get`, `remove`, `resize`)

**Target version: Java 21 LTS.** | [Index](../00-index.md)
Previous: [hash-map/06a-build-my-hash-map-a2-lazy-allocation-and-hooks.md](06a-build-my-hash-map-a2-lazy-allocation-and-hooks.md) · Next: [hash-map/08-build-my-hash-map-c-treeify-and-defaults.md](08-build-my-hash-map-c-treeify-and-defaults.md)

---

This is the working heart of the map: four methods that between them account for every structural change a `HashMap` ever makes. `putVal` inserts, `getNode` finds, `removeNode` unlinks, `resize` allocates and redistributes. Everything in files 08, 09 and 10 is either a wrapper around these or a hook they call.

**How the code blocks assemble.** `MyHashMap.java` is the concatenation, in order, of every code block labelled `// MyHashMap.java` in [06](06-build-my-hash-map.md) and [06a](06a-build-my-hash-map-a2-lazy-allocation-and-hooks.md), followed by every such block in this file, then [08](08-build-my-hash-map-c-treeify-and-defaults.md) and [09](09-build-my-hash-map-d-views-and-iterator.md); file 09 closes the class.

Three forward references appear below and are resolved in file 08: `SortedBin`, `treeifyBin` and `treeifyBinAt`. They are our stand-in for the JDK's `TreeNode`. Read them for now as "the bin has been converted to something that is not a plain chain"; the code compiles only once file 08's block is appended.

This file has no diagram — the four frames of the `put` trace (D-146) are embedded in [06a](06a-build-my-hash-map-a2-lazy-allocation-and-hooks.md), and re-reading them alongside `putVal` is the intended use.

---

## 1. `putVal` — the insert path

**Mental model.** `putVal` is a decision tree three levels deep, and it is worth holding the whole shape in your head before reading a line of it. Level one: *is there a table?* Level two: *is the bin empty?* If yes, one array store and you are done — this is the common case and it costs nothing. Level three: *is the key already here?* That is a walk, with the cheapest comparison first. Only after all of that does the size counter move and a resize become possible.

**Why it exists in this shape.** The single-argument `put(K, V)` is not enough for the rest of the class. `putIfAbsent` needs "insert only if there is no live value", the copy constructor needs "insert without triggering eviction", and `compute`/`merge` need both. Rather than four near-identical methods, `HashMap` has one private workhorse with two boolean flags — `onlyIfAbsent` and `evict` — and five thin public wrappers. That is JDK line 631.

**When you would write it differently.** Open addressing (`IdentityHashMap`, most C++ hash maps) has no chain to walk and no node to allocate, so its insert is a probe loop over a flat array — better cache behaviour, but deletion needs tombstones and resize is all-or-nothing. Separate chaining is the choice that makes `remove` cheap and makes per-bin treeification possible at all.

**How it works.** Five stages, in order.

*Stage 1, table check.* `if (tab == null || (n = tab.length) == 0) tab = resize()`. This is frame 1 of D-146 and it fires exactly once per map.

*Stage 2, empty bin.* `tab[i] = newNode(hash, key, value, null)` where `i = (n - 1) & hash`. Frame 2. One array store, no comparison, no `equals`.

*Stage 3, the chain walk.* Frame 3. Check the head node first — the JDK comments this "always check first node" — then loop. Each comparison is `e.hash == hash && (e.key == key || (key != null && key.equals(e.key)))`: integer compare, then reference compare, then `equals`. If the walk reaches the end, append and count; if `binCount` has reached `TREEIFY_THRESHOLD - 1` (that is, this new node is the eighth), call `treeifyBin`. The `- 1` is because `binCount` starts at 0 for the *second* node in the bin, the head having been checked before the loop.

*Stage 4, existing key.* If the walk found the key, write the value (unless `onlyIfAbsent` and the old value is non-null), fire `afterNodeAccess`, and **return early** — no `modCount` bump, no `size` bump, no resize. Replacing a value is not a structural modification, which is why you can `map.put(existingKey, v)` inside a loop over `map.keySet()` without a `ConcurrentModificationException`.

*Stage 5, the tail.* Only reached on a genuine insertion: `++modCount`, `if (++size > threshold) resize()`, `afterNodeInsertion(evict)`. Frame 4.

```java
// MyHashMap.java
    @Override
    public V put(K key, V value) {
        return putVal(spread(key), key, value, false, true);
    }

    final V putVal(int hash, K key, V value, boolean onlyIfAbsent, boolean evict) {
        Node<K, V>[] tab = table;
        int n;
        if (tab == null || (n = tab.length) == 0) {
            tab = resize();
            n = tab.length;
        }
        int i = (n - 1) & hash;
        Node<K, V> p = tab[i];
        if (p == null) {
            tab[i] = newNode(hash, key, value, null);
        } else {
            Node<K, V> e;
            if (p instanceof SortedBin<K, V> bin) {
                e = bin.find(hash, key);
                if (e == null) {
                    bin.insert(newNode(hash, key, value, null));
                    ++modCount;
                    if (++size > threshold) resize();
                    afterNodeInsertion(evict);
                    return null;
                }
            } else if (p.hash == hash && (p.key == key || (key != null && key.equals(p.key)))) {
                e = p;
            } else {
                for (int binCount = 0; ; ++binCount) {
                    if ((e = p.next) == null) {
                        p.next = newNode(hash, key, value, null);
                        if (binCount >= TREEIFY_THRESHOLD - 1)
                            treeifyBin(tab, hash);
                        break;
                    }
                    if (e.hash == hash && (e.key == key || (key != null && key.equals(e.key))))
                        break;
                    p = e;
                }
            }
            if (e != null) {
                V oldValue = e.value;
                if (!onlyIfAbsent || oldValue == null)
                    e.value = value;
                afterNodeAccess(e);
                return oldValue;
            }
        }
        ++modCount;
        if (++size > threshold) resize();
        afterNodeInsertion(evict);
        return null;
    }
```

**Two deviations from the JDK, both deliberate.** First, the JDK writes `if ((p = tab[i = (n - 1) & hash]) == null)` — assignment inside the condition, in the SSA-flavoured style Doug Lea's comment at line 227 explicitly defends as helping "avoid aliasing errors amid all of the twisty pointer operations". It is faster to read once you are used to it and slower to read the first ten times; we unroll it. Second, our `SortedBin` branch returns early because a sorted-array insert is a different operation from a chain append, where the JDK's `putTreeVal` returns a node and rejoins the common path. The observable behaviour is identical.

**The null key needs no branch.** `spread(null)` is 0, so the null key indexes bucket 0, and `p.key == key` succeeds by reference for `null == null` before `equals` is ever reached. Real output, `Demo` section 3:

```
put(a,1)      -> null
put(a,2)      -> 1
put(null,99)  -> null
get(null)     -> 99
null lands in bucket 0
```

**Pitfall:** `put` returns the *previous* value, and `null` means either "no previous mapping" or "the previous mapping was to null". `if (map.put(k, v) == null) { firstTime(); }` is wrong on a map that permits null values. `containsKey` is the only way to tell the two apart, and that is a second lookup — which is exactly the problem `computeIfAbsent` and `merge` exist to solve (file 08).

**Insight:** the resize check is `++size > threshold`, evaluated *after* the insert. So a map with threshold 12 holds 13 entries momentarily before doubling. The JDK never resizes pre-emptively, because it cannot know whether a `put` will insert or replace until the walk is done.

> **Definition.** `putVal` is the single insertion workhorse: it allocates the table on demand, takes a one-store fast path for an empty bin, otherwise walks the bin comparing hash then reference then `equals`, replaces in place without a structural modification if the key exists, and otherwise appends, bumps `modCount` and `size`, and resizes if the load factor has been exceeded.

---

## 2. `getNode`, and the read family built on it

**Mental model.** Reads are the insert path with the mutation removed. Same index computation, same three-stage comparison, same bin-type dispatch — and then four public methods that differ only in what they do with the node they find, or fail to find.

**Why one private finder.** `get`, `containsKey`, `getOrDefault`, `EntrySet.contains` and every `compute`-family method need "find the node for this key". Sharing one method means the comparison logic exists once. The JDK made this refactor in JDK 9 (before that, `getNode` took a pre-computed hash as a separate parameter; the signature was simplified to `getNode(Object)` when the redundant argument was removed).

**When the distinction matters to a caller.** `get` returning `null` is ambiguous — absent key, or key mapped to null. `containsKey` disambiguates. `getOrDefault` does *not*: it returns the default only when the key is absent, so a key mapped to `null` yields `null`, not the default. That trips people constantly, and the demo proves it.

**How it works.** JDK line 573. Head node first, then a chain walk, with a `TreeNode` branch in between. Note that the JDK's version checks `first.next != null` before testing `first instanceof TreeNode` — a micro-optimisation, since a tree bin always has more than one node. We test the head directly for clarity.

```java
// MyHashMap.java
    @Override
    public V get(Object key) {
        Node<K, V> e = getNode(key);
        return (e == null) ? null : e.value;
    }

    @Override
    public boolean containsKey(Object key) {
        return getNode(key) != null;
    }

    @Override
    public V getOrDefault(Object key, V defaultValue) {
        Node<K, V> e = getNode(key);
        return (e == null) ? defaultValue : e.value;
    }

    final Node<K, V> getNode(Object key) {
        Node<K, V>[] tab = table;
        int n;
        if (tab == null || (n = tab.length) == 0) return null;
        int hash = spread(key);
        Node<K, V> first = tab[(n - 1) & hash];
        if (first == null) return null;
        if (first instanceof SortedBin<K, V> bin) return bin.find(hash, key);
        if (first.hash == hash && (first.key == key || (key != null && key.equals(first.key))))
            return first;
        for (Node<K, V> e = first.next; e != null; e = e.next) {
            if (e.hash == hash && (e.key == key || (key != null && key.equals(e.key))))
                return e;
        }
        return null;
    }
```

Real output, `Demo` section 3:

```
containsKey(a)=true, containsKey(z)=false
getOrDefault(z, -1) = -1
getOrDefault(nullValued, -1) = null  (mapping exists, so the default is NOT used)
```

**Pitfall:** `getOrDefault` is not a null-safety wrapper. It answers "is this key present", not "is this value non-null". If you want the latter, `Objects.requireNonNullElse(map.get(k), fallback)` — or, better, do not put nulls in the map.

**Interview:** *"Is `HashMap.get` O(1)?"* — Amortised O(1) on the hash, **but** it is O(bin length) in truth: O(1) with a good hash, O(n) in a pure-chain implementation under adversarial keys, and O(log n) since Java 8 because a bin at length 8 with `Comparable` keys treeifies. The escape hatch is treeification, and it only works if your key type implements `Comparable<itself>`.

> **Definition.** `getNode` maps a key to its `Node` by masking the spread hash to a bucket index, then resolving within the bin — direct hit on the head, binary search if the bin is treeified, linear walk otherwise — using hash-then-reference-then-`equals` at every step.

---

## 3. `removeNode` — unlink, then notify

**Mental model.** Removal is a find that remembers the node *before* the match, because a singly linked chain cannot delete backwards. Everything else is bookkeeping: decrement, bump `modCount`, tell the subclass.

**Why the `matchValue` flag.** `Map.remove(key)` and `Map.remove(key, value)` (the two-argument default added in Java 8) differ only in whether the value must also match. One method, one boolean, two wrappers.

**When removal is the expensive case.** In a treeified bin the JDK's `removeTreeNode` has to rebalance and may untreeify; in our sorted bin, removal is an O(n) array shrink. Both are worse than a chain's O(1) unlink-once-found. Chains are the best structure for deletion and the worst for lookup, which is the whole tension treeification manages.

**How it works.** JDK line 819. We drop the JDK's fifth parameter, `boolean movable`, which exists only to tell `removeTreeNode` whether it may move the tree root — irrelevant without a red-black tree.

```java
// MyHashMap.java
    @Override
    public V remove(Object key) {
        Node<K, V> e = removeNode(spread(key), key, null, false);
        return (e == null) ? null : e.value;
    }

    @Override
    public boolean remove(Object key, Object value) {
        return removeNode(spread(key), key, value, true) != null;
    }

    final Node<K, V> removeNode(int hash, Object key, Object value, boolean matchValue) {
        Node<K, V>[] tab = table;
        int n;
        if (tab == null || (n = tab.length) == 0) return null;
        int index = (n - 1) & hash;
        Node<K, V> head = tab[index];
        if (head == null) return null;

        Node<K, V> node = null, prev = null;
        if (head instanceof SortedBin<K, V> bin) {
            node = bin.find(hash, key);
        } else if (head.hash == hash && (head.key == key || (key != null && key.equals(head.key)))) {
            node = head;
        } else {
            Node<K, V> p = head;
            for (Node<K, V> e = head.next; e != null; e = e.next) {
                if (e.hash == hash && (e.key == key || (key != null && key.equals(e.key)))) {
                    node = e;
                    prev = p;
                    break;
                }
                p = e;
            }
        }
        if (node == null) return null;
        if (matchValue) {
            V v = node.value;
            if (!(v == value || (value != null && value.equals(v)))) return null;
        }
        if (head instanceof SortedBin<K, V> bin) {
            bin.delete(node);
            if (bin.isEmpty()) tab[index] = null;
        } else if (prev == null) {
            tab[index] = node.next;
        } else {
            prev.next = node.next;
        }
        ++modCount;
        --size;
        afterNodeRemoval(node);
        return node;
    }

    @Override
    public void clear() {
        Node<K, V>[] tab = table;
        ++modCount;
        if (tab != null && size > 0) {
            size = 0;
            Arrays.fill(tab, null);
        }
    }
```

**`clear()` never shrinks the table.** After `map.clear()` a map that once held a million entries still owns a `Node[2097152]` — 16 MB of references on a 64-bit JVM with compressed oops. `java.util.HashMap.clear()` (line 864) behaves identically. If you are clearing a large map to reclaim memory, replace the reference instead: `map = new HashMap<>()`. Also note `++modCount` runs unconditionally, so `clear()` on an empty map still invalidates every live iterator — correct, and occasionally surprising.

**Pitfall:** `removeNode` returns the node, and `remove(Object)` turns that into a value. So `remove` returning `null` means either "not present" or "was mapped to null", the same ambiguity as `put`. The two-argument `remove(key, value)` returns a `boolean` and has no such problem.

**Insight:** `afterNodeRemoval` fires *after* the unlink, with the node already detached from the bin but its `before`/`after` pointers still intact. That ordering is exactly what `LinkedHashMap` needs, and reversing it would leave the overlay pointing into a chain the node has left.

> **Definition.** `removeNode` locates a key's node while retaining its predecessor, optionally verifies the value, unlinks it from the bin, decrements `size`, bumps `modCount`, and notifies the subclass through `afterNodeRemoval`.

---

## 4. `resize` — the `(e.hash & oldCap)` lo/hi split

**Mental model.** Doubling the capacity adds exactly one bit to the index. An entry that lived at index `j` in a table of `oldCap` slots now lives at either `j` or `j + oldCap`, and which one depends on a single bit of its hash: the bit with value `oldCap`. Nothing else changes. No rehashing, no `%`, no comparisons — one AND per entry, and every entry moves to one of two known destinations.

**Why it exists in this form.** Java 7's `transfer` rehashed with `indexFor(e.hash, newCapacity)` and prepended each entry to its new bin, which reversed chain order. Reversal is what made the famous Java 7 concurrent-resize infinite loop possible: two threads reversing the same chain could weld it into a cycle, and a subsequent `get` would spin forever at 100% CPU. Java 8's split builds the lo and hi lists head-to-tail, preserving relative order. That does **not** make `HashMap` thread-safe — concurrent resize still loses entries and corrupts `size` — it only removes one specific catastrophic failure mode.

**When the trade bites.** Doubling means the table is on average two-thirds full, so you carry up to 2× the array you need, and every resize is an O(capacity) stop-the-world pass over the whole table. Growth by a factor of 1.5, as `ArrayList` uses, would waste less but make the split arithmetic impossible — the whole trick depends on the new capacity being exactly twice the old.

**How it works.** JDK line 683, and it has two jobs. Jobs one: decide the new capacity and threshold, reading the three-state encoding from [06a §1](06a-build-my-hash-map-a2-lazy-allocation-and-hooks.md). Job two: redistribute.

The redistribution has three cases per bin. A single-node bin moves directly with `e.hash & (newCap - 1)` — no split needed, and this is the common case. A treeified bin, in the JDK, calls `TreeNode.split`. A chain runs the lo/hi split: walk it once, appending each node to a `lo` list if `(e.hash & oldCap) == 0` and to a `hi` list otherwise, then plant `loHead` at `j` and `hiHead` at `j + oldCap`. Both lists are built with tail pointers, so order is preserved.

```java
// MyHashMap.java
    final Node<K, V>[] resize() {
        Node<K, V>[] oldTab = table;
        int oldCap = (oldTab == null) ? 0 : oldTab.length;
        int oldThr = threshold;
        int newCap, newThr = 0;
        if (oldCap > 0) {
            if (oldCap >= MAXIMUM_CAPACITY) {
                threshold = Integer.MAX_VALUE;
                return oldTab;
            } else if ((newCap = oldCap << 1) < MAXIMUM_CAPACITY && oldCap >= DEFAULT_INITIAL_CAPACITY) {
                newThr = oldThr << 1;
            }
        } else if (oldThr > 0) {
            newCap = oldThr;
        } else {
            newCap = DEFAULT_INITIAL_CAPACITY;
            newThr = (int) (DEFAULT_LOAD_FACTOR * DEFAULT_INITIAL_CAPACITY);
        }
        if (newThr == 0) {
            float ft = (float) newCap * loadFactor;
            newThr = (newCap < MAXIMUM_CAPACITY && ft < (float) MAXIMUM_CAPACITY)
                     ? (int) ft : Integer.MAX_VALUE;
        }
        threshold = newThr;
        @SuppressWarnings({"rawtypes", "unchecked"})
        Node<K, V>[] newTab = (Node<K, V>[]) new Node[newCap];
        table = newTab;
        if (oldTab == null) return newTab;

        for (int j = 0; j < oldCap; ++j) {
            Node<K, V> e = oldTab[j];
            if (e == null) continue;
            oldTab[j] = null;
            if (e instanceof SortedBin<K, V> bin) e = bin.next;   // rebuild from scratch
            if (e.next == null) {
                newTab[e.hash & (newCap - 1)] = e;
                continue;
            }
            Node<K, V> loHead = null, loTail = null, hiHead = null, hiTail = null, next;
            do {
                next = e.next;
                if ((e.hash & oldCap) == 0) {
                    if (loTail == null) loHead = e; else loTail.next = e;
                    loTail = e;
                } else {
                    if (hiTail == null) hiHead = e; else hiTail.next = e;
                    hiTail = e;
                }
            } while ((e = next) != null);
            if (loTail != null) { loTail.next = null; newTab[j] = loHead; }
            if (hiTail != null) { hiTail.next = null; newTab[j + oldCap] = hiHead; }
        }
        retreeifyLongBins(newTab);
        return newTab;
    }

    private void retreeifyLongBins(Node<K, V>[] tab) {
        if (!treeifyEnabled || tab.length < MIN_TREEIFY_CAPACITY) return;
        for (int i = 0; i < tab.length; i++) {
            int c = 0;
            for (Node<K, V> e = tab[i]; e != null && c < TREEIFY_THRESHOLD; e = e.next) c++;
            if (c >= TREEIFY_THRESHOLD) treeifyBinAt(tab, i);
        }
    }
```

**The one simplification, stated exactly.** Where the JDK calls `TreeNode.split` to divide a tree in place — walking the tree's `prev`/`next` threading, rebuilding two trees, and untreeifying either half that falls to `UNTREEIFY_THRESHOLD` (6) or below — we flatten the sorted bin back to its plain chain (`e = bin.next`, which is valid because `SortedBin` keeps its items chained), run the ordinary lo/hi split on it, and then re-treeify in a second pass. That second pass is `retreeifyLongBins`. Cost: an extra O(capacity) scan of the new table plus a re-sort of each long bin. Benefit: `split`, `untreeify` and the tree-threading invariants do not have to exist. It is measured in [10b](10b-build-my-hash-map-g-diff-and-collision-dos.md).

`retreeifyLongBins` calls `treeifyBinAt` rather than `treeifyBin`, because `treeifyBin` may call `resize()` when the table is small — and calling `resize` from inside `resize` would recurse. The `tab.length < MIN_TREEIFY_CAPACITY` guard makes that impossible anyway; the two-method split makes it impossible *by construction*.

`oldTab[j] = null` before the walk is not cosmetic: it drops the old table's reference to the chain immediately, so if a GC runs mid-resize the old array does not keep the whole live set doubly reachable.

Real output, `Demo` section 4, showing order preserved across a resize from 32 to 64 — the six keys already in bin 0 stay in bin 0 in their original order, and the multiples of 16 that are not multiples of 32 land together in bin 16:

```
cap=32 bin[0] before resize: [0, 32, 64, 96, 128, 160]
cap=32 bin[0] after  resize: [0, 32, 64, 96, 128, 160, 192]
cap=32 bin[16] after resize: [16, 48, 80, 112, 144, 176]
```

**Pitfall:** `newThr = oldThr << 1` only runs when `oldCap >= DEFAULT_INITIAL_CAPACITY`. A map built with a tiny explicit capacity — say 4 — falls through to `newThr == 0` and recomputes `newCap * loadFactor` in floating point instead. Both paths agree; the shift is a fast path, not a different rule. Reading it as a special case for small maps is the misread.

**Interview:** *"Why is `HashMap` capacity always a power of two?"* — Three reasons, and most answers give only the first. Indexing becomes `(n-1) & hash` instead of `%`. Resize becomes a one-bit split into two known destinations. And `tableSizeFor` can round with a single `numberOfLeadingZeros` intrinsic. The cost is that a bad `hashCode` with structure in its low bits is not saved by a prime modulus — see [05c](05c-internals-e4-hashtable-and-prime-modulus.md).

> **Definition.** `resize` allocates the table on first use and thereafter doubles it, redistributing each bin by testing the single bit `e.hash & oldCap` — clear means the entry stays at index `j`, set means it moves to `j + oldCap` — building both destination chains head-to-tail so relative order is preserved.

---

## Pitfalls

### Treating a `null` return from `put` or `remove` as "the key was absent"

**Wrong**

```java
MyHashMap<String, Integer> m = new MyHashMap<>();
m.put("k", null);
if (m.put("k", 1) == null) {
    System.out.println("first insert");   // prints -- but it is the SECOND put
}
```

**Right**

```java
MyHashMap<String, Integer> m = new MyHashMap<>();
m.put("k", null);
if (!m.containsKey("k")) {
    m.put("k", 1);
} else {
    System.out.println("already present, value was " + m.get("k"));   // already present, value was null
}
// Better still, keep nulls out of the map and use:
//   m.computeIfAbsent("k", key -> 1);
```

**Why people believe it:** on a map that never stores nulls the idiom is correct, and most maps never store nulls. It fails the first time someone puts a null through a code path you did not write.

### Expecting `clear()` to free the table

**Wrong**

```java
MyHashMap<Integer, Integer> big = new MyHashMap<>();
for (int i = 0; i < 1_000_000; i++) big.put(i, i);
big.clear();
System.out.println("table still " + big.table.length + " slots");   // 2097152
```

**Right**

```java
MyHashMap<Integer, Integer> big = new MyHashMap<>();
for (int i = 0; i < 1_000_000; i++) big.put(i, i);
big = new MyHashMap<>();       // the old table becomes garbage as a whole
System.out.println("table " + (big.table == null ? "not allocated" : "allocated"));
```

**Why people believe it:** `clear()` sounds like a reset, and `size()` does go to 0. The array is retained deliberately — a map that is cleared and refilled in a loop should not re-grow every cycle.

### Believing Java 8's ordered resize made `HashMap` safe to share

**Wrong**

```java
// "The infinite-loop bug was fixed in Java 8, so concurrent writes are just lossy now."
MyHashMap<Integer, Integer> shared = new MyHashMap<>();
// two threads calling shared.put(...) -- still corrupt
```

**Right**

```java
java.util.Map<Integer, Integer> shared = new java.util.concurrent.ConcurrentHashMap<>();
// or, if writes are rare and reads dominate and the map is small:
// java.util.Collections.synchronizedMap(new MyHashMap<>())
```

**Why people believe it:** the Java 7 infinite loop was famous, well documented, and genuinely fixed. What was fixed is the *cycle*, not the race. Concurrent `putVal` still loses entries when two threads write the same bin, and `size` still drifts because `++size` is not atomic.

---

## Cheat sheet

| Operation | Mechanism | Structural? | JDK 21 line |
|---|---|---|---|
| `put` new key, empty bin | `tab[i] = newNode(...)` | yes | 631 |
| `put` new key, occupied bin | walk, append, maybe `treeifyBin` | yes | 631 |
| `put` existing key | `e.value = value`, `afterNodeAccess`, early return | **no** | 631 |
| `putVal` flags | `onlyIfAbsent` (skip when old value non-null), `evict` (allow eviction) | — | 631 |
| Comparison order | `hash ==` → `key ==` → `key.equals` | — | 631 |
| Treeify trigger | `binCount >= TREEIFY_THRESHOLD - 1`, i.e. the 8th node | — | 631 |
| Resize trigger | `++size > threshold`, checked after the insert | — | 631 |
| `get` / `containsKey` / `getOrDefault` | all one `getNode` call | no | 573 |
| `getOrDefault` | default only when the key is **absent**, not when the value is null | no | 632 |
| `remove(k)` | find with predecessor, unlink, `--size`, `afterNodeRemoval` | yes | 819 |
| `remove(k, v)` | same, plus a value equality check first | yes | 819 |
| `clear()` | `Arrays.fill(tab, null)`, `size = 0`, `++modCount`; **table not shrunk** | yes | 864 |
| Resize split test | `(e.hash & oldCap) == 0` → index `j`; else `j + oldCap` | — | 723 |
| Order across resize | preserved (Java 8+); reversed in Java 7 | — | 723 |
| Single-node bin at resize | placed directly via `e.hash & (newCap - 1)` | — | 716 |
| Capacity ceiling | at `2^30`, `threshold = Integer.MAX_VALUE` and growth stops | — | 690 |

---

## Self-test

**Q1.** Why does `put` on an existing key not bump `modCount`, and what does that let you do?

<details><summary>Answer</summary>

Because it is not a *structural* modification: no node is created or destroyed, no bin changes shape, no iterator's position becomes invalid. Only `e.value` is overwritten. That means you can legally do `for (String k : map.keySet()) map.put(k, transform(map.get(k)));` — replacing values while iterating keys — without a `ConcurrentModificationException`. Add one key that is not already present and the same loop throws. (`map.replaceAll` is the idiomatic way to write it.)

</details>

**Q2.** In the chain walk, why is the treeify test `binCount >= TREEIFY_THRESHOLD - 1` rather than `>= TREEIFY_THRESHOLD`?

<details><summary>Answer</summary>

Because `binCount` does not count the head. The head node is compared before the loop starts, and `binCount` is 0 on the iteration that examines the *second* node. So when `binCount == 7` the loop is examining the eighth node's slot, and the node being appended is the ninth link... except that the append happens on the iteration where `p.next == null`, which for a bin of eight existing nodes occurs at `binCount == 7`. Net effect: the bin is treeified when the node just appended brings the total to nine, which the JDK documents as "bins are converted to trees when adding an element to a bin with at least `TREEIFY_THRESHOLD` nodes" (line 253).

</details>

**Q3.** A map has capacity 32. An entry sits at index 5. After a resize to capacity 64, where can it be, and what decides?

<details><summary>Answer</summary>

Index 5 or index 37 (`5 + 32`), and nothing else. The new index is `hash & 63` where the old was `hash & 31`; the two differ only in bit 5, which has value 32 — that is `oldCap`. So the test is `(e.hash & oldCap) == 0`: clear means the new bit contributes nothing and the entry stays at 5; set means it contributes 32 and the entry moves to 37. No rehash, no modulus, one AND per entry.

</details>

**Q4.** What exactly was the Java 7 `HashMap` infinite loop, and what did Java 8 change?

<details><summary>Answer</summary>

Java 7's `transfer` moved entries by prepending each to the head of its new bin, which reversed chain order. Under concurrent resize, two threads reversing the same chain could produce a cycle — node A pointing to B and B pointing back to A — and any later `get` landing in that bin would spin forever, pinning a core at 100%. Java 8 replaced it with the lo/hi split, which appends to two lists with tail pointers and preserves order, so no reversal and no cycle. What did *not* change: concurrent writes still lose entries and still corrupt `size`. The fix removed a symptom, not the race.

</details>

**Q5.** Why does `resize()` set `oldTab[j] = null` before walking bin `j`?

<details><summary>Answer</summary>

To drop the old array's reference to that chain immediately. During a resize of a large map, both arrays are alive at once; without the nulling, a GC that runs mid-resize sees every already-moved entry reachable from two roots, which inflates the old-generation scan and can keep the old array's whole payload from being collected in that cycle. The nulling makes the old array progressively empty as the walk proceeds.

</details>

**Q6.** Our `resize` flattens a sorted bin and re-treeifies afterwards, where the JDK splits the tree in place. Name one behavioural consequence, not just a cost difference.

<details><summary>Answer</summary>

The JDK untreeifies during the split: a tree bin whose lo or hi half drops to `UNTREEIFY_THRESHOLD` (6) or fewer nodes becomes a plain chain again. Ours has no untreeify at all — `retreeifyLongBins` only converts upward. So a bin that treeifies and then loses nodes to a resize stays a `SortedBin` with two or three items, paying the sorted-array insert shift for no lookup benefit. It is correct, just occasionally pessimal, and it is one of the rows in file 10b's diff table.

</details>

**Q7.** `getOrDefault(k, -1)` returns `null`. What happened?

<details><summary>Answer</summary>

The key is present and mapped to `null`. `getOrDefault` is specified in terms of key presence, not value nullness: it returns the default only when `getNode` finds nothing. The demo shows exactly this — `getOrDefault(nullValued, -1) = null`. If you want "non-null or fallback", that is `Objects.requireNonNullElse(map.get(k), fallback)`; if you want neither surprise, keep nulls out of the map.

</details>

---

**Leaves covered:** 4.3.4, 4.3.5, 4.3.6 (3 leaves)
**Leaves deferred:** none — 4.3.1–4.3.2 are in [06-build-my-hash-map.md](06-build-my-hash-map.md), 4.3.3 in [06a-build-my-hash-map-a2-lazy-allocation-and-hooks.md](06a-build-my-hash-map-a2-lazy-allocation-and-hooks.md), 4.3.7–4.3.8 in [08-build-my-hash-map-c-treeify-and-defaults.md](08-build-my-hash-map-c-treeify-and-defaults.md), 4.3.9–4.3.10 in [09-build-my-hash-map-d-views-and-iterator.md](09-build-my-hash-map-d-views-and-iterator.md), 4.3.11–4.3.12 in [10-build-my-hash-map-e-set-linked-and-diff.md](10-build-my-hash-map-e-set-linked-and-diff.md), 4.3.13–4.3.14 in [10b-build-my-hash-map-g-diff-and-collision-dos.md](10b-build-my-hash-map-g-diff-and-collision-dos.md)
**Diagrams included:** none new — the `put` trace (D-146, frames a–d) is embedded in [06a-build-my-hash-map-a2-lazy-allocation-and-hooks.md](06a-build-my-hash-map-a2-lazy-allocation-and-hooks.md)
**Target version:** Java 21 LTS
**Lines:** 530
