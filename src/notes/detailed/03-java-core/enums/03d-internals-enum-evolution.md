# 03 Java Core — Enum evolution — INTERNALS (§3.10, 3.10.13–3.10.14)

**Target version: Java 21 LTS.** | **Part 3 of 5** | [Index](../00-index.md)
Previous: [`EnumSet` and `EnumMap` internals](03c-internals-enumset-enummap.md) · Next: [Records and sealed types](../records-and-sealed/01-basics.md)

The last two leaves of §3.10, and the two that cost real money. Everything before this file described an enum standing still. These two describe what happens when it changes — a constant added, a constant renamed, an ordinal already sitting in seven million rows — and both failure modes share the property that makes them expensive: **nothing throws.** The switch links, the row decodes, the value is valid, and the meaning is different.

Both are consequences of mechanisms established earlier. That adding a constant is binary-compatible is the `$SwitchMap` desugaring of [`03b-internals-guarantees-and-switch.md`](03b-internals-guarantees-and-switch.md) concept 3 doing exactly what it was designed to do. That the ordinal is unstable is the `<clinit>` of [`03-internals-enums.md`](03-internals-enums.md) concept 1 — `iconst_0`, `bipush 6` — writing declaration position in as a literal. This file is the operational half: what to do about both.

Everything below is measured on **Oracle JDK 21.0.7 (21.0.7+8-LTS-245, macOS aarch64)**, with **Oracle JDK 17.0.15** for the version comparison. The enum under test is the ten-constant `RestrictionType` from [`01-basics.md`](01-basics.md), with `SELF_EXCLUDED` at ordinal 7.

## 1. Adding a constant: source-compatible, behaviour-changing (3.10.13)

`[TRAP]` Adding an enum constant requires no downstream recompilation. That is a guarantee, and it is the problem: the code that does not have to change also does not have to *notice*.

### Why it exists

JLS §13 treats adding a member to an enum as both source-compatible and binary-compatible, and the `$SwitchMap` mechanism of [`03b-internals-guarantees-and-switch.md`](03b-internals-guarantees-and-switch.md) exists specifically to make it so at the bytecode level. That is the right design — the alternative is that every enum addition breaks every dependent artefact — but "compatible" is a statement about linking, not about behaviour. A `switch` with a `default` links fine and routes the new constant somewhere its author never considered.

### The mechanism

Four outcomes, all measured, depending on how the switch was written and whether it was recompiled.

| Switch shape | Recompiled? | Result on the new constant |
|---|---|---|
| Statement or expression **with** `default` | either | routes to `default`, silently. No error, no warning |
| Expression, exhaustive, **no** `default` | yes | **compile error**: "the switch expression does not cover all possible input values" |
| Expression, exhaustive, **no** `default` | no | `MatchException: null` at runtime (JDK 21); `IncompatibleClassChangeError: null` (JDK 17) |
| Statement, non-exhaustive, no `default` | either | falls through, doing nothing. No error |

The compile error is the whole value of the enum's closed set, and a `default` is the code opting out of it. Measured, on a switch expression covering all ten `RestrictionType` constants with no `default`, after appending `WAGERING_HELD` and recompiling: `error: the switch expression does not cover all possible input values`. And without recompiling, run against the new enum:

```
  SOURCE_OF_FUNDS_REQUIRED -> SOF
  COOLING_OFF              -> SELF_SERVICE
  DORMANT_FROZEN           -> DORMANT
  WAGERING_HELD            -> THREW java.lang.MatchException: null
```

The null message is structural, not an oversight: the bytecode constructs `new MatchException` with `aconst_null` twice, because at compile time the branch had been *proved* unreachable and there was nothing to say. [`03b-internals-guarantees-and-switch.md`](03b-internals-guarantees-and-switch.md) concept 3 has the listing.

The fourth row is worth naming because it is the most invisible: a switch *statement* that is not exhaustive and has no `default` simply does nothing for an unhandled value and falls out of the block. No error, no warning at default `javac` settings, no runtime signal. `-Xlint:all` does not flag it either, because a non-exhaustive switch statement is legal. If a switch statement is making a decision, converting it to an expression is the cheap way to get the exhaustiveness check retroactively — the conversion is usually mechanical and it is the single highest-value refactor available in an enum-heavy codebase.

### Diagram

No diagram for this concept: it is a four-row decision table and the table above is the correct rendering. The bytecode that produces the third and fourth rows is D-118, in [`03b-internals-guarantees-and-switch.md`](03b-internals-guarantees-and-switch.md).

### A concrete example

The two-part discipline: exhaustive switches in the core, tolerance only at the edges.

```java
public final class RestrictionRouting {

    /**
     * Exhaustive, no default. Adding a RestrictionType is a compile error here,
     * which is the point: a new restriction must be routed deliberately.
     */
    public static Queue route(RestrictionType type) {
        return switch (type) {
            case DEPOSIT_BLOCKED, DEPOSIT_LIMITED -> Queue.PAYMENTS;
            case STAKE_BLOCKED -> Queue.TRADING;
            case WITHDRAWAL_BLOCKED, WITHDRAWAL_HELD -> Queue.PAYMENTS;
            case SOURCE_OF_FUNDS_REQUIRED -> Queue.COMPLIANCE;
            case ALL_BLOCKED -> Queue.COMPLIANCE;
            case SELF_EXCLUDED, COOLING_OFF -> Queue.SELF_SERVICE;
            case DORMANT_FROZEN -> Queue.LIFECYCLE;
        };
    }

    /**
     * The only tolerant point. A code this build does not recognise fails here,
     * loudly, with the offending value in the message — not three layers deeper
     * with a queue name that looks plausible.
     */
    public static Queue routeFromWire(String code) {
        return RestrictionType.fromCode(code)
            .map(RestrictionRouting::route)
            .orElseThrow(() -> new IllegalArgumentException(
                "unroutable restriction code from wire: " + code
                    + " — a newer deployment may be producing a constant this build lacks"));
    }

    public enum Queue { PAYMENTS, TRADING, COMPLIANCE, SELF_SERVICE, LIFECYCLE }
}
```

The message on `routeFromWire` names the likely cause because that is precisely the rolling-upgrade scenario: a newer producer emitting a code an older consumer does not have. An operator reading that line at 03:00 needs the diagnosis, not just the symptom.

### The gotcha

**Pitfall:** a `default` branch that returns a plausible fallback. `default -> Queue.COMPLIANCE;` compiles, is defensible in review, and means the day someone adds `WAGERING_HELD` every wagering hold lands quietly in the compliance queue — staffed at 40 operators steady, 22 cases per operator per hour, with no procedure for a case type it has never seen. Symptom: no error anywhere; a queue's volume rising; and a discovery weeks later that a restriction type has never been actioned. Fix: omit the `default` so the compiler produces the list of places that must decide. Where you cannot — an enum owned by a library that may grow — write `default -> throw new IllegalStateException("unrouted restriction: " + type);`, which is a runtime failure rather than a compile-time one but is at least loud on the first request.

> **Definition.** Adding an enum constant is source- and binary-compatible under JLS §13, so a `switch` with a `default` routes it silently and a non-exhaustive statement ignores it, while a recompiled exhaustive switch expression is a compile error and a stale one throws `MatchException` (JDK 21) or `IncompatibleClassChangeError` (JDK 17) — which is why omitting `default` is the correct default wherever you own the enum.

---

## 2. Enums across a wire or a database (3.10.14)

`[TRAP]` Two rules, and the second is the one people skip. Persist a code the enum owns, never the ordinal — and handle an unrecognised value explicitly on read.

### Why it exists

The ordinal is a compile-time literal drawn from declaration order (see [`03-internals-enums.md`](03-internals-enums.md) concept 1: `iconst_0`, `bipush 6`, and so forth, baked into `<clinit>`), so it changes whenever the declaration changes. Measured: inserting one constant into `RestrictionType` changed the constant at index 7 from `SELF_EXCLUDED` to `SOURCE_OF_FUNDS_REQUIRED`. Stored ordinals therefore decode to a *different valid value* after an edit that looks purely additive — silently, with nothing to alert on. `name()` is better, being stable against reordering, but it is not stable against *renaming*, and serialization's by-name form offers no migration hook (see [`03b-internals-guarantees-and-switch.md`](03b-internals-guarantees-and-switch.md) concept 1). An explicit code field, owned by the enum and mapped by a table you control, is stable against both.

### The mechanism

The four options, ranked, with what each is stable against:

| Representation | Reordering | Renaming | Removing | Notes |
|---|---|---|---|---|
| `ordinal()` | **no** | yes | **no** | decodes to a different valid value. Never do this |
| `name()` | yes | **no** | **no** | `@Enumerated(EnumType.STRING)`; column must fit the longest identifier |
| Explicit code field | yes | yes | **no** | the production choice. A rename is free; a removal still needs a decision |
| Code + a mapping table | yes | yes | yes | the table absorbs a removal by pointing the old code somewhere |

Nothing is stable against *removing* a constant without a decision, because a stored value then names something that does not exist — the only question is whether that decision is yours (a mapping table entry, or an explicit throw) or the platform's (`ArrayIndexOutOfBoundsException` from `values()[i]`, or `IllegalArgumentException` from `valueOf`).

The read side is the half that gets skipped. `values()[storedOrdinal]` throws `ArrayIndexOutOfBoundsException` with a message containing only an integer. `valueOf(storedName)` throws `IllegalArgumentException: No enum constant <class>.<name>`, which is at least diagnosable. Neither tells the operator *why*, and during a rolling upgrade the why is almost always "a newer instance wrote a value this build does not have".

### Diagram

No diagram for this concept: it is a four-row comparison and the table above is the rendering.

### A concrete example

The full boundary, all three edges — database, JSON, and the enum's own table:

```java
public enum RestrictionType {
    DEPOSIT_BLOCKED("DEP_BLK"),
    STAKE_BLOCKED("STK_BLK"),
    WITHDRAWAL_BLOCKED("WDR_BLK"),
    DEPOSIT_LIMITED("DEP_LIM"),
    WITHDRAWAL_HELD("WDR_HLD"),
    SOURCE_OF_FUNDS_REQUIRED("SOF_REQ"),
    ALL_BLOCKED("ALL_BLK"),
    SELF_EXCLUDED("SELF_EXC"),
    COOLING_OFF("COOL_OFF"),
    DORMANT_FROZEN("DORM_FRZ");

    private static final Map<String, RestrictionType> BY_CODE;

    static {
        Map<String, RestrictionType> byCode = new HashMap<>();
        for (RestrictionType type : values()) {
            RestrictionType clash = byCode.put(type.code, type);
            if (clash != null) {
                throw new IllegalStateException("duplicate restriction code " + type.code
                    + " on " + clash.name() + " and " + type.name());
            }
        }
        BY_CODE = Map.copyOf(byCode);
    }

    private final String code;

    RestrictionType(String code) {
        this.code = code;
    }

    public String code() {
        return code;
    }

    public static Optional<RestrictionType> fromCode(String code) {
        return code == null ? Optional.empty() : Optional.ofNullable(BY_CODE.get(code));
    }
}
```

The database edge, with the converter applied automatically so no field can opt out:

```java
@Converter(autoApply = true)
public final class RestrictionTypeConverter
        implements AttributeConverter<RestrictionType, String> {

    @Override
    public String convertToDatabaseColumn(RestrictionType attribute) {
        return attribute == null ? null : attribute.code();
    }

    @Override
    public RestrictionType convertToEntityAttribute(String column) {
        if (column == null) {
            return null;
        }
        return RestrictionType.fromCode(column).orElseThrow(() -> new IllegalStateException(
            "restriction row holds an unknown code: " + column
                + " — a newer deployment wrote a constant this build does not have"));
    }
}
```

And the JSON edge, where the DTO carries codes rather than the enum:

```java
public record RestrictionView(String type, String source, Instant appliedAt) {

    public static RestrictionView of(Restriction restriction) {
        return new RestrictionView(
            restriction.type().code(),
            restriction.source().name(),
            restriction.appliedAt());
    }
}
```

`autoApply = true` is the load-bearing detail on the converter: without it, every entity field needs `@Convert`, and the one field somebody forgets falls back to `@Enumerated`'s default — which is `EnumType.ORDINAL`, so the omission silently reintroduces the original bug. With it, there is no way to get the ordinal by accident.

At QuizStakes scale the read-side message matters more than it looks. Ledger entries run at **~19.8M/day** and the hot window is **90 days**, so roughly 1.78 billion rows are readable at any time; a restriction code that decodes wrongly is not a bug you find by inspection. The `orElseThrow` naming both the code and the likely cause is what turns a silent mis-decode into a bounded incident.

### The gotcha

**Pitfall:** believing the rule is about databases. Every boundary is the same boundary. A `Map<Integer, X>` keyed on `ordinal()` in Redis; a protobuf or Avro field populated from `ordinal()`; a Kafka message with a numeric `restrictionType`; an `int[]` counters array whose index becomes a metric tag; a bitmask persisted as `1 << ordinal()`; a URL query parameter; a file format. In JPA specifically, a bare `@Enumerated` *is* the ordinal, because `EnumType.ORDINAL` is the annotation's declared default. Symptom, in all cases: values that decode correctly until the enum is edited, then decode to a different valid value — the worst available failure mode, because there is nothing to alert on. Fix: the only ordinal uses that are safe begin and end inside one JVM run — `EnumSet`, `EnumMap`, a `$SwitchMap` — because those are rebuilt from the current constant list at every class initialization.

> **Definition.** Persist an explicit code the enum owns, mapped through a `static final` table built from `values()`; `name()` is acceptable but breaks on rename, and `ordinal()` breaks on any edit to the declaration list — and on read, an unrecognised value must be an explicit decision with the offending value in the message, because a rolling upgrade will produce one.

---
---

## Pitfalls

### Reading a stored ordinal back through `values()`

**Wrong**

```java
public RestrictionType type() {
    return RestrictionType.values()[restrictionTypeColumn];
}
```

Two defects stacked. The index means whatever declaration order meant when the row was written — measured, inserting one constant moved index 7 from `SELF_EXCLUDED` to `SOURCE_OF_FUNDS_REQUIRED`, and the read succeeded with the wrong value. And for any stored value the *current* constant list does not cover, `values()[i]` throws `ArrayIndexOutOfBoundsException` with a message containing only an integer — which is exactly what happens when an older instance reads a newer instance's row during a rolling upgrade. Plus a 56-byte clone per call.

**Right**

```java
public RestrictionType type() {
    return RestrictionType.fromCode(restrictionTypeColumn)
        .orElseThrow(() -> new IllegalStateException(
            "restriction row " + id + " holds an unknown code: " + restrictionTypeColumn
                + " — a newer deployment wrote a constant this build does not have"));
}
```

The column holds a code the enum owns, so reordering cannot change its meaning; an unrecognised value fails with the row id, the offending code, and the diagnosis; and there is no `values()` clone, because `fromCode` is a lookup in a `static final` map built once at class initialization.

**Why people believe it:** `values()[ordinal]` is the obvious inverse of `ordinal()`, an `int` column indexes faster than a `varchar`, and the round trip is provably correct — for exactly as long as nobody edits the declaration list. The failure arrives a year later, from a change that reads as additive.

---

### Deploying a new enum constant to producers and consumers together

**Wrong**

A single rolling release that both adds `WAGERING_HELD` to `RestrictionType` and starts producing it. During the roll, half the fleet has the constant and half does not.

```java
// New build: produces the code.
restrictionService.apply(RestrictionType.WAGERING_HELD, RestrictionSource.SYSTEM_COMPLIANCE);
```

Three separate failure surfaces open at once. A consumer on the old build reading the row through a `String`-code converter throws `IllegalStateException: restriction row holds an unknown code: WAG_HLD`. A consumer reading a Java-serialized form throws `IllegalArgumentException: No enum constant RestrictionType.WAGERING_HELD` from inside `ObjectInputStream`. And a consumer with a stale exhaustive switch expression throws `MatchException: null` — measured on JDK 21.0.7; `IncompatibleClassChangeError: null` on 17. All three land on the nodes you did **not** change, which inverts the usual expectation about where a compatibility break shows up.

**Right**

Two deployments, in this order.

```java
// Deployment 1: every instance knows the constant. Nothing produces it.
public enum RestrictionType {
    DEPOSIT_BLOCKED("DEP_BLK"),
    STAKE_BLOCKED("STK_BLK"),
    WITHDRAWAL_BLOCKED("WDR_BLK"),
    DEPOSIT_LIMITED("DEP_LIM"),
    WITHDRAWAL_HELD("WDR_HLD"),
    SOURCE_OF_FUNDS_REQUIRED("SOF_REQ"),
    ALL_BLOCKED("ALL_BLK"),
    SELF_EXCLUDED("SELF_EXC"),
    COOLING_OFF("COOL_OFF"),
    DORMANT_FROZEN("DORM_FRZ"),
    WAGERING_HELD("WAG_HLD");     // known everywhere, produced nowhere
}
```

Once that build is on every instance — and every exhaustive switch has been recompiled against it, which the compiler forced — deployment 2 enables production of it. The gap between the two deployments must exceed the longest retention of anything holding the value: a Kafka topic's retention, a session store's TTL, a batch file's processing window. For the QuizStakes bank-withdrawal path that is at least the **4 payout windows a day** the banking partner runs.

**Why people believe it:** adding an enum constant is source- and binary-compatible under JLS §13, needs no downstream recompilation, and — for a `switch` with a `default` or for the `$SwitchMap` — genuinely is safe without coordination. The exceptions are serialization on the read side and the exhaustive switch, and both fail on the *old* code, so the usual "the new code is the risky code" heuristic points the wrong way.


### A `default` that returns a plausible fallback

**Wrong**

```java
public Queue route(RestrictionType type) {
    return switch (type) {
        case STAKE_BLOCKED -> Queue.TRADING;
        case SELF_EXCLUDED, COOLING_OFF -> Queue.SELF_SERVICE;
        case SOURCE_OF_FUNDS_REQUIRED, ALL_BLOCKED -> Queue.COMPLIANCE;
        default -> Queue.COMPLIANCE;        // "compliance can triage anything"
    };
}
```

Compiles, reviews well, and is green forever. Add `WAGERING_HELD` and every wagering hold silently joins the compliance queue — **40 operators steady, 90 at peak, 22 cases per operator per hour** — a queue with no procedure for a case type it has never seen. Nothing throws, nothing logs, and the discovery is weeks later when someone notices a restriction type has never been actioned.

**Right**

```java
public Queue route(RestrictionType type) {
    return switch (type) {
        case DEPOSIT_BLOCKED, DEPOSIT_LIMITED -> Queue.PAYMENTS;
        case STAKE_BLOCKED -> Queue.TRADING;
        case WITHDRAWAL_BLOCKED, WITHDRAWAL_HELD -> Queue.PAYMENTS;
        case SOURCE_OF_FUNDS_REQUIRED -> Queue.COMPLIANCE;
        case ALL_BLOCKED -> Queue.COMPLIANCE;
        case SELF_EXCLUDED, COOLING_OFF -> Queue.SELF_SERVICE;
        case DORMANT_FROZEN -> Queue.LIFECYCLE;
    };
}
```

Every constant listed, no `default`, so the expression is exhaustive and adding a constant produces `error: the switch expression does not cover all possible input values` at this line — a mechanical list of every place that must decide about the new value. Where the enum belongs to a library that may grow and a `default` is unavoidable, make it loud: `default -> throw new IllegalStateException("unrouted restriction: " + type);`.

**Why people believe it:** defensive programming is a good instinct, and a `default` looks like defence. Here it is the opposite: the enum's closed set is a compiler-checkable *guarantee*, and a `default` is the code asking the compiler to stop checking it.

---

## Cheat sheet

| Thing | Fact (Java 21 LTS) |
|---|---|
| Adding a constant | source- **and** binary-compatible under JLS §13. No downstream recompilation required |
| Why it is binary-compatible | the `$SwitchMap` array is sized from `values().length` at runtime; new constants get slot 0 = default |
| Adding a constant, `default` present | routes to `default`, silently. No error, no warning, no lint |
| Adding a constant, exhaustive + recompiled | **compile error**: "the switch expression does not cover all possible input values" |
| Adding a constant, exhaustive + stale | `MatchException: null` (JDK 21) / `IncompatibleClassChangeError: null` (JDK 17) |
| Why the message is null | the bytecode builds the exception with `aconst_null` twice — the branch had been *proved* unreachable |
| Non-exhaustive **statement**, no `default` | falls out of the block doing nothing. No error, no runtime signal, and `-Xlint:all` does not flag it |
| Highest-value refactor | convert a decision-making switch statement to an expression, to get exhaustiveness retroactively |
| Where to put tolerance | at the parse boundary, with the offending value still in scope. Keep the core switch exhaustive |
| A `default` that returns a fallback | converts a build failure into an unnoticed production behaviour. Throw instead, or omit it |
| Serialization on the read side | an older consumer meeting a newer constant's name gets `IllegalArgumentException: No enum constant` |
| Rolling-upgrade rule | deployment 1 ships the constant everywhere and produces nothing; deployment 2 enables production |
| Gap between the two deployments | must exceed the longest retention of anything holding the value |
| Which nodes fail | the **old** ones. Adding a constant breaks readers, not writers |
| Persist `ordinal()` | never. Measured: one insertion moved index 7 from `SELF_EXCLUDED` to `SOURCE_OF_FUNDS_REQUIRED` |
| Why the ordinal moves | it is an integer literal (`iconst_N` / `bipush N`) written into `<clinit>` from declaration position |
| Persist `name()` | survives reordering, **not** renaming. `@Enumerated(EnumType.STRING)` |
| `name()` column width | size it to the longest identifier — `SOURCE_OF_FUNDS_REQUIRED` is 24 characters |
| Persist an explicit code | survives reordering **and** renaming. The production choice |
| Code plus a mapping table | additionally survives removal, because an old code can be redirected in one line |
| Nothing survives removal | without a decision. The only question is whether it is yours or `values()[i]`'s |
| `values()[storedOrdinal]` | `ArrayIndexOutOfBoundsException` with a message containing only an integer. Plus a 56-byte clone per call |
| `valueOf(storedName)` | `IllegalArgumentException: No enum constant <class>.<name>` — at least diagnosable |
| JPA | `@Converter(autoApply = true)` on an `AttributeConverter<E, String>`. Never a bare `@Enumerated` |
| Why a bare `@Enumerated` is the bug | `EnumType.ORDINAL` is the annotation's own declared default |
| Read-side rule | throw with the offending value **and** the likely cause: "a newer deployment wrote a constant this build lacks" |
| Every boundary is the same boundary | Redis keys, protobuf/Avro fields, Kafka payloads, metric tags, `1 << ordinal()` bitmasks, URL parameters, file formats |
| Safe ordinal uses | those that begin and end inside one JVM run: `EnumSet`, `EnumMap`, `$SwitchMap`. All rebuilt at class init |

---

## Self-test

**Q1.** You add a constant to an enum and deploy without rebuilding a dependent artefact. Enumerate what happens.

<details><summary>Answer</summary>

Four outcomes, by switch shape. A switch **with a `default`** — statement or expression — routes the new constant to `default`, silently, with no error and no warning; the `$SwitchMap` array is sized from the *current* `values().length` and the new constant's slot is 0, which is the default branch. An **exhaustive expression with no `default`**, if recompiled, is a **compile error**: "the switch expression does not cover all possible input values" — which is the entire benefit of the enum's closed set. The same expression **not** recompiled throws at runtime: measured `java.lang.MatchException: null` on JDK 21.0.7 and `java.lang.IncompatibleClassChangeError: null` on JDK 17.0.15, both message-free because the bytecode constructs the exception with `aconst_null` twice — at compile time the branch had been proved unreachable, so there was nothing to say. And a **non-exhaustive switch statement with no `default`** simply falls out of the block doing nothing, with no error, no runtime signal, and no lint warning, because a non-exhaustive switch statement is legal. That fourth case is the most invisible and the argument for the highest-value refactor available in an enum-heavy codebase: converting a decision-making switch statement to an expression, which is usually mechanical and buys the exhaustiveness check retroactively. Nothing else breaks: adding a constant is source- and binary-compatible under JLS §13, and `$SwitchMap` makes it so at the bytecode level.

</details>

**Q2.** Give the four ways to represent an enum outside the process, ranked, with what each survives.

<details><summary>Answer</summary>

`ordinal()` survives nothing useful: it breaks on reordering *and* on insertion — measured, inserting one constant into `RestrictionType` changed the constant at index 7 from `SELF_EXCLUDED` to `SOURCE_OF_FUNDS_REQUIRED`, and the read threw nothing, returning a different valid value. It breaks on removal too, either silently or with `ArrayIndexOutOfBoundsException` carrying only an integer. Never. `name()` survives reordering — it is what `@Enumerated(EnumType.STRING)` and Java serialization both use — but not renaming, and serialization offers no `readResolve` hook to migrate a rename, so the only remedy there is a retained deprecated alias. It also needs the column sized to the longest identifier: `SOURCE_OF_FUNDS_REQUIRED` is 24 characters. An **explicit code field** owned by the enum survives both reordering and renaming, since the code is a value the enum declares rather than a derivative of its declaration — this is the production choice. A **code plus a mapping table** additionally survives removal, because an old code can be pointed at a replacement constant in one line of a map you control. Nothing survives removal without a *decision*; the only question is whether it is yours or the platform's. And whichever you choose, the read side needs an explicit unrecognised-value branch that names the offending value and the likely cause, because a rolling upgrade — an older instance reading what a newer instance wrote — will produce one.

</details>

---


**Q3.** During a rolling upgrade that adds an enum constant, which instances fail and why is that counter-intuitive?

<details><summary>Answer</summary>

The **old** ones — the instances you did not change. Adding a constant is source- and binary-compatible under JLS §13, so the new build links and runs fine and nothing forces a downstream rebuild. But three read paths on the old build meet a value it has never heard of. A `String`-code converter fails its `orElseThrow`. Java serialization fails inside `ObjectInputStream`, because the enum wire form is `name()` resolved through `Enum.valueOf`, giving `IllegalArgumentException: No enum constant <class>.<name>` — see [`03b-internals-guarantees-and-switch.md`](03b-internals-guarantees-and-switch.md) concept 1. And a stale exhaustive switch expression throws `MatchException: null` on JDK 21.0.7 or `IncompatibleClassChangeError: null` on 17.0.15, both measured. It is counter-intuitive because the usual heuristic is "the new code is the risky code, so watch the canary" — here the canary is healthy and the untouched majority is failing, so the alert fires on hosts nobody is looking at and the natural rollback instinct (revert the new build) *fixes* it, which reinforces a wrong diagnosis. The remedy is a two-phase deployment: ship the constant everywhere while producing nothing, wait out the longest retention of anything holding the value, then enable production. Or remove the platform from the decision with an explicit codec, so an unrecognised value is a branch your code chose rather than an exception thrown from library internals.

</details>

**Q4.** A team has a code-review rule against reordering enum constants and considers persisted ordinals safe. Respond.

<details><summary>Answer</summary>

The rule guards the wrong action. Reordering is only one way the index moves; **inserting** a constant anywhere except the end moves every ordinal after it, and inserting is a routine, obviously-additive change — nobody reviewing "add `WAGERING_HELD` to the restriction list" thinks of it as a data migration. Deleting is worse: it shifts everything after *and* leaves stored rows pointing at a valid-but-different constant. Measured: inserting one constant into `RestrictionType` changed the constant at index 7 from `SELF_EXCLUDED` to `SOURCE_OF_FUNDS_REQUIRED`, and the read path threw nothing and returned the wrong value. The mechanism is visible in the bytecode — the `<clinit>` writes each ordinal as an integer *literal* (`iconst_0` through `iconst_5`, then `bipush`) taken from declaration position, so recompiling with a different declaration writes different literals. For `SELF_EXCLUDED`, which carries `reversibleByOperator = false` and is the population a regulator asks about by name, a silent mis-decode is a compliance incident rather than a bug: those clients would be recorded as needing a source-of-funds document, which an operator can clear. And at **~19.8M ledger entries a day** with a **90-day hot window**, this is not something found by inspection. The correct guard is structural, not procedural: persist a code the enum owns, so no edit to the declaration list can change what a stored value means, and make an unrecognised code throw with the offending value and the likely cause in the message so a rolling upgrade fails loudly rather than quietly.

</details>

**Q5.** Which ordinal uses are safe, and what is the property that makes them so?

<details><summary>Answer</summary>

Exactly those that begin and end inside one JVM run, because they are rebuilt from the *current* constant list at every class initialization. Three of them, all in the platform. `EnumSet` computes `1L << ordinal` against a universe obtained from `Class.getEnumConstantsShared()`, so a set constructed in this run reflects this run's ordinals. `EnumMap` sizes `vals` from `keyUniverse.length` and indexes by `ordinal()`, same argument. And `$SwitchMap` — the most explicit case — builds its array in a synthetic holder class's `<clinit>` from `values().length`, populating it with `map[E.CONSTANT.ordinal()] = denseIndex` where the ordinal is *read from the constant at runtime*, which is precisely why a switch survives reordering without recompilation. The property they share: **the ordinal is consumed in the same process that produced it, and the producer is the class file currently on the classpath.** Everything unsafe violates that: a database column, a Redis key, a protobuf or Avro field, a Kafka payload, an `int[]` counter index that becomes a metric tag, a persisted `1 << ordinal()` bitmask, a URL parameter, a file format. A useful test to apply: if the number can be read by a process that did not also load the enum class that wrote it, the number is unsafe. That test also correctly classifies the awkward middle case — a local `int[]` cache indexed by ordinal is fine; the same array serialised to a cache server is not.

</details>

---

## Open questions

- **Unverified:** whether the change from `IncompatibleClassChangeError` (JDK 17.0.15) to `MatchException` (JDK 21.0.7) for a stale exhaustive switch expression is a specified behaviour change or a `javac` code-generation change. Both were measured on the identical experiment with identical source. The JDK 21 bytecode visibly constructs `MatchException` with two `aconst_null`s in the unreachable default branch, so the choice is made by the *compiler*, which implies the 17 build emitted `IncompatibleClassChangeError` there instead — but the JDK 17-compiled bytecode for that branch was not dumped to confirm. What would settle it: `javap -c` on the JDK 17-compiled exhaustive switch, plus the `java.lang.MatchException` javadoc, which states when the runtime throws it. Nothing here depends on the answer; both throwables are reported as measured.
- **Unverified:** whether `@Enumerated`'s `EnumType.ORDINAL` default is mandated by the Jakarta Persistence specification or is only the annotation's declared default value. The annotation's `value()` element has `ORDINAL` as its Java default, which is why a bare `@Enumerated` behaves that way regardless of provider — that much follows from the annotation declaration. Whether the specification additionally mandates a mapping for an enum-typed field carrying *no* `@Enumerated` was not checked, and providers have historically differed on untagged fields. What would settle it: the Jakarta Persistence 3.1 specification's basic-mappings section and the `jakarta.persistence.Enumerated` javadoc. The recommendation here — an explicit `@Converter(autoApply = true)` — is correct either way, because it removes the question.
- **Unverified:** the claim that a non-exhaustive switch *statement* with no `default` produces no warning under `-Xlint:all`. It is legal Java and no lint category obviously covers it, but no compilation with `-Xlint:all` was run against such a switch to confirm silence. What would settle it: `javac -Xlint:all` on a switch statement over `RestrictionType` handling three of ten constants with no `default`. The stronger and load-bearing claim — that it is legal, links fine, and does nothing for an unhandled value — follows from the language rules and from the measured `$SwitchMap` bytecode, where an unmapped ordinal reaches the `tableswitch` default and the default target for a statement is simply the instruction after the block.

---

**Leaves covered:** 3.10.13, 3.10.14 (2 leaves)
**Leaves deferred:** none
**Diagrams included:** none — §3.10's diagrams are D-117 in [`03-internals-enums.md`](03-internals-enums.md), D-118 in [`03b-internals-guarantees-and-switch.md`](03b-internals-guarantees-and-switch.md), and D-119 in [`03c-internals-enumset-enummap.md`](03c-internals-enumset-enummap.md)
**Target version:** Java 21 LTS
**Lines:** 426
