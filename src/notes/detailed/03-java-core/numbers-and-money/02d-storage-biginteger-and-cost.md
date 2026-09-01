# 03 Java Core — Money in storage, `BigInteger`, and what exactness costs — INTERMEDIATE (§2.4, 2.4.20–2.4.22)

**Target version: Java 21 LTS.** | **Part 2 of 5** | [Index](../00-index.md)
Previous: [MathContext, the constants, and a Money type](02c-mathcontext-constants-and-minor-units.md) · Next: [Parsing and formatting numbers](02e-parsing-and-formatting-numbers.md)

This file owns three things: how a `BigDecimal`'s exactness maps onto a SQL
column and what JDBC/JPA do at that boundary; `BigInteger`'s shape and its
number-theoretic API, including where RSA actually calls it; and a measured
correction to the folk claim that `BigDecimal` is "10-100x slower" than a
primitive. `02a` owns `BigDecimal`'s own internal fields; this file only reuses
them. No diagram belongs to this file — the pictures for adjacent material
live in `02b-equality-scale-and-rounding.md` (D-073, D-074) and
`03-internals-bigdecimal.md` (D-125). All measurements below were taken on
Oracle JDK 21.0.7 (build 21.0.7+8-LTS-245), macOS aarch64, with library source
quoted from that build's `lib/src.zip`.

---

## 1. Money in the database (2.4.20)

A SQL `NUMERIC(p,s)` column and a `BigDecimal` are the same idea told twice: an
exact integer significand plus a fixed scale, stored so no bit pattern ever has
to approximate a fraction it cannot represent. `DOUBLE PRECISION` is IEEE 754
binary64 — the same lossy encoding `02-numbers-and-money.md` measured failing
to hold `0.1` exactly. Choosing a column type for money is therefore not a
storage-efficiency question at all; it is the same exactness question one
layer further down the stack, and it has the same answer.

### Why it exists

A schema designer who has never seen the `0.1` bit pattern reaches for
`DOUBLE PRECISION` because it is the default numeric type in most ORMs'
example code and it "just works" in a quick test with round numbers. The
failure only shows up once enough rows accumulate that the per-row error
compounds into a visible discrepancy — which in a ledger table is exactly the
`SUM()` query an auditor runs.

### How it works

| Column type | Exactness | Range | What breaks |
|---|---|---|---|
| `NUMERIC(19,4)` | Exact decimal | ±10^15 with 4 fractional digits | Nothing at ledger scale; the house standard |
| `NUMERIC(19,2)` | Exact decimal | ±10^17 with 2 fractional digits | No headroom for an intermediate rate or fee below the minor unit |
| `BIGINT` minor units | Exact integer | ±9.2×10^18 (`Long.MAX_VALUE`) | No native decimal point; every query must know the implicit scale |
| `DOUBLE PRECISION` | Lossy binary | ~15-17 significant decimal digits | `SUM()` over many rows drifts from the exact total, as measured below |

`19,4` specifically, not `19,2`: 19 digits is the widest precision that still
maps cleanly onto a `long`-backed decimal representation on most database
engines (PostgreSQL's `numeric` is arbitrary-precision regardless, but SQL
Server's and many others' fast paths top out near there), and 4 decimal places
leaves two spare digits below the minor unit. That headroom exists because
intermediate values — a bonus percentage applied before rounding, a
per-transaction fee computed as a rate — routinely need a third or fourth
decimal place before the final `setScale(2, RoundingMode.HALF_UP)` collapses
them to the minor unit. A column fixed at scale 2 forces that rounding into the column itself,
at write time, with no chance to defer it to the point the business rule
actually specifies. That is why financial schemas standardise on `NUMERIC(19,4)`
rather than on 2.

**`NUMERIC` versus `DOUBLE PRECISION`, self-contained (guide 09 — SQL
databases).** `NUMERIC`/`DECIMAL` is stored as an exact decimal significand and
scale, so a value written as `4.20` reads back as exactly `4.20` and `SUM()`
over 2.8M rows is exact. `DOUBLE PRECISION` accumulates the same error §6.12
measured in Java: 2,800,000 additions of `4.20` in a `double` gives
`1.1759999999664538E7` against an exact `11760000.00`, an error of
`-0.00033546`. The database engine's binary floating-point adder has the same
IEEE 754 rounding behaviour as Java's `double`, because both implement the same
standard — the error is not a Java quirk, it is what binary64 does to a decimal
fraction it cannot represent, and it happens again inside the database if the
column type is `DOUBLE PRECISION`. Guide 09 covers the full database-side
picture.

**JDBC and JPA mapping, self-contained (guide 08 — Spring Data JPA).** JDBC
maps `NUMERIC`/`DECIMAL` columns to `BigDecimal` through
`ResultSet.getBigDecimal`, and the scale that comes back on that `BigDecimal`
is the **column's declared scale**, not whatever scale the Java value carried
when it was written. A value written at scale 2 into a `NUMERIC(19,4)` column
reads back at scale 4 — and by `02b`'s rule (`equals` compares scale before
significand) that is a `BigDecimal` an `equals`-based unit-test assertion will
reject even though `compareTo` says they are the same amount. Two consequences
a JPA user meets directly: `@Column(precision = 19, scale = 4)` on the entity
field is what generates the matching DDL, so the column's scale is declared
once and cannot silently drift from what the entity expects; and
`getBigDecimal` never routes the value through a `double` at any point, so the
binary-floating-point error cannot enter through this path at all — the risk
JDBC removes is exactly the one `NUMERIC` versus `DOUBLE PRECISION` describes
above.

**Pitfall:** treating the round-trip scale change as a bug in the JDBC driver
rather than the column's declared behaviour is the single most common cause of
a passing unit test (comparing freshly-constructed `BigDecimal`s at the scale
the test author typed) and a failing integration test (comparing a value just
read back from the database, at the column's scale) on the same money value.

> A `NUMERIC(p,s)` column is a `BigDecimal` one layer down: an exact
> significand plus a fixed scale, and JDBC preserves that scale exactly as the
> column declares it — never as the Java value that was written.

---

## 2. `BigInteger` (2.4.21)

`BigInteger` is not a `BigDecimal` without the decimal point; it is sign and
magnitude, stored as a sign flag and an array of digit words with no fixed
width and no wraparound. Reach for the shape first: there is no bit pattern
that means "the largest value this type can hold," because the array simply
grows.

### Why it exists

`long` overflows silently past `Long.MAX_VALUE`; `int` overflows silently past
`Integer.MAX_VALUE`. Number theory — RSA key generation, factorial-scale
combinatorics, arbitrary-precision counters — needs integers with no such
ceiling, and needs them without the caller ever thinking about how many bits
are enough.

### How it works

The JDK 21 field declarations, verbatim from `lib/src.zip`,
`java.base/java/math/BigInteger.java`:

```java
final int signum;   // line 144
final int[] mag;    // line 155
```

`signum` is -1, 0, or 1 — sign-magnitude, not two's complement. `mag` holds the
magnitude big-endian (most significant `int` word first) with no leading zero
words. Because there is no fixed-width two's complement representation
underneath, there is no overflow in the `int`/`long` sense at all: an
operation that would overflow a fixed-width type instead reallocates `mag` one
word larger. The cost of arbitrary precision is paid in allocation, not in
wraparound bugs.

The number-theoretic API the leaf names:

| Method | Purpose | Rough cost |
|---|---|---|
| `mod(BigInteger)` | Non-negative remainder (unlike `%`, never negative) | One division |
| `modPow(exponent, modulus)` | Modular exponentiation, `this^exponent mod modulus` | Square-and-multiply, not naive exponentiation then reduction |
| `gcd(BigInteger)` | Greatest common divisor, binary GCD algorithm | Roughly linear in bit length |
| `isProbablePrime(certainty)` | Probabilistic primality test | Miller-Rabin rounds scaled by `certainty` |

**RSA and `modPow`, self-contained (guide 13 — Web security).** RSA's core
operation is modular exponentiation: encryption computes `c = m.modPow(e, n)`
and decryption computes `m = c.modPow(d, n)`, where `n` is the public modulus
and `e`/`d` are the public and private exponents. That is precisely why
`BigInteger` lives in `java.math` rather than in a crypto-specific package —
it is the general-purpose arbitrary-precision integer type, and RSA is simply
one consumer of `modPow` among many. `isProbablePrime` takes a `certainty`
argument rather than promising a definite answer because primality testing at
RSA key sizes (2048+ bits) is done with Miller-Rabin, a probabilistic
algorithm: each round either proves compositeness or leaves a bounded chance
the number is composite anyway, and `certainty` controls how many rounds run,
trading CPU time against that residual false-positive probability. Application
code should never hand-roll RSA on top of raw `BigInteger` calls — use
`java.security`'s `KeyPairGenerator`, `Cipher`, and `Signature`, which handle
padding schemes, side-channel mitigations, and key encoding that a direct
`modPow` call does none of. Guide 13 covers the application-security surface
in full.

Multiplication switches strategy by operand size — verbatim threshold
declarations from the same source file:

```java
private static final int KARATSUBA_THRESHOLD = 80;          // line 218
private static final int TOOM_COOK_THRESHOLD = 240;         // line 227
```

The thresholds are counted in `int` words of `mag`, so `KARATSUBA_THRESHOLD =
80` is 80 × 32 = 2,560 bits ≈ 771 decimal digits. Below 80 words: schoolbook
multiplication, O(n²). From 80 up to 240 words: Karatsuba, O(n^1.585). At 240
words or above: 3-way Toom-Cook, O(n^1.465). There is no Schönhage-Strassen or
FFT-based multiplication in the JDK — at sizes beyond Toom-Cook's advantage
(tens of thousands of digits), a specialised big-number library will
outperform `BigInteger`, but QuizStakes-scale money and even RSA-scale keys
never approach that regime. `03b-internals-biginteger-and-long-cents.md` owns
the full internals walk of these algorithms; this file stops at the shape and
the public API.

The `valueOf` cache, verbatim:

```java
private static final int MAX_CONSTANT = 16;
private static final BigInteger[] posConst = new BigInteger[MAX_CONSTANT+1];
private static final BigInteger[] negConst = new BigInteger[MAX_CONSTANT+1];
```

Measured consequence: `BigInteger.valueOf(16) == BigInteger.valueOf(16)` is
`true`; `BigInteger.valueOf(17) == BigInteger.valueOf(17)` is `false`. The
cache runs exactly -16..16 inclusive, and nowhere further.

**Pitfall:** `==` accidentally returns the right answer for every value inside
the cache, which is precisely how the belief that `==` works on `BigInteger`
at all survives code review — the bug only surfaces once a value outside
-16..16 reaches the comparison. `../wrappers-and-boxing/01-basics.md` owns the
identical pattern for `Integer.valueOf`'s -128..127 cache; the mechanism and
the trap are the same shape one type over.

> `BigInteger` is sign-magnitude with an unbounded `int[]` magnitude, so it
> never overflows the way `int`/`long` do — the cost of that guarantee is paid
> in reallocation, not in wraparound bugs, and its `valueOf` cache makes `==`
> work only for -16..16.

---

## 3. What exactness costs (2.4.22)

`[NUM]` — this leaf's own text says "10-100x slower," and the honest response
to that figure is to correct it with measurement, not repeat it.

### How it works

From §6.12, measured wall-clock loop timings (5,000,000 array elements, best
of 5 runs after 4 warmups — not JMH, no error bars, quoted as ratios on one
build):

| Operation | ns/op |
|---|---|
| `long` cents add | **0.26** |
| `double` add | **0.52** |
| `BigDecimal.add`, compact (`intVal == null`) | **2.24** |
| `BigDecimal.add`, `intVal` attached | **3.61** |
| full bonus split `multiply(0.10).setScale(2, DOWN)` | **10.17** |

`BigDecimal.add` on the compact path is **8.6x** a `long` add, not 10-100x, and
4.3x a `double` add. The attached-`intVal` form (constructed through
`new BigDecimal(BigInteger, int)` rather than `valueOf`) is **1.6x the compact
form for the identical value**, purely because that constructor never nulls
out `intVal` — the object permanently carries an attached `BigInteger` it
never needs for the compact fast path. The full bonus-split pipeline —
`multiply` then `setScale`, two allocations rather than one — is **10.17
ns/op, 39x** a `long` add. The honest statement: **8.6x for a single add on the
fast path**, tens of times for a pipeline that allocates intermediates, and the
"10-100x" figure is fair only for the inflated path or a multi-step
calculation, not for `BigDecimal` arithmetic in general. Quote the brief's own
caveat whenever citing these: they are wall-clock loop timings over a
pre-filled random array, best of 5 after 4 warmups, not JMH results, and carry
no error bars.

The allocation half matters more at QuizStakes scale than the per-operation
timing does. From §6.11, measured retained memory:

| Allocation | bytes/instance |
|---|---|
| `long` (baseline) | 8 |
| `BigDecimal.valueOf(i, 2)` (compact) | **40.0** |
| `new BigDecimal(BigInteger.valueOf(i), 2)` (attached) | **104.2** |
| `new BigDecimal(String)`, 30-digit, inflated | **112.0** |

`BigDecimal` is immutable (`02a`'s rule), so every operation in a pipeline
returns a new instance — a three-step calculation allocates three objects, not
one mutated in place. At QuizStakes' 19.8M ledger entries/day, one compact
`BigDecimal` per entry costs 19,800,000 × 40 ≈ 792 MB/day. Building that same
day's entries through `new BigDecimal(BigInteger, int)` instead of `valueOf` —
104 bytes instead of 40, a 64-byte-per-instance difference — costs
19,800,000 × 64 = 1,267,200,000 bytes ≈ **1.27 GB/day of pure waste**, with no
behavioural difference to show for it.

### When to reach for it, and when not

The house tradeoff rule: `BigDecimal` everywhere by default, because
correctness on money is not negotiable and 8.6x a `long` add is not a cost
that shows up in a profile until a genuinely hot loop exists. Minor-units
`long` only where a profiler has already shown this specific arithmetic to be
the bottleneck — and once switched, measure again afterwards, because the
`long` path trades exactness-by-construction for exactness-by-discipline
(`Math.multiplyExact`, explicit minor-unit bookkeeping) and a regression there
is silent, not an exception. `../cost-model/02-master-cost-table.md` owns the
topic-wide cost table this leaf's numbers feed into; guide 06 covers
allocation and escape analysis, the mechanism that decides whether a
short-lived `BigDecimal` in a hot loop can be stack-allocated at all under the
current JIT.

**Pitfall:** reading "8.6x" and concluding `BigDecimal` is now cheap enough to
stop worrying about allocation ignores that the 8.6x figure is per-operation
CPU cost on the compact fast path only — the 1.27 GB/day figure above comes
from the *same* leaf's allocation cost, which the CPU ratio says nothing
about, and a pipeline of several `BigDecimal` operations pays both costs at
once.

> `BigDecimal.add` costs 8.6x a `long` add on the compact fast path, not
> 10-100x — but every operation allocates a new immutable instance at 40-112
> bytes against 8 for a `long`, and that allocation cost, not the per-op CPU
> ratio, is what dominates at ledger scale.

---

## Pitfalls

### The JDBC round-trip preserves the Java value's scale, not the column's

**Wrong**

```java
BigDecimal deposit = new BigDecimal("4.20");
preparedStatement.setBigDecimal(1, deposit);
preparedStatement.executeUpdate();
// column is NUMERIC(19,4)

BigDecimal reread = resultSet.getBigDecimal("amount");
assertEquals(deposit, reread);   // deposit has scale 2
```

`reread` comes back at scale 4 (`4.2000`), because `getBigDecimal` returns a
value at the **column's** declared scale, not the scale the write used —
`assertEquals` fails, because `BigDecimal.equals` compares scale before
significand, exactly as `02b` measured for `2.0` versus `2.00`.

**Right**

```java
BigDecimal deposit = new BigDecimal("4.20");
preparedStatement.setBigDecimal(1, deposit);
preparedStatement.executeUpdate();

BigDecimal reread = resultSet.getBigDecimal("amount");
assertEquals(0, deposit.compareTo(reread));   // compareTo ignores scale
```

`compareTo` returns `0` for any two `BigDecimal`s of equal numeric value
regardless of scale, so it is the correct comparison across a JDBC round-trip
whenever the column's declared scale can differ from the value's own.

**Why people believe it:** `equals` is the default comparison reflex for every
other JDK value type, and a unit test written against freshly-constructed
`BigDecimal`s (both at the same scale, because the test author typed them the
same way) passes cleanly — the scale mismatch only appears once a real column
declaration is in the path, which a unit test typically is not.

### `new BigDecimal(BigInteger, int)` is assumed to be as cheap as `valueOf`

**Wrong**

```java
long minorUnits = 6500L;
BigDecimal amount = new BigDecimal(BigInteger.valueOf(minorUnits), 2);
```

This constructs a `BigDecimal` that permanently carries an attached
`BigInteger` — measured, 104.2 bytes retained against 40.0 bytes for the
equivalent `valueOf` call, and 3.61 ns/op for a subsequent `add` against 2.24
ns/op for the compact form, purely because `intVal` was never nulled out.

**Right**

```java
long minorUnits = 6500L;
BigDecimal amount = BigDecimal.valueOf(minorUnits, 2);
```

`valueOf(long, int)` produces the compact form directly — measured `intCompact
= 6500`, `intVal = null` — at 40.0 bytes and the 2.24 ns/op add cost, for the
identical numeric value `65.00`.

**Why people believe it:** `compactValFor` (§6.7) shows the constructor *does*
set `intCompact` correctly when the magnitude fits — so the belief that "it
must be just as cheap, since the fast-path field is populated either way" is
half right. What it misses is that the constructor never nulls `intVal`, so
the object still carries the full attached `BigInteger` and its backing
`int[] mag` permanently, and every future operation on that instance pays the
larger object's cost even though `intCompact` alone would have been enough.

### "`BigDecimal` is 10-100x slower than primitives" is taken as a per-operation fact

**Wrong**

```java
// "BigDecimal is 10-100x slower, so avoid it in any loop"
BigDecimal total = BigDecimal.ZERO;
for (BigDecimal stake : stakes) {
    total = total.add(stake);
}
```

Rewriting this to `long` cents purely on the strength of a blanket "10-100x"
figure treats a multi-step-pipeline number as if it applied to every
`BigDecimal` operation, including the single `add` in this loop.

**Right**

```java
// measured: BigDecimal.add on the compact path is 8.6x a long add, not 10-100x
BigDecimal total = BigDecimal.ZERO;
for (BigDecimal stake : stakes) {
    total = total.add(stake);   // 2.24 ns/op measured, versus 0.26 ns/op for long
}
```

The loop above stays on `BigDecimal` unless a profiler shows this specific
loop is the bottleneck — 8.6x on a fast path is rarely the dominant cost in a
request that also touches a database and a network call, and switching away
from `BigDecimal` trades away correctness-by-construction for a discipline the
next engineer to touch the code has to know to maintain.

**Why people believe it:** the "10-100x" figure is real for the inflated path
and for a multi-step pipeline like `multiply` then `setScale` (measured 39x),
so the number is not fabricated — it is simply quoted without saying which
`BigDecimal` operation it describes, and a blanket "avoid `BigDecimal` in
loops" rule then gets applied to every operation indiscriminately, including
the cheap ones.

---

## Cheat sheet

| Thing | Fact (Java 21 LTS) |
|---|---|
| `NUMERIC(19,4)` vs `BigDecimal` | Same idea: exact significand + fixed scale, stored |
| `DOUBLE PRECISION` for money | Lossy binary64; measured 2.8M × 4.20 sums to `-0.00033546` error |
| Why 19,4 not 19,2 | 19 digits fits `long`-backed engines; scale 4 leaves 2 spare digits below the minor unit |
| `getBigDecimal` scale | Comes back at the **column's** declared scale, never the write-time scale |
| `@Column(precision=19, scale=4)` | Generates the matching DDL; keeps entity and column scale in sync |
| JDBC and `double` | `getBigDecimal` never routes through `double`; the binary-float error path is closed |
| Round-trip comparison | Use `compareTo`, never `equals`, across a JDBC round-trip |
| `BigInteger` representation | Sign-magnitude: `final int signum`, `final int[] mag`, big-endian, no leading zero words |
| `BigInteger` overflow | None — reallocates `mag` instead of wrapping |
| `mod` | Non-negative remainder, unlike `%` |
| `modPow(e, n)` | Modular exponentiation; RSA's core operation |
| `gcd` | Binary GCD algorithm |
| `isProbablePrime(certainty)` | Miller-Rabin, `certainty` rounds; probabilistic, not definite |
| RSA and `BigInteger` | `c = m.modPow(e, n)`; use `java.security`, never hand-rolled |
| `KARATSUBA_THRESHOLD` | 80 words = 2,560 bits ≈ 771 decimal digits |
| `TOOM_COOK_THRESHOLD` | 240 words |
| Below 80 words | Schoolbook, O(n²) |
| 80-240 words | Karatsuba, O(n^1.585) |
| 240+ words | 3-way Toom-Cook, O(n^1.465) |
| FFT/Schönhage-Strassen | Not present in the JDK |
| `BigInteger.valueOf` cache | Exactly -16..16 inclusive |
| Cache `==` | `valueOf(16) == valueOf(16)` true; `valueOf(17) == valueOf(17)` false |
| Same pattern elsewhere | `Integer.valueOf` caches -128..127 |
| `BigDecimal.add`, compact | 2.24 ns/op measured — **8.6x** a `long` add (0.26 ns/op) |
| `BigDecimal.add`, attached `intVal` | 3.61 ns/op — 1.6x the compact form, same value |
| Full bonus-split pipeline | 10.17 ns/op — **39x** a `long` add |
| "10-100x slower" claim | Overstated for compact single-op; fair for inflated/pipeline cases |
| Measurement caveat | Wall-clock loop timings, not JMH; no error bars |
| `BigDecimal.valueOf(i,2)` size | 40.0 bytes measured |
| `new BigDecimal(BigInteger,int)` size | 104.2 bytes measured — 64 bytes wasted vs `valueOf` |
| Inflated 30-digit `BigDecimal` size | 112.0 bytes measured |
| `long` size | 8 bytes |
| 19.8M entries/day, compact | ≈ 792 MB/day |
| 19.8M entries/day, attached `intVal` waste | ≈ 1.27 GB/day of pure waste |
| Default choice | `BigDecimal` everywhere; `long` minor units only after profiling shows a bottleneck |

---

## Self-test

**Q1.** A value is written to a `NUMERIC(19,4)` column as `new BigDecimal("4.20")` (scale 2) and read back with `getBigDecimal`. What scale does the returned value have, and why does `assertEquals` on the two values fail?

<details><summary>Answer</summary>

The returned value has scale 4, matching the column's declared scale, not the
scale the write used. `BigDecimal.equals` returns false the moment the two
scales differ, before it even inspects the significand — so `assertEquals`
between the scale-2 write value and the scale-4 read-back value fails even
though they represent the identical amount. The fix is to compare with
`compareTo`, which normalises scale away, returning 0 for any two
`BigDecimal`s of equal numeric value.

</details>

**Q2.** Why does `NUMERIC(19,4)` win over `NUMERIC(19,2)` for a financial schema, when the money itself only ever has two decimal places of real value?

<details><summary>Answer</summary>

Because intermediate calculations — a bonus percentage applied before the
final rounding, a fee expressed as a rate — routinely produce values with more
than two decimal places before the business rule's own
`setScale(2, RoundingMode.HALF_UP)` collapses them. A column fixed at scale 2 forces that rounding to happen at
write time, in the column itself, with no room to defer it to the point the
rule actually specifies the rounding mode. Scale 4 leaves two spare digits of
headroom below the minor unit for exactly that purpose, and 19 total digits is
the widest precision that still maps cleanly onto a `long`-backed
representation on most database engines.

</details>

**Q3.** What field does `BigInteger` use in place of two's-complement representation, and what is the practical consequence for overflow?

<details><summary>Answer</summary>

`BigInteger` stores a `final int signum` (-1, 0, or 1) and a `final int[] mag`
holding the magnitude big-endian with no leading zero words — sign-magnitude,
not two's complement. Because there is no fixed bit width, there is no
overflow in the `int`/`long` sense: an operation that would overflow a
fixed-width type instead reallocates `mag` one word larger. The cost of
arbitrary precision is paid entirely in allocation, never in a silent
wraparound bug.

</details>

**Q4.** Why does `isProbablePrime` take a `certainty` argument instead of just returning a definite yes/no?

<details><summary>Answer</summary>

Because primality testing at the sizes `BigInteger` is actually used for —
RSA key generation at 2048 bits and beyond — is done with the Miller-Rabin
algorithm, which is probabilistic: each round either proves the number is
composite or leaves a bounded residual chance it is composite anyway despite
passing. `certainty` controls how many Miller-Rabin rounds run, trading CPU
time for a smaller residual false-positive probability; there is no
constant-time definite primality test at these sizes that would make a
yes/no return value honest.

</details>

**Q5.** `BigInteger.valueOf(16) == BigInteger.valueOf(16)` is `true`. What does this actually prove about `BigInteger`'s `==` behaviour, and what is the risk of trusting it?

<details><summary>Answer</summary>

It proves nothing general — it only reflects that `valueOf` caches exactly the
range -16..16 inclusive as shared singleton instances (`MAX_CONSTANT = 16`),
so two `valueOf` calls for the same in-range value return the identical
object. `BigInteger.valueOf(17) == BigInteger.valueOf(17)` is `false`, proving
the general rule is `equals`, not `==`. The risk is that test data or example
code built from small numbers never surfaces the bug, so `==` looks correct
until a real value outside -16..16 reaches the comparison in production — the
exact same trap `Integer.valueOf`'s -128..127 cache sets for `Integer`.

</details>

**Q6.** Measured on JDK 21.0.7, `BigDecimal.add` on the compact path is 2.24 ns/op against 0.26 ns/op for a `long` add — an 8.6x ratio. Why does citing "`BigDecimal` is 10-100x slower than primitives" as a blanket fact overstate this?

<details><summary>Answer</summary>

Because 10-100x is only fair for the inflated representation (where `intVal`
is attached and every operation pays the larger object's cost) or for a
multi-step pipeline that allocates several intermediates — measured, the full
bonus-split pipeline of `multiply` then `setScale` is 10.17 ns/op, a 39x
ratio. A single `add` on the compact fast path, the common case for
money-sized values, measures 8.6x, not 10-100x. Quoting the higher figure for
every `BigDecimal` operation indiscriminately leads to premature optimisation
away from `BigDecimal` in code paths where the actual cost is a fraction of
what the folklore number implies.

</details>

---

## Open questions

None. Every numeric claim in this file traces to §6.7, §6.10, §6.11, or §6.12
of the measured brief, or to the `BigInteger`/`BigDecimal` Javadoc and the JDK
21 `lib/src.zip` source cited inline.

---

**Leaves covered:** 2.4.20–2.4.22 (3 leaves)
**Leaves deferred:** none
**Diagrams included:** none
**Target version:** Java 21 LTS
**Lines:** 553
