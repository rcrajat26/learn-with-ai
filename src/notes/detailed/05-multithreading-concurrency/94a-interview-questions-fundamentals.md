# 05 Multithreading and Concurrency — Interview questions: fundamentals — INTERVIEW (§5.1, questions 5.1.1–5.1.17)

**Target version: Java 21 LTS.** | **Part 5 of 5** | [Index](00-index.md)
Previous: [Part 4 interview wrap-up](93-interview-build-it.md) · Next: [Interview questions: fundamentals II](94a2-interview-questions-fundamentals-ii.md)

---

### 5.1.1 Process versus thread, and what exactly is shared

A process is an OS-level unit of isolation: its own virtual address space, its own file descriptor table, its own heap, its own security context, torn down as a unit by the kernel on exit.
A thread is a unit of scheduling *inside* a process, and every thread the JVM creates shares that process's single heap — every object, every static field, every open file descriptor and socket — with every other thread in the same JVM.
What is **not** shared is each thread's own call stack (its local variables and stack frames), its own program counter, and its own snapshot of CPU registers at any instant; those live in per-thread kernel structures, not on the shared heap.
Concretely: two worker threads both calling `fundsLedger.reserveStake(clientId, amount)` are reading and writing the exact same `CLIENT_CASH_AVAILABLE` and `CLIENT_CASH_RESERVED` ledger positions on the one shared `FundsLedger` instance.
That shared mutable state is precisely why the reservation path needs coordination at 1,200 reservations/sec peak, whereas a bug in one thread's stack-local `StakeSplit` computation for a single stake cannot leak into another thread's in-flight computation of a different stake.

**Follow-up:** Why is inter-thread communication cheaper than inter-process communication?
Sharing memory needs no copy and no kernel round trip — a write to a shared `AtomicLong` becomes visible to another thread purely through cache-coherence traffic between cores, whereas two processes need a pipe, socket, or shared-memory segment explicitly negotiated through the OS, each hop paying a context switch and often an actual data copy.

This is also why threads are the cheaper concurrency unit for a service handling 55k peak concurrent sessions: spinning up one JVM process per session would multiply the fixed cost of a full address space and heap by 55,000, whereas 55,000 platform threads (or, on Java 21, orders of magnitude more virtual threads) share one heap and one set of loaded classes.

**Interview:** When asked to justify why a request-handling tier uses threads rather than worker processes, the one-line answer is shared-heap concurrency amortizes fixed per-unit memory cost across every concurrent request, at the price of needing explicit coordination on anything mutable that crosses threads.

A related trap: some candidates claim processes are "always" safer because of isolation, without qualifying that the isolation is exactly what makes cross-process coordination expensive in the first place — safety and cost are the same tradeoff viewed from two sides, not two independent properties you get to pick freely.

**Pitfall:** Interviewers sometimes probe whether "shared heap" means every thread sees every object equally cheaply — it does not, at the hardware level. Threads pinned to different CPU sockets pay a real NUMA penalty reading a cache line another socket's core last wrote, so "shared heap" is a correctness statement about visibility (given proper synchronization), not a performance statement that all cross-thread reads cost the same regardless of topology.

**Follow-up:** Do threads within one process share environment variables and the working directory?
Yes — both are process-scoped, inherited identically by every thread within the JVM, unlike per-thread state such as the interrupt flag, the thread-local variable map, or the call stack, which are the genuinely per-thread pieces of state.

**Follow-up:** Is `ThreadLocal` state an exception to "threads share the heap"?
Not really an exception, just a controlled per-thread partition within it — each `Thread` object holds its own internal map from `ThreadLocal` instance to value, so the *storage* still lives on the shared heap inside the `Thread` object itself, but each thread only ever reads its own entry, which is why `ThreadLocal` is the standard tool for giving each thread its own private, non-shared copy of otherwise-shared-looking state.

### 5.1.2 `start()` versus `run()`. What happens if you call `start()` twice

`run()` is an ordinary method call: invoking `t.run()` directly executes that code on the *calling* thread, synchronously, with no new thread created and nothing happening concurrently — indistinguishable from calling any other method on the object.
`start()` is the one that actually asks the OS to create a new native thread and registers the `Thread` object as that new thread's entry point; the new native thread later calls `run()` on itself, on its own freshly allocated stack, scheduled independently by the OS.
Internally, `Thread.start()` checks and flips an internal `threadStatus` field from `NEW` to a live value before invoking a native `start0()`, and that same check is what protects against being called twice.
A `Thread` object represents a single native thread's lifecycle from birth to death, not a reusable task slot you can rewind and fire again.

**Pitfall:** The instinctive wrong answer is that a second `start()` throws `IllegalStateException`, reasoning by analogy with other JDK APIs that guard state transitions the same way.
It actually throws **`IllegalThreadStateException`**, a distinct `RuntimeException` subtype that has existed specifically for this case since JDK 1.0 — not `java.lang.IllegalStateException`, which is a different, more general type.
If your interviewer asks "what exception, exactly," naming the generic one is a tell that you have not actually hit this in practice.
The fix when you need the same logic to run again is to construct a brand-new `Thread` wrapping the same, reusable `Runnable` — the task is reusable, the thread handle is not.

**Follow-up:** Can you call `run()` directly right after `start()` on the same object?
Yes, nothing stops you at compile time, but it runs synchronously on your own thread and now races with whatever the started thread is independently doing on its own stack — almost always an accidental bug, and exactly the pattern static analyzers flag as "call to `run()` instead of `start()`."

**Interview:** This question is often the opening warm-up of a concurrency round precisely because the wrong exception type is such a clean tell of whether the candidate has actually debugged thread-lifecycle code, versus only having read about it; state the exception name confidently and move straight to the reusable-`Runnable` fix.

**Follow-up:** Does calling `start()` allocate the native OS thread immediately and synchronously, or is it asynchronous from the caller's point of view?
The call to `start0()` blocks until the native thread creation call itself returns, but nothing guarantees the new thread has actually begun executing `run()` by the time `start()` returns — the caller only knows creation was requested, not that execution has begun.

**Pitfall:** Code that assumes a freshly `start()`-ed worker has already begun processing — for example immediately submitting the first `WithdrawalTransaction` to a queue that worker is supposed to drain and expecting instant pickup — is relying on scheduling timing the JLS never promised; `Thread.start()` happens-before the started thread's first action, but that says nothing about *when* that first action executes relative to the caller's next line of code.

**Follow-up:** Can `start()` itself throw an exception unrelated to double-start?
Yes — `OutOfMemoryError` is a documented possibility if the OS cannot allocate a new native thread stack, which is exactly why unbounded thread creation (spawning a fresh `Thread` per incoming request at 55k peak concurrent sessions with no pool) is a genuine production risk, not merely a style concern.

**Follow-up:** Does the constructor `Thread(Runnable target)` invoke `target.run()` itself?
No — the constructor only stores the `Runnable` reference; nothing executes until `start()` is later called, which then invokes `run()` on the new thread, and `run()` in turn dispatches to the stored `target.run()` if one was supplied.

**Follow-up:** What is the default name assigned to a `Thread` if none is given?
`"Thread-" + n`, where `n` is a JVM-wide, monotonically increasing counter shared across every unnamed `Thread` ever constructed in that JVM — which is precisely why production code should always supply an explicit, meaningful name (e.g. via a custom `ThreadFactory`) so a `jstack` dump reads `withdrawal-settler-3` rather than an uninformative `Thread-47`.

### 5.1.3 Why is `Runnable` preferred to extending `Thread`

Extending `Thread` spends your one available superclass slot — Java has no multiple inheritance of implementation, so a class that must already extend something else (a shared abstract batch-job base class, a framework component base) simply cannot also extend `Thread`.
Implementing `Runnable` instead keeps the task as pure, decoupled behavior: the same `Runnable` that settles a batch of `WithdrawalTransaction`s can be handed to `new Thread(r)` for a one-off background thread, submitted to a pooled `ExecutorService` for the production path, or invoked directly and synchronously inside a unit test with no thread involved at all.
None of that is available once the logic is welded permanently into a `Thread` subclass.
It is also a cleaner separation of responsibility: `Thread` is a scheduling and lifecycle handle (state, interrupt flag, daemon-ness, priority); `Runnable` is the actual business logic, such as applying one `StakeSplit` to the ledger, and testing that logic should never need to drag thread-lifecycle machinery along with it.

**Follow-up:** Is there ever a legitimate reason to extend `Thread`?
Rarely — mostly when building low-level infrastructure that itself must override lifecycle behavior, such as a `ThreadFactory`'s own internal thread subclass tagging each created thread with a name or attaching tracing context at construction; ordinary application task code should essentially never extend `Thread`.

**Pitfall:** A subtler reason to avoid extending `Thread` is that overriding `run()` in a subclass silently discards whatever `Runnable` was passed to the two-argument `Thread(Runnable, String)` constructor — the subclass's `run()` wins, and a caller who supplied a task expecting it to execute is left debugging why nothing happened.

**Interview:** If pressed for a one-sentence rule: "favor composition (`Runnable`) over inheritance (`extends Thread`)" — the same general-purpose OOP principle applied specifically to threading, which is usually the framing the interviewer is fishing for.

**Follow-up:** Is `Callable<V>` a better fit than `Runnable` for settling a stake and reporting back a result?
Yes whenever the task needs to return a value or throw a checked exception — `Runnable.run()` returns `void` and cannot declare checked exceptions, while `Callable<V>.call()` can return the settled `StakeSplit` and can throw, which is exactly why `ExecutorService.submit(Callable<V>)` exists as the value-returning counterpart to `execute(Runnable)`.

**Interview:** A candidate who reaches for `Runnable` reflexively without ever mentioning `Callable` is missing half of the API surface interviewers expect familiarity with — naming both, and the specific criterion (return value or checked exception) for choosing between them, reads as fluency rather than memorization.

**Follow-up:** Can a `Runnable` be adapted into a `Callable` and vice versa without rewriting the logic?
Yes — `Executors.callable(Runnable, V result)` wraps a `Runnable` into a `Callable<V>` that returns the given fixed result on success, and any `Callable` can be wrapped as a `Runnable` by discarding its return value inside a lambda, so the two are freely interconvertible glue rather than fundamentally incompatible shapes.

### 5.1.4 Walk the six `Thread.State` values and the transitions between them

`Thread.State` has exactly six values: `NEW`, `RUNNABLE`, `BLOCKED`, `WAITING`, `TIMED_WAITING`, `TERMINATED`.
A thread begins `NEW` — constructed, `start()` not yet called, no native thread exists yet.
`start()` moves it to `RUNNABLE`, meaning eligible to run, whether or not it is actually executing on a physical core at this exact instant — the OS scheduler alone decides which `RUNNABLE` thread gets the next timeslice.
It moves to `BLOCKED` only while contending for a `synchronized` monitor another thread currently holds, for example two threads both wanting the intrinsic lock on the same `Reservation` object while one is settling it and the other trying to void it.
It moves to `WAITING` on an untimed `Object.wait()`, an untimed `Thread.join()`, or an untimed `LockSupport.park()` — unbounded, released only by an external signal such as `notify`, the joined thread terminating, or a matching `unpark`.
`TIMED_WAITING` covers the same family of calls given an explicit deadline or duration, plus a plain `Thread.sleep(millis)`.
`TERMINATED` is entered once `run()` returns normally or an uncaught exception propagates out of it, and it is a one-way door: a terminated `Thread` object's state never changes again, and calling `start()` on it now throws the same `IllegalThreadStateException` from 5.1.2.

**Insight:** `RUNNABLE` quietly conflates two different OS-level realities — actually executing on a core right now, versus merely ready and waiting in the scheduler's run queue for the next timeslice.
The JVM does not distinguish the two because that decision belongs entirely to the OS scheduler, which the JVM has no visibility into.

**Follow-up:** Which states can transition directly to `TERMINATED`?
All of `RUNNABLE`, `BLOCKED`, `WAITING`, and `TIMED_WAITING` can — a normal return or an uncaught exception can occur from any point inside `run()`, including from inside a blocking call if it is interrupted and the handler chooses to exit rather than retry.

**Interview:** Interviewers often follow this with "draw the transition diagram from memory" — the trick worth stating out loud is that there is no arrow from `NEW` directly to any state but `RUNNABLE`, and no arrow leaving `TERMINATED` at all, which is easy to forget under pressure and easy to get right if you say it as a rule rather than trying to redraw six boxes from scratch.

**Pitfall:** Confusing `BLOCKED` with `WAITING`/`TIMED_WAITING` is common — `BLOCKED` is specifically monitor contention on a `synchronized` entry, while `WAITING`/`TIMED_WAITING` cover `wait`, `join`, and `park`; a thread contending for a `ReentrantLock.lock()` reports neither `BLOCKED` nor `WAITING` in the `Thread.State` enum — it reports `WAITING`/`TIMED_WAITING` because `ReentrantLock` parks via `LockSupport`, not via monitor entry, a detail worth naming explicitly since it trips people who assume all lock contention shows `BLOCKED`.

`[VERSION-TRAP]` On Java 21, a **virtual thread** blocked on a monitor via `synchronized` does not show a distinct virtual-thread-specific state in `Thread.State` — it still reports `BLOCKED` — but critically it also pins its carrier platform thread for the duration, a Java-21-specific cost that disappears once JEP 491 lands in Java 24 and virtual threads can unmount from their carrier while blocked on a monitor.

**Follow-up:** Does `NEW` correspond to anything visible in a thread dump?
No — a `Thread` object that has been constructed but never `start()`-ed has no corresponding native OS thread at all, so it never appears in `jstack` output, which only enumerates threads the OS actually schedules.

**Follow-up:** Can a thread's `Thread.State` change between two consecutive `getState()` calls made microseconds apart from another thread?
Yes, and this is expected, not a bug — `getState()` is a point-in-time snapshot with no atomicity guarantee relative to the target thread's own execution, so code that branches on a previously observed state without re-checking it is reading stale information by the time it acts on it.

### 5.1.5 Why does a thread blocked on a socket read show `RUNNABLE`

`Thread.State` only models JVM-level concurrency constructs — monitor contention, `wait`/`join`/`park`.
A blocking read on a socket to the card PSP (p50 240 ms, p99 11 s at authorise) is a native OS system call; the JVM hands control to the kernel and has no visibility into whether the kernel has parked that OS thread waiting on the network.
From the JVM's point of view the Java thread never invoked a JVM-recognized blocking primitive at all — it is technically still "eligible to run" — so `getState()` faithfully reports `RUNNABLE`, even though at the OS level the thread is genuinely asleep inside `read()` and consuming zero CPU.

**Pitfall:** Debugging a pool that looks "stuck" waiting on the PSP by taking a `jstack` dump, seeing every worker report `RUNNABLE`, and concluding "they're all doing CPU work, so this must be a compute problem" — when in fact every one of them is parked in the kernel on a slow socket.
The fix is to read the stack trace's top frames, not the state label: `jstack` still shows a native I/O method such as `socketRead0` at the top of a thread's frame even while its reported state is `RUNNABLE`, which is the actual tell.

**Follow-up:** How would you confirm 40 pooled threads are genuinely stuck in the PSP call rather than burning CPU?
Read the `jstack` frames for native I/O methods, or correlate with per-thread CPU time from `top -H` or a JFR thread-CPU-load event — a thread doing real work accumulates CPU time even while `RUNNABLE`; a thread blocked on a socket does not, despite reporting the identical state.

This same blind spot is one of the arguments for virtual threads on Java 21: pinning a pool of platform threads to slow PSP calls at p99 11 seconds wastes OS threads that could otherwise be doing useful scheduling elsewhere, while a virtual thread parked on the same blocking call releases its carrier platform thread back to the pool, at the cost of `synchronized` blocks around such calls still pinning the carrier on Java 21 (fixed by JEP 491 in Java 24).

**Interview:** If asked to explain the practical impact in one line: a fixed-size pool of 200 platform threads all blocked on the PSP at p99 caps you at 200 concurrent authorisations regardless of how much spare CPU sits idle, while virtual threads let the same workload scale toward thousands of concurrent, mostly-parked authorisations bounded by memory rather than OS thread count.

**Follow-up:** Would increasing the platform thread pool size to 2,000 solve the same problem without virtual threads?
Partially, at a real cost — each platform thread reserves a fixed-size native stack (commonly around 1 MB by default), so 2,000 of them reserve roughly 2 GB of address space up front just for stacks, whereas virtual thread stacks are small and grow on the Java heap, which is the actual scaling argument, not merely "virtual threads are faster."

### 5.1.6 What does `Thread.sleep` release? What does `Object.wait` release?

`Thread.sleep(millis)` releases nothing at all: if the sleeping thread is holding a lock — say the monitor on a `Bonus` object while recomputing its clawback amount — it keeps holding that lock for the entire sleep duration, blocking every other thread that wants it even briefly.
That is a common cause of unexplained latency spikes when someone adds a `sleep` for "back-off" inside a synchronized block.
`Object.wait()` is the structural opposite: it must be called while already holding the target object's monitor, or it throws immediately, and calling it *atomically* releases that same monitor so another thread can acquire it, perform the work that will eventually satisfy the waiting thread's condition, and call `notify`/`notifyAll` to wake it back up.
That atomic release-then-park step is the entire reason `wait` exists as a separate primitive from `sleep` — `sleep` is not lock-aware in any way and has no mechanism for giving up a lock it happens to hold.

**Follow-up:** What exception does `wait()` throw if called without holding the monitor?
`IllegalMonitorStateException`, unconditionally, at runtime — there is no compile-time enforcement that a `wait()` call sits inside a `synchronized` block on the same receiver, which is a common source of bugs after a refactor accidentally moves the call outside its guarding block.

**Pitfall:** Calling `wait()` in an `if` rather than a `while` loop is a related, extremely common bug: spurious wakeups are permitted by the JLS, so a thread waiting for a `PaymentRun`'s sign-off flag to flip must re-check the condition itself after waking, not assume the wakeup means the condition now holds.

**Interview:** A natural follow-on is "why does `wait` need to be in a loop but `Thread.join()` doesn't need the caller to re-check anything?" — because `join()` internally already loops on `isAlive()` under the hood, re-`wait`-ing until the target thread has actually terminated; the loop is hidden inside the JDK implementation rather than pushed onto the caller.

**Pitfall:** A related but distinct trap is calling `notify()` instead of `notifyAll()` when more than one thread may be legitimately waiting on the same monitor for different reasons — `notify()` wakes exactly one arbitrarily chosen waiter, and if that waiter's own condition still isn't satisfied it goes back to waiting while every other, possibly-satisfiable waiter never gets a chance; `notifyAll()` is the safe default unless you can prove every waiter is interchangeable.

**Follow-up:** Is there a cost to always defaulting to `notifyAll()`?
Yes — every waiting thread wakes up and re-contends for the monitor, and every one except the eventual winner goes straight back to `wait()` after re-checking its condition, so under heavy contention with many waiters `notifyAll()` causes a burst of pointless wakeup-then-resleep cycles that `notify()` (when provably safe) avoids.

### 5.1.7 Why were `Thread.stop`/`suspend`/`resume` removed

`Thread.stop()` killed a target thread at an arbitrary bytecode instruction by asynchronously throwing `ThreadDeath` wherever that thread happened to be executing at the moment `stop()` was called.
That could be mid-update of a `FundsLedger` entry, leaving `CLIENT_CASH_RESERVED` decremented but `CLIENT_CASH_AVAILABLE` not yet incremented — an invariant torn with no transactional rollback and no reliable way to even detect the corruption afterward.
`suspend()`/`resume()` had a related but distinct failure mode: `suspend()` froze a target thread without releasing any locks it currently held, so if that frozen thread happened to hold the lock protecting the stake-reservation counter, every other thread wanting that same lock deadlocked permanently.
That includes, in the worst case, the one thread that was supposed to eventually call `resume()`, if it happened to need that same lock first.
Both were marked deprecated as inherently unsafe as far back as Java 1.2, and after two decades of that warning being widely ignored in legacy code, they were finally **removed outright** — not merely deprecated further — in **Java 20**.
Calling any of the three now throws `UnsupportedOperationException` at the call site instead of performing the unsafe action.

**Follow-up:** What replaced them conceptually?
Cooperative cancellation: the target thread itself checks a flag or its own interrupt status at a point of its own choosing and exits `run()` voluntarily, having first restored whatever invariant it was mid-updating — control over when it is safe to stop stays with the thread that owns the state, never with an external caller yanking control away from an in-progress mutation.

**Interview:** If asked "what does calling `Thread.stop()` on Java 21 actually do," the correct answer is that it compiles but throws `UnsupportedOperationException` at runtime — it has not merely been discouraged, it is a hard failure the moment it executes, which is a stronger statement than most candidates expect.

**Pitfall:** Some candidates confuse "deprecated" with "removed" and answer that `stop()` "still works but shouldn't be used" — on Java 21 that is simply false; the method exists on the API surface for source compatibility but its body unconditionally throws, so no code path through it can ever succeed.

**Follow-up:** Is `Thread.destroy()` in the same category?
Yes — `destroy()` was never even fully implemented in any shipped JDK; it always threw `NoSuchMethodError` historically, another member of this unsafe-lifecycle-control family alongside `stop`/`suspend`/`resume` that the JDK carried as dead API surface for a very long time before finally cleaning it up.

**Follow-up:** If `stop()` is unavailable, how do you handle a worker thread that is truly hung — for example wedged inside a third-party library call that never returns and never checks interruption?
There is no clean answer at the language level: an uninterruptible hang in native or blocking code that ignores `interrupt()` cannot be forcibly terminated without killing the whole JVM process, which is exactly why production systems isolate such risky calls behind a timeout at the I/O layer (a socket read timeout, an HTTP client deadline) rather than relying on thread-level cancellation to save them.

### 5.1.8 How do you stop a thread, properly

There is no forcible, externally-safe way to stop another thread — Java deliberately removed that button, as 5.1.7 explains.
The correct pattern is cooperative: call `interrupt()` on the target, and have the target's loop check `Thread.currentThread().isInterrupted()` — or simply let a blocking call like `queue.take()` throw `InterruptedException` on its behalf — and exit `run()` on its own terms.
That means releasing any locks and finishing any in-flight work cleanly, such as completing the current `WithdrawalTransaction` write rather than abandoning it half-applied.
A plain `volatile boolean running` flag also works for tight, CPU-bound loops that never call anything blocking, but `interrupt()` is generally preferred because it *also* unblocks a thread currently parked in `wait`/`sleep`/`join`/interruptible I/O.
A flag alone would leave such a thread stuck until the blocking call happened to return on its own, which for a queue with nothing arriving could be never.

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
        // apply to FundsLedger, then mark tx settled; a well-behaved
        // implementation finishes this call rather than aborting mid-write
    }
}
```

**Follow-up:** Why re-interrupt inside the `catch` before returning?
Catching `InterruptedException` clears the interrupt flag as a side effect; if this `run()`'s caller — a pooled worker wrapper that logs whether a thread exited due to cancellation or a genuine error — also inspects the flag afterward, losing it hides the cancellation signal from everything further up the call chain.

**Interview:** A staff-level follow-up worth being ready for: "how would you unit-test that this shutdown path actually stops within a bounded time?" The pattern is to interrupt the worker's thread from the test, then `join(timeoutMillis)` on it and assert `!thread.isAlive()` afterward — proving the cooperative shutdown actually terminates rather than merely proving the flag was set.

**Follow-up:** How does this pattern extend to a pool of workers rather than one thread?
`ExecutorService.shutdownNow()` interrupts every pooled worker and returns the tasks that never started; the caller then typically calls `awaitTermination(timeout, unit)` in a loop and, if it returns `false`, escalates — logging a hard failure rather than pretending the shutdown succeeded silently.

**Pitfall:** A worker that catches `InterruptedException`, restores the flag, but then loops back into `while (!Thread.currentThread().isInterrupted())` on the very next line is fine — the loop condition sees the restored flag and exits cleanly — but a worker that instead swallows the exception and continues into another blocking `queue.take()` will simply block again immediately, since a restored flag does not itself unblock a call already in progress; the explicit `return` in the snippet above is what actually stops the loop.

**Interview:** A common trick question: "if `interrupt()` is called while the thread is doing CPU-bound work with no blocking call in sight, what happens?" Nothing automatically — the interrupt flag is simply set and sits there until the code explicitly checks it, which is exactly why CPU-bound loops need their own periodic `isInterrupted()` check rather than relying on interruption to preempt them.

**Follow-up:** What happens if `interrupt()` is called on a thread that is already `TERMINATED`?
Nothing observable — it is a harmless no-op; there is no thread left to receive the flag, and no exception is thrown for interrupting a thread that has already finished.

**Follow-up:** Does interrupting a thread parked in `Object.wait()` guarantee it wakes immediately?
Yes for the `wait`/`sleep`/`join`/interruptible-I/O family specifically — those methods are documented to respond to interruption by throwing `InterruptedException` promptly rather than waiting for their timeout or condition to be satisfied first, which is what makes `interrupt()` a genuinely responsive cancellation signal rather than merely a flag someone might eventually notice.

### 5.1.9 What are the two legal responses to `InterruptedException`

First, propagate it: declare `throws InterruptedException` and let it bubble uncaught, which is correct whenever the calling method has no meaningful recovery of its own — a private helper invoked from `run()` with nothing special to clean up should simply pass it on.
Second, catch it, restore the interrupt status with `Thread.currentThread().interrupt()`, and then return or otherwise wind the method down — used at a boundary where a checked exception cannot be declared, most commonly `Runnable.run()`, whose signature has no `throws` clause at all.
What is **not** legal, in the sense of being a genuine correctness bug rather than a style preference, is swallowing it silently with `catch (InterruptedException e) {}`.
That loses the cancellation signal permanently: the thread keeps running as though nothing happened, finishing a stake-settlement job whose caller has already given up waiting and possibly already retried the same work elsewhere, silently doubling it.

**Pitfall:** An empty catch block around `InterruptedException` is one of the most common review-flagged concurrency bugs precisely because it has no immediate symptom under normal load.
The code appears to work fine and only misbehaves later in a confusing way, such as a shutdown sequence that hangs indefinitely because a worker thread never noticed it had been told to stop.

**Interview:** A good follow-up to expect: "what if you're in a `Future.get()` caller and it throws `InterruptedException` — do you have a third option?" No — the same two responses apply, but restoring the interrupt flag before returning is what lets an `ExecutorService`'s own shutdown machinery notice the caller wants out.

**Pitfall:** Wrapping `InterruptedException` in an unchecked `RuntimeException` and rethrowing it without also restoring the interrupt flag is a half-fix seen often in framework code — the caller now at least sees a failure, but any lower-level cancellation-aware code further down that also checks `isInterrupted()` still sees a clean, non-interrupted thread, because the flag itself was never restored.

**Interview:** Some interviewers ask for the fix as code rather than prose: `catch (InterruptedException e) { Thread.currentThread().interrupt(); throw new RuntimeException("settlement interrupted", e); }` — both the flag restoration and the wrapped exception, in that order, is the complete and expected answer.

**Follow-up:** Does the order of `interrupt()` and `throw` in that snippet matter?
Not functionally — the flag is a piece of thread-local state independent of the exception being thrown, so restoring it before or after constructing the wrapped exception has the same observable effect; restoring it first is simply the more readable convention, matching "acknowledge, then fail."

### 5.1.10 What is the difference between `isInterrupted()` and `Thread.interrupted()`

`isInterrupted()` is an instance method callable on any `Thread` reference from any other thread, and it does **not** clear the flag — calling it repeatedly returns the same answer until something else changes it.
That is exactly what makes it suitable for one thread non-destructively polling another's status.
`Thread.interrupted()` is, confusingly, a **static** method, and it always operates on the *currently executing* thread regardless of what receiver expression precedes it in source code; as a side effect it **clears** the flag and returns whatever it held immediately before clearing.
This asymmetry is deliberate: `interrupted()` is designed for a loop to consume the interrupt signal exactly once per occurrence and reset for the next one, while `isInterrupted()` is for external, non-destructive inspection of some other thread's status.

**Pitfall:** Writing `someOtherThread.interrupted()` compiles cleanly — it is a static method, so the receiver expression is evaluated and then discarded — but at runtime it always checks and clears the **calling** thread's own flag, never `someOtherThread`'s, regardless of what the code visually appears to be checking.
Most IDEs flag this with a static-method-called-on-instance warning, but it still slips into hand-rolled cancellation loops written under deadline pressure, and the resulting bug — a cancellation that silently never registers — is genuinely hard to spot in review.

**Follow-up:** Which one would you use to write a worker loop's own condition check on itself?
`Thread.interrupted()`, called with no receiver, or equivalently `Thread.currentThread().isInterrupted()` if you also need to leave the flag set for a caller further up — the choice is about whether the flag should be consumed here or preserved for someone else to inspect.

**Interview:** A quick memory check some interviewers use: "does `interrupted()` clear a flag that was never set?" Trivially yes in the sense that it still returns `false` and there is nothing to clear, but the point of the question is to confirm the candidate understands `interrupted()` always performs the clear-and-return-previous-value operation unconditionally, not only when the flag happened to be `true`.

**Follow-up:** Does a virtual thread's interrupt flag behave any differently from a platform thread's?
No — interruption semantics are identical for both; the flag, `interrupt()`, `isInterrupted()`, and `Thread.interrupted()` all behave the same way regardless of whether the thread is a carrier-bound virtual thread or an ordinary platform thread.

**Follow-up:** Is `Thread.interrupted()` safe to call from a signal handler or a shutdown hook?
Yes with a caveat — it is safe in the sense that it will not throw, but calling it from a shutdown hook clears the *hook thread's own* flag, not the flag of whatever application thread the hook is meant to be signaling, which is a scoping mistake worth watching for when writing shutdown logic that tries to coordinate cancellation across threads.

### 5.1.11 Daemon versus non-daemon threads

The JVM stays alive as long as at least one non-daemon thread is still running, and it exits the instant every *remaining* thread is a daemon, regardless of what those daemon threads happen to be doing mid-execution.
There is no graceful shutdown sequence for them, no guaranteed `finally` block execution — the process simply terminates underneath them.
Daemon threads are appropriate for background work whose loss on JVM exit is acceptable — a periodic metrics-flushing thread reporting the stake-reservation counter, a cache-warming thread for `ClientRestrictions` lookups that can simply rebuild on the next start.
Anything that must run to completion — flushing an approved `PaymentRun` file out to the banking partner, finishing pending writes into the ledger's 90-day hot window before shutdown — must either run on a non-daemon thread, or run on a daemon thread that the shutdown sequence explicitly `join()`s before letting the JVM exit, closing the gap deliberately rather than by accident.

**Follow-up:** How do you mark a thread daemon, and when must you do it?
`thread.setDaemon(true)`, and it must be called **before** `start()` — calling it after the thread has already started throws `IllegalThreadStateException`, the same exception family as a double `start()` call, because both guard against mutating a thread's identity once it is already live and scheduled.

**Pitfall:** Assuming an `ExecutorService`'s worker threads are daemon by default — `Executors.newFixedThreadPool` uses the default `ThreadFactory`, which creates **non-daemon** threads, so an application that forgets to call `shutdown()` on its executor will hang at JVM exit indefinitely, waiting on threads nobody told to stop, which is a frequent cause of a Spring Boot application that "won't exit" in CI.

**Interview:** A sharp follow-up worth anticipating: "is `main` itself a daemon thread?" No — `main` is the archetypal non-daemon thread, which is why a JVM whose `main` method returns immediately but has spawned non-daemon background threads (say, an unmanaged reporting thread for the stake-reservation counter) keeps the process alive well past `main`'s own completion, often surprising engineers who assume the process exits when `main` returns.

Note also that virtual threads on Java 21 are daemon threads by default and cannot be changed to non-daemon — `setDaemon(false)` on a virtual thread throws `IllegalArgumentException`, a deliberate design choice since virtual threads are meant to be cheap, disposable, and never individually load-bearing for JVM lifetime decisions.

**Pitfall:** Confusing "daemon thread" with "low priority thread" is a common conflation — daemon-ness controls only whether the thread's existence blocks JVM exit; it says nothing about scheduling priority, and a daemon thread can just as easily starve non-daemon threads of CPU time as any other thread can, since `setPriority()` is an entirely orthogonal, separately-configured property.

**Follow-up:** Does a daemon thread inherit its daemon status to threads it creates?
Yes — a thread created by a daemon thread is itself a daemon thread by default, which is why a badly designed background subsystem can end up spawning an entire daemon-only sub-hierarchy that never gets a chance to run its shutdown logic on JVM exit, since nothing in that hierarchy keeps the process alive.

**Follow-up:** Is the `main` thread's daemon-inherited spawn rule the reason a plain `new Thread(runnable).start()` in `main` is non-daemon by default?
Yes — new threads inherit daemon status from their *creating* thread unless explicitly overridden, and since `main` itself is non-daemon, any thread it directly spawns without calling `setDaemon(true)` is non-daemon too, which is the default most application code relies on without ever stating it explicitly.

### 5.1.12 What does `Thread.yield()` guarantee? (Nothing.)

Nothing, by specification, and that is the whole answer worth giving.
`yield()` is merely a hint to the scheduler that the current thread is willing to give up its current timeslice to another thread of the same or higher priority — but the JLS explicitly leaves the scheduler free to ignore the hint entirely, and on many modern OS schedulers it is effectively a no-op or immediately re-selects the very same thread that just called it.
It provides **no** memory visibility guarantee, unlike `synchronized` or `volatile`, and **no** ordering guarantee at all between the yielding thread and whatever runs next.
Code that relies on `yield()` to "let the other thread catch up" — for instance hoping a slower settlement worker gets a scheduling turn before a faster reservation worker floods a shared queue — depends on undefined scheduler behavior, and typically passes reliably in local testing on one OS/JVM combination while failing unpredictably in production on another.

**Insight:** `yield()` survives in the API mainly for spin-loop back-off inside low-level JDK code — for example a `StampedLock` optimistic-read retry loop — where "maybe let someone else go" costs essentially nothing if the scheduler ignores it, rather than as a tool application code should ever reach for as a scheduling guarantee.

**Follow-up:** Is there anything `yield()` is guaranteed to do?
Only that it is a suggestion the JVM is permitted to pass through to the underlying OS's own yield primitive (`sched_yield` on Linux) — the JLS makes no promise about the result, and even the OS-level primitive itself offers only a hint, not a contract, about which thread runs next.

**Pitfall:** Using a `yield()`-based busy-wait loop to implement "wait until a `WithdrawalTransaction` is settled" instead of a proper blocking wait is a genuine anti-pattern that shows up in interview take-homes — it burns a full core spinning, provides no correctness guarantee about when the condition becomes visible, and the correct tool is `wait`/`notify`, a `CountDownLatch`, or a `BlockingQueue`, all of which give both an actual wakeup mechanism and a memory-visibility guarantee that `yield()` simply does not have.

**Interview:** A comparison worth having ready: `Thread.onSpinWait()`, introduced later than `yield()`, is the modern, more targeted hint for tight spin-wait loops — it tells the CPU (via a hardware pause instruction on supporting architectures) that the current iteration is a spin-wait, letting hyperthread siblings make progress, without asking the OS scheduler to consider a full context switch the way `yield()` does.

**Follow-up:** Does `Thread.setPriority()` interact with `yield()` in any guaranteed way?
No — priority is itself only a hint to the OS scheduler, with no cross-platform guarantee of effect, so combining two independently unenforceable hints does not produce an enforceable outcome; neither should be relied on for correctness, only ever as an optional, best-effort tuning signal.

### 5.1.13 What are the *two* guarantees of `synchronized`

Mutual exclusion — only one thread may hold a given monitor at a time, so two threads both calling `reserveStake` on the same `FundsLedger` instance cannot interleave their reads and writes of the wallet's four buckets.
That guarantees the `StakeSplit` computed for one call cannot be corrupted by another call's partial update landing in between.
And visibility — entering a `synchronized` block establishes a happens-before edge with the *previous release* of that same monitor by any thread, meaning everything that releasing thread wrote before giving up the lock is guaranteed visible to whichever thread next acquires it, even for plain, non-`volatile` fields that carry no ordering guarantee of their own.
Candidates who name only mutual exclusion are giving half an answer, and typically cannot then explain why wrapping a shared field in `synchronized` also fixes visibility bugs that look, on the surface, like pure interleaving races rather than stale-read races.

**Follow-up:** Does `synchronized` guarantee fairness — that the longest-waiting thread acquires the lock next once it frees up?
No. The JVM's intrinsic lock makes no fairness guarantee at all; a thread that has just arrived can barge ahead of one that has been waiting far longer under sustained contention.
`ReentrantLock(true)` is the tool that gives approximate FIFO fairness when starvation is a real operational risk, at a measurable throughput cost.

**Pitfall:** Assuming `synchronized` alone gives ordering guarantees between two *different* locks — it only orders acquisitions and releases of the *same* monitor; two threads each synchronizing on a different `Reservation` object get no ordering relationship at all between their operations, however tempting it is to assume "it's all synchronized, so it's all ordered."

**Interview:** Interviewers sometimes probe whether the candidate knows `synchronized` also implies a compiler/CPU reordering barrier, not merely "mutual exclusion plus visibility" stated abstractly — the concrete answer is that no instruction from inside the block can be reordered to execute before the lock is acquired or after it is released, which is what actually makes the visibility guarantee hold in the presence of an optimizing JIT.

**Follow-up:** Does `synchronized` protect a field that a completely different, unsynchronized method also reads?
No — the visibility and ordering guarantees only apply between threads that both go through the *same* synchronized block or method on the *same* monitor; an unsynchronized reader anywhere else in the codebase gets none of those guarantees regardless of how carefully the writer side is locked.

**Follow-up:** Is entering a `synchronized` block on a monitor no one has ever released before still a happens-before edge for anything?
No meaningfully useful one — happens-before requires a prior release to pair with; the very first acquisition of a freshly constructed object's monitor has nothing to be ordered after except whatever safely published the object's reference in the first place, typically the constructor's own `final`-field guarantees (5.1.31) or the safe-publication mechanism used to hand out the reference.

### 5.1.14 What is a monitor, and where does it live

A monitor is the pairing of a mutual-exclusion lock with a wait-set, conceptually one per object, used by both `synchronized` and by `wait`/`notify`/`notifyAll`.
Every Java object logically has an associated monitor; in the JDK's actual implementation the monitor is not a heap-resident, fully materialized structure from the moment the object is created.
For an uncontended lock, the JVM uses lightweight, stack-based locking encoded directly into the object's header mark word, avoiding any real allocation at all.
The monitor only "inflates" into a full, heavyweight `ObjectMonitor` — historically a natively allocated structure — when real contention occurs and the JVM needs somewhere to actually park waiting threads.

`[VERSION-TRAP]` JDK 25's compact-object-headers work (JEP 519) further changes the physical picture by moving inflated-monitor bookkeeping toward a side-table representation rather than the inline mark-word encoding Java 21 still uses.
So "where does it live" genuinely has a version-scoped answer: logically it is attached to the object from the start on every version; physically, the cheap uncontended path avoids allocating anything at all until contention forces the JVM's hand, and exactly what that inflated structure looks like differs between 21 and 25.

**Follow-up:** Can you synchronize on a primitive value directly?
No — `synchronized` requires an object reference because locking state lives in the object's header, and primitives have no header at all; you must synchronize on a boxed wrapper or, far better, a dedicated `private final Object` lock created solely for that purpose.

**Interview:** Expect a quick sanity check here — "so does every object really cost extra memory for a monitor?" No: since the lock is only materialized on contention, an uncontended `Reservation` object pays essentially zero extra cost for the capability, which is the entire design point of lightweight, header-based locking.

**Pitfall:** Some candidates say the wait-set is a separate JDK-level data structure entirely disconnected from the lock; in fact the wait-set is part of the *same* monitor abstraction as the lock — a thread must hold the monitor to enter its wait-set via `wait()`, and it is released back onto the contention queue for that identical monitor once `notify` fires, which is why `wait`/`notify`/`notifyAll` are declared on `Object` rather than on some separate condition-variable type.

**Interview:** A related design question: "why does every `Object` carry the *potential* for a monitor rather than only classes that actually need one?" Because Java made locking a universal capability of every object rather than an opt-in interface, trading a small amount of header-bit reservation on every object for the simplicity of never needing a special "lockable" marker type.

**Follow-up:** How does `hashCode()` interact with the mark word that also encodes lock state?
The identity hash code, once computed, is cached in the same mark word region that also encodes lock state, which is why calling `hashCode()` on an object can force a lock-state transition on some JVM implementations — one of the reasons biased locking (5.1.7's neighbor topic in the wider syllabus) became increasingly awkward and was ultimately removed in Java 15.

### 5.1.15 Is `synchronized` reentrant, and why does it have to be

Yes — a thread that already holds a given monitor can re-acquire it on a nested call without blocking on itself; the JVM tracks a recursion count on the lock record and only fully releases the monitor once that count returns to zero, matching the number of exits to the number of entries.
It has to be reentrant because Java methods routinely call other `synchronized` methods on the same receiver, including through ordinary composition.
A `synchronized` `settleStake` method might internally call a `synchronized` `applyLedgerEntry` method on the very same `FundsLedger` instance, simply as part of implementing settlement in terms of a lower-level ledger write.
Without reentrancy, that nested acquisition would block indefinitely — the thread would be waiting on a lock it itself already holds, a self-deadlock baked directly into everyday method composition rather than into any unusual multi-thread interaction between two separate threads.

**Follow-up:** Is `ReentrantLock` reentrant for the same underlying reason?
Yes, by name and by explicit design — it maintains its own internal hold count precisely to match `synchronized`'s reentrant behavior, which is one of the reasons it could be introduced as a semantic drop-in replacement rather than forcing callers to reason about a fundamentally different locking model.

**Pitfall:** Reentrancy is not free of risk — a thread that acquires the same lock recursively three times must also release it exactly three times, and a `try/finally` mismatch (unlocking once in a `finally` block that should have run three times) leaves the lock held, silently blocking every other thread forever with no exception ever thrown to indicate the leak.

**Interview:** A candidate is sometimes asked to name a lock that is deliberately *not* reentrant — the answer is a raw `Semaphore` with a single permit, or a hand-rolled spinlock built on `AtomicBoolean.compareAndSet`; both will self-deadlock a thread that tries to acquire twice, which is precisely why they are unsuitable as a general-purpose substitute for `synchronized`/`ReentrantLock` inside method bodies that may call each other.

**Follow-up:** Does reentrancy apply across different objects of the same class?
No — reentrancy is per-monitor, not per-class; a thread holding the lock on `reservationA` gets no special treatment acquiring the lock on a different `reservationB`, even of the identical class, and must contend for it normally.

**Follow-up:** Can a thread deadlock itself by acquiring the same lock twice under different code paths?
No, precisely because of reentrancy — the entire point is that the same thread acquiring the same monitor any number of times never blocks; self-deadlock via reentrant acquisition is not possible in Java by design, unlike in lock implementations that are deliberately non-reentrant.

**Follow-up:** Does `ReentrantLock.getHoldCount()` expose the same recursion count `synchronized` tracks internally but never surfaces?
Yes — `getHoldCount()` is a documented, queryable method that returns exactly this count for the calling thread, giving explicit visibility into reentrancy depth that `synchronized`'s internal lock record never exposes through any public API.

### 5.1.16 Do a synchronized instance method and a synchronized static method exclude each other?

No — they lock on two entirely different monitors and never contend with each other, no matter how much load either is under.
A `synchronized` instance method locks on `this`, the specific object instance — for example one particular `Reservation` object.
A `synchronized` static method locks on the `Class` object for that class — for example `Reservation.class` — which is a single, JVM-wide object shared across every instance of the class.
A thread running inside a synchronized instance method on `reservationA` and a thread running inside a synchronized static method of the very same class execute fully concurrently, with zero mutual exclusion between them, because there is no shared lock object connecting the two calls at all.

**Pitfall:** Assuming "everything on this class is synchronized, so it's all safe together" when mixing static and instance synchronized methods that both touch a shared *static* field.
The instance-level lock provides zero protection for that static field, because the instance lock and the class lock are different monitor objects entirely.
The fix requires deliberately synchronizing on the same monitor from both kinds of methods — typically the `Class` object explicitly, from both places, rather than relying on the instance lock to somehow cover static state.

**Follow-up:** How would you make an instance method also lock on the class-wide monitor?
Replace `synchronized` on the method signature with an explicit `synchronized (Reservation.class) { ... }` block inside it, which makes the shared lock visible in the code rather than implicit in the method's own declaration.

**Interview:** This is frequently paired with a design-judgment follow-up — "is locking on `Class` objects ever a good idea?" Generally no for application code: `Class` objects are as globally shared and as easy to accidentally contend on from unrelated code as interned strings are, so a dedicated static `private static final Object` lock is almost always the better choice even for coordinating class-wide state.

**Pitfall:** A subtler variant: two subclasses of the same base class each declaring their own `synchronized` static method lock on *different* `Class` objects (`SubclassA.class` versus `SubclassB.class`), not on the common superclass — a candidate who assumes static synchronization is inherited the way instance behavior is will misjudge what actually excludes what.

**Follow-up:** What lock does a `synchronized` block around `this.getClass()` acquire compared to one around `Reservation.class` in a base class method?
They can differ at runtime — `getClass()` returns the *runtime* type, so a subclass instance yields the subclass's `Class` object, while `Reservation.class` is always the literal, compile-time class regardless of the actual runtime type, a distinction that matters the moment inheritance enters the picture.

### 5.1.17 What can go wrong locking on a `String` literal or a boxed `Integer`

String literals are interned into a JVM-wide shared pool, and boxed `Integer`s in the cached range −128 to 127 are returned by `Integer.valueOf` from a shared cache rather than freshly allocated.
So `synchronized("PAYMENT_RUN_LOCK")` or `synchronized(clientCount)` where `clientCount` is a small boxed `Integer` may silently share the *exact same object identity* with completely unrelated code elsewhere in the same JVM — including third-party library code you neither wrote nor control — that happens to use the identical string literal or the identical small integer value.
That unrelated code becomes an invisible co-contender on your lock: it can cause spurious blocking under load, or in the worst case a genuine deadlock against code with no visible relationship to yours in any stack trace, unless you already know to suspect literal or cache sharing as the cause.

**Pitfall:** The fix is to synchronize on a `private final Object` created specifically and solely as a lock, never exposed outside the class — `private final Object paymentRunLock = new Object();`
Never on interned literals, cached boxed primitives, or exposed mutable fields such as a plain `String` field another thread could reassign, which would change what monitor `synchronized` is actually locking on partway through the object's lifetime, a second and subtler variant of the same trap.

**Interview:** A well-prepared candidate mentions both halves unprompted — string interning *and* the `Integer` cache boundary at −128..127 — since interviewers often ask "does this only affect strings?" as a direct follow-up to see whether the answer was memorized narrowly.

**Follow-up:** Would `synchronized(new Object())` inside a loop body ever be correct?
No — a fresh `Object` created inside the method provides no exclusion at all between separate invocations or separate threads, since every call gets its own unique, never-shared monitor; the lock object must be shared and stable across every caller that needs to be excluded, typically a field, not a locally constructed value.

**Follow-up:** Does the same interning risk apply to enum constants used as lock objects?
No — enum constants are guaranteed unique, JVM-wide singletons by the language specification itself, with no equivalent of string interning or integer caching creating unintended sharing with unrelated code, which is one reason a private enum with a single constant is sometimes used as a deliberately safe, self-documenting lock object.

---

**Leaves covered:** 5.1.1–5.1.17 (17 questions)
**Leaves deferred:** none
**Diagrams included:** none
**Target version:** Java 21 LTS
**Lines:** 421
