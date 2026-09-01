# 03 Java Core — `BigDecimal` internals: arithmetic, equality and `toString` — INTERNALS (§3.14, 3.14.5–3.14.9)

**Target version: Java 21 LTS.** | **Part 3 of 5** | [Index](../00-index.md)
Previous: [BigDecimal internals: the field set and the compact path](03-internals-bigdecimal.md) · Next: [BigInteger internals and long cents](03b-internals-biginteger-and-long-cents.md)

This file builds on `03`'s field set (`intCompact`, `intVal`, `scale`,
`precision`, `stringCache`) to explain what `BigDecimal`'s arithmetic and
comparison operations actually do to those fields: how `new BigDecimal(double)`
fills them from an exact binary expansion, how `add`/`multiply`/`divide`
manipulate `scale`, why `equals` and `hashCode` treat `scale` as part of the
value's identity, and why `stripTrailingZeros` can produce a negative scale.
`03b` owns `BigInteger`'s own fields and the `long`-cents alternative. The
question this file answers: **given the field set, what exactly happens when
you call `.add()`, `.equals()`, or `.toString()`?**

Measured on Oracle JDK 21.0.7 (build 21.0.7+8-LTS-245), macOS aarch64 (Apple
Silicon), reflective field values via `--add-opens java.base/java.math=ALL-UNNAMED`.

---

## 1. `new BigDecimal(double)` at the field level (3.14.5)

`02a` already told you not to use this constructor for money. This concept
shows exactly what it builds when you do, and proves the digit count rather
than asserting it.

### How it works

The stored `double` for `0.1` is `0x3fb999999999999a` (`Double.doubleToLongBits(0.1)`):
sign bit `0`, biased exponent `1019` → unbiased `1019 - 1023 = -4`, and a
52-bit mantissa ending in `1010` — rounded **up** from the repeating pattern
that would otherwise end `1001` under round-to-nearest-even, because the true binary expansion of
0.1 (derived by repeated doubling: 0.1×2=0.2→0; 0.2×2=0.4→0; 0.4×2=0.8→0;
0.8×2=1.6→1; 0.6×2=1.2→1; then the cycle re-enters 0.2, so the pattern `1100`
repeats forever) never terminates and 52 bits force a cut.

The exact value a `double` holds is `(2^52 + mantissa) × 2^(exponent - 52)`, a
dyadic rational — a fraction whose denominator is a power of two. Because
`1/2^n = 5^n / 10^n`, any such fraction has an *exact*, terminating decimal
expansion, and that expansion has at most as many fractional digits as the
denominator's power of two. Prove the digit count for 0.1's stored double: the
unbiased exponent is −4 and there are 52 mantissa bits, so the denominator is
`2^(52+4) = 2^56`; a value with denominator `2^56` has an exact decimal
expansion of at most 56 fractional digits (since `1/2^56 = 5^56/10^56`, a
56-digit numerator over `10^56`). The measured result lands one digit under
that bound — scale 55, precision 55 — because the leading digit of the
numerator combines with an integer part of zero and the expansion's actual
significant-digit count is 55, not the full 56-digit denominator bound:

```
new BigDecimal(0.1) = 0.1000000000000000055511151231257827021181583404541015625
                       (scale 55, precision 55)
```

Measured field state for this instance: `intCompact = INFLATED` (the 55-digit
unscaled value cannot fit a `long`), `intVal` a 55-digit `BigInteger`, `scale =
55`.

Memory, extending `03`'s derivation method: a 55-digit magnitude needs `int`
words at roughly 9.6 decimal digits per 32-bit word, so `ceil(55 / 9.6) ≈ 6`
words — `int[6]` = 16-byte array header + 24 bytes payload = 40, aligned. Total
= 40 (outer `BigDecimal`) + 40 (`BigInteger`) + 40 (`int[6]`) = **120 bytes,
derived, not measured** — the brief's §6.11 measured a 30-digit inflated value
(4-word magnitude) at 112 bytes, not this 55-digit case; the 120 figure is
parked in `## Open questions` rather than stated as confirmed.

**Insight:** `new BigDecimal(double)` isn't buggy — it's doing exactly what
the field set says it should: it captures the *exact* value the `double`
holds, bit for bit, which is why it produces 55 digits of noise for a value a
human typed as "0.1." `BigDecimal.valueOf(double)` avoids this by routing
through `Double.toString(val)` first (`03`, concept 3), which prints the
shortest decimal that round-trips — "0.1" — and parses *that*.

**Pitfall:** the full three-part entry for this constructor is under
`## Pitfalls`.

> `new BigDecimal(double)` stores the exact binary value the `double`
> represents, not the decimal you typed — for 0.1 that is 55 digits deep,
> proven by the fact that a dyadic denominator of `2^56` bounds the expansion
> at 56 fractional digits.

---

## 2. Scale alignment inside `add`, and scale arithmetic (3.14.6)

### How it works

Every `BigDecimal` represents `unscaled × 10^(-scale)`. Derive each operation's
scale rule from that identity rather than quoting the Javadoc.

**Addition requires equal scales**, because you can only add the unscaled
significands directly once they represent the same power of ten. If
`a = ua × 10^(-sa)` and `b = ub × 10^(-sb)` with `sa < sb`, rewriting `a` as
`(ua × 10^(sb-sa)) × 10^(-sb)` makes the exponents match, so `add` rescales the
operand with the smaller scale by multiplying its significand by the
appropriate power of ten, then adds the (now-aligned) significands and keeps
the larger scale. Measured: `new BigDecimal("3.33").add(new
BigDecimal("0.1"))` gives `3.43` at scale `max(2,1) = 2` — "0.1" is rescaled
from unscaled `1`/scale `1` to unscaled `10`/scale `2` before the add. **This
rescaling multiplication can itself overflow a `long`**, which is why an add
between two previously-compact values can force one operand — and the result —
onto the inflated path.

**Multiplication needs no alignment: significands multiply, scales add.**
`(ua × 10^(-sa)) × (ub × 10^(-sb)) = (ua × ub) × 10^(-(sa+sb))` — no rescaling
step exists in the formula at all. Measured: `new
BigDecimal("3.33").multiply(new BigDecimal("0.10"))` has scale `4` (`2 + 2`);
`new BigDecimal("2.50").multiply(new BigDecimal("4"))` gives `10.00` at scale
`2` (`2 + 0`).

**Division's scale is not determined by the operands at all** — there is no
symmetric identity to derive it from the way there is for add and multiply,
because the exact quotient of two terminating decimals need not itself
terminate (a third's decimal expansion is infinite). That is the structural
reason `divide` must be told what scale to produce. Measured:

```
BigDecimal.ONE.divide(new BigDecimal("3"))
  -> ArithmeticException: Non-terminating decimal expansion; no exact
     representable decimal result.
BigDecimal.ONE.divide(new BigDecimal("2"))              = 0.5
new BigDecimal("10").divide(new BigDecimal("4"))        = 2.5
```

`ONE.divide(3)` with no scale or `MathContext` argument throws because the
exact result — the digit `3` repeating forever after the decimal point — cannot be represented in any finite
scale; `ONE.divide(2)` succeeds because `1/2` terminates exactly at scale 1;
`10.divide(4)` succeeds at scale 1 because `10/4 = 2.5` terminates. Giving an
explicit scale and `RoundingMode` sidesteps the whole problem by accepting an
inexact, rounded answer at a chosen precision instead of demanding the exact
one:

```
BigDecimal.ONE.divide(new BigDecimal("3"), 4, HALF_UP)        = 0.3333
new BigDecimal("100").divide(new BigDecimal("3"), MathContext.DECIMAL32)  = 33.33333
new BigDecimal("100").divide(new BigDecimal("3"), MathContext.DECIMAL64)  = 33.33333333333333
new BigDecimal("100").divide(new BigDecimal("3"), MathContext.DECIMAL128) = 33.33333333333333333333333333333333
```

| Constant | precision | roundingMode |
|---|---|---|
| `MathContext.DECIMAL32` | 7 | `HALF_EVEN` |
| `MathContext.DECIMAL64` | 16 | `HALF_EVEN` |
| `MathContext.DECIMAL128` | 34 | `HALF_EVEN` |
| `MathContext.UNLIMITED` | 0 (unbounded) | `HALF_UP` |

**Insight:** multiplication's scale growth is unbounded and cumulative — each
multiply adds the two input scales, with nothing to cap it — so a chain of
multiplications in a rate calculation (a bonus rate applied, then a fee rate,
then a tax rate) grows the result's scale one multiply at a time until the
value inflates past `MAX_COMPACT_DIGITS` and both memory and per-operation
cost jump (`03b`, concept 3, has the measured ratios). `MathContext` exists
precisely to cap that growth by rounding to a fixed precision after each
operation instead of letting scale accumulate freely. `02c` owns the
design-level guidance on choosing and applying a `MathContext`.

**Code — a chain of multiplications that grows scale unbounded, unless capped:**

```java
BigDecimal stake = new BigDecimal("4.20");
BigDecimal bonusRate = new BigDecimal("0.10");
BigDecimal loyaltyRate = new BigDecimal("0.025");
BigDecimal promoRate = new BigDecimal("0.0015");

BigDecimal uncapped = stake
        .multiply(bonusRate)      // scale 2 + 2 = 4
        .multiply(loyaltyRate)    // scale 4 + 3 = 7
        .multiply(promoRate);     // scale 7 + 4 = 11
System.out.println(uncapped.scale());  // 11, growing every step

BigDecimal capped = stake
        .multiply(bonusRate, MathContext.DECIMAL64)
        .multiply(loyaltyRate, MathContext.DECIMAL64)
        .multiply(promoRate, MathContext.DECIMAL64);
System.out.println(capped.precision() <= 16);  // true — DECIMAL64 bounds precision at 16
```

**Gotcha:** subtraction follows `add`'s scale-alignment rule exactly (it is
implemented as `add(other.negate())`), so no separate derivation is needed.

> `add` must align scales before combining significands because the
> unscaled-times-power-of-ten identity demands matching exponents; `multiply`
> never aligns because scales simply add; `divide` has no derivable scale at
> all, which is why the API forces the caller to supply one.

---

## 3. `equals` at the field level (3.14.7)

### How it works

The verbatim `equals`, JDK 21 `BigDecimal.java`:

```java
    public boolean equals(Object x) {
        if (!(x instanceof BigDecimal xDec))
            return false;
        if (x == this)
            return true;
        if (scale != xDec.scale)
            return false;
        long s = this.intCompact;
        long xs = xDec.intCompact;
        if (s != INFLATED) {
            if (xs == INFLATED)
                xs = compactValFor(xDec.intVal);
            return xs == s;
        } else if (xs != INFLATED)
            return xs == compactValFor(this.intVal);

        return this.inflated().equals(xDec.inflated());
    }
```

Line by line: `!(x instanceof BigDecimal xDec)` is a Java 16+ pattern-matching
`instanceof` — it replaces what used to be an explicit cast after a separate
`instanceof` check, binding `xDec` directly when the test passes. The identity
check `x == this` is placed **after** the type test, not before — a stylistic
choice that costs nothing since the type test is cheap, but it means the
identity fast path is reached only for objects that are already confirmed to
be `BigDecimal`s. `if (scale != xDec.scale) return false;` is the single most
consequential line in the whole method: it returns false before the
significand is examined at all, which is the entire reason `2.0` and `2.00`
are unequal. The remaining branches avoid materialising a `BigInteger` when
either side is compact: if `this` is compact (`s != INFLATED`), the other
side is coerced to a compact `long` via `compactValFor(xDec.intVal)` if
needed and the two `long`s are compared directly; if `this` is inflated but
the other side is compact, the symmetric coercion runs the other way; only
when **both** sides are inflated does the method fall through to comparing
the two `BigInteger`s via `this.inflated().equals(xDec.inflated())`. The `compactValFor` calls
here are the same reason an attached-`intVal` `BigDecimal` (`03`, concept 3)
still compares on the fast `long` path — its `intCompact` is already
populated correctly, so `equals` never needs to touch its `BigInteger` at
all.

Measured field values confirm the scale-first short-circuit:

| Value | `intCompact` | `scale` |
|---|---|---|
| `new BigDecimal("2.0")` | `20` | `1` |
| `new BigDecimal("2.00")` | `200` | `2` |

```
new BigDecimal("2.0").equals(new BigDecimal("2.00"))    -> false   (scale 1 != scale 2)
new BigDecimal("2.0").compareTo(new BigDecimal("2.00")) -> 0       (compareTo ignores scale)
```

`compareTo` is not shown here in full — its job is exactly to answer "same
numeric value regardless of scale," which is why it and `equals` disagree on
these two instances; `02b` owns the application-level consequences of that
split.

**Interview:** "Why are `2.0` and `2.00` not `.equals()`?" — because `equals`
returns false the instant it sees `scale != xDec.scale`, before comparing
significands at all; use `compareTo() == 0` for numeric equality that ignores
scale.

> `equals` treats `scale` as part of a `BigDecimal`'s identity and rejects a
> mismatch before ever looking at the significand; only `compareTo` answers
> "same number" independent of how it's scaled.

---

## 4. `hashCode` includes the scale (3.14.8)

### How it works

The verbatim `hashCode`:

```java
    public int hashCode() {
        if (intCompact != INFLATED) {
            long val2 = (intCompact < 0)? -intCompact : intCompact;
            int temp = (int)( ((int)(val2 >>> 32)) * 31  +
                              (val2 & LONG_MASK));
            return 31*((intCompact < 0) ?-temp:temp) + scale;
        } else
            return 31*intVal.hashCode() + scale;
    }
```

Walking it for the compact path: `val2` is the absolute value of
`intCompact`. `temp` folds the 64-bit `val2` into a 32-bit hash by taking the
high 32 bits (`val2 >>> 32`), multiplying by 31, and adding the low 32 bits
(`val2 & LONG_MASK`, masking off the sign-extended upper bits so only the low
word contributes). The sign of the original `intCompact` is then reapplied to
`temp`. Finally, `31*temp + scale` folds `scale` into the result — the exact
same "multiply-by-31-and-add" combining step used throughout the JDK for
composite hash codes. The inflated branch does the analogous thing using
`intVal.hashCode()` in place of the folded `long`.

`[PROVE]` — compute both measured hash codes by hand. For `2.0`
(`intCompact = 20, scale = 1`): `val2 = 20`; the high 32 bits of `20` are `0`,
so `temp = 0*31 + 20 = 20`; `intCompact` is non-negative so the sign step is a
no-op; result = `31*20 + 1 = 620 + 1 = 621`. For `2.00`
(`intCompact = 200, scale = 2`): `temp = 200`; result = `31*200 + 2 = 6200 + 2
= 6202`. Both match the measured values:

```
new BigDecimal("2.0").hashCode()   =  621
new BigDecimal("2.00").hashCode()  = 6202
```

**This is not a bug — it is required.** `equals` distinguishes `scale` (concept
3), and the `equals`/`hashCode` contract demands that equal objects produce
equal hashes — which, read in the contrapositive, means objects that
`hashCode` puts in *different* buckets are permitted to be unequal, but two
objects that actually differ by scale under `equals` **must not** collide
into a hash function that would let a `HashMap` treat them as interchangeable
in a way that breaks the contract. Since `equals` already treats `2.0` and
`2.00` as different values, `hashCode` **must** also treat their scale as
significant, or a hash-based collection could exhibit inconsistent behaviour
between `equals` and bucket placement. Measured consequence:

```
new HashSet<>(List.of(new BigDecimal("2.0"), new BigDecimal("2.00")))
   prints [2.00, 2.0]   size 2
new TreeSet<>(List.of(new BigDecimal("2.0"), new BigDecimal("2.00")))
   prints [2.0]         size 1
```

`HashSet` (built on `equals`/`hashCode`) keeps both as distinct entries;
`TreeSet` (built on `compareTo`, which ignores scale) collapses them to one.
`../objects-equality-and-lifecycle/01b-equals-hashcode-and-object-methods.md`
owns the general `equals`/`hashCode` contract; `02b-equality-scale-and-rounding.md`
owns the application-level consequences and embeds diagram D-073 covering this
exact `HashSet`-versus-`TreeSet` split — it is not re-embedded here.

**Pitfall:** the full three-part entry — using `BigDecimal` as a `HashMap` key
across differently-scaled values — is under `## Pitfalls`.

> `hashCode` folds `scale` into the result via the same `31*x + y` pattern
> used throughout the JDK, and it must, because `equals` already treats scale
> as part of identity — dropping it from `hashCode` would break the contract
> in the other direction.

---

## 5. `stripTrailingZeros` and negative scale (3.14.9)

### How it works

Derive the negative-scale result from the identity, rather than memorizing
it: `100` as a `BigDecimal` is `unscaled=100, scale=0`, meaning `100 ×
10^0`. Stripping trailing zeros from the significand reduces it from `100` to
`1`; to keep `unscaled × 10^(-scale)` equal to the same value 100, the scale
must become `-2`, since `1 × 10^(-(-2)) = 1 × 10^2 = 100`. Measured:

```
new BigDecimal("100").stripTrailingZeros()                  -> 1E+2
new BigDecimal("100").stripTrailingZeros().scale()            = -2   (NEGATIVE)
```

The source comment on the `scale` field declaration (`03`, concept 1) — "this
may have any value" — is exactly the licence for this: nothing in the field's
type or contract forbids scale going negative, and `stripTrailingZeros` is
the operation that actually produces one from ordinary input.

`toString` prints `1E+2` rather than `100` because the Javadoc for
`BigDecimal.toString()` specifies scientific notation whenever the value's
*adjusted exponent* (roughly, the power-of-ten position of the leading digit
once expressed relative to scale) meets a threshold condition, and a negative
scale reliably triggers that condition. Measured:

```
new BigDecimal("100").stripTrailingZeros().toString()        = "1E+2"
new BigDecimal("100").stripTrailingZeros().toPlainString()    = "100"
new BigDecimal("100.00").stripTrailingZeros()                 -> 1E+2
new BigDecimal("0.00").stripTrailingZeros()                   -> 0
new BigDecimal("1E+2").movePointLeft(2)                        -> 1
```

`toPlainString()` always renders the plain decimal form regardless of scale
sign, which is why it is the escape hatch. `movePointLeft(2)` on `1E+2`
(value 100) correctly returns `1` — the adjustment is on the value, not the
display format, so it composes correctly even through a negative-scale
intermediate.

**Code — the wire-format symptom, complete:**

```java
record BonusCap(BigDecimal amount) {}

BigDecimal cap = new BigDecimal("100.00").stripTrailingZeros();
BonusCap serialised = new BonusCap(cap);
// naive toString() serialisation puts "1E+2" into a JSON body:
String badJson = "{\"amount\":\"" + serialised.amount().toString() + "\"}";
System.out.println(badJson);   // {"amount":"1E+2"}   -- not valid JSON number syntax

// fixed: always render via toPlainString() at the boundary
String goodJson = "{\"amount\":\"" + serialised.amount().toPlainString() + "\"}";
System.out.println(goodJson);  // {"amount":"100"}
```

**Pitfall:** the full three-part entry is under `## Pitfalls`. Guide 12 by
number owns serialization-boundary conventions in general.

> `stripTrailingZeros` can drive `scale` negative — a value the field
> declaration explicitly permits — and a negative scale flips `toString` into
> scientific notation; `toPlainString()` is the fix at every serialization
> boundary.

---

## Pitfalls

### "`new BigDecimal(0.1)` gives me the value I typed, `0.1`"

**Wrong**

```java
BigDecimal fromDouble = new BigDecimal(0.1);
System.out.println(fromDouble);
```

```
0.1000000000000000055511151231257827021181583404541015625
```

**Right**

```java
BigDecimal fromValueOf = BigDecimal.valueOf(0.1);
System.out.println(fromValueOf);
```

```
0.1
```

`valueOf(double)` routes through `Double.toString(0.1)`, which prints the
shortest decimal that round-trips back to the same `double` — "0.1" — and
parses that string; `new BigDecimal(double)` instead captures the `double`'s
exact binary value, which for 0.1 is a 55-digit dyadic fraction, because
0.1 cannot be represented exactly in binary at all.

**Why people believe it:** `BigDecimal(String)` behaves exactly as typed, and
the `double` constructor looks parallel to it in the API, so it's natural to
assume the same "what you typed is what you get" behaviour — but a `double`
literal `0.1` was never actually 0.1 by the time it reaches the constructor;
it's already been rounded to the nearest representable binary value at
compile time.

### "Two `BigDecimal`s with the same numeric value are safe as `HashMap` keys"

**Wrong**

```java
Map<BigDecimal, String> stakeLabels = new HashMap<>();
stakeLabels.put(new BigDecimal("2.00"), "two units, standard entry");
String label = stakeLabels.get(new BigDecimal("2.0"));   // lookup with a differently-scaled equal value
System.out.println(label);
```

```
null
```

**Right**

```java
Map<BigDecimal, String> stakeLabels = new HashMap<>();
BigDecimal canonical = new BigDecimal("2.00").stripTrailingZeros();
stakeLabels.put(canonical, "two units, standard entry");
String label = stakeLabels.get(new BigDecimal("2.0").stripTrailingZeros());
System.out.println(label);
```

```
two units, standard entry
```

Normalizing both the stored key and the lookup key to the same canonical
scale (here, via `stripTrailingZeros()`, or equivalently via a fixed
`setScale`) makes `equals`/`hashCode` agree, because both then carry the same
`scale` field.

**Why people believe it:** `compareTo() == 0` treats `2.0` and `2.00` as "the
same number," and it's natural to assume `HashMap`, which stores by key
equality, will behave the same way — but `HashMap` uses `equals`/`hashCode`,
not `compareTo`, and those two methods disagree on scale by design.

### "`stripTrailingZeros().toString()` on a whole-number amount is always safe to display"

**Wrong**

```java
BigDecimal bonusCap = new BigDecimal("100.00").stripTrailingZeros();
System.out.println("Cap: " + bonusCap);
```

```
Cap: 1E+2
```

**Right**

```java
BigDecimal bonusCap = new BigDecimal("100.00").stripTrailingZeros();
System.out.println("Cap: " + bonusCap.toPlainString());
```

```
Cap: 100
```

`toPlainString()` always renders the ordinary decimal form; `toString()`
switches to scientific notation once the adjusted exponent condition fires,
which a negative scale (produced whenever trailing zeros strip past the
decimal point into the integer part) reliably triggers.

**Why people believe it:** `toString()` is the default rendering for almost
every Java type and usually "just works" for display, so it's easy to assume
it's safe for `BigDecimal` too — but `BigDecimal.toString()`'s contract is
specifically documented to use scientific notation under certain scale
conditions, which most other numeric types' `toString()` never does.

---

## Cheat sheet

| Thing | Fact (Java 21 LTS) |
|---|---|
| `new BigDecimal(0.1)` | 55-digit exact expansion, scale 55, precision 55, `intCompact = INFLATED` |
| `BigDecimal.valueOf(0.1)` | `"0.1"`, via `Double.toString` |
| Dyadic-denominator digit bound | `2^n` denominator → at most `n` fractional decimal digits (`1/2^n = 5^n/10^n`) |
| 0.1's stored double exponent | unbiased −4, 52 mantissa bits → denominator `2^56` |
| `add` scale rule | rescale smaller-scale operand up, result scale = `max(sa, sb)` |
| `add` overflow risk | rescaling multiply can overflow a `long`, forcing inflation |
| `multiply` scale rule | `result scale = sa + sb`, no alignment |
| `divide` scale rule | not derivable from operands; caller must supply scale or `MathContext` |
| `ONE.divide(3)` no args | `ArithmeticException: Non-terminating decimal expansion; no exact representable decimal result.` |
| `ONE.divide(3, 4, HALF_UP)` | `0.3333` |
| `MathContext.DECIMAL32/64/128` | precision 7/16/34, all `HALF_EVEN` |
| `MathContext.UNLIMITED` | precision 0 (unbounded), `HALF_UP` |
| `3.33 + 0.1` | `3.43`, scale `max(2,1)=2` |
| `3.33 * 0.10` | scale 4 (`2+2`) |
| `2.50 * 4` | `10.00`, scale 2 (`2+0`) |
| `equals` scale check | `if (scale != xDec.scale) return false;` — first check, before significand |
| `equals` compact/inflated | coerces via `compactValFor` so an attached-`intVal` value still fast-paths |
| `2.0.equals(2.00)` | `false` |
| `2.0.compareTo(2.00)` | `0` |
| `hashCode` fold | `31*temp + scale`, `temp` from folding `val2`'s high/low 32-bit halves |
| `2.0` hashCode, by hand | `31*20+1 = 621` |
| `2.00` hashCode, by hand | `31*200+2 = 6202` |
| `HashSet` of `{2.0, 2.00}` | size 2 |
| `TreeSet` of `{2.0, 2.00}` | size 1 |
| `stripTrailingZeros("100")` | unscaled `1`, scale `-2` |
| `stripTrailingZeros("100").toString()` | `"1E+2"` |
| `stripTrailingZeros("100").toPlainString()` | `"100"` |
| `stripTrailingZeros("0.00")` | `0` |
| `new BigDecimal("1E+2").movePointLeft(2)` | `1` |
| Fix for scientific-notation wire bug | `toPlainString()` at every serialization boundary |
| Canonical bonus split (3.33 stake) | `0.33` bonus + `3.00` cash, sums exactly to `3.33` |
| Wrong-direction rounding | `0.34` bonus + `3.00` cash = `3.34` — creates money |

---

## Self-test

**Q1.** Why does `new BigDecimal(0.1)` produce 55 digits instead of 1?

<details><summary>Answer</summary>

Because 0.1 has no exact binary (base-2) representation — its binary
expansion repeats forever — so the `double` type stores the nearest
representable value, a dyadic rational with a denominator that's a power of
two (specifically `2^56` for 0.1's stored bit pattern, from unbiased exponent
−4 and 52 mantissa bits). Any dyadic rational has an exact, terminating
decimal expansion, because `1/2^n` equals `5^n/10^n`, but that expansion can
run up to as many digits as the exponent — 55 significant digits in this
case. `new BigDecimal(double)` captures that exact stored value bit-for-bit,
which is why it shows all 55 digits rather than the "0.1" a human typed.

</details>

**Q2.** Why can't `divide`'s result scale be derived the way `add`'s and `multiply`'s can?

<details><summary>Answer</summary>

`add` and `multiply` both have a clean algebraic identity connecting the
input scales to the output scale — `add` needs matching exponents so the
result scale is the max of the two, and `multiply`'s scales simply add
because there's no rescaling step in the formula. Division has no such
identity, because the exact quotient of two terminating decimals is not
guaranteed to terminate itself — a third, for instance, is an infinite
repeating decimal. There is no finite scale that always represents the exact
answer, so the API requires the caller to either accept an exception when no
exact answer exists, or explicitly supply a scale and rounding mode to get an
approximate, but well-defined, result.

</details>

**Q3.** Walk through why `new BigDecimal("2.0")` and `new BigDecimal("2.00")` are not `.equals()` but do have `compareTo() == 0`.

<details><summary>Answer</summary>

`equals`'s very first substantive check is `if (scale != xDec.scale) return
false;` — it returns immediately once it sees the two scales differ, `1`
versus `2`, without ever looking at the significands. It never gets to the
point of noticing that `20 × 10^-1` and `200 × 10^-2` represent the same
numeric value. `compareTo`, by contrast, is specifically designed to compare
the two as numbers, which means it accounts for scale differences internally
and correctly reports them as numerically equal, returning `0`.

</details>

**Q4.** Prove by hand that `new BigDecimal("2.00").hashCode()` is 6202.

<details><summary>Answer</summary>

`intCompact` for `2.00` is `200`, `scale` is `2`. Since `intCompact != INFLATED`,
`val2 = 200` (already non-negative). The high 32 bits of `200` are `0`, so
`temp = (0 * 31) + 200 = 200`. Since `intCompact` is non-negative, the sign
step leaves `temp` at `200`. The final return is `31 * temp + scale = 31 *
200 + 2 = 6200 + 2 = 6202`, matching the measured value.

</details>

**Q5.** Why must `hashCode` fold in `scale`, given that `compareTo` deliberately ignores it?

<details><summary>Answer</summary>

Because `hashCode`'s contract is tied to `equals`, not to `compareTo` — equal
objects (by `equals`) must produce equal hash codes, and since `equals`
already treats differently-scaled values as unequal, `hashCode` folding in
`scale` is what keeps it consistent with `equals`. If `hashCode` ignored scale
while `equals` didn't, you could still satisfy the letter of the contract
(equal objects would still hash equally, since equal objects necessarily have
equal scale too), but hash distribution would be worse and, more importantly,
it would be a coincidence of implementation rather than a design that
generalizes — the JDK's actual choice ties the two together deliberately.
`compareTo` answers a different question ("same number?") and is allowed —
required, even, by its own contract with `equals` being "inconsistent with
equals" here — to disagree.

</details>

**Q6.** A `BonusCap` amount serializes to JSON as `"1E+2"` instead of `"100"`. What produced that, and what's the fix?

<details><summary>Answer</summary>

The value went through `stripTrailingZeros()` at some point, which reduced
`100`'s unscaled value from `100` to `1` and, to preserve the numeric value,
drove `scale` to `-2` — a value the `scale` field's own source comment
explicitly permits ("this may have any value"). `BigDecimal.toString()`'s
Javadoc specifies scientific notation once the adjusted exponent condition a
negative scale triggers is met, which is why it printed `1E+2`. The fix is to
call `toPlainString()` instead of relying on `toString()` at any
serialization boundary — `toPlainString()` always renders the ordinary
decimal form regardless of scale sign.

</details>

---

## Open questions

1. The exact retained byte count for a 55-digit inflated `BigDecimal` (as
   produced by `new BigDecimal(0.1)`) is derived here as 120 bytes by
   extending `03`'s measured-40/104/112 method to a 6-word magnitude, but it
   was not itself measured in the brief's evidence — a heap-delta run over
   2,000,000 such instances would confirm or correct it.

---

**Leaves covered:** 3.14.5–3.14.9 (5 leaves)
**Leaves deferred:** none
**Diagrams included:** none
**Target version:** Java 21 LTS
**Lines:** 671
