# 05 Multithreading and Concurrency — Hedging and deadlines — BUILD IT (§4.7, leaves 4.7.3–4.7.4)

**Target version: Java 21 LTS.** | **Part 4 of 5** | [Index](../00-index.md)
Previous: [Structured concurrency from scratch](07-structured-concurrency-from-scratch.md) · Next: [A minimal CompletableFuture](07c-a-minimal-completablefuture.md)

File `07` built `MiniScope` — a join point with a guest list, owner-thread and LIFO enforced — and
`ShutdownOnFailureScope`, which cancels the rest of the fan-out on the first failure. This file
keeps the same shapes and field names (`ownerThread`, `carrierExecutor`, `carrierFutures`) and adds
two more policies: shutdown-on-success for hedged requests, and a deadline.

## v3 — shutdown-on-success (hedging)

### Mental model

Where shutdown-on-failure races two *different* calls and needs both, shutdown-on-success races two
or more *equivalent* calls and needs only the fastest. The identity vendor has a p50 of 900ms but a
p99 of 38 seconds — a client stuck behind a slow vendor instance benefits from firing a second,
identical verification request after a short delay and taking whichever answer lands first,
cancelling the loser. This is hedging, not retrying: both requests are in flight simultaneously (or
staggered by a small delay), not sequential.

### Why it exists

A naive retry-after-timeout waits out the full 38-second p99 before trying again, doubling worst-case
latency to 76 seconds. A naive "just always send two requests" doubles load on the identity vendor
for every request, including the 50% that would have been fast anyway. Shutdown-on-success gives you
the tail-latency win of racing without waiting for the timeout, and — combined with a short hedge
delay — spends the extra vendor call only on the requests that are actually running slow.

### When to reach for it, and when not

Reach for it only when the operation is **idempotent and side-effect-free to duplicate** — a read
(identity verification is a query against the vendor, not a mutation) is safe to hedge; a
`FundsLedger` stake reservation is not, because two concurrent reservations against the same
applicant would double-reserve funds. Do not hedge anything that writes state unless the write
itself is idempotent under a stable key (an `IdempotencyKey`-guarded operation, covered in the
payments notes) — otherwise hedging silently turns "at most once" into "at least once, maybe
twice, with money involved."

### How it works

Same fork/track shape as `ShutdownOnFailureScope`, inverted: the first `Success` recorded wins,
cancels every other in-flight carrier, and `join()` exposes that winning result directly instead of
requiring the caller to inspect each `Subtask`.

### Code

```java
public final class ShutdownOnSuccessScope<T> implements AutoCloseable {

    private final Thread ownerThread = Thread.currentThread();
    private final ExecutorService carrierExecutor =
        Executors.newVirtualThreadPerTaskExecutor();
    private final List<Future<?>> carrierFutures = new CopyOnWriteArrayList<>();
    private final AtomicReference<T> winningResult = new AtomicReference<>();
    private final AtomicReference<Throwable> lastFailure = new AtomicReference<>();
    private final CountDownLatch resolved = new CountDownLatch(1);

    public void fork(Callable<T> task) {
        if (Thread.currentThread() != ownerThread) {
            throw new MiniScope.WrongThreadException("fork() called off owner thread");
        }
        Future<?> carrier = carrierExecutor.submit(() -> {
            try {
                T result = task.call();
                if (winningResult.compareAndSet(null, result)) {
                    resolved.countDown();
                    cancelAllOtherCarriers();
                }
            } catch (Throwable t) {
                lastFailure.compareAndSet(null, t);
            }
        });
        carrierFutures.add(carrier);
    }

    private void cancelAllOtherCarriers() {
        for (Future<?> carrier : carrierFutures) {
            carrier.cancel(true);
        }
    }

    public T join() throws InterruptedException, ExecutionException {
        resolved.await();
        T result = winningResult.get();
        if (result == null) {
            throw new ExecutionException(
                "All hedged attempts failed", lastFailure.get());
        }
        return result;
    }

    @Override
    public void close() {
        for (Future<?> carrier : carrierFutures) {
            carrier.cancel(true);
        }
        carrierExecutor.shutdown();
    }
}
```

Usage — hedge the identity vendor call after a 500ms stagger, because its p50 is 900ms and a call
still unanswered at 500ms is already trending toward the long tail:

```java
try (var hedge = new ShutdownOnSuccessScope<IdentityVerdict>()) {
    hedge.fork(() -> identityVendorClient.verify(applicationId));
    Thread.sleep(Duration.ofMillis(500));
    hedge.fork(() -> identityVendorClient.verify(applicationId));
    return hedge.join();
}
```

**Invariant.** `winningResult` is written at most once — `compareAndSet(null, result)` guarantees
that a second, slower success arriving after the race has already been decided cannot overwrite the
first winner, and `resolved` is counted down exactly once, on the winning path only, so `join()`
never returns before a real success (or every attempt failing) has actually happened.

**Cost.** The 500ms stagger is a real vendor call, not free — hedging a genuinely slow vendor at
its true p99 tail buys you the p50 latency at the cost of roughly one extra call for every request
whose first attempt runs past the stagger window. At 600/min estate-wide cap on the identity
vendor, a hedge policy has to be sized against that cap, not just against latency goals.

**Diff from the JDK's `StructuredTaskScope.ShutdownOnSuccess`.** The real one's `result()` throws
`IllegalStateException` if called before `join()`, and `NoSuchElementException` (via its `Joiner`)
if every subtask failed with no result recorded — a distinction this file collapses into a single
`ExecutionException` for brevity.

**Interview:** "difference between hedging and a plain retry?" — a retry is sequential and pays the
first attempt's full timeout before trying again; a hedge starts the second attempt while the first
is still running (often after a short stagger, not zero), so the caller's latency is bounded by
whichever attempt finishes first, not by the sum of a failed attempt plus a fresh one.

## v4 — a deadline, and the honest limitation

### Mental model

A deadline is `join()`'s cousin: instead of "wait until every subtask finishes," it's "wait until
every subtask finishes, or until this instant, whichever comes first." What happens to subtasks
still running when the deadline hits is the entire content of this section — and the honest answer
is: they get an interrupt request, nothing more.

### Why it exists

The watchlist provider carries a p99 of 25 seconds against its own declared 30-second timeout. If
`AssessmentService` has an SLA of, say, 5 seconds to return *some* answer to the caller (even a
"pending" status), a plain `join()` that waits for the vendor's full timeout blows that SLA on every
slow request. `joinUntil` lets the scope give up on waiting without giving up on trying to stop the
work.

### `[PROVE]` — the deadline is enforced only as far as interruption reaches

Walk the mechanism, not the claim. `joinUntil(Instant deadline)` computes a remaining duration and
calls the same `Future.get(long, TimeUnit)` overload used everywhere else, then — on timeout —
calls `cancel(true)` on every still-running carrier, exactly like `close()` does. `cancel(true)`'s
documented effect (`Future` javadoc) is: "if the thread executing this task ... should be
interrupted in an attempt to stop the task." *Attempt* is the JDK's own word. Interruption is
cooperative — it sets a flag and, for threads parked in an interruptible wait, throws
`InterruptedException` at the next such point. A subtask whose body is a tight CPU loop with no
`Thread.interrupted()` check, or whose body calls a non-interruptible native operation, observes
nothing. It keeps running.

So: `joinUntil` returning at the deadline is a guarantee about the **owner thread's** wait —
the owner thread genuinely stops waiting at the deadline — but it is not a guarantee about the
**subtask's** execution. Those are two different threads, and the deadline only controls the first
one directly. The second one is only *asked*.

```java
public T joinUntil(Instant deadline) throws InterruptedException, TimeoutException {
    Duration remaining = Duration.between(Instant.now(), deadline);
    if (remaining.isNegative()) {
        cancelAll();
        throw new TimeoutException("Deadline already passed");
    }
    try {
        return future.get(remaining.toNanos(), TimeUnit.NANOSECONDS);
    } catch (java.util.concurrent.TimeoutException e) {
        cancelAll(); // best-effort: requests interruption, does not confirm it
        throw new TimeoutException(
            "Deadline exceeded; interruption requested but not confirmed");
    } catch (ExecutionException e) {
        throw new RuntimeException(e.getCause());
    }
}

private void cancelAll() {
    for (Future<?> carrier : carrierFutures) {
        carrier.cancel(true);
    }
}
```

Proof this is not merely theoretical — a subtask that ignores interruption on purpose, run against
this exact `joinUntil`:

```java
try (var hedge = new ShutdownOnSuccessScope<String>()) {
    hedge.fork(() -> {
        long busyUntil = System.nanoTime() + Duration.ofSeconds(3).toNanos();
        while (System.nanoTime() < busyUntil) {
            // deliberately never checks Thread.interrupted() — models a
            // watchlist client wrapping a non-interruptible native call
        }
        return "watchlist-result-ignoring-interrupt";
    });
    try {
        String result = hedge.joinUntil(Instant.now().plusMillis(200));
        System.out.println("returned within deadline: " + result);
    } catch (TimeoutException e) {
        System.out.println("joinUntil returned at 200ms as promised: " + e.getMessage());
        // but the fork()'d task is still spinning for another ~2.8 seconds —
        // cancel(true) set its interrupt flag; the busy-loop never reads it.
    }
}
```

Running this: `joinUntil` throws `TimeoutException` at 200ms, on schedule. The forked task keeps
consuming a virtual thread's carrier for the remaining ~2.8 seconds regardless, because nothing in
its loop body ever observes the interrupt. That is the proof: the deadline bounds the owner
thread's wait exactly; it bounds the subtask's execution only if the subtask's code cooperates.

![D-208 — MiniScope's lifetime rules](../diagrams/D-208-miniscope-lifetime.svg)

**D-208** — `MiniScope`'s lifetime rules, re-embedded here because this is the file that proves the
diagram's printed caveat: a deadline cannot stop a subtask that ignores interruption. The join-then-close
edges in the diagram assume every subtask is well-behaved; this section is what happens when one
isn't.

**Pitfall:** treating `joinUntil` returning (successfully or via `TimeoutException`) as proof the
work has stopped, and proceeding to reuse a resource the subtask still holds — e.g., releasing a
connection-pool slot the still-running watchlist call is using, because the deadline said "done."
The fix is not a better deadline API — no deadline API can fix a callee that ignores interruption.
The fix is upstream: only pass deadlines through call chains that are themselves built to check
`Thread.interrupted()` at every blocking point, and treat any client library that wraps a
non-interruptible call (a raw JDBC driver call, some native crypto calls) as one that cannot be
safely deadline-bounded without a wrapping timeout at the I/O layer itself (a socket read timeout,
not a thread interrupt).

## Pitfalls

### Believing `TimeoutException` from `joinUntil` means the subtask is gone

**Wrong**

```java
try (var hedge = new ShutdownOnSuccessScope<ScreeningVerdict>()) {
    hedge.fork(() -> watchlistProvider.screen(applicantName));
    try {
        return hedge.joinUntil(Instant.now().plusSeconds(5));
    } catch (TimeoutException e) {
        releasePooledHttpConnection(); // assumes the call is finished; it may not be
        return ScreeningVerdict.pending();
    }
}
```

**Right** — release nothing the subtask might still be touching. Let `close()` (already called by
try-with-resources) issue the cancellation request, and have the watchlist client itself own its
connection lifecycle so a stuck call eventually times out at the socket layer independent of
whether the interrupt was ever observed.

**Why people believe it:** a deadline API that returns feels final, the same way a method call
returning normally usually means its side effects are complete. `joinUntil` breaks that intuition on
purpose — it is a promise about the *owner thread's wait*, not about the *subtask's completion*.

## Cheat sheet

| Policy | Wins on | Cancels | Failure surfaced as |
|---|---|---|---|
| `ShutdownOnFailureScope` (file `07`) | N/A — waits for all unless one fails | The rest, on first failure | `throwIfFailed()` after `join()` |
| `ShutdownOnSuccessScope` | First `Success` | The rest, on first success | `ExecutionException` from `join()` if all fail |
| `joinUntil(deadline)` | N/A — a time bound, not an outcome | Requests interruption on timeout | `TimeoutException`, subtask state unknown |

| Deadline claim | True? |
|---|---|
| Owner thread stops waiting at the deadline | Yes, exactly |
| Subtask is guaranteed stopped by the deadline | No — only if it checks interruption |
| `cancel(true)` forcibly halts a thread | No — it requests, via interrupt |
| A busy-loop with no interrupt check can be deadline-bounded | No |

## Self-test

**Q1.** Why must the hedge's second `fork()` in the usage example be staggered by `Thread.sleep`
rather than fired at the same instant as the first?

<details><summary>Answer</summary>

Firing both at once doubles vendor load on every single request, including the 50% that would have
returned in well under 900ms anyway. A stagger only spends the second call on requests where the
first attempt is already running long enough to suggest it's heading for the tail, which is the
entire economic case for hedging over duplicating.

</details>

**Q2.** In `ShutdownOnSuccessScope`, what would go wrong if `winningResult.compareAndSet(null,
result)` were replaced with a plain `winningResult.set(result)`?

<details><summary>Answer</summary>

Two carriers could both succeed near-simultaneously. With a plain `set`, both would write, both
would call `resolved.countDown()` (which is harmless, since `CountDownLatch` only counts down once
functionally past zero) but both would also call `cancelAllOtherCarriers()`, and — more seriously —
the final value in `winningResult` would be whichever write happened to land last, which is a race,
not "first success wins." `compareAndSet` makes the first writer the permanent winner.

</details>

**Q3.** `joinUntil` throws `TimeoutException` at the deadline. What, precisely, has and has not been
guaranteed to have happened at that point?

<details><summary>Answer</summary>

Guaranteed: the owner thread's wait ended at (or after) the deadline, and `cancel(true)` was called
on every still-tracked carrier, which sets each carrier thread's interrupt flag. Not guaranteed: that
any carrier thread has actually stopped running, released any resource it held, or even checked its
interrupt flag at all — that depends entirely on whether the subtask's own code cooperates with
interruption.

</details>

**Q4.** Why is hedging safe for the identity-verification read but unsafe for a `FundsLedger` stake
reservation, in the same `AssessmentService` request path?

<details><summary>Answer</summary>

Identity verification is a query with no side effect on the vendor or on our own state — running it
twice and discarding the loser changes nothing. A stake reservation moves money from available to
reserved buckets; forking it twice would attempt to reserve the same funds twice, and cancelling the
"loser" after the fact does not undo a reservation that may have already committed on the ledger
side. Hedging requires idempotence or side-effect-free reads; it is not a general-purpose latency
trick.

</details>

**Q5.** The proof code's busy-loop subtask keeps running for ~2.8 seconds after `joinUntil` throws
at 200ms. What single change to that subtask's body would make the deadline actually bound its
execution?

<details><summary>Answer</summary>

Add an interruption check inside the loop condition — e.g. `while (System.nanoTime() < busyUntil &&
!Thread.currentThread().isInterrupted())` — so the loop observes the flag `cancel(true)` sets and
exits promptly. The deadline mechanism was never broken; the subtask's refusal to cooperate was
the entire cause of the mismatch.

</details>

**Q6.** Why does `cancelAll()` in `joinUntil`'s timeout branch not simply block until every carrier
has confirmed it stopped, removing the ambiguity this file spends so much effort explaining?

<details><summary>Answer</summary>

Blocking until every carrier confirms it stopped would require the exact same trust in cooperative
interruption this file shows cannot be assumed — a non-cooperating subtask would make that wait
unbounded too, defeating the entire point of having a deadline. There is no safe bound to wait for
"confirmed stopped" without either trusting cooperation (which may not hold) or adding a second,
outer forceful-kill mechanism the JVM does not provide for arbitrary running code (`Thread.stop` was
removed in Java 20 precisely because forceful kill is unsafe).

</details>

---

**Leaves covered:** 4.7.3–4.7.4 (2 leaves)
**Leaves deferred:** none
**Diagrams included:** D-208
**Target version:** Java 21 LTS
**Lines:** 369
