# 03 Java Core — Version history, Java 1.0–17 — INTERNALS (§3.17)

**Target version: Java 21 LTS.** | **Part 3 of 5** | [Index](../00-index.md)
Previous: [The class file format](03a-internals-class-file-format.md) · Next: [Version history, Java 18 onward](04a-internals-version-history-18-onward.md)

This half runs Java 1.0 through Java 17 LTS, where the classic language surface stabilised — sealed classes final, `strictfp` retired, floating point always strict. Java 18 begins the cleanup-and-defaults era (UTF-8 by default, finalization deprecated for removal, Security Manager on its way out) and is covered in [version history, Java 18 onward](04a-internals-version-history-18-onward.md).

## The release train as three eras

Half the Java folklore an interviewer tests you on was true once. `substring` really did share its backing array; the string pool really did live in PermGen; `+` really did compile to a `StringBuilder` chain. Someone learned that, wrote it down, and the blog outlived the behaviour. Dating a claim separates "I read that somewhere" from "that changed in 7u6, and here is what replaced it."

**Why it exists.** Java's compatibility promise means old behaviour is rarely *removed*; it is superseded. The old form stays legal, keeps compiling, and keeps ranking in search results, so nothing expires the folklore but you.

**How it works.** Three eras, each with a different change rhythm — and a different failure mode for your memory.

| Era | Releases | Rhythm | What changed | Your memory's failure mode |
|---|---|---|---|---|
| Substrate fixed | 1.0–1.4 (1996–2002) | 2–3 years, ad hoc | Primitives, `Object`, the class file, dispatch, `assert` (1.4), regex (1.4) | You assume these are eternal. Mostly they are — that is why the rest of this guide describes them without version tags |
| Type machinery grows | 5–8 (2004–2014) | 2–3 years, one huge feature each | Generics, enums, annotations (5); try-with-resources, `invokedynamic` (7); lambdas, streams, `java.time` (8) | You attribute anything modern-feeling to 8 |
| Six-month train | 9–25 (2017–2025) | 6 months, preview→final increments | Modules, compact strings, `var`, records, sealed types, pattern matching, virtual threads | You attribute finalisation to the preview release, or the reverse |

The train also introduced the **preview lifecycle**: a language feature ships behind `--enable-preview`, may re-preview once or four times, and only then finalises. Records previewed in 14 and 15 and finalised in 16. Pattern matching for `switch` previewed in 17, 18, 19 and 20 and finalised in 21. Flexible constructor bodies previewed in 22, 23 and 24 and finalised in 25. "When did X land" has two answers, and interviewers usually want the second.

LTS releases are 8, 11, 17, 21 and 25 (Java 21 GA 19 September 2023; Java 25 GA 16 September 2025). Non-LTS releases 22 (19 March 2024), 23 (17 September 2024) and 24 (18 March 2025) are already end-of-life, which is exactly why their features feel unfamiliar even when they are final.

The third era's later releases — 18 through 25, plus the announced-not-landed direction — are enumerated in [version history, Java 18 onward](04a-internals-version-history-18-onward.md). This era table is the shared frame for both halves; that file recaps it in three lines rather than repeating it.

```java
// Verify at runtime rather than trusting a memory. Runs on JDK 21.
static String era() {
    int feature = Runtime.version().feature();
    return feature <= 4 ? "substrate era" : feature <= 8 ? "type-machinery era" : "six-month train";
}
```

**Gotcha:** `Runtime.version().feature()` exists only since Java 10 (on 9 it is `major()`), and `System.getProperty("java.version")` returns `"1.8.0_402"` on 8 but `"21.0.2"` on 21 — string-parsing it is the classic build-script bug.

> **Definition.** Java's version history is a compatibility-preserving accretion, so almost every retired behaviour still has live documentation describing it as current; dating a claim to its release is the only way to tell the two apart.

## Release by release

### Java 1.0–1.4 — the substrate (3.17.1)

The parts of this guide with no version tag were fixed here: the eight primitives, two's complement, IEEE 754, `Object`'s methods, single inheritance with interfaces, checked exceptions, the class file format. Java 1.4 added `assert` (disabled at runtime unless `-ea`) and `java.util.regex`. The synchronised legacy collections — `Vector`, `Hashtable`, `StringBuffer` — date from 1.0 and are still in `java.base`, uncontended-lock-cheap but never the right default.

```java
// Java 1.4 vintage: Hashtable-backed restriction lookup, no generics, synchronized on every access.
final class LegacyClientRestrictions {
    private final Hashtable restrictionsByType = new Hashtable();
    void add(String restrictionType, String source) { restrictionsByType.put(restrictionType, source); }
    String sourceOf(String restrictionType) { return (String) restrictionsByType.get(restrictionType); }
}

static String auditLine(String statusCode, long entryId) {          // StringBuffer, Java 1.0
    StringBuffer line = new StringBuffer(48);
    line.append(statusCode).append(' ').append(entryId);
    return line.toString();
}

static void checkSplit(StakeSplit split, Money stake) {              // assert, Java 1.4
    assert split.bonusPortion().amount().add(split.cashPortion().amount())
                .compareTo(stake.amount()) == 0 : "StakeSplit must sum to the stake";
}
```

**Pitfall:** `assert` is a no-op unless the JVM is started with `-ea`. A `StakeSplit` invariant guarded only by `assert` is unguarded in production. Ledger invariants belong in an `if` that throws `LedgerImbalanceException`.

### Java 5 — the type machinery (3.17.2)

Released 2004, and the single largest language delta ever. Generics (with erasure, so `List<Money>` and `List<Restriction>` share a class at runtime), `enum`, autoboxing/unboxing, varargs, annotations, the enhanced `for`, `static import`, covariant return types, `java.util.concurrent`, `Scanner`, and `StringBuilder` as the unsynchronised `StringBuffer`.

```java
enum RestrictionType { DEPOSIT_BLOCKED, STAKE_BLOCKED, WITHDRAWAL_BLOCKED, SELF_EXCLUDED }

final class ClientRestrictions {
    private final EnumMap<RestrictionType, Restriction> active = new EnumMap<>(RestrictionType.class);

    void add(Restriction restriction) { active.put(restriction.type(), restriction); }

    Restriction lookup(RestrictionType type) { return active.get(type); }   // no cast
}

static Money sum(Money[] parts) {                 // the array form varargs desugars to, Java 5
    BigDecimal total = BigDecimal.ZERO;
    for (Money part : parts) { total = total.add(part.amount()); }    // enhanced for, Java 5
    return new Money(total, Currency.getInstance("GBP"));
}

static Money netOf(List<Movement> movements) {                        // enhanced for over a generic List
    BigDecimal total = BigDecimal.ZERO;
    for (Movement movement : movements) { total = total.add(movement.signedAmount()); }
    return new Money(total, Currency.getInstance("GBP"));
}
```

**Gotcha:** varargs allocate an array per call. At 2.8M stake reservations a day, `Money.sum(bonus, cash)` on the hot path is 2.8M throwaway `Money[2]` allocations — cheap individually, visible in an allocation profile.

> **Definition.** Java 5 added compile-time type machinery over an unchanged runtime; erasure is the price paid for that, and every generics surprise later in this guide traces back to it.

### Java 6 — library polish (3.17.3)

Almost no language change. The one rule worth knowing: `@Override` became legal on a method implementing an *interface* method, not just overriding a class method. Code compiled for 5 that annotates an interface implementation fails on 5 and compiles on 6+.

> **Definition.** Java 6 widened `@Override` to interface implementations and otherwise left the language alone.

### Java 7 — Project Coin and `invokedynamic` (3.17.4) `[RESEARCH]`

The diamond operator `<>`, `String` in `switch`, try-with-resources, multi-catch, more precise rethrow, binary literals and numeric underscores, `java.util.Objects`, and the `invokedynamic` bytecode (unused by `javac` in 7 — it existed for JRuby and other guests, and Java itself only used it from 8 onward for lambdas). Two runtime changes that generate most of the folklore in this file: interned strings moved out of PermGen into the main heap (JDK-6962931), and `String` lost its `offset`/`count` fields in 7u6 (JDK-6924259), so `substring` copies.

```java
static final int  RESTRICTION_MASK     = 0b0000_1011;        // binary literal + underscores, Java 7
static final long LEDGER_ROWS_PER_YEAR = 7_200_000_000L;

static void writePayoutFile(PaymentRun run, Path target) {
    try (BufferedWriter writer = Files.newBufferedWriter(target)) {              // try-with-resources
        for (WithdrawalTransaction withdrawal : run.withdrawals()) {
            writer.write(withdrawal.reference());
            writer.newLine();
        }
    } catch (IOException cause) {
        throw new UncheckedIOException("PaymentRun " + run.id() + " payout file failed", cause);
    }
}

static void reserve(FundsLedger ledger, Reservation reservation) {
    try {
        ledger.reserveStake(reservation);
    } catch (InsufficientFundsException | RestrictedActionException failure) {   // multi-catch
        auditRejection(reservation, failure);
    }
}
```

**Gotcha:** `String` in `switch` compiles to a `hashCode` lookupswitch plus an `equals` guard, not a single comparison — so a `switch` on `"DEP-301 CAPTURED"` is fast but never null-safe. A null selector throws `NullPointerException` in 7 and still does in 21.

> **Definition.** Java 7 added syntactic relief plus `invokedynamic`, and quietly reversed two `String` implementation decisions that outlived their documentation by a decade.

### Java 8 — lambdas and the functional library (3.17.5) `[RESEARCH]`

Lambdas and method references, `default` and `static` interface methods, the stream API, `Optional`, `java.time`, repeatable annotations, type annotations, `Base64`, `StampedLock`, `LongAdder`, and — on the runtime side — the removal of PermGen in favour of Metaspace (JEP 122).

```java
// BonusService: expiry is 30 days from grant, computed with java.time instead of java.util.Date.
static Instant expiryOf(Instant grantedAt) { return grantedAt.plus(Duration.ofDays(30)); }

static Optional<Restriction> selfExclusion(ClientRestrictions restrictions) {
    return Optional.ofNullable(restrictions.lookup(RestrictionType.SELF_EXCLUDED));
}
```

**Gotcha:** `Optional` was designed as a stream return type, not a field type. It is not `Serializable`, and an `Optional<Restriction>` field on a `Restriction` aggregate is *Effective Java*'s Item 55: *Return optionals judiciously* being ignored.

> **Definition.** Java 8 added behaviour-as-data to the language and finished PermGen's removal; it is the release most modern features are wrongly attributed to.

### Java 9 — modules, compact strings, indified concat (3.17.6) `[RESEARCH]`

JEP 261 the module system, `List.of`/`Set.of`/`Map.of`, `private` interface methods, compact strings (JEP 254), indified string concatenation (JEP 280), `java.lang.ref.Cleaner`, `StackWalker`, try-with-resources over an effectively final variable, `Optional.stream()`, the diamond with anonymous classes, and deprecation of the boxed-primitive constructors.

```java
static final List<RestrictionType> ONBOARDING_BLOCKS =
        List.of(RestrictionType.STAKE_BLOCKED, RestrictionType.DEPOSIT_BLOCKED);   // immutable, null-hostile
```

**Gotcha:** `List.of` rejects nulls and returns a genuinely immutable list, unlike `Arrays.asList` (fixed-size but mutable, null-tolerant) and unlike `Collections.unmodifiableList` (a view over a still-mutable backing list). Three different "immutable" and only one of them is.

> **Definition.** Java 9 changed how the platform is packaged (modules) and how strings are stored and concatenated, making it the highest-density source of stale claims in this guide.

### Java 10 — `var` and app CDS (3.17.7)

Local-variable type inference (`var`, JEP 286), `List.copyOf`/`Set.copyOf`/`Map.copyOf`, `Optional.orElseThrow()` as the readable alias for `get()`, and application class-data sharing (JEP 310). `var` is a *reserved type name*, not a keyword: a variable or method may still be called `var`.

> **Definition.** `var` infers the declared type of a local from its initialiser at compile time; the bytecode is identical to writing the type out.

### Java 11 (LTS) — nestmates and the HTTP client (3.17.8) `[RESEARCH]`

`String.isBlank`/`lines`/`strip`/`stripLeading`/`stripTrailing`/`repeat`, `Files.readString`/`writeString`, the standard `java.net.http.HttpClient` (JEP 321), nest-based access control (JEP 181), single-file source launch (JEP 330), `Collection.toArray(IntFunction)`, and the removal of the bundled Java EE and CORBA modules (JEP 320) — the release that broke every build depending on `javax.xml.bind`.

```java
static boolean addressUsable(String submittedAddressLine) {
    return !submittedAddressLine.isBlank();       // Java 11: isBlank, unlike isEmpty, treats "   " as blank
}

static String padReference(String reference, int width) {
    return reference + " ".repeat(Math.max(0, width - reference.length()));   // Java 11: repeat
}

static String readPayoutFile(Path partnerFile) throws IOException {
    return Files.readString(partnerFile);   // Java 11, UTF-8 always — JEP 400 is in 04a-internals-version-history-18-onward.md
}
```

**Pitfall:** believing inner-class access to a private outer member goes through synthetic `access$000` bridge methods. True through Java 10. JEP 181 (Java 11) introduced the `NestHost`/`NestMembers` class-file attributes, so nestmates access each other's private members directly and `javac` stops generating the bridges. `javap -p` on a Java 21 nested class shows no `access$` methods. Mechanism in [nested classes](../inheritance-and-dispatch/04-internals-nested-classes.md).

### Java 12–13 — preview machinery arrives (3.17.9) `[RESEARCH]`

Java 12: `String.indent`, `String.transform`, `Files.mismatch`, switch *expressions* as a first preview (JEP 325), default CDS archives. Java 13: text blocks as a first preview (JEP 355), switch expressions re-previewed with `yield` replacing `break value` (JEP 354), and a small `String` implementation change — a private `hashIsZero` byte field (JDK-8221836) so that a string whose hash genuinely is zero stops recomputing it on every `hashCode()` call. The field costs nothing, fitting into existing object padding.

**Insight:** `hashIsZero` is the visible trace of `String`'s hash cache being a *non-volatile* benign data race — two threads may both compute the hash, and both write the same value. Detail in [`String` internals](../strings/03-internals-string.md).

### Java 14 — switch expressions final, records preview (3.17.10)

Switch expressions finalised (JEP 361), records as a first preview (JEP 359), helpful `NullPointerException` messages (JEP 358, off by default behind `-XX:+ShowCodeDetailsInExceptionMessages`), pattern matching for `instanceof` as a first preview (JEP 305), and `Object.finalize` further discouraged in its javadoc.

> **Definition.** Java 14 is where the preview pipeline started delivering: one feature finalised, three entering.

### Java 15 — text blocks final, helpful NPEs on (3.17.11) `[RESEARCH]`

Text blocks finalised (JEP 378), sealed classes as a first preview (JEP 360), `String.stripIndent`/`translateEscapes`/`formatted` added as the text-block support methods, biased locking disabled and deprecated (JEP 374), and — the detail people misremember — `ShowCodeDetailsInExceptionMessages` flipped to **true** by default (JDK-8233014).

```java
// Java 15+ default output for a null wallet.stakeable():
// Cannot invoke "Money.amount()" because the return value of
// "Wallet.stakeable()" is null
static BigDecimal stakeableAmount(Wallet wallet) {
    return wallet.stakeable().amount();
}
```

**Pitfall:** believing helpful NPE messages need a flag. They needed one in 14 only; they are on by default from 15. The security caveat is real, though — the message names your expressions, so echoing an NPE message into an HTTP response leaks internal structure.

### Java 16 — records final, inner statics allowed (3.17.12) `[RESEARCH]`

Records finalised (JEP 395), pattern matching for `instanceof` finalised (JEP 394), strong encapsulation of JDK internals **by default** (JEP 396), the boxed-primitive constructors terminally deprecated (JEP 390's follow-through), `Stream.toList()`, and — carried in the records JEP — inner (non-static nested) classes may now declare `static` members.

```java
final class BalanceView {
    List<Position> positions(FundsLedger ledger, AccountId accountId) {
        return ledger.positionsFor(accountId).stream().filter(Position::nonZero)
                     .toList();                  // Java 16; unmodifiable, unlike Collectors.toList()
    }

    class AuditTrail {                            // inner class with a static member: Java 16+, illegal in 15
        static final int MAX_ROWS = 500;
        List<StatusCode> rows() { return List.of(); }
    }
}

static Money of(String amount) { return new Money(new BigDecimal(amount), Currency.getInstance("GBP")); }
static Integer attempts(int count) { return Integer.valueOf(count); }   // not new Integer — deprecated in 16
```

**Pitfall:** believing inner classes cannot declare static members. True through Java 15, where a `static final int` inside a non-static nested class was a compile error unless it was a constant variable. Allowed since Java 16.

### Java 17 (LTS) — sealed classes, `strictfp` retired (3.17.13) `[RESEARCH]`

Sealed classes finalised (JEP 409), always-strict floating-point semantics restored (JEP 306), the `java.util.random.RandomGenerator` interface family (JEP 356), the Security Manager deprecated for removal (JEP 411), `Map.Entry.copyOf`, and `--illegal-access` removed entirely (JEP 403) so the 16 default becomes non-negotiable.

```java
sealed interface Verdict permits DocumentVerdict, ScreeningVerdict, ReviewVerdict, WealthVerdict {}

record DocumentVerdict(StatusCode code, boolean referred) implements Verdict {}
record ScreeningVerdict(StatusCode code, boolean prohibited) implements Verdict {}
record ReviewVerdict(StatusCode code, String operatorId) implements Verdict {}
record WealthVerdict(StatusCode code, Money declaredIncome) implements Verdict {}
```

> **Definition.** Java 17 closed the JDK-internals door permanently and made floating point unconditionally strict, retiring `strictfp` to a legal-but-inert modifier.

Java 18 onward continues in [version history, Java 18 onward](04a-internals-version-history-18-onward.md), starting with UTF-8 by default (leaf 3.17.14).

## Mechanisms worth walking

### The string pool leaving PermGen, and `substring` stopping sharing (Java 7)

**Mental model.** Two separate Java 7 changes about `String` that get merged into one wrong sentence. One moved *where interned strings live*. The other changed *what `substring` returns*.

**Why they exist.** PermGen was fixed-size: interning user input filled it and produced `OutOfMemoryError: PermGen space` with a mostly-empty heap. And `offset`/`count` meant every `substring` result pinned its parent's whole `char[]` alive — a four-character status prefix could retain a megabyte log line.

**How they work.** JDK-6962931 moved the `StringTable`'s referents to the ordinary heap in Java 7, so interned strings became normal collectable objects; PermGen itself was replaced by native Metaspace in Java 8 (JEP 122). Separately, JDK-6924259 removed `offset` and `count` in **7u6**, so `substring` allocates a new array and copies — O(n) where it had been O(1), and no retention.

| Claim | True in | Reality in Java 21 |
|---|---|---|
| Interned strings live in PermGen | ≤ 6 | Ordinary heap; the `StringTable` holds weak references |
| PermGen exists at all | ≤ 7 | Replaced by Metaspace in 8 |
| `substring` shares the parent array | ≤ 7u5 | Copies; O(n) in the substring length |

```java
// Java 21. Parsing "DEP-301 CAPTURED": the substring is independent, so the parent is collectable.
static String phaseOf(String cardDepositStatus) {
    int space = cardDepositStatus.indexOf(' ');
    return space < 0 ? cardDepositStatus : cardDepositStatus.substring(0, space);   // "DEP-301", fresh byte[]
}
```

**Pitfall:** believing the string pool lives in PermGen, so `-XX:MaxPermSize` tunes it. On Java 21 there is no PermGen and no `MaxPermSize` — the JVM refuses to start with it as a hard option. The pool's *hash table* size is `-XX:StringTableSize`; its default is version-dependent and **Unverified:** I could not confirm the Java 21 default, so do not quote a number.

**Pitfall:** believing `substring` is free, so tokenising the ~7.2B-a-year ledger rows with nested `substring` calls costs nothing. Since 7u6 each call copies. The escape hatch is `CharSequence.subSequence` over a `CharBuffer`, or index arithmetic with no substring at all.

> **Definition.** Java 7 moved interned strings to the collectable heap and, at 7u6, made `substring` a copy — trading O(1) slicing for the elimination of unbounded parent-array retention.

### `+` becoming `invokedynamic`, and compact strings (Java 9)

**Mental model.** In Java 9 `javac` stopped deciding *how* to concatenate and started emitting a single instruction that asks the runtime to decide.

**Why it exists.** The `StringBuilder` chain `javac` emitted through Java 8 pre-sized badly, resized, and copied twice per expression; deferring the decision to a bootstrap method lets the JIT size the result buffer exactly once. Separately, `String` had stored UTF-16 `char[]` since 1.0, doubling the footprint of the overwhelmingly Latin-1 content real applications hold.

**How it works.** JEP 280 makes `javac` emit `invokedynamic` against `StringConcatFactory.makeConcatWithConstants`, whose bootstrap builds a handle chain computing the exact length first. JEP 254 changes `String`'s field from `char[] value` to `byte[] value` plus a `byte coder` — `LATIN1` (one byte per character) or `UTF16` (two) — so an all-Latin-1 string halves.

| Release | What `"a" + b` compiles to | `String` storage |
|---|---|---|
| ≤ 8 | a `new StringBuilder()` / `append` / `toString` chain | `char[]`, always 2 bytes/char |
| 9–21 | `invokedynamic makeConcatWithConstants` | `byte[]` + `coder`, 1 byte/char for Latin-1 |
| Disable | `-XDstringConcat=inline` at compile time | `-XX:-CompactStrings` at run time |

```java
// Java 21. One indy call site, exact-sized buffer, no intermediate StringBuilder.
static String auditLine(PaymentRun run, StatusCode code) {
    return run.id() + " " + code.value() + " rows=" + run.withdrawals().size();
}

// Still quadratic in 21: the indy call site is inside the loop, so each iteration copies the whole accumulator.
static String slowJoin(List<WithdrawalTransaction> withdrawals) {
    String joined = "";
    for (WithdrawalTransaction withdrawal : withdrawals) { joined += withdrawal.reference() + ","; }
    return joined;
}
```

**Pitfall:** believing `+` compiles to a `StringBuilder` chain. It did through Java 8; from Java 9 it is `invokedynamic` to `StringConcatFactory`. The corollary people then get wrong in the other direction: JEP 280 does **not** fix `+=` in a loop. Each iteration is still a separate call site copying the whole accumulator, so `slowJoin` in the listing above is O(n²) on 21 exactly as on 8. Use an explicit `StringBuilder` or `String.join`.

**Trade-off on compact strings:** the ~7.2B ledger entries a year carrying `"CLIENT_CASH_RESERVED"` position strings drop from 40 bytes of payload to 20 — but every `charAt` now branches on the coder, and a single non-Latin-1 character in a string forces the whole string to UTF16. Depth in [`String` internals](../strings/03-internals-string.md) and [concat internals](../strings/04-internals-stringbuilder-and-concat.md).

> **Definition.** Java 9 replaced compile-time concatenation strategy with a runtime-linked `invokedynamic` call site (JEP 280) and replaced `String`'s UTF-16 array with a byte array plus a coder flag (JEP 254).

### Always-strict floating point makes `strictfp` a no-op (Java 17)

**Mental model.** `strictfp` existed to forbid a hardware-specific liberty that no supported hardware takes any more.

**Why it exists — and stopped.** Java 1.0 mandated strict IEEE 754, but the x87 FPU computed only in 80-bit extended precision, making strictness ruinously slow; Java 1.2 relaxed the default and added `strictfp` to opt back in. SSE2 made 64-bit-precision arithmetic native, so JEP 306 restored unconditional strictness in 17.

**How it works.** In Java 17+ every `float` and `double` operation is strict. `strictfp` remains a legal modifier on classes, interfaces and methods, and `Modifier.isStrict` still reports it, but it changes no result. `javac` on 17+ does not even record `ACC_STRICT` in the class file.

```java
// Compiled on JDK 21: bit-identical output with or without the strictfp modifier.
strictfp final class LegacyAffordabilityScore {
    static double score(double declaredIncome, double monthlyOutgoings) {
        return (declaredIncome - monthlyOutgoings * 12.0) / declaredIncome;
    }
}
```

**Pitfall:** believing `strictfp` still changes floating-point results, and adding it to an affordability calculation for determinism. It is inert from Java 17. Determinism for money comes from `BigDecimal` with an explicit `RoundingMode`, which is why `Money` wraps one. See [floating point](../numbers-and-money/04-internals-floating-point.md).

**Same arc, other half.** `strictfp` is a rule that stayed in the grammar after its meaning was deleted; `super()` first is a rule deleted from the grammar after 25 releases of being load-bearing. Both fail the same way — code written to the old rule still compiles, so nothing tells you the claim expired. The `super()` side is in [version history, Java 18 onward](04a-internals-version-history-18-onward.md#pitfalls).

> **Definition.** JEP 306 (Java 17) restored unconditional IEEE 754 strictness, reducing `strictfp` to a legal modifier with no semantic effect.

### Helpful NPEs become the default (Java 15)

**Mental model.** A default flipping, turning a class of guess-the-null debugging into a read-the-message one. Its sibling flip — the default charset becoming UTF-8 in Java 18 — is in [version history, Java 18 onward](04a-internals-version-history-18-onward.md#utf-8-by-default-java-18).

**Why it exists.** Before 15, an NPE named only the line.

**How it works.** JDK-8233014 flipped `ShowCodeDetailsInExceptionMessages` to true in 15, so the JVM reconstructs the failing expression from the bytecode and names it. The reconstruction is done from the bytecode of the throwing frame, which is why it can name `Wallet.stakeable()` as the null-returning call in the 3.17.11 listing above and not merely the statement.

> **Definition.** JDK-8233014 (Java 15) made helpful NPE messages the default rather than an opt-in flag.

### Strong encapsulation becomes deny-by-default (Java 16/17)

**Mental model.** Java 9 drew the module boundary. Java 16 started enforcing it. Java 17 removed the override.

**Why it exists.** JEP 261 defined modules in 9, but `--illegal-access=permit` was the default, so `setAccessible` into `sun.misc`, `java.lang` internals and every other JDK package kept working with a warning. Warnings do not migrate ecosystems.

**How it works.** JEP 396 (Java 16) changed the default to `--illegal-access=deny`: deep reflection into a non-`open` JDK package throws `InaccessibleObjectException` unless the run is granted `--add-opens`. JEP 403 (Java 17) removed the `--illegal-access` option entirely, so `permit` is no longer expressible.

| Release | `--illegal-access` default | Effect of `setAccessible` into a non-`open` JDK package |
|---|---|---|
| 9–15 | `permit` | Succeeds, one warning per package |
| 16 | `deny` | Throws `InaccessibleObjectException`; `--illegal-access=permit` restores |
| 17–25 | option removed | Throws; only `--add-opens` per package works |

```java
// Java 21: throws InaccessibleObjectException unless --add-opens java.base/java.lang=ALL-UNNAMED.
static int internalByteLength(String positionName) throws ReflectiveOperationException {
    Field value = String.class.getDeclaredField("value");
    value.setAccessible(true);                                   // throws on 16+ by default
    return ((byte[]) value.get(positionName)).length;
}
```

**Pitfall:** a Java 8-era agent or serialisation library that reads JDK internals runs with warnings on 11, throws on 17, and cannot be rescued by `--illegal-access=permit` because the option no longer exists. The migration is `--add-opens` per package as a stopgap, then a supported API. Modules in depth: [packages, modules and annotations](02-packages-modules-annotations.md).

> **Definition.** Strong encapsulation of JDK internals became the default in Java 16 (JEP 396) and unconditional in Java 17 (JEP 403), leaving `--add-opens` as the only escape.

## Pitfalls

### Believing `strictfp` still changes floating-point results

**Wrong**
```java
strictfp static double affordabilityRatio(double declaredIncome, double monthlyOutgoings) {
    return (declaredIncome - monthlyOutgoings * 12.0) / declaredIncome;
}
// On JDK 21 this produces bit-identical output to the same method without strictfp.
```

**Right**
```java
static BigDecimal affordabilityRatio(Money declaredIncome, Money monthlyOutgoings) {
    BigDecimal annualOutgoings = monthlyOutgoings.amount().multiply(BigDecimal.valueOf(12));
    return declaredIncome.amount().subtract(annualOutgoings)
                         .divide(declaredIncome.amount(), 6, RoundingMode.HALF_UP);
}
```

**Why people believe it:** `strictfp` is still a legal modifier, still highlighted by IDEs, and every pre-2021 tutorial says it forces IEEE 754. JEP 306 (Java 17) made all FP strict, so the modifier has nothing left to force.

### Believing the string pool lives in PermGen

**Wrong**
```java
// Reported fix for OutOfMemoryError from interning client references:
//   java -XX:MaxPermSize=512m -jar payment-service.jar
// On JDK 21 the JVM exits: "Unrecognized VM option 'MaxPermSize'".
```

**Right**
```java
// Do not intern unbounded input at all. A local map bounds the deduplication explicitly.
final class PositionNameCache {
    private final ConcurrentHashMap<String, String> canonical = new ConcurrentHashMap<>();

    String canonicalise(String positionName) {
        return canonical.computeIfAbsent(positionName, name -> name);
    }
}
```

**Why people believe it:** it was true through Java 6, and `OutOfMemoryError: PermGen space` was the canonical symptom of over-interning. Java 7 moved interned strings to the heap; Java 8 deleted PermGen.

### Believing `substring` shares the backing array

**Wrong**
```java
// Assumed O(1) and allocation-free, so called per ledger row (~19.8M/day).
static String phaseOf(String cardDepositStatus) {
    return cardDepositStatus.substring(0, cardDepositStatus.indexOf(' '));
}
// Since 7u6 every call allocates and copies a fresh byte[].
```

**Right**
```java
// Compare in place; no substring, no allocation.
static boolean isCaptured(String cardDepositStatus) {
    return cardDepositStatus.startsWith("DEP-301");
}
```

**Why people believe it:** through 7u5, `String` held `offset` and `count`, so `substring` was a genuine O(1) view — and the memory-leak articles explaining why that was bad are still the top search results.

### Believing `+` compiles to a `StringBuilder` chain

**Wrong**
```java
// "javac already turns this into a StringBuilder, so the loop is fine."
static String joinReferences(List<WithdrawalTransaction> withdrawals) {
    String joined = "";
    for (WithdrawalTransaction withdrawal : withdrawals) { joined += withdrawal.reference() + ","; }
    return joined;   // O(n^2) on JDK 8 and on JDK 21 alike
}
```

**Right**
```java
static String joinReferences(List<WithdrawalTransaction> withdrawals) {
    StringBuilder joined = new StringBuilder(withdrawals.size() * 24);
    for (WithdrawalTransaction withdrawal : withdrawals) {
        joined.append(withdrawal.reference()).append(',');
    }
    return joined.toString();
}
```

**Why people believe it:** it was literally the Java 8 bytecode, and the claim survives because the *conclusion* people draw from it — "`+` is fine" — is right for a single expression and wrong for a loop, in both eras.

## Cheat sheet

Java 18–25 rows are in [version history, Java 18 onward](04a-internals-version-history-18-onward.md#cheat-sheet).

| Release | The one thing to remember |
|---|---|
| 1.0 | Primitives, `Object`, checked exceptions; `Vector`/`Hashtable`/`StringBuffer` are synchronised legacy |
| 1.2 | Default FP relaxed for the x87 FPU; `strictfp` added to opt strictness back in |
| 1.4 | `assert` exists but is off without `-ea`; regex arrives |
| 5 | Generics, enums, annotations, `java.util.concurrent`, `StringBuilder` |
| 5 (erasure) | `List<Money>` and `List<Restriction>` are one runtime class |
| 6 | `@Override` on interface implementations |
| 7 | Try-with-resources; pool leaves PermGen; `invokedynamic` added but unused by `javac` |
| 7u6 | `substring` copies; `offset`/`count` deleted (JDK-6924259) |
| 8 | Lambdas, streams, `Optional`, `java.time`; PermGen removed (JEP 122) |
| 9 | Modules; compact strings (JEP 254); indified concat (JEP 280) |
| 10 | `var` |
| 11 LTS | `HttpClient`; nestmates (JEP 181) kill `access$000`; Java EE modules removed |
| 12 | Switch expressions preview 1 (JEP 325); default CDS archives |
| 13 | Text blocks preview 1; `break value` becomes `yield`; `hashIsZero` |
| 14 | Switch expressions final; helpful NPEs shipped, flag off |
| 15 | Text blocks final; helpful NPEs on by default; biased locking deprecated |
| 16 | Records final; static members in inner classes; encapsulation deny-by-default |
| 17 LTS | Sealed final; `strictfp` inert (JEP 306); `--illegal-access` removed (JEP 403) |
| 18 onward | Continues in [part 04a](04a-internals-version-history-18-onward.md) |

## Self-test

**Q1.** In which release did `+` stop compiling to a `StringBuilder` chain, and what replaced it?

<details><summary>Answer</summary>

Java 9, by JEP 280 (Indify String Concatenation). `javac` now emits a single `invokedynamic` against `StringConcatFactory.makeConcatWithConstants`, whose bootstrap method builds a method-handle chain that computes the exact result length before allocating. It does not help `+=` inside a loop: each iteration is a separate call site copying the whole accumulator, so that remains O(n²) on Java 21. `-XDstringConcat=inline` restores the pre-9 `StringBuilder` bytecode.

</details>

**Q2.** A colleague says `substring` is O(1) because it shares the parent array. When was that last true, and what changed?

<details><summary>Answer</summary>

Last true in 7u5. JDK-6924259 removed `String`'s `offset` and `count` fields in **7u6**, so `substring` allocates and copies — O(n) in the substring length. The motivation was retention: a short substring used to pin its parent's entire array alive. Note the two common misdatings: it was not Java 8, and it was not the base 7 release.

</details>

**Q3.** Does `strictfp` change anything on Java 21?

<details><summary>Answer</summary>

No. JEP 306 (Java 17, *Restore Always-Strict Floating-Point Semantics*) made every `float` and `double` operation strictly IEEE 754, so `strictfp` is a legal but inert modifier. It existed because Java 1.2 relaxed the default to accommodate the x87 FPU's mandatory 80-bit intermediate precision; SSE2 removed the need. For deterministic money arithmetic use `BigDecimal` with an explicit `RoundingMode`, not `strictfp`.

</details>

**Q4.** A Java 8-era library calls `setAccessible(true)` on a private `java.lang` field. Trace its fate across 11, 16, 17 and 26.

<details><summary>Answer</summary>

On 9–15 it succeeds with one warning per package (`--illegal-access=permit` was the default). On 16 it throws `InaccessibleObjectException` because JEP 396 changed the default to `deny`, though `--illegal-access=permit` still restores it. On 17 JEP 403 removed the `--illegal-access` option entirely, so only a targeted `--add-opens java.base/java.lang=ALL-UNNAMED` works. On 26, JEP 500 additionally warns at run time whenever deep reflection *mutates* a `final` field, and `--add-opens` alone no longer silences that — it needs `--enable-final-field-mutation`.

</details>

**Q5.** Which release moved interned strings out of PermGen, and which release removed PermGen itself?

<details><summary>Answer</summary>

Two different releases, which is why the claim gets garbled. Java 7 moved the `StringTable`'s referents to the ordinary heap (JDK-6962931), so interned strings became normal collectable objects. Java 8 then removed PermGen entirely in favour of native Metaspace (JEP 122). On Java 21 `-XX:MaxPermSize` is not merely ignored — the JVM refuses to start with it as a hard option.

</details>

**Q6.** A code review flags a `static final int MAX_ROWS = 500;` inside a non-static nested class as illegal. Is it?

<details><summary>Answer</summary>

Not since Java 16. Through Java 15 a `static` member inside an inner (non-static nested) class was a compile error unless it was a constant variable, so the workaround was to hoist it to the enclosing class or make the nested class `static`. JEP 395 (records, Java 16) carried the relaxation, so `BalanceView.AuditTrail` may declare `static final int MAX_ROWS` directly on a Java 21 target.

</details>

**Q7.** In which release did `@Override` become legal on a method implementing an interface method, and why does that break a build in the other direction?

<details><summary>Answer</summary>

Java 6. In Java 5 `@Override` applied only to methods overriding a *class* method, so annotating an interface implementation was a compile error. The asymmetry bites when source is compiled *down*: code written on 6+ that annotates interface implementations fails on a 5 compiler, while 5-era code never fails on 6+. It is the cleanest example of the era pattern — the rule loosened, so only the backward direction breaks.

</details>

## Deferred

None.

## Open questions

One number is genuinely unverified: the default of `-XX:StringTableSize` on Java 21. It sits with the Java 7 string-pool material in this file, and no value is printed anywhere here. `java -XX:+PrintFlagsFinal -version | grep StringTableSize` on the target JDK settles it.

Four release attributions that did not check out as given concern Java 18-onward material and are recorded, in corrected form, in [version history, Java 18 onward](04a-internals-version-history-18-onward.md#open-questions).

---

**Leaves covered:** 3.17.1–3.17.13 (13 leaves)
**Leaves deferred:** none
**Diagrams included:** none
**Target version:** Java 21 LTS
**Lines:** 577
