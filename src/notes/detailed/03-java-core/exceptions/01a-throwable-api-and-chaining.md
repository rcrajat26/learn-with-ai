# 03 Java Core — `Throwable`'s API and exception chaining — BASICS (§1.20, 1.20.7–1.20.8)

**Target version: Java 21 LTS.** | **Part 1 of 5** | [Index](../00-index.md)
Previous: [The exception model](01-basics.md) · Next: [`catch`, multi-catch and precise rethrow](01b-catch-multicatch-and-precise-rethrow.md)

Two leaves, but the surface underneath them is the whole `Throwable` class. First, the API surface, method by method, with the two fields it is built on: a `cause` that starts out pointing at itself as a "not set yet" flag, and a `stackTrace` that starts out as an empty array meaning "not yet decoded". Second, one habit — pass the cause, always — whose absence is invisible until the one week you need the log line it deleted.

Everything below is measured against **Oracle JDK 21.0.7 (21.0.7+8-LTS-245, macOS aarch64)**; library source is quoted from that build's `lib/src.zip`, `java.base/java/lang/Throwable.java`.

The checked/unchecked split and the `Throwable` hierarchy are [`01-basics.md`](01-basics.md)'s territory, not repeated here. `catch`-clause ordering, multi-catch and precise rethrow are [`01b-catch-multicatch-and-precise-rethrow.md`](01b-catch-multicatch-and-precise-rethrow.md). Try-with-resources and the suppression *mechanism* — when `addSuppressed` gets called and by what — are [`01c-try-with-resources-and-suppression.md`](01c-try-with-resources-and-suppression.md); this file owns only the `addSuppressed`/`getSuppressed` API shape. Logging discipline — `log.error("msg", e)` versus `e.getMessage()`, and why `printStackTrace` has no place in production code — is [`01e-catch-discipline-and-top-level-handling.md`](01e-catch-discipline-and-top-level-handling.md). Exception translation as a *design* decision, and carrying data as fields rather than formatting it into the message, is [`02b-designing-an-exception-hierarchy.md`](02b-designing-an-exception-hierarchy.md) (INTERMEDIATE) — this file owns the chaining mechanism, not the design judgment. `fillInStackTrace`'s cost and the lazy `backtrace` field are measured in [`03b-internals-stack-trace-capture.md`](03b-internals-stack-trace-capture.md) (INTERNALS); this file states the mechanism once and does not re-benchmark it. The `Suppressed:`/`Caused by:` trace format in full, plus `StackWalker`, is [`03d-internals-npe-messages-and-diagnostics.md`](03d-internals-npe-messages-and-diagnostics.md).

---

## 1. The `Throwable` API surface (1.20.7)

`Throwable` is not a bag of independent methods. It is two mutable fields — `cause` and `stackTrace` — each guarded by a write-once protocol, plus a third field (`suppressedExceptions`) added later under the same protocol, plus a set of accessors that expose them safely. Read the fields first and the methods make sense; read the methods first and half of them look like arbitrary API design.

The JDK's own comment on the protocol, verbatim from `Throwable.java`:

```java
/*
 * To allow Throwable objects to be made immutable and safely
 * reused by the JVM, such as OutOfMemoryErrors, fields of
 * Throwable that are writable in response to user actions, cause,
 * stackTrace, and suppressedExceptions obey the following
 * protocol:
 *
 * 1) The fields are initialized to a non-null sentinel value
 * which indicates the value has logically not been set.
 *
 * 2) Writing a null to the field indicates further writes
 * are forbidden
 *
 * 3) The sentinel value may be replaced with another non-null
 * value.
 */
```

That is the mental model for the entire table below: three fields, each starting at a sentinel meaning "unset", each writable exactly once from the sentinel to a real value, and each refusing further writes once it holds anything else (including an explicit `null`). `cause`'s sentinel is `this`. `stackTrace`'s sentinel is a shared empty array, `UNASSIGNED_STACK`. `suppressedExceptions`'s sentinel is a shared empty immutable list. The comment names the reason the protocol exists at all: HotSpot preallocates certain `OutOfMemoryError` instances for use when memory is too tight to safely allocate a new exception object, constructing them without calling `Throwable()`, so the fields land on `null` rather than the sentinel — which is why several methods below carry an explicit `stackTrace == null` or `backtrace != null` check rather than assuming the constructor always ran.

| Method | Signature | What it actually does | The trap |
|---|---|---|---|
| `getMessage` | `String getMessage()` | Returns `detailMessage` — a plain field read, nothing computed. | None: pure getter. |
| `getLocalizedMessage` | `String getLocalizedMessage()` | `return getMessage();` — see below. | Assuming a subclass has localized it. Almost none do. |
| `getCause` | `synchronized Throwable getCause()` | `return (cause == this ? null : cause);` — see below. | Assuming `getCause() == null` means "no cause was ever attempted"; it means "no cause is *currently* recorded", including the legitimate case of `initCause(null)`. |
| `initCause` | `synchronized Throwable initCause(Throwable cause)` | Write-once cause setter for constructors that took none. | See leaf 1.20.8's pitfall and the write-once rules below. |
| `getStackTrace` | `StackTraceElement[] getStackTrace()` | `getOurStackTrace().clone()` — a defensive copy, every call. | Calling it in a hot loop or per log line; each call allocates a fresh array. |
| `setStackTrace` | `void setStackTrace(StackTraceElement[] stackTrace)` | Defensively copies the argument, validates no element is `null`, then stores it — replacing whatever `fillInStackTrace` produced. | Silently a no-op if the stack trace was made immutable via the four-argument constructor. |
| `fillInStackTrace` | `synchronized Throwable fillInStackTrace()` | Calls a `native`, `synchronized` method that asks the JVM to snapshot the current thread's frames into `backtrace`. Called once, from every public constructor. | Overriding it without understanding it disables the *capture*, not merely the *print* — `getStackTrace()` on the result is a zero-length array, not a null one. |
| `printStackTrace` | `void printStackTrace()`, `void printStackTrace(PrintStream)`, `void printStackTrace(PrintWriter)` | Prints `toString()`, then each frame, then each suppressed exception (indented, recursively), then the cause (via `getCause()`, recursively), with an `N more` fold line for shared trailing frames. | Using it as your logging strategy — see [`01e`](01e-catch-discipline-and-top-level-handling.md). |
| `addSuppressed` | `final synchronized void addSuppressed(Throwable exception)` | Appends to the internal suppressed list, allocating it on first use. | `addSuppressed(this)` throws `IllegalArgumentException`; `addSuppressed(null)` throws `NullPointerException`. |
| `getSuppressed` | `final synchronized Throwable[] getSuppressed()` | Returns `EMPTY_THROWABLE_ARRAY` if none were ever added, else `suppressedExceptions.toArray(EMPTY_THROWABLE_ARRAY)` — a fresh copy every call. | Same defensive-copy cost as `getStackTrace`, easy to forget because the array is usually tiny. |
| `toString` | `String toString()` | `getClass().getName() + ": " + getLocalizedMessage()`, or just the class name if the message is `null`. | This is the first line every printed trace opens with — see below. |
| Four-arg constructor | `protected Throwable(String message, Throwable cause, boolean enableSuppression, boolean writableStackTrace)` | Java 7. Sets message and cause directly; conditionally skips `fillInStackTrace()`; conditionally nulls out the suppressed-exceptions list. | See its own treatment below — this is the hook [`03b-internals-stack-trace-capture.md`](03b-internals-stack-trace-capture.md) measures the cost of. |

Twelve entries; the next five earn their own prose because each carries a real surprise.

### `getMessage` / `getLocalizedMessage` — an extension point almost nobody uses

`getMessage()` returns the `detailMessage` field set by whichever constructor ran. `getLocalizedMessage()` looks like it should do something — the name implies locale-sensitive formatting — but in `Throwable` itself it is exactly this, quoted in full:

```java
public String getLocalizedMessage() {
    return getMessage();
}
```

One line. The Javadoc says outright that subclasses "may override this method in order to produce a locale-specific message", which makes `getLocalizedMessage` a designed extension point rather than a synonym that happened to exist — but in practice almost nothing in the JDK or in application code overrides it, because the convention that won instead is: keep the detail message in English and technical (it goes to logs and stack traces, which are read by engineers, not end users), and do any user-facing localization at the presentation layer from an error *code*, not from the exception's message text. **Interview:** "what's the difference between `getMessage` and `getLocalizedMessage`?" — the honest answer is "in `Throwable` itself, nothing; `getLocalizedMessage` is a hook for a subclass to override, and essentially none do."

### `getCause` and `initCause` — the `cause == this` sentinel

The field declaration and its comment, quoted:

```java
/**
 * The throwable that caused this throwable to get thrown, or null if this
 * throwable was not caused by another throwable, or if the causative
 * throwable is unknown.  If this field is equal to this throwable itself,
 * it indicates that the cause of this throwable has not yet been
 * initialized.
 *
 * @serial
 * @since 1.4
 */
private Throwable cause = this;
```

And the accessor:

```java
public synchronized Throwable getCause() {
    return (cause==this ? null : cause);
}
```

Read those two together. `cause` cannot start at `null`, because `null` is itself a legitimate, meaningful value for it — "there was a cause search and it concluded there is none" is different from "nobody has looked yet". So the field is initialised to `this`: a throwable pointing at itself is not a coherent causal chain (nothing can cause itself), which makes it a safe, unambiguous sentinel for "unset". `getCause()` translates that sentinel back to `null` for the caller, who never needs to know the sentinel exists — from outside, `getCause()` only ever returns a real cause or `null`. This is exactly why `initCause` *can* distinguish "cause never set" from "cause explicitly set to `null`": it inspects the raw field, not the translated one.

**Insight:** every other write-once field in `Throwable` (`stackTrace`, `suppressedExceptions`) needs a *different* sentinel because `null` is not available as "unset" for `cause` specifically — `cause` is the one field where an explicit `null` is a legal terminal value a caller can set. `this` is the only value guaranteed never to collide with a legitimate cause.

`initCause`, quoted in full:

```java
public synchronized Throwable initCause(Throwable cause) {
    if (this.cause != this)
        throw new IllegalStateException("Can't overwrite cause with " +
                                        Objects.toString(cause, "a null"), this);
    if (cause == this)
        throw new IllegalArgumentException("Self-causation not permitted", this);
    this.cause = cause;
    return this;
}
```

Two checks, two distinct exceptions:

- **`IllegalStateException`** if `this.cause != this` — meaning the sentinel is already gone, which happens two ways: the `(String, Throwable)` or `(Throwable)` constructor already set a real cause (even `null` counts as "already set"), or `initCause` was already called once before. Measured, on JDK 21.0.7, calling `initCause` a second time after the first succeeded:
  ```
  java.lang.IllegalStateException: Can't overwrite cause with java.lang.RuntimeException: cause2
  ```
  and calling it once on a throwable already constructed with `new Exception("msg", someCause)`:
  ```
  java.lang.IllegalStateException: Can't overwrite cause with java.lang.RuntimeException: cause2
  ```
  Same message shape both times, because both are "the sentinel is gone" — `initCause` cannot tell you *which* prior write happened, only that one did.
- **`IllegalArgumentException`** if `cause == this` — a throwable cannot cause itself. Measured:
  ```
  java.lang.IllegalArgumentException: Self-causation not permitted
  ```

`initCause` returns `this` — measured, `e.initCause(other) == e` is `true` — precisely so it composes with a `throw`: `throw new HighLevelException().initCause(lowLevel);` reads as one expression rather than three statements. This is the escape hatch **for a legacy exception class with no cause-taking constructor**: any `Throwable` subclass written before Java 1.4, or any subclass today that only bothered to declare `(String)`, still gets a cause attached — from the outside, after construction — because `initCause` is `public` on `Throwable` itself and every subclass inherits it whether or not it was designed with chaining in mind. The Javadoc's own example is exactly this shape:

```java
try {
    lowLevelOp();
} catch (LowLevelException le) {
    throw (HighLevelException)
          new HighLevelException().initCause(le); // Legacy constructor
}
```

### `getStackTrace` / `setStackTrace` — defensive copy, and the RPC use case

`getStackTrace()` is `getOurStackTrace().clone()`. Measured on JDK 21.0.7: two consecutive calls on the same exception return arrays that are `==`-unequal but element-equal —
```
sameArray=false equalContent=true
```
— confirming the clone is real, not an optimisation the JIT happens to elide. `setStackTrace(StackTraceElement[])` exists for a purpose the accessor name doesn't suggest: it is, per its own Javadoc, "designed for use by RPC frameworks and other advanced systems" that need to make a throwable report a stack trace that did not happen on this JVM — the classic case being a remote call that failed on a different machine, where the caller wants `getStackTrace()` to show the *remote* frames rather than (or in addition to) the local ones. `setStackTrace` defensively copies its argument and validates every element is non-`null` before storing, and — this is the trap in the table above — if the stack trace was made immutable via the four-argument constructor's `writableStackTrace = false`, the call silently does nothing beyond that validation; it does not throw. A later batch, [`../serialization/02-serialization.md`](../serialization/02-serialization.md), covers the case where the stack trace arrives via deserialization instead of via `setStackTrace` directly — the field obeys the identical write-once rule either way.

### `fillInStackTrace` — the `native` call every constructor makes

Every public `Throwable` constructor calls `fillInStackTrace()` (unless the four-argument constructor was given `writableStackTrace = false`, in which case it calls none of it and stores `null` instead). The method itself:

```java
public synchronized Throwable fillInStackTrace() {
    if (stackTrace != null ||
        backtrace != null /* Out of protocol state */ ) {
        fillInStackTrace(0);
        stackTrace = UNASSIGNED_STACK;
    }
    return this;
}

private native Throwable fillInStackTrace(int dummy);
```

It is `synchronized` and delegates to a `native` overload that talks directly to the JVM's frame-walking machinery, writing into the opaque `backtrace` field (decoded lazily into `StackTraceElement[]` only when `getStackTrace()` or `printStackTrace()` first asks — the cost and the measurement of that laziness belong to [`03b-internals-stack-trace-capture.md`](03b-internals-stack-trace-capture.md), not repeated here). Overriding `fillInStackTrace()` in a subclass to `return this;` — doing nothing — is the **stackless exception idiom**: it skips the capture entirely, and the resulting exception's `getStackTrace()` returns a zero-length array rather than throwing or returning `null`. Measured: a subclass built with the four-argument constructor's `writableStackTrace = false` produced `getStackTrace().length == 0`. `fillInStackTrace()` is also a documented no-op when the writable-stack-trace flag was set false at construction — calling it again on such an instance does nothing, by the same guard (`stackTrace != null || backtrace != null` is false).

### `printStackTrace` — the method whose replacement is the point

Three overloads, all funnelling into one private implementation that prints `this` (via `toString()`), then every frame, then every suppressed exception (recursively, each indented one level further and prefixed `Suppressed: `), then the cause (recursively, via `getCause()`, prefixed `Caused by: `) — with an `N more` fold line replacing any suffix of frames the printed throwable shares with its enclosing one. `getStackTrace()` versus this internal machinery reflects a real split: `printStackTrace` computes and formats everything itself using package-private `getOurStackTrace()`, so it does not pay `getStackTrace()`'s public defensive-copy cost internally. The two `PrintStream`/`PrintWriter` overloads exist so a caller can redirect the output — to a byte buffer, a file, or (least commonly, and never in production) `System.out` explicitly instead of the default `System.err`. **The answer in production code is a logger, not this method** — one line of the rule, with the full argument in [`01e-catch-discipline-and-top-level-handling.md`](01e-catch-discipline-and-top-level-handling.md).

### `addSuppressed` / `getSuppressed` — the try-with-resources API, added in Java 7

`addSuppressed(Throwable)`, quoted:

```java
public final synchronized void addSuppressed(Throwable exception) {
    if (exception == this)
        throw new IllegalArgumentException(SELF_SUPPRESSION_MESSAGE, exception);

    Objects.requireNonNull(exception, NULL_CAUSE_MESSAGE);

    if (suppressedExceptions == null) // Suppressed exceptions not recorded
        return;

    if (suppressedExceptions == SUPPRESSED_SENTINEL)
        suppressedExceptions = new ArrayList<>(1);

    suppressedExceptions.add(exception);
}
```

Measured: `addSuppressed(this)` throws
```
java.lang.IllegalArgumentException: Self-suppression not permitted
```
and `addSuppressed(null)` throws
```
java.lang.NullPointerException: Cannot suppress a null exception.
```
Note the allocation is deferred: `suppressedExceptions` starts at a shared empty immutable sentinel (`Collections.emptyList()`), and only the *first* `addSuppressed` call replaces it with a real, growable `ArrayList`. An exception with zero suppressed exceptions — the overwhelming majority — never allocates that list at all. `getSuppressed()` returns `EMPTY_THROWABLE_ARRAY` (a single shared empty array constant) when nothing was ever added, and otherwise `suppressedExceptions.toArray(EMPTY_THROWABLE_ARRAY)` — a fresh copy every call, measured `==`-unequal across two consecutive calls. This whole pair exists because of Java 7's try-with-resources: when the `try` block throws and the compiler-generated `close()` in the `finally` also throws, only one exception can propagate, and the other is not discarded — it is recorded here. The mechanism that decides *which* exception wins and *when* `addSuppressed` actually gets called is [`01c-try-with-resources-and-suppression.md`](01c-try-with-resources-and-suppression.md)'s territory; this file owns only the shape of the two methods.

### The four-argument protected constructor

```java
protected Throwable(String message, Throwable cause,
                    boolean enableSuppression,
                    boolean writableStackTrace) {
    if (writableStackTrace) {
        fillInStackTrace();
    } else {
        stackTrace = null;
    }
    detailMessage = message;
    this.cause = cause;
    if (!enableSuppression)
        suppressedExceptions = null;
}
```

Added in Java 7, `protected` — a subclass constructor calls it via `super(message, cause, enableSuppression, writableStackTrace)`, an ordinary caller cannot reach it directly. Two independent booleans, each switching off a distinct piece of `Throwable`'s default behaviour:

- **`writableStackTrace = false`** skips the `fillInStackTrace()` native call and sets `stackTrace` directly to `null` rather than the usual empty-array sentinel. `null` here is not "empty" — it is the field's own dedicated "further writes forbidden" state, so once set this way, `fillInStackTrace()` and `setStackTrace(StackTraceElement[])` both become permanent no-ops on this instance, and `getStackTrace()` returns a zero-length array forever.
- **`enableSuppression = false`** sets `suppressedExceptions` to `null` instead of the usual empty-list sentinel. `addSuppressed` checks for exactly this — `if (suppressedExceptions == null) return;` — so every future `addSuppressed` call on this instance is a validated no-op, and `getSuppressed()` always returns the empty array.

The JDK's own guidance, from the constructor's Javadoc: disabling either should be reserved for "exceptional circumstances where special requirements exist, such as a virtual machine reusing exception objects under low-memory situations" (this is precisely how HotSpot's preallocated `OutOfMemoryError` works) or "situations where a given exception object is repeatedly caught and rethrown, such as to implement control flow between two sub-systems" — a stackless exception used as a fast, cheap control-flow signal, where paying for a stack capture on every throw would be the actual bottleneck. This is the hook [`03b-internals-stack-trace-capture.md`](03b-internals-stack-trace-capture.md) measures the cost against.

### `toString()` composes the first line of every printed trace

`toString()` is `getClass().getName() + ": " + getLocalizedMessage()`, or just the class name if the message is `null`. This is not incidental to chaining: it is the exact string `printStackTrace` prints as the header line for the throwable itself, and as the text following `Caused by: ` or `Suppressed: ` for every throwable further down the chain. A `getMessage()` returning `null` is not an error — it just means the printed line is the bare class name, which is why an exception class with an unhelpful name and no message produces a genuinely useless trace header.

### The diagram

No diagram for this concept: the evidence is a JDK source comment describing a three-field write-once protocol, four quoted methods, and a comparison table — the prose above and the table are the clearer rendering than a picture of twelve boxes with arrows between them would be.

### A concrete example

The full method inventory in one throw path, from `QuizStakes`'s stake-reservation flow, showing several of the table's entries used together — capturing a stack, attaching a suppressed exception from a failed compensating action, and inspecting both later:

```java
public final class StakeReservationException extends RuntimeException {

    public StakeReservationException(String message, Throwable cause) {
        super(message, cause);
    }

    public StakeReservationException(String message) {
        super(message);
    }
}

public final class LedgerClient {

    public void reserveStake(RoundId roundId, Money stake) {
        try {
            writeReservationEntry(roundId, stake);
        } catch (SQLException writeFailure) {
            StakeReservationException toThrow = new StakeReservationException(
                "failed to reserve stake for round " + roundId + ": ledger write rejected",
                writeFailure);
            try {
                releaseHeldLock(roundId);
            } catch (RuntimeException lockReleaseFailure) {
                toThrow.addSuppressed(lockReleaseFailure);
            }
            throw toThrow;
        }
    }

    private void writeReservationEntry(RoundId roundId, Money stake) throws SQLException {
        throw new SQLException(
            "duplicate key value violates unique constraint \"ux_ledger_entry_idempotency_key\"",
            "23505");
    }

    private void releaseHeldLock(RoundId roundId) {
        // best-effort cleanup; may itself fail
    }
}
```

`writeFailure` is passed as the cause, so `getCause()` on the thrown `StakeReservationException` returns the original `SQLException` rather than `null`. If `releaseHeldLock` also throws, that second failure is not lost and not allowed to mask the first — it rides along via `addSuppressed`, retrievable later with `getSuppressed()`, and prints under a `Suppressed:` heading rather than replacing the primary exception on the way out.

### The gotcha

**Pitfall:** treating `getCause() == null` as proof that "nothing went wrong upstream" rather than "no cause is currently recorded". A throwable built with the no-cause constructors and never passed to `initCause` reports `getCause() == null` — indistinguishable, from the caller's side, from a throwable someone deliberately called `initCause(null)` on. Neither tells you whether an upstream failure was silently dropped versus never having existed. Fix: at the point you catch a lower-level exception, decide explicitly whether it is a cause worth keeping, and if it is, pass it — the two-constructor convention in the next concept exists specifically so that decision is never blocked by a missing constructor overload.

> **Definition.** `Throwable` is a class built on three write-once fields — `cause` (sentinel `this`), `stackTrace` (sentinel an empty array, or `null` if suppressed by the four-argument constructor), and `suppressedExceptions` (sentinel an empty immutable list, or `null` if suppressed) — with accessors that translate each sentinel back to the caller-visible `null` or empty form, defensive-copy every array they return, and compose into `printStackTrace`'s recursive cause-and-suppressed rendering via `getCause()` and `getSuppressed()`.

---

## 2. Exception chaining: always pass the cause (1.20.8) `[TRAP]`

The mental model: a chained exception is a **linked list**, not a single object. `getCause()` is the "next" pointer, `toString()` on each node is the printed line for that node, and `printStackTrace` is simply a traversal that prints every node and, for each one after the first, folds away the frames it shares with the node above it. Drop the pointer at any hop and the list is truncated there — permanently, because nothing downstream of that hop can reconstruct what used to be attached.

### Why it exists

A ledger write fails with a `SQLException` naming a specific violated constraint. `LedgerImbalanceException` catches it and needs to re-throw something meaningful to its own caller — a raw `SQLException` leaking out of a domain method is an abstraction leak, tying `PaymentService`'s API to the fact that `FundsLedger` happens to be backed by a relational database today. So `LedgerImbalanceException` is thrown instead — but if it does not carry the `SQLException` as its cause, whichever unique-constraint name made the write fail is now nowhere. It existed in memory for exactly as long as the `catch` block that swallowed it, and then it was gone. The two-argument constructor and `initCause` exist so that translating an exception — changing the type the caller sees — never has to mean discarding the information the original exception carried.

### When to reach for it, and when not

Every `catch` block that translates one exception type into another passes the caught exception as the cause of the new one — with essentially no exception to that rule inside a single process. The only case where chaining legitimately does not apply is when there genuinely is no prior throwable: an exception thrown from a validation check that found bad input directly, with nothing caught and nothing to attach. In that case there is nothing to chain to, and the single-argument `(String)` constructor is correct, not a violation of the rule — the trap here is different, it is *catching something and then not attaching it*, not *failing to invent a cause that doesn't exist*.

### How it works

`getCause()` returning the field set by the `(String, Throwable)` constructor (or by `initCause`) is measured and quoted in concept 1. The traversal that makes chaining visible is inside `printStackTrace`: after printing this throwable's own frames, it calls `getCause()`, and if that is non-`null`, recurses into printing that throwable under a `Caused by: ` prefix — which itself may have a cause that triggers a further recursion, which is exactly why it is called a *chain*.

The two constructor forms every custom exception should have, because between them they cover every real call site:

```java
public final class LedgerImbalanceException extends RuntimeException {

    public LedgerImbalanceException(String message) {
        super(message);
    }

    public LedgerImbalanceException(String message, Throwable cause) {
        super(message, cause);
    }
}
```

Omitting the second constructor is the root cause of the entire pitfall below — not carelessness at the call site. A developer writing `catch (SQLException e) { throw new LedgerImbalanceException("ledger write rejected"); }` against a class that has no `(String, Throwable)` constructor has no way to pass `e` even if they remember to — the class itself has already made the decision for them. This is why the convention in `Throwable`'s own class Javadoc is stated as a rule about the class, not about call sites: "those subclasses that might likely have a cause associated with them should have two more constructors, one that takes a `Throwable` (the cause), and one that takes a `String` (the detail message) and a `Throwable` (the cause)."

### The diagram

No diagram for this concept: the evidence is two printed stack traces, below, differing only in whether `Caused by:` lines are present at all — the traces themselves are the clearer rendering than a boxes-and-arrows picture of the same three exceptions.

### A concrete example

The scenario: `writeReservationEntry` fails against the ledger schema with a `SQLException` naming the violated unique-constraint index. `LedgerImbalanceException` catches it at the `FundsLedger` boundary and wraps it. `PaymentService` catches *that* and wraps it again for its own callers. Measured, printed with `printStackTrace` on JDK 21.0.7, **with the cause passed at both hops**:

```
Probe2$PaymentServiceException: PaymentService: stake reservation failed for client 9f2c4a1b-e88d-4e91-a7fa-11ab22cc33dd
	at Probe2.handlePaymentGood(Probe2.java:32)
	at Probe2.main(Probe2.java:57)
Caused by: Probe2$LedgerImbalanceException: failed to reserve stake for round r-88213: ledger write rejected
	at Probe2.reserveStakeGood(Probe2.java:24)
	at Probe2.handlePaymentGood(Probe2.java:30)
	... 1 more
Caused by: java.sql.SQLException: duplicate key value violates unique constraint "ux_ledger_entry_idempotency_key"
	at Probe2.writeLedgerEntry(Probe2.java:14)
	at Probe2.reserveStakeGood(Probe2.java:22)
	... 2 more
```

Read bottom-up: the `SQLException` is the root cause, naming the actual violated constraint (`ux_ledger_entry_idempotency_key`) — the one piece of information an on-call engineer needs to know this is a duplicate stake reservation, not a generic ledger failure. `LedgerImbalanceException` is the domain-level translation of it. `PaymentServiceException` is what `PaymentService`'s own callers see. Each `Caused by:` block folds its shared trailing frames against the block above it into an `N more` line, which is why the trace stays short even with two wrapping hops.

**Same code, cause dropped at both hops** — the identical scenario, with each wrapper's message text unchanged but constructed with the single-argument `(String)` constructor instead:

```
Probe2$PaymentServiceException: PaymentService: stake reservation failed for client 9f2c4a1b-e88d-4e91-a7fa-11ab22cc33dd
	at Probe2.handlePaymentBad(Probe2.java:50)
	at Probe2.main(Probe2.java:61)
```

That is the entire printed output. No `Caused by:` block. The string `ux_ledger_entry_idempotency_key` — the only fact that would have told anyone this was a duplicate-key failure rather than a timeout, a deadlock, or a connection drop — is not in this trace, not in any log built from this trace, and not recoverable from anything at or above `PaymentService`, because `getCause()` on the surfaced exception returns `null`. The `SQLException` was constructed, thrown, caught, and — because the `catch` block extracted only a hand-written message string and discarded the object itself — permanently destroyed. `[SENIOR IC]` This is not a rare mistake in production incident review: "the log says the payment failed, why doesn't it say why" is the single most common way this pitfall surfaces in an on-call rotation, days or weeks after the code that caused it was written.

### The gotcha

**Pitfall:** wrapping an exception for a cleaner API and losing the diagnostic trail because the cause was never attached. The wrong belief is that catching the low-level exception and writing its message into the new exception's string is "the same information, just reformatted" — `"ledger write failed: " + e.getMessage()`. It is not the same information: it discards the exception's *type* (so nothing downstream can `instanceof`-check or pattern-match on it), it discards any fields the original exception carried beyond its message (a `SQLException`'s SQL state, an HTTP client exception's status code), and it discards every frame of the original stack trace, leaving only the point where the *new* exception was constructed. The symptom is exactly the trace shown above: a short, clean-looking stack trace that gives no indication anything is missing, because there is nothing in the printed output to signal that a `Caused by:` section *should* have been there. Fix: every custom exception gets both the `(String)` and `(String, Throwable)` constructors, and every `catch` block that re-throws a different type passes the caught exception as the cause — `throw new LedgerImbalanceException("ledger write rejected", e);`, never `throw new LedgerImbalanceException("ledger write rejected: " + e.getMessage());`.

> **Definition.** Exception chaining is the `cause` field and the `getCause()`/`initCause()`/two-constructor mechanism that lets a translated exception still carry the exception it was translated from; a `catch` block that re-throws a different exception type without passing the original as the cause silently and permanently deletes the root cause from every trace and every log line built from that trace, with no visible sign in the shortened output that anything is missing.

---

## Pitfalls

### Wrapping an exception without passing the cause

**Wrong**

```java
static void reserveStakeBad() {
    try {
        writeLedgerEntry();
    } catch (SQLException e) {
        throw new LedgerImbalanceException(
            "failed to reserve stake for round r-88213: ledger write rejected");
    }
}
```

Printed trace, measured:

```
Probe2$PaymentServiceException: PaymentService: stake reservation failed for client 9f2c4a1b-e88d-4e91-a7fa-11ab22cc33dd
	at Probe2.handlePaymentBad(Probe2.java:50)
	at Probe2.main(Probe2.java:61)
```

No `Caused by:`. The unique-constraint name from the original `SQLException` is gone, and `getCause()` on the caught exception is `null` all the way up the call chain.

**Right**

```java
static void reserveStakeGood() {
    try {
        writeLedgerEntry();
    } catch (SQLException e) {
        throw new LedgerImbalanceException(
            "failed to reserve stake for round r-88213: ledger write rejected", e);
    }
}
```

Printed trace, measured, with the full three-level `Caused by:` chain shown in concept 2 above, ending in the actual violated constraint name. The fix requires the exception class to *have* the `(String, Throwable)` constructor — an exception class declaring only `(String)` makes this fix impossible at the call site, which is why both constructors belong on every custom exception from the start.

**Why people believe it:** the new exception's message often already contains a hand-written summary of what went wrong (`"ledger write rejected"`), so it feels like the information survived — it is right there in the string. What is missing is everything the original exception's *type* and *fields* carried beyond that one summary sentence, and every frame of where it actually happened.

### Assuming `getCause() == null` means nothing went wrong upstream

**Wrong**

```java
public void handle(StakeReservationException e) {
    if (e.getCause() == null) {
        log.warn("stake reservation failed, no upstream cause");
        // treated as a standalone failure — no root-cause investigation triggered
    }
}
```

`getCause()` returns `null` for two entirely different situations: no lower-level exception was ever caught, and a lower-level exception *was* caught but the code that constructed `StakeReservationException` used the single-argument constructor and threw the original away. This branch cannot tell them apart, and silently assumes the more reassuring one.

**Right**

Treat a missing cause as informative only when the throwing code is known to guarantee it — which means fixing the throwing side, not working around it at the catch site:

```java
public final class StakeReservationException extends RuntimeException {
    public StakeReservationException(String message, Throwable cause) {
        super(message, Objects.requireNonNull(cause,
            "StakeReservationException always wraps a lower-level failure"));
    }
}
```

Forcing every call site of this particular exception to supply a non-null cause turns "was there really no cause" back into a question the type system settles, rather than one a caller has to guess at from `getCause()`'s return value.

**Why people believe it:** `getCause()`'s contract genuinely does return `null` for "no cause, and none was intended" — that reading is correct for exceptions raised directly from bad input with nothing caught. The mistake is applying that reading uniformly to every exception in the codebase, including ones whose whole purpose is to wrap a lower-level failure.

### Configuring a boundary or framework to swallow the cause on rethrow

**Wrong**

```java
@ExceptionHandler(LedgerImbalanceException.class)
public ResponseEntity<ErrorBody> handle(LedgerImbalanceException e) {
    // e.getMessage() only — the framework's own re-wrap drops getCause()
    return ResponseEntity.status(409).body(new ErrorBody(e.getMessage()));
}
```

if some layer above this handler (a generic `@ControllerAdvice`, a gateway filter, an RPC boundary) constructs its *own* wrapping exception from `e.getMessage()` alone before logging it — a pattern that is easy to introduce once, centrally, and then forget about — every specific exception thrown anywhere in the application loses its cause at that single choke point, regardless of how carefully each individual `catch` block upstream passed it along.

**Right**

Log at the point where the full exception object is still in hand, with the exception passed to the logger as an object, not flattened to a string first:

```java
@ExceptionHandler(LedgerImbalanceException.class)
public ResponseEntity<ErrorBody> handle(LedgerImbalanceException e) {
    log.error("stake reservation failed", e);   // logger prints the full chain
    return ResponseEntity.status(409).body(new ErrorBody(e.getMessage()));
}
```

`log.error("msg", e)` versus `log.error(e.getMessage())` is a distinct discipline covered in full in [`01e-catch-discipline-and-top-level-handling.md`](01e-catch-discipline-and-top-level-handling.md); the point here is narrower — chaining only pays off if something downstream actually calls `getCause()` (directly, or via `printStackTrace`/a logger that does the same traversal) rather than flattening the exception to a single string before it reaches a sink that can print the whole chain.

**Why people believe it:** a single centralised exception handler feels like the right place to normalise error responses, and it is — for the *response*. The mistake is assuming the same centralisation is safe for *logging*, when logging is exactly the place the full chain needs to survive intact.

---

## Cheat sheet

| Thing | Fact (Java 21 LTS) |
|---|---|
| `getMessage()` | returns `detailMessage` field, no computation |
| `getLocalizedMessage()` | `return getMessage();` in `Throwable` itself — an extension point almost nobody overrides |
| `cause` field default | `this` — the sentinel meaning "not yet set"; never `null` by default |
| `getCause()` | `(cause == this ? null : cause)` |
| `initCause` overwrite (already set via ctor or prior call) | `IllegalStateException: Can't overwrite cause with` &lt;cause&gt; |
| `initCause(this)` | `IllegalArgumentException: Self-causation not permitted` |
| `initCause` return value | `this`, for `throw new X().initCause(c);` chaining |
| `getStackTrace()` | `getOurStackTrace().clone()` — fresh array **every call** |
| `setStackTrace(StackTraceElement[])` | defensive copy in; silent no-op if `writableStackTrace` was `false` |
| `fillInStackTrace()` | `synchronized`, delegates to a `native` overload; called by every ctor unless suppressed |
| Stackless idiom | override `fillInStackTrace()` to `return this;`, or use `writableStackTrace = false` |
| Stackless result | `getStackTrace().length == 0` |
| `printStackTrace()` default target | `System.err`; overloads take `PrintStream`/`PrintWriter` |
| `printStackTrace` in production | wrong — use a logger; see `01e` |
| `addSuppressed(this)` | `IllegalArgumentException: Self-suppression not permitted` |
| `addSuppressed(null)` | `NullPointerException: Cannot suppress a null exception.` |
| `getSuppressed()` | fresh copy every call; `EMPTY_THROWABLE_ARRAY` if none ever added |
| Suppressed-list allocation | deferred to the first `addSuppressed` call |
| Four-arg ctor | `protected Throwable(String, Throwable, boolean enableSuppression, boolean writableStackTrace)` — Java 7 |
| `enableSuppression = false` | `suppressedExceptions = null`; `addSuppressed` becomes a no-op |
| `writableStackTrace = false` | `stackTrace = null` directly, skips `fillInStackTrace()`; permanent |
| `toString()` | `getClass().getName() + ": " + getLocalizedMessage()`, or just the class name if message is `null` |
| Custom exception, minimum constructors | `(String)` and `(String, Throwable)` — always both |
| Chaining rule | `catch (X e) { throw new Y(msg, e); }` — never `throw new Y(msg + e.getMessage());` |
| Cause dropped | `Caused by:` block simply absent from the printed trace — no error, no warning |
| `getCause() == null` | means "no cause currently recorded" — could be legitimate, could be the pitfall |

---

## Self-test

**Q1.** Why does `Throwable` initialise its `cause` field to `this` rather than to `null`?

<details><summary>Answer</summary>

Because `null` is not available as the "unset" sentinel: it is itself a legitimate, meaningful terminal value for `cause` — a caller can legally call `initCause(null)` to record "there was a cause search and it concluded there is none," which must be distinguishable from "nobody has looked yet." `Throwable` needs a value that can never collide with a real cause, and a throwable pointing at itself is not a coherent causal chain — nothing can cause itself — so `this` is safe. The field declaration, quoted from JDK 21.0.7: `private Throwable cause = this;`, with the comment "If this field is equal to this throwable itself, it indicates that the cause of this throwable has not yet been initialized." The public accessor translates the sentinel back to the caller-visible form: `return (cause==this ? null : cause);` — so from outside, `getCause()` only ever returns a real cause or `null`, and the raw sentinel is never exposed. This is exactly what lets `initCause` distinguish "never set" from "set to null": it inspects `this.cause != this` on the raw field, which is `true` only while the sentinel is still in place.

</details>

**Q2.** A throwable was constructed with `new SomeException("message", someCause)`. What happens if code later calls `someException.initCause(otherCause)`, and why?

<details><summary>Answer</summary>

It throws `IllegalStateException`. Measured on JDK 21.0.7: `java.lang.IllegalStateException: Can't overwrite cause with java.lang.RuntimeException: cause2`. `initCause`'s first check is `if (this.cause != this) throw new IllegalStateException(message, this)` — and the two-argument constructor already assigned `this.cause = cause;` directly, bypassing the sentinel entirely, so by the time `initCause` runs, `this.cause` is already `someCause`, not `this`. The check cannot tell *how* the sentinel was cleared — the identical exception and message are thrown whether the cause was set by a constructor or by a prior successful `initCause` call — it only knows that it was. This is the practical meaning of "write-once": the write can happen via either mechanism, but only one of them, ever, for a given instance.

</details>

**Q3.** What is the exact difference in behaviour between `getStackTrace()` and `printStackTrace()` regarding the cost of repeated calls?

<details><summary>Answer</summary>

`getStackTrace()` is `getOurStackTrace().clone()` — a public method that allocates and returns a defensive copy of the backing array on every single call, specifically so a caller cannot mutate `Throwable`'s internal state by writing into the returned array. Measured on JDK 21.0.7: two consecutive `getStackTrace()` calls on the same exception return arrays that are `==`-unequal (`sameArray=false`) but element-equal (`equalContent=true`) — proving the clone happens every time, not just once. `printStackTrace()`, by contrast, calls the package-private `getOurStackTrace()` directly — the same underlying array, no clone — because it only reads the frames to format and print them and never hands the array to outside code. So a logging path that calls `getStackTrace()` once per frame per log event pays one allocation per call, which is a real, measurable regression under load; a path that only ever calls `printStackTrace()` (or a logger that walks the chain the same way) does not pay that cost at all. The fix when you need repeated access to the same trace is to call `getStackTrace()` once and reuse the returned array, not to call it again for every frame you want to inspect.

</details>

**Q4.** Someone writes `throw new LedgerImbalanceException("ledger write failed: " + e.getMessage());` inside a `catch (SQLException e)` block. What is lost, precisely, and what does the printed trace look like as a result?

<details><summary>Answer</summary>

Everything except the one string interpolated into the message. Lost: the `SQLException`'s *type*, so nothing downstream can `instanceof`-check or pattern-match on it to distinguish, say, a unique-constraint violation from a connection timeout; any fields `SQLException` carries beyond `getMessage()` — its SQL state and vendor error code, for instance; and every stack frame from where the `SQLException` actually occurred, leaving only the frame where `LedgerImbalanceException` itself was constructed. Measured, the printed trace for this pattern is exactly: the `LedgerImbalanceException`'s own class name, its interpolated message, and its own (short) stack — no `Caused by:` block at all, because `getCause()` on the thrown exception returns `null`. There is nothing in the printed output to indicate anything is missing; a short, clean trace is indistinguishable from one that never had more to show. The fix is `throw new LedgerImbalanceException("ledger write failed", e);` using a `(String, Throwable)` constructor, which requires that constructor to exist on the exception class in the first place.

</details>

**Q5.** What are the exact two exceptions `initCause` can throw, and what triggers each?

<details><summary>Answer</summary>

`IllegalStateException`, when `this.cause != this` — meaning the cause sentinel has already been cleared, either by the `(Throwable)` or `(String, Throwable)` constructor (even a `null` cause counts, since it is a real, non-sentinel value) or by a previous successful `initCause` call. Measured message: `Can't overwrite cause with java.lang.RuntimeException: cause2` — the message names the *new* cause that was rejected, not the existing one, so it does not by itself tell you which cause is already recorded; call `getCause()` separately for that. `IllegalArgumentException`, when the argument passed to `initCause` is `this` itself — a throwable cannot cause itself. Measured message: `Self-causation not permitted`. Both checks run in a `synchronized` method, and the state check runs before the self-reference check, so calling `e.initCause(e)` on a throwable whose cause is already set throws the state exception, not the self-causation one — the self-causation check is only reachable while the sentinel is still in place.

</details>

**Q6.** What exactly does the four-argument `Throwable` constructor's `writableStackTrace` parameter switch off, distinct from what `enableSuppression` switches off?

<details><summary>Answer</summary>

`writableStackTrace = false` sets the `stackTrace` field directly to `null` and skips the call to `fillInStackTrace()` that every other constructor makes — so no native frame-walking happens at construction, and `null` (as opposed to the usual empty-array sentinel) is a distinct state meaning "further writes forbidden": subsequent calls to `fillInStackTrace()` or `setStackTrace(StackTraceElement[])` on this instance become permanent no-ops, and `getStackTrace()` returns a zero-length array — measured, `length=0` — for the life of the object. `enableSuppression = false` is entirely independent: it sets `suppressedExceptions` to `null` instead of the usual empty-list sentinel, so `addSuppressed`'s own guard (`if (suppressedExceptions == null) return;`) makes every future `addSuppressed` call a validated no-op, and `getSuppressed()` always returns the empty array. Neither flag affects the other — an exception can suppress capture of its stack trace while still allowing suppressed exceptions to accumulate, or vice versa — which is why they are two separate booleans rather than one combined mode. The JDK's own guidance restricts both to "exceptional circumstances," naming HotSpot's preallocated `OutOfMemoryError` objects and control-flow exceptions that are repeatedly caught and rethrown as the intended use cases, not general application exceptions.

</details>

**Q7.** Why must every custom exception provide both a `(String)` and a `(String, Throwable)` constructor, rather than just the second one?

<details><summary>Answer</summary>

Because the two constructors correspond to two genuinely different situations, and collapsing to only the cause-taking one forces every call site — including the legitimate ones with no prior exception to attach — to either fabricate a `null` cause explicitly or invent a fake one, both of which are worse than a dedicated overload. `(String)` is correct when the exception represents a failure discovered directly, with nothing caught and nothing to chain to — for instance, a validation check on user-supplied input that found bad data with no lower-level exception involved. `(String, Throwable)` is correct whenever a `catch` block is translating one exception type into another, which is the common case for any layered system with a `FundsLedger`/`PaymentService`-style boundary. Providing only the cause-taking constructor does not prevent the mistake this file is about — it just relocates it, since a developer with no cause to pass will write `new SomeException("message", null)`, which works but reads oddly and is easy to typo into forgetting the `null` is deliberate. The actual failure mode this leaf warns about is the opposite gap: a class that provides only `(String)`, which makes it *impossible* to pass a cause even when the developer has one in hand and wants to.

</details>

**Q8.** A logging framework is configured to call `e.getMessage()` and log that string, rather than passing the throwable object itself to the logger. What breaks, given correctly-chained exceptions upstream?

<details><summary>Answer</summary>

The chaining upstream is entirely wasted, even though every `catch` block did the right thing. `getMessage()` returns only the single `detailMessage` string of the one exception object it is called on — it has no knowledge of `getCause()` and no mechanism to traverse it. `printStackTrace()`'s recursive `Caused by:`/`Suppressed:` rendering, and any real logger's equivalent traversal, only runs when the *throwable itself* is handed to the printing or logging call — `log.error("stake reservation failed", e)`, not `log.error("stake reservation failed: " + e.getMessage())`. So a correctly-chained three-level exception, logged via `getMessage()` alone, produces exactly the top-level message string and nothing else in the log — the root-cause `SQLException` and its unique-constraint name are still attached to the object in memory, `getCause()` would still return them if called, but nothing in this logging path ever calls it. The fix is entirely on the logging side: pass the exception object to the logger's throwable-accepting overload, which is the discipline [`01e-catch-discipline-and-top-level-handling.md`](01e-catch-discipline-and-top-level-handling.md) covers in full.

</details>

---

## Open questions

None.

---

**Leaves covered:** 1.20.7, 1.20.8 (2 leaves)
**Leaves deferred:** none
**Diagrams included:** none
**Target version:** Java 21 LTS
**Lines:** 586
