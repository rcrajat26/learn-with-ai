# 03 Java Core — `MathContext`, the constants, and a `Money` type — INTERMEDIATE (§2.4, 2.4.16–2.4.19)

**Target version: Java 21 LTS.** | **Part 2 of 5** | [Index](../00-index.md)
Previous: [Rounding modes and the BigDecimal API surface](02g-rounding-modes-and-the-api-surface.md) · Next: [Storage, BigInteger and cost](02d-storage-biginteger-and-cost.md)

This file owns four things: rounding by significant digits instead of by decimal
place (`MathContext` and its four constants), the trap in checking a `BigDecimal`
for zero, the minor-units `long` alternative to `BigDecimal` and its exact cost,
and a `Money` type that closes the three holes a bare `BigDecimal` amount leaves
open. `02b` owns `equals` versus `compareTo`, the eight `RoundingMode`s and
`setScale` in full — this file only reuses them. `02d` owns storage and
`BigInteger`. The question this file answers: once you can round a `BigDecimal`
correctly, how do you pick *which kind* of rounding, how do you avoid the classic
zero-check bug, and when do you leave `BigDecimal` altogether for a `long`. All
measurements below were taken on Oracle JDK 21.0.7 (build 21.0.7+8-LTS-245),
macOS aarch64, with library source quoted from that build's `lib/src.zip`.

This file carries no diagram from the topic's manifest. `02b` owns D-073 and
D-074 (equality and rounding-mode pictures); `03-internals-bigdecimal.md` owns
D-125 (the field layout, `INFLATED` and all).

---

## 1. `MathContext`: rounding by precision instead of by scale (2.4.16)

A `BigDecimal`'s `scale` counts digits *after* the decimal point. A
`MathContext`'s `precision` counts *significant* digits, full stop, wherever the
point falls. `stake.setScale(2, RoundingMode.HALF_EVEN)` says "two places after
the point, whatever the magnitude of the value in front of it." `new
MathContext(7, RoundingMode.HALF_EVEN)` says "seven significant digits total,
wherever the point lands" — the same seven digits describe `1234.567` and
`0.0001234567`.

### Why it exists

Money has a fixed minor unit, so scale is the right question: a `Movement` in
GBP is always two digits after the point, regardless of whether the amount is
0.01 or 1,000,000.00. But not every `BigDecimal` computation is money.
Intermediate values in a rate calculation, a statistical estimate, or a
compounding projection can range over many orders of magnitude, and the
meaningful digit *count* — not digit *position* — is what should stay fixed.
`MathContext` exists because `divide`, `add`, `subtract` and `multiply` all
have overloads that take one, and because unlimited-precision division is
sometimes not just slow but undefined (division that does not terminate has no
exact decimal answer at all — see `BigDecimal.ONE.divide(new
BigDecimal("3"))` below).

### How it works

A `MathContext` is an immutable pair: an `int precision` and a `RoundingMode`.
Four are predefined as `public static final` constants on `MathContext`, and
their measured values on this build are:

| Constant | `precision` | `RoundingMode` | Corresponds to |
|---|---|---|---|
| `MathContext.DECIMAL32` | 7 | `HALF_EVEN` | IEEE 754-2008 `decimal32` |
| `MathContext.DECIMAL64` | 16 | `HALF_EVEN` | IEEE 754-2008 `decimal64` |
| `MathContext.DECIMAL128` | 34 | `HALF_EVEN` | IEEE 754-2008 `decimal128` |
| `MathContext.UNLIMITED` | 0 | `HALF_UP` | No IEEE analogue |

The three named constants track the significand widths of the IEEE 754-2008
decimal interchange formats, which is why the precisions are 7, 16 and 34
rather than round powers of ten — the standard fixes those digit counts for
`decimal32`/`decimal64`/`decimal128` and the `java.math` Javadoc for
`MathContext` cites the same standard by name. `UNLIMITED` reports precision 0,
which the Javadoc defines as "unlimited precision arithmetic" — no rounding is
ever performed, so the `HALF_UP` mode attached to it can never fire; it exists
only because the `MathContext(int, RoundingMode)` constructor requires some
mode to be named.

Measured, dividing 100 by 3 at each named precision (§6.8):

```
new BigDecimal("100").divide(new BigDecimal("3"), MathContext.DECIMAL32)
  = 33.33333                                (7 significant digits)
new BigDecimal("100").divide(new BigDecimal("3"), MathContext.DECIMAL64)
  = 33.33333333333333                       (16 significant digits)
new BigDecimal("100").divide(new BigDecimal("3"), MathContext.DECIMAL128)
  = 33.33333333333333333333333333333333     (34 significant digits)
```

Each result has more `3`s after the point purely because the constant asks for
more total significant digits, not because the scale was configured directly —
the scale falls out of wherever the requested precision lands relative to the
integer part.

### When precision-based rounding beats scale-based

Take `AssessmentService` computing an affordability multiplier during
onboarding: `projectedCapacity = monthlyIncome.multiply(savingsRate, mc)` where
`savingsRate` might be `0.00034` for a low earner or `0.62` for a high one. If
you fixed a `scale(2)` on that intermediate, a genuinely small projection like
`0.000034` rounds straight to `0.00` and the information is gone before the
next multiplication ever sees it. If you instead fixed a generous `scale(20)`
to protect the small case, a large intermediate like `6175000` now carries
twenty trailing zero-ish digits that mean nothing and bloat every downstream
operation. Neither scale choice is right, because the *right* digit count does
not move with the value — which is exactly what `MathContext` is for:
`monthlyIncome.multiply(savingsRate, MathContext.DECIMAL64)` keeps 16
significant digits whether the result is `0.000034000000000000` or
`6175000.000000000000`, at the correct place each time.

The rule, stated plainly: use `MathContext` for an intermediate whose magnitude
you do not control in advance — a rate, a ratio, a projection. Use `setScale`
at the boundary where the value becomes an actual money amount with a fixed
minor unit — a `Movement`, a `Wallet` balance, anything that will be persisted
or displayed as currency.

**Pitfall:** the arithmetic-with-`MathContext` overloads —
`add(BigDecimal, MathContext)`, `subtract(BigDecimal, MathContext)`,
`multiply(BigDecimal, MathContext)`, `divide(BigDecimal, MathContext)` — round
the *result of that one call*, not just a final answer. Chain three of them
and you round three times, and each rounding's error can compound into the
next operation's input. A single `setScale` applied once, at the end of a
computation, rounds exactly once. If you must chain `MathContext`-bearing
calls, use `UNLIMITED` (or ordinary scale-tracking arithmetic) through the
intermediates and apply the precision or scale limit only at the boundary.

**Interview:** "When would you use `MathContext` over `setScale`?" — one line:
scale is for values with a fixed minor unit (money, at the boundary);
precision is for values whose magnitude varies and where the significant-digit
count, not the decimal position, is what must stay fixed (rates, scientific
intermediates).

> **`MathContext` fixes the count of significant digits kept after an
> operation, independent of where the decimal point falls; `setScale` fixes
> the count of digits kept after the point, independent of magnitude.**

---

## 2. The constants, and the cheap zero check (2.4.17)

`BigDecimal` publishes three cached constants — `ZERO`, `ONE`, `TEN` — and the
single most common bug in code that uses them is checking for zero the wrong
way. Measured on this build:

```
new BigDecimal("0.00").equals(BigDecimal.ZERO)      -> false
new BigDecimal("0.00").compareTo(BigDecimal.ZERO)   -> 0
new BigDecimal("0.00").signum()                     -> 0
```

### Why the trap exists

From `02a`, a `BigDecimal`'s identity is its unscaled value plus its scale.
`BigDecimal.ZERO` is constructed with scale 0. Any `BigDecimal` your own code
computes and rounds to two places — `setScale(2, RoundingMode.DOWN)` on an
exhausted bonus, say — carries scale 2, printing as `0.00`. From `02b`'s `equals` source, the
very first line of the comparison is `if (scale != xDec.scale) return false;`
— `equals` rejects on the scale mismatch before it ever inspects the
significand, so two values that represent the identical number compare
unequal.

### The concrete QuizStakes symptom

`BonusService` needs to know when a client's bonus is exhausted so it can stop
drawing from it and flip the `Bonus` to `CONSUMED`. Written as:

```java
if (bonusAvailable.equals(BigDecimal.ZERO)) {
    bonus.markConsumed();
}
```

`bonusAvailable` arrived from a ledger computation that ended in
`setScale(2, RoundingMode.DOWN)`, so an exhausted balance is the `BigDecimal`
`0.00` — scale 2. `equals(BigDecimal.ZERO)` (scale 0) returns `false` every
time. `BonusService` never marks the `Bonus` `CONSUMED`; every subsequent
stake keeps attempting to draw a non-existent remainder from an empty bucket,
and `min(BONUS_AVAILABLE, 10% of stake)` silently degenerates to zero forever
without the bucket's lifecycle ever closing.

**Pitfall:** the wrong belief is "`equals` compares numeric value, so
`equals(ZERO)` is a safe zero check." The symptom is exactly the `BonusService`
case above — a value that is mathematically zero and prints as `0.00` never
equals `BigDecimal.ZERO`. The fix is `bonusAvailable.signum() == 0`, or
equivalently `bonusAvailable.compareTo(BigDecimal.ZERO) == 0` — either compares
value, not (value, scale). **Why people believe it:** `equals` is the default
tool reached for whenever "is this the same as X" comes up, and for almost
every other type in the JDK, value equality is exactly what `equals` gives you
— `BigDecimal` is the outlier, and nothing about its Javadoc summary line
warns you away from the assumption before you hit it.

Ranked by what each check actually costs and means:

| Check | Correct for any scale? | Cost |
|---|---|---|
| `signum() == 0` | Yes | Reads one cached `int`/derived field, no allocation, scale-independent — the right default |
| `compareTo(BigDecimal.ZERO) == 0` | Yes | Correct, but does a full magnitude comparison with scale alignment |
| `equals(BigDecimal.ZERO)` | Only when the other value's scale happens to be exactly 0 | Wrong for any other scale — never use for a zero test |

`signum()` wins on both correctness and cost: it needs no scale alignment at
all, because the sign of a number does not depend on how many trailing zeros
you chose to keep.

The constants themselves, measured (§6.8, §6.7): `BigDecimal.ZERO.scale()` is
`0`; `BigDecimal.ONE` prints as `1`; `BigDecimal.TEN` prints as `10`. §6.7 also
shows `BigDecimal.ZERO` is built through a private constructor from one of a
small array of cached values, and — unlike most `BigDecimal`s constructed from
a compact `long`, which null out `intVal` — `ZERO`'s `intVal` field is
non-null, holding a cached `BigInteger` zero. The field-by-field reason lives
in `03-internals-bigdecimal.md`; the operational fact you need here is just
that `ZERO`, `ONE` and `TEN` are singletons you can compare against safely with
`signum()`/`compareTo()`, never with `equals()`.

**Insight:** the bug is not really about `BigDecimal.ZERO` specifically — it is
that `equals` on `BigDecimal` encodes *representation* equality (same
unscaled value, same scale), while `compareTo` and `signum()` encode
*mathematical* equality. Every zero check is a special case of the more general
rule from `02b`: reach for `compareTo`, not `equals`, whenever the values being
compared might have travelled through different rounding or construction
paths.

> **A `BigDecimal` is zero, mathematically, exactly when `signum() == 0` —
> never test with `equals(BigDecimal.ZERO)`, because `equals` also demands an
> identical scale.**

---

## 3. The minor-units `long` alternative (2.4.18)

Storing a stake as the `long` `420` and remembering, in your own head, that it
means 4.20 is exactly what a compact `BigDecimal` does internally — keep the
unscaled integer (`intCompact`), drop the `scale` field, and hold the scale as
an external fact instead of an object field. Framed that way, both the win and
the cost of the minor-units approach fall out of the same sentence: you keep
the fast, cheap part of `BigDecimal`'s representation and you lose the part
that made it self-describing and safe.

### The win, measured

Memory (§6.11): a compact `BigDecimal.valueOf(cents, 2)` measures **40 bytes**
per instance (12-byte header + 4-byte `intVal` reference + 4-byte `scale` +
4-byte `precision` + 4-byte `stringCache` reference + 8-byte `intCompact`,
rounding 36 up to the 8-byte alignment boundary gives 40). A boxed `Long`
measures **24 bytes** (12-byte header + 8-byte value, rounded up), but the
domain-relevant comparison is a raw `long` field inside another object, which
costs exactly its **8 bytes** with no header of its own — a **5x** reduction
against the 40-byte `BigDecimal`.

Speed (§6.12, measured wall-clock loop timings on JDK 21.0.7, explicitly not
JMH — no error bars, and a vectorisable loop can flatter the primitive case):
summing 5,000,000 array elements, `long` cents summation runs at **0.26
ns/op**, compact `BigDecimal.add` at **2.24 ns/op** — a measured **8.6x**
ratio.

QuizStakes scale, from the brief's own daily volume: at 19,800,000 ledger
entries/day, storing each as a compact `BigDecimal`:

```
19,800,000 × 40 bytes = 792,000,000 bytes ≈ 792 MB/day
```

against storing each as a `long`:

```
19,800,000 × 8 bytes = 158,400,000 bytes ≈ 158 MB/day
```

— roughly 634 MB/day saved, matching the 5x ratio above. And the whole-day
`add` cost, from the measured per-op figures: 2,800,000 stake-reservation
`BigDecimal.add` calls run in about 11 ms (2,800,000 × 2.24 ns ≈ 6.27 ms of
pure add time, 11 ms measured including loop/array overhead); the equivalent
`long` sum finishes in under 1 millisecond.

### The cost, stated as bluntly as the win

The scale lives nowhere the compiler can check. A `long cents = 420` and a
`long units = 4` are the exact same type — nothing in the type system stops a
caller passing a value scaled in units where the callee expected minor units,
or vice versa. A `PaymentService` method typed `void credit(long amountCents)`
compiles just as happily when called as `credit(420L)` (meaning 4.20) as when
called as `credit(4L)` (meaning 0.04) or, worse, when some upstream code passes
whole units by mistake and creates a **silent 100x error** — no exception, no
warning, just a wrong number that looks plausible until reconciliation catches
it.

The overflow bound, worked out (§6.12): `Long.MAX_VALUE` is
9,223,372,036,854,775,807. Interpreted as scale-2 cents, that is:

```
9,223,372,036,854,775,807 / 100 = 92,233,720,368,547,758.07 units
```

At 19,800,000 ledger entries/day averaging a stake of 4.20 (so 420 cents per
entry), one day's total volume in cents is:

```
19,800,000 × 420 = 8,316,000,000 cents/day
```

A single running total accumulating at that rate reaches `Long.MAX_VALUE`
after:

```
9,223,372,036,854,775,807 / 8,316,000,000 ≈ 1,109,111,596 days
1,109,111,596 / 365 ≈ 3,038,661 years
```

— so a per-client or per-position running total in cents cannot practically
overflow. What *can* overflow, and far sooner, is an **intermediate multiply**:
multiplying two moderately large `long`s (a large balance by a percentage
scaled as an integer, for instance) can exceed `Long.MAX_VALUE` long before any
running total would, and a plain `*` silently wraps rather than throwing. This
is exactly why `Math.multiplyExact` (and `addExact`/`subtractExact`) belong in
any long-cents arithmetic path — see
`../primitives-and-conversions/01a-integral-arithmetic.md` for overflow
semantics and the `*Exact` family in full, and
`03b-internals-biginteger-and-long-cents.md` for the internals treatment of
this same bound.

**The verdict:** `BigDecimal` at the domain boundary and in the ledger of
record — `FundsLedger`, `Movement`, anything that gets persisted, displayed,
or reconciled — because its self-describing scale and exact decimal semantics
are worth the 8.6x and the 5x. Minor-units `long` only inside a measured hot
path where the volume justifies the risk — and never let both representations
coexist for the same value without a named, explicit conversion function that
states the scale in its own signature (`long toCents(BigDecimal amount)`, not
a bare cast).

> **A minor-units `long` trades `BigDecimal`'s 40-byte, self-describing,
> 2.24 ns/op representation for an 8-byte, 0.26 ns/op integer whose scale
> exists only in the reader's head — a trade worth making only in a measured
> hot path, never in the ledger of record.**

---

## 4. A `Money` type, and why `BigDecimal` alone is not one (2.4.19)

A bare `BigDecimal amount` field, wherever it appears — a method parameter, a
`Wallet` DTO field, a `Movement` row — carries a number and nothing else. It
does not carry which currency that number is denominated in, it does not
enforce that the scale matches the currency's minor unit, and it does not stop
two amounts in different currencies from being added as if they were
comparable. `cashAvailable.add(bonusAvailable)` compiles and runs whether or
not the two happen to share a currency; a value with scale 4 slots into a
field every downstream reader assumes is scale 2, with no compiler diagnostic
either way. `BigDecimal` gives you exact decimal arithmetic; it does not give
you a *money type*.

A `Money` type closes those three holes: it pairs the amount with its
`Currency`, it normalises the scale from the currency itself rather than a
hardcoded constant, and it makes cross-currency arithmetic a compile-time
non-issue turned into a runtime-checked one at the single point where two
`Money` values actually meet.

```java
import java.math.BigDecimal;
import java.math.RoundingMode;
import java.util.Currency;
import java.util.Objects;

public record Money(BigDecimal amount, Currency currency) {

    public Money {
        Objects.requireNonNull(amount, "amount");
        Objects.requireNonNull(currency, "currency");
        int minorUnits = currency.getDefaultFractionDigits();
        if (minorUnits < 0) {
            throw new IllegalArgumentException(
                "currency has no fixed minor unit: " + currency);
        }
        if (amount.scale() != minorUnits) {
            amount = amount.setScale(minorUnits, RoundingMode.UNNECESSARY);
        }
    }

    public static Money of(BigDecimal amount, Currency currency) {
        int minorUnits = currency.getDefaultFractionDigits();
        BigDecimal normalised = amount.setScale(minorUnits, RoundingMode.HALF_EVEN);
        return new Money(normalised, currency);
    }

    public static Money zero(Currency currency) {
        int minorUnits = currency.getDefaultFractionDigits();
        return new Money(BigDecimal.ZERO.setScale(minorUnits), currency);
    }

    public Money add(Money other) {
        requireSameCurrency(other);
        return Money.of(this.amount.add(other.amount), currency);
    }

    public Money subtract(Money other) {
        requireSameCurrency(other);
        return Money.of(this.amount.subtract(other.amount), currency);
    }

    public Money multiply(BigDecimal scalar) {
        return Money.of(this.amount.multiply(scalar), currency);
    }

    public boolean isZero() {
        return amount.signum() == 0;
    }

    public boolean isGreaterThan(Money other) {
        requireSameCurrency(other);
        return this.amount.compareTo(other.amount) > 0;
    }

    public boolean isGreaterThanOrEqualTo(Money other) {
        requireSameCurrency(other);
        return this.amount.compareTo(other.amount) >= 0;
    }

    private void requireSameCurrency(Money other) {
        if (!this.currency.equals(other.currency)) {
            throw new IllegalArgumentException(
                "currency mismatch: " + this.currency + " vs " + other.currency);
        }
    }

    @Override
    public boolean equals(Object obj) {
        if (this == obj) {
            return true;
        }
        if (!(obj instanceof Money other)) {
            return false;
        }
        return this.currency.equals(other.currency)
            && this.amount.compareTo(other.amount) == 0;
    }

    @Override
    public int hashCode() {
        return Objects.hash(amount.stripTrailingZeros(), currency);
    }

    @Override
    public String toString() {
        return amount.toPlainString() + " " + currency.getCurrencyCode();
    }
}
```

The compact constructor guards the invariant on every construction path
(including the record's own canonical one); the `of` factory is the normal
entry point and rounds a caller-supplied amount to the currency's own
`getDefaultFractionDigits()` — 2 for GBP and USD, 0 for JPY — rather than a
hardcoded `2` that would silently mis-scale a yen amount. `add`/`subtract`
reject a currency mismatch before doing any arithmetic. `equals` compares
value via `compareTo`, not raw `BigDecimal.equals`, so two `Money` values
constructed via different paths but equal in value and currency compare equal
— the exact fix for the trap in Section 2, applied at the type's boundary so
every caller gets it for free. `hashCode` uses `stripTrailingZeros()` to stay
consistent with that `equals` (see `02b` for why hash and equals must agree on
what "equal" means). `toString` uses `toPlainString()`, never the default
`toString()`, so a value like `1E+2` never leaks into a log line meant to read
as currency.

`StakeSplit` builds directly on `Money`, enforcing its own invariant — the two
portions sum exactly to the stake — in a compact constructor by construction
rather than by post-hoc check: the cash portion is *derived* as the
remainder, so there is no arithmetic path that can produce a mismatch.

```java
import java.math.BigDecimal;
import java.math.RoundingMode;

public record StakeSplit(Money bonusPortion, Money cashPortion) {

    public StakeSplit {
        if (!bonusPortion.currency().equals(cashPortion.currency())) {
            throw new IllegalArgumentException(
                "StakeSplit portions must share a currency: "
                    + bonusPortion.currency() + " vs " + cashPortion.currency());
        }
    }

    public static StakeSplit of(Money stake, Money bonusAvailable) {
        if (!stake.currency().equals(bonusAvailable.currency())) {
            throw new IllegalArgumentException(
                "stake and bonus must share a currency: "
                    + stake.currency() + " vs " + bonusAvailable.currency());
        }
        BigDecimal tenPercentOfStake = stake.amount()
            .multiply(new BigDecimal("0.10"))
            .setScale(stake.currency().getDefaultFractionDigits(), RoundingMode.DOWN);
        BigDecimal bonusAmount = tenPercentOfStake.min(bonusAvailable.amount());
        Money bonusPortion = Money.of(bonusAmount, stake.currency());
        Money cashPortion = stake.subtract(bonusPortion);
        return new StakeSplit(bonusPortion, cashPortion);
    }

    public Money total() {
        return bonusPortion.add(cashPortion);
    }
}
```

Working the canonical case through this code: a stake of 3.33 GBP against
ample bonus available.

```java
import java.math.BigDecimal;
import java.util.Currency;

public final class StakeSplitDemo {
    public static void main(String[] args) {
        Currency gbp = Currency.getInstance("GBP");
        Money stake = Money.of(new BigDecimal("3.33"), gbp);
        Money bonusAvailable = Money.of(new BigDecimal("50.00"), gbp);

        StakeSplit split = StakeSplit.of(stake, bonusAvailable);

        System.out.println("bonus portion: " + split.bonusPortion());
        System.out.println("cash portion:  " + split.cashPortion());
        System.out.println("total:         " + split.total());
        System.out.println("invariant holds: " + split.total().equals(stake));
    }
}
```

Following the arithmetic by hand, matching §6.8's measured values: 10% of
3.33 is `3.33 × 0.10 = 0.3330` (scale 4, since scales add on multiply), and
`setScale(2, DOWN)` truncates that to `0.33`. `min(0.33, 50.00)` is `0.33`, so
the bonus portion is 0.33. The cash portion is derived, not separately
computed: `3.33 − 0.33 = 3.00`. The total is `0.33 + 3.00 = 3.33`, which
equals the original stake — the invariant holds by construction, because
`cashPortion` was never anything other than `stake.subtract(bonusPortion)`.
Rounding the bonus portion the other way — `HALF_UP` would give `0.33` here
too since the fourth digit is 0, but a stake where the fourth-decimal digit
rounds up (say a stake whose 10% lands on a value ending `5` at the third decimal) would
push the bonus to `0.34` while cash still supplies `3.00`, totalling `3.34` —
one cent created from nothing. `DOWN` on the bonus, with cash as the exact
remainder, is the only split that cannot manufacture money.

**Pitfall:** computing both portions independently — `bonus =
round(stake × 0.10)` and `cash = round(stake × 0.90)` — looks symmetric and
innocent, but each rounds separately, and two independently rounded halves are
not guaranteed to sum back to the original stake. The fix is exactly what
`StakeSplit.of` does above: round one portion, derive the other as the exact
remainder by subtraction, and the invariant is structurally guaranteed rather
than merely usually true. **Why people believe it:** "split into two pieces"
reads as a naturally symmetric operation, and rounding each piece the same way
feels like the fair, consistent choice — until the two roundings land on
opposite sides of a half-cent boundary and the sum drifts by exactly the
amount the "fair" rounding was supposed to prevent.

**Insight:** a record's identity is its component values — two `Money(3.33,
GBP)` values, however constructed, are the same `Money`. That is precisely
the semantics money needs (two ways of arriving at 3.33 GBP are the same 3.33
GBP) and precisely the semantics a JPA-managed entity must *not* have (two
`Client` rows with the same field values are still two different rows if they
have different primary keys). See
`../immutability-and-design/02-immutability.md` for immutability as a design
discipline in general, `../records-and-sealed/01-basics.md` for records
themselves, and guide 08 (Spring Data JPA) by number for why an `@Entity`
should not be a record.

**Interview:** "Why not just use `BigDecimal` for money?" — one line: because
money is an amount *and* a currency *and* a fixed scale, and `BigDecimal`
alone lets you add mismatched currencies and lets an inconsistent scale slip
through unnoticed; a `Money` type makes both mistakes a compile-time-adjacent,
constructor-time-enforced error instead of a silent one.

No gotcha beyond what is already covered above: the one thing to watch —
`getDefaultFractionDigits()` returning a negative value for currencies with no
fixed minor unit (funds/precious-metal codes) — is guarded explicitly in the
compact constructor above rather than left to surprise a caller.

> **`BigDecimal` gives exact arithmetic on one number; `Money` adds the
> currency and the scale discipline that turn that number into an amount you
> can safely compare, add, and persist.**

---

## Pitfalls

### `equals(BigDecimal.ZERO)` is a safe way to test for zero

**Wrong**

```java
BigDecimal bonusAvailable = new BigDecimal("0.33")
    .subtract(new BigDecimal("0.33"))
    .setScale(2, RoundingMode.DOWN);
boolean exhausted = bonusAvailable.equals(BigDecimal.ZERO);
```

`bonusAvailable` prints as `0.00` (scale 2); `BigDecimal.ZERO` has scale 0;
`exhausted` is `false` — measured, `new BigDecimal("0.00").equals(BigDecimal.ZERO)`
returns `false`.

**Right**

```java
boolean exhausted = bonusAvailable.signum() == 0;
```

`signum()` reads the sign independent of scale — measured, `new
BigDecimal("0.00").signum()` returns `0` regardless of how many trailing
zeros the value's scale carries.

**Why people believe it:** for every other common JDK type, `equals` means
"same value," so reaching for it on `BigDecimal` feels like the obviously
correct, idiomatic move — nothing in the type's surface API warns that its
`equals` is representation equality, not value equality, until a scale
mismatch produces a wrong answer in production.

### Chaining `MathContext`-bearing arithmetic rounds at every step

**Wrong**

```java
MathContext mc = MathContext.DECIMAL64;
BigDecimal result = principal
    .multiply(rate, mc)
    .add(fee, mc)
    .divide(periods, mc);
```

Each of `multiply`, `add` and `divide` rounds its own result to 16 significant
digits before the next operation ever sees it, so three separate roundings
compound instead of one rounding happening once at the end.

**Right**

```java
BigDecimal result = principal
    .multiply(rate)
    .add(fee)
    .divide(periods, MathContext.DECIMAL64);
```

Only the final `divide` — the one operation that can produce a
non-terminating decimal and therefore *needs* a context to avoid
`ArithmeticException` — rounds; `multiply` and `add` on `BigDecimal` are exact
operations with no context needed, so leaving them unrounded costs nothing and
avoids three unnecessary roundings.

**Why people believe it:** passing a `MathContext` to every arithmetic call in
a chain looks like defensive consistency — "always specify precision" reads as
a good habit — without noticing that `multiply` and `add` never needed
rounding in the first place, since they cannot overflow scale the way
division can.

### Independently rounding both portions of a split preserves the total

**Wrong**

```java
BigDecimal stake = new BigDecimal("3.335");
BigDecimal bonus = stake.multiply(new BigDecimal("0.10"))
    .setScale(2, RoundingMode.HALF_UP);
BigDecimal cash = stake.multiply(new BigDecimal("0.90"))
    .setScale(2, RoundingMode.HALF_UP);
```

`stake.multiply(0.10) = 0.3335`, `HALF_UP` to scale 2 gives `0.34`;
`stake.multiply(0.90) = 3.0015`, `HALF_UP` to scale 2 gives `3.00`; the two
sum to `3.34`, one cent more than the `3.335` stake — money created from
independent rounding.

**Right**

```java
BigDecimal bonus = stake.multiply(new BigDecimal("0.10"))
    .setScale(2, RoundingMode.DOWN);
BigDecimal cash = stake.subtract(bonus);
```

`bonus = 0.33` (`DOWN` truncates `0.3335` to `0.33`); `cash = stake − bonus =
3.335 − 0.33 = 3.005`, and `bonus.add(cash).compareTo(stake) == 0` holds
exactly, because `cash` was never independently rounded — it is defined as
whatever makes the total exact.

**Why people believe it:** rounding "the bonus part" and "the cash part" the
same way, by the same rule, looks fair and symmetric; the asymmetry that
actually guarantees correctness — round one side, derive the other by
subtraction — looks, at first glance, like favoritism toward one portion
rather than the only construction that cannot drift.

---

## Cheat sheet

| Thing | Fact (Java 21 LTS) |
|---|---|
| `scale` | Digits after the decimal point |
| `precision` (`MathContext`) | Total significant digits, regardless of point position |
| `MathContext.DECIMAL32` | precision 7, `HALF_EVEN` — IEEE 754-2008 decimal32 |
| `MathContext.DECIMAL64` | precision 16, `HALF_EVEN` — IEEE 754-2008 decimal64 |
| `MathContext.DECIMAL128` | precision 34, `HALF_EVEN` — IEEE 754-2008 decimal128 |
| `MathContext.UNLIMITED` | precision 0 ("no limit"), `HALF_UP` (never fires) |
| `100 ÷ 3` at DECIMAL32 | `33.33333` (7 sig digits) |
| `100 ÷ 3` at DECIMAL64 | `33.33333333333333` (16 sig digits) |
| `100 ÷ 3` at DECIMAL128 | `33.33333333333333333333333333333333` (34 sig digits) |
| Use `MathContext` when | Magnitude of the value is not fixed in advance (rates, intermediates) |
| Use `setScale` when | Value is money with a fixed minor unit, applied at the boundary |
| Chained `MathContext` ops | Round at every step — round once, at the end, instead |
| `new BigDecimal("0.00").equals(BigDecimal.ZERO)` | `false` — scale 2 vs scale 0 |
| `new BigDecimal("0.00").signum()` | `0` — correct, scale-independent |
| `new BigDecimal("0.00").compareTo(BigDecimal.ZERO)` | `0` — correct, does alignment work |
| Cheapest correct zero check | `signum() == 0` |
| `BigDecimal.ZERO.scale()` | `0` |
| `BigDecimal.ONE` | `1` |
| `BigDecimal.TEN` | `10` |
| `BigDecimal.ZERO`'s `intVal` | Non-null cached `BigInteger` zero (§6.7) |
| Compact `BigDecimal` size | 40 bytes measured (§6.11) |
| `long` field size | 8 bytes (no object header of its own) |
| Size ratio, `BigDecimal` vs `long` | 5x |
| `long` cents add | 0.26 ns/op measured (§6.12) |
| `BigDecimal.add` (compact) | 2.24 ns/op measured (§6.12) |
| Speed ratio, add | 8.6x, measured wall-clock, not JMH |
| 19.8M entries/day as `BigDecimal` | 792,000,000 bytes ≈ 792 MB/day |
| 19.8M entries/day as `long` | 158,400,000 bytes ≈ 158 MB/day |
| 2.8M `BigDecimal.add` calls | ≈11 ms measured |
| Equivalent `long` sum | under 1 ms |
| `Long.MAX_VALUE` as scale-2 cents | 92,233,720,368,547,758.07 units |
| Per-client cents total overflow bound | ≈3,038,661 years at 19.8M entries/day avg 4.20 |
| What actually overflows in long-cents code | An intermediate multiply, not a running total |
| Overflow-safe long arithmetic | `Math.multiplyExact`/`addExact`/`subtractExact` |
| minor-units `long` risk | Same type for units and minor units — a 100x error is silent |
| `Money` fixes over bare `BigDecimal` | Currency, normalised scale, cross-currency guard |
| `Money.of` scale source | `currency.getDefaultFractionDigits()`, never a hardcoded 2 |
| `Money.equals` | `compareTo`-based, scale-safe |
| `Money.toString` | `toPlainString()`, never bare `toString()` |
| `StakeSplit` invariant | `cashPortion = stake − bonusPortion` — derived, not separately rounded |
| Canonical split | 3.33 → 0.33 bonus (`DOWN`) + 3.00 cash (remainder) |
| Rounding bonus `HALF_UP` instead | Can create money (e.g. 0.34 + 3.00 = 3.34) |
| Record identity for `Money` | Right fit — value equality is exactly what money needs |
| Record identity for a JPA entity | Wrong fit — see guide 08 |

---

## Self-test

**Q1.** What is the difference between `scale` and `precision`, in one sentence each?

<details><summary>Answer</summary>

Scale is the count of digits after the decimal point — `setScale(2,
RoundingMode.HALF_EVEN)` always leaves exactly two digits past the point no
matter how large or small
the number is. Precision is the count of total significant digits — a
`MathContext` with precision 7 keeps seven meaningful digits wherever the
decimal point happens to fall, so the same context produces `33.33333` from
100÷3 and would produce `0.00003333333` from a much smaller division, seven
significant digits either way.

</details>

**Q2.** Why does `MathContext.UNLIMITED` report a rounding mode of `HALF_UP` if that mode can never actually fire?

<details><summary>Answer</summary>

`UNLIMITED` has precision 0, which by the `MathContext`/Javadoc convention
means "no limit" — no rounding is ever performed under this context, so no
rounding mode is ever consulted. But the `MathContext(int precision,
RoundingMode mode)` constructor requires some `RoundingMode` value to be
supplied; `HALF_UP` was chosen as that placeholder. It's not a meaningful
default, it's a constructor requirement satisfied with an inert value.

</details>

**Q3.** Why do `DECIMAL32`, `DECIMAL64` and `DECIMAL128` have precisions 7, 16 and 34 instead of round numbers like 5, 10 and 20?

<details><summary>Answer</summary>

Those three numbers are not arbitrary — they are the significand digit counts
fixed by the IEEE 754-2008 decimal interchange formats decimal32, decimal64
and decimal128. Java's `MathContext` constants are named after, and match,
that external standard rather than inventing their own round numbers.

</details>

**Q4.** A colleague writes `if (walletBalance.equals(BigDecimal.ZERO))` to check whether a client's wallet is empty. What's wrong, and what should they write instead?

<details><summary>Answer</summary>

`equals` on `BigDecimal` requires both the unscaled value and the scale to
match. `BigDecimal.ZERO` has scale 0, but `walletBalance` almost certainly
came out of a computation ending in `setScale(2, RoundingMode.DOWN)`, so it's scale 2 and
prints as `0.00`. `new BigDecimal("0.00").equals(BigDecimal.ZERO)` measures as
`false`, so the check silently never fires for an actually-empty wallet. The
fix is `walletBalance.signum() == 0`, which reads the sign directly and is
correct and cheap regardless of scale; `compareTo(BigDecimal.ZERO) == 0` also
works but does unnecessary scale-alignment work to get there.

</details>

**Q5.** Why does `StakeSplit.of` compute the cash portion as `stake.subtract(bonusPortion)` instead of computing it independently as `stake.multiply(0.90)` and rounding that?

<details><summary>Answer</summary>

Rounding each portion independently can produce two roundings that don't sum
back to the original stake — for example a stake of 3.335 splits under
independent `HALF_UP` rounding into a 0.34 bonus and a 3.00 cash portion,
totalling 3.34, one cent more than the stake. Deriving cash as the exact
remainder after the bonus is rounded guarantees, by construction, that
`bonus + cash == stake` always — there's no arithmetic path left that could
create or destroy money, because the second portion was never independently
rounded in the first place.

</details>

**Q6.** What's the measured memory and speed cost of using `BigDecimal` for a per-entry ledger amount instead of a `long` in minor units, and at what daily volume does that matter?

<details><summary>Answer</summary>

Measured on JDK 21.0.7: a compact `BigDecimal` instance is 40 bytes against 8
bytes for a `long` field — a 5x difference — and a `BigDecimal.add` runs at
2.24 ns/op against 0.26 ns/op for a `long` add, an 8.6x difference (wall-clock
loop timings, not JMH, so treat the ratio as directional). At QuizStakes'
19.8M ledger entries/day, that's the difference between roughly 792 MB/day and
158 MB/day of allocation, and between about 11 ms and under 1 ms to sum 2.8M
stake-reservation amounts. It matters specifically in a measured hot path at
that volume; it does not by itself justify abandoning `BigDecimal` in the
ledger of record, where the self-describing scale and exactness are worth the
cost.

</details>

**Q7.** If a per-client running total in minor-units `long` cents realistically can't overflow for millions of years, why does long-cents arithmetic still need `Math.multiplyExact`?

<details><summary>Answer</summary>

The running-total bound is reassuring only for accumulation by repeated
addition — at 19.8M entries/day averaging 420 cents, `Long.MAX_VALUE` cents
(about 92.2 quadrillion units) would take roughly 3 million years to reach by
summing. But a single intermediate *multiplication* — say a balance times a
percentage expressed as an integer numerator — can overflow `Long.MAX_VALUE`
in one step, far below any running total, and a plain `*` wraps around
silently instead of throwing. `Math.multiplyExact` (and the `addExact`/
`subtractExact` family) throws `ArithmeticException` on overflow instead of
producing a silently wrong, wrapped value.

</details>

**Q8.** Why is `BigDecimal amount` alone not sufficient as a money type, even once you've solved the equals/scale trap?

<details><summary>Answer</summary>

`BigDecimal` carries a number, exactly, and nothing else. It has no currency,
so `cashAvailable.add(bonusAvailable)` compiles and runs even if the two
amounts happen to be in different currencies — there's no type-level guard.
It also has no fixed scale invariant of its own — nothing stops a scale-4
value from being assigned into a field every other part of the system assumes
is scale 2. A `Money` type that pairs the amount with a `Currency`, normalises
the scale from that currency's own minor-unit count, and rejects
cross-currency arithmetic at the one point where two `Money` values actually
meet closes all three gaps that `BigDecimal` alone leaves open.

</details>

**Q9.** Why is a record the right choice for `Money` but the wrong choice for a JPA-managed entity like `Client`?

<details><summary>Answer</summary>

A record's identity is entirely its component values — two `Money(3.33, GBP)`
instances, however constructed, are equal and interchangeable, which is
exactly the semantics money needs: 3.33 GBP is 3.33 GBP no matter how it was
computed. A JPA entity's identity is its database-assigned primary key, not
its field values — two `Client` rows with identical name, address and status
but different primary keys are still two distinct clients, and a
record-style value-based `equals` would incorrectly treat them as the same
entity (and cause problems the moment fields change after the key is
assigned, since a record's hash and equality are tied to its full component
state).

</details>

---

## Open questions

None. Every numeric claim in this file traces to §6.7, §6.8, §6.11 or §6.12 of
the measured brief, or to the `MathContext`/`BigDecimal` Javadoc and the IEEE
754-2008 decimal interchange format naming cited inline.

---

**Leaves covered:** 2.4.16–2.4.19 (4 leaves)
**Leaves deferred:** none
**Diagrams included:** none
**Target version:** Java 21 LTS
**Lines:** 880
