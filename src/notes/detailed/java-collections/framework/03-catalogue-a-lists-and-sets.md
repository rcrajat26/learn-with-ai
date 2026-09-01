# 02 Java Collections — The framework itself — BASICS (§1.4 Every concrete implementation: the List and Set catalogue)

**Target version: Java 21 LTS.** | [Index](../00-index.md)
Previous: [framework/02-interface-method-surfaces.md](02-interface-method-surfaces.md) · Next: [framework/04-catalogue-b-maps.md](04-catalogue-b-maps.md)

Thirteen concrete classes implement `List` or `Set` in the JDK. Before touching
any one of them, place it on the hierarchy — this file's job is the map, not
the streets. The streets (growth arithmetic, node layout, write-path cost) live
in the sibling files linked from each scope note below; do not expect that
detail here.

![The full java.util interface hierarchy in Java 21 — locate every class in this catalogue on it before reading further](../diagrams/D-03-interface-hierarchy-java21.svg)

## The master attribute grid

This table is the spine of the file. Every leaf in §1.4 has a row.

| Class | Backing structure | Ordering guarantee | Null policy | Thread safety | Iterator type | Default/initial capacity | Pick it when | Do not pick it when |
|---|---|---|---|---|---|---|---|---|
| `ArrayList` | resizable `Object[]` | insertion order | nulls allowed | unsynchronized | fail-fast, `RandomAccess` | 10 on first add (lazy) | random access, iteration-heavy, append-heavy | frequent mid-list insert/remove |
| `LinkedList` | doubly-linked `Node` objects | insertion order | nulls allowed | unsynchronized | fail-fast, not `RandomAccess` | n/a (no array) | you need `Deque` semantics, frequent head/tail ops | you need indexed `get(i)` in a loop |
| `Vector` | resizable `Object[]` | insertion order | nulls allowed | synchronized (every method) | fail-fast | 10, doubles (or `capacityIncrement`) | legacy code already using it | any new code — see `CopyOnWriteArrayList` or external synchronization |
| `Stack` | `Vector` subclass | insertion order (LIFO via API) | nulls allowed | synchronized (inherited) | fail-fast, bottom-to-top | 10 (inherited) | never in new code | always — use `ArrayDeque` |
| `CopyOnWriteArrayList` | immutable snapshot `Object[]`, swapped on write | insertion order | nulls allowed | thread-safe, lock-free reads | snapshot iterator, never throws CME | 0 (grows on first add) | read-heavy, write-rare, concurrent iteration | write-heavy — every write copies the array |
| `HashSet` | `HashMap<E,Object>` wrapper | none | one null | unsynchronized | fail-fast | 16 buckets, load factor 0.75 | fastest general-purpose set, order irrelevant | you need insertion or sorted order |
| `LinkedHashSet` | `LinkedHashMap<E,Object>` wrapper | insertion order (`SequencedSet` in 21) | one null | unsynchronized | fail-fast | 16 buckets, load factor 0.75 | need predictable iteration at hash-map speed | memory is tight (extra link pointers) |
| `TreeSet` | `TreeMap<E,Object>` wrapper (red-black tree) | sorted (natural or `Comparator`) | no nulls with natural ordering | unsynchronized | fail-fast, in-order | n/a (tree) | need sorted iteration, range views | insertion order matters, or O(1) lookup matters |
| `EnumSet` (abstract) | single `long` (`RegularEnumSet`) or `long[]` (`JumboEnumSet`) | natural enum declaration order | no nulls | unsynchronized (wrap for concurrency) | fail-fast, ordinal order | fixed to enum universe size | any set whose keys are one enum type | keys are not all the same enum type |
| `CopyOnWriteArraySet` | `CopyOnWriteArrayList` internally | insertion order | nulls allowed | thread-safe, lock-free reads | snapshot iterator | 0 (grows on first add) | tiny, read-heavy, concurrent listener sets | anything with more than a handful of elements |
| `ConcurrentSkipListSet` | `ConcurrentSkipListMap` (skip list) | sorted | no nulls | thread-safe, lock-free reads/writes | weakly consistent | n/a (skip list) | concurrent sorted set, range queries under contention | single-threaded — `TreeSet` is cheaper |
| set from `newSetFromMap` | caller-supplied `Map<E,Boolean>` | whatever the backing map gives | whatever the backing map allows | whatever the backing map gives | delegates to the map's key set | delegates to the map | you need a `Set` view over a map with no `Set` counterpart (`WeakHashMap`, `IdentityHashMap`) | a purpose-built set class already exists |
| set from `newSequencedSetFromMap` | caller-supplied `SequencedMap<E,Boolean>` | the map's defined sequence | whatever the backing map allows | whatever the backing map gives | delegates, exposes `SequencedSet` | delegates to the map | same need as above, but you also want `reversed()`, `getFirst()`, `getLast()` | the backing map is not a `SequencedMap` |

## Primary concept: `ArrayList` vs `LinkedList` vs `Vector`/`Stack`

**Mental model.** `ArrayList` is a shelf of numbered slots — grab slot 47
directly. `LinkedList` is a chain of boxes, each holding its neighbours'
addresses — to reach box 47 you walk the chain from whichever end is closer.
`Vector` is the same shelf as `ArrayList`, but every reach for it requires
first taking a lock, whether or not anyone else is around.

**Why it exists.** Before generics-era collections, arrays gave fast random
access but fixed size; linked structures gave flexible size but no random
access. `ArrayList` and `LinkedList` are the two ends of that tradeoff made
concrete and interchangeable behind `List`. `Vector` predates the Collections
Framework entirely (JDK 1.0) and was retrofitted to implement `List` in 1.2;
`Stack` predates it too, bolted onto `Vector` rather than given its own
implementation.

**When to reach for it, and when not.** Default to `ArrayList` — cache
locality and O(1) indexed access win in the overwhelming majority of real
workloads, including ones with occasional inserts, because the memory-copy
cost of `System.arraycopy` is cheap in practice compared to pointer-chasing
through scattered heap objects. Reach for `LinkedList` only when you are
overwhelmingly using it as a `Deque` (push/pop/offer at both ends) and never
indexing into the middle — and even then, `ArrayDeque` usually wins because it
avoids per-element node allocation. Never reach for `Vector` or `Stack` in new
code: `Vector`'s synchronization is per-method, not per-transaction, so
compound operations (`if (!v.isEmpty()) v.get(0)`) still race; use
`CopyOnWriteArrayList`, `Collections.synchronizedList`, or a concurrent
collection instead.

**How it works.** `ArrayList` holds an `Object[] elementData` and a `size`
field; `add` writes to `elementData[size++]`, growing the array via
`Arrays.copyOf` when full. `LinkedList` holds `first`/`last` node references;
`add(index)` walks from whichever end is closer (`index < size/2` picks the
head) before splicing. `Vector` is structurally identical to `ArrayList` but
every public method carries `synchronized`; its growth policy differs too —
see the version trap below. `[X-REF]` The exact growth constants (`ArrayList`
grows by 1.5×, `Vector` by 2× or by `capacityIncrement`) and the `grow()`
source walk belong to `../array-list/01-internals-a-growth.md`; the
`LinkedList` node layout (`Node<E>` with `item`, `next`, `prev`) and the
mid-insert benchmark belong to `../linked-list/01-internals.md` — read both
before an internals-tier interview question on either.

No new diagram is assigned here; the shape is carried by the attribute grid
above and by `D-03-interface-hierarchy-java21.svg`, which already shows where
all three sit under `List`.

```java
List<Integer> shelf = new ArrayList<>();   // O(1) get(i), amortised O(1) add
shelf.add(10);
shelf.add(0, 5);                            // O(n): shifts everything right

Deque<Integer> chain = new LinkedList<>();  // O(1) at both ends
chain.addFirst(1);
chain.addLast(2);
chain.get(chain.size() / 2);                // O(n): walks from nearer end

@SuppressWarnings("deprecation")
Stack<Integer> legacy = new Stack<>();      // extends Vector — every op synchronized
legacy.push(1);
legacy.push(2);
for (int i : legacy) {
    System.out.print(i + " ");              // prints "1 2" — bottom to top,
}                                            // the opposite of pop() order
```

**Pitfall:** assuming `Stack`'s iterator visits in pop order. `pop()` returns
2 first (LIFO), but the `Iterator`/for-each walks the underlying `Vector`
index 0 upward — bottom to top — so the same loop that "looks like it prints
pop order" prints insertion order instead. `[TRAP]` Fix: iterate
`Collections.reverse`d, or better, do not use `Stack` — use `ArrayDeque` and
its `push`/`pop`/`peek`, which iterate top-to-bottom as expected.

**Insight:** `LinkedList` implements both `List` and `Deque`; most of its real
usage in production code is exclusively through the `Deque` methods
(`offer`, `poll`, `peek`), because that is the one thing it is actually good
at.

`[VERSION-TRAP]` `Vector`'s growth has never been 1.5× — it doubles capacity
by default (`capacityIncrement == 0` triggers `newCapacity = oldCapacity * 2`)
and always has, since JDK 1.0. The 1.5× figure belongs to `ArrayList` alone;
confusing the two is a common wrong answer on the "how much does an ArrayList
grow by" question. `[NUM]` For a `Vector` starting at capacity 10 with no
`capacityIncrement`: 10 → 20 → 40 → 80, always exactly double. `[X-REF]` Full
legacy mechanics (`elementCount`, `capacityIncrement`, the synchronized
`Enumeration`) are in `../framework/07-legacy-and-version-history.md`.

> **`ArrayList`** is an unsynchronized, resizable `Object[]`-backed `List`
> giving amortised O(1) indexed access and append, O(n) mid-list insert;
> **`LinkedList`** trades that indexed access for O(1) operations at either
> end via doubly-linked nodes; **`Vector`**/**`Stack`** are their
> synchronized, pre-generics ancestors that no new code should choose.

## Primary concept: `CopyOnWriteArrayList`

**Mental model.** Every writer photographs the entire list, edits the photo,
and nails the new photo up in place of the old one. Readers already holding
the old photo keep looking at it — undisturbed, and blissfully unaware a new
one now hangs on the wall.

**Why it exists.** `Vector` and `Collections.synchronizedList` block readers
during writes and throw `ConcurrentModificationException` if you iterate while
another thread mutates. Neither is acceptable for the read-mostly, write-rare
"list of observers" pattern (listener lists, cached config snapshots), where
you want iteration to never throw and never block on a concurrent write.

**When to reach for it, and when not.** Reach for it when reads vastly
outnumber writes and iteration correctness (no CME, ever) matters more than
write throughput — the canonical case is a listener/observer list mutated
rarely at startup or shutdown and iterated constantly. Do not reach for it for
anything write-heavy: every single `add`, `set`, or `remove` copies the entire
backing array, so a list of 100,000 elements with frequent writes is
catastrophic — `Collections.synchronizedList(new ArrayList<>())` or a
`ConcurrentLinkedQueue`-shaped structure wins there instead.

**How it works.** `[X-REF]` The full write-path mechanism — lock acquired,
new array allocated at `old.length + 1` (or fewer for bulk ops), contents
copied, element placed, reference swapped via `volatile` field, lock released
— and the cost-crossover analysis against `synchronizedList` under varying
read:write ratios both live in `../concurrent-collections/04-copy-on-write.md`.
The one-paragraph version: reads never lock and never see a torn list because
they always dereference the current, fully-built array; writes serialize on
an internal lock and pay O(n) per call regardless of what changed.

No new diagram — see `../concurrent-collections/04-copy-on-write.md` for the
snapshot-swap diagram if one is assigned there.

```java
List<String> listeners = new CopyOnWriteArrayList<>();
listeners.add("a");
listeners.add("b");

Iterator<String> it = listeners.iterator();  // snapshot taken here
listeners.add("c");                           // does not affect `it`
while (it.hasNext()) {
    System.out.println(it.next());            // prints only "a", "b"
}
System.out.println(listeners.size());          // 3
```

**Pitfall:** assuming the snapshot iterator sees new elements added mid-loop,
by analogy with `ArrayList`'s fail-fast behaviour throwing instead of silently
missing them. Neither happens here: no exception, no visibility of the
concurrent add — the iterator is frozen to the array it captured. Fix: treat
`CopyOnWriteArrayList` iteration as "a consistent point-in-time view," never
as "a live view," and re-fetch a fresh iterator if you need to see later
writes.

> **`CopyOnWriteArrayList`** gives lock-free, always-consistent, never-CME
> iteration by copying the entire backing array on every mutation — cheap for
> readers, increasingly expensive for writers as the list grows.

## Primary concept: the four hash/linked/tree/enum `Set` families

**Mental model.** `HashSet`, `LinkedHashSet`, and `TreeSet` are not
independent data structures — each is a thin `Set` face painted onto an
existing `Map` implementation, using the element as the key and a shared
dummy object as the value. `EnumSet` is the odd one out: no map underneath at
all, just a bit vector, because enum ordinals make direct bit-indexing
possible.

**Why it exists.** Rather than write and maintain three separate hash/tree/
linked-list set implementations, the JDK authors noticed that a `Set<E>` is
exactly a `Map<E, Boolean>` where you only ever look at the keys — so
`HashSet`, `LinkedHashSet`, and `TreeSet` are each a few hundred lines of
delegation over the `Map` they already had.

**When to reach for it, and when not.** `HashSet` is the default: pick it
unless you have a specific reason not to. Pick `LinkedHashSet` the moment a
test, a log, or a UI depends on iteration order matching insertion order.
Pick `TreeSet` the moment you need sorted iteration or range views
(`headSet`, `tailSet`, `subSet`) — and accept O(log n) instead of O(1) for
that. Pick `EnumSet` whenever every element is drawn from one enum type,
full stop — it is faster and smaller than any of the other three by a wide
margin and there is no reason not to use it for that case. Never pick
`TreeSet` with natural ordering if you need to store `null` — it throws
`NullPointerException` on first comparison; `HashSet` and `LinkedHashSet`
each tolerate exactly one `null`.

**How it works.** `[X-REF]` The `Set`-over-`Map` wrapper pattern in full —
the `private static final Object PRESENT = new Object();` sentinel, and how
`HashSet.add(e)` is literally `map.put(e, PRESENT) == null` — lives in
`../sets/01-set-over-map.md`; do not expect the field-by-field walk here.
`[RESEARCH]` `EnumSet` is abstract with two package-private subclasses chosen
by the enum's constant count at factory-method time: `RegularEnumSet`, used
when the enum universe has 64 or fewer constants, packs full set membership
into a single `long` bit vector (bit *i* set means ordinal *i* is present);
`JumboEnumSet`, used above that threshold, uses a `long[]` where element `j`
of the array covers ordinals `64j` through `64j+63`. `[NUM]` A single `long`
has 64 bits, so an enum with exactly 65 constants is the smallest one that
forces `JumboEnumSet` — 64 fits in one `long`, 65 needs a second. `[X-REF]`
The bit-vector arithmetic itself (`elementUnion`, `complement`, iteration via
`Long.numberOfTrailingZeros`) belongs to
`../specialised-maps/01-enum-collections.md` and
`../specialised-maps/02-internals-enum-map-set.md`.

No new diagram — the wrapper relationship is fully carried by the master grid
above; the bit-vector layout has its own diagram in the specialised-maps
files linked above.

```java
Set<String> hash = new HashSet<>();
Set<String> linked = new LinkedHashSet<>();
Set<String> tree = new TreeSet<>();
for (String s : List.of("banana", "apple", "cherry")) {
    hash.add(s); linked.add(s); tree.add(s);
}
System.out.println(hash);    // order unspecified, e.g. [banana, cherry, apple]
System.out.println(linked);  // [banana, apple, cherry] — insertion order
System.out.println(tree);    // [apple, banana, cherry] — sorted order

enum Day { MON, TUE, WED, THU, FRI, SAT, SUN }
EnumSet<Day> weekdays = EnumSet.range(Day.MON, Day.FRI); // RegularEnumSet: 7 <= 64
EnumSet<Day> weekend = EnumSet.complementOf(weekdays);
System.out.println(weekend); // [SAT, SUN]
```

**Pitfall:** assuming `HashSet`'s "no order guarantee" means "insertion
order, informally, until it doesn't." It means unspecified, full stop — the
apparent stability across runs is an artifact of hash-bucket layout for a
given JVM and key set, and it breaks the moment the table resizes or the key
distribution changes. Fix: if any order is relied upon, even loosely, use
`LinkedHashSet` or `TreeSet` explicitly.

**Interview:** "Why is `EnumSet` faster than `HashSet<SomeEnum>`?" — because
it does no hashing, no boxing of a `PRESENT` value, and no bucket traversal at
all; membership and union/intersection are single bitwise operations on
plain `long`s.

> A `Set` family member is a `Map` wearing a `Set` interface — except
> `EnumSet`, which discards the map entirely in favour of a `long` or
> `long[]` bit vector indexed by enum ordinal, because ordinals are already
> the dense integer keys a map would otherwise have to hash.

## Primary concept: concurrent and adapter sets — `CopyOnWriteArraySet`, `ConcurrentSkipListSet`, `newSetFromMap`, `newSequencedSetFromMap`

**Mental model.** These four are not a family by structure — they are a
family by role: each is what you reach for when neither `HashSet` nor
`TreeSet` can be made safe or shaped the way you need, without writing a set
implementation from scratch.

**Why it exists.** `Collections.synchronizedSet` blocks readers during
writes and still throws CME on concurrent iteration; there was no lock-free
concurrent sorted set, no lock-free small listener set, and no way to get a
`Set` view over map implementations — `WeakHashMap`, `IdentityHashMap` — that
never shipped their own `Set` counterpart, because a `Set` is just a subset
of what a `Map` can do.

**When to reach for it, and when not.** `CopyOnWriteArraySet` for the same
narrow case as `CopyOnWriteArrayList` — tiny, read-heavy, write-rare — and
for nothing larger, since `contains`/`add` are both O(n) linear scans over
the backing list (there is no hashing at all). `ConcurrentSkipListSet` when
you need a sorted set under real concurrent read/write contention;
single-threaded code should use `TreeSet` instead, since the skip list pays
extra pointer overhead for concurrency it isn't using. `newSetFromMap` only
when you need a `Set` view over a map that has no purpose-built `Set` sibling
— most commonly `Collections.newSetFromMap(new WeakHashMap<>())` for a
weakly-referenced set, or over an `IdentityHashMap` for reference-equality
membership. `newSequencedSetFromMap` in the same situation, but when the
backing map is also a `SequencedMap` and you want `getFirst`/`getLast`/
`reversed()` on the resulting set.

**How it works.** `[RESEARCH]` `Collections.newSetFromMap(Map<E,Boolean> map)`
requires an empty map, wraps it, and every `add(e)` becomes `map.put(e,
Boolean.TRUE) == null`; the returned object also implements `Serializable`
if the map does. `[RESEARCH]` `Collections.newSequencedSetFromMap
(SequencedMap<E,Boolean> map)` is its Java 21 counterpart, introduced with
JEP 431's Sequenced Collections: it requires an empty `SequencedMap` and
returns a `SequencedSet<E>` delegating `addFirst`/`addLast`/`reversed()` to
the backing map's corresponding sequenced operations. `ConcurrentSkipListSet`
delegates entirely to an internal `ConcurrentSkipListMap`, the same
skip-list structure used there, giving expected O(log n) operations with
lock-free reads and fine-grained write coordination.

No new diagram — the skip-list layout belongs wherever `ConcurrentSkipListMap`
internals are covered in the maps catalogue; this file carries the shape via
the master grid.

```java
Set<Object> weakIdentitySet =
    Collections.newSetFromMap(new WeakHashMap<>());       // GC-eligible keys
weakIdentitySet.add(new Object());                          // may vanish on GC

SequencedMap<String, Boolean> seq = new LinkedHashMap<>();
SequencedSet<String> seqSet = Collections.newSequencedSetFromMap(seq);
seqSet.addFirst("b");
seqSet.addFirst("a");
System.out.println(seqSet);        // [a, b]
System.out.println(seqSet.getLast()); // "b"

Set<Integer> sortedConcurrent = new ConcurrentSkipListSet<>();
sortedConcurrent.add(5);
sortedConcurrent.add(1);
System.out.println(sortedConcurrent); // [1, 5] — sorted, safe under contention
```

**Pitfall:** passing a non-empty map to `newSetFromMap` or
`newSequencedSetFromMap`, expecting the existing entries to become set
members. Both methods throw `IllegalArgumentException` if the map is not
empty at call time — the wrapper does not adopt pre-existing keys, it only
ever writes through it going forward.

> `CopyOnWriteArraySet` and `ConcurrentSkipListSet` are concurrency-shaped
> answers to "I need a thread-safe `Set`"; `newSetFromMap` and
> `newSequencedSetFromMap` are shape-shaped answers to "I need a `Set` view
> over a `Map` implementation that never got its own `Set` class."

## Open questions

None — both research-flagged claims (`EnumSet`'s 64-constant split,
`Collections.newSequencedSetFromMap`'s Java 21 signature and empty-map
precondition) were confirmed against current documentation while writing
this file.

## Pitfalls

### Assuming `ArrayList` and `LinkedList` are interchangeable because both implement `List`

**Wrong**
```java
List<Integer> queue = new ArrayList<>();
for (int i = 0; i < 100_000; i++) {
    queue.add(0, i);          // O(n) shift on every single call
}
```

**Right**
```java
Deque<Integer> queue = new ArrayDeque<>();   // or LinkedList if you need List too
for (int i = 0; i < 100_000; i++) {
    queue.addFirst(i);        // O(1) at the head
}
```

**Why people believe it:** both satisfy the same `List` contract and both
compile identically against `add(0, e)` — the interface hides the O(n) vs
O(1) difference in `ArrayList`'s array-shift completely until a profiler or a
production slowdown surfaces it.

### Assuming `HashSet<MyEnum>` and `EnumSet<MyEnum>` behave identically, just with different performance

**Wrong**
```java
Set<Day> days = new HashSet<>();
days.add(Day.MON);
days.add(null);              // compiles, runs — HashSet tolerates one null
```

**Right**
```java
EnumSet<Day> days = EnumSet.of(Day.MON);
days.add(null);              // throws NullPointerException immediately
```

**Why people believe it:** both are `Set<Day>` and both support the same
`add`/`contains`/`remove` surface, so the null-tolerance difference — a
direct consequence of `EnumSet` indexing by ordinal, and `null` having no
ordinal — is invisible until it throws at runtime.

## Cheat sheet

| Class | O(1) op | O(n) op | Nulls | Thread-safe | Sorted/ordered |
|---|---|---|---|---|---|
| `ArrayList` | get/set/append | insert/remove middle | yes | no | insertion |
| `LinkedList` | add/remove at ends | get(i) | yes | no | insertion |
| `Vector`/`Stack` | same as ArrayList, locked | same as ArrayList, locked | yes | yes (coarse) | insertion |
| `CopyOnWriteArrayList` | reads | every write | yes | yes (lock-free read) | insertion |
| `HashSet` | add/contains/remove | none | 1 | no | none |
| `LinkedHashSet` | add/contains/remove | none | 1 | no | insertion |
| `TreeSet` | none | add/contains/remove: O(log n) | 0 (natural order) | no | sorted |
| `EnumSet` | add/contains/remove/union | none | 0 | no | ordinal |
| `CopyOnWriteArraySet` | reads | add/contains/remove | yes | yes | insertion |
| `ConcurrentSkipListSet` | none | O(log n) all ops | 0 | yes | sorted |
| `newSetFromMap` | delegates to map | delegates to map | delegates to map | delegates to map | delegates to map |
| `newSequencedSetFromMap` | delegates to map | delegates to map | delegates to map | delegates to map | delegates to map's sequence |

## Self-test

**Q1.** Why does `ArrayList` outperform `LinkedList` even for workloads with
frequent inserts, as long as those inserts aren't near the front?

<details><summary>Answer</summary>

`System.arraycopy` moves contiguous memory in one operation with excellent
cache locality; `LinkedList` inserts are O(1) once you're at the right node,
but *getting* to that node means pointer-chasing through scattered heap
objects, which is slower in practice than the array shift for all but the
largest lists or front-heavy access patterns.

</details>

**Q2.** What is wrong with the belief that `Stack`'s iterator returns
elements in pop order?

<details><summary>Answer</summary>

`Stack extends Vector`, and its iterator walks the backing array from index 0
upward — insertion order, bottom to top — while `pop()` removes from the top
(the end of the array). The two orders are opposite; only `pop()` in a loop
gives LIFO order, the iterator does not.

</details>

**Q3.** Why is `CopyOnWriteArrayList` safe to iterate concurrently with
writers, with no `ConcurrentModificationException` possible?

<details><summary>Answer</summary>

Every write allocates a brand-new array, populates it, and swaps the
reference; an iterator created before the write holds a reference to the old
array, which is never mutated after its creation, so the iterator sees a
frozen, internally-consistent snapshot rather than a live, mutating
structure.

</details>

**Q4.** Why does `TreeSet` throw `NullPointerException` on `add(null)` under
natural ordering, but `HashSet` and `LinkedHashSet` accept exactly one null?

<details><summary>Answer</summary>

`TreeSet` must compare the new element against existing elements to place it
in sorted order, and `null.compareTo(x)` (or `x.compareTo(null)`) has no
defined result — natural ordering has no comparison for null. `HashSet`/
`LinkedHashSet` only need `hashCode`/`equals`, and both wrapper `HashMap`/
`LinkedHashMap` implementations special-case a null key into bucket 0.

</details>

**Q5.** What determines whether `EnumSet.noneOf(MyEnum.class)` returns a
`RegularEnumSet` or a `JumboEnumSet`?

<details><summary>Answer</summary>

The number of constants in `MyEnum`: 64 or fewer selects `RegularEnumSet`,
which packs membership into one `long` bit vector; 65 or more selects
`JumboEnumSet`, which uses a `long[]` where each element covers 64 more
ordinals.

</details>

**Q6.** When does `Collections.newSetFromMap` throw, and why?

<details><summary>Answer</summary>

It throws `IllegalArgumentException` if the supplied map is not empty at call
time, because the wrapper only ever writes new entries through to the map
going forward — it does not retroactively adopt existing keys as set members.

</details>

**Q7.** Why does `ConcurrentSkipListSet` cost more per operation than
`TreeSet` in a single-threaded benchmark?

<details><summary>Answer</summary>

`ConcurrentSkipListSet` is backed by a skip list with probabilistic
multi-level pointers sized for lock-free concurrent traversal, which carries
extra pointer-following and node overhead compared to `TreeSet`'s red-black
tree — overhead that only pays for itself under real concurrent contention.

</details>

**Q8.** Why is `CopyOnWriteArraySet.contains` O(n) instead of O(1)?

<details><summary>Answer</summary>

It is backed by `CopyOnWriteArrayList`, a plain array with no hash index, so
membership testing is a linear scan; the class trades lookup speed for
lock-free, always-consistent concurrent iteration, which only makes sense for
small collections.

</details>

---

**Leaves covered:** 1.4.1–1.4.13 (13 leaves)
**Leaves deferred:** none
**Diagrams included:** D-03 (re-embedded canonical hierarchy)
**Target version:** Java 21 LTS
**Lines:**      513
