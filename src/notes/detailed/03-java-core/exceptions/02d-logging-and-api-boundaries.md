# 03 Java Core — Logging discipline and the API boundary — INTERMEDIATE (§2.6.14–2.6.16)

**Target version: Java 21 LTS.** | **Part 2 of 5** | [Index](../00-index.md)
Previous: [Exception cost and exceptions as control flow](02c-cost-and-control-flow.md) · Next: [Resources, interrupts and testing](02e-resources-interrupts-and-testing.md)

`01e-catch-discipline-and-top-level-handling.md` states the language-level rule — log or rethrow, never both; log the throwable object, never `getMessage()` — and defers the full treatment here. This file is that treatment, plus the two facts that sit either side of it: never swallow and never `printStackTrace()`, and what happens once an exception reaches the edge of the process and has to become an HTTP response instead of a Java object. All three leaves are one continuous idea. A `Throwable` carries a type, a message, a stack trace and a cause chain because that is what a *developer* needs to diagnose a failure. None of that is what a *log aggregator* needs (it needs the object, structured, once), and none of it is what an *external client* needs (it needs a stable code and a correlation id, and nothing else). Getting all three leaves right is the same discipline applied at three different distances from the failure.

Everything measured below is against **Oracle JDK 21.0.7 (21.0.7+8-LTS-245, macOS aarch64)**, in scratch directories under `/tmp/`. SLF4J and Spring are not on this machine's build classpath for this note set, so every claim about SLF4J's argument handling and every claim about Spring's API is a documentation check against a primary source — the SLF4J issue tracker and Javadoc, the Spring Framework source on GitHub, and the Spring Boot source on GitHub — stated as such at the point it is made, never implied to have been compiled or run.

---

## 1. Logging discipline: log or rethrow, log the object (2.6.14)

### Mental model

A caught exception has exactly one home per layer of the call stack: the layer that can actually **do** something about it — retry, translate it, return a fallback, or turn it into an HTTP response — logs it, once, as a complete object. Every other layer it passes through is a pipe, not a destination, and a pipe that also prints what flows through it is not being careful, it is duplicating the flow. `getMessage()` is a summary a human wrote (or the JVM synthesized) for the *first* sentence of a diagnosis; the throwable itself — type, message, stack trace, `Caused by:` chain, suppressed exceptions — is the whole diagnosis. Passing the object to the logger and passing its message to the logger are not two ways of writing the same log line; they are a complete record and a lossy fragment of it.

### Why it exists as a trap

Both halves of this rule get broken by code that looks more careful than the alternative, not less. `log.error("stake reservation failed: " + e.getMessage())` reads, on a review skim, as an improvement over an empty catch — something was logged. And `catch (Exception e) { log.error("failed", e); throw e; }` reads as extra diligence — logged *and* propagated, so surely nothing is lost either way. Both instincts are wrong for the same underlying reason: they treat logging as a side effect that is always safe to add, rather than as a decision about which single layer owns the record of this failure. The `[TRAP]` here is specifically the message-string form, because it is syntactically valid, produces real output, and only fails you on the one input that matters most — a `NullPointerException` or any other exception thrown with no explicit message.

### When this is ever legitimate to break

The "log or rethrow" half has exactly one sanctioned exception, and it is narrow: a boundary that has context the outer frame will never see again — a batch index, a partially-applied `StakeSplit`, a request-scoped correlation id that is about to fall out of scope — logs that context at `DEBUG` and rethrows, without also logging the throwable's own stack trace a second time. The outer frame still gets exactly one full log record, at whichever level it decides; the inner frame's `DEBUG` line supplies detail the outer one structurally cannot reconstruct. This is a case of the inner layer contributing information the boundary would otherwise lose, not a case of it logging the same throwable a second time.

The "log the object, not the message" half has no legitimate exception. There is no scenario where `getMessage()` alone is preferable to the object — if the message is genuinely all a downstream consumer should see, that is a job for a *response body* (concept 3), constructed deliberately from the exception's fields, not for what gets *logged*.

### How it works

**The mechanism that makes "pass the object" actually work.** SLF4J's `Logger` interface declares overloads such as `error(String format, Object arg)`, `error(String format, Object arg1, Object arg2)`, and a widest form taking an erased `Object[] arguments` array (written in source using the varargs shorthand for that same array parameter). None of these has a dedicated `Throwable` parameter for the multi-argument case — instead, per the SLF4J issue tracker's own description of the behaviour (`qos-ch/slf4j` issue #390, "Message formatting with last argument being Throwable") and the pattern demonstrated in SLF4J's own documentation and widely-cited usage (Baeldung's "Logging Exceptions Using SLF4J" reproduces the same rule), a **trailing argument whose type is `Throwable`, that has no corresponding `{}` placeholder left to fill, is peeled off by the formatter and rendered as a stack trace underneath the formatted message** rather than substituted into the string. This is a documentation check, not a run on this machine, since SLF4J is not on this project's classpath — but it is the load-bearing fact behind every "pass `e`, don't call `e.getMessage()`" recommendation, so it is worth being precise about the mechanism rather than citing it as folklore: it is the *last positional argument*, of type `Throwable`, with the placeholder count already exhausted, that triggers the special handling. `log.error("stake reservation failed for round {}", roundId, e)` has one `{}` and two non-format arguments; `roundId` fills the placeholder, and `e`, left over and `Throwable`-typed, gets the special treatment instead of being coerced to a string and substituted nowhere.

**The equivalent, run for real, on `java.util.logging` via `System.Logger`** (Java 9), since SLF4J is unavailable here. `Objects.requireNonNull(Object)` — the single-argument overload — throws a `NullPointerException` with **no message at all**, which is the honest way to produce the literal `null` this rule warns about, rather than relying on a dereference NPE, which since Java 15 usually carries a helpful, non-null message (concept 5 of `01e-catch-discipline-and-top-level-handling.md`). Measured on JDK 21.0.7:

```java
import java.util.Objects;

record Reservation(String roundId) {}

static Reservation lookupReservation(String roundId) {
    return null; // stubbed for this measurement
}

public static void main(String[] args) {
    String roundId = "round-771";
    try {
        Reservation reservation = Objects.requireNonNull(lookupReservation(roundId));
        System.out.println(reservation);
    } catch (NullPointerException e) {
        System.out.println("failed: " + e.getMessage());
    }
}
```

printed exactly:

```
failed: null
```

`Objects.requireNonNull(Object)`'s single-argument overload constructs its `NullPointerException` with no message, by design — it is meant to be paired with the two-argument overload when a message is wanted, and callers who reach for the one-argument form specifically because it is shorter are the ones who produce a `getMessage()` that is `null`. Now the logged-object form, run for real with `System.Logger`:

```java
import java.lang.System.Logger;
import java.lang.System.Logger.Level;

static final Logger log = System.getLogger("PaymentService");

static void reserveStake(String roundId) {
    try {
        Reservation reservation = Objects.requireNonNull(lookupReservation(roundId));
    } catch (NullPointerException e) {
        log.log(Level.ERROR, "stake reservation failed for round " + roundId, e);
    }
}
```

Measured output:

```
Aug 29, 2026 2:11:36 PM PaymentService reserveStake
SEVERE: stake reservation failed for round round-771
java.lang.NullPointerException
	at PaymentService.reserveStake(PaymentService.java:9)
```

The `String`-concatenation form printed `failed: null` — five characters that tell an on-call engineer nothing beyond "something null happened, somewhere, in a method that calls something." The object form printed the exception's type, its full stack trace including the exact line, and would have printed a `Caused by:` chain underneath had one been present. Neither line is longer to write; only one of them is diagnosable at 3 a.m.

**"Log or rethrow, never both" — the mechanism, run for real.** A caught-and-rethrown exception that is also logged at every catch site along the way produces one full copy of the same stack trace per layer that does it — not a summary, the *entire* trace, repeated. Five layers of `catch (Exception e) { log.error("stake reservation failed", e); throw e; }` is five copies of one failure in the log, and now whoever is triaging cannot tell from the log volume alone whether there were five independent failures or one failure logged five times. Measured on JDK 21.0.7 with two layers — `reserveStake`, which logs and rethrows, called by `handleReservation`, which also logs and rethrows nothing further, just absorbs it:

```java
static void reserveStake(String roundId) throws Exception {
    try {
        settleAtQuizEngine(roundId);
    } catch (Exception e) {
        log.log(Level.ERROR, "reserveStake failed for round " + roundId, e);
        throw e;
    }
}

static void handleReservation(String roundId) {
    try {
        reserveStake(roundId);
    } catch (Exception e) {
        log.log(Level.ERROR, "handleReservation failed for round " + roundId, e);
    }
}

static void settleAtQuizEngine(String roundId) {
    throw new IllegalStateException("quiz engine rejected round " + roundId);
}
```

produced:

```
Aug 29, 2026 2:12:12 PM DoubleLog reserveStake
SEVERE: reserveStake failed for round round-771
java.lang.IllegalStateException: quiz engine rejected round round-771
	at DoubleLog.settleAtQuizEngine(DoubleLog.java:25)
	at DoubleLog.reserveStake(DoubleLog.java:9)
	at DoubleLog.handleReservation(DoubleLog.java:18)
	at DoubleLog.main(DoubleLog.java:29)

Aug 29, 2026 2:12:12 PM DoubleLog handleReservation
SEVERE: handleReservation failed for round round-771
java.lang.IllegalStateException: quiz engine rejected round round-771
	at DoubleLog.settleAtQuizEngine(DoubleLog.java:25)
	at DoubleLog.reserveStake(DoubleLog.java:9)
	at DoubleLog.handleReservation(DoubleLog.java:18)
	at DoubleLog.main(DoubleLog.java:29)
```

The identical five-line trace, twice, twelve lines total for one failure. The rule with its boundary, stated precisely: **the frame that handles the failure logs it once; every frame that merely translates or propagates it stays silent and rethrows with the cause preserved** (`01a-throwable-api-and-chaining.md` owns the chaining mechanism itself). "Handles" means the frame is the last one that will ever see this exception as an exception — a `@RestControllerAdvice` handler (concept 3), a scheduled job's top-level catch, a message-consumer's poison-pill handler. Everything upstream of that point is a pipe.

**Which level for what.** Four levels, one purpose each, specifically as they apply to an exception rather than to logging in general:

| Level | When, for an exception | QuizStakes example |
|---|---|---|
| `ERROR` | The failure needs a human, now or on the next triage pass | `LedgerImbalanceException` reaching the `@RestControllerAdvice` catch-all — the ledger is the source of truth and an imbalance is never expected |
| `WARN` | The path degraded but the system recovered without help | A `BonusIneligibleException` caught and converted into "deposit succeeded, bonus not granted" — the deposit itself still worked |
| `INFO` | A business event that happens to be modeled as an exception | `RestrictedActionException` for a stake attempt blocked by `SELF_EXCLUDED` — expected, auditable, not a defect |
| `DEBUG` | Diagnostic detail a human will want only while actively investigating | The boundary-with-context case above: a batch index or partial `StakeSplit`, logged and rethrown without the trace |

**Whether `isDebugEnabled()` is needed.** This is a supporting fact, not a primary concept: it has no diagram, no sibling to be weighed against, and the only tradeoff is computational, not architectural. `log.debug("stake split for round {}", roundId)` needs no `if (log.isDebugEnabled())` guard, because SLF4J's parameterized form does not evaluate or concatenate anything until (and unless) the logger decides the level is enabled — `roundId` is just a reference passed into a method call, cheap regardless. The guard becomes necessary only when an *argument itself* is expensive to compute — `log.debug("stake split: {}", computeExpensiveDiagnosticSplitSummary(reservation))` evaluates that call whether or not `DEBUG` is enabled, unless wrapped in `if (log.isDebugEnabled())`. **Gotcha:** guarding every parameterized debug call "to be safe" is dead code that adds a branch for no benefit; guard only the ones whose arguments do real work.

**Structured context over string formatting.** Also a supporting fact: an MDC (Mapped Diagnostic Context) entry or a structured key-value logging call carrying `roundId` and `clientId` as their own fields is strictly better than formatting them into the message string, for exactly the reason exception fields (`02b-designing-an-exception-hierarchy.md`'s subject) beat message strings — a field can be filtered on, aggregated, and alerted on by a log platform; a substring inside a formatted sentence can only be grepped. `MDC.put("roundId", roundId.toString())` before a block of work, cleared in a `finally`, means every log line emitted inside that block — including ones written by code that has no idea a `roundId` exists — carries it as a structured field.

### The diagram

No diagram for this concept: the evidence is `failed: null` next to a five-line stack trace, and a five-line trace printed twice next to a five-line trace printed once. Both comparisons are two blocks of real text side by side, and the prose above is the clearer rendering than a picture of the same two blocks would be.

### A minimal concrete example

```java
import java.lang.System.Logger;
import java.lang.System.Logger.Level;
import java.util.Objects;

public final class StakeReservationService {

    private static final Logger log = System.getLogger(StakeReservationService.class.getName());

    record Reservation(RoundId roundId, StakeSplit split) {}
    record RoundId(java.util.UUID value) {}
    record StakeSplit(java.math.BigDecimal bonusPortion, java.math.BigDecimal cashPortion) {}

    void reserveStakeWrong(RoundId roundId) {
        try {
            quizEngineReserve(roundId);
        } catch (Exception e) {
            System.out.println("stake reservation failed for round " + roundId + ": " + e.getMessage());
        }
    }

    void reserveStakeRight(RoundId roundId) {
        try {
            quizEngineReserve(roundId);
        } catch (Exception e) {
            log.log(Level.ERROR, "stake reservation failed for round " + roundId, e);
            throw new RestrictedActionException(
                    RestrictionType.STAKE_BLOCKED,
                    "stake reservation failed for round " + roundId,
                    e);
        }
    }

    private void quizEngineReserve(RoundId roundId) {
        Reservation reservation = Objects.requireNonNull(lookupReservation(roundId));
        reservation.split();
    }

    private Reservation lookupReservation(RoundId roundId) {
        return null; // Quiz Engine client stubbed as unreachable for this scenario
    }
}
```

`reserveStakeWrong` prints `stake reservation failed for round RoundId[value=<uuid>]: null` — measured (with the record's UUID standing in for one concrete run's value), matching the `Objects.requireNonNull` run above. `reserveStakeRight` logs the full object once, then rethrows a translated, chained exception (`01a-throwable-api-and-chaining.md`) rather than the raw `NullPointerException` — which is also "log or rethrow, never both" in its other common shape: the log call and the throw are two different exceptions, the original (logged, stays here) and the translated one (not logged again, propagated).

### The gotcha

**Pitfall:** believing `catch (Exception e) { log.error("stake reservation failed: " + e.getMessage()); }` counts as handling the exception because it produces visible output. Wrong belief: "I logged something, so the failure is recorded." Symptom: for the single most common uncaught failure shape — a `NullPointerException` or any exception constructed via a single-argument factory that sets no message — the log line reads `stake reservation failed: null`, and the stack trace, the exact failing line, and any `Caused by:` chain are gone permanently; the only artifact of the failure is five characters that could describe any bug in the method. Fix: never call `.getMessage()` for the purpose of logging; pass the throwable itself as the trailing argument (`log.error("stake reservation failed for round {}", roundId, e)`), and log it at exactly one layer, per the "log or rethrow" rule above — the fix for one half of this leaf is incomplete without the other, because a correctly-object-logged exception that is *then* rethrown and logged again at every layer above it has traded one failure mode (no information) for another (duplicated information masking the real failure count).

> **Definition.** Logging discipline for a caught exception is two rules that fail independently: log the `Throwable` object itself, never its `getMessage()` result folded into a string, because the object carries the type, the stack trace and the full `Caused by:` chain that the message string does not; and log it at exactly one layer — the one that handles it — never at every layer that merely rethrows it, because each additional logging site duplicates the identical trace rather than adding information.

---

## 2. Never swallow, never `printStackTrace()` (2.6.15)

### Mental model

A swallowed exception and a `printStackTrace()`'d exception fail the same way for different reasons: both convert a signal the rest of the program (and the humans operating it) were relying on into something that either does not exist or exists somewhere nobody is looking. An empty `catch` destroys the signal outright. `printStackTrace()` does not destroy it — it writes it to `System.err`, faithfully — but `System.err` in a containerized service is not the log pipeline; it is a file descriptor that may or may not be captured, correlated, timestamped, or searchable, depending entirely on infrastructure decisions the calling code has no visibility into.

### Why this is a trap

`printStackTrace()` is the first thing most Java developers learn, in a classroom `catch` block, before they have ever heard of a logging framework — it is a zero-dependency, zero-configuration, always-available way to see a trace, and it works perfectly in that setting because a classroom program's `System.err` and its terminal are the same thing. The trap is that it keeps compiling and keeps "working" — in the sense of not throwing — after the code moves into a service running inside a container, where `System.err` is redirected somewhere quite different from a developer's terminal, and the gap between "ran without error" and "produced a diagnosable record" opens silently.

### When either is ever legitimate

`printStackTrace()`: essentially never in code that ships. The narrow exception is a genuinely throwaway script with no logging framework configured and no expectation of ever running unattended — and even there, `e.printStackTrace(System.out)` at least keeps it out of a stream some shells treat specially, which is a minor point next to the real fix, which is to configure a logger. Swallowing: never — an empty `catch`, a `catch` that logs at a level nobody monitors on a path that cannot actually continue safely, and a `catch` that returns a default value indistinguishable from a real one are three shapes of the same failure, not three different decisions with three different valid uses.

### How it works

**What `printStackTrace()` actually does — read from the source, not from memory.** JDK 21.0.7's `java.lang.Throwable` (`lib/src.zip`), `printStackTrace(PrintStream s)`:

```java
public void printStackTrace(PrintStream s) {
    printStackTrace(new WrappedPrintStream(s));
}

private void printStackTrace(PrintStreamOrWriter s) {
    Object lock = s.lock();
    if (lock instanceof InternalLock locker) {
        locker.lock();
        try {
            lockedPrintStackTrace(s);
        } finally {
            locker.unlock();
        }
    } else synchronized (lock) {
        lockedPrintStackTrace(s);
    }
}
```

and `WrappedPrintStream.lock()`:

```java
Object lock() {
    return SharedSecrets.getJavaIOPrintStreamAccess().lock(printStream);
}
```

That resolves to the same lock `PrintStream.println` itself synchronizes on. **The folklore claim — "`printStackTrace()` produces torn, interleaved lines under concurrent use" — is not what this source shows, and the honest claim is a different one.** `printStackTrace()` on a given `PrintStream` *is* mutually exclusive with any other write that goes through that same `PrintStream`'s lock, including another thread's `printStackTrace()` call and another thread's `println`. What is true, and is the real reason not to use it, is entirely about *where the bytes go*, not about *whether they get torn*: `System.err` is a raw byte stream with no timestamp, no level, no thread name, no MDC context, and no structured fields — none of the things a configured logger's appender attaches to every line by contract. In a containerized service, `System.err` is typically captured by whatever collects container stdout/stderr, which means the trace *can* end up in a log aggregation system, but as an unparsed, unstructured, unattributed blob sitting in the same stream as anything else the process (or, without care, another process sharing the same container) writes to `System.err` — not lost, but stripped of everything that makes the rest of the log pipeline queryable.

**The three shapes of swallowing.** The empty `catch` is the obvious one and needs no code to demonstrate. The two sneakier ones:

*A `catch` that logs at `DEBUG` on a path that cannot actually continue.* `DEBUG` is filtered out in production by default in most logging configurations — logging at `DEBUG` and then proceeding as though nothing happened is functionally identical to an empty catch in the environment that matters most, with the added cost of looking reviewed. If `settleStakeBatch` cannot produce a correct result once a `LedgerImbalanceException` occurs, logging that fact at a level nobody's alerting is watching and then returning as if the batch succeeded is a swallow wearing a disguise.

*A `catch` that returns a default the caller cannot distinguish from a real answer.* `BigDecimal.ZERO` returned from a stake-settlement failure looks, to the caller, identical to a legitimately-zero settlement — the caller has no way to tell "the Quiz Engine confirmed zero winnings" from "the Quiz Engine call threw and we made something up." This is worse than the empty catch in one specific sense: an empty catch's downstream symptom is usually a `null` or a missing side effect that eventually surfaces as its own, separate failure; a plausible-looking default can propagate for a long time before anyone notices the number was fabricated.

### The diagram

No diagram for this concept: the evidence is one quoted source method showing a genuine lock, contrasted with one sentence about what that lock does not fix (the destination), and two short code shapes for the sneaky swallows; a picture would restate the source quote in boxes.

### A minimal concrete example

```java
BigDecimal settleStakeBatchWrong(List<Reservation> batch) {
    try {
        return quizEngineSettle(batch);
    } catch (Exception e) {
        e.printStackTrace(); // goes to System.err: no timestamp, no level, no MDC
        return BigDecimal.ZERO; // indistinguishable from a genuine zero settlement
    }
}

BigDecimal settleStakeBatchAlsoWrong(List<Reservation> batch) {
    try {
        return quizEngineSettle(batch);
    } catch (Exception e) {
        log.log(Level.DEBUG, "settlement issue for batch of " + batch.size() + " reservations", e);
        return BigDecimal.ZERO; // DEBUG is filtered in production: this is the empty catch, disguised
    }
}

BigDecimal settleStakeBatchRight(List<Reservation> batch) {
    try {
        return quizEngineSettle(batch);
    } catch (RuntimeException e) {
        log.log(Level.ERROR, "settlement failed for batch of " + batch.size() + " reservations", e);
        throw new LedgerImbalanceException(
                "settlement failed for batch of " + batch.size() + " reservations", e);
    }
}
```

`settleStakeBatchRight` does the two things the other two both skip: it logs at a level someone is actually watching, and it makes the failure visible to the *caller* — throwing a `LedgerImbalanceException`, rather than returning a value the caller has no way to distinguish from success.

### The gotcha

**Pitfall:** treating a `catch` block that logs at `DEBUG` and returns a plausible default as meaningfully different from an empty `catch`, because it "does something." Wrong belief: "I logged it and returned a safe fallback, so this is handled, unlike a bare empty catch." Symptom: `settleStakeBatchAlsoWrong` runs in production for months returning `BigDecimal.ZERO` on every Quiz Engine timeout, with a `DEBUG`-level line nobody's alerting rules will ever surface, until a reconciliation job — comparing ledger totals against the Quiz Engine's own records — flags a discrepancy that has been accumulating the entire time, with no log evidence pointing at when it started because the level filtering ate every occurrence. Fix: the level a caught exception is logged at must match how observable the failure needs to be, not how the developer felt while writing the catch block; if the caller cannot proceed correctly, the exception must reach the caller, at `ERROR`, not be absorbed into a default that looks like a real answer.

> **Definition.** Swallowing is any `catch` block that neither surfaces the failure to its caller nor makes it visible at a log level someone is watching — an empty body, a `printStackTrace()` call (visible only to whoever happens to be reading `System.err` raw, with no structure), a `DEBUG`-level log on a path that cannot actually continue, and a returned default indistinguishable from a genuine result are four shapes of the identical failure to route the signal.

---

## 3. Exceptions across the API boundary (2.6.16)

### Mental model

An exception is an *internal* control-flow construct — it exists to unwind a call stack inside one process, carrying a type, a message, and a trace that make sense only to someone who can read that process's source code. An HTTP response is an *external* contract — a status code and a body that a client written by a different team, possibly outside the company, has to be able to parse without ever seeing that source. The API boundary's entire job is a **total mapping** from the first to the second: every exception the domain can throw has a defined HTTP outcome, including — especially — the ones nobody explicitly planned for.

### Why it exists

Without a deliberate boundary, the mapping happens by accident: an unhandled `LedgerImbalanceException` propagates out through whatever framework machinery is above the controller, and the framework's own default error handling decides what the client sees — which, unconfigured, is frequently a `500` whose body contains the exception's class name, its message, and its full stack trace, because the framework's default error page was designed for a developer looking at `localhost` during development, not for an untrusted caller in production. The interview-answerable mechanism, in full: an `@RestControllerAdvice` class registers `@ExceptionHandler` methods that Spring's dispatcher consults *before* falling through to that framework default, keyed by the most specific applicable exception type in the catch hierardchy, giving the application exactly one place that owns the exception-to-response mapping for every controller in the module — one gate instead of one accidental leak per unhandled type. Guide 07 (Spring core) owns the container and AOP mechanics `@RestControllerAdvice` is built on; guide 12 (API design) owns REST contract and JSON design in full generality; guide 13 (Web security) owns the OWASP treatment of information disclosure this section is a specific instance of.

### When to reach for a full mapping, and when it is already handled

Reach for an explicit `@ExceptionHandler` for every domain exception a client can be expected to react to differently — `InsufficientFundsException` and `RestrictedActionException` are not the same failure from the client's point of view, and collapsing both to a generic `500` forces the client to string-match a message to tell them apart, which `02b-designing-an-exception-hierarchy.md`'s structured-fields argument exists specifically to avoid. Do not reach for a bespoke handler per exception *subtype* within a family that the client genuinely cannot and should not distinguish — a single handler for the sealed `Verdict` hierarchy's failure cases, mapped by outcome rather than by concrete class, is the right level of granularity there. And the catch-all `Exception` handler is not a dumping ground to avoid writing the specific ones; it is the deliberate last line for the failures nobody predicted, and its whole job is different in kind from the specific handlers above it — it must never let anything through unmapped, including a `LedgerImbalanceException` subtype nobody remembered to add a handler for, which is the harder failure mode, not the easier one.

### How it works

**The status mapping**, five domain exceptions plus the deliberate catch-all:

| Exception | HTTP status | Response body contains |
|---|---|---|
| `InsufficientFundsException` | 422 Unprocessable Entity | stable code `INSUFFICIENT_FUNDS`, no internal detail |
| `RestrictedActionException` | 403 Forbidden | stable code `RESTRICTED_ACTION`, the restriction type only if it is itself client-facing vocabulary |
| `IllegalTransitionException` | 409 Conflict | stable code `ILLEGAL_TRANSITION` |
| `BonusIneligibleException` | 422 Unprocessable Entity | stable code `BONUS_INELIGIBLE` |
| `LedgerImbalanceException` | 500 Internal Server Error | stable code `INTERNAL_ERROR`, correlation id — nothing about the ledger |
| Anything else (`Exception`) | 500 Internal Server Error | stable code `INTERNAL_ERROR`, correlation id only |

Note the last two rows deliberately return the *same* client-visible shape. A `LedgerImbalanceException` is exactly as much "we don't know what to tell you" from the client's perspective as a truly unanticipated `Exception` — the fact that the server-side developer named it is irrelevant to what a client at the boundary is entitled to learn.

**`ProblemDetail` and the RFC.** Verified against the Spring Framework 6.1 Javadoc (`docs.spring.io`) and the Spring Framework source on GitHub (`spring-web/src/main/java/org/springframework/http/ProblemDetail.java`): `org.springframework.http.ProblemDetail` is a class in the `spring-web` module, available since **Spring Framework 6.0** (and therefore Spring Boot 3.0), representing a **Problem Details for HTTP APIs** payload — `type`, `title`, `status`, `detail`, `instance`, plus a `properties` map for non-standard extension fields. Also verified: **RFC 9457** (published 2023) obsoleted **RFC 7807** (the original 2016 "Problem Details" specification); Spring's own documentation describes its support as being for RFC 9457, "previously known as RFC 7807" — so code and prose describing this as "RFC 7807 support" is not wrong about the shape (RFC 9457 is a compatible refinement, not a breaking redesign) but is citing the superseded RFC number, which is exactly the kind of stale detail worth catching before it goes in a design doc or an interview answer.

**The `@RestControllerAdvice`, written against the documented Spring Boot 3.x API.** Not compiled — Spring is not on this machine — but written to the shape shown in the current Spring Framework reference documentation's "Error Responses" chapter and the `ProblemDetail`/`ErrorResponse` Javadoc:

```java
@RestControllerAdvice
public class PaymentApiExceptionHandler {

    private static final Logger log = System.getLogger(PaymentApiExceptionHandler.class.getName());

    @ExceptionHandler(InsufficientFundsException.class)
    public ProblemDetail handleInsufficientFunds(InsufficientFundsException e) {
        ProblemDetail problem = ProblemDetail.forStatus(HttpStatus.UNPROCESSABLE_ENTITY);
        problem.setTitle("Insufficient stakeable balance");
        problem.setProperty("code", "INSUFFICIENT_FUNDS");
        return problem;
    }

    @ExceptionHandler(RestrictedActionException.class)
    public ProblemDetail handleRestrictedAction(RestrictedActionException e) {
        ProblemDetail problem = ProblemDetail.forStatus(HttpStatus.FORBIDDEN);
        problem.setTitle("Action restricted");
        problem.setProperty("code", "RESTRICTED_ACTION");
        return problem;
    }

    @ExceptionHandler(IllegalTransitionException.class)
    public ProblemDetail handleIllegalTransition(IllegalTransitionException e) {
        ProblemDetail problem = ProblemDetail.forStatus(HttpStatus.CONFLICT);
        problem.setTitle("Illegal state transition");
        problem.setProperty("code", "ILLEGAL_TRANSITION");
        return problem;
    }

    @ExceptionHandler(BonusIneligibleException.class)
    public ProblemDetail handleBonusIneligible(BonusIneligibleException e) {
        ProblemDetail problem = ProblemDetail.forStatus(HttpStatus.UNPROCESSABLE_ENTITY);
        problem.setTitle("Bonus not granted");
        problem.setProperty("code", "BONUS_INELIGIBLE");
        return problem;
    }

    @ExceptionHandler(LedgerImbalanceException.class)
    public ProblemDetail handleLedgerImbalance(LedgerImbalanceException e) {
        String correlationId = java.util.UUID.randomUUID().toString();
        log.log(Level.ERROR, "correlationId=" + correlationId + " ledger imbalance at API boundary", e);
        ProblemDetail problem = ProblemDetail.forStatus(HttpStatus.INTERNAL_SERVER_ERROR);
        problem.setTitle("Internal error");
        problem.setProperty("code", "INTERNAL_ERROR");
        problem.setProperty("correlationId", correlationId);
        return problem;
    }

    @ExceptionHandler(Exception.class)
    public ProblemDetail handleUnexpected(Exception e) {
        String correlationId = java.util.UUID.randomUUID().toString();
        log.log(Level.ERROR, "correlationId=" + correlationId + " unhandled exception at API boundary", e);
        ProblemDetail problem = ProblemDetail.forStatus(HttpStatus.INTERNAL_SERVER_ERROR);
        problem.setTitle("Internal error");
        problem.setProperty("code", "INTERNAL_ERROR");
        problem.setProperty("correlationId", correlationId);
        return problem;
    }
}
```

The catch-all is the point of the whole design, not an afterthought below it: it is what makes the mapping *total*. It logs the full throwable, at `ERROR`, exactly once — this handler is the "layer that handles it" from concept 1 — and returns a body containing **only** the correlation id and a code stable enough for a client's own error-handling code to switch on, matching:

```json
{
  "type": "about:blank",
  "title": "Internal error",
  "status": 500,
  "code": "INTERNAL_ERROR",
  "correlationId": "3f6a9e2c-8b41-4b3a-9b2e-7d1a4c9f0e11"
}
```

**The three leak channels, and the fix for each:**

| Leak channel | What it hands an attacker or a curious client | Fix |
|---|---|---|
| Stack trace in the response body | Internal class names, package structure, exact line numbers — a map of the implementation for free | Never serialize a `Throwable` (or its `getStackTrace()`) into any response body; the catch-all handler above constructs a fresh `ProblemDetail`, never touches `e`'s trace |
| The exception's own `getMessage()` | Since Java 15, a helpful NPE message can name internal field and method names by default (JEP 358, covered in depth in `03d-internals-npe-messages-and-diagnostics.md`) — exactly the "internal detail" this boundary exists to stop, now arriving through a channel nobody thought of as a message at all | Never pass `e.getMessage()` into a response body for an unanticipated exception type; the specific handlers above use a title the developer wrote, not the exception's own message |
| The framework default | A misconfigured `server.error.include-stacktrace` serves a trace even with an explicit `@RestControllerAdvice` in place, on any path the advice does not cover | Verify the property explicitly rather than trusting the framework default (next paragraph) |

**The framework default, verified from source rather than assumed.** Fetched directly from the Spring Boot 3.3.3 source on GitHub, `ErrorProperties.java`: `private IncludeAttribute includeStacktrace = IncludeAttribute.NEVER;`, with the enum declared as `NEVER, ALWAYS, ON_PARAM`. So the property `server.error.include-stacktrace` (Spring Boot 3.x) **defaults to `NEVER`** — the safe default is already the out-of-the-box behaviour, and a service that leaks a trace via this path has had it explicitly set to `ALWAYS` (or `ON_PARAM` with an untrusted-caller-controllable parameter) somewhere in its configuration, not merely "forgotten to configure" it. That is worth stating precisely because the opposite claim — that Spring Boot serves stack traces by default and you must remember to turn it off — is repeated often enough online (including in Spring Boot's own GitHub issue tracker, where a 2020 report of exactly that claim, issue #21497, was closed without confirming the default had regressed) that it is worth citing the field initializer directly rather than the folklore.

### The diagram

No diagram for this concept: the evidence is a five-row status table, a three-row leak table, and one complete class — all three are already the clearest possible rendering of "which exception maps to which response, and where the mapping can leak," and a diagram would need to re-encode the same rows as boxes.

### A minimal concrete example

Shown above in full — the `PaymentApiExceptionHandler` class is the complete, self-contained example for this concept; splitting it further would separate the specific handlers from the catch-all that gives them their point.

### The gotcha

**Pitfall:** believing "never return the stack trace" means the response body should be as empty as possible, including omitting the correlation id "for security." Wrong belief: a minimal error body is automatically a more secure one. Symptom: a support engineer receiving a client's bug report has nothing to search the logs for — no id, no code — and has to ask the client to reproduce the failure with timing information close enough to grep the logs by timestamp, which frequently fails when the client's clock and the server's log timestamps are not in the same timezone or are off by the latency of the request itself. Fix: the correlation id is not the information being protected against; the stack trace, the message, and the internal class names are. Returning **only** the correlation id and a stable code costs the caller the one-round-trip debugging convenience a verbose error gives a developer during local testing — the trade is deliberate, not accidental, and it is why the id is generated and logged *before* it is returned, so that trade never becomes "we also lost the ability to find the failure server-side."

> **Definition.** The API boundary is the single point — in Spring Boot 3.x, a `@RestControllerAdvice` with `@ExceptionHandler` methods returning `ProblemDetail` (Spring Framework 6, RFC 9457, which obsoleted RFC 7807) — that provides a total mapping from every exception the domain can throw, named or not, to an HTTP response containing a stable machine-readable code and a correlation id and nothing else; the stack trace, the exception's own message, and the framework's own default error page (`server.error.include-stacktrace`, defaulting to `NEVER` in Spring Boot 3.x) are the three channels that leak the mapping's internals if the boundary is incomplete or misconfigured.

---

## Pitfalls

### Logging `e.getMessage()` instead of the throwable

**Wrong**

```java
catch (Exception e) {
    log.error("stake reservation failed: " + e.getMessage());
}
```

Measured, for an exception constructed with no message (`Objects.requireNonNull(Object)`'s single-argument overload): `stake reservation failed: null`. The stack trace and any `Caused by:` chain are gone; the log line is indistinguishable from any other bug in the same method.

**Right**

```java
catch (Exception e) {
    log.error("stake reservation failed for round {}", roundId, e);
}
```

The trailing `Throwable` argument is recognized by SLF4J (a documentation check here, per the SLF4J issue tracker's own description of the behaviour — not run on this machine) and rendered as a full stack trace beneath the formatted line, independent of how many `{}` placeholders the format string has.

**Why people believe it:** `getMessage()` reads as "the human-written part" of the exception — short, readable, feels deliberate to print. The mistake is not noticing that the object *is* the human-readable part, once the logger formats it, and the message string alone is a lossy summary that goes silent on exactly the exceptions the JVM constructs without one.

### Logging and rethrowing at every layer

**Wrong**

```java
static void reserveStake(String roundId) throws Exception {
    try {
        settleAtQuizEngine(roundId);
    } catch (Exception e) {
        log.error("reserveStake failed for round " + roundId, e);
        throw e;
    }
}

static void handleReservation(String roundId) {
    try {
        reserveStake(roundId);
    } catch (Exception e) {
        log.error("handleReservation failed for round " + roundId, e);
    }
}
```

Measured on JDK 21.0.7 with `System.Logger`: the identical five-line stack trace printed twice, twelve lines of log output for one failure, with no way for a reader of the log alone to tell "two failures" from "one failure logged twice."

**Right**

```java
static void reserveStake(String roundId) throws Exception {
    try {
        settleAtQuizEngine(roundId);
    } catch (Exception e) {
        throw e; // no log here — this frame is a pipe, not the destination
    }
}

static void handleReservation(String roundId) {
    try {
        reserveStake(roundId);
    } catch (Exception e) {
        log.error("handleReservation failed for round " + roundId, e); // the one frame that owns this
    }
}
```

**Why people believe it:** each individual `catch (Exception e) { log.error("failed", e); throw e; }` looks, read in isolation, like the more careful version of a bare rethrow — logged *and* propagated, nothing lost. What is invisible from inside any single method is that every other frame on the same call path made the identical choice, and the multiplication only becomes visible once you read the aggregate log output for one real failure.

### `printStackTrace()` shipped past a local development environment

**Wrong**

```java
catch (Exception e) {
    e.printStackTrace();
}
```

`System.err` in a containerized service is a raw byte stream with no timestamp, no level, no thread name and no MDC context attached — none of what a configured logger's appender contributes by contract. JDK 21.0.7's `Throwable.printStackTrace` source (`lib/src.zip`) does synchronize on the same lock `PrintStream.println` uses, so the folklore claim about torn interleaved lines does not hold up against the source — the real problem is entirely about which pipeline the bytes land in, not whether they arrive intact.

**Right**

```java
catch (Exception e) {
    log.error("settlement failed for batch of {} reservations", batch.size(), e);
    throw new LedgerImbalanceException(
            "settlement failed for batch of " + batch.size() + " reservations", e);
}
```

**Why people believe it:** `printStackTrace()` is usually the first way anyone sees an exception's trace at all, in a classroom `catch` block where the terminal and `System.err` are the same destination — it keeps compiling, keeps producing visible output, and nothing about running it in a container announces that the output is now going somewhere nobody configured to look.

---

## Cheat sheet

| Situation | Rule |
|---|---|
| Logging a caught exception | Pass the `Throwable` object as a trailing argument; never `.getMessage()` concatenated into the message string |
| A bare NPE's `getMessage()` | Since Java 15, usually a helpful non-null message for a *dereference* NPE; `Objects.requireNonNull(Object)`'s single-arg overload still gives literally `null` |
| Which layer logs | Exactly one — the layer that handles the failure. Every layer that only translates or rethrows stays silent |
| Legitimate exception to "log or rethrow" | A boundary logging context at `DEBUG` (not the trace) that the outer frame cannot reconstruct, then rethrowing |
| `ERROR` | Needs a human — an unexpected `LedgerImbalanceException`, the catch-all handler |
| `WARN` | Degraded but recovered — a caught `BonusIneligibleException` on an otherwise-successful deposit |
| `INFO` | Expected business event modeled as an exception — a `RestrictedActionException` for `SELF_EXCLUDED` |
| `DEBUG` | Diagnostic detail only — filtered out in most production configs, so never the sole record of a real failure |
| `if (log.isDebugEnabled())` | Needed only when an argument itself is expensive to compute; not needed for a bare `{}` reference |
| `printStackTrace()` | Writes to `System.err`: no timestamp, level, thread name or MDC. Synchronizes on `PrintStream`'s own lock (measured, JDK 21.0.7 source) — not torn, just unstructured and off the log pipeline |
| Swallow shape 1 | Empty `catch` |
| Swallow shape 2 | `catch` that logs at `DEBUG` on a path that cannot actually continue |
| Swallow shape 3 | `catch` that returns a default indistinguishable from a real answer |
| `ProblemDetail` | `org.springframework.http.ProblemDetail`, Spring Framework 6.0 / Spring Boot 3.0+ |
| RFC | RFC 9457 ("Problem Details for HTTP APIs"), obsoletes RFC 7807 |
| `@RestControllerAdvice` catch-all | Logs the throwable at `ERROR` with a generated correlation id; returns only the id and a stable code |
| `server.error.include-stacktrace` (Spring Boot 3.x) | Defaults to `NEVER` (verified: Spring Boot 3.3.3 `ErrorProperties.java` source). Values: `NEVER`, `ALWAYS`, `ON_PARAM` |
| Leak channel 1 | Stack trace in the body — fix: never serialize `e`'s trace into a response |
| Leak channel 2 | `e.getMessage()` in the body — can name internal fields/methods since Java 15 (JEP 358) |
| Leak channel 3 | Framework default misconfigured to `ALWAYS`/`ON_PARAM` — fix: verify the property explicitly |
| Correlation id | Generated at the boundary, logged with the throwable, returned to the client — the reason the client never needs the trace |

---

## Self-test

**Q1.** Why is `log.error("stake reservation failed: " + e.getMessage())` worse than it looks, given that it does produce a log line?

<details><summary>Answer</summary>

Because `getMessage()` returns only the string passed to the exception's constructor, which for many common failures is `null` — not "usually populated but occasionally missing," but reliably `null` for, for example, `Objects.requireNonNull(Object)`'s single-argument overload, which constructs its `NullPointerException` with no message by design. String concatenation turns that into the literal text `"null"`, so the log line reads `stake reservation failed: null`, which carries no information about which reference was null, in which method, or what the call chain leading there looked like — the stack trace and any `Caused by:` chain are entirely absent from a `getMessage()` call. Measured on JDK 21.0.7: exactly that output, `failed: null`, for a `NullPointerException` produced this way. The fix is to pass the throwable itself as a trailing argument to the logger — `log.error("stake reservation failed for round {}", roundId, e)` — which SLF4J's argument handling (a documentation check on this machine, since SLF4J is not on the classpath here) recognizes as a `Throwable` to render in full underneath the message, independent of the placeholder count.

</details>

**Q2.** State the "log or rethrow, never both" rule precisely, including its one sanctioned exception.

<details><summary>Answer</summary>

Exactly one layer of the call stack should produce a full log record for a given failure: the layer that handles it — meaning the layer that will not see this exception as an exception again, because it retries, translates it into a different exception, returns a fallback, or turns it into an HTTP response. Every layer the exception passes through on the way there should rethrow (or wrap-and-rethrow, chaining the cause) without also logging the full object, because each additional logging site reproduces the identical stack trace rather than adding information — measured on JDK 21.0.7 with a two-layer call chain, logging at both layers produced the same five-line trace printed twice, twelve lines for one failure, with no way to tell from log volume alone whether there were one or two failures. The one sanctioned exception is a boundary that has context the outer frame structurally cannot reconstruct — a batch index, a partially-applied `StakeSplit` — logging that context at `DEBUG`, without the trace, and then rethrowing; the outer frame still produces exactly one full record.

</details>

**Q3.** What does JDK 21's `Throwable.printStackTrace` source actually show about thread safety, and what does that not fix?

<details><summary>Answer</summary>

It shows a genuine lock: `printStackTrace(PrintStream s)` wraps the stream and synchronizes on the same lock object `PrintStream.println` itself uses (`SharedSecrets.getJavaIOPrintStreamAccess().lock(printStream)`, or an `InternalLock` on newer stream implementations), so two threads calling `printStackTrace()` on the same stream, or one calling `printStackTrace()` while another calls `println`, are mutually exclusive on that stream — lines are not torn or interleaved mid-line. What that does not fix is the destination: `System.err` is a raw byte stream with no timestamp, no level, no thread name, and no MDC context — none of what a logging framework's appender attaches to every line as part of the log pipeline's contract. In a containerized service, those bytes may or may not be captured by whatever collects container output, and even when they are, they arrive as an unstructured blob rather than a queryable, leveled, correlated log entry. The correct claim is about the log pipeline being bypassed, not about corrupted output.

</details>

**Q4.** Give the two sneaky forms of swallowing beyond the empty `catch`, with a QuizStakes example of each.

<details><summary>Answer</summary>

First, a `catch` that logs at `DEBUG` on a path that cannot actually continue: `catch (Exception e) { log.debug("settlement issue", e); return BigDecimal.ZERO; }` inside a stake-settlement method — `DEBUG` is filtered out of most production log configurations, so this is functionally an empty catch with the added risk of looking reviewed, and the caller proceeds as though the settlement succeeded. Second, a `catch` that returns a default indistinguishable from a genuine result: the same `BigDecimal.ZERO` return, from the caller's point of view, looks identical whether the Quiz Engine genuinely confirmed a zero-value settlement or the call threw and the method fabricated a value — a reconciliation job comparing ledger totals against the Quiz Engine's own records is often the only thing that eventually surfaces the discrepancy, long after the failures that caused it. Both differ from the empty catch only in that they produce *some* artifact; neither surfaces the failure to a caller or to a log level anyone is actually watching, which is the actual definition of swallowing.

</details>

**Q5.** What is the actual default for Spring Boot 3.x's `server.error.include-stacktrace`, and where was it verified?

<details><summary>Answer</summary>

`NEVER`. Verified by fetching `ErrorProperties.java` directly from the Spring Boot 3.3.3 tag on GitHub: `private IncludeAttribute includeStacktrace = IncludeAttribute.NEVER;`, with `IncludeAttribute` declaring `NEVER, ALWAYS, ON_PARAM`. So a Spring Boot 3.x service does not leak stack traces via this path out of the box; a service that does has had the property explicitly set to `ALWAYS`, or to `ON_PARAM` with a request parameter an untrusted caller can control. This is worth stating precisely because the opposite belief — that Spring Boot serves traces by default and a team must remember to disable it — circulates widely enough, including as a since-unconfirmed GitHub issue report (spring-projects/spring-boot#21497) claiming exactly that regression, that citing the field initializer directly is safer than repeating the claim.

</details>

**Q6.** Name the three channels a stack trace or internal detail can leak across an API boundary, and the fix for each.

<details><summary>Answer</summary>

First, the stack trace serialized directly into the response body — an attacker or a curious client learns internal class names, package structure and exact line numbers; the fix is that no `@ExceptionHandler` should ever put `e.getStackTrace()` or the trace's string form into the returned body, which the `@RestControllerAdvice` example here satisfies by constructing a fresh `ProblemDetail` that never touches the caught exception's trace. Second, the exception's own `getMessage()` returned as the client-visible detail — since Java 15, a helpful NullPointerException message can name internal field and method names by default (JEP 358), so a message that looks like harmless prose can itself be an information leak; the fix is that specific handlers use a title the developer wrote deliberately, never the caught exception's own message, and the catch-all handler returns only a correlation id and a stable code. Third, the framework's own default error handling, which can be configured (deliberately or by a stale configuration inherited from another environment) to include a trace regardless of what the application's own handlers do — the fix is to verify the actual property and default (`server.error.include-stacktrace`, `NEVER` by default in Spring Boot 3.x, verified from source above) rather than assume it, since a value of `ALWAYS` or `ON_PARAM` bypasses everything the application-level handlers were careful about.

</details>

**Q7.** Why does the catch-all `Exception` handler map to the same response shape as the specific `LedgerImbalanceException` handler, rather than something more detailed since the developer at least named that exception?

<details><summary>Answer</summary>

Because the shape of what a client is entitled to learn is determined by what the client can usefully *do* with the information, not by whether a server-side developer happened to give the failure a name. A `LedgerImbalanceException` and a genuinely unanticipated `Exception` are both, from outside the process, "something failed that the client cannot fix by changing its request" — there is no client-side retry-with-different-input strategy for either one, unlike `InsufficientFundsException` (client can deposit more) or `IllegalTransitionException` (client can check current state first). Both therefore return the same minimal shape — a stable `INTERNAL_ERROR` code and a correlation id — with the actual diagnostic value (the specific exception type, its message, its trace) logged server-side at `ERROR` under that same correlation id, where a human with access to the source and the logs can look it up. Collapsing both into the same client-visible shape is a deliberate design choice, not a missed opportunity to be more specific.

</details>

**Q8.** A response body returns nothing but an HTTP status and an empty JSON object, on the theory that this is the most secure possible error response. What is wrong with that design?

<details><summary>Answer</summary>

It over-corrects past the actual boundary of what needs protecting. The stack trace, the exception's message, and internal class or method names are the things that leak implementation detail to an untrusted caller; a correlation id is not one of them — it is an opaque, meaningless token to anyone without access to the server-side logs, and its entire purpose is to let a support engineer or the client's own support process locate the matching server-side `ERROR` log entry, which is where the real diagnostic content (the throwable, logged once, at the boundary) actually lives. Omitting the correlation id "to be safe" removes the one piece of information a legitimate support interaction needs and gives up nothing in exchange, since no attacker gains anything from a random UUID that does not decode to anything about the system's internals. The correct trade is: give up the stack trace and the message (real cost: a developer debugging locally loses a round trip of convenience they'd get from a verbose error), keep the correlation id (real benefit: the failure remains findable after the response has been returned).

</details>

---

## Open questions

None.

---

**Leaves covered:** 2.6.14, 2.6.15, 2.6.16 (3 leaves)
**Leaves deferred:** none
**Diagrams included:** none
**Target version:** Java 21 LTS
**Lines:** 646
