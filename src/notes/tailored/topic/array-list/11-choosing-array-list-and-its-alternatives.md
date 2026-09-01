# `ArrayList` — 11 Choosing `ArrayList` and its alternatives

**Target version: Java 21 LTS.** | [Map](00-map.md)
Assumes: the cost table, the footprint arithmetic, and the measured traversal figures (file 10).
Previous: [10 Cost and memory](10-cost-and-memory.md) · Next: [12 Failure modes in production](12-failure-modes-in-production.md)

Files 01–10 gave you the contract, the hierarchy, the member surface, every
construction route, the internals, and the cost model. This file spends none
of that on re-explanation. It spends it on a decision: given a slice of
QuizStakes state, which of six list-shaped types do you reach for, and why the
answer changes so rarely toward `LinkedList`.

## The map before the streets

Six leaves. Each is reachable; only one condition selects each leaf.

![Six leaves. `LinkedList` is reachable, but the condition that selects it is narrower than most people assume.](diagrams/D-15-which-list-decision-tree.svg)

Root to leaf, in words:

1. Not a `List` at all — keyed lookup or smallest-first retrieval → skip to
   the non-list leaves below.
2. Contents never change after construction → `List.of(...)`.
3. Concurrent readers and writers: reads dominate, snapshot iteration is fine
   → `CopyOnWriteArrayList`. Both frequent, "not corrupted" is enough →
   `Collections.synchronizedList(new ArrayList<>())`.
4. Insert/remove only at the front or back, never indexed → `ArrayDeque` —
   unless you hold a `ListIterator` mid-list and need to insert/remove there
   repeatedly, which `ArrayDeque` cannot do because it is not a `List`.
5. Indexed access, occasional insert/remove anywhere, single-threaded or
   externally synchronized → `ArrayList`.
6. A held `ListIterator` cursor, repeated local insert/remove, never indexed
   by position, `n` large enough that a shift would dominate → `LinkedList`.
   The narrowest box on the tree — most people who land here actually belong
   in leaf 4 or leaf 5.

## Q-30 — Where `ArrayList` beats `LinkedList` even where big-O says it should not

### Locality beats pointer-chasing at equal big-O

Big-O counts operations, not nanoseconds. `ArrayList` stores elements as
consecutive 4-byte references in one `Object[]` (file 10's footprint
arithmetic); `LinkedList` stores each element in its own 24-byte `Node`,
wherever the allocator placed it, linked by `next`/`prev`. Walking the array
is a fixed 4-byte stride; walking the list follows a pointer that could be
anywhere on the heap.

**Mechanism.** A core fetches a 64-byte cache line at a time, and the
prefetcher speculatively pulls the next line when it recognises a linear
stride. `ArrayList` delivers **16 references per cache line**, and the stride
never varies, so the prefetcher stays ahead. A `LinkedList` node is 24 bytes —
fewer than 3 per line even in the best case — and nodes are allocated one
`add` at a time, not in traversal order, so by the time a long-lived list is
walked, consecutive nodes can be scattered anywhere in the heap. Each `next`
hop is a coin flip on whether the line is already cached; there is no stride
for the prefetcher to exploit.

**Measured on JDK 21.0.7**, 200 000 elements, tenth warm iteration: `ArrayList`
for-each **103 µs**; `LinkedList` for-each **329 µs** — **3.2×** slower at
identical O(n). This is Q-30's headline number, and it does not shrink or grow
with `n` — it is a constant-factor gap, which is exactly why it surprises
people who expect "same complexity" to mean "same speed."

> **Definition.** Two algorithms with identical asymptotic complexity can
> differ by an order of magnitude in wall-clock time, because complexity
> counts operations and hardware charges differently depending on whether the
> memory an operation touches is predictable.

### The `LinkedList.get(i)` trap — the exponent, not just the constant, is wrong

`ArrayList.get(i)` is one array index. `LinkedList` has no array, so
`get(i)` walks from whichever end is nearer — itself O(n). Calling it in an
index loop turns an apparently linear scan into `O(k·n)`.

```java
List<PaymentIntent> intents = new LinkedList<>(paymentIntents); // 200_000
for (int i = 0; i < 20_000; i++) {
    touch(intents.get(i));   // index loop over a non-RandomAccess list — the trap
}
```

**Measured on JDK 21.0.7:** walking only the **first 20 000** of 200 000
`LinkedList` elements by `get(i)` costs **352 ms**, against **101 µs** for
scanning the **entire** 200 000-element `ArrayList` the same way — roughly
**3 500×** for a tenth of the work. `List`'s Javadoc recommends checking
`RandomAccess` before writing an index loop precisely because of this trap;
`Collections.binarySearch`, `.reverse`, and `.shuffle` all branch on it
internally.

**Interview:** "Does `ArrayList` or `LinkedList` win `get(i)` in a loop?"
`ArrayList` — `LinkedList.get(i)` is itself O(n), so an index loop over it is
O(n²), a different complexity class, not just a slower constant.

### The one case `LinkedList` genuinely wins — and why it still usually loses

**Measured:** 100 000 `add(0, e)` calls: **< 1 ms** on `LinkedList` against
**314 ms** on `ArrayList` (file 10). `ArrayList.add(0, e)` shifts every
element one slot right via `arraycopy`; `LinkedList.addFirst` allocates one
node and rewires two pointers — genuinely O(1). That win is real. It is also
rarely the right production answer, because `ArrayDeque` gives the same O(1)
head insertion (below) without the 24-byte node tax or the traversal tax
above — `LinkedList` earning the microbenchmark does not make it the
production choice when a cheaper alternative matches its one advantage.

The honest condition where `LinkedList` still wins: a held `ListIterator`
positioned mid-list, repeated `add`/`remove` at that cursor — O(1) per call,
no shift, because the iterator already knows the node — **and** no positional
indexing, **and** no hot traversal, **and** `n` large enough for a shift to
matter. Most code reaching for `LinkedList` for "middle insertions" is really
computing an index and calling `add(index, e)` — O(n) on `LinkedList` too,
because reaching `index` is the same walk as `get(i)`.

File 09's spliterator fact applies here without re-deriving it:
`ArrayList.spliterator()` reports `SIZED | SUBSIZED` (measured `16464`),
letting a parallel stream pre-size splits with zero copying; `LinkedList`'s
spliterator reports neither, so it cannot.

> **Definition.** `LinkedList` wins exactly one operation — O(1) at an
> already-held iterator cursor — and even that has a cheaper-on-every-axis
> competitor for the specific case of the two ends.

## Q-33 — When `ArrayList` is right, and which alternative wins otherwise

### Comparison table — all six leaves

| | `ArrayList` | `ArrayDeque` | `LinkedList` | `CopyOnWriteArrayList` | `List.of(...)` | `synchronizedList` |
|---|---|---|---|---|---|---|
| Indexed `get(i)` | O(1) | **no `get(int)` — not a `List`** | O(n) | O(1) | O(1) | O(1), delegates |
| Insert/remove at ends | O(n) shift (O(n) `add(0,e)`) | Amortised **O(1) both ends** | O(1) both ends | O(n) — full copy | n/a, immutable | Same as delegate + lock |
| Insert/remove in middle | O(n) shift | not supported | O(n) to reach index; O(1) at held cursor | O(n) copy | n/a | O(n) + lock |
| Per-element footprint | 4 B + ≤33% slack | 4 B, no node | 24-B `Node` — 6× | 4 B, whole array copied per write | Cheapest — `List12` has **no array** for ≤2 elements | Same as delegate |
| Iteration under concurrent mutation | Fail-fast, best-effort | Fail-fast | Fail-fast | **Snapshot** — never CME, never sees later writes | n/a | Fail-fast; **iterator not synchronized** |
| Thread-safety | None | None | None | Full, read-optimised | Full — nothing to synchronize | Full, one monitor |
| Mutability | Mutable | Mutable | Mutable | Mutable | **Immutable** | Mutable (delegates) |
| `null` | Accepts | **Rejects** | Accepts | Accepts | **Rejects** (NPE) | Same as delegate |

The `null` row is a real migration hazard: code that stores an occasional
`null` runs fine on `ArrayList`; swapping to `ArrayDeque` (for the head-insert
win) or `List.of` (for the immutability win) throws `NullPointerException` at
a call site nowhere near the type change — file 12's territory, flagged here
because it belongs at decision time.

### `ArrayDeque` — the real answer to head insertion

A circular array with `head`/`tail` indices that wrap; both ends are the same
operation — write, advance, mask. It supersedes `Stack` and is documented as
likely faster than `LinkedList` for stack/queue use. It doubles capacity
(not `ArrayList`'s 1.5×) and allocates no per-element node — footprint matches
`ArrayList`, not `LinkedList`. It has **no `get(int)`** — the one missing
method that makes it a distinct leaf rather than a strict upgrade.

```java
Deque<BankDepositRecord> ingestionQueue = new ArrayDeque<>();
void onRecordRead(BankDepositRecord r) { ingestionQueue.addLast(r); }
BankDepositRecord nextForMatching() { return ingestionQueue.pollFirst(); } // null if empty
```

Appendix A.5's bank-deposit feed is **40 000 records/day, 500 000 at
month-end**, consumed FIFO, never indexed. `ArrayList.remove(0)` per record
shifts every remaining element — O(n) per poll, O(n²) to drain 500 000.
`ArrayDeque.pollFirst()` stays amortised O(1) regardless of volume. Where
producer and consumer are genuinely separate threads, reach for a
`BlockingQueue` implementation instead — `ArrayDeque` itself is not
thread-safe.

**Pitfall:** `ArrayDeque` rejects `null` outright (`NullPointerException`) —
`null` is the internal sentinel for "empty" in peek/poll. A queue element that
can legitimately be absent needs `Optional` or a distinct state, never a
stored `null`.

> **Definition.** `ArrayDeque` is the array-backed, non-thread-safe,
> `null`-rejecting `Deque` giving amortised O(1) at both ends with no
> per-element node — the answer whenever indexing is not also required.

### `CopyOnWriteArrayList` and `Collections.synchronizedList`

`CopyOnWriteArrayList` copies the **entire** backing array on every mutation —
O(n) per write, so a write-heavy structure built on it is quadratic in
aggregate. Its iterator walks a **snapshot** captured at creation: never
`ConcurrentModificationException`, never sees a later write. It fits a
read-mostly listener list — the callbacks `BankDeposits` notifies when a
statement file finishes — added/removed rarely, invoked constantly. It does
**not** fit the ingestion queue itself.

`Collections.synchronizedList` wraps every method in one shared monitor —
each individual call is atomic. Its **iterator is not synchronized**, and is
still fail-fast: a `for-each` must be wrapped by the caller in
`synchronized (list) { ... }` for the whole traversal, or another thread's
mutation between `hasNext()`/`next()` calls throws `ConcurrentModificationException`.
This is the exact misconception the class exists to correct — safe calls,
not safe iteration.

**Pitfall — believing synchronization makes iteration safe:**
```java
List<PaymentIntent> safe = Collections.synchronizedList(new ArrayList<>());
for (PaymentIntent p : safe) { ... }   // -> ConcurrentModificationException under load
```
Right: `synchronized (safe) { for (PaymentIntent p : safe) { ... } }` — hold
the wrapper's own monitor for the entire loop, because that is the one thing
the wrapper does not do for you.

### `List.of(...)` and `PaymentRun.itemIds`

`List.of(...)` dispatches by arity to purpose-built immutable types.
**Measured:** one or two elements → `ImmutableCollections$List12`, which
stores elements directly as fields — **no backing array at all**. Three or
more → `ListN`, array-backed but with no growth machinery, no `modCount`, no
mutation path whatsoever.

`Movement.entries` (Appendix C.2, C.6) fits exactly: 2–4 `LedgerEntry` values,
append-only under §11.7 invariant 7, sum-to-zero under invariant 1, never
touched again once posted. A bonus grant's 2 entries need no array at all;
a stake's 4 entries get `ListN` with zero mutation surface:

```java
List<LedgerEntry> stakeReserved = List.of(cashDebit, bonusDebit, cashCredit, bonusCredit);
Movement m = new Movement(id, idemKey, stakeReserved, MovementReason.STAKE_RESERVED, now);
// stakeReserved.add(extra) -> UnsupportedOperationException
```

This buys immutability enforced by the type, not convention — no method
exists that could break the sum-to-zero invariant later.

`PaymentRun.itemIds` is the opposite shape: it grows as approved withdrawals
are collected before submission (§13.1), and Appendix A.5 fixes the count at
roughly **1 800** per run. The count is known before the list is built, so
`new ArrayList<>(1800)` converts what would otherwise be several resizes
along file 10's default growth sequence into zero, at the cost of at most
1 800 wasted 4-byte slots if the estimate runs high — immaterial against a
12 GB heap (Appendix A.6). Indexed access is also live here — the payout-file
writer addresses items by position — exactly leaf 5's pattern.

**Pitfall:** `List.of("x", null)` throws `NullPointerException` (measured) —
any value that might legitimately be absent must be filtered or wrapped
before it reaches `List.of(...)`.

### When "which list" is the wrong question

§15.4 states cash available and restriction decisions must **never** be
cached, but the current agreement version's text is the opposite case:
changes rarely, read on every screen. Appendix C.6 assigns it an **LRU map**,
not a list — the access pattern is keyed lookup by `AgreementRef`, and no
list on this tree has a key. A complete decision procedure has to be able to
say "not a list at all" rather than force the nearest leaf.

Same reason, one line: the reservation expiry index (Appendix C.6) is a
**priority queue by `expiresAt`** — smallest-expiry-first needs the min on
top, which no list gives without an O(n) scan or an O(n log n) re-sort per
insert.

## Pitfalls

### "`LinkedList` is right for frequent insertions"

**Wrong**
```java
List<PaymentIntent> pending = new LinkedList<>();
for (PaymentIntent p : incoming) {
    pending.add(findInsertPosition(pending, p), p);   // indexed insert, no held iterator
}
```
`findInsertPosition` and the subsequent `add(index, e)` both walk from an end
to reach `index` — O(n), same as `ArrayList`'s shift, plus the 6× footprint
and 3.2×-worse traversal from Q-30. No `ListIterator` is held across calls, so
`LinkedList`'s one advantage never fires.

**Right**
```java
List<PaymentIntent> pending = new ArrayList<>(incoming.size());
for (PaymentIntent p : incoming) {
    int pos = Collections.binarySearch(pending, p, BY_PRIORITY);
    pending.add(pos < 0 ? -pos - 1 : pos, p);
}
```
Still O(n) per insert, but the shift is a packed `arraycopy`, and
`binarySearch` on a `RandomAccess` list is O(log n) rather than the O(n)
fallback `Collections.binarySearch` uses on a non-`RandomAccess` list.

**Why people believe it:** "insertion in the middle is a linked-list
strength" is true only once already positioned — almost no real call site is;
it is computing an index and calling `add(index, e)`, which pays exactly the
traversal cost `LinkedList` was supposed to avoid.

## Cheat sheet

| Need | Choice |
|---|---|
| Indexed access, general purpose, single-threaded | `ArrayList` |
| Indexed access, size known up front | `new ArrayList<>(knownSize)` |
| Insert/remove at either end only, no indexing | `ArrayDeque` |
| End insert/remove, producer/consumer across threads | `BlockingQueue` impl |
| Contents fixed at construction | `List.of(...)` |
| Read-mostly, safe iteration without locking | `CopyOnWriteArrayList` |
| Every call atomic, iteration wrapped manually | `Collections.synchronizedList` |
| Held `ListIterator`, repeated local insert/remove, large n | `LinkedList` (narrow) |
| Keyed lookup, small, hot, rarely changes | LRU map — not a list |
| Smallest-expiry-first retrieval | Priority queue — not a list |
| `for-each`/`stream()` over the whole collection | `ArrayList` — 3.2× faster than `LinkedList` |
| Index loop (`get(i)` in a `for`) | `ArrayList` only — O(n²) on `LinkedList` |
| `null` elements must be storable | `ArrayList`/`LinkedList` — never `ArrayDeque`/`List.of` |

## Self-test

**Q1.** 200 000-element `for-each`: 103 µs `ArrayList`, 329 µs `LinkedList`.
Both O(n). What hardware fact explains the 3.2×?

<details><summary>Answer</summary>

`ArrayList` packs 16 references per 64-byte cache line at a fixed stride the
prefetcher recognises. `LinkedList` nodes (24 bytes) are scattered in
allocation order, not traversal order, so each `next` hop risks a cache miss
the prefetcher cannot predict.

</details>

**Q2.** Why is scanning the first 20 000 of 200 000 `LinkedList` elements by
`get(i)` about 3 500× slower than scanning the entire 200 000 `ArrayList`?

<details><summary>Answer</summary>

`LinkedList.get(i)` is itself O(n) — no array to index, so it walks from the
nearer end. A loop calling it n times is O(k·n), not O(k). `ArrayList.get(i)`
is O(1), so the same loop over it stays O(n).

</details>

**Q3.** `LinkedList` wins 100 000 `add(0,e)` (< 1 ms vs 314 ms). Why is this
rarely the deciding fact?

<details><summary>Answer</summary>

`ArrayDeque` matches that O(1) head insertion without the 24-byte node
footprint or the cache-miss traversal cost. `LinkedList`'s one microbenchmark
win is beaten on every other axis by a cheaper alternative.

</details>

**Q4.** `queue.get(2)` does not compile on `ArrayDeque<T> queue`. Why, given
it is array-backed?

<details><summary>Answer</summary>

`ArrayDeque` implements `Deque`/`Queue`, not `List` — no `get(int)` exists.
Being array-backed buys O(1)-amortised operations at both ends with good
locality, not a random-access promise a wrapped circular buffer cannot keep.

</details>

**Q5.** Why does a plain `for-each` over `Collections.synchronizedList(list)`
still risk `ConcurrentModificationException`?

<details><summary>Answer</summary>

The wrapper's `iterator()` returns the delegate's own unsynchronized
iterator. Each `hasNext()`/`next()` call is unprotected individually, so
another thread can mutate between calls. The caller must hold the wrapper's
monitor for the whole loop manually.

</details>

**Q6.** `Movement.entries` holds 2–4 `LedgerEntry` values, never mutated after
posting. Which construct, and what does it buy?

<details><summary>Answer</summary>

`List.of(...)`. Two entries need no backing array at all
(`ImmutableCollections$List12`). Immutability is enforced by the type — no
mutation method exists — so the sum-to-zero ledger invariant cannot be broken
later.

</details>

**Q7.** Why `new ArrayList<>(1800)` for `PaymentRun.itemIds` rather than a
bare `new ArrayList<>()`?

<details><summary>Answer</summary>

The run's item set size is known before the list is built. Pre-sizing avoids
every resize along the default growth sequence at the cost of at most 1 800
wasted 4-byte slots if the estimate runs high.

</details>

**Q8.** Why is `ArrayList.remove(0)` wrong for the 500 000-record month-end
bank-deposit queue, and what replaces it?

<details><summary>Answer</summary>

Each `remove(0)` shifts every remaining element — O(n) per call, O(n²) to
drain the file. `ArrayDeque.pollFirst()` stays amortised O(1) regardless of
depth, with no per-element node.

</details>

**Q9.** Why is "which list" the wrong question for the agreement cache?

<details><summary>Answer</summary>

The access pattern is keyed lookup by `AgreementRef`, not sequential or
positional access. Appendix C.6 assigns it an LRU map — none of the six
list-shaped leaves has a key, so forcing one is the wrong answer.

</details>

**Q10.** `List.of("x", null)` and `new ArrayDeque<>().addFirst(null)` both
throw `NullPointerException`; `ArrayList.add(null)` does not. Why does this
matter at decision time, not just at migration time?

<details><summary>Answer</summary>

Code storing an occasional `null` runs fine against `ArrayList`. Swapping to
`ArrayDeque` or `List.of` for a genuine performance or immutability reason
introduces a runtime NPE at an unrelated call site — the cost lands on
whoever migrates later, so it belongs in the decision, not after it.

</details>

---

**Questions answered:** Q-30, Q-33
**Sets up:** Next: the ways a correct-looking ArrayList usage still takes production down.
**Diagrams included:** D-15
**Target version:** Java 21 LTS
**Lines:** 424
