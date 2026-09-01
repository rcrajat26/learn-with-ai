# 05 Multithreading and Concurrency — The trap index — INTERVIEW (§5.2)

**Target version: Java 21 LTS.** | **Part 5 of 5** | [Index](00-index.md)
Previous: [Interview questions: design and judgement II](94e2-interview-design-and-judgement-ii.md) · Next: [The drills and the atomic concept checklist](94f2-drills-and-atomic-checklist.md)

This is the page you read in the elevator. Every row is a belief a candidate actually holds walking
in, the QuizStakes symptom it produces under load, and the one-line fix. No theory here — that
lives in the earlier files. If a row doesn't make sense, go re-read the concept; this page only
works as a refresher.

**D-213** — The 55-item trap index, grouped.

### Memory model and visibility (5.2.1–5.2.5)

| # | The wrong belief, verbatim | The symptom in production | The fix | Leaf |
|---|---|---|---|---|
| 1 | "`volatile` makes it atomic." | `volatile long stakeCount; stakeCount++;` under 3,400 settlements/sec loses updates — the counter reads 41 instead of 43. | `volatile` gives visibility of each write, not read-modify-write atomicity. Use `AtomicLong`/`LongAdder` for compound updates. | 5.2.1 |
| 2 | "`synchronized` is only about mutual exclusion." | A "no contention here" refactor drops `synchronized` around a bonus-balance read; another thread keeps seeing the stale `BONUS_AVAILABLE` value indefinitely. | `synchronized` also opens a happens-before edge on entry/exit — it publishes writes, not just serializes them. | 5.2.2 |
| 3 | "`volatile` flushes the cache to main memory." | Engineer designs around an imaginary "flush instruction," misjudges cost, and can't explain why two cores ever see a consistent value without one. | MESI already keeps caches coherent; `volatile` inserts memory barriers that drain the store buffer and prevent reordering — there is no flush-to-RAM step. | 5.2.3 |
| 4 | "Happens-before means happens earlier in time." | Two unsynchronized writes to `Restriction.state` on different cores, nanoseconds apart, are assumed visible to each other because of the wall-clock gap. | Happens-before is a program-order/synchronization-order relation, not a clock. No synchronization edge = no visibility guarantee, regardless of elapsed time. | 5.2.4 |
| 5 | "It works on my machine" = x86-TSO. | Ledger-reconciliation code passes every test on an x86 dev laptop, then reorders on an ARM production host, and a `PaymentRun` worker reads a stale ledger position. | x86-TSO is one of the strongest memory models in production use; ARM/POWER are weaker. Code correctness must come from the JMM's guarantees (`volatile`/`final`/`synchronized`), never the chip. | 5.2.5 |

### Locking, interrupts, futures (5.2.6–5.2.13)

| # | The wrong belief, verbatim | The symptom in production | The fix | Leaf |
|---|---|---|---|---|
| 6 | "`sleep` releases the lock." | A settlement worker calls `Thread.sleep(200)` inside a `synchronized(fundsLedger)` block; the other eleven threads queued on that monitor block for the full 200 ms each time. | `sleep` holds every lock it entered with. Only `wait()` or leaving the `synchronized` block releases the monitor. | 5.2.6 |
| 7 | "Adding a sleep fixes the race." | `Thread.sleep(10)` between the stake-availability check and the reservation write makes the race "disappear" in a local test, then reappears the first night at 1,200 reservations/sec. | Sleep narrows the timing window; it does not close it. Use a CAS loop, a lock, or an atomic compound method. | 5.2.7 |
| 8 | "`start()` twice throws `IllegalStateException`." | A `catch (IllegalStateException e)` wrapped around a second `start()` call on a settlement worker never fires — the real exception propagates uncaught and kills the batch. | It throws `IllegalThreadStateException`. A `Thread` object can be started exactly once, ever, no matter its current state. | 5.2.8 |
| 9 | "Catching and ignoring `InterruptedException` is fine." | `catch (InterruptedException e) {}` inside a stake-settlement loop swallows the executor's shutdown signal; the worker keeps looping through `awaitTermination`, and the JVM never exits. | Restore the flag — `Thread.currentThread().interrupt()` — or propagate; never swallow it silently. | 5.2.9 |
| 10 | "`Future.cancel(true)` kills the task." | Cancelling an in-flight `DocumentVerification` vendor call with `cancel(true)` interrupts the thread, but the vendor's blocking HTTP client ignores the interrupt and keeps running. | `cancel` only sets the interrupt flag (or interrupts a blocking call that honours it). The task itself must check `Thread.interrupted()` or use interruptible I/O to actually stop. | 5.2.10 |
| 11 | "`CompletableFuture.cancel(true)` interrupts the task." | Cancelling a chained bonus-calculation `CompletableFuture` completes the future exceptionally, but the underlying thread keeps computing to the end regardless of `mayInterruptIfRunning`. | `CompletableFuture.cancel` never interrupts the running thread — the boolean argument is vestigial. Build a cooperative cancellation flag if the work must actually stop. | 5.2.11 |
| 12 | "`orTimeout` cancels the work." | `orTimeout(3, SECONDS)` on a ledger-write call fires a `TimeoutException` on the future while the underlying JDBC write to `FundsLedger` keeps running in the background and commits anyway. | `orTimeout` only completes the *future* exceptionally; it does not stop the upstream computation. Cooperative cancellation of the underlying call is a separate mechanism. | 5.2.12 |
| 13 | "`anyOf` gives the first success." | `CompletableFuture.anyOf` across three identity-vendor calls completes with a failed result because one vendor call failed fast, discarding a still-pending successful check. | `anyOf` completes on the first *completion*, success or failure. First-success semantics need a custom combinator that filters failures. | 5.2.13 |

### Executors and thread pools (5.2.14–5.2.17)

| # | The wrong belief, verbatim | The symptom in production | The fix | Leaf |
|---|---|---|---|---|
| 14 | "`newFixedThreadPool` respects maximumPoolSize." | Expecting settlement-worker capacity to grow under a peak burst; it never does, because `corePoolSize == maximumPoolSize` in a fixed pool, so the unbounded queue absorbs everything instead. | `maximumPoolSize` is irrelevant when it equals `corePoolSize`. Growth requires `corePoolSize < maximumPoolSize` *and* a bounded queue that can actually fill. | 5.2.14 |
| 15 | "The pool queues before it creates core threads." | Submitting 8 settlement tasks to a pool with `corePoolSize = 8` and expecting them to queue behind a smaller warm set of threads; instead all 8 spin up new core threads immediately. | `ThreadPoolExecutor` starts a fresh core thread per submission until `corePoolSize` is reached, and only *then* starts queuing. Queuing happens after core is full, not before. | 5.2.15 |
| 16 | "`DiscardOldestPolicy` is a reasonable default." | Under saturation, the oldest queued bank-withdrawal task is silently dropped from the `PaymentRun` queue — the client's money is never processed and no exception ever surfaces. | The actual default is `AbortPolicy` (throws `RejectedExecutionException`). `DiscardOldestPolicy` silently loses work — never acceptable on a money-moving path; prefer `CallerRunsPolicy` or explicit backpressure. | 5.2.16 |
| 17 | "An unbounded queue is safer than rejecting." | The default unbounded `LinkedBlockingQueue` behind `newFixedThreadPool` backs up during a Quiz Engine slowdown, and the process dies with `OutOfMemoryError` from a queue full of pending settlements. | Bound the queue and pick a rejection/backpressure policy deliberately. An unbounded queue converts a slow consumer into an OOM crash instead of controlled backpressure. | 5.2.17 |

### Concurrent collections (5.2.18–5.2.23)

| # | The wrong belief, verbatim | The symptom in production | The fix | Leaf |
|---|---|---|---|---|
| 18 | "`ConcurrentHashMap` makes my compound action atomic." | `if (!map.containsKey(k)) map.put(k, v)` guarding a bonus-eligibility cache races under concurrent onboarding, and two bonus grants issue for one prospect. | `ConcurrentHashMap` makes *each individual call* atomic, not sequences of them. Use `putIfAbsent`/`computeIfAbsent` for the compound check-then-act. | 5.2.18 |
| 19 | "`size()` on a concurrent collection is exact." | A reconciliation dashboard treats `map.size()` over in-flight `PaymentRun` entries as an exact count and it drifts under concurrent mutation. | `size()` on concurrent collections is a best-effort, non-linearizable estimate. Don't use it for exact accounting; maintain a dedicated counter if exactness matters. | 5.2.19 |
| 20 | "`CopyOnWriteArrayList` is a fast concurrent list." | Appending stake-reservation events (2.8M/day) into a `CopyOnWriteArrayList` copies the entire backing array on every `add`; throughput collapses and the heap balloons. | COW is for read-heavy, rarely-mutated collections (listener lists), not write-heavy logs. Use a concurrent queue or a batching structure instead. | 5.2.20 |
| 21 | "Fail-fast iterators are a thread-safety mechanism." | A team relies on `ConcurrentModificationException` to "catch races" while iterating ledger positions, then removes the actual synchronization, treating the exception as a safety net. | Fail-fast is a best-effort bug detector, not a guarantee — it can fail to fire and still corrupts state either way. It does not make iteration thread-safe. | 5.2.21 |
| 22 | "`Collections.synchronizedList` is safe to iterate." | Iterating a `synchronizedList` of pending `WithdrawalTransaction`s without an external lock throws `ConcurrentModificationException` when a `PaymentRun` thread concurrently appends. | Each individual method is synchronized, but iteration is a sequence of calls. Wrap the whole loop in `synchronized (list) { ... }`. | 5.2.22 |
| 23 | "`Collections.unmodifiableList` is thread-safe / is a copy." | `unmodifiableList` wraps the live restrictions list; another thread mutates the backing list mid-iteration and the "immutable" view throws `CME` or shows torn state. | It's a live read-only *view*, not a defensive copy and not synchronized. Structural changes to the backing list are still visible and still unsafe to iterate concurrently. | 5.2.23 |

### Atomics and CAS (5.2.24–5.2.26)

| # | The wrong belief, verbatim | The symptom in production | The fix | Leaf |
|---|---|---|---|---|
| 24 | "Two atomics make an atomic pair." | `AtomicLong cashAvailable` and `AtomicLong bonusAvailable` updated in two separate atomic operations; a reader computing the derived stakeable total observes cash updated but bonus not yet, and reserves against a wrong figure. | Composing two independently-atomic fields is not atomic together. Guard the pair with one lock, one CAS over a composite reference, or an immutable snapshot object. | 5.2.24 |
| 25 | "`LongAdder` can replace `AtomicLong` everywhere." | Swapping the ledger sequence-number generator from `AtomicLong` to `LongAdder` breaks uniqueness — code needed `compareAndSet`/an immediately-consistent `get()`, which striped counters don't give cheaply. | `LongAdder` trades single-value read/CAS availability for write throughput via internal striping. It's for hot counters read rarely, not for values you CAS on. | 5.2.25 |
| 26 | "ABA is a Java problem." | A candidate worries about classic ABA on every `AtomicReference` CAS over `PaymentRun` ids, the way it's taught for lock-free C stacks. | In Java, GC won't reuse an object's identity while it's still reachable, so ABA via reclaimed-and-reused memory mostly doesn't occur. It can still surface with intentionally pooled/recycled objects — that's the narrower real case. | 5.2.26 |

### Locks (5.2.27–5.2.34)

| # | The wrong belief, verbatim | The symptom in production | The fix | Leaf |
|---|---|---|---|---|
| 27 | "Biased → thin → fat lock escalation." | A candidate describes biased locking as an active tuning lever for the `FundsLedger` monitor on a current JDK. | Biased locking was disabled by JEP 374 in Java 15 and later removed entirely. Escalation today is just thin (lightweight stack-lock) → fat (inflated monitor). | 5.2.27 |
| 28 | "Locks are slow." | An engineer replaces an uncontended `synchronized` block guarding a rarely-touched restriction flag with a hand-rolled lock-free scheme, adding complexity for no measurable gain. | An uncontended `synchronized` is cheap — fast-path CAS, no OS wait, no syscall. Locks only get expensive under genuine contention. | 5.2.28 |
| 29 | "Narrow critical sections are always better." | Splitting the `FundsLedger` debit and credit into two separate `synchronized` blocks to "shrink" each one lets a reader observe the debit applied and the credit not yet — the ledger is momentarily unbalanced. | Lock coarsening exists precisely because narrower isn't automatically safer. Scope the critical section to the invariant it protects, not to an arbitrary minimality target. | 5.2.29 |
| 30 | "`ReentrantLock` releases on exception like `synchronized`." | An exception thrown mid-settlement inside a `try` block with no `finally` leaves the `ReentrantLock` held forever, wedging every subsequent `PaymentRun`. | `ReentrantLock` never auto-releases. Every acquisition needs `try { ... } finally { lock.unlock(); }`. | 5.2.30 |
| 31 | "Fair locks are the safe default." | Switching `new ReentrantLock(true)` onto the hot stake-reservation path collapses throughput because every acquisition now pays FIFO queuing and extra context-switch overhead. | Fairness trades large throughput for an ordering guarantee almost nothing needs. Default to unfair; reach for fair only when starvation is proven, not feared. | 5.2.31 |
| 32 | "`ReadWriteLock` is faster because reads are more common." | Wrapping a rarely-contended `LimitSet` read with `ReentrantReadWriteLock` is slower than plain `synchronized`, because the RW bookkeeping dominates when hold times are short and contention is low. | `ReadWriteLock` wins only when read-hold time is long *and* reader concurrency is actually exploited. For short critical sections it's pure overhead over `synchronized`. | 5.2.32 |
| 33 | "`StampedLock` is a drop-in `ReentrantReadWriteLock`." | Reentrant-style code that reuses a stamp across nested calls, or unlocks the balance-view read path with the wrong stamp, throws `IllegalMonitorStateException` or deadlocks. | `StampedLock` is not reentrant and exposes a stamp-based optimistic-read API with no relation to `ReentrantReadWriteLock`'s. It cannot be substituted mechanically. | 5.2.33 |
| 34 | "`Semaphore(1)` is a mutex." | A callback thread that never acquired the permit calls `release()` on a `Semaphore(1)` guarding stake reservations after a `DocumentVerification` completes, "unlocking" a reservation another thread is still using. | `Semaphore` has no ownership concept — any thread may release regardless of which thread acquired. It is not equivalent to a mutex's owner-only-unlock discipline. | 5.2.34 |

### `wait`/`notify` and `ThreadLocal` (5.2.35–5.2.39)

| # | The wrong belief, verbatim | The symptom in production | The fix | Leaf |
|---|---|---|---|---|
| 35 | "`notify` is a cheaper `notifyAll`." | A `PaymentRun` producer calls `notify()` on a `FundsLedger` monitor with multiple consumers waiting on different conditions; it wakes the wrong waiter, which rechecks, finds its condition false, and goes back to sleep — the intended consumer never wakes. | `notify` wakes one arbitrary waiter. It is only safe when every waiter is interchangeable; otherwise use `notifyAll`. | 5.2.35 |
| 36 | "`if (!cond) wait();`" | A spurious wakeup (or a stolen notification) lets a settlement thread fall through past `wait()` while the condition is still false, and it reads a half-updated reservation. | Always loop: `while (!cond) wait();`. Re-check the condition after every wakeup, spurious or not. | 5.2.36 |
| 37 | "`ThreadLocal.set(null)` cleans up." | `threadLocal.set(null)` in a pooled settlement worker still leaves a live `Entry` in the thread's `ThreadLocalMap`; the next task on that pooled thread sees a stale mapping, and the leak accrues across the pool's lifetime. | `set(null)` still stores an entry with a `null` value. Call `remove()` to actually delete it. | 5.2.37 |
| 38 | "`InheritableThreadLocal` propagates context into a pool." | An operator's audit `ClientId`, set via `InheritableThreadLocal` on a request thread, never appears inside a pooled settlement worker — the worker thread was constructed once at pool startup, long before this request existed. | Inheritance copies the value at `Thread` construction time only, not at task submission. Pooled threads never re-inherit; pass context explicitly (or use `ScopedValue`). | 5.2.38 |
| 39 | "`ThreadLocal` caching is still a good idea with virtual threads." | Caching a reusable formatter or status-code buffer per `ThreadLocal` across millions of cheap virtual threads for stake settlements multiplies memory — one instance per virtual thread instead of per handful of platform threads. | `ThreadLocal` pooling assumed a small, fixed thread count. With millions of virtual threads, prefer `ScopedValue` or plain per-call allocation. | 5.2.39 |

### Virtual threads (5.2.40–5.2.44)

| # | The wrong belief, verbatim | The symptom in production | The fix | Leaf |
|---|---|---|---|---|
| 40 | "Virtual threads are faster." | Replacing the CPU-bound stake-settlement compute loop with virtual threads shows no speedup — sometimes worse, from added scheduling overhead. | Virtual threads cut the cost of *blocking*, not CPU-bound compute. Compute-bound work is bounded by core count no matter which thread abstraction runs it. | 5.2.40 |
| 41 | "Pool the virtual threads." | Wrapping virtual-thread creation for onboarding checks inside a bounded pool (`newFixedThreadPool`-style) throttles concurrency to a handful and defeats the entire design. | Virtual threads are meant to be created per task, cheaply, unpooled — use `Executors.newVirtualThreadPerTaskExecutor()` and limit concurrency with a semaphore against the real constrained resource instead. | 5.2.41 |
| 42 | "Replace `synchronized` with `ReentrantLock` for virtual threads." **[VERSION-TRAP]** | On Java 21, a `synchronized` block guarding `FundsLedger` inside a virtual-thread-per-task settlement handler pins its carrier thread under load, starving other virtual threads; the team keeps "fixing" every `synchronized` block reflexively even after upgrading. | True and necessary on Java 21: swap the hot `synchronized` block for `ReentrantLock` to avoid carrier pinning. JEP 491 made this unnecessary starting Java 24 — `synchronized` no longer pins — and `-Djdk.tracePinnedThreads`, the 21-era diagnostic flag, no longer exists on 24+. | 5.2.42 |
| 43 | "Virtual threads removed my need for backpressure." | Spawning one virtual thread per incoming stake reservation with no limiter during a 1,200/sec peak floods the downstream connection pool and the Quiz Engine, even though thread *creation* itself was cheap. | Virtual threads remove thread-creation cost, not downstream capacity limits. Still size a semaphore or bounded queue to the constrained resource behind the call. | 5.2.43 |
| 44 | "`jstack` shows my virtual threads." | A `jstack` dump taken to investigate a wedged `PaymentRun` shows only platform/carrier threads — the millions of virtual threads doing the actual blocked work are invisible. | Use `jcmd <pid> Thread.dump_to_file` or JFR virtual-thread events instead; plain `jstack` does not enumerate virtual threads. | 5.2.44 |

### Deadlocks, scheduling, and "harmless" shortcuts (5.2.45–5.2.49)

| # | The wrong belief, verbatim | The symptom in production | The fix | Leaf |
|---|---|---|---|---|
| 45 | "The JVM breaks deadlocks." | Two settlement threads lock two client accounts in opposite order and the team assumes it will "resolve itself" given enough time. | The JVM has no runtime deadlock detection or recovery. A real deadlock hangs forever until the process is restarted; tooling only detects it *after the fact*. | 5.2.45 |
| 46 | "`jstack` finds all deadlocks." | `jstack`'s automatic cycle detector reports nothing even though a settlement worker is permanently blocked, because the cycle runs through `ReentrantLock`/`Condition` objects, not intrinsic monitors. | `jstack`'s built-in detection covers monitor (`synchronized`) cycles reliably but not all `java.util.concurrent` lock cycles — trace "waiting to lock" ownership chains manually for those. | 5.2.46 |
| 47 | "Thread priorities work." | Setting a high `Thread.setPriority()` on the `PaymentRun` settlement thread to "make it go faster" produces no observable scheduling change on the target OS. | Java thread priority is an advisory hint mapped inconsistently — often collapsed — onto native OS priorities. Never rely on it for correctness or throughput. | 5.2.47 |
| 48 | "A shutdown hook always runs." | A shutdown hook registered to flush pending `FundsLedger` writes never runs after a `kill -9` or an `OutOfMemoryError`-triggered abrupt crash; in-flight settlements are lost. | Shutdown hooks run only on orderly shutdown (normal exit, `SIGTERM`). They never run on `kill -9`, a native crash, or `Runtime.halt()`. | 5.2.48 |
| 49 | "A benign data race is fine." | An unsynchronized boolean "just a status flag" marking a `PaymentRun` as complete gets hoisted or reordered by the JIT; a settlement thread spins forever, never observing the write. | There is no such thing as a benign data race under the JMM — the compiler may transform unsynchronized shared state in ways that break even "trivial" flags. Use `volatile`/atomics regardless of how simple the field looks. | 5.2.49 |

### Timeouts, containers, and streams (5.2.50–5.2.55)

| # | The wrong belief, verbatim | The symptom in production | The fix | Leaf |
|---|---|---|---|---|
| 50 | "`System.currentTimeMillis()` is fine for a timeout." | An NTP adjustment shifts the wall clock backward mid stake-settlement timeout computation, producing a negative or wildly wrong elapsed duration — the timeout never fires, or fires instantly. | Use `System.nanoTime()` for elapsed-time/timeout math — it's monotonic and immune to wall-clock adjustments. `currentTimeMillis()` is for timestamps, not durations. | 5.2.50 |
| 51 | "`availableProcessors()` is the machine's core count." | Sizing the settlement thread pool from `Runtime.getRuntime().availableProcessors()` inside a Kubernetes pod capped at 2 CPUs returns the *host's* 64 cores, oversubscribing the pool badly. | In a cgroup-limited container, `availableProcessors()` may reflect the host rather than the quota depending on JVM and container-runtime version. Verify it and cap explicitly rather than trusting it blindly. | 5.2.51 |
| 52 | "Parallel streams use my executor." | Submitting a parallel-stream stake aggregation from inside a custom `ExecutorService`, expecting it to run on that pool's threads — it silently runs on `ForkJoinPool.commonPool()` instead. | Parallel streams always use `ForkJoinPool.commonPool()` by default; there is no ambient "current executor" propagation. Only submitting the whole stream operation via a custom `ForkJoinPool.submit(...)` changes that. | 5.2.52 |
| 53 | "The common pool is a good place for I/O." | A parallel stream making blocking `DocumentVerification` HTTP calls saturates the shared `ForkJoinPool.commonPool()`, starving unrelated `CompletableFuture` default-executor work application-wide. | The common pool is sized to core count for CPU-bound work and shared JVM-wide. Never run blocking I/O on it; use a dedicated bounded executor instead. | 5.2.53 |
| 54 | "Structured concurrency is final." **[VERSION-TRAP]** | A candidate states structured concurrency shipped GA by Java 21, or even by Java 25, with no preview flag. | Still preview through JDK 25 (fifth preview round, JEP 505). `--enable-preview` is required on every JDK version to date, including 25. | 5.2.54 |
| 55 | "Scoped values are still preview." (Final in 25.) **[VERSION-TRAP]** | A candidate on Java 25 still compiles with `--enable-preview` for `ScopedValue` and avoids using it in "real" production code out of caution. | JEP 506 finalized scoped values as a standard feature in Java 25 — no preview flag needed there. They remained preview only through 21–24. | 5.2.55 |

---

## The ones that need code to be legible

Seven of the fifty-five collapse a whole demo into one line; these don't. Each is the wrong
snippet, the actual observed output, and the fix.

**5.2.6 — sleep does not release the lock.**

```java
synchronized (fundsLedger) {
    applyDebit(clientId, amount);
    Thread.sleep(200);           // BROKEN: monitor stays held for 200ms
    applyCredit(houseAccount, amount);
}
```
Output: eleven other settlement threads pile up on `fundsLedger`'s monitor, each waiting the full
200 ms even though none of them touch the account being debited. Fix — move the sleep (or the
whole slow call) entirely outside the synchronized block, or replace it with a `CountDownLatch`/
`Condition` wait that can be signalled early.

**5.2.29 — narrowing a critical section can break the invariant it existed to protect.**

```java
// BROKEN: two locks instead of one, invariant window opens up
synchronized (fundsLedger) { applyDebit(clientCash, stake.amount()); }
synchronized (fundsLedger) { applyCredit(houseRevenue, stake.amount()); }
```
Output: a concurrent reconciliation job reads the ledger between the two blocks and reports it
unbalanced — debit posted, credit missing — even though both statements "look" synchronized.
Fix: one critical section for the whole double-entry write.
```java
synchronized (fundsLedger) {
    applyDebit(clientCash, stake.amount());
    applyCredit(houseRevenue, stake.amount());
}
```

**5.2.34 — `Semaphore(1)` has no owner.**

```java
Semaphore reservationGate = new Semaphore(1);
reservationGate.acquire();               // acquired on settlement-thread
vendorClient.verifyAsync(clientId)
    .thenRun(reservationGate::release);  // BROKEN: released on a callback thread
```
Output: the callback thread's `release()` succeeds even though it never called `acquire()` —
the semaphore is now at permit count 1 while the settlement thread believes it still holds
exclusive access, and a second reservation slips in concurrently. Fix: use `ReentrantLock`
when ownership matters, or make the async completion re-acquire on the owning thread before
proceeding rather than releasing from wherever the callback happens to run.

**5.2.37 — `set(null)` leaves an entry behind.**

```java
static final ThreadLocal<ClientId> AUDIT_CLIENT = new ThreadLocal<>();
// end of task on a pooled settlement worker:
AUDIT_CLIENT.set(null);   // BROKEN: still an Entry, key ClientId is null-valued not gone
```
Output: heap dumps of the settlement pool show thousands of retained `ThreadLocalMap.Entry`
objects after a week of running; `AUDIT_CLIENT.get()` on the next task returns `null` correctly,
but the entry itself, and anything it transitively pinned before being nulled, lingers until the
next `ThreadLocalMap` resize sweeps stale entries. Fix:
```java
AUDIT_CLIENT.remove();   // actually deletes the Entry
```

**5.2.42 — `synchronized` pinning is a Java-21 fact, not a permanent one.**

```java
// Java 21, virtual-thread-per-task executor:
void settleStake(Reservation r) {
    synchronized (fundsLedger) {          // pins the carrier thread on 21
        ledger.settle(r);                 // blocking JDBC call inside the lock
    }
}
```
Output on Java 21 under `newVirtualThreadPerTaskExecutor()`: with only a handful of carrier
platform threads, a burst of settlements each pinning their carrier while blocked on the JDBC
call starves every other virtual thread scheduled onto those carriers — throughput falls off a
cliff well before CPU or connection-pool limits are hit. Fix on 21: swap to `ReentrantLock`.
```java
private final ReentrantLock ledgerLock = new ReentrantLock();
void settleStake(Reservation r) {
    ledgerLock.lock();
    try { ledger.settle(r); } finally { ledgerLock.unlock(); }
}
```
On Java 24+, JEP 491 removed the pinning cause for `synchronized` outright — the original snippet
is fine unmodified there, and `-Djdk.tracePinnedThreads` (the flag used to diagnose this on 21)
no longer exists to even check.

**5.2.50 — `currentTimeMillis()` is not monotonic.**

```java
long start = System.currentTimeMillis();
awaitVendorResponse(clientId);
long elapsed = System.currentTimeMillis() - start;   // BROKEN
if (elapsed > TIMEOUT_MS) abortVerification(clientId);
```
Output: an NTP step backward during the call makes `elapsed` negative; the `if` never trips, the
verification never aborts, and a stuck `DocumentVerification` call blocks a review-queue slot
indefinitely. Fix:
```java
long start = System.nanoTime();
awaitVendorResponse(clientId);
long elapsedNanos = System.nanoTime() - start;
if (elapsedNanos > TIMEOUT_NANOS) abortVerification(clientId);
```

**5.2.52 — parallel streams don't inherit "the pool you're in."**

```java
ExecutorService settlementPool = Executors.newFixedThreadPool(8);
settlementPool.submit(() -> {
    stakeIds.parallelStream()                 // BROKEN assumption
        .forEach(StakeSettlement::settle);    // runs on ForkJoinPool.commonPool(), not settlementPool
});
```
Output: thread names in the settlement log read `ForkJoin.commonPool-worker-N`, not the pool's
own threads; under load the commonPool is shared with every other parallel-stream and
`CompletableFuture.supplyAsync` call in the JVM, so unrelated onboarding work slows down too.
Fix: don't route blocking or isolatable work through the default parallel-stream pool at all —
submit explicit tasks to `settlementPool` instead of relying on `parallelStream()`'s implicit
executor.

---

**Leaves covered:** 5.2.1–5.2.55 (55 leaves)
**Leaves deferred:** none
**Diagrams included:** D-213
**Target version:** Java 21 LTS
**Lines:** 250
