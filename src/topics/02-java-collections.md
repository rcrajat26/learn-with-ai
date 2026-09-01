# 02 — Java Collections

The Collections Framework is the most-probed library area in Java interviews because the internals are
knowable and the trade-offs are real. Know the constants. Interviewers use them as a proxy for whether
you have read the source.

Deep concurrency semantics (memory model, atomicity, locking) live in guide 05; this file covers the
concurrent collections only at the "which one and why" level.

---

## 1. The hierarchy

`Collection` is the root of sequences and sets. `Map` is **not** a `Collection` — it stores pairs, not
elements, so it deliberately sits outside the hierarchy.

```
Iterable
└── Collection
    ├── List      — ordered, indexed, duplicates allowed
    │   ├── ArrayList, LinkedList, Vector (legacy), CopyOnWriteArrayList
    ├── Set       — no duplicates
    │   ├── HashSet, LinkedHashSet
    │   └── SortedSet → NavigableSet → TreeSet, ConcurrentSkipListSet
    └── Queue     — insertion/removal at ends
        ├── Deque → ArrayDeque, LinkedList
        ├── PriorityQueue
        └── BlockingQueue → ArrayBlockingQueue, LinkedBlockingQueue, ...

Map
├── HashMap → LinkedHashMap
├── SortedMap → NavigableMap → TreeMap, ConcurrentSkipListMap
├── Hashtable (legacy), ConcurrentHashMap
├── EnumMap, IdentityHashMap, WeakHashMap
```

Choosing quickly: need order of insertion → `ArrayList`/`LinkedHashMap`. Need sorted order →
`TreeMap`/`TreeSet`. Need uniqueness only → `HashSet`. Need both ends → `ArrayDeque`. Need
priority → `PriorityQueue`. Need thread safety → `ConcurrentHashMap`/`CopyOnWriteArrayList`.

---

## 2. ArrayList internals

Backed by an `Object[] elementData`. `size` is the logical count; `elementData.length` is capacity.

- Default capacity is **10**, allocated lazily on first add (an empty `new ArrayList<>()` starts with a
  shared empty array, so an unused list costs almost nothing).
- Growth is `newCapacity = oldCapacity + (oldCapacity >> 1)` — **1.5×**, not 2×. So 10 → 15 → 22 → 33.
- Growth copies via `Arrays.copyOf`, i.e. `System.arraycopy` — an intrinsic, very fast, but still O(n).

Costs: `get`/`set` O(1). `add` at the end amortized O(1). `add`/`remove` at index i is O(n−i) shifting.
`contains`/`indexOf` O(n) linear scan.

`ensureCapacity(n)` or `new ArrayList<>(n)` pre-sizes and eliminates all intermediate copies. Do this
whenever you know the size — it is the single highest-value ArrayList optimization.

**Trap:** `remove` on a list is overloaded. `remove(int index)` removes by position; `remove(Object o)`
removes by value. With a `List<Integer>`, `list.remove(2)` removes index 2, while
`list.remove(Integer.valueOf(2))` removes the element 2. This is a classic interview question and a
real production bug.

**Trap:** `Arrays.asList(arr)` returns a fixed-size view backed by the array. `add`/`remove` throw
`UnsupportedOperationException`, and `set` writes through to the original array. `List.of(...)`
(Java 9+) is fully immutable and rejects nulls.

---

## 3. LinkedList internals

A doubly linked list of `Node` objects, each holding `item`, `prev`, `next`. It implements both `List`
and `Deque`.

Costs: `addFirst`/`addLast`/`removeFirst`/`removeLast` O(1). `get(i)` O(n) — though it walks from
whichever end is closer. Insert/remove at a known iterator position O(1).

**Trap:** LinkedList is almost never the right choice in practice. Every element costs a separate
object (24+ bytes of overhead versus a 4–8 byte array slot), pointer chasing destroys cache locality,
and the O(1) insert only materializes if you already hold the node. Even for queue workloads,
`ArrayDeque` beats it. Use LinkedList in an interview answer only to contrast with ArrayList.

---

## 4. ArrayDeque internals

A resizable **circular buffer** over an array with `head` and `tail` indices. Adding at either end is
amortized O(1) with no per-element allocation. Capacity is a power of two so index wrapping is a
bitmask (`(head - 1) & (elements.length - 1)`) rather than a modulo.

It is the recommended implementation for both `Stack` and `Queue`.

**Trap:** `ArrayDeque` does not permit `null`, because null is its internal empty-slot sentinel.
`LinkedList` permits it. Code that queues possibly-null values will NPE on insert.

**Trap:** `java.util.Stack` extends `Vector` — synchronized on every method (paying for locks you do
not need) and its iterator goes bottom-to-top, which is the opposite of pop order.

---

## 5. HashMap — the deep dive

This is the single most examined class in Java interviews.

### Structure
An array `Node<K,V>[] table` of **buckets**. Each bucket holds either a linked list of nodes or a
red-black tree. Each `Node` stores `hash`, `key`, `value`, `next`.

### Constants you must know
| Constant | Value | Meaning |
|---|---|---|
| `DEFAULT_INITIAL_CAPACITY` | 16 | initial bucket count, always a power of two |
| `DEFAULT_LOAD_FACTOR` | 0.75 | resize when size > capacity × 0.75 |
| `TREEIFY_THRESHOLD` | 8 | bucket converts list → red-black tree at 8 nodes |
| `UNTREEIFY_THRESHOLD` | 6 | tree reverts to list on shrink (hysteresis avoids thrashing) |
| `MIN_TREEIFY_CAPACITY` | 64 | below this table size, a long bucket triggers a resize instead of treeifying |

### The spread function
Capacity is a power of two, so the bucket index is `hash & (capacity - 1)` — a bitmask, far cheaper
than a modulo. But masking keeps only the *low* bits, so two keys differing only in high bits would
collide. `HashMap.hash()` fixes this:

```java
static final int hash(Object key) {
    int h;
    return (key == null) ? 0 : (h = key.hashCode()) ^ (h >>> 16);
}
```

XOR-ing the high 16 bits into the low 16 mixes high-bit entropy down into the masked region. One shift
and one XOR — deliberately cheap.

### Why 0.75
It is the empirical balance point. Lower load factor means fewer collisions but more wasted memory and
more resizes; higher means denser buckets and longer chains. At 0.75 with a good hash, bucket
occupancy follows a Poisson distribution where a bucket reaching 8 elements has probability under one
in ten million — which is exactly why 8 was chosen as the treeify threshold.

### Resizing
When `size > capacity * loadFactor`, the table **doubles**. Since capacity is a power of two, each
entry either stays at index `i` or moves to `i + oldCapacity`, decided by a single bit test
(`(hash & oldCapacity) == 0`). Java 8+ exploits this to split each bucket into a "lo" and "hi" list
without recomputing hashes, and it preserves relative order — which fixed the Java 7 infinite-loop
bug under concurrent resize (Java 7 reversed the list during transfer).

### Treeification
At 8 nodes in one bucket, if the table is at least 64 entries, the bucket becomes a red-black tree,
bounding worst-case lookup at O(log n) instead of O(n). This is a defence against hash-collision DoS
attacks. Below capacity 64 the map resizes instead, on the theory that the collisions are from a small
table rather than a bad hash.

### Costs
`get`/`put`/`remove` average O(1), worst case O(log n) after treeification (O(n) before Java 8).

**Trap:** sizing. `new HashMap<>(100)` does not hold 100 entries without resizing — it rounds up to
capacity 128, and the resize threshold is 128 × 0.75 = 96. To hold n entries resize-free, pass
`n / 0.75 + 1`. Java 19+ offers `HashMap.newHashMap(n)` which does this arithmetic for you.

**Trap:** null handling. `HashMap` allows one null key (bucket 0) and many null values. `Hashtable` and
`ConcurrentHashMap` allow neither. With HashMap, `get(k) == null` is ambiguous between "absent" and
"mapped to null" — use `containsKey` when it matters.

---

## 6. LinkedHashMap and LRU caches

`LinkedHashMap` extends `HashMap` and adds a doubly linked list threading all entries, giving
predictable iteration order at a small memory cost.

Two modes:
- **Insertion order** (default) — iterates in the order keys were first inserted. Re-putting an
  existing key does not move it.
- **Access order** (`accessOrder = true` in the 3-arg constructor) — every `get` and `put` moves the
  entry to the tail. The head is therefore the least recently used.

That is an LRU cache in ten lines:

```java
class LruCache<K, V> extends LinkedHashMap<K, V> {
    private final int capacity;
    LruCache(int capacity) {
        super(capacity, 0.75f, true);   // true = access order
        this.capacity = capacity;
    }
    @Override protected boolean removeEldestEntry(Map.Entry<K, V> eldest) {
        return size() > capacity;
    }
}
```

`removeEldestEntry` is a hook `HashMap` calls after every insertion; returning true evicts the head.

**Trap:** access-order `LinkedHashMap` mutates its linked list on `get`, so a plain read is a
structural change from the iterator's perspective and is not thread-safe even for concurrent readers.
Wrap with `Collections.synchronizedMap` or use Caffeine.

---

## 7. TreeMap and navigation

A **red-black tree**: a self-balancing BST maintaining these invariants — nodes are red or black, the
root is black, no red node has a red child, and every path from a node to its leaves contains the same
number of black nodes. Those rules bound the longest path at twice the shortest, giving height
O(log n). Insert and delete restore the invariants via rotations and recolouring.

All of `get`, `put`, `remove`, `containsKey` are O(log n) — never O(1), which is the price of order.

Ordering comes from the keys' `Comparable` or a supplied `Comparator`.

The `NavigableMap` API is the reason to reach for TreeMap:

| Method | Returns |
|---|---|
| `floorKey(k)` | greatest key ≤ k |
| `ceilingKey(k)` | least key ≥ k |
| `lowerKey(k)` | greatest key strictly < k |
| `higherKey(k)` | least key strictly > k |
| `firstKey` / `lastKey` | extremes |
| `headMap` / `tailMap` / `subMap` | live range views |
| `descendingMap` | reversed view |

These make TreeMap the right structure for time-series bucketing, rate limiters, interval lookup, and
"find the closest match" problems.

**Trap:** TreeMap uses `compareTo`/`compare` for equality, **not** `equals`. If your comparator says
two objects are equal, the map treats them as the same key even if `equals` disagrees. This is how a
`TreeSet` silently drops elements: a comparator that only compares one field collapses distinct
objects. `Comparable` should be consistent with `equals`.

**Trap:** TreeMap rejects null keys (it must call `compareTo` on them).

---

## 8. Set variants

Every `Set` in the JDK is a thin wrapper over the corresponding `Map` with a shared dummy value object.
`HashSet` holds a `HashMap`; `add` returns `map.put(e, PRESENT) == null`. Everything you know about
HashMap sizing, hashing and resizing therefore applies to HashSet unchanged.

- `HashSet` — O(1) average, no order guarantee, allows one null.
- `LinkedHashSet` — O(1) with insertion order preserved; the right default when you dedupe but the
  output order should be stable and reproducible.
- `TreeSet` — O(log n), sorted, `NavigableSet` methods (`floor`, `ceiling`, `headSet`, `pollFirst`).
- `EnumSet` — a bit vector over the enum constants. Extremely fast and compact; use it whenever the
  element type is an enum.
- `CopyOnWriteArraySet` — for tiny, read-dominated, concurrently accessed sets (listener lists).

---

## 9. PriorityQueue mechanics

A binary min-heap in an `Object[]`. For index i: parent `(i-1)>>>1`, children `2i+1`, `2i+2`.

- `peek` O(1), `offer` O(log n) via `siftUp`, `poll` O(log n) via `siftDown`.
- `remove(Object)` is O(n) — it must scan to find the element first.
- `contains` is O(n).
- Default capacity 11; growth is doubling below 64 and 1.5× above.
- Constructing from an existing collection uses `heapify`, which is O(n).

Max-heap via `new PriorityQueue<>(Comparator.reverseOrder())`.

**Trap:** iteration order and `toString` are heap-array order, which is *not* sorted. Only successive
`poll()` calls produce sorted output. People assert on `toString` in tests and get burned.

**Trap:** mutating an element's priority field after insertion does not reheapify. The invariant
breaks silently. Remove, mutate, re-insert.

---

## 10. equals and hashCode

The contract:
1. Consistent — repeated calls return the same result while the object is unchanged.
2. `a.equals(b)` implies `b.equals(a)` (symmetric), and equality is reflexive and transitive.
3. **`a.equals(b)` implies `a.hashCode() == b.hashCode()`.**
4. Unequal objects *may* share a hash code (a collision), that is legal but degrades performance.
5. `x.equals(null)` is false.

Break rule 3 and your object becomes undiscoverable in any hash-based structure: you insert it, then
look it up with an equal object, and the lookup hashes to a different bucket and finds nothing.

Both must be derived from the same fields, and those fields should be immutable.

**Trap — the mutable key:** put an object in a HashSet, mutate a field used by `hashCode`, then call
`contains(sameObject)`. It returns false. The entry is stranded in the old bucket, still consuming
memory, unreachable by lookup though still visible to iteration. Never mutate key state.

**Trap:** overloading instead of overriding. `public boolean equals(MyType other)` does not override
`Object.equals(Object)`. Collections call the `Object` version and fall back to identity. Always
annotate `@Override`.

**Trap:** using `getClass() != o.getClass()` versus `instanceof` changes subclass behaviour.
`instanceof` can break symmetry with subclasses that add fields; `getClass()` breaks Liskov
substitution. Records sidestep this by being final with generated implementations.

Java 16+ `record` generates both correctly from all components — the best default for value types.

---

## 11. Fail-fast iterators and ConcurrentModificationException

Every `ArrayList`, `HashMap`, etc. keeps a `modCount` incremented on every structural modification
(add, remove, clear — *not* `set` on a list or value replacement in a map). An iterator snapshots
`modCount` at creation as `expectedModCount` and compares on every `next()`. A mismatch throws
`ConcurrentModificationException`.

This is a **best-effort bug detector**, not a thread-safety guarantee — it is not reliably thrown, and
its absence proves nothing.

```java
// Throws CME
for (String s : list) if (s.startsWith("x")) list.remove(s);

// Correct: iterator's own remove keeps expectedModCount in sync
Iterator<String> it = list.iterator();
while (it.hasNext()) if (it.next().startsWith("x")) it.remove();

// Correct and clearer
list.removeIf(s -> s.startsWith("x"));
```

**Trap:** removing the second-to-last element in an indexed for-each loop can complete *without* CME,
because `hasNext()` returns false when `cursor == size` and the check never runs. So the bug hides
some of the time — the worst kind.

**Fail-safe** alternatives iterate a snapshot or a live-but-tolerant view:
`CopyOnWriteArrayList` (iterator sees the array as of creation; writes copy the whole array — reads
free, writes O(n)) and `ConcurrentHashMap` (weakly consistent iterator, never throws CME, may or may
not reflect concurrent updates).

---

## 12. Collections utilities

- `Collections.unmodifiableList/Set/Map(c)` — an unmodifiable **view**. The underlying collection can
  still change and the view reflects it. `List.copyOf(c)` makes a genuinely independent immutable copy.
- `Collections.synchronizedList/Map(c)` — wraps every method in a lock on a single mutex. Compound
  operations still need external synchronization, and **iteration must be manually synchronized** on
  the wrapper or you get CME.
- `Collections.emptyList()` / `singletonList(x)` — allocation-free constants; useful in hot paths.
- `Collections.sort`, `reverse`, `shuffle`, `swap`, `frequency`, `disjoint`, `nCopies`, `min`, `max`,
  `binarySearch`.
- `List.of` / `Map.of` / `Set.of` (Java 9) — immutable, reject nulls, throw on duplicate keys, and
  have unspecified iteration order that is deliberately randomized per JVM run so you cannot depend on
  it.

**Trap:** `Map.of` is limited to 10 pairs; beyond that use `Map.ofEntries(entry(k, v), ...)`.

---

## 13. Concurrent collections — orientation only

| Class | Use when | Mechanism sketch |
|---|---|---|
| `ConcurrentHashMap` | general concurrent map | per-bin CAS + `synchronized` on the first node; no whole-map lock |
| `CopyOnWriteArrayList` | many reads, very few writes | every write copies the backing array |
| `ConcurrentLinkedQueue` | unbounded non-blocking queue | lock-free CAS (Michael-Scott) |
| `ArrayBlockingQueue` | bounded producer-consumer | one lock plus not-full/not-empty conditions |
| `LinkedBlockingQueue` | producer-consumer, higher throughput | separate head/tail locks |
| `ConcurrentSkipListMap` | concurrent *sorted* map | lock-free skip list, O(log n) |

`ConcurrentHashMap` replaced Java 7's segment locking (16 fixed segments) with per-bucket locking in
Java 8, so contention scales with the table size.

**Trap:** thread-safe individual operations do not make compound operations atomic.
`if (!map.containsKey(k)) map.put(k, v)` is a race even on a ConcurrentHashMap. Use the atomic
compound methods: `putIfAbsent`, `computeIfAbsent`, `merge`, `compute`, `replace`.

Full treatment — happens-before, `computeIfAbsent` recursion deadlock, sizing semantics — is in
guide 05.

---

## 14. Comparator fluency

Since Java 8, comparators compose:

```java
people.sort(Comparator.comparing(Person::lastName)
                      .thenComparing(Person::firstName)
                      .thenComparingInt(Person::age)
                      .reversed());

// nulls last, natural order within non-nulls
list.sort(Comparator.nullsLast(Comparator.naturalOrder()));

// custom key extractor with its own comparator
list.sort(Comparator.comparing(Order::customer, byCustomerPriority));
```

Use the primitive specializations `comparingInt`, `comparingLong`, `comparingDouble` to avoid boxing
on every comparison in a hot sort.

**Trap:** `reversed()` applies to the *whole* chain built so far, not just the last key. If you want
last-name ascending and age descending, write
`comparing(Person::lastName).thenComparing(Person::age, reverseOrder())`.

**Trap:** a comparator that is inconsistent (not transitive, or asymmetric) makes `Collections.sort`
throw `IllegalArgumentException: Comparison method violates its general contract!` — because TimSort
detects the inconsistency mid-merge. The usual cause is subtracting ints (`a.value - b.value`)
and overflowing. Use `Integer.compare(a, b)`.

`Arrays.sort` on primitives uses dual-pivot quicksort (O(n log n) average, in place, not stable).
`Arrays.sort`/`Collections.sort` on objects uses TimSort — stable, adaptive, O(n) on nearly-sorted
input, O(n) extra space. Stability is why you can sort by one key then another and keep the first
ordering within ties.

---

## Atomic concept checklist

- [ ] `Map` is not a `Collection`.
- [ ] ArrayList grows 1.5×, default capacity 10, allocated lazily; pre-size when the count is known.
- [ ] `list.remove(int)` removes by index and `list.remove(Object)` by value — the ambiguity bites `List<Integer>`.
- [ ] `Arrays.asList` is a fixed-size write-through view; `List.of` is immutable and null-hostile.
- [ ] LinkedList loses to ArrayDeque for queues and to ArrayList for almost everything else.
- [ ] ArrayDeque is a power-of-two circular buffer and forbids null; `java.util.Stack` is legacy and iterates backwards.
- [ ] HashMap: capacity 16, load factor 0.75, treeify at 8 nodes only above table size 64, untreeify at 6.
- [ ] Bucket index is `hash & (capacity-1)`, which is why `hash()` XORs the high 16 bits down.
- [ ] Resize doubles capacity and splits each bucket by one bit test, preserving order.
- [ ] `new HashMap<>(n)` does not hold n entries without resizing; pass `n/0.75 + 1`.
- [ ] HashMap allows one null key; ConcurrentHashMap and Hashtable allow none.
- [ ] LinkedHashMap in access-order mode plus `removeEldestEntry` is an LRU cache; access-order `get` mutates state.
- [ ] TreeMap is a red-black tree, O(log n), and uses `compareTo` rather than `equals` for key identity.
- [ ] NavigableMap's floor/ceiling/subMap are the reason to choose TreeMap.
- [ ] Every Set is a Map wrapper with a dummy value; EnumSet is a bit vector.
- [ ] PriorityQueue iteration is not sorted; `remove(Object)` is O(n); mutating priority after insert corrupts the heap.
- [ ] Equal objects must have equal hash codes; mutable keys strand entries in the wrong bucket.
- [ ] `equals(MyType)` overloads rather than overrides — always use `@Override`.
- [ ] CME comes from a `modCount`/`expectedModCount` mismatch and is best-effort, not a guarantee.
- [ ] Use `Iterator.remove` or `removeIf` to remove during traversal.
- [ ] `unmodifiableList` is a view; `List.copyOf` is a copy.
- [ ] `synchronizedMap` still requires manual synchronization around iteration and compound actions.
- [ ] Atomic per-operation safety does not make check-then-act atomic; use `computeIfAbsent`/`merge`.
- [ ] `Comparator.reversed()` reverses the whole chain built so far.
- [ ] Never compare by subtraction — it overflows and TimSort will throw a contract-violation error.
- [ ] Object sorts use stable TimSort; primitive sorts use unstable dual-pivot quicksort.