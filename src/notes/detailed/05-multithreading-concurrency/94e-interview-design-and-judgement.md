# 05 Multithreading and Concurrency — Interview questions: design and judgement — INTERVIEW (§5.1, questions 5.1.116–5.1.124)

**Target version: Java 21 LTS.** | **Part 5 of 5** | [Index](00-index.md)
Previous: [Interview questions: Loom](94d2-interview-questions-liveness-and-loom-ii.md) · Next: [Interview questions: design and judgement II](94e2-interview-design-and-judgement-ii.md)

---

These are build-it questions, not recall questions. The interviewer wants the clarifying
questions first, the invariant stated before code, a compiling implementation, and the trade-off
defended against the sibling that lost. Whiteboard-length code, not teaching-length code.

## 5.1.116 — Design a thread-safe LRU cache, and defend every choice

**Clarify first:** capacity fixed or configurable at runtime? Read-heavy or write-heavy — a
`ClientRestrictions` lookup happens on every gated action, so reads dominate 50:1. Does eviction
need a callback (audit log the evicted restriction)? Single JVM or does this need to survive a
restart (it doesn't — restrictions live in the ledger; this cache is a hot-path shortcut over
2.4M clients, most of whom have zero active restrictions)?

**Invariant:** at most `capacity` entries; the least-recently-*accessed* entry is evicted first;
a `get` counts as an access that pushes an entry to most-recently-used.

```java
final class RestrictionCache<K, V> {
    private final int capacity;
    private final LinkedHashMap<K, V> map;
    private final ReentrantReadWriteLock lock = new ReentrantReadWriteLock();

    RestrictionCache(int capacity) {
        this.capacity = capacity;
        this.map = new LinkedHashMap<>(capacity, 0.75f, true) {
            @Override protected boolean removeEldestEntry(Map.Entry<K, V> eldest) {
                return size() > RestrictionCache.this.capacity;
            }
        };
    }

    V get(K clientId) {
        lock.writeLock().lock(); // access-order read still mutates the linked list
        try {
            return map.get(clientId);
        } finally {
            lock.writeLock().unlock();
        }
    }

    void put(K clientId, V restrictions) {
        lock.writeLock().lock();
        try {
            map.put(clientId, restrictions);
        } finally {
            lock.writeLock().unlock();
        }
    }
}
```

**Policy:** `LinkedHashMap(accessOrder=true)` gives O(1) get/put/evict via its internal doubly
linked list — a hand-rolled `HashMap` + `Deque` reimplements exactly this for no gain. The write
lock on `get` is the deliberate, defensible choice: access-order mutates the map's internal links
on every read, so a `ReadWriteLock` would give false safety — two concurrent "reads" would race on
the same linked-list pointers. `synchronized` on both methods is equivalent and simpler; the
`ReentrantReadWriteLock` only earns its keep if a rarer bulk-read path (`entrySet()` for an admin
dump) can safely take the read side. **Insight:** the classic "LRU cache" interview answer that
uses a `ReadWriteLock` around `get` is a correctness bug hiding behind a performance idea.

**Pitfall:** answering with `ConcurrentHashMap` alone — it has no ordering and no eviction; you'd
need a separate `ConcurrentLinkedDeque` for recency, and now updating both under one lock is
exactly the `LinkedHashMap` you avoided building.

**Follow-up:** under contention (many concurrent `get`s) a single write lock serializes every
access — for a read-heavy 2.4M-client cache the fix is **sharding**: N `RestrictionCache`
instances keyed by `clientId.hashCode() % N`, each with its own lock and its own smaller capacity.
Across two JVMs there is no shared cache at all — this is intentionally per-instance; a distributed
LRU (Redis, capacity by memory not count) is a different question with a different invariant
(cross-instance freshness, not cross-instance size).

## 5.1.117 — Design a rate limiter for "10 concurrent calls to a downstream service"

**Clarify first:** is this a *concurrency* limit (at most 10 in flight) or a *throughput* limit
(at most N per second)? The phrasing says concurrent — that's a bulkhead, not a token bucket.
Blocking or failing fast when the 11th call arrives? Fair queueing or first-ready-wins? This fronts
the identity-document verification vendor call, separate from its estate-wide 600/min cap —
10 concurrent is this service's *own* slice of that budget.

**Invariant:** at most 10 calls to the vendor are in flight at any instant; the 11th caller waits
(or fails fast) until one of the 10 completes.

```java
final class VendorConcurrencyLimiter {
    private final Semaphore permits = new Semaphore(10, true); // fair: FIFO under contention

    <T> T call(Callable<T> vendorCall, Duration timeout) throws Exception {
        if (!permits.tryAcquire(timeout.toMillis(), TimeUnit.MILLISECONDS)) {
            throw new TimeoutException("identity vendor at capacity (10 in flight)");
        }
        try {
            return vendorCall.call();
        } finally {
            permits.release();
        }
    }
}
```

**Policy:** `Semaphore` is exactly this primitive — a counter of permits with no ownership
requirement, because the thread that acquires need not be the thread that releases (a virtual
thread doing the vendor call may hand release to a callback). A `ReentrantLock` is wrong here: it
enforces mutual exclusion (1), not a counted pool (N), and it demands the releasing thread be the
acquiring thread. Fairness is deliberately on — an unfair semaphore can starve a caller
indefinitely under sustained load, and a stuck onboarding application is worse than a slower one.

**Pitfall:** using an `AtomicInteger` counter with compare-and-swap for "in flight ≤ 10" — it looks
lock-free and fast, but a thread that dies or throws between increment and decrement leaks a
permit forever with no `finally` to force cleanup. `Semaphore.release()` in a `finally` block is
the whole point.

**Follow-up:** under real contention 10 is almost always too tight in isolation — size it from
Little's law against the vendor's own p50 (900ms) and p99 (38s): at 900ms and target 5 req/s that's
~4.5 concurrent, but the p99 tail means a handful of slow calls can pin most of the 10 permits, so
production code pairs this with a **per-call timeout** shorter than the semaphore wait, not just
on the acquire. Across two JVMs a local `Semaphore` only limits *this* JVM's slice — the 600/min
estate cap needs a shared counter (Redis `INCR` with a sliding window, or the vendor's own 429s
respected as backpressure), because ten JVMs each running "10 concurrent" independently blow past
600/min without ever hitting a local limiter.

## 5.1.118 — Design a connection pool

**Clarify first:** connections to what (the PSP payout endpoint here) — expensive to establish
(TLS handshake, auth) relative to use? Fixed size or elastic between min/max? What happens on
borrow when the pool is exhausted — block, time out, or grow? Health-checked before reuse?

**Invariant:** a connection handed out by `borrow()` is never handed out again until `return()`
is called on it; the pool never exceeds `maxSize` live connections.

```java
final class PspConnectionPool implements AutoCloseable {
    private final BlockingQueue<PspConnection> idle;
    private final Semaphore capacity;
    private final Supplier<PspConnection> factory;

    PspConnectionPool(int maxSize, Supplier<PspConnection> factory) {
        this.idle = new LinkedBlockingQueue<>();
        this.capacity = new Semaphore(maxSize);
        this.factory = factory;
    }

    PspConnection borrow(Duration timeout) throws InterruptedException, TimeoutException {
        if (!capacity.tryAcquire(timeout.toMillis(), TimeUnit.MILLISECONDS)) {
            throw new TimeoutException("PSP pool exhausted");
        }
        PspConnection conn = idle.poll();
        if (conn == null || !conn.isHealthy()) {
            conn = factory.get(); // lazily create up to the permit count
        }
        return conn;
    }

    void giveBack(PspConnection conn) {
        if (conn.isHealthy()) idle.offer(conn); else conn.close();
        capacity.release();
    }

    @Override public void close() {
        idle.forEach(PspConnection::close);
    }
}
```

**Policy:** `Semaphore` caps the total (idle + borrowed), `BlockingQueue` holds the idle set — two
primitives, each doing one job, is clearer than one lock guarding both a counter and a collection.
This is the same shape as `VendorConcurrencyLimiter` above with state (a reusable connection)
riding on the permit instead of nothing; naming that similarity out loud is itself a signal in the
interview.

**Pitfall:** health-checking on *return*, not *borrow* — a connection can go stale while sitting
idle (PSP-side idle timeout), so a pool that only checks on the way back in hands out dead
connections. Check on borrow too, cheaply (a lightweight ping or a last-used timestamp).

**Follow-up:** under contention, `tryAcquire` timeouts should be short and the caller should treat
a pool-exhaustion timeout as backpressure, not retry-forever — retrying immediately just adds load
to an already-saturated pool (thundering herd). Across two JVMs, pools are per-instance by nature
(TCP connections aren't shareable across processes); the cross-JVM concern is capping the *sum* of
all instances' `maxSize` against the PSP's own connection ceiling, which is an ops/config problem,
not a code one.

## 5.1.119 — Implement a blocking queue with `wait`/`notify`

**Clarify first:** single producer/consumer or many of each? FIFO required? Bounded — this backs
the `WithdrawalTransaction` buffer feeding a `PaymentRun` at capacity 1,000.

**Invariant:** `size` is always in `[0, capacity]`; `take()` never returns while empty; `put()`
never proceeds while full.

```java
final class WaitNotifyWithdrawalBuffer {
    private final Queue<WithdrawalTransaction> items = new ArrayDeque<>();
    private final int capacity;

    WaitNotifyWithdrawalBuffer(int capacity) { this.capacity = capacity; }

    synchronized void put(WithdrawalTransaction tx) throws InterruptedException {
        while (items.size() == capacity) wait();       // must be a loop, not an if
        items.add(tx);
        notifyAll();                                    // wakes waiting takers too
    }

    synchronized WithdrawalTransaction take() throws InterruptedException {
        while (items.isEmpty()) wait();
        WithdrawalTransaction tx = items.poll();
        notifyAll();                                    // wakes waiting putters too
        return tx;
    }
}
```

**Policy:** `synchronized` + `wait`/`notifyAll` is the primitive being tested here, not the best
tool for production — this is the mechanism question, and `notifyAll` (not `notify`) is
non-negotiable with two different wait conditions sharing one monitor, or a woken putter can steal
a signal meant for a waiting taker and both sides hang.

**Pitfall:** `if (items.isEmpty()) wait()` instead of `while` — a spurious wakeup (permitted by the
JLS with no corresponding `notify`) resumes the thread with the condition still false, and it
proceeds to `poll()` a null off an empty queue.

**Follow-up:** under contention every `put`/`take` pair serializes through one monitor — real
throughput needs the `Condition`-based version next (5.1.120), which gives producers and
consumers separate wait sets. This is inherently single-JVM; a cross-JVM version of the same
invariant is what a message broker (SQS, Kafka) is for.

## 5.1.120 — Implement a bounded blocking queue with `Condition`s

Already built at teaching length in
[`build-it/03-bounded-blocking-queue.md`](build-it/03-bounded-blocking-queue.md); this is the
20-line whiteboard version.

**Invariant:** identical to 5.1.119 — same bounded `WithdrawalTransaction` buffer, capacity 1,000.

```java
final class ConditionWithdrawalBuffer {
    private final Queue<WithdrawalTransaction> items = new ArrayDeque<>();
    private final int capacity;
    private final ReentrantLock lock = new ReentrantLock();
    private final Condition notFull = lock.newCondition();
    private final Condition notEmpty = lock.newCondition();

    ConditionWithdrawalBuffer(int capacity) { this.capacity = capacity; }

    void put(WithdrawalTransaction tx) throws InterruptedException {
        lock.lock();
        try {
            while (items.size() == capacity) notFull.await();
            items.add(tx);
            notEmpty.signal();          // only wakes a taker — cheaper than signalAll
        } finally { lock.unlock(); }
    }

    WithdrawalTransaction take() throws InterruptedException {
        lock.lock();
        try {
            while (items.isEmpty()) notEmpty.await();
            WithdrawalTransaction tx = items.poll();
            notFull.signal();           // only wakes a putter
            return tx;
        } finally { lock.unlock(); }
    }
}
```

**Policy:** two `Condition`s on one `Lock` replace the single monitor's mixed wait set — `signal`
(not `signalAll`) is now correct and cheaper, because `notFull` only ever needs to wake a putter
and `notEmpty` only a taker; there is no cross-talk to guard against. This is precisely what
`LinkedBlockingQueue` does internally with two locks (`putLock`/`takeLock`) for head and tail —
naming that in the interview is the signal that you understand the JDK didn't reinvent this.

**Pitfall:** using `signal()` instead of `signalAll()` on the *wrong* condition — if put mistakenly
signals `notFull` instead of `notEmpty`, no waiting taker ever wakes and the system deadlocks
silently under load, not immediately.

**Follow-up:** under heavy contention this still shares one `ReentrantLock` between both ends —
`LinkedBlockingQueue`'s two-lock design lets a put and a take proceed fully in parallel when the
queue is neither full nor empty, which is the actual throughput win over this version. Cross-JVM:
not applicable — same note as 5.1.119.

## 5.1.121 — Print odd/even numbers alternately with two threads — three solutions

**Clarify first:** strict alternation required (never two odds in a row), or just eventually fair?
Framing: two workers alternately emitting settlement sequence numbers for a stake round, one
emits even IDs, one emits odd.

**Invariant:** the merged output is `1, 2, 3, 4, …` — no two consecutive numbers from the same
thread.

```java
// Solution 1: wait/notify on a shared "whose turn" flag
final class AlternatingSequencer {
    private int next = 1;
    private final int max;
    AlternatingSequencer(int max) { this.max = max; }

    synchronized void emitOdd() throws InterruptedException {
        while (next <= max) {
            while (next % 2 == 0) wait();
            System.out.println("odd: " + next++);
            notifyAll();
        }
    }
    synchronized void emitEven() throws InterruptedException {
        while (next <= max) {
            while (next % 2 == 1) wait();
            System.out.println("even: " + next++);
            notifyAll();
        }
    }
}

// Solution 2: two Semaphores, ping-pong
final class SemaphoreSequencer {
    private final Semaphore oddTurn = new Semaphore(1);
    private final Semaphore evenTurn = new Semaphore(0);
    void emitOdd(int n) throws InterruptedException {
        oddTurn.acquire(); System.out.println("odd: " + n); evenTurn.release();
    }
    void emitEven(int n) throws InterruptedException {
        evenTurn.acquire(); System.out.println("even: " + n); oddTurn.release();
    }
}

// Solution 3: AtomicInteger + spin (CPU-wasteful, shown to name the trade-off)
final class SpinSequencer {
    private final AtomicInteger next = new AtomicInteger(1);
    void emitOdd(int n) { while (next.get() != n) Thread.onSpinWait(); System.out.println("odd: " + n); next.incrementAndGet(); }
    void emitEven(int n) { while (next.get() != n) Thread.onSpinWait(); System.out.println("even: " + n); next.incrementAndGet(); }
}
```

**Policy:** the semaphore ping-pong is the cleanest — no shared mutable state to guard, no
`while` re-check needed beyond the acquire itself, and it generalizes trivially to N-way
round-robin by chaining N semaphores in a ring. The spin version is the deliberately-bad third
answer: it burns a core per waiter and is only ever justified when the expected wait is
sub-microsecond, which alternating print statements never are.

**Pitfall:** giving only the `wait`/`notify` version and calling it done — interviewers ask for
three specifically to see whether you know semaphores can encode turn-taking without any explicit
"whose turn" state at all.

**Follow-up:** across two JVMs, none of these three work — turn-taking needs a distributed
coordinator (a lock service, or one side polling a shared counter in a database/Redis), and the
strict alternation invariant becomes probabilistic once network latency is in the loop.

## 5.1.122 — Print A/B/C in order with three threads

Framing: three pipeline stages of a stake lifecycle — `RESERVE`, `SETTLE`, `NOTIFY` — must run in
that order, repeatedly, one thread per stage.

**Invariant:** for every round, `RESERVE` completes fully before `SETTLE` starts, and `SETTLE`
completes fully before `NOTIFY` starts.

```java
final class StagePipeline {
    private final Semaphore reserveDone = new Semaphore(0);
    private final Semaphore settleDone = new Semaphore(0);

    void reserve() { System.out.println("RESERVE"); reserveDone.release(); }
    void settle() throws InterruptedException {
        reserveDone.acquire();
        System.out.println("SETTLE");
        settleDone.release();
    }
    void notifyClient() throws InterruptedException {
        settleDone.acquire();
        System.out.println("NOTIFY");
    }
}
```

**Policy:** a chain of `Semaphore(0)` permits is a one-shot happens-before edge per stage — each
stage releases exactly the permit its successor blocks on. For a *repeating* pipeline (many
rounds) use `CyclicBarrier(3)` instead: three parties rendezvous each round, and the barrier
action can reset shared per-round state before releasing everyone, which a semaphore chain cannot
express without re-acquiring three separate permits by hand each round.

**Pitfall:** reaching for `CountDownLatch` — a latch counts down to zero exactly once and cannot
be reset, so it solves one round and silently does nothing on the second unless you allocate a
fresh latch per round, which is more code than the semaphore chain for the one-shot case.

**Follow-up:** under contention with many concurrent rounds in flight, this ordering is per-round
state, not global — each `WithdrawalTransaction`'s own `RESERVE→SETTLE→NOTIFY` needs its own
semaphore triple, not one shared across all rounds, or rounds interleave their signals. Across two
JVMs the ordering constraint becomes a workflow/orchestration concern (a state machine persisted
per transaction, or a Kafka topic per stage) rather than an in-memory primitive.

## 5.1.123 — The dining philosophers, with the resource-ordering and the arbitrator solution

Framing: five settlement workers each need two adjacent shared ledger-partition locks (a
`transfer` between two clients' wallets locks both wallets) to post a double-entry move; naive
lock-acquire-in-request-order deadlocks in a ring.

**Invariant:** a circular wait among the five workers, each holding one lock and waiting for the
next, never occurs.

```java
// Solution 1: resource ordering — always lock the lower-ID wallet first
void transfer(WalletLock a, WalletLock b) {
    WalletLock first = a.id() < b.id() ? a : b;
    WalletLock second = a.id() < b.id() ? b : a;
    first.lock();
    try {
        second.lock();
        try {
            // post the double-entry move
        } finally { second.unlock(); }
    } finally { first.unlock(); }
}

// Solution 2: arbitrator — a semaphore admits at most 4 of 5 workers at once
final class WalletArbitrator {
    private final Semaphore admission = new Semaphore(4); // one fewer than the ring size
    void transfer(WalletLock a, WalletLock b, Runnable move) throws InterruptedException {
        admission.acquire();
        try {
            a.lock();
            try { b.lock(); try { move.run(); } finally { b.unlock(); } }
            finally { a.unlock(); }
        } finally { admission.release(); }
    }
}
```

**Policy:** resource ordering (lock by ascending wallet ID, always) is the production answer —
zero extra objects, breaks the cycle by construction, since a circular wait requires every worker
to hold its lower lock while waiting for a higher one, which ordering forbids. The arbitrator is
the textbook alternative worth naming: capping concurrent admission at N−1 guarantees at least one
worker always has both locks free to acquire, so the ring can never fully close — useful only when
you cannot impose a global order on the resources (e.g. the locks are opaque handles from a
library you don't control).

**Pitfall:** "just use `tryLock` with a timeout and retry on failure" — it avoids deadlock but
trades it for livelock under load: five workers can retry in lockstep indefinitely, each backing
off and re-colliding, with no progress guarantee at all.

**Follow-up:** at real settlement volume (3,400/sec burst) resource ordering is strictly better
than the arbitrator because it adds no contention point — the arbitrator's `Semaphore(4)` becomes
a fifth hot lock that every transfer must pass through. Across two JVMs, resource ordering still
works if wallet IDs are globally comparable (they are — `ClientId` wraps a UUID), but the locks
themselves must move to a distributed lock manager or, better, to the ledger's own row-level
locking in the database, which already enforces a global order via primary-key locking.

## 5.1.124 — Implement a read-write lock

The JDK's `ReentrantReadWriteLock` mechanics are covered in
[`locks/01a-basics-reentrantlock-and-rwlock.md`](locks/01a-basics-reentrantlock-and-rwlock.md);
this is the from-scratch interview version, guarding a `ClientRestrictions` snapshot that many
gate checks read and one compliance job occasionally rewrites.

**Invariant:** any number of readers may hold the lock concurrently, **or** exactly one writer
holds it exclusively — never both at once, and a waiting writer is not starved forever.

```java
final class SimpleReadWriteLock {
    private int activeReaders = 0;
    private boolean writerActive = false;
    private int waitingWriters = 0; // writer-preferring: blocks new readers once a writer waits

    synchronized void lockRead() throws InterruptedException {
        while (writerActive || waitingWriters > 0) wait();
        activeReaders++;
    }

    synchronized void unlockRead() {
        activeReaders--;
        if (activeReaders == 0) notifyAll();
    }

    synchronized void lockWrite() throws InterruptedException {
        waitingWriters++;
        try {
            while (writerActive || activeReaders > 0) wait();
        } finally {
            waitingWriters--;
        }
        writerActive = true;
    }

    synchronized void unlockWrite() {
        writerActive = false;
        notifyAll();
    }
}
```

**Policy:** `synchronized` + `wait`/`notifyAll` again, because the state being protected (two
counters and a flag) is small and the transitions are exactly the kind of compound
check-then-act `AtomicInteger` alone can't express atomically. The writer-preference flag
(`waitingWriters`) is the deliberate design choice being defended: without it, a steady stream of
readers can starve a waiting writer forever, which for a compliance rewrite of restrictions is
unacceptable — a stale restriction outliving its intended lift window is a regulatory problem, not
just a performance one.

**Pitfall:** forgetting the writer-preference counter entirely and just checking
`writerActive || activeReaders > 0` for both sides symmetrically — it compiles, passes a two-thread
test, and starves writers the moment read traffic is continuous, which is exactly the 50:1
read-heavy shape this cache actually sees.

**Follow-up:** under contention this single monitor serializes even the *decision* to read
concurrently — `ReentrantReadWriteLock` avoids that by using AQS's shared/exclusive queue modes
instead of one lock guarding counters, letting the fast path (uncontended read) avoid any
`wait`/`notify` machinery at all. Across two JVMs there is no shared reader/writer state to
coordinate — each JVM's cache is independent, and the actual cross-JVM invariant (don't serve a
restriction more than a few seconds stale) is enforced by a short TTL or a pub/sub invalidation
message, not a lock.

---

**Leaves covered:** 5.1.116–5.1.124 (9 questions)
**Leaves deferred:** none
**Diagrams included:** none
**Target version:** Java 21 LTS
**Lines:** 519
