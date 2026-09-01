# 03 Java Core — Control flow: branches, loops and abrupt completion — BASICS (§1.8, 1.8.1–1.8.5)

**Target version: Java 21 LTS.** | **Part 1 of 5** | [Index](../00-index.md)
Previous: [Numeric promotion, boxing and inference conversions](../primitives-and-conversions/03a-promotion-boxing-and-inference.md) · Next: [The classic switch statement and fall-through](01a-switch.md)

Control flow is the one part of the language where the source you write and the
bytecode that runs diverge sharply. A `switch` on a `String` is two switches. An
enhanced `for` is two entirely different loops depending on what you iterate. A
`while (true)` is a compile error waiting for a statement after it, while an
`if (true)` is not. Everything below is grounded in JLS 21 §14 and in `javap -c`
listings captured from a real JDK 21 `javac` on this machine.

This part covers branching and looping: the dangling-else binding rule, the five
loop forms, the two enhanced-for desugarings, `break`/`continue`/labels, and
abrupt completion as a specified concept. Every form of `switch` is in
[The classic switch statement and fall-through](01a-switch.md) and its two successors;
`assert` and `synchronized` are in
[Assertions and guarded blocks](01d-assertions-and-synchronized.md), and try/finally
and the unreachable-statement rules are in
[try as control flow, and unreachable code](01e-try-and-unreachable-code.md).

---

## 1. `if`/`else` and the dangling-else binding rule (1.8.1)

**Mechanism.** JLS 21 §14.9 splits `if` into two productions: `IfThenStatement`
and `IfThenElseStatement`. The grammar is ambiguous when an `else` follows two
open `if`s, and the spec resolves it by fiat: an `else` binds to the *nearest*
preceding `if` that does not already have one. Indentation is not input to the
compiler.

```java
static String label(int reviewCases, boolean operatorOnShift) {
    String out = "AA-700 REVIEW_QUEUED";
    if (reviewCases > 0)
        if (operatorOnShift)
            out = "AA-711 REVIEW_APPROVED";
    else
        out = "AA-900 DECLINED";   // binds to `if (operatorOnShift)`, not the outer if
    return out;
}
```

Called with `reviewCases == 0` this returns `"AA-700 REVIEW_QUEUED"` — the `else`
never runs, because control never reached the inner `if`. The author's intent
(`reviewCases == 0` means declined) is silently lost.

**Pitfall:** believing the `else` pairs with the `if` it is *aligned* with. Symptom:
a branch that appears dead in coverage reports and a declined-path status code that
is never emitted. Fix: brace every `if` body without exception. Braces are what
make the binding explicit, which is why every house style in a regulated codebase
mandates them — the rule is not about typing, it is about the one construct in Java
whose meaning changes with an invisible token.

> A dangling `else` binds to the innermost `if` that lacks one (JLS 21 §14.9);
> braces are the only way to express any other binding.

---

## 2. The five loop forms (1.8.2)

**Mechanism.** All five are statements, not expressions; none of them produce a
value. `while` tests before the body, `do-while` after (so the body runs at least
once), the three-part `for` owns its init/condition/update in one header, and the
two enhanced forms hide their bookkeeping entirely.

| Form | Test point | Loop variable scope | Iteration count when the sequence is empty | Use it when |
|---|---|---|---|---|
| `while (c) { }` | before body | none declared | 0 | the condition is the whole story (a poll, an expiry sweep) |
| `do { } while (c);` | after body | none declared | 1 | at least one attempt is mandatory (a retry, capped at 3) |
| `for (init; c; upd)` | before body | header-local | 0 | you need the index, or a descending / non-unit stride |
| `for (T t : iterable)` | before body | body-local, effectively final per iteration | 0 | you need the element and nothing else |
| `for (T t : array)` | before body | body-local, effectively final per iteration | 0 | same, over an array |

The `for` header's condition is optional: `for (;;)` is the idiomatic infinite loop
and behaves exactly like `while (true)` for reachability purposes — the unreachable
statement rules that make a trailing statement after such a loop a compile error are
§16 in [try as control flow, and unreachable code](01e-try-and-unreachable-code.md).

**Pitfall:** using an enhanced `for` and then wanting the index. There is no hidden
counter to read. Either switch to a three-part `for` or carry your own `int i`
outside the loop — do not call `list.indexOf(element)` inside the body, which turns
an O(n) sweep of a `PaymentRun`'s 260-transaction batch into O(n²).

> `while`, `do-while`, and the three-part `for` are loop statements over a boolean
> condition; the two enhanced forms are syntactic sugar with no user-visible
> counter (JLS 21 §14.12–§14.14).

---

## 3. Enhanced-for has two different desugarings (1.8.3) [BYTECODE]

**Concept.** One piece of syntax, two unrelated loops. Write `for (x : thing)` and
`javac` looks at the static type of `thing`: if it is an array you get an index
loop with `arraylength`; if it is an `Iterable` you get an iterator loop with
`hasNext`/`next`. Nothing at runtime dispatches between them — the choice is frozen
at compile time.

**Why it exists.** Before Java 5, iterating a `List` meant naming the iterator
yourself, and the single most common bug was updating the wrong loop variable or
calling `next()` twice in one iteration. The enhanced form removes the ability to
name the iterator at all, which removes the bug class. Arrays got the same syntax
for symmetry, but arrays are not `Iterable`, so the compiler needed a second
expansion.

**How it works.** JLS 21 §14.14.2 specifies both expansions literally. For an
`Iterable` selector, with `#i` a compiler-generated name you cannot collide with:

```
for (I #i = Expression.iterator(); #i.hasNext(); ) {
    { TargetType Identifier = (TargetType) #i.next(); }
    Statement
}
```

For an array selector:

```
T[] #a = Expression;
for (int #i = 0; #i < #a.length; #i++) {
    { TargetType Identifier = #a[#i]; }
    Statement
}
```

Two consequences fall straight out. The array form reads `#a.length` **once**, into
a local, before the first iteration — it is not re-read per iteration. And the
`Iterable` form inserts a `checkcast` on every `next()`, because `Iterator.next()`
erases to `Object`.

Captured listings (real, from `javac --release 21` / `javap -c` on JDK 21):

```
static int countTx(java.util.List<java.lang.String>);
     0: iconst_0
     1: istore_1
     2: aload_0
     3: invokeinterface #7,  1   // InterfaceMethod java/util/List.iterator:()Ljava/util/Iterator;
     8: astore_2                 // the hidden #i lives in slot 2
     9: aload_2
    10: invokeinterface #13,  1  // Iterator.hasNext:()Z
    15: ifeq          38         // exit
    18: aload_2
    19: invokeinterface #19,  1  // Iterator.next:()Ljava/lang/Object;
    24: checkcast     #23        // class java/lang/String   <-- erasure tax
    27: astore_3
    28: iload_1
    29: aload_3
    30: invokevirtual #25        // String.length:()I
    33: iadd
    34: istore_1
    35: goto          9
    38: iload_1
    39: ireturn
```

```
static int countEntries(long[]);
     0: iconst_0
     1: istore_1
     2: aload_0
     3: astore_2                 // #a
     4: aload_2
     5: arraylength
     6: istore_3                 // length hoisted ONCE into slot 3
     7: iconst_0
     8: istore        4           // #i
    10: iload         4
    12: iload_3
    13: if_icmpge     34
    16: aload_2
    17: iload         4
    19: laload
    20: lstore        5
    22: iload_1
    23: lload         5
    25: l2i
    26: iadd
    27: istore_1
    28: iinc          4, 1
    31: goto          10
    34: iload_1
    35: ireturn
```

Read the array listing top to bottom: `arraylength` at offset 5 executes once, its
result is stored at 6, and the loop test at 10–13 compares against that *local*.
No `arraylength` appears inside the back edge. The iterator listing has no such
hoist — every iteration pays two interface calls plus a cast.

```java
record Money(java.math.BigDecimal amount, java.util.Currency currency) {}
record AccountId(java.util.UUID value) {}
record WithdrawalTransaction(AccountId account, Money amount, String statusCode) {}
record LedgerEntry(String position, long minorUnits) {}
record PaymentRun(String runId, java.util.List<WithdrawalTransaction> transactions) {}

final class BankWithdrawal {

    // Iterable selector -> iterator loop + checkcast per element
    java.math.BigDecimal batchTotal(PaymentRun run) {
        java.math.BigDecimal total = java.math.BigDecimal.ZERO;
        for (WithdrawalTransaction tx : run.transactions()) {
            if ("BDP-301".equals(tx.statusCode())) {
                total = total.add(tx.amount().amount());
            }
        }
        return total;
    }

    // array selector -> index loop, arraylength hoisted once
    long netMovement(LedgerEntry[] entries) {
        long net = 0L;
        for (LedgerEntry e : entries) {
            net += switch (e.position()) {
                case "CLIENT_CASH_AVAILABLE" -> e.minorUnits();
                case "SUSPENSE", "BANK_SETTLEMENT" -> -e.minorUnits();
                default -> 0L;
            };
        }
        return net;
    }
}
```

**Pitfall:** thinking the enhanced form protects you from concurrent modification.
It does the opposite — it makes the iterator invisible, so when `remove()` is called
on the underlying `List` inside the body you get a `ConcurrentModificationException`
from a `next()` you never wrote. The iterator obtained at loop entry is the same
fail-fast iterator you would have created by hand; its `modCount` snapshot is taken
once, at `iterator()`, and every `next()` compares against it. To remove while
iterating you must name the iterator explicitly and call `Iterator.remove()`, or
build a new list. Fail-fast semantics, `modCount`, and the concurrent collections
that opt out of them are covered in **02 Java collections**.

> The enhanced `for` is compile-time sugar with two expansions selected by the
> static type of the selector: an `Iterator` loop for `Iterable`, an index loop with
> a hoisted `length` for arrays (JLS 21 §14.14.2).

---

## 4. `break`, `continue`, and the only legal use of a label (1.8.4)

**Mechanism.** `break` with no label exits the innermost enclosing `switch`, `for`,
`while`, or `do`. `continue` with no label jumps to the update/test of the innermost
enclosing loop (`continue` is illegal outside a loop — it cannot target a `switch`).
A *label* is an identifier prefixed to a statement, and JLS 21 §14.7 gives it
exactly one purpose: to be named by a `break` or `continue` inside that statement.
Java reserves the keyword `goto` and defines no meaning for it; labels are not a
back door to one, because a labelled `break` can only jump *forward out of* the
labelled statement and a labelled `continue` can only target a labelled *loop*.

```java
enum RestrictionType {
    DEPOSIT_BLOCKED, STAKE_BLOCKED, WITHDRAWAL_BLOCKED, DEPOSIT_LIMITED,
    WITHDRAWAL_HELD, SOURCE_OF_FUNDS_REQUIRED, ALL_BLOCKED, SELF_EXCLUDED,
    COOLING_OFF, DORMANT_FROZEN
}
enum RestrictionSource { SYSTEM_ONBOARDING, SYSTEM_COMPLIANCE, SYSTEM_LIFECYCLE, ADMIN, CLIENT }
record RestrictionKey(RestrictionType type, RestrictionSource source) {}
record Restriction(RestrictionKey key, String state) {}

final class ClientRestrictions {

    /** First blocking (transaction, restriction) pair in the run, or null if the run is clean. */
    static Object[] firstBlocked(PaymentRun run, java.util.Map<AccountId, java.util.List<Restriction>> byAccount) {
        Object[] hit = null;
        scan:
        for (WithdrawalTransaction tx : run.transactions()) {
            java.util.List<Restriction> active = byAccount.getOrDefault(tx.account(), java.util.List.of());
            for (Restriction r : active) {
                if (!"ACTIVE".equals(r.state())) {
                    continue;                 // inner loop only
                }
                switch (r.key().type()) {
                    case WITHDRAWAL_BLOCKED, ALL_BLOCKED, SELF_EXCLUDED -> {
                        hit = new Object[] { tx, r };
                        break scan;           // leaves BOTH loops at once
                    }
                    default -> { }
                }
            }
        }
        return hit;
    }
}
```

**Insight:** an unlabelled `break` inside a `switch` inside a loop breaks the
*`switch`*, not the loop. That is why `break scan;` above needs the label at all —
`break;` there would have continued scanning the remaining restrictions. This is the
single most common reason a labelled `break` is not optional: a `switch` sitting
between you and the loop you meant to exit. Note also that the arrow-form `switch`
arm makes the intent readable; in the colon form the same `break scan;` is easy to
misread as the switch's own `break`. The two `switch` forms are compared in
[The classic switch statement and fall-through](01a-switch.md).

> A label exists solely to be the target of a `break` or `continue` within the
> statement it labels (JLS 21 §14.7); Java has no `goto`.

---

## 5. `return` and abrupt completion as a specified concept (1.8.5)

**Mechanism.** JLS 21 §14.1 defines the vocabulary the rest of chapter 14 is
written in:

> "Every statement has a normal mode of execution in which certain computational
> steps are carried out. [text elided] However, certain events may prevent completion of all
> the steps of a statement as described, in which case the statement is said to
> complete abruptly." — JLS 21 §14.1, *Normal and Abrupt Completion of Statements*

There are exactly four ways to complete abruptly, and every one of them carries a
*reason* that propagates outward until something consumes it:

| Abrupt completion | Reason carried | Consumed by | Escapes the method? |
|---|---|---|---|
| `break` (with or without label) | target statement | the enclosing `switch`/loop, or the labelled statement | no |
| `continue` (with or without label) | target loop | the enclosing (or labelled) loop | no |
| `return` | optional value | the method invocation itself | yes |
| `throw` | a `Throwable` | a matching `catch`, else the caller | yes |

**Insight:** `finally` is the one construct that can *change* the reason. If a
`finally` block itself completes abruptly, its reason replaces the pending one —
which is exactly how a `return` inside `finally` swallows an in-flight exception.
That is the mechanism, and §15 in
[try as control flow, and unreachable code](01e-try-and-unreachable-code.md)
plus `../exceptions/01-basics.md` develop it.

**Interview:** "What does 'abrupt completion' mean?" — Answer: a statement stopped
before its normal steps finished, and it carries a reason (break/continue target,
return value, or thrown value) that propagates until a construct consumes it; the
compiler's reachability analysis (§16, in
[try as control flow, and unreachable code](01e-try-and-unreachable-code.md))
is defined purely in these terms.

> Abrupt completion is a statement ending early with a propagating reason —
> `break`, `continue`, `return`, or `throw` (JLS 21 §14.1).

---

## Pitfalls

### "An `else` pairs with the `if` it is aligned with"

**Wrong**

```java
static String reviewLabel(int reviewCases, boolean operatorOnShift) {
    String out = "AA-610 DOCUMENTS_UPLOADED";
    if (reviewCases > 0)
        if (operatorOnShift)
            out = "AA-801 ACTIVATED";
    else
        out = "AA-700 REVIEW_QUEUED";   // intended: no cases -> queue it
    return out;
}
// reviewLabel(0, true) -> "AA-610 DOCUMENTS_UPLOADED". The else never ran.
```

**Right**

```java
static String reviewLabel(int reviewCases, boolean operatorOnShift) {
    if (reviewCases > 0) {
        if (operatorOnShift) {
            return "AA-801 ACTIVATED";
        }
        return "AA-610 DOCUMENTS_UPLOADED";
    } else {
        return "AA-700 REVIEW_QUEUED";
    }
}
// reviewLabel(0, true) -> "AA-700 REVIEW_QUEUED". Braces make the binding explicit.
```

**Why people believe it:** indentation is how humans parse nesting, and it is the
only cue present in the wrong version. `javac` never reads whitespace; JLS 21 §14.9
binds a dangling `else` to the innermost `if` lacking one, and braces are the only
syntax that can say otherwise.

### "`break` inside a `switch` inside a loop exits the loop"

**Wrong**

```java
static Restriction firstBlocking(java.util.List<Restriction> active) {
    Restriction found = null;
    for (Restriction r : active) {
        switch (r.key().type()) {
            case SELF_EXCLUDED:
            case ALL_BLOCKED:
                found = r;
                break;          // leaves the SWITCH; the loop keeps going
            default:
                break;
        }
    }
    return found;               // ends up as the LAST blocking restriction, not the first
}
```

**Right**

```java
static Restriction firstBlocking(java.util.List<Restriction> active) {
    Restriction found = null;
    scan:
    for (Restriction r : active) {
        switch (r.key().type()) {
            case SELF_EXCLUDED, ALL_BLOCKED -> {
                found = r;
                break scan;     // leaves the labelled loop
            }
            default -> { }
        }
    }
    return found;               // genuinely the first blocking restriction
}
```

**Why people believe it:** in every loop that contains no `switch`, `break` does
exit the loop, so the rule is learned as "break exits the loop". JLS 21 §14.15
targets the innermost enclosing `switch`, `for`, `while` or `do` — and a `switch`
counts. Labelling the loop is the only fix that keeps the `switch`.

### "Reassigning the enhanced-for variable writes back to the array"

**Wrong**

```java
static void zeroSuspense(LedgerEntry[] entries) {
    for (LedgerEntry e : entries) {
        if ("SUSPENSE".equals(e.position())) {
            e = new LedgerEntry("SUSPENSE", 0L);   // rebinds a body-local only
        }
    }
    // entries is unchanged. Nothing was written back.
}
```

**Right**

```java
static void zeroSuspense(LedgerEntry[] entries) {
    for (int i = 0; i < entries.length; i++) {
        if ("SUSPENSE".equals(entries[i].position())) {
            entries[i] = new LedgerEntry("SUSPENSE", 0L);   // writes the slot
        }
    }
}
```

**Why people believe it:** the variable looks like an alias for the slot, the way a
C++ `for (auto& e : entries)` reference would be. JLS 21 §14.14.2's array expansion
is explicit: the body opens with `TargetType Identifier = #a[#i];`, a fresh local
initialised by copy on every iteration. To mutate the sequence you need the index,
which the enhanced form does not expose.

---

## Cheat sheet

| Thing | Rule |
|---|---|
| dangling `else` | binds to nearest `if` without one (JLS 21 §14.9) |
| brace policy | brace every `if` body; it is the only way to express another binding |
| `while (c)` | tests before the body; 0 iterations over an empty condition |
| `do { } while (c)` | tests after the body; body runs at least once (a retry capped at 3) |
| `for (init; c; upd)` | loop variable is header-local; use it when you need the index or a stride |
| `for (;;)` | same as `while (true)` for reachability (see part 1b §16) |
| enhanced `for`, `Iterable` | `iterator()` once + `hasNext`/`next` + `checkcast` per element |
| enhanced `for`, array | index loop, `arraylength` hoisted once into a local |
| enhanced `for` variable | fresh body-local per iteration; reassigning it writes nothing back |
| enhanced `for` index | there is none; carry your own `int` or use a three-part `for` |
| removing while iterating | name the `Iterator` and call `remove()`, or `removeIf` |
| `break` (no label) | innermost enclosing `switch`, `for`, `while`, `do` |
| `break` inside `switch` inside loop | breaks the **switch**; label the loop to exit it |
| `continue` (no label) | loops only; illegal targeting a `switch` |
| labelled `continue` | must target a labelled *loop* |
| label | only target of `break`/`continue`; `goto` is reserved and meaningless |
| abrupt completion | `break`, `continue`, `return`, `throw` (JLS 21 §14.1) |
| escapes the method | `return` and `throw` only |
| `finally` abrupt | replaces the pending reason — never `return` there |

---

## Self-test

**Q1.** What does an enhanced `for` over a `LedgerEntry[]` do that an enhanced `for` over a `List<LedgerEntry>` does not?

<details><summary>Answer</summary>

It compiles to a completely different loop. The array form expands to an index loop
that reads `arraylength` exactly once before the first iteration, stores it in a
local, and compares the index against that local on every iteration — confirmed in
the captured listing where `arraylength` sits at offset 5 and the test at offsets
10–13 compares two locals. The `Iterable` form expands to `iterator()` once, then
`hasNext()` and `next()` per iteration, plus a `checkcast` on every element because
`Iterator.next()` erases to `Object`. So the array form pays no interface dispatch and
no cast; the `Iterable` form pays two interface calls and one cast per element. Both
expansions are specified literally in JLS 21 §14.14.2, and the choice is made from the
static type of the selector at compile time — nothing dispatches at runtime.

</details>

**Q2.** You have `switch (r.key().type())` inside a `for` inside a `for`, and you want the outer loop to stop on the first blocking restriction. What exactly do you write, and what goes wrong if you write `break;`?

<details><summary>Answer</summary>

Label the outer loop (`scan:`) and write `break scan;` from inside the switch arm. A
bare `break;` binds to the *innermost* enclosing `switch`, loop, or `do` — and the
`switch` is innermost, so `break;` merely leaves the switch and the inner loop
continues over the remaining restrictions, then the outer loop continues over the
remaining transactions. That is the single most common reason a labelled `break` is not
optional: a `switch` sitting between you and the loop you meant to exit. This is also
the only legal use of a label in Java (JLS 21 §14.7) — a label exists purely to be
named by a `break` or `continue` inside the statement it labels. Java reserves `goto`
as a keyword and gives it no meaning, and a labelled `break` can only jump forward out
of the labelled statement, so labels are not a back door to one.

</details>

**Q3.** In the `label` method of §1, why does calling it with `reviewCases == 0` return `"AA-700 REVIEW_QUEUED"` rather than `"AA-900 DECLINED"`?

<details><summary>Answer</summary>

Because the `else` binds to the inner `if (operatorOnShift)`, not to the outer
`if (reviewCases > 0)`. JLS 21 §14.9 gives two productions, `IfThenStatement` and
`IfThenElseStatement`, and the grammar is genuinely ambiguous when an `else` follows
two open `if`s; the spec resolves the ambiguity by fiat, binding the `else` to the
nearest preceding `if` that does not already have one. Indentation is not input to the
compiler, so the fact that the `else` is aligned with the outer `if` means nothing.
With `reviewCases == 0` the outer condition is false, so control never enters the outer
`if` at all — neither the inner `if` nor its `else` is reached, and `out` keeps its
initial value. The fix is not to re-indent; it is to brace every `if` body, because
braces are the only syntax that can express a binding other than the nearest one.

</details>

**Q4.** Name the four ways a statement can complete abruptly, what each one carries, and which of them can escape the method.

<details><summary>Answer</summary>

JLS 21 §14.1 defines exactly four. `break`, with or without a label, carries its
target statement and is consumed by the enclosing `switch` or loop, or by the labelled
statement; it cannot escape the method. `continue`, with or without a label, carries
its target loop and is consumed by that loop; it cannot escape the method either, and
it is illegal outside a loop. `return` carries an optional value and is consumed by the
method invocation itself, so it does escape the method. `throw` carries a `Throwable`
and is consumed by a matching `catch`, or else propagates to the caller, so it escapes
too. The reason propagates outward until something consumes it, and `finally` is the
one construct that can *replace* a pending reason: if the `finally` block itself
completes abruptly, its reason wins, which is exactly how a `return` inside `finally`
discards an in-flight exception. The whole of chapter 14 — including the reachability
analysis that rejects unreachable statements — is written in this vocabulary.

</details>

**Q5.** Write out JLS 21 §14.14.2's two expansions of the enhanced `for`, and name the two consequences that fall straight out of them.

<details><summary>Answer</summary>

For an `Iterable` selector, with `#i` a compiler-generated name you cannot collide
with, the expansion is `for (I #i = Expression.iterator(); #i.hasNext(); ) { { TargetType Identifier = (TargetType) #i.next(); } Statement }`.
For an array selector it is `T[] #a = Expression; for (int #i = 0; #i < #a.length; #i++) { { TargetType Identifier = #a[#i]; } Statement }`.
First consequence: the array form assigns the selector to `#a` and reads `#a.length`
into a local before the first iteration, so `arraylength` executes once and never
appears on the back edge — visible in the captured listing at offset 5, with the loop
test at 10–13 comparing two locals. Second consequence: the `Iterable` form has an
explicit `(TargetType)` cast in the expansion, which becomes a `checkcast` on every
element because `Iterator.next()` erases to `Object` — visible at offset 24 of the
iterator listing. A third, quieter consequence is that the loop variable is declared
*inside* the body block, initialised by copy each iteration, so reassigning it writes
nothing back to the array or collection.

</details>

## Open questions

None.

---

**Leaves covered:** 1.8.1, 1.8.2, 1.8.3, 1.8.4, 1.8.5 (5 leaves)
**Leaves deferred:** none
**Diagrams included:** none
**Target version:** Java 21 LTS
**Lines:** 589
