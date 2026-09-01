# 02 Java Collections — The trap index and the version-stale claims table (§5.2)

**Target version: Java 21 LTS.** | [Index](00-index.md)
Previous: [92d-interview-internals-d-atomic-concept-checklist.md](92d-interview-internals-d-atomic-concept-checklist.md) · Next: [93b-drills.md](93b-drills.md)

This is the highest-value-per-minute page in the set, and it is the one to read first on the night
before an interview. Every row is a claim that a competent engineer believes and that is wrong —
either wrong outright, or wrong for Java 21 and right for Java 7.

Nothing here was derived by reasoning about what *ought* to be true. Every row was verified against
JDK 21 source or by compiling and running a program, in the course of writing the other 145 files in
this set, and the "proved in" column names the file that carries the mechanism and the transcript.
Where a claim is a *version* trap rather than a plain error it is in §5.2.2 rather than §5.2.1, with
the release that changed it.

The drills that use this material — numbers, matrices, cost, which-one, mechanism — are in
[93b](93b-drills.md); the code-reading drills and the spaced-repetition schedule are in
[93c](93c-code-reading-and-schedule.md).

## §5.2.1 The trap index

Four tables, grouped by where the mistake happens. Read the middle column first: the symptom is
what you will actually see in production, and it is what makes the trap memorable.

### Hashing, keys and equality

| The wrong belief | What actually happens | The fix | Proved in |
|---|---|---|---|
| "Treeification bounds hash-collision attacks at O(n log n)" | Only if the keys are **`Comparable`**. `TreeNode.find` searches *both* subtrees when `tieBreakOrder` gave it no real ordering. At 20,000 identical-hash keys: chain 312 ms, treeified `Comparable` 2.06 ms, treeified non-`Comparable` **529 ms — worse than no tree** | Implement `Comparable` on the key, or fix the `hashCode`. `String` is `Comparable`, so the CVE-2011-4858 surface really is covered; a custom key type gets nothing | [hash-map/04c](hash-map/04c-internals-d3-collision-dos.md), [hash-map/10b](hash-map/10b-build-my-hash-map-g-diff-and-collision-dos.md) |
| "A bin becomes a tree at 8 nodes" | At **nine**. `binCount` counts `next` hops from an already-rejected head — the source comment is `// -1 for 1st` — and the test runs after the new node is linked | Say "the ninth node", and add the second precondition below | [hash-map/02b](hash-map/02b-internals-b2-bincount-and-treeifybin.md) |
| "Nine colliding keys always give you a tree" | Not if `tab.length < MIN_TREEIFY_CAPACITY = 64`. `treeifyBin` calls `resize()` and treeifies **nothing**. With default sizing the first `TreeNode` appears at the **11th** insert; pre-sized to 64 slots, at the 9th | Pre-size, or state both preconditions | [92c puzzle 4](92c-interview-internals-c-puzzles-and-checklist.md) |
| "A tree bin reverts to a list once it drops below 6" | `UNTREEIFY_THRESHOLD` is read **only inside `TreeNode.split`**, during a resize (`:2325`, `:2334`). The removal path's guard at `:2207` is **structural** — it tests whether the root is missing a child or grandchild. A measured 13-node bin stayed a tree down to 4 nodes and flipped at 3 | Quote the structural guard, and note the flip point is removal-order dependent | [hash-map/03c](hash-map/03c-internals-c3-tree-split.md), [hash-map/04b](hash-map/04b-internals-d2-poisson-and-hysteresis.md) |
| "`new HashMap<>(1000)` holds 1000 entries" | It asks for a 1024-slot table and resizes when size passes 768. Measured: `new HashMap<>(100)` resizes on insert **#97** | `HashMap.newHashMap(n)` (Java 19+), else `new HashMap<>((int)(n / 0.75f) + 1)` | [hash-map/05](hash-map/05-internals-e-sizing-and-iteration.md), [91c puzzle 1](91c-interview-intermediate-c-puzzles.md) |
| "`(int)(n / 0.75f) + 1` is always the right pre-size" | At `n = 3 × 2^k` the `+ 1` tips over a power-of-two boundary. Measured at n = 6144: the folk formula gives a **16,384**-slot table where `newHashMap` gives 8,192 | Use `newHashMap`, which uses `Math.ceil` in `double` | [91c puzzle 1](91c-interview-intermediate-c-puzzles.md) |
| "Removing entries frees the map's memory" | The table is never shrunk, by `remove` or by `clear()`. A drained 10M-entry map still owns a `1 << 24` array; measured, a 200,000-entry map keeps 524,288 slots after `clear()` | Replace the map object: `map = HashMap.newHashMap(expected)` | [hash-map/05a](hash-map/05a-internals-e1-removal-and-iteration-order.md), [92c puzzle 3](92c-interview-internals-c-puzzles-and-checklist.md) |
| "Iterating a nearly-empty map is fast" | Iteration is **O(capacity + size)**. Measured: 3 entries in a 2²¹-slot table took 1,178,557 ns per walk against 64 ns in a fresh 16-slot map | Same fix — rebuild the map, or use `LinkedHashMap`, whose iteration is O(size) | [hash-map/05b](hash-map/05b-internals-e2-views-hooks-and-hashtable.md) |
| "Iteration within a bin is insertion order" | True for a linked bin, **false once it treeifies**: `moveRootToFront` splices the current red-black root to the head of the chain, and a rebalance changes which node that is | Say "table order, then chain order — and a treeified bin is headed by the tree root" | [hash-map/05a1](hash-map/05a1-internals-e1b-iteration-order.md) |
| "A mutated key just becomes unfindable" | It becomes unfindable *and* stays alive: measured, `get` → `null`, `containsKey` → `false`, `remove` → `null`, while `size()` is 1 and iteration still yields the value. Nothing can ever remove it | Immutable keys, or remove-mutate-reinsert | [92c puzzle 3](92c-interview-internals-c-puzzles-and-checklist.md), [contracts/02](contracts/02-equals-hashcode-contract.md) |
| "`Hashtable` uses prime capacities for better distribution" | Growth is `(oldCapacity << 1) + 1`, which produces **odd** numbers. Only **6 of the first 15** capacities are prime — 11, 23, 47, 191, 383 and **6,143, the last one**. 12287 = 11 × 1117 | The intent is real, the implementation stops working after the first few growths; `HashMap` chose masking plus a spread instead | [hash-map/05c](hash-map/05c-internals-e4-hashtable-and-prime-modulus.md) |
| "`equals` and `hashCode` decide `TreeMap` membership" | `compare(k1, k2) == 0` decides it, always. `equals` is never consulted for ordering, lookup or duplicate detection — so `containsKey` and `Map.equals` can disagree | Keep the comparator consistent with `equals`, or know which question you are asking | [tree-map/03](tree-map/03-internals-b1-key-identity-and-nulls.md) |
| "`putIfAbsent` will not overwrite anything" | It overwrites a stored **`null`**: the guard is `if (!onlyIfAbsent \|\| oldValue == null)`. "Absent" means no *value*, not no *key* | Do not store `null` values in a map you query with `putIfAbsent` or `getOrDefault` | [utilities/04](utilities/04-map-default-methods.md), [91c puzzle 5](91c-interview-intermediate-c-puzzles.md) |
| "`EnumMap`'s entry iterator reuses one `Entry` object" | It allocates a **fresh** `Entry(index++)` per `next()`, in JDK 8 through 25 alike. What is true is that the entry holds only an `int index` and reads `vals[index]` live — and `new ArrayList<>(entrySet())` gives `SimpleEntry` **snapshots**, which is why the wrong model survives experiment | State both halves: fresh allocation, live reads | [specialised-maps/02](specialised-maps/02-internals-enum-map-set.md) |
| "`RegularEnumSet.complement()` is `~elements & mask`" | There is **no `mask` field**. The mask is recomputed inline as `-1L >>> -universe.length`, relying on a `long` shift using only the low 6 bits of the distance | Quote the negative shift distance — it is the interesting part | [specialised-maps/02b](specialised-maps/02b-internals-enum-set.md) |
| "`IdentityHashMap`'s constructor takes a capacity" | It takes an `expectedMaxSize`. `new IdentityHashMap<>(100)` allocates a **512-slot** table, and a default map resizes on the **22nd** put | Do not hard-code the relationship; the javadoc declines to specify it | [specialised-maps/04a](specialised-maps/04a-internals-identity-sizing-and-uses.md) |
| "`WeakHashMap` is a cache" | It has no size bound, no TTL, and no policy — entry lifetime is key *reachability*, on the collector's schedule. And a value that references its own key makes the entry **immortal** | Caffeine. If you must, wrap values in a `WeakReference` to break the back-reference | [specialised-maps/03b](specialised-maps/03b-weak-hash-map.md) |
| "`WeakHashMap.size()` is a pure read" | It expunges cleared entries as a side effect, so it can return a smaller number than the call before it, with no modification in between | Never treat `size()`/`isEmpty()`/`get` on a `WeakHashMap` as stable | [specialised-maps/04b](specialised-maps/04b-internals-weak-hash-map.md) |

### Ordering, iteration and comparison

| The wrong belief | What actually happens | The fix | Proved in |
|---|---|---|---|
| "Fail-fast iteration reliably detects concurrent modification" | It is best-effort. Removing the **second-to-last** element through the list ends the loop one element early with **no exception**: `hasNext()` is `cursor != size`, and the decremented `size` meets the incremented `cursor` exactly. Measured: `visited=[a, b, c]` of four | Always mutate through the iterator, or use `removeIf` | [iteration/02](iteration/02-fail-fast-fail-safe.md), [90c puzzle 3](90c-interview-basics-c-puzzles.md) |
| "A `ConcurrentModificationException` means nothing happened" | The mutation already happened; CME is a *report*, not a rollback. Measured: the list is `[a, c, d]` after the throw, and a recursive `computeIfAbsent` on a `HashMap` leaves `{y=added from inside}` with the outer key never inserted | Do not catch-and-continue; fix the mutation | [90c puzzle 3](90c-interview-basics-c-puzzles.md), [91c puzzle 5](91c-interview-intermediate-c-puzzles.md) |
| "A `get` is always a read" | On an **access-order** `LinkedHashMap` it performs six pointer writes and `++modCount`. Two concurrent `get` calls are two writers, and a `get` inside iteration over the same map throws CME | Insertion order, a real mutex, or Caffeine. A `ReadWriteLock` does **not** work — readers need the write lock | [linked-hash-map/01b1](linked-hash-map/01b1-internals-b2-access-order-is-a-write.md) |
| "Only `get` counts as an access" | `afterNodeAccess` has **eight** call sites in JDK 21, so `putIfAbsent` and `computeIfAbsent` **on an already-present key also relink**. Measured: `computeIfAbsent("a")` on a present key gives `[b, c, a]` while `containsKey("b")` changes nothing | Enumerate the write-ish reads before relying on recency | [linked-hash-map/01a](linked-hash-map/01a-internals-a2-hooks-and-access-order.md) |
| "An over-bound `LinkedHashMap` LRU drains back to its limit" | Each `put` adds one and evicts at most one, so the net change is **zero**: a map filled to 10 with a bound of 3 stays at 10 across further puts | Do not exceed the bound — and note the copy constructor does, because `putMapEntries` passes `evict = false` | [linked-hash-map/01b](linked-hash-map/01b-internals-b-lru-and-sequenced.md) |
| "`putFirst` prioritises a key" | On an access-order map it moves the key to the **head**, which is the *eviction* end. Measured: `[b, c, a]` becomes `[a, b, c]` with `a` now least-recently-used. An absent key inserted by `putFirst` into a full LRU self-evicts immediately | Use it only on insertion-order maps | [linked-hash-map/01c](linked-hash-map/01c-internals-c-sequenced-and-caching.md), [92c puzzle 2](92c-interview-internals-c-puzzles-and-checklist.md) |
| "`PriorityQueue` iteration is sorted" | Iteration, `toString`, `forEach`, `stream()` and `toArray()` are all **heap order**. Only index 0 is guaranteed to be the minimum | Drain with repeated `poll` if you need order; never assert on `toString` | [priority-queue/01b](priority-queue/01b-internals-removeat-and-iteration.md) |
| "`PriorityQueue` is stable for equal priorities" | `siftUp` breaks on `>= 0` and `siftDown` on `<= 0`, so equal elements do not move. Measured: seven equal items inserted `a`…`g` drain as `agfedcb` | Add a `long` sequence number and `thenComparingLong` | [priority-queue/02](priority-queue/02-internals-b-traps.md) |
| "Changing an element's priority reorders the heap" | Nothing re-sifts. Measured: `{1, 5, 9}` with the 1 mutated to 99 drains as `99 5 9`, so `peek()` returned a non-minimum | Remove, mutate, reinsert; or tombstones and lazy deletion; or an indexed heap | [priority-queue/02](priority-queue/02-internals-b-traps.md) |
| "`HashMap` iteration order is stable enough to assert on" | Deterministic per JDK build and key set, unspecified by contract, and **rearranged by every resize**. `Set.of`/`Map.of` are worse: salted per JVM start from `System.nanoTime()`. Measured across three runs of one program: `[f,e,d,c,b,a]`, `[a,b,c,d,e,f]`, `[b,c,d,e,f,a]` | Assert on contents, or on `stream().sorted().toList()`, or hold a `LinkedHashSet`/`TreeSet` | [92c puzzle 5](92c-interview-internals-c-puzzles-and-checklist.md), [immutable-collections/04b2](immutable-collections/04b2-internals-salt-cds-and-null-hostility.md) |
| "Small `Integer` keys iterate in sorted order" | Only while every key is below the capacity: `hashCode` is the value, the spread is the identity below 65,536, and `v & (n−1) == v`. Measured: adding 100 puts it in **slot 4** and adding −1 puts it in **slot 0** | Never depend on it | [92c puzzle 5](92c-interview-internals-c-puzzles-and-checklist.md) |
| "`list.remove(x)` removes the value `x`" | On a `List<Integer>` a literal `int` selects `remove(int index)`. Measured: `remove(1)` on `[10,20,30,40]` gives `[10,30,40]` — **and the same source line removes the value 1** when the variable is declared `Collection<Integer>` | `remove(Integer.valueOf(x))` | [90c puzzle 5](90c-interview-basics-c-puzzles.md) |
| "`a.getX() - b.getX()` is a fine comparator" | `int` subtraction overflows and the sign inverts, breaking transitivity. TimSort detects it later and elsewhere with `IllegalArgumentException: Comparison method violates its general contract!` | `Integer.compare`, or `Comparator.comparingInt` | [contracts/01](contracts/01-ordering.md), [utilities/02](utilities/02-sorting-a-timsort.md) |
| "`comparing(A).thenComparing(B).reversed()` is A ascending, B descending" | `reversed()` flips the sign of the **entire chain** built so far | Reverse the individual key comparator instead | [contracts/01](contracts/01-ordering.md) |
| "`binarySearch` on an unsorted list throws or returns −1" | It returns a **wrong answer**, silently. The miss encoding is `-(insertionPoint) - 1` | Sort first, with the *same* comparator you search with | [utilities/01](utilities/01-collections-and-arrays.md) |
| "`Stack` iterates in pop order" | `Stack extends Vector`, so it iterates **bottom-to-top** — the reverse of pop order. Measured: `Stack` for-each gives `a b c` where `ArrayDeque`-as-stack gives `c b a`. And `Stack.search` is 1-based from the top | Use `ArrayDeque` for a stack | [90c puzzle 2](90c-interview-basics-c-puzzles.md), [framework/07-legacy-a](framework/07-legacy-a-vector-stack-hashtable.md) |
| "`LinkedList.get(n/2)` is `n/2` hops" | `node(int)` walks from the nearer end, so the worst case is **`⌊(n−1)/2⌋`** — 4 hops on a 10-element list, and `get(8)` is **1 hop** | Quote the loop bound, not the asymptotic | [linked-list/01](linked-list/01-internals.md) |
| "`linkedList.parallelStream()` parallelises" | `trySplit` cannot index; it copies a prefix with `BATCH_UNIT = 1024` growing per call. Measured on 1,000 elements: `left=1000, right=0` — one chunk, no parallelism | Copy to an `ArrayList` first | [91c puzzle 4](91c-interview-intermediate-c-puzzles.md) |
| "`List.of(...)` advertises `IMMUTABLE` to the stream framework" | `List.of(1,2,3).spliterator()` reports **`IMMUTABLE=false`** — `AbstractImmutableList` never overrides `spliterator()`, so the default supplies `ORDERED` only | Do not infer characteristics from the class's guarantees | [91c puzzle 4](91c-interview-intermediate-c-puzzles.md) |

### Views, copies and immutability

| The wrong belief | What actually happens | The fix | Proved in |
|---|---|---|---|
| "`Collections.unmodifiableList(x)` makes the list immutable" | It is a live **view**. Measured: the wrapper grew from 2 elements to 3 when the backing list was appended to, without anyone touching the wrapper | `List.copyOf(x)` for a snapshot | [90c puzzle 4](90c-interview-basics-c-puzzles.md), [immutable-collections/01](immutable-collections/01-views-copies-snapshots.md) |
| "An immutable collection is immutable all the way down" | Every JDK factory is **shallow**. Measured: both `unmodifiableList` and `List.copyOf` printed `one!` after the element's `StringBuilder` was mutated | An immutable element type is the only route to depth; there is no deep-copy factory in `java.util` | [90c puzzle 4](90c-interview-basics-c-puzzles.md), [immutable-collections/02a](immutable-collections/02a-shallow-immutability-and-boundaries.md) |
| "`Arrays.asList(...)` is read-only" | Fixed-**size** only. `set`, `sort` and `replaceAll` all write **through to the caller's array**; only the size-changing methods throw, and they throw because they are not overridden | `List.of(...)`, or `new ArrayList<>(Arrays.asList(...))` for a mutable copy | [immutable-collections/01d](immutable-collections/01d-arrays-aslist.md) |
| "`Arrays.asList(intArray)` gives a `List<Integer>`" | It gives a `List<int[]>` of size 1, with no warning even under `-Xlint:all`, because a type variable cannot bind to `int` | `Arrays.stream(arr).boxed().toList()` | [immutable-collections/01d](immutable-collections/01d-arrays-aslist.md) |
| "`Collections.emptyList()` and `List.of()` are interchangeable" | Different objects (`==` is `false`) with **opposite mutator contracts**: measured, `emptyList().clear()` succeeds silently while `List.of().clear()` throws | Choose on semantics — fail-loud versus null-tolerant | [90c puzzle 4](90c-interview-basics-c-puzzles.md), [immutable-collections/04e](immutable-collections/04e-internals-layout-and-legacy-factories.md) |
| "`Map.of(k1,v1,k2,v2)` builds a `Map2`" | There is **no `Map2`**. `Map1` covers exactly one pair; two pairs go straight to `MapN`. (`List12` really does cover one *and* two.) | — | [immutable-collections/04](immutable-collections/04-internals-immutable-collections.md) |
| "A `TreeMap` range view rejects out-of-range operations" | It fences **writes only**. Measured: `headMap(30).remove(99)` returns `null` and **leaves key 99 alive in the source**, `get(99)` returns `null`, and only `put(99, ...)` throws `IllegalArgumentException: key out of range` | Never trust a range view's `remove` to report failure | [immutable-collections/01c](immutable-collections/01c-treemap-range-and-reversed-views.md), [91c puzzle 3](91c-interview-intermediate-c-puzzles.md) |
| "`subList` is a cheap way to keep a window" | Its three fields pin the **whole parent array**. Measured: a 10-element window on a 500,000-element list keeps a 2 MB `Object[]` reachable; on a million-element list, 3.81 MiB | `List.copyOf(sub)` or `new ArrayList<>(sub)` | [immutable-collections/01](immutable-collections/01-views-copies-snapshots.md), [92c puzzle 3](92c-interview-internals-c-puzzles-and-checklist.md) |
| "`entrySet()` gives you copies of the entries" | On a `HashMap` it gives the map's own `Node` objects. `setValue` writes into the map, is not structural, and still works after the mapping is removed — writing into memory nothing can reach | `Map.entry(e.getKey(), e.getValue())` to keep a pair | [immutable-collections/01b](immutable-collections/01b-map-views-and-arrays-aslist.md) |
| "`values().remove(v)` removes every matching entry" | It removes exactly **one**: `Values` declares no `remove` override, and the inherited `AbstractCollection` scan returns on the first hit | `values().removeIf(...)` | [immutable-collections/01b](immutable-collections/01b-map-views-and-arrays-aslist.md) |
| "`reversed()` costs a copy" | It is a live O(1) view — and its orientation flips writes. Measured: `view.addFirst("X")` appended `X` to the **source's tail**, and `view.add("Y")` landed at the source's **front** | Know which end you mean; snapshot with `List.copyOf(view)` | [92c puzzle 2](92c-interview-internals-c-puzzles-and-checklist.md), [sequenced-collections/01](sequenced-collections/01-sequenced-collections.md) |
| "`reversed().reversed()` is a view of a view" | For `List` and `LinkedHashMap` it returns the **original object by identity** — `LinkedHashMap.java:1224` is literally `return base;`. Not so for `TreeMap.descendingMap()`, which builds a fresh `AscendingSubMap`: `equals` but not `==` | Three different identity answers on three classes; check the one you are using | [92c puzzle 2](92c-interview-internals-c-puzzles-and-checklist.md), [immutable-collections/04d](immutable-collections/04d-internals-sublist-and-reversed-view.md) |
| "`List.of(...).contains(null)` returns `false`" | It **throws `NullPointerException`**, at every arity including the empty list, and through `subList` and `reversed()` views. `Stream.toList()`'s `ListN` is the exception — it permits nulls | Use `Collections.unmodifiable*` if you need null-tolerant queries | [immutable-collections/03c](immutable-collections/03c-null-queries-and-guava.md) |
| "`collect(Collectors.toList())` returns an immutable list" | It returns a **mutable** list of unspecified type. `Stream.toList()` is the unmodifiable one, and it *permits* nulls; `toUnmodifiableList()` is unmodifiable and rejects them | Pick deliberately; `toCollection(ArrayList::new)` when you want mutability by contract | [immutable-collections/02b](immutable-collections/02b-entries-snapshots-and-stream-terminals.md) |
| "`EnumSet.of(...)` is immutable because it is a factory" | `EnumSet` is **mutable** — a `long` bitmask with `add` and `remove`. `final` protects only the reference | `Set.copyOf(EnumSet.of(...))`, which loses the bitmask | [immutable-collections/03](immutable-collections/03-immutability-tiers.md) |
| "`Map.entry(k, v)` is a drop-in `SimpleEntry`" | `KeyValueHolder` is **not `Serializable`**, and it rejects null keys and values at construction | `AbstractMap.SimpleImmutableEntry` if it must go on the wire | [immutable-collections/02b](immutable-collections/02b-entries-snapshots-and-stream-terminals.md) |
| "`Collections.nCopies(3, x)` makes three copies" | One object holding **one shared reference**, n times — O(1) memory. With a mutable element, "row 0" and "row 2" are the same object | Build the rows in a loop | [utilities/01](utilities/01-collections-and-arrays.md) |

### Concurrency, cost and capacity

| The wrong belief | What actually happens | The fix | Proved in |
|---|---|---|---|
| "`Collections.synchronizedMap` makes the map thread-safe" | Each *call* is atomic. Compound actions still race, and `iterator()`/`spliterator()`/`stream()` return the **raw** delegate with no synchronization at all | `ConcurrentHashMap`, or hold `synchronized (wrapper)` across the whole loop yourself | [concurrent-collections/01](concurrent-collections/01-thread-safety-and-wrappers.md) |
| "`synchronizedMap(...).keySet()` may use a different mutex" | The views are each constructed with the **identical outer `mutex` field**, in both JDK 8 and JDK 21 — `Collections.java:2912-2934` and `:2604-2623`. The warning is unfounded | Iterate views under `synchronized (wrapper)`; the mutex is not the problem | [concurrent-collections/01](concurrent-collections/01-thread-safety-and-wrappers.md) |
| "A recursive `computeIfAbsent` on `ConcurrentHashMap` deadlocks" | On one thread it **throws `IllegalStateException: Recursive update`** — `synchronized` is reentrant, so it cannot self-block. A key landing in a *different* bin **succeeds**, and is still a javadoc-contract violation. A genuine two-thread deadlock is constructible but not deterministically demonstrable | Do not mutate the map from inside the mapping function, on any `Map` implementation | [concurrent-collections/03](concurrent-collections/03-internals-chm-b.md), [91c puzzle 5](91c-interview-intermediate-c-puzzles.md) |
| "`ConcurrentHashMap.size()` is exact" | An unlocked sum of `baseCount` plus a lazily-allocated `CounterCell[]`, so an estimate — and it **clamps at `Integer.MAX_VALUE`** | `mappingCount()` for the `long`; exclusive access if you truly need exactness | [concurrent-collections/03](concurrent-collections/03-internals-chm-b.md) |
| "`ConcurrentHashMap` forbids null values" | The guard at `:1011` is `if (key == null \|\| value == null)` — it bans null **keys as well** | Say both | [concurrent-collections/03b](concurrent-collections/03b-internals-chm-c-bulk-nulls-and-segments.md) |
| "`CopyOnWriteArraySet` is a concurrent `HashSet`" | It wraps a `CopyOnWriteArrayList`, so `add` and `contains` are **O(n)** scans and every write copies the array | `ConcurrentHashMap.newKeySet()` | [sets/01b](sets/01b-set-over-map-siblings-and-exceptions.md) |
| "`ConcurrentLinkedQueue.size()` is O(1)" | It is **O(n)** and approximate — it walks the list; `isEmpty()` is the O(1) one | `isEmpty()`, or maintain your own counter | [concurrent-collections/05b](concurrent-collections/05b-lock-free-queues-and-choosing.md) |
| "`DelayQueue.size()` tells you how many items are ready" | It counts expired **and unexpired** elements; `poll()` returns `null` when the head is not yet due | Do not size-check a `DelayQueue` to decide whether to poll | [concurrent-collections/05](concurrent-collections/05-blocking-and-lock-free-queues.md) |
| "`new LinkedBlockingQueue<>()` is bounded" | Its default capacity is `Integer.MAX_VALUE` — effectively unbounded, so a fast producer makes the queue the leak | Pass a capacity, or use `ArrayBlockingQueue`, which cannot be unbounded | [concurrent-collections/05](concurrent-collections/05-blocking-and-lock-free-queues.md) |
| "`removeAll` is O(n)" | Its cost is receiver size × the **argument's** `contains`. With a `List` argument it is O(n·m) | `list.removeAll(new HashSet<>(other))`, unconditionally | [sets/02](sets/02-set-algebra.md) |
| "`retainAll` on a mismatched `EnumSet` is a no-op" | It **silently empties** the receiver. (`addAll` throws `ClassCastException`; `removeAll` returns `false`; `containsAll` reduces to `arg.isEmpty()`) | Check the element type | [specialised-maps/01](specialised-maps/01-enum-collections.md) |
| "Amortised O(1) means predictable latency" | One `add` in the sequence copies the whole array — 4 MB at a million elements. Amortised is a bound on the *sequence* | Pre-size, and know your tail latency is not your average | [array-list/04](array-list/04-amortised-analysis.md) |
| "`Collection.removeIf` is O(n) everywhere" | The **interface default** is an iterator loop, which is O(n²) on an `ArrayList`. `ArrayList` overrides it with a two-pass `long[]` bitset compaction | Use the concrete class's override; do not inherit the default in your own `List` | [array-list/02b](array-list/02b-internals-bulk-removal.md) |
| "An empty collection is free" | `ArrayList` ~24 B and `HashMap` ~48 B with nothing allocated — but a map of drained lists costs ~144 B per key against ~48 B for a flat map | Do not pre-create empties; remove the key when its collection empties | [cost-and-memory/03](cost-and-memory/03-internals-memory-collections.md), [92c puzzle 3](92c-interview-internals-c-puzzles-and-checklist.md) |
| "A `HashMap` table for n entries is `n / 0.75` slots" | It is the next **power of two** above that. Measured at n = 1,000,000: `2^21` = 2,097,152 slots — 2.1 slots per entry, 57% more array than the load factor implies, and ~72 B per entry rather than the idealised 69 | Size with `newHashMap`, and expect the array cost to jump at power-of-two boundaries | [92c puzzle 1](92c-interview-internals-c-puzzles-and-checklist.md) |

## §5.2.2 The version-stale claims table — D-152

**D-152** is a `table`-type manifest entry, so this Markdown table *is* the diagram; there is no SVG.
Columns are the manifest's: what old material says, what Java 21 does, which release changed it, and
the one-line answer that shows you know both.

**Departure from the manifest, recorded deliberately:** the manifest lists "`ArrayDeque`
power-of-two masking" as **one** row. It is **two** changes, nine releases apart, and the
16-versus-17 half is the better question — so it appears as two rows below. Three further rows were
added from findings made while writing this set, and are marked *added*.

| What old material says | What Java 21 does | Changed in | The answer that shows you know both |
|---|---|---|---|
| "`ArrayDeque` rounds capacity to a power of two and wraps with `& (length - 1)`" | No mask at all — `inc`/`dec`/`sub` helpers, one branch each, and capacity is not rounded | **JDK 9** | "The mask is JDK 8 only; JDK 9 rewrote the wraparound into `inc`/`dec`/`sub`." |
| "A default `ArrayDeque` holds 16 elements in a 16-slot array" | `new Object[16 + 1]` — 17 slots, 16 usable, because one slot must stay empty for `head == tail` to mean empty | **JDK 12** *(second half of the manifest's single row)* | "Capacity 17 since JDK 12; before that the no-arg deque allocated 16 slots and held only 15, despite the javadoc promising 16." |
| "`HashMap` rehashes with a four-shift, four-xor spread and a random seed" | One line: `(h = key.hashCode()) ^ (h >>> 16)`. The seeded `hashSeed` and `jdk.map.althashing.threshold` are gone | **Java 8** | "Java 8 replaced Java 7u6's seeded four-shift spread with a single xor-shift, because treeification now bounds the degenerate bin — the spread only has to make it rare, not prevent it." |
| "`HashMap` under concurrency spins forever in an infinite loop" | That specific cycle is gone: Java 8 tail-appends into fresh lo/hi lists instead of re-heading a live chain. The map is still unsafe — lost entries, resurrected entries, torn `size`, NPE from inside `HashMap` | **Java 8** | "Java 8 killed the *cycle*, not the corruption. The Java 7 loop came from head-insertion during `transfer`." |
| "`ConcurrentHashMap` uses 16 `Segment` locks" | Per-bin concurrency: `casTabAt` for an empty bin, `synchronized (f)` on the bin head. **But `static class Segment` still exists** at `:1380` as a serialization stub | **Java 8** | "Segment *locking* was abandoned in Java 8; the `Segment` class survives in JDK 21 for serialization compatibility, and a Java 8+ serialized map still writes segment-shaped data." |
| "`sizeCtl` is `-(1 + the number of active resizing threads)`" | The low 16 bits hold `2 + helpers`; the high 16 hold a resize **stamp** identifying the table size. For `n = 16` the first resizer writes **`-2145714174`**, not `-2` | **Java 8** *(added — and the JDK's own field comment at `:792-799` is the stale source)* | "`resizeStamp(16)` is `numberOfLeadingZeros(16) \| (1 << 15)` = 32795, and `32795 << 16` is `-2145714176`, so the first resizer CASes `-2145714174`. The field javadoc still says `-2`." |
| "`Collections.sort` copies the list into an array and sorts that" | `Collections.sort(list)` is `list.sort(null)`. The **default** `List.sort` does copy and write back, but `ArrayList` overrides it to sort `elementData` in place | **Java 8** | "Since Java 8 it delegates to `List.sort`, and `ArrayList`'s override sorts in place — it still bumps `modCount`, so a held iterator is poisoned either way." |
| "Hash-table capacity should be prime for good distribution" | `HashMap` uses a power of two so the index is a mask and a resize is one bit test per entry. `Hashtable`'s `2n + 1` produces odd numbers, only 6 of the first 15 prime | **Java 1.2** *(`HashMap`'s design)* | "Power of two, because `2n − 1` is `(n − 1)` plus one bit of value `n` — so a resize moves each entry to `j` or `j + oldCap` by one bit test. The price is masking away the high bits, which is why `hash()` folds them down." |
| "`Hashtable` and `HashMap` differ only in synchronization" | Also: capacity 11 vs 16, `2n + 1` vs doubling, modulo vs mask, no spread vs `h ^ (h >>> 16)`, null rejection vs one null key, no treeification vs treeify at 9, and `Enumeration`s that are not fail-fast | **Java 1.2** | "Six other differences, and the one that bites is that a degenerate `Hashtable` bin stays O(n) — there is no treeification." |
| "`LinkedHashMap` appends with `linkNodeLast`" | The method is **`linkNodeAtEnd`** (`:236`), with a `putMode == PUT_FIRST` branch added for `SequencedMap` | **Java 21** *(added)* | "Renamed in JDK 21 when `putFirst`/`putLast` arrived; JDK 8's `linkNodeLast` body is exactly the JDK 21 method's `else` arm." |
| "`CopyOnWriteArrayList` guards writes with a `ReentrantLock`" | `final transient Object lock = new Object()` (`:107`) and `synchronized (lock)` | **between JDK 8 and 11**, around 2018 | "A plain monitor since JDK 11 — the class needs no `Condition` or `tryLock`, and the JDK's own comment says so." |
| "`SynchronousQueue` is a `TransferStack` or a `TransferQueue`" | One `static final class Transferer<E> extends LinkedTransferQueue<E>` (`:152`); unfair mode is `xferLifo`, fair mode is inherited | **JDK 21** *(added)* | "Both classes are gone in JDK 21 — `SynchronousQueue` is now implemented in terms of `LinkedTransferQueue`. The behaviour is unchanged: zero capacity, direct handoff, `isEmpty()` always true." |
| "`ConcurrentSkipListMap` has a `HeadIndex` and `p = 0.25` per level" | No `HeadIndex` class exists; `head` is a plain `Index<K,V>`. The class comment states `k = 1, p = 0.5`, meaning about **one-quarter of nodes are indexed at all** and then **half** per additional level, up to 62 | **post-JDK-12 rewrite** | "0.25 is the fraction of nodes with any index — `doPut` gates on `(lr & 0x3) == 0` — and 0.5 is the per-level continuation probability. Two parameters, not one." |
| "A tree bin untreeifies at 6 on removal" | `UNTREEIFY_THRESHOLD` is read only in `TreeNode.split`. Removal untreeifies on **tree shape**, measured at 3 nodes for a 13-node bin | **never — the folklore was always wrong**, same structure in JDK 8 | "It is not a version change. The removal guard at `:2207` tests whether the root is missing a child or grandchild, and never reads the constant." |
| "`EnumMap`'s entry iterator reuses one `Entry`" | Fresh `new Entry(index++)` per `next()` in JDK 8, 17, 21 and 25 | **never — the folklore was always wrong** | "Identical in all four JDKs. `lastReturnedEntry` is `remove()` support, not an allocation optimisation." |
| "`collect(toList())` gives you an unmodifiable list" | Mutable, unspecified type. `Stream.toList()` (Java 16) is the unmodifiable one — and it permits nulls | **Java 16** *(when the confusion started)* | "Three different contracts: `collect(toList())` mutable, `Stream.toList()` unmodifiable but null-tolerant, `toUnmodifiableList()` unmodifiable and null-hostile." |
| "Nothing was added to the collections framework after Java 8's streams" | Java 9 immutable factories, Java 10 `copyOf`, Java 16 `Stream.toList()`, Java 19 the `newXxx` sized factories, Java 21 sequenced collections | **9, 10, 16, 19, 21** | "The last structural addition is JEP 431's sequenced tier in Java 21; the last quiet one is the Java 19 `newHashMap` family that finally lets you size a map by entry count." |
| "Virtual threads never pin the carrier" | On **JDK 21** a virtual thread blocking inside `synchronized` **does** pin its carrier; JEP 491 removed that | **JDK 24** | "Correct from JDK 24 onward. On 21, prefer a `ReentrantLock` over `synchronized` around anything that blocks." |

## §5.2.3 The five most expensive real-world mistakes

Ranked by what they actually cost when they happen, not by how often they appear in interviews.

### 1. An unbounded collection used as a cache

**The shape.** A `static final Map<K, V>` — or a `ConcurrentHashMap` field — that only ever gets
`put` into. Often introduced as "memoisation".

**The failure.** Heap exhaustion, and the process dies rather than degrades. The tell in a heap dump
is one `HashMap` at the top of the dominator tree with an enormous retained size, and a
`collection_fill_ratio` that looks perfectly healthy — because the map is not over-allocated, it is
just too big.

**Why the usual fixes do not work.** `WeakHashMap` is not a bound: it ties entry lifetime to key
*reachability*, so a cache whose keys are interned strings or small boxed integers never releases
anything, and a value that references its own key is immortal regardless.
`LinkedHashMap` with `removeEldestEntry` **is** a bound, and it is unsynchronized and
scan-vulnerable — one pass over a key space larger than the cache evicts the entire hot set
(measured in this set: 100% hit rate to 0%).

**The fix.** Caffeine, with an explicit `maximumSize` or `expireAfterWrite`. If a dependency is
impossible, an access-order `LinkedHashMap` behind a mutex, with the bound and the eviction reason
logged. And register the size as a metric either way, so the graph shows it before the heap does.

### 2. A mutable key

**The shape.** An entity with a generated `equals`/`hashCode` — often a JPA entity or a Lombok
`@EqualsAndHashCode` class — used as a `HashMap` key or a `HashSet` element, and then mutated.

**The failure.** The entry becomes **unreachable by key while remaining fully alive**. Measured:
`get` returns `null`, `containsKey` is `false`, `remove` returns `null`, and `size()` still counts it
and iteration still yields it. So the cleanup code that would have removed it cannot find it, and
the collection grows monotonically.

**Why it survives testing.** Holding the *same reference* still finds the entry, because the bin walk
tries `(k = e.key) == key` before `equals`. Unit tests hold the same object; production looks the key
up from a fresh parse or a new transaction.

**The fix.** Immutable keys — a `record` of the identifying fields, or the entity's ID rather than the
entity. If you must key on a mutable object, remove it before mutating and re-insert after. And
never let `hashCode` read a field that a setter can change.

### 3. `removeAll` with a `List` argument

**The shape.** `activeIds.removeAll(bannedIds)` where both are `List`s, or a `Set` receiver with a
`List` argument.

**The failure.** O(n·m). At 50,000 and 20,000 elements that is a billion `equals` calls, and the
request that triggers it simply stops responding. It reviews clean, because the line reads like a set
operation and the cost is entirely in the *argument's* `contains`.

**The fix, unconditional.** `receiver.removeAll(new HashSet<>(argument))`. Wrapping costs one O(m)
pass and turns the whole call into O(n + m); it is never worth reasoning about the sizes first. Note
that `AbstractSet.removeAll`'s smaller-side optimisation does **not** rescue you — it only helps when
the other side has O(1) `contains`.

### 4. `LinkedList` chosen "for performance"

**The shape.** `List<T> items = new LinkedList<>();` with a comment about insertions being O(1).

**The failure.** Slower and larger on essentially every workload. `get(i)` is a walk of up to
`⌊(n−1)/2⌋` hops, so a located mid-list insert measured 21–32× slower than the same insert on an
`ArrayList` at n ≥ 10,000; each node costs 24 bytes against a 4-byte array slot; iteration is a
pointer chase with no prefetching; and `parallelStream()` does not parallelise, because `trySplit`
copies a batch rather than indexing.

**The fix.** `ArrayList` for lists, `ArrayDeque` for queues and stacks. `LinkedList` earns its place
only when you need `null` elements at the ends or you are splicing through a held `ListIterator` —
and then the O(1) really is O(1), measured flat at ~7 ns per insert from 1,000 to 100,000 elements.

### 5. `Collections.synchronizedMap` believed to be enough

**The shape.** A shared map wrapped once at construction, and then used exactly as if it were
single-threaded.

**The failure.** Three distinct bugs, all invisible in review. **Compound actions race** —
`if (!m.containsKey(k)) m.put(k, v)` is two `synchronized` blocks with a window between them.
**Iteration is not covered at all** — `iterator()`, `spliterator()` and `stream()` return the raw
underlying objects with no synchronization, which the source comment says outright, so a for-each
over a shared wrapper throws `ConcurrentModificationException` or worse. And **it does not scale**:
one mutex means readers block readers.

**What is genuinely safe.** Each individual call, including the wrapper's own `merge` and
`computeIfAbsent`, which are single `synchronized` blocks. And the derived views *do* share the outer
mutex, in JDK 8 and 21 alike — the folklore warning about that is unfounded.

**The fix.** `ConcurrentHashMap`, and express the atomicity you need with `putIfAbsent`, `merge` or
`compute` rather than with a lock you hold across two calls. If the unit of atomicity spans two
collections, no wrapper and no concurrent collection can express it — that is the case where your own
lock is the right answer.

## Pitfalls

### Reciting a trap without its mechanism

**Wrong**

> "`HashMap` treeifies at 8 and untreeifies at 6."

Two constants and no understanding. The follow-up — "when is 6 actually tested?" — ends the topic,
because the answer is "only during a resize split", and a memorised pair cannot get there.

**Right**

> "It treeifies when a bin would hold nine nodes, in a table of at least 64 slots. The 6 is a
> hysteresis band so a bin hovering at the threshold does not thrash — and it is read **only** inside
> `TreeNode.split`. Plain removal untreeifies on tree *shape*, not on a count."

**Why people do it:** a trap list is a list, and lists invite memorisation. Every row in §5.2.1 has a
"proved in" column for exactly this reason: the row is the index, the file is the answer.

### Treating a version trap as a plain error

**Wrong**

> "That blog post is wrong: `ConcurrentHashMap` doesn't have segments."

**Right**

> "That's the Java 7 design, and it was accurate then — 16 `ReentrantLock` segments with a
> `concurrencyLevel` argument. Java 8 moved to per-bin CAS-and-monitor. And the `Segment` class is
> still in JDK 21 at `:1380` as a serialization stub, so 'removed' is not quite right either."

**Why it matters more than being right:** the interviewer may be the person who wrote that code, and
"the old design and why it changed" is a much stronger answer than "that's wrong". Every row in
§5.2.2 has a *which release* column so you can date the claim rather than dismiss it.

## Cheat sheet

| Trap, in four words | The correction |
|---|---|
| treeify bounds collisions | only for `Comparable` keys |
| treeifies at 8 | ninth node, and table ≥ 64 slots |
| untreeifies at 6 | only inside `split`; removal is structural |
| `new HashMap<>(n)` | holds `0.75n`; use `newHashMap(n)` |
| removal frees memory | table never shrinks, `clear()` included |
| bin order is insertion order | not once treeified — `moveRootToFront` |
| fail-fast is reliable | second-to-last element skips silently |
| CME means nothing happened | the mutation already landed |
| `get` is a read | not on an access-order `LinkedHashMap` |
| only `get` is an access | eight call sites, including `computeIfAbsent` |
| over-bound LRU drains | one in, one out — it stays over |
| `putFirst` prioritises | it moves the key to the eviction end |
| heap iteration is sorted | heap order; only index 0 is the minimum |
| heap is stable | `agfedcb`; add a `long` sequence number |
| `HashMap` order is stable | unspecified; `Set.of` is salted per JVM run |
| `list.remove(x)` removes x | `remove(int)` wins on a `List` |
| `a - b` comparator | overflows; `Integer.compare` |
| `binarySearch` unsorted | silently wrong, not an error |
| `Stack` iterates in pop order | bottom-to-top |
| `LinkedList.get` is n/2 hops | `⌊(n−1)/2⌋`, and `get(8)` of 10 is 1 hop |
| `unmodifiableList` is immutable | live view of a mutable list |
| immutable is deep | every JDK factory is shallow |
| `Arrays.asList` is read-only | fixed-size; `set`/`sort` write through |
| `emptyList()` == `List.of()` | different objects, opposite `clear()` contracts |
| range views reject everything | writes only; `remove` is a silent no-op |
| `subList` is cheap to keep | pins the whole parent array |
| `entrySet()` gives copies | the map's own nodes |
| `values().remove(v)` removes all | exactly one |
| `reversed()` copies | live view, and it flips which end you write |
| `List.of().contains(null)` | throws NPE |
| `collect(toList())` is immutable | mutable, unspecified type |
| `EnumSet.of` is immutable | mutable bitmask |
| `nCopies` copies | one shared reference n times |
| `synchronizedMap` is thread-safe | per call only; iteration is unsynchronized |
| recursive `computeIfAbsent` deadlocks | `IllegalStateException: Recursive update` |
| `chm.size()` is exact | estimate, and clamps at `Integer.MAX_VALUE` |
| CHM forbids null values | keys too, same guard |
| `CopyOnWriteArraySet` is a hash set | a list — O(n) `add` and `contains` |
| `ConcurrentLinkedQueue.size()` is O(1) | O(n); `isEmpty()` is the O(1) one |
| `new LinkedBlockingQueue<>()` is bounded | `Integer.MAX_VALUE` |
| `removeAll` is O(n) | receiver × argument's `contains` |
| mismatched `EnumSet.retainAll` | silently empties the receiver |
| amortised O(1) is predictable | one call copies the whole array |
| `Collection.removeIf` is O(n) | the default is O(n²) on `ArrayList` |
| empty collections are free | ~144 B/key for a map of drained lists |
| table is `n / 0.75` slots | next power of two — 2.1 slots/entry at n = 10⁶ |

## Self-test

**Q1.** Name the two preconditions for a `HashMap` bin to become a tree, and the number of nodes at
which it happens.

<details><summary>Answer</summary>

The bin must reach **nine** nodes — `binCount >= TREEIFY_THRESHOLD - 1`, where `binCount` counts
`next` hops from an already-rejected head, evaluated after the new node is linked — **and** the table
must already have at least `MIN_TREEIFY_CAPACITY = 64` slots. If it does not, `treeifyBin` calls
`resize()` and treeifies nothing, which is why a default-sized map with all-colliding keys gets its
first `TreeNode` at the **11th** insert rather than the 9th. And the third thing to add unprompted:
the resulting tree only bounds lookup if the keys are `Comparable`.

</details>

**Q2.** An interviewer says "Java 8 fixed `HashMap` under concurrency." What do you say?

<details><summary>Answer</summary>

Java 8 fixed **one specific failure**: the infinite loop. Java 7's `transfer` inserted at the head of
the new bin, re-heading a live chain, so two racing resizes could write `B.next = A` and then
`A.next = B` and leave a cycle — after which any `get` walking that bin spun at 100% CPU, in a
*reader* thread, with no exception. Java 8 builds fresh lo/hi lists by tail insertion and publishes
them at the end, so no live chain is ever re-headed and that cycle is impossible. Everything else
remains: two threads can both publish a new table and lose one's entries, `removeNode` can
resurrect a removed node through a stale `next`, `++size` tears, and `HashMap` can throw NPE or
AIOOBE from inside itself. `modCount` is racy too, so fail-fast cannot be relied on to tell you.

</details>

**Q3.** Which of these is a *version* trap and which was never true: "`ArrayDeque` uses a
power-of-two mask", "`EnumMap`'s entry iterator reuses one `Entry`", "a tree bin untreeifies at 6 on
removal"?

<details><summary>Answer</summary>

The first is a genuine version trap — true in JDK 8, false from JDK 9, which replaced the mask with
`inc`/`dec`/`sub` helpers. (And the neighbouring change is separate: the no-arg capacity went 16 → 17
in JDK 12, not in the JDK 9 rewrite.) The other two were **never** true. `EnumMap.EntryIterator`
allocates a fresh `Entry(index++)` per `next()` in JDK 8, 17, 21 and 25 alike — verified in all four
— and the untreeify-on-removal guard has been structural since Java 8 shipped, testing whether the
tree root is missing a child or grandchild and never reading `UNTREEIFY_THRESHOLD`. Distinguishing
"stale" from "always wrong" matters: for a stale claim you date it, for folklore you correct it.

</details>

**Q4.** Your service's p99 latency has a periodic spike traced to a `List` that grows to a few
million elements. Two candidate explanations, and how you would tell them apart.

<details><summary>Answer</summary>

Either the amortised growth copy or a bad access pattern. `ArrayList` growth is the likelier one: an
`add` at a capacity boundary does one `Arrays.copyOf` of the whole array — 4 MB of references at a
million elements — so the spike is periodic with geometrically increasing gaps, which is the
signature to look for. That is amortised O(1) behaving exactly as specified; the fix is to pre-size,
because amortised is a bound on the sequence and says nothing about any single call. The other
explanation is an O(n) operation somebody thinks is cheap — `contains`, `indexOf`, `remove(Object)`,
or a `removeAll` with a `List` argument — and those scale with *request rate*, not with a doubling
schedule, so the spike would not have geometric spacing. Allocation profiling separates them
immediately: the growth copy shows as large `Object[]` allocations at decreasing frequency.

</details>

**Q5.** You inherit code with `Collections.synchronizedMap(new HashMap<>())` shared across threads.
Name the three defects and the order you would fix them in.

<details><summary>Answer</summary>

(1) **Compound actions race** — every `containsKey`-then-`put` or `get`-then-`put` pair has a window
between two separate `synchronized` blocks. (2) **Iteration is unsynchronized** — `iterator()`,
`spliterator()` and `stream()` return the raw underlying objects, so any for-each over the wrapper is
unguarded and can throw CME or read torn state; the caller must hold `synchronized (wrapper)` across
the whole loop. (3) **It does not scale** — one mutex serialises readers against readers.

Fix order: replace the map with a `ConcurrentHashMap` first, because that dissolves (1) and (3)
together provided you express atomicity with `putIfAbsent`/`merge`/`compute` rather than with your
own two-call sequences, and it makes iteration weakly consistent so (2) stops being a correctness
issue. Only if the atomic unit spans more than one collection do you need your own lock — no wrapper
and no concurrent collection can express "these two maps update together". What you should *not*
"fix" is the mutex on the derived views: `keySet()`, `values()` and `entrySet()` genuinely do share
the outer mutex, in both JDK 8 and JDK 21.

</details>

---

**Leaves covered:** 5.2.1, 5.2.2, 5.2.3 (3 leaves)
**Leaves deferred:** none
**Diagrams included:** D-152 (rendered as a Markdown table, per its `table` type in the manifest; one
deliberate departure recorded inline — the manifest's single `ArrayDeque` row is two changes)
**Target version:** Java 21 LTS
**Lines:** 417
