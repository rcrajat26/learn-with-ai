# 03 Java Core — `Double.compare`, NaN, and the `float`-versus-`double` choice — INTERMEDIATE (§2.4, 2.4.5–2.4.6)

**Target version: Java 21 LTS.** | **Part 2 of 5** | [Index](../00-index.md)
Previous: [Numbers: floating point in the money layer](02-numbers-and-money.md) · Next: [BigDecimal structure and construction](02a-bigdecimal-structure-and-construction.md)

This file continues §2.4's floating-point half of the money layer.
`02-numbers-and-money.md` owns why `double` cannot exactly hold 0.1, the
error that accumulates across a stream of additions, and why a fixed epsilon
comparison is mathematically unsound. This file owns what is left of §2.4:
the three-way disagreement between `==`, `equals` and `Double.compare` on
`NaN` and signed zero, and the `float`-versus-`double` storage decision.

All measurements below are from Oracle JDK 21.0.7 (build 21.0.7+8-LTS-245),
macOS aarch64 (Apple Silicon), compiled and run in a scratch directory under
`/tmp/`.

This file carries no diagram. `02-numbers-and-money.md` owns D-071 (why
`double` cannot hold 0.1), and `04a-internals-ulp-rounding-and-tostring.md`
owns D-126 (the ulp-spacing curve).

---

## 1. `Double.compare` versus `<` and `==` (2.4.5)

`[TRAP]` `==`, `.equals`, and `Double.compare` disagree with each other on two
specific inputs — `NaN` and signed zero — and the disagreement is not a bug in
any one of them: each was specified to satisfy a different contract.

### Why it exists

IEEE 754 defines `==` semantics so that `NaN` compares unequal to everything
including itself (a `NaN` means "the result of this computation is not a
number," and two unrelated not-a-number results should not be asserted
equal), and so that `+0.0 == -0.0` (they denote the same mathematical value,
zero, even though the sign bit differs). But `Object.equals` and
`Comparable.compareTo` have a different job: `equals`/`hashCode` must be
consistent so that `HashMap`/`HashSet` behave correctly, and `compareTo` must
impose a *total order* so a `TreeMap`/`TreeSet` never has two elements that
are simultaneously "less than" each other or where sort order is undefined.
IEEE 754's `NaN != NaN` and `0.0 == -0.0` are incompatible with a total order
(a total order needs every element to equal itself, and needs distinguishable
values to sort somewhere), so `Double.equals` and `Double.compare` were
deliberately specified to disagree with raw IEEE `==`.

### How it works

`[NUM]` Measured, JDK 21.0.7:

```
Double.NaN == Double.NaN                                    -> false
Double.valueOf(NaN).equals(Double.valueOf(NaN))              -> true
Double.compare(Double.NaN, Double.POSITIVE_INFINITY)         ->  1

0.0 == -0.0                                                  -> true
Double.compare(0.0, -0.0)                                    ->  1
Double.valueOf(0.0).equals(Double.valueOf(-0.0))             -> false

Double.doubleToLongBits(0.0)   = 0x0
Double.doubleToLongBits(-0.0)  = 0x8000000000000000
```

The bits make the disagreement mechanical, not mysterious: `0.0` and `-0.0`
are different bit patterns (`0x0` versus `0x8000000000000000`, differing only
in the sign bit), so anything that compares bit-pattern-derived identity —
`equals`, which is specified in terms of `doubleToLongBits` — sees them as
different objects entirely, while IEEE `==` is specified to treat all zeros
as equal regardless of sign. `Double.compare` treats `-0.0` as *less than*
`0.0` (hence `Double.compare(0.0, -0.0) = 1`, meaning `0.0` sorts after
`-0.0`) precisely so that a total order exists: it needs some fixed answer
for every pair, and IEEE `==` refuses to give one since it says they're
equal, so `compare` picks a convention. Likewise `Double.compare` places
`NaN` as greater than every other value including `POSITIVE_INFINITY` (hence
the `1`), giving `NaN` a fixed slot at the top of the order — again solving a
problem IEEE `==` refuses to solve, since IEEE `==` says `NaN` compares false
against everything, including itself.

| Comparison | `NaN` vs `NaN` | `0.0` vs `-0.0` | ordinary values (e.g. `4.20` vs `5.10`) |
|---|---|---|---|
| `==` (IEEE 754 semantics) | `false` | `true` | ordinary numeric comparison |
| `Double.valueOf(x).equals(y)` | `true` | `false` | matches `==` for non-zero, non-NaN values |
| `Double.compare(x, y)` | returns `1`: `NaN` sorts as greatest | returns `1`: `0.0` sorts after `-0.0` | matches `==`-derived ordering |

A `TreeMap<Double, Movement>` keyed by an unusual value like a bonus balance
of `NaN` (which should never legitimately occur, but must not corrupt the
tree if it does) relies on `compareTo`/`Double.compare` giving `NaN` a fixed,
consistent position; using `<`/`>` for that comparison would leave every
comparison against `NaN` returning `false`, which is not a valid total order
and would corrupt the tree's invariants.

**Pitfall: "`==` and `Double.compare` always agree, so it doesn't matter which
one I reach for."**

**Wrong**

```java
double reservedBonus = 0.0 / 0.0; // NaN, e.g. from a corrupted 0/0 stake ratio
if (reservedBonus == Double.NaN) {
    throw new LedgerImbalanceException("bonus balance is NaN");
}
// falls through: the == check silently never fires, NaN propagates downstream
```

Measured: `reservedBonus == Double.NaN` is `false` even though
`reservedBonus` genuinely holds `NaN`, because IEEE `==` specifies that `NaN`
compares unequal to everything, itself included — the guard never trips and a
corrupted balance flows into the ledger undetected.

**Right**

```java
double reservedBonus = 0.0 / 0.0;
if (Double.isNaN(reservedBonus)) {
    throw new LedgerImbalanceException("bonus balance is NaN");
}
```

`Double.isNaN` checks the bit pattern directly (any exponent of all-1-bits
with a nonzero mantissa) rather than relying on IEEE equality, so it reliably
detects `NaN` regardless of the comparison operator pitfall above.

**Why people believe it:** `==` "just works" for every other primitive
double-precision comparison a working engineer writes day to day — ordinary
finite values compare exactly the way intuition expects — so there is no
everyday feedback teaching that `NaN` and signed zero are special-cased by
the IEEE spec itself, not by Java.

---

## 2. `float` versus `double` (2.4.6)

Picture halving the register width: `float` is IEEE 754 binary32, 4 bytes
with 23 explicit mantissa bits, against `double`'s 8 bytes and 52 explicit
mantissa bits. Every one of the precision problems from `02-numbers-and-money.md`
exists for `float` too, and is roughly nine orders of magnitude worse.

### Why it exists

`float` predates ubiquitous 64-bit hardware and wide memory budgets — packing
twice as many values into a cache line or a large array mattered when memory
was the scarce resource. On modern JVMs, arithmetic on `float` and `double`
costs about the same per operation (both use the FPU's native paths), so the
only remaining argument for `float` is raw storage density in very large
arrays.

### How it works — the measured gap

```
(double) 0.1f                = 0.10000000149011612
new BigDecimal((double)0.1f) = 0.100000001490116119384765625
   ^ float -> double widening is EXACT: it reproduces exactly the value the
     float held, which was never 0.1. The widening loses nothing; it just
     reveals how much less precise 0.1f already was compared to 0.1d.

(float) 0.1d       = 0.1        (Float.toString prints the shortest round-tripping
                                  string for a float, which happens to be "0.1")
(float) 1e40       = Infinity   (overflow: exceeds Float.MAX_VALUE)
(float) 1e-50      = 0.0        (underflow: below what a float can represent, even subnormal)

(float) 16777217     = 1.6777216E7
(int)(float) 16777217 = 16777216
   ^ 16777217 = 2^24 + 1 is the first int a float cannot represent exactly:
     float has 23 explicit mantissa bits (24 bits of precision with the
     implicit leading bit), so it can represent every integer up to 2^24
     exactly, but 2^24 + 1 needs a 25th bit of precision it does not have.
     The round trip through float silently loses the +1.

Math.ulp(1.0f) = 1.1920929E-7
Math.ulp(1.0)  = 2.220446049250313E-16
   ^ ratio: 1.1920929E-7 / 2.220446049250313E-16 ~= 536,870,912, i.e. about
     nine orders of magnitude (2^29) coarser spacing at the same nominal
     value 1.0.
```

`[NUM]` Every one of those figures is measured on this build (Oracle JDK
21.0.7), from the brief's §6.4.

| Property | `float` (binary32) | `double` (binary64) |
|---|---|---|
| Storage | 4 bytes | 8 bytes |
| Explicit mantissa bits | 23 | 52 |
| `Math.ulp(1.0)` | `1.1920929E-7` | `2.220446049250313E-16` |
| Largest exactly-representable consecutive integer | `2^24` (16,777,216) | `2^53` (9,007,199,254,740,992) |
| `MIN_VALUE` (smallest positive subnormal) | `1.4E-45` | `4.9E-324` |
| Arithmetic cost on a modern JIT | comparable per-op to `double` | comparable per-op to `float` |

### When to reach for it, and when not

The QuizStakes verdict: never use `float` for anything that is computed,
compared, or persisted as money or as a decision input — the precision loss
above is strictly worse than `double`'s while buying no speed advantage on
current hardware. The only legitimate case is storage density in an array
large enough that halving 8 bytes to 4 changes whether the data fits in
memory or in a cache tier at all. At QuizStakes's measured ~19.8M ledger
entries/day, that is a storage argument, not an arithmetic one — and the
ledger's actual money fields are `BigDecimal`, not `float` or `double`,
specifically to avoid this whole question.

**Gotcha:** widening `float` to `double` is always exact (it is a strict
superset of representable precision), but it never recovers precision the
`float` never had — `(double) 0.1f` proves this: the widened value still
shows the `float`'s own rounding error to more decimal places, it does not
become `0.1`.

Primitive `float`/`double` language-level semantics and the IEEE 754 layout
diagram (D-009) belong to `../primitives-and-conversions/01c-floating-point.md`;
binary64 internals, denormals, `Double.toString`'s algorithm and `strictfp`
belong to `04-internals-floating-point.md`.

**Interview:** "When would you use `float` instead of `double`?" — almost
never; the only defensible case is memory pressure in a very large array
where halving per-element storage changes a capacity or cache-fit decision,
and even then only for values where the precision loss is provably tolerable,
which money never is.

> **`float` halves both the storage and the precision of `double`; the
> precision loss buys no speed advantage on modern hardware, so the only
> legitimate reason to choose it is array storage density at scale, never
> arithmetic quality.**

---

## Pitfalls

### "`==` and `Double.compare` always agree, so it doesn't matter which I use."

**Wrong**

```java
double reservedBonus = 0.0 / 0.0; // NaN
if (reservedBonus == Double.NaN) {
    throw new LedgerImbalanceException("bonus balance is NaN");
}
```

Measured: the `==` check never throws, even though `reservedBonus` is
genuinely `NaN`, because IEEE 754 `==` specifies that `NaN` compares unequal
to everything including itself (`Double.NaN == Double.NaN` measures `false`).

**Right**

```java
double reservedBonus = 0.0 / 0.0;
if (Double.isNaN(reservedBonus)) {
    throw new LedgerImbalanceException("bonus balance is NaN");
}
```

`Double.isNaN` inspects the bit pattern (all-ones exponent, nonzero
mantissa) directly rather than relying on an equality operator whose IEEE
semantics were never designed to detect `NaN` at all.

**Why people believe it:** `==` behaves exactly as expected for every
ordinary finite double comparison an engineer writes day to day, so there is
no routine feedback exposing that `NaN` and signed zero are IEEE-754
special cases carved out of ordinary equality on purpose.

### "Storing `0.0` and `-0.0` in a `Set<Double>` of settled bonus balances dedupes them, since `0.0 == -0.0`."

**Wrong**

```java
Set<Double> settledBalances = new HashSet<>();
settledBalances.add(0.0);
settledBalances.add(-0.0);
System.out.println(settledBalances.size());
```

Measured: this prints `2`, not `1`. `HashSet` uses `equals`/`hashCode`, not
`==`, and `Double.valueOf(0.0).equals(Double.valueOf(-0.0))` measures
`false` because `equals` is specified in terms of `doubleToLongBits`, which
gives `0.0` and `-0.0` different bit patterns (`0x0` versus
`0x8000000000000000`) even though IEEE `==` treats them as the same value.
A settlement job that assumes a zeroed-out `BonusService` balance always
dedupes against a residual `-0.0` left over from an earlier `0.0 - x`
subtraction will silently carry two "distinct" zero entries.

**Right**

```java
Set<Double> settledBalances = new HashSet<>();
settledBalances.add(normalizeZero(0.0));
settledBalances.add(normalizeZero(-0.0));
System.out.println(settledBalances.size()); // 1

static double normalizeZero(double value) {
    return value == 0.0 ? 0.0 : value;
}
```

Normalizing every zero to a canonical positive `0.0` before it enters a
hash-based collection makes `equals`/`hashCode` agree with the IEEE `==`
notion that all zeros are the same value — or, for anything that is actually
money, use `BigDecimal` and this question does not arise, since `BigDecimal`
has no signed-zero bit pattern to disagree about.

**Why people believe it:** engineers correctly remember that `0.0 == -0.0`
is `true` and assume every other equality-flavored check in the language
agrees with `==`, not realizing `equals`/`hashCode` are specified against
the bit pattern rather than the IEEE comparison operator.

### "Sorting a `List<Double>` of affordability scores with a hand-rolled `<`/`>` comparator is fine as long as `Collections.sort` is used."

**Wrong**

```java
List<Double> affordabilityScores = new ArrayList<>(List.of(4.20, Double.NaN, 65.0, 260.0));
affordabilityScores.sort((a, b) -> a < b ? -1 : (a > b ? 1 : 0));
```

Measured: for any pair involving the `NaN` score (e.g. a corrupted
affordability calculation), both `a < b` and `a > b` evaluate `false` under
IEEE 754 semantics, so the comparator returns `0` — claiming `NaN` is "equal"
to every other score. That violates the transitivity a sort algorithm relies
on, and on a large enough list this comparator can throw
`IllegalArgumentException: Comparison method violates its general contract!`
from TimSort's internal consistency check, or silently produce an
inconsistently ordered list when the list is short enough not to trip the
check.

**Right**

```java
affordabilityScores.sort(Double::compare);
```

`Double.compare` gives `NaN` a fixed, total-order position — greater than
every other value including `POSITIVE_INFINITY` — so every pair has a
consistent, transitive answer and TimSort's invariants hold regardless of
how many `NaN` scores are present.

**Why people believe it:** `<` and `>` are the natural, familiar way to write
a comparator, and they are completely correct for a list with no `NaN` or
signed-zero values in it — the failure only appears once a genuinely
corrupted or missing score enters the data, which is easy to never test for.

---

## Cheat sheet

| Thing | Fact (Java 21 LTS) |
|---|---|
| `Double.NaN == Double.NaN` | `false` |
| `Double.valueOf(NaN).equals(Double.valueOf(NaN))` | `true` |
| `Double.compare(NaN, POSITIVE_INFINITY)` | `1` (`NaN` sorts greatest) |
| `0.0 == -0.0` | `true` |
| `Double.compare(0.0, -0.0)` | `1` (`0.0` sorts after `-0.0`) |
| `Double.valueOf(0.0).equals(Double.valueOf(-0.0))` | `false` |
| `Double.doubleToLongBits(0.0)` vs `(-0.0)` | `0x0` vs `0x8000000000000000` |
| Why `compareTo` disagrees with `==` | `Comparable` needs a total order; IEEE `==` refuses to give `NaN` and signed zero one |
| Reliable NaN check | `Double.isNaN(x)`, never `x == Double.NaN` |
| Safe comparator for a list that may contain NaN | `Double::compare`, never a hand-rolled `<`/`>` comparator |
| `float` explicit mantissa bits | 23, vs `double`'s 52 |
| `float` storage | 4 bytes, vs `double`'s 8 |
| `Math.ulp(1.0f)` vs `Math.ulp(1.0)` | `1.1920929E-7` vs `2.220446049250313E-16` — about nine orders of magnitude coarser |
| First `int` a `float` cannot represent exactly | `2^24 + 1 = 16777217`; `(float) 16777217` = `1.6777216E7`, round trip loses 1 |
| `(double) 0.1f` | `0.10000000149011612` — widening is exact, exposing the float's own imprecision |
| `(float) 1e40` | `Infinity` (overflow) |
| `(float) 1e-50` | `0.0` (underflow) |
| When `float` is defensible | array storage density at large scale only, never arithmetic quality |
| QuizStakes rule | `float` never for money; `BigDecimal` for every `Money` field |

---

## Self-test

**Q1.** `Double.NaN == Double.NaN` is `false`, but `Double.valueOf(Double.NaN).equals(Double.valueOf(Double.NaN))` is `true`. Explain the discrepancy.

<details><summary>Answer</summary>

`==` follows IEEE 754 semantics, which specify that `NaN` compares unequal to
every value including itself, since a `NaN` represents "not a number" and two
unrelated invalid results should not be asserted equal. `Double.equals` has a
different job: `Object.equals`/`hashCode` must be internally consistent so
hash-based collections work correctly, and IEEE `NaN != NaN` would break
that — a `HashSet` could never find a `NaN` it just inserted. So
`Double.equals` is specified in terms of `doubleToLongBits`, which maps every
`NaN` bit pattern to a single canonical representation and compares those,
giving `true` for `NaN` against `NaN`. The two methods are deliberately
different because they serve different contracts.

</details>

**Q2.** Why does `Double.compare(0.0, -0.0)` return `1` when `0.0 == -0.0` is `true`?

<details><summary>Answer</summary>

`0.0` and `-0.0` have different bit patterns (`0x0` versus
`0x8000000000000000`, differing only in the sign bit), and IEEE `==`
specifies they should compare equal since they denote the same mathematical
value, zero. But `Comparable.compareTo` must impose a strict total order for
things like `TreeMap` to work correctly, and a total order requires a
consistent, fixed answer for every pair — it cannot rely on IEEE `==`'s
"they're equal" answer here without contradicting the fact that they are
distinguishable bit patterns. `Double.compare` picks a convention: `-0.0` is
treated as less than `0.0`, so `Double.compare(0.0, -0.0)` returns a positive
number.

</details>

**Q3.** Give the QuizStakes rule for when `float` is acceptable, and justify it with the measured numbers.

<details><summary>Answer</summary>

Never for money or for anything computed or compared — the only legitimate
case is storage density in an array so large that halving 8 bytes to 4
changes whether the data fits in available memory. The precision case
against `float` is stark: it has 23 explicit mantissa bits against `double`'s
52, `Math.ulp(1.0f)` is `1.1920929E-7` against `Math.ulp(1.0)`'s
`2.220446049250313E-16` — about nine orders of magnitude coarser — and it
cannot even represent every integer past `2^24 + 1 = 16777217` exactly
(`(float) 16777217` prints `1.6777216E7`, silently losing the `+1`). None of
this buys a speed advantage on modern hardware, since `float` and `double`
arithmetic cost about the same per operation on a current JIT, so the only
remaining reason to reach for `float` is the storage argument, which at
QuizStakes's scale is about array capacity, never arithmetic.

</details>

**Q4.** What does `(double) 0.1f` demonstrate, and why does the value it produces matter?

<details><summary>Answer</summary>

`(double) 0.1f` measures `0.10000000149011612`. Widening a `float` to a
`double` is an exact operation — it introduces no new error, it exactly
reproduces the value the `float` already held. The fact that the widened
value is not `0.1` proves the `float` literal `0.1f` was already a worse
approximation of 0.1 than the `double` literal `0.1` is; the widening merely
makes that pre-existing imprecision visible at higher decimal resolution
rather than hiding it, since `float` has far fewer mantissa bits to spend on
the same repeating binary expansion problem that `02-numbers-and-money.md`
derives for 0.1.

</details>

**Q5.** Why can a hand-rolled comparator using `<` and `>` throw `IllegalArgumentException: Comparison method violates its general contract!` when sorting a `List<Double>`, and what fixes it?

<details><summary>Answer</summary>

Under IEEE 754 semantics, both `a < b` and `a > b` evaluate `false` whenever
either operand is `NaN`, so a comparator written as
`(a, b) -> a < b ? -1 : (a > b ? 1 : 0)` returns `0` for every pair involving
a `NaN` value — claiming `NaN` is "equal" to everything, including values it
is not equal to in any consistent sense. That breaks the transitivity
`Collections.sort`/`Arrays.sort` (TimSort) assumes, and TimSort's internal
consistency check can detect the contradiction on a sufficiently large input
and throw rather than silently misorder the list. The fix is to use
`Double.compare` (directly, or via `Double::compare` as the comparator),
which gives `NaN` a fixed, total-order position — greater than every other
value — so every pairwise comparison is consistent regardless of how many
`NaN` values are present.

</details>

---

## Open questions

None. Every claim above traces to the brief's §6.1–§6.5, or to the JDK 21
source, or is a derivation worked on the page.

---

**Leaves covered:** 2.4.5, 2.4.6 (2 leaves)
**Leaves deferred:** none
**Diagrams included:** none
**Target version:** Java 21 LTS
**Lines:** 467
