# 05 Multithreading and Concurrency — The Michael–Scott queue — BUILD IT (§4.4, leaves 4.4.5–4.4.6)

**Target version: Java 21 LTS.** | **Part 4 of 5** | [Index](../00-index.md)
Previous: [Why plain Java is usually ABA-safe](04b-why-java-is-aba-safe.md) · Next: [A striped counter, measured](04d-striped-counter-and-measurement.md)

## 4.4.5 `MichaelScottQueue<E>`

### Mental model

A Treiber stack ([04-treiber-stack-and-aba.md](04-treiber-stack-and-aba.md)) needs one CAS because
it has one pointer to defend: `top`. A FIFO queue needs to CAS at *both* ends independently — a
producer appends at the tail, a consumer removes from the head, and the two must never block each
other even though they touch opposite ends of the same linked structure. Picture a conveyor belt fed
from the right and drained from the left, with a permanently empty placeholder pallet sitting at the
very front of the belt that is never itself a real item — it exists purely so "the belt is empty"
and "the belt has one item" look like the same shape (a pallet with something or nothing behind it)
instead of two special cases. `settlement-ingest` threads push `WithdrawalTransaction`s onto the
tail; `payment-run-worker` threads drain from the head; the dummy pallet is what lets both sides
never have to ask "am I the special case."

### Why it exists

A synchronized queue serializes every enqueue against every dequeue through one lock, even though
the two operations touch different ends of the structure and, absent races on the same end, never
logically conflict. The Michael–Scott algorithm (Maged Michael and Michael Scott, 1996) is the
standard non-blocking FIFO queue precisely because it lets producers and consumers proceed
independently — each side has its own CAS target — while remaining correct under arbitrary
interleaving. It underlies `java.util.concurrent.ConcurrentLinkedQueue`.

### When to reach for it, and when not

Reach for a Michael–Scott-style queue when you need FIFO order, unbounded capacity, and
non-blocking `offer`/`poll` under contention from both ends — the `stake reservation` intake path
buffering settlement records at up to 3,400/sec burst before a batch of `payment-run-worker`
threads drains them is exactly this shape: producers never wait on consumers and vice versa. Do not
reach for it when you need bounded capacity with backpressure (an `ArrayBlockingQueue`'s park/unpark
handoff, §4.3, gives a producer somewhere to *wait* when the consumer falls behind, which this
queue's `offer` never does — it always succeeds, silently growing without limit); when you need LIFO
order (the Treiber stack, 04); or when you need blocking `take()` semantics without spinning
(`LinkedBlockingQueue` pairs a two-lock design with actual `Condition` waiting, §3.10).

### How it works

Two `AtomicReference<Node<E>>` fields, `head` and `tail`, both initialized to point at one shared
**dummy node** whose `item` is always `null` — a sentinel that never holds real data. Head always
points at a node whose `next` (once populated) is the *actual* first element; the value a caller
receives from `dequeue()` is always `head.get().next.item`, never `head.get().item`.

**`enqueue`** is two separate steps that are not atomic with each other, which is the entire subtlety
of the algorithm:

1. Read `tail`, read `tail.next`. If `tail.next` is not `null`, the tail pointer is **lagging** —
   some other thread already linked a new node onto the real last node but has not yet advanced
   `tail` to point at it. Help that thread by CASing `tail` forward to `tail.next`, then restart the
   whole loop from a fresh read.
2. If `tail.next` genuinely is `null` (this really is the last node), CAS `tail.next` from `null` to
   the new node. If that CAS wins, the new node is now reachable from the queue — logically enqueued
   — even though `tail` itself still points at the old last node. Immediately attempt one more CAS
   to swing `tail` forward to the new node; whether or not *that* CAS succeeds does not matter to
   correctness (see 4.4.6), because any other thread that needs `tail` to be current will perform the
   same "help advance" step in its own step 1.

**`dequeue`** reads `head`, reads `head.next`. If `head.next` is `null`, the queue is empty (only the
dummy remains). Otherwise it reads the item off `head.next` *before* attempting the CAS (because
after the CAS, another thread could reuse or GC that node), then CASes `head` from the old dummy to
`head.next`. The node that used to be `head.next` becomes the new dummy — its own `item` is
irrelevant once it plays that role, since dequeue always reads from `head.next`, never `head.item`.
The just-retired old dummy is unlinked by setting its own `next` to point at itself
(`p.next = p`) — a **self-link** — solely so that any thread still holding a stale reference to that
old dummy and traversing forward detects the self-link and knows to restart its traversal from
`head` rather than following a pointer into a node that is no longer part of the live queue.

![D-178 — The Michael–Scott queue's lagging tail](../diagrams/D-178-michael-scott-lagging-tail.svg)

**D-178** — The Michael–Scott queue's lagging tail: a dummy head, a `tail` pointer lagging one node
behind the last real element while an in-flight enqueue's `next`-CAS has already linked the new
node; a second thread noticing the lag and helping advance `tail`; and a dequeued node with
`next == p` (self-linked) so a stale traverser restarts from `head` instead of following a dead
pointer.

```java
import java.util.NoSuchElementException;
import java.util.concurrent.atomic.AtomicReference;

/**
 * A lock-free FIFO queue of settlement records, in the shape of Michael and Scott's 1996
 * two-lock-free-pointer design. Producers (settlement-ingest-N) enqueue; consumers
 * (payment-run-worker-N) dequeue. Neither side blocks the other.
 */
public final class MichaelScottQueue<E> {

    private static final class Node<E> {
        volatile E item;
        final AtomicReference<Node<E>> next = new AtomicReference<>();
        Node(E item) { this.item = item; }
    }

    private final AtomicReference<Node<E>> head;
    private final AtomicReference<Node<E>> tail;

    public MichaelScottQueue() {
        Node<E> dummy = new Node<>(null);
        this.head = new AtomicReference<>(dummy);
        this.tail = new AtomicReference<>(dummy);
    }

    /** Always succeeds; unbounded. No backpressure — see the diff table below. */
    public void enqueue(E item) {
        if (item == null) {
            throw new NullPointerException("MichaelScottQueue rejects null, same as ConcurrentLinkedQueue");
        }
        Node<E> newNode = new Node<>(item);
        while (true) {
            Node<E> currentTail = tail.get();
            Node<E> tailNext = currentTail.next.get();
            if (currentTail != tail.get()) {
                continue; // tail changed under us mid-read; restart
            }
            if (tailNext != null) {
                // tail is lagging one node behind the real last node — help advance it, then retry.
                tail.compareAndSet(currentTail, tailNext);
                continue;
            }
            // tailNext is null: currentTail really is the last node. Link the new node in.
            if (currentTail.next.compareAndSet(null, newNode)) {
                // Logically enqueued the instant this CAS wins, regardless of what happens next.
                tail.compareAndSet(currentTail, newNode); // best-effort; ok if this loses the race
                return;
            }
            // else: someone else linked first, loop and retry from a fresh read.
        }
    }

    /** Returns null on empty, matching Queue.poll(), never throws on empty. */
    public E dequeue() {
        while (true) {
            Node<E> currentHead = head.get();
            Node<E> currentTail = tail.get();
            Node<E> headNext = currentHead.next.get();
            if (currentHead != head.get()) {
                continue; // head changed under us mid-read; restart
            }
            if (currentHead == currentTail) {
                if (headNext == null) {
                    return null; // truly empty: dummy has no successor
                }
                // head == tail but headNext isn't null: tail is lagging behind an in-flight
                // enqueue. Help advance it, exactly as enqueue would, then retry.
                tail.compareAndSet(currentTail, headNext);
                continue;
            }
            // Read the item BEFORE the CAS: after head moves, another thread may self-link
            // or reuse this node, and re-reading item afterward would be racy.
            E item = headNext.item;
            if (head.compareAndSet(currentHead, headNext)) {
                currentHead.next.set(currentHead); // self-link the retired dummy: p.next == p
                return item;
            }
            // else: someone else dequeued first, loop and retry.
        }
    }

    public boolean isEmpty() {
        Node<E> currentHead = head.get();
        return currentHead.next.get() == null;
    }

    /** O(n) and approximate: a concurrent snapshot of a moving structure has no single true size. */
    public int size() {
        int count = 0;
        Node<E> node = head.get().next.get();
        while (node != null) {
            count++;
            node = node.next.get();
        }
        return count;
    }

    /** Convenience wrapper matching Queue.remove()'s throwing contract. */
    public E dequeueOrThrow() {
        E item = dequeue();
        if (item == null) {
            throw new NoSuchElementException("no settlement records pending");
        }
        return item;
    }
}
```

Every `settlement-ingest-N` thread calls `enqueue` for each settled `WithdrawalTransaction`; a fixed
pool of `payment-run-worker-N` threads calls `dequeue` in a loop, batching whatever they drain into
the next `PaymentRun`. Neither side ever holds a lock that the other waits on.

### The cost

`enqueue` allocates one `Node` and performs one or two CASes per call (one guaranteed, one
best-effort); under heavy contention the "help advance tail" branch means a slow producer's enqueue
can be completed on its behalf by a faster one, which is a throughput win but means a single
`enqueue` call's *wall-clock* cost is not bounded by that thread's own progress alone. `dequeue`
performs at most one CAS on the happy path but must retry the entire read-read-read sequence from
scratch on any interference, including interference on `tail` that has nothing to do with the head
side — a dequeuing thread pays for a lagging tail even though dequeue never advances `tail` for its
own sake, only to unblock its own empty-check. `size()` walks the entire live chain and is O(n); on
a queue draining at 3,400 settlements/sec burst, calling `size()` for anything other than rough
monitoring is a self-inflicted bottleneck — the JDK's own `ConcurrentLinkedQueue.size()` carries the
identical warning.

**Pitfall:** treating `enqueue`'s return as confirmation that the internal state is fully
consistent. The moment the `next`-CAS in step 2 wins, the element is logically in the queue and
visible to a concurrent `dequeue`, but `tail` itself may still point at the *previous* node for an
arbitrary stretch of wall-clock time if the thread that just linked it stalls before its own
best-effort `tail` CAS. Code that reads `tail` directly to "find the last element" (instead of going
through `enqueue`/`dequeue`) is reading a value that can be one hop behind reality by design, not by
bug.

**Insight:** the lagging tail is not a bug tolerated for simplicity — it is the mechanism that makes
`enqueue` a single point of atomicity. If `enqueue` had to CAS both `tail.next` *and* `tail` itself
as one atomic unit, it would need a double-word CAS the JVM does not have (the same problem
`AtomicStampedReference` solves with boxing in 04-treiber-stack-and-aba.md). Splitting the two CASes
and making *every* thread — not just the original enqueuer — responsible for finishing the second
one is what lets the algorithm stay lock-free with only single-word CAS.

### Diff vs the real one — `ConcurrentLinkedQueue`

| Dimension | `MichaelScottQueue<E>` above | `java.util.concurrent.ConcurrentLinkedQueue<E>` |
|---|---|---|
| Core algorithm | Michael–Scott, textbook shape | Michael–Scott, same lineage, per JDK source comments crediting the 1996 paper |
| CAS primitive | `AtomicReference<Node<E>>` per field | `VarHandle` CAS directly on `item`/`next` fields, no per-field wrapper object |
| Dummy-node identity | fixed dummy created in the constructor, never revisited as a special case | the JDK implementation allows the head node itself to *become* self-linked and lazily updates which node is "head" during traversal, an optimization on top of the same core idea |
| Self-link handling on stale traversal | `p.next == p` triggers a caller-side restart-from-head in any code that walks the list (e.g. `size()`) | identical technique — an `updateHead` helper detects self-links during iteration and restarts from the current `head` |
| `size()` | O(n), single-pass walk, explicitly approximate | O(n), explicitly documented as "may return inaccurate results if elements are added or removed during traversal" |
| Null policy | rejects `null` items, matching the JDK | `null` rejected — used internally to mean "no such element" |
| Iterator | none provided | full weakly-consistent `Iterator`, tolerates concurrent structural change without `ConcurrentModificationException` |
| Why the JDK bothers | — | additional lazy-update optimizations to reduce CAS traffic on `head`/`tail` under sustained load, plus the iterator machinery a hand-rolled queue skips |

## 4.4.6 [PROVE] The linearization points, and why the lagging tail does not move them

### What a linearization point is, restated for this queue

A concurrent operation's linearization point is the single instant at which it can be said to have
"taken effect" for every other thread simultaneously — the one atomic step after which its result is
visible to all observers and before which it is invisible to all of them. For a non-blocking
structure built from CAS retry loops, the linearization point is almost always *the CAS that
succeeds*, because that is the only step in the whole operation that is genuinely atomic with
respect to every other thread; everything else (reads, comparisons, retry decisions) is just a
thread privately deciding what to try next.

### Enqueue's linearization point: the successful `tail.next` CAS

`enqueue(item)` linearizes at the instant its `currentTail.next.compareAndSet(null, newNode)` call
succeeds — **not** at the subsequent best-effort `tail.compareAndSet(currentTail, newNode)`, and
**not** at the method's return.

**The argument.** Before that CAS succeeds, no other thread's traversal starting from `head` can
ever reach `newNode`: the only pointer that could lead there is `currentTail.next`, and it is still
`null`. The instant the CAS succeeds, `currentTail.next` holds `newNode`, and any thread walking the
chain from `head` — including a concurrent `dequeue` performing its emptiness check, or another
`enqueue` reading `tail.next` to decide whether to help — will now see it. This is a binary,
instantaneous flip from "unreachable from head" to "reachable from head," which is exactly what
linearization requires: a single point separating "has not happened" from "has happened," visible
identically to every other thread from that point on. The `tail` pointer itself never enters this
argument.

### Dequeue's linearization point: the successful `head` CAS

`dequeue()` linearizes at the instant its `head.compareAndSet(currentHead, headNext)` call succeeds.

**The argument.** Before that CAS, `head` still points at `currentHead` (the old dummy), so the
value `headNext.item` remains logically "still in the queue" — a concurrent `dequeue` attempt by
another thread reading `head` would observe the same `currentHead`/`headNext` pair and race for the
same CAS. The instant this thread's CAS wins, `head` now points at `headNext`; the item that used to
live at `headNext.item` is, from every other thread's perspective, gone from the queue in that same
instant — any other `dequeue` now reads a *different* `head` and cannot also claim the item this
thread just claimed, because CAS's atomicity guarantees only one caller observes `head.get() ==
currentHead` as true and wins. The subsequent self-link (`currentHead.next.set(currentHead)`) is
pure cleanup for stale traversers — it happens strictly after the linearization point and changes
nothing about which thread received which item.

### Why the lagging `tail` does not move either linearization point

This is the load-bearing argument the whole design rests on, and it is subtle enough to state
directly: **`tail` is never read by any correctness-relevant check in `dequeue`, except to decide
whether to help advance it — and helping-to-advance is idempotent and order-independent.**

Walk through what would go wrong if this were false. Suppose, counterfactually, that some other
thread's correctness depended on `tail` being exactly current — say, a hypothetical `peekLast()`
that trusted `tail.get().item` as "the last item in the queue" without checking `tail.next`. That
method would be **wrong** during exactly the window this file's D-178 diagram depicts: the window
between step 2's first CAS (linking `newNode` onto `currentTail.next`) and its second, best-effort
CAS (swinging `tail` to `newNode`). During that window `tail` still names the *previous* last node,
even though a new one is already reachable and linearized-in. This is real and is why the algorithm
explicitly does **not** provide `peekLast()`, and why this file's `dequeue` never trusts `tail`
directly — it only ever uses `tail` as a hint to decide "should I help swing this forward," and it
re-derives correctness from `head`/`head.next` alone.

The reason this laxity is safe rather than a bug: every operation that *needs* `tail` to be current
for its own progress — `enqueue` linking a second node behind a first that hasn't had its `tail` CAS
applied yet, or `dequeue`'s `currentHead == currentTail` branch noticing `headNext != null` — performs
the same single-word CAS (`tail.compareAndSet(currentTail, headNext-or-tailNext)`) that the original
enqueuer would have performed itself. Because that CAS is idempotent (CASing `tail` from the same
stale value to the same correct value succeeds identically whichever thread executes it, and simply
no-ops as a failed CAS for every thread that arrives after the first one to succeed), it does not
matter *which* thread advances `tail`, or *when*, relative to any other thread's enqueue or dequeue.
`tail` is allowed to be stale by exactly one hop, for an arbitrary duration, because nothing that
determines an enqueue's or a dequeue's linearization point ever consults it directly — only `head`,
`head.next`, and `tail.next` (never `tail` itself as a value) participate in either argument above.
This is precisely why leaf 4.4.5's implementation reads `tailNext = currentTail.next.get()` rather
than trusting `tail` to already be the true last node: the correctness argument routes entirely
around `tail`'s currency.

**Why the dummy node is required.** Without a permanent non-data dummy, `head` and `tail` would need
to be `null` when the queue is empty, and enqueueing the first real element would need to
simultaneously establish *both* `head` and `tail` pointing at it — two independent CAS targets that
cannot be updated atomically together without the double-word CAS the JVM does not provide (the same
constraint 4.4.5's Insight named). Keeping a dummy always present means `head` and `tail` are never
`null` and the empty/one-element/many-element cases never diverge in shape: `enqueue` always CASes
`someNode.next` from `null` to a new node, and `dequeue` always CASes `head` from the current dummy
to `head.next`, whether that is the first real element or the fifth. The dummy is what lets a single
CAS shape handle every queue size, including zero and one — exactly the same argument the Treiber
stack answers with the `null`-safe `top` field, except the queue needs it twice, once per end.

**Interview:** "Where exactly does an enqueue take effect if `tail` doesn't move until a second CAS?"
— at the first CAS, the one that links the new node into `currentTail.next`; that is the only step
visible identically to every other thread from that instant on, and `tail`'s own position is
deliberately allowed to lag because every consumer of `tail` treats it as a hint to help-advance, not
as ground truth.

> Enqueue linearizes at the CAS that links the new node into the previous last node's `next` field;
> dequeue linearizes at the CAS that advances `head` past the dummy; the `tail` pointer's own
> position never participates in either argument, because every operation that needs `tail` current
> re-derives it via the same idempotent help-advance CAS rather than trusting `tail.get()` directly.

## Pitfalls

### Trusting `tail` as "the current last element"

**Wrong**
```java
E lastItemSeen = tail.get().item; // "tail always points at the last node, right?"
```
For the window between an enqueue's node-linking CAS and its tail-swinging CAS, `tail` still names
the *previous* node — this read can return stale or wrong data, or throw if it happens to read the
dummy's `null` item.

**Right**
```java
// There is no safe direct peekLast(). Drain via dequeue(), or walk from head if you must inspect.
Node<E> node = head.get();
Node<E> last = node;
while ((node = node.next.get()) != null) {
    last = node;
}
E lastItemSeen = last.item; // O(n), but correct: derived from head, not from tail
```
**Why people believe it:** the field is literally named `tail`, and in a sequential mental model
"the tail field points at the tail" sounds tautological — the two-CAS split that deliberately lets it
lag is easy to miss unless you've traced the algorithm's help-advance step yourself.

### Assuming `enqueue`'s return means `tail` is now current

**Wrong** — code that calls `enqueue(x)` and then immediately assumes `tail.get()` names the node
just added, e.g. to grab a reference for later use without going through `dequeue`.

**Right** — never read `tail` for anything except deciding whether to help-advance it; if you need a
handle to the node you just enqueued, capture the `Node` reference before the call, not by reading
`tail` after.

**Why people believe it:** the best-effort second CAS *usually* wins immediately on an uncontended
queue, so this bug is invisible in a single-threaded test and only surfaces under real concurrent
load, exactly the shape of bug the algorithm is designed to tolerate internally but that external
callers must not rely on.

## Cheat sheet

| Concept | One-line fact |
|---|---|
| Structure | dummy head node; `head`/`tail` are independent `AtomicReference<Node<E>>` fields |
| `enqueue` | CAS `tail.next` from `null` to new node (linearization point), then best-effort CAS `tail` forward |
| `dequeue` | CAS `head` from dummy to `head.next` (linearization point); read item before the CAS |
| Lagging tail | `tail` can be one hop stale by design; any thread needing it current helps advance it with the same idempotent CAS |
| Self-link | retired dummy sets `next = this`; a stale traverser sees `p.next == p` and restarts from `head` |
| Why the dummy is required | avoids needing to atomically establish both `head` and `tail` on the first insert — no double-word CAS available |
| `enqueue` linearization point | the successful `tail.next` CAS, not the `tail`-swing CAS, not the return |
| `dequeue` linearization point | the successful `head` CAS |
| `size()` | O(n), explicitly approximate, same warning as `ConcurrentLinkedQueue` |
| ABA exposure | same as the Treiber stack (04): safe by GC reachability unless nodes are pooled |
| `ConcurrentLinkedQueue` diff | `VarHandle` CAS, weakly-consistent iterator, same self-link technique |

## Self-test

**Q1.** Why does `enqueue` need two separate CASes instead of one?

<details><summary>Answer</summary>

Linking the new node in (`tail.next` from `null` to the node) and advancing `tail` to point at it
are two logically separate pointer updates on two different fields. The JVM has no native
double-word CAS that could update both atomically as one operation (the same limitation
`AtomicStampedReference` works around by boxing, in 04-treiber-stack-and-aba.md). Splitting them
into two single-word CASes, and making the second one a "best-effort, anyone can finish it" step,
is what lets the algorithm stay lock-free using only ordinary single-word CAS.

</details>

**Q2.** A thread calls `enqueue`, its `tail.next` CAS succeeds, and it is then descheduled before
its `tail`-swinging CAS runs. What happens to the queue in the meantime, and is anything broken?

<details><summary>Answer</summary>

The new node is already fully enqueued and visible — a concurrent `dequeue` can already retrieve
earlier elements up to it, and a concurrent `enqueue` will notice `tail.next != null` on its next
attempt and help swing `tail` forward itself before proceeding. Nothing is broken: the queue's
correctness never depended on the descheduled thread finishing its own second CAS, which is
precisely the point of making that step idempotent and thread-agnostic.

</details>

**Q3.** Why must `dequeue` read `headNext.item` before performing the `head` CAS, rather than after?

<details><summary>Answer</summary>

After the CAS succeeds, `currentHead` (the old node about to become the new dummy) may immediately
be self-linked or become eligible for reuse by another thread's logic; reading `item` off a node
after it has left the live structure risks reading a value that has since been mutated or cleared
for a different purpose. Reading it first, while the node is still guaranteed to be exactly what the
CAS is about to validate against, is the only point at which the read is guaranteed race-free.

</details>

**Q4.** What condition does `dequeue` check to distinguish "the queue is genuinely empty" from "an
enqueue is in flight and the tail is lagging," and why do both cases show `head == tail`?

<details><summary>Answer</summary>

Both cases show `head == tail` because in a genuinely empty queue there is only the dummy, which
both pointers name; and during an in-flight enqueue that has linked its node but not yet swung
`tail`, `tail` still names the old last node — which, if the queue had exactly one element before
this enqueue, is also what `head` names. The distinguishing check is `headNext == null`: if it's
`null`, there truly is no successor and the queue is empty; if it's non-`null`, `tail` is lagging
behind a real, already-linearized-in enqueue, and `dequeue` helps advance `tail` before retrying.

</details>

**Q5.** State the exact linearization point of `enqueue`, and explain in one sentence why it is not
the best-effort `tail`-swinging CAS.

<details><summary>Answer</summary>

The linearization point is the successful `compareAndSet(null, newNode)` on `currentTail.next`. It
is not the `tail`-swinging CAS because that second CAS changes nothing about which nodes are
reachable from `head` — the new node was already reachable, and thus already visible to every other
thread, the instant the first CAS succeeded; the second CAS only updates a hint field that other
threads use to decide whether to help, not a field any correctness argument depends on.

</details>

**Q6.** Why is the dummy node required at all — what would go wrong with a `head`/`tail` design that
starts both fields as `null` on an empty queue?

<details><summary>Answer</summary>

Enqueueing into an empty `null`/`null` queue would need to atomically set both `head` and `tail` to
point at the new node in one step, since there is no existing node whose `next` field could be
CASed. That is a two-field atomic update with no single-word CAS available, the same double-word
limitation that forces `enqueue`'s two-step design for every subsequent element. Keeping a permanent
non-data dummy present means the first real element is inserted by the exact same single CAS shape
(`dummy.next` from `null` to the new node) as every later element, so no special-cased "is this the
first insert" branch is ever needed.

</details>

**Q7.** Why does a stale traverser need to detect `p.next == p` rather than simply following `next`
until it hits `null`?

<details><summary>Answer</summary>

Once a node is dequeued, it is no longer part of the live queue but a thread that read a reference to
it before the dequeue may still be mid-traversal holding that reference. If the retired node's `next`
were left pointing at whatever it pointed to while live, a stale traverser would keep walking through
now-detached, logically-removed nodes — memory that has left the structure but happens to still be
linked internally. Self-linking (`p.next = p`) turns that into a detectable, unambiguous signal: any
traverser that ever reads `node.next == node` knows immediately it has fallen off the live chain and
must restart from the current `head`, rather than silently walking a dead sublist.

</details>

**Q8.** Two `payment-run-worker` threads call `dequeue()` concurrently against a queue holding
exactly one settlement record. Walk through why only one of them can receive that record.

<details><summary>Answer</summary>

Both threads read the same `currentHead` (the dummy) and the same `headNext` (the one real node),
and both read the same item off `headNext.item`. Both then attempt
`head.compareAndSet(currentHead, headNext)`. CAS guarantees that only one caller observes the
precondition `head.get() == currentHead` as true and successfully writes; the other's CAS fails
because by the time it executes, `head` no longer equals `currentHead`. The losing thread detects
the failed CAS, loops, re-reads `head` (now the former `headNext`), sees its own `next` is `null`,
and returns `null` for empty — it never returns the item, even though it computed the same `item`
value locally, because it never won the linearizing CAS.

</details>

---

**Leaves covered:** 4.4.5–4.4.6 (2 leaves)
**Leaves deferred:** none
**Diagrams included:** D-178
**Target version:** Java 21 LTS
**Lines:** 508
