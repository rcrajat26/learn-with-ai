# 02 Java Collections — The drills: numbers, matrices, cost, which-one, mechanism (§5.3)

**Target version: Java 21 LTS.** | [Index](00-index.md)
Previous: [93-drills-and-traps.md](93-drills-and-traps.md) · Next: [93c-code-reading-and-schedule.md](93c-code-reading-and-schedule.md)

Five drills, each one a *recall* exercise rather than a reading exercise. Cover the right-hand column,
work down the left, and say the answer out loud — writing it down is slower and less like the
interview. Anything you miss twice goes on a list; the spaced-repetition schedule in
[93c](93c-code-reading-and-schedule.md) is built around that list.

The trap index these drills draw on is in [93](93-drills-and-traps.md).

## §5.3.1 The numbers drill

Recite the value **and** one sentence of why it is that value. A number without its reason is worth
nothing in an interview, because the follow-up is always "why?".

### The constants that come up most

| Prompt | Value | Why that value |
|---|---|---|
| `HashMap` default capacity | 16 | `1 << 4`; power of two so the index is a mask |
| `HashMap` load factor | 0.75f | Poisson λ = 0.5 makes an 8-node bin a 6-in-100-million event while the array is only ~20% of the footprint |
| `TREEIFY_THRESHOLD` | 8 | the point where a long bin is evidence of bad hashes rather than bad luck |
| `UNTREEIFY_THRESHOLD` | 6 | a hysteresis band of 2, which must exceed the maximum per-operation size change of 1 |
| `MIN_TREEIFY_CAPACITY` | 64 | `4 × TREEIFY_THRESHOLD`; below it, resizing is cheaper than treeifying |
| `HashMap` maximum capacity | `1 << 30` | the largest power of two that is a positive `int` |
| Nodes in a bin when it treeifies | 9 | `binCount` counts hops from an already-rejected head |
| First `TreeNode` in a default-sized map | the 11th insert | two resizes first, because the table starts below 64 slots |
| `ArrayList` default capacity | 10 | applied on the first `add` from the defaulted sentinel |
| `ArrayList` growth factor | 1.5× | `old + (old >> 1)`; below φ ≈ 1.618 so freed blocks can be reused |
| `ArrayList` growth ladder | 10, 15, 22, 33, 49, 73 | — |
| `new ArrayList<>(0)` ladder | 1, 2, 3, 4, 6, 9, 13 | `newLength(0, 1, 0)` gives 1, not 10 |
| `Vector` growth | 2× | only when `capacityIncrement` is 0 or unset |
| Max array length | `Integer.MAX_VALUE - 8` | `SOFT_MAX_ARRAY_LENGTH`; the 8 is header headroom on some VMs |
| `ArrayDeque` no-arg capacity | 17 | `new Object[16 + 1]`; one slot must stay empty. **Since JDK 12** |
| `ArrayDeque` growth jump | `old < 64 ? old + 2 : old >> 1` | roughly doubles while small, then 50% |
| `PriorityQueue` default capacity | 11 | arbitrary, unchanged since Java 5 |
| `PriorityQueue` capacity ladder | 11, 24, 50, 102, 153 | same jump rule as `ArrayDeque` |
| `Hashtable` default capacity | 11 | and growth is `(oldCapacity << 1) + 1` |
| Last prime in `Hashtable`'s ladder | 6,143 | only 6 of the first 15 capacities are prime at all |
| `IdentityHashMap` default capacity | 32 | table length 64, because keys and values interleave |
| `IdentityHashMap` load factor | 2/3 of capacity | i.e. 1/3 of `table.length`; a default map resizes on the 22nd put |
| `IdentityHashMap` index multiplier | −254 | `(h << 1) - (h << 8)`; even, so the result is an even slot |
| `WeakHashMap` defaults | 16 and 0.75f | a real initial *capacity*, unlike `IdentityHashMap` |
| `EnumSet` Regular/Jumbo boundary | 64 constants | one `long` versus a `long[]` |
| `String.hashCode` multiplier | 31 | odd prime, and `31 = 2^5 − 1` so the JIT shifts |
| `Boolean.hashCode` | 1231 / 1237 | arbitrary constants |
| `"Aa"` and `"BB"` hash | 2112 both | and 2ᵏ collisions from k concatenated blocks |
| `Integer` cache range | −128..127 | `valueOf` shares those instances |
| TimSort `MIN_MERGE` | 32 | below it, binary insertion sort |
| `parallelSort` sequential cutover | 8192 | `MIN_ARRAY_SORT_GRAN` |
| `IteratorSpliterator` batch | `BATCH_UNIT = 1024`, `MAX_BATCH = 1 << 25` | why a small `LinkedList` splits into one chunk |
| `Map.of` maximum pairs | 10 | 11 pairs is a compile error; use `Map.ofEntries` |
| `EXPAND_FACTOR` | 2 | a **correctness** requirement — at 1, `probe` on a miss would not terminate |
| `MIN_TRANSFER_STRIDE` | 16 | the floor on a `ConcurrentHashMap` resize claim |
| `MAX_RESIZERS` | 65535 | the low 16 bits of `sizeCtl` |
| `RESIZE_STAMP_BITS` / `SHIFT` | 16 / 16 | the high half of `sizeCtl` is a table-size stamp |
| `MOVED` / `TREEBIN` / `RESERVED` | −1 / −2 / −3 | the only negative `Node.hash` values |
| `ConcurrentSkipListMap` levels | max 62, `k = 1`, `p = 0.5` | 1-in-4 nodes indexed at all, then half per extra level |
| Java 7 `ConcurrentHashMap` segments | 16 default, 65,536 max | `DEFAULT_CONCURRENCY_LEVEL`, `MAX_SEGMENTS` |
| `LinkedBlockingQueue` default capacity | `Integer.MAX_VALUE` | the unbounded trap |

### The byte arithmetic

| Prompt | Value |
|---|---|
| Object header, compressed oops | 12 B |
| Array header | 16 B |
| Reference | 4 B, or 8 B above the ~32 GB cliff |
| Rounding quantum | 8 B |
| `Integer` / `Long` | 16 B / 24 B |
| `HashMap.Node` | 32 B |
| `LinkedHashMap.Entry` | 40 B |
| `HashMap.TreeNode` | 56 B |
| `TreeMap.Entry` | 40 B |
| `LinkedList` node | 24 B |
| Empty `ArrayList` / `HashMap` | ~24 B / ~48 B, with nothing allocated |
| `HashMap<Integer,Integer>` per entry | ~69 B idealised, ~72 B measured at n = 10⁶ |
| `List.of(a, b)` | 24 B, one object, no array |
| `new ArrayList<>(List.of(a, b))` | 48 B |
| Hand-built LRU entry vs `LinkedHashMap` | 64 B vs 40 B |

### The `Collections` thresholds

| Prompt | Value |
|---|---|
| `BINARYSEARCH_THRESHOLD` | 5000 |
| `REVERSE_THRESHOLD` | 18 |
| `SHUFFLE_THRESHOLD` | 5 |
| `FILL_THRESHOLD` | 25 |
| `ROTATE_THRESHOLD` | 100 |
| `COPY_THRESHOLD` | 10 |
| `REPLACEALL_THRESHOLD` | 11 |
| `INDEXOFSUBLIST_THRESHOLD` | 35 |

All eight exist for one reason: above the threshold, a non-`RandomAccess` list is walked with an
iterator instead of by index, so the algorithm does not become O(n²) on a `LinkedList`.

## §5.3.2 The matrices drill

Four matrices. Recite each row *with its reason* — the reason is what makes it recallable.

### Null policy

| Class | Null key | Null value | The mechanical reason |
|---|---|---|---|
| `HashMap`, `LinkedHashMap` | one | any | `null` hashes to 0 and is matched by `==` |
| `IdentityHashMap` | one | any | via a `NULL_KEY` sentinel |
| `WeakHashMap` | one | any | same sentinel trick |
| `TreeMap` / `TreeSet` | no, under natural ordering | any | `null.compareTo(...)` cannot run; a null-tolerant `Comparator` lifts the ban |
| `Hashtable` | no | no | 1.0-era defensiveness |
| `ConcurrentHashMap` | no | no | `get` returning `null` must unambiguously mean absent |
| `ArrayDeque` | n/a | rejects elements | `null` marks a free slot |
| `PriorityQueue` | n/a | rejects elements | `queue[0] == null` is the emptiness test |
| `EnumMap` | no | yes | a key must have an `ordinal()` |
| `ArrayList`, `LinkedList` | n/a | allows | nothing depends on `null` |
| `List.of`/`Set.of`/`Map.of` | no | no | fail-fast; even `contains(null)` throws |
| `Arrays.asList`, `unmodifiable*`, `Stream.toList()` | n/a | allows | they inherit the backing store's policy |

### Thread safety and iterator contract

| Class | Safety | Iterator |
|---|---|---|
| `ArrayList`, `HashMap`, `TreeMap`, `ArrayDeque`, `PriorityQueue` | none | fail-fast |
| `Vector`, `Hashtable` | coarse `synchronized` | fail-fast via `iterator()`; **not** via `elements()`/`keys()` |
| `Collections.synchronized*` | one mutex per call | fail-fast, and **unsynchronized** — lock the loop yourself |
| `CopyOnWriteArrayList`/`ArraySet` | lock-free reads, copying writes | snapshot; `remove` throws |
| `ConcurrentHashMap` | per-bin CAS + monitor | weakly consistent |
| `ConcurrentSkipListMap`/`Set` | lock-free | weakly consistent |
| `ArrayBlockingQueue` | 1 lock, 2 conditions | weakly consistent |
| `LinkedBlockingQueue` | 2 locks | weakly consistent |
| `ConcurrentLinkedQueue` | Michael–Scott lock-free | weakly consistent |
| `List.of`/`Set.of`/`Map.of` | immutable, so safe | immutable |

### Ordering

| Guarantee | Classes |
|---|---|
| insertion / encounter order | `ArrayList`, `LinkedList`, `ArrayDeque`, `LinkedHashMap`, `LinkedHashSet`, `CopyOnWriteArrayList` |
| sorted by comparator | `TreeMap`, `TreeSet`, `ConcurrentSkipListMap`/`Set`, `PriorityBlockingQueue` on drain |
| ordinal order | `EnumMap`, `EnumSet` |
| heap order, not sorted | `PriorityQueue`, `DelayQueue` on iteration |
| unspecified but deterministic per build | `HashMap`, `HashSet`, `Hashtable`, `IdentityHashMap`, `WeakHashMap` |
| **randomised per JVM run** | `Set.of`, `Map.of`, `Set.copyOf`, `Map.copyOf` |
| access order, on request | `LinkedHashMap(cap, lf, true)` |

### Mutability tiers

| Rung | Factory | `set` | `add`/`remove` | Nulls | Reflects source |
|---|---|---|---|---|---|
| 0 | `new ArrayList<>`, `new HashMap<>`, **`EnumSet.of`** | yes | yes | yes | n/a |
| 1a | `Arrays.asList` | **yes, write-through** | throws | yes | yes, both ways |
| 1b | `Collections.nCopies` | throws | throws | yes | n/a |
| 2 | `Collections.unmodifiable*` | throws | throws | yes | **yes** |
| 3 | `List.copyOf` / `Set.copyOf` / `Map.copyOf` | throws | throws | **NPE** | no |
| 4 | `List.of` / `Set.of` / `Map.of` | throws | throws | **NPE**, and duplicates rejected for `Set`/`Map` | no |

Every rung is shallow. `EnumSet.of` sitting at rung 0 is the row people get wrong.

## §5.3.3 The cost drill

State **amortised/expected** and **worst case** for each, from memory.

| Operation | Amortised / expected | Worst case | The reason for the worst case |
|---|---|---|---|
| `ArrayList.get(i)` | O(1) | O(1) | one address computation |
| `ArrayList.add(e)` | O(1) | **O(n)** | the growth copy |
| `ArrayList.add(i, e)` | O(n − i) | O(n) | one `arraycopy` |
| `ArrayList.remove(i)` | O(n − i) | O(n) | one `arraycopy`; `remove(size-1)` copies nothing |
| `ArrayList.contains` | O(n) | O(n) | linear scan |
| `ArrayList.removeIf` | O(n) | O(n) | two-pass bitset — but the interface **default** is O(n²) |
| `LinkedList.get(i)` | O(n) | `⌊(n−1)/2⌋` hops | walks from the nearer end |
| `LinkedList.addFirst/addLast` | O(1) | O(1) | pointer writes only |
| `LinkedList` splice at a held cursor | O(1) | O(1) | the only case it wins |
| `ArrayDeque.addFirst/addLast` | O(1) | **O(n)** | the growth copy plus the un-wrap slide |
| `ArrayDeque.remove(Object)` | O(n) | O(n) | scan, then shift the shorter side |
| `HashMap.get/put` | O(1) | **O(log n)** per treeified bin, O(n) untreeified or non-`Comparable` | bin length |
| `HashMap.resize` | — | O(capacity) | every slot is visited |
| `HashMap` iteration | O(capacity + size) | same | empty slots are visited too |
| `HashMap.containsValue` | O(n) | O(n) | no value index exists |
| `LinkedHashMap` iteration | O(size) | O(size) | walks the order list, not the table |
| `LinkedHashMap.get`, access order | O(1) **write** | O(1) | six pointer writes + `modCount++` |
| `TreeMap.get/put/remove` | O(log n) | O(log n) | `h ≤ 2·log₂(n+1)`, with a large constant |
| `TreeMap` iteration | O(n) | O(n) | amortised O(1) per successor step |
| `TreeMap` range-view creation | O(1) | O(1) | cost deferred to iteration |
| `new TreeMap<>(sortedMap)` | **O(n)** | O(n) | `buildFromSorted`, zero comparisons |
| `TreeMap` range-view `size()` | O(k) | O(k) | not cached |
| `PriorityQueue.offer` | O(log n), ~1.6 comparisons expected | O(log n) | `siftUp` |
| `PriorityQueue.poll` | O(log n) | O(log n) | `siftDown`, ~2·log₂ n comparisons |
| `PriorityQueue.peek` | O(1) | O(1) | index 0 |
| `new PriorityQueue<>(collection)` | **O(n)** | O(n) | `heapify`; `addAll` is O(n log n) |
| `PriorityQueue.remove(Object)` | O(n) | O(n) | linear `indexOf`, then O(log n) repair |
| `EnumMap.get/put` | O(1) | **O(1)** | array index by ordinal — no collisions possible |
| `EnumSet` bulk ops | O(1) | O(1) for ≤64 constants | one bitwise instruction |
| `IdentityHashMap.get` | O(1) | O(run length) | linear probing |
| `IdentityHashMap.remove` | O(run length) | O(run length) | back-shift can relocate several entries |
| `CopyOnWriteArrayList.get` | O(1) | O(1) | volatile read |
| `CopyOnWriteArrayList.add` | **O(n)** | O(n) | full array copy, exactly `len + 1` |
| `CopyOnWriteArraySet.contains` | O(n) | O(n) | it is a list underneath |
| `ConcurrentHashMap.get/put` | O(1) | O(log n) per `TreeBin` with `Comparable` keys, else O(n) | same bin structure as `HashMap` |
| `ConcurrentHashMap.size()` | O(cells) | O(cells) | an unlocked sum, so an estimate |
| `ConcurrentLinkedQueue.size()` | **O(n)** | O(n) | walks the list; `isEmpty()` is O(1) |
| `ConcurrentSkipListMap.get/put` | O(log n) expected | O(n) pathological | probabilistic levels |
| `list.removeAll(c)` | O(n × cost of `c.contains`) | O(n·m) with a `List` argument | wrap the argument in a `HashSet` |
| `Collections.binarySearch` | O(log n) | O(n) on a non-`RandomAccess` list below the threshold | indexed access on a chain |
| Object sort | O(n log n) | O(n log n) | TimSort; **O(n)** best case on a sorted run |
| Primitive sort | O(n log n) | O(n log n) with the heapsort fallback | dual-pivot quicksort |

Two framing sentences worth having ready: **`containsValue` is O(n) on every `Map`, without
exception**, and **the only O(1)-worst-case map lookup in `java.util` is `EnumMap`'s**.

## §5.3.4 The which-one drill

One word each. If your answer needs a clause, you have not finished the drill.

| Scenario | Answer |
|---|---|
| A list you will index into and append to | `ArrayList` |
| A queue between a producer and a consumer, same thread pool, needs backpressure | `ArrayBlockingQueue` |
| A stack | `ArrayDeque` |
| A set of strings, order irrelevant | `HashSet` |
| A set you will print to a user in insertion order | `LinkedHashSet` |
| A set of enum constants | `EnumSet` |
| "All events between 09:00 and 10:00" | `TreeMap` |
| "The last price at or before this timestamp" | `TreeMap`, via `floorEntry` |
| A bounded cache with a size limit and no dependencies | `LinkedHashMap` in access order |
| A bounded cache with a TTL, in production | Caffeine |
| A map shared by 16 threads, mostly reads | `ConcurrentHashMap` |
| A sorted map shared by threads | `ConcurrentSkipListMap` |
| A listener registry iterated on every event | `CopyOnWriteArrayList` |
| A set of small non-negative integers, dense domain | `BitSet` |
| Metadata that must vanish when its subject does | `WeakHashMap` |
| A visited-set during object-graph traversal | `IdentityHashMap` |
| Top 100 of a billion streamed numbers | a size-100 min-heap |
| A fixed-size buffer that overwrites its oldest entry | a hand-rolled ring buffer |
| A constant returned from a public API | `List.of` |
| A snapshot of internal state returned from a getter | `List.copyOf` |
| A `Map<K, List<V>>` you keep having to clean up | Guava `Multimap` |
| A million `int` keys mapped to `int` values | a primitive map — fastutil or Eclipse Collections |

## §5.3.5 The mechanism drill

One sentence each, out loud. These are the ten sentences that decide whether an interviewer thinks
you have read the source.

| Mechanism | The one sentence |
|---|---|
| `spread` | Xor the hash with its own top 16 bits, so that the high entropy survives a mask that keeps only the low `log₂ n` bits. |
| the lo/hi split | Doubling adds exactly one bit to the mask, so each entry either stays at `j` or moves to `j + oldCap`, decided by `(hash & oldCap) == 0` — one bit test, no rehashing. |
| `treeify` | Rewrite the bin's `Node`s as `TreeNode`s keeping the `next` chain alive, then build a red-black tree over them — so the bin is simultaneously a tree and a list, which is what makes `untreeify` cheap. |
| `siftUp` | Carry a hole up toward the root, shifting each larger parent down, and write the element once at the end: `log₂ n` comparisons, `d + 1` writes, no swaps. |
| `rotateLeft` | Promote a node's right child in its place, re-parent the child's old left subtree as the node's new right subtree, and fix the three reciprocal parent pointers — the in-order sequence is unchanged. |
| `modCount` | A plain `int` bumped by every structural change; an iterator snapshots it at construction and re-checks it at the top of `next()`, which is why mutation through the iterator is safe and mutation through the collection is not. |
| `ForwardingNode` | A node with `hash == MOVED` left in a migrated `ConcurrentHashMap` bin, holding `nextTable`, so a reader follows it into the new table and a writer calls `helpTransfer` and joins the resize. |
| `SALT32L` | A 32-bit value derived from `System.nanoTime()` at `ImmutableCollections` class-init, used **only** by `SetN`/`MapN` iterators to choose a start slot and direction — so iteration order varies per JVM run while lookup stays deterministic. |
| `afterNodeAccess` | `LinkedHashMap`'s relink hook: six pointer writes moving the accessed node to the tail plus `++modCount`, which is why a `get` on an access-order map is a structural write. |
| `expungeStaleEntries` | Poll the `ReferenceQueue` of a `WeakHashMap` and unlink each entry whose key the GC has cleared, using the entry's cached `hash` because the key is already gone — and it runs inside ordinary reads, which is why `size()` can shrink on its own. |

Five more worth adding once the first ten are automatic:

| Mechanism | The one sentence |
|---|---|
| `heapify` | Run `siftDown` backwards from `(n >>> 1) - 1`, which is O(n) because `Σ h/2^h = 2` — most nodes are near the bottom and barely move. |
| `buildFromSorted` | Build a balanced red-black tree from sorted input by recursive midpoint selection, colouring one computed level red — O(n), zero comparisons, zero rotations. |
| `probe` | Linear-probe the immutable open-addressed table from `floorMod(hash, len)`, returning `i` on a hit and `-(i + 1)` on a miss, so one call answers both "is it there" and "where would it go". |
| `closeDeletion` | After removing an `IdentityHashMap` entry, walk forward and back-shift any entry whose home slot lies on the circular path to the hole, because a tombstone would break the stop-at-first-null invariant. |
| `transfer` | Threads CAS-claim strides of at least 16 bins downward from `transferIndex`, migrate each with the same lo/hi rule as `HashMap`, and leave a `ForwardingNode` behind — so the resize is cooperative rather than stop-the-world. |

## Pitfalls

### Drilling the numbers without the reasons

**Wrong**

> "16, 0.75, 8, 6, 64, 10, 1.5, 11, 17."

Nine numbers in four seconds, and the first follow-up ends it. Worse, an unreasoned list is
brittle: under pressure people swap 8 and 6, or attach 64 to the wrong constant.

**Right**

> "Default capacity 16, because a power of two makes the index a mask. Load factor 0.75, from the
> Poisson table at λ = 0.5. Treeify at 8, untreeify at 6 — the gap is hysteresis. Min-treeify
> capacity 64, four times the treeify threshold, because below that resizing is the cheaper fix."

**Why people do it:** the numbers drill *looks* like rote memorisation, and it is the one drill where
that reading is most tempting. The reason column exists because the reason is what an interviewer
actually asks for, and because a number with a reason attached is much harder to forget.

### Answering the which-one drill with a paragraph

**Wrong**

> "For a stack, well, it depends — `Stack` is synchronized which might matter, and `LinkedList`
> implements `Deque` so that works too, and `ArrayDeque` is generally recommended but…"

**Right**

> "`ArrayDeque`." *(then stop; if they want the reason, they will ask, and it is one sentence: no
> per-element node, and its iteration order matches pop order)*

**Why people do it:** hedging feels safer than committing. It is not — a confident one-word answer
followed by a crisp reason on request reads as experience, while a paragraph of caveats reads as
someone who has not decided. Save the caveats for when the scenario is genuinely ambiguous, and then
say *which* fact would change your answer.

## Cheat sheet

| Drill | The five things you must not miss |
|---|---|
| Numbers | 16 / 0.75 / 8 / 6 / 64 / `1 << 30`; `ArrayList` 10 then 1.5×; `ArrayDeque` **17**; `PriorityQueue` and `Hashtable` **11**; `Integer.MAX_VALUE - 8` |
| Bytes | header 12, array header 16, ref 4, round to 8 ⇒ `Node` 32, `Entry` 40, `TreeNode` 56, `Integer` 16 |
| Null policy | one null key on the three hash maps; banned on `TreeMap` under natural ordering, `Hashtable`, `ConcurrentHashMap`, `ArrayDeque`, `PriorityQueue`, the `of` family |
| Iterators | fail-fast unsynchronized, snapshot copy-on-write, weakly consistent concurrent — and the wrappers' iterators are **not** synchronized |
| Ordering | `Set.of`/`Map.of` are randomised **per JVM run**; `HashMap` is unspecified but deterministic; only `LinkedHash*` and `Tree*` are guaranteed |
| Mutability | `Arrays.asList` writes through; `unmodifiable*` is a live view; `EnumSet.of` is rung 0 |
| Cost | `containsValue` O(n) on every map; `EnumMap` is the only O(1)-worst-case lookup; `CopyOnWriteArrayList.add` O(n); `ConcurrentLinkedQueue.size()` O(n) |
| Cost, construction | `new TreeMap<>(sortedMap)` and `new PriorityQueue<>(collection)` are **O(n)**; the `put`/`addAll` equivalents are O(n log n) |
| Which-one | `ArrayList`, `ArrayDeque`, `HashMap`, `HashSet` are the four defaults; everything else needs a stated reason |
| Mechanism | spread, lo/hi split, treeify, siftUp, rotateLeft, `modCount`, `ForwardingNode`, `SALT32L`, `afterNodeAccess`, `expungeStaleEntries` |

## Self-test

**Q1.** Recite the six `HashMap` constants with a reason each, in under thirty seconds.

<details><summary>Answer</summary>

`DEFAULT_INITIAL_CAPACITY = 1 << 4 = 16` — a power of two, so the bin index is `hash & (n − 1)` and a
resize is one bit test per entry. `DEFAULT_LOAD_FACTOR = 0.75f` — the Poisson table at λ = 0.5 makes
an eight-node bin a 6-in-100-million event while the table array is only about 20% of the footprint.
`TREEIFY_THRESHOLD = 8` — past that point a long bin is evidence of bad hashes rather than bad luck.
`UNTREEIFY_THRESHOLD = 6` — a hysteresis gap of 2, which must exceed the maximum size change per
operation of 1; and it is read only inside `TreeNode.split`. `MIN_TREEIFY_CAPACITY = 64` — four times
the treeify threshold, because in a small table a long bin more likely means the table is too small.
`MAXIMUM_CAPACITY = 1 << 30` — the largest power of two that is a positive `int`.

</details>

**Q2.** Which three constants do people most often attach to the wrong class, and what are the right
answers?

<details><summary>Answer</summary>

**11** belongs to `PriorityQueue` (`DEFAULT_INITIAL_CAPACITY`) *and* to `Hashtable` (initial
capacity), and to neither `ArrayList` nor `HashMap`. **16** is `HashMap`'s default capacity and also
Java 7's `ConcurrentHashMap` segment count and `MIN_TRANSFER_STRIDE` — but **not** `ArrayDeque`'s
capacity, which is 17 since JDK 12. And **10** is `ArrayList`'s `DEFAULT_CAPACITY`, applied on the
first `add`, and also `Map.of`'s maximum pair count — while `Map.of` taking 20 *arguments* is the
number people quote instead.

</details>

**Q3.** Name every `java.util` collection whose *construction* from an existing collection is
asymptotically cheaper than inserting the elements one at a time.

<details><summary>Answer</summary>

Three. `new PriorityQueue<>(collection)` reaches `heapify`, which is O(n) via `Σ h/2^h = 2`, where an
`offer` loop or `addAll` is O(n log n). `new TreeMap<>(sortedMap)` — and `new TreeSet<>(sortedSet)` —
reaches `buildFromSorted`, which is O(n) with zero comparisons and zero rotations, where n `put`
calls are O(n log n); the fast path requires the source to be a `SortedMap`/`SortedSet` with a
compatible comparator and the target to be empty. And `EnumSet.copyOf(nonEmptyEnumSet)` is an O(1)
`clone` of a bitmask, where `EnumSet.copyOf(plainCollection)` is O(n) and throws
`IllegalArgumentException` on an empty argument. `new HashMap<>(map)` is *not* in this list — it
pre-sizes and then re-`put`s every entry.

</details>

**Q4.** Give the one-sentence mechanism for `ForwardingNode` and for `SALT32L`.

<details><summary>Answer</summary>

`ForwardingNode`: a node with `hash == MOVED == -1` left behind in a migrated `ConcurrentHashMap`
bin, holding a reference to `nextTable`, so a reader that lands on it follows into the new table via
its own `find`, while a writer that lands on it calls `helpTransfer`, registers in `sizeCtl` and runs
a `transfer` pass itself before retrying.

`SALT32L`: a 32-bit value derived from `System.nanoTime()` when `ImmutableCollections` initialises,
consumed **only** by the `SetN` and `MapN` iterators — which use a multiply-shift to pick a starting
slot, with `REVERSE` from its low bit choosing the direction. Placement and `probe` are unsalted, so
`contains` is fully deterministic while iteration order changes on every JVM start, deliberately, to
break code that depends on it.

</details>

**Q5.** Which-one drill, fast: sorted-and-concurrent; dense small-int set; visited-set in a graph
walk; bounded producer-consumer queue; constant returned from a public API.

<details><summary>Answer</summary>

`ConcurrentSkipListMap` (the only concurrent sorted option in `java.util`); `BitSet`;
`IdentityHashMap` — or `Collections.newSetFromMap(new IdentityHashMap<>())` for the set form;
`ArrayBlockingQueue` (bounded at construction, unlike `LinkedBlockingQueue`, whose default is
`Integer.MAX_VALUE`); `List.of`. Five answers, five words each at most — and if the interviewer wants
the reason, each is one sentence.

</details>

---

**Leaves covered:** 5.3.1, 5.3.2, 5.3.3, 5.3.4, 5.3.5 (5 leaves)
**Leaves deferred:** none
**Diagrams included:** none
**Target version:** Java 21 LTS
**Lines:** 406
