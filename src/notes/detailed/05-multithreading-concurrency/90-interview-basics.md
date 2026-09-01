# 05 Multithreading and Concurrency — Part 1 interview wrap-up — BASICS (§1.1–§1.26)

**Target version: Java 21 LTS.** | **Part 1 of 5** | [Index](00-index.md)
Previous: [Liveness failures](liveness/01-basics-failures.md) · Next: [The master tables](master-tables/01-the-master-tables.md)

## Part 1 summary table

Eighteen subject folders, §1.1 through §1.26. Every row states the same four things an interviewer is actually probing for: what the guarantee buys you, what it costs, what wins when it loses, and the one fact most likely to come back as a follow-up.

Three of the eighteen rows carry a live version trap worth re-checking before an interview: `synchronized` pins a virtual-thread carrier on Java 21 until JEP 491 lands in 24; explicit locks are the version-scoped workaround for exactly that; and structured concurrency is still a moving preview API (JEP 505 → 525 → 533), so its exact surface should not be quoted as final.

Read the "chosen against" column as a decision tree, not a list of trivia: every row names exactly one sibling, and in a real interview the reason a candidate reaches for `ReentrantLock` over `synchronized`, or `LongAdder` over `AtomicLong`, or `ConcurrentSkipListMap` over `ConcurrentHashMap`, is almost always the actual question being asked, phrased as "why did you pick X here."

The "cost" column is worth a second pass on its own, because it is the column most candidates skip when they've only memorized the guarantee: every one of these eighteen tools buys something at a price, whether that price is carrier pinning, manual `unlock()` discipline, retry storms under contention, or simply the reasoning overhead of one more moving part in the system — and naming the price unprompted is usually what separates a Senior IC answer from a Staff one on the exact same question.

| Subject | Guarantee it provides | Cost | Chosen against | Single most-asked fact |
|---|---|---|---|---|
| Foundations (why concurrency costs, OS substrate) | None by itself — explains why a context switch and a cache miss are expensive before any API is introduced | Order-of-magnitude context-switch cost, dominated by cache/TLB reload, not register save | Single-threaded / process-based concurrency | A context switch is order-of-magnitude microseconds — the cost is cold caches on the new thread, not the save/restore itself |
| `Thread` API, lifecycle/states, interruption | Cooperative signalling only — `interrupt()` requests, it never forces | An OS thread reserves ~1 MB of stack whether or not it is ever unblocked | Virtual threads (§1.22) once the workload is I/O-bound | `interrupt()` only sets a flag and wakes blocking calls; nothing forcibly stops a running thread — `Thread.stop()` was removed in Java 20 |
| Thread-safety vocabulary, races, compound actions | None — the vocabulary names the failure, it does not fix it | Reasoning cost: every shared mutable field is a candidate race until proven otherwise | Immutability / confinement, which sidestep the vocabulary entirely | `count++` on a shared field is three unsynchronized steps (read, add, write) — a check-then-act or read-modify-write race, not a single op |
| `synchronized` | Mutual exclusion plus a happens-before edge from unlock to the next lock on the same monitor | Pins a platform carrier thread under a virtual thread in Java 21 (JEP 491 lifts this in 24) | `ReentrantLock` when you need `tryLock`, timeouts, or virtual-thread-friendly blocking | Monitor unlock is unconditional on exit, even via exception — it is JVM-managed, not code you can forget to write |
| `volatile` | Visibility plus ordering (no reordering across the access) — never atomicity | No caching in a register; every read/write crosses a memory barrier | `AtomicLong`/`synchronized` the moment the operation is compound (read-modify-write) | `volatile` does not "flush to main memory" — MESI already keeps caches coherent; it establishes happens-before ordering, not a cache flush |
| Java Memory Model, happens-before | Defines exactly which reorderings are legal and what happens-before actually buys the reader | Reasoning complexity — correctness is proven against happens-before, never against program-order intuition | Nothing — it is the umbrella every other row is checked against | Two actions with no happens-before edge can be legally reordered even on a single core, regardless of program order |
| `final` fields, safe publication | A correctly-constructed `final` field is visible without synchronization to any thread that later sees the reference | Broken instantly if `this` escapes during the constructor (listener registration, starting a thread from the constructor) | `volatile` publication when the field must still change after construction | `final` alone does not publish the *reference* safely — the reference itself needs a safe-publication path (a `final` field, `volatile`, or a lock) |
| `wait`/`notify` | Coordination only — no guarantee by itself; requires holding the object's monitor | Spurious wakeups, and `notify()` can wake the wrong waiter and lose the signal | `java.util.concurrent.locks.Condition`, which gives multiple wait-sets per lock | `wait()` must sit in a `while` loop re-checking the predicate, never in an `if`, because of spurious wakeup |
| Atomics, CAS | Lock-free atomicity on a single variable via a hardware compare-and-swap | Under contention, CAS retries pile up — `AtomicLong` degrades toward the same ceiling as a lock | `LongAdder` once the counter is write-heavy and hot (the 3,400/sec settlement burst) | CAS is compare-and-swap on one word; `LongAdder` beats `AtomicLong` under contention by striping the counter across cells, not by avoiding CAS |
| Explicit locks (`ReentrantLock`, `ReadWriteLock`) | Same mutual exclusion as `synchronized`, plus `tryLock`, timed lock, interruptible acquire, fairness, multiple conditions | Manual `unlock()` in `finally` — the JVM will not do it for you | `synchronized` when none of the extra capability is needed and pinning is not a concern | `ReentrantLock` does not pin a virtual thread the way `synchronized` does in Java 21 — the version-scoped reason it is recommended for virtual-thread code |
| Synchronizers (`CountDownLatch`, `Semaphore`, `CyclicBarrier`, `Phaser`) | Each gives a distinct, named coordination shape, all built on AQS | Picking the wrong one reinvents what an existing one already does correctly | Each other — the choice is a comparison, not a single answer | `CountDownLatch` is single-use and cannot reset; `CyclicBarrier` resets automatically and is reusable across rounds |
| Concurrent collections, `BlockingQueue` | Thread-safe single operations — never a compound sequence across two calls | `ConcurrentHashMap` has no cross-bucket atomicity; `CopyOnWriteArrayList` writes copy the whole backing array | `Collections.synchronizedList` when you need compound-operation locking via `synchronized(list)` | `CopyOnWriteArrayList` under 2.8M appends/day is a throughput disaster — it is a read-mostly structure, not a general list |
| Executor framework, `ThreadPoolExecutor`, scheduled executors | Decouples task submission from thread lifecycle; bounds concurrent resource use | A misconfigured queue-plus-pool combination silently unbounds memory or starts rejecting | Raw `new Thread(...)` per task, or a virtual-thread-per-task executor for I/O-bound work | `ThreadPoolExecutor` only grows past `corePoolSize` once the queue is *full* — with an unbounded queue, `maximumPoolSize` is dead configuration |
| `CompletableFuture`, fork/join | Documented async composition with a fixed default threading model (`ForkJoinPool.commonPool()`) | The common pool starves the moment a stage blocks on I/O; work-stealing adds overhead for tiny tasks | A dedicated bounded executor passed explicitly to every `*Async` call | `thenApply` runs on the completing thread (or the caller, if already complete); `thenApplyAsync` explicitly hops to an executor — the most common `CompletableFuture` trap |
| `ThreadLocal` | Per-thread variable copies with zero synchronization | Leaks in pooled-thread environments — the thread outlives the logical task and keeps the stale value | Passing context explicitly, or a scoped value once finalized (JEP 506, Java 25) | `ThreadLocal` plus a thread pool is a classic leak: the *thread*, not the task, owns the slot — always `remove()` in a `finally` |
| Virtual threads | Cheap, KB-scale, OS-thread-independent unit of concurrency for blocking-style code | `synchronized` pins the carrier in Java 21; native-frame calls pin too | Platform threads for CPU-bound work; reactive style when pinning cannot be tolerated at all | Handling 55k peak concurrent sessions as blocking virtual threads costs kilobytes per thread instead of megabytes — that ratio is the entire pitch |
| Structured concurrency | A task's child threads share the parent's lifetime — no orphaned subtask ever outlives its scope | Still preview (JEP 505 → 525 → 533) — the API surface has moved release to release | Manually wired `CompletableFuture` fan-out/fan-in, which gives no scope-level cancellation for free | `StructuredTaskScope` ties cancellation and error propagation to the enclosing scope — one failed subtask can short-circuit its siblings automatically |
| Liveness failures (deadlock, livelock, starvation) | None — these are what happens when the guarantees above are used incorrectly | Full hangs or throughput collapse, diagnosed after the fact via `jstack`/JFR | Disciplined lock ordering, or `tryLock` with a timeout, as the structural fix | Deadlock needs all four Coffman conditions at once; breaking any single one — usually circular wait, via lock ordering — prevents it |

## Interview questions

Ten questions spanning foundations through liveness. Every model answer is written at speaking length — what a candidate actually says out loud in 45 to 60 seconds — followed by the follow-up the interviewer asks next and a one-line answer to it.

Each answer also carries a **Pitfall**, naming the specific wrong belief that produces the bug in practice, and an **Insight**, the mechanism-level detail that separates "knows the rule" from "knows why the rule is true." Reading only the bolded lines top to bottom is a legitimate fast pass the night before an interview; reading the full paragraphs is the version that survives a real follow-up question.

Every QuizStakes number quoted below — 1,200/sec, 240 ms, 3,400/sec, 55k, and the rest — is taken verbatim from the shared domain figures in Part 1's earlier files, never invented for the sake of a rounder-sounding sentence, so cross-referencing an answer against an earlier day's arithmetic will always agree with what's stated here.

**Q1. How do you stop a running thread safely in Java, and why doesn't `Thread.stop()` exist as an option anymore?**

I'd say interruption is cooperative, not a kill switch — calling `interrupt()` just sets a flag on the target thread and, if that thread is currently blocked in something like `sleep`, `wait`, or a blocking queue call, it throws `InterruptedException` and clears the flag on the way out. The thread itself has to check `Thread.currentThread().isInterrupted()` in its loop, or let the checked exception propagate outward, and actually decide to exit — nothing forces it to. That's the whole point of leaving it cooperative: a worker draining `WithdrawalTransaction`s from a `BlockingQueue` toward a `PaymentRun` gets to finish the transaction it currently holds, or roll it back cleanly, instead of being torn out of the middle of a write to `FundsLedger`.

`Thread.stop()` used to be the forcible version, and it's worth being specific about why it was dangerous rather than just calling it "unsafe": it could release a monitor while an invariant was half-updated — for example after debiting `CASH_AVAILABLE` but before crediting `CASH_RESERVED` on the other side of a stake reservation — leaving the wallet in a state no code path was ever designed to see. That's why it was deprecated for decades before being formally removed as of Java 20, where calling it today throws `UnsupportedOperationException` rather than merely a compiler warning.

**Insight:** interruption only does something to a thread that is already checking for it, either explicitly or by sitting inside a JDK method documented to be interruptible — a thread spinning in a tight CPU loop with no such check is, from the interrupter's point of view, unstoppable.

**Pitfall:** the wrong belief is that catching `InterruptedException` and silently swallowing it is harmless because "the loop will just try again." The symptom is a thread that never actually shuts down under load, because the interrupt status was consumed by the `catch` block and never re-set — the fix is either to let the exception propagate, or to call `Thread.currentThread().interrupt()` inside the `catch` before continuing, so the status survives for the next check.

**Interview:** this is usually framed as "what's wrong with this code" over a snippet that swallows `InterruptedException` in an empty `catch` block — the one-line answer is that it silently discards the interrupt status, so a caller checking `isInterrupted()` afterward gets `false` and thinks nothing happened.

**Follow-up — what happens if the loop body is a long CPU-bound computation with no blocking call inside it, say scoring 40k peak daily applications for affordability?** You have to poll `Thread.currentThread().isInterrupted()` yourself at regular points inside the computation and exit early on `true`, because interruption gives a CPU-bound loop no help at all — nothing throws for you the way `sleep` or a queue `take()` would.

**Q2. Walk me through why `synchronized` on a method updating a client's cash balance is safe, and what it costs you if that method runs inside a virtual thread on Java 21.**

`synchronized` gives you two things at once, and interviewers are listening for whether you name both: mutual exclusion, so only one thread can be inside `FundsLedger.reserveStake` for a given lock at a time, and a happens-before edge — everything the previous thread wrote before releasing the monitor is guaranteed visible to the next thread that acquires it. That second part is the one people forget; they describe `synchronized` as "just a mutex" and miss that it's also what makes the reserved-cash write visible to the next stake reservation on the same wallet at all. Without the happens-before edge, mutual exclusion alone would stop two threads corrupting the number simultaneously, but it wouldn't stop the next thread — running strictly after, on a different core — from reading a stale cached value.

The cost on Java 21 specifically is pinning: if a virtual thread blocks inside a `synchronized` block, it pins its carrier platform thread instead of unmounting back to the scheduler the way it would if it blocked on `ReentrantLock` or I/O. A burst of contended `synchronized` calls at the 1,200/sec stake-reservation peak, run under virtual threads, can exhaust the carrier pool even though the whole point of virtual threads was to let thousands of them share a handful of carriers — the exact scenario JEP 491 was written to fix by removing pinning as a `synchronized` side effect in Java 24.

**Insight:** the pinning problem only bites when a virtual thread *blocks* inside `synchronized` — brief, uncontended critical sections that never actually wait for the monitor don't pin anything, which is why this only shows up under real contention, not in a smoke test.

**Pitfall:** the wrong belief is that switching every `synchronized` block to `ReentrantLock` is always the right move on Java 21. The symptom of over-applying that fix is losing the JVM's automatic unlock-on-exception and paying manual `try/finally` discipline everywhere, for code paths that never actually run under virtual threads or never block long enough to matter — the fix is to reserve the swap for hot paths that genuinely run under virtual threads and can genuinely block, like a call gated behind PSP latency.

**Interview:** this is usually asked as "does `ReentrantLock` replace `synchronized` everywhere now" — the one-line answer is no, only where pinning under virtual threads is a real risk; platform-thread code with brief critical sections has no reason to give up `synchronized`'s automatic unlock guarantee.

**Follow-up — what would you do differently if this code is going to run under virtual threads on Java 21 today?** Swap `synchronized` for `ReentrantLock` around that hot path, since `ReentrantLock` gives the same mutual exclusion and happens-before guarantee without pinning the carrier when a virtual thread blocks on it.

**Q3. What exactly does `volatile` guarantee on a flag like a "stake reservations paused" switch, and what does it not give you?**

`volatile` guarantees visibility and ordering — a write from one thread becomes visible to any thread that subsequently reads that same field, and the compiler and CPU won't reorder other accesses across it. What it does not give you is atomicity for anything compound: if the field were a counter tracking paused reservations and two threads did `counter++`, `volatile` wouldn't stop the lost update, because that's a read-modify-write across three steps, not a single atomic read or write.

I'd also correct the common phrasing up front, because it's the mistake I've seen carried the furthest into people's careers: `volatile` doesn't "flush to main memory," because the caches are already kept coherent by a protocol like MESI on any hardware Java targets today. What `volatile` actually does is insert store and load barriers around the access that establish happens-before ordering between the write and the read — a completely different mechanism from cache invalidation, and one that matters because it also constrains *reordering* of surrounding code, not just eventual visibility.

**Insight:** the "flush to main memory" story predicts that `volatile` should be about *when* a value becomes visible; the happens-before story correctly predicts that `volatile` is also about ordering everything else around it — which is the detail that actually explains double-checked locking needing a `volatile` reference.

**Pitfall:** the wrong belief is "I made it `volatile`, so it's thread-safe now" applied to any field, regardless of whether the operation on it is a single read/write or a compound sequence. The symptom is a lost-update bug on a field everyone insists "can't possibly be racy — look, it's `volatile`" — the fix is to check whether the operation is genuinely a single access; if it's compound, reach for `synchronized`, a lock, or an atomic instead.

**Interview:** this is usually framed as "is `volatile` enough here" over a snippet doing `volatile int` compound arithmetic — the one-line answer is no, `volatile` only ever fixes visibility and ordering, never atomicity of anything beyond a single read or a single write.

**Follow-up — so when would plain `volatile` still be wrong, even on a boolean like `paused`?** Check-then-act — `if (!paused) { paused = true; startDraining(); }` is still racy even with `volatile`, because the check and the act are two separate accesses and two threads can both pass the check before either writes.

**Q4. Two threads each write a field and read the other's field without synchronization — why can the classic result be that both reads see the old value, even though each write happened first in its own thread?**

That's the textbook Java Memory Model reordering example, and the honest answer is that "happens first in its own thread" only constrains that thread's own program order — it says nothing about when the other thread observes it. Without a happens-before edge between the two threads, the JIT and the CPU are both free to reorder independent stores and loads within a thread, and the store might simply not be visible to the other thread's read yet, regardless of which line came first in the source.

So if thread A does `cashPosted = true; r1 = bonusPosted;` and thread B does `bonusPosted = true; r2 = cashPosted;` — modelling two settlement threads each posting one leg of a `StakeSplit` and then peeking at the other leg — with plain fields, `r1 == false && r2 == false` is a legal outcome under the JMM, not a bug in a specific JVM. It just looks impossible if you reason about it as if the statements executed in the textual order across threads, but the model that actually governs correctness here is happens-before, not "wall-clock order of the source lines." Fixing it means introducing a real happens-before edge — making both fields `volatile`, or wrapping both writes and both reads in the same lock guarding the settlement record.

**Insight:** this is the single clearest demonstration that "the compiler wouldn't do that to my code" is not a safety argument — a compiler that reorders `cashPosted = true` and `r1 = bonusPosted ? 1 : 0` has broken no rule of the single-threaded semantics it is required to preserve, because neither statement depends on the other in that thread alone.

**Pitfall:** the wrong belief is "these are two independent booleans on two different threads, so there's no shared state to worry about." The symptom is exactly this puzzle's `r1=0 r2=0` outcome catching a reviewer off guard in production — the fix is recognizing that *any* field read by one thread and written by another is shared state requiring a happens-before edge, regardless of how unrelated the two fields look.

**Interview:** this is the question behind almost every "explain happens-before" prompt — the interviewer wants to hear that happens-before is a *specified partial order*, not "whatever order the source code reads in," and that the JMM exists precisely because that gap between program order and cross-thread visibility is real, not hypothetical.

**Follow-up — is this just theoretical, or does it actually happen on real hardware?** It's observable in practice, not theoretical — store buffers delay when a write becomes visible to other cores, and instruction reordering can move independent accesses around, which is exactly why the JMM spec exists as a contract instead of "don't worry about it."

**Q5. When would you reach for `final` fields and safe publication instead of `synchronized`, and what's the trap people fall into?**

If an object like `StakeSplit(Money bonusPortion, Money cashPortion)` is fully constructed before its reference is shared, and its fields are all `final`, then any thread that obtains the reference afterward is guaranteed to see the fully-initialized state — the 0.33 bonus and 3.00 cash from the canonical 3.33 rounding split — without needing any lock on read. That's the safe-publication guarantee the JMM gives `final` fields specifically, and it's a real performance win over locking every read of an object that never changes after construction.

The trap is publishing the reference itself unsafely — for example handing `this` out of the constructor to a listener, or starting a background thread from inside the constructor — because then another thread can observe the object before its `final` fields have finished being assigned, and the guarantee doesn't apply anymore even though every field is technically `final`. The fix is to finish construction fully, then publish the reference afterward through a safe path — a `final` field on another object, a `volatile` reference, or a properly synchronized handoff — never a reference leaked mid-constructor.

**Insight:** the guarantee is about the constructor's write barrier at the end of initialization, not about the keyword `final` doing anything magical at read time — which is exactly why leaking `this` early defeats it: the reads race ahead of the barrier that was supposed to protect them.

**Pitfall:** the wrong belief is "the constructor finished running, so publication must be safe." The symptom is a `StakeSplit` (or any similarly immutable record) that occasionally shows partially-initialized fields to a reader thread — the fix is checking not when construction finished but *how* the reference reached the other thread; a raw field assignment with no `volatile`, no lock, and no `final`-field indirection is not a safe publication path no matter how long after construction it happens.

**Interview:** this usually comes as "is a record automatically thread-safe for publication" — the one-line answer is that a record's fields being implicitly `final` gives safe publication for the fields themselves, but the reference to the record instance still needs a safe publication path of its own.

**Follow-up — does this protect a mutable object reachable through a final field, say a mutable ledger cursor referenced by `StakeSplit`?** No — `final` only protects the fields it directly guards, not mutable state reachable through them; that reachable state needs its own protection, whether that's immutability of its own or a lock.

**Q6. Why must a call to `wait()` sit inside a `while` loop instead of an `if`, and what's the difference from using `Condition`?**

`wait()` releases the monitor and parks the thread, but it can wake up for reasons other than a matching `notify()` — a spurious wakeup is explicitly permitted by the JLS — and even a real `notifyAll()` can wake a waiter whose condition is no longer true because another thread got there first and consumed the resource, for example another consumer already drained the last `WithdrawalTransaction` off the queue between the notify and this waiter actually getting scheduled. So the only safe pattern is `while (!conditionHolds()) { wait(); }`, re-checking the predicate every single time control returns from `wait()`, rather than assuming a return means the condition is now satisfied.

`Condition`, from `java.util.concurrent.locks`, is the same idea generalized to multiple wait-sets: instead of one implicit wait-set per monitor, a `ReentrantLock` can have several `Condition` objects, so a producer waiting for "queue not full" toward the `PaymentRun` batch and a consumer waiting for "queue not empty" don't get spuriously signalled by each other's `notifyAll()`-equivalent — each side has its own `awaitingNotFull` or `awaitingNotEmpty` condition to `await()` and `signalAll()` on.

**Insight:** `notifyAll()` is not "wasteful but safe" the way it's sometimes described — it is the *minimum* correct default given `notify()`'s failure mode, and the cost of waking extra threads that immediately re-check and re-sleep is almost always cheaper than debugging a hang that only shows up under production load.

**Pitfall:** the wrong belief is "I only have one kind of waiter on this monitor, so `notify()` is safe here." The symptom is an intermittent hang that only appears under real concurrency, where the woken thread happens to be a spurious wakeup rather than the specific event you needed — the fix is defaulting to `notifyAll()` unless you have proven, not assumed, that every waiter's predicate becomes true together.

**Interview:** this is usually asked as "why does the JLS allow spurious wakeups at all" — the one-line answer is that permitting them gives JVM implementations freedom to build `wait`/`notify` on lower-level, more efficient OS primitives without guaranteeing a perfect one-to-one mapping between a `notify()` call and a wakeup.

**Follow-up — why is `notify()` dangerous compared to `notifyAll()` here?** `notify()` picks one arbitrary waiter to wake, and if it happens to be one whose predicate still doesn't hold, the thread that actually needed waking never gets signalled, which surfaces in production as a hang with no exception anywhere.

**Q7. The settlement counter runs at 3,400 increments per second at burst. Why would you reach for `LongAdder` over `AtomicLong` there, given both are lock-free?**

Both use compare-and-swap under the hood, so neither blocks in the sense of parking a thread, but `AtomicLong` funnels every thread's CAS attempt onto the same single memory location, and at 3,400/sec with many concurrent settling threads that turns into a retry storm — each failed CAS means the thread has to reread the current value and retry, and contention grows with the number of threads simultaneously hammering the same cache line. `LongAdder` instead stripes the count across multiple internal `Cell` slots, so contending threads usually land on different cells and update those independently, only getting combined into a total when you call `sum()` — which trades a slightly stale, non-linearizable read for dramatically lower write contention under exactly this kind of burst.

The tradeoff to state explicitly, because interviewers specifically probe for whether you know it, is that `LongAdder.sum()` is not linearizable against concurrent updates the way `AtomicLong.get()` is — it can return a value that never existed at any single wall-clock instant if updates are landing on different cells while you're summing them. That makes it the right tool for a settlement-throughput metric someone is going to look at on a dashboard, but the wrong tool for a value another thread needs to branch on atomically right now.

**Insight:** the striping in `LongAdder` is adaptive — it starts as a single cell indistinguishable from `AtomicLong` and only grows additional cells once contention is actually detected via failed CAS attempts, so there's no memory cost paid for stripes you never needed.

**Pitfall:** the wrong belief is "lock-free means fast, so `AtomicLong` scales fine under any load." The symptom is throughput flattening or even dropping as thread count rises on a hot counter, which looks like it "shouldn't happen" because there's no lock in sight — the fix is recognizing that a CAS retry loop under contention degrades the same way lock contention does, just without a `BLOCKED` thread state to show it in a thread dump.

**Interview:** this is usually framed as "you've profiled a hot counter and it's not scaling — what do you check" — the one-line answer is contention on a single memory location via CAS retries, which `LongAdder`'s striping is specifically designed to relieve.

**Follow-up — when would you still pick `AtomicLong` over `LongAdder`?** Anytime you need `compareAndSet` semantics on the value itself, like a CAS-based state transition for a `Reservation`, because `LongAdder` only exposes accumulation, not a compare-and-set on a single authoritative value.

**Q8. Stake reservations peak at 1,200/sec and the downstream PSP call has a 240 ms p50. How do you size the `ThreadPoolExecutor` handling that, and what happens if you get the queue wrong?**

I'd apply Little's law first — at 1,200/sec arrival and 240 ms average time in the downstream call, the expected concurrent in-flight tasks are 1,200 × 0.24 ≈ 288, so the pool needs to be sized around that order of magnitude if the goal is to avoid queueing under normal load. Then I'd re-check the same arithmetic against the p99 of 11 seconds, which pushes expected concurrent tasks toward 1,200 × 11 = 13,200 — an impossible pool size to actually provision — which tells you the p99 case has to be handled by shedding load or routing to a separate slow-path pool, not by sizing the main pool to absorb it.

On the queue side, the mechanism people get backwards is that `ThreadPoolExecutor` only creates a thread past `corePoolSize` once the work queue is completely full — so pairing a large or unbounded `LinkedBlockingQueue` with a small `maximumPoolSize` means the pool never grows past `corePoolSize` at all; tasks just pile up in the queue instead of on extra threads, and you get unbounded latency growth on every stake reservation with no `RejectedExecutionException` to warn anyone until the process runs out of heap holding queued tasks.

**Insight:** this is precisely backwards from what most engineers guess the pool does — the queue is consulted *before* the pool grows toward `maximumPoolSize`, not after, so a "safety margin" unbounded queue is actually what disables the pool's ability to scale up under load.

**Pitfall:** the wrong belief is "a bigger queue is always safer than a smaller one, since it absorbs bursts without rejecting work." The symptom is a queue that grows without bound during a downstream slowdown, converting a latency problem into an out-of-memory problem hours later, far from the original cause — the fix is a bounded queue sized to a deliberate, small buffer, so the pool is forced to either grow, shed, or apply back-pressure instead of silently accumulating.

**Interview:** this is usually asked as "what does `maximumPoolSize` actually control" — the one-line answer is that it only kicks in once the queue rejects a new task by being full, so an unbounded queue effectively caps the pool at `corePoolSize` forever regardless of what `maximumPoolSize` is set to.

**Follow-up — so what queue would you actually use here?** A bounded `ArrayBlockingQueue` sized to a short buffer, paired with a `CallerRunsPolicy` or an explicit shedding response, so back-pressure on the reservation path is visible immediately instead of silently growing memory.

**Q9. What's the actual difference between `thenApply` and `thenApplyAsync` on a `CompletableFuture` chaining a card PSP call to a ledger update, and why does it matter?**

`thenApply` runs its function on whichever thread completes the previous stage — if the PSP authorise future is already done by the time you attach the callback, it runs inline on the calling thread synchronously; if it completes later, it runs on whatever thread the completion happened on, which for a PSP call is often an I/O callback thread from the HTTP client's own pool, not one you chose. `thenApplyAsync` without an explicit executor instead always submits to `ForkJoinPool.commonPool()`, and with an executor argument it runs there specifically — so it's a deliberate hop to a named thread pool rather than an implicit "wherever the completion landed."

This matters in practice because if you write the `FundsLedger` update as `thenApply`, assuming it'll run on "some background thread," but the completion happens to fire on the calling thread synchronously — say the PSP responded well inside its 240 ms p50 window before the callback even attached — you can end up doing a blocking ledger write inside a request thread you thought was free to return to its caller. That's a subtle latency regression that only shows up under the specific timing where completion races the callback attachment.

**Insight:** `thenApply` versus `thenApplyAsync` is not "sync versus async" in the way those words usually mean — both are non-blocking with respect to the *caller thread waiting for a result*; the actual axis is "which thread runs the callback," and that axis is invisible until you trace an actual thread name in a profiler.

**Pitfall:** the wrong belief is "`thenApplyAsync` is the safe default because it's explicitly async." The symptom is a request-thread stall that happens only intermittently, exactly when the upstream future completes fast enough to race the callback attachment on `thenApply`, or a starved common pool when every stage in the codebase defaults to `thenApplyAsync` with no executor — the fix in both directions is to name the executor explicitly for anything that can block, and to stop treating "async-suffixed" as a synonym for "safe."

**Interview:** this is usually asked as "trace which thread runs this callback" over a `CompletableFuture` chain with mixed `thenApply`/`thenApplyAsync` calls — the one-line answer is that you cannot know without checking whether the previous stage was already complete at attachment time, which is precisely why relying on the implicit behaviour is fragile.

**Follow-up — what goes wrong if you use `thenApplyAsync` without an explicit executor for a blocking ledger call?** You're now competing with every other `CompletableFuture` callback in the JVM for the shared common pool, which is sized to available processors and easily starved the moment any of those callbacks blocks on I/O.

**Q10. Two operations transfer funds between two client wallets in opposite directions and each locks its own account object first — why can this deadlock, and how do you fix it structurally?**

If operation A locks client X's wallet then tries to lock client Y's, while operation B locks client Y's wallet then tries to lock client X's, you can end up with A holding X and waiting on Y while B holds Y and waiting on X at the same moment — each holds a resource the other needs and neither will release what it holds, which is a circular wait, one of the four Coffman conditions (mutual exclusion, hold-and-wait, no preemption, circular wait) that must all hold simultaneously for deadlock to occur.

Since mutual exclusion is inherent to using a lock at all, and preemption isn't something you generally want to allow mid-transfer without corrupting an in-flight update, the practical fix targets circular wait directly: impose a total order on lock acquisition — for instance always lock the wallet belonging to the lower `ClientId` first, regardless of which operation initiated the transfer or which direction the money is moving — so two concurrent transfers between the same pair of clients can never form a cycle. The alternative, if a strict global order over the resources isn't practical because the set of lockable objects isn't known up front, is `tryLock` with a timeout on the second lock, backing off and retrying the whole operation if it can't be acquired — which trades deadlock for livelock risk unless the backoff is randomized rather than fixed.

**Insight:** lock ordering works because deadlock requires a *cycle*, and a total order over lock acquisition makes a cycle syntactically impossible — every transfer acquires locks in the same relative sequence, so no two transfers can ever be waiting on each other in opposite directions.

**Pitfall:** the wrong belief is "each transfer method locks its own two accounts inside a single `synchronized` block, so it must be atomic and therefore safe." The symptom is an intermittent full-application hang under real traffic that never reproduces in a single-threaded test — the fix is checking not whether each individual method is internally consistent, but whether the *order* in which any two concurrently-running methods acquire multiple locks can differ.

**Interview:** this is usually staged as "here are two transfer methods, spot the bug" — the one-line answer is to look for two locks acquired in opposite order across two methods, which is the signature of a circular-wait deadlock regardless of how correct each method looks in isolation.

**Follow-up — how would you detect this happened in production?** A thread dump showing both threads `BLOCKED` waiting on each other's monitor, which `jstack` explicitly flags with the line "Found one Java-level deadlock" and prints both stacks and the lock each thread is holding versus waiting for.

Read back across the ten, the follow-ups cluster into three recurring interviewer moves: naming the sibling that wins when the answer's tool loses (`ReentrantLock` over `synchronized`, `LongAdder` over `AtomicLong`, `Condition` over the implicit monitor wait-set), pinning a claim to a concrete QuizStakes number instead of an abstract one (the 1,200/sec and 240 ms of Q8, the 3,400/sec of Q7), and asking how the failure actually surfaces in production rather than in theory (a hang, a thread dump, a starved pool). Rehearsing an answer without covering all three leaves exactly the gap the follow-up is designed to probe.

The ten also split cleanly by which guarantee is at stake: Q1 and Q10 are about coordination discipline (interruption, lock ordering) rather than a single primitive; Q2, Q3, and Q4 are about the JMM's visibility and ordering contract; Q5 and Q6 are about publication and wait-set coordination; Q7, Q8, and Q9 are about throughput under load once the correctness question is already settled. An interviewer moving down this list in order is testing whether the candidate's mental model holds together as a system, not just as ten isolated facts.

None of the ten depends on a fact outside Part 1 to answer fully — that boundary is deliberate, since the same interview loop typically saves streaming and distributed variants of these questions for a later round grounded in Parts 2 through 5.

## Predict the output

Five complete, compiling Java 21 snippets, drawn from the stake-reservation and settlement paths. Three of the five have more than one legal output under the JMM — the point of the puzzle is naming the full legal set, not guessing the one you'd see on your own laptop.

Every snippet is self-contained and runnable as written — copy it into a single-file source launch (`java Snippet.java` on Java 21 needs no build step) and the behaviour it demonstrates, or fails to demonstrate on a given run, is exactly the point: a race that doesn't reproduce on the first ten runs is not a race that has been fixed, it is a race that hasn't triggered yet.

**Puzzle 1 — the visibility trap (multiple legal outputs).**

```java
public final class ReservationWorker {

    private static boolean stopRequested = false;

    public static void main(String[] args) throws InterruptedException {
        Thread worker = new Thread(() -> {
            long spins = 0;
            while (!stopRequested) {
                spins++; // pretend this is FundsLedger.reserveStake polling
            }
            System.out.println("worker stopped after " + spins + " spins");
        });
        worker.start();
        Thread.sleep(100); // give the worker a head start before requesting stop
        System.out.println("main: requesting stop");
        stopRequested = true; // a PLAIN field write — no happens-before edge to the worker
        worker.join(); // may never return: see "Legal outputs" below
        System.out.println("main: done");
    }
}
```

**Legal outputs, both consistent with the JMM:**

- `main: requesting stop`, then eventually `worker stopped after <N> spins`, then `main: done`, and the process exits normally.
- `main: requesting stop`, and then the process hangs forever — `worker stopped` and `main: done` never print, and `worker.join()` in `main` never returns.

**Why:** `stopRequested` is a plain field with no happens-before edge between the write in `main` and the read in the loop. The JIT is legally allowed to hoist the read out of the loop entirely — since nothing in the loop body appears, from the compiler's point of view, to change `stopRequested`, it is free to load it into a register once before the loop starts and never look at memory again, turning `while (!stopRequested)` into the equivalent of `while (true)` on that thread even though `main` did write `true` a moment later.

Whether it actually hangs depends on JIT compilation tier, platform, and how aggressively the loop was optimized — on an interpreter-only run it will very likely terminate because the interpreter re-reads the field every iteration, while a hot loop that has been promoted to C2-compiled code can hang indefinitely because the compiler has proven, correctly under single-threaded semantics, that the field "can't" change inside the loop. Both outcomes are legal under the JMM specification regardless of what any particular run happens to show, which is precisely the bug `volatile` exists to close.

**Insight:** "it worked on my machine" is not evidence of correctness for this class of bug — the same source file, recompiled at a different optimization tier or run on a different JVM implementation, can flip which of the two legal outcomes you actually observe, which is exactly why this kind of race survives code review and passes CI before it surfaces in production under sustained load.

**Pitfall:** the wrong belief is "the field is only written once, from one thread, so there's nothing to synchronize." The symptom is that single-writer, multi-reader fields are exactly the shape this bug hides in best, because a code reviewer's instinct for "where are the races" tends to look for concurrent writers, not for a lone writer whose single write simply never becomes visible to a reader on another thread — the fix is treating cross-thread visibility as a property of the *read*, not just the write.

**Interview:** this puzzle is usually posed as "why might this loop never terminate even though the flag is set" — the one-line answer is that a plain field gives the JIT permission to cache the read, and only `volatile` (or synchronization) removes that permission.

**Puzzle 2 — the same worker, fixed (single legal output).**

```java
public final class ReservationWorkerFixed {

    private static volatile boolean stopRequested = false;

    public static void main(String[] args) throws InterruptedException {
        Thread worker = new Thread(() -> {
            while (!stopRequested) { /* poll */ }
            System.out.println("worker stopped");
        });
        worker.start();
        Thread.sleep(50);
        stopRequested = true;
        worker.join();
        System.out.println("main: done");
    }
}
```

**Output (the only legal one):**
```
worker stopped
main: done
```

**Why:** `volatile` gives a happens-before edge from the write in `main` to every subsequent read in the worker, so the write is guaranteed visible and the loop is guaranteed to terminate — the JIT is no longer permitted to hoist the read out of the loop, because a `volatile` read must observe the most recent `volatile` write according to the JMM, not merely "a" write at some unspecified prior time. `join()` then happens-after the worker's completion by definition, so `main: done` is guaranteed to print after `worker stopped`, in that order, on every run, on every JVM implementation, at every optimization tier.

There is exactly one legal interleaving of output here, which is the entire point of the fix: the JMM does not merely make the hang *less likely*, it removes the second legal outcome from the specification entirely.

**Insight:** contrast this with Puzzle 1 — the only source difference is one keyword, `volatile`, and it moves the program from "two legal outcomes under the JMM, one of which hangs forever" to "one legal outcome, guaranteed," without touching a single line of the surrounding logic. That is the entire value proposition of getting visibility right: it converts undefined scheduling-dependent behaviour into a specified, testable guarantee.

**Pitfall:** the wrong belief is that `volatile` is "slower, so only use it if you actually see a bug." The symptom is exactly Puzzle 1's flaky hang, discovered under production load rather than in a code review — the fix is treating any field read by one thread and written by another as a candidate for `volatile` (or a lock) by default, not as an optimization to add reactively after an incident.

**Puzzle 3 — the classic JMM reordering (multiple legal outputs).**

```java
public final class LedgerFlagReordering {

    static boolean cashPosted = false;
    static boolean bonusPosted = false;
    static int r1, r2;

    public static void main(String[] args) throws InterruptedException {
        // Thread A posts the cash leg of a StakeSplit, then peeks at whether
        // the bonus leg (posted by thread B) is visible yet.
        Thread a = new Thread(() -> { cashPosted = true; r1 = bonusPosted ? 1 : 0; });
        // Thread B posts the bonus leg, then peeks at the cash leg — the
        // mirror image of thread A, racing against it with no lock.
        Thread b = new Thread(() -> { bonusPosted = true; r2 = cashPosted ? 1 : 0; });
        a.start(); b.start();
        a.join(); b.join();
        System.out.println("r1=" + r1 + " r2=" + r2);
    }
}
```

**Legal outputs, all four consistent with the JMM:**

- `r1=1 r2=1` — the intuitive case: both writes are visible to both reads.
- `r1=1 r2=0` — B's read of `cashPosted` executes before A's write is visible to it.
- `r1=0 r2=1` — the mirror image: A's read of `bonusPosted` executes before B's write is visible to it.
- `r1=0 r2=0` — the surprising case: neither write is visible to the other thread's read, even though each thread wrote its own flag "first" in its own program order.

**Why:** `cashPosted` and `bonusPosted` are plain fields, so there is no happens-before edge between thread A's write and thread B's read, or vice versa. `r1=0 r2=0` is the one that looks impossible to programmer intuition — "each thread wrote its flag before reading the other's, so at least one read should see a `true`" — but the JMM only constrains *program order within a thread*, not cross-thread visibility timing. The store to `cashPosted` can sit in thread A's CPU store buffer, invisible to any other core including the one running thread B, for long enough that B's read of it executes and returns the old value; the same applies symmetrically to B's store of `bonusPosted`.

The JIT compiler is a second, independent source of the same surprise, distinct from the hardware one: even without store buffers, the compiler is allowed to reorder the two independent statements inside each thread's body, since nothing in the single-threaded semantics of either thread depends on their relative order — so `r1 = bonusPosted ? 1 : 0` could execute before `cashPosted = true` is even issued, from the compiler's point of view, and still be a fully "correct" single-threaded compilation of that thread's code in isolation.

Making both fields `volatile`, or synchronizing both threads on the same lock guarding the settlement record, removes every outcome except `r1=1 r2=1`, because a `volatile` write happens-before a subsequent `volatile` read of the same field on any thread, closing the exact gap this snippet exploits.

**Insight:** this is the reason production code should never reach for a plain field as an inter-thread signal, no matter how "small" or "obviously fine" the write looks — the JMM does not grant an exception for booleans, for single-word writes, or for fields that "surely" get read soon after.

**Interview:** this is the canonical "explain the JMM reordering example" question — the strong answer names all four outcomes up front, calls out `r1=0 r2=0` as the surprising one, and grounds the fix in happens-before rather than in "the compiler probably wouldn't do that."

**Puzzle 4 — `synchronized` removes the race (single legal output).**

```java
public final class SynchronizedReservationCounter {

    private long reservations = 0;

    private synchronized void reserve() { reservations++; }
    // Same three bytecode steps as the racy version below, but now guarded
    // by the instance monitor — mutual exclusion plus a happens-before edge.

    public static void main(String[] args) throws InterruptedException {
        SynchronizedReservationCounter counter = new SynchronizedReservationCounter();
        Runnable task = () -> { for (int i = 0; i < 1000; i++) counter.reserve(); };
        Thread t1 = new Thread(task);
        Thread t2 = new Thread(task);
        t1.start(); t2.start();
        t1.join(); t2.join();
        System.out.println(counter.reservations);
    }
}
```

**Output (the only legal one):** `2000`

**Why:** every `reserve()` call is mutually exclusive and each unlock establishes happens-before with the next lock, so the 2,000 increments are fully serialized with no lost updates — whichever thread's call runs at a given moment sees every prior increment, because the happens-before edge guarantees it, not merely because "only one thread is in there at once." There is exactly one legal final value here, `2000`, regardless of how the OS scheduler interleaves the two threads across however many context switches actually occur.

**Insight:** this is the whole reason `synchronized` earns the carrier-pinning cost discussed in Q2 — it converts a scheduling-dependent race into a scheduling-independent guarantee, and that guarantee is exactly what the next puzzle loses by removing one keyword.

**Pitfall:** the wrong belief is that `synchronized` is "expensive, so only add it once you've actually seen a bug." The symptom, if that belief is acted on, is exactly Puzzle 5's non-deterministic count shipping to production silently, because nothing about a compiling, apparently-correct-looking `count++` signals that it needs a lock — the fix is defaulting to protecting any counter incremented from more than one thread, and only removing that protection later with a measured reason, such as switching to `LongAdder`.

**Interview:** interviewers pair this puzzle with Puzzle 5 specifically to see whether you can articulate *why* the guaranteed single output disappears when `synchronized` is removed, rather than just recognizing that it does.

**Puzzle 5 — the unsynchronized counter (multiple legal outputs, a range not a single number).**

```java
public final class RacyReservationCounter {

    private long reservations = 0;

    private void reserve() { reservations++; } // NOT synchronized — deliberately broken
    // reservations++ is getfield, ladd, putfield — three steps, no lock,
    // no happens-before edge between the two threads calling this method.

    public static void main(String[] args) throws InterruptedException {
        RacyReservationCounter counter = new RacyReservationCounter();
        // Each thread performs 1,000 stake reservations against the same
        // shared counter with no coordination between them whatsoever.
        Runnable task = () -> { for (int i = 0; i < 1000; i++) counter.reserve(); };
        Thread t1 = new Thread(task);
        Thread t2 = new Thread(task);
        t1.start(); t2.start();
        t1.join(); t2.join();
        System.out.println(counter.reservations);
    }
}
```

**Legal outputs — a range, not a single number:**

- Any integer in `[2, 2000]` is a legal final value under the JMM.
- `2000` is legal — and observed — whenever no interleaving ever loses an update; nothing about the JMM makes this the *guaranteed* result, it is simply one point in the legal range.
- Values below `2000` are legal whenever two threads read the same stale value before either writes back — the more such collisions, the further below `2000` the final count falls.
- In practice, on real hardware, a single run typically prints something well above 1,000 and often close to 2,000 — for example `1517` — because true simultaneous reads of the exact same field are a small fraction of 2,000 rapid increments, but the exact number is scheduling-dependent and not reproducible between runs.

**Why:** `reservations++` is read, add, write across three separate bytecode-level steps (`getfield`, `ladd`, `putfield`, roughly) with no atomicity guarantee and no happens-before edge between the two threads. Whenever both threads read the same value before either writes back — thread 1 reads 500, thread 2 reads 500, both compute 501, both write 501 — one increment is silently lost, and the counter has fallen one behind where it should be, with no exception and no signal that anything went wrong.

The JMM does not pin down thread scheduling, so it does not pin down which interleavings occur; it only guarantees the observable result is consistent with *some* legal interleaving of the individual reads and writes. That is why the honest interview answer to "what's the output" is a range, not a number — quoting a single figure like `2000` here would be describing the lucky case, not the guarantee the language actually makes.

The lower bound of `2`, not `1`, matters because the very first increment on either thread always applies cleanly before any contention is possible — there has to be at least one prior value in the field before a second thread can race against it — so it is not realistic (though not formally impossible under an adversarial scheduler) for every single one of the remaining 1,998 increments to collide down to the theoretical floor.

**Insight:** "usually close to 2000" is an empirical observation about typical thread scheduling on real hardware, not a JMM guarantee — and this exact snippet, `count++` shared across two threads with no synchronization, is the standard first demonstration in every serious concurrency course that a single line of Java can hide a three-step race.

**Pitfall:** the wrong belief is "I ran it ten times and always got 2000, so it must be safe on my platform." The symptom is that this observation is real but non-portable — it depends on how rarely the two threads' three-step sequences actually interleave on the tested hardware and JVM, and a different core count, a different JIT tier, or added contention elsewhere in the process can shift the observed range meaningfully; the only fix is synchronization, never a larger sample of "it worked" runs.

**Interview:** this is the puzzle interviewers use to separate "knows `count++` isn't atomic" from "can explain why the observed range isn't `[1, 2000]` and isn't a fixed number either" — the strong answer states the range, names the mechanism, and explicitly declines to guess a single figure.

Across all five, the pattern to carry into an interview is the same one three times over: a plain field used across threads has no happens-before edge, so the JVM, the JIT, and the hardware are all free to defer, reorder, or cache its value in ways that look impossible from the source alone. `synchronized`, `volatile`, and the atomics each close that gap in a different shape — mutual exclusion plus ordering, ordering alone, or lock-free single-variable atomicity — and naming which shape a given race needs is the actual skill being tested, not memorizing that races are bad.

Notice also the pairing structure: Puzzles 1 and 2 are the same worker with one keyword added, and Puzzles 4 and 5 are the same counter with one keyword removed. That pairing is deliberate and worth reproducing on a whiteboard — showing the minimal diff between broken and fixed code demonstrates the mechanism far more convincingly than describing it in the abstract, and it is exactly the format most interviewers reach for when they want to see whether a candidate actually understands *why* the fix works, not just *that* it works.

Puzzle 3 stands alone as the odd one out in that pairing, and deliberately so: it has no "fixed" companion snippet, because the point of the classic JMM reordering example is the surprise itself — `r1=0 r2=0` — not a before-and-after diff. If a candidate can explain why that specific outcome is legal without being shown the fix first, that is the strongest signal in this entire question set that the JMM is understood as a model, not memorized as a list of rules about `volatile` and `synchronized`.

---

**Leaves covered:** 1.1–1.26 (26 leaves, Part 1 wrap-up)
**Leaves deferred:** none
**Diagrams included:** none
**Target version:** Java 21 LTS
**Lines:** 401
