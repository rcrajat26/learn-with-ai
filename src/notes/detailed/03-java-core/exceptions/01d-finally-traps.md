# 03 Java Core — The three ways `finally` betrays you — BASICS (§1.20, 1.20.16–1.20.21)

**Target version: Java 21 LTS.** | **Part 1 of 5** | [Index](../00-index.md)
Previous: [try-with-resources and suppression](01c-try-with-resources-and-suppression.md) · Next: [Catch discipline and top-level handling](01e-catch-discipline-and-top-level-handling.md)

`finally` has exactly one guarantee: it runs on every way a `try` block can exit. Nobody designed the three traps below — they all fall out of that one guarantee colliding with three separate, ordinary pieces of Java control flow: `return`'s "abrupt completion with a value" semantics, `throw`'s "abrupt completion with a `Throwable`" semantics, and `System.exit`'s "the JVM stops running Java code right here" semantics. Each collision resolves the same way: whatever the `finally` block does *last* wins, and whatever was already in flight is discarded without a trace. Everything below is measured against **Oracle JDK 21.0.7 (21.0.7+8-LTS-245, macOS aarch64)**, with a cross-check against JDK 8u202's and JDK 17.0.15's compilers for the one claim that could plausibly have changed. The relevant JLS sections are 14.1 (normal and abrupt completion), 14.17 (`return`), and 14.20.2 (execution of `try`-`finally`).

The closest neighbour to this file is [`01c-try-with-resources-and-suppression.md`](01c-try-with-resources-and-suppression.md): it owns the *fix* — try-with-resources, its reverse close order, and the suppression mechanism that keeps a body exception primary while a close failure rides along under it — and it owns the pre-Java-7 `finally { conn.close(); }` idiom as the motivating defect for that fix. This file owns the *general* shape of that defect: the three ways any `finally` block, not just a resource-closing one, can destroy whatever the `try` was in the middle of doing, and the fourth way the whole mechanism can be skipped outright. Where `01c` shows one instance of "a throw from `finally` replaces the original exception" using `conn.close()` as the culprit, this file shows the general rule and adds `return`, `break`/`continue`, and process termination to the list.

The resource types are the same as `01c`'s: `LedgerConnection`, an `AutoCloseable` handle on the double-entry ledger, and `PaymentRunFileWriter`, an `AutoCloseable` writer for the batched payout file the banking partner ingests four times a day.

---

## 1. `return` inside `finally` discards both the in-flight exception and the `try` block's return value (1.20.16)

`[TRAP]` `[PROVE]` `[BYTECODE]` The claim usually stated as "a `return` in `finally` swallows everything" needs the actual bytecode to be convincing, not the sentence — and it needs the *second* half of the claim, which is easy to forget: it swallows a computed return value from the `try` just as completely as it swallows an exception.

### Mental model

A `try`/`finally` pair has, from the outside, exactly one way to complete: normally with one value, or abruptly with one `Throwable`. Whatever the `try` block was doing to complete — computing `-1`, computing `4200`, throwing `InsufficientFundsException` — is a completion *in progress* when `finally` starts. If `finally` itself completes abruptly by returning a value, JLS §14.20.2 says the `try`-`finally` statement completes that way, full stop, and the `try` block's own completion is discarded as though it had never happened. This is not a special rule for exceptions and a different special rule for return values; it is one rule, "the `finally` block's own abrupt completion overrides the `try` block's," applied uniformly to both.

### Why it exists

Nobody designed this as a feature. `finally`'s entire contract is "runs on every exit path, including exceptional ones," and `return`'s entire contract is "completes the enclosing method abruptly, right here, with this value." The language has to pick one behavior when both are true simultaneously — a `finally` block executing while a `try` block's own completion is still pending — and the choice the JLS makes is temporal: whichever completion happens *later* in fully working out the statement wins, and `finally` runs last by definition. There is no alternative rule that would not itself be surprising in some other way, and the actual defect is not the rule but that `javac`, `checkstyle` and every IDE let you write a `return` inside `finally` with no warning by default.

### When to reach for it, and when not

Never, for `return`. There is no legitimate use of `return` inside `finally` in application code — the one theoretical case, deliberately overriding a `try`'s outcome, is better expressed as an explicit `if` inside the `finally` that decides whether to override, with a comment explaining why, rather than a bare `return` that overrides unconditionally and silently. Every mainstream static analyser treats a `finally`-block `return` (and, by the same logic, `throw`, `break`, and `continue`) as a defect on sight. Error Prone flags it under its **`Finally`** check, with the message "If you return or throw from a finally block, then values returned or thrown from the try-catch block will be ignored"; SonarQube flags it as rule **`S1143`**, "Jump statements should not occur in `finally` blocks." Both fail a build by default in a reasonably strict CI configuration, and both fire on the same four statement kinds (`return`, `throw`, `break`, `continue`) inside a `finally` block, with no legitimate exception ever excluded from the flag. **Unverified:** the exact SpotBugs bug-pattern identifier for this specific shape — SpotBugs is known to flag related `finally`-block misuse, but the precise pattern code was not confirmed against the SpotBugs pattern list in this pass.

### How it works

`[BYTECODE]` The exact shape, measured with `javap -c -p -v` on JDK 21.0.7. Source:

```java
static int swallow(int stakeMinor) {
    try {
        throw new InsufficientFundsException("CLIENT_CASH_AVAILABLE too low");
    } finally {
        return -1;
    }
}
```

Output:

```
static int swallow(int);
  descriptor: (I)I
  flags: (0x0008) ACC_STATIC
  Code:
    stack=3, locals=2, args_size=1
       0: new           #25   // class InsufficientFundsException
       3: dup
       4: ldc           #27   // String CLIENT_CASH_AVAILABLE too low
       6: invokespecial #29   // Method InsufficientFundsException."<init>":(Ljava/lang/String;)V
       9: athrow
      10: astore_1
      11: iconst_m1
      12: ireturn
    Exception table:
       from    to  target type
           0    11    10   any
```

Read it instruction by instruction. Offsets 0–9 are the `try` block: allocate `InsufficientFundsException`, call its constructor with the message, and `athrow` it. That `athrow` never returns control to offset 10 the normal way — it completes abruptly, and the JVM looks for a handler covering the range it threw from. The exception table's one row says: for any exception thrown between offset 0 and offset 11 (`from 0 to 11`), of `type any` — not a specific class, `any` — jump to offset 10. That `any` handler is the JVM-level realization of `finally`: it catches everything, unconditionally, because `finally` must run regardless of what kind of `Throwable` is in flight, or none at all.

At offset 10, `astore_1` stores the caught exception — the live `InsufficientFundsException` object, message and all — into local variable slot 1. And that is the last anything in this method ever does with slot 1. Offsets 11–12 are `iconst_m1; ireturn`: push the constant `-1`, return it. Nothing reads slot 1. Nothing rethrows it. Nothing logs it. It is not caught-and-rethrown, not suppressed via `addSuppressed`, not chained via `initCause`; it is stored into a local that goes out of scope when the method returns, and the object becomes ordinary unreachable garbage. Measured, running `swallow(500)` prints:

```
swallow returned: -1
```

with no exception, no stack trace, no log line anywhere — because none was ever produced past `athrow`. The `-1` is the `finally` block's own `return`, which is a `ireturn` instruction that completes the method right there; the `try` block's `athrow` never got a chance to finish propagating.

![D-055 — `return` inside `finally` swallows everything](../diagrams/D-055-return-in-finally.svg)

**D-055** — Two frames. The left frame shows the `swallow` source above the fold; the right frame shows the exact `javap` listing measured above, with the `any` handler at offset 10 annotated to show `astore_1` storing the in-flight exception into a slot nothing else in the method reads. Both frames name the same values so the figure and the text agree: the returned value is `-1`, and the discarded object is `InsufficientFundsException: CLIENT_CASH_AVAILABLE too low`.

The bytecode-level mechanics of *why* the exception table is shaped this way — including the three-copy duplication a `try`/`catch`/`finally` compiles to, versus the single `any`-handler shape a bare `try`/`finally` compiles to — is [`03a-internals-finally-and-twr-desugaring.md`](03a-internals-finally-and-twr-desugaring.md)'s territory; this file uses the reading above only to explain the language-level behavior. One piece of that duplicated shape is worth showing here because it is the bridge to concept 2 below. Measured on the same JDK, source `try { return stakeMinor / 10; } catch (ArithmeticException e) { return 0; } finally { audit(stakeMinor); }`:

```
Exception table:
   from    to  target type
       0     5    11   Class java/lang/ArithmeticException
       0     5    20   any
      11    14    20   any
```

with `audit(stakeMinor)` called three times in the compiled method — once at PC 5–6 on the normal-exit path, once at PC 14–15 on the catch-block path, and once at PC 21–22 inside the `any`-handler copy. Note the second `any` row: `from 11 to 14 target 20` guards the **catch block itself**, offsets 11 through 14 — so `audit` still runs even if the `catch` block's own code throws. That is why a `finally` is guaranteed to run when a `catch` throws, and it is the mechanism concept 2 below relies on when it says a throwing `finally` "replaces the same way" regardless of whether the original exception came from the `try` body or from a `catch` block that itself threw.

**Version behavior.** Compiling the exact `swallow` shape above with `javac` from JDK 8u202, JDK 17.0.15, and JDK 21.0.7 in turn produces byte-identical instruction sequences and an identical exception table shape in all three — only the constant-pool index numbers differ, which is expected and immaterial. This trap has not moved in over a decade of `javac` releases and has no reason to.

### A concrete example

The bytecode above is the primary proof. The second half of the leaf — that `return` in `finally` also discards a *computed* return value from the `try`, with no exception involved at all — needs its own, separately measured proof, because it is easy to assume the trap is exception-specific:

```java
static int stake(int stakeMinor) {
    try {
        return stakeMinor;
    } finally {
        return -1;
    }
}

public static void main(String[] args) {
    System.out.println("stake(4200) = " + stake(4200));
}
```

Measured on JDK 21.0.7:

```
stake(4200) = -1
```

No exception was ever in play here — the `try` block completed *normally*, having computed `4200` as its return value. That computed value is discarded exactly as completely as the `InsufficientFundsException` was above, by the identical mechanism: the `try` block's `ireturn 4200` is an abrupt completion in progress, `finally`'s own `ireturn -1` supersedes it per the same JLS §14.20.2 rule, and `4200` is never observed by anything — not even transiently in a caller-visible way. `4200` is computed, loaded onto the operand stack, and then simply never used, because control transfers into the `finally` block's own code before the `try` block's `return` instruction can complete the method.

### The gotcha

**Pitfall:** believing that only a `throw`-then-`return` combination triggers this, and that a plain `try { return x; } finally { return y; }` with no exceptions anywhere is somehow safer because "nothing is being caught." Symptom: a method that appears, on a normal, non-exceptional run, to always return the `finally` block's value regardless of what the `try` computed — usually surfacing as "this method always returns `-1`/`false`/`null` no matter what I do to the input," debugged for an hour before anyone thinks to look at the `finally` block, because the natural instinct is to suspect the `try` body's logic first. Fix: never write `return` inside a `finally` block. If cleanup logic in a `finally` needs to run and it happens to compute something, store it to a local and let the `try`/`catch` path's own `return` carry the real result; do not let the `finally` block issue the `return` statement itself. Enable Error Prone's `Finally` check or SonarQube `S1143` in CI so this is a build failure rather than a debugging session.

> **Definition.** A `return` statement executed inside a `finally` block completes that `finally` block abruptly with a value, and per JLS §14.20.2 that completion supersedes whatever the corresponding `try` block was already doing to complete — whether that was returning a different value or propagating a `Throwable` — discarding it with no trace: not caught, not suppressed, not chained, simply never observed again by anything in the program.

---

## 2. A `finally` block that throws replaces the original exception the same way (1.20.17)

The mechanism is identical to concept 1's — `finally`'s own abrupt completion supersedes the `try` block's — with `throw` in place of `return`. The reason it earns separate billing rather than a one-line footnote is that a throwing `finally` is far more common in real code than a `return`-in-`finally`, because it usually is not written directly: it is a `close()` call, a network flush, or a database commit inside the `finally` block, any of which can throw for reasons that have nothing to do with the primary work the method was doing.

### Mental model

Same envelope-and-letter picture as `01c` concept 2, run backwards. There, try-with-resources clips the close failure to the back of the envelope as a suppressed note, keeping the body's exception as the main letter. Here, with a hand-rolled `finally` that throws, there is no clip — the new letter doesn't attach to the old one, it replaces it in the envelope entirely, and the old letter is thrown away, not filed anywhere.

### Why it exists

Not a restatement of "why suppression exists" — the narrower, prior fact. Per JLS §14.20.2, an exception thrown from a `finally` block unconditionally replaces any exception already propagating out of the corresponding `try` block (or `catch` block — see the second `any` row in concept 1's three-row exception table). This is the raw language rule that try-with-resources and its `addSuppressed` machinery exist specifically to paper over for `AutoCloseable` resources; concept 1's mechanism is a `return` doing the same thing, and this is a `throw` doing it.

### When you would still see this, and why you should not write it

Any `finally` block whose own cleanup code can throw a checked or unchecked exception is exposed to this, not only the classic `conn.close()` case `01c` already measured. A `QuizStakes` example that is not resource-closing at all: a `finally` block that calls `VoidStake` on the Quiz Engine to unwind a reservation after a body failure, where `VoidStake` itself can throw if the round has already settled. There is no legitimate reason to let that throw propagate raw from the `finally`; the fix, shown below, is to catch it and either attach it as suppressed or log it explicitly, never let it fly free.

### How it works

Measured on JDK 21.0.7, a `finally` block that itself throws, layered on top of a `try` block that was already propagating a different exception:

```java
static void closeRedeal(int stakeMinor) {
    try {
        throw new LedgerImbalanceException(
            "run PR-2026-08-29 debits 4820.00 credits 4819.67");
    } finally {
        throw new IllegalStateException(
            "quiz engine VoidStake failed for round R-88123");
    }
}

public static void main(String[] args) {
    closeRedeal(420);
}
```

Run uncaught, this printed:

```
Exception in thread "main" java.lang.IllegalStateException: quiz engine VoidStake failed for round R-88123
	at ThrowingFinally.closeRedeal(ThrowingFinally.java:9)
	at ThrowingFinally.main(ThrowingFinally.java:13)
```

**The `LedgerImbalanceException` is gone.** Read the trace for what is absent, not just what is present: there is no `Suppressed:` line — this is not `addSuppressed` behavior, because nothing in this code called it. There is no `Caused by:` line either — this is not exception chaining, because nothing called `initCause`. The `LedgerImbalanceException` object was constructed, began propagating out of the `try` block via `athrow`, and was replaced in full — by the identical `any`-handler mechanism concept 1 walked — the instant the `finally` block's own `throw` executed. `getSuppressed()` on the caught `IllegalStateException`, checked directly, returns an empty array. The `LedgerImbalanceException` still exists as an object on the heap until garbage collected, but nothing retains a reference to it and nothing in the printed trace names it. For a payment run in the middle of 7k batched bank withdrawals a day, this converts "the ledger was out of balance by 0.33 on run PR-2026-08-29" into "the quiz engine's `VoidStake` call failed for round R-88123" — with no trace anywhere of the balance problem that was the actual incident.

**The two fixes.** First, and preferred whenever the resource is `AutoCloseable`: try-with-resources, exactly as `01c` measured, which suppresses the close failure under the primary rather than replacing it. Second, where try-with-resources does not apply — because the cleanup call is not a `close()` on an `AutoCloseable`, as with the `VoidStake` example above — a hand-written guard around the cleanup, structured the same way `01c` concept 3 shows the compiler's own equivalent:

```java
static void closeRedeal(int stakeMinor) {
    RuntimeException primary = null;
    try {
        throw new LedgerImbalanceException(
            "run PR-2026-08-29 debits 4820.00 credits 4819.67");
    } catch (RuntimeException e) {
        primary = e;
        throw e;
    } finally {
        try {
            voidStake(stakeMinor);
        } catch (Throwable cleanupFailure) {
            if (primary != null) {
                primary.addSuppressed(cleanupFailure);
            } else {
                if (cleanupFailure instanceof RuntimeException re) {
                    throw re;
                }
                throw new IllegalStateException(cleanupFailure);
            }
        }
    }
}
```

catching `Throwable` here specifically because `voidStake` may throw something outside the `RuntimeException` hierarchy that the surrounding method signature cannot declare, and because a cleanup step that is itself allowed to fail silently on an `Error` is worse than one that at least tries to attach it; the general rule against catching `Throwable` at ordinary call sites is [`01e-catch-discipline-and-top-level-handling.md`](01e-catch-discipline-and-top-level-handling.md)'s territory, and this narrow, cleanup-guard exception to it is exactly the shape that file's discussion of `Throwable` should be read against.

**The `break`/`continue` variant, verified.** An abrupt `break` or `continue` out of a `finally` block inside a loop discards an in-flight exception by the identical mechanism — `break`/`continue` are abrupt completions too, and JLS §14.20.2 does not distinguish them from `return` or `throw` for this purpose. Measured, a loop over a batch of stakes where the body throws on a zero stake and the `finally` deliberately breaks out of the loop on that same condition:

```java
static String reconcile(int[] stakeMinorBatch) {
    for (int stakeMinor : stakeMinorBatch) {
        try {
            if (stakeMinor == 0) {
                throw new LedgerImbalanceException(
                    "zero stake in batch, run PR-2026-08-29");
            }
            System.out.println("body: reconciled " + stakeMinor);
        } finally {
            if (stakeMinor == 0) {
                System.out.println("finally: breaking out, stakeMinor=0");
                break;
            }
        }
    }
    return "reconcile completed with no exception propagated";
}

public static void main(String[] args) {
    System.out.println(reconcile(new int[]{100, 0, 200}));
}
```

printed:

```
body: reconciled 100
finally: breaking out, stakeMinor=0
reconcile completed with no exception propagated
```

The `LedgerImbalanceException` thrown for the zero-stake entry never surfaces anywhere — not as a caught exception, not as an uncaught trace, not as a log line. `reconcile` runs to completion and returns its normal string as though every entry in the batch had been fine. This is the same defect as concept 1 and the `throw`-replaces-`throw` case above, wearing a third costume: a `finally` block containing a `break` (or, identically, a `continue`) is exactly as capable of discarding an exception as one containing a `return` or a `throw`, and it is arguably the hardest of the three to spot in review, because `break` inside a `finally` inside a loop does not look like it is "returning" anything at all.

### Diagram

No separate diagram for this concept: it is D-055's mechanism (concept 1's `any`-handler-supersedes-completion rule) with `throw` and `break`/`continue` substituted for `return`, and a second figure showing the identical exception-table shape with a different abrupt-completion instruction at the end would draw nothing new.

### The gotcha

Already stated above in the "how it works" section as the operational failure mode, per the `[TRAP]` obligation being on 1.20.16 and 1.20.21 rather than 1.20.17 — this leaf's pitfall is folded into the `Pitfalls` section's second entry below rather than repeated inline, since it is the same shape as concept 1's with the trigger swapped.

> **Definition.** An exception thrown from a `finally` block, or a `break`/`continue` executed inside one, completes that `finally` block abruptly and — per JLS §14.20.2, by the identical mechanism that makes a `finally`-block `return` supersede the `try` block's completion — replaces any exception already propagating from the corresponding `try` or `catch` block, with no `Suppressed:` line and no `Caused by:` chain; only try-with-resources's compiler-generated `addSuppressed` pattern, or a hand-written equivalent guard, prevents the replacement.

---

## 3. `System.exit` in a `try` block skips `finally` entirely (1.20.21)

`[TRAP]` `[PROVE]`

### Mental model

`finally`'s "runs on every exit path" guarantee is a guarantee about *Java control flow* — every way a `try` block can complete as far as the language and the bytecode verifier are concerned. `System.exit` is not a way for a `try` block to complete; it is a request that terminates the entire JVM process, which stops running Java bytecode altogether, `finally` blocks included, at the moment the request is honored. There is no completion for `finally` to react to, because the method that contains the `finally` never finishes executing in any sense the language defines.

### Why it exists

This is the sharpest form of the same underlying idea running through this whole file: `finally`'s guarantee has an unstated boundary — "every way *the program* can exit this block," not "every way the process can end." `System.exit` calls `Runtime.exit`, which invokes `Shutdown.exit`, which runs registered shutdown hooks and then halts the JVM. None of that machinery re-enters or unwinds through the stack frame containing the `try`/`finally` at all; the call to `System.exit` simply never returns to its caller in the same thread, so the enclosing `finally` block's code is never reached the ordinary way.

### When to reach for it, and when not

`System.exit` belongs at the outermost edge of a standalone process — a batch job's `main`, a CLI tool signalling failure to its shell via exit code — called after every resource the process owns has already been explicitly closed, never nested inside a `try` block whose `finally` is expected to run cleanup. Never call it from inside a framework-managed component such as a Spring bean, a servlet, or a background worker thread inside a larger application, because it terminates the entire JVM process, taking down every other request or job the process was serving. The operational shape this bites in practice: a `PaymentRun` worker thread that detects a fatal condition — the ledger connection reporting a corrupted state, say — and reacts by calling `System.exit` on a fatal condition from inside a `try` block that holds an open `LedgerConnection` and a `PaymentRunFileWriter`. The `finally` meant to close both, or the try-with-resources meant to close both, never runs; the ledger connection is left unclosed at the pool, and the payout file the banking partner's next ingest window expects is left half-written, because the writer's buffered bytes were never flushed.

### How it works

`[PROVE]` Four measurements, in the order they build the picture.

**`finally` does not run.** Measured on JDK 21.0.7, a `try`/`finally` with `System.exit` in the body:

```java
static void closeRedeal(int stakeMinor) {
    LedgerConnection ledger = new LedgerConnection();
    try {
        System.out.println("body: fatal condition detected on PaymentRun PR-2026-08-29, exiting");
        System.exit(1);
    } finally {
        System.out.println("finally: cleanup done");
    }
}
```

printed:

```
body: fatal condition detected on PaymentRun PR-2026-08-29, exiting
```

with process exit code `1`. `"finally: cleanup done"` never printed. Not delayed, not reordered — never executed at all.

**A try-with-resources `close()` does not run either.** Measured, the identical body wrapped in a try-with-resources over `LedgerConnection`:

```java
try (LedgerConnection ledger = new LedgerConnection()) {
    System.out.println("body: fatal condition detected on PaymentRun PR-2026-08-29, exiting");
    System.exit(1);
}
```

printed the same single line, with no `"close: LedgerConnection"` line — confirming that try-with-resources gives no protection here either, because its compiler-generated cleanup is a `finally`-equivalent, and `finally`-equivalents are exactly what `System.exit` skips. This is the one place in the whole file where try-with-resources is not a fix: it fixes the exception-replacement defect of concepts 1 and 2, but a process-terminating call inside the body defeats it by the same mechanism it defeats a hand-written `finally`.

**A registered shutdown hook does run.** Measured, a `Runtime.getRuntime().addShutdownHook` registered before the `exit` call:

```java
Runtime.getRuntime().addShutdownHook(new Thread(() ->
    System.out.println("shutdown hook: flushing PaymentRunFileWriter for PR-2026-08-29")));
System.out.println("body: fatal condition detected, exiting");
System.exit(1);
```

printed:

```
body: fatal condition detected, exiting
shutdown hook: flushing PaymentRunFileWriter for PR-2026-08-29
```

with exit code `1`. `Runtime.exit` runs every registered shutdown hook, each in its own thread, as part of the process's normal shutdown sequence before the JVM actually halts — `System.exit` and a plain `return` from `main` both trigger this same shutdown sequence. This is the load-bearing half of the leaf: a shutdown hook is not a `finally` block and is registered as an API rather than written inline at the call site, so it is the only cleanup mechanism a process retains once `System.exit` has been called. `Runtime.addShutdownHook`, its threading model, ordering guarantees (there are none between hooks registered independently — they may run concurrently with each other), and its interaction with `Thread.UncaughtExceptionHandler` are [`01e-catch-discipline-and-top-level-handling.md`](01e-catch-discipline-and-top-level-handling.md)'s full treatment; this file states only that the hook runs, which is the fact that bears on the `finally` trap.

**`Runtime.getRuntime().halt()` skips even the shutdown hook.** Measured, the identical shutdown-hook setup with `halt(2)` in place of `exit(1)`:

```java
Runtime.getRuntime().addShutdownHook(new Thread(() ->
    System.out.println("shutdown hook: flushing PaymentRunFileWriter for PR-2026-08-29")));
System.out.println("body: catastrophic condition, halting");
Runtime.getRuntime().halt(2);
```

printed:

```
body: catastrophic condition, halting
```

with exit code `2`. The shutdown hook never ran. `halt` is documented to forcibly terminate the JVM, and measured, it terminates it hard enough to skip the one cleanup mechanism `System.exit` itself preserves. `halt` exists for the case where the shutdown sequence itself is what is misbehaving — a shutdown hook that hangs, or a `System.exit` call that never returns because a hook is stuck — and calling it from ordinary application code to skip cleanup "because it is faster" trades a correctness guarantee for a speed difference nobody asked for.

| Exit mechanism | `finally` runs | try-with-resources `close()` runs | Shutdown hook runs |
|---|---|---|---|
| `System.exit(n)` | No | No | Yes |
| `Runtime.getRuntime().halt(n)` | No | No | No |
| Normal return from `main` | Yes | Yes | Yes |
| Uncaught exception from `main` | Yes | Yes | Yes |

### Diagram

No diagram for this concept: the evidence is four short programs and their measured stdout, laid out in the table above, and a picture of "code after `System.exit` does not run" would only restate the table.

### A concrete example

The `PaymentRun` worker shape named above, made concrete, showing both the trap and the fix:

```java
static void runFatalShutdown(LedgerConnection ledger, PaymentRunFileWriter file, int stakeMinor) {
    if (stakeMinor < 0) {
        System.out.println("body: corrupted ledger state detected, exiting immediately");
        System.exit(70);   // EX_SOFTWARE — neither ledger nor file is ever closed
    }
    ledger.debit();
    file.write();
}
```

Against this, the same reaction with cleanup ordered before the exit rather than left to a `finally` that will never run:

```java
static void runFatalShutdownSafely(LedgerConnection ledger, PaymentRunFileWriter file, int stakeMinor) {
    if (stakeMinor < 0) {
        System.out.println("body: corrupted ledger state detected, closing resources before exit");
        try {
            file.close();
        } finally {
            ledger.close();
        }
        System.exit(70);
    }
    ledger.debit();
    file.write();
}
```

The second form still uses a `finally` internally — but it runs the `finally`-protected cleanup *before* calling `System.exit`, so the cleanup executes as ordinary Java control flow, ahead of the point where the JVM stops running any of it. The general shape: `System.exit` must be the very last statement your code executes, with every resource it might have been relying on a later `finally` to close already closed by the time it is called.

### The gotcha

**Pitfall:** believing a `try`-with-resources block or a `finally` block is a safety net against a fatal error path that calls `System.exit`, because "the resource declaration is right there, so it must get cleaned up." Symptom: after a fatal shutdown in production, the connection pool reports a leaked `LedgerConnection` that was never returned, and the banking partner's next ingest window rejects a payout file that is missing its trailing record because `PaymentRunFileWriter.close()` — which flushes the final buffered bytes — never ran. Both failures show up downstream and disconnected from the `System.exit` call that caused them, often on a completely different system (the connection pool's leak detector, the banking partner's file validator) than the one that logged the fatal condition. Fix: never call `System.exit` from inside a `try` block whose `finally` (or try-with-resources) is doing work you need; close every such resource explicitly, in the same order a `finally` would have, immediately before the `exit` call — or, better, restrict `System.exit` calls to a single top-level shutdown routine that has already been handed confirmation every resource is closed, rather than letting it appear inline wherever a fatal condition is detected.

> **Definition.** `System.exit` terminates the JVM process via `Runtime.exit`, which runs every registered shutdown hook and then halts — it does not complete the calling method by any means the language defines, so no `finally` block and no try-with-resources `close()` on the call stack above it ever runs; `Runtime.getRuntime().halt()` terminates harder still, skipping shutdown hooks too, which makes a registered shutdown hook the only cleanup mechanism `System.exit` (not `halt`) leaves available to a process.

---

## Pitfalls

### Returning a default from a finally block

**Wrong**

```java
static int swallow(int stakeMinor) {
    try {
        throw new InsufficientFundsException("CLIENT_CASH_AVAILABLE too low");
    } finally {
        return -1;
    }
}

public static void main(String[] args) {
    System.out.println("swallow returned: " + swallow(500));
}
```

Measured output:

```
swallow returned: -1
```

No exception is thrown or logged anywhere. The `InsufficientFundsException` was constructed, began propagating via `athrow`, and was discarded the instant the `finally` block's own `ireturn` executed — measured in the bytecode as an `any`-handler that `astore`s the exception into a local nothing ever reads.

**Right**

```java
static int checkStake(int stakeMinor) {
    if (stakeMinor > CLIENT_CASH_AVAILABLE) {
        throw new InsufficientFundsException("CLIENT_CASH_AVAILABLE too low");
    }
    return stakeMinor;
}
```

with no `finally` in the picture at all here, because there is nothing to clean up — a `finally` should exist only when there is cleanup work to do, never as a place to compute or guard a return value. Where cleanup genuinely is needed alongside a value the `try` computed, keep the `return` inside the `try`/`catch` path and let the `finally` do cleanup with no `return` of its own:

```java
static int settleAndAudit(int stakeMinor) {
    try {
        return stakeMinor / 10;
    } catch (ArithmeticException e) {
        return 0;
    } finally {
        audit(stakeMinor);   // no return, no throw, no break, no continue
    }
}
```

**Why people believe it:** a `return` inside `finally` reads, to a first pass, as "make sure this method always returns *something* even if things go wrong" — a defensive instinct that is reasonable in spirit and catastrophic in this specific shape, because it silently discards the very failure the defensiveness was supposed to be protecting against.

### Letting a cleanup call inside `finally` throw unguarded

**Wrong**

```java
static void closeRedeal(int stakeMinor) {
    try {
        throw new LedgerImbalanceException(
            "run PR-2026-08-29 debits 4820.00 credits 4819.67");
    } finally {
        throw new IllegalStateException(
            "quiz engine VoidStake failed for round R-88123");
    }
}
```

Measured, run uncaught:

```
Exception in thread "main" java.lang.IllegalStateException: quiz engine VoidStake failed for round R-88123
	at ThrowingFinally.closeRedeal(ThrowingFinally.java:9)
	at ThrowingFinally.main(ThrowingFinally.java:13)
```

The `LedgerImbalanceException` — the actual incident — is not suppressed, not chained, not present anywhere in this output. The identical replacement happens with a `break` or `continue` inside a `finally` in a loop: measured, a batch-reconciliation loop where the `try` throws `LedgerImbalanceException` on a zero stake and the `finally` responds by `break`-ing out of the loop on that same condition ran to completion and returned its normal "no exception" result string, with the exception never surfacing anywhere.

**Right**

```java
static void closeRedeal(int stakeMinor) {
    RuntimeException primary = null;
    try {
        throw new LedgerImbalanceException(
            "run PR-2026-08-29 debits 4820.00 credits 4819.67");
    } catch (RuntimeException e) {
        primary = e;
        throw e;
    } finally {
        try {
            voidStake(stakeMinor);
        } catch (Throwable cleanupFailure) {
            if (primary != null) {
                primary.addSuppressed(cleanupFailure);
            } else if (cleanupFailure instanceof RuntimeException re) {
                throw re;
            } else {
                throw new IllegalStateException(cleanupFailure);
            }
        }
    }
}
```

Measured, run against the identical two failures: `IllegalStateException` from `voidStake` lands under `Suppressed:` on the primary `LedgerImbalanceException`, rather than replacing it.

**Why people believe it:** the success path of a `finally` block that calls cleanup logic never exercises this failure mode — `voidStake` succeeding is the common case in every test anyone is likely to write — so the replacement bug is dormant until the exact day both the `try` body and the cleanup call fail together, which is usually the worst possible day for it to happen.

### Trusting `finally` (or try-with-resources) as a safety net across `System.exit`

**Wrong**

```java
static void runFatalShutdown(LedgerConnection ledger, PaymentRunFileWriter file, int stakeMinor) {
    if (stakeMinor < 0) {
        System.out.println("body: corrupted ledger state detected, exiting immediately");
        System.exit(70);
    }
    ledger.debit();
    file.write();
}
```

with `ledger` and `file` opened via try-with-resources or a hand-written `finally` further up the call stack. Measured: calling this prints only the one `"body:"` line; neither `ledger.close()` nor `file.close()` — nor any `finally` block anywhere on the call stack — ever runs, because `System.exit` terminates the process rather than completing any method on that stack.

**Right**

```java
static void runFatalShutdownSafely(LedgerConnection ledger, PaymentRunFileWriter file, int stakeMinor) {
    if (stakeMinor < 0) {
        System.out.println("body: corrupted ledger state detected, closing resources before exit");
        try {
            file.close();
        } finally {
            ledger.close();
        }
        System.exit(70);
    }
    ledger.debit();
    file.write();
}
```

Cleanup runs as ordinary Java control flow before `System.exit` is called, rather than being left to a `finally` that the exit call would otherwise skip. Where cleanup absolutely cannot be guaranteed to run before every possible fatal exit point, register it as a shutdown hook instead — measured, a shutdown hook registered with `Runtime.getRuntime().addShutdownHook` does run following `System.exit`, though not following `Runtime.getRuntime().halt()`.

**Why people believe it:** a `try`-with-resources declaration or an explicit `finally` block sitting visibly around the code path that calls `System.exit` looks like protection, because in every other circumstance covered by this file it is — the one thing that reliably defeats it, terminating the process itself, does not look like an exceptional control-flow event the way a `throw` or a `return` does, so it is easy to overlook as a fourth way `finally` can fail to run.

---

## Cheat sheet

| Thing | Fact (Java 21 LTS) |
|---|---|
| Rule underlying all three traps | JLS §14.20.2: a `finally` block's own abrupt completion supersedes whatever the `try` (or `catch`) block was already doing to complete |
| `return` in `finally`, exception in flight | discards the exception; not caught-and-rethrown, not suppressed, not chained — stored to a dead local (`astore`) and never read |
| `return` in `finally`, `try` computed a value | discards the computed value too, with no exception involved at all — the `finally`'s `return` wins unconditionally |
| Bytecode shape (`swallow`) | `any` handler at the `athrow`'s target does `astore_1` on the exception; nothing ever reads that slot |
| Version behavior | byte-identical instruction sequence on JDK 8, 17, 21 `javac` — this trap has not moved |
| Static analysis | Error Prone check `Finally`; SonarQube rule `S1143` ("Jump statements should not occur in `finally` blocks") |
| `throw` in `finally` | replaces (not suppresses, not chains) any exception already propagating from `try` or `catch` — identical mechanism to `return`, per JLS §14.20.2 |
| `break`/`continue` in `finally` (in a loop) | discards an in-flight exception identically — measured, a loop completes normally with the exception never surfacing |
| Printed trace of a replaced exception | no `Suppressed:` line, no `Caused by:` line — the original is simply absent |
| Fix 1 (resource is `AutoCloseable`) | try-with-resources — suppresses the close failure under the primary instead of replacing it ([`01c`](01c-try-with-resources-and-suppression.md)) |
| Fix 2 (cleanup is not a `close()`) | hand-written `try { cleanup(); } catch (Throwable t) { primary.addSuppressed(t); }` guard |
| `System.exit` in a `try` block | `finally` does not run — measured |
| `System.exit` in a try-with-resources body | `close()` does not run either — measured; the one place try-with-resources gives no protection |
| `System.exit` and a shutdown hook | the hook **does** run — the only cleanup mechanism `System.exit` preserves |
| `Runtime.getRuntime().halt()` | skips `finally`, skips `close()`, and skips shutdown hooks too — measured |
| Operational failure shape | a `PaymentRun` worker calling `System.exit` on a fatal condition leaves the ledger connection unclosed and the payout file half-written |
| Safe pattern around `System.exit` | close every resource explicitly, in order, immediately before the call — `System.exit` is the last statement executed, not one nested inside a `try` whose `finally` matters |

---

## Self-test

**Q1.** Walk the `swallow` bytecode's exception table and say exactly where the thrown exception goes.

<details><summary>Answer</summary>

Measured on JDK 21.0.7: the exception table has one row, `from 0 to 11 target 10 type any`. The `try` block's code (offsets 0–9) constructs `InsufficientFundsException`, calls its constructor, and executes `athrow`. That `athrow` is inside the guarded range `0` to `11`, so the JVM transfers control to offset 10 regardless of the exception's type — `any` means the handler at that offset is `finally`'s realization at the bytecode level, unconditional. At offset 10, a single `astore_1` stores the live exception object into local variable slot 1. Nothing in the method from that point on reads slot 1: offsets 11–12 are `iconst_m1; ireturn`, which push `-1` and return it immediately. The exception is not rethrown, not logged, not suppressed via `addSuppressed`, not chained via `initCause` — it is written to a local that is never read again, and becomes ordinary unreachable garbage once the method returns and the frame is popped. Measured, calling `swallow(500)` prints `swallow returned: -1` with no trace of the exception anywhere.

</details>

**Q2.** A `try` block computes a return value with no exception involved anywhere. Does a `return` in `finally` still cause a problem, and if so, what exactly is lost?

<details><summary>Answer</summary>

Yes, and the loss is the computed value itself, with no exception in the picture at all. Measured on JDK 21.0.7: `static int stake(int stakeMinor) { try { return stakeMinor; } finally { return -1; } }` called as `stake(4200)` printed `stake(4200) = -1`. The `try` block completed normally, having computed `4200` as its intended return value — that value was loaded onto the operand stack as part of the `try` block's own `ireturn`, but that `ireturn` never got to complete the method, because JLS §14.20.2's rule that a `finally` block's abrupt completion supersedes the `try` block's applies uniformly to both an in-flight exception and an in-flight normal completion carrying a value. `4200` is never observed by anything, not even transiently — the method's actual return, as seen by `main`, is `-1`. This is the half of the leaf that is easy to forget when the trap is described purely in terms of "swallowing exceptions": the same mechanism swallows an ordinary computed result just as completely.

</details>

**Q3.** A `finally` block that throws replaces the `try` block's exception. Does the printed stack trace show the original as `Caused by:`, as `Suppressed:`, or neither — and how do you know?

<details><summary>Answer</summary>

Neither. Measured on JDK 21.0.7: `try { throw new LedgerImbalanceException("run PR-2026-08-29 debits 4820.00 credits 4819.67"); } finally { throw new IllegalStateException("quiz engine VoidStake failed for round R-88123"); }`, run uncaught, printed only `Exception in thread "main" java.lang.IllegalStateException: quiz engine VoidStake failed for round R-88123` with its own two stack frames — no `Suppressed:` block and no `Caused by:` chain anywhere in the output. Checking `getSuppressed()` on the caught `IllegalStateException` directly confirms an empty array. This is expected, not a logging gap: `Suppressed:` only appears when something has called `addSuppressed` (which try-with-resources does automatically, and which this hand-written code never called), and `Caused by:` only appears when something has called `initCause` or used the cause-taking constructor. A raw `throw` inside a `finally` block does neither — it is a plain, ordinary `athrow` that happens to be the one the JVM's `any`-handler mechanism honors last, per JLS §14.20.2, and the earlier exception is simply never referenced by the one that survives.

</details>

**Q4.** Show that a `break` inside a `finally` block, with no `return` or `throw` anywhere in the `finally`, can discard an in-flight exception.

<details><summary>Answer</summary>

Measured on JDK 21.0.7 with a batch-reconciliation loop: `for (int stakeMinor : stakeMinorBatch) { try { if (stakeMinor == 0) throw new LedgerImbalanceException("zero stake in batch, run PR-2026-08-29"); System.out.println("body: reconciled " + stakeMinor); } finally { if (stakeMinor == 0) { System.out.println("finally: breaking out, stakeMinor=0"); break; } } }` followed by `return "reconcile completed with no exception propagated";`. Run against `{100, 0, 200}`, this printed `body: reconciled 100`, `finally: breaking out, stakeMinor=0`, and then the method's own return string — with the `LedgerImbalanceException` thrown for the zero-stake entry never appearing anywhere, caught or uncaught. `break` is an abrupt completion exactly as `return` and `throw` are, and JLS §14.20.2 makes no distinction between the three for this rule: whichever abrupt (or normal) completion the `finally` block itself produces last supersedes the `try` block's pending completion. A `break` (or, identically, a `continue`) inside a `finally` inside a loop is arguably the hardest of the four shapes to spot in code review, because it does not read as "returning" or "throwing" anything — it just looks like ordinary loop control.

</details>

**Q5.** A `try`-with-resources block's body calls `System.exit`. Does the resource's `close()` run? Contrast with a hand-written `finally` doing the same close.

<details><summary>Answer</summary>

No, in both cases — measured identically for both. `try (LedgerConnection ledger = new LedgerConnection()) { System.out.println("body: fatal condition detected on PaymentRun PR-2026-08-29, exiting"); System.exit(1); }` printed only the one body line, with no `"close: LedgerConnection"` line, and the identical hand-written `try { System.exit(1); } finally { ledger.close(); }` shape behaves the same way. `System.exit` calls `Runtime.exit`, which runs the JVM's shutdown sequence (registered shutdown hooks, then halt) rather than unwinding the call stack the way a `return` or an exception does — so no method on that stack, including the one holding the try-with-resources statement, ever completes by any means the language defines, and the compiler-generated cleanup a try-with-resources block emits is, mechanically, itself a `finally`-equivalent. This is the one case in this file where try-with-resources offers no protection over a hand-written `finally`: both are equally skipped, because the thing defeating them is not an exception-handling defect but a process-termination call that neither mechanism was ever designed to survive.

</details>

**Q6.** A shutdown hook is registered before `System.exit` is called. Does it run? Does the same hook run if `Runtime.getRuntime().halt()` is called instead?

<details><summary>Answer</summary>

It runs for `System.exit`, and it does not run for `halt`. Measured on JDK 21.0.7: `Runtime.getRuntime().addShutdownHook(new Thread(() -> System.out.println("shutdown hook: flushing PaymentRunFileWriter for PR-2026-08-29")));` followed by `System.exit(1)` printed the body line, then the shutdown-hook line, then exited with code `1` — confirming `Runtime.exit`'s documented shutdown sequence runs every registered hook before halting. The identical setup with `Runtime.getRuntime().halt(2)` in place of `System.exit(1)` printed only the body line and exited with code `2`; the shutdown hook line never printed. `halt` is documented to terminate the JVM forcibly, and measured, it skips even the one cleanup mechanism `System.exit` preserves. The practical consequence: a shutdown hook is the only "finally" a process retains once `System.exit` has been called, which is why it is worth registering one for anything that must run on every normal or `System.exit`-triggered shutdown — but it offers no protection at all against a `halt()` call, deliberate or accidental, anywhere in the process.

</details>

**Q7.** Someone argues that enabling a static-analysis rule against `return` in `finally` is unnecessary because "nobody writes that on purpose." What is wrong with the argument, and which two checks would you point to?

<details><summary>Answer</summary>

The argument conflates "written on purpose" with "written knowingly." Nobody sits down intending to discard an exception, but the instinct to write `return` inside `finally` shows up specifically in code trying to be *defensive* — guaranteeing some value comes back even if something upstream went wrong — which is exactly the reasoning that produces this bug, not an exception to it. The bug is invisible on every successful run and on every test that does not specifically arrange for both the `try` block and a `finally`-level `return` to be active simultaneously, which most test suites never do, because the `try` block's own exception path is usually tested separately from any cleanup logic in `finally`. The two checks worth naming: Error Prone's `Finally` check, which fires specifically on `return`/`throw`/`break`/`continue` inside a `finally` block with the message that values or exceptions from the `try`/`catch` will be ignored; and SonarQube rule `S1143`, "Jump statements should not occur in `finally` blocks," which covers the identical set of four statement kinds. Both are cheap to enable, produce no false positives against legitimate code (because there is no legitimate use of any of the four inside a `finally`), and turn this file's entire first two concepts into a compile-time or CI-time finding instead of a production incident.

</details>

**Q8.** Contrast what happens to an in-flight `LedgerImbalanceException` under four different things a `finally` block might do: nothing (plain cleanup), `return`, `throw`, and `break` inside a loop.

<details><summary>Answer</summary>

Plain cleanup with no jump statement lets the exception propagate normally — this is the only one of the four that preserves it, and it is what every `finally` block should do. `return` inside `finally`, measured, discards it: the exception is stored to a dead local by the `any`-handler and the method returns the `finally` block's value instead, with no trace of the exception anywhere. `throw` inside `finally`, measured, replaces it: the new exception propagates in the old one's place, with no `Suppressed:` and no `Caused by:` line connecting the two. `break` inside `finally` (inside a loop), measured, discards it identically to `return` — the loop simply continues past the iteration that threw, and the method that contains it can return a completely normal-looking result as though every iteration had succeeded. All four are the same underlying JLS §14.20.2 rule — a `finally` block's own completion supersedes the `try` block's — with only the specific *kind* of superseding completion changing; `continue` inside a `finally` (inside a loop) behaves like `break` for this purpose, differing only in which iteration control resumes at rather than in whether the exception survives.

</details>

---

## Open questions

- **Unverified:** the exact SpotBugs bug-pattern identifier for a `finally`-block `return`/`throw`/`break`/`continue`. Concept 1 names Error Prone's `Finally` check and SonarQube rule `S1143` with confidence, both independently well-documented; SpotBugs is understood to flag related misuse in `finally` blocks but its specific pattern code for this exact shape was not looked up against the SpotBugs pattern catalog in this pass. What would settle it: the SpotBugs bug descriptions list (`bugDescriptions.html` in the SpotBugs distribution, or the online pattern catalog) searched for `finally`.

---

**Leaves covered:** 1.20.16, 1.20.17, 1.20.21 (3 leaves)
**Leaves deferred:** none
**Diagrams included:** D-055
**Target version:** Java 21 LTS
**Lines:** 648
