# 02 Java Collections — Interview, INTERNALS tier — questions 19–36 (§5.1)

**Target version: Java 21 LTS.** | [Index](00-index.md)
Previous: [92a-interview-internals-a2-questions-10-18.md](92a-interview-internals-a2-questions-10-18.md) · Next: [92c-interview-internals-c-puzzles-and-checklist.md](92c-interview-internals-c-puzzles-and-checklist.md)

Part 3 of the INTERNALS question set: questions 19–36 of 36 — the amortisation proof, the
`ConcurrentHashMap` block, red-black trees, and one source-level question per remaining subject.
The tier summary table is in [92](92-interview-internals.md); questions 10–18 are in
[92a](92a-interview-internals-a2-questions-10-18.md); the puzzles and the atomic concept checklist
are in [92c](92c-interview-internals-c-puzzles-and-checklist.md).

Line numbers are JDK 21. Nothing here is a JMH figure — every measurement in this set is
single-shot wall clock, and the ratio is the claim.

## Q&A 19–36

### Q19. "Prove that `ArrayList.add` is amortised O(1)." (§5.1.14)

**Model answer.** Three standard proofs, and the one to give depends on how much time you have.

**The aggregate method** is the fastest to say. With growth factor `g`, the capacities on the way to
`n` form a geometric sequence, so the total elements copied is
`c + gc + g²c + … ≈ n·g/(g − 1)`. At the JDK's `g = 1.5` that is about **3n** copies for n appends,
so the total cost of n appends is O(n) and the cost per append is O(1). At `g = 2` it is 2n.
Measured for a million appends at 1.5×: 29 grows and 2,430,972 copies, final capacity 1,215,487.

**The accounting method.** Charge each `add` a constant number of credits: one to write the element,
and the rest banked to pay for the future copy of itself and of the elements that will not have been
copied since the last growth. At `g = 2` three credits suffice; at `g = 1.5` you need **four**,
because a smaller factor means each element is copied more often.

**The potential method** is the one that catches people out, because the textbook potential function
is for doubling. `Φ = 2·size − capacity` works at `g = 2` and provably fails at 1.5 — it yields
`0.5c + 3` rather than a constant. The general form is
`Φ_g = (g/(g − 1))·size − (1/(g − 1))·capacity`, which at 1.5 is `3·size − 2·capacity`, giving an
amortised cost of 4.

**And the caveat that makes this a good answer rather than a recited one:** amortised O(1) is a
guarantee about a *sequence*, not about any single call. One `add` in that sequence copies the entire
array — for a million-element list, 4 MB — so the operation has O(n) worst-case latency, and in a
latency-sensitive service that lands on some unlucky request. Amortised is also adversary-proof,
which distinguishes it from `HashMap.get`'s *average*-case O(1): no input can make n appends cost
more than O(n), whereas an attacker who controls hash codes can absolutely make `get` cost O(n).

**One-line close:** total copies over n appends are `n·g/(g−1)` ≈ 3n at 1.5×, so O(n) total and O(1)
each — but one of those calls is O(n), and amortised does not mean predictable.

### Q20. "How does `ConcurrentHashMap` achieve thread safety without locking the whole map?" (§5.1.19)

**Model answer.** By locking one **bin** at a time, and by not locking reads at all.

The write path has two cases. If the target bin is empty, the writer installs its node with a single
`casTabAt` — a compare-and-swap on the table slot, no lock. If the bin is occupied, the writer does
`synchronized (f)` where `f` is the **bin head node itself**, then re-checks `tabAt(tab, i) == f`
inside the lock, because the head may have changed between the read and the acquisition. So the
granularity is one bin, and two writers touching different bins never interact.

The read path takes no lock, no CAS and performs no write. `get` is volatile reads only —
`Node.val` and `Node.next` are `volatile`, and the table itself is read with `tabAt` (an acquire
read) — so a reader sees a consistent node or the next one, never a torn state. That is also why its
iterators are *weakly consistent* and can never throw `ConcurrentModificationException`: there is no
`modCount` to compare.

Three node hashes are reserved as signals, and knowing them is the tell that you have read the
class: `MOVED = -1` (a `ForwardingNode`, meaning "this bin has been migrated, go to `nextTable`"),
`TREEBIN = -2` (the bin is a `TreeBin`, which carries its own read-write `lockState` distinct from
`HashMap`'s lock-free `TreeNode`), and `RESERVED = -3` (a `ReservationNode`, held while a
`computeIfAbsent` mapping function runs). `spread` clears the sign bit —
`(h ^ (h >>> 16)) & 0x7fffffff` — precisely so that a user hash can never collide with those.

**If they push:** the resize is the good follow-up, because it is *cooperative* rather than
stop-the-world. See Q29.

**One-line close:** CAS to install into an empty bin, `synchronized` on the bin head otherwise, and
reads are volatile reads with no lock — so the lock granularity is one bin, not the map.

### Q21. "Why does `ConcurrentHashMap` not allow null?" (§5.1.20)

**Model answer.** Because with no lock, `get` returning `null` would be irreducibly ambiguous.
On a plain `HashMap` you resolve "absent or mapped to null?" with a follow-up `containsKey` — that
works because you can reason about the map not changing between the two calls. On a concurrent map
you cannot: the entry may be inserted or removed between them, so `containsKey` answers a different
question than `get` did, and no amount of re-checking closes the window. Doug Lea's position is that
the ambiguity is a design defect that `HashMap` merely tolerates and a concurrent map cannot.

The mechanism is one guard: `if (key == null || value == null) throw new NullPointerException();` at
`ConcurrentHashMap.java:1011`. Note what most write-ups get wrong — it bans null **keys as well as
values**, in the same line. The keys ban has an additional reason on top: the null key's index
cannot be computed from a hash.

There is a second consequence worth volunteering. Because `null` is unambiguous, `null` becomes
usable as a *signal*: `compute`, `computeIfAbsent`, `computeIfPresent` and `merge` all treat a
`null` return from the remapping function as "remove this mapping", which is a cleaner API than it
could otherwise have been.

**One-line close:** with no lock, `get` returning `null` cannot be disambiguated by a follow-up
`containsKey`, so the guard at `:1011` bans both null keys and null values — and frees `null` up as
the "remove" signal in the compute family.

### Q22. "Is `size()` on a `ConcurrentHashMap` accurate?" (§5.1.21)

**Model answer.** No, and it is documented not to be — it is an estimate, and there are two
separate reasons.

The counting mechanism is a **striped counter**, borrowed from `LongAdder`. There is a
`baseCount` field that writers CAS; when that CAS fails under contention, the map lazily allocates a
`CounterCell[]` and writers CAS into a cell chosen by their thread's probe. `sumCount()` then adds
`baseCount` plus every non-null cell, **with no lock**, so it can read cell A before an update and
cell B after one. On an uncontended map `counterCells` stays `null` and the count comes straight
from `baseCount`.

The second reason is more basic: even a perfectly-read count is stale the instant it returns under
concurrent writes. So "accurate" is not a property `size()` could have.

There is also a signature problem: `size()` returns `int`, so it **clamps** at `Integer.MAX_VALUE` —
a map with more mappings than that reports the wrong number, deliberately. `mappingCount()` (since
Java 8) returns a `long` and is the method to use for a large map.

**If they push:** the `CounterCell` class is annotated `@Contended`, which pads each cell onto its
own cache line so that two threads incrementing different cells do not fight over one line. That
costs roughly 8× the memory for the array and eliminates false sharing — the trade only makes sense
because the array is allocated lazily, on contention. `@Contended` is JDK-internal and not usable
from application code.

**One-line close:** an estimate from an unlocked sum over `baseCount` plus lazily-allocated
`@Contended` counter cells — and use `mappingCount()`, because `size()` clamps at
`Integer.MAX_VALUE`.

### Q23. "What is a red-black tree, and why not AVL?" (§5.1.28)

**Model answer.** A binary search tree with one extra bit per node and five invariants that
together bound the height:

1. every node is red or black;
2. the root is black;
3. every `NIL` leaf is black;
4. **no red node has a red child** — reds cannot be consecutive;
5. **every root-to-leaf path has the same number of black nodes** — equal black height.

The bound follows from 4 and 5 in two steps. Rule 4 means at most half the nodes on any path are
red, so `h ≤ 2·bh(root)`. Rule 5 plus induction means a subtree of black height `bh` holds at least
`2^bh − 1` internal nodes. Combining them: **`h ≤ 2·log₂(n + 1)`**, so lookup is O(log n) with no
probabilistic hand-waving.

Why not AVL: AVL keeps a tighter height (about `1.44·log₂ n` against red-black's `2·log₂ n`), so it
wins on **lookup**. But it maintains that tightness with more rebalancing work per write —
rebalancing can propagate further and more often. Red-black is deliberately looser and therefore
cheaper to fix up, with a small bounded cost per insert or delete. For a general-purpose map with a
mixed read/write load, the JDK chose the cheaper write. If your workload were read-almost-only, AVL
would be the better structure.

**If they push:** two things. `fixAfterInsertion` has four cases (red uncle → recolour and continue
up; black uncle with a zigzag → rotate at the parent to straighten, then fall into the next case;
black uncle straight → recolour and rotate at the grandparent, terminating; then force the root
black after the loop), and `fixAfterDeletion` has four mirrored cases with the "double black"
concept. And the reason the JDK picked red-black over a skip list, which is the other O(log n)
option: a skip list mutation is a single-pointer CAS and is valid at every intermediate step, which
is why `ConcurrentSkipListMap` can be lock-free — whereas a rotation needs three or more pointers
updated together, which a single-word CAS cannot do. So `TreeMap` and `ConcurrentSkipListMap` differ
in structure for a concurrency reason, not a performance one.

**One-line close:** five invariants give `h ≤ 2·log₂(n+1)`; AVL is tighter and so faster to read but
costlier to write, and the JDK optimised for the mixed workload.

### Q24. "How does `HashSet` avoid duplicating `HashMap`, and how far does that pattern go?"

**Model answer.** `HashSet` holds `private transient HashMap<E,Object> map` and one shared
`private static final Object PRESENT = new Object()`. `add(e)` is
`return map.put(e, PRESENT) == null;` — the return value comes free from `put`'s existing contract,
so there is no second lookup. Every `HashMap` constant therefore applies unchanged: capacity 16,
load factor 0.75, treeify at nine nodes in a 64-slot table, one null element.

`LinkedHashSet` goes one level further and is a nice piece of API archaeology: it `extends HashSet`
and every constructor calls the package-private `HashSet(int, float, boolean dummy)`, whose only job
is to build a `LinkedHashMap` instead. The `dummy` boolean carries no information at all — it exists
purely to disambiguate the overload from `HashSet(int, float)`.

`TreeSet` wraps a `TreeMap` the same way, `ConcurrentSkipListSet` wraps a `ConcurrentSkipListMap`,
and `Collections.newSetFromMap(m)` is the generalised form: hand it any empty `Map<E,Boolean>` and
you get a `Set` with that map's semantics — `newSetFromMap(new IdentityHashMap<>())` for an identity
set, `newSetFromMap(new WeakHashMap<>())` for a weak one.

**If they push:** the cost and the two exceptions. The cost is one wasted reference per element: a
`HashMap.Node` is 32 bytes where a hypothetical value-less node would be 24. The exceptions are
`CopyOnWriteArraySet`, which wraps a `CopyOnWriteArrayList` — so `add` and `contains` are O(n) scans
— and `EnumSet`, which is a bitmask in a `long` (or a `long[]`) with no map and no list underneath.
`ConcurrentHashMap.newKeySet()` is the pattern done properly for concurrency: a private map plus a
key-set view whose `add` works, unlike `chm.keySet()`, whose `add` throws because there is no value
to store.

**One-line close:** a `HashMap` field plus one JVM-wide `PRESENT` sentinel, generalised by
`newSetFromMap` — broken only by `CopyOnWriteArraySet` (a list) and `EnumSet` (a bitmask).

### Q25. "How is `EnumSet` implemented?"

**Model answer.** As a bit vector over ordinals, in one of two subclasses chosen by the **number of
constants in the enum**, not by the size of the set. `EnumSet.noneOf` reads
`universe.length <= 64` and returns a `RegularEnumSet`, whose entire state is
`private long elements`, or a `JumboEnumSet`, whose state is a `long[]` sized `(N + 63) >>> 6` plus a
cached `int size`.

Membership is `(elements & (1L << e.ordinal())) != 0`; `add` is `|=`, `remove` is `&= ~`. `size()` on
the regular form is `Long.bitCount(elements)`, recomputed rather than stored. Bulk operations are
single machine instructions: union is `elements |= es.elements`, difference `&= ~`, intersection
`&=`, and `containsAll` is `(es.elements & ~elements) == 0` — no loop, no allocation, no comparison.

The mask trick is worth being able to explain, because it looks like a bug. `allOf`'s mask is
`elements = -1L >>> -universe.length`, and `complement()` is `~elements` followed by the same mask.
A *negative* shift distance works because the JLS specifies that a `long` shift uses only the low six
bits of the distance, so `>>> -5` is `>>> 59`. And note: there is **no `mask` field** — the mask is
recomputed inline, so any description of `complement()` as `~elements & mask` is describing
something that does not exist.

**If they push:** the `universe` array comes from
`SharedSecrets.getJavaLangAccess().getEnumConstantsShared` — shared and **uncloned**, so it costs
nothing per set. The class is `sealed` since Java 17, `permits JumboEnumSet, RegularEnumSet`. And
the bulk fast paths require the argument to be a `RegularEnumSet` of the *same* element type;
with a mismatch each operation degrades differently — `addAll` throws `ClassCastException`,
`removeAll` returns `false`, `containsAll` reduces to `arg.isEmpty()`, and **`retainAll` silently
empties the receiver**, which is the dangerous one.

**One-line close:** ordinals as bits in a `long` (or a `long[]` above 64 constants), so set algebra
is one instruction — and the mask is recomputed with a negative shift distance, not stored.

### Q26. "How does `IdentityHashMap` store its entries?"

**Model answer.** In one flat `Object[]`, with the key at an even index and its value at `i + 1`.
There is **no `Entry` or `Node` class in the whole class** — `entrySet()` synthesises views on
demand. `table.length` is always `2 × capacity` and always a power of two.

The index function is `((h << 1) - (h << 8)) & (length - 1)` where `h` is
`System.identityHashCode(x)`. The multiplier is `-254` = `-2 × 127`, which mixes low bits upward and,
because it is even, guarantees an even result — the evenness comes from the multiplier, not from a
mask. Collisions are resolved by **linear probing**: `nextKeyIndex(i, len)` is
`i + 2 < len ? i + 2 : 0`, stepping over key/value pairs, and the probe stops at the first slot with
a `null` key. That stopping rule is the whole invariant, and it is why the table must never fill
completely — a full table would make `get` loop forever, so the class guards it with
`IllegalStateException("Capacity exhausted.")`.

Deletion cannot leave a tombstone, because a tombstone would break the "stop at the first null" rule.
Instead `closeDeletion(d)` performs Knuth's Algorithm R back-shift: it walks forward from the hole
and moves any entry whose home slot lies on the circular path `[home, current)` back into it,
repeating with the hole at the new position. So **one `remove` can relocate several entries**, and a
cached slot index is never valid across a removal.

**If they push:** the sizing is the outlier detail. The constructor argument is an
`expectedMaxSize`, not a capacity — `capacity(e)` is `Integer.highestOneBit(3e)` clamped to
`[4, 1 << 29]` — and the load factor is a fixed 2/3 of capacity, i.e. 1/3 of `table.length`. The
resize test is `s = size + 1; s + (s << 1) > len`, so a default map (capacity 32, table length 64)
resizes on the **22nd** `put`. Null keys are supported via a `static final Object NULL_KEY`
sentinel, and the null key hashes to an ordinary slot — not slot 0.

**One-line close:** one interleaved `Object[]` with no entry objects, an identity hash scrambled to
an even index, linear probing that stops at the first null key, and back-shift deletion that can
relocate entries.

### Q27. "When exactly does a `WeakHashMap` entry disappear?"

**Model answer.** In four steps, and the gap between step 2 and step 4 is unbounded.

1. You drop your last strong reference to the key.
2. The GC clears the referent — `Entry extends WeakReference<Object>`, so the entry **is** the weak
   reference to the key.
3. The GC enqueues that entry on the map's `private final ReferenceQueue<Object> queue`.
4. The **next map operation** calls `expungeStaleEntries()`, which polls the queue and unlinks each
   dead entry from its bucket.

There is no background thread; cleanup piggybacks on your calls. The funnels are `getTable()` and
`size()`, so almost any read triggers it — which is why `size()` can shrink between two adjacent
calls with nothing else happening, `isEmpty()` can flip, and `get` can start returning `null`. Those
are documented, not bugs.

Two implementation details that explain the design. The entry caches `final int hash`, because by
expunge time the key is already `null` and cannot be re-hashed — the cached hash is the only route
back to the right bucket. And `expungeStaleEntries` nulls `e.value` ("Help GC") but deliberately does
**not** null `e.next`, because an in-flight `HashIterator` may be parked on that entry.

**If they push:** the exceptions to the funnel, and the leak. `clear()` does not expunge — it drains
the queue by hand, twice — and iteration expunges only once, in the iterator's constructor, while
holding strong references to `nextKey`/`currentKey` so the key cannot vanish mid-loop. The
guaranteed leak is the **value-holds-key** cycle: the map holds values strongly, so if a value
references its own key the entry is immortal; the two-entry variant, where V1 references K2 and V2
references K1, is immortal too and much harder to spot. And `ThreadLocalMap.Entry` has the same
shape — `extends WeakReference<ThreadLocal<?>>` with a strong `Object value` — but **no queue at
all**, which is why a pooled thread plus a forgotten `ThreadLocal` gives you an unreachable value
that is never collected. Always `finally { threadLocal.remove(); }`.

**One-line close:** key unreachable → GC clears → GC enqueues → your next map call unlinks, with an
unbounded gap in the middle — and a value referencing its own key makes the entry immortal.

### Q28. "What are TimSort's invariants, and what was the de Gouw bug?"

**Model answer.** TimSort scans for **natural runs** — maximal ascending or strictly descending
sequences, with descending runs reversed in place — and merges them under a stack discipline. Short
inputs skip all of it: below `MIN_MERGE = 32` it is a binary insertion sort. Above that, runs shorter
than `minRunLength(n)` are extended by insertion sort, where `minRunLength` right-shifts `n` until it
is below 32 while OR-accumulating whether any shifted-out bit was set — so the run length divides the
array into a near-power-of-two number of runs, which is what makes the merges balanced.

The stack invariants, for run lengths held on the pending-run stack, are:

- `runLen[i] > runLen[i+1] + runLen[i+2]`
- `runLen[i+1] > runLen[i+2]`

Maintaining them keeps the merge tree balanced and bounds the stack depth, which is why the stack can
be a fixed-size array sized from `n`.

The **de Gouw bug** (JDK-8072909) is that `mergeCollapse` checked only the top three entries, which
turns out not to preserve the invariant *globally* — a formal analysis using KeY found inputs where
the stack could exceed its allocated depth and produce an
`ArrayIndexOutOfBoundsException`. The detail that makes this a good story: **the JDK's fix enlarged
the stack bound** (for example 19 → 24 and 40 → 49) rather than correcting the merge logic. So the
implementation is still not the one the proof validates; it is the one whose failure mode is now
unreachable in practice.

**If they push:** the user-visible symptom of a *different* problem is
`IllegalArgumentException: Comparison method violates its general contract!`, which is TimSort
detecting that your comparator is not a total order — usually `int`-subtraction overflow. And
stability is what buys TimSort its place: sort by a secondary key, then stably by the primary, and
you get (primary, secondary) ordering for free. Primitives get dual-pivot quicksort instead, because
an `int` has no identity for stability to preserve and comparisons are nearly free.

**One-line close:** run detection with `MIN_MERGE = 32` and two stack invariants;
JDK-8072909 showed the three-entry collapse check does not preserve them globally, and the JDK
enlarged the stack instead of fixing the logic.

### Q29. "How does `ConcurrentHashMap` resize without stopping the world?"

**Model answer. Cooperatively — every thread that touches a bin under migration is conscripted into
doing part of the work.**

A resizing thread claims a contiguous **stride** of bins to migrate, walking **downward** from the
top of the table. `transferIndex` holds the next unclaimed index (stored as index-plus-one), and a
thread claims work with a CAS:
`CAS(transferIndex, nextIndex, max(0, nextIndex - stride))`. The stride is
`(NCPU > 1) ? (n >>> 3) / NCPU : n`, floored at `MIN_TRANSFER_STRIDE = 16` — the floor exists both to
keep the claim CAS from dominating and to avoid two threads working adjacent cache lines. On a
12-core machine, that formula means real parallelism only begins around `n = 2048`.

When a bin has been migrated, the resizer installs a **`ForwardingNode`** in the old table slot:
`hash == MOVED == -1`, holding a reference to `nextTable`, and with a `find` that searches the *new*
table. So a **reader** that lands on a migrated bin follows the forwarding node and completes
correctly — reads never block on a resize.

A **writer** that lands on one calls `helpTransfer`, which registers itself in `sizeCtl` and runs a
full `transfer` pass before retrying its write. That is the elegant part: the thread that would
otherwise have waited becomes an extra resizer.

Two more details worth quoting. Migration reuses the bin's longest uniform tail by reference —
`runBit`/`lastRun` — so only the prefix of a chain is copied. And the lo/hi split rule is
**identical to `HashMap`'s**: `(hash & n) == 0` stays at `i`, otherwise it moves to `i + n`.

**If they push:** this is the case where the honest answer includes what cannot be shown. A
`ForwardingNode` caught mid-resize, two threads simultaneously inside `transfer`, and an in-flight
`sizeCtl` value are all **unobservable** from application code without instrumenting the JVM — so
the right thing is to derive them from the source rather than fabricate a transcript.

**One-line close:** threads CAS-claim strides downward, install a `ForwardingNode` per migrated bin
so readers follow into the new table, and a blocked writer calls `helpTransfer` and becomes a
resizer.

### Q30. "What does `sizeCtl` actually hold?"

**Model answer.** Four states, and one of them is famously misdescribed **by the JDK's own field
comment**.

- `0` — the table has not been created yet.
- `-1` — `initTable()` is in progress.
- **positive** — the resize threshold, `0.75 × capacity`.
- **negative and not −1** — a resize is in flight. And here is where the comment is wrong.

The comment at `ConcurrentHashMap.java:792`–`:799` says the value is
`-(1 + the number of active resizing threads)`, so two resizers would be `-3`. That has not been
true since Java 8 shipped, and essentially every article repeats it. What the code does: the
**first** resizer CASes
`sizeCtl = (resizeStamp(n) << RESIZE_STAMP_SHIFT) + 2` (`addCount` `:2353`, `tryPresize`
`:2413`–`:2414`), and each **helper** CASes `sc + 1` (`addCount` `:2350`, `helpTransfer` `:2373`). So
the **low 16 bits hold `2 + helpers`** and the **high 16 bits hold a stamp identifying which table
size is being resized** — which is what stops a thread from joining a resize that has already
finished and restarted at a different size.

The arithmetic, which is the part that lands in an interview: `resizeStamp(n)` is
`Integer.numberOfLeadingZeros(n) | (1 << 15)` (`:2284`–`:2286`), with `RESIZE_STAMP_BITS = 16`
(`:575`), `RESIZE_STAMP_SHIFT = 16` (`:586`) and `MAX_RESIZERS = 65535` (`:581`). For `n = 16`:
`numberOfLeadingZeros(16) = 27`, so `resizeStamp(16) = 27 | 32768 = 32795`, and `32795 << 16` is
`-2145714176` as a signed `int`. The first resizer therefore sets **`sizeCtl = -2145714174`** — not
`-2`.

The finishing thread identifies itself by testing
`(sc - 2) == resizeStamp(n) << RESIZE_STAMP_SHIFT`, and the new threshold is computed as
`(n << 1) - (n >>> 1)`, which is `0.75 × 2n` without a multiply.

**If they push:** this is the strongest available answer to "how do you know a claim is true?" The
JDK's prose is the source of the error, so agreeing with the comment is not evidence. Read the CAS
sites.

**One-line close:** 0 / −1 / positive threshold / stamped-negative — and during a resize the low 16
bits are `2 + helpers` while the high 16 are a table-size stamp, so for `n = 16` the first resizer
writes `-2145714174`, not the `-2` the field comment implies.

### Q31. "Walk me through `CopyOnWriteArrayList`'s write path."

**Model answer.** One field and one lock. The state is
`private transient volatile Object[] array` (`:110`), and every mutator runs under
`synchronized (lock)` where `lock` is `final transient Object lock = new Object()` (`:107`) — a
**plain monitor, not a `ReentrantLock`**. `add(E)` clones the array to exactly `len + 1` (no growth
factor, no slack), writes the element, and publishes with `setArray`. Reads take nothing at all: a
volatile read of `array` plus an index.

Two details that catch people. `set(int, E)` skips the `.clone()` only when the new value is
*reference-equal* to the old one — but it still calls `setArray` unconditionally, to get the
happens-before edge. And the bulk mutators (`removeIf`, `replaceAll`, `sort`) do exactly **one** copy
for the whole call, not one per element, which is a real reason to prefer them over a loop.

The iterator is a **snapshot**: `COWIterator` holds a private `Object[] snapshot` plus a cursor, so
it can never throw `ConcurrentModificationException`, and `remove`/`set`/`add` on it throw
`UnsupportedOperationException` on every path. That is the property the class was built for —
a listener registry where a listener may deregister itself during dispatch.

**If they push:** the lock type is a version trap. JDK 8u202 declared
`final transient ReentrantLock lock = new ReentrantLock();` (`:97` in that tree); JDK 11.0.27 already
carries the `Object` monitor, so the change landed between 8 and 11 — around 2018 — and the JDK's own
comment explains why: a plain monitor is cheaper and the class needs no `Condition` or `tryLock`. Any
write-up describing a `ReentrantLock` field is describing the old code. And the cost model:
n sequential `add` calls copy `n(n+1)/2` references, so building a 10,000-element list this way
copies about 50 million references.

**One-line close:** a `volatile Object[]` published under a plain `Object` monitor, one full copy per
mutation, and a frozen-array iterator that cannot CME and cannot remove.

### Q32. "How does `ConcurrentSkipListMap` get O(log n) without rotations?"

**Model answer.** With a probabilistic index structure instead of a balanced one. There is a base
list of `Node<K,V>` in key order, and above it a sparse tower of `Index<K,V>` levels that let a
search skip ahead. A lookup descends the levels, moving right while the next key is smaller, and
drops a level when it is not — expected O(log n).

The parameters are hardwired, and the JDK class comment at
`ConcurrentSkipListMap.java:246`–`:251` states them exactly: **`k = 1, p = 0.5`**, meaning "about
**one-quarter** of the nodes have indices; of those that do, half have one level, a quarter two, and
so on, up to a maximum of **62 levels**". The code matches: `doPut` first gates whether a node is
indexed *at all* with `if ((lr & 0x3) == 0)` — a **1-in-4** test — and then grants each *additional*
level at **1-in-2** odds by shifting a random `long` left and testing the sign. So the two numbers
mean different things, and "p = 0.25" alone is wrong: **0.25 is the fraction of nodes that get an
index, 0.5 is the per-level continuation probability.**

Insertion is a single `casNext`. Deletion is two-phase: first CAS the node's `value` to `null`
(logical deletion), then unlink it physically — and *any* thread may complete the unlink, which is
what keeps the structure lock-free without a helper thread.

Why this structure rather than a red-black tree is the interesting half: every skip-list mutation is
a **single-pointer CAS** and the structure is valid at every intermediate state, whereas a tree
rotation must update three or more pointers together, which a single-word CAS cannot do atomically.
Lock-free is natural on a skip list and very hard on a red-black tree.

**If they push:** two version traps. JDK 21 has `Node` and `Index` with `head` as a plain
`Index<K,V>` field and **no `HeadIndex` class** — that was removed in the post-JDK-12 rewrite, so any
description built around `HeadIndex` is stale. And `size()` is **O(n)**: it walks the base list,
because no counter is maintained. Iterators are weakly consistent and never throw CME.

**One-line close:** a base list plus a probabilistic `Index` tower — 1-in-4 nodes indexed at all,
then `p = 0.5` per extra level — with insert as one CAS and delete as mark-then-unlink, which is
exactly what a tree rotation cannot be.

### Q33. "What did you learn from writing your own `HashMap` that reading the source did not teach you?"

**Model answer.** Three things, and they are the kind of answer that only comes from having done it.

**The extension surface is not obvious until you need it.** To make a `MyLinkedHashMap` work on top
of `MyHashMap`, you discover you need exactly seven members exposed: `Node` visibility, `newNode`,
`replacementNode`, and the three `afterNode*` hooks, plus field visibility. Reading `HashMap` you see
seven package-private members; building on it you find out *why each one exists* — and specifically
that missing `newTreeNode`/`replacementTreeNode` silently scrambles encounter order the moment a bin
treeifies.

**Simplifying the tree bin has a measurable price, in the direction you would not guess.** Replacing
the red-black tree bin with a **sorted array** plus binary search gives the same **O(log n) lookup**
— measured at 10.20 ms per 100,000 gets against the JDK's 10.42 ms at 20,000 colliding keys, so
genuinely equal. But insertion becomes **O(n)** because the array must shift: filling those 20,000
keys took 222 ms against the JDK's 1.43 ms. So the build bounds lookup and not insert, where the JDK
bounds both — and that asymmetry is invisible from reading the code, where both look like "a sorted
structure".

**Lazy allocation is load-bearing, not a micro-optimisation.** `resize()` being both the allocator
and the grower means there is no `initTable` and no null-table branch scattered through `put`; you
only appreciate that when you write the version that *does* have the branch everywhere.

**If they push:** the honest diffs of any hand-built version are worth stating — no `Serializable`,
no `clone`, no `Spliterator`, no view `toArray` specialisations, and `ArraysSupport.newLength` cannot
be reproduced at all because `jdk.internal.util` is not exported. And the differential test is what
makes the exercise worth anything: 200,000 random operations against `java.util.HashMap` with a
fixed seed, comparing the return value and `size` after **every** call, then `equals` both ways at
the end.

**One-line close:** that the extension surface is seven specific members, that a sorted-array bin
matches the tree on lookup but is O(n) on insert, and that a differential test against the real class
is the only way to know your version is right.

### Q34. "How do the Java 21 reversed views work internally?"

**Model answer.** They are thin objects holding one reference to the source, with index or
direction inverted on the way through.

`LinkedHashMap.reversed()` returns a `ReversedLinkedHashMapView` holding a single `base` field. Its
own `keySet`/`values`/`entrySet` are sub-views of the same map, so writes propagate both ways. And
the detail that surprises people: its `reversed()` is literally `return base;`
(`LinkedHashMap.java:1224`), so **`m.reversed().reversed() == m` is `true`** and double reversal
allocates nothing.

`List.reversed()` returns a `ReverseOrderListView`, created by
`ReverseOrderListView.of(this, true)`, which **unwraps** when handed an existing view — so double
reversal is identity for lists too. `get(i)` becomes `base.get(size - i - 1)`, `indexOf` and
`lastIndexOf` swap, `view.add(x)` becomes `base.add(0, x)`, and `view.sort(c)` becomes
`base.sort(reverseOrder(c))`. Its immutable counterpart is `AbstractImmutableList.reversed()`, which
passes `modifiable = false`, and every mutator calls `checkModifiable()` **first**, so the view
throws before reaching the base.

`TreeMap` is the exception to know: `reversed()` **is** `descendingMap()` (the `NavigableMap` default
returns it), and `descendingMap()` is one-slot cached — but `descendingMap().descendingMap()` builds
a fresh `AscendingSubMap`, so it is `equals` to the original and **not `==`**. `TreeSet.descendingSet()`
is not cached at all; every call allocates.

**If they push:** two consequences. `ReverseOrderListView.subList` **silently loses**
`RandomAccess`, because the `Rand` subclass that carries the marker is not used for sublists — so a
`Collections` method that branches on `instanceof RandomAccess` quietly takes the iterator path.
And neither `SubList` nor `ReverseOrderListView` is `Serializable`, which is documented in the
latter's javadoc.

**One-line close:** one `base` field with the index or direction flipped; double reversal is identity
for `List` and `LinkedHashMap` because the view's `reversed()` returns the base, and it is *not* for
`TreeMap.descendingMap()`.

### Q35. "How does `String.hashCode` work, and what is `hashIsZero`?"

**Model answer.** `s[0]·31^(n−1) + s[1]·31^(n−2) + … + s[n−1]`, computed as a loop of
`h = 31 * h + s[i]`. 31 is an odd prime, and the JIT turns the multiply into `(h << 5) - h` because
`31 = 2⁵ − 1`.

The result is **cached** in a non-`volatile` `int hash` field — a benign data race: two threads may
both compute it, but they compute the same value, so a torn read is impossible for an `int` and the
worst case is duplicated work. `hashIsZero` is a second `boolean` field added in **Java 13**
(JDK-8054307) to solve one specific problem: a `String` whose hash genuinely *is* 0 — the empty
string, or `"\u0000"` — would otherwise be recomputed on every call, because `hash == 0` was the
"not yet computed" sentinel. With the flag, "computed and zero" and "not computed" are distinct.

The consequence to volunteer is the security one: because the function is public, fixed and
unseeded, collisions are **engineerable**. `"Aa"` and `"BB"` both hash to 2112, and because the
function is a 31-fold, any concatenation of colliding blocks also collides — giving 2ᵏ colliding
strings of length 2k for free. That is the primitive behind CVE-2011-4858, and it is why Java 8's
treeification exists.

**If they push:** the parallel facts for the other JDK types, because they come up in the same
breath. `Integer.hashCode()` is the value itself. `Long`'s is `(int)(value ^ (value >>> 32))`.
`Double`'s goes through `doubleToLongBits` then xor-folds, so `0.0` and `-0.0` hash differently.
`Boolean`'s is the arbitrary 1231/1237. And `Enum.hashCode()` is declared **`public final`** and is
identity-based, so you cannot give an enum a value-based hash — which is exactly why enum-keyed
`HashMap` iteration order is stable within a run and unspecified across runs, and why `EnumMap`
exists.

**One-line close:** a 31-fold cached in a non-volatile field, with `hashIsZero` (Java 13)
distinguishing a real hash of 0 from "not computed" — and the function being public and unseeded is
what makes collisions engineerable.

### Q36. "How are the immutable collections serialized?"

**Model answer.** Through a **serialization proxy**, and the class it names is worth getting right.
Every `List.of`/`Set.of`/`Map.of` implementation has a `writeReplace` that emits a
`java.util.CollSer` — a package-private **top-level** class, so `java.util.CollSer` and *not*
`ImmutableCollections$CollSer` — carrying a tag and a flat element array. Its
`serialVersionUID` is `6309168927139932177L`, and the implementation classes declare none of their
own.

The tags are `1 = IMM_LIST`, `2 = IMM_SET`, `3 = IMM_MAP`, `4 = IMM_LIST_NULLS`, read as `tag & 0xff`
with the high 24 bits reserved. `IMM_LIST_NULLS` was added for `Stream.toList()` in Java 16, because
that method returns a `ListN` with `allowNulls == true` and the old tag could not express it.
`readResolve` re-runs the factory in the receiving JVM, which means it **re-validates**: a stream
carrying duplicate elements for a `Set.of` produces an `IllegalArgumentException` internally, caught
and rethrown as `InvalidObjectException`.

The implementation classes' own `readObject` throws
`InvalidObjectException("not serial proxy")` — and that path is genuinely reachable, not defensive
dead code, if someone hand-crafts a stream.

**If they push:** two consequences. A round-tripped `Set.of` iterates in the **receiving** JVM's
`SALT32L` order, not the sender's — so serialized order is not a channel you can rely on. And what
is *not* serializable: `Map.of(...).keySet()` (an anonymous `AbstractMap$1`), `SubList`,
`ReverseOrderListView`, and `KeyValueHolder` (what `Map.entry` returns) — so a DTO holding
`Map.entry(k, v)` will fail to serialize while one holding a `SimpleEntry` succeeds.

The wider serialization facts for collections follow the same principle: the storage array is
`transient` everywhere, because layout is not portable. `ArrayList` writes `size` plus the live
elements so it does not serialize unused capacity; `HashMap` writes entries and re-`put`s them,
because bucket positions depend on `hashCode()` values the reading JVM may compute differently;
`TreeMap` writes its comparator, which must therefore be `Serializable` — a lambda comparator makes
the map unserializable at runtime.

**One-line close:** `writeReplace` to a package-private top-level `java.util.CollSer` with a tag plus
a flat array, `readResolve` re-running the factory and re-validating — and the receiving JVM's salt
decides the iteration order.

## Pitfalls

### Reciting the `sizeCtl` encoding from the JDK's own field comment

**Wrong**

> "`sizeCtl` is `-1` while initialising and `-(1 + the number of active resizing threads)` during a
> resize, so two resizers means `-3`."

**Right**

> "The first resizer CASes `(resizeStamp(n) << 16) + 2` and each helper CASes `sc + 1`, so the low
> 16 bits are `2 + helpers` and the high 16 are a table-size stamp. For `n = 16`,
> `numberOfLeadingZeros(16) = 27`, `resizeStamp(16) = 27 | 32768 = 32795`, and `32795 << 16` is
> `-2145714176`, so the first resizer writes `sizeCtl = -2145714174`."

**Why people believe it:** the field comment at `ConcurrentHashMap.java:792`–`:799` says exactly the
wrong thing, and it has said so since Java 8. This is the one place in the topic where agreeing with
the JDK's prose is *evidence of not having read the code*, and it is worth saying out loud in an
interview for that reason.

### Saying "segments were removed in Java 8"

**Wrong**

> "Java 7's `ConcurrentHashMap` used 16 `Segment` locks; Java 8 removed segments entirely and
> switched to per-bin locking."

The second clause is wrong twice: the *class* is still there, and what was abandoned was segment
*locking*.

**Right**

> "Segment **locking** was abandoned in Java 8 in favour of per-bin CAS-and-monitor. But
> `static class Segment<K,V> extends ReentrantLock implements Serializable` **survives in JDK 21** at
> `ConcurrentHashMap.java:1380`, retained purely for serialization compatibility — same
> `serialVersionUID`, same javadoc as the JDK 8 stub. It participates in no operation, and a Java 8+
> serialized `ConcurrentHashMap` still writes segment-shaped data."

**Why people believe it:** the behavioural change is the memorable part, and nobody greps for a class
that does nothing. Naming the surviving stub, and the reason it survives, is a much stronger answer
than the version everyone gives.

## Cheat sheet

| Question | The one-line answer |
|---|---|
| Amortised proof, aggregate | total copies ≈ `n·g/(g−1)` — 3n at 1.5×, 2n at 2× |
| Amortised proof, accounting | 4 credits per `add` at 1.5×, 3 at 2× |
| Amortised proof, potential | `Φ_g = (g/(g−1))s − (1/(g−1))c`; the textbook `2s − c` is doubling-only |
| Amortised vs average | amortised is adversary-proof over a sequence; average assumes a distribution |
| CHM write path | `casTabAt` for an empty bin; `synchronized (f)` on the bin head, re-checking `tabAt` inside |
| CHM read path | volatile reads only — no lock, no CAS, never a CME |
| Reserved node hashes | `MOVED = -1`, `TREEBIN = -2`, `RESERVED = -3` |
| `spread` in CHM | `(h ^ (h >>> 16)) & 0x7fffffff` — clears the sign bit so user hashes cannot collide with those |
| CHM nulls | banned for **keys and values**, one guard at `:1011` |
| Why CHM bans null | `get` returning null cannot be disambiguated by a later `containsKey` without a lock |
| CHM `size()` | an estimate: unlocked sum of `baseCount` + `CounterCell[]`; clamps at `Integer.MAX_VALUE` |
| CHM `mappingCount()` | `long`, no clamp — the method to use |
| `@Contended` | pads each `CounterCell` to its own cache line; ~8× array memory, no false sharing |
| Red-black invariants | red/black; black root; black NILs; no red-red; equal black height |
| Height bound | `h ≤ 2·log₂(n + 1)` |
| AVL vs red-black | AVL ~`1.44 log₂ n` (better reads), red-black cheaper fix-ups (better writes) |
| Lock-free on a skip list vs a tree | one-pointer CAS vs a rotation needing 3+ pointers together |
| `HashSet` | `HashMap` field + one JVM-wide `PRESENT`; `add` is `put(e, PRESENT) == null` |
| `LinkedHashSet` ctor | package-private `HashSet(int, float, boolean dummy)`; the boolean carries no data |
| Pattern breakers | `CopyOnWriteArraySet` (a list, O(n)) and `EnumSet` (a bitmask) |
| `EnumSet` split | `universe.length <= 64` → `RegularEnumSet` (one `long`), else `JumboEnumSet` (`long[]`) |
| `EnumSet` bulk ops | `|=`, `&= ~`, `&=` — one instruction; mismatched type: `retainAll` silently empties |
| `EnumSet` mask | `-1L >>> -universe.length`, recomputed inline; **no `mask` field** |
| `IdentityHashMap` storage | one flat `Object[]`, key at `2i`, value at `2i+1`, **no entry class** |
| Its index function | `((h << 1) - (h << 8)) & (len - 1)` — multiplier `-254`, so always even |
| Its probe | `nextKeyIndex` = `i + 2`, stop at the first null key; table must never fill |
| Its deletion | `closeDeletion`, Knuth back-shift, no tombstones — can relocate several entries |
| Its ctor argument | `expectedMaxSize`; default map resizes on the **22nd** put; load factor 2/3 of capacity |
| `WeakHashMap` clearing | drop key → GC clears → GC enqueues → **next map call** expunges |
| Its expunge funnels | `getTable()`, `size()`, `resize()`; `clear()` drains by hand; iteration expunges once in the ctor |
| Why the entry caches `hash` | the key is already null at expunge time and cannot be re-hashed |
| The guaranteed leak | value references its own key (or a two-entry cycle) |
| `ThreadLocalMap.Entry` | same weak-key shape, **no queue** — always `finally { tl.remove(); }` |
| TimSort | run detection, `MIN_MERGE = 32`, `minRunLength` shift-and-OR |
| Its stack invariants | `runLen[i] > runLen[i+1] + runLen[i+2]` and `runLen[i+1] > runLen[i+2]` |
| de Gouw bug | JDK-8072909; the JDK **enlarged the stack bound** rather than fixing `mergeCollapse` |
| CHM resize claim | CAS `transferIndex` downward; stride `(n >>> 3) / NCPU`, floor `MIN_TRANSFER_STRIDE = 16` |
| `ForwardingNode` | `hash == MOVED`, holds `nextTable`, its `find` searches the new table |
| `helpTransfer` | turns a blocked writer into an extra resizer |
| CHM split rule | `(hash & n) == 0` → stay at `i`, else `i + n` — identical to `HashMap` |
| New CHM threshold | `(n << 1) - (n >>> 1)` = `0.75 × 2n` without a multiply |
| `sizeCtl` states | 0 / −1 / positive threshold / stamped-negative |
| `sizeCtl` during resize | low 16 = `2 + helpers`, high 16 = table-size stamp; **not** `-(1 + resizers)` |
| `sizeCtl` for `n = 16` | `resizeStamp = 32795`, `32795 << 16 = -2145714176`, first resizer writes `-2145714174` |
| CoW state and lock | `volatile Object[] array` (`:110`) under `final transient Object lock` (`:107`) |
| CoW lock version trap | `ReentrantLock` in JDK 8, plain monitor by 11 |
| CoW `add` | copies exactly `len + 1`; bulk mutators copy **once** for the whole call |
| `COWIterator` | frozen array; never CMEs; `remove`/`set`/`add` always throw |
| `ConcurrentSkipListMap` | `Node` base list + probabilistic `Index` levels; **no `HeadIndex`** in JDK 21 |
| Its two probabilities | 1-in-4 chance of any index (`lr & 0x3`), then `p = 0.5` per extra level, max 62 |
| Its deletion | CAS value to `null`, then unlink — any thread may finish it |
| Its `size()` | O(n), no counter |
| `Segment` in JDK 21 | still present at `:1380` as a serialization stub — segment *locking* was abandoned, not the class |
| Sorted-array bin vs tree bin | equal O(log n) lookup (10.20 vs 10.42 ms), but O(n) insert (222 vs 1.43 ms) |
| `LinkedHashMap.reversed()` | `ReversedLinkedHashMapView` with one `base` field; its `reversed()` is `return base;` |
| Double reversal | identity for `List` and `LinkedHashMap`; **not** for `TreeMap.descendingMap()` |
| `ReverseOrderListView.subList` | silently loses `RandomAccess` |
| `String.hashCode` | 31-fold, cached in a non-volatile `int`; `31 = 2⁵ − 1` so the JIT shifts |
| `hashIsZero` | Java 13 (JDK-8054307) — distinguishes a real hash of 0 from "not computed" |
| Engineered collisions | `"Aa"`/`"BB"` = 2112; 2ᵏ colliding strings of length 2k |
| `Enum.hashCode()` | `public final`, identity-based — unoverridable, hence `EnumMap` |
| Immutable serialization | `writeReplace` → `java.util.CollSer` (top-level, package-private), UID `6309168927139932177L` |
| Its tags | 1 `IMM_LIST`, 2 `IMM_SET`, 3 `IMM_MAP`, 4 `IMM_LIST_NULLS` (Java 16, for `Stream.toList()`) |
| Impl `readObject` | throws `InvalidObjectException("not serial proxy")` — reachable |
| Not serializable | `Map.of(...).keySet()`, `SubList`, `ReverseOrderListView`, `KeyValueHolder` |
| Unobservable from application code | in-flight `sizeCtl`, a mid-resize `ForwardingNode`, two threads inside `transfer`, a contended `CounterCell[]`, a `TreeBin` reader during rotation, the two-thread `computeIfAbsent` deadlock |

## Self-test

**Q1.** Why is `ArrayList.add`'s amortised O(1) a stronger claim than `HashMap.get`'s average O(1)?

<details><summary>Answer</summary>

Because amortised quantifies over a *sequence* with no assumption about the input, while average
quantifies over a *distribution* of inputs. No sequence of n appends can cost more than O(n) — an
adversary choosing your data cannot change that, because the bound comes from the geometric growth
schedule. `HashMap.get`'s O(1) assumes the keys spread, and an adversary who controls hash codes
breaks it outright: that is the entire hash-collision denial-of-service attack. Both are "O(1)" in
the cost table and only one of them survives an attacker.

</details>

**Q2.** Two threads write to a `ConcurrentHashMap` and one of them triggers a resize. What does the
other one do?

<details><summary>Answer</summary>

If its bin has not been migrated yet, nothing special — it CASes or locks that bin as usual. If it
lands on a bin whose slot now holds a `ForwardingNode` (`hash == MOVED`), it calls `helpTransfer`,
which registers it in `sizeCtl` (CAS of `sc + 1`), makes it run a full `transfer` pass claiming
strides via `transferIndex`, and then returns the new table so the write can be retried against it.
So a writer that would have blocked instead becomes an extra resizer. A *reader* in the same
situation never blocks at all: `ForwardingNode.find` searches `nextTable` on its behalf.

</details>

**Q3.** `chm.size()` returns 1,000 and you immediately iterate and count 1,002 entries. Is this a
bug?

<details><summary>Answer</summary>

No. `size()` is documented as an estimate. It is `sumCount()`, an unlocked sum of `baseCount` plus
every non-null `CounterCell`, so it can read one stripe before an update and another after; and even
a perfect read is stale the moment it returns if writers are active. Iteration is separately weakly
consistent — it walks live state and may observe entries inserted after it started. If you need a
count for a large map use `mappingCount()`, which returns a `long` and does not clamp at
`Integer.MAX_VALUE` the way `size()` does; if you need an exact count you need exclusive access,
which is not what this class is for.

</details>

**Q4.** Your `WeakHashMap<Config, Metrics>` shows entries surviving long after their keys went out
of scope, and a heap dump shows the `Config` objects still reachable. Where do you look?

<details><summary>Answer</summary>

At the **values**. `WeakHashMap` holds keys weakly and values *strongly*, so any path
`map → table → Entry.value → … → key` keeps the key strongly reachable and the entry immortal. The
usual causes are a back-reference field on the value, a listener the value registered, or a
two-entry cycle where V1 references K2 and V2 references K1 — the second is nastier because no value
holds *its own* key. Check also whether the keys are of a type that is never unreachable at all:
`String` literals and `intern()`ed strings, boxed `Integer`s in `[-128, 127]`, `Class` objects and
enum constants all outlive the map. Fixes: remove the back-reference, wrap the value in a
`WeakReference`, or stop using `WeakHashMap` and use Caffeine with an explicit bound.

</details>

**Q5.** Someone says `ConcurrentSkipListMap` uses "p = 0.25 for its levels". Correct them precisely.

<details><summary>Answer</summary>

Two parameters are being conflated. The class comment at `ConcurrentSkipListMap.java:246`–`:251`
states the hardwired values as `k = 1, p = 0.5`, and explains that this makes "about one-quarter of
the nodes have indices" — so **0.25 is the fraction of nodes that get an index at all**, and
**0.5 is the probability of each additional level given that a node is indexed**. The code matches:
`doPut` gates indexing with `if ((lr & 0x3) == 0)`, a 1-in-4 test, then grants extra levels at
1-in-2 odds by shifting a random `long`, up to a maximum of 62 levels. While you are correcting
them, the other stale thing to check is `HeadIndex`: JDK 21 has no such class — `head` is a plain
`Index<K,V>` field since the post-JDK-12 rewrite.

</details>

**Q6.** Why can `Map.entry(k, v)` not be put in a serialized DTO, while `new SimpleEntry<>(k, v)`
can?

<details><summary>Answer</summary>

Because `Map.entry` returns a `java.util.KeyValueHolder`, which is **not** `Serializable` —
deliberately, since it is an immutable value-like holder — while
`AbstractMap.SimpleEntry` and `SimpleImmutableEntry` both are. The other differences are worth
knowing in the same breath: `Map.entry` rejects null keys and values at construction where
`SimpleEntry` allows them, and `SimpleEntry.setValue` mutates its own field only (it writes through
to nothing), unlike an entry obtained from a `HashMap` iterator, which writes into the map's actual
node. `Map.Entry.copyOf(e)` (Java 17) returns a `KeyValueHolder` too, and returns the same instance
if the argument already is one.

</details>

---

**Leaves covered:** 5.1.14, 5.1.19, 5.1.20, 5.1.21, 5.1.28 (5 leaves)
**Leaves deferred:** none
**Diagrams included:** none
**Target version:** Java 21 LTS
**Lines:** 812
