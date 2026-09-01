# 03 Java Core — Value-object builds — the allocation and precision comparison — BUILD IT (§4.7, 4.7.3)

**Target version: Java 21 LTS.** | **Part 4 of 5** | [Index](../00-index.md)
Previous: [Money two ways](04-value-objects-and-money.md) · Next: [The rounding-bias experiment](04e-rounding-bias-experiment.md)

---

Two representations of the same money — `Money(BigDecimal, Currency)` and
`MoneyMinor(long, Currency)` — differ in two ways, and only one of them matters.

The measurable difference is **2.67×** in bytes allocated per stake split, with escape analysis
disabled: 192 B against 72 B measuring the split alone, 256 B against 96 B measuring the split plus
the construction of its input. That is a capacity question. At 2.8M stake reservations a day the
split-alone basis is 537.6 MB/day of young-generation churn against 201.6 MB/day, and neither figure
decides a design.

The unbounded difference is which roundings each representation can express, and what a rounding
mode does to a bonus balance over a million operations. That is a **correctness** question, and it
is the one that loses money. This file measures the first difference and establishes where each
representation is exact; [the rounding-bias experiment](04e-rounding-bias-experiment.md) runs the
million roundings and prices the second.

**Every composite allocation figure in this file carries its basis, and that is not pedantry.** The
per-object figures — 40 B for a `BigDecimal`, 64 B for a `Money`, 24 B for a `MoneyMinor` — reproduce
identically on every run, on this machine and on order 21's. The *composite* split figure does not:
272 B, 256 B, 192 B and 152 B have all been measured for "one stake split", and every one of them is
correct for its own basis. The bases that differ are whether the input `Money` is pre-built or
constructed inside the measured region, and whether escape analysis is on. A composite allocation
number without its basis is not a measurement, it is a number. D-135 in order 21 was amended for the
same reason: it now gives the two bases and the 2.67× ratio rather than one composite figure.

Neither harness here is JMH: no forking, no `Blackhole`, no dead-code guard beyond a `volatile`
sink, and the JIT's compilation state is whatever a warm loop in one process produces. Neither is
the canonical cost harness — [the master cost table](../cost-model/02-master-cost-table.md) owns
that one and its five cost bands, and is equally explicit that it is not JMH. Guide 06 owns JMH.
Everything below was compiled and run on **Oracle JDK 21.0.7 (build 21.0.7+8-LTS-245), macOS
aarch64**, compressed oops on.

## Part one — allocation

Order 21's `Money`, `MoneyMinor` and `StakeSplit` are restated inside the harness, because a
measurement file that describes the code it measured rather than showing it is not evidence — every
byte count below came from exactly this file. `StakeSplitMinor` is new, and exists only for fairness:
order 21's `splitMinor` returned a two-element array, and comparing a record-returning path against
an array-returning path measures the container. Both cost 24 B, so the ratio is unchanged, but the
comparison is now like for like.

The house method is `com.sun.management.ThreadMXBean.getThreadAllocatedBytes` deltas across a loop
after a warm-up, with each result stored to a `volatile` field so nothing is dead code. `perUnit`
lets one `make()` cover a whole batch and still report a per-split figure.

```java
import com.sun.management.ThreadMXBean;
import java.lang.management.ManagementFactory;
import java.math.BigDecimal;
import java.math.RoundingMode;
import java.util.Currency;
import java.util.Objects;

public final class AllocationHarness {

    static final Currency GBP = Currency.getInstance("GBP");
    static final BigDecimal BONUS_RATE = new BigDecimal("0.10");

    record Money(BigDecimal amount, Currency currency) {
        Money {
            Objects.requireNonNull(amount, "amount");
            Objects.requireNonNull(currency, "currency");
            int digits = currency.getDefaultFractionDigits();
            if (amount.scale() != digits) {
                amount = amount.setScale(digits, RoundingMode.UNNECESSARY);
            }
        }

        static Money of(long minorUnits, Currency currency) {
            return new Money(BigDecimal.valueOf(minorUnits, currency.getDefaultFractionDigits()), currency);
        }

        Money minus(Money other) {
            if (!currency.equals(other.currency)) {
                throw new IllegalArgumentException("currency mismatch: " + currency + " vs " + other.currency);
            }
            return new Money(amount.subtract(other.amount), currency);
        }

        Money multiply(BigDecimal factor, RoundingMode mode) {
            return new Money(amount.multiply(factor).setScale(currency.getDefaultFractionDigits(), mode), currency);
        }
    }

    record MoneyMinor(long units, Currency currency) {
        MoneyMinor {
            Objects.requireNonNull(currency, "currency");
        }

        MoneyMinor minus(MoneyMinor other) {
            if (!currency.equals(other.currency)) {
                throw new IllegalArgumentException("currency mismatch");
            }
            return new MoneyMinor(Math.subtractExact(units, other.units), currency);
        }
    }

    record StakeSplit(Money bonusPortion, Money cashPortion) { }

    record StakeSplitMinor(MoneyMinor bonusPortion, MoneyMinor cashPortion) { }

    /** The BigDecimal path: bonus is 10% of stake rounded DOWN, cash covers the remainder. */
    static StakeSplit splitBigDecimal(Money stake) {
        Money bonus = stake.multiply(BONUS_RATE, RoundingMode.DOWN);
        return new StakeSplit(bonus, stake.minus(bonus));
    }

    /** The long path: integer division by 10 truncates, which IS RoundingMode.DOWN for positives. */
    static StakeSplitMinor splitMinor(MoneyMinor stake) {
        MoneyMinor bonus = new MoneyMinor(stake.units() / 10, stake.currency());
        return new StakeSplitMinor(bonus, stake.minus(bonus));
    }

    interface Alloc {
        Object make();
    }

    static volatile Object sink;
    static final ThreadMXBean BEAN = (ThreadMXBean) ManagementFactory.getThreadMXBean();
    static final long TID = Thread.currentThread().threadId();

    /** perUnit is how many splits one make() performs, so a batch reports per-split too. */
    static void perOp(String label, int iters, int perUnit, Alloc a) {
        for (int i = 0; i < iters / 10; i++) {
            sink = a.make();
        }
        long before = BEAN.getThreadAllocatedBytes(TID);
        for (int i = 0; i < iters; i++) {
            sink = a.make();
        }
        long total = BEAN.getThreadAllocatedBytes(TID) - before;
        System.out.printf("%-42s %,14d B total  %9.2f B/op  %6.2f B/split%n",
                label, total, (double) total / iters, (double) total / iters / perUnit);
    }

    public static void main(String[] args) {
        boolean eaOn = ManagementFactory.getRuntimeMXBean().getInputArguments()
                .stream().noneMatch(a -> a.contains("-DoEscapeAnalysis"));
        System.out.println("escape analysis on: " + eaOn);

        final Money stake = Money.of(333, GBP);
        final MoneyMinor stakeMinor = new MoneyMinor(333, GBP);
        final int n = 2_000_000;

        perOp("BigDecimal.valueOf(333, 2)", n, 1, () -> BigDecimal.valueOf(333, 2));
        perOp("new Money(BigDecimal.valueOf(333,2), GBP)", n, 1, () -> new Money(BigDecimal.valueOf(333, 2), GBP));
        perOp("new MoneyMinor(333, GBP)", n, 1, () -> new MoneyMinor(333, GBP));
        perOp("splitBigDecimal(stake)", n, 1, () -> splitBigDecimal(stake));
        perOp("splitMinor(stakeMinor)", n, 1, () -> splitMinor(stakeMinor));
        perOp("splitBigDecimal(Money.of(333, GBP))", n, 1, () -> splitBigDecimal(Money.of(333, GBP)));
        perOp("splitMinor(new MoneyMinor(333, GBP))", n, 1, () -> splitMinor(new MoneyMinor(333, GBP)));
        perOp("batch of 1,000 BigDecimal splits", 2_000, 1_000, () -> {
            StakeSplit last = null;
            for (int i = 0; i < 1_000; i++) {
                last = splitBigDecimal(stake);
            }
            return last;
        });
        perOp("batch of 1,000 long splits", 2_000, 1_000, () -> {
            StakeSplitMinor last = null;
            for (int i = 0; i < 1_000; i++) {
                last = splitMinor(stakeMinor);
            }
            return last;
        });
    }
}
```

### Both configurations, real output

```console
$ java -XX:-DoEscapeAnalysis AllocationHarness
escape analysis on: false
BigDecimal.valueOf(333, 2)                     80,000,000 B total      40.00 B/op   40.00 B/split
new Money(BigDecimal.valueOf(333,2), GBP)     128,000,000 B total      64.00 B/op   64.00 B/split
new MoneyMinor(333, GBP)                       48,000,000 B total      24.00 B/op   24.00 B/split
splitBigDecimal(stake)                        384,000,000 B total     192.00 B/op  192.00 B/split
splitMinor(stakeMinor)                        144,000,000 B total      72.00 B/op   72.00 B/split
splitBigDecimal(Money.of(333, GBP))           512,000,000 B total     256.00 B/op  256.00 B/split
splitMinor(new MoneyMinor(333, GBP))          192,000,000 B total      96.00 B/op   96.00 B/split
batch of 1,000 BigDecimal splits              384,000,000 B total  192000.00 B/op  192.00 B/split
batch of 1,000 long splits                    144,000,000 B total   72000.00 B/op   72.00 B/split
```

```console
$ java AllocationHarness
escape analysis on: true
BigDecimal.valueOf(333, 2)                     80,000,000 B total      40.00 B/op   40.00 B/split
new Money(BigDecimal.valueOf(333,2), GBP)     128,000,000 B total      64.00 B/op   64.00 B/split
new MoneyMinor(333, GBP)                       48,000,000 B total      24.00 B/op   24.00 B/split
splitBigDecimal(stake)                        304,000,000 B total     152.00 B/op  152.00 B/split
splitMinor(stakeMinor)                        144,000,000 B total      72.00 B/op   72.00 B/split
splitBigDecimal(Money.of(333, GBP))           432,000,000 B total     216.00 B/op  216.00 B/split
splitMinor(new MoneyMinor(333, GBP))          144,000,000 B total      72.00 B/op   72.00 B/split
batch of 1,000 BigDecimal splits              304,000,000 B total  152000.00 B/op  152.00 B/split
batch of 1,000 long splits                    144,000,000 B total   72000.00 B/op   72.00 B/split
```

### The byte arithmetic

| Object | Header | Fields | Sum | Aligned | Measured |
|---|---|---|---|---|---|
| `BigDecimal` | 12 | `intVal` ref 4, `scale` 4, `precision` 4, `stringCache` ref 4, `intCompact` long 8 = 24 | 36 | **40** | 40.00 B/op |
| `Money` alone | 12 | two refs, 4 + 4 = 8 | 20 | **24** | 64 − 40 = 24 |
| `Money` with its `BigDecimal` | — | — | — | **64** | 64.00 B/op |
| `MoneyMinor` | 12 | `units` long 8, `currency` ref 4 = 12 | 24 | **24** | 24.00 B/op |
| `StakeSplit`, `StakeSplitMinor` | 12 | two refs, 4 + 4 = 8 | 20 | **24** | derived below |

`Currency` costs nothing per instance: `Currency.getInstance` returns an interned instance from a
static table, so every `Money` shares one `GBP` object and pays only the 4-byte reference.
`splitBigDecimal(stake)`, escape analysis off, allocation by allocation:

| Allocation | Bytes |
|---|---|
| `amount.multiply(BONUS_RATE)` result, a `BigDecimal` at scale 4 | 40 |
| `.setScale(2, DOWN)` result, another `BigDecimal` | 40 |
| the `Money` wrapping the bonus | 24 |
| `amount.subtract(other.amount)` result, another `BigDecimal` | 40 |
| the `Money` wrapping the cash | 24 |
| `new StakeSplit(bonus, cash)` | 24 |
| **Total** | **192** |

40 + 40 + 24 + 40 + 24 + 24 = **192**, and the harness printed 192.00. `splitMinor` allocates two
`MoneyMinor` (one directly, one inside `minus`) plus the `StakeSplitMinor`: 24 + 24 + 24 = **72**,
printed as 72.00. **192 / 72 = 2.67×.** Starting from a bare `long` adds one `BigDecimal` plus one
`Money` (40 + 24 = 64) to the first path and one `MoneyMinor` (24) to the second: 192 + 64 = **256**
and 72 + 24 = **96**, both printed, 256 / 96 = 2.67× again. The batch confirms there is no fixed cost
to amortise: 1,000 splits allocate exactly 192,000 B and 72,000 B.

**Insight:** the difference is not that `BigDecimal` is a fat object — 40 B against a `MoneyMinor`'s
24 B is nothing. It is that `BigDecimal` is **immutable**, so each of the three arithmetic steps
materialises a new one. Immutability is the cost, not width.

### What escape analysis does to the answer

Under the default JIT the split drops from 192 B to 152 B — exactly 40 B, exactly one `BigDecimal`.
The only `BigDecimal` in `splitBigDecimal` that never escapes is the `multiply` result: `setScale`
consumes it on the next expression and no reference survives, so C2 scalar-replaces it and the
object is never born. The other two are reachable from the returned `StakeSplit`. **Unverified:**
that attribution rests on the delta being exactly one `BigDecimal` plus that object being the only
non-escaping one; `-XX:+PrintEliminateAllocations` would confirm it but is `notproduct`.

The long path shows the effect more cleanly. `splitMinor(stakeMinor)` is 72 B under both
configurations, because all three objects escape through the return value. But
`splitMinor(new MoneyMinor(333, GBP))` is 96 B with escape analysis off and **72 B** with it on: the
temporary input is consumed entirely inside the callee after inlining, so C2 deletes it. That is why
a default-JIT figure is not a statement about a representation — it measures what C2 proved about one
call site in one warm loop. Put the split behind an interface with three implementations so the site
goes megamorphic and inlining fails, and the deleted allocations come back. Report both, always.

**And this is where the basis rule earns its keep.** Four composite figures now exist for "one stake
split" on this JDK — 192, 256, 152, 216 — from two orthogonal choices: what the measured region
contains, and whether escape analysis is on. A fifth, the commissioned 272 B and its 3.78× ratio
against 72 B, reproduced on no basis this file could construct; 3.78× is additionally
unlike-for-unlike, dividing a split that builds its own input by one that does not. The per-object
figures agree everywhere, so the disagreement is confined to the intermediate count inside the
measured region. 201.6 MB/day reproduces exactly.

### The daily figure, and what it actually costs

QuizStakes reserves **2.8M stakes a day**, one split each.

| Path | B/split | Per day | Configuration |
|---|---|---|---|
| `BigDecimal` | 192 | 2,800,000 × 192 = 537,600,000 B ≈ **537.6 MB/day** | escape analysis off |
| `long` | 72 | 2,800,000 × 72 = 201,600,000 B ≈ **201.6 MB/day** | escape analysis off |
| `BigDecimal` | 152 | 2,800,000 × 152 = 425,600,000 B ≈ **425.6 MB/day** | default JIT |
| `long` | 72 | 2,800,000 × 72 = 201,600,000 B ≈ **201.6 MB/day** | default JIT |

The difference is 537,600,000 − 201,600,000 = 336,000,000 B ≈ 336 MB/day, or 3.9 kB/s averaged over
the day; at the 1,200/sec peak, 230 kB/s.

**This does not decide the design.** Not one byte is heap growth. A `StakeSplit` is dead microseconds
after the reservation reaches the ledger, so all of it dies in the young generation, and the cost of
a young collection is proportional to what **survives**, not to what was allocated. Guide 06 owns GC.

**Pitfall:** the figure that would decide it is allocation rate at peak on the hottest path, not
bytes per day — and the honest reading is that 2.8M splits a day is not enough volume for allocation
to decide either way. Choose on precision and API clarity; allocation is a tiebreaker.

### Diff vs the real one — this harness versus JMH

| Axis | This harness | JMH |
|---|---|---|
| Edge cases | one fixed input, so branch prediction is perfect and no `BigDecimal` slow path runs | `@Param` sweeps inputs; 3.33, 3.35 and an inflated `BigDecimal` would each be a run |
| Intrinsics | none involved; `getThreadAllocatedBytes` is a plain JVM TI call | reads the same counters via `GcProfiler` under `-prof gc`, normalised per operation |
| Serialization | not applicable to a harness | not applicable |
| Null policy | `sink` starts null and is never read, so nothing observes it | `Blackhole.consume` is null-tolerant by design |
| Thread safety | single-threaded; `getThreadAllocatedBytes` is per-thread, so a second thread is invisible | `@Threads` and `@State(Scope.Benchmark)` make the multi-threaded case expressible |
| Allocation tricks | defeats scalar replacement only with the blunt global `-XX:-DoEscapeAnalysis` | same problem, same blunt fix; JMH measures both configurations rather than making C2 lie |
| Why the JDK bothers | `getThreadAllocatedBytes` exists so a container can bill allocation per request thread, and is cheap because TLAB accounting already tracks it | JMH exists because hand-rolled loops silently report a JIT state rather than a cost |

The section-wide diff of these value objects against what a plain `record` gives you for free lives
in [the §4.7 diff](04d-value-object-diff.md), leaf 4.7.8.

> **Allocation:** the `BigDecimal` split costs 2.67× the bytes of the `long` split because immutable
> arithmetic materialises an object per step — and at 2.8M splits a day that is 336 MB of
> young-generation garbage, not enough to decide anything.

## Part two — precision, the half that matters

A `BigDecimal` is an unscaled integer plus a decimal `scale`, its value being
*unscaled* × 10<sup>−scale</sup>. Because the base is 10, every value a human can write with
finitely many decimal digits is exactly representable, and `add`, `subtract` and `multiply` are
always exact — they compute the exact result and derive the scale from the operands. A `long` of
minor units is the same idea with the scale pinned to the currency's `getDefaultFractionDigits()`,
so addition and subtraction of whole minor units are exact too, and cheaper. A `double` is base
**2**, so 0.1, 0.2 and 0.33 are not representable at all and every operation starts from a value
already wrong. [Numbers and money](../numbers-and-money/02-numbers-and-money.md) owns money
representation; [the `BigDecimal` internals](../numbers-and-money/03-internals-bigdecimal.md) own
the field set and the `intCompact` fast path. Division is where all three break, differently.

```java
import java.math.BigDecimal;
import java.math.MathContext;
import java.math.RoundingMode;

public final class PrecisionHarness {

    static final BigDecimal TENTH = new BigDecimal("0.10");
    static final BigDecimal THREE = new BigDecimal("3");

    static void show(String label, Object value) {
        System.out.printf("  %-26s %s%n", label, value);
    }

    public static void main(String[] args) {
        BigDecimal stake = new BigDecimal("3.33");

        System.out.println("1. BigDecimal is exact for anything writable; multiply grows the scale");
        show("3.33 scale", stake.scale());
        show("3.33 * 0.10", stake.multiply(TENTH) + ", scale " + stake.multiply(TENTH).scale());

        System.out.println("2. divide is the one operation that refuses to guess");
        try {
            show("1 / 3", BigDecimal.ONE.divide(THREE));
        } catch (ArithmeticException e) {
            show("1 / 3", e.getClass().getName() + ": " + e.getMessage());
        }
        show("1/3 scale 2 HALF_EVEN", BigDecimal.ONE.divide(THREE, 2, RoundingMode.HALF_EVEN));
        BigDecimal ctx = BigDecimal.ONE.divide(THREE, MathContext.DECIMAL64);
        show("1/3 DECIMAL64", ctx + ", scale " + ctx.scale());

        System.out.println("3. minor-unit long: exact on + and -, truncates toward zero on /");
        show("333 / 10", 333L / 10 + " minor units, " + 333L % 10 + " tenths of a unit discarded");
        show("333 - 33", (333L - 33L) + " minor units; 33 + 300 == 333 is " + (33L + 300L == 333L));
        show("335 / 10", 335L / 10 + " minor units: an exact half, silently dropped");
        show("-335 / 10", -335L / 10 + " minor units: truncation toward zero rounds a negative UP");

        System.out.println("4. double is wrong for both, and never says so");
        show("0.1 + 0.2", (0.1 + 0.2) + "; == 0.3 is " + (0.1 + 0.2 == 0.3));
        show("new BigDecimal(0.1)", new BigDecimal(0.1));

        double bonusDouble = 0.0;
        BigDecimal bonusDecimal = BigDecimal.ZERO.setScale(2);
        long bonusMinor = 0L;
        for (int i = 0; i < 3_100; i++) {
            bonusDouble += 0.10 * 4.20;
            bonusDecimal = bonusDecimal.add(new BigDecimal("4.20").multiply(TENTH).setScale(2, RoundingMode.DOWN));
            bonusMinor += 420L / 10L;
        }
        System.out.println("5. a bonus balance: 3,100 grants of 10% of 4.20, three ways");
        show("double", bonusDouble);
        show("BigDecimal", bonusDecimal);
        show("long minor units", bonusMinor + " = " + BigDecimal.valueOf(bonusMinor, 2));
        show("double error", BigDecimal.valueOf(bonusDouble).subtract(bonusDecimal));

        double stakeable = 0.0;
        for (int i = 0; i < 1_000_000; i++) {
            stakeable += 0.01;
        }
        System.out.println("6. a stakeable balance: 1,000,000 double additions of 0.01");
        show("double", stakeable + "  (exact answer 10000.00)");
        show("drift", BigDecimal.valueOf(stakeable).subtract(new BigDecimal("10000.00")));
    }
}
```

```console
$ java PrecisionHarness
1. BigDecimal is exact for anything writable; multiply grows the scale
  3.33 scale                 2
  3.33 * 0.10                0.3330, scale 4
2. divide is the one operation that refuses to guess
  1 / 3                      java.lang.ArithmeticException: Non-terminating decimal expansion; no exact representable decimal result.
  1/3 scale 2 HALF_EVEN      0.33
  1/3 DECIMAL64              0.3333333333333333, scale 16
3. minor-unit long: exact on + and -, truncates toward zero on /
  333 / 10                   33 minor units, 3 tenths of a unit discarded
  333 - 33                   300 minor units; 33 + 300 == 333 is true
  335 / 10                   33 minor units: an exact half, silently dropped
  -335 / 10                  -33 minor units: truncation toward zero rounds a negative UP
4. double is wrong for both, and never says so
  0.1 + 0.2                  0.30000000000000004; == 0.3 is false
  new BigDecimal(0.1)        0.1000000000000000055511151231257827021181583404541015625
5. a bonus balance: 3,100 grants of 10% of 4.20, three ways
  double                     1302.0000000000045
  BigDecimal                 1302.00
  long minor units           130200 = 1302.00
  double error               4.5E-12
6. a stakeable balance: 1,000,000 double additions of 0.01
  double                     10000.000000171856  (exact answer 10000.00)
  drift                      1.71856E-7
```

### Reading it

**`multiply` is exact and grows the scale.** 3.33 times 0.10 gives 0.3330 at scale **4** — the exact
product, the scale being the sum of the operand scales. Nothing is lost and nothing is decided:
0.3330 is not yet a bonus, because a bonus must be expressible in minor units. Rounding is a
separate, explicit step, and that separation is the design.

**`divide` with neither a scale nor a `MathContext` throws.** `BigDecimal.ONE.divide(THREE)` raises
`ArithmeticException: Non-terminating decimal expansion; no exact representable decimal result.` It
is the only place `BigDecimal` refuses to answer, and it refuses rather than guess a precision. Two
fixes: a scale plus a `RoundingMode`, giving 0.33; or a `MathContext`, giving 0.3333333333333333 at
scale 16. Prefer the first for money — a scale is a currency fact, a precision is not. It throws only
when the quotient does not terminate, so a test suite built on divisors of 10 passes and the
exception arrives the first time a stake is split seven ways.

**`long` truncates, and the truncation is the bonus rule.** `333 / 10 == 33`, discarding 3 tenths of
a minor unit; `335 / 10 == 33` too, discarding an exact half. For positive values Java's integer
division is precisely `RoundingMode.DOWN`, which is precisely what the bonus rule wants — not a
coincidence to celebrate but one to write down, because the `long` path then enforces the right rule
by accident and offers no place to notice if the rule changes. And it truncates **toward zero**, so
`-335 / 10 == -33` rounds a negative *up*: a clawback expressed as a negative amount silently
favours the client.

**`double` is wrong in both directions.** Accumulating 3,100 bonus grants of 10% of 4.20 into a
`double` bonus balance gives 1302.0000000000045 where the exact answer is 1302.00 — an error of
4.5E-12, invisible until it meets a reconciliation that compares to the penny. A million additions
of 0.01 to a stakeable balance reaches 10000.000000171856, a drift of 1.71856E-7. Neither error is
large; both are non-zero, and a ledger whose invariant is "debits equal credits **exactly**" fails on
a non-zero error of any size.

**Insight:** `new BigDecimal(0.1)` prints `0.1000000000000000055511151231257827021181583404541015625`.
That is not a `BigDecimal` defect — it is the exact value of the `double` you handed it. The `double`
constructor is faithful; the `double` is the lie. Use `new BigDecimal(String)` or
`BigDecimal.valueOf`, which routes through `Double.toString` for the shortest round-tripping decimal.

> **Precision:** `BigDecimal` is exact for every operation except division, which throws rather than
> guess; minor-unit `long` is exact for addition and subtraction and truncates toward zero on
> division; `double` is exact for neither and never signals.


## Pitfalls

### Quoting a composite allocation figure without naming its basis

**Wrong**

```java
perOp("splitBigDecimal(stake)", n, 1, () -> splitBigDecimal(stake));
perOp("splitBigDecimal(Money.of(333, GBP))", n, 1, () -> splitBigDecimal(Money.of(333, GBP)));
```

```console
$ java -XX:-DoEscapeAnalysis AllocationHarness
splitBigDecimal(stake)                        384,000,000 B total     192.00 B/op  192.00 B/split
splitBigDecimal(Money.of(333, GBP))           512,000,000 B total     256.00 B/op  256.00 B/split
$ java AllocationHarness
splitBigDecimal(stake)                        304,000,000 B total     152.00 B/op  152.00 B/split
splitBigDecimal(Money.of(333, GBP))           432,000,000 B total     216.00 B/op  216.00 B/split
```

"A stake split costs 192 B." Four numbers, one operation, and all four are printed by the same
harness in the same session: 192, 256, 152, 216. Pick one and put it in a design document and it
will be contradicted by the next person who measures, who will conclude the first measurement was
wrong rather than differently based.

**Right**

State the basis with the number, every time, and prefer the ratio when comparing representations:

| Basis | `BigDecimal` | `long` | Ratio |
|---|---|---|---|
| Split alone, escape analysis off | 192 B | 72 B | 2.67× |
| Split plus input construction, escape analysis off | 256 B | 96 B | 2.67× |
| Split alone, default JIT | 152 B | 72 B | 2.11× |
| Split plus input construction, default JIT | 216 B | 72 B | 3.00× |

The ratio is stable at 2.67× across both like-for-like bases, which is the finding worth carrying.
The per-object figures — 40 B, 64 B, 24 B — need no basis, because a constructor has only one.

**Why people believe it:** because for a single object the question does not arise. `new
MoneyMinor(333, GBP)` is 24 B under every configuration and on every machine with compressed oops,
so "measure it and quote the number" is a habit that works perfectly right up to the first composite
operation. A composite figure is a sum over a region you chose, under a compiler configuration you
may not have chosen deliberately, and both choices move it.

### Calling `BigDecimal.divide` with neither a scale nor a `MathContext`

**Wrong**

```java
BigDecimal stake = new BigDecimal("3.33");
System.out.println("3.33 / 3 = " + stake.divide(new BigDecimal("3")));
System.out.println("3.33 / 7 = " + stake.divide(new BigDecimal("7")));
```

```console
3.33 / 3 = 1.11
java.lang.ArithmeticException: Non-terminating decimal expansion; no exact representable decimal result.
	at java.base/java.math.BigDecimal.divide(BigDecimal.java:1783)
	at Pitfalls.main(Pitfalls.java:26)
```

The first line succeeds, which is what makes this dangerous: the two-argument `divide` throws only
when the quotient has no terminating decimal expansion. A test suite built on divisors of 10 passes,
and the exception arrives the first time a stake is split seven ways.

**Right**

```java
BigDecimal stake = new BigDecimal("3.33");
BigDecimal share = stake.divide(new BigDecimal("7"), 2, RoundingMode.DOWN);
BigDecimal remainder = stake.subtract(share.multiply(new BigDecimal("7")));
System.out.println("share " + share + " x7, remainder " + remainder);
```

```console
share 0.47 x7, remainder 0.04
```

Pass a scale and a mode, then account for the remainder explicitly — the same shape as
`StakeSplit`'s "cash covers the remainder". `MathContext.DECIMAL64` also stops the exception but
gives 16 significant digits at scale 16, which is not a currency amount.

**Why people believe it:** because `add`, `subtract` and `multiply` are total functions on
`BigDecimal` and never throw, so `divide` looks like it should be too. It is the one arithmetic
method that can be handed a question with no exact answer, and the API's choice was to refuse rather
than silently pick a precision.

### Using `double` for an intermediate and `BigDecimal` for storage

**Wrong**

```java
for (long m = 105; m <= 995; m += 10) {
    BigDecimal exact = BigDecimal.valueOf(m, 2).multiply(new BigDecimal("0.10"));
    BigDecimal exactHalfUp = exact.setScale(2, RoundingMode.HALF_UP);
    double d = (m / 100.0) * 0.10;
    BigDecimal doubleHalfUp = new BigDecimal(d).setScale(2, RoundingMode.HALF_UP);
    if (exactHalfUp.compareTo(doubleHalfUp) != 0) {
        System.out.println("stake " + BigDecimal.valueOf(m, 2) + " exact " + exact
                + " -> HALF_UP " + exactHalfUp + " | double " + new BigDecimal(d)
                + " -> HALF_UP " + doubleHalfUp);
    }
}
```

```console
stake 1.15 exact 0.1150 -> HALF_UP 0.12 | double 0.1149999999999999911182158029987476766109466552734375 -> HALF_UP 0.11
stake 1.45 exact 0.1450 -> HALF_UP 0.15 | double 0.1449999999999999900079927783735911361873149871826171875 -> HALF_UP 0.14
stake 2.05 exact 0.2050 -> HALF_UP 0.21 | double 0.2049999999999999877875467291232780553400516510009765625 -> HALF_UP 0.20
stake 9.85 exact 0.9850 -> HALF_UP 0.99 | double 0.98499999999999998667732370449812151491641998291015625 -> HALF_UP 0.98
stake 9.95 exact 0.9950 -> HALF_UP 1.00 | double 0.99499999999999999555910790149937383830547332763671875 -> HALF_UP 0.99
```

Seventeen of the ninety stakes in that range round differently once a `double` carries the
intermediate, and those are five of them. The `double` product lands just *below* the exact
half-minor-unit rather than on it, so the tie never fires and `HALF_UP` silently behaves as `DOWN`.
On other stakes the `double` lands just above and the error flips sign, which is why no test suite
finds it and no reconciliation can predict it.

**Right**

```java
BigDecimal stakeAmount = new BigDecimal("3.35");
BigDecimal bonus = stakeAmount.multiply(new BigDecimal("0.10")).setScale(2, RoundingMode.DOWN);
System.out.println("exact product: " + stakeAmount.multiply(new BigDecimal("0.10")));
System.out.println("bonus        : " + bonus);
```

```console
exact product: 0.3350
bonus        : 0.33
```

The value enters as a decimal string, stays decimal through the multiply, and the only rounding is
the one you asked for at the scale you named. No `double` touches it.

**Why people believe it:** because the storage type is what appears in the schema and the API, so
"we use `BigDecimal` for money" feels like the box is ticked. The rounding decision is made by
whatever computed the value, not by whatever stores it, and a `double` intermediate has already
chosen a wrong value before `BigDecimal` sees it. `new BigDecimal(double)` is faithful to that wrong
value, which is why its output looks alarming and gets blamed on `BigDecimal`.

## Cheat sheet

| Fact | Value |
|---|---|
| `BigDecimal` instance | 12 header + 4 `intVal` + 4 `scale` + 4 `precision` + 4 `stringCache` + 8 `intCompact` = 36 → **40 B** |
| `Money(BigDecimal, Currency)` | 24 B record + 40 B `BigDecimal` = **64 B**; `Currency` interned, not charged |
| `MoneyMinor(long, Currency)` | 12 + 8 + 4 = **24 B** exactly |
| `StakeSplit`, `StakeSplitMinor` | 12 + 4 + 4 = 20 → **24 B** |
| Split alone, escape analysis off | **192 B** vs **72 B**, ratio **2.67×** |
| Split plus input construction, escape analysis off | **256 B** vs **96 B**, ratio **2.67×** |
| Split alone, default JIT | **152 B** vs **72 B**, ratio 2.11× |
| Split plus input construction, default JIT | **216 B** vs **72 B**, ratio 3.00× |
| Rule | a composite allocation figure without its basis is a number, not a measurement |
| 2.8M splits/day, split-alone basis | 537.6 MB/day vs 201.6 MB/day; difference 336 MB/day = 3.9 kB/s |
| What that costs | young-generation churn only; nothing survives, so it decides nothing |
| Why `BigDecimal` costs more | immutability: three arithmetic steps, three new objects — not object width |
| `divide`, no scale, no `MathContext` | `ArithmeticException: Non-terminating decimal expansion` |
| `multiply` scale | sum of operand scales; 3.33 × 0.10 = 0.3330 at scale 4 |
| `1/3` at scale 2 `HALF_EVEN`, at `DECIMAL64` | 0.33; 0.3333333333333333 at scale **16** |
| Java integer division | truncates toward zero: `DOWN` for positives, `UP` for negatives |
| `333 / 10`, `335 / 10`, `-335 / 10` | 33, 33, −33 minor units |
| `0.1 + 0.2` | `0.30000000000000004`; `== 0.3` is false |
| 3,100 `double` bonus grants of 10% of 4.20 | 1302.0000000000045 against an exact 1302.00; error 4.5E-12 |
| 1M `double` additions of 0.01 | 10000.000000171856; drift 1.71856E-7 |
| `new BigDecimal(0.1)` | `0.1000000000000000055511151231257827021181583404541015625` — faithful to the `double` |
| Use instead | `new BigDecimal(String)` or `BigDecimal.valueOf` |
| Not JMH | no forking, no `Blackhole`, no variance estimate; ratios within one run only |

## Self-test

**Q1.** A colleague measures `MoneyMinor` construction at 24 B and a full `BigDecimal` split at
152 B under the default JIT, and concludes the `BigDecimal` path costs 6.3× as much. Name both
errors and give the right pair of numbers.

<details><summary>Answer</summary>

First, 24 B is a construction and 152 B a whole split, so the comparison is between different
operations; the like-for-like `long` split is 72 B, giving 152 / 72 = 2.11×. Second, 152 B is a
default-JIT figure that already has one 40 B `BigDecimal` deleted by scalar replacement — with
`-XX:-DoEscapeAnalysis` the split is 192 B and the ratio is 2.67×. Present both configurations
labelled, and note that the default-JIT figure describes what one monomorphic call site in a hot
loop got away with rather than what the representation costs.

</details>

**Q2.** Four figures have been measured for "one stake split" on the same JDK: 272 B, 256 B, 192 B
and 152 B. Explain how all four can be correct.

<details><summary>Answer</summary>

They differ on two independent choices of basis. The first is what the measured region contains: a
split from a pre-built `Money` allocates 192 B, while a split that also constructs its input
allocates one more `BigDecimal` and one more `Money`, 40 + 24 = 64 B more, giving 256 B. The second
is the compiler configuration: with escape analysis on, C2 scalar-replaces the one `BigDecimal` that
never escapes, taking 192 B to 152 B and 256 B to 216 B. 272 B is a fifth basis with a different
intermediate count that this file could not reproduce and reports as such.

The per-object figures do not have this problem: a constructor has exactly one basis, so 40 B, 64 B
and 24 B reproduce identically everywhere. The right practice is to quote a composite figure only
with its basis, and to prefer the ratio when the point is a comparison — 2.67× holds on both
like-for-like bases.

</details>

**Q3.** Why does `BigDecimal.ONE.divide(new BigDecimal("3"))` throw while
`new BigDecimal("3.33").divide(new BigDecimal("3"))` returns 1.11?

<details><summary>Answer</summary>

The two-argument `divide` computes the exact quotient and throws only if the decimal expansion does
not terminate. 1/3 is 0.333 recurring, so it throws `ArithmeticException: Non-terminating decimal
expansion; no exact representable decimal result.` 3.33/3 is exactly 1.11, so it returns quietly.
That is what makes it dangerous: the failure depends on the *values*, not the code, so a test suite
built on values that divide evenly passes and the exception arrives in production. Pass a scale and
a `RoundingMode`, and account for the remainder separately.

</details>

**Q4.** `splitMinor(stakeMinor)` allocates 72 B under both JIT configurations, but
`splitMinor(new MoneyMinor(333, GBP))` allocates 96 B with escape analysis off and 72 B with it on.
Why the asymmetry, and what does it tell you about quoting default-JIT figures?

<details><summary>Answer</summary>

In the first form all three objects — the bonus `MoneyMinor`, the cash `MoneyMinor` and the
`StakeSplitMinor` — are reachable from the return value, so they escape and must be allocated no
matter what C2 proves. In the second form there is a fourth object, the temporary input
`MoneyMinor`, and after inlining it is consumed entirely inside the callee and never escapes, so C2
scalar-replaces it and its 24 B disappears.

The lesson is that scalar replacement is a *per-call-site* optimisation contingent on inlining, and
a microbenchmark's call site is the most optimisable one that will ever exist. Put the split behind
an interface with three implementations so the site goes megamorphic, or call it cold, and the 24 B
comes back. The `-XX:-DoEscapeAnalysis` figure is what the representation costs; the default-JIT
figure is what one call site got away with. Report both.

</details>

**Q5.** The `BigDecimal` split allocates 336 MB/day more than the `long` split at QuizStakes' volume.
Why is that not an argument for the `long` representation?

<details><summary>Answer</summary>

Because none of it is heap growth. A `StakeSplit` is dead microseconds after the reservation reaches
the ledger, so every byte dies in the young generation, and the cost of a young collection is
proportional to what **survives**, not to what was allocated. 336 MB/day is 3.9 kB/s averaged, and
230 kB/s at the 1,200/sec peak — a handful of extra minor collections against a multi-gigabyte young
generation.

The figure that could decide a design is allocation rate at peak on the hottest path, and 2.8M
splits a day does not get there. Choose the representation on precision and API clarity; the
allocation figure is a tiebreaker at best. Anyone presenting 2.67× as the deciding argument has
measured a real thing and drawn an unsupported conclusion from it.

</details>

**Q6.** Why is `new BigDecimal(0.1)` printing
`0.1000000000000000055511151231257827021181583404541015625` not a `BigDecimal` bug?

<details><summary>Answer</summary>

Because that is the exact value of the `double` literal `0.1`. A `double` is base 2, and 0.1 has no
finite binary expansion, so the nearest representable `double` is that long decimal. The `double`
constructor of `BigDecimal` is documented to be exactly faithful to the bits it is handed, so it
prints what the `double` actually is rather than what the source text looked like. The `double` is
the lie; `BigDecimal` is the only thing in the chain telling the truth.

Use `new BigDecimal("0.1")`, which parses the decimal text, or `BigDecimal.valueOf(0.1)`, which
routes through `Double.toString` and yields the shortest decimal that round-trips to the same
`double` — 0.1. The faithful constructor is still the right default for the JDK, because a lossy one
would hide exactly the error you need to see.

</details>

## Open questions

- **Unverified:** attributing the 40 B saved under the default JIT specifically to the `multiply`
  result being scalar-replaced. It follows from the delta being exactly one `BigDecimal` and that
  object being the only non-escaping one, but `-XX:+PrintEliminateAllocations` is `notproduct` and
  refuses to start on a product JVM. A fastdebug JDK 21 build would settle it directly.
- The commissioned composite figure of 272 B per `BigDecimal` split, and its 3.78× ratio, did not
  reproduce on any basis this file could construct; the closest is 256 B for split-plus-input with
  escape analysis off. The exact `splitBigDecimal` source those figures came from would settle it,
  and the per-object figures agree everywhere, so the discrepancy is confined to the intermediate
  count inside the measured region.

---

**Leaves covered:** 4.7.3 (allocation and precision half; the rounding-bias half is in
[04e-rounding-bias-experiment.md](04e-rounding-bias-experiment.md))
**Leaves deferred:** none
**Diagrams included:** none
**Target version:** Java 21 LTS
**Lines:** 749
