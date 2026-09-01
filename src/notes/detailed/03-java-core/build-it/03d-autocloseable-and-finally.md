# 03 Java Core — Exception builds — a custom `AutoCloseable`, close order, and suppression — BUILD IT (§4.6.3)

**Target version: Java 21 LTS.** | **Part 4 of 5** | [Index](../00-index.md)
Previous: [The stackless exception](03h-stackless-exception.md) · Next: [How finally destroys the primary exception](03l-finally-destroys-the-primary.md)

Two resources open in a bank-withdrawal `PaymentRun` export: a `LedgerBatchWriter` holding a
buffered batch of `Movement` rows, and a `PaymentRunExportStream` holding a reservation and owing a
trailer. The body throws `InsufficientFundsException`; both `close()` calls still have real work to
do, and one of them fails too.

Try-with-resources is a **compiler rewrite**, not a runtime feature. It closes in **reverse
declaration order**, and when a `close()` fails while an exception is already in flight it **adds**
the close failure to the primary via `Throwable.addSuppressed` instead of replacing it. Both halves
of that sentence are the file: the order, because resource two was constructed from resource one;
and the addition, because a cleanup failure must not be allowed to overwrite the failure that caused
the cleanup. What `finally` does instead — discard the primary outright — is
[How finally destroys the primary exception](03l-finally-destroys-the-primary.md), leaf 4.6.4.
Everything below was compiled and run on **Oracle JDK 21.0.7 (build 21.0.7+8-LTS-245), macOS
aarch64** and all output is pasted from the run.

---

## 4.6.3 A custom `AutoCloseable` with an idempotent `close()` `[PROVE]`

### What the javadoc actually says

Read this before writing the guard, because the received wisdom overstates it. From the JDK 21
`java.lang.AutoCloseable.close()` javadoc (`$JAVA_HOME/lib/src.zip`,
`java.base/java/lang/AutoCloseable.java`):

> Note that unlike the `close` method of `Closeable`, this `close` method is *not* required to be
> idempotent. In other words, calling this `close` method more than once may have some visible side
> effect, unlike `Closeable.close` which is required to have no effect if called more than once.
>
> However, implementers of this interface are strongly encouraged to make their `close` methods
> idempotent.

Three separate facts, and interviews conflate them:

| Type | Idempotence | Source |
|---|---|---|
| `java.io.Closeable.close()` | **required** to have no effect if called more than once | `Closeable` javadoc |
| `java.lang.AutoCloseable.close()` | **not required**; "strongly encouraged" | `AutoCloseable` javadoc, quoted above |
| The try-with-resources statement | calls `close()` **at most once** per resource | JLS 14.20.3 desugaring |

The language will not call your `close()` twice; the *program* will, because a caller closed
explicitly inside the block and the generated code closed again on the way out — the most common
route to a double close, demonstrated below. The javadoc also advises marking the resource closed
*before* throwing, so a failing close still releases what it can.

**Insight:** `AutoCloseable` also makes no promise about *which thread* calls `close()`. Nothing in
the interface says the closing thread is the opening thread — a resource handed to an executor, or
closed by a `Cleaner` action, or closed by a shutdown hook, is closed by a different thread.

### The non-idempotent version, and what it costs

`close()` here genuinely does work: it flushes the buffered batch to `FundsLedger`. Failing to
close loses the batch; closing twice posts it twice.

```java
static final class NaiveLedgerBatchWriter implements AutoCloseable {
    private final String name;
    private final FundsLedger ledger;
    private final List<ExportRow> buffer = new ArrayList<>();

    NaiveLedgerBatchWriter(String name, FundsLedger ledger) {
        this.name = name;
        this.ledger = ledger;
    }

    void write(String position, long minorUnits) {
        buffer.add(new ExportRow(position, minorUnits));
    }

    @Override
    public void close() {
        System.out.println("  " + name + ".close() entered, flushing " + buffer.size() + " buffered rows");
        ledger.post(buffer);
    }
}
```

The sink and the row type, in full:

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

Driver — a caller that closes explicitly, as callers do:

```java
FundsLedger ledger = new FundsLedger();
try (NaiveLedgerBatchWriter w = new NaiveLedgerBatchWriter("naiveWriter", ledger)) {
    w.write("BANK_SETTLEMENT", 26000);
    w.write("BANK_SETTLEMENT", 18000);
    w.close();
}
System.out.println("  ledger.postedEntries=" + ledger.postedEntries
        + " postedMinorUnits=" + ledger.postedMinorUnits);
```

Real output:

```console
  naiveWriter.close() entered, flushing 2 buffered rows
    FundsLedger.post: 2 rows, running total 2 entries / 44000 minor units
  naiveWriter.close() entered, flushing 2 buffered rows
    FundsLedger.post: 2 rows, running total 4 entries / 88000 minor units
  ledger.postedEntries=4 postedMinorUnits=88000
```

Two bank withdrawals worth 440.00 posted as 880.00 — money created, caught downstream as a
`LedgerImbalanceException` in a reconciliation job hours later with nothing pointing back here.

### The guard, and what kind of flag it needs

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

Which flag, precisely:

| Flag | Guarantees | Use when |
|---|---|---|
| plain `boolean closed` | nothing across threads; two threads can both read `false` and both flush; a later reader may never see `true` at all | single-threaded ownership *and* you are willing to write that down |
| `volatile boolean closed` | visibility only. `if (!closed) { closed = true; flush(); }` is still a read-modify-write race — both threads can pass the check | you need the *state* visible (a `write()` on another thread must see the resource is closed) but closes are serialized by construction |
| `AtomicBoolean` + `compareAndSet` | exactly one caller wins, on any thread, always | the general case, which is what a library type must assume |

Note the ordering inside the guard: the flag flips **before** the flush, so a `close()` that throws
partway through still leaves the resource marked closed — the javadoc's "relinquish the underlying
resources and internally *mark* the resource as closed, prior to throwing the exception".

Same driver, guarded type:

```console
  ledgerWriter.close() entered, flushing 2 buffered rows
    FundsLedger.post: 2 rows, running total 2 entries / 44000 minor units
  ledgerWriter.close() entered, already closed, returning
  ledger.postedEntries=2 postedMinorUnits=44000
```

### The second resource, which depends on the first

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

### The two-resource harness

```java
static void twr(boolean bodyThrows, boolean writerFails, boolean streamFails) {
    FundsLedger ledger = new FundsLedger();
    try (LedgerBatchWriter writer = new LedgerBatchWriter("ledgerWriter", ledger, writerFails);
         PaymentRunExportStream export = new PaymentRunExportStream("paymentRunExport", writer, ledger, streamFails)) {
        export.exportWithdrawal(26000);
        export.exportWithdrawal(18000);
        if (bodyThrows) {
            throw new InsufficientFundsException(
                    "withdrawable 18000 below requested 26000",
                    Map.of("position", "CLIENT_CASH_AVAILABLE", "requested", 26000L));
        }
        System.out.println("  body completed normally");
    } catch (RuntimeException e) {
        report(e);
    }
    System.out.println("  ledger.postedEntries=" + ledger.postedEntries
            + " openReservations=" + ledger.openReservations);
}
```

`report(e)` prints the caught exception's simple name and message as `caught primary:`, then
`e.getSuppressed().length`, then one `suppressed[i] =` line per entry, then `e.printStackTrace(System.out)`
between `--- printStackTrace ---` and `--- end ---` markers. Every console block below is its output.
The scratch program wraps each case in its own named method, which is what the stack traces name.

### Close order: reverse of declaration

Body throws, both closes succeed:

```console
  paymentRunExport opened, reservation taken, openReservations=1
  paymentRunExport.close() entered, writing trailer for 2 rows
    reservation released, openReservations=0
  ledgerWriter.close() entered, flushing 3 buffered rows
    FundsLedger.post: 3 rows, running total 3 entries / 43998 minor units
  caught primary: InsufficientFundsException: withdrawable 18000 below requested 26000
  getSuppressed().length = 0
  --- printStackTrace ---
ResourceBuilds$InsufficientFundsException: withdrawable 18000 below requested 26000
	at ResourceBuilds.twr(ResourceBuilds.java:211)
	at ResourceBuilds.main(ResourceBuilds.java:364)
  --- end ---
  ledger.postedEntries=3 openReservations=0
```

`paymentRunExport` was declared second and closed first. Three rows flushed, not two — the third is
the trailer `CLIENT_CASH_RESERVED -2` that `paymentRunExport.close()` wrote *through* the writer.
That is why reverse is the only sane order: declaration order is construction order and therefore
dependency order, and unwinding a dependency graph means going backwards. Reverse it and the
trailer write hits a closed writer.

### Suppression: the close failure is added, not substituted

Body throws, and `paymentRunExport.close()` throws too:

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
	at ResourceBuilds.twr(ResourceBuilds.java:211)
	at ResourceBuilds.main(ResourceBuilds.java:366)
	Suppressed: ResourceBuilds$RestrictedActionException: WITHDRAWAL_HELD from SYSTEM_COMPLIANCE applied mid-run
		at ResourceBuilds$PaymentRunExportStream.close(ResourceBuilds.java:172)
		at ResourceBuilds.twr(ResourceBuilds.java:204)
		... 1 more
  --- end ---
  ledger.postedEntries=3 openReservations=0
```

Two facts in that trace. The primary is still the body's `InsufficientFundsException` — the real
failure survives. And `ledgerWriter.close()` **still ran** after `paymentRunExport.close()` threw:
try-with-resources closes every resource regardless of what the earlier closes did, so the batch was
not lost.

The mechanism, self-contained: `Throwable` carries a `suppressedExceptions` list; `addSuppressed(t)`
appends to it, `getSuppressed()` returns a defensive copy as an array, and `printStackTrace` renders
each entry as an indented `Suppressed:` block with a fold line for the frames shared with the
enclosing trace. The language feature is owned by
[`../exceptions/01c-try-with-resources-and-suppression.md`](../exceptions/01c-try-with-resources-and-suppression.md).

Two edges that bite: `addSuppressed(this)` throws `IllegalArgumentException` and
`addSuppressed(null)` throws `NullPointerException`; and a `Throwable` built with
`enableSuppression = false` through the four-argument protected constructor **silently discards**
suppressed exceptions, so making your domain base suppressionless for speed makes the close failure
above vanish without a word. That constructor is owned by
[The stackless exception](03h-stackless-exception.md).

### Body succeeds and a close throws — the genuine surprise

```console
  paymentRunExport opened, reservation taken, openReservations=1
  body completed normally
  paymentRunExport.close() entered, writing trailer for 2 rows
    reservation released, openReservations=0
  ledgerWriter.close() entered, flushing 3 buffered rows
    FundsLedger.post: 3 rows, running total 3 entries / 43998 minor units
  caught primary: RestrictedActionException: WITHDRAWAL_HELD from SYSTEM_COMPLIANCE applied mid-run
  getSuppressed().length = 0
  --- printStackTrace ---
ResourceBuilds$RestrictedActionException: WITHDRAWAL_HELD from SYSTEM_COMPLIANCE applied mid-run
	at ResourceBuilds$PaymentRunExportStream.close(ResourceBuilds.java:172)
	at ResourceBuilds.twr(ResourceBuilds.java:214)
	at ResourceBuilds.main(ResourceBuilds.java:365)
  --- end ---
```

With no primary to attach to, the close failure **is** the primary — try-with-resources does not
swallow close failures, and suppression only happens when an exception is already in flight. If the
body returns a value and the close then throws, the caller sees the exception and never the value,
which is right for a `close()` that flushes: the flush is part of the operation succeeding.

### Both closes throw — two suppressed, in close order

```console
  caught primary: InsufficientFundsException: withdrawable 18000 below requested 26000
  getSuppressed().length = 2
    suppressed[0] = RestrictedActionException: WITHDRAWAL_HELD from SYSTEM_COMPLIANCE applied mid-run
    suppressed[1] = LedgerImbalanceException: batch debits 4200 do not match credits 4180
  --- printStackTrace ---
ResourceBuilds$InsufficientFundsException: withdrawable 18000 below requested 26000
	at ResourceBuilds.twr(ResourceBuilds.java:211)
	at ResourceBuilds.main(ResourceBuilds.java:367)
	Suppressed: ResourceBuilds$RestrictedActionException: WITHDRAWAL_HELD from SYSTEM_COMPLIANCE applied mid-run
		at ResourceBuilds$PaymentRunExportStream.close(ResourceBuilds.java:172)
		at ResourceBuilds.twr(ResourceBuilds.java:204)
		... 1 more
	Suppressed: ResourceBuilds$LedgerImbalanceException: batch debits 4200 do not match credits 4180
		at ResourceBuilds$LedgerBatchWriter.close(ResourceBuilds.java:126)
		at ResourceBuilds.twr(ResourceBuilds.java:204)
		... 1 more
  --- end ---
```

Suppressed order is close order, so reverse declaration order. Nothing is lost: one primary, two
suppressed, three distinct failures reportable from one catch.

### A `null` resource expression

```java
FundsLedger ledger = new FundsLedger();
LedgerBatchWriter absent = null;
try (LedgerBatchWriter writer = absent) {
    System.out.println("  body ran, writer == null is " + (writer == null));
}
System.out.println("  no NPE on close; ledger.postedEntries=" + ledger.postedEntries);
```

```console
  body ran, writer == null is true
  no NPE on close; ledger.postedEntries=0
```

No NPE, verified on 21.0.7: the generated code null-checks each resource before calling `close()`
(JLS 14.20.3.1 specifies the `if (r != null) r.close()` shape), so a possibly-absent resource needs
no `if (writer != null)` of your own.

### The Java 9 form: an existing effectively-final variable

```java
FundsLedger ledger = new FundsLedger();
LedgerBatchWriter writer = new LedgerBatchWriter("ledgerWriter", ledger, false);
writer.write("BANK_SETTLEMENT", 26000);
try (writer) {
    System.out.println("  body ran with an effectively final existing variable");
}
System.out.println("  ledger.postedEntries=" + ledger.postedEntries);
```

```console
  body ran with an effectively final existing variable
  ledgerWriter.close() entered, flushing 1 buffered rows
    FundsLedger.post: 1 rows, running total 1 entries / 26000 minor units
  ledger.postedEntries=1
```

**Version note.** Java 7 and 8 accepted only the *declaration* form, `try (Type name = expr)`, whose
variable is implicitly `final` — you cannot reassign it in the body. Java 9 (JEP 213) added the
*variable* form, `try (existingVar)`, requiring final or effectively final. Older material shows only
the declaration form, so `try (writer; export)` reads as a syntax error to anyone taught on 8.

### What the compiler generates `[BYTECODE]`

`javap -c -p` on a one-resource `try (writer) { }` shows no `finally` at all. The resource reference
is copied into a fresh never-reassigned local (what "implicitly final" buys the compiler); the body
runs; then an `ifnull`-guarded `invokeinterface` of `close()` on the **normal** path; and, under an
exception-table row covering the body with handler type `Throwable`, a second copy of the same
`ifnull`-guarded close on the **exceptional** path, itself wrapped in an exception-table row whose
handler does `aload` primary, `aload` close-failure, `invokevirtual Throwable.addSuppressed`, then
`athrow` of the **primary**. Two resources nest that shape, the outer range covering the body *and*
the inner resource's close — which is why an inner close failure still triggers the outer close. No
synthetic `$closeResource` helper appears on JDK 21's javac; the sequence is inlined per resource
(verified by grepping the `javap -c -p` output of a four-resource version for `closeResource`: zero
hits). The full listing and the desugaring history are owned by
[`../exceptions/03a-internals-finally-and-twr-desugaring.md`](../exceptions/03a-internals-finally-and-twr-desugaring.md).

**Interview:** "Does try-with-resources use `finally` under the hood?" No. It generates explicit
exception-table ranges plus a duplicated normal-path close, because `finally` cannot express "close,
and if that throws, attach it to the exception I am already carrying".

### Diff vs the real one

Against `java.io.BufferedOutputStream` and `java.util.zip.ZipOutputStream`, the JDK types with the
same shape — buffered, flush-on-close, wrapping:

| Axis | These builds | The JDK's closeable streams |
|---|---|---|
| Edge cases | one flag, one flush; `write` after close throws `IllegalStateException` | `FilterOutputStream.close` uses a `try (out)` on the delegate so the flush failure is suppressed onto the close failure; `write` after close throws `IOException("Stream closed")` |
| Intrinsics | none | none in `close()`; `BufferedOutputStream`'s buffer copies go through intrinsified `System.arraycopy` |
| Serialization | none; buffer is a plain `ArrayList` | streams are not serializable at all — a closed-over stream field breaks `Serializable` classes, which is why they are `transient` |
| Null policy | `List.copyOf` and `Map.copyOf` reject nulls; the resource expression itself may be `null` and the generated null check handles it | `Objects.requireNonNull` on wrapped streams at construction; `FilterOutputStream` tolerates a null delegate only until first use |
| Thread safety | `AtomicBoolean` makes close once-only; the buffer is **not** guarded, so concurrent `write` is unsafe | `BufferedOutputStream` synchronizes on the instance (JDK 21 uses a `closed` flag plus internal locking); `Closeable.close` is contractually idempotent, not contractually concurrent-safe |
| Allocation tricks | `List.copyOf(buffer)` allocates one array per close | JDK streams reuse one `byte[]` for the lifetime; `Channels`/`ByteBuffer` paths avoid the copy entirely |
| Why the JDK bothers | it does not ship a ledger writer | the flush-on-close contract is the only reason buffered output is correct; the suppression rewrite is the only mechanism that reports a flush failure without losing the exception that caused the early exit |

> **Definition.** A well-behaved `AutoCloseable` releases its resource and marks itself closed
> exactly once, no matter how many callers call `close()` or from which thread, and reports a
> release failure by throwing — leaving try-with-resources to decide whether that throw becomes the
> primary exception or a suppressed one.

The section-wide §4.6 diff table lives in
[The Cleaner-based holder and the §4.6 diff table](03j-cleaner-and-diff.md) (leaf 4.6.9).

---

## Pitfalls

### A non-idempotent `close()` that a caller also closes explicitly

**Wrong**

```java
try (NaiveLedgerBatchWriter w = new NaiveLedgerBatchWriter("naiveWriter", ledger)) {
    w.write("BANK_SETTLEMENT", 26000);
    w.write("BANK_SETTLEMENT", 18000);
    w.close();      // "be tidy, flush early"
}
```

```console
  naiveWriter.close() entered, flushing 2 buffered rows
    FundsLedger.post: 2 rows, running total 2 entries / 44000 minor units
  naiveWriter.close() entered, flushing 2 buffered rows
    FundsLedger.post: 2 rows, running total 4 entries / 88000 minor units
  ledger.postedEntries=4 postedMinorUnits=88000
```

440.00 of bank withdrawals posted as 880.00.

**Right**

```java
private final AtomicBoolean closed = new AtomicBoolean(false);

@Override
public void close() {
    if (!closed.compareAndSet(false, true)) {
        return;
    }
    List<ExportRow> batch = List.copyOf(buffer);
    buffer.clear();
    ledger.post(batch);
}
```

```console
  ledgerWriter.close() entered, flushing 2 buffered rows
    FundsLedger.post: 2 rows, running total 2 entries / 44000 minor units
  ledgerWriter.close() entered, already closed, returning
  ledger.postedEntries=2 postedMinorUnits=44000
```

**Why people believe it:** `java.io.Closeable` *requires* idempotence, and almost every closeable
type a Java developer touches is a `Closeable`, so "close twice is free" is true of everything they
have met. `AutoCloseable` only *encourages* it, and a domain resource you wrote yourself is exactly
where the encouragement was ignored.

### Believing a suppressed exception gets logged by default

**Wrong**

```java
} catch (InsufficientFundsException e) {
    log.error("payment run failed: {}", e.getMessage());
}
```

Output: `payment run failed: withdrawable 18000 below requested 26000`. The
`RestrictedActionException` from the close is attached to `e` and appears nowhere in the log.

**Right**

```java
} catch (InsufficientFundsException e) {
    log.error("payment run failed", e);                  // renders Suppressed: blocks
    for (Throwable closeFailure : e.getSuppressed()) {   // and act on them
        ledgerAlarms.raise(closeFailure);
    }
}
```

**Why people believe it:** suppressed exceptions *do* show up during development, because unhandled
exceptions reach the default handler, which calls `printStackTrace`. The moment a `catch` logs
`e.getMessage()` — or the message without the throwable — the suppressed list is invisible. Nothing
prints it on its own.

### Believing resources close in declaration order

**Wrong**

Hand-rolled cleanup that closes in the order the resources were declared, which is what someone who
believes try-with-resources does the same thing will write:

```java
LedgerBatchWriter writer = new LedgerBatchWriter("ledgerWriter", ledger, false);
PaymentRunExportStream export = new PaymentRunExportStream("paymentRunExport", writer, ledger, false);
try {
    export.exportWithdrawal(26000);
} finally {
    writer.close();   // declaration order: the dependency first
    export.close();
}
```

```console
  paymentRunExport opened, reservation taken, openReservations=1
  ledgerWriter.close() entered, flushing 1 buffered rows
    FundsLedger.post: 1 rows, running total 1 entries / 26000 minor units
  paymentRunExport.close() entered, writing trailer for 1 rows
Exception in thread "main" java.lang.IllegalStateException: ledgerWriter is closed
	at ResourceBuilds$LedgerBatchWriter.write(ResourceBuilds.java:108)
	at ResourceBuilds$PaymentRunExportStream.close(ResourceBuilds.java:166)
	at ResourceBuilds.declarationOrderClose(ResourceBuilds.java:346)
	at ResourceBuilds.main(ResourceBuilds.java:373)
```

The trailer write hits a closed writer, the reservation is never released, and the stream's `closed`
flag is already `true`, so a retry will not fix it.

**Right**

Declare in dependency order — the thing others depend on first — and let the compiler's reverse-order
close unwind it:

```java
try (LedgerBatchWriter writer = new LedgerBatchWriter("ledgerWriter", ledger, false);
     PaymentRunExportStream export = new PaymentRunExportStream("paymentRunExport", writer, ledger, false)) {
    export.exportWithdrawal(26000);
}
System.out.println("  ledger.postedEntries=" + ledger.postedEntries);
```

```console
  paymentRunExport opened, reservation taken, openReservations=1
  paymentRunExport.close() entered, writing trailer for 1 rows
    reservation released, openReservations=0
  ledgerWriter.close() entered, flushing 2 buffered rows
    FundsLedger.post: 2 rows, running total 2 entries / 25999 minor units
  ledger.postedEntries=2
```

**Why people believe it:** every other list in Java is processed front to back, and the resource
list *looks* like a list of statements. It is a stack, and the compiler pops it.

---

## Cheat sheet

| Fact | Value |
|---|---|
| `Closeable.close()` idempotent | **required** |
| `AutoCloseable.close()` idempotent | **not required**, "strongly encouraged" |
| Times try-with-resources calls `close()` | at most once, per resource |
| Which thread calls `close()` | unspecified; not promised to be the opening thread |
| Close order | reverse of declaration |
| Body throws, close throws | body's exception is primary; close failure via `addSuppressed` |
| Body succeeds, close throws | close failure **is** the primary |
| Both closes throw | two suppressed, in close order |
| Later closes after an earlier close throws | still run; try-with-resources closes every resource |
| `null` resource expression | generated `ifnull` skip; no NPE, no close |
| Suppressed printed | only by something printing the primary's full trace |
| `enableSuppression = false` | `addSuppressed` silently no-ops |
| Syntax | Java 7/8: declaration form only; Java 9+: also `try (effectivelyFinalVar)` |
| Bytecode shape | duplicated close paths + exception-table rows + `Throwable.addSuppressed`; no `finally`, no `$closeResource` on 21 |
| Guard flag choice | `AtomicBoolean.compareAndSet` for the general case; `volatile boolean` only for visibility of state |

---

## Self-test

**Q1.** In a two-resource try-with-resources where the body throws and *both* `close()` calls throw,
how many exceptions reach the caller and in what relationship?

<details><summary>Answer</summary>

One: the body's exception, as the primary. Both close failures are attached via `addSuppressed`, so
`getSuppressed().length == 2`, ordered by close order — reverse declaration order, so the
last-declared resource's failure is `suppressed[0]`. The measured run prints
`InsufficientFundsException` as primary with `RestrictedActionException` then
`LedgerImbalanceException` as the two `Suppressed:` blocks. Nothing is lost.

</details>

**Q2.** The body of a try-with-resources completes normally and one `close()` throws. What does the
method do?

<details><summary>Answer</summary>

It throws the close failure. There is no primary for it to be suppressed onto, so the close failure
*is* the primary: statements after the block do not run and a value the body assigned is never
returned. Correct behaviour for a `close()` that flushes — the operation did not succeed until the
flush did.

</details>

**Q3.** `AutoCloseable.close()` is not required to be idempotent and try-with-resources calls it at
most once. So why guard it?

<details><summary>Answer</summary>

Because the *program* calls it more than once even though the language does not: a caller that
closes explicitly inside the block for tidiness, a resource closed by a `Cleaner` action or shutdown
hook as well as by its owner, a wrapper whose `close()` closes a delegate something else also
closes. With a flushing `close()` the second call re-posts the batch — the measured run turned 44000
minor units into 88000. The javadoc's "strongly encouraged" is about this, not about the language.

</details>

**Q4.** `volatile boolean closed` or `AtomicBoolean`?

<details><summary>Answer</summary>

`AtomicBoolean` with `compareAndSet` for anything a second thread might close. `volatile` gives
visibility but not atomicity, so `if (!closed) { closed = true; flush(); }` still lets two threads
both read `false` and both flush. `volatile` is the right choice when other methods must *observe*
the closed state promptly but closes are serialized by construction. A plain `boolean` is acceptable
only under documented single-thread ownership — and `AutoCloseable` makes no promise that `close()`
runs on the thread that opened the resource.

</details>

**Q5.** Why does declaration order in the resource list have to be dependency order?

<details><summary>Answer</summary>

Because close order is the reverse. A resource constructed *from* an earlier one — an export stream
writing its trailer through a ledger batch writer — must finish before the resource it depends on is
closed, so declaring the dependency first means it is closed last. The measured run shows the writer
flushing **three** rows, not two: the third is the trailer written during the stream's own close.

</details>

**Q6.** What happens when the resource expression evaluates to `null`, and what does that let you
delete?

<details><summary>Answer</summary>

Nothing happens: the generated code null-checks each resource before calling `close()` — JLS
14.20.3.1 specifies the `if (r != null) r.close()` shape, visible as an `ifnull` on both the normal
and the exceptional close paths — so there is no NPE and no close. The measured run prints
`writer == null is true` and completes. That deletes the `if (writer != null)` you would otherwise
write in a `finally`, which is one of the few pieces of hand-rolled cleanup that is *purely*
redundant rather than merely risky.

</details>

**Q7.** Team convention says every custom exception base sets `enableSuppression = false` for speed.
What breaks?

<details><summary>Answer</summary>

Every suppressed exception is silently discarded: `addSuppressed` becomes a no-op and
`getSuppressed()` always returns empty, so a close failure attached by try-with-resources disappears
with no error and no log line — the same information loss as a bare `finally`, but built into the
exception type and invisible at the call site. See
[The stackless exception](03h-stackless-exception.md).

</details>

---

## Open questions

- none

---

**Leaves covered:** 4.6.3 (1 leaf)
**Leaves deferred:** none
**Diagrams included:** none
**Target version:** Java 21 LTS
**Lines:** 753
