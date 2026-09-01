# 03 Java Core — `Clock`, precision, leap seconds and what goes on the wire — INTERMEDIATE (§2.5, 2.5.23–2.5.27)

**Target version: Java 21 LTS.** | **Part 2 of 5** | [Index](../00-index.md)
Previous: [DateTimeFormatter: formatting, pattern traps and parsing strictness](02d-formatting-and-parsing.md) · Next: [java.time internals: the field layouts](03-internals-java-time.md)

This file owns testable time via `Clock`, the Java-9 precision change in `Instant.now()`, why `java.time` ignores leap seconds but not leap years, the three-way split between `Instant`/`currentTimeMillis`/`nanoTime`, and what representation to put on the wire or in storage. It does not own DST gaps/overlaps (`02b-amounts-dst-and-tzdb.md`) or field-level internals (`03-internals-java-time.md`, next in sequence). The question this file answers: once you have a correct instant, how do you get it deterministically in a test, keep its precision intact across a database round trip, and hand it to another system without ambiguity? Measured on Oracle JDK 21.0.7 (build 21.0.7+8-LTS-245), macOS aarch64, tzdb 2025a. No diagram in this file — see `02-date-and-time.md` (D-075, D-080), `02b-amounts-dst-and-tzdb.md` (D-077, D-078) and `02c-temporal-arithmetic-and-adjusters.md` (D-079) for the pictures covering adjacent material.

---

## 1. Inject a `Clock` (2.5.23)

`Instant.now()` is a static call to the outside world — in a stack trace it is indistinguishable from a network call, and like any such call it makes the surrounding code untestable and non-deterministic: run it twice and it answers differently by design. `Clock` is the seam Java provides for this: an abstract class with exactly one job, answering "what time is it", that you pass into a constructor rather than reach for from inside domain logic. Java 17 added `InstantSource` as a narrower interface for code that only ever needs the instant, not the zone `Clock` also carries.

### Why it exists

Before `Clock` (pre-Java 8), testing time-dependent code meant either sleeping in the test, wrapping `System.currentTimeMillis()` behind a hand-rolled seam, or reaching for a static-mocking library. `Clock` makes the seam part of the standard library, so every `java.time` type that needs "now" — `Instant.now(Clock)`, `LocalDate.now(Clock)`, `ZonedDateTime.now(Clock)` — accepts one as a parameter.

### How it works

| Factory | Purpose |
|---|---|
| `Clock.systemUTC()` | production default — no zone dependency, which is the entire point |
| `Clock.system(ZoneId)` | production, when the zone genuinely needs to travel with the clock |
| `Clock.fixed(Instant, ZoneId)` | a test clock frozen at one instant |
| `Clock.offset(Clock, Duration)` | a test clock shifted from a base clock — how you test a 30-day bonus expiry without waiting 30 days |
| `Clock.tick(Clock, Duration)` and `tickMillis`/`tickSeconds`/`tickMinutes` | a clock that truncates to the given resolution on every read |

Measured, §6.17: `Clock.systemUTC().instant()` gave `2026-08-29T09:57:50.444986Z`; `Clock.tickMillis(ZoneOffset.UTC).instant()` gave `2026-08-29T09:57:50.445Z` — the tick clock truncates (with rounding) to millisecond resolution on every call, which is sometimes exactly what production wants, not only tests (see concept 2).

```java
public record Bonus(
        String bonusId,
        String clientId,
        BigDecimal amount,
        Instant grantedAt,
        Instant expiresAt,
        BonusStatus status) {

    public boolean isExpired(Instant asOf) {
        return !asOf.isBefore(expiresAt);
    }
}

public enum BonusStatus { GRANTED, ACTIVE, CONSUMED, EXPIRED, CLAWED_BACK }

public final class BonusService {

    private static final BigDecimal GRANT_RATE = new BigDecimal("0.10");
    private static final BigDecimal GRANT_CAP = new BigDecimal("100.00");
    private static final Duration EXPIRY_WINDOW = Duration.ofDays(30);

    private final Clock clock;

    public BonusService(Clock clock) {
        this.clock = clock;
    }

    public Bonus grant(String bonusId, String clientId, BigDecimal firstDeposit) {
        BigDecimal amount = firstDeposit.multiply(GRANT_RATE)
                .setScale(2, RoundingMode.DOWN)
                .min(GRANT_CAP);
        Instant now = clock.instant();
        return new Bonus(bonusId, clientId, amount, now, now.plus(EXPIRY_WINDOW),
                BonusStatus.GRANTED);
    }

    public boolean isExpired(Bonus bonus) {
        return bonus.isExpired(clock.instant());
    }
}
```

```java
class BonusServiceTest {

    private static final Instant GRANTED_AT = Instant.parse("2026-03-01T00:00:00Z");

    @Test
    void grantsTenPercentCappedAtOneHundred() {
        Clock fixed = Clock.fixed(GRANTED_AT, ZoneOffset.UTC);
        BonusService service = new BonusService(fixed);

        Bonus bonus = service.grant("BON-1", "CLI-1", new BigDecimal("2000.00"));

        assertEquals(new BigDecimal("100.00"), bonus.amount());
        assertEquals(GRANTED_AT.plus(Duration.ofDays(30)), bonus.expiresAt());
    }

    @Test
    void expiresExactlyThirtyDaysAfterGrant() {
        Clock atGrant = Clock.fixed(GRANTED_AT, ZoneOffset.UTC);
        BonusService service = new BonusService(atGrant);
        Bonus bonus = service.grant("BON-2", "CLI-2", new BigDecimal("420.00"));

        Clock justBefore = Clock.offset(atGrant, Duration.ofDays(30).minusSeconds(1));
        Clock justAfter = Clock.offset(atGrant, Duration.ofDays(30));

        assertFalse(bonus.isExpired(justBefore.instant()));
        assertTrue(bonus.isExpired(justAfter.instant()));
    }
}
```

`Clock.offset` crosses the 30-day expiry boundary deterministically, one second on either side, with no `Thread.sleep` and no dependency on when the test happens to run.

The Spring-idiomatic arrangement is a `Clock` bean — `@Bean Clock clock() { return Clock.systemUTC(); }` in production configuration, overridden with `Clock.fixed(Instant, ZoneId)` in the test context. Mocking a static `Instant.now()` call instead needs `mockito-inline` or `MockedStatic`, and is worse on every axis: the mock is global for the scope it's active in, it does not compose across parallel tests, and it hides the dependency on "current time" inside the method body instead of declaring it in the constructor signature. Guide 16 (Testing) owns the full pattern.

**Insight:** the same seam argument applies to `ZoneId.systemDefault()` (`02a-instant-local-and-zoned.md`) and to `UUID.randomUUID()` — any static call to ambient, non-deterministic state is the identical testability problem, and the identical fix is to inject it.

> `Clock` turns "what time is it" from an ambient static call into an explicit, injectable dependency, which is what makes time-dependent domain logic deterministically testable.

## 2. `Instant.now()`'s precision changed (2.5.24)

**Pitfall:** a test that compared two `Instant`s for equality passed reliably on Java 8 and started failing on Java 9+ with a diff of a few hundred microseconds — and got blamed on the database.

What used to be true, on **Java 8**: `Clock.systemUTC()` was specified and implemented at **millisecond** resolution, so `Instant.now()` always had a `nano` value ending in six zeros. A round trip through a millisecond-precision database column was lossless — by accident, because the source value never had sub-millisecond content to lose. What is true from **Java 9 onward**: the implementation switched to the best resolution the host OS clock offers, which is microseconds on most platforms and nanoseconds where the OS allows it. That accidental losslessness is gone.

Measured on JDK 21.0.7: `Instant.now()` gave `2026-08-29T09:57:50.444951Z`, `getNano()` = `444951000`. **The trailing three zeros are the tell**: six significant fractional digits, i.e. microsecond resolution, on this macOS aarch64 build. Then the failure, measured: `now.truncatedTo(ChronoUnit.MILLIS)` gives `2026-08-29T09:57:50.444Z`, and `now.equals(now.truncatedTo(ChronoUnit.MILLIS))` is **`false`**. That is the entire failure mode: write an `Instant` at microsecond precision into a `TIMESTAMP(3)` column, read it back at millisecond precision, and an `assertEquals` fails on a value that is correct to the millisecond and only disagrees below it.

**VERSION TRAP:** this is exactly the kind of thing an interviewer who learned `java.time` on Java 8 will still describe as "millisecond precision, like `Date`" — it was true then and it stopped being true in Java 9.

The fix, stated as a rule: **truncate deliberately, at the boundary, on both sides** — call `truncatedTo(ChronoUnit.MILLIS)` (or whatever unit matches the column) before persisting, and apply the same truncation to any in-memory value you compare against after reading back. Do not paper over the mismatch with an equality tolerance; make the precision explicit instead, matched to the column's declared precision. `Clock.tickMillis(ZoneOffset.UTC)` (concept 1) is the production-side way to get this guarantee at the source rather than after the fact. Cross-reference `03c-internals-precision-scale-and-legacy-bridging.md` for the internal representation, and `02d-formatting-and-parsing.md` concept 5 for `Date.from(Instant)`, which truncates to milliseconds on the legacy path for the identical underlying reason.

> `Instant.now()` returns microsecond resolution on Java 9+ (nanosecond where the OS allows), not the millisecond resolution Java 8 guaranteed, and the two `Instant`s either side of a `truncatedTo` call are not `equals`.

## 3. Leap seconds and leap years (2.5.25)

These are two unrelated things this leaf pairs together, so treat them separately.

### Leap seconds

`java.time` does not model them at all. The `Instant` Javadoc defines the **"Java time-scale"**, which requires every calendar day to contain exactly 86,400 seconds — a UTC leap second literally cannot be represented in this scale, and no `Instant` value is ever `:60`. What happens in practice is that the JDK relies on the host system clock, and the host typically smears or steps the leap second (NTP implementations differ in how), so from `java.time`'s point of view a second is simply the slightly wrong length for a while, invisibly. The practical consequence: a duration measured across a leap-second event can be off by up to a second — irrelevant for a `PaymentRun` settlement window, relevant only for a system whose correctness genuinely depends on sub-second UTC alignment. This is a deliberate simplification the Javadoc states outright, not an oversight, and the payoff is that `Duration` arithmetic stays exact and `86400` is reliably one day, every day.

### Leap years

The proleptic ISO calendar rule: divisible by 4, except centuries, except centuries divisible by 400. Measured, `Year.isLeap`: 2026 → `false`, 2028 → `true`, **1900 → `false`**, 2000 → `true`. `Year.isLeap` is a static method; `YearMonth.lengthOfMonth()` and `Year.length()` are the derived queries that use it, and this is the same clamping rule `02c-temporal-arithmetic-and-adjusters.md` measured for `plusMonths` landing on a shortened February.

**Interview:** "is 1900 a leap year" is asked precisely because the naive divisible-by-4 rule says yes and the correct, century-aware answer is no — 1900 is a century not divisible by 400.

> `java.time` guarantees every day has exactly 86,400 seconds by construction (leap seconds are simply not representable), while leap years are a fully modeled, queryable calendar rule via `Year.isLeap`.

## 4. Three clocks, three questions (2.5.26)

`Instant.now()`, `System.currentTimeMillis()` and `System.nanoTime()` answer genuinely different questions and are not interchangeable.

| | Question it answers | Monotonic | Epoch-anchored | Resolution on JDK 21.0.7 | QuizStakes use |
|---|---|---|---|---|---|
| `Instant.now()` | What wall-clock moment is this | No — an NTP adjustment can move it backwards | Yes | Microsecond (measured) | What `Movement.postedAt` stores |
| `System.currentTimeMillis()` | Same question, millisecond resolution | No — same caveat | Yes | Millisecond | No reason to prefer over `Instant` in new code; bare `long`, no type safety, no zone |
| `System.nanoTime()` | How much time has elapsed since some arbitrary origin | Yes | No — origin is meaningless and can differ between JVM runs | Nanosecond-ish | Timing a PSP authorise call against the p50 240ms / p99 11s figures |

The verdict as one rule: **never subtract two `Instant`s or two `currentTimeMillis()` values to measure elapsed time** — a clock adjustment mid-measurement can produce a negative or wildly inflated duration, because neither is monotonic. And **never store a `nanoTime()` value** — it is only comparable to another `nanoTime()` reading from the same JVM run; persisted, transmitted, or compared across processes it means nothing.

**Pitfall:** timing a card-authorisation call with `System.currentTimeMillis()` end minus start, and finding a negative latency show up in the metrics after an NTP correction landed mid-call.

```java
public final class PspLatencyTimer {

    public <T> T timeAuthorise(Supplier<T> call, LongConsumer recordNanos) {
        long startNanos = System.nanoTime();
        try {
            return call.get();
        } finally {
            recordNanos.accept(System.nanoTime() - startNanos);
        }
    }
}
```

`System.nanoTime()` is the only correct choice here because it is monotonic — a single subtraction of two readings from the same JVM run cannot go negative from a clock adjustment the way `Instant.now()` or `currentTimeMillis()` readings can.

> `Instant.now()` and `System.currentTimeMillis()` answer "what time is it" and can jump; `System.nanoTime()` answers "how much time elapsed" and cannot go backwards, but its value is meaningless outside the process that produced it.

## 5. What goes on the wire and into storage (2.5.27)

| Representation | Example | Cost |
|---|---|---|
| ISO-8601 string | `2026-03-15T14:30:45.123456789Z` | ~30 bytes; self-describing, human-readable in a log, unambiguous about the zone, sorts lexicographically in chronological order when normalised to `Z` |
| Epoch millis (number) | `1774000000123` | 8 bytes; cheap to compare and index, but no zone, no precision beyond millisecond, unreadable to a human debugging a payload |
| Locale-formatted string | `15/03/2026 14:30` | Never correct on a machine boundary — the pattern-letter and locale traps `02d-formatting-and-parsing.md` measured apply in full |

The rules the leaf is really asking for: ISO-8601 by default on any external contract, because the cost of the extra bytes is nothing against the cost of ambiguity between two systems. Epoch millis only inside a system you control end to end, where compactness has been measured to actually matter. A locale-formatted string only on the last hop to a human, generated at render time and never persisted.

To make ISO-8601 work in practice, add three details: normalise to `Z` rather than a local offset, so lexical and chronological order agree; emit the same number of fractional digits on every value, so lexical comparison is total rather than accidentally string-length-dependent; and decide the precision explicitly per concept 2, rather than letting whatever the platform clock happens to return leak into the contract unexamined.

Jackson serialises `Instant` as a decimal epoch-seconds number by default, and needs the `JavaTimeModule` registered plus `SerializationFeature.WRITE_DATES_AS_TIMESTAMPS` disabled to emit ISO-8601 instead — this single missing configuration is the most common source of a wire contract nobody actually intended to ship. The corresponding OpenAPI type is `string` with `format: date-time` for an instant and `format: date` for a `LocalDate`. Guide 12 (API design) owns the full serialization contract.

For storage, guide 09 owns the column-type mapping in detail and `02a-instant-local-and-zoned.md` owns the decision of which Java type maps to which column type at all; the short version is `TIMESTAMP WITH TIME ZONE` for an `Instant`, `DATE` for a `LocalDate`, with the column's fractional precision matched to whatever you truncate to per concept 2.

None of this is expensive to get right. From §6.11: an `Instant` is 24 bytes measured (12-byte header + 8-byte `seconds` + 4-byte `nanos`), so 19,800,000 ledger entries/day × 24 bytes ≈ 475 MB/day just to hold the timestamps — doing the ISO-8601-and-truncate-deliberately version costs nothing over doing it wrong.

**Interview:** "why not just use epoch millis everywhere, it's smaller" — the answer names the two things it loses that ISO-8601 keeps for free: the zone/offset information and human readability in a log, and that 22 extra bytes per timestamp is immaterial next to either.

> Prefer ISO-8601 normalised to `Z` with an explicit, fixed fractional precision for any contract crossing a process boundary; epoch millis is an optimization for a closed system, and a locale-formatted string belongs only at the point of human display.

---

## Pitfalls

### "`Clock.systemUTC()` calls are fine to sprinkle through domain logic since they're all reading the same clock anyway"

**Wrong**

```java
public boolean isExpired(Bonus bonus) {
    return !Clock.systemUTC().instant().isBefore(bonus.expiresAt());
}
```

Compiles, works, and is untestable: any test exercising this method either sleeps for 30 days or cannot deterministically cross the expiry boundary at all.

**Right**

```java
public final class BonusService {
    private final Clock clock;
    public BonusService(Clock clock) { this.clock = clock; }

    public boolean isExpired(Bonus bonus) {
        return !clock.instant().isBefore(bonus.expiresAt());
    }
}
```

A test constructs `new BonusService(Clock.fixed(Instant, ZoneId))` or `Clock.offset(Clock, Duration)` and crosses the boundary in a single assertion, with no wall-clock dependency.

**Why people believe it:** `Clock.systemUTC()` is a one-line static call with no visible downside at the call site — the cost only appears later, when someone tries to write a deterministic test around the method.

### "`Instant.now()` round-trips through a millisecond database column without loss, like it always has"

**Wrong**

```java
Instant now = Instant.now();
saveToTimestampColumn(now);               // column is TIMESTAMP(3)
Instant reloaded = loadFromColumn();
assertEquals(now, reloaded);              // fails on JDK 9+
```

Fails intermittently with a diff of a few hundred microseconds, because `now` carries microsecond resolution on Java 9+ and the column only stores milliseconds.

**Right**

```java
Instant now = Instant.now().truncatedTo(ChronoUnit.MILLIS);
saveToTimestampColumn(now);
Instant reloaded = loadFromColumn();
assertEquals(now, reloaded);              // both sides at the same precision
```

Truncate on the write side (or on both sides symmetrically) to match the column's declared precision, rather than comparing values at two different resolutions.

**Why people believe it:** it genuinely was lossless on Java 8, where `Clock.systemUTC()` itself only produced millisecond resolution — the assumption is version-stale, not baseless.

### "Timing an operation by subtracting two `Instant.now()` (or `currentTimeMillis()`) readings gives elapsed time"

**Wrong**

```java
Instant start = Instant.now();
callPsp();
Instant end = Instant.now();
Duration elapsed = Duration.between(start, end);   // can be negative
```

An NTP correction landing between `start` and `end` can move the wall clock backwards, producing a negative or wildly wrong `Duration` — with no exception to signal it.

**Right**

```java
long startNanos = System.nanoTime();
callPsp();
long elapsedNanos = System.nanoTime() - startNanos;
```

`System.nanoTime()` is monotonic within a single JVM run, so a single subtraction of two of its readings cannot go backwards regardless of what the wall clock does mid-measurement.

**Why people believe it:** `Instant` and `currentTimeMillis()` are the obvious, ubiquitous choice for "what time is it", and their non-monotonicity only ever shows up under an NTP adjustment that most local testing never triggers.

---

## Cheat sheet

| Thing | Fact (Java 21 LTS) |
|---|---|
| `Clock` role | Injectable seam for "what time is it"; replaces static `Instant.now()` calls in domain logic |
| `InstantSource` | Java 17+, narrower interface than `Clock` for code needing only the instant |
| `Clock.systemUTC()` | Production default, no zone dependency |
| `Clock.system(ZoneId)` | Production, when the zone must travel with the clock |
| `Clock.fixed(Instant, ZoneId)` | Test clock frozen at one instant |
| `Clock.offset(Clock, Duration)` | Test clock shifted from a base — crosses boundaries deterministically |
| `Clock.tickMillis`/`tickSeconds`/`tickMinutes` | Truncates resolution on every read |
| Measured `tickMillis` vs `systemUTC` | `2026-08-29T09:57:50.445Z` vs `2026-08-29T09:57:50.444986Z` |
| Spring pattern | `Clock` bean, `systemUTC()` in prod, `fixed(Instant, ZoneId)` in test context |
| Mocking static `Instant.now()` | Needs `mockito-inline`/`MockedStatic`; global scope, doesn't compose — worse than injection |
| Java 8 `Instant.now()` resolution | Millisecond (VERSION TRAP — interviewers still ask for this) |
| Java 9+ `Instant.now()` resolution | Microsecond typical, nanosecond where OS allows |
| Measured `Instant.now()` | `2026-08-29T09:57:50.444951Z`, `getNano()` = `444951000` |
| `truncatedTo(MILLIS)` vs untruncated | `now.equals(now.truncatedTo(MILLIS))` → `false` |
| Precision mismatch fix | Truncate deliberately at the boundary, on both sides; never tolerance-compare |
| Leap seconds in `java.time` | Not modeled — Java time-scale defines every day as exactly 86,400 seconds |
| Leap-second real-world effect | Host clock smears/steps it; sub-second UTC alignment only, irrelevant to `PaymentRun` windows |
| Leap year rule | Divisible by 4, except centuries, except centuries divisible by 400 |
| Measured `Year.isLeap` | 2026 false, 2028 true, 1900 false, 2000 true |
| `Instant.now()` question | What wall-clock moment is this — not monotonic, epoch-anchored |
| `System.currentTimeMillis()` question | Same as `Instant.now()`, millisecond, bare `long`, no zone |
| `System.nanoTime()` question | How much time has elapsed — monotonic, not epoch-anchored |
| Comparing `nanoTime()` across JVMs | Meaningless — origin differs per run |
| Never do | Subtract two `Instant`/`currentTimeMillis()` values for elapsed time |
| Never do | Persist or transmit a `nanoTime()` value |
| ISO-8601 wire format | Default choice; ~30 bytes, zone-unambiguous, sorts correctly when normalised to `Z` |
| Epoch millis wire format | 8 bytes; no zone, no sub-millisecond precision; closed-system optimization only |
| Locale-formatted string | Human display only, generated at render time, never persisted |
| ISO-8601 sorting requirement | Normalise offset to `Z`; fixed fractional-digit count |
| Jackson `Instant` default | Epoch-seconds number; needs `JavaTimeModule` + `WRITE_DATES_AS_TIMESTAMPS` disabled for ISO-8601 |
| OpenAPI type, `Instant` | `string`, `format: date-time` |
| OpenAPI type, `LocalDate` | `string`, `format: date` |
| Storage column, `Instant` | `TIMESTAMP WITH TIME ZONE` |
| Storage column, `LocalDate` | `DATE` |
| `Instant` memory footprint | 24 bytes measured |
| QuizStakes daily `Instant` cost | 19.8M × 24 bytes ≈ 475 MB/day |

---

## Self-test

**Q1.** Why is injecting a `Clock` better than calling `Instant.now()` directly inside domain logic, and what is the Java 17 alternative for code that only needs the instant?

<details><summary>Answer</summary>

`Instant.now()` is a static call to ambient, non-deterministic state — it makes the surrounding code untestable without sleeping or static-mocking. Injecting a `Clock` turns "what time is it" into an explicit dependency you can swap for `Clock.fixed` or `Clock.offset` in a test, crossing time boundaries deterministically. Java 17 added `InstantSource` as a narrower interface for code that only needs the instant, not the zone `Clock` also carries.

</details>

**Q2.** What resolution does `Instant.now()` give on Java 21, what did it give on Java 8, and why does that matter for a database round trip?

<details><summary>Answer</summary>

On Java 8, `Clock.systemUTC()` was specified at millisecond resolution, so a round trip through a millisecond-precision `TIMESTAMP` column was lossless by accident. On Java 9 and later, including 21, resolution comes from the best the OS clock offers — measured as microsecond on this build (`getNano()` ending in `000`). Writing that value into a millisecond column and comparing with `equals` after reading it back now fails, because the sub-millisecond digits are gone from the column but not from the in-memory comparison value unless you truncate both sides deliberately.

</details>

**Q3.** Does `java.time` ever produce an `Instant` at `:60` seconds for a leap second? Why or why not?

<details><summary>Answer</summary>

No. The Java time-scale, as defined in the `Instant` Javadoc, requires every calendar day to have exactly 86,400 seconds, so a UTC leap second has no representation in it at all. In practice the host OS clock smears or steps the leap second, so `java.time` just sees a second that's slightly the wrong length for a while. This is a deliberate simplification that keeps `Duration` arithmetic exact, not an oversight.

</details>

**Q4.** Is 1900 a leap year? What's the rule and why does the naive version get it wrong?

<details><summary>Answer</summary>

No, 1900 is not a leap year. The rule is: divisible by 4, except century years, except century years divisible by 400. 1900 is a century year not divisible by 400, so it's excluded. The naive "divisible by 4" rule says yes, which is exactly why this is a common interview trap — 2000, by contrast, is divisible by 400 and is a leap year.

</details>

**Q5.** Why is it wrong to measure elapsed time by subtracting two `Instant.now()` or two `System.currentTimeMillis()` readings, and what should you use instead?

<details><summary>Answer</summary>

Neither `Instant.now()` nor `System.currentTimeMillis()` is monotonic — an NTP clock adjustment between the two readings can move the wall clock backwards, producing a negative or nonsensical duration. `System.nanoTime()` is monotonic within a single JVM run and is the correct choice for measuring elapsed time, such as a PSP call's latency, though its absolute value is meaningless outside that run and must never be stored or compared across processes.

</details>

**Q6.** Why should a wire contract prefer an ISO-8601 string over epoch millis by default, and when is epoch millis actually the right call?

<details><summary>Answer</summary>

ISO-8601 carries the zone/offset unambiguously and is human-readable in a log, at a cost of roughly 30 bytes versus epoch millis's 8 — a cost that's immaterial against the cost of an ambiguous or zone-less timestamp on an external contract. Epoch millis is the right call only inside a system you control end to end, where compactness has actually been measured to matter, and even then it sacrifices zone information and precision beyond milliseconds.

</details>

---

## Open questions

None — every claim in this file traces to brief §6.11, §6.13, §6.16, §6.17, or to the `Instant`/`Clock` Javadoc and the ISO-8601 standard named directly.

---

**Leaves covered:** 2.5.23–2.5.27 (5 leaves)
**Leaves deferred:** none
**Diagrams included:** none
**Target version:** Java 21 LTS
**Lines:** 387
