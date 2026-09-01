# 03 Java Core — Value-object builds — `Clock` injection and testable time — BUILD IT (§4.7.7)

**Target version: Java 21 LTS.** | **Part 4 of 5** | [Index](../00-index.md)
Previous: [A deep-copy utility for a nested object graph](04b-deep-copy-and-clock-injection.md) · Next: [The §4.7 diff against what a record gives you](04d-value-object-diff.md)

One build, written twice: a `BonusExpiryService` whose 30-day boundary can be tested exactly
because its clock is a constructor parameter, and the same service with `Instant.now()` welded into
the method body, which cannot. It is a `[BUILD]` item, so it closes with its own **Diff vs the real
one** table. The other §4.7 build, the deep-copy utility, is
[A deep-copy utility for a nested object graph](04b-deep-copy-and-clock-injection.md); the
section-wide §4.7 diff against what a `record` gives you for free is
[The §4.7 diff against what a record gives you](04d-value-object-diff.md).

Everything below compiled and ran on **Oracle JDK 21.0.7 (build 21.0.7+8-LTS-245), macOS aarch64
(Apple silicon)**, compressed oops on.

---

## 4.7.7 `Clock`-injected `BonusExpiryService` `[X-REF 16]`

The leaf's generic `InvoiceService` instantiated in this domain is a **`BonusExpiryService`**,
because the bonus rules are the domain's explicitly time-dependent ones: a bonus **expires 30 days
from grant** and the unspent part **reverses to `PROMOTIONAL_EXPENSE`**; the coupon is **valid 14
days from registration**. Two windows, two exact boundaries, real behaviour to test.

```java
public final class Bonus {
    final String bonusId;
    final long grantedUnits;          // minor units, 10% of first deposit capped at 100.00
    final Instant grantedAt;
    String status;                    // GRANTED, ACTIVE, CONSUMED, EXPIRED, CLAWED_BACK
    long unspentUnits;

    Bonus(String bonusId, long grantedUnits, Instant grantedAt) {
        this.bonusId = bonusId;
        this.grantedUnits = grantedUnits;
        this.grantedAt = grantedAt;
        this.status = "ACTIVE";
        this.unspentUnits = grantedUnits;
    }

    @Override public String toString() {
        return "Bonus[" + bonusId + " granted=" + grantedUnits + " unspent=" + unspentUnits
                + " status=" + status + "]";
    }
}

/** Minimal double-entry sink: enough to assert what was posted. */
public final class FundsLedger {
    final List<String> postings = new ArrayList<>();

    void post(String position, long units, String reference) {
        postings.add(position + " " + units + " " + reference);
    }

    @Override public String toString() { return postings.toString(); }
}
```

### First, the untestable version

```java
/** The version you cannot test: the clock read is welded into the method body. */
public final class BonusExpiryServiceUntestable {

    static final int EXPIRY_DAYS = 30;
    static final int COUPON_VALIDITY_DAYS = 14;

    private final FundsLedger ledger;

    BonusExpiryServiceUntestable(FundsLedger ledger) { this.ledger = ledger; }

    /** Expires the bonus if it is 30 days past grant, reversing the unspent part. */
    public boolean expireIfDue(Bonus bonus) {
        Instant expiresAt = bonus.grantedAt.plus(EXPIRY_DAYS, ChronoUnit.DAYS);
        if (Instant.now().isBefore(expiresAt)) return false;
        ledger.post("PROMOTIONAL_EXPENSE", bonus.unspentUnits, bonus.bonusId);
        bonus.status = "EXPIRED";
        bonus.unspentUnits = 0;
        return true;
    }

    public boolean isCouponValid(Instant registeredAt) {
        return Instant.now().isBefore(registeredAt.plus(COUPON_VALIDITY_DAYS, ChronoUnit.DAYS));
    }
}
```

Rather than assert this is untestable, write the best test it admits and watch it fail. The one
lever available is `grantedAt`: back-date the grant so the boundary sits one nanosecond in the
future, then assert the bonus has *not* expired.

```java
/** The best test you can write against Instant.now(), and why it fails. */
public final class UntestableBoundaryAttempt {
    public static void main(String[] args) {
        FundsLedger ledger = new FundsLedger();
        var service = new BonusExpiryServiceUntestable(ledger);

        Instant grantedAt = Instant.now().minus(30, ChronoUnit.DAYS).plusNanos(1);
        Bonus bonus = new Bonus("BON-7741", 4200, grantedAt);
        boolean expired = service.expireIfDue(bonus);
        System.out.println("expected expired=false, got expired=" + expired);
        System.out.println("  " + bonus + " ledger=" + ledger);

        Instant readInTest = Instant.now();
        Instant readInService = Instant.now();
        System.out.println("two consecutive Instant.now() reads differ by "
                + java.time.Duration.between(readInTest, readInService).toNanos() + " ns");
    }
}
```

```console
expected expired=false, got expired=true
  Bonus[BON-7741 granted=4200 unspent=0 status=EXPIRED] ledger=[PROMOTIONAL_EXPENSE 4200 BON-7741]
two consecutive Instant.now() reads differ by 2000 ns
```

The test is wrong and the code is right, and from inside the test the two are indistinguishable.
The service's clock read happens *after* the test's — 2,000 ns later on this run — so the
one-nanosecond margin is gone before the comparison executes. What remains is: wait 30 days; change
the machine's system clock, which breaks every other test on the box and is not available under a
CI runner; or mock the static.

**What mocking the static costs.** `Instant.now()` is `static`, so plain Mockito cannot touch it:
you need `mockito-inline` behaviour (the default from Mockito 5) and
`Mockito.mockStatic(Instant.class)`, which installs a byte-code-level interception for that class
for as long as the returned `MockedStatic` is open — hence a `try`-with-resources scope, and no
parallel test on the same class. You are mocking a JDK type used by everything on the thread, so
the interception also catches `Instant.now()` calls inside collaborators you did not mean to stub;
and the test breaks when the call site moves — refactor `expireIfDue` to delegate to a helper that
calls `Clock.systemUTC().instant()` and the mock stubs a method nobody calls while the test still
passes, for the wrong reason. Guide 16 owns Mockito and `mockStatic`.

### Then the injected version

```java
/** The testable version: the clock is a constructor parameter like any other collaborator. */
public final class BonusExpiryService {

    static final int EXPIRY_DAYS = 30;
    static final int COUPON_VALIDITY_DAYS = 14;

    private final FundsLedger ledger;
    private final Clock clock;

    BonusExpiryService(FundsLedger ledger, Clock clock) {
        this.ledger = ledger;
        this.clock = clock;
    }

    /** Production wiring. */
    static BonusExpiryService production(FundsLedger ledger) {
        return new BonusExpiryService(ledger, Clock.systemUTC());
    }

    public boolean expireIfDue(Bonus bonus) {
        Instant expiresAt = bonus.grantedAt.plus(EXPIRY_DAYS, ChronoUnit.DAYS);
        Instant now = clock.instant();
        if (now.isBefore(expiresAt)) return false;     // expired iff now >= expiresAt
        ledger.post("PROMOTIONAL_EXPENSE", bonus.unspentUnits, bonus.bonusId);
        bonus.status = "EXPIRED";
        bonus.unspentUnits = 0;
        return true;
    }

    public boolean isCouponValid(Instant registeredAt) {
        return clock.instant().isBefore(registeredAt.plus(COUPON_VALIDITY_DAYS, ChronoUnit.DAYS));
    }
}
```

**Which comparison, and why it matters.** The guard is `now.isBefore(expiresAt)` meaning "not yet
expired", so expiry is `!now.isBefore(expiresAt)`, that is `now >= expiresAt`: the boundary instant
itself is expired. `now.isAfter(expiresAt)` would leave the boundary instant *unexpired*, keeping
the bonus alive for one extra nanosecond — one extra millisecond once the value passes through a
`TIMESTAMP(3)` column, one extra **day** if the comparison is made on `LocalDate`. `isBefore`,
`isAfter` and `!isBefore` are three different boundary policies and the choice must be deliberate.
The default to reach for: **half-open windows**, `[grantedAt, grantedAt + 30d)`, because half-open
intervals tile with no overlap and no gap.

The test is a plain `main` with `assert`, run with `-ea`; JUnit is not on this classpath.

```java
/** Plain main plus assert statements: no JUnit on the classpath. Run with -ea. */
public final class BonusExpiryServiceTest {

    static final Instant GRANTED_AT = Instant.parse("2026-08-29T09:15:30Z");
    static final Instant EXPIRES_AT = GRANTED_AT.plus(30, ChronoUnit.DAYS);

    static BonusExpiryService at(Instant now, FundsLedger ledger) {
        return new BonusExpiryService(ledger, Clock.fixed(now, ZoneOffset.UTC));
    }

    static void oneNanoBeforeExpiry() {
        FundsLedger ledger = new FundsLedger();
        Bonus bonus = new Bonus("BON-7741", 4200, GRANTED_AT);
        boolean expired = at(EXPIRES_AT.minusNanos(1), ledger).expireIfDue(bonus);
        System.out.println("one nanosecond before " + EXPIRES_AT + ": expired=" + expired
                + " " + bonus + " ledger=" + ledger);
        assert !expired : "must not expire before the boundary";
        assert bonus.status.equals("ACTIVE");
        assert ledger.postings.isEmpty();
    }

    static void exactlyAtExpiry() {
        FundsLedger ledger = new FundsLedger();
        Bonus bonus = new Bonus("BON-7741", 4200, GRANTED_AT);
        boolean expired = at(EXPIRES_AT, ledger).expireIfDue(bonus);
        System.out.println("exactly at            " + EXPIRES_AT + ": expired=" + expired
                + " " + bonus + " ledger=" + ledger);
        assert expired : "must expire at the boundary";
        assert bonus.status.equals("EXPIRED");
        assert ledger.postings.equals(java.util.List.of("PROMOTIONAL_EXPENSE 4200 BON-7741"));
    }

    static void couponBoundary() {
        Instant registeredAt = Instant.parse("2026-08-01T00:00:00Z");
        Instant couponEnds = registeredAt.plus(14, ChronoUnit.DAYS);
        FundsLedger ledger = new FundsLedger();
        boolean lastNano = at(couponEnds.minusNanos(1), ledger).isCouponValid(registeredAt);
        boolean onTheDot = at(couponEnds, ledger).isCouponValid(registeredAt);
        System.out.println("coupon valid one nanosecond before " + couponEnds + ": " + lastNano);
        System.out.println("coupon valid exactly at            " + couponEnds + ": " + onTheDot);
        assert lastNano;
        assert !onTheDot;
    }

    public static void main(String[] args) {
        boolean assertionsOn = false;
        assert assertionsOn = true;
        System.out.println("assertions enabled: " + assertionsOn);
        oneNanoBeforeExpiry();
        exactlyAtExpiry();
        couponBoundary();
        System.out.println("3 tests passed");
    }
}
```

`java -ea BonusExpiryServiceTest`:

```console
assertions enabled: true
one nanosecond before 2026-09-28T09:15:30Z: expired=false Bonus[BON-7741 granted=4200 unspent=4200 status=ACTIVE] ledger=[]
exactly at            2026-09-28T09:15:30Z: expired=true Bonus[BON-7741 granted=4200 unspent=0 status=EXPIRED] ledger=[PROMOTIONAL_EXPENSE 4200 BON-7741]
coupon valid one nanosecond before 2026-08-15T00:00:00Z: true
coupon valid exactly at            2026-08-15T00:00:00Z: false
3 tests passed
```

The first two lines are the whole argument for the technique: one nanosecond apart, deterministic,
in under a millisecond, with the ledger assertion proving the reversal posted to
`PROMOTIONAL_EXPENSE` exactly once and only on the expired side. `assert assertionsOn = true` is
there because a `main`-based test passes silently with assertions off; the printed
`assertions enabled: true` is the guard against a green run that tested nothing.

### `Clock`'s implementations

| Factory | Returns | For | Trap |
|---|---|---|---|
| `Clock.systemUTC()` | system clock, UTC zone | production default; UTC keeps `Instant` arithmetic zone-free | precision is platform-dependent, see below |
| `Clock.systemDefaultZone()` | system clock, `ZoneId.systemDefault()` | rarely what a service wants | the zone comes from the deployment host, so identical code behaves differently in two regions |
| `Clock.fixed(instant, zone)` | a clock frozen at one instant | boundary tests; every read is identical | freezes time, so code measuring a *duration* between two reads sees zero |
| `Clock.offset(base, duration)` | `base` shifted by a fixed `Duration` | "30 days later" against a live clock; a skewed peer | the offset is fixed, not a rate: it does not model drift |
| `Clock.tick(base, tickDuration)` | `base` truncated down to a multiple of the tick | reproducing a coarse upstream or storage precision | truncation is toward the past, so a tick clock can read *before* an event that already happened |
| `Clock.tickSeconds(zone)`, `Clock.tickMinutes(zone)` | `tick` at 1-second and 1-minute granularity | asserting on whole-second or whole-minute timestamps | a test written against `tickMinutes` tolerates up to 59 seconds of wrongness |

Measured on this build:

```console
java.version = 21.0.7
systemUTC().instant() = 2026-08-29T13:54:03.377669Z  nano=377669000  nano%1000=0  nano%1000000=669000
systemUTC().instant() = 2026-08-29T13:54:03.386566Z  nano=386566000  nano%1000=0  nano%1000000=566000
systemUTC().instant() = 2026-08-29T13:54:03.386613Z  nano=386613000  nano%1000=0  nano%1000000=613000
tickMinutes().instant() = 2026-08-29T13:54:00Z
offset(fixed, +30d)     = 2026-09-28T09:15:30Z
```

**The precision trap, verified rather than repeated.** `nano % 1000 == 0` on every read and
`nano % 1000000 != 0` on every read: JDK 21.0.7 here returns **microsecond** precision — three
non-zero digits past the millisecond, none past the microsecond. On Java 8 `Clock.systemUTC()` was
millisecond precision, backed by `System.currentTimeMillis()`; JDK 9 moved it to the best precision
the operating system offers, which is microseconds on Linux and macOS. So a test asserting
`instant.getNano() % 1_000_000 == 0`, or comparing a value round-tripped through a
millisecond-precision column against a fresh `Clock.systemUTC()` read, **passes on 8 and fails on
21**. The JDK 21 javadoc for `Clock.systemUTC()` states the precision is not fixed and may be
finer than milliseconds; the three reads above are the confirmation on this build. Storage
precision and truncation policy belong to
[`../date-and-time/02e-clock-precision-and-storage.md`](../date-and-time/02e-clock-precision-and-storage.md),
which owns `Clock` and precision as a subject.

**The honest limit.** Injecting a `Clock` makes *your* code's time readable and nothing else's. A
database `DEFAULT CURRENT_TIMESTAMP`, a JPA `@CreationTimestamp`, a Kafka record's broker
timestamp, an HTTP `Date` header, a JWT `exp` validated by a library's internal clock, a cache TTL
inside a client — every one reads a clock you did not inject and cannot fix. The technique buys
deterministic *domain* logic, which is where the 30-day and 14-day rules live, and nothing at the
edges. Push time-dependent decisions inward, out of the infrastructure that will not take a
`Clock`.

### Diff vs the real one

| Axis | This build (the injection pattern) | The real `java.time.Clock` |
|---|---|---|
| Edge cases | `Clock.fixed` removes elapsed time, so nothing here exercises drift or a clock stepping backwards | `Clock` is documented as possibly non-monotonic: `instant()` can go backwards across an NTP step, which is why elapsed time must use `System.nanoTime()` |
| Intrinsics | none | `System.currentTimeMillis()` and `System.nanoTime()` underneath are `@IntrinsicCandidate` and compile to a VM-level time read; `Clock.systemUTC().instant()` adds a virtual call and an `Instant` allocation |
| Serialization | `Bonus` carries an `Instant`, which serializes in a compact epoch-seconds-plus-nanos form | `SystemClock`, `FixedClock`, `OffsetClock` and `TickClock` are `Serializable`; the abstract `Clock` is not, so a `Clock` field in a serializable service must be `transient` |
| Null policy | this build takes the `Clock` with no null check; production passes `Clock.systemUTC()` | every `Clock` factory throws `NullPointerException` on a null zone or base clock; `Objects.requireNonNull(clock)` is the version to ship |
| Thread safety | one `Clock` in a `final` field, never mutated, safe to share | all JDK `Clock` implementations are immutable and thread-safe by specification, and subclasses are required to be |
| Allocation tricks | none; one `Instant` per `expireIfDue` call | `Clock.fixed` returns a stored `Instant` with zero allocation per read; `SystemClock.instant()` allocates one `Instant` per call, which is why hot loops read `currentTimeMillis()` directly |
| Why the JDK bothers | this is the entire reason `Clock` is a type rather than a static method | `Clock` shipped with `java.time` in Java 8 **as** the injection seam JSR-310 was asked for; every `java.time` type has a `now(Clock)` overload for it, and `LocalDate.now(clock)` is the one to use when the rule is in days rather than instants |

---

## Pitfalls

### Calling `Instant.now()` inside domain logic

**Wrong**

```java
public boolean expireIfDue(Bonus bonus) {
    Instant expiresAt = bonus.grantedAt.plus(30, ChronoUnit.DAYS);
    if (Instant.now().isBefore(expiresAt)) return false;
    ledger.post("PROMOTIONAL_EXPENSE", bonus.unspentUnits, bonus.bonusId);
    return true;
}
```

```console
expected expired=false, got expired=true
two consecutive Instant.now() reads differ by 2000 ns
```

**Right**

```java
public boolean expireIfDue(Bonus bonus) {
    Instant expiresAt = bonus.grantedAt.plus(EXPIRY_DAYS, ChronoUnit.DAYS);
    if (clock.instant().isBefore(expiresAt)) return false;
    ledger.post("PROMOTIONAL_EXPENSE", bonus.unspentUnits, bonus.bonusId);
    bonus.status = "EXPIRED";
    bonus.unspentUnits = 0;
    return true;
}
```

```console
one nanosecond before 2026-09-28T09:15:30Z: expired=false
exactly at            2026-09-28T09:15:30Z: expired=true
```

**Why people believe it:** `Instant.now()` reads as the obvious way to ask the time, and a `Clock`
parameter looks like ceremony for the tests' benefit. The clock is an input to the decision in the
same sense the ledger is; hard-coding it is the same mistake as `new FundsLedger()` inside the
method, and it only looks different because time feels ambient.
### Asserting on `Clock.systemUTC()`'s precision

**Wrong**

```java
Instant live = Clock.systemUTC().instant();
assert live.getNano() % 1_000_000 == 0
        : "expected millisecond precision, nano=" + live.getNano();
```

```console
Clock.systemUTC().instant() = 2026-08-29T14:23:19.791147Z
millisecond-precision assertion FAILED: expected millisecond precision, nano=791147000
```

The same assertion passed on Java 8, where `Clock.systemUTC()` was millisecond precision backed by
`System.currentTimeMillis()`. On this JDK 21.0.7 it reads microseconds — `791147000` nanoseconds is
`791147` microseconds — so the test fails on 21 having passed for years on 8.

**Right**

```java
Instant fixed = Clock.fixed(Instant.parse("2026-09-28T09:15:30Z"), ZoneOffset.UTC).instant();
Instant truncated = live.truncatedTo(ChronoUnit.MILLIS);
```

```console
Clock.fixed at 2026-09-28T09:15:30Z = 2026-09-28T09:15:30Z nano=0
live.truncatedTo(MILLIS) = 2026-08-29T14:23:19.791Z nano=791000000 nano%1000000=0
```

Assert against an injected `Clock.fixed`, whose precision you chose, or truncate explicitly to the
precision your storage actually has. Never assert on the platform's.

**Why people believe it:** every Java 8 tutorial, and a great deal of production code written
against it, treats "the current time" and "milliseconds since the epoch" as the same thing, because
for a decade they were. JDK 9 changed `Clock.systemUTC()` to the best precision the operating
system offers, and the change is invisible until a test compares a truncated value with a live
read.

### Choosing the wrong comparison at the boundary

**Wrong**

```java
static boolean expiredByIsAfter(Instant now) {
    return now.isAfter(EXPIRES_AT);
}
```

```console
now == expiresAt == 2026-09-28T09:15:30Z
  now.isAfter(expiresAt)    -> expired=false
  !now.isBefore(expiresAt)  -> expired=true
same instant truncated to days: 2026-09-28T00:00:00Z -> isAfter says expired=false, window lost 9 hours
```

**Right**

```java
static boolean expiredByNotIsBefore(Instant now) {
    return !now.isBefore(EXPIRES_AT);
}
```

The bonus is expired at the boundary instant itself, so the active window is half-open,
`[grantedAt, grantedAt + 30d)`, and consecutive windows tile with no overlap and no gap.

**Why people believe it:** "expired means the expiry time has passed" reads as strictly after, and
`isAfter` is the method whose name matches that sentence. The cost is invisible at nanosecond
precision and grows with every truncation the value passes through — the last line of that output
is the same instant truncated to days, where `isAfter` keeps a 30-day promotional liability alive
for another 9 hours, and at 3.1k bonus grants a day averaging 42 that is a real number.

---

## Cheat sheet

| Thing | Answer |
|---|---|
| Testable time | `Clock` constructor parameter, `clock.instant()` at the call site |
| Production wiring | `Clock.systemUTC()` — UTC keeps `Instant` arithmetic zone-free |
| Test wiring | `Clock.fixed(Instant.parse("2026-09-28T09:15:30Z"), ZoneOffset.UTC)` |
| Why `Instant.now()` is untestable | the test's clock read and the service's are microseconds apart, so an exact boundary cannot be hit |
| Measured gap between two `Instant.now()` reads | 2,000 ns on this build |
| Cost of `mockStatic` instead | `mockito-inline`, a `try`-with-resources scope, no parallelism on that class, and it breaks when the call site moves |
| The five `Clock` factories | `systemUTC`, `systemDefaultZone`, `fixed`, `offset`, `tick` / `tickSeconds` / `tickMinutes` |
| `Clock.fixed` limit | freezes time, so code measuring a duration between two reads sees zero |
| `Clock.tick` limit | truncates toward the past, so it can read before an event that already happened |
| Expiry comparison | expired iff `!now.isBefore(expiresAt)`; half-open `[grantedAt, grantedAt + 30d)` |
| `Clock.systemUTC()` precision | milliseconds on Java 8, **microseconds** on JDK 9+ (measured: nano % 1000 == 0, nano % 1000000 != 0) |
| Elapsed time | never a `Clock` — `System.nanoTime()`; a `Clock` may step backwards across an NTP step |
| `Clock` and serialization | the four implementations are `Serializable`, the abstract `Clock` is not: mark the field `transient` |
| Not fixed by injecting a `Clock` | database `CURRENT_TIMESTAMP`, `@CreationTimestamp`, broker timestamps, library TTLs, JWT `exp` |
| `main`-based test guard | `assert assertionsOn = true` then print it, or a green run tested nothing |
| Bonus windows | expiry 30 days from grant, unspent to `PROMOTIONAL_EXPENSE`; coupon 14 days from registration |

---

## Self-test


**Q1.** The 30-day boundary: why does `now.isAfter(expiresAt)` versus `!now.isBefore(expiresAt)`
matter, when they differ for exactly one instant?

<details><summary>Answer</summary>

Because "one instant" is only true at the precision you are comparing at, and that precision
shrinks the moment the value leaves the JVM. In memory the difference is a nanosecond; in a
`TIMESTAMP(3)` column, a millisecond; compared as `LocalDate`, a whole day — a 30-day promotional
liability quietly becoming 31 days across every bonus in the book, at 3.1k grants a day averaging
42.

There is also a tiling argument. With `!now.isBefore(expiresAt)` the active window is half-open,
`[grantedAt, grantedAt + 30d)`, so consecutive windows abut with no overlap and no gap. With
`isAfter` they overlap at the endpoints, so one instant can belong to two windows — the class of
bug that surfaces as a double posting to `PROMOTIONAL_EXPENSE`. Half-open is the default, and the
test asserting both sides one nanosecond apart is what pins it.

</details>

**Q2.** Your service takes a `Clock`, its boundaries are tested exactly, and a bonus still expires
a day late in production. Where do you look?

<details><summary>Answer</summary>

At every clock you did not inject. In order: the database — a `DEFAULT CURRENT_TIMESTAMP` or a JPA
`@CreationTimestamp` setting `grantedAt` from the DB server's clock in its own zone rather than
from your `Clock`; the scheduler that triggers the expiry sweep, which may run in local time and
skip or repeat an hour across a DST transition; truncation on write, if `grantedAt` lands in a
second- or date-precision column and is then compared against a microsecond-precision read; and the
zone behind any `LocalDate` comparison, since `systemDefaultZone()` differs per host. The rule that
follows: the timestamp a domain rule depends on should be set by the injected clock at the domain
boundary and passed inward, never defaulted by the storage layer.

</details>

**Q3.** You inject a `Clock` and then use it to time how long the expiry sweep took. What is wrong
with that?

<details><summary>Answer</summary>

A `Clock` reports wall-clock time, and wall-clock time is not monotonic: `instant()` can go
backwards across an NTP step or a manual clock adjustment, so the difference between two reads can
be negative, zero, or wrong by however far the clock jumped. `Clock.fixed`, the implementation your
tests use, makes it worse in a way tests cannot catch — every read returns the same instant, so any
duration measured through the injected clock is exactly zero in every test and plausible-looking in
production.

Elapsed time is `System.nanoTime()`, which is specified as a monotonic high-resolution source with
no relationship to wall-clock time and no meaning as an absolute value. The two concerns are
separate: inject a `Clock` for *decisions about when* something happens, use `nanoTime` for *how
long* something took, and never route one through the other.

</details>

**Q4.** `Clock.tickMinutes(ZoneOffset.UTC)` printed `2026-08-29T13:54:00Z` while `systemUTC()` read
`13:54:03.386566Z`. Where is that useful and where is it a trap?

<details><summary>Answer</summary>

Useful when something downstream really is coarse: a partner file dropped once a minute, a cache
whose TTL is expressed in whole minutes, an upstream timestamp you know is second-precision.
Modelling that coarseness in the clock rather than sprinkling `truncatedTo` calls through the
domain keeps one decision in one place.

The trap is twofold. Truncation is toward the past, so a tick clock can report an instant *before*
an event that has already happened — a bonus granted at `13:54:03` compared against a
`tickMinutes` read of `13:54:00` looks like it was granted in the future. And as a test fixture it
is far too forgiving: a test that only ever compares whole minutes will pass with up to 59 seconds
of error in the code under test, which is exactly the size of bug the boundary tests in this file
exist to catch. Use `Clock.fixed` for boundary tests and reserve `tick` for modelling a real
coarseness that exists in the system.

</details>

**Q5.** The interviewer says "just use `mockStatic` on `Instant.now()`, same result, no constructor
parameter". Answer them.

<details><summary>Answer</summary>

It is not the same result. `mockStatic` gives a byte-code-level interception of a JDK type for
every call on the thread while the `MockedStatic` is open, so it catches `Instant.now()` calls
inside collaborators you did not intend to stub, it forces a `try`-with-resources scope in every
test, it rules out parallel tests touching that class, and it needs `mockito-inline` behaviour on
the classpath. Worse, it is coupled to the *call site* rather than the behaviour: refactor
`expireIfDue` to delegate to a helper that reads `Clock.systemUTC().instant()` and the mock now
stubs a method nobody calls, while the test keeps passing for the wrong reason.

The `Clock` parameter is coupled to the collaboration instead. It needs no framework, works in a
plain `main` with `assert` as this file demonstrates, is visible in the constructor signature so
the dependency is documented, and survives refactoring because the seam is the field, not a line of
code. And the JDK is already built for it: every `java.time` type has a `now(Clock)` overload
precisely so that time can be injected rather than intercepted.

</details>


---

## Open questions

- none

---

**Leaves covered:** 4.7.7 (1 leaf)
**Leaves deferred:** none
**Diagrams included:** none
**Target version:** Java 21 LTS
**Lines:** 568
