# 05 Multithreading and Concurrency — The deadlock and livelock harnesses — BUILD IT (§4.8, leaves 4.8.3–4.8.4)

**Target version: Java 21 LTS.** | **Part 4 of 5** | [Index](../00-index.md)
Previous: [The visibility and lost-update harnesses](08-visibility-and-lost-update.md) · Next: [The false-sharing and starvation harnesses](08c-false-sharing-and-starvation.md)

Two failure modes that both look like "the system stopped making progress," and are diagnosed by
opposite symptoms. The domain object throughout is `FundsLedger`, transferring between two
client accounts, and the two locks are the accounts' own monitors.

## 4.8.3 — The deadlock harness

### What it demonstrates

Two threads each hold one lock and wait for the other's lock, in opposite acquisition order.
Neither can ever proceed. This is the textbook circular-wait condition, built from a realistic
operation — a fund transfer between two client accounts — where the lock-ordering bug is easy to
introduce by accident: `transfer(accountA, accountB, amount)` locks in argument order, so a
concurrent `transfer(accountB, accountA, amount)` locks in the opposite order, and the two calls
deadlock if their timing interleaves at the wrong moment.

### The runnable code

```java
package quizstakes.concurrency.harness;

import java.math.BigDecimal;
import java.util.concurrent.CountDownLatch;

/**
 * Two accounts, two threads transferring in opposite directions.
 * BROKEN: locks are acquired in argument order, so the two concurrent
 * transfers lock accountA/accountB and accountB/accountA respectively,
 * and can deadlock.
 */
public final class DeadlockHarness {

    static final class ClientAccount {
        final String accountId;
        BigDecimal cashAvailable;

        ClientAccount(String accountId, BigDecimal cashAvailable) {
            this.accountId = accountId;
            this.cashAvailable = cashAvailable;
        }
    }

    // BROKEN: locks accountId order is whatever the caller passes
    static void transfer(ClientAccount from, ClientAccount to, BigDecimal amount)
            throws InterruptedException {
        synchronized (from) {
            Thread.sleep(50); // widen the window so the race is reliably observed
            synchronized (to) {
                from.cashAvailable = from.cashAvailable.subtract(amount);
                to.cashAvailable = to.cashAvailable.add(amount);
            }
        }
    }

    public static void main(String[] args) throws InterruptedException {
        ClientAccount accountAlpha = new ClientAccount("client-alpha-9001", new BigDecimal("500.00"));
        ClientAccount accountBeta = new ClientAccount("client-beta-4477", new BigDecimal("300.00"));

        CountDownLatch startGate = new CountDownLatch(1);

        Thread paymentRunWorker2 = new Thread(() -> {
            try {
                startGate.await();
                System.out.println("payment-run-worker-2: transferring alpha -> beta");
                transfer(accountAlpha, accountBeta, new BigDecimal("50.00"));
                System.out.println("payment-run-worker-2: done");
            } catch (InterruptedException e) {
                Thread.currentThread().interrupt();
            }
        }, "payment-run-worker-2");

        Thread paymentRunWorker7 = new Thread(() -> {
            try {
                startGate.await();
                System.out.println("payment-run-worker-7: transferring beta -> alpha");
                transfer(accountBeta, accountAlpha, new BigDecimal("20.00"));
                System.out.println("payment-run-worker-7: done");
            } catch (InterruptedException e) {
                Thread.currentThread().interrupt();
            }
        }, "payment-run-worker-7");

        paymentRunWorker2.start();
        paymentRunWorker7.start();
        startGate.countDown();

        paymentRunWorker2.join(5000);
        paymentRunWorker7.join(5000);
        System.out.println("worker-2 alive: " + paymentRunWorker2.isAlive());
        System.out.println("worker-7 alive: " + paymentRunWorker7.isAlive());
        // Observed: both threads print their opening line, neither prints "done",
        // both remain alive after the 5s join timeout — permanent deadlock.
    }
}
```

### What you actually observe when you run it

Both threads print their "transferring" line, then both block forever: `payment-run-worker-2`
holds `accountAlpha`'s monitor and waits for `accountBeta`'s; `payment-run-worker-7` holds
`accountBeta`'s monitor and waits for `accountAlpha`'s. Neither `join` call returns within the
timeout, and both `isAlive()` checks report `true`. The `Thread.sleep(50)` inside the harness
exists only to widen the interleaving window so the deadlock reproduces reliably in a small demo
— production deadlocks of this shape do not need an artificial sleep, they just need unlucky
timing at scale, which is why 2.8M/day stake settlements and payment runs both flowing through
`FundsLedger` make this a realistic, not contrived, risk.

### The watchdog that detects it

```java
package quizstakes.concurrency.harness;

import java.lang.management.ManagementFactory;
import java.lang.management.ThreadInfo;
import java.lang.management.ThreadMXBean;
import java.util.concurrent.Executors;
import java.util.concurrent.ScheduledExecutorService;
import java.util.concurrent.TimeUnit;

/**
 * A watchdog thread that polls ThreadMXBean.findDeadlockedThreads() and
 * logs the cycle when one appears. Run alongside DeadlockHarness.
 */
public final class DeadlockWatchdog {

    public static void main(String[] args) {
        ThreadMXBean threadBean = ManagementFactory.getThreadMXBean();
        ScheduledExecutorService watchdogScheduler =
                Executors.newSingleThreadScheduledExecutor(r -> {
                    Thread t = new Thread(r, "deadlock-watchdog");
                    t.setDaemon(true);
                    return t;
                });

        watchdogScheduler.scheduleAtFixedRate(() -> {
            long[] deadlockedIds = threadBean.findDeadlockedThreads();
            if (deadlockedIds == null) {
                return;
            }
            ThreadInfo[] infos = threadBean.getThreadInfo(deadlockedIds, true, true);
            StringBuilder report = new StringBuilder("DEADLOCK DETECTED among threads:\n");
            for (ThreadInfo info : infos) {
                report.append("  ").append(info.getThreadName())
                      .append(" is waiting on ").append(info.getLockName())
                      .append(" held by ").append(info.getLockOwnerName())
                      .append('\n');
            }
            System.err.println(report);
        }, 1, 1, TimeUnit.SECONDS);

        // Reproduce DeadlockHarness's transfer scenario here or attach to a
        // running JVM via jcmd/jstack instead; the polling loop above is the
        // reusable part.
    }
}
```

**Reading `findDeadlockedThreads()`'s output for this scenario:**

```
DEADLOCK DETECTED among threads:
  payment-run-worker-2 is waiting on quizstakes...ClientAccount@1a2b3c4 held by payment-run-worker-7
  payment-run-worker-7 is waiting on quizstakes...ClientAccount@5d6e7f8 held by payment-run-worker-2
```

Each `ThreadInfo` names the monitor it is blocked on (`getLockName()`) and the thread currently
holding that monitor (`getLockOwnerName()`). The two lines form the cycle explicitly:
`worker-2 → waits on Beta's lock → held by worker-7 → waits on Alpha's lock → held by worker-2`.
That is the entire diagnosis — a genuine deadlock cycle, not a slow operation — and it is exactly
what `jstack <pid>` prints under a `Found one Java-level deadlock:` heading using the same
underlying `ThreadMXBean` data.

**Insight:** `findDeadlockedThreads()` (as opposed to the deprecated
`findMonitorDeadlockedThreads()`) also detects cycles that include `java.util.concurrent.locks`
ownable synchronizers, not just intrinsic monitors — it walks the JVM's internal lock-ownership
graph, which is why it can name the exact objects involved rather than merely reporting "no
progress."

### The fix

```java
package quizstakes.concurrency.harness;

import java.math.BigDecimal;

public final class DeadlockHarnessFixed {

    static final class ClientAccount implements Comparable<ClientAccount> {
        final String accountId;
        BigDecimal cashAvailable;

        ClientAccount(String accountId, BigDecimal cashAvailable) {
            this.accountId = accountId;
            this.cashAvailable = cashAvailable;
        }

        @Override
        public int compareTo(ClientAccount other) {
            return this.accountId.compareTo(other.accountId);
        }
    }

    // FIX: always acquire locks in a total, global order (here: accountId order),
    // regardless of which account is "from" and which is "to".
    static void transfer(ClientAccount from, ClientAccount to, BigDecimal amount) {
        ClientAccount first = from.compareTo(to) <= 0 ? from : to;
        ClientAccount second = from.compareTo(to) <= 0 ? to : from;

        synchronized (first) {
            synchronized (second) {
                from.cashAvailable = from.cashAvailable.subtract(amount);
                to.cashAvailable = to.cashAvailable.add(amount);
            }
        }
    }
}
```

### Why the fix works

A deadlock requires all four Coffman conditions simultaneously: mutual exclusion, hold-and-wait,
no preemption, and circular wait. The harness cannot remove mutual exclusion (locks must exclude)
or preemption (Java's intrinsic locks are never revoked from a thread), and hold-and-wait is
inherent to needing both accounts locked at once. The one condition that is a pure ordering
choice is **circular wait** — and imposing a total order on lock acquisition (here, by
`accountId`) guarantees that any two threads locking the same pair of accounts always request
them in the same sequence, so a cycle can never form: whichever thread acquires the
lower-ordered account first will find the higher-ordered account free of any thread that has
*not yet* acquired the lower one.

> **Definition:** A deadlock is a set of threads each holding a resource the others are waiting
> for, forming a cycle with no possible progress; it is prevented, not detected, by imposing a
> consistent global acquisition order on every lock two or more threads can hold simultaneously.

**Pitfall:** fixing "the deadlock I saw" by adding a `tryLock` with a timeout instead of fixing
the lock order. A timeout converts a permanent hang into an intermittent failure — the retry
might deadlock again on the next attempt — whereas a total lock order removes the possibility
structurally.

**Interview:** "How do you prevent deadlock?" — break one of the four Coffman conditions; in
practice this almost always means eliminating circular wait via a consistent global lock order.

---

## 4.8.4 — The livelock harness

### What it demonstrates

Two threads, each trying to be polite by backing off when they detect contention, back off in
lockstep forever: both notice the other is "busy," both yield, both retry at the same moment,
both notice the other is busy again. No thread is ever blocked — every thread is fully runnable
and burning CPU — but no thread ever makes progress. This is livelock's defining contrast with
deadlock: **deadlock shows near-zero CPU** (the threads are `BLOCKED`, parked, doing nothing);
**livelock shows high CPU and zero throughput** (the threads are `RUNNABLE`, spinning, doing
work that accomplishes nothing).

### The runnable code

```java
package quizstakes.concurrency.harness;

import java.util.concurrent.atomic.AtomicBoolean;
import java.util.concurrent.TimeUnit;

/**
 * BROKEN: two settlement workers each try to reserve a shared resource
 * (here, exclusive access to run a settlement batch) and politely back off
 * whenever they see the other is "in use" -- in perfect lockstep, forever.
 */
public final class LivelockHarness {

    static final AtomicBoolean settlementBatchInUse = new AtomicBoolean(false);
    static volatile boolean stop = false;

    static void tryRunBatch(String workerName) throws InterruptedException {
        int attempts = 0;
        while (!stop) {
            attempts++;
            if (settlementBatchInUse.compareAndSet(false, true)) {
                try {
                    System.out.println(workerName + " running settlement batch (attempt " + attempts + ")");
                    return;
                } finally {
                    settlementBatchInUse.set(false);
                }
            } else {
                // Politely back off with a FIXED delay -- both workers wake at
                // the same instant and collide again.
                System.out.println(workerName + " sees batch in use, backing off (attempt " + attempts + ")");
                Thread.sleep(10);
            }
        }
    }

    public static void main(String[] args) throws InterruptedException {
        // Force both workers to observe "in use" simultaneously by having
        // a third party hold the flag briefly at the moment both start.
        settlementBatchInUse.set(true);

        Thread settlementIngest3 = new Thread(() -> {
            try {
                tryRunBatch("settlement-ingest-3");
            } catch (InterruptedException e) {
                Thread.currentThread().interrupt();
            }
        }, "settlement-ingest-3");

        Thread settlementIngest8 = new Thread(() -> {
            try {
                tryRunBatch("settlement-ingest-8");
            } catch (InterruptedException e) {
                Thread.currentThread().interrupt();
            }
        }, "settlement-ingest-8");

        settlementIngest3.start();
        settlementIngest8.start();

        TimeUnit.MILLISECONDS.sleep(20);
        settlementBatchInUse.set(false); // release the artificial hold

        // In the broken version below, both workers can end up perpetually
        // toggling the flag true/false in the same instant against each other
        // if their sleeps stay in phase -- demonstrated by forcing the same
        // fixed 10ms backoff and near-simultaneous starts.
        TimeUnit.SECONDS.sleep(3);
        stop = true;
        settlementIngest3.join();
        settlementIngest8.join();
    }
}
```

### What you actually observe when you run it

In the general case a fixed, identical backoff delay does not livelock every run — real
schedulers introduce enough jitter that two threads rarely stay in perfect lockstep for long on
a single-machine JVM demo. But under load, or with a shorter/synchronized backoff, or on a
system with few cores where the scheduler alternates the two threads with mechanical regularity,
the symptom is characteristic and reproducible: both threads print "backing off" lines
indefinitely, CPU usage for both threads sits high (order-of-magnitude: both near their fair
share of a core, spinning), and the "running settlement batch" success line never appears. This
is the operational tell used to distinguish livelock from deadlock in production: `jstack` shows
both threads `RUNNABLE`, not `BLOCKED`, and a CPU profile shows sustained activity with zero
forward progress in the metric that matters (settlement batches actually completed).

| Symptom | Deadlock | Livelock |
|---|---|---|
| Thread state (`jstack`) | `BLOCKED`, waiting on a monitor | `RUNNABLE`, spinning/retrying |
| CPU usage | Near zero for the stuck threads | High — often near 100% of a core each |
| Detected by `ThreadMXBean.findDeadlockedThreads()` | Yes | No — no lock cycle exists to find |
| Throughput | Zero, permanently | Zero, despite visible "work" |
| Typical cause | Circular wait on ordered locks | Symmetric backoff with no randomness |

**Pitfall:** assuming a `ThreadMXBean` deadlock watchdog (4.8.3) will also catch livelock. It will
not — there is no lock-ownership cycle to walk, because neither thread is ever `BLOCKED` on the
other's monitor. Livelock has to be diagnosed operationally: high CPU with flat or zero
throughput on the metric that should be increasing.

### The fix

```java
package quizstakes.concurrency.harness;

import java.util.concurrent.ThreadLocalRandom;
import java.util.concurrent.atomic.AtomicBoolean;

public final class LivelockHarnessFixed {

    static final AtomicBoolean settlementBatchInUse = new AtomicBoolean(false);

    static void tryRunBatch(String workerName) throws InterruptedException {
        int attempts = 0;
        int baseBackoffMillis = 5;
        while (true) {
            attempts++;
            if (settlementBatchInUse.compareAndSet(false, true)) {
                try {
                    System.out.println(workerName + " running settlement batch (attempt " + attempts + ")");
                    return;
                } finally {
                    settlementBatchInUse.set(false);
                }
            } else {
                // FIX: randomised, exponentially widening backoff breaks the
                // lockstep symmetry.
                int capMillis = Math.min(baseBackoffMillis * (1 << Math.min(attempts, 6)), 500);
                long jitterMillis = ThreadLocalRandom.current().nextLong(capMillis);
                Thread.sleep(jitterMillis);
            }
        }
    }
}
```

### Why the fix works

Livelock's defining condition is that both threads' retry decisions are correlated closely enough
in time that they keep colliding — a fixed backoff makes that correlation *stable*, because both
threads wake up after exactly the same delay every time. Replacing it with a **randomised**
backoff (and widening the range with each retry, the same idea as Ethernet's exponential backoff)
makes the two threads' wake times diverge after a small number of collisions with overwhelming
probability, so one of them ends up waking first, sees the flag clear, and wins the race — after
which progress resumes. This is the same class of fix as `[BUILD]` leaf 4.8.3's total lock order:
both replace a structural cause of non-progress (circular wait; perfectly correlated retries)
with a structural guarantee against it (an acyclic order; decorrelated timing), rather than
papering over a symptom.

> **Definition:** Livelock is a state where every thread remains runnable and actively executing,
> yet no thread makes forward progress, because each thread's action is a reaction to the others'
> that perpetually re-creates the same conflicting state — distinguished operationally from
> deadlock by high CPU and `RUNNABLE` thread states rather than `BLOCKED` ones.

**Interview:** "What's the difference between deadlock and livelock?" — deadlock: threads are
blocked, CPU is idle, no progress, detectable by walking the lock-ownership graph. Livelock:
threads are runnable and busy, CPU is high, no progress, not detectable by lock-graph analysis —
diagnosed by watching throughput stay flat while CPU stays high.

## Pitfalls

### Believing a `ThreadMXBean` watchdog covers all "stuck" symptoms

**Wrong**

```java
// "we have a deadlock watchdog running in production, we'd know if threads got stuck"
if (threadBean.findDeadlockedThreads() == null) {
    // assumed: no thread is stuck
}
```

**Right**

```java
// Monitor both signals: lock-cycle detection AND a throughput/CPU correlation check
if (threadBean.findDeadlockedThreads() != null) {
    logDeadlockCycle();
} else if (cpuUsageHigh() && throughputFlat()) {
    logSuspectedLivelock();
}
```

**Why people believe it:** "stuck" is treated as one failure mode in most runbooks, and
`findDeadlockedThreads()` is the well-known tool for it, so it is easy to assume it is the whole
answer. It only covers cycles in the lock-ownership graph — livelock never forms one.

### Fixing a deadlock by adding a lock timeout instead of a lock order

**Wrong**

```java
// "just add a timeout so it can't hang forever"
if (lockA.tryLock(100, TimeUnit.MILLISECONDS)) {
    if (lockB.tryLock(100, TimeUnit.MILLISECONDS)) {
        // ... still deadlocks occasionally, now as an intermittent timeout instead
    }
}
```

**Right**

```java
// Impose a total order and always acquire in that order (see DeadlockHarnessFixed)
```

**Why people believe it:** a timeout does make the *symptom* — an infinite hang — go away, which
looks like a fix under time pressure. It converts a deterministic, always-reproducible deadlock
into an intermittent one that resurfaces under load, without addressing the circular-wait
condition that causes it.

## Cheat sheet

| Aspect | Deadlock | Livelock |
|---|---|---|
| Thread state | `BLOCKED` | `RUNNABLE` |
| CPU | ~0 | high |
| Detected by `findDeadlockedThreads()` | yes | no |
| Root cause | circular wait on ordered locks | symmetric, correlated retry/backoff |
| Structural fix | total lock order | randomised/exponential backoff |
| Diagnostic tool | `jstack`, `ThreadMXBean` | CPU profile + throughput metric, side by side |

## Self-test

**Q1.** What are the four Coffman conditions, and which one does a total lock order break?

<details><summary>Answer</summary>

Mutual exclusion, hold-and-wait, no preemption, and circular wait. A total lock order breaks
circular wait: if every thread acquires locks in the same global order, no cycle of "waiting for"
relationships can ever form.

</details>

**Q2.** Why does `ThreadMXBean.findDeadlockedThreads()` fail to detect a livelock?

<details><summary>Answer</summary>

It works by walking the JVM's lock-ownership graph looking for a cycle of threads each waiting
on a lock held by the next. Livelocked threads are never `BLOCKED` waiting on a lock — they are
`RUNNABLE`, repeatedly acquiring and releasing (or failing a CAS on) a resource — so there is no
ownership cycle for the graph walk to find.

</details>

**Q3.** In the deadlock harness, why does adding `Thread.sleep(50)` between the two `synchronized`
blocks make the deadlock reproduce reliably instead of being a rare race?

<details><summary>Answer</summary>

Without the sleep, one thread might acquire both locks and finish before the other thread even
starts, so the race window in which both threads hold one lock and want the other's is narrow
and easy to miss in a short-lived demo. The sleep widens that window so both threads are
virtually guaranteed to be holding their first lock and requesting their second at the same time.

</details>

**Q4.** Why is a fixed backoff delay the root cause of the livelock harness, rather than the CAS
loop itself?

<details><summary>Answer</summary>

The CAS loop itself is correct — it retries only when the resource is genuinely unavailable. The
problem is that both threads compute the exact same delay before retrying, so their retry
attempts stay correlated in time indefinitely: if they collide once, a fixed delay guarantees
they collide again on the very next attempt, forever.

</details>

**Q5.** Why does randomising the backoff fix the livelock rather than merely making it less
likely?

<details><summary>Answer</summary>

It does not make livelock structurally impossible the way a total lock order makes deadlock
impossible — two threads could still, by chance, pick colliding delays repeatedly. But because
the delay is drawn independently and (with exponential widening) from a growing range, the
probability of continued collision shrinks geometrically with each retry, so in practice
progress resumes almost immediately and the probability of indefinite livelock becomes
vanishingly small rather than structurally guaranteed at zero.

</details>

**Q6.** A production dashboard shows a settlement worker pool at 100% CPU with throughput at
zero. What is the first thing to check, and why not `jstack` for deadlock first?

<details><summary>Answer</summary>

Check thread state distribution first (e.g. via `jstack` or `jcmd Thread.print`) — if threads are
`RUNNABLE` rather than `BLOCKED`, high CPU with zero throughput is the livelock signature, not
deadlock, and a deadlock-focused watchdog check would report nothing found even though the
system is genuinely stuck.

</details>

---

**Leaves covered:** 4.8.3–4.8.4 (2 leaves)
**Leaves deferred:** none
**Diagrams included:** none
**Target version:** Java 21 LTS
**Lines:** 565
