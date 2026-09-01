# 03 Java Core — Exception builds — structured context, immutability, and the null policy — BUILD IT (§4.6.1)

**Target version: Java 21 LTS.** | **Part 4 of 5** | [Index](../00-index.md)
Previous: [A domain exception hierarchy](03c-exception-hierarchy-and-stackless.md) · Next: [Catch boundaries and the serial form](03n-exception-boundaries-and-serialization.md)

All numbers on this page were measured on **Oracle JDK 21.0.7 (build 21.0.7+8-LTS-245), macOS
aarch64 (Apple silicon)**, compressed oops on.

Leaf 4.6.1 runs across three files. This one holds the **structured context**: the `FailureDetail`
carrier, the defensive copy that makes it immutable, the null policy and its enforcement, and the
derived `getMessage()`. The hierarchy and its two roots are in
[`03c-exception-hierarchy-and-stackless.md`](03c-exception-hierarchy-and-stackless.md); the catch
boundary and the serial form are in
[`03n-exception-boundaries-and-serialization.md`](03n-exception-boundaries-and-serialization.md).

---

## §4.6.1 `[BUILD]` The context carrier: immutable, typed, and the message derived from it

### The shape

One object holds everything a failure knows, and it is not a `Throwable`. That is forced: the
hierarchy has two roots, `Exception` and `RuntimeException`, and no class extends both, so shared
state has to be composed rather than inherited. What gets composed is three things and a rule:

| Piece | Type | Rule |
|---|---|---|
| the code | `ErrorCode` | non-null, `Serializable`, supplies `code()`, `label()`, `structured()` |
| the context | `Map<String, Serializable>` | defensively copied, immutable, no null keys, no null values |
| the message | derived | computed from the first two on every call; never stored |

The rule that makes the rest fall out: **there is exactly one copy of the facts.** The accessors
read the map, and `getMessage()` reads the same map. Nothing can disagree with anything.

```java
/** The shared payload of every domain failure. Held by composition because the hierarchy has
 *  two roots (Exception and RuntimeException) and Java has no shared superclass to put it in. */
public final class FailureDetail implements Serializable {

    private static final long serialVersionUID = 1L;

    private final ErrorCode errorCode;

    /** Declared type is not Serializable, so -Xlint:serial warns; the runtime value always is,
     *  because Map.copyOf returns a serializable immutable map. Mirrors what Throwable itself
     *  does with its suppressedExceptions field. */
    @SuppressWarnings("serial")
    private final Map<String, Serializable> context;

    public FailureDetail(ErrorCode errorCode, Map<String, ? extends Serializable> context) {
        this.errorCode = Objects.requireNonNull(errorCode, "errorCode");
        // Defensive copy AND immutability in one call. Map.copyOf rejects null keys and null
        // values, so the null policy is enforced here rather than documented and hoped for.
        this.context = Map.copyOf(Objects.requireNonNull(context, "context"));
    }

    public ErrorCode errorCode() {
        return errorCode;
    }

    public Map<String, Serializable> context() {
        return context;
    }

    public Serializable contextValue(String key) {
        return context.get(Objects.requireNonNull(key, "key"));
    }

    /** The message is derived, never stored, so code and context can never disagree.
     *  Keys are sorted so two occurrences of the same failure render identically. */
    public String renderMessage() {
        StringBuilder out = new StringBuilder(64);
        out.append(errorCode.code());
        if (!errorCode.label().equals(errorCode.code())) out.append(' ').append(errorCode.label());
        if (!context.isEmpty()) {
            out.append(" [");
            boolean first = true;
            for (Map.Entry<String, Serializable> e : new TreeMap<>(context).entrySet()) {
                if (!first) out.append(", ");
                out.append(e.getKey()).append('=').append(e.getValue());
                first = false;
            }
            out.append(']');
        }
        return out.toString();
    }
}
```

`Map.copyOf` does three jobs in one call: it copies (so the caller's map cannot reach in later),
it returns `ImmutableCollections.MapN` (so nothing can mutate it afterwards), and it throws
`NullPointerException` on a null key or value (so the null policy is enforced rather than
documented). [`../immutability-and-design/02-immutability.md`](../immutability-and-design/02-immutability.md)
owns defensive copying and safe publication in full.

### The message, derived rather than stored

`renderMessage()` is the only place a human-readable form exists, and it is called, not cached.
Two properties are worth naming. It sorts the keys through a `TreeMap`, so two occurrences of the
same failure render identically regardless of how the caller's map iterated — without that, a
`HashMap`-sourced context could render `[delta=GBP 0.01, entryId=LE-88213]` on one occurrence and
`[entryId=LE-88213, delta=GBP 0.01]` on the next, and log-based grouping would split one failure
into two. And it suppresses the label when it equals the code, which is why a bare-name fault
renders `INSUFFICIENT_FUNDS` once followed by its context, rather than repeating the name twice.

The two roots call `super(null, cause)` and declare `getMessage()` `final`, so the stored
`detailMessage` is permanently `null` and no subclass can reintroduce a second copy. Real output
from the structured form, showing the derived message beside the typed accessors that read the
same map:

```console
structured: INSUFFICIENT_FUNDS [clientId=3f2a1c88-0000-4000-8000-000000000001, requested=GBP 4.20, shortfall=GBP 2.45, stakeable=GBP 1.75]
  code             = INSUFFICIENT_FUNDS
  shortfall        = GBP 2.45
  offer instead    = GBP 1.75
  api body         = {"code":"INSUFFICIENT_FUNDS","shortfall":"2.45"}
```

`shortfall` appears in the message *and* in `e.shortfall()` because there is one map behind both.
Note it is a derived value — 4.20 minus 1.75 — computed in the constructor, which is the kind of
thing a formatted message reliably forgets to print.

### Context immutability: the bug, then the fix

```java
/** A base class that keeps the caller's map instead of copying it. */
static final class LeakyFailure extends RuntimeException {
    private static final long serialVersionUID = 1L;
    @SuppressWarnings("serial")
    private final Map<String, Serializable> context;
    LeakyFailure(Map<String, Serializable> context) { this.context = context; }
    @Override public String getMessage() { return "LEDGER_IMBALANCE " + context; }
}

static void mutableContextBug() {
    Map<String, Serializable> ctx = new HashMap<>();
    ctx.put("entryId", "LE-88213");
    ctx.put("delta", Money.gbp("0.01"));
    LeakyFailure leaked = new LeakyFailure(ctx);
    System.out.println("leaky at throw  : " + leaked.getMessage());
    ctx.put("delta", Money.gbp("0.00"));
    ctx.put("entryId", "LE-00000");
    System.out.println("leaky at log    : " + leaked.getMessage());

    LedgerImbalanceException copied =
            new LedgerImbalanceException("LE-88213", Money.gbp("4.20"), Money.gbp("4.19"));
    System.out.println("copied at throw : " + copied.getMessage());
    try {
        copied.context().put("delta", Money.gbp("0.00"));
    } catch (UnsupportedOperationException e) {
        System.out.println("copied mutation : " + e.getClass().getName() + " (as designed)");
    }
    System.out.println("copied at log   : " + copied.getMessage());
}
```

Real output:

```console
leaky at throw  : LEDGER_IMBALANCE {delta=GBP 0.01, entryId=LE-88213}
leaky at log    : LEDGER_IMBALANCE {delta=GBP 0.00, entryId=LE-00000}
copied at throw : LEDGER_IMBALANCE [credits=GBP 4.19, debits=GBP 4.20, delta=GBP 0.01, entryId=LE-88213]
copied mutation : java.lang.UnsupportedOperationException (as designed)
copied at log   : LEDGER_IMBALANCE [credits=GBP 4.19, debits=GBP 4.20, delta=GBP 0.01, entryId=LE-88213]
```

The leaky version reported a 0.01 ledger imbalance on entry `LE-88213` at the throw site, and a
balanced entry `LE-00000` by the time it reached the log. That is not a cosmetic bug: the record
of a money failure changed after the fact, and the incident review has nothing to work from.

### Null policy, enforced

```java
static void nullPolicy() {
    try {
        new LedgerImbalanceException(null, Money.gbp("4.20"), Money.gbp("4.19"));
    } catch (NullPointerException e) {
        System.out.println("null context value rejected: " + e.getClass().getName());
    }
    try {
        new RestrictedActionException(null, ClientId.of("3f2a1c88-0000-4000-8000-000000000001"),
                new RestrictionKey(RestrictionType.STAKE_BLOCKED, RestrictionSource.ADMIN));
    } catch (NullPointerException e) {
        System.out.println("null errorCode rejected    : " + e.getMessage());
    }
}
```

```console
null context value rejected: java.lang.NullPointerException
null errorCode rejected    : errorCode
```

A `null` context value is rejected by `Map.of` before `Map.copyOf` ever sees it; a `null`
`errorCode` by `Objects.requireNonNull`, which is why the second message is the field name.
`cause` is the one field where `null` is legal and meaningful: it means "no cause", which is what
`Throwable` itself uses `null` for.

> **A domain exception is a code plus an immutable typed context, with the message derived from
> both — so that a caller can branch, an API can contract, and an operator can search, from the
> same single copy of the facts.**

### Diff vs the real one — the context carrier

| Aspect | This build | The JDK / a mature framework |
|---|---|---|
| Edge cases | empty context renders as bare code; keys sorted for determinism; `structured()` may be `null` | `java.nio.file.FileSystemException` carries exactly three typed fields (`file`, `other`, `reason`) and builds its message by concatenation in `getMessage()` — derived, like this one, but fixed-arity rather than a map |
| Intrinsics | none | none; `Map.copyOf` is ordinary Java, though `ImmutableCollections` is heavily `@Stable`-annotated for the JIT |
| Serialization | `serialVersionUID = 1L`; `Serializable` bound on values; `@SuppressWarnings("serial")` on the `Map`-typed field | `Throwable` carries the same suppression on its own `List<Throwable> suppressedExceptions` (`Throwable.java:234-235`), for the same reason: the declared type is not `Serializable`, the runtime value always is |
| Null policy | `errorCode` and `context` non-null; values non-null via `Map.of`/`Map.copyOf`; `cause` nullable | `Throwable` permits a null message and a null cause and documents both; `FileSystemException` permits a null `other` and a null `reason` |
| Thread safety | deeply immutable after construction, so it publishes safely with no synchronisation | `Throwable` is *mutable* and its mutators (`fillInStackTrace`, `setStackTrace`, `addSuppressed`, `initCause`) are all `synchronized` precisely because it is not |
| Allocation tricks | one `FailureDetail` plus one `ImmutableCollections$MapN` plus `n` entries — measured at 25.02 ns for a four-entry context | `Map.of` has hand-written arity-specialised overloads up to ten pairs to avoid the varargs array; `UNASSIGNED_STACK` and `SUPPRESSED_SENTINEL` are shared singletons so an unfilled `Throwable` allocates neither array nor list |
| Why the JDK bothers | — | `Throwable` must be constructible when the heap is exhausted, which is why the sentinels exist; a `Map`-based context would be an allocation it cannot afford, which is why the JDK's own exceptions use fixed typed fields instead |

The 25.02 ns figure is measured in
[`03h-stackless-exception.md`](03h-stackless-exception.md), where it turns out to be the *entire*
cost of a stackless exception at depth 1. Structured context is not free; it is worth its price
for anything a caller branches on, and it is the reason a preallocated singleton — which carries
no context — is an order of magnitude cheaper still. The §4.6-wide diff table, leaf 4.6.9, lives in
[`03j-cleaner-and-diff.md`](03j-cleaner-and-diff.md).

---

## Pitfalls

### A mutable context map

**Wrong**

```java
LeakyFailure(Map<String, Serializable> context) { this.context = context; }
```

```console
leaky at throw  : LEDGER_IMBALANCE {delta=GBP 0.01, entryId=LE-88213}
leaky at log    : LEDGER_IMBALANCE {delta=GBP 0.00, entryId=LE-00000}
```

The caller reused its `HashMap` for the next ledger entry. The record of a 0.01 imbalance on
`LE-88213` became a clean bill of health on `LE-00000` somewhere between the `throw` and the log
appender.

**Right**

```java
this.context = Map.copyOf(Objects.requireNonNull(context, "context"));
```

```console
copied mutation : java.lang.UnsupportedOperationException (as designed)
copied at log   : LEDGER_IMBALANCE [credits=GBP 4.19, debits=GBP 4.20, delta=GBP 0.01, entryId=LE-88213]
```

One call copies, freezes, and rejects nulls.

**Why people believe it:** an exception feels like a short-lived object thrown and immediately
caught, so aliasing the caller's map looks free. Logging is asynchronous, incident capture is
asynchronous, and the exception can easily outlive the map's next mutation.

### Storing the rendered message instead of deriving it

**Wrong**

```java
protected QuizStakesRuntimeException(ErrorCode errorCode,
                                     Map<String, ? extends Serializable> context) {
    super(errorCode.code() + " " + errorCode.label() + " " + context);   // rendered once, stored
    this.detail = new FailureDetail(errorCode, context);
}
```

Now there are two copies of the facts. Six months later somebody adds `"shortfall"` to
`InsufficientFundsException`'s context map. Every accessor sees it; the message, built from the
`Map` at construction time, happens to as well — until somebody instead changes `renderMessage()`
to redact a client id, and the stored message keeps printing it. Nothing fails: the message is a
`String`, and every test asserting on it still passes because they were written against the stored
form.

**Right**

```java
@Override public final String getMessage() { return detail.renderMessage(); }
```

`super(null, cause)`, nothing stored, `final` so no subclass can reintroduce the second copy. The
message and the accessors read the same immutable map, so they cannot disagree.

**Why people believe it:** `Throwable`'s own constructor takes the message, so passing one looks
like the intended use — and computing a `String` on every `getMessage()` call sounds wasteful.
Both are true and neither matters: the constructor also accepts `null`, and `getMessage()` is
called once per failure, at log time, on a path that has already thrown.

### Assuming the `Serializable` bound on context values guarantees anything

**Wrong**

```java
List<Object> holder = new ArrayList<>();
holder.add(new OperatorHandle("OP-4417"));   // OperatorHandle does not implement Serializable
Serializable smuggled = (Serializable) holder;   // ArrayList does, so this compiles and passes the bound
Map<String, Serializable> ctx = Map.of("entryId", "LE-88213", "raisedBy", smuggled);
```

The bound is satisfied, the exception constructs, and the message renders perfectly:

```console
renders fine       = LEDGER_IMBALANCE [entryId=LE-88213, raisedBy=[operator:OP-4417]]
round trip         = NotSerializableException: qs.SerializationRoundTrip$OperatorHandle
```

The failure arrives at `writeObject` time — which in practice means when the exception crosses a
process boundary during an incident, at the worst possible moment.

**Right**

Keep the bound, because it catches the common case at compile time, and additionally keep the
context values to types you control and have tested through a round trip: the value records
(`Money`, `ClientId`, `RestrictionKey`), `String`, and boxed primitives. Where a value is a handle
to something outside the domain, put its identifier in the map rather than the handle:

```java
Map.of("entryId", "LE-88213", "raisedBy", "OP-4417")   // the badge, not the OperatorHandle
```

**Why people believe it:** a generic bound normally *is* a guarantee — `<T extends Comparable<T>>`
really does mean you can call `compareTo`. `Serializable` breaks the pattern because it is a marker
with no methods and no contract about a type's contents, so the bound proves only that the
top-level object opted in, not that anything it references did.

---

## Cheat sheet

| Thing | Value / rule |
|---|---|
| Context type | `Map<String, Serializable>`, constructor parameter `Map<String, ? extends Serializable>` |
| The one call that does it all | `Map.copyOf` — copies, freezes, rejects null keys and null values |
| Copy, why | without it the caller mutates the record of a failure after the throw |
| Immutable map class | `java.util.ImmutableCollections$MapN`; mutation throws `UnsupportedOperationException` |
| Message policy | derived in a `final getMessage()`; `super(null, cause)`; never stored |
| Determinism | keys sorted through a `TreeMap` in `renderMessage()`, so repeat occurrences group in a log |
| Label suppression | omitted when it equals the code, so bare-name faults do not render their name twice |
| Null policy | `errorCode` non-null via `Objects.requireNonNull`; context keys and values non-null via `Map.of`/`Map.copyOf`; `cause` nullable and meaningful |
| NPE message | the field name for `requireNonNull`, empty for `Map.of` — which is how you tell which check fired |
| `Serializable` bound | a marker check only; contents are not covered |
| `@SuppressWarnings("serial")` | on the `Map`-typed field, mirroring `Throwable`'s own on `suppressedExceptions` |
| Measured cost | 25.02 ns for a four-entry context — the whole cost of a stackless exception at depth 1 |
| Where leaf 4.6.1 continues | hierarchy in `03c`, boundary and serial form in `03n` |

## Self-test

**Q1.** Why is `getMessage()` declared `final` on both roots and derived from the code plus the
context, rather than formatted once and handed to `super(message, cause)`?

<details><summary>Answer</summary>

Because a stored message is a second copy of the facts, and two copies drift. If the message is
built in the constructor and the context is stored separately, any later change to how the context
is populated leaves the message stale, and nothing in the compiler or the test suite notices — the
message is a `String` and every assertion on it still passes. Deriving it means there is exactly
one copy: `renderMessage()` reads the same `errorCode` and the same immutable map the accessors
read. `final` closes the other hole: a subclass overriding `getMessage()` could reintroduce the
drift for its own branch of the hierarchy while every other branch stayed honest. The constructor
passes `null` as the stored `detailMessage` deliberately, which is legal — `Throwable` allows a
null message.

</details>

**Q2.** `Map.copyOf` replaced three separate defensive steps. Name them, and say what each one
prevents.

<details><summary>Answer</summary>

It copies, which stops the caller's map from reaching into the exception after the throw — the
measured bug where a 0.01 imbalance on `LE-88213` became a balanced `LE-00000` between the throw
site and the log. It returns an `ImmutableCollections$MapN`, so nothing that later gets a
reference to `context()` can mutate it either; the demo confirms an `UnsupportedOperationException`
on `put`. And it rejects null keys and null values with a `NullPointerException`, which turns the
null policy from a line of javadoc into an enforced invariant. Doing these by hand would be
`new HashMap<>(context)` then `Collections.unmodifiableMap` then a loop over the entries checking
for nulls — three steps, one of which people routinely skip, and `unmodifiableMap` returns a
*view* that still reflects later changes to the backing map, so the hand-rolled version is
subtly wrong in exactly the way the copy was meant to fix.

</details>

**Q3.** The leaky version printed a different message at the log than at the throw. Why is that
worse than a merely cosmetic bug?

<details><summary>Answer</summary>

Because the two lines are the record of a money failure, and they disagree:

```console
leaky at throw  : LEDGER_IMBALANCE {delta=GBP 0.01, entryId=LE-88213}
leaky at log    : LEDGER_IMBALANCE {delta=GBP 0.00, entryId=LE-00000}
```

`LEDGER_IMBALANCE` is the unchecked, unrecoverable one — debits did not equal credits, so money
was created or destroyed. The log says entry `LE-00000` was balanced. The incident review therefore
has no entry id to look up and no delta to reconcile, and the natural conclusion is that the alert
was spurious. The caller did nothing exotic: it reused a `HashMap` for the next ledger entry, which
is ordinary and correct behaviour for a caller that does not know an exception aliased it. The bug
is entirely in the exception's constructor.

</details>

**Q4.** Constructing `LedgerImbalanceException` with a null `entryId` gives an NPE with no message;
constructing `RestrictedActionException` with a null `errorCode` gives one whose message is
`errorCode`. Why the difference, and why is it useful?

<details><summary>Answer</summary>

Two different checks fired. The null `entryId` was a null *value* in the `Map.of` call inside
`LedgerImbalanceException`'s constructor, and `Map.of` throws a bare `NullPointerException` with no
message — it does not know which of its arguments you meant. The null `errorCode` hit
`Objects.requireNonNull(errorCode, "errorCode")` in `FailureDetail`, which puts the field name in
the message. That is useful precisely because it tells you which layer rejected the argument
without reading the stack trace: a message means the explicit guard fired, no message means
`Map.of` did, and the fix is different in each case. It is also why the guard is worth writing at
all when `Map.copyOf` would have thrown anyway — `Objects.requireNonNull` with a name is a
strictly better diagnostic than the collection's own check.

</details>

**Q5.** Why is the constructor parameter `Map<String, ? extends Serializable>` rather than
`Map<String, Serializable>`, when the field is the latter?

<details><summary>Answer</summary>

So a caller can pass a more specific map without copying it first. `Map<String, Money>` is not a
`Map<String, Serializable>` — generics are invariant, which is the whole point of
`02d-wildcard-copy-varargs-and-diff.md`'s subject — so with the narrower parameter type a caller
holding a `Map<String, Money>` would have to build a second map just to satisfy the signature. The
wildcard accepts it. The field can be `Map<String, Serializable>` because `Map.copyOf` returns a
genuinely new map whose value type is inferred from the bound, and because the field is only ever
read: nothing writes into it, so the invariance that makes `? extends` necessary on the way in is
irrelevant once the copy exists. This is the standard PECS reading — the parameter is a producer of
values, so `extends`.

</details>

## Open questions

- none

---

**Leaves covered:** 4.6.1, part 2 of 3 — the structured context, its defensive copy, the null policy, and the derived message (1 leaf, shared with `03c-exception-hierarchy-and-stackless.md` and `03n-exception-boundaries-and-serialization.md`)
**Leaves deferred:** none
**Diagrams included:** none
**Target version:** Java 21 LTS
**Lines:** 453
