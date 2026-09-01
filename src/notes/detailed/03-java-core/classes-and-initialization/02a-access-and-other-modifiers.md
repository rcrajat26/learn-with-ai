# 03 Java Core — Access and the remaining modifiers — BASICS (§1.14, 1.14.12–1.14.20)

**Target version: Java 21 LTS.** | **Part 1 of 5** | [Index](../00-index.md)
Previous: [Modifiers: `static` and `final`](02-modifiers.md) · Next: [Class loading, linking and initialization](03-internals-class-loading-and-init.md)

What remains after `static` and `final` is a set of modifiers that split into three unrelated jobs wearing the same grammatical costume: four levels of access control decide who may name a declaration; `synchronized`, `volatile` and `transient` are instructions to the runtime about locking, memory visibility and serialization; `native` hands the body to another language; `abstract` and the `sealed` family shape the inheritance graph; and `strictfp` is historical residue that the specification now describes with the word "obsolete." This file is the mechanism under all nine — the two-gate access check that Java 9 bolted in front of the classic one, the `protected` rule that fails to compile in a way almost nobody predicts, the `strictfp` keyword that sets no bit in a Java 21 class file, the exact object each form of `synchronized` locks, and one table of every legal and implicit modifier per declaration kind. Everything below that touches a class file or a compile error was compiled on this machine with `javac --release 21` (Oracle GraalVM 25.0.1 toolchain, class-file major version 65 = Java 21) and the real output pasted in.

## 1. Access control is two gates in series (1.14.12)

Picture two turnstiles in a corridor, one behind the other. The first turnstile is the module system: it asks "is the *package* this type lives in readable from where you stand?" The second turnstile is the classic member check, the one that existed in Java 1.0: it asks "is this *member* declared to let you in?" You need both to pass. Before Java 9 there was only the second turnstile, which is why an entire generation of Java engineers carries a four-row visibility table in their head that is missing a column.

### Why it exists

The second gate — `public`/`protected`/package-private/`private` — exists because a class has two audiences: the code that uses it and the code that implements it, and those two audiences need different amounts of the class's surface. The first gate exists because the second gate turned out to be too coarse at library scale. `sun.misc.Unsafe` was `public`. Every internal JDK utility that a library wanted to reach was `public`, because `public` was the only way to be visible across a package boundary at all, and a JDK internal is by definition in a different package from its callers. The result was that the JDK could not evolve its own internals without breaking the ecosystem, because "internal" was a naming convention (`com.sun.*`, `sun.*`) enforced by documentation and nothing else. Java 9's module system added a gate the compiler and the JVM both enforce: a package is invisible outside its module unless the module's declaration explicitly `exports` it, regardless of how `public` anything inside it is.

### How it works

`[SOURCE]` JLS 21 §6.6.1 states the member rule in a shape that is literally two conditions in series: "A member (class, interface, field, or method) of a class, interface, type parameter, or reference type, or a constructor of a class, is accessible only if (i) the class, interface, type parameter, or reference type is accessible, and (ii) the member or constructor is declared to permit access". Clause (i) is the first gate; clause (ii) is the second. And the type-level rule that clause (i) delegates to is, verbatim from the same section:

> If a top level class or interface is declared `public` and is a member of a package that is not exported by a module, then the class or interface may be accessed by any code in the same module.

Read what that does *not* say. It does not say "and by code in other modules." A `public` class in a non-exported package of a named module is reachable from its own module and nowhere else. `public` stopped meaning "visible everywhere" in Java 9; it now means "visible to the whole module, and beyond it only if the module says so."

**D-041** — Access modifier visibility.

| Modifier | Same class | Same package | Subclass in another package | Unrelated class in another package | Another module, package not `exports`ed |
|---|---|---|---|---|---|
| `public` | yes | yes | yes | yes | **no** |
| `protected` | yes | yes | yes — *restricted*, see below | no | no |
| package-private (no modifier) | yes | yes | no | no | no |
| `private` | yes | no | no | no | no |

*Restriction (JLS 21 §6.6.2.1):* a subclass in another package may access a `protected` instance member only when the qualifying expression's type is the subclass itself or a subclass of it. `ShellRestrictions extends ClientRestrictions` can read `this.reservedAmount` and `other.reservedAmount` where `other` is a `ShellRestrictions`, but cannot read `other.reservedAmount` where `other` is declared as a plain `ClientRestrictions`. Section 2 compiles that failure.

The fifth column is the whole reason this is a Java 9+ table. Note that the answer there is **no for every row, `public` included** — the module gate is checked first, and it does not care what the member modifier says. There is no member modifier that opens a package the module has not exported.

Two consequences of the ordering that people get wrong. First, the "same package, different module" cell that the leaf asks about does not exist for named modules at all: a package may not be split across two named modules, and `javac` says so directly. Second, the classpath is not exempt from the model, it is a *special case* of it — every classpath type lands in the unnamed module, which reads every other module and exports every one of its own packages, so on a pure-classpath build the first gate is always open and the table collapses to its first four columns. That is why the fifth column feels like news: most day-to-day Java never turns the first gate on.

### The example

Two modules. `com.quizstakes.ledger` exports its API package and keeps an internal one to itself; `com.quizstakes.client` requires it and tries to reach both.

```java
// module com.quizstakes.ledger — module-info.java
module com.quizstakes.ledger {
    exports com.quizstakes.ledger;
}
```

```java
// com/quizstakes/ledger/LedgerPositions.java — in the exported package
package com.quizstakes.ledger;

public final class LedgerPositions {
    public static final String CLIENT_CASH_AVAILABLE = "CLIENT_CASH_AVAILABLE";

    private LedgerPositions() { }
}
```

```java
// com/quizstakes/ledger/internal/LedgerImbalanceDetector.java — NOT exported
package com.quizstakes.ledger.internal;

public class LedgerImbalanceDetector {
    public static boolean balanced(long debits, long credits) {
        return debits == credits;
    }
}
```

```java
// module com.quizstakes.client — module-info.java
module com.quizstakes.client {
    requires com.quizstakes.ledger;
}
```

```java
// com/quizstakes/client/BalanceView.java
package com.quizstakes.client;

import com.quizstakes.ledger.LedgerPositions;
import com.quizstakes.ledger.internal.LedgerImbalanceDetector;

public class BalanceView {
    public String position() {
        return LedgerPositions.CLIENT_CASH_AVAILABLE;
    }

    public boolean check() {
        return LedgerImbalanceDetector.balanced(19_800_000L, 19_800_000L);
    }
}
```

`[PROVE]` Compiled with `javac --release 21 --module-source-path mm`, the exact output:

```
BalanceView.java:3: error: package com.quizstakes.ledger.internal is not visible
import com.quizstakes.ledger.internal.LedgerImbalanceDetector;
                            ^
  (package com.quizstakes.ledger.internal is declared in module com.quizstakes.ledger, which does not export it)
1 error
```

`LedgerImbalanceDetector` is `public`. `balanced` is `public static`. The reference still does not compile, and the diagnostic names the reason as the *package*, not the member — gate one, before gate two was ever consulted. Adding `--add-exports com.quizstakes.ledger/com.quizstakes.ledger.internal=com.quizstakes.client` to the same command compiles it cleanly, which is the escape hatch and its cost in one line: it works, and it is a build-configuration promise that must be repeated at every compile and every launch, in every downstream build, forever. `[X-REF]` `exports` versus `opens`, the transitive forms, reflective access and the deep-reflection story are `../language-substrate/02-packages-modules-annotations.md`'s territory (leaves 1.23.6–1.23.8, diagram D-060).

And the split-package attempt, so the "same package, different module" cell is settled by evidence rather than assertion. Declaring `package com.quizstakes.ledger;` inside a second named module produced:

```
BonusPositions.java:1: error: package exists in another module: com.quizstakes.ledger
package com.quizstakes.ledger;
^
```

### The gotcha

**Pitfall:** believing a compile error mentioning a `public` member means the member modifier is wrong. Wrong belief: "it says not visible, so I need to widen the access modifier." Symptom: an engineer adds `public` to something already `public`, or promotes a package-private helper to `public` and the error does not move, because the error was never about the member. Fix: read whether the diagnostic names a *package* or a *member*. A package-level diagnostic is gate one and is fixed in `module-info.java` (`exports`) or on the command line (`--add-exports`); a member-level diagnostic is gate two and is fixed at the declaration.

**Insight:** the two gates also explain a `private` detail worth knowing, from the same §6.6.1: `private` access is permitted "within the body of the top level class or interface that encloses the declaration", and additionally in the `permits` clause and in the record component list of that top-level class. `private` is a *top-level-class* boundary, not a class boundary — which is exactly why one nested class can read another nested class's `private` fields inside the same file, and why nest-based access control exists in the class file at all.

> Access control in Java 21 is two independent checks in series: the module system's readability-and-`exports` check on the package, then the classic `public`/`protected`/package-private/`private` check on the member — and the module check runs first and ignores the member modifier entirely.

## 2. `protected` is not "subclass only" (1.14.13)

Picture `protected` not as a permission granted to a *class* but as a permission granted to a *job*: implementing one particular object. You are inside `ShellRestrictions`, a subclass. You may touch the protected parts of the object you are currently implementing — yourself, or anything you can prove is also a `ShellRestrictions`. You may not reach into a sibling implementation's protected parts just because you share an ancestor with it.

### Why it exists

`protected` is the modifier for "part of the extension contract, not part of the use contract." A superclass wants to hand subclasses a hook — a field they must maintain, a template method they must call — without putting it on the public API where arbitrary callers would depend on it. The pre-`protected` alternatives were both bad: make it `public` and it becomes API you can never remove, or make it package-private and subclassing is confined to your own package.

The qualifying-type restriction exists because the *loose* rule would break encapsulation in a way that is easy to see once stated. If any subclass could reach any superclass-typed reference's protected fields, then writing one subclass of `ClientRestrictions` would grant you write access to the protected internals of *every* `ClientRestrictions` subclass in the system, including ones written by other teams under different invariants. `protected` would become a system-wide backdoor: extend the base class once, and every sibling's internals are yours.

### How it works

`[SOURCE]` JLS 21 §6.6.2, verbatim: "A `protected` member or constructor of an object may be accessed from outside the package in which it is declared only by code that is responsible for the implementation of that object."

And §6.6.2.1, the operative clauses, verbatim:

> Let C be the class in which a `protected` member is declared. Access is permitted only within the body of a subclass S of C.

> If the access is by (i) a qualified name of the form *ExpressionName*`.`*Id* or *TypeName*`.`*Id*, or (ii) a field access expression of the form *Primary*`.`*Id*, then access to the instance field *Id* is permitted if and only if the qualifying type is S or a subclass of S.

The same clause is repeated for method invocations and method references. So the rule has two halves, and both must hold for cross-package access: you must be lexically inside a subclass, **and** the thing on the left of the dot must be typed as your own class or narrower. Note the phrase "if and only if the qualifying type is S" — it is the *static* type of the qualifying expression that decides, not the runtime class, so a downcast is the only fix and it moves the failure from compile time to run time.

§6.6.2.1 also settles the module question this file's D-041 table raises: "Depending on C's accessibility, S may be declared in the same package as C, or in different package of the same module as C, or in a package of a different module entirely." The `protected` rule is module-agnostic — but it still sits behind gate one, so a `protected` member in a non-exported package is unreachable from another module no matter how correct your qualifying type is.

Inside the declaring package, none of this applies. §6.6.1's `protected` bullet permits access outright when "access to the member or constructor occurs from within the package containing the class in which the `protected` member or constructor is declared." That is the half of `protected` that gets forgotten: **`protected` is strictly wider than package-private, and it includes package access unconditionally.** A `protected` member is visible to every class in its own package, subclass or not, related or not.

### The diagram

No manifest diagram covers this concept; D-041's `Restriction` footnote is the picture, and it is above.

### The example

`ClientRestrictions` in package `p1`, tracking the reserved amount behind a restriction; `ShellRestrictions` in package `p2`, a subclass in a different package.

```java
package p1;

import java.math.BigDecimal;

public class ClientRestrictions {
    protected BigDecimal reservedAmount = BigDecimal.ZERO;

    protected void lift(String restrictionType) {
        System.out.println("lifted " + restrictionType);
    }
}
```

```java
package p2;

import java.math.BigDecimal;
import p1.ClientRestrictions;

public class ShellRestrictions extends ClientRestrictions {

    BigDecimal ownReserved() {
        return this.reservedAmount;                 // legal: qualifying type is ShellRestrictions
    }

    BigDecimal siblingReserved(ShellRestrictions other) {
        return other.reservedAmount;                // legal: qualifying type is ShellRestrictions
    }

    BigDecimal parentReserved(ClientRestrictions other) {
        return other.reservedAmount;                // COMPILE ERROR: qualifying type is ClientRestrictions
    }

    void liftVia(ClientRestrictions other) {
        other.lift("STAKE_BLOCKED");               // COMPILE ERROR: same reason, method form
    }
}
```

`[PROVE]` `javac --release 21`, real output, both errors and nothing else:

```
p2/ShellRestrictions.java:7: error: reservedAmount has protected access in ClientRestrictions
    BigDecimal parentReserved(ClientRestrictions other) { return other.reservedAmount; }
                                                                      ^
p2/ShellRestrictions.java:8: error: lift(String) has protected access in ClientRestrictions
    void liftVia(ClientRestrictions other) { other.lift("STAKE_BLOCKED"); }
                                                  ^
2 errors
```

Walk the argument, because the point is that the two legal lines and the two illegal lines differ in exactly one respect. All four accesses occur inside the body of `ShellRestrictions`, so the first half of §6.6.2.1 ("only within the body of a subclass S of C") holds for all four. The second half — "the qualifying type is S or a subclass of S" — holds for `this` (type `ShellRestrictions`) and for `other` in `siblingReserved` (declared type `ShellRestrictions`), and fails for `other` in `parentReserved` and `liftVia`, whose declared type is `ClientRestrictions`, a *superclass* of S, not S or below. The runtime object passed to `parentReserved` may well *be* a `ShellRestrictions`; the compiler does not care and cannot, because the check is on the static type. `((ShellRestrictions) other).reservedAmount` compiles and throws `ClassCastException` at run time whenever the argument is some other subclass — which is the design working as intended, not a loophole: you have asserted "this is my own kind of object," and the JVM verifies the assertion.

### The gotcha

**Pitfall:** wrong belief — "`protected` means subclasses only, and package-private is the wider one." Symptom: engineers reach for `protected` to *narrow* a package-private member, and are surprised that unrelated classes in the same package still compile against it; or they mark a field `protected` intending "only my subclasses touch this" and discover every class in the package can write it. Fix: internalise the ordering `private` ⊂ package-private ⊂ `protected` ⊂ `public`. `protected` is package-private **plus** cross-package subclasses, restricted by qualifying type. There is no modifier that means "subclasses only, and not my own package."

**Interview:** the 90-second answer is the two halves plus the reason. Weak: "`protected` means subclasses and the same package." Strong: "`protected` is package access plus cross-package subclass access, and the cross-package half carries a restriction from JLS §6.6.2.1 — inside a subclass S in another package you may only touch a protected member through a qualifying expression whose *static* type is S or narrower, because `protected` grants you the right to implement your own objects, not to reach into a sibling subclass's internals. That is why `other.reservedAmount` compiles when `other` is declared as your own type and fails when it is declared as the superclass, even if the runtime object is identical."

> `protected` grants package access unconditionally plus cross-package access from within a subclass S, and for instance members that cross-package access is permitted only when the qualifying expression's static type is S or a subclass of S.

## 3. `strictfp` is a no-op, and it was never the escape hatch you think (1.14.17, 1.14.18)

Picture the timeline backwards from how it is usually told. Strict floating point is not a special mode someone added; it is the **original** behaviour of the language. Java 1.2 *removed* the guarantee to buy speed on the hardware of 1998, and handed you `strictfp` as the way to ask for the old behaviour back. Java 17 undid that removal. `strictfp` is therefore not a feature that stopped working — it is a request for something that is now unconditional, like a light switch wired to a lamp that is already permanently on.

### Why it exists — and why it stopped mattering

`[SOURCE]` JEP 306, fetched from `openjdk.org/jeps/306`: title **"Restore Always-Strict Floating-Point Semantics"**, owner Joe Darcy, type Feature, scope SE, **Status Closed / Delivered, Release 17**, component specification / language, issue 8175916. Its summary, verbatim:

> Make floating-point operations consistently strict, rather than have both strict floating-point semantics (`strictfp`) and subtly different default floating-point semantics. This will restore the original floating-point semantics to the language and VM, matching the semantics before the introduction of strict and default floating-point modes in Java SE 1.2.

"Restore" and "the original floating-point semantics" are the load-bearing words. The x86 floating-point unit of the era, x87, held intermediate results in 80-bit extended-precision registers; forcing every intermediate `double` back to 64 bits meant a store-and-reload per operation, which was measurably expensive. Java 1.2 therefore relaxed the default: a conforming JVM was permitted to keep intermediates wider than the declared type, so the same expression could produce different `double` results on different platforms. `strictfp` was the opt-out from the relaxation. SSE2 (2001 onward) made 64-bit-precision arithmetic native and free, the performance argument evaporated, and Java 17 deleted the relaxed mode — leaving `strictfp` as a keyword that requests the only behaviour available.

### How it works — the three-part version statement

**True in Java 21:** every floating-point expression is evaluated strictly, everywhere, with no modifier. `strictfp` parses, compiles, and changes nothing observable. `[SOURCE]` JLS 21 §8.4.3.5, verbatim: "The `strictfp` modifier on a method declaration is obsolete and should not be used in new code. Its presence or absence has no effect at run time." And §8.1.1.3 for classes: "The `strictfp` modifier on a class declaration is obsolete and should not be used in new code. Its presence or absence has no effect at compile time or run time." §9.1.1.2 says the same for interfaces.

**Used to be true, Java 1.2 through Java 16:** omitting `strictfp` permitted a JVM to keep intermediate results in extended precision, so the same arithmetic could yield different `double` values on different hardware, and `strictfp` was the way to forbid that.

**Why it stopped being true:** SSE2-class hardware made strict double-precision arithmetic cost nothing, so the escape hatch bought no performance and cost specification and implementation complexity.

`[VERSION-TRAP]` `[RESEARCH]` Now the part that even careful write-ups get wrong, and which needed the class file to settle. `[SOURCE]` JVMS 21 Table 4.6-A lists `ACC_STRICT` = `0x0800` with the description "In a class file whose major version number is at least 46 and at most 60: Declared `strictfp`." The following paragraph, verbatim:

> The value `0x0800` is interpreted as the `ACC_STRICT` flag only in a class file whose major version number is at least 46 and at most 60. […] (Setting the `ACC_STRICT` flag constrained a method's floating-point instructions in Java SE 1.2 through 16 (§2.8).) For methods in a class file whose major version number is less than 46 or greater than 60, the value `0x0800` is not interpreted as the `ACC_STRICT` flag, but rather is unassigned; it is not meaningful to "set the `ACC_STRICT` flag" in such a class file.

Major version 60 is Java 16; Java 17 is 61; Java 21 is 65. So in a Java 21 class file **`ACC_STRICT` does not exist as a flag at all** — `0x0800` is unassigned. `strictfp` in Java 21 is not "a flag that no longer means anything"; it is not recorded in the class file in any form. Measured, not inferred: the class below, compiled with `javac --release 21`, produced major version 65, and `javap -v` reported the `strictfp` method's flags as `(0x0001) ACC_PUBLIC` — `0x0800` absent.

### The example

The floating-point sum that matters in QuizStakes is a bonus balance, not an abstract `double`. Bonus stake consumption is `min(BONUS_AVAILABLE, 10% of stake)` with the bonus portion rounding **down**, and the canonical case is a stake of 3.33 splitting as 0.33 bonus plus 3.00 cash.

```java
import java.math.BigDecimal;
import java.math.RoundingMode;

public final class BonusRules {
    static final BigDecimal BONUS_STAKE_RATE = new BigDecimal("0.10");

    /** The correct split: exact decimal arithmetic, bonus portion rounded down. */
    static StakeSplit split(BigDecimal stake, BigDecimal bonusAvailable) {
        BigDecimal wanted = stake.multiply(BONUS_STAKE_RATE).setScale(2, RoundingMode.DOWN);
        BigDecimal bonusPortion = wanted.min(bonusAvailable);
        BigDecimal cashPortion = stake.subtract(bonusPortion);
        return new StakeSplit(bonusPortion, cashPortion);
    }

    /** strictfp buys nothing here, and never did buy what people think. */
    static strictfp double splitBroken(double stake, double bonusAvailable) {
        double wanted = Math.floor(stake * 0.10 * 100.0) / 100.0;
        return Math.min(wanted, bonusAvailable);
    }

    record StakeSplit(BigDecimal bonusPortion, BigDecimal cashPortion) {
        StakeSplit {
            // invariant: the two portions sum exactly to the stake
            if (bonusPortion.signum() < 0 || cashPortion.signum() < 0) {
                throw new IllegalArgumentException("negative portion");
            }
        }
    }

    public static void main(String[] args) {
        StakeSplit s = split(new BigDecimal("3.33"), new BigDecimal("50.00"));
        System.out.println("bonus=" + s.bonusPortion()
                + " cash=" + s.cashPortion()
                + " sum=" + s.bonusPortion().add(s.cashPortion()));
        double accumulated = 0.0;
        for (int i = 0; i < 3; i++) {
            accumulated += 0.33;
        }
        System.out.println("double accumulation of 0.33 three times = " + accumulated);
        System.out.println("0.1 + 0.2 = " + (0.1 + 0.2));
    }
}
```

`[PROVE]` Real output on this machine:

```
bonus=0.33 cash=3.00 sum=3.33
double accumulation of 0.33 three times = 0.99
0.1 + 0.2 = 0.30000000000000004
```

`0.1 + 0.2 == 0.30000000000000004` is IEEE 754 binary representation, fully strict, fully deterministic, and completely unaffected by `strictfp` — that discrepancy is the arithmetic being *correct* per the standard. `[X-REF]` the representation story itself, `Math.fma`, and why the x87 extended-precision detour mattered are `../primitives-and-conversions/01c-floating-point.md` and `../numbers-and-money/04-internals-floating-point.md`. What matters here: `javac --release 21` on that `strictfp` method emitted a diagnostic of its own:

```
warning: [strictfp] as of release 17, all floating-point expressions are evaluated
strictly and 'strictfp' is not required
```

The compiler has a named lint category for the keyword. That is as close to an official "delete this" as the toolchain gets.

### `native` (1.14.17)

`native` on a method means "there is no Java body; the implementation is supplied by the platform, bound at first invocation." The declaration ends with a semicolon and the class file records `ACC_NATIVE` = `0x0100` with no `Code` attribute at all — the method has no bytecode to hold. `native` combines legally with `synchronized` (the monitor is acquired by the JVM before control transfers to the native implementation, exactly as for a Java method), and illegally with `abstract` and with `strictfp`; `javac --release 21` on `public native strictfp long hsmBad(byte[] payload)` reported `error: illegal combination of modifiers: native and strictfp`, which is JLS §8.4.3's rule "It is a compile-time error if a method declaration that contains the keyword `native` also contains `strictfp`." In QuizStakes the one plausible `native` is a hardware-security-module call on the card-payment path:

```java
public class CardPayments {
    /** Implemented by the vendor's HSM shared library; bound via JNI at first call. */
    public native long hsmSignIntent(byte[] payload);
}
```

`[X-REF 06]` JNI's binding rules, name mangling, the local/global reference model and the Panama alternative belong to guide **06 JVM internals**.

### The gotcha

**Pitfall:** wrong belief — "adding `strictfp` will make this cross-platform floating-point discrepancy go away." Symptom: a 2026 engineer sees two environments disagreeing on a `double` total, finds a 2009 blog post about `strictfp`, adds it, and the discrepancy stays — because on Java 17+ both environments were already strict, so the difference is coming from somewhere else entirely (a different rounding mode in the code path, a `float` versus `double` widening, a different order of accumulation, a different JDK's `Math` versus `StrictMath` choice for a transcendental function, or simply different input data). Fix: `strictfp` cannot be the answer on Java 17 or later. Look for accumulation order, `Math` versus `StrictMath`, and the actual inputs — and for money, stop using binary floating point at all.

> On Java 21, `strictfp` is obsolete per JLS §8.1.1.3, §8.4.3.5 and §9.1.1.2: all floating-point arithmetic is unconditionally strict, `javac` warns on the keyword, and `ACC_STRICT` is not even a defined flag in a class file of major version 61 or above.

## 4. `synchronized`: what object is actually locked (1.14.15)

Picture `synchronized` as never being about the *code*. It is always about an *object*, and the code merely names which one. Three forms, three answers: on an instance method the object is `this`; on a static method the object is the `Class` object of the declaring class; on a block the object is whatever the parenthesised expression evaluates to. Every question about `synchronized` reduces to "which object, and who else can reach it."

### Why it exists, and the mechanism

`[SOURCE]` JLS 21 §8.4.3.6: "A `synchronized` method acquires a monitor (§17.1) before it executes. For a class (`static`) method, the monitor associated with the `Class` object for the method's class is used. For an instance method, the monitor associated with `this` (the object for which the method was invoked) is used." §14.19 for the statement form: "let the non-null value of the *Expression* be V. The executing thread locks the monitor associated with V" — and, critically, "the locks acquired by `synchronized` statements are the same as the locks that are acquired implicitly by `synchronized` methods", and "A single thread may acquire a lock more than once" (monitors are reentrant). A `synchronized (expr)` where `expr` evaluates to `null` throws `NullPointerException`, per the same section.

The static case has a trap inside it: the monitor is the `Class` object of the **declaring** class, resolved at compile time, not the runtime class of any instance. A `static synchronized` method on `BonusRules` locks `BonusRules.class` even when called through a subclass name.

Two class-file facts, both measured. A `synchronized` **method** carries `ACC_SYNCHRONIZED` = `0x0020` and has **no** `monitorenter`/`monitorexit` in its `Code` — the JVM acquires and releases the monitor around the invocation itself. A `synchronized` **block** compiles to explicit `monitorenter`/`monitorexit` plus a synthetic exception handler whose sole job is to release the monitor if the block completes abruptly.

| Form | Object locked | Class-file mechanism |
|---|---|---|
| `synchronized` instance method | `this` | `ACC_SYNCHRONIZED` (`0x0020`) on the method; no monitor bytecodes |
| `static synchronized` method | the `Class` object of the *declaring* class | `ACC_SYNCHRONIZED` + `ACC_STATIC`; no monitor bytecodes |
| `synchronized (expr) { }` block | the object `expr` evaluates to; NPE if `null` | `monitorenter` / `monitorexit` + synthetic `any` exception handler |

### The example and the bytecode

```java
import java.math.BigDecimal;

public class FundsLedger {
    private BigDecimal cashAvailable = BigDecimal.ZERO;
    private final Object ledgerLock = new Object();
    static BigDecimal houseRevenue = BigDecimal.ZERO;

    public synchronized void creditCashInstance(BigDecimal amount) {
        cashAvailable = cashAvailable.add(amount);
    }

    public static synchronized void creditHouseRevenue(BigDecimal amount) {
        houseRevenue = houseRevenue.add(amount);
    }

    public void creditCashBlock(BigDecimal amount) {
        synchronized (ledgerLock) {
            cashAvailable = cashAvailable.add(amount);
        }
    }
}
```

`[PROVE]` `javap -c -p` on the Java 21 class file, the two contrasting method bodies as emitted:

```
  public synchronized void creditCashInstance(java.math.BigDecimal);
    Code:
         0: aload_0
         1: aload_0
         2: getfield      #13   // Field cashAvailable:Ljava/math/BigDecimal;
         5: aload_1
         6: invokevirtual #22   // Method java/math/BigDecimal.add:(Ljava/math/BigDecimal;)Ljava/math/BigDecimal;
         9: putfield      #13   // Field cashAvailable:Ljava/math/BigDecimal;
        12: return

  public void creditCashBlock(java.math.BigDecimal);
    Code:
         0: aload_0
         1: getfield      #18   // Field ledgerLock:Ljava/lang/Object;
         4: dup
         5: astore_2
         6: monitorenter
         7: aload_0
         8: aload_0
         9: getfield      #13   // Field cashAvailable:Ljava/math/BigDecimal;
        12: aload_1
        13: invokevirtual #22   // Method java/math/BigDecimal.add:(Ljava/math/BigDecimal;)Ljava/math/BigDecimal;
        16: putfield      #13   // Field cashAvailable:Ljava/math/BigDecimal;
        19: aload_2
        20: monitorexit
        21: goto          29
        24: astore_3
        25: aload_2
        26: monitorexit
        27: aload_3
        28: athrow
        29: return
      Exception table:
         from    to  target type
             7    21    24   any
            24    27    24   any
```

Everything worth knowing is visible there. `creditCashInstance` contains no locking instruction whatsoever — the monitor is entirely in the method's flags, which `javap -v` confirmed as `(0x0021) ACC_PUBLIC, ACC_SYNCHRONIZED`, and the static form as `(0x0029) ACC_PUBLIC, ACC_STATIC, ACC_SYNCHRONIZED`. `creditCashBlock` locks the *lock object*, not `this`: instruction 1 reads `ledgerLock`, `dup`/`astore_2` stashes it so the release path has the same reference, then `monitorenter`. Offsets 24–28 are the synthetic handler covering the whole body with `type = any` — it releases the monitor and rethrows, which is why an exception inside a `synchronized` block cannot leak a held lock. Note the second exception-table row, `24 27 24 any`: the handler covers *itself*, so a failure in `monitorexit` re-enters the release path rather than escaping with the monitor held.

`[X-REF 05]` `[X-REF]` the memory-model half — that `monitorexit` and `monitorenter` on the same monitor establish happens-before, and that a `synchronized` method's flag has identical memory semantics to the bytecode form — is guide **05 Concurrency**'s. `../language-substrate/03a-internals-class-file-format.md` owns access-flag encoding and reading `javap -v`. One line of forward pointer: a `synchronized` block inside a `<clinit>` is a deadlock recipe, because class initialization already holds a per-class init lock; `03-internals-class-loading-and-init.md` treats that interaction.

### The gotcha

**Pitfall:** wrong belief — "`public synchronized` makes this method thread-safe, full stop." Symptom: an unrelated caller does `synchronized (fundsLedger) { … }` and now contends with every `synchronized` method on the object, or holds the lock across a slow call and stalls the whole ledger — because a `synchronized` public method **publishes its lock**. Any code holding a reference to the object can lock the same monitor. Fix: the `private final Object ledgerLock` idiom above. The lock is unreachable from outside, so the contention set is exactly the code you wrote.

The contention arithmetic, since this is the leaf where it is real. QuizStakes runs stake reservations at 2.8M/day with a **1200/sec peak**. A single `synchronized` method on one shared `FundsLedger` instance serialises every one of those 1200 calls per second through one monitor. The cost has a hard ceiling set by the critical section's duration: at 1200/sec, the critical section's mean duration must stay under 1/1200 second — about 833 microseconds — merely to keep up, and queueing theory says you want to be well under that, not near it, or the wait time explodes. A `BigDecimal.add` is nanoseconds and fine; a database round trip inside the same `synchronized` block is not, and no amount of lock tuning fixes it. The escape hatches, cheapest first: shrink the critical section to the state mutation only; split the lock by ledger position, so `CLIENT_CASH_AVAILABLE` and `CLIENT_BONUS_AVAILABLE` do not contend; or drop the monitor for a lock-free structure. Each is a real trade — lock splitting means you can no longer atomically update two positions at once, which for a ledger whose whole point is that debits equal credits is a correctness question, not a performance one.

> `synchronized` locks an object, never a region of code: `this` for an instance method, the declaring class's `Class` object for a static method, the evaluated expression for a block — and the method forms record `ACC_SYNCHRONIZED` while the block form emits `monitorenter`/`monitorexit` guarded by a synthetic catch-all handler.

## Supporting facts

### `abstract`, and the six modifiers it cannot share a declaration with (1.14.14)

`abstract` on a class means "incomplete, or to be treated as incomplete" — `[SOURCE]` JLS §8.1.1.1 makes it a compile-time error to instantiate one via a class instance creation expression, and a compile-time error for a non-`abstract` normal class to have an abstract method. An `abstract` class may still have constructors, instance fields, instance initializers and fully implemented methods; the constructor runs when a concrete subclass is instantiated, which is why `abstract` classes routinely carry state that subclasses inherit rather than re-declare. `abstract` on a method declares signature, result and `throws` clause without a body (§8.4.3.1), and such a declaration must appear directly within an `abstract` class unless it occurs within an enum declaration.

The illegal combinations, verbatim from `[SOURCE]` JLS 21 §8.4.3: "It is a compile-time error if a method declaration that contains the keyword `abstract` also contains any one of the keywords `private`, `static`, `final`, `native`, `strictfp`, or `synchronized`." Six, not three. And for classes, `[SOURCE]` §8.1.1.2: "It is a compile-time error if a class is declared both `final` and `abstract`, because the implementation of such a class could never be completed." Each one has a one-line reason: `private` and `final` and `static` make overriding impossible, so there is no way to ever supply the missing body; `native`, `strictfp` and `synchronized` are all statements *about a body*, and there is no body. `[PROVE]` all seven, compiled together with `javac --release 21`, real output:

```
error: illegal combination of modifiers: abstract and final      (final abstract class)
error: illegal combination of modifiers: abstract and private
error: illegal combination of modifiers: abstract and static
error: illegal combination of modifiers: abstract and final      (on the method)
error: illegal combination of modifiers: abstract and synchronized
error: illegal combination of modifiers: abstract and native
error: illegal combination of modifiers: abstract and strictfp
```

**Insight:** an interface is implicitly `abstract` — `[SOURCE]` §9.1.1.1: "Every interface is implicitly `abstract`. This modifier is obsolete and should not be used in new code." Confirmed in the class file: an interface compiled with no modifier beyond `public` reported `flags: (0x0601) ACC_PUBLIC, ACC_INTERFACE, ACC_ABSTRACT`. `[X-REF]` `abstract` class versus interface *as a design choice*, default methods and the diamond are `../inheritance-and-dispatch/01-basics.md`'s (diagrams D-047, D-048); this leaf owns only the modifier legality.

> `abstract` declares a missing implementation, and is therefore a compile-time error alongside any modifier that either forecloses overriding (`private`, `static`, `final`) or describes a body that does not exist (`native`, `strictfp`, `synchronized`) — plus `final` on a class.

### `volatile` and `transient` share nothing but a slot in the grammar (1.14.16)

These two are in the same leaf and the same production — `[SOURCE]` §8.3.1's `FieldModifier: Annotation public protected private static final transient volatile` — and that adjacency is the entire source of the confusion. They belong to different subsystems and neither has any bearing on the other.

`volatile` is a memory-model modifier. `[SOURCE]` §8.3.1.4: "A field may be declared `volatile`, in which case the Java Memory Model ensures that all threads see a consistent value for the variable (§17.4)." Mechanically it forbids the caching and reordering that would let one thread miss another's write, and it adds one guarantee that is easy to forget: **`volatile` `long` and `double` reads and writes are atomic, and non-`volatile` `long` and `double` reads and writes are not** — a 64-bit non-volatile field may be observed torn, half-written, per JLS §17.7. Same section, verbatim, and a compile error people meet by accident: "It is a compile-time error if a `final` variable is also declared `volatile`." `[PROVE]` `final volatile int stakeCount = 0;` produced `error: illegal combination of modifiers: final and volatile`. The reason is that the two are answers to the same question and they conflict: `final` says the value never changes after construction and the JMM freezes it, `volatile` says it changes and every change must be published. `final transient String idempotencyKey = "k";` in the same compilation unit produced **no** error — legal, and pointless for a `final` field you actually need after deserialization, since it will come back as `null`.

`transient` is a serialization modifier with zero memory-model meaning. `[SOURCE]` §8.3.1.3's example says only that if such an instance "were saved to persistent storage by a system service, then only the [non-transient] fields would be saved", and defers the details to `java.io.Serializable`. Concretely: `ObjectOutputStream`'s default mechanism skips the field on write, and on read the field is never assigned, so it holds its type's default value — `null`, `0`, `false` — no matter what it held before. Nothing in the class hierarchy runs to restore it unless you write `readObject` yourself. `[X-REF]` `Serializable`, `writeObject`/`readObject`, `serialVersionUID` and the reconstruction path are `../serialization/02-serialization.md`'s.

| Field modifier | Subsystem | Guarantee | Combines with `final`? |
|---|---|---|---|
| `volatile` | Java Memory Model (§17.4) | cross-thread visibility, no reordering, 64-bit atomicity for `long`/`double` | **no** — compile error (§8.3.1.4) |
| `transient` | serialization (`java.io.Serializable`) | field skipped on write; default value on read | yes — legal, and usually a bug |
| `final` | JMM freeze + immutability (`02-modifiers.md`) | assigned once; safe publication after construction | n/a |

`[X-REF 05]` happens-before, the exact reordering rules `volatile` forbids, and when `volatile` is *not* enough (compound updates such as `count++`) are guide **05 Concurrency**'s. `final`'s freeze semantics are `02-modifiers.md` and `04-internals-final-and-constant-folding.md`.

> `volatile` is a thread-visibility modifier that cannot coexist with `final`; `transient` is a serialization modifier that can, and the only thing they have in common is a line in the `FieldModifier` grammar.

### `sealed`, `non-sealed`, `permits` (1.14.19)

`[SOURCE]` JEP 409 "Sealed Classes", fetched from `openjdk.org/jeps/409`: owner Gavin Bierman, type Feature, scope SE, **Status Closed / Delivered, Release 17**, issue 8260514, previewed as **JEP 360** in JDK 15 and **JEP 397** in JDK 16, finalised in 17 with no changes from 16. `sealed` restricts which classes may directly extend or implement a type; `permits` names them. `[SOURCE]` JLS §8.1.1.2: "It is a compile-time error if a class has a sealed direct superclass or a sealed direct superinterface, and is not declared `final`, `sealed`, or `non-sealed` either explicitly or implicitly" — so `sealed` forces every direct subtype to state its own extensibility, and `non-sealed` is the explicit re-opening. Same section: "It is a compile-time error if a class is declared `non-sealed` but has neither a sealed direct superclass nor a sealed direct superinterface." The `permits` clause may be omitted when all permitted subtypes are in the same compilation unit.

`[SOURCE]` JVMS 21 §4.7.31: "a sealed class or interface is indicated in a class file by the presence of the `PermittedSubclasses` attribute" — there is no `ACC_SEALED` flag, and "a `ClassFile` structure may have a `PermittedSubclasses` attribute, or have its `ACC_FINAL` flag set, but not both." That attribute is what makes exhaustiveness checking in a pattern `switch` decidable at compile time. QuizStakes' `Verdict` is the ready-made example:

```java
public sealed interface Verdict
        permits DocumentVerdict, ScreeningVerdict, ReviewVerdict, WealthVerdict {
    String statusCode();
}

record DocumentVerdict(boolean verified) implements Verdict {
    public String statusCode() {
        return verified ? "AA-611 DOCUMENTS_VERIFIED" : "AA-650 DOCUMENTS_REFERRED";
    }
}

record ScreeningVerdict(boolean clear) implements Verdict {
    public String statusCode() {
        return clear ? "AA-501 SCREENING_CLEAR" : "AA-500 SCREENING_IN_PROGRESS";
    }
}

non-sealed class ReviewVerdict implements Verdict {
    public String statusCode() { return "AA-711 REVIEW_APPROVED"; }
}

sealed class WealthVerdict implements Verdict permits SourceOfFundsVerdict {
    public String statusCode() { return "AA-700 REVIEW_QUEUED"; }
}

final class SourceOfFundsVerdict extends WealthVerdict { }
```

`[PROVE]` `javap -v Verdict` on the compiled result:

```
PermittedSubclasses:
  DocumentVerdict
  ScreeningVerdict
  ReviewVerdict
  WealthVerdict
```

The records satisfy the "`final`, `sealed`, or `non-sealed`" rule implicitly — `[SOURCE]` §8.1.1.2: "a record class is implicitly `final`, so it can also implement a sealed interface", confirmed in the class file as `flags: (0x0030) ACC_FINAL, ACC_SUPER` on `DocumentVerdict`. `ReviewVerdict` needs the explicit `non-sealed`; `WealthVerdict` chains the seal one level further. `[X-REF 04]` pattern matching, exhaustive `switch` over a sealed hierarchy and the `default`-free form are guide **04 Modern Java**'s.

> `sealed` plus `permits` records the authorised direct subtypes in the class file's `PermittedSubclasses` attribute — not a flag — which is what lets a pattern `switch` be checked exhaustively at compile time, and it forces every direct subtype to declare itself `final`, `sealed` or `non-sealed`.

### The legal modifier combinations for each declaration kind (1.14.20)

Every cell below is either the modifier grammar production or an explicit rule from JLS 21; every *implicit* cell was checked against the specification and, where a class file could show it, against `javap -v` output from a `javac --release 21` build. This is a separate table from D-041: D-041 is about *visibility*, this is about *legality*.

| Declaration kind | Access modifiers legal | Other modifiers legal | Implicit |
|---|---|---|---|
| Top-level class | `public` only | `abstract`, `final`, `sealed`, `non-sealed`, `strictfp` (obsolete) | package access if no modifier |
| Member class | all four | `static`, `abstract`, `final`, `sealed`, `non-sealed`, `strictfp` | — |
| Local class | none — compile error | `abstract`, `final`; not `static`, `sealed`, `non-sealed` | — |
| Anonymous class | none | none | never `abstract`, never `sealed`; **never `final`** when declared by `new X() { }`; always `final` when declared by an enum constant body |
| Top-level interface | `public` only | `abstract` (obsolete), `sealed`, `non-sealed`, `strictfp` (obsolete) | `abstract`; package access if no modifier |
| Member interface | all four, but `protected`/`private` illegal inside an interface | `static`, `sealed`, `non-sealed`, `strictfp` | `abstract`, `static`; also `public` when nested in an interface |
| Annotation interface | `public` only at top level | `abstract`, `static`, `strictfp`; **`sealed`/`non-sealed` illegal** | `abstract`, and `static` when nested |
| `enum` | all four for a member enum; `public` only at top level | none of `abstract`/`final`/`sealed`/`non-sealed` needed | `final` — **unless** at least one enum constant has a class body, in which case implicitly `sealed`, permitting exactly the anonymous constant bodies; nested enum implicitly `static` |
| `record` | all four for a member record; `public` only at top level | `final` (redundant), `static` (redundant on a member record) | `final`; nested record implicitly `static`; superclass is `java.lang.Record` |
| Field (in a class) | all four | `static`, `final`, `transient`, `volatile`; `final volatile` is an error | package access if no modifier |
| Field (in an interface) | `public` only | `static`, `final` (all redundant) | `public static final` |
| Method (in a class) | all four | `abstract`, `static`, `final`, `synchronized`, `native`, `strictfp` | package access if no modifier |
| Method (in an interface) | `public` or `private` only | `abstract`, `default`, `static`, `strictfp` | `public` if no access modifier; `abstract` if no body and not `static`/`private` |
| Constructor | all four, and nothing else | none — the grammar admits only annotations and access modifiers | package access if no modifier |
| Instance initializer `{ }` | none | none | — |
| Static initializer `static { }` | none | `static` is the whole declaration | — |

`[PROVE]` on the surprising cells, all measured. Interface members, compiled and read back with `javap -v`: field `GRANT_CAP` → `flags: (0x0019) ACC_PUBLIC, ACC_STATIC, ACC_FINAL`; bodiless method `grant` → `(0x0401) ACC_PUBLIC, ACC_ABSTRACT`; `default` method → `(0x0001) ACC_PUBLIC` with no `ACC_ABSTRACT` and no `default` flag (there is none); nested member class `GrantOutcome` → `public static` in the `NestMembers`/`InnerClasses` record, matching `[SOURCE]` §9.5: "Every member class or interface declaration in the body of an interface declaration is implicitly `public` and `static`". Enums: a plain `enum RestrictionSource { SYSTEM_ONBOARDING, ADMIN }` → `flags: (0x4030) ACC_FINAL, ACC_SUPER, ACC_ENUM`; an enum with one constant-specific class body (`SELF_EXCLUDED { … }`) → `flags: (0x4021) ACC_PUBLIC, ACC_SUPER, ACC_ENUM` — **no `ACC_FINAL`** — plus `PermittedSubclasses: RestrictionType$1`, exactly as §8.1.1.2 and §8.9 describe. And `protected class Nope { }` at top level → `error: modifier protected not allowed here`.

`[VERSION-TRAP]` One widely repeated claim is false and this table corrects it: **an anonymous class is not implicitly `final`.** `[SOURCE]` JLS 21 §15.9.5, verbatim: "An anonymous class is never `abstract`. An anonymous class is never `sealed` […]. An anonymous class declared by a class instance creation expression is never `final`. An anonymous class declared by an enum constant is always `final`." The spec then notes that "An anonymous class being non-final is relevant in casting" — narrowing reference conversion needs the class to be non-final to be legal at compile time. So the two kinds of anonymous class differ, and the `new X() { }` kind is the *non*-final one.

## Pitfalls

### Adding `strictfp` to fix a cross-platform floating-point discrepancy

**Wrong**

```java
// 2026. Two environments report different bonus totals; a blog post suggests strictfp.
public strictfp final class BonusAccrual {
    static double accrue(double[] stakes) {
        double total = 0.0;
        for (double s : stakes) {
            total += s * 0.10;
        }
        return total;
    }
}
```

Output that surprises: the discrepancy does not move, and `javac --release 21` answers with a diagnostic instead:

```
warning: [strictfp] as of release 17, all floating-point expressions are evaluated
strictly and 'strictfp' is not required
```

Both environments were already strict, and `javap -v` shows the `strictfp` method's flags as `(0x0001) ACC_PUBLIC` — `0x0800` is unassigned in a major-version-65 class file, so the keyword left no trace to have any effect with.

**Right**

```java
import java.math.BigDecimal;
import java.math.RoundingMode;

public final class BonusAccrual {
    private static final BigDecimal RATE = new BigDecimal("0.10");

    static BigDecimal accrue(java.util.List<BigDecimal> stakes) {
        BigDecimal total = BigDecimal.ZERO;
        for (BigDecimal s : stakes) {
            total = total.add(s.multiply(RATE).setScale(2, RoundingMode.DOWN));
        }
        return total;
    }
}
```

The guarantee this actually gets: exact decimal arithmetic with an explicit rounding mode and scale, so the result is reproducible by definition rather than by hoping two JVMs agree. The remaining discrepancy in the original was accumulation order and binary representation, neither of which `strictfp` ever addressed.

**Why people believe it:** between Java 1.2 and Java 16 `strictfp` genuinely did fix a real cross-platform divergence, so a decade of accurate blog posts now give exactly the wrong advice, and nothing in the keyword's name signals that it expired in 17.

### Believing `protected` means "subclasses only"

**Wrong**

```java
package p1;

public class ClientRestrictions {
    protected java.math.BigDecimal reservedAmount = java.math.BigDecimal.ZERO;
}

// same package p1, not a subclass, not related at all:
class RestrictionAuditor {
    void tamper(ClientRestrictions r) {
        r.reservedAmount = new java.math.BigDecimal("-1");  // compiles fine
    }
}
```

The surprise: `RestrictionAuditor` is not a subclass and never mentions inheritance, yet it writes the field freely — because `protected` includes package access unconditionally, per JLS §6.6.1.

**Right**

```java
package p1;

public class ClientRestrictions {
    private java.math.BigDecimal reservedAmount = java.math.BigDecimal.ZERO;

    /** The extension hook, without exposing the field. */
    protected final java.math.BigDecimal reservedAmount() {
        return reservedAmount;
    }

    protected final void reserve(java.math.BigDecimal delta) {
        if (delta.signum() < 0) {
            throw new IllegalArgumentException("negative reservation");
        }
        this.reservedAmount = this.reservedAmount.add(delta);
    }
}
```

`private` field plus `protected final` accessors: subclasses get the hook, the package cannot reach the state, and the invariant is enforced in one place.

**Why people believe it:** the word "protected" reads like a narrowing of "package-private", and every introductory table lists the four modifiers in an order that implies increasing restriction rather than the actual nesting `private` ⊂ package-private ⊂ `protected` ⊂ `public`.

### Reading a protected field through a superclass-typed reference

**Wrong**

```java
package p2;

import p1.ClientRestrictions;

public class ShellRestrictions extends ClientRestrictions {
    java.math.BigDecimal compareAgainst(ClientRestrictions other) {
        return other.reservedAmount;
    }
}
```

Real `javac --release 21` output:

```
error: reservedAmount has protected access in ClientRestrictions
        return other.reservedAmount;
                    ^
```

Surprising because `this.reservedAmount` on the line above compiles, and the runtime object passed in may well be a `ShellRestrictions`.

**Right**

```java
package p2;

import p1.ClientRestrictions;

public class ShellRestrictions extends ClientRestrictions {
    /** Qualifying type is ShellRestrictions, so §6.6.2.1 permits the access. */
    java.math.BigDecimal compareAgainst(ShellRestrictions other) {
        return other.reservedAmount;
    }
}
```

This gets the guarantee because §6.6.2.1 checks the *static* type of the qualifying expression: narrow the parameter and the access is legal with no cast and no run-time risk. Casting instead (`((ShellRestrictions) other).reservedAmount`) also compiles, but converts a compile-time rejection into a `ClassCastException` waiting for the first sibling subclass.

**Why people believe it:** the rule has no analogue in any other access modifier — `public`, package-private and `private` all depend only on *where the code is*, and `protected` uniquely also depends on *what the reference is typed as*.

### Believing `public` is enough to be visible across a module boundary

**Wrong**

```java
// module com.quizstakes.ledger declares: exports com.quizstakes.ledger;
package com.quizstakes.ledger.internal;

public class LedgerImbalanceDetector {
    public static boolean balanced(long debits, long credits) {
        return debits == credits;
    }
}
```

Consumed from another module, the real error:

```
error: package com.quizstakes.ledger.internal is not visible
  (package com.quizstakes.ledger.internal is declared in module com.quizstakes.ledger,
   which does not export it)
```

Everything in sight is `public`. The diagnostic names the *package*, because gate one failed before the member modifier was consulted.

**Right**

```java
module com.quizstakes.ledger {
    exports com.quizstakes.ledger;
    exports com.quizstakes.ledger.internal to com.quizstakes.client;
}
```

A qualified `exports` opens the package to exactly one named consumer and nobody else, which is the guarantee: the internal package stays internal to the rest of the world. `--add-exports` on the command line does the same thing without touching the module declaration, at the cost of having to repeat it in every build and launch configuration downstream, forever.

**Why people believe it:** for the twenty-one years before Java 9, `public` did mean "visible everywhere", and on a classpath-only build it still does — the unnamed module exports all its packages and reads all others, so the first gate is invisible until the day someone adds a `module-info.java`.

## Cheat sheet

| Item | Value |
|---|---|
| Access = two gates, in series | (1) module readability + `exports` on the package, (2) member modifier — gate 1 runs first (JLS §6.6.1) |
| D-041, `public` | same class yes · same package yes · subclass other package yes · unrelated other package yes · non-exported package in another module **no** |
| D-041, `protected` | yes · yes · yes (restricted) · no · no |
| D-041, package-private | yes · yes · no · no · no |
| D-041, `private` | yes · no · no · no · no |
| `public` in a non-exported package | reachable from its own module only (JLS §6.6.1) |
| "Same package, different module" | impossible for named modules — `error: package exists in another module` |
| Classpath | unnamed module: reads everything, exports everything — gate 1 always open |
| `protected` = | package access **plus** cross-package subclass access; strictly wider than package-private |
| §6.6.2.1 restriction | cross-package, instance member: qualifying expression's **static** type must be S or a subclass of S |
| `private` scope | the whole **top-level** class, plus its `permits` clause and record component list |
| `abstract` illegal with (method) | `private`, `static`, `final`, `native`, `strictfp`, `synchronized` (JLS §8.4.3) |
| `abstract` illegal with (class) | `final` (JLS §8.1.1.2) |
| `native` illegal with | `abstract`, `strictfp`; legal with `synchronized` |
| `synchronized` instance method locks | `this` — flag `ACC_SYNCHRONIZED` (`0x0020`), no monitor bytecodes |
| `static synchronized` method locks | the **declaring** class's `Class` object — `ACC_SYNCHRONIZED` + `ACC_STATIC` |
| `synchronized (expr)` block locks | the value of `expr`; NPE if `null`; `monitorenter`/`monitorexit` + synthetic `any` handler |
| Lock exposure | a `synchronized` public method publishes its monitor — use `private final Object lock` |
| `volatile` extra guarantee | `long`/`double` reads and writes become atomic; non-volatile 64-bit fields may tear (§17.7) |
| `final volatile` | compile error (JLS §8.3.1.4) |
| `final transient` | legal; the field returns as its default value after deserialization |
| `transient` subsystem | serialization only — no memory-model meaning whatsoever |
| `strictfp` on Java 21 | no-op; JLS §8.1.1.3 / §8.4.3.5 / §9.1.1.2 say "obsolete"; `javac` emits a `[strictfp]` warning |
| `strictfp` history | strict was original; Java 1.2 introduced the relaxed default; **JEP 306** restored always-strict in **17** |
| `ACC_STRICT` (`0x0800`) | interpreted only in class files of major version 46–60 (Java 1.2–16); **unassigned** at 61+ |
| `sealed` | Java **17**, **JEP 409** (previews: JEP 360 in 15, JEP 397 in 16); issue 8260514 |
| `sealed` in the class file | `PermittedSubclasses` attribute — there is no `ACC_SEALED`; mutually exclusive with `ACC_FINAL` |
| Direct subtype of a `sealed` type | must be `final`, `sealed` or `non-sealed`, explicitly or implicitly |
| Interface fields | implicitly `public static final` — measured `(0x0019)` |
| Interface methods | implicitly `public`; implicitly `abstract` if bodiless and not `static`/`private` |
| Nested type in an interface | implicitly `public static` (JLS §9.5) |
| `enum` | implicitly `final` — **unless** a constant has a class body, then implicitly `sealed`, no `ACC_FINAL` |
| `record` | implicitly `final`; nested record implicitly `static`; superclass `java.lang.Record` |
| Anonymous class | never `abstract`, never `sealed`; **never `final`** from `new X() { }`; always `final` from an enum constant body |
| Constructor modifiers | annotations and the three access modifiers, and nothing else |
| Local class | no access modifier, no `static`, no `sealed`/`non-sealed` |
| Annotation interface | `sealed`/`non-sealed` illegal (JLS §9.6) |

## Self-test

**Q1.** A colleague reports that a `public` class with a `public static` method will not compile from another module. Nothing is misspelled and the module is `requires`d. What is wrong, and how does the error message tell you?

<details><summary>Answer</summary>

The class is in a package the owning module does not `exports`. Access control in Java 21 is two checks in series, and JLS §6.6.1 states them as such: a member is accessible only if (i) the type is accessible and (ii) the member permits access. Gate one is the module system's readability-and-`exports` check on the *package*, and it runs first and ignores the member modifier entirely. §6.6.1 also says outright that a `public` top-level class in a package that is not exported "may be accessed by any code in the same module" — and says nothing about other modules, deliberately. The message tells you which gate failed by naming a package rather than a member: `package com.quizstakes.ledger.internal is not visible (package … is declared in module com.quizstakes.ledger, which does not export it)`. The fixes are `exports com.quizstakes.ledger.internal;` in `module-info.java`, a qualified `exports … to com.quizstakes.client;` if you want exactly one consumer, or `--add-exports` on the command line — which works but must be repeated at every compile and launch in every downstream build forever.

</details>

**Q2.** Inside a subclass `ShellRestrictions` in a different package from `ClientRestrictions`, why does `other.reservedAmount` compile when `other` is declared `ShellRestrictions` and fail when it is declared `ClientRestrictions`, even though the same object may be passed in both cases?

<details><summary>Answer</summary>

Because JLS §6.6.2.1 checks the *static* type of the qualifying expression, not the runtime class. The rule has two halves. First: "Let C be the class in which a `protected` member is declared. Access is permitted only within the body of a subclass S of C" — satisfied in both cases, since both accesses are lexically inside `ShellRestrictions`. Second: for an instance field access of the form *Primary*`.`*Id*, "access to the instance field *Id* is permitted if and only if the qualifying type is S or a subclass of S" — satisfied when `other` is declared `ShellRestrictions`, violated when it is declared `ClientRestrictions`, because `ClientRestrictions` is a *super*class of S. The compiler cannot consult the runtime type; that is the point. The rationale is in §6.6.2's opening sentence: a protected member may be accessed from outside its package "only by code that is responsible for the implementation of that object" — writing one subclass must not hand you access to every sibling subclass's internals. The real error is `error: reservedAmount has protected access in ClientRestrictions`. Narrowing the parameter type fixes it cleanly; a downcast also compiles but converts the compile-time rejection into a `ClassCastException` on the first sibling subclass.

</details>

**Q3.** An interviewer says "`strictfp` guarantees the same floating-point result on every platform." What is your answer for Java 21?

<details><summary>Answer</summary>

On Java 21 the guarantee is unconditional and `strictfp` is irrelevant to it. JLS §8.4.3.5 says the modifier on a method "is obsolete and should not be used in new code. Its presence or absence has no effect at run time", and §8.1.1.3 and §9.1.1.2 say the same for classes and interfaces. The history runs the opposite way from how it is usually told: JEP 306, "Restore Always-Strict Floating-Point Semantics", delivered in **Release 17**, states it will "restore the original floating-point semantics to the language and VM, matching the semantics before the introduction of strict and default floating-point modes in Java SE 1.2." Strict was original; Java 1.2 *introduced* a relaxed default so JVMs could keep intermediates in x87's 80-bit extended-precision registers, and `strictfp` was the opt-out from that relaxation. SSE2 made strict 64-bit arithmetic free, so Java 17 deleted the relaxed mode. The class-file consequence is sharper than "the flag is ignored": JVMS 21 says `0x0800` is interpreted as `ACC_STRICT` only in class files of major version 46 through 60 — Java 1.2 through 16 — and at 61 or above it "is not interpreted as the `ACC_STRICT` flag, but rather is unassigned." A Java 21 class file (major 65) records nothing at all for `strictfp`; measured, a `strictfp` method's flags read `(0x0001) ACC_PUBLIC`. And `javac --release 21` emits a `[strictfp]` lint warning telling you to delete it.

</details>

**Q4.** Name the object locked by each of the three `synchronized` forms, and say how you would prove the difference from the class file.

<details><summary>Answer</summary>

Instance method locks `this`; `static` method locks the `Class` object of the **declaring** class (resolved at compile time, so a subclass name in the call does not change it); `synchronized (expr)` block locks whatever `expr` evaluates to, throwing `NullPointerException` if that is `null`. JLS §8.4.3.6 and §14.19 state all three, and §14.19 adds that these are the same monitors and that a single thread may acquire one more than once — monitors are reentrant. The class-file proof is a contrast: a `synchronized` *method* carries the `ACC_SYNCHRONIZED` flag (`0x0020`) and its `Code` contains **no** monitor instruction — measured `(0x0021) ACC_PUBLIC, ACC_SYNCHRONIZED` for the instance form and `(0x0029) ACC_PUBLIC, ACC_STATIC, ACC_SYNCHRONIZED` for the static one — because the JVM acquires and releases around the invocation. A `synchronized` *block* has plain flags and explicit `monitorenter` at offset 6 and `monitorexit` at 20, plus a synthetic exception handler at 24 covering the body with `type = any` that releases and rethrows, so an exception cannot leak a held monitor. The handler's exception-table row also covers itself (`24 27 24 any`), so a failure in `monitorexit` re-enters the release path.

</details>

**Q5.** Which six modifiers are illegal on a method alongside `abstract`, and what single question do all six answers reduce to?

<details><summary>Answer</summary>

JLS §8.4.3, verbatim: "It is a compile-time error if a method declaration that contains the keyword `abstract` also contains any one of the keywords `private`, `static`, `final`, `native`, `strictfp`, or `synchronized`." Six, and the count itself is the trap — most people name three. They split into two reasons. `private`, `static` and `final` all make overriding impossible, so the missing body could never be supplied by anyone: the declaration would be permanently unimplementable. `native`, `strictfp` and `synchronized` are all statements *about a body* — where the implementation lives, how its floating-point arithmetic is constrained, whether a monitor wraps its execution — and an `abstract` method has no body for them to describe. Separately, on a *class*, `abstract` is illegal with `final`, and §8.1.1.2 gives the reason in the spec text: "the implementation of such a class could never be completed." Worth adding: an `abstract` class may still have constructors, instance fields and concrete methods, which surprises people — the constructor runs when a concrete subclass is instantiated.

</details>

**Q6.** `volatile` and `transient` are both field modifiers in the same grammar production. What does each actually do, and which one cannot be combined with `final`?

<details><summary>Answer</summary>

They belong to unrelated subsystems and the shared grammar slot is the only thing they have in common. `volatile` is a Java Memory Model modifier: JLS §8.3.1.4 says the JMM "ensures that all threads see a consistent value for the variable", meaning it forbids the caching and reordering that would let one thread miss another's write — and it adds a guarantee people forget, that `volatile` `long` and `double` reads and writes are atomic where non-volatile 64-bit fields may be observed torn per §17.7. `transient` is a serialization modifier with no memory-model meaning at all: `ObjectOutputStream`'s default mechanism skips the field on write, and on read it is never assigned, so it holds its type's default value — `null`, `0`, `false` — unless you write `readObject` to restore it. `final volatile` is a **compile error**: §8.3.1.4 states "It is a compile-time error if a `final` variable is also declared `volatile`", because the two answer the same question with contradictory answers — `final` says the value never changes after construction and the JMM freezes it, `volatile` says it changes and every change must be published. `final transient` is legal and almost always a bug, since a `final` field you needed after deserialization comes back as its default.

</details>

**Q7.** How is a `sealed` type represented in the class file, and what does that representation make possible?

<details><summary>Answer</summary>

By the `PermittedSubclasses` attribute on the `ClassFile` structure, not by a flag. JVMS 21 §4.7.31 addresses the obvious guess directly: one might expect an `ACC_SEALED` flag by analogy with `final`/`ACC_FINAL`, but "in fact, a sealed class or interface is indicated in a class file by the presence of the `PermittedSubclasses` attribute", and a class file "may have a `PermittedSubclasses` attribute, or have its `ACC_FINAL` flag set, but not both." Measured on `sealed interface Verdict permits DocumentVerdict, ScreeningVerdict, ReviewVerdict, WealthVerdict`, `javap -v` prints exactly those four names under `PermittedSubclasses`. What it makes possible is compile-time exhaustiveness: because the complete set of direct subtypes is recorded and closed, a pattern `switch` over the hierarchy can be proven to cover every case with no `default` branch. `sealed` shipped in Java 17 as JEP 409 (previewed as JEP 360 in 15 and JEP 397 in 16), and it forces every direct subtype to declare itself `final`, `sealed` or `non-sealed` — implicitly satisfied by records and by enums without constant bodies, both of which are implicitly `final`.

</details>

**Q8.** Which "implicit modifier" facts about enums, records, interfaces and anonymous classes are most commonly stated wrongly?

<details><summary>Answer</summary>

Four. (1) An `enum` is implicitly `final` **only if no constant has a class body**; JLS §8.1.1.2 says an enum class "is either implicitly `final` or implicitly `sealed`", and §8.9 makes it implicitly `sealed` when at least one constant has a class body, with the permitted subclasses being the anonymous classes those bodies declare. Measured: a plain enum reads `(0x4030) ACC_FINAL, ACC_SUPER, ACC_ENUM`; one with a constant body reads `(0x4021) ACC_PUBLIC, ACC_SUPER, ACC_ENUM` with no `ACC_FINAL`, plus `PermittedSubclasses: RestrictionType$1`. (2) A `record` is implicitly `final`, always, and a nested record is implicitly `static`. (3) A nested type declared inside an interface is implicitly `public static` per §9.5, and `protected`/`private` on it is a compile error — while interface *fields* are implicitly `public static final` and interface *methods* are implicitly `public`, and implicitly `abstract` when bodiless and neither `static` nor `private`. (4) The one that is usually stated backwards: an anonymous class is **not** implicitly `final`. §15.9.5 says "An anonymous class declared by a class instance creation expression is never `final`", and only "An anonymous class declared by an enum constant is always `final`." The non-finality matters for narrowing reference conversion in casts.

</details>

## Open questions

- None. Every claim above is anchored to JLS 21 (§6.6.1, §6.6.2, §6.6.2.1, §8.1.1.1, §8.1.1.2, §8.1.1.3, §8.3.1, §8.3.1.3, §8.3.1.4, §8.4.3, §8.4.3.1, §8.4.3.5, §8.4.3.6, §8.9, §8.10, §9.1.1.1, §9.1.1.2, §9.4, §9.5, §14.3, §14.19, §15.9.5), JVMS 21 (Table 4.6-A, §4.7.31), JEP 306 or JEP 409, and every compile error, warning and class-file flag quoted was produced on this machine by `javac --release 21` / `javap` and pasted verbatim. One toolchain caveat, stated rather than hidden: the installed JDK is Oracle GraalVM 25.0.1, driven with `--release 21`, which enforces Java 21 language rules and emits class-file major version 65; the class-file and diagnostic evidence is therefore Java 21 evidence, but a native Java 21 `javac` could in principle word a diagnostic differently.

---

**Leaves covered:** 1.14.12, 1.14.13, 1.14.14, 1.14.15, 1.14.16, 1.14.17, 1.14.18, 1.14.19, 1.14.20 (9 leaves)
**Leaves deferred:** none
**Diagrams included:** D-041 (rendered as a Markdown table per the manifest)
**Target version:** Java 21 LTS
**Lines:** 844
