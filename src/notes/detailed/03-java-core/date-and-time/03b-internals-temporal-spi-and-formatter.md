# 03 Java Core — The `Temporal` SPI, `DateTimeFormatter` internals, and value-based types — INTERNALS (§3.16, 3.16.8–3.16.10)

**Target version: Java 21 LTS.** | **Part 3 of 5** | [Index](../00-index.md)
Previous: [ZoneRules, the tzdb file, and the proleptic ISO chronology](03a-internals-zonerules-and-tzdb.md) · Next: [Instant precision, conversion overflow and legacy bridging](03c-internals-precision-scale-and-legacy-bridging.md)

This file owns the extension mechanism underneath every `java.time` type —
the six SPI interfaces that make `plus`, `with` and `format` work the same way
across twenty unrelated classes — plus the proof that `DateTimeFormatter` is
safe to share across threads, and the `@ValueBased` contract that makes `==`
on any of these types a defect waiting to happen. `03-internals-java-time.md`
owns the field-by-field memory layout that this file's identity-cache
evidence depends on; `03a-internals-zonerules-and-tzdb.md` owns the tzdb file
format and the proleptic ISO chronology. Neither of those pictures is
repeated here: this file carries no diagram of its own — see
`03-internals-java-time.md` (D-127) and `03a-internals-zonerules-and-tzdb.md`
(D-128) for the ones that cover this row.

Measurement environment: Oracle JDK 21.0.7 (build 21.0.7+8-LTS-245), macOS
aarch64, tzdb 2025a. Figures below are cited from that run; anything not
measured is named against the Javadoc or JLS directly.

---

## 1. The `Temporal` SPI, and how `plus(1, ChronoUnit.DAYS)` resolves (3.16.8)

Twenty types — `Instant`, `LocalDate`, `LocalTime`, `LocalDateTime`,
`ZonedDateTime`, `OffsetDateTime`, `YearMonth`, `Year`, and more — look like a
bag of unrelated classes until you stop reading them as dates and start
reading them as thin shells over six interfaces. The arithmetic does not live
in the date types at all. It lives in the *units and fields* that get handed
to them. That inversion — ask the unit how to add itself, not ask the date how
to add a unit — is the design the rest of the package is built on.

### Why it exists

Before this SPI, "add a day" meant a method per type per unit:
`Calendar.add(Calendar.DAY_OF_MONTH, 1)` with an `int` constant and no
type safety, or a hand-rolled `addDays` on every custom date class a codebase
accumulated. Neither approach let a caller write generic code over "some
temporal, some unit" — `Calendar.add` takes an untyped field constant, and a
bespoke `addDays` only exists on the one type its author wrote it for. The SPI
makes the unit and the field first-class values so the same call shape works
for every type that supports that unit, and new units and adjusters can be
added by third-party code without ever touching `java.time` itself.

### How it works

The six interfaces, what each is, and one real implementation:

| Interface | What it is | Implementation |
|---|---|---|
| `TemporalAccessor` | Read-only: "I can be asked for a field" | `LocalDate`, `Instant`, and `java.time.format.Parsed` all implement it |
| `Temporal` | Extends `TemporalAccessor`, adds `plus`/`minus`/`with`: "I can produce a modified copy" | `LocalDate`, `Instant`, `ZonedDateTime` |
| `TemporalField` | A readable/settable field | `ChronoField` is the standard enum (`DAY_OF_MONTH`, `MONTH_OF_YEAR`, …) |
| `TemporalUnit` | A unit of measure | `ChronoUnit` is the standard enum (`DAYS`, `HOURS`, `MONTHS`, …) |
| `TemporalAdjuster` | A `Temporal -> Temporal` function | `TemporalAdjusters` holds the standard ones (`lastDayOfMonth()`, `next(DayOfWeek)`) |
| `TemporalAmount` | An amount expressible as a set of unit-quantity pairs | `Duration` and `Period` both implement it |

`TemporalAccessor` matters because `DateTimeFormatter.parse` cannot know in
advance which concrete type the caller wants — it hands back a
`java.time.format.Parsed`, itself a `TemporalAccessor`, and the caller queries
fields off it or converts with `LocalDate.from(parsed)`. `TemporalAmount`
matters because it is why `plus(TemporalAmount)` accepts either a `Duration`
or a `Period` with no overload resolution trickery: both simply implement the
one interface.

Now the mechanism the leaf names. `temporal.plus(1, ChronoUnit.DAYS)` contains
**no switch over unit types anywhere**. `Temporal.plus(long, TemporalUnit)` is
specified to delegate to the unit itself: the concrete type's implementation
calls back `unit.addTo(this, amount)`, and `ChronoUnit.DAYS.addTo` in turn
calls into the temporal's own type-specific arithmetic (for a
`LocalDate`-shaped temporal, its `plusDays`; for an `Instant`-shaped one, its
own second/nanosecond arithmetic). That is double dispatch: the unit decides
how to interpret itself against a temporal, and the temporal decides how to
apply that interpretation to its own fields, and neither one contains a type
test on the other. It is why the identical call — same method name, same
argument shape — means **exactly 86,400 seconds** when the receiver is an
`Instant`, and **one calendar day, DST included, wall-clock preserved** when
the receiver is a `LocalDate` or a `ZonedDateTime`. This is the field-level
restatement of the `Duration`-versus-`Period` divergence
`02b-amounts-dst-and-tzdb.md` measured across the `Europe/London`
spring-forward: the two types never talk to each other, they each just answer
`addTo` differently.

The guard that keeps this safe is `isSupported(TemporalUnit)`, checked before
the delegation runs. An unsupported unit throws
`UnsupportedTemporalTypeException` rather than silently doing something
wrong. Measured behaviour worth stating precisely: `Instant` does not support
`ChronoUnit.MONTHS` (a month has no fixed length in seconds, so there is no
way to answer "add one month" as a fixed offset), and `LocalDate` does not
support `ChronoUnit.HOURS` (a `LocalDate` has no time-of-day component to
advance).

`ChronoField` carries the same double-dispatch shape on the read side, and it
explains an error message the reader has already met. Every `ChronoField` has
a `range()` — the valid `ValueRange` for that field — and `range()` is what
produces `Invalid value for MonthOfYear (valid values 1 - 12): 13`, measured
in `02d-formatting-and-parsing.md`'s parse failure on `2026-13-01`. The
message names the field (`MonthOfYear`), the field's own declared range
(`1 - 12`), and the offending value (`13`) — all three come out of
`ChronoField.MONTH_OF_YEAR.range()` and the field's own validation, not out of
`LocalDate`.

`TemporalQuery` is the read-only mirror of `TemporalAdjuster`: a
`TemporalAccessor -> R` function used with `temporal.query(TemporalQuery)`,
with the standard ones (`localDate()`, `zoneId()`, `precision()`) living in
`TemporalQueries`.

### A concrete example

QuizStakes settles the banking partner's payout file in **4 windows per
day** (§6, "Numbers you may quote"). A custom `TemporalUnit` for "payout
windows" is the right vehicle when the unit needs to compose with `plus`,
`minus` and `between` rather than live as a static helper method — implementing
`TemporalUnit` gets it `Temporal.plus(long, TemporalUnit)` for free on every
temporal that declares support for it, which a helper method never would.

```java
enum PayoutWindowUnit implements TemporalUnit {
    PAYOUT_WINDOWS;

    private static final Duration WINDOW_LENGTH = Duration.ofHours(6);

    @Override
    public Duration getDuration() {
        return WINDOW_LENGTH;
    }

    @Override
    public boolean isDurationEstimated() {
        return false;
    }

    @Override
    public boolean isDateBased() {
        return false;
    }

    @Override
    public boolean isTimeBased() {
        return true;
    }

    @Override
    public boolean isSupportedBy(Temporal temporal) {
        return temporal.isSupported(ChronoUnit.SECONDS);
    }

    @Override
    @SuppressWarnings("unchecked")
    public <R extends Temporal> R addTo(R temporal, long amount) {
        return (R) temporal.plus(amount * WINDOW_LENGTH.toSeconds(), ChronoUnit.SECONDS);
    }

    @Override
    public long between(Temporal start, Temporal end) {
        long startSeconds = ChronoUnit.SECONDS.between(start, end.query(t -> start));
        return ChronoUnit.SECONDS.between(start, end) / WINDOW_LENGTH.toSeconds();
    }
}
```

`getDuration()` reports the fixed length (6 hours, so 4 windows tile exactly
into a day), `isDurationEstimated()` is `false` because unlike `MONTHS` this
unit has no calendar-dependent length, `isSupportedBy` delegates to
`ChronoUnit.SECONDS` support (so it works on any `Instant`- or
`LocalDateTime`-shaped temporal), and `addTo`/`between` both reduce to
`ChronoUnit.SECONDS` arithmetic — the same delegation pattern the built-in
`ChronoUnit` constants use. With this in place,
`instant.plus(1, PayoutWindowUnit.PAYOUT_WINDOWS)` composes exactly like
`instant.plus(1, ChronoUnit.DAYS)`, because both go through the identical
`Temporal.plus(long, TemporalUnit)` dispatch. `02c-temporal-arithmetic-and-adjusters.md`
covers the application-level use of `TemporalAdjuster` and `ChronoUnit`; this
is the SPI those calls are built from.

**Gotcha:** no version trap applies to the SPI shape itself — it has been
stable since Java 8. The trap is entirely in `isSupported` being skipped:
code that assumes every `Temporal` supports every `ChronoUnit` will compile
and then throw `UnsupportedTemporalTypeException` in production on the first
`Instant.plus(1, ChronoUnit.MONTHS)` call.

**Insight:** `plus(1, ChronoUnit.DAYS)` on an `Instant` and on a `LocalDate`
run through the identical `Temporal.plus(long, TemporalUnit)` dispatch and
never share a code path once the unit's own `addTo` takes over — which is why
the two calls can legitimately mean different things without either class
containing a type check on the other.

**Interview:** "How does `LocalDate.plus(1, ChronoUnit.DAYS)` know what a day
means?" — it doesn't; `ChronoUnit.DAYS.addTo(localDate, 1)` does, and it calls
back into `LocalDate`'s own day arithmetic. The date type only knows how to
apply an amount in its own units; the unit type knows how to translate itself
into a call the date type understands.

> A `Temporal` never contains its own arithmetic for a given unit — it
> delegates to the `TemporalUnit`, which calls back into the temporal's
> native operation, and that double dispatch is what lets one `plus` method
> mean 86,400 seconds on an `Instant` and one calendar day on a `LocalDate`.

---

## 2. `DateTimeFormatter` immutability, proved (3.16.9)

A `DateTimeFormatter` obtained from `ofPattern` looks, from the call site,
like it might be doing what `SimpleDateFormat` does — walking a pattern
string and building output field by field on every call. It is not. By the
time `format` or `parse` is ever invoked, the pattern has already been turned
into a fixed tree of objects, and that tree is never touched again.

### Why it exists

`SimpleDateFormat` is not thread-unsafe by accident of implementation
detail — it is unsafe because its design puts a mutable `Calendar` inside
every formatter instance and mutates it on every `format` call
(`02-date-and-time.md` and D-080 own that measurement in full). `DateTimeFormatter`
had to not repeat that, because "build once, reuse everywhere" — as a
`static final` field — is exactly the usage pattern applications want, and
that pattern is only safe if the object holds nothing that a call mutates.

### How it works

`DateTimeFormatterBuilder` accumulates a list of printer/parser components as
`appendValue`, `appendLiteral`, `appendPattern` and friends are called, and
`toFormatter()` freezes that list into a `CompositePrinterParser` tree. The
resulting `DateTimeFormatter` holds that tree plus a `Locale`, a
`DecimalStyle`, a `ResolverStyle`, a resolver-field set, a `Chronology` and a
`ZoneId` — **all final, none mutated by `format` or `parse`**. Every
`withLocale`, `withZone`, `withResolverStyle` and `withChronology` call
returns a **new** `DateTimeFormatter` sharing the same printer/parser tree,
which is what keeps making a zone- or locale-adjusted copy cheap: the
expensive part (the tree) is shared, only the small final fields differ.

`[PROVE]` needs both the structural argument and the empirical confirmation,
and they are not the same thing.

The structural half: there is no per-call mutable state on the formatter
itself, so two threads formatting concurrently touch nothing in common that
either one writes. Contrast `SimpleDateFormat`'s inherited
`protected Calendar calendar` — exactly one shared mutable field, and that
field is the entire bug.

The empirical half, measured (§6.18): 8 threads, 50,000 formats each, 400,000
total, each thread formatting **its own distinct** `Instant`, using
`DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm:ss.SSS").withZone(ZoneId.of("Europe/London"))`:

```
distinct wrong results : 0
exceptions             : 0
```

Say plainly what that number can and cannot establish. It is **consistent
with** thread safety, and it is **not a proof** of it — no finite run proves
the absence of a race, because the race that did not fire in 400,000 calls
could still exist and simply not have been scheduled into visibility this
time. The structural argument — no shared mutable state — is the actual
proof. The measured run is the confirmation that the structural argument
matches observed behaviour, and it is worth having anyway because the same
harness, run against `SimpleDateFormat` under identical load, produced 504
distinct wrong outputs and 0 exceptions (`02-date-and-time.md`, D-080) — so
the harness is demonstrably capable of finding a race when one is actually
there, which makes its silence on `DateTimeFormatter` mean something.

The practical consequence follows directly: a `static final DateTimeFormatter`
is correct and idiomatic, and building one is not free — the builder walks
the pattern string and constructs the printer/parser tree — so hoisting
construction to a constant is a genuine, safe optimisation. This is the exact
opposite of hoisting a `SimpleDateFormat` to a `static final` field, which is
a genuine and catastrophic mistake for the reason above. One caveat: parsing
still allocates a mutable `java.time.format.Parsed` per call to hold the
in-progress field values, and that is fine because it is per-call, stack-local
in effect, and never shared across threads.

```java
public final class SettlementFormats {

    public static final DateTimeFormatter LEDGER_TIMESTAMP =
            DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm:ss.SSS")
                    .withZone(ZoneId.of("Europe/London"));

    private SettlementFormats() {
    }
}
```

Every `Movement` in `FundsLedger` can format its `postedAt` `Instant` through
this one shared constant, from any settlement worker thread, with no lock and
no per-call allocation of the formatter itself.

**Pitfall:** treating `DateTimeFormatter` as needing the same
one-per-thread discipline as `SimpleDateFormat`. It does not — a shared
`static final` instance is the idiomatic and correct usage, and wrapping it
in a `ThreadLocal` only adds cost for no safety benefit.

**Insight:** immutability is not a property you test for — it is a property
you read off the field declarations. `03-internals-java-time.md`'s field walk
across `Instant`, `LocalDate`, `LocalTime` and `ZonedDateTime` is the same
kind of reading applied to the value types; this section applies it to the
formatter.

**Interview:** "Is `DateTimeFormatter` thread-safe, and why?" — yes, because
the printer/parser tree is built once by `DateTimeFormatterBuilder` and
frozen; `format` and `parse` only read it. Contrast `SimpleDateFormat`, which
mutates a shared `Calendar` field on every call.

> `DateTimeFormatter` is thread-safe because its printer/parser tree is built
> once and never mutated after `toFormatter()` — safety by construction, not
> by locking.

---

## 3. `@ValueBased`, and why `==` is never correct (3.16.10)

Every `java.time` type is annotated `jdk.internal.ValueBased`. It is not a
language feature and it changes no compiler behaviour — it is a documented
contract to the reader (and, eventually, to the JVM) that instances of the
type are freely substitutable, have no meaningful identity, and are
candidates for the value-class treatment Project Valhalla is building toward.
Three obligations follow from that contract, and application code can violate
all three today without the compiler saying a word.

### How it works

**Do not rely on identity.** The measurements in §6.13 are worse than a flat
"`==` is always false", which would at least be a safe rule to internalise by
accident:

```
LocalTime.of(14, 0)  == LocalTime.of(14, 0)   -> true    (both are the cached HOURS[14])
LocalTime.of(14, 30) == LocalTime.of(14, 30)  -> false
LocalTime.NOON       == LocalTime.of(12, 0)   -> true
Instant.ofEpochSecond(0) == Instant.EPOCH     -> true
```

`LocalTime` keeps a `private static final LocalTime[] HOURS = new LocalTime[24]`
(§6.13) and `LocalTime.of` returns the cached array element whenever the
minute, second and nanosecond are all zero. So `==` on a whole-hour time is
`true` by accident of caching, and the identical-looking call on a half-hour
time is `false`. That means `==` works for some values and fails for others,
which is the most dangerous shape a wrong tool can take: a test written
against `LocalTime.of(14, 0)` passes, and the identical assertion shape
against `LocalTime.of(14, 30)` — a stake placed at half past — fails, with
nothing in the code to suggest why.

**Pitfall:** comparing `java.time` values with `==` because a quick manual
check on a whole-hour or whole-second value happened to return `true`. The
fix is `equals`, `compareTo`, or `isBefore`/`isAfter`, unconditionally, with
no carve-out for values that "look safe". This is the same shape of bug as
`Integer`'s −128..127 autoboxing cache (`../wrappers-and-boxing/01-basics.md`)
and `BigInteger.valueOf`'s −16..16 cache (§6.10,
`../numbers-and-money/03b-internals-biginteger-and-long-cents.md`) — three
unrelated caches in three unrelated types, and the identical lesson each
time: a cache makes `==` intermittently pass, and intermittent is worse than
always-false.

**Do not synchronise on them.** This is a real correctness bug, not a style
preference. A `synchronized` block on a value-based instance may lock on a
shared cached instance — `LocalTime.NOON`, say — so two entirely unrelated
pieces of code contend on the same monitor without either one knowing the
other exists; or it may lock on a freshly allocated instance every time,
`synchronized (LocalTime.of(14, 30))`, in which case the lock protects
nothing at all because no other thread can ever be holding the same monitor.
`javac` warns on `synchronized` over a value-based type, and a future
value-class implementation could turn that into a hard error, since a true
value class has no monitor to acquire — so this is not merely stylistically
wrong today, it is standing on a deprecation path. Guide 05 (concurrency)
owns the memory-model half of why locking matters at all.

**Do not depend on `hashCode` stability across JVMs, or on
`System.identityHashCode`.** `equals` and `hashCode` on every `java.time`
type are pure functions of the declared fields (`03-internals-java-time.md`'s
field walk), so they are stable across runs and across JVMs for the same
logical value — which is the actual property callers want from a value type,
and the one `==` cannot give at all, cache or no cache.

### When to reach for it, and when not

Project Valhalla's value classes are the destination this annotation is
pointing at, and `@ValueBased` marks exactly the types intended to migrate —
but no part of that has shipped in Java 21, and it would be dishonest to
imply a timeline here. The one rule that survives regardless of when Valhalla
lands: use `equals`, `compareTo`, `isBefore` and `isAfter`; never `==`; never
`synchronized` on a temporal.

**Insight:** the annotation is descriptive, not enforced. Nothing in the
compiler stops `synchronized (localDate)` or `a == b` from compiling — the
protection here is entirely in the reader knowing the contract, which is
exactly why it is worth stating explicitly rather than assuming it is
"obviously" understood.

**Interview:** "Why is `==` never correct on a `LocalDate`?" — because
`@ValueBased` types make no identity guarantee at all: some values happen to
come from an internal cache and compare `==` true, most do not, and neither
outcome is part of the contract. Use `equals`.

> `@ValueBased` types promise substitutability and disclaim identity; caching
> makes `==` pass by accident on some values and fail on others, so the only
> safe comparison is `equals`, `compareTo`, or a named directional check.

---
## Pitfalls

### "`==` on a `LocalTime` is always false, so it's safe to rely on when it happens to be true"

**Wrong**

```java
LocalTime settlementCutoff = LocalTime.of(14, 0);
LocalTime candidate = LocalTime.of(14, 0);
if (candidate == settlementCutoff) {
    // route to same-day settlement
}
```

Passes every time this test is run, because both calls return the cached
`HOURS[14]` instance (§6.13). Change the cutoff to `LocalTime.of(14, 30)` and
the identical `==` check silently starts returning `false` for equal values.

**Right**

```java
LocalTime settlementCutoff = LocalTime.of(14, 0);
LocalTime candidate = LocalTime.of(14, 0);
if (candidate.equals(settlementCutoff)) {
    // route to same-day settlement
}
```

`equals` compares the `hour`, `minute`, `second` and `nano` fields directly
(`03-internals-java-time.md`), so it gives the same answer for every equal
value regardless of whether that value happens to be cached.

**Why people believe it:** a developer manually tests `LocalTime.of(14, 0) ==
LocalTime.of(14, 0)` in a REPL or a quick unit test, sees `true`, and
generalises to "temporal `==` works for whole values" without knowing the
`HOURS` cache is the only reason it worked at all.

### "A `Temporal.plus(n, unit)` call works for any unit any temporal supports, so no guard is needed"

**Wrong**

```java
Instant settlementDeadline = Instant.now();
Instant nextReviewCycle = settlementDeadline.plus(1, ChronoUnit.MONTHS);
```

Throws `UnsupportedTemporalTypeException: Unsupported unit: Months` at
runtime — `Instant` never supports `ChronoUnit.MONTHS` because a month has no
fixed length in seconds, and nothing at compile time flags the mismatch.

**Right**

```java
Instant settlementDeadline = Instant.now();
ChronoUnit unit = ChronoUnit.MONTHS;
if (settlementDeadline.isSupported(unit)) {
    settlementDeadline.plus(1, unit);
} else {
    ZonedDateTime.ofInstant(settlementDeadline, ZoneId.of("Europe/London"))
            .plus(1, unit)
            .toInstant();
}
```

Checking `isSupported` first, or moving to a calendar-aware type
(`ZonedDateTime`) before applying a calendar-based unit, avoids the exception
entirely — the guard is part of the SPI precisely because not every
`Temporal`/`TemporalUnit` pairing is meaningful.

**Why people believe it:** the method signature `plus(long, TemporalUnit)` is
identical across every `Temporal` implementation, so it looks polymorphic in
the sense that any unit should work anywhere — the SPI's uniform surface
hides that support is still per-type.

### "`DateTimeFormatter` needs one instance per thread, like `SimpleDateFormat`"

**Wrong**

```java
private static final ThreadLocal<DateTimeFormatter> LEDGER_FORMAT =
        ThreadLocal.withInitial(() -> DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm:ss.SSS"));
```

Compiles and runs correctly, but pays the cost of one
`DateTimeFormatterBuilder` walk and one `CompositePrinterParser` tree per
thread for no safety gain — the formatter was already safe to share.

**Right**

```java
private static final DateTimeFormatter LEDGER_FORMAT =
        DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm:ss.SSS");
```

Measured (§6.18): 8 threads x 50,000 formats each against one shared
instance, 0 distinct wrong results, 0 exceptions — a single `static final`
field is both correct and cheaper.

**Why people believe it:** `SimpleDateFormat`'s well-earned reputation for
needing per-thread instances (or a lock) gets over-applied to every formatter
type in the JDK, without checking whether the new type shares the same
mutable-state design that made the old one unsafe.

---

## Cheat sheet

| Thing | Fact (Java 21 LTS) |
|---|---|
| `TemporalAccessor` | Read-only field access; `LocalDate`, `Instant`, `Parsed` all implement it |
| `Temporal` | Extends `TemporalAccessor`; adds `plus`/`minus`/`with` |
| `TemporalField` | Standard impl: `ChronoField` (`DAY_OF_MONTH`, `MONTH_OF_YEAR`, `YEAR`) |
| `TemporalUnit` | Standard impl: `ChronoUnit` (`DAYS`, `HOURS`, `MONTHS`) |
| `TemporalAdjuster` | `Temporal -> Temporal`; standard ones in `TemporalAdjusters` |
| `TemporalAmount` | `Duration` and `Period` both implement it |
| `TemporalQuery` | `TemporalAccessor -> R`; standard ones in `TemporalQueries` |
| `plus(n, unit)` resolution | `Temporal.plus` delegates to `unit.addTo(this, n)`, which calls back into the temporal's own arithmetic |
| Guard before delegation | `isSupported(TemporalUnit)`; unsupported throws `UnsupportedTemporalTypeException` |
| `Instant` + `ChronoUnit.MONTHS` | Unsupported: no fixed seconds length for a month |
| `LocalDate` + `ChronoUnit.HOURS` | Unsupported: no time-of-day component |
| `ChronoField.range()` | Source of `Invalid value for MonthOfYear (valid values 1 - 12): 13` |
| `DateTimeFormatterBuilder.toFormatter()` | Freezes accumulated components into a `CompositePrinterParser` tree |
| `DateTimeFormatter` fields | Tree, `Locale`, `DecimalStyle`, `ResolverStyle`, resolver fields, `Chronology`, `ZoneId` — all final |
| `withLocale`/`withZone`/etc. | Return a new `DateTimeFormatter` sharing the same tree |
| `DateTimeFormatter` thread-safety proof | Structural: no shared mutable state, ever mutated by `format`/`parse` |
| `DateTimeFormatter` thread-safety confirmation | Measured: 8 x 50,000 formats, own `Instant` each, 0 wrong, 0 exceptions (§6.18) |
| Same harness vs `SimpleDateFormat` | 504 distinct wrong outputs, 0 exceptions (§6.18, D-080) |
| What the measured run proves | Consistent with thread safety; not a proof — the structural argument is the proof |
| `static final DateTimeFormatter` | Idiomatic and correct; building one is not free, so hoisting it is a real optimisation |
| Parsing per call | Allocates a mutable `Parsed`; fine because it is per-call, never shared |
| `@ValueBased` | Marker on `java.time` types, wrappers, `Optional`; documents substitutability, no identity guarantee |
| `LocalTime.of(14,0) == LocalTime.of(14,0)` | `true` — both are cached `HOURS[14]` |
| `LocalTime.of(14,30) == LocalTime.of(14,30)` | `false` — not cached |
| `LocalTime.NOON == LocalTime.of(12,0)` | `true` |
| `Instant.ofEpochSecond(0) == Instant.EPOCH` | `true` |
| Same-shape caches elsewhere | `Integer` −128..127; `BigInteger.valueOf` −16..16 (§6.10) |
| Synchronising on a value-based type | May lock a shared cached instance or a fresh one every time; `javac` warns |
| `hashCode`/`equals` on `java.time` types | Pure functions of fields; stable across runs and JVMs |
| Correct comparisons | `equals`, `compareTo`, `isBefore`, `isAfter` — never `==` |
| Project Valhalla status in Java 21 | Not shipped; `@ValueBased` marks intended future value classes only |

---

## Self-test

**Q1.** Why does `LocalDate.plus(1, ChronoUnit.DAYS)` and `Instant.plus(1, ChronoUnit.DAYS)` produce different results without either class knowing about the other?

<details><summary>Answer</summary>

`Temporal.plus(long, TemporalUnit)` delegates to the unit: it calls
`unit.addTo(this, amount)`, and `ChronoUnit.DAYS.addTo` calls back into the
receiving temporal's own type-specific arithmetic. `LocalDate`'s arithmetic
interprets a day as one calendar day (with month/year rollover); `Instant`'s
interprets it as exactly 86,400 seconds. Neither class contains a switch or a
type check on the other — the divergence lives entirely in what each type's
own arithmetic method does once the unit calls back into it.

</details>

**Q2.** What throws when you call `Instant.now().plus(1, ChronoUnit.MONTHS)`, and why?

<details><summary>Answer</summary>

`UnsupportedTemporalTypeException`. `Temporal.plus` checks
`isSupported(TemporalUnit)` before delegating, and `Instant` does not support
`ChronoUnit.MONTHS` because a month has no fixed length in seconds — `Instant`
only supports units with a fixed duration (`NANOS`, `MICROS`, `MILLIS`,
`SECONDS`, `MINUTES`, `HOURS`, `HALF_DAYS`, `DAYS`), not calendar-based ones.

</details>

**Q3.** Is `DateTimeFormatter` thread-safe, and what is the actual proof — not just the measured run?

<details><summary>Answer</summary>

Yes. The proof is structural: `DateTimeFormatterBuilder.toFormatter()` freezes
an accumulated printer/parser tree into a `CompositePrinterParser`, and the
resulting `DateTimeFormatter` holds that tree plus a handful of final fields
(`Locale`, `DecimalStyle`, `ResolverStyle`, `Chronology`, `ZoneId`) that
`format` and `parse` only ever read. With no field mutated by either call,
there is nothing for two threads to race on. The measured run — 8 threads x
50,000 formats each, 0 wrong results — is confirmation that this holds in
practice, not the proof itself; no finite run can prove the absence of a
race.

</details>

**Q4.** Why is `LocalTime.of(14, 0) == LocalTime.of(14, 0)` `true` while `LocalTime.of(14, 30) == LocalTime.of(14, 30)` is `false`?

<details><summary>Answer</summary>

`LocalTime` keeps a `private static final LocalTime[] HOURS = new LocalTime[24]`
cache, and `LocalTime.of` returns the shared cached instance whenever minute,
second and nanosecond are all zero. `14:00` hits that cache, so both calls
return the identical object and `==` is `true`. `14:30` is not a whole hour,
so `of` allocates a fresh instance each call, and `==` is `false`. Neither
outcome is part of any documented contract — it is purely an artifact of the
cache, which is exactly why `==` must never be used on these types.

</details>

**Q5.** Why is it a genuine bug, not just a style issue, to `synchronized` on a `LocalDate` or an `Instant`?

<details><summary>Answer</summary>

Because a value-based type gives no identity guarantee, the object you lock
on might be a shared cached instance — meaning two unrelated pieces of code
end up contending on the same monitor without either one intending to — or it
might be a freshly allocated instance every single call, meaning the lock
protects nothing because no other thread can ever hold the same monitor.
Either way the lock does not do what the code author assumed. `javac` warns
on this, and a future Valhalla value-class implementation could make it a
hard error since true value classes have no monitor at all.

</details>

**Q6.** What does the JDK 21 `Instant.MAX.toEpochMilli()` throw, and what does that tell you about how `toEpochMilli` is implemented? (Cross-check against 3.16.12 in the next file.)

<details><summary>Answer</summary>

It throws `ArithmeticException: long overflow`. That tells you the
implementation uses checked arithmetic (multiplication that detects overflow)
rather than plain `long` multiplication that would silently wrap — the JDK
chose to fail loudly on an out-of-range conversion rather than return a
plausible-looking wrong number. The full derivation of why the range does not
fit is in `03c-internals-precision-scale-and-legacy-bridging.md`, §2.

</details>

---

## Open questions

None. Every claim above is sourced from §6.13, §6.16, §6.17, §6.18 of the
measured brief, or from the `Temporal`/`TemporalUnit`/`DateTimeFormatterBuilder`
Javadoc contracts named inline.

---

**Leaves covered:** 3.16.8–3.16.10 (3 leaves)
**Leaves deferred:** none
**Diagrams included:** none
**Target version:** Java 21 LTS
**Lines:** 642
