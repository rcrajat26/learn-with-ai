# 03 Java Core — Floating point internals: the binary64 layout — INTERNALS (§3.15, 3.15.1–3.15.5)

**Target version: Java 21 LTS.** | **Part 3 of 5** | [Index](../00-index.md)
Previous: [BigInteger internals and the long cents bound](03b-internals-biginteger-and-long-cents.md) · Next: [Math.ulp, rounding and Double.toString](04a-internals-ulp-rounding-and-tostring.md)

This file owns the bit-level anatomy of a `double`: the 1/11/52 split, the
exact stored value of `0.1`, the difference between `doubleToLongBits` and
`doubleToRawLongBits`, the subnormal range, and the arithmetic rules for
infinities and NaN. `04a` covers ulp spacing, rounding mode and
`Double.toString`; `04b` covers `strictfp`/`StrictMath`/`fma`; `04c` closes
with compensated summation, widening/narrowing, and the money-versus-double
decision. The question this file answers: **what exactly do 64 bits have to
mean for `0.1 + 0.2` to equal `0.30000000000000004`, and what happens at the
edges — zero, infinity, NaN, the smallest representable value?**

Measured on Oracle JDK 21.0.7 (build 21.0.7+8-LTS-245), macOS aarch64 (Apple
Silicon), bit patterns via `Double.doubleToLongBits`/`doubleToRawLongBits`.

---

## 1. The binary64 layout (3.15.1)

A `double` is not a little decimal number wearing a costume — it is 64 bits
partitioned into three fields, and the value they encode is a binary
scientific notation: `(-1)^sign x 1.mantissa x 2^(exponent - 1023)` for a
normal number. Picture a fixed-width record, not a number line.

### Why it exists

Fixed-width binary floating point trades exactness for a *bounded relative
error across an enormous dynamic range* — the same 64 bits represent both
4.9E-324 and 1.7976931348623157E308. A fixed-point representation with that
range would need thousands of bits. IEEE 754 (1985, revised 2008 and 2019)
standardized the trade so every conforming implementation — every JVM, every
C compiler, every hardware FPU — agrees on the encoding and the arithmetic.

### How it works

The 64 bits split 1 (sign) / 11 (exponent) / 52 (mantissa). `[PROVE]` each
number rather than accept it:

**The exponent bias is 1023.** An 11-bit field holds 2^11 = 2048 distinct
codes. Two are reserved (all-zero and all-one, below), leaving 2046 usable
exponent values that must cover a symmetric range of positive and negative
exponents so that a value and its reciprocal are both representable. Splitting
2046 in half gives 1023 on each side of zero: the bias 1023 = 2^10 - 1 is
exactly the midpoint of the 2046 usable codes, so a biased field of 1 encodes
the most negative usable exponent and 2046 encodes the most positive.

**The effective significand is 53 bits, not 52.** Every normal binary number
can be written with its leading significant bit equal to 1 (shift the binary
point until it is), so that leading 1 never has to be stored — it is
*implicit*. The 52 stored mantissa bits plus that implicit bit give 53 bits of
precision. That is where the famous "doubles are exact up to 2^53" limit comes
from: 2^53 = 9007199254740992 is the first integer whose binary representation
needs a 54th significant bit, so it and its neighbours start colliding onto
the same `double`.

**`MAX_VALUE` follows from the same fields.** The largest finite exponent code
is 2046 (2047 is reserved for infinity/NaN), giving unbiased exponent 2046 -
1023 = 1023. The largest significand is all 52 mantissa bits set, i.e.
1.1111...1 in binary = 2 - 2^-52. So `Double.MAX_VALUE` = (2 - 2^-52) x
2^1023 = 1.7976931348623157E308, matching the measured value in §6.3.

The two reserved exponent codes are the hinge for everything else in this
file: all-zero-exponent means zero or a subnormal (concept 4), all-one-exponent
means infinity or NaN (concept 5).

The language-level `float`/`double` semantics and the layout diagram (D-009)
live in [`../primitives-and-conversions/01c-floating-point.md`](../primitives-and-conversions/01c-floating-point.md) —
this file does not repeat or re-embed that diagram.

**Insight:** the bias is not an arbitrary offset chosen for convenience — it
falls straight out of needing a symmetric two-sided exponent range from a
field that can only count upward from zero.

> A `double` is 1 sign bit, an 11-bit biased exponent (bias 1023), and 52
> explicit mantissa bits with one implicit leading 1, together encoding
> `(-1)^sign x 1.mantissa x 2^(exponent - 1023)`.

## 2. The exact bits of 0.1 (3.15.2)

`0.1` looks exact when you type it. It has never once been exact inside a
`double`. The gap between the decimal literal and the stored binary value is
the single fact that explains almost every floating-point surprise in this
row.

### Why it exists

Decimal fractions and binary fractions terminate on different denominators.
A decimal fraction terminates exactly when its denominator's prime factors are
only 2s and 5s (0.1 = 1/10 = 1/(2x5)); a binary fraction terminates only when
the denominator's prime factors are exclusively 2s. 1/10 has a factor of 5, so
it cannot terminate in binary — it must repeat, forever, and 52 mantissa bits
force a cut.

### How it works

`[PROVE]` the binary expansion by the standard doubling algorithm: multiply
the fraction by 2, the integer part is the next bit, keep the fractional part
and repeat.

```
0.1 x 2 = 0.2  -> bit 0
0.2 x 2 = 0.4  -> bit 0
0.4 x 2 = 0.8  -> bit 0
0.8 x 2 = 1.6  -> bit 1   (fractional part 0.6)
0.6 x 2 = 1.2  -> bit 1   (fractional part 0.2 -- the cycle re-enters 0.2)
```

So 0.1 in binary is 0.0001100110011001100 with 1100 recurring. 52 mantissa
bits cannot hold an infinite recurring pattern, so the expansion is truncated
and rounded to the nearest representable value.

The measured bits, `Double.doubleToLongBits(0.1)` = `0x3fb999999999999a`, split:

| Field | Bits | Value |
|---|---|---|
| Sign | `0` | positive |
| Biased exponent | `01111111011` | 1019 -> unbiased 1019 - 1023 = -4 |
| Mantissa | `1001100110011001100110011001100110011001100110011010` | ends `...1010` |

The final nibble is `1010`, not the `1001` the recurring `0110`-pattern would
naively continue with — it was rounded **up** because the first discarded bit
beyond the 52nd was `1` (a tie-breaking-and-above case under
round-to-nearest-even, detailed in `04a`). The compact confirmation:
`Double.toHexString(0.1)` = `0x1.999999999999ap-4` — the trailing `a` is
exactly that rounded-up nibble, and `p-4` is the unbiased exponent -4.

The exact stored value, from §6.1, `new BigDecimal(0.1)` =
`0.1000000000000000055511151231257827021181583404541015625`, scale 55. `[PROVE]`
the 55: the stored value is `1.mantissa x 2^-4`, a dyadic rational with
denominator `2^56` (52 mantissa bits plus the implicit bit, shifted by the -4
exponent, gives `2^(52+4)` = `2^56` in the denominator once put over a common
base). Since `1/2^n = 5^n / 10^n`, any dyadic fraction with denominator `2^56`
terminates in at most 56 decimal digits — matching the measured 55 (the
leading digit accounts for the one power of ten saved by the value being
just under 2^-3). The syllabus leaf's truncated `...1257827` is not the full
value; the measured 55-digit expansion above is.

Application-level treatment of this gap lives in
[`02-numbers-and-money.md`](02-numbers-and-money.md); what `new BigDecimal(0.1)`
actually builds out of these bits is in
[`02a-bigdecimal-structure-and-construction.md`](02a-bigdecimal-structure-and-construction.md).

**Interview:** "why is 0.1 not exact in binary" — the one-line answer is 1/10
has a factor of 5, binary fractions only terminate on powers of 2, so 0.1
recurs and 52 bits truncate it.

> `0.1` as a `double` is not 0.1 — it is the nearest binary64 value,
> `0.1000000000000000055511151231257827021181583404541015625`, produced by
> rounding an infinitely recurring binary fraction to 53 significant bits.

## 3. `doubleToLongBits` versus `doubleToRawLongBits` (3.15.3)

Two methods that look like one does the "safe" thing and one does the
"dangerous" thing. That is not the distinction — both are safe; they answer
different questions.

### Why it exists

A NaN is not one bit pattern. Every code with the reserved all-one exponent
and a nonzero mantissa is a NaN, and the mantissa's remaining bits are free —
that is 2^52 - 1 distinct NaN encodings (the all-zero mantissa with an all-one
exponent is reserved for infinity instead). Distinguishing "canonical NaN, use
this everywhere identity matters" from "the exact bits some computation
produced" needs two different accessors.

### How it works

Per the Javadoc, `doubleToLongBits` collapses **every** NaN encoding to the
single canonical value `0x7ff8000000000000L`; `doubleToRawLongBits` returns
the bits completely unchanged. Measured in §6.2:

```
Double.doubleToRawLongBits(Double.longBitsToDouble(0x7ff8000000000001L)) = 0x7ff8000000000001
Double.doubleToLongBits(   Double.longBitsToDouble(0x7ff8000000000001L)) = 0x7ff8000000000000
```

The mantissa bits below the quiet-NaN indicator bit, plus the sign bit, form a
free "payload" a computation can leave behind — some native math libraries
encode diagnostic information there. `doubleToLongBits` treats all of that as
noise and normalizes it away; `doubleToRawLongBits` preserves it exactly.

`Double.hashCode` and `Double.equals` are built on `doubleToLongBits`
specifically so that every NaN hashes and compares identically to every other
NaN — which is why, measured in §6.2, `Double.valueOf(Double.NaN).equals(Double.valueOf(Double.NaN))`
is `true` while `Double.NaN == Double.NaN` is `false`: `==` is the raw IEEE
comparison (unordered, so NaN compares unequal to everything including
itself), `equals` is bit-canonicalized identity.

```java
record BonusYieldSample(double perStakeReturn) {
    // Using doubleToLongBits (via equals/hashCode) means every NaN sample
    // collapses to one bucket for dedup/statistics purposes.
    boolean sameBits(BonusYieldSample other) {
        return Double.doubleToLongBits(perStakeReturn)
                == Double.doubleToLongBits(other.perStakeReturn);
    }

    // Using doubleToRawLongBits would treat two differently-payloaded NaNs
    // (e.g. one from 0.0/0.0, one propagated from a native library) as
    // distinct -- almost never what a QuizStakes analytics job wants.
    boolean sameRawBits(BonusYieldSample other) {
        return Double.doubleToRawLongBits(perStakeReturn)
                == Double.doubleToRawLongBits(other.perStakeReturn);
    }
}
```

**Pitfall:** the wrong belief is that the two methods are interchangeable and
`doubleToRawLongBits` is merely the faster variant. The symptom is a
bit-comparison-based equality, a hash function, or a "round-trip the bits"
unit test that passes when written with one method and silently fails when
someone "optimizes" it to the other, because two NaN-producing computations
rarely produce bit-identical payloads. The fix: use `doubleToLongBits` (or
`Double.equals`/`hashCode`, which already do) for anything comparing or
hashing values; reach for `doubleToRawLongBits` only when the exact stored
encoding — payload included — is the thing under test.

Cross-reference: [`../objects-equality-and-lifecycle/01b-equals-hashcode-and-object-methods.md`](../objects-equality-and-lifecycle/01b-equals-hashcode-and-object-methods.md).

> `doubleToLongBits` normalizes every NaN to one canonical pattern before
> returning its bits; `doubleToRawLongBits` returns the stored bits, payload
> and all, unchanged.

## 4. Denormals (3.15.4)

Below the smallest normal value, IEEE 754 does not simply give up and jump to
zero — it spends the mantissa bits differently to buy a graceful ramp down.

### Why it exists

Without subnormals, the gap between `0.0` and the smallest normal value would
be a cliff: `a - b == 0.0` could be true for two *distinct* nonzero values
even though `a != b`, because the difference underflows straight past every
representable nonzero value to zero. Subnormals guarantee that if `a != b`
then `a - b != 0.0` for any two representable finite values that are not
themselves the closest possible pair — a property called gradual underflow.

### How it works

When the biased exponent field is all zero, two things change at once: the
implicit leading bit becomes 0 instead of 1, and the exponent is pinned at
the minimum normal exponent rather than continuing to decrease. Every
subnormal mantissa bit spent now buys smaller magnitude instead of more
precision, so precision degrades gracefully as the value shrinks toward zero.

Measured bit patterns, §6.3:

| Value | Bits | Biased exponent | Exponent field |
|---|---|---|---|
| `Double.MIN_NORMAL` | `0x0010000000000000` | 1 | normal (barely) |
| `Double.MIN_NORMAL / 2` | `0x0008000000000000` | 0 | subnormal |
| `Double.MIN_VALUE` | `0x1` | 0 | subnormal, single mantissa bit |

And the values: `Double.MIN_NORMAL` = 2.2250738585072014E-308,
`Double.MIN_VALUE` = 4.9E-324 (the smallest positive **subnormal** — not the
most negative `double`, which is `-Double.MAX_VALUE`), `MIN_NORMAL / 2` =
1.1125369292536007E-308 (a valid subnormal, half of `MIN_NORMAL` exactly), and
`MIN_VALUE / 2` = **0.0** — there is no mantissa bit left to shift into, so it
underflows all the way to zero. `Math.ulp(Double.MIN_NORMAL)` = 4.9E-324, which
*equals* `MIN_VALUE`: in the subnormal range the spacing between consecutive
doubles is constant, unlike the proportional spacing everywhere else
(`04a` covers that contrast in full).

```java
double bonusYieldFloor = Double.MIN_NORMAL / 2;   // 1.1125369292536007E-308, a valid subnormal
double belowRepresentable = Double.MIN_VALUE / 2; // 0.0 -- underflowed, not a bug
```

On the performance cliff, `[RESEARCH]`-honest: subnormal arithmetic is handled
by microcode or a dedicated slow path on some x86 CPU generations, with
reported slowdowns commonly cited at one to two orders of magnitude — this is
a hardware property, not something JEP 306 or the JLS mandates or forbids.
**No measurement of this cliff exists on the brief's build (Apple Silicon
aarch64)**, so no slowdown factor is asserted here; see `## Open questions`.
Unlike C, Java exposes no `-ffast-math` and no flush-to-zero switch — there is
no opt-out. QuizStakes framing: no money value is ever remotely near 1e-308,
so this concerns a statistics or ML feature pipeline, never the ledger.

**Interview:** "what is a subnormal number for" — trading precision for
gradual underflow, so that `a == b` implies `a - b == 0.0` reliably near zero
without a hard cliff to the value zero.

> A subnormal (denormal) `double` has an all-zero exponent field, an implicit
> leading bit of 0 instead of 1, and a fixed minimum exponent — trading
> mantissa precision for a smooth ramp down to zero instead of a hard cliff.

## 5. Infinities and NaN arithmetic (3.15.5)

| Expression | Result | Why |
|---|---|---|
| `1.0 / 0.0` | `Infinity` | nonzero over zero, sign-carrying |
| `-1.0 / 0.0` | `-Infinity` | sign of dividend preserved |
| `0.0 / 0.0` | `NaN` | no defensible answer |
| `Double.POSITIVE_INFINITY - Double.POSITIVE_INFINITY` | `NaN` | no defensible answer |
| `Double.POSITIVE_INFINITY * 0` | `NaN` | no defensible answer |
| `Math.sqrt(-1)` | `NaN` | no real root |

Infinity is produced by overflow (a finite computation whose true result
exceeds `MAX_VALUE`) or by dividing a nonzero value by zero, and it is a
sign-carrying value that keeps arithmetic **total** — every operation
produces some result, never an exception. NaN is produced by an operation
with no defensible real-number answer (0/0, infinity minus infinity, infinity
times zero, the square root of a negative number) and it is **contagious**:
every arithmetic operation with a NaN operand produces NaN, by design, so a
single corrupted value poisons everything downstream of it rather than
vanishing.

Contrast integer division: `1 / 0` throws `ArithmeticException` instead of
producing a sentinel value, because `int`/`long` arithmetic has no
representable "infinity" to fall back on — see
[`../primitives-and-conversions/01a-integral-arithmetic.md`](../primitives-and-conversions/01a-integral-arithmetic.md).

**Insight:** floating point chose totality (always a result) over
loudness (an exception); integer arithmetic chose the opposite. Neither is
strictly safer — each is safer in a different failure mode.

QuizStakes symptom: a `double` throughput metric (settlements per second)
divided by a zero-length observation window silently becomes `Infinity`; once
that feeds into an average with other windows the average becomes `NaN`, and
a dashboard renders a blank tile instead of an error — exactly the failure
mode integer arithmetic would have made loud with an exception at the point
of the bad divide.

No gotcha beyond the contagion rule already stated: there is no case where a
NaN operand yields a non-NaN result.

---

## Pitfalls

### "`doubleToLongBits` and `doubleToRawLongBits` are interchangeable"

**Wrong**

```java
double a = Double.longBitsToDouble(0x7ff8000000000001L);
double b = Double.longBitsToDouble(0x7ff800000000000aL);
boolean same = Double.doubleToRawLongBits(a) == Double.doubleToRawLongBits(b);
```

`same` is `false` — two different NaN payloads, so the raw bits differ even
though both are unmistakably NaN.

**Right**

```java
boolean same = Double.doubleToLongBits(a) == Double.doubleToLongBits(b);
// true -- both canonicalize to 0x7ff8000000000000
```

`doubleToLongBits` normalizes every NaN encoding first, matching what
`Double.equals`/`hashCode` do, so two NaNs of any payload compare equal.

**Why people believe it:** the method names differ only by the word "Raw",
which reads like a performance qualifier ("the fast unchecked version"), not
a semantic one.

### "`Double.MIN_VALUE` is the most negative double"

**Wrong**

```java
double mostNegative = Double.MIN_VALUE;
// caller assumes this is the floor of the double range
```

`Double.MIN_VALUE` is 4.9E-324 — the smallest **positive** representable
value, a subnormal. It is closer to zero than any other positive `double`.

**Right**

```java
double mostNegative = -Double.MAX_VALUE; // -1.7976931348623157E308
```

`MIN_VALUE` names the minimum on the *positive* magnitude scale (smallest
step above zero), not the minimum on the signed number line.

**Why people believe it:** every other `MIN_VALUE` in the primitive wrapper
classes (`Integer.MIN_VALUE`, `Long.MIN_VALUE`) is the most negative
representable value, so the name reads as consistent when it is the opposite
for floating point.

### "NaN behaves like any other sentinel value in comparisons"

**Wrong**

```java
double bonusYield = 0.0 / 0.0;
if (bonusYield == Double.NaN) {   // never true, always false
    flagCorruptSample(bonusYield);
}
```

This never fires — `NaN == NaN` is always `false` by the IEEE 754 unordered
comparison rule, so the corrupt sample is silently missed.

**Right**

```java
if (Double.isNaN(bonusYield)) {
    flagCorruptSample(bonusYield);
}
```

`Double.isNaN` performs the correct check (`bonusYield != bonusYield` is the
classic trick, but `isNaN` is the documented way to spell it).

**Why people believe it:** `==` is the natural first reach for equality in
Java, and for every other `double` value it works exactly as expected.

---

## Cheat sheet

| Thing | Fact (Java 21 LTS) |
|---|---|
| `double` layout | 1 sign + 11 exponent (bias 1023) + 52 mantissa, implicit leading 1 |
| Effective precision | 53 bits (52 stored + 1 implicit) |
| Exact-integer bound | 2^53 = 9007199254740992 |
| `Double.MAX_VALUE` | 1.7976931348623157E308 = (2 - 2^-52) x 2^1023 |
| Most negative `double` | `-Double.MAX_VALUE`, not `MIN_VALUE` |
| `Double.MIN_NORMAL` | 2.2250738585072014E-308 |
| `Double.MIN_VALUE` | 4.9E-324, smallest positive subnormal |
| `MIN_VALUE / 2` | 0.0 (underflow, no bit left) |
| `bits(0.1)` | `0x3fb999999999999a` |
| Exact value of `0.1` (`double`) | 0.1000000000000000055511151231257827021181583404541015625 (scale 55) |
| `Double.toHexString(0.1)` | `0x1.999999999999ap-4` |
| Reserved exponent codes | all-zero -> zero/subnormal; all-one -> infinity/NaN |
| Distinct quiet-NaN encodings | 2^52 - 1 |
| `doubleToLongBits(NaN)` | always `0x7ff8000000000000` (canonicalized) |
| `doubleToRawLongBits(NaN)` | preserves the exact stored payload |
| `Double.NaN == Double.NaN` | `false` |
| `Double.valueOf(NaN).equals(Double.valueOf(NaN))` | `true` |
| `0.0 == -0.0` | `true` |
| `Double.valueOf(0.0).equals(Double.valueOf(-0.0))` | `false` |
| `bits(0.0)` vs `bits(-0.0)` | `0x0` vs `0x8000000000000000` |
| `1.0 / 0.0` | `Infinity` |
| `0.0 / 0.0` | `NaN` |
| `Infinity - Infinity` | `NaN` |
| `Infinity * 0` | `NaN` |
| `Math.sqrt(-1)` | `NaN` |
| Integer `1 / 0` | throws `ArithmeticException` (contrast) |
| Subnormal spacing | constant (`Math.ulp(MIN_NORMAL) == MIN_VALUE`) |
| Normal spacing | proportional to magnitude (see `04a`) |
| Subnormal perf cliff | hardware-dependent, magnitude unmeasured here |
| Java flush-to-zero opt-out | none — no `-ffast-math` equivalent |

---

## Self-test

**Q1.** Why is `0.1` not exactly representable as a `double`, in one sentence?

<details><summary>Answer</summary>

1/10 has a prime factor of 5 in its denominator, and a binary fraction can
only terminate when its denominator's prime factors are exclusively 2, so
0.1 becomes an infinitely recurring binary fraction (`0.0001100110011...`
with `1100` repeating) that 52 mantissa bits must truncate and round.

</details>

**Q2.** What is the difference between `Double.doubleToLongBits` and
`Double.doubleToRawLongBits`, and which one backs `Double.equals`?

<details><summary>Answer</summary>

`doubleToLongBits` first canonicalizes any NaN to the single bit pattern
`0x7ff8000000000000` and then returns the bits; `doubleToRawLongBits` returns
the stored bits completely unchanged, payload and all. `Double.equals` (and
`hashCode`) are built on `doubleToLongBits`, which is exactly why two
different NaN values are `.equals()` to each other even though `==` between
two NaNs is always `false`.

</details>

**Q3.** Is `Double.MIN_VALUE` the most negative `double`? If not, what is?

<details><summary>Answer</summary>

No. `Double.MIN_VALUE` is 4.9E-324, the smallest positive representable
value (a subnormal) — closest to zero on the positive side. The most negative
`double` is `-Double.MAX_VALUE`, approximately -1.7976931348623157E308. The
name is misleading by analogy with `Integer.MIN_VALUE`, which really is the
most negative value for that type.

</details>

**Q4.** What happens when you compute `Double.MIN_VALUE / 2`, and why?

<details><summary>Answer</summary>

It evaluates to exactly `0.0`. `Double.MIN_VALUE` already has only a single
mantissa bit set at the smallest possible magnitude (the subnormal range's
finest step); there is no lower nonzero value to round to, so the result
underflows to zero. This is expected IEEE 754 behavior, not a bug.

</details>

**Q5.** Why does `0.0 / 0.0` produce `NaN` while `1.0 / 0.0` produces
`Infinity`?

<details><summary>Answer</summary>

`1.0 / 0.0` is a nonzero value divided by zero, which IEEE 754 defines as a
sign-carrying overflow to infinity — arithmetic stays total. `0.0 / 0.0` has
no defensible real-number answer (any value times zero is zero, so there is
no unique quotient), so it produces NaN, the sentinel for "no defensible
result," which then contaminates every subsequent computation that touches
it.

</details>

**Q6.** What are the two reserved exponent field codes in binary64, and what
does each one mean?

<details><summary>Answer</summary>

All-zero (biased exponent 0) means zero (if mantissa is also zero) or a
subnormal (if mantissa is nonzero), with the implicit leading bit becoming 0
instead of 1. All-one (biased exponent 2047) means infinity (if mantissa is
zero) or NaN (if mantissa is nonzero) — and for NaN, the sign bit plus the
51 mantissa bits below the quiet-NaN indicator form a free payload, giving
2^52 - 1 distinct NaN encodings.

</details>

---

## Open questions

1. The magnitude of the subnormal-arithmetic performance cliff on the brief's
   build (Oracle JDK 21.0.7, Apple Silicon aarch64) is not measured here —
   only the general hardware-dependent mechanism (microcode/slow-path
   handling on some x86 generations) is documented from public knowledge. A
   JMH microbenchmark comparing repeated arithmetic on normal-range operands
   against subnormal-range operands on this exact build and platform would
   settle the actual slowdown factor, if any, on Apple Silicon.

---

**Leaves covered:** 3.15.1–3.15.5 (5 leaves)
**Leaves deferred:** none
**Diagrams included:** none
**Target version:** Java 21 LTS
**Lines:** 550
