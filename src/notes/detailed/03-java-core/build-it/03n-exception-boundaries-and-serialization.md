# 03 Java Core — Exception builds — catch boundaries and the serial form — BUILD IT (§4.6.1)

**Target version: Java 21 LTS.** | **Part 4 of 5** | [Index](../00-index.md)
Previous: [Structured context, immutability, and the null policy](03m-exception-context-and-null-policy.md) · Next: [The stackless exception](03h-stackless-exception.md)

All numbers on this page were measured on **Oracle JDK 21.0.7 (build 21.0.7+8-LTS-245), macOS
aarch64 (Apple silicon)**, compressed oops on.

Leaf 4.6.1 runs across three files. This one holds the **boundary and the wire**: what a catch
clause can and cannot name, the narrowing pattern that spans two roots, which classes it is a
mistake to catch, and what survives a serialization round trip. The hierarchy is in
[`03c-exception-hierarchy-and-stackless.md`](03c-exception-hierarchy-and-stackless.md); the
structured context is in
[`03m-exception-context-and-null-policy.md`](03m-exception-context-and-null-policy.md).

---

## §4.6.1 `[BUILD]` The boundary, and the serial form

### The shape

Two facts about `catch` shape everything on this page, and the first one is a compiler rule rather
than a design opinion:

| Fact | Consequence for a two-root hierarchy |
|---|---|
| `catch` requires a `Throwable` subtype (JLS 14.20) | `DomainFailure`, the interface both roots implement, can never appear in a catch clause |
| A catch clause catches every subclass | catching your own base class catches the failures you cannot handle along with the ones you can |

So the boundary is written the other way round from how it reads in a design document: catch a real
`Throwable` type, then narrow with an `instanceof` pattern to reach the code and the context.

### The boundary, and why it cannot catch the interface

```java
static void twoRootsOneCatch() {
    Runnable[] sites = {
            () -> { throw new LedgerImbalanceException("LE-88214",
                    Money.gbp("4.20"), Money.gbp("4.19")); },
            () -> { throw new IllegalTransitionException(
                    ApplicationStatusCode.AA_699_DOCUMENTS_EXHAUSTED,
                    "AA-610 DOCUMENTS_UPLOADED", "AP-4471902"); }
    };
    for (Runnable site : sites) {
        try {
            site.run();
        } catch (RuntimeException e) {
            // catch cannot name an interface: JLS 14.20 requires the catch type to be a
            // subtype of Throwable. So the boundary catches a Throwable type and narrows.
            if (e instanceof DomainFailure f) {
                System.out.println("boundary caught " + f.errorCode().code()
                        + " structured=" + f.errorCode().structured()
                        + " -> " + e.getMessage());
            } else {
                throw e;
            }
        }
    }
    try {
        throw new BonusIneligibleException(ApplicationStatusCode.AO_139_DUPLICATE_IDENTITY,
                ClientId.of("3f2a1c88-0000-4000-8000-000000000002"), 1, "WELCOME10");
    } catch (QuizStakesException e) {
        System.out.println("boundary caught " + e.errorCode() + " -> " + e.getMessage());
    }
    try {
        throw new RestrictedActionException(ApplicationStatusCode.AA_599_SCREENING_PROHIBITED,
                ClientId.of("3f2a1c88-0000-4000-8000-000000000003"),
                new RestrictionKey(RestrictionType.STAKE_BLOCKED,
                        RestrictionSource.SYSTEM_COMPLIANCE));
    } catch (RestrictedActionException e) {
        System.out.println("boundary caught " + e.errorCode() + " reversible="
                + e.reversibleByOperator() + " blocking=" + e.blocking());
    }
}
```

```console
boundary caught LEDGER_IMBALANCE structured=null -> LEDGER_IMBALANCE [credits=GBP 4.19, debits=GBP 4.20, delta=GBP 0.01, entryId=LE-88214]
boundary caught AA-699 structured=AA-699 -> AA-699 DOCUMENTS_EXHAUSTED [applicationId=AP-4471902, attemptedTarget=AA-610 DOCUMENTS_UPLOADED, from=AA-699, terminal=true]
boundary caught AO-139 DUPLICATE_IDENTITY -> AO-139 DUPLICATE_IDENTITY [clientId=3f2a1c88-0000-4000-8000-000000000002, coupon=WELCOME10, depositOrdinal=1]
boundary caught AA-599 SCREENING_PROHIBITED reversible=true blocking=STAKE_BLOCKED/SYSTEM_COMPLIANCE
```

[`../exceptions/02d-logging-and-api-boundaries.md`](../exceptions/02d-logging-and-api-boundaries.md)
owns the boundary itself — the mapping from code to HTTP status, what goes in the response body
versus the log, and structured logging of the context map.
[`../exceptions/02b-designing-an-exception-hierarchy.md`](../exceptions/02b-designing-an-exception-hierarchy.md)
owns hierarchy design in full: how many roots, how deep, when to introduce a new class at all.

### Serialization

`Throwable` is `Serializable` with `serialVersionUID = -3042686055658047285L` ("use
serialVersionUID from JDK 1.0.2 for interoperability", `Throwable.java:117-119`). Every subclass
in the hierarchy declares its own `serialVersionUID = 1L`. `ErrorCode extends Serializable`, so
the code field is safe by the type system; the context values are bounded by
`Map<String, ? extends Serializable>` in the constructor. That bound is a **marker check, not a
guarantee** — `Serializable` says nothing about a type's contents.

```java
static byte[] write(Object o) throws Exception {
    ByteArrayOutputStream bytes = new ByteArrayOutputStream();
    try (ObjectOutputStream out = new ObjectOutputStream(bytes)) {
        out.writeObject(o);
    }
    return bytes.toByteArray();
}

static Object read(byte[] b) throws Exception {
    try (ObjectInputStream in = new ObjectInputStream(new ByteArrayInputStream(b))) {
        return in.readObject();
    }
}

/** A restriction whose "source" is an operator handle that forgot to implement Serializable.
 *  Its declared type satisfies the Serializable bound; its runtime content does not. */
static final class OperatorHandle {
    private final String badge;
    OperatorHandle(String badge) { this.badge = badge; }
    @Override public String toString() { return "operator:" + badge; }
}

static void cleanRoundTrip() throws Exception {
    InsufficientFundsException original = new InsufficientFundsException(
            ClientId.of("3f2a1c88-0000-4000-8000-000000000001"),
            Money.gbp("4.20"), Money.gbp("1.75"));
    byte[] wire = write(original);
    InsufficientFundsException revived = (InsufficientFundsException) read(wire);
    System.out.println("wire bytes         = " + wire.length);
    System.out.println("revived message    = " + revived.getMessage());
    System.out.println("revived shortfall  = " + revived.shortfall());
    System.out.println("revived code class = " + revived.errorCode().getClass().getName());
    System.out.println("code identity kept = "
            + (revived.errorCode() == DomainFault.INSUFFICIENT_FUNDS));
    System.out.println("context immutable  = " + revived.context().getClass().getName());
    System.out.println("frames preserved   = " + revived.getStackTrace().length);
}

static void nonSerializableValue() throws Exception {
    List<Object> holder = new ArrayList<>();
    holder.add(new OperatorHandle("OP-4417"));
    // ArrayList IS Serializable, so this passes the Map<String, Serializable> bound.
    Serializable smuggled = (Serializable) holder;
    LedgerImbalanceException fault = new LedgerImbalanceException(
            "LE-88213", Money.gbp("4.20"), Money.gbp("4.19"));
    Map<String, Serializable> ctx = Map.of("entryId", "LE-88213", "raisedBy", smuggled);
    FailureDetail detail = new FailureDetail(DomainFault.LEDGER_IMBALANCE, ctx);
    System.out.println("renders fine       = " + detail.renderMessage());
    System.out.println("fault renders fine = " + fault.getMessage());
    try {
        write(detail);
        System.out.println("round trip         = unexpectedly succeeded");
    } catch (NotSerializableException e) {
        System.out.println("round trip         = NotSerializableException: " + e.getMessage());
    }
}
```

Real output:

```console
wire bytes         = 1713
revived message    = INSUFFICIENT_FUNDS [clientId=3f2a1c88-0000-4000-8000-000000000001, requested=GBP 4.20, shortfall=GBP 2.45, stakeable=GBP 1.75]
revived shortfall  = GBP 2.45
revived code class = qs.DomainFault
code identity kept = true
context immutable  = java.util.ImmutableCollections$MapN
frames preserved   = 2
--
renders fine       = LEDGER_IMBALANCE [entryId=LE-88213, raisedBy=[operator:OP-4417]]
fault renders fine = LEDGER_IMBALANCE [credits=GBP 4.19, debits=GBP 4.20, delta=GBP 0.01, entryId=LE-88213]
round trip         = NotSerializableException: qs.SerializationRoundTrip$OperatorHandle
```

Four facts worth reading off that output. `code identity kept = true` because enum
deserialization resolves to the existing constant, so `==` on the code still works after a round
trip. `context immutable = ImmutableCollections$MapN` because the immutable map's serial proxy
reconstructs an immutable map, not a `HashMap` — the guarantee survives the wire.
`frames preserved = 2` because `Throwable.writeObject` writes the *materialised*
`StackTraceElement[]` (see `Throwable.java:936-1000`), so a revived exception has a trace even
though its `backtrace` is `transient`. And the failure mode is late: everything *renders* fine,
and the `NotSerializableException` arrives only at the moment you try to ship it.

The declared field type `Map<String, Serializable>` is not itself `Serializable`, so
`-Xlint:serial` warns. The suppression is deliberate and mirrors the JDK's own: `Throwable`
carries `@SuppressWarnings("serial") private List<Throwable> suppressedExceptions`
(`Throwable.java:234-235`) for exactly the same reason.

> **A boundary catches `Throwable` types and narrows to interfaces, never the reverse; and a
> domain exception's serial form preserves its code's identity, its context's immutability and its
> materialised frames, while guaranteeing nothing about what the context values themselves
> contain.**

### Diff vs the real one — the boundary and the serial form

| Aspect | This build | The JDK |
|---|---|---|
| Edge cases | zero-length and populated contexts both round-trip; `structured()` may be `null` after revival | `Throwable.readObject` (`Throwable.java:1028-1040`) must cope with a serial form whose `stackTrace` is `null`, and can substitute a one-element `SentinelHolder.STACK_TRACE_SENTINEL` meaning "a trace existed but was omitted" — a state no Java-level constructor can produce |
| Intrinsics | none | none; but `getOurStackTrace` materialises `StackTraceElement` objects from the VM-side `backtrace` via `StackTraceElement.of`, which is where the native boundary sits |
| Serialization | `serialVersionUID = 1L` per class; measured 1,713 bytes for a four-entry context; enum code identity preserved | `Throwable`'s `serialVersionUID` is frozen at the JDK 1.0.2 value `-3042686055658047285L`; `writeObject` walks the suppressed list, refuses to serialize a self-suppressing throwable, and hand-rolls the sentinel protocol |
| Null policy | `cause` may be null on the wire and revives as null | identical; `initCause` after revival throws `IllegalStateException` because `cause` is already set |
| Thread safety | the revived exception is deeply immutable, so it publishes safely | the revived `Throwable` is as mutable as any other; `readObject` deliberately assigns `UNASSIGNED_STACK.clone()` rather than the sentinel itself so that identity comparison in `getOurStackTrace` keeps working |
| Allocation tricks | none — `ObjectInputStream` rebuilds the `MapN` through its serial proxy | `ImmutableCollections`' `CollSer` proxy reconstructs the immutable form rather than a `HashMap`, which is why the immutability guarantee survives the wire at no extra cost |
| Why the JDK bothers | — | a `Throwable` crossing an RMI or a serialized-session boundary has to arrive with a readable trace on a JVM that never ran the frames, which is why `stackTrace` is materialised on write while `backtrace` stays `transient` |

The §4.6-wide diff table, leaf 4.6.9, lives in
[`03j-cleaner-and-diff.md`](03j-cleaner-and-diff.md).

---

## Pitfalls

### Catching the base class of your own hierarchy

**Wrong**

```java
try {
    ledger.post(entry);
    return reservation;
} catch (QuizStakesRuntimeException e) {      // "handle all our own failures here"
    log.warn("reservation failed: {}", e.errorCode().code());
    return Reservation.rejected();
}
```

`LedgerImbalanceException` and `IllegalTransitionException` share that base. The imbalance — an
invariant break that means money has been created or destroyed — is now downgraded to a WARN and
a rejected reservation. The system keeps trading on a broken ledger.

**Right**

Catch the classes you can actually handle, and let the rest through:

```java
try {
    ledger.post(entry);
    return reservation;
} catch (IllegalTransitionException e) {
    log.warn("reservation rejected: {} {}", e.errorCode().code(), e.attemptedTarget());
    return Reservation.rejected();
}
// LedgerImbalanceException propagates: nothing here can fix it
```

**Why people believe it:** a common base class is presented as the payoff for building a
hierarchy — "now you can catch everything in one place." The base class is for the *boundary*
that translates codes into responses and then stops the request, not for a mid-stack handler that
continues.

### Trying to catch the interface that unifies your hierarchy

**Wrong**

```java
try {
    reservations.reserve(clientId, stake);
} catch (DomainFailure f) {                 // the interface both roots implement
    respond(f.errorCode(), f.context());
}
```

It does not compile, and the message is worth recognising on sight because it looks like a generics
problem and is not:

```console
qs/HierarchyDemo.java:89: error: incompatible types: DomainFailure cannot be converted to Throwable
            } catch (DomainFailure f) {
                     ^
1 error
```

**Right**

Catch a real `Throwable` type and narrow with a pattern, rethrowing what you did not mean to
catch:

```java
} catch (RuntimeException e) {
    // catch cannot name an interface: JLS 14.20 requires the catch type to be a
    // subtype of Throwable. So the boundary catches a Throwable type and narrows.
    if (e instanceof DomainFailure f) {
        System.out.println("boundary caught " + f.errorCode().code()
                + " structured=" + f.errorCode().structured()
                + " -> " + e.getMessage());
    } else {
        throw e;
    }
}
```

The `else { throw e; }` is the part people drop, and dropping it silently converts a narrow
handler into a catch-all that swallows every unrelated `RuntimeException` in the block.

**Why people believe it:** every other place a type appears in Java, an interface is
interchangeable with a class — parameters, fields, generic bounds, `instanceof`. `catch` is the
exception, because the JVM's exception table stores a constant-pool class reference that the
verifier requires to be assignable to `Throwable`, and an arbitrary interface is not. The design
consequence is real rather than cosmetic: a two-root hierarchy genuinely has no single catch clause
that spans it.

### Reading `frames preserved = 2` as proof that the trace always survives

**Wrong**

```java
InsufficientFundsException revived = (InsufficientFundsException) read(write(original));
// "backtrace is transient, so the trace must be gone"
assert revived.getStackTrace().length == 0;
```

The assertion fails. Measured:

```console
frames preserved   = 2
```

The opposite mistake is just as common — assuming the trace always survives, and then being
surprised by a stackless exception, whose serial form legitimately carries zero frames because
`stackTrace` was `null` before it was ever written.

**Right**

Reason from what `writeObject` writes rather than from which fields are `transient`.
`Throwable.writeObject` calls the equivalent of `getOurStackTrace()` first, so the *materialised*
`StackTraceElement[]` goes on the wire even though the VM-side `backtrace` does not. So: a normal
exception's frames survive, a stackless one's do not, and the count you get back is whatever had
been materialised — never more than `MaxJavaStackTraceDepth`, which is 1024 by default on this
build.

**Why people believe it:** `private transient Object backtrace` is right there in the source, and
`transient` normally does mean "not serialized, therefore lost". It is true of `backtrace` and
false of the trace, because `Throwable` keeps two representations of the same information and
serializes the other one.

---

## Cheat sheet

| Thing | Value / rule |
|---|---|
| `catch (SomeInterface e)` | does not compile — JLS 14.20 requires a `Throwable` subtype |
| The javac error | `incompatible types: DomainFailure cannot be converted to Throwable` |
| The boundary pattern | catch a `Throwable` type, narrow with `instanceof`, `else { throw e; }` |
| The clause people forget | `else { throw e; }` — without it a narrow handler is a catch-all |
| Catching your own base | catches the failures you cannot handle; catch the classes you can |
| `LedgerImbalanceException` | never catch it below the top-level handler; the invariant is already broken |
| Round-trip size | 1,713 bytes for a four-entry context |
| Enum code identity | preserved — `revived.errorCode() == DomainFault.INSUFFICIENT_FUNDS` is `true` |
| Context class after revival | `java.util.ImmutableCollections$MapN` — immutability survives the wire |
| Frames after revival | 2, because `writeObject` writes the materialised `StackTraceElement[]` |
| `backtrace` | `transient` and lost; irrelevant, because the other representation is written |
| `Serializable` bound | a marker check only; `NotSerializableException` arrives at write time |
| `Throwable.serialVersionUID` | `-3042686055658047285L`, frozen at the JDK 1.0.2 value |
| Where leaf 4.6.1 continues | hierarchy in `03c`, context and null policy in `03m` |

## Self-test

**Q3.** Why can `catch (DomainFailure f)` not compile, and what do you write instead?

<details><summary>Answer</summary>

JLS 14.20 requires the type of a `catch` parameter to be `Throwable` or a subclass of it (or a
type variable whose bound is). `DomainFailure` is an interface, so it is not, regardless of the
fact that every implementer is a `Throwable`. javac says `incompatible types: DomainFailure
cannot be converted to Throwable`. You catch a real `Throwable` type — `RuntimeException`, or
`Exception` at a true boundary — and narrow with a pattern: `catch (RuntimeException e) { if (e
instanceof DomainFailure f) { handle(f); } else { throw e; } }`. The `else throw e` matters;
without it
you have quietly become a catch-all.

</details>

**Q5.** `ErrorCode extends Serializable`. Does that guarantee the exception round-trips?

<details><summary>Answer</summary>

No. It guarantees the *code* field round-trips, which is worth having — and because the codes are
enums, deserialization resolves to the existing constant, so `revived.errorCode() ==
DomainFault.INSUFFICIENT_FUNDS` is still `true`. It says nothing about the context values.
`Serializable` is a marker interface with no methods and no contract about contents: an
`ArrayList` satisfies the bound and then throws `NotSerializableException` at write time if it
holds one object that does not. The measured failure was
`NotSerializableException: qs.SerializationRoundTrip$OperatorHandle`, raised only at
`writeObject` time — the exception rendered its message perfectly right up to that point.

</details>

**Q3.** The boundary demo throws four times but uses three different catch clauses. Why can the
first two share one and the last two not?

<details><summary>Answer</summary>

Because the first two are unchecked and the last two are checked, and that decides what a catch
clause is allowed to name. `LedgerImbalanceException` and `IllegalTransitionException` both extend
`QuizStakesRuntimeException`, so they can be thrown from inside a `Runnable` — whose `run()`
declares no checked exceptions — and caught together as `RuntimeException`, then narrowed to
`DomainFailure`. `BonusIneligibleException` and `RestrictedActionException` extend
`QuizStakesException`, so they cannot go through a `Runnable` at all, and each is caught at the
type the call site actually needs: `QuizStakesException` where only the code matters,
`RestrictedActionException` itself where the handler wants `blocking()` and
`reversibleByOperator()`. The general point is that the two-root split is visible at every catch
site, not just in the class declarations — which is the real cost of needing both checked and
unchecked members in one family.

</details>

**Q4.** After a round trip, `revived.errorCode() == DomainFault.INSUFFICIENT_FUNDS` is `true`. Why
does reference equality survive deserialization here when it generally does not?

<details><summary>Answer</summary>

Because the code is an enum constant, and enum deserialization is special-cased: the serial form
carries the enum's class and the constant's *name*, and `readObject` resolves it through
`Enum.valueOf` rather than allocating a new instance. So the revived reference points at the same
singleton the running JVM already had. This is the same guarantee that makes the enum singleton
pattern safe against serialization attacks, and it is why an enum is the right type for an error
code that crosses a process boundary: a `record` code carrying the same four components would
revive as a distinct object and `==` would be `false`, forcing every downstream comparison to use
`equals`. It also means a `switch` on the revived code still works, and that a code removed from
the enum in a later version fails loudly with `InvalidObjectException` rather than silently
deserializing into something meaningless.

</details>

**Q5.** Why is catching `QuizStakesRuntimeException` at a mid-stack handler worse than catching
nothing at all?

<details><summary>Answer</summary>

Because it converts an unrecoverable failure into a plausible-looking success path.
`LedgerImbalanceException` and `IllegalTransitionException` share that base; the first means debits
did not equal credits, so money has been created or destroyed. A handler that catches the base
class, logs at WARN and returns `Reservation.rejected()` reports a routine rejection to the caller
and a warning to the log, and the system keeps trading on a broken ledger. Catching nothing would
have let it reach the top-level handler, which stops the request and pages someone — strictly
better. The base class exists for the *boundary* that translates codes into responses and then
terminates the request, not for a mid-stack handler that continues; a mid-stack handler should name
the classes it can actually do something about, which here is `IllegalTransitionException` and not
the imbalance.

</details>

## Open questions

- none

---

**Leaves covered:** 4.6.1, part 3 of 3 — the catch boundary, the narrowing pattern, and the serial form (1 leaf, shared with `03c-exception-hierarchy-and-stackless.md` and `03m-exception-context-and-null-policy.md`)
**Leaves deferred:** none
**Diagrams included:** none
**Target version:** Java 21 LTS
**Lines:** 453
