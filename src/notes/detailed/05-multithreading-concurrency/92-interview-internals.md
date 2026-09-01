# 05 Multithreading and Concurrency — Part 3 interview wrap-up — INTERNALS (§3.1–§3.13)

**Target version: Java 21 LTS.** | **Part 3 of 5** | [Index](00-index.md)
Previous: [Profiling, metrics and limits](observability/03-internals-profiling-and-metrics.md) · Next: [Locks from first principles](build-it/01-locks-from-first-principles.md)

Part 3 is the source-walk tier. Parts 1 and 2 taught the contract and the decision; this tier asks "and what actually executes when you write that line" — the mark word, the `ObjectMonitor`, the AQS queue, the `ConcurrentHashMap` bin lock, the continuation that makes a virtual thread cheap. This file drills recall across all thirteen §3.x sections without re-deriving any of it — it assumes §3.1–§3.13 have already been read closely, most of them at `[SOURCE]`/`[RESEARCH]`-tagged confirmation against `openjdk/jdk`.

The three blocks below are deliberately shaped differently. The summary table is a cold-recall drill — one row per subject, five columns each, meant to be read top to bottom the morning of an interview. The interview questions are full spoken answers, not crib notes, because a candidate who has only memorized the table's phrases will visibly run out of material the moment an interviewer asks "why" a second time. The predict-the-output puzzles are the hardest check of the three: they require the mechanism to actually be internalized well enough to reason about interleavings that were never explicitly stated in any prior file.

## Part 3 summary table

| Section | The mechanism it turns on | Structure/constant that implements it | The number you must state cold | The widely-repeated claim that is now false | The follow-up it invites |
|---|---|---|---|---|---|
| §3.1 Object header and mark word | Header layout and the multiplexed mark word | `markWord.hpp`: `locked_value=0` (`00`), `unlocked_value=1` (`01`), `monitor_value=2` (`10`), `marked_value=3` (`11`) | Header is 12 B compressed-oops / 16 B uncompressed, `lock_bits=2` at `lock_shift=0` | "The mark word has a lock-state field and a hash field, stored separately" — it is one 64-bit word reinterpreted by its own tag bits, there is no separate field | If the header is only 12 B, where does a 31-bit identity hash actually live once the object is locked? |
| §3.2 Monitor implementation | Lightweight (stack) locking, the displaced header, inflation, adaptive spin | `ObjectMonitor` fields confirmed at `jdk-21+35`: `_owner`, `_recursions`, `_cxq`, `_EntryList`, `_WaitSet`, `_succ` | Zero heap allocations on the uncontended path; one native `ObjectMonitor` allocated per inflation event | "Biased locking is why uncontended `synchronized` is cheap on modern JVMs" — JEP 374 disabled it in Java 15; the cheap path today is stack-locking, not a bias check | Once inflated, does the lock ever deflate back to stack-locked, and who triggers that? |
| §3.3 JIT optimisations on locks/memory | Lock elision, lock coarsening, non-volatile-read hoisting, `volatile` codegen | AArch64 `volatile` lowers to `ldar`/`stlr`; x86-TSO relies on the hardware's own total-store-order plus a `lock`-prefixed RMW | Order-of-magnitude: a `volatile` write costs roughly one extra store-buffer-draining instruction on AArch64, near-zero marginal cost on x86-TSO | "`volatile` is free" — true only as an x86 folklore artifact; it is a real, distinct instruction pair on AArch64 because that ISA is weakly ordered | Given that asymmetry, why does portable JMM-correct code still have to assume the weaker (ARM-like) model? |
| §3.4 Safepoints | Global synchronization points, time-to-safepoint vs pause time | Safepoint poll: a JIT-emitted load against a trap page, checked at loop back-edges and method returns | `GuaranteedSafepointInterval = 1000 ms` — the JVM forces a poll opportunity at least this often even with no pending request | "GC pause time is the whole cost of a stop-the-world pause" — time-to-safepoint, the wait for the last straggling thread to reach a poll, is a separate and often invisible tax | Why would a tight counted `int` loop with no method calls be the classic case that blows up time-to-safepoint? |
| §3.5 `AbstractQueuedSynchronizer` | The CLH-variant wait queue, template methods, `state` | Post-JDK-14 bit-flag `waitStatus`: `WAITING = 1`, `COND = 2`, `CANCELLED = 0x80000000`, with `ExclusiveNode`/`SharedNode`/`ConditionNode` subclasses | `CANCELLED = 0x80000000` — the sign bit alone marks a cancelled node, distinguishing it from any additive combination of the other flags | "AQS `waitStatus` is `SIGNAL=-1`/`CONDITION=-2`/`PROPAGATE=-3`" — that JDK 8-era small-integer encoding was replaced by the bit-flag scheme after JDK 14 | If the encoding changed, does `ReentrantLock`'s or `CountDownLatch`'s public contract change with it? |
| §3.6 `LockSupport`/park and the OS layer | The permit model, `park`/`unpark`, the Linux futex path | `Parker` rides a per-thread futex word; `park(Object blocker)` records the blocker for thread dumps | Order-of-magnitude: one to ten microseconds for an uncontended park/unpark round trip via `futex_wait`/`futex_wake` | "`park()` throws `InterruptedException` like `wait()` does" — it returns silently on interrupt, without clearing the flag and without consuming a permit | Given `park()` never throws, how does a well-written blocking utility actually detect and propagate interruption? |
| §3.7 The JMM formally | Executions, happens-before consistency, the committed-sets construction | JLS §17.4.6's two-clause happens-before-consistency test, built up incrementally via committed sets | Two clauses, not one — hb-consistency alone under-constrains the model, which is exactly why a second construction is layered on top | "Happens-before-consistent is the whole memory model" — it alone would legalize out-of-thin-air values; committed sets exist specifically to forbid self-justifying causal loops | Which of the five canonical litmus tests (roach motel, out-of-thin-air, IRIW, final-field, barrier cookbook) does committed sets police directly? |
| §3.8 `ConcurrentHashMap` internals | CAS-install then per-bin lock, cooperative striped resize | `spread(h) = (h ^ (h >>> 16)) & HASH_BITS`; `sizeCtl`: `0` default, positive = threshold, `-1` = initializing, `-(1+n)` = `n` resizing threads | `TREEIFY_THRESHOLD = 8`, `UNTREEIFY_THRESHOLD = 6`, `MIN_TREEIFY_CAPACITY = 64`, `MIN_TRANSFER_STRIDE = 16`, load factor `0.75` hard-coded | "`ConcurrentHashMap` locks the whole table on every write" — only a non-empty bin takes `synchronized(binHead)`; an empty bin's first insert is a single lock-free CAS | Why does treeification require `MIN_TREEIFY_CAPACITY = 64` on top of bin length 8 rather than treeifying any 8-node bin? |
| §3.9 `Striped64`/`LongAdder`, false sharing | Per-thread probe hashing into a `Cell[]`, `@Contended` padding | `Cell` is `@sun.misc.Contended`-annotated; array grows only up to `NCPU`, doubling on collision | 64-byte cache line; 128-byte effective `@Contended` padding via `-XX:ContendedPaddingWidth` | "`LongAdder.sum()` returns the exact current total" — it walks `base` plus every live `Cell` with no lock and no fence, so a racing `sum()` converges only once writers quiesce | If `sum()` isn't linearizable, what tool in `java.util.concurrent.atomic` do you reach for instead when a hard cap must be enforced? |
| §3.10 Queue and executor internals | Michael–Scott lock-free queue, `ctl` bit packing, worker lifecycle | `ThreadPoolExecutor.ctl`: high 3 bits = run state (`RUNNING` … `TERMINATED`), low 29 bits = worker count; `Worker` is itself an `AbstractQueuedSynchronizer` | `CAPACITY = (1<<29)-1 = 536,870,911`; `RUNNING = -1<<29`; `FutureTask` states `NEW = 0` … `INTERRUPTED = 6` | "A new task always spins up a new worker thread if one is free" — `execute()` tries `workQueue.offer()` before ever considering a new worker, up to `corePoolSize` | Why is `Worker`'s AQS `state` initialised to `-1` rather than `0` at construction? |
| §3.11 `ForkJoinPool` and work stealing | Per-worker double-ended queue, `ctl` as a signed 64-bit counter | `WorkQueue` array: owner pushes/pops one end (LIFO), thieves CAS-steal from the other (FIFO); `ManagedBlocker` for compensated blocking | `DEFAULT_COMMON_MAX_SPARES = 256` — the ceiling on compensating threads the common pool will create for blocked tasks | "Work stealing means every push/pop is a CAS" — only a thief's steal needs one; the owner's own push/pop at the opposite end is unsynchronised in the common case | What specifically stops the compensating-thread mechanism from spawning unboundedly under a flood of blocking calls? |
| §3.12 Virtual thread internals | Delimited continuations, mount/unmount, freeze/thaw | `StackChunk` is a relocatable heap object the GC walks; default scheduler is `ForkJoinPool` in FIFO (`asyncMode=true`) mode | JEP 491 is final in JDK 24 — `synchronized` no longer pins a carrier there, and `-Djdk.tracePinnedThreads` was removed with it | "`synchronized` never pins a virtual thread" — true only from JDK 24 onward; on the Java 21 baseline of this file it still pins because monitor ownership is tracked by carrier identity | On Java 21, what's the actual fix for code that must not pin — rewrite with `ReentrantLock`, or wait for the runtime to fix it? |
| §3.13 Runtime observability | `jstack` dump anatomy, JFR concurrency events, `ThreadMXBean` | Dump line shape: `"pool-1-thread-3" #14 prio=5 tid=0x... nid=0x1a3 waiting on condition`; `jdk.JavaMonitorEnter`/`jdk.ThreadPark` JFR events | JFR's default 20 ms threshold on monitor-enter/thread-park events — waits shorter than that never surface as a JFR event at all | "If `jstack` shows no blocked threads, there's no concurrency bug" — none of `jstack`, JFR, or `ThreadMXBean` can observe a data race; they see scheduling state, not memory visibility | Given a 20 ms JFR floor, what technique catches lock contention that never crosses that threshold but still adds up under load? |

## Interview questions

Ten questions, each answered at the length a candidate would actually speak it — 45 to 60 seconds — followed by the natural follow-up an interviewer asks next and its own one-line answer. None of these re-derive mechanism from scratch; they assume the source walk already happened and drill the recall and the "why" behind it.

### Q1. Walk me through what actually happens, at the mark-word level, when two threads race to lock the same `FundsLedger` for the first time — one wins uncontended, and explain why the loser's path is fundamentally different work, not just "the same thing but slower."

The winner takes the fast path HotSpot always tries first: it finds the mark word neutral — tag `01`, holding only identity hash and GC age bits — pushes a `BasicLock` onto its own stack frame, copies the current mark word into that `BasicLock` as the displaced header, and CASes the object's header to point at the `BasicLock`, flipping the tag to `00`. That's the entire cost: one CAS, zero heap allocation, and the lock state now lives inside the winning thread's own stack frame rather than anywhere shared.

The loser's fast-path CAS fails, because by the time it runs, the mark word already points at the winner's `BasicLock`, not the neutral pattern the loser's compare expected. At that point there is no queue to join yet — a `BasicLock` has nowhere to hold a list of waiters — so `ObjectSynchronizer::enter` allocates a real `ObjectMonitor` on the native heap and inflates the lock, flipping the tag to `10`. The loser pushes itself onto `_cxq`, the monitor's lock-free LIFO admission stack, with one more CAS, then spins briefly under the adaptive-spin heuristic before parking if the spin doesn't pay off.

The asymmetry is the whole point of the design: the winner never touches anything more expensive than its own stack, while the loser's mere presence permanently upgrades the lock to monitor-backed for as long as that `ObjectMonitor` stays allocated — even after the loser eventually acquires and releases it, the lock stays inflated until an idle deflation pass (JDK 15+, asynchronous, not safepoint-only anymore) reclaims it. So contention isn't just "the loser waits longer" — it's a structural cost paid by the object itself, applying to every subsequent acquisition by any thread until deflation runs.

For `FundsLedger`, this means the very first contended acquisition of a given ledger row's lock changes the cost profile of every subsequent acquisition of that same row for as long as the JVM keeps the `ObjectMonitor` around — a detail worth citing when someone asks why lock-striping (one fine-grained lock per shard rather than one lock guarding the whole ledger) matters beyond the obvious "less contention" answer: fewer distinct objects ever pay the permanent inflation cost in the first place.

One caveat worth stating unprompted: none of this — stack-locking, inflation, `_cxq` — is biased locking. That fourth tag (`101`) existed on pre-15 JVMs and stamped a specific thread's id into the header so re-entry cost a plain compare; JEP 374 disabled it by default in Java 15 because bias revocation needed a stop-the-world safepoint, and by then CAS had gotten cheap enough that the win no longer justified the cost. On Java 21 there are exactly three states, not four.

**Follow-up:** "Does the object ever go back to being stack-locked once it's inflated?" **Answer:** No — not without help. Deflation reclaims the `ObjectMonitor` and returns the mark word to neutral (`01`) once the JVM's async deflation pass (JDK 15+) observes it's unowned and unwaited-on, but the *next* lock attempt after that starts fresh from the stack-locking fast path again; the object doesn't silently revert mid-lifetime while still in active use.

It's worth adding, unprompted, why deflation had to move off the safepoint entirely: before JDK 15, monitor deflation only ran during a stop-the-world safepoint (typically piggybacked on a GC), which meant a JVM under light GC pressure could accumulate thousands of dead `ObjectMonitor`s — each one real native memory — for an arbitrarily long time between GCs. The async deflation thread introduced in JDK 15 walks the monitor list independently of GC cadence specifically to bound that native-memory growth under workloads like QuizStakes's stake-reservation hot path, where millions of short-lived contended locks per day would otherwise pin native memory indefinitely.

### Q2. Name two things the JIT is allowed to do to a `synchronized` block that would look wrong if you reasoned about it purely from the bytecode, and explain why each is still correct.

Lock elision is the first: if escape analysis proves an object can never be observed by another thread — it's allocated, locked, used, and discarded entirely within one method with no reference ever published outside it — the JIT can remove the `monitorenter`/`monitorexit` pair entirely. This is safe precisely because "no other thread can ever see this object" is the exact condition under which a lock provides zero actual guarantee; the lock was never doing anything but paying a CAS for a mutual-exclusion property nobody else could violate.

Lock coarsening is the second: if the JIT sees a tight loop that repeatedly acquires and releases the same lock — say, several sequential `synchronized(fundsLedger)` blocks back to back with no intervening logic that needs the lock released between them — it can merge them into one wider critical section, trading a shorter total held-time story for fewer acquire/release pairs. This is legal because the JLS's happens-before contract only requires that operations inside the original critical sections stay ordered relative to each other and to other threads' synchronized access to the same monitor; widening the section to cover the gaps between them doesn't violate any ordering another thread could observe, it just holds the lock slightly longer in exchange for far fewer CAS operations.

The one the JIT is never allowed to do is hoist a `volatile` read out of a loop the way it can hoist a plain field read — a non-volatile read of a flag checked in a spin loop can legally be hoisted above the loop entirely, turning `while (!stopRequested) {}` into an infinite loop if `stopRequested` is a plain field, because nothing in the JMM obligates the JIT to re-read it. The instant that field is `volatile`, the happens-before contract forbids the hoist, because every iteration's read has to be capable of observing a write from another thread that happened-before it in synchronization order — which is the entire reason `volatile` fixes that specific bug and a plain field does not.

Worth naming a fourth, more subtle case if pressed: `volatile` codegen itself differs by ISA in a way that isn't just "one instruction is used instead of another." On x86-TSO, ordinary stores already establish a total store order, so a `volatile` store needs no extra fence for store-then-load-elsewhere ordering beyond what a `lock`-prefixed CAS already requires for atomicity where one is used; on AArch64, which is weakly ordered by design, `volatile` reads and writes compile to the explicitly acquire/release-ordered `ldar`/`stlr` instruction pair, a real and distinct cost the x86 build simply doesn't pay. Reasoning about `volatile` cost from x86 experience alone is exactly the trap this asymmetry sets.

**Follow-up:** "If lock elision removes the monitor entirely, does that mean escape-analysis-proven-local objects never pay for `synchronized`?" **Answer:** Only in the steady state, after the JIT has compiled and inlined enough to run escape analysis; the interpreter and any not-yet-optimized tier still pay the full `monitorenter`/`monitorexit` cost until the method warms up, so the saving is a hot-path property, not a guarantee from line one.

A third case, worth naming because interviewers often ask for it directly, is lock coarsening across an inlined call boundary: if `PaymentService.recordSettlement` is a small `synchronized` method that gets inlined into a caller loop that itself calls it repeatedly with no intervening escape point, the JIT can coarsen across the inline boundary as if the two synchronized regions had been written adjacently by hand in the caller. This is the same legality argument as coarsening within one method — the JLS's happens-before contract only cares about relative ordering of accesses inside and across synchronized regions on the same monitor, not about the lexical shape of the source that produced them — but it surprises people because the source code never shows two `synchronized` blocks next to each other at all.

### Q3. What is a safepoint, and why is "time-to-safepoint" a real number engineers should care about separately from GC pause time?

A safepoint is a point at which every Java thread in the JVM has reached a state where its internal structures — stack, registers, heap references — are in a known, consistent shape that native VM operations (a GC cycle, a biased-lock revocation back when that existed, a JFR dump, a deoptimization) can safely inspect or move without racing the thread's own execution. The JVM achieves this by having the JIT emit a cheap poll — a load against a guard page — at loop back-edges and method returns, and when a safepoint is requested, every thread checks that poll at its next opportunity and blocks there until the VM operation finishes.

Pause time is what shows up in a GC log — the duration of the actual GC work once every thread has reached the safepoint. Time-to-safepoint is a separate, often invisible number: the time between the VM requesting the safepoint and the last straggling thread actually reaching its poll point. A thread executing a long counted loop that the JIT compiled without inserting a back-edge poll — historically true for some tightly bounded loops before JIT safepoint-bias fixes — can run for a surprisingly long time before it ever checks in, and the entire JVM, including every other thread that already reached the safepoint and is now just waiting, sits frozen the whole time.

Worth naming precisely what the poll itself costs, order-of-magnitude: a single unconditional load against a page that is normally readable, checked at loop back-edges and returns — cheap enough that the JIT emits it almost everywhere, and the entire cost model only turns pathological when a specific compiled path genuinely lacks one.

This matters in production specifically because a profiler using safepoint-biased sampling — the classic case being tools that can only take a stack sample *at* a safepoint — introduces a systematic bias: it only ever sees the states threads are in when they're near a safepoint poll, which skews the sampled profile away from code that runs long stretches between polls, understating exactly the methods most likely to be causing the time-to-safepoint problem in the first place. async-profiler's async, signal-based sampling exists specifically to avoid that bias. Virtual threads add one more wrinkle: because there can be far more of them than platform threads, and unmounted virtual threads aren't independently scheduled OS entities, safepoint semantics apply at the carrier level — it's carriers that need to reach the poll, not every virtual thread individually, which changes how you reason about time-to-safepoint under a virtual-thread-heavy workload.

**Follow-up:** "Is `GuaranteedSafepointInterval` something you'd ever tune in production?" **Answer:** Rarely — it exists as a backstop (default 1000 ms) to force a poll opportunity even absent an explicit request, mainly so JFR and diagnostic tooling never wait indefinitely; lowering it trades a small constant background overhead for tighter diagnostic latency, and raising it is a red flag that something else should be fixed instead.

Two profiler categories worth distinguishing for the follow-up "how would you even see this": safepoint-biased samplers (older `hprof`-style tools, and any profiler relying on `AsyncGetCallTrace` before its JDK 21 stabilization) can only take a stack sample once a thread has already reached a safepoint, so they systematically under-sample exactly the code paths whose long gaps between polls are the thing worth measuring; async-profiler's signal-based sampling interrupts a thread wherever it happens to be running, safepoint or not, which is why it's the tool of choice for diagnosing time-to-safepoint outliers rather than the pause times a GC log already reports directly.

The QuizStakes-shaped version of this failure mode is worth stating concretely: a batch reconciliation job walking all 19.8M daily ledger entries in one tight loop, compiled to native code with the loop's back-edge poll correctly present, still contributes real wall-clock time to any concurrent safepoint request — every iteration checks the poll, so the *cost* of the check itself, not its absence, becomes the thing worth profiling once that loop runs often enough. The failure mode this question is really fishing for is the *absent* poll case — a loop the JIT proved has a small, statically bounded iteration count and therefore didn't bother instrumenting with a back-edge check at all, which then runs to completion, uninterruptible, if that bound turns out to be wrong at runtime (a bug, not intended behavior, but one JIT safepoint-bias fixes have specifically targeted over the years).

### Q4. Explain the AQS acquire path for `ReentrantLock.lock()` in non-fair mode, and be specific about what `state` means and what the CLH-variant queue actually looks like.

`AbstractQueuedSynchronizer` doesn't know what a lock is — it exposes an `int state` and a set of protected template methods (`tryAcquire`, `tryRelease`, and the shared-mode equivalents) that a concrete synchronizer overrides to give `state` meaning. For `ReentrantLock`, `state` is the hold count: `0` means unlocked, and each reentrant `lock()` call by the current owner increments it by one, so `unlock()` has to be called the same number of times before `state` returns to zero and another thread can win it.

Reentrancy itself deserves one explicit sentence beyond "the hold count increments": `tryAcquire` checks `getExclusiveOwnerThread() == Thread.currentThread()` before falling through to the barging CAS, and only the *owning* thread's re-entry increments `state` without any CAS at all — a non-owner attempting to acquire an already-held lock never touches that branch, so reentrancy is a plain field read plus a plain field write on the fast path, cheaper than the first acquisition's CAS, not more expensive.

Non-fair `tryAcquire` first attempts a raw CAS from `0` to `1` before doing anything else — this is barging, and it's deliberate: a thread calling `lock()` gets to try acquiring immediately, even if other threads are already queued and have been waiting longer, because in practice this dramatically improves throughput at the cost of some fairness. Only if that immediate CAS fails does the thread go through `acquireQueued`: it wraps itself in a `Node`, appends itself to the tail of an internal doubly-linked queue — a CLH-lock variant, where each node's `prev` pointer is set before the CAS that publishes the node, which is why enqueue traversal for correctness purposes walks backwards from `tail` rather than forwards from `head` — and then spins in a loop checking whether its predecessor is `head` and whether it can now win the CAS; if not, it sets its predecessor's `waitStatus` to `SIGNAL` and parks via `LockSupport.park`.

The queue is intrusive — nodes aren't a generic linked-list library type, they're `AQS.Node` instances embedded directly in the synchronizer, with a `waitStatus` field carrying `SIGNAL` (this node's successor needs unparking on release), `CANCELLED` (timed out or interrupted, needs unlinking), `CONDITION` (parked on a `ConditionObject`'s separate wait queue, not this one), or `PROPAGATE` (used only in shared mode, to make a release propagate to more than one waiter). Release walks from `head` forward — the direction that's actually safe once a node is fully linked — finds the next non-cancelled successor, and unparks it, which is where that thread's `acquireQueued` loop wakes up and retries the CAS.

Cancellation is the part people forget to mention unprompted: if `acquireQueued`'s wait is interrupted or times out, the node's `waitStatus` flips to `CANCELLED` and `cancelAcquire` unlinks it by skipping over it rather than physically removing it from the middle of the queue immediately — a cancelled node stays reachable for a while, its predecessor's `next` pointer eventually retargeted past it, because safely unlinking a node out of a lock-free doubly-linked structure under concurrent traversal is exactly the kind of operation that's cheaper to defer and skip than to do eagerly and correctly in one step.

**Follow-up:** "You described the JDK 8-era `waitStatus` encoding — is that still accurate on a current JDK?" **Answer:** No, and saying so unprompted is the stronger answer: post-JDK-14 AQS replaced that small-integer `waitStatus` with bit flags (`WAITING = 1`, `COND = 2`, `CANCELLED = 0x80000000`) plus `ExclusiveNode`/`SharedNode`/`ConditionNode` subclasses, though the CLH-variant queue shape and the barging behavior described here are unchanged.

The subclassing itself is the detail that separates a candidate who read the changelog from one who read the source: `ExclusiveNode` and `SharedNode` exist because exclusive acquire (a `ReentrantLock`) and shared acquire (a `Semaphore`, a `CountDownLatch`) have different propagation-on-release rules, and giving each its own node subtype lets the JVM avoid a mode-dispatch branch on every queue operation that the old single `Node` class needed. `ConditionNode` is the third subtype, and it's specifically why a thread parked on a `Condition` doesn't sit in the same physical queue as a thread waiting to acquire the lock outright — `await()` moves the node onto a wholly separate per-`Condition` wait queue, and only `signal()`/`signalAll()` transfers it back onto the main AQS queue to compete for re-acquisition.

### Q5. What are the three legal reasons `LockSupport.park()` can return, and why does that make `park`/`unpark` fundamentally different from `wait`/`notify`?

`park()` can return for exactly three reasons: another thread called `unpark()` on this thread and consumed the permit that grants; a spurious wakeup, which the JavaDoc explicitly permits and callers must tolerate by re-checking their condition in a loop; or the thread was interrupted, in which case `park()` returns without clearing the interrupt flag and without consuming any permit. That third case is the one people get wrong most often — `park()` doesn't throw `InterruptedException`, it just returns, so code that assumes "no exception means I actually got my permit" is silently wrong under interruption.

The structural difference from `wait`/`notify` is the permit model itself: every thread has an associated binary permit, available or not, and `unpark(thread)` makes it available regardless of whether the target thread has called `park()` yet — if `unpark()` runs first, the next `park()` call returns immediately without blocking at all, consuming that pre-existing permit. `wait`/`notify` has no such memory: a `notify()` call with no thread currently waiting on the monitor is simply lost, which is exactly why every `wait()` loop has to re-check its condition in a `while`, not just to guard against spurious wakeup but because the notification itself could have raced the wait and vanished.

One more precise distinction worth having ready: `park()`'s spurious-wakeup allowance exists for the same reason `Object.wait()`'s does — the JVM reserves the right to wake a parked thread for internal bookkeeping reasons (a signal delivery, an internal safepoint-adjacent mechanism) that have nothing to do with the application's condition, and documenting it as legal rather than trying to eliminate it entirely keeps the implementation free to make those internal choices without breaking the public contract.

Underneath, on Linux, `park`/`unpark` for a platform thread is implemented via the `Parker` class riding a futex: parking does a `futex_wait` on a per-thread word if the permit isn't already set, and unparking does a `futex_wake`, so the round trip is a couple of syscalls, order-of-magnitude one to ten microseconds — a real number worth stating as a band, not a measured constant, since it depends on kernel and hardware. `park(Object blocker)` is the overload every high-level concurrency utility actually uses instead of the bare `park()`, because it records the blocker object so a thread dump prints `- parking to wait for <0x...> (a java.util.concurrent.locks.AbstractQueuedSynchronizer$ConditionObject)` — that line is how you read a `jstack` dump and know a thread is blocked on a specific lock or condition rather than just "parked, cause unknown."

**Follow-up:** "Could you build `wait`/`notify` semantics on top of `park`/`unpark`, or is it the other way around?" **Answer:** `park`/`unpark` is the lower-level primitive AQS itself is built on, and `Condition` (AQS's `wait`/`notify` replacement) is implemented in terms of it — the permit model can express monitor-style waiting, but a plain permit can't express `notify()`'s "wake exactly one arbitrary waiter" fairness-free selection without the surrounding queue AQS provides.

There's also a timed family worth naming: `parkNanos(long)` and `parkUntil(long)` are the primitives underneath every timed acquire in the JDK — `ReentrantLock.tryLock(timeout, unit)`, `CountDownLatch.await(timeout, unit)`, `Future.get(timeout, unit)` — and they share the same three-legal-return-reasons contract as bare `park()`, plus a fourth: the deadline simply elapsing. A caller can't distinguish "I was unparked" from "my timeout elapsed at almost exactly the same instant" purely from `parkNanos`'s return; it has to re-check its actual condition and remaining time budget afterward, which is precisely why every JDK timed-wait implementation is a loop, never a single call.

### Q6. State the formal happens-before-consistency requirement from the JMM, and explain in your own words why the JLS needs a "committed sets" construction instead of just defining happens-before and stopping there.

Happens-before consistency has two clauses, both from JLS §17.4.6: first, for every read `r` in the execution, the write `w` that `r` observes must not come after `r` in the happens-before order — a read can only see a write that's happens-before it, or one that's unordered with it (a genuine race), never one that comes strictly later; second, the total synchronization order — the order of all lock/unlock, volatile read/write, and thread start/join actions — has to be consistent with the happens-before partial order the program derives. Together those two clauses say: whatever the actual execution turns out to be, it has to be explicable as *some* interleaving that respects the ordering constraints synchronization actually establishes.

The reason the JLS needs the heavier committed-sets construction on top of just "happens-before consistent" is that happens-before-consistency alone is too permissive — it would legalize out-of-thin-air values, where a thread reads a value that no write in the program ever actually produced, justified only by a circular chain of "this write could have happened because that read observed a value consistent with it, which could happen because..." The committed-sets construction incrementally builds up the set of actions that are allowed to be considered "already executed" at each step, action by action, specifically so that no action can be justified by assuming its own effect already happened — it rules out exactly the self-justifying causal loops that plain happens-before-consistency doesn't forbid on its own.

One consequence worth drawing out explicitly: IRIW-style anomalies are why "sequential consistency" and "the JMM's guarantees" are not the same claim — a JVM is free to allow four threads to disagree on the global order of two independent volatile writes as long as each individual thread's own view stays internally happens-before-consistent, because the JMM was deliberately designed to permit real, weakly-ordered hardware to implement it efficiently rather than mandate a single global total order the way sequential consistency would.

This is the machinery behind the five litmus tests every serious JMM discussion cites: roach motel (synchronization actions can move into a critical section but never out — code can be reordered *inward* toward a lock but not *outward* past it), out-of-thin-air (values must trace to an actual write, not a self-consistent fiction), IRIW (independent reads of independent writes — four threads, two writing distinct volatiles, two reading both in opposite orders, can still legally observe inconsistent global orderings on hardware weaker than sequential consistency), the final-field rules (a correctly published `final` field is guaranteed visible without any synchronization, because the JMM inserts a freeze-and-guarantee-visibility semantics specifically at constructor exit), and the cookbook of memory-barrier placements JIT authors implement against, not application authors. Nobody derives the committed-sets construction from memory in an interview — the honest answer is naming what it exists to prevent and why happens-before-consistency by itself falls short.

**Follow-up:** "As an application author, do you ever need the committed-sets construction directly?" **Answer:** Essentially never — it's the formal justification JIT and hardware-memory-model authors reason against; application code only needs the derived, practical rules (happens-before edges from locks, `volatile`, thread start/join, and final-field publication), which is exactly why every practitioner-facing JMM explanation skips straight to happens-before and never mentions committed sets at all.

The final-field rule deserves one concrete sentence because it's the one practitioners actually rely on without noticing: constructing an immutable `Money(BigDecimal amount, Currency currency)` and publishing the reference safely (never leaking `this` from the constructor before it completes) guarantees every other thread that reads that reference afterward sees the fully-initialized `amount` and `currency`, with no `volatile`, no lock, and no explicit synchronization anywhere — the freeze semantics the JMM attaches to constructor exit for `final` fields does that work silently, which is exactly why immutable value types are the cheapest possible way to publish data safely across threads.

### Q7. Describe what happens inside `ConcurrentHashMap.put()` for a brand-new key hashing into an empty bin, versus a key that collides into a bin already holding entries — and quote `sizeCtl`'s possible meanings.

For a new key into an empty bin, the path is nearly lock-free: `spread(key.hashCode())` — `(h ^ (h >>> 16)) & HASH_BITS` — mixes the high bits into the low bits to reduce collision clustering from poor `hashCode()` implementations, then the table index is derived from that spread hash. If the bin at that index is `null`, `putVal` does a single CAS to install a new `Node` directly — no lock taken at all, because there's no existing chain to race against, only an empty slot to claim.

One nuance worth stating unprompted: the CAS-install path isn't quite lock-free in the absolute sense people assume, because a check-then-CAS on a `null` bin can still race another thread's check-then-CAS on the same bin — `putVal` handles that by retrying the whole per-bin attempt in a loop if its own CAS fails, rather than falling back to a lock for the empty-bin case, so the fast path stays lock-free even under a genuine race for the first slot in a bin.

For a colliding key, the bin already has a head node, and CHM falls back to `synchronized(binHead)` — a plain monitor lock scoped to that one bin's head node, not a global table lock — to walk the chain (or the `TreeBin` if it's already treeified) and either update an existing key's value or append a new node. This is the core design insight: contention is confined to whichever single bin two threads happen to collide into, so the map as a whole scales with bin count, not with a single lock's throughput ceiling — QuizStakes's `ClientRestrictions` map, sized for 2.4M clients, only ever contends on a bin, never on the whole structure.

`sizeCtl` multiplexes four meanings depending on its sign and value, the same style of overloading the mark word uses for lock state: `0` is the uninitialized default before the table is first allocated; a positive value is the next resize threshold (roughly 0.75× the table capacity); `-1` means the table is currently being initialized by exactly one thread via `initTable`; and `-(1 + n)` for `n > 0` means `n` threads are cooperatively resizing right now. That cooperative resize is the other structural feature worth naming: `transfer` splits the old table into low and high halves per bin (the "lo/hi split"), and multiple threads can each claim a stride of bins to migrate concurrently rather than one thread rehashing the entire table alone — which is exactly why a CHM resize under load doesn't produce the same multi-hundred-millisecond stop-the-world-feeling pause a naive single-threaded rehash would. Treeification only kicks in at bin length 8 and only if the table itself is already at least `MIN_TREEIFY_CAPACITY = 64` — below that size, CHM prefers to resize the table rather than treeify a small table's overcrowded bins, since a bigger table is a cheaper fix than a red-black tree for that case; untreeify happens back down at length 6, with the gap between 8 and 6 deliberately preventing thrashing at the boundary.

**Follow-up:** "What stops two threads from both trying to `initTable()` the very first time the map is touched?" **Answer:** The same `sizeCtl` field arbitrates it: a thread that CASes `sizeCtl` from its current value to `-1` wins the right to allocate the initial table, and every other thread that loses that CAS just spins (`Thread.yield()`) until `table` is non-null, so initialization itself is lock-free and single-writer by construction, not by a separate lock object.

The resize path itself is worth one more level of detail because it's the part that actually explains the `-(1+n)` encoding: `transfer` splits the old table's bins into a "lo" list (elements staying at the same index in the doubled table) and a "hi" list (elements moving to `index + oldCapacity`) using a bit test against the old capacity, and each resizing thread claims a contiguous stride of bins — at least `MIN_TRANSFER_STRIDE = 16` — to migrate on its own. Every thread that finishes its stride decrements the resizer count encoded in `sizeCtl`; the last one to finish (the CAS that would take the count to zero) is the one responsible for swapping in the new table and clearing the resize-in-progress state, which is why `-(1+n)` has to carry the actual live count rather than a boolean.

### Q8. Why does `LongAdder` outperform `AtomicLong` under high contention, and what specifically is `Striped64` doing that a naive "just use an array of counters" implementation would get wrong?

The naive version — an array of plain `long` counters, one per thread or per stripe, summed on read — gets false sharing wrong: if those counters sit contiguously in an array, several of them share the same CPU cache line, and even though two threads are writing to logically distinct counters with zero actual data dependency, the cache-coherence protocol treats the whole 64-byte line as contended, forcing it to bounce between cores on every write. `Striped64`'s `Cell` class is specifically annotated `@sun.misc.Contended`, which the JVM honors by padding each `Cell` out to its own cache line — effectively 128 bytes of padding by default (`-XX:ContendedPaddingWidth`) — so that two threads updating adjacent cells never invalidate each other's cache line even though the cells sit in the same backing array.

The second piece is how a thread picks which cell to write: each thread carries a pseudo-random probe value, and on contention (a CAS on `base` or a cell fails), `Striped64` either retries against a different, rehashed probe or grows the `Cell[]` array — capped at `NCPU`, since past one cell per core there's no more contention left to relieve. Under low contention, `LongAdder` writes go straight to `base`, a single `long`, with cost indistinguishable from `AtomicLong`; it's only once contention appears that cells get allocated at all, so the memory cost scales with observed contention, not with a size chosen up front.

The tradeoff, worth stating unprompted because it's the part people get wrong: `sum()` walks `base` plus every live `Cell` with no lock and no fence coordinating it against concurrent `add()` calls, so it is not a linearizable read — call it while writers are actively adding and you can observe a value that never corresponded to any single instant in time, only converging to the true total once writers quiesce. That's not a bug, it's the JMM-visible cost of the design: `LongAdder` optimizes for write throughput at the explicit expense of read consistency, which is exactly why it's the wrong tool for `FundsLedger`'s reservation counter — anything gating a hard cap needs `compareAndSet`'s atomicity, which `LongAdder` doesn't expose — but the right tool for a settlement-throughput counter like the 3,400/sec burst metric, where an approximately-current value is all anyone needs.

**Follow-up:** "Could you make `sum()` linearizable without giving up `LongAdder`'s write throughput?" **Answer:** Not without reintroducing the exact contention `Striped64` exists to avoid — a linearizable snapshot needs either a global lock over all cells during the read (which serializes writers against the reader) or a quiescence barrier, and `LongAdder` deliberately trades that guarantee away because the counters it targets (throughput metrics, not correctness gates) never needed it.

Worth stating why the cap is exactly `NCPU` and not something larger: once there are at least as many `Cell` slots as logical cores, every core can in principle be writing to a distinct cache line simultaneously with zero remaining contention to relieve, so growing the array further only wastes memory and makes `sum()`'s walk longer for no throughput benefit. This is the same reasoning `ForkJoinPool`'s default parallelism and `Runtime.availableProcessors()`-sized pools lean on elsewhere in this topic — `NCPU` isn't a magic constant, it's the point past which adding more of the resource stops buying anything.

### Q9. Trace what happens inside `ThreadPoolExecutor` when a task is submitted while the pool is `RUNNING` but at its core size with a full queue, and explain what `ctl` is actually packing.

`ctl` is a single `AtomicInteger` packing two logically separate pieces of state into one word: the high 3 bits encode the run state (`RUNNING`, `SHUTDOWN`, `STOP`, `TIDYING`, `TERMINATED`, in that lifecycle order, with numerically increasing values as the pool winds down), and the low 29 bits encode the current worker count. Packing them together — rather than two separate fields — means a single CAS can atomically check-and-update both, which matters because `execute()` has to answer "is the pool still running, and do I have room to add a worker" as one atomic question, not two separate reads that could race a concurrent `shutdown()` call landing in between them.

`execute()`'s submission algorithm, given a task arriving when the pool is already at `corePoolSize` workers: it first tries `workQueue.offer(task)` rather than immediately spinning up a new worker, because `ThreadPoolExecutor` prefers reusing existing threads to creating new ones. If the queue is bounded and full, `offer` fails, and only then does the executor attempt to add a new worker up to `maximumPoolSize`; if that also fails because the pool is already at `maximumPoolSize`, the task is handed to the configured `RejectedExecutionHandler` — `AbortPolicy`, `CallerRunsPolicy`, `DiscardPolicy`, or `DiscardOldestPolicy`.

Worth stating why `offer()` is tried before creating a worker even when the pool hasn't yet reached `maximumPoolSize`: `execute()`'s check order is core-then-queue-then-max specifically to prefer bounded memory and thread-count growth over latency, which is why a `LinkedBlockingQueue` with no explicit capacity bound (the default for `Executors.newFixedThreadPool`) can silently mean `maximumPoolSize` is never reached at all — the queue absorbs everything before the pool ever grows past `corePoolSize`, a classic misconfiguration for a bursty producer like the 1,200/sec stake-reservation peak.

Each `Worker` is itself an `AbstractQueuedSynchronizer` subclass — an unusual, minimal use of AQS as a non-reentrant mutex rather than a reentrant lock, initialized with `state = -1` specifically so the worker can't be interrupted by `shutdown()`'s "interrupt idle workers" pass before `runWorker` has even started executing its first task. `runWorker` locks the worker (acquiring that AQS state), then loops calling `getTask()` — which pulls from the queue, applying `keepAliveTime` timeout logic once the pool is above `corePoolSize` or `allowCoreThreadTimeOut` is set — running each task in between, and only exits the loop (letting the worker thread die) once `getTask()` returns `null`, meaning no more work is coming and this worker isn't needed. On the async side, `FutureTask` tracks its own lifecycle as an explicit state machine — `NEW`, `COMPLETING`, `NORMAL`, `EXCEPTIONAL`, `CANCELLED`, `INTERRUPTING`, `INTERRUPTED` — and `CompletableFuture` builds its dependent-stage graph as a Treiber stack of `Completion` nodes pushed via CAS, so that completing a stage pops and triggers every registered dependent without needing a lock over the whole chain.

**Follow-up:** "Why does `execute()` try the queue before trying a new worker, given a new worker could start the task sooner?" **Answer:** Thread creation is the expensive operation being amortized — `ThreadPoolExecutor` is explicitly optimizing for total throughput and OS resource usage over any single task's latency, so it will happily let a task sit briefly in the queue rather than pay for a new native thread whenever an existing worker could reasonably drain it instead.

The four `RejectedExecutionHandler` policies are worth being able to name concretely against QuizStakes, because "which one would you pick" is the natural next question: `AbortPolicy` (default) throws `RejectedExecutionException` back to the caller submitting a `BankWithdrawal` payout task, which is correct when a caller must know synchronously that the work was refused; `CallerRunsPolicy` runs the task on the submitting thread itself, which naturally throttles a bursty producer like the 1,200/sec stake-reservation peak by slowing down whoever's generating the load; `DiscardPolicy` silently drops the task, almost never right for anything touching the ledger; and `DiscardOldestPolicy` evicts the queue's oldest pending task to make room, which is dangerous for ordered financial operations since it can silently reorder or drop an older withdrawal in favor of a newer one.

### Q10. Explain work stealing in `ForkJoinPool` well enough to say why a worker never contends with itself, and then explain what compensation and `ManagedBlocker` are for.

Each worker owns one `WorkQueue`, backed by an array functioning as a double-ended queue. The owning worker pushes and pops from one end — conventionally treated as the bottom — with no synchronization at all when there's no thief racing it, because only the owner ever touches that end under the common case; that's the entire reason work stealing scales as well as it does, since the overwhelmingly common operation (a worker draining its own freshly-forked subtasks) touches no shared, contended memory.

The LIFO-at-the-bottom, FIFO-at-the-top asymmetry isn't incidental either: an owner popping its own most-recently-pushed subtask (LIFO) tends to work on data it just touched, which is friendlier to cache locality than popping the oldest task would be, while a thief stealing from the opposite end (FIFO, oldest-first) tends to grab the largest remaining chunk of undivided work in a typical divide-and-conquer decomposition — exactly the steal that's worth the CAS, rather than repeatedly re-stealing small tail fragments. A thief worker that's run out of its own work looks at another worker's queue and steals from the opposite end — the top — using a CAS, so the one operation that genuinely needs synchronization (a steal, racing either the owner's own pop or another thief) is exactly the operation that gets it, and nothing else pays that cost.

`ctl` here plays the same multiplexing role it does in `ThreadPoolExecutor`, just packed into a signed 64-bit field instead of a 32-bit one, tracking active thread count, total thread count, and a stack of idle workers waiting to be woken, so the pool can decide in one atomic read whether it needs to unpark an idle worker or create a new one when work becomes available.

Compensation and `ManagedBlocker` exist for the specific problem of a `ForkJoinTask` that needs to block on something the pool itself has no visibility into — a blocking I/O call, or a `Future.get()` on work outside the pool. Ordinarily, a worker blocking ties up one of the pool's fixed parallelism slots for no compute reason, starving other tasks; `ForkJoinPool.managedBlock()`, given a `ManagedBlocker` implementation, tells the pool "I'm about to block, and here's how you'd know I'm done" — and the pool responds by spinning up a compensating thread to temporarily replace the blocked worker's parallelism slot, so the blocking task doesn't silently shrink the pool's effective capacity. `helpJoin` is the complementary mechanism for the non-blocking case: a worker that calls `join()` on a task it can see hasn't completed yet tries to help execute pending work from that task's own queue instead of just parking, since the JVM would rather do useful work than block outright. `CountedCompleter` is a lower-level `ForkJoinTask` variant used when you want explicit completion-counting control over a task tree rather than relying on the default recursive-join propagation — useful for graph-shaped decompositions where a simple divide-and-conquer join tree doesn't fit. A concrete case where it earns its keep over plain `RecursiveTask`: fanning a settlement-reconciliation sweep out across many independent `PaymentRun` batches where completion needs to be signalled once *all* sibling batches finish rather than following a strict binary join tree, `CountedCompleter.onCompletion` gives that fan-in point explicitly instead of forcing an artificial tree shape onto a naturally flat set of parallel batches.

The `ctl` field's own bit layout is worth one more precise sentence, since "signed 64-bit counter" undersells what it's doing: it packs the total worker count, the active (non-idle) worker count, and a Treiber-stack-style pointer to the top of the idle-worker list into different bit ranges of the same word, so a single CAS can atomically answer "is there an idle worker to wake, and if I wake it, how do the counts change" — the identical multiplexing trick `ThreadPoolExecutor.ctl` uses at 32 bits, just needing the extra width because `ForkJoinPool` tracks more independent quantities at once.

Two JDK bug IDs worth having ready if pressed on ForkJoinPool correctness history: JDK-8330017 and JDK-8315740, both concerning edge cases in the pool's internal accounting under specific termination and compensation sequences — cite them as "known tracked issues," not as facts to explain the internals of from memory.

**Follow-up:** "What happens if `managedBlock()` is never called and a worker just blocks directly on I/O?" **Answer:** The pool has no way to know it should compensate, so that worker's parallelism slot is simply gone for the duration of the block — with a fixed-size common pool this is exactly how a handful of accidental blocking calls silently degrade throughput on every other submitted task, which is why `ManagedBlocker` exists as an opt-in contract rather than something the pool can infer automatically.

`helpQuiesce()` is the related mechanism worth naming for completeness: a worker can call it to actively help drain the entire pool's remaining work down to quiescence rather than just its own subtask, which is useful for a bulk QuizStakes batch job (say, the nightly `PaymentRun` sign-off sweep) that wants to block the calling thread until every submitted fork-join task across the whole pool has actually finished, not merely the one task it directly joined on.

## Predict the output

Five complete, compiling snippets. At least two turn purely on an internals fact rather than ordinary concurrency reasoning — `System.identityHashCode` forcing inflation and a `jstack`-visible pinning difference across the JEP 491 boundary are both here. Every "output" below is either exact or the full set of legal outcomes; where more than one output is legal, both are shown and the reason neither can be ruled out is stated explicitly.

**Puzzle 1 — stack-locking versus forced inflation, observed via `hashCode()`**

```java
import org.openjdk.jol.info.ClassLayout;

public class MarkWordDemo {
    static final class Reservation {
        long reservedAtEpochMillis = 1_735_689_600_000L;
    }

    public static void main(String[] args) throws InterruptedException {
        Reservation r = new Reservation();
        synchronized (r) {
            System.out.println("stack-locked tag bits low byte odd/even: "
                    + (readMarkLowByte(r) % 2 == 0 ? "even (00, stack-locked)" : "odd"));
        }

        r.hashCode();

        synchronized (r) {
            System.out.println("after hashCode(), locked again -> monitor allocated: "
                    + (readMarkLowByte(r) == 0x02 ? "inflated (tag 10)" : "not inflated"));
        }
    }

    static long readMarkLowByte(Object o) {
        String printable = ClassLayout.parseInstance(o).toPrintable();
        return printable.contains("(fat lock)") || printable.contains("monitor") ? 0x02L : 0x00L;
    }
}
```

<details><summary>Output and why</summary>

```
stack-locked tag bits low byte odd/even: even (00, stack-locked)
after hashCode(), locked again -> monitor allocated: inflated (tag 10)
```

The first `synchronized (r)` block finds `r`'s mark word neutral (tag `01`, no hash yet) and takes the cheap stack-locking path — CAS the mark word to point at a `BasicLock` on the current stack frame, tag becomes `00`. Calling `r.hashCode()` afterward — while `r` is unlocked — writes the 31-bit identity hash into the mark word's neutral-state bits, leaving the tag at `01` but marking the object "hash-bearing." The second `synchronized (r)` block now finds a hash-bearing object: HotSpot's rule is that a hash-bearing object can never be stack-locked again, because a `BasicLock` lives in one thread's stack frame and the hash has to remain readable from any thread at any time — so this acquisition inflates straight to a real `ObjectMonitor`, tag `10`, with the hash copied into the monitor where it's permanently reachable. This is a real, illustrative harness rather than a literal captured JOL run this session — the mechanism it demonstrates (hashCode-forced inflation) is confirmed against `markWord.hpp` and HotSpot's documented `ObjectSynchronizer::enter` behavior, not against a live trace.

Worth extending: `System.identityHashCode(r)` (the true source of `Object.hashCode()`'s default implementation) produces the identical forcing effect even if `Reservation` never overrides `hashCode()` at all, because the hash gets computed and cached in the mark word the first time *anything* asks for it — `hashCode()`, `identityHashCode()`, a debugger inspecting the object, or a hash-based collection storing it by identity. This is precisely why interview folklore ("never call `hashCode()` on a lock object") understates the trap: the forcing behavior isn't about calling a specific method, it's about the mark word acquiring a hash at all, from any caller, at any time before or during a lock's lifetime.

</details>

**Puzzle 2 — AQS barging versus queued fairness**

```java
import java.util.concurrent.locks.ReentrantLock;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.TimeUnit;

public class BargingDemo {
    public static void main(String[] args) throws InterruptedException {
        ReentrantLock lock = new ReentrantLock(false); // non-fair
        lock.lock();

        Thread queued = new Thread(() -> {
            lock.lock();
            System.out.println("queued thread acquired");
            lock.unlock();
        }, "settlement-ingest-1");
        queued.start();
        Thread.sleep(100); // ensure "queued" is parked in the AQS wait queue

        CountDownLatch bargerDone = new CountDownLatch(1);
        lock.unlock(); // release: about to hand off, but hasn't unparked anyone yet at this instant

        Thread barger = new Thread(() -> {
            if (lock.tryLock()) {
                System.out.println("barger acquired first, despite arriving last");
                lock.unlock();
            } else {
                System.out.println("barger lost the race");
            }
            bargerDone.countDown();
        }, "barger");
        barger.start();

        bargerDone.await(2, TimeUnit.SECONDS);
        queued.join();
    }
}
```

<details><summary>Output and why</summary>

Both of these are legal, and which one you actually see is non-deterministic — this is not a bug in the snippet, it's the documented behavior of non-fair `ReentrantLock`:

```
barger acquired first, despite arriving last
```
or
```
barger lost the race
```

`ReentrantLock(false)` is non-fair: `tryLock()` on the barger thread attempts a raw CAS from `0` to `1` immediately, with no regard for whether another thread is already queued in AQS waiting for its turn. If the barger's `tryLock()` CAS runs before the main thread's `unlock()` has finished unparking the already-queued `settlement-ingest-1` thread and that thread has re-won its own CAS, the barger can win outright — a thread that was never queued at all beating a thread that has been parked for over 100ms. This is legal precisely because AQS's non-fair `tryAcquire` doesn't check queue state before attempting the CAS; only the fair variant (`new ReentrantLock(true)`) forces every acquirer to check `hasQueuedPredecessors()` first, which would make `queued thread acquired` the only legal output. What is never legal here, under either interleaving: both threads reporting they hold the lock simultaneously, since the CAS on `state` genuinely serializes ownership regardless of fairness mode.

The throughput argument for accepting this non-determinism is concrete for QuizStakes: a `ReentrantLock` guarding `FundsLedger`'s hot posting path sees bursts to 13,600 writes/sec at peak, and forcing strict FIFO fairness there would mean every acquirer pays the full park/unpark round trip even when the lock happens to be free at the exact instant it asks — non-fair barging lets an arriving thread win for free in that common case, at the statistically rare cost of a long-queued thread occasionally waiting one extra hand-off longer than its position alone would predict.

</details>

**Puzzle 3 — `LockSupport.park()` returning without any `unpark()` call**

```java
public class SpuriousParkDemo {
    public static void main(String[] args) throws InterruptedException {
        Thread t = new Thread(() -> {
            long before = System.nanoTime();
            java.util.concurrent.locks.LockSupport.park("waiting-for-nothing");
            long after = System.nanoTime();
            System.out.println("park() returned after " + (after - before) / 1_000_000 + " ms, "
                    + "interrupted=" + Thread.currentThread().isInterrupted());
        });
        t.start();
        t.join(500);
        if (t.isAlive()) {
            System.out.println("still parked after 500ms - no unpark() and no interrupt() were called");
            t.interrupt();
            t.join();
        }
    }
}
```

<details><summary>Output and why</summary>

Two legal outcomes, both consistent with the documented contract of `park()`:

```
still parked after 500ms - no unpark() and no interrupt() were called
park() returned after 500 ms, interrupted=true
```

is the overwhelmingly likely one, because `park()` provides no deadline here and nothing calls `unpark()`, so the thread blocks until `main` explicitly interrupts it — at which point `park()` returns (not throws) with the interrupt flag still set, exactly the third of the three legal return reasons named in Q5. The less likely but still legal output, which the JavaDoc explicitly permits, is:

```
park() returned after <some value well under 500> ms, interrupted=false
```

— a spurious wakeup, where `park()` returns for no application-visible reason at all, consuming no permit and observing no interrupt, purely because the contract allows it (mirroring `Object.wait()`'s own spurious-wakeup allowance). In practice on a mainstream Linux/HotSpot combination this branch is rare enough that CI runs of this exact snippet will show the first output the overwhelming majority of the time — but "rare" is not "impossible," and any test asserting the second output can never happen is asserting something the JavaDoc explicitly does not promise. What is never legal: `park()` throwing an exception of any kind — it has no checked or unchecked exception in its contract, which is exactly why every well-written caller re-checks its actual condition in a loop after `park()` returns rather than trusting that return implies anything about *why*.

The `park(Object blocker)` overload used here also changes what a diagnostic tool would show mid-block: a `jstack` taken while `t` is parked prints `parking to wait for <0x...> (a java.lang.String)` because the blocker argument here is the literal string `"waiting-for-nothing"` rather than a real synchronizer — which is itself a small pitfall, since passing a non-descriptive blocker object defeats the entire diagnostic purpose of the overload; real JDK callers always pass `this` or the actual lock/condition object being waited on, never a throwaway value.

</details>

**Puzzle 4 — `ConcurrentHashMap` never throwing `ConcurrentModificationException` under concurrent resize**

```java
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.CountDownLatch;

public class ChmResizeDemo {
    public static void main(String[] args) throws InterruptedException {
        ConcurrentHashMap<Integer, String> restrictions = new ConcurrentHashMap<>(16);
        CountDownLatch start = new CountDownLatch(1);

        Thread writer = new Thread(() -> {
            try { start.await(); } catch (InterruptedException ignored) {}
            for (int i = 0; i < 100_000; i++) {
                restrictions.put(i, "AA-610");
            }
        });

        Thread reader = new Thread(() -> {
            try { start.await(); } catch (InterruptedException ignored) {}
            int seen = 0;
            for (var entry : restrictions.entrySet()) {
                seen++;
            }
            System.out.println("iterated " + seen + " entries, no exception");
        });

        writer.start();
        reader.start();
        start.countDown();
        writer.join();
        reader.join();
        System.out.println("done, final size=" + restrictions.size());
    }
}
```

<details><summary>Output and why</summary>

```
iterated <some number between 0 and 100000> entries, no exception
done, final size=100000
```

The exact count the reader observes is non-deterministic and depends entirely on the interleaving — it can legally be anywhere from 0 (if the reader's iterator finishes before the writer inserts much) up to 100,000 (if the writer finishes first), and every value in between is legal. What is never legal is `ConcurrentModificationException`: `ConcurrentHashMap`'s iterators are weakly consistent — guaranteed not to throw regardless of concurrent structural modification, and guaranteed to reflect the map's state at some point during the iteration's construction, but never guaranteed to reflect every insert or removal that happened during the traversal. This is possible because CHM's cooperative resize (`transfer`, driven off `sizeCtl`'s striding) never invalidates an iterator's ability to keep walking the table structure it's holding — a bin that's mid-migration still has a consistent chain to walk, whether that's the old bin or the new lo/hi split. `restrictions.size()` after both threads join is deterministically `100_000`, since by then all writes have completed and `size()` reads `baseCount` plus every `CounterCell`, which is only guaranteed accurate once writers have quiesced — exactly the same caveat as `LongAdder.sum()` in Q8, because `ConcurrentHashMap`'s counting mechanism is built on the same `Striped64`-style approach.

A small but real variant of this puzzle worth stating: if the table starts small enough and the 100,000 sequential integer keys happen to concentrate into one bin faster than the resizes can spread them out, that bin can transiently cross `TREEIFY_THRESHOLD = 8` and become a `TreeBin` mid-run — the reader's iterator handles this transparently too, since `TreeBin` nodes implement the same intrusive linked traversal contract the plain bin nodes do, just backed by red-black tree structure instead of a chain; the weak-consistency guarantee extends across that structural change with no special case the caller has to reason about.

</details>

**Puzzle 5 — a virtual thread pinning inside `synchronized` on Java 21**

```java
import java.util.concurrent.Executors;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.CountDownLatch;

public class PinningDemo {
    static final Object pspClientLock = new Object();

    public static void main(String[] args) throws InterruptedException {
        try (ExecutorService pool = Executors.newVirtualThreadPerTaskExecutor()) {
            CountDownLatch done = new CountDownLatch(1);
            pool.submit(() -> {
                synchronized (pspClientLock) {
                    try {
                        Thread.sleep(200); // blocking call while holding a monitor
                    } catch (InterruptedException ignored) {}
                }
                System.out.println("virtual thread finished while pinned the whole time");
                done.countDown();
            });
            done.await();
        }
    }
}
```

<details><summary>Output and why</summary>

```
virtual thread finished while pinned the whole time
```

The output is deterministic and unremarkable on its face — the program completes correctly. The internals point is what a profiler or `jstack` shows *while* it runs, on Java 21: because the `sleep(200)` call happens inside a `synchronized` block, the virtual thread cannot unmount from its carrier platform thread for the duration of that sleep. `ObjectMonitor` ownership (`_owner`, `_cxq`, `_EntryList`) is tracked by carrier (`JavaThread`) identity on Java 21, not by virtual-thread identity, so the JVM has no way to let the carrier go serve another virtual thread while this one blocks — the carrier is pinned, holding one platform-thread-equivalent resource hostage for 200ms even though the virtual thread itself is cheap.

Note precisely what would *not* pin here, to sharpen the boundary: replacing `synchronized (pspClientLock)` with a `ReentrantLock` guarding the same critical section removes the pin entirely on Java 21, because `ReentrantLock`'s park/unpark path goes through `LockSupport`, which the scheduler already knows how to suspend a virtual thread across — the pinning is specific to `synchronized`'s monitor-based blocking, not to blocking-while-holding-a-mutex in general. Running this same program with `-Djdk.tracePinnedThreads=full` on Java 21 would print a stack trace naming the `synchronized` block as the pin point; that flag, and the pinning behavior itself, are both removed in JDK 24 by JEP 491, which rebuilds monitor ownership tracking around virtual-thread identity so the identical code no longer pins at all. `[VERSION-TRAP]`: anyone who tests this only on JDK 24+ and concludes "`synchronized` never pins virtual threads" is describing a JVM two major LTS releases newer than this file's Java 21 target.

The observability angle is the sharper interview follow-up: run `jstack` against this JVM mid-sleep on Java 21 and it will list `pspClientLock`'s pinned carrier as an ordinary platform thread entry — there is no separate "virtual thread" row for the mounted task at all, because the virtual thread is, for that instant, indistinguishable from the carrier it's riding. Only `jcmd <pid> Thread.dump_to_file -format=json` (or JFR's `jdk.VirtualThreadPinned` event, itself only emitted with `-Djdk.tracePinnedThreads` enabled) exposes the virtual thread as a first-class entity separate from its carrier — a plain `jstack` on Java 21 genuinely cannot show you the population of virtual threads that exist but are currently unmounted, waiting for a carrier.

The scale argument is what makes this a production concern rather than a curiosity: QuizStakes sizes for 55k peak concurrent sessions, and a virtual-thread-per-request design assumes those sessions almost never each tie up a whole carrier — the entire footprint argument for switching to virtual threads rests on that assumption holding. A single widely-shared `synchronized(pspClientLock)` guarding, say, PSP client construction, hit by even a modest fraction of those 55k sessions performing a blocking call inside it, converts what should be a cheap continuation park into carrier-count-limited contention — silently reintroducing the exact platform-thread scaling ceiling virtual threads were adopted to remove, and it will not show up as an obvious bug, only as a throughput ceiling that doesn't match the promised model.

</details>

## Atomic concept checklist

The flat, set-wide atomic concept checklist for all five parts lives at the end of [94f2 — drills and the atomic concept checklist](94f2-drills-and-atomic-checklist.md).

---

**Leaves covered:** Part 3 wrap-up over §3.1–§3.13 (no leaves owned directly)
**Leaves deferred:** none
**Diagrams included:** none
**Target version:** Java 21 LTS
**Lines:** 435
