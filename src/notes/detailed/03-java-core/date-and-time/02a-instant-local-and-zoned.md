# 03 Java Core — `Instant`, local and zoned: which type answers which question — INTERMEDIATE (§2.5, 2.5.5–2.5.6, 2.5.11–2.5.12)

**Target version: Java 21 LTS.** | **Part 2 of 5** | [Index](../00-index.md)
Previous: [Date and time: why java.time exists, and the type map](02-date-and-time.md) · Next: [Amounts, DST and the tzdb](02b-amounts-dst-and-tzdb.md)

This file owns the practical modelling decision the type map in `02` only
named: which of `Instant`, `LocalDateTime`, `ZonedDateTime`, `OffsetDateTime`
correctly answers "does this identify a moment," what to store where, the
region-versus-fixed-offset distinction, and the hidden host dependency in
`ZoneId.systemDefault()`. `02b` picks up the full DST gap/overlap mechanics
this file only needs the surface of. Measured on Oracle JDK 21.0.7 (build
21.0.7+8-LTS-245), macOS aarch64, tzdb version 2025a. This file has no diagram
of its own beyond a table — D-075 and D-080 live in `02-date-and-time.md`;
D-077 and D-078 live in `02b-amounts-dst-and-tzdb.md`.

---

## 1. `LocalDateTime` is not an instant (2.5.5)

**Pitfall:** treating `LocalDateTime` as a timestamp because
`LocalDateTime.now()` compiles, runs, and its `toString()` looks exactly like
one.

### The model

`LocalDateTime` is what a wall clock and a calendar on a wall *read* — with
no statement about which wall. `2026-03-15T14:30` is 09:00 UTC in London and
19:00 UTC+5:30 the same clock face in Kolkata name two different moments on
the timeline. Written on its own, `2026-03-15T14:30` names no point on the
timeline at all; it names a reading that could belong to any of 603 zones.

### Proof from the API surface

The type system enforces this, and enforces it by omission rather than by
exception. There is no `LocalDateTime.toEpochMilli()`. There is no
zero-argument `toInstant()`. The only two routes off `LocalDateTime` and onto
the timeline both *demand* the missing piece as an argument:

```java
LocalDateTime reading = LocalDateTime.of(2026, 3, 15, 14, 30);

Instant viaOffset = reading.toInstant(ZoneOffset.of("+05:30"));   // must supply offset
ZonedDateTime viaZone = reading.atZone(ZoneId.of("Asia/Kolkata")); // must supply zone
Instant viaZoneThenInstant = viaZone.toInstant();
```

**That absence is the type system telling the truth.** `LocalDateTime` cannot
lie about being a timestamp, because it has no method that would let it
pretend to be one without the caller supplying the missing zone or offset
explicitly.

### The QuizStakes symptom

`Movement.postedAt` typed as `LocalDateTime` reads correctly on a developer's
laptop in one zone, reads correctly in a single-region deployment, and
silently misorders settlements the moment two services in different zones
write rows into the same ledger — because `2026-03-15T14:30` from a
`Europe/London` node and `2026-03-15T14:30` from an `Asia/Kolkata` node
compare as *equal* local readings while naming moments 5.5 hours apart. Both
values look entirely plausible in isolation, so nothing fails loudly; the
ledger simply has entries in the wrong order.

```java
// WRONG: no statement of which wall clock this reading belongs to.
public record Movement(long id, BigDecimal amount, LocalDateTime postedAt) {}

// RIGHT: an instant, unambiguous regardless of which service or region wrote it.
public record Movement(long id, BigDecimal amount, Instant postedAt) {

    // The zone belongs at the presentation boundary, not on the domain type.
    public String renderedFor(ZoneId viewerZone) {
        return postedAt.atZone(viewerZone).toLocalDateTime().toString();
    }
}
```

**Insight:** `Instant` and `LocalDateTime` are both `Comparable`, but
comparing one to the other is not even *expressible* — there is no overload
of `compareTo` that accepts the other type. That is a small mercy the API
earns precisely by keeping the two types separate: the compiler refuses the
comparison a developer should never have written by hand.

**Interview:** "Why can't you convert `LocalDateTime` to epoch millis
directly?" — because it names a calendar/clock reading with no zone, and a
reading with no zone corresponds to a different instant in every zone; the
API forces the missing zone or offset to be supplied as an argument rather
than silently defaulting one in.

> `LocalDateTime` is a wall-clock-and-calendar reading with no stated wall —
> it cannot identify a moment, and the API enforces that by giving it no
> zero-argument route onto the timeline.

---

## 2. What to store for what (2.5.6)

The rule, then the reason: store an `Instant` for anything that **happened**
— a deposit capture, a stake settlement, a status transition to
`AA-801 ACTIVATED`. Store a `LocalDate` for anything that **is a date in
someone's calendar with no time or zone attached** — a client's date of
birth, a `PaymentRun` business date, the end date of a 14-day coupon validity
window.

The test that decides which one a given field is: would a reader in another
zone need to see a *different local rendering* of this value to understand
it correctly? An event time — yes, render it in the viewer's own zone. A date
of birth — no, a client born on 1990-03-15 was born on 1990-03-15 everywhere
on Earth, and running that date through a zone conversion is exactly how
implementations end up making someone a day younger or older by accident.

### `[X-REF 09]` — database column types

`TIMESTAMP WITH TIME ZONE` normalises the stored value to UTC on write and is
the correct column for an `Instant` — the zone information you pass in is
used only to compute the UTC value, then discarded, which matches `Instant`
exactly since `Instant` never carried a zone either. `TIMESTAMP WITHOUT TIME
ZONE` stores precisely the local reading handed to it, with no normalisation,
and is the correct column for a `LocalDateTime` *only* when the value
genuinely is meant as a zoneless reading. `DATE` is correct for a `LocalDate`.
The trap: storing an event time in `TIMESTAMP WITHOUT TIME ZONE` works fine
until the application's default zone changes underneath it — see concept 4 —
at which point every previously-stored reading is silently reinterpreted
against a different zone. Guide 09 (SQL databases) owns the full column-type
treatment.

### Why the choice is cheap

Measured retained memory, JDK 21.0.7, 2,000,000 retained instances (§6.11):

| Type | Bytes/instance |
|---|---|
| `Instant` | 24.2 |
| `LocalDate` | 24.3 |
| `LocalDateTime` | 72.0 |
| `ZonedDateTime` | 96.0 |

The correct type is also the smaller one. At QuizStakes' measured 19.8M
ledger entries/day, each holding one `Instant` at 24 bytes:
19,800,000 × 24 ≈ 475,200,000 bytes ≈ **475 MB/day**. Storing a
`ZonedDateTime` instead of an `Instant` for the same field:
19,800,000 × 96 ≈ 1,900,800,000 bytes ≈ **1.9 GB/day** — roughly four times
the allocation, for information (a zone) the event-time field never needed in
the first place, since an `Instant` is already unambiguous. Full field
layouts and the object-header arithmetic behind these numbers are in
`03-internals-java-time.md` and D-127.

**D-076 belongs here — the summary of this concept and the one before it.**

**D-076** — Three types, three questions.

| Type | Identifies a moment | Survives a zone change | Right for a stake settlement timestamp | Right for a client date of birth | Right for a scheduled future `PaymentRun` | Database column type |
|---|---|---|---|---|---|---|
| `Instant` | Yes — a fixed point on the timeline, seconds + nanos since epoch | Yes — unaffected, since it never carried a zone to change | Yes — the event already happened, so the offset that applied is fixed forever | No — a birth date has no time-of-day and needs no timeline position | No — has no way to express "resolve against whatever rules apply at that future moment" | `TIMESTAMP WITH TIME ZONE` |
| `LocalDateTime` | No — a calendar/clock reading naming no specific wall | N/A — has no zone to survive a change of | No — ambiguous the moment two zones are involved (concept 1) | Yes, if truncated to the date part, but `LocalDate` is the tighter fit | Partially — needs a `ZoneId` paired with it to be resolvable later | `TIMESTAMP WITHOUT TIME ZONE`, only when the zonelessness is intentional |
| `ZonedDateTime` | Yes — resolves to exactly one `Instant` at the moment it is read | Yes, and correctly — re-resolves against the region's current rules on every read | Acceptable but heavier than needed for something already fixed | No — carries a time-of-day and zone a birth date does not have | Yes — this is the reason it exists; re-resolves against DST rules that may change before the future date arrives (`02b`) | Not a native SQL type; store the region separately if precise future re-resolution matters |
| `OffsetDateTime` | Yes — resolves to exactly one `Instant`, computed directly from the stored offset | No — the offset is frozen at write time and does not track rule changes | Yes — a fixed offset is fine for something that already happened | No | No — a frozen offset cannot express "this local time may later require a different offset" (concept 3) | Common wire-format type; maps cleanly to `TIMESTAMP WITH TIME ZONE` on read |
| epoch millis (`long`) | Yes — a raw instant with no readable structure | Yes — a number has no zone to lose | Acceptable but loses type safety — nothing stops arithmetic that silently mixes millis with seconds or with an unrelated `long` | No — needs decoding through a zone to become a meaningful calendar date first | No — same objection as `Instant` | `BIGINT`, occasionally seen in legacy or cross-language wire formats |

**Gotcha:** no gotcha beyond what the table already states plainly — the risk
here is skimming the table instead of reading each "no" as a reason, not
just a verdict.

> Store what *happened* as an `Instant`; store what *is a date on someone's
> calendar* as a `LocalDate`; the memory cost of getting it right is smaller,
> not larger, than getting it wrong.

---

## 3. `ZoneId` versus `ZoneOffset` (2.5.11)

**Pitfall:** using `OffsetDateTime` with a fixed offset for a future
scheduled event, on the reasoning that "the offset is right today."

### The distinction

A `ZoneId` such as `Europe/London` names a **region** — a named set of rules
saying which offset applies at which instant, and crucially, those rules
change (governments move DST boundaries; `Europe/London` itself has switched
between +00:00 and +01:00 twice a year for decades and could change the
schedule again). A `ZoneOffset` such as `+01:00` is a **fixed number of
seconds from UTC**, with no rules attached and nothing that can change.
`ZoneOffset extends ZoneId`, which is exactly why the two are interchangeable
in method signatures that accept `ZoneId` — and exactly why the difference
is easy to overlook until it matters.

### Why the region must be stored for future scheduling

Measured, tzdb 2025a, `Europe/London` (§6.14). The region's rules define two
transitions relevant here — a spring **gap** and an autumn **overlap** — and
a fixed offset can express neither.

A `PaymentRun` payout window scheduled for local `2026-10-25T01:30` in
`Europe/London`:

- Stored as `OffsetDateTime` with `+01:00` baked in, it is pinned to one
  instant forever, computed once, at write time.
- Stored as `ZonedDateTime` with the region `Europe/London`, it is
  **re-resolved** against the rules whenever it is read, and the rules say
  that local reading has **two** valid offsets that night —
  `r.getValidOffsets(LocalDateTime.of(2026, 10, 25, 1, 30))` returns
  `[+01:00, Z]`, an hour apart, because 01:30 local time occurs twice as
  the clocks fall back.

And going the other direction, six months earlier: local `01:30` on
2026-03-29 has **zero** valid offsets —
`r.getValidOffsets(LocalDateTime.of(2026, 3, 29, 1, 30))` returns `[]` —
because the clocks spring forward through that exact half hour and it never
occurs at all. A fixed offset cannot represent either situation: it does not
so much answer the question wrong as fail to notice there is a question to
ask. `02b-amounts-dst-and-tzdb.md` owns the full gap/overlap resolution
mechanics and D-077; this file stops at the modelling consequence.

### The decision rule

| Situation | Type to use |
|---|---|
| A **past** event, already happened | `Instant` — the rules that applied are already resolved and cannot retroactively change |
| A **future** scheduled local time (a `PaymentRun` payout window, a recurring batch cut-off) | `ZonedDateTime` with a named region, so it re-resolves against whatever rules are in force when the date arrives |
| A value received off the wire that carried an offset but no region (many APIs and log formats do this) | `OffsetDateTime` — the offset is what was actually given; inventing a region would be a guess, not a fact |
| A zone genuinely without daylight-saving rules (UTC itself) | `ZoneOffset.UTC` — there are no rules to lose by using a fixed offset here |

**Pitfall:** using `OffsetDateTime` for future scheduling. The offset that is
correct today is not guaranteed to be the offset that applies when the
future date actually arrives, and `OffsetDateTime` has no mechanism to
notice the rules changed underneath it — it simply keeps the frozen offset
it was given.

> `ZoneId` names a region whose offset the rules decide and can change;
> `ZoneOffset` names a fixed number with no rules — store the region whenever
> the date being scheduled is in the future.

---

## 4. `ZoneId.systemDefault()` is a hidden host dependency (2.5.12)

**Pitfall:** calling `LocalDate.now()`, `LocalDateTime.now()`, or
`ZonedDateTime.now()` with no arguments inside domain logic, and assuming the
result means the same thing regardless of where the process runs.

### The mechanism

`ZoneId.systemDefault()` reads `TimeZone.getDefault()`, which the JVM derives
from the `user.timezone` system property if it is set, else the `TZ`
environment variable if it is set, else the host operating system's
configured zone — none of which are under the application code's control.
Every no-argument `now()` call anywhere in `java.time` routes through this,
so a piece of business logic that calls `LocalDate.now()` carries an
invisible dependency on wherever the JVM process happens to be executing,
and identical code produces different values across two deployments of the
same artifact.

### The measured evidence

On the machine these notes were measured on: `ZoneId.systemDefault()`
returned **`Asia/Kolkata`**, and `TimeZone.getDefault().getID()` agreed,
also returning `Asia/Kolkata`. A container image with no `TZ` environment
variable set typically resolves to `UTC` by default. So a developer's laptop
(`Asia/Kolkata`, UTC+5:30) and a production container with no explicit `TZ`
(`UTC`) disagree by five and a half hours on what "today" means for any
`now()`-derived date boundary — precisely the leaf's point, and precisely
why a date-boundary bug of this shape reproduces on neither the developer's
machine nor a naive local test run.

### `[X-REF 19]` — deployment configuration

Set `TZ` explicitly in the container image or the deployment manifest rather
than relying on whatever the base image happens to default to, or pass
`-Duser.timezone=UTC` on the JVM command line. Pin the value in the
deployment configuration and treat any change to it as a configuration
change with a blast radius, because it silently moves every
`now()`-derived date boundary computed by every service reading that
configuration. Guide 19 (deployment/configuration) owns the operational
detail of pinning and auditing this setting.

### The durable, code-level fix

Configuration pinning helps, but the fix that survives a misconfigured host
is to never call the no-argument `now()` inside domain logic at all: inject
a `Clock` (`02e-clock-precision-and-storage.md` owns the full `Clock`
treatment) and pass an explicit `ZoneId` at every point a local date or time
is actually needed, typically only at a presentation boundary.

```java
public final class BonusService {

    private static final int EXPIRY_DAYS = 30;

    // WRONG: LocalDate.now() silently depends on the host's default zone.
    public boolean isExpiredUnsafe(LocalDate grantedOn) {
        return LocalDate.now().isAfter(grantedOn.plusDays(EXPIRY_DAYS));
    }

    private final Clock clock;
    private final ZoneId businessZone;

    public BonusService(Clock clock, ZoneId businessZone) {
        this.clock = clock;
        this.businessZone = businessZone;
    }

    // RIGHT: the zone is an explicit, injected dependency, and the clock is
    // swappable in tests without touching the host's configuration at all.
    public boolean isExpired(LocalDate grantedOn) {
        LocalDate today = LocalDate.now(clock.withZone(businessZone));
        return today.isAfter(grantedOn.plusDays(EXPIRY_DAYS));
    }
}
```

A bonus grant made at `23:30 UTC` falls on different calendar days depending
on which zone decides "today": `isExpiredUnsafe` answers using whatever zone
the host happens to be in, while `isExpired` answers using the zone the
business actually operates in, injected and named explicitly, regardless of
where the JVM process is deployed.

**Insight:** this is the same class of hidden host dependency as the
default-`Locale` trap in number formatting — one hides a zone, the other
hides a locale, and both are silently supplied by the environment rather than
by the caller. See
`../numbers-and-money/02e-parsing-and-formatting-numbers.md`.

> `ZoneId.systemDefault()` is not a constant — it is whatever `TZ`, the
> `user.timezone` property, or the host OS happens to say today, which is why
> domain logic should take an explicit `Clock` and `ZoneId` rather than ever
> calling the no-argument `now()`.

---

## Pitfalls

### `LocalDateTime.now().toString()` looks like a timestamp, so it must be one

**Wrong**

```java
public record Movement(long id, BigDecimal amount, LocalDateTime postedAt) {}

Movement m = new Movement(1, new BigDecimal("4.20"), LocalDateTime.now());
// m.postedAt() prints "2026-03-15T14:30:45.123456" — looks exactly like a timestamp
```

Two services in different zones writing this field produce local readings
that compare as ordered by clock-face value, not by actual moment — a
ledger row from `Europe/London` at 23:00 sorts before one from
`Asia/Kolkata` at 04:30 the same UTC instant, even though the London entry
happened later.

**Right**

```java
public record Movement(long id, BigDecimal amount, Instant postedAt) {}

Movement m = new Movement(1, new BigDecimal("4.20"), clock.instant());
// unambiguous regardless of which service, region, or zone produced it
```

**Why people believe it:** `LocalDateTime.now()` compiles without error,
returns a value immediately, and that value's `toString()` is visually
indistinguishable from an actual timestamp — nothing about calling it signals
that the zone information has been silently dropped.

### `ZoneId` and `ZoneOffset` are interchangeable since one extends the other

**Wrong**

```java
OffsetDateTime payoutWindow =
        OffsetDateTime.of(LocalDateTime.of(2026, 10, 25, 1, 30), ZoneOffset.ofHours(1));
// stored months in advance for a future PaymentRun
```

`r.getValidOffsets(LocalDateTime.of(2026, 10, 25, 1, 30))` returns
`[+01:00, Z]` — two valid offsets exist for that local time in
`Europe/London` because of the autumn clock-change overlap, and the frozen
`+01:00` cannot express or re-resolve against that fact.

**Right**

```java
ZonedDateTime payoutWindow =
        ZonedDateTime.of(LocalDateTime.of(2026, 10, 25, 1, 30), ZoneId.of("Europe/London"));
// re-resolves against Europe/London's rules whenever it is read
```

**Why people believe it:** `ZoneOffset extends ZoneId`, so every method that
accepts a `ZoneId` also accepts a `ZoneOffset` without a compile error,
which reads as permission to use them interchangeably rather than as an
implementation detail of the class hierarchy.

### `ZoneId.systemDefault()` returns a stable, environment-independent value

**Wrong**

```java
public LocalDate today() {
    return LocalDate.now();   // implicitly ZoneId.systemDefault()
}
```

Measured: on the development machine, `ZoneId.systemDefault()` is
`Asia/Kolkata`; a container with no `TZ` set typically resolves to `UTC`.
The same call returns dates up to 5.5 hours apart in calendar-day terms
depending purely on deployment environment.

**Right**

```java
public LocalDate today(Clock clock) {
    return LocalDate.now(clock);   // zone is explicit, part of the injected Clock
}
```

**Why people believe it:** `ZoneId.systemDefault()` returns *some* value
every time, consistently, on a given machine — the inconsistency only
appears when the same code is compared across two different machines or
containers, which most local testing never does.

---

## Cheat sheet

| Thing | Fact (Java 21 LTS) |
|---|---|
| `LocalDateTime.toEpochMilli()` | does not exist |
| `LocalDateTime.toInstant()` | does not exist with zero arguments; requires `toInstant(ZoneOffset)` |
| Route from `LocalDateTime` to an instant | `toInstant(ZoneOffset)` or `atZone(ZoneId).toInstant()` |
| `Instant` compared to `LocalDateTime` | not expressible — no `compareTo` overload accepts the other type |
| Store for "it happened" | `Instant` |
| Store for "a calendar date, no time, no zone" | `LocalDate` |
| SQL column for `Instant` | `TIMESTAMP WITH TIME ZONE` (normalises to UTC on write) |
| SQL column for a genuinely zoneless `LocalDateTime` | `TIMESTAMP WITHOUT TIME ZONE` |
| SQL column for `LocalDate` | `DATE` |
| Bytes/instance, `Instant` (measured) | 24.2 |
| Bytes/instance, `LocalDate` (measured) | 24.3 |
| Bytes/instance, `LocalDateTime` (measured) | 72.0 |
| Bytes/instance, `ZonedDateTime` (measured) | 96.0 |
| 19.8M `Instant`s/day allocation (measured base) | ≈ 475 MB/day |
| 19.8M `ZonedDateTime`s/day allocation, same count | ≈ 1.9 GB/day |
| `ZoneId` | a region; rules that decide offset-by-instant, and those rules change |
| `ZoneOffset` | a fixed number of seconds from UTC; no rules; `ZoneOffset extends ZoneId` |
| `Europe/London` spring gap, 2026 (measured) | `getValidOffsets(2026-03-29T01:30)` → `[]` |
| `Europe/London` autumn overlap, 2026 (measured) | `getValidOffsets(2026-10-25T01:30)` → `[+01:00, Z]` |
| Future scheduled event | `ZonedDateTime` + region, so it re-resolves against future rule changes |
| Past event | `Instant`, or `OffsetDateTime` if the source only supplied an offset |
| Fixed-offset zone with genuinely no rules | `ZoneOffset.UTC` |
| `ZoneId.systemDefault()` reads | `user.timezone` property → `TZ` env var → host OS default |
| Measured `ZoneId.systemDefault()` on dev machine | `Asia/Kolkata` |
| Typical container default with no `TZ` set | `UTC` |
| Fix for the hidden host dependency | inject `Clock`, pass explicit `ZoneId` at presentation boundaries |
| Never call in domain logic | the no-argument `now()` family |
| Parallel trap in number formatting | default `Locale` in `NumberFormat`/`DecimalFormat` — same hidden-host-dependency shape |
| D-076 in this file | rendered as a Markdown table per the manifest, not an SVG |

---

## Self-test

**Q1.** A teammate argues `LocalDateTime` is fine for `Movement.postedAt`
because its `toString()` already looks like a full timestamp. What is wrong
with that argument?

<details><summary>Answer</summary>

Looking like a timestamp is not the same as identifying one. `LocalDateTime`
has no zone, so `2026-03-15T14:30` names a different actual moment depending
on which zone produced it — the same local reading from `Europe/London` and
from `Asia/Kolkata` are 5.5 hours apart on the real timeline while comparing
as equal local values. The proof is in the API: there is no
`LocalDateTime.toEpochMilli()` and no zero-argument `toInstant()`; both exits
onto the timeline demand a zone or offset be supplied, because the type
genuinely does not have that information.

</details>

**Q2.** Give the rule for choosing between `Instant` and `LocalDate` for a
new field, and the test that decides it.

<details><summary>Answer</summary>

Store an `Instant` for anything that happened — an event with a position on
the universal timeline. Store a `LocalDate` for anything that is a date in
someone's calendar with no time or zone attached. The test: would a viewer
in a different zone need to see a different local rendering to understand
the value correctly? An event time — yes, so it needs a timeline position
(`Instant`) that can be rendered per-viewer. A date of birth — no, it is the
same date everywhere, so it needs no timeline position at all.

</details>

**Q3.** Why is `ZoneOffset` unsuitable for a `PaymentRun` payout window
scheduled six months in the future?

<details><summary>Answer</summary>

A `ZoneOffset` is a fixed number of seconds from UTC with no rules attached,
frozen at the moment it is created. A future scheduled local time needs to
be re-resolved against whatever DST rules are in force when that date
actually arrives, because those rules can define a gap (the local time never
occurs, as measured for `Europe/London` on 2026-03-29 at 01:30, where
`getValidOffsets` returns an empty list) or an overlap (the local time occurs
twice, as measured on 2026-10-25 at 01:30, where it returns two offsets an
hour apart). Only a `ZoneId`-backed `ZonedDateTime` can express and resolve
either situation; a frozen offset has no mechanism to notice the rules even
apply differently that day.

</details>

**Q4.** What determines the value `ZoneId.systemDefault()` returns, and why
is that a problem for domain logic?

<details><summary>Answer</summary>

It reads, in order, the `user.timezone` system property, then the `TZ`
environment variable, then the host operating system's configured zone —
none of which the application code controls or is even aware of at compile
time. It is a problem because every no-argument `now()` call routes through
it, so identical code produces different dates or timestamps purely based on
where the process happens to be deployed. Measured evidence: the same code
returns `Asia/Kolkata`-relative values on the development machine and would
typically return UTC-relative values on a container with no `TZ` configured
— a difference of 5.5 hours in what "today" means.

</details>

**Q5.** What is the durable fix for the `ZoneId.systemDefault()` dependency,
beyond pinning `TZ` in the deployment manifest?

<details><summary>Answer</summary>

Never call the no-argument `now()` family inside domain logic. Inject a
`Clock` into the service (so tests can substitute a fixed or offset clock)
and pass an explicit `ZoneId` representing the business's actual operating
zone, rather than the host's default zone, whenever a local date or time is
computed. Reserve the conversion back to a viewer's local zone for the
presentation boundary. Pinning `TZ` at the deployment level is still worth
doing as a second line of defense, but it does not fix code that hardcodes
an implicit dependency on whatever zone happens to be configured.

</details>

**Q6.** Why can a `ZonedDateTime` and an `OffsetDateTime` both resolve to
exactly one `Instant`, yet only one of them is right for future scheduling?

<details><summary>Answer</summary>

Both types carry enough information to compute a single instant at the
moment they are constructed or read — `ZonedDateTime` via its `ZoneId` plus
the currently-applicable offset, `OffsetDateTime` via the fixed offset it
was given directly. The difference is what happens on a *later* read.
`ZonedDateTime` re-resolves its stored local time against the region's
current rules every time it is queried, so a future date that turns out to
fall in a gap or an overlap is still handled correctly. `OffsetDateTime`'s
offset is frozen at construction and never re-resolved, so if the rules
governing that local time change before the future date arrives, the frozen
offset is simply wrong and nothing recomputes it.

</details>

---

## Open questions

None — every figure above is measured in §6 of the batch briefing (Oracle
JDK 21.0.7, tzdb 2025a) or follows directly from the `java.time` API surface
(the absence of `LocalDateTime.toEpochMilli()`/no-arg `toInstant()`, the
`ZoneOffset extends ZoneId` relationship, both verifiable against the
Javadoc).

---

**Leaves covered:** 2.5.5, 2.5.6, 2.5.11, 2.5.12 (4 leaves)
**Leaves deferred:** none
**Diagrams included:** D-076 (rendered as a Markdown table per the manifest)
**Target version:** Java 21 LTS
**Lines:** 575
