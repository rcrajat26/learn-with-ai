# 03 Java Core — Exception builds — a domain hierarchy with error codes and structured context — BUILD IT (§4.6.1)

**Target version: Java 21 LTS.** | **Part 4 of 5** | [Index](../00-index.md)
Previous: [The values() cache and the §4.5 diff table](03b-enum-values-cache-and-diff.md) · Next: [Structured context, immutability, and the null policy](03m-exception-context-and-null-policy.md)

All numbers on this page were measured on **Oracle JDK 21.0.7 (build 21.0.7+8-LTS-245), macOS
aarch64 (Apple silicon)**, compressed oops on.

Leaf 4.6.1 runs across three files. This one holds the **hierarchy itself**: the two abstract
roots, the error code's type and the `XX-Nnn` structure, the five domain exceptions, and the
checked-versus-unchecked decision per exception. The structured context, its defensive copy, the
null policy and the derived `getMessage()` are in
[`03m-exception-context-and-null-policy.md`](03m-exception-context-and-null-policy.md); the catch
boundary and the serial form are in
[`03n-exception-boundaries-and-serialization.md`](03n-exception-boundaries-and-serialization.md).

---

## The family, before the details

Six classes, two roots. The two roots are forced, not chosen: Java has no way to put shared
state in one place when half the hierarchy must extend `Exception` and half must extend
`RuntimeException`.

| Class | Root | Checked | Error code carried | Can a caller recover? |
|---|---|---|---|---|
| `QuizStakesException` | `Exception` | yes | any `ErrorCode` | abstract base |
| `QuizStakesRuntimeException` | `RuntimeException` | no | any `ErrorCode` | abstract base |
| `InsufficientFundsException` | checked base | yes | `INSUFFICIENT_FUNDS` | yes — offer a smaller stake |
| `RestrictedActionException` | checked base | yes | `AA-599 SCREENING_PROHIBITED` | yes — translate to a refusal |
| `BonusIneligibleException` | checked base | yes | `AO-139 DUPLICATE_IDENTITY` | yes — complete the deposit, no bonus |
| `IllegalTransitionException` | runtime base | no | the current-state code, e.g. `AA-699` | no — the caller has a bug |
| `LedgerImbalanceException` | runtime base | no | `LEDGER_IMBALANCE` | no — the double-entry invariant broke |

Both roots implement one interface, `DomainFailure`, so a boundary can read the code and the
context off either half without knowing which branch it came from. What that interface cannot do
is appear in a `catch` clause — a fact this file proves rather than asserts.

Supporting types: `StatusCode` (the `XX-Nnn` record), `ErrorCode` (the interface),
`ApplicationStatusCode` and `DomainFault` (the two code enums), `FailureDetail` (the shared
payload, held by composition).

---

## §4.6.1 `[BUILD]` The hierarchy: an error code and structured context, not a formatted message

### The shape and the reason

A formatted message is a one-way function. You take a client id, an amount and a shortfall, you
run them through `String` concatenation, and what comes out is a sentence. The sentence goes in a
log. Everything a caller could have branched on is now behind a regex.

The same failure, twice:

```java
/** The same failure, formatted. Everything the caller needs is now inside a String. */
static void formattedForm(ClientId id) {
    try {
        throw new IllegalStateException("Insufficient funds: client " + id
                + " has 1.75 but needs 4.20");
    } catch (IllegalStateException e) {
        System.out.println("formatted : " + e.getMessage());
        System.out.println("  shortfall a caller can branch on: none, it is inside the text");
    }
}

/** The same failure, structured. */
static void structuredForm(ClientId id) {
    try {
        throw new InsufficientFundsException(id, Money.gbp("4.20"), Money.gbp("1.75"));
    } catch (InsufficientFundsException e) {
        System.out.println("structured: " + e.getMessage());
        System.out.println("  code             = " + e.errorCode().code());
        System.out.println("  shortfall        = " + e.shortfall());
        System.out.println("  offer instead    = " + e.stakeable());
        System.out.println("  api body         = {\"code\":\"" + e.errorCode().code()
                + "\",\"shortfall\":\"" + e.shortfall().amount() + "\"}");
    }
}
```

Real output:

```console
formatted : Insufficient funds: client 3f2a1c88-0000-4000-8000-000000000001 has 1.75 but needs 4.20
  shortfall a caller can branch on: none, it is inside the text
structured: INSUFFICIENT_FUNDS [clientId=3f2a1c88-0000-4000-8000-000000000001, requested=GBP 4.20, shortfall=GBP 2.45, stakeable=GBP 1.75]
  code             = INSUFFICIENT_FUNDS
  shortfall        = GBP 2.45
  offer instead    = GBP 1.75
  api body         = {"code":"INSUFFICIENT_FUNDS","shortfall":"2.45"}
```

The two things the formatted form cannot do, concretely:

1. **A caller deciding on the shortfall.** `e.shortfall()` returns a `Money`. The formatted form
   would need `Pattern.compile("has ([0-9.]+) but needs")`, which breaks the first time somebody
   adds a currency symbol to the message. And notice the message never even *contained* the
   shortfall — 2.45 is derived in the constructor. The formatted form would have had to think of
   printing it.
2. **A stable error contract.** The structured form's `code()` is the API's error identifier. It
   is a fixed string, tested, documented, and unaffected by anyone rewording the message.
   Reword the formatted message and every client parsing it breaks silently.

**Insight:** the derived `getMessage()` is what makes this safe rather than merely tidy. The
message is *computed* from code plus context on every call, so there is no second copy of the
facts that can drift out of step with the first.

### The value types the context carries

Every context value must be `Serializable`, so the domain's value types declare it. Nothing here
is novel — they are the ordinary records — but the five exceptions below will not compile without
them, so they ship in full:

```java
public record Money(BigDecimal amount, Currency currency) implements Serializable {
    private static final long serialVersionUID = 1L;
    public static final Currency GBP = Currency.getInstance("GBP");

    public static Money gbp(String amount) { return new Money(new BigDecimal(amount), GBP); }

    public Money minus(Money other) {
        if (!currency.equals(other.currency)) throw new IllegalArgumentException("currency mismatch");
        return new Money(amount.subtract(other.amount), currency);
    }

    public boolean lessThan(Money other) { return amount.compareTo(other.amount) < 0; }

    @Override public String toString() { return currency.getCurrencyCode() + " " + amount; }
}

public record ClientId(UUID value) implements Serializable {
    private static final long serialVersionUID = 1L;
    public static ClientId of(String uuid) { return new ClientId(UUID.fromString(uuid)); }
    @Override public String toString() { return value.toString(); }
}

/** Restriction identity is the pair (type, source), never the type alone. */
public record RestrictionKey(RestrictionType type, RestrictionSource source) implements Serializable {
    private static final long serialVersionUID = 1L;
    @Override public String toString() { return type + "/" + source; }
}

public enum RestrictionType {
    DEPOSIT_BLOCKED, STAKE_BLOCKED, WITHDRAWAL_BLOCKED, DEPOSIT_LIMITED, WITHDRAWAL_HELD,
    SOURCE_OF_FUNDS_REQUIRED, ALL_BLOCKED, SELF_EXCLUDED, COOLING_OFF, DORMANT_FROZEN
}

public enum RestrictionSource {
    SYSTEM_ONBOARDING, SYSTEM_COMPLIANCE, SYSTEM_LIFECYCLE, ADMIN, CLIENT
}
```

`Money.minus` is what `InsufficientFundsException` calls to derive its shortfall and
`LedgerImbalanceException` calls to derive its delta, which is the reason both are computed in the
constructor rather than left to the caller.
[`04-value-objects-and-money.md`](04-value-objects-and-money.md) owns `Money` properly — scale,
rounding, and the currency check this version does the minimum of.

### Decision 1: the error code's type

Three candidates, and the choice is not a matter of taste:

| Option | Compile-time safety | Exhaustive switch | Wire-stable | Cost |
|---|---|---|---|---|
| `String code` | none — a typo compiles | no | yes | free; every call site can invent a code |
| `enum` constant | full | yes | yes, via a declared code string | one enum per code family |
| `StatusCode(domain, phase, disposition, variant)` record | partial — components validated, values not | no | yes, via `render()` | the code space is open; nothing stops `ZZ-000` |

The build uses **all three, layered**: an `enum` for the closed set of published codes, each
constant holding a validated `StatusCode` record, each rendering a `String` for the wire. The
enum gives you the exhaustive `switch` at the API boundary; the record gives you the structural
predicate (`blocked()`); the string is what crosses the network.

```java
/** The domain's numbered-code shape: XX-Nnn, where N is the phase, the middle digit the
 *  disposition (0 in progress, 1 success, 5 referred to a human, 9 failed or blocked). */
public record StatusCode(String domain, int phase, int disposition, int variant)
        implements java.io.Serializable {

    private static final long serialVersionUID = 1L;

    public StatusCode {
        if (domain == null) throw new NullPointerException("domain");
        if (domain.length() < 2 || domain.length() > 3)
            throw new IllegalArgumentException("domain must be 2-3 letters: " + domain);
        requireDigit(phase, "phase");
        requireDigit(disposition, "disposition");
        requireDigit(variant, "variant");
    }

    private static void requireDigit(int v, String what) {
        if (v < 0 || v > 9) throw new IllegalArgumentException(what + " must be 0-9: " + v);
    }

    public static StatusCode parse(String rendered) {
        int dash = rendered.indexOf('-');
        if (dash < 0 || rendered.length() - dash != 4)
            throw new IllegalArgumentException("not an XX-Nnn code: " + rendered);
        String dom = rendered.substring(0, dash);
        return new StatusCode(dom,
                rendered.charAt(dash + 1) - '0',
                rendered.charAt(dash + 2) - '0',
                rendered.charAt(dash + 3) - '0');
    }

    public String render() {
        return domain + "-" + phase + disposition + variant;
    }

    /** True when the documented middle-digit disposition says failed-or-blocked. */
    public boolean failedByDisposition() {
        return disposition == 9;
    }

    /** True when either the disposition digit or the variant digit carries the 9 marker. The
     *  published catalogue uses both conventions - see the note in the text. */
    public boolean blocked() {
        return disposition == 9 || variant == 9;
    }

    @Override
    public String toString() {
        return render();
    }
}
```

**Pitfall:** the first version of `blocked()` asserted `disposition == 9` and the enum's
constructor threw `AssertionError: AO-119 is not a 9-disposition code` at class-initialisation
time. The published catalogue is not internally consistent about where the failure marker goes.
`AA-599`, `AA-690`, `AA-699`, `AA-799` and `AO-099` put it in the middle digit as documented;
`AO-119 AGE_INELIGIBLE`, `AO-129 JURISDICTION_INELIGIBLE`, `AO-139 DUPLICATE_IDENTITY` and
`AO-149 WEALTH_REJECTED` put it in the last digit, with a middle digit of `1`. Symptom: an
`AssertionError` inside `<clinit>`, which surfaces as `ExceptionInInitializerError` at the first
use of the enum and is spectacularly hard to read. Fix: accept both conventions in the predicate,
keep the strict one available as `failedByDisposition()`, and write the ambiguity down instead of
letting an assertion encode a rule the data does not follow.

```java
/** A stable, searchable, branchable identifier for one failure mode. Extends Serializable
 *  because it is a field of a Throwable, and Throwable is Serializable. */
public interface ErrorCode extends java.io.Serializable {
    /** The wire form: "AA-599" for a numbered code, "LEDGER_IMBALANCE" for a bare-name one. */
    String code();

    /** The human-readable constant name, e.g. "SCREENING_PROHIBITED". */
    String label();

    /** The XX-Nnn breakdown, or null for a bare-name code that has no numbered form. */
    StatusCode structured();
}
```

```java
/** Every 9-disposition code the application catalogue publishes. Verbatim; nothing invented. */
public enum ApplicationStatusCode implements ErrorCode {
    AO_099_UNIQUENESS_FAILED("AO-099", "UNIQUENESS_FAILED"),
    AO_119_AGE_INELIGIBLE("AO-119", "AGE_INELIGIBLE"),
    AO_129_JURISDICTION_INELIGIBLE("AO-129", "JURISDICTION_INELIGIBLE"),
    AO_139_DUPLICATE_IDENTITY("AO-139", "DUPLICATE_IDENTITY"),
    AO_149_WEALTH_REJECTED("AO-149", "WEALTH_REJECTED"),
    AA_599_SCREENING_PROHIBITED("AA-599", "SCREENING_PROHIBITED"),
    AA_690_DOCUMENTS_REJECTED("AA-690", "DOCUMENTS_REJECTED"),
    AA_699_DOCUMENTS_EXHAUSTED("AA-699", "DOCUMENTS_EXHAUSTED"),
    AA_799_REVIEW_DECLINED("AA-799", "REVIEW_DECLINED");

    private final String code;
    private final String label;
    private final StatusCode structured;

    ApplicationStatusCode(String code, String label) {
        this.code = code;
        this.label = label;
        this.structured = StatusCode.parse(code);
        if (!structured.blocked())
            throw new AssertionError(code + " carries no 9 failure marker");
    }

    @Override public String code() { return code; }
    @Override public String label() { return label; }
    @Override public StatusCode structured() { return structured; }
    @Override public String toString() { return code + " " + label; }
}
```

The catalogue publishes `9`-disposition codes only in the `AO-` and `AA-` families. The `DEP-`
and `BDP-` families exist but are not enumerated at that disposition, so the money faults get
**bare-name codes** — the same style the domain already uses for its bare-name state machines —
rather than a fabricated `DEP-399`:

```java
/** Failures the numbered catalogue does not publish a 9-disposition code for. Bare-name codes,
 *  in the same style as the domain's bare-name machines. No XX-Nnn code is invented for them. */
public enum DomainFault implements ErrorCode {
    INSUFFICIENT_FUNDS,
    LEDGER_IMBALANCE;

    @Override public String code() { return name(); }
    @Override public String label() { return name(); }
    @Override public StatusCode structured() { return null; }
    @Override public String toString() { return name(); }
}
```

### Decision 2: checked or unchecked, per exception

The rule that actually works: **checked when the immediate caller has a sensible non-exceptional
continuation; unchecked when nobody up the stack does.** Applied honestly:

| Exception | Choice | Because | Cost of getting it wrong the other way |
|---|---|---|---|
| `InsufficientFundsException` | checked | the stake site can offer a smaller stake or prompt a deposit; the compiler should make it say which | unchecked: a missed catch turns a routine rejection into a 500 and an alert page |
| `RestrictedActionException` | checked | an expected outcome of a legitimate call; the API layer must map it to a refusal | unchecked: a `SELF_EXCLUDED` client gets a 500 instead of a refusal, which is a regulatory problem |
| `BonusIneligibleException` | checked | the deposit must complete whether or not the bonus grants | unchecked: a silently swallowed ineligibility leaves the deposit path looking successful with no bonus and no record |
| `IllegalTransitionException` | unchecked | reaching it means the caller asked the machine for a transition it forbids: a bug | checked: every transition call site grows a `catch` that can only log and rethrow |
| `LedgerImbalanceException` | unchecked | debits did not equal credits; there is no recovery anywhere | checked: `throws` pollutes the entire ledger write path and someone eventually catches it to keep the signature clean |

**Interview:** "when do you use a checked exception?" The answer that lands is not "for
recoverable errors" — that is the javadoc, and it begs the question. It is: *checked when the
call site's correct behaviour differs from just propagating.* If every honest handler is
`catch (e) { throw new RuntimeException(e); }`, the exception should have been unchecked.

`BonusIneligibleException` is the interesting one, because the honest answer is that it should
not be an exception at all. A first-deposit bonus that does not qualify is a *decision*, not a
failure, and a `Result<Bonus, ErrorCode>` models it without unwinding anything.
[`02a-generic-containers.md`](02a-generic-containers.md) builds that `Result<T,E>` with
`map`/`flatMap`/`fold`, and the four workarounds for a checked exception crossing a `Function`
boundary. This file builds the exceptions that alternative competes with; when both fit, the
`Result` usually wins.

### The two roots, and the interface that unifies them

The payload every failure carries — the `ErrorCode` and the immutable context map — cannot live in
a shared superclass, because there is no shared superclass to put it in. It lives in a composed
`FailureDetail`, built in full in
[`03m-exception-context-and-null-policy.md`](03m-exception-context-and-null-policy.md); the two
roots below delegate to it. What *can* be shared is an interface both roots implement:

```java
/** Implemented by both roots of the hierarchy, so one catch clause can span checked and
 *  unchecked branches when a boundary genuinely must handle everything. */
public interface DomainFailure {
    ErrorCode errorCode();
    Map<String, Serializable> context();
    Serializable contextValue(String key);
}
```

```java
/** Checked root: the caller has a plausible recovery and the compiler should say so. */
public abstract class QuizStakesException extends Exception implements DomainFailure {

    private static final long serialVersionUID = 1L;

    private final FailureDetail detail;

    protected QuizStakesException(ErrorCode errorCode,
                                  Map<String, ? extends Serializable> context) {
        this(errorCode, context, null);
    }

    protected QuizStakesException(ErrorCode errorCode,
                                  Map<String, ? extends Serializable> context,
                                  Throwable cause) {
        super(null, cause);
        this.detail = new FailureDetail(errorCode, context);
    }

    /** Stackless variant: writableStackTrace = false. Suppression stays on. */
    protected QuizStakesException(ErrorCode errorCode,
                                  Map<String, ? extends Serializable> context,
                                  Throwable cause,
                                  boolean writableStackTrace) {
        super(null, cause, true, writableStackTrace);
        this.detail = new FailureDetail(errorCode, context);
    }

    @Override public final ErrorCode errorCode() { return detail.errorCode(); }
    @Override public final Map<String, Serializable> context() { return detail.context(); }
    @Override public final Serializable contextValue(String key) { return detail.contextValue(key); }

    @Override public final String getMessage() { return detail.renderMessage(); }
}
```

```java
/** Unchecked root: an invariant broke or the caller made a programming error. Nobody up the
 *  stack can recover, so forcing every frame to declare it buys nothing. */
public abstract class QuizStakesRuntimeException extends RuntimeException implements DomainFailure {

    private static final long serialVersionUID = 1L;

    private final FailureDetail detail;

    protected QuizStakesRuntimeException(ErrorCode errorCode,
                                         Map<String, ? extends Serializable> context) {
        this(errorCode, context, null);
    }

    protected QuizStakesRuntimeException(ErrorCode errorCode,
                                         Map<String, ? extends Serializable> context,
                                         Throwable cause) {
        super(null, cause);
        this.detail = new FailureDetail(errorCode, context);
    }

    @Override public final ErrorCode errorCode() { return detail.errorCode(); }
    @Override public final Map<String, Serializable> context() { return detail.context(); }
    @Override public final Serializable contextValue(String key) { return detail.contextValue(key); }

    @Override public final String getMessage() { return detail.renderMessage(); }
}
```

Note `super(null, cause)` in both: the stored `detailMessage` is deliberately `null`, and
`getMessage()` is `final` and derived. Two copies of the facts cannot drift when there is only
one copy.

**Pitfall:** `catch (DomainFailure f)` does not compile. JLS 14.20 requires a catch parameter's
type to be `Throwable` or a subclass, and an interface is neither, however many `Throwable`
subclasses implement it. Symptom: `error: incompatible types: DomainFailure cannot be converted
to Throwable`. Fix: catch a real `Throwable` type and narrow with a pattern.

[`03n-exception-boundaries-and-serialization.md`](03n-exception-boundaries-and-serialization.md)
ships the boundary that does the narrowing, with the real javac error and the captured output.

### The five domain exceptions

```java
/** CHECKED. A stake reservation whose stakeable total does not cover the stake. The caller can
 *  recover: offer a smaller stake, or prompt a deposit. */
public final class InsufficientFundsException extends QuizStakesException {

    private static final long serialVersionUID = 1L;

    public InsufficientFundsException(ClientId clientId, Money requested, Money stakeable) {
        super(DomainFault.INSUFFICIENT_FUNDS, Map.of(
                "clientId", clientId,
                "requested", requested,
                "stakeable", stakeable,
                "shortfall", requested.minus(stakeable)));
    }

    /** The typed accessor a caller branches on. No regex over a message. */
    public Money shortfall() { return (Money) contextValue("shortfall"); }

    public Money stakeable() { return (Money) contextValue("stakeable"); }
}
```

```java
/** CHECKED. A money action blocked by an active restriction. Expected outcome of a legitimate
 *  call; the API layer must translate it, not 500 on it. */
public final class RestrictedActionException extends QuizStakesException {

    private static final long serialVersionUID = 1L;

    public RestrictedActionException(ErrorCode errorCode, ClientId clientId, RestrictionKey blocking) {
        super(errorCode, Map.of(
                "clientId", clientId,
                "restriction", blocking,
                "reversibleByOperator", blocking.type() != RestrictionType.SELF_EXCLUDED));
    }

    public RestrictionKey blocking() { return (RestrictionKey) contextValue("restriction"); }

    public boolean reversibleByOperator() { return (Boolean) contextValue("reversibleByOperator"); }
}
```

```java
/** CHECKED. A first-deposit bonus grant that does not qualify. The caller always has a sensible
 *  continuation - complete the deposit with no bonus - so the compiler should make it say so. */
public final class BonusIneligibleException extends QuizStakesException {

    private static final long serialVersionUID = 1L;

    public BonusIneligibleException(ErrorCode errorCode, ClientId clientId,
                                    int depositOrdinal, String coupon) {
        super(errorCode, Map.of(
                "clientId", clientId,
                "depositOrdinal", depositOrdinal,
                "coupon", coupon));
    }

    public int depositOrdinal() { return (Integer) contextValue("depositOrdinal"); }
}
```

```java
/** UNCHECKED. A transition the state machine does not permit. Reaching this means the caller
 *  asked for something the machine forbids: a bug, not a business outcome. */
public final class IllegalTransitionException extends QuizStakesRuntimeException {

    private static final long serialVersionUID = 1L;

    public IllegalTransitionException(ApplicationStatusCode from, String attemptedTarget,
                                      String applicationId) {
        super(from, Map.of(
                "applicationId", applicationId,
                "from", from.code(),
                "attemptedTarget", attemptedTarget,
                "terminal", true));
    }

    public String attemptedTarget() { return (String) contextValue("attemptedTarget"); }
}
```

```java
/** UNCHECKED. Debits did not equal credits. The double-entry invariant broke; no caller
 *  anywhere up the stack can put it back. Fail loudly, write nothing further. */
public final class LedgerImbalanceException extends QuizStakesRuntimeException {

    private static final long serialVersionUID = 1L;

    public LedgerImbalanceException(String entryId, Money debits, Money credits) {
        super(DomainFault.LEDGER_IMBALANCE, Map.of(
                "entryId", entryId,
                "debits", debits,
                "credits", credits,
                "delta", debits.minus(credits)));
    }

    public BigDecimal delta() { return ((Money) contextValue("delta")).amount(); }
}
```

`RestrictedActionException` deliberately takes the `ErrorCode` rather than hard-coding one: the
same class covers `AA-599 SCREENING_PROHIBITED` on a compliance block and `AA-699
DOCUMENTS_EXHAUSTED` on an onboarding one. `IllegalTransitionException` uses the *current state's*
code as the error code, which is the right choice — the interesting fact is where you were, not
where you were going.

> **A domain exception hierarchy is a choice made twice per class: which root it extends, which
> decides whether the compiler forces callers to acknowledge it; and which error code it carries,
> which decides whether anyone downstream can branch on it.**

### Diff vs the real one — §4.6.1

| Aspect | This build | The JDK / a mature framework |
|---|---|---|
| Edge cases | one code per constant, both digit conventions accepted, `structured()` may be `null` | `SQLException(String reason, String SQLState, int vendorCode)` carries a five-char SQLState *and* a vendor int, plus an `Iterable` chain of *sibling* exceptions via `getNextException()` — a shape this build has no equivalent of |
| Intrinsics | none | none either; exception construction is ordinary Java plus one native `fillInStackTrace(int)` |
| Serialization | `serialVersionUID = 1L` per class, `Serializable` bound on values, enum identity survives | `Throwable`'s `serialVersionUID = -3042686055658047285L` is frozen at the JDK 1.0.2 value; its `writeObject` reconstructs `stackTrace` and `suppressedExceptions` through a hand-written protocol with an out-of-band `SentinelHolder.STACK_TRACE_SENTINEL` |
| Null policy | `errorCode` and `context` non-null, values non-null via `Map.of`/`Map.copyOf`, `cause` nullable | `Throwable` allows a null message and a null cause; `NoSuchFileException` allows a null `other` and a null `reason` and documents each |
| Thread safety | the exception is deeply immutable after construction, so it publishes safely | `Throwable` is *mutable*: `fillInStackTrace`, `setStackTrace`, `addSuppressed` and `initCause` are all `synchronized` on the throwable, precisely because it is not |
| Allocation tricks | none — one `FailureDetail`, one `MapN`, `n` entries | `UNASSIGNED_STACK` and `SUPPRESSED_SENTINEL` are shared singletons so an unfilled throwable allocates no array and no list; `backtrace` is a `transient` VM-side structure so `StackTraceElement` objects are built lazily on first read |
| Why the JDK bothers | — | `Throwable` must work when the heap is exhausted (`OutOfMemoryError`), which is why the sentinels exist and why the four-argument constructor exists at all — its javadoc names `OutOfMemoryError`, `NullPointerException` and `ArithmeticException` as the motivating cases |

The §4.6-wide diff table — "how the JDK's own resource classes handle these cases", leaf 4.6.9 —
lives in [`03j-cleaner-and-diff.md`](03j-cleaner-and-diff.md).

---

## Pitfalls

### Formatting the message and losing the data

**Wrong**

```java
throw new IllegalStateException("Insufficient funds: client " + id
        + " has 1.75 but needs 4.20");
```

```console
Insufficient funds: client 3f2a1c88-0000-4000-8000-000000000001 has 1.75 but needs 4.20
```

The caller wants to offer a smaller stake. The only route to the number is
`Pattern.compile("has ([0-9.]+) but needs")`, which breaks when someone adds a currency prefix,
and the shortfall of 2.45 was never in the string at all.

**Right**

```java
throw new InsufficientFundsException(id, Money.gbp("4.20"), Money.gbp("1.75"));
// caller:
catch (InsufficientFundsException e) {
    return Offer.reduceTo(e.stakeable());   // typed Money, no parsing
}
```

```console
INSUFFICIENT_FUNDS [clientId=3f2a1c88-0000-4000-8000-000000000001, requested=GBP 4.20, shortfall=GBP 2.45, stakeable=GBP 1.75]
```

The message is *derived* from the same fields the caller reads, so it can never disagree with
them.

**Why people believe it:** `getMessage()` is the one accessor every logging framework already
calls, so putting everything in it looks like the way to make sure the information survives. It
does survive — as text, to a human, once.

### Making everything unchecked, as a policy

**Wrong**

```java
// "checked exceptions are a failed experiment, so nothing in this codebase is checked"
public final class InsufficientFundsException extends QuizStakesRuntimeException { }
public final class RestrictedActionException extends QuizStakesRuntimeException { }
public final class BonusIneligibleException extends QuizStakesRuntimeException { }
```

Three of the five now compile at every call site without a word from the compiler. A stake
reservation that legitimately rejects for insufficient funds propagates to the top-level handler
and returns a 500. A `SELF_EXCLUDED` client asking to stake gets a 500 rather than a refusal,
which in a regulated platform is a reportable defect rather than a bug. And a first deposit whose
bonus does not qualify silently completes with no bonus and no record, because nothing forced the
deposit path to decide what to do.

**Right**

Decide per class, on whether the immediate caller's correct behaviour differs from propagating:

```java
public final class InsufficientFundsException extends QuizStakesException { }        // checked
public final class RestrictedActionException extends QuizStakesException { }         // checked
public final class BonusIneligibleException extends QuizStakesException { }          // checked
public final class IllegalTransitionException extends QuizStakesRuntimeException { } // unchecked
public final class LedgerImbalanceException extends QuizStakesRuntimeException { }   // unchecked
```

The two unchecked ones earn it: an illegal transition is a caller bug and a ledger imbalance is a
broken invariant, and neither has a handler anywhere up the stack that could do better than
propagate.

**Why people believe it:** the argument against checked exceptions is real and well made — they
leak into signatures, they do not compose with lambdas, and they get "handled" by being wrapped in
a `RuntimeException` two frames up. All true, and all an argument against checked exceptions *for
failures nobody can recover from*, which is the majority. Turning that into a blanket policy
throws away the compiler's help on exactly the minority where it pays.

### Inventing a status code because the catalogue does not publish one

**Wrong**

```java
// no 9-disposition DEP- code exists, so make one up that "looks right"
DEP_399_INSUFFICIENT_FUNDS("DEP-399", "INSUFFICIENT_FUNDS"),
```

It parses, `blocked()` returns `true`, and it renders as `DEP-399 INSUFFICIENT_FUNDS`. It is also
now in log aggregation queries, dashboards and an API error contract, and it means nothing to the
team that owns the deposit domain. When they eventually assign `DEP-399` to something real, two
different failures share one code and every query built on it is silently wrong.

**Right**

Use a bare-name code, which the domain already does for its state machines, and leave the numbered
space to whoever owns it:

```java
public enum DomainFault implements ErrorCode {
    INSUFFICIENT_FUNDS,
    LEDGER_IMBALANCE;

    @Override public String code() { return name(); }
    @Override public String label() { return name(); }
    @Override public StatusCode structured() { return null; }
}
```

`structured()` returning `null` is the honest signal: this code has no numbered form yet. A caller
that needs the phase or the disposition can test for `null` instead of parsing a fiction.

**Why people believe it:** the structure is documented — `XX-Nnn`, `9` for failed or blocked — and
a documented structure feels like a licence to generate members of it. It is a licence to *parse*
them, not to mint them; the code space is a shared namespace, and the published list is the only
authority for what is in it.

---

## Cheat sheet

| Thing | Value / rule |
|---|---|
| Checked when | the call site's correct behaviour differs from just propagating. Unchecked when every honest handler would be `catch (e) { throw new RuntimeException(e); }` |
| Two roots, why | no class extends both `Exception` and `RuntimeException`; the shared payload goes in a composed `FailureDetail` |
| Error-code type | enum for the closed set, a `StatusCode(domain, phase, disposition, variant)` record inside each constant, a `String` on the wire |
| Code structure | `XX-Nnn`; disposition `0` in progress, `1` success, `5` referred, `9` failed or blocked |
| Catalogue caveat | `AA-599`/`AA-690`/`AA-699`/`AA-799`/`AO-099` mark failure in the middle digit; `AO-119`/`AO-129`/`AO-139`/`AO-149` mark it in the last |
| Money-family codes | no `9`-disposition `DEP-`/`BDP-` code is published, so money faults use bare-name codes and `structured()` returns `null`. Never invent one |
| `IllegalTransitionException`'s code | the *current* state, not the attempted target |
| `catch (SomeInterface e)` | does not compile; JLS 14.20 wants a `Throwable` subtype |
| The five, at a glance | `InsufficientFunds`, `RestrictedAction`, `BonusIneligible` checked; `IllegalTransition`, `LedgerImbalance` unchecked |
| Message policy | `super(null, cause)`; `getMessage()` is `final` and derived — see `03m` |
| Where leaf 4.6.1 continues | context and null policy in `03m`, boundary and serial form in `03n` |
| Where the §4.6 diff table lives | leaf 4.6.9, in `03j-cleaner-and-diff.md` |

## Self-test

**Q4.** The hierarchy has two abstract roots. Why not one, and what does the split cost you?

<details><summary>Answer</summary>

Because "checked" and "unchecked" are decided by which class you extend, and no class is a
subclass of both `Exception` and `RuntimeException`. If you want `InsufficientFundsException`
checked and `LedgerImbalanceException` unchecked, they cannot share a superclass below
`Exception`. The split costs three things: the shared payload has to live in a separate object
(`FailureDetail`) held by composition, both roots have to duplicate the same six delegating
methods, and — the real cost — there is no single `catch` clause that spans both, because the
`DomainFailure` interface that unifies them cannot appear in a `catch`.

</details>

**Q2.** The catalogue's `AO-119` broke an assertion in the enum's constructor. What did that look
like at runtime, and what is the general lesson?

<details><summary>Answer</summary>

`AssertionError: AO-119 is not a 9-disposition code`, thrown from `ApplicationStatusCode.<init>`
inside `<clinit>` — which reaches the caller as `ExceptionInInitializerError` at the first touch of
the enum, possibly in an unrelated code path, with the real cause a level down. The catalogue is
not internally consistent: `AA-599`, `AA-690`, `AA-699`, `AA-799` and `AO-099` put the `9` in the
middle digit; `AO-119`, `AO-129`, `AO-139` and `AO-149` put it in the last, with a middle digit of
`1`. The lesson: an assertion in a static initialiser encodes a rule about *data you do not
control*, and its failure mode is maximally obscure. Model the rule the data follows, and keep the
strict one as `failedByDisposition()`.

</details>

**Q3.** Give the rule for checked versus unchecked that survives contact with a real codebase, and
apply it to `LedgerImbalanceException`.

<details><summary>Answer</summary>

Checked when the immediate caller's correct behaviour differs from simply propagating; unchecked
when it does not. The usual formulation — "checked for recoverable errors" — begs the question,
because "recoverable" is exactly what is in dispute. The operational test: if every honest handler
you can imagine writing is `catch (e) { throw new RuntimeException(e); }`, the exception should
have been unchecked, because a checked one has only added noise to signatures. Applied to
`LedgerImbalanceException`: debits did not equal credits, so money has been created or destroyed
and the double-entry invariant is broken. No caller — not the reservation service, not the API
layer, not the top-level handler — can restore it. Making it checked would put `throws` on every
method in the ledger write path, and the predictable result is that somebody catches it to keep a
signature clean, which is the worst possible outcome for this particular failure. Unchecked, it
propagates to the top-level handler, which stops the request and pages someone.

</details>

**Q4.** Why is the error code an enum whose constants each hold a `StatusCode` record, rather than
just an enum, or just the record?

<details><summary>Answer</summary>

Because the three candidates each give you exactly one of the three things you need. A plain
`String` is wire-stable and free, and offers no compile-time safety at all — any call site can
invent a code and it compiles. A bare `StatusCode(domain, phase, disposition, variant)` record
validates its components but not their *values*: nothing stops `ZZ-000`, because the code space it
describes is open. An enum alone gives you the closed set and the exhaustive `switch` at the API
boundary, but says nothing about structure, so you cannot ask "is this a failure code?" without a
lookup table. Layering them gets all three: the enum closes the set and enables the exhaustive
`switch`, the `StatusCode` inside each constant supplies the structural predicate `blocked()`, and
`code()` renders the `String` that crosses the network. The cost is one enum per code family and a
`StatusCode.parse` in each constructor — which is where the `AO-119` inconsistency surfaced, at
class-initialisation time rather than in production.

</details>

**Q5.** `IllegalTransitionException` carries `AA-699 DOCUMENTS_EXHAUSTED` when someone attempts a
move to `AA-610 DOCUMENTS_UPLOADED`. Why the current state rather than the attempted target?

<details><summary>Answer</summary>

Because the current state is the fact that explains the refusal, and the attempted target is
merely what was asked for. `AA-699 DOCUMENTS_EXHAUSTED` is terminal: the application has run out
of document attempts, and *no* transition out of it is permitted. Coding the exception by the
target would produce a different code for every attempted move out of the same dead state, which
fragments the very grouping an operator needs — "how many applications are stuck at
`AA-699` and still being poked?" becomes unanswerable. Coding it by the source answers that
question directly, and the attempted target is still in the context map under `attemptedTarget`
for anyone who needs it. The general rule: the error code should name the condition, and the
context should carry the request.

</details>

## Open questions

- none

---

**Leaves covered:** 4.6.1, part 1 of 3 — the hierarchy, the error-code type, and the checked-versus-unchecked decision (1 leaf, shared with `03m-exception-context-and-null-policy.md` and `03n-exception-boundaries-and-serialization.md`)
**Leaves deferred:** none
**Diagrams included:** none
**Target version:** Java 21 LTS
**Lines:** 791
