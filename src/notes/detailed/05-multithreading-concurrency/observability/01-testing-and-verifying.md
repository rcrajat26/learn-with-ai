# 05 Multithreading and Concurrency — Testing and verifying concurrent code — INTERMEDIATE (§2.12)

**Target version: Java 21 LTS.** | **Part 2 of 5** | [Index](../00-index.md)
Previous: [ThreadLocal and context propagation](../thread-local/02-context-propagation.md) · Next: [The concurrency-adjacent utility surface](../utility-surface/01-the-adjacent-apis.md)

A green JUnit run on `FundsLedger.reserveStake` proves exactly one thing: that *one* interleaving
of the threads that touched it, on *this* JVM and CPU, produced the right answer. It says nothing
about the interleavings the scheduler declined to pick today. The JMM permits reorderings x86-TSO
happens not to exhibit — a test that never fails on a laptop can fail on the first AArch64 build
box it meets. A single-threaded bug is a fixed point: run it a thousand times, it fails a thousand
times. A concurrency bug is a *distribution*: run it a thousand times, it might fail once, or
never, while still being live in production at 1,200 reservations/sec. Absence of a failing test
is not evidence of absence — it is evidence the scheduler has not yet handed you the bad
interleaving.

Verification for concurrent code is therefore an escalation ladder, each rung finding a class of
bug the rung below structurally cannot:

1. A **unit test** finds logic bugs on the happy interleaving.
2. A **stress test** raises the odds of hitting a bad interleaving, but a hit is a coin flip and
   says nothing about interleavings the CPU's memory model does not produce.
3. **jcstress** replaces "run it and hope" with a harness pinning actors to hardware threads,
   enumerating outcomes against the JMM's *permitted* set — the only rung that can *show* a
   reordering rather than fail to rule one out.
4. **Static analysis** finds bugs no running ever finds, since it never needed an unlucky
   interleaving — it reads the lock discipline off the source.

None subsumes the others: unit tests alone have not tested concurrency, jcstress alone has not
tested business logic. §2.12 covers all four rungs plus the runtime-detection tools that catch what
shipped anyway.

## 2.12.1 Why unit tests do not find concurrency bugs `[PROVE]`

**Mental model.** A concurrent method's behavior is a function of the interleaving of instructions
across threads, not just of its inputs. For `n` threads each executing `k` instructions, the number
of distinct interleavings is the multinomial coefficient `(nk)! / (k!)^n` — for `n=2, k=4` that is
`8!/(4!·4!) = 70` distinct schedules for a four-line method. A JUnit test that calls `reserveStake`
from the test thread exercises exactly **one** schedule: the one where nothing else runs
concurrently. It never lands inside the *concurrent* subset of that space at all.

**The proof, worked.** Take a simplified `FundsLedger.reserveStake` that (buggily) does:

```java
Money available = ledger.readAvailable(clientId);      // step A
if (available.compareTo(stakeAmount) < 0) {
    throw new InsufficientFundsException(clientId);
}
ledger.debit(clientId, stakeAmount);                    // step B
```

Single-threaded, `A` then `B` always happens atomically from the caller's point of view, so the
check-then-act race between them is invisible. Two client threads racing the same wallet down to
its last 4.20 in stakeable funds can both read `available = 4.20` at step A, both pass the check,
and both debit — the ledger goes negative, `LedgerImbalanceException` never fires, and the bug is
a business incident, not a stack trace. A unit test calling `reserveStake` sequentially, even a
hundred times, never constructs the state where two threads are both between A and B at once.
**A test suite with 100% branch coverage can still have 0% interleaving coverage** — coverage
tools do not measure the axis the bug lives on.

**What you *can* test deterministically** (2.12.2): the parts that do not depend on interleaving
order — a state machine's transition table (feed events, assert resulting state), the cancellation
protocol (`cancel()` then `get()` throws `CancellationException`), the shutdown path (no new tasks
after `shutdown()`), and lock discipline via `Thread.holdsLock(monitor)`, checking a method holds
the lock a reviewer claims without needing two threads. Cheap, but these test *sequential*
properties of concurrent code, not concurrency itself.

> **Definition:** a unit test validates one interleaving; a concurrency bug lives in interleavings
> the test never constructs, so passing tests and thread-unsafe code are the expected co-occurrence.

## 2.12.2 Deterministic scheduling by injection `[X-REF 16]`

The cheapest way to make concurrent code testable is to never let the test depend on a real
scheduler: inject an `Executor`, wiring a real pool in production and
`Executors.newSingleThreadExecutor()` (or an inline same-thread `Executor`) in tests. This turns
"does `PaymentService` submit exactly one retry after a PSP timeout" into a sequential assertion —
call the method, drain the executor, assert the mock PSP client saw one call. It tests *what got
submitted*, not *how the scheduler interleaved it*, exactly the gap 2.12.1 describes. See guide 16
for the submission algorithm this technique tests around.

## 2.12.3 The `CountDownLatch` start-gate / end-gate harness `[BUILD]`

**Mental model.** A stress test's job is to *maximize the probability* N threads execute the
contended region at the same instant, because an interleaving bug only shows up when threads
actually overlap. Left to `Thread.start()` in a loop the JVM staggers startup — thread 8 may start
after thread 1 has already finished. The fix is two latches: a **start gate** every worker blocks
on until all are ready, released in one instruction so all begin together; and an **end gate**
(counted down by each worker, awaited by the test thread) so the assertion runs only after every
worker has finished, not after an arbitrary sleep.

**Why it exists, and when to reach for it.** Before latches, teams used `Thread.sleep(N)` to "give
threads time" — too short is a false pass, too long is slow and flaky. The end-gate `await()`
cannot return until every `countDown()` has happened, replacing a guess with a guarantee. Reach for
it for any invariant that must hold under concurrent mutation. It is not a substitute for jcstress
(2.12.6) when the question is specifically about instruction reordering — this harness answers "does
the business invariant survive contention," a cheaper question worth asking first.

**How it works, and the code.** Eight threads race `FundsLedger.reserveStake` a million times each
against the same wallet, refilling between reservations so it never runs dry, asserting
`StakeSplit`'s invariant after every call: `bonusPortion + cashPortion == stakeAmount` exactly, in
`BigDecimal`, not `Money` equality post-rounding.

```java
final class FundsLedgerStakeSplitStressTest {

    @Test
    void reserveStakeAlwaysSumsExactlyToTheStakeUnderContention() throws InterruptedException {
        int threadCount = 8;
        int iterationsPerThread = 1_000_000;

        FundsLedger ledger = new FundsLedger(seedWalletWith(cash("500.00"), bonus("50.00")));
        ClientId clientId = ClientId.of(UUID.randomUUID());
        Money stake = Money.of(new BigDecimal("4.20"), Currency.getInstance("GBP"));
        CountDownLatch startGate = new CountDownLatch(1);
        CountDownLatch endGate = new CountDownLatch(threadCount);
        AtomicReference<Throwable> firstFailure = new AtomicReference<>();
        AtomicLong invariantChecks = new AtomicLong();
        ExecutorService pool = Executors.newFixedThreadPool(threadCount);
        for (int t = 0; t < threadCount; t++) {
            pool.submit(() -> {
                try {
                    startGate.await();
                    for (int i = 0; i < iterationsPerThread; i++) {
                        StakeSplit split = ledger.reserveStake(clientId, stake);
                        Money sum = split.bonusPortion().add(split.cashPortion());
                        if (sum.amount().compareTo(stake.amount()) != 0) {
                            throw new LedgerImbalanceException(
                                "split %s + %s != stake %s".formatted(
                                    split.bonusPortion(), split.cashPortion(), stake));
                        }
                        invariantChecks.incrementAndGet();
                        ledger.settleStakeAsWin(clientId, stake);   // refill so the wallet never runs dry
                    }
                } catch (Throwable t2) {
                    firstFailure.compareAndSet(null, t2);
                } finally {
                    endGate.countDown();
                }
            });
        }

        startGate.countDown();                 // release all 8 at once
        endGate.await();                        // do not assert until every worker finished
        pool.shutdown();
        assertThat(firstFailure.get()).isNull();
        assertThat(invariantChecks.get()).isEqualTo((long) threadCount * iterationsPerThread);
    }
}
```

**The gotcha.** `startGate.countDown()` happening "at once" is best effort, not a guarantee — the OS
still schedules eight `await()` returns independently, and thread 1 can be milliseconds ahead of
thread 8 on a loaded CI box. The gate raises overlap probability; it does not make it certain — a
stress test that never fails is weak evidence, not proof (see 2.12.5 for the weak-memory-model
half most teams skip).

> **Definition:** the latch harness turns "start N threads and hope they overlap" into "release N
> already-waiting threads at once, and do not check the result until all N finish" — the cheapest
> lever for raising interleaving pressure without touching the JMM.

## 2.12.4 `Awaitility` for eventual conditions `[X-REF 16]` `[RESEARCH]`

Where a stress test needs to assert something that becomes true *eventually* — a reconciliation
job has processed a settlement — `Thread.sleep(500)` is flaky (may not be enough under load) and
slow (always 500 ms, even if true after 5 ms). `Awaitility.await().atMost(5,
SECONDS).untilAsserted(() -> assertThat(ledger.positionOf(SUSPENSE)).isEqualTo(ZERO))` polls on a
short interval and returns the instant it passes, failing loudly with the last assertion error on
timeout. **Unverified:** the current Awaitility major version and default poll interval were not
re-checked in this session — verify the coordinate before pinning a version.

## 2.12.5 Static stress testing without a weak-memory machine `[TRAP]`

**Pitfall:** running the 2.12.3 harness once, on a laptop, on x86, and declaring the method thread
safe. x86-TSO forbids store-store and load-load reordering outright and only allows store-load
reordering — exactly the pattern the Dekker/store-buffering litmus test (2.12.6) needs to manifest.
**A race invisible on x86 because TSO happens to preserve the order code silently depends on can
fire routinely on AArch64**, where only `volatile`/`Atomic*`/lock-guarded accesses are guaranteed
ordered. The fix: run the *same* stress test on an AArch64 box (Graviton, or an Apple Silicon
`linux/arm64` image) as a required CI leg, not an optional nightly. If the invariant only ever
failed there, that is not "flaky CI" — it is the bug jcstress exists to demonstrate in isolation.

## 2.12.6 The jcstress harness: showing a reordering, not just failing to rule it out `[RESEARCH]` `[BUILD]`

**Mental model.** jcstress is not a stress-test library like 2.12.3 — it is a *statistics engine
over interleavings*. It pins named actor methods to hardware threads, runs the combination billions
of times across forked JVMs, tallies which combinations of the actors' return values occurred, and
reports the tally against a table of which combinations the JMM *permits*. Where a stress test
gives pass/fail, jcstress gives a histogram: "outcome `(1,0)` occurred 4.2 billion times; `(0,0)`
occurred 12 times" — the 12 is the reordering caught in the act, not inferred from a failure three
layers up the stack.

**Why it exists, and when to reach for it.** Before jcstress (OpenJDK's own project, same lineage
as JMH), demonstrating a JMM-permitted reordering meant trusting the JLS chapter 17 formalism or
getting unlucky with a bespoke racer — unreliable, not CI-admissible. Reach for it when the
question is specifically about ordering guarantees; not for a business invariant (2.12.3 is
cheaper) and not as a substitute for the happens-before rules — it shows *that* a reordering
happens, not *why* the spec permits it.

**How it works.** A jcstress test is a `@JCStressTest` class with `@State` fields shared across
actors, one method per thread annotated `@Actor`, an optional `@Arbiter` computing a value from
final state, and `@Outcome` annotations classifying every result tuple as `ACCEPTABLE` (permitted,
boring), `ACCEPTABLE_INTERESTING` (permitted, exactly the reordering being demonstrated), or
`FORBIDDEN` (a JMM violation in the JVM itself — jcstress fails the run if observed).

**The worked litmus test.** Frame store buffering (Dekker) in QuizStakes: two plain (non-volatile)
`int` fields simulate a racy "has the reservation posted / has the settlement posted" check a naive
reconciliation job might use instead of a proper happens-before edge.

```java
@JCStressTest
@Outcome(id = "1, 1", expect = Expect.ACCEPTABLE,
         desc = "Both actors saw the other's write — the common, uninteresting case.")
@Outcome(id = "1, 0", expect = Expect.ACCEPTABLE,
         desc = "Actor 2 ran after actor 1's write was visible, but actor 1 ran before actor 2's.")
@Outcome(id = "0, 1", expect = Expect.ACCEPTABLE,
         desc = "The symmetric case.")
@Outcome(id = "0, 0", expect = Expect.ACCEPTABLE_INTERESTING,
         desc = "The store-buffering reorder: each actor's own store is buffered past its own load, "
              + "so each reads the OTHER's pre-write value. Legal under the JMM for plain fields; "
              + "this is the outcome that would be FORBIDDEN if the fields were volatile.")
@State
public class ReservationSettlementStoreBufferingTest {
    int reservationPosted;   // plain field, deliberately not volatile
    int settlementPosted;    // plain field, deliberately not volatile

    @Actor
    public void reservationWorker(I_Result r) {
        reservationPosted = 1;
        r.r1 = settlementPosted;
    }

    @Actor
    public void settlementWorker(I_Result r) {
        settlementPosted = 1;
        r.r2 = reservationPosted;
    }
}
```

`I_Result` is jcstress's built-in two-int result holder; jcstress tallies `(r1, r2)` pairs across
billions of forked-JVM executions and classifies each against the `@Outcome` table above. The
`(0, 0)` row is the entire point of the test: rare on strongly-ordered x86 (TSO discourages but
does not forbid every store-buffering window), far more frequent on AArch64's weaker ordering.
**Unverified:** the exact relative frequency of `(0,0)` on current Graviton vs. Apple Silicon was
not measured in this session — treat any specific count as illustrative, not a captured benchmark.

**The fix**: mark both fields `volatile`. The JMM rule that a volatile write happens-before every
subsequent volatile read of the same field forces `(0,0)` out of the permitted set entirely; the
volatile version of the same test reclassifies that row `FORBIDDEN`, and jcstress failing to
observe it after billions of runs becomes actual evidence, not the absence of luck.


**D-138** — A jcstress litmus test, read.

| Outcome `(r1, r2)` | Sequentially consistent? | Permitted by JMM (plain fields) | Observed on x86 | Observed on AArch64 | jcstress classification | The fix |
|---|---|---|---|---|---|---|
| `(1, 1)` | Yes | Yes | Yes, overwhelmingly common | Yes, overwhelmingly common | `ACCEPTABLE` | none needed for this row |
| `(1, 0)` | Yes | Yes | Yes | Yes | `ACCEPTABLE` | none needed for this row |
| `(0, 1)` | Yes | Yes | Yes | Yes | `ACCEPTABLE` | none needed for this row |
| `(0, 0)` | **No** | Yes, via store-buffering | Rare | Markedly more frequent | `ACCEPTABLE_INTERESTING` | mark both fields `volatile`; reclassifies `(0,0)` `FORBIDDEN` |

**The gotcha.** `@Outcome` strings must match the result object's field order exactly (`"r1, r2"`,
not `"r2, r1"`); a transposed pair silently swaps the interesting and boring classifications, and
the test "passes" having verified nothing.

**Interview:** *"How would you prove a memory-model reordering is real, not theoretical?"* — run
the litmus test with the fields non-volatile; a nonzero `(0,0)` count is direct evidence, which no
`Thread.sleep`-based test can show since it only reports an *outcome* diverged, never a reorder.

> **Definition:** jcstress turns "the JMM permits this reordering" from a specification claim into
> an observed frequency, by pinning actors to threads and tallying result tuples against a table of
> legal outcomes.

## 2.12.7 JMH `@Group` for asymmetric read/write concurrency benchmarks `[X-REF 06]` `[RESEARCH]`

**Mental model.** A plain `@Benchmark` under `@Threads(8)` measures eight threads doing the *same*
operation — useless for "how does `BalanceView`'s read throughput change while
`FundsLedger.reserveStake` writes underneath it," since real traffic is asymmetric (2.8M stake
reservations/day against a far higher rate of balance reads). `@Group` lets a class declare
multiple `@Benchmark` methods tagged into a named group, `@GroupThreads(n)` fixing how many threads
run each — e.g. 1 writer calling `reserveStake` against 7 readers calling `readStakeable`, in one
measured iteration on shared `@State(Scope.Group)` state.

**Why it exists, and when to reach for it.** Hand-rolling threads inside a benchmark method body
bypasses JMH's warmup, forking, and `Blackhole` machinery, so the result is not trustworthy.
Reach for `@Group` whenever the production access pattern is asymmetric — most caches and ledgers
are read-heavy with occasional writes; not for an uncontended hot loop, a plain `@Benchmark` with
`@Threads(1)`.

**How it works, and the code.**

```java
@State(Scope.Group)
@BenchmarkMode(Mode.Throughput)
@OutputTimeUnit(TimeUnit.MICROSECONDS)
public class FundsLedgerContentionBenchmark {
    private FundsLedger ledger;
    private ClientId clientId;
    private Money stake;

    @Setup(Level.Trial)
    public void setUp() {
        ledger = new FundsLedger(seedWalletWith(cash("10000.00"), bonus("500.00")));
        clientId = ClientId.of(UUID.randomUUID());
        stake = Money.of(new BigDecimal("4.20"), Currency.getInstance("GBP"));
    }

    @Benchmark
    @Group("ledgerTraffic")
    @GroupThreads(1)
    public StakeSplit reserve() {
        return ledger.reserveStake(clientId, stake);
    }

    @Benchmark
    @Group("ledgerTraffic")
    @GroupThreads(7)
    public Money readBalance(Blackhole bh) {
        Money stakeable = ledger.readStakeable(clientId);
        bh.consume(stakeable);
        return stakeable;
    }
}
```

`Blackhole.consume` on the read path stops the JIT from proving `readBalance`'s return value is
unused and eliding the read entirely — a naive loop benchmark with no side effect frequently
measures dead-code elimination, not the operation's cost (2.12.9). The `1`-vs-`7` split
approximates the domain's write-to-read skew without claiming to reproduce the literal 1,200/sec
figure; only the *relative* effect of adding contention is portable across machines.

**The gotcha.** `@State(Scope.Group)` — not `Scope.Thread` — is what makes threads in one group
share `ledger` and `clientId`; `Scope.Thread` gives every thread its own uncontended `FundsLedger`,
silently measuring zero contention while still reporting a plausible-looking number.

**Benchmark traps specific to concurrency (2.12.10):** measuring an uncontended single-thread
benchmark and reporting it as "the lock's cost under load" (contention cost is superlinear near
saturation, not constant per call); benchmarking on an otherwise-idle machine, hiding cache-line
and core-count effects; and forgetting the JIT can prove a lock thread-confined and elide
`synchronized` via lock elision, so a "benchmark" of a thread-local lock reports near-zero cost
unrelated to the lock's real cost once the object escapes.

> **Definition:** `@Group` with `@GroupThreads` lets one JMH benchmark model a mixed reader/writer
> workload against shared state in a single measured run — the only way to get a trustworthy number
> for "how much does this write slow down these reads."

## 2.12.8 Static analysis: catching the bug without ever running it `[RESEARCH]`

**Mental model.** Every tool above needs a bad interleaving to actually occur before it can report
anything. Static analysis reads the *lock discipline* off the source — which fields a `@GuardedBy`
annotation claims are protected, whether every access site holds it — and reports a violation the
first time the checker runs, with zero probability involved.

**Why it exists, and its limits.** A field almost always accessed under the right lock, with one
call site that forgot, can pass every stress test for months if that site is rare in traffic;
static checkers do not care how rarely a site executes. Reach for it as a compile-time gate on any
class with declared lock ownership; it cannot verify the *chosen* lock is the *correct* one, only
that it is consistently held.

**How it works.** ErrorProne's `@GuardedBy` checker flags any read/write site that does not hold
the annotation's named lock — a `FundsLedger` field `@GuardedBy("reservationLock") private
BigDecimal reservedTotal` touched by a metrics method that forgot to synchronize is a build-time
error, not a 3 a.m. page. SpotBugs' detectors catch pattern-level mistakes without annotations:
`IS2_INCONSISTENT_SYNC` (inconsistent synchronization — the 2.12.1 check-then-act shape),
`DC_DOUBLECHECK` (double-checked locking on a non-`volatile` field), `LI_LAZY_INIT_STATIC` (an
unsynchronized lazily-initialized static), `NN_NAKED_NOTIFY` (`notify` with no visible state change
before it), and `SWL_SLEEP_WITH_LOCK_HELD` (`sleep` inside a `synchronized` block).

**The gotcha.** `@GuardedBy` is advisory metadata — it only catches what the ErrorProne plugin is
actually wired into the build and not suppressed. A `@SuppressWarnings("GuardedBy")` added under
deadline pressure silently reopens exactly the bug class the annotation existed to prevent.

> **Definition:** static analysis trades the interleaving-tools' need for an unlucky schedule for a
> lock-discipline model of the source, catching the rare call site every build instead of the one
> time in a million it races.

## 2.12.9 Runtime detection in production `[BUILD]`

Tests and static analysis catch what they catch before ship; a watchdog catches what got through.
`ThreadMXBean.findDeadlockedThreads()` returns the thread IDs participating in a cycle of lock
ownership — run it on a schedule, not on demand, because a deadlock does not announce itself with
an exception, it announces itself with silence:

```java
final class DeadlockWatchdog {
    private final ThreadMXBean threadMXBean = ManagementFactory.getThreadMXBean();
    private final ScheduledExecutorService scheduler =
        Executors.newSingleThreadScheduledExecutor(Thread.ofPlatform().name("deadlock-watchdog").factory());

    void start() {
        scheduler.scheduleAtFixedRate(this::checkOnce, 30, 30, TimeUnit.SECONDS);
    }

    private void checkOnce() {
        long[] deadlockedIds = threadMXBean.findDeadlockedThreads();
        if (deadlockedIds == null) {
            return;
        }
        ThreadInfo[] infos = threadMXBean.getThreadInfo(deadlockedIds, true, true);
        for (ThreadInfo info : infos) {
            log.error("deadlock detected: thread {} blocked on {} owned by {}",
                info.getThreadName(), info.getLockName(), info.getLockOwnerName());
        }
    }
}
```

Pair this with a **lock-timeout policy that logs instead of hanging** (`tryLock(timeout, unit)`
over `lock()` on cross-service `Lock`s). JFR's monitor events (`jdk.JavaMonitorEnter`,
`jdk.JavaMonitorWait`, `jdk.ThreadPark`) record contention with stack traces continuously at low
overhead — but show *contention*, not *deadlock*, so a mature setup runs both.

**Chaos-style verification (2.12.11):** run the same stress test under `-XX:+UseSerialGC` (changes
pause shape), under `taskset`/a CPU quota with fewer cores than threads (forces preemption), and on
a different architecture — each changes the interleaving *distribution* without changing the code,
so a bug reproducing under only one is real, just statistically rare by default.

**Reproducing a heisenbug (2.12.12):** a race that vanishes under a debugger or a log line is not
evidence it went away — both introduce an accidental memory barrier. **Pitfall:** "the log line
made it stop happening, so it's fixed" — the logger's internal synchronization absorbs the race,
not resolves it; removing it in production brings the bug back. The real levers: raise thread
count well beyond production concurrency, insert `Thread.onSpinWait()` to widen the window without
a context switch, run on the weakest-ordered hardware available (2.12.5), and remove — never add —
the suspected accidental barrier.


**D-139** — What each verification tool can and cannot find.

| Tool | Lost update | Deadlock | Data race | Contention | Leak | Runs in CI |
|---|---|---|---|---|---|---|
| Unit test | If it constructs the interleaving (rare, usually no) | No | No | No | No | Yes |
| Stress test (2.12.3) | Yes, probabilistically | Rarely — needs the timing luck | Indirectly, via corrupted output | Coarsely, via throughput drop | No | Yes |
| jcstress (2.12.6) | No — wrong granularity | No | Yes — its entire purpose | No | No | Rarely (slow, dedicated job) |
| JMH (2.12.7) | No | No | No | Yes — its entire purpose | No | Rarely (slow, dedicated job) |
| ErrorProne `@GuardedBy` (2.12.8) | Yes, if annotated | No | Partially (unguarded field access) | No | No | Yes |
| SpotBugs detectors (2.12.8) | Partially (`IS2_INCONSISTENT_SYNC`) | No | Partially | No | No (except static resource-leak patterns) | Yes |
| `ThreadMXBean` watchdog (2.12.9) | No | Yes — its entire purpose | No | No | No | No (production runtime) |
| JFR (2.12.9) | No | No (shows blocking, not the cycle) | No | Yes, with stack traces | Partially (allocation profiling) | No (production runtime) |
| async-profiler | No | No | No | Yes, wall-clock and lock profiling | Yes (native memory modes) | No (production/staging) |
| Thread dump (`jstack`/`jcmd`) | No | Yes, read manually | No | Snapshot only, not a rate | No | No (on-demand diagnostic) |

## Pitfalls

### Assuming a stress test that passed 1,000 times proves thread safety

**Wrong**

```java
for (int i = 0; i < 1000; i++) {
    runStressTestOnce();   // "1000 green runs, ship it"
}
```

The loop reruns the *same* JVM and CPU every time — it samples one narrow region of the
interleaving space a thousand times, not a thousand different regions.

**Right**

```java
// CI matrix: one job on x86_64, one job on aarch64, plus a dedicated jcstress job
// for any field whose synchronization was recently touched.
```

Vary the *hardware memory model*, not just the iteration count — the AArch64 leg and the jcstress
run find the class of bug more x86 iterations cannot.

**Why people believe it:** intuition transfers from single-threaded flaky-test hunting, where more
runs genuinely do increase confidence, because that trigger condition does not depend on the CPU's
memory model — only a concurrency bug's does.

### Believing `notify()` wakes the "right" waiter

**Wrong**

```java
synchronized (lock) {
    condition = true;
    lock.notify();   // assumes exactly one specific waiter will wake and proceed
}
```

`notify()` wakes an unspecified single waiter chosen by the JVM; SpotBugs flags this shape as
`NN_NAKED_NOTIFY` because nothing re-checks the woken thread's condition actually became true.

**Right**

```java
synchronized (lock) {
    condition = true;
    lock.notifyAll();   // every waiter re-checks its own condition in a while loop before proceeding
}
```

Each waiter loops `while (!myCondition) { lock.wait(); }` rather than a one-shot `if`, so a
spuriously-woken or wrong-condition thread just goes back to waiting.

**Why people believe it:** `notify()` reads as "notify the (singular, implied) thread," and a toy
two-thread example genuinely has only one waiter, so the bug is invisible until a third is added.

## Cheat sheet

| Tool | Question it answers | Cost to run | Belongs in |
|---|---|---|---|
| Unit test | Does the sequential logic work? | Milliseconds | Every PR |
| Latch-harness stress test | Does the invariant survive N threads × M iterations? | Seconds | Every PR (fast) + nightly (long) |
| Awaitility | Did this eventually become true? | Milliseconds–seconds | Every PR |
| jcstress | Can this specific reordering be observed? | Minutes–hours (forked JVMs) | Dedicated job, on lock-discipline changes |
| JMH `@Group` | How much does write traffic slow down reads? | Minutes | Dedicated perf job, on hot-path changes |
| ErrorProne `@GuardedBy` | Is the declared lock discipline consistent? | Build-time, near-zero | Every build (compiler plugin) |
| SpotBugs concurrency detectors | Does the code match known-bad patterns? | Seconds–minutes | Every PR (static gate) |
| `ThreadMXBean` watchdog | Is there a deadlock right now? | Continuous, low overhead | Production, scheduled |
| JFR monitor events | Where is production actually contending? | Continuous, low overhead | Production, always-on |
| AArch64 CI leg | Does the invariant survive a weaker memory model? | Same as the x86 job | Required CI leg, not optional nightly |

## Self-test

**Q1.** A `FundsLedger.reserveStake` unit test with 100% branch coverage passes reliably. What has
it actually proven, and what has it not?

<details><summary>Answer</summary>

It proved the sequential logic is correct on the one schedule with no concurrent thread. It did not
prove thread safety: coverage measures which lines executed, not cross-thread interleavings, so a
check-then-act race between two individually-covered lines is invisible to it.

</details>

**Q2.** Why does the `CountDownLatch` start-gate/end-gate harness use two separate latches instead
of one?

<details><summary>Answer</summary>

The start gate releases every worker at the same instant instead of staggering `Thread.start()`
calls. The end gate ensures the assertion runs only after every worker has finished. One latch
cannot do both roles because `CountDownLatch` only counts down and cannot be reset.

</details>

**Q3.** What specific outcome does the store-buffering (Dekker) jcstress test look for, and why is
it legal under the JMM for plain fields?

<details><summary>Answer</summary>

The `(0, 0)` outcome: each actor reads the *other* actor's field as its initial value, though both
already wrote their own field first. Legal because, absent a happens-before edge between them, each
actor's own store can be reordered past its own load by the store buffer or the compiler.

</details>

**Q4.** Why does `@State(Scope.Group)` matter for a JMH `@Group` benchmark, and what happens with
`@State(Scope.Thread)` by mistake?

<details><summary>Answer</summary>

`Scope.Group` makes every thread in the group share the same object, required to measure
contention. `Scope.Thread` gives each its own private copy, so the "readers" never touch the
writer's object — the benchmark still reports a number, but it describes eight uncontended
operations, not the contention being measured.

</details>

**Q5.** A SpotBugs run flags `DC_DOUBLECHECK` on a lazy-initialization method. What is the
underlying bug, and the minimal fix?

<details><summary>Answer</summary>

A double-checked-locking idiom on a plain, non-`volatile` field: another thread can observe a
non-null reference to a partially-constructed object because the publishing write and the
constructor's writes are unordered from its point of view. The fix is declaring the field
`volatile`, establishing the happens-before edge that makes safe publication hold.

</details>

**Q6.** What does JFR's `jdk.JavaMonitorEnter` event tell you that `ThreadMXBean
.findDeadlockedThreads()` cannot, and vice versa?

<details><summary>Answer</summary>

Monitor events record ongoing lock contention with stack traces, continuously, even with no
deadlock present. `findDeadlockedThreads()` detects a cycle of lock ownership precisely, but only
as a point-in-time snapshot when polled. Contention without a cycle is invisible to the watchdog;
a cycle that resolves before the next poll is invisible to JFR's contention view alone.

</details>

## Open questions

- **Unverified:** the current major version and default poll interval of `Awaitility` (2.12.4) —
  verify against the project's build coordinates before pinning a version.
- **Unverified:** the relative frequency of the store-buffering `(0,0)` outcome (2.12.6) on current
  Graviton vs. Apple Silicon — any count in this file is illustrative, not a captured benchmark.

---

**Leaves covered:** 2.12.1–2.12.14 (14 leaves)
**Leaves deferred:** none
**Diagrams included:** D-138, D-139
**Target version:** Java 21 LTS
**Lines:** 598
