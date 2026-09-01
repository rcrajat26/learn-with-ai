# 03 Java Core — Diagnostic harnesses — the puzzler harness, snippets 1 to 8 — BUILD IT (§4.8.1)

**Target version: Java 21 LTS.** | **Part 4 of 5** | [Index](../00-index.md)
Previous: [The §4.7 diff against what a record gives you](04d-value-object-diff.md) · Next: [The puzzler harness, snippets 9–15](05f-puzzler-harness-part-two.md)

Fifteen expressions, each a few characters from something a QuizStakes ledger would have got wrong
in production, and every one decided by a rule you can name. The shape of what you are building:
one class, fifteen methods, one `main` that calls them in order, one captured run. When you can say
*which* rule fired — JLS 15.7's evaluation order, 15.25's conditional typing, 15.26.2's implicit
narrowing cast, 5.1.7's mandated cache range — you own the puzzle. When you can only say "Java is
odd there", the interviewer finds out in one follow-up. Every output below came from
`javac PuzzlerHarnessPartOne.java && java PuzzlerHarnessPartOne` on **Oracle JDK 21.0.7 (build
21.0.7+8-LTS-245), macOS aarch64**.

This file carries snippets **1 to 8**; [snippets 9 to 15](05f-puzzler-harness-part-two.md) carry the
rest of the leaf, along with the `Diff vs the real one` table, the measured `-Xlint` finding and the
full-harness `main`.

**Two of the eight here are commonly explained wrongly, including in the brief that commissioned
this file.** The ternary does *not* throw when the guard is true, and `i = i++` is *not* undefined
behaviour in Java. Both are corrected below against bytecode, not against memory. A third
correction, that `+` has not compiled to a `StringBuilder` chain since Java 8, lands with snippet 10
in the second file.

---

## The fifteen at a glance

| # | Snippet | Prints | Category |
|---|---|---|---|
| 1 | `i = i++` on a stake-scan counter | `0` | evaluation order |
| 2 | `'A' + 1` for the phase letter of `AA-610` | `66` | promotion |
| 3 | `stakeBlocked ? 0 : nullInteger`, guard true | `0`, **no NPE** | unboxing |
| 4 | `Integer 128 == Integer 128` | `false` | caching |
| 5 | `long w = 30 * 24 * 60 * 60 * 1000 * 1000` | `2134720512` | overflow |
| 6 | `Math.abs(Integer.MIN_VALUE)` | `-2147483648` | two's complement |
| 7 | `"3.2.1".split(".")` | `[]`, length 0 | regex |
| 8 | `0.1 + 0.2` as a bonus balance | `0.30000000000000004` | floating point |
| 9 | `new BigDecimal("2.0").equals(new BigDecimal("2.00"))` | `false` | scale equality |
| 10 | `"coupon=" + nullString` | `coupon=null`, length 11 | concatenation |
| 11 | `restrictionMask << 32` on an `int` | unchanged, `11` | shift masking |
| 12 | `byte retryBudget = 10; retryBudget += 300;` | `54` | narrowing |
| 13 | `Math.round(-2.5)` | `-2` | rounding |
| 14 | `static railName()` through a base-typed reference | `bank-withdrawal` | dispatch |
| 15 | one object, two reference types, two `maxStakeMinor` | `100` / `500` | hiding |

Rows 9 to 15 are covered in [the second file](05f-puzzler-harness-part-two.md); the table stays whole
here because it is the map for the leaf. Read the category column as the question behind the
question — snippet 12 is not about `byte`, it asks whether you know compound assignment carries a
cast the plain form does not.

---

## 1 — `i = i++`: the store wins

```java
static void selfAssignedIncrement() {
    int reservationsScanned = 0;
    reservationsScanned = reservationsScanned++;
    System.out.println("01 i = i++                    : " + reservationsScanned);
}
```

```text
01 i = i++                    : 0
```

**Mechanism.** JLS 15.26.1 fixes the order inside a simple assignment: the target location is
determined, the right-hand operand is fully evaluated, then the value is stored. Postfix `++`
(JLS 15.14.2) yields the *old* value and increments as a side effect, so the increment happens and
the store overwrites it with the value captured before it.

```text
static int selfAssign();
  Code:
     0: iconst_0
     1: istore_0
     2: iload_0
     3: iinc          0, 1
     6: istore_0
     7: iload_0
     8: ireturn
```

`iload_0` pushes the current `0` onto the operand stack. `iinc 0, 1` increments local slot 0 **in
place without touching the stack** — the slot now holds `1`, the stack still holds `0`. `istore_0`
pops that stale `0` back into slot 0. Three instructions, and the third erases the second.

**Interview:** the follow-up is always "and in C?" There it is *undefined behaviour* — no sequencing
guarantee between the increment and the assignment. Java removed that freedom deliberately: JLS
15.7 mandates left-to-right operand evaluation, so `i = i++` is well defined and always leaves `i`
unchanged. `../primitives-and-conversions/02-operators-and-expressions.md` owns evaluation order.

---

## 2 — `char + int`: binary numeric promotion eats the `char`

```java
static void charPlusIntPromotes() {
    char phaseLetter = 'A';                 // the 'A' of AA-610
    System.out.println("02 'A' + 1 (int)              : " + (phaseLetter + 1));
    System.out.println("02 (char)('A' + 1)            : " + (char) (phaseLetter + 1));
    char advanced = phaseLetter;
    advanced += 1;
    System.out.println("02 'A' += 1 (char)            : " + advanced);
}
```

```text
02 'A' + 1 (int)              : 66
02 (char)('A' + 1)            : B
02 'A' += 1 (char)            : B
```

**Mechanism.** `+` on `char` and `int` triggers binary numeric promotion (JLS 5.6.2): the `char`
widens to `int`, the addition is `int` addition, and the expression's type is `int`. No rule returns
the result to `char`, so `'A' + 1` is the `int` 66 and concatenation renders it as digits; the
explicit cast reinterprets 66 as U+0042 and prints `B`. The third line is the bridge to
[snippet 12](05f-puzzler-harness-part-two.md) —
`advanced += 1` compiles and stays a `char` because compound assignment inserts an implicit
narrowing cast (JLS 15.26.2). Same arithmetic, one hidden cast apart.
`../primitives-and-conversions/02a-assignment-and-bitwise.md` owns that cast.

---

## 3 — Ternary unboxing: the myth and the mechanism

```java
static void ternaryUnboxingThrows() {
    Integer unknownStakeCount = null;
    boolean stakeBlocked = true;
    try {
        int stakes = stakeBlocked ? 0 : unknownStakeCount;
        System.out.println("03a guard true, null in else  : " + stakes);
    } catch (NullPointerException e) {
        System.out.println("03a guard true, null in else  : NullPointerException");
    }
    try {
        int stakes = !stakeBlocked ? 0 : unknownStakeCount;
        System.out.println("03b guard false, null taken   : " + stakes);
    } catch (NullPointerException e) {
        System.out.println("03b guard false, null taken   : NullPointerException");
    }
    Integer boxedCount = 42;
    Object promoted = stakeBlocked ? boxedCount : 0.0;
    System.out.println("03c true ? Integer(42) : 0.0  : " + promoted
            + " of type " + promoted.getClass().getSimpleName());
    Object bothReference = stakeBlocked ? (Integer) 0 : unknownStakeCount;
    System.out.println("03d both operands reference   : " + bothReference);
}
```

```text
03a guard true, null in else  : 0
03b guard false, null taken   : NullPointerException
03c true ? Integer(42) : 0.0  : 42.0 of type Double
03d both operands reference   : 0
```

**Mechanism, and the correction.** The widely-repeated claim is that `flag ? 1 : nullInteger` throws
even when `flag` is true, "because unboxing applies to the expression's type rather than to the
branch taken". Line `03a` disproves it. JLS 15.25 classifies this as a *numeric* conditional
expression — operand types `int` and `Integer` give expression type `int` by Table 15.25-B, so the
`Integer` operand is subject to unboxing — but 15.25 equally says only **one** of the two operands
is evaluated, and the conversion applies to the value that operand produced.

```text
static int ternary(boolean, java.lang.Integer);
  Code:
     0: iload_0
     1: ifeq          8
     4: iconst_0
     5: goto          12
     8: aload_1
     9: invokevirtual #11                 // Method java/lang/Integer.intValue:()I
    12: ireturn
```

`ifeq 8` jumps to the else-arm only when the guard is false. `iconst_0` / `goto 12` is the then-arm:
push `0`, skip everything else. The `invokevirtual intValue` at offset 9 is reachable **only**
through that jump. An unevaluated operand cannot throw, so `03a` prints `0` and `03b`, where the
null operand *is* taken, throws.

**Insight:** the real trap is the type, not a null. In `03c` the untaken operand `0.0` is a
`double`, so Table 15.25-B promotes the whole expression to `double` and the `Integer` is unboxed,
widened and reboxed as a `Double`:

```text
static java.lang.Object promotedTernary(boolean, java.lang.Integer);
  Code:
     0: iload_0
     1: ifeq          12
     4: aload_1
     5: invokevirtual #11                 // Method java/lang/Integer.intValue:()I
     8: i2d
     9: goto          13
    12: dconst_0
    13: invokestatic  #17                 // Method java/lang/Double.valueOf:(D)Ljava/lang/Double;
    16: areturn
```

`intValue` unboxes, `i2d` widens, `Double.valueOf` boxes. An `Integer` went in and a `Double` came
out, decided by an operand never evaluated — and had `boxedCount` been null, offset 5 would throw
*on the taken branch*, which is where the myth comes from. Line `03d` is the escape hatch: make both
operands reference types and 15.25 takes the reference conditional path with no unboxing at all.
`../primitives-and-conversions/02c-conditional-operator.md` owns the 15.25 tables.

---

## 4 — The `Integer` cache boundary at 127/128

```java
static void integerCacheBoundary() {
    Integer operatorsOnShiftLow = 127, operatorsAgainLow = 127;
    Integer operatorsOnShift = 128, operatorsAgain = 128;
    System.out.println("04 127 == 127                 : " + (operatorsOnShiftLow == operatorsAgainLow));
    System.out.println("04 128 == 128                 : " + (operatorsOnShift == operatorsAgain));
    System.out.println("04 128.equals(128)            : " + operatorsOnShift.equals(operatorsAgain));
}
```

```text
04 127 == 127                 : true
04 128 == 128                 : false
04 128.equals(128)            : true
```

**Mechanism.** Boxing in assignment context compiles to `Integer.valueOf(int)`, whose JDK 21 body is
three lines:

```java
public static Integer valueOf(int i) {
    if (i >= IntegerCache.low && i <= IntegerCache.high)
        return IntegerCache.cache[i + (-IntegerCache.low)];
    return new Integer(i);
}
```

Inside the range you get the *same object* twice, so `==` is true by accident; one past the top bound
you get two fresh objects and it is false. JLS 5.1.7 mandates caching only for −128..127, so 127 is
the last value any conforming JVM must intern. `equals` compares the wrapped `int` and is unaffected.

**The tunability is asymmetric.** `low` is `static final int low = -128;`, a compile-time constant
with no property read. The upper bound is read at class-init from
`java.lang.Integer.IntegerCache.high` and floored at 127 by `h = Math.max(parseInt(prop), 127)`;
`-XX:AutoBoxCacheMax` sets that same property. Measured on 21.0.7, with `Integer a = 1000, b = 1000`
and `Integer lowA = -129, lowB = -129`:

| Configuration | `a == b` | `lowA == lowB` |
|---|---|---|
| default | `false` | `false` |
| `-XX:AutoBoxCacheMax=2000` | `true` | `false` |
| `-Djava.lang.Integer.IntegerCache.high=2000` | `true` | `false` |

Widening the cache widens the range over which `==` silently works, making the bug harder to find,
not easier. `../wrappers-and-boxing/01a-the-wrapper-caches.md` owns the cache;
`../wrappers-and-boxing/01a2-the-archived-cache.md` owns the CDS-archived variant.

---

## 5 — Overflow before the widening

```java
static void overflowBeforeWidening() {
    long bonusWindowMicros = 30 * 24 * 60 * 60 * 1000 * 1000;
    System.out.println("05 30d micros, int math       : " + bonusWindowMicros);
    long fixedWithSuffix = 30L * 24 * 60 * 60 * 1000 * 1000;
    System.out.println("05 30d micros, long math      : " + fixedWithSuffix);
    try {
        int caught = Math.multiplyExact(30 * 24 * 60 * 60 * 1000, 1000);
        System.out.println("05 Math.multiplyExact        : " + caught);
    } catch (ArithmeticException e) {
        System.out.println("05 Math.multiplyExact(int)    : ArithmeticException: " + e.getMessage());
    }
}
```

```text
05 30d micros, int math       : 2134720512
05 30d micros, long math      : 2592000000000
05 Math.multiplyExact(int)    : ArithmeticException: integer overflow
```

**Mechanism.** Bonus expiry is 30 days from grant. Every literal is an `int`, so every
multiplication is `int` multiplication, and JLS 15.17.1 specifies that as wrapping modulo 2^32 with
**no** overflow indication: 2,592,000,000,000 − 603 × 4,294,967,296 = 2,134,720,512. Only then does
widening to `long` happen (JLS 5.1.2), faithfully widening the already-wrong `int` — the declared
type of the variable never reaches back into the expression. `30L` makes the first operand a `long`
so promotion carries through every subsequent multiplication; `Math.multiplyExact(int, int)` does
the same `int` arithmetic but throws instead of wrapping, which is the right choice where a silent
wrong number is worse than a failed request.
`../primitives-and-conversions/01a-integral-arithmetic.md` owns wrapping and the `*Exact` family.

---

## 6 — `Math.abs(Integer.MIN_VALUE)` is negative

```java
static void absOfMostNegative() {
    int ledgerDelta = Integer.MIN_VALUE;
    System.out.println("06 Math.abs(MIN_VALUE)        : " + Math.abs(ledgerDelta));
    System.out.println("06 abs(MIN_VALUE) < 0         : " + (Math.abs(ledgerDelta) < 0));
    try {
        System.out.println("06 Math.absExact              : " + Math.absExact(ledgerDelta));
    } catch (ArithmeticException e) {
        System.out.println("06 Math.absExact(MIN_VALUE)   : ArithmeticException: " + e.getMessage());
    }
}
```

```text
06 Math.abs(MIN_VALUE)        : -2147483648
06 abs(MIN_VALUE) < 0         : true
06 Math.absExact(MIN_VALUE)   : ArithmeticException: Overflow to represent absolute value of Integer.MIN_VALUE
```

**Mechanism.** Two's complement over 32 bits covers −2^31..2^31−1, asymmetric by one because zero
occupies a slot on the non-negative side, so `+2147483648` is simply not an `int`. `Math.abs` is
specified to return the argument unchanged for `Integer.MIN_VALUE`, which means a ledger-delta
magnitude check written `Math.abs(delta) < limit` passes for the one value that most needs
rejecting. The strict alternative is `Math.absExact`, whose JDK 21 body tests for
`Integer.MIN_VALUE` and throws the `ArithmeticException` captured above; it was added in **Java 15**
and both the `int` and `long` overloads are present in 21, verified by running it.
`../primitives-and-conversions/01a-integral-arithmetic.md` owns two's complement and `Math.abs`.

---

## 7 — `split` takes a regex, then discards trailing empties

```java
static void splitTakesARegex() {
    String schemaVersion = "3.2.1";
    System.out.println("07 \"3.2.1\".split(\".\")        : " + Arrays.toString(schemaVersion.split(".")) + " length=" + schemaVersion.split(".").length);
    System.out.println("07 split(\"\\\\.\")               : " + Arrays.toString(schemaVersion.split("\\.")));
    System.out.println("07 split(Pattern.quote(\".\"))  : " + Arrays.toString(schemaVersion.split(java.util.regex.Pattern.quote("."))));
    String status = "AA-610-";
    System.out.println("07 \"AA-610-\".split(\"-\")       : " + Arrays.toString(status.split("-")) + " length=" + status.split("-").length);
    System.out.println("07 same with limit -1         : " + Arrays.toString(status.split("-", -1)) + " length=" + status.split("-", -1).length);
}
```

```text
07 "3.2.1".split(".")        : [] length=0
07 split("\\.")               : [3, 2, 1]
07 split(Pattern.quote("."))  : [3, 2, 1]
07 "AA-610-".split("-")       : [AA, 610] length=2
07 same with limit -1         : [AA, 610, ] length=3
```

**Mechanism, both halves.** `String.split(String)` interprets its argument as a *regular
expression*, and `.` is the metacharacter matching any character except a line terminator — so every
character of `"3.2.1"` is a delimiter, every field is empty, and the zero-limit rule removes all
trailing empty strings, collapsing five empties to length **0**. `Pattern.quote(".")` wraps the
argument in the literal-quote escape so it matches as text; `"\\."` escapes the metacharacter
directly. The second half bites on well-formed delimiters too: `"AA-610-".split("-")` discards the
empty field after the final `-` and reports length 2 for a three-field status string, while a
**negative** limit keeps every trailing empty and reports 3. Any parser that round-trips `AA-610-`
by splitting and rejoining loses the trailing separator unless it passes `-1`.
`../strings/01-basics.md` owns `split`, `Pattern.quote` and the limit rule.

---

## 8 — `0.1 + 0.2` as a bonus balance

```java
static void binaryFloatingPointSum() {
    double bonusBalance = 0.1 + 0.2;
    System.out.println("08 0.1 + 0.2                  : " + bonusBalance);
    System.out.println("08 == 0.3                     : " + (bonusBalance == 0.3));
    System.out.println("08 exact value of the sum     : " + new BigDecimal(bonusBalance));
}
```

```text
08 0.1 + 0.2                  : 0.30000000000000004
08 == 0.3                     : false
08 exact value of the sum     : 0.3000000000000000444089209850062616169452667236328125
```

**Mechanism.** IEEE 754 binary64 holds a sign, an 11-bit exponent and a 53-bit significand, all base
2, so it represents only rationals whose denominator is a power of two; 1/10 is not one, so `0.1` and
`0.2` are each stored as the nearest representable neighbour. Their exact sum is not representable
either, so the addition rounds a second time (round-to-nearest-even, JLS 15.18.2) and lands one ulp
above the double nearest `0.3`. The third line proves it: `new BigDecimal(double)` takes the double's
*exact* value rather than its shortest round-trip string. A bonus balance is money, so the fix is not
a tolerance but `BigDecimal` with an explicit scale, or minor units in a `long` — the canonical
QuizStakes case is a stake of 3.33 splitting as 0.33 bonus + 3.00 cash, where the wrong type stops
the two parts summing to the stake. `../primitives-and-conversions/01c-floating-point.md` owns
binary64.

---

## The driver for snippets 1 to 8

The eight methods above are the harness. `PuzzlerHarnessPartOne` is a driver of its own that runs
exactly this file's half, so you can compile and execute the first eight without waiting for the
other seven:

```java
public static void main(String[] args) {
    selfAssignedIncrement();
    charPlusIntPromotes();
    ternaryUnboxingThrows();
    integerCacheBoundary();
    overflowBeforeWidening();
    absOfMostNegative();
    splitTakesARegex();
    binaryFloatingPointSum();
}
```

The class needs only `java.math.BigDecimal` and `java.util.Arrays` imported; there are no nested
classes in this half, since the two class pairs belong to snippets 14 and 15. Compiled and run on
21.0.7, the whole half produces 25 lines:

```text
01 i = i++                    : 0
02 'A' + 1 (int)              : 66
02 (char)('A' + 1)            : B
02 'A' += 1 (char)            : B
03a guard true, null in else  : 0
03b guard false, null taken   : NullPointerException
03c true ? Integer(42) : 0.0  : 42.0 of type Double
03d both operands reference   : 0
04 127 == 127                 : true
04 128 == 128                 : false
04 128.equals(128)            : true
05 30d micros, int math       : 2134720512
05 30d micros, long math      : 2592000000000
05 Math.multiplyExact(int)    : ArithmeticException: integer overflow
06 Math.abs(MIN_VALUE)        : -2147483648
06 abs(MIN_VALUE) < 0         : true
06 Math.absExact(MIN_VALUE)   : ArithmeticException: Overflow to represent absolute value of Integer.MIN_VALUE
07 "3.2.1".split(".")        : [] length=0
07 split("\\.")               : [3, 2, 1]
07 split(Pattern.quote("."))  : [3, 2, 1]
07 "AA-610-".split("-")       : [AA, 610] length=2
07 same with limit -1         : [AA, 610, ] length=3
08 0.1 + 0.2                  : 0.30000000000000004
08 == 0.3                     : false
08 exact value of the sum     : 0.3000000000000000444089209850062616169452667236328125
```

Nothing escapes `main` — the three methods that provoke an exception catch it and print it, so the
driver's exit status is zero and a failed line is a printed line rather than a stopped run. That is
the one design decision in the harness worth copying: a diagnostic that aborts on its first surprise
only ever teaches you one thing per run.

> A diagnostic harness is a program whose output is its argument: it does not describe what the
> language does, it makes the language do it and captures the result.

**Interview:** asked to explain any of these eight, name the rule and its number before you name the
output. "It prints 66" is a memorised fact; "binary numeric promotion, JLS 5.6.2, so the expression's
type is `int` and there is no rule that returns it to `char`" is the answer that survives the
follow-up.

**Gotcha for this half:** all eight are *specified*. None is a bug, none is implementation-defined,
none will be fixed. The surprise is a gap between your model and the spec, and the harness closes it
by measurement instead of by memory.

---

## Pitfalls

### Believing the ternary unboxes both operands

**Wrong**

```java
Integer unknownStakeCount = null;
boolean stakeBlocked = true;
int stakes = stakeBlocked ? 0 : unknownStakeCount;   // "throws NPE regardless of the guard"
```

Actual output: `0`. No exception — the `invokevirtual Integer.intValue` sits behind `ifeq` and is
never reached when the guard is true.

**Right**

```java
Integer boxedCount = 42;
Object promoted = stakeBlocked ? boxedCount : 0.0;   // 42.0, a Double
```

The untaken operand *does* change the expression's type (JLS 15.25, Table 15.25-B), and that is the
real hazard: an `Integer` becomes a `Double`, and if it were null the unboxing on the *taken* branch
would throw. Make both operands reference types to take the reference conditional path and skip
unboxing entirely.

**Why people believe it:** the correct half of the rule — that the *type* is computed from both
operands — gets over-extended into the *evaluation*, which is the one thing 15.25 explicitly
restricts to a single operand.

### Trusting `split` with a punctuation delimiter

**Wrong**

```java
String[] parts = "3.2.1".split(".");
System.out.println(parts.length + " " + Arrays.toString(parts));
```

Actual output: `0 []`. Not three parts, not five empties — an empty array, so the next line throws
`ArrayIndexOutOfBoundsException` on `parts[0]`.

**Right**

```java
String[] parts = "3.2.1".split(Pattern.quote("."));      // [3, 2, 1]
String[] fields = "AA-610-".split("-", -1);              // [AA, 610, ] keeps the trailing empty
```

`Pattern.quote` for a literal delimiter, and a negative `limit` whenever a trailing empty field is
meaningful.

**Why people believe it:** the method is on `String`, is named `split`, and takes a `String` — no
part of the signature says "regex" — and it behaves correctly for the delimiters people test first,
`,` and `;`. The name lies about the contract.

---

### Calling `i = i++` undefined behaviour in Java

**Wrong**

```java
int reservationsScanned = 0;
reservationsScanned = reservationsScanned++;   // "undefined — the compiler may do anything"
```

Actual output: `0`, on every conforming JVM, every time. The claim is imported from C, where this
expression genuinely *is* undefined behaviour because the standard imposes no sequencing between the
increment and the assignment.

**Right**

```java
int reservationsScanned = 0;
reservationsScanned++;                          // 1 — say what you mean
```

Java specifies the whole thing. JLS 15.7 mandates left-to-right operand evaluation, JLS 15.26.1
fixes the order inside a simple assignment, and JLS 15.14.2 makes postfix `++` yield the old value.
The bytecode `iload_0; iinc 0, 1; istore_0` is therefore the *only* legal compilation, and the
result is `0` by specification rather than by luck.

**Why people believe it:** every C and C++ style guide files `i = i++` under "undefined behaviour,
never write it", the advice not to write it is correct in Java too, and the reason gets carried
across with the advice. The interview follow-up is exactly this distinction, and answering
"undefined" fails it — the right answer is "well defined, and it leaves `i` unchanged".

### Expecting `'A' + 1` to stay a `char`

**Wrong**

```java
char phaseLetter = 'A';
System.out.println("phase " + (phaseLetter + 1));   // expecting "phase B"
```

Actual output: `phase 66`. Building a status prefix this way turns `AA-610` into `66A-610` in a log
line, and the bug survives review because the expression reads like character arithmetic.

**Right**

```java
char phaseLetter = 'A';
System.out.println("phase " + (char) (phaseLetter + 1));   // phase B
char advanced = phaseLetter;
advanced += 1;                                             // also B, cast is implicit
```

Binary numeric promotion (JLS 5.6.2) makes `+` on `char` and `int` an `int` addition with an `int`
result, and nothing narrows it back. Either cast explicitly, or use `+=`, whose specified expansion
(JLS 15.26.2) inserts the narrowing cast for you.

**Why people believe it:** `char` prints as a character, compares with `<` like a number, and
indexes into strings, so it behaves like a distinct character type in every context except the one
that matters. The `+=` form working correctly reinforces the wrong model — it looks like proof that
`char` arithmetic stays `char`, when in fact it is proof that compound assignment hides a cast.

---

## Cheat sheet

| Puzzle | Result | Rule | Fix |
|---|---|---|---|
| `i = i++` | unchanged | JLS 15.26.1: `iload`, `iinc`, `istore`; defined, not UB | `i++;` alone |
| `'A' + 1` | `66` | JLS 5.6.2 promotion to `int` | cast to `char`, or `+=` |
| `true ? 0 : nullInteger` | `0`, no NPE | JLS 15.25: type from both, evaluation of one | both operands reference-typed |
| `true ? boxedInt : 0.0` | a `Double` | Table 15.25-B promotes to `double` | keep operand types equal |
| `Integer 128 == 128` | `false` | `valueOf` caches −128..127 (JLS 5.1.7) | `equals`, or `intValue()` |
| `Integer -129 == -129` | `false`, untunable | `low` is a compile-time `-128`; only `high` reads a property | never compare wrappers with `==` |
| `long` from `int` product | `2134720512` | `int` multiply wraps mod 2^32 before widening | `30L` first, `Math.multiplyExact` |
| `Math.abs(MIN_VALUE)` | negative | two's complement asymmetric by one | `Math.absExact`, Java 15+ |
| `"3.2.1".split(".")` | `[]` | regex `.` matches all; trailing empties dropped | `Pattern.quote`, limit `-1` |
| `"AA-610-".split("-")` | length 2 | zero limit discards trailing empties | pass limit `-1` |
| `0.1 + 0.2` | `0.30000000000000004` | binary64 cannot hold 1/10 | `BigDecimal`, or minor units |
| `new BigDecimal(double)` | 55 digits | takes the double's *exact* value | `BigDecimal.valueOf`, or the `String` form |

---

## Self-test

Different snippets from the fifteen. Predict before unfolding; all outputs below were captured on
21.0.7.

**Q1.** `int reservations = 0; int result = reservations++ + ++reservations;` — `result` and
`reservations`?

<details><summary>Answer</summary>

`result` is 2 and `reservations` is 2. Evaluation is left to right (JLS 15.7): `reservations++`
yields the old `0` and leaves the variable at 1, then `++reservations` increments to 2 and yields 2,
so the sum is 0 + 2. Unlike `i = i++` nothing is overwritten — both side effects survive because
neither is followed by a store of a stale value. The bytecode is
`iload_0; iinc 0,1; iinc 0,1; iload_0; iadd`, and the two `iinc`s are separated by nothing that
reads the stack.

</details>

**Q2.** `Long depositCount = 95000L; System.out.println(depositCount.equals(95000));`

<details><summary>Answer</summary>

`false`. The literal `95000` is an `int`, so it boxes to an `Integer`, and `Long.equals` begins with
an `instanceof Long` test that an `Integer` fails — it returns false without ever comparing numbers.
Numeric promotion is a rule about operators, not about method arguments. Write
`depositCount.equals(95000L)`, or `depositCount == 95000L`, which unboxes and compares as `long`.
This is the wrapper-equality sibling of snippet 4 and it silently breaks every `Map<Long, ?>` lookup
keyed with an `int` literal.

</details>

**Q3.** `System.out.println(-7 / 2); System.out.println(-7 % 2); System.out.println(Math.floorMod(-7, 2));`

<details><summary>Answer</summary>

`-3`, `-1`, `1`. JLS 15.17.2 specifies integer division as truncating toward zero, so −7/2 is −3 and
not −4. JLS 15.17.3 then requires `(a/b)*b + (a%b) == a`, which forces the remainder to carry the
sign of the *dividend*: −3 × 2 + (−1) = −7. `Math.floorMod` divides with floor semantics and always
returns a result with the sign of the divisor, which is what bucketing needs — a shard index computed
with `%` on a negative hash is negative and indexes out of the array.

</details>

**Q4.** `double ledgerTotal = 1e16; System.out.println(ledgerTotal + 1 == ledgerTotal);`

<details><summary>Answer</summary>

`true`. At 1e16 the gap between adjacent binary64 values is 2, so `1` is less than half a step and
round-to-nearest returns the same double. Adding 1 is a no-op, and a loop that accumulates 7.2B
ledger entries into a `double` stops making progress long before it finishes. This is the argument
for `long` minor units at QuizStakes' 19.8M entries per day: a `long` counts exactly to
9.2 × 10^18 minor units with no silent stall.

</details>

---

**Q5.** `System.out.println(1 / 2 * 2.0);` and `System.out.println(2.0 * 1 / 2);`

<details><summary>Answer</summary>

`0.0` and `1.0`. `*` and `/` share a precedence level and associate left to right, so the first
expression evaluates `1 / 2` first — both operands are `int`, so it is *integer* division and
truncates to `0` (JLS 15.17.2) — and only then promotes to `double` for the multiply. The second
expression promotes on its very first operation, so everything after it is `double` arithmetic. The
declared type of the destination is irrelevant in both cases, which is the same lesson as snippet
5's overflow: promotion is decided operand by operand, left to right, never by where the value is
going. A stake-to-bonus ratio computed as `bonusMinor / stakeMinor * 100` is this bug with a
plausible name.

</details>

**Q6.** `Map<String, Integer> openStakes` holds one entry for `client-4471`. What does
`int count = openStakes.get("client-9902");` do?

<details><summary>Answer</summary>

It throws `NullPointerException`. `HashMap.get` returns `null` for a missing key, the assignment
context requires an `int`, so JLS 5.1.8 applies an unboxing conversion — which is a call to
`Integer.intValue()` on a null reference. The stack trace points at the assignment line and names no
map method, which is why this reads as an impossible NPE on a line containing no visible
dereference. It is snippet 3's mechanism without the ternary: unboxing is the hazard, and the
conditional operator was only ever the delivery vehicle. Declare the variable `Integer`, or use
`getOrDefault("client-9902", 0)`.

</details>

---

## Open questions

- none

---

**Leaves covered:** 4.8.1 (snippets 1–8; snippets 9–15 are in 05f-puzzler-harness-part-two.md)
**Leaves deferred:** none
**Diagrams included:** none
**Target version:** Java 21 LTS
**Lines:** 703
