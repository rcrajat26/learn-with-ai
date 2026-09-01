# 03 Java Core — switch expressions and pattern matching — BASICS (§1.8, 1.8.11, 1.8.12)

**Target version: Java 21 LTS.** | **Part 1 of 5** | [Index](../00-index.md)
Previous: [switch on a String, on an enum, and on null](01b-string-and-enum-switch.md) · Next: [Assertions and guarded blocks](01d-assertions-and-synchronized.md)

Java 14 and Java 21 between them turned `switch` from a jump table into an
expression that the compiler checks for coverage. The arrow form kills fall-through.
The expression form produces a value and is therefore obliged to be exhaustive. And
the Java 21 pattern switch replaces the constant label with a *shape*, destructures
records, and reports its own failure modes as `MatchException`. This part covers all
three, against behaviour captured from a real JDK 21.

The classic colon form and fall-through are in
[The classic switch statement and fall-through](01a-switch.md); the compiled forms of
`String` and enum selectors, and `null` selectors, are in
[switch on a String, on an enum, and on null](01b-string-and-enum-switch.md).

---

## 11. Arrow form, `switch` expressions, `yield`, exhaustiveness (1.8.11)

**Concept.** Java 14 split one keyword into two shapes. The arrow form kills
fall-through: an arm is a single statement, block, or expression, and control leaves
the switch when it finishes. The expression form goes further — the whole `switch`
*produces a value*, so it can be assigned, returned, or passed as an argument, and
because it must produce a value it must be exhaustive.

**Why it exists.** The colon form has three defects that no amount of discipline
fixes: fall-through by default (§7), a shared scope across all arms (declare
`Money fee` in one case and it is in scope, uninitialised, in the next), and the
`temporary-variable-then-assign-in-every-branch` pattern which forces a non-final
local for what is conceptually one value. Arrow form fixes the first two, expression
form fixes the third.

**How it works.** Three shapes, and which one you get depends on syntax alone:

| Shape | Falls through? | Arm scope | Produces a value | Exhaustiveness required |
|---|---|---|---|---|
| statement, colon (`case X:`) | yes | one scope for the whole block | no | no |
| statement, arrow (`case X ->`) | no | per-arm | no | no |
| expression, arrow (`var v = switch (s) { }`) | no | per-arm | yes | **yes** |
| expression, colon with `yield` | no (each arm must yield or throw) | one scope | yes | **yes** |

An arrow arm that is a *block* needs `yield` to produce the value; an arrow arm that
is a single expression produces it implicitly. `yield` is a restricted identifier,
not a keyword — a variable named `yield` still compiles, which is how the feature was
added without breaking source compatibility.

Exhaustiveness is checked by the compiler, and it is the whole reason to prefer the
expression form. Over an `enum`, covering every constant satisfies it *without* a
`default`; over a sealed interface, covering every permitted subtype does. Observed
on JDK 21, a switch expression over `sealed interface Rail permits Card, Bank` that
handles only `Card`:

```
Ex.java:4: error: the switch expression does not cover all possible input values
```

**Tradeoff:** omitting `default` on an exhaustive enum switch buys you a compile
error the day somebody adds a constant — exactly the signal you want when
`RestrictionType` grows an eleventh member. It costs you runtime robustness against
a *separately compiled* enum that grew a constant you never saw: `javac` inserts a
synthetic default that throws (an `IncompatibleClassChangeError` on older releases,
`MatchException` on 21). The escape hatch when you deploy the enum and the switch
independently is to write `default ->` and handle the unknown explicitly; the cost is
losing the compile-time nudge.

```java
record Money2(java.math.BigDecimal amount, java.util.Currency currency) {}

final class RestrictionPolicy {

    /** Expression form, exhaustive over the enum, no default: adding a constant breaks the build. */
    static boolean blocksStaking(RestrictionType type) {
        return switch (type) {
            case STAKE_BLOCKED, ALL_BLOCKED, SELF_EXCLUDED, COOLING_OFF, DORMANT_FROZEN -> true;
            case DEPOSIT_BLOCKED, WITHDRAWAL_BLOCKED, DEPOSIT_LIMITED,
                 WITHDRAWAL_HELD, SOURCE_OF_FUNDS_REQUIRED -> false;
        };
    }

    /** Block arms need `yield`. Multi-statement work plus one produced value. */
    static int reviewPriority(String statusCode) {
        return switch (statusCode) {
            case "AA-550" -> 1;
            case "AA-650" -> {
                int base = 2;
                int documentPenalty = 1;
                yield base + documentPenalty;
            }
            case "AA-700" -> 3;
            default -> {
                yield 9;
            }
        };
    }

    public static void main(String[] args) {
        System.out.println(blocksStaking(RestrictionType.SELF_EXCLUDED));   // true
        System.out.println(blocksStaking(RestrictionType.DEPOSIT_LIMITED)); // false
        System.out.println(reviewPriority("AA-650"));                       // 3
        System.out.println(reviewPriority("DEP-301"));                      // 9
    }
}
```

**Pitfall:** mixing colon and arrow arms in one switch. It is a compile error
("different case kinds used in the switch"), and the error text sends people looking
for a syntax typo. Fix: convert the whole switch; there is no incremental migration
within a single block.

**Insight:** an arrow-form *statement* switch is still not exhaustive-checked. Only
the *expression* form forces coverage. Reaching for `return switch (x) { }` instead
of `switch (x) { }` plus assignments is what buys the guarantee — the arrow is not
enough on its own.

Deeper treatment of switch expressions, `yield` scoping, and the exhaustiveness
algorithm is in **04 Modern Java**.

> Arrow-form arms cannot fall through and each has its own scope; a `switch`
> *expression* additionally produces a value and is therefore required to be
> exhaustive (Java 14+, JLS 21 §14.11 and §15.28).

---

## 12. Pattern matching for `switch`, record patterns, `MatchException` (1.8.12)

**Concept.** The case label stops being a constant and becomes a *shape*. A pattern
switch asks "what is this, and what is inside it", binds the answer to a name, and —
over a sealed hierarchy — proves at compile time that you asked about every
possibility. The chain of `if (v instanceof DocumentVerdict d)` tests collapses into
one total expression.

**Why it exists.** Java 16 gave `instanceof` a binding form
(`if (v instanceof DocumentVerdict d)`), which removed the cast but not the chain.
The chain has no exhaustiveness check, its order is load-bearing and invisible, and
it degenerates into a visitor when you add a fourth subtype. Java 21 (JEP 441) moved
the same test into `switch`, where the compiler already knew how to check coverage.
The binding `instanceof` form itself, including its flow scoping rules, is in
[The conditional operator and pattern `instanceof`](../primitives-and-conversions/02c-conditional-operator.md).

**How it works.** A `case` label may now be a *type pattern* (`case DocumentVerdict d`),
a *record pattern* that destructures components positionally
(`case DocumentVerdict(Outcome o, String reason, Instant at, String by)`, nestable),
`case null`, or any of these with a `when` guard. Dominance is checked: a pattern that
can never match because an earlier one subsumes it is a compile error, so the ordering
bug the `instanceof` chain permits is gone.

`MatchException` is the new failure mode, and it exists for two situations. First,
the synthetic default of an exhaustive switch whose sealed hierarchy grew a subtype
after compilation. Second — the subtle one — a record pattern's accessor throwing:
destructuring calls the accessor, and if a user-written accessor throws, the pattern
match neither succeeds nor fails, so Java 21 wraps the thrown exception in a
`MatchException` rather than letting it escape as itself. Observed on JDK 21 with a
`DocumentVerdict` whose `outcome()` throws `IllegalStateException`:

```
java.lang.MatchException / cause=java.lang.IllegalStateException: boom
```

The original exception is preserved as the cause.

```java
import java.time.Instant;

record Outcome(String statusCode, String label) {}

sealed interface Verdict
        permits DocumentVerdict, ScreeningVerdict, ReviewVerdict, WealthVerdict {
    Outcome outcome();
    String reason();
    Instant decidedAt();
    String decidedBy();
}
record DocumentVerdict(Outcome outcome, String reason, Instant decidedAt, String decidedBy) implements Verdict {}
record ScreeningVerdict(Outcome outcome, String reason, Instant decidedAt, String decidedBy) implements Verdict {}
record ReviewVerdict(Outcome outcome, String reason, Instant decidedAt, String decidedBy) implements Verdict {}
record WealthVerdict(Outcome outcome, String reason, Instant decidedAt, String decidedBy) implements Verdict {}

final class AccountActivation {

    /** Exhaustive over the sealed hierarchy: no default, and adding a permitted subtype breaks the build. */
    static String nextStatus(Verdict v) {
        return switch (v) {
            case null -> "AA-700 REVIEW_QUEUED";
            case DocumentVerdict(Outcome(String code, String ignored), String reason, Instant at, String by)
                    when code.equals("AA-690") -> "AA-900 DECLINED (" + reason + " by " + by + " at " + at + ")";
            case DocumentVerdict(Outcome(String code, String ignored), String r, Instant at, String by) ->
                    switch (code) {
                        case "AA-611" -> "AA-700 REVIEW_QUEUED";
                        case "AA-650" -> "AA-700 REVIEW_QUEUED";
                        default -> "AA-600 DOCUMENTS_REQUESTED";
                    };
            case ScreeningVerdict s when s.outcome().statusCode().equals("AA-550") -> "AA-700 REVIEW_QUEUED";
            case ScreeningVerdict s -> "AA-600 DOCUMENTS_REQUESTED";
            case ReviewVerdict r when r.outcome().statusCode().equals("AA-711") -> "AA-801 ACTIVATED";
            case ReviewVerdict r -> "AA-799 REVIEW_DECLINED";
            case WealthVerdict w when w.outcome().statusCode().equals("AO-145") -> "AA-700 REVIEW_QUEUED";
            case WealthVerdict w -> "AO-141 WEALTH_ACCEPTABLE";
        };
    }

    public static void main(String[] args) {
        Instant now = Instant.parse("2026-08-29T10:00:00Z");
        System.out.println(nextStatus(null));
        System.out.println(nextStatus(new DocumentVerdict(new Outcome("AA-690", "rejected"), "blurred scan", now, "op-17")));
        System.out.println(nextStatus(new DocumentVerdict(new Outcome("AA-611", "verified"), "clean", now, "op-17")));
        System.out.println(nextStatus(new ReviewVerdict(new Outcome("AA-711", "approved"), "clean", now, "op-04")));
        System.out.println(nextStatus(new WealthVerdict(new Outcome("AO-145", "referred"), "band 4", now, "system")));
    }
}
```

**Insight:** the record pattern `DocumentVerdict(Outcome(String code, String ignored), String r, Instant at, String by)`
nests. The outer pattern calls `outcome()`, the inner one calls `statusCode()` and
`label()` on the result — three accessor calls, each of which is a place a
`MatchException` can originate. That is the price of destructuring: patterns are not
free field reads, they are accessor invocations, and a record with a computed or
validating accessor turns pattern matching into arbitrary code execution.

**Pitfall:** writing an accessor that throws, or that is expensive, on a record used
as a pattern subject. Symptom: `MatchException` from a `switch` that contains no
`throw`, or a `switch` whose cost scales with how many arms precede the match. Fix:
keep record accessors trivial — a record is a data carrier, and any validation
belongs in the canonical constructor, which runs once.

The full pattern grammar, dominance rules, generic record patterns, and the
exhaustiveness algorithm are in **04 Modern Java**. `case null` and the classic
form's NPE-on-null behaviour are in
[switch on a String, on an enum, and on null](01b-string-and-enum-switch.md).

> Java 21's pattern switch matches on type and structure, binds components via
> record patterns, and reports an unmatchable selector or a throwing accessor as
> `MatchException` (JEP 441; JLS 21 §14.11, §14.30).

---

## Pitfalls

### "An arrow-form `switch` is exhaustiveness-checked"

**Wrong**

```java
static void applyRestriction(RestrictionType type, PositionStore store) {
    switch (type) {                        // statement form, arrow arms
        case STAKE_BLOCKED -> store.reserve(0);
        case SELF_EXCLUDED -> store.reserve(0);
    }
    // Compiles. Every other RestrictionType silently does nothing.
}
```

**Right**

```java
static boolean applyRestriction(RestrictionType type, PositionStore store) {
    return switch (type) {                 // expression form: coverage enforced
        case STAKE_BLOCKED, SELF_EXCLUDED, ALL_BLOCKED, COOLING_OFF, DORMANT_FROZEN -> store.reserve(0);
        case DEPOSIT_BLOCKED, WITHDRAWAL_BLOCKED, DEPOSIT_LIMITED,
             WITHDRAWAL_HELD, SOURCE_OF_FUNDS_REQUIRED -> true;
    };
    // Adding an eleventh constant is now a compile error, which is the point.
}
```

**Why people believe it:** the arrow and the exhaustiveness rule arrived together in
Java 14, so they get remembered as one feature. Exhaustiveness attaches to the
*expression* form, because only an expression is obliged to produce a value.

### "A block arm ends with its value, the way a lambda body does"

**Wrong**

```java
static int reviewPriority(String statusCode) {
    return switch (statusCode) {
        case "AA-610 DOCUMENTS_UPLOADED" -> 2;
        case "AA-700 REVIEW_QUEUED" -> {
            int base = 3;
            int queuePenalty = 1;
            base + queuePenalty;           // intended as "the value of this arm"
        }
        default -> 9;
    };
}
// Two errors, not one: `base + queuePenalty;` is not a statement, and the block arm
// can complete normally without producing a value.
```

**Right**

```java
static int reviewPriority(String statusCode) {
    return switch (statusCode) {
        case "AA-610 DOCUMENTS_UPLOADED" -> 2;
        case "AA-700 REVIEW_QUEUED" -> {
            int base = 3;
            int queuePenalty = 1;
            yield base + queuePenalty;     // every path out of a block arm yields or throws
        }
        default -> 9;
    };
}
```

**Why people believe it:** the arrow is the same token as a lambda's, and a lambda
block body *does* name its result — with `return`. The switch arm needed a different
word, because `return` inside a switch expression already means "return from the
enclosing method", which would leave the expression's value undefined; JLS 21
therefore rejects `return` in a switch expression outright. `yield` is that different
word, and it is a *restricted identifier* rather than a reserved one, because Java 14
shipped into a world where `yield` was already a method name in the JDK itself
(`Thread.yield()`) and reserving it would have broken source compatibility. The rule
to hold onto: a single-expression arm produces its value implicitly, and a block arm
must `yield` on every path that completes normally.

### "A record pattern reads the components, so destructuring can't throw"

**Wrong**

```java
record DocumentVerdict(Outcome outcome, String reason, Instant decidedAt, String decidedBy)
        implements Verdict {
    @Override public Outcome outcome() {
        if (reason == null) {
            throw new IllegalStateException("boom");   // a "defensive" accessor
        }
        return outcome;
    }
}

static String route(Verdict v) {
    return switch (v) {
        // Destructuring INVOKES outcome(). A throw here is not a failed match.
        case DocumentVerdict(Outcome(String code, String label), String r, Instant at, String by) -> code;
        default -> "AA-700 REVIEW_QUEUED";
    };
}
// route(verdictWithNullReason) -> java.lang.MatchException, cause IllegalStateException: boom.
// No `throw` appears anywhere in route().
```

**Right**

```java
record DocumentVerdict(Outcome outcome, String reason, Instant decidedAt, String decidedBy)
        implements Verdict {
    DocumentVerdict {
        // Validate once, in the canonical constructor. Accessors stay trivial field reads.
        if (outcome == null || reason == null) {
            throw new IllegalArgumentException("DocumentVerdict requires an outcome and a reason");
        }
    }
}
// Now no construction path can produce a verdict whose accessor throws, so the
// pattern switch has no way to surface a MatchException from destructuring.
```

**Why people believe it:** the syntax looks like field access and the JEP calls it
"destructuring", which suggests taking a value apart rather than calling into it. A
record pattern is specified in terms of the accessor methods, so an overridden or
computed accessor runs — nested patterns run several, one per level. Java 21 wraps a
throw from that call in `MatchException` (cause preserved) precisely because the match
neither succeeded nor failed, and the switch has no arm for "the question could not be
asked".

---

## Cheat sheet

| Thing | Rule |
|---|---|
| arrow form | no fall-through, per-arm scope, since 14 |
| four shapes | colon statement, arrow statement, arrow expression, colon expression with `yield` |
| `yield` | value out of a block arm; restricted identifier, not a keyword |
| single-expression arm | produces its value implicitly, no `yield` needed |
| exhaustiveness | required for switch **expressions** only, not arrow statements |
| exhaustive over an enum | cover every constant; `default` then becomes optional |
| exhaustive over a sealed type | cover every permitted subtype |
| exhaustiveness error text | "the switch expression does not cover all possible input values" |
| synthetic default | inserted for an exhaustive switch; throws `MatchException` on 21 |
| mixing colon and arrow | compile error: "different case kinds used in the switch" |
| pattern switch | type patterns, record patterns, `when` guards, `case null`, since 21 (JEP 441) |
| record patterns | accessor *invocations*, nestable; keep accessors trivial |
| dominance | a pattern subsumed by an earlier one is a compile error, not dead code |
| `MatchException` | unmatched exhaustive selector, or a throwing record accessor (cause preserved) |
| when to keep `default ->` | the enum or sealed type is deployed separately from the switch |

---

## Self-test

**Q1.** Which of these is exhaustiveness-checked: an arrow-form `switch` statement, or a colon-form `switch` expression using `yield`?

<details><summary>Answer</summary>

The colon-form expression. Exhaustiveness attaches to the *expression* form, not to
the arrow syntax, because only an expression is obliged to produce a value on every
path — so the compiler must prove every path is covered. An arrow-form *statement*
switch over an enum may cover two constants out of ten and compile silently, doing
nothing for the other eight. Conversely `var x = switch (t) { case A: yield 1; }`
with constants uncovered is rejected. Confirmed on JDK 21: a switch expression over
`sealed interface Rail permits Card, Bank` handling only `Card` fails with
"the switch expression does not cover all possible input values". The practical rule is
to prefer `return switch (x) { }` over `switch (x) { }` plus assignments, because the
expression form is what buys the compile error when the enum or sealed hierarchy grows.

</details>

**Q2.** Where can a `MatchException` come from, and what does it wrap?

<details><summary>Answer</summary>

Two places. First, the synthetic default of an exhaustive pattern switch: if a sealed
hierarchy gained a permitted subtype after the switch was compiled, the switch has no
arm for it, and rather than falling out with an undefined value it throws
`MatchException`. Second — the one that bites — a record pattern's accessor throwing.
Destructuring `case DocumentVerdict(Outcome(String code, String label), String r, Instant at, String by)`
invokes `outcome()`, then `statusCode()` and `label()` on the result. If a user-written
accessor throws, the pattern match neither succeeded nor failed, so Java 21 wraps the
thrown exception in a `MatchException` with the original as its cause. Verified on JDK
21: an accessor throwing `IllegalStateException("boom")` surfaced as
`java.lang.MatchException` with `cause=java.lang.IllegalStateException: boom`. The
lesson is that record accessors must stay trivial, because pattern matching executes
them.

</details>

**Q3.** When does an arrow arm need `yield`, and what happens if you write `return` there instead?

<details><summary>Answer</summary>

An arrow arm whose body is a *single expression* produces the switch's value
implicitly — `case "AA-550" -> 1;` needs nothing. An arrow arm whose body is a
*block* needs `yield`, because a block is a sequence of statements and none of them
is distinguished as the result: `case "AA-650" -> { int base = 2; yield base + 1; }`.
Every path out of a block arm in a switch expression must either `yield` a value or
complete abruptly by throwing; a block arm that can complete normally without
yielding is a compile error. `return` is not an alternative. Inside a switch
*expression*, `return` is rejected outright, because the expression is in the middle
of evaluating the enclosing method's result and returning from the method would leave
the expression's value undefined. Inside a switch *statement* the opposite holds:
`return` is legal there and `yield` is not, since a statement has no value to yield.
This is one of the places the statement/expression distinction is not cosmetic.

</details>

**Q4.** Your pattern switch lists `case ScreeningVerdict s ->` before `case ScreeningVerdict s when s.outcome().statusCode().equals("AA-550") ->`. What does the compiler say, and why is this a rule rather than a lint?

<details><summary>Answer</summary>

It is a compile error: the second label is dominated by the first. The unguarded type
pattern `ScreeningVerdict s` matches every `ScreeningVerdict`, so no value can ever
reach the guarded arm below it, and JLS 21 makes a dominated case label an error
rather than dead code. The rule exists because the chain it replaced —
`if (v instanceof ScreeningVerdict s && s.isPotentialMatch()) else if (v instanceof ScreeningVerdict s)`
— had exactly the same hazard with no diagnostic at all: reordering two `instanceof`
tests silently changed which branch ran, and the ordering was invisible in review.
Making dominance an error turns a class of ordering bug into a build failure. The fix
is to put the more specific label first: the guarded arm, then the unguarded one as
the fall-back. Note the asymmetry — a *guarded* pattern never dominates anything,
because the compiler cannot prove the guard is always true, so the ordering rule only
ever forces guards and narrower types upward.

</details>

**Q5.** You omit `default` from an exhaustive switch expression over a sealed `Verdict` hierarchy, and the hierarchy gains a fifth permitted subtype in a JAR you do not recompile against. What happens at runtime, and what is the trade you made?

<details><summary>Answer</summary>

At runtime a `Verdict` of the new subtype reaches the switch, matches no arm, and the
synthetic default `javac` inserted for the exhaustive switch throws — `MatchException`
on Java 21, `IncompatibleClassChangeError` on some earlier releases. It does not
silently return a default value, which is the correct choice: the switch was compiled
under a proof of totality that no longer holds, so continuing would mean producing a
value the code never reasoned about. The trade is explicit. Omitting `default` buys a
*compile-time* error the moment somebody adds a subtype in a build that recompiles the
switch, which is exactly the signal you want when a fifth verdict type appears and
eleven percent of activations go to manual review on the strength of these decisions.
It costs *runtime* robustness when the sealed type and the switch ship independently,
because then nothing recompiles and the failure moves from build time to request time.
The rule of thumb: omit `default` when the sealed type and the switch are in the same
build unit; write `default ->` and handle the unknown explicitly when they are not.

</details>

**Q6.** Why is mixing `case X:` and `case Y ->` in one switch a compile error rather than a per-arm choice?

<details><summary>Answer</summary>

Because the two forms disagree about what a case *is*, not merely how it is spelled.
A colon group is an entry point into one shared block: all groups share a scope, and
control flows from one into the next unless terminated. An arrow arm is a
self-contained unit with its own scope that cannot be entered from the arm above it.
There is no coherent meaning for a colon group falling into an arrow arm, and no
coherent scope for a variable declared in a colon group when an arrow arm follows it.
So JLS 21 requires every label in a switch block to use the same kind, and `javac`
reports "different case kinds used in the switch". The practical consequence is that
migration is per-block and atomic: you convert a whole switch or none of it. The error
text is unhelpfully generic and sends people hunting for a typo, so recognising it as
"you left one colon behind" is worth remembering. Converting also means auditing every
group for deliberate fall-through, since the arrow form cannot express it — grouped
labels become a comma list, but a genuine fall-through has to be rewritten.

</details>

---

## Open questions

None.

---

**Leaves covered:** 1.8.11, 1.8.12 (2 leaves)
**Leaves deferred:** none
**Diagrams included:** none
**Target version:** Java 21 LTS
**Lines:** 520
