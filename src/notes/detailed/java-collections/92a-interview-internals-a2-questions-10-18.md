# 02 Java Collections — Interview, INTERNALS tier — questions 10–18 (§5.1)

**Target version: Java 21 LTS.** | [Index](00-index.md)
Previous: [92-interview-internals.md](92-interview-internals.md) · Next: [92b-interview-internals-b-questions-19-36.md](92b-interview-internals-b-questions-19-36.md)

Part 2 of the INTERNALS question set. [92](92-interview-internals.md) carries the tier summary
table and the nine canonical `HashMap` questions (§5.1.1–5.1.9); this file carries questions 10–18,
one source-level question per remaining subject folder. Questions 19–36 are in
[92b](92b-interview-internals-b-questions-19-36.md), the puzzles in
[92c](92c-interview-internals-c-puzzles-and-checklist.md), and the atomic concept checklist in
[92d](92d-interview-internals-d-atomic-concept-checklist.md).

Every line number is JDK 21 unless stated.

## Q&A 10–18

### Q10. "Walk me through `ArrayList.grow`."

**Model answer.** The interesting part is before the arithmetic: `ArrayList` has **two distinct
empty arrays**, both `{}`, and it tells them apart by **reference identity**.
`EMPTY_ELEMENTDATA` (`:123`) is used by `new ArrayList<>(0)` and the empty-collection constructor;
`DEFAULTCAPACITY_EMPTY_ELEMENTDATA` (`:130`) is used by the no-arg constructor. The array identity
*is* the flag for "should the first add inflate to 10?" — there is no boolean.

`grow(minCapacity)` (`:231`) delegates to
`ArraysSupport.newLength(oldCapacity, minCapacity - oldCapacity, oldCapacity >> 1)`, i.e. minimum
growth and *preferred* growth, and `newLength` returns `oldLength + max(minGrowth, prefGrowth)`. So
the 1.5× is a *preference* that a large `addAll` overrides: `addAll` grows to exactly
`size + numNew` with no headroom.

The else-branch of `grow` handles the defaulted-empty case with
`Math.max(DEFAULT_CAPACITY, minCapacity)` — which is how the no-arg list becomes 10 — while
`new ArrayList<>(0)` gets `newLength(0, 1, 0)` and becomes **1**, giving the entirely different
ladder 1, 2, 3, 4, 6, 9, 13.

The ceiling is `SOFT_MAX_ARRAY_LENGTH = Integer.MAX_VALUE - 8` (`ArraysSupport.java:692`); beyond it
`hugeLength` either returns `max(SOFT_MAX, minLength)` or throws `OutOfMemoryError`. The `- 8` is
headroom for array header words on some VMs.

**If they push:** capacity is not a field — it is `elementData.length`, with no accessor. And two
different OOMEs are reachable: `Requested array size exceeds VM limit` for a length past the VM's
maximum, and plain `Java heap space` for a legal length with no room. Pre-JDK-17 the arithmetic lived
in `ArrayList` itself as `newCapacity`/`hugeCapacity` with a local `MAX_ARRAY_SIZE`, which is why
older write-ups quote different names.

**One-line close:** two identity-distinguished empty sentinels, then
`newLength(old, minGrowth, old >> 1)` — so 1.5× is a preference, and a bulk add overrides it exactly.

### Q11. "How does `ArrayDeque` avoid a `size` field?"

**Model answer.** It derives size from its two indices: `sub(tail, head, elements.length)`. The
invariant is that `head` is the first element and `tail` is the **next free slot**, so
`elements[tail]` is always `null` and `head == tail` means empty. That one always-empty slot is why
`new ArrayDeque<>()` allocates **17** slots for 16 usable elements, and why `new ArrayDeque<>(n)`
allocates `n + 1`.

Wraparound is three static helpers — `inc`, `dec`, `sub` — each one branch, no `%`. `addFirst` moves
`head` then writes; `addLast` writes then moves `tail`; growth triggers *after* the write, when
`head == tail`.

`grow` computes `jump = oldCapacity < 64 ? oldCapacity + 2 : oldCapacity >> 1` — so it roughly
doubles while small and then grows 50%, giving 17 → 36 → 74 → 111 → 166 from the default. After the
copy, if the contents were wrapped (`tail < head`, or `tail == head` with a non-null slot at `head`)
it slides the head leg forward by `newCapacity - oldCapacity` so the elements are contiguous again.

**If they push:** the version history is two changes nine releases apart, and most write-ups collapse
them into one. The **power-of-two capacity and mask** are **JDK 8 only** — JDK 9 already has
`inc`/`dec`/`sub` and no mask. The **no-arg capacity change from 16 to 17** landed in **JDK 12**:
8u202, 9 and 11.0.27 all allocate `new Object[16]`, while 12 onward allocate `new Object[16 + 1]`.
So before JDK 12 a default `ArrayDeque` held only 15 elements despite its javadoc promising 16.

Also: there is **no `modCount`**. Comodification detection is partial — `nonNullElementAt` throws
CME when it finds a null slot where an element should be — which makes `ArrayDeque` weaker at
fail-fast than `ArrayList`, and it is the mechanical reason `null` elements are banned.

**One-line close:** `head`/`tail` with one slot always empty, so `size` is arithmetic — capacity 17,
`inc`/`dec`/`sub` instead of a mask since JDK 9, and 16→17 only in JDK 12.

### Q12. "Why does `PriorityQueue` have two separate sift methods, and what does `removeAt` return?"

**Model answer.** Two sifts because of **JIT monomorphism**. `siftUp` and `siftDown` each exist in
a comparator variant and a `Comparable` variant (`siftUpUsingComparator`/`siftUpComparable` and the
same for down), chosen once per call by whether `comparator == null`. Merging them would put a
megamorphic call site on the hot path — the JVM could not inline the comparison — so the JDK
duplicates the loop instead. `TreeMap` does the same thing with `getEntry` and
`getEntryUsingComparator`.

Neither sift swaps. Both move a **hole**: `siftUp` walks toward the root shifting parents down and
writes the element once at the end, `log₂ n` comparisons and `d + 1` writes. `siftDown` costs about
`2·log₂ n` comparisons because each level needs one to pick the smaller child and one to decide
whether to continue.

`removeAt(i)` is the subtle one. It moves the last element into slot `i` and sifts it down; if it
did not move (`es[i] == moved`), it sifts it **up** as well. And its return value encodes what
happened: `null` means nothing that was *before* index `i` moved, and a non-null return is the
element that **climbed past** `i`. That matters because a live iterator has already walked past
index `i` and would otherwise never see it.

Which is why `PriorityQueue.Itr` carries a `forgetMeNot` deque: elements relocated behind the cursor
are stashed there and delivered after the array walk finishes, and `hasNext()` is
`cursor < size || (forgetMeNot != null && !forgetMeNot.isEmpty())`. The identity tests in `removeAt`
are `==`, never `equals`, because duplicates are legal.

**If they push:** `heapify` is the O(n) construction — `for (int i = (n >>> 1) - 1; i >= 0; i--)
siftDown(i, es[i])`, backwards because `siftDown` requires valid subtrees below. The bound comes from
`Σ h/2^h = 2`. And it is reachable **only** through the `Collection` constructor: `addAll` is an
`offer` loop and therefore O(n log n).

**One-line close:** two sifts to keep each call site monomorphic for the JIT, and `removeAt` returns
the element that climbed past the hole so the iterator can replay it from `forgetMeNot`.

### Q13. "Walk me through `TreeMap.deleteEntry`."

**Model answer.** The trick is that it never deletes a node with two children. If `p` has both, it
finds `p`'s **successor** `s`, copies `s`'s key and value *into* `p`, and then deletes `s` instead —
`p.key = s.key; p.value = s.value; p = s;`. The successor of a two-child node is the leftmost node of
its right subtree, so it has at most one child by construction. No pointer surgery happens in that
block; it is a content copy.

Then the replacement is `p.left != null ? p.left : p.right`, at most one non-null. The node is
spliced out, and **`fixAfterDeletion` runs only if the physically removed node was BLACK** — removing
a red node cannot change any path's black height, so there is nothing to repair.

`fixAfterDeletion` itself is a single `while` loop with one `if (x == leftOf(parentOf(x)))` split, and
both branches implement the same four logical cases mirrored: sibling red; sibling black with both
children black; sibling black with the near child red and the far child black; sibling black with the
far child red, which terminates unconditionally by setting `x = root`. Four cases × two mirrors = eight
code branches — not, as often stated, six distinct cases.

**If they push:** `successor(t)` has two branches, and the second is the one to know: when
`t.right == null`, it climbs while `t` is a *right* child, returning the first ancestor reached via a
left-child link. A single call is O(log n) worst case, but a full in-order traversal is O(n) total —
each edge is traversed at most once down and once up — so the amortised cost per step is O(1). That
is why iterating a `TreeMap` is O(n) and not O(n log n).

And the one-off worth quoting: `buildFromSorted` builds a balanced tree from sorted input in
**O(n)** with zero comparisons and zero rotations, colouring one level red by arithmetic
(`computeRedLevel`). It is reachable from the `TreeMap(SortedMap)` constructor, from `putAll` when the
target is empty and the source is a compatible `SortedMap`, and from deserialization — so
`new TreeMap<>(sortedMap)` is asymptotically better than a `put` loop.

**One-line close:** two-child deletion copies the successor's contents up and deletes the successor,
then `fixAfterDeletion` runs only if the removed node was black — four cases, mirrored.

### Q14. "How does `LinkedHashMap` hook into `HashMap` without `HashMap` knowing?"

**Model answer.** Through seven package-private members, and the reason it works is that
`HashMap.putVal` **never writes `new Node<>` directly**.

Four are allocation factories: `newNode`, `replacementNode`, `newTreeNode`,
`replacementTreeNode`. `LinkedHashMap` overrides all four — `new*` calls `linkNodeAtEnd` because a
new entry belongs at the end of the encounter order, while `replacement*` calls `transferLinks`
because a substituted node must inherit the old one's position. You need all four rather than one,
because treeify and untreeify **re-box** nodes: miss `newTreeNode`/`replacementTreeNode` and the
encounter order scrambles the moment a bin reaches size 8.

Three are hooks, empty in `HashMap` at `:1941`–`:1943`: `afterNodeAccess`, `afterNodeInsertion(boolean
evict)`, `afterNodeRemoval`. `afterNodeInsertion` is the eviction trigger — its three guards are
`evict`, `head != null`, and `removeEldestEntry(head)` — and `afterNodeAccess` is the access-order
relink, six pointer writes plus `++modCount`.

The `Entry` type adds `before` and `after` to `HashMap.Node`, so it is one object per entry and 40
bytes rather than 32. Note the odd inheritance: `HashMap.TreeNode extends LinkedHashMap.Entry`, so a
plain `HashMap`'s tree nodes carry `before`/`after` fields that are always null.

**If they push:** two version and precision points. The append method is **`linkNodeAtEnd`** in JDK
21 (`LinkedHashMap.java:236`), renamed from `linkNodeLast` (JDK 8 `:222`, JDK 17 `:223`) when
`putFirst`/`putLast` arrived with `SequencedMap`; the JDK 8 body is exactly the JDK 21 method's
`else` arm. And `afterNodeAccess` has **eight** call sites in JDK 21's `HashMap` — 663, 1166, 1178,
1223, 1234, 1273, 1329, 1400 — so `putIfAbsent` and `computeIfAbsent` **on an already-present key
also relink**, while `containsKey` and `Entry.setValue` do not. The javadoc's `get`/`getOrDefault`
framing is incomplete.

A detail for the source-reading question: `afterNodeAccess`'s `else last = b;` arm is provably
unreachable. The method only enters that block when `(last = tail) != e`, so `e` is not the tail, so
`e` has a successor, so `a = p.after` is never null and the `if (a != null)` branch always wins. The
same property holds in JDK 8's guard, so it is long-standing defensive dead code rather than a JDK 21
regression.

**One-line close:** four node factories plus three `afterNode*` hooks, all package-private — and you
need all four factories because treeify re-boxes nodes.

### Q15. "What does `trySplit` promise, and which characteristics matter?"

**Model answer.** `trySplit` returns a **disjoint prefix** of the remaining elements and leaves the
rest in the receiver, or returns `null` to mean "I am a leaf, stop splitting". Together the two must
cover exactly what the original covered — that is the whole contract, and it is why a spliterator
can be handed to fork/join.

The characteristics that decide whether parallelism can work are `SIZED` and `SUBSIZED`. `SIZED`
means `estimateSize()` is exact; `SUBSIZED` means it will still be exact for **both halves after a
split**, which is what lets the framework pre-size output arrays. `ArrayList` and the immutable lists
have both. `HashSet` and `TreeSet` are `SIZED` but **not** `SUBSIZED`, because a split by
table-index range cannot say how many elements a range holds.

Split quality is the other half, and it is structural, not a tuning matter. `ArrayList` splits at
`(lo + hi) >>> 1` in constant time with no elements moved. `LinkedList` cannot index, so its
`trySplit` **walks** the chain and copies a prefix into an `Object[]`, sized `BATCH_UNIT = 1 << 10`
and growing per call up to `MAX_BATCH = 1 << 25`. For a list under 1,024 elements the first batch
takes everything and there is no parallelism at all.

**If they push:** `Spliterator` is also the bridge to streams — `stream()` is
`StreamSupport.stream(spliterator(), false)` — so a custom collection gets streams for free once it
has a spliterator. The three things a hand-written one must get right are: an honest size (or do not
claim `SIZED`), honest characteristics (`IMMUTABLE` or `CONCURRENT` means it must never throw CME),
and genuinely disjoint splits. And the danger nobody sees coming: `parallelStream()` uses the shared
`ForkJoinPool.commonPool()`, so a blocking operation inside a parallel stream starves every other
parallel stream in the JVM.

**One-line close:** a disjoint prefix or `null`; `SIZED` plus `SUBSIZED` is what makes a split
useful, and `ArrayList` splits in O(1) where `LinkedList` copies a batch.

### Q16. "How are `List.of` and `Map.of` implemented?"

**Model answer.** As size-specialised classes with no `Node` objects anywhere.
`List.of` gives the shared `EMPTY_LIST` at arity 0, a `List12` at 1 or 2, and a `ListN` at 3 or
more. `List12` has exactly two fields, `e0` and `e1`, no array and no size field — `size()` is
`e1 != EMPTY ? 2 : 1`, comparing against a private sentinel object rather than `null` so that
HotSpot can constant-fold the `@Stable` fields. `Set.of` mirrors it with `Set12`/`SetN`. `Map.of`
gives `Map1` for one pair and `MapN` for everything else — **there is no `Map2`**, which is worth
knowing because `List12` really does cover both sizes.

`SetN` and `MapN` use **open addressing with linear probing** and no chaining, no tombstones (they
are immutable, so nothing is ever deleted) and no tree fallback. The table is oversized by
`EXPAND_FACTOR = 2`, and that constant is a **correctness requirement, not a tuning knob**: at
factor 1 a lookup miss on a full table would loop forever rather than terminate. `probe` returns `i`
for a hit and `-(i + 1)` for a miss, so one call serves both "is it present" and "where does it go".
`MapN` interleaves keys and values in one `Object[]` — key at `2i`, value at `2i + 1` — so `get` is
one probe plus `table[i + 1]`.

The arity overloads are about allocation, not speed: arities 0–2 allocate **no array at all**, 3–10
adopt the varargs array via `listFromTrustedArray` with **no defensive copy**, and `of(E...)` copies,
because a caller who kept the array could otherwise mutate a supposedly immutable list. That copy is
also TOCTOU-safe — it copies and null-checks in one pass so no slot is read twice.

**If they push:** the salt. `SALT32L` is derived from `System.nanoTime()` at class initialisation, and
`REVERSE` from its low bit, and they are consumed by **iterators only** — `SetNIterator` and
`MapNIterator` use a multiply-shift to pick a starting slot and a direction. Placement and lookup
(`probe`) are entirely unsalted, so `contains` is deterministic while iteration order changes on
every JVM start, by design, to break code that came to depend on it. And CDS does **not** pin it: the
build-derived seed applies under `-Xshare:dump`, not at runtime.

**One-line close:** size-specialised classes with no nodes, open addressing at `EXPAND_FACTOR = 2`
for correctness, and a per-JVM-run salt that reorders **iteration only**.

### Q17. "Where do the 32, 40 and 56 bytes come from?"

**Model answer.** Four numbers and one rounding rule, and then everything else is arithmetic. On
64-bit HotSpot with compressed oops: an object header is **12** bytes, an array header **16** (the
12 plus a 4-byte length), a reference is **4** bytes, an `int` is 4, and every object is padded up to
a multiple of **8**.

So:

- `HashMap.Node` = 12 header + 4 `hash` + 4 `key` + 4 `value` + 4 `next` = 28 → **32**.
- `LinkedHashMap.Entry` = that plus `before` + `after` = 36 → **40**.
- `HashMap.TreeNode` = that plus `parent`, `left`, `right`, `prev` and a `boolean red` = 53 → **56**.
- `Integer` = 12 + 4 = **16**, no padding needed.
- `Long` = 12 + 4 padding + 8 = **24**.

The number to quote for the real cost of a map is the amortised per-entry figure: a
`HashMap<Integer,Integer>` entry is about **69 bytes** — a 32-byte `Node`, two 16-byte boxes, and
about 5.33 bytes of table slot (4 bytes divided by the 0.75 load factor). That is 69 bytes to store
eight bytes of payload, which is the sentence that changes how people size caches.

**If they push:** the flags that move the baseline are worth naming, because each one invalidates the
arithmetic. `-XX:-UseCompressedOops`, or a heap above the ~32 GB cliff, makes every reference 8
bytes — so `Node` goes to 48 and a boxed-`Integer` map nearly doubles. `-XX:ObjectAlignmentInBytes=N`
changes the rounding quantum *and* moves the cliff to `2³² × N`.
`-XX:+UseCompactObjectHeaders` (experimental in JDK 24, product in 25) takes the header from 12 to 8.
And `-XX:-UseCompressedClassPointers` takes it from 12 to 16.

For a specific object, do not derive it — measure it with JOL:
`ClassLayout.parseInstance(obj).toPrintable()` for the layout and
`GraphLayout.parseInstance(obj).totalSize()` for the whole graph.

**One-line close:** header 12, array header 16, ref 4, round to 8 — giving `Node` 32, `Entry` 40,
`TreeNode` 56, and about 69 bytes per `HashMap<Integer,Integer>` entry.

### Q18. "What do the `Abstract*` skeletons give you, and where do they hurt?"

**Model answer.** They exist so that a new collection needs two or three methods rather than
twenty, and each one derives everything else from the pair you supply. The cost is that the
*derivation* assumes a performance shape.

`AbstractCollection` wants `iterator()` and `size()`, and gives you `contains`, `toArray`,
`addAll`, `toString`. Note what it does **not** give you: `equals` and `hashCode`, deliberately,
because it cannot know whether you are a `List` (order-sensitive 31-fold) or a `Set`
(order-insensitive sum).

`AbstractList` wants `get(int)` and `size()` and gives you the iterator, `equals`, `indexOf` and
`subList`. Its iterator is implemented **in terms of `get(int)`** — so if `get` is O(i), a full
iteration is O(n²), and the caller sees only a for-each loop. That is why
`AbstractSequentialList` exists: you supply `listIterator(int)` and it derives
`get`/`set`/`add`/`remove` from the cursor. `LinkedList` extends that one.

`AbstractMap` wants only `entrySet()`, and derives `get`, `containsKey`, `equals` and `hashCode` —
with the same trap one level up: the derived `get` is a **linear scan of the entry set**, so
`AbstractMap.get` is O(n) unless you override it. `AbstractSet` adds set `equals`/`hashCode` and a
`removeAll` that iterates the smaller side. `AbstractQueue` derives `add`/`remove()`/`element()` from
`offer`/`poll`/`peek`, and bans null elements as a consequence of using `null` as the empty sentinel.

**If they push:** the extend-versus-delegate question, and the answer that shows judgement.
Extending a *concrete* class is the trap: override `add` on `ArrayList` and `addAll` may bypass your
override, because sibling methods are free to touch internal state directly. Delegation costs
boilerplate and gives you every entry point — which is precisely why `HashSet` **delegates** to a
`HashMap` rather than extending one, and why `LinkedHashSet` extends `HashSet` only to swap the map
it constructs.

**One-line close:** two or three methods each, but `AbstractList` derives iteration from `get` (O(n²)
on a linked structure) and `AbstractMap` derives `get` from `entrySet` (O(n)) — so pick the skeleton
that matches your access shape, or delegate.

## Pitfalls

### Quoting `LinkedList.get`'s worst case as `n/2` hops

**Wrong**

> "`node(int)` walks from whichever end is closer, so the worst case is `n/2` hops — 5 hops on a
> 10-node list."

**Right**

> "The backward branch is `for (int i = size - 1; i > index; i--) x = x.prev;`
> (`LinkedList.java:577`), so on a 10-node chain `last` is index 9 and `get(8)` is **one** hop. The
> worst case is **`⌊(n−1)/2⌋`** — 4 hops, at index 4 via the forward branch or index 5 via the
> backward one."

**Why people believe it:** `n/2` is the right *asymptotic* answer and it is what every summary says,
so the off-by-one never gets checked. It is worth having exactly right, because "what does `get(8)`
on a 10-element `LinkedList` cost" is a question with a specific number as its answer, and 1 is a
more surprising answer than 5.

### Describing `ArrayDeque` as power-of-two masked

**Wrong**

> "`ArrayDeque` rounds its capacity up to a power of two so it can wrap with `& (length - 1)`, and
> the default is 16."

Both halves are stale, and by different amounts.

**Right**

> "The power-of-two capacity and the mask are **JDK 8 only**. JDK 9 rewrote it to `inc`/`dec`/`sub`
> helpers — one branch each, no mask, capacity not rounded. Separately, the no-arg capacity changed
> from 16 to **17** (`new Object[16 + 1]`) in **JDK 12**, not in the JDK 9 rewrite: 8u202, 9 and
> 11.0.27 all allocate 16. So before JDK 12 a default `ArrayDeque` held only 15 elements, despite
> its javadoc promising 16."

**Why people believe it:** the JDK 9 rewrite is well known and the capacity change is not, so the
two get collapsed into one event nine releases wide. Naming both changes separately, with the
release each landed in, is a strong signal you read the source across versions rather than one blog
post about the rewrite.

## Cheat sheet

| Question | The one-line answer |
|---|---|
| `ArrayList` empty sentinels | two `{}` arrays distinguished by **reference identity**; no boolean flag |
| `grow` | `ArraysSupport.newLength(old, minCapacity - old, old >> 1)` = `old + max(min, pref)` |
| `new ArrayList<>(0)` ladder | 1, 2, 3, 4, 6, 9, 13 — the no-arg ladder is 10, 15, 22, 33, 49 |
| `addAll` growth | exactly `size + numNew`, overriding the 1.5× preference |
| Array ceiling | `SOFT_MAX_ARRAY_LENGTH = Integer.MAX_VALUE - 8` |
| Two reachable OOMEs | `Requested array size exceeds VM limit` vs `Java heap space` |
| `ArrayDeque` | `head`/`tail`, one slot always null, `size` is `sub(tail, head, len)` |
| `ArrayDeque` version traps | mask removed in **JDK 9**; capacity 16 → 17 in **JDK 12** |
| `ArrayDeque` growth | `jump = old < 64 ? old + 2 : old >> 1`; un-wrap slide after the copy |
| `ArrayDeque` fail-fast | no `modCount`; partial detection via `nonNullElementAt` |
| `LinkedList.node(int)` | forward when `index < (size >> 1)`; worst case `⌊(n−1)/2⌋` hops |
| Two sift methods | JIT monomorphism — a merged version goes megamorphic on `Comparator` |
| `siftUp`/`siftDown` cost | `log₂ n` / `2·log₂ n` comparisons; both move a hole, no swaps |
| `heapify` | backwards from `(n >>> 1) - 1`, O(n) via `Σ h/2^h = 2`; only via the `Collection` ctor |
| `removeAt` return | `null` = nothing before `i` moved; non-null = the element that climbed past `i` |
| `forgetMeNot` | the iterator's deque for elements relocated behind the cursor |
| `deleteEntry` two-child case | copy the successor's key/value up, delete the successor instead |
| `fixAfterDeletion` | runs only if the removed node was BLACK; 4 logical cases × 2 mirrors |
| `successor` second branch | climb while `t` is a **right** child; first left-link ancestor |
| In-order traversal | O(n) total, amortised O(1) per step, because each edge is crossed at most twice |
| `buildFromSorted` | O(n), zero comparisons, zero rotations, one arithmetic colouring pass |
| Its three entry points | `TreeMap(SortedMap)`, `putAll` into an empty compatible map, deserialization |
| `LinkedHashMap` seam | 4 node factories + 3 `afterNode*` hooks, all package-private |
| Why 4 factories | treeify/untreeify re-box nodes; missing two scrambles order at bin size 8 |
| Append method | `linkNodeAtEnd` (JDK 21 `:236`), was `linkNodeLast` (8 `:222`, 17 `:223`) |
| `afterNodeAccess` call sites | **8** in JDK 21 — including `putIfAbsent` and `computeIfAbsent` on a present key |
| `afterNodeAccess` dead code | the `else last = b;` arm is provably unreachable, in 8 and 21 alike |
| `TreeNode` inheritance | `HashMap.TreeNode extends LinkedHashMap.Entry` — plain maps carry unused links |
| `trySplit` | disjoint **prefix**, or `null` for a leaf |
| `SIZED` / `SUBSIZED` | exact size / both halves will know theirs too |
| Not `SUBSIZED` | `HashSet`, `TreeSet` — a table-range split cannot promise per-half counts |
| `LinkedList` split | copies a prefix, `BATCH_UNIT = 1 << 10`, `MAX_BATCH = 1 << 25` |
| `parallelStream()` pool | the shared `ForkJoinPool.commonPool()` — blocking in it starves the JVM |
| `stream()` | `StreamSupport.stream(spliterator(), false)` — a spliterator buys you streams |
| `List.of` classes | `EMPTY_LIST` / `List12` / `ListN`; `Map1` / `MapN`, and **no `Map2`** |
| `List12` | fields `e0`, `e1`; `size()` is `e1 != EMPTY ? 2 : 1`; 24 bytes, no array |
| Arity and arrays | 0–2 allocate none; 3–10 adopt the varargs array; `of(E...)` copies |
| `EXPAND_FACTOR = 2` | a correctness requirement — at 1, `probe` on a miss would not terminate |
| `probe` | returns `i` on a hit, `-(i + 1)` on a miss |
| `MapN` layout | one flat `Object[]`, key at `2i`, value at `2i + 1` |
| `SALT32L` | from `System.nanoTime()` at class init; consumed by **iterators only** |
| Byte units | header 12, array header 16, ref 4, pad to 8 |
| Node ladder | `Node` 32, `LinkedHashMap.Entry` 40, `TreeNode` 56, `Integer` 16, `Long` 24 |
| `HashMap<Integer,Integer>` entry | ≈ **69 bytes** to store 8 bytes of payload |
| Compressed-oops cliff | ~32 GB, and it scales with `-XX:ObjectAlignmentInBytes` |
| Header-changing flags | `-UseCompressedOops` (ref 4→8), `+UseCompactObjectHeaders` (12→8), `-UseCompressedClassPointers` (12→16) |
| `AbstractList` trap | derives iteration from `get` → O(n²) on a linked structure |
| `AbstractMap` trap | derives `get` from `entrySet` → O(n) unless overridden |
| `AbstractCollection` omission | no `equals`/`hashCode` — it cannot know `List` from `Set` |
| Extend vs delegate | sibling methods bypass an override on a concrete class — `HashSet` delegates |

## Self-test

**Q1.** Why does `TreeMap` keep two nearly identical search loops?

<details><summary>Answer</summary>

For JIT monomorphism. `getEntry` casts the key to `Comparable` and calls `compareTo`;
`getEntryUsingComparator` calls `comparator.compare`. Which one runs is decided once, by whether
`comparator == null`, so each call site sees exactly one implementation of the comparison and the JIT
can inline it. A single merged loop with a branch on every comparison would be megamorphic on the
`Comparator` interface and would not inline. `PriorityQueue` does the same thing with four sift
methods — `siftUpComparable`/`siftUpUsingComparator` and the same for down — for the same reason.

</details>

**Q2.** `AbstractMap.get` is O(n). Which JDK classes rely on `AbstractMap` and how do they avoid
that?

<details><summary>Answer</summary>

They override `get`. `HashMap` extends `AbstractMap` and supplies its own `get`/`getNode`, so the
inherited linear scan is never used; `TreeMap` and `EnumMap` do the same. What they *do* keep from
`AbstractMap` are `equals`, `hashCode`, `toString`, `putAll` and the cached `keySet`/`values` fields.
The `ImmutableCollections` maps also extend `AbstractMap` — which is why `Map.of(...).keySet()` is
cached and returns the same instance, and also why `Map1`/`MapN` are **not** `@ValueBased`: those
inherited cache fields are mutable state, which disqualifies them.

</details>

**Q3.** `new ArrayDeque<>(16)` — how many slots, and how many elements can it hold before growing?

<details><summary>Answer</summary>

17 slots, holding 16 elements. Every capacity request becomes `n + 1`, because `tail` must be able
to sit on an empty slot for `head == tail` to mean "empty" rather than "full" — there is no `size`
field to disambiguate them. The same reservation is why the **no-arg** constructor allocates
`new Object[16 + 1]` since JDK 12, and why before JDK 12 the no-arg deque allocated 16 slots and
therefore held only 15 elements while its javadoc promised 16. Growth triggers after a write, when
`head == tail`, and adds `jump = old < 64 ? old + 2 : old >> 1`.

</details>

**Q4.** You have a 500-element `LinkedList` and call `parallelStream()`. How many chunks does the
work split into?

<details><summary>Answer</summary>

One — so there is no parallelism at all. `LLSpliterator.trySplit` cannot index into a chain, so it
walks forward copying elements into an `Object[]` whose size starts at `BATCH_UNIT = 1 << 10` = 1024
and grows on each subsequent call up to `MAX_BATCH = 1 << 25`. With only 500 elements the first
batch consumes the entire list, the receiver is left empty, and the framework has a single chunk.
On a much larger list you do get chunks, but every split costs a traversal plus an allocation, and
the chunks are batches rather than halves. Copy to an `ArrayList` first, which splits at
`(lo + hi) >>> 1` in constant time.

</details>

**Q5.** `List.of("a", "b")` and `List.of("a", "b", "c")` — how many objects does each allocate, and
why is that not just an optimisation?

<details><summary>Answer</summary>

Two elements allocate **one** object, a `List12` with fields `e0` and `e1` and no array at all —
24 bytes. Three elements allocate **two**: a `ListN` plus its `Object[]`, about 56 bytes. The arity
overloads exist so that the small cases pay no array, and so that arities 3–10 can *adopt* the
varargs array via `listFromTrustedArray` with no defensive copy, where the general `of(E...)` must
copy because the caller may have kept a reference to the array. That copy is not just prudence, it
is TOCTOU-safe: it copies and null-checks in a single pass, so no slot is read twice and a
concurrent write cannot slip a `null` past the check. And `List12`'s `size()` compares `e1` against
a private `EMPTY` sentinel rather than `null`, because `@Stable` only constant-folds non-default
values.

</details>

---

**Leaves covered:** none — this file is the second half of row 72's Q&A block; the §5.1 leaves it
supports (5.1.1–5.1.9) are claimed by [92-interview-internals.md](92-interview-internals.md)
**Leaves deferred:** none
**Diagrams included:** none
**Target version:** Java 21 LTS
**Lines:** 493
