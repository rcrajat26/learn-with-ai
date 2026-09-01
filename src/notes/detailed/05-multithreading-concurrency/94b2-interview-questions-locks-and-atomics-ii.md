# 05 Multithreading and Concurrency — Interview questions: locks and atomics II — INTERVIEW (§5.1, questions 5.1.48–5.1.60)

**Target version: Java 21 LTS.** | **Part 5 of 5** | [Index](00-index.md)
Previous: [Interview questions: locks and atomics](94b-interview-questions-locks-and-atomics.md) · Next: [Interview questions: collections and executors](94c-interview-questions-collections-and-executors.md)

---

### 5.1.48 Explain `LockSupport.park`/`unpark` and the permit

`LockSupport.park()` blocks the calling thread unless it holds a **permit**, in which case it consumes the permit and returns immediately without blocking at all. `LockSupport.unpark(thread)` gives that thread a permit if it doesn't already have one — capped at one permit per thread, not a counter (calling `unpark` twice before the target parks doesn't grant two "free passes"). This is the primitive almost every higher-level blocking construct is built on: `ReentrantLock`, `Semaphore`, and `CountDownLatch` all park waiting threads via `LockSupport` under AQS rather than using `Object.wait()`. The permit model solves the ordering problem `wait`/`notify` has (5.1.47's lost wakeup): because `unpark` can be called *before* `park`, and the permit persists until consumed, a thread that races to call `unpark` slightly early doesn't lose the signal the way a `notify()` with no waiter does — the next `park()` call simply sees the permit already there and returns instantly.

```java
// simplified sketch of how a queued AQS waiter blocks
while (!tryAcquireStakeReservationSlot()) {
    LockSupport.park(this);           // blocks unless a permit is already available
    if (Thread.interrupted()) {
        throw new InterruptedException();
    }
}
```

**Follow-up:** Does `park()` require holding a lock first, unlike `wait()`? No — `park`/`unpark` have no association with any monitor or `Lock` object at all; they operate purely on the calling/target thread, which is what lets AQS build arbitrary lock semantics on top without needing a built-in monitor.

**Follow-up (continued):** What does the `blocker` object passed to `LockSupport.park(Object blocker)` actually do? It's purely diagnostic — it's recorded so a thread dump or `jstack` can report *what* the parked thread is blocked on (visible via `LockSupport.getBlocker(thread)`), with zero effect on the actual parking/unparking semantics; omitting it (the bare no-arg `park()`) works identically but leaves less information for anyone debugging the dump later.

**Pitfall:** assuming `unpark` calls accumulate, so two `unpark()` calls followed by two `park()` calls both return immediately. They don't — the permit is binary; the second `park()` blocks normally.

**Second follow-up:** Why does `park()` sometimes return spuriously, with no `unpark()` and no permit present? The javadoc explicitly permits this too — `park()` can return "for no reason," which is why every real usage wraps it in a loop that re-checks the actual condition (`tryAcquireStakeReservationSlot()` above), exactly mirroring the `while`-loop discipline `wait()` requires (5.1.44) for the identical reason.

**Third follow-up:** Does `park()` clear interrupt status? No — if the parked thread is interrupted, `park()` returns without throwing (unlike `wait()`), and the interrupt flag remains set; the caller is responsible for checking `Thread.interrupted()` after every return from `park()`, exactly as the sketch above does.

| Operation | Blocks on | Signals via | Loses a signal if sent early? |
|---|---|---|---|
| `Object.wait()`/`notify()` | The intrinsic monitor | `notify()`/`notifyAll()` | Yes — no persisted state (5.1.47) |
| `LockSupport.park()`/`unpark()` | The target thread directly | A one-bit permit per thread | No — the permit persists until consumed |

---

### 5.1.49 What is AQS and what does `state` mean in `ReentrantLock`, `Semaphore` and `CountDownLatch`

`AbstractQueuedSynchronizer` (AQS) is the shared framework nearly every JDK blocking construct is built on: it owns a single `volatile int state` field, a FIFO wait queue of parked threads, and `acquire`/`release` template methods that subclasses customize by defining what "acquired" means for their `state` value. The framework handles the hard, easy-to-get-wrong parts — queueing, parking, `unpark`ing the right successor, handling cancellation — so each construct only has to define the meaning of the integer:

| Class | Meaning of `state` |
|---|---|
| `ReentrantLock` | 0 = unlocked; N > 0 = locked, held N times by the owning thread (reentrancy count) |
| `Semaphore` | Number of permits currently available; `acquire` decrements, `release` increments, can go negative-conceptually blocked waiters queue when it hits 0 |
| `CountDownLatch` | Count remaining until zero; starts at N, `countDown()` decrements, reaching 0 permanently releases every waiter |

The `state` field is `volatile`, so any thread's read of it sees the latest write without needing the full lock — cheap CAS attempts on `state` are the fast path (barging, 5.1.37); falling into the queue is the slow path. Java 21 runs the post-JDK-14 AQS internals: waiting nodes carry bit-flag status (`WAITING = 1`, `COND = 2`, `CANCELLED = 0x80000000`) and are represented as `ExclusiveNode` / `SharedNode` / `ConditionNode` subclasses rather than the single generic node with an integer `waitStatus` field that JDK 8-era AQS used and that most blog posts still describe.

**Follow-up:** Why is `state` a single `int` rather than something richer? Simplicity and CAS-ability — a single 32-bit CAS is cheap and universally supported; anything richer (a struct, a pair) would need a heavier synchronization primitive to update atomically, defeating the purpose.

**Follow-up (continued):** How does a fair `ReentrantLock` (5.1.36) build FIFO ordering on top of a shared `int state`? Fairness lives entirely in `tryAcquire`'s logic, not in `state` itself — the fair variant additionally checks `hasQueuedPredecessors()` (does the wait queue already have an earlier-arrived node?) before attempting the CAS, refusing to barge even when `state` is currently `0`; the non-fair variant skips that check and just CASes.

**[VERSION-TRAP]** Don't describe the JDK 8 `waitStatus` encoding (`SIGNAL`, `CANCELLED`, `CONDITION`, `PROPAGATE`, `0`) as current — post-JDK-14 AQS replaced that single encoding with the bit-flag scheme above and split node types by acquisition mode (exclusive vs. shared vs. condition).

```java
// simplified sketch of the AQS acquire template — real code lives in AbstractQueuedSynchronizer
final void acquire(int arg) {
    if (!tryAcquire(arg)) {                 // subclass-defined: e.g. CAS state 0 -> 1 for ReentrantLock
        ExclusiveNode node = addToQueue();  // CAS this thread's node onto the wait queue
        boolean interrupted = false;
        for (;;) {
            if (node.isFirstInQueue() && tryAcquire(arg)) {
                return;                     // won the retry race after being at the head
            }
            LockSupport.park(this);         // block via the primitive from 5.1.48
            if (Thread.interrupted()) {
                interrupted = true;
            }
        }
    }
}
```

**Second follow-up:** How does `Semaphore.acquire()` map onto this same template if it can grant to multiple threads at once? `Semaphore` uses AQS's *shared* acquire mode (`tryAcquireShared`/`releaseShared`) rather than the exclusive mode `ReentrantLock` uses — a successful shared acquire can propagate the wakeup to the next queued node too, which is how multiple permits release multiple waiters off one `release()` call.

**Third follow-up:** Why does `CountDownLatch` use shared mode as well, even though only one thread calls `countDown()` at a time in practice? Because *every* waiter must be released together when the count hits zero, not just one — shared mode's propagate-on-success behavior is exactly what lets a single `countDown()` reaching zero wake every blocked `await()` caller in one pass rather than one at a time.

---

### 5.1.50 How does `Condition.await` differ from `Object.wait` internally

`Object.wait()` is intrinsic to the JVM's built-in monitor — every object has one, `wait()`/`notify()`/`notifyAll()` operate on that single implicit monitor, and a thread can only ever wait on the monitor of the object whose `synchronized` block it's inside. `Condition.await()` belongs to an explicit `Lock` (typically `ReentrantLock`) and is created via `lock.newCondition()`; critically, **one `Lock` can produce multiple independent `Condition` objects**, each with its own wait set. That's the concrete win: the bank-withdrawal queue's `notFull` and `notEmpty` waiters can sit in two separate queues under one lock, so a `signal()` on `notEmpty` wakes only a consumer, never a producer waiting on `notFull` — impossible with a single object monitor, where `notify()`/`notifyAll()` reach every waiter regardless of what condition they're actually blocked on (the exact ambiguity that forces `notifyAll()` in 5.1.45's mixed-condition case).

Internally, `Condition.await()` is implemented via AQS's `ConditionObject`, which maintains its own linked list of `ConditionNode`s completely separate from the lock's main acquisition queue; `await()` atomically releases the lock (recording the current hold count so reentrant locks are restored correctly) and parks the thread on `LockSupport`, exactly mirroring `wait()`'s atomic-release-and-block guarantee but implemented in library code over AQS rather than as a JVM intrinsic.

**Follow-up:** Can you mix `synchronized`/`wait()` and `Lock`/`Condition` on the same piece of shared state? Not safely on the same object — a thread blocked in `Condition.await()` under a `Lock` is invisible to `Object.notify()` calls on that same object's monitor, and vice versa; pick one model per protected resource.

**Follow-up (continued):** Does `Condition.await()` restore the exact reentrancy hold count on reacquisition the same way `Object.wait()` does? Yes — `ConditionObject.await()` records `getHoldCount()` before fully releasing the lock and reacquires that same count once it wins the lock back, so a thread that had entered the lock three times reentrantly resumes with hold count three, not one, after the wait completes.

**Insight:** the "one lock, many conditions" idea is `Condition`'s entire reason to exist — everything else about it deliberately mirrors `Object.wait()`'s semantics (spurious wakeups included, same `while`-loop requirement).

**Second follow-up:** Does `Condition.await()` propagate `InterruptedException` the same way `Object.wait()` does? Yes by default (`await()` throws it), though `Condition` additionally offers `awaitUninterruptibly()` for the rare case where a wait genuinely must not be interrupted — `Object.wait()` has no equivalent uninterruptible variant, which is one of the small feature gaps `Condition` closes.

**Third follow-up:** What happens to a `ConditionNode` when its `Condition.signal()` fires? It's unlinked from the `ConditionObject`'s wait list and transferred onto the lock's main AQS acquisition queue — the thread doesn't resume running immediately, it just becomes eligible to compete for the lock again, exactly as if it had just called `lock()` fresh, which is why a signalled thread still has to re-acquire the lock before `await()` actually returns.

---

## Atomics and lock-free

### 5.1.51 What is CAS and what instruction implements it

Compare-And-Swap is an atomic hardware primitive: given a memory location, an expected value, and a new value, the CPU atomically checks whether the location still holds the expected value and, only if so, writes the new value — reporting success or failure as a single indivisible operation with no window where another thread could interleave between the compare and the swap. On x86, it's implemented by the `CMPXCHG` instruction with the `LOCK` prefix (`LOCK CMPXCHG`), which asserts a bus/cache-line lock for the instruction's duration so no other core's `CMPXCHG` or any memory access to that line can interleave. `java.util.concurrent.atomic` classes (`AtomicLong`, `AtomicInteger`, `AtomicReference`) expose this through `compareAndSet`/`compareAndExchange`, which the JIT compiles down to that locked instruction directly — no OS involvement, no thread parking, just a hardware-guaranteed atomic read-modify-write that either succeeds in place or reports failure so the caller can retry.

**Follow-up:** Why is CAS preferred over a lock for simple counters? Because it never blocks — a failed CAS just means "retry," which on modest contention is far cheaper than parking and being rescheduled by the OS, and it has no lock-held-forever failure mode since there's no lock to leak.

**Follow-up (continued):** Is CAS free on a single-core system, since there's no other core to race against? No — the `LOCK` prefix still costs something even on a single core, chiefly by draining the store buffer and preventing instruction reordering around it; the cost is smaller than on a multi-core system with real cache-coherence traffic, but it isn't zero.

**Interview:** "What happens under heavy contention with CAS?" It degrades to a hot retry loop — every thread's CAS keeps failing and retrying, burning CPU cycles on contention rather than parking; this is exactly the pathology `LongAdder` (5.1.56) is designed to avoid by spreading the contention across cells.

```
; conceptual x86 for a compareAndSet(expected, newValue) on a shared long
mov  rax, expected        ; RAX is the implicit compare register for CMPXCHG
mov  rcx, newValue
lock cmpxchg [address], rcx   ; atomically: if [address] == RAX, store RCX and set ZF; else load actual value into RAX
jne  retry                    ; ZF clear -> comparison failed, caller retries with the fresh RAX value
```

**Second follow-up:** Is CAS free of the ABA problem by itself? No — CAS only guarantees the *value* at the address hasn't changed since it was read; it says nothing about the history in between, which is exactly the gap ABA (5.1.54) exploits.

**Second follow-up (continued):** Does a successful CAS also act as a memory barrier? Yes — a JDK `Atomic*` CAS carries full volatile-equivalent ordering: everything the thread wrote before the CAS becomes visible to any thread that later reads the same location, matching the guarantee a `volatile` write gives, not merely an atomic-but-unordered update.

**Third follow-up:** Does the JVM ever emit `LOCK CMPXCHG` even for a single-threaded, uncontended `AtomicLong`? Yes — the JIT does not special-case "no other thread exists"; the locked instruction always executes because there is no cheap way to know at compile time whether contention is possible, which is the fixed cost every `Atomic*` operation pays regardless of actual concurrency.

| Architecture | Native CAS primitive | Shape |
|---|---|---|
| x86 / x86-64 | `LOCK CMPXCHG` | Single instruction, bus/cache-line locked, atomic in hardware |
| ARM (AArch64) | `LDXR` / `STXR` (load-exclusive / store-exclusive) | A retry-loop pair — the store fails if anything touched the address between the two instructions, so ARM's CAS is itself built from a mini compare-and-retry sequence |
| RISC-V | `LR` / `SC` (load-reserved / store-conditional) | Same load-linked/store-conditional shape as ARM |

**Fourth follow-up:** Does the JVM abstract these architecture differences away from Java code? Completely — `Unsafe`/`VarHandle` compile to whichever native primitive the target architecture provides, so `AtomicLong.compareAndSet()` behaves identically from Java regardless of whether it lowers to one `CMPXCHG` or an `LDXR`/`STXR` pair underneath.

---

### 5.1.52 Write `incrementAndGet` by hand

```java
public final class ManualCounter {
    private final AtomicLong value = new AtomicLong();

    public long incrementAndGet() {
        long current;
        long next;
        do {
            current = value.get();
            next = current + 1;
        } while (!value.compareAndSet(current, next));
        return next;
    }
}
```

The loop reads the current value, computes the desired next value, and attempts a CAS from `current` to `next`. If another thread updated `value` between the `get()` and the `compareAndSet` — say two threads are both incrementing the same `AtomicLong` tracking in-flight `FundsLedger.reserveStake` calls — the CAS fails because the actual value no longer matches `current`, the loop re-reads the (now-updated) value, and retries. This is the retry-loop pattern every real `AtomicLong.incrementAndGet()` uses internally (via `Unsafe.getAndAddLong`, which itself loops on a CAS-like primitive at the JVM intrinsic level).

**Follow-up:** Why not just `value.getAndIncrement()`? That's the exact library equivalent, implemented with the same CAS-retry shape (or, on recent JVMs, directly as `LOCK XADD` where the hardware supports fetch-and-add natively) — writing it by hand is purely to demonstrate the pattern.

**Follow-up (continued):** What's the difference between `compareAndSet` and `compareAndExchange` on `AtomicLong`? `compareAndSet` returns a `boolean` (did it succeed?); `compareAndExchange` returns the *witnessed* value — whatever was actually in memory at the moment of the attempt, whether or not the swap succeeded — which lets a retry loop skip a separate `get()` call on failure since the failed attempt already handed back the fresh value to retry with.

**Pitfall:** writing `value.set(value.get() + 1)` instead of a CAS loop — that's a classic read-modify-write race with no atomicity at all; two threads reading the same `current` both compute `current + 1` and one increment is silently lost.

**Second follow-up:** How would you extend this by-hand loop to implement `getAndAdd(delta)` generically? Change `next = current + 1` to `next = current + delta` and return `current` instead of `next` — the retry structure is identical, only the arithmetic and the returned value differ.

**Third follow-up:** Is there a cheaper hardware path than CAS-retry for pure increments? Yes on architectures with a native fetch-and-add instruction (`LOCK XADD` on x86) — the JIT can compile `AtomicLong.getAndIncrement()`/`incrementAndGet()` directly to that single locked instruction instead of a compare-and-swap loop, since no comparison against an expected value is needed for a pure add.

---

### 5.1.53 Lock-free versus wait-free versus obstruction-free

| Guarantee | What it promises | Failure mode it still allows |
|---|---|---|
| **Obstruction-free** | A thread running in isolation (no contention) completes in a bounded number of steps | Under real contention, threads can livelock — repeatedly stepping on each other and restarting forever |
| **Lock-free** | At least one thread in the system makes progress in a bounded number of steps, system-wide | An individual thread can still be starved indefinitely while others keep succeeding |
| **Wait-free** | Every thread completes its operation in a bounded number of steps, regardless of what other threads do | Strongest guarantee; rarely achieved in practice for anything beyond simple primitives, due to the complexity cost |

The CAS-retry loop in 5.1.52 is **lock-free**, not wait-free: under heavy contention a specific thread's CAS can keep failing indefinitely while other threads' CASes keep succeeding — the system as a whole always makes progress (someone's increment lands each retry round), but no individual thread is guaranteed to. `AtomicLong` on a hot counter tracking the 3,400 settlements/sec burst is exactly this: aggregate throughput stays healthy, but a particular unlucky thread could in theory be starved across many retries.

**Follow-up:** Where would you actually need wait-free guarantees? Hard real-time systems (signal handlers, certain lock-free data structures used inside a garbage collector itself) where an individual operation missing its deadline is a correctness failure, not just a fairness inconvenience — rare in typical backend Java work.

**Interview:** "Is `LongAdder` wait-free?" No — it's lock-free, same as `AtomicLong`; its win is reducing *contention* by striping across cells (5.1.56), not changing the progress guarantee class.

**Second follow-up:** Is a `synchronized`-protected counter any of these three? No — a blocking lock gives none of them; a thread that acquires the monitor and is then descheduled by the OS can hold up every other thread indefinitely, which is exactly the unbounded-delay scenario these three classes are defined to rule out to varying degrees.

**Interview (continued):** "Rank the three by how commonly you'd actually reach for each in backend Java code." Lock-free is the everyday default (`Atomic*`, `LongAdder`, `ConcurrentHashMap`'s internals); obstruction-free shows up mostly as an intermediate design step or a known-flawed early attempt rather than a shipped choice; wait-free is reserved for the rare hard-real-time or GC-internal corner most application engineers never touch directly.

**Third follow-up:** Where does a CAS-retry loop actually sit if contention is so extreme that a specific thread's CAS fails thousands of times in a row? Still lock-free by definition — the *system* is still making progress (other threads' CASes are succeeding), which is all lock-free promises; that specific thread's poor luck is a fairness problem, not a liveness violation of the lock-free guarantee.

```java
// obstruction-free but NOT lock-free: this "backs off and restarts from scratch"
// pattern makes no system-wide progress guarantee under contention
void obstructionFreeIncrement(AtomicLong counter) {
    while (true) {
        long snapshot = counter.get();
        // ... arbitrarily long computation using snapshot ...
        if (counter.compareAndSet(snapshot, snapshot + 1)) {
            return;                 // succeeds only if truly uncontended for the whole window
        }
        // no bound on retries if contention is continuous — two threads can livelock,
        // each restarting the other's long computation forever
    }
}
```

`AtomicLong.incrementAndGet()` itself avoids this livelock because its retry window is a single CAS with no arbitrary work in between — that tight retry loop is what actually earns it the *lock-free*, not merely obstruction-free, classification.

---

### 5.1.54 What is the ABA problem and when does it actually matter in Java

ABA happens when a CAS succeeds because the observed value matches the expected value, but the value actually changed and changed back in between — thread T1 reads value A, gets preempted; thread T2 changes A to B and then back to A; T1 resumes, its CAS from A to (whatever it wants) succeeds because the value *is* A again, even though the underlying state went through a meaningful transition T1 never saw. The classic case is a lock-free stack: T1 reads the head pointer (node A), gets suspended; T2 pops A, pops the next node B, then pushes A back — same pointer value, different stack contents underneath; T1's CAS on the head succeeds and corrupts the stack because it assumed nothing happened to A's `next` pointer while it wasn't looking. In Java this matters concretely in **hand-rolled lock-free structures built on `AtomicReference`** — a lock-free queue or stack implemented on raw object references is exactly where ABA bites, because the reference identity, not the object's logical value, is what CAS compares.

**Follow-up:** How do you fix ABA when it does matter? `AtomicStampedReference` or `AtomicMarkableReference` pair the reference with a version stamp (or a boolean mark) so the CAS compares both the reference *and* the stamp — a reference that went A→B→A now has a different stamp than it started with, and the CAS correctly fails.

**Follow-up (continued):** What's the practical difference between `AtomicStampedReference` and `AtomicMarkableReference`? `AtomicStampedReference` carries an arbitrary `int` version stamp you increment yourself on every logical mutation; `AtomicMarkableReference` carries a single `boolean` mark instead — cheaper when the only thing you need to detect is "has this been touched at all" rather than "how many times."

**Pitfall:** treating ABA as a live concern for everyday code using `AtomicLong`/`AtomicInteger` counters. Numeric counters don't have the "reference identity implies unchanged structure" assumption that makes ABA dangerous — a counter going from 5 to 6 and back to 5 genuinely means "back to the same logical state," which is the correct outcome, not a bug.

```java
// A lock-free stack of pending WithdrawalTransactions — the classic ABA-vulnerable shape
final AtomicReference<Node> head = new AtomicReference<>();

record Node(WithdrawalTransaction tx, Node next) {}

void push(WithdrawalTransaction tx) {
    Node newHead;
    Node oldHead;
    do {
        oldHead = head.get();
        newHead = new Node(tx, oldHead);
    } while (!head.compareAndSet(oldHead, newHead));
}

WithdrawalTransaction pop() {
    Node oldHead;
    Node newHead;
    do {
        oldHead = head.get();
        if (oldHead == null) return null;
        newHead = oldHead.next();          // ABA risk: another thread could pop+push node A back here
    } while (!head.compareAndSet(oldHead, newHead));
    return oldHead.tx();
}
```

If, between reading `oldHead` and the CAS in `pop()`, another thread pops node A, pops the node after it, and then pushes a brand-new node that happens to be object A again (only possible if A were somehow reused — Java's GC actually rules this out per 5.1.55, but the *logical* variant survives if A's `next` field were mutable and got mutated back), the CAS would succeed against a `next` pointer that no longer means what it meant when read.

**Second follow-up:** Would making `Node.next` `final`, as above, eliminate the ABA risk entirely for this stack? Largely yes for this exact shape — because `Node` is immutable, "the same node A" really does mean "the same `next` value," so the residual logical-mutation ABA case from 5.1.54/5.1.55 doesn't apply here; the risk resurfaces only if a mutable node type is substituted in.

---

### 5.1.55 Why does Java's GC make most ABA problems disappear

ABA is dangerous specifically when a reclaimed/reused memory address gets reassigned to a *different* logical object that happens to occupy the same memory location — the classic C/C++ ABA scenario is "this pointer got freed and a new allocation landed at the same address," so the pointer-equality check ("is it still A?") is fooled by address reuse alone, with no relationship between the two objects sharing that address. Java's garbage collector never lets that happen: as long as any live reference to an object exists, the GC will not reclaim it or reuse its address for something else, and object identity (what `==` and `AtomicReference.compareAndSet` actually compare, since Java references aren't raw pointers a program can reinterpret) is tied to the object, not a raw memory address a new object could later occupy. So a CAS from "reference to node A" back to "a different reference that happens to alias A's old address" simply can't happen in Java — if a `CAS` on an `AtomicReference<Node>` sees the value is still node A, it genuinely is the same logical object A that existed the whole time, still reachable, never recycled. The residual ABA risk in Java is purely **logical** — A's *fields* mutated and were mutated back (the stack example in 5.1.54, where A the node object never moved but its `next` pointer changed and changed back) — not address-reuse ABA, which the managed heap eliminates by construction.

**Follow-up:** So is `AtomicStampedReference` ever actually needed in Java, given this? Yes, for the logical-mutation variant — a mutable node's internal state changing and reverting is still a real risk with plain `AtomicReference`; the stamp guards against that, not against address reuse.

**Insight:** this is one of the cleanest examples of "managed memory changes which classic concurrency bugs are even reachable" — a C++ concurrency answer about ABA and a Java one are answering genuinely different threat models.

**Second follow-up:** Does this mean Java's lock-free algorithms can be simpler than their C++ equivalents? Often yes for exactly this reason — algorithms that in C++ need hazard pointers or epoch-based reclamation purely to guard against address-reuse ABA can, in Java, skip that machinery entirely and only need to worry about the narrower logical-mutation case, if their nodes are immutable at all.

**Third follow-up:** Does this argument extend to `Unsafe`-based off-heap memory access in Java? No — off-heap memory (a `ByteBuffer.allocateDirect`, a raw `MemorySegment`) is not managed by the GC, so address-reuse ABA is a live concern there exactly as in C++; the "GC makes ABA disappear" argument is specific to ordinary on-heap object references.

---

### 5.1.56 `AtomicLong` versus `LongAdder` — how does `LongAdder` work and when does it lose

`AtomicLong` keeps a single `volatile long` and every `incrementAndGet()` CAS-races against every other thread on that one memory location — under the 3,400 settlements/sec burst with many threads all bumping the same counter, cache-line contention on that single field turns into a hot spot: every core's cache invalidates every other's on each successful CAS (a form of false sharing at the field level, not just the padding sense). `LongAdder` fixes this by striping: it holds a base value plus a resizable array of `Cell`s (each padded to occupy its own cache line, avoiding false sharing between cells), and `add()`/`increment()` picks a cell based on a thread-local hash, CASes on that cell instead of a shared field, and only falls back to CASing the shared `base` when there's no contention (or the `Cell` array hasn't been created yet). Under contention the JVM grows the cell array so more threads spread across more cells, sharply cutting the CAS-failure rate any single thread experiences. `LongAdder` **loses** to `AtomicLong` when you need the value read frequently *during* concurrent updates and need it to be a single, immediately consistent value for CAS-based coordination — `LongAdder` has no `compareAndSet`, and `sum()` is a snapshot that can be stale the instant after it's read (5.1.57); `AtomicLong` also wins when write concurrency is low, since `LongAdder`'s extra cell-array indirection is pure overhead with nothing to spread out.

**Follow-up:** Does `LongAdder` support decrement? Yes — `decrement()`/`add(-n)` work identically; the striping applies in both directions since a `Cell` just accumulates a signed delta.

**Follow-up (continued):** How does a thread get assigned to a particular `Cell`? Through a per-thread probe hash (`Thread.getThreadLocalRandomProbe()`, refreshed on collision), not the thread's identity or id directly — two threads whose probes happen to hash to the same cell index will still contend on that cell until the array grows or a rehash separates them.

**Interview:** "When would you pick `AtomicLong` over `LongAdder` for a hot counter?" When you need the current value to make an atomic decision (a CAS-based limit check, "only proceed if count < maxConcurrent"), not just to observe an eventually-accurate total — `LongAdder` gives you the latter, not the former.

```java
// settlement counter under the 3,400/sec burst — LongAdder is the right shape:
// many concurrent writers, occasional approximate reads for a dashboard
private final LongAdder settlementsProcessed = new LongAdder();

void onSettlement(FundsLedger.Settlement s) {
    applySettlement(s);
    settlementsProcessed.increment();       // CASes a striped Cell, not one shared field
}

long currentThroughputSnapshot() {
    return settlementsProcessed.sum();      // approximate, fine for a dashboard (5.1.57)
}
```

**Second follow-up:** Does `LongAdder` allocate its `Cell` array eagerly at construction? No — it starts with just the `base` field and only allocates the `Cell` array lazily, on the first observed CAS failure on `base`, growing it further only if contention persists after that — so a `LongAdder` under no contention costs essentially the same as an `AtomicLong`.

**Third follow-up:** Is `LongAccumulator` just a generalized `LongAdder`? Yes — `LongAccumulator` takes an arbitrary associative `LongBinaryOperator` instead of being hardwired to addition, using the identical striped-cell mechanism; `LongAdder` is effectively `LongAccumulator` specialized to `(x, y) -> x + y` with a zero identity, exposed under a simpler API for the common case.

---

### 5.1.57 Why is `LongAdder.sum()` not atomic

`sum()` computes its result by iterating the `base` value plus every currently-allocated `Cell` in the array and summing them in a plain loop — it is **not** a single atomic read of one location, because there is no single location; the total is spread across potentially many `Cell`s that different threads can be concurrently CASing at the moment `sum()` runs. So `sum()` returns a value that is consistent only if no other thread updates any cell during the iteration; in practice, under continuous contention (`FundsLedger` settlements arriving throughout), `sum()` is a best-effort snapshot that may not reflect any single instant in time — it can, in principle, be lower than the true count at the *start* of the call and higher than the true count at the *end*, if updates land on cells already-summed versus not-yet-summed during the traversal. This is an explicit, documented trade-off: `LongAdder`'s javadoc calls `sum()` accurate "in the absence of concurrent updates" and merely a reasonable approximation otherwise — the class optimizes for update throughput, not for read consistency, which is the opposite trade-off from `AtomicLong`.

**Follow-up:** Is this a problem for a dashboard reading settlement throughput? Generally no — a monitoring read of an approximate, slightly-stale aggregate is exactly the use case `LongAdder` is built for; it becomes a problem only if code tries to use `sum()` as an input to a correctness decision (a limit check), which is precisely what `AtomicLong`/CAS should be used for instead.

**Follow-up (continued):** Could a new `Cell` being allocated mid-`sum()` cause it to be missed or double-counted? It cannot be double-counted (a `Cell` only ever gets summed once, at whatever value it holds at the moment `sum()` reaches it), but a `Cell` created after `sum()` has already passed that array slot is simply not seen this call — consistent with `sum()`'s documented "no concurrent updates" caveat rather than a distinct bug.

**Pitfall:** calling `sum()` in a loop expecting monotonically increasing values as a correctness invariant during heavy concurrent writes and asserting on it in a test — the class doesn't promise that, and a flaky assertion here is a test bug, not a `LongAdder` bug.

**Second follow-up:** Does `LongAdder` offer any way to get a truly consistent total? `reset()` combined with `sumThenReset()` at least gives an atomic-per-cell reset sequence useful for periodic reporting windows, but it still doesn't freeze all concurrent writers during the read — for a genuinely consistent snapshot you would need external coordination (a `StampedLock` or quiescing writers), which defeats the point of using `LongAdder` in the first place.

**Third follow-up:** Why doesn't `LongAdder` just synchronize `sum()` to make it exact? Because doing so would force every concurrent updater to serialize behind the sum computation at least momentarily, reintroducing the exact contention striping was built to remove — the class's entire value proposition is trading read-exactness for write-throughput, and synchronizing `sum()` gives that trade back for free.

---

### 5.1.58 What is false sharing and how does `LongAdder` avoid it

False sharing happens when two or more independent variables that different threads modify concurrently happen to live on the **same CPU cache line** (typically 64 bytes) — even though the variables have nothing logically to do with each other, every write to one invalidates the entire cache line in every other core's cache, forcing a re-fetch from a shared cache level or memory, which shows up as contention-like slowdown even though there's no actual data race or shared state. If `LongAdder`'s `Cell` objects were laid out adjacently in memory with no padding, two threads updating *different* cells (which is the whole point of striping — to avoid contention) would still ping-pong the same cache line back and forth, silently reintroducing the exact contention the striping was meant to eliminate. `LongAdder`'s `Cell` class is annotated `@sun.misc.Contended` (or padded manually with unused long fields in versions before that annotation), which forces each `Cell` onto its own cache line by inserting padding bytes around it — the JVM (with `-XX:-RestrictContended` off by default for internal JDK classes) honors this and spaces the cells out in memory so concurrent updates to different cells never invalidate each other's cache lines.

**Follow-up:** Does this padding cost memory? Yes — each padded `Cell` consumes a full cache line (64 bytes) rather than the 8 bytes a bare `long` needs, which is a deliberate trade of memory for throughput; with a modest array of cells this is negligible in absolute terms.

**Follow-up (continued):** Is false sharing only a problem for atomics and counters? No — any two independent, frequently-and-concurrently-written fields on adjacent memory can suffer it, including two unrelated instance fields on the same object that happen to be laid out close together by the JVM; the fix generalizes beyond `LongAdder` to any hot, contended field pair.

**Insight:** false sharing is invisible in code review — nothing about `Cell field1; Cell field2;` looks wrong — which is exactly why it's a favorite "what's actually happening at the hardware level" interview probe.

```java
// illustrating manual cache-line padding, the pre-@Contended technique LongAdder's
// predecessor classes used before the annotation existed
static final class PaddedCounter {
    volatile long value;
    // 7 unused longs = 56 bytes of padding; with the 8-byte value field, fills a 64-byte line
    long p1, p2, p3, p4, p5, p6, p7;
}
```

**Second follow-up:** Would using an array of plain `long`s indexed by thread instead of an array of padded `Cell` objects avoid false sharing on its own? No — adjacent array elements are exactly the classic false-sharing case (a `long[]` packs 8 values per 64-byte cache line with zero gaps), which is precisely why `LongAdder` uses discrete padded objects rather than a dense primitive array for its striping.

**Third follow-up:** Is `@Contended` usable in ordinary application code the same way `LongAdder` uses it internally? Not without a JVM flag — `@Contended` (in `jdk.internal.vm.annotation`) is restricted to JDK-internal classes by default; application code needs `-XX:-RestrictContended` to have the annotation honored outside the JDK's own module, which is rarely worth doing compared to manual field padding for the rare case an application genuinely needs it.

---

### 5.1.59 What is a `VarHandle` and what are its four ordering modes

`VarHandle` (JEP 193, finalized in Java 9) is a typed, reflection-like handle to a variable — a field, an array element, or an off-heap location — that exposes a family of access modes with precisely specified memory-ordering semantics, replacing the old pattern of reaching for `sun.misc.Unsafe` directly. It gives fine control between the two extremes of "plain field access" and "fully synchronized," letting code pick exactly the ordering strength it needs and pay only for that:

| Mode | Ordering guarantee | Roughly equivalent to |
|---|---|---|
| **Plain** | No ordering guarantee at all beyond normal Java semantics | A bare, non-volatile field read/write |
| **Opaque** | Guarantees the access itself won't be reordered with respect to *other accesses to the same variable*, but no happens-before ordering with other variables | Weaker than volatile — useful for statistics counters where only per-variable coherence matters |
| **Release/Acquire** | A release write establishes happens-before with a subsequent acquire read of the same variable — one-directional barriers, cheaper than full volatile | `setRelease`/`getAcquire` — half of a `volatile`'s guarantee, in the direction actually needed |
| **Volatile** | Full happens-before in both directions, sequential consistency with respect to other volatiles | Identical to a `volatile` field |

`VarHandle.compareAndSet`, `getAndAdd`, `getAndSet` and friends are also exposed with these same ordering variants, giving CAS operations the same fine-grained control.

**Follow-up:** Why would you choose Opaque or Release/Acquire instead of just using `volatile`? Cost — full volatile ordering requires a memory fence on every access, which is more expensive than the CPU strictly needs when only a weaker guarantee (like "this specific write becomes visible to a specific later read," not "all writes are globally ordered") is actually required; `VarHandle` lets you ask for exactly that and no more.

**Follow-up (continued):** Does choosing Plain mode through a `VarHandle` behave any differently from just declaring the field non-volatile and accessing it directly? No — Plain mode is deliberately the weakest tier, equivalent to ordinary field access with no ordering guarantee beyond normal Java semantics; it exists in the API mainly so code that already holds a `VarHandle` for other access modes can also express "no ordering needed here" without switching back to a raw field reference.

**Interview:** "How does `VarHandle` relate to `AtomicLong`?" Since Java 9, most `Atomic*` classes are implemented internally using `VarHandle` rather than raw `Unsafe` calls — `VarHandle` is the general-purpose mechanism; `AtomicLong` etc. are convenience wrappers around one specific use of it.

```java
private static final VarHandle SETTLED_COUNT;
static {
    try {
        SETTLED_COUNT = MethodHandles.lookup()
            .findVarHandle(SettlementStats.class, "settledCount", long.class);
    } catch (ReflectiveOperationException e) {
        throw new ExceptionInInitializerError(e);
    }
}

private long settledCount;   // deliberately not volatile — VarHandle chooses the mode per access

void recordSettlementOpaque() {
    long current = (long) SETTLED_COUNT.getOpaque(this);
    SETTLED_COUNT.setOpaque(this, current + 1);   // per-variable coherence only, cheaper than volatile
}
```

**Second follow-up:** Can `VarHandle` target `private` fields on an arbitrary class the way reflection can? Only through a `MethodHandles.Lookup` obtained with sufficient access — typically `MethodHandles.lookup()` called from within the declaring class itself; `VarHandle` deliberately does not offer the same broad `setAccessible(true)`-style bypass reflection allows, keeping access control intact.

---

### 5.1.60 When would you use `setRelease` instead of a volatile write

`setRelease` is appropriate when you need one-directional ordering — "everything I wrote before this point must be visible to any thread that later does an acquire-read of this same variable and sees my value" — but you don't need the full bidirectional, globally-sequentially-consistent guarantee a `volatile` write provides, and you want to avoid paying for the stronger (and more expensive) full fence a plain volatile store issues on most architectures. A concrete shape: a worker thread finishes populating an immutable `LimitSet` snapshot, then wants to publish the reference so other threads (reading via `getAcquire`) see a fully-constructed object — that's a classic safe-publication pattern, and `setRelease`/`getAcquire` gives exactly the happens-before edge needed for safe publication without paying for `volatile`'s additional guarantee that this write is also ordered with respect to *every other* volatile variable in the program, which the publish scenario doesn't need.

```java
private static final VarHandle LIMITS_HANDLE;
static {
    try {
        LIMITS_HANDLE = MethodHandles.lookup()
            .findVarHandle(LimitCache.class, "limits", LimitSet.class);
    } catch (ReflectiveOperationException e) {
        throw new ExceptionInInitializerError(e);
    }
}

private volatile LimitSet limits;   // field declared volatile only for the safe-publication baseline

void publish(LimitSet updated) {
    LIMITS_HANDLE.setRelease(this, updated);   // release: prior writes to `updated`'s fields are visible after this
}

LimitSet read() {
    return (LimitSet) LIMITS_HANDLE.getAcquire(this); // acquire: pairs with the release above
}
```

**Follow-up:** Is this a premature optimization for most application code? Usually yes — the cost difference between `setRelease`/`getAcquire` and plain `volatile` is measured in nanoseconds per access and only matters on extremely hot paths (a counter or flag touched millions of times per second); for ordinary `FundsLedger`-adjacent code, plain `volatile` is the right default and `VarHandle` ordering tuning is reached for only after profiling shows the fence cost matters.

**Pitfall:** using `setRelease` where two-way ordering is actually required (for example, a flag that must be checked by a thread that then writes something else expecting sequential consistency with a third thread). Release/acquire is a one-directional handshake between exactly the writer and the reader of that one variable — it does not give the same total-order guarantee across multiple volatile variables that full volatile semantics do.

**Second follow-up:** How does `setRelease` differ from `setOpaque` in what it guarantees? `setOpaque` only guarantees ordering relative to *other accesses to that same variable* — it says nothing about visibility of the writer's *other* field writes; `setRelease` additionally guarantees that everything the writer did *before* the release write (any fields of `updated`, for instance) becomes visible to whatever thread later does the matching `getAcquire`, which is exactly the safe-publication property the `LimitSet` example needs and `setOpaque` alone would not provide.

**Third follow-up:** Would a plain, non-`VarHandle` `volatile` field have been functionally wrong for the `LimitSet` publish example, or just slower? Just slower — correctness-wise a `volatile` write/read pair gives a strictly stronger guarantee than release/acquire, so it would work; the `VarHandle` version is reached for only once profiling shows the extra fence cost matters on that specific hot path.

---

**Leaves covered:** 5.1.48–5.1.60 (13 questions)
**Leaves deferred:** none
**Diagrams included:** none
**Target version:** Java 21 LTS
**Lines:** 420
