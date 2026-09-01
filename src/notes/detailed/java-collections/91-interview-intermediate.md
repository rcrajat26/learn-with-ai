# 02 Java Collections — Interview, INTERMEDIATE tier — summary and questions 1–18 (§5.1)

**Target version: Java 21 LTS.** | [Index](00-index.md)
Previous: [90c-interview-basics-c-puzzles.md](90c-interview-basics-c-puzzles.md) · Next: [91b-interview-intermediate-b-questions-19-36.md](91b-interview-intermediate-b-questions-19-36.md)

The INTERMEDIATE tier is where the questions stop being "what is it" and become "what does it
cost, and what loses". This file carries the tier summary table across all **18 subject folders**
and questions 1–18 of 36. Questions 19–36 are in
[91b](91b-interview-intermediate-b-questions-19-36.md); the five puzzles are in
[91c](91c-interview-intermediate-c-puzzles.md).

## Tier summary table — the tradeoff per subject

| Subject | The decision you are being asked to make | The cost that decides it | What the answer is not |
|---|---|---|---|
| The framework itself | which interface to accept and return | none at runtime — it is an API-evolution cost | not "the concrete class I happen to use" |
| Ordering contracts | natural order or an external `Comparator` | a comparator inconsistent with `equals` splits `contains` from `equals` | not interchangeable: `TreeMap` never calls `equals` |
| Iteration | mutate through the iterator, snapshot, or concurrent collection | `Iterator.remove` is O(1)…O(n) depending on the structure | not "wrap it in try/catch" |
| Sequenced collections (21) | is `reversed()` enough, or do you need a copy | O(1) view versus O(n) snapshot | not a copy, and `addFirst` on the view writes to the source's tail |
| Cost and memory | amortised, average, or worst case — which one does your SLA care about | amortised O(1) still contains one O(n) copy | not "O(1) means fast every time" |
| `ArrayList` | pre-size or let it grow | ~3n reference copies over n appends at 1.5× | not 2× growth, and it never shrinks |
| `LinkedList` | do you hold a cursor | O(n) to reach the index kills the O(1) splice | not "better for insertions" |
| `ArrayDeque` | deque, or a blocking queue | no backpressure — it grows until OOM | not thread-safe, and not null-tolerant |
| `PriorityQueue` | full sort, heap, or bounded top-k | O(n log n) versus O(n log k) with O(k) memory | not stable, and not sorted when iterated |
| `HashMap` | default map, or do you need order/concurrency | O(1) expected, O(log n) per treeified bin **with `Comparable` keys**, and a resize is O(capacity) | not ordered, and not shrinkable |
| `LinkedHashMap` | insertion order, access order, or a real cache | access order makes every `get` a write | not thread-safe under `get`, even with a read lock |
| `TreeMap` | do you need ranges and neighbours, or just lookup | O(log n) with a large constant: pointer chase plus virtual compare | not a drop-in `HashMap` — `compare == 0` is identity |
| Sets | is your argument a `Set` or a `List` | `removeAll` costs receiver-size × argument-`contains` | not symmetric: `a.removeAll(b)` and `b.removeAll(a)` differ in cost |
| Specialised maps and sets | is the key an enum, an identity, or a lifetime | `EnumMap` is `4n` bytes for the whole universe, eagerly | `WeakHashMap` is not a cache; `Hashtable` capacities are not prime |
| Immutability and views | view, copy, or snapshot at the API boundary | `copyOf` is O(n) and two arrays; a view is O(1) and live | not deep, ever |
| Concurrent collections | lock, copy-on-write, or a concurrent collection | copy-on-write is O(n) per write; the crossover is a write ratio near `c/n` | a synchronized wrapper is not a concurrent collection |
| Utility surfaces | `Collections` helper, stream, or hand-rolled loop | a stream costs allocation and boxing you can measure | `binarySearch` on unsorted input is not an error, it is a wrong answer |
| Build it | use the JDK class, a library, or write one | writing one costs correctness risk; a library costs dependency surface | not "the JDK does not have it" until you have checked Guava |

## Q&A 1–18

### Q1. "What is `ArrayList`'s growth factor, and why not 2×?" (§5.1.13)

**Model answer.** 1.5×, computed as `oldCapacity + (oldCapacity >> 1)` — a shift and an add, no
floating point. From the default capacity of 10 the ladder is 10, 15, 22, 33, 49, 73, 109, 163.

The reason it is not 2× is memory behaviour, not speed. With any growth factor `g`, the total
copying over n appends is about `n·g/(g−1)`, so 1.5× copies about 3n references and 2× copies about
2n. So 2× copies **less**. What 1.5× buys is reuse: freed blocks can satisfy a later request only
when `g` is below the golden ratio, φ ≈ 1.618. At 2×, the sum of all previously freed blocks is
always just short of the next request, so the allocator can never reuse them and the heap ratchets
upward. At 1.5× it can. The peak live memory during the copy is also lower — `(1+g)·c`, so 2.5× the
old capacity instead of 3×.

**If they push:** the potential-function proof does not survive the change of factor. The classic
`Φ = 2·size − capacity` is the *doubling* potential and fails at 1.5×; the general form is
`Φ_g = (g/(g−1))·size − (1/(g−1))·capacity`, which gives `3·size − 2·capacity` and an amortised
cost of 4 rather than 3. Other runtimes chose differently: CPython grows at about 1.125×, Go
doubles below 256 elements and then adds a quarter.

**One-line close:** 1.5× via a shift, chosen for allocator reuse below φ rather than for fewer
copies — 2× is `Vector`.

### Q2. "`TreeMap` vs `HashMap` — and when do you actually need `TreeMap`?" (§5.1.26)

**Model answer.** `HashMap` is an array indexed by a hash: O(1) expected lookup, no order.
`TreeMap` is a red-black tree ordered by a comparator: O(log n) lookup, total order maintained at
all times. On raw lookup `HashMap` wins and it is not close — one array index against a walk of
`log₂ n` pointer chases, each with a virtual comparison.

You need `TreeMap` when you need the *order*, and specifically when you need one of the things a
sorted structure gives you for free:

- **neighbour queries** — `floorKey`, `ceilingKey`, `lowerKey`, `higherKey`. This is the real answer,
  and "as-of" time-series lookup is the canonical case: `floorEntry(timestamp)` gives you the last
  value at or before that instant.
- **range views** — `subMap`, `headMap`, `tailMap`, live and O(1) to create, O(log n) to enter.
- **sorted iteration** without a sort at the end.
- **first/last plus poll** — `pollFirstEntry` in one descent, which is a priority queue with keyed
  updates.

The costs to name: 40 bytes per entry against `HashMap`'s 32, no null keys under natural ordering,
and every operation pays the comparator.

**One-line close:** `HashMap` unless you need neighbours, ranges or sorted iteration — and if you do,
nothing else in `java.util` gives them to you.

### Q3. "How does `TreeMap` decide two keys are the same?" (§5.1.27)

**Model answer.** `compare(k1, k2) == 0`, and nothing else. `equals` and `hashCode` are never
consulted — not for ordering, not for lookup, not for duplicate detection. That is the single most
consequential difference from `HashMap`, and it is easy to state and easy to forget.

The routing is decided once, at construction: if you passed a `Comparator`, every comparison goes
through it; otherwise the key is cast to `Comparable` and `compareTo` runs. The JDK even keeps two
near-identical search loops — `getEntry` and `getEntryUsingComparator` — so that each call site is
monomorphic for the JIT.

The consequence is that a comparator inconsistent with `equals` gives you a map where
`containsKey` and `Map.equals` disagree: `containsKey` is comparator-based, while `Map.equals`
inherited from `AbstractMap` is `equals`-based. `BigDecimal` is the standard example —
`new BigDecimal("2.0").compareTo(new BigDecimal("2.00")) == 0` but they are not `equals`, so a
`TreeSet` holds one of them and a `HashSet` holds both.

**If they push:** this is also why a case-insensitive `TreeMap` built with
`String.CASE_INSENSITIVE_ORDER` treats `"Key"` and `"KEY"` as the same key while a `HashMap` would
not — usually the behaviour you wanted, achieved by a mechanism people do not expect.

**One-line close:** `compare == 0` is key identity, so the comparator, not `equals`, defines what a
duplicate is.

### Q4. "How would you implement an LRU cache?" — and "without `LinkedHashMap`?" (§5.1.17)

**Model answer.** With `LinkedHashMap` it is about ten lines: construct it in **access order** and
override the eviction hook.

```java
public final class LruCache<K, V> extends LinkedHashMap<K, V> {
    private static final long serialVersionUID = 1L;
    private final int maxEntries;

    public LruCache(int maxEntries) {
        super((int) (maxEntries / 0.75f) + 1, 0.75f, true);   // true = access order
        this.maxEntries = maxEntries;
    }

    @Override
    protected boolean removeEldestEntry(Map.Entry<K, V> eldest) {
        return size() > maxEntries;
    }
}
```

Access order means a successful `get` relinks the entry to the tail, so the head is always the least
recently used. `removeEldestEntry` is called after every *new-key* insertion, and returning `true`
evicts the head.

Without it, you build the same two structures by hand: a `HashMap<K, Node>` for O(1) lookup plus a
doubly-linked list for O(1) recency. The design decisions worth saying out loud:

- the map's value is the **node**, never the value — otherwise you cannot unlink in O(1);
- use **sentinel** head and tail nodes, which turns `unlink` from four branches into two writes;
- eviction must remove from **both** structures in one method, always together. Forgetting the map
  removal is the classic bug: `size()` drifts above the bound and then eviction stops entirely, and
  a `get` on an evicted key returns a value *and* relinks a dead node.

The cost of hand-rolling, measured in this set: 64 bytes per entry against `LinkedHashMap`'s 40,
plus code you now own.

**If they push:** three things the `LinkedHashMap` version gets wrong that people miss. It is not
thread-safe, and in access order a `get` is a *write*, so a `ReadWriteLock` does not help — readers
need the write lock. An over-bound map does not drain: each `put` adds one and evicts at most one,
so a map filled to 10 with a bound of 3 stays at 10. And an LRU built by the copy constructor
exceeds its own bound, because `putMapEntries` passes `evict = false`.

**One-line close:** access-order `LinkedHashMap` plus `removeEldestEntry`, or `HashMap<K,Node>` plus
a sentinel-terminated doubly-linked list by hand — and in production, Caffeine.

### Q5. "Why does `Collections.sort` throw 'Comparison method violates its general contract'?" (§5.1.24)

**Model answer.** Because TimSort checked, and your comparator is inconsistent. TimSort is a
merge sort over detected runs, and it maintains invariants on a stack of run lengths. If the
comparator is not a total order, the merge can walk off the end of a run, and rather than corrupt
the array the implementation throws `IllegalArgumentException` with that message.

The four usual causes, in order of frequency:

1. **`int` subtraction** — `a.getSize() - b.getSize()` overflows for large or negative values and
   the sign flips. Use `Integer.compare`.
2. **Non-transitivity** — a hand-written comparator with special cases, typically "nulls or
   defaults sort first" bolted onto a comparison that also returns 0 for them.
3. **Mutation during the sort** — another thread, or your own `compare`, changing a field the
   comparison reads.
4. **An unguarded null field** dereferenced only on some paths, which makes the comparison
   inconsistent rather than throwing.

The important framing: the exception is a **symptom of your bug, reported late**. It is
data-dependent, so it appears in production on a large list and not in your unit test, and the
stack trace points at `TimSort.mergeHi`, not at your comparator.

**If they push:** the flag `-Djava.util.Arrays.useLegacyMergeSort=true` restores the pre-Java-7
merge sort and makes the exception go away. It does not fix anything — you now have a silently
wrongly-ordered list. And there is a genuine JDK-side subtlety: the de Gouw proof
(JDK-8072909) showed `mergeCollapse`'s three-entry invariant check is insufficient, and the JDK's
fix was to **enlarge the run-length stack bound** rather than correct the merge logic.

**One-line close:** TimSort detected that your comparator is not a total order — almost always
`a - b` overflow — and the fix is `Integer.compare`, never the legacy flag.

### Q6. "Which sort does Java use, and why two different ones?" (§5.1.25)

**Model answer.** Two algorithms, chosen by whether the elements have identity.

**Objects** get **TimSort**: an adaptive, stable merge sort. `MIN_MERGE` is 32, so short arrays are
just binary insertion sort; longer ones detect natural ascending or descending runs and merge them
under stack invariants. Best case O(n) on already-sorted or reverse-sorted input, worst case
O(n log n), O(n/2) extra space.

**Primitives** get **dual-pivot quicksort**: in place, not stable, O(n log n) average with an
O(n²) worst case that is mitigated by falling back to heapsort past a recursion-depth cap. Small
ranges (below roughly 44 elements) use insertion sort; `byte`/`char`/`short` above a threshold use
counting sort.

The reason for the split is the reason to remember it. Stability only means something when two
"equal" elements are distinguishable — for an `int`, 5 is 5, so there is nothing to preserve. And
for objects a comparison is an expensive virtual call, so TimSort's strategy of *minimising
comparisons* pays; for primitives a comparison is nearly free, so quicksort's strategy of
minimising memory passes pays instead. Object sorting also cannot be done in place cheaply, because
you need the extra array anyway.

**If they push:** `Collections.sort(list)` since Java 8 is just `list.sort(null)`, and the default
`List.sort` copies to an array, sorts, and writes back through a `ListIterator`. `ArrayList`
overrides it to sort `elementData` in place — but it still bumps `modCount`, so any held iterator is
poisoned. `Arrays.parallelSort` falls back to sequential below 8,192 elements.

**One-line close:** stable TimSort for objects because comparisons are expensive and identity
matters, unstable dual-pivot quicksort for primitives because neither is true.

### Q7. "When is `CopyOnWriteArrayList` the right choice?" (§5.1.22)

**Model answer.** When reads vastly outnumber writes and the read path must never lock. The
canonical case is a listener or observer registry: registered once at startup, iterated on every
event.

The mechanism explains the constraint. The backing store is a `volatile Object[]`; a read is a
volatile array read with no lock at all, and every write copies the **whole** array under a monitor
and publishes the new one. So a write is O(n) with no growth factor and no slack —
`add` copies exactly `len + 1`. Building a list of 10,000 elements one `add` at a time copies about
50 million references.

The crossover is worth stating as arithmetic: it pays when the write ratio is below roughly `c/n`
for a small constant `c`, so about 1% of operations at n = 100, and about 0.0001% at a million. In
other words the tolerable write rate falls linearly as the collection grows.

What you get in exchange, beyond lock-free reads: a **snapshot iterator**. It holds a private
frozen array, so it never throws `ConcurrentModificationException` and a listener can deregister
itself during dispatch without breaking the loop. The corollary is that `iterator.remove()` throws
`UnsupportedOperationException` — always, on every path.

**If they push:** the lock is a plain `Object` monitor in JDK 11 and later. It was a `ReentrantLock`
in Java 8, so any write-up describing `final transient ReentrantLock lock` is describing the old
code. And `CopyOnWriteArraySet` is a thin wrapper over the list, so its `add` and `contains` are
both O(n) — it is not a hash set.

**One-line close:** read-mostly, small, and you need iteration that cannot throw — listener lists,
essentially; anything write-heavy wants `ConcurrentHashMap.newKeySet()` or a lock.

### Q8. "What is a view, and name three in `java.util`?"

**Model answer.** A view is an object with no storage of its own that presents another
collection's state through a different interface or window. Two properties define it: creating one
is O(1) with no element copying, and everything you see through it is live.

Three, with what each is a window onto:

- `list.subList(a, b)` — an index window. Its fields are just `root`, `offset` and `size`, so a
  32-byte object can pin a 4 MB array alive, and a structural change to the parent poisons it with
  a `ConcurrentModificationException` on next use.
- `map.keySet()`/`values()`/`entrySet()` — the three doors from `Map` into the `Collection` world.
  Cached, so the same instance comes back every call; `remove` through them deletes mappings.
- `treeMap.subMap(a, b)` and `descendingMap()`, and Java 21's `reversed()` — order and range
  windows. Writes through them land in the source.

And `Collections.unmodifiableList(x)` is the view whose *purpose* is confused most often: it makes
the collection read-only through **your** reference while leaving it fully mutable through the
owner's.

**If they push:** the two hazards of views are retention and staleness. A `subList` you keep holds
the whole parent array; the fix is `List.copyOf(sub)`. And a `TreeMap` range view throws only on an
out-of-range **write** — an out-of-range `get` or `remove` is a silent no-op, so
`headMap(30).remove(99)` returns `null` and leaves key 99 alive in the source.

**One-line close:** O(1) to create, live to read, and dangerous to keep — a view is a window, not a
copy.

### Q9. "What exactly counts as a structural modification?"

**Model answer.** Anything that changes the size of the collection, plus a couple of cases that do
not look like it. The definition matters because it is exactly what bumps `modCount` and therefore
what a held iterator will notice.

| Operation | Structural? |
|---|---|
| `add`, `remove`, `clear`, `addAll`, `removeIf`, `retainAll` | yes |
| `list.set(i, v)` | **no** |
| `map.put(existingKey, v)` — value overwrite | **no** |
| `entry.setValue(v)` | **no** |
| `list.sort(...)`, `list.replaceAll(...)` | **yes** — both bump `modCount` |
| `ArrayList.ensureCapacity`, `trimToSize` | yes, `modCount` is bumped even with no size change |
| `LinkedHashMap.get` in **access order** | **yes** — six pointer writes and `++modCount` |
| `HashMap.get` | no |

The two entries that decide interview answers are the last pair and `sort`. A `get` on an
access-order `LinkedHashMap` is a structural modification, so a `get` inside an iteration over that
same map throws CME, and two concurrent readers are two concurrent writers. And a `sort` in the
middle of a loop poisons the iterator you were holding.

**If they push:** for a `subList`, the check is against the **root**'s `modCount`, not the immediate
parent's — so mutating a grandparent invalidates a nested sublist. And `WeakHashMap` is stranger
still: `size()` can shrink between two adjacent calls without anyone modifying anything, because
expunging cleared keys happens inside ordinary reads.

**One-line close:** size changes, plus `sort`/`replaceAll`, plus an access-order `get` — and `set`
and `setValue` are the safe ones.

### Q10. "You are designing an API. What collection types do you accept and return?"

**Model answer.** Accept the widest interface that the method actually uses, and return the
narrowest thing that states your guarantee.

For parameters: `Collection<E>` if you only iterate, `List<E>` if order matters, `Set<E>` if you
rely on uniqueness, `Iterable<E>` if you truly only need a for-each. Never a concrete class —
`ArrayList` in a signature bans the caller from passing `List.of(...)` for no benefit. Use
`? extends E` when you only read from it, which is the PECS rule and is exactly why
`Collection.addAll` takes `Collection<? extends E>`.

For returns: never `null` — return `List.of()` or `Collections.emptyList()`, because every caller
otherwise needs a null check that someone will forget. If the collection is internal state, return
`List.copyOf(field)` rather than `Collections.unmodifiableList(field)`: the wrapper is O(1) but
stays live, so the caller can observe your mutations mid-iteration and get a CME in *their* code.
Return the field directly only when its type is already immutable.

And do the defensive copy in the **constructor**, not in the getter. One copy at construction
beats one copy per call, and it makes the object's invariant true from birth.

**One-line close:** accept the widest interface, return an immutable snapshot, never return `null`,
and copy at construction rather than on every read.

### Q11. "Amortised, average, worst case — state the difference precisely."

**Model answer.** They quantify over different things, and mixing them up is how latency SLAs get
missed.

- **Worst case** — the maximum over all inputs for a *single* operation. `ArrayList.add` is O(n)
  worst case, because one of them copies the whole array.
- **Amortised** — the average over a *sequence* of operations, guaranteed against an adversary. It
  is not probabilistic: `ArrayList.add` is amortised O(1) because any n appends cost O(n) total,
  full stop, and no input can make it worse.
- **Average case** — the expectation over a *distribution of inputs*. `HashMap.get` is O(1) average
  because keys are assumed to spread. An adversary who controls the keys breaks it, which is exactly
  the hash-collision attack.

So the two O(1)s in the cost table mean different things: `ArrayList.add`'s is adversary-proof and
`HashMap.get`'s is not.

The practical consequence to volunteer: **amortised O(1) does not mean predictable latency**. In a
latency-sensitive service, an `ArrayList` that grows to a million elements does one 4 MB copy at
some unlucky request, and a `HashMap` resize rehashes the whole table. Pre-size both, and if you
cannot, know that the tail latency is not the average.

**One-line close:** worst case is one operation, amortised is a sequence with no distribution
assumed, average assumes a distribution — and only amortised survives an adversary.

### Q12. "What did the sequenced interfaces change for `LinkedHashMap` and `TreeMap`?"

**Model answer.** JEP 431 in Java 21 added three interfaces —`SequencedCollection`,
`SequencedSet`, `SequencedMap` — and retrofitted them onto the classes that already had an
encounter order. `List` and `Deque` became `SequencedCollection`s, `LinkedHashSet` and `SortedSet`
became `SequencedSet`s, `LinkedHashMap` and `SortedMap` became `SequencedMap`s.

What changed in practice is that first/last operations and reversal became uniform, and the same
method now behaves differently depending on whether the order is *maintained by you* or *derived
from a comparator*:

| Operation | `LinkedHashMap` | `TreeMap` |
|---|---|---|
| `putFirst`/`putLast` | moves the key, O(1) splice | `UnsupportedOperationException` |
| `firstEntry`/`lastEntry` | O(1) | O(log n) |
| `pollFirstEntry`/`pollLastEntry` | O(1) | O(log n) |
| `reversed()` | live view, `reversed().reversed() == this` | live view, and it *is* `descendingMap()` |

`TreeMap.putFirst` has to throw, because the position of a key is not yours to choose.

**If they push:** two details. `LinkedHashMap` does not override `firstEntry`/`lastEntry` — they come
from `SequencedMap`'s interface defaults, which are written in terms of `entrySet()` and
`reversed()`. So `firstEntry()` returns an unmodifiable snapshot holder whose `setValue` throws,
and `lastEntry()` routes through `reversed()` and allocates a view plus an entry-set view plus an
iterator on every call — the two are asymmetric in allocations even though both are O(1). And on an
access-order map, `putFirst` moves a key to the **eviction** end, so "keep hot keys at the front" is
an anti-optimisation.

**One-line close:** a uniform first/last/`reversed()` tier, where the write methods throw on
comparator-ordered maps because position is not the caller's to set.

### Q13. "How do you compute set intersection and difference, and what is the trap?"

**Model answer.** The bulk operations *are* set algebra: `addAll` is union, `removeAll` is
difference, `retainAll` is intersection, `containsAll` is the subset test. All of them mutate the
receiver, except `containsAll`.

The trap is the cost, and it is entirely about the **argument**. `a.removeAll(b)` iterates `a` and
calls `b.contains(...)` per element, so the cost is `size(a) × contains(b)`. If `b` is a `List`,
`contains` is O(n) and the whole call is O(n·m) — the classic pathological line that looks
innocent in review. The fix is unconditional: wrap the argument in a `HashSet` first.
`new HashSet<>(b)` costs O(m) once and turns the whole thing into O(n).

There is a subtlety on the `Set` side worth knowing: `AbstractSet.removeAll` branches on
`size() > c.size()` and iterates whichever side is smaller. That only helps when the *other* side
has O(1) `contains`, so it does not rescue you from a `List` argument.

**If they push:** two more. `map.keySet().retainAll(keep)` is a live view, so it deletes entries from
the map — usually what you wanted, occasionally a surprise. And symmetric difference and multisets
are simply absent from `java.util`: build `(a∪b)∖(a∩b)` by hand, or use Guava's
`Sets.symmetricDifference` and `Multiset`.

**One-line close:** the bulk methods are set algebra, and the cost is receiver size times the
argument's `contains` — so wrap the argument in a `HashSet`, always.

### Q14. "`ArrayDeque` or `ArrayBlockingQueue` between a producer and a consumer?"

**Model answer.** `ArrayBlockingQueue`, and the reason is backpressure rather than thread safety.
`ArrayDeque` is not thread-safe at all, but even a synchronized wrapper around it would be the wrong
answer, because it is **unbounded**: a producer faster than its consumer grows the array until the
heap is gone. That is the failure mode where the queue itself is the leak.

`ArrayBlockingQueue` is fixed-capacity at construction. `put` blocks when full, `take` blocks when
empty, and the bound is the flow-control mechanism: a slow consumer throttles the producer instead
of consuming memory. Internally it is one `ReentrantLock` and two `Condition`s, `notEmpty` and
`notFull`.

The `BlockingQueue` surface is a 4×3 matrix worth reciting: for insert, remove and examine, each
operation comes in throwing, special-value, blocking and timed forms — `add`/`offer`/`put`/
`offer(e, timeout)`, and `remove`/`poll`/`take`/`poll(timeout)`. Examine is the incomplete row:
`element` and `peek` only, no blocking form.

**If they push:** `LinkedBlockingQueue` defaults to `Integer.MAX_VALUE` capacity if you do not pass
one, which is the same unbounded trap wearing a bounded-looking name. It uses two locks —
`putLock` and `takeLock` — so producers and consumers do not contend, and its `size()` is lock-free
via an `AtomicInteger`, where `ArrayBlockingQueue.size()` takes the lock.

**One-line close:** a bounded `ArrayBlockingQueue`, because the point is backpressure — and check
whether you accidentally constructed an unbounded `LinkedBlockingQueue`.

### Q15. "How do you make a `PriorityQueue` stable?"

**Model answer. `PriorityQueue` is not stable and cannot be made stable by changing the queue —
you change the elements.** The instability is mechanical: `siftUp` stops on `>= 0` and `siftDown`
stops on `<= 0`, so an equal comparison stops the move, and equal-priority elements come out in an
order determined by array positions. Measured in this set: seven equal-priority items inserted `a`
through `g` drain as `agfedcb`.

The fix is to make equality impossible by adding a tiebreak the queue can see. Wrap each element
with a monotonically increasing sequence number and compare on it second:

```java
Comparator<Stamped<E>> stable =
        Comparator.<Stamped<E>, E>comparing(Stamped::value, byPriority)
                  .thenComparingLong(Stamped::seq);
```

Three details that matter. Use `thenComparingLong`, not `thenComparing` — the boxing form allocates
a `Long` per comparison, and there are about `2·log₂ n` comparisons per `poll`. Use a `long`
counter: an `int` inverts the order within each priority after 2³¹ insertions. And make the wrapper
private, so the elements you hand back are the caller's own objects.

**If they push:** the related trap is mutating an element's priority in place. The heap does not
re-sift, so `peek()` can return a non-minimum — measured: `{1, 5, 9}` with the 1 mutated to 99
drains as `99 5 9`. The three fixes are remove-mutate-reinsert (O(n) because `indexOf` is a linear
scan), immutable entries plus tombstones and lazy deletion (which is how Dijkstra is actually
written), or an indexed heap you maintain yourself.

**One-line close:** add a `long` sequence number as a secondary key — the queue cannot be made
stable, but the comparator can make ties impossible.

### Q16. "Does `Hashtable` use prime capacities for better distribution?"

**Model answer.** No — that is folklore, and the arithmetic is a satisfying way to show it.
`Hashtable` starts at capacity 11 and grows by `(oldCapacity << 1) + 1`, giving 11, 23, 47, 95,
191, 383, 767, 1535, 3071, 6143 and 12287. That rule produces **odd** numbers, not primes,
and the class never tests for primality. Exactly **6 of the first 15** capacities are prime — 11,
23, 47, 191, 383 and 6,143, which is the last one; after that they all factor. 95 = 5×19,
767 = 13×59, 3071 = 37×83, 12287 = 11×1117.

The 12287 = 11×1117 case is the good illustration of why anyone cared: keys congruent modulo 11
alias into the same buckets in a way a power-of-two mask would not reproduce. So the *intent* of a
prime modulus is real; `Hashtable`'s implementation of it stops working after the first few growths.

`HashMap` took the other road deliberately: a power-of-two capacity so the index is
`hash & (n − 1)`, one AND instead of an integer division. The price is that a mask throws away the
high bits, which is exactly why `HashMap` must spread first with `h ^ (h >>> 16)`. Measured in this
set, mask versus modulo is about 1.96× per element — but the real argument is the resize: with a
power-of-two table, moving an entry is one bit test, `(hash & oldCap) == 0`, while modulo indexing
gives a destination unrelated to the source and needs a division per entry.

**One-line close:** it grows `2n + 1`, which is odd rather than prime, and only 6 of the first 15
capacities are actually prime — `HashMap` chose masking plus a spread instead.

### Q17. "What does `Collections.binarySearch` return when the key is missing?"

**Model answer.** A negative number that encodes the insertion point: `-(insertion point) - 1`.
So a return of `-3` means the key is not present and belongs at index 2. The encoding exists because
0 is a valid index, so a plain `-1` could not distinguish "not found" from anything useful; and the
decode is `int insertAt = -result - 1`, which is the idiom for "find or insert".

The silent-wrong case is the important half of the answer: **`binarySearch` on an unsorted list
does not throw.** It returns a wrong index, or a negative number whose insertion point is
meaningless, and nothing tells you. Same for a list sorted by a *different* comparator from the one
you pass. That is a correctness bug that survives testing whenever your test data happens to be
sorted.

**If they push:** it is also cost-sensitive to the list type. For a non-`RandomAccess` list the
implementation switches to an iterator-based binary search above `BINARYSEARCH_THRESHOLD = 5000`
elements, because indexed access on a `LinkedList` would make each probe O(n). The `Collections`
class is full of those thresholds — `REVERSE_THRESHOLD = 18`, `SHUFFLE_THRESHOLD = 5`,
`ROTATE_THRESHOLD = 100` — all doing the same thing: branch on `instanceof RandomAccess` and pick an
algorithm.

**One-line close:** `-(insertionPoint) - 1`, decoded as `-r - 1` — and on unsorted input it is
silently wrong rather than an error.

### Q18. "You need a cache with a TTL and a size bound. What do you use?"

**Model answer.** Caffeine. That is the honest answer, and being able to say *why* the JDK
options fail is the interesting part.

`LinkedHashMap` in access order gives you an exact LRU with a size bound and nothing else: no TTL,
no weighting, no eviction listener, no concurrency. It is also **scan-vulnerable** — measured in
this set, one pass over 1,000 keys took a 100-entry cache from a 100% hit rate to 0%, because a
scan evicts the entire hot set. And it cannot be made concurrent cheaply, because access order makes
`get` a write.

`WeakHashMap` is not a cache at all, and this is the more common mistake. Its keys are weak, so
entries vanish when the *key* becomes unreachable — which is a lifetime-tracking mechanism, not an
eviction policy. There is no size bound, no TTL, and the timing is the garbage collector's. Worse,
if a value holds a reference to its own key, the entry is immortal; and `String` literals and small
boxed `Integer`s are interned, so those keys never clear at all.

Caffeine gives you size and time bounds, an eviction listener, async loading, and a W-TinyLFU
policy — an admission filter over a 4-bit count-min sketch, roughly 8 bytes per entry — that is not
scan-vulnerable. Its reads go to striped per-thread ring buffers replayed asynchronously, so
readers do not serialise on one lock the way an access-order `LinkedHashMap` does.

**One-line close:** Caffeine — `LinkedHashMap` is an unsynchronised scan-vulnerable LRU with no TTL,
and `WeakHashMap` tracks key lifetime rather than caching anything.

## Pitfalls

### Sizing a `HashMap` with `new HashMap<>(n)`

**Wrong**

```java
Map<String, String> m = new HashMap<>(1000);   // "room for 1000"
```

It has room for 750. The argument is a *capacity*, and the map resizes when `size` exceeds
`capacity × 0.75`.

**Right**

```java
Map<String, String> m = HashMap.newHashMap(1000);          // Java 19+
Map<String, String> pre19 = new HashMap<>((int) (1000 / 0.75f) + 1);
```

**Why people believe it:** every other collection's constructor argument means "how much I intend to
put in" — `new ArrayList<>(1000)` really does hold 1000. `HashMap` is the one where the argument is
about the table, not the contents, which is why Java 19 added the four `newXxx` factories that take
the count you actually mean.

### Using `Collections.synchronizedMap` and thinking the compound action is safe

**Wrong**

```java
Map<String, Integer> counts = Collections.synchronizedMap(new HashMap<>());
Integer current = counts.get(key);          // lock acquired and released
counts.put(key, current == null ? 1 : current + 1);   // and again — race in between
```

**Right**

```java
Map<String, Integer> counts = new ConcurrentHashMap<>();
counts.merge(key, 1, Integer::sum);        // one atomic operation
```

**Why people believe it:** the wrapper genuinely makes every individual call atomic, so each line
looks safe in isolation. The gap between the two calls is invisible in the source. Note that
`synchronizedMap`'s own `merge`/`computeIfAbsent` *are* single `synchronized` blocks and so are
atomic — the problem is only the compound action you write yourself.

## Cheat sheet

| Question | The one-line answer |
|---|---|
| `ArrayList` growth | 1.5×, `old + (old >> 1)`; chosen for allocator reuse below φ ≈ 1.618 |
| Total copies over n appends | ≈ `n·g/(g−1)` — 3n at 1.5×, 2n at 2× |
| Amortised charge at 1.5× | 4 credits (3 at 2×); `Φ_g = (g/(g−1))s − (1/(g−1))c` |
| `TreeMap` over `HashMap` when | neighbours (`floor`/`ceiling`), ranges, sorted iteration, poll-first |
| `TreeMap` key identity | `compare(...) == 0`, never `equals` |
| Comparator inconsistent with `equals` | `containsKey` and `Map.equals` disagree (`BigDecimal`) |
| LRU in ten lines | `LinkedHashMap(cap, 0.75f, true)` + `removeEldestEntry: size() > max` |
| LRU by hand | `HashMap<K,Node>` + sentinel-terminated doubly-linked list; map's value is the **node** |
| Over-bound LRU | does not drain — one in, one out |
| LRU built by copy constructor | exceeds its bound (`evict == false`) |
| "Comparison method violates its general contract" | your comparator is not a total order, usually `a - b` overflow |
| Legacy sort flag | `-Djava.util.Arrays.useLegacyMergeSort=true` — hides the bug, does not fix it |
| Object sort | TimSort, stable, `MIN_MERGE = 32`, O(n) best, O(n/2) space |
| Primitive sort | dual-pivot quicksort, in place, unstable, heapsort fallback past a depth cap |
| `parallelSort` cutover | 8192 elements |
| `CopyOnWriteArrayList` write | one full array copy per mutation, O(n), exactly `len + 1` |
| Copy-on-write crossover | write ratio below ≈ `c/n` — ~1% at n=100, ~0.0001% at n=10⁶ |
| `COWIterator` | snapshot; never CMEs; `remove`/`set`/`add` always throw |
| CoW lock | plain `Object` monitor since JDK 11; `ReentrantLock` in Java 8 |
| Views to name | `subList`, the three `Map` views, `subMap`/`descendingMap`/`reversed()` |
| Range-view write out of bounds | `IllegalArgumentException`; **read and remove are silent no-ops** |
| Structural modification | size change, plus `sort`/`replaceAll`, plus an access-order `get` |
| Not structural | `set(i,v)`, `put` on an existing key, `entry.setValue` |
| API signature rule | accept the widest interface, return `List.copyOf`, never return `null` |
| Amortised vs average | sequence with no distribution (adversary-proof) vs a distribution (attackable) |
| `TreeMap.putFirst` | throws — position is the comparator's, not yours |
| `LinkedHashMap.firstEntry` | interface default; returns an unmodifiable holder; `lastEntry` allocates more |
| `removeAll` cost | receiver size × argument `contains` — wrap the argument in a `HashSet` |
| Absent from `java.util` | symmetric difference, multiset, multimap, bimap |
| Producer/consumer queue | `ArrayBlockingQueue` for backpressure; `LinkedBlockingQueue` is unbounded by default |
| `BlockingQueue` matrix | insert/remove/examine × throw/special-value/block/timed; examine has no blocking form |
| `PriorityQueue` stability | none; add a `long` sequence number and `thenComparingLong` |
| Mutating a priority in place | never re-sifts; `peek()` can return a non-minimum |
| `Hashtable` capacities | 11, 23, 47, 95, …; only 6 of the first 15 are prime, last is 6,143 |
| `HashMap` index | `hash & (n − 1)`, which is why `h ^ (h >>> 16)` is mandatory |
| `binarySearch` miss | `-(insertionPoint) - 1`; unsorted input is silently wrong |
| `Collections` thresholds | binarySearch 5000, reverse 18, shuffle 5, fill 25, rotate 100, copy 10 |
| Cache with TTL | Caffeine; `LinkedHashMap` is scan-vulnerable, `WeakHashMap` is not a cache |

## Self-test

**Q1.** Why is 1.5× growth better than 2× if 2× does fewer copies?

<details><summary>Answer</summary>

Because of allocator reuse and peak memory, not copy count. With growth factor `g`, the sum of all
previously freed blocks exceeds the next request only when `g < φ ≈ 1.618`; at `g = 2` the freed
blocks are always just too small, so the allocator has to take fresh memory every time and the heap
ratchets up. Peak live memory during the copy is `(1 + g)·c`, so 2.5c at 1.5× against 3c at 2×.
The copy count genuinely favours 2× — about 2n references against 3n — which is why this is a
tradeoff rather than a strict win.

</details>

**Q2.** A `TreeMap<String, V>` built with `String.CASE_INSENSITIVE_ORDER` reports
`containsKey("KEY") == true` after `put("Key", v)`, but `map.equals(hashMapWithSameEntries)` is
`false`. Why?

<details><summary>Answer</summary>

Because the two questions are answered by different mechanisms. `containsKey` routes through the
comparator, and case-insensitive comparison returns 0, so the key is "the same key".
`Map.equals` is inherited from `AbstractMap` and compares entry sets using `Object.equals`, where
`"Key"` and `"KEY"` are different strings. This is precisely the consequence of a comparator that is
not consistent with `equals`, and it is legal — the JDK documents consistency as a recommendation,
not a requirement.

</details>

**Q3.** You wrap a mutable list in `Collections.unmodifiableList` and return it from a getter.
Your caller reports an intermittent `ConcurrentModificationException` inside *their* loop. Explain.

<details><summary>Answer</summary>

The wrapper is a live view of your still-mutable field. When your code structurally modifies the
backing list while the caller is iterating the view, the backing list's `modCount` changes, the
caller's iterator notices, and it throws — in their stack, from a collection they were told was
read-only. Returning `List.copyOf(field)` fixes it: an independent snapshot cannot be changed by
you. This is the reason the copy is the recommended default for getters despite costing O(n).

</details>

**Q4.** `queue.offer(item)` on a `LinkedBlockingQueue` never blocks in your service, and you run out
of memory under load. What happened?

<details><summary>Answer</summary>

The queue was constructed without a capacity, so it is bounded at `Integer.MAX_VALUE` — effectively
unbounded. `offer` returns `true` forever, the producer never experiences backpressure, and the
queue becomes the leak. Pass an explicit capacity, or use `ArrayBlockingQueue`, which cannot be
constructed unbounded. Also note `offer` versus `put`: `offer` reports fullness by returning
`false`, `put` blocks — so with a real bound you must decide which failure you want.

</details>

**Q5.** Give the one-line fix for `list.removeAll(otherList)` being slow, and say why it works.

<details><summary>Answer</summary>

`list.removeAll(new HashSet<>(otherList))`. The cost of `removeAll` is the receiver's size
multiplied by the *argument's* `contains` cost; a `List` argument makes each `contains` O(m), so the
whole call is O(n·m). Building the `HashSet` is one O(m) pass and makes each `contains` O(1), giving
O(n + m) overall. Do it unconditionally — the wrap is cheap enough that it is never worth
reasoning about the sizes. Note that `AbstractSet.removeAll`'s smaller-side optimisation does not
rescue you here, because it only helps when the other side has O(1) `contains`.

</details>

**Q6.** Why does a `ReadWriteLock` fail to make an access-order `LinkedHashMap` safe for concurrent
readers?

<details><summary>Answer</summary>

Because in access order a `get` is a writer. `LinkedHashMap.get` calls `afterNodeAccess`, which
performs six pointer writes to move the entry to the tail and increments `modCount`. So every
"reader" mutates the structure, and they would all need the write lock — leaving the read lock
unused and the whole point of the `ReadWriteLock` gone. The workable options are a plain mutex
(`Collections.synchronizedMap`, plus your own lock across any iteration), insertion order instead of
access order, or Caffeine, which routes reads into striped per-thread buffers replayed
asynchronously.

</details>

---

**Leaves covered:** 5.1.13, 5.1.17, 5.1.22, 5.1.24, 5.1.25, 5.1.26, 5.1.27 (7 leaves)
**Leaves deferred:** none
**Diagrams included:** none
**Target version:** Java 21 LTS
**Lines:** 711
