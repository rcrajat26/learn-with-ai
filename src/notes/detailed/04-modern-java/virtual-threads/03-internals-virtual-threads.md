# 04 Modern Java — Virtual threads — INTERNALS (§3.14)

**Target version: Java 21 LTS.** | **Part 3 of 5** | [Index](../00-index.md)
Previous: [Virtual threads — in production](02-in-production.md) · Next: [Structured concurrency — basics](../structured-concurrency/01-basics.md)

Everything in the earlier parts of this guide — "virtual threads are cheap", "the scheduler
mounts them onto carriers", "some calls pin" — was usage-level vocabulary. This file opens the
box. By the end you should be able to draw the object graph that a blocked virtual thread leaves
behind, quote the actual `ForkJoinPool` constructor call that creates the default scheduler, and
say precisely which Java release changed which pinning behaviour and why.

## The three-layer hierarchy, before any detail

| Layer | Type | Responsibility |
|---|---|---|
| Task | `java.lang.VirtualThread` | The `Thread` subclass the application code holds a reference to. Owns the nine-state lifecycle. |
| Suspension mechanism | `jdk.internal.vm.Continuation` | A resumable computation. Knows how to `yield()` out of the middle of a call stack and `run()` back into it. |
| Execution resource | `ForkJoinPool` (FIFO/async mode) scheduler, backed by **carrier** platform threads | Decides which continuation runs on which OS thread, and when. |

`![D-159 — The three layers of a virtual thread](../diagrams/D-159-three-layers-virtual-thread.svg)`

**D-159** — The three layers of a virtual thread

Read the diagram top to bottom, not as three independent classes but as three
layers of *indirection over one call stack*. `VirtualThread` is the identity and the
public API surface — `start()`, `interrupt()`, `getState()`. `Continuation` is the
mechanism that can stop that call stack mid-frame and hand it back later.
`ForkJoinPool` is the thing that decides *when* "later" is. `Thread.currentThread()`
called from inside a virtual thread returns the `VirtualThread` object, never the
carrier — the carrier is reachable only through JDK-internal API
(`jdk.internal.misc.CarrierThread`), which is a deliberate encapsulation: application
code that pins to carrier identity would silently break every time the scheduler's
tuning changed.

---

## Concept 1 — `Continuation`: mount/unmount and the heap-resident `StackChunk`

**Mental model.** A `Continuation` is a call stack that has learned to detach itself
from a physical OS thread and live in the heap as ordinary data, then reattach to a
(possibly different) OS thread and keep running exactly where it left off — like a
tape you can pull out of one tape deck mid-playback and load into a different deck
without losing your place. Nothing about the frames themselves changes; only which
piece of hardware is reading them.

**Why it exists.** A platform thread's call stack is a fixed, OS-reserved region of
native memory tied to one kernel thread for its entire life — that pairing is exactly
what makes platform threads expensive at scale (Part 1 of this guide covered the
per-thread reservation cost) and exactly what makes blocking a platform thread waste
a whole kernel thread's worth of resources for the duration of the wait. Before
`Continuation` existed inside the JDK, the only way to get thread-like concurrency
without one-OS-thread-per-task was to restructure code around callbacks or
`CompletableFuture` chains — Part 2's "colored functions" problem. `Continuation`
is the primitive that lets the JDK give you back a normal, blocking, top-to-bottom
call stack while *underneath* multiplexing thousands of those stacks over a handful
of real OS threads.

**When to reach for it, and when not.** You never construct a `jdk.internal.vm
.Continuation` directly — it is `jdk.internal`, not public API, and `VirtualThread`
is the only supported way to get this behaviour. The sibling it is chosen over is
manual continuation-passing style (nested callbacks, or a hand-rolled state machine)
and reactive pipelines (`CompletableFuture`, project Reactor). Those remain the right
choice when you need genuinely non-blocking backpressure-aware pipelines over data
that is itself a stream; `Continuation`-backed virtual threads are the right choice
when the code is naturally sequential and the only problem was the cost of blocking.

**How it works.** `Continuation` exposes two operations that matter here:

- `enter()` (invoked once, transitively, when the virtual thread is scheduled to run)
  — pushes the continuation's frames onto the *current* platform thread's native
  stack and begins or resumes executing them. This platform thread becomes the
  **carrier** for the duration.
- `yield()` — called by the JDK's own instrumented blocking code (never by
  application code) when the running virtual thread is about to block. It walks the
  live Java frames between the point of the call and the continuation's base frame,
  copies them out of the carrier's native stack into a **`StackChunk`** — a
  perfectly ordinary object living on the Java heap — and then returns control to
  the scheduler on that carrier, freeing the carrier to run something else.

The copy in the other direction is called **mount**: when the scheduler later
decides to run this virtual thread again (on the same carrier or, just as often, a
different one), it copies the frames back out of the `StackChunk` and onto whichever
carrier's native stack picked it up, then resumes execution at the exact bytecode
index where `yield()` returned. **Unmount** is the same copy run the other way, out
to the chunk, at the moment of blocking.

`![D-160 — Stack chunks live on the heap](../diagrams/D-160-stack-chunks-live-heap.svg)`

**D-160** — Stack chunks live on the heap

The diagram is the single most useful mental picture in this file: one carrier's
native stack holding three *mounted* frames on the left, and the heap on the right
holding `StackChunk` objects for every virtual thread that is currently parked or
waiting — which, under load, is the overwhelming majority of them. The arrows
labelled "mount" and "unmount" are the copy in each direction. **`[PROVE]` — why
copying is lazy/partial, not a full-stack memcpy every time:** a virtual thread does
not carry a fixed maximum stack depth the way a platform thread reserves 1 MB up
front. A `StackChunk` starts small and grows a new chunk (chained to the previous
one) only when a deeper call actually needs more room, and on unmount the JDK only
needs to copy the frames that are *live* between the blocking call site and the
chunk's existing high-water mark — it does not walk frames that were already
persisted from an earlier partial unmount, and it does not eagerly copy frames the
next resume will overwrite before they are read. This is what keeps the common case
— a short-lived virtual thread doing one blocking network call three or four frames
deep — a copy of a few hundred bytes rather than a copy of a full call stack's worth
of pages.

**Example — the PSP call, walked frame by frame.** QuizStakes routes a card
withdrawal's authorisation through `CardPayments`, which calls the PSP's
`authorise` endpoint with a documented **p50 of 240 ms** (Appendix A). On a virtual
thread, that four-frame call chain is exactly what gets unmounted and remounted:

```java
// Frame 4 (innermost, where the blocking call actually happens)
HttpResponse<String> authorise(WithdrawalTransaction withdrawal) throws IOException, InterruptedException {
    HttpRequest request = HttpRequest.newBuilder()
            .uri(URI.create("https://psp.internal/v2/authorise"))
            .timeout(Duration.ofSeconds(11)) // matches the PSP's documented p99
            .POST(HttpRequest.BodyPublishers.ofString(withdrawal.toAuthorisePayload()))
            .build();
    return httpClient.send(request, HttpResponse.BodyHandlers.ofString()); // <-- yield() happens here
}

// Frame 3
HttpResponse<String> authoriseWithRetry(WithdrawalTransaction withdrawal) throws IOException, InterruptedException {
    return authorise(withdrawal);
}

// Frame 2
PaymentIntent processCardWithdrawal(WithdrawalTransaction withdrawal) throws IOException, InterruptedException {
    HttpResponse<String> response = authoriseWithRetry(withdrawal);
    return PaymentIntent.fromAuthoriseResponse(withdrawal.id(), response);
}

// Frame 1 (the virtual thread's entry point)
Runnable authoriseTask(WithdrawalTransaction withdrawal) {
    return () -> {
        try {
            PaymentIntent intent = processCardWithdrawal(withdrawal);
            ledger.record(intent);
        } catch (IOException | InterruptedException e) {
            throw new IllegalStateException("PSP authorise failed for " + withdrawal.id(), e);
        }
    };
}
```

`Thread.ofVirtual().start(authoriseTask(withdrawal))` puts all four frames on the
carrier's native stack. The moment `httpClient.send` reaches the socket read that
cannot complete immediately, the JDK's instrumented `HttpClient` internals call
`Continuation.yield()`. That copies frames 1 through 4 — `authoriseTask`'s lambda,
`processCardWithdrawal`, `authoriseWithRetry`, and `authorise` up to its current
program counter — into this virtual thread's `StackChunk` on the heap, and the
carrier is immediately free to mount a different virtual thread. Up to 240 ms later
(the PSP's p50; this specific call could also take the documented p99 of 11 s), the
selector thread that owns the socket signals completion, the scheduler resubmits
this virtual thread's continuation, some carrier (not necessarily the original one)
mounts it by copying those same four frames back onto its native stack, and
execution resumes inside `authorise` at the instruction right after the blocking
read — with `withdrawal`, `request`, and every other local exactly as they were.

**Heap arithmetic for 1,000,000 virtual threads `[NUM]`.** A platform thread reserves
native stack memory up front, before it runs a single frame — commonly 1 MB on a
64-bit HotSpot default (`-Xss`, platform-dependent). One million platform threads
therefore demand **1,000,000 × 1 MB ≈ 976 GB of reserved address space** before
accounting for anything else — a figure that fails outright on most machines, both
because address space that large is impractical to commit and because the OS's
per-process thread-count ceiling is reached long before that. A virtual thread's
`StackChunk`, in contrast, starts near-empty and grows only to the depth actually
used. Taking an illustrative (not JDK-specified) average of **2 KB of live-frame
data per parked virtual thread** — generous for a four-frame call like the one
above — the heap cost of one million parked virtual threads is
**1,000,000 × 2 KB ≈ 1.9 GB**, comfortably inside an ordinary service heap, and it is
*heap* memory subject to GC like any other object graph, not reserved native address
space. **This is leaf 3.14.10's point exactly:** a million virtual threads is a
question you answer by sizing the heap and watching GC pause times, not a question
you answer by checking `ulimit -u` or worrying about running out of 48-bit virtual
address space. The 2 KB figure is a scenario assumption for the arithmetic, not a
constant the JDK guarantees — real chunk size depends on call depth and the JDK
version's frame layout, which is why this guide states the assumption rather than
presenting it as a fixed number.

**Gotcha.** Because the `StackChunk` is an ordinary heap object, a virtual thread
that is merely *parked* (not running) is fully visible to, and moved by, the
garbage collector like any other reachable object — which means a leaked reference
to a never-completing virtual thread (for example, one blocked forever on a queue
nobody ever fills) leaks heap, not just a thread-count slot in some pool. It shows
up in a heap dump as retained `StackChunk` bytes, not as an OS thread count.

> **Definition.** A `Continuation` is a resumable call stack; `yield()` copies its
> live frames from the carrier's native stack into a heap-resident `StackChunk`,
> and a later mount copies them back — the mechanism that lets a virtual thread's
> logical stack outlive, and outnumber, the OS threads that ever run it.

**Supporting fact — `Thread.currentThread()` returns the `VirtualThread` `[RESEARCH]`.**
Inside code running on a virtual thread, `Thread.currentThread()` always returns the
`VirtualThread` instance, never the carrier `Thread`. This holds even while mounted:
the carrier is a real platform `Thread` object underneath, but it is deliberately
reachable only through internal API (`jdk.internal.misc.CarrierThread`, not exported
to application modules). **Gotcha:** code that tries to identify "which OS thread am
I actually running on" for diagnostic logging by calling `Thread.currentThread()
.getId()` gets the virtual thread's identity every time, which is exactly what you
want for correlating log lines to a logical task, and exactly the wrong tool if what
you actually needed was carrier/CPU affinity information — that has to come from
JFR (`jdk.VirtualThreadPinned`, `jdk.VirtualThreadStart`) or `jcmd`, not from
`Thread` identity.

> **Definition.** `Thread.currentThread()` on a virtual thread returns the
> `VirtualThread`; the carrier platform thread is intentionally inaccessible from
> application code.

---

## Concept 2 — `VirtualThread`'s nine-state machine

**Mental model.** Nine named states, but they cluster into three phases a reader
should hold in their head as "not yet running", "in flight", and "done" — the
individual state names then just describe *where* in flight it currently is: on a
carrier executing, trying to leave a carrier, waiting to be handed a carrier again,
or stuck because it could not leave one.

**Why it exists.** A platform thread's OS-level states (`NEW`, `RUNNABLE`,
`BLOCKED`, `WAITING`, `TIMED_WAITING`, `TERMINATED` — the six values of
`Thread.State`) are too coarse to describe what a virtual thread is doing, because
those six states say nothing about *carrier occupancy*, which is the resource that
actually matters for a virtual thread. `Thread.getState()` on a virtual thread
still reports one of the same six public `Thread.State` values (source
compatibility demands it), but the JDK's internal bookkeeping tracks nine finer
states to know precisely when a continuation may safely yield, when it is mid-yield,
and when it failed to yield because it was pinned.

**When to reach for it, and when not.** You do not construct or read these nine
internal states directly from application code — there is no public API exposing
`PINNED` or `YIELDING` as distinct from the public `Thread.State` values (`PINNED`
folds into `RUNNABLE`/`WAITING` from the outside, depending on JDK version). The
place these states are genuinely visible is JFR: `jdk.VirtualThreadPinned` fires
precisely on a failed yield attempt, and `jcmd <pid> Thread.dump_to_file
-format=json` labels threads with a state string that maps onto this internal
machine. Reach for `Thread.getState()` for coarse liveness checks; reach for JFR
when you need to know *why* a virtual thread did not yield when you expected it to.

**How it works.**

| State | Meaning |
|---|---|
| `NEW` | Constructed, not yet started. |
| `STARTED` | `start()` has been called; submitted to the scheduler, not yet mounted. |
| `RUNNABLE` | Eligible to run; queued on the scheduler waiting for a carrier. |
| `RUNNING` | Mounted on a carrier, executing bytecode. |
| `PARKING` | In the act of attempting to park (calling `yield()`) — transient. |
| `PARKED` | Successfully yielded; unmounted, its `StackChunk` waiting on the heap for the event that unparks it. |
| `PINNED` | Attempted to yield while pinned (native frame or, on Java 21, a held monitor on the stack); the yield failed and the virtual thread keeps running **on its carrier**, blocking that carrier instead of freeing it. |
| `YIELDING` | In the act of a *cooperative* yield (not a blocking park) — used for fairness, e.g. explicit `Thread.yield()`. |
| `TERMINATED` | Run method has returned or thrown. |

`![D-161 — `VirtualThread`'s state machine](../diagrams/D-161-virtualthread-s-state-machine.svg)`

**D-161** — `VirtualThread`'s state machine

Trace the labelled transitions in the diagram: `start` moves `NEW → STARTED`, the
scheduler's own dispatch moves `STARTED → RUNNABLE`, a carrier picking the task up
is `RUNNABLE → RUNNING` (this is *mount*), a blocking call attempts `RUNNING →
PARKING`, and that attempt resolves one of two ways — `PARKING → PARKED` on success
(this is *unmount*, freeing the carrier) or `PARKING → PINNED` on failure, in which
case the virtual thread does **not** free its carrier and simply blocks it in place
until the operation completes. `unpark` moves `PARKED → RUNNABLE` again — back onto
the scheduler's queue, not directly onto a carrier — and `completion` moves
`RUNNING → TERMINATED`.

**Example.** Watching the state machine from the outside during a QuizStakes stake
settlement:

```java
Thread settlementThread = Thread.ofVirtual().unstarted(() -> {
    quizEngine.settleStake(reservation.id(), Verdict.WIN); // blocks on a socket read internally
});
System.out.println(settlementThread.getState()); // NEW

settlementThread.start();
System.out.println(settlementThread.getState()); // RUNNABLE or RUNNING, depending on timing

settlementThread.join();
System.out.println(settlementThread.getState()); // TERMINATED
```

Because `PARKED`, `PINNED`, `PARKING`, and `YIELDING` are internal-only, this
program can only ever observe the public `Thread.State` mapping of them
(`RUNNABLE`, `WAITING`/`TIMED_WAITING`, or `TERMINATED`); the finer nine-state
picture is what you would additionally see by attaching JFR or a debugger during
the `settleStake` call.

**Gotcha.** `PINNED` is easy to misread as "blocked, same as `PARKED`" from a
throughput graph, because in both cases the virtual thread is not making progress.
The difference that matters operationally is which resource is consumed while
waiting: a `PARKED` virtual thread consumes only heap; a `PINNED` one consumes an
entire carrier for the whole wait, exactly like a blocked platform thread would —
which is why a service that reports "healthy p50 latency" while actually pinning
heavily can still exhaust its carrier pool under concurrency and fall over on tail
latency alone.

> **Definition.** `VirtualThread` cycles through nine internal states —
> `NEW`, `STARTED`, `RUNNABLE`, `RUNNING`, `PARKING`, `PARKED`, `PINNED`,
> `YIELDING`, `TERMINATED` — of which the public `Thread.State` enum exposes only
> a coarser six-value view.

---

## Concept 3 — The FIFO scheduler and its verified defaults

**Mental model.** The default scheduler is not a bespoke virtual-thread engine — it
is the same `ForkJoinPool` class that backs parallel streams and the common pool,
just constructed with a different mode switch flipped (`asyncMode = true`) and
different tuning constants. Picture the same machine wearing a different setting on
its dial.

**Why it exists.** Something has to decide which of potentially millions of
`RUNNABLE` virtual threads gets the next available carrier, and do so with minimal
per-decision overhead, because that decision happens on every single mount. Reusing
`ForkJoinPool` rather than writing a new work queue from scratch reused a
battle-tested, lock-free, per-worker-queue task dispatcher that the JDK already had
— it only needed the FIFO/async mode, which `ForkJoinPool` already supported for
exactly this "independent asynchronous events" case (`ForkJoinPool`'s own javadoc
calls this async mode "for use with event-style tasks that are never joined").

**When to reach for it, and when not.** You do not choose the default scheduler at
the call site — `Thread.ofVirtual()` always uses it unless the virtual thread was
created through a custom `Executor` passed to `Thread.Builder.OfVirtual.scheduler`
(an internal-only hook, not public API in 21). The sibling worth naming is the
*common pool* used by parallel streams and `CompletableFuture.supplyAsync`, which is
also a `ForkJoinPool` but in the opposite (LIFO, work-stealing) mode — covered next.

**How it works — `[SOURCE]`, quoted verbatim from `VirtualThread.createDefaultScheduler()`,
OpenJDK at the jdk-21+35 tag:**

```java
int parallelism, maxPoolSize, minRunnable;
String parallelismValue = System.getProperty("jdk.virtualThreadScheduler.parallelism");
String maxPoolSizeValue = System.getProperty("jdk.virtualThreadScheduler.maxPoolSize");
String minRunnableValue = System.getProperty("jdk.virtualThreadScheduler.minRunnable");
if (parallelismValue != null) {
    parallelism = Integer.parseInt(parallelismValue);
} else {
    parallelism = Runtime.getRuntime().availableProcessors();
}
if (maxPoolSizeValue != null) {
    maxPoolSize = Integer.parseInt(maxPoolSizeValue);
    parallelism = Integer.min(parallelism, maxPoolSize);
} else {
    maxPoolSize = Integer.max(parallelism, 256);
}
if (minRunnableValue != null) {
    minRunnable = Integer.parseInt(minRunnableValue);
} else {
    minRunnable = Integer.max(parallelism / 2, 1);
}
Thread.UncaughtExceptionHandler handler = (t, e) -> { };
boolean asyncMode = true; // FIFO
return new ForkJoinPool(parallelism, factory, handler, asyncMode,
             0, maxPoolSize, minRunnable, pool -> true, 30, SECONDS);
```

Reading it line by line, because every constant here is asked about directly:

- **`parallelism`** defaults to `Runtime.getRuntime().availableProcessors()` — the
  number of carrier threads the scheduler will try to keep active. It can be
  overridden with the system property `jdk.virtualThreadScheduler.parallelism`.
- **`maxPoolSize`** defaults to **`Integer.max(parallelism, 256)` — a floor, not a
  flat 256.** On an 8-core box that is `max(8, 256) = 256`. On a box with, say, 320
  available processors, it is `max(320, 256) = 320` — parallelism wins. **Anyone who
  states the default as a flat "256" is only correct for machines with 256 or fewer
  processors**, which is most machines today but is not what the source says.
  Overridable via `jdk.virtualThreadScheduler.maxPoolSize`.
- The `else` branch that sets `maxPoolSize` is skipped when the property **is**
  supplied, and in that branch there is a side effect worth calling out explicitly:
  `parallelism = Integer.min(parallelism, maxPoolSize)`. **Setting
  `jdk.virtualThreadScheduler.maxPoolSize` below the processor count silently
  clamps `parallelism` down to match it too** — one property quietly moves two
  numbers, which is a real footgun for anyone who sets a small `maxPoolSize` to cap
  memory and is surprised that steady-state throughput also dropped.
- **`minRunnable`** defaults to `Integer.max(parallelism / 2, 1)` — a third tuning
  knob, `jdk.virtualThreadScheduler.minRunnable`, that almost no blog post mentions.
  It is the threshold of runnable (not-yet-mounted) tasks below which the pool
  considers itself under-supplied and may try to add a compensating worker
  (Concept 6 covers this compensation mechanism in full).
- **`asyncMode = true`**, and the source's own comment on that exact line is
  `// FIFO` — that comment, in the JDK's own source, is the primary-source evidence
  for calling this scheduler FIFO; it is not this guide's inference.
- The `ForkJoinPool` constructor's remaining arguments are a `0` minimum-spare
  argument, the `maxPoolSize` and `minRunnable` computed above, a saturation
  predicate `pool -> true` (meaning: never refuse to run a task by throwing — always
  attempt to find or create a worker), and a **30-second worker keep-alive**
  (`30, SECONDS`) — idle carrier threads beyond the steady `parallelism` count are
  retired after 30 seconds of inactivity.

**Consistent worked numbers for this file, per the one-machine convention this
guide's diagrams share (§8 of the verified-figures note): an 8-core box.**
`parallelism = 8`, `maxPoolSize = max(8, 256) = 256`, `minRunnable = max(8/2, 1) =
4`.

`![D-162 — FIFO for virtual threads, LIFO for parallel streams](../diagrams/D-162-fifo-virtual-threads-lifo.svg)`

**D-162** — FIFO for virtual threads, LIFO for parallel streams

**`[PROVE]` — why FIFO here and LIFO for the common pool.** The common pool (used
by `parallelStream()` and bare `CompletableFuture.supplyAsync`) uses LIFO
work-stealing: a worker pushes and pops its **own** queue's head (LIFO, maximising
cache locality on the subtask it just produced, because divide-and-conquer
subtasks are typically related — e.g. two halves of the same array range) and only
steals from the **tail** of another worker's queue when idle, which minimises
contention on hot heads. That design is optimised for *recursively split
subtasks* of one larger computation, where locality between a task and the
subtasks it just spawned pays off. Virtual threads are the opposite shape: each one
is an **independent**, unrelated task — a request handler, a settlement job, a
notification send — with no relationship to the task queued before or after it.
For independent tasks, the property worth optimising is **fairness**: a task
queued first should not starve behind a burst of tasks queued after it, which is
exactly what a FIFO (async-mode) queue guarantees and a LIFO queue does not.
Running virtual threads through a LIFO pool would let the most-recently-submitted
task keep jumping the queue ahead of older, still-waiting tasks whenever a worker
is free — starvation under sustained load, which is unacceptable for the kind of
one-task-per-request workload virtual threads exist to serve. The left panel of
D-162 draws the virtual-thread scheduler's queue head-first (dequeue from the
front, matching submission order); the right panel draws the common pool's
own-head push/pop with tail stealing.

**Example — confirming effective values at runtime `[NUM]`.** The scheduler itself
is `jdk.internal`, so there is no public getter for "what parallelism did the
default scheduler actually pick". Two supported ways to confirm it in QuizStakes'
payment-processing service:

```java
// 1. Confirm the *inputs* you control, before the scheduler is ever created:
System.out.println(Runtime.getRuntime().availableProcessors()); // e.g. 8
System.out.println(System.getProperty("jdk.virtualThreadScheduler.maxPoolSize")); // null unless set

// 2. Confirm the *effect* under load, via a thread dump taken while
//    the service is saturated with virtual threads blocked on the PSP:
//    jcmd <pid> Thread.dump_to_file -format=json /tmp/quizstakes-dump.json
//    -> count distinct carrier thread names in the JSON; under sustained
//       card-authorise load this converges to the effective parallelism
//       (8 on this file's reference machine), not to the number of
//       concurrently-blocked virtual threads (which can be in the thousands).
```

**Gotcha.** `Runtime.getRuntime().availableProcessors()` reflects the **container's**
CPU quota when the JVM correctly detects cgroup limits (Java 10+), not the host's
physical core count — a QuizStakes pod capped at 2 vCPUs gets `parallelism = 2` and
therefore `minRunnable = 1`, regardless of how many cores the underlying node has.
Sizing `-XX:ActiveProcessorCount` or the cgroup CPU quota is, transitively, sizing
the virtual-thread scheduler's parallelism too.

> **Definition.** The default virtual-thread scheduler is a `ForkJoinPool`
> constructed with `asyncMode = true` (FIFO), parallelism defaulting to
> `availableProcessors()`, `maxPoolSize` defaulting to `Integer.max(parallelism,
> 256)`, and `minRunnable` defaulting to `Integer.max(parallelism / 2, 1)` — three
> independently tunable properties, only one of which most material ever mentions.

---

## Concept 4 — Instrumented and non-instrumented blocking points

**Mental model.** "Virtual-thread friendly" is not a property of *blocking* in
general — it is a property of a specific, enumerable list of JDK call sites that
the JDK's engineers rewrote to call `Continuation.yield()` instead of parking the
underlying OS thread. Everything not on that list still blocks a real OS thread,
virtual or not.

**Why it exists.** Making a blocking call yield instead of block requires the code
*at that call site* to know it is running on a virtual thread and to cooperate —
there is no general JVM-level mechanism that retrofits arbitrary blocking native
calls into yields. The JDK team went through the standard library's actually-hot
blocking paths (sockets, NIO, `java.util.concurrent` primitives, `Thread.sleep`)
and rewrote each one specifically; this is deliberate, incremental engineering
work, not a byproduct of virtual threads existing.

**When to reach for it, and when not.** This is not a choice you make — it is a
map you need before you can reason about a stack trace or a throughput graph. The
practical use is diagnostic: when a service pinned or a carrier pool saturates
unexpectedly, the first question is "which of these blocking calls is actually on
the instrumented list, and which isn't".

**How it works.** The instrumented set, `[X-REF 05]`:

| Category | Examples |
|---|---|
| `java.net` sockets | `Socket`, `ServerSocket` blocking reads/accepts |
| NIO channels and `Selector` | `SocketChannel`, `Selector.select` |
| `HttpClient` | both the synchronous `send` and the async client's internal blocking waits |
| Timed waits | `Thread.sleep` |
| Park primitives | `LockSupport.park`/`parkNanos` |
| `java.util.concurrent` | `ReentrantLock`, blocking queues (`BlockingQueue.take`/`put`), `CountDownLatch.await`, `Semaphore.acquire` |
| Process control | `Process.waitFor` |

Each of these has an internal implementation path that, when running on a virtual
thread, calls `Continuation.yield()` instead of making the underlying OS-level
blocking syscall directly on the carrier — freeing the carrier for other work while
this virtual thread waits, then re-scheduling it when the event arrives (socket
readable, timer elapsed, lock available). The full mechanism for *how* each of
these individually is wired — the `Poller`/selector integration for sockets, the
timer wheel behind `Thread.sleep`, `AbstractQueuedSynchronizer`'s virtual-thread-aware
park path — belongs to guide 05 (multithreading and concurrency); what you need here
is that this list is finite, deliberate, and worth memorizing, because it is exactly
the boundary of where virtual threads deliver their promised cheapness.

**The non-instrumented set, `[TRAP]` `[RESEARCH]`:**

- **Most file I/O** (`FileInputStream`, `FileChannel`, and friends) is *not*
  instrumented on Java 21. These calls are dispatched to run on a carrier (or an
  internal bounded pool used specifically for this purpose) and genuinely block
  that carrier for the duration — file I/O in the JDK maps to blocking native
  syscalls that were not given a virtual-thread-aware rewrite in this release,
  unlike sockets.
- **`Object.wait()`, before Java 24**, does not yield — waiting inside a
  `synchronized` block already pins the carrier for the reason Concept 5 covers
  (a held monitor pins the continuation), so the wait compounds an existing pin
  rather than introducing a separate one.
- **Any JNI frame** on the continuation's stack — native code the JVM cannot walk
  or relocate, so a continuation with a JNI frame anywhere on it cannot yield at
  all until that frame unwinds, for the same structural reason a native frame pins
  in Concept 5.

**Pitfall — assuming "virtual thread" means "every blocking call yields":**

**Wrong**

```java
// A QuizStakes batch job reading 40,000 uploaded identity documents from
// local disk, one virtual thread per file, expecting near-zero carrier cost:
try (var scope = Executors.newVirtualThreadPerTaskExecutor()) {
    for (Path documentPath : uploadedDocuments) {
        scope.submit(() -> Files.readAllBytes(documentPath)); // NOT instrumented
    }
} // 40,000 virtual threads queue up, but file reads block real carriers —
  // throughput caps out at roughly `parallelism` concurrent reads, not 40,000
```

**Right**

```java
// Accept that file I/O consumes a carrier for its duration and size the
// expectation accordingly — or move the read to a purpose-built bounded
// executor sized for disk parallelism, keeping virtual threads for the
// genuinely instrumented parts of the pipeline (e.g. the downstream HTTP
// call to the DocumentVerification vendor):
try (var ioExecutor = Executors.newFixedThreadPool(4); // matches disk parallelism, not core count
     var scope = Executors.newVirtualThreadPerTaskExecutor()) {
    for (Path documentPath : uploadedDocuments) {
        scope.submit(() -> {
            byte[] bytes = ioExecutor.submit(() -> Files.readAllBytes(documentPath)).get();
            return documentVerificationClient.verify(bytes); // this leg genuinely yields
        });
    }
}
```

**Why people believe it:** the marketing framing of virtual threads is
"write blocking code, get async performance for free", and that is true for the
instrumented list — which happens to cover the calls people reach for most, sockets
and locks — so it is easy to generalise to "all blocking calls" without ever
hitting the file-I/O case in a quick benchmark.

> **Definition.** A blocking call yields its virtual thread's carrier only if the
> JDK rewired that specific call site to invoke `Continuation.yield()`; the
> instrumented set covers network I/O, NIO, `HttpClient`, timed waits, park
> primitives, `j.u.c` synchronizers, and `Process.waitFor` — file I/O, pre-24
> `Object.wait`, and JNI frames are not on it.

---

## Concept 5 — Pinning is a property of the continuation, and JEP 491

**Mental model.** Pinning is not a bug or a missed optimisation — it is a
structural consequence of what a continuation is allowed to safely detach *from*.
A continuation can only yield if every frame between the yield point and its base
is something the JVM knows how to relocate; a frame the JVM cannot relocate simply
cannot be unmounted, full stop.

**Why it exists (as a constraint, not a feature).** Two kinds of frames break the
"the JVM can move this" guarantee. A **native frame** (JNI, or any frame below a
call into native code) is opaque to the JVM — the JVM does not know its layout and
cannot copy it into a `StackChunk` and later replay it on a different OS thread,
because the native code may hold raw pointers into that specific OS thread's native
stack. A **held object monitor**, on Java 21, is pinned for a related but distinct
reason: `synchronized`'s locking protocol at that release is implemented in terms
of the OS thread that acquired it — unmounting mid-hold would mean the "owner" of
the monitor becomes ambiguous the moment a different carrier resumes the
continuation.

**When this matters, and when it does not.** A continuation that blocks *without*
either of these two things on its stack yields normally and costs nothing extra.
The failure mode only shows up when a blocking call (Concept 4's instrumented list)
happens **while a monitor is held or a native frame is present** — the yield is
attempted, fails, and the virtual thread falls back to blocking its carrier in
place (state `PINNED`, Concept 2), which is exactly as expensive as blocking a
platform thread for that duration.

**How it works, and the version delta `[VERSION-TRAP]`:**

`![D-163 — Pinning is a property of the continuation](../diagrams/D-163-pinning-property-continuation.svg)`

**D-163** — Pinning is a property of the continuation

- **Java 21 (this file's target version):** a `synchronized` block or method that
  performs an instrumented blocking call while the monitor is held pins the
  carrier for the duration. This is a real, current-release trap: "use
  `ReentrantLock` instead of `synchronized` around blocking calls on virtual
  threads" is **correct advice on Java 21**.
- **Java 24, JEP 491 ("Synchronize Virtual Threads without Pinning"):** object
  monitors become continuation-aware. `synchronized` **no longer pins** on 24+ —
  the JVM's monitor implementation was reworked so that a virtual thread can
  release and later reacquire the monitor's ownership record across a
  mount/unmount boundary. **Native frames and JNI still pin on 24 and beyond** —
  JEP 491 addresses the monitor case specifically; it does not and cannot address
  the "JVM cannot relocate opaque native state" case, because that is a structural
  property of native code, not an implementation choice inside the JVM's monitor
  subsystem.

**The version-scoped answer, stated plainly:** "avoid `synchronized` around
blocking calls on virtual threads, prefer `ReentrantLock`" is the **correct answer
on Java 21** and the **unnecessary-but-harmless answer from Java 24 onward** — an
interviewer who asks this question is testing whether you know it changed, not
just whether you know the Java-21 folklore. Every "use `ReentrantLock`" answer in
this guide, and any answer you give in an interview, should name the version it
applies to.

**`-Djdk.tracePinnedThreads` and its successor `[RESEARCH]` `[VERSION-TRAP]`.**
`-Djdk.tracePinnedThreads` was introduced by **JEP 444** (the JEP that finalized
virtual threads in Java 21) as a JVM flag that prints a stack trace to standard
error every time a virtual thread parks while pinned — `full` prints every frame,
`short` prints only the pinning frame. It remains available on 21 and is the
quickest way to find pinning sites without instrumenting anything. It has since
been **superseded in practice** by the **`jdk.VirtualThreadPinned` JFR event**,
which fires on the same condition but carries structured data a stderr print does
not: the pinning **reason** (monitor vs. native frame) and the **carrier thread's
identity**, queryable and aggregable across a whole JFR recording rather than
grepped line-by-line out of logs. For a production QuizStakes service, the JFR
event is strictly more useful — it can be correlated against the same recording's
GC pauses, allocation profile, and carrier-pool saturation without a separate
logging pass.

**Example.**

```java
// Java 21: this pins. synchronized + a blocking network call inside it.
class ClientRestrictions {
    private final Object lock = new Object();

    void applyWithdrawalHold(ClientId clientId, RestrictionKey key) throws IOException {
        synchronized (lock) {
            screeningService.recheck(clientId); // instrumented HTTP call — but the monitor is held
            restrictions.add(clientId, key);     // PINNED for the duration of recheck() on Java 21
        }
    }

    // Java 21 fix: replace the monitor with a lock the continuation-aware
    // park path already understands, because ReentrantLock's internals sit
    // on AbstractQueuedSynchronizer, which is itself on the instrumented list.
    private final ReentrantLock reentrantLock = new ReentrantLock();

    void applyWithdrawalHoldFixed(ClientId clientId, RestrictionKey key) throws IOException {
        reentrantLock.lock();
        try {
            screeningService.recheck(clientId); // now yields normally, no pin
            restrictions.add(clientId, key);
        } finally {
            reentrantLock.unlock();
        }
    }
    // On Java 24+ (JEP 491), applyWithdrawalHold's original synchronized form
    // no longer pins either — the fix above becomes optional, not necessary.
}
```

**Gotcha.** A native frame pin is invisible to a `synchronized`-to-`ReentrantLock`
refactor — if the pinning cause is a JNI call (a native image-processing library
used by `DocumentVerification`, for instance) sitting below an instrumented
blocking call, no amount of lock-type substitution removes it on any Java version,
because JEP 491 never touches native frames. The JFR event's reason field is what
tells you which of the two you actually have before you pick a fix.

> **Definition.** Pinning is the JVM's refusal to unmount a continuation whose
> stack contains a frame it cannot relocate — a native/JNI frame on every current
> release, and a held object monitor on Java 21 through 23, resolved for monitors
> specifically by JEP 491 in Java 24.

---

## Concept 6 — No preemption, and carrier-pool compensation

**Mental model.** The scheduler's fairness guarantee (FIFO, Concept 3) only
governs which `RUNNABLE` task gets picked up **next**; it says nothing about how
long a task, once running, is allowed to keep its carrier. A virtual thread that
never blocks and never explicitly yields simply keeps its carrier forever — the
scheduler has no clock-interrupt mechanism to forcibly take it back.

**Why it exists (as a constraint).** Cooperative-yield scheduling — yield only at
explicit points, mount/unmount only through `Continuation`'s API — is exactly what
makes the mount/unmount machinery in Concept 1 tractable and cheap: the JVM only
ever needs to capture state at a small, known set of yield points, never at an
arbitrary instruction the way an OS preempts a kernel thread on a timer interrupt.
That simplicity is bought at the price of no preemption: there is no equivalent of
an OS timeslice for virtual threads.

**When this matters.** It matters precisely for CPU-bound work with no blocking
calls inside it — a tight loop, a large in-memory sort, an unbounded recursive
computation. It does not matter for the overwhelmingly common virtual-thread
workload (I/O-bound request handling that blocks frequently on instrumented calls),
because each block is itself an opportunity for the scheduler to reclaim the
carrier.

**How it works.** `[TRAP]` `[PROVE]`: consider a QuizStakes reporting job that
recomputes a settlement summary over an in-memory batch of stake reservations
purely in Java, with no I/O:

```java
Runnable computeSettlementSummary(List<StakeReservation> batch) {
    return () -> {
        BigDecimal total = BigDecimal.ZERO;
        for (StakeReservation reservation : batch) { // no blocking call anywhere in this loop
            total = total.add(reservation.stakeAmount());
        }
        summaryStore.publish(total); // the only potential yield point, and only at the very end
    };
}
```

If `batch` is large enough that this loop runs for, say, 400 ms of pure CPU work,
that virtual thread occupies its carrier for the full 400 ms with **no
opportunity for the scheduler to intervene** — there is no timer that forces a
yield partway through. Submit eight of these (on the reference 8-core box's
`parallelism = 8`) and every carrier the default scheduler owns is occupied for
400 ms straight; every other `RUNNABLE` virtual thread — including latency-sensitive
request handlers doing genuinely short I/O-bound work — queues behind them for up
to 400 ms, regardless of FIFO fairness, because FIFO only orders *who gets a
carrier next*, not *how long they keep it*. **This is the concrete failure mode
behind the general warning "don't run CPU-bound work on virtual threads without
thought" — it is not that virtual threads compute slower, it is that one runaway
CPU-bound task can starve every co-scheduled I/O-bound task on the same scheduler.**

**Compensation, and why the pool has a `maxPoolSize` at all `[RESEARCH]` `[NUM]`.**
The scheduler is not entirely helpless against carrier exhaustion — it just cannot
act on CPU-bound starvation (Concept 6's core limitation), only on **pinning**
(Concept 5) and explicit `ManagedBlocker` use. When a virtual thread pins (fails to
yield because of a held monitor or a native frame) or a task explicitly registers
itself via `ForkJoinPool.ManagedBlocker`, the scheduler can recognise that a
carrier is effectively unavailable for new work for an extended period and grow
the pool by spinning up an additional carrier thread, up to `maxPoolSize` — the
`Integer.max(parallelism, 256)` default from Concept 3. This is precisely **why the
pool has a ceiling at all**: without `maxPoolSize`, sustained pinning under load
could grow the carrier pool without bound, trading the original platform-thread
scaling problem right back for a different one; `maxPoolSize` caps how far the
scheduler is willing to compensate before it simply queues remaining work behind
the pinned carriers. On the reference 8-core box, that ceiling is 256 — the
scheduler can grow from 8 carriers to as many as 256 before it stops compensating,
which is generous headroom for occasional pinning but not infinite, and explicitly
not a substitute for fixing the pinning site once JFR has identified it.

**Gotcha.** Compensation only fires for pinning and `ManagedBlocker` registration —
it does **not** fire for a CPU-bound virtual thread that simply never blocks and
never pins, because that thread never signals "I am unavailable" to anything; from
the scheduler's point of view it looks identical to useful, ongoing work. There is
no configuration flag that makes the scheduler preempt a compute-bound virtual
thread; the only fix is architectural — keep CPU-bound work off the default
virtual-thread scheduler (a dedicated `ForkJoinPool` or platform-thread pool sized
for compute, exactly as you would size a compute pool today), or break the
computation into chunks with explicit `Thread.yield()` calls between chunks so the
scheduler gets a cooperative opportunity to intervene.

> **Definition.** Virtual threads are scheduled cooperatively with no timeslice
> preemption; a task that never blocks or explicitly yields keeps its carrier
> indefinitely, and the scheduler's only lever against carrier starvation is
> compensating growth toward `maxPoolSize`, triggered by pinning or
> `ManagedBlocker` use — never by CPU-bound duration alone.

---

## Supporting facts

**Thread-local storage is per virtual thread `[NUM]` `[PROVE]`.** A `ThreadLocal`
attached from inside a virtual thread is scoped to that `VirtualThread` instance,
exactly as it would be for a platform thread — there is no sharing or pooling of
thread-local state across the virtual threads that happen to share a carrier over
time. The consequence worth proving through arithmetic: a per-thread cache pattern
that was safe and cheap for a platform-thread pool of, say, 200 threads (200 cache
instances total, one per pooled platform thread, reused across every request that
pool ever serves) becomes a **per-task allocation** under virtual threads, because
QuizStakes' peak of 55,000 concurrent sessions (Appendix A) means up to 55,000 live
`ThreadLocal` slots for the same cache, each initialised once and then discarded
when its one-shot virtual thread terminates — 55,000 cache-object allocations
under peak load where the platform-thread version made exactly 200. **Pitfall:**
carrying a `ThreadLocal`-based per-thread cache pattern forward from a
platform-thread-pool design into a virtual-thread design without re-deriving this
arithmetic silently turns a bounded, amortised cost into an unbounded, per-request
one; the fix is either a genuinely shared cache (with the concurrency control that
implies) or `ScopedValue` (Java 21 preview, structurally similar cost profile but
immutable-after-bind, covered in the structured-concurrency guide that follows
this file) rather than `ThreadLocal`, depending on whether mutation is needed.

> **Definition.** `ThreadLocal` state is scoped per `VirtualThread`, not per
> carrier — a per-thread cache pattern becomes a per-task allocation once the
> "thread" in question is virtual and one-shot.

**Thread dumps: `jcmd Thread.dump_to_file -format=json` `[RESEARCH]` `[TRAP]`.**
`jcmd <pid> Thread.dump_to_file -format=json <path>` is the supported way to dump
virtual threads at scale — the traditional `jstack`/`Thread.dump_to_file
-format=plain` output is impractical once there are thousands of virtual threads,
and the JSON format additionally groups virtual threads under the structured-
concurrency scope tree they belong to when one is in use (the next file in this
set covers that tree). **Gotcha:** the JSON dump deliberately **omits object
addresses, monitor/lock ownership detail, and JNI frame statistics** for virtual
threads — information the plain-format dump does include for platform threads.
**Pitfall:** reaching for the JSON thread dump to diagnose a suspected pinning-by-
monitor issue and finding no lock-ownership data in it, then concluding pinning
"isn't happening" — the JSON dump is the wrong tool for that specific question;
`jdk.VirtualThreadPinned` JFR events (Concept 5) or `-Djdk.tracePinnedThreads`
carry the monitor/pinning detail the thread dump intentionally leaves out.

> **Definition.** `jcmd Thread.dump_to_file -format=json` is the scale-appropriate
> way to enumerate virtual threads and their structured-concurrency tree, at the
> cost of omitting the lock and JNI detail the older plain-format dump carries.

---

## Pitfalls

### Assuming the default `maxPoolSize` is always 256

**Wrong**

```java
// "The virtual-thread carrier pool caps at 256, so at most 256 carriers
// will ever exist" — stated as a flat fact regardless of hardware.
```

**Right**

```java
// maxPoolSize = Integer.max(parallelism, 256). On a 320-core box with no
// override, maxPoolSize is 320, not 256 — parallelism wins once it exceeds
// the 256 floor. Verify per-machine rather than quoting the common case:
System.out.println(Runtime.getRuntime().availableProcessors()); // parallelism input
// then: maxPoolSize == Math.max(thatValue, 256), per VirtualThread.createDefaultScheduler()
```

**Why people believe it:** 256 is the number every blog post quotes, because it is
the number that applies on essentially every laptop and most commodity server SKUs
today (well under 256 cores) — the source's actual `Integer.max` framing only
becomes visible on hardware most engineers never personally provision.

### Treating `synchronized` pinning as a permanent fact about virtual threads

**Wrong**

```java
// A blanket team rule: "never use synchronized with virtual threads,
// full stop" — applied unconditionally to a Java 24 codebase.
```

**Right**

```java
// State the version. On Java 21–23, synchronized around a blocking call
// pins and ReentrantLock is the fix. On Java 24+ (JEP 491), synchronized
// no longer pins for the monitor case — only native/JNI frames still do.
// Check java.lang.Runtime.version() or the build's target release before
// applying the rule, and re-check native-library boundaries either way.
```

**Why people believe it:** the Java-21 launch of virtual threads is what most
engineers' mental model was formed against, and JEP 491 landing three releases
later in Java 24 does not automatically propagate into team wikis or Stack
Overflow answers written in 2023–2024.

### Expecting file I/O to yield like socket I/O

**Wrong**

```java
// Assuming Files.readAllBytes inside a virtual thread frees its carrier
// the same way a socket read would, and sizing the executor for 10,000
// concurrent file reads accordingly.
try (var executor = Executors.newVirtualThreadPerTaskExecutor()) {
    documentPaths.forEach(path -> executor.submit(() -> Files.readAllBytes(path)));
}
```

**Right**

```java
// File I/O is not on the instrumented list on Java 21 — it consumes a
// carrier for its duration like any blocking call on a platform thread.
// Route it through an executor sized for actual disk parallelism, and
// reserve virtual threads for the instrumented legs of the same pipeline.
try (var diskExecutor = Executors.newFixedThreadPool(4);
     var taskExecutor = Executors.newVirtualThreadPerTaskExecutor()) {
    documentPaths.forEach(path -> taskExecutor.submit(() -> {
        byte[] bytes = diskExecutor.submit(() -> Files.readAllBytes(path)).get();
        return documentVerificationClient.verify(bytes);
    }));
}
```

**Why people believe it:** "virtual threads make blocking I/O cheap" is stated
without the qualifier "the specific, instrumented set of I/O calls", and file I/O
feels categorically the same as network I/O to most readers.

### Expecting FIFO fairness to bound how long a task holds its carrier

**Wrong**

```java
// "The scheduler is FIFO, so no task can be starved for long" — applied
// to a mix of I/O-bound handlers and an occasional CPU-bound batch job
// on the same default virtual-thread scheduler.
```

**Right**

```java
// FIFO only orders which RUNNABLE task is picked up next; it does not
// preempt a task that is already RUNNING. Keep CPU-bound work off the
// default scheduler entirely — route it to a dedicated pool sized for
// compute, exactly as you would without virtual threads in the picture.
ExecutorService computeBoundPool = Executors.newFixedThreadPool(
        Runtime.getRuntime().availableProcessors());
computeBoundPool.submit(() -> computeSettlementSummary(largeBatch));
```

**Why people believe it:** "fair" and "bounded wait" sound like the same property,
but FIFO fairness is a queue-ordering guarantee, and the absence of preemption is a
completely separate axis that FIFO says nothing about.

---

## Cheat sheet

| Fact | Value / behaviour |
|---|---|
| Three layers | `VirtualThread` (identity/API) → `Continuation` (suspend/resume) → `ForkJoinPool` scheduler (dispatch) → carrier platform threads |
| Mount / unmount | Copy `StackChunk` (heap) frames onto/off the carrier's native stack; lazy/partial, not a full-stack copy |
| Nine internal states | `NEW`, `STARTED`, `RUNNABLE`, `RUNNING`, `PARKING`, `PARKED`, `PINNED`, `YIELDING`, `TERMINATED` |
| Public `Thread.State` | Only six values — the nine internal states map onto them coarsely |
| Default scheduler | `ForkJoinPool`, `asyncMode = true` (source comment: `// FIFO`) |
| `parallelism` default | `availableProcessors()`; property `jdk.virtualThreadScheduler.parallelism` |
| `maxPoolSize` default | `Integer.max(parallelism, 256)` — **floor, not flat 256** ; property `jdk.virtualThreadScheduler.maxPoolSize`, which also clamps `parallelism` down if set below it |
| `minRunnable` default | `Integer.max(parallelism / 2, 1)`; property `jdk.virtualThreadScheduler.minRunnable` |
| Worker keep-alive | 30 seconds; saturation predicate `pool -> true` |
| FIFO vs LIFO | Virtual threads: FIFO, independent tasks, fairness. Common pool: LIFO work-stealing, recursive subtasks, locality |
| Instrumented blocking | sockets, NIO/`Selector`, `HttpClient`, `Thread.sleep`, `LockSupport.park`, `j.u.c` locks/queues, `Process.waitFor` |
| Non-instrumented blocking | most file I/O, `Object.wait` before Java 24, any JNI frame |
| Pinning causes, Java 21 | held object monitor, native/JNI frame |
| Pinning causes, Java 24+ (JEP 491) | native/JNI frame only — monitors no longer pin |
| Pinning diagnostics | `-Djdk.tracePinnedThreads` (JEP 444) or `jdk.VirtualThreadPinned` JFR event (reason + carrier identity) |
| Preemption | None — a CPU-bound virtual thread holds its carrier until it blocks or finishes |
| Compensation trigger | Pinning or `ManagedBlocker` registration — never CPU-bound duration alone |
| Compensation ceiling | `maxPoolSize` |
| Thread dumps at scale | `jcmd <pid> Thread.dump_to_file -format=json`; includes structured-concurrency tree, omits addresses/lock info/JNI stats |
| `ThreadLocal` scope | Per `VirtualThread`, not per carrier — per-thread cache becomes per-task allocation |

---

## Self-test

**Q1.** `VirtualThread.createDefaultScheduler()` sets `maxPoolSize` to
`Integer.max(parallelism, 256)` rather than a flat `256`. On a machine with 400
available processors and no system-property overrides, what is the effective
`maxPoolSize`, and why?

<details><summary>Answer</summary>

400. `parallelism` defaults to `availableProcessors()` = 400, and `maxPoolSize =
Integer.max(parallelism, 256) = Integer.max(400, 256) = 400`. The 256 in the
source is a floor that only takes effect when `parallelism` is below it — most
machines today have fewer than 256 processors, which is why "the default is 256"
is a common but only conditionally correct simplification.

</details>

**Q2.** A virtual thread calls a method that acquires a `synchronized` lock, then
inside that block calls `Thread.sleep(500)`. On Java 21, what state does the
virtual thread end up in, and what carrier-level cost does that impose? How does
the answer change on Java 24?

<details><summary>Answer</summary>

On Java 21, the attempt to yield during `Thread.sleep` fails because a monitor
(held by the `synchronized` block) is on the continuation's stack — the state
transition is `RUNNING → PARKING → PINNED`, and the virtual thread blocks its
**carrier** for the full 500 ms exactly as a platform thread would, defeating the
point of using a virtual thread there. On Java 24+, JEP 491 makes object monitors
continuation-aware, so the yield succeeds normally: `RUNNING → PARKING → PARKED`,
the carrier is freed for other work during the sleep, and the virtual thread only
occupies a carrier again once the 500 ms elapses and it is rescheduled.

</details>

**Q3.** Why does the default virtual-thread scheduler use FIFO (async mode)
instead of the LIFO work-stealing that the common `ForkJoinPool` uses for parallel
streams?

<details><summary>Answer</summary>

LIFO work-stealing is optimised for recursively split subtasks of one larger
computation, where a worker's own most-recently-produced subtask has good cache
locality with the work the worker just did — pushing/popping its own queue's head
exploits that. Virtual threads are independent, unrelated tasks with no such
locality relationship to each other, so the property worth optimising is fairness
instead: a task submitted earlier should not be starved behind a burst of later
submissions. FIFO (dequeue from the head in submission order) delivers that
fairness guarantee; LIFO would let newly submitted tasks repeatedly jump ahead of
older ones whenever a worker frees up, which is starvation under sustained load.

</details>

**Q4.** A batch job runs eight CPU-bound virtual threads with no blocking calls at
all, on an 8-core machine using the default scheduler (`parallelism = 8`). A ninth,
I/O-bound virtual thread that only needs to make one quick instrumented HTTP call
is submitted at the same time. What happens to it, and why doesn't FIFO fairness
prevent it?

<details><summary>Answer</summary>

It queues behind the eight CPU-bound tasks and gets no carrier until one of them
either blocks (on an instrumented call — but by assumption they never do) or
finishes entirely, because there is no preemption: a running virtual thread keeps
its carrier until it yields or terminates, regardless of how long that takes. FIFO
fairness only governs the order in which `RUNNABLE` (queued, not-yet-mounted)
tasks are picked up next — it says nothing about how long a task, once `RUNNING`,
is allowed to hold its carrier. The ninth task was queued after the eight
CPU-bound ones (or concurrently with them occupying all eight carriers), so FIFO
correctly puts it next in line for a carrier — it just never gets one until a
carrier is actually freed.

</details>

**Q5.** What, specifically, is a `StackChunk`, and why does "lazy/partial copying"
matter for whether one million parked virtual threads is a heap-sizing problem or
an address-space problem?

<details><summary>Answer</summary>

A `StackChunk` is an ordinary heap-resident Java object that holds the copied live
frames of a virtual thread's continuation while it is unmounted — subject to GC
like any other object, not a reserved region of native address space the way a
platform thread's stack is. Lazy/partial copying means the JVM only copies the
frames actually live between the yield point and the chunk's existing depth, and
only grows the chunk when a call genuinely needs more room, rather than reserving
or copying a fixed maximum stack size up front. Because of that, the per-thread
cost of one million parked virtual threads scales with actual call depth used (an
illustrative few kilobytes each, landing in the low gigabytes in aggregate) rather
than with a fixed per-thread reservation — which is exactly why it is a question
you answer by sizing the heap, not by checking how much virtual address space or
how many OS thread slots you have.

</details>

**Q6.** Name two blocking operations that are **not** instrumented on Java 21, and
state the mechanism-level reason each one still blocks its carrier.

<details><summary>Answer</summary>

Most file I/O (e.g. `Files.readAllBytes`, `FileChannel` reads) is not instrumented
on Java 21 — the underlying native file syscalls were not given a virtual-thread-
aware rewrite in this release, unlike sockets, so the call blocks whatever carrier
is running it for its full duration. Any frame that has called into native code
via JNI also blocks — the JVM cannot relocate an opaque native frame's state into
a `StackChunk` because it does not know that frame's internal layout and the
native code may hold raw pointers tied to that specific OS thread, so the
continuation cannot yield at all while such a frame is on its stack, and the call
simply runs to completion on the carrier that is holding it.

</details>

**Q7.** Explain why setting the system property `jdk.virtualThreadScheduler
.maxPoolSize` to a value below `Runtime.getRuntime().availableProcessors()` is a
trap, using the source's own branching logic.

<details><summary>Answer</summary>

In `createDefaultScheduler()`, when `maxPoolSizeValue` is supplied, the code runs
`maxPoolSize = Integer.parseInt(maxPoolSizeValue); parallelism = Integer.min
(parallelism, maxPoolSize);` — supplying the property does not just cap the pool's
maximum growth, it also clamps `parallelism` down to that same ceiling if
`parallelism` (from `availableProcessors()` or an explicit override) was larger.
Someone setting `maxPoolSize` purely to bound worst-case memory or thread-count
growth under pinning will unintentionally reduce steady-state throughput too,
because the number of carriers actively kept warm (`parallelism`) just got pulled
down to match.

</details>

**Q8.** A production incident report says "we saw high pinned-thread counts, so we
converted every `synchronized` block in the request path to `ReentrantLock`, but
pinning is still happening." What is the most likely explanation, and what tool
would confirm it?

<details><summary>Answer</summary>

The remaining pins are most likely caused by native/JNI frames, not monitors —
converting `synchronized` to `ReentrantLock` only removes the held-monitor pinning
cause (the Java-21-specific one that JEP 491 later fixes at the JVM level), and has
no effect on native-frame pinning, which persists on every current release
including Java 24+. The `jdk.VirtualThreadPinned` JFR event carries a pinning
**reason** field alongside the carrier's identity, which would directly confirm
whether the remaining pins are attributed to a native frame rather than a monitor,
pointing the investigation at whatever native library (e.g. an image-processing
JNI call inside document verification) sits on the affected call paths.

</details>

## Deferred

None.

## Open questions

- The 2 KB-per-parked-virtual-thread figure used in the 1,000,000-virtual-thread
  heap arithmetic (Concept 1) is stated explicitly as an illustrative assumption
  for the arithmetic, not a JDK-guaranteed constant — the JDK does not publish a
  fixed average `StackChunk` payload size, since it depends on call depth and the
  exact frame layout of the release in use. A source that would settle the *exact*
  distribution for a given call shape is a heap dump histogram of `StackChunk`
  instances taken from a running service under the specific workload in question,
  not a static JDK constant.

---

**Leaves covered:** 3.14.1–3.14.18 (18 leaves)
**Leaves deferred:** None
**Diagrams included:** D-159, D-160, D-161, D-162, D-163
**Target version:** Java 21 LTS
**Lines:** 1132
