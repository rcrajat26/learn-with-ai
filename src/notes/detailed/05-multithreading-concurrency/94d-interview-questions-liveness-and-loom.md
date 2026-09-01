# 05 Multithreading and Concurrency — Interview questions: liveness and diagnostics — INTERVIEW (§5.1, questions 5.1.92–5.1.103)

**Target version: Java 21 LTS.** | **Part 5 of 5** | [Index](00-index.md)
Previous: [Interview questions: collections and executors II](94c2-interview-questions-collections-and-executors-ii.md) · Next: [Interview questions: liveness and Loom II](94d2-interview-questions-liveness-and-loom-ii.md)

---

### 5.1.92 What are the four Coffman conditions and which one do you break in practice.

A deadlock only forms if all four hold at once:

- **Mutual exclusion** — the resource can't be shared, one holder at a time.
- **Hold and wait** — a thread keeps what it already has while blocking for more.
- **No preemption** — nobody can force a thread to give up a lock it holds.
- **Circular wait** — a cycle of threads, each waiting on the next one's resource.

Break any single one and the deadlock is structurally impossible, not just statistically unlikely — that is the whole reason the taxonomy earns its keep in an interview rather than being trivia.

In practice you almost never touch mutual exclusion, because locks exist precisely because the resource genuinely can't be shared — two threads cannot both hold `FundsLedger`'s row lock on the same account and both be correct. You rarely get preemption for free in the JVM either: there is no OS-style priority-based lock stealing, and forcibly interrupting a thread mid-`synchronized` block is exactly the semantics `Thread.stop` used to provide — which is why it now throws `UnsupportedOperationException`, removed rather than merely deprecated as of Java 20. It left shared state half-updated with no way to reason about what condition it was left in.

So the two levers that actually work day to day are:

1. **Hold-and-wait** — acquire everything a task needs up front, or release between acquisitions instead of nesting them.
2. **Circular wait** — impose a total order on lock acquisition so every thread takes locks in the same order regardless of which one looks "first" from its own call site.

For `FundsLedger.transfer(accountA, accountB)` that means always locking the account with the smaller `AccountId` first, regardless of which side of the transfer it happens to be.

The naive version that violates this — shown here **broken** so the fix in 5.1.93 has something concrete to fix:

```java
// broken — locks in argument order, not a stable total order
void transferBroken(AccountId from, AccountId to, Money amount) {
    ledgerLocks.get(from).lock();
    try {
        ledgerLocks.get(to).lock();
        try {
            fundsLedger.debit(from, amount);
            fundsLedger.credit(to, amount);
        } finally {
            ledgerLocks.get(to).unlock();
        }
    } finally {
        ledgerLocks.get(from).unlock();
    }
}
```

Call this once as `transferBroken(accountA, accountB, 50)` and concurrently as `transferBroken(accountB, accountA, 30)` and the four Coffman conditions are all present simultaneously: each `Lock` is exclusive, each thread holds its first lock while waiting for the second, neither JVM thread can preempt the other's hold, and the two calls form a two-node cycle.

Nothing about `transferBroken` is exotic or contrived — it is the natural way to write the method if you only think about correctness within a single call, which is exactly why this bug survives code review so often.

**Follow-up:** Could you use a lock timeout instead of ordering?
Yes — `tryLock(timeout)` breaks no-preemption in effect, by letting a thread that can't get the second lock back off and retry rather than hold the first lock forever. That trades a deadlock for a possible livelock if both sides back off in lockstep on the same cadence, which is exactly why jittered backoff matters once you take this route.

**Pitfall:** naming only circular wait and treating the other three as trivia. Interviewers ask for all four specifically to see whether the candidate understands *why* ordering and up-front acquisition are the two practical fixes — that understanding only follows from having ruled out the other two conditions as untouchable in the first place.

**Second follow-up:** Is there a fifth condition people sometimes add?
No — the classic 1971 Coffman formulation is exactly these four, and all four are individually necessary and jointly sufficient. Anything else offered as a "fifth condition" (like "no timeout") is really a restatement of no-preemption applied to a specific mitigation, not a distinct structural requirement for deadlock to occur.

**Version note:** none of the four conditions or their fixes are version-sensitive in themselves — lock ordering and `tryLock` predate every JDK version this material cares about. The one adjacent version fact worth having ready is that biased locking, which used to be part of the folklore explanation for why uncontended `synchronized` was "free," was deprecated and disabled by JEP 374 in Java 15 and later removed; it has no bearing on deadlock avoidance, but interviewers sometimes probe whether a candidate still repeats the obsolete "biased → thin → fat" story when asked about locking generally.

### 5.1.93 Solve the account-transfer deadlock.

Two concurrent transfers — `transfer(accountA, accountB, 50)` and its mirror `transfer(accountB, accountA, 30)` — each lock their first argument then their second, in argument order.

- Thread 1 locks A, then blocks trying to lock B.
- Thread 2 has already locked B, then blocks trying to lock A.

That is a circular wait with exactly two participants, the smallest deadlock that can exist, and it is deterministic under load, not a rare race — any pair of transfers between the same two accounts in opposite directions will eventually collide this way. The fix is lock ordering by a stable, total order: `AccountId` wraps a `UUID`, which has a natural total order via `compareTo`, so compare on the business key, never on argument position or call-site order.

```java
void transfer(AccountId from, AccountId to, Money amount) {
    AccountId first = from.compareTo(to) <= 0 ? from : to;
    AccountId second = first.equals(from) ? to : from;
    Lock lockA = ledgerLocks.get(first);
    Lock lockB = ledgerLocks.get(second);
    lockA.lock();
    try {
        lockB.lock();
        try {
            fundsLedger.debit(from, amount);
            fundsLedger.credit(to, amount);
        } finally {
            lockB.unlock();
        }
    } finally {
        lockA.unlock();
    }
}
```

Both directions now acquire the same account's lock first, so the cycle can't form — one thread always fully acquires both locks, or blocks on the very first one, before the other thread can begin its own acquisition sequence.

**Pitfall:** ordering by object identity (`System.identityHashCode`) instead of a stable business key works until two `Account` objects collide on identity hash, or the wrapper gets recreated across a cache eviction and receives a new identity hash entirely. Order strictly on the immutable `AccountId`, never on a mutable wrapper's hash code.

**Follow-up:** What if you can't get a natural pairwise order — say, N accounts settling inside one batch `PaymentRun`?
Sort the whole batch's account IDs once at the top of the batch, then acquire in that sorted order across all N. It is the identical idea generalized from pairs to N-ary, and it still only needs a total order, not a single global lock.

**Second follow-up:** Could `tryLock` with a timeout replace ordering here entirely, so you never have to think about total order?
It would remove the deadlock, but at the cost of introducing retry logic, wasted work on the rollback path when the second lock times out, and a livelock risk if two transfers between the same pair keep colliding on their timeouts. Ordering is strictly cheaper when a stable business key already exists, which `AccountId` does — `tryLock` earns its keep for resources that genuinely have no natural total order, not as a first resort.

### 5.1.94 Deadlock versus livelock versus starvation versus lock convoy.

| Term | What's happening | Threads doing work? | Typical fix |
|---|---|---|---|
| Deadlock | Circular wait, nobody makes progress | No — all BLOCKED/WAITING forever | Lock ordering, timeouts |
| Livelock | Threads actively react to each other and repeatedly back off | Yes — burning CPU, RUNNABLE | Randomized backoff, breaking symmetry |
| Starvation | One thread never gets scheduled/never wins the lock | Others yes, this one no | Fair locks, priority fix, bounding queue depth |
| Lock convoy | Many threads serialize on one lock even though contention should be brief | Yes, but throughput collapses | Reduce hold time, shard the lock, lock-free structure |

The distinguishing interview question is CPU. Deadlock is 0% CPU on the stuck threads, because they are parked waiting for a monitor that will never free. Livelock is 100% CPU doing nothing productive, because the threads are actively, repeatedly, symmetrically reacting to each other.

A poison `WithdrawalTransaction` that keeps getting redelivered, rejected by a downstream validation, and requeued — because two retry handlers both back off and retry on exactly the same cadence as the payment run's clock tick — is a livelock, not a deadlock. The threads are working flat out, CPU pegged, just never making net progress on that one message.

Starvation is different again: not symmetric reaction, but one thread perpetually losing a fair fight, typically because an unfair `synchronized` monitor or an unfair `ReentrantLock(false)` keeps handing the lock to whichever thread happens to be scheduled next rather than the one that has been waiting longest.

Lock convoy is the throughput-shaped variant: no single thread is starved and there is no cycle, but so many threads pile up on one lock that system-wide throughput collapses even though every individual acquisition eventually succeeds — this shop sees it when 1,200 stake-reservation threads/sec all funnel through one coarse `synchronized` block instead of a sharded structure.

Starvation's fix in code is a one-argument constructor change, which is exactly why interviewers like asking for it directly:

```java
Lock stakeQueueLock = new ReentrantLock(true); // fair — FIFO grant order
```

`new ReentrantLock(true)` requests a fair lock, which grants to the longest-waiting thread rather than whichever thread the scheduler happens to wake first; the tradeoff is materially lower throughput than the default unfair lock under heavy contention, because a fair lock forces a queue hand-off instead of letting a lucky already-running thread barge in — never make every lock fair by default just to fix one starving caller.

**Follow-up:** How do you fix the redelivery livelock concretely?
Add randomized jitter to the retry delay so the two handlers desynchronize instead of retrying in lockstep, and cap redelivery count so a genuinely poison message dead-letters instead of cycling forever. Jitter fixes the livelock symptom; the dead-letter cap fixes the underlying poison message.

```java
long backoffMillis(int attempt) {
    long base = Duration.ofMillis(200).toMillis() * (1L << Math.min(attempt, 6));
    long jitter = ThreadLocalRandom.current().nextLong(base / 2);
    return base + jitter;
}

void handle(WithdrawalTransaction withdrawal, int attempt) {
    if (attempt >= MAX_REDELIVERIES) {
        deadLetter(withdrawal);
        return;
    }
    scheduler.schedule(() -> retry(withdrawal, attempt + 1),
            backoffMillis(attempt), TimeUnit.MILLISECONDS);
}
```

Randomizing on `ThreadLocalRandom` per attempt breaks the exact-cadence symmetry that produced the livelock in the first place; the hard `MAX_REDELIVERIES` cap is what turns "livelock" into "handled failure" instead of an infinite retry that merely looks less synchronized.

### 5.1.95 How do you detect a deadlock in production, and can the JVM break it?

Detection tools, from manual to continuous:

- `jstack <pid>` prints a `"Found one Java-level deadlock"` block naming the exact threads and lock cycle, when the deadlocked threads hold intrinsic (`synchronized`) monitors or `java.util.concurrent.locks.Lock` instances whose ownership the JVM can introspect.
- `jcmd <pid> Thread.print` produces the same data live, without needing `jstack` as a separate binary.
- `ThreadMXBean.findDeadlockedThreads()` lets you build a scheduled health check that pages a human before a support ticket about stalled `FundsLedger` transfers does.

**The JVM cannot break a deadlock itself.** There is no preemption mechanism in the platform — once threads are in a wait-for cycle on monitors, the JVM keeps reporting the cycle forever but never resolves it unilaterally. The only remedies are restarting the process or forcibly killing the offending threads, and killing a thread mid-`synchronized` is precisely the operation `Thread.stop` used to perform, which is exactly why it now throws `UnsupportedOperationException`.

The documented `jstack` output shape for the transfer deadlock in 5.1.93, reproduced (this is the exact block format `jstack` writes, not a live capture):

```
Found one Java-level deadlock:
=============================
"payment-run-worker-3":
  waiting to lock monitor 0x00007f... (a java.lang.Object),
  which is held by "payment-run-worker-7"
"payment-run-worker-7":
  waiting to lock monitor 0x00007f... (a java.lang.Object),
  which is held by "payment-run-worker-3"

Java stack information for the threads listed above:
"payment-run-worker-3":
        at FundsLedger.debit(FundsLedger.java:88)
        - waiting to lock <0x000000076ab...> (a Account)
        - locked <0x000000076ac...> (a Account)
"payment-run-worker-7":
        at FundsLedger.debit(FundsLedger.java:88)
        - waiting to lock <0x000000076ac...> (a Account)
        - locked <0x000000076ab...> (a Account)
```

Read it bottom-up: each thread's `locked` line names what it already holds, its `waiting to lock` line names what it wants next. Trace the two lines across both threads and the cycle is explicit, no guessing required.

**Pitfall:** assuming a deadlock will surface as an alert on its own. Nothing pages anyone by default; wire `findDeadlockedThreads()` into a scheduled health check, or the first signal is a support ticket about transfers that silently stopped completing.

**Follow-up:** Does `findDeadlockedThreads()` see the same deadlocks `jstack` reports?
Yes for platform threads holding introspectable monitors — it is the same underlying detection machinery `jstack` calls into. It has the identical blind spot for virtual threads and cross-resource deadlocks that 5.1.96 covers next, so a scheduled health check built on it is not a complete safety net by itself.

**Version note:** none of this — `jstack`, `jcmd Thread.print`, `ThreadMXBean.findDeadlockedThreads()` — changed shape across Java 21 through 25. What did change is what's on the other end of the stack: Java 24's JEP 491 (5.1.107) means fewer virtual threads get artificially pinned into monitor contention in the first place, which reduces false-positive-looking "contention" that isn't really a resource deadlock at all, just pinning masquerading as slow progress.

### 5.1.96 What deadlocks can `jstack` *not* see.

Three categories, each more relevant to this stack than the last:

- **Non-JVM resources.** A thread holding a database row lock while waiting on another thread's DB lock: `jstack` shows both threads as RUNNABLE or WAITING inside a JDBC call, with no cycle visible, because the actual cycle lives in the database's own lock manager, entirely outside anything the JVM can introspect.
- **Custom `Lock` implementations.** Only visible if they register ownership through `LockSupport`'s blocker mechanism (`LockSupport.setCurrentBlocker`); a hand-rolled lock that skips that call is structurally invisible to deadlock detection even though it behaves like a lock.
- **Virtual threads.** A virtual thread blocked on a monitor while unmounted has no OS thread behind it at all, so a deadlock purely among virtual threads is invisible to `jstack`, which only ever walks platform-thread stacks.

The tool for the virtual-thread case is `jcmd <pid> Thread.dump_to_file -format=json` (mechanics in 5.1.110), and even that dump, unlike classic `jstack`, does not automatically flag a cycle — it shows every thread's stack, mounted or not, but the deadlock-cycle detection logic behind the `"Found one Java-level deadlock"` banner is not run over virtual threads at all.

**Follow-up:** So what's your actual toolchain for a suspected cross-resource deadlock spanning the JVM and the database?
`jstack` (or the JSON dump if virtual threads are involved) for the JVM side, the database's own lock-wait view — Postgres `pg_locks` joined against `pg_stat_activity` — for the DB side, correlated manually by thread name and the query text each thread is blocked on. No single tool sees both halves of a cross-system cycle.

A custom lock that wants to be `jstack`-visible has to opt in explicitly:

```java
class LedgerRowLock {
    private final AtomicReference<Thread> owner = new AtomicReference<>();

    void lock() {
        while (!owner.compareAndSet(null, Thread.currentThread())) {
            LockSupport.setCurrentBlocker(this);
            LockSupport.park();
            LockSupport.setCurrentBlocker(null);
        }
    }

    void unlock() {
        owner.set(null);
        LockSupport.unpark(waitingThread());
    }

    private Thread waitingThread() {
        return null;
    }
}
```

Calling `LockSupport.setCurrentBlocker(this)` before `park()` is what lets a dump tool report *what* a parked thread is blocked on; skip it and the thread just shows as parked on nothing identifiable.

### 5.1.97 What do BLOCKED and WAITING each tell you in a thread dump.

- `BLOCKED` means the thread wants a `synchronized` monitor another thread currently holds — it is queued in the monitor's entry set, actively contending, and transitions to RUNNABLE the instant the holder releases and the scheduler grants it entry.
- `WAITING` / `TIMED_WAITING` means the thread already released or never needed a monitor and is instead parked voluntarily — inside `Object.wait()`, `LockSupport.park()`, `Thread.join()`, or blocked inside `Lock.lock()` from `java.util.concurrent`, which parks under the hood rather than monitor-blocking. `ReentrantLock` contention therefore always shows as WAITING, never BLOCKED.

The distinction changes what you do next. A pile of `BLOCKED` threads on the same monitor is a contention hotspot with an identifiable owner — read the dump for who currently holds it, and what that thread's own stack is doing. A pile of `WAITING` threads is threads *choosing* to wait, typically idle pool workers parked on an empty `LinkedBlockingQueue.take()` or a `CountDownLatch.await()` — not contention, just nothing queued for them.

The documented shape, side by side:

```
"payment-run-worker-9" #34 prio=5 os_prio=0 tid=0x... nid=0x2a1 waiting for monitor entry [0x...]
   java.lang.Thread.State: BLOCKED (on object monitor)
        at FundsLedger.debit(FundsLedger.java:88)
        - waiting to lock <0x000000076ab...> (a Account)

"pool-3-thread-2" #41 prio=5 os_prio=0 tid=0x... nid=0x2b6 waiting on condition [0x...]
   java.lang.Thread.State: WAITING (parking)
        at jdk.internal.misc.Unsafe.park(Native Method)
        - parking to wait for  <0x000000076cd...> (a java.util.concurrent.locks.AbstractQueuedSynchronizer$ConditionObject)
        at java.util.concurrent.locks.LockSupport.park(LockSupport.java:221)
        at java.util.concurrent.LinkedBlockingQueue.take(LinkedBlockingQueue.java:435)
```

The first thread is contending for a monitor someone else already owns; the second is idle, parked with nothing enqueued to work on — same two-line dump shape, opposite meaning.

**Pitfall:** treating every nonzero `BLOCKED` count as proof "the lock is the bottleneck." If the same handful of threads cycle quickly through BLOCKED and back to RUNNABLE across successive dumps, that is healthy, short-lived contention doing exactly what a lock is for. The actual smoking gun is BLOCKED threads whose identity and stack do not change across three consecutive dumps taken five seconds apart — that owner is genuinely stuck, not merely busy.

**Follow-up:** What does `TIMED_WAITING` add beyond plain `WAITING` that changes the diagnosis?
`TIMED_WAITING` means the park or wait call carries a deadline — `Thread.sleep(ms)`, `Object.wait(ms)`, `Lock.tryLock(timeout, unit)`. A thread stuck there is bounded by definition; a large cluster of `TIMED_WAITING` threads usually means a retry loop with backoff (5.1.94's livelock candidate) rather than a genuinely stuck resource wait, which is the useful signal `WAITING` alone doesn't give you.

### 5.1.98 A service is at 100% CPU with no throughput — walk your diagnosis.

100% CPU with zero throughput means threads are RUNNABLE and spinning, not blocked, so it is neither a classic deadlock (0% CPU) nor plain I/O starvation.

Take two `jstack` (or `jcmd Thread.print`) dumps five to ten seconds apart and diff the stacks of every RUNNABLE thread — if the top frames are identical across both samples with no application-level progress markers changing, that thread is spinning, not merely busy. Three causes account for most real incidents at this shop:

- **Livelocked retry loop** chewing through a poison `WithdrawalTransaction` (5.1.94), where the stack shows application retry/backoff frames cycling.
- **Spin-lock or busy-wait CAS loop** that never backs off, typically surfacing when a single hot `AtomicLong` counting settlements degenerates under the 3,400/sec settlement burst into cache-line ping-pong across cores, with `compareAndSet` sitting at the top of every sample and nothing changing beneath it.
- **GC thrash**, where application threads genuinely are RUNNABLE but making no forward progress because the CPU budget is consumed by back-to-back GC cycles — confirm or rule this out with `jstat -gcutil <pid> 1000` running in parallel with the thread dumps, watching for a GC generation that never drains.

Correlate the specific hot thread IDs against OS-level per-thread CPU (5.1.100) to confirm which threads, not just which state, are actually burning the core, since "100% CPU" at the process level can hide one pathological thread among many idle ones.

**Follow-up:** How do you tell a livelock from a raw spin-lock issue purely from the stack trace, without instrumentation?
A livelock's stack shows application-level retry/backoff code, with the specific frames cycling between samples as retry logic runs its course. A spin-lock issue pins the exact same low-level `compareAndSet`/`Unsafe` frame at the top of the stack across every sample, with nothing beneath it ever changing.

**Second follow-up:** Would enabling GC logging after the fact catch a GC-thrash cause retroactively?
No — GC logs (`-Xlog:gc*`) have to already be enabled before the incident, since they're a running record, not a snapshot you can request after the fact. This is the practical argument for always running production services with GC logging on by default at low overhead, rather than treating it as a diagnostic you enable only once something has already gone wrong.

### 5.1.99 A service is at 0% CPU with no throughput — walk your diagnosis.

Zero CPU with zero throughput means every thread that should be doing work is parked or blocked, not spinning — the opposite failure mode from 5.1.98, and it points somewhere entirely different.

- Start with `jstack`/`jcmd Thread.print`: a genuine `synchronized` deadlock announces itself directly via the `"Found one Java-level deadlock"` block.
- If that block is absent, look for a pool-exhaustion pattern: all workers WAITING on `LinkedBlockingQueue.take()` with an empty queue is healthy idle. All workers BLOCKED or WAITING inside one downstream client call that never returns is the failure — every request thread parked inside the card PSP client, waiting on a socket read that never completes because the PSP is down and no client-side timeout was ever configured, so the documented p99 of 11 seconds never gets a chance to trip because there is no timeout to trip at all.
- Check the connection pool independently of the downstream call: 14,000 concurrent sessions hitting a 20-connection HikariCP pool to the ledger database will park every one of them on `HikariPool.getConnection()` the instant the pool saturates. If connections are being checked out and never returned — a leak, not saturation — throughput drops permanently to zero while CPU sits idle, because there is never a connection available again without a restart.

**Pitfall:** assuming 0% CPU means "nothing is happening" and therefore safe to ignore briefly. It means every thread that would otherwise be doing CPU work is instead parked waiting on something external — that something is almost always an unbounded wait with no timeout, and the fix is nearly always adding one, not adding capacity.

**Insight:** 0% CPU with no throughput almost always traces to an external dependency called without a timeout, or a fixed-size resource pool leaking its permits; it is rarely a JVM-internal cause the way 100% CPU usually is, which is why the diagnosis order here — deadlock check, then pool state, then downstream timeouts — differs completely from 5.1.98's.

HikariCP has a built-in leak detector worth naming here, because it turns this whole diagnosis into an alert instead of a manual investigation:

```java
HikariConfig config = new HikariConfig();
config.setMaximumPoolSize(20);
config.setLeakDetectionThreshold(Duration.ofSeconds(5).toMillis());
```

Past the 5-second threshold, HikariCP logs a stack trace for whichever thread checked the connection out and hasn't returned it — pointing straight at the leaking call site instead of leaving you to infer it from a saturated pool and a pile of parked request threads.

### 5.1.100 How do you find which Java thread is burning a core.

Two-step correlation: OS first, then JVM.

1. On Linux, `top -H -p <pid>` shows per-thread CPU with the OS thread ID (TID) printed in decimal.
2. Convert that TID to hexadecimal — `printf '%x\n' <tid>`.
3. Grep for it in a `jstack <pid>` capture: Java thread dumps print the native thread ID as `nid=0x<hex>` on the same header line as the thread's Java name and state.

That single header line then tells you the thread's logical name, its state — almost always RUNNABLE for a genuinely CPU-burning thread — and its full stack directly beneath it; read the top few frames to see exactly what it was doing at the moment of capture. `jcmd <pid> Thread.print` gives the equivalent output without needing the separate `jstack` binary present.

For a more surgical, lower-overhead capture — especially when the hot thread rotates across a pool rather than staying pinned to one identity — attach `async-profiler` to the PID for a CPU flame graph, which sidesteps the manual TID-to-`nid` correlation entirely and aggregates across however many threads actually carried the hot code path.

**Pitfall:** on a virtual-thread-heavy service this TID-correlation technique only ever finds hot **carrier** threads, never the virtual thread mounted on one at capture time, unless the capture happens to land mid-mount. A virtual thread that spins briefly and then unmounts can be gone entirely by the time the TID is correlated back to a `jstack` dump — one more reason `jcmd Thread.dump_to_file -format=json` (5.1.110) becomes the primary tool, not a fallback, once Loom is in the picture.

A quick recall table for the whole liveness-and-diagnostics toolchain covered across 5.1.95–5.1.100, worth having in one place before an interview:

| Tool | Sees platform threads | Sees virtual threads | Flags deadlock cycles automatically | Shows lock ownership |
|---|---|---|---|---|
| `jstack <pid>` | Yes | Only while mounted | Yes, for introspectable monitors | Yes |
| `jcmd <pid> Thread.print` | Yes | Only while mounted | Yes, for introspectable monitors | Yes |
| `jcmd <pid> Thread.dump_to_file -format=json` | Yes | Yes, mounted or not | No | No — omitted from the JSON format |
| `ThreadMXBean.findDeadlockedThreads()` | Yes | Only while mounted | Yes | N/A — returns thread IDs only |
| `async-profiler` / JFR execution samples | Yes | Yes, when sampled while mounted | No — it's a profiler, not a deadlock detector | No |

Reading this table left to right is the honest summary of 5.1.96 and 5.1.110 in one place: nothing sees unmounted virtual threads *and* automatically flags a cycle — you always trade one capability for the other once Loom is genuinely in play.

**Follow-up:** Is there a way to get the same answer without manual TID arithmetic at all?
Yes — Java Flight Recorder's `jdk.ExecutionSample` event, viewed in JDK Mission Control, attributes CPU samples to Java thread names directly without ever surfacing the OS TID, and it can run continuously at low overhead rather than requiring a point-in-time `top -H` capture during the incident.

**Version note:** the `top -H` → `nid=0x<hex>` correlation is stable across every JDK version discussed in this material; nothing about it changed with Loom. What changes with Loom is only the caveat above — the technique finds carriers, not virtual threads — which is a new *category* of blind spot introduced by JEP 425/444 (virtual threads, finalized in Java 21), not a change to the diagnostic technique itself.

---

**ThreadLocal, virtual threads, structured concurrency**

### 5.1.101 How is `ThreadLocal` stored, and why is the key weak but the value strong.

Each `Thread` — platform or virtual — carries a `ThreadLocal.ThreadLocalMap`, a private, open-addressed hash map that lives on the thread itself, not a shared map keyed by thread identity somewhere central.

- Every `Entry` in that map is a `WeakReference<ThreadLocal<?>>` for the **key**.
- The **value** is held with a plain, ordinary **strong** reference.

The key is weak on purpose: once nothing outside the map still references the `ThreadLocal` instance itself — say a `static final` field's declaring class gets unloaded along with its classloader — the entry's key can be collected by the GC, and the now-key-less slot becomes reclaimable the next time `get`/`set`/`remove` happens to sweep past it during its own housekeeping.

The value is strong for a symmetric reason: a weak value would let a thread's own session context vanish mid-use under GC pressure while the thread is still actively reading it — an intermittent, essentially undebuggable heisenbug that would appear only under memory pressure.

That asymmetry is exactly what creates 5.1.102's leak shape: the key can be collected, but a stale, strongly-referenced value with no live key just sits in the map — unreachable by any code that still has the original `ThreadLocal` reference — until some future map operation happens to notice and sweep it.

**Follow-up:** does calling `remove()` help even immediately before a `set()` with a fresh value anyway?
Yes, specifically when it is the *last* use on that thread before the thread returns to a pool — `remove()` clears both the key slot and the strongly-held value immediately, rather than waiting for GC to collect the weak key and then waiting further for some future map operation to notice the key is gone and reclaim the value.

**Second follow-up:** why does `ThreadLocalMap` use open addressing with linear probing instead of chaining like `HashMap`?
Because it is optimized for the common case of very few entries per thread — most threads hold a handful of `ThreadLocal`s at most — where the overhead of allocating a `Node` per chain entry would dominate; linear probing over a small array is both smaller and faster at that scale, and it is also what makes the weak-key sweep cheap, since `expungeStaleEntry` can walk a contiguous probe sequence rather than following pointers.

### 5.1.102 Describe the thread-pool `ThreadLocal` leak — both halves.

**Half one, the map-half leak.** A pooled worker thread lives far longer than any single task submitted to it. If a task calls `sessionContext.set(ctx)` and never calls `remove()`, the resulting `Entry` — weak key, strong value — sits in that worker's `ThreadLocalMap` after the task completes, because the map is swept only lazily, on some *future* `get`/`set`/rehash operation, never automatically on task completion.

**Half two, the cross-task leak.** The very next unrelated task that happens to land on that same pooled thread, if it calls `get()` naively without first checking for a stale or unexpected value, silently reads the *previous* task's context — a correctness bug, not merely a memory one, and one that is essentially invisible in testing because tests rarely reuse the exact same pooled thread across two different logical clients.

This shop measured the map-half leak directly in production: a per-request `ThreadLocal` cache of client restriction lookups grew from roughly 200 live entries to **443,267** over a single weekend, because the executor's core pool threads never terminated, each one accumulated one stale `Entry` per distinct client ID ever routed to it, and nothing in the request path ever called `remove()` on task completion.

```java
executor.execute(() -> {
    try {
        clientRestrictionsContext.set(loadRestrictions(clientId));
        process(request);
    } finally {
        clientRestrictionsContext.remove();
    }
});
```

The `finally` is the entire fix for both halves at once — it bounds the entry's lifetime to the task's lifetime rather than the thread's, which eliminates the map-half leak directly and eliminates the cross-task leak as a side effect, since there is nothing stale left for the next task to accidentally read.

**Pitfall:** wrapping only the `set` call in a `try` without a matching `finally`, or assuming an exception path will "naturally" clean things up on its own. An exception thrown anywhere between the `set` and any manual cleanup leaves the stale entry exactly as it would have been with no cleanup logic at all.

**Follow-up:** would a bounded-size `ThreadLocal` cache with an eviction policy have prevented the 200 → 443,267 growth even without `remove()`?
No — the growth is bounded by *distinct clients ever routed to each worker thread*, not by any cache the application code controls; `ThreadLocalMap` itself has no eviction policy, so nothing short of `remove()` (or the worker thread dying, which a fixed-size pool never lets happen) bounds it.

### 5.1.103 Why does `InheritableThreadLocal` not solve context propagation for pools.

`InheritableThreadLocal` copies the parent thread's value into the child **at the exact moment the child `Thread` object is constructed** — a one-time snapshot taken inside the `Thread` constructor, not a live link that tracks the parent's current value over time.

That model fits `Thread`-per-task code perfectly, where a brand-new thread really is created for each unit of work and really does have one obvious, single parent to inherit from at that moment.

It is structurally wrong for a pool, though: pool worker threads are constructed once, up front, long before any particular task's context exists at all, so there is no meaningful "parent" to inherit from at construction time. The one-time inheritance already happened, against whatever thread happened to be constructing pool threads at startup — often the main thread — and every subsequent task that ever runs on that worker inherits that same stale, startup-time snapshot rather than its own submitter's actual context.

This is precisely why `ScopedValue` (5.1.114) and structured concurrency were designed around explicit, call-scoped binding instead of thread-identity-based inheritance — the propagation model has to be tied to the logical *task*, not to a `Thread` object's identity, and a pool worker's `Thread` identity is deliberately decoupled from any one logical task by the entire premise of pooling.

**Insight:** virtual threads change nothing here on their own, even though Loom makes thread-per-task cheap again. `InheritableThreadLocal`'s copy-at-construction semantics are orthogonal to platform-vs-virtual; a virtual-thread-per-task executor genuinely does construct one new virtual thread per task, so inheritance *would* technically work there, but that is an argument for using `ScopedValue` or explicit context passing everywhere uniformly, not a reason to lean on `InheritableThreadLocal` selectively depending on which executor happens to be in play.

**Follow-up:** is there a pooled-executor-safe way to get automatic propagation without `ScopedValue`, on Java 21 today?
Not automatically — the honest answer is explicit propagation: capture the context at submission time and wrap the `Runnable`/`Callable` so it sets and clears the context itself, which is exactly what tracing libraries like Micrometer's context propagation do under the hood. There is no free automatic-inheritance mechanism for pools short of `ScopedValue` combined with structured concurrency.

```java
Runnable propagating(Runnable task) {
    Map<String, String> captured = clientRestrictionsContext.get();
    return () -> {
        clientRestrictionsContext.set(captured);
        try {
            task.run();
        } finally {
            clientRestrictionsContext.remove();
        }
    };
}

executor.execute(propagating(() -> process(request)));
```

Wrapping the submission this way makes propagation explicit and visible at the call site, which is the honest tradeoff against `InheritableThreadLocal`'s implicit-but-wrong behavior — more boilerplate, but boilerplate that actually does what it looks like it does.

---

**Leaves covered:** 5.1.92–5.1.103 (12 questions)
**Leaves deferred:** none
**Diagrams included:** none
**Target version:** Java 21 LTS
**Lines:** 420
