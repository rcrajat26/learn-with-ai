# 05 Multithreading and Concurrency — Interview questions: locks and atomics — INTERVIEW (§5.1, questions 5.1.34–5.1.47)

**Target version: Java 21 LTS.** | **Part 5 of 5** | [Index](00-index.md)
Previous: [Interview questions: fundamentals II](94a2-interview-questions-fundamentals-ii.md) · Next: [Interview questions: locks and atomics II](94b2-interview-questions-locks-and-atomics-ii.md)

---

### 5.1.34 `synchronized` versus `ReentrantLock`: when do you reach for each

`synchronized` is the default, and the honest answer starts there rather than at the fancier tool. It's JVM-native: the bytecode compiler emits `monitorenter`/`monitorexit` around the block and, critically, emits `monitorexit` on every exit path including exceptions — that's not discipline the programmer has to remember, it's the compiler's job. Under the hood HotSpot's monitor (`ObjectMonitor`) maintains an owner field, a recursion count for reentrancy, and two internal wait structures, `_cxq` (a lock-free contention queue newly-blocked threads CAS themselves onto) and `_EntryList` (a list the owning thread migrates waiters into on unlock, from which the JVM picks a successor to wake) — none of that is visible to the programmer, which is precisely the appeal. Reach for `ReentrantLock` when you need something `synchronized` structurally cannot express: `tryLock(timeout)` so a thread contending for `FundsLedger.reserveStake` doesn't hang indefinitely behind a stuck settlement, `lockInterruptibly()` so a blocked thread can be cancelled from outside, multiple independent `Condition` objects on one lock (a bounded withdrawal queue needing separate `notFull`/`notEmpty` waits, 5.1.42/5.1.50), or explicit fairness (5.1.36). Everything else — a plain mutex around one critical section with one obvious exit path — should stay `synchronized`; it is less code, has no unlock-discipline to get wrong, and the JIT can apply lock elision and adaptive spinning to it in ways a library-level `Lock` can't fully match.

**Follow-up:** Does `ReentrantLock` outperform `synchronized` under contention on Java 21? Not reliably — both bottom out in the same OS-level park/unpark under real contention (5.1.48); `ReentrantLock`'s actual edge is its feature surface, not raw throughput, and under low contention `synchronized`'s fast CAS path is competitive since biased locking's removal (5.1.36) leveled that ground further.

**Pitfall:** treating `ReentrantLock` as "the modern replacement" for `synchronized` and reaching for it by default. That trades away the compiler-guaranteed unlock-on-exception for manual `try`/`finally` discipline (5.1.35) in exchange for features most call sites never use, with no throughput win in the common uncontended case.

**[VERSION-TRAP]** On Java 21, `synchronized` **pins** a carrier thread whenever a virtual thread blocks inside it — the virtual thread cannot unmount from its carrier, so the carrier is stuck too, defeating the purpose of running thousands of virtual threads over a handful of platform carriers. `ReentrantLock`'s park-based blocking does not pin. This was the real, narrow justification for "prefer `ReentrantLock` inside virtual-thread bodies" on 21. **JEP 491, final in JDK 24**, removes `synchronized`'s pinning behavior entirely — the virtual thread now correctly unmounts even while blocked inside a monitor — and `-Djdk.tracePinnedThreads` was removed alongside it since there's nothing left to trace. On 24+, this whole justification for preferring `ReentrantLock` in virtual-thread code disappears.

**Second follow-up:** How would you actually detect pinning in a Java 21 production service handling `FundsLedger` traffic on virtual threads? Run with `-Djdk.tracePinnedThreads=full`, which dumps a stack trace every time a virtual thread parks while pinned — that trace points directly at the `synchronized` block to either replace with `ReentrantLock` or leave alone if the pinned section is short-lived and contention is low.

**Third follow-up:** Does pinning corrupt correctness, or only hurt throughput? Only throughput and scheduling fairness — a pinned carrier just can't run other virtual threads for the duration, which under enough concurrent pinning starves the whole carrier pool; the pinned code itself still executes correctly, which is why the pinning discussion belongs in a performance review, not a correctness review.

```java
// Java 21: this method, invoked from a virtual thread, pins its carrier for the
// duration of reserveAgainstLedger — replace synchronized with ReentrantLock to unpin
Object monitor = new Object();

void reserveStakeOnVirtualThread(ClientId clientId, Money stake) {
    synchronized (monitor) {                 // <- pins the carrier on Java 21
        reserveAgainstLedger(clientId, stake);
    }
}

// fixed for Java 21 virtual-thread call sites
private final ReentrantLock reservationLock = new ReentrantLock();

void reserveStakeOnVirtualThreadFixed(ClientId clientId, Money stake) {
    reservationLock.lock();                  // parks without pinning the carrier
    try {
        reserveAgainstLedger(clientId, stake);
    } finally {
        reservationLock.unlock();
    }
}
```

---

### 5.1.35 Why must `unlock()` be in a `finally`

Because `ReentrantLock.lock()` and `unlock()` are two independent method calls with no compiler-enforced pairing — unlike `synchronized`, where the JVM itself emits `monitorexit` on every possible exit from the block. If the critical section between `lock()` and `unlock()` throws and `unlock()` isn't guaranteed to run regardless, the lock is held forever: nothing times it out, nothing detects the thread died mid-section (barring `Thread.holdsLock` introspection nobody actually polls), and there's no ordinary JVM machinery that reclaims a `ReentrantLock` the way an OS reclaims file descriptors on process exit. Concretely on `FundsLedger.reserveStake`: a leaked lock there doesn't just strand one caller, it stops every other thread trying to reserve a stake for that same client permanently, and because a plain `lock()` call blocks indefinitely with no timeout, the failure has no natural self-healing path — it needs an operator restart. The idiom fixes this by construction:

```java
reservationLock.lock();
try {
    reserveAgainstLedger(clientId, stakeAmount);
} finally {
    reservationLock.unlock();
}
```

`lock()` is called **outside** the `try` deliberately — if acquisition itself fails or throws before the lock is actually held, the `finally` block would otherwise call `unlock()` on a lock the current thread never took, throwing `IllegalMonitorStateException` and masking whatever the real failure was.

**Follow-up:** What if `unlock()` itself throws? It's specified not to for the JDK's own `Lock` implementations — `unlock()` on a lock a thread legitimately holds is a bookkeeping decrement, not an operation with meaningful failure modes; if a custom `Lock` implementation can throw from `unlock()`, that is a defect in that implementation, not a scenario ordinary code needs to defend against.

**Pitfall:** placing `lock.lock()` inside the `try` block "for symmetry" with `unlock()`. If the JVM throws between entering `try` and completing acquisition (rare, but real under memory pressure during lock bookkeeping), the `finally` fires and calls `unlock()` on a lock never actually acquired.

**Second follow-up:** Does the same discipline apply to `Semaphore.acquire()`/`release()` and `StampedLock`'s explicit unlock calls? Yes across the board — anything in `java.util.concurrent.locks` and `Semaphore` that pairs an explicit acquire call with an explicit release call needs the release in a `finally`, because none of them get compiler-guaranteed cleanup the way `synchronized` does.

**Third follow-up:** What tooling catches a forgotten `unlock()` before it reaches production? Static analysis (SpotBugs' `UL_UNRELEASED_LOCK` rule, Error Prone's lock checks) flags a `lock()` call not immediately followed by a `try`/`finally` pattern; at runtime, a thread dump showing a `ReentrantLock` with a permanent owner and other threads parked on it in `WAITING` state is the live symptom to look for.

---

### 5.1.36 What is a fair lock and what does it cost

A fair `ReentrantLock`, constructed with `new ReentrantLock(true)`, hands the lock to whichever thread has been waiting longest — strict FIFO order enforced by walking the AQS wait queue rather than letting a freshly-arriving thread win a race for a just-released lock. That guarantee is worth paying for when starvation itself is the failure mode to avoid: an operator-approval queue for a `PaymentRun`, where every queued operator's request must eventually be serviced regardless of how many later requests keep arriving, benefits from fairness precisely because bounded wait time matters more than aggregate throughput. The cost is that fairness removes the fast path entirely — even when the lock happens to be free at the instant a thread calls `lock()`, a fair lock still checks whether the queue is non-empty and, if so, forces the new arrival to queue behind everyone already waiting rather than letting it CAS the lock directly. That single extra check, multiplied across every acquisition, routinely costs an order of magnitude in throughput versus barging (5.1.37) under light-to-moderate contention, because it converts what could have been a same-thread CAS-and-continue into a queue-and-park round trip through the OS scheduler. On `FundsLedger`'s 3,400 settlements/sec burst, defaulting to fairness for the sake of a guarantee the workload doesn't actually need (settlement processing order doesn't have to match lock-queue arrival order) would materially cut the ceiling for no correctness benefit.

**Follow-up:** Does fairness guarantee zero starvation in absolute terms? Only relative to other threads competing through that same `Lock` object — it says nothing about OS-level scheduling fairness across the whole system, and a newly-created thread not yet queued at all is unaffected by the guarantee until it actually calls `lock()`.

**Pitfall:** treating fairness as "free correctness" with no downside and defaulting every `ReentrantLock` in a codebase to `true`. On a hot path this can be an order-of-magnitude throughput hit for a starvation guarantee that specific lock never actually needed.

```java
// operator approval queue for PaymentRun sign-off — starvation is the failure mode to avoid
private final ReentrantLock approvalLock = new ReentrantLock(true);   // fair: strict FIFO grant order

void submitForSignOff(PaymentRun run) {
    approvalLock.lock();
    try {
        queueForOperatorReview(run);       // every queued operator eventually gets a turn
    } finally {
        approvalLock.unlock();
    }
}
```

**Second follow-up:** Does a fair `ReentrantLock` also make its `Condition`s fair? Yes — `Condition.await()`/`signal()` created from a fair lock hand the lock to the longest-waiting thread on resumption too, preserving FIFO order end to end rather than just at initial acquisition.

**Third follow-up:** Is `synchronized` ever fair? No — `synchronized` offers no fairness knob at all; the JVM's monitor implementation makes no FIFO guarantee about which blocked thread gets the monitor next, which is itself a reason to reach for `ReentrantLock(true)` when fairness is a hard requirement rather than trying to approximate it with `synchronized`.

---

### 5.1.37 Why is barging faster than fairness

Barging means a thread calling `lock()` on a lock that happens to be free takes it via a single successful CAS on the AQS `state` field, full stop — it never consults the wait queue, never parks, never triggers a context switch, and the whole operation is a handful of CPU cycles. That's the fast path an uncontended or lightly-contended non-fair lock takes essentially every time. A fair lock forbids exactly that shortcut: even when the lock is free at the moment `lock()` is called, a fair implementation must first check whether the AQS wait queue is non-empty, and if it is, the new arrival must queue behind existing waiters rather than jump the CAS — turning what would have been one atomic instruction into queue-node allocation, insertion, and (usually) a park/unpark round trip through the kernel scheduler, which is roughly an order of magnitude more expensive than a bare CAS. The efficiency case for barging rests on how rarely that shortcut is unavailable in real workloads: on `ClientRestrictions`' 99%-read cache, the rare write-path lock/unlock pairs almost always find the lock free and barge through in nanoseconds; forcing every one of them through a fairness check would tax the overwhelmingly common uncontended case to protect against a contention scenario that barely occurs.

**Follow-up:** Can barging itself cause starvation? Yes in principle — a thread parked at the head of the AQS queue can be repeatedly overtaken by threads that barge in while it's still waking up, though in practice this is self-limiting because the parked thread, once `unpark`ed, retries its own CAS on equal footing with any new arrival rather than being forced back to the tail.

**Insight:** barging and fairness operate on the exact same primitive — the AQS `state` field and its CAS. The only difference is one extra branch ("is the queue non-empty?") before attempting the CAS. That single branch is where the entire throughput gap between the two modes comes from.

| Path | Steps taken | Approximate cost |
|---|---|---|
| Barge, lock free | One CAS on `state`, done | Nanoseconds |
| Fair, lock free | Check queue non-empty, then CAS if empty | Nanoseconds, but conditional |
| Contended, either mode | Allocate/queue node, park, wait for `unpark` | Order of magnitude higher — a full OS scheduler round trip |

**Second follow-up:** Does `synchronized` also barge? Yes — an uncontended `monitorenter` is a single CAS attempt on the object header (or an inline cache check on Java 21's monitor implementation) with no queue consultation at all, which is why `synchronized` and non-fair `ReentrantLock` post similar numbers on lightly-contended workloads.

---

### 5.1.38 When does a `ReadWriteLock` actually win

A `ReadWriteLock` earns its keep specifically when reads vastly outnumber writes **and** the protected critical section is expensive enough that serializing readers against each other under a plain mutex genuinely costs something. `ClientRestrictions`' read cache is the textbook case: with 99% of the 2.4M-client lookup traffic being reads (does this client currently carry `SELF_EXCLUDED`, `WITHDRAWAL_HELD`, or anything else blocking?) and writes (a restriction applied or lifted) rare, a plain `synchronized`/`ReentrantLock` mutex would force every one of those reads to queue behind every other read even though none of them mutate anything — pure wasted serialization. `ReentrantReadWriteLock` lets any number of readers hold the read lock simultaneously and only forces exclusivity for the rare writer, so read throughput scales with core count instead of collapsing to one-at-a-time. It **loses** in two situations: when the guarded read is cheap enough that the read-lock's own acquire/release bookkeeping (tracking reader counts, checking for a waiting writer) costs more than the mutex it replaced ever did, and when writes are frequent enough that readers rarely get to actually overlap, in which case `ReadWriteLock`'s extra internal state (two conceptual locks, a reader count, writer-preference logic) is paid for with no concurrency benefit over a single `ReentrantLock`.

**Follow-up:** What's the alternative when reads are cheap but very frequent? A `StampedLock`'s optimistic read (5.1.40) skips locking almost entirely for the common case, or — where the guarded value changes rarely relative to reads — an immutable snapshot published through a single `volatile` reference swap, which needs no lock at all on the read side.

**Interview:** "Would `ReadWriteLock` help `FundsLedger.reserveStake`?" No — every call there is a mutation across the ledger's cash/bonus buckets, so effectively every caller is a writer; `ReadWriteLock` degenerates to plain mutual exclusion with extra overhead and buys nothing.

```java
private final ReentrantReadWriteLock restrictionsLock = new ReentrantReadWriteLock();

boolean isBlocked(ClientId clientId, RestrictionType type) {
    restrictionsLock.readLock().lock();
    try {
        return activeRestrictions(clientId).stream().anyMatch(r -> r.type() == type);
    } finally {
        restrictionsLock.readLock().unlock();
    }
}

void applyRestriction(ClientId clientId, Restriction restriction) {
    restrictionsLock.writeLock().lock();
    try {
        restrictionsFor(clientId).add(restriction);
    } finally {
        restrictionsLock.writeLock().unlock();
    }
}
```

**Second follow-up:** Is `ReentrantReadWriteLock` reader- or writer-preferring? Non-fair mode has no strict preference and can starve a waiting writer under sustained read load; fair mode (`new ReentrantReadWriteLock(true)`) guarantees a waiting writer isn't perpetually overtaken by new readers, at the usual fairness throughput cost.

**Third follow-up:** Can the same thread hold both a read lock and a write lock it acquired independently, for unrelated purposes? A thread already holding the write lock can also acquire the read lock (used for downgrading, 5.1.39) since the write lock implies full access; but a thread holding only the read lock cannot separately acquire the write lock on top of it — that's the upgrade case, and it deadlocks as covered next.

---

### 5.1.39 Why can you downgrade a write lock to a read lock but not upgrade

Downgrading — acquire the write lock, then acquire the read lock while still holding the write lock, then release the write lock — is safe because the thread never loses exclusivity partway through: it moves from "nobody else may read or write" straight to "I may read, others may also now read," which is a strictly weaker guarantee reached without ever passing through a window where two threads could believe they hold conflicting access simultaneously. Upgrading — holding the read lock and then trying to acquire the write lock while still holding the read lock — is unsupported and unsafe by construction: if two threads both hold the read lock on `ClientRestrictions`' cache and each then calls `writeLock().lock()` without releasing its read lock first, both block forever, each waiting for the other's read lock to drain, and neither will ever release its own read lock because each is waiting on the write lock it hasn't gotten yet. There's no symmetric way to break that without one thread unilaterally dropping its read lock and racing to reacquire as a writer — and that reopens exactly the window (another thread mutating state between the drop and the reacquire) the whole two-phase protocol exists to close. `ReentrantReadWriteLock`'s javadoc states this directly: read-to-write upgrade is not supported.

**Follow-up:** How do you implement "read, then conditionally write" safely given this? Release the read lock entirely, acquire the write lock fresh, and **re-check the condition inside the write-locked section** — never assume a value observed under the read lock is still true once that lock has been released, because another writer may have run in the gap.

**Pitfall:** calling `writeLock().lock()` while still holding `readLock()` on the same thread and treating the resulting hang as a bug in unrelated code. It's a designed-in, documented deadlock — grep the call site for a lingering read-lock hold before looking anywhere else.

**Second follow-up:** Is this specific to `ReentrantReadWriteLock`, or true of read-write locking in general? It's specific to how `ReentrantReadWriteLock` is built — the restriction is documented for that class; a different read-write lock implementation could in principle support single-thread upgrade with different internal bookkeeping, but the JDK's version doesn't, and treating "upgrade is unsafe" as a blanket rule is the safer interview answer.

```java
// BROKEN — read-to-write upgrade deadlocks if another thread also holds the read lock
readWriteLock.readLock().lock();
try {
    if (needsRestrictionUpdate(clientId)) {
        readWriteLock.writeLock().lock();   // can deadlock against a concurrent reader doing the same
        try {
            applyRestrictionUpdate(clientId);
        } finally {
            readWriteLock.writeLock().unlock();
        }
    }
} finally {
    readWriteLock.readLock().unlock();
}

// FIXED — release the read lock fully, then acquire the write lock, then re-check
readWriteLock.readLock().lock();
boolean needsUpdate;
try {
    needsUpdate = needsRestrictionUpdate(clientId);
} finally {
    readWriteLock.readLock().unlock();
}
if (needsUpdate) {
    readWriteLock.writeLock().lock();
    try {
        if (needsRestrictionUpdate(clientId)) {   // re-check: state may have changed after the read lock dropped
            applyRestrictionUpdate(clientId);
        }
    } finally {
        readWriteLock.writeLock().unlock();
    }
}
```

---

### 5.1.40 What is `StampedLock`'s optimistic read and what must you not do inside one

`StampedLock.tryOptimisticRead()` returns a `long` stamp — essentially a version snapshot of an internal counter — without acquiring anything at all: no CAS on a lock-state field for the reader, no memory barrier issued, just a plain read of the counter. The caller then reads whatever shared data it needs directly, unguarded, and only afterward calls `lock.validate(stamp)`, which checks whether any writer acquired the write lock (and thus bumped the counter) since the stamp was taken. If `validate` returns `false`, the optimistic read is discarded and the caller must retry, typically by falling back to a full `readLock()`. Applied to the cached `LimitSet(dailyDeposit, maxStake, monthlyLoss)`: a stake-eligibility check can read all three fields with zero locking overhead and validate once at the end, paying a real lock's cost only on the rare occasion a limit change actually raced with the read — which on a value that changes on the order of once per compliance event against millions of stake checks is a very good trade. The rule that makes this safe rather than reckless: **nothing read inside the optimistic section may be acted on irreversibly before `validate()` succeeds** — no I/O, no state mutation, no exception thrown based on the value — because the fields read during the window are not protected against a concurrent writer and may be a torn, mid-update mix of old and new values; the code only learns whether that mix was valid after the fact.

```java
long stamp = limitsLock.tryOptimisticRead();
long dailyDeposit = limits.dailyDeposit();
long maxStake = limits.maxStake();
long monthlyLoss = limits.monthlyLoss();
if (!limitsLock.validate(stamp)) {
    stamp = limitsLock.readLock();
    try {
        dailyDeposit = limits.dailyDeposit();
        maxStake = limits.maxStake();
        monthlyLoss = limits.monthlyLoss();
    } finally {
        limitsLock.unlockRead(stamp);
    }
}
```

**Follow-up:** Why isn't a plain `volatile` field enough here? A single `volatile` gives atomicity for that one field alone, but `LimitSet` spans three fields — reading them individually as separate volatiles can still observe an inconsistent combination (a stale `dailyDeposit` paired with a fresh `maxStake`) unless all three are captured as one atomically-swapped reference, which is exactly what the validated optimistic read achieves without ever blocking the writer.

**Pitfall:** dereferencing a field read inside the optimistic block to perform a side effect — throwing `InsufficientFundsException`, logging, returning a value to a caller — **before** calling `validate()`. If the read was torn, that side effect just fired on garbage data with no way to un-fire it.

**Second follow-up:** What does `tryOptimisticRead()` return if a writer currently holds the write lock at the moment it's called? It returns `0`, a sentinel meaning "no optimistic read is possible right now" — `validate(0)` always fails, so the caller falls straight through to the full `readLock()` path without needing a special case.

**Third follow-up:** How does `validate()` actually detect a concurrent write without locking? It compares the stamp's embedded version bits against `StampedLock`'s current internal state word — a successful `writeLock()` acquisition always changes that word's version bits, so a mismatch is proof a write happened, and this comparison is itself just a plain volatile-field read, cheap enough to make the whole optimistic protocol worthwhile.

---

### 5.1.41 Why is `StampedLock` not reentrant, and what happens if you try

`StampedLock` tracks its state purely through the stamp value it hands back on acquisition — there is no per-thread "who currently owns this" bookkeeping the way `ReentrantLock` and `synchronized` maintain a hold count against the owning thread's identity. That absence is deliberate: adding owner-tracking would cost exactly the per-acquisition overhead `StampedLock` exists to avoid, which is what makes its optimistic-read path (5.1.40) cheap in the first place. The consequence: if a thread already holding the write lock calls `writeLock()` again — directly, through recursion, or by calling a helper method that also takes the same lock — the second call blocks waiting for the stamp to be released. Since the *same* thread holds the outstanding stamp and will never call `unlockWrite` from inside a call it hasn't returned from, the thread deadlocks against itself. Concretely, if a `LimitSet`-update path calls a private helper that also tries to acquire the same `StampedLock`'s write lock, the code compiles fine, tests pass if that helper is never exercised through the locked call path, and the first production request that actually traverses both call sites simultaneously hangs forever with no exception to point at the cause.

**Follow-up:** Why did the JDK authors accept this trade-off instead of adding reentrancy? Because reentrancy bookkeeping is exactly the per-acquisition cost `StampedLock` was designed to strip out; restoring it would undo the performance case for using `StampedLock` over `ReentrantReadWriteLock` in the first place.

**Insight:** `StampedLock` doesn't even implement `java.util.concurrent.locks.Lock` — its unlock calls require the specific stamp value returned by the matching acquire, not merely "the same lock object," which is a direct consequence of tracking state by stamp rather than by owner identity.

**Second follow-up:** How would you refactor a recursive `LimitSet` updater around this constraint? Split the public entry point (which acquires the write lock and returns a stamp) from an internal, unlocked helper that assumes the caller already holds the lock — the recursive or nested call goes through the unlocked helper directly, never back through `writeLock()`.

**Third follow-up:** Is `StampedLock` at least reentrant for the same thread taking the *read* lock twice? No, not that either — read-locking twice from the same thread can also deadlock if a writer is queued in between the two read acquisitions, because `StampedLock`'s reader admission is not reentrancy-aware; treat every acquisition on `StampedLock` as if it could block regardless of what the calling thread already holds.

---

### 5.1.42 `CountDownLatch` versus `CyclicBarrier` versus `Phaser`

| Class | Reusable | Wait condition | QuizStakes shape |
|---|---|---|---|
| `CountDownLatch` | No — fires once, stays open forever after | Internal counter reaches zero; any thread may decrement, any thread may await | One-shot gate: block the operator dashboard read until N parallel `DocumentVerification` vendor calls for a batch have all returned |
| `CyclicBarrier` | Yes — resets automatically after every trip | All N registered parties must arrive before any proceed | Repeated rounds: N settlement workers each finish one batch of `FundsLedger` writes, then all wait for each other before the next batch starts, optionally merging results via the barrier action |
| `Phaser` | Yes, and parties can register/deregister between phases | A phase advances once all currently-registered parties arrive | Variable-width fan-out: a `PaymentRun`'s active worker count shrinks as batches of `WithdrawalTransaction`s complete and grows as new ones are picked up |

`CountDownLatch` cannot be reset once its count hits zero — it fires permanently open, which fits a startup or completion gate but nothing that needs to repeat. `CyclicBarrier` resets itself automatically each cycle and additionally runs a supplied `Runnable` exactly once per trip, on the thread that arrives last, which is the natural place to merge per-worker results before releasing the next round. `Phaser` generalizes both: it tracks phase numbers explicitly, supports dynamic party registration (`register()`/`arriveAndDeregister()`) so the set of participants can legitimately change between phases, and offers both blocking (`arriveAndAwaitAdvance`) and non-blocking (`arrive`) arrival — the latter lets a party signal it has finished this phase without waiting around for the others itself.

**Follow-up:** Why is `Phaser` rarely reached for despite being strictly more capable? Its flexibility comes with subtler failure modes — forgetting to deregister a completed party leaves the phase permanently stuck waiting for an arrival that will never come — and most real fan-out/fan-in problems have a fixed party count, where the simpler two classes are easier to reason about and to get right.

**Pitfall:** using a `CountDownLatch` and hunting for a "reset" method to reuse it for a second round of settlement workers. There isn't one — allocating a fresh `CountDownLatch` each round works but is itself a signal that a `CyclicBarrier` was the correct tool from the start.

```java
int workerCount = 4;
CyclicBarrier roundBarrier = new CyclicBarrier(workerCount,
    () -> mergeBatchResults(currentBatch));   // runs once per trip, on the last arriving thread

Runnable settlementWorker = () -> {
    while (moreBatches()) {
        processSettlementBatch();             // each worker's slice of FundsLedger writes
        try {
            roundBarrier.await();              // blocks until all 4 workers finish this round
        } catch (InterruptedException | BrokenBarrierException e) {
            Thread.currentThread().interrupt();
            return;
        }
    }
};
```

**Second follow-up:** What happens if one party never arrives at a `CyclicBarrier`? Every other waiting thread eventually throws `BrokenBarrierException` (immediately if a thread was interrupted or timed out first, otherwise once any thread does), and the barrier itself becomes permanently broken until explicitly `reset()` — it does not silently proceed with fewer parties.

**Third follow-up:** Could a `CountDownLatch` substitute for a `CyclicBarrier` if you just allocate a new one every round? Mechanically yes, but you lose the barrier action running exactly once on a designated thread, and you need external coordination to know when it's safe to allocate the next round's latch — `CyclicBarrier` bundles both concerns into one object precisely because they're needed together in a repeating-round design.

---

### 5.1.43 Is `Semaphore(1)` a mutex? (No — say why.)

Not really, despite behaving like one on the surface. A `Semaphore(1)` carries **no ownership concept**: the thread that calls `release()` need not be the same thread that called `acquire()`. That's a genuine feature in some designs — a request thread can `acquire()` a permit bounding in-flight calls to the Card PSP, and a separate callback thread handling the PSP's async response can `release()` it once that response lands, something `ReentrantLock` and `synchronized` cannot express since both are strictly tied to the acquiring thread and throw `IllegalMonitorStateException` (or, for `synchronized`, simply won't compile a mismatched release) if a different thread attempts to release. It also has **no reentrancy**: a thread that `acquire()`s the same `Semaphore(1)` twice blocks on its own second call and deadlocks itself, whereas `ReentrantLock.lock()` called twice by the owning thread just bumps a hold count and returns immediately. Applied concretely: a `Semaphore(N)` limiting concurrent outstanding `PaymentService` calls into the PSP is exactly right precisely because a permit acquired on the request thread is released on a different callback thread when the async result arrives — a lock could never model that relationship.

**Follow-up:** What actually makes something a true mutex, then? Enforced thread ownership on release plus safe re-acquisition by the owner (reentrancy) — `Semaphore(1)` has neither property; it only coincidentally shares the "at most one permit outstanding" arithmetic with a mutex.

**Pitfall:** using `Semaphore(1)` in place of a mutex and being surprised when, under a bug, a *different* thread calls `release()` and silently hands the permit to a second thread while the first still believes it holds exclusive access — the API permits this with no exception raised, by design.

```java
private final Semaphore pspInFlight = new Semaphore(20);   // bound concurrent PSP calls

void authoriseCardPayment(PaymentIntent intent) {
    pspInFlight.acquireUninterruptibly();
    cardPsp.authoriseAsync(intent, response -> {
        recordAuthorisation(response);
        pspInFlight.release();          // released on the callback thread, not the caller's thread
    });
}
```

**Second follow-up:** Does `Semaphore` support fairness the same way `ReentrantLock` does? Yes — `new Semaphore(permits, true)` gives FIFO permit grant order among blocked acquirers, with the identical barging-versus-fairness throughput trade-off as 5.1.36/5.1.37.

**Third follow-up:** Can `Semaphore.release()` be called more times than `acquire()`, growing the permit count beyond its starting value? Yes — nothing stops it, which is sometimes used deliberately to seed extra capacity at runtime, but called by accident (a double-release bug in error-handling code) it silently over-admits concurrent PSP calls past the intended bound with no exception to flag it.

---

### 5.1.44 Why must `wait()` be in a `while` loop — give both reasons

Reason one is **spurious wakeups** (5.1.46): the JLS explicitly permits `wait()` to return with no `notify`/`notifyAll` ever having been called, so the condition the thread was actually waiting for may still be false the instant it wakes — re-checking after the wake, rather than trusting it, is the only conformant approach. Reason two is **the condition being invalidated between wakeup and re-acquiring the monitor**, or equivalently, multiple waiters competing for a single true condition. When `notifyAll()` wakes several threads all parked on the bank-withdrawal queue's `notEmpty` predicate, they don't all resume atomically — each must re-acquire the monitor one at a time, serialized by the lock itself. Whichever thread runs first might drain the only queued `WithdrawalTransaction`, so by the time the second woken thread finally gets the lock and looks, the queue is empty again even though it genuinely "was notified." An `if` check would let that second thread proceed on stale information and `poll()` an empty structure (returning `null` and corrupting downstream logic that assumed a non-null transaction); `while (queue.isEmpty()) wait();` forces a fresh check immediately after re-acquiring the lock, before the queue is ever touched.

```java
synchronized (queue) {
    while (queue.isEmpty()) {
        queue.wait();
    }
    WithdrawalTransaction next = queue.poll();
    // process next — guaranteed non-null here
}
```

**Follow-up:** Does `Condition.await()` carry the same requirement? Yes, identically — the `Condition` javadoc documents the same spurious-wakeup possibility and the same re-check obligation as `Object.wait()`; the `while`-loop idiom carries over unchanged to `Condition`-based code (5.1.50).

**Pitfall:** replacing the `while` with `if` on the reasoning "I only ever call `notify()` once per item added, so there's exactly one thing to wake for." That reasoning silently drops the spurious-wakeup case entirely and breaks the instant more than one waiter is ever woken for any reason, including a later refactor to `notifyAll()`.

**Second follow-up:** Does re-checking in a `while` loop cost anything measurable versus `if`? Negligibly — it's one extra predicate evaluation per wakeup, dwarfed by the park/unpark round trip (5.1.48) that already dominates the cost of any blocking wait; there is no real performance argument for skipping it.

**Third follow-up:** Does a thread calling `wait()` release the monitor's reentrancy count in one step, or one level per call? One `wait()` call releases the monitor completely regardless of how many times the calling thread had re-entered it — the JVM records the full recursion count before releasing, then restores that exact count when the thread reacquires the monitor after being woken, so nested `synchronized` blocks resume with correct reentrancy afterward.

---

### 5.1.45 `notify` versus `notifyAll`, and when `notify` loses a signal

`notify()` wakes exactly one arbitrarily-chosen thread waiting on the monitor; `notifyAll()` wakes every waiting thread, all of which then compete to re-acquire the lock in turn and re-check their own condition — which is exactly why 5.1.44's `while` loop is mandatory regardless of which one is used. `notify()` is only safe when every thread parked on that monitor is waiting for the *same* logical condition, such that waking any arbitrary one of them is an equally correct outcome. The classic failure — a lost wakeup wearing a different hat from 5.1.47 — arises when threads waiting for **different** conditions share one monitor object instead of separate `Condition`s: imagine producers waiting for `notFull` and consumers waiting for `notEmpty`, both parked via `wait()` on the same combined lock object. If a producer calls `notify()` intending to wake a `notFull`-waiting thread, but the JVM's arbitrary choice happens to wake a thread actually blocked on `notEmpty`, that thread wakes, re-checks its own (still-false) condition, and goes right back to sleep — meanwhile the `notFull` waiter that should have been woken stays parked, potentially indefinitely if no further `notify()` call ever arrives to try again. `notifyAll()` sidesteps this specific failure because every waiter, regardless of which condition it's actually blocked on, gets a chance to re-check and only the ones whose condition now holds proceed.

**Follow-up:** When is `notify()` actually the right call? Only inside a single-condition monitor where every waiter is interchangeable, and typically chosen deliberately to avoid the "thundering herd" cost of waking every thread with `notifyAll()` when only one can usefully proceed; `Condition.signal()` gives the same precision safely because each `Condition` object's wait set holds only threads blocked on that one specific predicate.

**Pitfall:** using a single lock object with `notify()` for two logically different wait conditions on the same withdrawal queue. Fix: call `lock.newCondition()` twice to obtain distinct `notFull` and `notEmpty` `Condition` objects, each with its own precisely-targeted `signal()`.

```java
private final ReentrantLock lock = new ReentrantLock();
private final Condition notFull = lock.newCondition();
private final Condition notEmpty = lock.newCondition();
private final Deque<WithdrawalTransaction> queue = new ArrayDeque<>();
private final int capacity = 500;

void put(WithdrawalTransaction tx) throws InterruptedException {
    lock.lock();
    try {
        while (queue.size() == capacity) {
            notFull.await();
        }
        queue.addLast(tx);
        notEmpty.signal();      // precise: only a consumer waits on notEmpty
    } finally {
        lock.unlock();
    }
}
```

**Second follow-up:** Could you get the same precision with plain `Object.wait`/`notify` and two separate lock objects instead of two `Condition`s on one lock? No — splitting into two locks breaks the atomicity between checking queue size and signalling, since the producer and consumer would then be synchronizing on different monitors for what must be one consistent view of the shared queue; two `Condition`s on **one** `Lock` is what preserves both precision and atomicity together.

**Third follow-up:** What does `notifyAll()` cost that `signal()` on a precise `Condition` avoids? Every woken thread has to re-acquire the lock, re-check its predicate, and (if false) re-park — a "thundering herd" of wasted wakeups when only one of them could possibly proceed; targeting the correct `Condition` means only threads that could plausibly proceed are ever woken in the first place.

---

### 5.1.46 What is a spurious wakeup and where does it come from

A spurious wakeup is `wait()` (or `Condition.await()`) returning even though no thread ever called `notify()`, `notifyAll()`, or `signal()` — nothing in the program logic explains the wakeup, yet it happened anyway. The JLS permits this explicitly (§17.2: "waiting threads may sometimes wake up without having been notified"), and it is not treated as a JVM defect — it traces back to how monitor waits are commonly built on top of OS-level condition variables (POSIX `pthread_cond_wait`, for instance, is documented as allowed to wake spuriously), where the coupling between "a signal was delivered" and "this exact waiting thread was woken because of it" isn't perfectly guaranteed at the kernel/scheduler boundary, and closing that gap completely would cost more in every implementation than simply requiring callers to re-verify their condition on wake. This is the concrete reason the `while`-loop idiom (5.1.44) is a language-level requirement rather than defensive-programming advice — spurious wakeups are a documented, allowed possibility, and `if (condition) wait();` is non-conformant regardless of whether any particular test run happens to exercise it.

**Follow-up:** Can a test reliably reproduce a spurious wakeup on demand? Not portably — whether and when one occurs depends on the JVM's threading implementation and the underlying OS, which is exactly why "it never happened across my test suite" carries no weight as evidence of correctness here.

**Pitfall:** dismissing spurious wakeups as a JLS technicality that "basically never happens in practice, so `if` is fine." Even on platforms where the OS itself never spuriously wakes a thread, `notifyAll()` used with multiple distinct wait conditions on one monitor (5.1.45) reproduces the identical symptom through a completely different mechanism, so the `while` loop earns its keep either way.

**Second follow-up:** Is a spurious wakeup a sign of a bug in the JVM or the application? Neither — it's expected, specified behavior; the only bug is application code that fails to re-check its condition after waking, which is exactly what the mandatory `while` loop exists to prevent.

**Third follow-up:** Do virtual threads change anything about spurious wakeups? No — `wait()`/`Condition.await()` called from a virtual thread are still specified to allow spurious wakeup identically to a platform thread; virtual threads change scheduling and pinning behavior (5.1.34), not the JLS-level wait semantics.

---

### 5.1.47 What is the lost-wakeup bug and how do you prevent it

A lost wakeup happens when a thread calls `notify()`/`notifyAll()` **before** the thread that needed it has actually entered `wait()` — the notification has nowhere to land, so it simply vanishes, and the intended waiter blocks forever, rescued only by an unrelated later notification or an accidental spurious wakeup. The canonical trigger is checking the condition and calling `wait()` in a way that isn't atomic with respect to the notifier — either checking outside the lock guarding the condition, or checking under the lock but releasing it before calling `wait()`:

```java
// BROKEN — check-then-wait is not atomic with respect to the notifying thread
if (withdrawalQueue.isEmpty()) {                 // (1) observes: empty
    // <-- another thread can add an item and call notify() right here,
    //     before this thread ever reaches wait() below — that signal is lost
    synchronized (withdrawalQueue) {
        withdrawalQueue.wait();                  // (2) now waits, but the notify already fired
    }
}
```

The fix is that the condition check, the `wait()` call, and the notifier's state mutation must all occur while holding the **same** monitor, closing the window in which a notify could be sent while nobody is either already waiting or atomically about to start waiting:

```java
// consumer side
synchronized (withdrawalQueue) {
    while (withdrawalQueue.isEmpty()) {
        withdrawalQueue.wait();
    }
    WithdrawalTransaction next = withdrawalQueue.poll();
}

// producer side, symmetrically under the same monitor
synchronized (withdrawalQueue) {
    withdrawalQueue.add(transaction);
    withdrawalQueue.notifyAll();
}
```

This works because `wait()` is specified to atomically release the monitor and park the thread — there is no instant where the thread has given up the lock but is not yet actually waiting — and because both producer and consumer serialize through the same monitor, a `notifyAll()` can only ever run either strictly before a waiter checks (and it will then see the updated state and skip `wait()` entirely) or strictly after a waiter is already parked (and it will then be woken directly). There is no gap left for a signal to fall into.

**Follow-up:** Does the identical bug apply to `Condition`? Yes, unchanged in shape — `await()`/`signal()` require the same `Lock` to be held around both the condition check and the state mutation, for exactly the same atomicity reason.

**Pitfall:** moving the `wait()` call inside `synchronized` while leaving the *initial* condition check outside it, believing "the wait is protected now." The check itself must be inside the same synchronized block that contains the `wait()` call — protecting only the wait and not the check preceding it reopens the identical race.

**Second follow-up:** Is a lost wakeup the same bug as a missed signal in `CountDownLatch`? No — `CountDownLatch.countDown()` permanently decrements shared state that `await()` checks against on every call, so a `countDown()` that runs before any thread calls `await()` is never lost, it's simply already reflected in the counter; `wait()`/`notify()` have no such persistent state to consult, which is exactly why the ordering matters there and doesn't here.

**Third follow-up:** Why can't `wait()` simply check the condition itself before parking, the way a well-written caller does? `wait()` has no way to know what condition the caller cares about — it's a generic primitive operating purely on the monitor, not on application state, so the responsibility for checking the actual predicate has to live in the caller's own `while` loop; this is also why every `wait()` call site needs its own correctly-scoped condition check rather than relying on the primitive to provide one.

---

**Leaves covered:** 5.1.34–5.1.47 (14 questions)
**Leaves deferred:** none
**Diagrams included:** none
**Target version:** Java 21 LTS
**Lines:** 434
