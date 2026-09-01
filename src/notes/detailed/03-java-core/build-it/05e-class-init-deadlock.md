# 03 Java Core — Diagnostic harnesses — the class-initialization deadlock — BUILD IT (§4.8, 4.8.4)

**Target version: Java 21 LTS.** | **Part 4 of 5** | [Index](../00-index.md)
Previous: [Class-initialization order](05g-class-initialization-order.md) · Next: [The constant-inlining harness](05b-inlining-and-retention-harnesses.md)

Two threads, two classes, no `synchronized` anywhere in the program, and the JVM stops. Not a crash,
not an exception, not a log line — two live threads sitting in `<clinit>` frames forever.
`BonusService`'s static initializer reads a field of `FundsLedger` and `FundsLedger`'s reads a field
of `BonusService`; one thread touches each; each now holds the initialization lock of the class it
entered and waits for the lock the other holds.

Nothing in that is a bug. Class initialization is *specified* to be thread-safe and to run exactly
once, and the JVM delivers that with a per-class initialization lock: the first thread to touch a
class takes that class's lock, runs its `<clinit>`, and every other thread that touches the same
class blocks until it finishes. The guarantee is the feature; the deadlock is the feature working
exactly as written, applied to a cycle. There is no JVM bug to file and no patch to wait for — which
is why this one is nasty, and why a `synchronized` block or a lock-ordering convention cannot fix it.
You do not own the locks. The JVM does, they are not Java monitors, and you cannot see them, acquire
them, or order them.

## Where the single-threaded case sits (recap, then cross-reference)

[Construction and initialization-order harnesses](05a-construction-and-init-harnesses.md) owns
initialization *order* (4.8.3) and the constructor-calls-an-overridable-method trap (4.8.2). Recap:
within one class the JVM initializes `ConstantValue` static finals first, then runs static field
initializers and `static {}` blocks in source order as one synthetic `<clinit>`; instance
initializers and constructor bodies run later, per-instance, superclass first. Reading a static field
of a *different* class from inside `<clinit>` triggers that class's initialization at the point of
the read — the mechanism this file abuses.
`../classes-and-initialization/03-internals-class-loading-and-init.md` owns load-link-initialize and
`../classes-and-initialization/03a-internals-class-init-locking-and-failure.md` owns the locking and
failure states. Guide 05 owns deadlock as a concurrency topic; guide 06 owns class loading at the
runtime level.

## The mechanism, from the specification

The deadlock is the spec being followed, so the spec text carries the argument. JVMS 21, §5.5
*Initialization*, gives the procedure as a numbered list of twelve steps. Verbatim, the setup:

> For each class or interface `C`, there is a unique initialization lock `LC`. The mapping from
> `C` to `LC` is left to the discretion of the Java Virtual Machine implementation. For example,
> `LC` could be the `Class` object for `C`, or the monitor associated with that `Class` object.

`LC` is per class, not global, and no ordering is imposed on the set of all `LC` — the spec never
contemplates a thread holding two of them, but a `<clinit>` that reads another class does exactly
that. Then the steps that matter:

> 1. Synchronize on the initialization lock, `LC`, for `C`. This involves waiting until the
>    current thread can acquire `LC`.
>
> 2. If the `Class` object for `C` indicates that initialization is in progress for `C` by some
>    other thread, then release `LC` and block the current thread until informed that the
>    in-progress initialization has completed, at which time repeat this procedure.
>
>    Thread interrupt status is unaffected by execution of the initialization procedure.

Step 1 is the acquisition: first thread here wins. Step 2 is the whole deadlock — "block the current
thread until informed" is unconditional, with no timeout and no cycle check, and the parenthetical
says the wait is not interruptible. You cannot `Thread.interrupt()` your way out, so the usual
"interrupt the stuck worker and let the pool recycle it" recovery does nothing.

> 3. If the `Class` object for `C` indicates that initialization is in progress for `C` by the
>    current thread, then this must be a recursive request for initialization. Release `LC` and
>    complete normally.

Step 3 is why the single-threaded case does not hang: same thread, re-entrant, the procedure returns
and the caller proceeds as if the class were done. It is not done — its `<clinit>` is half-way
through — so the caller reads whatever the fields hold right now, which for fields not yet assigned
is the default `0` or `null`. **The single-threaded run does not fail; it silently lies.**

> 5. If the `Class` object for `C` is in an erroneous state, then initialization is not possible.
>    Release `LC` and throw a `NoClassDefFoundError`.
>
> 6. Otherwise, record the fact that initialization of the `Class` object for `C` is in progress
>    by the current thread, and release `LC`.
>
> 9. Next, execute the class or interface initialization method of `C`.
>
> 10. If the execution of the class or interface initialization method completes normally, then
>     acquire `LC`, label the `Class` object for `C` as fully initialized, notify all waiting
>     threads, release `LC`, and complete this procedure normally.

Step 6 records ownership in the `Class` object's state and then *releases* `LC`: mutual exclusion for
the duration of `<clinit>` comes from the recorded in-progress state plus step 2's wait, not from
continuously holding the monitor. Step 5 is the aftermath of a `<clinit>` that threw — the class is
permanently `erroneous`, and every later touch from any thread gets `NoClassDefFoundError` rather
than a retry. Step 9 is your `static {}` block; step 10 holds the "notify all waiting threads" that
step 2's blocked thread waits for, and a thread stuck inside step 9 never reaches step 10.

And §5.4.3.6 says out loud that this shape is legal, contrasting it with resolution, which *does*
detect its cycles and throw:

> Unlike class initialization (§5.5), where cycles are allowed between uninitialized classes,
> resolution does not allow cycles in symbolic references to dynamically-computed constants.

Initialization does not detect cycles at all, by design: in one thread a cycle is harmless (step 3),
and the spec chose re-entrance over rejection.

> A class-initialization deadlock is the per-class initialization lock of JVMS §5.5 step 1 acquired
> in two different orders by two threads, made unbreakable by step 2's uninterruptible,
> timeout-free wait.

## The cyclic pair, complete

Two service holders a real QuizStakes startup path would plausibly contain. `BonusService` sizes
per-position counters, so it wants the ledger's position count. `FundsLedger` pre-validates
`PROMOTIONAL_EXPENSE` postings, so it wants the bonus cap. Each reads the other from `<clinit>`.

```java
package quizstakes.cycle;

import java.util.Map;

/** Grants 10% of the first deposit capped at 100. Sizes per-position counters, so it reads FundsLedger. */
public final class BonusService {

    /** 100 major units expressed in minor units. Not a compile-time constant. */
    public static final int BONUS_CAP_MINOR_UNITS;

    public static final Map<String, Integer> BONUS_RULES;

    /** What this class saw of FundsLedger while initializing. */
    public static int ledgerPositionCountSeen;

    static {
        StartupAlignment.arriveInsideStaticInitializer();

        // Cross-reference FIRST, before this class's own fields are assigned.
        ledgerPositionCountSeen = FundsLedger.POSITION_COUNT;
        BONUS_CAP_MINOR_UNITS = 10_000;
        BONUS_RULES = Map.of(
                "BONUS_PERCENT_OF_DEPOSIT", 10,
                "BONUS_CAP_MINOR_UNITS", BONUS_CAP_MINOR_UNITS,
                "COUPON_VALIDITY_DAYS", 14,
                "BONUS_EXPIRY_DAYS", 30);
    }

    private BonusService() {}

    /** Grant for a first deposit, in minor units: 10% capped at BONUS_CAP_MINOR_UNITS. */
    public static int grantFor(int depositMinorUnits) {
        return Math.min(depositMinorUnits / 10, BONUS_CAP_MINOR_UNITS);
    }
}
```

```java
package quizstakes.cycle;

import java.util.List;

/** The double-entry record. Wants the bonus cap to pre-validate PROMOTIONAL_EXPENSE postings, so it reads BonusService. That closes the cycle. */
public final class FundsLedger {

    public static final List<String> POSITIONS = List.of(
            "CLIENT_CASH_AVAILABLE",
            "CLIENT_CASH_RESERVED",
            "CLIENT_BONUS_AVAILABLE",
            "CLIENT_BONUS_RESERVED",
            "SUSPENSE",
            "PSP_RECEIVABLE",
            "BANK_SETTLEMENT",
            "HOUSE_REVENUE",
            "PROMOTIONAL_EXPENSE",
            "FEES",
            "CHARGEBACK_LOSS");

    public static final int POSITION_COUNT;

    /** What this class saw of BonusService while initializing. */
    public static int bonusCapSeen;

    static {
        StartupAlignment.arriveInsideStaticInitializer();

        POSITION_COUNT = POSITIONS.size();

        // Cross-reference back into BonusService. This closes the cycle.
        bonusCapSeen = BonusService.BONUS_CAP_MINOR_UNITS;
    }
    private FundsLedger() {}

    public static int indexOfPosition(String position) {
        return POSITIONS.indexOf(position);
    }
}
```

The window in these `<clinit>` bodies is a few hundred nanoseconds, which is not a reproduction.
`StartupAlignment` stands in for the work a real static initializer does — reading a properties file,
querying a code table — and guarantees both threads are *inside* their own `<clinit>`, each holding
one initialization lock, before either crosses over. It is a no-op unless a harness arms it, so the
same two classes serve both runs.

```java
package quizstakes.cycle;

import java.util.concurrent.BrokenBarrierException;
import java.util.concurrent.CyclicBarrier;

/** Widens the class-initialization race window deterministically: both threads are inside their own static initializer, each holding one initialization lock, before either crosses over. */
public final class StartupAlignment {

    private static volatile CyclicBarrier barrier;
    private StartupAlignment() {}

    /** Install a barrier. Call from the main thread before starting workers. */
    public static void expectParticipants(int participants) {
        barrier = new CyclicBarrier(participants);
    }

    /** No-op when no barrier is installed, so single-threaded runs are unaffected. */
    public static void arriveInsideStaticInitializer() {
        CyclicBarrier local = barrier;
        if (local == null) {
            return;
        }
        try {
            local.await();
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
        } catch (BrokenBarrierException e) {
            throw new IllegalStateException("startup alignment barrier broken", e);
        }
    }
}
```

**Insight:** `BONUS_CAP_MINOR_UNITS` is `static final int` but assigned *inside* the static block,
not at its declaration. That is load-bearing. `javap -c -p quizstakes.cycle.FundsLedger`, tail of
`<clinit>`:

```text
      82: putstatic     #56                 // Field POSITION_COUNT:I
      85: getstatic     #60                 // Field quizstakes/cycle/BonusService.BONUS_CAP_MINOR_UNITS:I
      88: putstatic     #65                 // Field bonusCapSeen:I
      91: return
```

Instruction `85` is a real `getstatic` against another class, and `getstatic` is one of the four
instructions §5.5 lists as an initialization trigger. Declare the field as
`public static final int BONUS_CAP_MINOR_UNITS = 10_000;` instead and it becomes a compile-time
constant: `javac` folds it, the same line compiles to `sipush 10000` with no class reference at all,
and the two-thread harness then prints `NO DEADLOCK: both workers finished` (measured). That is a
landmine, not a fix — the day someone replaces `10_000` with `readCapFromConfig()` the fold
disappears, the `getstatic` returns, and the deadlock arrives in a one-line commit.
[Constant inlining and inner-class retention](05b-inlining-and-retention-harnesses.md) owns the
inlining mechanics.

## Run 1 — one thread, both directions

`SingleThreadedRun` is `main` scaffolding: it touches one class of the pair, then prints the four
fields with their expected values. No barrier is installed, so the aligner returns immediately.

Real output, Oracle JDK 21.0.7 (build 21.0.7+8-LTS-245), macOS aarch64:

```console
$ java -cp out quizstakes.cycle.SingleThreadedRun bonus
thread: main | touching first: bonus
BonusService.grantFor(65_00) = 650
BonusService.BONUS_CAP_MINOR_UNITS   = 10000
FundsLedger.POSITION_COUNT           = 11
BonusService.ledgerPositionCountSeen = 11   (expected 11)
FundsLedger.bonusCapSeen             = 0   (expected 10000)
run completed, no deadlock

$ java -cp out quizstakes.cycle.SingleThreadedRun ledger
thread: main | touching first: ledger
FundsLedger.indexOfPosition("CLIENT_BONUS_RESERVED") = 3
BonusService.BONUS_CAP_MINOR_UNITS   = 10000
FundsLedger.POSITION_COUNT           = 11
BonusService.ledgerPositionCountSeen = 11   (expected 11)
FundsLedger.bonusCapSeen             = 10000   (expected 10000)
run completed, no deadlock
```

Read both runs against §5.5 step 3. Touching `BonusService` first: its `<clinit>` reaches the
cross-reference before assigning `BONUS_CAP_MINOR_UNITS`, triggers `FundsLedger`, whose `<clinit>`
reads `BonusService.BONUS_CAP_MINOR_UNITS` — in-progress *by the current thread*, so step 3 lets it
through and it reads the default. `bonusCapSeen = 0`: every `PROMOTIONAL_EXPENSE` pre-validation now
compares against a cap of nothing. Touching `FundsLedger` first, the same cycle produces `10000`,
because `POSITION_COUNT` is assigned *before* that class crosses over. Same code, same JVM, opposite
correctness, decided by which class the process happened to touch first.

**Pitfall:** the single-threaded run is where your unit tests live, and it never throws — it prints a
wrong number that looks plausible. The bug ships not because it is subtle but because the suite's one
thread walks the cycle re-entrantly and reports green.

## Run 2 — two threads, and the deadlock

The harness never hangs: it joins with a timeout, then interrogates the JVM about its own state.
Workers are daemons so the reporting path can exit.

```java
package quizstakes.cycle;

import java.lang.management.ManagementFactory;
import java.lang.management.ThreadInfo;
import java.lang.management.ThreadMXBean;
import java.util.Arrays;
import java.util.concurrent.TimeUnit;

public final class DeadlockHarness {

    private static final long JOIN_TIMEOUT_MILLIS = 3_000L;
    private DeadlockHarness() {}

    public static void main(String[] args) throws InterruptedException {
        // Initialize the aligner from the main thread so its own <clinit> is not
        // part of the race, then arm it for the two workers only.
        StartupAlignment.expectParticipants(2);

        Thread bonusStartupWorker = new Thread(
                () -> System.out.println("  bonus grant for a 65.00 deposit = " + BonusService.grantFor(6500)),
                "bonusStartupWorker");
        Thread ledgerStartupWorker = new Thread(
                () -> System.out.println("  CLIENT_BONUS_RESERVED index = "
                        + FundsLedger.indexOfPosition("CLIENT_BONUS_RESERVED")),
                "ledgerStartupWorker");

        bonusStartupWorker.setDaemon(true);
        ledgerStartupWorker.setDaemon(true);
        bonusStartupWorker.start();
        ledgerStartupWorker.start();
        bonusStartupWorker.join(JOIN_TIMEOUT_MILLIS);
        ledgerStartupWorker.join(JOIN_TIMEOUT_MILLIS);

        boolean bonusAlive = bonusStartupWorker.isAlive();
        boolean ledgerAlive = ledgerStartupWorker.isAlive();
        System.out.println("after " + JOIN_TIMEOUT_MILLIS + " ms:");
        System.out.println("  bonusStartupWorker  alive=" + bonusAlive + " state=" + bonusStartupWorker.getState());
        System.out.println("  ledgerStartupWorker alive=" + ledgerAlive + " state=" + ledgerStartupWorker.getState());
        if (!bonusAlive && !ledgerAlive) {
            System.out.println("NO DEADLOCK: both workers finished");
            return;
        }

        ThreadMXBean threads = ManagementFactory.getThreadMXBean();
        long[] fullDeadlock = threads.findDeadlockedThreads();
        long[] monitorDeadlock = threads.findMonitorDeadlockedThreads();
        System.out.println("  ThreadMXBean.findDeadlockedThreads()        = "
                + (fullDeadlock == null ? "null" : Arrays.toString(fullDeadlock)));
        System.out.println("  ThreadMXBean.findMonitorDeadlockedThreads() = "
                + (monitorDeadlock == null ? "null" : Arrays.toString(monitorDeadlock)));
        System.out.println();
        System.out.println("---- stacks of the two startup workers ----");
        for (Thread worker : new Thread[] { bonusStartupWorker, ledgerStartupWorker }) {
            ThreadInfo info = threads.getThreadInfo(worker.threadId(), Integer.MAX_VALUE);
            if (info == null) {
                System.out.println("\"" + worker.getName() + "\" gone");
                continue;
            }
            System.out.printf("\"%s\" tid=%d state=%s lockName=%s lockOwnerName=%s blockedCount=%d waitedCount=%d%n",
                    info.getThreadName(), info.getThreadId(), info.getThreadState(), info.getLockName(),
                    info.getLockOwnerName(), info.getBlockedCount(), info.getWaitedCount());
            for (StackTraceElement frame : info.getStackTrace()) {
                System.out.println("\tat " + frame);
            }
            System.out.println();
        }
        System.out.println("PROCESS IS STUCK: two live threads, neither making progress,"
                + " and no monitor cycle to find");
        TimeUnit.MILLISECONDS.sleep(50);
        Runtime.getRuntime().halt(3);
    }
}
```

Real output:

```console
$ java -cp out quizstakes.cycle.DeadlockHarness
after 3000 ms:
  bonusStartupWorker  alive=true state=RUNNABLE
  ledgerStartupWorker alive=true state=RUNNABLE
  ThreadMXBean.findDeadlockedThreads()        = null
  ThreadMXBean.findMonitorDeadlockedThreads() = null

---- stacks of the two startup workers ----
"bonusStartupWorker" tid=20 state=RUNNABLE lockName=null lockOwnerName=null blockedCount=0 waitedCount=0
	at app//quizstakes.cycle.BonusService.<clinit>(BonusService.java:20)
	at app//quizstakes.cycle.DeadlockHarness.lambda$main$0(DeadlockHarness.java:20)
	at app//quizstakes.cycle.DeadlockHarness$$Lambda/0x0000007001000bf0.run(Unknown Source)
	at java.base@21.0.7/java.lang.Thread.runWith(Thread.java:1596)
	at java.base@21.0.7/java.lang.Thread.run(Thread.java:1583)

"ledgerStartupWorker" tid=21 state=RUNNABLE lockName=null lockOwnerName=null blockedCount=0 waitedCount=0
	at app//quizstakes.cycle.FundsLedger.<clinit>(FundsLedger.java:32)
	at app//quizstakes.cycle.DeadlockHarness.lambda$main$1(DeadlockHarness.java:24)
	at app//quizstakes.cycle.DeadlockHarness$$Lambda/0x0000007001001000.run(Unknown Source)
	at java.base@21.0.7/java.lang.Thread.runWith(Thread.java:1596)
	at java.base@21.0.7/java.lang.Thread.run(Thread.java:1583)

PROCESS IS STUCK: two live threads, neither making progress, and no monitor cycle to find
```

Four facts in that dump, in order of diagnostic value.

**The `<clinit>` frames.** `BonusService.java:20` is exactly
`ledgerPositionCountSeen = FundsLedger.POSITION_COUNT;` and `FundsLedger.java:32` is exactly
`bonusCapSeen = BonusService.BONUS_CAP_MINOR_UNITS;` — both threads parked on the cross-reference
line. **Two threads simultaneously inside two different `<clinit>` frames, forever, is the
signature.**

**`state=RUNNABLE`, not `BLOCKED`.** The threads burn no CPU (`cpu=0.64ms` and `cpu=0.26ms` over 8
seconds of hanging, from the `jstack` below) yet report `RUNNABLE`, because the step 2 wait happens
below the Java level. Any rule shaped "alert when threads are `BLOCKED`" is blind to this.

**`lockName=null`, `lockOwnerName=null`, `blockedCount=0`, `waitedCount=0`.** The one API that would
name who holds what is empty.

**Both detectors return `null`.** The single most valuable fact in the file. The strictly-stronger
`findDeadlockedThreads` covers object monitors *and* ownable synchronizers — its javadoc's
"deadlocked" is exactly a cycle in those two graphs — and sees nothing, because the initialization
lock is neither. **An operator who checks for a deadlock and gets a clean answer concludes the
process is not deadlocked. It is.**

Reliability, ten consecutive runs (exit `3` is the deadlock-detected path, `0` completion) — ten for
ten, and the barrier is what does that; without it the reproduction is luck:

```console
$ for i in 1 2 3 4 5 6 7 8 9 10; do java -cp out quizstakes.cycle.DeadlockHarness >/dev/null 2>&1; echo -n "$? "; done
3 3 3 3 3 3 3 3 3 3
```

### What `jstack` and `jcmd` say

A second entry point, `HungStartup`, starts the same two workers as non-daemon threads and never
joins, so the JVM stays hung and attachable. It printed `pid 78784 hung; jstack it`, and
`jstack 78784` gave (both worker entries, verbatim, minus the two trailing
`java.lang.Thread.runWith` / `run` frames):

```text
"bonusStartupWorker" #20 [25091] prio=5 os_prio=31 cpu=0.64ms elapsed=8.04s tid=0x000000011e80c600 nid=25091 in Object.wait()  [0x000000016fb8e000]
   java.lang.Thread.State: RUNNABLE
	at quizstakes.cycle.BonusService.<clinit>(BonusService.java:20)
	- waiting on the Class initialization monitor for quizstakes.cycle.FundsLedger
	at quizstakes.cycle.HungStartup.lambda$main$0(HungStartup.java:13)
	at quizstakes.cycle.HungStartup$$Lambda/0x0000007001000bf0.run(Unknown Source)

"ledgerStartupWorker" #21 [29443] prio=5 os_prio=31 cpu=0.26ms elapsed=8.04s tid=0x000000011f008200 nid=29443 in Object.wait()  [0x000000016fd9a000]
   java.lang.Thread.State: RUNNABLE
	at quizstakes.cycle.FundsLedger.<clinit>(FundsLedger.java:32)
	- waiting on the Class initialization monitor for quizstakes.cycle.BonusService
	at quizstakes.cycle.HungStartup.lambda$main$1(HungStartup.java:14)
	at quizstakes.cycle.HungStartup$$Lambda/0x0000007001001000.run(Unknown Source)
```

`jcmd 78784 Thread.print` produced byte-identical worker entries — same annotation, same states.

This is the good news, and the difference between a five-minute diagnosis and a five-day one:
`- waiting on the Class initialization monitor for quizstakes.cycle.FundsLedger` is a frame
annotation the Java API cannot give you, and the mirror-image line under the other thread closes the
cycle. Note also the contradiction between one thread's own two lines — header `in Object.wait()`,
`Thread.State: RUNNABLE`: the VM-level wait is visible to the dump machinery but not reflected in the
Java thread state.

The bad news, in the same dump: no deadlock report.

```console
$ jstack 78784 | grep -c "Found one Java-level deadlock"
0
```

`jstack` printed both edges of the cycle and its deadlock analyser still says nothing, because that
analyser looks for monitor and synchronizer cycles. **The annotation is the evidence; the deadlock
section is not.** Read the frames, not the summary.

**Interview:** "A production JVM is hung, `jstack` reports no deadlock, threads are `RUNNABLE`, CPU
is idle. What do you look at?" The `<clinit>` frames and any
`waiting on the Class initialization monitor` annotations — nothing else produces that combination.

### The lock that does not help

The instinct is to serialise both initializers behind one shared monitor taken first in each
`<clinit>`. Run as a third variant (`quizstakes.locked`, same harness, same barrier), it produced:

```console
  bonusStartupWorker  alive=true state=RUNNABLE
  ledgerStartupWorker alive=true state=BLOCKED
  ThreadMXBean.findDeadlockedThreads()        = null
  ThreadMXBean.findMonitorDeadlockedThreads() = null
"ledgerStartupWorker" tid=21 state=BLOCKED lockName=java.lang.Object@312b1dae lockOwnerName=bonusStartupWorker blockedCount=2 waitedCount=0
	at app//quizstakes.locked.FundsLedger.<clinit>(FundsLedger.java:10)
PROCESS IS STUCK: two live threads, neither making progress, and no monitor cycle to find
```

A *hybrid* cycle: `bonusStartupWorker` holds `BonusService`'s initialization lock *and* the global
monitor while waiting for `FundsLedger`'s; `ledgerStartupWorker` holds `FundsLedger`'s initialization
lock while blocked on the global monitor. Half the cycle became a Java monitor, so that thread now
reports `BLOCKED` with a named owner — and `findDeadlockedThreads()` *still* returns `null`, because
it needs the *whole* cycle in the monitor graph. The lock made the dump prettier and the deadlock no
less permanent: no ordering of a lock you added removes the ordering the JVM already imposed via
`getstatic`. The two static blocks are in the Pitfalls entry below; nothing else changed.

## How this shows up in production

QuizStakes starts, the readiness probe hits a single-threaded warm-up that touches `BonusService`
first, and everything comes up green — with `FundsLedger.bonusCapSeen == 0`, unnoticed because no
posting has exercised it yet. Then the first request burst arrives and the pool touches both holders
at once: a worker handling a bonus grant (3.1k/day, 8/sec) and a worker handling a stake reservation
(1,200/sec peak) hit `BonusService` and `FundsLedger` in the same millisecond. Two pool threads die
into `<clinit>` frames, every later thread that touches either class parks on §5.5 step 2 behind
them, and the pool drains one request at a time until it is gone. No exception, no log line, no CPU,
no memory growth, no GC activity. The liveness probe times out, the orchestrator restarts the pod,
the restart succeeds under low load, and it reappears at the next ramp — and because a restart
"fixes" it and the dump reports no deadlock, the investigation goes to the load balancer and the
database for two days.

## The fixes, ranked

| Rank | Fix | Works? | Why |
|---|---|---|---|
| 1 | Remove the cycle — one class owns the shared constant, both read it | Yes, permanently | No edge, so no cycle at any concurrency, in any touch order |
| 2 | Move the cross-reference out of `<clinit>` into an `init()` called after both classes exist | Yes | The read happens with no initialization lock held by anyone |
| 3 | Lazy holder class on one side | Yes | Breaks one edge of the cycle; see below |
| 4 | Force initialization order from a single thread at startup | Yes, fragile | Correct only while every entry point goes through the forced order |
| 5 | `synchronized` or a lock-ordering convention | **No** | Measured above: the cycle is not made of locks you own |
| 6 | Make the field a compile-time constant | Accidental | The fold removes the `getstatic`; any change to a non-constant initializer brings the deadlock back |

Rank 4 is what teams ship under incident pressure: a `StartupWarmup` touching `FundsLedger` then
`BonusService` from the main thread before the listener opens. It works — the classes are fully
initialized before any pool thread exists — and it breaks silently the day someone adds a lazy
endpoint, a scheduler, or a `@PostConstruct` on another thread. It buys a night, not a fix. Rank 5 is
the one to say out loud in an interview: **you cannot fix this with a lock, because the locks in the
cycle are not yours.**

### The holder-idiom fix, run

`FundsLedger` stops reading `BonusService` in `<clinit>` and reads it from a private nested holder
whose own initialization is triggered by the first call to `bonusCapSeen()` — by which time
`FundsLedger`'s initialization lock is long released. `BonusService` is unchanged.

```java
package quizstakes.fixed;

import java.util.List;

/** Same class, one edge of the cycle removed: the bonus cap moves out of {@code <clinit>} into a holder. */
public final class FundsLedger {

    public static final List<String> POSITIONS = List.of(
            "CLIENT_CASH_AVAILABLE", "CLIENT_CASH_RESERVED", "CLIENT_BONUS_AVAILABLE",
            "CLIENT_BONUS_RESERVED", "SUSPENSE", "PSP_RECEIVABLE", "BANK_SETTLEMENT",
            "HOUSE_REVENUE", "PROMOTIONAL_EXPENSE", "FEES", "CHARGEBACK_LOSS");

    public static final int POSITION_COUNT;

    static {
        StartupAlignment.arriveInsideStaticInitializer();
        POSITION_COUNT = POSITIONS.size();
        // No reference to BonusService here. The cycle is gone.
    }
    /** Initialized on first use of bonusCapSeen(), not with FundsLedger. */
    private static final class BonusCapHolder {
        static final int VALUE = BonusService.BONUS_CAP_MINOR_UNITS;
    }
    private FundsLedger() {}

    public static int bonusCapSeen() {
        return BonusCapHolder.VALUE;
    }

    public static int indexOfPosition(String position) {
        return POSITIONS.indexOf(position);
    }
}
```

The identical two-thread harness, barrier still armed, run three times — first run shown, the other
two identical but for the elapsed figure (10392 and 3146 microseconds):

```console
$ java -cp out quizstakes.fixed.FixedHarness
  CLIENT_BONUS_RESERVED index = 3
  bonus grant for a 65.00 deposit = 650
bonusStartupWorker  alive=false state=TERMINATED
ledgerStartupWorker alive=false state=TERMINATED
both workers joined in 3016 microseconds
BonusService.ledgerPositionCountSeen = 11   (expected 11)
FundsLedger.bonusCapSeen()           = 10000   (expected 10000)
NO DEADLOCK
```

Both workers terminate in milliseconds, and `bonusCapSeen()` is `10000` — the holder
fixed Run 1's silent zero too, because by the time it initializes `BonusService.<clinit>` has
genuinely completed. One directed edge remains (`BonusService` initializes `FundsLedger`), which is
fine: a directed acyclic graph of static initializers cannot deadlock, however many threads enter it.

**Insight:** the holder idiom is usually sold as a laziness optimisation. Its more important property
is structural: **a holder class is a place to put one edge of an initialization graph so that edge is
no longer in a cycle.**

## Finding it before it ships

`javac -Xlint:all` on the cyclic pair produces **no output at all** — no warning, no note — and the
full `javac --help-lint` key list contains nothing about initialization cycles. The nearest key is
`this-escape`, which is the 4.8.2 trap owned by
[Construction and initialization-order harnesses](05a-construction-and-init-harnesses.md). What can
and cannot see it:

| Technique | Sees it? | Note |
|---|---|---|
| `javac -Xlint:all` | No | Verified: zero diagnostics on the cyclic pair |
| Unit tests | No | Single-threaded, so step 3 makes them pass with a wrong value |
| `findDeadlockedThreads` in a watchdog | No | Verified `null` in both the plain and the `synchronized` variant |
| `jstack` / `jcmd Thread.print`, read by a human | Yes | The `Class initialization monitor` annotation names both edges |
| A concurrent smoke test that touches every holder from a pool on a cold JVM | Yes | The only automatable check found here; a barrier is not needed at scale |
| Static bytecode scan for `<clinit>` out-edges, then a cycle search | Yes, in principle | Buildable from the `javap` evidence above; nothing off-the-shelf was verified to do it |

No standard JDK tool catches this before it ships. The practical defence is a review rule: **a
`static {}` block that names another application class is a code smell — justify it or move it into a
holder.**

## Diff vs the real one

| Axis | This harness | A real production hang | Why the gap |
|---|---|---|---|
| Reproduction reliability | 10/10 runs, deterministic via `CyclicBarrier` | Rare; needs two threads inside two `<clinit>` bodies within microseconds | The barrier manufactures a window that real code holds open only while doing I/O in `<clinit>` |
| Edge cases | Exactly two classes, one cycle, two threads | Cycles of three or more classes across framework and application code, N pool threads piling up behind them | Longer cycles are harder to see; extra threads all park on step 2 and look identical |
| What the thread dump shows | `<clinit>` frames, `RUNNABLE`, `lockName=null`; `jstack` adds `waiting on the Class initialization monitor for X` | Identical, but buried among hundreds of pool threads also parked on step 2 | Nothing distinguishes the two culprits from their victims except being *inside* `<clinit>` rather than at its call site |
| `findDeadlockedThreads` | `null` (verified) | `null` | The initialization lock is neither an object monitor nor an ownable synchronizer |
| Single-threaded case distinguishable? | Yes, side by side: `bonusCapSeen = 0` versus a hang | No — the wrong value has been in production for months before the hang | Step 3's re-entrance turns the cycle into a data bug until concurrency turns it into a liveness bug |
| Thread safety | The pair is *perfectly* thread-safe by the spec | Same | The JVM's guarantee is intact, and the guarantee is what stops the process |
| Null policy | Silent `0` here (`int` field); a `null` for a reference field, then an NPE inside `<clinit>` | An NPE inside `<clinit>` becomes `ExceptionInInitializerError`, and §5.5 step 5 marks the class permanently `erroneous` | An `int` cycle lies quietly; a reference cycle can be louder but leaves the class unusable for the JVM's lifetime |
| Intrinsics / allocation tricks | Neither involved | Neither involved | `<clinit>` is ordinary bytecode, the `getstatic` initialization check is a JIT-elided guard rather than an intrinsic, and the failure is a liveness property, not an allocation one |
| Serialization | Not applicable | Deserializing an object initializes its class, so a deserializer thread is a plausible second toucher | Any code path can be the second thread; framework threads are the common real culprits |
| Recovery | Harness reports and `halt(3)`s | Process restart only, the wait being uninterruptible per §5.5 step 2 | No timeout, no interrupt and no unwind exists |
| Why the JVM bothers | — | Exactly-once, thread-safe initialization is a language guarantee thousands of singletons rely on | Cycle detection would have to reject the legal single-threaded re-entrant case, so the spec allows cycles instead |

## Pitfalls

### Believing class initialization cannot deadlock because the JVM makes it thread-safe

**Wrong**

```java
// "static init is thread-safe, so I don't need to think about it"
static { ledgerPositionCountSeen = FundsLedger.POSITION_COUNT; }   // in BonusService
static { bonusCapSeen = BonusService.BONUS_CAP_MINOR_UNITS; }      // in FundsLedger
```

Real output, two threads:

```console
  bonusStartupWorker  alive=true state=RUNNABLE
  ledgerStartupWorker alive=true state=RUNNABLE
PROCESS IS STUCK: two live threads, neither making progress, and no monitor cycle to find
```

**Right**

One edge only, or a holder class on one side, so `FundsLedger` no longer names `BonusService` in
`<clinit>`:

```java
private static final class BonusCapHolder {
    static final int VALUE = BonusService.BONUS_CAP_MINOR_UNITS;
}

public static int bonusCapSeen() {
    return BonusCapHolder.VALUE;
}
```

```console
both workers joined in 3016 microseconds
FundsLedger.bonusCapSeen()           = 10000   (expected 10000)
NO DEADLOCK
```

**Why people believe it:** the guarantee is real and correctly stated everywhere. The unstated half
is that it is delivered with a per-class lock, and a per-class lock plus a cycle plus two threads is
the textbook deadlock recipe. Thread-safe means "no torn state", never "no deadlock".

### Trusting `findDeadlockedThreads` or a monitor-cycle dump to find it

**Wrong**

```java
long[] deadlocked = ManagementFactory.getThreadMXBean().findDeadlockedThreads();
if (deadlocked == null) {
    log.info("watchdog: no deadlock");   // the process is deadlocked right now
}
```

```console
  ThreadMXBean.findDeadlockedThreads()        = null
  ThreadMXBean.findMonitorDeadlockedThreads() = null
$ jstack 78784 | grep -c "Found one Java-level deadlock"
0
```

**Right**

Look for the frames, not the verdict. A watchdog that means it must scan stacks:

```java
ThreadMXBean threads = ManagementFactory.getThreadMXBean();
for (ThreadInfo info : threads.dumpAllThreads(false, false, Integer.MAX_VALUE)) {
    for (StackTraceElement frame : info.getStackTrace()) {
        if ("<clinit>".equals(frame.getMethodName())) {
            log.warn("thread {} is inside {}.<clinit>", info.getThreadName(), frame.getClassName());
        }
    }
}
```

Two or more threads reported here at once, unchanging across two samples, is the signature. For a
human `jstack` is better: its annotation
`- waiting on the Class initialization monitor for quizstakes.cycle.FundsLedger` names the edge.

**Why people believe it:** `findDeadlockedThreads` is documented as the strong one — monitors *and*
ownable synchronizers, against `findMonitorDeadlockedThreads`' monitors only — so it reads like
"finds all deadlocks". It finds all deadlocks *in those two graphs*; the initialization lock is in
neither, and `jstack`'s deadlock section uses the same analysis.

### Believing the single-threaded success means the cycle is harmless

**Wrong**

```java
// green test suite:
assertEquals(650, BonusService.grantFor(6500));
assertEquals(3, FundsLedger.indexOfPosition("CLIENT_BONUS_RESERVED"));
```

```console
thread: main | touching first: bonus
BonusService.grantFor(65_00) = 650
FundsLedger.bonusCapSeen             = 0   (expected 10000)
run completed, no deadlock
```

Both assertions pass, while the cap the ledger validates every `PROMOTIONAL_EXPENSE` posting
against is `0`.

**Right**

Assert the cross-referenced values, and add the Run 2 harness as a test with a join timeout so a
cycle fails the build instead of a probe:

```java
assertEquals(11, BonusService.ledgerPositionCountSeen);
assertEquals(10_000, FundsLedger.bonusCapSeen());   // fails at 0 on the cyclic version
```

**Why people believe it:** §5.5 step 3 is *designed* to make the single-threaded case succeed, and it
succeeds silently rather than throwing. A green suite plus a numerically plausible value reads as
evidence of correctness. It is evidence that only one thread ran.

### Believing a `synchronized` block or a lock ordering fixes it

**Wrong**

```java
// quizstakes.locked.StartupOrdering: public static final Object HOLDER_INIT_LOCK = new Object();

static {                                        // BonusService, unchanged otherwise
    synchronized (StartupOrdering.HOLDER_INIT_LOCK) {
        ledgerPositionCountSeen = FundsLedger.POSITION_COUNT;
        BONUS_CAP_MINOR_UNITS = 10_000;
    }
}

static {                                        // FundsLedger, unchanged otherwise
    synchronized (StartupOrdering.HOLDER_INIT_LOCK) {
        POSITION_COUNT = 11;
        bonusCapSeen = BonusService.BONUS_CAP_MINOR_UNITS;
    }
}
```

Measured result: `bonusStartupWorker alive=true state=RUNNABLE`,
`ledgerStartupWorker alive=true state=BLOCKED`, `findDeadlockedThreads() = null`, process stuck.

**Right**

Delete the edge — there is no lock-based fix, so the fix is structural: a holder class, an `init()`
method called after both classes exist, or a single owner for the shared constant.

```java
static {
    POSITION_COUNT = POSITIONS.size();
    // No reference to BonusService here. The cycle is gone.
}
```

**Why people believe it:** every other deadlock they have fixed *was* fixable by consistent lock
ordering, and that instinct is right whenever both locks are yours. Here one lock per cycle belongs
to the JVM, is acquired implicitly by a `getstatic`, and is invisible to your convention — so your
lock joins the cycle rather than replacing it.

## Cheat sheet

| Fact | Value |
|---|---|
| Spec | JVMS 21 §5.5, twelve-step procedure; lock `LC`, one per class, mapping implementation-defined. Cycles legal per §5.4.3.6 |
| Step 1 / Step 2 | Acquire `LC`; if in progress by *another* thread, release and **block, uninterruptibly, no timeout** |
| Step 3 | In progress by *the current* thread: release `LC`, **complete normally** (re-entrant) |
| Steps 5 / 6 / 9 / 10 | `erroneous` means `NoClassDefFoundError` forever; record-and-release; run `<clinit>`; mark initialized and notify waiters |
| Triggers | `new`, `getstatic`, `putstatic`, `invokestatic`, reflection, subclass init, start class |
| 1 thread / 2 threads on a cycle | Succeeds, second class reads default `0` or `null` / permanent hang |
| Observed | `Thread.State` `RUNNABLE` (not `BLOCKED`), CPU idle, `ThreadInfo` lock fields all null/zero |
| Both `ThreadMXBean` deadlock finders | `null` — measured |
| `jstack` | No deadlock section (measured); frames annotated `- waiting on the Class initialization monitor for <class>` |
| Real fixes | Remove the edge; holder class; post-init `init()`; forced single-thread order (fragile). A lock never works |

## Self-test

**Q1.** Two threads, two classes whose static initializers reference each other. Why is this a
deadlock and not a race the JVM resolves?

<details><summary>Answer</summary>

Because JVMS §5.5 step 1 makes each thread acquire the target class's unique initialization lock `LC`
and step 6 records that class as in-progress by that thread. Thread A, initializing `BonusService`,
reaches the `getstatic` on `FundsLedger`, runs the whole procedure for `FundsLedger` and lands on
step 2 — in progress by *some other thread* — so it blocks until notified; thread B is symmetrically
blocked on `BonusService`. The notification in step 10 only happens when a `<clinit>` completes
normally, and neither ever will. The procedure has no cycle detection and step 2 has no timeout, so
the JVM has nothing with which to resolve it.

</details>

**Q2.** The same cyclic pair, one thread. What happens, and which spec step decides it?

<details><summary>Answer</summary>

It completes, with a wrong value. Step 3: in progress *by the current thread* is treated as a
recursive request, so the procedure returns and the caller reads fields of a class whose `<clinit>`
is part-way through — any field not yet assigned reads its default. Measured: touching `BonusService`
first, `FundsLedger.bonusCapSeen` is `0` instead of `10000`; touching `FundsLedger` first it is
`10000`, because `POSITION_COUNT` is assigned before that class crosses over. Opposite correctness
from the same code, decided by touch order.

</details>

**Q3.** `findDeadlockedThreads()` returns `null` while the process is hung on an initialization
cycle. Is that a JDK bug?

<details><summary>Answer</summary>

No. Its contract is a cycle in object-monitor ownership or in ownable synchronizers
(`AbstractOwnableSynchronizer`, so `ReentrantLock` and friends), and the initialization lock is
neither: the mapping from class to `LC` is implementation-defined, the wait happens below the Java
level, and `ThreadInfo` reports no lock name or owner for it. Both finders returned `null` here and
`jstack` printed no `Found one Java-level deadlock` section, measured on JDK 21.0.7. The detector
answers the question it was designed for; that is just not the question you have.

</details>

**Q4.** Why does the holder-class idiom fix this, and why is calling it "a laziness optimisation"
underselling it?

<details><summary>Answer</summary>

Moving `BonusService.BONUS_CAP_MINOR_UNITS` into a private nested `BonusCapHolder` means
`FundsLedger.<clinit>` no longer contains a `getstatic` against `BonusService`, so the edge
`FundsLedger -> BonusService` leaves the initialization graph. What is left is a single directed edge
`BonusService -> FundsLedger`, and a directed acyclic initialization graph cannot deadlock at any
level of concurrency. The laziness is a side effect. Measured: the same two-thread harness completes
in under 4 ms and `bonusCapSeen()` returns the correct `10000`, because the holder initializes after
`BonusService.<clinit>` has genuinely finished.

</details>

**Q5.** Can you recover a hung JVM in this state without restarting it?

<details><summary>Answer</summary>

No. JVMS §5.5 step 2 blocks "until informed that the in-progress initialization has completed" and
states that "thread interrupt status is unaffected by execution of the initialization procedure", so
the wait has no timeout and ignores `Thread.interrupt()`. There is no API to abandon an in-progress
initialization, the two classes never reach step 10 to notify anyone, and every thread that later
touches either class joins the same wait, so the pool drains rather than recovers. Restart is the
only option — which is exactly why the incident looks transient and gets misattributed.

</details>

## Open questions

- **Unverified:** why the stuck threads report `Thread.State: RUNNABLE` while `jstack`'s header line
  for the same thread says `in Object.wait()`. The observation is measured and reproducible; the
  mechanism is not. Reading `InstanceKlass::initialize_impl` and its `ObjectLocker` wait in
  `src/hotspot/share/oops/instanceKlass.cpp` would settle whether the Java thread state is
  deliberately left untouched or simply not updated for a VM-level wait.
- **Unverified:** whether any off-the-shelf static-analysis tool detects initialization cycles. Only
  `javac -Xlint:all` was tested (no diagnostics); running SpotBugs, Error Prone or SonarQube against
  the cyclic pair would settle it.

---

**Leaves covered:** 4.8.4 (1 leaf)
**Leaves deferred:** none
**Diagrams included:** none
**Target version:** Java 21 LTS
**Lines:** 898
