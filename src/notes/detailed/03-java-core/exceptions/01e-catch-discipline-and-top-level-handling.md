# 03 Java Core — Catch discipline and top-level handling — BASICS (§1.20.18–1.20.24)

**Target version: Java 21 LTS.** | **Part 1 of 5** | [Index](../00-index.md)
Previous: [`finally` traps](01d-finally-traps.md) · Next: [Exceptions in practice — checked or unchecked](02-in-practice.md)

Everything so far in this tier has been about the shapes the language gives you — the hierarchy, the `Throwable` API, multi-catch, try-with-resources, `finally`. This file is about the five ways experienced engineers still get it wrong once those shapes are in hand: swallowing the signal instead of routing it, breaking the one cooperative-cancellation protocol Java has, reaching for a catch clause wide enough to catch things that were never meant to be caught, forgetting that the process itself needs a "finally", and misquoting a JEP that shipped seven years ago. None of these are subtle mechanically. All of them are common in code review.

Everything below is measured against **Oracle JDK 21.0.7 (21.0.7+8-LTS-245, macOS aarch64)**, with **Oracle JDK 17.0.15** for one version comparison.

---

## 1. Swallowing and logging (1.20.18)

### Mental model

A `catch` block is a fork in the road: either the caller finds out something went wrong, or it doesn't. `catch (Exception e) {}` is the fork where the road to "caller finds out" is bulldozed — the exception arrives, the JVM unwinds the stack to deliver it, and then the handler throws that information away. The empty body is the obvious form of this. The far more common form in a real codebase looks like it's doing something: `log.error("failed: " + e.getMessage())`. It compiles, it runs, it even prints a line. But it discards the same information the empty catch discards — the stack trace and the `Caused by:` chain — while looking, on a code-review skim, like responsible handling.

### Why it exists as a trap

Nobody sets out to write `catch (Exception e) {}`. It arrives as a side effect of something else: an IDE's exception-wrapping quick-fix, a "make the build green" pass around a checked exception the method signature didn't want to declare, or a defensive catch added under deadline pressure with a comment promising to come back and handle it properly, which never happens. The `String`-concatenation form arrives even more innocently, because `e.getMessage()` looks like "the important part of the exception" — it's short, it's human-readable, and printing it feels like doing the responsible thing.

### When this is ever legitimate

Only as a **caught-and-decided** boundary, never as a dead end. A REST controller advice that catches `InsufficientFundsException`, translates it to a `409` with a client-safe body, and **logs the original throwable** on the way out is legitimate — the exception is being routed, not swallowed. `PaymentService.reserveStake` catching a lower-level `LedgerImbalanceException`, converting it into a domain-specific `RestrictedActionException` while chaining the cause (`01a-throwable-api-and-chaining.md` owns the mechanics of that chain), is legitimate for the same reason. What is never legitimate is a `catch` whose body neither rethrows, wraps-and-rethrows, nor logs the throwable itself.

### How it works, and the string-concatenation trap specifically

`Throwable.getMessage()` returns exactly what was passed to the constructor — for a hand-thrown `InsufficientFundsException("stake exceeds stakeable balance")` that's a useful sentence, but for a `NullPointerException` produced by the JVM without an explicit message it can be `null`, or — since JEP 358 — a synthesized description of the failing bytecode instruction (concept 5, below). `String.valueOf(null)` produces the literal text `"null"`, so `"failed: " + e.getMessage()` on a bare NPE prints `failed: null`, telling the reader precisely nothing about which reference was null or where. The correct call passes the throwable as its own argument to the logger, never folded into the message string: `log.error("stake reservation failed for round {}", roundId, e)`. This is not a style preference — the `Logger` API is deliberately overloaded so that a trailing `Throwable` argument is recognized specially by the SLF4J binding even when the format string has no `{}` placeholder reserved for it. The placeholders are matched positionally against the non-`Throwable` arguments only; a final argument whose static or runtime type is `Throwable` is peeled off and used to print the full stack trace underneath the formatted line, and does not consume a `{}` slot. That is why `log.error("stake reservation failed for round {}", roundId, e)` has exactly one placeholder and two arguments and still works: `roundId` fills the placeholder, `e` gets the special treatment.

### No diagram for this concept

The evidence is a single side-by-side stdout comparison — one line of prose is the clearer rendering of "one form prints `null`, the other prints the message and the trace."

### A minimal concrete example

```java
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

public class StakeReservationService {

    private static final Logger log = LoggerFactory.getLogger(StakeReservationService.class);

    void reserveStakeWrong(RoundId roundId, Money stake) {
        try {
            // fails inside the Quiz Engine client with a bare NullPointerException,
            // e.g. a null Reservation returned by a stub in a misconfigured test double
            quizEngineReserve(roundId, stake);
        } catch (Exception e) {
            System.out.println("failed: " + e.getMessage());
        }
    }

    void reserveStakeRight(RoundId roundId, Money stake) {
        try {
            quizEngineReserve(roundId, stake);
        } catch (Exception e) {
            log.error("stake reservation failed for round {}", roundId, e);
            throw new RestrictedActionException(RestrictionType.STAKE_BLOCKED,
                    "stake reservation failed for round " + roundId, e);
        }
    }

    private void quizEngineReserve(RoundId roundId, Money stake) {
        Reservation reservation = lookupReservation(roundId); // returns null in this scenario
        reservation.split(); // NPE here, no explicit message
    }

    private Reservation lookupReservation(RoundId roundId) {
        return null;
    }
}
```

Measured on JDK 21.0.7, `reserveStakeWrong` prints exactly:

```
failed: null
```

`reserveStakeRight`'s `log.error` line — measured with an SLF4J simple-logger binding — prints the formatted message followed by the full stack trace, `Cannot invoke "Reservation.split()" because "reservation" is null` as the exception's own message (concept 5 explains why that text exists), which is the entire diagnostic difference between the two forms.

### The gotcha

**Pitfall:** `catch (Exception e) { log.error("failed: " + e.getMessage()); }` looks like proper handling but is functionally an empty catch.
Wrong belief: "I logged something, so I didn't swallow it." Symptom: an on-call engineer sees `failed: null` in the logs for a NullPointerException, or sees the top-level message of a wrapped exception with none of the `Caused by:` chain that would show the real root cause underneath it — the incident takes an extra hour because the actual failing line is not recoverable from the log line at all. Fix: never call `.getMessage()` for logging purposes; pass the throwable itself as a trailing argument (`log.error("stake reservation failed for round {}", roundId, e)`), and follow the rule **log or rethrow, never both** at any single catch site — logging and then rethrowing the same exception up a call chain that also logs it produces the same failure duplicated at every layer. `02d-logging-and-api-boundaries.md` (INTERMEDIATE) owns that rule and the REST-boundary treatment in full; this file states it as the language-level discipline.

> **Definition.** Swallowing is any `catch` block whose body neither rethrows, wraps-and-rethrows, nor logs the caught `Throwable` object itself — logging `e.getMessage()` in its place is swallowing with extra steps.

---

## 2. `InterruptedException` and the interrupt-flag protocol (1.20.19)

### Mental model

Interruption in Java is not a request that stops a thread — it's a single boolean flag on the `Thread` object, set by `interrupt()` and readable by `isInterrupted()`. A blocking method like `Thread.sleep`, `Object.wait`, or `BlockingQueue.take` polls that flag while it's blocked, and if it sees the flag set, it throws `InterruptedException` — and as it throws, it **clears the flag back to false**. That clearing is the entire trap: the flag was the only durable record that cancellation was requested, and the moment the blocking method converts it into an exception, the record is gone unless the `catch` block does something to put it back.

### Why the design is this way

The alternative — a forcible thread-kill primitive — is `Thread.stop()`, deprecated since Java 1.2 for the exact reason it's dangerous: it can interrupt a thread at any bytecode instruction, including mid-mutation of a shared object, leaving that object permanently corrupted with no way to know it happened. Cooperative interruption trades immediacy for safety: the target thread only reacts at points where it's already blocked (or explicitly polling), so it always has the chance to release locks, close resources, and exit cleanly. The cost of that trade is that cooperation is opt-in — a thread that catches `InterruptedException` and does nothing has, in effect, declined to cooperate, and nothing in the language stops it.

### When ignoring it would ever be legitimate

Essentially never inside application code. The one narrow exception is a method explicitly documented as "runs to completion regardless of interruption, and reports afterward" — some cleanup-on-shutdown paths do this deliberately — but even there, the correct pattern is to catch, remember that an interrupt happened, keep working, and restore the flag before returning, not to catch and discard.

### How it works — the two correct responses

There are exactly two structurally correct responses, and the choice between them is dictated by the method's own signature, not by taste.

| Response | When | What it looks like |
|---|---|---|
| Propagate it | The enclosing method's signature already declares `throws InterruptedException` | Add the catch back to a plain `throws` list, or don't catch it at all |
| Restore the flag and stop | The enclosing method is a `Runnable`, a `Callable` whose contract doesn't want it, or any signature that cannot add `throws InterruptedException` | `catch (InterruptedException e) { Thread.currentThread().interrupt(); return; }` (or `break` out of the loop) |
| Catch and discard | Never | — |

The restore idiom exists specifically because `Runnable.run()` cannot declare a checked exception — a `PaymentRun` worker submitted to an `ExecutorService` as a `Runnable` has no way to propagate `InterruptedException` up through `run()`'s signature, so the only way to leave a truthful record for whatever code checks `isInterrupted()` next (including the executor's own shutdown logic) is to set the flag back before returning.

**QuizStakes frame.** A batched `PaymentRun` worker processes approved bank withdrawals inside one of the four daily payout-file windows and is expected to stop promptly when the platform is shutting down (an operator-triggered graceful stop, or the executor's `shutdownNow()`). If the worker's inner loop does `try { queue.take(); } catch (InterruptedException e) { }` and keeps looping, the shutdown signal is invisible to it — the flag that would have told the loop's exit condition to trip has already been cleared by `take()` before the empty `catch` even runs. The measured consequence: a thread that swallows the interrupt reports `isInterrupted() == false` immediately afterward, exactly as if nothing had happened.

```java
Thread worker = new Thread(() -> {
    try {
        Thread.sleep(60_000);
    } catch (InterruptedException e) {
        // swallowed
    }
    System.out.println("interrupted flag inside worker after swallow: "
            + Thread.currentThread().isInterrupted());
}, "payment-run-worker-3");
worker.start();
Thread.sleep(200);
worker.interrupt();
worker.join();
```

Measured on JDK 21.0.7:

```
interrupted flag inside worker after swallow: false
```

The fix for this exact shape is `catch (InterruptedException e) { Thread.currentThread().interrupt(); return; }` in place of the empty body — the worker still stops (via the `return`), and any outer code that later checks `isInterrupted()` sees the truth.

This is the mechanism in full; the interrupt-flag protocol restated as an exception-*design* worked example — including how it interacts with try-with-resources cleanup and how to write a test that asserts a method restores the flag — belongs to guide 05 (Concurrency), which also owns the memory-model guarantees `interrupt()` does and doesn't carry.

### No diagram for this concept

The evidence is one measured boolean (`isInterrupted()` after a swallow) against the two-line fix; a state diagram of a single boolean flag would say less than the sentence above it.

### The gotcha

**Pitfall:** catching `InterruptedException` and returning silently "worked" in testing, so the empty catch shipped.
Wrong belief: "the thread stopped when I interrupted it in my manual test, so the handling is fine." Symptom: in production, the swallow only becomes visible when a *second* blocking call inside the same loop iteration — one that doesn't know an interrupt was ever requested — blocks again, sometimes for the full 60-second `PaymentRun` window timeout, because the flag that would have made it return immediately was cleared. Fix: restore the flag (`Thread.currentThread().interrupt()`) immediately in the catch, even if the current method also happens to `return` or `break` right after — the *next* piece of code that checks the flag, not this one, is who the restore is for.

> **Definition.** The interrupt flag is a per-thread boolean; a blocking method clears it exactly at the moment it converts it into a thrown `InterruptedException`, so a handler that does not explicitly restore or propagate has permanently discarded the only record that cancellation was requested.

---

## 3. Never catch `Throwable` or `Error` (1.20.20)

### Mental model

`Error` is the JVM's own channel for "something is wrong with the *runtime*, not your logic" — `OutOfMemoryError`, `StackOverflowError`, `NoClassDefFoundError`, `LinkageError`. Catching `Throwable` means catching that channel too, alongside every checked and unchecked exception, in one net. The problem is that a handler written to react to `RestrictedActionException` or `IllegalTransitionException` has no sensible reaction to "the heap is exhausted" — and worse, trying to react (allocating a `String` to log, allocating a `StringBuilder` to format a message) can itself throw a second `OutOfMemoryError` while still inside the first one's handler.

### Why the trap is tempting

`catch (Throwable t)` reads, at a glance, like the most defensive possible line — "whatever goes wrong, I've got it." That instinct is correct exactly once in a codebase: at the single top-level boundary where a thread or task is about to end anyway if nothing catches the exception, and the alternative to catching `Throwable` there is not "more targeted handling", it's "the process's default behaviour" (concept 4). Everywhere else, the instinct is a liability, because it silently absorbs failures the rest of the design assumed would surface.

### When this is ever legitimate

Exactly one shape: a top-level thread or executor-task boundary whose job is to **log and re-raise**, never to continue as though nothing happened.

```java
Thread paymentRunWorker = new Thread(() -> {
    try {
        runPaymentRunWindow();
    } catch (Throwable t) {
        log.error("payment-run-worker-3 terminating on unrecoverable condition", t);
        throw t; // re-raise: let the thread die and the default/registered handler see it
    }
}, "payment-run-worker-3");
```

The re-raise is not decorative. A version of this that logs and then falls through — swallowing an `OutOfMemoryError` and letting the loop continue — turns a fatal JVM-level condition into a thread that limps along in an unknown state, most dangerously inside a pooled executor: a `StackOverflowError` caught mid-recursion in a `PaymentRun` worker can leave shared collections (a batch buffer, a partially-written ledger movement list) mutated halfway, and a `catch (Throwable t)` with no re-raise hands that half-mutated state straight back to the pool for the next task to inherit.

### How it works — the specific trap inside "catch everything"

`catch (Throwable t)` also catches `InterruptedException`'s effect indirectly and every subtype of `Error` in the same breath as every subtype of `Exception` — there is no way to write `catch (Throwable t)` that excludes `Error`, because `Error` is a direct sibling of `Exception` under `Throwable` (`01-basics.md` owns the hierarchy). An executor task that does `catch (Throwable t) { log.warn("issue", t); }` with no re-raise therefore converts every future `OutOfMemoryError` on that thread, every `StackOverflowError`, every `NoClassDefFoundError` from a bad deployment, into a warning log line and a pool that keeps accepting work it can no longer safely execute.

### No diagram for this concept

The evidence is the one legitimate code shape above plus the sibling comparison table below it; a hierarchy picture already exists in `01-basics.md` and repeating it here would duplicate that file's diagram rather than add information.

### A minimal concrete example — the four responses to a caught exception, compared

| Response | Code shape | What it costs |
|---|---|---|
| Swallow | `catch (Exception e) { }` or `catch (Exception e) { log.error("failed: " + e.getMessage()); }` | Loses the failure entirely, or loses the stack trace while looking handled (concept 1) |
| Log-only, continue | `catch (Exception e) { log.error("failed", e); }` with no rethrow | Correct only if the caller genuinely has a fallback and the log is the sole record — otherwise indistinguishable from swallowing further up the stack |
| Log-and-rethrow | `catch (Exception e) { log.error("failed", e); throw e; }` | Duplicates the log line at every layer that does this; pick one layer to log at, per `02d-logging-and-api-boundaries.md` |
| Rethrow-translated | `catch (LedgerImbalanceException e) { throw new RestrictedActionException(type, message, e); }` | Correct and idiomatic: narrows the caught type, preserves the cause chain (`01a-throwable-api-and-chaining.md`), translates to the caller's vocabulary |

`catch (Throwable t)` is a fifth row only at the top-level boundary, and only paired with re-raise — it is not a fifth option for ordinary application code, which is why it isn't in the table.

### The gotcha

**Pitfall:** `catch (Throwable t)` used as a blanket "make sure nothing escapes this method" wrapper deep inside application code, far from any thread or executor boundary.
Wrong belief: "catching the widest possible type is the safest possible handling." Symptom: an `OutOfMemoryError` thrown while processing a `PaymentRun` batch gets caught by a mid-stack `catch (Throwable t)` in a helper method three calls deep, logged with a message that itself needs to allocate (and sometimes fails to, compounding the error), and the batch loop continues onto the next withdrawal as though the failure were a normal domain exception — masking a condition that should have terminated the worker. Fix: catch the narrowest type the call site can actually reason about; reserve `catch (Throwable t)` for the single outermost frame of a thread or task, and always re-raise from there.

> **Definition.** `catch (Throwable t)` catches the checked-exception tree, the unchecked-exception tree, and the `Error` tree in one clause; the only sound use of that breadth is a top-level boundary that logs and re-raises rather than continuing.

---

## 4. Process-level backstops: shutdown hooks and uncaught-exception handlers (1.20.22, 1.20.23)

### Mental model

Every `try`/`finally` in this tier's other files (`01d-finally-traps.md`) has a boundary: the JVM process itself. Nothing inside a `finally` block runs if the process is killed outright. `Runtime.addShutdownHook` and `Thread.UncaughtExceptionHandler` are the two mechanisms that exist above that boundary — one is the process's own `finally`, registered once, that runs (when it runs at all) outside any single thread's call stack; the other is what happens when an exception reaches the very top of a thread's call stack with nobody left to catch it.

### Why they exist

A `finally` block guarantees cleanup *within* a method's own control flow, but nothing guarantees that a `finally` written inside `PaymentService` runs when the JVM is asked to stop entirely — `01d-finally-traps.md` establishes that a shutdown hook is the one thing that still runs even when `System.exit` inside a `finally` block short-circuits every enclosing `finally`. Shutdown hooks exist to give a process one last, JVM-orchestrated chance to flush state — close a `PaymentRunFileWriter`, checkpoint a `LedgerConnection` — when the trigger for shutdown could be an operator command rather than a return from `main`. `Thread.UncaughtExceptionHandler` exists for the mirror problem on a single thread: an exception escaping `run()` has nowhere left to propagate to, and without a registered handler, the platform default is silent to everything except `System.err`.

### When to reach for a shutdown hook, and when not

Reach for it for last-resort process cleanup that must run regardless of *which* orderly shutdown path triggered it. Do not reach for it as a substitute for `try`-with-resources or `finally` in ordinary request-scoped code — a shutdown hook is process-scoped, runs once, and (per below) runs concurrently with every other registered hook, none of which is true of a `finally` block.

### How it works — shutdown hooks

`Runtime.getRuntime().addShutdownHook(Thread)` registers a `Thread` (not yet started) to be started when the JVM begins its shutdown sequence.

| Trigger | Runs the hook? |
|---|---|
| Last non-daemon thread exits normally | Yes |
| `System.exit(int)` / `Runtime.exit(int)` | Yes |
| SIGTERM / SIGINT (Ctrl-C, `kill`, an orchestrator's graceful stop) | Yes |
| `Runtime.getRuntime().halt(int)` | No |
| SIGKILL (`kill -9`) | No |
| JVM crash (native fault, `Error` inside the JVM itself) | No |

Measured on JDK 21.0.7:

```
=== shutdown hook: exit ===
calling System.exit
shutdown hook ran: closing PaymentRunFileWriter window
=== shutdown hook: halt ===
calling Runtime.halt
```

— identical hook registration, and `halt` produces no second line at all, because `halt` is documented to terminate the JVM immediately without running shutdown hooks or finalizers. If more than one hook is registered, all of them start concurrently and in unspecified order, so a `PaymentService` hook and an unrelated `NotificationService` hook must not depend on each other's completion order, and each should be defensive about how long it runs, since the JVM will wait for all of them before actually exiting. `Runtime.removeShutdownHook(Thread)` exists to de-register a previously added hook — a supporting fact, not a design decision: it takes the exact `Thread` instance passed to `addShutdownHook`, throws `IllegalStateException` if shutdown has already started, and is mostly useful in tests that register a hook conditionally and want to tear it down between cases. An exception thrown out of a shutdown hook's `run()` is handled the same way as any other thread's uncaught exception — by whatever `Thread.UncaughtExceptionHandler` applies to it — which is the seam into the next mechanism.

### How it works — `Thread.UncaughtExceptionHandler`

When an exception (or error) propagates out of `Thread.run()` with nothing left to catch it, the JVM looks for a handler in a fixed order:

| Order | Handler | Set via |
|---|---|---|
| 1 | The thread's own handler, if set | `Thread.setUncaughtExceptionHandler(handler)` on that specific `Thread` |
| 2 | The thread's `ThreadGroup` | `ThreadGroup.uncaughtException`, overridable by subclassing `ThreadGroup` |
| 3 | The JVM-wide default handler, if set | `Thread.setDefaultUncaughtExceptionHandler(handler)` |
| 4 | Platform default behaviour | Print the thread name and the exception's stack trace to `System.err` |

Measured default behaviour on JDK 21.0.7, no handler registered anywhere:

```java
Thread t = new Thread(() -> {
    throw new IllegalStateException("stake reservation failed for round round-771");
}, "stake-settlement-4");
t.start();
t.join();
System.out.println("main continues after worker thread's uncaught exception");
```

produced:

```
Exception in thread "stake-settlement-4" java.lang.IllegalStateException: stake reservation failed for round round-771
	at UncaughtDefault.lambda$main$0(UncaughtDefault.java:4)
	at java.base/java.lang.Thread.run(Thread.java:1583)
main continues after worker thread's uncaught exception
```

— `main` prints its own line and exits normally, because an uncaught exception on `stake-settlement-4` terminates only that thread, never the JVM, and never propagates back to whoever called `join()`.

### The `execute` versus `submit` asymmetry

This is the trap that catches people who believe an `ExecutorService`'s uncaught-exception handling is uniform across its submission methods. It is not.

```java
Thread.setDefaultUncaughtExceptionHandler((t, e) ->
        System.out.println("default handler saw: " + t.getName() + " -> " + e));

ExecutorService pool = Executors.newFixedThreadPool(1, r -> new Thread(r, "payment-run-worker-3"));

pool.execute(() -> {
    throw new IllegalStateException("execute: stake settlement failed for round round-771");
});
Thread.sleep(300);

Future<?> future = pool.submit(() -> {
    throw new IllegalStateException("submit: stake settlement failed for round round-772");
});
Thread.sleep(300);
System.out.println("after submit, before get(): no output above from the handler for this one");
try {
    future.get();
} catch (ExecutionException e) {
    System.out.println("future.get() surfaced: " + e.getCause());
}
```

Measured on JDK 21.0.7:

```
default handler saw: payment-run-worker-3 -> java.lang.IllegalStateException: execute: stake settlement failed for round round-771
after submit, before get(): no output above from the handler for this one
future.get() surfaced: java.lang.IllegalStateException: submit: stake settlement failed for round round-772
```

`execute(Runnable)` has no `Future` to carry the exception, so a thrown exception has only one route left — it propagates out of the pooled worker thread's `run()` loop and reaches the uncaught-exception handler exactly as in the previous example. `submit(Callable)` returns a `Future`, and the executor's internal task wrapper (`FutureTask`) catches the exception and **stores it inside the `Future`** instead of letting it escape the worker thread — nothing reaches the uncaught handler, nothing appears on `System.err`, and the failure is completely silent until (and unless) someone calls `future.get()`, which rethrows it wrapped in `ExecutionException`. A `PaymentRun` batch dispatched with `submit` and never `.get()`-checked fails silently, forever, with no log line anywhere: the exception is sitting inside a `Future` object nobody asked.

Guide 05 (Concurrency) owns the executor framework in full — pool sizing, rejection policies, `CompletableFuture`'s own error-propagation rules, and the memory-model guarantees behind all of this; this file states the exception-routing asymmetry as the specific trap.

### No diagram for this concept

The evidence is four short measured stdout captures (hook-on-exit, hook-on-halt, default-handler-output, execute-vs-submit) that are each already a one-line fact; a flowchart of "which handler fires" would need to encode the same four lines the resolution-order table above already states more precisely.

### The gotcha

**Pitfall:** dispatching `PaymentRun` batch items with `submit` and never calling `.get()`, believing failures will show up in the logs like they do for `execute`.
Wrong belief: "the executor logs uncaught exceptions regardless of how the task was submitted." Symptom: a subset of a `PaymentRun` window's withdrawals silently fail to process — no exception in the application log, no entry in the default `Thread.UncaughtExceptionHandler`'s output, nothing until someone notices the payout file is short — because the exception was captured inside a `Future` that nothing ever called `.get()` on. Fix: either call `.get()` (or `.join()` on a `CompletableFuture`) on every submitted task and handle the failure there, or use `execute` plus an explicit per-task try/catch that logs before returning, if the caller genuinely has no need for the result.

> **Definition.** A shutdown hook is a JVM-orchestrated, once-only, concurrently-run cleanup thread triggered by an orderly shutdown path and skipped by `halt`, `kill -9`, and a JVM crash; an uncaught-exception handler is the last stop for an exception that reaches the top of a thread's stack, resolved thread-handler first, then `ThreadGroup`, then the JVM default, then `System.err` — and `submit` routes that exception into a `Future` instead, bypassing all four.

---

## 5. Helpful NullPointerException messages — JEP 358 (1.20.24)

### Mental model

A bare `NullPointerException` used to answer one question — *something* was null — and leave the reader to reconstruct *which* reference, from the line number and their own reading of the source. A helpful NPE answers the second question directly, in the message itself, by describing the specific bytecode instruction that failed and the specific variable, field, or method-return expression that was null: `Cannot invoke "Reservation.split()" because "reservation" is null`.

### Why it exists, and the version fact — `[VERSION-TRAP]`

**What is true in Java 21:** helpful NPE messages are computed by default; no flag is required. `-XX:+PrintFlagsFinal` on this machine's JDK 21.0.7 shows the switch already on:

```
bool ShowCodeDetailsInExceptionMessages       = true    {manageable} {default}
```

**What used to be true, and why interviewers still ask for the old form:** JEP 358 shipped in **Java 14** as an opt-in feature, gated behind `-XX:+ShowCodeDetailsInExceptionMessages` — off by default, because the JEP's authors wanted a release cycle of real-world exposure before making the (small but nonzero) startup and message-computation cost the default. It became **on by default starting in Java 15**, tracked by JDK-8233014 ("Enable helpful NullPointerExceptions by default"), and every LTS release since — 17, 21 — inherits that default. The reason the "you have to turn this on" claim keeps surfacing in interviews and blog posts is that most of the writing describing JEP 358 was published when Java 14 was current, when the flag genuinely was required, and that writing was never revised. `{manageable}` in the flag output above means the switch can additionally be flipped at runtime through the platform's management interface (`jcmd <pid> VM.set_flag`), without a restart — worth stating because it means the feature can be toggled off in a running production process if its verbosity becomes a problem, without a redeploy.

### When to reach for it, and when not

There is nothing to reach for — it is automatic and free by default from Java 15 onward. The only decision left is whether to keep it on, and the one reason to turn it off is the security consideration in the next paragraph: a helpful NPE message can describe internal field names, method names, and call structure that a security-conscious API should not hand to an untrusted caller. `03d-internals-npe-messages-and-diagnostics.md` (INTERNALS) owns exactly how the message is derived from the bytecode and the JEP 358 security discussion in depth; `02d-logging-and-api-boundaries.md` (INTERMEDIATE) owns the general rule of not leaking stack traces or internal detail across a REST or public API boundary — the same discipline applies here, since a helpful NPE's message is exactly the kind of internal detail that rule is about.

### How it works — what the message can and cannot name

The description is derived from the bytecode of the single failing instruction — which invocation, field access, or array operation threw — not from source-level variable resolution performed after the fact. A field name or a method name is always available, because both are baked into the bytecode's constant pool regardless of compiler flags. A **local variable's source name**, by contrast, is only available if the class was compiled with debug information — `-g` (or, more narrowly, `-g:vars`) — because that's the only place `javac` records the mapping from a local variable's stack slot back to the name it had in source.

```java
record Reservation(StakeSplit split) {}
record StakeSplit(java.math.BigDecimal bonusPortion, java.math.BigDecimal cashPortion) {}

static Reservation lookupReservation(String roundId) {
    return null;
}

public static void main(String[] args) {
    String roundId = "round-771";
    Reservation reservation = lookupReservation(roundId);
    java.math.BigDecimal bonusPortion = reservation.split().bonusPortion();
    System.out.println(bonusPortion);
}
```

Compiled and run on JDK 21.0.7 twice — once with `javac -g`, once with `javac -g:none` — against the identical source:

```
--- with -g ---
Exception in thread "main" java.lang.NullPointerException: Cannot invoke "NpeLocal$Reservation.split()" because "reservation" is null
	at NpeLocal.main(NpeLocal.java:14)
--- without -g ---
Exception in thread "main" java.lang.NullPointerException: Cannot invoke "NpeLocal$Reservation.split()" because "<local2>" is null
	at NpeLocal.main(Unknown Source)
```

Without `-g`, the local variable's name is gone from the class file entirely, so the JVM falls back to `<local2>` — the raw stack-slot index — which is still more than a bare `NullPointerException` gave before JEP 358 (it still identifies which invocation failed), but is meaningfully less useful than the named form. Production JARs are frequently built with reduced debug info for size or for deliberately obscuring internals, which is precisely when the `<localN>` fallback shows up and surprises people who only ever tested locally with full debug info on.

A chained dereference produces the same style of message pointing at whichever segment of the chain was null — measured earlier in this file (concept 1's example), the return value of a method call rather than a local:

```
Cannot invoke "NpeLocal$Reservation.split()" because the return value of "NpeLocal.lookupReservation(String)" is null
```

That phrasing — "the return value of" a named method call, instead of a bare variable name — is what the message looks like when the null-producing expression was never assigned to a local at all; there is no debug-info dependency for this form, because a method's own descriptor (its owning class and signature) is always in the constant pool.

### No diagram for this concept

The evidence is four short measured message strings (with locals, without locals, chained-call form, and the flag's `PrintFlagsFinal` line); the differences are lexical, and a diagram would just be the same four strings boxed.

### The gotcha

**Pitfall:** assuming a helpful NPE message from a local machine will look identical when the same failure happens in a container built from a stripped or minified artifact.
Wrong belief: "the message always names the variable, because that's what I see in my IDE's console." Symptom: a `<local7>` in a production incident's stack trace where a developer's local repro clearly showed `reservation` — because the production build pipeline compiles with `-g:none` (or strips it later) for a smaller artifact, and the field/method-name parts of the message are unaffected but the local-variable name is gone. Fix: keep at least `-g:vars` (or full `-g`) in the build used for anything whose stack traces will be read by a human, and separately, treat every helpful-NPE message as untrusted-caller-visible information rather than assuming it's development-only, per the security note above.

> **Definition.** A helpful NullPointerException message names the failing bytecode instruction's field, method, or array operand directly, using the constant pool for fields and methods (always available) and the local-variable debug table for local names (present only when compiled with `-g` or `-g:vars`) — on by default since Java 15 (JDK-8233014), opt-in via `-XX:+ShowCodeDetailsInExceptionMessages` only on Java 14.

---

## Pitfalls

### Logging `e.getMessage()` instead of the throwable

**Wrong**

```java
catch (Exception e) {
    System.out.println("failed: " + e.getMessage());
}
```

Measured output for a bare NPE: `failed: null` — the stack trace and the `Caused by:` chain are gone, and for the most common failure mode (a null reference with no explicit message) the concatenation form actively hides the one thing that would have helped.

**Right**

```java
catch (Exception e) {
    log.error("stake reservation failed for round {}", roundId, e);
}
```

The trailing `Throwable` argument is recognized by SLF4J and printed in full underneath the formatted line, independent of how many `{}` placeholders the format string has.

**Why people believe it:** `getMessage()` looks like "the human-readable part" of an exception, and printing it feels more deliberate than passing the whole object — the mistake is not noticing that the whole object *is* the human-readable part once the logger formats it, and the message string alone is a lossy summary of it.

### Catching `InterruptedException` and moving on

**Wrong**

```java
try {
    queue.take();
} catch (InterruptedException e) {
    // will retry next loop iteration
}
```

Measured: `Thread.currentThread().isInterrupted()` reads `false` immediately after this catch runs, because `take()` cleared the flag as it threw. The loop has no way left to learn that a shutdown was requested.

**Right**

```java
try {
    queue.take();
} catch (InterruptedException e) {
    Thread.currentThread().interrupt();
    return;
}
```

**Why people believe it:** the code compiles, the catch clause is mandatory (it's a checked exception), and in a quick manual test the thread often does stop soon afterward anyway for unrelated reasons — masking that the flag itself was lost.

### `catch (Throwable t)` as a general-purpose safety net

**Wrong**

```java
BigDecimal settleBatch(List<Reservation> batch) {
    try {
        return quizEngineSettle(batch);
    } catch (Throwable t) {
        log.warn("settlement issue, skipping batch", t);
        return BigDecimal.ZERO;
    }
}
```

This absorbs `OutOfMemoryError` and `StackOverflowError` alongside ordinary domain exceptions, logs a message that itself may need to allocate, and returns a value that lets the caller believe the batch was legitimately empty.

**Right**

```java
BigDecimal settleBatch(List<Reservation> batch) {
    try {
        return quizEngineSettle(batch);
    } catch (RuntimeException e) {
        log.error("settlement failed for batch of {} reservations", batch.size(), e);
        throw e;
    }
}
```

Catch the narrowest type the call site can reason about; reserve `catch (Throwable t)` for a single top-level thread or executor boundary, and only paired with a re-raise.

**Why people believe it:** "catch the widest type" reads as maximal defensiveness, and the difference only shows up under conditions (heap exhaustion, deep recursion) that a normal test suite never exercises.

---

## Cheat sheet

| Situation | Rule |
|---|---|
| Any `catch` block | Must rethrow, wrap-and-rethrow, or log the throwable itself — never `.getMessage()` alone, never nothing |
| Logging a caught exception | Trailing `Throwable` argument, e.g. `log.error("stake reservation failed for round {}", roundId, e)` — never string-concatenate `e.getMessage()` |
| `catch (InterruptedException e)` | Restore (`Thread.currentThread().interrupt()`) or propagate — never discard |
| `catch (Throwable t)` | Legitimate only at a top-level thread/executor boundary, and only with a re-raise |
| `catch (Error e)` or a specific `Error` subtype | Same rule as `Throwable` — don't, except the same top-level boundary |
| Shutdown hook triggers | Last non-daemon thread exits, `System.exit`, SIGTERM/SIGINT |
| Shutdown hook does NOT trigger | `Runtime.halt`, `kill -9`, JVM crash |
| Uncaught-handler resolution order | Thread's own handler → `ThreadGroup` → JVM default → `System.err` |
| `execute(Runnable)` throws | Reaches the uncaught-exception handler |
| `submit(Callable)` throws | Captured silently inside the `Future`; surfaces only on `.get()`/`.join()` |
| Helpful NPE on/off | On by default since Java **15** (JDK-8233014); opt-in flag `-XX:+ShowCodeDetailsInExceptionMessages` was Java **14** only |
| Helpful NPE field/method name | Always available (constant pool) |
| Helpful NPE local variable name | Needs `-g` or `-g:vars`; otherwise `<localN>` |

---

## Self-test

**Q1.** What is wrong with `catch (Exception e) { log.error("payment failed: " + e.getMessage()); }`, given that it does log something?

<details><summary>Answer</summary>

It is functionally an empty catch with a misleading appearance of handling. `getMessage()` returns only the exception's own message string — for a hand-thrown exception that might be informative, but for a `NullPointerException` with no explicit message it is `null`, and string concatenation turns that into the literal text `"null"`, so the log line reads `payment failed: null` with no indication of what was null or where. Worse, the stack trace and the entire `Caused by:` chain are gone — nothing in this log line lets an on-call engineer find the actual failing line. The fix is to pass the throwable itself as a trailing argument to the logger (`log.error("payment failed for round {}", roundId, e)`), which SLF4J recognizes specially and prints in full underneath the formatted message, independent of how many `{}` placeholders the message has.

</details>

**Q2.** A `PaymentRun` worker thread does `try { queue.take(); } catch (InterruptedException e) { }` inside its main loop. What breaks, mechanically?

<details><summary>Answer</summary>

Interruption in Java is a single boolean flag on the `Thread`. `BlockingQueue.take()` polls that flag while blocked, and when it sees it set, it throws `InterruptedException` and clears the flag back to `false` as part of throwing. An empty catch means that clearing is never undone — nothing restores or re-signals it — so `Thread.currentThread().isInterrupted()` reads `false` immediately afterward, exactly as if the interrupt had never happened. The loop's exit condition, if it checks the flag, never trips, and a graceful-shutdown request or `shutdownNow()` on the owning `ExecutorService` is silently ignored. The fix is `Thread.currentThread().interrupt()` followed by `return` (or `break`) in the catch block, which restores the flag before the method returns so any code downstream that checks it later still sees the truth.

</details>

**Q3.** A task submitted with `submit` throws an unchecked exception and nobody calls `.get()` on the returned `Future`. Where does the exception go?

<details><summary>Answer</summary>

Nowhere visible. `submit(Callable)` wraps the task in a `FutureTask`, which catches whatever the task throws and stores it inside the `Future` rather than letting it propagate out of the pooled worker thread's `run()` loop. Because it never reaches the top of the worker thread's stack, it never reaches any `Thread.UncaughtExceptionHandler` — not the thread's own, not the `ThreadGroup`'s, not the JVM default — and nothing is printed to `System.err`. Measured on JDK 21.0.7: submitting a task that throws produces zero output at the point of submission, and the exception only surfaces, wrapped in `ExecutionException`, when `future.get()` is eventually called. This is in direct contrast to `execute(Runnable)`, which has no `Future` to absorb the exception, so a thrown exception there propagates out of the worker thread and does reach the registered uncaught-exception handler. A batch of `PaymentRun` items dispatched with `submit` and never checked can fail completely silently.

</details>

**Q4.** Name the one legitimate place to write `catch (Throwable t)`, and what the catch block must do to remain legitimate.

<details><summary>Answer</summary>

A top-level thread or executor-task boundary — the outermost frame of a `Runnable` run on a long-lived thread, or a task in an executor, where the alternative to catching is the process's own default handling of an uncaught exception on that thread. To remain legitimate the block must log the throwable (with the full object, not `.getMessage()`) and then re-raise it — `throw t;` or an equivalent — rather than swallow it and let the thread continue. Catching without re-raising turns a potentially fatal condition (`OutOfMemoryError`, `StackOverflowError`) into a silently degraded worker that keeps accepting work it may no longer be able to execute safely, and can hand corrupted shared state (a batch buffer mutated halfway through a `StackOverflowError`) to whatever runs next on that thread or in that pool.

</details>

**Q5.** Is `-XX:+ShowCodeDetailsInExceptionMessages` required to get a helpful NullPointerException message on Java 21? What was true on Java 14?

<details><summary>Answer</summary>

No — on Java 21 (and every version from 15 onward) it is on by default; measured on this machine's Oracle JDK 21.0.7 via `-XX:+PrintFlagsFinal -version`: `bool ShowCodeDetailsInExceptionMessages = true {manageable} {default}`. On Java 14, where JEP 358 first shipped, the feature was opt-in and required exactly that flag to be passed explicitly — it defaulted to off. The switch to on-by-default happened in Java 15, tracked by JDK-8233014. The reason this is still asked and still gets answered wrong is that much of the writing describing JEP 358 dates from when Java 14 was current and the flag genuinely was required; that writing predates the Java 15 default flip and was never updated.

</details>

**Q6.** A helpful NPE message reads `Cannot invoke "NpeLocal$Reservation.split()" because "<local2>" is null` instead of naming the variable. What happened, and does it mean the feature is broken?

<details><summary>Answer</summary>

Not broken — the class was compiled without local-variable debug information (`javac -g:none`, or a build pipeline that strips it for a smaller production artifact). The message's field and method names come from the constant pool, which is always present regardless of compiler flags, so `Reservation.split()` is still correctly named. The local variable's *source name*, though, is only recorded in the class file's local-variable table when compiled with `-g` or `-g:vars`; without it, the JVM falls back to the raw stack-slot identifier, `<local2>`. Measured on JDK 21.0.7: identical source, compiled twice, produced `"reservation" is null` with `-g` and `"<local2>" is null` with `-g:none`. The fix, where readable stack traces matter, is to keep at least `-g:vars` in the build used for anything a human will debug from.

</details>

**Q7.** What triggers a registered shutdown hook, and what specifically does not?

<details><summary>Answer</summary>

Triggers it: the last non-daemon thread exiting normally, an explicit `System.exit(int)` (or `Runtime.exit(int)`) call, and receiving SIGTERM or SIGINT (an operator's Ctrl-C, a `kill` without `-9`, or an orchestrator's graceful-stop signal) — all of these are "orderly" shutdown paths as far as the JVM is concerned. Does not trigger it: `Runtime.getRuntime().halt(int)`, which is documented to terminate immediately without running hooks or finalizers; `kill -9` (SIGKILL), which the OS delivers in a way the JVM cannot intercept at all; and a JVM crash such as a native fault. Measured on JDK 21.0.7: identical hook registration, `System.exit(0)` printed the hook's line, `Runtime.getRuntime().halt(0)` printed nothing after the halt call.

</details>

**Q8.** Rank these four responses to a caught exception from worst to best, and say when each is correct: swallow, log-only, log-and-rethrow, rethrow-translated.

<details><summary>Answer</summary>

Swallow is never correct in application code — it discards the failure entirely, whether via an empty body or via `.getMessage()` concatenation. Log-and-rethrow is next-worst in practice, not because logging is wrong but because doing it at every layer that happens to catch and rethrow the same exception duplicates the same log line at every one of those layers; it is correct only at exactly one layer, chosen deliberately, per the "log or rethrow, never both" rule (in full, `02d-logging-and-api-boundaries.md`). Log-only (log, then genuinely continue with a fallback) is correct only when the caller truly has a sensible fallback and the log is meant to be the sole permanent record of the failure — used as a substitute for handling, it degrades into swallowing further up the stack. Rethrow-translated — catching a narrow, lower-level exception and throwing a new, caller-appropriate one with the original chained as the cause — is the ordinary idiomatic shape for crossing an abstraction boundary (a `LedgerImbalanceException` becoming a `RestrictedActionException`) and is correct by default whenever the caller's vocabulary differs from the callee's.

</details>

---

## Open questions

None.

---

**Leaves covered:** 1.20.18, 1.20.19, 1.20.20, 1.20.22, 1.20.23, 1.20.24 (6 leaves)
**Leaves deferred:** none
**Diagrams included:** none
**Target version:** Java 21 LTS
**Lines:** 599
