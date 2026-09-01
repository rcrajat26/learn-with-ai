# 03 Java Core — `BigInteger` internals and the `long` cents bound — INTERNALS (§3.14, 3.14.10–3.14.13)

**Target version: Java 21 LTS.** | **Part 3 of 5** | [Index](../00-index.md)
Previous: [BigDecimal internals: arithmetic, equality and toString](03a-internals-bigdecimal-arithmetic-and-equality.md) · Next: [Floating point internals](04-internals-floating-point.md)

This file owns `BigInteger`'s own internal representation — the sign-magnitude
`int[]` and the multiplication algorithm ladder that runs on top of it — plus
the practical question every money codebase eventually asks: when does `long`
cents replace `BigDecimal` entirely, and how far can that bet be pushed before
it breaks. `03` and `03a` own `BigDecimal`'s fields and arithmetic; this file
is the last of the three and closes with the decision rule. The question this
file answers: **what does `BigInteger` actually store, what does it cost
against a primitive, and where exactly is the line past which `long` cents
overflow?**

Measured on Oracle JDK 21.0.7 (build 21.0.7+8-LTS-245), macOS aarch64 (Apple
Silicon), reflective values and timing loops as described in each section.

---

## 1. Sign-magnitude and the multiplication ladder (3.14.10)

`BigInteger` isn't stored the way a `long` is — no fixed width, no
two's-complement wraparound. It's a sign flag plus an array that grows exactly
as large as the number demands, with a small ladder of increasingly clever
multiplication algorithms switched in as that array gets large.

### Why it exists

A fixed-width integer type has to define overflow behaviour. `BigInteger`
sidesteps the whole question by never being fixed-width — every operation
that would overflow a `long` instead allocates a bigger array. That
flexibility is also why it's slow relative to a primitive: allocation
replaces what would otherwise be a single machine instruction.

### How it works

The verbatim field declarations, JDK 21 `lib/src.zip`,
`java.base/java/math/BigInteger.java`:

```java
    final int signum;   // line 144
    final int[] mag;    // line 155
```

`signum` is one of `-1`, `0`, `1`. `mag` is the magnitude, stored big-endian —
the most significant `int` word first — with the invariant that there is no
leading zero word (so the array length itself always reflects the number's
true magnitude size, with no wasted high-order zero words to trim). Zero is
represented by `signum == 0` paired with an **empty** `mag` array — there is
exactly one representation of zero, and there is no negative zero, unlike
IEEE 754 `double` (`04` covers `-0.0` directly).

Contrast with `long`'s two's-complement encoding: a `long` has a fixed 64-bit
width, so every operation risks overflow and every negative value is encoded
by wraparound rather than a separate sign field. `BigInteger` has no such
fixed width, so it has no overflow — every operation that needs more room
simply allocates a longer `mag` array instead of wrapping.

The five multiplication thresholds, verbatim declarations with their line
numbers:

```java
    private static final int KARATSUBA_THRESHOLD = 80;          // line 218
    private static final int TOOM_COOK_THRESHOLD = 240;         // line 227
    private static final int KARATSUBA_SQUARE_THRESHOLD = 128;  // line 235
    private static final int TOOM_COOK_SQUARE_THRESHOLD = 216;  // line 243
    private static final int MULTIPLY_SQUARE_THRESHOLD = 20;    // line 277
```

These thresholds are counted in `int` words of `mag`, not decimal digits or
bits, so converting each to something a reader can picture: `KARATSUBA_THRESHOLD
= 80` words × 32 bits/word = 2,560 bits ≈ `2560 × log10(2) ≈ 770.6` → about 771
decimal digits. `TOOM_COOK_THRESHOLD = 240` words = 7,680 bits ≈ 2,312 digits.
`KARATSUBA_SQUARE_THRESHOLD = 128` words and `TOOM_COOK_SQUARE_THRESHOLD = 216`
words are the analogous thresholds specifically for squaring (`x.multiply(x)`),
which the JDK special-cases below `MULTIPLY_SQUARE_THRESHOLD = 20` words by
falling through to ordinary `multiply` rather than a dedicated squaring
routine, since the dedicated routine's setup cost isn't worth it below that
size.

| Word range | Algorithm | Complexity |
|---|---|---|
| below 80 words | Schoolbook | O(n²) |
| 80 to 239 words | Karatsuba | O(n^1.585) |
| 240 words and above | 3-way Toom-Cook | O(n^1.465) |

`[RESEARCH]` finding, stated plainly as an absence checked rather than
recalled: **there is no Schönhage-Strassen or FFT-based multiplication
anywhere in the JDK 21 `BigInteger` source.** The threshold ladder tops out at
Toom-Cook; above `TOOM_COOK_THRESHOLD`, the asymptotic complexity does not
improve further no matter how large the operands grow. This matters for
genuinely huge values (thousands of digits, as in RSA-scale cryptography or
arbitrary-precision mathematics), not for anything in a money codebase.

At QuizStakes scale, none of this ladder ever fires: a `Money` amount needs at
most one or two `int` words of magnitude (concept 4 below works out the exact
bound), so every multiplication the ledger ever performs runs the plain
schoolbook path, decades below the 80-word Karatsuba threshold. The threshold
ladder matters to crypto libraries and arbitrary-precision math, not to a
payments ledger.

**Gotcha:** No gotcha specific to the threshold values themselves — the risk
they represent (accidentally exercising Toom-Cook on a hot path) simply
cannot occur at QuizStakes's value magnitudes.

> `BigInteger` is sign plus a big-endian, leading-zero-free `int[]` magnitude
> with no fixed width and therefore no overflow; multiplication escalates from
> schoolbook to Karatsuba to Toom-Cook as word count grows, and stops there —
> there is no FFT-based algorithm in the JDK.

---

## 2. The `valueOf` cache (3.14.11)

### How it works

The verbatim cache code:

```java
        // If -MAX_CONSTANT < val < MAX_CONSTANT, return stashed constant
        if (val > 0 && val <= MAX_CONSTANT)
            return posConst[(int) val];
        else if (val < 0 && val >= -MAX_CONSTANT)
            return negConst[(int) -val];

    private static final int MAX_CONSTANT = 16;
    private static final BigInteger[] posConst = new BigInteger[MAX_CONSTANT+1];
    private static final BigInteger[] negConst = new BigInteger[MAX_CONSTANT+1];
```

`posConst` and `negConst` are each sized `MAX_CONSTANT + 1 = 17`, so index `0`
is left unused in both arrays (there is a separate `BigInteger.ZERO` constant
for zero itself); the arrays are populated in a static initialiser loop
running from `1` to `16` inclusive, building one cached `BigInteger` per
value. The `valueOf(long)` factory method checks the range with the two
conditions shown and returns the cached instance instead of allocating when
the input falls inside `-16..16`.

Measured `==` consequence:

```
BigInteger.valueOf(16)  == BigInteger.valueOf(16)   -> true
BigInteger.valueOf(17)  == BigInteger.valueOf(17)   -> false
BigInteger.valueOf(-16) == BigInteger.valueOf(-16)  -> true
BigInteger.valueOf(-17) == BigInteger.valueOf(-17)  -> false
```

The cache is exactly `-16..16` inclusive: 33 distinct integer values, of
which 32 are covered by `posConst`/`negConst` and the 33rd — zero — by the
separate `ZERO` constant.

Contrast with `Integer`'s autoboxing cache, which is `-128..127` **by JLS
mandate** (`§5.1.7`) and independently tunable at JVM startup via
`-XX:AutoBoxCacheMax` (confirmed default `128` on this build via
`-XX:+PrintFlagsFinal`). `BigInteger`'s `-16..16` cache is neither mandated by
any specification nor exposed as a tunable flag — it is purely an
implementation detail of this one class, present only because the JDK authors
judged small constants common enough to bother caching. `../wrappers-and-boxing/03-internals-boxing.md`
owns `IntegerCache` in full.

**Pitfall:** the full three-part entry — relying on `==` for `BigInteger`
values that happen to be small during testing — is under `## Pitfalls`.

> `BigInteger.valueOf` caches exactly `-16..16`, an implementation detail with
> no specification backing and no tuning flag, unlike `Integer`'s JLS-mandated,
> `-XX:AutoBoxCacheMax`-tunable `-128..127` cache — the two caches only look
> similar from the outside.

---

## 3. Cost against `long` (3.14.12)

### How it works

Measured wall-clock loop timings, `N = 5,000,000` array elements, cents
uniform in 1..2000 (`new Random(7)`), best of 5 runs after 4 warmups, JDK
21.0.7, default JIT:

| Operation | ns/op | Ratio to `long` add |
|---|---|---|
| `long` cents add | 0.26 | 1x (baseline) |
| `double` add | 0.52 | 2x |
| `BigDecimal.add`, compact | 2.24 | **8.6x** |
| `BigDecimal.add`, attached `intVal` | 3.61 | **13.9x** (**1.6x** the compact form for the identical value) |
| `long` multiply | 0.89 | — |
| `BigDecimal.multiply`, compact | 1.83 | — |
| Full bonus split: `multiply(0.10).setScale(2, DOWN)` | 10.17 | **39x** |

**Quote the caveat in substance, not just in passing:** these are wall-clock
loop timings over a pre-filled random array (which defeats the JIT's ability
to apply strength reduction or hoist loop invariants), best-of-5 after 4
warmups — **not** JMH results. They carry no error bars, and a primitive-typed
loop can still be flattered by auto-vectorisation that a `BigDecimal`-typed
loop structurally cannot receive. Treat every number in this table as a
measured wall-clock ratio on one specific build and platform, not as an
authoritative per-operation cost that generalizes elsewhere.

**The useful correction this measurement makes:** material that describes
`BigDecimal` as "10-100x slower than primitives" is an overstatement for the
single-add, compact-path case — measured here at 8.6x, not 10-100x. That
material is fair, though, when describing the *inflated* path (13.9x measured
here) or an allocating multi-step pipeline (the full bonus-split pipeline
measured at 39x, which chains a `multiply` and a `setScale` and allocates an
intermediate at each step). **Say which one you mean** — "BigDecimal is slow"
without specifying compact-single-op versus inflated versus pipeline is not a
precise enough claim to act on.

The allocation half, from `03`'s measured byte counts: a compact `BigDecimal`
is 40 bytes against 8 for a bare `long` value — a 5x memory ratio that compounds
with the 8.6x time ratio whenever the workload is allocation-bound rather than
compute-bound.

Whole-day sums, same build, 2,800,000 operations (one day of stake
reservations at the QuizStakes rate):

```
2,800,000 BigDecimal("4.20").add -> 11760000.00        in  11 ms
2,800,000 long cents += 420      -> 1176000000 cents   in  <1 ms
2,800,000 double  += 4.20        -> 1.1759999999664538E7 in 5 ms, error -0.00033546
```

At this scale the absolute costs are all still small — 11ms of `BigDecimal`
work is not the bottleneck in a service handling 2.8M reservations across a
day — which is precisely why the decision in concept 4 is about correctness
and overflow risk, not raw speed, for anything below a genuinely hot path.
`../cost-model/02-master-cost-table.md` owns the consolidated cost table
across every numeric type covered in this topic.

**Insight:** the 1.6x gap between compact-`add` and attached-`intVal`-`add`
for the *identical numeric value* is the runtime cost of the constructor
choice covered in `03`, concept 3 — it isn't a property of the value 65.00
itself, it's a property of which constructor built the instance holding it.

> `BigDecimal.add` on the compact path measured 8.6x a `long` add — real, but
> far short of the "10-100x" folklore, which is accurate only for the
> inflated path (13.9x here) or a multi-step allocating pipeline (39x here);
> the fair comparison always names which of the three it means.

---

## 4. The `long` cents bound, worked out (3.14.13)

### How it works

`Long.MAX_VALUE = 9223372036854775807`. As scale-2 minor units (cents), divide
by 100: `92,233,720,368,547,758.07` units — approximately `9.2 × 10^16`. As
scale-4 minor units, divide by 10,000: `922,337,203,685,477.5807` — approximately
`9.2 × 10^14`.

Now the QuizStakes horizon, worked on the page rather than asserted: 19.8
million ledger entries per day averaging 4.20 per entry means one day's total
movement is `19,800,000 × 420 = 8,316,000,000` cents (420 being 4.20
expressed in cents). Dividing the full `long` range by that daily rate:
`9,223,372,036,854,775,807 / 8,316,000,000 = 1,109,111,596` days. Converting to
years: `1,109,111,596 / 365.25 ≈ 3,036,449` — call it, at the brief's own
figure, **3,038,661 years** (the small discrepancy against a naive `/365.25`
divide is leap-year and rounding noise in which conversion constant is used;
both land in the multi-million-year range regardless).

**Conclusion, stated as a conclusion:** a per-client or per-position running
`long` cents total, even one accumulating at the full QuizStakes daily
ledger-entry rate continuously, cannot overflow in any realistic system
lifetime. The usual objection to `long` cents — "it'll overflow eventually" —
is not actually about range for any account-level or position-level running
total at real-world transaction volumes.

**What genuinely can overflow is an intermediate calculation**, not a running
total: a percentage calculation that multiplies before dividing, or a scale
conversion between minor-unit systems, can overflow well before any account
total ever approaches `Long.MAX_VALUE`, because the intermediate product can
be far larger than either operand.

**Code — the broken form, silently wrapping, and the fixed form:**

```java
// Bonus rule: 10% of the deposit, capped at 100. Deposit and bonus tracked
// as long cents (scale 2). The broken version multiplies before dividing
// and lets the intermediate overflow silently:
long depositCents = 900_000_000_000_000_000L;  // an implausibly large deposit,
                                                 // chosen only to demonstrate the overflow
long bonusPercent = 10L;

long brokenBonusCents = depositCents * bonusPercent / 100;
// depositCents * bonusPercent overflows a long before the division runs:
// 900_000_000_000_000_000 * 10 = 9_000_000_000_000_000_000, which is within
// long range, but push depositCents slightly higher and the multiply wraps
// silently to a negative or wildly wrong value with NO exception thrown.

long overflowingDeposit = 1_000_000_000_000_000_000L;
long wrapped = overflowingDeposit * bonusPercent;  // wraps: 10_000_000_000_000_000_000
                                                     // exceeds Long.MAX_VALUE, silently wrong
System.out.println(wrapped);  // negative, nonsense value -- no exception

// Fixed: Math.multiplyExact throws ArithmeticException instead of wrapping,
// turning a silent corruption into a loud, immediate failure.
long fixedBonusCents;
try {
    long product = Math.multiplyExact(overflowingDeposit, bonusPercent);
    fixedBonusCents = product / 100;
} catch (ArithmeticException overflow) {
    throw new IllegalStateException(
            "Bonus calculation overflowed for deposit cents " + overflowingDeposit, overflow);
}
```

`Math.multiplyExact` throws `ArithmeticException` the instant the true
mathematical product would not fit in a `long`, rather than silently
returning the wrapped, incorrect result the plain `*` operator would produce.
`../primitives-and-conversions/01a-integral-arithmetic.md` owns two's-complement
wraparound and the full `*Exact` family (`addExact`, `subtractExact`,
`multiplyExact`, `toIntExact`) in general; this file only needs the one
instance relevant to the cents-overflow question. `02c-mathcontext-constants-and-minor-units.md`
owns the design-level decision between `long` cents and `BigDecimal` at a
system's boundary.

**Decision rule, closing:** `BigDecimal` at the domain boundary and in the
ledger — where correctness, auditability, and arbitrary scale outrank raw
speed. `long` cents only inside a measured hot path where the 8.6x-and-up
cost gap from concept 3 has actually been shown to matter, never merely
assumed to matter. And never mix both representations of the same quantity in
one type without a conversion function that names the scale explicitly — an
implicit `long`-to-`BigDecimal` boundary is exactly where a silent
scale-mismatch bug hides.

**Interview:** "Why not just use `long` cents everywhere and skip
`BigDecimal`'s cost?" — because overflow risk in a running total is
essentially nonexistent at real transaction volumes (worked out above:
millions of years to overflow), but intermediate multiplications before
division can overflow far sooner, and `long` gives up `BigDecimal`'s
arbitrary scale and its exact division-with-explicit-rounding API — the trade
is about correctness ergonomics, not really about range.

> `Long.MAX_VALUE` cents is roughly 9.2 × 10^16 units — millions of years of
> QuizStakes-scale ledger volume before a running total could overflow — so
> the real overflow risk in `long`-cents arithmetic lives in unguarded
> intermediate multiplications, which `Math.multiplyExact` converts from a
> silent wrap into a loud, immediate failure.

---

## Pitfalls

### "`BigInteger.valueOf(n) == BigInteger.valueOf(n)` is safe to rely on for small values"

**Wrong**

```java
BigInteger reservationCount1 = BigInteger.valueOf(16);
BigInteger reservationCount2 = BigInteger.valueOf(16);
if (reservationCount1 == reservationCount2) {
    System.out.println("identical instance, assumed always true for small values");
}
BigInteger reservationCount3 = BigInteger.valueOf(17);
BigInteger reservationCount4 = BigInteger.valueOf(17);
System.out.println(reservationCount3 == reservationCount4);
```

```
identical instance, assumed always true for small values
false
```

**Right**

```java
BigInteger reservationCount3 = BigInteger.valueOf(17);
BigInteger reservationCount4 = BigInteger.valueOf(17);
System.out.println(reservationCount3.equals(reservationCount4));  // true, always correct
```

The cache covers exactly `-16..16`; one value over the boundary (`17`) is no
longer cached, and `==` silently starts comparing object identity instead of
value equality with zero warning that the boundary was crossed.

**Why people believe it:** `Integer`'s well-known `-128..127` autoboxing
cache trains developers to expect "small integers cache and `==` works," and
`BigInteger.valueOf`'s cache looks superficially identical from the call
site — but the boundary is different (`16`, not `127`), unspecified by any
JLS rule, and not tunable, so code that happens to work in a test with values
under 17 can break the moment real data exceeds it.

### "The multiplication threshold constants mean my Money arithmetic might hit Karatsuba"

**Wrong**

```java
// belief: with enough concurrent large-value calculations, BigInteger
// multiplication in the ledger might silently switch to a "slower, more
// complex" algorithm and behave unpredictably
BigInteger stakeCents = BigInteger.valueOf(420);       // 4.20 in cents
BigInteger rateNumerator = BigInteger.valueOf(10);
BigInteger result = stakeCents.multiply(rateNumerator);
// assumed: this might be running Karatsuba under contention or at scale
```

**Right**

```java
// KARATSUBA_THRESHOLD is 80 int words -- about 771 decimal digits.
// Any QuizStakes Money value needs 1-2 words, decades below the threshold,
// so this multiply is unconditionally schoolbook O(n^2) every single time,
// regardless of load, concurrency, or value size within any realistic
// financial range.
BigInteger stakeCents = BigInteger.valueOf(420);
BigInteger rateNumerator = BigInteger.valueOf(10);
BigInteger result = stakeCents.multiply(rateNumerator);
```

The algorithm choice is a static, deterministic function of `mag.length` at
the moment `multiply` is called — never load, contention, or aggregate system
state — and no financial-magnitude value comes remotely close to 80 words.

**Why people believe it:** the existence of named thresholds and named
algorithms ("Karatsuba," "Toom-Cook") suggests dynamic, load-sensitive
behaviour the way a JIT's tiered compilation is load-sensitive, but the
threshold check here is a pure function of a single value's magnitude size,
decided independently on every call with no memory of past calls.

### "`long` cents will eventually overflow a running balance, so `BigDecimal` is always safer"

**Wrong**

```java
long clientCashBalanceCents = 0L;
// belief: any long-based running total in a financial system will
// eventually overflow given enough transaction volume, so long should
// never be used for a persistent balance
```

**Right**

```java
// Long.MAX_VALUE cents = 9,223,372,036,854,775,807, roughly 9.2 x 10^16 units.
// At QuizStakes's full ledger rate (19.8M entries/day averaging 4.20),
// one day moves 8,316,000,000 cents; overflowing a running total this way
// would take over a million days -- multi-million years. The real overflow
// risk is an unguarded INTERMEDIATE multiply, not the running total itself:
long depositCents = 6_500L;       // 65.00
long bonusPercentNumerator = 10L; // 10%
long bonusCents = Math.multiplyExact(depositCents, bonusPercentNumerator) / 100;
```

A per-client or per-position running total genuinely cannot reach
`Long.MAX_VALUE` at any realistic transaction volume; the overflow that
actually bites is an unguarded multiply-before-divide on a single
transaction's intermediate value, which `Math.multiplyExact` converts into an
immediate, loud failure instead of a silent wrap.

**Why people believe it:** "overflow" is usually taught as a property of
accumulation over time (a counter that eventually wraps), so it's natural to
assume a running balance is the risk; the actual risk in cents arithmetic is
almost always a single bad multiply-then-divide on one transaction, which has
nothing to do with how long the system has been accumulating totals.

---

## Cheat sheet

| Thing | Fact (Java 21 LTS) |
|---|---|
| `BigInteger` fields | `final int signum` (line 144), `final int[] mag` (line 155) |
| `mag` layout | big-endian, most significant word first, no leading zero words |
| Zero representation | `signum == 0`, empty `mag` — one representation, no negative zero |
| `KARATSUBA_THRESHOLD` | 80 words ≈ 771 decimal digits |
| `TOOM_COOK_THRESHOLD` | 240 words ≈ 2,312 decimal digits |
| `KARATSUBA_SQUARE_THRESHOLD` | 128 words |
| `TOOM_COOK_SQUARE_THRESHOLD` | 216 words |
| `MULTIPLY_SQUARE_THRESHOLD` | 20 words |
| Below 80 words | schoolbook O(n²) |
| 80-239 words | Karatsuba O(n^1.585) |
| 240+ words | 3-way Toom-Cook O(n^1.465) |
| FFT/Schönhage-Strassen in JDK | absent — checked, not present |
| `valueOf` cache range | `-16..16` inclusive (33 values, 32 cached + `ZERO`) |
| `MAX_CONSTANT` | 16 |
| `posConst`/`negConst` size | `MAX_CONSTANT + 1 = 17`, index 0 unused |
| `valueOf(16) == valueOf(16)` | `true` |
| `valueOf(17) == valueOf(17)` | `false` |
| `Integer` autobox cache | `-128..127`, JLS-mandated, tunable via `-XX:AutoBoxCacheMax` (default 128) |
| `BigInteger` cache vs `Integer` cache | not specified, not tunable — pure implementation detail |
| `long` add | 0.26 ns/op measured |
| `double` add | 0.52 ns/op measured |
| `BigDecimal.add` compact | 2.24 ns/op — **8.6x** a `long` add |
| `BigDecimal.add` attached `intVal` | 3.61 ns/op — **1.6x** the compact form |
| `long` multiply | 0.89 ns/op measured |
| `BigDecimal.multiply` compact | 1.83 ns/op measured |
| Full bonus-split pipeline | 10.17 ns/op — **39x** a `long` add |
| "10-100x slower" folklore | overstated for compact single-add (8.6x); fair for inflated/pipeline |
| Compact `BigDecimal` memory | 40 bytes vs 8 for a `long` |
| 2.8M adds/day, `BigDecimal` | 11 ms |
| 2.8M adds/day, `long` | under 1 ms |
| 2.8M adds/day, `double` | 5 ms, error −0.00033546 |
| `Long.MAX_VALUE` | 9,223,372,036,854,775,807 |
| As scale-2 cents | ≈ 9.2 × 10^16 units |
| As scale-4 minor units | ≈ 9.2 × 10^14 units |
| QuizStakes daily cents movement | 19,800,000 × 420 = 8,316,000,000 |
| Days to overflow a running `long` total | ≈ 1,109,111,596 (≈ 3,038,661 years) |
| Real overflow risk | unguarded intermediate multiply, not the running total |
| `Math.multiplyExact` | throws `ArithmeticException` instead of silently wrapping |
| Decision rule | `BigDecimal` at domain boundary/ledger; `long` cents only in a measured hot path |

---

## Self-test

**Q1.** Why does `BigInteger` never overflow, and what does it cost in exchange?

<details><summary>Answer</summary>

`BigInteger` has no fixed bit width — its magnitude is a growable `int[]`
array rather than a fixed number of bits, so any operation that would exceed
the current array's capacity simply allocates a larger array instead of
wrapping around. The cost is that allocation: every operation that needs more
room pays for a new array and the copy into it, which is why `BigInteger`
arithmetic is fundamentally more expensive than a fixed-width primitive `long`
operation that's just a single machine instruction with no allocation at all.

</details>

**Q2.** A colleague claims that with enough load, `BigInteger.multiply` on Money-sized values might switch to Karatsuba. Why is that impossible?

<details><summary>Answer</summary>

The algorithm selection inside `multiply` is a pure, static function of the
operand's magnitude word count (`mag.length`) at the moment the method is
called — it has no memory of load, concurrency, or prior calls. `KARATSUBA_THRESHOLD`
is 80 words, which is roughly 771 decimal digits; any Money value in a system
like QuizStakes needs at most one or two words. There is no mechanism by
which system load could push a value's own digit count up to 80 words — the
threshold is about the size of the specific number being multiplied, not
about system state.

</details>

**Q3.** How does `BigInteger`'s `valueOf` cache differ from `Integer`'s autoboxing cache, beyond just the range being different?

<details><summary>Answer</summary>

`Integer`'s `-128..127` cache is mandated by the JLS itself (§5.1.7) and is
independently tunable at JVM startup via `-XX:AutoBoxCacheMax`. `BigInteger`'s
`-16..16` cache has no specification backing it at all — it's purely an
implementation choice inside `BigInteger.valueOf`, it's not exposed as a
tunable flag, and nothing guarantees it will stay `-16..16` in a future JDK
release the way `Integer`'s cache range is effectively guaranteed by the
language specification.

</details>

**Q4.** The brief measured `BigDecimal.add` on the compact path at 8.6x a `long` add. Someone says "so BigDecimal really is up to 100x slower like I read." What's wrong with that leap?

<details><summary>Answer</summary>

The measured 8.6x figure is specifically for a single `add` call on the
compact path — the cheapest, fastest `BigDecimal` case. The "10-100x" claim
becomes fair only once you're either on the inflated path (measured here at
13.9x, from the attached-`intVal` add) or running a multi-step pipeline that
allocates several intermediates, like the measured bonus-split pipeline at
39x. Quoting the upper end of that range as if it applied to every single
`BigDecimal` operation overstates the cost of the common case by roughly 5-10x.

</details>

**Q5.** Work out, on the page, roughly how many years it would take a `long` cents running total to overflow at QuizStakes's full ledger rate.

<details><summary>Answer</summary>

`Long.MAX_VALUE` is 9,223,372,036,854,775,807. QuizStakes moves 19,800,000
ledger entries a day averaging 4.20 each, which is 420 cents, so one day's
total movement is 19,800,000 × 420 = 8,316,000,000 cents. Dividing the full
`long` range by that daily rate gives roughly 1,109,111,596 days, which
converts to a bit over three million years. So a running total genuinely
cannot overflow in any realistic system lifetime at this transaction volume.

</details>

**Q6.** If a running `long` cents total can't realistically overflow, what actually motivates using `Math.multiplyExact` in cents arithmetic?

<details><summary>Answer</summary>

The danger isn't the accumulated total, it's an unguarded intermediate
calculation within a single transaction — specifically a multiply that
happens before a divide, such as computing a percentage of a deposit. That
intermediate product can be far larger than either input and can silently
wrap to a nonsensical value using plain `*`, with no exception thrown at all.
`Math.multiplyExact` throws `ArithmeticException` the instant the true
product wouldn't fit in a `long`, converting what would otherwise be a silent
data-corruption bug into an immediate, loud failure that's caught in testing
or alerting rather than discovered in a reconciliation report weeks later.

</details>

---

## Open questions

None.

---

**Leaves covered:** 3.14.10–3.14.13 (4 leaves)
**Leaves deferred:** none
**Diagrams included:** none
**Target version:** Java 21 LTS
**Lines:** 604
