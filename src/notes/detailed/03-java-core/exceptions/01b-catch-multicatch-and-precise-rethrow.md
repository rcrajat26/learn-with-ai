# 03 Java Core — `catch` semantics, multi-catch and precise rethrow — BASICS (§1.20)

**Target version: Java 21 LTS.** | **Part 1 of 5** | [Index](../00-index.md)
Previous: [`Throwable`'s API and exception chaining](01a-throwable-api-and-chaining.md) · Next: [try-with-resources and suppression](01c-try-with-resources-and-suppression.md)

Three things, all decided at compile time and all provable with `javac` diagnostics rather than argument: which `catch` clause a thrown exception lands in, what static type a multi-catch parameter actually has, and how `javac` narrows a rethrow's declared type down from `Exception` to the two or three concrete types a `try` body can actually produce. None of this is folklore-territory — every claim below is a quoted compiler message from Oracle JDK 21.0.7 (`21.0.7+8-LTS-245`, macOS aarch64), measured in a scratch directory.

This file assumes the `Throwable` hierarchy and the checked/unchecked compile-time rule from [`01-basics.md`](01-basics.md) concept 1, and `Throwable`'s own API and chaining from [`01a-throwable-api-and-chaining.md`](01a-throwable-api-and-chaining.md). It does not cover try-with-resources, resource close order or suppression — that is [`01c-try-with-resources-and-suppression.md`](01c-try-with-resources-and-suppression.md) — nor the `finally` traps (`return` inside `finally`, a `finally` that throws, `System.exit` skipping `finally`), which are [`01d-finally-traps.md`](01d-finally-traps.md). It also does not cover the swallow anti-pattern, catching `Throwable`, or the `InterruptedException` protocol, which are [`01e-catch-discipline-and-top-level-handling.md`](01e-catch-discipline-and-top-level-handling.md).

---

## 1. `try`/`catch`/`finally` semantics, catch-clause ordering, and the two shapes of unreachable catch (1.20.9)

The model: a `try` block runs; if it throws, the JVM walks the `catch` clauses **top to bottom** and runs the body of the first one whose declared type is assignable from the thrown exception's runtime type. At most one `catch` clause ever runs. `finally`, if present, runs after that — whether a `catch` ran, whether none matched, or whether the `try` completed normally. `javac` enforces "top to bottom" as a compile-time ordering rule rather than leaving it as a runtime race, because a rule you can only observe at runtime is a rule nobody reliably gets right.

### Why it exists

Exception matching is `instanceof`-shaped, not equality-shaped: a `catch (IOException e)` also catches a `SocketTimeoutException`, because that class extends `IOException`. Once matching is a subtype test, clause order stops being cosmetic. If a broader clause sits above a narrower one, the narrower clause can never be reached — its exception type is always caught by the clause above it first. `javac` treats this as a defect worth refusing to compile rather than a style nit, because a `catch` clause that can never run is not defensive code, it is dead code that *looks* like a handler and hides the fact that nothing actually handles that case.

### When it applies, and when it does not

The unreachable-catch rule fires only when one clause's type is a **supertype** of a later clause's type. Two unrelated exception types, in either order, are both reachable — neither can ever catch the other's instances, so there is no shadowing. This is a different rule from ordinary unreachable-code analysis: `../control-flow/01e-try-and-unreachable-code.md` covers `try`/`finally` control flow and unreachable statements from the language side (dead code after a `return`, `while (true)` with no `break`), which is a **statement-reachability** analysis over the whole method body. The unreachable-catch rule here is narrower and purely **type-relational** — it only ever compares one catch clause's declared type against another's, and it fires even though every statement in the method is otherwise perfectly reachable. Do not conflate the two: a method can have a completely reachable body and still fail to compile because of one shadowed `catch`.

### How it works

Measured on JDK 21.0.7, a `catch (IOException e)` placed after `catch (Exception e)`:

```java
static void probe() throws IOException {
    try {
        throw new IOException("boom");
    } catch (Exception e) {
        System.out.println("wide");
    } catch (IOException e) {
        System.out.println("narrow");
    }
}
```

```
T1.java:9: error: exception IOException has already been caught
        } catch (IOException e) {
          ^
1 error
```

**"Already been caught"** is the precise diagnosis: not "unreachable code", not "duplicate catch" — the compiler is saying that any `IOException` reaching this `try` was already routed to the clause above. Two unrelated types compile without complaint in either order, because neither shadows the other:

```java
try {
    reserveStakeAndPersist();
} catch (java.sql.SQLException e) {
    // ledger write failed
} catch (java.io.IOException e) {
    // quiz engine socket reset
}
```

is fine, and so is the same pair reversed — `SQLException` and `IOException` share no ancestor below `Exception`, so neither clause can pre-empt the other.

The part people get wrong is the mirror-image rule, and it is a *different* mechanism from shadowing: `javac` also refuses a `catch` of a **checked** exception type that the `try` body provably cannot throw. Measured:

```java
static void probe() {
    try {
        System.out.println("no checked exception thrown here");
    } catch (SQLException e) {
        System.out.println("unreachable checked catch");
    }
}
```

```
T2.java:7: error: exception SQLException is never thrown in body of corresponding try statement
        } catch (SQLException e) {
          ^
1 error
```

This is only possible for **checked** exceptions, because the compiler tracks, per JLS §11.2.3, the exact set of checked exception types a `try` body can throw — every method call's `throws` clause is known statically. An **unchecked** exception type in the same position is legal even though the body provably cannot throw it, because unchecked types are exempted from that analysis entirely — nothing constrains what a future refactor of the body might throw, and the JLS does not require (or permit `javac` to attempt) proving an `Error` or `RuntimeException` unreachable. Measured, the unchecked equivalent of the exact same body compiles cleanly:

```java
static void probe() {
    try {
        System.out.println("no checked exception thrown here");
    } catch (IllegalStateException e) {
        System.out.println("unchecked catch of an unthrown type is legal");
    }
}
```

compiles with no diagnostic at all — `javac T3.java` exits 0. **Insight:** this asymmetry is exactly the checked/unchecked split from [`01-basics.md`](01-basics.md) concept 1 showing up as a second, independent compile-time consequence: checked exceptions are a closed, statically-known set per `try` body, so a clause for one that cannot occur is provably dead; unchecked exceptions are open-ended by design, so the same clause is defensive rather than dead, and `javac` has no basis to refuse it.

Clause scope, briefly, because it is easy to get backwards under pressure: each `catch` clause's parameter is a **new variable, scoped only to that clause's block** — `catch (IOException e)` in one clause and `catch (SQLException e)` in a sibling clause are two unrelated variables that happen to share a name; there is no shared `e` visible across the `try`. `finally`, when present, runs after whichever single `catch` clause ran (or after none did, if nothing matched, or after the `try` block itself if it completed without throwing) — the interacting traps around `finally` swallowing a `return` or an exception are [`01d-finally-traps.md`](01d-finally-traps.md)'s territory, not repeated here.

### Diagram

No diagram for this concept: the evidence is two quoted compile errors testing opposite directions of one type-relational rule, and the prose above is the clearer rendering.

### A concrete example

```java
import java.io.IOException;
import java.sql.SQLException;

public final class StakeReservationHandler {

    static void reserveStake(boolean viaBankRail) throws IOException, SQLException {
        try {
            if (viaBankRail) {
                throw new SQLException("ledger write failed for stake reservation");
            }
            throw new IOException("quiz engine socket reset during ReserveStake");
        } catch (SQLException e) {
            System.out.println("ledger persistence failure, retry via outbox: " + e.getMessage());
        } catch (IOException e) {
            System.out.println("quiz engine unreachable, void the reservation: " + e.getMessage());
        }
    }
}
```

`SQLException` and `IOException` share no relationship below `Exception`, so the order of these two clauses is a documentation choice, not a compile constraint — swap them and the file still compiles.

### The gotcha

**Pitfall:** assuming the unreachable-catch check is only about supertype-before-subtype ordering, and being surprised when a `catch` of an unthrowable *checked* type also fails to compile with no ordering involved at all — it is a single, otherwise-innocent clause, not a pair. **Interview:** "does `javac` ever reject a single `catch` clause with no other clause around it?" — yes, for a checked type the enclosing `try` cannot throw; the diagnosis is "is never thrown in body of corresponding try statement", a different message from "has already been caught", and it does not apply to unchecked types at all.

> **Definition.** A thrown exception runs at most one `catch` clause, chosen top to bottom by the first assignable declared type, followed unconditionally by `finally`; `javac` rejects a clause whose declared type is a supertype of an earlier clause's ("already been caught") and separately rejects a `catch` of a checked type the `try` body cannot statically throw ("is never thrown"), while the identical clause for an unchecked type is always legal.

---

## 2. Multi-catch (Java 7): one handler, and `e` typed at the least upper bound (1.20.10)

The model: `catch (LedgerImbalanceException | BonusIneligibleException e)` is one clause with several alternative types and one handler body, and the variable it binds is not typed as either alternative — it is typed as their **least upper bound** (LUB), the most specific common ancestor the two share. Picture it as the compiler drawing the smallest box that contains both alternative types and handing you a reference of that box's type; you get everything both alternatives have in common and nothing that belongs to only one of them.

### Why it exists

Before Java 7, an identical handler for two or more exception types had exactly one option that avoided duplicating the handler body: catch the common supertype.

```java
// pre-Java-7 shape
try {
    reserveStakeAndApplyBonus();
} catch (RuntimeException e) {
    if (e instanceof LedgerImbalanceException || e instanceof BonusIneligibleException) {
        logAndReject(e);
    } else {
        throw e;
    }
}
```

That widens the `catch` to everything else that also happens to extend `RuntimeException`, defeating the whole point of listing specific exception types, and needs an `instanceof` re-narrowing plus a manual rethrow for the cases it was never meant to catch. The alternative — duplicating the handler body once per `catch` clause — keeps the typing precise but means every change to the shared logic is a multi-site edit. Multi-catch, from Project Coin in Java 7, removes the tradeoff: list the exact alternatives, share one body, and let the type system compute the narrowest thing that is still true of all of them.

### When to reach for it, and when not

Multi-catch is right when the **handling** is identical across the alternatives — same log line, same rejection, same rethrow. A chain of separate `catch` clauses is right when the handling *differs*, and it is also required whenever the body needs a member that exists on only one alternative and not on their common ancestor — which is exactly what concept 2's proof below demonstrates failing.

| Shape | `e`'s static type | Implicitly final | Precise-rethrow eligible | Exception-table rows emitted |
|---|---|---|---|---|
| Single `catch (T e)` | `T`, exactly | No — ordinary local | Yes, if `e` is effectively final | One row |
| Multi-catch `catch (A \| B e)` | LUB of `A` and `B` | Yes — always | Yes, always (cannot be reassigned) | One row per alternative type, same handler PC |
| Chain of narrow catches | Each clause's own declared type | No — each is an ordinary local | Yes per clause, if effectively final | One row per clause |

The exception-table row count is the measured, mechanism-level fact; the full `javap` walk that produces it belongs to [`03-internals-exception-mechanics.md`](03-internals-exception-mechanics.md) and is not reproduced here — the one sentence worth carrying: **multi-catch compiles to one exception-table row per listed type, all pointing at the same handler program counter**, so the JVM still does an ordinary linear type match per alternative; the sharing is entirely a `javac`-level, source-level convenience, not a new runtime dispatch mechanism.

### How it works

The LUB claim, proved rather than asserted. `LedgerImbalanceException` and `BonusIneligibleException` both extend `RuntimeException` directly and share no narrower common ancestor. `LedgerImbalanceException` additionally declares a method, `ledgerDetail()`, that `BonusIneligibleException` does not have:

```java
public class LedgerImbalanceException extends RuntimeException {
    public LedgerImbalanceException(String message) { super(message); }
    public String ledgerDetail() { return "ledger-detail"; }
}

public class BonusIneligibleException extends RuntimeException {
    public BonusIneligibleException(String message) { super(message); }
}
```

```java
static void probe(boolean flag) {
    try {
        if (flag) {
            throw new LedgerImbalanceException("stake 3.33 split mismatch");
        } else {
            throw new BonusIneligibleException("coupon expired");
        }
    } catch (LedgerImbalanceException | BonusIneligibleException e) {
        System.out.println(e.ledgerDetail());
    }
}
```

Measured on JDK 21.0.7:

```
T4.java:10: error: cannot find symbol
            System.out.println(e.ledgerDetail());
                                ^
  symbol:   method ledgerDetail()
  location: variable e of type RuntimeException
```

Read the last line literally: `location: variable e of type RuntimeException`. Not `LedgerImbalanceException`, not `Throwable`, and not "one of the alternatives" — the compiler names the LUB explicitly. `e` genuinely has static type `RuntimeException` here, computed from the two declared alternatives, and `RuntimeException` has no `ledgerDetail()`, so the call does not compile regardless of which branch actually threw at runtime.

`e` is also **implicitly final** — JLS-mandated, not a style convention — and this is a second, independent restriction from the LUB typing, not a consequence of it. Measured:

```java
catch (LedgerImbalanceException | BonusIneligibleException e) {
    e = new BonusIneligibleException("reassigned");
    System.out.println(e);
}
```

```
T5.java:10: error: multi-catch parameter e may not be assigned
            e = new BonusIneligibleException("reassigned");
```

Contrast with a **single**-type `catch` parameter, where the identical assignment is legal:

```java
static void probeCatch() {
    try {
        throw new LedgerImbalanceException("stake mismatch");
    } catch (LedgerImbalanceException e) {
        e = new LedgerImbalanceException("reassigned single-catch, legal");
        System.out.println(e);
    }
}
```

compiles cleanly on JDK 21.0.7 — `javac T7.java` exits 0 with no diagnostic. That asymmetry — final for multi-catch, ordinary for single-catch — is the bridge to concept 3: reassigning a catch parameter is exactly what disables precise rethrow, and multi-catch parameters are permanently immune to that failure mode because the language makes reassignment a compile error rather than merely a bad idea.

Last shape: an alternative that is a subclass of another alternative in the same clause is redundant in the same way an unreachable `catch` clause is redundant, and `javac` refuses it outright rather than silently accepting the wider type. Measured:

```java
catch (RuntimeException | LedgerImbalanceException e) {
    System.out.println(e);
}
```

```
T6.java:9: error: Alternatives in a multi-catch statement cannot be related by subclassing
        } catch (RuntimeException | LedgerImbalanceException e) {
                                    ^
  Alternative LedgerImbalanceException is a subclass of alternative RuntimeException
```

The message names both types and the direction of the relationship explicitly — this is a distinct diagnostic from the unreachable-catch error in concept 1, though the underlying reason is the same shape: listing `LedgerImbalanceException` alongside its own ancestor `RuntimeException` adds nothing, because every `LedgerImbalanceException` was already covered by `RuntimeException`.

### Diagram

No diagram for this concept: the evidence is four quoted compile errors, each isolating one restriction, and the prose above is the clearer rendering.

### A concrete example

```java
import java.io.IOException;
import java.sql.SQLException;

public final class StakeRejectionHandler {

    static void rejectAndLog(boolean viaBankRail) throws IOException, SQLException {
        try {
            if (viaBankRail) {
                throw new SQLException("ledger write failed for stake reservation");
            }
            throw new IOException("quiz engine socket reset during ReserveStake");
        } catch (IOException | SQLException e) {
            // e's static type is Exception (the LUB of IOException and SQLException) —
            // this call is legal because Exception declares getMessage().
            System.out.println("stake reservation failed, voiding: " + e.getMessage());
        }
    }
}
```

`IOException` and `SQLException` both extend `Exception` directly and share nothing narrower, so `e` here is typed `Exception` — verified the same way as above, by removing `getMessage()` and confirming the compile succeeds only because `Exception` declares it.

### The gotcha

**Pitfall:** reaching for multi-catch and then discovering, mid-handler, that the body needs a member only one alternative declares — at that point the fix is not to cast (a cast defeats the safety multi-catch exists to provide and reintroduces exactly the `instanceof` re-narrowing multi-catch was meant to remove) but to split back into a chain of narrow `catch` clauses. **Interview:** "what type does `e` have in `catch (A | B e)`?" — the least upper bound of `A` and `B`, not `Throwable`, not the first alternative listed, and the answer is provable by removing a method only one side declares and reading `location:` in the resulting `cannot find symbol` error.

> **Definition.** Multi-catch binds one implicitly-final parameter, typed as the least upper bound of its listed alternatives, to one shared handler body; alternatives related by subclassing are a compile error identical in spirit to an unreachable single `catch`, and the implicit finality is unconditional — unlike a single-type `catch` parameter, which is an ordinary reassignable local.

---

## 3. Precise rethrow (Java 7): narrowing a rethrow's `throws` to what the body actually threw (1.20.11)

The model: a handler shaped `catch (Exception e) { logIt(e); throw e; }` looks, by its declared parameter type, like it can throw anything assignable to `Exception`. Since Java 7, `javac` does not take that declaration at face value for the purposes of the *enclosing method's* `throws` clause — it re-derives what `e` can actually hold at the `throw e` site from the set of checked exception types the `try` body can actually produce, intersected with the catch parameter's declared type, and requires only that narrower set to be declared. Picture it as the compiler quietly substituting a more specific type for `e` at exactly one point — the `throw` statement — while every other use of `e` in the handler still sees the wide declared type.

### Why it exists

Before Java 7, a handler that needed to log-and-rethrow multiple checked exception types under one wide `catch (Exception e)` had no way to preserve narrow `throws` declarations on the enclosing method, because the compiler only ever looked at `e`'s *declared* type — `Exception` — to check the `throw e` against the method signature. That forced one of two shapes: declare `throws Exception` on the enclosing method (technically correct, but it discards the caller's ability to catch the two concrete types separately, and it forces every caller up the chain to either also declare `throws Exception` or catch a type too broad to act on), or duplicate the log line across a chain of narrow `catch` clauses, one per concrete type, purely to keep each rethrow narrowly typed. Both are worse than the mechanism Java 7 added.

### When to reach for it, and when not

Precise rethrow is not something you opt into with syntax — it is a compiler analysis that activates automatically whenever the conditions hold, so "reaching for it" means writing the log-and-rethrow shape and expecting the narrow `throws` to be verified, not writing anything extra. It stops applying, silently, the moment the catch parameter is reassigned anywhere in the handler — the proof below shows exactly that failure. When the handler genuinely needs to substitute a *different* exception (wrapping, translating), precise rethrow does not apply at all, because the thing being thrown is no longer `e`; that is ordinary exception translation and is typed by the wrapper's declared constructor, not by this mechanism.

### How it works

The precondition is **effective finality**: since Java 7, when a `catch` parameter is never reassigned in its clause's body, `javac` treats the `throw` of that parameter as throwing the intersection of the parameter's declared type and the set of checked exception types the `try` body can actually raise — the same statically-known set from concept 1's unreachable-checked-catch analysis (JLS §11.2.3), not a guess. Measured on JDK 21.0.7, a method whose body throws exactly `IOException` and `SQLException`, caught as `catch (Exception e)`, logged, and rethrown:

```java
import java.io.IOException;
import java.sql.SQLException;

public final class StakeReservationLedgerWriter {

    // Precise rethrow: the try body can throw only IOException and SQLException,
    // so the compiler lets the method declare exactly that pair — not Exception.
    static void reserveStakeAndPersist(boolean viaBankRail) throws IOException, SQLException {
        try {
            if (viaBankRail) {
                throw new SQLException("ledger write failed for stake reservation");
            } else {
                throw new IOException("quiz engine socket reset during ReserveStake");
            }
        } catch (Exception e) {
            System.out.println("logging before precise rethrow: " + e.getMessage());
            throw e;
        }
    }
}
```

```
$ javac StakeReservationLedgerWriter.java
$
```

Compiles with no diagnostic, and the method declares `throws IOException, SQLException` — **not** `throws Exception` — even though `e`'s *declared* type at the `catch` clause is `Exception`. A caller of `reserveStakeAndPersist` can therefore catch `IOException` and `SQLException` separately with the same precision as if the body had never gone through a wide `catch` at all; the wide `catch (Exception e)` is purely a shared-handler convenience and costs the caller nothing.

Now the proof that this is conditional, not unconditional, on `e` staying effectively final. Reassigning `e` anywhere in the handler — even to a value of the exact same static type — turns off the narrowing:

```java
static void reserveStakeAndPersist(boolean viaBankRail) throws IOException, SQLException {
    try {
        if (viaBankRail) {
            throw new SQLException("ledger write failed for stake reservation");
        } else {
            throw new IOException("quiz engine socket reset during ReserveStake");
        }
    } catch (Exception e) {
        e = new Exception("wrapped");
        throw e;
    }
}
```

```
SQLExceptionUseBroken.java:14: error: unreported exception Exception; must be caught or declared to be thrown
            throw e;
            ^
1 error
```

This is the whole point, and it is worth reading the error precisely: `javac` now checks `throw e` against `e`'s plain declared type, `Exception`, because the narrowing precondition — effective finality — no longer holds, and `Exception` is not in the method's `throws` clause. The fix without reverting to the wide declaration is to stop reassigning `e`; the fix if reassignment is genuinely needed is to widen the method's `throws` clause back to `Exception`, which is precisely the pre-Java-7 shape:

```java
static void reserveStakeAndPersist(boolean viaBankRail) throws Exception {
    try {
        if (viaBankRail) {
            throw new SQLException("ledger write failed for stake reservation");
        } else {
            throw new IOException("quiz engine socket reset during ReserveStake");
        }
    } catch (Exception e) {
        e = new Exception("wrapped");
        throw e;
    }
}
```

compiles cleanly — measured, `javac` exits 0 with no diagnostic — and this is exactly the shape legacy code is full of: `throws Exception` on a method that, if its handler were written to stay effectively final, could have declared two or three concrete checked types instead. The wide declaration is not always laziness; in code predating Java 7, or in code whose handler genuinely needs to reassign the caught variable, it is close to the only option, the other being a duplicated chain of narrow `catch` clauses purely to keep each rethrow's typing precise.

### Diagram

No diagram for this concept: the evidence is one compiling narrow declaration, one compile error produced by a single-line change, and the prose above is the clearer rendering of both.

### A concrete example

The example above **is** the minimal concrete example — `StakeReservationLedgerWriter.reserveStakeAndPersist`, with its narrowed `throws IOException, SQLException` verified by the fact that it compiles at all, since `throw e` inside a `catch (Exception e)` block would otherwise require `throws Exception` on the enclosing method.

### The gotcha

**Pitfall:** believing precise rethrow is a property of the `throw e` statement in isolation, and being surprised when adding an unrelated line — a reassignment of `e` for what looks like a harmless logging tweak — breaks compilation at the `throw` several lines below it. **Insight:** the analysis is whole-clause, not local to the `throw` statement; effective finality is a property of the entire `catch` block, so a reassignment anywhere in that block, even one that never executes before the `throw`, disables the narrowing for the whole clause. **Interview:** "why does assigning to a `catch` parameter break precise rethrow?" — because the narrowing is conditioned on the parameter being effectively final for the whole clause; once it can be reassigned, `javac` can no longer prove the value reaching `throw e` is limited to what the `try` body raised, so it falls back to checking the rethrow against the parameter's plain declared type.

> **Definition.** Since Java 7, `javac` types `throw e` inside a `catch` clause by the intersection of the parameter's declared type and the checked exception types the `try` body can actually raise, but only while the parameter is effectively final for that clause — reassigning it anywhere in the clause reverts the check to the parameter's plain declared type, which is why precise rethrow and multi-catch's mandatory finality compose so well together, while a reassigned single-type `catch` parameter forces the pre-Java-7 wide `throws` declaration.

---

## Pitfalls

### Assuming multi-catch gives `e` the alternative's own type

**Wrong**

```java
try {
    if (viaBankRail) {
        throw new LedgerImbalanceException("stake 3.33 split mismatch");
    } else {
        throw new BonusIneligibleException("coupon expired");
    }
} catch (LedgerImbalanceException | BonusIneligibleException e) {
    System.out.println(e.ledgerDetail());   // ledgerDetail() is only on LedgerImbalanceException
}
```

```
error: cannot find symbol
            System.out.println(e.ledgerDetail());
                                ^
  symbol:   method ledgerDetail()
  location: variable e of type RuntimeException
```

**Right**

```java
try {
    if (viaBankRail) {
        throw new LedgerImbalanceException("stake 3.33 split mismatch");
    } else {
        throw new BonusIneligibleException("coupon expired");
    }
} catch (LedgerImbalanceException e) {
    System.out.println(e.ledgerDetail());
} catch (BonusIneligibleException e) {
    System.out.println("coupon rejected: " + e.getMessage());
}
```

Split back into a chain the moment the handling needs a member unique to one alternative — a cast onto the multi-catch parameter would compile but reintroduces exactly the runtime type check multi-catch exists to remove at compile time.

**Why people believe it:** the source lists both concrete types side by side, so it reads as though the compiler "remembers" which branch matched and lets you use either type's members. It does not — `e` has exactly one static type for the whole clause, computed once, before the code runs.

### Believing a reassigned multi-catch parameter is possible because a single-catch parameter allows it

**Wrong**

```java
catch (LedgerImbalanceException | BonusIneligibleException e) {
    e = new BonusIneligibleException("normalise before logging");
    logRejection(e);
}
```

```
error: multi-catch parameter e may not be assigned
            e = new BonusIneligibleException("normalise before logging");
            ^
```

**Right**

```java
catch (LedgerImbalanceException | BonusIneligibleException original) {
    RuntimeException normalised = new BonusIneligibleException(
        "normalised: " + original.getMessage());
    logRejection(normalised);
}
```

Bind a second, ordinary local instead of trying to overwrite the catch parameter — multi-catch parameters are final unconditionally, not final-if-you-happen-not-to-need-reassignment.

**Why people believe it:** a single-type `catch` parameter is an ordinary reassignable local — measured above, reassigning `e` inside `catch (LedgerImbalanceException e)` to a fresh `LedgerImbalanceException` compiles cleanly — so the restriction feels like it should generalise the same way from one catch shape to the other. It is a separate, unconditional rule specific to multi-catch, not a consequence of the LUB typing.

### Reassigning a rethrown catch parameter and expecting the narrow `throws` to survive

**Wrong**

```java
static void reserveStakeAndPersist(boolean viaBankRail) throws IOException, SQLException {
    try {
        if (viaBankRail) {
            throw new SQLException("ledger write failed for stake reservation");
        } else {
            throw new IOException("quiz engine socket reset during ReserveStake");
        }
    } catch (Exception e) {
        e = new Exception("wrapped");   // breaks precise rethrow for the whole clause
        throw e;
    }
}
```

```
error: unreported exception Exception; must be caught or declared to be thrown
            throw e;
            ^
```

**Right**

```java
static void reserveStakeAndPersist(boolean viaBankRail) throws IOException, SQLException {
    try {
        if (viaBankRail) {
            throw new SQLException("ledger write failed for stake reservation");
        } else {
            throw new IOException("quiz engine socket reset during ReserveStake");
        }
    } catch (Exception e) {
        System.out.println("logging before precise rethrow: " + e.getMessage());
        throw e;   // e is never reassigned in this clause -- effectively final
    }
}
```

Keep the catch parameter untouched for the whole clause; if the handler genuinely needs to substitute a different exception object, either throw the new object directly with its own narrow static type, or accept `throws Exception` on the enclosing method.

**Why people believe it:** the reassignment looks purely cosmetic — same declared type, same value class in this example — so it is easy to assume the compiler only cares about what `e` is declared as, not whether it could have been reassigned. The whole-clause effective-finality check is not visible anywhere in the source; it only shows up as a compile error several lines away, at the `throw`, when it fails.

---

## Cheat sheet

| Thing | Fact (Java 21 LTS, measured on JDK 21.0.7) |
|---|---|
| Catch selection | first clause, top to bottom, whose declared type is assignable from the thrown exception's runtime type; at most one runs |
| `finally` | runs after the selected `catch` (or after none matched, or after normal completion); traps in [`01d-finally-traps.md`](01d-finally-traps.md) |
| Catch parameter scope | new variable per clause; same name across sibling clauses does not share state |
| Unreachable catch (supertype before subtype) | `error: exception IOException has already been caught` |
| Unreachable catch (checked type never thrown) | `error: exception SQLException is never thrown in body of corresponding try statement` |
| Same shape for an unchecked type | legal — `javac` exits 0, no diagnostic |
| Why the asymmetry | checked exceptions are a statically-known closed set per `try` body (JLS §11.2.3); unchecked exceptions are open-ended by design |
| Unreachable-catch vs unreachable-code | different rules — this file's is type-relational; `../control-flow/01e-try-and-unreachable-code.md` covers statement reachability |
| Multi-catch, `e`'s type | least upper bound (LUB) of the listed alternatives — proved via `cannot find symbol` plus `location: variable e of type RuntimeException` |
| Multi-catch, finality | implicitly final, unconditionally — `error: multi-catch parameter e may not be assigned` |
| Single-catch parameter finality | ordinary reassignable local — no error on the identical assignment |
| Multi-catch, subclass alternative | `error: Alternatives in a multi-catch statement cannot be related by subclassing` |
| Multi-catch vs chain, when to pick which | multi-catch when handling is identical; chain when handling differs or a body-specific member is needed |
| Exception-table shape (see [`03-internals-exception-mechanics.md`](03-internals-exception-mechanics.md)) | multi-catch emits one row per listed type, all targeting the same handler PC |
| Precise rethrow precondition | catch parameter effectively final **for the whole clause**, not just up to the `throw` |
| Precise rethrow, what narrows | `throw e`'s checked type = declared catch type ∩ checked types the `try` body can actually raise |
| Precise rethrow, proof shape | method declares `throws IOException, SQLException`, catches `Exception e`, rethrows `e` — compiles with no diagnostic |
| Breaking precise rethrow | any reassignment of `e` in the clause — `error: unreported exception Exception; must be caught or declared to be thrown` |
| Pre-Java-7 workaround | `throws Exception` on the enclosing method, or a duplicated chain of narrow `catch` clauses |
| Era | both features are Java 7, Project Coin |

---

## Self-test

**Q1.** Why does `catch (IOException e)` placed after `catch (Exception e)` fail to compile, and what is the exact diagnosis?

<details><summary>Answer</summary>

Because catch selection walks clauses top to bottom and picks the first one whose declared type is assignable from the thrown exception's runtime type; since `IOException` is a subtype of `Exception`, any `IOException` thrown in that `try` would already have matched the `Exception` clause above, so the `IOException` clause could never run. Measured on JDK 21.0.7: `error: exception IOException has already been caught`, pointing at the `catch (IOException e)` line. The rule fires only when the earlier type is a genuine supertype of the later one — two unrelated types, in either order, both compile, because neither can pre-empt the other.

</details>

**Q2.** A `try` body throws no checked exceptions at all. What happens if you write `catch (SQLException e)` around it, versus `catch (IllegalStateException e)`?

<details><summary>Answer</summary>

They behave oppositely. `catch (SQLException e)` fails to compile: measured, `error: exception SQLException is never thrown in body of corresponding try statement`, because `javac` statically tracks the exact set of checked exception types a `try` body can throw (JLS §11.2.3) and refuses a clause for a checked type outside that set. `catch (IllegalStateException e)` compiles cleanly with no diagnostic, because unchecked exception types are exempt from that analysis — the compiler makes no attempt to prove an unchecked type unreachable, since nothing in the language constrains what a future change to the body might throw. This is the checked/unchecked split from [`01-basics.md`](01-basics.md) concept 1 surfacing as a second, independent compile-time consequence.

</details>

**Q3.** Why does assigning to a `catch` parameter break precise rethrow?

<details><summary>Answer</summary>

Precise rethrow narrows `throw e`'s checked type to the intersection of `e`'s declared catch type and the checked exception types the `try` body can actually raise, but this narrowing is conditioned on `e` being effectively final for the **entire** clause — the compiler needs to prove that the only values `e` can ever hold at the `throw` are the ones the `try` body produced. The moment `e` is reassigned anywhere in the clause, that proof no longer holds — `e` could hold an arbitrary value of its declared type — so `javac` falls back to checking `throw e` against `e`'s plain declared type. Measured: with `e = new Exception("wrapped");` added before `throw e;` inside `catch (Exception e)`, a method declaring `throws IOException, SQLException` fails with `error: unreported exception Exception; must be caught or declared to be thrown`, even though the reassignment is on an unconditional path and even though its static type is the same `Exception` the parameter was already declared as. The fix is either to leave `e` untouched, or to widen the method's `throws` clause back to `Exception`.

</details>

**Q4.** What static type does `e` have in `catch (LedgerImbalanceException | BonusIneligibleException e)`, given both extend `RuntimeException` directly with nothing narrower in common? How would you prove it rather than assert it?

<details><summary>Answer</summary>

`RuntimeException` — the least upper bound of the two alternatives, not `Throwable`, not `Exception`, and not either alternative itself. To prove it rather than recall it: call a method that exists on only one of the two alternatives, such as `LedgerImbalanceException.ledgerDetail()`, from inside the multi-catch body, and read the compiler's own diagnosis. Measured on JDK 21.0.7: `error: cannot find symbol`, followed by `location: variable e of type RuntimeException` — the compiler states the inferred type explicitly in the `location:` line, which is stronger evidence than any specification quotation because it is the exact type the compiler used to reject the call.

</details>

**Q5.** Is `catch (RuntimeException | LedgerImbalanceException e)` legal? Why or why not?

<details><summary>Answer</summary>

No. `LedgerImbalanceException` extends `RuntimeException`, so the two alternatives are related by subclassing, and multi-catch specifically forbids that combination — it is redundant in the same way as an unreachable single `catch`, since every `LedgerImbalanceException` is already a `RuntimeException`. Measured: `error: Alternatives in a multi-catch statement cannot be related by subclassing`, followed by a second line naming the direction explicitly: `Alternative LedgerImbalanceException is a subclass of alternative RuntimeException`. This is a distinct diagnostic from the "already been caught" error in concept 1, though the underlying idea — one alternative contributes nothing once a broader one is present — is the same.

</details>

**Q6.** Is a single-type `catch` parameter implicitly final the same way a multi-catch parameter is?

<details><summary>Answer</summary>

No. A single-type `catch (LedgerImbalanceException e)` parameter is an ordinary reassignable local — measured, `e = new LedgerImbalanceException("reassigned single-catch, legal");` inside such a clause compiles with no diagnostic on JDK 21.0.7. Multi-catch parameters are implicitly final unconditionally, regardless of whether the body would ever actually need to reassign them — measured, the identical-looking assignment inside a multi-catch clause produces `error: multi-catch parameter e may not be assigned`. The two rules are independent: multi-catch's finality is not a side effect of the LUB typing, it is a separate restriction the language imposes specifically on the multi-catch form.

</details>

**Q7.** Before Java 7, what were the two ways to get precise per-type handling of two checked exceptions thrown by the same `try` body, and what did each cost?

<details><summary>Answer</summary>

Either declare `throws Exception` (or the LUB of the actual types) on the enclosing method and catch everything under one wide `catch (Exception e)`, which compiles but forces every caller up the chain to also declare or catch something broader than what can actually occur, discarding precision the caller might have wanted; or write a chain of narrow `catch` clauses, one per concrete checked type, which keeps every rethrow precisely typed but duplicates the shared handler body once per clause, so any change to the shared logic is a multi-site edit. Java 7's precise rethrow and multi-catch together remove the tradeoff: one shared handler body, and the enclosing method still only needs to declare the narrow set the body actually throws, as long as the catch parameter stays effectively final.

</details>

**Q8.** A method's `try` body throws only `IOException` and `SQLException`. It is caught as `catch (Exception e)`, logged, and rethrown as `throw e;`, with no reassignment of `e` anywhere in the clause. What can the enclosing method declare in its `throws` clause?

<details><summary>Answer</summary>

`throws IOException, SQLException` — not `throws Exception`. Measured on JDK 21.0.7: exactly this shape compiles with no diagnostic when the method declares only the narrow pair. The mechanism is precise rethrow: because `e` is effectively final for the whole clause, `javac` types `throw e` by the intersection of `e`'s declared type (`Exception`) and the checked exception types the `try` body can actually raise (`IOException`, `SQLException`), which is the narrower pair, and checks the enclosing method's `throws` clause against that narrower set rather than against `e`'s plain declared type.

</details>

---

## Open questions

None.

---

**Leaves covered:** 1.20.9, 1.20.10, 1.20.11 (3 leaves)
**Leaves deferred:** none
**Diagrams included:** none
**Target version:** Java 21 LTS
**Lines:** 627
