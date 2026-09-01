# 03 Java Core — Immutability and design — Shallow versus deep, the building blocks, and what immutability costs — INTERMEDIATE (§2.3, 2.3.6–2.3.10)

**Target version: Java 21 LTS.** | **Part 2 of 5** | [Index](../00-index.md)
Previous: [The five immutability rules](02-immutability.md) · Next: [Records, the final-field freeze, and the cached derived field](02b-records-jmm-and-builders.md)

---

`02-immutability.md` settled the five rules, the static-factory substitute for rule 1, the copy-then-validate ordering, the copy-out-versus-view decision, and `List.copyOf` against `Collections.unmodifiable*`. All five rules were stated as if applying them ended the argument. They do not: a class can satisfy all five and still be mutable, because rule 4's copy has a *depth*, and the depth of the copy has to match the depth of the mutability. This file establishes that gap, then closes it from both ends — the JDK types whose mutability forces a copy on you, and the JDK types whose immutability means there is nothing to copy — and finishes with the two things the leaf list asks for last: the five benefits stated as mechanisms rather than adjectives, and the honest price. Records, the JMM `final`-field freeze and builders are `02b-records-jmm-and-builders.md`'s.

Every measured output below was produced on **Oracle JDK 21.0.7 (21.0.7+8-LTS-245), macOS aarch64**, compiled and run from a scratch directory under `/tmp/`. Library source is quoted from that build's `lib/src.zip`.

---

## 1. Shallow versus deep immutability: an immutable holder of mutable elements (2.3.6)

`[TRAP]` — `final` and "immutable" answer different questions, and almost every leak in this file is that confusion cashed out. `final` on a field is a statement about the **reference**: this slot will never be repointed at a different object. It says nothing whatsoever about whether the object at the far end of the reference can change under you. So a class can be a perfectly sealed box — `final class`, every field `private final`, no method named `set` anywhere — and still be mutable, because somebody else holds a key to what is *inside* the box.

The useful mental image is a safe deposit box bolted to the floor. `final` bolts the box down: nobody can swap your box for a different one. It does not lock the lid, and it certainly does not stop the person who handed you the contents from reaching back in.

### Why it exists

Because Java has no transitive `final` and no way to express one. There is no `deeply final`, no `const` propagating through a reference the way C++'s does, no compiler check that the object graph reachable from an immutable object is itself immutable. The JLS defines `final` on a field as a single-assignment constraint on the variable (JLS 21 §4.12.4, §8.3.1.2) and stops there. So "is this object immutable?" is a question about the whole reachable graph, and the language will only ever answer it for the first hop. Everything past the first hop is your discipline, which is why it fails.

### When to reach for it, and when not

Deep immutability is the target for every type that crosses a trust boundary or a thread boundary: `Money`, `LedgerEntry`, `Movement`, `PaymentRun`, `StakeSplit`, `Restriction`. Reach for the cheap route — make every field's type already immutable (§3) — before the expensive route of deep-copying per boundary crossing (§2). Do not reach for deep copying on a large graph read far more often than it is constructed: a `PaymentRun` holding 10,000 withdrawal ids, deep-copied on every accessor call at four banking-partner windows a day, buys a guarantee that immutable element types would have given for free.

### How it works

Two distinct failure forms, and they need different fixes.

| Form | What the holder does | Where the leak is | The fix |
|---|---|---|---|
| **Shallow immutability** | Stores the caller's mutable object directly in a `final` field, and/or returns it from an accessor | Hop 1 — the field's own referent | Copy in and copy out (rules 4 and 5), or replace the field's type (§3) |
| **Immutable holder of mutable elements** | Correctly stores `List.copyOf(entries)` — a list nobody can add to or remove from | Hop 2 — the *elements* the immutable list holds | Make the element type immutable, or deep-copy the elements |

The second form is the one that survives review, because the holder is genuinely correct. `List.copyOf` gives you a list whose every mutator throws and whose contents no later change to the source can reach — `02-immutability.md` §5 measured exactly that. What it does not give you is any control over the objects *in* the list. `List.copyOf` copies references; it does not copy referents. If `LedgerEntry` has a settable `amountMinor`, then `movement.entries().get(0).setAmountMinor(-99_999L)` walks straight through the immutable list and changes what `movement.totalMinor()` reports.

**The rule that unifies both forms: the copy-in depth must match the mutability depth.** A one-hop copy against a two-hop mutable graph is a one-hop guarantee, which is no guarantee at all. There are exactly two ways to reach real deep immutability:

1. **Every element and field type is itself immutable.** Then the depth of the mutability is zero and any copy depth satisfies it. This is what §3's building blocks buy, and it is the answer in essentially every case.
2. **A genuine deep copy at every boundary crossing.** Recursively copy the reachable graph on the way in and on the way out. This is what §2's mutable types force on you when you cannot replace them, and §5 prices it.

`../objects-equality-and-lifecycle/02-copying-and-composite-equality.md` owns the deep-copy mechanics themselves — why `clone()` is shallow by default, why a copy constructor per level is the maintainable form, and why a `Serializable` round-trip is the lazy form. The mechanism in one paragraph: a shallow copy allocates a new object and assigns each field from the original, so every reference field in the copy points at the *same* referent as the original's; a deep copy recurses, allocating a fresh referent per reference field, and terminates only where it reaches a type that needs no copy — which is why option 1 makes option 2 unnecessary rather than merely cheaper.

### Diagram

No diagram is assigned to this concept. The two failure forms differ only in which hop leaks, which a two-row table states more precisely than a picture, and the printed before/after totals below are the actual evidence; `../objects-equality-and-lifecycle/01-basics.md` carries **D-036** for `clone()` being shallow, which is the closest adjacent picture of the same one-hop/two-hop distinction.

### A concrete example

Form one. All five rules *look* satisfied — `final class`, three `private final` fields, no mutators — and the class is mutable in both directions at once.

```java
public final class PaymentRunLeaky {
    private final String runRef;
    private final Date approvedAt;          // mutable JDK type, stored directly
    private final long[] amountsMinor;      // arrays have no immutable form

    public PaymentRunLeaky(String runRef, Date approvedAt, long[] amountsMinor) {
        this.runRef = Objects.requireNonNull(runRef, "runRef must not be null");
        this.approvedAt = Objects.requireNonNull(approvedAt, "approvedAt must not be null");
        this.amountsMinor = Objects.requireNonNull(amountsMinor, "amountsMinor must not be null");
    }

    public String runRef() { return runRef; }
    public Date approvedAt() { return approvedAt; }
    public long[] amountsMinor() { return amountsMinor; }

    public long totalMinor() {
        long total = 0;
        for (long amount : amountsMinor) {
            total += amount;
        }
        return total;
    }
}
```

The sealed version, with the copy at both boundaries and at the right depth — one hop, because `Date` and `long[]` are one-hop mutable:

```java
public final class PaymentRunSealed {
    private final String runRef;
    private final Date approvedAt;
    private final long[] amountsMinor;

    public PaymentRunSealed(String runRef, Date approvedAt, long[] amountsMinor) {
        this.runRef = Objects.requireNonNull(runRef, "runRef must not be null");
        this.approvedAt = new Date(approvedAt.getTime());                         // copy in
        this.amountsMinor = Arrays.copyOf(amountsMinor, amountsMinor.length);     // copy in
    }

    public String runRef() { return runRef; }
    public Date approvedAt() { return new Date(approvedAt.getTime()); }           // copy out
    public long[] amountsMinor() { return Arrays.copyOf(amountsMinor, amountsMinor.length); }

    public long totalMinor() {
        long total = 0;
        for (long amount : amountsMinor) {
            total += amount;
        }
        return total;
    }
}
```

Measured — the caller keeps its `Date` and its array, mutates both, and additionally writes through both accessors:

```
approvedAt after construction = 1756000000000
totalMinor  after construction = 44000
approvedAt after caller's setTime = 1
totalMinor  after caller's writes  = 9999999
sealed approvedAt = 1756000000000
sealed totalMinor = 44000
```

The sign-off timestamp on a batch of approved bank withdrawals moved to epoch millisecond 1, and the run total went from 440.00 to 99,999.99, on an object with no setter anywhere and every field `final`.

Form two. Now the holder is correct and the leak is one hop down:

```java
public final class LedgerEntryMutable {
    private final String position;
    private long amountMinor;                      // the whole bug, in one non-final field

    public LedgerEntryMutable(String position, long amountMinor) {
        this.position = Objects.requireNonNull(position, "position must not be null");
        this.amountMinor = amountMinor;
    }

    public long amountMinor() { return amountMinor; }
    public void setAmountMinor(long amountMinor) { this.amountMinor = amountMinor; }

    @Override public String toString() { return position + ":" + amountMinor; }
}

public final class MovementHolder {
    private final List<LedgerEntryMutable> entries;

    public MovementHolder(List<LedgerEntryMutable> entries) {
        Objects.requireNonNull(entries, "entries must not be null");
        this.entries = List.copyOf(entries);       // genuinely immutable list
    }

    public List<LedgerEntryMutable> entries() { return entries; }

    public long totalMinor() {
        long total = 0;
        for (LedgerEntryMutable entry : entries) {
            total += entry.amountMinor();
        }
        return total;
    }
}
```

Measured:

```
entries=[CLIENT_CASH_AVAILABLE:-420, CLIENT_CASH_RESERVED:420] totalMinor=0
entries().add -> UnsupportedOperationException
entries=[CLIENT_CASH_AVAILABLE:-99999, CLIENT_CASH_RESERVED:420] totalMinor=-99579
```

Line 2 is the list keeping its promise: structural modification is impossible. Line 3 is `entries().get(0).setAmountMinor(-99_999L)`, and the double-entry invariant — the two positions summing to zero — is now false, in an object whose constructor could not have prevented it with any amount of `List.copyOf`. Making `LedgerEntryMutable` a `record LedgerEntry(String position, long amountMinor)` removes this failure mode entirely, because there is no second hop left.

### The gotcha

**Pitfall:** believing that because every field is `final`, the object is immutable. The wrong belief is that `final` is transitive. Symptom: a compliance audit shows a `PaymentRun`'s `approvedAt` changed after operator sign-off — the timestamp in the payout file does not match the timestamp in the audit trail — and there is no setter anywhere in the codebase, no `PaymentRun` method on any stack trace that could have done it, and no database update to blame. The write came from the *caller*, through a reference the constructor accepted and never copied, or through an accessor that handed the field's referent back. Fix: rule 4's copy-in and rule 5's copy-out from `02-immutability.md`, at the depth the field's type actually needs — and, where §2 and §3 make it possible, replacing the mutable field type outright, which is strictly better because it removes the obligation rather than discharging it.

**Insight:** the two forms have the same diagnostic. Call an accessor, call it again with no method on the object in between, and see whether the two answers agree. That test catches form one and form two identically, and it is the behavioural definition `02-immutability.md` §1 opened with, applied as a test rather than as a definition.

> **Definition.** An object is *shallowly* immutable when its own fields cannot be repointed but the objects they reference can change, and *deeply* immutable when nothing reachable from it can change; `final` and rule 4's copy each buy exactly one hop, so an immutable holder of mutable elements — a `List.copyOf` of settable `LedgerEntry` objects — is mutable, and the only two cures are element types that are themselves immutable or a genuine deep copy at every boundary crossing.

---

## 2. Mutable JDK types that force copies (2.3.7)

Five types in the standard library do most of the damage in real codebases, and they do it for four different reasons: one is obviously mutable, one mutates while you read it, one has no immutable form in the language at all, one has an immutable twin people forget to use, and one is mutable *invisibly*. The last is the dangerous one, because it produces wrong answers instead of exceptions.

### Why it exists

All five predate the design consensus they violate. `java.util.Date` and `Calendar` are Java 1.0 and 1.1, from an era when a mutable "value" was ordinary; `SimpleDateFormat` inherits its mutability from `DateFormat`, which caches a `Calendar` as a `protected` field so subclasses can reuse it. Arrays are mutable because they are a primitive of the language, defined in the JVM specification before any library existed to have an opinion. None of this is fixable without breaking compatibility, so the JDK's answer has been to ship immutable replacements alongside — `java.time` in Java 8, `List.of`/`List.copyOf` in Java 9/10 — and leave the old shapes in place forever.

### How it works

| Type | What is mutable about it | Immutable replacement | When you cannot replace it |
|---|---|---|---|
| `java.util.Date` | `setTime(long)` rewrites the instant in place; also `Cloneable` and `Serializable`, so it leaks by three routes | `java.time.Instant` (an instant) or `LocalDate` (a date) | Copy in **and** out with `new Date(d.getTime())`. Convert at the boundary: `d.toInstant()` inbound, `Date.from(instant)` outbound, keeping `Instant` in the field |
| `java.util.Calendar` | Every setter, **and** `get(int)` — see the source below. Its lazy-recompute fields are written during an ordinary read | `java.time.ZonedDateTime` | Never share one. Construct, read, discard, inside one method, on one thread |
| Arrays (`long[]`, `LedgerEntry[]`) | **No immutable form exists in Java.** `final long[]` is a fixed reference to a fully writable buffer | `List.of(...)` / `List.copyOf(...)`, or a record wrapping the values | `Arrays.copyOf(a, a.length)` in and out — the only defence. Deep-copy element by element if the elements are mutable (§1) |
| `java.util` collections (`ArrayList`, `HashMap`, `HashSet`) | Every structural mutator, on the collection the field points at | `List.copyOf`, `Map.copyOf`, `Set.copyOf` | `List.copyOf` at the boundary per `02-immutability.md` §5, which is free when the caller already passed an immutable list |
| `SimpleDateFormat` | **Invisibly**: it carries a mutable `Calendar` in `DateFormat`'s `protected` field and rewrites it on every `format` and `parse`. Documented as not synchronized | `java.time.format.DateTimeFormatter` | There is no safe sharing. `ThreadLocal<SimpleDateFormat>` or a fresh instance per call, both strictly worse than migrating |

`[SOURCE]` The `Calendar`-mutates-on-read claim, from `java.base/java/util/Calendar.java`, JDK 21.0.7:

```java
public int get(int field)
{
    complete();
    return internalGet(field);
}

protected void complete()
{
    if (!isTimeSet) {
        updateTime();
    }
    if (!areFieldsSet || !areAllFieldsSet) {
        computeFields(); // fills in unset fields
        areAllFieldsSet = areFieldsSet = true;
    }
}
```

Read it line by line. `get(int)` — the plainest read operation the class has — calls `complete()` before returning anything. `complete()` tests `isTimeSet`; if the millisecond instant has not been derived from the field values, `updateTime()` writes it. It then tests two more flags and, if the field array is stale or partial, calls `computeFields()`, which repopulates the entire `fields` array, and finally assigns both flags to `true`. So a single `cal.get(Calendar.DAY_OF_MONTH)` from two threads is two concurrent writers to `fields`, `isTimeSet`, `areFieldsSet` and `areAllFieldsSet`, with no synchronisation anywhere. That is why "I only read from the shared `Calendar`" is not a defence, and it is the mechanism underneath `SimpleDateFormat`'s thread-unsafety, since `DateFormat` declares `protected Calendar calendar;` and every `format` and `parse` drives it.

`[SOURCE]` And the JDK says the replacement out loud. From `java.base/java/text/SimpleDateFormat.java`, JDK 21.0.7:

```java
 * <h3><a id="synchronization">Synchronization</a></h3>
 *
 * <p>
 * Date formats are not synchronized.
 * It is recommended to create separate format instances for each thread.
 * If multiple threads access a format concurrently, it must be synchronized
 * externally.
 * @apiNote Consider using {@link java.time.format.DateTimeFormatter} as an
 * immutable and thread-safe alternative.
```

The `@apiNote`'s wording is the whole argument in one line: `DateTimeFormatter` is the alternative *because it is immutable*, and therefore thread-safe, and therefore shareable. Not because it is newer.

**Interview:** "Why is `SimpleDateFormat` not thread-safe, and what do you use instead?" The weak answer is "it's an old API, use `DateTimeFormatter`." The answer that lands names the mechanism and the direction of the fix: `SimpleDateFormat` keeps parse and format state in a mutable `Calendar` held in `DateFormat`'s `protected calendar` field, so two threads sharing one instance interleave writes to the same field array; the failure is *silent wrong output*, not an exception, which is why it survives testing. `DateTimeFormatter` is the replacement because it is immutable — it holds no per-call state at all, so one static instance is safe for every thread — and the javadoc's own `@apiNote` says so in exactly those terms.

`../date-and-time/02-date-and-time.md` owns `java.time` in full — the type-per-concept map, the conversion table to and from `Date`, and **D-080** for the `SimpleDateFormat` race, which is the closest adjacent picture to this section. `../arrays/01-basics.md` owns arrays, covariance and varargs.

### Diagram

No diagram is assigned to this concept. Five types with four different mutability mechanisms is a comparison, and the brief's own rule makes a table the correct form for it; the one part that genuinely needs a picture — the interleaving of two threads inside a shared `SimpleDateFormat` — is drawn as **D-080** in `../date-and-time/02-date-and-time.md`.

### A concrete example

The `static final SimpleDateFormat` that every codebase has, on the ledger-write path. 8 threads, 20,000 parses each, 160,000 total:

```java
private static final SimpleDateFormat LEDGER_DATE = new SimpleDateFormat("yyyy-MM-dd");

static void parseAcross(int threads, int perThread) throws Exception {
    ExecutorService pool = Executors.newFixedThreadPool(threads);
    Set<String> wrong = ConcurrentHashMap.newKeySet();
    AtomicInteger exceptions = new AtomicInteger();
    Set<String> kinds = ConcurrentHashMap.newKeySet();
    List<Future<?>> futures = new ArrayList<>();
    for (int t = 0; t < threads; t++) {
        futures.add(pool.submit(() -> {
            for (int i = 0; i < perThread; i++) {
                try {
                    Date parsed = LEDGER_DATE.parse("2026-08-29");
                    if (parsed.getTime() != 1_787_961_600_000L) {
                        wrong.add(String.valueOf(parsed.getTime()));
                    }
                } catch (ParseException | RuntimeException e) {
                    exceptions.incrementAndGet();
                    kinds.add(e.getClass().getName());
                }
            }
        }));
    }
    for (Future<?> f : futures) {
        f.get();
    }
    pool.shutdown();
    System.out.println("distinct WRONG parse results  = " + wrong.size());
    System.out.println("exceptions thrown             = " + exceptions.get() + " " + kinds);
}
```

Measured on JDK 21.0.7:

```
== 3. SimpleDateFormat shared across threads ==
distinct WRONG parse results  = 2325
exceptions thrown             = 3470 [java.lang.NumberFormatException, java.lang.ArrayIndexOutOfBoundsException]

== 4. DateTimeFormatter, same 160,000 parses ==
distinct WRONG parse results  = 0
exceptions thrown             = 0 []
```

Read the numbers carefully, because the exceptions are the *good* half. 3,470 calls threw `NumberFormatException` or `ArrayIndexOutOfBoundsException` — loud, traceable, alerting. **2,325 distinct wrong instants came back with no exception at all**, from a single input string that has exactly one correct answer. Every one of those is a ledger row dated to something other than 2026-08-29, written at up to 13,600 rows/sec, discovered by reconciliation weeks later. The `DateTimeFormatter` run is the same 160,000 parses through one shared static instance with zero of either, because there is no per-call state to corrupt.

### The gotcha

**Pitfall:** believing a `ThreadLocal<SimpleDateFormat>` makes the problem go away, so the type is fine after all. It does remove the race — each thread gets its own instance and no two threads touch one `Calendar`. What it does not remove is the cost: on a virtual-thread or high-churn platform-thread executor a `ThreadLocal` keyed per thread creates one formatter per thread and holds it until the thread dies, which is a per-thread retained object and, on very large thread counts, a leak shape rather than a cache. Symptom: heap dumps showing thousands of `SimpleDateFormat` instances rooted in `ThreadLocalMap`. Fix: `DateTimeFormatter`, one `static final` instance, no `ThreadLocal` at all — the immutable type needs no per-thread anything. `../objects-equality-and-lifecycle/03a-finalization-cleanup-and-leaks.md` owns the `ThreadLocal` retention shape.

> **Definition.** `Date`, `Calendar`, arrays, the `java.util` collections and `SimpleDateFormat` are the mutable JDK types that force a defensive copy on any class that stores them — `Date` through `setTime`, `Calendar` through both its setters and its lazily-recomputing `get`, arrays because Java provides no immutable array at all, the collections through their mutators, and `SimpleDateFormat` invisibly through the mutable `Calendar` it inherits from `DateFormat` — and in every one of the five cases the correct fix is not a better copy but an immutable replacement type.

---

## 3. Already-immutable building blocks (2.3.8)

The point of this section is not the list of seven types. It is the leverage: **a class every one of whose field types is on this list needs no copy-in and no copy-out at all.** Rules 4 and 5 become no-ops, not because you discharged the obligation carefully, but because the obligation never arose. Reaching that state is almost always cheaper than writing and maintaining the copies, and it is the single highest-value move in this whole file.

### Why it exists

The JDK's own immutable types are not immutable by accident; they are immutable so that they can be freely shared, cached and interned inside the library itself. `String` has to be immutable for the constant pool and for `substring` sharing to be sound; the wrappers have to be immutable for `Integer.valueOf`'s cache to be correct; `java.time` was designed immutable from the first line of JSR-310 precisely because `Date` and `Calendar` had demonstrated the alternative. Every one of these was a decision to pay allocation per change in exchange for never needing a lock or a copy, which is §4 and §5's trade-off made once, at the platform level, on your behalf.

### How it works

| Type | What makes it immutable | Value-based in JDK 21? | What that costs you | The QuizStakes field it is right for |
|---|---|---|---|---|
| `java.time` types (`Instant`, `LocalDate`, `ZonedDateTime`, `Duration`) | All fields `final` primitives or immutable types; every `plusX`/`withX` returns a new instance | **Yes** — annotated `@jdk.internal.ValueBased`, and the javadoc states "This class is immutable and thread-safe" | Do not synchronize on one, do not rely on identity, `==` is meaningless | `Application.submittedAt`, `Bonus.expiresAt`, `PaymentRun.approvedAt` |
| `String` | `private final byte[] value` never handed out; `private final byte coder` | No — not annotated, and identity is observable through interning | Nothing beyond `==` never being the right comparison | `IdempotencyKey.value`, `Restriction.reason`, `AgreementRef.documentId` |
| Wrappers (`Integer`, `Long`, `Boolean`, `Character`, `Byte`, `Short`, `Float`, `Double`) | Single `private final` primitive field | **Yes** — all eight annotated `@jdk.internal.ValueBased` | `==` compares identity and the cache makes it *look* like it compares value inside −128..127; never synchronize on one | Nothing directly — prefer a domain type over a bare wrapper field |
| `BigDecimal` | `final int scale`, `final long intCompact`, `final BigInteger intVal`; every operation returns a new instance | No — not annotated in JDK 21 | **`equals` sees scale** — see below | `Money.amount` |
| `BigInteger` | `final int signum`, `final int[] mag` — the array is never handed out | No — not annotated in JDK 21 | Arithmetic is O(digits), not O(1) | Nothing on a hot path; a running total in a reconciliation report |
| `UUID` | Two `final long` fields; javadoc: "an immutable universally unique identifier" | No — not annotated in JDK 21 | 16 bytes of payload and a 36-char `toString`; the string form is far dearer than the object | The wrapped value inside `ClientId`, `ApplicationId`, `AccountId`, `RoundId` |
| `Locale` | All fields `final`; `clone()` returns `super.clone()` with no mutable state to copy | No — not annotated in JDK 21 | Immutable *instance*, mutable *process-wide default* — see below | `Jurisdiction`'s formatting locale |

**Value-based, precisely.** `[RESEARCH]` Verified by grepping `@jdk.internal.ValueBased` across JDK 21.0.7's `lib/src.zip`: all eight wrappers and the `java.time` types carry it; `String`, `BigDecimal`, `BigInteger`, `UUID` and `Locale` do not. The annotation is the JDK's marker for a class whose instances have no meaningful identity — so the runtime is permitted to substitute one instance for an equal one, and a program that depends on identity (`==`, `synchronized` on the instance, identity-hash-based caching) is depending on something the platform has explicitly declined to promise. `../objects-equality-and-lifecycle/01-basics.md` owns value-based classes; `../wrappers-and-boxing/01-basics.md` owns the caches and the `==` boundary at 127/128.

**`BigDecimal` is immutable but `equals` sees scale.** Measured on JDK 21.0.7:

```
2.0.equals(2.00)      = false
2.0.compareTo(2.00)   = 0
hashCodes equal       = false
HashSet.contains(2.00)= false
```

`equals` compares unscaled value *and* scale, so `2.0` (unscaled 20, scale 1) and `2.00` (unscaled 200, scale 2) are unequal while `compareTo` returns 0. The consequence for an immutable `Money`: it is a perfectly safe map key — its hash cannot drift — but two `Money` values a human would call equal are not, unless the constructor normalises the scale. Hence `setScale(2, RoundingMode.UNNECESSARY)` in `02-immutability.md` §2's `Money.of`: normalisation in the factory is what makes `equals` mean what the domain means. `../numbers-and-money/02-numbers-and-money.md` owns `BigDecimal`, scale and `RoundingMode` in full.

**`Locale` is immutable; `Locale.setDefault` is a process-wide mutable global.** Measured on JDK 21.0.7:

```
default locale        = en_US
"ID-9001".toLowerCase() = id-9001
default locale        = tr
"ID-9001".toLowerCase() = ıd-9001
toLowerCase(Locale.ROOT) = id-9001
```

Under the Turkish locale, `toLowerCase()` maps `I` to the dotless lowercase Turkish i, so a lookup key derived from a document reference stops matching. Nothing about the `Locale` instance changed — every `Locale` object involved is immutable. What changed was the static default that the no-argument `toLowerCase()`, `toUpperCase()`, `String.format` and `DateTimeFormatter.ofPattern` all read, and `Locale.setDefault` is `public static synchronized void`, callable from any library on the classpath at any time. The lesson generalises past `Locale`: **the immutability of an instance says nothing about the mutability of a static that selects which instance is used.** The fix is always to pass the locale explicitly — `toLowerCase(Locale.ROOT)` for machine-facing keys — and never to rely on the default.

### Diagram

No diagram is assigned to this concept. Seven types compared across four dimensions is exactly the ≥3-item comparison the house rules require a table for, and the two honesty notes are proved by printed output rather than by a picture; `../objects-equality-and-lifecycle/01-basics.md` carries the value-based-class figure that is the nearest adjacent one.

### A concrete example

§1's leaking `PaymentRunLeaky`, rebuilt with every field type drawn from the table. Rules 4 and 5 both become no-ops.

```java
public final class PaymentRun {
    private final String runRef;                 // immutable
    private final Instant approvedAt;            // immutable, value-based
    private final List<WithdrawalId> itemIds;    // immutable list of immutable ids
    private final Money total;                   // immutable: BigDecimal + Currency enum

    public PaymentRun(String runRef, Instant approvedAt, List<WithdrawalId> itemIds, Money total) {
        this.runRef = Objects.requireNonNull(runRef, "runRef must not be null");
        this.approvedAt = Objects.requireNonNull(approvedAt, "approvedAt must not be null");
        Objects.requireNonNull(itemIds, "itemIds must not be null");
        this.itemIds = List.copyOf(itemIds);     // the ONLY copy left, and only because
                                                 // List is an interface the caller chose
        this.total = Objects.requireNonNull(total, "total must not be null");
    }

    public String runRef() { return runRef; }
    public Instant approvedAt() { return approvedAt; }        // no copy: Instant is immutable
    public List<WithdrawalId> itemIds() { return itemIds; }   // no copy: the list is immutable
    public Money total() { return total; }                    // no copy: Money is immutable
}
```

Four fields, four accessors, zero defensive copies on the way out, and exactly one on the way in — and that one survives only because `List` is an interface, so the caller could have handed in an `ArrayList`. Replace the parameter type with a record wrapping the ids and even that copy disappears. Compare against `PaymentRunSealed` in §1, which needed a `new Date(...)` and an `Arrays.copyOf` at four separate points and would need one more at every future accessor.

**`WithdrawalId` as a record.** The element type has to be immutable too, or §1's form-two leak reopens through the list. `record WithdrawalId(UUID value) {}` is the whole declaration: one field, an immutable type, implicitly `final`, implicitly `private final`, no mutator. `../records-and-sealed/01a-object-methods-sealed-and-fit.md` owns the generated members and the "when to reach for a record" decision; leaf 2.3.11 in `02b-records-jmm-and-builders.md` owns what a compact constructor still has to do when a component is *not* immutable.

### The gotcha

**Pitfall:** believing that because `String` is immutable, a `String`-typed field needs no thought. The immutability is real; the trap is that a `String` derived from a locale-sensitive operation is not a stable value. Symptom: an `IdempotencyKey` built with `reference.toLowerCase()` matches on the operator's machine and misses in production, or matches in the morning and misses after a library called `Locale.setDefault` during startup, producing a duplicate card withdrawal because the idempotency lookup found nothing. Fix: `toLowerCase(Locale.ROOT)` for every key, identifier, protocol token and status code — anywhere the string is read by a machine rather than a human.

> **Definition.** The `java.time` types, `String`, the eight wrappers, `BigDecimal`, `BigInteger`, `UUID` and `Locale` are the JDK's already-immutable building blocks, and their real value is compositional: a class whose every field type is drawn from that set needs neither a defensive copy in nor one out, because there is nothing reachable from it that anyone can change — subject to two edges, that `BigDecimal.equals` compares scale as well as value, and that an immutable `Locale` instance coexists with a mutable process-wide `Locale.setDefault` that silently changes what the no-argument `toLowerCase()` does.

---

## 4. The five benefits, each with its mechanism (2.3.9)

Five separate mechanisms, not five adjectives. Each one follows from immutability for a different reason, and an interview answer that names the reason rather than the adjective is the difference between "immutable objects are thread-safe" and a real explanation.

### Why it exists

Immutability is the only design constraint in Java that buys five unrelated guarantees from one decision. That is unusual enough to be worth enumerating, and the enumeration is also the answer to "why would you accept the allocation cost?" — §5's price is paid once, and these are the five things it buys.

### How it works

| Benefit | The mechanism it follows from | Where it pays in QuizStakes |
|---|---|---|
| Thread safety with no synchronisation | No write ever happens after publication, so there is no pair of operations for two threads to order | `Money` and `StakeSplit` crossing the 3,400/sec settlement burst with no lock |
| Safe map key | `hashCode` is a function of contents; contents are fixed for the object's lifetime, so the hash computed at insertion is the hash computed at every lookup for ever | `RestrictionKey(type, source)` as a `HashMap` key in `ClientRestrictions` |
| Safe caching and sharing | Two callers holding one instance cannot interfere, so one instance can serve all of them | one shared `Money.ZERO` across 2.8M/day stake reservations |
| No defensive copying by callers | The caller cannot be harmed by keeping the reference, so it need not copy on receipt | `BalanceView` handing the same `Money` to four downstream services |
| Failure atomicity | A method that cannot write cannot half-write; it either produces a whole new valid object or produces nothing | `Movement` under `LedgerImbalanceException` |

**Thread safety with no synchronisation.** A data race requires two conflicting accesses to the same location, at least one of them a write, unordered by happens-before. An immutable object has no write after construction, so no pair of accesses conflicts, so the race cannot be constructed and there is nothing to synchronize. This is why a `Money` can be handed from the 1,200/sec reservation path to the 3,400/sec settlement path with no lock, no `volatile` and no `AtomicReference`. The subtlety is *publication*: the object still has to become visible to the reading thread, and the JMM's `final`-field freeze is what makes even a racy publication of a fully-immutable object safe. That is leaf 2.3.13, owned by `02b-records-jmm-and-builders.md`, and guide 05 owns the memory model itself. Do not take the freeze for granted here; take the "no write to order" argument, which is the part this leaf is about.

**Safe map key.** A `HashMap` computes a key's hash once, at insertion, files the entry in the bucket that hash selects, and never recomputes it. If the key's hash later changes, the entry stays in its old bucket and lookups go to the new one, so the key can no longer find itself. Measured on JDK 21.0.7, with the leak from §1 — an immutable `List.copyOf` key whose *element* is mutable:

```
key.hashCode()                 = 1915670596
lookup before element mutation = PR-2026-08-29
key.hashCode()                 = 1915671175
lookup after  element mutation = null
map size / entry still present = 1 / [PR-2026-08-29]
```

Four lines that make the benefit concrete by removing it. The map still holds the value — `size()` is 1 and `values()` prints it — but `get(key)` with the *same key reference that inserted it* returns `null`, because `List.hashCode` folds its elements' hashes and one element's hash moved: `1915671175 − 1915670596 = 579`. An immutable key cannot do this. `../objects-equality-and-lifecycle/01b-equals-hashcode-and-object-methods.md` owns the `equals`/`hashCode` contract; guide 02 owns bucket layout and treeification.

**Safe caching and sharing.** `[NUM]` A shared instance is only safe if nobody can mutate it, so interning is a benefit immutability unlocks rather than an independent technique. The arithmetic, using the brief's layout rules — 12-byte header (8-byte mark word + 4-byte compressed class pointer), 4 bytes per reference field, size rounded up to a multiple of 8: `Money(BigDecimal amount, Currency currency)` is 12 + 4 + 4 = 20 bytes, rounded to **24 bytes**. Stake consumption is `min(BONUS_AVAILABLE, 10% of stake)`, so for the large majority of the 2.8M/day stake reservations whose client has no bonus, the bonus portion of the `StakeSplit` is a zero `Money`. Interning that one value saves 2.8M × 24 = **67.2 MB/day** of Eden churn, and at the 1,200/sec peak, 1,200 × 24 = **28.8 KB/sec**. `../objects-equality-and-lifecycle/05-internals-object-layout.md` owns the layout derivation; `../strings/01b-the-string-pool.md` owns interning's pathological form, and leaf 2.3.14 in `02b-records-jmm-and-builders.md` owns when interning is worth it.

**No defensive copying by callers.** This is the mirror of §5's cost, and it is the benefit nobody counts because it shows up as work that does not happen. When `BalanceView` returns a mutable `Date`, every careful caller must write `new Date(returned.getTime())` — and every careless one is a bug waiting. When it returns an `Instant`, no caller copies anything. Price it against `../cost-model/02-master-cost-table.md`: one avoided `new Date(...)` is an escaping small-object allocation at roughly 4 ns and 24 bytes, and it is avoided *once per caller per call*, so a value passed to four downstream services saves four copies rather than one. The producer paying one allocation to save N is the trade, and N is usually greater than one.

**Failure atomicity.** The one candidates cannot articulate, and the one interviewers like. A method that mutates its receiver field by field can throw partway through, leaving the receiver in a state that satisfies no invariant — and the caller that catches the exception now holds a corrupt object with no way to repair it. An immutable design cannot produce that state, because the only place fields are written is a constructor, and a constructor that throws produces no reference at all.

### Diagram

No diagram is assigned to this concept. Five mechanisms are a table plus one worked failure per row, and the two that genuinely need evidence — hash drift and failure atomicity — are proved above and below as printed output rather than as a picture; guide 05 owns the safe-publication figure that the thread-safety row leans on.

### A concrete example

Failure atomicity, both versions, complete. The mutable one writes `debitMinor` and `feeMinor`, validates, then writes `creditMinor`:

```java
public final class MovementMutable {
    private long debitMinor;
    private long creditMinor;
    private long feeMinor;

    public MovementMutable(long debitMinor, long creditMinor, long feeMinor) {
        this.debitMinor = debitMinor;
        this.creditMinor = creditMinor;
        this.feeMinor = feeMinor;
    }

    public void apply(long debitMinor, long creditMinor, long feeMinor) {
        this.debitMinor = debitMinor;
        this.feeMinor = feeMinor;
        if (debitMinor + creditMinor + feeMinor != 0) {
            throw new LedgerImbalanceException(
                "debit+credit+fee = " + (debitMinor + creditMinor + feeMinor));
        }
        this.creditMinor = creditMinor;
    }

    public boolean balances() { return debitMinor + creditMinor + feeMinor == 0; }
}

public final class MovementImmutable {
    private final long debitMinor;
    private final long creditMinor;
    private final long feeMinor;

    public MovementImmutable(long debitMinor, long creditMinor, long feeMinor) {
        if (debitMinor + creditMinor + feeMinor != 0) {
            throw new LedgerImbalanceException(
                "debit+credit+fee = " + (debitMinor + creditMinor + feeMinor));
        }
        this.debitMinor = debitMinor;
        this.creditMinor = creditMinor;
        this.feeMinor = feeMinor;
    }

    public MovementImmutable applied(long debitMinor, long creditMinor, long feeMinor) {
        return new MovementImmutable(debitMinor, creditMinor, feeMinor);
    }

    public boolean balances() { return debitMinor + creditMinor + feeMinor == 0; }
}
```

Measured on JDK 21.0.7, both starting balanced at `(-420, 420, 0)` and both handed the same unbalanced `(-500, 500, 7)`:

```
mutable   before: debit=-420 credit=420 fee=0  balances=true
mutable   threw : debit+credit+fee = 7
mutable   after : debit=-500 credit=420 fee=7  balances=false
immutable before: debit=-420 credit=420 fee=0  balances=true
immutable threw : debit+credit+fee = 7
immutable after : debit=-420 credit=420 fee=0  balances=true
```

Both threw the same exception with the same message. The mutable receiver is now `(-500, 420, 7)` — a combination that was never handed to any method, satisfies no invariant, and sums to `−500 + 420 + 7 = −73` rather than 0. The immutable receiver is untouched and still balances; the failed `applied` call produced no object at all. The caller of the mutable version has caught an exception and is holding a `Movement` it must now discard, and if that `Movement` was already published to the ledger writer, it cannot.

### The gotcha

**Pitfall:** believing "immutable" alone makes a shared object safe to publish, so no further thought is needed about threads. Immutability removes the *data race on the fields*. It does not by itself remove every question about when a second thread sees the object — that is the safe-publication question, and the reason it is usually answered in your favour is the JMM's `final`-field freeze, which is a specific guarantee with specific conditions, including that no reference to the object escaped its own constructor. Symptom: an "immutable" class that leaks `this` from its constructor to a listener registry and is observed by another thread with zero-valued fields. Fix: know the freeze's conditions. Leaf 2.3.13 in `02b-records-jmm-and-builders.md` owns them and owns the still-unsafe immutable that violates them; guide 05 owns the memory model.

> **Definition.** Immutability buys five independent guarantees from one decision — lock-free thread safety, because no write follows publication and there is nothing to order; a permanently valid `hashCode`, because contents cannot drift out of their bucket; safe caching and sharing, because two holders of one instance cannot interfere; no defensive copying by callers, because a retained reference cannot harm them; and failure atomicity, because the only place fields are written is a constructor and a constructor that throws yields no object.

---

## 5. The costs: allocation per change, and the `withX` idiom (2.3.10)

`[NUM]` Immutability has exactly one real cost — you allocate to change anything — and the mistake in both directions is refusing to do the arithmetic. "Allocations are slow" is folklore; "allocations are free" is the same folklore inverted. The number that decides it is **changes per second × object size**, and it decides differently for `Money` than for a growing payout buffer.

### Why it exists

There is no third option. A value that cannot be overwritten and must nevertheless be updated has to be a *new* value, and in Java a new value of reference type is a heap allocation. The `withX` idiom exists because Java has no language-level "copy with one field changed" — no `with` expression, no record update syntax in 21 — so the copy constructor has to be written out by hand, once per field.

### How it works

Price it from `../cost-model/02-master-cost-table.md`, which measured this exact question on this exact build:

- A **non-escaping** small-object allocation measured **0.30–0.56 ns**, at the harness floor, because C2's escape analysis proved the reference never left the method and scalar replacement removed the allocation outright. Turning off `-XX:+DoEscapeAnalysis` moved the same loop to **4.01 ns**, a `4.008 / 0.559 = 7.2×` jump, which is what proves the elimination was happening.
- An **escaping** small-object allocation measured **~4 ns**. That is a TLAB bump-pointer increment plus header initialisation, and it is the honest planning figure whenever the object is stored, returned or published.
- **Unverified:** C2 makes no documented guarantee about when escape analysis or scalar replacement fires, so the 0.56 ns figure is a statement about what the compiler did to that loop, not a property you can design against.

Now the arithmetic for a `Money` rebuilt once per stake reservation, at the 1,200/sec peak, with the 24-byte layout derived in §4:

| Quantity | Arithmetic | Result |
|---|---|---|
| Time cost, escaping | 1,200/sec × 4 ns | 4.8 µs/sec — 0.00048% of one core |
| Allocation volume | 1,200/sec × 24 bytes | 28.8 KB/sec |
| Daily volume | 2.8M/day × 24 bytes | 67.2 MB/day of Eden |

**The conclusion the numbers actually support:** at that rate the allocation is negligible and the readability is free. 4.8 microseconds per second of wall time is not a budget line, and 28.8 KB/sec is young-generation churn that a modern collector reclaims for essentially nothing. Anyone proposing a mutable `Money` to save this has not multiplied.

**Where the cost does bite:** when the *same* object is rebuilt many times inside one operation, so the multiplier is not the operation rate but the operation rate times the loop length. That is the `String`-concat-in-a-loop shape — build a 40-line payout audit block with `+=` and you allocate a `String` and a `byte[]` per line, at O(total length) per append, which is why `StringBuilder` exists. `../strings/02-performance-and-text.md` owns that measurement and `StringBuilder`'s growth policy in full.

### Diagram

No diagram is assigned to this concept. The cost is arithmetic — three multiplications and an allocation count — and arithmetic belongs in a table; `../cost-model/02-master-cost-table.md` carries the escape-analysis figure this section prices against and owns its picture.

### A concrete example

`[BUILD]` The `withX` idiom in full, on both a value type and an aggregate.

```java
public final class Money {
    private final BigDecimal amount;
    private final Currency currency;

    public Money(BigDecimal amount, Currency currency) {
        this.amount = Objects.requireNonNull(amount, "amount must not be null")
                             .setScale(2, RoundingMode.UNNECESSARY);
        this.currency = Objects.requireNonNull(currency, "currency must not be null");
    }

    public BigDecimal amount() { return amount; }
    public Currency currency() { return currency; }

    public Money withAmount(BigDecimal amount) { return new Money(amount, currency); }
    public Money withCurrency(Currency currency) { return new Money(amount, currency); }
}

public final class PaymentRun {
    private final String runRef;
    private final List<WithdrawalId> itemIds;
    private final String signedOffBy;

    public PaymentRun(String runRef, List<WithdrawalId> itemIds, String signedOffBy) {
        this.runRef = Objects.requireNonNull(runRef, "runRef must not be null");
        Objects.requireNonNull(itemIds, "itemIds must not be null");
        this.itemIds = List.copyOf(itemIds);
        this.signedOffBy = signedOffBy;                       // null until operator sign-off
    }

    public String runRef() { return runRef; }
    public List<WithdrawalId> itemIds() { return itemIds; }
    public String signedOffBy() { return signedOffBy; }

    public PaymentRun withItemAdded(WithdrawalId id) {
        List<WithdrawalId> next = new ArrayList<>(itemIds);
        next.add(Objects.requireNonNull(id, "id must not be null"));
        return new PaymentRun(runRef, next, signedOffBy);
    }

    public PaymentRun withSignedOffBy(String operatorRef) {
        return new PaymentRun(runRef, itemIds, operatorRef);
    }

    public PaymentRun withRunRef(String runRef) {
        return new PaymentRun(runRef, itemIds, signedOffBy);
    }
}
```

Two things go wrong with it, and both are why `02b-records-jmm-and-builders.md` owns the builder.

**N fields means N `withX` methods, and a combinatorial mess once callers need to change two at once.** Three fields gives three methods, and callers who want two changes chain two calls. Add a fourth field and you write a fourth method; add a requirement to change two fields *atomically with respect to validation* and no chain of single-field `withX` calls expresses it, because each link constructs and validates an intermediate that may not be legal. A `PaymentRun` whose invariant is "`signedOffBy` is non-null only if every item is approved" cannot be reached by `withItemAdded` then `withSignedOffBy` if the intermediate violates it. That is the argument for a builder: one mutable staging object, one validation, one construction.

**A `withX` chain allocates one intermediate per link.** Measured on JDK 21.0.7, with a counter in each constructor:

```
after construction, PaymentRun instances = 1
after a 3-link withX chain, instances    = 4
kept: PR-2026-08-30 [WD-9001, WD-9002] signedOffBy=OP-40
original untouched: PR-2026-08-29 [WD-9001] signedOffBy=null
same end state via one factory call, instances = 1
kept: PR-2026-08-30 [WD-9001, WD-9002] signedOffBy=OP-40
Money instances for a 2-link chain = 3 kept 3.33 USD
```

`run.withItemAdded(id).withSignedOffBy(ref).withRunRef(newRef)` constructed **four** `PaymentRun` objects to keep one — three of them garbage the instant the next link ran — plus three `ArrayList`/`List.copyOf` pairs for the item list, which for a 10,000-item run is three full array copies. The last line shows the same shape on `Money`: a two-link chain, three instances. The fix is either a builder or a single multi-argument factory, and the sixth line prices it: the identical end state through one constructor call is **one** instance. On a path called at 1,200/sec, a three-link chain is 3,600 wasted allocations/sec at 24 bytes each — 86.4 KB/sec — for nothing. Escape analysis may remove the intermediates when they do not escape, but each link's result is passed to the next method, so C2 has to inline the whole chain to see it, and that is a decision it makes no promise about.

### The gotcha

**When immutability is genuinely the wrong choice.** One shape, stated precisely: an object that is **large** and changes on **every** operation, so the copy cost is O(size) and the multiplier is the full operation count. Accumulating a banking-partner payout file — 7k bank withdrawals per day into a growing `byte[]`, one append per withdrawal — is exactly that shape. An immutable buffer copies n bytes on append number n, making the whole accumulation O(n²): at 7,000 appends of ~180 bytes each the file is `7,000 × 180 = 1,260,000 bytes ≈ 1.26 MB`, and an immutable accumulator copies `180 × (7,000 × 7,001 / 2) = 4,410,630,000 bytes ≈ 4.4 GB` to produce it, where a mutable one writes 1.26 MB. That is not a constant factor, it is a complexity class, and no amount of allocator speed fixes it.

That is why `StringBuilder` is mutable and `String` is not. Same data, two objects, two opposite decisions, and the decision was made on exactly this axis: `String` is shared, cached, used as a map key and hashed once, so it is immutable; `StringBuilder` is a private accumulator inside one method that is appended to and then discarded, so it is mutable. **The symmetry is the best one-line answer to "when would you not make it immutable": when the object is a private accumulator rather than a shared value — large, edited incrementally, and never handed to anyone until it is finished.** Build mutable locally, publish immutable — which is precisely the builder, and precisely why `02-immutability.md` §1 said an immutable `PaymentRun` should be built once from a mutable local list rather than mutated by copying.

**Pitfall:** reaching for `withX` on a collection-valued field in a loop. Symptom: a method that adds 200 approved withdrawals to a run by calling `withItemAdded` 200 times, producing 200 `PaymentRun` objects and 200 array copies of average length 100 — 20,000 element copies to build a 200-element list. Fix: accumulate into a local `ArrayList`, construct once. `../generics/02-in-anger.md` owns the signature shape for a factory that takes a `Collection<? extends WithdrawalId>` so callers are not forced to convert first.

> **Definition.** The cost of immutability is one allocation per change — measured on JDK 21.0.7 at ~4 ns and 24 bytes for a small escaping object, and at the harness floor when C2 can prove it does not escape — which is negligible when the multiplier is the operation rate (1,200/sec × 24 bytes = 28.8 KB/sec for `Money`) and decisive when the multiplier is operation rate times object size on every operation (a growing payout buffer, O(n²) in copies); the `withX` copy-constructor idiom is how "modification" is expressed, at the price of one method per field and one wasted intermediate per chain link, both of which are the argument for a builder.

---

## Pitfalls

### Every field is `final`, so the object is immutable

**Wrong**

```java
public final class PaymentRunLeaky {
    private final Date approvedAt;                 // final. never reassigned.
    private final long[] amountsMinor;             // final. never reassigned.

    public PaymentRunLeaky(Date approvedAt, long[] amountsMinor) {
        this.approvedAt = approvedAt;
        this.amountsMinor = amountsMinor;
    }

    public Date approvedAt() { return approvedAt; }
    public long[] amountsMinor() { return amountsMinor; }

    public long totalMinor() {
        long total = 0;
        for (long amount : amountsMinor) {
            total += amount;
        }
        return total;
    }
}
```

```
approvedAt after construction = 1756000000000
totalMinor  after construction = 44000
approvedAt after caller's setTime = 1
totalMinor  after caller's writes  = 9999999
```

The caller called `setTime(0L)` on the `Date` it passed in, wrote `amounts[0] = 9_999_999L` on the array it passed in, and wrote through both accessors. Sign-off time and run total both changed on an object with no setter.

**Right**

```java
public PaymentRunSealed(Date approvedAt, long[] amountsMinor) {
    this.approvedAt = new Date(approvedAt.getTime());                         // copy in
    this.amountsMinor = Arrays.copyOf(amountsMinor, amountsMinor.length);     // copy in
}

public Date approvedAt() { return new Date(approvedAt.getTime()); }           // copy out
public long[] amountsMinor() { return Arrays.copyOf(amountsMinor, amountsMinor.length); }
```

```
sealed approvedAt = 1756000000000
sealed totalMinor = 44000
```

Better still, per §3: make the fields `Instant` and `List<WithdrawalId>` and all four copies disappear, because there is nothing left to copy.

**Why people believe it:** `final` is the keyword the language offers for "cannot change", and it delivers on that promise exactly — for the variable. Every tutorial's examples are `private final int` and `private final String`, which happen to satisfy both readings because `int` has no interior and `String` is already immutable, so the gap between "the field cannot change" and "the object cannot change" never surfaces until the first `Date` or `long[]` field.

### `List.copyOf` makes the collection field safe, so the class is immutable

**Wrong**

```java
public final class MovementHolder {
    private final List<LedgerEntryMutable> entries;

    public MovementHolder(List<LedgerEntryMutable> entries) {
        this.entries = List.copyOf(entries);       // genuinely immutable list
    }

    public List<LedgerEntryMutable> entries() { return entries; }

    public long totalMinor() {
        long total = 0;
        for (LedgerEntryMutable entry : entries) {
            total += entry.amountMinor();
        }
        return total;
    }
}
```

```
entries=[CLIENT_CASH_AVAILABLE:-420, CLIENT_CASH_RESERVED:420] totalMinor=0
entries().add -> UnsupportedOperationException
entries=[CLIENT_CASH_AVAILABLE:-99999, CLIENT_CASH_RESERVED:420] totalMinor=-99579
```

`add` throws, as advertised — and `entries().get(0).setAmountMinor(-99_999L)` walked straight through it. The double-entry invariant is now false.

**Right**

```java
public record LedgerEntry(String position, long amountMinor) {
    public LedgerEntry {
        Objects.requireNonNull(position, "position must not be null");
    }
}

public final class Movement {
    private final List<LedgerEntry> entries;

    public Movement(List<LedgerEntry> entries) {
        Objects.requireNonNull(entries, "entries must not be null");
        this.entries = List.copyOf(entries);
    }

    public List<LedgerEntry> entries() { return entries; }

    public long totalMinor() {
        long total = 0;
        for (LedgerEntry entry : entries) {
            total += entry.amountMinor();
        }
        return total;
    }
}
```

The list is immutable *and* nothing in it can change, so the copy depth now matches the mutability depth — which is zero. `entries()` needs no wrapper and no copy.

**Why people believe it:** `List.copyOf` is the documented, correct, idiomatic fix for the collection-field leak, and it does exactly what it says. The slip is that "immutable list" is a claim about the list's structure — its size and which references occupy which slots — and never a claim about the objects those references point at. A test asserting `assertThrows(UnsupportedOperationException.class, () -> movement.entries().add(entry))` passes on the broken version, which is why the belief survives review.

### A `static final SimpleDateFormat` is fine because it is only ever read from

**Wrong**

```java
private static final SimpleDateFormat LEDGER_DATE = new SimpleDateFormat("yyyy-MM-dd");

static Date parseLedgerDate(String text) throws ParseException {
    return LEDGER_DATE.parse(text);        // called from every ledger-writer thread
}
```

160,000 parses of the single string `"2026-08-29"` across 8 threads, measured on JDK 21.0.7:

```
distinct WRONG parse results  = 2325
exceptions thrown             = 3470 [java.lang.NumberFormatException, java.lang.ArrayIndexOutOfBoundsException]
```

The 3,470 exceptions are the visible half. The 2,325 distinct wrong instants returned **without any exception** are ledger rows dated to something other than the input, at up to 13,600 rows/sec.

**Right**

```java
private static final DateTimeFormatter LEDGER_DATE = DateTimeFormatter.ISO_LOCAL_DATE;

static LocalDate parseLedgerDate(String text) {
    return LocalDate.parse(text, LEDGER_DATE);
}
```

The same 160,000 parses through the same single shared static instance:

```
distinct WRONG parse results  = 0
exceptions thrown             = 0 []
```

`DateTimeFormatter` holds no per-call state, so there is nothing for two threads to corrupt — the javadoc's `@apiNote` on `SimpleDateFormat` recommends it in exactly those words: "an immutable and thread-safe alternative."

**Why people believe it:** "read-only access needs no synchronisation" is a correct rule applied to a type that does not qualify. `parse` and `format` *look* like reads — they take a value and return a value, and neither is named `set` — but `DateFormat` declares `protected Calendar calendar;` and `Calendar.get(int)` itself calls `complete()`, which writes `isTimeSet`, `areFieldsSet`, `areAllFieldsSet` and the whole `fields` array. The mutation is two layers below the method you called, in a field you never touch, so nothing at the call site suggests it exists.

## Cheat sheet

| Question | Answer |
|---|---|
| What does `final` on a reference field guarantee? | The reference is never repointed. Nothing about the referent. |
| Copy depth rule | The copy-in depth must match the mutability depth. One-hop copy, two-hop mutability = mutable. |
| `List.copyOf` guarantees | Structure fixed, elements untouched. Immutable holder of mutable elements is mutable. |
| Two routes to deep immutability | (1) every field/element type already immutable — preferred; (2) genuine deep copy per boundary crossing |
| Mutable JDK types forcing copies | `Date`, `Calendar`, arrays, `java.util` collections, `SimpleDateFormat` |
| Arrays | No immutable array exists in Java. `Arrays.copyOf` in and out, or `List.of`/`List.copyOf` |
| `Calendar.get(int)` | Calls `complete()`, which writes `isTimeSet`, `areFieldsSet`, `areAllFieldsSet` and `fields[]`. A read mutates. |
| `SimpleDateFormat` shared, 160k parses / 8 threads | 2,325 distinct wrong results + 3,470 exceptions. `DateTimeFormatter`: 0 and 0 |
| Already-immutable blocks | `java.time`, `String`, 8 wrappers, `BigDecimal`, `BigInteger`, `UUID`, `Locale` |
| `@jdk.internal.ValueBased` in JDK 21 | Yes: 8 wrappers + `java.time`. No: `String`, `BigDecimal`, `BigInteger`, `UUID`, `Locale` |
| `BigDecimal` edge | `equals` compares scale: `2.0.equals(2.00)` is `false`, `compareTo` is `0`. Normalise in the factory |
| `Locale` edge | Instance immutable; `Locale.setDefault` is a process-wide mutable global. Under `tr`, `"ID".toLowerCase()` yields a dotless i |
| The five benefits | no-lock thread safety · stable `hashCode` · safe caching/sharing · callers need no copy · failure atomicity |
| Failure atomicity, measured | mutable `apply` throws leaving `(-500, 420, 7)`, `balances=false`; immutable leaves `(-420, 420, 0)` intact |
| `Money` size | 12-byte header + 4 + 4 = 20 → **24 bytes** (8-aligned) |
| Allocation cost, JDK 21.0.7 | escaping ~4 ns; non-escaping 0.30–0.56 ns (eliminated, no guarantee) |
| `Money` at 1,200/sec | 4.8 µs/sec, 28.8 KB/sec, 67.2 MB/day. Negligible. |
| `withX` chain cost, measured | 3-link chain = 4 `PaymentRun` instances; one factory call = 1 |
| `withX` limits | N fields = N methods; no atomic multi-field change; one intermediate per link → use a builder |
| When NOT to be immutable | Large object changing on every operation. Growing payout `byte[]` is O(n²) in copies. Hence `StringBuilder` |

## Self-test

**Q1.** A `PaymentRun` is `final`, has three `private final` fields, and no method whose name begins with `set`. An audit shows its `approvedAt` changed after operator sign-off. Where is the bug, and what are the two candidate fixes?

<details><summary>Answer</summary>

`approvedAt` is a `java.util.Date`, which has a live `setTime(long)`. `final` fixes the reference, not the referent, so somebody who holds the same `Date` object rewrote it in place. There are two routes in: the constructor stored the caller's `Date` without copying, so the caller still holds it; and the accessor returns the field, so any caller can obtain it. Both must be closed. Fix one, minimal: `this.approvedAt = new Date(approvedAt.getTime())` in the constructor and `return new Date(approvedAt.getTime())` in the accessor — a one-hop copy, which is the right depth because `Date` is one-hop mutable. Fix two, better: change the field type to `java.time.Instant`, which is immutable and value-based, converting at the boundary with `d.toInstant()` and `Date.from(instant)`. Fix two is strictly preferable because it removes the obligation rather than discharging it — every future accessor is automatically correct, whereas fix one has to be remembered again each time a method is added.

</details>

**Q2.** `Movement` stores `List.copyOf(entries)` and returns the field directly. `movement.entries().add(x)` throws. Is `Movement` immutable?

<details><summary>Answer</summary>

Not necessarily — it depends entirely on `LedgerEntry`. `List.copyOf` gives an immutable *structure*: the size is fixed and no slot can be repointed, so `add`, `remove`, `set` and `clear` all throw. It copies references, not referents, so it says nothing about the objects in the slots. If `LedgerEntry` has a settable field, `movement.entries().get(0).setAmountMinor(-99_999L)` changes what `movement.totalMinor()` reports, and measured that took the double-entry total from 0 to −99,579. This is the "immutable holder of mutable elements" shape, and the giveaway is that the standard test — `assertThrows(UnsupportedOperationException.class, () -> movement.entries().add(x))` — passes on the broken version. The rule: the copy-in depth must match the mutability depth. Making `LedgerEntry` a record with only immutable components reduces the mutability depth to zero, after which any copy depth suffices.

</details>

**Q3.** Why is `SimpleDateFormat` unsafe to share even if every caller only ever calls `parse`, never `format` and never a setter?

<details><summary>Answer</summary>

Because `parse` is not a read at the level that matters. `DateFormat` declares `protected Calendar calendar;` and `SimpleDateFormat` drives that shared instance through every `parse` and `format` call. And `Calendar` itself mutates during reads: `Calendar.get(int)` calls `complete()`, which writes `isTimeSet` via `updateTime()`, then writes the entire `fields` array via `computeFields()`, then assigns `areAllFieldsSet = areFieldsSet = true`. So two threads calling `parse` on one `SimpleDateFormat` are two concurrent writers to the same field array with no synchronisation. Measured on JDK 21.0.7, 8 threads parsing the same string 20,000 times each produced 3,470 exceptions and — worse — 2,325 distinct wrong instants returned with no exception. The javadoc's `@apiNote` names the fix: `DateTimeFormatter`, "an immutable and thread-safe alternative." Immutable is the reason; newer is not.

</details>

**Q4.** `Locale` is immutable and every field is `final`. Why can `"ID-9001".toLowerCase()` still return different strings at different times in one JVM?

<details><summary>Answer</summary>

Because the no-argument `toLowerCase()` reads `Locale.getDefault()`, and `Locale.setDefault(Locale)` is a `public static synchronized void` that any library on the classpath can call at any point, including during startup. The `Locale` *instances* are all immutable — nothing about any one object changed. What changed is the static that selects which instance is used. Measured: under `en_US`, `"ID-9001".toLowerCase()` yields `id-9001`; after `Locale.setDefault(Locale.forLanguageTag("tr"))` the same call yields the Turkish dotless lowercase i in the first position, because Turkish maps uppercase I to a dotless form. The general lesson is that an instance's immutability says nothing about the mutability of a static that chooses the instance. The fix is to pass the locale explicitly — `toLowerCase(Locale.ROOT)` for every machine-read key, identifier, protocol token and status code.

</details>

**Q5.** Explain failure atomicity in terms of mechanism, not adjectives, and give the case where it matters.

<details><summary>Answer</summary>

A mutable method writes its receiver's fields one at a time. If it throws between two of those writes, the receiver is left in a state that was never a legal state and satisfies no invariant, and the caller that caught the exception now holds a corrupt object it cannot repair. An immutable design cannot produce that state, because the only place fields are written is a constructor, and a constructor that throws yields no reference at all — the caller either gets a whole valid object or gets an exception and its original object untouched. Measured: `MovementMutable.apply(-500, 500, 7)` writes `debitMinor` and `feeMinor`, validates, throws `LedgerImbalanceException`, and leaves `(-500, 420, 7)` with `balances=false` — a combination handed to no method. `MovementImmutable.applied` with the same arguments throws from the constructor and leaves the original `(-420, 420, 0)` intact, still balancing. It matters most where the corrupt object has already been published: on the 230/sec sustained ledger-write path a half-written `Movement` already handed to the writer cannot be recalled.

</details>

**Q6.** A colleague wants a mutable `Money` "because immutability allocates on every stake reservation." Answer them with arithmetic.

<details><summary>Answer</summary>

`Money(BigDecimal, Currency)` is a 12-byte header plus two 4-byte compressed-oop fields, 20 bytes rounded up to 24 under 8-byte alignment. Stake reservations peak at 1,200/sec and run at 2.8M/day. On JDK 21.0.7 an escaping small-object allocation measured ~4 ns, so: 1,200 × 4 ns = 4.8 µs/sec, which is 0.00048% of one core-second; 1,200 × 24 = 28.8 KB/sec of Eden; 2.8M × 24 = 67.2 MB/day. Young-generation churn at 28.8 KB/sec is not a budget line, so the mutable rewrite buys nothing measurable and gives up lock-free sharing, a stable `hashCode`, and failure atomicity. Where the argument *would* have merit is a different shape: the same object rebuilt many times inside one operation. A three-link `withX` chain measured four `PaymentRun` instances to keep one, and a 200-iteration `withItemAdded` loop copies the item array 200 times — that is what a builder or a single multi-argument factory fixes, and the measured comparison is 4 instances against 1 for the identical end state.

</details>

**Q7.** When is immutability the wrong choice? Give the shape and the JDK's own example.

<details><summary>Answer</summary>

When the object is large and changes on every operation, so the copy is O(size) and happens once per operation, making the whole accumulation O(n²). Accumulating a banking-partner payout file is exactly that: 7k bank withdrawals per day appended to a growing buffer at ~180 bytes each. An immutable buffer copies n bytes on append n, so producing a `7,000 × 180 = 1.26 MB` file involves `180 × (7,000 × 7,001 / 2) ≈ 4.4 GB` of copying, against 1.26 MB for a mutable one. That is a complexity class, not a constant factor, and no allocator speed fixes it. The JDK made both decisions deliberately on the same data: `String` is shared, cached, hashed once and used as a map key, so it is immutable; `StringBuilder` is a private accumulator inside one method, appended to and then discarded, so it is mutable. The general rule that falls out: **build mutable locally, publish immutable** — which is precisely what a builder is, and why an immutable `PaymentRun` should be constructed once from a mutable local list rather than mutated by copying.

</details>

## Open questions

- **Unverified:** C2's escape-analysis and scalar-replacement heuristics are not specified anywhere and the JVM makes no documented guarantee about when either applies, so the 0.30–0.56 ns non-escaping allocation figure quoted in §5 is a statement about what the compiler did to that specific loop rather than a property to design against. What would settle it: nothing available — the behaviour is deliberately unspecified. `-XX:+PrintEscapeAnalysis` on a fastdebug build plus `-XX:+PrintEliminateAllocations` would show what C2 decided for a *given* method, which is diagnostic, not a guarantee.
- **Unverified:** whether the intermediates in a `withX` chain such as `run.withItemAdded(id).withSignedOffBy(ref).withRunRef(newRef)` are ever scalar-replaced in practice. Each link's result is passed to the next method, so C2 would have to inline the whole chain to prove non-escape, and the measured instance count (4) came from a constructor-side counter, which itself makes the allocation observable and therefore prevents elimination. What would settle it: a JMH benchmark with `-prof gc` comparing chain and single-factory forms with no counter present.

---

**Leaves covered:** 2.3.6, 2.3.7, 2.3.8, 2.3.9, 2.3.10 (5 leaves)
**Leaves deferred:** none
**Diagrams included:** none
**Target version:** Java 21 LTS
**Lines:** 882
