# 03 Java Core — Diagnostic harnesses — the DST harness, and the `Duration`/`Period` divergence — BUILD IT (§4.8, 4.8.10)

**Target version: Java 21 LTS.** | **Part 4 of 5** | [Index](../00-index.md)
Previous: [The SimpleDateFormat race](05d-concurrency-and-time-harnesses.md) · Next: [Part 1 interview wrap-up](../90-interview-basics.md)

---

## 1. The shape: a zone is a partial, non-injective function from labels to instants

A `LocalDateTime` is a **label**. `2026-03-29T01:30` is four numbers and a colon; it names a position
on a wall clock and nothing else. It does not identify a moment. An `Instant` is a moment — a count
of seconds and nanos from the epoch, the same for every observer. A `ZoneId`'s rules are the function
that converts between them, and that function is neither total nor injective:

| Property | What it would mean | Do the rules have it? |
|---|---|---|
| Total | every label maps to at least one instant | **no** — in a spring gap a label maps to zero |
| Injective | every label maps to at most one instant | **no** — in an autumn overlap a label maps to two |
| Bijective | exactly one instant per label, both ways | **no** — twice a year, for one hour |

That is the whole subject. Every DST bug is one of those two facts arriving somewhere that assumed a
bijection: a scheduler that thinks a local time names one moment a day, a uniqueness constraint on a
local timestamp column, an idempotency key built from a wall-clock string, an "add one day" that
quietly means "add 86,400 seconds".

`Duration` and `Period` diverge for the same reason from the other direction. `Duration` is a count of
seconds and nanos added **on the instant timeline**; `Period` is a count of calendar units added **on
the label timeline** and then re-resolved through the rules. Away from a transition both agree, which
is why the difference stays invisible for 363 days a year. Across a transition, one day is 23 hours or
25 hours depending on which timeline you counted on, and the two operations produce different instants
with almost the same spelling.

Three siblings own the theory: the rule table and how binary `tzdb.dat` loads is
[`../date-and-time/03a-internals-zonerules-and-tzdb.md`](../date-and-time/03a-internals-zonerules-and-tzdb.md),
amounts and DST semantics are
[`../date-and-time/02b-amounts-dst-and-tzdb.md`](../date-and-time/02b-amounts-dst-and-tzdb.md), and
temporal arithmetic is
[`../date-and-time/02c-temporal-arithmetic-and-adjusters.md`](../date-and-time/02c-temporal-arithmetic-and-adjusters.md).
This file is the **executed harness** and the printed evidence.

> A zone's rules are a partial, non-injective map from wall-clock labels to instants; the gap and
> the overlap are precisely where that map fails, and every DST bug is one of those two failures
> reaching code that assumed a bijection.

---

## 2. Pick the zone, and print the tzdb version rather than assuming it

QuizStakes is a UK-regulated platform, so `Europe/London` is the zone that matters: the banking
partner's payout file has **4 windows/day**, specified by UK wall clock.

**Do not hard-code the transition dates from memory.** The JDK ships a compiled copy of the IANA
time-zone database, and that copy is **updated in patch releases**. A reader on 21.0.9 may see
different *future* transitions from a reader on 21.0.7 — the past is stable, the future is a forecast
encoded in a `ZoneOffsetTransitionRule`. So the harness asks the rules what the next transition is,
and prints the tzdb version it asked. On the build in use — **Oracle JDK 21.0.7 (build
21.0.7+8-LTS-245), macOS aarch64** — that is:

```console
tzdb versions, Europe/London   [2025a]
next after 2026-01-01Z         Transition[Gap at 2026-03-29T01:00Z to +01:00]
next after that                Transition[Overlap at 2026-10-25T02:00+01:00 to Z]
```

So the two dates this file works with, **read from the rules rather than remembered**: the spring gap
opens at `2026-03-29T01:00` GMT and closes at `02:00` BST; the autumn overlap covers labels
`2026-10-25T01:00` to `02:00`, entered at `02:00 BST`.

**Insight:** `ZoneRulesProvider.getVersions(zoneId)` returns a `NavigableMap<String, ZoneRules>` keyed
by tzdb version string. The JDK's built-in provider publishes exactly one version, so the key set is
a single element — but the API is a map because a provider *may* serve several, which is how
`-Djava.time.zone.DefaultZoneRulesProvider` replacements support historical rule sets.

---

## 3. The harness

One class, complete, nothing elided. It prints the environment, then the gap, then the overlap, then the
divergence, then the legacy `Calendar` comparison; the real output follows in § 4. Note that the machine's
default zone here is `Asia/Kolkata` — the harness never reads the default zone for a computation, and every
call passes `Europe/London` explicitly, which is the discipline you want in production code too.

```java
import java.time.*;
import java.time.temporal.ChronoUnit;
import java.time.zone.ZoneOffsetTransition;
import java.time.zone.ZoneRules;
import java.time.zone.ZoneRulesProvider;
import java.util.*;

/**
 * Prints the gap and overlap behaviour of ZonedDateTime for Europe/London, and the
 * Duration/Period divergence across both transitions. Domain: QuizStakes PaymentRun,
 * which has four banking-partner payout windows a day.
 */
public final class DstHarness {

    static final ZoneId LONDON = ZoneId.of("Europe/London");
    static final ZoneRules RULES = LONDON.getRules();

    record IdempotencyKey(String value) { }

    /** The broken key: derived from a local wall-clock label. */
    static IdempotencyKey localKey(String runName, LocalDateTime label) {
        return new IdempotencyKey(runName + ":" + label);
    }

    /** The fixed key: derived from the instant the run actually fired at. */
    static IdempotencyKey instantKey(String runName, ZonedDateTime run) {
        return new IdempotencyKey(runName + ":" + run.toInstant().getEpochSecond());
    }

    static void p(String label, Object value) {
        System.out.printf("%-30s %s%n", label, value);
    }

    static void banner(String title) {
        System.out.println();
        System.out.println("=== " + title + " ===");
    }

    /**
     * Prints what each factory does with one label, and describes its transition.
     * strictCandidates is a List rather than a varargs parameter purely so this file
     * carries no bare ellipsis.
     */
    static void describeLabel(LocalDateTime label, List<ZoneOffset> strictCandidates) {
        List<ZoneOffset> valid = RULES.getValidOffsets(label);
        p("label under test", label);
        p("getValidOffsets", valid + "  (size=" + valid.size() + ")");
        ZoneOffsetTransition t = RULES.getTransition(label);
        p("getTransition", t);
        p("  isGap / isOverlap", t.isGap() + " / " + t.isOverlap());
        p("  getDuration", t.getDuration());
        p("  label before / after", t.getDateTimeBefore() + " / " + t.getDateTimeAfter());
        p("  offset before / after", t.getOffsetBefore() + " / " + t.getOffsetAfter());
        ZonedDateTime resolved = ZonedDateTime.of(label, LONDON);
        p("ZonedDateTime.of(label,zone)", resolved
                + "  localDateTime=" + resolved.toLocalDateTime()
                + "  instant=" + resolved.toInstant());
        p("label.atZone(zone)", label.atZone(LONDON)
                + "  equalToOf=" + label.atZone(LONDON).equals(resolved));
        for (ZoneOffset candidate : strictCandidates) {
            try {
                ZonedDateTime strict = ZonedDateTime.ofStrict(label, candidate, LONDON);
                p("ofStrict(label," + candidate + ")", strict + "  instant=" + strict.toInstant());
            } catch (DateTimeException e) {
                p("ofStrict(label," + candidate + ")", e.getClass().getName());
                p("  message", e.getMessage());
            }
        }
    }

    /** Prints plus(Duration.ofDays(1)) against plus(Period.ofDays(1)) from one start. */
    static void divergence(ZonedDateTime start) {
        ZonedDateTime byDuration = start.plus(Duration.ofDays(1));
        ZonedDateTime byPeriod = start.plus(Period.ofDays(1));
        p("start", start + "  instant=" + start.toInstant());
        p("plus(Duration.ofDays(1))", byDuration + "  instant=" + byDuration.toInstant());
        p("plus(Period.ofDays(1))", byPeriod + "  instant=" + byPeriod.toInstant());
        p("labels differ by",
                Duration.between(byDuration.toLocalDateTime(), byPeriod.toLocalDateTime()));
        p("elapsed Duration / Period", Duration.between(start, byDuration).toHours() + "h / "
                + Duration.between(start, byPeriod).toHours() + "h");
    }

    static boolean timeZoneHasSetRawOffset() {
        for (var method : TimeZone.class.getMethods()) {
            if (method.getName().equals("setRawOffset")) {
                return true;
            }
        }
        return false;
    }

    public static void main(String[] args) {
        banner("0. environment");
        p("java.version / vendor", System.getProperty("java.version")
                + " / " + System.getProperty("java.vendor"));
        p("tzdb versions, Europe/London", ZoneRulesProvider.getVersions("Europe/London").keySet());
        p("default zone", ZoneId.systemDefault());
        ZoneOffsetTransition spring = RULES.nextTransition(Instant.parse("2026-01-01T00:00:00Z"));
        ZoneOffsetTransition autumn = RULES.nextTransition(spring.getInstant().plusSeconds(1));
        p("next after 2026-01-01Z", spring);
        p("next after that", autumn);

        banner("1. the spring gap: a label that maps to no instant");
        LocalDateTime inGap = LocalDateTime.of(2026, 3, 29, 1, 30);
        describeLabel(inGap, List.of(ZoneOffset.UTC, ZoneOffset.ofHours(1)));
        ZonedDateTime gapResolved = ZonedDateTime.of(inGap, LONDON);

        banner("2. a PaymentRun window scheduled inside the gap");
        LocalDate springDay = LocalDate.of(2026, 3, 29);
        for (LocalTime window : List.of(LocalTime.of(1, 30), LocalTime.of(7, 30),
                LocalTime.of(13, 30), LocalTime.of(19, 30))) {
            ZonedDateTime fires = LocalDateTime.of(springDay, window).atZone(LONDON);
            System.out.printf("window %s -> fires at %s (offset %s, instant %s)%n",
                    window, fires.toLocalTime(), fires.getOffset(), fires.toInstant());
        }

        banner("3. the autumn overlap: a label that maps to two instants");
        LocalDateTime inOverlap = LocalDateTime.of(2026, 10, 25, 1, 30);
        describeLabel(inOverlap,
                List.of(ZoneOffset.ofHours(1), ZoneOffset.UTC, ZoneOffset.ofHours(2)));
        ZonedDateTime defaulted = ZonedDateTime.of(inOverlap, LONDON);
        ZonedDateTime earlier = defaulted.withEarlierOffsetAtOverlap();
        ZonedDateTime later = defaulted.withLaterOffsetAtOverlap();
        p("withEarlierOffsetAtOverlap", earlier + "  instant=" + earlier.toInstant());
        p("withLaterOffsetAtOverlap", later + "  instant=" + later.toInstant());
        p("same label / instants apart", earlier.toLocalDateTime().equals(later.toLocalDateTime())
                + " / " + Duration.between(earlier.toInstant(), later.toInstant()));
        p("of() picked the earlier?", defaulted.getOffset().equals(earlier.getOffset()));

        banner("4. the idempotency-key collision, and the fix");
        p("local key, 1st occurrence", localKey("PaymentRun", earlier.toLocalDateTime()));
        p("local key, 2nd occurrence", localKey("PaymentRun", later.toLocalDateTime()));
        p("keys equal, duplicate payout", localKey("PaymentRun", earlier.toLocalDateTime())
                .equals(localKey("PaymentRun", later.toLocalDateTime())));
        p("instant key, 1st occurrence", instantKey("PaymentRun", earlier));
        p("instant key, 2nd occurrence", instantKey("PaymentRun", later));
        p("keys equal", instantKey("PaymentRun", earlier).equals(instantKey("PaymentRun", later)));

        banner("5. Duration vs Period across the spring transition");
        divergence(ZonedDateTime.of(LocalDateTime.of(2026, 3, 28, 19, 30), LONDON));

        banner("6. Duration vs Period across the autumn transition");
        divergence(ZonedDateTime.of(LocalDateTime.of(2026, 10, 24, 19, 30), LONDON));

        banner("7. Duration.between vs ChronoUnit across a transition");
        ZonedDateTime runStart = ZonedDateTime.of(LocalDateTime.of(2026, 3, 28, 19, 30), LONDON);
        ZonedDateTime runEnd = ZonedDateTime.of(LocalDateTime.of(2026, 3, 29, 19, 0), LONDON);
        p("start / end", runStart + "  ->  " + runEnd);
        p("Duration.between", Duration.between(runStart, runEnd)
                + "  toHours=" + Duration.between(runStart, runEnd).toHours());
        p("ChronoUnit.HOURS.between", ChronoUnit.HOURS.between(runStart, runEnd));
        p("ChronoUnit.DAYS.between", ChronoUnit.DAYS.between(runStart, runEnd)
                + "  <- no whole 24h elapsed, though the calendar date advanced");
        p("DAYS.between on LocalDates",
                ChronoUnit.DAYS.between(runStart.toLocalDate(), runEnd.toLocalDate()));
        p("Period.between on LocalDates",
                Period.between(runStart.toLocalDate(), runEnd.toLocalDate()));

        banner("8. plusDays is Period semantics, not Duration semantics");
        ZonedDateTime byPlusDays = runStart.plusDays(1);
        p("base", runStart);
        p("base.plusDays(1)", byPlusDays);
        p("base.plus(Period.ofDays(1))", runStart.plus(Period.ofDays(1)));
        p("base.plus(Duration.ofDays(1))", runStart.plus(Duration.ofDays(1)));
        p("plusDays == plus(Period)", byPlusDays.equals(runStart.plus(Period.ofDays(1))));
        p("plusDays == plus(Duration)", byPlusDays.equals(runStart.plus(Duration.ofDays(1))));

        banner("9. what java.util.Calendar does with the same gap label");
        TimeZone londonLegacy = TimeZone.getTimeZone("Europe/London");
        p("TimeZone id / useDaylightTime",
                londonLegacy.getID() + " / " + londonLegacy.useDaylightTime());
        Calendar cal = Calendar.getInstance(londonLegacy);
        cal.clear();
        cal.set(2026, Calendar.MARCH, 29, 1, 30, 0);
        p("isLenient", cal.isLenient());
        p("set(2026-03-29 01:30) millis", cal.getTimeInMillis());
        p("  read back HOUR:MINUTE", cal.get(Calendar.HOUR_OF_DAY) + ":" + cal.get(Calendar.MINUTE)
                + "  <- silently normalised, no signal");
        p("  as an Instant", cal.toInstant()
                + "  sameAsJavaTime=" + cal.toInstant().equals(gapResolved.toInstant()));
        cal.setLenient(false);
        cal.clear();
        cal.set(2026, Calendar.MARCH, 29, 1, 30, 0);
        try {
            p("non-lenient millis", cal.getTimeInMillis() + "  <- no complaint about the gap");
        } catch (IllegalArgumentException e) {
            p("non-lenient threw", e);
        }
        p("closest legacy probe", "TimeZone.inDaylightTime(Date) = "
                + londonLegacy.inDaylightTime(Date.from(gapResolved.toInstant())));
        p("TimeZone.setRawOffset exists", timeZoneHasSetRawOffset());
        Calendar settlementView = Calendar.getInstance(londonLegacy);
        settlementView.setTimeInMillis(gapResolved.toInstant().toEpochMilli());
        p("calendar HOUR_OF_DAY", settlementView.get(Calendar.HOUR_OF_DAY));
        settlementView.add(Calendar.HOUR_OF_DAY, 1);
        p("after in-place add(1h)", settlementView.get(Calendar.HOUR_OF_DAY)
                + "  <- the same object changed under any other holder");
    }
}
```

Compiled with `javac -d out DstHarness.java` and run with `java -cp out DstHarness`, under
`JAVA_HOME=/Library/Java/JavaVirtualMachines/jdk-21.jdk/Contents/Home`.

---

## 4. The real output

```console
=== 0. environment ===
java.version / vendor          21.0.7 / Oracle Corporation
tzdb versions, Europe/London   [2025a]
default zone                   Asia/Kolkata
next after 2026-01-01Z         Transition[Gap at 2026-03-29T01:00Z to +01:00]
next after that                Transition[Overlap at 2026-10-25T02:00+01:00 to Z]

=== 1. the spring gap: a label that maps to no instant ===
label under test               2026-03-29T01:30
getValidOffsets                []  (size=0)
getTransition                  Transition[Gap at 2026-03-29T01:00Z to +01:00]
  isGap / isOverlap            true / false
  getDuration                  PT1H
  label before / after         2026-03-29T01:00 / 2026-03-29T02:00
  offset before / after        Z / +01:00
ZonedDateTime.of(label,zone)   2026-03-29T02:30+01:00[Europe/London]  localDateTime=2026-03-29T02:30  instant=2026-03-29T01:30:00Z
label.atZone(zone)             2026-03-29T02:30+01:00[Europe/London]  equalToOf=true
ofStrict(label,Z)              java.time.DateTimeException
  message                      LocalDateTime '2026-03-29T01:30' does not exist in zone 'Europe/London' due to a gap in the local time-line, typically caused by daylight savings
ofStrict(label,+01:00)         java.time.DateTimeException
  message                      LocalDateTime '2026-03-29T01:30' does not exist in zone 'Europe/London' due to a gap in the local time-line, typically caused by daylight savings

=== 2. a PaymentRun window scheduled inside the gap ===
window 01:30 -> fires at 02:30 (offset +01:00, instant 2026-03-29T01:30:00Z)
window 07:30 -> fires at 07:30 (offset +01:00, instant 2026-03-29T06:30:00Z)
window 13:30 -> fires at 13:30 (offset +01:00, instant 2026-03-29T12:30:00Z)
window 19:30 -> fires at 19:30 (offset +01:00, instant 2026-03-29T18:30:00Z)

=== 3. the autumn overlap: a label that maps to two instants ===
label under test               2026-10-25T01:30
getValidOffsets                [+01:00, Z]  (size=2)
getTransition                  Transition[Overlap at 2026-10-25T02:00+01:00 to Z]
  isGap / isOverlap            false / true
  getDuration                  PT-1H
  label before / after         2026-10-25T02:00 / 2026-10-25T01:00
  offset before / after        +01:00 / Z
ZonedDateTime.of(label,zone)   2026-10-25T01:30+01:00[Europe/London]  localDateTime=2026-10-25T01:30  instant=2026-10-25T00:30:00Z
label.atZone(zone)             2026-10-25T01:30+01:00[Europe/London]  equalToOf=true
ofStrict(label,+01:00)         2026-10-25T01:30+01:00[Europe/London]  instant=2026-10-25T00:30:00Z
ofStrict(label,Z)              2026-10-25T01:30Z[Europe/London]  instant=2026-10-25T01:30:00Z
ofStrict(label,+02:00)         java.time.DateTimeException
  message                      ZoneOffset '+02:00' is not valid for LocalDateTime '2026-10-25T01:30' in zone 'Europe/London'
withEarlierOffsetAtOverlap     2026-10-25T01:30+01:00[Europe/London]  instant=2026-10-25T00:30:00Z
withLaterOffsetAtOverlap       2026-10-25T01:30Z[Europe/London]  instant=2026-10-25T01:30:00Z
same label / instants apart    true / PT1H
of() picked the earlier?       true

=== 4. the idempotency-key collision, and the fix ===
local key, 1st occurrence      IdempotencyKey[value=PaymentRun:2026-10-25T01:30]
local key, 2nd occurrence      IdempotencyKey[value=PaymentRun:2026-10-25T01:30]
keys equal, duplicate payout   true
instant key, 1st occurrence    IdempotencyKey[value=PaymentRun:1792888200]
instant key, 2nd occurrence    IdempotencyKey[value=PaymentRun:1792891800]
keys equal                     false

=== 5. Duration vs Period across the spring transition ===
start                          2026-03-28T19:30Z[Europe/London]  instant=2026-03-28T19:30:00Z
plus(Duration.ofDays(1))       2026-03-29T20:30+01:00[Europe/London]  instant=2026-03-29T19:30:00Z
plus(Period.ofDays(1))         2026-03-29T19:30+01:00[Europe/London]  instant=2026-03-29T18:30:00Z
labels differ by               PT-1H
elapsed Duration / Period      24h / 23h

=== 6. Duration vs Period across the autumn transition ===
start                          2026-10-24T19:30+01:00[Europe/London]  instant=2026-10-24T18:30:00Z
plus(Duration.ofDays(1))       2026-10-25T18:30Z[Europe/London]  instant=2026-10-25T18:30:00Z
plus(Period.ofDays(1))         2026-10-25T19:30Z[Europe/London]  instant=2026-10-25T19:30:00Z
labels differ by               PT1H
elapsed Duration / Period      24h / 25h

=== 7. Duration.between vs ChronoUnit across a transition ===
start / end                    2026-03-28T19:30Z[Europe/London]  ->  2026-03-29T19:00+01:00[Europe/London]
Duration.between               PT22H30M  toHours=22
ChronoUnit.HOURS.between       22
ChronoUnit.DAYS.between        0  <- no whole 24h elapsed, though the calendar date advanced
DAYS.between on LocalDates     1
Period.between on LocalDates   P1D

=== 8. plusDays is Period semantics, not Duration semantics ===
base                           2026-03-28T19:30Z[Europe/London]
base.plusDays(1)               2026-03-29T19:30+01:00[Europe/London]
base.plus(Period.ofDays(1))    2026-03-29T19:30+01:00[Europe/London]
base.plus(Duration.ofDays(1))  2026-03-29T20:30+01:00[Europe/London]
plusDays == plus(Period)       true
plusDays == plus(Duration)     false

=== 9. what java.util.Calendar does with the same gap label ===
TimeZone id / useDaylightTime  Europe/London / true
isLenient                      true
set(2026-03-29 01:30) millis   1774747800000
  read back HOUR:MINUTE        2:30  <- silently normalised, no signal
  as an Instant                2026-03-29T01:30:00Z  sameAsJavaTime=true
non-lenient threw              java.lang.IllegalArgumentException: HOUR_OF_DAY: 1 -> 2
closest legacy probe           TimeZone.inDaylightTime(Date) = true
TimeZone.setRawOffset exists   true
calendar HOUR_OF_DAY           2
after in-place add(1h)         3  <- the same object changed under any other holder
```

---

## 5. Reading the gap output

`getValidOffsets(2026-03-29T01:30)` returned `[]`. That empty list **is** the gap: the API is telling
you there is no offset under which this label denotes a real instant. It is the only non-throwing way
to detect a gap, and what every parser should consult before committing a human-supplied wall-clock
time to storage. `getTransition` then hands back the `ZoneOffsetTransition` that swallowed the label:
`getDuration()` is `PT1H`, the before-label is `01:00` (the last label that exists) and the after-label
`02:00` (the first past the hole). The missing labels are `[01:00, 02:00)` on 29 March 2026.

**`ZonedDateTime.of(label, zone)` does not throw.** It returned `2026-03-29T02:30+01:00`, and its own
`localDateTime` printed as `02:30` — **not the label that was passed in**. `of` pushed the result
forward by the gap's length and adopted the post-transition offset `+01:00`. `label.atZone(zone)` does
exactly the same thing; the harness proved it with `equalToOf=true`, so there is no "strict `atZone`"
hiding in the API.

`ofStrict` is the factory that refuses. With `Z` (the pre-transition offset) it threw
`java.time.DateTimeException`: `LocalDateTime '2026-03-29T01:30' does not exist in zone
'Europe/London' due to a gap in the local time-line, typically caused by daylight savings`. With
`+01:00` it threw the identical message — in a gap *no* offset is valid, so the offset argument is
irrelevant. Reach for `ofStrict` whenever a nonexistent label is a **data error** you want surfaced
rather than silently repaired: an operator typing a payout window, a client-submitted self-exclusion
end time, a batch file of wall-clock timestamps.

**The domain consequence.** Section 2 of the output makes it concrete. The banking partner's payout
file has **4 windows/day**, specified as UK wall-clock times. Give the `01:30` window a label inside
the gap and it does not run at `01:30` — it runs **once**, at the shifted instant, appearing as `02:30`
local; the other three windows are untouched. A `PaymentRun` scheduled by local wall-clock time moves
on exactly two days a year, and only for the windows near the transition.

> A gap is an interval of labels with no instants: `getValidOffsets` returns empty, `of` and
> `atZone` silently shift forward by the gap length, and only `ofStrict` refuses.

---

## 6. Reading the overlap output

`getValidOffsets(2026-10-25T01:30)` returned `[+01:00, Z]` — **two** offsets, earlier first. The label
is real twice. `ZonedDateTime.of(label, zone)` returned the `+01:00` version, and the harness confirmed
`of() picked the earlier? = true`. That is not luck; it is the documented rule — in an overlap `of`
takes the earlier offset, the **first** occurrence of the label.

| Call | `toString()` | `toInstant()` |
|---|---|---|
| `withEarlierOffsetAtOverlap()` | `2026-10-25T01:30+01:00[Europe/London]` | `2026-10-25T00:30:00Z` |
| `withLaterOffsetAtOverlap()` | `2026-10-25T01:30Z[Europe/London]` | `2026-10-25T01:30:00Z` |

Identical label, instants exactly `PT1H` apart — the harness printed both facts as `true / PT1H`. Two
different moments wearing the same name. Both methods are no-ops outside an overlap, returning `this`
rather than throwing, so they are safe to call unconditionally.

`ofStrict` with each of the two valid offsets **succeeded**, returning the two distinct instants — the
one case where `ofStrict` is not merely a validator but the only way to *express* which occurrence you
meant. With a third, wrong offset `+02:00` it threw `ZoneOffset '+02:00' is not valid for
LocalDateTime '2026-10-25T01:30' in zone 'Europe/London'`, a different message from the gap case and
useful in a log: "does not exist" means gap, "is not valid for" means the offset was not a candidate.
Meanwhile `isOverlap()` is true, `getDuration()` is **`PT-1H`** — negative, which is how
`ZoneOffsetTransition` encodes "the local timeline went backwards" — and the before-label (`02:00`) is
*after* the after-label (`01:00`) on the label timeline. Those names refer to the transition instant,
not to label ordering.

### The idempotency-key bug

QuizStakes has `IdempotencyKey(String value)`, and an hourly `PaymentRun` inside the overlap runs
**twice at the same label**:

```text
local key, 1st occurrence      IdempotencyKey[value=PaymentRun:2026-10-25T01:30]
local key, 2nd occurrence      IdempotencyKey[value=PaymentRun:2026-10-25T01:30]
keys equal, duplicate payout   true
```

Two genuinely distinct payout batches, one key. Whatever the key protects — the PSP payout call, the
`BANK_SETTLEMENT` movement, the file handed to the banking partner — the second run is either swallowed
as a replay (a **missed** payout) or, if the dedupe store already expired the entry, accepted as new (a
**duplicate** payout). Once a year, in the small hours, in a regulated product. Key on the instant:

```text
instant key, 1st occurrence    IdempotencyKey[value=PaymentRun:1792888200]
instant key, 2nd occurrence    IdempotencyKey[value=PaymentRun:1792891800]
keys equal                     false
```

`1792891800 - 1792888200 = 3600`, exactly the overlap hour. Any instant-derived form works —
`Instant.toString()`, the epoch second, epoch millis. What must not appear in a key is a
`LocalDateTime`, a `LocalDate` plus wall-clock hour, or a formatted local string.

**Interview:** "How would you make a nightly job idempotent?" The answer that lands is "key on the
instant the job fired, not the local timestamp — because in an autumn DST overlap the local
timestamp repeats and the key collides."

> An overlap is an interval of labels with two instants each: `getValidOffsets` returns two offsets,
> `of` takes the earlier, and any identity derived from the label collides between the two
> occurrences.

---

## 7. The `Duration`/`Period` divergence

One sentence each, and they are the whole mechanism. **`Duration`** is a fixed count of **seconds and
nanos** added on the **instant** timeline: the instant moves by exactly that much, and the local
label lands wherever the rules put it. **`Period`** is a count of **calendar units** added to the
**label**, with the result re-resolved against the rules: the label is preserved, and the elapsed
time comes out as whatever the calendar day happened to be worth.

The JDK 21 javadoc on `ZonedDateTime.plus(long, TemporalUnit)` states the split in exactly those
terms:

```text
Date units operate on the local time-line.
The period is first added to the local date-time, then converted back
to a zoned date-time using the zone ID.

Time units operate on the instant time-line.
```

Adding one day both ways, from a start before each 2026 transition:

| Start | Operation | Result | Elapsed |
|---|---|---|---|
| `2026-03-28T19:30Z` | `plus(Duration.ofDays(1))` | `2026-03-29T20:30+01:00` | 24h |
| `2026-03-28T19:30Z` | `plus(Period.ofDays(1))` | `2026-03-29T19:30+01:00` | **23h** |
| `2026-10-24T19:30+01:00` | `plus(Duration.ofDays(1))` | `2026-10-25T18:30Z` | 24h |
| `2026-10-24T19:30+01:00` | `plus(Period.ofDays(1))` | `2026-10-25T19:30Z` | **25h** |

In spring the `Duration` path kept 24 hours and the **label moved forward** from `19:30` to `20:30`, while
the `Period` path kept the **label** at `19:30` and the elapsed time collapsed to 23 hours, because 29
March 2026 in London is a 23-hour day. In autumn the numbers go the other way: the `Duration` label
slipped **back** to `18:30`, and the `Period` path held `19:30` at the cost of 25 hours.

**Insight:** neither answer is wrong. "One day later" is genuinely ambiguous, and `java.time` forces you
to say which one you meant by making them different types — which is why `TemporalAmount` has two
implementations rather than one.

### `Duration.between` vs `ChronoUnit`

The case people find hardest. Take a `PaymentRun` window on 28 March at `19:30` and the next on 29
March at `19:00`:

| Measurement | Value |
|---|---|
| `Duration.between(start, end)` | `PT22H30M`, `toHours()` = 22 |
| `ChronoUnit.HOURS.between(start, end)` | 22 |
| `ChronoUnit.DAYS.between(start, end)` | **0** |
| `ChronoUnit.DAYS.between(start.toLocalDate(), end.toLocalDate())` | **1** |
| `Period.between(start.toLocalDate(), end.toLocalDate())` | `P1D` |

`ChronoUnit.DAYS.between` on two `ZonedDateTime`s counts **complete 24-hour periods** and truncates
toward zero. Only 22h30m elapsed, so the answer is 0 — even though the calendar date plainly advanced
by one. Reduce both sides to `LocalDate` and the same unit returns 1, because now it counts calendar
days. The unit did not change; the operand type did, and that changed the timeline it counts on. So
`ChronoUnit.DAYS.between(zdtA, zdtB)` is not "how many dates did we cross" — for that, convert to
`LocalDate` first and say so.

### The API asymmetry worth memorising

`zdt.plusDays(1)` is **`Period` semantics**, not `Duration` semantics. The harness proved it —
`plusDays == plus(Period) = true`, `plusDays == plus(Duration) = false` — and the JDK 21 javadoc for
`ZonedDateTime.plusDays` confirms it directly:

```text
This operates on the local time-line, adding days to the local date-time.
This is then converted back to a ZonedDateTime, using the zone ID to obtain the offset.
When converting back to ZonedDateTime, if the local date-time is in an overlap,
then the offset will be retained if possible, otherwise the earlier offset will be used.
If in a gap, the local date-time will be adjusted forward by the length of the gap.
```

So `plusDays(1)` and `plus(Duration.ofDays(1))` are different operations with almost the same
spelling. The mnemonic: on `ZonedDateTime`, `plusDays` / `plusWeeks` / `plusMonths` / `plusYears` are
label arithmetic, `plusHours` / `plusMinutes` / `plusSeconds` / `plusNanos` are instant arithmetic,
and the boundary sits exactly between `plusDays` and `plusHours` — which is why "add 24 hours" and
"add a day" are not synonyms here.

### The three amount mechanisms, side by side

| | `Duration` | `Period` | `ChronoUnit.X.between` |
|---|---|---|---|
| Counts | seconds + nanos | years, months, days | one named unit, truncated toward zero |
| Timeline | instant | label, then re-resolved | instant for time units, label for date units — set by the **operand type** |
| Largest unit modelled | days, as 86,400s exactly | months and years, calendar-aware | whatever unit you name |
| DST behaviour | ignores transitions; label drifts | absorbs transitions; label held | follows the operand's timeline |
| At a gap | never lands in one; instant arithmetic cannot | result re-resolved: shifted forward by the gap length | measurement only, no resolution step |
| At an overlap | lands on a definite instant, offset unambiguous | offset retained if still valid, else the earlier one | measurement only |
| Reach for it when | timeouts, SLAs, retry backoff, "how long did this take" | "same time tomorrow", billing periods, 30-day bonus expiry | "how many whole X between these two" |

The **30 days from grant** bonus expiry is a `Period` question: a client granted a bonus at `19:30` should
see it expire at `19:30` thirty days later, which measured on this build means 719 elapsed hours across
the spring transition and 721 across the autumn one, not 720. The identity vendor's **30s timeout** is a
`Duration` question, and nonsense as a `Period` — `Period` has no sub-day units.

---

## 8. The rule this file exists to leave you with

**Store and compare instants. Use local date-times only at the boundary where a human specified one,
and re-resolve them against the rules every time.**

Everything above is a consequence. A `LocalDateTime` in a database column for an event timestamp is a
bug: it is a label, so it is ambiguous during an overlap, impossible during a gap, and unorderable
against rows written under a different offset. Guide 09 owns `TIMESTAMP WITH TIME ZONE`; guide 12 owns
ISO-8601 on the wire, and why offset-carrying `2026-10-25T01:30:00Z` is the only interchange form that
survives a round trip.

At the boundary, three habits cover almost everything. Read human input as a `LocalDateTime` plus an
explicit `ZoneId` and check `getValidOffsets(label)` — size 0 means reject, size 2 means ask which one,
size 1 means proceed. Persist and compare the resulting `Instant`, alongside the `ZoneId` if you will
ever re-render the label, and never the offset alone, since an offset is a snapshot of rules that
change. Derive identity — idempotency keys, dedupe hashes, natural keys — from the instant, never the
label.

For a fixed clock in tests, [`04f-clock-injection.md`](04f-clock-injection.md) owns `Clock` injection
and testable time, including the measured result that `Clock.systemUTC()` returns microsecond
precision on this build. Pin an injected `Clock` to the overlap hour rather than hacking a system
property.

---

## 9. Diff vs the real one

The build here is a harness, not a reimplementation of `java.time`, so the honest comparison is
`java.time` against the API it replaced — `java.util.Date` / `Calendar` / `TimeZone` — on the DST
question specifically. Section 9 of the output is the evidence.

| Axis | `java.util.Calendar` / `TimeZone` | `java.time` (`ZonedDateTime` / `ZoneRules`) |
|---|---|---|
| **Gap detectable?** | No equivalent of `getValidOffsets`. Lenient `set(2026, MARCH, 29, 1, 30, 0)` produced millis `1774747800000` and read back `HOUR:MINUTE = 2:30` — **silently normalised, no signal**. The closest probe is `TimeZone.inDaylightTime(Date)`, which answers a different question. | `getValidOffsets` returns an empty `List<ZoneOffset>`; `getTransition(label).isGap()` is true, with `getDuration()`, `getDateTimeBefore()` and `getDateTimeAfter()`. |
| **Overlap detectable?** | Not at all. A `Calendar` field set names one of the two instants and gives no way to ask for the other, or to learn another exists. | Two offsets from `getValidOffsets`; `withEarlierOffsetAtOverlap` / `withLaterOffsetAtOverlap` select between them; `isOverlap()` reports it. |
| **Lenient behaviour** | Lenient by default. `setLenient(false)` does complain, but about field normalisation, not DST: `IllegalArgumentException: HOUR_OF_DAY: 1 -> 2`. You cannot tell a gap from a typo'd hour. | No leniency switch. `of` / `atZone` always resolve; `ofStrict` always refuses, with messages distinguishing "does not exist" from "is not valid for". |
| **Edge cases** | Gap and overlap both resolve to *something*, chosen by `GregorianCalendar`'s internal rules and not stated in any signature. `add` and `roll` differ silently across a transition. | Gap and overlap are named concepts with API surface. `Duration` vs `Period` makes the ambiguous "one day" a compile-time choice. |
| **Mutability** | `Calendar` is mutable — the harness read `HOUR_OF_DAY = 2`, called `add(HOUR_OF_DAY, 1)` in place, and read `3` back from the same object. `TimeZone` is mutable too: `setRawOffset` exists (reflection said `true`), so a shared `TimeZone` can be retuned under every holder. | Immutable throughout. `plus`, `with*` and `truncatedTo` return new instances. See [`../immutability-and-design/02-immutability.md`](../immutability-and-design/02-immutability.md). |
| **Thread safety** | Not thread-safe. A shared `Calendar` corrupts under concurrent field access, and `SimpleDateFormat`'s internal `Calendar` is the classic case — order 31 (`05d-concurrency-and-time-harnesses.md`) demonstrates that race. | Thread-safe by immutability. `ZoneRules` instances are shared and safe; `DateTimeFormatter` is immutable and safe, which is the whole reason it replaced `SimpleDateFormat`. |
| **Null policy** | Mixed. `setTimeZone(null)` and friends fail late, often as an obscure NPE inside a normalisation path. | Uniform `Objects.requireNonNull` on every public factory parameter, failing at the call site with the parameter name. |
| **Serialization** | `Date` serializes as a `long`. `Calendar` serializes its whole mutable field array plus a `TimeZone` — large and version-fragile. | Compact custom `writeReplace` forms via `java.time.Ser`; `ZonedDateTime` writes date, time, offset and zone id. The tzdb is *not* serialized — the zone id is a late-bound reference, so a deserialized value re-resolves against the reading JVM's rules. |
| **Intrinsics** | None relevant. | None in the DST path either. `System.currentTimeMillis` / `nanoTime` under `Clock` are intrinsified; rule lookup is plain Java doing a binary search over transition arrays. |
| **Allocation tricks** | Cheap per operation because you mutate one object — but that mutation *is* the bug. | Every operation allocates. `ZonedDateTime` is three references (`LocalDateTime`, `ZoneOffset`, `ZoneId`); `ZoneOffset` instances are cached and interned by total seconds, and `ZoneRules` is shared per zone, so the per-call cost is the date-time object, not the rules. |
| **Why the JDK bothers** | — | Because "is this label a real moment, and how many moments is it" was **unanswerable** in the old API. Everything else — immutability, thread safety, the type-level `Duration`/`Period` split — falls out of taking that question seriously. JSR-310 did not make date handling prettier; it made a class of bug expressible and therefore checkable. |

---

## Pitfalls

### Believing `ZonedDateTime.of` throws on a nonexistent local date-time

**Wrong**

```java
LocalDateTime window = LocalDateTime.of(2026, 3, 29, 1, 30);
// "if this label is bogus I'll get an exception and can reject the PaymentRun"
ZonedDateTime fires = ZonedDateTime.of(window, ZoneId.of("Europe/London"));
System.out.println(fires);
```

```console
2026-03-29T02:30+01:00[Europe/London]
```

No exception. The object claims `02:30`, not the time anyone asked for, and the `PaymentRun` was
accepted with silently altered data.

**Right**

```java
ZoneId london = ZoneId.of("Europe/London");
LocalDateTime window = LocalDateTime.of(2026, 3, 29, 1, 30);
List<ZoneOffset> valid = london.getRules().getValidOffsets(window);
if (valid.isEmpty()) {
    throw new IllegalArgumentException("payout window " + window
            + " does not exist in " + london);
}
ZonedDateTime fires = ZonedDateTime.ofStrict(window, valid.get(0), london);
```

**Why people believe it:** every other `java.time` factory validates aggressively — `LocalDate.of(2026,
2, 30)` throws, `LocalTime.of(25, 0)` throws — so `of` reads like a validating constructor. It is, for
its arguments; the gap is a property of the *zone*, and `of` is documented to resolve rather than
reject, with `ofStrict` as the opt-in strict form.

### Believing `plusDays(1)` and `plus(Duration.ofDays(1))` are the same

**Wrong**

```java
ZonedDateTime base = ZonedDateTime.of(
        LocalDateTime.of(2026, 3, 28, 19, 30), ZoneId.of("Europe/London"));
// "same thing, one is just more explicit"
System.out.println(base.plusDays(1));
System.out.println(base.plus(Duration.ofDays(1)));
```

```console
2026-03-29T19:30+01:00[Europe/London]
2026-03-29T20:30+01:00[Europe/London]
```

An hour apart. If those two spellings appear in the scheduler and in the "did the previous window
already run" check, they disagree once a year and a payout window either doubles or vanishes.

**Right**

```java
// "same wall-clock time tomorrow" -> calendar arithmetic
ZonedDateTime nextWindow = base.plusDays(1);              // or base.plus(Period.ofDays(1))
// "exactly 24 hours of elapsed time later" -> instant arithmetic
ZonedDateTime deadline = base.plus(Duration.ofDays(1));   // or base.plusHours(24)
```

Pick by intent and say which in the variable name; on `ZonedDateTime` the line is drawn between
`plusDays` (label) and `plusHours` (instant).

**Why people believe it:** `Duration.ofDays(1)` reads as "one day", and for 363 days a year the two
agree, so tests written on an arbitrary date pass. The JDK 21 javadoc for `Duration.ofDays` says no more
than it does: it "obtains a `Duration` representing a number of standard 24 hour days", where "each day
is 86400 seconds which implies a 24 hour day". No calendar is consulted, so no transition is absorbed.

### Building an idempotency key from a local date-time

**Wrong**

```java
record IdempotencyKey(String value) { }

IdempotencyKey keyFor(String runName, LocalDateTime firedAt) {
    return new IdempotencyKey(runName + ":" + firedAt);
}
```

```console
local key, 1st occurrence      IdempotencyKey[value=PaymentRun:2026-10-25T01:30]
local key, 2nd occurrence      IdempotencyKey[value=PaymentRun:2026-10-25T01:30]
keys equal, duplicate payout   true
```

Two distinct payout batches, one key — same failure mode as a `UNIQUE` constraint on a
`LocalDateTime` column, or a `Map<LocalDateTime, PaymentRun>`.

**Right**

```java
IdempotencyKey keyFor(String runName, ZonedDateTime firedAt) {
    return new IdempotencyKey(runName + ":" + firedAt.toInstant().getEpochSecond());
}
```

```console
instant key, 1st occurrence    IdempotencyKey[value=PaymentRun:1792888200]
instant key, 2nd occurrence    IdempotencyKey[value=PaymentRun:1792891800]
keys equal                     false
```

**Why people believe it:** the local timestamp is what appears in the operator UI and the log line,
so it feels like the run's natural identity. It is the run's *presentation*, and presentation is not
identity — the label repeats for one hour a year, exactly long enough to cover a scheduled window.

### Believing the JDK's tzdb is fixed for a given Java version

**Wrong**

```java
// "21 ships tzdb 2025a, so I can hard-code the transition and skip the rules lookup"
LocalDateTime springForward2027 = LocalDateTime.of(2027, 3, 28, 1, 0);
```

The harness printed `tzdb versions, Europe/London   [2025a]` on **21.0.7**. A colleague on a later
21.0.x patch may hold a different tzdb release, and a jurisdiction that abolishes DST — several have
legislated toward it — changes future transitions without changing the Java version number. The
hard-coded date silently becomes wrong for future dates only, so nothing fails until it matters.

**Right**

```java
ZoneRules rules = ZoneId.of("Europe/London").getRules();
ZoneOffsetTransition next = rules.nextTransition(Instant.now());
// and, for the record, log what you resolved against:
String tzdb = ZoneRulesProvider.getVersions("Europe/London").lastKey();
```

Ask the rules, and log the tzdb version alongside any stored future-dated schedule.

**Why people believe it:** "Java version" and "library data" feel like one thing because they ship in
one download. The tzdb is *data*, refreshed into `$JAVA_HOME/lib/tzdb.dat` on patch releases, and the
future half of it is a forecast.

---

## Cheat sheet

| Question | Call | Gap answer | Overlap answer |
|---|---|---|---|
| Is this label real? | `rules.getValidOffsets(local)` | `[]`, size 0 | two offsets, earlier first |
| Which transition? | `rules.getTransition(local)` | `isGap() == true` | `isOverlap() == true` |
| How wide? | `transition.getDuration()` | `PT1H` | `PT-1H`, negative |
| Resolve leniently | `ZonedDateTime.of(local, zone)`, `local.atZone(zone)` | shifts forward by gap length | picks the **earlier** offset |
| Resolve strictly | `ZonedDateTime.ofStrict(local, offset, zone)` | throws for **any** offset | succeeds for either valid offset |
| Pick the occurrence | `withEarlierOffsetAtOverlap()` / `withLaterOffsetAtOverlap()` | no-op | selects; instants 1h apart |
| Add elapsed time | `plus(Duration)`, `plusHours` | instant timeline, label drifts | same |
| Add calendar time | `plus(Period)`, `plusDays` | label held, re-resolved forward | label held, offset retained if valid |
| Elapsed between two | `Duration.between(a, b)` | real elapsed: 23h or 25h day | same |
| Whole units between two | `ChronoUnit.X.between(a, b)` | truncates; `DAYS` needs a full 24h | same |
| tzdb version | `ZoneRulesProvider.getVersions(id)` | `[2025a]` on JDK 21.0.7 | same |

Storage rule: **instant + zone id**. Never a `LocalDateTime` for an event, never a bare offset for a
future schedule.

---

## Self-test

**Q1.** `ZonedDateTime.of(LocalDateTime.of(2026, 3, 29, 1, 30), ZoneId.of("Europe/London"))` — what
does it return and what does it throw?

<details><summary>Answer</summary>

It returns `2026-03-29T02:30+01:00[Europe/London]` and throws nothing. `01:30` is inside the spring gap,
which on tzdb 2025a covers labels `[01:00, 02:00)` on 29 March 2026. `of` is documented to resolve a gap
by moving the local date-time **forward by the length of the gap** and adopting the post-transition
offset, so the returned object's local date-time is `02:30` — not the label you passed — and its instant
is `2026-03-29T01:30:00Z`. `atZone` behaves identically. The factory that throws is `ofStrict`, reporting
`LocalDateTime '2026-03-29T01:30' does not exist in zone 'Europe/London' due to a gap in the local
time-line, typically caused by daylight savings`, and it throws for *any* offset argument.

</details>

**Q2.** How do you detect a gap and an overlap without catching an exception?

<details><summary>Answer</summary>

`zone.getRules().getValidOffsets(localDateTime)`. Size 0 means gap, size 1 the normal case, size 2
overlap — and in the overlap case the list is ordered earlier-offset first, so `get(0)` is the first
occurrence and `get(1)` the second. For the transition itself, `rules.getTransition(localDateTime)`
returns a `ZoneOffsetTransition` (or `null` outside a transition) with `isGap()`, `isOverlap()`,
`getDuration()`, `getDateTimeBefore()` and `getDateTimeAfter()`. Measured on JDK 21.0.7 for
`Europe/London`: `getValidOffsets` returned `[]` for `2026-03-29T01:30` and `[+01:00, Z]` for
`2026-10-25T01:30`.

</details>

**Q3.** Why is `zdt.plusDays(1)` not the same as `zdt.plus(Duration.ofDays(1))`?

<details><summary>Answer</summary>

`plusDays` is date-unit arithmetic, so per the JDK 21 javadoc it "operates on the local time-line":
the day is added to the `LocalDateTime`, then the result is re-resolved against the zone rules.
`plus(Duration.ofDays(1))` is time-unit arithmetic — `Duration.ofDays(1)` is exactly 86,400 seconds
— so it operates on the instant timeline. Away from a transition both agree. Across the 2026 spring
transition, starting from `2026-03-28T19:30Z`, `plusDays(1)` gives `2026-03-29T19:30+01:00` (label
held, 23 hours elapsed) and `plus(Duration.ofDays(1))` gives `2026-03-29T20:30+01:00` (24 hours
elapsed, label drifted). `plusDays(1)` equals `plus(Period.ofDays(1))`, which the harness confirmed
as `true`. The boundary on `ZonedDateTime` sits between `plusDays` and `plusHours`.

</details>

**Q4.** An hourly settlement job writes a row keyed on its local firing time. What breaks, when, and
how do you fix it?

<details><summary>Answer</summary>

On the autumn transition night the job runs twice at the same label — `2026-10-25T01:30` occurs at
`00:30Z` and again at `01:30Z`, one hour apart. Every identity derived from the label collides: an
`IdempotencyKey(String value)` built from it, a `UNIQUE` index on a `LocalDateTime` column, a
`Map<LocalDateTime, PaymentRun>`. The second run is either rejected as a replay, losing a payout, or
accepted as new if the dedupe window has expired, duplicating one. The fix is to derive identity from
the instant: `firedAt.toInstant().getEpochSecond()` gave `1792888200` and `1792891800` for the two
occurrences, differing by exactly 3600. Store the instant; render the label only for display.

</details>

**Q5.** What did `java.util.Calendar` do with the gap label, and why is that the argument for
`java.time`?

<details><summary>Answer</summary>

Lenient `Calendar.set(2026, MARCH, 29, 1, 30, 0)` in `Europe/London` produced millis `1774747800000` and
read back `HOUR:MINUTE = 2:30` — the same instant `java.time` resolves to, but with **no signal** that
anything was adjusted. `setLenient(false)` did throw, but as `IllegalArgumentException: HOUR_OF_DAY: 1
-> 2`, a field-normalisation complaint indistinguishable from a typo'd hour. There is no
`getValidOffsets` equivalent and no way to learn that an overlap label has a second occurrence. That is
the argument: "is this label a real moment, and how many moments is it" was unanswerable in the old API.
Immutability and thread safety matter too — the harness mutated a `Calendar` in place from hour 2 to
hour 3, and `TimeZone` still exposes `setRawOffset` — but the DST question could not be worked around.

</details>

---

## Open questions

- none

---

Part 4 set out to build the mechanisms rather than describe them, and it did: thirty-odd from-scratch
types and diagnostic harnesses — `MyString` and its intern pool, `MyStringBuilder`'s growth arithmetic,
`MyInteger`'s cache, generic containers and super type tokens, five enum patterns, the exception and
`AutoCloseable` machinery, `Money` two ways, and ten harnesses that each print a behaviour the language
does not advertise — every one compiled and run on a real JDK 21.0.7 with the actual output pasted
rather than predicted. The recurring lesson is the one this file ends on: the mechanism is never quite
what the folklore says it is. `of` does not throw on a gap, `plusDays` is not `plus(Duration.ofDays(1))`,
the tzdb is not pinned to a Java version — and the only reliable way to find out is to run it. For the
same material in question form, see [`../93-interview-build-it.md`](../93-interview-build-it.md).

---

**Leaves covered:** 4.8.10 (1 leaf)
**Leaves deferred:** none
**Diagrams included:** none
**Target version:** Java 21 LTS
**Lines:** 900
