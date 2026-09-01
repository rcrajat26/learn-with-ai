# 02 Java Collections — Interview, INTERMEDIATE tier — questions 19–36 (§5.1)

**Target version: Java 21 LTS.** | [Index](00-index.md)
Previous: [91-interview-intermediate.md](91-interview-intermediate.md) · Next: [91c-interview-intermediate-c-puzzles.md](91c-interview-intermediate-c-puzzles.md)

Second half of the INTERMEDIATE question set: questions 19–36 of 36. The tier summary table is in
[91](91-interview-intermediate.md); the puzzles are in
[91c](91c-interview-intermediate-c-puzzles.md).

## Q&A 19–36

### Q19. "What is `subList`, and what is dangerous about it?" (§5.1.31)

**Model answer.** It is a live index window onto the parent list, not a copy. Creating it is O(1)
and allocates about 32 bytes — the `SubList` holds only `root`, `parent`, `offset` and `size` — and
reads go straight to `root.elementData[offset + index]`, so even a nested sublist is one
dereference deep, not a chain.

Three dangers, in the order they bite.

**Invalidation.** A structural change to the parent made *not through the view* poisons the view:
the next operation on it throws `ConcurrentModificationException`. And the check is against the
**root**'s `modCount`, not the immediate parent's, so mutating a grandparent invalidates a nested
sublist. Note also that `parent.set(i, x)` does *not* poison it (`set` is not structural) while
`parent.sort(...)` and `parent.replaceAll(...)` both do.

**Retention.** The 32-byte view keeps the entire parent array reachable. `list.subList(0, 10)` of a
million-element list pins about 3.81 MiB alive — the classic "why is this cache holding 4 GB"
finding in a heap dump. The fix is `new ArrayList<>(sub)` or `List.copyOf(sub)`.

**Write-through, which is also its best feature.** Mutating through the view mutates the parent, and
that gives you the only public route to range deletion: `list.subList(a, b).clear()` deletes
`[a, b)` in one `System.arraycopy`. `removeRange` itself is `protected`, so the sublist is the door.

**One-line close:** a live 32-byte window that can pin megabytes and can be invalidated by a
change it did not make — copy it if you are going to keep it, and use `subList(a,b).clear()` when
you want a range delete.

### Q20. "Why is `EnumMap` faster than `HashMap` for enum keys?" (§5.1.34)

**Model answer.** Because it does not hash anything. Every enum constant has a dense
`ordinal()`, so `EnumMap` is a plain `Object[] vals` indexed by ordinal: `put` is literally
`vals[key.ordinal()] = maskNull(value)`. That is O(1) **worst case**, not expected — no hash, no
spread, no bin, no `equals` call, no collision, no resize, ever.

Two consequences beyond speed. Iteration is in **ordinal (declaration) order**, which is a
guarantee `HashMap` cannot give you. And the memory shape inverts: an `EnumMap`'s array is sized by
the *enum's* constant count, not by how many keys you put in, so it costs about `32 + 16 + 4N`
bytes regardless of occupancy. For a 5-constant enum that is 72 bytes total; for a 500-constant
enum it is about 2 KB even if you store two entries. The crossover where `EnumMap` starts losing to
`HashMap` on memory is roughly `N > 4m + 20` for `m` stored mappings.

The `keyUniverse` array is not even copied — it comes from
`SharedSecrets.getJavaLangAccess().getEnumConstantsShared`, shared across every `EnumMap` of that
type.

**If they push:** null keys throw (a key must have an ordinal) but null values are allowed via a
private sentinel. There is no `modCount`, so iterators are weakly consistent and never throw CME.
And the folklore that `EntryIterator` hands out a single reused `Entry` object is **false** — it
allocates a fresh `Entry(index++)` per `next()` in JDK 8 through 25. What is true is that the entry
holds only an `int index` and reads `vals[index]` **live**, so a retained entry tracks later changes
to the map; and collecting the entry set into a list gives you `SimpleEntry` *snapshots* instead,
which is exactly why the wrong model survives casual experiment.

**One-line close:** an ordinal-indexed array, so O(1) worst case with no hashing and ordinal
iteration order — paid for by an array sized to the enum, not to your data.

### Q21. "What is `WeakHashMap` for, and why is it not a cache?" (§5.1.35)

**Model answer.** It is for associating data with an object for exactly as long as *someone else*
keeps that object alive. The canonical use is metadata keyed by a live object — a listener
registry, a per-class computed value — where you want the entry to disappear when the key becomes
unreachable rather than at a time you choose.

The mechanism: each `Entry extends WeakReference<Object>`, so the entry **is** the reference to the
key. There is no background thread. When the GC clears a key it enqueues the entry on a
`ReferenceQueue`, and the entry is unlinked lazily by `expungeStaleEntries()`, which runs inside
ordinary operations — `getTable()` and `size()` are the funnels.

It is not a cache because it has no cache properties at all: **no size bound, no TTL, no eviction
policy, and the timing is the collector's**, not yours. It also has one specific failure that
guarantees a leak: if the **value** references its own key, the map holds the value strongly, the
value holds the key strongly, and the entry is immortal. The subtler variant is a cycle across two
entries — V1 references K2 and V2 references K1 — where neither holds *its own* key and both are
still immortal.

And in practice the keys people reach for never clear: `String` literals and `intern()`ed strings
are in the constant pool, small boxed `Integer`s are in the `valueOf` cache, `Class` objects live as
long as their loader.

**If they push:** the invariants a normal `Map` gives you do not hold. `size()` can shrink between
two adjacent calls with no modification in between, `isEmpty()` can flip, and `get` can start
returning `null` — because expunging happens *inside* those reads. `WeakHashMap` also has no
treeification, so a degenerate bucket stays O(n). For an actual cache, use Caffeine.

**One-line close:** entry lifetime tied to key reachability, not a policy — and a value that
references its key makes the entry immortal.

### Q22. "What is `IdentityHashMap` for?" (§5.1.36)

**Model answer.** For keying on object *identity* rather than on `equals` — it compares keys with
`==` and hashes with `System.identityHashCode`. It exists because there is a class of algorithms
where two equal-but-distinct objects must be treated as different: object-graph traversal and
transformation (have I visited *this* node?), serialization back-reference tables, proxy registries,
and cycle detection. Using a `HashMap` there would silently merge distinct nodes that happen to be
`equals`.

The implementation is unusual and worth knowing, because it explains the constraints. There is **no
`Entry` class at all** — keys and values interleave in one flat `Object[]`, key at an even index and
value at `i + 1`. Collisions are handled by **linear probing** (`nextKeyIndex` is `i + 2`), the
probe stops at the first `null` key slot, and deletion does a Knuth back-shift rather than leaving
tombstones. So a `remove` can *relocate* other entries, and there is no treeification.

Two sizing surprises: the constructor argument is an **`expectedMaxSize`**, not a capacity — the
class is the outlier among `java.util` hash containers — and the load factor is a fixed 2/3 of
capacity, so a default map (capacity 32, table length 64) resizes on the **22nd** `put`.

**If they push:** it deliberately violates the `Map` contract, and its javadoc says so. Its `equals`
is asymmetric against other maps: with the same key identity and an equal-but-distinct value,
`ihm.equals(hm)` is `false` while `hm.equals(ihm)` is `true`, because `IdentityHashMap`'s entry set
compares values by identity too while `AbstractMap.equals` compares them with `equals`. So never
put one in a `Set` or use one as a map key. And never key it on `String`, boxed primitives, or any
interned or cached type — identity is not stable for those in the way you expect.

**One-line close:** `==` keying for object-graph work, on a flat interleaved open-addressed table —
a documented contract violation, so keep it out of sets.

### Q23. "How does `PriorityQueue` work, and why isn't its iteration sorted?" (§5.1.37)

**Model answer.** It is a binary min-heap in an array. The heap invariant is only about the
ancestor relation: for every node and every descendant, `parent <= descendant`. **Nothing is
promised about siblings.** Index arithmetic does the tree: parent is `(k - 1) >>> 1`, children are
`2k + 1` and `2k + 2`, and the first leaf is at `size >>> 1`.

`offer` puts the element at the end and calls `siftUp`, which walks toward the root shifting parents
down — `log₂ n` comparisons and `d + 1` writes, no swaps. `poll` takes index 0, moves the last
element to the root and calls `siftDown`, which costs about `2·log₂ n` comparisons because each
level needs one comparison to pick the smaller child and one to decide whether to descend. Building
from a `Collection` is O(n) via `heapify`, which runs `siftDown` **backwards** from `(n >>> 1) - 1`.

Iteration is not sorted because iteration walks the **array**, and the array is heap order.
`queue[lastRet = cursor++]` — no ordering logic anywhere. The only guarantee is that index 0 is the
minimum. And that applies equally to `toString`, `forEach`, `stream()` and `toArray()`: all of them
show heap order. The only sorted view is a destructive drain by repeated `poll`.

**If they push:** the two related traps. Mutating an element's priority in place does not re-sift,
so `peek()` can return a non-minimum. And the queue is unbounded and unstable — `siftUp` breaks on
`>= 0`, so equal elements do not move, and their relative order is an artefact of array positions.
For tests, assert on the drained order, never on `toString`.

**One-line close:** an array binary heap where only the ancestor relation holds, so iteration is
array order — drain it with `poll` if you want sorted.

### Q24. "How would you find the top k elements of a stream of a billion numbers?" (§5.1.38)

**Model answer.** A bounded **min**-heap of size k. Push the first k elements; after that, compare
each arrival against the root and replace the root only if the arrival is larger. That is O(n log k)
time and O(k) memory, and it makes exactly one pass — which is the requirement a billion-element
stream is really testing.

```java
static <T> List<T> topK(Iterator<T> source, int k, Comparator<? super T> order) {
    PriorityQueue<T> heap = new PriorityQueue<>(k, order);   // MIN-heap by `order`
    while (source.hasNext()) {
        T next = source.next();
        if (heap.size() < k) {
            heap.offer(next);
        } else if (order.compare(next, heap.peek()) > 0) {   // beats the weakest keeper
            heap.poll();
            heap.offer(next);
        }
    }
    List<T> result = new ArrayList<>(heap);
    result.sort(order.reversed());                            // heap order is not sorted
    return result;
}
```

The counter-intuitive part is the min-heap for the *largest* k, and it is worth saying explicitly:
the root must be the **weakest element you are keeping**, because that is the one a newcomer has to
beat. A max-heap would put your best element where you keep looking, which tells you nothing about
what to evict.

The `else if` guard matters at scale: a losing element costs one comparison, not an `offer` plus a
`poll`. With random input, almost all of a billion elements lose immediately.

Compare the alternatives: sorting everything is O(n log n) time and O(n) memory, which does not fit;
`stream().sorted().limit(k)` is worse than it looks because `sorted()` is a **stateful** operation
that buffers the entire upstream before emitting anything — it will not terminate on an infinite
stream and it will not fit a billion elements in memory.

**If they push:** if the data is distributed, this is a natural two-phase reduction — top k per
shard, then a k-way merge of the shard results, which is O(k log shards). And if you need
approximate frequency rather than exact extremes, the answer changes to a count-min sketch or
Space-Saving.

**One-line close:** a size-k min-heap in one pass, O(n log k) and O(k) memory — and sort the k
results at the end, because the heap is not sorted.

### Q25. "How would you make an existing collection thread-safe?" (§5.1.42)

**Model answer.** In order of preference, and the first option is usually the right one:

1. **Replace it with a concurrent collection.** `ConcurrentHashMap` for a map,
   `ConcurrentHashMap.newKeySet()` for a set, `ConcurrentLinkedQueue` or a `BlockingQueue` for a
   queue, `ConcurrentSkipListMap` if you need sorted-and-concurrent (the only option). This is not
   just finer locking — it gives you atomic compound methods and iterators that never throw.
2. **Make it immutable and publish it safely.** `List.copyOf(...)` in a `final` field is thread-safe
   with no locking at all. If the data is written once and read many times, this is the cheapest
   correct answer, and it is the one candidates forget.
3. **Copy-on-write**, if reads dominate overwhelmingly and the collection is small.
4. **Wrap it** with `Collections.synchronizedMap`/`synchronizedList`. This is the *last* option, and
   you must say what it does not give you: iteration is not covered — `iterator()` returns the raw
   underlying iterator, so you hold `synchronized (theWrapper)` across the whole loop yourself — and
   compound actions are not atomic, because each call is its own `synchronized` block.
5. **Your own lock** around a plain collection, which is genuinely the right answer when the unit of
   atomicity spans more than one collection. No wrapper can express "these two maps update
   together".

The framing that lands: *thread safety is a property of an operation, not of a data structure*. A
`ConcurrentHashMap` does not make `if (!m.containsKey(k)) m.put(k, v)` safe; `putIfAbsent` does.

**If they push:** two facts about the wrappers. The derived views *do* share the outer mutex —
`synchronizedMap(m).keySet()` is constructed with the identical mutex field in both JDK 8 and JDK
21, so the folklore warning about version-dependent view locking is unfounded. And the wrapper's own
`merge`/`computeIfAbsent` **are** atomic, each being one `synchronized` block; it is only the
compound actions you write that race.

**One-line close:** prefer a concurrent collection or an immutable copy; a synchronized wrapper is
per-call only and leaves iteration and compound actions to you.

### Q26. "Why does `addAll` take `Collection<? extends E>` and a comparator `Comparator<? super T>`?"

**Model answer.** PECS — producer `extends`, consumer `super`. `addAll` only *reads* from its
argument, so the argument is a producer and `? extends E` lets you pass a `List<Integer>` to a
`Collection<Number>.addAll`. A comparator only *consumes* `T`, so `? super T` lets a
`Comparator<Object>` or a `Comparator<Animal>` sort a `List<Dog>` — which is what makes an inherited
`compareTo` usable.

The reason `add` is barred on a `List<? extends Number>` follows from the same rule: the wildcard
means "some specific unknown subtype of `Number`", and no value is provably safe for an unknown
subtype — the list might really be a `List<Integer>` and you might be adding a `Double`. Only `null`
is allowed. Reading, on the other hand, is always safe: whatever comes out is at least a `Number`.

The bound that trips people is `<T extends Comparable<? super T>>`, on `Collections.sort`/`max`/`min`.
Read it as "`T`, or any supertype of `T`, must be `Comparable`" — the `? super T` is there so that a
class whose `compareTo` is inherited from a parent still qualifies.

**If they push:** the practical rules are: use wildcards in parameters, avoid them in return types
(a wildcard return pushes capture problems onto every caller), and remember `List<Object>` is *not*
a supertype of `List<String>` — only `List<? extends Object>` is. That is also the deeper reason
generics are invariant: arrays chose covariance and pay for it at runtime with
`ArrayStoreException`, generics chose invariance and catch it at compile time.

**One-line close:** produce-`extends`, consume-`super`; `add` is barred under `? extends` because no
value is safe for an unknown subtype.

### Q27. "Is `removeIf` different from a loop with `Iterator.remove`?"

**Model answer.** On an `ArrayList`, very. `Collection`'s **default** `removeIf` is an iterator
loop calling `it.remove()`, and on an `ArrayList` each of those is an O(n) `arraycopy`, so the
default is O(n²). `ArrayList` overrides it with a two-pass algorithm that is O(n): the first pass
runs the predicate over every element and records the victims in a `long[]` bitset, and the second
pass compacts the survivors with a single shift per gap. `modCount` is bumped exactly once, between
the passes.

Details worth having: the bitset is allocated lazily, only after the first match, and sized from the
first condemned index rather than from 0 — `nBits(n)` is `((n - 1) >> 6) + 1`, a ceiling divide by
64. The predicate runs exactly once per element, always. And a *structural* mutation from inside the
predicate is detected and throws CME — after the predicate's side effects have already happened,
because the check is at the end of the pass.

So the answer to "which should I use" is: `removeIf` when the decision is per-element, a manual
iterator loop when you need other per-element logic in the same pass, and collect-then-`removeAll`
when the decision needs cross-element context.

**If they push:** `removeAll` and `retainAll` share one implementation, `batchRemove`, with a single
boolean flag. Its cost is receiver size × the argument's `contains`, and it has a nice property most
people never notice: if the argument throws mid-scan, the `catch` block slides the untested tail
down so the list is left consistent, and then rethrows.

**One-line close:** `ArrayList.removeIf` is a two-pass bitset compaction and O(n), where the
interface default with `it.remove()` would be O(n²).

### Q28. "What are the traps in `Collectors.toMap`?"

**Model answer.** Three, and all three are runtime failures on data that passed your tests.

**Duplicate keys throw.** The two-argument `toMap` throws `IllegalStateException: Duplicate key ...`
the first time two elements map to the same key. That is usually the *right* default, but it means
any `toMap` over data you do not control needs the three-argument form with an explicit merge
function.

**Null values throw.** `toMap` uses `map.merge` internally, and `merge` treats a null value as
"remove", so the implementation rejects it with a `NullPointerException` — even though the
underlying `HashMap` would happily store a null value. `groupingBy` does not have this problem;
`toMap` does.

**The result type is unspecified.** You get some `Map` — a `HashMap` today — so iteration order is
not defined. If you need order, use the four-argument form with a supplier:
`toMap(k, v, (a, b) -> b, LinkedHashMap::new)` or `TreeMap::new`.

**If they push:** the neighbouring family has the same shape of traps. `toList()` returns a mutable
list of unspecified type; `Stream.toList()` returns an unmodifiable one that *does* permit nulls;
`toUnmodifiableList()` returns an unmodifiable one that rejects them. And when you actually want a
count or a grouping, prefer `groupingBy(f, counting())` over a `toMap` with a merge function — it
says what it means and cannot hit the duplicate-key throw.

**One-line close:** duplicate keys throw `IllegalStateException`, null values throw NPE, and the map
type is unspecified — reach for the three- or four-argument form by default.

### Q29. "How do you find out which collection is using your heap?"

**Model answer.** Take a heap dump and ask the right question of it, rather than guessing from the
code.

Capture: `jcmd <pid> GC.heap_dump /tmp/heap.hprof`, or `jmap -dump:live,...` if you want a full GC
first. For a fast triage without a dump, `jcmd <pid> GC.class_histogram` shows live instance counts
per class, which is often enough to see 20 million `HashMap$Node`s.

Then in Eclipse MAT the queries that matter are collection-specific:

- **Dominator Tree** sorted by retained heap — who is actually keeping this alive.
- `collection_fill_ratio` and `array_fill_ratio` — over-allocation: `ArrayList`s that grew and were
  never trimmed, or a `HashMap` table that stayed huge after a `clear()`.
- `map_collision_ratio` — a ratio near 1.0 is a broken or degenerate `hashCode`, which is the
  finding you cannot get any other way.
- `collections_grouped_by_size` — the "one million empty `ArrayList`s" shape.

For a specific object in a test or a microbenchmark, JOL is the direct tool:
`ClassLayout.parseInstance(obj).toPrintable()` for the shallow layout and
`GraphLayout.parseInstance(obj).totalSize()` for the whole graph.

**If they push:** two production-side notes. Allocation *rate* is a different question from
retention — use JFR (`jdk.ObjectAllocationSample`) or async-profiler's `-e alloc` for that. And the
cheapest permanent guard is a gauge: register the size of any long-lived collection as a metric, so
the graph shows the leak before the heap does.

**One-line close:** heap dump plus MAT's collection queries — `collection_fill_ratio` for
over-allocation and `map_collision_ratio` for a bad `hashCode` — and JOL when you want exact bytes.

### Q30. "Why is `AbstractList` the wrong skeleton for a linked structure?"

**Model answer.** Because `AbstractList` implements its iterator in terms of `get(int)`. If your
`get(i)` is O(i), which it is for anything linked, then a full iteration is O(n²) — and the caller
has no idea, because they just wrote a for-each loop.

That is precisely why `AbstractSequentialList` exists: you implement `listIterator(int)` and it
derives `get`/`set`/`add`/`remove` from the cursor instead. `LinkedList` extends it. Note the
residual cost: `get(i)` on its own is still O(i); what you have fixed is *iteration*.

The wider point is that the six skeletons each demand different methods and hand back different
guarantees:

| Skeleton | You supply | You get free | The danger |
|---|---|---|---|
| `AbstractCollection` | `iterator`, `size` | `contains`, `toString`, `toArray`, `addAll` | no `equals`/`hashCode` |
| `AbstractList` | `get`, `size` | iterator, `equals`, `indexOf`, `subList` | O(n²) iteration if `get` is not O(1) |
| `AbstractSequentialList` | `listIterator(int)` | `get`/`set`/`add`/`remove` | `get(i)` alone is still O(i) |
| `AbstractSet` | (from `AbstractCollection`) | set `equals`/`hashCode`, smaller-side `removeAll` | — |
| `AbstractQueue` | `offer`, `poll`, `peek` | `add`, `remove()`, `element()` | bans null elements |
| `AbstractMap` | `entrySet` | `get`, `containsKey`, `equals`, `hashCode` | O(n) `get` unless you override it |

**If they push:** the choice between extending and delegating. Extending a *concrete* class is the
trap — override `add` on `ArrayList` and `addAll` may bypass it, because sibling methods are free to
use internal state directly. Delegation costs boilerplate and gives you every entry point, which is
why `HashSet` delegates to a `HashMap` rather than extending one.

**One-line close:** `AbstractList` derives iteration from `get`, so on a linked structure iteration
becomes O(n²) — use `AbstractSequentialList`, or delegate.

### Q31. "Is `HashMap` iteration order stable?"

**Model answer.** Deterministic, but not guaranteed and not stable across changes. Iteration walks
the table from slot 0 upward and, within a slot, follows the bin's chain. So the order is a function
of the table length and the keys' hashes — there is no salt anywhere in `HashMap`, and `hash()` is
pure, so two runs of the same program on the same JDK give the same order.

What breaks it: **every resize**. Keys that shared a slot are redistributed — each key either stays
at index `j` or moves to `j + oldCapacity` — so the interleaving changes wholesale. With defaults
the first resize happens on the 13th insert (capacity 16, threshold 12). Iteration is also
O(capacity + size), because every empty slot is visited.

The illusion that catches people: small `Integer` keys look sorted, because `Integer.hashCode()` is
the value, the spread `h ^ (h >>> 16)` is the identity below 65,536, and `v & (n − 1) == v` while
`v` is below the capacity. It stops looking sorted the moment a key exceeds the capacity (100 lands
in slot 4 of a 16-slot table) or goes negative.

**If they push:** two refinements. Order **within** a plain bin is chain order, and since Java 8's
tail-append it survives a resize — Java 7's head insertion reversed every bin. But once a bin
treeifies, the head of the chain is whichever node is currently the **red-black root**, because
`moveRootToFront` splices it there, and a rebalance changes it — so "table order then insertion
order" is wrong for treeified bins. And if you want randomised-per-run order, that is `Set.of`/
`Map.of`, which salt their iterators from `System.nanoTime()` deliberately.

**One-line close:** deterministic per JDK build and key set, unspecified by contract, and rearranged
by every resize — use `LinkedHashMap` or `TreeMap` if you need an order.

### Q32. "Which collections are `Serializable`, and what is `transient`?"

**Model answer.** Almost all the concrete `java.util` collections are `Serializable`; the **views**
are not. `map.keySet()`, `values()`, `entrySet()`, `subList`, and Java 21's reversed views all fail,
because a view has no independent state to write.

The interesting part is what each class marks `transient` and why, because in every case the reason
is that the *in-memory layout is not portable*:

- `ArrayList.elementData` is transient. A custom `writeObject` writes `size` and the live elements,
  so you do not serialise unused capacity.
- `HashMap`'s `table` is transient. The bucket layout depends on `hashCode()` values *at write time*,
  and the reading JVM may compute different ones — `Object.hashCode` is identity-based, and enum
  hashes are per-run. So `readObject` re-`put`s every entry instead.
- `LinkedList`'s node links, and `TreeMap`'s tree structure, likewise: entries are written in order
  and the structure is rebuilt on read. `TreeMap` writes its comparator, which therefore must itself
  be `Serializable` — a lambda comparator makes the map unserializable at runtime.

The `HashMap` rule has a nasty corollary: if a key's `hashCode` changed between write and read, the
entry lands in a different bucket and is *unreachable by key* in the deserialised map. That is the
serialization form of the mutable-key trap.

**If they push:** the immutable collections use a serialization **proxy**. `List.of(...)` has a
`writeReplace` that emits a `java.util.CollSer` — a package-private *top-level* class, not
`ImmutableCollections$CollSer` — carrying a tag and a flat element array, and the implementation
classes' own `readObject` throws `InvalidObjectException`. A round-tripped `Set.of` re-shuffles
under the **receiving** JVM's salt. And collections are a known deserialization gadget-chain
surface, which is why `readObject` on untrusted input is a security question, not just a correctness
one.

**One-line close:** concrete classes yes, views no — and the storage array is transient everywhere,
because bucket and node layout is not portable across JVMs.

### Q33. "How do you write a fixed-capacity queue that overwrites its oldest element?"

**Model answer.** A ring buffer: an array plus `head`, `tail` and — the decision that matters — an
explicit `count`. With `count` you can distinguish full from empty when `head == tail`; without it
you must waste a slot, which is the trade `ArrayDeque` makes.

The JDK has nothing for this, and that is the point of the question: `ArrayDeque` *grows* instead of
overwriting, so it gives you no bound and no backpressure, and a `BlockingQueue` blocks instead of
overwriting. Overwrite-oldest is a genuinely different policy — it is what you want for a
fixed-size audit trail, a metrics window, or a crash-log buffer, where the newest data is the data
you care about.

The invariants to state: `size` is `count`, not derived from the indices; on overwrite you advance
**both** `tail` and `head`; and you null the vacated slot so the overwritten element can be
collected. Wraparound uses `(i + 1) % capacity`, or a mask if you force the capacity to a power of
two — which is what `ArrayDeque` did until JDK 9, when it moved to explicit `inc`/`dec`/`sub`
helpers with a single branch each.

**If they push:** the closest library equivalents are Apache Commons Collections'
`CircularFifoQueue` and, for the lock-free single-producer case, JCTools. And if the buffer is
crossing threads, do not write your own — the memory-ordering requirements on `head`/`tail` are
exactly where hand-rolled ring buffers go wrong.

**One-line close:** array plus `head`/`tail` plus an explicit `count`, advancing both indices on
overwrite — the JDK has no overwrite-oldest queue, which is why this one is worth writing.

### Q34. "Is there any case where `LinkedList` beats `ArrayDeque`?"

**Model answer.** Two, and both are narrow.

**Null elements.** `ArrayDeque` rejects `null` because `null` is its free-slot marker.
`LinkedList` accepts it. If a `null` genuinely means something in your queue, that is a real reason.

**A held `ListIterator`.** `LinkedList` is also a `List`, so you can walk it with a `ListIterator`
and splice at the cursor in true O(1) — no shift, no copy. Measured in this set: about 7 ns per
insert, flat from 1,000 to 100,000 elements, where the same insert *located by index* is 21–32×
slower than `ArrayList`. That is the shape of the whole `LinkedList` story: the splice is fast, the
navigation is not.

Everything else favours `ArrayDeque`: 4 bytes per slot against 24 bytes per node, no per-element
allocation, and prefetchable iteration over two contiguous slices.

**If they push:** the parallel-stream angle is a good one. `LinkedList`'s spliterator is `SIZED` and
`SUBSIZED`, but `trySplit` cannot index — it walks and copies a prefix into an `Object[]`, with
`BATCH_UNIT = 1024` growing per call. So for a list smaller than 1,024 elements the *first* batch
takes everything and the split is useless, and for larger ones each split costs a walk.
`ArrayList` splits at `(lo + hi) >>> 1` in constant time. That is why `linkedList.parallelStream()`
is nearly always slower than the sequential version.

**One-line close:** null tolerance and a held cursor — otherwise `ArrayDeque`, which is smaller,
faster and splits properly.

### Q35. "`ConcurrentHashMap.newKeySet()`, `Collections.newSetFromMap`, or `CopyOnWriteArraySet`?"

**Model answer.** All three are "a set built on something else", and they differ in what that
something is.

`ConcurrentHashMap.newKeySet()` is the default answer for a concurrent unsorted set: it creates a
private `ConcurrentHashMap` and returns a view of its key set, so you get O(1) amortised `add` and
`contains`, striped/CAS concurrency, and weakly consistent iteration that never throws. Note the
distinction from `chm.keySet()` on an existing map, whose `add` throws
`UnsupportedOperationException` because there is no value to store — while `chm.keySet(someValue)`
returns a live view whose `add` inserts that value.

`Collections.newSetFromMap(m)` is the generic form of the same trick, and its use is when you need a
set with some *other* map's semantics: `newSetFromMap(new IdentityHashMap<>())` for an identity set,
`newSetFromMap(new WeakHashMap<>())` for a weak set. It delegates everything — cost, ordering, null
policy, thread safety — to the map you pass, and it requires that map to be empty at construction.

`CopyOnWriteArraySet` is the odd one: it wraps a `CopyOnWriteArrayList`, not a map, so `add` and
`contains` are **O(n)** scans and every write copies the array. Use it only for a small read-mostly
set — the listener-registry shape again.

**One-line close:** `newKeySet()` for concurrent, `newSetFromMap` to borrow another map's semantics,
`CopyOnWriteArraySet` only when it is small and read-mostly, because it is a list underneath.

### Q36. "How do you build an immutable value type with a collection field?"

**Model answer. Copy on the way in, and hand back something the caller cannot use to reach your
state.** A `record` gets `equals`/`hashCode`/`toString` right but does **not** make its components
immutable, so a record holding a `List` is only as immutable as that list.

```java
public record Order(String id, List<String> lineItems) {
    public Order(String id, List<String> lineItems) {
        this.id = Objects.requireNonNull(id);
        this.lineItems = List.copyOf(lineItems);   // snapshot at the boundary
    }
}
```

`List.copyOf` in the canonical constructor is the whole trick: the caller cannot keep a handle on
the list you actually hold, and the generated accessor can safely return the field directly, at zero
cost, because it is already immutable. `List.copyOf` also rejects nulls, and it returns the argument
unchanged when the argument is already a null-free immutable list — so the common path is free.

What it does **not** buy you is depth. If `lineItems` were a `List<StringBuilder>`, the list is
frozen and the builders are not. There is no deep-copy factory anywhere in `java.util`; the only
route to deep immutability is an immutable element type all the way down.

**If they push:** do not use `Collections.unmodifiableList(field)` for this. It is a view, so it
leaves your field mutable *and* lets the caller observe your mutations mid-iteration. And for a
`record` with an array component, replace the array with a `List` — the generated `equals` compares
array *identity*, so two logically-equal records with distinct arrays are not `equals`.

**One-line close:** `List.copyOf` in the constructor, return the field directly, and remember it is
shallow — an immutable element type is the only route to depth.

## Pitfalls

### Returning `Collectors.toMap` results and assuming order

**Wrong**

```java
Map<String, Integer> byName = people.stream()
        .collect(Collectors.toMap(Person::name, Person::age));   // ISE on a duplicate name
```

Two bugs: the map type and iteration order are unspecified, and the first duplicate name throws
`IllegalStateException` in production on data your test did not have.

**Right**

```java
Map<String, Integer> byName = people.stream()
        .collect(Collectors.toMap(
                Person::name,
                Person::age,
                (a, b) -> b,            // explicit duplicate policy
                LinkedHashMap::new));   // explicit map type, so order is defined
```

**Why people believe it:** the two-argument form is the one in every example, and it works right up
until the data contains a duplicate key or someone depends on encounter order.

### Keying an `IdentityHashMap` on strings

**Wrong**

```java
Map<String, Config> byName = new IdentityHashMap<>();
byName.put("prod", config);
String key = readFromFile();          // "prod", but a fresh object
Config c = byName.get(key);           // null — different identity
```

**Right**

```java
Map<String, Config> byName = new HashMap<>();   // equals-based, which is what you meant
```

**Why people believe it:** the literal-to-literal case works, because `"prod"` in two places in
source is the *same* interned object. It fails the moment a key arrives from I/O, parsing or string
concatenation — so the bug appears only with real input.

## Cheat sheet

| Question | The one-line answer |
|---|---|
| `subList` fields | `root`, `offset`, `size` — ~32 bytes, reads are one dereference |
| `subList` invalidation | structural change to the **root** poisons it; `set` does not, `sort` does |
| `subList` retention | pins the whole parent array — `List.copyOf(sub)` to detach |
| Range delete | `list.subList(a, b).clear()`; `removeRange` is `protected` |
| `EnumMap` mechanism | `vals[key.ordinal()]` — O(1) worst case, no hashing, ordinal iteration order |
| `EnumMap` memory | `32 + 16 + 4N` for the enum's N constants, whatever the occupancy |
| `EnumMap.EntryIterator` | allocates a fresh `Entry` per `next()`; the entry reads `vals[index]` live |
| `WeakHashMap` purpose | entry lifetime tied to key reachability; no bound, no TTL, GC-timed |
| `WeakHashMap` guaranteed leak | value references its own key (or a two-entry cycle) |
| Keys that never clear | `String` literals/`intern()`, `Integer` `[-128,127]`, `Class`, enums |
| `WeakHashMap.size()` | can shrink between adjacent calls — expunge runs inside reads |
| `IdentityHashMap` | `==` keying, flat interleaved table, linear probing, back-shift deletion |
| `IdentityHashMap` ctor arg | `expectedMaxSize`, not capacity; default resizes on the 22nd put |
| `IdentityHashMap.equals` | asymmetric against other maps — never put one in a `Set` |
| Heap invariant | ancestor ≤ descendant; nothing about siblings |
| Heap index maths | parent `(k-1) >>> 1`, children `2k+1`/`2k+2`, first leaf `size >>> 1` |
| `heapify` | `siftDown` backwards from `(n >>> 1) - 1`, O(n) |
| Heap iteration | array order; only index 0 is the minimum; drain with `poll` for sorted |
| Top k of n | size-k **min**-heap, one pass, O(n log k) time, O(k) memory |
| Why min-heap for top k | the root is the weakest keeper — the bar a newcomer must clear |
| `stream().sorted().limit(k)` | `sorted()` is stateful and buffers everything — wrong for a huge stream |
| Thread-safety options | concurrent collection > immutable copy > copy-on-write > wrapper > your own lock |
| Wrapper does not cover | `iterator()`/`spliterator()`/`stream()`, and compound actions |
| PECS | producer `extends`, consumer `super`; `add` barred under `? extends` |
| `<T extends Comparable<? super T>>` | `T` or a supertype must be `Comparable` — admits inherited `compareTo` |
| `ArrayList.removeIf` | two-pass `long[]` bitset compaction, O(n); the interface default is O(n²) |
| `removeAll`/`retainAll` | one `batchRemove` with a boolean; repairs the tail if the argument throws |
| `Collectors.toMap` traps | duplicate key → `IllegalStateException`, null value → NPE, map type unspecified |
| Heap-dump triage | `jcmd GC.heap_dump`; MAT `collection_fill_ratio`, `map_collision_ratio` |
| Exact bytes for one object | JOL `ClassLayout.parseInstance` / `GraphLayout.parseInstance` |
| `AbstractList` danger | derives iteration from `get`, so O(n²) on a linked structure |
| Linked-structure skeleton | `AbstractSequentialList` — you supply `listIterator(int)` |
| `HashMap` iteration order | slot 0 upward, then chain order; no salt; rearranged by every resize |
| Treeified bin head | the current red-black root (`moveRootToFront`), **not** insertion order |
| Views and serialization | views are **not** `Serializable`; storage arrays are `transient` everywhere |
| `HashMap` deserialization | entries are re-`put`; a changed `hashCode` strands the entry |
| Immutable collections on the wire | `writeReplace` → `java.util.CollSer`; `Set.of` re-shuffles under the receiver's salt |
| Overwrite-oldest queue | ring buffer with an explicit `count`; the JDK has none |
| `LinkedList` over `ArrayDeque` | null elements, or a held `ListIterator` |
| `LinkedList` spliterator | `trySplit` copies a prefix, `BATCH_UNIT = 1024` — one batch takes a small list whole |
| Concurrent set | `ConcurrentHashMap.newKeySet()`; `chm.keySet().add` throws, `chm.keySet(v).add` works |
| `CopyOnWriteArraySet` | a list underneath — `add`/`contains` are O(n) |
| Immutable value type | `List.copyOf` in the constructor, return the field directly, still shallow |
| `record` with an array component | generated `equals` compares array identity — use a `List` |

## Self-test

**Q1.** A heap dump shows a 4 MB `Object[]` retained by a 32-byte object. What is the 32-byte
object, and what is the fix?

<details><summary>Answer</summary>

Almost certainly an `ArrayList$SubList` (or an `ImmutableCollections$SubList`). It holds `root`,
`offset` and `size` and nothing else, so it is tiny — but the `root` reference keeps the parent's
entire backing array reachable, including the million elements outside the window. A one-million
element `Object[]` is 4,000,016 bytes under compressed oops. The fix is to detach:
`new ArrayList<>(sub)` for a mutable copy or `List.copyOf(sub)` for an immutable one. The same shape
occurs with `String.substring` in very old JDKs and with a retained `Map.Entry`.

</details>

**Q2.** Why does `EnumMap` beat a `HashMap` with enum keys even though enum `hashCode` is cheap?

<details><summary>Answer</summary>

Because the cost is not the hash computation, it is everything after it. `HashMap` must spread the
hash, mask it to a bin, load the bin, compare the cached hash, compare the reference, possibly walk
a chain, and possibly resize. `EnumMap` does one array store at `key.ordinal()` — O(1) *worst case*,
with no collisions possible by construction. It also gets ordinal iteration order for free and
allocates one array for the whole universe rather than a `Node` per entry. The relevant enum
`hashCode` fact is different: it is declared `public final` on `Enum` and is identity-based, so it
is stable within a run but not across runs, which makes a plain `HashMap` over enum keys have
per-run iteration order.

</details>

**Q3.** Your `WeakHashMap<Session, UserData>` never shrinks. The `UserData` has a `session` field.
Explain and fix.

<details><summary>Answer</summary>

The map holds the key weakly but the **value** strongly: `map → table → Entry.value → UserData →
session`. So the key is strongly reachable through the map's own value, the GC never clears it, and
the entry is immortal. This is the documented value-holds-key leak. Fixes, in order of preference:
remove the back-reference from `UserData`; or store
`map.put(session, new WeakReference<>(userData))` and unwrap on `get`; or stop using
`WeakHashMap` and use Caffeine with an explicit size or time bound, which is what you probably
wanted. Watch for the two-entry variant too, where V1 references K2 and V2 references K1 — neither
value holds *its own* key, and both entries are still immortal.

</details>

**Q4.** `PriorityQueue.toString()` on a queue of `3, 1, 2` prints `[1, 3, 2]`. Is that a bug?

<details><summary>Answer</summary>

No. `toString` walks the backing array, and the array is in heap order, which only promises that
every node is ≤ its descendants. Index 0 is the minimum (1), and 3 and 2 are its children in
whatever positions `siftUp` left them. There is no promise about siblings, so `[1, 3, 2]` and
`[1, 2, 3]` are both valid heaps for that input. The same applies to `forEach`, `stream()`,
`toArray()` and iteration. If a test needs a defined order, drain the queue with repeated `poll`.

</details>

**Q5.** You need a set of 50,000 elements shared by 16 threads, mostly `contains` with occasional
`add`. Which set, and why not the other two?

<details><summary>Answer</summary>

`ConcurrentHashMap.newKeySet()`. It gives O(1) `contains` with no lock on the read path, per-bin
locking for writes, and iterators that never throw. `CopyOnWriteArraySet` is wrong twice over at
this size: it is a `CopyOnWriteArrayList` underneath, so `contains` is an O(n) scan of 50,000
elements on every call, and each `add` copies the whole array. `Collections.synchronizedSet(new
HashSet<>())` serialises all 16 threads on one mutex even for reads, and still leaves you to lock
around any iteration yourself. If the set had to be sorted, the answer would change to
`ConcurrentSkipListSet` — the only concurrent sorted option.

</details>

**Q6.** Why is `HashMap`'s `table` field `transient` when the whole point of serializing a map is to
preserve its contents?

<details><summary>Answer</summary>

Because the table *layout* is not portable, only the contents are. A key's bucket is derived from
its `hashCode()`, and `hashCode()` is not required to be stable across JVMs — `Object.hashCode` is
identity-based, `Enum.hashCode` is identity-based, and any user class may compute differently under
a different JVM or configuration. Writing the array would produce a structure the reading JVM
cannot trust, so `writeObject` writes the entries and `readObject` re-`put`s them, rebuilding the
table under the *reader's* hashes. The corollary is the serialization form of the mutable-key trap:
if a key's `hashCode` changed between write and read, the entry is still in the map but no lookup
will find it.

</details>

---

**Leaves covered:** 5.1.31, 5.1.34, 5.1.35, 5.1.36, 5.1.37, 5.1.38, 5.1.42 (7 leaves)
**Leaves deferred:** none
**Diagrams included:** none
**Target version:** Java 21 LTS
**Lines:** 734
