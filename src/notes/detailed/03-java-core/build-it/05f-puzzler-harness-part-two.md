# 03 Java Core — Diagnostic harnesses — the puzzler harness, snippets 9 to 15 — BUILD IT (§4.8.1)

**Target version: Java 21 LTS.** | **Part 4 of 5** | [Index](../00-index.md)
Previous: [The puzzler harness, snippets 1–8](05-diagnostic-harnesses.md) · Next: [The constructor-calls-an-overridable-method trap](05a-construction-and-init-harnesses.md)

Seven more expressions, and the shift from arithmetic to representation. Snippets 1 to 8 were about
what the compiler does to your operands; these are about what your *types* already are before the
compiler touches them — a scale hiding inside a `BigDecimal`, a recipe hiding inside a `+`, a shift
distance the JLS silently truncates, two fields where the source shows one. The
[first file](05-diagnostic-harnesses.md) holds snippets 1 to 8 and the fifteen-row map for the whole
leaf; this one closes it with the `Diff vs the real one` table, the measured `-Xlint` finding and the
full-harness `main`. Every output below came from `java PuzzlerHarness` on **Oracle JDK 21.0.7 (build
21.0.7+8-LTS-245), macOS aarch64**.

**Two of the seven here are commonly explained wrongly, including in the brief that commissioned
this file.** `Math.round` is *not* specified as `floor(x + 0.5)` in Java 21, and `+` has not compiled
to a `StringBuilder` chain since Java 8. Both are corrected below against the JDK 21 javadoc and
captured bytecode, not against memory. The third correction — that `-Xlint:all` catches **one** of
the fifteen rather than several — arrives with the lint measurement near the end.

| # | Snippet | Prints | Category |
|---|---|---|---|
| 9 | `new BigDecimal("2.0").equals(new BigDecimal("2.00"))` | `false` | scale equality |
| 10 | `"coupon=" + nullString` | `coupon=null`, length 11 | concatenation |
| 11 | `restrictionMask << 32` on an `int` | unchanged, `11` | shift masking |
| 12 | `byte retryBudget = 10; retryBudget += 300;` | `54` | narrowing |
| 13 | `Math.round(-2.5)` | `-2` | rounding |
| 14 | `static railName()` through a base-typed reference | `bank-withdrawal` | dispatch |
| 15 | one object, two reference types, two `maxStakeMinor` | `100` / `500` | hiding |

---

## 9 — `BigDecimal.equals` compares scale

```java
static void bigDecimalEqualsIsScaleSensitive() {
    BigDecimal grantedBonus = new BigDecimal("2.0");
    BigDecimal reportedBonus = new BigDecimal("2.00");
    System.out.println("09 equals                     : " + grantedBonus.equals(reportedBonus));
    System.out.println("09 compareTo == 0             : " + (grantedBonus.compareTo(reportedBonus) == 0));
    System.out.println("09 hashCode pair              : " + grantedBonus.hashCode() + " / " + reportedBonus.hashCode());
    var hashSet = new java.util.HashSet<BigDecimal>();
    hashSet.add(grantedBonus);
    var treeSet = new java.util.TreeSet<BigDecimal>();
    treeSet.add(grantedBonus);
    System.out.println("09 HashSet.contains(2.00)     : " + hashSet.contains(reportedBonus));
    System.out.println("09 TreeSet.contains(2.00)     : " + treeSet.contains(reportedBonus));
}
```

```text
09 equals                     : false
09 compareTo == 0             : true
09 hashCode pair              : 621 / 6202
09 HashSet.contains(2.00)     : false
09 TreeSet.contains(2.00)     : true
```

**Mechanism.** A `BigDecimal` is the pair (unscaled value, scale) representing
`unscaledValue × 10^-scale`: `"2.0"` is (20, 1) and `"2.00"` is (200, 2). `equals` is true only when
both components match, and `hashCode` is derived from both — which is why 621 and 6202 differ and
why `equals`/`hashCode` stay mutually consistent. `compareTo` compares numeric value and ignores
scale, so it reports 0. `BigDecimal` is therefore a documented, deliberate violation of the
`Comparable` recommendation that `compareTo` agree with `equals`, and collections split along that
line: `HashSet` and `HashMap` use `equals`/`hashCode` and miss the value, `TreeSet` and `TreeMap` use
`compareTo` and find it. The same divergence breaks JUnit's `assertEquals` where
`isEqualByComparingTo` passes, and it is the commonest cause of a green ledger assertion failing
after a `setScale` is introduced upstream.
`../numbers-and-money/02b-equality-scale-and-rounding.md` owns this in full.

---

## 10 — `"" + null` prints four characters and does not throw

```java
static void concatenatingNull() {
    String missingCoupon = null;
    String rendered = "coupon=" + missingCoupon;
    System.out.println("10 \"coupon=\" + null           : " + rendered + " length=" + rendered.length());
    System.out.println("10 String.valueOf(null-ref)   : " + String.valueOf(missingCoupon));
    try {
        System.out.println("10 String.valueOf((Object)nul): " + String.valueOf((Object) null));
    } catch (NullPointerException e) {
        System.out.println("10 String.valueOf((Object)nul): NPE");
    }
    try {
        System.out.println("10 String.valueOf(null)       : " + String.valueOf(null));
    } catch (NullPointerException e) {
        System.out.println("10 String.valueOf(null)       : NullPointerException (bound to char[] overload)");
    }
}
```

```text
10 "coupon=" + null           : coupon=null length=11
10 String.valueOf(null-ref)   : null
10 String.valueOf((Object)nul): null
10 String.valueOf(null)       : NullPointerException (bound to char[] overload)
```

**Mechanism, and the version trap.** JLS 15.18.1 says a `null` reference operand of `+` is converted
to the string `"null"` — four characters, so `"coupon="` at 7 gives length 11. On Java 9 and later
the compiler does not build that with a `StringBuilder` chain; JEP 280 replaced the desugaring with
a single `invokedynamic`:

```text
static java.lang.String concatNull(java.lang.String);
  Code:
     0: aload_0
     1: invokedynamic #7,  0              // InvokeDynamic #0:makeConcatWithConstants:(Ljava/lang/String;)Ljava/lang/String;
     6: areturn
```

`aload_0` pushes the (null) argument. `invokedynamic` names a call site whose bootstrap method is
`StringConcatFactory.makeConcatWithConstants`, and the constant-pool entry carries the *recipe*,
which `javap -v` renders as escape text:

```text
BootstrapMethods:
  0: #41 REF_invokeStatic java/lang/invoke/StringConcatFactory.makeConcatWithConstants
    Method arguments:
      #39 coupon=
```

The literal prefix is baked into the recipe and the escape sequence backslash-u-0-0-0-1 is the
placeholder for argument 0. On first execution the bootstrap links a method-handle chain that calls
`String.valueOf` on the reference argument, and `String.valueOf(Object)` returns the literal `"null"`
for a null input. Nothing in the `+` operator special-cases null at runtime.

**This is a version trap.** Every pre-Java-9 explanation says `+` becomes a `new StringBuilder()`
chain of `append` calls followed by `toString`, and that was true through Java 8. Recompiling the
same method with `javac -XDstringConcat=inline` on 21.0.7 reproduces exactly that legacy shape:
`new StringBuilder`, `dup`, `invokespecial <init>`, `ldc "coupon="`, `invokevirtual append`,
`aload_0`, a second `invokevirtual append`, `invokevirtual toString`, `areturn` — nine instructions
where the indy form has two, with one `StringBuilder` and one `char[]` allocated per call and the
same printed output. `-XDstringConcat` is an internal `javac` option, not a supported flag; it
exists to let you see the old shape, not to ship with.

**The adjacent trap, established by compiling it.** `String.valueOf(null)` with a bare `null`
literal **compiles cleanly** and throws at runtime. Two overloads are applicable,
`valueOf(Object)` and `valueOf(char[])`; `char[]` is a subtype of `Object`, so JLS 15.12.2.5 picks it
as most specific and there is no ambiguity error. Its body is `return new String(data);`, which
dereferences the array:

```text
Exception in thread "main" java.lang.NullPointerException: Cannot read the array length because "value" is null
	at java.base/java.lang.String.<init>(String.java:278)
	at java.base/java.lang.String.valueOf(String.java:4479)
	at ValueOfNull.main(ValueOfNull.java:3)
```

Casting to `(Object)` selects the other overload and prints `null`; a *typed* null in a `String`
variable also binds to `valueOf(Object)`. Only the bare literal reaches `char[]`.
`../primitives-and-conversions/02d-string-concatenation.md` and
`../strings/04b-internals-indified-concat.md` own the indified concat machinery.

---

## 11 — Shift distances are masked

```java
static void shiftDistanceIsMasked() {
    int restrictionMask = 0b1011;               // STAKE_BLOCKED | DEPOSIT_BLOCKED | SELF_EXCLUDED
    System.out.println("11 mask << 32 (int)           : " + (restrictionMask << 32));
    System.out.println("11 32 & 0x1f                  : " + (32 & 0x1f));
    System.out.println("11 mask << 33 (int)           : " + (restrictionMask << 33));
    long wideMask = 0b1011L;
    System.out.println("11 wideMask << 64 (long)      : " + (wideMask << 64));
    System.out.println("11 64 & 0x3f                  : " + (64 & 0x3f));
    System.out.println("11 wideMask << 65 (long)      : " + (wideMask << 65));
}
```

```text
11 mask << 32 (int)           : 11
11 32 & 0x1f                  : 0
11 mask << 33 (int)           : 22
11 wideMask << 64 (long)      : 11
11 64 & 0x3f                  : 0
11 wideMask << 65 (long)      : 22
```

**Mechanism.** JLS 15.19 applies unary numeric promotion to each operand *separately*: if the
promoted left operand is `int`, only the low **five** bits of the distance are used, equivalent to
`distance & 0x1f`; if it is `long`, the low **six** bits, `distance & 0x3f`. So `<< 32` on an `int`
is `<< 0`, an identity returning the mask unchanged as 11, and `<< 33` is `<< 1`, doubling it to 22.
The masking is the JLS's rule, not the CPU's, though it matches the x86 and AArch64 shift semantics
the JIT lowers to. The lethal version is a bitmask built with `1 << bit` where `bit` is a
restriction ordinal: cross 32 restriction types and `1 << 32` silently returns 1, aliasing the new
type onto `DEPOSIT_BLOCKED`. Use `1L << bit` with a `long` mask, or an `EnumSet`, which is exactly a
`long` bitmask with the arithmetic hidden.
`../primitives-and-conversions/01b-shifts-and-unsigned.md` owns shifts and masking.

---

## 12 — Compound assignment carries a hidden narrowing cast

```java
static void compoundAssignmentNarrows() {
    byte retryBudget = 10;
    retryBudget += 300;
    System.out.println("12 byte 10 += 300             : " + retryBudget);
    System.out.println("12 (byte)(10 + 300)           : " + (byte) (10 + 300));
    short referralQueueDepth = 30000;
    referralQueueDepth += 10000;
    System.out.println("12 short 30000 += 10000       : " + referralQueueDepth);
    char phase = 'A';
    phase += 65535;
    System.out.println("12 char 'A' += 65535 as int   : " + (int) phase);
}
```

```text
12 byte 10 += 300             : 54
12 (byte)(10 + 300)           : 54
12 short 30000 += 10000       : -25536
12 char 'A' += 65535 as int   : 64
```

**Mechanism.** JLS 15.26.2 specifies `E1 op= E2` as equivalent to `E1 = (T)((E1) op (E2))` where `T`
is the type of `E1` — **the cast is part of the specification.** The addition happens in `int` and
the result is narrowed back to `byte` by discarding all but the low 8 bits: 310 = 0x136, low byte
0x36 = 54. The plain form has no such cast and is a compile error, which is the whole puzzle:

```text
FailNarrow.java:4: error: incompatible types: possible lossy conversion from int to byte
        retryBudget = retryBudget + 300;
                                  ^
1 error
```

The bytecode shows the inserted cast as one instruction:

```text
static byte narrowing();
  Code:
     0: bipush        10
     2: istore_0
     3: iload_0
     4: sipush        300
     7: iadd
     8: i2b
     9: istore_0
    10: iload_0
    11: ireturn
```

`iload_0` and `sipush 300` push the operands, `iadd` produces 310 as an `int`, and `i2b` is the
narrowing conversion the source never wrote — it truncates to the low byte and sign-extends back for
the slot. Remove `i2b` and you have the illegal form. The `short` line applies the same rule at 16
bits signed (40000 mod 2^16, read as signed, is −25536) and the `char` line at 16 bits unsigned
(65 + 65535 = 65600, mod 2^16 = 64, printed as an `int` so no non-printable character reaches the
terminal). `../primitives-and-conversions/02a-assignment-and-bitwise.md` owns compound assignment.

---

## 13 — `Math.round(-2.5)` is −2

```java
static void roundHalfTowardPositiveInfinity() {
    System.out.println("13 Math.round(-2.5)           : " + Math.round(-2.5));
    System.out.println("13 Math.round(2.5)            : " + Math.round(2.5));
    System.out.println("13 Math.round(-3.5)           : " + Math.round(-3.5));
    System.out.println("13 Math.floor(-2.5 + 0.5)     : " + Math.floor(-2.5 + 0.5));
    System.out.println("13 BigDecimal HALF_UP(-2.5)   : "
            + new BigDecimal("-2.5").setScale(0, java.math.RoundingMode.HALF_UP));
}
```

```text
13 Math.round(-2.5)           : -2
13 Math.round(2.5)            : 3
13 Math.round(-3.5)           : -3
13 Math.floor(-2.5 + 0.5)     : -2.0
13 BigDecimal HALF_UP(-2.5)   : -3
```

**Mechanism, and a second correction.** The JDK 21 javadoc for `Math.round(double)` opens:

> Returns the closest `long` to the argument, with ties rounding to positive infinity.

Ties round **toward positive infinity**, so −2.5 goes up to −2 and +2.5 up to 3 — HALF_UP for
positives and HALF_DOWN for negatives, an asymmetric rule that biases a sum of signed values upward,
which is why it must never round a ledger movement. `RoundingMode.HALF_UP` rounds away from zero and
gives −3 for the same input; the two disagree on every negative tie. People get this wrong in both
directions: they expect −3 by reasoning from "half up" as away-from-zero, or they justify −2 by
quoting `(long)Math.floor(a + 0.5)` — the pre-Java-8 javadoc wording, and **not** the Java 21
specification. One input separates the formula from the method:

```text
Math.round(0.49999999999999994) = 0
(long)Math.floor(x + 0.5)       = 1
```

`0.49999999999999994` is the double just below one half; adding 0.5 rounds up to exactly 1.0 before
`floor` sees it, so the old formula returns 1 for a value unambiguously below the tie. JDK-8010430
changed the implementation in 7u40/8 to compute the result from the bit pattern and reworded the
javadoc to the sentence quoted above. Quote the formula and you will be right about −2.5 and wrong
about this input. `../numbers-and-money/02g-rounding-modes-and-the-api-surface.md` owns
`RoundingMode`.

---

## 14 — Static methods are hidden, not overridden

```java
static class WithdrawalRail {
    static String railName() { return "bank-withdrawal"; }
    String describe() { return "rail=" + railName(); }
}

static class CardWithdrawalRail extends WithdrawalRail {
    static String railName() { return "card-withdrawal"; }
}

static void staticMethodsAreHiddenNotOverridden() {
    WithdrawalRail asBase = new CardWithdrawalRail();
    System.out.println("14 WithdrawalRail.railName()  : " + WithdrawalRail.railName());
    System.out.println("14 CardWithdrawalRail.railName: " + CardWithdrawalRail.railName());
    System.out.println("14 describe() on a card rail  : " + asBase.describe());
}
```

```text
14 WithdrawalRail.railName()  : bank-withdrawal
14 CardWithdrawalRail.railName: card-withdrawal
14 describe() on a card rail  : rail=bank-withdrawal
```

**Mechanism.** JLS 8.4.8.2: a `static` method with the same signature as one in a superclass *hides*
it rather than overriding it. Overriding is a runtime property implemented by `invokevirtual`'s
vtable lookup on the receiver's actual class; a static call compiles to `invokestatic`, which names
a resolved method in the constant pool and has no receiver to dispatch on, so the target is fixed at
compile time from the **static type** of the qualifying expression. `describe()` is declared in
`WithdrawalRail`, so its unqualified `railName()` resolves to `WithdrawalRail.railName` and keeps
returning `bank-withdrawal` for a `CardWithdrawalRail` instance — the object's real class is never
consulted. The same rule makes `asBase.railName()` return `bank-withdrawal`, and that form is the
one thing in this file `javac` warns about; see the `-Xlint` section.
`../inheritance-and-dispatch/01-basics.md` owns hiding versus overriding and
`../inheritance-and-dispatch/03-internals-dispatch.md` the instruction split.

---

## 15 — Field hiding creates two fields

```java
static class Reservation {
    int maxStakeMinor = 500;
    int declaredMax() { return maxStakeMinor; }
}

static class BonusReservation extends Reservation {
    int maxStakeMinor = 100;
    int declaredMaxHere() { return maxStakeMinor; }
}

static void fieldsAreHiddenNotOverridden() {
    BonusReservation reservation = new BonusReservation();
    Reservation asBase = reservation;
    System.out.println("15 via BonusReservation ref   : " + reservation.maxStakeMinor);
    System.out.println("15 via Reservation ref        : " + asBase.maxStakeMinor);
    System.out.println("15 super.maxStakeMinor        : " + ((Reservation) reservation).maxStakeMinor);
    System.out.println("15 declaredMax() (base body)  : " + reservation.declaredMax());
    System.out.println("15 declaredMaxHere() (sub)    : " + reservation.declaredMaxHere());
}
```

```text
15 via BonusReservation ref   : 100
15 via Reservation ref        : 500
15 super.maxStakeMinor        : 500
15 declaredMax() (base body)  : 500
15 declaredMaxHere() (sub)    : 100
```

**Mechanism.** Fields are never polymorphic. JLS 8.3 says a subclass field declaration *hides* any
accessible superclass field of the same name, and the object layout carries **both** — one `int` slot
from `Reservation`, one from `BonusReservation`, four bytes each, both initialized. Access compiles
to `getfield` naming a `Fieldref` that includes the declaring class, chosen at compile time from the
static type of the qualifying expression, so the *same object* reports 100 through a
`BonusReservation` reference and 500 through a `Reservation` reference and a cast changes the answer
without changing the object. `declaredMax()` is declared in `Reservation`, so its body reads
`Reservation.maxStakeMinor` and prints 500 — a virtual call that dispatched into the right class body
still read the wrong field, which is why this bug survives code review.
`../inheritance-and-dispatch/01-basics.md` owns field hiding.

> A diagnostic harness is a program whose output is its argument: it does not describe what the
> language does, it makes the language do it and captures the result.

**Gotcha for the whole file:** all fifteen are *specified*. None is a bug, none is
implementation-defined, none will be fixed. The surprise is a gap between your model and the spec,
and the harness closes it by measurement instead of by memory.

---

## The whole run

The harness's own `main` drives the whole leaf, both files' methods, in order. Snippets 1 to 8 are
defined in [the first file](05-diagnostic-harnesses.md), which also ships a driver for just that
half:

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
    bigDecimalEqualsIsScaleSensitive();
    concatenatingNull();
    shiftDistanceIsMasked();
    compoundAssignmentNarrows();
    roundHalfTowardPositiveInfinity();
    staticMethodsAreHiddenNotOverridden();
    fieldsAreHiddenNotOverridden();
}
```

The class needs only `java.math.BigDecimal` and `java.util.Arrays` imported; the two class pairs for
snippets 14 and 15 are `static` nested classes of `PuzzlerHarness`. Running it produces 57 lines —
the 32 quoted section by section above, preceded by the 25 that
[snippets 1 to 8](05-diagnostic-harnesses.md) produce, in that order. No exception escapes `main` —
the four methods that throw across the two halves catch and report it, so the exit status is zero
and a surprising line is a printed line rather than a stopped run.

---

### What `javac -Xlint:all` actually warns about

Claimed, then checked. `javac -Xlint:all -d lintout PuzzlerHarness.java` on 21.0.7:

```text
PuzzlerHarness.java:149: warning: [lossy-conversions] implicit cast from int to byte in compound assignment is possibly lossy
        retryBudget += 300;
                       ^
1 warning
```

**One warning out of fifteen puzzles**, and only snippet 12's `byte` line. Three findings worth
carrying:

- The `short referralQueueDepth += 10000;` and `char phase += 65535;` lines on the *same* rule draw
  nothing. `lossy-conversions` checks whether the right-hand *operand* is representable in the
  left-hand type, not whether the *result* is: 300 does not fit in a `byte`, but 10000 fits in a
  `short` and 65535 fits in a `char`. The two silent lines overflow just as hard.
- `i = i++`, the cache `==`, `split(".")`, the overflow-before-widening, `Math.abs(MIN_VALUE)` and
  both hiding puzzles draw nothing at all. `javac --help-lint` on 21 lists no reference-comparison,
  no integer-overflow and no shadowed-field key; IDE inspections and Error Prone cover those.
- Compiled separately, `asBase.railName()` — a static call through an instance reference — does warn
  under `-Xlint:static`: "static method should be qualified by type name, WithdrawalRail, instead of
  by an expression". The harness avoids that form, which is why it is absent above.

---

## Diff vs the real one

The "real one" is *Java Puzzlers* plus the JLS the puzzles derive from. A harness's honest axes are
coverage and provenance.

| Axis | This harness | The book and the JLS |
|---|---|---|
| **Scope and edge cases** | 15 snippets, one leaf, one input each plus the boundary (127/128, `<< 32` and `<< 33`, ±2.5, −3.5) | *Java Puzzlers* has 95 and explores families; the `Long.MIN_VALUE` and `float` variants are not exercised here |
| **Compiler vs runtime** | 6 are compiler decisions (1, 2, 3, 10, and the resolution in 12, 14/15); 9 are runtime | the book does not partition them; the JLS chapter tells you — ch. 8 and 15 are compile-time, `java.lang` javadoc is runtime |
| **Specified vs implementation-defined** | all 15 specified; none implementation-defined | JLS 5.1.7 mandates only −128..127, so snippet 4's boundary is a floor, not a ceiling — `-XX:AutoBoxCacheMax` moves yours |
| **Version drift** | 3 of 15 have moved: concat desugaring (Java 9, JEP 280), `Math.round` wording and implementation (JDK-8010430, 7u40/8), `Math.absExact` added (Java 15) | the 2005 book predates all three; its `+` chapter is now wrong on mechanism though right on output |
| **Null policy** | 3 and 10 are the null puzzles; 3 throws on the taken branch only, 10 never throws | JLS 15.18.1 for concat, 5.1.8 for unboxing; `String.valueOf(null)`'s NPE is overload resolution (15.12.2.5), not a null rule |
| **Serialization** | not exercised — no snippet crosses a stream | the field-hiding pair would serialize *both* `maxStakeMinor` slots, one per declaring class |
| **Thread safety** | single-threaded by construction, no shared mutable state | none of the fifteen is concurrency-sensitive; §4.8.9's formatter race is the concurrency harness |
| **Allocation and intrinsics** | one `Integer` per uncached box, one `BigDecimal` per literal, one indified `String` per concat; nothing timed | `Math.round` and `Math.abs` are `@IntrinsicCandidate`, so the JIT replaces them with machine instructions and the puzzle survives anyway; `../cost-model/02-master-cost-table.md` owns cost, and this is not JMH |
| **Tool coverage** | `-Xlint:all` catches 1 of 15, measured above | Error Prone's `ReferenceEquality`, `SelfAssignment` and `BadShiftAmount` cover several more; IntelliJ flags most |
| **Why the JDK bothers** | the JDK ships no puzzler harness | each behaviour bought something: promotion bought one arithmetic model, the cache allocation-free small boxing, masking a single machine instruction, scale-sensitive `equals` exact decimal round-tripping. Every puzzle is a paid-for trade-off, not an accident |

---

## Pitfalls

### Quoting `Math.round` as `floor(x + 0.5)`

**Wrong**

```java
System.out.println(Math.round(0.49999999999999994));                  // predicted 1
System.out.println((long) Math.floor(0.49999999999999994 + 0.5));     // 1
```

Actual first line: `0`. The formula and the method disagree.

**Right**

> Returns the closest `long` to the argument, with ties rounding to positive infinity.

That JDK 21 javadoc sentence is the whole rule: `Math.round(-2.5)` is `-2`, `Math.round(2.5)` is `3`,
and `0.49999999999999994` is not a tie so it rounds to `0`. For money do not use `Math.round` at
all — `new BigDecimal("-2.5").setScale(0, RoundingMode.HALF_UP)` gives `-3` and is symmetric about
zero.

**Why people believe it:** `floor(x + 0.5)` *was* the specified behaviour, quoted verbatim in the
javadoc through Java 6, and it gives the right answer for every input a person tries by hand.
JDK-8010430 changed both wording and implementation; the mnemonic outlived the spec.

### Reading `b += x` as shorthand for `b = b + x`

**Wrong**

```java
byte retryBudget = 10;
retryBudget += 300;                 // "identical to retryBudget = retryBudget + 300"
```

They are not identical, and the proof is that one compiles and the other does not:
`retryBudget = retryBudget + 300;` fails with
`error: incompatible types: possible lossy conversion from int to byte`, while the compound form
compiles and silently produces `54`. Reasoning about `+=` by textual substitution gets you the wrong
answer in both directions — you predict a compile error that does not happen, and you miss the
truncation that does.

**Right**

```java
// JLS 15.26.2: E1 op= E2 means E1 = (T)((E1) op (E2)), T = the type of E1.
// The cast is specified, so write the accumulator at the width the arithmetic needs:
int retryBudget = 10;
retryBudget += 300;                 // 310, no hidden narrowing
```

And do not rely on the compiler to flag it. `-Xlint:all` on 21.0.7 warns for
`byte retryBudget += 300` but is **silent** for `short referralQueueDepth += 10000` and
`char phase += 65535`, because `lossy-conversions` tests whether the right-hand *operand* fits the
left-hand type, not whether the *result* does. The two silent lines overflow just as hard.

**Why people believe it:** the shorthand reading is how `+=` is taught, it is correct for `int` and
`long` and every reference type, and it is correct for `double` too — so it holds everywhere except
the three narrow integral types and `char`, which is exactly where a byte-width field or a `char`
status letter lives. A rule that is right 90% of the time and silent when wrong is worse than one
that is right half the time and loud.

### Explaining `+` as a `StringBuilder` chain

**Wrong**

```java
String rendered = "coupon=" + missingCoupon + " for " + clientId;
// "the compiler rewrites this as a new StringBuilder, four append calls, then toString"
```

The output is right and the mechanism is a version stale by seven releases. On 21.0.7 that whole
expression is two instructions — the argument loads, then one `invokedynamic` against
`StringConcatFactory.makeConcatWithConstants` with the literal text carried in a recipe in the
constant pool. There is no `StringBuilder` in the bytecode at all.

**Right**

```java
// Java 9+: one indy call site, linked once, no StringBuilder in the class file.
String rendered = "coupon=" + missingCoupon + " for " + clientId;

// Still worth a StringBuilder when the concatenation is a loop, because indy
// linkage is per call site, not per iteration:
var summary = new StringBuilder();
for (Movement movement : run.movements()) summary.append(movement.code()).append(';');
```

Verify it yourself rather than trusting either claim: `javap -c -p` shows the indy form, and
`javac -XDstringConcat=inline` reproduces the pre-9 `StringBuilder` shape for comparison.

**Why people believe it:** it was exactly true from Java 5 through Java 8, it is what every
still-indexed blog post and most interview crib sheets say, and the advice that follows from it —
prefer `StringBuilder` inside loops — remains correct on 21 for an unrelated reason. A rule that
still gives the right *action* is very hard to dislodge, which is why interviewers use it to
separate memorised answers from checked ones.

---

## Cheat sheet

| Puzzle | Result | Rule | Fix |
|---|---|---|---|
| `BigDecimal "2.0".equals("2.00")` | `false` | `equals` compares unscaled value **and** scale | `compareTo(x) == 0` |
| `HashSet` vs `TreeSet` membership | `false` / `true` | hash sets use `equals`, sorted sets use `compareTo` | pick the collection for the semantics you want |
| `"coupon=" + null` | `coupon=null` | JLS 15.18.1, then indified `String.valueOf` | `Objects.requireNonNullElse` |
| `+` desugaring on 21 | one `invokedynamic` | JEP 280, `StringConcatFactory`; `StringBuilder` was Java 8 and earlier | `javap -c`, or `-XDstringConcat=inline` to see the old shape |
| `String.valueOf(null)` | NPE | bare literal binds the `char[]` overload (JLS 15.12.2.5) | cast to `(Object)` |
| `mask << 32` on `int` | unchanged | distance masked `& 0x1f` | `1L << bit`, or `EnumSet` |
| `mask << 64` on `long` | unchanged | distance masked `& 0x3f` | check the bit index against the width |
| `byte b = 10; b += 300` | `54` | JLS 15.26.2 inserts `(byte)`; bytecode `i2b` | widen the variable to `int` |
| `b = b + 300` | compile error | plain assignment has no implicit narrowing cast | this is the *correct* behaviour |
| `Math.round(-2.5)` | `-2` | ties round toward **positive infinity**, not away from zero | `setScale(0, HALF_UP)` |
| `Math.round(0.49999999999999994)` | `0` | not `floor(x + 0.5)` since 7u40/8, JDK-8010430 | quote the javadoc, not the formula |
| static hiding | base version | `invokestatic` binds to the static type (JLS 8.4.8.2) | never redeclare a `static` |
| field hiding | two live fields | `getfield` names the declaring class (JLS 8.3) | never reuse a field name |
| `-Xlint:all` coverage | 1 of 15 | `lossy-conversions` only, and only when the *operand* does not fit | Error Prone, IDE inspections |

---

## Self-test

Different snippets from the seven in this file. Predict before unfolding; all outputs below were
captured on 21.0.7.

**Q1.** A stake list holding `[100, 200, 300]` as a `List<Integer>` is pruned with
`stakeIds.remove(2)`. What is left, and what does `remove(Integer.valueOf(200))` leave?

<details><summary>Answer</summary>

`remove(2)` leaves `[100, 200]` and `remove(Integer.valueOf(200))` leaves `[100, 300]`. `List<E>`
declares both `remove(int index)` and `remove(Object o)`; with an `int` argument the first is
applicable without any boxing, and JLS 15.12.2 resolves overloads in a phase that permits neither
boxing nor varargs *before* considering one that does — so `remove(2)` deletes position 2, the
element `300`. This is the one overload trap in the collections API that no cast can hide:
`remove(Integer.valueOf(200))` or `remove((Integer) 200)` is the only way to reach the value form.

</details>

**Q2.** `System.out.println("total=" + Integer.MAX_VALUE + 1);` versus
`System.out.println("total=" + (Integer.MAX_VALUE + 1));`

<details><summary>Answer</summary>

The first prints `total=21474836471` and the second `total=-2147483648`. `+` is left-associative, so
the first concatenates the string with `2147483647` and then concatenates the character `1` onto the
result — 11 digits that are not a number. Parenthesising makes the addition an `int` addition first,
which wraps mod 2^32 to `Integer.MIN_VALUE` per JLS 15.18.2. Both are wrong for a ledger total; the
correct form widens the accumulator to `long` before the arithmetic.

</details>

**Q3.** `System.out.println(new BigDecimal("2.00").stripTrailingZeros());` and
`System.out.println(new BigDecimal("100").stripTrailingZeros());`

<details><summary>Answer</summary>

`2` and `1E+2`. `stripTrailingZeros` removes trailing zeros by *reducing the scale*, and for `"100"`
that means unscaled value 1 with scale −2 — a negative scale, which `toString` renders in scientific
notation. So normalising a ledger amount for comparison can turn `100` into the string `1E+2` on its
way into a report or a database column. `toPlainString()` prints `100` and is what you want for
output; `compareTo` is what you want for comparison, since it ignores scale and makes the whole
normalisation step unnecessary. This is snippet 9's mechanism seen from the other end: the scale is
not presentation, it is part of the value.

</details>

**Q4.** A restriction bit mask holds `-8`. What do `-8 >> 1` and `-8 >>> 1` print?

<details><summary>Answer</summary>

`-4` and `2147483644`. `>>` is the arithmetic right shift: it propagates the sign bit, so it behaves
like division by two rounding toward negative infinity and keeps the value negative. `>>>` is the
logical right shift: it feeds in zeros from the left, so the sign bit becomes an ordinary data bit
and −8's two's-complement pattern `0xFFFFFFF8` becomes `0x7FFFFFFC` = 2,147,483,644. Java has no
`<<<` because a left shift feeds zeros in from the right either way, which is the giveaway that the
two right shifts differ only in what they feed in. Both mask their distance exactly as snippet 11
shows, and `>>>` on a `byte` or `short` promotes to `int` first, which is where most sign-extension
bugs actually come from.

</details>

**Q5.** `WithdrawalRail` declares `private String railName()` and a public `describe()` that calls
it. `CardWithdrawalRail extends WithdrawalRail` declares a non-private `String railName()`. What
does `new CardWithdrawalRail().describe()` print?

<details><summary>Answer</summary>

`rail=bank-withdrawal`, verified by running it. A `private` method is not inherited and cannot be
overridden (JLS 8.4.8), so the subclass declaration is a brand new, unrelated method rather than an
override. Worth checking rather than assuming: `javap -c -p` shows the call inside `describe()`
compiled to `invokevirtual`, not `invokespecial` — but JVMS 5.4.6 method selection returns the
*resolved* method unchanged when it is `private`, so no override lookup happens and the target is
`WithdrawalRail.railName` permanently. Adding `@Override` to the subclass method turns it into
`error: method does not override or implement a method from a supertype`, which is the cheapest way
to find this. It is snippet 14's lesson without `static` in it:
dynamic dispatch is not a property of *calling* a method, it is a property of the specific pair of
declarations, and three modifiers — `private`, `static`, `final` — each opt out of it for a different
reason.

</details>

---

## Open questions

- none

---

**Leaves covered:** 4.8.1 (snippets 9–15; snippets 1–8 are in 05-diagnostic-harnesses.md)
**Leaves deferred:** none
**Diagrams included:** none
**Target version:** Java 21 LTS
**Lines:** 692
