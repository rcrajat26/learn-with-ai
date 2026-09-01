# 05 — Multithreading and Concurrency

The highest-signal Java interview topic, because almost everyone can define `volatile` and almost
nobody can say precisely what it does not do. Read the memory-model sections twice.

---

## 1. Processes versus threads

A **process** has its own virtual address space; the OS isolates it. A **thread** is a unit of
scheduling inside a process.

Within a process, threads **share the heap, static fields, and metaspace**, and each owns its **stack,
program counter, and registers**. That split is the entire source of concurrency bugs: locals are
private and safe, anything reachable from the heap is shared and unsafe.

Context switching between threads is cheaper than between processes (no page-table swap) but is still
microseconds plus cache pollution. A platform thread in Java maps 1:1 to an OS thread and reserves
about 1 MB of stack (`-Xss`), which is why tens of thousands of platform threads is a memory and
scheduling problem — and why virtual threads exist (guide 04).

---

## 2. Thread lifecycle

`Thread.State`:

- **NEW** — created, `start()` not yet called.
- **RUNNABLE** — running or ready to run (Java does not distinguish; a thread blocked on socket I/O is
  still reported RUNNABLE, which surprises people reading thread dumps).
- **BLOCKED** — waiting to acquire a `synchronized` monitor.
- **WAITING** — `Object.wait()`, `Thread.join()`, `LockSupport.park()` with no timeout.
- **TIMED_WAITING** — the timed versions, plus `Thread.sleep`.
- **TERMINATED** — run method finished.

**Trap:** BLOCKED and WAITING mean different things in a thread dump. BLOCKED means contention on a
monitor — look for who holds it. WAITING means the thread is deliberately parked awaiting a signal.
A pile of BLOCKED threads is a lock contention problem; a pile of WAITING threads on a pool queue is
usually normal.

`start()` creates a new thread of execution; `run()` just calls the method on the current thread.
Calling `start()` twice throws `IllegalStateException`.

**Interruption** is cooperative. `interrupt()` sets a flag. Blocking methods that declare
`InterruptedException` throw it and **clear the flag**. Nothing is forcibly stopped.
`Thread.stop()` is removed — it unlocked monitors at arbitrary points and left objects broken.

---

## 3. Race conditions

A race is when correctness depends on the relative timing of threads. Two canonical shapes:

**Read-modify-write.** `count++` is three bytecode steps: read, add, write. Two threads can both read
5, both write 6, and one increment vanishes.

**Check-then-act.** The state you checked can change before you act:

```java
if (map.get(key) == null) {       // check
    map.put(key, compute());      // act — another thread may have inserted in between
}
```

Lazy initialization, "create if absent", and "check the file exists then open it" are all this bug.

The fix in both cases is to make the compound operation atomic: a lock, an atomic class, or an atomic
API on a concurrent collection.

---

## 4. synchronized — two guarantees

Every Java object has a **monitor**. `synchronized` acquires it on entry and releases on exit
(including via exception). It is reentrant: a thread already holding a monitor can reacquire it,
tracked by a hold count.

`synchronized` gives **two** guarantees, and forgetting the second is a common gap:

1. **Mutual exclusion** — one thread at a time in blocks guarded by the same monitor.
2. **Visibility** — releasing a monitor flushes writes so that a subsequent acquirer of the *same*
   monitor sees them. Formally, an unlock happens-before every later lock of that monitor.

Forms:
```java
synchronized void m() {}          // locks on `this`
static synchronized void s() {}   // locks on MyClass.class — a DIFFERENT monitor
synchronized (lock) { }           // locks on an explicit object
```

**Trap:** an instance method and a static method of the same class do not exclude each other. They use
different monitors.

**Trap:** synchronizing on a field you reassign, or on a `String` literal or boxed `Integer`. Literals
and cached boxes are shared JVM-wide, so unrelated code can deadlock with you. Use a
`private final Object lock = new Object();`.

**Trap:** two threads synchronizing on *different* objects get no exclusion and no visibility.
Guarding shared state means always the same lock.

Lock granularity: `synchronized` on a whole method serializes everything. Prefer the narrowest block
that keeps the invariant — but never do I/O or call unknown code while holding a lock.

---

## 5. volatile — visibility and ordering, NOT atomicity

`volatile` provides:
1. **Visibility** — a write is immediately visible to any subsequent read by another thread. Reads and
   writes go to main memory (conceptually), never to a thread-local cached copy, and the compiler may
   not hoist the read out of a loop.
2. **Ordering** — memory barriers around the access. Everything written before a volatile write is
   visible to a thread that reads that volatile and sees the new value. This is the happens-before
   edge.
3. Atomicity of 64-bit `long`/`double` reads and writes, which are otherwise permitted to tear into
   two 32-bit halves.

`volatile` does **not** provide atomicity for compound operations.

```java
volatile int count;
count++;    // STILL BROKEN — read, increment, write is three operations
```

Every read sees the latest value, and every write is published, but two threads can still read the
same value and both write the same increment. Visibility fixes staleness; it does not make a sequence
indivisible.

**Use volatile for:** a status/stop flag, a one-way state transition, a reference published once
(safe publication), and the reference in double-checked locking.

**Do not use it for:** counters, accumulators, or any state whose new value depends on the old one.
That needs `AtomicInteger`, `LongAdder`, or a lock.

```java
private volatile boolean running = true;   // correct use
public void stop() { running = false; }
public void run() { while (running) { work(); } }
```

Without `volatile` here, the JIT is entitled to hoist the field read out of the loop, and the loop
never exits — a real, reproducible bug, not a theoretical one.

---

## 6. The happens-before relation

The Java Memory Model does not promise that threads see each other's writes at all, unless a
happens-before edge exists. If action A happens-before B, then A's effects are visible to B.

The edges you must know:
- **Program order** within a single thread.
- **Monitor lock** — an unlock happens-before every subsequent lock of the same monitor.
- **Volatile** — a write happens-before every subsequent read of the same field.
- **Thread start** — everything before `t.start()` happens-before anything in t.
- **Thread termination** — everything in t happens-before `t.join()` returning.
- **Final fields** — a properly constructed object's final fields are visible without synchronization.
- **Transitivity** — A hb B and B hb C implies A hb C.
- Anything put into a concurrent collection or executor happens-before its retrieval/execution.

Without an edge, the compiler, the CPU, and the cache hierarchy may all reorder. "It worked on my
machine" often means x86, which has a strong memory model; the same code breaks on ARM.

---

## 7. Atomics and CAS

`AtomicInteger`, `AtomicLong`, `AtomicReference`, `AtomicBoolean` and the array/field-updater variants
give lock-free atomic operations via **compare-and-swap**, a single CPU instruction
(`lock cmpxchg` on x86) that atomically writes a new value only if the current value equals an
expected one.

```java
// what incrementAndGet does underneath
int prev, next;
do {
    prev = get();
    next = prev + 1;
} while (!compareAndSet(prev, next));
```

If another thread wins the race, CAS fails and the loop retries with the fresh value. No lock, no
blocking, no context switch. Under low-to-moderate contention this beats `synchronized` easily; under
extreme contention the retry loop burns CPU and a lock can win.

**LongAdder** (Java 8) is the high-contention answer. It keeps an array of per-thread-ish cells and
sums them on `sum()`. Writes spread across cells, eliminating the single hot cache line. Use it for
counters and metrics; use `AtomicLong` when you need an exact instantaneous value from
`incrementAndGet`.

**Trap — the ABA problem:** CAS compares values, not history. A value can change from A to B and back
to A, and CAS succeeds although the world changed underneath. Matters for lock-free stacks and
pointer-recycling structures; `AtomicStampedReference` adds a version stamp to fix it.

---

## 8. Deadlock and friends

**Deadlock** requires all four Coffman conditions simultaneously: mutual exclusion, hold-and-wait, no
preemption, and circular wait. Break any one and deadlock is impossible.

The practical break is **circular wait**: impose a global lock ordering and always acquire in that
order. When the objects have no natural order, use `System.identityHashCode` as a tiebreaker (with a
third "tiebreak lock" for the rare hash collision) — this is the standard account-transfer solution.

Alternative: `ReentrantLock.tryLock(timeout)` and back off on failure, so you can never hold and wait
indefinitely.

Related failures:
- **Livelock** — threads keep responding to each other and make no progress (two people stepping
  aside in a corridor). Fix with randomized backoff.
- **Starvation** — a thread never gets the resource; a barging lock plus a hot thread can do this.
  `new ReentrantLock(true)` (fair mode) prevents it at a large throughput cost.
- **Lock convoy** — many threads serialize behind one slow lock holder.

Detect deadlock with a thread dump: `jstack` prints "Found one Java-level deadlock" with the cycle.
Never hold two locks while calling out to code you do not control.

---

## 9. ExecutorService and ThreadPoolExecutor

Creating a thread per task does not bound resources. An executor decouples task submission from
execution policy.

```java
new ThreadPoolExecutor(
    corePoolSize, maximumPoolSize, keepAliveTime, unit,
    workQueue, threadFactory, rejectedExecutionHandler);
```

### The submission algorithm — memorize this order

1. If fewer than **corePoolSize** threads exist, **create a new thread**, even if other threads are
   idle.
2. Else, try to **enqueue** the task on the work queue.
3. Only if the queue is **full**, create a new thread up to **maximumPoolSize**.
4. If the queue is full and the pool is at maximum, apply the **rejection policy**.

**Trap — the unbounded-queue trap.** `Executors.newFixedThreadPool(n)` uses a `LinkedBlockingQueue`
with no capacity bound. The queue therefore *never* fills, so step 3 never happens and
`maximumPoolSize` is dead code. Under overload, tasks accumulate until the heap is exhausted —
`OutOfMemoryError` instead of graceful shedding. This is the single most common production thread-pool
bug. Always pass a bounded queue and a rejection policy.

`Executors.newCachedThreadPool` has the mirror-image problem: `SynchronousQueue` (capacity zero) plus
`maximumPoolSize = Integer.MAX_VALUE`, so every task that cannot hand off immediately creates a
thread — unbounded thread creation.

**Rejection policies:**
| Policy | Behaviour |
|---|---|
| `AbortPolicy` (default) | throws `RejectedExecutionException` |
| `CallerRunsPolicy` | the submitting thread runs the task itself |
| `DiscardPolicy` | silently drops the task |
| `DiscardOldestPolicy` | drops the head of the queue, retries |

`CallerRunsPolicy` is the useful one for pipelines: the producer is forced to execute the work, which
stops it producing, which applies **backpressure** all the way up to the source. It is a throttle, not
a failure.

**Sizing:** CPU-bound ≈ number of cores. I/O-bound ≈ `cores × (1 + waitTime/serviceTime)`. Measure.
Separate pools for separate workloads — a shared pool means a slow downstream call starves everything
(bulkhead pattern).

**Shutdown:** `shutdown()` stops accepting new tasks and drains the queue; `shutdownNow()` interrupts
running tasks and returns the pending ones. Always `awaitTermination` with a timeout. A non-daemon
pool thread that is never shut down keeps the JVM alive.

`ScheduledThreadPoolExecutor` handles delayed and periodic tasks. Note that
`scheduleAtFixedRate` fires on a fixed schedule and can bunch up if a run overruns, while
`scheduleWithFixedDelay` waits a fixed gap after each completion. **An uncaught exception in a
scheduled task silently cancels all future executions** — wrap the body in try/catch.

---

## 10. Future and CompletableFuture

`Future.get()` **blocks**. `Future` has no composition, no callbacks, and no way to complete it
externally, so a chain of `Future.get()` calls is just sequential code with extra threads.

`CompletableFuture` fixes all three:

```java
CompletableFuture.supplyAsync(() -> fetchUser(id), executor)
    .thenApply(User::accountId)                       // transform, same thread
    .thenCompose(acct -> fetchBalanceAsync(acct))     // flatMap another future
    .thenCombine(fetchLimitsAsync(id), Balance::with) // join two independent futures
    .orTimeout(2, TimeUnit.SECONDS)
    .exceptionally(ex -> Balance.unavailable())       // recover
    .thenAccept(this::render);
```

`thenApply` vs `thenApplyAsync`: the non-async form may run on whichever thread completed the previous
stage (or the calling thread if it is already complete), so a slow lambda there occupies someone
else's thread. The async form resubmits to an executor.

**Trap:** the no-executor overloads use `ForkJoinPool.commonPool()`, shared JVM-wide. Blocking there
starves parallel streams and every other user. **Always pass your own executor.**

**Trap — swallowed exceptions.** If you never call `get`, `join`, `handle`, `exceptionally`, or
`whenComplete`, an exception thrown inside a stage is stored in the future and **disappears silently**.
The most common form is a fire-and-forget `runAsync(...)` with no terminal handler. Always terminate a
chain with `whenComplete` or `exceptionally` and log.

Exceptions propagate down the chain wrapped in `CompletionException`; unwrap with `getCause()`.
`allOf` waits for all (and returns `Void` — you re-read the individual futures); `anyOf` returns the
first to complete, including the first to fail.

---

## 11. BlockingQueue and backpressure

`BlockingQueue` blocks the producer when full and the consumer when empty — a bounded buffer that
handles the coordination for you and is the backbone of the producer-consumer pattern.

Four method families: throws (`add`/`remove`), returns special value (`offer`/`poll`), blocks
(`put`/`take`), and times out (`offer(t,u)`/`poll(t,u)`).

| Implementation | Character |
|---|---|
| `ArrayBlockingQueue` | bounded, array-backed, single lock, optional fairness |
| `LinkedBlockingQueue` | optionally bounded, separate head/tail locks — higher throughput |
| `SynchronousQueue` | zero capacity, direct hand-off; a put waits for a take |
| `PriorityBlockingQueue` | unbounded, ordered |
| `DelayQueue` | elements become available only after their delay expires |
| `LinkedTransferQueue` | `transfer()` waits until a consumer takes the element |

**Bounding is the point.** An unbounded queue converts an overload problem into a memory problem and
delays failure until the worst possible moment. A bounded queue applies backpressure: the producer
slows to the consumer's rate. Every queue in your system should have a limit and a defined behaviour
when it is reached.

---

## 12. ThreadLocal and the pool leak

`ThreadLocal<T>` gives each thread its own value. It is stored in a `ThreadLocalMap` inside the
`Thread` object, keyed by a weak reference to the ThreadLocal instance. Used for per-request context
(MDC logging, security context, transaction context) and for non-thread-safe objects you would
otherwise construct repeatedly.

**Trap — the thread-pool leak.** Pool threads are *reused indefinitely*. A value set during request A
is still there for request B on the same thread. That is both a correctness bug (leaking a previous
user's security context — a genuine security incident class) and a memory leak (the value is strongly
referenced by the live thread forever).

The key in `ThreadLocalMap` is weak, but the **value is strongly referenced**, so even if the
ThreadLocal itself becomes garbage the entry can survive until the thread dies or the map is cleaned.
Pool threads never die.

Always:
```java
try {
    CONTEXT.set(ctx);
    handle(request);
} finally {
    CONTEXT.remove();     // not set(null) — remove() clears the map entry
}
```

`InheritableThreadLocal` copies to child threads at creation — which does not work with pools, since
threads are created before your request exists. Scoped values (Java 21 preview) are the modern
replacement: immutable, bounded to a dynamic scope, and virtual-thread friendly.

---

## 13. Safe publication and double-checked locking

Publishing an object means making its reference visible to other threads. The danger is that the
reference can become visible **before** the constructor's writes, because the constructor's stores and
the reference store can be reordered. Another thread then sees a non-null reference to a
partially-constructed object.

Safe publication mechanisms:
- Initialize in a static initializer (class initialization is guaranteed by the JVM).
- Store into a `volatile` field or an `AtomicReference`.
- Store into a field guarded by a lock, and read under the same lock.
- Store into a concurrent collection.
- **Final fields** — the JMM guarantees that a thread seeing a reference to a correctly constructed
  object sees its final fields fully initialized, with no synchronization. This is why immutable
  objects with final fields are freely shareable — and why letting `this` escape from a constructor
  destroys the guarantee.

**Double-checked locking** must have the `volatile`:

```java
private volatile Singleton instance;      // volatile is mandatory

public Singleton getInstance() {
    if (instance == null) {                    // no lock on the fast path
        synchronized (this) {
            if (instance == null) {            // re-check under the lock
                instance = new Singleton();
            }
        }
    }
    return instance;
}
```

Without `volatile` this is the textbook broken idiom: another thread can observe a non-null `instance`
whose fields are still defaults. Better alternatives: an enum singleton, or the holder idiom (a static
nested class initialized lazily by the classloader, which needs no synchronization at all).

---

## 14. ConcurrentHashMap

Java 8+ implementation: the table is an array of bins. Inserting into an empty bin is a plain CAS;
inserting into an occupied bin takes a `synchronized` lock **on the first node of that bin only**.
Reads are lock-free (nodes' `val` and `next` are volatile). So contention scales with table size
rather than with a fixed 16 segments as in Java 7.

Retrievals reflect the results of the most recently *completed* update. Iterators are **weakly
consistent**: they never throw `ConcurrentModificationException` and may or may not show concurrent
changes. `size()` is an estimate under concurrent mutation.

**Trap:** every individual method is atomic, but **combining two is not**:

```java
if (!map.containsKey(k)) map.put(k, v);       // race — two threads can both pass the check
```

Use the atomic compound methods instead: `putIfAbsent`, `computeIfAbsent`, `computeIfPresent`,
`compute`, `merge`, `replace(k, old, new)`.

```java
map.computeIfAbsent(key, k -> expensiveLoad(k));   // mapping function runs at most once per key
map.merge(key, 1L, Long::sum);                     // atomic counter
```

**Trap:** the function passed to `computeIfAbsent` runs **while holding the bin lock**. It must be
short, must not block, and must not modify the same map — recursive `computeIfAbsent` on the same map
can deadlock or throw `IllegalStateException: Recursive update`. (On a plain `HashMap` the same
pattern silently corrupts the table.)

`ConcurrentHashMap` forbids null keys and null values, precisely so `get` returning null is
unambiguous — in a concurrent map you could not otherwise distinguish "absent" from "mapped to null".

---

## 15. wait / notify

The low-level condition mechanism. `wait()`, `notify()`, `notifyAll()` are `Object` methods and
**must** be called while holding that object's monitor, or you get
`IllegalMonitorStateException`. `wait()` atomically releases the monitor and suspends; on wake it
reacquires before returning.

**Always wait in a loop**, never in an `if`:

```java
synchronized (lock) {
    while (!condition) {      // while, not if
        lock.wait();
    }
    // condition is now true and we hold the lock
}
```

Two reasons: **spurious wakeups** are permitted by the spec, and with `notifyAll` several threads wake
but only one can win the race to re-check the condition — the losers must go back to waiting.

Prefer `notifyAll` over `notify` unless every waiter is provably interchangeable; `notify` can wake the
one thread that cannot proceed, and the signal is lost.

In modern code, use `BlockingQueue`, `CountDownLatch`, or `Condition` instead. Know `wait`/`notify`
because it is asked, not because you should write it.

---

## 16. ReentrantLock and friends

`ReentrantLock` is `synchronized` with more control:
- `tryLock()` and `tryLock(timeout)` — never block forever, enabling deadlock avoidance.
- `lockInterruptibly()` — cancellable acquisition.
- Optional **fairness** (`new ReentrantLock(true)`): FIFO ordering, no starvation, significantly lower
  throughput because it forbids barging.
- Multiple `Condition` objects per lock — separate not-full and not-empty wait sets, so you can signal
  precisely instead of waking everyone.

```java
lock.lock();
try { ... } finally { lock.unlock(); }    // the finally is mandatory
```

**Trap:** forgetting `unlock` in a `finally`. `synchronized` releases automatically on exception;
`ReentrantLock` does not.

`ReentrantReadWriteLock` allows many concurrent readers or one writer. It only wins when reads
dominate and are long; otherwise the bookkeeping overhead exceeds the benefit. `StampedLock` adds an
**optimistic read** mode — read a stamp, read the data, then validate the stamp; if a write intervened,
fall back to a real read lock. It is not reentrant, which trips people up.

**Coordination primitives:**

| Primitive | Semantics |
|---|---|
| `CountDownLatch(n)` | threads `await()` until `countDown()` has been called n times. **One-shot** — cannot be reset. |
| `CyclicBarrier(n)` | n threads wait for each other, then all proceed; **reusable**, optional barrier action. |
| `Semaphore(n)` | n permits; `acquire`/`release` bound concurrent access. Permits are not owned, so any thread may release. |
| `Phaser` | a flexible, dynamic-party barrier for multi-phase work. |
| `Exchanger` | two threads swap objects at a rendezvous point. |

Latch for "wait for startup to finish"; barrier for "iterate in synchronized rounds"; semaphore for
"at most 10 concurrent calls to this downstream service" (a rate/concurrency limiter, and your
backpressure tool when virtual threads removed your pool).

---

## 17. Producer-consumer, assembled

```java
BlockingQueue<Task> queue = new ArrayBlockingQueue<>(1000);   // bounded — backpressure

ExecutorService consumers = new ThreadPoolExecutor(
        4, 4, 0L, TimeUnit.MILLISECONDS,
        new ArrayBlockingQueue<>(100),
        new ThreadPoolExecutor.CallerRunsPolicy());           // bounded + throttling

// producer
while (hasMore()) {
    queue.put(next());          // blocks when full — the producer is throttled
}
queue.put(POISON_PILL);         // sentinel per consumer, for clean shutdown

// consumer
while (true) {
    Task t = queue.take();      // blocks when empty
    if (t == POISON_PILL) break;
    try { process(t); }
    catch (Exception e) { log.error("task failed", e); }   // never let it kill the loop
}
```

Every design decision here is a talking point: the bound gives backpressure, `CallerRunsPolicy` gives
throttling rather than data loss, the poison pill gives ordered shutdown, and the try/catch keeps one
bad task from killing a worker.

---

## Atomic concept checklist

- [ ] Threads share the heap and statics; each owns its stack. That split is where every race comes from.
- [ ] BLOCKED means monitor contention; WAITING means a deliberate park. Socket I/O reports RUNNABLE.
- [ ] `start()` creates a thread; `run()` does not. Interruption is a cooperative flag.
- [ ] `count++` is read-modify-write; `if (absent) put` is check-then-act. Both are races.
- [ ] `synchronized` gives mutual exclusion **and** visibility; instance and static methods use different monitors.
- [ ] Never lock on a String literal, a boxed Integer, or a reassignable field.
- [ ] `volatile` gives visibility and ordering plus atomic 64-bit access — it does **not** make `count++` atomic.
- [ ] `volatile` is right for stop flags and DCL references; wrong for counters.
- [ ] Without a happens-before edge there is no visibility guarantee at all; know the seven edges.
- [ ] Atomics use CAS retry loops; LongAdder beats AtomicLong under heavy write contention.
- [ ] ABA: CAS compares values, not history; `AtomicStampedReference` fixes it.
- [ ] Deadlock needs all four Coffman conditions; global lock ordering breaks circular wait.
- [ ] Pool order: core threads first, **then queue**, then max threads, then reject.
- [ ] `newFixedThreadPool` has an unbounded queue, so maximumPoolSize is dead and overload becomes OOM.
- [ ] `CallerRunsPolicy` converts rejection into backpressure on the producer.
- [ ] An uncaught exception in a scheduled task cancels all future runs.
- [ ] `CompletableFuture` without an explicit executor uses the shared common pool.
- [ ] A CompletableFuture chain with no terminal handler swallows exceptions silently.
- [ ] Every queue needs a bound; unbounded queues convert overload into OOM.
- [ ] `SynchronousQueue` has zero capacity — it is a hand-off, not storage.
- [ ] ThreadLocal in a pooled thread leaks the value into the next request; always `remove()` in a finally.
- [ ] Safe publication requires volatile, final, a lock, or a concurrent collection — a bare reference store can be reordered.
- [ ] Double-checked locking is broken without `volatile`; the holder idiom or an enum is simpler.
- [ ] ConcurrentHashMap locks per bin, reads lock-free, iterators weakly consistent, `size()` approximate.
- [ ] Compound actions on a concurrent map need `computeIfAbsent`/`merge`, not containsKey-then-put.
- [ ] The `computeIfAbsent` mapping function runs under the bin lock: keep it short and never recursive.
- [ ] ConcurrentHashMap forbids nulls so that a null `get` is unambiguous.
- [ ] Always `wait()` in a `while` loop — spurious wakeups and notifyAll losers are both real.
- [ ] `ReentrantLock` needs `unlock()` in a finally; it adds tryLock, interruptibility, fairness, and multiple Conditions.
- [ ] CountDownLatch is one-shot, CyclicBarrier is reusable, Semaphore permits are not thread-owned.