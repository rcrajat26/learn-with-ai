# 03 Java Core — Exception builds — the `finally`-return harness — BUILD IT (§4.6, leaf 4.6.8)

**Target version: Java 21 LTS.** | **Part 4 of 5** | [Index](../00-index.md)
Previous: [AutoCloseable, try-with-resources, and suppression](03d-autocloseable-and-finally.md) · Next: [CheckedFunction and sneaky-throw](03e-checked-crossing-cleaner-and-diff.md)

---

A `return` in a `finally` block does not override the `try` block's result. It **abruptly completes
the whole `try` statement** — and whatever abrupt completion was already in flight, including a
thrown exception mid-propagation, is discarded. Not caught, not logged, not chained as a cause, not
attached with `addSuppressed`. The JLS's own word for it is "forgotten".

That is why this bug is invisible in a way almost no other Java bug is: no stack trace, because
nothing printed one; no compiler error, because the code is legal; no failing test, because the
method returns a plausible success value.

The sibling case — a `throw` inside `finally` discarding the pending exception — is the same
destruction by a different abrupt-completion reason and belongs to
[`03d-autocloseable-and-finally.md`](03d-autocloseable-and-finally.md), along with
try-with-resources' `addSuppressed`, close ordering and idempotent `close()`. It differs in one
respect: a `throw` in `finally` at least leaves *an* exception, so somebody eventually notices.

## What the specification actually says

JLS §14.20.2 (*Execution of try-finally and try-catch-finally*) enumerates the cases. Two clauses,
quoted:

> If execution of the try block completes abruptly because of a `throw` of a value V […] If the
> finally block completes abruptly for reason S, then the try statement completes abruptly for
> reason S (and the throw of value V is discarded and forgotten).

> If the catch block completes abruptly for reason R, then the finally block is executed. […] If
> the finally block completes abruptly for reason S, then the try statement completes abruptly
> for reason S (and reason R is discarded).

A third clause repeats the sentence for "any other reason R", covering `break`, `continue` and
`return` out of the `try` block. Read the shape, not the words: **reason S always beats reason R,
whatever R was.** A `return` is a reason — JLS §14.1 lists the abrupt-completion reasons as `break`,
`continue`, `return` and a `throw`. Nothing ranks a thrown exception above a `return`; they are
peers, and the later wins.

> **A `return`, `break` or `continue` in a `finally` block completes the enclosing `try` statement
> abruptly for its own reason, silently discarding any pending exception, return or jump.**

## The harness

Seven cases, each a method named for what it does, run in order from one `main`. The domain is the
`PaymentRun` batch writer: bank withdrawals go out in four windows a day, and `writeLedgerEntries`
refuses to book a run whose withdrawals do not sum to the operator's signed declared total.

The exception names are the ones
[`03c-exception-hierarchy-and-stackless.md`](03c-exception-hierarchy-and-stackless.md) built —
`LedgerImbalanceException` (unchecked), `InsufficientFundsException` (checked) and
`IllegalTransitionException` (unchecked) — carrying a plain message rather than that file's
`FailureDetail` / `ErrorCode` machinery. Order 15 owns the real hierarchy.

```java
import java.math.BigDecimal;
import java.util.ArrayList;
import java.util.List;
import java.util.function.Supplier;

/** Every way a `finally` block can abruptly complete a `try` statement and destroy what was
 *  in flight. Domain: the PaymentRun batch writer for bank withdrawals. */
public final class FinallyReturnHarness {

    // ---------- domain ----------

    record Money(BigDecimal amount, String currency) {
        Money plus(Money other) { return new Money(amount.add(other.amount), currency); }
        Money minus(Money other) { return new Money(amount.subtract(other.amount), currency); }
        @Override public String toString() { return amount.toPlainString() + " " + currency; }
        static Money of(String v) { return new Money(new BigDecimal(v), "GBP"); }
    }
    /** A batch of approved bank withdrawals. `declaredTotal` is what the operator signed off. */
    record PaymentRun(int window, List<Money> withdrawals, Money declaredTotal) {
        Money sum() {
            Money total = Money.of("0.00");
            for (Money w : withdrawals) total = total.plus(w);
            return total;
        }
        boolean balances() { return sum().amount().compareTo(declaredTotal.amount()) == 0; }
    }

    static final class LedgerImbalanceException extends RuntimeException {
        private static final long serialVersionUID = 1L;
        LedgerImbalanceException(int window, Money booked, Money declared) {
            super("LEDGER_IMBALANCE window=" + window + " booked=" + booked
                    + " declared=" + declared + " delta=" + booked.minus(declared));
        }
    }

    static final class InsufficientFundsException extends Exception {
        private static final long serialVersionUID = 1L;
        InsufficientFundsException(Money shortfall) {
            super("INSUFFICIENT_FUNDS shortfall=" + shortfall);
        }
    }

    static final class IllegalTransitionException extends RuntimeException {
        private static final long serialVersionUID = 1L;
        IllegalTransitionException(String from, String to) {
            super("ILLEGAL_TRANSITION " + from + " -> " + to);
        }
    }

    /** Writes one ledger entry pair per withdrawal, then checks double entry. Returns the
     *  number of entries written. Throws if debits did not equal credits. */
    static int writeLedgerEntries(PaymentRun run) {
        int entries = run.withdrawals().size() * 2;
        if (!run.balances()) {
            throw new LedgerImbalanceException(run.window(), run.sum(), run.declaredTotal());
        }
        return entries;
    }
```

### Cases 1 and 2 — the exception dies, and the return value dies

```java
    // ---------- case 1: try throws, finally returns ----------

    /** The headline bug. `writeLedgerEntries` throws; the `return` in `finally` abruptly
     *  completes the whole try statement and the pending exception is discarded. */
    static int case1SwallowedLedgerImbalance(PaymentRun run) {
        try {
            return writeLedgerEntries(run);
        } finally {
            return run.withdrawals().size() * 2;
        }
    }

    /** Same shape with a CHECKED exception. No `throws` clause, and it compiles: JLS 11.2.2
     *  says a try statement can throw E only if its finally block can complete normally. */
    static int case1bCheckedNeedsNoThrows(Money shortfall) {
        try {
            throw new InsufficientFundsException(shortfall);
        } finally {
            return 0;
        }
    }

    // ---------- case 2: try returns, finally returns ----------

    static int case2FinallyReturnWinsOverTryReturn(PaymentRun run) {
        try {
            return run.withdrawals().size() * 2;
        } finally {
            return -1;
        }
    }
```

**Insight:** `case1bCheckedNeedsNoThrows` throws a *checked* exception in its `try` block and
carries **no `throws` clause at all** — and compiles clean. JLS §11.2.2 lists the exception classes
a `try` statement can throw, and every clause is conditioned on "no finally block is present or the
finally block can complete normally". A `finally` that returns cannot complete normally, so by the
specification the `try` statement throws nothing and there is nothing to declare. The
checked-exception system — the one feature Java has for making failure paths visible in signatures
— knows the exception has been destroyed, agrees, and says nothing.

### Case 3 — the case that separates understanding from folklore

The folklore says "mutating the variable in `finally` changes what the caller sees". It does not
for a primitive or an immutable, and it does for a mutable object — both halves from one cause.
`return expr;` evaluates `expr` and copies the resulting **value** to the return slot *before* the
`finally` body runs. For an `int` that value is the number; for a `Money` or a `List` it is the
reference. Reassigning the local cannot reach the copy; mutating the object it points at can.
[`../immutability-and-design/03-pass-by-value.md`](../immutability-and-design/03-pass-by-value.md)
owns pass-by-value in full.

```java
    // ---------- case 3: finally mutates but does not return ----------

    /** Primitive. The value was copied to the return slot before `finally` ran. */
    static int case3aPrimitiveMutationInvisible(PaymentRun run) {
        int entries = run.withdrawals().size() * 2;
        try {
            return entries;
        } finally {
            entries = -999;
            System.out.println("    [finally] local entries is now " + entries);
        }
    }

    /** Immutable value object. Reassigning the local cannot reach the copied reference. */
    static Money case3bImmutableMutationInvisible(PaymentRun run) {
        Money total = run.sum();
        try {
            return total;
        } finally {
            total = total.plus(Money.of("1000.00"));
            System.out.println("    [finally] local total is now " + total);
        }
    }

    /** Mutable object. The copied thing was the reference, so the mutation IS visible. */
    static List<String> case3cMutableMutationVisible(PaymentRun run) {
        List<String> failures = new ArrayList<>();
        try {
            if (!run.balances()) failures.add("LEDGER_IMBALANCE window=" + run.window());
            return failures;
        } finally {
            failures.add("ADDED_IN_FINALLY");
            System.out.println("    [finally] list now has " + failures.size() + " entries");
        }
    }
```

### Case 4 — `break` and `continue`, separately

```java
    // ---------- case 4: finally breaks / continues ----------

    /** `break` in `finally` abruptly completes the try statement by exiting the loop. */
    static String case4aFinallyBreaksOutOfLoop(List<PaymentRun> runs) {
        String lastStatus = "no windows processed";
        for (PaymentRun run : runs) {
            try {
                int entries = writeLedgerEntries(run);
                lastStatus = "window " + run.window() + " wrote " + entries + " entries";
            } finally {
                if (!run.balances()) {
                    System.out.println("    [finally] window " + run.window()
                            + " did not balance; breaking");
                    break;
                }
            }
        }
        return lastStatus;
    }

    /** `continue` in `finally` destroys the exception and carries on to the next window. */
    static int case4bFinallyContinuesPastFailure(List<PaymentRun> runs) {
        int written = 0;
        for (PaymentRun run : runs) {
            try {
                written += writeLedgerEntries(run);
                System.out.println("    [try] window " + run.window() + " ok, running total "
                        + written);
            } finally {
                continue;
            }
        }
        return written;
    }
```

Case 4b is the nastier of the two in production: `continue` in a batch loop reads as "skip the bad
record and keep going", a legitimate policy — except that it also erases *why* the record was bad,
and the accumulator quietly under-counts.

### Case 5 — the `catch` block is not safe either

```java
    // ---------- case 5: catch is throwing, finally returns ----------

    /** The `catch` maps the imbalance to an illegal transition. The `finally` return destroys
     *  the catch block's exception exactly as it would have destroyed the try block's. */
    static String case5FinallyReturnDestroysCatchThrow(PaymentRun run) {
        try {
            writeLedgerEntries(run);
            return "AA-801 ACTIVATED";
        } catch (LedgerImbalanceException e) {
            System.out.println("    [catch] mapping " + e.getMessage());
            throw new IllegalTransitionException("PaymentRun.APPROVED", "PaymentRun.SETTLED");
        } finally {
            return "AA-801 ACTIVATED";
        }
    }
```

This is the case people get wrong once they have learned the first one. "Catch it and rethrow
something meaningful" does not help: the `catch` block's own `throw` is reason R, the `finally`
return is reason S, and the second JLS clause quoted above says S wins. The `catch` block ran,
logged, built its wrapped exception — and it evaporated.

### Case 6 — nested, inner `finally` returns

```java
    // ---------- case 6: nested, inner finally returns ----------

    /** Outer body throws. The outer `finally` runs with that exception pending, and its own
     *  inner `finally` returns, so both the outer pending exception and the inner one die. */
    static String case6NestedInnerFinallyReturns(PaymentRun run) {
        try {
            throw new LedgerImbalanceException(run.window(), run.sum(), run.declaredTotal());
        } finally {
            System.out.println("    [outer finally] entered with an imbalance pending");
            try {
                throw new IllegalTransitionException("PaymentRun.SETTLING", "PaymentRun.FAILED");
            } finally {
                System.out.println("    [inner finally] returning");
                return "BDP-101 SETTLED";
            }
        }
    }
```

Two exceptions destroyed by one `return`. The inner `try` statement completes abruptly for reason
"return `BDP-101 SETTLED`", discarding the `IllegalTransitionException`. That abrupt completion *is*
the outer `finally` completing abruptly, so the outer `try` statement completes for the same reason,
discarding the `LedgerImbalanceException`. The rule composes, in the wrong direction.

### Case 7 — the two correct forms, run alongside

```java
    // ---------- case 7: the correct forms ----------

    /** `finally` for cleanup only: no return, no throw, no break, no continue. The pending
     *  exception survives and the caller sees it. */
    static int case7aFinallyCleanupOnly(PaymentRun run) {
        boolean fileOpen = true;
        try {
            return writeLedgerEntries(run);
        } finally {
            fileOpen = false;
            System.out.println("    [finally] payout file closed, fileOpen=" + fileOpen);
        }
    }

    /** Try-with-resources cannot express the bug: there is no author-written block for a
     *  `return` to live in. The close runs, the exception propagates. */
    static final class PayoutFile implements AutoCloseable {
        private final int window;
        PayoutFile(int window) {
            this.window = window;
            System.out.println("    [open] payout file for window " + window);
        }
        @Override public void close() {
            System.out.println("    [close] payout file for window " + window);
        }
    }

    static int case7bTryWithResources(PaymentRun run) {
        try (PayoutFile file = new PayoutFile(run.window())) {
            return writeLedgerEntries(run);
        }
    }
```

Case 7b is the structural argument for try-with-resources that has nothing to do with brevity. The
cleanup lives in `close()`, whose body cannot `return` out of the *caller's* `try` statement.
**The bug is not discouraged here; it is unexpressible.** Order 17 owns suppression.

### The driver

```java
    // ---------- driver ----------

    static PaymentRun balancedRun(int window) {
        return new PaymentRun(window, List.of(Money.of("260.00"), Money.of("260.00")),
                Money.of("520.00"));
    }

    static PaymentRun imbalancedRun(int window) {
        return new PaymentRun(window, List.of(Money.of("260.00"), Money.of("260.00")),
                Money.of("520.01"));
    }

    /** Banner FIRST, then the case, so its [finally] lines land between banner and result. */
    static void run(String label, Supplier<Object> oneCase) {
        System.out.println();
        System.out.println("== " + label);
        System.out.println("  caller sees: " + oneCase.get());
    }

    /** Renders an escaping LedgerImbalanceException as a log line would. */
    static Object caught(Supplier<Object> body) {
        try {
            return body.get();
        } catch (LedgerImbalanceException e) {
            return e.getClass().getSimpleName() + ": " + e.getMessage();
        }
    }

    public static void main(String[] args) {
        PaymentRun bad = imbalancedRun(3);
        PaymentRun good = balancedRun(1);
        List<PaymentRun> windows = List.of(good, bad, balancedRun(4));

        run("case 1  try throws, finally returns", () -> case1SwallowedLedgerImbalance(bad));
        run("case 1b checked throw, finally returns, no throws clause", () -> case1bCheckedNeedsNoThrows(Money.of("4.20")));
        run("case 2  try returns 4, finally returns -1", () -> case2FinallyReturnWinsOverTryReturn(good));
        run("case 3a primitive mutated in finally", () -> case3aPrimitiveMutationInvisible(good));
        run("case 3b immutable reassigned in finally", () -> case3bImmutableMutationInvisible(good));
        run("case 3c mutable List mutated in finally", () -> case3cMutableMutationVisible(bad));
        run("case 4a finally breaks out of the loop", () -> case4aFinallyBreaksOutOfLoop(windows));
        run("case 4b finally continues to the next window", () -> case4bFinallyContinuesPastFailure(windows));
        run("case 5  catch is throwing, finally returns", () -> case5FinallyReturnDestroysCatchThrow(bad));
        run("case 6  nested, inner finally returns", () -> case6NestedInnerFinallyReturns(bad));
        run("case 7a finally for cleanup only (correct)", () -> caught(() -> case7aFinallyCleanupOnly(bad)));
        run("case 7b try-with-resources (correct, bug unexpressible)", () -> caught(() -> case7bTryWithResources(bad)));
    }
}
```

### Real output

Oracle JDK 21.0.7 (build 21.0.7+8-LTS-245), macOS aarch64. `javac -d . FinallyReturnHarness.java`
compiles with **no warnings and no errors** at default settings, and prints:

```console
== case 1  try throws, finally returns
  caller sees: 4

== case 1b checked throw, finally returns, no throws clause
  caller sees: 0

== case 2  try returns 4, finally returns -1
  caller sees: -1

== case 3a primitive mutated in finally
    [finally] local entries is now -999
  caller sees: 4

== case 3b immutable reassigned in finally
    [finally] local total is now 1520.00 GBP
  caller sees: 520.00 GBP

== case 3c mutable List mutated in finally
    [finally] list now has 2 entries
  caller sees: [LEDGER_IMBALANCE window=3, ADDED_IN_FINALLY]

== case 4a finally breaks out of the loop
    [finally] window 3 did not balance; breaking
  caller sees: window 1 wrote 4 entries

== case 4b finally continues to the next window
    [try] window 1 ok, running total 4
    [try] window 4 ok, running total 8
  caller sees: 8

== case 5  catch is throwing, finally returns
    [catch] mapping LEDGER_IMBALANCE window=3 booked=520.00 GBP declared=520.01 GBP delta=-0.01 GBP
  caller sees: AA-801 ACTIVATED

== case 6  nested, inner finally returns
    [outer finally] entered with an imbalance pending
    [inner finally] returning
  caller sees: BDP-101 SETTLED

== case 7a finally for cleanup only (correct)
    [finally] payout file closed, fileOpen=false
  caller sees: LedgerImbalanceException: LEDGER_IMBALANCE window=3 booked=520.00 GBP declared=520.01 GBP delta=-0.01 GBP

== case 7b try-with-resources (correct, bug unexpressible)
    [open] payout file for window 3
    [close] payout file for window 3
  caller sees: LedgerImbalanceException: LEDGER_IMBALANCE window=3 booked=520.00 GBP declared=520.01 GBP delta=-0.01 GBP
```

Three lines in that output are the whole file. Case 1 reports `4` entries written for a run whose
withdrawals sum to `520.00` against a declared `520.01`. Case 4b reports `8` with no indication a
third window was attempted. Case 5 reports `AA-801 ACTIVATED` after its `catch` block visibly ran
and visibly threw.

## The mechanism, in bytecode

`finally` is not a runtime construct: no class-file attribute, no JVM instruction. `javac`
**duplicates the `finally` body into every path that leaves the `try` block** and adds one entry to
the `Code` attribute's exception table with type `any` (`catch_type` 0, "catch everything, including
`Error`") covering the `try` range. That handler runs the duplicated body, then rethrows.

Case 1, from `javap -c -p`:
```text
  static int case1SwallowedLedgerImbalance(FinallyReturnHarness$PaymentRun);
    Code:
       0: aload_0
       1: invokestatic  #38                 // Method writeLedgerEntries:(LFinallyReturnHarness$PaymentRun;)I
       4: istore_1
       5: aload_0
       6: invokevirtual #7                  // Method FinallyReturnHarness$PaymentRun.withdrawals:()Ljava/util/List;
       9: invokeinterface #13,  1           // InterfaceMethod java/util/List.size:()I
      14: iconst_2
      15: imul
      16: ireturn
      17: astore_2
      18: aload_0
      19: invokevirtual #7                  // Method FinallyReturnHarness$PaymentRun.withdrawals:()Ljava/util/List;
      22: invokeinterface #13,  1           // InterfaceMethod java/util/List.size:()I
      27: iconst_2
      28: imul
      29: ireturn
    Exception table:
       from    to  target type
           0     5    17   any
```

| Offsets | What it is |
|---|---|
| `0`–`1` | the `try` body: call `writeLedgerEntries` |
| `4` | `istore_1` — the `try` block's `return` value goes to a local slot, not to the caller |
| `5`–`16` | copy 1 of the `finally` body, on the normal-completion path. It computes `size() * 2` and `ireturn`s. The value stored at `4` is never read. |
| `17` | `astore_2` — **the handler entry point. This is where the pending exception stops existing.** |
| `18`–`29` | copy 2 of the same `finally` body, on the exceptional path. Same computation, same `ireturn`. |

Offset `17` is the exact instruction. `astore_2` pops the throwable into local slot 2, and slot 2 is
never loaded again anywhere in the method — no `aload_2`, no `athrow`. The rethrow a well-formed
handler ends with was never generated: `javac` inlined a `finally` body ending in `ireturn`, so the
rethrow is unreachable and javac does not emit unreachable code. The only reference to the in-flight
`LedgerImbalanceException` in the whole method is a store into a dead slot.

`case7aFinallyCleanupOnly`, the correct form, ends one instruction pair differently:

```text
      23: astore_3
      24: iconst_0
      25: istore_1
      26: getstatic     #49                 // Field java/lang/System.out:Ljava/io/PrintStream;
      29: iload_1
      30: invokedynamic #143,  0            // InvokeDynamic #8:makeConcatWithConstants:(Z)Ljava/lang/String;
      35: invokevirtual #59                 // Method java/io/PrintStream.println:(Ljava/lang/String;)V
      38: aload_3
      39: athrow
    Exception table:
       from    to  target type
           2     7    23   any
```

`astore_3` at `23`, the duplicated cleanup, then `38: aload_3` / `39: athrow` — same store, but the
slot is read back and rethrown. That pair is the whole difference between a batch that reports its
imbalance and one that hides it.

Case 3a proves the copy-to-return-slot claim the same way:

```text
      11: istore_1
      12: iload_1
      13: istore_2
      14: sipush        -999
      17: istore_1
      18: getstatic     #49                 // Field java/lang/System.out:Ljava/io/PrintStream;
      21: iload_1
      22: invokedynamic #55,  0             // InvokeDynamic #0:makeConcatWithConstants:(I)Ljava/lang/String;
      27: invokevirtual #59                 // Method java/io/PrintStream.println:(Ljava/lang/String;)V
      30: iload_2
      31: ireturn
```

That is offsets `11`–`31`, the normal path; the handler at `32` duplicates the same body and ends
`aload_3; athrow`, and the exception table reads `from 12 to 14 target 32 any`. Read the normal
path: `12: iload_1` / `13: istore_2` is the copy, `17: istore_1` is the mutation, `30: iload_2` is
the return. Two different slots, so the mutation cannot be seen. Case 3c has no analogue: the slot
is never rewritten, and `failures.add` mutates the heap object the caller now holds.

**Version fact.** JVMS §4.10.2.5 describes the *old* mechanism: "a compiler […] that generates
class files with version number 50.0 or below may use the exception-handling facilities together
with two special instructions: `jsr` […] and `ret`" — one copy of the `finally` body as a
subroutine, with every exit path doing a `jsr` to it. That shape is now **illegal**, not merely
unfashionable: JVMS §4.9.1 states that "if the class file version number is 51.0 or above, then
instances of instructions using the `jsr`, `jsr_w`, or `ret` opcodes must not appear in the code
array." 51.0 is Java 7; this harness compiles to major version 65 (Java 21) and `javap` over the
whole class shows zero `jsr`, `jsr_w` or `ret`. Material explaining `finally` in terms of `jsr` is
describing a shape you cannot legally produce today. **Unverified:** the exact javac release that
stopped *emitting* `jsr` (it predates the prohibition, in the 1.4.2-to-6 window).

The desugaring in full belongs to
[`../exceptions/03a-internals-finally-and-twr-desugaring.md`](../exceptions/03a-internals-finally-and-twr-desugaring.md);
the exception table's format and throw/catch dispatch to
[`../exceptions/03-internals-exception-mechanics.md`](../exceptions/03-internals-exception-mechanics.md).

## Catching it in review and in CI

Measured on this exact harness, not recalled.

`javac` at default settings prints nothing. **But `-Xlint:finally` does flag it** — the common claim
that the compiler is silent here is wrong, and wrong in a way that matters, because the check
exists and is merely off by default. On the harness it prints seven warnings:

```console
FinallyReturnHarness.java:70: warning: [finally] finally clause cannot complete normally
        }
        ^
```

The hits land on cases 1, 1b, 2, 4b's `continue`, 5, and both `finally` blocks of case 6.
`-Xlint:all` adds only an unrelated `[try]` warning about case 7b's unreferenced resource. What it
**misses** is the interesting part:

| Case | `-Xlint:finally` | Why |
|---|---|---|
| 1, 1b, 2, 4b, 5, 6 (twice) | warns | the `finally` block definitely cannot complete normally |
| 4a — `break` guarded by `if (!run.balances())` | **silent** | the block *can* complete normally, so the check does not fire |
| 3a, 3b, 3c — mutation in `finally` | **silent** | nothing abrupt happens; the misunderstanding is not a lint-able shape |

The lint is a structural check on "cannot complete normally", not a data-flow check on "might
discard a pending exception". Put the `return` behind an `if` and it goes quiet — which is the form
this bug takes in real code: nobody writes a bare `return` in a `finally`, plenty write
`if (retriesExhausted) return partialResult;`.

Third-party checks, verified against their published catalogues:

| Tool | Identifier | What it says |
|---|---|---|
| ErrorProne | `Finally` (alternate names `finally`, `ThrowFromFinallyBlock`), severity `WARNING`, tag `FragileCode` | "If you return or throw from a finally, then values returned or thrown from the try-catch block will be ignored. Consider using try-with-resources instead." |
| PMD | `category/java/errorprone.xml/ReturnFromFinallyBlock`, since PMD 1.05, priority Medium (3) | "Avoid returning from a finally block, this can discard exceptions." |
| SpotBugs | **no such pattern** | SpotBugs' `FI_` prefix is the *finalizer* family (`FI_EMPTY`, `FI_USELESS`, `FI_MISSING_SUPER_CALL` and five others). Its published bug-description list has no return-from-finally pattern at all. An `FI_FINALLY_RETURN` identifier does not exist — do not cite it. |

**Unverified:** whether ErrorProne's `Finally` and PMD's `ReturnFromFinallyBlock` fire on a
*conditional* `break`/`continue`, as opposed to an unconditional `return`. Neither tool is
installed here and both published descriptions mention only `return` and `throw`. Guide 16 owns
static-analysis tooling.

The tool-free control that actually works in review: **a `finally` block may contain no `return`,
no `throw`, no `break`, no `continue` and no labelled jump.** One grep, no false negatives.

## The domain consequence

`case1SwallowedLedgerImbalance` is what a real `PaymentRun` batch writer looks like after someone
"fixed" a resource leak by moving the return into the `finally`. QuizStakes sends 7k bank
withdrawals a day out in four windows, average value 260. A swallowed `LedgerImbalanceException`
means debits did not equal credits for that window and the writer returned an entry count anyway,
so the batch was marked complete and the operator's sign-off went through. Nothing logged, nothing
alerted; the discrepancy surfaces days later as a reconciliation break against the banking
partner's payout file with no window and no timestamp to anchor it to. The correct form,
`case7aFinallyCleanupOnly`, put `window=3 booked=520.00 GBP declared=520.01 GBP delta=-0.01 GBP`
straight into the log instead.

## Diff vs the real one

"The real one" is how the JDK and production code handle cleanup, the subject being a construct.

| Dimension | This harness | The real thing (JDK / production practice) |
|---|---|---|
| Edge cases | seven demonstrated cases, all synchronous, single-threaded, one exception type per path | a `finally` also loses `Error`s — `StackOverflowError`, `OutOfMemoryError` and `ThreadDeath` all travel the `any` handler; and an `InterruptedException` swallowed in `finally` also loses the interrupt status unless re-set |
| Intrinsics | none; `finally` has no runtime presence to intrinsify | C2 does not treat exception paths as intrinsics either, but it *does* deoptimise on a cold throw and may recompile without the handler; the dead `astore` in case 1 is eliminated by the JIT, which is why the swallowing costs nothing measurable and never shows up in a profile |
| Serialization | the three exceptions carry `serialVersionUID = 1L` and a message only; no structured context to serialise | order 15's hierarchy serialises a `FailureDetail` with an `ErrorCode` and an immutable `Map<String, Serializable>` context, so a swallowed exception would at least have had something to persist |
| Null policy | none needed; `Money.of` and the records take no nulls in this harness and would NPE at `BigDecimal` construction | `Throwable.addSuppressed` throws NPE on a null argument and `IllegalArgumentException` if you suppress a throwable with itself; try-with-resources' synthesised code handles a null resource by skipping the `close()` |
| Thread safety | none; all seven cases are single-threaded by construction | the same bug in a `stakeSettlementWorker` pool is worse, not better: the swallowed exception never reaches the `Thread.UncaughtExceptionHandler`, so the one place that would have logged it is bypassed, and an `ExecutorService` task returns a `Future` that completes *successfully* |
| Allocation tricks | none; the exceptions capture full stack traces | order 16's stackless exception (`writableStackTrace = false`) skips `fillInStackTrace` — worth noting that a swallowed exception paid for its stack-trace capture and then had it thrown away, so the bug is a pure cost |
| Why the JDK bothers | it does not: `finally` predates try-with-resources and the JDK's own code has been migrated away from it | Java 7's JEP-less try-with-resources exists precisely because hand-written `finally` cleanup got this and the suppression case wrong constantly; `Cleaner` (order 20) exists for the case where there is no lexical scope to hang a `finally` on |

The section-wide §4.6 diff table is leaf 4.6.9 and lives in
[`03j-cleaner-and-diff.md`](03j-cleaner-and-diff.md).

## The seven cases

| # | The `try` did | The `finally` did | The caller observed | What was destroyed |
|---|---|---|---|---|
| 1 | threw `LedgerImbalanceException` | `return size() * 2` | `4`, a plausible success | the exception, with no record anywhere |
| 2 | `return size() * 2` (= 4) | `return -1` | `-1` | the `try` block's return value 4 |
| 3a, 3b | `return entries` (= 4); `return total` (`520.00 GBP`) | `entries = -999`; reassigned `total` to `1520.00 GBP` | `4`; `520.00 GBP` | nothing — value and reference were both already copied to the return slot |
| 3c | `return failures` (1 element) | `failures.add(…)` | 2 elements, including `ADDED_IN_FINALLY` | nothing was destroyed, but the caller's list was mutated after the `return` |
| 4a | threw on window 3 | `break` (guarded by an `if`) | `window 1 wrote 4 entries`; loop ended early | the exception, and windows after the failure |
| 4b | threw on window 3 | `continue` | `8`, two windows counted | the exception; window 3 silently absent from the total |
| 5 | threw; `catch` ran and threw `IllegalTransitionException` | `return "AA-801 ACTIVATED"` | `AA-801 ACTIVATED` | the `catch` block's exception |
| 6 | threw `LedgerImbalanceException`; inner `try` threw `IllegalTransitionException` | inner `finally` returned `"BDP-101 SETTLED"` | `BDP-101 SETTLED` | both exceptions |
| 7a | threw | cleanup only | `LedgerImbalanceException` with window, totals and delta | nothing — correct |
| 7b | threw | `close()` via try-with-resources | `LedgerImbalanceException`, after `close` ran | nothing — correct, and the bug is unexpressible |

## Pitfalls

### Believing a `return` in `finally` "overrides" the `try` block's return

**Wrong**
```java
static int entriesWritten(PaymentRun run) {
    try {
        return writeLedgerEntries(run);        // throws for window 3
    } finally {
        return run.withdrawals().size() * 2;  // "just overriding the return value"
    }
}
```

Real output for the imbalanced window-3 run: `caller sees: 4`. No exception, no log line, no
trace. "Overriding a return value" describes case 2 only; case 1 has no return value to override,
because the `try` block never produced one.

**Right**
```java
static int entriesWritten(PaymentRun run) {
    int fallback = run.withdrawals().size() * 2;
    try {
        return writeLedgerEntries(run);
    } finally {
        System.out.println("    [finally] payout file closed, fallback would have been "
                + fallback);
    }
}
```

The `finally` completes normally, so the `try` statement completes abruptly for the pending `throw`.
Real output: `LedgerImbalanceException: LEDGER_IMBALANCE window=3 booked=520.00 GBP declared=520.01
GBP delta=-0.01 GBP`. If a fallback genuinely is the policy, express it in a `catch` block where the
exception is visible, never in `finally`.

**Why people believe it:** case 2 is the first one everybody meets, usually as a puzzler, and "the
`finally` return wins" is a correct summary *of case 2*. Generalising from "wins over the other
return" to "overrides the result" loses the fact that a thrown exception is also a result, and one
the JLS treats as a peer reason, not as privileged.

### Believing a `catch` block's exception is safe from a `finally` return

**Wrong**
```java
try {
    writeLedgerEntries(run);
    return "AA-801 ACTIVATED";
} catch (LedgerImbalanceException e) {
    throw new IllegalTransitionException("PaymentRun.APPROVED", "PaymentRun.SETTLED");
} finally {
    return "AA-801 ACTIVATED";   // "the catch already handled it, this is the happy path"
}
```

Real output: the `catch` block's `println` fires, then `caller sees: AA-801 ACTIVATED`. The wrapped
exception was constructed, its stack trace captured, and it was discarded.

**Right** — single exit outside the whole statement, `finally` reduced to cleanup:
```java
String status;
try (PayoutFile file = new PayoutFile(run.window())) {
    writeLedgerEntries(run);
    status = "AA-801 ACTIVATED";
} catch (LedgerImbalanceException e) {
    throw new IllegalTransitionException("PaymentRun.APPROVED", "PaymentRun.SETTLED");
}
return status;
```

Real output: `[open]`, `[close]`, then
`IllegalTransitionException: ILLEGAL_TRANSITION PaymentRun.APPROVED -> PaymentRun.SETTLED`.

**Why people believe it:** the mental model is a pipeline — `try` fails, `catch` handles, `finally`
tidies — in which nothing is left in flight by the time `finally` runs. JLS §14.20.2 has a clause
for this case precisely because there *is*: the `catch` block's own abrupt completion, reason R.

### Believing that mutating the returned variable in `finally` changes what the caller sees

**Wrong**
```java
int entries = run.withdrawals().size() * 2;
try {
    return entries;
} finally {
    entries = -999;   // "the caller will get -999"
}
```

Real output: `[finally] local entries is now -999` then `caller sees: 4`. The `finally` block
genuinely did change the local, and the caller genuinely did not see it.

**Right** — the change has to be on the path that produces the return value:
```java
int entries = run.withdrawals().size() * 2;
try {
    if (!run.balances()) entries = -999;
    return entries;
} finally {
    System.out.println("    [finally] payout file closed");
}
```

Real output: `[finally] payout file closed` then `caller sees: -999`. Know the exception, though:
for a **mutable** return value the folklore is accidentally right, because what got copied was the
reference — `case3cMutableMutationVisible` returns `[LEDGER_IMBALANCE window=3, ADDED_IN_FINALLY]`.

**Why people believe it:** they have seen the mutable case work, and it is a short step from
"`failures.add(…)` in a `finally` changes what the caller sees" to "the `finally` runs before the
caller gets the value, so it can change it". Case 3a's offsets `12`–`13`, `iload_1; istore_2`, are
where the belief breaks: the copy happens before the `finally` body, not after.

## Cheat sheet

| Fact | Value |
|---|---|
| Rule | JLS §14.20.2 — `finally` completing abruptly for reason S discards pending reason R; the reasons (JLS §14.1) are `break`, `continue`, `return`, a `throw` |
| Destroyed by `return` in `finally` | the `try` block's exception, the `try` block's return value, the `catch` block's exception, the `catch` block's return value |
| Runtime construct? | no — `javac` duplicates the `finally` body per exit path, plus one `any` (`catch_type` 0) exception-table entry over the `try` range |
| Instruction where the exception dies | the handler's `astore` into a slot never read again; the correct form ends `aload_N; athrow` |
| Mutating the returned local in `finally` | invisible for primitives and immutables (value already copied to the return slot); visible for mutable objects (the reference was copied) |
| Checked exception in `try` + `return` in `finally` | no `throws` clause needed — JLS §11.2.2 conditions every clause on the `finally` completing normally |
| `javac` | silent by default; `-Xlint:finally` warns "finally clause cannot complete normally", but misses conditional jumps and all mutation cases |
| Third-party | ErrorProne check `Finally` (WARNING, FragileCode); PMD `errorprone.xml/ReturnFromFinallyBlock` |
| SpotBugs | no such pattern; `FI_` is the finalizer family |
| `jsr`/`ret` | illegal in class file version 51.0+ (Java 7+), JVMS §4.9.1; described in §4.10.2.5 as the ≤50.0 technique |
| Review rule, no false negatives | no `return`, `throw`, `break`, `continue` or labelled jump inside any `finally` |
| Structurally immune | try-with-resources — cleanup lives in `close()`, which cannot abruptly complete the caller's `try` |

## Self-test

**Q1.** `case1SwallowedLedgerImbalance` returns `4` for a run that fails its double-entry check.
Name the single bytecode instruction at which the `LedgerImbalanceException` ceases to be
reachable, and say why no rethrow follows it.

<details><summary>Answer</summary>

Offset `17`, `astore_2` — the entry point of the exception-table handler covering the `try` range
`0`–`4` with type `any`. It pops the throwable into local slot 2, and slot 2 is never loaded again:
no `aload_2`, no `athrow`. The rethrow is absent because `javac` duplicated a `finally` body ending
in `ireturn` (offset `29`) into the handler, making the rethrow unreachable, and javac does not emit
unreachable code. Compare `case7aFinallyCleanupOnly`, ending `38: aload_3` / `39: athrow`.

</details>

**Q2.** One of these mutations is visible to the caller and one is not. Which, and what single fact
explains both?

```java
static Money a(PaymentRun run) { Money t = run.sum();
    try { return t; } finally { t = t.plus(Money.of("1000.00")); } }
static List<String> b(PaymentRun run) { List<String> f = new ArrayList<>();
    try { return f; } finally { f.add("ADDED_IN_FINALLY"); } }
```

<details><summary>Answer</summary>

`a` returns `520.00 GBP`, the original — invisible. `b` returns a list containing
`ADDED_IN_FINALLY` — visible. One fact: `return expr;` copies the resulting **value** to the return
slot before the `finally` body runs, and Java copies values, never variables. In `a` the copied
value is a reference to the original `Money`, so reassigning `t` rebinds the local only. In `b` the
copied value is a reference to the `ArrayList`, and `f.add` mutates the object it points at — the
same object the caller receives. The bytecode is literal about it: `iload_1; istore_2` copies to a
second slot, `iload_2; ireturn` returns the copy.
[`../immutability-and-design/03-pass-by-value.md`](../immutability-and-design/03-pass-by-value.md)
owns this.

</details>

**Q3.** A colleague argues that catching and rethrowing a wrapped exception protects against the
`finally`-return bug, because the `catch` block has already dealt with the original. Refute it from
the specification.

<details><summary>Answer</summary>

JLS §14.20.2 has a clause for exactly this: "If the catch block completes abruptly for reason R,
then the finally block is executed. […] If the finally block completes abruptly for reason S, then
the try statement completes abruptly for reason S (and reason R is discarded)." The `catch` block's
own `throw` is reason R and gets no protection. `case5FinallyReturnDestroysCatchThrow` shows its
`println` in the output — it ran, it built its `IllegalTransitionException` — and the caller still
sees `AA-801 ACTIVATED`. Wrapping makes the loss worse: the original is reachable only through the
wrapper that was discarded.

</details>

**Q4.** `-Xlint:finally` warns about six constructs in the harness but not about
`case4aFinallyBreaksOutOfLoop`. Why not, and what does that imply about relying on it?

<details><summary>Answer</summary>

The lint's condition is the structural, definite property "finally clause cannot complete
normally". Case 4a's `break` sits inside `if (!run.balances())`, so the block *can* complete
normally on the balanced path and the check stays quiet; case 4b's bare `continue` is unconditional,
so it fires. That is backwards from what you want: real code contains guarded jumps
(`if (retriesExhausted) return partialResult;`), not bare ones. Enable it with `-Werror` as a
floor, but the rule with no false negatives is the flat one — no control-transfer statement of any
kind inside a `finally`.

</details>

**Q5.** Why is the bug structurally impossible to write with try-with-resources?

<details><summary>Answer</summary>

There is no author-written `finally` block for a `return` to live in. Cleanup lives in the
resource's `close()`, and a `return` inside `close()` returns from `close()` — it cannot abruptly
complete the caller's `try` statement. The cleanup path, the `addSuppressed` call and the rethrow
are synthesised by javac from a fixed template, so they are right by construction.
`case7bTryWithResources` prints `[open]`, `[close]`, then the `LedgerImbalanceException` intact. A
`throw` from `close()` remains a hazard, but its exception is suppressed onto the primary rather
than replacing it — order 17 owns that.

</details>

**Q6.** A `PaymentRun` writer with this bug is deployed. What is the observable production
signature, and why does no monitoring catch it?

<details><summary>Answer</summary>

There is no signature. The method returns a plausible entry count, the batch is marked complete and
the sign-off proceeds. No exception reaches a log appender, a `Thread.UncaughtExceptionHandler`, an
error-rate metric or an APM error span, because none was ever thrown out of anything; an
`ExecutorService` task's `Future` completes *successfully*. The JIT eliminates the dead `astore`, so
there is no cost signal in a profile either. It surfaces days later as a reconciliation break with
nothing to anchor it to, because the one thing that knew the window and the delta was discarded the
moment it was constructed.

</details>

## Open questions

- The exact javac release that stopped emitting `jsr`/`ret` for `finally` bodies. JVMS §4.9.1 fixes
  the *prohibition* at class file version 51.0 and §4.10.2.5 scopes the technique to ≤50.0, which
  bounds when the shape became illegal, not when javac changed. Compiling with `-target 1.4` on a
  JDK old enough to accept it and reading the `Code` attribute would settle it.
- Whether ErrorProne's `Finally` and PMD's `ReturnFromFinallyBlock` fire on a *conditional*
  `break`/`continue` rather than an unconditional `return`/`throw`. Both published descriptions
  mention only `return` and `throw`; neither tool is installed here. Running each over this harness
  — one guarded `break` (4a), one unconditional `continue` (4b) — settles it.

---

**Leaves covered:** 4.6.8 (1 leaf)
**Leaves deferred:** none
**Diagrams included:** none
**Target version:** Java 21 LTS
**Lines:** 899
