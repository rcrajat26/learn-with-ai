# 03 Java Core — Value-object builds — the rounding-bias experiment over 1,000,000 roundings — BUILD IT (§4.7, 4.7.3)

**Target version: Java 21 LTS.** | **Part 4 of 5** | [Index](../00-index.md)
Previous: [The allocation and precision comparison](04c-allocation-and-rounding-bias.md) · Next: [The two escape bugs, and a List component three ways](04a-defensive-copying-and-collections.md)

---

`HALF_UP` and `HALF_EVEN` differ on exactly one input class — a value sitting precisely halfway
between two representable results — so an experiment comparing them measures how often your
operation produces one, and nothing else. Get that wrong and the experiment is worthless: over a
million uniformly random scale-8 amounts the two modes disagreed **once**, measured below, which is
a true fact about random data and a useless one about money.

Over the operation QuizStakes actually performs — 10% of a two-decimal stake — a tie fires **one
time in ten**, and over a million ties `HALF_UP` drifts **+5,000.00** where `HALF_EVEN` drifts
**+0.88**. Scaled to 2.8M stake reservations a day the choice of mode is worth **13,993.56 a day**
of withdrawable cash the house never received. Every one of those figures is measured on this page.

And then the judgement, which is what the leaf is really for: QuizStakes' bonus rule is neither
mode. It is `DOWN`, because rounding a bonus up creates money. The numerical argument does not pick
the mode — it prices each option so that somebody else can.

[The allocation and precision comparison](04c-allocation-and-rounding-bias.md) owns the two `Money`
representations, their allocation cost, and where each is exact; this file assumes them. The
section-wide diff of these value objects against what a plain `record` gives you for free lives in
[the §4.7 diff](04d-value-object-diff.md), leaf 4.7.8.

This harness is not JMH, and does not need to be: the drift figures are exact `BigDecimal` sums, not
measurements of the machine. [The master cost table](../cost-model/02-master-cost-table.md) owns the
canonical timing harness and is equally explicit that it is not JMH either; guide 06 owns JMH.
Everything below was compiled and run on **Oracle JDK 21.0.7 (build 21.0.7+8-LTS-245), macOS
aarch64**.

## The experiment

### Get the design right, because the obvious design proves nothing

`HALF_UP` and `HALF_EVEN` differ on **exactly one input class**: a value sitting precisely halfway
between two representable results. On everything else both round to the nearest neighbour and agree.
So the experiment's entire signal is how often an exact half occurs — a property of the *operation*,
not of the modes.

| Regime | Probability of an exact half at scale 2 | What a bias experiment there measures |
|---|---|---|
| Full-precision random amounts, scale 8 | the last six digits must be `500000`: 1 in 1,000,000 | nothing; the modes look identical |
| Realistic stakes: 10% of a 2-decimal amount | the exact bonus's third decimal equals the stake's last minor digit, so 1 in **10** | the real exposure |
| Engineered halves: stakes ending in 5 minor units | 1 in 1 | isolates what the modes actually do |

The middle row is the one that is easy to get wrong. Taking 10% of a two-decimal amount produces a
three-decimal exact result whose third digit is the stake's last minor digit, so a half fires
whenever the stake ends in 5 pence — **one stake in ten**, not one in a million. The widely repeated
claim that random data almost never hits a half is true for the top row and false for the row
QuizStakes lives in. All three are run below.

### The expectations, derived before the run

Let a stake be `10t + 5` minor units, so the exact bonus is `t + 0.5` minor units — always a tie.
Drift is the cumulative signed `rounded − exact`.

- **`HALF_UP`** rounds a tie away from zero, and every value here is positive, so every rounding
  gains `+0.5` minor units. Over 1,000,000: **+500,000 minor units = +5,000.00**, with no variance,
  because this is arithmetic rather than sampling.
- **`DOWN`** truncates toward zero, losing `−0.5` every time: **−500,000 minor units = −5,000.00**.
- **`HALF_EVEN`** takes the even neighbour, which for `t + 0.5` is `t` when `t` is even and `t + 1`
  when `t` is odd: `−0.5` half the time, `+0.5` the rest. With `t` uniform, expected drift **0**,
  with a random-walk residual of order `0.5 × sqrt(1,000,000)` = ±500 minor units. The prediction is
  "near zero", not "zero".
- **`HALF_UP != HALF_EVEN`** exactly when `t` is even: **≈500,000**. **`HALF_UP != DOWN`** on every
  tie: **1,000,000**.

For the realistic run one stake in ten is a tie, so the tie-driven part scales by 0.1: `HALF_UP`
drift ≈ **+50,000 minor units**, `HALF_EVEN` ≈ 0, disagreements ≈ 50,000. Non-tie roundings cancel
symmetrically — third decimals 1–4 round down by 0.1–0.4, 6–9 round up by 0.4–0.1. `DOWN` is the
exception: it loses on *every* non-zero third decimal, so its drift should be about
`−0.45 × 1,000,000 = −450,000` minor units.

### The harness, complete

All drift accounting is in `BigDecimal`, because an experiment about rounding error that accumulated
its own results in `double` would be measuring itself. All three runs share one loop, differing only
in the amount supplier.

```java
import java.math.BigDecimal;
import java.math.RoundingMode;
import java.util.Random;
import java.util.function.Supplier;

public final class RoundingBiasHarness {

    static final int ROUNDINGS = 1_000_000;
    static final long SEED = 20260829L;
    static final BigDecimal TENTH = new BigDecimal("0.10");
    static final BigDecimal HALF_MINOR_UNIT = new BigDecimal("0.005");

    /** 10% of a stake given in minor units, exact and unrounded. */
    static BigDecimal exactBonus(long stakeMinorUnits) {
        return BigDecimal.valueOf(stakeMinorUnits, 2).multiply(TENTH);
    }

    static String apply(BigDecimal value, RoundingMode mode) {
        try {
            return value.setScale(2, mode).toPlainString();
        } catch (ArithmeticException e) {
            return "throws";
        }
    }

    /** Cumulative signed drift is what reconciliation sees, so that is what this measures. */
    static void drift(String mode, BigDecimal d) {
        System.out.printf("  %-9s drift        %s minor units = %s major units%n", mode,
                d.movePointRight(2).stripTrailingZeros().toPlainString(),
                d.setScale(Math.max(3, d.scale()), RoundingMode.UNNECESSARY).toPlainString());
    }

    static void run(String label, Supplier<BigDecimal> exactBonuses) {
        long halves = 0, diffUpEven = 0, diffUpDown = 0;
        BigDecimal driftUp = BigDecimal.ZERO, driftEven = BigDecimal.ZERO, driftDown = BigDecimal.ZERO;
        for (int i = 0; i < ROUNDINGS; i++) {
            BigDecimal exact = exactBonuses.get();
            BigDecimal up = exact.setScale(2, RoundingMode.HALF_UP);
            BigDecimal even = exact.setScale(2, RoundingMode.HALF_EVEN);
            BigDecimal down = exact.setScale(2, RoundingMode.DOWN);
            if (exact.subtract(down).compareTo(HALF_MINOR_UNIT) == 0) {
                halves++;
            }
            if (up.compareTo(even) != 0) {
                diffUpEven++;
            }
            if (up.compareTo(down) != 0) {
                diffUpDown++;
            }
            driftUp = driftUp.add(up.subtract(exact));
            driftEven = driftEven.add(even.subtract(exact));
            driftDown = driftDown.add(down.subtract(exact));
        }
        System.out.println(label);
        System.out.printf("  exact halves           %,d of %,d (%.4f%%)%n",
                halves, ROUNDINGS, 100.0 * halves / ROUNDINGS);
        drift("HALF_UP", driftUp);
        drift("HALF_EVEN", driftEven);
        drift("DOWN", driftDown);
        System.out.printf("  HALF_UP != HALF_EVEN   %,d roundings%n", diffUpEven);
        System.out.printf("  HALF_UP != DOWN        %,d roundings%n", diffUpDown);
        System.out.println();
    }

    public static void main(String[] args) {
        Random randomA = new Random(SEED);
        run("Run A: 1,000,000 engineered halves; stake = 10t + 5 minor units, t uniform in [10,99]",
                () -> exactBonus(10L * (10 + randomA.nextInt(90)) + 5));

        Random randomB = new Random(SEED);
        run("Run B: 1,000,000 realistic stakes, minor units uniform in [100,999]",
                () -> exactBonus(100L + randomB.nextInt(900)));

        Random randomC = new Random(SEED);
        run("Run C: 1,000,000 scale-8 amounts, uniform in [1.00000000, 9.99999999]",
                () -> BigDecimal.valueOf(100_000_000L + randomC.nextLong(900_000_000L), 8));

        System.out.println("The eight RoundingMode constants, each on five bonus values");
        BigDecimal[] cases = { new BigDecimal("0.335"), new BigDecimal("-0.335"),
                new BigDecimal("0.333"), new BigDecimal("0.337"), new BigDecimal("0.330") };
        System.out.printf("%-12s %8s %8s %8s %8s %8s%n", "mode", "+0.335", "-0.335", "0.333", "0.337", "0.330");
        for (RoundingMode mode : RoundingMode.values()) {
            System.out.printf("%-12s", mode);
            for (BigDecimal c : cases) {
                System.out.printf(" %8s", apply(c, mode));
            }
            System.out.println();
        }

        System.out.println();
        System.out.println("Where HALF_UP and DOWN diverge on a bonus portion");
        for (long minorUnits : new long[] { 333, 335, 345, 420, 425 }) {
            BigDecimal stake = BigDecimal.valueOf(minorUnits, 2);
            BigDecimal exact = exactBonus(minorUnits);
            BigDecimal up = exact.setScale(2, RoundingMode.HALF_UP);
            BigDecimal down = exact.setScale(2, RoundingMode.DOWN);
            System.out.printf("stake %s exact %s | HALF_UP %s + %s | DOWN %s + %s | %s%n",
                    stake.toPlainString(), exact.toPlainString(),
                    up.toPlainString(), stake.subtract(up).toPlainString(),
                    down.toPlainString(), stake.subtract(down).toPlainString(),
                    up.compareTo(down) == 0 ? "same" : "DIVERGE by 0.01 of withdrawable cash");
        }
    }
}
```

```console
$ java RoundingBiasHarness
Run A: 1,000,000 engineered halves; stake = 10t + 5 minor units, t uniform in [10,99]
  exact halves           1,000,000 of 1,000,000 (100.0000%)
  HALF_UP   drift        500000 minor units = 5000.0000 major units
  HALF_EVEN drift        88 minor units = 0.8800 major units
  DOWN      drift        -500000 minor units = -5000.0000 major units
  HALF_UP != HALF_EVEN   499,912 roundings
  HALF_UP != DOWN        1,000,000 roundings

Run B: 1,000,000 realistic stakes, minor units uniform in [100,999]
  exact halves           99,826 of 1,000,000 (9.9826%)
  HALF_UP   drift        49827.6 minor units = 498.2760 major units
  HALF_EVEN drift        -82.4 minor units = -0.8240 major units
  DOWN      drift        -449942.4 minor units = -4499.4240 major units
  HALF_UP != HALF_EVEN   49,910 roundings
  HALF_UP != DOWN        499,770 roundings

Run C: 1,000,000 scale-8 amounts, uniform in [1.00000000, 9.99999999]
  exact halves           2 of 1,000,000 (0.0002%)
  HALF_UP   drift        -22.676089 minor units = -0.22676089 major units
  HALF_EVEN drift        -23.676089 minor units = -0.23676089 major units
  DOWN      drift        -499932.676089 minor units = -4999.32676089 major units
  HALF_UP != HALF_EVEN   1 roundings
  HALF_UP != DOWN        499,910 roundings

The eight RoundingMode constants, each on five bonus values
mode           +0.335   -0.335    0.333    0.337    0.330
UP               0.34    -0.34     0.34     0.34     0.33
DOWN             0.33    -0.33     0.33     0.33     0.33
CEILING          0.34    -0.33     0.34     0.34     0.33
FLOOR            0.33    -0.34     0.33     0.33     0.33
HALF_UP          0.34    -0.34     0.33     0.34     0.33
HALF_DOWN        0.33    -0.33     0.33     0.34     0.33
HALF_EVEN        0.34    -0.34     0.33     0.34     0.33
UNNECESSARY    throws   throws   throws   throws     0.33

Where HALF_UP and DOWN diverge on a bonus portion
stake 3.33 exact 0.3330 | HALF_UP 0.33 + 3.00 | DOWN 0.33 + 3.00 | same
stake 3.35 exact 0.3350 | HALF_UP 0.34 + 3.01 | DOWN 0.33 + 3.02 | DIVERGE by 0.01 of withdrawable cash
stake 3.45 exact 0.3450 | HALF_UP 0.35 + 3.10 | DOWN 0.34 + 3.11 | DIVERGE by 0.01 of withdrawable cash
stake 4.20 exact 0.4200 | HALF_UP 0.42 + 3.78 | DOWN 0.42 + 3.78 | same
stake 4.25 exact 0.4250 | HALF_UP 0.43 + 3.82 | DOWN 0.42 + 3.83 | DIVERGE by 0.01 of withdrawable cash
```

### Prediction against measurement

| Quantity | Predicted | Measured | Verdict |
|---|---|---|---|
| Run A halves | 1,000,000 | 1,000,000 | exact |
| Run A `HALF_UP` / `DOWN` drift | +500,000 / −500,000 minor units | +500,000 / −500,000 | exact |
| Run A `HALF_EVEN` drift | ≈0, within ±500 minor units | +88 (0.8800 major) | inside the band |
| Run A `HALF_UP != HALF_EVEN`, `!= DOWN` | ≈500,000, 1,000,000 | 499,912, 1,000,000 | inside the band |
| Run B halves | ≈100,000 | 99,826 | inside the band |
| Run B `HALF_UP` / `HALF_EVEN` / `DOWN` drift | ≈+50,000 / ≈0 / ≈−450,000 | +49,827.6 / −82.4 / −449,942.4 | all inside the band |
| Run C halves, mode disagreements | ≈1, ≈1 | 2, 1 | inside the band |

Every prediction held, including the one that is interesting *because* it held exactly: Run A's
`HALF_UP` drift is +500,000 with no residual, because a positive tie rounds away from zero every
single time and the drift is `0.5 × n` with zero variance.

The run also checks itself. Run A's 499,912 `HALF_UP`-versus-`HALF_EVEN` disagreements is the count
of even `t`, so odd minus even is `500,088 − 499,912 = 176`, and `176 × 0.5 = 88` minor units — the
`HALF_EVEN` drift, recovered from a different column of the same output.

Run C is the cautionary tale. Over a million roundings of scale-8 amounts `HALF_UP` and `HALF_EVEN`
disagreed **once**, and their cumulative drifts differ by exactly 0.01 — that one disagreement. A
paper concluding the modes are equivalent would be faithfully reporting an experiment that answers a
question nobody asked.

### The eight `RoundingMode` constants

`RoundingMode` is an eight-constant enum, added in Java 5 as the type-safe replacement for
`BigDecimal`'s eight `ROUND_*` `int` constants (still present, deprecated for removal). Four modes
ignore the value's position between neighbours and decide by direction: `UP` away from zero, `DOWN`
toward zero, `CEILING` toward positive infinity, `FLOOR` toward negative infinity. Three round to
the nearest neighbour and differ only on a tie: `HALF_UP` away from zero, `HALF_DOWN` toward zero,
`HALF_EVEN` toward the even neighbour. `UNNECESSARY` asserts no rounding is needed and throws if it
is. [Rounding modes and the API surface](../numbers-and-money/02g-rounding-modes-and-the-api-surface.md)
owns the full API. Every cell below is a printed value from the run above.

| Mode | +0.335 | −0.335 | 0.333 | 0.337 | 0.330 | Throws? | QuizStakes use |
|---|---|---|---|---|---|---|---|
| `UP` | 0.34 | −0.34 | 0.34 | 0.34 | 0.33 | no | never; it inflates every amount |
| `DOWN` | 0.33 | −0.33 | 0.33 | 0.33 | 0.33 | no | **the bonus portion of a stake split** |
| `CEILING` | 0.34 | −0.33 | 0.34 | 0.34 | 0.33 | no | a deposit limit or max-stake ceiling the client must not exceed |
| `FLOOR` | 0.33 | −0.34 | 0.33 | 0.33 | 0.33 | no | a withdrawable-balance display, so the figure never exceeds what is available |
| `HALF_UP` | 0.34 | −0.34 | 0.33 | 0.34 | 0.33 | no | fee or interest presentation where a regulator specifies commercial rounding |
| `HALF_DOWN` | 0.33 | −0.33 | 0.33 | 0.34 | 0.33 | no | nowhere; `HALF_UP`'s mirror with no business meaning here |
| `HALF_EVEN` | 0.34 | −0.34 | 0.33 | 0.34 | 0.33 | no | proportional allocation of a `PaymentRun` fee, where long-run neutrality is the goal |
| `UNNECESSARY` | throws | throws | throws | throws | 0.33 | **yes** | `Money`'s compact constructor, asserting the amount already sits at the currency's scale |

Two things fall out that the prose usually gets wrong. `UP` and `DOWN` are **not** `CEILING` and
`FLOOR` — they agree on positives and disagree on negatives, which is exactly where a clawback
lives. And `HALF_UP` and `HALF_EVEN` produce identical output in all four non-tie columns; the only
column where they *can* differ is the first, and on 0.335 they agree there too, because the even
neighbour happens to be the upward one.

### Where the money appears

The canonical 3.33 case does not show it: 0.333 is not a tie, so both modes give 0.33 bonus and 3.00
cash. The divergence needs a stake ending in 5 pence — 3.35 splits as 0.34 + 3.01 under `HALF_UP`
and 0.33 + 3.02 under `DOWN`, and the printed table shows the same 0.01 on 3.45 and 4.25.

The `StakeSplit` invariant holds in every row — bonus plus cash equals the stake exactly, so nothing
looks wrong in the ledger. The leak is in *which bucket* paid. Bonus is stakeable but never directly
withdrawable; cash is both. Rounding the bonus portion **up** debits 0.01 more from
`CLIENT_BONUS_AVAILABLE` and 0.01 less from `CLIENT_CASH_AVAILABLE`, leaving the client 0.01 more
withdrawable money than a 10% bonus entitles them to — money the house never received, invisible to
the balance check. Price it from Run B's measured drift columns, over 2.8M reservations a day:

- `HALF_UP` against `DOWN`: `49,827.6 − (−449,942.4) = 499,770` minor units per million roundings =
  4,997.70 major units. `4,997.70 × 2.8 = ` **13,993.56 per day**.
- `HALF_EVEN` against `DOWN`: `−82.4 − (−449,942.4) = 449,860` minor units = 4,498.60 major units.
  `4,498.60 × 2.8 = ` **12,596.08 per day**.
- `DOWN`: zero, and 4,499.42 per million roundings of bias *against* the client.

Against a bonus programme of 3.1k grants a day at an average of 42 — `3,100 × 42 = 130,200` a day of
intended promotional spend — `HALF_UP` is a **10.7% overrun on the entire bonus budget**
(`13,993.56 / 130,200`) and `HALF_EVEN` a 9.7% one, from nothing but a rounding mode.

### The judgement

`HALF_EVEN` is banker's rounding, and Run A shows why it earned the name: over a million ties it
drifted 0.88 where `HALF_UP` drifted 5,000.00. It is the tie-break that does not systematically
favour either party, which is why IEEE 754's default rounding is its binary equivalent and why
`MathContext.DECIMAL64` specifies it.

**And it is the wrong choice here.** QuizStakes' bonus rule is neither: the bonus portion rounds
**down** to the minor unit and cash covers the remainder. Run A shows `DOWN` drifting −5,000.00 over
a million ties, a systematic bias against the client, and that is the *intended* behaviour, not a
defect. The rule is asymmetric on purpose, because the outcomes are not symmetric in consequence:
under-granting a bonus by 0.005 costs the client half a penny of stakeable-but-not-withdrawable
promotional money, while over-granting creates withdrawable money from nothing, and a regulated
platform cannot do the second.

So the answer to "which rounding mode for money" is that it is a **business rule, not a numerical
preference**. The numerical argument does not choose; it prices each choice, and the three prices
above are what this experiment bought. Then the compliance owner picks, and the code says
`RoundingMode.DOWN` with a comment naming the rule.

**Interview:** "Which rounding mode would you use for money?" The answer that scores is "whichever
the business rule specifies — and if nobody has specified one, that is the finding; but I can tell
you what each costs." Then name `HALF_EVEN` as the default when the requirement is long-run
neutrality between two parties, and `DOWN` or `FLOOR` when one direction creates money.

**Pitfall:** `MathContext.DECIMAL64` uses `HALF_EVEN` and 16 significant digits, so reaching for it
to stop `divide` throwing imports both. Sixteen digits of *precision* is not a *scale*, so the
result's scale is unpredictable — measured at 16 above — and a `Money` asserting
`RoundingMode.UNNECESSARY` at the currency's scale then throws somewhere else.

### Diff vs the real one — this experiment versus a statistical framework

| Axis | This harness | What a property-based or JMH framework would add |
|---|---|---|
| Edge cases | covers positive ties, negative ties, non-ties and exact values in the mode table; the million-rounding runs use **positive amounts only**, so they never exercise the `DOWN`-versus-`FLOOR` divergence where a clawback lives | a parameterised sign, and a generator over the whole `long` minor-unit range |
| Intrinsics | every value stays at scale 2–8, so `setScale` runs on `BigDecimal`'s `intCompact` `long` fast path and no `BigInteger` code executes | nothing to add; a run over inflated `BigDecimal`s would exercise a wholly different path |
| Serialization | not applicable; nothing crosses a boundary | not applicable |
| Null policy | `setScale` would NPE on a null mode; not exercised | a null-mode case in a parameterised sweep |
| Thread safety | single-threaded; each run gets its own `Random` because the shared one is thread-safe but contended | `ThreadLocalRandom`, and `@State(Scope.Thread)` for the accumulators |
| Allocation tricks | allocates several `BigDecimal`s per iteration and does not care, because this measures values, not bytes | `-prof gc` would show it and correctly report it as irrelevant here |
| Why the JDK bothers | `RoundingMode` is an enum rather than eight `int` constants so the compiler rejects a mode from the wrong family, and `UNNECESSARY` exists so code can *assert* no rounding happened rather than hope | JMH is for timing, not correctness; these drift figures need no JMH because they are exact `BigDecimal` sums, not measurements of the machine |

> **Rounding bias:** `HALF_UP` and `HALF_EVEN` differ only on an exact tie, so the whole signal is
> how often your operation produces one — for a 10% bonus on a two-decimal stake that is one time in
> ten, worth 13,993.56 a day of created withdrawable cash across 2.8M reservations.

## Pitfalls

### Running the bias experiment over random data and concluding the modes are equivalent

**Wrong**

Run C above is that experiment, and its printed verdict is the belief in action:

```console
Run C: 1,000,000 scale-8 amounts, uniform in [1.00000000, 9.99999999]
  exact halves           2 of 1,000,000 (0.0002%)
  HALF_UP != HALF_EVEN   1 roundings
```

One disagreement in a million. Ship `HALF_UP`, it makes no difference — and the bonus split then
leaks 13,993.56 a day.

**Right**

Sample the distribution the *operation* produces, not a uniform distribution over the value space.
10% of a two-decimal stake always has a third decimal equal to the stake's last minor digit, so ties
fire one time in ten. Run B measured 99,826 ties and 499,770 `HALF_UP`-versus-`DOWN` divergences per
million — five orders of magnitude more exposure than the scale-8 experiment suggested. Pair it with
Run A, engineered so every value is a tie, which isolates the modes with no sampling noise at all
and gave `HALF_UP` +5,000.00 against `HALF_EVEN`'s +0.88.

**Why people believe it:** because "test it on random data" is genuinely good advice for almost
every other numerical experiment, and because scale-8 amounts *feel* like a more thorough test than
two-decimal ones. The intuition that finer-grained inputs are a harder test is exactly backwards
when the behaviour under test fires only on a coarse-grained coincidence.

### Believing `HALF_EVEN` is always the right choice for money

**Wrong**

```java
BigDecimal stake = new BigDecimal("3.35");
BigDecimal bonus = stake.multiply(new BigDecimal("0.10")).setScale(2, RoundingMode.HALF_EVEN);
BigDecimal cash = stake.subtract(bonus);
System.out.println("bonus " + bonus + " + cash " + cash + " = " + bonus.add(cash));
```

```console
bonus 0.34 + cash 3.01 = 3.35
```

The invariant holds and the total is right, and the split is still wrong: a 10% bonus on 3.35 is
exactly 0.335, and 0.34 grants a penny of bonus the deposit never funded — which, because bonus is
non-withdrawable and cash is not, leaves the client a penny more withdrawable cash. Run B measured
this firing on 49,910 of a million realistic stakes.

**Right**

```java
BigDecimal stake = new BigDecimal("3.35");
BigDecimal bonus = stake.multiply(new BigDecimal("0.10")).setScale(2, RoundingMode.DOWN);
BigDecimal cash = stake.subtract(bonus);
System.out.println("bonus " + bonus + " + cash " + cash + " = " + bonus.add(cash));
```

```console
bonus 0.33 + cash 3.02 = 3.35
```

The bonus rounds down, cash covers the remainder, the sum is still exactly the stake, and the house
never over-grants. `DOWN`, not `HALF_EVEN`, because the bonus rule is asymmetric on purpose.

**Why people believe it:** because `HALF_EVEN` genuinely is the right default for *symmetric*
rounding between two parties, it is what `MathContext.DECIMAL64` specifies, it is IEEE 754's
default, and "banker's rounding" sounds like it settles the question for banking. It answers a
different question — how to break a tie without long-run bias — and says nothing about a rule that
is deliberately biased.


### Believing `HALF_UP` and `DOWN` agree because they agree on the canonical stake

**Wrong**

```java
static BigDecimal bonus(String stake, RoundingMode mode) {
    return new BigDecimal(stake).multiply(new BigDecimal("0.10")).setScale(2, mode);
}

System.out.println("the canonical stake only:");
System.out.println("  3.33 HALF_UP " + bonus("3.33", RoundingMode.HALF_UP)
        + ", DOWN " + bonus("3.33", RoundingMode.DOWN)
        + ", equal: " + bonus("3.33", RoundingMode.HALF_UP).equals(bonus("3.33", RoundingMode.DOWN)));
```

```console
the canonical stake only:
  3.33 HALF_UP 0.33, DOWN 0.33, equal: true
```

The canonical example every note in this set uses to teach bonus rounding is a stake of 3.33, and on
3.33 the two modes agree — 10% is 0.333, which is not a tie, so both truncate to 0.33. A test suite
whose only rounding case is the canonical one passes under either mode, and the rule looks like a
matter of taste.

**Right**

Sweep the whole stake range rather than testing the example the documentation happened to pick:

```java
System.out.println("the next stake up that ends in 5 pence:");
System.out.println("  3.35 HALF_UP " + bonus("3.35", RoundingMode.HALF_UP)
        + ", DOWN " + bonus("3.35", RoundingMode.DOWN)
        + ", equal: " + bonus("3.35", RoundingMode.HALF_UP).equals(bonus("3.35", RoundingMode.DOWN)));
System.out.println("sweeping every 2-decimal stake from 1.00 to 9.99:");
int diverge = 0;
for (long m = 100; m <= 999; m++) {
    BigDecimal stake = BigDecimal.valueOf(m, 2);
    BigDecimal up = stake.multiply(new BigDecimal("0.10")).setScale(2, RoundingMode.HALF_UP);
    BigDecimal down = stake.multiply(new BigDecimal("0.10")).setScale(2, RoundingMode.DOWN);
    if (up.compareTo(down) != 0) {
        diverge++;
    }
}
System.out.println("  HALF_UP and DOWN diverge on " + diverge + " of 900 stakes");
```

```console
the next stake up that ends in 5 pence:
  3.35 HALF_UP 0.34, DOWN 0.33, equal: false
sweeping every 2-decimal stake from 1.00 to 9.99:
  HALF_UP and DOWN diverge on 450 of 900 stakes
```

Exactly half of all two-decimal stakes diverge — the exhaustive result, and it matches Run B's
sampled 499,770 divergences per million (49.977%) to within sampling noise. The canonical 3.33 is
one of the 450 that agree, which is precisely why it is a bad regression test for the rounding rule
and a good one for the split invariant.

**Why people believe it:** because 3.33 is the example in the spec, and an example chosen to
illustrate "the bonus rounds down" is naturally one where rounding down is visible in the arithmetic
(0.333 → 0.33) rather than one where the tie-break decides. The example teaches the rule and hides
the divergence, which is a good example and a terrible test case.

### Treating the choice of rounding mode as a numerical question

**Wrong**

`HALF_EVEN` is banker's rounding, it is IEEE 754's default, it is what `MathContext.DECIMAL64`
specifies, and Run A proves it is the least biased tie-break on the page — 0.88 of drift over a
million ties against `HALF_UP`'s 5,000.00. So use `HALF_EVEN` for money and move on.

```console
Run A: 1,000,000 engineered halves
  HALF_UP   drift        500000 minor units = 5000.0000 major units
  HALF_EVEN drift        88 minor units = 0.8800 major units
  DOWN      drift        -500000 minor units = -5000.0000 major units
```

Every number there is correct and the conclusion does not follow. Run B prices `HALF_EVEN` at
12,596.08 a day of withdrawable cash created against `DOWN` — 9.7% of the entire bonus budget — for
a platform whose rule forbids creating any.

**Right**

Read the same output as a price list rather than a ranking, and let the rule choose:

| Mode | Run A drift over 1M ties | Cost per day at 2.8M splits | When it is right |
|---|---|---|---|
| `HALF_UP` | +5,000.00 | 13,993.56 | a regulator specifies commercial rounding |
| `HALF_EVEN` | +0.88 | 12,596.08 | long-run neutrality between two parties is the requirement |
| `DOWN` | −5,000.00 | 0 | one direction creates money — **QuizStakes' bonus rule** |

`DOWN`'s −5,000.00 is a systematic bias against the client, and it is the *intended* behaviour, not
a defect: under-granting a bonus by 0.005 costs the client half a penny of
stakeable-but-not-withdrawable promotional money, while over-granting creates withdrawable money
from nothing. The code says `RoundingMode.DOWN` with a comment naming the rule, and if no rule has
been written down, that absence is the finding to escalate.

**Why people believe it:** because "banker's rounding" sounds like it settles the question for
banking, and because `HALF_EVEN` genuinely is the correct default for the question it answers — how
to break a tie without favouring either party over a long run. A rule that is *deliberately*
asymmetric is outside that question's scope entirely, and no amount of drift measurement will
surface it, because the measurement cannot know which direction is forbidden.

## Cheat sheet

| Fact | Value |
|---|---|
| `HALF_UP` vs `HALF_EVEN` | differ **only** on an exact tie; identical on every other input |
| So the experiment measures | how often *your operation* produces a tie — nothing about the modes |
| Tie rate, 10% of a 2-decimal stake | **1 in 10** (stake ends in 5 minor units); measured 99,826 per million |
| Tie rate, scale-8 random amounts | 2 per million; 1 mode disagreement per million |
| Divergence, `HALF_UP` vs `DOWN`, exhaustive | **450 of 900** two-decimal stakes; sampled 499,770 per million |
| Run A, 1M engineered ties: `HALF_UP` | **+500,000 minor units = +5,000.00**, zero variance |
| Run A, 1M engineered ties: `HALF_EVEN` | +88 minor units = +0.88 (random walk, sd ≈ 500 minor units) |
| Run A, 1M engineered ties: `DOWN` | **−500,000 minor units = −5,000.00** |
| Run B, realistic: `HALF_UP` / `HALF_EVEN` / `DOWN` | +49,827.6 / −82.4 / −449,942.4 minor units |
| Cost per day at 2.8M splits | `HALF_UP` **13,993.56**, `HALF_EVEN` **12,596.08**, `DOWN` **0** |
| As a share of bonus spend (3,100 × 42 = 130,200/day) | 10.7% and 9.7% |
| Why it is a leak at all | bonus is non-withdrawable, cash is both; rounding the bonus up spends bonus and spares cash |
| `StakeSplit` invariant | holds under every mode — it constrains the total, not which bucket paid |
| QuizStakes bonus rounding | **`RoundingMode.DOWN`**; cash covers the remainder |
| Canonical 3.33 | `HALF_UP` and `DOWN` both give 0.33 — a bad regression test for the rule |
| First divergent stake | 3.35 → `HALF_UP` 0.34 + 3.01, `DOWN` 0.33 + 3.02 |
| The eight modes | `UP`, `DOWN`, `CEILING`, `FLOOR`, `HALF_UP`, `HALF_DOWN`, `HALF_EVEN`, `UNNECESSARY` |
| `UP`/`DOWN` vs `CEILING`/`FLOOR` | agree on positives, differ on negatives — where a clawback lives |
| `UNNECESSARY` | throws unless no rounding is needed; use it as an assertion |
| `MathContext.DECIMAL64` | `HALF_EVEN` at 16 significant digits — a precision, not a scale |
| Measure | cumulative **signed** drift, not a count of differing roundings — drift is what reconciliation sees |
| Not JMH | and it does not need to be: the drift figures are exact `BigDecimal` sums |

## Self-test

**Q1.** You round a million uniformly random scale-8 amounts, find `HALF_UP` and `HALF_EVEN` disagree
once, and report that the mode is immaterial. What did you measure, and what answers the question?

<details><summary>Answer</summary>

You measured how often a uniformly random scale-8 amount sits exactly halfway between two scale-2
neighbours, which needs its last six digits to be exactly 500000 — one chance in a million. Run C
measured 2 ties and 1 disagreement, so it correctly reports that random high-precision data almost
never triggers the only input class where the modes differ. That is a fact about the data, not the
modes.

Sample the distribution the real operation produces instead. A 10% bonus on a two-decimal stake
yields a three-decimal exact result whose third digit is the stake's last minor digit, so a tie fires
whenever the stake ends in 5 pence: 99,826 per million measured. Pair it with a run engineered so
every value is a tie, which isolates the modes without sampling noise and gave `HALF_UP` +5,000.00
against `HALF_EVEN`'s +0.88.

</details>

**Q2.** In the engineered run `HALF_UP`'s drift came out at exactly +500,000 minor units with no
residual while `HALF_EVEN`'s came out at +88. Why does one have zero variance and the other not?

<details><summary>Answer</summary>

`HALF_UP` rounds a tie away from zero unconditionally, and every value in the run is a positive exact
tie, so every rounding gains exactly +0.5 minor units regardless of the digits: the drift is
`0.5 × 1,000,000 = 500,000` deterministically — arithmetic, not sampling.

`HALF_EVEN` takes the even neighbour, so for an exact bonus of `t + 0.5` minor units it rounds down
to `t` when `t` is even and up to `t + 1` when `t` is odd. The drift is `0.5 × (oddCount − evenCount)`,
and with `t` drawn at random that difference is a random walk with expectation 0 and standard
deviation about `sqrt(1,000,000) = 1,000`, so the drift's standard deviation is about 500 minor
units. The measured +88 is 176 more odd draws than even — confirmed by the run's own disagreement
count of 499,912, which is the number of even `t`: `500,088 − 499,912 = 176`, and `176 × 0.5 = 88`.

</details>

**Q3.** With `HALF_EVEN` a stake of 3.35 splits as 0.34 bonus plus 3.01 cash, which sums to 3.35, so
the `StakeSplit` invariant holds. Where is the money going wrong, and what does it cost?

<details><summary>Answer</summary>

The invariant constrains the total, not the allocation between buckets, and the buckets are not
interchangeable: bonus is stakeable but never directly withdrawable, cash is both. A 10% bonus on
3.35 is exactly 0.335, so rounding the bonus up to 0.34 charges a penny more to
`CLIENT_BONUS_AVAILABLE` and a penny less to `CLIENT_CASH_AVAILABLE`, leaving the client a penny more
withdrawable money than the deposit funded. The ledger balances and the house has created
withdrawable value out of a rounding mode.

From Run B's drift columns scaled to 2.8M reservations a day: `HALF_EVEN` grants 449,860 minor units
more than `DOWN` per million roundings, which is 4,498.60 major units, so `4,498.60 × 2.8 = 12,596.08`
a day; `HALF_UP` is worse at 13,993.56. Against 130,200 a day of intended bonus spend those are 9.7%
and 10.7% overruns. The rule is `DOWN` on the bonus with cash covering the remainder: 0.33 plus 3.02.

</details>

**Q4.** `UP` and `CEILING` agree on every positive value. Give the input on which they differ and
name the QuizStakes operation where that difference matters.

<details><summary>Answer</summary>

They differ on any negative value. Measured: −0.335 gives −0.34 under `UP` (away from zero) and
−0.33 under `CEILING` (toward positive infinity); `DOWN` and `FLOOR` mirror it at −0.33 and −0.34.

It matters on a clawback, the one QuizStakes operation naturally expressed as a negative amount. A
clawback takes unspent bonus first and sends any shortfall to `PROMOTIONAL_EXPENSE`, so a mode that
rounds a negative toward zero recovers less than the rule says. It is also why the minor-unit `long`
representation needs care: Java's integer division truncates toward zero, so `-335 / 10 == -33`,
which is `UP` on a negative — the opposite of the `DOWN` it delivers on positives.

</details>

**Q5.** Why does the harness accumulate drift in `BigDecimal` and report it in minor units, rather
than counting how many roundings differed between two modes?

<details><summary>Answer</summary>

Two separate reasons. Accumulating in `BigDecimal` rather than `double` is because an experiment
about rounding error that accumulated its own results in a lossy type would be measuring itself; the
drift figures are then exact sums, not measurements, which is also why this harness needs no JMH.

Reporting signed drift rather than a count is because drift is what reconciliation sees. A count of
differing roundings does not tell you the direction or the magnitude: Run B's 49,910
`HALF_UP`-versus-`HALF_EVEN` disagreements could in principle have cancelled out, and the only way
to know they did not is the signed sum. Drift also converts directly into money — 499,770 minor units
per million roundings becomes 13,993.56 a day at 2.8M splits — which a count never does.

</details>

**Q6.** A reviewer says the whole experiment is pointless because the platform should just store
money in minor-unit `long`s, where integer division truncates and the question disappears. What is
right and what is wrong about that?

<details><summary>Answer</summary>

Right that for positive amounts Java's integer division is precisely `RoundingMode.DOWN`, so
`335 / 10 == 33` and the `long` representation delivers the bonus rule with no rounding mode named
anywhere. That is a real advantage and it is why the `long` path is worth considering.

Wrong on three counts. First, it delivers the rule *by accident*: there is no place in the code where
the rule is stated, so nothing breaks visibly if the rule changes and nothing documents it if it does
not. Second, truncation is toward zero, not downward, so `-335 / 10 == -33` rounds a negative up and
a clawback silently favours the client — the `long` representation has not removed the rounding
decision, it has hidden it and got the negative case wrong. Third, the experiment's conclusion is not
about a representation at all: it is that the mode is a business rule, and a representation that
cannot express the alternatives cannot be told when the rule changes.

</details>

## Open questions

- The million-rounding runs use **positive amounts only**, so they never exercise the
  `DOWN`-versus-`FLOOR` divergence on negatives, which is where a clawback lives. The mode table
  covers the negative tie (−0.335) case by construction, but no drift figure here prices a clawback.
  A run over signed stake amounts would settle what that costs.

---

**Leaves covered:** 4.7.3 (the rounding-bias half; the allocation and precision half is in
[04c-allocation-and-rounding-bias.md](04c-allocation-and-rounding-bias.md))
**Leaves deferred:** none
**Diagrams included:** none
**Target version:** Java 21 LTS
**Lines:** 688
