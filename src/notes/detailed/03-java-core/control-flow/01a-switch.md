# 03 Java Core — The classic switch statement and fall-through — BASICS (§1.8, 1.8.6, 1.8.7)

**Target version: Java 21 LTS.** | **Part 1 of 5** | [Index](../00-index.md)
Previous: [Control flow: branches, loops and abrupt completion](01-basics.md) · Next: [switch on a String, on an enum, and on null](01b-string-and-enum-switch.md)

`switch` is the construct where the gap between source and bytecode is widest, and
the classic colon form is where the trouble starts. It is not a set of exclusive
branches — it is one block with labelled entry points and no walls between them.
This part covers that form end to end: the permitted selector types, where
`default` may sit, and the missing-`break` bug class, against `javac` output
captured from a real JDK 21.

Branching, looping, labels and abrupt completion are in
[Control flow: branches, loops and abrupt completion](01-basics.md). The compiled
forms of a `String` and an enum switch, and `null` selectors, are in
[switch on a String, on an enum, and on null](01b-string-and-enum-switch.md); the
arrow form, `switch` expressions and Java 21 pattern matching are in
[switch expressions and pattern matching](01c-switch-expressions-and-patterns.md).

---

## 6. The classic `switch` statement (1.8.6)

**Concept.** A jump table with a doorway per case and no walls between them. You
enter at the matching label and keep walking through every subsequent label until
something makes you leave. Every other language's `switch` is a set of exclusive
branches; Java's colon-form `switch` is one block with entry points.

**Why it exists.** C's `switch` compiled to a single indexed jump, which was
dramatically cheaper than a chain of comparisons on 1970s hardware. Java inherited
the syntax verbatim, fall-through included, to keep C programmers productive. The
JVM kept the payoff: two dedicated opcodes, `tableswitch` for dense label sets
(O(1), an array index) and `lookupswitch` for sparse ones (a sorted key table,
O(log n) binary search).

**How it works.** The selector is evaluated once, unboxed if it is a wrapper, and
matched against compile-time constant labels which must be distinct. `default` may
appear anywhere in the block, not only last — it is just another entry point, and
control falls out of it into whatever label follows.

| Selector type | Since | Notes |
|---|---|---|
| `byte`, `short`, `char`, `int` | 1.0 | `long`, `float`, `double`, `boolean` are **not** permitted |
| `Byte`, `Short`, `Character`, `Integer` | 5 | unboxed at the selector; `null` throws NPE (§10) |
| `String` | 7 | compiles to two switches (§8) |
| enum types | 5 | labels are bare constant names; compiles via `$SwitchMap` (§9) |
| `long`, `float`, `double`, `boolean`, any reference type | — | rejected in a *non-pattern* switch |
| any reference type, plus patterns and `case null` | 21 | only in a *pattern* switch (§12) |

Since Java 21 the selector rules split by switch kind. JLS 21 §14.11.1 governs
which selector types a given switch block is compatible with; the traditional
constant-label switch keeps the row set above, while a switch block containing any
pattern or `null` label admits arbitrary reference types.

**Unverified:** the exact verbatim sentence in JLS 21 §14.11.1 enumerating permitted
selector types — JLS 21 restructured the SE 8 wording ("The type of the selector
expression must be char, byte, short, int, Character, Byte, Short, Integer, String,
or an enum type") into the enhanced/non-enhanced split, and I have not read the
current sentence directly. The behaviour in the table is confirmed by compiling each
case on JDK 21.

**Pitfall:** switching on a `long`. `switch (stakeCount)` where `stakeCount` is a
`long` — the 2.8M/day reservation counter — is a compile error, not a silent
narrowing. Symptom: "incompatible types: possible lossy conversion from long to
int". Fix: switch on a derived `int` bucket, or use `if`/`else` ranges; do not cast,
because `(int)` on a value above 2³¹−1 wraps silently.

> The classic `switch` is a single block with constant-labelled entry points, an
> optionally-positioned `default`, and no implicit exit between labels
> (JLS 21 §14.11).

The two compiled forms — the two-stage `hashCode`-then-`equals` shape of a `String`
switch (§8) and the synthetic `$SwitchMap` of an enum switch (§9) — plus what a
`null` selector does (§10) are in
[switch on a String, on an enum, and on null](01b-string-and-enum-switch.md).

---

## 7. Missing `break` is a bug class, not a typo (1.8.7) [TRAP]

**Concept.** Fall-through is opt-out. Every colon-form case that does not end in
`break`, `return`, `throw`, `continue`, or `yield` continues into the next one, and
the compiler is silent by default because fall-through is *sometimes* what you want.

**How it works.** Grouping labels (`case A: case B: doThing(); break;`) is
fall-through used deliberately, and it is common enough that `javac` cannot warn on
all of it. `-Xlint:fallthrough` splits the difference: it warns when a case group
with a non-empty body falls into the next label. Captured on JDK 21:

```
FT.java:6: warning: [fallthrough] possible fall-through into case
            case 2: f = 20; break;
            ^
1 warning
```

Note where the caret points — at the case being *fallen into*, not the one missing
the `break`. The warning is also suppressed by a `// $FALL-THROUGH$` comment in some
toolchains and by `@SuppressWarnings("fallthrough")` on the enclosing method, so a
deliberate fall-through can be documented without losing the check elsewhere.

**Pitfall:** believing the compiler catches a forgotten `break`. It does not, unless
you enable the lint, and most builds do not. Symptom: a deposit is charged a fee
belonging to a later phase, discovered weeks later in reconciliation, because
`case DEP_301:` fell into `case DEP_309:`. Fix, in order of strength: (1) use the
arrow form (§11), which cannot fall through at all; (2) if you must keep the colon
form, add `-Xlint:fallthrough -Werror` to the build; (3) end every case with an
explicit exit even when it is the last one.

**Tradeoff:** `-Werror` on this lint costs you the ability to write intentional
fall-through without an annotation — a real cost in a state machine where three
phases share a suffix of work. The escape hatch is
`@SuppressWarnings("fallthrough")` scoped to that one method, never to the class.

> Colon-form cases fall through unless explicitly terminated; `-Xlint:fallthrough`
> exists because the compiler cannot distinguish deliberate grouping from a
> forgotten `break`.

The arrow form referenced above as fix (1) — the form that cannot fall through at
all — is in
[switch expressions and pattern matching](01c-switch-expressions-and-patterns.md).

---

## Pitfalls

### "A missing `break` is caught by the compiler"

**Wrong**

```java
static int feeMinor(String depositStatus) {
    int fee = 0;
    switch (depositStatus) {
        case "DEP-301": fee = 25;      // no break
        case "DEP-309": fee = 150;     // captured deposits now pay the failed-deposit fee
            break;
        default: fee = 0;
    }
    return fee;
}
// feeMinor("DEP-301") -> 150, not 25. Compiles clean with default javac flags.
```

**Right**

```java
static int feeMinor(String depositStatus) {
    return switch (depositStatus) {
        case "DEP-301" -> 25;
        case "DEP-309" -> 150;
        default -> 0;
    };
}
// feeMinor("DEP-301") -> 25. Arrow arms cannot fall through; there is no break to forget.
```

**Why people believe it:** every other modern language either has no fall-through or
warns loudly, and `javac`'s fall-through check is off unless you pass
`-Xlint:fallthrough`, which most Maven and Gradle defaults do not.

### "A `long` selector just narrows to `int`"

**Wrong**

```java
static int reservationBand(long reservationsToday) {
    switch (reservationsToday) {           // 2.8M/day counter
        case 0: return 0;
        default: return 1;
    }
}
// error: incompatible types: possible lossy conversion from long to int
```

**Right**

```java
static int reservationBand(long reservationsToday) {
    if (reservationsToday == 0L) {
        return 0;
    }
    if (reservationsToday < 1_000_000L) {
        return 1;
    }
    return 2;
}
// Ranges over a long belong in if/else. Casting to int would wrap above 2^31-1.
```

**Why people believe it:** assignment contexts elsewhere in the language perform
widening silently, so the selector feels like it should narrow silently too. It does
not: the permitted non-pattern selector types are `byte`, `short`, `char`, `int`,
their wrappers, `String` and enum types, and `long`/`float`/`double`/`boolean` are
rejected outright rather than converted.

### "`default` must be the last case, so control cannot fall out of it"

**Wrong**

```java
static int retryBudget(String withdrawalStatus) {
    int budget = 0;
    switch (withdrawalStatus) {
        default:                       // legal here, and it falls through
            budget = 3;                // retry counts are capped at 3
        case "DEP-301":
            budget = 0;                // every unknown status also lands here
            break;
        case "AA-700":
            budget = 1;
            break;
    }
    return budget;
}
// retryBudget("WHATEVER") -> 0, not 3. default ran, then fell into "DEP-301".
```

**Right**

```java
static int retryBudget(String withdrawalStatus) {
    int budget = 0;
    switch (withdrawalStatus) {
        case "DEP-301":
            budget = 0;
            break;
        case "AA-700":
            budget = 1;
            break;
        default:
            budget = 3;                // last, and terminated anyway
            break;
    }
    return budget;
}
// retryBudget("WHATEVER") -> 3. Position is a convention; the break is the guarantee.
```

**Why people believe it:** in almost every codebase `default` *is* written last, so
the language rule and the convention are never observed to differ. JLS 21 §14.11
makes `default` an ordinary group in the block: it may appear anywhere, its labels
are not special at runtime beyond "no constant matched", and control falls out of its
body into the next label exactly like any other group.

---

## Cheat sheet

| Thing | Rule |
|---|---|
| classic selector types | `byte`/`short`/`char`/`int` + wrappers, `String` (7), enum (5) |
| never a selector | `long`, `float`, `double`, `boolean` |
| pattern-switch selector | any reference type, once a pattern or `case null` label is present (21) |
| selector evaluation | once, unboxed if a wrapper; labels must be distinct compile-time constants |
| `long` selector | compile error: "incompatible types: possible lossy conversion from long to int" |
| `default` position | anywhere in the block, not only last; control falls out of it too |
| JVM opcodes | `tableswitch` for dense labels (array index), `lookupswitch` for sparse (sorted binary search) |
| fall-through | default in colon form; every non-terminated group continues into the next |
| terminators | `break`, `return`, `throw`, `continue`, `yield` |
| `-Xlint:fallthrough` | warns on a non-empty group falling into the next; caret points at the case fallen *into* |
| grouped labels | `case A: case B: body; break;` — empty groups do not warn |
| suppressing that lint | `@SuppressWarnings("fallthrough")` on the method, never the class |
| strongest fix | the arrow form, which cannot fall through at all (§11) |

---

## Self-test

**Q1.** Which selector types does a non-pattern `switch` accept, and what happens if you hand it the `long` reservation counter?

<details><summary>Answer</summary>

A non-pattern `switch` accepts `byte`, `short`, `char` and `int`; their wrappers
`Byte`, `Short`, `Character` and `Integer`, which are unboxed at the selector and
therefore throw NPE on `null`; `String`, since Java 7; and enum types, since Java 5.
It rejects `long`, `float`, `double`, `boolean` and every other reference type. A
`long` selector is a compile error — "incompatible types: possible lossy conversion
from long to int" — not a silent narrowing, which is the right call: the 2.8M/day
reservation counter would eventually exceed 2³¹−1 and an inserted `(int)` cast would
wrap into a negative band with no diagnostic. The fix is either to derive an `int`
bucket before switching or to express the ranges as `if`/`else`. Since Java 21 the
rules split by switch kind: a switch block containing any pattern label or `case null`
admits arbitrary reference types instead, governed by JLS 21 §14.11.1.

</details>

**Q2.** `-Xlint:fallthrough` fires on your state machine, but one of the fall-throughs is deliberate. What are your options, and what does the warning's caret actually point at?

<details><summary>Answer</summary>

The caret points at the case being *fallen into*, not at the case that is missing the
`break` — captured on JDK 21 as
`FT.java:6: warning: [fallthrough] possible fall-through into case` with the caret
under `case 2: f = 20; break;`. That surprises people who read the warning as
"you forgot a break here". Options, in order of strength. Convert the block to the
arrow form, which cannot fall through at all and so removes the question. If you must
keep the colon form, keep the lint and add `-Werror`, then annotate the one deliberate
site with `@SuppressWarnings("fallthrough")` on the enclosing method — never on the
class, which would blind you to the next accidental one. Some toolchains also honour a
`// $FALL-THROUGH$` comment on the falling case, which documents intent at the exact
line. The residual cost of `-Werror` is real: a state machine where three phases share
a suffix of work now needs an annotation to say so.

</details>

**Q3.** Where may `default` appear in a colon-form `switch`, and what happens to control when the `default` body finishes?

<details><summary>Answer</summary>

Anywhere. `default` is an ordinary group in the block under JLS 21 §14.11 — its only
special property is that it is the entry point chosen when no constant label matched.
It may be written first, in the middle, or last, and its body obeys exactly the same
fall-through rule as every other group: when the last statement of the `default` body
completes normally, control continues into whatever label follows it in source order.
So `default: budget = 3; case "DEP-301": budget = 0; break;` sets `budget` to 3 and
then immediately overwrites it with 0 for every unmatched withdrawal status. The
convention of writing `default` last is what hides this, and the convention is not the
rule. Terminate the `default` body with `break` (or `return`/`throw`) even when it is
last, so that inserting a case below it later cannot change its meaning.

</details>

**Q4.** `javac` has two switch opcodes. Which does it pick, and on what basis?

<details><summary>Answer</summary>

`tableswitch` for a dense set of labels and `lookupswitch` for a sparse one.
`tableswitch` stores a low bound, a high bound and one jump offset per value in the
range, so selecting a target is a single bounds check plus an array index — O(1) — but
its size is proportional to `high - low + 1`, so a label set of 1, 2 and 1_000_000
would emit a million-entry table. `lookupswitch` stores explicit key/offset pairs,
which the JVM specification requires to be sorted ascending by key, and the target is
found by binary search — O(log n) — with size proportional to the number of labels
only. `javac` weighs the two by estimating the space and time cost of each for the
actual label set and picking the cheaper, which is why the four case labels
`AA-610`, `AA-700`, `AA-801` and `DEP-301` mapped to a dense 0/1/2/3 index emit a
`tableswitch` while the same four routed by hash emit a `lookupswitch`. The choice is
an implementation decision of the compiler, not something the source controls.

</details>

**Q5.** Given `case "AA-610": case "AA-700": queueForReview(reservation); break;`, is that fall-through, and will `-Xlint:fallthrough` complain?

<details><summary>Answer</summary>

It is fall-through, and it will not complain. Control entering at `case "AA-610":`
finds an empty group — no statements at all between that label and the next — and
falls straight into `case "AA-700":`, which is how label grouping was expressed in
the colon form for the language's first two decades: sharing a body meant letting one
label fall into another. `-Xlint:fallthrough` is written to permit exactly this: it
warns only when a group with a *non-empty* body falls into the next label, because
that is the shape a forgotten `break` produces. An empty group carries no work that
could be executed twice, so it is unambiguous. Java 14 added a genuine comma list, so
the same thing can now be written `case "AA-610", "AA-700":` in the colon form or
`case "AA-610", "AA-700" ->` in the arrow form, which states the intent directly
instead of relying on fall-through to express it.

</details>

**Q6.** Your build passes `-Xlint:fallthrough -Werror` and one method genuinely needs fall-through. Where does the suppression go, and why not one level up?

<details><summary>Answer</summary>

On the enclosing method: `@SuppressWarnings("fallthrough")` immediately above the
method that contains the deliberate fall-through. The annotation's effect covers the
whole declaration it is attached to and everything lexically inside it, so putting it
on the class silences the check for every switch in the class — including the accidental
missing `break` somebody adds to a different method next quarter, which is the exact
defect the lint exists to catch. Method scope keeps the blast radius to the one block
you have reasoned about. Two refinements are worth knowing. Some toolchains honour a
`// $FALL-THROUGH$` comment on the falling case, which is narrower still because it
documents the intent at the precise line rather than the whole method. And the
strongest option remains not needing the suppression: converting the block to the
arrow form removes fall-through as a possibility, so the lint has nothing to report.

</details>

---

## Open questions

None. The JLS 21 §14.11.1 selector-types wording flagged as unverified in §6 is
tracked as an open question in
[switch on a String, on an enum, and on null](01b-string-and-enum-switch.md).

---

**Leaves covered:** 1.8.6, 1.8.7 (2 leaves)
**Leaves deferred:** none
**Diagrams included:** none
**Target version:** Java 21 LTS
**Lines:** 393
