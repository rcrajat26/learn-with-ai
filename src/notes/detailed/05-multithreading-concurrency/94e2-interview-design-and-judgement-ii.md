# 05 Multithreading and Concurrency — Interview questions: design and judgement II — INTERVIEW (§5.1, questions 5.1.125–5.1.132)

**Target version: Java 21 LTS.** | **Part 5 of 5** | [Index](00-index.md)
Previous: [Interview questions: design and judgement](94e-interview-design-and-judgement.md) · Next: [The trap index](94f-trap-index.md)

---

Second half of the build-it set, plus the four judgement questions that close out the topic: no
code to write, but a position to defend with the same rigor as an implementation.

## 5.1.125 — Implement a barrier

**Clarify first:** fixed party count known up front, or does it vary per round? Does the barrier
need to run a shared action once all parties arrive (aggregate the round's stake settlements
before the next round opens)? Reusable across many rounds, or one-shot?

**Invariant:** no party proceeds past the barrier point until every party has arrived at it, for
this round; the barrier resets automatically for the next round.

```java
final class SettlementRoundBarrier {
    private final int parties;
    private int arrived = 0;
    private int generation = 0; // guards against a late/spurious wakeup from a stale round
    private final Runnable onRoundComplete;

    SettlementRoundBarrier(int parties, Runnable onRoundComplete) {
        this.parties = parties;
        this.onRoundComplete = onRoundComplete;
    }

    synchronized void await() throws InterruptedException {
        int myGeneration = generation;
        arrived++;
        if (arrived == parties) {
            onRoundComplete.run();     // last arriver runs the aggregation, then releases everyone
            arrived = 0;
            generation++;
            notifyAll();
        } else {
            while (myGeneration == generation) wait();
        }
    }
}
```

**Policy:** the `generation` counter is the detail that separates a correct barrier from a broken
one — without it, a thread woken by a spurious wakeup, or a thread from round 2 arriving early,
can misread `arrived == 0` as "barrier still open for round 1" and either double-count or fall
through prematurely. `CyclicBarrier` in the JDK carries this exact field (`generation` /
`Generation` object) for the same reason. A `CountDownLatch` cannot substitute: it is single-use
and has no notion of "reset for the next round."

**Pitfall:** building the reset logic without the generation guard — "just reset `arrived` to 0
when it hits `parties`" looks right until two rounds overlap slightly (a slow party from round N
is still checking `arrived == 0` right as round N+1's first party increments it), corrupting the
count.

**Follow-up:** under contention with a large party count, the single `synchronized` block
serializes arrival — fine for barrier semantics (arrival must be a serialization point by
definition) but means the `onRoundComplete` aggregation runs on whichever thread happens to be
last, which should be fast and non-blocking or it holds every other party waiting on the monitor
exit. Across two JVMs a barrier has no meaning without a shared coordination point — replace it
with a distributed rendezvous (all instances write "round N done" to a shared store, one instance
polls for count == N), which trades a monitor wait for a poll loop or a pub/sub notification.

## 5.1.126 — Implement `CompletableFuture.allOf`

**Clarify first:** does the result need the individual values, or just "all done" (the real
`allOf` returns `CompletableFuture<Void>`, deliberately, because the futures may have different
types)? Should the first failure fail the combined future immediately, or wait for all to settle?

**Invariant:** the returned future completes only after every input future has completed
(successfully or exceptionally), and completes exceptionally if any input did.

```java
static CompletableFuture<Void> allOf(CompletableFuture<?>... futures) {
    CompletableFuture<Void> combined = new CompletableFuture<>();
    AtomicInteger remaining = new AtomicInteger(futures.length);
    if (futures.length == 0) {
        combined.complete(null);
        return combined;
    }
    for (CompletableFuture<?> f : futures) {
        f.whenComplete((value, error) -> {
            if (error != null) {
                combined.completeExceptionally(error); // first failure wins; later ones no-op
            } else if (remaining.decrementAndGet() == 0) {
                combined.complete(null);
            }
        });
    }
    return combined;
}
```

Used to fan out a `PaymentRun`'s per-`WithdrawalTransaction` PSP calls and wait for the whole
batch: `allOf(txFutures.toArray(CompletableFuture[]::new)).thenRun(this::closeRun)`.

**Policy:** `AtomicInteger.decrementAndGet` is the right primitive because completion callbacks
race from arbitrary pool threads with no shared lock already held — a plain `int` with a
`synchronized` block would work too but adds a monitor for no benefit over one atomic op. The
"first failure wins" behavior matches the JDK's actual `allOf`: `completeExceptionally` on an
already-completed future is a documented no-op, so later failures are silently dropped, which is
worth saying out loud as a known limitation rather than a bug.

**Pitfall:** decrementing the counter *before* checking the error branch, or checking `remaining`
inside the error branch too — either shape can double-complete `combined` (once via error, once
via the counter hitting zero), and `complete()` after `completeExceptionally()` is also a silent
no-op, so the bug hides rather than throwing.

**Follow-up:** at scale (a `PaymentRun` batching thousands of withdrawals) this fans out one
callback per future on the common pool by default — pass an explicit executor to `whenComplete`
if the PSP calls are blocking I/O, or the common `ForkJoinPool` starves other work. Across two
JVMs, `CompletableFuture` composition is inherently local; a distributed "wait for all" needs a
count in a shared store (Redis `DECR` to zero) plus a notification channel, which is the same
shape with the atomic swapped for a network round trip.

## 5.1.127 — Implement a thread-safe singleton — five ways, ranked

Mechanics of each are in
[`volatile-and-jmm/03b-basics-lazy-init-and-singletons.md`](volatile-and-jmm/03b-basics-lazy-init-and-singletons.md).
Ranked for a `BonusService` singleton (stateless, expensive-ish to construct — loads promo rules).

| Rank | Technique | Why |
|---|---|---|
| 1 | Enum singleton | Serialization-safe, reflection-safe, one line, JLS-guaranteed thread-safe class init |
| 2 | Static holder class (`Holder.INSTANCE`) | Lazy, no lock ever taken, relies on JLS class-init guarantee |
| 3 | Eager `static final` field | Simplest correct option when eager cost is acceptable — `BonusService` has none |
| 4 | Double-checked locking with `volatile` | Correct only since JMM 2004 with `volatile`; verbose for the same result as #2 |
| 5 | `synchronized` on every `getInstance()` call | Correct but pays a monitor on every call forever, not just at init |

```java
final class BonusService {
    private BonusService() { /* load promo rules */ }
    private static final class Holder {
        static final BonusService INSTANCE = new BonusService();
    }
    static BonusService instance() { return Holder.INSTANCE; }
}
```

**Policy:** rank 1 and 2 both lean on the same JLS guarantee — a class is initialized at most
once, under a lock the JVM already manages, the first time it's actively used — so neither pays a
runtime lock. Enum wins outright when serialization or reflection-based instantiation is a live
concern (both `BonusService` and most singletons in this codebase are not, so #2 is the pragmatic
default people actually reach for).

**Pitfall:** double-checked locking *without* `volatile` on the instance field — this was broken
pre-JMM-2004 and is still the version most engineers half-remember: the constructor's writes can
be reordered past the reference publish, so a second thread can observe a non-null reference to a
partially-constructed object.

**Follow-up:** none of these five change shape under contention — that's their point; the lock (if
any) is paid once. Across two JVMs "singleton" means something different entirely: each JVM gets
its own instance regardless of technique, so a true cross-instance singleton (one `BonusService`
computing promo eligibility for the whole fleet) requires an external coordinator — a leader
election or simply moving the state to a shared store and making the class stateless everywhere.

## 5.1.128 — Make an existing non-thread-safe class thread-safe without editing it

**Clarify first:** can the class be subclassed, or is it `final`? Is the goal full internal
synchronization or just safe *usage* from your call site? Example: `SimpleDateFormat`-style class
(cheap stand-in: an unsynchronized `RestrictionFormatter` with mutable internal scratch state)
used from multiple settlement threads.

**Options, in order of preference:**

1. **Confine it** — one instance per thread via `ThreadLocal<RestrictionFormatter>`, no locking at
   all, no shared state to race on. Best when the class is cheap enough to have one per thread.
2. **Wrap it** — a decorator class exposing the same methods, each `synchronized`, delegating to
   a private instance. Works for any class regardless of `final`, at the cost of full
   serialization of every call.
3. **Pool it** — for expensive-to-construct instances, a small pool (à la 5.1.118) handing out
   exclusive-use instances rather than confining one per thread.
4. **Subclass and override** — only viable if not `final`; usually strictly worse than wrapping
   because it couples you to the parent's internals.

```java
final class SynchronizedRestrictionFormatter {
    private final RestrictionFormatter delegate = new RestrictionFormatter();
    synchronized String format(Restriction r) { return delegate.format(r); }
}
```

**Policy:** `ThreadLocal` confinement is the answer worth leading with — it converts a
synchronization problem into a non-problem by giving every thread its own private copy, at the
cost of one instance per thread instead of one shared instance. The wrapper is the fallback for
when the object is too heavy to duplicate per thread or the thread population is unbounded
(virtual threads make "one per thread" risky at 55k peak concurrent sessions — see 5.1.131).

**Pitfall:** wrapping only *some* of the methods with `synchronized` because "only these two are
called concurrently" — if the unwrapped methods share mutable state with the wrapped ones, this is
exactly as broken as no wrapping at all, just with a false sense of safety.

**Follow-up:** under high thread-count contention the `synchronized` wrapper degenerates to fully
serial access — no different from any other single-lock chokepoint; the `ThreadLocal` approach
doesn't degrade under contention because there is none, but it degrades under *thread count* (5.1
below) since each virtual thread would carry its own copy. Cross-JVM: not applicable — this is a
same-process object graph problem.

## 5.1.129 — You have a shared counter at 100k updates/sec — walk the options

Framing: counting stake settlements, which run at 3,400/sec burst in this domain — scale the
question up to 100k/sec to force the harder answer.

| Option | Mechanism | Verdict at 100k/sec |
|---|---|---|
| `synchronized` + `long` | monitor per increment | Fails — every update serializes through one lock; throughput ceiling far below 100k/sec |
| `AtomicLong.incrementAndGet` | CAS retry loop | Works, but CAS failure rate rises with core count — cache-line ping-pong (false sharing on the one counter) becomes the bottleneck |
| `LongAdder` | striped cells, one per contending thread, summed on read | Best fit — designed exactly for high-write, occasional-read; each thread updates its own cell, no cross-thread CAS contention |
| Per-thread counters + periodic merge | manual striping | Same idea as `LongAdder`, reimplemented by hand — no reason to, unless the merge cadence itself needs custom control |

**Policy:** `LongAdder` is the answer, and the *why* is what's being tested: `AtomicLong` still
funnels every writer through CAS on one shared cache line, so under real contention most CAS
attempts fail and retry, burning cycles without making progress. `LongAdder` gives each contending
thread (JVM detects contention and grows the cell array) its own `Cell`, so increments hit
independent cache lines — reads (`sum()`) walk and add all cells, which is more expensive per
read but reads are rare here (a dashboard poll, not a per-settlement check).

**Pitfall:** reaching for `LongAdder` and then calling `sum()` on the hot path anyway — `sum()`
is not atomic with respect to concurrent increments (it can observe a mid-update value on some
cells) and it's O(number of cells), not O(1) like `AtomicLong.get()`. It's a write-optimized,
read-tolerant structure, not a general-purpose counter.

**Follow-up:** at even higher contention, sharding manually (N `AtomicLong`s, thread ID mod N)
converges to what `LongAdder` already does dynamically, so there's rarely a reason to hand-roll it.
Across two JVMs, neither option shares a count — 100k/sec settlements across a fleet need each
instance's local `LongAdder` periodically flushed to a shared aggregator (a metrics pipeline), not
a single logical counter; there is no lock-free primitive that makes a cross-process counter free.

## 5.1.130 — Your p99 doubled after adding a cache — how could a cache make it slower?

Not a code question — a diagnosis question. Framing: a `RestrictionCache` (5.1.116) was added in
front of the restrction lookup and p99 latency for gated actions doubled.

**Candidate causes, roughly in likelihood order:**

- **Lock contention the cache introduced that wasn't there before.** If the cache serializes
  reads behind a single lock (the write-lock-on-`get` LRU from 5.1.116, at high concurrency), the
  cache itself becomes the new bottleneck — the p50 improves (cache hits are fast) while the p99
  gets worse (everyone queues behind the lock during a burst).
- **Cache miss penalty stacking on top of the original cost**, not replacing it — if a miss still
  does the full original lookup *plus* a cache write, and the hit rate is lower than assumed
  (restrictions genuinely churn for a subset of clients), a large fraction of requests now pay
  original-cost-plus-overhead.
- **GC pressure from cache churn.** A cache holding short-lived entries at high turnover
  (2.4M clients, low hit rate on a cold cache after a deploy) generates garbage fast enough to
  shift GC pause frequency, and pause time shows up as tail latency, not average latency —
  exactly a p99 signature, not a p50 one.
- **False sharing or hot-field contention** on the cache's own bookkeeping (a shared hit/miss
  counter updated on every access) — see 5.1.129; an `AtomicLong` stats counter added "just for
  observability" can itself become the tail-latency source.

**Insight:** a cache trades average latency for tail latency almost by construction whenever the
miss path contends on something the no-cache path didn't — the fix is never "remove the cache", it's
finding which shared structure the cache added and removing *that* contention (shard the cache,
async the stats, size it to the working set so misses are rare enough not to matter).

**Pitfall:** assuming "cache = faster" is an invariant and looking everywhere except the cache
itself for the regression — the failure mode is specifically p99, and p99 problems are almost
always contention or GC, both of which a naively-built cache is a prime suspect for introducing.

## 5.1.131 — When would you choose reactive over virtual threads in 2026, honestly

Judgement question, no code. Framing: identity vendor calls, PSP calls, and the ledger writer all
face this choice.

**Reactive (WebFlux/Reactor) still wins when:**
- The workload is genuinely I/O-bound with **backpressure as a first-class concern** — a slow PSP
  downstream needs the caller to signal "slow down" upstream, and virtual threads have no native
  backpressure primitive; you'd hand-roll it with semaphores (5.1.117) anyway.
- The team already has deep Reactor operator fluency and a large reactive codebase — the
  migration cost of ripping it out for threads is real and virtual threads don't pay for
  themselves on a system that isn't thread-starved today.
- **Non-blocking is required for a reason other than thread count** — e.g. a strict
  single-event-loop ordering guarantee (Node-style), which a thread-per-request model, virtual or
  not, doesn't give you for free.

**Virtual threads win when:**
- The code is **blocking I/O written in the imperative style** already (JDBC, blocking HTTP
  clients) — this describes most of the ledger and PSP call paths — and the only reason it was
  reactive was to avoid exhausting a small platform-thread pool at 55k peak concurrent sessions.
  Virtual threads remove that constraint directly, with no operator-chain rewrite.
- **Debuggability matters** — a virtual-thread stack trace reads like a normal call stack; a
  Reactor operator chain's stack trace is a wall of `onNext`/`subscribe` frames with the actual
  business logic buried or missing entirely.
- **`ThreadLocal`-based code exists and can't be rewritten soon** — it works unmodified under
  virtual threads (mind the footprint per thread — 5.1.128), whereas reactive code must not use
  `ThreadLocal` at all without `Context` shims.

**Insight:** the honest 2026 framing is not "reactive is obsolete" — it's "reactive's core reason
to exist (don't block a scarce platform thread) is gone for new code, but backpressure and
operator composition are real reasons that survive," and JEP 491 (virtual threads no longer pin on
`synchronized`, shipped in JDK 24) removed the last major *correctness* argument against adopting
virtual threads in already-`synchronized` code, which used to be a real blocker.

**Pitfall:** answering "always virtual threads now" — it signals not having internalized what
backpressure actually buys a system under sustained overload, which virtual threads alone don't
provide.

## 5.1.132 — How would you test the concurrent class you just wrote

Judgement question closing the topic — applies to any of 5.1.116–5.1.130's implementations.

**Layers, in order of what catches what:**

1. **Single-threaded correctness first.** Every concurrent class has a sequential behavior
   (a `RestrictionCache` used by one thread is still an LRU cache) — test that in isolation before
   testing concurrency at all, or a concurrency bug and a logic bug look identical in a flaky test.
2. **Deterministic concurrency tests via explicit interleaving control** — a
   `CyclicBarrier`-gated test that forces N threads to reach a specific point simultaneously
   (e.g. all N call `put()` on a full `WithdrawalBuffer` at once) is far more reliable than
   "spin up 100 threads and hope for a race," which passes most of the time even with a real bug
   present.
3. **Stress/soak tests for throughput claims** — the `LongAdder` vs `AtomicLong` choice (5.1.129)
   is a performance claim, not a correctness one; it needs a JMH-style benchmark under realistic
   contention (many threads, short critical section), not a unit test.
4. **`jcstress` for memory-visibility claims specifically** — a happens-before bug (a missing
   `volatile`, a broken double-checked-locking) will not reliably reproduce under a normal JUnit
   test even run thousands of times on x86, because the JMM violation may never manifest on a
   strongly-ordered architecture; `jcstress` runs the same interleaving under forced scheduling
   pressure and on multiple hardware memory models.
5. **Chaos at the boundary** — kill a thread mid-operation (interrupt it inside `put()`), verify
   the invariant still holds afterward (no leaked permit, no corrupted count) — this is what
   catches the missing-`finally` class of bug (5.1.117's pitfall).

**Insight:** "run it under load and see if it breaks" is necessary but is the weakest tool in this
list — it has no theory of *why* it would catch a given bug, whereas barrier-gated deterministic
interleaving tests are constructed specifically to hit the exact race the code is suspected of
having.

**Pitfall:** treating a concurrency test suite that's "green for a week in CI" as proof of
correctness — most concurrency bugs are probabilistic and schedule-dependent; a `jcstress`-style
tool that deliberately forces contended interleavings finds bugs that a thousand normal CI runs
never surface, because normal CI runs rarely hit the unlucky schedule at all.

---

**Leaves covered:** 5.1.125–5.1.132 (8 questions)
**Leaves deferred:** none
**Diagrams included:** none
**Target version:** Java 21 LTS
**Lines:** 344
