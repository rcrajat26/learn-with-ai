# 05 Multithreading and Concurrency — Bounded blocking queue: the monitor and condition versions — BUILD IT (§4.3, leaves 4.3.1–4.3.2)

**Target version: Java 21 LTS.** | **Part 4 of 5** | [Index](../00-index.md)
Previous: [The consolidated AQS diff table](02c-aqs-consolidated-diff.md) · Next: [The two-lock queue and timed operations](03b-two-lock-queue-and-timed-ops.md)

## Hierarchy before details

Three ways to build the same bounded queue, all correct, all shipping different tradeoffs. This file
builds the first two; the third is the subject of the next file, but its row belongs in this table
because the whole point of §4.3 is comparing all three side by side before committing to one.

**D-203 — Three bounded queues, three signalling schemes**

| Version | Waiters woken per operation | Producers/consumers contend on the same lock? | Allocation per element | Cascading-signal rule | Correctness obligation |
|---|---|---|---|---|---|
| `synchronized` + `wait`/`notifyAll` | All waiters on the object's single wait set — one queue for both `notFull` and `notEmpty` waiters | Yes — one monitor, one wait set, producers and consumers block each other even when the operations are logically independent | None beyond the ring buffer's backing array (elements only) | `notifyAll()` on every state change; no signal can be scoped narrower than "everyone" | Every waiter must re-check its predicate in a `while` loop — `notifyAll` wakes threads waiting on the wrong predicate too |
| `ReentrantLock` + `notFull`/`notEmpty` `Condition`s | Exactly one, chosen by which `Condition` is signalled | Yes — still one lock, but the two `Condition`s split the wait *set*, not the lock it's mutual exclusion | None beyond the ring buffer's backing array | `signal()` targets the correct condition directly; no cascade needed because the predicate space is split at the `Condition` level | Producer must signal `notEmpty` (not `notFull`) and vice versa — swapping the two silently reintroduces lost wakeups |
| Two locks (`putLock`/`takeLock`) + `AtomicInteger count` (next file) | Exactly one, and only within the relevant lock's own conditions | **No** — producers hold only `putLock`, consumers hold only `takeLock`; they contend only at the boundary transitions (empty→non-empty, full→non-full) | None beyond the ring buffer's backing array | A `count` transition across 0 or `capacity` triggers a cross-lock signal — this is the one place correctness depends on *which* lock you are holding when you read `count` | The two locks must never be acquired in the opposite order by any code path, or this becomes a deadlock waiting to happen |

The third row is built in [`03b-two-lock-queue-and-timed-ops.md`](03b-two-lock-queue-and-timed-ops.md) —
it is placed here because this table is the map for the whole of §4.3, not just this file.

Both versions built below solve the identical problem: a queue of `WithdrawalTransaction`s, capacity
1,000, fed by `settlement-ingest-N` producer threads submitting bank withdrawals (running at roughly
7k/day in steady state, arriving in bursts) and drained by consumer threads assembling a `PaymentRun`.
Two producers and two consumers share the queue in both examples, matching the wait-set scenario this
set has used since Day 14's `wait`/`notifyAll` walkthrough.

## 4.3.1 — `synchronized` + `wait`/`notifyAll` over an array ring buffer

**Mental model first.** Picture a single locked room with one door. Everyone waiting to get in —
whether they're waiting to *drop something off* (a producer, blocked because the room is full) or
waiting to *pick something up* (a consumer, blocked because the room is empty) — stands in the same
hallway outside that one door. When anyone inside the room changes anything and shouts "next!", the
whole hallway stirs, checks whether the thing *they* were waiting for is now true, and everyone whose
condition still isn't true goes back to waiting. It is crude, but it is impossible to get the "who do I
wake" question wrong, because there is no such question — you always wake everyone and let them
self-select.

**Why it exists.** Before `java.util.concurrent` existed at all (Java 1.0–1.4), `synchronized` plus the
`Object` monitor methods (`wait`/`notify`/`notifyAll`) were the *only* blocking coordination primitive
in the language. A bounded producer–consumer queue is one of the oldest coordination problems in
concurrent programming, and this is the oldest correct Java idiom for solving it — every later version
in this file exists to fix a specific cost this one pays.

**When to reach for it, and when not.** Reach for it when you need a self-contained, dependency-free,
JDK 1.0-portable blocking queue and the workload is light enough that thundering-herd wakeups are not a
measurable cost — a small internal queue behind a low-throughput admin endpoint, for instance. Do not
reach for it once producer and consumer arrival rates both matter under load: `notifyAll()` wakes every
waiter on every operation, including waiters whose predicate cannot possibly be true, which is wasted
work under contention. The direct sibling that wins there is 4.3.2, the two-`Condition` version below,
which signals exactly the waiters that can proceed.

**How it works.** The queue is a fixed-size array used as a ring buffer: a `head` index for the next
element to remove, a `tail` index for the next slot to fill, and a `count` of how many elements are
currently held, all three protected by the object's own intrinsic lock (the `synchronized` keyword on
each method, or an explicit `synchronized (this)` block). `put` blocks while `count == capacity`; `take`
blocks while `count == 0`. Both block by calling `wait()`, which atomically releases the monitor and
parks the calling thread on the object's *wait set* — a data structure JLS §17.2 specifies belongs to
the monitor itself, not to any particular predicate. `notifyAll()`, called after every successful `put`
or `take`, moves every parked thread from the wait set back onto the queue contending for the monitor;
each one, on reacquiring it, must re-evaluate its own `while` condition before proceeding, because
`notifyAll` carries no information about *which* predicate became true.

**Insight:** the `while` loop, not `notify` vs `notifyAll`, is what actually keeps this correct. Even if
this version used a hypothetical "smart notify" that only woke waiters whose exact predicate held, the
loop would still be required — JLS 17.2 explicitly permits spurious wakeups, where `wait()` returns with
no `notify` at all having happened, and a woken thread can also lose a race to another woken thread that
drained the last element between the notify and its own re-acquisition of the monitor.

**D-203 above** is the map for this: this row shows one shared wait set and a mandatory `notifyAll`,
which is the direct cause of the "all waiters check" behavior below.

```java
import java.util.concurrent.TimeUnit;

record Money(long minorUnits) {
    Money {
        if (minorUnits < 0) throw new IllegalArgumentException("minorUnits must be >= 0: " + minorUnits);
    }
}

record WithdrawalTransaction(String withdrawalId, Money amount) {}

/**
 * A bounded ring-buffer queue of WithdrawalTransactions feeding a PaymentRun, built with
 * synchronized + wait/notifyAll. Two settlement-ingest-N producers submit withdrawals; two
 * PaymentRun assembly consumers drain them, sharing one wait set for both directions.
 */
final class MonitorWithdrawalQueue {
    private final WithdrawalTransaction[] items;
    private int head = 0;
    private int tail = 0;
    private int count = 0;

    MonitorWithdrawalQueue(int capacity) {
        if (capacity <= 0) throw new IllegalArgumentException("capacity must be > 0: " + capacity);
        this.items = new WithdrawalTransaction[capacity];
    }

    /** Called by a settlement-ingest-N producer thread. Blocks while the ring buffer is full. */
    public synchronized void put(WithdrawalTransaction withdrawal) throws InterruptedException {
        if (withdrawal == null) throw new NullPointerException("withdrawal must not be null");
        while (count == items.length) {
            wait();
        }
        items[tail] = withdrawal;
        tail = (tail + 1) % items.length;
        count++;
        notifyAll();
    }

    /** Called by a PaymentRun assembly consumer thread. Blocks while the ring buffer is empty. */
    public synchronized WithdrawalTransaction take() throws InterruptedException {
        while (count == 0) {
            wait();
        }
        WithdrawalTransaction withdrawal = items[head];
        items[head] = null;
        head = (head + 1) % items.length;
        count--;
        notifyAll();
        return withdrawal;
    }

    /** Snapshot only — the count may change the instant this returns. */
    public synchronized int size() {
        return count;
    }
}
```

**The gotcha.** Writing `if (count == items.length) wait();` instead of `while (count == items.length)
wait();` is the single most common defect in hand-rolled monitor queues, and it is subtle because it
only manifests under concurrency — a single-producer, single-consumer smoke test will never trigger it.
With two consumers racing to drain the last element: consumer A calls `take()`, sees `count == 0` is
false, proceeds to grab the element — then before A finishes, the JVM schedules consumer B, whose
earlier `wait()` (parked when the queue was empty) has just been woken by a producer's `notifyAll()`.
If B used `if` instead of `while`, it resumes execution *after* the `wait()` call believing the queue is
non-empty without ever re-checking, and reads a stale or already-consumed slot. `while` forces every
waking thread to re-verify its own predicate against current state, no matter how it got woken.

**Pitfall:** believing `notify()` is a safe drop-in replacement for `notifyAll()` here because "only one
thread needs to wake up." With one shared wait set holding both producers and consumers, `notify()`
picks an arbitrary thread from the set — it could wake a still-blocked producer when only a consumer
could actually proceed, and vice versa. The producer re-checks its `while (count == items.length)`,
finds it still true, and goes back to sleep — and because `notify()` already consumed the one wakeup
this round, the consumer that could have proceeded never gets woken at all. This is a **lost wakeup**,
and it can deadlock the whole queue permanently if no further `put`/`take` calls ever arrive to trigger
another `notifyAll()`. `notifyAll()` is not an optimization here — it is a correctness requirement, paid
for with the cost the D-203 table's first row already calls out: every waiter, including every waiter
whose predicate is still false, wakes up and re-blocks.

**Interview:** "Why does this queue use `notifyAll()` and not `notify()`, and what's it costing you?" —
answer: because the wait set is shared between two independent predicates (not-full and not-empty) and
`notify()` cannot target one over the other, so using it risks a permanent lost wakeup; the cost paid
for correctness is a full "wake everyone, most go back to sleep" cycle on every single `put`/`take`,
which is exactly the cost the two-`Condition` version below removes.

> **A `synchronized`/`wait`/`notifyAll` bounded queue keeps every waiter — producers and consumers alike
> — on one monitor's single wait set, and pays for that simplicity with a mandatory `notifyAll()` on
> every operation and a `while`-guarded re-check by every thread it wakes.**

## 4.3.2 — `ReentrantLock` with two `Condition`s (`notFull`, `notEmpty`)

**Mental model first.** Same locked room, but now there are two separate hallways outside two separate
doors into it — one hallway for people waiting to drop something off, one for people waiting to pick
something up. The room still only lets one person in at a time (there's still one lock), but when
something is dropped off, only the pickup hallway gets called; when something is picked up, only the
drop-off hallway gets called. Nobody stands in the wrong hallway, and nobody in either hallway wakes up
to find their reason for waiting still unresolved.

**Why it exists.** `notifyAll()` in the monitor version wakes every waiter regardless of which predicate
it is blocked on, because the intrinsic monitor JLS gives every object exactly one wait set — there is
no way to ask it for "wake only the not-empty waiters." `java.util.concurrent.locks.Condition`,
introduced with `java.util.concurrent.locks.Lock` in Java 5 (JSR-166, Doug Lea), exists specifically to
split that one wait set into as many independently-signallable wait sets as a lock needs. `ArrayBlockingQueue`
itself is built exactly this way — one `ReentrantLock`, two `Condition`s — which is why this version, not
the monitor version, is what production Java code actually reaches for.

**When to reach for it, and when not.** Reach for it whenever a bounded buffer has two or more logically
distinct wait predicates guarded by the same lock — `notFull`/`notEmpty` is the canonical pair, but the
same shape applies to bulk-drain thresholds or watermark-based backpressure. Do not reach for it when
producers and consumers should not contend on the same lock at all: at very high throughput with both
sides hot, even signalling the exactly-right condition still means every `put` and every `take`
serializes through one shared `ReentrantLock`. That is precisely the case the next file's two-lock
version is built for — it is the sibling that wins once contention, not signalling precision, is the
bottleneck.

**How it works.** `ReentrantLock.newCondition()` returns a `ConditionObject`, which is its own AQS-based
wait queue chained off the same lock's synchronization state — the same mechanism this file's earlier
siblings in `02b-aqs-fairness-and-conditions.md` already built and used. `await()` on a `Condition`
atomically releases the lock and parks the calling thread on *that condition's own queue*, not on any
shared object wait set. `signal()` wakes exactly the head of that one queue — moving it onto the lock's
main acquire queue to contend for re-entry — leaving every thread parked on the *other* condition
completely undisturbed. Because `notFull` and `notEmpty` are two separate `ConditionObject` instances,
a `put()` that transitions the queue from empty to non-empty can call `notEmpty.signal()` and guarantee
that only a consumer, never another producer, is woken.

**D-203, second row:** this is the "exactly one, chosen by which `Condition` is signalled" line — the
mechanism that removes the wasted-wakeup cost the monitor row above pays on every call.

```java
import java.util.ArrayDeque;
import java.util.Deque;
import java.util.concurrent.locks.Condition;
import java.util.concurrent.locks.ReentrantLock;

/**
 * A bounded queue of WithdrawalTransactions feeding a PaymentRun, built with a real
 * java.util.concurrent.locks.ReentrantLock and two Conditions. Same two-producer,
 * two-consumer settlement-ingest-N shape as MonitorWithdrawalQueue above, but each
 * put/take signals only the waiters that can actually proceed.
 */
final class ConditionWithdrawalQueue {
    private final ReentrantLock lock = new ReentrantLock();
    private final Condition notFull = lock.newCondition();
    private final Condition notEmpty = lock.newCondition();
    private final Deque<WithdrawalTransaction> items = new ArrayDeque<>();
    private final int capacity;

    ConditionWithdrawalQueue(int capacity) {
        if (capacity <= 0) throw new IllegalArgumentException("capacity must be > 0: " + capacity);
        this.capacity = capacity;
    }

    /** Called by a settlement-ingest-N producer thread. Blocks while the queue is full. */
    public void put(WithdrawalTransaction withdrawal) throws InterruptedException {
        if (withdrawal == null) throw new NullPointerException("withdrawal must not be null");
        lock.lock();
        try {
            while (items.size() == capacity) {
                notFull.await();
            }
            items.addLast(withdrawal);
            notEmpty.signal();
        } finally {
            lock.unlock();
        }
    }

    /** Called by a PaymentRun assembly consumer thread. Blocks while the queue is empty. */
    public WithdrawalTransaction take() throws InterruptedException {
        lock.lock();
        try {
            while (items.isEmpty()) {
                notEmpty.await();
            }
            WithdrawalTransaction withdrawal = items.removeFirst();
            notFull.signal();
            return withdrawal;
        } finally {
            lock.unlock();
        }
    }

    /** Snapshot only — the size may change the instant this returns. */
    public int size() {
        lock.lock();
        try {
            return items.size();
        } finally {
            lock.unlock();
        }
    }
}
```

**The `signal`, not `signalAll`, correctness argument. `[PROVE]`** The claim to prove: calling
`notEmpty.signal()` inside `put()` (rather than `notEmpty.signalAll()`) never leaves a consumer waiting
forever, even with two consumers parked on `notEmpty` at once. The proof rests on three facts about this
particular queue, all present in the code above:

1. **Every `put()` adds exactly one element**, and every `take()` removes exactly one element. A single
   successful `put()` therefore makes at most one previously-blocked `take()` runnable — the queue goes
   from `size() == 0` to `size() == 1`, and only one waiter's predicate (`items.isEmpty()`) needs to
   flip from true to false.
2. **`signal()` wakes exactly the longest-waiting thread on that condition's queue** — `ConditionObject`
   maintains its own FIFO list of waiters, and `signal()` moves the head of that list to the lock's
   acquire queue. It does not pick arbitrarily and does not wake zero threads if the list is non-empty.
3. **The woken thread re-checks `while (items.isEmpty())` before proceeding**, exactly as the monitor
   version does. If some other thread — say, another consumer that was never blocked, calling `take()`
   for the first time — raced in and drained the element first, the woken thread finds `isEmpty()` true
   again and calls `notEmpty.await()` a second time, correctly going back to sleep instead of consuming
   nothing.

Combine (1) and (2): one `put()` makes at most one waiter runnable, and `signal()` wakes at most one
waiter — there is no scenario where `signal()` fails to wake a thread that could proceed, and no
scenario where it wakes a thread that unfairly consumes an opportunity meant for two waiters, because
only one opportunity was ever created. Combine with (3): even if the *wrong* consumer race wins after
being woken, the `while` loop's re-check means correctness (no double-consumption, no missed element)
is never at risk — only fairness (which thread got the element) is unspecified, and this queue makes no
fairness promise beyond whatever the underlying non-fair `ReentrantLock` provides. `signalAll()` here
would wake every consumer waiting on `notEmpty` for a single new element, all but one of which would
immediately re-check, find the queue empty again, and go back to sleep — correct, but strictly more
wasted wakeups for zero additional safety, which is exactly the cost this version exists to avoid.

**The one case this proof does not cover** is a `put()` that adds more than one element per call (a
hypothetical bulk-`putAll`) — that would require `signalAll()` or a loop of `signal()` calls matching
the number of newly-available slots, because a single `signal()` only ever wakes one waiter regardless
of how many elements became available. `put()` above adds exactly one, so this does not apply to the
code as written, but it is the boundary of the argument, not a footnote — a maintainer adding a batch
API to this class must revisit this proof, not silently reuse `signal()`.

**The gotcha.** Signalling the wrong condition compiles and often "seems" to work under light load,
which makes it dangerous. If `put()` accidentally called `notFull.signal()` instead of `notEmpty.signal()`
— an easy transcription error given how symmetric the two methods are — a consumer parked on `notEmpty`
after the queue emptied out would never be woken by that `put()`. It would remain parked until some
*other* event happens to also call `notEmpty.signal()` — for example, another `take()` completing —
which can mask the bug entirely in a workload with steady traffic on both sides, and only manifest as a
stuck consumer during a lull, exactly the kind of intermittent production incident that's hardest to
reproduce.

**Interview:** "Why does the JDK's `ArrayBlockingQueue` use two `Condition`s instead of one shared
`notifyAll`-style wakeup?" — answer: two `Condition`s let `put()` and `take()` each wake only the
waiters whose predicate they just made true, avoiding the "wake everyone, most re-block" cost of a
single shared wait set, at the price of needing to get the `signal`-vs-`signalAll` and
"which-condition" choices exactly right — get either wrong and you reintroduce the lost-wakeup class of
bug the monitor version was already vulnerable to.

> **Splitting one lock's wait set into multiple `Condition`s lets each state transition wake exactly the
> threads that transition unblocks, trading the monitor version's "wake everyone, let them figure it
> out" simplicity for a signalling discipline that must name the correct condition every time.**

## Diff vs the real one

Both classes above are teaching builds; the real `java.util.concurrent.ArrayBlockingQueue` (verified
against `ArrayBlockingQueue.java`, `jdk-21` tag, `raw.githubusercontent.com/openjdk/jdk`) differs from
each in the same handful of dimensions. The full consolidated diff table for §4.3, covering all three
versions against both `ArrayBlockingQueue` and `LinkedBlockingQueue`, lands in
[`03d-queue-consolidated-diff.md`](03d-queue-consolidated-diff.md); here is the per-leaf note for each
version built above.

### 4.3.1 (`MonitorWithdrawalQueue`) vs `ArrayBlockingQueue`

| Dimension | `MonitorWithdrawalQueue` (this file) | Real `ArrayBlockingQueue` |
|---|---|---|
| Bounds/state checks | `put`/`take` null-check the element and validate `capacity > 0` in the constructor only | Same null and capacity checks, plus `Objects.requireNonNull` with a consistent message, and `offer`/`poll` non-blocking variants this build does not have |
| Intrinsics | `synchronized` methods on `this` — the queue object itself is the lock | A private final `ReentrantLock`, not the queue object — callers can never accidentally synchronize on it externally and create a hidden coupling |
| Signalling | `notifyAll()` on every mutation — no way to target one predicate | `Condition`-based (see 4.3.2's version), never uses monitor `wait`/`notify` at all |
| Cancellation | `wait()` throws `InterruptedException`, propagated uncaught — no `tryPut`/timed variant | Full family: `offer(e, timeout, unit)`, `poll(timeout, unit)`, plus interruptible blocking as standard |
| Why the JDK bothers | A hand-rolled monitor queue is fine for a single internal buffer; production code needs timeouts so a stalled downstream `PaymentRun` consumer cannot hang a producer forever | — |

### 4.3.2 (`ConditionWithdrawalQueue`) vs `ArrayBlockingQueue`

| Dimension | `ConditionWithdrawalQueue` (this file) | Real `ArrayBlockingQueue` |
|---|---|---|
| Backing storage | `ArrayDeque<WithdrawalTransaction>`, which resizes internally and is not a fixed ring buffer over a plain array | A genuine fixed-size `Object[] items` ring buffer with `takeIndex`/`putIndex`/`count` fields — no resizing, no per-element node allocation |
| Fairness | Default non-fair `ReentrantLock` only, no constructor option | Constructor overload `ArrayBlockingQueue(int capacity, boolean fair)` — `fair = true` uses a fair `ReentrantLock`, trading throughput for FIFO-across-threads ordering |
| Serialization | Not `Serializable` | `Serializable`, consistent with the rest of `java.util.concurrent`'s collection classes |
| Null policy | Throws `NullPointerException` explicitly in `put()` | Same — `BlockingQueue` contract forbids `null` elements everywhere, and `ArrayBlockingQueue` enforces it identically |
| Spliterator/iteration | No `Iterator` implementation at all | Implements `Iterable` with a weakly-consistent iterator that never throws `ConcurrentModificationException` and reflects a reasonable, not necessarily exact, snapshot of concurrent state |
| Why the JDK bothers | A teaching build needs only `put`/`take`; production callers need `drainTo`, iteration for monitoring/dumps, and a fairness knob for latency-sensitive `settlement-ingest-N` pipelines that must not starve any one producer | — |

The full diff versus `ArrayBlockingQueue` and `LinkedBlockingQueue`, consolidated across all three §4.3
versions, lands in `03d-queue-consolidated-diff.md`.

## Pitfalls

### Using `notify()` instead of `notifyAll()` on a shared wait set

**Wrong**

```java
public synchronized void put(WithdrawalTransaction withdrawal) throws InterruptedException {
    while (count == items.length) {
        wait();
    }
    items[tail] = withdrawal;
    tail = (tail + 1) % items.length;
    count++;
    notify(); // wakes an arbitrary thread — could be another blocked producer
}
```

With two producers and two consumers sharing one wait set, this `notify()` might wake a producer that
is itself blocked on `count == items.length` — that producer re-checks, finds its own predicate still
true, and goes back to sleep, and the consumer that could have proceeded is never woken. Under a burst
that fills the queue and drains it in one pass, this manifests as consumers stalling indefinitely even
though withdrawals are sitting in the buffer.

**Right**

```java
public synchronized void put(WithdrawalTransaction withdrawal) throws InterruptedException {
    while (count == items.length) {
        wait();
    }
    items[tail] = withdrawal;
    tail = (tail + 1) % items.length;
    count++;
    notifyAll(); // every waiter re-checks; only the ones whose predicate is now true proceed
}
```

**Why people believe it:** `notify()` "sounds" like the right call because logically only one new slot
opened up, so it feels like only one thread needs to wake. That reasoning is correct about *how many*
threads can usefully proceed, but wrong about whether the JVM can pick the *right* one — a single
monitor wait set carries no information about which predicate each parked thread is waiting on.

### Signalling the wrong `Condition`

**Wrong**

```java
public void put(WithdrawalTransaction withdrawal) throws InterruptedException {
    lock.lock();
    try {
        while (items.size() == capacity) {
            notFull.await();
        }
        items.addLast(withdrawal);
        notFull.signal(); // wrong condition — should be notEmpty
    } finally {
        lock.unlock();
    }
}
```

A consumer parked on `notEmpty` is never woken by this `put()`. If no other `take()` or `put()` happens
to also call `notEmpty.signal()`, that consumer stays parked forever even though an element is sitting
in the queue waiting for it.

**Right**

```java
public void put(WithdrawalTransaction withdrawal) throws InterruptedException {
    lock.lock();
    try {
        while (items.size() == capacity) {
            notFull.await();
        }
        items.addLast(withdrawal);
        notEmpty.signal(); // put() makes the queue non-empty, so it wakes notEmpty waiters
    } finally {
        lock.unlock();
    }
}
```

**Why people believe it:** the two methods are structurally symmetric — `put` awaits `notFull` and
`take` awaits `notEmpty` — and it is easy to pattern-match "the condition I just awaited" instead of
"the condition whose predicate my action just made true," especially when copy-pasting one method to
write the other.

## Cheat sheet

| Fact | Value |
|---|---|
| Monitor version's wait set | One, shared by producers and consumers |
| Monitor version's mandatory signal call | `notifyAll()` — `notify()` risks a lost wakeup |
| Condition version's wait sets | Two — `notFull`, `notEmpty`, each a separate `ConditionObject` |
| Condition version's signal call | `signal()` on the *other* condition from the one just awaited |
| Loop guard, both versions | `while (predicate)`, never `if` |
| Why `while` and not `if` | Spurious wakeups are legal per JLS 17.2; another thread can also win the race after a wakeup |
| `Condition.await()` release scope | Releases the lock's entire hold count, re-acquires all of it on return |
| `ArrayBlockingQueue` signalling mechanism | Same shape as 4.3.2 — one `ReentrantLock`, two `Condition`s |
| `ArrayBlockingQueue` fairness knob | `ArrayBlockingQueue(capacity, fair)` constructor overload |
| Cost the two-lock version (next file) removes | Producer/consumer contention on one shared lock |

## Self-test

**Q1.** Why does `MonitorWithdrawalQueue.put()` use `while (count == items.length)` instead of
`if (count == items.length)`?

<details><summary>Answer</summary>

Because a thread woken from `wait()` is not guaranteed to find its predicate true — the JLS explicitly
permits spurious wakeups with no matching `notify` at all, and even a genuine `notifyAll()` can wake
multiple threads whose predicates only one of them can satisfy (another thread may win the race to
consume the freed slot first). `while` forces every woken thread to re-verify the actual state before
proceeding; `if` would let a thread barrel ahead on a stale assumption.

</details>

**Q2.** In `MonitorWithdrawalQueue`, why must `put()` and `take()` both call `notifyAll()` rather than
`notify()`?

<details><summary>Answer</summary>

Because both producers and consumers share the same object monitor's single wait set, and `notify()`
picks an arbitrary waiting thread with no regard for which predicate it's blocked on. If `notify()`
happens to wake a thread whose condition is still false, that thread re-blocks and the signal is wasted
— potentially leaving a thread that actually could have proceeded parked forever (a lost wakeup).
`notifyAll()` wakes everyone, and the `while` loop lets each one self-select correctly.

</details>

**Q3.** What does `ConditionWithdrawalQueue.put()` signal, and why not the condition it might seem
symmetric to await?

<details><summary>Answer</summary>

It signals `notEmpty`, not `notFull`. `put()` awaits `notFull` while the queue is full, but once it adds
an element, the queue transitions toward non-empty — that's the predicate consumers waiting on
`notEmpty` care about. Signalling `notFull` instead would wake the wrong (or no) waiters and could strand
a consumer indefinitely if no other operation happens to also touch `notEmpty`.

</details>

**Q4.** Prove that `signal()`, not `signalAll()`, is safe inside `ConditionWithdrawalQueue.put()`.

<details><summary>Answer</summary>

Each successful `put()` adds exactly one element, which can make at most one blocked `take()`'s
predicate (`items.isEmpty()`) become false. `Condition.signal()` wakes exactly the longest-waiting
thread on that condition's own FIFO queue — never zero (if one is waiting) and never more than one. So
one `put()` never needs to wake more than one `notEmpty` waiter, and `signal()` always wakes at least
one if any are parked. The woken thread still re-checks `while (items.isEmpty())` before proceeding, so
even if a different consumer races in and drains the element first, the woken thread safely re-blocks
instead of double-consuming. This breaks only if a single call can add more than one element (e.g. a
hypothetical bulk `putAll`), which `put()` as written does not do.

</details>

**Q5.** Two consumers are both parked on `notEmpty` in `ConditionWithdrawalQueue`. A producer calls
`put()` once. How many consumers actually retrieve an element, and how many wake up?

<details><summary>Answer</summary>

Exactly one consumer retrieves an element — only one element was added. `signal()` wakes exactly one of
the two parked consumers (the longest-waiting one under this class's non-fair `ReentrantLock`, though no
strict FIFO guarantee is made). The other consumer remains parked on `notEmpty` until a later `put()`
signals it.

</details>

**Q6.** What would go wrong if `ConditionWithdrawalQueue` used a single shared `Condition` for both
`notFull` and `notEmpty` instead of two?

<details><summary>Answer</summary>

It would collapse back into the same shape as the monitor version's wait set — a single queue holding
both producers and consumers — and `signal()` on that shared condition would risk waking the wrong kind
of waiter (a producer when only a consumer could proceed, or vice versa), reintroducing the lost-wakeup
risk that using two separate conditions was specifically built to eliminate. It would also force a
switch back to `signalAll()` for correctness, discarding the whole efficiency benefit of using
`Condition` over intrinsic monitors.

</details>

**Q7.** Why doesn't `MonitorWithdrawalQueue.put()` need to null-check `capacity` on every call, only in
the constructor?

<details><summary>Answer</summary>

`capacity` is captured as `items.length`, a fixed array size set once at construction and never
reassigned; the constructor already validates `capacity > 0` before allocating that array. There is no
code path that can change the array's length afterward, so re-validating it per call would be pure
overhead checking an invariant that cannot change.

</details>

**Q8.** `ArrayBlockingQueue` uses two `Condition`s from the same `ReentrantLock`. Could it instead use
two entirely separate `ReentrantLock`s, one for each condition?

<details><summary>Answer</summary>

No — a `Condition` is created by `Lock.newCondition()` and is permanently tied to the state of the lock
that created it; `await()` releases and re-acquires *that* lock's hold, not some other lock's. Two
independent locks would mean a producer and a consumer could genuinely run `put()` and `take()`
concurrently without excluding each other, which is exactly what the two-lock version in
`03b-two-lock-queue-and-timed-ops.md` does — but that requires abandoning the single shared `count`
field these two `Condition`s both rely on and replacing it with something safe to read from both locks,
such as an `AtomicInteger`, which is precisely D-203's third row.

</details>

---

**Leaves covered:** 4.3.1–4.3.2 (2 leaves)
**Leaves deferred:** none
**Diagrams included:** D-203
**Target version:** Java 21 LTS
**Lines:** 450
