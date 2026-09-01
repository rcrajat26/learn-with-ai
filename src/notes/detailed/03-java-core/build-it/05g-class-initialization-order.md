# 03 Java Core — Diagnostic harnesses — class-initialization order, and what triggers it — BUILD IT (§4.8 (4.8.3))

**Target version: Java 21 LTS.** | **Part 4 of 5** | [Index](../00-index.md)
Previous: [The constructor-calls-an-overridable-method trap](05a-construction-and-init-harnesses.md) · Next: [The class-initialization deadlock](05e-class-init-deadlock.md)

Two sequences, both printed. The leaf is `[PROVE]`, and the printed sequence *is* the argument
— so every line of output below was captured from a real run on **Oracle JDK 21.0.7 (build
21.0.7+8-LTS-245), macOS aarch64 (Apple silicon)**, compressed oops on. Nothing here is
predicted. The bug that lives inside this ordering is proved separately in
[The constructor-calls-an-overridable-method trap](05a-construction-and-init-harnesses.md).

---

## 4.8.3 The class-initialization-order harness `[PROVE]`

Two independent sequences run when you touch a class for the first time and then create an
instance, and they nest rather than interleave. `<clinit>` — class initialization — runs once
per class, superclass first, and finishes entirely before the first `<init>` starts. `<init>`
— instance initialization — runs per object, superclass-constructor-first, with each level's
field initializers spliced in between its `super` call and the rest of its constructor body.

The harness makes every phase announce itself, in both classes, with a static block sitting
*between* two static field initializers so the textual interleaving is visible.

```java
/** 4.8.3 — exact initialization sequence for a two-level hierarchy. */
public class InitOrder {

    static String say(String line) {
        System.out.println(line);
        return line;
    }

    static class Reservation {
        static final String SUPER_STATIC_FIRST =
                say("Reservation  : static field  SUPER_STATIC_FIRST");

        static {
            say("Reservation  : static block");
        }

        static final String SUPER_STATIC_SECOND =
                say("Reservation  : static field  SUPER_STATIC_SECOND");

        String superInstanceFirst = say("Reservation  : instance field superInstanceFirst");

        {
            say("Reservation  : instance block");
        }

        String superInstanceSecond = say("Reservation  : instance field superInstanceSecond");

        Reservation() {
            say("Reservation  : ctor body statement 1");
            say("Reservation  : ctor body statement 2");
        }
    }

    static final class BonusReservation extends Reservation {
        static final String SUB_STATIC_FIRST =
                say("BonusReserv. : static field  SUB_STATIC_FIRST");

        static {
            say("BonusReserv. : static block");
        }

        static final String SUB_STATIC_SECOND =
                say("BonusReserv. : static field  SUB_STATIC_SECOND");

        String subInstanceFirst = say("BonusReserv. : instance field subInstanceFirst");

        {
            say("BonusReserv. : instance block");
        }

        String subInstanceSecond = say("BonusReserv. : instance field subInstanceSecond");

        BonusReservation() {
            say("BonusReserv. : ctor body statement 1");
        }
    }

    public static void main(String[] args) {
        say("main         : entered");
        new BonusReservation();
        say("main         : second instance follows");
        new BonusReservation();
    }
}
```

```bash
javac -Xlint:all InitOrder.java   # exit 0, no warnings
java InitOrder
```

```console
main         : entered
Reservation  : static field  SUPER_STATIC_FIRST
Reservation  : static block
Reservation  : static field  SUPER_STATIC_SECOND
BonusReserv. : static field  SUB_STATIC_FIRST
BonusReserv. : static block
BonusReserv. : static field  SUB_STATIC_SECOND
Reservation  : instance field superInstanceFirst
Reservation  : instance block
Reservation  : instance field superInstanceSecond
Reservation  : ctor body statement 1
Reservation  : ctor body statement 2
BonusReserv. : instance field subInstanceFirst
BonusReserv. : instance block
BonusReserv. : instance field subInstanceSecond
BonusReserv. : ctor body statement 1
main         : second instance follows
Reservation  : instance field superInstanceFirst
Reservation  : instance block
Reservation  : instance field superInstanceSecond
Reservation  : ctor body statement 1
Reservation  : ctor body statement 2
BonusReserv. : instance field subInstanceFirst
BonusReserv. : instance block
BonusReserv. : instance field subInstanceSecond
BonusReserv. : ctor body statement 1
```

### Reading the class-initialization half

Lines 2 through 7. `Reservation`'s three static items run before `BonusReservation`'s three,
because initializing a class first initializes its superclass. Within each class, the static
field initializer, the static block, and the second static field initializer run **in the
order they appear in the source** — the block is not hoisted above or below the fields. There
is one `<clinit>` per class and it is the concatenation of every static initializer in textual
order.

That textual ordering is the reason the "illegal forward reference" rule exists: a static
initializer cannot read a static field declared later in the same class through its simple
name, because at that point in `<clinit>` the later field still holds its default and the
value would be silently wrong.

```java
static class BonusPolicy {
    static final int CAP_MINOR_UNITS = GRANT_PERCENT * 1000;
    static final int GRANT_PERCENT = 10;
}
```

```console
ForwardRef.java:3: error: illegal forward reference
        static final int CAP_MINOR_UNITS = GRANT_PERCENT * 1000;
                                           ^
1 error
```

The rule is textual, not dataflow-based, and it is deliberately narrow — it only covers the
simple-name case. `BonusPolicy.GRANT_PERCENT * 1000` (qualified) compiles and reads `0`.

Lines 17 onwards prove the once-only part: the second `new BonusReservation()` emits no
static line at all. `<clinit>` has already run; the class is `initialized` and never runs it
again.

### Reading the instance-initialization half

Lines 8 through 16, in order: `Reservation`'s field initializer, `Reservation`'s instance
block, `Reservation`'s second field initializer, then both statements of `Reservation`'s
constructor body — and only then the same four for `BonusReservation`.

The part people misremember is the relationship between the constructor body and the field
initializers. The constructor body does *not* run first. The sequence inside one level is:
the `super` call, then this level's instance field initializers and instance initializer
blocks in textual order, then the remaining statements of the constructor body. Both
`Reservation` ctor-body lines appear *after* all three `Reservation` initializer lines.

### The bytecode `[BYTECODE]`

`javap -c -p InitOrder$Reservation.class`:

```text
class InitOrder$Reservation {
  static final java.lang.String SUPER_STATIC_FIRST;
  static final java.lang.String SUPER_STATIC_SECOND;
  java.lang.String superInstanceFirst;
  java.lang.String superInstanceSecond;

  InitOrder$Reservation();
    Code:
       0: aload_0
       1: invokespecial #1                  // Method java/lang/Object."<init>":()V
       4: aload_0
       5: ldc           #7                  // String Reservation  : instance field superInstanceFirst
       7: invokestatic  #9                  // Method InitOrder.say:(Ljava/lang/String;)Ljava/lang/String;
      10: putfield      #15                 // Field superInstanceFirst:Ljava/lang/String;
      13: ldc           #21                 // String Reservation  : instance block
      15: invokestatic  #9                  // Method InitOrder.say:(Ljava/lang/String;)Ljava/lang/String;
      18: pop
      19: aload_0
      20: ldc           #23                 // String Reservation  : instance field superInstanceSecond
      22: invokestatic  #9                  // Method InitOrder.say:(Ljava/lang/String;)Ljava/lang/String;
      25: putfield      #25                 // Field superInstanceSecond:Ljava/lang/String;
      28: ldc           #28                 // String Reservation  : ctor body statement 1
      30: invokestatic  #9                  // Method InitOrder.say:(Ljava/lang/String;)Ljava/lang/String;
      33: pop
      34: ldc           #30                 // String Reservation  : ctor body statement 2
      36: invokestatic  #9                  // Method InitOrder.say:(Ljava/lang/String;)Ljava/lang/String;
      39: pop
      40: return

  static {};
    Code:
       0: ldc           #32                 // String Reservation  : static field  SUPER_STATIC_FIRST
       2: invokestatic  #9                  // Method InitOrder.say:(Ljava/lang/String;)Ljava/lang/String;
       5: putstatic     #34                 // Field SUPER_STATIC_FIRST:Ljava/lang/String;
       8: ldc           #37                 // String Reservation  : static block
      10: invokestatic  #9                  // Method InitOrder.say:(Ljava/lang/String;)Ljava/lang/String;
      13: pop
      14: ldc           #39                 // String Reservation  : static field  SUPER_STATIC_SECOND
      16: invokestatic  #9                  // Method InitOrder.say:(Ljava/lang/String;)Ljava/lang/String;
      19: putstatic     #41                 // Field SUPER_STATIC_SECOND:Ljava/lang/String;
      22: return
}
```

Instruction by instruction, `<init>`:

- `0: aload_0` / `1: invokespecial Object."<init>"` — the `super` call. First thing in the
  method, no exceptions. `javac` inserted it; the source has no explicit `super` call.
- `4–10` — `aload_0`, the string constant, the `say` call, `putfield superInstanceFirst`.
  That is the **first field initializer**, compiled inline, immediately after the `super` call.
- `13–18` — constant, `say`, `pop`. The **instance initializer block**. No `putfield` because
  the block assigns nothing, and the `pop` discards `say`'s return value. It sits between the
  two field initializers exactly where the source put it.
- `19–25` — the **second field initializer**, `putfield superInstanceSecond`.
- `28–39` — the two **constructor body** statements, last.
- `40: return`.

And `<clinit>`: the same splicing with `putstatic` instead of `putfield`, three items, textual
order, one method.

The mechanism is in what is *absent*. `javap -p InitOrder$Reservation.class` lists the
members:

```text
class InitOrder$Reservation {
  static final java.lang.String SUPER_STATIC_FIRST;
  static final java.lang.String SUPER_STATIC_SECOND;
  java.lang.String superInstanceFirst;
  java.lang.String superInstanceSecond;
  InitOrder$Reservation();
  static {};
}
```

Two methods. `<init>` and `<clinit>`. There is no method for the instance initializer block,
none for the static block, and none for any field initializer — the class file format has no
such concept. `javac` splices them into `<init>` (immediately after the `super` call) and into
`<clinit>` (from the top), in source order. **That is why the order is textual and why you
cannot reorder it at runtime**: by the time the JVM sees the class, the ordering is a fixed
sequence of bytecodes in a single method body. There is nothing left to reorder.

The subclass's `<init>` shows the same shape with `invokespecial InitOrder$Reservation."<init>"`
at offset 1 instead of `Object`'s, then `putfield subInstanceFirst`, the block, the second
`putfield`, and one ctor-body statement — offsets `0`, `1`, `4–10`, `13–18`, `19–25`, `28–33`,
`34: return`.

### What triggers initialization

An order harness that never shows *when* the order fires is half the leaf. Six cases, all run.

```java
/** 4.8.3 continued — what triggers class initialization and what does not. */
public class Triggers {

    // --- 1. `new` ---
    static class CardDepositRail {
        static { System.out.println("    <clinit> CardDepositRail"); }
        CardDepositRail() { }
    }

    // --- 2. a static method call ---
    static class BankWithdrawalRail {
        static { System.out.println("    <clinit> BankWithdrawalRail"); }
        static String rail() { return "bank withdrawal"; }
    }

    // --- 3. a static field read that is NOT a compile-time constant ---
    static class BonusGrantCounter {
        static { System.out.println("    <clinit> BonusGrantCounter"); }
        static final int GRANTS_PER_DAY = Integer.parseInt("3100");   // runtime value
    }

    // --- 4. a static final compile-time constant: read does NOT trigger ---
    static class BonusPolicy {
        static { System.out.println("    <clinit> BonusPolicy  (SHOULD NOT APPEAR)"); }
        static final int MAX_BONUS_MINOR_UNITS = 10000;   // constant expression
        static final String BONUS_STATUS = "GRANTED";     // constant expression
    }

    // --- 5. a type reference and a .class literal do NOT trigger ---
    static class PaymentRunBatch {
        static { System.out.println("    <clinit> PaymentRunBatch (SHOULD NOT APPEAR)"); }
        static final int WINDOWS_PER_DAY = 4;
    }

    // --- 6. Class.forName with and without the initialize flag ---
    static class ScreeningGate {
        static { System.out.println("    <clinit> ScreeningGate"); }
    }

    static class DocumentGate {
        static { System.out.println("    <clinit> DocumentGate"); }
    }

    public static void main(String[] args) throws Exception {
        System.out.println("1. new CardDepositRail():");
        new CardDepositRail();

        System.out.println("2. BankWithdrawalRail.rail():");
        System.out.println("    returned " + BankWithdrawalRail.rail());

        System.out.println("3. read BonusGrantCounter.GRANTS_PER_DAY (runtime-computed):");
        System.out.println("    value " + BonusGrantCounter.GRANTS_PER_DAY);

        System.out.println("4. read BonusPolicy.MAX_BONUS_MINOR_UNITS and BONUS_STATUS (constants):");
        System.out.println("    value " + BonusPolicy.MAX_BONUS_MINOR_UNITS
                + " / " + BonusPolicy.BONUS_STATUS);

        System.out.println("5. declare a PaymentRunBatch-typed variable and take PaymentRunBatch.class:");
        PaymentRunBatch batch = null;
        Class<?> batchType = PaymentRunBatch.class;
        System.out.println("    type is " + batchType.getName() + ", variable is " + batch);

        System.out.println("6a. Class.forName(name, false, loader) on ScreeningGate:");
        Class<?> lazy = Class.forName("Triggers$ScreeningGate", false,
                Triggers.class.getClassLoader());
        System.out.println("    loaded, not initialized: " + lazy.getName());

        System.out.println("6b. Class.forName(name) on DocumentGate:");
        Class<?> eager = Class.forName("Triggers$DocumentGate");
        System.out.println("    loaded and initialized: " + eager.getName());

        System.out.println("6c. now force ScreeningGate with Class.forName(name):");
        Class.forName("Triggers$ScreeningGate");
    }
}
```

```bash
javac -Xlint:all Triggers.java   # exit 0, no warnings
java Triggers
```

```console
1. new CardDepositRail():
    <clinit> CardDepositRail
2. BankWithdrawalRail.rail():
    <clinit> BankWithdrawalRail
    returned bank withdrawal
3. read BonusGrantCounter.GRANTS_PER_DAY (runtime-computed):
    <clinit> BonusGrantCounter
    value 3100
4. read BonusPolicy.MAX_BONUS_MINOR_UNITS and BONUS_STATUS (constants):
    value 10000 / GRANTED
5. declare a PaymentRunBatch-typed variable and take PaymentRunBatch.class:
    type is Triggers$PaymentRunBatch, variable is null
6a. Class.forName(name, false, loader) on ScreeningGate:
    loaded, not initialized: Triggers$ScreeningGate
6b. Class.forName(name) on DocumentGate:
    <clinit> DocumentGate
    loaded and initialized: Triggers$DocumentGate
6c. now force ScreeningGate with Class.forName(name):
    <clinit> ScreeningGate
```

| Case | Action | `<clinit>` ran? | Evidence in the run |
|---|---|---|---|
| 1 | `new CardDepositRail()` | yes | `<clinit> CardDepositRail` |
| 2 | `BankWithdrawalRail.rail()` static call | yes | line printed before `returned` |
| 3 | read `static final int` computed at runtime | yes | `<clinit> BonusGrantCounter` before `value 3100` |
| 4 | read `static final` **compile-time constant** | **no** | no `BonusPolicy` line; value still `10000 / GRANTED` |
| 5 | typed variable + `.class` literal | **no** | no `PaymentRunBatch` line; `.class` resolved fine |
| 6a | `Class.forName(name, false, loader)` | **no** | `loaded, not initialized` with no `<clinit>` line |
| 6b | `Class.forName(name)` | yes | `initialize` defaults to `true` |
| 6c | `Class.forName(name)` on the already-loaded class | yes | initialization is a separate step from loading |

Note what cases 4 and 5 mean together: `PaymentRunBatch` was *loaded* — the JVM resolved the
`.class` literal and `getName()` worked — and yet never *initialized*. Loading, linking and
initialization are three phases; only the third runs `<clinit>`. That separation is
[`../classes-and-initialization/03-internals-class-loading-and-init.md`](../classes-and-initialization/03-internals-class-loading-and-init.md)'s
subject, and the full trigger list with its JLS §12.4.1 wording is
[`../classes-and-initialization/01d-class-initialization-triggers.md`](../classes-and-initialization/01d-class-initialization-triggers.md)'s.

### Where the constant-inlining evidence actually lives `[NUM]`

Case 4's evidence is not in `BonusPolicy` — it is in the **caller**. A `static final` field
initialized with a constant expression is a compile-time constant, and `javac` copies its
*value* into the caller's constant pool. The caller ends up with no reference to the declaring
class at all, so at runtime there is nothing to trigger.

```java
public class ConstantReader {
    static int cappedBonusMinorUnits(int tenPercentOfDeposit) {
        return Math.min(tenPercentOfDeposit, Triggers.BonusPolicy.MAX_BONUS_MINOR_UNITS);
    }

    static int windowsPerDay() {
        return Triggers.PaymentRunBatch.WINDOWS_PER_DAY;
    }

    static int grantsPerDay() {
        return Triggers.BonusGrantCounter.GRANTS_PER_DAY;
    }
}
```

`javap -c -p ConstantReader.class`:

```text
  static int cappedBonusMinorUnits(int);
    Code:
       0: iload_0
       1: sipush        10000
       4: invokestatic  #9                  // Method java/lang/Math.min:(II)I
       7: ireturn

  static int windowsPerDay();
    Code:
       0: iconst_4
       1: ireturn

  static int grantsPerDay();
    Code:
       0: getstatic     #17                 // Field Triggers$BonusGrantCounter.GRANTS_PER_DAY:I
       3: ireturn
```

- `sipush 10000` — the bonus cap of 100 units, in minor units, as a literal operand. The
  string `BonusPolicy` appears nowhere in this method.
- `iconst_4` — the four payout windows per day, folded to a single-byte opcode. Same story.
- `getstatic Triggers$BonusGrantCounter.GRANTS_PER_DAY:I` — the runtime-computed one keeps a
  symbolic reference, and *that* is the instruction whose resolution triggers `<clinit>`.

Two methods with no dependency on the declaring class, one with a hard dependency, and the
only difference in the source is whether the initializer is a constant expression. That is
also the version trap: change `MAX_BONUS_MINOR_UNITS = 10000` to
`= Integer.parseInt("10000")` and every already-compiled caller keeps the inlined `10000`
until it is recompiled. Constant folding across compilation units is
[`../classes-and-initialization/04-internals-final-and-constant-folding.md`](../classes-and-initialization/04-internals-final-and-constant-folding.md)'s.
The `javap` above is here only as **trigger** evidence — the reason case 4 does not run
`<clinit>`. Leaf 4.8.5, the constant-inlining harness proper, with the recompile-one-side and
observe-the-stale-value demonstration, is
[The constant-inlining harness](05b-inlining-and-retention-harnesses.md); this file does not
pre-empt it.

### The failure mode

If a static initializer throws, the JVM wraps the throwable in `ExceptionInInitializerError`,
marks the class **erroneous**, and never retries. Every later touch of that class throws
`NoClassDefFoundError`.

```java
public class ErroneousTrace {
    static class FundsLedger {
        static final int OPENING_POSITION = Integer.parseInt("CLIENT_CASH_AVAILABLE");
        static int position() { return OPENING_POSITION; }
    }

    public static void main(String[] args) {
        try {
            FundsLedger.position();
        } catch (Throwable first) {
            System.out.println("--- first touch ---");
            first.printStackTrace(System.out);
        }
        System.out.println("--- second touch ---");
        FundsLedger.position();
    }
}
```

```console
--- first touch ---
java.lang.ExceptionInInitializerError
	at ErroneousTrace.main(ErroneousTrace.java:9)
Caused by: java.lang.NumberFormatException: For input string: "CLIENT_CASH_AVAILABLE"
	at java.base/java.lang.NumberFormatException.forInputString(NumberFormatException.java:67)
	at java.base/java.lang.Integer.parseInt(Integer.java:662)
	at java.base/java.lang.Integer.parseInt(Integer.java:778)
	at ErroneousTrace$FundsLedger.<clinit>(ErroneousTrace.java:3)
	... 1 more
--- second touch ---
Exception in thread "main" java.lang.NoClassDefFoundError: Could not initialize class ErroneousTrace$FundsLedger
	at ErroneousTrace.main(ErroneousTrace.java:15)
Caused by: java.lang.ExceptionInInitializerError: Exception java.lang.NumberFormatException: For input string: "CLIENT_CASH_AVAILABLE" [in thread "main"]
	at java.base/java.lang.NumberFormatException.forInputString(NumberFormatException.java:67)
	at java.base/java.lang.Integer.parseInt(Integer.java:662)
	at java.base/java.lang.Integer.parseInt(Integer.java:778)
	at ErroneousTrace$FundsLedger.<clinit>(ErroneousTrace.java:3)
	at ErroneousTrace.main(ErroneousTrace.java:9)
```

The `... 1 more` on the first trace is a genuine JVM-printed fold line — the common frames
between the `NumberFormatException` and the enclosing `ExceptionInInitializerError` were
collapsed, and the one frame folded is `ErroneousTrace.main`.

**Version note, and a correction to widely-repeated advice.** The folklore says the second
`NoClassDefFoundError` carries *no* mention of the original cause, so only the first stack
trace in the log is worth reading. On JDK 21.0.7 that is measurably false: the
`NoClassDefFoundError` chains the original `ExceptionInInitializerError` as its cause,
including the `NumberFormatException` message, the `<clinit>` frame, and the name of the
thread that first failed (`[in thread "main"]`). HotSpot retains the original error for
exactly this purpose. The advice is still *directionally* right — the first trace is the one
with the original throwable as a first-class `Caused by` chain rather than a stringified
message — but "no mention of the cause" is a version-stale claim, and quoting it in an
interview on a modern JDK is a mistake. **Unverified:** which JDK release introduced the
chained cause; the behaviour above is what 21.0.7 does.

The `<clinit>` lock, the erroneous state machine and the concurrent version of this failure
belong to
[`../classes-and-initialization/03a-internals-class-init-locking-and-failure.md`](../classes-and-initialization/03a-internals-class-init-locking-and-failure.md).
The two-thread class-initialization **deadlock** — the same lock, acquired in opposite orders
by two threads — is the next file's leaf, 4.8.4:
[The class-initialization deadlock](05e-class-init-deadlock.md). This file's 4.8.3 is the
single-threaded order; that one is the concurrent failure.

**Interview:** "What runs first, the constructor body or the field initializers?" — The field
initializers, in textual order with the instance blocks, spliced immediately after the `super`
call. The constructor body statements run last. `javap` shows one `<init>` method with the
whole sequence inlined.

### Diff vs the real one

The "real one" is the JVM's own initialization machinery, which this harness observes rather
than reimplements.

| Axis | This harness | The real JVM (HotSpot 21) |
|---|---|---|
| Edge cases | two levels, one thread, no interfaces | interfaces with `default` methods initialize on `default`-method invocation but not on constant read; enums, records, hidden classes and lambda proxies each have their own trigger nuances |
| Intrinsics | none | `<clinit>` completion is a JIT precondition — C2 will not inline through an uninitialized class, and a class's initialized state is a compiler dependency that can force deoptimization |
| Serialization | not `Serializable` | `readObject` skips constructors and runs no field initializers at all; a `Serializable` version of `Reservation` would emit none of the instance lines on deserialization |
| Null policy | fields observed at defaults, no guards | the JVM guarantees zeroed fields; there is no "uninitialized memory" path, which is why [the constructor trap](05a-construction-and-init-harnesses.md) reads `0` and `null` rather than garbage |
| Thread safety | single-threaded — output order is total | `<clinit>` runs under a per-class init lock with an eight-state machine; concurrent triggers block, recursive triggers from the same thread pass straight through, and the deadlock case is order 28's |
| Allocation tricks | 25 `String` constants from the pool, plus one `Reservation` header each run | CDS pre-resolves and archives constant-pool entries so first-touch cost drops; `-Xshare:off` measurably changes when `<clinit>` becomes cheap |
| Why the JDK bothers | — | lazy initialization is the contract that lets a 100 MB class path start in milliseconds; making `<clinit>` eager would force every class on the path to run its statics at launch |

> **Definition.** Class initialization runs once per class, superclass first, as a single
> `<clinit>` method built from every static initializer in textual order; instance
> initialization runs per object as a single `<init>` method whose body is the `super` call,
> then that level's field initializers and instance blocks in textual order, then the
> constructor body.

---

## Pitfalls

### Believing the constructor body runs before the field initializers

**Wrong**

```java
Reservation() {
    say("Reservation  : ctor body statement 1");
    say("Reservation  : ctor body statement 2");
}
```

Expected first; observed last:

```console
Reservation  : instance field superInstanceFirst
Reservation  : instance block
Reservation  : instance field superInstanceSecond
Reservation  : ctor body statement 1
Reservation  : ctor body statement 2
```

**Right**

The bytecode is unambiguous: `invokespecial` at offset 1, `putfield superInstanceFirst` at 10,
the instance block at 13–18, `putfield superInstanceSecond` at 25, and only then the ctor-body
pairs at 28–39. If you need a value before the field initializers, compute it in the `super`
arguments or in a `private static` helper called from them.

**Why people believe it:** a constructor is "the code that builds the object", so it feels
like the first thing to run. Field initializers look like declarations, and declarations do
not usually execute.

### Believing that reading any static field initializes the class

**Wrong**

```java
System.out.println(Triggers.BonusPolicy.MAX_BONUS_MINOR_UNITS);   // expect <clinit> to run
```

```console
4. read BonusPolicy.MAX_BONUS_MINOR_UNITS and BONUS_STATUS (constants):
    value 10000 / GRANTED
```

No `<clinit> BonusPolicy` line. The static block never ran.

**Right**

Only a read of a static field that is **not** a compile-time constant triggers initialization.
The caller's bytecode is the tell — `sipush 10000` (no class reference at all) versus
`getstatic Triggers$BonusGrantCounter.GRANTS_PER_DAY:I` (a symbolic reference whose resolution
triggers `<clinit>`). To force the initializer, read a non-constant field, call a static
method, or use `Class.forName(name)`.

**Why people believe it:** JLS §12.4.1's trigger list gets summarised as "a static field is
used", and the compile-time-constant carve-out is a footnote. It also depends on the
initializer expression, not on the field's type or modifiers, so two fields that look
identical behave differently.

### Believing `ExceptionInInitializerError` will appear again on the second attempt

**Wrong**

```java
try { FundsLedger.position(); } catch (ExceptionInInitializerError retryable) {
    FundsLedger.position();   // "the second call re-runs <clinit> and throws the same thing"
}
```

```console
Exception in thread "main" java.lang.NoClassDefFoundError: Could not initialize class ErroneousTrace$FundsLedger
```

A different error type, and `<clinit>` never runs again.

**Right**

Treat an `ExceptionInInitializerError` as terminal for that class in that class loader. Keep
fallible work — config parsing, file reads, network calls — out of static initializers; put it
in an explicitly invoked initialization method you can retry, or in a holder class you only
touch once the inputs are known good.

**Why people believe it:** every other error in Java is retryable in the sense that repeating
the operation repeats the error. Class initialization is a once-per-class state transition,
not an operation, so repeating the trigger queries a cached failure instead of re-attempting
the work. The belief is also reinforced by a second, opposite piece of folklore — that the
later `NoClassDefFoundError` carries no mention of the original cause at all — which makes the
second error look like a *different, unrelated* failure rather than a cached one. On JDK 21.0.7
that folklore is measurably false: the `NoClassDefFoundError` chains the original
`ExceptionInInitializerError` as its cause, message and failing thread name included, and the
captured trace above shows it. Read the chain and the cached-failure mechanism is visible on
the page.

---


## Cheat sheet

| Question | Answer |
|---|---|
| Order for `new BonusReservation()` | `Reservation.<clinit>` → `BonusReservation.<clinit>` → `Reservation` field inits + blocks (textual) → `Reservation` ctor body → same two for `BonusReservation` |
| Where field initializers live | spliced into `<init>` right after the `super` call; no separate method exists |
| Where static initializers live | spliced into `<clinit>` in textual order; one `<clinit>` per class |
| Why the order is textual | `javap -p` lists only `<init>` and `<clinit>` — there is nothing left to reorder at runtime |
| Order within one class's statics | field initializers and static blocks interleaved exactly as written |
| Second instance | no static output — `<clinit>` runs once per class per loader |
| Triggers `<clinit>` | `new`, static method call, non-constant static field access, `Class.forName(name)`, reflective instantiation, subclass initialization |
| Does **not** trigger `<clinit>` | compile-time-constant `static final` read, type reference, `X.class`, `Class.forName(name, false, loader)` |
| Constant-inlining evidence | in the **caller**: `sipush 10000`, `iconst_4`, no symbolic reference to the declaring class |
| Non-constant static read | `getstatic Triggers$BonusGrantCounter.GRANTS_PER_DAY:I` — resolving that instruction is the trigger |
| Loaded but not initialized | possible and observable: `.class` and `getName()` work with `<clinit>` unrun |
| Illegal forward reference | simple-name read of a later static field in the same class; a qualified read compiles and yields the default |
| Static initializer throws | `ExceptionInInitializerError`; class marked erroneous forever in that loader |
| Second touch of an erroneous class | `NoClassDefFoundError: Could not initialize class …` — and on 21.0.7 the original `ExceptionInInitializerError` **is** chained as its cause |

---

## Self-test

**Q1.** In the two-level harness, why does the static block appear *between* the two static
field initializers rather than before or after both?

<details><summary>Answer</summary>

There is one `<clinit>` per class and `javac` builds it by concatenating every static
initializer in source order, treating static field initializers and static blocks identically.
`javap -c -p` shows `<clinit>` as `putstatic SUPER_STATIC_FIRST`, then the block's
`ldc`/`invokestatic`/`pop`, then `putstatic SUPER_STATIC_SECOND`, then `return`. No method
corresponds to the block, so nothing could be scheduled independently. The same splicing puts
instance initializers into `<init>` immediately after the `super` call.

</details>

**Q2.** Reading `BonusPolicy.MAX_BONUS_MINOR_UNITS` does not run `BonusPolicy`'s static block.
Where do you look for the proof, and what do you expect to see?

<details><summary>Answer</summary>

In the **caller**'s bytecode, not the declaring class's. `MAX_BONUS_MINOR_UNITS = 10000` is a
`static final` initialized with a constant expression, so it is a compile-time constant and
`javac` copies the value into every caller's constant pool. `javap -c -p ConstantReader.class`
shows `sipush 10000` in `cappedBonusMinorUnits` and `iconst_4` in `windowsPerDay` — neither
method holds a symbolic reference to the declaring class, so there is no resolution at runtime
to trigger initialization. The contrast case, `grantsPerDay`, compiles to
`getstatic Triggers$BonusGrantCounter.GRANTS_PER_DAY:I`, and resolving that `getstatic` is the
trigger. The corollary is the stale-constant trap: change the initializer to a runtime
expression and already-compiled callers keep the old inlined value until recompiled.

</details>

**Q3.** A `Class.forName` call did not run the static block. Why, and how do you force it?

<details><summary>Answer</summary>

The three-argument overload `Class.forName(String, boolean initialize, ClassLoader)` was
called with `initialize = false`. Loading, linking and initialization are separate phases; that
call performs the first two and stops, so `getName()` works while `<clinit>` has not run. The
one-argument `Class.forName(String)` defaults `initialize` to `true` and does run it — and
calling it later on an already-loaded-but-uninitialized class initializes it then, as case 6c
of the harness shows. `new`, a static method call, and a non-constant static field access force
it too.

</details>

**Q4.** A static initializer threw on startup. The log has two stack traces. What are they, and
which one do you read?

<details><summary>Answer</summary>

The first is `ExceptionInInitializerError` with the real fault as its `Caused by` — in the
harness, `NumberFormatException: For input string: "CLIENT_CASH_AVAILABLE"` with the `<clinit>`
frame and a `... 1 more` fold line. The second, from any later touch, is
`NoClassDefFoundError: Could not initialize class …`, because the class was marked erroneous
and `<clinit>` will never run again in that loader. Read the first: it carries the original
throwable as a first-class exception chain. The common claim that the second trace mentions
nothing about the cause is version-stale — on 21.0.7 the `NoClassDefFoundError` does chain the
original `ExceptionInInitializerError`, message and failing thread name included — but the
first trace is still the better one.

</details>


**Q5.** `CAP_MINOR_UNITS = GRANT_PERCENT * 1000` above `GRANT_PERCENT = 10` is an illegal
forward reference. Why does the qualified form compile, and what does it produce?

<details><summary>Answer</summary>

The rule is textual and deliberately narrow: it forbids reading a static field of the same
class through its **simple name** from an initializer that appears earlier in the source. Write
`BonusPolicy.GRANT_PERCENT * 1000` instead and it compiles, because the qualified form is not
covered. What it produces is `0` — `<clinit>` is a single method built by concatenating the
static initializers in source order, so at the point `CAP_MINOR_UNITS` is assigned,
`GRANT_PERCENT` has only had its allocation-time default written. The compile error exists to
stop exactly that silent wrong value; the qualified escape hatch is why the harness prints the
error for one form and nothing for the other.

</details>

**Q6.** The harness took `PaymentRunBatch.class`, called `getName()` on it, and the static block
never ran. Was the class loaded?

<details><summary>Answer</summary>

Yes. Loading, linking and initialization are three separate phases, and only the third runs
`<clinit>`. The `.class` literal forced the JVM to load and link `PaymentRunBatch` — it had to,
or `getName()` could not have returned `Triggers$PaymentRunBatch` — and then stopped. The same
split is what `Class.forName(name, false, loader)` exposes deliberately. So "the class was
never touched" is the wrong summary of a non-trigger case; the right one is "the class was
loaded, and its `<clinit>` was not run". The one genuine never-touched case in the harness is
the compile-time constant, where the caller's bytecode holds `sipush 10000` and no reference to
the declaring class at all.

</details>

---

## Open questions

- **When the chained cause was added.** JDK 21.0.7 chains the original
  `ExceptionInInitializerError` as the cause of the later `NoClassDefFoundError`. Which release
  introduced that is unconfirmed; settled by the HotSpot change history for
  `throw_class_initialization_error`, or the JDK bug-database entry for the improved
  `NoClassDefFoundError` message.

---

**Leaves covered:** 4.8.3 (1 leaf)
**Leaves deferred:** none — 4.8.4, the concurrent class-initialization deadlock, is order 28's (`05e-class-init-deadlock.md`); 4.8.5, the constant-inlining harness, is order 29's (`05b-inlining-and-retention-harnesses.md`)
**Diagrams included:** none
**Target version:** Java 21 LTS
**Lines:** 785
