# 02 Java Collections — `HashMap` — INTERNALS (§4.3 `MyHashMap<K,V>` — the sorted bin, and the four default methods)

**Target version: Java 21 LTS.** | [Index](../00-index.md)
Previous: [hash-map/07-build-my-hash-map-b-put-get-resize.md](07-build-my-hash-map-b-put-get-resize.md) · Next: [hash-map/09-build-my-hash-map-d-views-and-iterator.md](09-build-my-hash-map-d-views-and-iterator.md)

---

Two things that look unrelated and are not. Treeification exists because a bin can be attacked; `computeIfAbsent` has a `ConcurrentModificationException` check because a *mapping function* can attack the table. Both are the same lesson: a hash map's invariants are only as strong as its willingness to notice when they break.

**How the code blocks assemble.** `MyHashMap.java` is the concatenation, in order, of every code block labelled `// MyHashMap.java` in [06](06-build-my-hash-map.md), [06a](06a-build-my-hash-map-a2-lazy-allocation-and-hooks.md) and [07](07-build-my-hash-map-b-put-get-resize.md), followed by every such block in this file, then [09](09-build-my-hash-map-d-views-and-iterator.md); file 09 closes the class.

This file has no diagram — the collision-DoS measurement that gives the sorted bin its point is D-147, in [10b](10b-build-my-hash-map-g-diff-and-collision-dos.md).

---

## 1. The `Comparable` screen — `comparableClassFor`

**Mental model.** Before a bin can be ordered, its keys must have an order. `Object` does not. `Comparable` alone is not enough either, because `class Foo implements Comparable<Bar>` compiles fine and `((Comparable) aFoo).compareTo(aFoo)` would then throw `ClassCastException` at runtime. So the JDK checks something stricter and reflective: *does this key's class directly declare `implements Comparable<itself>`?* Only then is `compareTo` safe to call on two instances of that class.

**Why it exists.** Treeification's whole benefit is a total order over the bin's keys. If the order is not total and not type-safe, the tree is worse than useless — and the JDK's fallback, `tieBreakOrder`, compares class names and then `System.identityHashCode`, which is stable within a run but arbitrary. The screen is what decides whether the good path or the arbitrary path runs.

**When it fails.** Records with an explicit `Comparable<Self>` pass. `String` passes (and is special-cased for speed, being the most common key type by a wide margin). Enums **fail** — `Foo extends Enum<Foo>`, and `Comparable<Foo>` comes from the superclass, not from `Foo`'s own `getGenericInterfaces()`. Lambdas, anonymous classes, and any class that inherits `Comparable` from a parent all fail.

**How it works.** JDK 21 line 345. Four conditions, all required:

```
static Class<?> comparableClassFor(Object x) {
    if (x instanceof Comparable) {
        Class<?> c; Type[] ts, as; ParameterizedType p;
        if ((c = x.getClass()) == String.class) // bypass checks
            return c;
        if ((ts = c.getGenericInterfaces()) != null) {
            for (Type t : ts) {
                if ((t instanceof ParameterizedType) &&
                    ((p = (ParameterizedType) t).getRawType() ==
                     Comparable.class) &&
                    (as = p.getActualTypeArguments()) != null &&
                    as.length == 1 && as[0] == c) // type arg is c
                    return c;
            }
        }
    }
    return null;
}
```

**You cannot call this method.** It is package-private in `java.util`, like `AbstractMap`'s view cache fields. Writing it yourself is not duplication for its own sake — it is the only option, and it is the second of the two places in this build where the JDK's design is visible but not reachable.

```java
// MyHashMap.java
    static Class<?> comparableClassFor(Object x) {
        if (x instanceof Comparable) {
            Class<?> c = x.getClass();
            if (c == String.class) return c;
            for (Type t : c.getGenericInterfaces()) {
                if (t instanceof ParameterizedType p && p.getRawType() == Comparable.class) {
                    Type[] as = p.getActualTypeArguments();
                    if (as.length == 1 && as[0] == c) return c;
                }
            }
        }
        return null;
    }

    @SuppressWarnings({"rawtypes", "unchecked"})
    static int compareKeys(Class<?> kc, Object a, Object b) {
        return (a == null || b == null || a.getClass() != kc || b.getClass() != kc)
               ? 0 : ((Comparable) a).compareTo(b);
    }
```

`compareKeys` mirrors the JDK's `compareComparables` (line 366): it returns 0 — "no information" — rather than throwing, whenever either operand is not exactly of the screened class. The raw `Comparable` cast is unavoidable; the class check immediately before it is what makes the cast safe, and the `@SuppressWarnings` documents that.

Real output, `Demo` section 5:

```
comparableClassFor("s")        = class java.lang.String
comparableClassFor(Poison(1))  = class Demo$Poison
comparableClassFor(PoisonNC(1))= null
```

**Pitfall:** `x instanceof Comparable` is *not* the screen. It is only the first of four tests, and passing it is what makes the remaining three necessary — a class can be `Comparable` to something other than itself.

> **Definition.** `comparableClassFor(x)` returns `x`'s class if and only if that class directly declares `implements Comparable<ThatSameClass>`, and `null` otherwise; it is the gate that decides whether a bin's keys can be ordered safely.

---

## 2. `SortedBin` — the treeify simplification, stated exactly

**Mental model.** A red-black tree bounds *both* lookup and insert at O(log n). A sorted array bounds *lookup* at O(log n) via binary search and leaves *insert* at O(n) because of the shift. For the problem treeification actually solves — an attacker jamming thousands of keys into one bin and then reading them back — bounding lookup is most of the value, and it costs about 110 lines instead of about 400. That is the trade this file makes, deliberately and with the consequence measured in [10b](10b-build-my-hash-map-g-diff-and-collision-dos.md).

**Why not the real red-black tree.** `HashMap.TreeNode` (JDK line 1966) is 620 lines: `treeify`, `untreeify`, `putTreeVal`, `removeTreeNode`, `split`, `rotateLeft`, `rotateRight`, `balanceInsertion`, `balanceDeletion`, `moveRootToFront`, `checkInvariants`, plus the `prev` back-pointer that keeps a tree bin simultaneously traversable as a list. Writing it would duplicate `../tree-map/`'s territory and teach red-black balancing rather than hash maps. **The honest framing is not "this is simpler", it is "this is a different point on the same curve, and here is exactly where it sits."**

**When our choice is actually better.** File [04c](04c-internals-d3-collision-dos.md) measured that the JDK's tree bin for **non-`Comparable`** keys is *slower* than a plain chain, because every `putTreeVal` walks the tree calling `tieBreakOrder` — an `identityHashCode` comparison that carries no useful ordering — and then still has to scan for `equals`. We do not treeify at all when the screen fails; we leave a chain. On that input our build is faster than the JDK's. File 10b reproduces both numbers.

**How it works.** `SortedBin<K,V> extends Node<K,V>` and sits as the bin head, holding:

- `items` — a `Node[]` of the bin's entries in `compareTo` order, binary-searched.
- `overflow` — a plain chain of entries whose key class is *not* the screened class. The JDK puts these in the tree via `tieBreakOrder`; we scan them linearly. This is the one case where our bin degrades to O(n), and it requires the attacker to mix key classes in one bin.
- `next` — kept wired through `items` then `overflow` by `relink()`, so `resize`, `containsValue` and the iterator can all walk a sorted bin as an ordinary chain without knowing it is one.

That last point is the design's load-bearing trick: everything that only *reads sequentially* needs no `SortedBin` branch at all.

```java
// MyHashMap.java
    static final class SortedBin<K, V> extends Node<K, V> {
        final Class<?> keyClass;
        Node<K, V>[] items;
        Node<K, V> overflow;

        SortedBin(int hash, Class<?> keyClass, Node<K, V>[] items) {
            super(hash, null, null, null);
            this.keyClass = keyClass;
            this.items = items;
            relink();
        }

        private void relink() {
            Node<K, V> chain = overflow;
            for (int i = items.length - 1; i >= 0; i--) {
                items[i].next = chain;
                chain = items[i];
            }
            this.next = chain;
        }

        boolean indexable(Object key) {
            return key != null && key.getClass() == keyClass;
        }

        int slot(Object key) {
            int lo = 0, hi = items.length - 1;
            while (lo <= hi) {
                int mid = (lo + hi) >>> 1;
                int cmp = compareKeys(keyClass, items[mid].key, key);
                if (cmp < 0) lo = mid + 1;
                else if (cmp > 0) hi = mid - 1;
                else {
                    for (int i = mid; i >= 0 && compareKeys(keyClass, items[i].key, key) == 0; i--)
                        if (Objects.equals(items[i].key, key)) return i;
                    for (int i = mid + 1; i < items.length
                            && compareKeys(keyClass, items[i].key, key) == 0; i++)
                        if (Objects.equals(items[i].key, key)) return i;
                    return -mid - 1;
                }
            }
            return -lo - 1;
        }

        Node<K, V> find(int hash, Object key) {
            if (indexable(key)) {
                int i = slot(key);
                return (i >= 0) ? items[i] : null;
            }
            for (Node<K, V> e = overflow; e != null; e = e.next)
                if (e.hash == hash && Objects.equals(e.key, key)) return e;
            return null;
        }

        void insert(Node<K, V> node) {
            if (indexable(node.key)) {
                int i = slot(node.key);
                int at = (i >= 0) ? i : -i - 1;
                @SuppressWarnings({"rawtypes", "unchecked"})
                Node<K, V>[] grown = (Node<K, V>[]) new Node[items.length + 1];
                System.arraycopy(items, 0, grown, 0, at);
                grown[at] = node;
                System.arraycopy(items, at, grown, at + 1, items.length - at);
                items = grown;
            } else {
                node.next = overflow;
                overflow = node;
            }
            relink();
        }

        void delete(Node<K, V> node) {
            if (indexable(node.key)) {
                int at = -1;
                for (int i = 0; i < items.length; i++) if (items[i] == node) { at = i; break; }
                if (at < 0) return;
                @SuppressWarnings({"rawtypes", "unchecked"})
                Node<K, V>[] shrunk = (Node<K, V>[]) new Node[items.length - 1];
                System.arraycopy(items, 0, shrunk, 0, at);
                System.arraycopy(items, at + 1, shrunk, at, items.length - at - 1);
                items = shrunk;
            } else {
                Node<K, V> prev = null;
                for (Node<K, V> e = overflow; e != null; prev = e, e = e.next) {
                    if (e == node) {
                        if (prev == null) overflow = e.next; else prev.next = e.next;
                        break;
                    }
                }
            }
            relink();
        }

        boolean isEmpty() { return items.length == 0 && overflow == null; }

        int length() {
            int n = items.length;
            for (Node<K, V> e = overflow; e != null; e = e.next) n++;
            return n;
        }
    }
```

`slot` deserves a second look. A plain binary search would be wrong here, because `compareTo` and `equals` are allowed to disagree — `a.compareTo(b) == 0` does not imply `a.equals(b)`. So on a `compareTo` hit, `slot` scans left and right across the whole run of `compareTo`-equal keys looking for an `equals` match, and only returns a negative insertion point if none is found. That is the sorted-array equivalent of what the JDK's `find` does when it walks both subtrees on a tie.

Now the conversion itself.

```java
// MyHashMap.java
    final void treeifyBin(Node<K, V>[] tab, int hash) {
        int n;
        if (tab == null || (n = tab.length) < MIN_TREEIFY_CAPACITY) {
            resize();
            return;
        }
        treeifyBinAt(tab, (n - 1) & hash);
    }

    final void treeifyBinAt(Node<K, V>[] tab, int index) {
        Node<K, V> head = tab[index];
        if (!treeifyEnabled || head == null || head instanceof SortedBin) return;
        Class<?> kc = comparableClassFor(head.key);
        if (kc == null) return;
        int count = 0;
        for (Node<K, V> e = head; e != null; e = e.next) {
            if (comparableClassFor(e.key) != kc) return;
            count++;
        }
        @SuppressWarnings({"rawtypes", "unchecked"})
        Node<K, V>[] items = (Node<K, V>[]) new Node[count];
        int i = 0;
        for (Node<K, V> e = head; e != null; e = e.next) items[i++] = replacementNode(e, null);
        Arrays.sort(items, (a, b) -> compareKeys(kc, a.key, b.key));
        tab[index] = new SortedBin<>(head.hash, kc, items);
    }

    final int binLengthOf(Object key) {
        Node<K, V>[] tab = table;
        if (tab == null || tab.length == 0) return 0;
        Node<K, V> head = tab[(tab.length - 1) & spread(key)];
        if (head instanceof SortedBin<K, V> bin) return bin.length();
        int n = 0;
        for (Node<K, V> e = head; e != null; e = e.next) n++;
        return n;
    }

    final boolean binIsSorted(Object key) {
        Node<K, V>[] tab = table;
        return tab != null && tab.length > 0
               && tab[(tab.length - 1) & spread(key)] instanceof SortedBin;
    }
```

`treeifyBin` keeps the JDK's most important behaviour verbatim: **if the table is smaller than `MIN_TREEIFY_CAPACITY` (64), resize instead of treeifying.** A long bin in a 16-slot table is far more likely to mean "this map is too small" than "these keys collide", and doubling redistributes for free. Only when a bin is still long in a 64-slot-or-larger table is collision the plausible explanation.

`treeifyBinAt` uses `replacementNode`, not the original nodes. Nothing in *this* class needs that — the entries would work fine reused — but `MyLinkedHashMap` needs it, because `replacementNode` is where `transferLinks` runs. Building the treeify path on the factory from day one is what makes file 10 a 236-line file rather than a debugging session. `Arrays.sort` on an object array is a stable merge sort, so keys that tie under `compareTo` keep their chain order.

`binLengthOf` and `binIsSorted` are inspection helpers with no JDK counterpart. They exist so the demo and the benchmark can assert on bin state rather than assert on timings.

**The diff, stated exactly, and repeated in [10b](10b-build-my-hash-map-g-diff-and-collision-dos.md):**

| Aspect | JDK `TreeNode` | Our `SortedBin` |
|---|---|---|
| Lookup in a poisoned bin | O(log n), red-black tree | **O(log n)**, binary search — same bound |
| Insert into a poisoned bin | O(log n), tree insert + rebalance | **O(n)**, array shift |
| Delete from a poisoned bin | O(log n), tree delete + rebalance | **O(n)**, array shift |
| Screen failure (`comparableClassFor == null`) | treeify anyway, order by `tieBreakOrder` (class name, then `identityHashCode`) | **leave the bin a plain chain** — measurably faster, see [04c](04c-internals-d3-collision-dos.md) |
| Mixed key classes in one bin | all in the tree, `tieBreakOrder` resolves | screened class in the sorted array, the rest in an `overflow` chain scanned linearly |
| Untreeify below 6 nodes | yes, `UNTREEIFY_THRESHOLD` | **no** — a shrunken bin stays a `SortedBin` |
| Resize | `TreeNode.split` divides the tree in place | flatten to a chain, lo/hi split, re-treeify in a second pass |
| Iteration order within a bin | tree order, via the `prev`/`next` threading | `compareTo` order, via `relink()` |
| Lines of code | ~620 (`TreeNode`) | ~110 (`SortedBin`) |

**So this build bounds lookup and not insert, where the JDK bounds both.** Say that sentence in an interview and you have demonstrated more than a memorised "Java 8 added trees".

Real output, `Demo` sections 5 and 6 — twenty keys with identical hash codes, inserted in descending order, come back out sorted, and stay correct after ten removals:

```
Comparable keys : binIsSorted=true, binLength=20, get(Poison(7))=7
sorted bin contents (first 8): [1, 2, 3, 4, 5, 6, 7, 8]
non-Comparable  : binIsSorted=false, binLength=20, get(PoisonNC(7))=7
```
```
after removing the 10 odd keys: size=10, binLength=10, get(Poison(7))=null, get(Poison(8))=8
```

**Pitfall:** treeification does not make a bad `hashCode()` acceptable. It caps the damage at O(log n) *and only for `Comparable` keys*; for everything else you are back to a linear chain. The real fix is always the key's `hashCode`.

**Interview:** *"What happens when a `HashMap` bin gets too long?"* — At eight nodes it treeifies, **but** only if the table already has at least 64 slots (otherwise it resizes instead), **and** only usefully if the key class implements `Comparable<itself>` — enums and any class inheriting `Comparable` from a parent fail the screen.

> **Definition.** `SortedBin` is a bin representation that keeps screened-`Comparable` keys in a `compareTo`-ordered array searched in O(log n) and everything else in a linear overflow chain — bounding lookup in a collision-poisoned bin at the same order as the JDK's red-black tree, at the cost of O(n) insertion and no untreeify.

---

## 3. `computeIfAbsent`, `compute`, `merge`, `putIfAbsent`

**Mental model.** These four are all "read-modify-write in one lookup". Written by hand, each is a `get`, a branch, and a `put` — two or three hash computations and two or three bin walks, with a window in between where the map can change. Written as a default method, it is one lookup and one write, and — the part people miss — the JDK will *tell you* if the function you passed mutated the map underneath it.

**Why the mutation check exists.** A mapping function that puts into the same map can trigger a resize while `computeIfAbsent` is holding a stale `tab` reference and a stale bin index. On JDK 8 this silently corrupted the table: entries vanished, and in the worst reported cases a bin became cyclic. JDK 9 added the `int mc = modCount` snapshot and the post-call comparison, turning silent corruption into a loud `ConcurrentModificationException`. **Version trap:** if you have ever seen the advice "never call `computeIfAbsent` recursively", this is why — and on JDK 9+ the advice is enforced rather than merely offered.

**When to reach for which.** They differ most in their null semantics, and the differences are not intuitive:

| Method | Function returns `null` | Existing value is `null` | Function called when? |
|---|---|---|---|
| `computeIfAbsent(k, f)` | **no entry inserted**, returns `null` | treated as absent, function runs | key absent, or mapped to `null` |
| `computeIfPresent(k, f)` | **entry removed** | treated as absent, function does not run | key present with a non-null value |
| `compute(k, f)` | **entry removed** (or never created) | passed to the function as `null` | always |
| `merge(k, v, f)` | **entry removed** | function skipped, `v` stored directly | key present with a non-null value |
| `putIfAbsent(k, v)` | n/a — no function | **overwritten** with `v` | n/a |

`putIfAbsent` overwriting a null value is the one that surprises everyone, and it falls straight out of `putVal`'s `if (!onlyIfAbsent || oldValue == null) e.value = value;`.

**How it works.** JDK lines 1195 (`computeIfAbsent`), 1261 (`computeIfPresent`), 1295 (`compute`), 1360 (`merge`). The shape is the same in all of them: locate, snapshot `modCount`, call the function, compare `modCount`, then act.

```java
// MyHashMap.java
    @Override
    public V putIfAbsent(K key, V value) {
        return putVal(spread(key), key, value, true, true);
    }

    @Override
    public V computeIfAbsent(K key, Function<? super K, ? extends V> mappingFunction) {
        Objects.requireNonNull(mappingFunction);
        int hash = spread(key);
        Node<K, V> old = getNode(key);
        if (old != null && old.value != null) {
            afterNodeAccess(old);
            return old.value;
        }
        int mc = modCount;
        V v = mappingFunction.apply(key);
        if (mc != modCount) throw new ConcurrentModificationException();
        if (v == null) return null;
        if (old != null) {
            old.value = v;
            afterNodeAccess(old);
            return v;
        }
        putVal(hash, key, v, false, true);
        return v;
    }

    @Override
    public V compute(K key, BiFunction<? super K, ? super V, ? extends V> remappingFunction) {
        Objects.requireNonNull(remappingFunction);
        int hash = spread(key);
        Node<K, V> old = getNode(key);
        V oldValue = (old == null) ? null : old.value;
        int mc = modCount;
        V v = remappingFunction.apply(key, oldValue);
        if (mc != modCount) throw new ConcurrentModificationException();
        if (old != null) {
            if (v != null) {
                old.value = v;
                afterNodeAccess(old);
            } else {
                removeNode(hash, key, null, false);
            }
        } else if (v != null) {
            putVal(hash, key, v, false, true);
        }
        return v;
    }

    @Override
    public V merge(K key, V value, BiFunction<? super V, ? super V, ? extends V> remappingFunction) {
        Objects.requireNonNull(value);
        Objects.requireNonNull(remappingFunction);
        int hash = spread(key);
        Node<K, V> old = getNode(key);
        if (old == null) {
            putVal(hash, key, value, false, true);
            return value;
        }
        V v;
        if (old.value != null) {
            int mc = modCount;
            v = remappingFunction.apply(old.value, value);
            if (mc != modCount) throw new ConcurrentModificationException();
        } else {
            v = value;
        }
        if (v != null) {
            old.value = v;
            afterNodeAccess(old);
        } else {
            removeNode(hash, key, null, false);
        }
        return v;
    }
```

**One divergence, and its cost.** The JDK inlines the bin walk into each of these methods, so it locates the bin once and inserts directly into `tab[i]` — one traversal total. We call `getNode` and then `putVal`, which is two traversals of the same bin. The JDK's version is roughly forty lines longer per method and duplicates the treeify and resize logic four times. We pay one extra bin walk (typically one or two node visits) on the insert path only, and the observable behaviour — return values, insertion, removal, exceptions, hook firing — is identical. If you are writing this for production rather than for understanding, inline it.

`computeIfPresent` is not overridden; `Map`'s default implementation is correct here, built from `get`, `put` and `remove`. It costs an extra lookup and does *not* carry the mutation check — a real gap in the default, and a reason to prefer `compute`.

Real output, `Demo` section 7, every line a distinct null semantic:

```
computeIfAbsent(new, k -> 10)      -> 10
computeIfAbsent(new, k -> 99)      -> 10   (present, function not called)
computeIfAbsent(skip, k -> null)   -> null ; containsKey(skip)=false  (no entry inserted)
computeIfAbsent(nullv, k -> 7)     -> 7   (null value counts as absent)
compute(keep, (k,v) -> null)       -> null ; containsKey(keep)=false  (entry REMOVED)
merge(hits, 1, Integer::sum)       -> 1
merge(hits, 1, Integer::sum)       -> 2
merge(hits, 1, (a,b) -> null)      -> null ; containsKey(hits)=false  (entry REMOVED)
putIfAbsent(x,5) with x->null      -> null ; get(x)=5  (null value OVERWRITTEN)
putIfAbsent(y,5) with y->1         -> 1 ; get(y)=1   (kept)
```

And the mutation check firing, `Demo` section 8:

```java
// (excerpt from Demo.java section 8 -- the full file is assembled in 10a)
MyHashMap<String, Integer> rec = new MyHashMap<>();
try {
    rec.computeIfAbsent("outer", k -> {
        rec.put("inner", 1);
        return 2;
    });
    System.out.println("no exception -- detection FAILED");
} catch (ConcurrentModificationException e) {
    System.out.println("caught " + e.getClass().getName() + " as expected");
}
System.out.println("map after the failed call: " + new java.util.TreeMap<>(rec));
```

```
caught java.util.ConcurrentModificationException as expected
map after the failed call: {inner=1}
```

Note the aftermath: `inner` **is** in the map and `outer` is not. The exception is a detector, not a transaction — the mutation the function performed is not rolled back. That is worth knowing before you catch one.

For the idiom itself — when to reach for `merge` over `computeIfAbsent`, the multimap pattern, counting — see [../utilities/04-map-default-methods.md](../utilities/04-map-default-methods.md). This section is about the mechanism.

**Pitfall:** `map.computeIfAbsent(k, key -> expensive())` where `expensive()` itself touches `map` is the recursive trap, and it is very easy to write by accident through two layers of helper methods — a memoised recursive function is the classic case. Compute the dependency *before* the call, or use a two-phase build.

**Insight:** the check is `mc != modCount`, not `mc < modCount`. A function that inserts one entry and removes another leaves `modCount` two higher, and is caught. A function that reads only leaves it unchanged, and is not. There is no way for a mutating function to slip through by balancing its changes, because every structural operation increments and none ever decrements.

**Interview:** *"Is `computeIfAbsent` atomic on `HashMap`?"* — No. It is a *single-traversal* operation, which is a performance property, not a concurrency one. Only `ConcurrentHashMap.computeIfAbsent` is atomic, and there it holds the bin lock for the duration of the mapping function — which is why calling a slow or reentrant function inside it can deadlock.

> **Definition.** The four default methods collapse read-modify-write into one traversal, differ systematically in whether a `null` result inserts nothing or removes the entry, and — `computeIfAbsent`, `compute` and `merge`, but not `computeIfPresent` — detect a mapping function that structurally modified the map by comparing `modCount` across the call.

---

## Pitfalls

### Believing `implements Comparable` is enough to get a tree bin

**Wrong**

```java
enum Status implements Comparable<Status> { A, B }   // does not even compile
// and the version that does compile:
enum Status { A, B }
// Status IS Comparable -- but via Enum<Status>, not its own interface list.
// comparableClassFor(Status.A) returns null. Bins of enum keys never treeify.
```

**Right**

```java
record Poison(int id) implements Comparable<Poison> {
    @Override public int hashCode() { return 0; }
    @Override public int compareTo(Poison o) { return Integer.compare(id, o.id); }
}
// comparableClassFor(new Poison(1)) == Poison.class -- the screen passes.
```

**Why people believe it:** `Status.A.compareTo(Status.B)` compiles and works, so the class is obviously `Comparable`. The screen is reflective and looks at `getGenericInterfaces()` of the concrete class only — inherited `Comparable` is invisible to it.

### Catching a `ConcurrentModificationException` from `computeIfAbsent` and retrying

**Wrong**

```java
try {
    map.computeIfAbsent(k, key -> { map.put(other, 1); return 2; });
} catch (ConcurrentModificationException e) {
    map.computeIfAbsent(k, key -> { map.put(other, 1); return 2; });   // same fault, twice the damage
}
```

**Right**

```java
// hoist the dependency out of the mapping function
map.putIfAbsent(other, 1);
map.computeIfAbsent(k, key -> 2);
```

**Why people believe it:** `ConcurrentModificationException` usually means "another thread interfered, try again". Here it means "the function you passed is structurally wrong", and retrying re-runs the same mutation. The demo shows the first attempt already left `inner` in the map.

## Cheat sheet

| Item | Rule | JDK 21 line |
|---|---|---|
| Screen | class must *directly* declare `implements Comparable<Self>` | 345 |
| `String` | special-cased, bypasses the reflective check | 348 |
| Enums | **fail** the screen — `Comparable` comes from `Enum<E>` | 345 |
| `compareComparables` | returns 0 when the class does not match; never throws | 366 |
| Treeify trigger | 8th node in a bin | 260, 631 |
| Treeify precondition | table capacity ≥ 64, else resize instead | 275, 761 |
| Screen fails, JDK | treeifies anyway, `tieBreakOrder` = class name then `identityHashCode` | 2058 |
| Screen fails, ours | leaves a plain chain — faster on that input | this file |
| Our lookup bound | O(log n) binary search — same as the JDK | this file |
| Our insert bound | **O(n)** array shift — the JDK is O(log n) | this file |
| Untreeify | JDK yes at ≤ 6 nodes; ours never | 267 |
| Mutation check | `int mc = modCount` before the function, compare after | 1227 |
| Detected in | `computeIfAbsent`, `computeIfPresent`, `compute`, `merge` | 1195–1400 |
| Not detected in | `Map`'s default `computeIfPresent` if you inherit it | — |
| `computeIfAbsent` returns null | nothing inserted | 1229 |
| `compute` / `merge` return null | entry **removed** | 1331, 1402 |
| `putIfAbsent` on a null value | **overwrites** it — "absent" means no *value*, not no *key* | 631 |
| CME is not a rollback | the function's mutation persists | 1227 |
| Atomicity | none on `HashMap`; only `ConcurrentHashMap` is atomic | — |

---

## Self-test

**Q1.** Why does `slot` scan left and right after a `compareTo` hit instead of returning `mid`?

<details><summary>Answer</summary>

Because `compareTo` and `equals` are permitted to disagree — a class can have a natural ordering inconsistent with equals (`BigDecimal` is the canonical example: `new BigDecimal("1.0").compareTo(new BigDecimal("1.00")) == 0` but they are not `equals`). Binary search finds *a* member of the run of `compareTo`-equal keys, not necessarily the one that is `equals` to the probe. So `slot` walks the whole tie run in both directions checking `equals`, and returns a negative insertion point only if none matches. The JDK's `TreeNode.find` has the same problem and solves it by searching both subtrees on a tie.

</details>

**Q2.** Our `treeifyBinAt` calls `replacementNode(e, null)` even though reusing the existing nodes would work. Why?

<details><summary>Answer</summary>

Because `MyLinkedHashMap` overrides `replacementNode` to run `transferLinks`, moving the discarded node's `before`/`after` pointers onto its replacement. If treeification reused the originals, the sorted bin would hold nodes that are `MyHashMap.Node` in some paths and `MyLinkedHashMap.Entry` in others, and the linked overlay would point at objects no longer in the bin — iteration order would silently diverge from the map's contents. Routing every node conversion through the factory is what lets file 10 add the overlay without touching this method.

</details>

**Q3.** Why does `treeifyBin` resize instead of treeifying when the table has fewer than 64 slots?

<details><summary>Answer</summary>

Because at small capacity, a bin of eight is much more likely to mean "too few buckets" than "colliding hash codes". With 16 slots and 8 entries in one bin, doubling to 32 will, for well-distributed keys, split that bin roughly in half — cheaper and better than building a tree. Only when the table already has 64+ slots does a bin of eight indicate that the keys themselves collide, at which point no amount of resizing helps and the bin structure has to change. `MIN_TREEIFY_CAPACITY` is documented as "at least `4 * TREEIFY_THRESHOLD`" (line 271) precisely to keep the two thresholds from fighting.

</details>

**Q4.** Both the JDK's tree bin and our sorted bin give O(log n) lookup. Where do they diverge, and which input exposes it?

<details><summary>Answer</summary>

Insertion and deletion. The JDK's red-black tree inserts in O(log n) with a rebalance; our sorted array inserts in O(n) because of the `System.arraycopy` shift. The exposing input is exactly the DoS workload: inserting n keys with identical hash codes costs the JDK O(n log n) total and costs us O(n²). File 10b measures both — our sorted bin is roughly half the cost of a pure chain but nowhere near the JDK's tree, while our *lookup* on the same data matches the JDK's almost exactly. Bounding lookup and not insert is the honest one-line summary.

</details>

**Q5.** `computeIfAbsent` throws `ConcurrentModificationException`. Is the map unchanged?

<details><summary>Answer</summary>

No. The check happens *after* the mapping function has already run and already mutated the map; the exception reports the fault, it does not undo it. In the demo, the mapping function put `inner=1` and then the exception fired, leaving `{inner=1}` — with `outer` never inserted. Treat the exception as "your code has a structural bug", not as "the operation was rejected".

</details>

**Q6.** Name the three methods where a `null` return from the function removes the entry, and the one where it does not.

<details><summary>Answer</summary>

`compute`, `computeIfPresent` and `merge` all remove the entry when the remapping function returns `null`. `computeIfAbsent` does not — a `null` from the mapping function simply means "no mapping to create", and nothing is inserted (and nothing existing is touched, because `computeIfAbsent` only runs the function when there was no live value in the first place). The demo prints all four cases.

</details>

---

**Leaves covered:** 4.3.7, 4.3.8 (2 leaves)
**Leaves deferred:** none — 4.3.1–4.3.2 are in [06-build-my-hash-map.md](06-build-my-hash-map.md), 4.3.3 in [06a-build-my-hash-map-a2-lazy-allocation-and-hooks.md](06a-build-my-hash-map-a2-lazy-allocation-and-hooks.md), 4.3.4–4.3.6 in [07-build-my-hash-map-b-put-get-resize.md](07-build-my-hash-map-b-put-get-resize.md), 4.3.9–4.3.10 in [09-build-my-hash-map-d-views-and-iterator.md](09-build-my-hash-map-d-views-and-iterator.md), 4.3.11–4.3.12 in [10-build-my-hash-map-e-set-linked-and-diff.md](10-build-my-hash-map-e-set-linked-and-diff.md), 4.3.13–4.3.14 in [10b-build-my-hash-map-g-diff-and-collision-dos.md](10b-build-my-hash-map-g-diff-and-collision-dos.md)
**Diagrams included:** none new — the `put` trace (D-146, frames a–d) is embedded in [06a-build-my-hash-map-a2-lazy-allocation-and-hooks.md](06a-build-my-hash-map-a2-lazy-allocation-and-hooks.md)
**Target version:** Java 21 LTS
**Lines:** 584
