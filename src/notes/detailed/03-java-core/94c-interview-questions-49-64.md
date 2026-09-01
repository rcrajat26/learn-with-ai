# 03 Java Core — The eighty questions, 49–64 — INTERVIEW (§5.1, 5.1.49–5.1.64)

**Target version: Java 21 LTS.** | **Part 5 of 5** | [Index](00-index.md)
Previous: [The eighty questions, 33–48](94b-interview-questions-33-48.md) · Next: [The eighty questions, 65–80](94d-interview-questions-65-80.md)

## The questions, continued

One `###` per question, Q49 through Q64; for how to use this file see [`94-interview-questions-and-drills.md`](94-interview-questions-and-drills.md).

### Q49. "Do records give you immutability?"

**The 30-second answer.** Not on their own. A record gives you rules 1 through 3 of immutability for free and compiler-enforced — implicitly `final`, components stored as `private final` fields, and no instance fields are even legal to declare. It does not give you rules 4 and 5, defensive copying in and out, because the canonical constructor stores whatever reference it was handed and the accessor hands that same reference back. A record over a mutable component — a `List`, an array, a `Date` — is only shallowly immutable.

**The 5-minute answer.** Measured on JDK 21.0.7, `record Money(BigDecimal amount, Currency currency)` compiles to `final class Money extends java.lang.Record` with flags `(0x0030) ACC_FINAL, ACC_SUPER` and each component as a `private final` field. There is no `ACC_RECORD` flag — record-ness is a class-file `Record` attribute, not a bit. The canonical constructor's body is `invokespecial Record.<init>` followed by one `putfield` per component: no validation, no copying, unless you write a compact constructor. A compact constructor's assignments are to the *parameter*, not `this.field` — `this.x = ...` is a compile error inside one — and the compiler appends the generated `putfield`s *after* your body runs, which is why `entries = List.copyOf(entries);` in the body actually changes what gets stored. `List.copyOf` closes both holes at once: it copies on the way in and returns an unmodifiable list, so nothing extra is needed on the way out; it also returns the same instance when handed an already-immutable list, so the copy is free for well-behaved callers. For a component with no immutable equivalent — a `byte[]`, a `Date` — the two directions need closing separately: `signature = signature.clone()` in the constructor, plus an `@Override public byte[] signature() { return signature.clone(); }` accessor. One more thing worth volunteering: records *do* give you real thread-safety for the fields themselves, because the JLS §17.5 final-field freeze applies to every component — a thread that obtains the record's reference sees correctly-initialised fields even through a data race. What that freeze does not cover is the *interior* of a mutable component; two threads sharing a record with a mutable `List` field share that list with no synchronisation at all.

```java
public record LimitSet(String clientId, List<String> restrictionKeys) {

    public LimitSet {
        Objects.requireNonNull(clientId, "clientId");
        restrictionKeys = List.copyOf(restrictionKeys);   // rule 4 and 5, in one line
    }
}

List<String> mutable = new ArrayList<>(List.of("STAKE_BLOCKED"));
LimitSet safe = new LimitSet("c-1", mutable);
mutable.add("SELF_EXCLUDED");                              // caller still holds the reference
safe.restrictionKeys().add("SELF_EXCLUDED");                // UnsupportedOperationException, measured
```

**The follow-up they will ask** — "What if the component itself needs to change what an accessor returns?" Override the accessor to return a defensive copy, but know that `equals`/`hashCode`/`toString` read the *field* directly via `REF_getField` method handles, never the accessor, so overriding the accessor does not change generated equality.

**Where this is written** — [`records-and-sealed/01-basics.md`](records-and-sealed/01-basics.md), [`records-and-sealed/01a-object-methods-sealed-and-fit.md`](records-and-sealed/01a-object-methods-sealed-and-fit.md), [`immutability-and-design/02b-records-jmm-and-builders.md`](immutability-and-design/02b-records-jmm-and-builders.md).

---

### Q50. "Why is 0.1 + 0.2 != 0.3?"

**The 30-second answer.** `binary64` stores a binary fraction, and 0.1, 0.2 and 0.3 are all decimal fractions with a factor of 5 in the denominator, which has no finite binary expansion — the same reason 1/3 has no finite decimal expansion. Each of `0.1` and `0.2` is stored as the *nearest representable* `double`, both slightly off, and adding those two approximations does not cancel the errors; the sum rounds to `0.30000000000000004`, not the mathematical `0.3`.

**The 5-minute answer.** Derive it by the doubling algorithm: `0.1 × 2 = 0.2 → 0`, `0.2 × 2 = 0.4 → 0`, `0.4 × 2 = 0.8 → 0`, `0.8 × 2 = 1.6 → 1`, `0.6 × 2 = 1.2 → 1`, and the cycle re-enters at `0.2`, so `0.1` in binary is `0.0001100110011...` with `1100` repeating forever. `binary64` gives 52 stored mantissa bits plus one implicit leading bit — 53 significant bits — so the repeating expansion is cut and rounded. Measured, `Double.doubleToLongBits(0.1) = 0x3fb999999999999a`: sign 0, biased exponent 1019 (unbiased −4), mantissa ending `...1010` — rounded *up* from the naive truncation `...1001`, because the first discarded bit was 1. `new BigDecimal(0.1)` walks that exact bit pattern with no rounding and prints `0.1000000000000000055511151231257827021181583404541015625`, 55 digits — that is not a display artefact, it is the exact rational number `0x3fb999999999999a` denotes. `0.2` is similarly stored slightly high. Add the two stored values and round the sum to the nearest `binary64`: the result is `0.3000000000000000444089209850062616169452667236328125`, whose shortest round-tripping decimal — what `Double.toString` prints — is `0.30000000000000004`. This is a specification fact, not a Java bug: every language using IEEE 754 binary64 gets the identical answer. In money terms: a bonus balance accumulated as a `double`, one grant of 0.42 at a time, 100 times, gives `41.99999999999992`, not `42.0` — while the same accumulation as `long` minor units gives exactly `4200`.

```java
double bonusDouble = 0.0;
for (int i = 0; i < 100; i++) { bonusDouble += 0.42; }
System.out.println(bonusDouble);                 // 41.99999999999992

long bonusMinorUnits = 0L;
for (int i = 0; i < 100; i++) { bonusMinorUnits += 42L; }
System.out.println(bonusMinorUnits);             // 4200, exact
```

**The follow-up they will ask** — "How do you compare two doubles safely, then?" Never with `==` for a computed value; use a relative-magnitude epsilon (`Math.abs(a - b) <= tolerance * Math.max(Math.abs(a), Math.abs(b))`), because a fixed absolute epsilon is simultaneously too tight at large magnitudes and too loose at small ones — for money, the honest fix is not a better epsilon, it is `BigDecimal.compareTo`.

**Where this is written** — [`primitives-and-conversions/01c-floating-point.md`](primitives-and-conversions/01c-floating-point.md), [`numbers-and-money/04-internals-floating-point.md`](numbers-and-money/04-internals-floating-point.md), [`numbers-and-money/02-numbers-and-money.md`](numbers-and-money/02-numbers-and-money.md).

---

### Q51. "Why is new BigDecimal(0.1) wrong?"

**The 30-second answer.** It is not wrong, it is *exact* — exact with respect to the `double` argument, which is precisely the trap. `0.1` as a `double` literal was never `0.1`; it is the nearest binary64 approximation, a 55-digit decimal value once you write it out in full. `new BigDecimal(double)` faithfully reconstructs that exact value, giving you 55 digits of noise instead of the `0.1` a human typed. The constructor did its job correctly; the job itself was the wrong one to ask for.

**The 5-minute answer.** Measured on JDK 21.0.7: `new BigDecimal(0.1)` prints `0.1000000000000000055511151231257827021181583404541015625`, scale 55, `intCompact = INFLATED` (`Long.MIN_VALUE`, the sentinel meaning "read the significand from `intVal`"), with a 55-digit `BigInteger` attached. Deriving the digit count rather than trusting it: `0.1`'s stored bits give unbiased exponent −4 with 52 mantissa bits, so the value is a dyadic rational with denominator `2^56`; since `1/2^n = 5^n/10^n`, any such fraction terminates in decimal at no more than 56 digits, and the actual expansion lands one digit under that bound at 55. Contrast the two constructors that get it right. `new BigDecimal("0.1")` never touches a `double` — it parses the three characters `"0.1"` directly to unscaled value `1`, scale `1`. `BigDecimal.valueOf(double)` is `return new BigDecimal(Double.toString(val));` — it routes through `Double.toString`, whose contract is to produce the *shortest decimal string that round-trips* to the same `double` bits, so `Double.toString(0.1)` is `"0.1"` and `valueOf(0.1)` lands on the same scale-1 result as the `String` constructor. `valueOf` only fixes the single conversion, though — it cannot undo error already baked in by prior `double` arithmetic: `BigDecimal.valueOf(sum)` where `sum` is `0.1 + 0.2` as a `double` still prints `0.30000000000000004`, because that really is `sum`'s value. The domain rule: money enters the system as a `String` or as integer minor units, never through a `double` — if a JSON deserializer would otherwise produce a `double` for an amount field, configure it to bind a `String` or a `BigDecimal` directly.

```java
new BigDecimal(0.1)              // 0.1000000000000000055511151231257827021181583404541015625, scale 55
new BigDecimal("0.1")            // 0.1, scale 1, unscaled 1
BigDecimal.valueOf(0.1)          // 0.1, scale 1 -- via Double.toString("0.1") then the String ctor
```

**The follow-up they will ask** — "Is `BigDecimal.valueOf` always safe then?" No — it only cleans up a single `double`-to-decimal conversion; summing `0.1` as a `double` 100,000 times drifts to `10000.000000018848`, and `BigDecimal.valueOf` on that result reports the drift faithfully rather than removing it.

**Where this is written** — [`numbers-and-money/02a-bigdecimal-structure-and-construction.md`](numbers-and-money/02a-bigdecimal-structure-and-construction.md), [`numbers-and-money/03-internals-bigdecimal.md`](numbers-and-money/03-internals-bigdecimal.md).

---

### Q52. "Why is new BigDecimal("2.0").equals(new BigDecimal("2.00")) false?"

**The 30-second answer.** Because `BigDecimal.equals` compares *representation* — unscaled value and scale — not numeric value, and it checks scale before it ever looks at the significand. `"2.0"` parses to unscaled `20`, scale `1`; `"2.00"` parses to unscaled `200`, scale `2`. Different scales fail the very first line of `equals` and it returns `false` without comparing magnitudes at all, even though both denote the same number. `compareTo` is the one that answers "same numeric value" — it returns `0` here. `BigDecimal` is the JDK's own documented exception to "`compareTo` consistent with `equals`."

**The 5-minute answer.** The verbatim JDK 21 source: `equals` starts `if (!(x instanceof BigDecimal xDec)) return false; if (x == this) return true; if (scale != xDec.scale) return false;` — that third line runs before either `intCompact` or `intVal` is examined. Only when scales match does it fall through to comparing significands, coercing through `compactValFor` so an attached-but-compact value still fast-paths. `hashCode` mirrors it: `31 * temp + scale`, folding the significand and then mixing in scale as the final term — this is not a bug, it is *required*, because `equals` already treats differently-scaled values as unequal, so `hashCode` must too or the contract breaks in the other direction. Measured: `"2.0".hashCode() = 621` (`31*20+1`), `"2.00".hashCode() = 6202` (`31*200+2`). Consequence: `new HashSet<>(List.of(new BigDecimal("2.0"), new BigDecimal("2.00")))` has size **2**, printing `[2.00, 2.0]`, because the two hash to different buckets and fail `equals` inside any bucket they'd share; the same two elements in a `TreeSet` collapse to size **1**, because a `TreeSet` never calls `hashCode`/`equals` at all — it orders and deduplicates purely by `compareTo`. The canonical rounding example makes the stakes concrete: a stake of **3.33** splits as 10% bonus, rounded **down**, giving **0.33 bonus + 3.00 cash** — and `BigDecimal.equals` scale-mismatches would make two representations of that same split compare unequal in a naive `Money` unless the type normalises scale at construction, which is exactly why `Money`'s compact constructor pins `amount.setScale(currency.getDefaultFractionDigits(), RoundingMode.UNNECESSARY)`: once every `Money` in a given currency shares one canonical scale, `equals` and `compareTo` can never disagree again.

```java
new BigDecimal("2.0").equals(new BigDecimal("2.00"))     // false
new BigDecimal("2.0").compareTo(new BigDecimal("2.00"))  // 0
new HashSet<>(List.of(new BigDecimal("2.0"), new BigDecimal("2.00"))).size()   // 2
new TreeSet<>(List.of(new BigDecimal("2.0"), new BigDecimal("2.00"))).size()   // 1
```

**The follow-up they will ask** — "How do you write a `Money.equals` that doesn't have this trap?" Override it to compare by `compareTo(other.amount) == 0` rather than delegating to the generated record `equals` (which would call `BigDecimal.equals` on the component), and derive `hashCode` from `amount.stripTrailingZeros()` so equal values still land in the same bucket.

**Where this is written** — [`numbers-and-money/02b-equality-scale-and-rounding.md`](numbers-and-money/02b-equality-scale-and-rounding.md), [`numbers-and-money/03a-internals-bigdecimal-arithmetic-and-equality.md`](numbers-and-money/03a-internals-bigdecimal-arithmetic-and-equality.md).

---

### Q53. "How do you store money in Java and in the database?"

**The 30-second answer.** In Java, a domain `Money` type wrapping `BigDecimal` and `Currency`, with the scale pinned to the currency's minor unit at construction — never a bare `BigDecimal`, and never a `double`. In the database, `NUMERIC(19,4)` — exact decimal, four fractional digits even though the minor unit is two, because intermediate calculations (a bonus rate, a fee) routinely need a third or fourth decimal place before the business rule's own rounding collapses them. The alternative, a `BIGINT` of minor units, trades that self-describing exactness for raw speed and a 5× smaller footprint, and belongs only in a profiler-justified hot path, never in the ledger of record.

**The 5-minute answer.** `BigDecimal` is `unscaledValue × 10^(-scale)`; small unscaled values live in a compact `long` field (`intCompact`), and only fall back to a `BigInteger` (`intVal`) past roughly 18 decimal digits. Measured, a compact `BigDecimal` is **40 bytes** (12-byte header + 4-byte `intVal` ref + 4-byte `scale` + 4-byte `precision` + 4-byte `stringCache` ref + 8-byte `intCompact`, aligned); `new Money(BigDecimal, Currency)` as a record adds 24 bytes for the record shell, for **64 bytes** total. The minor-units alternative, `MoneyMinor(long units, Currency currency)`, measures **24 bytes** exactly — a **2.67×** allocation difference on a full stake split, escape analysis off. `NUMERIC(19,4)` versus `NUMERIC(19,2)`: 19 total digits is the widest precision that still fits a `long`-backed fast path on most engines, and scale 4 leaves two spare digits of headroom below the minor unit for exactly the intermediate-rate case; a column fixed at scale 2 forces rounding into the write itself, with no chance to defer to the point the business rule actually names a `RoundingMode`. JDBC preserves the *column's* declared scale on read, never the write-time scale — a value written as `new BigDecimal("4.20")` (scale 2) into a `NUMERIC(19,4)` column reads back as `4.2000` (scale 4), and `assertEquals` on the two fails even though `compareTo` says they match; use `compareTo`, never `equals`, across a JDBC round-trip. `DOUBLE PRECISION` for money repeats the exact IEEE-754 failure measured in Q50 inside the database: 2.8M additions of `4.20` sum to an error of `-0.00033546`, not zero. At QuizStakes' scale — ~19.8M ledger entries/day, ~180 bytes/row, ~7.2B rows/year, ~1.3 TB/year, with a 90-day hot window against 7-year retention — the 40-vs-24-byte Java-side difference is noise against the row width, which is why the domain type stays `BigDecimal`-backed while the reservation *hot loop*, at 2.8M/day peaking 1,200/sec, is the one place a profiler-justified switch to minor-unit `long` would pay for itself.

```java
public record Money(BigDecimal amount, Currency currency) {
    public Money {
        int digits = currency.getDefaultFractionDigits();
        amount = amount.setScale(digits, RoundingMode.UNNECESSARY);   // pinned scale, once
    }
}
```

```sql
CREATE TABLE ledger_entry (amount NUMERIC(19,4) NOT NULL, currency CHAR(3) NOT NULL);
```

```java
// The JDBC round-trip trap this domain lives with:
BigDecimal deposit = new BigDecimal("4.20");                    // scale 2
preparedStatement.setBigDecimal(1, deposit);
preparedStatement.executeUpdate();
BigDecimal reread = resultSet.getBigDecimal("amount");          // scale 4 -- the column's declared scale
assertEquals(0, deposit.compareTo(reread));                     // right: compareTo, never equals
```

**The follow-up they will ask** — "When would you switch to minor-unit `long`?" Only once a profiler shows the `BigDecimal` allocation is the actual bottleneck on a specific hot path — never speculatively, and never in the ledger of record, because the `long` path silently loses `HALF_EVEN` (integer `/` only gives `DOWN`, and `Math.floorDiv` gives `FLOOR`) and loses the currency-scale self-description that made the `BigDecimal.equals` trap fixable in the first place.

**Where this is written** — [`numbers-and-money/02d-storage-biginteger-and-cost.md`](numbers-and-money/02d-storage-biginteger-and-cost.md), [`numbers-and-money/02c-mathcontext-constants-and-minor-units.md`](numbers-and-money/02c-mathcontext-constants-and-minor-units.md), [`build-it/04-value-objects-and-money.md`](build-it/04-value-objects-and-money.md), [`build-it/04d-value-object-diff.md`](build-it/04d-value-object-diff.md).

---

### Q54. "What is HALF_EVEN and why does a bank care?"

**The 30-second answer.** `HALF_EVEN` — "banker's rounding" — resolves an exact tie (a discarded fraction of precisely 0.5 at the target scale) by moving to whichever neighbouring digit is even, rather than always rounding away from zero like `HALF_UP`. Over many independent ties the sign of each `HALF_EVEN` adjustment is effectively a coin flip, so the errors cancel — measured, `HALF_UP` drifts +5,000.00 over a million engineered ties, `HALF_EVEN` drifts only +0.88. A bank cares because repeated `HALF_UP` rounding on millions of transactions is a systematic, unidirectional bias — real money created from nothing, in one direction, forever.

**The 5-minute answer.** `2.335` rounded to scale 2 must pick `2.33` or `2.34` — an exact tie. `HALF_EVEN` looks at the *retained* last digit of each candidate: `2.33` ends in 3 (odd), `2.34` ends in 4 (even), so it picks **2.34**. `2.345` at scale 2 must pick `2.34` or `2.35`; this time `2.34` already ends in an even digit, so it *stays*, giving **2.34** again — same rule, opposite direction, because the tie-break depends on which neighbour happens to be even, not on any consistent "round up" bias. Measured over 1,000,000 engineered exact ties (`t + 0.5` minor units): `HALF_UP` drifts **+500,000 minor units** with *zero variance* (every positive tie rounds away from zero, deterministically), `DOWN` drifts **−500,000**, and `HALF_EVEN` drifts **+88** — a random walk of order `sqrt(n)`, not a linear accumulator. On the *realistic* QuizStakes operation — 10% of a two-decimal stake — a tie fires **one time in ten** (whenever the stake ends in 5 pence), not one in a million: measured, `HALF_UP` versus `DOWN` diverges by 499,770 minor units per million roundings, pricing out to **13,993.56/day** of created withdrawable cash at 2.8M reservations/day, versus **12,596.08/day** for `HALF_EVEN`. And here is the sharp turn a strong candidate takes: **QuizStakes' actual bonus rule is neither `HALF_UP` nor `HALF_EVEN` — it is `DOWN`.** The bonus portion of a stake always rounds down to the minor unit and cash covers the exact remainder by subtraction (`cash = stake − bonus`, never independently rounded), because rounding the bonus *up* creates withdrawable money the house never received: bonus is stakeable-but-not-withdrawable, cash is both, so an over-granted bonus of one cent is a cent of real money conjured from a rounding mode. `HALF_EVEN` is the right default when a *single* figure must be rounded in isolation with no second bucket to absorb the discarded fraction — a displayed tax figure, a one-shot currency conversion. It is the wrong answer the moment a domain rule is deliberately asymmetric, which is exactly the QuizStakes case: the choice of rounding mode is a business rule, not a numerical default, and the numbers above exist to price each option, not to pick one.

```java
Money bonus = stake.multiply(new BigDecimal("0.10"), RoundingMode.DOWN);   // never HALF_UP or HALF_EVEN here
Money cash = stake.subtract(bonus);                                        // derived, never independently rounded
// stake 3.33 -> bonus 0.33 + cash 3.00; rounding the bonus up gives 0.34 + 3.00 = 3.34, creating a cent
```

**The follow-up they will ask** — "Why not just use integer minor-unit `long` and let `/` truncate?" Because Java's `/` truncation is `DOWN` only for positive dividends — it becomes `UP` on negatives (`-335 / 10 == -33`, not `-34`), which silently favours the client on a clawback, and it delivers the correct rule by accident with nothing in the code documenting that "the mode is `DOWN`" was ever a decision.

**Where this is written** — [`numbers-and-money/02g-rounding-modes-and-the-api-surface.md`](numbers-and-money/02g-rounding-modes-and-the-api-surface.md), [`build-it/04e-rounding-bias-experiment.md`](build-it/04e-rounding-bias-experiment.md), [`build-it/04c-allocation-and-rounding-bias.md`](build-it/04c-allocation-and-rounding-bias.md).

---

### Q55. "Why is SimpleDateFormat dangerous?"

**The 30-second answer.** `SimpleDateFormat` inherits one mutable `protected Calendar calendar` field from `DateFormat`, and every call to `format` mutates it via `calendar.setTime(date)` before reading fields back off the same shared object. Cache one instance in a `static final` field and call it from multiple threads and one thread's `setTime` can land between another thread's `setTime` and its field reads — silently swapping dates between callers, with **no exception thrown at all**. `DateTimeFormatter` has no such state; it is an immutable printer/parser tree built once and read-only forever, which is why it is safe to cache and `SimpleDateFormat` is not.

**The 5-minute answer.** Measured on JDK 21.0.7: 8 threads, 50,000 `format` calls each on a shared `SimpleDateFormat`, each thread formatting its *own distinct* date — **503 distinct wrong output strings**, **0 exceptions**. Every one of eight workers observed the identical wrong date `2026-03-02`, belonging to none of them, which is exactly the signature of the shared `Calendar` being caught mid-write. Identical load through a single shared `static final DateTimeFormatter.ofPattern(...).withZone(...)` — **0 distinct wrong results**. The failure is worse than a crash because it's silent: values get written into `LedgerEntry.postedAt` or similar fields and the corruption is discovered weeks later at reconciliation, when the audit trail no longer matches the ledger it claims to describe. The fix is never a lock — it is to stop sharing the mutable state at all: construct a fresh `SimpleDateFormat` per use (correct but allocates), or migrate entirely to `java.time`'s `DateTimeFormatter`, which operates on `Instant` plus an explicit `ZoneId` rather than a zoneless `Date`, and whose immutability makes the `static final` field pattern not just permitted but the idiom. The identical defect exists one file over in `DecimalFormat.parse`, which shares a mutable field set the same way — measured, 8,693 distinct wrong results out of 1.6M parses under the same load shape, corrupting *amounts* rather than dates.

```java
public final class SettlementTimestampFormatter {

    // WRONG: shared, mutable, and every thread calls format() on the same instance.
    private static final SimpleDateFormat UNSAFE_FORMAT =
            new SimpleDateFormat("yyyy-MM-dd HH:mm:ss.SSS");

    public static String formatUnsafe(Date postedAt) {
        return UNSAFE_FORMAT.format(postedAt);   // races with every other caller
    }

    // RIGHT: immutable by construction, operates on Instant + an explicit zone.
    private static final DateTimeFormatter SAFE_FORMAT =
            DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm:ss.SSS")
                    .withZone(ZoneId.of("Europe/London"));

    public static String formatSafe(Instant postedAt) {
        return SAFE_FORMAT.format(postedAt);
    }
}
```

**The follow-up they will ask** — "Is `Calendar` itself thread-safe if I don't share a formatter?" No — `Calendar` is the same kind of mutable, unsynchronised state; the identical race applies to any shared, mutating `Calendar` instance regardless of whether a `SimpleDateFormat` wraps it.

**Where this is written** — [`date-and-time/02-date-and-time.md`](date-and-time/02-date-and-time.md), [`build-it/05d-concurrency-and-time-harnesses.md`](build-it/05d-concurrency-and-time-harnesses.md).

---

### Q56. "LocalDateTime vs Instant vs ZonedDateTime — what do you store for an event?"

**The 30-second answer.** `Instant` for anything that *happened* — a deposit capture, a stake settlement, a status transition — because it is a fixed point on the universal timeline with no zone to lose or misinterpret. `LocalDate` for anything that *is a date on someone's calendar* with no time or zone component — a date of birth, a coupon's expiry date. `LocalDateTime` is neither an instant nor safe for either job: it names a calendar/clock reading with no stated wall, so the identical text `2026-03-15T14:30` names a different real moment depending on which zone produced it, and there is no zero-argument way to turn it into an instant at all — that absence in the API is the type system telling you the truth.

**The 5-minute answer.** The proof is structural: `LocalDateTime` has no `toEpochMilli()` and no zero-argument `toInstant()`. The only two exits onto the timeline both *demand* the missing zone or offset as an argument — `reading.toInstant(ZoneOffset.of("+05:30"))` or `reading.atZone(ZoneId.of("Asia/Kolkata"))`. Two services in different zones writing `Movement.postedAt` as `LocalDateTime` produce readings that compare correctly *as text* but can be hours apart on the real timeline, silently misordering settlements with no exception anywhere — a `Europe/London` entry at 23:00 sorts before an `Asia/Kolkata` entry at 04:30 the same UTC instant, even though London happened later. The deciding test for which type a field needs: would a viewer in another zone need a *different local rendering* to understand the value correctly? An event time — yes, so store `Instant` and render per-viewer at the boundary. A date of birth — no, `1990-03-15` was that date everywhere on Earth, and running it through a zone conversion is exactly how implementations make someone a day younger or older by accident. Measured memory, which happens to favour correctness: `Instant` is 24.2 bytes, `LocalDate` 24.3, `LocalDateTime` 72.0, `ZonedDateTime` 96.0 — storing an event as `ZonedDateTime` instead of `Instant` for QuizStakes' 19.8M ledger entries/day costs roughly 1.9 GB/day instead of 475 MB/day, four times the allocation for zone information the event never needed since it's already unambiguous. Database mapping follows the same split: `TIMESTAMP WITH TIME ZONE` for `Instant` (normalises to UTC on write, discards the input zone), `TIMESTAMP WITHOUT TIME ZONE` only for a genuinely zoneless `LocalDateTime`, `DATE` for `LocalDate`.

```java
// WRONG: no statement of which wall clock this belongs to.
public record Movement(long id, BigDecimal amount, LocalDateTime postedAt) {}

// RIGHT: unambiguous regardless of which service or region wrote it.
public record Movement(long id, BigDecimal amount, Instant postedAt) {
    public String renderedFor(ZoneId viewerZone) {
        return postedAt.atZone(viewerZone).toLocalDateTime().toString();   // zone applied only at display
    }
}
```

**The follow-up they will ask** — "What about a *future* scheduled event, like a payout window?" That is neither `Instant` (the rules that apply at that future moment aren't fixed yet) nor `OffsetDateTime` (a frozen offset can't notice the rules changed) — it's `ZonedDateTime` with a named region, so it re-resolves against DST rules current when the date arrives; that's Q57's subject.

**Where this is written** — [`date-and-time/02-date-and-time.md`](date-and-time/02-date-and-time.md), [`date-and-time/02a-instant-local-and-zoned.md`](date-and-time/02a-instant-local-and-zoned.md).

---

### Q57. "Duration.ofDays(1) vs Period.ofDays(1) across DST."

**The 30-second answer.** `Duration` is a stopwatch — a fixed count of seconds and nanoseconds added on the *instant* timeline; `Duration.ofDays(1)` is always exactly 86,400 seconds, and the wall-clock label drifts wherever the rules put it. `Period` is a calendar — a count of years/months/days added on the *label* timeline, then re-resolved through the zone's rules; `Period.ofDays(1)` preserves the wall-clock reading and lets the elapsed time come out to whatever that particular calendar day is actually worth — 23 hours or 25 across a DST transition, not 24. They agree 363 days a year and diverge by exactly the DST offset on the two days that have one.

**The 5-minute answer.** Measured on JDK 21.0.7, tzdb 2025a, `Europe/London`'s 2026 spring-forward gap is `2026-03-29T01:00Z to +01:00` (a 1-hour gap) and the autumn overlap is `2026-10-25T02:00+01:00 to Z`. A bonus granted at local `23:00` on `2026-03-28`: `grant.plus(Duration.ofDays(1))` gives `2026-03-30T00:00+01:00[Europe/London]`, instant `2026-03-29T23:00:00Z` — exactly 24 hours later, and the *label* moved from 23:00 to 00:00 because the DST jump ate an hour along the way; `grant.plus(Period.ofDays(1))` gives `2026-03-29T23:00+01:00[Europe/London]`, instant `2026-03-29T22:00:00Z` — the label stayed at 23:00, and only **23 hours** of elapsed time passed. `Duration.between(...)` of the two results is `PT1H`. On the autumn transition the numbers invert: `Duration` gives 24h and the label slips *back*; `Period` holds the label and costs **25h**. The JDK 21 javadoc states the split exactly: "Date units operate on the local time-line... Time units operate on the instant time-line." Crucially, `ZonedDateTime.plusDays(1)` is `Period` semantics, not `Duration` — measured, `plusDays == plus(Period)` is `true`, `plusDays == plus(Duration)` is `false` — and `ChronoUnit.DAYS.between(zdtA, zdtB)` follows whichever timeline the *operand type* implies: on two `ZonedDateTime`s it counts complete 24-hour periods (truncating toward zero, so `PT22H30M` elapsed gives `DAYS.between == 0` even though the calendar date plainly advanced), while on the same two values reduced to `LocalDate` it gives `1`. For QuizStakes: the 30-day bonus expiry is written as "30 days from grant" in calendar terms, so it is a `Period.ofDays(30)` question — a client thinks in calendar days, and `Duration.ofDays(30)` would add exactly 720 hours and expire a still-live bonus an hour early or late across any DST transition the window spans, incorrectly reversing an unspent balance to `PROMOTIONAL_EXPENSE`. The identity vendor's 30-second timeout, by contrast, is unambiguously a `Duration` question — `Period` has no sub-day units at all, so it isn't even expressible there.

```java
ZonedDateTime grant = ZonedDateTime.of(LocalDateTime.of(2026, 3, 28, 23, 0), ZoneId.of("Europe/London"));
grant.plus(Duration.ofDays(1)).toInstant();   // 2026-03-29T23:00:00Z -- 24h elapsed, label drifted
grant.plus(Period.ofDays(1)).toInstant();     // 2026-03-29T22:00:00Z -- 23h elapsed, label held

public ZonedDateTime expiryOf(Instant grantedAt, ZoneId operatingZone) {
    return ZonedDateTime.ofInstant(grantedAt, operatingZone).plus(Period.ofDays(30));   // calendar rule
}
```

**The follow-up they will ask** — "What does `ZonedDateTime.of` do if the local label falls inside the gap?" It never throws — it silently shifts the label forward by exactly the gap's length and adopts the post-transition offset; `ofStrict` is the factory that refuses, throwing `DateTimeException` naming the gap.

**Where this is written** — [`date-and-time/02b-amounts-dst-and-tzdb.md`](date-and-time/02b-amounts-dst-and-tzdb.md), [`build-it/05i-dst-harness.md`](build-it/05i-dst-harness.md), [`date-and-time/03a-internals-zonerules-and-tzdb.md`](date-and-time/03a-internals-zonerules-and-tzdb.md).

---

### Q58. "How do you make time testable?"

**The 30-second answer.** Inject a `Clock` rather than calling the static, ambient `Instant.now()` or `LocalDate.now()` inside domain logic. `Clock` is an abstract class whose one job is answering "what time is it," passed into a constructor like any other dependency; every `java.time` factory that needs "now" — `Instant.now(Clock)`, `LocalDate.now(Clock)` — accepts one. In production, inject `Clock.systemUTC()`; in a test, substitute `Clock.fixed(Instant, ZoneId)` for a frozen instant or `Clock.offset(baseClock, Duration)` to deterministically cross a boundary — testing a 30-day bonus expiry without waiting 30 days or sleeping in the test.

**The 5-minute answer.** `Instant.now()` in a stack trace is indistinguishable from a network call, and is exactly as untestable: call it twice and by design it answers differently. `Clock` factories cover every case: `Clock.systemUTC()` (production default, no zone dependency), `Clock.system(ZoneId)` (production when the zone must travel with the clock), `Clock.fixed(Instant, ZoneId)` (a test clock frozen at one instant), `Clock.offset(Clock, Duration)` (shifted from a base, crossing boundaries deterministically), and `Clock.tick(Clock, Duration)`/`tickMillis`/`tickSeconds`/`tickMinutes` (truncates resolution on every read). The Spring-idiomatic shape is a `Clock` bean — `Clock.systemUTC()` wired in production, `Clock.fixed(...)` overridden in the test context — and it beats mocking a static `Instant.now()` call on every axis: mocking a static needs `mockito-inline`/`MockedStatic`, is global for its scope, does not compose across parallel tests, and hides the "current time" dependency inside the method body instead of declaring it in the constructor signature. There is a precision version-trap adjacent to this: on **Java 8**, `Clock.systemUTC()` was millisecond-resolution, so round-tripping through a millisecond database column was lossless by accident; from **Java 9 onward** the implementation switched to the host OS clock's best resolution — measured microsecond on this build (`getNano()` ending in three zeros, e.g. `444951000`) — so `now.equals(now.truncatedTo(ChronoUnit.MILLIS))` is now **false**, and a test that compares an `Instant` before and after a database round-trip through a `TIMESTAMP(3)` column fails intermittently on a diff of a few hundred microseconds. The fix is to truncate deliberately, on both sides, matched to the column's declared precision — never paper over the mismatch with a tolerance. `Clock` also generalises to any other ambient static that hides a dependency — `ZoneId.systemDefault()` and `UUID.randomUUID()` are the identical shape, and the identical fix (inject it) applies.

```java
public record Bonus(String bonusId, String clientId, BigDecimal amount, Instant grantedAt, Instant expiresAt) {
    public boolean isExpired(Instant asOf) { return !asOf.isBefore(expiresAt); }
}

public final class BonusService {
    private static final Duration EXPIRY_WINDOW = Duration.ofDays(30);
    private final Clock clock;

    public BonusService(Clock clock) { this.clock = clock; }

    public Bonus grant(String bonusId, String clientId, BigDecimal firstDeposit) {
        Instant now = clock.instant();
        BigDecimal amount = firstDeposit.multiply(new BigDecimal("0.10"))
                .setScale(2, RoundingMode.DOWN).min(new BigDecimal("100.00"));
        return new Bonus(bonusId, clientId, amount, now, now.plus(EXPIRY_WINDOW));
    }

    public boolean isExpired(Bonus bonus) {
        return !clock.instant().isBefore(bonus.expiresAt());
    }
}

class BonusServiceTest {
    private static final Instant GRANTED_AT = Instant.parse("2026-03-01T00:00:00Z");

    @Test
    void expiresExactlyThirtyDaysAfterGrant() {
        Clock atGrant = Clock.fixed(GRANTED_AT, ZoneOffset.UTC);
        Bonus bonus = new BonusService(atGrant).grant("BON-1", "CLI-1", new BigDecimal("420.00"));

        Clock justBefore = Clock.offset(atGrant, Duration.ofDays(30).minusSeconds(1));
        Clock justAfter = Clock.offset(atGrant, Duration.ofDays(30));

        assertFalse(new BonusService(justBefore).isExpired(bonus));
        assertTrue(new BonusService(justAfter).isExpired(bonus));   // crosses the boundary, no sleep
    }
}
```

**The follow-up they will ask** — "What's the Java 17 alternative when you only need the instant, not the zone?" `InstantSource` — a narrower interface exposing just `instant()`, which `Clock` implements.

**Where this is written** — [`date-and-time/02e-clock-precision-and-storage.md`](date-and-time/02e-clock-precision-and-storage.md), [`build-it/04f-clock-injection.md`](build-it/04f-clock-injection.md).

---

### Q59. "Is Java pass-by-value or pass-by-reference? Prove it."

**The 30-second answer.** Always pass-by-value, with no exception, for every type, in every version since 1.0. A method call copies the contents of the argument variable into a fresh local-variable slot in the callee's frame — that's the whole mechanism. For a reference type, what's copied is the *reference*, so the callee shares the caller's object but never the caller's variable. The proof is the asymmetry: mutating through a parameter is visible to the caller, but assigning a new value to the parameter is not — and if Java passed objects by reference, both would have to be visible.

**The 5-minute answer.** JLS 21 §8.4.1: a formal parameter is a *local variable* of the invoked method, initialised by copying the value of the argument expression — one frame, one slot, no link back to the caller's frame afterward. Measured on JDK 21.0.7: `voidStake(Reservation res, int attempt)` whose body does `res.status = "VOIDED"; res = new Reservation("REPLACED", 0); attempt = 2;` — inside the callee, `res` prints `REPLACED`/`0` and `attempt` prints `2`; back in the caller, `r` prints `VOIDED`/`420` (the original `stakeMinor`) and `attempt` still prints `1`. The mutation crossed the boundary; the reassignment did not. The bytecode makes it exact: `res.status = "VOIDED"` compiles to `putfield`, which writes into the field of the *one* heap object both frames' references designate — that's the crossing mechanism, and it crosses through the heap, never through the frames. `res = new Reservation(...)` compiles to `astore_0`, which writes into **local slot 0 of this frame only**; no instruction in the JVM's instruction set can reach another frame's local-variable array (JVMS §2.6.1). This is why a `swap(a, b)` cannot be written for *any* type in Java, primitive or reference — not because of immutability, but because the callee has no name for the caller's slots at all; it's unexpressible, not merely unimplemented. The workaround the JDK actually ships — `Collections.swap(list, i, j)` — sidesteps the whole problem by swapping *elements of a shared mutable object addressed by index*, never variables. The correct multi-value return is a record: `record SwapResult(Reservation first, Reservation second)`, with the *caller* rebinding its own two variables from the result — the only place in the language that can happen. The accurate name for this observable behaviour, from Liskov's CLU, is **call-by-sharing**: shares the object, never the variable.

```java
static void voidStake(Reservation res, int attempt) {
    res.status = "VOIDED";                        // putfield -- crosses via the heap, caller sees it
    res = new Reservation("REPLACED", 0);          // astore_0 -- this frame's slot only, caller sees nothing
    attempt = 2;                                   // istore_1 -- same
}
// caller: r.status prints VOIDED, attempt still 1
```

**The follow-up they will ask** — "So `String` gets no special treatment either?" Correct — a `String` parameter's reassignment is invisible for the identical reason a mutable type's reassignment is invisible; what immutability adds is narrower — it removes the *mutate* case entirely, since `String` has no mutator, leaving only the (already-invisible) reassign case.

**Where this is written** — [`immutability-and-design/03-pass-by-value.md`](immutability-and-design/03-pass-by-value.md), [`build-it/05c-dispatch-and-value-harnesses.md`](build-it/05c-dispatch-and-value-harnesses.md) (the pass-by-value harness lives here despite the file's slug).

---

### Q60. "Why can't you write a swap(a, b) method?"

**The 30-second answer.** Because a formal parameter is a local variable of the *callee's own frame* (JLS §8.4.1), and no JVM instruction can write into another frame's local-variable array (JVMS §2.6.1). A method body never has a handle on the caller's variables — only copies of their contents. Swapping the callee's own two parameter slots works perfectly and is completely invisible to the caller, because the caller's variables were never touched at all. This isn't a missing library feature; it's structurally unexpressible in the language as designed.

**The 5-minute answer.** Measured, JDK 21.0.7: `swap(Reservation first, Reservation second)` doing `Reservation scratch = first; first = second; second = scratch;` prints, *inside the method*, `first=PR-BANK second=PR-CARD` — a correct swap. One line later, the caller still prints `first=PR-CARD second=PR-BANK` — completely unswapped. The bytecode for `swap` is six instructions, and every one is a load from or store to a local slot of `swap`'s own frame: `aload_0; astore_2; aload_1; astore_0; aload_2; astore_1` — no `putfield`, no array store, no static write, nothing that touches memory shared with the caller. It is a perfectly correct swap of three local slots invisible to everyone else. Three shapes *do* work, and each costs something different: (1) return a record — `record SwapResult(Reservation first, Reservation second)`, caller reassigns its own two variables from the result; no shared mutable state, no allocation the caller didn't ask for, the type says what happened, and this is what you ship. (2) A one-element array or a two-slot holder as an out-parameter — `long[] out = new long[2]; swap(out);` — works, because the array *is* a heap object and both frames' references point at it, but it costs an allocation, has no compile-time arity check, and the signature no longer tells a reader what the method produces. (3) A mutable holder object, structurally identical to the array with names attached — same cost, same shape. This is exactly why `Collections.swap(List<?> list, int i, int j)` exists in the JDK and `Collections.swap(a, b)` does not: the list is standing in for the variables, and the two indices are standing in for the names — swapping list *elements* addressed by index is expressible; swapping *variables* named at the call site is not.

```java
record Reservation(String runId, long stakeMinorUnits) {}

static void swapAttempt(Reservation first, Reservation second) {
    Reservation scratch = first;
    first = second;
    second = scratch;
    System.out.println("inside swapAttempt: first=" + first.runId() + " second=" + second.runId());
}
// caller: swapAttempt(cardRun, bankRun); -- caller's own cardRun/bankRun are untouched afterward

record RunPair(Reservation first, Reservation second) {}

static RunPair swapped(Reservation first, Reservation second) {
    return new RunPair(second, first);
}

public static void main(String[] args) {
    Reservation cardRun = new Reservation("PR-CARD", 420);
    Reservation bankRun = new Reservation("PR-BANK", 315);
    swapAttempt(cardRun, bankRun);
    System.out.println("after swapAttempt: " + cardRun.runId() + " " + bankRun.runId());  // unchanged

    RunPair pair = swapped(cardRun, bankRun);
    cardRun = pair.first();          // the CALLER rebinds its own variables -- the only place this can happen
    bankRun = pair.second();
    System.out.println("after swapped(): " + cardRun.runId() + " " + bankRun.runId());    // genuinely swapped
}
```

**The follow-up they will ask** — "Would a hypothetical `ref`/`out` parameter in Java fix this?" Yes, structurally — that's exactly what C#'s `ref Reservation` or C++'s `Reservation&` add: an alias to the caller's storage rather than a copy of its contents, which Java deliberately never introduced because the language has no expression that denotes "the caller's slot" at all — no address-of, ever, by design.

**Where this is written** — [`immutability-and-design/03-pass-by-value.md`](immutability-and-design/03-pass-by-value.md), [`build-it/05c-dispatch-and-value-harnesses.md`](build-it/05c-dispatch-and-value-harnesses.md).

---

### Q61. "What is autoboxing, and where does it bite you?"

**The 30-second answer.** Autoboxing is a pure compile-time rewrite, introduced in Java 5 alongside generics, with zero runtime support: wherever a primitive sits where a reference is required, `javac` inserts `invokestatic Wrapper.valueOf(prim)`; wherever a reference sits where a primitive is required, it inserts `invokevirtual wrapper.primValue()`. It bites in four predictable places, all downstream of that one rewrite being invisible at the source level: boxing returns a *shared* instance for cached small values, so `==` between two wrappers is a reference comparison that flips at 127/128; unboxing is a virtual call, so a `null` wrapper throws `NullPointerException` at a line with no visible method call; a mixed `==` between a primitive and a wrapper *unboxes* and compares numerically, so the same operator means two different things depending on the operands' static types; and a boxed accumulator in a loop allocates once per iteration.

**The 5-minute answer.** Measured on JDK 21.0.7, `static Integer boxRetryCount(int n) { return n; }` is three instructions — `iload_0`, `invokestatic Integer.valueOf:(I)Ljava/lang/Integer;`, `areturn` — and the reverse is `aload_0`, `invokevirtual Integer.intValue:()I`, `ireturn`. Take the four traps in order. **Cache boundary:** `Integer big1 = 1000, big2 = 1000;` gives `big1 == big2` → **false** (1000 is outside `IntegerCache`'s −128..127, so each box is a distinct `new Integer`), but `big1 == 1000` (a primitive on one side) → **true**, because that comparison unboxes and compares values under JLS §15.21.1 — the *less* type-safe-looking form is the correct one, and adding a primitive to one side of a wrapper comparison makes it *more* correct, not less. **Null unboxing:** `int reserved = positionsByType.get("CLIENT_BONUS_RESERVED");` on an absent key throws, measured, `NullPointerException: Cannot invoke "java.lang.Integer.intValue()" because the return value of "java.util.Map.get(Object)" is null` — the target type `int` is what forces the `intValue()` call; the identical line with an `Integer` target type cannot throw. **Mixed `==` and null:** `nullInteger == 5` unboxes and **throws**, while `nullInteger == otherInteger` (both references) is `if_acmpne` and returns `false` with **no throw** — the null-safe-looking expression throws and the unsafe-looking one doesn't, entirely decided by the other operand's static type. **Cost:** `Long sum = 0L; for (...) { sum += minorUnits; }` is not one instruction — `Long` is immutable, so `+=` compiles to unbox (`longValue()`), `ladd`, rebox (`Long.valueOf`), reassign; measured **24 bytes allocated per iteration**, versus **0** for a primitive `long` accumulator over the identical loop. At QuizStakes' 2.8M reservations/day that's ~64 MiB/day of pure young-gen churn — not resident heap, since every box dies before the next iteration, but a rate that sets young-GC frequency. Structurally, boxing is *forced*, not optional, in exactly three cases, all one root cause: erasure means a generic type argument can never be a primitive — a collection element, any `Comparator<Integer>`/`Function<Integer,R>`, and `Optional<T>` all need reference types. There is a fourth, non-cost case: a genuinely nullable column (`Integer bonusCapMinorUnits`), where the box *carries information* rather than overhead — `ResultSet.getInt` silently maps SQL `NULL` to `0`, conflating "no bonus" with "bonus of zero," so `getObject`/`wasNull()` into an `Integer` is the correct, not merely safe, choice there.

```java
static int reservedBonus(Map<String, Integer> m) { return m.get("CLIENT_BONUS_RESERVED"); }  // throws on absent key
Long sum = 0L; for (int u : units) { sum += u; }   // 24 bytes/iteration -- unbox, ladd, rebox, reassign
long sum2 = 0L; for (int u : units) { sum2 += u; } // 0 bytes -- lload, iadd, lstore
```

**The follow-up they will ask** — "Why does `Character` not extend `Number`?" `Number`'s contract is four numeric conversion methods with no honest implementation for `boolean` and only a misleading one for `char` (the UTF-16 code unit, which is a real number that means nothing arithmetically) — so the platform declines to offer the operation rather than offer one that lets you accidentally average a list of characters.

**Where this is written** — [`wrappers-and-boxing/01-basics.md`](wrappers-and-boxing/01-basics.md), [`wrappers-and-boxing/01g-the-cost-of-boxing.md`](wrappers-and-boxing/01g-the-cost-of-boxing.md), [`wrappers-and-boxing/01c-unboxing-null.md`](wrappers-and-boxing/01c-unboxing-null.md), [`wrappers-and-boxing/01h-when-boxing-is-unavoidable.md`](wrappers-and-boxing/01h-when-boxing-is-unavoidable.md).

---

### Q62. "What does Math.abs(Integer.MIN_VALUE) return?"

**The 30-second answer.** `Integer.MIN_VALUE` itself — `-2147483648`, still negative. Two's complement has one more negative value than positive (2^32 patterns, one is zero, and the remaining odd count of non-zero patterns can't split evenly, so the extra one goes to the negatives), which means `+2147483648` has no 32-bit encoding at all. Negation is invert-then-add-one, and applying that to `0x80000000` carries all the way through the 31 inverted ones and lands back on the sign bit — a fixed point. `Math.abs`, specified as "negate if negative," returns the input unchanged.

**The 5-minute answer.** Count the patterns: 4,294,967,296 total, one is zero, leaving 4,294,967,295 non-zero — odd, so two's complement assigns 2,147,483,648 negatives against 2,147,483,647 positives, giving `Integer.MIN_VALUE = -2147483648` and `MAX_VALUE = 2147483647`. Work the negation of `MIN_VALUE` bit by bit: `0x80000000` inverted is `0x7FFFFFFF`, and adding 1 to that carries through all 31 set bits and rolls back to `0x80000000` — bit-identical to the input, so `-Integer.MIN_VALUE == Integer.MIN_VALUE`, measured. `Math.abs(int)`'s spec is literally "if the argument is negative, the negation of the argument" — apply that to `MIN_VALUE` and you get `MIN_VALUE` back, still negative; this is not a bug, it is the only 32-bit answer available. The production shape this bites: `Math.abs(hash) % shardCount` used to pick a shard from a hash code — for roughly one input in 4.29 billion (whenever the hash happens to equal `Integer.MIN_VALUE`), `Math.abs` returns the same negative value and `%` on it yields a *negative* index, throwing `ArrayIndexOutOfBoundsException` from code that has run correctly in production for months, at low frequency but with certainty eventually — at 19.8M ledger entries/day this is roughly once every 217 days. Two fixes, for two different intents. `Math.floorMod(hash, shardCount)` is non-negative for a positive divisor on *every* input, because it never negates at all, so it has no `Math.abs`-style fixed point — this is the correct fix for sharding/indexing. `Math.absExact(int)` (Java 15+) throws `ArithmeticException` on the minimum value rather than lying — correct when the caller genuinely needs "absolute value or an error," not a wraparound index.

```java
final class ShardingProbe {
    public static void main(String[] args) {
        System.out.println("Math.abs(MIN_VALUE)   = " + Math.abs(Integer.MIN_VALUE));   // -2147483648
        System.out.println("-Integer.MIN_VALUE    = " + (-Integer.MIN_VALUE));           // -2147483648
        System.out.println("floorMod(MIN, 8)      = " + Math.floorMod(Integer.MIN_VALUE, 8)); // 0
        try {
            Math.absExact(Integer.MIN_VALUE);
        } catch (ArithmeticException e) {
            System.out.println("absExact(MIN) threw: " + e.getMessage());
        }

        // The reservation-shard bug: Math.abs(hash) % shardCount goes negative once in 4.29 billion --
        // exactly when the hash equals MIN_VALUE and the shard count does not evenly divide 2^31.
        int reservationHash = Integer.MIN_VALUE;
        int badShard = Math.abs(reservationHash) % 100;      // Math.abs(MIN_VALUE) is still MIN_VALUE
        int goodShard = Math.floorMod(reservationHash, 100); // correct for every input, including MIN_VALUE itself
        System.out.println("badShard  = " + badShard);       // -48 -- ArrayIndexOutOfBoundsException risk
        System.out.println("goodShard = " + goodShard);      // 52, always non-negative
    }
}
```

**The follow-up they will ask** — "Does `(byte) 200` have the same shape?" Yes, the identical argument one width down: the literal `200` is an `int` (`0x000000C8`), the narrowing cast to `byte` keeps the low 8 bits `0xC8 = 11001000` and reinterprets the top bit as sign, giving `-56` — equivalently `200 - 256`; any `int v` casts to the `byte` congruent to `v` modulo 256 in `[-128, 127]`.

**Where this is written** — [`primitives-and-conversions/01a-integral-arithmetic.md`](primitives-and-conversions/01a-integral-arithmetic.md).

---

### Q63. "What does i = i++ do?"

**The 30-second answer.** Nothing — `i` is unchanged. Postfix `++` yields the variable's value *before* incrementing; the surrounding assignment then stores that pre-increment value back over the (already-happened) increment. It is not undefined behaviour the way `i = i++` would be in C — Java specifies the order completely (JLS §15.7 fixes operand evaluation order, §15.14.2 fixes postfix's value), so the answer is always the original value on every conforming JVM.

**The 5-minute answer.** Trace `int i = 2; i = i++;` through the compiler's own steps: (1) the assignment target `i` is remembered first (JLS §15.26.1); (2) the right-hand side `i++` is evaluated — its *value* is `2`, the pre-increment value, pushed to the operand stack; (3) as `i++`'s side effect, the local slot is set to `3`; (4) the assignment stores the *stacked* value, `2`, back into the remembered slot. Final value: **2** — step 3's write was overwritten by step 4. The bytecode makes the two-different-places mechanism visible: `iconst_2; istore_1` (`i = 2`), then `iload_1` (push the *current* value 2 onto the stack — a snapshot), `iinc 1, 1` (add 1 *in place* to the local slot, `i` becomes 3, stack untouched), `istore_1` (pop the *stacked* 2 back into the slot, clobbering the 3). `iinc` is the only JVM instruction that mutates a local without going through the operand stack at all — that asymmetry between where the snapshot lives (the stack) and where the increment lives (the slot) is the entire mechanism. Frame this in the domain as a stake-reservation retry counter: a `Reservation` field `attempt` capped at 3 — writing `attempt = attempt++;` intending "bump it" leaves `attempt` permanently unmoved, and the retry loop never reaches its cap; the audit trail shows four `ReserveStake` calls while `attempt` stays 0. The general lesson generalises past `++`: any expression that both reads and writes the *same* variable within one statement needs the value/side-effect split kept straight — `i++ + ++i` starting from `i=2` evaluates left-to-right (JLS §15.7): `i++` yields 2, bumps `i` to 3; `++i` bumps `i` to 4 first, then yields 4; the sum is `2 + 4 = 6`, and `i` ends at 4 — a single, fully-specified answer, where the identical C expression is undefined behaviour because C leaves the sequencing of the two increments unspecified.

```java
final class RetryCounterDemo {
    static int selfAssignIncrement() {
        int attempt = 2;
        attempt = attempt++;   // yields 2, bumps to 3, then stores 2 back
        return attempt;        // 2
    }

    static int correctBump() {
        int attempt = 2;
        attempt++;             // side effect only, value discarded -- nothing overwrites it
        return attempt;        // 3
    }

    static int mixed() {
        int attempt = 2;
        return attempt++ + ++attempt;   // left operand first (JLS 15.7): 2, then attempt=3;
    }                                    // right operand: attempt=4, yields 4; sum = 2 + 4 = 6

    public static void main(String[] args) {
        System.out.println(selfAssignIncrement()); // 2
        System.out.println(correctBump());         // 3
        System.out.println(mixed());                // 6
    }
}
```

**The follow-up they will ask** — "How do you write it so it actually bumps the counter?" `attempt++;` as a bare statement (side effect only, the discarded value is never stored anywhere), or `attempt = attempt + 1;` — never fuse the pre/post-increment operator with a self-assignment.

**Where this is written** — [`primitives-and-conversions/02-operators-and-expressions.md`](primitives-and-conversions/02-operators-and-expressions.md).

---

### Q64. "Why does byte b = 10; b += 300; compile?"

**The 30-second answer.** Because compound assignment carries a *hidden narrowing cast* that the explicit form doesn't. JLS §15.26.2 defines `E1 op= E2` as `E1 = (T)((E1) op (E2))`, where `T` is `E1`'s own type — so `b += 300` expands to `b = (byte)(b + 300)`, and that implicit `(byte)` is exactly what satisfies assignment conversion. `b = b + 300;` has no such cast, and `b + 300` is an `int` of value 310 that doesn't fit a `byte`, so `javac` rejects it with "possible lossy conversion from int to byte." After compiling, `b` holds **54**, not 310 — truncated, silently, with no warning of any kind.

**The 5-minute answer.** Work the truncation by hand: `b = 10` is `0000 1010`; promotion widens it to `int` for the addition, `10 + 300 = 310`; in 32 bits, `310 = 0000 0000 0000 0000 0000 0001 0011 0110`; the implicit `(byte)` cast keeps only the low 8 bits, `0011 0110 = 32+16+4+2 = 54`, and the sign bit of that byte is 0 so the result is positive 54. The bytecode makes the hidden cast a single visible instruction: `bipush 10; istore_0; iload_0; sipush 300; iadd; i2b; istore_0` — that `i2b` at offset 8 is the cast you never wrote, converting the `int` sum to `byte` by keeping the low 8 bits; `char` behaves identically via `i2c`. Why the language is built this way at all: without the implicit cast, `+=` would be entirely useless on any type narrower than `int`, because binary numeric promotion turns `byte + int` into `int` — `byte b = 0; b += 1;` wouldn't compile without it. The designers chose "always compiles, may silently truncate" over "never compiles on narrow types," and the removed safety net lands precisely where narrow types live: wire-format fields, byte parsers, `char` cursors. This generalises past integer narrowing, too — `int stakeCount = 0; stakeCount += 3.7;` compiles and leaves `stakeCount` at **3**, because the implicit cast applies to the *promoted* result of the arithmetic (here `double`), and `(int)` on a `double` is `d2i`, which truncates toward zero with no diagnostic; `+=` will happily swallow a floating-point right-hand side onto an integral left-hand side. Only plain `=` and the fully-explicit longhand `x = x + y` will refuse a lossy conversion — `+=` never will. On a QuizStakes-shaped `byte retries` parsed from a one-octet wire field, `retries += deltaFromHeader` wraps past 127 into negative values with zero warning, so a retry counter can read `-102` in the audit trail while a naive `retries < 3` cap check keeps passing forever. The fix on narrow integral fields is either to widen to `int` and range-check explicitly, or to write the cast by hand — `retries = (byte) (retries + 300);` — so a reviewer actually sees the truncation happening.

```java
byte retries = 10;
retries += 300;                 // compiles: i2b, 310 -> 54, no warning
// retries = retries + 300;     // error: possible lossy conversion from int to byte

int stakeCount = 0;
stakeCount += 3.7;               // compiles: d2i truncates toward zero -> 3, not a compile error
```

**The follow-up they will ask** — "Does compound assignment evaluate a side-effecting index expression twice?" No — JLS §15.26.2's expansion explicitly evaluates `E1` only once, so `positions[cursor++] += 5;` reads and writes `positions[0]` and leaves `cursor` at 1, not 2; this is one place the compound form is strictly *safer* than any naive longhand.

**Where this is written** — [`primitives-and-conversions/02a-assignment-and-bitwise.md`](primitives-and-conversions/02a-assignment-and-bitwise.md), [`primitives-and-conversions/03-conversions-and-contexts.md`](primitives-and-conversions/03-conversions-and-contexts.md).

---

**Leaves covered:** 5.1.49–5.1.64 (16 leaves)
**Leaves deferred:** none
**Diagrams included:** none
**Target version:** Java 21 LTS
**Lines:** 460
