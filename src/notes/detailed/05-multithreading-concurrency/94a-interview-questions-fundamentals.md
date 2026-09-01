# 05 Multithreading and Concurrency — Interview questions: fundamentals — INTERVIEW (§5.1, questions 5.1.1–5.1.17)

**Target version: Java 21 LTS.** | **Part 5 of 5** | [Index](00-index.md)
Previous: [Part 4 interview wrap-up](93-interview-build-it.md) · Next: [Interview questions: fundamentals II](94a2-interview-questions-fundamentals-ii.md)

---

### 5.1.1 Process versus thread, and what exactly is shared

A process is an OS-level unit of isolation: its own virtual address space, its own file descriptor table, its own heap. A thread is a unit of scheduling *inside* a process. All threads in one JVM process share the heap — every object, every static field — and share open file descriptors and sockets. What is **not** shared is each thread's stack (its local variables and call frames), its program counter, and its set of CPU registers at any instant. That is why two threads settling the same `WithdrawalTransaction` can both see the same `FundsLedger` instance and race on it, while a bug in one thread's stack-local `StakeSplit` computation cannot corrupt another thread's copy.

**Follow-up:** Why is inter-thread communication cheaper than inter-process communication? Because sharing memory needs no copy or kernel round-trip — a write to a shared `AtomicLong` counter is visible to another thread through cache-coherence traffic, whereas two processes need a pipe, socket, or shared-memory segment negotiated through the OS.

### 5.1.2 `start()` versus `run()`. What happens if you call `start()` twice

`run()` is a plain method call — invoking `t.run()` executes the code on the *calling* thread, no new thread is created, and nothing happens concurrently. `start()` asks the OS to create a new native thread, registers the JVM's `Thread` object as its entry point, and that new thread later calls `run()` on itself. Internally `Thread.start()` flips `threadStatus` from `NEW` (0) to a live state via native `start0()`, and it guards against a second call: the field is inspected before the native call fires. Calling `start()` a second time on the same `Thread` object throws.

**Pitfall:** The wrong belief is that the second `start()` throws `IllegalStateException` because "the thread is in the wrong state" — a generic-sounding guess. It actually throws **`IllegalThreadStateException`**, a `RuntimeException` subtype defined specifically for this case since JDK 1.0. The fix, if you need to re-run logic, is to construct a fresh `Thread` — a `Thread` object is single-use.

**Follow-up:** Can you call `run()` after `start()` on the same object? Yes, but it runs synchronously on your thread and races with whatever the started thread is doing — almost always a bug, not a feature.

### 5.1.3 Why is `Runnable` preferred to extending `Thread`

Extending `Thread` burns your only superclass slot — Java has no multiple inheritance, so a class that must already extend something (a Spring `@Component` base, say) cannot also extend `Thread`. Implementing `Runnable` keeps the task as pure behavior, decoupled from "is a thread": the same `Runnable` that settles a batch of `WithdrawalTransaction`s can be handed to `new Thread(r)`, to an `ExecutorService`, or run inline in a test, none of which is possible if the logic is welded to a `Thread` subclass. It also matches the Single Responsibility Principle — `Thread` is a scheduling handle, not a place for business logic.

**Follow-up:** Is there ever a legitimate reason to extend `Thread`? Rarely — only when you are building infrastructure that overrides thread lifecycle methods themselves (e.g. a custom `ThreadFactory`'s internal thread subclass tracking JFR events), never for application code.

### 5.1.4 Walk the six `Thread.State` values and the transitions between them

`Thread.State` has exactly six values: `NEW`, `RUNNABLE`, `BLOCKED`, `WAITING`, `TIMED_WAITING`, `TERMINATED`. A thread starts `NEW` (constructed, not started), moves to `RUNNABLE` on `start()` — meaning eligible to run, whether or not actually executing on a core right now. It moves to `BLOCKED` only when contending for a `synchronized` monitor another thread holds — say, two threads both wanting the lock on the same `Reservation` object. It moves to `WAITING` on `Object.wait()` with no timeout, `Thread.join()` with no timeout, or `LockSupport.park()` — no timeout, no bound. `TIMED_WAITING` is the same set of calls with a timeout argument, plus `Thread.sleep(millis)`. `TERMINATED` is entered once `run()` returns or throws, and it is a one-way door — a terminated `Thread` object cannot be restarted.

**Insight:** `RUNNABLE` in the JVM's terminology conflates two OS-level states — actually running on a core, and ready-but-waiting for the scheduler to grant a timeslice. The JVM does not distinguish them because the OS scheduler, not the JVM, owns that decision.

**Follow-up:** Which states can transition directly to `TERMINATED`? All of `RUNNABLE`, `BLOCKED`, `WAITING`, and `TIMED_WAITING` can — an uncaught exception or a normal return can happen from any point in `run()`, including while notionally blocked if the block is interrupted and the handler exits.

### 5.1.5 Why does a thread blocked on a socket read show `RUNNABLE`

Because `Thread.State` only models JVM-level concurrency constructs — monitor contention, `wait`/`join`/`park`. A blocking read on a `CardPayments` socket call to the PSP is a native OS system call; the JVM has handed control to the kernel and has no visibility into whether the kernel scheduler has parked that OS thread waiting on the NIC. From the JVM's point of view the Java thread is still "eligible to run" — it never called a JVM-level blocking primitive — so `getState()` reports `RUNNABLE` even though, at the OS level, `top -H` or a `jstack` dump would show it asleep in `read()`.

**Pitfall:** Debugging a thread pool "stuck" on the PSP at p99 11 seconds by staring at `jstack`'s reported state and seeing `RUNNABLE` on all of them, concluding "they're all busy" — when in fact they are all parked in the kernel waiting on a slow socket. Read the stack trace frames (`socketRead0`), not just the state label.

**Follow-up:** How would you actually confirm 40 threads are stuck in the PSP call and not doing CPU work? Take a `jstack` dump and read the top frames for native I/O methods, or correlate with `top -H` CPU-per-thread — a thread truly burning CPU shows nonzero CPU time, a blocked-on-socket thread does not.

### 5.1.6 What does `Thread.sleep` release? What does `Object.wait` release?

`Thread.sleep(millis)` releases nothing — if the sleeping thread holds a lock (say, the monitor on a `Bonus` object while recomputing its clawback), it keeps holding that lock for the entire sleep, blocking every other thread that wants it. `Object.wait()` is the opposite: it **must** be called while holding the object's monitor, and calling it atomically releases that monitor so another thread can acquire it, do work, and call `notify`/`notifyAll`. This is the whole point of `wait` — it exists precisely to let go of the lock while waiting for a condition, which `sleep` structurally cannot do.

**Follow-up:** What exception does `wait()` throw if called without holding the monitor? `IllegalMonitorStateException`, at runtime, unconditionally — there is no compile-time check.

### 5.1.7 Why were `Thread.stop`/`suspend`/`resume` removed

`Thread.stop()` killed a thread at an arbitrary bytecode instruction by throwing a `ThreadDeath` asynchronously at whatever point it happened to be executing — including mid-update of a `FundsLedger` entry, leaving `CLIENT_CASH_RESERVED` decremented but `CLIENT_CASH_AVAILABLE` not yet incremented, a torn invariant with no way to detect or repair it. `suspend()`/`resume()` had a matching problem: `suspend()` froze a thread without releasing any locks it held, so if that thread held the lock protecting the reservation counter, every other thread wanting that lock deadlocked forever, since the only thread that could call `resume()` might itself need that same lock. Both were deprecated since Java 1.2 and finally **removed** — not merely deprecated — in **Java 20**; calling them now throws `UnsupportedOperationException`.

**Follow-up:** What replaced them conceptually? Cooperative cancellation: the target thread checks a flag or its own interrupt status and exits `run()` voluntarily, at a safe point of its own choosing.

### 5.1.8 How do you stop a thread, properly

There is no forcible, safe way to stop another thread from outside — Java deliberately removed that button. The correct pattern is cooperative: call `interrupt()` on the target, and have the target's loop check `Thread.currentThread().isInterrupted()` (or let a blocking call like `queue.take()` throw `InterruptedException`) and exit `run()` on its own terms, releasing any locks and flushing any in-flight state cleanly — for example finishing the current `WithdrawalTransaction` write before returning rather than abandoning it mid-flush. A `volatile boolean running` flag works too for CPU-bound loops with no blocking calls, but `interrupt()` is preferred because it also unblocks a thread parked in `wait`/`sleep`/`join`/blocking I/O that respects interruption.

```java
final class WithdrawalRunner implements Runnable {
    private final BlockingQueue<WithdrawalTransaction> queue;

    WithdrawalRunner(BlockingQueue<WithdrawalTransaction> queue) {
        this.queue = queue;
    }

    @Override
    public void run() {
        while (!Thread.currentThread().isInterrupted()) {
            try {
                WithdrawalTransaction tx = queue.take();
                settle(tx);
            } catch (InterruptedException e) {
                Thread.currentThread().interrupt();
                return;
            }
        }
    }

    private void settle(WithdrawalTransaction tx) {
        // apply to FundsLedger, then mark tx settled
    }
}
```

**Follow-up:** Why re-interrupt inside the `catch` before returning? Because catching `InterruptedException` clears the interrupt flag; if this method's caller — say a pooled worker wrapper — also checks the flag to decide whether to log a clean shutdown versus an error, losing that flag hides the signal.

### 5.1.9 What are the two legal responses to `InterruptedException`

First: propagate it — declare `throws InterruptedException` and let it bubble, which is correct when the calling method has no meaningful recovery of its own, such as a private helper called from `run()`. Second: catch it, restore the interrupt status with `Thread.currentThread().interrupt()`, and then return or otherwise wind down — used at a boundary where you cannot declare a checked exception, such as `Runnable.run()`, which has no `throws` clause. What is **not** legal, in the sense of being a correctness bug, is swallowing it silently — catching it and doing nothing loses the cancellation signal permanently, and the thread will run to completion on a stake-settlement job the caller already gave up waiting for.

**Pitfall:** `catch (InterruptedException e) {}` is one of the most common review-flagged bugs — the thread looks fine, keeps running, and only fails later in a confusing way (e.g. a shutdown hook that hangs because a worker never noticed it was told to stop).

### 5.1.10 What is the difference between `isInterrupted()` and `Thread.interrupted()`

`isInterrupted()` is an instance method, callable on any `Thread` reference, and it does **not** clear the flag — you can call it repeatedly and get the same answer until something else clears it. `Thread.interrupted()` is a **static** method that always operates on the *currently executing* thread, and as a side effect it **clears** the interrupt flag, returning what the flag was before clearing. This asymmetry exists because `interrupted()` is meant for a loop to consume the signal exactly once per interruption, while `isInterrupted()` is for one thread inspecting another's state without side effects.

**Pitfall:** Calling `someOtherThread.interrupted()` compiles — it is a static method, so the receiver expression is evaluated then discarded — but it always checks and clears the *calling* thread's flag, not `someOtherThread`'s. This is a genuine trap; IDEs warn on it, but it slips into hand-rolled cancellation loops.

### 5.1.11 Daemon versus non-daemon threads

The JVM stays alive as long as at least one non-daemon thread is running; it exits the moment every remaining thread is a daemon, regardless of what those daemon threads are mid-doing — there is no graceful shutdown, no `finally` block guarantee. Daemon threads are for background work whose loss on exit is acceptable: a metrics-flushing thread for the stake-reservation counter, a periodic cache-warming thread. Anything that must complete — flushing a `PaymentRun` file to the banking partner, finishing writes to the ledger's hot window — must run on a non-daemon thread, or on a daemon thread the shutdown sequence explicitly `join()`s before the JVM is allowed to exit.

**Follow-up:** How do you mark a thread daemon, and when must you do it? `thread.setDaemon(true)`, and it must be called **before** `start()` — `IllegalThreadStateException` if called after the thread has already started, mirroring the same exception as a double `start()`.

### 5.1.12 What does `Thread.yield()` guarantee? (Nothing.)

Nothing, by specification. `yield()` is a hint to the scheduler that the current thread is willing to give up its current timeslice to another runnable thread of the same or higher priority — but the JVM spec explicitly leaves the scheduler free to ignore it entirely, and on many modern OS schedulers it effectively is a no-op or immediately re-selects the same thread. It provides **no** memory visibility guarantee (unlike `synchronized` or `volatile`) and no ordering guarantee. Code that relies on `yield()` to "let the other thread catch up" — for instance, hoping a settlement worker gets a turn before a reservation worker floods the queue — is relying on undefined scheduler behavior and will fail unpredictably across JVMs and OS versions.

**Insight:** `yield()` survives in the API mostly for spin-loop back-off in low-level code (e.g. inside `StampedLock`'s optimistic-read retry) where "maybe let someone else go" costs nothing if ignored, not as an application-level scheduling tool.

### 5.1.13 What are the *two* guarantees of `synchronized`

Mutual exclusion — only one thread may hold a given monitor at a time, so two threads calling `reserveStake` on the same `FundsLedger` instance cannot interleave their reads and writes of the wallet's four buckets. And visibility — entering a `synchronized` block establishes a happens-before edge with the *previous* release of the same monitor by any thread, so everything that thread wrote before releasing is guaranteed visible to the thread that next acquires it, even without `volatile` on the individual fields. Candidates who name only mutual exclusion miss half the answer and cannot then explain why `synchronized` fixes visibility bugs that look like pure races.

**Follow-up:** Does `synchronized` guarantee fairness — that the longest-waiting thread gets the lock next? No, the JVM's intrinsic lock makes no fairness guarantee; a newly arriving thread can barge ahead of one that has waited longer. `ReentrantLock(true)` is the tool when fairness matters.

### 5.1.14 What is a monitor, and where does it live

A monitor is the pairing of a mutual-exclusion lock with a wait-set, one per object, used by `synchronized` and by `wait`/`notify`. Conceptually every Java object has an associated monitor; in the JDK's actual implementation the monitor is not always a heap-resident, fully materialized structure — for an uncontended lock the JVM uses lightweight, stack-based locking encoded directly in the object header's mark word, and only "inflates" to a full, heavyweight `ObjectMonitor` (a native C++ structure, historically malloc'd, with JDK 25's compact-headers work moving toward a side-table) when there is real contention. So "where does it live" has a version-scoped answer: logically it is attached to the object; physically, cheap paths avoid allocating anything until contention forces inflation.

**Follow-up:** Can you synchronize on a primitive? No — `synchronized` requires an object reference; primitives have no header to hold lock state, so you must synchronize on a wrapper or a dedicated lock object instead.

### 5.1.15 Is `synchronized` reentrant, and why does it have to be

Yes — a thread already holding a monitor can re-acquire it on a nested call without blocking on itself; the JVM tracks a recursion count on the lock record and only fully releases when the count returns to zero. It has to be reentrant because Java methods routinely call other `synchronized` methods on the same object, including through inheritance: a `synchronized` `settleStake` method might call a `synchronized` `applyLedgerEntry` method on the same `FundsLedger` instance. Without reentrancy that second acquisition would block forever — the thread would be waiting on a lock it itself already holds, a self-deadlock baked into ordinary method composition.

**Follow-up:** Is `ReentrantLock` reentrant for the same reason? Yes, by name and by design — it maintains its own hold count exactly to match `synchronized`'s behavior, which is why it was a drop-in semantic upgrade rather than a different locking model.

### 5.1.16 Do a synchronized instance method and a synchronized static method exclude each other?

No — they lock on two different monitors and never contend with each other, regardless of how many times either is called. A `synchronized` instance method locks on `this`, the specific object instance (e.g. one particular `Reservation`). A `synchronized` static method locks on the `Class` object for that class (e.g. `Reservation.class`), which is a single, JVM-wide object shared across every instance. Two threads, one inside a synchronized instance method on `reservationA` and one inside a synchronized static method of the same class, run fully concurrently — there is no shared lock between them at all.

**Pitfall:** Assuming "it's all synchronized on the same class, so it's safe" when mixing static and instance synchronized methods that touch a shared static field — the instance-level lock provides zero protection for that static field, because the two lock objects are different.

### 5.1.17 What can go wrong locking on a `String` literal or a boxed `Integer`

String literals are interned and boxed `Integer`s in the range âˆ’128 to 127 are cached by `Integer.valueOf`, so `synchronized("PAYMENT_RUN_LOCK")` or `synchronized(clientCount)` where `clientCount` is a small boxed `Integer` may silently share the *identical* object with completely unrelated code elsewhere in the JVM — including third-party libraries — that happens to use the same literal or the same small integer value. That unrelated code becomes an invisible co-contender on your lock, causing spurious blocking or, worse, a deadlock with code you have no control over and cannot see in a stack trace without knowing to look for it.

**Pitfall:** The fix is to synchronize on a `private final Object` created specifically as a lock, dedicated and never exposed — e.g. `private final Object paymentRunLock = new Object();` — never on interned literals, cached boxed primitives, or exposed mutable state like a `String` field that another thread could reassign, changing what monitor `synchronized` locks on mid-flight.

---

**Leaves covered:** 5.1.1–5.1.17 (17 questions)
**Leaves deferred:** none
**Diagrams included:** none
**Target version:** Java 21 LTS
**Lines:** 145
