# 03 Java Core — Parsing traps and the statics — BASICS (§1.9, 1.9.14, 1.9.16, 1.9.17)

**Target version: Java 21 LTS.** | **Part 1 of 5** | [Index](../00-index.md)
Previous: [`parseInt` versus `valueOf(String)`](01e2-parseint-versus-valueof-string.md) · Next: [The cost of boxing](01g-the-cost-of-boxing.md)

Three unrelated things live in this file because they live in the same place in the JDK. The wrapper
classes are not just boxes; they are the platform's dumping ground for everything that is *about* a
primitive type. And two of the parsers that live there have failure policies that disagree with each
other in a way that quietly costs money at a validation boundary.

---

## 1. The statics inventory (1.9.14)

`[RESEARCH]` A wrapper class is four unrelated libraries wearing one name. `Integer` holds the
**limits and metadata** of the `int` type, the **parsers** that turn text into an `int`, the
**formatters** that turn an `int` into text, and a set of **bit primitives** that have nothing to do
with boxing at all. Nothing links them except the type they mention. That is why the class has 60-odd
static members and no coherent theme, and why remembering it as one API is hopeless. Remember it as
four groups.

Each group below is a table, because a table is what an inventory is. Every figure is measured on
JDK 21.0.7 (21.0.7+8-LTS-245); every member is confirmed present with that exact signature in
`java.base/java/lang/Integer.java` on that build.

### 1.1 Limits and metadata

| Member | Declared as | Measured value (`Integer` unless stated) |
|---|---|---|
| `MIN_VALUE` | `@Native public static final int MIN_VALUE = 0x80000000;` | `-2147483648` |
| `MAX_VALUE` | `@Native public static final int MAX_VALUE = 0x7fffffff;` | `2147483647` |
| `SIZE` | `@Native public static final int SIZE = 32;` | `32` — bits. `Long.SIZE = 64` |
| `BYTES` | `public static final int BYTES = SIZE / Byte.SIZE;` | `4` — derived, not a literal. `Long.BYTES = 8` |
| `TYPE` | `public static final Class<Integer> TYPE = (Class<Integer>) Class.getPrimitiveClass("int");` | prints `int`; `Integer.TYPE == int.class` is **true** |

Two of those rows deserve a sentence. `BYTES` is not an independent constant: its declaration in JDK
21 source is `SIZE / Byte.SIZE`, so `32 / 8 = 4` — the arithmetic is done by the compiler and folded
into the class file, and the same relation holds for every wrapper (`Long`: `64 / 8 = 8`;
`Character`: `16 / 8 = 2`).

`TYPE` is a `Class` object for the **primitive**, not for the wrapper. `Integer.TYPE` and
`int.class` are the same object — measured `true` — and they are the *only* two ways to name that
`Class` in Java source. This matters for reflection: a method declared `void reserve(int amount)`
reports `int.class` from `getParameterTypes()`, and a lookup keyed on `Integer.class` will not match
it. `TYPE` exists because before class literals on primitives were available it was the only handle.

`Character` is the one wrapper whose `MIN_VALUE` is not negative: `char` is unsigned, so
`(int) Character.MIN_VALUE = 0` and `(int) Character.MAX_VALUE = 65535` (both measured). Widths,
ranges and defaults for all eight primitives are tabulated once in
[`../primitives-and-conversions/01-basics.md`](../primitives-and-conversions/01-basics.md) and are
not restated here.

### 1.2 Formatters

| Method | Radix | Signed? | Measured |
|---|---|---|---|
| `toBinaryString(int)` | 2 | **unsigned** | `toBinaryString(-56)` = `11111111111111111111111111001000` |
| `toOctalString(int)` | 8 | **unsigned** | `toOctalString(56)` = `70` |
| `toHexString(int)` | 16 | **unsigned** | `toHexString(-56)` = `ffffffc8` |
| `toString(int, int)` | 2–36 | **signed** | `toString(255, 16)` = `ff`; `toString(-56, 2)` = `-111000` |

**Insight:** the three radix-specific formatters treat the value as **unsigned** — all 32 bits, no
sign, exactly what is in the register. `toString(int, radix)` treats it as **signed** and emits a
minus sign. Same number, two different strings: `-56` is `ffffffc8` through `toHexString` and
`-111000` through `toString(-56, 2)`. This is precisely the bug you get when one part of the codebase
dumps a restriction bit mask with `toBinaryString` and another logs it with `toString(mask, 2)` and
someone diffs the two logs.

The bounds behaviour of `toString(int, int)` is a genuine surprise, and it is in the source:

```java
public static String toString(int i, int radix) {
    if (radix < Character.MIN_RADIX || radix > Character.MAX_RADIX)
        radix = 10;
```

An out-of-range radix is **silently replaced by 10**. Measured: `Integer.toString(255, 1)` returns
`255` and `Integer.toString(255, 99)` returns `255`. Contrast `Integer.parseInt("12", 1)`, which
**throws** `NumberFormatException: radix 1 less than Character.MIN_RADIX`. Two methods, same class,
same illegal argument, opposite policies. Both measured; no rationale for the asymmetry is stated in
the JLS, the javadoc or the JDK bug database, so none is offered here.

`MIN_RADIX` is 2 and `MAX_RADIX` is 36 (`Character`), which is why 36 is the ceiling: ten digits plus
twenty-six letters.

### 1.3 Arithmetic and comparison helpers

| Method | Body in JDK 21 source | Measured |
|---|---|---|
| `compare(int, int)` | `(x < y) ? -1 : ((x == y) ? 0 : 1)` | `compare(1, 2)` = `-1` |
| `sum(int, int)` | `a + b` | `sum(3, 4)` = `7` |
| `max(int, int)` | `Math.max(a, b)` | `max(3, 4)` = `4` |
| `min(int, int)` | `Math.min(a, b)` | `min(3, 4)` = `3` |
| `signum(int)` | `(i >> 31) \| (-i >>> 31)` | `signum(-1200)` = `-1`; `signum(0)` = `0` |

`sum`, `min` and `max` look like pure noise — three static methods that wrap an operator and two
`Math` calls. They exist for one reason, and the javadoc says it outright: each carries
`@see java.util.function.BinaryOperator` and `@since 1.8`. They are **method-reference targets**.
`Integer::sum` is a `BinaryOperator<Integer>`; `a + b` is not a value and cannot be passed to
`Stream.reduce`. Without them, every reduction needed a lambda.

```java
int totalMinorUnits = reservations.stream()
        .map(Reservation::stakeMinorUnits)
        .reduce(0, Integer::sum);
```

They do **no** overflow checking — `Integer.sum` is `a + b`, silently wrapping in two's complement
exactly like the operator. If a reduction over 2.8M stake reservations can exceed
`Integer.MAX_VALUE`, `Integer::sum` will wrap without a sound; use `Math::addExact`, which throws
`ArithmeticException`, or reduce into a `long`. Two's complement wraparound is derived in
[`../primitives-and-conversions/01a-integral-arithmetic.md`](../primitives-and-conversions/01a-integral-arithmetic.md).

`compare` guarantees the **sign** of the result, not its magnitude. Its javadoc promises "a value
less than `0`", and the JDK 21 body happens to return exactly `-1`, `0` or `1` — but a test asserting
`assertEquals(-1, Integer.compare(a, b))` is asserting an implementation detail, not the contract.
The other half of the same lesson: `a - b` is not a substitute for `compare`, because subtraction
overflows. For two ledger ids near the ends of the range, `a - b` produces a value whose sign is the
opposite of the true ordering, and a `TreeMap` built on that comparator loses entries.

**Interview:** "Why is `Integer.compare(a, b)` preferred over `a - b` in a comparator?" — because
`a - b` overflows for operands far apart in the `int` range and reports the wrong sign, while
`compare` branches on `<` and `==` and cannot overflow.

### 1.4 Bit primitives

All six operate on the 32-bit two's-complement pattern and never touch boxing.

| Method | What it returns | Measured on `1200` |
|---|---|---|
| `bitCount(int)` | number of one-bits | `4` |
| `highestOneBit(int)` | the value of the most significant one-bit | `1024` |
| `numberOfLeadingZeros(int)` | zeros above the highest one-bit | `21` |
| `numberOfTrailingZeros(int)` | zeros below the lowest one-bit | `4` |
| `reverse(int)` | bit order reversed end-to-end | `220200960` |
| `rotateLeft(int, int)` | left shift with wraparound | `rotateLeft(1200, 4)` = `19200` |

`[NUM]` Do not memorise those. Derive them. `Integer.toBinaryString(1200)` is measured as
`10010110000`, and the arithmetic checks out: `1024 + 128 + 32 + 16 = 1200`. Lay the pattern against
its bit indices, high on the left:

| Bit index | 31–11 | 10 | 9 | 8 | 7 | 6 | 5 | 4 | 3 | 2 | 1 | 0 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Value | all 0 | 1 | 0 | 0 | 1 | 0 | 1 | 1 | 0 | 0 | 0 | 0 |

Now every figure falls out of that one row:

- **`bitCount`** — count the ones: bits 10, 7, 5, 4. That is **4**.
- **`highestOneBit`** — the highest one is bit 10, and its *value* (not its index) is
  `2^10 = 1024`. Note it returns the value, so `highestOneBit(0)` is `0` (measured) and
  `highestOneBit(-56)` is `-2147483648` (measured) because bit 31 is set in every negative number.
- **`numberOfLeadingZeros`** — the pattern is 11 bits wide, so bits 31 down to 11 are zero:
  `32 - 11 = 21`.
- **`numberOfTrailingZeros`** — the lowest one is bit 4, so bits 3, 2, 1, 0 are zero: **4**.
  Equivalently, `log2(1200 & -1200) = log2(16) = 4`.
- **`rotateLeft(1200, 4)`** — the pattern moves to bits 14, 11, 9, 8; nothing wrapped off the top
  because bits 28–31 were zero, so it is the same as a shift: `1200 * 16 = 19200`.

Both edge cases are worth carrying: `numberOfLeadingZeros(0)` and `numberOfTrailingZeros(0)` both
return **32** (measured), which is one more than any bit index — the sentinel for "no one-bit exists".

`reverse(1)` returning `Integer.MIN_VALUE` looks like a bug and is not. The input has exactly one
bit set, at index 0. Reversing sends index 0 to index 31. Bit 31 is the sign bit in two's complement,
and a value with only bit 31 set is `-2^31 = -2147483648`. Measured: `Integer.reverse(1)` =
`-2147483648`. A reversal of a nonnegative number can be negative, and there is no overflow check to
catch it.

**Insight:** four of these — `bitCount`, `reverse`, `numberOfLeadingZeros`,
`numberOfTrailingZeros` — carry `@IntrinsicCandidate` in JDK 21 source. The Java body you can read is
a fallback; C2 replaces the call with a single machine instruction (`CNT`/`CLZ`/`RBIT` on aarch64,
`POPCNT`/`LZCNT` on x86-64). So these are not clever tricks to be avoided on readability grounds —
they are cheaper than the loop you would write instead, and the loop is *less* readable. Guide **06
JVM internals** covers how an intrinsic is substituted.

The genuine use in QuizStakes is the restriction bit mask. Ten restriction types, one `int`, bit
index equal to the enum ordinal:

```java
enum RestrictionType {
    DEPOSIT_BLOCKED, STAKE_BLOCKED, WITHDRAWAL_BLOCKED, DEPOSIT_LIMITED, WITHDRAWAL_HELD,
    SOURCE_OF_FUNDS_REQUIRED, ALL_BLOCKED, SELF_EXCLUDED, COOLING_OFF, DORMANT_FROZEN
}

static int maskOf(EnumSet<RestrictionType> types) {
    int mask = 0;
    for (RestrictionType type : types) {
        mask |= 1 << type.ordinal();
    }
    return mask;
}

static int activeCount(int mask) {
    return Integer.bitCount(mask);
}

static RestrictionType lowestOrdinalActive(int mask) {
    if (mask == 0) {
        throw new IllegalStateException("no active restrictions");
    }
    return RestrictionType.values()[Integer.numberOfTrailingZeros(mask)];
}
```

Measured, for `EnumSet.of(WITHDRAWAL_HELD, SELF_EXCLUDED, COOLING_OFF)`:

```
mask                = 400
toBinaryString(400) = 110010000
bitCount(400)       = 3
numberOfTrailingZeros(400) = 4
lowestOrdinalActive = WITHDRAWAL_HELD
```

`400 = 256 + 128 + 16`, which is bits 8, 7 and 4 — `COOLING_OFF`, `SELF_EXCLUDED`, `WITHDRAWAL_HELD`.
`bitCount` counts them without a loop and `numberOfTrailingZeros` finds the lowest ordinal in one
instruction.

You would not actually write this, because the platform already did: `EnumSet` for an enum with 64 or
fewer constants *is* a `long` bit vector, and its `size()` is `Long.bitCount(elements)` — see
[`../enums/03c-internals-enumset-enummap.md`](../enums/03c-internals-enumset-enummap.md). Note too
that restriction identity in QuizStakes is the pair (type, source), not the type alone, so a single
10-bit mask cannot represent the real domain: it collapses `STAKE_BLOCKED` from `SYSTEM_ONBOARDING`
and from `ADMIN` into one bit, and those two lift under completely different rules.

> **Definition.** The wrapper classes carry four independent static families — type limits and
> metadata, parsers, formatters, and bit primitives — related only by the primitive type they
> describe; the formatters split into unsigned radix-specific ones and a signed general one, and the
> bit primitives are JIT intrinsics rather than convenience wrappers.

---

## 2. `Double.parseDouble` accepts more than you think (1.9.16)

`[TRAP]` `parseDouble` is not a parser for the numbers a human types. It is a parser for the **IEEE
754 double value space**, and that space contains three values that are not numbers at all: `NaN`,
`+Infinity` and `-Infinity`. They are legal `double`s, so they are legal input. A string that no user
would ever intend to type parses cleanly, silently, and then behaves like a landmine in arithmetic.

### Why it exists

`Double.toString` must round-trip: `parseDouble(toString(d))` has to recover `d` for every `double`
including the three special ones, and `toString` emits exactly the tokens `NaN`, `Infinity` and
`-Infinity` for them. So `parseDouble` **must** accept those spellings, or the platform's own
serialization of a `double` would not survive being read back. That is a good reason, and it is
exactly why the method is dangerous at an input boundary: it was designed for machine-generated text
and is routinely pointed at human-supplied text.

Reach for `parseDouble` when the string came from `Double.toString`, from a numeric column you
control, or from a protocol whose grammar you have already validated. Do not reach for it at an HTTP
or CSV boundary; validate first, or use `BigDecimal`, whose constructor accepts only a decimal
grammar and rejects all three special tokens outright.

### The mechanism

`Double.parseDouble(String)` in JDK 21 delegates in one line:

```java
public static double parseDouble(String s) throws NumberFormatException {
    return FloatingDecimal.parseDouble(s);
}
```

`FloatingDecimal.readJavaFormatString` recognises the JLS floating-literal grammar plus the three
special tokens, and it calls `String.trim()` on its input first. All of this is observable:

| Input | Measured result |
|---|---|
| `""` | throws `java.lang.NumberFormatException: empty String` |
| `"NaN"` | `NaN` |
| `"Infinity"` | `Infinity` |
| `"-Infinity"` | `-Infinity` |
| `"inf"` | throws `java.lang.NumberFormatException: For input string: "inf"` |
| `" 1.0 "` | `1.0` — surrounding whitespace **is** trimmed |
| `"0x1p-3"` | `0.125` — hex float literals are accepted |
| `"0x1.8p1"` | `3.0` |
| `null` | throws `java.lang.NullPointerException: Cannot invoke "String.trim()" because "in" is null` |

Three details in that table are the whole concept.

First, the exception message for the empty string is **`empty String`**, with that exact odd
capitalisation, not the `For input string: ""` shape every other bad input produces. It is a
distinctive string worth recognising in a log.

Second, the accepted spellings are **exact and case-sensitive**. `"inf"` throws; so would `"NAN"` or
`"infinity"`. That is what defeats the naive fix — a blocklist checking for the substring `inf`
case-insensitively rejects strings the parser would have rejected anyway and still lets through
whatever spelling you did not think of. The set of accepted non-finite tokens is small and fixed;
testing the *result* is reliable, testing the *input* is not.

Third, `parseDouble` **trims** and `Integer.parseInt` **does not**. Measured:
`Double.parseDouble(" 1.0 ")` = `1.0`, while `Integer.parseInt(" 12")` throws
`NumberFormatException: For input string: " 12"` — two parsers in the same package with opposite
whitespace policies. The NPE message above is direct evidence: the stack frame names `String.trim()`,
because trimming is literally the first thing the double parser does. The rationale for the
inconsistency is not stated in the javadoc or the JLS; treat it as a fact, not a rule with a reason.

### Diagram

No diagram for this concept: the evidence is a nine-row table of measured inputs and exception
strings, and the table is the clearer rendering.

### A concrete example

The money boundary. A deposit amount arrives as text, is parsed to `double`, and is validated by
range. Here is what actually happens, measured:

```java
static double naiveDepositAmount(String raw) {
    double amount = Double.parseDouble(raw);
    if (amount <= 0 || amount > 250_000) {
        throw new IllegalArgumentException("deposit out of range: " + amount);
    }
    return amount;
}

static double naiveBonusGrant(double deposit) {
    return Math.min(deposit * 0.10, 100);       // 10% of the deposit, capped at 100
}
```

```
naiveDepositAmount("Infinity")  -> IllegalArgumentException: deposit out of range: Infinity
naiveDepositAmount("NaN")       -> returns NaN
  naiveBonusGrant(NaN)          =  NaN
```

Read that carefully, because it inverts the obvious guess. `Infinity` **is** caught, because
`Infinity > 250_000` is `true`. `NaN` is **not**, because every comparison involving `NaN` is `false`
by IEEE 754: measured, `NaN <= 0` is `false`, `NaN > 250_000` is `false`, and even `NaN == NaN` is
`false`. A range check written as "reject if out of bounds" therefore accepts `NaN` unconditionally.
The `NaN` then contaminates everything downstream: `Math.min(NaN * 0.10, 100)` is `NaN` (measured),
so the bonus grant is `NaN`; converting to minor units, `(long) NaN` is **`0`** and
`(long) Infinity` is **`9223372036854775807`** (both measured), so a `NaN` amount posts a silent
zero-value `LedgerEntry` and an `Infinity` amount posts `Long.MAX_VALUE` minor units against
`CLIENT_CASH_AVAILABLE`. Neither raises `LedgerImbalanceException`, because both sides of the
double-entry are equally wrong.

The guard that works, and the thing you should have written instead:

```java
// Correct, if you are stuck with double: reject at the parse, on finiteness, not on range.
static double checkedDepositAmount(String raw) {
    double amount = Double.parseDouble(raw);
    if (!Double.isFinite(amount)) {
        throw new IllegalArgumentException("deposit is not a finite amount: " + raw);
    }
    if (amount <= 0 || amount > 250_000) {
        throw new IllegalArgumentException("deposit out of range: " + amount);
    }
    return amount;
}

// Better: money is never a double.
static BigDecimal depositAmount(String raw) {
    BigDecimal amount = new BigDecimal(raw.strip());
    if (amount.signum() <= 0 || amount.compareTo(new BigDecimal("250000")) > 0) {
        throw new IllegalArgumentException("deposit out of range: " + amount);
    }
    return amount.setScale(2, RoundingMode.UNNECESSARY);
}

static BigDecimal bonusGrant(BigDecimal deposit) {
    return deposit.multiply(new BigDecimal("0.10"))
                  .setScale(2, RoundingMode.DOWN)
                  .min(new BigDecimal("100.00"));
}
```

Measured behaviour of those three:

```
checkedDepositAmount("Infinity") -> IllegalArgumentException: deposit is not a finite amount: Infinity
depositAmount("Infinity")        -> NumberFormatException: Character I is neither a decimal digit
                                    number, decimal point, nor "e" notation exponential mark.
depositAmount("420.00")  -> 420.00 ; bonusGrant -> 42.00
depositAmount("3000.00") -> 3000.00; bonusGrant -> 100.00     (the cap)
```

`Double.isFinite` is the single check that covers all three bad values at once — measured,
`isFinite(NaN)` and `isFinite(Infinity)` are both `false`. And `new BigDecimal("Infinity")` throws
without any guard from you, which is the strongest argument for the second version: the correct
type makes the invalid input unrepresentable. `RoundingMode.DOWN` on the bonus is the domain's
rounding rule — the bonus portion rounds down to the minor unit and cash covers the remainder, which
is why a stake of **3.33** splits as **0.33 bonus + 3.00 cash**.

### The gotcha

The `isNaN`/`isInfinite` check placed *after* the arithmetic. By the time a `NaN` shows up in a
total, you have lost the information you needed: `NaN` is absorbing, so
`cashAvailable + bonusAvailable` is `NaN` if either operand is, and `Infinity - Infinity` is `NaN`
(measured) — a legitimate-looking subtraction manufactures a `NaN` from two non-`NaN` operands.
Once one position in the wallet is `NaN`, every derived total is `NaN` and you cannot tell which
input caused it. Validate at the parse. IEEE 754's absorbing and unordered semantics are derived in
[`../primitives-and-conversions/01c-floating-point.md`](../primitives-and-conversions/01c-floating-point.md).

**Interview:** "What does `Double.parseDouble("Infinity")` do?" — returns
`Double.POSITIVE_INFINITY`, no exception; `"NaN"` and `"-Infinity"` likewise; only `""` and
misspellings such as `"inf"` throw `NumberFormatException`. The follow-up is always "so how do you
validate a parsed amount" and the answer is `Double.isFinite` at the parse, or `BigDecimal` so the
tokens never parse at all.

> **Definition.** `Double.parseDouble` accepts the exact, case-sensitive tokens `NaN`, `Infinity`
> and `-Infinity` along with hex float literals, trims surrounding whitespace, and throws
> `NumberFormatException: empty String` on `""` — so a parsed `double` must be checked with
> `Double.isFinite`, since a range comparison silently admits `NaN`.

---

## 3. `Boolean.parseBoolean` never throws, and that is the trap (1.9.17)

`[TRAP]` It is not a parser. It is a predicate. The entire method body in JDK 21 is one line:

```java
public static boolean parseBoolean(String s) {
    return "true".equalsIgnoreCase(s);
}
```

There is no validation because there is no failure mode. Every string in the universe maps to a
`boolean`: the word "true" in any casing maps to `true`, and **everything else** — including `null`,
including `"false"`, including `"ture"`, including `"1"` — maps to `false`. There is no input for
which this method can tell you that you got it wrong.

### Why it exists

Same round-trip argument as `parseDouble`, and it is even tighter here. `Boolean.toString` emits
exactly two strings, `"true"` and `"false"`. If your input provably came from `Boolean.toString`, a
total function is strictly more convenient than a throwing one: no `try`/`catch`, no `Optional`, no
branch. The method is correct for its designed input.

It bites wherever the input is not machine-generated: application configuration, query parameters,
environment variables, feature-flag services, CSV imports, operator-entered admin forms. In every one
of those, a human can type something, and `parseBoolean` will not tell you they did.

`Boolean.valueOf(String)` gives you no more signal — its body is
`return parseBoolean(s) ? TRUE : FALSE;`, so it is the same predicate with a box on top. Measured:
`Boolean.valueOf((String) null)` returns `false`, not `null`, and does not throw.

### The mechanism

Measured on JDK 21.0.7:

| Input | Result | What the author probably intended |
|---|---|---|
| `"true"` | `true` | `true` |
| `"TRUE"` | `true` | `true` — case-insensitivity is real and deliberate |
| `"tRuE"` | `true` | `true` |
| `"false"` | `false` | `false` |
| `"ture"` | `false` | `true` — **a typo flips the value** |
| `"yes"` | `false` | `true` |
| `"1"` | `false` | `true` |
| `"true "` | `false` | `true` — no trimming, unlike `parseDouble` |
| `null` | `false` | an error |

That eighth row is quietly nasty: `Boolean.parseBoolean("true ")` is `false` (measured), because
`equalsIgnoreCase` compares the whole string and there is no `trim()` anywhere in the body. A
trailing space in a properties file silently disables a flag.

Set that against the other two parsers in this file, because the three-way contrast is the thing to
carry into an interview:

| Method | Bad input | Policy |
|---|---|---|
| `Integer.parseInt("abc")` | throws `NumberFormatException: For input string: "abc"` | reject loudly |
| `Integer.parseInt(null)` | throws `NumberFormatException: Cannot parse null string` | reject loudly |
| `Double.parseDouble("")` | throws `NumberFormatException: empty String` | reject loudly |
| `Double.parseDouble("Infinity")` | returns `Infinity` | **accept a value you did not want** |
| `Boolean.parseBoolean("ture")` | returns `false` | **accept silently, with a default** |
| `Boolean.parseBoolean(null)` | returns `false` | **accept silently, with a default** |

Three methods, one package, three different failure policies. `NumberFormatException` is a subclass
of `IllegalArgumentException` and therefore unchecked, so even the loud ones are loud only at
runtime; the parser landscape in this package is walked in detail in
[`01e2-parseint-versus-valueof-string.md`](01e2-parseint-versus-valueof-string.md).

### Diagram

No diagram for this concept: the mechanism is a one-line method body plus a nine-row input table,
both already on the page.

### A concrete example

A compliance gate read from configuration. `SELF_EXCLUDED` carries `reversibleByOperator = false` in
QuizStakes, and the enforcement switch for it is the last thing you want to fail open.

```java
sealed interface FlagValue {
    record Set(boolean value) implements FlagValue {}
    record Absent() implements FlagValue {}
}

static FlagValue strictFlag(Map<String, String> config, String key) {
    String raw = config.get(key);
    if (raw == null) {
        return new FlagValue.Absent();
    }
    return switch (raw.strip()) {
        case "true"  -> new FlagValue.Set(true);
        case "false" -> new FlagValue.Set(false);
        default -> throw new IllegalArgumentException(
                "compliance flag " + key + " must be exactly \"true\" or \"false\", got: \"" + raw + "\"");
    };
}

static boolean gateClosed(Map<String, String> config, String key) {
    return switch (strictFlag(config, key)) {
        case FlagValue.Set(boolean value) -> value;
        case FlagValue.Absent()           -> true;     // absent means closed, deliberately
    };
}
```

Measured:

```
Boolean.parseBoolean("ture")                        = false
strictFlag(config, "restriction.SELF_EXCLUDED.enforced") with value "ture"
  -> IllegalArgumentException: compliance flag restriction.SELF_EXCLUDED.enforced
     must be exactly "true" or "false", got: "ture"
gateClosed(Map.of(), "restriction.SELF_EXCLUDED.enforced")                        = true
gateClosed(Map.of(key, "false"), "restriction.SELF_EXCLUDED.enforced")            = false
```

Three properties make this a real fix rather than a longer spelling of the same bug. A malformed
value **throws**, and the message names both the key and the offending text, so the deployment fails
at startup instead of at the first withdrawal. A **missing** value is distinguished from a malformed
one by the tri-state, so "not configured yet" and "configured wrongly" get different handling. And
the safe default lives in exactly one place — the `Absent` arm — rather than being an emergent
property of `parseBoolean` returning `false`.

**Insight:** with `parseBoolean`, the default is not something you chose; it is whatever `false`
happens to mean in the surrounding `if`. If the safe state is "restriction enforced" and the code
reads `if (Boolean.parseBoolean(raw)) { enforce(); }`, then every typo, every trailing space and
every missing key **disables the gate**. The failure mode is not "wrong value", it is "wrong default,
selected by accident".

### The gotcha

Writing your own `parseBoolean` that accepts `"yes"`, `"1"`, `"on"`, `"y"` — and still returns
`false` for everything else. You have widened the accepting set, which feels like progress, and left
the actual defect untouched: `"ture"` still silently means `false`. The defect was never the size of
the accepted vocabulary; it was the absence of a rejection path. A lenient parser is fine, provided
it throws on what it does not recognise.

**Interview:** "How does `Boolean.parseBoolean` report a malformed input?" — it does not. Its body
is `"true".equalsIgnoreCase(s)`, so it is total: no exception, `null` included, and every
unrecognised string returns `false`. Follow up unprompted with the consequence — a typo in a config
flag silently selects the `false` branch — and with the fix, an explicit strict parser.

> **Definition.** `Boolean.parseBoolean(s)` is exactly `"true".equalsIgnoreCase(s)` — case-insensitive,
> total, never throwing, `null`-tolerant — so it cannot distinguish a legitimate `"false"` from a
> typo or a missing value, and any code relying on a safe default of `true` is relying on something
> the method does not provide.

---

## Pitfalls

### Validating a parsed `double` amount by range instead of by finiteness

**Wrong**

```java
double amount = Double.parseDouble(request.amount());
if (amount <= 0 || amount > 250_000) {
    throw new IllegalArgumentException("deposit out of range: " + amount);
}
ledger.post(CLIENT_CASH_AVAILABLE, (long) (amount * 100));
```

```
request.amount() = "NaN"
  NaN <= 0        -> false
  NaN > 250000    -> false
  check PASSES; (long) (NaN * 100) = 0
  a zero-value LedgerEntry is posted and no exception is raised
request.amount() = "Infinity"
  (long) (Infinity * 100) = 9223372036854775807   if the bound check is ever removed or reordered
```

**Right**

```java
double amount = Double.parseDouble(request.amount());
if (!Double.isFinite(amount)) {                       // covers NaN, +Infinity, -Infinity
    throw new IllegalArgumentException("deposit is not a finite amount: " + request.amount());
}
if (amount <= 0 || amount > 250_000) {
    throw new IllegalArgumentException("deposit out of range: " + amount);
}
```

Better still, never parse money into a `double`: `new BigDecimal("Infinity")` throws
`NumberFormatException` with no guard from you, which makes the bad input unrepresentable rather
than merely detected.

**Why people believe it:** a range check *looks* total — every number is either inside the bounds or
outside them. That reasoning assumes a total order, and IEEE 754 `NaN` is **unordered**: measured,
`NaN <= 0`, `NaN > 250_000` and `NaN == NaN` are all `false`, so `NaN` is neither inside nor outside
and falls through a check phrased as "reject if outside".

### Reading a compliance flag with `Boolean.parseBoolean` and relying on a safe default of `true`

**Wrong**

```java
// application.properties:  restriction.SELF_EXCLUDED.enforced=ture
boolean enforced = Boolean.parseBoolean(config.get("restriction.SELF_EXCLUDED.enforced"));
if (enforced) {
    restrictions.apply(new RestrictionKey(SELF_EXCLUDED, SYSTEM_COMPLIANCE));
}
```

```
Boolean.parseBoolean("ture")   = false      (measured)
Boolean.parseBoolean("true ")  = false      (measured -- trailing space, no trimming)
Boolean.parseBoolean(null)     = false      (measured -- key absent from the file)
-> the restriction is never applied; no log line, no exception, no failed startup
```

**Right**

```java
String raw = config.get("restriction.SELF_EXCLUDED.enforced");
boolean enforced = switch (raw == null ? "true" : raw.strip()) {   // absent means enforced
    case "true"  -> true;
    case "false" -> false;
    default -> throw new IllegalArgumentException(
            "restriction.SELF_EXCLUDED.enforced must be exactly \"true\" or \"false\", got: \"" + raw + "\"");
};
```

The malformed value now fails the deployment, and the message names the key and the text.

**Why people believe it:** every other parser in `java.lang` throws on garbage —
`Integer.parseInt("abc")` and `Double.parseDouble("")` both raise `NumberFormatException` — so
`parseBoolean` is assumed to follow the family policy. It does not; its body is
`"true".equalsIgnoreCase(s)` and has no throw statement at all.

### Reading `toBinaryString` or `toHexString` output as a signed number

**Wrong**

```java
int mask = -56;                                    // a corrupted restriction mask
log.info("restriction mask = {}", Integer.toBinaryString(mask));
log.info("restriction mask = {}", Integer.toString(mask, 2));   // elsewhere in the codebase
```

```
Integer.toBinaryString(-56) = 11111111111111111111111111001000     (measured, unsigned, 32 bits)
Integer.toString(-56, 2)    = -111000                              (measured, signed)
-> two log lines for the same int; a string comparison between them never matches,
   and reading the first as a magnitude gives 4294967240 instead of -56
```

**Right**

```java
// Pick one representation and state its width. The unsigned 32-bit form is the useful one
// for a bit mask, zero-padded so masks line up in a log:
String rendered = String.format("%32s", Integer.toBinaryString(mask)).replace(' ', '0');
// and for the numeric value, print the int itself, not a radix conversion of it.
```

**Why people believe it:** `Integer.toString(i)` and `Integer.toString(i, 10)` agree on negatives,
so the radix parameter looks like a pure formatting choice. It is not: `toBinaryString`,
`toOctalString` and `toHexString` are documented as unsigned and emit all 32 bits with no sign,
while `toString(int, radix)` is signed and emits a minus sign. The unsigned story is developed in
[`../primitives-and-conversions/01b-shifts-and-unsigned.md`](../primitives-and-conversions/01b-shifts-and-unsigned.md).

### Using `a - b` as a comparator, or asserting `Integer.compare` returns exactly `-1`

**Wrong**

```java
Comparator<LedgerEntry> byId = (left, right) -> (int) (left.id() - right.id());   // overflows
assertEquals(-1, Integer.compare(left.sequence(), right.sequence()));            // over-specified
```

```
left.id() = 2147483647, right.id() = -2 (as ints)
  2147483647 - (-2) = -2147483647   -> negative, so "left < right", which is backwards
```

**Right**

```java
Comparator<LedgerEntry> byId = Comparator.comparingLong(LedgerEntry::id);   // uses Long.compare
assertTrue(Integer.compare(left.sequence(), right.sequence()) < 0);         // assert the sign only
```

**Why people believe it:** `a - b` is the textbook C idiom and it works for small values, so it
survives every test written with small values. And `Integer.compare`'s JDK 21 body really does
return `(x < y) ? -1 : ((x == y) ? 0 : 1)`, so `-1` is what you observe — but the javadoc promises
only "a value less than `0`", and pinning the magnitude in a test pins an implementation detail.

---

## Cheat sheet

| Thing | Fact (Java 21 LTS) |
|---|---|
| `Integer.SIZE` / `BYTES` | `32` / `4`; `BYTES` is declared `SIZE / Byte.SIZE` |
| `Long.SIZE` / `BYTES` | `64` / `8` |
| `Integer.MIN_VALUE` / `MAX_VALUE` | `-2147483648` / `2147483647`, declared as `0x80000000` / `0x7fffffff` |
| `Character.MIN_VALUE` | code unit `0` — the only wrapper whose `MIN_VALUE` is not negative |
| `(int) Character.MAX_VALUE` | `65535` |
| `Integer.TYPE` | the `Class` for the primitive; `Integer.TYPE == int.class` is `true` |
| `toBinaryString` / `toOctalString` / `toHexString` | **unsigned**, all 32 bits, no minus sign |
| `toString(int, radix)` | **signed**; emits a minus sign |
| `toBinaryString(-56)` | `11111111111111111111111111001000` |
| `toHexString(-56)` | `ffffffc8` |
| `toString(-56, 2)` | `-111000` |
| `toString(255, 16)` | `ff` |
| `toString(255, 1)` / `toString(255, 99)` | both `255` — out-of-range radix silently becomes 10 |
| `parseInt("12", 1)` | **throws** `radix 1 less than Character.MIN_RADIX` — opposite of `toString` |
| `Character.MIN_RADIX` / `MAX_RADIX` | `2` / `36` |
| `Integer.compare(1, 2)` | `-1`; contract guarantees the **sign** only |
| `Integer.sum/min/max` | `a + b`, `Math.min`, `Math.max`; `@since 1.8`, exist as `BinaryOperator` targets; **no** overflow check |
| `Integer.signum(-1200)` / `signum(0)` | `-1` / `0` |
| `Integer.toBinaryString(1200)` | `10010110000` = `1024 + 128 + 32 + 16` |
| `bitCount(1200)` | `4` |
| `highestOneBit(1200)` | `1024` — the **value**, not the index |
| `highestOneBit(0)` / `highestOneBit(-56)` | `0` / `-2147483648` |
| `numberOfLeadingZeros(1200)` | `21` = `32 - 11` |
| `numberOfTrailingZeros(1200)` | `4` |
| `numberOfLeadingZeros(0)` / `numberOfTrailingZeros(0)` | both `32` |
| `reverse(1)` | `-2147483648` — bit 0 becomes the sign bit |
| `rotateLeft(1, 1)` / `rotateLeft(1200, 4)` | `2` / `19200` |
| Intrinsics | `bitCount`, `reverse`, `numberOfLeadingZeros`, `numberOfTrailingZeros` are `@IntrinsicCandidate` |
| `Double.parseDouble("")` | throws `NumberFormatException: empty String` (note the capitalisation) |
| `Double.parseDouble("NaN")` / `"Infinity"` / `"-Infinity"` | succeed, returning those values |
| `Double.parseDouble("inf")` | throws — accepted spellings are exact and case-sensitive |
| `Double.parseDouble(" 1.0 ")` | `1.0` — **trims**; `Integer.parseInt(" 12")` **throws** |
| `Double.parseDouble("0x1p-3")` | `0.125` — hex float literals accepted |
| `Double.parseDouble(null)` | `NullPointerException` naming `String.trim()` |
| `Double.isFinite` | the one check covering `NaN` and both infinities |
| `NaN` and range checks | `NaN <= 0`, `NaN > n` and `NaN == NaN` are all `false` — `NaN` defeats both bounds |
| `(long) NaN` / `(long) Infinity` | `0` / `9223372036854775807` |
| `Boolean.parseBoolean(s)` | literally `"true".equalsIgnoreCase(s)` |
| `parseBoolean("TRUE")` / `"tRuE"` | both `true` — case-insensitive |
| `parseBoolean("yes")` / `"1"` / `"ture"` / `"true "` / `null` | all `false`; never throws |
| `Boolean.valueOf((String) null)` | `false`, not `null` |
| `new BigDecimal("Infinity")` | throws `NumberFormatException` — rejects what `parseDouble` accepts |
| Failure policies | `parseInt` throws, `parseDouble` throws-or-accepts-non-finite, `parseBoolean` never throws |

---

## Self-test

**Q1.** What does `Double.parseDouble("Infinity")` return, and what does `Double.parseDouble("inf")` do?

<details><summary>Answer</summary>

`parseDouble("Infinity")` returns `Double.POSITIVE_INFINITY` with no exception. `"NaN"` returns
`NaN` and `"-Infinity"` returns negative infinity. `"inf"` throws
`java.lang.NumberFormatException: For input string: "inf"` — the accepted tokens are exact and
case-sensitive. The reason the three special tokens are accepted at all is round-tripping:
`Double.toString` emits exactly `NaN`, `Infinity` and `-Infinity` for those values, so `parseDouble`
has to read them back or the platform's own serialization would not survive. `parseDouble("")` is
the odd one out — it throws `NumberFormatException: empty String`, not the usual
`For input string:` shape.

</details>

**Q2.** A deposit endpoint parses the amount with `Double.parseDouble` and then checks
`if (amount <= 0 || amount > 250_000) throw`. Which inputs get through that it should not?

<details><summary>Answer</summary>

`"NaN"` gets through. Every comparison involving `NaN` is `false` under IEEE 754, so `NaN <= 0` is
`false` and `NaN > 250_000` is `false` — measured — and the check phrased as "reject if outside the
bounds" therefore rejects nothing. `"Infinity"` is actually caught, because `Infinity > 250_000` is
`true`, which is the counter-intuitive half. The `NaN` then contaminates the rest: `Math.min(NaN *
0.10, 100)` is `NaN`, so the bonus grant is `NaN`, and `(long) NaN` is `0`, so a zero-value
`LedgerEntry` is posted with no exception. The fix is `Double.isFinite(amount)` at the parse, which
covers `NaN` and both infinities in one check, or better, parse to `BigDecimal` — `new
BigDecimal("Infinity")` throws `NumberFormatException` with no guard from you.

</details>

**Q3.** How does `Boolean.parseBoolean` report a malformed input?

<details><summary>Answer</summary>

It does not. The entire JDK 21 body is `return "true".equalsIgnoreCase(s);`. It is total: there is no
throw statement, `null` is accepted and returns `false`, and every string other than "true" in some
casing returns `false`. So `"TRUE"` and `"tRuE"` are `true`, while `"yes"`, `"1"`, `"ture"`,
`"true "` — note the trailing space, since there is no trimming — and `null` are all `false`. That
makes it unusable at a boundary where a human supplies the text, because a typo does not fail, it
silently selects the `false` branch. If the safe state was "restriction enforced", the typo disabled
the gate. `Boolean.valueOf(String)` is no better: its body is `parseBoolean(s) ? TRUE : FALSE`.

</details>

**Q4.** `Integer.toHexString(-56)` is `ffffffc8` but `Integer.toString(-56, 2)` is `-111000`. Why the
difference?

<details><summary>Answer</summary>

`toBinaryString`, `toOctalString` and `toHexString` treat the argument as **unsigned** — they print
all 32 bits of the two's-complement pattern with no sign character, which is why `-56` comes out as
`ffffffc8`, the same bits you would see in a register. `toString(int, radix)` is **signed**: it
formats the magnitude and prepends a minus sign, so `-56` in radix 2 is `-111000`. The practical
consequence is that two log statements about the same `int` can produce strings that share no
characters, and reading the unsigned form as a magnitude gives `4294967240` instead of `-56`. A
related trap in the same method: an out-of-range radix in `toString(int, radix)` is silently replaced
by 10 — measured, `toString(255, 1)` and `toString(255, 99)` both return `255` — while
`parseInt("12", 1)` throws.

</details>

**Q5.** Derive `bitCount`, `highestOneBit`, `numberOfLeadingZeros` and `numberOfTrailingZeros` for
`1200` from its bit pattern.

<details><summary>Answer</summary>

`Integer.toBinaryString(1200)` is `10010110000`, and the arithmetic confirms it:
`1024 + 128 + 32 + 16 = 1200`, so bits 10, 7, 5 and 4 are set. Four bits set, so `bitCount` is `4`.
The highest set bit is index 10 and `highestOneBit` returns its **value**, `2^10 = 1024`, not the
index. The pattern occupies 11 bits, so bits 31 down to 11 are zero and `numberOfLeadingZeros` is
`32 - 11 = 21`. The lowest set bit is index 4, so four zeros sit below it and
`numberOfTrailingZeros` is `4`. Two edge cases: for input `0`, both zero-counting methods return
`32`, and `highestOneBit(0)` returns `0`. Four of these methods carry `@IntrinsicCandidate` in JDK 21
source, so C2 emits a single machine instruction rather than running the Java body.

</details>

**Q6.** Why does `Integer.reverse(1)` return `Integer.MIN_VALUE`?

<details><summary>Answer</summary>

`1` has exactly one bit set, at index 0. Reversing the 32-bit pattern end-to-end sends index 0 to
index 31. In two's complement, bit 31 is the sign bit, and an `int` with only bit 31 set is
`-2^31 = -2147483648`, which is `Integer.MIN_VALUE`. Measured on JDK 21.0.7. The general lesson is
that these bit methods operate on the pattern and make no promises about sign: a reversal of a small
positive number is usually negative, and there is no overflow or sign check to warn you.
`highestOneBit(-56)` shows the same thing from the other direction — it returns `-2147483648`,
because bit 31 is set in every negative `int`.

</details>

**Q7.** Why do `Integer.sum`, `Integer.min` and `Integer.max` exist, given that `+`, `Math.min` and
`Math.max` already do the job?

<details><summary>Answer</summary>

They exist to be **method references**. `a + b` is an expression, not a value, so it cannot be passed
to `Stream.reduce` or stored in a `BinaryOperator`; `Integer::sum` can. All three are `@since 1.8`
and each carries `@see java.util.function.BinaryOperator` in its javadoc, which is the JDK saying so
explicitly. Their bodies are exactly `a + b`, `Math.min(a, b)` and `Math.max(a, b)`. The important
caveat is that `Integer.sum` does **no** overflow checking — it wraps in two's complement exactly
like the operator — so a reduction over 2.8M stake reservations can silently wrap past
`Integer.MAX_VALUE`. Use `Math::addExact`, which throws `ArithmeticException`, or reduce into a
`long`.

</details>

**Q8.** What does `Integer.compare` guarantee, and why is `a - b` not a substitute?

<details><summary>Answer</summary>

`Integer.compare` guarantees the **sign** of the result: negative if `x < y`, zero if equal, positive
if `x > y`. The JDK 21 body is `(x < y) ? -1 : ((x == y) ? 0 : 1)`, so you will observe exactly
`-1`, `0` or `1`, but the javadoc promises only "a value less than `0`" — a test asserting
`assertEquals(-1, Integer.compare(a, b))` pins an implementation detail. `a - b` is not a substitute
because subtraction overflows: for `a = 2147483647` and `b = -2`, `a - b` is `-2147483647`, a
negative number that claims `a < b` when the opposite is true. A `TreeMap` or a sort built on that
comparator silently misorders and can lose entries. `Comparator.comparingInt` and
`Comparator.comparingLong` delegate to `Integer.compare` and `Long.compare` and are the right
default.

</details>

---

## Open questions

- Why `Integer.toString(int, radix)` silently falls back to radix 10 while
  `Integer.parseInt(String, int)` throws `NumberFormatException` on the same out-of-range radix.
  Both behaviours are measured on JDK 21.0.7 and the fallback is visible in the `toString` source
  (`if (radix < Character.MIN_RADIX || radix > Character.MAX_RADIX) radix = 10;`), but no rationale
  appears in the javadoc, the JLS, or the JDK bug database entries located. What would settle it: the
  original JDK 1.0 review discussion or a bug report explaining the asymmetry.
- Why `Double.parseDouble` trims surrounding whitespace and `Integer.parseInt` does not. The
  behaviour is measured (`parseDouble(" 1.0 ")` = `1.0`; `parseInt(" 12")` throws) and the mechanism
  is visible — the NPE from `parseDouble(null)` names `String.trim()`, so trimming is the first step
  of `FloatingDecimal.readJavaFormatString` — but the design reason for the inconsistency is not
  documented in either javadoc. What would settle it: the `FloatingDecimal` change history or a
  javadoc clarification bug.

---

**Leaves covered:** 1.9.14, 1.9.16, 1.9.17 (3 leaves)
**Leaves deferred:** none
**Diagrams included:** none
**Target version:** Java 21 LTS
**Lines:** 899
