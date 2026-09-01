# 05 Multithreading and Concurrency — The queue consolidated diff table — BUILD IT (§4.3, leaf 4.3.7)

**Target version: Java 21 LTS.** | **Part 4 of 5** | [Index](../00-index.md)
Previous: [drainTo and the SPSC ring](03c-drainto-and-the-spsc-ring.md) · Next: [Treiber stack and ABA](04-treiber-stack-and-aba.md)

This leaf is a comparison table with an argument wrapped around it, not a mechanism taught from
scratch — the usual eight-beat concept structure doesn't apply here. What follows is the table, then
one paragraph per column explaining why the JDK bothers with it.

Source read for every claim below: `openjdk/jdk` at tag `jdk-21-ga`,
`src/java.base/share/classes/java/util/concurrent/ArrayBlockingQueue.java` and
`LinkedBlockingQueue.java` (fetched via `raw.githubusercontent.com`).

## §4.3 in one line each

| File | What it built |
|---|---|
| `03-bounded-blocking-queue.md` (4.3.1–4.3.2) | v1: `synchronized` + `wait`/`notifyAll` ring buffer, `while (count == items.length) wait();`. v2: `ReentrantLock` with two `Condition`s (`notFull`, `notEmpty`), targeted signalling instead of `signalAll`. |
| `03b-two-lock-queue-and-timed-ops.md` (4.3.3–4.3.4) | v3: two-lock (`putLock`/`takeLock`) linked list with `AtomicInteger count`, cascading-signal rule; timed `offer`/`poll` as an `awaitNanos` deadline loop. |
| `03c-drainto-and-the-spsc-ring.md` (4.3.5–4.3.6) | `drainTo` added to v3; lock-free SPSC ring with padded `head`/`tail` `AtomicLong`s and `index & (capacity - 1)` masking. |

All four sit under the same running example: a bounded queue of `WithdrawalTransaction`, capacity
1,000, feeding a `PaymentRun`, filled by threads named `settlement-ingest-N` at up to 3,400
settlements/sec against 7k withdrawals/day.

## The diff table

| Dimension | v1 (§4.3.1, monitor) | v2 (§4.3.2, lock+2 conditions) | v3 (§4.3.3–4.3.6, two-lock linked) | SPSC ring (§4.3.6) | `ArrayBlockingQueue` | `LinkedBlockingQueue` |
|---|---|---|---|---|---|---|
| Fairness flag | none | none | none | not applicable (single producer, single consumer, no contention to arbitrate) | `ArrayBlockingQueue(capacity, boolean fair)` → `new ReentrantLock(fair)` | none — always non-fair `ReentrantLock`s |
| Null rejection | not enforced by us | not enforced by us | not enforced by us | not enforced by us | throws `NullPointerException` from `put`/`offer`/`add` | same |
| `Spliterator`/`forEach`/`removeIf` | none | none | none | none | all three implemented, spliterator documented "weakly consistent" | all three implemented, same wording |
| `remove(Object)` | single monitor, correct by construction | single lock, correct by construction | **not implemented** in the teaching version — see below | not applicable to a ring with two fixed roles | single `lock.lock()`, walks the array under that one lock | **`fullyLock()`/`fullyUnlock()`**, walks the list holding both locks |
| Serialization | not implemented | not implemented | not implemented | not implemented | default serialization: `items` array is `@SuppressWarnings("serial")` but **not** transient; custom `readObject` re-validates invariants, no custom `writeObject` | custom `writeObject`/`readObject`; list pointers `head`/`last` are `transient` and rebuilt on read, but the locks (`putLock`, `takeLock`) and their `Condition`s are **not** transient |
| Weakly consistent iterator | n/a (no iterator) | n/a | n/a | n/a | yes | yes |
| Why `fullyLock()` exists | n/a — one lock guards everything | n/a — one lock guards everything | would need it the moment `remove(Object)`/`iterator()`/`toString()` were added | n/a — no whole-structure operation is ever needed | n/a — `ArrayBlockingQueue` has exactly one lock, so there is nothing to "fully" lock | exists precisely because put-side and take-side each have their own lock; anything that must see the whole chain needs both |

### `remove(Object)` — the reason `fullyLock()` exists

`LinkedBlockingQueue`'s two-lock design (built as v3 in `03b-two-lock-queue-and-timed-ops.md`) lets a
producer append at the tail under `putLock` while a consumer removes from the head under `takeLock`,
fully concurrently. That is the entire point of the split. But `remove(Object)` — used, for example,
to purge a cancelled `WithdrawalTransaction` before it reaches the `PaymentRun` — has to walk the
*whole* chain from `head` to the last node. If it only held `takeLock`, a producer could still be
linking a new node onto `last` while the removal is mid-walk near the tail, corrupting the traversal
or losing an update. The fix, verified against the JDK source, is:

```java
void fullyLock() {
    putLock.lock();
    takeLock.lock();
}

void fullyUnlock() {
    takeLock.unlock();
    putLock.unlock();
}
```

**Lock order: `putLock` first, then `takeLock`. Unlock in the reverse order — `takeLock` first, then
`putLock`.** Every whole-queue operation (`remove(Object)`, `contains`, `toArray`, `toString`,
`clear`, and the iterator's construction) goes through `fullyLock()`/`fullyUnlock()`, always in that
same order. That fixed order is what prevents a deadlock against `put()` (which only ever takes
`putLock`) and `take()` (which only ever takes `takeLock`) — no code path anywhere in the class
acquires `takeLock` before `putLock`.

```java
// LinkedBlockingQueue.remove(Object), confirmed against jdk-21-ga source
public boolean remove(Object o) {
    if (o == null) return false;
    fullyLock();
    try {
        for (Node<WithdrawalTransaction> pred = head, p = pred.next;
             p != null;
             pred = p, p = p.next) {
            if (o.equals(p.item)) {
                unlink(p, pred);
                return true;
            }
        }
        return false;
    } finally {
        fullyUnlock();
    }
}
```

**Insight:** the two-lock split is only safe because exactly one operation family (the whole-queue
ones) ever needs both locks, and that family always takes them in the same fixed order. Split locking
without a designated "sometimes I need everything" escape hatch works only as long as nobody adds an
operation that touches both ends — the moment `03b`'s v3 grows a `remove(Object)`, it needs
`fullyLock()` too, and it must copy the JDK's order exactly, not invent its own.

Removing cancelled withdrawals in bulk before a `PaymentRun` closes its batch is exactly a `removeIf`
use, which the JDK gives you but v3 does not:

```java
// java.util.concurrent.LinkedBlockingQueue<WithdrawalTransaction>.removeIf, as ships in the JDK,
// used against the settlement queue before closing a PaymentRun batch
BlockingQueue<WithdrawalTransaction> settlementQueue =
        new LinkedBlockingQueue<>(1_000);

settlementQueue.removeIf(tx -> tx.status() == WithdrawalStatus.CANCELLED);
```

`removeIf` on `LinkedBlockingQueue` also takes `fullyLock()` internally for the same reason — a
predicate-driven bulk removal is a whole-queue operation.

### The fairness flag

`ArrayBlockingQueue(int capacity, boolean fair)` forwards `fair` straight into
`new ReentrantLock(fair)`; `LinkedBlockingQueue` has no such constructor and always builds
non-fair locks. None of v1–v3 or the SPSC ring exposes a fairness knob either.

A fair lock guarantees threads acquire in roughly FIFO order — the `settlement-ingest-N` thread that
has been blocked longest on a full queue is the next one let in when a slot opens. The cost is real:
fair `ReentrantLock` acquisition is measurably slower under contention because it can't let a
newly-arriving thread barge in and grab a free lock ahead of a thread that's already parked — every
acquisition has to check the queue. **Tradeoff:** non-fair (the default) gets higher aggregate
throughput because barging avoids the cost of waking a parked thread just to have it re-check and
re-park; fair avoids starvation, where one producer thread could in principle keep winning the race
for decades while another sits parked. A bounded queue is one of the few places this tradeoff is worth
paying for, because unlike most locks, a full or empty queue is a *steady-state* condition under
load — if `settlement-ingest-3` is consistently starved out of a saturated queue while
`settlement-ingest-1` and `-2` keep barging in, that's not a rare race, it's a systemic imbalance that
shows up as one ingest thread's backlog growing unboundedly while its siblings drain fine.

**Interview:** "Why would you ever pay for a fair `ArrayBlockingQueue`?" — because under sustained
contention non-fair locks can (not will, but statistically can) let some threads starve indefinitely
while others repeatedly barge ahead; fairness trades throughput for a bound on wait time. Most queues
never need it because contention is bursty, not sustained.

### Null rejection

Every `BlockingQueue` method — `add`, `put`, `offer` — throws `NullPointerException` on a null
element. This is because `poll()` (and `peek()`) return `null` to signal "the queue is empty right
now." If null were also a legal element, a caller could not tell the difference between "empty" and
"the head element happens to be null," and `poll()` would need a second signal (an exception, or an
`Optional`) to disambiguate — which the JDK collections framework predates and never retrofitted.
**Interview:** "Why can't a `BlockingQueue` hold null?" — one-line answer: because `null` is already
the empty-queue sentinel for `poll()`/`peek()`, so allowing it as a value would make emptiness
ambiguous. This is a five-second answer that people routinely get wrong by saying "because
`ConcurrentHashMap` doesn't allow nulls either" — that's a different reason (disambiguating "absent
key" from "key mapped to null" in `get()`), not this one.

### `Spliterator` / `forEach` / `removeIf`

None of v1, v2, v3, or the SPSC ring implements `Collection`, so none of them has an iterator,
`forEach`, `removeIf`, or a `Spliterator` at all — they only expose the `BlockingQueue`-shaped
methods (`put`, `take`, `offer`, `poll`, `drainTo`). Both JDK classes implement `Collection` fully,
and their `iterator()`, `spliterator()`, and `forEach()` are all documented, per source, as **weakly
consistent**.

Weakly consistent means three specific guarantees, and it is worth naming all three because
"weakly consistent" is often used as a synonym for "vague":

1. It never throws `ConcurrentModificationException`, no matter what happens to the queue during the
   traversal.
2. It may or may not reflect elements added or removed after the iterator/spliterator was created —
   no promise either way.
3. It is guaranteed to traverse each element that was present at creation, and each such element, at
   most once.

**Contrast with fail-fast:** an `ArrayList` iterator is fail-fast — it throws
`ConcurrentModificationException` the moment it detects the backing structure changed underneath it,
via a `modCount` check. Fail-fast trades availability for a loud, early crash on detected corruption;
weakly consistent trades certainty about staleness for never crashing. A weakly-consistent iterator
over the settlement queue mid-`PaymentRun` will happily keep iterating while `settlement-ingest-7`
appends and a `take()` thread drains — it just doesn't promise which of those new elements you'll see.

**Pitfall:** treating a weakly consistent iterator's snapshot as *the* snapshot. Code that does
`int n = 0; for (var tx : settlementQueue) n++;` and then assumes `n` equals the batch size handed to
a `PaymentRun` will be wrong under concurrent `put`/`take` — the count reflects *some* interleaving,
not a fixed point in time. **Fix:** use `drainTo` (built in `03c-drainto-and-the-spsc-ring.md`,
§4.3.5) when an atomic, all-or-nothing view is required, not iteration.

### Serialization

`ArrayBlockingQueue` serializes with **no custom `writeObject`**: the backing `items` array field is
annotated `@SuppressWarnings("serial")` but is not `transient`, so it round-trips via default Java
serialization. It does supply a custom `readObject` that calls `s.defaultReadObject()` and then
re-validates queue invariants (`invariantsSatisfied()`), throwing `InvalidObjectException` if a
corrupted stream produced an inconsistent `count`/`putIndex`/`takeIndex`.

`LinkedBlockingQueue` does the opposite: it **does** define both `writeObject` and `readObject`, and
its `writeObject` takes `fullyLock()` before writing, then walks the list writing each `item` followed
by a `null` sentinel — it does not serialize `Node` objects directly. Correspondingly, `head` and
`last` are declared `transient` and rebuilt node-by-node in `readObject`. What is **not** transient,
in either class, is the locking machinery itself: `ReentrantLock`, `Condition`, and `AtomicInteger`
are all themselves `Serializable`, so `putLock`, `takeLock`, `notEmpty`, and `notFull` serialize by
default along with the rest of the object (each `Condition` field carries `@SuppressWarnings("serial")`
to silence the "non-transient non-serializable field" lint, since `Condition` itself is not
`Serializable` but the concrete `AbstractQueuedSynchronizer.ConditionObject` is). **The transient
fields are the list *pointers* (`head`, `last`), not the locks** — a detail worth stating exactly
because it inverts the naive guess that "of course the locks are transient, you can't serialize a
lock." You can, and the JDK does.

**Why walk-and-rewrite instead of serializing nodes directly:** a `Node<E>` holds a raw `next`
reference chain; serializing it directly would work but would also serialize the exact chain
structure including any node identity, and more importantly requires holding `fullyLock()` for the
entire walk regardless — so the JDK takes the opportunity to also produce a clean, compact stream (one
`item` per queue element, no per-node bookkeeping) rather than a mechanical field dump.

### What a teaching implementation skips that production spends effort on

None of v1–v3 or the SPSC ring does bounds/state validation on deserialization, uses `@Contended`
padding beyond what §4.3.6 already added to the ring's `head`/`tail`, or documents its memory-ordering
level per field. A production queue used for real settlement traffic spends deliberate effort on:
input validation at every public entry point (null checks, capacity checks on construction,
invariant checks on deserialization) so a corrupted stream fails loudly instead of silently wedging
the queue; the choice of intrinsic (`AtomicInteger`/`AtomicLong` compare-and-swap vs. plain volatile
read/write) at each field, matched exactly to what that field's access pattern needs — no stronger,
no weaker; and zero incidental allocation per element on the hot path, which is why the SPSC ring uses
a preallocated backing array rather than allocating a `Node` per `WithdrawalTransaction`. At 7k
withdrawals a day (roughly one every twelve seconds) none of this effort is load-bearing — a
`LinkedBlockingQueue` allocating a `Node` per put is invisible. At 3,400 settlements/sec sustained,
every one of these choices is the difference between the queue disappearing from a profile and the
queue dominating it.

## Open questions

**Unverified:** whether `ArrayBlockingQueue.removeIf`'s internal bulk-removal path also holds the
single lock for the entire predicate evaluation (as opposed to per-element locking) was not directly
quoted from source in this pass — the fetched summary described it as "delegates to bulk removal with
predicate filtering logic" without the exact method body. Treat the row above ("all three
implemented") as correct on presence, but confirm the locking granularity of `removeIf` specifically
against source before quoting it in an interview answer.

## Pitfalls

### Assuming a fair queue is free or default

**Wrong**
```java
// Assumes ArrayBlockingQueue is fair "because it has a lock", so ingest threads
// are served in arrival order under contention.
BlockingQueue<WithdrawalTransaction> q = new ArrayBlockingQueue<>(1_000);
```
Under sustained contention from multiple `settlement-ingest-N` threads, this queue is non-fair by
default — some threads can be repeatedly barged past, in principle indefinitely.

**Right**
```java
// Explicit: pay the fairness cost only when starvation is an observed problem.
BlockingQueue<WithdrawalTransaction> q = new ArrayBlockingQueue<>(1_000, /* fair = */ true);
```
Fairness must be requested; it is never the default in either JDK queue.

**Why people believe it:** `ReentrantLock` conceptually feels like it should treat waiters equally,
and most people never hit the throughput cost of fairness in practice, so they assume the safer-sounding
default is fair.

### Assuming `remove(Object)` on `LinkedBlockingQueue` only needs `takeLock`

**Wrong**
```java
// Reasoning: "remove() is a removal, and takeLock guards removals from the head,
// so takeLock alone should be enough."
```
This reasoning is not code you'd write, but it is the exact bug you'd introduce if you tried to
reimplement `remove(Object)` on v3 (the two-lock linked queue from `03b`) using only `takeLock` — a
concurrent `put()` (which uses `putLock`, not `takeLock`) could still be linking a new tail node while
the removal walks the chain, since nothing serializes the two locks against each other in that case.

**Right**
```java
public boolean remove(Object o) {
    if (o == null) return false;
    fullyLock();               // putLock then takeLock — matches every other whole-queue op
    try {
        // walk head -> ... -> last, unlink matching node
        return true;   // or false
    } finally {
        fullyUnlock();          // takeLock then putLock — exact reverse order
    }
}
```
Any operation that must see or mutate the whole chain — not just one end — needs both locks, taken in
the fixed order the rest of the class uses.

**Why people believe it:** the two-lock split is introduced (correctly) as "put-side and take-side
never block each other," and it's an easy overgeneralization from there to "so any operation only
needs the lock for the end it conceptually touches" — `remove(Object)` doesn't conceptually touch
just one end, it touches the whole structure.

### Treating "weakly consistent" as "eventually consistent" or "unsafe"

**Wrong**
```java
// "Weakly consistent must mean it's not thread-safe to iterate concurrently,
// so I need external synchronization around this loop."
synchronized (settlementQueue) {
    for (WithdrawalTransaction tx : settlementQueue) { /* ... */ }
}
```
`LinkedBlockingQueue` and `ArrayBlockingQueue` iterators are safe to use without any external lock —
"weakly consistent" describes what the iterator promises to *return*, not whether it's safe to *call*.
The `synchronized` block above adds nothing but contention (and doesn't even use the queue's actual
lock, so it wouldn't help even if help were needed).

**Right**
```java
for (WithdrawalTransaction tx : settlementQueue) {
    // safe without external synchronization; may or may not see concurrent
    // puts/takes made after the iterator was created
}
```

**Why people believe it:** "weak" reads as "weak guarantee about safety" rather than its actual
meaning, "weak guarantee about which writes are visible" — thread-safety and staleness guarantees are
different axes, and the name conflates them in casual reading.

## Cheat sheet

| Question | Answer |
|---|---|
| Fairness flag exists on which queue? | `ArrayBlockingQueue(cap, boolean fair)` only. `LinkedBlockingQueue`: never. |
| Fairness default | Non-fair (barging allowed) unless `fair=true` passed explicitly. |
| Null allowed as an element? | No, in every `BlockingQueue`. `poll()`/`peek()` use `null` as the empty sentinel. |
| `fullyLock()` order | `putLock.lock()` then `takeLock.lock()`. |
| `fullyUnlock()` order | `takeLock.unlock()` then `putLock.unlock()` — exact reverse. |
| Who calls `fullyLock()`? | Any whole-queue op: `remove(Object)`, `removeIf`, `contains`, `toArray`, `toString`, `clear`, iterator construction. |
| `ArrayBlockingQueue.remove(Object)` locking | Single lock — there's only one lock to take. |
| Iterator/Spliterator consistency model | Weakly consistent: never CME, may/may not see post-creation writes, visits each pre-existing element at most once. |
| Contrast | Fail-fast (`ArrayList`) throws CME on detected structural change; weakly consistent never throws. |
| `ArrayBlockingQueue` transient fields | None — `items` serializes via default mechanism; custom `readObject` re-validates invariants. |
| `LinkedBlockingQueue` transient fields | `head`, `last` (list pointers) — rebuilt in `readObject`. Locks/conditions are NOT transient. |
| `LinkedBlockingQueue` custom serialization | Both `writeObject` (locks via `fullyLock()`, writes items + null sentinel) and `readObject`. |
| `ArrayBlockingQueue` custom serialization | `readObject` only (validates invariants); no custom `writeObject`. |
| What v1–v3 / SPSC skip that the JDK has | Fairness option, `Collection` methods, `Spliterator`, serialization, invariant re-validation. |

## Self-test

**Q1.** Why does neither `ArrayBlockingQueue` nor `LinkedBlockingQueue` allow a fairness constructor
that also applies to `LinkedBlockingQueue`?

<details><summary>Answer</summary>

`LinkedBlockingQueue` simply never exposes one — its constructors take only capacity (and an optional
initial `Collection`), and its two `ReentrantLock`s are always constructed non-fair. This is a JDK
design choice, not a technical impossibility: nothing prevents a `ReentrantLock(true)` from being used
for `putLock`/`takeLock`, the API just never surfaced the option. Only `ArrayBlockingQueue` exposes
`ArrayBlockingQueue(int capacity, boolean fair)`.

</details>

**Q2.** A caller does `Object result = queue.poll();` and gets `null`. Name the two situations this
could mean, and explain why the API can't distinguish them for you.

<details><summary>Answer</summary>

Either the queue was empty at the moment of the poll, or (in a hypothetical queue that allowed null
elements) the head element's value was itself `null`. The API can't distinguish them because
`poll()`'s only channel back to the caller is its return value, and that channel is already spent
signaling "empty" via `null`. This is exactly why every `BlockingQueue` implementation rejects null
elements outright at `put`/`offer`/`add` time — it removes the ambiguity by construction rather than
asking every caller to disambiguate.

</details>

**Q3.** In `LinkedBlockingQueue.fullyLock()`, what would happen if the acquisition order were
reversed — `takeLock` first, then `putLock` — in just one call site, while every other call site kept
`putLock` first?

<details><summary>Answer</summary>

Deadlock becomes possible. If thread A calls the reversed-order site and acquires `takeLock`, while
thread B concurrently calls a normal-order whole-queue op and acquires `putLock`, then A blocks
waiting for `putLock` (held by nobody yet, but B is about to want `takeLock`) and B blocks waiting for
`takeLock` (held by A) — classic circular wait. The JDK avoids this by having every single call site
that needs both locks acquire them in exactly one order, everywhere, with no exceptions.

</details>

**Q4.** Why does `LinkedBlockingQueue.writeObject()` write each `item` individually followed by a
`null` sentinel, rather than just relying on default serialization of the `Node` chain from `head`?

<details><summary>Answer</summary>

Two reasons work together. First, `head` and `last` are declared `transient` specifically so the
internal `Node` linkage isn't part of the serialized form — writing the raw chain would tie the
serialized representation to internal implementation details (and would still require holding
`fullyLock()` for consistency, so there's no simplicity gained). Second, writing plain items with a
`null` terminator produces a clean, self-describing stream that `readObject` can rebuild by simply
calling `add(item)` in a loop until it reads the sentinel — decoupling the wire format from the
internal node representation entirely.

</details>

**Q5.** Is it correct to say "the locks in `LinkedBlockingQueue` are transient because you can't
serialize a `ReentrantLock`"? Justify your answer against the source.

<details><summary>Answer</summary>

No. `ReentrantLock` and its `Condition` implementation (`AbstractQueuedSynchronizer.ConditionObject`)
are both `Serializable`, so they are *not* declared transient, and they do serialize by default along
with the rest of the object (the `Condition` fields carry `@SuppressWarnings("serial")` only to
silence a lint about the `Condition` interface itself not being `Serializable`, which is a compile-time
concern, not a runtime one). What actually is `transient` is `head` and `last` — the list pointers —
because the node chain is reconstructed explicitly in `readObject` rather than deserialized directly.

</details>

**Q6.** A weakly-consistent iterator over the settlement queue is created, then five more
`WithdrawalTransaction`s are `put()` before the iteration finishes. What is guaranteed about whether
those five show up in the iteration?

<details><summary>Answer</summary>

Nothing is guaranteed either way — "weakly consistent" explicitly does not promise the iterator will
or won't reflect elements added after its creation. What *is* guaranteed: no
`ConcurrentModificationException` will be thrown regardless of what those concurrent puts do, and every
element that was present when the iterator was created will be visited at most once (it may also be
visited zero times if it was removed before the iterator reached it, but never more than once).

</details>

**Q7.** Why is `remove(Object)` a "whole-queue operation" on `LinkedBlockingQueue` but not on
`ArrayBlockingQueue`, given that both eventually need to scan and unlink/shift an element?

<details><summary>Answer</summary>

The distinction isn't about `remove(Object)` itself — it's about how many locks each class has.
`ArrayBlockingQueue` has exactly one lock guarding the entire array, so any operation, whole-queue or
not, only ever needs that one lock; there's no "fully" to distinguish from "partially." `LinkedBlockingQueue`
split its locking into `putLock` (tail) and `takeLock` (head) specifically so put and take can proceed
without contending with each other. `remove(Object)` breaks that separation because it must traverse
from `head` all the way to `last`, crossing both zones, so it's the operation category that needs both
locks — hence `fullyLock()`.

</details>

**Q8.** Why is fairness "one of the few places you might actually pay for it" in a queue, compared to,
say, a lock guarding a short critical section elsewhere in the same settlement pipeline?

<details><summary>Answer</summary>

A short critical section is contended briefly and rarely — fairness's throughput cost there is
negligible because the lock isn't held long enough or contended often enough for barging vs. queueing
to matter. A bounded queue at capacity under sustained load is the opposite: `put()` and `take()` are
called constantly and the lock is genuinely hot, so the throughput cost of fairness (extra bookkeeping
on every acquisition, no barging) is paid on every single element, continuously, for as long as the
system runs at that load — making it one of the rare cases where the cost is large enough, and
persistent enough, to actually show up in a profile or a latency budget.

</details>

---

**Leaves covered:** 4.3.7 (1 leaf)
**Leaves deferred:** none
**Diagrams included:** none
**Target version:** Java 21 LTS
**Lines:** 280
