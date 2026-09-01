# 03 Java Core — Compensated summation, narrowing, and where floating point fits — INTERNALS (§3.15, 3.15.12–3.15.14)

**Target version: Java 21 LTS.** | **Part 3 of 5** | [Index](../00-index.md)
Previous: [strictfp, StrictMath and Math.fma](04b-internals-strictfp-strictmath-and-fma.md) · Next: [Date and time](../date-and-time/02-date-and-time.md)

This file closes the floating-point row: why `DoubleStream.sum()` gives a
different, more accurate answer than a naive accumulation loop over the exact
same numbers; why widening a `float` to a `double` never loses information
while the reverse always risks it; and, having spent four files on binary
floating point's mechanics, the closing judgement on when it is the right
tool at all. The question this file answers: **what does the JDK actually do
differently when you call `.sum()` instead of writing the loop yourself, and
where does that leave the boundary between `double` and `BigDecimal`?**

Measured on Oracle JDK 21.0.7 (build 21.0.7+8-LTS-245), macOS aarch64 (Apple
Silicon).

---

## 1. Compensated summation (3.15.12)

A running total accumulated one small addend at a time drifts further from
the true sum the longer the loop runs — not because addition is broken, but
because the accumulator itself is growing while the addends stay the same
size, and once the accumulator's ulp exceeds an addend's magnitude, that
addend's low-order bits are simply gone.

### Why it exists

Picture summing 2.8 million stake reservations of 4.20 into a running
`double` total. Once the total passes roughly 1.176E7, `Math.ulp` at that
magnitude is about 1.86E-9 — still tiny, but every addition from here on
rounds the exact mathematical sum to the nearest multiple of that ulp, and
those roundings do not cancel on average; they accumulate a directional
drift. Over millions of additions the drift becomes measurable money-sized
error, not noise.

### How it works

`[PROVE]` with the measurements from §6.5. Summing `0.1` a hundred thousand
times:

```
naive loop                  = 10000.000000018848   (error +1.8848368199542165E-8)
Arrays.stream(values).sum()    = 10000.0               (error 0.0)
Kahan summation, by hand    = 10000.0
```

3,100 additions of 42.42 (a day of bonus grants at the average value):

```
naive double  = 131501.99999999543
exact         = BigDecimal("42.42").multiply(BigDecimal("3100")) = 131502.00
```

2,800,000 additions of 4.20 (a day of stake reservations):

```
naive double = 1.1759999999664538E7   (error -0.00033546239137649536)
exact        = 11760000.00
```

The naive loop's error grows with the count and the accumulator's magnitude;
the stream's `.sum()` and the hand-written Kahan loop both land on the exact
answer for the `0.1` case, and dramatically closer for the larger runs. That
is not because streams are magic — `DoubleStream.sum()` runs a genuinely
different algorithm, called compensated (Kahan-Babuska) summation, which
tracks the rounding error from each addition and feeds it back into the next
one instead of discarding it.

The verbatim JDK 21 `DoublePipeline.sum()`, `java.util.stream`:

```java
public final double sum() {
    /*
     * In the arrays allocated for the collect operation, index 0
     * holds the high-order bits of the running sum, index 1 holds
     * the negated low-order bits of the sum computed via compensated
     * summation, and index 2 holds the simple sum used to compute
     * the proper result if the stream contains infinite values of
     * the same sign.
     */
    double[] summation = collect(() -> new double[3],
                           (ll, d) -> {
                               Collectors.sumWithCompensation(ll, d);
                               ll[2] += d;
                           },
                           (ll, rr) -> {
                               Collectors.sumWithCompensation(ll, rr[0]);
                               // Subtract compensation bits
                               Collectors.sumWithCompensation(ll, -rr[1]);
                               ll[2] += rr[2];
                           });

    return Collectors.computeFinalSum(summation);
}
```

`summation` is a three-element `double[]` accumulator, not a single running
total. Index 0 is the high-order running sum — the value you would get from
a naive loop at any given point. Index 1 is the **negated** low-order
compensation — the rounding error the last addition threw away, stored with
its sign flipped so it can be *subtracted back in* on the next step rather
than added, which the collector's own comment marks. Index 2 is a plain,
uncompensated simple sum, kept only as a fallback for the one case
compensation cannot handle: summing same-signed infinities (below).

The verbatim `Collectors.sumWithCompensation`:

```java
static double[] sumWithCompensation(double[] intermediateSum, double value) {
    double tmp = value - intermediateSum[1];
    double sum = intermediateSum[0];
    double velvel = sum + tmp; // Little wolf of rounding error
    intermediateSum[1] = (velvel - sum) - tmp;
    intermediateSum[0] = velvel;
    return intermediateSum;
}
```

Walked line by line: `tmp = value - intermediateSum[1]` applies the
compensation carried from the previous step — subtracting the negated
compensation is adding back the error that was lost last time, correcting
`value` before it is added. `sum = intermediateSum[0]` reads the current
running total. `velvel = sum + tmp` performs the actual lossy addition — this
is the one line that can lose bits, and its comment names the phenomenon
directly ("little wolf of rounding error," a play on the algorithm's German
etymological roots). `intermediateSum[1] = (velvel - sum) - tmp` is the trick
that recovers exactly what was lost: `velvel - sum` mathematically should
equal `tmp` exactly, but because `velvel` was rounded, it usually does not —
the difference `(velvel - sum) - tmp` is precisely the rounding error the
addition just introduced, computed using ordinary `double` arithmetic on
already-rounded values (this recovery trick is itself exact under IEEE 754
addition semantics). That recovered error is stored back at index 1, negated,
ready to be subtracted back in on the next call. `intermediateSum[0] = velvel`
commits the new running total.

The verbatim `Collectors.computeFinalSum`:

```java
static double computeFinalSum(double[] summands) {
    // Final sum with better error bounds subtract second summand as it is negated
    double tmp = summands[0] - summands[1];
    double simpleSum = summands[summands.length - 1];
    if (Double.isNaN(tmp) && Double.isInfinite(simpleSum))
        return simpleSum;
    else
        return tmp;
}
```

`tmp = summands[0] - summands[1]` applies one final round of compensation to
the running total. The `NaN`-and-infinite special case explains why index 2
exists at all: if the stream summed several same-signed infinities, the
compensation arithmetic at some point computes `infinity - infinity`, which
is `NaN` (per `04`'s arithmetic rules) even though the *actual* mathematically
correct sum is clearly that same infinity, not `NaN`. In that specific case
the plain uncompensated simple sum at index 2 is consulted instead and
returned, correctly signed, rather than propagating the spurious `NaN`.

The parallel-merge branch (the second `collect` lambda) merges two partial
`double[3]` accumulators from different stream segments: it feeds in the
other segment's running sum (`rr[0]`) and then subtracts its compensation
(`-rr[1]`, again negated for the same reason as above) so the merge itself
does not lose the accuracy already banked in each half.

`[X-REF 04]` `DoubleStream.sum()` is therefore **not** a rewrite of your loop
into stream syntax — it is a genuinely different algorithm that produces a
genuinely different (and more accurate) result, and the same is true of
`Collectors.summingDouble` and `DoubleSummaryStatistics`, which are built on
the identical compensation mechanism. By contrast, `reduce(0.0, Double::sum)`
performs the plain, uncompensated addition at every step — it is the naive
algorithm expressed via `reduce`, and it reproduces the naive loop's error
exactly. So replacing a hand-written summation loop with `stream().sum()`
can silently change the numeric output — worth knowing before anyone calls
that swap "a pure refactor with no behavior change." Guide 04 (lambdas,
streams, Optional, records) is where the general stream-terminal-operation
material lives; this paragraph is the self-contained floating-point-specific
mechanism behind one of its terminal operations.

The honest limit: compensated summation buys roughly double the effective
working precision — it is dramatically better than the naive loop, not
exact. For actual money, the answer is still `BigDecimal` or minor-units
`long`, exactly because those represent the underlying decimal values
exactly rather than reducing (without eliminating) accumulated binary
rounding error; see
[`02c-mathcontext-constants-and-minor-units.md`](02c-mathcontext-constants-and-minor-units.md).

**Insight:** the "little wolf of rounding error" comment names the real
mechanism precisely — every `double` addition loses a small, deterministic
amount of information, and compensated summation's entire trick is computing
exactly how much was lost (using the same lossy arithmetic, cleverly
arranged) and feeding it back in rather than discarding it.

**Pitfall:** the wrong belief is that switching a summation loop to
`stream().sum()` is purely a style change with identical output. The
symptom: a numeric regression test that compares a refactored stream-based
total against a previously-recorded loop-based total and fails on a tiny
difference that looks like a flaky test, when it is in fact both
implementations working correctly — just implementing different algorithms.
The fix: know that `sum()`/`summingDouble`/`DoubleSummaryStatistics` are
compensated and `reduce(0.0, Double::sum)` is not, and pick the comparison
baseline accordingly (or use `BigDecimal` for the reference value so the
question of which `double` algorithm is "right" doesn't arise).

> `DoubleStream.sum()` runs compensated (Kahan-Babuska) summation, carrying
> the previous addition's rounding error forward and subtracting it back in
> on the next step, which is why it measurably beats a naive accumulation
> loop over the same values — while still not being exact, which is why money
> still belongs in `BigDecimal`.

## 2. Widening is exact, narrowing is not (3.15.13)

`float` to `double` never has to think about what to do with information it
cannot fit. `double` to `float` always might have to throw information away.

### Why it exists

The two IEEE formats are not scaled copies of each other with room to spare
in only one direction by luck — binary32 (`float`) has 8 exponent bits and 23
mantissa bits; binary64 (`double`) has 11 and 52. Every one of binary32's
possible exponent and mantissa values fits inside binary64's wider fields
with room to spare in both, so there is structurally no value a `float` can
hold that a `double` cannot represent exactly. Going the other direction,
binary64 can represent both far larger magnitudes (more exponent bits) and
far finer precision (more mantissa bits) than binary32 has room for, so
either dimension can force information loss.

### How it works

`[PROVE]` the widening claim from the field widths alone, not from an
example: any `float` value's exponent (at most 8 bits of range) fits inside
`double`'s 11-bit exponent field with room to spare, and any `float` value's
23-bit mantissa fits inside `double`'s 52-bit mantissa field padded with
trailing zero bits. There is no rounding decision to make — the conversion is
exact by construction, every time, for every representable `float` value.
JLS 5.1.2 lists `float` -> `double` as a widening primitive conversion that
never loses information, on exactly this basis.

The consequence that surprises people, measured in §6.4:

```
(double) 0.1f                = 0.10000000149011612
new BigDecimal((double)0.1f) = 0.100000001490116119384765625
```

Widening did not *introduce* that error — it *exposed* an error the `float`
had already been carrying the whole time, because `0.1f` itself was never
exactly one tenth (23 mantissa bits truncate the same recurring binary
fraction `04` derived for `double`, just more aggressively). `Float.toString`
was hiding that error by applying the identical shortest-round-trip
contract `04a` described for `double`, printing `"0.1"` for the `float` —
which is precisely why the widened `double` value looks alarming even though
nothing new went wrong at the widening step itself.

Narrowing, measured, §6.4:

```
(float) 0.1d       = 0.1          (a genuinely different stored value, printed
                                    by the same shortest-round-trip rule --
                                    the loss is invisible at a glance)
(float) 1e40       = Infinity     (magnitude overflow: exceeds float's MAX_VALUE)
(float) 1e-50      = 0.0          (magnitude underflow: below float's smallest subnormal)
(float) 16777217   = 1.6777216E7
(int)(float) 16777217 = 16777216
```

`(float) 16777217` is the sharpest example: `2^24 + 1 = 16777217` is the
first `int` value a `float`'s 23+1 = 24 effective significand bits cannot
represent exactly (contrast `double`'s exact-integer bound of `2^53`,
established in `04`), so it rounds to the nearest representable `float`,
`16777216` (`2^24`), and converting that back to `int` silently loses the 1.

The ulp comparison, §6.3, quantifies just how much coarser `float` is:

```
Math.ulp(1.0f) = 1.1920929E-7
Math.ulp(1.0)  = 2.220446049250313E-16
```

`float`'s spacing at 1.0 is about nine orders of magnitude coarser than
`double`'s.

```java
record StakeAmountF(float value) {
    // Narrowing double -> float can both lose precision AND lose magnitude
    // (overflow to Infinity, underflow to 0.0) -- JLS 5.1.3 lists both risks.
    static StakeAmountF fromDouble(double amount) {
        return new StakeAmountF((float) amount);
    }
}
```

JLS 5.1.2 lists `float` -> `double` as a widening primitive conversion that
never loses information; JLS 5.1.3 lists `double` -> `float` as a narrowing
primitive conversion that may lose both precision and magnitude. Cross
reference [`../primitives-and-conversions/03-conversions-and-contexts.md`](../primitives-and-conversions/03-conversions-and-contexts.md)
for the full conversion-context rules and
[`../primitives-and-conversions/03a-promotion-boxing-and-inference.md`](../primitives-and-conversions/03a-promotion-boxing-and-inference.md)
(which owns diagram D-020) for binary numeric promotion — neither diagram is
re-embedded here.

**Pitfall:** the wrong belief is that a `float` value printed as `"0.1"` and
then widened to `double` somehow "becomes" less accurate during the widening
step. The symptom is debugging effort spent on the widening conversion itself
when the actual imprecision was baked in the moment the `float` literal
`0.1f` was parsed. The fix: widening is exact by construction (JLS 5.1.2) —
if a widened value looks wrong, the error was already present in the
narrower source value; inspect that value with `Float.toHexString` rather
than suspecting the conversion.

**Interview:** "is `float` to `double` conversion always safe" — yes, exactly,
by JLS 5.1.2, because binary64's exponent and mantissa fields are strict
supersets of binary32's; the reverse direction (JLS 5.1.3) can lose precision,
overflow to infinity, or underflow to zero.

> `float` -> `double` widening is exact because binary64's exponent and
> mantissa fields structurally contain every value binary32's fields can
> express; `double` -> `float` narrowing can lose precision, overflow to
> `Infinity`, or underflow to `0.0f`, because the reverse containment does
> not hold.

## 3. Where floating point fits (3.15.14)

Four files have derived the mechanics. This closes with the judgement call
they all point toward.

| Domain | Deciding property | Right tool |
|---|---|---|
| Physics, simulation | relative error is the meaningful measure; inputs already approximate; dynamic range enormous | `double` |
| Statistics, ML | same, plus `float` often deliberate — halves memory, feeds SIMD | `float` or `double` |
| Money | values are exact decimals by definition; every cent must reconcile | `BigDecimal` or minor-units `long` |
| Counters, quantities | integers; must never silently lose a unit | `long` (never silently loses a unit above `2^53` the way `double` does) |
| Identifiers | never arithmetic at all | `UUID` (wrapped as `RoundId`/`ClientId`/etc.) or `String` |

The decisive test fits in one sentence: **is the value a measurement or a
count?** A measurement already carries some inherent error (a sensor reading,
a probability estimate, a latency sample), and floating point adds a bounded,
well-understood relative error on top of that — an acceptable trade for the
dynamic range and speed it buys. A count is exact by definition — there is no
"approximately 42 cents" — and floating point's bounded relative error
*destroys* that exactness rather than merely adding to pre-existing
imprecision.

The QuizStakes application of that test: a `Money` amount is a count of minor
units (cents), never a `double` — the ledger's entire correctness rests on
exact reconciliation, and `03`/`03a`/`03b` cover why `BigDecimal` (or
minor-units `long` under the bound derived in `03b`) is the answer. A p99
settlement latency figure is a measurement — `double` is fine, and the
compensated-summation concerns from concept 1 are the only caveat worth
tracking if many such measurements get summed. A client `Position` balance is
a count, same as `Money`. An affordability score or a risk-model coefficient
is a measurement, same as the latency figure.

This row's four files established two escape hatches for the cases that
sit at the boundary: compensated summation (concept 1) when a `double`
accumulation genuinely must happen and the naive loop's drift is
unacceptable, and `BigDecimal` (with its own minor-units-`long` fallback)
when the value must never be approximate at all. Neither is a substitute for
the other — see
[`02c-mathcontext-constants-and-minor-units.md`](02c-mathcontext-constants-and-minor-units.md)
for the `BigDecimal`/minor-units decision in full, and
[`../cost-model/02-master-cost-table.md`](../cost-model/02-master-cost-table.md)
for where the measured per-operation costs of each choice land side by side.

No gotcha beyond the decisive test already stated: once "measurement or
count" is answered honestly for a given field, the type choice follows
mechanically.

**Interview:** "when is `double` acceptable and when is it not" — acceptable
for measurements that already carry inherent error and benefit from `double`'s
dynamic range and speed; never acceptable for exact counts like money, where
the value is defined to be exact and floating point's bounded relative error
destroys that guarantee rather than merely padding an existing one.

> The choice between `double` and an exact type turns on one question — is
> the value a measurement, which already tolerates bounded error, or a count,
> which is defined to be exact — and money, being a count, is never a
> `double`.

---

## Pitfalls

### "Switching a summation loop to `.sum()` is a pure refactor"

**Wrong**

```java
double naiveTotal = 0.0;
for (double stake : stakeAmounts) {
    naiveTotal += stake;
}
// "let's clean this up with a stream, same result, just nicer syntax"
double streamTotal = Arrays.stream(stakeAmounts).sum();
assert naiveTotal == streamTotal; // fails for large arrays
```

Measured in §6.5, summing 2,800,000 copies of `4.20`: the naive loop gives
`1.1759999999664538E7`, `Arrays.stream(values).sum()` gives the exact
`11760000.00`-equivalent value — they are not the same `double`.

**Right**

```java
// Know which algorithm you're comparing against before asserting equality.
double exact = new BigDecimal("4.20").multiply(BigDecimal.valueOf(count)).doubleValue();
assertThat(streamTotal).isCloseTo(exact, within(1e-6));
```

Compare against an exact reference value (or an explicit tolerance) rather
than asserting bit-for-bit equality between two different summation
algorithms.

**Why people believe it:** a stream terminal operation and a hand-written
loop look like two syntaxes for the same computation, and for small inputs
the difference is too small to notice.

### "float to double widening can introduce new rounding error"

**Wrong**

```java
float storedRate = 0.1f;
double widened = storedRate; // "the widening step probably rounds a bit"
System.out.println(widened); // 0.10000000149011612 -- "the widening broke it!"
```

The widening step is exact by construction (JLS 5.1.2) — it introduced
nothing. The imprecision was already present in `storedRate` and was simply
hidden by `Float.toString`'s shortest-round-trip printing of it as `"0.1"`.

**Right**

```java
float storedRate = 0.1f;
System.out.println(Float.toHexString(storedRate)); // inspect the float itself first
double widened = storedRate; // exact widening, per JLS 5.1.2
```

Diagnose the value at its narrower source before suspecting the widening
conversion.

**Why people believe it:** the printed `double` value looks "worse" than the
printed `float` value, which reads as the conversion having damaged
something, when actually it simply stopped hiding what was already there.

### "money summed with double is fine as long as you're careful with rounding"

**Wrong**

```java
double dailyStakeTotal = 0.0;
for (Stake s : todaysStakes) {
    dailyStakeTotal += s.amount(); // "careful" double accumulation
}
// reconciled against the ledger's BigDecimal total at end of day
```

Measured in §6.12: over one day's 2,800,000 stake reservations, the naive
`double` total is off by −0.00033546 against the exact `BigDecimal` total —
small in isolation, but a nonzero reconciliation discrepancy that a
regulated ledger cannot simply write off.

**Right**

```java
BigDecimal dailyStakeTotal = BigDecimal.ZERO;
for (Stake s : todaysStakes) {
    dailyStakeTotal = dailyStakeTotal.add(s.amount());
}
```

`BigDecimal` addition is exact for exact decimal inputs — there is no
accumulation drift to reconcile away, at the measured cost of roughly 8.6x a
`long` add (`03b`).

**Why people believe it:** "careful" summation (compensated, or even just a
smaller loop) genuinely reduces the error, and it is easy to conflate
"much smaller error" with "no error," especially before a reconciliation
process surfaces the discrepancy.

---

## Cheat sheet

| Thing | Fact (Java 21 LTS) |
|---|---|
| Naive sum of 100,000 x 0.1 | 10000.000000018848 (error +1.8848E-8) |
| `Arrays.stream(values).sum()` of same | 10000.0 (exact) |
| Naive sum of 2.8M x 4.20 | 1.1759999999664538E7 (error −0.00033546) |
| `DoubleStream.sum()` algorithm | compensated (Kahan-Babuska) summation |
| Accumulator shape | `double[3]`: [0] running sum, [1] negated compensation, [2] simple sum |
| `Collectors.sumWithCompensation` role | carries forward and reapplies previous rounding loss |
| Why index 2 (simple sum) exists | rescues same-signed-infinity sums from spurious `NaN` |
| `reduce(0.0, Double::sum)` | naive algorithm — no compensation |
| `Collectors.summingDouble` / `DoubleSummaryStatistics` | also compensated |
| Compensated summation exactness | ~2x effective precision, not exact |
| `float` -> `double` | widening, always exact (JLS 5.1.2) |
| `double` -> `float` | narrowing, may lose precision and/or magnitude (JLS 5.1.3) |
| `(double) 0.1f` | 0.10000000149011612 |
| `(float) 0.1d` | 0.1 (printed; different stored value than `0.1f`) |
| `(float) 1e40` | `Infinity` (overflow) |
| `(float) 1e-50` | `0.0` (underflow) |
| First `int` a `float` can't represent | `16777217` (`2^24 + 1`) |
| `(float) 16777217` then `(int)` | `16777216` — loses the 1 |
| `Math.ulp(1.0f)` | 1.1920929E-7 |
| `Math.ulp(1.0)` (double) | 2.220446049250313E-16 |
| `float` vs `double` spacing at 1.0 | ~9 orders of magnitude coarser |
| Decisive type-choice test | measurement (tolerates error) vs. count (must be exact) |
| Money type | `BigDecimal` or minor-units `long`, never `double` |
| Counters/quantities type | `long` |
| Identifiers | `UUID`-wrapped value types or `String`, never numeric |

---

## Self-test

**Q1.** Why does `Arrays.stream(doubles).sum()` give a different, more
accurate result than a hand-written accumulation loop over the same array?

<details><summary>Answer</summary>

`DoubleStream.sum()` runs compensated (Kahan-Babuska) summation instead of a
plain running total. It tracks the rounding error lost on each addition in a
second accumulator, negated, and feeds it back into the next addition,
recovering most of what a naive loop would silently discard. Measured over
100,000 additions of 0.1, the naive loop is off by +1.8848E-8 while the
stream's sum lands on the exact answer.

</details>

**Q2.** What do the three slots of the `double[3]` accumulator inside
`DoublePipeline.sum()` each hold?

<details><summary>Answer</summary>

Index 0 holds the high-order running sum — the ordinary accumulated total.
Index 1 holds the negated low-order compensation — the rounding error lost
on the previous addition, stored with its sign flipped so it can be
subtracted back in (equivalently, added back) on the next step. Index 2
holds a plain, uncompensated simple sum, kept only as a fallback to recover
the correct signed infinity if the stream sums same-signed infinities, since
the compensation arithmetic would otherwise produce a spurious NaN from an
implicit infinity-minus-infinity.

</details>

**Q3.** Does `reduce(0.0, Double::sum)` get the same compensation benefit as
`.sum()`?

<details><summary>Answer</summary>

No. `reduce(0.0, Double::sum)` performs plain, uncompensated addition at
every step — it is the naive algorithm expressed through `reduce`, and it
reproduces the naive loop's accumulated error exactly. Only `.sum()`,
`Collectors.summingDouble`, and `DoubleSummaryStatistics` use compensated
summation.

</details>

**Q4.** Why is `float` to `double` widening always exact, while `double` to
`float` narrowing is not?

<details><summary>Answer</summary>

binary32 (`float`) has 8 exponent bits and 23 mantissa bits; binary64
(`double`) has 11 and 52 — every field binary32 uses fits inside binary64's
wider fields with room to spare, so there is no value a `float` holds that a
`double` cannot represent exactly, making the conversion lossless by
construction (JLS 5.1.2). Going the other direction, `double` can represent
larger magnitudes and finer precision than `float` has room for, so
narrowing can lose precision, overflow to `Infinity`, or underflow to
`0.0f` (JLS 5.1.3).

</details>

**Q5.** What is `16777217` significant for in the context of `float`
narrowing, and what happens when it round-trips through one?

<details><summary>Answer</summary>

`16777217` is `2^24 + 1`, the first `int` value a `float`'s effective 24-bit
significand (23 stored mantissa bits plus the implicit leading bit) cannot
represent exactly. `(float) 16777217` rounds to the nearest representable
float, `16777216` (`2^24`), and converting that back with `(int)` yields
`16777216` — the round trip silently loses the `+1`.

</details>

**Q6.** What single question decides whether a value should be a `double` or
an exact type like `BigDecimal`/`long`?

<details><summary>Answer</summary>

Whether the value is a measurement or a count. A measurement (a sensor
reading, a latency sample, a probability estimate) already carries inherent
error, and floating point's bounded relative error is an acceptable further
approximation on top of that — `double` is appropriate. A count (money,
inventory, a position balance) is exact by definition, and floating point's
bounded relative error destroys that exactness rather than adding to
existing imprecision — an exact type like `BigDecimal` or a minor-units
`long` is required instead.

</details>

---

## Open questions

None.

---

**Leaves covered:** 3.15.12–3.15.14 (3 leaves)
**Leaves deferred:** none
**Diagrams included:** none
**Target version:** Java 21 LTS
**Lines:** 619
