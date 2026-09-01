# 03 Java Core — The constant-inlining harness — BUILD IT (§4.8.5)

**Target version: Java 21 LTS.** | **Part 4 of 5** | [Index](../00-index.md)
Previous: [The class-initialization deadlock](05e-class-init-deadlock.md) · Next: [The inner-class retention harness](05h-inner-class-retention.md)

A `static final int` initialised from a literal is not a field read at runtime. It is not a field
read at all. `javac` copies the *value* into the constant pool of every class that reads it, and
the reading class is left with no mention of the declaring class — no `Fieldref`, nothing to
resolve. The value a caller uses is therefore the value that was true when **the caller** was
compiled. Recompile only the declaring class and every already-compiled caller keeps the old value:
silently, with no warning and no linkage error, because there is nothing left to link.

This file performs that. Real compiles, a real edit, a real partial recompile, the real stale
value, and `javap` read instruction by instruction. Everything below was run in
`/tmp/jcb-n-work-29/` on **Oracle JDK 21.0.7 (build 21.0.7+8-LTS-245), macOS aarch64 (Apple
silicon)**. Leaf 4.8.6, the inner-class retention harness, lives in
[The inner-class retention harness](05h-inner-class-retention.md) despite this file's name.

---

## 1. The mechanism, stated once

**Constant variable** (JLS 4.12.4): a `final` variable of primitive type or type `String`,
initialised with a constant expression. Not a `BigDecimal`. Not an `Integer`.

**Constant expression** (JLS 15.29): literals, casts to primitive or `String`, the arithmetic,
shift, comparison, bitwise, logical and conditional operators over constant expressions, and
simple or qualified names referring to constant variables. `new` is not on that list; neither is a
method invocation; neither is `null`.

**What the binary must contain** (JLS 13.1, item 3, verbatim):

> A reference to a field that is a constant variable (§4.12.4) must be resolved at compile time
> to the value V denoted by the constant variable's initializer.
>
> If such a field is `static`, then no reference to the field should be present in the code in a
> binary file, including the class or interface which declared the field.

Not "may be absent" — *should not be present*. `javac` is required to erase the reference. The
value survives in the declaring class only as a `ConstantValue` attribute on the field, which
exists so that a *future* compilation of a caller can read the value out of the class file with no
source available — which is why the inlining crosses jar boundaries. That attribute's class-file
layout belongs to
[the class-file format](../language-substrate/03a-internals-class-file-format.md); `final` and
constant folding as a topic to
[final and constant folding](../classes-and-initialization/04-internals-final-and-constant-folding.md);
the `static final` modifier pair to
[modifiers](../classes-and-initialization/02-modifiers.md), which carries the diagram of this
mechanism.

One consequence is established elsewhere: because the caller emits no `getstatic`, reading a
compile-time constant **does not trigger initialisation of the declaring class** — that is
[Class-initialization order](05g-class-initialization-order.md)'s ground, and it points here for
the staleness. The two facts are one fact seen from two sides.

> A constant variable is a `final` primitive-or-`String` field whose value `javac` bakes into
> every reader, leaving the reader with no runtime dependency on the declaring class at all.

---

## 2. The harness

Two files. `BonusRules` holds the QuizStakes bonus tuning parameters — exactly the kind of value
that gets tuned, which is exactly why this bites. `BonusService` reads them and computes a grant:
10% of the first deposit, capped at 100.

`BonusRules.java`:

```java
import java.math.BigDecimal;

/** QuizStakes bonus tuning parameters. Grant = 10% of the first deposit, capped at 100. */
public final class BonusRules {

    /** Constant expression: final, int, initialised from a literal. */
    public static final int BONUS_PERCENT = 10;

    /** Constant expression: final, String, initialised from a literal. */
    public static final String BONUS_CODE = "AA-801";

    /** NOT a constant expression: `new` is never one. */
    public static final BigDecimal BONUS_CAP = new BigDecimal("100");

    /** NOT a constant expression: a method invocation is never one. */
    public static final int GRANTS_PER_DAY = Integer.parseInt(
            System.getProperty("quizstakes.bonus.grantsPerDay", "3100"));

    /** NOT final, so never inlined regardless of the initialiser. */
    public static int COUPON_VALIDITY_DAYS = 14;

    static {
        System.out.println("[BonusRules class initialiser ran]");
    }

    private BonusRules() {
    }
}
```

`BonusService.java`:

```java
import java.math.BigDecimal;
import java.math.RoundingMode;

/** Computes the first-deposit bonus grant for a QuizStakes client. */
public final class BonusService {

    /** No concat folding here, so the pushed constant is visible on its own. */
    public static int percentInUse() {
        return BonusRules.BONUS_PERCENT;
    }

    public static BigDecimal grantFor(BigDecimal firstDeposit) {
        BigDecimal pct = BigDecimal.valueOf(BonusRules.BONUS_PERCENT)
                .divide(BigDecimal.valueOf(100));
        BigDecimal raw = firstDeposit.multiply(pct).setScale(2, RoundingMode.DOWN);
        return raw.min(BonusRules.BONUS_CAP);
    }

    public static void main(String[] args) {
        System.out.println("percentInUse()       = " + percentInUse());
        System.out.println("BONUS_CODE           = " + BonusRules.BONUS_CODE);
        System.out.println("BONUS_CAP            = " + BonusRules.BONUS_CAP);
        System.out.println("GRANTS_PER_DAY       = " + BonusRules.GRANTS_PER_DAY);
        System.out.println("COUPON_VALIDITY_DAYS = " + BonusRules.COUPON_VALIDITY_DAYS);
        System.out.println("grant on deposit 65  = " + grantFor(new BigDecimal("65.00")));
        System.out.println("grant on deposit 480 = " + grantFor(new BigDecimal("480.00")));
    }
}
```

### Stage 1 — compile both, run

```bash
export JAVA_HOME=/Library/Java/JavaVirtualMachines/jdk-21.jdk/Contents/Home
export PATH="$JAVA_HOME/bin:$PATH"
cd /tmp/jcb-n-work-29/stage1
javac BonusRules.java BonusService.java
java BonusService
```

```console
percentInUse()       = 10
BONUS_CODE           = AA-801
[BonusRules class initialiser ran]
BONUS_CAP            = 100
GRANTS_PER_DAY       = 3100
COUPON_VALIDITY_DAYS = 14
grant on deposit 65  = 6.50
grant on deposit 480 = 48.00
```

Correct: 10% of 65 is 6.50, 10% of 480 is 48.00, neither hits the cap of 100.

**Insight:** look at *where* `[BonusRules class initialiser ran]` printed. Not first. It printed
after two lines that read fields of `BonusRules`, because those two reads were inlined and never
touched the class. Initialisation happened only when line three needed `BONUS_CAP`, whose read is
a real `getstatic`. The ordering is itself proof that inlined reads carry no dependency.

### Stage 2 — edit only `BonusRules.java`

A real tuning change: the percent drops from 10 to 8, the code moves from `AA-801` to `AA-711`,
the cap from 100 to 80, the coupon window from 14 days to 30.

```bash
sed -i '' -e 's/BONUS_PERCENT = 10;/BONUS_PERCENT = 8;/' \
          -e 's/BONUS_CODE = "AA-801";/BONUS_CODE = "AA-711";/' \
          -e 's/new BigDecimal("100");/new BigDecimal("80");/' \
          -e 's/COUPON_VALIDITY_DAYS = 14;/COUPON_VALIDITY_DAYS = 30;/' BonusRules.java
grep -n 'BONUS_PERCENT =\|BONUS_CODE =\|BigDecimal("80")\|COUPON_VALIDITY_DAYS =' BonusRules.java
```

```console
7:    public static final int BONUS_PERCENT = 8;
10:    public static final String BONUS_CODE = "AA-711";
13:    public static final BigDecimal BONUS_CAP = new BigDecimal("80");
20:    public static int COUPON_VALIDITY_DAYS = 30;
```

### Stage 3 — recompile only the changed file, run

```bash
javac BonusRules.java
java BonusService
```

```console
percentInUse()       = 10
BONUS_CODE           = AA-801
[BonusRules class initialiser ran]
BONUS_CAP            = 80
GRANTS_PER_DAY       = 3100
COUPON_VALIDITY_DAYS = 30
grant on deposit 65  = 6.50
grant on deposit 480 = 48.00
```

There it is. `BONUS_CAP` moved to 80 and `COUPON_VALIDITY_DAYS` to 30. `BONUS_PERCENT` is still
**10**, `BONUS_CODE` is still **AA-801**, and the grants are computed at the old percentage: 6.50
instead of 5.20, 48.00 instead of 38.40. No warning, exit status 0. The split is exact — the two
constant variables went stale, the two non-constants and the non-`final` field did not.

### Stage 4 — recompile both, run

```bash
javac BonusRules.java BonusService.java
java BonusService
```

```console
percentInUse()       = 8
BONUS_CODE           = AA-711
[BonusRules class initialiser ran]
BONUS_CAP            = 80
GRANTS_PER_DAY       = 3100
COUPON_VALIDITY_DAYS = 30
grant on deposit 65  = 5.20
grant on deposit 480 = 38.40
```

Recompiling the *reader* is what moved the value. Nothing about the declaring class changed
between stage 3 and stage 4.

---

## 3. The bytecode, read instruction by instruction

`javap -c -p BonusService.class` at stage 1 and stage 3 (identical — the partial recompile never
touched this class file):

```console
  public static int percentInUse();
    Code:
       0: bipush        10
       2: ireturn
```

Two instructions. `bipush 10` pushes the byte-sized immediate `10` onto the operand stack;
`ireturn` returns it. There is no `getstatic`, no `Fieldref`. The method body does not know
`BonusRules` exists.

```console
  public static java.math.BigDecimal grantFor(java.math.BigDecimal);
    Code:
       0: ldc2_w        #9                  // long 10l
       3: invokestatic  #11                 // Method java/math/BigDecimal.valueOf:(J)Ljava/math/BigDecimal;
       6: ldc2_w        #17                 // long 100l
       9: invokestatic  #11                 // Method java/math/BigDecimal.valueOf:(J)Ljava/math/BigDecimal;
      12: invokevirtual #19                 // Method java/math/BigDecimal.divide:(Ljava/math/BigDecimal;)Ljava/math/BigDecimal;
      15: astore_1
      16: aload_0
      17: aload_1
      18: invokevirtual #23                 // Method java/math/BigDecimal.multiply:(Ljava/math/BigDecimal;)Ljava/math/BigDecimal;
      21: iconst_2
      22: getstatic     #26                 // Field java/math/RoundingMode.DOWN:Ljava/math/RoundingMode;
      25: invokevirtual #32                 // Method java/math/BigDecimal.setScale:(ILjava/math/RoundingMode;)Ljava/math/BigDecimal;
      28: astore_2
      29: aload_2
      30: getstatic     #36                 // Field BonusRules.BONUS_CAP:Ljava/math/BigDecimal;
      33: invokevirtual #40                 // Method java/math/BigDecimal.min:(Ljava/math/BigDecimal;)Ljava/math/BigDecimal;
      36: areturn
```

Instruction 0 is the whole lesson. `BONUS_PERCENT` was an `int` in the source; the call needs a
`long`, so `javac` performed the widening at compile time and emitted `ldc2_w` against a `long`
pool entry holding `10`. The declaring class is not named. Instructions 15 through 29 are ordinary
local-variable and argument shuffling around the two `BigDecimal` calls. Instruction 30, by
contrast, is a genuine `getstatic` naming `BonusRules.BONUS_CAP` — resolved at runtime, and
therefore picking up the change.

`main` sharpens it further. The `BONUS_CODE` print compiles to
`ldc #65 // String BONUS_CODE           = AA-801` then `invokevirtual println`, because label and
value were concatenated **at compile time** into one pool entry — concatenation of two constant
expressions being itself a constant expression, so not even an `invokedynamic` concat was needed.
That one pool entry is what stage 3 printed. The `GRANTS_PER_DAY` and `COUPON_VALIDITY_DAYS`
prints, by contrast, are `getstatic` at instructions 42 and 56, each followed by an
`invokedynamic makeConcatWithConstants` because the value is only known at runtime. After stage
4's full recompile the two inlined sites read `bipush 8` and
`ldc #65 // String BONUS_CODE           = AA-711`.

### The declaring class's side: the `ConstantValue` attribute

`javap -v -p BonusRules.class`, field section, at stage 1:

```console
  public static final int BONUS_PERCENT;
    descriptor: I
    flags: (0x0019) ACC_PUBLIC, ACC_STATIC, ACC_FINAL
    ConstantValue: int 10

  public static final java.lang.String BONUS_CODE;
    descriptor: Ljava/lang/String;
    flags: (0x0019) ACC_PUBLIC, ACC_STATIC, ACC_FINAL
    ConstantValue: String AA-801

  public static final java.math.BigDecimal BONUS_CAP;
    descriptor: Ljava/math/BigDecimal;
    flags: (0x0019) ACC_PUBLIC, ACC_STATIC, ACC_FINAL

  public static final int GRANTS_PER_DAY;
    descriptor: I
    flags: (0x0019) ACC_PUBLIC, ACC_STATIC, ACC_FINAL

  public static int COUPON_VALIDITY_DAYS;
    descriptor: I
    flags: (0x0009) ACC_PUBLIC, ACC_STATIC
```

`ConstantValue` is present on exactly the two constant variables and absent on the other three,
even though `BONUS_CAP` and `GRANTS_PER_DAY` both carry `ACC_FINAL`. `ACC_FINAL` is not the
discriminator; the presence of `ConstantValue` is.

### There is no reference left to break

```bash
javap -v -p BonusService.class | grep -n "BonusRules"
```

```console
19:    #7 = Class              #8            // BonusRules
20:    #8 = Utf8               BonusRules
46:   #36 = Fieldref           #7.#37        // BonusRules.BONUS_CAP:Ljava/math/BigDecimal;
85:   #75 = Fieldref           #7.#76        // BonusRules.GRANTS_PER_DAY:I
90:   #80 = Fieldref           #7.#81        // BonusRules.COUPON_VALIDITY_DAYS:I
```

Three `Fieldref` entries, for the three non-inlined fields. None for `BONUS_PERCENT`, none for
`BONUS_CODE`. So those fields need not exist. **Delete both declarations** from `BonusRules.java`,
leaving only `BONUS_CAP`, `GRANTS_PER_DAY`, `COUPON_VALIDITY_DAYS` and the private constructor;
recompile only that file, and run the untouched reader:

```console
percentInUse()       = 10
BONUS_CODE           = AA-801
BONUS_CAP            = 100
GRANTS_PER_DAY       = 3100
COUPON_VALIDITY_DAYS = 14
grant on deposit 65  = 6.50
grant on deposit 480 = 48.00
exit=0
```

The program prints two fields that no longer exist, and exits cleanly. Now delete `BONUS_CAP`
instead — a `final` field that is *not* a constant variable — and again recompile only the
declaring class:

```console
percentInUse()       = 10
BONUS_CODE           = AA-801
Exception in thread "main" java.lang.NoSuchFieldError: Class BonusRules does not have member field 'java.math.BigDecimal BONUS_CAP'
	at BonusService.main(BonusService.java:22)
```

That contrast is the entire point. Where a reference survives, the JVM checks it and fails loudly.
Where `javac` erased the reference, there is nothing to check, so a mismatch is indistinguishable
from correctness; `NoSuchFieldError` is possible only where a `Fieldref` remains to be resolved.

**Gotcha:** the failure mode is inverted from the usual intuition. The *safer-looking* declaration
— `final`, primitive, immutable, no allocation — is the one with no runtime verification; the
heavier-looking `BigDecimal` field is the one the JVM polices.

---

## 4. The boundary: four declarations, side by side

| Declaration | Constant expression? | Reader's bytecode | Goes stale? | Reading it initialises `BonusRules`? |
|---|---|---|---|---|
| `static final int BONUS_PERCENT = 10;` | yes (literal, JLS 15.29) | `bipush 10` / `ldc` of the folded value | **yes** | **no** |
| `static final String BONUS_CODE = "AA-801";` | yes (`String` literal) | `ldc` of the folded `String`, interned | **yes** | **no** |
| `static final BigDecimal BONUS_CAP = new BigDecimal("100");` | no (`new` is not one) | `getstatic BonusRules.BONUS_CAP` | no | yes |
| `static final int GRANTS_PER_DAY = Integer.parseInt(System.getProperty("quizstakes.bonus.grantsPerDay", "3100"));` | no (method invocation) | `getstatic BonusRules.GRANTS_PER_DAY` | no | yes |

Row two: the inlined `String` is a `String` literal in the *reader's* own pool, so it is interned
there — the interning half belongs to
[the string pool](../strings/01b-the-string-pool.md) — and a `String` constant behaves
**identically** to an `int` constant here, being a reference type buying no protection. Row four:
`GRANTS_PER_DAY` is `static final` and its value is fixed for the life of the JVM, yet it is not a
constant variable, because `Integer.parseInt` and `System.getProperty` are method invocations.
Constant-ness is a property of the initialiser expression, not of whether the value is stable.

### `final` alone is not the trigger — `static final` with a constant initialiser is

`COUPON_VALIDITY_DAYS` is `public static int`, initialised from the literal `14`. Its flags are
`(0x0009) ACC_PUBLIC, ACC_STATIC` — no `ACC_FINAL`, no `ConstantValue` — and the reader emits
`getstatic BonusRules.COUPON_VALIDITY_DAYS:I` at instruction 56. It moved from 14 to 30 across the
partial recompile: dropping `final` defeats inlining entirely. A *non-`static`* `final` primitive
field initialised from a literal is a constant variable too (JLS 4.12.4 does not require `static`),
but JLS 13.1 confines the erasure to the declaring class in that case — readers outside the class
still emit `getfield`, so instance fields are not a staleness vector across compilation units.

---

## 5. Interfaces are not a safe hiding place

The most common real instance of this bug puts the tunable on an interface, because "constants go
in an interface" is folklore. Interface fields are implicitly `public static final` (JLS 9.3), so
they inline the same way — `javap -v BonusTuning.class` shows both fields with
`flags: (0x0019) ACC_PUBLIC, ACC_STATIC, ACC_FINAL` and a `ConstantValue` attribute, none of it
written in the source.

`BonusTuning.java`:

```java
/** Interface constants are implicitly public static final. */
public interface BonusTuning {
    int BONUS_PERCENT = 10;
    String BONUS_CODE = "AA-801";
}
```

`BonusAudit.java`:

```java
/** Reconciles the bonus the ledger recorded against the rule the audit run believes. */
public final class BonusAudit {

    public static void main(String[] args) {
        System.out.println("interface BONUS_PERCENT = " + BonusTuning.BONUS_PERCENT);
        System.out.println("interface BONUS_CODE    = " + BonusTuning.BONUS_CODE);
    }
}
```

```bash
cd /tmp/jcb-n-work-29/iface
javac BonusTuning.java BonusAudit.java && java BonusAudit
```

```console
interface BONUS_PERCENT = 10
interface BONUS_CODE    = AA-801
```

The reader, from `javap -c -p BonusAudit.class`:

```console
       0: getstatic     #7                  // Field java/lang/System.out:Ljava/io/PrintStream;
       3: ldc           #15                 // String interface BONUS_PERCENT = 10
       5: invokevirtual #17                 // Method java/io/PrintStream.println:(Ljava/lang/String;)V
       8: getstatic     #7                  // Field java/lang/System.out:Ljava/io/PrintStream;
      11: ldc           #23                 // String interface BONUS_CODE    = AA-801
      13: invokevirtual #17                 // Method java/io/PrintStream.println:(Ljava/lang/String;)V
      16: return
```

Both values folded into `ldc` string constants; the interface is named nowhere in the method body.
Now edit the interface only — 10 to 8, `AA-801` to `AA-711` — recompile only the interface, rerun:

```console
interface BONUS_PERCENT = 10
interface BONUS_CODE    = AA-801
```

Stale, and there is no `implements` relationship anywhere in this program. An interface is a worse
hiding place than a class. If the constants must stay there, expose them through a `static`
interface method, which compiles to `invokestatic` at every call site.

---

## 6. Why the JDK does this at all

Because it makes constants free, and that is a real, everywhere benefit.

- **No field read.** `bipush 10` versus `getstatic` plus constant-pool resolution plus a memory
  load. The constant is an operand of the instruction.
- **No class initialisation.** `Integer.MAX_VALUE` costs nothing and cannot deadlock, because
  reading it neither loads nor initialises `java.lang.Integer`.
- **Folding before the JIT exists.** `javac` folds arithmetic over constant expressions itself, so
  `65 * BONUS_PERCENT / 100` becomes one pool entry — and `switch` labels, array dimensions and
  annotation values *require* compile-time constants, so the machinery must exist regardless.
- **Conditional compilation.** JLS 13.4.9 names this as the deciding reason: `if (DEBUG) { }` with
  `static final boolean DEBUG = false;` compiles to nothing, and JLS 14.22's unreachable-code
  rules are written so that this stays legal.
- **The price, in the same breath.** The value becomes part of every reader's binary, so changing
  it is a change to every reader, and nothing in the toolchain says so.

---

## 7. Binary compatibility: compatible, and wrong

JLS 13.4.9, *`final` Fields and `static` Constant Variables*, verbatim:

> If a field is a constant variable (§4.12.4), and moreover is `static`, then deleting the keyword
> `final` or changing its value will not break compatibility with pre-existing binaries by causing
> them not to run, but they will not see any new value for a usage of the field unless they are
> recompiled. This result is a side-effect of the decision to support conditional compilation
> (§14.22). (One might suppose that the new value is not seen if the usage occurs in a constant
> expression (§15.29) but is seen otherwise. This is not so; pre-existing binaries do not see the
> new value at all.)

Two things there earn attention. "Will not break compatibility with pre-existing binaries by
causing them not to run" makes this a **binary compatible** change by JLS 13's own definition,
which is precisely why no tool complains. And the parenthesis rules out the hopeful theory: it is
not "inlined where a constant is required, resolved otherwise" — every use site is inlined,
unconditionally. Binary compatible and behaviourally incompatible at once. That gap is the whole
hazard, and the JLS gives the remedy directly:

> The best way to avoid problems with "inconstant constants" in widely-distributed code is to use
> `static` constant variables only for values which truly are unlikely ever to change. Other than
> for true mathematical constants, we recommend that source code make very sparing use of `static`
> constant variables.

> If the read-only nature of `final` is required, a better choice is to declare a `private`
> `static` variable and a suitable accessor method to get its value.

**Interview:** "Is changing the value of a `public static final int` a breaking change?" The
answer that lands: binary compatible, behaviourally incompatible — callers link fine and keep the
old value until recompiled, per JLS 13.4.9.

---

## 8. How it bites in a real build

The harness is two files in one directory, so a full `javac` fixes it. Production is not.

- **Multi-module incremental compilation.** Module `bonus-rules` bumps `BONUS_PERCENT` from 10 to
  8. `BonusService` is recompiled because it changed for another reason; the audit module did not
  change, so its class files come from the build cache. `BonusService` now grants 5.20 on a 65
  deposit and the audit run reconciles against 6.50. At 3.1k bonus grants a day, averaging 42,
  every one mismatches. The `FundsLedger` stays internally consistent — every entry balances — and
  the reconciliation report shows a break with no exception, no log line and no failing test,
  because both sides are doing exactly what their bytecode says.
- **A jar upgraded without recompiling dependents.** Drop in a new `bonus-rules.jar`, restart, and
  part of the estate uses the old percent. This is what the harness *cannot* reproduce and where it
  is most dangerous, because the stale caller's source may not be in your repository at all.
- **The tell.** Two components disagreeing about a number that appears in exactly one place in the
  source. If `grep` finds one definition and the runtime shows two values, suspect inlining first.

---

## 9. The fixes, ranked, and re-tested

All three code fixes are in one file below and all three were put back through the stale-value
procedure.

```java
import java.math.BigDecimal;

/** The same tuning parameters, declared so that none of them can be inlined. */
public final class BonusRules {

    /** Fix 1: boxing. `Integer` is not a primitive type, so this is not a constant expression. */
    public static final Integer BONUS_PERCENT_BOXED = 10;

    /** Fix 2: an accessor. A method invocation is never a constant expression at the call site. */
    private static final int BONUS_PERCENT = 10;

    public static int bonusPercent() {
        return BONUS_PERCENT;
    }

    /** Fix 3: a non-primitive, non-String type. */
    public static final BigDecimal BONUS_CAP = new BigDecimal("100");

    private BonusRules() {
    }
}
```

```java
public final class BonusService {

    public static void main(String[] args) {
        System.out.println("BONUS_PERCENT_BOXED = " + BonusRules.BONUS_PERCENT_BOXED);
        System.out.println("bonusPercent()      = " + BonusRules.bonusPercent());
        System.out.println("BONUS_CAP           = " + BonusRules.BONUS_CAP);
    }
}
```

```bash
cd /tmp/jcb-n-work-29/fixes
javac BonusRules.java BonusService.java && java BonusService
```

```console
BONUS_PERCENT_BOXED = 10
bonusPercent()      = 10
BONUS_CAP           = 100
```

The reader's three reads, from `javap -c -p BonusService.class` — a `getstatic`, an `invokestatic`
and a `getstatic`, nothing folded:

```console
       3: getstatic     #13                 // Field BonusRules.BONUS_PERCENT_BOXED:Ljava/lang/Integer;
      17: invokestatic  #29                 // Method BonusRules.bonusPercent:()I
      31: getstatic     #36                 // Field BonusRules.BONUS_CAP:Ljava/math/BigDecimal;
```

Now edit only `BonusRules.java` — 10 to 8, cap 100 to 80 — recompile only it, and rerun the
untouched reader:

```bash
sed -i '' -e 's/BONUS_PERCENT_BOXED = 10;/BONUS_PERCENT_BOXED = 8;/' \
          -e 's/BONUS_PERCENT = 10;/BONUS_PERCENT = 8;/' \
          -e 's/new BigDecimal("100");/new BigDecimal("80");/' BonusRules.java
javac BonusRules.java && java BonusService
```

```console
BONUS_PERCENT_BOXED = 8
bonusPercent()      = 8
BONUS_CAP           = 80
```

All three propagated.

| Fix | What it costs | When to pick it |
|---|---|---|
| Read from configuration (`@Value`, a properties file, a feature flag) | a config source, a startup failure mode, and no compile-time `switch`-label use | the value is operational and changes without a release |
| `private static final` plus a `static` accessor | one `invokestatic` per read, JIT-inlined to nothing after warm-up | the JLS's own recommendation; the default for a published API |
| Non-primitive type (`BigDecimal`, `Integer`, an enum, a record) | one object and one `getstatic`; unboxing on every read if it sits in a hot loop | the value is money or a domain type anyway |
| Accept the inlining, enforce clean builds | slower CI, and a discipline that erodes | the value is a true invariant, like a currency's minor-unit scale |

**Insight:** the accessor fix works even though `bonusPercent()`'s own body compiles to
`bipush 8`. The fold still happens — inside the declaring class, which is recompiled with the
change by definition. What the accessor removes is the fold at the *reader's* site: the boundary
you are protecting is the compilation-unit boundary, not the fold. For the same reason the
declaring class still carries `ConstantValue: int 8` on its `private` field, harmlessly —
`private` means no other compilation unit can name it, so no other binary can inline it.

---

## 10. Detection

**`javac -Xlint`**, against both the partial recompile and the full one:

```bash
javac -Xlint:all BonusRules.java ; echo "exit=$?"
javac -Xlint:all BonusRules.java BonusService.java ; echo "exit=$?"
```

```console
exit=0
exit=0
```

Silence in both cases. There is no lint category for this and there cannot usefully be one:
`javac` compiling `BonusRules.java` alone has no idea any reader exists, and `javac` compiling
both is producing a correct build. "Nothing" is the finding — do not expect the compiler to help.

**Build tools.** Gradle's incremental Java compiler is documented to give up on incremental
compilation when a constant changes; the Java plugin userguide states that "The compile task does
not use incremental build immediately after a compile error or if a Java constant changes." That
is the right conservative behaviour — it cannot cheaply know which classes inlined the value, so
it recompiles the source set. **Unverified:** whether that fallback reaches *consuming* projects
in the same build, and whether the wording holds in the Gradle version you are on.
**Unverified:** `maven-compiler-plugin`'s incremental staleness check appears to compare
source-versus-class timestamps and, to my knowledge, does not model constant dependencies — which
would make `mvn clean` the only reliable remedy there — but I could not confirm it. **What actually
works:** treat a constant's value as part of your module's ABI, so if it changes you rebuild every
dependent from source, and make CI's default a clean build for release artefacts.

---

## 11. Diff vs the real one

| Axis | This harness | A real multi-module build | What the JLS guarantees |
|---|---|---|---|
| Edge cases | one declaring class, one reader, one directory, no packages | transitive dependents, split package hierarchies, annotation processors, generated sources that also inline | 13.1 applies identically at every scale — the erasure is per compilation unit |
| Intrinsics / JIT | irrelevant; the fold is `javac`'s, before the JVM starts | same; C2 folds further, but the staleness is already baked into the class file | the fold is a *language* requirement, not an optimisation the JIT may skip |
| Serialization | not exercised | a constant used as a `serialVersionUID` or an enum's persisted code goes stale in writer and reader independently, so a wire format can silently fork | `serialVersionUID` is itself a constant variable and inlines |
| Null policy | `BONUS_CODE` is non-null; `static final String X = null;` is *not* a constant variable, so it emits `getstatic` | same, and a genuine trap: adding `= null` as a default silently changes the linkage shape | JLS 15.29 omits `null` from constant expressions |
| Thread safety | none needed; `bipush` reads no shared state | same — the one axis where inlining is strictly better: no read of a mutable static, no visibility question | a constant variable "must always appear to have been initialized" (13.1); no race window |
| Allocation tricks | zero; the `int` is an instruction operand, the `String` an interned pool entry | same; the boxing fix reintroduces one `Integer`, cached for both 10 and 8, so still no allocation | none |
| Why the JDK bothers | free reads, no class initialisation, conditional compilation | identical motive, and the reason `Integer.MAX_VALUE` is shaped this way | 13.4.9 names conditional compilation (14.22) as the deciding reason |
| What it cannot show | a jar upgraded in place; a stale dependent whose source you do not have; a build cache serving a stale class | exactly those | 13.4.9 classifies all of them as binary compatible, so no tool is obliged to notice |

---

## Pitfalls

### Believing that recompiling the declaring class is enough

**Wrong**

```bash
javac BonusRules.java     # the file I changed
java BonusService | grep 'percentInUse\|BONUS_CODE\|grant on'
```

```console
percentInUse()       = 10
BONUS_CODE           = AA-801
grant on deposit 65  = 6.50
grant on deposit 480 = 48.00
```

The source says 8 and `AA-711`. The program says 10 and `AA-801`, and grants 6.50 instead of 5.20.

**Right**

```bash
javac BonusRules.java BonusService.java
java BonusService | grep 'percentInUse\|BONUS_CODE\|grant on'
```

```console
percentInUse()       = 8
BONUS_CODE           = AA-711
grant on deposit 65  = 5.20
grant on deposit 480 = 38.40
```

Every reader must be recompiled, because the value lives in every reader's constant pool. The
declaring class file is not consulted at runtime for that field at all.

**Why people believe it:** every other kind of change works that way — change a method body,
recompile that class, and callers pick it up through the `invokevirtual` at runtime. Late binding
is the rule for methods; constants are the exception nobody mentions.

### Believing `final` is what causes the inlining

**Wrong**

```java
// "It is final, so I must add a getter to avoid the inlining problem."
public static final BigDecimal BONUS_CAP = new BigDecimal("100");
```

```console
      30: getstatic     #36                 // Field BonusRules.BONUS_CAP:Ljava/math/BigDecimal;
```

Nothing was inlined. `javap -v` shows no `ConstantValue` attribute on this field. The accessor
adds a method call and fixes nothing that was broken.

**Right**

```java
public static final int BONUS_PERCENT = 10;                        // constant variable
public static final BigDecimal BONUS_CAP = new BigDecimal("100");  // not one
```

```console
  public static final int BONUS_PERCENT;
    ConstantValue: int 10

  public static final java.math.BigDecimal BONUS_CAP;
    descriptor: Ljava/math/BigDecimal;
    flags: (0x0019) ACC_PUBLIC, ACC_STATIC, ACC_FINAL
```

Three conditions, all required: `static`, `final`, and an initialiser that is a constant expression
over a primitive or `String`. `ACC_FINAL` in the flags tells you nothing; the presence of
`ConstantValue` tells you everything.

**Why people believe it:** `final` is the visible keyword and "final means fixed" is the mental
model everyone arrives with. The type and constant-expression restrictions live in JLS 4.12.4 and
15.29, which nobody reads before writing a constant.

### Putting the tunable value on an interface

**Wrong**

```java
public interface BonusTuning { int BONUS_PERCENT = 10; }
```

Edit to `8`, recompile only `BonusTuning.java`, rerun `BonusAudit`, and it still prints
`interface BONUS_PERCENT = 10` — the demonstration in section 5, with the `ldc` to prove it.
Interface fields are implicitly `public static final` (JLS 9.3), so they are constant variables by
default; the interface makes it *more* likely, not less.

**Right**

```java
public interface BonusTuning {
    static int bonusPercent() {
        return 10;
    }
}
```

A `static` interface method compiles to `invokestatic` at every call site, so the value resolves
at runtime and a partial recompile propagates it.

**Why people believe it:** the "constants interface" was a real pre-enum idiom, and interfaces feel
like declaration-only files with no runtime presence — exactly backwards here, because having no
runtime presence is what makes the value get copied into everyone.

---

## Cheat sheet

| Question | Answer |
|---|---|
| What gets inlined | `static final` primitive or `String` initialised with a constant expression (JLS 4.12.4) |
| What does not | `new` anything, any method call, `null`, non-`final`, non-primitive/non-`String` types |
| Where the value lives | declarer: the field's `ConstantValue` attribute. Reader: the reader's own constant pool |
| Reader's bytecode when inlined | `bipush` / `ldc` / `ldc2_w`; no `getstatic`, no `Fieldref`, no `Class` entry for the declarer |
| Reader's bytecode when not inlined | `getstatic Declarer.FIELD` |
| Does an inlined read initialise the declarer | no |
| Does changing the value break linkage | no — binary compatible, behaviourally incompatible (JLS 13.4.9) |
| Does deleting an inlined constant break linkage | no; deleting a non-constant field gives `NoSuchFieldError` |
| Interface constants | implicitly `public static final`, so inlined identically |
| `static final String` vs `static final int` | no difference; the `String` is additionally interned in the reader |
| `javac -Xlint:all` | says nothing, exit 0. Gradle falls back to a full source-set recompile |
| Fixes | `private static` plus a `static` accessor (the JLS's own advice); boxed or non-primitive type; configuration |
| Why it exists | free reads, no class initialisation, conditional compilation (`if (DEBUG)`) |
| How to spot it in the wild | two components disagree about a value that appears once in the source |

---

## Self-test

**Q1.** `BONUS_PERCENT` changed from 10 to 8 and only its declaring class was recompiled. Why does
the caller still print 10, and what would the JVM have to do to notice?

<details><summary>Answer</summary>

Because the caller's class file contains no reference to the field. `javac` resolved
`BonusRules.BONUS_PERCENT` at compile time to the value 10 and emitted `bipush 10` — JLS 13.1 item
3 requires exactly this, saying no reference to a `static` constant variable "should be present in
the code in a binary file". There is no `Fieldref` on account of that field, so there is nothing
for the JVM to resolve or compare. To notice, the JVM would have to record which constants each
class inlined and at what values, then verify them at link time — information that is not in the
class file format and that the JLS declines to require, since the change is binary compatible.

</details>

**Q2.** `BONUS_CAP` is `public static final BigDecimal`. Why did it pick up its new value without
recompiling the reader?

<details><summary>Answer</summary>

Because it is not a constant variable. JLS 4.12.4 restricts constant variables to primitive types
and `String`, and JLS 15.29 does not admit `new` into a constant expression, so
`new BigDecimal("100")` disqualifies it twice over. `javap -v` shows no `ConstantValue` attribute
on the field, and the reader emits `getstatic BonusRules.BONUS_CAP:Ljava/math/BigDecimal;`, which
resolves at runtime against whatever class file is on the classpath. The assignment itself happens
in `BonusRules`' `<clinit>`, which runs in the recompiled class.

</details>

**Q3.** In the stage-1 output, `[BonusRules class initialiser ran]` printed *third*, after two
lines that read fields of `BonusRules`. Explain.

<details><summary>Answer</summary>

The first two lines read `BONUS_PERCENT` and `BONUS_CODE`, both inlined, so the emitted
instructions were a `bipush` and an `ldc` of a folded `String` — neither mentions `BonusRules`, so
neither is a class-initialisation trigger under JVMS 5.5. The third line reads `BONUS_CAP` via
`getstatic`, which *is* a trigger, and that is when `<clinit>` ran and printed. The ordering is
direct evidence that inlined reads carry no dependency on the declaring class.
[Class-initialization order](05g-class-initialization-order.md) covers the trigger rules.

</details>

**Q4.** Does declaring the constant on an interface instead of a class avoid the problem?

<details><summary>Answer</summary>

No, it makes it more likely. Interface fields are implicitly `public static final` (JLS 9.3), so
`int BONUS_PERCENT = 10;` in an interface is a constant variable whether or not you wrote the
modifiers; it gets a `ConstantValue` attribute and is inlined into every reader. The demonstration
above changes the interface's value from 10 to 8, recompiles only the interface, and the reader
still prints 10 — and that reader does not even implement the interface. If constants must live on
an interface, expose them through a `static` interface method, which compiles to `invokestatic`.

</details>

**Q5.** `static final int GRANTS_PER_DAY = Integer.parseInt(System.getProperty("quizstakes.bonus.grantsPerDay", "3100"));`
is `static`, `final`, of type `int`, and its value never changes after startup. Is it inlined?

<details><summary>Answer</summary>

No. Constant-ness is a property of the *initialiser expression*, not of whether the value happens
to be stable. `Integer.parseInt` and `System.getProperty` are method invocations, and JLS 15.29
does not admit method invocations into constant expressions, so the field is not a constant
variable. `javap -v` shows no `ConstantValue` attribute on it, and every reader emits
`getstatic BonusRules.GRANTS_PER_DAY:I`. Consequently it also *does* trigger initialisation of
`BonusRules` when read, and it *does* pick up a change on a partial recompile.

</details>

---

## Open questions

- **Unverified:** whether Gradle's constant-change fallback to full recompilation extends across
  project boundaries to consuming projects in the same build, or recompiles only the source set
  owning the changed constant. Settled by a two-project Gradle build run with `--info`, reading the
  incremental-compilation decision for the consumer against that Gradle version's userguide.
- **Unverified:** whether `maven-compiler-plugin`'s incremental staleness check models constant
  dependencies at all. My belief is that it compares source and class timestamps only, making
  `mvn clean` the sole reliable remedy; not confirmed against the plugin's documentation.
- **Unverified:** the exact current wording of the Gradle userguide sentence quoted in section 10;
  read from the "current" docs URL rather than a pinned version, so re-check your own Gradle's docs.

---

**Leaves covered:** 4.8.5 (1 leaf)
**Leaves deferred:** none
**Diagrams included:** none
**Target version:** Java 21 LTS
**Lines:** 899
