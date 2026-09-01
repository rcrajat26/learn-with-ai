# 02 Java Collections — Interview, BASICS tier — summary and questions 1–18 (§5.1)

**Target version: Java 21 LTS.** | [Index](00-index.md)
Previous: [build-it/01-supporting-builds.md](build-it/01-supporting-builds.md) · Next: [90b-interview-basics-b-questions-19-36.md](90b-interview-basics-b-questions-19-36.md)

This is the first of three BASICS-tier interview files. It carries the part summary table
for all **18 subject folders** in the set, the answer shape to use under time pressure, and
questions 1–18 of 36. Questions 19–36 are in
[90b](90b-interview-basics-b-questions-19-36.md); the five predict-the-output puzzles are in
[90c](90c-interview-basics-c-puzzles.md).

Answers here are written at spoken length — what you would actually say out loud, not a
hint and not an essay. Where a number appears, it is the number in the JDK 21 source, and the
subject file that proves it is linked.

## Part summary table — all 18 subjects

| Subject | What it is, in one line | Numbers to know cold | The trap | Read |
|---|---|---|---|---|
| The framework itself | `Iterable` → `Collection` → `List`/`Set`/`Queue`, with `Map` as a sibling, not a subtype | 1.2 (framework), 5 (generics), 21 (sequenced) | `Map` is not a `Collection`; `Arrays.asList` is fixed-size, not immutable | [framework/01](framework/01-basics-why-and-hierarchy.md) |
| Ordering contracts | `compareTo`/`Comparator` decide order; `equals`/`hashCode` decide identity | `31` multiplier; `Boolean` hashes `1231`/`1237` | subtracting ints in a comparator overflows; a mutable key strands its entry | [contracts/01](contracts/01-ordering.md), [contracts/02](contracts/02-equals-hashcode-contract.md) |
| Iteration | `Iterator` is a cursor with `modCount` fail-fast detection | `Iterator.remove` is O(1) on `LinkedList`/`HashMap`, O(n) on `ArrayList` | removing the **second-to-last** element through the list ends the loop early with no exception | [iteration/01](iteration/01-basics-iteration.md), [iteration/02](iteration/02-fail-fast-fail-safe.md) |
| Sequenced collections (21) | `SequencedCollection`/`SequencedSet`/`SequencedMap` — a first/last/`reversed()` tier | 7 / 1 / 10 new methods; JEP 431 | `reversed()` is a live write-through **view**, and `addFirst` on it appends to the source | [sequenced-collections/01](sequenced-collections/01-sequenced-collections.md) |
| Cost and memory | the master cost table plus the byte arithmetic behind it | `Node` 32 B, `LinkedHashMap.Entry` 40 B, `TreeNode` 56 B, `Integer` 16 B | `containsValue` is O(n) on every `Map`, always | [cost-and-memory/01](cost-and-memory/01-master-cost-table.md) |
| `ArrayList` | `Object[]` plus a `size`, grown by 1.5× | `DEFAULT_CAPACITY = 10`; 10, 15, 22, 33, 49, 73 | growth is **1.5×, not 2×** — 2× is `Vector` | [array-list/01](array-list/01-internals-a-growth.md) |
| `LinkedList` | doubly-linked nodes with a bidirectional `node(int)` shortcut | 24 B/node; worst hop `⌊(n−1)/2⌋` | it loses to `ArrayList` even at mid-list insert once you count the walk to the index | [linked-list/01](linked-list/01-internals.md) |
| `ArrayDeque` | circular array, one slot always empty, `head`/`tail` only | no-arg capacity **17** since JDK 12 (16 before) | rejects `null`, because `null` marks a free slot; and it has no `modCount` | [array-deque/01](array-deque/01-internals.md) |
| `PriorityQueue` | array binary min-heap; only index 0 is ordered | `DEFAULT_INITIAL_CAPACITY = 11`; ladder 11, 24, 50, 102 | iteration, `toString`, `stream` and `toArray` are **heap order, not sorted** | [priority-queue/01](priority-queue/01-internals-a-heap.md) |
| `HashMap` | table of bins; a bin is a chain, or a red-black tree once long enough | 16, 0.75, 8, 6, 64, `1 << 30` | treeify only bounds an attack if the keys are `Comparable` | [hash-map/01](hash-map/01-internals-a-constants-and-hash.md) |
| `LinkedHashMap` | `HashMap` plus a `before`/`after` order list threaded through the same nodes | +8 B/entry; `removeEldestEntry` | in access order, a plain `get` is a **structural write** and can throw CME | [linked-hash-map/01](linked-hash-map/01-internals.md) |
| `TreeMap` | red-black tree; `NavigableMap` range and neighbour queries | height ≤ `2·log₂(n+1)`; 40 B/entry | key identity is `compare(...) == 0`, never `equals` | [tree-map/01](tree-map/01-navigable-api.md) |
| Sets | almost every `Set` is a `Map` with one shared dummy value | `PRESENT`, one instance JVM-wide; 32 B/element | `removeAll` with a `List` argument is O(n·m) | [sets/01](sets/01-set-over-map.md), [sets/02](sets/02-set-algebra.md) |
| Specialised maps and sets | `EnumMap`/`EnumSet`, `IdentityHashMap`, `WeakHashMap`, `Hashtable`, `Properties` | `EnumSet` ≤ 64 constants = one `long`; `IdentityHashMap` default capacity 32 | `WeakHashMap` is not a cache; a value that references its own key never clears | [specialised-maps/01](specialised-maps/01-enum-collections.md) |
| Immutability and views | view vs copy vs snapshot, and the five-rung immutability ladder | `List.of` arities 0–10 + varargs | `unmodifiableList` is a live view of a mutable list, and it is shallow | [immutable-collections/01](immutable-collections/01-views-copies-snapshots.md) |
| Concurrent collections | `ConcurrentHashMap`, the blocking queues, copy-on-write | CHM bins locked individually; `LinkedBlockingQueue` default capacity `Integer.MAX_VALUE` | a synchronized wrapper makes each *call* atomic, never a compound action | [concurrent-collections/01](concurrent-collections/01-thread-safety-and-wrappers.md) |
| Utility surfaces | `Collections`, `Arrays`, sorting, `Map` defaults, streams, serialization | TimSort `MIN_MERGE = 32`; `parallelSort` cutover 8192 | `binarySearch` on unsorted input is silently wrong, not an error | [utilities/01](utilities/01-collections-and-arrays.md) |
| Build it | hand-built `ArrayList`, `HashMap`, deque, heap, LRU, ring buffer, bimap | — | writing one is the only way to answer "what happens on resize" without hand-waving | [build-it/01](build-it/01-supporting-builds.md) |

## The answer shape

Every question below is answered in three moves, and the order matters more than the content.

1. **One sentence that names the mechanism.** Not a definition — the shape. "A `HashMap` is an
   array of bins, and the key's hash picks the bin."
2. **The number or the tradeoff.** One concrete constant, cost, or sibling that loses. This is
   what separates a candidate who has read the source from one who has read a blog post.
3. **Stop.** Let them ask for depth. A 90-second answer that lands beats a four-minute answer
   that wanders, and the follow-up is where you show range.

If you do not know, say what you do know and where the boundary is: "I know it treeifies at 8
and the bin has to be in a table of at least 64 slots; I do not remember the exact untreeify
trigger on removal." That is a strong answer, because it is honest and specific.

## Q&A 1–18

### Q1. "`ArrayList` vs `LinkedList` — when would you actually use `LinkedList`?" (§5.1.12)

**Model answer.** `ArrayList` is a contiguous `Object[]` with a size; `LinkedList` is a chain of
nodes each holding an element and two pointers. So `ArrayList` gives you O(1) indexed access and
one `System.arraycopy` per insert or removal, while `LinkedList` gives you O(1) splice at a point
you are already holding, and O(n) to *find* that point.

The honest answer to "when" is: almost never. The textbook case — inserting in the middle — is
one `LinkedList` wins only if you already have a cursor there, because `get(i)` costs a walk of up
to `⌊(n−1)/2⌋` hops. Measured in this set, a located mid-list insert on `LinkedList` is 21–32×
slower than the same insert on `ArrayList` at n ≥ 10,000, because the walk dominates the shift.
Add 24 bytes per node against 4 bytes per array slot and terrible cache locality, and the case
collapses.

The real reasons to pick it are: you need `Deque` behaviour with `null` elements permitted
(`ArrayDeque` rejects `null`), or you are holding a `ListIterator` and splicing through it. For a
queue or stack, use `ArrayDeque`; for a list, use `ArrayList`.

**One-line close:** `ArrayList` unless you hold a cursor or need null-tolerant ends — and then
usually `ArrayDeque`, not `LinkedList`.

### Q2. "What is the `equals`/`hashCode` contract, and what breaks if you violate it?" (§5.1.10)

**Model answer.** `equals` must be reflexive, symmetric, transitive and consistent, and `x.equals(null)`
must be false. `hashCode` must be consistent within a run, and — the load-bearing clause — equal
objects must have equal hash codes. The converse is not required.

What breaks is specific, not vague. A hashed collection finds a key in two steps: it picks the bin
from the hash, then compares within that bin. If two equal objects hash differently they land in
different bins, so `get`, `contains` and `remove` all miss even though the object is in the map.
It is not corrupted — iteration still yields it — it is *unreachable by key*, which reads as a leak.

The mirror failure is a mutable key: put an object in, then mutate a field that `hashCode` reads.
The entry stays in the bin computed at insertion time, and now no lookup can reach it. `HashMap`
caches the hash in the `Node` at insert, so nothing recomputes and nothing warns you.

**If they push:** `record` gets both right by construction and is the answer for a value type —
except with an array component, where the generated `equals` compares array identity. Use a `List`
field instead.

**One-line close:** break `hashCode` and the entry becomes unreachable but not gone, which is why
the symptom is a growing map, not an exception.

### Q3. "Can two unequal objects have the same hash code? Can two equal objects have different ones?" (§5.1.11)

**Model answer.** Yes to the first, no to the second. `hashCode` returns an `int`, so 2³² buckets
of possible values against unbounded objects — collisions are a mathematical certainty, and the
contract explicitly allows them. That is why a hash map compares with `equals` after choosing the
bin, and why a good `hashCode` is about *spreading*, not about uniqueness.

Two equal objects with different hashes is a contract violation, and it is the one that breaks
lookup, as in the previous question. The JDK relies on the promise everywhere: `HashMap` never
re-derives a hash, it caches it in the node.

**If they push:** the concrete demonstration is `"Aa"` and `"BB"`, which both hash to 2112 — and
because `String.hashCode` is a 31-fold, any concatenation of those blocks collides too, giving 2ᵏ
colliding strings of length 2k. That is exactly the primitive behind CVE-2011-4858.

**One-line close:** collisions are legal and expected; unequal hashes for equal objects are a bug.

### Q4. "`HashMap` vs `Hashtable` vs `ConcurrentHashMap`." (§5.1.18)

**Model answer.** All three are hash maps; the difference is the concurrency story and the age of
the design.

| | `HashMap` | `Hashtable` | `ConcurrentHashMap` |
|---|---|---|---|
| Since | 1.2 | 1.0 | 1.5 |
| Thread safety | none | every method `synchronized` on the whole object | per-bin: CAS to install the first node, `synchronized` on the bin head after that |
| Default capacity | 16 | 11 | 16 |
| Growth | double | `(oldCapacity << 1) + 1` | double, **cooperatively** — writers help migrate |
| Index | `hash & (n − 1)` | `(hash & 0x7FFFFFFF) % length` | `hash & (n − 1)` |
| Nulls | one null key, any null values | neither | neither key nor value |
| Iterators | fail-fast | fail-fast via `iterator()`, **not** via `keys()`/`elements()` | weakly consistent, never throws CME |
| `size()` | exact | exact | an **estimate** under concurrent writes |

The point to make out loud is that `Hashtable` is not "the thread-safe `HashMap`". Its lock is the
whole map, so readers block readers, and it still cannot make a compound action atomic —
`if (!t.containsKey(k)) t.put(k, v)` races in `Hashtable` exactly as it does in a
`synchronizedMap`. `ConcurrentHashMap` is not just finer-grained locking, it is a different
contract: atomic compound methods (`putIfAbsent`, `computeIfAbsent`, `merge`) and iterators that
never throw.

**If they push:** "the only difference is synchronization" is a version-stale claim from before
Java 8 and it is wrong on capacity, growth, indexing, null policy, spreading and long-bin
behaviour. `Hashtable` has no treeification; a degenerate bin stays O(n).

**One-line close:** `HashMap` by default, `ConcurrentHashMap` when shared, `Hashtable` never in new
code.

### Q5. "What is `ConcurrentModificationException` and how do you avoid it?" (§5.1.15)

**Model answer.** It is fail-fast bug detection, not a concurrency guarantee. An `ArrayList` keeps
a `modCount` that increments on every structural change; its iterator snapshots that count at
construction and re-checks it at the top of `next()`. If they differ, the iterator concludes the
collection changed underneath it and throws.

You avoid it by mutating through the iterator — `it.remove()` — or by using `removeIf`, which does
the same thing in one pass, or by collecting the victims and removing after the loop. Note what
"structural" means: `list.set(i, v)` and `map.put(existingKey, v)` are not structural and do not
bump `modCount`, so they are safe mid-iteration. `list.sort(...)` **is** structural, so an
iterator held across a sort is poisoned.

The subtlety worth volunteering: fail-fast is best-effort. Remove the second-to-last element
through the list rather than the iterator and you get no exception at all — the loop just ends one
element early, silently, because `hasNext()` is `cursor != size` and both moved by one. That
silent case is worse than the exception.

**One-line close:** CME means "you mutated the collection, not the iterator"; the fix is always to
mutate through the iterator, and the danger is the case that does not throw.

### Q6. "Fail-fast vs fail-safe vs weakly consistent iterators." (§5.1.16)

**Model answer.** Three different contracts, and only two of the three names are real.

- **Fail-fast** — `ArrayList`, `HashMap`, `TreeMap`, `ArrayDeque` (partially), and the
  `Collections.synchronized*` wrappers. Detects comodification via `modCount` and throws
  `ConcurrentModificationException`. Best-effort: the javadoc says the behaviour "cannot be
  guaranteed", and the second-to-last-element case proves it.
- **Snapshot** — `CopyOnWriteArrayList`/`CopyOnWriteArraySet`. The iterator holds a private,
  frozen `Object[]`, so it can never throw CME and never sees later writes. `remove()` on it
  throws `UnsupportedOperationException` unconditionally.
- **Weakly consistent** — `ConcurrentHashMap`, `ConcurrentSkipListMap`, `ConcurrentLinkedQueue`.
  Traverses live state, reflects some concurrent updates and not others, and never throws. It is
  not a point-in-time view.

"Fail-safe" is the term interviewers use for the last two together. It is worth saying that the
JDK does not use that word, and that the two behave very differently: a snapshot iterator gives
you a consistent old view, a weakly consistent one gives you an inconsistent current view.

**One-line close:** fail-fast detects your bug, snapshot freezes a view, weakly consistent never
throws and never promises a view.

### Q7. "Why is `ArrayList` the default `List`, and how does it grow?"

**Model answer.** Because a contiguous array is the shape hardware likes: indexed access is one
address computation, and iteration is a linear prefetchable walk. A `LinkedList` pays a pointer
chase per element and 24 bytes per node.

Growth is the interesting half. `new ArrayList<>()` allocates **no array at all** — it points at a
shared empty sentinel and inflates to `DEFAULT_CAPACITY = 10` on the first `add`. After that it
grows by **1.5×**, computed as `oldCapacity + (oldCapacity >> 1)`, giving 10, 15, 22, 33, 49, 73.
Each growth is one `Arrays.copyOf`, and the total copying over n appends is about 3n references,
which is where "amortised O(1)" comes from.

**If they push:** 2× is `Vector`, and only when `capacityIncrement` is zero. And an `addAll` grows
to exactly `size + numNew` with no headroom, so a loop of `addAll` calls behaves differently from
a loop of `add` calls.

**One-line close:** lazy array, inflate to 10, then 1.5× — and 1.5× not 2× is the detail that
shows you looked.

### Q8. "Which collections reject `null`, and why?"

**Model answer.** It is never arbitrary — each rejection has a mechanical reason.

| Class | Null policy | Reason |
|---|---|---|
| `HashMap`, `LinkedHashMap` | one null key, any null values | null hashes to 0 and is matched by `==`; harmless |
| `ArrayDeque` | rejects | `null` in a slot **means** "free slot" |
| `PriorityQueue` | rejects | `queue[0] == null` is the emptiness test, and `null` is not comparable |
| `TreeMap`/`TreeSet` | rejects under natural ordering | `null.compareTo(...)` cannot work; a null-tolerant `Comparator` lifts the ban |
| `Hashtable` | rejects both | 1.0-era defensiveness |
| `ConcurrentHashMap` | rejects both | `get` returning `null` must unambiguously mean "absent" — with no lock you cannot re-check |
| `EnumMap` | rejects null keys, allows null values | a key must have an `ordinal()`; values use a private sentinel |
| `List.of`/`Set.of`/`Map.of` | reject | fail-fast immutability, and it lets `contains(null)` throw rather than lie |

**One-line close:** every null ban is a sentinel collision or an ambiguity the API cannot resolve —
name the sentinel and you have named the reason.

### Q9. "Java 21's `reversed()` — is it a copy or a view?"

**Model answer.** A live view, and that is the part people get wrong. `list.reversed()` returns a
`ReverseOrderListView` over the same backing list: writes through it land in the source, and
writes to the source are visible through it. It is O(1) to create.

The consequence to state is the orientation flip. On `[A, B, C]`, calling `addFirst("X")` on the
view puts `X` at the **end** of the source, because "first" in the view is "last" in the source.
Measured: source becomes `[A, B, C, X]` and the view reads `[X, C, B, A]`. Similarly `view.add(x)`
appends to the view and therefore lands at the front of the source.

**If they push:** `reversed().reversed()` returns the original object by identity for `List` and for
`LinkedHashMap` — the view's `reversed()` is literally `return base;`. It is **not** identity for
`TreeMap.descendingMap()`, which builds a fresh `AscendingSubMap` that is `equals` but not `==`.

**One-line close:** a view, so cheap to take and dangerous to write through without thinking about
which end you mean.

### Q10. "Why must you never write `a.getAge() - b.getAge()` in a comparator?"

**Model answer.** Because `int` subtraction overflows and the sign flips. With
`a = Integer.MIN_VALUE` and `b = 1`, the true answer is "a is less", but the subtraction wraps to a
positive value and the comparator says the opposite. That breaks antisymmetry and transitivity, and
TimSort detects the inconsistency and throws
`IllegalArgumentException: Comparison method violates its general contract!` — usually far away
from the comparator, in a sort of a large list, non-deterministically.

The fix is `Integer.compare(a, b)`, or `Comparator.comparingInt(Person::getAge)`, which avoids
boxing as well.

**If they push:** the same class of bug shows up with `Double`: use `Double.compare`, not `<`, so
that `NaN` and `-0.0` are ordered consistently. And `reversed()` flips the sign of the **whole
chain** built so far, not just the last key — that is a frequent source of a wrong secondary sort.

**One-line close:** subtraction overflows, `Integer.compare` does not, and the sort will only tell
you months later.

### Q11. "What are the three ways to walk a `Map`, and which do you use?"

**Model answer.** `keySet()`, `values()`, and `entrySet()`. If you need both key and value, use
`entrySet()` — one pass, one object per entry, and each element is the map's own node. Using
`keySet()` and then `map.get(k)` inside the loop doubles the work: a second hash and a second bin
walk per key.

All three are **live views**, not copies, and each is cached — `map.keySet() == map.keySet()` is
`true`. Removing through a view removes from the map: `keySet().remove(k)` deletes the mapping,
`values().remove(v)` deletes exactly **one** matching entry, and `entrySet().remove(e)` requires
both key and value to match. None of them supports `add`.

**If they push:** `entry.setValue(v)` writes straight into the node and is not structural, so it is
safe mid-iteration; and iteration of a `HashMap` is O(capacity + size), not O(size), because every
empty slot is visited too.

**One-line close:** `entrySet()` when you need both, and remember the views are live doors into the
map, not snapshots.

### Q12. "Why does an `ArrayList<Integer>` cost about five times an `int[]`?"

**Model answer.** Because every element becomes a heap object. An `int[]` of a million elements is
about 4 MB: a 16-byte header plus 4 bytes per slot. An `ArrayList<Integer>` of the same million is
about 20 MB — the list shell, a reference array at 4 bytes per slot under compressed oops, and a
separate 16-byte `Integer` object per element (12-byte header plus a 4-byte `int`).

On top of the bytes you pay a pointer chase per access, which costs more than the bytes on a
cache-sensitive loop. And `ArrayList` never shrinks, so a list that peaked large carries about 25%
slack forever unless you call `trimToSize()`.

**If they push:** the `Integer` cache covers `−128..127` only, so those are shared instances; above
that every box is a new object, which is also why `==` on boxed values "works" in small tests and
fails in production. For a numeric hot path use `int[]`, or a primitive-specialised map from
fastutil or Eclipse Collections.

**One-line close:** 4 bytes becomes 16 plus a pointer, so five times the memory and a cache miss
per element.

### Q13. "Why does `ArrayDeque` reject `null`?"

**Model answer.** Because `null` is already taken: the implementation is a circular `Object[]` with
`head` and `tail` indices and **no size field**, and an empty slot is represented by `null`. The
class even relies on it — `elements[tail]` is always `null`, and the iterator's
`nonNullElementAt` uses a null slot as its (partial) comodification check. Allowing a `null`
element would make "empty slot" and "stored null" indistinguishable.

Worth adding: `ArrayDeque` has no `modCount` at all, so its fail-fast detection is weaker than
`ArrayList`'s, and its no-arg capacity is **17**, not 16 — `new Object[16 + 1]`, one slot reserved
so `head == tail` can mean "empty" — and that changed in **JDK 12**, not in the JDK 9 rewrite.

**One-line close:** `null` is the free-slot marker, so a null element would break the emptiness
invariant; use `LinkedList` if you genuinely need null-tolerant ends.

### Q14. "When do you use a `PriorityQueue` instead of sorting a list?"

**Model answer.** When you need the extreme repeatedly while the data is still arriving, or when
you only want the top k. A `PriorityQueue` is an array binary heap: `offer` and `poll` are O(log n),
`peek` is O(1), and building one from a `Collection` is O(n) via `heapify` — cheaper than the
O(n log n) a full sort costs.

For "top k of a billion", the answer is a **min**-heap of size k: push, and once it is full,
compare against the root and replace it if the new element is bigger. That is O(n log k) time and
O(k) memory instead of O(n log n) and O(n). The counter-intuitive part — a min-heap for the
*largest* k — is worth saying explicitly: the root has to be the weakest element you are keeping,
because that is the one a newcomer must beat.

**If they push:** it is unbounded, unstable (equal elements come out in arbitrary order), and its
iteration is heap order, not sorted order. The only sorted view is a destructive drain by repeated
`poll`.

**One-line close:** a heap when you want the extreme repeatedly or only the top k; a sort when you
want everything in order once.

### Q15. "What does `TreeMap` require of its keys?"

**Model answer.** Either the keys implement `Comparable`, or you pass a `Comparator` at
construction. That choice is fixed for the life of the map — it is even part of the serialized
form — and it decides which of two internal search loops runs.

Two consequences people miss. First, `null` keys are rejected under natural ordering because
`compareTo` would be called on a null receiver; with a `Comparator.nullsFirst(...)` they are
allowed, because the comparator owns that decision. Second, and more important: key identity in a
`TreeMap` is `compare(k1, k2) == 0`, **never** `equals`. So a comparator that is not consistent
with `equals` gives you a map where `containsKey` and `Map.equals` disagree — the classic case is
`BigDecimal`, where `2.0` and `2.00` compare equal but are not `equals`.

**One-line close:** `Comparable` or a `Comparator`, no nulls without one, and duplicate detection is
`compare == 0` rather than `equals`.

### Q16. "How is `HashSet` implemented?"

**Model answer.** As a `HashMap` with the values thrown away. The field is literally
`private transient HashMap<E,Object> map`, and `add(e)` is
`return map.put(e, PRESENT) == null;` where `PRESENT` is a single `static final Object` shared for
the whole JVM. Every `HashMap` fact therefore transfers unchanged: capacity 16, load factor 0.75,
treeify at 8, one null element allowed, iteration order unspecified.

The cost of the trick is one wasted reference per element — 32 bytes per `Node` where a
value-less node could have been 24 — and the benefit is that `HashSet` needed almost no code.
`LinkedHashSet` is the same trick one level further: it extends `HashSet` and calls a
package-private constructor whose only job is to build a `LinkedHashMap` instead. `TreeSet` wraps a
`TreeMap` the same way.

**If they push:** the two classes that break the pattern are `CopyOnWriteArraySet`, which wraps a
`CopyOnWriteArrayList` and so is O(n) per `add`, and `EnumSet`, which is a bitmask in a `long`.

**One-line close:** a `Map` with a dummy value, which is why every `HashMap` number is also a
`HashSet` number.

### Q17. "What is `Properties`, and what is wrong with it?"

**Model answer.** It is the `.properties` file API, and it extends `Hashtable<Object,Object>` —
which is the thing that is wrong with it. Because it is a `Map<Object,Object>`, nothing stops you
putting a non-`String` key or value in, and then `getProperty` silently ignores it: `getProperty`
filters on `instanceof String` before consulting the `defaults` chain, while plain `get` does not.
So `p.put("k", 42)` followed by `p.getProperty("k")` returns `null`.

Use `setProperty`/`getProperty` exclusively, never `put`/`get`. Also worth knowing: since Java 9
the real storage is a `ConcurrentHashMap` behind the `Hashtable` façade, so it genuinely is
thread-safe; `stringPropertyNames()` is an unmodifiable **snapshot** that walks the defaults chain
and keeps `String`-only pairs; and `System.getProperties()` hands you the live, mutable, shared
singleton rather than a copy.

**One-line close:** a `Hashtable` pretending to be a string map — stay on `setProperty`/`getProperty`
and it behaves.

### Q18. "Is `List.copyOf(x)` a view or a snapshot?"

**Model answer.** A snapshot, and an immutable one. `List.copyOf` copies the elements into an
`ImmutableCollections.ListN` (or a `List12` for one or two elements), so later changes to the
source are invisible. `Collections.unmodifiableList(x)` is the opposite: a live read-through
**view** over the same backing list, so every change to the source shows up through the wrapper.
That is the single distinction to get right, because both are described as "read-only".

Two refinements. `List.copyOf` rejects `null` elements with an NPE, and it can return the argument
unchanged when the argument is already a null-free immutable list — so `List.copyOf(List.of(1,2))`
returns the same instance. And both are **shallow**: freezing the list does not freeze the objects
in it.

**One-line close:** `copyOf` snapshots and rejects nulls, `unmodifiableList` wraps and stays live —
and neither makes the elements immutable.

## Pitfalls

### Answering "how does `HashMap` work" by starting with a definition

**Wrong**

> "`HashMap` is a class in `java.util` that implements the `Map` interface and stores key-value
> pairs. It is not synchronized and permits null values and one null key."

That is the javadoc's first paragraph. It tells the interviewer nothing except that you can read.

**Right**

> "It is an array of bins. The key's `hashCode` is spread with one xor-shift, masked down to a bin
> index, and the bin is a chain — or a red-black tree once it holds nine nodes in a table of at
> least 64 slots. It doubles at 75% load, and on resize each entry either stays where it is or
> moves exactly `oldCapacity` slots up, decided by one bit."

**Why people believe it:** interview prep material is written as glossary entries, and a definition
feels safer under stress. But the mechanism is the answer, and it is also shorter.

### Saying "fail-safe" as if the JDK defined it

**Wrong**

> "`ConcurrentHashMap`'s iterator is fail-safe, so it works on a copy."

Two errors in one sentence: "fail-safe" is not a JDK term, and `ConcurrentHashMap` does not copy
anything. Only `CopyOnWriteArrayList` iterates a copy.

**Right**

> "`ConcurrentHashMap`'s iterator is weakly consistent: it walks live state, may or may not see
> writes that happen during the walk, and never throws. `CopyOnWriteArrayList`'s is a snapshot over
> a frozen array, so it sees nothing that happens after it was created."

**Why people believe it:** every blog post on the topic uses the three-way "fail-fast / fail-safe"
framing, and it collapses two genuinely different contracts into one word.

### Quoting "treeify makes collisions O(log n)" without the qualifier

**Wrong**

> "Since Java 8 a long bin becomes a red-black tree, so hash-collision denial of service is fixed
> at O(n log n)."

**Right**

> "A long bin becomes a red-black tree, **provided the keys are `Comparable`**. Without a real
> ordering, `TreeNode.find` has to search both subtrees, and a treeified bin of non-`Comparable`
> keys is measurably *worse* than a plain chain — 529 ms against 312 ms at 20,000 identical-hash
> keys, where `Comparable` keys took 2.06 ms. `String` is `Comparable`, so the actual attack
> surface is covered; a custom key type gets nothing."

**Why people believe it:** JEP 180's summary says "balanced trees", and the `Comparable`
precondition is buried in a `HashMap` class comment. The unqualified version is repeated
everywhere.

## Cheat sheet

| Question | The one-line answer |
|---|---|
| Default `List` / `Set` / `Map` / `Queue` | `ArrayList` / `HashSet` / `HashMap` / `ArrayDeque` |
| `ArrayList` growth | lazy, inflate to 10, then 1.5× |
| `Vector` growth | 2×, but only when `capacityIncrement` is 0 |
| `HashMap` constants | 16, 0.75, treeify 8, untreeify 6, min-treeify-capacity 64, max `1 << 30` |
| `Hashtable` constants | capacity 11, growth `2n + 1`, index by `%` |
| `ArrayDeque` no-arg capacity | 17 since JDK 12, 16 before |
| `PriorityQueue` no-arg capacity | 11 |
| Null key allowed | `HashMap`, `LinkedHashMap`, `IdentityHashMap`, `WeakHashMap` (one each) |
| Null banned entirely | `TreeMap`/`TreeSet` (natural order), `Hashtable`, `ConcurrentHashMap`, `ArrayDeque`, `PriorityQueue`, `List.of` family |
| Structural modification | anything that changes size; **not** `set(i,v)`, **not** `put` on an existing key, **not** `entry.setValue` |
| `list.sort(...)` mid-iteration | structural — poisons a held iterator |
| Iterator contracts | fail-fast (unsynchronized + wrappers), snapshot (copy-on-write), weakly consistent (concurrent) |
| `containsValue` cost | O(n) on every `Map`, no exceptions |
| `HashMap` iteration cost | O(capacity + size) — empty slots are visited |
| `Set` implemented as | a `Map` with a shared `PRESENT` dummy value |
| View vs snapshot | `unmodifiableList` = live view; `List.copyOf` = immutable snapshot |
| `reversed()` | live write-through view; `addFirst` on it appends to the source |
| `Iterator.remove` cost | O(1) `LinkedList`/`HashMap`, O(log n) `TreeMap`, O(n) `ArrayList`, unsupported on immutable and copy-on-write |
| Comparator rule | never subtract; `Integer.compare`, and `reversed()` flips the whole chain |
| Sizing a map for n entries | `HashMap.newHashMap(n)` (Java 19+), not `new HashMap<>(n)` |

## Self-test

**Q1.** A colleague says `Hashtable` and `HashMap` differ only in synchronization. Give three
other differences.

<details><summary>Answer</summary>

Default capacity 11 versus 16; growth `(oldCapacity << 1) + 1` versus doubling; bin index by
`(hash & 0x7FFFFFFF) % length` versus `hash & (n − 1)`. Also: `Hashtable` rejects null keys and
values where `HashMap` allows one null key and any null values; `Hashtable` applies no spread
function to `hashCode()`; `Hashtable` has no treeification, so a degenerate bin stays O(n); and
`Hashtable` exposes `Enumeration`s via `keys()`/`elements()` that are **not** fail-fast.

</details>

**Q2.** Why does removing the second-to-last element of an `ArrayList` inside a for-each loop not
throw `ConcurrentModificationException`?

<details><summary>Answer</summary>

`hasNext()` is `cursor != size`, not `cursor < size`. Removing an element decrements `size` by one
at the moment `cursor` has also advanced by one, so the two meet exactly and the loop exits before
`next()` — which is the only place the `modCount` check lives — runs again. The removal succeeds,
the last element is never visited, and nothing is reported. This is the reason the javadoc calls
fail-fast best-effort rather than guaranteed.

</details>

**Q3.** `map.keySet().remove(k)` — what happens to the map?

<details><summary>Answer</summary>

The mapping for `k` is deleted from the map. The three views (`keySet`, `values`, `entrySet`) are
live doors into the map, not copies, and each is cached so the same instance is returned every
call. `keySet().remove(k)` calls `removeNode` with `matchValue = false`, so the value is ignored;
`entrySet().remove(e)` passes `matchValue = true` and so requires key *and* value to match; and
`values().remove(v)` removes exactly one arbitrary matching entry, because `Values` declares no
`remove` override and the inherited `AbstractCollection` scan returns on the first hit.

</details>

**Q4.** You need a queue. Why not `LinkedList`, which implements `Queue`?

<details><summary>Answer</summary>

`ArrayDeque` is faster and smaller for the same job: a circular array with no per-element node, so
4 bytes per slot against `LinkedList`'s 24 bytes per node, and no pointer chase. `LinkedList` wins
only when you need `null` elements at the ends (`ArrayDeque` rejects `null`, because `null` marks a
free slot) or when you are splicing through a held `ListIterator`. Note the two costs of
`ArrayDeque`: it has no `modCount`, so comodification detection is partial, and its no-arg capacity
is 17 rather than 16.

</details>

**Q5.** Someone hands you a `List` from an API and says "it's immutable". What do you check?

<details><summary>Answer</summary>

Three things. (1) Is it immutable or merely unmodifiable? `Collections.unmodifiableList(x)` is a
live view — the owner of `x` can still change what you see. (2) Is it shallow? Every JDK immutable
collection is: `List.of(sb)` freezes which `StringBuilder` is in slot 0, not its contents. (3) Does
it tolerate `null` queries? `List.of(...).contains(null)` throws NPE, where
`Collections.unmodifiableList(...)` and `Arrays.asList(...)` return `false`. If you need a real
guarantee, take `List.copyOf(x)` yourself — a snapshot that also rejects nulls.

</details>

**Q6.** Why does `HashMap` cache the hash in the node rather than recomputing it?

<details><summary>Answer</summary>

Two reasons. Speed: `resize` moves every entry, and with the hash cached in a `final int` field no
user `hashCode()` runs during a resize at all — Java 7 called it per entry. And correctness of the
comparison order: the cached `int` compare is the cheap first gate in
`e.hash == hash && ((k = e.key) == key || (key != null && key.equals(k)))`, so a mismatching key
never reaches `equals`. The consequence is the mutable-key trap: because nothing recomputes, an
object whose hash changes after insertion stays in the bin it was filed under and becomes
unreachable by key.

</details>

---

**Leaves covered:** 5.1.10, 5.1.11, 5.1.12, 5.1.15, 5.1.16, 5.1.18 (6 leaves)
**Leaves deferred:** none
**Diagrams included:** none
**Target version:** Java 21 LTS
**Lines:** 575
