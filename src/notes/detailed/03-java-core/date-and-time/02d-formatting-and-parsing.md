# 03 Java Core — `DateTimeFormatter`: formatting, pattern traps and parsing strictness — INTERMEDIATE (§2.5, 2.5.18–2.5.22)

**Target version: Java 21 LTS.** | **Part 2 of 5** | [Index](../00-index.md)
Previous: [Temporal arithmetic, adjusters and the SPI layer](02c-temporal-arithmetic-and-adjusters.md) · Next: [Clock, precision and storage](02e-clock-precision-and-storage.md)

This file owns `DateTimeFormatter` construction, the pattern-letter traps, parsing strictness, `DateTimeParseException`, and legacy `Date`/`Calendar`/`Timestamp` interop. It does not own zone gaps/overlaps (`02b-amounts-dst-and-tzdb.md`), temporal arithmetic (`02c-temporal-arithmetic-and-adjusters.md`), or the `SimpleDateFormat` race (`02-date-and-time.md`, which also owns diagram D-080). The question this file answers: given a correct `Instant` or `LocalDate`, how do you turn it into text without corrupting it, and how do you turn text back without silently accepting garbage? Measured on Oracle JDK 21.0.7 (build 21.0.7+8-LTS-245), macOS aarch64, tzdb 2025a. No diagram in this file — see `02-date-and-time.md` (D-075, D-080), `02b-amounts-dst-and-tzdb.md` (D-077, D-078) and `02c-temporal-arithmetic-and-adjusters.md` (D-079) for the pictures covering adjacent material.

---

## 1. `DateTimeFormatter` is immutable, and what ships built in (2.5.18)

A `DateTimeFormatter` is not a wrapper around a mutable `Calendar` the way `SimpleDateFormat` is. It is a **printer/parser tree, built once** by `DateTimeFormatterBuilder` (directly, or under the hood of `ofPattern`) and never mutated again. Formatting walks that tree read-only against the `TemporalAccessor` you pass in; nothing about the call touches instance state. That is why `withZone`, `withLocale` and `withResolverStyle` each return a **new** `DateTimeFormatter` rather than mutating the receiver — the old one still exists, unchanged, and anyone still holding a reference to it is unaffected.

### Why it exists

`SimpleDateFormat` keeps a `protected Calendar calendar` field that `format` mutates on every call (`calendar.setTime(date)` then reads fields back out). Two threads sharing one instance interleave a write from thread A with a read from thread B, and thread B's output carries thread A's date. `java.time`'s designers built the formatter as an immutable tree specifically to remove that failure mode at the type level rather than document it away.

### How it works

Measured, §6.18: 8 threads, 50,000 formats each (400,000 total), each thread formatting its own distinct `Instant`, one shared `DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm:ss.SSS").withZone(ZoneId.of("Europe/London"))` — **0 distinct wrong results, 0 exceptions.** Contrast the identical load against one shared `SimpleDateFormat`: 504 distinct wrong output strings, 0 exceptions (that measurement, and D-080, belong to `02-date-and-time.md`). The `DateTimeFormatter` result is not luck; there is no mutable field for two threads to race on. **A `static final DateTimeFormatter` field is correct and idiomatic** — build it once per pattern, share it everywhere, never synchronize around it.

### A concrete example

| Constant | Example output | QuizStakes use |
|---|---|---|
| `ISO_INSTANT` | `2026-03-15T14:30:45.123456789Z` | `Movement.postedAt` on the wire |
| `ISO_LOCAL_DATE` | `2026-03-15` | a client's date of birth |
| `ISO_OFFSET_DATE_TIME` | `2026-03-15T14:30:45+01:00` | echoing back a JSON body that carried an offset |
| `RFC_1123_DATE_TIME` | `Thu, 15 Mar 2026 14:30:45 GMT` | HTTP headers only |

| Construction | When it is right |
|---|---|
| `ofPattern(String)` | a fixed machine format you control on both ends |
| `ofLocalizedDateTime(FormatStyle)` | human-facing output, locale-driven — **never** for a machine boundary |
| `DateTimeFormatterBuilder` | optional sections, case-insensitive matching, or a default for a missing field — `appendPattern`, `optionalStart`/`optionalEnd`, `parseCaseInsensitive`, `parseDefaulting` |

**Insight:** `ofPattern` with no `Locale` argument uses the platform default locale, so a pattern containing `MMM` or `EEE` renders different text on a differently-configured host — the same hidden-host-dependency class as `ZoneId.systemDefault()` (`02a-instant-local-and-zoned.md`) and the default-locale `NumberFormat` trap (`../numbers-and-money/02e-parsing-and-formatting-numbers.md`). Always pass `Locale.ROOT` for a machine format: `DateTimeFormatter.ofPattern("yyyy-MM-dd", Locale.ROOT)`.

> A `DateTimeFormatter` is an immutable printer/parser tree built once by `DateTimeFormatterBuilder`; thread safety is structural, not achieved by locking.

## 2. Pattern-letter traps (2.5.19)

**Pitfall:** reaching for an uppercase pattern letter because it "looks more formal" than the lowercase one — `YYYY`, `DD`, `MM` where a minute is meant, `HH` where 12-hour is meant. Every one of these compiles, every one of these silently produces a wrong value.

### The New Year's Eve bug

Measured: `LocalDate.of(2025,12,29).format(ofPattern("yyyy-MM-dd"))` gives `2025-12-29`; the same date with `ofPattern("YYYY-MM-dd")` gives **`2026-12-29`**. `YYYY` is the **week-based year** from the ISO-8601 week-numbering scheme, not the calendar year. 2025-12-29 is a Monday, and that Monday falls in ISO week 1 of 2026, so the week-based year is 2026 while the calendar year is still 2025. The bug is invisible for roughly 51 weeks a year — `YYYY` and `yyyy` agree everywhere except the handful of late-December/early-January days that straddle a week-year boundary — and then, at exactly the point in the calendar when a finance team is least equipped to absorb a surprise, it silently misfiles up to a week of `LedgerEntry` rows under next year.

### The four-way corruption

Measured in one run against `LocalDateTime.of(2026,3,15,14,30,45)`: `ofPattern("dd/MM/yyyy HH:mm")` gives the correct `15/03/2026 14:30`. `ofPattern("DD/mm/yyyy hh:MM")` gives **`74/30/2026 02:03`** — every one of the four swapped letters is wrong:

| Letter used | Meant | Actually is | Value printed |
|---|---|---|---|
| `DD` | day-of-**month** | day-of-**year** | `74` |
| `mm` | month-of-year | minute-of-**hour** | `30`, in the month slot |
| `hh` | 24-hour clock hour | clock-hour-of-**am-pm** (1–12) | `02`, with no AM/PM marker emitted, so 2 is genuinely ambiguous between 2am and 2pm |
| `MM` | minute-of-hour | **month**-of-year | `03`, in the minute slot |

### The full set to know cold

| Case-sensitive pair | Difference |
|---|---|
| `yyyy` / `YYYY` / `uuuu` | year-of-era / week-based-year / proleptic year (no era) |
| `MM` / `mm` | month-of-year / minute-of-hour |
| `dd` / `DD` | day-of-month / day-of-year |
| `HH` / `hh` / `kk` / `KK` | hour 0–23 / clock-hour-of-am-pm 1–12 / clock-hour-of-day 1–24 / hour-of-am-pm 0–11 |
| `ss` / `SS` / `S` | second-of-minute / fraction-of-second (padded) / fraction-of-second (unpadded count) |
| `EEE` / `eee` | day-of-week name (fixed order) / localized day-of-week number |
| `a` | AM/PM marker |
| `zzz` / `ZZZ` / `XXX` / `VV` | zone name / RFC-822 offset / ISO-8601 offset with colon / zone id |

**Interview:** the question is usually "what is wrong with `YYYY-MM-dd`". The strong answer names the week-based year specifically, cites a concrete date where it diverges from the calendar year (late December, ISO week 1 of the next year), and states the fix: use `uuuu` (proleptic year, no era ambiguity — see concept 3) by default, reserve `YYYY` for genuine ISO week-numbering output, and prefer a built-in `ISO_*` constant over a hand-rolled pattern wherever one fits the contract.

> `YYYY`, `DD` and `hh` are legal pattern letters that answer a different question than the one their lowercase or 24-hour siblings answer, and none of them raise a compile or runtime error when misused.

## 3. Parsing strictness (2.5.20)

The same input string and the same pattern produce **three different answers** depending on `ResolverStyle`, and the default is not the strict one. Measured parsing `"2026-02-30"` — a date that does not exist:

| `ResolverStyle` | Pattern | Result |
|---|---|---|
| `STRICT` | `yyyy-MM-dd` | `DateTimeParseException: Text '2026-02-30' could not be parsed: Unable to obtain LocalDate from TemporalAccessor: {DayOfMonth=30, MonthOfYear=2, YearOfEra=2026},ISO of type java.time.format.Parsed` |
| `SMART` (default) | `yyyy-MM-dd` | `2026-02-28` — clamped, no exception |
| `LENIENT` | `uuuu-MM-dd` | `2026-03-02` — overflowed into March |

### How the three resolve fields

`STRICT` requires every field to be independently valid and mutually consistent — day 30 is invalid for month 2 in any year, so resolution fails outright. `SMART` resolves in whatever way is "sensible", which for an out-of-range day-of-month means clamping to the month's actual length — the same clamp `02c-temporal-arithmetic-and-adjusters.md` measured for `plusMonths` (31 January + 1 month clamps to 28 February). `LENIENT` lets a field overflow its normal range and carries the excess into the next larger field, so day 30 of February becomes day 2 of March. The leaf's "why is SMART the default" is answered honestly, not charitably: SMART is the behaviour least likely to reject real-world input, which is right for a form a human typed into and wrong for a validated machine boundary. It is a compatibility and usability choice, not a correctness one.

### The `yyyy`-with-STRICT trap

Reaching for `STRICT` for safety produces a parser that rejects ordinary, valid dates if the pattern still uses `yyyy`. Measured: `LocalDate.parse("2026-03-15", ofPattern("yyyy-MM-dd").withResolverStyle(STRICT))` throws `DateTimeParseException: Text '2026-03-15' could not be parsed: Unable to obtain LocalDate from TemporalAccessor: {DayOfMonth=15, MonthOfYear=3, YearOfEra=2026},ISO of type java.time.format.Parsed`, even though 2026-03-15 is a perfectly valid date. `yyyy` is year-**of-era**, and STRICT then demands an era field to go with it, which `ISO_LOCAL_DATE`-style input never supplies. The fix is `uuuu`, the proleptic year, which needs no era at all — **this is the real reason to prefer `uuuu` over `yyyy` everywhere**, tying back to concept 2's rule.

**Pitfall:** switching to `ResolverStyle.STRICT` "to be safe" without also switching `yyyy` to `uuuu`, and shipping a parser that rejects every ordinary date it is handed.

> `ResolverStyle` governs how out-of-range or incomplete fields are resolved into a value, not whether the input text is well-formed; `SMART` is the default because it is the most forgiving of the three, not the most correct.

## 4. `DateTimeParseException` and reporting the error (2.5.21)

`DateTimeParseException` extends `DateTimeException`, which extends `RuntimeException` — parse failure is **unchecked**, and callers routinely forget to catch it at all. Beyond the message, it carries two structured fields a plain string does not: `getParsedString()` and `getErrorIndex()`.

Measured, parsing `"2026-13-01"`: `getErrorIndex()` is **`0`**, `getParsedString()` is `"2026-13-01"`, and the message is `Text '2026-13-01' could not be parsed: Invalid value for MonthOfYear (valid values 1 - 12): 13`.

The error index is **0, not 5** (where the "13" starts), because the failure happened during field *resolution*, after the entire text was already consumed lexically — there is no single offending character, only an invalid combination discovered afterward. `getErrorIndex()` points at the start of the parse for a resolution failure and at the actual offending character only for a lexical failure (an unrecognized token, a literal mismatch). A caller that renders a caret under `getErrorIndex()` on every failure will point at the wrong place for the most common class of error.

```java
public record FieldError(String field, String rejectedValue, String reason) {}

public final class OnboardingDateParser {

    private static final DateTimeFormatter DOB_FORMAT =
            DateTimeFormatter.ofPattern("uuuu-MM-dd", Locale.ROOT)
                    .withResolverStyle(ResolverStyle.STRICT);

    public LocalDate parseDateOfBirth(String field, String rawValue) {
        try {
            return LocalDate.parse(rawValue, DOB_FORMAT);
        } catch (DateTimeParseException e) {
            throw new BonusIneligibleException(
                    describe(field, rawValue, e));
        }
    }

    private FieldError describe(String field, String rawValue, DateTimeParseException e) {
        String reason = e.getMessage() != null && e.getMessage().contains(": ")
                ? e.getMessage().substring(e.getMessage().lastIndexOf(": ") + 2)
                : "value could not be parsed as a date";
        return new FieldError(field, rawValue, reason);
    }
}
```

`describe` extracts a short, client-safe reason from the exception's own message rather than forwarding `e.toString()` or a stack trace to an `ApplicationGateway` response — the raw exception can leak internal type names (`TemporalAccessor`, `Parsed`) that mean nothing to a client filling in a date-of-birth field. Cross-reference `../exceptions/02d-logging-and-api-boundaries.md` and guide 12 (API design) for the full error-contract shape this feeds into.

> `DateTimeParseException.getErrorIndex()` marks where parsing gave up, which for a resolution failure is the start of the string, not the position of the invalid field.

## 5. Legacy interop (2.5.22)

| Method | Direction | What it loses |
|---|---|---|
| `Date.toInstant()` | millis `long` → `Instant` | nothing — exact |
| `Date.from(Instant)` | `Instant` → `Date` | **lossy** — truncates below millisecond |
| `Calendar.toInstant()` | `Calendar` → `Instant` | nothing beyond what the `Calendar` already held |
| `GregorianCalendar.toZonedDateTime()` | `GregorianCalendar` → `ZonedDateTime` | nothing — the only legacy conversion that carries a zone, since a `GregorianCalendar` has one |
| `Timestamp.toInstant()` / `Timestamp.from(Instant)` | both directions | nothing — nanosecond-capable, unlike plain `Date` |

Measured truncation, §6.20: `Date.from(Instant.parse("2026-03-15T14:30:45.123456789Z")).toInstant()` returns `2026-03-15T14:30:45.123Z` — **six digits of fractional precision silently gone**, no exception, no warning.

`Timestamp` has its own oddity: after `ts.setNanos(123456789)`, `ts.getTime()` returns `1774000000123` (the inherited millis field absorbed the millisecond part) while `ts.toString()` shows `2026-03-20 15:16:40.123456789` (nine fractional digits, from `Timestamp`'s own `nanos` field) — the value genuinely lives in two places at once. The `equals` relationship is asymmetric in the same family: `d.equals(ts)` is `true` (`Date.equals` only compares `getTime()`) but `ts.equals(d)` is `false` (`Timestamp.equals` rejects anything that isn't a `Timestamp`), which breaks the symmetry clause of the `equals` contract. `03c-internals-precision-scale-and-legacy-bridging.md` owns that measurement in full.

JPA 2.2+ and Hibernate map `Instant`, `LocalDate`, `LocalDateTime` and `OffsetDateTime` directly onto the corresponding SQL types, so `@Temporal` plus a `java.util.Date` field is legacy scaffolding on any entity written against Java 21 and the first thing to remove when touching an older one. What actually bounds round-trip fidelity is the column's own declared precision: an `Instant` carrying microsecond resolution (concept 2 of `02e-clock-precision-and-storage.md`) stored into a millisecond-precision `TIMESTAMP` column comes back truncated, and an `equals`-based assertion on the round trip fails even though nothing is broken beyond the column definition. Guide 08 (Spring Data JPA) owns the mapping annotations and repository-level detail. The rule: convert at the boundary, once, in one place, and never let a `java.util.Date` past it into domain code.

**Insight:** the `Date.from` truncation here and the `Instant` round-trip loss in concept 2 of `02e-clock-precision-and-storage.md` are the same defect — a narrower time representation silently absorbing precision — on two different paths, legacy and modern.

---

## Pitfalls

### "Uppercase pattern letters are just the formal version of lowercase ones"

**Wrong**

```java
LocalDate.of(2025, 12, 29).format(DateTimeFormatter.ofPattern("YYYY-MM-dd"));
```

`2026-12-29` — the calendar year was 2025, but `YYYY` printed the ISO week-based year, which is 2026 because 2025-12-29 falls in ISO week 1 of 2026.

**Right**

```java
LocalDate.of(2025, 12, 29).format(DateTimeFormatter.ofPattern("yyyy-MM-dd"));
```

`2025-12-29` — `yyyy` is year-of-era, which for the ISO chronology matches the calendar year the reader expects.

**Why people believe it:** `YYYY` compiles, produces plausible-looking output for 51 weeks of the year, and nothing in the API name ("year" pattern, capitalized) hints that it means something structurally different from `yyyy`.

### "Switching to `ResolverStyle.STRICT` makes parsing safer"

**Wrong**

```java
LocalDate.parse("2026-03-15",
        DateTimeFormatter.ofPattern("yyyy-MM-dd").withResolverStyle(ResolverStyle.STRICT));
```

Throws `DateTimeParseException` on a perfectly valid date, because `yyyy` is year-of-era and `STRICT` then requires an era field the input never supplies.

**Right**

```java
LocalDate.parse("2026-03-15",
        DateTimeFormatter.ofPattern("uuuu-MM-dd").withResolverStyle(ResolverStyle.STRICT));
```

Returns `2026-03-15` — `uuuu` is the proleptic year and needs no era, so `STRICT` has a consistent, complete set of fields to resolve.

**Why people believe it:** `STRICT` is the intuitive name for "reject bad input", and the failure only shows up once you combine it with the also-intuitive-looking `yyyy` — a combination nothing in either name warns you about.

### "`getErrorIndex()` points at the character that was wrong"

**Wrong**

```java
try {
    LocalDate.parse("2026-13-01");
} catch (DateTimeParseException e) {
    System.out.println("^".repeat(e.getErrorIndex()) + "^");   // points at column 0
}
```

Prints a single caret at position 0 for `"2026-13-01"`, nowhere near the `13` that is actually invalid.

**Right**

```java
try {
    LocalDate.parse("2026-13-01");
} catch (DateTimeParseException e) {
    log.warn("could not parse '{}': {}", e.getParsedString(), e.getMessage());
}
```

Report the parsed string and the exception's own message, which already names the offending field (`MonthOfYear`) and value (`13`), instead of trying to derive a character position that resolution failures do not have.

**Why people believe it:** for a *lexical* failure (an unparseable token) `getErrorIndex()` really does point at the bad character, so the API's behavior on the far more common *resolution* failure (a well-formed but invalid combination of fields) looks like a bug rather than the documented, different case it is.

### "`Date.from(Instant)` round-trips an `Instant` exactly"

**Wrong**

```java
Instant original = Instant.parse("2026-03-15T14:30:45.123456789Z");
Instant roundTripped = Date.from(original).toInstant();
assert roundTripped.equals(original);   // fails
```

`roundTripped` is `2026-03-15T14:30:45.123Z` — six digits of fractional precision are gone, silently, with no exception.

**Right**

```java
Instant original = Instant.parse("2026-03-15T14:30:45.123456789Z");
Instant truncated = original.truncatedTo(ChronoUnit.MILLIS);
assert Date.from(truncated).toInstant().equals(truncated);
```

Truncate to millisecond resolution before comparing, matching the precision `java.util.Date` actually stores.

**Why people believe it:** `Date.from` is a clean-looking, single-argument static factory with no javadoc warning at the call site, and the loss is invisible until a test compares the round-tripped value against the original at full precision.

---

## Cheat sheet

| Thing | Fact (Java 21 LTS) |
|---|---|
| `DateTimeFormatter` mutability | Immutable, built once by `DateTimeFormatterBuilder`; thread-safe by construction |
| `withZone`/`withLocale`/`withResolverStyle` | Each returns a new formatter, does not mutate the receiver |
| Measured concurrency, 8×50k formats | 0 wrong results, 0 exceptions |
| `static final DateTimeFormatter` | Correct and idiomatic; share freely |
| `ISO_INSTANT` | `2026-03-15T14:30:45.123456789Z` — wire format for `Instant` |
| `ISO_LOCAL_DATE` | `2026-03-15` — wire format for `LocalDate` |
| `ISO_OFFSET_DATE_TIME` | Offset included, e.g. `+01:00` |
| `RFC_1123_DATE_TIME` | HTTP header dates only |
| `ofPattern` no-locale | Uses platform default locale — hidden host dependency |
| Machine format locale | Always `Locale.ROOT` |
| `yyyy` | Year-of-era |
| `YYYY` | Week-based year (ISO 8601 week numbering) — the New Year's Eve bug |
| `uuuu` | Proleptic year, no era — prefer by default |
| `2025-12-29` formatted `yyyy` vs `YYYY` | `2025-12-29` vs `2026-12-29` |
| `DD` | Day-of-**year** |
| `dd` | Day-of-month |
| `mm` | Minute-of-hour |
| `MM` | Month-of-year |
| `hh` | Clock-hour-of-am-pm (1–12), no AM/PM printed unless `a` added |
| `HH` | Hour-of-day (0–23) |
| `kk` / `KK` | Clock-hour-of-day (1–24) / hour-of-am-pm (0–11) |
| Four-letter swap measured | `DD/mm/yyyy hh:MM` on 2026-03-15T14:30:45 → `74/30/2026 02:03` |
| `ResolverStyle.SMART` | Default; clamps out-of-range fields (e.g. day 30 in Feb → 28) |
| `ResolverStyle.STRICT` | Rejects any inconsistent or invalid field combination |
| `ResolverStyle.LENIENT` | Overflows excess into the next larger field |
| `"2026-02-30"` under SMART/STRICT/LENIENT | `2026-02-28` / exception / `2026-03-02` |
| STRICT + `yyyy` trap | Rejects even valid dates — needs an era `yyyy` doesn't supply |
| STRICT fix | Use `uuuu`, not `yyyy` |
| `DateTimeParseException` supertype | `DateTimeException` → unchecked `RuntimeException` |
| `getErrorIndex()` on resolution failure | Points at 0, not the offending field's position |
| `getErrorIndex()` on lexical failure | Points at the actual bad character |
| `getParsedString()` | Returns the full original input text |
| `Date.toInstant()` | Exact, millis → `Instant` |
| `Date.from(Instant)` | Lossy — truncates below millisecond |
| `GregorianCalendar.toZonedDateTime()` | Only legacy conversion that carries a zone |
| `Timestamp` vs `Date` precision | `Timestamp` nanosecond-capable via its own `nanos` field |
| `d.equals(ts)` vs `ts.equals(d)` | `true` vs `false` — asymmetric, breaks `equals` contract |
| JPA 2.2+/Hibernate | Map `Instant`/`LocalDate`/`LocalDateTime`/`OffsetDateTime` directly; drop `@Temporal` + `Date` |
| Round-trip fidelity bound | The column's declared precision, not the Java type |

---

## Self-test

**Q1.** Why does `ofPattern("YYYY-MM-dd")` print the wrong year for some dates, and which dates specifically?

<details><summary>Answer</summary>

`YYYY` is the ISO-8601 week-based year, not the calendar year. It diverges from `yyyy` only for the handful of late-December or early-January dates that fall in a week belonging to the other calendar year — for example 2025-12-29, a Monday, which is in ISO week 1 of 2026, so `YYYY` prints 2026 while the calendar year is 2025. The fix is to use `yyyy` (or `uuuu`) unless you genuinely want ISO week-numbering output.

</details>

**Q2.** What exactly is wrong with the pattern `"DD/mm/yyyy hh:MM"` applied to `2026-03-15T14:30:45`, letter by letter?

<details><summary>Answer</summary>

Measured output is `74/30/2026 02:03`, all four non-`yyyy` letters wrong. `DD` is day-of-year, giving 74 instead of the day-of-month 15. `mm` is minute-of-hour, printing 30 in the slot meant for the month. `hh` is clock-hour-of-am-pm, giving 02 with no AM/PM marker, so it's ambiguous between 2am and 2pm. `MM` is month-of-year, printing 03 in the slot meant for minutes. The fix is `dd/MM/yyyy HH:mm`.

</details>

**Q3.** Why is `SMART` the default `ResolverStyle`, and what does it do with `"2026-02-30"`?

<details><summary>Answer</summary>

`SMART` clamps invalid but "close" values to something sensible — day 30 of February clamps to February's actual length, giving `2026-02-28`, with no exception. It's the default because it's the most forgiving of the three styles for real-world input, which suits a UI form. That's a usability choice, not a correctness one: `STRICT` would reject the input outright, and a validated machine boundary should generally prefer `STRICT`.

</details>

**Q4.** You switch a parser to `ResolverStyle.STRICT` for safety and it starts rejecting ordinary, correct dates. Why, and what's the fix?

<details><summary>Answer</summary>

If the pattern uses `yyyy` (year-of-era), `STRICT` demands a consistent era field alongside it, and plain ISO-style input like `"2026-03-15"` never supplies one, so resolution fails even though the date is valid. The fix is to use `uuuu`, the proleptic year, which needs no era and resolves cleanly under `STRICT`.

</details>

**Q5.** A caller catches `DateTimeParseException` and renders a caret under `getErrorIndex()` to show the user where the input went wrong. Why does that often point at the wrong place?

<details><summary>Answer</summary>

`getErrorIndex()` only points at the actual bad character for a lexical failure — unparseable text. For the more common case, a resolution failure (well-formed text but an invalid combination of fields, e.g. month 13), the whole string is consumed successfully first and the failure is discovered afterward during resolution, so the index is 0 regardless of where the bad field appeared in the string. The caller should report the field name and value from the exception's message instead of relying on the index for that case.

</details>

**Q6.** What precision does `Date.from(Instant)` preserve, and what silently happens to the rest?

<details><summary>Answer</summary>

`Date` only stores millisecond resolution internally, so `Date.from(Instant)` truncates anything finer without throwing. Measured: `Instant.parse("2026-03-15T14:30:45.123456789Z")` round-trips through `Date.from` and back to `2026-03-15T14:30:45.123Z` — six digits gone. Any code converting between `Instant` and `Date` needs to either accept millisecond precision as the ceiling or avoid the conversion entirely.

</details>

---

## Open questions

None — every claim in this file traces to brief §6.17, §6.18, §6.20, or to the constant/method names in the `java.time.format` and `java.sql` Javadoc.

---

**Leaves covered:** 2.5.18–2.5.22 (5 leaves)
**Leaves deferred:** none
**Diagrams included:** none
**Target version:** Java 21 LTS
**Lines:** 364
