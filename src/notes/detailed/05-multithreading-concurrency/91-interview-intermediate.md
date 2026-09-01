# 05 Multithreading and Concurrency — Part 2 interview wrap-up — INTERMEDIATE (§2.1–§2.15)

**Target version: Java 21 LTS.** | **Part 2 of 5** | [Index](00-index.md)
Previous: [Version delta, Java 5 to 25](version-delta/01-java-5-to-25.md) · Next: [The object header and the mark word](synchronized/02-internals-header-and-mark-word.md)

Part 2 is the judgement tier. Part 1 taught mechanism — what `happens-before` means, how `synchronized` escalates, how AQS queues waiters. Part 2 teaches *decisions*: which primitive, which pool size, which collection, which shutdown policy, and what number backs each answer. This file drills that recall without re-deriving the mechanism — it assumes §2.1–§2.15 have already been read.

## Part 2 summary table

Fifteen subjects, fifteen decisions. The table is deliberately dense — every cell is something a candidate should be able to reproduce cold, without deriving it from first principles under interview pressure. Read the "wrong answer" column as a checklist of beliefs to actively unlearn, not as a joke at the expense of junior engineers: every one of these is a belief a competent engineer holds until the first time it costs them an incident.

| Subject | The decision it teaches | The number/formula to produce | The wrong answer people give | The follow-up it invites |
|---|---|---|---|---|
| §2.1 Master cost/latency/footprint/guarantee tables | Which axis dominates for this workload — cost, latency, footprint, or guarantee strength | Order-of-magnitude ladder: uncontended `synchronized` ~tens of ns, contended lock ~µs, park/unpark ~µs–ms, blocking I/O ~ms–s | "Locks are slow" as a blanket claim, ignoring that uncontended locking is nearly free | "Which of these have you actually measured versus assumed?" |
| §2.2 Contention economics | Whether contention, not raw throughput, is the bottleneck | `AtomicLong` vs `LongAdder` crossover at roughly 2–4 concurrent writers | Reaching for `LongAdder` everywhere "because it's faster" | "What does `LongAdder` cost you on the read side?" |
| §2.3 Choosing a synchronization primitive | `synchronized` vs `ReentrantLock` vs `StampedLock` vs `Semaphore` vs lock-free | Read-write lock crossover at roughly 90% reads | "`ReentrantLock` is strictly better than `synchronized`" | "When does `synchronized` still win outright?" |
| §2.4 Pool sizing and executor configuration | CPU-bound vs I/O-bound sizing formula, and which rejection policy | I/O-bound pool: `8 cores × 0.9 utilisation × (1 + 100 ms wait / 2 ms compute) ≈ 8 × 0.9 × 51 = 367` | Sizing every pool to `availableProcessors()` regardless of workload shape | "What happens to that formula if the downstream wait spikes to 500 ms?" |
| §2.5 The atomicity decision | Single-variable CAS vs `synchronized` block vs `Atomic*` composite | A read-then-write on a `Reservation` needs the block, not the field, to be atomic | Assuming `AtomicLong.incrementAndGet()` makes a two-field update atomic | "Why doesn't making every field `Atomic*` fix the invariant?" |
| §2.6 The concurrent-collection decision | `ConcurrentHashMap` vs `CopyOnWriteArrayList` vs `ConcurrentSkipListMap` vs `BlockingQueue` | `CopyOnWriteArrayList` on 2.8M appends/day copies the backing array on every write — O(n) per write | Using `CopyOnWriteArrayList` for a write-heavy structure "because it's thread-safe" | "What access pattern actually justifies copy-on-write?" |
| §2.7 Producer–consumer and backpressure | Bounded vs unbounded queue, and what backpressure actually buys you | A 1,000-deep queue in front of a 50 ms service adds up to 50 s of tail latency at saturation | Making the queue unbounded "so nothing gets rejected" | "What should happen instead of growing the queue — reject, shed, or slow the producer?" |
| §2.8 `CompletableFuture` in anger | `thenApply` vs `thenApplyAsync`, default pool vs custom executor, exception shape | Chaining onto the common pool silently starves other CPU-bound work sharing it | Assuming every `.thenApply` runs on the thread that completed the future | "What breaks when a stage in the chain blocks on I/O?" |
| §2.9 Virtual threads in production | When virtual threads help versus when they don't | 55k peak concurrent sessions as platform threads is untenable; as virtual threads it's routine | "Virtual threads make everything faster," including CPU-bound work | "What still pins a virtual thread on Java 21, and what changed in Java 24?" |
| §2.10 Thread-safe class design | Confinement vs immutability vs synchronization vs a bespoke concurrent class | A `Wallet`'s four buckets need one lock around the invariant, not four locks around each field | Making every field `volatile` and calling the class thread-safe | "What's the difference between thread-safe and atomic-as-a-whole?" |
| §2.11 `ThreadLocal` and context propagation | When `ThreadLocal` helps versus when it silently breaks under pooling or async hops | A per-request cache regression: expected 200 entries, observed 443,267 after a leak across pooled threads | Assuming `ThreadLocal.remove()` isn't needed because "the thread dies anyway" | "How does this same leak show up with virtual threads instead of a pool?" |
| §2.12 Testing and verifying concurrent code | Stress test vs model checker vs code review for a given race | 14,000 concurrent sessions against a 20-connection pool as the stress scenario that actually reproduces exhaustion | Trusting a test that "passed 100 times" as proof of no race | "What would actually falsify this test — what interleaving does it not cover?" |
| §2.13 Concurrency-adjacent utility surface | `CountDownLatch` vs `CyclicBarrier` vs `Phaser` vs `Exchanger` vs `Semaphore` as a rate limiter | A `Semaphore(20)` bounding concurrent PSP calls, not the connection pool itself | Using a `CountDownLatch` where the count needs to reset — that's a `CyclicBarrier`'s job | "What happens if a party never arrives at the barrier?" |
| §2.14 Concurrency beyond one JVM | In-process lock vs distributed lock vs idempotency key vs optimistic versioning | Ledger write rate of 230/sec sustained, 13,600/sec peak — no single-JVM lock reaches across that fleet | Assuming a `synchronized` method prevents a double-charge across two pods | "Why does an idempotency key beat a distributed lock here?" |
| §2.15 The Java 5 → 25 version delta | Which concurrency feature is stable, preview, or removed at Java 21 versus later LTS | JEP 491 final in JDK 24; JEP 506 (scoped values) final in JDK 25; structured concurrency still preview in JDK 25 | Citing scoped values or structured concurrency as final on Java 21 | "What's still preview on the very latest JDK, and why hasn't it shipped?" |

These ten cover the full arc of Part 2, from picking a pool size to reasoning about a fleet of pods. Each answer is written at the length an actual candidate would speak it — roughly 45 to 60 seconds — because a staff-level answer to "how would you decide" is a short paragraph with a number in it, not a one-line keyword definition and not a five-minute monologue. Every answer below closes with the follow-up question an interviewer typically asks next, and a one-line answer to that follow-up, because the follow-up is where the judgement tier is actually assessed — anyone can recite the first-order tradeoff, but the follow-up tests whether the candidate understands the *boundary* of their own answer.

## Interview questions

**Q1. You're sizing a thread pool for the deposit-confirmation callback handler, which calls out to the card PSP and does almost no CPU work. Walk me through how you size it.**

I'd start from the shape of the work, not a fixed number. This is I/O-bound — each task spends most of its life waiting on the PSP, not the CPU. The formula is `threads = cores × target utilisation × (1 + wait/compute)`. With 8 cores, aiming for 90% utilisation, a 100 ms downstream wait and about 2 ms of actual compute per callback, that's `8 × 0.9 × (1 + 100/2) = 8 × 0.9 × 51 ≈ 367` threads.

That number only holds for this specific wait-to-compute ratio, and I'd sanity-check it against Little's law rather than trust the formula in isolation: at 1,200 stake reservations/sec against the PSP's 240 ms p50, that's roughly `1,200 × 0.24 = 288` concurrent in-flight calls at steady state, which is the same order of magnitude as the 367 the sizing formula produced — a useful cross-check, not a coincidence. If the PSP's p99 spikes to 11 s instead, the same law gives `1,200 × 11 = 13,200` concurrent calls, which no platform-thread pool should ever try to hold open — that's the signal to reach for virtual threads or an explicit backpressure mechanism instead of scaling the pool further.

```java
int cores = Runtime.getRuntime().availableProcessors();   // 8 on the reference box
double targetUtilisation = 0.9;
double waitMillis = 100, computeMillis = 2;
int poolSize = (int) Math.ceil(cores * targetUtilisation * (1 + waitMillis / computeMillis));
// poolSize == 367
```

- CPU-bound pools: size near `cores + 1`, never past it, because more threads than cores just adds context-switch overhead with no extra throughput.
- I/O-bound pools: size from the wait/compute ratio, and re-derive the number whenever the downstream latency profile shifts.
- Either way, cap the queue — an unbounded queue in front of a slow PSP converts overload into unbounded tail latency instead of surfacing it as an explicit rejection.

*Follow-up: "What if the PSP has a hard concurrency cap of 200 calls?"* — bound actual concurrency with a `Semaphore(200)` around the call site, independent of pool size, so the pool can still schedule work but never floods the PSP past what it can take.

**Q2. `AtomicLong` versus `LongAdder` for the stake-settlement counter running at 3,400/sec burst — which do you pick, and why isn't the answer always "LongAdder"?**

It depends on writer count and whether I ever need to read the exact value mid-flight. `AtomicLong` funnels every writer through one CAS loop on one cache line — fine up to roughly 2–4 concurrent writers, but past that the retry storm dominates and throughput falls off a cliff as cores spin retrying instead of doing work. `LongAdder` spreads writes across striped cells that only reconcile on `sum()`, so it scales far better under contention — 3,400/sec across dozens of settlement threads is squarely in `LongAdder` territory.

The cost is twofold: `sum()` is not a linearizable snapshot — called concurrently with in-flight `add()`s, it can return a value that doesn't correspond to any single instant, only converging once writers quiesce — and the striped cells cost more memory than a single `long`, scaling with observed contention rather than a fixed size. If I needed the counter for a CAS-based invariant instead — "reject this stake if reservations just crossed a hard cap" — I'd keep `AtomicLong`, because `compareAndSet` is the operation I actually need and `LongAdder` doesn't expose an equivalent that's cheap to use correctly.

```java
// Under low contention (0-1 concurrent writer), both cost about the same:
AtomicLong reservations = new AtomicLong();
reservations.incrementAndGet();          // single CAS, no retry storm

// Under high contention (dozens of settlement threads), LongAdder wins:
LongAdder settlementCount = new LongAdder();
settlementCount.increment();             // writes to a striped Cell, rarely contends
long snapshot = settlementCount.sum();   // reconciles cells; not a linearizable read
```

Numbers to have ready:

- Crossover point: roughly 2–4 concurrent writers before `LongAdder` overtakes `AtomicLong`.
- Settlement burst: 3,400/sec, comfortably past the crossover.
- Memory cost: `LongAdder`'s cell array grows with observed contention, not with a fixed cap chosen up front.

*Follow-up: "What does `LongAdder.sum()` actually do under the hood?"* — it walks the base value plus every striped `Cell` and sums them without locking, so it's cheap but only eventually accurate.

**Q3. Compare `ReentrantReadWriteLock` against a plain `ReentrantLock` for guarding the in-memory restriction cache that's read on every gate check and written only when compliance updates a restriction.**

This is the textbook case for a read-write lock, but only past a read/write ratio threshold — the crossover where tracking readers and writers separately actually pays for itself is roughly 90% reads. A restriction cache checked on nearly every stake and deposit, but written only when compliance acts, sits well past that line — the lock's shared mode lets thousands of concurrent gate checks proceed without blocking each other, serializing only against the rare write. Below that threshold, the extra state-tracking overhead of a read-write lock actually costs more than it saves, and a plain `ReentrantLock` — or even `synchronized` — wins outright.

I'd also consider `StampedLock`'s optimistic-read mode here, since restriction checks are short and retryable: take a stamp, read the fields, then validate the stamp and retry as a pessimistic read only on the rare case of a concurrent write. That avoids taking any lock at all in the common case, at the cost of code that's noticeably harder to get right — which is why I'd still default to `ReentrantReadWriteLock` first, since it's easier to reason about and the read/write skew already justifies the complexity without needing the extra optimistic-read machinery.

```java
final StampedLock lock = new StampedLock();

RestrictionSet checkGate(ClientId clientId) {
    long stamp = lock.tryOptimisticRead();
    RestrictionSet snapshot = restrictionsByClient.get(clientId);   // read without blocking
    if (!lock.validate(stamp)) {                                    // a writer interleaved — retry pessimistically
        stamp = lock.readLock();
        try { snapshot = restrictionsByClient.get(clientId); }
        finally { lock.unlockRead(stamp); }
    }
    return snapshot;
}
```

Numbers to have ready:

- Read/write crossover: roughly 90% reads before a read-write lock earns its bookkeeping cost.
- Restriction cache: read on essentially every stake and deposit, written only on compliance action — far past that line.

*Follow-up: "What's the risk of writer starvation with a read-write lock?"* — a nonstop stream of readers can starve a waiting writer unless the implementation is fair; `ReentrantReadWriteLock`'s fair mode trades some read throughput to fix that.

**Q4. Your team wants an unbounded queue in front of the withdrawal-processing worker pool "so nothing ever gets rejected." What do you say?**

I'd push back, because unbounded queues don't remove backpressure — they hide it and convert it into latency instead of an explicit signal. If the downstream withdrawal service degrades to 50 ms per call and the queue grows to 1,000 items deep, the last item in that queue waits up to 50 seconds before it's even attempted, long after any caller's timeout has expired — so we're doing wasted work on requests nobody is still waiting for, while looking healthy on a naive "no rejections" dashboard. A bounded queue with an explicit rejection or shedding policy makes the failure visible immediately, which lets upstream retry or queue at a layer that can actually absorb it — batching bank withdrawals into a `PaymentRun` instead of processing them synchronously one at a time, for instance.

The rejection policy itself is a real decision, not a default to accept:

- `AbortPolicy` — throws `RejectedExecutionException` immediately; use when the caller can see the failure and retry or fail fast.
- `CallerRunsPolicy` — runs the task on the submitting thread, which naturally slows the producer; use when the caller can afford to do the work itself.
- `DiscardPolicy` — silently drops the task; almost never correct for anything touching money.
- `DiscardOldestPolicy` — drops the oldest queued task to make room; only correct when older work is genuinely less valuable than newer work.

```java
new ThreadPoolExecutor(
        20, 20, 0L, TimeUnit.MILLISECONDS,
        new ArrayBlockingQueue<>(1_000),              // bounded — the 50 s tail-latency ceiling
        new ThreadPoolExecutor.AbortPolicy());         // explicit rejection, not silent growth
```

Numbers to have ready: a 1,000-deep queue in front of a 50 ms downstream call adds up to 50 s of tail latency at saturation — that's the number that turns "just make the queue bigger" into a concrete, falsifiable SLA conversation instead of a vague preference.

*Follow-up: "What rejection policy would you pick for withdrawals specifically?"* — `AbortPolicy`, because a silently dropped or reordered withdrawal is a ledger integrity problem, and the caller needs an explicit signal to retry through the normal request path.

**Q5. Walk me through chaining a `CompletableFuture` pipeline for "verify identity document, then check screening, then activate the account" — what goes wrong if you get the async variants wrong?**

The chain is `verify().thenComposeAsync(v -> screen(v), executor).thenApply(this::activate)`. The choice between `thenApply` and `thenApplyAsync` decides which thread runs the continuation: `thenApply` runs on whichever thread completes the prior stage — which could be the calling thread if the future was already done, or a `ForkJoinPool.commonPool()` worker if it wasn't — while `thenApplyAsync` with an explicit executor guarantees the continuation runs on a thread I control.

```java
verify(applicationId)
    .thenComposeAsync(this::screen, screeningExecutor)   // explicit executor: I own the thread
    .thenApply(this::activate)                            // implicit: runs wherever the prior stage finished
    .exceptionally(this::toReferral);
```

Getting this wrong means CPU-light glue code and CPU-heavy document verification can end up sharing the common pool with unrelated parallel streams elsewhere in the JVM, and one slow stage starves everything else queued behind it. I'd use `thenComposeAsync` with a dedicated executor for any stage that calls out to the identity vendor or screening provider, since those calls block, and reserve the default pool only for pure, fast transformations. Exceptions propagate as a wrapped `CompletionException` down the chain, so a single `.exceptionally()` or `.handle()` at the end catches failures from any stage without wrapping each one in its own try/catch.

*Follow-up: "What happens to an exception thrown inside a `thenApply` stage?"* — it short-circuits the remaining `thenApply`/`thenCompose` stages and surfaces at the next `.exceptionally()` or `.handle()`, wrapped in `CompletionException`.

**Q6. When do virtual threads actually help in this system, and when do they not?**

They help wherever the bottleneck is thread count, not CPU — the onboarding gateway holding 14,000 steady, 55,000 peak concurrent sessions is the canonical case. Modeling each session as a platform thread would exhaust the OS well before it exhausts the CPU, since platform threads carry megabyte-scale stacks and OS-level scheduling cost that's order-of-magnitude far heavier than a virtual thread's continuation object; virtual threads are cheap enough that one-per-session is routine, and each blocking call — waiting on the identity vendor's p99 38 s, or the watchlist provider's 25 s — just unmounts the virtual thread from its carrier instead of parking an expensive OS thread.

They do not help CPU-bound work like scoring an affordability model or computing a payout batch — there, the bottleneck is core count, and more virtual threads just means more contention for the same cores with extra scheduling overhead on top. The one gotcha for Java 21 specifically is pinning: a virtual thread blocked inside a `synchronized` block pins its carrier thread instead of unmounting, so any `synchronized`-guarded call to a blocking resource under virtual threads reintroduces exactly the platform-thread scaling limit we were trying to avoid — swapping the `synchronized` block for a `ReentrantLock` around the same critical section removes the pin on Java 21.

```java
// Java 21: this pins the carrier thread for the duration of the PSP call.
synchronized (pspClientLock) { pspClient.charge(withdrawal); }

// Java 21 fix: swap the monitor for a lock that unmounts cleanly.
pspClientLock.lock();
try { pspClient.charge(withdrawal); } finally { pspClientLock.unlock(); }
```

Numbers to have ready: 55k peak concurrent sessions is the footprint argument for virtual threads — that many platform threads, at roughly a megabyte of stack each, is a gigabyte-plus of stack space before a single request is served; virtual threads carry no such per-thread reservation.

*Follow-up: "How would that pinning problem look different on Java 24?"* — JEP 491 shipped final in JDK 24 and removes `synchronized`'s pinning behavior, so the same code stops pinning without any change; `-Djdk.tracePinnedThreads` was removed alongside it since it's no longer needed for that case.

**Q7. Design the `Wallet` class so it's thread-safe against concurrent stake reservations and deposit credits touching its four buckets. What's the actual unit of atomicity?**

The unit of atomicity is the invariant, not the field — `CASH_AVAILABLE`, `CASH_RESERVED`, `BONUS_AVAILABLE`, and `BONUS_RESERVED` move together whenever a stake is reserved, so the lock has to protect all four as one group, not each individually.

```java
final class Wallet {
    private final ReentrantLock lock = new ReentrantLock();
    private Money cashAvailable, cashReserved, bonusAvailable, bonusReserved;

    StakeSplit reserve(Money stakeAmount) {
        lock.lock();
        try {
            StakeSplit split = computeSplit(stakeAmount, bonusAvailable);
            bonusAvailable = bonusAvailable.subtract(split.bonusPortion());
            bonusReserved  = bonusReserved.add(split.bonusPortion());
            cashAvailable  = cashAvailable.subtract(split.cashPortion());
            cashReserved   = cashReserved.add(split.cashPortion());
            return split;
        } finally { lock.unlock(); }
    }
}
```

Making each field `volatile` or wrapping each in its own `AtomicLong` would make individual reads and writes atomic but would do nothing to stop two threads from interleaving a reservation such that cash and bonus buckets disagree about a stake's split — the four-bucket invariant is a relationship between fields, and no per-field guarantee expresses that. Confinement is the alternative I'd actually prefer where possible: route all mutations for one wallet through a single-threaded actor-like executor keyed by `ClientId`, which removes the lock entirely at the cost of an extra hop and some added latency under low contention.

Numbers to have ready: the win/void/loss asymmetry is the sharpest edge of this invariant — reserved bonus returns as cash on a win, as bonus on a void, and moves to `HOUSE_REVENUE` on a loss, so the four-bucket update is never a simple decrement-then-increment even outside of concurrency concerns; the lock has to protect the whole branch, not just the arithmetic.

*Follow-up: "Why not just make `Wallet` immutable and replace it wholesale on each stake?"* — you can, with `compareAndSet` on an `AtomicReference<Wallet>`, but that pushes retry-on-conflict logic to every writer and gets expensive under real contention; a lock is simpler here because writes are the common case, not the rare one.

**Q8. Your logs show that trace IDs go missing on roughly a third of async continuation log lines during onboarding. Where do you look first?**

I'd suspect `ThreadLocal`-based context propagation across an async boundary before anything else, because that's the textbook failure mode. If the trace ID lives in an MDC `ThreadLocal` set at the start of a request on the request thread, and a stage of the pipeline hops onto `CompletableFuture.supplyAsync()` without an executor that copies MDC context, the continuation runs on a different thread — a common-pool or executor worker — that never had `MDC.put` called on it, so `MDC.get("traceId")` returns `null` on that thread even though it was set moments earlier on the caller.

```java
Executor mdcAware(Executor delegate) {
    return task -> {
        Map<String, String> context = MDC.getCopyOfContextMap();
        delegate.execute(() -> {
            if (context != null) MDC.setContextMap(context);
            try { task.run(); } finally { MDC.clear(); }
        });
    };
}
```

I'd also check whether the leak runs the other way — a pooled thread that picked up a stale trace ID from a previous request because nothing called `MDC.clear()` on completion — since that produces the opposite symptom, a trace ID that's present but wrong rather than absent, and it's the same root cause: `ThreadLocal` state outliving the logical unit of work it was meant to describe.

Numbers to have ready: a per-request cache built on the same flawed assumption regressed from an expected 200 entries to 443,267 once pooled threads started accumulating stale `ThreadLocal` state across requests instead of being cleared — the same missing `remove()` call that drops trace ids also leaks whatever else was stashed alongside them.

*Follow-up: "Why does this get worse, not better, with virtual threads?"* — it doesn't get worse mechanically, but virtual threads make thread-hopping far more common since every blocking call can trigger an unmount/remount onto a different carrier, so any code that assumed "same thread throughout" breaks more often, not less; scoped values were designed as the eventual fix.

**Q9. How would you actually test that the withdrawal ledger doesn't double-credit under concurrent settlement and chargeback processing for the same transaction?**

A test that runs the two operations once, sequentially, and asserts the final balance proves nothing about the race — the bug only shows up under interleaving. I'd write a stress test that fires both operations from separate threads at the same `WithdrawalTransaction`, gated behind a `CyclicBarrier` so they start as close to simultaneously as the JVM allows, and repeat it thousands of times looking for any run where the ledger sums don't balance — because a race that fires one time in ten thousand still fires in production at 230 writes/sec sustained, 13,600/sec peak. I'd size the reproduction scenario against a real bottleneck too — 14,000 concurrent sessions against a 20-connection pool is the kind of ratio that reliably surfaces pool-exhaustion races that a two-thread unit test never would.

That catches the common case but not every interleaving, so alongside it I'd add an invariant check baked into the ledger write path itself — every write validates against `LedgerImbalanceException` before committing — so that even an interleaving the stress test didn't happen to hit still gets caught the moment it occurs, in test or in production. For genuinely subtle races I'd reach for a model checker or an explicit interleaving-exploration tool rather than trusting statistical stress testing alone, since "passed 100,000 iterations" is evidence, not proof.

```java
CyclicBarrier gate = new CyclicBarrier(2);
Runnable atGate = () -> { try { gate.await(); } catch (Exception ignored) {} };

Thread settle = new Thread(() -> { atGate.run(); ledger.settle(transactionId); });
Thread chargeback = new Thread(() -> { atGate.run(); ledger.chargeback(transactionId); });
settle.start(); chargeback.start();
settle.join(); chargeback.join();

assertLedgerBalances(transactionId);   // run this assertion, not a fixed final-balance check, every iteration
```

Numbers to have ready: 14,000 concurrent sessions against a 20-connection pool is the ratio that reliably reproduces pool-exhaustion races — a two-thread unit test at that scale proves nothing about what happens at 700-to-1 contention.

*Follow-up: "What's wrong with just adding `Thread.sleep()` calls to force the interleaving you expect?"* — it only tests the one interleaving you hand-picked and gives false confidence about every other ordering; use a barrier or a deterministic scheduler instead.

**Q10. What breaks when a service moves from a single JVM with `synchronized` guarding "one withdrawal per client at a time" to five pods behind a load balancer?**

The lock stops guarding anything the moment there's more than one JVM, because `synchronized` only ever excludes threads inside the same process — it has no visibility into what another pod is doing. Two withdrawal requests for the same client landing on two different pods can both pass a `synchronized`-guarded check and both proceed, producing a double payout that no in-process lock could have prevented. The fix has to live at a layer both pods share:

- **Distributed lock** (database row lock, or a coordination service) — works, but adds a liveness dependency and has to handle lease expiry mid-operation.
- **Idempotency key** enforced by a unique constraint — the request carries a key the ledger deduplicates on; a retried request with the same key returns the original result instead of creating a second one.
- **Optimistic versioning** on the `WithdrawalTransaction` row — a second concurrent write loses the compare-and-swap and is rejected outright.

For QuizStakes specifically I'd reach for the idempotency key first — it's simpler to reason about than a distributed lock, doesn't need a coordination service, and degrades safely under retries, which is exactly the failure mode a load-balanced payment path needs to survive.

```java
@Transactional
WithdrawalResult process(WithdrawalRequest request) {
    // unique constraint on idempotency_key does the cross-pod exclusion the synchronized block cannot
    return withdrawalRepository.findByIdempotencyKey(request.idempotencyKey())
            .map(WithdrawalResult::fromExisting)
            .orElseGet(() -> withdrawalRepository.save(request.toNewTransaction()));
}
```

Numbers to have ready: ledger write rate of 230/sec sustained, 13,600/sec peak — any coordination mechanism that adds a network round trip per write has to survive that peak without becoming the new bottleneck, which is another point in the idempotency key's favor over an external distributed lock.

*Follow-up: "Why is a distributed lock worse here than an idempotency key?"* — a lock adds a liveness dependency on the coordination service and still has to handle lease expiry mid-operation, while an idempotency key needs nothing more than a unique constraint already enforced by the database.

## Predict the output

Five snippets, each complete and compiling on Java 21. Two turn on nothing exotic — just the same discipline Part 2 already demanded: know the actual guarantee an API gives you, not the guarantee its name suggests. The other three are the specific Part 2 failure modes named in this file's brief: a pool that deadlocks on its own task dependency, a rejection policy that behaves differently after shutdown than before it, and a container CPU quota that silently changes a sizing formula's input. Read each snippet before reading the answer — the value is in predicting wrong once and seeing exactly where the intuition broke.

**Puzzle 1 — a pool that deadlocks on task dependency**

```java
ExecutorService reviewPool = Executors.newFixedThreadPool(1);

Future<ScreeningVerdict> outer = reviewPool.submit(() -> {
    Future<DocumentVerdict> inner = reviewPool.submit(() -> DocumentVerdict.CLEARED);
    return new ScreeningVerdict(inner.get(), Instant.now());
});

System.out.println(outer.get());
```

**Output:** the program never terminates — `outer.get()` blocks forever.

The pool has exactly one worker thread. That thread is running the outer task, which calls `inner.get()` and blocks waiting for the inner task to complete. But the inner task is still sitting in the pool's queue, because the only worker thread is busy blocking on it. Nothing will ever run it. This is the single-threaded-pool self-submission deadlock: a fixed pool of size N deadlocks the instant a task submitted to it depends on the completion of another task submitted to the same pool, once more than N such tasks are chained at once.

**Insight:** this isn't a bug in `ExecutorService` — it's a structural hazard of using one pool for both the outer orchestration and the inner leaf work. The fix is to run dependent sub-tasks on a separate pool, or to restructure with `CompletableFuture.supplyAsync(..., innerPool)` so outer and inner never compete for the same fixed worker count. **Interview:** "how would you detect this in production before it deadlocks a whole pool?" — a thread dump showing every pool worker `WAITING` on a `Future.get()` for a task still `NEW` in the same pool's queue is the signature; watchdog alerts on worker-utilization-at-100%-with-zero-throughput catch it faster than waiting for a timeout.

Also watch for the same shape in disguise:

- a `ForkJoinPool` task that joins a sibling submitted to the same pool without `ForkJoinPool.managedBlock` — usually self-heals via work-stealing, but not always, depending on parallelism.
- a `newFixedThreadPool(N)` where N dependent stages are chained more than N deep — the deadlock is latent until load pushes past N simultaneous chains.
- a review-queue design where an `AA-710 REVIEW_IN_PROGRESS` case's completion callback is submitted back onto the same bounded operator-assignment pool that is currently full.

**Puzzle 2 — `CallerRunsPolicy` after `shutdown()`**

```java
ThreadPoolExecutor pool = new ThreadPoolExecutor(
        1, 1, 0L, TimeUnit.MILLISECONDS,
        new SynchronousQueue<>(),
        new ThreadPoolExecutor.CallerRunsPolicy());

pool.shutdown();
pool.execute(() -> System.out.println("settling stake reservation"));
System.out.println("submit returned");
```

**Output:**
```
submit returned
```
`"settling stake reservation"` is never printed, and no exception is thrown.

`CallerRunsPolicy.rejectedExecution` is implemented as `if (!e.isShutdown()) { r.run(); }` — it only runs the rejected task on the caller's thread when the executor is *not* shutdown. Here the pool was already shut down before `execute()` was called, so the `SynchronousQueue` has no consumer, the task is rejected, `isShutdown()` is true, and the policy silently drops the task instead of running it or throwing.

**Pitfall:** people assume `CallerRunsPolicy` guarantees the task always runs somewhere — it doesn't, once the pool is shutting down, and the caller gets no signal that work was discarded. Anyone relying on `CallerRunsPolicy` as a last line of defense against lost withdrawal-settlement tasks needs to check `isShutdown()` themselves before submitting, or accept that a task submitted during shutdown may simply vanish. **Interview:** "does `CallerRunsPolicy` ever silently drop a task?" — yes, exactly this case, immediately after `shutdown()`.

**Puzzle 3 — a lost MDC trace id across an async hop**

```java
MDC.put("traceId", "onboard-4471");

CompletableFuture<Void> future = CompletableFuture
        .supplyAsync(() -> "screening result for " + MDC.get("traceId"))
        .thenAccept(System.out::println);

future.join();
```

**Output:**
```
screening result for null
```

`MDC.put` writes to a `ThreadLocal` on the calling thread. `CompletableFuture.supplyAsync()` with no explicit executor runs its supplier on a `ForkJoinPool.commonPool()` worker thread, which never had `MDC.put` called on it and therefore sees no trace ID — `MDC.get("traceId")` returns `null` on that thread even though it was set moments earlier on the caller.

**Pitfall:** logging frameworks that rely on MDC for trace correlation lose the trace id the instant work crosses an async boundary unless the executor is wrapped to copy the context map at submission time. **Fix:** wrap the executor as shown in Q8, or capture `MDC.getCopyOfContextMap()` before the async call and call `MDC.setContextMap(...)` at the top of the supplier. **Interview:** "would `thenApply` instead of `supplyAsync` fix this?" — no; the loss happens at the async hop itself, regardless of which stage in the chain it occurs at, as soon as execution moves to a thread that never had the `ThreadLocal` set.

With the wrapped executor from Q8 in place, the same snippet prints correctly:

```java
Executor traced = mdcAware(ForkJoinPool.commonPool());
CompletableFuture.supplyAsync(() -> "screening result for " + MDC.get("traceId"), traced)
        .thenAccept(System.out::println);
// screening result for onboard-4471
```

**Puzzle 4 — `LongAdder.sum()` under concurrent writes**

```java
LongAdder settlements = new LongAdder();
ExecutorService pool = Executors.newFixedThreadPool(4);
CountDownLatch start = new CountDownLatch(1);

for (int i = 0; i < 4; i++) {
    pool.submit(() -> {
        try { start.await(); } catch (InterruptedException e) { Thread.currentThread().interrupt(); }
        for (int j = 0; j < 1000; j++) settlements.increment();
    });
}
start.countDown();
Thread.sleep(50);
System.out.println(settlements.sum());
```

**Output:** any value from `0` up to `4000`, most likely close to but not guaranteed to equal `4000` — the exact number is not deterministic.

The four worker threads race to add 1,000 each, but `sum()` is called from the main thread after only a fixed 50 ms sleep, with no `join()` or barrier guaranteeing the workers have finished. `LongAdder.sum()` itself is not a linearizable snapshot even when the writers *have* finished — it walks the base and every striped cell without locking, so a call made concurrently with in-flight `add()`s can observe a partially-updated set of cells. Here the bigger issue is simpler: the test has a race between "workers finish" and "main thread reads," so the legal output set is genuinely `[0, 4000]`, with `4000` only guaranteed if the workers are joined first.

**Fix:** replace the sleep with `pool.shutdown(); pool.awaitTermination(1, TimeUnit.SECONDS);` before reading `sum()`; only then is `4000` guaranteed. **Insight:** this is the same shape of bug as Q9's ledger race — a plausible-looking synchronization primitive (`LongAdder`, a fixed sleep) standing in for an actual happens-before edge, when only `join()`, `awaitTermination()`, or a latch actually establishes one.

The corrected version, with the guarantee actually in place:

```java
pool.shutdown();
if (!pool.awaitTermination(1, TimeUnit.SECONDS)) {
    throw new IllegalStateException("settlement workers did not finish in time");
}
System.out.println(settlements.sum());   // deterministically 4000
```

**Puzzle 5 — `availableProcessors()` under a cgroup**

```java
System.out.println(Runtime.getRuntime().availableProcessors());
```

Run on an 8-core host, inside a container with a cgroup CPU quota of `0.5` cores (e.g. Kubernetes `resources.limits.cpu: "500m"`).

**Output:**
```
1
```

Since JDK 10 (and backported to 8u191), the JVM is container-aware and reads the cgroup CPU quota rather than the host's physical core count, computing `availableProcessors()` as the ceiling of the quota — a 0.5-CPU limit rounds up to `1`, not `0`, and never reports the host's 8.

**Pitfall:** a pool sized with `Runtime.getRuntime().availableProcessors() × 2` inside such a container gets sized for a single core, not the fleet, which silently caps throughput far below what the code's author assumed when they reasoned about "an 8-core box" during local development. **Interview:** "if this pool looks under-provisioned in production but fine locally, what's the first thing you check?" — the container's actual CPU quota versus the host's core count, via `cat /sys/fs/cgroup/cpu.max` or the JVM's own `-XX:+PrintFlagsFinal` output for `ActiveProcessorCount`, before assuming the code itself regressed.

This is the same trap as Q1's pool-sizing formula wearing a different hat: the formula `8 × 0.9 × 51 = 367` is only correct if `cores` genuinely means 8. Compute the same formula with `cores = 1`, the value the container actually reports, and the "right" pool size collapses to roughly 46 — a fivefold difference driven entirely by which number `availableProcessors()` happened to return that morning, not by anything the developer changed in the pool-sizing code itself. Anyone who hardcodes the pool size from a local run and never re-derives it against the actual runtime environment inherits this gap silently.

---

**Leaves covered:** none of its own — Part 2 wrap-up over §2.1–§2.15
**Leaves deferred:** none
**Diagrams included:** none
**Target version:** Java 21 LTS
**Lines:** 401
