# 03 Java Core — Exception builds — how `finally` destroys the primary exception — BUILD IT (§4.6.4)

**Target version: Java 21 LTS.** | **Part 4 of 5** | [Index](../00-index.md)
Previous: [AutoCloseable, try-with-resources, and suppression](03d-autocloseable-and-finally.md) · Next: [The finally-return harness](03i-finally-return-harness.md)

An exception is in flight out of a `PaymentRun` export body. Cleanup runs. The cleanup itself throws.
One of those two exceptions reaches the caller and the other one is either attached to it or gone
forever, and which of the two happens is decided entirely by whether the cleanup was written as
try-with-resources or as a `finally` block.

`finally` has exactly one exit and one exception slot — the one the JVM is already unwinding with.
By JLS 14.20.2, if the `try` block completes abruptly for one reason and the `finally` block itself
completes abruptly for another, the `try` statement completes abruptly for the **finally's** reason
and the body's is **discarded**: not chained, not logged, not recorded anywhere. The stack trace the
caller receives points at the cleanup, not at the fault. That is a misleading error rather than a
missing one, which costs the investigation as well as the incident.

This file builds that failure, runs it, then builds the two ways to write `finally` so it does not
happen and compares all three. [AutoCloseable, try-with-resources, and suppression](03d-autocloseable-and-finally.md)
(leaf 4.6.3) owns the resources, close order and the suppression mechanism; this file reuses its two
resources unchanged so the comparison is exact. Everything below was compiled and run on **Oracle
JDK 21.0.7 (build 21.0.7+8-LTS-245), macOS aarch64** and all output is pasted from the run.

---

## The two resources, unchanged from leaf 4.6.3

Both are `AutoCloseable` with an idempotent `close()` that genuinely does work — the writer flushes a
buffered batch to `FundsLedger`, the export stream writes a trailer *through* the writer and releases
a reservation — so failing to close has an observable consequence. The sink and the row type:

```java
record ExportRow(String position, long minorUnits) {}

static final class FundsLedger {
    int postedEntries;
    long postedMinorUnits;
    int openReservations;

    void post(List<ExportRow> batch) {
        for (ExportRow row : batch) {
            postedEntries++;
            postedMinorUnits += row.minorUnits();
        }
        System.out.println("    FundsLedger.post: " + batch.size() + " rows, running total "
                + postedEntries + " entries / " + postedMinorUnits + " minor units");
    }

    void reserve() { openReservations++; }
    void release() { openReservations--; }
}
```

The guarded batch writer, whose `close()` flushes:

```java
static final class LedgerBatchWriter implements AutoCloseable {
    private final String name;
    private final FundsLedger ledger;
    private final boolean failOnClose;
    private final List<ExportRow> buffer = new ArrayList<>();
    private final AtomicBoolean closed = new AtomicBoolean(false);

    LedgerBatchWriter(String name, FundsLedger ledger, boolean failOnClose) {
        this.name = name;
        this.ledger = ledger;
        this.failOnClose = failOnClose;
    }

    void write(String position, long minorUnits) {
        if (closed.get()) {
            throw new IllegalStateException(name + " is closed");
        }
        buffer.add(new ExportRow(position, minorUnits));
    }

    @Override
    public void close() {
        if (!closed.compareAndSet(false, true)) {
            System.out.println("  " + name + ".close() entered, already closed, returning");
            return;
        }
        System.out.println("  " + name + ".close() entered, flushing " + buffer.size() + " buffered rows");
        List<ExportRow> batch = List.copyOf(buffer);
        buffer.clear();
        ledger.post(batch);
        if (failOnClose) {
            throw new LedgerImbalanceException(
                    "batch debits 4200 do not match credits 4180",
                    Map.of("writer", name, "rows", batch.size()));
        }
    }
}
```

The export stream, constructed from the writer and therefore dependent on it:

```java
static final class PaymentRunExportStream implements AutoCloseable {
    private final String name;
    private final LedgerBatchWriter writer;
    private final FundsLedger ledger;
    private final boolean failOnClose;
    private final AtomicBoolean closed = new AtomicBoolean(false);
    private int rowsExported;

    PaymentRunExportStream(String name, LedgerBatchWriter writer, FundsLedger ledger, boolean failOnClose) {
        this.name = name;
        this.writer = writer;
        this.ledger = ledger;
        this.failOnClose = failOnClose;
        ledger.reserve();
        System.out.println("  " + name + " opened, reservation taken, openReservations="
                + ledger.openReservations);
    }

    void exportWithdrawal(long minorUnits) {
        if (closed.get()) {
            throw new IllegalStateException(name + " is closed");
        }
        writer.write("BANK_SETTLEMENT", minorUnits);
        rowsExported++;
    }

    @Override
    public void close() {
        if (!closed.compareAndSet(false, true)) {
            System.out.println("  " + name + ".close() entered, already closed, returning");
            return;
        }
        System.out.println("  " + name + ".close() entered, writing trailer for " + rowsExported + " rows");
        writer.write("CLIENT_CASH_RESERVED", -rowsExported);
        ledger.release();
        System.out.println("    reservation released, openReservations=" + ledger.openReservations);
        if (failOnClose) {
            throw new RestrictedActionException(
                    "WITHDRAWAL_HELD from SYSTEM_COMPLIANCE applied mid-run",
                    Map.of("stream", name, "rows", rowsExported));
        }
    }
}
```

`InsufficientFundsException`, `RestrictedActionException` and `LedgerImbalanceException` come from
[A domain exception hierarchy](03c-exception-hierarchy-and-stackless.md), which owns them; the scratch
program re-declares the three as subclasses of an abstract `QuizStakesException extends
RuntimeException` storing `Map.copyOf(context)`, minus that file's `StatusCode`-shaped error code.

Both override `close()` with **no** `throws` clause. `AutoCloseable.close()` declares `throws
Exception` and the javadoc "strongly encourages" narrowing it; narrowing to nothing means callers
need no `catch (Exception)` they did not ask for.

`report(e)` prints the caught exception's simple name and message as `caught primary:`, then
`e.getSuppressed().length`, then one `suppressed[i] =` line per entry, then `e.printStackTrace(System.out)`
between `--- printStackTrace ---` and `--- end ---` markers. Every console block below is its output.
The scratch program wraps each case in its own named method, which is what the stack traces name.

---

## 4.6.4 The same scenario with `finally`, and the exception it destroys `[PROVE]`

Same two resources, same body failure, same close failure. Only the cleanup construct changes.

```java
LedgerBatchWriter writer = new LedgerBatchWriter("ledgerWriter", ledger, false);
PaymentRunExportStream export = new PaymentRunExportStream("paymentRunExport", writer, ledger, true);
try {
    try {
        export.exportWithdrawal(26000);
        export.exportWithdrawal(18000);
        throw new InsufficientFundsException(
                "withdrawable 18000 below requested 26000",
                Map.of("position", "CLIENT_CASH_AVAILABLE", "requested", 26000L));
    } finally {
        export.close();
        writer.close();
    }
} catch (RuntimeException e) {
    report(e);
}
```

Real output:

```console
  paymentRunExport opened, reservation taken, openReservations=1
  paymentRunExport.close() entered, writing trailer for 2 rows
    reservation released, openReservations=0
  caught primary: RestrictedActionException: WITHDRAWAL_HELD from SYSTEM_COMPLIANCE applied mid-run
  getSuppressed().length = 0
  --- printStackTrace ---
ResourceBuilds$RestrictedActionException: WITHDRAWAL_HELD from SYSTEM_COMPLIANCE applied mid-run
	at ResourceBuilds$PaymentRunExportStream.close(ResourceBuilds.java:172)
	at ResourceBuilds.finallyDestroys(ResourceBuilds.java:267)
	at ResourceBuilds.main(ResourceBuilds.java:370)
  --- end ---
```

The try-with-resources run of the *identical* failure reported `InsufficientFundsException` with the
`RestrictedActionException` attached as `Suppressed:`. Here:

- `getSuppressed().length = 0`. The `InsufficientFundsException` is gone — not logged, not chained,
  not recorded; the object was discarded and is unreachable.
- The trace points at `PaymentRunExportStream.close`, so on-call reads "WITHDRAWAL_HELD from
  SYSTEM_COMPLIANCE" and investigates compliance restrictions. The fault was insufficient
  withdrawable funds. **A misleading error is worse than a missing one** — it costs the
  investigation as well as the incident.
- `FundsLedger.post` never appears: `export.close()` threw, so `writer.close()` on the next line
  never ran and the batch of two bank withdrawals was silently dropped. A hand-rolled `finally`
  closing several resources on consecutive lines closes *only up to the first failure*.

### Why the exception disappears

JLS 14.20.2: if the `try` block completes abruptly for reason *R* (a thrown exception) and the
`finally` block itself completes abruptly for reason *S*, the `try` statement completes abruptly for
reason **S** and reason *R* is **discarded**. A `throw`, a `return`, a `break` or a `continue` in
`finally` all replace whatever the body was doing; there is no slot on the new exception where the
old one is stashed and no diagnostic anywhere. Neither the JVM nor javac warns (some IDEs and Error
Prone's `Finally` check do). Try-with-resources fixes this by *not being* `finally` — it parks the
primary in a local, closes, and calls `addSuppressed` on the local before rethrowing it.

**Insight:** `finally` has exactly one exception slot — the one the JVM is unwinding with. The
suppression list exists because the language needed a second slot and `finally` had nowhere to put
it.

### Writing `finally` correctly, two ways

Nested try/catch that logs the close failure and lets the primary propagate:

```java
} finally {
    try {
        export.close();
    } catch (RuntimeException closeFailure) {
        System.out.println("  LOG close failure: " + closeFailure);
    }
    try {
        writer.close();
    } catch (RuntimeException closeFailure) {
        System.out.println("  LOG close failure: " + closeFailure);
    }
}
```

```console
  paymentRunExport opened, reservation taken, openReservations=1
  paymentRunExport.close() entered, writing trailer for 2 rows
    reservation released, openReservations=0
  LOG close failure: ResourceBuilds$RestrictedActionException: WITHDRAWAL_HELD from SYSTEM_COMPLIANCE applied mid-run
  ledgerWriter.close() entered, flushing 3 buffered rows
    FundsLedger.post: 3 rows, running total 3 entries / 43998 minor units
  caught primary: InsufficientFundsException: withdrawable 18000 below requested 26000
  getSuppressed().length = 0
  --- printStackTrace ---
ResourceBuilds$InsufficientFundsException: withdrawable 18000 below requested 26000
	at ResourceBuilds.finallyNestedCatch(ResourceBuilds.java:285)
	at ResourceBuilds.main(ResourceBuilds.java:371)
  --- end ---
```

The primary survives and the batch flushes, but the close failure is now only in a log line: the
caller's exception carries no evidence of it, so an alert keyed on exception type never fires and a
test asserting on the thrown exception cannot see it.

Manual `addSuppressed` on the caught primary:

```java
RuntimeException primary = null;
try {
    export.exportWithdrawal(26000);
    export.exportWithdrawal(18000);
    throw new InsufficientFundsException(
            "withdrawable 18000 below requested 26000",
            Map.of("position", "CLIENT_CASH_AVAILABLE", "requested", 26000L));
} catch (RuntimeException e) {
    primary = e;
} finally {
    primary = closeQuietly(export, primary);
    primary = closeQuietly(writer, primary);
}
report(primary);
```

```java
static RuntimeException closeQuietly(AutoCloseable resource, RuntimeException primary) {
    try {
        resource.close();
        return primary;
    } catch (Exception closeFailure) {
        if (primary != null) {
            primary.addSuppressed(closeFailure);
            return primary;
        }
        return closeFailure instanceof RuntimeException re
                ? re
                : new IllegalStateException("close failed", closeFailure);
    }
}
```

```console
  paymentRunExport opened, reservation taken, openReservations=1
  paymentRunExport.close() entered, writing trailer for 2 rows
    reservation released, openReservations=0
  ledgerWriter.close() entered, flushing 3 buffered rows
    FundsLedger.post: 3 rows, running total 3 entries / 43998 minor units
  caught primary: InsufficientFundsException: withdrawable 18000 below requested 26000
  getSuppressed().length = 1
    suppressed[0] = RestrictedActionException: WITHDRAWAL_HELD from SYSTEM_COMPLIANCE applied mid-run
  --- printStackTrace ---
ResourceBuilds$InsufficientFundsException: withdrawable 18000 below requested 26000
	at ResourceBuilds.finallyManualSuppress(ResourceBuilds.java:313)
	at ResourceBuilds.main(ResourceBuilds.java:372)
	Suppressed: ResourceBuilds$RestrictedActionException: WITHDRAWAL_HELD from SYSTEM_COMPLIANCE applied mid-run
		at ResourceBuilds$PaymentRunExportStream.close(ResourceBuilds.java:172)
		at ResourceBuilds.closeQuietly(ResourceBuilds.java:325)
		at ResourceBuilds.finallyManualSuppress(ResourceBuilds.java:317)
		... 1 more
  --- end ---
```

### All three, compared

| | try-with-resources | `finally` + nested catch that logs | `finally` + manual `addSuppressed` |
|---|---|---|---|
| Primary survives a close failure | yes, by construction | yes | yes, if you remember the null case |
| Close failure reaches the caller | yes, as `Suppressed:` | no — log only | yes, as `Suppressed:` |
| All resources closed even if an earlier close throws | yes | yes, one nested try per resource | yes, one `closeQuietly` per resource |
| Close order | reverse declaration, enforced by the compiler | whatever you typed | whatever you typed |
| `null` resource | null-checked by generated code | your problem | your problem |
| Close-fails-with-no-primary | close failure becomes the primary | swallowed entirely | handled only by the `else` branch you must write |
| Reviewer must check | the resource list | every nested catch | the null branch, the order, the reassignment |

**Ship try-with-resources.** Reach for the manual forms only when the close is not a resource close
at all — releasing a reservation taken by hand, or unwinding two things whose order is not
declaration order. Both manual versions still get two things wrong that the compiler gets right for
free: close order is not enforced (nothing stops a refactor reordering the two `closeQuietly` calls
and closing the writer before its dependent), and correctness depends on someone remembering — the
logic is right in `closeQuietly` because it is written once, and copied inline into four `finally`
blocks it will be wrong in at least one.

By the same abrupt-completion rule `finally` destroys `return` values too — a `finally` that
*returns* replaces the body's return value outright, and returning while an exception is in flight
discards the exception exactly as a `throw` does. That harness is
[The finally-return harness](03i-finally-return-harness.md) (leaf 4.6.8); the `finally` traps
catalogue is [`../exceptions/01d-finally-traps.md`](../exceptions/01d-finally-traps.md).

### Diff vs the real one

The manual `closeQuietly` helper against the JDK's own equivalents:

| Axis | `closeQuietly` here | The JDK / the compiler |
|---|---|---|
| Edge cases | handles primary-null and checked-close; does not handle `Error` separately, so an `OutOfMemoryError` from a close propagates and destroys the primary | the generated code catches `Throwable`, so even an `Error` from `close()` becomes suppressed rather than replacing the primary |
| Intrinsics | none | none; `addSuppressed` is plain Java with a synchronized-free single-threaded assumption |
| Serialization | not serializable | `Throwable`'s `suppressedExceptions` **is** serialized (the field participates in `writeObject`); `SUPPRESSED_SENTINEL` deserializes back to the immutable empty list |
| Null policy | explicit `primary != null` branch | `addSuppressed(null)` throws NPE, `addSuppressed(this)` throws `IllegalArgumentException`; the compiler can never hit either |
| Thread safety | none; the `primary` local is confined to one call | `suppressedExceptions` is an unsynchronized `ArrayList`; concurrent `addSuppressed` on a shared `Throwable` is unsafe, which is one more reason not to cache exception singletons |
| Allocation tricks | wraps a checked close failure in a new `IllegalStateException` | the suppressed list starts as a shared immutable sentinel and is only allocated on first `addSuppressed`, so exception-free paths cost nothing |
| Why the JDK bothers | it does not ship this helper — `try`-with-resources replaced the need | JDK 7 added `addSuppressed`/`getSuppressed` **for** try-with-resources; the API is public so hand-written cleanup can match the language's behaviour |

> **Definition.** `finally` has one exit and one exception slot, so any abrupt completion inside it
> replaces the body's — try-with-resources exists precisely because correct resource cleanup needs
> two slots, and it fills the second with `addSuppressed`.


The section-wide §4.6 diff table lives in
[The Cleaner-based holder and the §4.6 diff table](03j-cleaner-and-diff.md) (leaf 4.6.9).

---

## Pitfalls

### Throwing from `finally` and losing the real failure

**Wrong**

```java
try {
    export.exportWithdrawal(26000);
    throw new InsufficientFundsException("withdrawable 18000 below requested 26000",
            Map.of("position", "CLIENT_CASH_AVAILABLE", "requested", 26000L));
} finally {
    export.close();   // throws RestrictedActionException
}
```

```console
ResourceBuilds$RestrictedActionException: WITHDRAWAL_HELD from SYSTEM_COMPLIANCE applied mid-run
	at ResourceBuilds$PaymentRunExportStream.close(ResourceBuilds.java:172)
	at ResourceBuilds.finallyDestroys(ResourceBuilds.java:267)
	at ResourceBuilds.main(ResourceBuilds.java:370)
```

`InsufficientFundsException` is not in that trace and is not anywhere else either.

**Right**

```java
try (LedgerBatchWriter writer = new LedgerBatchWriter("ledgerWriter", ledger, false);
     PaymentRunExportStream export = new PaymentRunExportStream("paymentRunExport", writer, ledger, true)) {
    export.exportWithdrawal(26000);
    throw new InsufficientFundsException("withdrawable 18000 below requested 26000",
            Map.of("position", "CLIENT_CASH_AVAILABLE", "requested", 26000L));
}
```

The primary is `InsufficientFundsException` with `RestrictedActionException` attached as
`Suppressed:` — the output is under
[AutoCloseable, try-with-resources, and suppression](03d-autocloseable-and-finally.md), leaf 4.6.3.

**Why people believe it:** `finally` is taught as "always runs", which is true, and that gets
upgraded to "always runs harmlessly". Nothing in the syntax hints the block can overwrite the
exception the JVM is already carrying, and javac emits no warning.


### Believing an exception thrown from a `catch` block is safe from the `finally`

**Wrong**

```java
try {
    export.exportWithdrawal(26000);
    throw new InsufficientFundsException(
            "withdrawable 18000 below requested 26000",
            Map.of("position", "CLIENT_CASH_AVAILABLE", "requested", 26000L));
} catch (InsufficientFundsException e) {
    throw new RestrictedActionException(          // translate at the boundary
            "WITHDRAWAL_HELD from SYSTEM_COMPLIANCE applied mid-run",
            Map.of("stream", "paymentRunExport", "rows", 1));
} finally {
    export.close();   // throws RestrictedActionException
    writer.close();
}
```

```console
  paymentRunExport opened, reservation taken, openReservations=1
  paymentRunExport.close() entered, writing trailer for 1 rows
    reservation released, openReservations=0
  caught primary: RestrictedActionException: WITHDRAWAL_HELD from SYSTEM_COMPLIANCE applied mid-run
  getSuppressed().length = 0
  --- printStackTrace ---
ResourceBuilds$RestrictedActionException: WITHDRAWAL_HELD from SYSTEM_COMPLIANCE applied mid-run
	at ResourceBuilds$PaymentRunExportStream.close(ResourceBuilds.java:172)
	at ResourceBuilds.catchDestroyed(ResourceBuilds.java:396)
	at ResourceBuilds.main(ResourceBuilds.java:375)
  --- end ---
```

The type that arrives looks like the translated exception the `catch` block built, and a reader of
the log would conclude the translation worked. It did not: the `RestrictedActionException` in that
trace was thrown by `PaymentRunExportStream.close`, at line 172, not by the `catch` block. The
`catch` block's exception was discarded with the same silence as a body exception, and
`ledgerWriter.close()` never ran, so the batch was dropped as well. Two exceptions were destroyed
here, not one — the original `InsufficientFundsException` by the `catch`, and the `catch`'s
translation by the `finally`.

**Right**

Translate outside the resource scope, so cleanup happens under try-with-resources and the
translation cannot collide with it:

```java
try {
    try (LedgerBatchWriter writer = new LedgerBatchWriter("ledgerWriter", ledger, false);
         PaymentRunExportStream export = new PaymentRunExportStream("paymentRunExport", writer, ledger, true)) {
        export.exportWithdrawal(26000);
        throw new InsufficientFundsException(
                "withdrawable 18000 below requested 26000",
                Map.of("position", "CLIENT_CASH_AVAILABLE", "requested", 26000L));
    }
} catch (InsufficientFundsException e) {
    throw new RestrictedActionException(
            "WITHDRAWAL_HELD from SYSTEM_COMPLIANCE applied mid-run",
            Map.of("stream", "paymentRunExport", "rows", 1));
}
```

The inner statement closes both resources and attaches the close failure to the
`InsufficientFundsException` as `Suppressed:` before the outer `catch` ever sees it, so the
translation happens on a complete exception rather than racing the cleanup.

**Why people believe it:** JLS 14.20.2's rule is usually taught as "an exception from the `try`
block", and `catch` feels like a separate, later phase that has already handled the failure. The
rule is about the whole `try` statement: an exception propagating out of a `catch` block is exactly
as abruptly-completing, and exactly as destructible, as one from the body.

### Believing manual `addSuppressed` is equivalent to try-with-resources

**Wrong**

```java
} finally {
    primary = closeQuietly(writer, primary);    // declaration order, not reverse
    primary = closeQuietly(export, primary);
}
```

```console
  paymentRunExport opened, reservation taken, openReservations=1
  ledgerWriter.close() entered, flushing 1 buffered rows
    FundsLedger.post: 1 rows, running total 1 entries / 26000 minor units
  paymentRunExport.close() entered, writing trailer for 1 rows
  caught primary: InsufficientFundsException: withdrawable 18000 below requested 26000
  getSuppressed().length = 1
    suppressed[0] = IllegalStateException: ledgerWriter is closed
  --- printStackTrace ---
ResourceBuilds$InsufficientFundsException: withdrawable 18000 below requested 26000
	at ResourceBuilds.manualWrongOrder(ResourceBuilds.java:413)
	at ResourceBuilds.main(ResourceBuilds.java:376)
	Suppressed: java.lang.IllegalStateException: ledgerWriter is closed
		at ResourceBuilds$LedgerBatchWriter.write(ResourceBuilds.java:108)
		at ResourceBuilds$PaymentRunExportStream.close(ResourceBuilds.java:166)
		at ResourceBuilds.closeQuietly(ResourceBuilds.java:325)
		at ResourceBuilds.manualWrongOrder(ResourceBuilds.java:418)
		... 1 more
  --- end ---
```

The suppression logic worked perfectly and the primary survived, which is what makes this one
dangerous: the manual route preserved the exception but *invented a second failure*. Neither
resource was configured to fail here — `failOnClose` is `false` on both. Closing the writer first
left the export stream's trailer write with a closed collaborator, so `close()` threw
`IllegalStateException: ledgerWriter is closed` and the trailer row was never written. The batch
posted **one** row instead of two.

**Right**

```java
try (LedgerBatchWriter writer = new LedgerBatchWriter("ledgerWriter", ledger, false);
     PaymentRunExportStream export = new PaymentRunExportStream("paymentRunExport", writer, ledger, false)) {
    export.exportWithdrawal(26000);
}
```

Close order is reverse declaration order, enforced by the compiler, so the dependent resource always
finishes before the resource it depends on is closed. No ordering decision is left to the author and
none can be reversed by a later refactor.

**Why people believe it:** `closeQuietly` visibly calls `addSuppressed`, so it looks like it does
what the compiler does. It does the *suppression* part; it does not do the *ordering* part, and
ordering is the half nothing reminds you about — the code compiles, reads correctly, and only
misbehaves when one resource actually depends on another.

---

## Cheat sheet

| Fact | Value |
|---|---|
| `throw` in `finally` while an exception is in flight | body's exception **discarded** (JLS 14.20.2) |
| Applies to an exception from a `catch` block too | yes — the rule is about the whole `try` statement |
| Also applies to `return`, `break`, `continue` in `finally` | yes, same abrupt-completion rule |
| Where the discarded exception is recorded | nowhere; no chain, no log, no warning from javac |
| Symptom in production | trace points at the cleanup, not at the fault |
| Second symptom of hand-rolled `finally` cleanup | resources after the failing close never close |
| `finally` + nested try/catch that logs | primary survives; close failure only in the log, not on the exception |
| `finally` + manual `addSuppressed` | primary survives with the close failure attached; ordering still yours to get right |
| try-with-resources | primary survives, close failure attached, order enforced, null handled |
| Which to ship | try-with-resources; manual only when the cleanup is not a resource close |
| `finally`-**return** swallowing | leaf 4.6.8, [The finally-return harness](03i-finally-return-harness.md) |

---

## Self-test

**Q1.** A production alert fires on `RestrictedActionException` from `PaymentRunExportStream.close`.
The team spends an hour on compliance restrictions and finds nothing. What is the shape of the bug?

<details><summary>Answer</summary>

Cleanup written as a bare `finally` that calls `close()`. The close failure abruptly completed the
`try` and discarded the real primary — `InsufficientFundsException` from the body — so the trace
points at the close, not the fault. Try-with-resources would have reported the primary with the
close failure attached as `Suppressed:`. A second symptom confirms it: resources closed after the
failing one never get closed, so the buffered ledger batch was dropped too.

</details>

**Q2.** State the rule that destroys the exception, precisely.

<details><summary>Answer</summary>

JLS 14.20.2. If the `try` block completes abruptly for reason *R* and the `finally` block itself
completes abruptly for reason *S*, the whole `try` statement completes abruptly for reason **S** and
reason *R* is discarded. *R* and *S* can each be a thrown exception, a `return`, a `break` or a
`continue` — the rule does not distinguish. Nothing stashes *R* anywhere: there is no chain, no
suppressed list, and neither the JVM nor javac warns.

</details>

**Q3.** An exception thrown from a `catch` block — is it protected from the `finally`?

<details><summary>Answer</summary>

No. The rule is about the whole `try` statement, not just the body, so a `catch` block's exception
propagating outward is exactly as abruptly-completing as the body's and is discarded by a `finally`
that throws in exactly the same way. The measured run is worse than the simple case: the original
`InsufficientFundsException` was destroyed by the `catch` block's translation, and the translation
was then destroyed by the `finally`, leaving a `RestrictedActionException` whose stack trace points
at `PaymentRunExportStream.close` — the same *type* the `catch` block built, from a completely
different place.

</details>

**Q4.** `finally` with a nested try/catch that logs each close failure keeps the primary alive. What
does it still lose?

<details><summary>Answer</summary>

The close failure never reaches the caller. It exists only as a log line, so the exception object
carries no evidence of it: an alert keyed on exception type never fires, a test asserting on the
thrown exception cannot see it, and a caller that wants to decide differently when the flush failed
has nothing to branch on. The measured run shows `getSuppressed().length = 0` on a primary that
propagated cleanly while the close failure went to standard output only.

</details>

**Q5.** `closeQuietly` calls `addSuppressed` exactly as the compiler does, so what does the manual
route still get wrong?

<details><summary>Answer</summary>

Close order, and the fact that you have to remember. The measured run closed the writer before the
export stream that depends on it: suppression worked and the primary survived, but the trailer write
hit a closed writer and *invented* an `IllegalStateException: ledgerWriter is closed` even though
neither resource was configured to fail. Try-with-resources closes in reverse declaration order by
construction, null-checks each resource, and closes every one of them even when an earlier close
throws — three guarantees the manual version re-implements by hand each time.

</details>

**Q6.** Does the same destruction happen with `return` instead of `throw` in the `finally`?

<details><summary>Answer</summary>

Yes — `return` is abrupt completion, so a `finally` that returns while an exception is in flight
discards the exception just as a `throw` does, and a `finally` that returns during a normal `return`
replaces the body's value outright. Reassigning the returned local inside `finally` is different and
changes nothing, because the value was already evaluated. That harness, with the bytecode, is leaf
4.6.8 in [The finally-return harness](03i-finally-return-harness.md).

</details>

---

## Open questions

- none

---

**Leaves covered:** 4.6.4 (1 leaf)
**Leaves deferred:** none
**Diagrams included:** none
**Target version:** Java 21 LTS
**Lines:** 658
