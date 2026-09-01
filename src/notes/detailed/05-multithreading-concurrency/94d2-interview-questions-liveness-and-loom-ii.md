# 05 Multithreading and Concurrency — Interview questions: Loom — INTERVIEW (§5.1, questions 5.1.104–5.1.115)

**Target version: Java 21 LTS.** | **Part 5 of 5** | [Index](00-index.md)
Previous: [Interview questions: liveness and diagnostics](94d-interview-questions-liveness-and-loom.md) · Next: [Interview questions: design and judgement](94e-interview-design-and-judgement.md)

---

### 5.1.104 What is a virtual thread and where does its stack live.

A virtual thread is a `Thread` instance the JVM schedules itself, rather than the OS scheduling it — `Thread.ofVirtual().start(task)` returns a real `Thread` object, same public API surface as always, but it is not backed 1:1 by an OS thread.

- Its stack is **not** a fixed-size native stack the OS reserves up front the way a platform thread's is.
- It is a small, resizable, heap-allocated `StackChunk` object that grows and shrinks as the virtual thread's call depth changes.
- It starts at a few hundred bytes, versus the roughly 512 KB–1 MB a platform thread's OS stack reserves before a single byte of business logic has run.

That footprint difference is the entire reason a JVM can host hundreds of thousands of virtual threads where it could host at most a few thousand platform threads: the cost per idle virtual thread is a small heap object, not a reserved OS stack plus a kernel scheduling entity.

This shop's peak of **55,000 concurrent sessions** is the canonical case for the footprint argument:

- One virtual thread per session at a few hundred bytes each is single-digit megabytes total.
- One platform thread per session at ~1 MB reserved stack each is tens of gigabytes of address space committed before any business logic runs at all.

**Follow-up:** does the virtual thread's `Thread` object itself live on the heap the whole time?
Yes — the `Thread` object and its `StackChunk` are ordinary heap objects, garbage collected like anything else once nothing references the (terminated) virtual thread; there is no separate native handle to leak if you forget to close something.

> A virtual thread is a `Thread` scheduled by the JVM onto a pool of OS carrier threads, with its call stack held as a small, resizable, heap-allocated `StackChunk` instead of a fixed native stack.

Creating and starting one is deliberately unremarkable — the point is that it looks exactly like ordinary `Thread` code:

```java
Thread sessionThread = Thread.ofVirtual()
        .name("client-session-", 0)
        .start(() -> handleSession(session));
sessionThread.join();
```

`Thread.ofVirtual()` returns a builder; `.start(Runnable)` creates and starts the virtual thread in one call. Nothing here differs syntactically from `Thread.ofPlatform()` except the factory name — which is exactly the design goal: existing blocking, thread-shaped code should port with a one-line executor or thread-factory change, not a rewrite.

**Version note:** virtual threads themselves were finalized in **Java 21 under JEP 444** (preceded by JEP 425 and 436 as earlier previews/incubations) — this is the one Loom feature that is *not* a version trap for the 21 baseline; treat it as fully final, stable API from day one of the LTS.

### 5.1.105 What is mounting and unmounting.

**Mounting** is a virtual thread being assigned to an OS carrier thread so it can actually execute:

- The carrier's native stack briefly becomes the virtual thread's execution context.
- The virtual thread's own heap-based `StackChunk` holds the continuation state for everything above that point.

**Unmounting** is the reverse. When the virtual thread would otherwise block — a socket read, `Lock.lock()`, `Thread.sleep()`, a blocking-queue `take()` — the JVM instead:

1. Captures the running continuation via `Continuation.yield`.
2. Detaches it from the carrier and stores it in the `StackChunk`.
3. Frees the carrier to mount a *different* runnable virtual thread.

When the blocking operation completes, the virtual thread is re-mounted onto some carrier — not necessarily the same one it started on — and resumes exactly where it left off, at the exact point `Continuation.yield` returned. From the programmer's point of view the *virtual* thread blocked; from the OS's point of view the *carrier* thread never blocked at all — it went and ran something else.

**Insight:** this is precisely why writing "async-style" code with callbacks and `CompletableFuture` chains stops paying for itself once you have Loom — blocking, straight-line code gets the same carrier-thread efficiency for free, without the readability cost of the callback style.

**Follow-up:** what data actually moves at a mount/unmount boundary?
Just the continuation's frame data inside the `StackChunk` plus scheduler bookkeeping — no OS context switch, no kernel involvement. That is why mount/unmount is order-of-magnitude cheaper than an OS thread context switch, though **no authoritative per-instruction cost table exists** to cite a specific number against, so state this as an order-of-magnitude claim, never a measured constant.

The single fact worth memorizing here, because it's the sharpest edge in the whole topic and 5.1.111 hinges on it:

| Blocking operation | Unmounts the virtual thread? | Mechanism |
|---|---|---|
| Socket read/write | Yes | Kernel-backed poller (`epoll`/`kqueue`) notifies the scheduler when ready |
| `Thread.sleep(...)` | Yes | Scheduled wakeup, no carrier held meanwhile |
| `Lock.lock()` / `Semaphore.acquire()` | Yes | Parks via `LockSupport`, same continuation-yield path |
| `synchronized` block (Java 21) | **No — pins** | Monitor tied to the carrier's native frame (5.1.107) |
| `synchronized` block (Java 24+) | Yes | JEP 491 removed the pin |
| File I/O on Linux | **No — pins** | No poller integration for the filesystem; the carrier is consumed for the syscall's duration |
| Native / JNI / FFM call | **No — pins** | No continuation-capture mechanism exists on the native stack, on any version |

Sockets and file I/O look identical from the calling code — both are just "a blocking read call" — but only one of them actually frees its carrier. That asymmetry is the single most-tested fact in this material.

### 5.1.106 What is the virtual-thread scheduler and how is it sized.

The scheduler that decides which carrier thread runs which runnable virtual thread is a dedicated `ForkJoinPool`, run in **FIFO async mode** — not the default work-stealing LIFO mode `ForkJoinPool` uses for `parallelStream()` and the common pool.

FIFO matters here specifically because virtual-thread tasks are typically request-response work, where fairness across many short-lived tasks beats depth-first throughput on a handful of long ones.

Two independent sizing knobs:

| Property | Governs | Default |
|---|---|---|
| `jdk.virtualThreadScheduler.parallelism` | Number of carrier threads actively running virtual threads | `Runtime.getRuntime().availableProcessors()` |
| `jdk.virtualThreadScheduler.maxPoolSize` | Total carrier threads the pool can ever create, including ones parked to compensate for pinning | `Integer.max(parallelism, 256)` |

`maxPoolSize` exists because a pinned virtual thread (5.1.107) occupies its carrier for the duration of the pin; the scheduler compensates by creating additional carrier threads up to `maxPoolSize` so pinning doesn't starve every other runnable virtual thread of a carrier to run on.

**Pitfall:** confusing `maxPoolSize` with a concurrency limit on your business logic. It caps carrier *threads*, and a virtual thread that is unmounted — blocked on I/O — does not occupy a carrier at all, so this knob does nothing to bound, say, concurrent outbound calls to the card PSP; that is 5.1.109's job entirely.

```java
System.setProperty("jdk.virtualThreadScheduler.parallelism", "8");
System.setProperty("jdk.virtualThreadScheduler.maxPoolSize", "512");
```

Both properties must be set before the scheduler's `ForkJoinPool` is first created — typically before any virtual thread is started — since the pool reads them once at construction and does not reconfigure itself afterward.

**Follow-up:** would raising `parallelism` above `availableProcessors()` help a CPU-bound virtual-thread workload?
No — raising it past the physical core count just adds oversubscription and context-switch overhead for CPU-bound work, exactly as it would for a platform-thread pool; the parallelism knob is for tuning how many carriers exist, not a lever that manufactures more CPU. It helps only workloads where carriers themselves become the bottleneck due to unusually long CPU-bound stretches between blocking points.

### 5.1.107 What is pinning, what caused it in Java 21, and what changed in Java 24.

Pinning is a virtual thread that **cannot unmount** while blocked, because it is holding something the JVM cannot safely detach from a carrier mid-block.

On **Java 21**, the dominant cause is `synchronized`:

- Entering a `synchronized` block or method captures the monitor at the OS-thread level — the JVM's monitor implementation is tied to the carrier's native frame.
- A virtual thread blocked *inside* a `synchronized` block on, say, a slow downstream call keeps its carrier pinned for the entire block.
- That defeats the point of Loom for that stretch of code — the carrier can't go run anything else while the pin holds.

Native, JNI, and FFM (Foreign Function & Memory) frames pin on **every** version, because native code has no continuation-capture mechanism at all — there is no `StackChunk` equivalent on the native stack side. On Java 21 the diagnostic is `-Djdk.tracePinnedThreads=full` (or `short`), which logs the offending stack whenever a pin actually blocks long enough to matter.

**`[VERSION-TRAP]`** JEP 491, *"Synchronize Virtual Threads without Pinning,"* is final and shipped in **JDK 24** — `synchronized` no longer pins on 24+, and `-Djdk.tracePinnedThreads` was **removed along with the problem it diagnosed**. Native, JNI, and FFM frames still pin on 24+; that cause was never `synchronized`-specific and JEP 491 doesn't touch it.

On Java 21, the practical fix is what it was before Loom shipped `synchronized` support at all: swap the hot `synchronized` block for a `java.util.concurrent.locks.ReentrantLock`, which parks — and lets the virtual thread unmount — instead of monitor-blocking.

**Follow-up:** why doesn't the fix matter as much once you're on 24?
It still matters for native/JNI/FFM code paths, but for ordinary `synchronized`-guarded Java code, the whole class of pinning bugs this shop would have hit protecting a `synchronized`-guarded in-memory restriction cache under virtual threads simply stops existing.

The **broken** Java 21 version and its fix, side by side:

```java
// broken on Java 21 — pins the carrier for the whole synchronized block
synchronized Restrictions lookup(ClientId clientId) {
    return restrictionsCache.computeIfAbsent(clientId, this::loadFromDatabase);
}
```

```java
// fixed for Java 21 — ReentrantLock parks instead of monitor-blocking
private final ReentrantLock cacheLock = new ReentrantLock();

Restrictions lookup(ClientId clientId) {
    cacheLock.lock();
    try {
        return restrictionsCache.computeIfAbsent(clientId, this::loadFromDatabase);
    } finally {
        cacheLock.unlock();
    }
}
```

On Java 24+ the first version is no longer a bug at all — JEP 491 makes `synchronized` unmount-safe — but writing the `ReentrantLock` version is still the safer default for code that has to run correctly on both 21 and 24, since it behaves identically (correctly) on either.

The trace `-Djdk.tracePinnedThreads=full` produces on Java 21 when the broken version actually pins:

```
Thread[#31,client-session-4,5,main]
    java.base/java.lang.Thread.dumpStack(Thread.java:1626)
    java.base/java.lang.VirtualThread.print(VirtualThread.java:...)
    RestrictionCache.lookup(RestrictionCache.java:12) <== monitor
```

The `<== monitor` marker on the frame is the tell — it names the exact `synchronized` call site responsible, which is why this flag was the primary Java 21 diagnostic tool before JEP 491 removed the problem it existed to find.

### 5.1.108 Why should you never pool virtual threads.

Pooling exists to amortize the cost of creating an expensive resource. For platform threads, that cost is real: a reserved native stack and an OS scheduling entity, genuinely expensive to create and destroy per task.

A virtual thread's cost is a small heap object — creating one is closer to allocating an object than to a `pthread_create` syscall, so there is nothing expensive left to amortize, and pooling actively removes the property you wanted Loom for in the first place:

- A pool caps concurrency at its size — exactly the platform-thread behavior of "only N requests in flight" that virtual threads exist to escape.
- The entire pitch of Loom is one virtual thread per logical task, however many tasks that turns out to be.
- Pooling virtual threads reintroduces the `ThreadLocal` leak shape from 5.1.102 — a long-lived pooled virtual thread accumulating stale `ThreadLocal` entries across tasks — for zero benefit, since the thing you'd normally pool to save (thread creation cost) was never expensive here.

**Pitfall:** wrapping `Executors.newVirtualThreadPerTaskExecutor()`'s output in a fixed-size pool "to be safe." That executor already creates one virtual thread per submitted task and discards it on completion; adding a pool on top just caps concurrency for no savings, and adds back the leak risk it was designed to avoid.

**Wrong**, the reflex carried over from platform-thread habits:

```java
ExecutorService platformStylePool =
        Executors.newFixedThreadPool(200, Thread.ofVirtual().factory());
```

This compiles and runs, and looks reasonable at a glance, but `newFixedThreadPool` recycles 200 long-lived worker threads — here virtual ones — across every submitted task, which is exactly the pooling model 5.1.108 argues against.

**Right**:

```java
ExecutorService perTask = Executors.newVirtualThreadPerTaskExecutor();
```

One virtual thread per task, created and discarded per submission, with concurrency bounded by whatever explicit gate (5.1.109) the downstream resource actually needs — not by an arbitrary pool size chosen to mimic platform-thread capacity planning that no longer applies.

### 5.1.109 How do you limit concurrency once you have virtual threads.

Not with pool size — with an explicit concurrency gate, because virtual threads decouple "how many logical tasks are in flight" from "how many OS resources that costs."

The standard tool is a `Semaphore` sized to the *downstream* resource's real limit, acquired before the constrained call and released after:

```java
private final Semaphore pspConcurrency = new Semaphore(64);

Money authorise(WithdrawalTransaction withdrawal) throws InterruptedException {
    pspConcurrency.acquire();
    try {
        return cardPayments.authorise(withdrawal);
    } finally {
        pspConcurrency.release();
    }
}
```

This bounds concurrent calls into the card PSP to 64 regardless of how many virtual threads are attempting withdrawals — the semaphore park unmounts the waiting virtual thread cheaply, so a burst of 5,000 concurrent withdrawal requests just queues on the semaphore without costing 5,000 carrier threads or 5,000 OS threads.

The same pattern applies to the ledger connection pool: HikariCP's 20-connection limit is already this kind of gate, and it works unchanged under virtual threads, because the gate is a semaphore-like structure, not a thread count.

**Follow-up:** would a `RateLimiter` (token bucket) be better than a raw `Semaphore` here?
For a hard concurrency ceiling — "the PSP will 503 us past 64 concurrent connections" — a semaphore is the right primitive. A token-bucket limiter is for a *rate* ceiling (calls per second), a different constraint that a semaphore alone doesn't express; the two compose when both limits are real.

**Second follow-up:** does `Executors.newVirtualThreadPerTaskExecutor()` need its own concurrency limit as well, separate from the semaphore?
Not usually — the executor itself doesn't need bounding, because it isn't the scarce resource; the downstream call is. Bounding the executor would just re-introduce the pooling anti-pattern from 5.1.108 for no reason, when the semaphore already protects the thing that actually has a limit.

### 5.1.110 Why don't virtual threads appear in `jstack`, and what do you use instead.

`jstack` walks the JVM's registered **platform** threads and reads their native stacks — it predates Loom entirely and has no concept of an unmounted virtual thread, which at that moment is nothing but a heap object with no OS thread backing it to walk.

- A virtual thread only becomes visible to a platform-thread-oriented tool for the brief window it's actually mounted on a carrier.
- Even then it shows up as if it were the carrier, not as its own named entity.

The tool built for this is `jcmd <pid> Thread.dump_to_file -format=json`, which asks the JVM runtime directly for every live thread — mounted or not, virtual or platform — and emits it as structured JSON rather than the old text format.

**The tradeoff is real, not cosmetic: the JSON dump omits lock-ownership detail and JNI stack information** that the old-style dump carried. You get thread state and stack, not the full monitor-ownership graph, so a deadlock purely among unmounted virtual threads is *visible* — you can see both stacks — but not *automatically diagnosed* as a cycle the way `jstack`'s `"Found one Java-level deadlock"` banner was.

**Pitfall:** running plain `jstack` on a Loom-heavy service and concluding "there's nothing wrong, thread count looks fine." You're seeing carrier-thread count, bounded near `availableProcessors()`, not the actual concurrency of virtual threads in flight — which could be in the tens of thousands and entirely invisible to that tool.

**Follow-up:** does JFR (Java Flight Recorder) fill the JSON dump's gap on lock ownership?
Partially — JFR's `jdk.VirtualThreadPinned` and thread-park events give you pinning and blocking duration over time, which the point-in-time JSON dump doesn't, but neither tool reconstructs the full monitor-ownership graph the old `jstack` deadlock detector built for platform threads.

The documented JSON dump shape, reproduced — this is the format `jcmd Thread.dump_to_file -format=json` writes, not a live capture:

```json
{
  "threadDump": {
    "threads": [
      {
        "tid": "0x2a1",
        "name": "",
        "virtual": true,
        "state": "WAITING",
        "stack": [
          "java.base/java.lang.VirtualThread.parkOnCarrierThread(VirtualThread.java:...)",
          "CardPayments.authorise(CardPayments.java:44)",
          "PaymentService.processWithdrawal(PaymentService.java:71)"
        ]
      }
    ]
  }
}
```

Note `"virtual": true` and the empty `"name"` — virtual threads are typically unnamed unless the code explicitly names them via `Thread.ofVirtual().name(...)`, which is itself a good operational habit once this JSON format is your primary diagnostic tool.

### 5.1.111 What is the most common surprise after migrating to virtual threads.

Pinning-driven throughput collapse under load that doesn't show up in a smoke test:

- A service migrates its request-handling threads to virtual threads.
- It passes functional testing fine, because concurrency is low in that environment.
- It falls over in production because a `synchronized` block guarding, say, an in-memory `ClientRestrictions` cache — previously fine on platform threads because it was held for microseconds — now pins its carrier for the duration of every blocking call made *inside* that block, by any virtual thread that happens to acquire it under real concurrency.
- Effective parallelism collapses toward the fixed carrier-pool size.

The second most common surprise is the file I/O caveat: **sockets unmount cleanly through a poller, but file I/O on Linux does not.** A virtual thread doing blocking file reads or writes consumes its carrier for the duration, exactly like a platform thread would. A service that assumed "virtual threads mean everything is now cheap and non-blocking" gets no benefit on its file-heavy code paths — writing audit log entries to disk per transaction, for instance — and can still exhaust carriers under load there.

**Follow-up:** how would you find the pinning collapse in staging before production sees it?
Run with `-Djdk.tracePinnedThreads=full` (Java 21 only — removed in 24 per 5.1.107) under a realistic *concurrent* load test, not a functional smoke test, and grep the log for pin events on the hot request path.

**Second follow-up:** why doesn't a smoke test catch this?
A smoke test typically runs one or a handful of requests at a time, so the `synchronized` block is never actually contended — pinning only *matters* when a carrier that's pinned is also needed by other runnable virtual threads, which requires real concurrency to manifest as a throughput problem rather than a silent, harmless pin.

A third surprise worth naming, smaller but real: thread-count-based monitoring dashboards stop meaning what they used to. A dashboard built around "platform thread count near pool max means we're saturated" reports a flat, low, uninteresting carrier count under Loom regardless of how many virtual threads — and therefore how much real request concurrency — are actually in flight; the useful signal moves to virtual-thread count and semaphore/queue depth on the actual concurrency gates from 5.1.109, not carrier count.

A fourth, subtler surprise: interrupting a virtual thread that's pinned inside a `synchronized` block on Java 21 behaves like interrupting a platform thread stuck the same way — the interrupt is delivered but has no effect until the thread reaches an interruptible point, which a pinned thread stuck on a slow downstream call inside `synchronized` may never do in time. Teams that lean on `Thread.interrupt()` as their cancellation mechanism under a tight SLA discover this only once real pinning happens under load, since it is invisible in any test that never actually contends the pin.

### 5.1.112 Do virtual threads make code faster? (Scale, not speed.)

No — and this is the single most load-bearing sentence to get right in an interview.

- A single request handled by one virtual thread does not complete any faster than the same request on a platform thread.
- The CPU work is identical.
- The downstream call latencies are identical — the card PSP's p50 of 240 ms is 240 ms either way.
- A virtual thread that is mounted and actually running competes for the same CPU cores as everything else.

What changes is **how many** requests the JVM can have in flight *concurrently* without the memory and OS-scheduling cost of one platform thread per request. Little's law makes the payoff concrete:

- At 1,200 stake reservations/sec against the PSP's 240 ms p50, Little's law says roughly **288** concurrent in-flight calls are needed just to keep up (1,200 × 0.24 = 288).
- At the PSP's 11 s p99, that number jumps to roughly **13,200** concurrent in-flight calls during a tail-latency spike (1,200 × 11 = 13,200).

A platform-thread-per-request model would need to reserve stack for 13,200 OS threads to survive that spike without rejecting work. A virtual-thread model needs 13,200 small heap objects and however many carrier threads — roughly `availableProcessors()` — can keep the CPU-bound slices of that work moving.

**Insight:** virtual threads buy you *headroom under concurrency* — specifically the ability to hold many blocked, waiting requests cheaply. They do not buy you lower latency, higher CPU throughput, or a faster PSP.

The Little's law arithmetic, worked explicitly:

```
concurrency = arrival_rate × latency

p50 case:  1,200 req/sec × 0.24 sec  =   288 concurrent in-flight calls
p99 case:  1,200 req/sec × 11.0 sec  = 13,200 concurrent in-flight calls
```

At the p50 figure, 288 platform threads is well within reach of most JVM configurations — the argument for Loom is weak here. At the p99 figure during a tail-latency spike, 13,200 platform threads at ~1 MB reserved stack each is roughly 13 GB of address space committed to threads that are doing nothing but waiting — that is the regime where virtual threads change what's operationally survivable, not the steady-state p50 case.

That gap between the p50 and p99 regimes is also the honest answer to "why do this at all if p50 already works fine" — a system sized for p50 concurrency on platform threads falls over exactly during the tail-latency spikes it most needs to survive, which is precisely when the PSP is already struggling and load is backing up.

**Pitfall:** benchmarking a single-threaded, no-contention microbenchmark and concluding virtual threads are "slower," because mount/unmount adds a small fixed overhead per blocking call versus a platform thread's direct OS block. True, and irrelevant — that overhead is amortized away at any real concurrency level where it's actually competing against reserving gigabytes of stack for threads.

**Follow-up:** does GC pause behavior change under virtual threads, given how many more `Thread` objects exist?
Not fundamentally — `StackChunk` objects are ordinary heap objects subject to the same generational GC as everything else, and modern collectors (G1, ZGC) already scale to large object counts; the practical effect is more heap pressure from many small objects rather than a change in GC algorithm behavior, and it is a real capacity-planning input, not a correctness concern.

### 5.1.113 What problem does structured concurrency solve that `CompletableFuture` does not.

`CompletableFuture` composes concurrent work but has no structural guarantee that a child task's lifetime is bounded by its parent's:

- You can fire off `supplyAsync` calls freely.
- If the parent method returns — or throws — without every future being joined, cancelled, or otherwise accounted for, those tasks keep running orphaned.
- There is no propagated cancellation and no owner for errors that surface, if at all, somewhere disconnected from the call site that spawned them.

Structured concurrency (`StructuredTaskScope`, still preview) enforces the rule directly in the API shape:

1. Every forked subtask is a child of the scope it was forked in.
2. The scope's `join()` blocks until all children complete.
3. If the scope exits — including exceptionally — every still-running child is interrupted before control returns to the caller.

Concretely: fanning out a `WithdrawalTransaction` authorisation to the card PSP and a fraud-screening call concurrently, then failing the whole authorisation the instant either one fails, is exactly what `StructuredTaskScope.ShutdownOnFailure` expresses directly. With `CompletableFuture` you'd hand-roll the cancellation propagation and the try/finally hygiene to make sure the loser doesn't keep running after the winner — or the failure — is already handled.

**Pitfall:** describing structured concurrency as "just a nicer `CompletableFuture` API." The nicer syntax is real but incidental; the load-bearing property is the structural guarantee that no child task can outlive the scope that created it — that is what closes the orphaned-task class of bug, not the syntax.

**Follow-up:** does `StructuredTaskScope` replace `CompletableFuture` entirely?
No — `CompletableFuture` is still the right tool for pipeline-shaped async composition (`thenApply`, `thenCompose`) where there's no natural fork/join structure; structured concurrency targets the specific shape of "spawn N children, wait for all or the first failure, then close," which `CompletableFuture` can express but doesn't enforce.

The fan-out itself, on Java 21 with `--enable-preview` — API shape as of the early previews current at 21, noted as preview throughout:

```java
Money authoriseWithScreening(WithdrawalTransaction withdrawal) throws Exception {
    try (var scope = new StructuredTaskScope.ShutdownOnFailure()) {
        Supplier<Money> psp = scope.fork(() -> cardPayments.authorise(withdrawal));
        Supplier<ScreeningVerdict> screening = scope.fork(() -> screeningService.check(withdrawal));

        scope.join();
        scope.throwIfFailed();

        if (screening.get() instanceof ScreeningVerdict.Blocked blocked) {
            throw new RestrictedActionException(blocked.reason());
        }
        return psp.get();
    }
}
```

`scope.join()` blocks for both forked tasks; `scope.throwIfFailed()` propagates the first failure and — because of `ShutdownOnFailure` — has already interrupted whichever task hadn't finished yet. Compare that to the `CompletableFuture` equivalent, which needs manual `.exceptionally()` wiring on *both* futures plus explicit `.cancel(true)` calls to get the same shutdown-on-failure behavior, and still won't interrupt a task blocked inside a non-cooperative call the way structured concurrency's scope-exit interruption is designed to.

### 5.1.114 `ScopedValue` versus `ThreadLocal`.

| | `ThreadLocal` | `ScopedValue` |
|---|---|---|
| Mutability | Mutable — `set()` any time | Immutable within a binding — bound once via `where(...).run(...)`, no `set()` |
| Lifetime | Until `remove()` or thread death | Exactly the dynamic extent of the `run`/`call` block |
| Pool leak risk | Yes — the 5.1.102 leak | No — value is unbound automatically when the block exits, nothing to forget |
| Propagation to children | Only `InheritableThreadLocal`, snapshot at construction (5.1.103) | Structurally inherited by tasks forked inside the block from a `StructuredTaskScope`, no copy step |
| Cost per virtual thread | One `ThreadLocalMap` entry per thread, unbounded growth | Designed for cheap binding at massive virtual-thread scale — no per-thread map to leak |

`ScopedValue` fixes the propagation gap 5.1.103 named directly: instead of a value copied once at thread-construction time, it's bound for the exact duration of a call and visible to everything structurally nested inside that call — including forked structured-concurrency children — with no `set`/`remove` bookkeeping and therefore no leak surface at all.

```java
private static final ScopedValue<ClientId> CURRENT_CLIENT = ScopedValue.newInstance();

void handle(WithdrawalTransaction withdrawal) {
    ScopedValue.where(CURRENT_CLIENT, withdrawal.clientId())
            .run(() -> processWithdrawal(withdrawal));
}

void processWithdrawal(WithdrawalTransaction withdrawal) {
    ClientId client = CURRENT_CLIENT.get(); // visible anywhere nested inside run()
    audit(client, withdrawal);
}
```

**`[VERSION-TRAP]`** on Java 21, `ScopedValue` is preview (`--enable-preview` required); **it reaches final status in Java 25 under JEP 506** — treat it as preview-only for any Java 21 production claim, and don't state it as shipped-and-stable on 21 in an interview answer.

**Follow-up:** why can't you just call `CURRENT_CLIENT.get()` from a completely unrelated thread the way `ThreadLocal` might accidentally let you if propagation were wired up wrong?
Because `ScopedValue.get()` throws `NoSuchElementException` outside an active `where(...).run(...)` binding for that instance — there is no ambient global state to accidentally read, which is the exact class of cross-task leak 5.1.102 describes for `ThreadLocal`, closed by construction.

**Second follow-up:** can a `ScopedValue` binding be rebound partway through, the way `ThreadLocal.set()` can be called again mid-thread?
Not in place — `ScopedValue.where(...)` establishes a fresh, nested binding scoped to its own `run`/`call` block; calling it again inside that block shadows the outer binding for the nested block's duration only, and the outer value reappears once the nested block exits. There is no operation that mutates an existing binding, which is precisely the immutability property that makes it safe to hand to forked structured-concurrency children without defensive copying.

### 5.1.115 Is structured concurrency final yet? (No — say which JEP and which release.)

No. As of Java 25, structured concurrency is still in **preview** — JEP 505, the fifth preview round for the feature, following JEP 428, 437, 453, and 480. The API shape has genuinely changed across those previews, not just the preview flag toggling on and off.

Do not describe it as final, and do not conflate it with `ScopedValue`, which *did* reach final status — under JEP 506 — in Java 25. The two features shipped in the same JDK generation on different tracks: one final, one still preview.

| Feature | JEP | Status by Java 25 |
|---|---|---|
| Virtual threads | 444 | Final (Java 21) |
| Synchronize virtual threads without pinning | 491 | Final (Java 24) |
| Scoped values | 506 | Final (Java 25) |
| Structured concurrency | 505 (5th preview) | Still preview |

This table is the single artifact worth memorizing out of the entire Loom topic area: every row's JEP number and final-vs-preview status, cold, because interviewers use exactly this confusion — virtual threads final, pinning fix final, scoped values final, structured concurrency *not* final — to separate candidates who tracked the actual release notes from candidates who absorbed a "Loom is done now" impression from a conference talk given mid-preview.

**Interview:** "scoped values are final in 25 under JEP 506; structured concurrency is still preview in 25 under JEP 505" is the exact sentence to have ready. Stating a specific JEP number for each — not just "one's done and one isn't" — is what separates a candidate who read the release notes from one who read a blog summary.

**Follow-up:** if structured concurrency is still preview, is it safe to use in this shop's production code today, on Java 21?
Preview features require `--enable-preview` at both compile and run time, which ties the running JVM to an exact preview API shape that has already changed across five iterations — using it in production on Java 21 means committing to a migration every time the preview shape shifts, which is a real cost to weigh against the orphaned-task bug class it closes.

**Second follow-up:** what actually changed in the API shape across the five previews, at a high level?
Class and method names moved (`StructuredTaskScope.open()` factory-style construction was introduced in later previews alongside the constructor-based form shown in 5.1.113's example), and the join/error-handling policy classes (`ShutdownOnFailure`, `ShutdownOnSuccess`) were refined for clarity — the structural guarantee itself (children bounded by scope lifetime) has been stable since the first preview; it's the surrounding ergonomics that kept moving, which is exactly why pinning a specific JDK's preview shape into production code is risky.

**Third follow-up:** given all that, what's the honest recommendation for this shop's `WithdrawalTransaction` authorisation fan-out today, on Java 21?
Ship the `CompletableFuture`-based version with hand-rolled cancellation for anything customer-facing in production now, and keep the `StructuredTaskScope` version (5.1.113) as the target to migrate to once the feature finalizes — tracking it in code as a known, deliberate technical-debt item rather than either ignoring structured concurrency entirely or taking on a preview-API dependency in a payments-adjacent code path.

---

**Leaves covered:** 5.1.104–5.1.115 (12 questions)
**Leaves deferred:** none
**Diagrams included:** none
**Target version:** Java 21 LTS
**Lines:** 420
