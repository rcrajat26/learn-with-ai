# 03 Java Core — Instant precision, conversion overflow, the Java time-scale and legacy bridging — INTERNALS (§3.16, 3.16.11–3.16.14)

**Target version: Java 21 LTS.** | **Part 3 of 5** | [Index](../00-index.md)
Previous: [The Temporal SPI, DateTimeFormatter internals, and value-based types](03b-internals-temporal-spi-and-formatter.md) · Next: [Serialization](../serialization/02-serialization.md)

This file closes the row: where `Instant`'s claimed nanosecond field actually
gets its resolution from, why converting an extreme `Instant` to epoch millis
can overflow a `long` and how the JDK responds, what "the Java time-scale"
means as a definition rather than a vibe, and the field-level mechanics of
`java.util.Date`/`java.sql.Timestamp` that make their `equals` contract
asymmetric. `02e-clock-precision-and-storage.md` owns the version-trap framing
and the `Clock` injection story at the application level — this file does not
repeat either, only the mechanism underneath them. No diagram accompanies
this file — see `03-internals-java-time.md` (D-127) and
`03a-internals-zonerules-and-tzdb.md` (D-128) for this row's pictures.

Measurement environment: Oracle JDK 21.0.7 (build 21.0.7+8-LTS-245), macOS
aarch64, tzdb 2025a. Figures below are cited from that run; anything not
measured is named against the Javadoc directly.

---

## 1. Instant precision at the field level (3.16.11)

`Instant` declares `private final int nanos` (§6.13), which can hold a value
from 0 to 999,999,999 — nanosecond resolution, by field capacity. Whether any
given `Instant` actually *carries* nanosecond information is a separate
question entirely, and it is answered by the clock, not by the field.

### Why it exists

An `int nanos` field costs nothing extra to declare at full nanosecond width
even if most clocks cannot fill it meaningfully — the field capacity is a
one-time design decision, made once, that then has to serve every future
clock source without another field-layout change. Binding the type's
precision to whatever the *current* system clock happens to deliver would
have made every future improvement in OS clock resolution a breaking change
to the type's declared contract.

### How it works

`Clock.systemUTC()` obtains the current instant from `VM.getNanoTimeAdjustment`
against the platform's own OS clock call, not from a dedicated nanosecond
timer — so the field's declared capacity (nanoseconds) and the value's actual
resolution (whatever the OS clock delivers) are two different limits, and the
second one is the one that binds in practice. This is genuinely
platform-dependent: the `Instant.now()` Javadoc promises only "the best,
most precise available system clock", not any specific unit, so portable code
must not assume either microsecond or nanosecond resolution.

Measured on this build: `Instant.now()` returned
`2026-08-29T09:57:50.444951Z`, with `getNano()` reporting `444951000`. The
trailing three zeros are the tell — six significant fractional digits, then
zero-padding to fill the `int` field's nine-digit width. That is microsecond
resolution on macOS aarch64, not nanosecond, despite the field being wide
enough for either.

The round-trip failure the leaf names follows directly, and it is worth
reading precisely rather than as "truncation loses precision", because the
interesting part is *why* it fails as an equality check specifically:

```
now                                             = 2026-08-29T09:57:50.444951Z
now.truncatedTo(ChronoUnit.MILLIS)              = 2026-08-29T09:57:50.444Z
now.equals(now.truncatedTo(ChronoUnit.MILLIS))  -> false
```

`Instant.equals` compares `seconds` and `nanos` exactly — there is no
tolerance anywhere in the type, by field or by method. `now`'s `nanos` field
holds `444951000`; the truncated copy's `nanos` field holds `444000000`. Those
are two different `int` values, so the two objects are unequal by the plain
field comparison `equals` performs, full stop. No amount of "the difference is
only microseconds" enters into it, because `Instant` was never designed to
compare "close enough" — that is a decision for the caller to make explicitly,
with an explicit tolerance or an explicit truncation, never implicitly by
`equals`.

**[X-REF 16]** An assertion on an `Instant` that made a database round trip
must handle this at the boundary in one of three ways: truncate both sides to
the column's actual precision deliberately before comparing, compare with
`isEqual` or `compareTo` after an explicit `truncatedTo` call on both values,
or use an assertion library's temporal tolerance (AssertJ's `isCloseTo` with a
`TemporalUnitOffset`). Of the three, deliberate truncation at the boundary is
the one that also fixes the underlying production behaviour rather than only
making the test pass — a system that stores millisecond-precision timestamps
and then compares against a microsecond-precision in-memory value has the
same bug in production code paths that never run under a test at all. Guide
16 (Testing) covers the assertion-library mechanics in full.

The production-side equivalent of deliberate truncation is `Clock.tickMillis`,
measured to return `2026-08-29T09:57:50.445Z` where the untruncated system
clock at the same moment gave `2026-08-29T09:57:50.444986Z` — `tickMillis`
rounds to the millisecond at the source, rather than leaving callers to
truncate after the fact.

**Pitfall:** asserting `instant.equals(instantFromDatabase)` after a round
trip through a column with coarser precision than the in-memory clock.
`Instant.equals` compares `seconds` and `nanos` exactly with zero tolerance,
so a value with real microsecond content will never equal its
millisecond-truncated database copy — truncate both sides to the same
precision before comparing, or compare with an explicit tolerance.

**Insight:** the field is nanosecond-wide by design margin, not by guaranteed
content — treat `getNano()`'s trailing zeros as a live signal of the actual
clock resolution on the platform you are running on, not as evidence that
`Instant` itself only supports coarser precision.

**Interview:** "Why did a millisecond round-trip `equals` check that passed
on Java 8 start failing on Java 17?" — `Clock.systemUTC()` moved from
millisecond resolution on Java 8 to microsecond (or better) resolution on
Java 9+, so a database column that only stores millisecond precision now
silently drops information the JVM's own clock actually populated, and
`equals`'s exact field comparison has no tolerance to absorb the gap.

> `Instant`'s `nanos` field can hold nanosecond resolution, but the actual
> precision of any given value is whatever the underlying `Clock` delivered —
> a platform-dependent fact, not a type guarantee — and `equals` compares
> `seconds` and `nanos` exactly, with no tolerance for the difference.

---

## 2. Conversion overflow — `toEpochMilli`, `Instant.MIN`/`MAX` (3.16.12)

`Instant`'s declared range is enormous — a billion proleptic years either
side of the epoch — and a `long` of milliseconds simply cannot address all of
it. That mismatch is not a bug; it is the reason `toEpochMilli` is allowed to
throw at all.

The range: `Instant.MIN` = `-1000000000-01-01T00:00:00Z`, `Instant.MAX` =
`+1000000000-12-31T23:59:59.999999999Z`.

Derive why `toEpochMilli` cannot cover that span. `Long.MAX_VALUE` is
`9,223,372,036,854,775,807`. As milliseconds, dividing by 1000 gives
`9,223,372,036,854,775` seconds; dividing that by 31,556,952 (the mean number
of seconds in a Gregorian year) gives approximately `292,277,024` years. So a
`long` of milliseconds spans roughly **±292 million years** around the epoch.
`Instant`'s declared range is **±1 billion years** — about **3.4 times wider**
than a millisecond `long` can express (1,000,000,000 / 292,277,024 ≈ 3.42).
Measured: `Instant.MAX.toEpochMilli()` throws
`ArithmeticException: long overflow`.

The implementation choice behind that exception is the point worth taking
away. `toEpochMilli` uses **checked** multiplication and addition rather than
plain `long` arithmetic that would silently wrap on overflow, so an
out-of-range instant fails loudly with a named exception instead of returning
a plausible-looking wrong millisecond value. That is the same discipline
`Math.multiplyExact` provides for money arithmetic
(`../numbers-and-money/03b-internals-biginteger-and-long-cents.md`) and it is
the opposite of the silent two's-complement wraparound that plain `long`
arithmetic performs by default
(`../primitives-and-conversions/01a-integral-arithmetic.md`).

There is a practical corollary. `getEpochSecond()` and `getNano()` never
overflow, because they are `Instant`'s own stored fields (`long seconds`,
`int nanos`) — the overflow only happens in the derived `toEpochMilli`
conversion, not in reading the instant's native representation. So if a
system genuinely needs to serialise an extreme `Instant` — outside the
±292-million-year band a millisecond `long` can hold — the fix is to
serialise `getEpochSecond()` and `getNano()` directly, not `toEpochMilli()`.
In practice, no QuizStakes timestamp — a `Movement.postedAt`, a
`PaymentRun` cutoff, a `Bonus` expiry — comes anywhere near this boundary; the
value of knowing the mechanism is what it reveals about JDK design
philosophy: loud failure was chosen over silent corruption, deliberately, at
every conversion boundary in this part of the API.

```java
public record PayoutFileTimestamp(long epochSecond, int nano) {

    public static PayoutFileTimestamp from(Instant instant) {
        return new PayoutFileTimestamp(instant.getEpochSecond(), instant.getNano());
    }

    public Instant toInstant() {
        return Instant.ofEpochSecond(epochSecond, nano);
    }
}
```

Round-tripping through `epochSecond`/`nano` rather than `toEpochMilli()`
means this record can carry any `Instant` in the declared `MIN`..`MAX` range
without ever risking the overflow exception — at the cost of two `long`/`int`
fields instead of one `long`.

**Pitfall:** assuming `toEpochMilli()` is a safe, universal conversion for
any `Instant` a system might construct. It is safe for the ±292-million-year
band a millisecond `long` can hold, and it throws `ArithmeticException` for
anything constructed near `Instant.MIN` or `Instant.MAX` — which a system
that lets any code construct arbitrary instants (from untrusted input, say)
can actually reach.

**Insight:** the 3.4x mismatch between `Instant`'s declared range and a
millisecond `long`'s range is not an oversight — the range was chosen to be
"proleptic Gregorian to the edges of plausible use", independent of whatever
representation a given conversion method happens to use, and each conversion
method is then responsible for failing honestly when it cannot cover that
range.

**Interview:** "Can `Instant.toEpochMilli()` throw?" — yes, `ArithmeticException:
long overflow`, for instants near `Instant.MIN` or `Instant.MAX`, because a
`long` of milliseconds spans about ±292 million years while `Instant` itself
spans about ±1 billion.

> `toEpochMilli()` uses checked arithmetic and throws
> `ArithmeticException: long overflow` for instants outside the roughly
> ±292-million-year range a millisecond `long` can express — `Instant`'s own
> range is about 3.4x wider, so the checked failure is the deliberate,
> documented behaviour, not a defect.

---

## 3. The Java time-scale, and the deliberate omission of leap seconds (3.16.13)

The `Instant` Javadoc defines something it calls the "Java time-scale", and
it is worth reading as an actual specification rather than folklore about
"Java ignoring leap seconds", because the requirements are specific enough to
state as a list.

The definition, as given: each calendar day has exactly 86,400 "seconds"; the
time-scale agrees exactly with UTC for the whole period for which UTC is
defined, **except** in the vicinity of a leap second, where the specification
permits the implementation to smear rather than represent a `:60` second
directly; and for periods before UTC's own definition, it agrees with UT1.

What "exactly 86,400" buys is the whole trade, and it is a real trade, not a
free lunch. Because every day is defined to have the same number of seconds,
`Duration` arithmetic is exact and reversible — adding a `Duration` and then
subtracting it always returns to the original instant, with no day-dependent
correction needed. `ChronoUnit.SECONDS.between` reduces to plain subtraction
of `seconds` fields, with no leap-second table to consult. And no `Instant`
value can ever have a `:60` second field, because the scale simply defines
that second out of existence for accounting purposes.

What it costs, and where the cost lands: an interval measured across an
actual UTC leap second is off by up to one second, because that second either
never existed in Java's accounting at all, or was absorbed into a
smear by the host clock rather than represented explicitly. The JDK itself
does not implement the smearing — it takes whatever the underlying host clock
delivers, and NTP implementations differ in how they handle a leap second
(some step it in one jump, some slew the clock rate over the surrounding
seconds, some smear it over an entire day), so the observable behaviour at
the moment of a leap second is a property of the deployment's clock
infrastructure, not of Java itself.

This is documented as deliberate, not discovered as an oversight — and the
honest verdict for this domain is that it does not matter here. No QuizStakes
figure is sensitive to a one-second discrepancy: not the `PaymentRun` window
cutoff, not the 30-day bonus expiry window (§4, bonus rules), not a p99
latency measurement against the card PSP's 11-second authorise figure (§4,
numbers). The correct engineering response to a limitation this small,
relative to every real deadline in the domain, is to know it exists and
deliberately not design around it — spending effort compensating for a
sub-second discrepancy in a system whose smallest meaningful time window is
measured in seconds-to-days would be effort spent on the wrong axis.
`02c-temporal-arithmetic-and-adjusters.md` covers the leap-*year* half of
calendar irregularity (`Year.isLeap`, end-of-month clamping) — that is a
distinct mechanism from leap *seconds* and is not repeated here.

**Pitfall:** treating "Java doesn't handle leap seconds" as a bug report
worth filing or working around. It is a documented part of the Java
time-scale's definition, and the systems it would matter to (precise
astronomical timing, certain financial settlement protocols with
sub-second regulatory tolerances) are not the ones this domain, or most
application domains, operate in.

**Insight:** the time-scale's "exactly 86,400 seconds per day" rule is what
makes `Duration` arithmetic exact in the first place — the leap-second
omission is not a separate quirk sitting alongside clean arithmetic, it is
the price paid *for* clean arithmetic.

**Interview:** "How does `java.time` handle leap seconds?" — it defines them
out of its accounting: every day is defined as exactly 86,400 seconds, UTC is
followed exactly everywhere except at a leap second, where the JDK permits a
smear rather than a `:60` value, and the actual smearing behaviour is
delegated entirely to the host clock and its NTP configuration.

> The Java time-scale defines every day as exactly 86,400 seconds and
> tracks UTC exactly except at a leap second, where the specification
> permits the underlying clock to smear rather than expose a `:60` second —
> a deliberate trade that makes `Duration` arithmetic exact at the cost of
> sub-second accuracy across the rare leap-second boundary.

---

## 4. `Date` and `Timestamp` internals (3.16.14)

`java.util.Date` is a **mutable wrapper around a single `long` of
milliseconds since the epoch** — no zone, no calendar, and a class name that
describes none of what it actually stores. `java.sql.Timestamp` **extends**
`Date` and adds its own separate `int nanos` field, and that addition is
where nearly every surprise in this section originates, because the value is
now split across two fields — one inherited, one new — in a way neither
type's public API makes obvious at the call site.

### How it works

**The split, measured (§6.20).** Starting from a `Timestamp` constructed on
`1774000000000L` milliseconds, after `ts.setNanos(123456789)`:

```
ts.getTime()   -> 1774000000123
ts.toString()  -> "2026-03-20 15:16:40.123456789"
ts.toInstant() -> 2026-03-20T09:46:40.123456789Z
```

`getTime()` — inherited straight from `Date` — reads back
`1774000000123`: the millisecond portion of the nanosecond value
(`123` of `123456789`) has been folded back into the inherited millis field,
while the full nine-digit value only appears through `toString()` or
`toInstant()`. So the inherited field carries millisecond resolution and the
`nanos` field separately carries the complete sub-second value, and the two
are kept partially redundant with each other rather than one deriving
cleanly from the other. The practical hazard: code that calls `getTime()` on
a `Timestamp` — perfectly ordinary-looking code, since `getTime()` is
`Date`'s own method — silently truncates to milliseconds with no signal that
more precision was ever present.

**The asymmetry, measured (§6.20) — the interview-grade fact in this
section.** For a `Date` and a `Timestamp` built from the identical millis
value:

```
d.equals(ts)                -> true
ts.equals(d)                -> false      <-- ASYMMETRIC
d.getTime() == ts.getTime() -> true
d.compareTo(ts)              -> 0
```

The mechanism is exact and small. `Date.equals(Object)` compares only
`getTime()` against any object that is itself a `Date` (or a subclass), so it
accepts a `Timestamp` carrying the same millis value without objection.
`Timestamp.equals(Object)` is overridden to return `false` for anything that
is not itself a `Timestamp` — a `Date` fails that check immediately,
regardless of what `getTime()` returns. That directly **violates the
symmetry clause of the `equals` contract**: `a.equals(b)` must equal
`b.equals(a)` for any non-null `a` and `b`. The consequence is concrete and
not merely theoretical: a `HashSet<Date>` or a `Map` keyed on `Date` that
happens to contain both a `Date` and a `Timestamp` for the same instant
cannot behave sensibly, because whether a lookup succeeds depends on which
object happens to be the receiver of `equals` — `set.contains(timestamp)`
and `set.contains(date)` can give different answers for logically identical
membership tests. This is the textbook demonstration of why extending a
concrete class and narrowing (or otherwise changing) its `equals` behaviour
is a mistake — `../objects-equality-and-lifecycle/01b-equals-hashcode-and-object-methods.md`
owns the contract itself, and `../inheritance-and-dispatch/01-basics.md`
owns the inheritance half of why concrete-class extension is the wrong tool
here.

**The bridge methods, and the loss each one carries, measured (§6.20).**

| Conversion | Behaviour | Measured |
|---|---|---|
| `Date.toInstant()` | Exact: millis converted to seconds + nanos, normalised to a non-negative `nanos` even for pre-epoch dates | Lossless |
| `Date.from(Instant)` | Truncates below the millisecond, no exception | `Date.from(Instant.parse("2026-03-15T14:30:45.123456789Z")).toInstant()` → `2026-03-15T14:30:45.123Z` — six digits gone silently |
| `Timestamp.from(Instant)` / `Timestamp.toInstant()` | Nanosecond-capable | Lossless |

`Date.from` losing six fractional digits with no exception anywhere is the
one thing worth internalising as a standalone fact: it is the single place in
this bridge where data quietly disappears rather than either round-tripping
exactly or failing loudly, which puts it in sharp contrast with the checked,
loud-failure discipline `toEpochMilli()` uses (this file, §2) for a different
kind of boundary violation. `Timestamp`'s nanosecond capability is the one
thing it does better than `Date` — the price is the split-field
representation and the broken `equals` symmetry documented above.

### A concrete example

```java
public final class LegacyTimestampBridge {

    public static Instant toDomainInstant(java.util.Date legacyValue) {
        return legacyValue.toInstant();
    }

    public static java.sql.Timestamp toJdbcTimestamp(Instant domainValue) {
        return java.sql.Timestamp.from(domainValue);
    }
}
```

The rule this file closes on: convert at the boundary, in exactly one place,
and never let a `java.util.Date` or a `java.sql.Timestamp` reach domain code
past that boundary. `02a-instant-local-and-zoned.md` argued for that
discipline from the modelling side — pick `Instant`/`LocalDate`/`ZonedDateTime`
as your domain types and never let a legacy type leak past the JDBC or
serialization boundary. This file has now justified the same rule from the
field level: `Date` loses precision silently on the way in from `Instant`,
and `Timestamp` breaks `equals`'s symmetry contract on the way anywhere it is
compared against its own superclass.

**Pitfall:** treating `Date.from(Instant)` as a lossless, safe conversion
because it neither throws nor visibly changes the value at millisecond
granularity. It truncates any fractional-millisecond content with no
exception — measured, nine digits become three with the last six simply
discarded.

**Pitfall:** storing both `Date` and `Timestamp` instances for the same
logical moment in one `Set` or `Map` and expecting `contains`/lookup to treat
them as interchangeable. `Timestamp.equals` rejects any non-`Timestamp`
argument, so `ts.equals(date)` is `false` even when `date.equals(ts)` is
`true` — the container's behaviour then depends on which object is the
receiver.

**Insight:** the split between `getTime()` (millisecond, inherited) and
`getNanos()` (nanosecond, own field) on `Timestamp` is not two views of one
number — they are two separately-settable fields kept only partially in sync
by convention, which is exactly why `setNanos` folding the millisecond part
back into `getTime()`'s underlying storage is worth reading as a field-level
mechanism rather than a black box.

**Interview:** "Why can't you put a `Date` and a `Timestamp` for the same
instant in the same `HashSet` safely?" — because `Timestamp.equals` overrides
`Date.equals` to reject any non-`Timestamp` argument, so `ts.equals(date)` and
`date.equals(ts)` disagree — a direct violation of `equals`'s symmetry
contract, and `hashCode`/`equals`-based containers assume symmetry holds.

> `Timestamp` extends the concrete, mutable `Date` and narrows `equals` to
> reject non-`Timestamp` arguments while `Date.equals` accepts any subclass
> with matching millis — an asymmetric pair that is the textbook argument
> against extending a concrete class to add a field and an `equals` override.

---

## Pitfalls

### "`Instant.equals` after a database round trip should pass if the values are 'basically the same'"

**Wrong**

```java
Instant before = Instant.now();
saveToLedgerColumn(before);
Instant after = loadFromLedgerColumn();
assertThat(after).isEqualTo(before);
```

Fails intermittently: measured, `now.equals(now.truncatedTo(ChronoUnit.MILLIS))`
is `false`, because a millisecond-precision database column drops the
microsecond content the JDK 9+ clock actually populated, and `Instant.equals`
compares `seconds` and `nanos` with zero tolerance.

**Right**

```java
Instant before = Instant.now().truncatedTo(ChronoUnit.MILLIS);
saveToLedgerColumn(before);
Instant after = loadFromLedgerColumn();
assertThat(after).isEqualTo(before);
```

Truncating before the boundary on both sides makes the comparison exact at
the precision the storage layer actually supports, and it also fixes the
same mismatch in any production code path that compares the stored value
against a freshly-read clock value.

**Why people believe it:** on Java 8, `Clock.systemUTC()` itself returned
millisecond precision, so this exact test passed by accident — the round
trip really was lossless back then. Java 9+ changed the clock's resolution,
not the test's correctness, and the old assumption silently stopped holding.

### "`Instant.toEpochMilli()` is safe for any `Instant` you can construct"

**Wrong**

```java
Instant farFuture = Instant.MAX;
long millis = farFuture.toEpochMilli();
```

Throws `ArithmeticException: long overflow` — `Instant.MAX` is about a
billion proleptic years from the epoch, roughly 3.4x further than a
millisecond `long` (about ±292 million years) can express.

**Right**

```java
Instant farFuture = Instant.MAX;
long epochSecond = farFuture.getEpochSecond();
int nano = farFuture.getNano();
```

`getEpochSecond()` and `getNano()` read `Instant`'s own stored fields
directly and never overflow — any instant that needs to survive a conversion
outside the millisecond `long`'s range should be carried through these two
fields, not through `toEpochMilli()`.

**Why people believe it:** `toEpochMilli()` works without incident for every
ordinary, present-day timestamp a typical application ever constructs, so
the method looks universally safe until an instant near `MIN` or `MAX`
actually reaches it — which in most systems, including QuizStakes, simply
never happens, making the failure mode easy to miss in testing.

### "`Date` and `Timestamp` are interchangeable for equality purposes since one extends the other"

**Wrong**

```java
Set<Date> postedTimestamps = new HashSet<>();
postedTimestamps.add(new Timestamp(1774000000000L));
boolean found = postedTimestamps.contains(new Date(1774000000000L));
```

`found` is unreliable depending on hash-bucket layout and which object's
`equals` a given `HashSet` implementation happens to invoke during the
lookup — measured, `Timestamp.equals(Date)` is `false` while
`Date.equals(Timestamp)` is `true` for the identical millis value, so the
contract `equals` relies on is already broken before this container is even
involved.

**Right**

```java
Set<Instant> postedTimestamps = new HashSet<>();
postedTimestamps.add(new Timestamp(1774000000000L).toInstant());
boolean found = postedTimestamps.contains(new Date(1774000000000L).toInstant());
```

Converting both legacy values to `Instant` at the point of insertion removes
the asymmetric `equals` entirely — `Instant.equals` compares its own
`seconds`/`nanos` fields symmetrically, with no subclass-narrowing involved.

**Why people believe it:** `Timestamp extends Date` reads, at the type-system
level, as "a `Timestamp` is-a `Date`", and most well-behaved subclass
relationships in application code do preserve `equals` symmetry — `Timestamp`
is the counter-example the JDK itself ships, precisely because it overrides
`equals` to narrow the accepted type rather than only extending the compared
fields.

---

## Cheat sheet

| Thing | Fact (Java 21 LTS) |
|---|---|
| `Instant.nanos` field capacity | 0..999,999,999 (`int`), nanosecond-wide by declaration |
| Actual resolution source | Whatever `Clock.systemUTC()` obtains from the OS via `VM.getNanoTimeAdjustment` |
| Measured resolution, this build | Microsecond (trailing three digits of `getNano()` always `000`) |
| Measured `Instant.now()` | `2026-08-29T09:57:50.444951Z`, `getNano()` = `444951000` |
| `now.truncatedTo(MILLIS)` | `2026-08-29T09:57:50.444Z` |
| `now.equals(truncated)` | `false` — `equals` compares `seconds`/`nanos` exactly, no tolerance |
| Version trap | Java 8 `Clock.systemUTC()` = millisecond precision; Java 9+ = microsecond or better |
| `Clock.tickMillis` | Rounds at the source: measured `09:57:50.445Z` vs untruncated `09:57:50.444986Z` |
| Round-trip test fix (X-REF 16) | Truncate both sides deliberately, or compare with tolerance, at the boundary |
| `Instant.MIN` | `-1000000000-01-01T00:00:00Z` |
| `Instant.MAX` | `+1000000000-12-31T23:59:59.999999999Z` |
| `long` ms range | `Long.MAX_VALUE` ms ÷ 1000 ÷ 31,556,952 s/yr ≈ 292,277,024 years |
| `Instant` range vs `long` ms range | ~1 billion years vs ~292 million — about 3.4x wider |
| `Instant.MAX.toEpochMilli()` | Throws `ArithmeticException: long overflow` |
| Why it throws | `toEpochMilli` uses checked arithmetic, not silent wraparound |
| Overflow-safe fields | `getEpochSecond()`, `getNano()` — never overflow |
| Java time-scale, seconds/day | Exactly 86,400, always |
| Java time-scale vs UTC | Exact, except at a leap second, where a smear is permitted |
| Java time-scale, pre-UTC | Agrees with UT1 |
| What exact 86,400 buys | Exact/reversible `Duration` arithmetic; `SECONDS.between` is plain subtraction |
| What it costs | Up to 1 second of drift across an actual UTC leap second |
| Who implements the smear | The host clock / NTP configuration, not the JDK |
| QuizStakes sensitivity to 1s drift | None — no figure in the domain depends on sub-second accuracy |
| `java.util.Date` internals | Mutable wrapper around one `long` millis field; no zone, no calendar |
| `java.sql.Timestamp` internals | Extends `Date`; adds its own `int nanos` field |
| `ts.setNanos(123456789)` then `ts.getTime()` | Millis portion (123) folds back into inherited field |
| `d.equals(ts)` | `true` (same millis) |
| `ts.equals(d)` | `false` — asymmetric |
| Root cause of asymmetry | `Timestamp.equals` rejects non-`Timestamp`; `Date.equals` accepts any matching-millis `Date` subclass |
| `d.compareTo(ts)` | `0` |
| `Date.toInstant()` | Exact, lossless |
| `Date.from(Instant)` | Truncates below millisecond, no exception — 6 digits lost silently |
| `Timestamp.from`/`toInstant()` | Nanosecond-capable, lossless |
| Boundary discipline | Convert `Date`/`Timestamp` to `Instant` in exactly one place; never let them reach domain code |

---

## Self-test

**Q1.** Why does `Instant.now().equals(Instant.now().truncatedTo(ChronoUnit.MILLIS))` return `false`, and why did the equivalent check pass on Java 8?

<details><summary>Answer</summary>

`Instant.equals` compares the `seconds` and `nanos` fields exactly, with no
built-in tolerance. On this build, `Instant.now()` carries real microsecond
content (measured: `getNano()` = `444951000`, six significant digits), so
truncating to milliseconds produces a genuinely different `nanos` value
(`444000000`) and the two objects are unequal by definition. On Java 8,
`Clock.systemUTC()` itself only delivered millisecond precision, so
`Instant.now()` never had sub-millisecond content to lose in the first place
and the identical equality check passed by coincidence of the clock's
resolution, not by any guarantee in `Instant` itself.

</details>

**Q2.** Derive why `Instant.MAX.toEpochMilli()` overflows, using the actual numbers.

<details><summary>Answer</summary>

`Instant.MAX` is about one billion proleptic years from the epoch. A `long`
holding milliseconds maxes out at `Long.MAX_VALUE` = 9,223,372,036,854,775,807;
dividing by 1000 gives about 9.22 quadrillion seconds, and dividing that by
roughly 31,556,952 seconds per year gives about 292,277,024 years — call it
292 million. `Instant`'s billion-year range is roughly 3.4 times wider than
that, so any instant close to `Instant.MAX` or `Instant.MIN` cannot be
represented as a millisecond count in a `long`, and `toEpochMilli()`'s
checked arithmetic throws `ArithmeticException: long overflow` rather than
returning a wrapped, wrong value.

</details>

**Q3.** State the Java time-scale's definition in your own words, and say what it buys and what it costs.

<details><summary>Answer</summary>

Every calendar day is defined to have exactly 86,400 seconds; the scale
tracks UTC exactly except around an actual leap second, where the
specification permits the implementation to smear rather than expose a `:60`
value; before UTC's own definition existed, the scale follows UT1 instead.
The benefit is that `Duration` arithmetic becomes exact and reversible and
`ChronoUnit.SECONDS.between` is a plain subtraction, with no leap-second
table needed anywhere. The cost is that an interval measured across a real
UTC leap second can be off by up to one second, and how that second is
actually absorbed is left entirely to the host clock and its NTP
configuration rather than being handled by the JDK.

</details>

**Q4.** Why does `ts.equals(date)` return `false` while `date.equals(ts)` returns `true` for a `Date` and a `Timestamp` built from the same millis value, and why does that matter?

<details><summary>Answer</summary>

`Date.equals(Object)` only compares `getTime()` and accepts any `Date`
subclass with a matching value, so it accepts the `Timestamp`.
`Timestamp.equals(Object)` is overridden to return `false` for anything that
is not itself a `Timestamp`, so it rejects the plain `Date` even though the
millisecond values are identical. That breaks the symmetry clause of the
`equals` contract (`a.equals(b)` must equal `b.equals(a)`), and the practical
consequence is that a `HashSet` or `Map` containing both a `Date` and a
`Timestamp` for the same instant cannot behave predictably — whether a
lookup succeeds depends on which object happens to be the receiver of the
`equals` call.

</details>

**Q5.** What exactly does `Timestamp.setNanos(123456789)` do to the value returned by the inherited `getTime()`, and why does that matter for a naive caller?

<details><summary>Answer</summary>

Measured: after constructing a `Timestamp` on 1,774,000,000,000 ms and
calling `setNanos(123456789)`, `getTime()` returns `1774000000123` — the
millisecond portion of the nanosecond value (123 of 123456789) is folded back
into the inherited millis field, while the complete nine-digit fractional
value is only visible through `toString()` or `toInstant()`. A caller who
reads `getTime()` expecting the full precision they just set gets silently
truncated to milliseconds, with nothing in the method signature or a thrown
exception to indicate precision was lost.

</details>

**Q6.** Why is `Date.from(Instant)` a lossy conversion, and how does that differ from `toEpochMilli()`'s handling of an out-of-range value?

<details><summary>Answer</summary>

`Date.from(Instant)` truncates anything below millisecond precision with no
exception at all — measured, converting
`Instant.parse("2026-03-15T14:30:45.123456789Z")` through `Date.from` and back
through `toInstant()` yields `2026-03-15T14:30:45.123Z`, silently discarding
six fractional digits. That is the opposite discipline from
`toEpochMilli()`, which uses checked arithmetic and throws
`ArithmeticException: long overflow` rather than silently returning a
truncated or wrapped value when the conversion cannot be represented exactly.
One boundary fails loudly; the other loses data quietly — which is why
`Date.from` is the one to treat with suspicion at any boundary that cares
about sub-millisecond precision.

</details>

---

## Open questions

None. Every claim above is sourced from §6.13, §6.17, §6.20 of the measured
brief, or from the `Instant` Javadoc's time-scale definition and
`toEpochMilli` contract named inline.

---

**Leaves covered:** 3.16.11–3.16.14 (4 leaves)
**Leaves deferred:** none
**Diagrams included:** none
**Target version:** Java 21 LTS
**Lines:** 686
