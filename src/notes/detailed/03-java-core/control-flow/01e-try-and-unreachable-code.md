# 03 Java Core — try as control flow, and unreachable code — BASICS (§1.8, 1.8.15, 1.8.16)

**Target version: Java 21 LTS.** | **Part 1 of 5** | [Index](../00-index.md)
Previous: [Assertions and guarded blocks](01d-assertions-and-synchronized.md) · Next: [Wrappers and autoboxing](../wrappers-and-boxing/01-basics.md)

The last two statement forms in §1.8 are the ones that decide what happens when
control does *not* proceed normally. A `finally` can replace the reason a statement
completed abruptly, discarding an in-flight exception with no diagnostic. And
`javac`'s reachability analysis rejects a statement after `while (true)` while
cheerfully accepting one after `if (true) { return; }`. Everything below is grounded
in JLS 21 §14 and in `javac` runs captured on JDK 21.

Branching, looping, labels and abrupt completion are in
[Control flow: branches, loops and abrupt completion](01-basics.md); `assert` and
`synchronized` are in
[Assertions and guarded blocks](01d-assertions-and-synchronized.md).

---

## 15. `try`/`catch`/`finally` and try-with-resources as control flow (1.8.15)

**Mechanism.** `throw` is the fourth abrupt-completion reason from §5 (in
[Control flow: branches, loops and abrupt completion](01-basics.md)), and
`try`/`catch`/`finally` is the construct that consumes it. Three rules matter here
and are developed fully in `../exceptions/01-basics.md`:

1. `finally` runs on every exit from `try` — normal completion, `return`, `break`,
   `continue`, and any `throw`.
2. If `finally` itself completes abruptly, its reason **replaces** the pending one.
   A `return` in `finally` therefore discards an in-flight exception, which is why
   the compiler's `-Xlint:finally` and every static analyser flag it.
3. Try-with-resources is sugar: it emits a hidden `finally` that calls `close()` in
   reverse declaration order, and — unlike a hand-written `finally` — an exception
   from `close()` is *suppressed* onto the primary exception via
   `Throwable.addSuppressed` rather than replacing it.

```java
final class PaymentRunWriter implements AutoCloseable {
    private final String runId;
    PaymentRunWriter(String runId) { this.runId = runId; }
    void write(WithdrawalTransaction tx) { }
    @Override public void close() { }

    static void emit(PaymentRun run) {
        try (PaymentRunWriter w = new PaymentRunWriter(run.runId())) {
            for (WithdrawalTransaction tx : run.transactions()) {
                w.write(tx);
            }
        }
    }
}
```

**Pitfall:** a `return` inside `finally`. Symptom: a `LedgerImbalanceException` that
the logs prove was thrown but that no caller ever sees, because the `finally`
returned a value and the exception was dropped. Fix: `finally` must not contain
`return`, `break`, `continue`, or `throw`; use try-with-resources for cleanup so you
never need to write the `finally` at all.

Exception hierarchies, checked-vs-unchecked, suppression, and the full cost model
are in `../exceptions/01-basics.md` and §1.20.

> `try`/`catch`/`finally` is the construct that consumes an abrupt `throw`, and a
> `finally` completing abruptly replaces the pending reason (JLS 21 §14.20.2).

---

## 16. Unreachable statements: `while (true)` is an error, `if (true)` is not (1.8.16) [TRAP] [PROVE]

**Concept.** `javac` runs a conservative reachability analysis and rejects any
statement it can prove cannot execute. It treats `while (true)` as never completing
normally, so anything after it is unreachable and the build fails. It deliberately
refuses to apply the same reasoning to `if` — an `if (true)` whose branch returns
leaves the following statement formally reachable, even though it obviously is not.

**Why it exists.** The `if` exemption is a documented carve-out, not an oversight.
Before Java had `static final` constant folding used for feature flags, C
programmers wrote `#ifdef DEBUG`. Java's answer is
`static final boolean DEBUG = false;` plus `if (DEBUG) { }` — the compiler folds the
condition and emits no bytecode for the branch, giving conditional compilation with
no preprocessor. If reachability analysis treated `if` the way it treats `while`,
flipping `DEBUG` to `false` would make the *rest of the method* unreachable and break
the build. JLS 21 §14.21 exempts `if` for exactly this reason. What counts as a
constant expression for this folding is covered in
[Operators and expressions](../primitives-and-conversions/02-operators-and-expressions.md).

**How it works.** §14.21 is written in terms of §14.1's normal/abrupt vocabulary. A
`while` statement can complete normally only if its condition is not the constant
`true`, **or** the loop contains a reachable `break` that targets it. An `if`
statement can complete normally if its then-branch can, *or* its else-branch can,
*or* it has no else — and critically the analysis pretends the condition might be
either value regardless of constant folding.

![D-024 — unreachable statements: while(true) versus if(true)](../diagrams/D-024-unreachable-code.svg)

**D-024** — Start on the left: `while (true)` with `auditLedger();` after it, and the
compiler's verdict `error: unreachable statement`. Then compare the right panel,
`if (true) { return; }` followed by the same call — accepted, dead, and shipped. The
annotation panel is the point: §14.21's exemption of `if` is what makes
`static final boolean DEBUG = false` work as conditional compilation.

**The proof.** Both halves compiled on JDK 21. The failing half:

```java
final class ReservationExpiry {
    static void bad() {
        while (true) { }
        auditLedger();
    }
    static void auditLedger() { }
}
```

```
Un2.java:5: error: unreachable statement
    static void bad() { while (true) { } auditLedger(); }
                                         ^
1 error
```

The accepted half, same compiler, same run:

```java
final class ReservationExpiryOk {
    static final boolean DEBUG = false;

    static void ok() {
        if (true) { return; }
        auditLedger();        // dead, but legal
    }

    static void alsoOk() {
        if (DEBUG) { return; }
        auditLedger();        // this is why the exemption exists
    }

    static void auditLedger() { }
}
```

Compiles with no error and no warning. Work the difference through: in `bad()`, §14.21
says the `while` cannot complete normally (constant `true` condition, no `break`
targeting it), so the statement *after* it is unreachable and the spec mandates a
compile-time error. In `ok()`, §14.21 says the `if` can complete normally because the
rule for `if` ignores the constant value of the condition entirely — so
`auditLedger()` is reachable *by the rule*, even though no execution reaches it. The
error is not about whether the code runs; it is about what the specified analysis can
conclude.

Add a `break` and the `while` becomes completable, which is exactly the real
reservation-expiry shape:

```java
final class ReservationSweeper {
    private volatile boolean shuttingDown = false;
    private int sweeps = 0;

    /** Expire stale stake reservations until told to stop. */
    void run() {
        while (true) {
            if (shuttingDown) {
                break;                 // makes the loop completable
            }
            expireOneBatch();
            sweeps++;
        }
        auditLedger();                 // now reachable, and compiles
    }

    private void expireOneBatch() { }
    private void auditLedger() { }
}
```

**Pitfall:** believing `if (false) { }` is a compile error like unreachable code
elsewhere. It is not — it compiles, emits nothing, and is the sanctioned conditional
compilation idiom. The symmetric wrong belief is that `while (true)` with a trailing
statement is "just a warning". Symptom: a build that fails only after somebody adds a
line below a supervisor loop. Fix: put the trailing work *inside* the loop after a
`break`, or restructure the loop condition to be a real boolean.

**Interview:** "Why does `while (true); stmt;` fail to compile but `if (true) return; stmt;`
not?" — Answer: JLS 21 §14.21 defines a `while` with a constant-`true` condition and no
targeting `break` as unable to complete normally, making the next statement
unreachable; it deliberately exempts `if` so that `if (CONSTANT_FALSE)` works as
conditional compilation without breaking every statement that follows.

> An unreachable statement is a compile-time error under JLS 21 §14.21, which
> analyses `while`/`for` conditions as constants but deliberately exempts `if` to
> permit constant-guarded conditional compilation.

---

## Pitfalls

### "A `return` in `finally` is just a tidy way to name the result"

**Wrong**

```java
static boolean settle(FundsLedger ledger, WithdrawalTransaction tx) {
    boolean applied = false;
    try {
        ledger.apply(tx);            // may throw LedgerImbalanceException
        applied = true;
        return applied;
    } finally {
        return applied;              // swallows any in-flight exception
    }
}
// A thrown LedgerImbalanceException never reaches the caller; settle() returns false.
```

**Right**

```java
static boolean settle(FundsLedger ledger, WithdrawalTransaction tx) {
    try {
        ledger.apply(tx);
        return true;
    } finally {
        ledger.flushAuditBuffer();   // side effect only; no abrupt completion
    }
}
// The exception propagates, and the audit buffer is still flushed on every path.
```

**Why people believe it:** `finally` reads as "the last thing", and the last thing a
method does is return. JLS 21 §14.20.2 is explicit that a `finally` completing
abruptly *replaces* the pending reason — so a pending `throw` is discarded, silently
and with no diagnostic beyond `-Xlint:finally`. Reserve `finally` for side effects, and
prefer try-with-resources so you rarely write one.

### "Unreachable code is a warning, and `if (false)` is an error"

**Wrong**

```java
final class SweeperBad {
    static final boolean DEBUG = false;

    static void run() {
        while (true) { expireOneBatch(); }
        auditLedger();          // author expects a warning; the build fails
    }

    static void alsoBad() {
        if (DEBUG) { return; }  // author expects an error; this is perfectly legal
        auditLedger();
    }

    static void expireOneBatch() { }
    static void auditLedger() { }
}
```

**Right**

```java
final class SweeperOk {
    static final boolean DEBUG = false;
    private volatile boolean shuttingDown = false;

    void run() {
        while (true) {
            if (shuttingDown) { break; }   // the loop can now complete normally
            expireOneBatch();
        }
        auditLedger();                     // reachable by the rule, and compiles
    }

    void debugOnly() {
        if (DEBUG) { auditLedger(); }      // folded away, emits no bytecode
    }

    private void expireOneBatch() { }
    private void auditLedger() { }
}
```

**Why people believe it:** both beliefs come from expecting the compiler to reason
about what actually executes. It does not; JLS 21 §14.21 specifies a structural
analysis. A `while` whose condition is the constant `true` with no targeting `break`
is *defined* as unable to complete normally, which makes the next statement
unreachable and mandates `error: unreachable statement`. The rule for `if`
deliberately ignores the condition's constant value, which is exactly what makes
`static final boolean DEBUG = false` usable as conditional compilation.

### "Resources in a try-with-resources close in the order I declared them"

**Wrong**

```java
/** One of the four daily payout windows: ~7k bank withdrawals split across them. */
static void emitWindow(PaymentRun run) {
    try (FundsLedger ledger = FundsLedger.open(run.runId());
         PaymentRunWriter writer = new PaymentRunWriter(run.runId(), ledger)) {
        for (WithdrawalTransaction tx : run.transactions()) {
            writer.write(tx);
        }
    }
    // Author's belief: ledger closes first, then writer.
    // If that were true, writer.close() would flush its buffer through a ledger
    // that had already been closed, and every trailing LedgerEntry would be lost.
}
```

**Right**

```java
static void emitWindow(PaymentRun run) {
    try (FundsLedger ledger = FundsLedger.open(run.runId());
         PaymentRunWriter writer = new PaymentRunWriter(run.runId(), ledger)) {
        for (WithdrawalTransaction tx : run.transactions()) {
            writer.write(tx);
        }
    }
    // Actual order: writer.close() first, then ledger.close() — reverse of declaration.
    // The dependent resource is torn down while the thing it depends on is still open,
    // which is why declaring the dependency second is the correct habit.
}
```

**Why people believe it:** the resource list reads like a sequence of statements, and
sequences run forwards. Closing has to run backwards for the same reason a stack
unwinds backwards: a resource declared later may hold a reference to one declared
earlier, so releasing the earlier one first would leave the later one operating on
something already shut. JLS 21 specifies the reverse order, and the sugar's hidden
`finally` blocks are nested rather than sequential, which is also what makes
suppression work — an exception from an inner `close()` is attached to the primary via
`Throwable.addSuppressed` as the nesting unwinds, rather than replacing it.

---

## Cheat sheet

| Thing | Rule |
|---|---|
| `finally` runs on | normal completion, `return`, `break`, `continue`, `throw` |
| `finally` abrupt | replaces the pending reason — never `return`/`break`/`continue`/`throw` there |
| lint for it | `-Xlint:finally`; every static analyser flags it too |
| try-with-resources | hidden `finally`, `close()` in reverse declaration order |
| why reverse order | a later resource may depend on an earlier one |
| `close()` throwing | suppressed onto the primary via `Throwable.addSuppressed`, not substituted |
| retrieving the suppressed | `Throwable.getSuppressed()` |
| resource variables | implicitly final; may also be an effectively-final existing variable (9+) |
| `throw` | the fourth abrupt-completion reason, alongside `return`/`break`/`continue` |
| `while (true)` + trailing statement | `error: unreachable statement` (JLS 21 §14.21) |
| making the loop completable | a reachable `break` that targets it |
| `if (true) { return; }` + trailing statement | legal; the `if` rule ignores the constant condition |
| why the exemption exists | `static final boolean DEBUG = false` as conditional compilation |
| the analysis is structural | about what the rule can conclude, not about what executes |
| unreachable is an error | not a warning; there is no flag to downgrade it |

---

## Self-test

**Q1.** Why does `while (true) { } auditLedger();` fail to compile while `if (true) { return; } auditLedger();` compiles?

<details><summary>Answer</summary>

JLS 21 §14.21 defines reachability structurally. A `while` whose condition is the
constant `true` and which contains no `break` targeting it cannot complete normally,
so the statement after it is unreachable and the spec mandates a compile-time error —
observed as `error: unreachable statement`. The rule for `if`, by contrast,
deliberately ignores whether the condition is a constant: an `if` can complete
normally if either branch can or if there is no else, so the following statement is
reachable *by the rule* even when no execution reaches it. The exemption is
intentional: it is what makes `static final boolean DEBUG = false;` plus
`if (DEBUG) { }` work as conditional compilation. Without it, flipping a debug flag to
false would render the rest of every method unreachable and break the build.

</details>

**Q2.** A `finally` block and a try-with-resources `close()` both run on the way out. What is the difference when both the body and the cleanup throw?

<details><summary>Answer</summary>

With a hand-written `finally` that throws, the `finally`'s reason *replaces* the
pending one (JLS 21 §14.20.2), so the body's exception is discarded and the caller sees
only the cleanup failure — the original cause is gone, with no diagnostic beyond
`-Xlint:finally`. Try-with-resources deliberately does not do that. It emits a hidden
`finally` that calls `close()` on each resource in reverse declaration order, and if a
`close()` throws while an exception from the body is already in flight, the `close()`
exception is *suppressed* onto the primary via `Throwable.addSuppressed` rather than
substituted for it. The caller therefore gets the body's exception, which is the one
that explains the failure, with the cleanup failure retrievable from
`getSuppressed()`. The same asymmetry applies to `return`: a `return` in `finally`
discards an in-flight exception, which is why the rule is that `finally` must not
contain `return`, `break`, `continue` or `throw`, and why cleanup belongs in
try-with-resources.

</details>

**Q3.** Enumerate the exits from a `try` block on which `finally` runs, and name the one case where it does not.

<details><summary>Answer</summary>

It runs on all five ways the block can finish. Normal completion — control reaches the
closing brace. `return`, including a `return` whose value has already been computed:
the value is evaluated, then the `finally` runs, then the method returns. `break` and
`continue` targeting a loop or label outside the `try`, where the `finally` runs before
control transfers. And any `throw`, whether from a `throw` statement, a failed method
call, or an implicit one such as a null dereference — the `finally` runs as the
exception propagates through, whether or not a matching `catch` exists. That last point
is worth stating precisely: `finally` is not conditional on the exception being caught.
The cases where it does not run are not exits from the block at all: `System.exit`,
which terminates the JVM without unwinding, a `Runtime.halt`, an infinite loop or a
blocked call inside the `try` that never finishes, a JVM crash, and a
`StackOverflowError` or `OutOfMemoryError` severe enough that the handler itself cannot
run. Everything that is genuinely an exit from the block runs the `finally`.

</details>

**Q4.** A supervisor loop is `while (true) { expireOneBatch(); }` and you need to run `auditLedger()` after it. The build now fails. What are your options, and which is right?

<details><summary>Answer</summary>

The build fails with `error: unreachable statement` because §14.21 defines a
constant-`true` `while` with no targeting `break` as unable to complete normally.
Three options. Wrong first: move `auditLedger()` inside the loop body, which changes
the semantics from "audit once after shutdown" to "audit every sweep" — 2.8M
reservations a day makes that a different program. Also wrong: replace `true` with a
non-constant expression such as a `volatile boolean` field read, which does silence the
error, because the condition is no longer a constant expression and the `while` is
therefore analysed as completable — but it silences it by hiding the structure rather
than expressing it, and a reader can no longer see where the loop terminates. Right:
add a reachable `break` that targets the loop, guarded by the shutdown condition, and
leave `auditLedger()` after it. That is `while (true) { if (shuttingDown) { break; }
expireOneBatch(); }` followed by `auditLedger();`. The `break` makes the loop
completable by the rule, so the trailing statement is reachable and compiles, and it
states the exit point at the exact line where the decision is made.

</details>

**Q5.** Unreachable code is an error, not a warning, and there is no flag to downgrade it. Is that a good design?

<details><summary>Answer</summary>

Yes, and the reason is that the analysis is cheap, total and structural, so a violation
is never a false positive about the rule — only ever about intent. §14.21 does not ask
"does this execute"; that question is undecidable in general. It asks "can the preceding
statement complete normally under these specific structural rules", which is a decision
procedure the compiler can run exactly. When it says a statement is unreachable, the
statement genuinely is unreachable, so keeping it in the source is at best a leftover
and at worst a misunderstanding of the loop above it. Making it an error rather than a
warning also protects the spec's own consistency: definite-assignment analysis is
defined in the same normal/abrupt vocabulary, so permitting unreachable statements
would require saying what a local's assignment state is on a path that does not exist.
The price of the strictness is exactly one nuisance case — a trailing statement below a
supervisor loop — and the language paid for it in a different currency by exempting
`if`, which is what makes constant-guarded conditional compilation possible without a
preprocessor.

</details>

**Q6.** `try (FundsLedger ledger = FundsLedger.open(); PaymentRunWriter writer = new PaymentRunWriter(runId, ledger))` — why does the declaration order matter, and can a resource variable be reassigned inside the body?

<details><summary>Answer</summary>

Order matters because closing runs in *reverse* declaration order. `writer` is closed
first, then `ledger`, which is the order you need: `writer` holds a reference to
`ledger` and its `close()` flushes buffered `LedgerEntry` rows through it, so `ledger`
must still be open at that moment. Declaring the dependency second — the thing that
*depends*, second — is therefore the habit to keep, and reversing the two lines would
mean `writer.close()` writing into a closed ledger and losing every trailing entry from
the payout window. The sugar's hidden `finally` blocks are nested rather than
sequential, which is what produces the reverse order and also what makes suppression
work as the nesting unwinds. And no: a resource variable is implicitly `final`, so it
cannot be reassigned inside the body — that is deliberate, because the hidden `finally`
calls `close()` on the variable, and reassigning it would close something other than
what was opened. Since Java 9 the resource specification may also name an existing
effectively-final variable instead of declaring a new one, which covers the case where
the resource was created earlier; the same immutability requirement is why it must be
effectively final.

</details>

---

## Open questions

None.

---

**Leaves covered:** 1.8.15, 1.8.16 (2 leaves)
**Leaves deferred:** none
**Diagrams included:** D-024
**Target version:** Java 21 LTS
**Lines:** 492
