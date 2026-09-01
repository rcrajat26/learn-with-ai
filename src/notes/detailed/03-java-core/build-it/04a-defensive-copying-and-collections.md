# 03 Java Core — Value-object builds: the two escape bugs, and a `List` component three ways — BUILD IT (§4.7.4, §4.7.5)

**Target version: Java 21 LTS.** | **Part 4 of 5** | [Index](../00-index.md)
Previous: [Allocation, precision, and rounding bias](04c-allocation-and-rounding-bias.md) · Next: [Deep copy, and Clock injection](04b-deep-copy-and-clock-injection.md)

An immutable object is a fence around some state. `final` on a field is a claim about the fence
post, not the field's interior: the reference will never be reassigned, and nothing whatever is
said about whether the thing it points at can change. The fence has exactly two holes.

| Hole | Where it is | What leaks | Who mutates |
|---|---|---|---|
| **In** | the constructor | the caller's reference becomes your field | the caller, after you return |
| **Out** | the accessor | your field becomes the caller's reference | any holder, at any time |

Close one and the object is still mutable. Close both and it is immutable — provided the
component has no third hole, which is the shallow-versus-deep question that
`../immutability-and-design/02a-shallow-deep-and-building-blocks.md` owns.

Both builds below reuse the types order 21 (`04-value-objects-and-money.md`) shipped:
`Money(BigDecimal amount, Currency currency)`, a record whose compact constructor forces the
scale from `Currency.getDefaultFractionDigits()`, and `ClientId` wrapping a `UUID`. Restated in
five lines so the programs on this page compile standalone; the definitions live there.

```java
record ClientId(UUID value) {
    static ClientId of(String s) { return new ClientId(UUID.fromString(s)); }
    @Override public String toString() { return "ClientId[" + value + "]"; }
}
record Money(BigDecimal amount, Currency currency) {
    Money { amount = amount.setScale(currency.getDefaultFractionDigits(), RoundingMode.UNNECESSARY); }
    static Money gbp(String v) { return new Money(new BigDecimal(v), Currency.getInstance("GBP")); }
    @Override public String toString() { return currency.getCurrencyCode() + " " + amount; }
}
```

---

## §4.7.4 — A mutable-input value class, both escape bugs, then fixed `[BUILD]` `[PROVE]`

### The component, and why `Date` is the exhibit

QuizStakes grants a `Bonus` of 10% of the first deposit capped at 100, and it expires 30 days
from grant. So a `Bonus` carries a grant timestamp, and the timestamp decides money: whether a
stake may draw bonus at all, and whether unspent bonus reverses to `PROMOTIONAL_EXPENSE`.

The timestamp is the mutable component. In new code it is an `Instant` and there is nothing to
discuss. The historical exhibit is `java.util.Date`, the JDK's own worst offender: a value — a
single instant — with a public `setTime(long)` that mutates it in place, so every `Date` you
hand out or accept is a live wire. A `Date` in new code is wrong; it is used here because it is
the shortest complete demonstration of a bug class that lands identically on
`java.util.Calendar`, on any `List` field, on `byte[]`, and on any hand-written mutable
aggregate that leaks into a value object.

### Version 1 — no copy in, no copy out

```java
static final class BonusNoCopy {
    private final ClientId clientId;
    private final Money amount;
    private final Date grantedAt;

    BonusNoCopy(ClientId clientId, Money amount, Date grantedAt) {
        this.clientId = clientId;
        this.amount = amount;
        this.grantedAt = grantedAt;           // stores the caller's reference
    }

    ClientId clientId() { return clientId; }
    Money amount() { return amount; }
    Date grantedAt() { return grantedAt; }    // hands out the internal reference
    Date expiresAt() { return new Date(grantedAt.getTime() + Duration.ofDays(30).toMillis()); }
    boolean expiredAt(Date now) { return now.after(expiresAt()); }

    @Override public String toString() {
        return "Bonus[" + clientId + ", " + amount + ", grantedAt=" + grantedAt.getTime()
                + ", expiresAt=" + expiresAt().getTime() + "]";
    }
}
```

Every field is `private final`. There is no setter. The class is `final`. By every checklist
this is an immutable value object, and it is not one.

```java
ClientId client = ClientId.of("8f14e45f-ceea-467a-9e2b-1c3d4a5b6c70");
Money grant = Money.gbp("42.00");

Date grantedAt = new Date(1_700_000_000_000L);
BonusNoCopy b1 = new BonusNoCopy(client, grant, grantedAt);
System.out.println("after construction : " + b1);
grantedAt.setTime(1_600_000_000_000L);   // caller mutates its own reference
System.out.println("after caller mutate: " + b1);
System.out.println("no method was called on b1");
```

Real output, Oracle JDK 21.0.7 (build 21.0.7+8-LTS-245), macOS aarch64:

```console
=== attack 1: no copy in ===
after construction : Bonus[ClientId[8f14e45f-ceea-467a-9e2b-1c3d4a5b6c70], GBP 42.00, grantedAt=1700000000000, expiresAt=1702592000000]
after caller mutate: Bonus[ClientId[8f14e45f-ceea-467a-9e2b-1c3d4a5b6c70], GBP 42.00, grantedAt=1600000000000, expiresAt=1602592000000]
no method was called on b1
```

The grant moved back 100,000,000,000 ms — about 1,157 days — and the derived expiry moved with
it. The `Bonus` is now `EXPIRED` and nobody called anything on it: an unspent bonus became
reversible to `PROMOTIONAL_EXPENSE` because an unrelated caller reused a `Date` variable.

### Version 2 — copy in, still no copy out

The common stopping point: read about defensive copying, add the constructor copy, move on — and
half of it is still broken.

```java
static final class BonusCopyInOnly {
    private final ClientId clientId;
    private final Money amount;
    private final Date grantedAt;

    BonusCopyInOnly(ClientId clientId, Money amount, Date grantedAt) {
        this.clientId = clientId;
        this.amount = amount;
        this.grantedAt = new Date(grantedAt.getTime());   // copy in
    }

    Date grantedAt() { return grantedAt; }               // still leaks
    Date expiresAt() { return new Date(grantedAt.getTime() + Duration.ofDays(30).toMillis()); }

    @Override public String toString() {
        return "Bonus[" + clientId + ", " + amount + ", grantedAt=" + grantedAt.getTime()
                + ", expiresAt=" + expiresAt().getTime() + "]";
    }
}
```

```java
Date fresh = new Date(1_700_000_000_000L);
BonusCopyInOnly b2 = new BonusCopyInOnly(client, grant, fresh);
fresh.setTime(1_600_000_000_000L);                          // attack 1, now defeated
System.out.println("copy-in defeats attack 1: " + b2);
b2.grantedAt().setTime(1_600_000_000_000L);                 // attack 2, one expression
System.out.println("attack 2 lands       : " + b2);
```

```console
=== attack 2: no copy out (survives fix 1) ===
copy-in defeats attack 1: Bonus[ClientId[8f14e45f-ceea-467a-9e2b-1c3d4a5b6c70], GBP 42.00, grantedAt=1700000000000, expiresAt=1702592000000]
attack 2 lands       : Bonus[ClientId[8f14e45f-ceea-467a-9e2b-1c3d4a5b6c70], GBP 42.00, grantedAt=1600000000000, expiresAt=1602592000000]
```

Attack 1 is dead; attack 2 lands on the same line of state, in one expression, with no local
variable and no aliasing anyone would notice in review.

**Insight:** the two holes are independent, and the second is worse. A leaked constructor
argument needs the caller to keep a reference; a leaked accessor result hands a fresh reference
to *every* caller, forever.

### Version 3 — both holes closed

```java
static final class BonusFixed {
    private final ClientId clientId;
    private final Money amount;
    private final Date grantedAt;

    BonusFixed(ClientId clientId, Money amount, Date grantedAt) {
        this.clientId = clientId;
        this.amount = amount;
        this.grantedAt = new Date(grantedAt.getTime());   // copy in
    }

    Date grantedAt() { return new Date(grantedAt.getTime()); }   // copy out
    Date expiresAt() { return new Date(grantedAt.getTime() + Duration.ofDays(30).toMillis()); }

    @Override public String toString() {
        return "Bonus[" + clientId + ", " + amount + ", grantedAt=" + grantedAt.getTime()
                + ", expiresAt=" + expiresAt().getTime() + "]";
    }
}
```

```console
=== both fixed ===
after construction : Bonus[ClientId[8f14e45f-ceea-467a-9e2b-1c3d4a5b6c70], GBP 42.00, grantedAt=1700000000000, expiresAt=1702592000000]
after attack 1     : Bonus[ClientId[8f14e45f-ceea-467a-9e2b-1c3d4a5b6c70], GBP 42.00, grantedAt=1700000000000, expiresAt=1702592000000]
after attack 2     : Bonus[ClientId[8f14e45f-ceea-467a-9e2b-1c3d4a5b6c70], GBP 42.00, grantedAt=1700000000000, expiresAt=1702592000000]
```

Both attacks run and neither moves the state.

### Why the copy is `new Date(d.getTime())` and never `d.clone()`

`Date` implements `Cloneable`, so `clone()` looks like the natural copy. It is not, because
`clone()` on a non-final type returns an instance of the *argument's* runtime class, which may
be a hostile subclass that overrides the accessor. `new Date(long)` cannot: the result is
exactly `java.util.Date`, whatever came in. Probed against a `Date` subclass whose `getTime()`
returns 1700000000000 on the first call and 1600000000000 on every call after it — the same
trick as `OscillatingGrantDate` in the next subsection:

```console
clone() runtime class : CloneProbe$OscillatingGrantDate
clone() getTime()     : 1700000000000
clone() getTime() again: 1600000000000
new Date(getTime()) class: java.util.Date
new Date(getTime()) value: 1700000000000, again 1700000000000
```

The `clone()` "copy" is still an `OscillatingGrantDate` and still lies. The constructor copy is
a plain `Date` and cannot.

### The ordering subtlety: check-then-copy is still broken

Copying in is not enough if you **validate the caller's object and then copy it**. That is two
reads of a value the caller controls, and nothing says the two reads agree. Between the check
and the copy the value can change — by a second thread, or, deterministically, by a subclass
whose accessor returns something different each call.

QuizStakes gate: the grant timestamp must be no more than 30 days old, or the `Bonus` is
`EXPIRED` before it is created.

```java
static final long NOW = 1_700_000_000_000L;
static final long THIRTY_DAYS = Duration.ofDays(30).toMillis();

/** Returns a legal timestamp the first time it is asked, a long-expired one afterwards. */
static final class OscillatingGrantDate extends Date {
    private int calls = 0;
    OscillatingGrantDate() { super(NOW - Duration.ofDays(1).toMillis()); }
    @Override public long getTime() {
        calls++;
        return calls == 1
                ? NOW - Duration.ofDays(1).toMillis()      // 1 day old: passes the gate
                : NOW - Duration.ofDays(400).toMillis();   // 400 days old: already expired
    }
}

static final class BonusCheckThenCopy {
    private final ClientId clientId;
    private final Money amount;
    private final Date grantedAt;

    BonusCheckThenCopy(ClientId clientId, Money amount, Date grantedAt) {
        if (grantedAt.getTime() < NOW - THIRTY_DAYS) {         // CHECK: on the caller's object
            throw new IllegalArgumentException("bonus already EXPIRED at grant time");
        }
        this.clientId = clientId;
        this.amount = amount;
        this.grantedAt = new Date(grantedAt.getTime());        // USE: second read, different value
    }

    long ageDays() { return Duration.ofMillis(NOW - grantedAt.getTime()).toDays(); }
    Date grantedAt() { return new Date(grantedAt.getTime()); }
    @Override public String toString() { return "Bonus[" + clientId + ", " + amount + ", ageDays=" + ageDays() + "]"; }
}

static final class BonusCopyThenCheck {
    private final ClientId clientId;
    private final Money amount;
    private final Date grantedAt;

    BonusCopyThenCheck(ClientId clientId, Money amount, Date grantedAt) {
        Date snapshot = new Date(grantedAt.getTime());         // COPY first, one read only
        if (snapshot.getTime() < NOW - THIRTY_DAYS) {          // CHECK the copy
            throw new IllegalArgumentException("bonus already EXPIRED at grant time");
        }
        this.clientId = clientId;
        this.amount = amount;
        this.grantedAt = snapshot;
    }

    long ageDays() { return Duration.ofMillis(NOW - grantedAt.getTime()).toDays(); }
    Date grantedAt() { return new Date(grantedAt.getTime()); }
    @Override public String toString() { return "Bonus[" + clientId + ", " + amount + ", ageDays=" + ageDays() + "]"; }
}
```

```console
=== check-then-copy, hostile input ===
constructed: Bonus[ClientId[8f14e45f-ceea-467a-9e2b-1c3d4a5b6c70], GBP 42.00, ageDays=400]
gate said <= 30 days old; stored value is 400 days old

=== copy-then-check, same hostile input ===
constructed: Bonus[ClientId[8f14e45f-ceea-467a-9e2b-1c3d4a5b6c70], GBP 42.00, ageDays=1]
the checked value IS the stored value: 1 days old

=== copy-then-check, honest input ===
Bonus[ClientId[8f14e45f-ceea-467a-9e2b-1c3d4a5b6c70], GBP 42.00, ageDays=1]
```

Check-then-copy constructs a `Bonus` 400 days old through a gate that rejects anything over 30:
the invariant is stated, enforced, and false. Copy-then-check reads the caller's object exactly
once, so the validated value is the stored value and there is no window.

The two-thread version — a `paymentRunWorker` calling `setTime` on the shared `Date` between
the check and the copy — is the same defect, but it is nondeterministic and a passing run proves
nothing, so the subclass route is what is demonstrated here.

> **Copy first, then validate the copy: a value you validated and a value you stored are the
> same value only if you read the caller's object once.**

**Interview:** "You copy the argument in the constructor — is that enough?" Answer: only if the
copy happens before the validation; otherwise the check and the store see different values.

### The cost, and the escape hatch that is not "skip the copy"

Measured with `com.sun.management.ThreadMXBean.getThreadAllocatedBytes` deltas over 2,000,000
iterations after a 20,000-iteration warm-up, under `-XX:-DoEscapeAnalysis`, on Oracle JDK 21.0.7
(build 21.0.7+8-LTS-245), macOS aarch64, compressed oops on — order 22's configuration. Not JMH.

`new Date(d.getTime())` costs **24 B**: header 12 (mark 8 + compressed klass 4) + `fastTime`
long 8 + `cdate` reference 4 = 24, already 8-aligned. One per construction and one per read.
At QuizStakes' 3.1k bonus grants/day that is nothing; on an accessor consulted per stake
reservation at 1,200/sec peak it is 28.8 kB/sec of pure garbage to hand back a value that never
changes.

The escape hatch is not "skip the copy out." It is "stop holding a mutable component."

```java
record BonusGrant(ClientId clientId, Money amount, Instant grantedAt) {
    BonusGrant {
        if (grantedAt.isBefore(Instant.ofEpochMilli(NOW).minus(Duration.ofDays(30)))) {
            throw new IllegalArgumentException("bonus already EXPIRED at grant time");
        }
    }
    Instant expiresAt() { return grantedAt.plus(Duration.ofDays(30)); }
}
```

```console
=== Instant component: no copies anywhere ===
BonusGrant[clientId=ClientId[8f14e45f-ceea-467a-9e2b-1c3d4a5b6c70], amount=GBP 42.00, grantedAt=2023-11-13T22:13:20Z]
expiresAt = 2023-12-13T22:13:20Z
rejected: bonus already EXPIRED at grant time
```

`Instant` is final and has no mutator, so both copies are unnecessary, the record's generated
accessor is safe as generated, the ordering question disappears (there is nothing to copy), and
the allocation goes to zero. That is the recommendation: `Instant`, `LocalDate`, `Money`,
`List.of` — pick components that cannot change and the section stops applying. Copy defensively
only when a mutable component is forced on you by an API you do not own. Immutability design
(safe publication, `final` field semantics) is `../immutability-and-design/02-immutability.md`;
copying and composite equality is
`../objects-equality-and-lifecycle/02-copying-and-composite-equality.md`.

### Diff vs the real one — `BonusFixed` versus `java.util.Date` as the JDK ships it

| Axis | `BonusFixed` here | The JDK's own types |
|---|---|---|
| Edge cases | one `long` component, no calendar arithmetic, no time zone | `Date` carries a lazily-computed `BaseCalendar.Date cdate`, a `Long.MIN_VALUE` sentinel for "not set", and pre-Gregorian-cutover handling |
| Intrinsics | none | none in `Date`; `Instant.now()` reaches `VM.getNanoTimeAdjustment`, an intrinsic |
| Serialization | none declared; `Date`'s `writeObject` writes only `getTime()`, so a serialized graph would round-trip the `long` | `Date` has `serialVersionUID = 7523967970034938905L` and a custom `writeObject`/`readObject` pair |
| Null policy | `grantedAt.getTime()` NPEs on null with no message — a real class needs `Objects.requireNonNull(grantedAt, "grantedAt")` | `Instant.plus` and friends do explicit `Objects.requireNonNull` with named parameters |
| Thread safety | safe once both holes are closed: `final` field, immutable-after-construction, safely published | `Date` is documented as not thread-safe; `Instant` is immutable and thread-safe by construction |
| Allocation tricks | none; 24 B per copy, twice per round trip | `java.time` interns nothing but avoids the copies entirely; `Instant.EPOCH` is a shared constant |
| Why the JDK bothers | it does not, any more: `java.time` exists precisely so this class of build is unnecessary | `Date`'s mutability is a 1996 mistake preserved for compatibility; JSR-310 replaced it and every `java.time` type is final and immutable |

---

## §4.7.5 — An immutable class with a `List` component, three ways `[BUILD]` `[PROVE]`

A `PaymentRun` is a batch of approved bank withdrawals with operator sign-off: 7k bank
withdrawals/day in 4 windows. It holds the withdrawal ids in the run, and once signed off that
membership is a fact and must not move.

```java
/** A bank withdrawal in a PaymentRun. Mutable status: the operator signs it off later. */
static final class WithdrawalTransaction {
    private final String id;
    private String status;
    WithdrawalTransaction(String id, String status) { this.id = id; this.status = status; }
    String id() { return id; }
    String status() { return status; }
    void status(String status) { this.status = status; }
    @Override public String toString() { return id + ":" + status; }
}
```

### Way 1 — the broken direct assignment

```java
static final class PaymentRunDirect {
    private final String runId;
    private final List<String> withdrawalIds;
    PaymentRunDirect(String runId, List<String> withdrawalIds) {
        this.runId = runId;
        this.withdrawalIds = withdrawalIds;         // stores the caller's list
    }
    List<String> withdrawalIds() { return withdrawalIds; }   // hands it straight back
    int size() { return withdrawalIds.size(); }
    @Override public String toString() { return runId + withdrawalIds; }
}
```

```console
=== way 1: direct assignment, attack in ===
after construction : PR-9001[WT-1001, WT-1002] size=2
after caller add   : PR-9001[WT-1001, WT-1002, WT-9999] size=3

=== way 1: direct assignment, attack out ===
after holder clear : PR-9001[] size=0
```

Both directions. `WT-9999` entered a signed-off run without a sign-off, then the whole run was
emptied through the accessor.

### Way 2 — `Collections.unmodifiableList`, and the half-fix that fools people

```java
// 2a: unmodifiableList WITHOUT a copy - the half-fix
static final class PaymentRunViewOnly {
    private final String runId;
    private final List<String> withdrawalIds;
    PaymentRunViewOnly(String runId, List<String> withdrawalIds) {
        this.runId = runId;
        this.withdrawalIds = Collections.unmodifiableList(withdrawalIds);   // view over the CALLER's list
    }
    List<String> withdrawalIds() { return withdrawalIds; }
    @Override public String toString() { return runId + withdrawalIds; }
}

// 2b: unmodifiableList over a copy
static final class PaymentRunUnmodifiableCopy {
    private final String runId;
    private final List<String> withdrawalIds;
    PaymentRunUnmodifiableCopy(String runId, List<String> withdrawalIds) {
        this.runId = runId;
        this.withdrawalIds = Collections.unmodifiableList(new ArrayList<>(withdrawalIds));
    }
    List<String> withdrawalIds() { return withdrawalIds; }
    @Override public String toString() { return runId + withdrawalIds; }
}
```

`Collections.unmodifiableList` returns a **view**. `UnmodifiableList` holds a reference to the
list you gave it and forwards every read to it; only the mutators throw. So `unmodifiableList`
without a copy produces an object that refuses your writes and accepts the caller's.

```console
=== way 2a: unmodifiableList without a copy ===
after construction : PR-9002[WT-1001, WT-1002]
add through view    : UnsupportedOperationException (as advertised)
caller adds to its own backing list
the 'unmodifiable'  : PR-9002[WT-1001, WT-1002, WT-9999]
```

That is the whole point of the word *view*, and it is the single most common half-fix in this
area: the wrapper's `UnsupportedOperationException` is convincing, so the missing copy never
gets noticed.

With the copy in place, nothing gets through:

```console
=== way 2b: unmodifiableList over a copy ===
after caller add    : PR-9003[WT-1001, WT-1002]
add                 : UnsupportedOperationException
iterator().remove() : UnsupportedOperationException
listIterator().set(): UnsupportedOperationException
wrapper class       : java.util.Collections$UnmodifiableRandomAccessList
```

`listIterator().set()` is worth confirming rather than assuming, because `set` replaces an
element without changing size and a wrapper could plausibly have let it through. It does not.
JDK 21 `java.util.Collections`, inside `UnmodifiableList.listIterator(int)`:

```java
public ListIterator<E> listIterator(final int index) {
    return new ListIterator<>() {
        private final ListIterator<? extends E> i
            = list.listIterator(index);

        public boolean hasNext()     {return i.hasNext();}
        public E next()              {return i.next();}
        public int nextIndex()       {return i.nextIndex();}

        public void remove() {
            throw new UnsupportedOperationException();
        }
        public void set(E e) {
            throw new UnsupportedOperationException();
        }
        public void add(E e) {
            throw new UnsupportedOperationException();
        }
```

An anonymous `ListIterator` that delegates every navigation and query method to the backing
iterator `i` — `hasPrevious`, `previous`, `previousIndex` and `forEachRemaining` follow the same
three shown here — and hard-throws from all three mutators, `remove`, `set` and `add`.
`UnmodifiableList.subList` wraps the backing sublist in a fresh `UnmodifiableList`, so protection
is not lost through a view of a view.

### Way 3 — `List.copyOf`

```java
record PaymentRunCopyOf(String runId, List<String> withdrawalIds) {
    PaymentRunCopyOf {
        withdrawalIds = List.copyOf(withdrawalIds);
    }
    @Override public String toString() { return runId + withdrawalIds; }
}
```

Java 10 (`@since 10`). One call does both jobs: it copies, and the result is a genuinely
immutable `List` from the `ImmutableCollections` family, not a view over anything — so the
record's generated accessor is safe as generated, with no copy out to write.

```console
=== way 3: List.copyOf ===
after caller add    : PR-9004[WT-1001, WT-1002]
add                 : UnsupportedOperationException
result class        : java.util.ImmutableCollections$List12
```

Two behaviours are folklore-prone; both come from the source. JDK 21 `java.util.List`:

```java
static <E> List<E> copyOf(Collection<? extends E> coll) {
    return ImmutableCollections.listCopy(coll);
}
```

and `java.util.ImmutableCollections`:

```java
static <E> List<E> listCopy(Collection<? extends E> coll) {
    if (coll instanceof List12 || (coll instanceof ListN<?> c && !c.allowNulls)) {
        return (List<E>)coll;
    } else if (coll.isEmpty()) { // implicit nullcheck of coll
        return List.of();
    } else {
        return (List<E>)List.of(coll.toArray());
    }
}
```

Read it branch by branch. The first returns **the argument itself** when the argument is already
a null-rejecting immutable list — `List12` (the one- and two-element specialisation) or a `ListN`
built with `allowNulls == false`, which is what `List.of` produces. Legitimate precisely because
such a list cannot change, so sharing is indistinguishable from copying. Note the guard: a
`ListN` with `allowNulls == true` (what `Stream.toList()` produces) is *not* returned as-is,
because it may hold nulls and `copyOf`'s contract forbids them. The second branch turns any empty
collection into the shared `List.of()`, and is where the null check on `coll` itself happens. The
third is the real copy, through the null-rejecting `List.of(Object[])`.

```console
=== does List.copyOf ever return its argument? ===
List.copyOf(List.of(..)) == argument            : true
List.copyOf(ArrayList) == argument              : false
List.copyOf(unmodifiableList(..)) == argument   : false
List.copyOf(List.of()) == List.of()            : true
```

`unmodifiableList(x)` is a `Collections$UnmodifiableRandomAccessList`, not an
`AbstractImmutableList`, so `copyOf` copies it — correctly, because its backing list can change.

The null policy is the behavioural difference that breaks migrations:

```console
=== null policy ===
unmodifiableList over a copy holding null: [WT-1001, null]
List.copyOf(list with null) -> NullPointerException, message=null
```

`unmodifiableList(new ArrayList<>(withNull))` holds the null and prints it. `List.copyOf` throws
`NullPointerException` with a null message, so the stack trace is the only clue. Code storing a
sparse `List<String>` of withdrawal ids starts throwing the day someone swaps in `copyOf`.

### The shallow-copy limit, which applies to all three

Copying a list copies the references in it. A mutable **element** is still shared.

```java
WithdrawalTransaction wt = new WithdrawalTransaction("WT-1001", "REQUIRED");
List<WithdrawalTransaction> txCaller = new ArrayList<>(List.of(wt));
List<WithdrawalTransaction> stored = List.copyOf(txCaller);
System.out.println("stored before        : " + stored);
wt.status("SATISFIED");
System.out.println("caller mutated the element it still holds");
System.out.println("stored after         : " + stored);
System.out.println("same element object  : " + (stored.get(0) == wt));
```

```console
=== shallow-copy limit: a mutable ELEMENT ===
stored before        : [WT-1001:REQUIRED]
caller mutated the element it still holds
stored after         : [WT-1001:SATISFIED]
same element object  : true
```

`List.copyOf` gave a new, immutable, independent list — and the status inside it went `REQUIRED`
to `SATISFIED` anyway. Same conclusion as §4.7.4: make the element immutable, and
`record WithdrawalTransaction(String id, String status)` closes it completely for free. Shallow
versus deep is owned by `../immutability-and-design/02a-shallow-deep-and-building-blocks.md`; if
the element genuinely cannot be immutable, order 24 (`04b-deep-copy-and-clock-injection.md`)
builds the deep-copy utility as leaf 4.7.6 — use that rather than writing another.

### Allocation, measured

Same harness and configuration as above: `getThreadAllocatedBytes` deltas, 2,000,000 iterations,
20,000-iteration warm-up, `-XX:-DoEscapeAnalysis`, Oracle JDK 21.0.7 (build 21.0.7+8-LTS-245),
macOS aarch64, compressed oops on, five `String` elements. Not JMH.

| Construction | Measured | Byte arithmetic |
|---|---|---|
| direct assignment | **0 B** | nothing allocated |
| `new ArrayList<>(five)` | **64 B** | `ArrayList` 12 header + 4 `elementData` + 4 `size` + 4 `modCount` = 24; `Object[5]` 12 + 4 length + 20 = 36 → 40. 24 + 40 = 64 |
| `unmodifiableList(new ArrayList<>(five))` | **88 B** | the 64 above + `UnmodifiableRandomAccessList` 12 header + 4 `c` + 4 `list` = 20 → 24. 64 + 24 = 88 |
| `List.copyOf(five)` | **104 B** | `coll.toArray()` 40 + `ListN`'s own defensive re-copy of that array 40 + `ListN` 12 header + 4 `elements` + 1 `allowNulls` = 17 → 24. 40 + 40 + 24 = 104 |
| `List.copyOf(List.of(five elements))` | **0 B** | the `listCopy` fast path returns the argument |

`List.copyOf` is the most expensive copying form, by 40 B, because it copies the array twice:
once out of the source collection and once into `ListN`'s private storage. That is the price of
"cannot be aliased by anything, ever," and against 64 B for a bare `ArrayList` it is not worth
optimising. Feed it a `List.of` and it costs nothing.

### The three ways compared

| Axis | Direct assignment | `unmodifiableList` over a copy | `List.copyOf` |
|---|---|---|---|
| Copies the input | no | yes (the explicit `new ArrayList<>`) | yes, unless the fast path applies |
| Result | the caller's list | an unmodifiable **view** over your private copy | a genuinely immutable list |
| Caller can mutate the field | yes, in both directions | no | no |
| Needs a copy-out in the accessor | yes, and even then the field is still mutable internally | no | no |
| Null elements | allowed | allowed | rejected with `NullPointerException` (null message) |
| Throws | nothing | `UnsupportedOperationException` from `add`/`remove`/`set`/`clear`/`sort`, from `iterator().remove()`, and from all three `listIterator` mutators | `UnsupportedOperationException` from the same set, thrown by `ImmutableCollections.uoe()` |
| Allocation, 5 elements | 0 B | 88 B | 104 B, or 0 B on the fast path |
| Can return the argument unchanged | trivially (it *is* the argument) | no — always a fresh wrapper for a `List` | yes, for `List12` and null-rejecting `ListN` |
| Introduced | — | Java 1.2 | Java 10 |
| Internal code can still mutate | yes | **yes** — the private `ArrayList` is reachable from inside the class | no |

Ship **`List.copyOf`**. One call instead of two, no copy-out, and it closes the hole 2b leaves
open: the `unmodifiableList` version still has a mutable `ArrayList` behind the wrapper, which a
later method on the same class can reach and change. `List.copyOf` has nothing to reach. The one
case not to: a component that legitimately holds nulls, where `copyOf` throws — and the right
move there is to stop holding nulls (a `List<Optional<String>>`, a sentinel, a separate count),
not to reach back for `unmodifiableList`. An absent withdrawal id is a modelling bug.

### Diff vs the real one — `PaymentRunCopyOf` versus `ImmutableCollections`

| Axis | `PaymentRunCopyOf` here | `java.util.ImmutableCollections` |
|---|---|---|
| Edge cases | delegates all of them to `List.copyOf` | `List12` specialises size 1 and 2 with no backing array at all; `ListN` handles the rest; `SubList` and reversed views are separate classes |
| Intrinsics | none | none; the family's speed comes from field layout and final classes, not intrinsics |
| Serialization | none declared | `CollSer` is a single serialization proxy for the whole family, with a tag byte per shape, so the concrete classes never appear in a stream |
| Null policy | inherited: `NullPointerException` on a null element | `ListN` carries an `allowNulls` flag; `List.of` sets it false, and the trusted-array factory behind `Stream.toList()` sets it true |
| Thread safety | immutable and safely published via the record's `final` field | immutable; `SALT32L`/`REVERSE` randomisation affects only iteration order of `Set`/`Map`, not `List` |
| Allocation tricks | none of its own | the `listCopy` identity fast path; the shared empty `List.of()`; `List12` avoiding an array entirely for one and two elements |
| Why the JDK bothers | it does not need to — this is three lines of reuse | `Collections.unmodifiableList` was a view, which is a different and weaker guarantee; JEP-less but JDK 9/10 added the factories so "immutable list" stopped meaning "wrapper over something mutable" |

The section-wide §4.7 diff — all of these builds against what a `record` gives you for free — is
leaf 4.7.8 and lives in order 25, `04d-value-object-diff.md`.

---

## Pitfalls

### Believing `final` on a field makes the object immutable

**Wrong**

```java
private final Date grantedAt;                          // final, private, no setter, class is final
BonusNoCopy(ClientId clientId, Money amount, Date grantedAt) { this.grantedAt = grantedAt; }
```

```console
after construction : Bonus[ClientId[8f14e45f-ceea-467a-9e2b-1c3d4a5b6c70], GBP 42.00, grantedAt=1700000000000, expiresAt=1702592000000]
after caller mutate: Bonus[ClientId[8f14e45f-ceea-467a-9e2b-1c3d4a5b6c70], GBP 42.00, grantedAt=1600000000000, expiresAt=1602592000000]
```

**Right**

`final` freezes the reference, not the referent. Freeze the referent too — copy at both
boundaries, or better, pick a component with no mutator, which removes both copies:

```java
record BonusGrant(ClientId clientId, Money amount, Instant grantedAt) { }
```

**Why people believe it:** `final` genuinely does make a `final int` or `final String` field
unchangeable, and those are the fields people meet first. "Final means it cannot change" holds
for primitives and for immutable component types, which is most fields, so it survives a long
time before a `Date` or a `List` breaks it.

### Wrapping the caller's list in `unmodifiableList` without copying it

**Wrong**

```java
this.withdrawalIds = Collections.unmodifiableList(withdrawalIds);   // view over the CALLER's list
```

```console
add through view    : UnsupportedOperationException (as advertised)
caller adds to its own backing list
the 'unmodifiable'  : PR-9002[WT-1001, WT-1002, WT-9999]
```

**Right**

```java
this.withdrawalIds = List.copyOf(withdrawalIds);   // copies AND is immutable, not a view
```

**Why people believe it:** the wrapper does throw `UnsupportedOperationException`, immediately
and loudly, the first time anyone tests it — and that test passes. The javadoc's word is *view*,
but "unmodifiable" reads as a property of the data rather than of one reference to it.

### Copying in but not out

**Wrong**

```java
BonusCopyInOnly(ClientId clientId, Money amount, Date grantedAt) {
    this.grantedAt = new Date(grantedAt.getTime());   // copy in
}
Date grantedAt() { return grantedAt; }               // and straight back out
```

```console
copy-in defeats attack 1: Bonus[ClientId[8f14e45f-ceea-467a-9e2b-1c3d4a5b6c70], GBP 42.00, grantedAt=1700000000000, expiresAt=1702592000000]
attack 2 lands       : Bonus[ClientId[8f14e45f-ceea-467a-9e2b-1c3d4a5b6c70], GBP 42.00, grantedAt=1600000000000, expiresAt=1602592000000]
```

**Right**

```java
Date grantedAt() { return new Date(grantedAt.getTime()); }   // copy out too
```

**Why people believe it:** defensive copying is taught as a constructor technique, and the
constructor is where the "defence" metaphor puts it — you guard the door you come in through. An
accessor does not look like a mutation point, because getters are read-only by reputation. They
are read-only about the *reference*.

### Validating before copying

**Wrong**

```java
if (grantedAt.getTime() < NOW - THIRTY_DAYS) {         // CHECK the caller's object
    throw new IllegalArgumentException("bonus already EXPIRED at grant time");
}
this.grantedAt = new Date(grantedAt.getTime());        // then read it a SECOND time
```

```console
constructed: Bonus[ClientId[8f14e45f-ceea-467a-9e2b-1c3d4a5b6c70], GBP 42.00, ageDays=400]
gate said <= 30 days old; stored value is 400 days old
```

**Right**

```java
Date snapshot = new Date(grantedAt.getTime());         // COPY first, one read only
if (snapshot.getTime() < NOW - THIRTY_DAYS) {          // CHECK the copy
    throw new IllegalArgumentException("bonus already EXPIRED at grant time");
}
this.grantedAt = snapshot;
```

**Why people believe it:** validate-first reads as defensive programming — reject bad input
before spending an allocation on it — and every guard-clause style guide recommends that order.
It is correct for immutable arguments, which is nearly all of them. The moment the argument is
mutable, "validate then use" is two reads of a value someone else controls.

### Believing a record gives you defensive copying for free

**Wrong**

```java
record PaymentRunLeaky(String runId, List<String> withdrawalIds) { }   // no compact constructor
```

Both escape holes are open: the canonical constructor assigns the parameter straight to the
field, and the generated accessor returns it straight back. `callerList.add("WT-9999")` and
`run.withdrawalIds().clear()` both land, exactly as they did on `PaymentRunDirect`. The record's
final fields and generated `equals`/`hashCode` change nothing about that.

**Right**

```java
record PaymentRunCopyOf(String runId, List<String> withdrawalIds) {
    PaymentRunCopyOf {
        withdrawalIds = List.copyOf(withdrawalIds);
    }
}
```

**Why people believe it:** records are the language's answer to value objects and do give a great
deal for free — final fields, component equality, no setters. The guaranteed part is *shallow*
immutability. The compact constructor exists so there is somewhere to put the copy, which is a
strong hint that nobody puts it there for you.

---

## Cheat sheet

| Question | Answer |
|---|---|
| Holes in an immutable boundary | two: constructor in, accessor out; `new Date(long)` is 24 B |
| What `final` on a field guarantees | the reference never changes; the referent may |
| Copy a `Date` with | `new Date(d.getTime())` — never `d.clone()`, which preserves a hostile subclass |
| Validation order | copy first, then validate the copy; one read of the caller's object |
| `unmodifiableList(x)` | a **view**; `x` is still mutable and still the backing list |
| `unmodifiableList` blocks | `add`/`remove`/`set`/`clear`/`sort`, `iterator().remove()`, all three `listIterator` mutators; `subList` re-wraps |
| `List.copyOf` | Java 10; copies **and** is immutable; no copy-out needed |
| `List.copyOf` null policy | `NullPointerException`, message `null` |
| `List.copyOf` fast path | returns the argument for `List12` and for `ListN` with `allowNulls == false` |
| Cost, 5 elements | 0 B direct / 88 B wrap-a-copy / 104 B `copyOf` / 0 B `copyOf` fast path; every JDK copy is shallow |
| Record for free | shallow-final fields only; the compact constructor is where the copy goes |
| The real fix | an immutable component (`Instant`, `Money`, `List.of`) — both copies vanish |

---

## Self-test

**Q1.** `BonusCopyInOnly` copies its `Date` argument in the constructor. Name the surviving
attack and write the one expression that performs it.

<details><summary>Answer</summary>

The copy-out hole. `grantedAt()` returns the internal reference, so any holder mutates the
object's state through it: `b2.grantedAt().setTime(1_600_000_000_000L);` — one expression, no
local variable. Measured, the grant moves from 1700000000000 to 1600000000000 and `expiresAt()`
moves with it. Fixing only the constructor is the common stopping point because a getter does
not look like a mutation site.

</details>

**Q2.** Why is `new Date(d.getTime())` the right defensive copy and `d.clone()` the wrong one,
given that `Date implements Cloneable`?

<details><summary>Answer</summary>

`clone()` returns an instance of the argument's runtime class, so a `Date` subclass that
overrides `getTime()` survives cloning and keeps lying. Measured: cloning an
`OscillatingGrantDate` produced a `CloneProbe$OscillatingGrantDate` whose `getTime()` returned
1700000000000 then 1600000000000. `new Date(long)` reads the value once and produces exactly
`java.util.Date`, which has no override to honour — the same probe gave 1700000000000 twice.

</details>

**Q3.** A constructor validates its `Date` argument and then copies it. Both steps are present.
What is wrong, and what is the fix?

<details><summary>Answer</summary>

It reads the caller's object twice and nothing guarantees the reads agree. A subclass with an
oscillating `getTime()` passes a "no older than 30 days" gate on read one and stores a
400-day-old value on read two — measured, a `Bonus` with `ageDays=400` through that gate. A
concurrent `setTime` from a `paymentRunWorker` does the same nondeterministically. Fix: copy
first, validate the copy, so the validated value provably is the stored value.

</details>

**Q4.** `Collections.unmodifiableList(callerList)` throws `UnsupportedOperationException` from
`add`. Is the field it is assigned to immutable?

<details><summary>Answer</summary>

No — it is a view. `UnmodifiableList` holds a reference to `callerList` and forwards every read
to it; only the mutators throw. The caller still holds `callerList`, and measured, `PR-9002`
grew a `WT-9999` entry through that original reference. Fix: copy before wrapping, or use
`List.copyOf`, which is not a view over anything.

</details>

**Q5.** When does `List.copyOf` return its argument rather than a copy, and why is that not a
bug? What breaks when a service migrates to it from `unmodifiableList`?

<details><summary>Answer</summary>

`ImmutableCollections.listCopy` returns the argument when it is a `List12` or a `ListN` with
`allowNulls == false` — the shapes `List.of` produces. Safe, because such a list has no mutator
and no backing array anyone else holds, so sharing and copying are observationally identical.
Measured: `List.copyOf(List.of("WT-1001", "WT-1002")) == that list` is `true`, while the same
call on an `ArrayList` or a `Collections.unmodifiableList` view is `false`.

The migration breaks on nulls. `unmodifiableList` over an `ArrayList` holds them —
`[WT-1001, null]` prints fine — while `List.copyOf` throws `NullPointerException` with a null
message, so the stack trace is the only clue. The fix is to stop storing nulls, not to revert.

</details>

---

## Open questions

- none

---

**Leaves covered:** 4.7.4, 4.7.5 (2 leaves)
**Leaves deferred:** none
**Diagrams included:** none
**Target version:** Java 21 LTS
**Lines:** 899
