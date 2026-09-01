# 04 Modern Java — The 95 questions, part C — INTERVIEW (§5.1)

**Target version: Java 21 LTS.** | **Part 5 of 5** | [Index](00-index.md)
Previous: [The 95 questions, part B — interview questions b](94-interview-questions-b.md) · Next: [Traps, drills and the checklist — traps drills and checklist](95-traps-drills-and-checklist.md)

### 5.1.65 "What does a sealed hierarchy buy a `switch`?"

Say this: QuizStakes models a verdict as a sealed interface — `Verdict` permits exactly
`DocumentVerdict`, `ScreeningVerdict`, `ReviewVerdict` and `WealthVerdict`. Because the compiler
knows the *complete* list of permitted subtypes — it's baked into the class file as a
`PermittedSubclasses` attribute — a pattern `switch` over a `Verdict` can be proven exhaustive at
compile time without a `default` branch, as long as every permitted subtype (or a supertype
pattern that subsumes it) has a case. Compare that to switching over a plain interface: the
compiler has no closed list, so it forces you to write `default`, and if you forget a subtype the
first anyone hears about it is a bug report. With sealing, the moment someone adds a fifth verdict
type, say `AmlVerdict`, every switch over `Verdict` that lacks a matching case **fails to compile**
until it's updated. The exhaustiveness check isn't a lint warning — it's a hard compiler error, so
the sealed hierarchy converts "did we handle every case" from a runtime hope into a build-time
guarantee.

```java
sealed interface Verdict permits DocumentVerdict, ScreeningVerdict, ReviewVerdict, WealthVerdict {}

record DocumentVerdict(String outcome, String reason, java.time.Instant decidedAt, String decidedBy)
        implements Verdict {}
record ScreeningVerdict(String outcome, String reason, java.time.Instant decidedAt, String decidedBy)
        implements Verdict {}
record ReviewVerdict(String outcome, String reason, java.time.Instant decidedAt, String decidedBy)
        implements Verdict {}
record WealthVerdict(String outcome, String reason, java.time.Instant decidedAt, String decidedBy)
        implements Verdict {}

static String route(Verdict v) {
    return switch (v) {
        case DocumentVerdict d  -> "AA-611 DOCUMENTS_VERIFIED path: " + d.outcome();
        case ScreeningVerdict s -> "AA-501 SCREENING_CLEAR path: " + s.outcome();
        case ReviewVerdict r    -> "AA-711 REVIEW_APPROVED path: " + r.outcome();
        case WealthVerdict w    -> "AO-141 WEALTH_ACCEPTABLE path: " + w.outcome();
        // no default needed — the compiler has proven this is every Verdict there is
    };
}
```

**Interview:** Sealing gives the switch a closed, compiler-known set of subtypes, so exhaustiveness
becomes a compile error instead of a runtime gap.

### 5.1.66 "Why would you deliberately omit `default` from a switch?"

Say this: you omit `default` on purpose to get a compile-time tripwire. If `AssessmentService`
routes on `Verdict` and someone on another team adds `AmlVerdict` to the sealed hierarchy six
months later, an exhaustive switch with no `default` breaks the build immediately, at every call
site that switches on `Verdict`, with a clear "not exhaustive" error pointing at the exact line.
Add a `default` "just to be safe" and that protection disappears — the new case silently falls
into whatever the `default` branch does, which is usually the wrong behavior dressed up as no
error at all. The cost is a **binary**-compatibility gap the source-compatibility guarantee doesn't
cover: if the `Verdict` module is recompiled and shipped as a jar with the new subtype, but
`AssessmentService`'s class file is *not* recompiled, the two are now binary-inconsistent, and a
`switch` that used to be exhaustive can encounter a value it has no case for at runtime — that is
exactly the scenario question 5.1.69 covers. So the tradeoff is: no `default` catches the mistake
at compile time whenever you *do* recompile together, at the cost of a rarer runtime failure mode
when you don't.

**Interview:** Omitting `default` turns "did I handle every case" into a compile error at every
call site, at the cost of a `MatchException` if the hierarchy and the switch site drift out of
binary sync.

### 5.1.67 "What is flow scoping? Why is `s` in scope after `if (!(o instanceof String s)) return;`?"

Say this: flow scoping means a pattern variable's scope is determined by definite-assignment
analysis, not by lexical nesting the way a normal local variable's scope is. For
`if (!(o instanceof String s)) return;`, the compiler reasons about the two paths out of the `if`:
if the negated condition is true — meaning `o instanceof String s` is *false* — the `return`
executes and control never reaches the code after the `if`. The only way to fall through to the
statement after the `if` is for the condition to be false, which means `!(o instanceof String s)`
is false, which means `o instanceof String s` is **true**, which means `s` was definitely
assigned. So the compiler extends `s`'s scope past the closing brace of the `if`, into the
enclosing block, because it can prove by flow analysis that every path reaching that point has `s`
bound. This is a genuine change in how Java thinks about scope: pre-16, scope was purely
lexical — a block's braces were the scope. Pattern variables use "the set of program points where
the pattern is definitely matched," which can extend past a brace, stop short of one, or (for `&&`
chains) start mid-expression.

```java
static String describeIdentifier(Object identifier) {
    if (!(identifier instanceof ClientId id)) {
        return "not a client id";
    }
    // id is in scope here — flow analysis proved this line is only reached when the cast holds
    return "client " + id;
}
```

**Insight:** the rule isn't "negated instanceof extends scope" as a special case — it's the general
definite-assignment analysis the compiler already runs for local variables, applied to pattern
variables. It falls out of the same machinery that flags "variable might not have been
initialized."

**Interview:** Pattern variable scope follows flow analysis, not braces — `s` is visible wherever
the compiler can prove the match must have succeeded to reach that point.

### 5.1.68 "What happens when a pattern switch gets a null?"

Say this: unlike a classic `switch` on a boxed type or an enum, a pattern `switch` does **not**
implicitly throw on `null` at the top — `null` is a value the switch can explicitly route with a
`case null` label. If you write a pattern switch with type-pattern cases and a plain `default`,
but no `case null`, and the selector is `null`, you get a `NullPointerException`, not a
`MatchException` and not a silent match into `default`. I verified this directly: compiling a
switch over `Verdict` with cases for `DocumentVerdict`/`ScreeningVerdict` and a bare `default`,
then calling it with `null`, threw `java.lang.NullPointerException` — the switch does an explicit
null-check up front (`Objects.requireNonNull` shows up in the bytecode) before it ever consults the
`typeSwitch` bootstrap. Add `case null ->` (optionally combined as `case null, default ->`) and the
`null` now matches that label instead of throwing:

```java
static String label(Object o) {
    return switch (o) {
        case null -> "no verdict yet";                 // must be explicit
        case DocumentVerdict d -> "doc:" + d.outcome();
        default -> "other";
    };
}
```

**Pitfall:** assuming `default` catches `null` the way it catches every other unmatched value.
`default` alone does **not** match `null` — only `case null` or the combined `case null, default`
label does. Forgetting the `case null` on a selector that legitimately carries `null` (a client
lookup that hasn't happened yet, in QuizStakes terms) turns a normal "not present" case into an
`NullPointerException` in production. Fix: always ask "can this selector be `null`?" before
choosing whether to add `case null`.

**Interview:** A pattern switch throws `NullPointerException` on a `null` selector unless you add
an explicit `case null` label — `default` alone won't catch it.

### 5.1.69 "What is `MatchException` and when have you seen one?"

**The 30-second version:** `java.lang.MatchException` is a `RuntimeException` the JVM throws when
a switch expression or statement that the compiler proved exhaustive turns out, at run time, to
not actually cover the value it's handed — almost always because of a binary-compatibility skew
between when the switch was compiled and when the type it switches on changed shape.

**The 5-minute version:** I reproduced this on this machine two ways, and both point at the same
root cause: the compiler's exhaustiveness proof is checked at compile time against the class files
it sees *then*, and nothing re-validates that proof at run time except a fallback throw if the
value doesn't land in any case. First, the classic enum case: compile an enum switch expression
with `case CARD -> ...` / `case BANK -> ...` and no default, decompile it, and the fallback path
literally is a `MatchException`:

```
32: new           #13    // class java/lang/MatchException
35: dup
36: aconst_null
37: aconst_null
38: invokespecial #15    // Method java/lang/MatchException."<init>":(Ljava/lang/String;Ljava/lang/Throwable;)V
41: athrow
```

That's the ordinal-based `lookupswitch` falling through to `default:` at bytecode offset 32,
constructing a `MatchException` with `(null, null)` — no message, no cause — and throwing it. This
is also the corrected version of a widely-stated fact: through Java 20 that same synthetic
fallback threw `IncompatibleClassChangeError`; from Java 21 it throws `MatchException`. The
synthetic default has existed at every release — what changed at 21 is the exception *type*, not
its existence. I compiled the identical enum-plus-switch source across `--release 14`, `--release
17` and `--release 21`, removed a constant and recompiled only the enum without touching the
switch's class file, and got:

```
release 14 -> Exception in thread "main" java.lang.IncompatibleClassChangeError
release 17 -> Exception in thread "main" java.lang.IncompatibleClassChangeError
release 21 -> Exception in thread "main" java.lang.MatchException
```

Second, the sealed-type case, which is the one you'll actually describe as "when have you seen
one" in an interview: imagine `Verdict` ships in its own module, sealed to
`DocumentVerdict`/`ScreeningVerdict`/`ReviewVerdict`/`WealthVerdict`, and `AssessmentService` has a
pattern switch routing on it, compiled against that four-case hierarchy. Compliance adds a fifth
permitted subtype, `AmlVerdict`, recompiles the `Verdict` module, and it ships as an updated jar —
but `AssessmentService`'s class file is *not* recompiled against the new jar (a partial deploy, a
stale artifact in a shared library repo). At run time, an `AmlVerdict` instance reaches
`AssessmentService`'s switch. The compiler's exhaustiveness proof was valid when it ran — against
the old, four-case `Verdict` — but the world has moved on underneath it. The switch has no case
for `AmlVerdict`, hits the synthetic default, and throws `MatchException`. That's the honest
"when have you seen one" story: not a bug in the switch, but binary skew between a sealed
hierarchy and a switch that was exhaustive when it was compiled and stopped being exhaustive when
one side of the pair moved without the other.

**Pitfall:** treating `MatchException` as "the switch has a bug." It almost never does — the
compiler already proved the switch exhaustive against what it saw. `MatchException` is evidence
that the class files on the classpath at run time disagree with the class files the compiler
checked against at compile time. The fix is redeploying the consuming module together with the
hierarchy, not adding a defensive `default`.

**Interview:** `MatchException` is the runtime's admission that a switch the compiler proved
exhaustive no longer is, almost always from a sealed hierarchy or enum changing shape without the
switch site being recompiled against it; before Java 21 the same situation threw
`IncompatibleClassChangeError` instead.

### 5.1.70 "Explain dominance. Why must a guarded case come first?"

Say this: dominance is the compile-time check that stops a pattern switch from containing
unreachable cases. One case label **dominates** another if every value the later label could match
is already matched by the earlier one — in which case the later label can never be selected, and
the compiler rejects the switch with "this case label is dominated by a preceding case label." The
critical wrinkle is that **dominance analysis ignores guards** — a `when` clause narrows *which*
values a case handles at runtime, but it plays no part in deciding whether one pattern subsumes
another at compile time. That's precisely why a guarded case must be written **before** the
unguarded case with the same or a broader pattern: an unguarded `case ScreeningVerdict s` matches
every `ScreeningVerdict`, full stop — the compiler doesn't look at whether a later case has a
guard, it only looks at the pattern shape. So if you write the unguarded case first, a later
`case ScreeningVerdict s when s.outcome().equals("CLEAR")` is dead code by pattern shape alone (the
guard doesn't rescue it), and the compiler rejects it as dominated. Flip the order — guarded case
first, unguarded case second — and there's no domination, because the guarded case doesn't cover
*every* `ScreeningVerdict`, only some of them; the unguarded case that follows is reachable for the
rest.

```java
// Correct: guarded case first
static String status(Verdict v) {
    return switch (v) {
        case ScreeningVerdict s when s.outcome().equals("AA-599") -> "prohibited, escalate";
        case ScreeningVerdict s -> "screening: " + s.outcome();   // reachable — catches the rest
        case DocumentVerdict d -> "documents: " + d.outcome();
        default -> "other";
    };
}
```

```
// Wrong order — compile error
static String broken(Verdict v) {
    return switch (v) {
        case ScreeningVerdict s -> "screening: " + s.outcome();
        case ScreeningVerdict s when s.outcome().equals("AA-599") -> "prohibited"; // dominated — dead code
        default -> "other";
    };
}
```

`[PROVE]` Why this must be true in general, not just for this example: suppose the compiler *did*
let a guard rescue a dominated case. Then reachability of the later case would depend on the
runtime value of the guard expression — something the compiler cannot evaluate at compile time in
general (the guard can call arbitrary methods). Exhaustiveness and dead-code analysis are
compile-time properties; if dominance depended on guard truth, the compiler could never statically
decide reachability, and the whole point of the dominance check — catching genuinely unreachable
patterns before runtime — would collapse into "maybe unreachable, we can't tell." Ignoring guards
for dominance is what keeps the check decidable.

**Interview:** Dominance is pattern-shape-only; guards never rescue a case from being dominated,
so a guarded case must precede the broader unguarded case it's carving an exception out of.

### 5.1.71 "What are record patterns and how deep can they nest?"

Say this: a record pattern deconstructs a record in the pattern itself, binding each component to
a nested pattern instead of binding the whole record and then calling accessors. QuizStakes has
`StakeSplit(Money bonusPortion, Money cashPortion)` and `Money(BigDecimal amount, Currency
currency)` — a record pattern can match a `StakeSplit` and, in the same pattern, reach *into* each
`Money` component and bind its `amount` and `currency` directly, with no accessor calls in the
body at all. Nesting has no fixed depth limit — you can nest a record pattern inside a record
pattern inside a record pattern, as deep as the object graph actually goes, and each level can mix
type patterns, `var` patterns and further record patterns freely. The compiler desugars nested
record patterns into a sequence of `instanceof`-and-accessor checks, one level at a time, so the
runtime cost is proportional to the nesting depth, not free — but there's no artificial ceiling
the JLS imposes.

```java
record Money(java.math.BigDecimal amount, java.util.Currency currency) {}
record StakeSplit(Money bonusPortion, Money cashPortion) {}
record Reservation(String roundId, StakeSplit split) {}

static String describe(Object o) {
    return switch (o) {
        // three levels deep: Reservation -> StakeSplit -> Money, both sides
        case Reservation(String roundId,
                          StakeSplit(Money(var bonusAmt, var ccy), Money(var cashAmt, var ccy2)))
                when ccy.equals(ccy2) ->
            "round " + roundId + ": bonus=" + bonusAmt + " cash=" + cashAmt + " " + ccy;
        case Reservation r -> "mismatched currency split in round " + r.roundId();
        default -> "not a reservation";
    };
}
```

Every binding (`roundId`, `bonusAmt`, `ccy`, `cashAmt`, `ccy2`) is directly usable in the case
body — no `.split().bonusPortion().amount()` chain. Record patterns can also use `var` for any
component whose type is obvious from the record's declaration, which is what keeps deep nesting
readable instead of a wall of explicit types.

**Interview:** Record patterns deconstruct nested records inline in the pattern, to arbitrary
depth, with each level compiling to an `instanceof`-plus-accessor check.

### 5.1.72 "How does a pattern switch compile? Is it a chain of `instanceof`?"

Say this: no — it is not simply lowered into a chain of `if (x instanceof T t) ... else if
(x instanceof U u) ...`. I compiled a pattern switch over `Verdict` (a `DocumentVerdict` case, a
guarded `ScreeningVerdict` case, then an unguarded `ScreeningVerdict` case, then `default`) and
decompiled it. The real mechanism is an `invokedynamic` call to a bootstrap method — `typeSwitch`
in `java.lang.runtime.SwitchBootstraps` — that takes the selector and a "starting index," and
returns which case index matches, which the bytecode then dispatches on with an ordinary
`tableswitch`:

```
9: aload_1
10: iload_2                       // the restart index, starts at 0
11: invokedynamic #13,0           // typeSwitch:(Ljava/lang/Object;I)I
16: tableswitch { 0: 44  1: 61  2: 90  default: 109 }
```

The interesting part is what happens when a guard fails. The bytecode I produced has a **restart
loop**: case 1 (the guarded `ScreeningVerdict` at offset 61) checks the type with `checkcast`,
evaluates the guard, and if the guard is false it does `iconst_2; istore_2; goto 9` — it
increments the restart index to `2` and jumps back to the same `invokedynamic` call at offset 11,
asking the bootstrap "starting your search from index 2, which case matches now?" That's how a
guard failing at case *k* correctly falls through to case *k+1* onward rather than restarting the
whole match from case 0 or skipping straight to `default`: the index threaded through the
`invokedynamic` call *is* the fallthrough position. So the actual shape is: one indirect call per
switch evaluation (cached after first linkage, the way all `invokedynamic` call sites are), a
`tableswitch` on the returned index, and — only for guarded cases — a loop back into that same call
site with an advanced index if the guard rejects the match. That's meaningfully different from a
flat `instanceof` chain: the type tests and the guard evaluation are two separate steps threaded
through a shared bootstrap, not independent `if`/`else if` branches you'd hand-write.

**Insight:** the restart index is exactly why dominance (5.1.70) has to be checked at compile
time and can't be deferred to runtime — the runtime mechanism has no way to "back up" past a case
it already determined does not match; it can only move forward from wherever the last guard
rejection left off.

**Interview:** A pattern switch compiles to an `invokedynamic` call into `SwitchBootstraps
.typeSwitch`, a `tableswitch` on the returned index, and — for guarded cases — a loop that re-calls
the bootstrap with an advanced index when a guard fails; it is not a flat `instanceof` chain.

### 5.1.73 "Switch statement vs switch expression — name three differences."

| Aspect | Switch statement | Switch expression |
|---|---|---|
| Produces a value | No — falls through to whatever comes after | Yes — the whole construct evaluates to a value used in an assignment, return, argument, etc. |
| Exhaustiveness | Never required, even for enums or sealed types | Required — every possible input must be covered (a `default`, or the compiler-proven closed set) |
| Fallthrough between labels | `case` labels with `:` fall through to the next label unless you `break` | Arrow labels (`->`) never fall through — each case is a self-contained block, no `break` needed |
| Multiple labels per case | `case A: case B:` stacked, one per line | `case A, B ->` on one label |
| How a case yields its value | Not applicable (no value produced) | Arrow form: the expression after `->` *is* the value; block form: `yield` supplies it |

A fourth worth knowing even though only three were asked for: a switch **expression** must be
exhaustive to compile at all — a non-exhaustive switch expression over, say, a sealed type missing
a permitted subtype and no `default`, is a compile error, not a runtime risk. A switch
**statement** has no such requirement in either form; it's legal (if usually a code smell) to
switch on a sealed type in statement form and simply do nothing for the cases you didn't list.

**Interview:** A switch expression must produce a value and must be exhaustive; a switch statement
does neither, and colon-labels fall through where arrow-labels never do.

### 5.1.74 "`yield` vs `return` inside a switch."

Say this: `yield` supplies the value of the *enclosing switch expression* from within a block-form
case; `return` exits the *enclosing method*, jumping straight past the switch and out of the whole
method call. They are not interchangeable, and using the wrong one either doesn't compile or does
something you didn't intend. In arrow form, the expression after `->` is implicitly the case's
value and neither keyword is needed for the simple case; but the moment a case needs more than one
statement, you switch to a block `{ ... }` and that block must produce its value with `yield`:

```java
static String riskBand(int screeningHits) {
    return switch (screeningHits) {
        case 0 -> "clear";                                  // arrow: expression is the value
        case 1, 2 -> {
            String note = "borderline, " + screeningHits + " hit(s)";
            yield note;                                      // block form: yield supplies the value
        }
        default -> {
            if (screeningHits >= 10) {
                return "AA-599";                              // return exits riskBand entirely, bypassing the switch's value
            }
            yield "AA-550";                                   // yield supplies the switch's value instead
        }
    };
}
```

**Pitfall:** writing `return` inside a switch **expression**'s block case expecting it to behave
like `yield`. It compiles (it's legal to `return` from inside a switch expression's block), but it
does not make that value the switch's result — it exits the method immediately, so any code after
the switch, and the assignment the switch's result was meant to feed, never happens. This is a
real bug class, not a style nit: it shows up as "the method returned early and none of the
downstream ledger update happened," and the fix is checking every block-form case for a stray
`return` where `yield` was meant.

**Interview:** `yield` hands a value back to the switch expression; `return` exits the whole
method — mixing them up inside a block case is a real, silent bug, not a style choice.

### 5.1.75 "What is `$SwitchMap` and why does it exist?"

Say this: I compiled a classic (colon-form) `switch` on a **top-level, separately-compiled** enum
and decompiled the result, and it generated a synthetic nested class — `EnumSwitchStmt2$1` — with
a single field, `static final int[] $SwitchMap$Rail`, populated in a static initializer:

```
static final int[] $SwitchMap$Rail;
static {};
    invokestatic  Rail.values:()[LRail;
    arraylength
    newarray int
    putstatic $SwitchMap$Rail:[I
    getstatic $SwitchMap$Rail:[I
    getstatic Rail.CARD:LRail;
    invokevirtual Rail.ordinal:()I
    iconst_1
    iastore                          // wrapped in a try/catch NoSuchFieldError, per constant
    ...
```

The map is `[ordinal-of-CARD -> 1, ordinal-of-BANK -> 2, ...]`, built once per class that switches
on that enum, and each entry is wrapped in its own `try { ... } catch (NoSuchFieldError e) {}`
block. That try/catch is the actual reason `$SwitchMap` exists: a `switch` on an enum compiles
down to a `lookupswitch`/`tableswitch` on the enum constant's **ordinal**, but ordinals are only
stable within one compilation. If `Rail` is reordered or a constant is removed and only `Rail` is
recompiled — not the class doing the switch — a `NoSuchFieldError` at the static-init line for the
missing constant is exactly the failure that *would* happen if the map build assumed every
constant still exists; catching it per-constant lets the map degrade gracefully (that slot just
stays `0`) instead of the whole class failing to initialize. Crucially, I confirmed the synthetic
class is **only generated when the enum lives in a separate top-level compilation unit** from the
switch. A `switch` on an enum declared inside the *same file* as the switch — I tested this
directly — produces **no** `$SwitchMap` class at all; the compiler emits a direct `ordinal()` call
and `lookupswitch` with no indirection, because there's no cross-compilation-unit skew to guard
against.

**Version behavior:** none of this applies to modern **switch expressions on sealed types** or
pattern switches (5.1.72) — those use the `SwitchBootstraps.typeSwitch` `invokedynamic` mechanism
introduced with pattern matching for switch, which has nothing to do with `$SwitchMap`. Plain
`switch` on an enum, even written today in arrow form, still goes through the ordinal-based
`lookupswitch`, and `$SwitchMap` still appears whenever the enum and the switch site are compiled
separately. This is a piece of javac machinery that predates records and sealed types by well over
a decade and simply never went away.

**Interview:** `$SwitchMap` is a per-class-file cache mapping enum ordinals to case indices,
generated only when the enum being switched on is compiled separately from the switch, so a
reordered or removed constant fails soft via a caught `NoSuchFieldError` instead of corrupting the
map.

### 5.1.76 "How does a text block decide indentation?"

Say this: the compiler computes **incidental whitespace** — the common leading-whitespace prefix
shared by every non-blank content line and the closing delimiter's line — and strips exactly that
much from every line, regardless of how far the text block is indented in the source file. Nesting
a text block four levels deep inside a method does not bake four levels of indentation into the
resulting string, because the closing `"""` participates in the minimum-indentation calculation:
put the closing delimiter flush with the content and you get zero stripped; indent the closing
delimiter to match the content's own indentation and *that* becomes the common margin. Trailing
whitespace on each line is stripped unconditionally (not just the incidental amount) unless
protected with `\s` (5.1.77).

```java
static String stakeSettlementSql() {
    return """
        SELECT amount, currency
        FROM ledger_entry
        WHERE position IN ('CLIENT_CASH_AVAILABLE', 'CLIENT_BONUS_AVAILABLE')
          AND round_id = ?
        """;
}
```

Here the closing `"""` lines up with `SELECT`, `FROM`, `WHERE`'s common 8-space margin, so that
8-space indentation is incidental and stripped; the result starts at `SELECT amount, currency` with
no leading spaces, and the `AND` line keeps its two extra spaces relative to `WHERE` because those
are *beyond* the common margin, not part of it.

**Pitfall:** assuming the source-file indentation of the text block literal is preserved verbatim.
It isn't — indent the whole literal to match surrounding code (which you should, for
readability) and the compiler removes exactly that indentation from the resulting `String`, because
it computes the margin from the block's own lines, not from column zero.

**Interview:** Text-block indentation is computed as the smallest common leading whitespace across
every content line and the closing delimiter, then stripped from all of them — so re-indenting the
whole block in source doesn't change the value it produces.

### 5.1.77 "What does `\s` do in a text block, and why would you need it?"

Say this: `\s` is an escape for a single literal space character, and it exists specifically to
defeat the automatic trailing-whitespace stripping described in 5.1.76. Every line of a text block
has its trailing whitespace removed unconditionally, independent of the incidental-whitespace
calculation — this keeps editors that trim trailing spaces on save from silently altering a text
block's meaning. But sometimes trailing spaces are semantically part of the string, most commonly
in fixed-width or padded output. Ending a line with `\s` instead of a real trailing space marks
that space as significant, so it survives the strip.

```java
static String paymentRunHeader() {
    return """
        PaymentRun\s\s\s\sStatus
        ----------------------
        """;
}
```

Without the `\s\s\s\s`, four trailing spaces meant to pad `PaymentRun` out to a fixed column would
simply vanish at compile time, and the header row would silently misalign against the dashed
separator line below it — exactly the kind of bug that only shows up when someone diffs rendered
output and can't see why the columns are off by four characters.

**Interview:** `\s` is an escaped literal space that survives text blocks' automatic trailing-space
stripping — needed whenever trailing spaces are meaningful, like padded columns.

### 5.1.78 "Are text blocks interned?"

Say this: yes, exactly the same way any compile-time-constant `String` literal is. A text block
with no interpolation and no runtime concatenation is a constant expression, so javac puts its
final value — after indentation stripping and escape processing — into the class file's constant
pool, and the first reference to it at run time interns it into the JVM's string pool just like
`"CLIENT_BONUS_RESERVED"` would be. Two text blocks in different classes that produce character-
for-character identical content **after** the compiler's stripping step are `==`-equal at runtime,
for the same reason two ordinary string literals with the same text are. The moment a text block
stops being a compile-time constant — because it's built with `+` against a runtime variable, or
formatted with `.formatted(...)` — it's an ordinary heap `String` like any other, not interned
unless you call `.intern()` yourself.

```java
static final String LEDGER_QUERY = """
        SELECT amount FROM ledger_entry WHERE round_id = ?
        """;
// LEDGER_QUERY == "SELECT amount FROM ledger_entry WHERE round_id = ?\n" -> true, both interned
```

**Pitfall:** believing text blocks get some special non-interned "multi-line string" treatment
because the syntax looks different from a regular literal. Mechanically, by the time the compiler
is done stripping indentation and normalizing line terminators, a constant text block *is* a
`String` literal, entered into the constant pool exactly the same way — there is no separate
runtime representation.

**Interview:** A constant text block is interned exactly like any string literal, because after
indentation stripping it becomes a constant-pool entry — that stops the moment it's built with
runtime concatenation.

### 5.1.79 "Does Java have string interpolation?"

Say this: not as a shipped, stable feature as of Java 21 — the closest thing, **string templates**
(`STR."Round \{roundId} settled \{amount}"`), was a **preview** feature (JEP 430 in Java 21, JEP
459 second preview in Java 22), and it was **withdrawn** rather than finalized: the OpenJDK team
pulled it after the second preview to redesign the feature, so it never shipped as a permanent
Java language feature in the JDK 21/22 shape. What Java has always had, and still has, is
`String.format`, `"%s".formatted(...)`, and plain `+` concatenation — none of which is
"interpolation" in the sense of a literal embedding an expression directly inside `{}` markers
resolved by the compiler. If you're asked this cold, the honest answer is: there *was* a preview
feature aimed at exactly this, it changed shape and got pulled, and as of the LTS releases through
21, Java does not have finalized string interpolation — you reach for `.formatted(...)` or a text
block plus `String.format`.

```java
// what Java 21 actually has (no interpolation):
String roundId = "R-48213";
java.math.BigDecimal settled = new java.math.BigDecimal("3.33");
String line = "Round %s settled %s".formatted(roundId, settled);
```

**Version behavior:** don't state string templates as a shipped Java 21 feature — it requires
`--enable-preview` even in 21/22, and was withdrawn afterward rather than promoted to standard, so
code depending on it isn't something you'd write in production against an LTS release.

**Interview:** No — string interpolation existed only as the preview "string templates" feature
in Java 21/22, which was withdrawn rather than finalized; `.formatted(...)` is the standard tool.

### 5.1.80 "What is a virtual thread and how is it scheduled?"

**The 30-second version:** a virtual thread is a `Thread` implementation whose stack lives on the
heap rather than being pinned to a fixed-size OS thread stack, and whose execution is scheduled
onto a small pool of OS threads (called *carriers*) by a user-mode scheduler rather than the OS
kernel. The JDK creates and destroys them cheaply — no OS thread, no OS-level context switch — so
you can run hundreds of thousands of them concurrently, which makes thread-per-request/thread-per-
stake-reservation style code scale without needing an async/reactive rewrite.

**The 5-minute version:** the default scheduler backing virtual threads is a dedicated
`ForkJoinPool`, built by `VirtualThread.createDefaultScheduler()`. I pulled the exact source at the
`jdk-21+35` tag and it's more nuanced than the number everyone quotes:

```java
int parallelism, maxPoolSize, minRunnable;
// ... reads jdk.virtualThreadScheduler.parallelism / .maxPoolSize / .minRunnable
if (parallelismValue != null) {
    parallelism = Integer.parseInt(parallelismValue);
} else {
    parallelism = Runtime.getRuntime().availableProcessors();
}
if (maxPoolSizeValue != null) {
    maxPoolSize = Integer.parseInt(maxPoolSizeValue);
    parallelism = Integer.min(parallelism, maxPoolSize);
} else {
    maxPoolSize = Integer.max(parallelism, 256);
}
if (minRunnableValue != null) {
    minRunnable = Integer.parseInt(minRunnableValue);
} else {
    minRunnable = Integer.max(parallelism / 2, 1);
}
boolean asyncMode = true; // FIFO
return new ForkJoinPool(parallelism, factory, handler, asyncMode,
             0, maxPoolSize, minRunnable, pool -> true, 30, SECONDS);
```

Four things this source settles, that most blog-level material gets wrong or leaves out:

- **Default parallelism** is `availableProcessors()` — on the 8-core box these notes use
  consistently, that's **8**.
- **`maxPoolSize` defaults to `Integer.max(parallelism, 256)` — 256 is a floor, not the default on
  every machine.** On an 8-core box, `max(8, 256)` = **256**. Only on a box with *more* than 256
  available processors does `maxPoolSize` exceed 256 and track the core count instead — say
  "256 is the floor" rather than "the default is 256," because on a 300-core machine it isn't.
- Setting `jdk.virtualThreadScheduler.maxPoolSize` **below** the processor count doesn't just cap
  pool growth — it **clamps `parallelism` down to it too** (`parallelism = min(parallelism,
  maxPoolSize)`), so one system property silently moves two different numbers.
- `minRunnable` defaults to `max(parallelism / 2, 1)` — on the 8-core box, `max(4, 1)` = **4** — a
  third tuning knob (`jdk.virtualThreadScheduler.minRunnable`) most material never mentions at all.

The pool itself is constructed with `asyncMode = true`, and the source's own inline comment on that
exact line is `// FIFO` — that comment is the evidence for "virtual thread scheduling is FIFO,"
not folklore. It also carries a 30-second worker keep-alive and a `pool -> true` saturation
predicate (the pool never refuses to grow toward `maxPoolSize` on the saturation check). The
scheduling model in one sentence: a virtual thread is a *task* submitted to this `ForkJoinPool`;
when it blocks on a supported operation it unmounts from its carrier (5.1.81) and the carrier goes
back to picking up other virtual-thread tasks, which is the entire mechanism that lets 55k
concurrent QuizStakes client sessions ride on 8 carrier threads instead of 55k OS threads.

**Interview:** A virtual thread is a heap-allocated, JDK-scheduled `Thread` running on a small pool
of carrier OS threads via a dedicated `ForkJoinPool`; parallelism defaults to the core count,
`maxPoolSize` defaults to `max(parallelism, 256)` — a floor, not a flat 256 — and the pool runs
FIFO by the source's own comment.

### 5.1.81 "Walk me through mounting and unmounting."

Say this: mounting is a virtual thread being assigned to run on a carrier (platform) thread;
unmounting is it being taken back off that carrier so the carrier is free to run something else,
while the virtual thread's state is preserved on the heap to resume later. The mechanism underneath
is a `Continuation` — the virtual thread's stack frames are captured as a continuation object
rather than living in the OS thread's native stack. When a virtual thread performs a blocking
operation the JDK has taught to cooperate with this — `Thread.sleep`, blocking I/O on the modern
NIO-backed socket/file APIs, `java.util.concurrent` locks, blocking queue operations — instead of
parking the carrier OS thread the way old-style blocking would, the runtime **unmounts** the
virtual thread: it freezes the continuation (its Java stack frames, local variables, and the
current instruction pointer), returns the carrier to the scheduler's pool to go pick up other
virtual-thread work, and stashes the frozen continuation until the blocking condition clears. When
it clears — the socket has data, the lock is free, the sleep duration elapses — the scheduler
**mounts** the virtual thread onto *some* carrier (not necessarily the same one it started on) and
resumes the continuation exactly where it froze. A single virtual thread might mount onto three
different carrier threads over its lifetime, one per unmount/remount cycle, and that's completely
invisible to the code running on it — `Thread.currentThread()` still returns the same virtual
`Thread` object throughout.

```java
// Reserving a stake: blocks on the Quiz Engine call, then on a ledger write.
// Neither blocking point requires the carrier to sit idle — the virtual thread unmounts at each.
Verdict reserve(String roundId, java.math.BigDecimal stake) throws Exception {
    var ack = quizEngineClient.reserveStake(roundId, stake);   // unmounts while awaiting I/O
    ledger.write(roundId, ack);                                // unmounts again on the ledger call
    return ack.verdict();
}
```

**Insight:** the whole value proposition collapses to one sentence — unmounting exists so that
"blocked" and "occupying an OS thread" stop being the same event. Pre-Loom, a thread blocked on I/O
still held its OS thread hostage; a virtual thread blocked on I/O releases its carrier back to the
pool, which is the mechanism, not a side effect, behind running orders of magnitude more concurrent
blocking operations than you have OS threads.

**Interview:** Mounting/unmounting is a `Continuation` being frozen off a carrier thread (on a
cooperating block) and later thawed back onto some carrier — the carrier is only ever occupied
while the virtual thread is actually runnable, not while it's blocked.

### 5.1.82 "What is pinning? What causes it on Java 21, and what changed in 24?"

**The 30-second version:** pinning is a virtual thread blocking *without* unmounting — it keeps
its carrier occupied for the duration of the block, defeating the entire scaling model, because now
one blocked "cheap" thread is holding one expensive OS thread hostage exactly like pre-Loom code
did. On Java 21, the two causes are executing inside a `synchronized` block or method while
blocking, and executing inside a native frame (a JNI call, or a foreign-function call) while
blocking.

**The 5-minute version, dated at every claim:** on Java 21, entering a `synchronized` block or
method makes the virtual thread's continuation **not freezable** while that monitor is held —
JEP 491 didn't exist yet, and the JVM's object-monitor implementation wasn't continuation-aware, so
if code blocks on I/O or another lock *while holding a `synchronized` monitor*, the virtual thread
pins its carrier for the full duration instead of unmounting. Picture the exact QuizStakes shape
that triggers this: a legacy JDBC driver wrapped by `CardPayments` predates virtual threads and
still uses `synchronized` internally around its connection object; a repository method calls into
it from inside its own `synchronized` block to serialize access to a shared connection pool
handle:

```java
class LegacyCardPaymentGateway {
    private final Object connectionLock = new Object();
    private final java.sql.Connection legacyJdbcConnection;

    String capturePayment(String paymentIntentId) throws java.sql.SQLException {
        synchronized (connectionLock) {                 // holding a monitor...
            try (var stmt = legacyJdbcConnection.prepareStatement(
                    "UPDATE payment_intent SET status = 'DEP-301' WHERE id = ?")) {
                stmt.setString(1, paymentIntentId);
                stmt.executeUpdate();                     // ...while blocking on network I/O — pins the carrier
                return "DEP-301 CAPTURED";
            }
        }
    }
}
```

On Java 21, that `executeUpdate()` call blocks on socket I/O *inside* the `synchronized` block, so
the virtual thread cannot unmount — it pins `CardPayments`'s carrier for the full round trip to the
database, no matter how many other stake settlements are waiting for a carrier. Native frames pin
for a different reason entirely: the continuation freezing machinery walks and relocates Java
stack frames, and it simply has no representation for a native (JNI or foreign-function) stack
frame — it can't freeze what it can't describe, so any block while inside a native call pins,
version-independent of everything below.

**What changed in Java 24:** JEP 491 makes JDK object-monitor implementation continuation-aware,
so `synchronized` **no longer pins** starting in Java 24 — a virtual thread blocking while holding
a `synchronized` monitor can unmount just like it can outside one. That removes the single most
common pinning cause developers hit in practice. What does **not** change: native and foreign
frames still pin on 24, because that's a structural limitation of what a continuation can capture,
not an implementation gap JEP 491 addresses — so the `jdk.VirtualThreadPinned` JFR event (5.1.83)
survives into 24, it just fires far less often. The practical consequence: "replace `synchronized`
with `ReentrantLock` to avoid pinning" is a **version-scoped** answer — correct advice on Java 21,
and unnecessary (though harmless) advice from Java 24 onward, once you're actually running on 24.

**Pitfall:** citing "avoid `synchronized`, use `ReentrantLock`" as a timeless virtual-thread rule.
State the version: it's the fix for Java 21's `synchronized`-pins-a-carrier behavior, and JEP 491
in Java 24 removes the need for it for that specific cause, while leaving native-frame pinning
untouched at every version.

**Interview:** Pinning is a virtual thread blocking without unmounting, keeping its carrier
occupied; on Java 21 it's caused by blocking inside `synchronized` (monitor implementation isn't
continuation-aware yet) or inside a native frame — JEP 491 in Java 24 fixes the `synchronized`
case, but native-frame pinning is structural and persists.

### 5.1.83 "How do you detect pinning in production?"

Say this: the primary tool is JFR — the JDK emits a `jdk.VirtualThreadPinned` event every time a
virtual thread pins its carrier, and it carries a stack trace of exactly where the pin happened, so
you don't have to guess which `synchronized` block or native call is responsible. In production
you'd enable a continuous JFR recording (low overhead, designed to run always-on) and either stream
events to an observability pipeline or periodically dump and inspect the recording, filtering for
`jdk.VirtualThreadPinned`. There's also a JVM flag, `-Djdk.tracePinnedThreads=full` (or `short` for
a condensed form), that prints a stack trace directly to stdout/stderr the instant a pin occurs —
useful for a quick local repro against the `LegacyCardPaymentGateway` example in 5.1.82, but too
noisy and too much I/O overhead to leave on in a production fleet processing 3,400 stake
settlements/sec. The practical workflow: run `-Djdk.tracePinnedThreads=full` against a load test or
staging traffic to find pin sites cheaply during development, then rely on the JFR event in
production so the always-on, low-overhead path catches pins that only show up under real traffic
patterns (a connection-pool exhaustion path, a rare retry branch) that a load test didn't exercise.

```
$ java -Djdk.tracePinnedThreads=full -jar quizstakes-payments.jar
Thread[#31,CardPayments-vt-7,5,CarrierThreads]
    java.base/java.net.Socket$SocketInputStream.socketRead0(Native Method)
    ...
    <-- LegacyCardPaymentGateway.capturePayment(LegacyCardPaymentGateway.java:9) <== monitors:1
```

**Interview:** `jdk.VirtualThreadPinned` JFR events (always-on, low overhead, carries the stack) for
production; `-Djdk.tracePinnedThreads=full` for a fast local repro during development.

### 5.1.84 "Should you pool virtual threads?"

Say this: no — pooling defeats the entire point, and the JDK's own `Executors
.newVirtualThreadPerTaskExecutor()` is a deliberate statement that the intended usage pattern is
one virtual thread per task, created fresh, never reused. Pooling exists in the platform-thread
world to amortize the real cost of an OS thread — the megabyte-scale stack allocation, the kernel
scheduling entity, the context-switch overhead — over many short-lived tasks, because *creating*
that OS thread is expensive relative to the work it'll do. A virtual thread doesn't carry that
cost: its "stack" starts as a small, growable heap-allocated chunk, there's no OS-level entity to
set up, and creation is closer to allocating an object than spinning up a kernel thread. Pool them
anyway and you inherit every pooling downside — a fixed capacity that can exhaust under load
(exactly the resource-starvation failure thread pools are notorious for), thread-local state
leaking across "borrowed" reuse, no natural per-task lifecycle for structured concurrency to hook
into — while gaining nothing, because there is no expensive creation cost to amortize. The right
mental model: a virtual thread is a *task representation*, not a *resource*. You don't pool
`Runnable`s; you don't pool virtual threads for the same reason.

```java
// Right: one virtual thread per stake reservation, created and discarded per request
try (var executor = Executors.newVirtualThreadPerTaskExecutor()) {
    for (var reservation : pendingReservations) {
        executor.submit(() -> quizEngineClient.reserveStake(reservation.roundId(), reservation.stake()));
    }
} // executor.close() waits for outstanding tasks — every virtual thread it spawned is already done or abandoned
```

**Pitfall:** wrapping virtual threads in a fixed-size pool "to be safe," carried over from
platform-thread habits. The safety pooling gave you there was capping *concurrent OS threads*; a
fixed-size virtual-thread pool caps concurrency for no reason and reintroduces the queueing and
starvation failure modes virtual threads were adopted to remove.

**Interview:** Don't pool them — creation is cheap enough that pooling only adds capacity limits
and stale reuse with no offsetting benefit; use one virtual thread per task via
`Executors.newVirtualThreadPerTaskExecutor()`.

### 5.1.85 "Do virtual threads help CPU-bound work?"

Say this: no, not directly, and saying otherwise is one of the fastest ways to reveal you don't
have the mechanism model. Virtual threads solve the *blocking* problem — they let a program hold
open more concurrent blocked operations than it has OS threads, because a blocked virtual thread
releases its carrier. A CPU-bound task — say, computing risk scores over a batch of 2.8M stake
records with no I/O in the loop — is never blocked; it's runnable the entire time it's executing.
Running it on a virtual thread doesn't make the CPU-bound work finish faster, because the
bottleneck was never "an OS thread is idle waiting for something" — it was always "the CPU is
saturated doing arithmetic." The number of virtual threads you spin up for CPU-bound work is still
ultimately bounded by the number of carrier threads actually able to run code simultaneously, which
is bounded by core count, same as platform threads. If anything, misapplying virtual threads to a
CPU-bound workload can make things *worse*: the scheduler's default parallelism equals
`availableProcessors()`, so flooding it with more CPU-bound virtual-thread tasks than carriers just
queues them behind each other on the same small pool that your platform-thread `ForkJoinPool
.commonPool()` — used by parallel streams — is *also* competing for cycles on, with no priority
distinction between the two.

**Insight:** the diagnostic question that cuts through this every time is "does this task ever
block?" If the honest answer is "no, it's pure computation," virtual threads are the wrong tool —
reach for a bounded platform-thread pool sized to core count, or a parallel stream, both of which
are explicitly designed around CPU-bound decomposition (see 5.1.95's ForkJoinPool material on
`LEAF_TARGET`).

**Interview:** No — virtual threads only help when a task blocks; CPU-bound work has no idle time
to reclaim, so it's still bounded by core count regardless of how many virtual threads you launch.

### 5.1.86 "You removed the thread pool. What did you also remove?"

Say this: swapping a bounded platform-thread pool for `Executors
.newVirtualThreadPerTaskExecutor()` removes the pool's **backpressure**, not just its thread-count
limit. A bounded pool of, say, 200 platform threads processing incoming stake reservations was
doing two jobs at once: running the work, *and* implicitly capping how much concurrent work the
system would accept — request 201 waits in the queue (or gets rejected) instead of proceeding.
Delete that pool in favor of one virtual thread per task and every incoming reservation gets a
thread immediately; there's no queue depth throttling how much concurrently-in-flight work exists.
If the *downstream* dependency — the Quiz Engine, the ledger's database connection pool, the PSP —
can't actually sustain unbounded concurrent calls, you've traded "requests queue safely in the
thread pool" for "requests all proceed simultaneously and the downstream falls over," which is
often a worse failure mode because it fails all of them roughly at once instead of degrading
gracefully. The pool's identity-based coupling disappears too: code that assumed "there are at
most N of these running, so I can safely have N pre-allocated buffers/connections/permits" loses
that invariant, because virtual threads don't cap anything on their own.

The fix is to reintroduce backpressure **explicitly**, at the actual constrained resource, rather
than implicitly via the thread count: a `Semaphore` sized to what the Quiz Engine can sustain, a
bounded connection pool the ledger writes go through (HikariCP's own pool still caps *that*), or an
explicit rate limiter in front of the PSP call. None of that is virtual-thread-specific machinery —
it's the same backpressure primitives that existed before Loom — the point is that removing the
thread pool removed an *implicit* one, and it has to be replaced with an *explicit* one wherever the
implicit limit was actually load-bearing.

```java
// Explicit backpressure replacing the pool's implicit cap on concurrent Quiz Engine calls
private final java.util.concurrent.Semaphore quizEngineConcurrency = new java.util.concurrent.Semaphore(200);

void reserveStake(String roundId, java.math.BigDecimal stake) throws InterruptedException {
    quizEngineConcurrency.acquire();
    try {
        quizEngineClient.reserveStake(roundId, stake);   // now on a virtual thread, still capped downstream
    } finally {
        quizEngineConcurrency.release();
    }
}
```

**Interview:** You removed the pool's implicit backpressure — the thread count was quietly
capping concurrent downstream calls — and that cap has to be reintroduced explicitly (a semaphore,
a bounded connection pool, a rate limiter) or the downstream dependency absorbs unbounded
concurrency instead.

### 5.1.87 "What breaks in a Spring Boot app when you turn virtual threads on?"

Say this: turning on `spring.threads.virtual.enabled=true` swaps the request-handling executor to
virtual threads, and the breakage clusters around three things that assumed platform-thread
semantics. First, **`ThreadLocal`-heavy code that assumed a small, bounded number of threads** — a
connection-per-thread cache, or a security-context holder implemented as a plain `ThreadLocal` with
a large or expensive-to-create value — now gets one fresh instance per virtual thread instead of
per pooled platform thread, and if there are tens of thousands of virtual threads instead of two
hundred pooled ones, that pattern's memory and setup cost multiplies accordingly (5.1.89 covers the
mechanism). Second, **`synchronized`-guarded code on the request path** now risks pinning
(5.1.82) — a legacy library, a synchronized cache, a JDBC driver like the `CardPayments` example
that predates virtual threads, all become carrier-occupying liabilities they weren't before, because
under the old platform-thread model pinning wasn't even a concept. Third, **connection pools and
other bounded resources sized for platform-thread concurrency levels become the bottleneck** — a
HikariCP pool sized to "200 platform threads, so 200 connections is enough" now faces potentially
tens of thousands of concurrent virtual threads all wanting a connection at once, and the pool
itself, unmodified, is now the queueing point that used to be the thread pool (this is 5.1.86's
backpressure point, showing up specifically in the Spring/HikariCP shape). None of these are
Spring-specific bugs — they're the same three underlying mechanisms (`ThreadLocal` cost, pinning,
implicit backpressure loss) surfacing through Spring's request-handling path, which is exactly why
Spring gated it behind an explicit property instead of defaulting it on.

**Pitfall:** flipping `spring.threads.virtual.enabled=true` and assuming it's purely additive
throughput. Audit for `synchronized` on the request path, oversized or expensive `ThreadLocal`
usage, and connection-pool sizing before enabling it — all three assumptions Spring's blocking
Tomcat/platform-thread model let you get away with silently break their cost model under virtual
threads.

**Interview:** `synchronized` blocks start pinning, `ThreadLocal` patterns sized for hundreds of
platform threads now run per tens-of-thousands of virtual threads, and connection pools sized for
platform-thread concurrency become the new bottleneck once the implicit thread-count throttle is
gone.

### 5.1.88 "How many virtual threads can you create, and what limits it?"

Say this: there's no fixed JVM-imposed count the way there effectively is for platform threads
(where you hit OS thread-count or memory limits in the low thousands per process). The practical
ceiling for virtual threads is **heap memory for their continuation stacks plus whatever the actual
workload's other resource needs are** — each virtual thread's stack starts small and grows on the
heap as needed, so millions of virtual threads is realistic memory-wise on typical server hardware,
in a way millions of platform threads never was (each platform thread reserves a fixed, much larger
native stack up front). What actually limits you in practice is almost never the virtual thread
count itself — it's the **carrier pool's parallelism**, which caps how many of them can be
*running* simultaneously (not how many can *exist* — a blocked, unmounted virtual thread costs
almost nothing), or a **downstream dependency's own concurrency limit** (the Quiz Engine, the
ledger's connection pool, the PSP's rate limits) that you'd hit long before JVM memory becomes the
constraint. Concretely: QuizStakes could plausibly have 100,000+ virtual threads alive
simultaneously representing 55k peak concurrent client sessions plus in-flight stake operations,
almost all of them unmounted and idle at any instant, riding on a scheduler whose default
parallelism is the 8-core box's **8** — the limiting resource was never "how many virtual threads
can exist," it was "how many of them can be actively running Java code on a carrier at once,"
which tracks core count, not thread count.

**Interview:** No practical fixed count — it's bounded by heap for their stacks, which supports far
more than platform threads ever could; the real limits in practice are carrier-pool parallelism
(how many run at once) and downstream dependency concurrency, not virtual-thread creation itself.

### 5.1.89 "What does `ThreadLocal` cost now?"

Say this: mechanically, `ThreadLocal` costs exactly what it always did **per thread** — a slot in
that thread's `ThreadLocalMap`, populated lazily on first `get()`/`set()`. What changed is the
*multiplier*. A platform-thread-pooled application with 200 request-handling threads has at most
200 `ThreadLocal` instances alive for any given `ThreadLocal` field, because the pool caps the
thread count and the values are naturally reused across many requests handled by the same pooled
thread. Move the same code onto virtual threads and the population of "threads" explodes from 200
to potentially the peak concurrent request count — 55k for QuizStakes at peak — and because virtual
threads are typically one-per-task rather than reused, **each one gets its own fresh
`ThreadLocal` value**, computed or allocated from scratch, with none of the natural reuse pooled
platform threads gave you for free. A `ThreadLocal<StringBuilder>` used as a per-thread scratch
buffer, cheap to keep around 200 times, becomes 55,000 fresh `StringBuilder`s under virtual
threads — not because `ThreadLocal` itself got slower, but because there are vastly more distinct
threads now paying its setup cost individually, and nothing recycles them the way a bounded pool
implicitly did. This is exactly the mechanism problem `ScopedValue` (5.1.93) targets: a
`ThreadLocal` mutates and is inherited (expensively, by copying) into child threads if you use
`InheritableThreadLocal`; a `ScopedValue` is bound once for a well-defined dynamic scope and shared
immutably, which is a far better fit for one-virtual-thread-per-task code that spawns further
virtual threads for sub-tasks.

**Interview:** `ThreadLocal` itself is unchanged; what changed is that virtual threads multiply the
number of distinct threads by orders of magnitude and don't naturally reuse them, so per-thread
setup cost that was amortized across ~200 pooled platform threads now happens per task instead.

### 5.1.90 "What is structured concurrency and what does it guarantee?"

Say this: structured concurrency ties the lifetime of every child task to the lexical scope that
spawned it, the same way structured programming ties a loop's or a block's lifetime to its braces —
you can't have a "forked" subtask that outlives the block that forked it, can't lose track of one,
and can't have the parent return while a child is still silently running. On Java 21 (JEP 453,
preview, requires `--enable-preview`), the API is `StructuredTaskScope`, opened in a
try-with-resources block, with `fork(...)` returning a `Subtask<T>` (not a bare `Future<T>`) for
each child, and `join()` blocking the owner until all forked subtasks complete (or a policy trips)
before the scope's `close()` is reached. What it **guarantees**, concretely: no child task can
outlive its scope — `close()` will not return while any subtask is still running, so a scope going
out of the `try` block is a hard guarantee that nothing it spawned is still executing in the
background afterward; failure propagation is structural, not something you have to manually
`.join()`-and-check on every future — a `ShutdownOnFailure` policy cancels sibling subtasks the
moment one fails, and `join()` surfaces that failure to the owner; and there's a single, visible
place in the code — the scope's block — where "everything this unit of work spawned" lives, instead
of fire-and-forget tasks scattered across an executor with no lexical anchor.

```java
// AssessmentService fans out three independent checks for one application, cancels the rest on first failure
try (var scope = new StructuredTaskScope.ShutdownOnFailure()) {
    StructuredTaskScope.Subtask<DocumentVerdict>  docTask    = scope.fork(() -> documentVerification.verify(applicationId));
    StructuredTaskScope.Subtask<ScreeningVerdict> screenTask = scope.fork(() -> screeningService.screen(applicationId));
    StructuredTaskScope.Subtask<WealthVerdict>    wealthTask = scope.fork(() -> assessmentService.assessWealth(applicationId));

    scope.join();                 // waits for all three, or returns early on first failure
    scope.throwIfFailed();        // rethrows the first failure, having already cancelled the others

    // all three guaranteed complete here — none can still be running past this point
    return new AssessmentOutcome(docTask.get(), screenTask.get(), wealthTask.get());
}
```

**Insight:** the guarantee is really about **cancellation propagating both ways** — the scope
cancels its children if the owner's block exits abnormally, and `ShutdownOnFailure` cancels
siblings if one child fails — which is precisely the thing unstructured "just fire off a
`CompletableFuture` and hope someone joins it later" code has no mechanism for at all.

**Interview:** Structured concurrency scopes a task's children to the block that forked them,
guaranteeing none outlive it, with cancellation propagating in both directions between parent and
siblings — Java 21's `StructuredTaskScope` (preview, JEP 453) is the concrete API.

### 5.1.91 "How is `StructuredTaskScope` different from `CompletableFuture.allOf`?"

| Aspect | `CompletableFuture.allOf` | `StructuredTaskScope` |
|---|---|---|
| Task lifetime | Not scoped — futures can outlive the method that created them, nothing stops that | Structurally bound to the try-with-resources block; `close()` will not return with children still running |
| Cancellation on failure | None built in — `allOf` completes exceptionally, but sibling futures keep running unless you manually cancel each one | `ShutdownOnFailure` cancels remaining subtasks automatically the moment one fails |
| Error surfacing | The combined future holds *a* exception; inspecting which of N futures failed, and getting the others' results, is manual bookkeeping | `join()` + `throwIfFailed()` gives the first failure directly; completed `Subtask`s expose `.get()` for their own results, in-progress/cancelled ones don't |
| Thread identity / debugging | Callbacks can run on arbitrary pool threads picked by whichever executor completed the future, muddying stack traces | Each subtask runs on its own (typically virtual) thread forked directly from the scope — a thread dump shows the real parent/child shape |
| Composability with cancellation | `Future.cancel()` exists but nothing wires it automatically between siblings | Cancellation is structural — cancelling the scope (its owner thread being interrupted, or a `ShutdownOnFailure`/`ShutdownOnSuccess` policy tripping) cancels every open subtask |
| Return semantics | A `CompletableFuture<Void>`; results have to be pulled from the original futures you closed over | Subtasks carry their own typed result; the scope's block reads naturally as "spawn these, wait, use the results" |

The single sentence version: `allOf` composes completion, `StructuredTaskScope` composes
**lifetime and cancellation** — `allOf` will happily tell you all four futures are done (or one
failed) without ever having had the power to stop the other three from continuing to run, whereas a
`StructuredTaskScope` scope is specifically designed so that possibility doesn't exist.

**Interview:** `allOf` only aggregates completion of independently-running futures with no
cancellation coupling between them; `StructuredTaskScope` binds child lifetime to the parent scope
and propagates cancellation structurally in both directions.

### 5.1.92 "Is structured concurrency final? What changed in 25?"

Say this: no, as of Java 21 it is still a **preview** feature — JEP 453, requiring
`--enable-preview` to compile and run, with public constructors on `StructuredTaskScope`, `fork`
returning `Subtask<T>`, and the two built-in policies `ShutdownOnFailure` and `ShutdownOnSuccess`.
Worth naming precisely because it moved packages: at 21 it lives in `java.util.concurrent`, having
moved out of the earlier incubator package, `jdk.incubator.concurrent`, that pre-21 previews used.
It went through further preview iterations after 21 (JEP 480 in Java 23, JEP 499 in Java 24) before
**JEP 505 in Java 25** reshaped the API rather than simply finalizing the 21 shape verbatim: the
**public constructors are replaced by static `open()` factory methods**, and the two named policy
subclasses (`ShutdownOnFailure`/`ShutdownOnSuccess`) are **replaced by a composable `Joiner`**
abstraction — instead of picking one of two hardcoded policies, you supply a `Joiner`
implementation that defines how results and failures across subtasks combine, which generalizes
past the "shutdown on first failure" / "shutdown on first success" binary the 21 preview shipped
with. So the honest answer to "is it final" is: not at 21, and even the eventual shape isn't a
straight-line finalization of what 21 previewed — the API surface changed meaningfully on the way,
which is itself worth saying out loud, because it means code written against the Java 21 preview
API is not forward-compatible with the 25 shape without changes.

**Version behavior:** never present `StructuredTaskScope`'s Java 21 constructor-based API as the
finalized form. If asked "what would this look like once it's stable," the honest answer references
`Joiner` and static factories from JEP 505, explicitly flagged as the Java 25 shape, not 21's.

**Interview:** No — Java 21's `StructuredTaskScope` (JEP 453) is preview, and Java 25's JEP 505
replaces its public constructors with static `open()` factories and its two hardcoded shutdown
policies with a composable `Joiner`, so the API itself changed shape on the way to finalization.

### 5.1.93 "What are scoped values and why not just use `ThreadLocal`?"

Say this: a scoped value (`ScopedValue`, preview in Java 21 under JEP 446) binds an immutable value
for the dynamic extent of a specific block of code — `ScopedValue.where(KEY, value).run(() -> {
...})` — and that binding is visible to everything called from inside that block, including code
running on virtual threads forked from within it, without the value being mutable or requiring
explicit propagation through every method signature. The reason it exists instead of just reusing
`ThreadLocal` is a direct consequence of 5.1.89's cost problem plus a correctness problem
`ThreadLocal` never solved: `ThreadLocal` is **mutable** for the life of the thread — anyone with a
reference to the `ThreadLocal` field can call `.set()` at any point and change what every
subsequent read on that thread sees, which is a real source of bugs (a leaked value from a
previous request handled by a reused platform thread, or code deep in a call stack rebinding a
value the caller didn't expect changed) — and its natural cross-thread propagation mechanism,
`InheritableThreadLocal`, **copies** the value into every child thread at creation time, which is
exactly the wrong cost model for spawning tens of thousands of short-lived virtual-thread subtasks
from a `StructuredTaskScope`. A `ScopedValue` is bound **once**, is **immutable** for its entire
binding, and is **automatically visible** (not copied — shared) to every subtask forked within that
binding's scope, and the binding is guaranteed to unbind cleanly when the `run`/`call` block exits,
which lines up exactly with structured concurrency's own scoping discipline (5.1.90). In QuizStakes
terms: an `ApplicationId` or a request-scoped `IdempotencyKey` that every fork inside
`AssessmentService`'s `StructuredTaskScope` (document verification, screening, wealth check) needs
to read, but that none of them should be able to accidentally reassign for the others, is exactly
the shape `ScopedValue` targets and `ThreadLocal` doesn't.

```java
static final ScopedValue<String> APPLICATION_ID = ScopedValue.newInstance();

void assess(String applicationId) throws Exception {
    ScopedValue.where(APPLICATION_ID, applicationId).run(() -> {
        try (var scope = new StructuredTaskScope.ShutdownOnFailure()) {
            scope.fork(() -> documentVerification.verify(APPLICATION_ID.get()));   // reads the bound value
            scope.fork(() -> screeningService.screen(APPLICATION_ID.get()));       // same binding, no copy, no re-threading it through parameters
            scope.join().throwIfFailed();
        }
    });
}
```

**Interview:** `ScopedValue` is an immutable, one-shot binding for a well-defined dynamic scope,
automatically visible to forked subtasks without copying — it fixes `ThreadLocal`'s mutability
(anyone can `.set()` it mid-flight) and its expensive per-child-thread copy semantics under
`InheritableThreadLocal`, both of which are the wrong shape for structured, virtual-thread-heavy
code.

### 5.1.94 "What are sequenced collections and which types got them?"

Say this: sequenced collections (JEP 431, Java 21) retrofit a common contract — `SequencedCollection`,
`SequencedSet`, `SequencedMap` — onto every collection type that already had a well-defined
encounter order but lacked a uniform API for it. Before 21, "get the first element" meant
`list.get(0)` on a `List`, `deque.peekFirst()` on a `Deque`, `.iterator().next()` for a
`LinkedHashSet`, and there was no first-class way to get the *last* element of a `LinkedHashMap` at
all without iterating the whole thing — three different types with a real, meaningful order, three
incompatible partial APIs. `SequencedCollection` adds `getFirst()`, `getLast()`, `addFirst(e)`,
`addLast(e)`, `removeFirst()`, `removeLast()`, and `reversed()` — a view showing the same elements
in reverse encounter order, cheaply, without copying. `SequencedSet` is a `SequencedCollection`
that's also a `Set`; `SequencedMap` adds the map-shaped equivalents — `firstEntry()`, `lastEntry()`,
`putFirst(k,v)`, `putLast(k,v)`, `reversed()` — a reversed-order view of the map itself.

| Type | Implements | What it gained |
|---|---|---|
| `List` (all implementations) | `SequencedCollection` | `getFirst()`/`getLast()`/`reversed()` replace `get(0)`/`get(size()-1)`/manual reverse-copy |
| `Deque` (`ArrayDeque`, `LinkedList`) | `SequencedCollection` | Existing `peekFirst`/`peekLast`-style methods now sit under one shared contract with `List` |
| `LinkedHashSet` | `SequencedSet` | First uniform ordered-first/last API a hash-based set ever had |
| `LinkedHashMap` | `SequencedMap` | First-class `firstEntry()`/`lastEntry()`/`reversed()` where before you needed the internal access-order flag and manual iteration |
| `TreeMap`, `TreeSet` | `SequencedMap`/`SequencedSet` | Uniform API alongside their existing `first()`/`last()`, now interoperable with the shared contract |

```java
// A LinkedHashMap tracking the most recent ledger entries per client, oldest-first insertion order
LinkedHashMap<String, java.math.BigDecimal> recentSettlements = new LinkedHashMap<>();
recentSettlements.put("R-48213", new java.math.BigDecimal("3.33"));
recentSettlements.put("R-48214", new java.math.BigDecimal("1.10"));

var mostRecent = recentSettlements.lastEntry();          // no manual iteration needed, pre-21 this required tracking it yourself
var oldestFirst = recentSettlements.sequencedKeySet();     // sequenced view
var newestFirst = recentSettlements.reversed();            // a live, reversed-order view — not a copy
```

**Pitfall:** assuming `reversed()` returns a copy. It returns a **view** — mutations through the
reversed view write back to the original collection in reverse-mapped position, and mutating the
original is visible through the view. Treating it like a snapshot and mutating both independently
produces surprising cross-talk.

**Interview:** JEP 431 gives `List`, `Deque`, `LinkedHashSet` and `LinkedHashMap` (plus
`TreeMap`/`TreeSet`) a shared `getFirst`/`getLast`/`reversed()`-shaped contract, replacing a decade
of inconsistent, type-specific ways to ask "what's first" or "what's last."

### 5.1.95 "What is the single most useful thing added between Java 8 and 21, and why?"

Say this: for a backend engineer running services under real production load, it's **virtual
threads** — not because pattern matching or records aren't genuinely good language ergonomics, but
because virtual threads change what's *architecturally possible* rather than just what's pleasant
to write. Every other Java-8-to-21 feature — records, sealed types, pattern matching, text blocks,
sequenced collections — makes the code you'd already write cleaner or safer to write. Virtual
threads let you delete an entire category of code and the reasoning that went with it: reactive
pipelines, `CompletableFuture` chains threaded through unrelated business logic purely to avoid
blocking a scarce platform thread, callback-based async I/O adopted not because the domain wanted
it but because thread-per-request stopped scaling once you had 55k concurrent QuizStakes client
sessions to serve off a fixed-size thread pool. Thread-per-request, ordinary blocking JDBC calls,
ordinary try/catch — the style every engineer already thinks in — becomes viable again at the
concurrency levels that used to force a reactive rewrite, and structured concurrency (5.1.90) gives
that same straightforward style a correct way to fan out and join concurrent work, closing the gap
that used to be reactive-only territory (parallel calls to `DocumentVerification`, `ScreeningService`
and the wealth check, joined with real cancellation semantics, in code that reads top to bottom).

That said, the honest caveat belongs in the answer too: virtual threads only pay off for I/O-bound,
blocking-heavy workloads (5.1.85) — a CPU-bound batch job over QuizStakes's 2.8M daily stake
records still lives and dies by `ForkJoinPool` parallel decomposition, which is unrelated
machinery. Worth grounding in real numbers to show you're not hand-waving: `ForkJoinPool
.commonPool()`'s default parallelism is `availableProcessors() - 1`, but the thread that
**submits** the terminal operation participates in the computation too, so the effective width
equals the full core count, not one less — say both halves together or the number's wrong. On the
consistent 8-core box these notes use: commonPool parallelism = **7**, effective width = **8**,
`LEAF_TARGET` (`AbstractTask`, verified at the `jdk-21+35` tag) = `getCommonPoolParallelism() << 2`
= `7 << 2` = **28** — the javadoc's own words are "we over-partition, currently to approximately
four tasks per processor" — and `suggestTargetSize` does **floored integer division clamped to a
minimum of 1**, not "rounded up" as it's sometimes described:

```java
public static long suggestTargetSize(long sizeEstimate) {
    long est = sizeEstimate / getLeafTarget();
    return est > 0L ? est : 1L;
}
```

Over 2,800,000 stake reservations: `2_800_000 / 28` = **100,000** exactly, giving **28 leaf tasks**
of 100,000 elements each for a parallel stream over that dataset. That's the CPU-bound machinery,
untouched by virtual threads; the I/O-bound majority of QuizStakes's traffic — the 1,200
reservations/sec hitting the Quiz Engine, the 3,400 settlements/sec burst, the PSP calls at 240ms
p50 — is exactly where virtual threads' unmount-on-block mechanism (5.1.81) turns "one OS thread
per in-flight request" into "a request occupies a carrier only while it's actually computing,"
which is the answer to why virtual threads are the single highest-leverage addition for a service
that spends most of its time waiting on something else.

**Interview:** Virtual threads — because they don't just improve code quality, they remove the
architectural forcing function (thread-per-request doesn't scale) that pushed I/O-bound services
toward reactive programming in the first place, while CPU-bound work still runs on the unrelated
`ForkJoinPool` machinery virtual threads were never meant to replace.

---

## Pitfalls

### Assuming `default` on a pattern switch catches a `null` selector

**Wrong**

```java
static String label(Object o) {
    return switch (o) {
        case DocumentVerdict d -> "doc:" + d.outcome();
        default -> "other";     // looks like it should catch null too
    };
}
// label(null) -> throws NullPointerException, does NOT return "other"
```

**Right**

```java
static String label(Object o) {
    return switch (o) {
        case null -> "no verdict yet";      // explicit — this is what actually catches null
        case DocumentVerdict d -> "doc:" + d.outcome();
        default -> "other";
    };
}
```

**Why people believe it:** `default` reads as "everything else," and in a classic `switch` on a
boxed type, `null` throws before the switch is even entered, so there's never been a `default`
that needed to catch it — the pattern-switch behavior (an explicit `case null` label, distinct from
`default`) is a genuinely new rule, not an extension of old behavior, and it's easy to assume the
old "switch on `null` always throws" folklore still applies universally.

### Placing an unguarded case before the guarded case it should carve an exception out of

**Wrong**

```java
static String status(Verdict v) {
    return switch (v) {
        case ScreeningVerdict s -> "screening: " + s.outcome();
        case ScreeningVerdict s when s.outcome().equals("AA-599") -> "prohibited";  // compile error: dominated
        default -> "other";
    };
}
```

**Right**

```java
static String status(Verdict v) {
    return switch (v) {
        case ScreeningVerdict s when s.outcome().equals("AA-599") -> "prohibited";  // guarded case first
        case ScreeningVerdict s -> "screening: " + s.outcome();
        default -> "other";
    };
}
```

**Why people believe it:** it reads naturally to put "the common case" first and "the special case"
second, the way you'd order `if`/`else if` chains in prose — but dominance analysis ignores guards
entirely, so the unguarded pattern placed first already covers every value the guarded case could
ever match, making the guarded case permanently unreachable and a compile error rather than a
silent bug.

### Treating `-Djdk.virtualThreadScheduler.maxPoolSize` as an independent knob

**Wrong**

```
-Djdk.virtualThreadScheduler.parallelism=8 -Djdk.virtualThreadScheduler.maxPoolSize=4
```

Assuming this leaves `parallelism=8` untouched and just narrows how far the pool can burst above
it — it doesn't.

**Right**

Read the source's own logic before setting `maxPoolSize` below the intended parallelism:

```java
if (maxPoolSizeValue != null) {
    maxPoolSize = Integer.parseInt(maxPoolSizeValue);
    parallelism = Integer.min(parallelism, maxPoolSize);   // parallelism is silently clamped down too
}
```

Setting `maxPoolSize=4` with `parallelism=8` requested clamps the effective parallelism down to
**4** as well — both numbers move together whenever `maxPoolSize` is the smaller of the two.

**Why people believe it:** `maxPoolSize` and `parallelism` sound like they describe independent
axes — "how many threads normally run" versus "how many it can grow to under load" — and in most
other pool APIs (`ThreadPoolExecutor`'s core-vs-max size) those really are independent. The virtual
thread scheduler's `ForkJoinPool` constructor doesn't allow `maxPoolSize` below `parallelism`, so
the source clamps one to protect the invariant, and that clamp is easy to miss unless you've read
the actual `createDefaultScheduler()` body.

---

## Cheat sheet

| Question area | One-line answer |
|---|---|
| Sealed + switch | Closed permitted-subtype list lets the compiler prove exhaustiveness with no `default` |
| Flow scoping | Pattern variable scope follows definite-assignment proof, not braces |
| `null` in pattern switch | NPE unless an explicit `case null` label is present; `default` never catches `null` |
| `MatchException` | Runtime admission that a compile-time-exhaustive switch no longer is (binary skew); replaced `IncompatibleClassChangeError` at 21 |
| Dominance | Pattern-shape-only; guards never rescue a dominated case — guarded case must come first |
| Record patterns | Deconstruct nested records inline, unlimited nesting depth, `var` per component |
| Pattern switch compilation | `invokedynamic` → `SwitchBootstraps.typeSwitch` → `tableswitch`; guard failure loops back with an advanced index |
| Switch statement vs expression | Expression: value-producing, exhaustive, arrow never falls through; statement: neither |
| `yield` vs `return` | `yield` supplies the switch's value; `return` exits the whole method |
| `$SwitchMap` | Ordinal→case-index cache, only for enums compiled separately from the switch site; not used by pattern/sealed switches |
| Text block indentation | Common leading whitespace across content lines + closing delimiter, stripped from all |
| `\s` | Escaped literal space that survives automatic trailing-whitespace stripping |
| Text block interning | Constant text blocks are interned exactly like string literals |
| String interpolation | No stable form in 21 — string templates (JEP 430) were preview, then withdrawn |
| Virtual thread scheduler | `ForkJoinPool`, parallelism = cores, `maxPoolSize` = `max(parallelism, 256)` (floor, not flat), `minRunnable` = `max(parallelism/2, 1)`, FIFO |
| Mount/unmount | `Continuation` freeze/thaw off a carrier on a cooperating block; carrier only busy while runnable |
| Pinning | Blocking inside `synchronized` (21) or a native frame (every version) keeps the carrier occupied; JEP 491 (Java 24) fixes the `synchronized` case only |
| Detect pinning | `jdk.VirtualThreadPinned` JFR event (production); `-Djdk.tracePinnedThreads=full` (dev repro) |
| Pool virtual threads? | No — creation is cheap, pooling only reintroduces capacity limits |
| CPU-bound work | No help — no idle time to reclaim; still bounded by core count via `ForkJoinPool` |
| Removing the thread pool | Also removes its implicit backpressure — replace with an explicit semaphore/pool/limiter |
| Spring Boot virtual threads | Audits: `synchronized` on request path (pinning), oversized `ThreadLocal` (multiplied per task), connection pool sizing (new bottleneck) |
| How many virtual threads | No fixed count — heap-bound; real limits are carrier parallelism and downstream concurrency |
| `ThreadLocal` cost now | Same per-thread cost, vastly more threads, no pooled reuse — multiplies, doesn't change per-unit |
| Structured concurrency guarantee | No child outlives its scope; cancellation propagates both directions |
| `StructuredTaskScope` vs `allOf` | `allOf` composes completion only; `StructuredTaskScope` composes lifetime + cancellation |
| Structured concurrency status | Preview at 21 (JEP 453); JEP 505 (Java 25) replaces constructors with `open()` and policies with `Joiner` |
| Scoped values vs `ThreadLocal` | Immutable, one-shot binding, shared (not copied) into forked subtasks; preview JEP 446 |
| Sequenced collections | `getFirst`/`getLast`/`reversed()` contract on `List`, `Deque`, `LinkedHashSet`, `LinkedHashMap` (JEP 431); `reversed()` is a live view |
| Most useful 8→21 addition | Virtual threads — removes the architectural forcing function toward reactive programming for I/O-bound services |

---

## Self-test

**Q1.** A pattern switch over `Verdict` has cases for `DocumentVerdict` and `ScreeningVerdict` and
a `default`, no `case null`. What happens when it's invoked with `null`, and why is that not the
same as before pattern matching for switch existed?

<details><summary>Answer</summary>

It throws `NullPointerException`. Mechanically the switch performs an explicit null-check
(`Objects.requireNonNull`-shaped) before ever consulting the `SwitchBootstraps.typeSwitch`
bootstrap, and `default` is not treated as matching `null` — only an explicit `case null` label (or
`case null, default`) does. This is a genuinely new rule introduced with pattern matching for
switch, not a restatement of classic switch behavior: a classic `switch` on a boxed type or enum
also throws `NullPointerException` on `null`, but it had no concept of a `case null` label at all —
there was no way to opt into handling `null` inside the switch itself, you had to null-check before
entering it. Pattern switch keeps the "throws by default" behavior but adds the option to route
`null` explicitly, which is the part worth naming as new.

</details>

**Q2.** Two developers argue about whether `case String s -> ...` followed later by
`case String s when s.length() == 0 -> ...` in the same switch will compile. Who's right, and why?

<details><summary>Answer</summary>

It will not compile — the second developer arguing it fails is right. Dominance analysis ignores
guards entirely and looks only at pattern shape: the first case, `String s` with no guard, matches
every possible `String`, including empty ones. The compiler doesn't ask "does the later case's
guard carve out a reachable subset" — guards play no role in the dominance check — so the second
case is judged dominated and unreachable purely by pattern shape, and the compiler rejects it with
a dominance error. Swapping the order (guarded case first) fixes it.

</details>

**Q3.** Why does the virtual thread scheduler's `maxPoolSize` default formula matter more on a
128-core machine than on an 8-core machine?

<details><summary>Answer</summary>

The default is `Integer.max(parallelism, 256)`. On an 8-core box, `max(8, 256)` = 256 — the 256
floor dominates, and "the default is 256" happens to describe reality. On a 128-core box,
`max(128, 256)` is still 256 — the floor still dominates, parallelism hasn't caught up yet. It only
stops dominating once `availableProcessors()` exceeds 256, at which point `maxPoolSize` tracks the
actual core count instead of the flat floor. The point of the question is that "the default is
256" is a claim that happens to be true below 257 cores and is simply wrong above it — the correct
mental model is "256 is a floor, not a flat default," which matters increasingly as core counts on
real hardware climb toward and past that number.

</details>

**Q4.** A `synchronized` block in a legacy JDBC driver blocks a virtual thread on socket I/O. On
Java 21, does the carrier get released? On Java 24?

<details><summary>Answer</summary>

On Java 21, no — the virtual thread pins its carrier for the duration of the block, because the
JVM's object-monitor implementation isn't continuation-aware yet: holding a `synchronized` monitor
while blocking prevents the continuation from freezing. On Java 24, JEP 491 makes object monitors
continuation-aware, so the same code no longer pins on that account — the carrier is released
normally. The caveat that survives both versions: if the block were instead happening inside a
native (JNI/foreign-function) frame rather than a `synchronized` block, it would pin on *both* 21
and 24, because native-frame pinning is a structural limit of what a continuation can capture, not
something JEP 491 touches.

</details>

**Q5.** `Collectors.summingInt` and `Collectors.summingLong` are sometimes both described as
"accumulate into a `long[]`, so they never overflow." Is that accurate?

<details><summary>Answer</summary>

No, and it's only half-right for one of the two. Verified against `Collectors` at the `jdk-21+35`
tag: `summingInt`'s accumulator is `new int[1]` — the running sum is held as an `int` the entire
time, so it has exactly the silent-overflow trap `IntStream.sum()` has. `summingLong`'s accumulator
genuinely is `new long[1]`. Summing 1,000,000,000 three times (3,000,000,000 total, which overflows
a 32-bit `int`) demonstrates it directly: `summingInt` produces -1294967296 (wrapped), `summingLong`
produces the correct 3000000000. `averagingInt` is the one that's actually always safe regardless —
it accumulates into `long[2]` (sum, count) even though it's summing `int`-typed elements — which is
the detail that gets conflated with `summingInt` if you don't check each collector's accumulator
type individually.

</details>

**Q6.** Why is `StructuredTaskScope`'s `fork()` returning a `Subtask<T>` instead of a
`Future<T>` a meaningful design choice, not just a naming difference?

<details><summary>Answer</summary>

A bare `Future<T>` carries no structural relationship to the scope that created it — nothing stops
you from stashing it somewhere and reading it long after the scope has closed, which is exactly the
unstructured-lifetime problem `StructuredTaskScope` exists to prevent. `Subtask<T>` is scoped to
its owning `StructuredTaskScope`: calling `.get()` on it is only meaningful, and only guaranteed
consistent, after `join()` has returned inside that scope's still-open try-with-resources block. The
type itself encodes "this result belongs to a task whose lifetime is bounded by this specific
scope," which a general-purpose `Future<T>` — designed to be freely passed around and outlive
whatever created it — deliberately does not encode.

</details>

**Q7.** A team asks why they can't just wrap `StructuredTaskScope` usage in a reusable pooled
utility so they don't have to write the try-with-resources block every time. What's the problem
with that plan?

<details><summary>Answer</summary>

Pooling or reusing a `StructuredTaskScope` instance across multiple logical units of work breaks
the entire guarantee it exists to provide. The scope's lifetime *is* the unit of structure — its
`close()` is what proves no forked subtask is still running, and that proof is only meaningful once
per scope instance, tied to one try-with-resources block. Reusing an instance across calls either
requires re-opening it (at which point you've just re-created a new scope with extra ceremony, no
actual reuse), or risks a second call's subtasks getting tangled with an earlier call's still-
finishing cleanup — exactly the kind of cross-task lifetime confusion structured concurrency was
built to make impossible. The right amount of "reuse" is a helper method that opens a fresh scope
each call, not a pooled scope object.

</details>

**Q8.** What's the mechanical reason a `ScopedValue` is a better fit than an
`InheritableThreadLocal` for values that need to be visible inside a `StructuredTaskScope`'s forked
subtasks?

<details><summary>Answer</summary>

`InheritableThreadLocal` propagates to a child thread by **copying** the value at the moment the
child thread is created — for a `StructuredTaskScope` forking, say, three subtasks off one virtual
thread, that's three separate copy operations, and it happens fresh every single fork, at whatever
concurrency the workload runs at (55k peak concurrent sessions' worth of forks, if this were request
-scoped). A `ScopedValue` binding is established once via `ScopedValue.where(...).run(...)` and is
simply *visible*, immutably, to any code executing within that dynamic scope, including forked
subtasks — no copy per fork, and no possibility of a subtask independently mutating what a sibling
sees, because `ScopedValue` offers no `.set()` at all once bound. The cost difference (copy-per-
child vs. shared-immutable-binding) and the correctness difference (mutable vs. immutable) are both
mechanical consequences of how each one is actually implemented, not just API taste.

</details>

**Q9.** `list.reversed()` on a `List` implementing `SequencedCollection` — is the result safe to
hand to another thread while the original list is still being mutated?

<details><summary>Answer</summary>

No — `reversed()` returns a **live view**, not a copy or a snapshot. It shows the same underlying
elements in reverse encounter order, and mutations to the original list are visible through the
view (and vice versa, for mutable views). Handing a `reversed()` view to another thread while the
original list is concurrently mutated has exactly the same thread-safety hazards as sharing the
original list itself — `SequencedCollection` didn't add any synchronization, it added a different
way of looking at the same backing structure. If independent-snapshot semantics are needed, an
explicit copy (`new ArrayList<>(list.reversed())`, or equivalent) is required, the same as it always
was for any other collection view.

</details>

**Q10.** Why does the `$SwitchMap` synthetic class wrap each ordinal lookup in its own
`try { ... } catch (NoSuchFieldError e) {}` rather than one try/catch around the whole static
initializer?

<details><summary>Answer</summary>

A single try/catch around the whole initializer would mean one missing or renamed enum constant
poisons the entire map — the moment the first `NoSuchFieldError` is thrown, the catch block would
be entered and every subsequent constant's slot would silently never get populated, even for
constants that are perfectly fine. Wrapping each constant's lookup individually means a single
stale or removed constant leaves only *that* constant's slot at its default value (`0`), while
every other constant's mapping is still correctly populated. It's a fine-grained degrade-gracefully
strategy specifically because the failure mode being guarded against — one enum constant changing
across separate compilation — is expected to be localized to that one constant, not systemic.

</details>

## Deferred

None.

## Open questions

- **Unverified:** the exact JFR field/schema details of `jdk.VirtualThreadPinned` (e.g. whether the
  event payload distinguishes a `synchronized`-caused pin from a native-frame-caused pin in a
  structured field versus only in the free-text stack trace) were described from the documented
  behavior of the event and the `-Djdk.tracePinnedThreads` flag rather than from inspecting a
  captured JFR recording's raw event schema on this machine. Settling it would mean capturing an
  actual `jdk.VirtualThreadPinned` event from a running pinned-thread repro and inspecting its
  fields with `jfr print --events jdk.VirtualThreadPinned`.
- **Unverified:** `ScopedValue`'s exact Java 21 preview API surface (`ScopedValue.newInstance()`,
  `.where(...).run(...)`/`.call(...)`) was drawn from JEP 446's published API shape rather than
  compiled and run on this machine, since `ScopedValue` requires `--enable-preview` and this
  environment's `javac`/`java` are version 25, where the preview API has since evolved past its
  Java 21 shape. Settling it would mean compiling the JEP 446 example against an actual JDK 21
  distribution with `--enable-preview --release 21`.

---

**Leaves covered:** 5.1.65–5.1.95 (31 leaves)
**Leaves deferred:** none
**Diagrams included:** none
**Target version:** Java 21 LTS
**Lines:** 1504
