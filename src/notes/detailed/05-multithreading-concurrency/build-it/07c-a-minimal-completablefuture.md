# 05 Multithreading and Concurrency — A minimal CompletableFuture — BUILD IT (§4.7, leaves 4.7.5–4.7.6)

**Target version: Java 21 LTS.** | **Part 4 of 5** | [Index](../00-index.md)
Previous: [Hedging and deadlines](07b-hedging-and-deadlines.md) · Next: [The visibility and lost-update harnesses](08-visibility-and-lost-update.md)

`MiniScope` and its policy variants (files `07`, `07b`) are about **structure** — every subtask is
owned, tracked, and bounded by an enclosing block. `CompletableFuture` predates structured
concurrency by a decade and solves a different problem: composing async results with callbacks,
with no enclosing block at all — a value that arrives later, and a chain of transformations to run
once it does. This file builds the minimal version of that machinery: `MiniFuture`.

## v1 — the core: a volatile result slot and a Treiber stack of callbacks

### Mental model

A `MiniFuture<T>` is a **postbox with a notice board**. Before the value arrives, the postbox is
empty and the notice board holds a list of people to notify. The moment a value is dropped in the
box, everyone on the notice board is called, in whatever order they can be reached, and anyone who
signs up *after* the value has already arrived gets called immediately instead of being added to a
now-useless board.

### Why it exists

Before `CompletableFuture` (Java 8), `Future<T>` had `get()` and nothing else — no way to attach a
callback, no way to compose two async results, no way to complete a future from arbitrary code
rather than only from the task that created it. Every "when this finishes, then do that" had to be
hand-rolled with `wait`/`notify` or a listener interface reinvented per call site. `CompletableFuture`
made a single, composable interface where the result is a first-class value.

### When to reach for it, and when not

Reach for `CompletableFuture` (the real one, in production) for composing independent or
dependent async calls without an enclosing scope block — a `NotificationService` dispatch that
fires-and-forgets a delivery attempt and separately logs its outcome via `whenComplete`, with no
caller waiting synchronously. Reach for `StructuredTaskScope` instead when the caller genuinely
needs to wait for the result before proceeding and wants cancellation propagation and thread-dump
visibility — `AssessmentService`'s two-vendor fan-out in files `07`/`07b` is exactly that case, which
is why it was built on `MiniScope`, not on futures. The two are not competitors; `CompletableFuture`
composes, structured concurrency bounds.

### How it works

Three fields carry the whole design. `volatile Object result` holds one of three shapes: `null`
sentinel object `UNSET` meaning "not yet complete" (a real `null` result value is wrapped so it is
distinguishable from "unset"), the actual result value, or an `AltResult` wrapping a `Throwable` for
a failed completion. `volatile Completion stack` is the head of a **Treiber stack** (from file `04`
— a lock-free singly-linked stack via CAS on the head pointer) of pending callback nodes. `complete`
CASes `result` from `UNSET` to the real value, then walks and fires the stack.

```java
public class MiniFuture<T> {

    private static final Object UNSET = new Object();

    private record AltResult(Throwable cause) {}

    private static final VarHandle RESULT;
    private static final VarHandle STACK;
    static {
        try {
            RESULT = MethodHandles.lookup()
                .findVarHandle(MiniFuture.class, "result", Object.class);
            STACK = MethodHandles.lookup()
                .findVarHandle(MiniFuture.class, "stack", Completion.class);
        } catch (ReflectiveOperationException e) {
            throw new ExceptionInInitializerError(e);
        }
    }

    private volatile Object result = UNSET;
    private volatile Completion stack;

    private abstract static class Completion {
        volatile Completion next;
        abstract void run();
    }

    public boolean complete(T value) {
        boolean did = RESULT.compareAndSet(this, UNSET, value == null ? new AltResult(null) : value);
        if (did) {
            postComplete();
        }
        return did;
    }

    public boolean completeExceptionally(Throwable cause) {
        boolean did = RESULT.compareAndSet(this, UNSET, new AltResult(cause));
        if (did) {
            postComplete();
        }
        return did;
    }

    public boolean isDone() {
        return result != UNSET;
    }

    @SuppressWarnings("unchecked")
    public T join() {
        Object r = result;
        while (r == UNSET) {
            Thread.onSpinWait();
            r = result;
        }
        if (r instanceof AltResult alt) {
            throw (alt.cause() instanceof RuntimeException re)
                ? re
                : new CompletionException(alt.cause());
        }
        return r == PRESENT_NULL ? null : (T) r;
    }

    private static final Object PRESENT_NULL = new Object();

    private void pushCompletion(Completion node) {
        Completion existingHead;
        do {
            existingHead = stack;
            node.next = existingHead;
        } while (!STACK.compareAndSet(this, existingHead, node));
        if (result != UNSET) {
            postComplete();
        }
    }

    private void postComplete() {
        Completion node = (Completion) STACK.getAndSet(this, null);
        while (node != null) {
            Completion next = node.next;
            node.next = null;
            node.run();
            node = next;
        }
    }
}
```

**`join()`'s spin-wait is a simplification, said outright.** The real `CompletableFuture` parks the
waiting thread (`LockSupport.park`) after a bounded number of spins rather than spinning forever —
spinning is only shown here because it makes the `volatile` read/write happens-before relationship
the whole mechanism depends on visible without introducing a second synchronization primitive.
Production code must never spin-wait on a future this way; it burns a core for the entire wait.

**Invariant.** `result` transitions exactly once, from `UNSET` to a terminal value — the
`compareAndSet` in both `complete` and `completeExceptionally` is the single-writer gate, so calling
`complete` twice (or `complete` then `completeExceptionally`) is safe: the second call's CAS fails
and returns `false`, per the real API's documented "returns `true` only if this invocation caused
this to transition."

**Cost.** The `AltResult` wrapper for a `null` completion value and for exceptions means every read
of `result` pays a type check (`instanceof AltResult`) even on the hot, successful path — a small,
constant cost the real JDK implementation makes too, for the same reason: `Object result` cannot
otherwise distinguish "unset," "successfully completed with `null`," and "failed."

## v2 — `postComplete` and the recursion-unrolling `[PROVE]`

### `[PROVE]` — why `postComplete` is a loop, not recursion

The naive way to fire a stack of callbacks is recursive: each `Completion.run()` calls the next
one directly. Walk what that costs. Every `thenApply` chained onto a future pushes one more
`Completion` onto the stack; a chain of `f.thenApply(a).thenApply(b).thenApply(c)...` a thousand
deep, then completed, would — if `run()` called `next.run()` from inside itself — build a call stack
a thousand frames deep for something that is logically a flat sequence of independent
transformations. Push that to ten thousand steps (not unreasonable for, say, a generated batch
pipeline stitching together per-item transforms) and it overflows `StackOverflowError` — a `Fatal`
failure for work that did no recursion in the domain sense at all, only in the implementation's
accident of using function calls to walk a list.

The fix in `postComplete` above is iterative: `STACK.getAndSet(this, null)` atomically detaches the
whole list in one step (so concurrent `pushCompletion` calls racing with completion see either the
full pre-detachment stack or start a fresh one — never a partially-detached one), then a `while`
loop walks it node by node, calling `run()` on each without any node's `run()` needing to invoke the
next. Each `run()` may itself call `postComplete()` on a *different* `MiniFuture` (the one returned
by `thenApply`, whose own completion may have its own waiting callbacks) — but that is a fresh call
with its own loop, not a recursive descent into the same stack. The proof that this actually bounds
stack depth: trace `thenApply`'s implementation below and see that `run()` calls
`downstream.complete(...)`, and `complete` calls `postComplete` on `downstream`, which is a
**sibling call**, not a nested return address on the original `postComplete`'s frame — the depth
added per link in the chain is O(1) stack frames that unwind before the next link's `postComplete`
begins, not O(n) accumulated frames.

### `thenApply`, `thenCompose`, `whenComplete`

```java
public <U> MiniFuture<U> thenApply(Function<? super T, ? extends U> fn) {
    MiniFuture<U> downstream = new MiniFuture<>();
    pushCompletion(new Completion() {
        @Override
        void run() {
            try {
                T upstreamValue = MiniFuture.this.join();
                downstream.complete(fn.apply(upstreamValue));
            } catch (Throwable t) {
                downstream.completeExceptionally(t);
            }
        }
    });
    return downstream;
}

public <U> MiniFuture<U> thenCompose(Function<? super T, ? extends MiniFuture<U>> fn) {
    MiniFuture<U> downstream = new MiniFuture<>();
    pushCompletion(new Completion() {
        @Override
        void run() {
            try {
                T upstreamValue = MiniFuture.this.join();
                MiniFuture<U> inner = fn.apply(upstreamValue);
                inner.pushCompletion(new Completion() {
                    @Override
                    void run() {
                        try {
                            downstream.complete(inner.join());
                        } catch (Throwable t) {
                            downstream.completeExceptionally(t);
                        }
                    }
                });
            } catch (Throwable t) {
                downstream.completeExceptionally(t);
            }
        }
    });
    return downstream;
}

public MiniFuture<T> whenComplete(BiConsumer<? super T, ? super Throwable> action) {
    MiniFuture<T> downstream = new MiniFuture<>();
    pushCompletion(new Completion() {
        @Override
        void run() {
            Object r = MiniFuture.this.result;
            T value = null;
            Throwable failure = null;
            if (r instanceof AltResult alt) {
                failure = alt.cause();
            } else {
                @SuppressWarnings("unchecked")
                T cast = (r == PRESENT_NULL) ? null : (T) r;
                value = cast;
            }
            try {
                action.accept(value, failure);
            } finally {
                if (failure != null) {
                    downstream.completeExceptionally(failure);
                } else {
                    downstream.complete(value);
                }
            }
        }
    });
    return downstream;
}
```

Usage — the `AssessmentService` deriving a limit proposal only once wealth scoring completes,
logging the outcome regardless of how it resolves:

```java
MiniFuture<WealthVerdict> wealthScoreFuture = scoreWealth(applicationId);

MiniFuture<LimitSet> limitProposalFuture = wealthScoreFuture
    .thenApply(verdict -> deriveLimitProposal(verdict))
    .whenComplete((limits, failure) -> {
        if (failure != null) {
            auditLog.record(applicationId, "limit-derivation-failed", failure);
        } else {
            auditLog.record(applicationId, "limit-derivation-succeeded", limits);
        }
    });
```

**Invariant.** `pushCompletion` re-checks `result != UNSET` after CASing the node onto the stack —
this closes the race where `complete` runs its `postComplete` (finding an empty stack) *between*
the CAS that publishes a `Completion` and that same push seeing `UNSET`. Without the re-check, a
callback registered a few nanoseconds after completion could be pushed onto a stack that will never
be walked again, and would simply never fire.

**Cost.** Every `thenApply`/`thenCompose` allocates a new `MiniFuture` and a new `Completion`
instance — a chain of ten transformations is ten heap allocations before any of them run. The real
`CompletableFuture` amortizes some of this via `minimalCompletionStage()` variants that skip
building a full mutable future when the caller only needs a read-only view, which this file does
not implement.

**Pitfall:** assuming `whenComplete`'s action running means the *downstream* future it returns is
already resolved from the caller's perspective. `whenComplete` returns a *new* `MiniFuture<T>` that
completes only after `action` finishes running — chaining another `.thenApply` off the original
`wealthScoreFuture` instead of off `whenComplete`'s return value silently skips waiting on the
logging step, which matters if a caller depends on side effects (like the audit write above)
happening-before the next stage.

## Diff table — `MiniFuture` versus the real APIs

| Concern | `MiniFuture` (this file) | `CompletableFuture` | `StructuredTaskScope` (JEP 505, 5th preview) |
|---|---|---|---|
| Thread tracking | None | None (callbacks run on completing thread or supplied executor) | `ThreadFlock` — JDK-internal, tracks every forked thread |
| Diagnostics | None | None beyond stack traces | JSON thread-dump integration — forked threads appear under the owning scope in `jcmd Thread.dump_to_file` |
| Structural violation | Not applicable — no scope | Not applicable | `StructureViolationException` on out-of-order close, or a thread outliving its scope |
| Scoped-value inheritance | Plain field capture in lambdas | Inherits nothing automatically; must pass explicitly | Automatic across the fork boundary — `ScopedValue` bindings on the owner thread are visible to forked threads (JEP 506, final in JDK 25) |
| Cancellation | None implemented | `cancel()` marks the future cancelled; does not interrupt a running stage unless `mayInterruptIfRunning` and the stage checks | Interrupt request via `Joiner`-driven cancellation on scope exit |
| Failure model | `AltResult` wrapper, thrown as `CompletionException` from `join()` | Same `AltResult`/`NIL`-style internal sentinel (JDK source uses `AltResult` and a `NIL` singleton for `null`) | Configurable via `Joiner` — `awaitAllSuccessfulOrThrow`, `anySuccessfulResultOrThrow`, custom |
| Combinator surface | `thenApply`, `thenCompose`, `whenComplete` — 3 methods | ~60 methods: `thenCombine`, `thenAcceptBoth`, `applyToEither`, `orTimeout`, `completeOnTimeout`, async variants of every combinator, `allOf`, `anyOf`, and more | N/A — different composition model entirely (fork/join, not chained callbacks) |
| Preview status on Java 21 | Not applicable (plain class) | Final since Java 8 | **Preview** — requires `--enable-preview`; API shape has changed across previews (JEP 428 → 437 → 453 → 480 → 499 → 505), so any snippet must state which preview it targets |
| Preview status on Java 25 | Not applicable | Final | Still preview (JEP 505, 5th iteration) — do not describe as final |
| Scoped values status on Java 25 | Not applicable | Not applicable | `ScopedValue` (JEP 506) is **final** in JDK 25 — do not conflate its finality with structured concurrency's continued preview status |

**Version note:** any `StructuredTaskScope` snippet run on Java 21 requires
`--enable-preview` at both compile and run time, and the class shape shown in this topic's earlier
`MiniScope` files is deliberately hand-rolled specifically so it needs no preview flag — the real
API's `fork`/`join`/`Joiner` surface was still being revised as of JDK 25's fifth preview and is not
safe to treat as stable.

## Pitfalls

### Assuming a `Completion` fires in the order it was registered

**Wrong**

```java
future.thenApply(v -> { log.info("first"); return v; });
future.thenApply(v -> { log.info("second"); return v; });
// assumes "first" logs before "second"
```

Both push onto the same Treiber stack via `pushCompletion`, and a Treiber stack is LIFO — the second
registration lands on top and is popped first by `postComplete`'s `while` loop. There is no
ordering guarantee between independently-registered callbacks on the same future, in this file or
in the real `CompletableFuture` (whose javadoc documents "no guarantees are made about the order").

**Right** — if two callbacks must run in a specific order, chain them: `future.thenRun(() ->
log.info("first")).thenRun(() -> log.info("second"))`, which makes the ordering an explicit data
dependency instead of an accident of stack-push order.

**Why people believe it:** registration code visually reads top-to-bottom, and most single-threaded
list-processing intuitions (like adding listeners to a `List`) do preserve insertion order — a
Treiber stack deliberately trades that guarantee for lock-freedom.

## Cheat sheet

| Field | Purpose |
|---|---|
| `volatile Object result` | `UNSET` sentinel, real value, `PRESENT_NULL` sentinel, or `AltResult(cause)` |
| `volatile Completion stack` | Treiber-stack head of pending callbacks |
| `complete` / `completeExceptionally` | CAS `result` from `UNSET`; single-writer gate |
| `postComplete` | `getAndSet(null)` to detach the whole stack, then iterate — not recurse |
| `pushCompletion` | CAS-push, then re-check `result != UNSET` to close the register-after-complete race |
| `thenApply` | Transform value, propagate failure unchanged |
| `thenCompose` | Flatten a `Function<T, MiniFuture<U>>` instead of nesting futures |
| `whenComplete` | Observe both outcomes; downstream mirrors upstream after the action runs |

## Self-test

**Q1.** Why does `postComplete` call `STACK.getAndSet(this, null)` instead of reading `stack` and
then setting it to `null` in two separate steps?

<details><summary>Answer</summary>

Two separate steps would race with a concurrent `pushCompletion`: a callback could be pushed onto
the stack between the read and the `null`-set, and then be silently discarded by the `null`-set
without ever having its `run()` called. `getAndSet` performs the read-and-clear atomically, so
every node that was on the stack at the instant of the swap is captured in the returned list, and
any node pushed after the swap sees a fresh, empty `stack` to build its own chain on (and, per
`pushCompletion`'s re-check, immediately triggers its own `postComplete` if the future is already
done).

</details>

**Q2.** Why is a chain of a thousand `thenApply` calls, once completed, not at risk of
`StackOverflowError` in this implementation, given that `run()` for one `Completion` does call into
another future's `complete`?

<details><summary>Answer</summary>

Because `complete` calling `postComplete` on the downstream future is a call that returns before the
outer `postComplete`'s loop advances to its next node — it is not a self-recursive call back into
the same stack-walking loop. Each link's `run()` → `complete()` → `postComplete()` sequence completes
and unwinds its own small, bounded stack depth before control returns to the calling loop, rather
than each link adding a permanent frame that stays on the stack until the very last link resolves.

</details>

**Q3.** Two threads call `future.thenApply(...)` at the same moment the future is being completed by
a third thread. Walk what `pushCompletion`'s re-check of `result != UNSET` actually prevents.

<details><summary>Answer</summary>

Without the re-check: a `Completion` could be CAS-pushed onto the stack a moment after the
completing thread's `postComplete` already ran and found the stack empty (because the completing
thread's CAS on `result` happened, and its `postComplete`'s `getAndSet` happened, both before the
push). That `Completion` would then sit on the stack forever with nothing scheduled to walk it
again. The re-check makes the pushing thread itself notice `result != UNSET` immediately after its
push and call `postComplete` itself, guaranteeing every registered callback either joins a walk
already in flight or triggers its own.

</details>

**Q4.** Why does `whenComplete`'s returned future need to be a distinct `MiniFuture<T>` rather than
just returning `this`?

<details><summary>Answer</summary>

Returning `this` would let a caller chain further stages off the *original* future, which resolves
the instant the original completes — before `action` has necessarily run. `AssessmentService`'s
audit-logging example depends on the log write happening before any dependent stage proceeds; a
distinct downstream future that only completes once `action.accept(...)` has finished running is
what makes that ordering an actual guarantee instead of a coincidence of timing.

</details>

**Q5.** Structured concurrency and scoped values are both discussed in this note set. Which one is
final in Java 25, and which is still preview — and why does this file insist on keeping them
separate?

<details><summary>Answer</summary>

`ScopedValue` (JEP 506) is final in Java 25. `StructuredTaskScope` (JEP 505, its fifth preview
iteration) is still preview in Java 25. They ship on different tracks despite being designed to work
together, and conflating them produces the specific, checkable error of describing structured
concurrency as stable when its API shape (the `fork`/`join`/`Joiner` surface) has changed release to
release and is not yet frozen.

</details>

**Q6.** Why can this file's `MiniFuture` be run on plain Java 21 with no `--enable-preview` flag,
while a `StructuredTaskScope` snippet targeting the same JDK cannot?

<details><summary>Answer</summary>

`MiniFuture` is an ordinary hand-written class using only stable, non-preview JDK APIs
(`VarHandle`, `volatile`, plain classes) — nothing about it depends on a JEP that has not shipped as
final. `StructuredTaskScope`, by contrast, is itself a preview feature (JEP 428 originally, now on
its fifth preview as JEP 505) — using the real JDK class at all, on any Java 21 through 25 build,
requires `--enable-preview` at both compile and run time because the API is explicitly not
finalized.

</details>

---

**Leaves covered:** 4.7.5–4.7.6 (2 leaves)
**Leaves deferred:** none
**Diagrams included:** none
**Target version:** Java 21 LTS
**Lines:** 445
