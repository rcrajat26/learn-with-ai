# 03 Java Core — Version history, Java 18 onward — INTERNALS (§3.17)

**Target version: Java 21 LTS.** | **Part 3 of 5** | [Index](../00-index.md)
Previous: [Version history, Java 1.0–17](04-internals-version-history.md) · Next: [Observability toolkit](05-internals-observability.md)

This half starts at Java 18, where the cleanup-and-defaults era begins — UTF-8 by default, finalization deprecated for removal, Security Manager on its way out. Java 1.0 through Java 17 LTS, where the classic language surface stabilised (sealed classes final, `strictfp` retired, floating point always strict), is in [version history, Java 1.0–17](04-internals-version-history.md).

## The release train, in three lines

Three eras: the substrate fixed in 1.0–1.4, the type machinery grown one huge feature at a time in 5–8, and the six-month train from 9 onward that ships language features through a preview lifecycle before finalising them. This file covers the train's second half, 18 through 25, plus the announced-not-landed direction.

The full treatment of the eras — the rhythm table, the preview lifecycle, the LTS and end-of-life dates, and the `Runtime.version().feature()` check — is in [version history, Java 1.0–17](04-internals-version-history.md#the-release-train-as-three-eras). It is not repeated here.

## Release by release, Java 18 onward

### Java 18 — UTF-8 by default (3.17.14) `[RESEARCH]`

UTF-8 as the default charset (JEP 400), finalization deprecated for removal (JEP 421), the `jwebserver` simple web server (JEP 408), `@snippet` in javadoc (JEP 413), and core reflection reimplemented on method handles (JEP 416).

> **Definition.** From Java 18 `Charset.defaultCharset()` is UTF-8 on every platform unless `-Dfile.encoding` overrides it; before 18 it was derived from the host locale.

### Java 19–20 — the preview staging ground (3.17.15) `[X-REF 04]`

Nothing here finalised for the language. Java 19: virtual threads (JEP 425, preview 1), structured concurrency (JEP 428, incubator), record patterns (JEP 405, preview 1), pattern matching for `switch` (JEP 427, preview 3). Java 20: the same four re-previewed (JEP 436, 437, 432, 433). Mechanically, a virtual thread is a `Thread` whose continuation is mounted onto a small pool of platform carrier threads and unmounted at every blocking point, so a blocking call parks a heap-allocated continuation instead of a 1 MB OS stack — which is why 1,200/sec stake reservations each blocking on the ledger no longer need 1,200 platform threads. Full treatment in **04 Modern Java**.

### Java 21 (LTS) — the current target (3.17.16) `[RESEARCH]` `[X-REF 04]`

Virtual threads final (JEP 444), record patterns final (JEP 440), pattern matching for `switch` final (JEP 441), sequenced collections (JEP 431), generational ZGC (JEP 439), plus previews: string templates (JEP 430, preview 1), unnamed patterns and variables (JEP 443, preview 1), unnamed classes and instance main methods (JEP 445, preview 1), scoped values (JEP 446, preview 1), structured concurrency (JEP 453, preview 1). `javac` also gained the `this-escape` lint, which warns when a constructor calls an overridable method.

```java
static StatusCode disposition(Verdict verdict) {
    return switch (verdict) {                          // exhaustive over the sealed hierarchy, no default
        case DocumentVerdict(StatusCode code, boolean referred)   -> code;   // record patterns
        case ScreeningVerdict(StatusCode code, boolean prohibited) -> code;
        case ReviewVerdict(StatusCode code, String operatorId)     -> code;
        case WealthVerdict(StatusCode code, Money declaredIncome)  -> code;
    };
}

static Money bonusPortionOf(StakeSplit split) {
    return split instanceof StakeSplit(Money bonus, Money cash) ? bonus : Money.zero();
}

// Sequenced collections: the ordered Application audit trail finally names both ends.
static StatusCode latestStatus(SequencedCollection<StatusCode> auditTrail) { return auditTrail.getLast(); }
```

**Interview:** "What did Java 21 finalise?" — virtual threads, record patterns, pattern matching for `switch`, sequenced collections, generational ZGC. String templates were *preview only* in 21, and were withdrawn entirely in 23 rather than finalised.

### Java 22–23 — unnamed final, `super()` relaxed in preview (3.17.17) `[RESEARCH]`

Java 22: unnamed variables and patterns final (JEP 456), statements before `super()` as preview 1 (JEP 447), string templates preview 2 (JEP 459), Class-File API preview 1 (JEP 457), stream gatherers preview 1 (JEP 461), multi-file source launch (JEP 458). Java 23: primitive types in patterns, `instanceof` and `switch` preview 1 (JEP 455), flexible constructor bodies preview 2 (JEP 482), Class-File API preview 2 (JEP 466), Markdown documentation comments (JEP 467), and the memory-access methods of `sun.misc.Unsafe` deprecated for removal (JEP 471). String templates were dropped from 23 with no replacement preview.

```java
static Money cashPortionOf(StakeSplit split) {
    return switch (split) {
        case StakeSplit(_, Money cash) -> cash;    // Java 22 final: unnamed pattern for the ignored component
    };
}
```

### Java 24–25 — constructors, headers, scoped values (3.17.18) `[RESEARCH]` `[X-REF 04]`

Java 24 (GA 18 March 2025): Class-File API final (JEP 484), `synchronized` no longer pinning virtual threads (JEP 491), the Security Manager permanently disabled (JEP 486), compact object headers as an experimental feature (JEP 450), stream gatherers final (JEP 485), flexible constructor bodies preview 3 (JEP 492), module import declarations preview 2 (JEP 494), warning on `sun.misc.Unsafe` memory-access use (JEP 498).

Java 25 (LTS, GA 16 September 2025): flexible constructor bodies final (JEP 513), module import declarations final (JEP 511), compact source files and instance main methods final (JEP 512), scoped values final (JEP 506), compact object headers as a product feature (JEP 519, still opt-in via `-XX:+UseCompactObjectHeaders`), primitive types in patterns preview 3 (JEP 507), structured concurrency preview 5 (JEP 505), stable values preview 1 (JEP 502).

```java
// Java 25 final (JEP 513): validation before super(), no static-factory workaround needed.
final class ReservedPosition extends Position {
    private final Money reserved;

    ReservedPosition(AccountId accountId, Money reserved) {
        if (reserved.amount().signum() < 0) { throw new InsufficientFundsException("negative reservation"); }
        super(accountId, "CLIENT_BONUS_RESERVED");   // legal from Java 25; preview in 22, 23, 24
        this.reserved = reserved;
    }
}
```

**Pitfall:** believing `super()` must be the first statement in a constructor. True from 1.0 through 21, which is why the workaround idiom is a `private` constructor plus a `static` factory that validates first. Preview in 22 (JEP 447), 23 (JEP 482) and 24 (JEP 492); final in 25 (JEP 513). The prologue still cannot read `this`.

**Insight:** JEP 491 matters more than it sounds. Before 24, a virtual thread blocking inside a `synchronized` block *pinned* its carrier platform thread, so a `synchronized` critical section around a `FundsLedger` position could starve the carrier pool at 1,200 reservations/sec. From 24, `synchronized` unmounts like any other blocking point, and the standard advice to rewrite `synchronized` as `ReentrantLock` for virtual-thread code expires.

### Announced, not landed (3.17.19) `[RESEARCH]`

Three directions that change claims in this guide but are not in any LTS you can deploy today.

- **Valhalla value classes** — JEP 401, *Value Classes and Objects*, is a preview feature targeting JDK 28 (integration into mainline mid-2026), available now only in Project Valhalla early-access builds. A value class has no identity, so the JVM may flatten it into its container and scalarise it in the JIT. `Money(BigDecimal amount, Currency currency)` as a value class would remove a `Money` allocation per stake split — roughly 2.8M/day of reservation boxing plus the `StakeSplit` wrapper — but a `BigDecimal` field is itself a reference, so flattening `Money` only pays fully if the amount becomes a `long` of minor units.
- **JEP 500, *Prepare to Make Final Mean Final*** — completed for **JDK 26**, not 25. Deep reflection that mutates a `final` field warns at run time by default, and `--add-opens` alone no longer silences it; `--enable-final-field-mutation` grants it per module and `--illegal-final-field-mutation` selects warn/deny. A later release throws by default.
- **Lazy `static final` fields** — shipped in preview as **JEP 502 Stable Values** (JDK 25) and renamed and reshaped as **JEP 526 Lazy Constants** (second preview, JDK 26). A lazy constant is a holder computed at most once, giving the JIT the constant-folding it grants a `final` field while deferring the initialisation cost off the class-init path.

**Pitfall:** believing reflection can freely mutate a `final` field. In Java 21, `setAccessible(true)` then `Field.set` on a `static final` field throws `IllegalAccessException` regardless of openness, and on any field of a record or hidden class it also throws. Mutating a non-static `final` field still works in 21 — but only if the declaring package is `open` to your module, which since Java 16 (JEP 396) it is not by default for JDK packages, and since Java 17 (JEP 403) cannot be relaxed with `--illegal-access`. JDK 26 warns on the remaining case.

## Mechanisms worth walking

### UTF-8 by default (Java 18)

**Mental model.** A default flipping, turning a class of environment-dependent bug into a non-bug. Its sibling flip — helpful NPE messages becoming the default in Java 15 — is in [version history, Java 1.0–17](04-internals-version-history.md#helpful-npes-become-the-default-java-15).

**Why it exists.** Before 18, `Charset.defaultCharset()` came from the host locale — UTF-8 in a Linux container, `windows-1252` on a laptop, `US-ASCII` under an empty `LANG` — so charset-less code was correct in CI and corrupt in production.

**How it works.** JEP 400 fixes the default to UTF-8 for `Charset.defaultCharset()` and every charset-less API (`new FileReader`, `new String(byte[])`, `PrintStream`), with `-Dfile.encoding=COMPAT` restoring the old locale-derived behaviour.

```java
// Locale-derived charset through 17, UTF-8 from 18: same source, two behaviours.
static String readPayoutFileLocaleDependent(Path partnerFile) throws IOException {
    try (var reader = new BufferedReader(new FileReader(partnerFile.toFile()))) {   // no charset argument
        return reader.lines().collect(Collectors.joining("\n"));
    }
}

// Correct on every release since 7: state the charset.
static String readPayoutFile(Path partnerFile) throws IOException {
    return Files.readString(partnerFile, StandardCharsets.UTF_8);
}
```

**Pitfall:** believing the default charset is still platform-dependent, and therefore that pinning `-Dfile.encoding=UTF-8` is required. From Java 18 it is redundant; on Java 17 and earlier it is essential. A service on 17 reading the banking partner payout file with `new FileReader` mangles non-ASCII client names under a non-UTF-8 locale; the same code on 18 does not. Note the asymmetry — `Files.readString(Path)` was UTF-8 from its introduction in Java 11, so the bug only ever lived in the charset-less legacy APIs.

> **Definition.** JEP 400 (Java 18) made UTF-8 the default charset on all platforms.

## What changed in which release (3.17.20)

The Java 1.0–17 rows below are summaries; their detail — the release entries, the mechanisms and the pitfalls they generate — is in [version history, Java 1.0–17](04-internals-version-history.md).

**D-129** — What changed in which release.

| Release (GA) | Language features | Core-library changes relevant to this guide | Version traps introduced or resolved |
|---|---|---|---|
| 5 (2004-09) | Generics, enums, autoboxing, varargs, annotations, enhanced `for`, `static import`, covariant returns | `java.util.concurrent`, `StringBuilder`, `Scanner`, `EnumMap` | Erasure introduced; `StringBuffer` becomes legacy |
| 6 (2006-12) | `@Override` allowed on interface implementations | Minor library work only | Code with `@Override` on an interface method stops compiling on 5 |
| 7 (2011-07) | Diamond `<>`, `String` in `switch`, try-with-resources, multi-catch, precise rethrow, binary literals, underscores | `java.util.Objects`, `invokedynamic` bytecode, `NIO.2` | **Resolves:** pool in PermGen (moved to heap); `substring` sharing (7u6 copies) |
| 8 (2014-03) | Lambdas, method references, `default`/`static` interface methods, repeatable and type annotations | Streams, `Optional`, `java.time`, `Base64`, `StampedLock`, `LongAdder` | **Resolves:** PermGen removed (Metaspace, JEP 122). Introduces "everything modern is Java 8" folklore |
| 9 (2017-09) | Modules (JEP 261), `private` interface methods, try-with-resources on effectively final, diamond with anonymous classes | `List.of`, compact strings (JEP 254), indified concat (JEP 280), `Cleaner`, `StackWalker`, `Optional.stream`, wrapper constructors deprecated | **Resolves:** `+` → `StringBuilder` (now `invokedynamic`); UTF-16-only `String`. **Introduces:** `--illegal-access=permit` warnings |
| 10 (2018-03) | `var` (JEP 286) | `List.copyOf`, `Optional.orElseThrow()`, application CDS (JEP 310) | `var` is a reserved type name, not a keyword |
| 11 LTS (2018-09) | Local `var` in lambda parameters | `String.isBlank`/`lines`/`strip`/`repeat`, `Files.readString`, `HttpClient` (JEP 321), `Collection.toArray(IntFunction)`, nestmates (JEP 181), single-file launch (JEP 330) | **Resolves:** `access$000` bridges (nestmates). **Introduces:** Java EE/CORBA modules removed (JEP 320) |
| 12 (2019-03) | Switch expressions (preview 1, JEP 325) | `String.indent`, `String.transform`, `Files.mismatch`, default CDS archives | Preview features require `--enable-preview` and are class-file-version-pinned |
| 13 (2019-09) | Text blocks (preview 1, JEP 355), switch expressions preview 2 with `yield` (JEP 354) | `String.hashIsZero` caching field (JDK-8221836) | `break value` from the 12 preview becomes `yield` |
| 14 (2020-03) | Switch expressions **final** (JEP 361), records preview 1 (JEP 359), pattern `instanceof` preview 1 (JEP 305) | Helpful NPEs (JEP 358, off by default), `finalize` further discouraged | **Introduces:** helpful NPEs behind `-XX:+ShowCodeDetailsInExceptionMessages` |
| 15 (2020-09) | Text blocks **final** (JEP 378), sealed preview 1 (JEP 360) | `String.stripIndent`/`translateEscapes`/`formatted`, biased locking deprecated (JEP 374) | **Resolves:** helpful NPEs off by default (now on). Records' fields become reflection-immutable |
| 16 (2021-03) | Records **final** (JEP 395), pattern `instanceof` **final** (JEP 394), static members in inner classes | `Stream.toList()`, wrapper constructors terminally deprecated, strong encapsulation by default (JEP 396) | **Resolves:** inner classes cannot hold static members. **Introduces:** `InaccessibleObjectException` by default |
| 17 LTS (2021-09) | Sealed classes **final** (JEP 409) | Always-strict FP (JEP 306), `RandomGenerator` (JEP 356), `Map.Entry.copyOf`, Security Manager deprecated (JEP 411), `--illegal-access` removed (JEP 403) | **Resolves:** `strictfp` is meaningful (now inert). Last release with locale-derived default charset |
| 18 (2022-03) | No final language change | UTF-8 by default (JEP 400), finalization deprecated for removal (JEP 421), `jwebserver` (JEP 408), `@snippet` (JEP 413), reflection on method handles (JEP 416) | **Resolves:** platform-dependent default charset. `-Dfile.encoding=COMPAT` is the escape |
| 19 (2022-09) | Record patterns preview 1 (JEP 405), pattern `switch` preview 3 (JEP 427) | Virtual threads preview 1 (JEP 425), structured concurrency incubator (JEP 428) | Virtual threads pin the carrier inside `synchronized` |
| 20 (2023-03) | Record patterns preview 2 (JEP 432), pattern `switch` preview 4 (JEP 433) | Virtual threads preview 2 (JEP 436), structured concurrency preview 2 (JEP 437) | Nothing final; a pure staging release |
| 21 LTS (2023-09) | Record patterns **final** (JEP 440), pattern `switch` **final** (JEP 441), string templates preview 1 (JEP 430), unnamed patterns/variables preview 1 (JEP 443), `this-escape` lint | Virtual threads **final** (JEP 444), sequenced collections (JEP 431), generational ZGC (JEP 439), scoped values preview 1 (JEP 446) | String templates are preview only and later withdrawn — do not call them a Java 21 feature |
| 22 (2024-03) | Unnamed variables and patterns **final** (JEP 456), statements before `super()` preview 1 (JEP 447), string templates preview 2 (JEP 459) | Class-File API preview 1 (JEP 457), stream gatherers preview 1 (JEP 461), FFM API final (JEP 454), multi-file launch (JEP 458) | `_` becomes a legal unnamed variable, having been an error since 9 |
| 23 (2024-09) | Primitive types in patterns preview 1 (JEP 455), flexible constructor bodies preview 2 (JEP 482) | Class-File API preview 2 (JEP 466), Markdown javadoc (JEP 467), `sun.misc.Unsafe` memory access deprecated for removal (JEP 471), generational ZGC by default (JEP 474) | String templates dropped with no replacement preview |
| 24 (2025-03) | Flexible constructor bodies preview 3 (JEP 492), module imports preview 2 (JEP 494) | Class-File API **final** (JEP 484), stream gatherers **final** (JEP 485), Security Manager permanently disabled (JEP 486), `synchronized` no longer pins virtual threads (JEP 491), compact object headers experimental (JEP 450), `Unsafe` use warns (JEP 498) | **Resolves:** rewrite `synchronized` as `ReentrantLock` for virtual threads. Security Manager cannot be enabled at all |
| 25 LTS (2025-09) | Flexible constructor bodies **final** (JEP 513), module import declarations **final** (JEP 511), compact source files and instance `main` **final** (JEP 512), primitive patterns preview 3 (JEP 507) | Scoped values **final** (JEP 506), compact object headers as a product feature (JEP 519, opt-in), stable values preview 1 (JEP 502), structured concurrency preview 5 (JEP 505) | **Resolves:** `super()` must be the first statement. Ahead: JEP 500 (final means final) and JEP 526 (lazy constants) in 26; JEP 401 value classes targeting 28 |

## Pitfalls

### Believing `super()` must be the first statement in a constructor

**Wrong**
```java
// Idiom adopted because validation could not precede super() before Java 25.
final class ReservedPosition extends Position {
    private ReservedPosition(AccountId accountId, Money reserved) { super(accountId, "CLIENT_BONUS_RESERVED"); }

    static ReservedPosition of(AccountId accountId, Money reserved) {
        if (reserved.amount().signum() < 0) { throw new InsufficientFundsException("negative reservation"); }
        return new ReservedPosition(accountId, reserved);
    }
}
```

**Right**
```java
// Java 25, JEP 513. The prologue validates before delegating; it still may not read this.
final class ReservedPosition extends Position {
    ReservedPosition(AccountId accountId, Money reserved) {
        if (reserved.amount().signum() < 0) { throw new InsufficientFundsException("negative reservation"); }
        super(accountId, "CLIENT_BONUS_RESERVED");
    }
}
```

**Why people believe it:** it was a JLS rule from 1.0 through 21, and it is still true on every LTS before 25 — so on a Java 21 target the static-factory idiom remains correct. This is the mirror of `strictfp`, whose rule outlived its meaning rather than the reverse: see [always-strict floating point](04-internals-version-history.md#always-strict-floating-point-makes-strictfp-a-no-op-java-17).

### Believing `finalize` still runs reliably

**Wrong**
```java
// Cleanup for the payout-file handle, relied on because "the GC will call it".
final class PayoutFileHandle {
    private final FileChannel channel;

    PayoutFileHandle(FileChannel channel) { this.channel = channel; }

    @Override protected void finalize() throws Throwable {   // deprecated for removal since Java 18
        channel.close();                                     // may never run; ordering undefined
    }
}
```

**Right**
```java
// Deterministic release via AutoCloseable, with a Cleaner (Java 9) only as a leak backstop.
final class PayoutFileHandle implements AutoCloseable {
    private static final Cleaner CLEANER = Cleaner.create();
    private final FileChannel channel;
    private final Cleaner.Cleanable cleanable;

    PayoutFileHandle(FileChannel channel) {
        this.channel = channel;
        this.cleanable = CLEANER.register(this, new CloseAction(channel));
    }

    @Override public void close() { cleanable.clean(); }

    private record CloseAction(FileChannel channel) implements Runnable {
        @Override public void run() { try { channel.close(); } catch (IOException ignored) { } }
    }
}
```

**Why people believe it:** `finalize` was on `Object` from 1.0 and every pre-2015 resource-management tutorial shows it. JEP 421 (Java 18) deprecated finalization for removal and added `--finalization=disabled` so a run can prove it does not depend on finalizers; a future release removes the mechanism entirely. Even before deprecation the guarantee was weak — a finalizer may run late, on an arbitrary thread, or never, and a `PaymentRun` holding 4,000 open channels through a finalization queue exhausts the file-descriptor limit before the GC gets to them. Lifecycle detail in [object lifecycle and references](../objects-equality-and-lifecycle/03-lifecycle-and-references.md).

### Believing the Security Manager is still available

**Wrong**
```java
// Sandbox for the partner-supplied bonus rules script, still in the service bootstrap.
static void installSandbox() {
    System.setSecurityManager(new SecurityManager());   // UnsupportedOperationException on JDK 24+
}
// Run with -Djava.security.manager=allow through 23; on 24+ the JVM refuses the property.
```

**Right**
```java
// No in-process sandbox exists any more. Isolate at the process or container boundary instead,
// and gate what BonusService will evaluate by allow-listing rule shapes before execution.
static void evaluate(BonusRule rule) {
    if (!BonusService.ALLOWED_RULE_SHAPES.contains(rule.shape())) {
        throw new RestrictedActionException("AA-801 ACTIVATED requires an allow-listed rule shape");
    }
    BonusService.apply(rule);
}
```

**Why people believe it:** `SecurityManager`, `AccessController` and `java.policy` are still *present* in `java.base` on Java 21, and `System.setSecurityManager` still compiles, so the API looks live. JEP 411 (Java 17) deprecated it for removal and made `System.setSecurityManager` throw unless the run passes `-Djava.security.manager=allow`; JEP 486 (JDK 24) permanently disabled it, so the manager can no longer be set at all and the `allow` value is gone. On a Java 21 target the API works but is deprecated for removal, and writing new code against it buys a migration.

## Cheat sheet

Java 1.0–17 rows are in [version history, Java 1.0–17](04-internals-version-history.md#cheat-sheet).

| Release | The one thing to remember |
|---|---|
| 1.0–17 | See [part 04](04-internals-version-history.md) |
| 18 | UTF-8 by default (JEP 400) |
| 18 (lifecycle) | Finalization deprecated for removal (JEP 421); `--finalization=disabled` proves independence |
| 18 (tooling) | `jwebserver` (JEP 408), `@snippet` javadoc (JEP 413), reflection on method handles (JEP 416) |
| 19 | Virtual threads preview 1 (JEP 425); record patterns preview 1 (JEP 405) |
| 20 | Nothing final; a pure staging release |
| 21 LTS | Virtual threads, record patterns, pattern `switch`, sequenced collections |
| 21 (preview) | String templates (JEP 430) — preview only, withdrawn in 23; not a Java 21 feature |
| 22 | Unnamed variables and patterns final; `super()` relaxation previews (JEP 447) |
| 22 (library) | Class-File API preview 1 (JEP 457), stream gatherers preview 1 (JEP 461), FFM final (JEP 454) |
| 23 | Markdown javadoc; `Unsafe` memory access deprecated (JEP 471); string templates dropped |
| 23 (GC) | Generational ZGC becomes the default (JEP 474) |
| 24 | Class-File API final; `synchronized` stops pinning (JEP 491); Security Manager off for good (JEP 486) |
| 24 (headers) | Compact object headers, experimental (JEP 450) |
| 25 LTS | Flexible constructor bodies final (JEP 513); scoped values final; compact object headers a product feature (JEP 519) |
| 25 (preview) | Stable values (JEP 502), primitive patterns preview 3 (JEP 507), structured concurrency preview 5 (JEP 505) |
| 26 | JEP 500 final-means-final warnings; JEP 526 lazy constants; JEP 534 compact headers by default |
| 28 (target) | JEP 401 value classes, preview |

## Self-test

**Q1.** Which of these is *not* a Java 21 feature: virtual threads, record patterns, string templates, sequenced collections?

<details><summary>Answer</summary>

String templates. JEP 430 made them a first preview in Java 21, JEP 459 a second preview in 22, and they were then withdrawn from 23 with no replacement preview. Virtual threads (JEP 444), record patterns (JEP 440) and sequenced collections (JEP 431) all finalised in 21, alongside pattern matching for `switch` (JEP 441) and generational ZGC (JEP 439).

</details>

**Q2.** When did `synchronized` stop pinning a virtual thread's carrier, and why does it matter?

<details><summary>Answer</summary>

Java 24, JEP 491 (*Synchronize Virtual Threads without Pinning*). Before it, a virtual thread that blocked inside a `synchronized` block kept its carrier platform thread mounted, so a `synchronized` critical section around a `FundsLedger` position could starve the carrier pool under 1,200 stake reservations/sec. That is why pre-24 guidance was to rewrite `synchronized` as `ReentrantLock` in virtual-thread code. From 24 that rewrite is unnecessary — but on a Java 21 target the pinning is real and the guidance still applies.

</details>

**Q3.** What does `Charset.defaultCharset()` return on Java 17 and on Java 18, and what is the escape hatch?

<details><summary>Answer</summary>

On 17 and earlier it is derived from the host locale — UTF-8 in a typical Linux container, `windows-1252` on a Windows laptop, `US-ASCII` under an empty `LANG`. From 18, JEP 400 fixes it to UTF-8 on every platform, along with every charset-less API (`new FileReader`, `new String(byte[])`, `PrintStream`). The escape is `-Dfile.encoding=COMPAT`, which restores the locale-derived behaviour. Stating the charset explicitly is correct on every release, and `Files.readString(Path)` was already UTF-8 from Java 11.

</details>

**Q4.** Is `finalize` safe to use on a Java 21 target?

<details><summary>Answer</summary>

It compiles, and it is deprecated for removal. JEP 421 (Java 18) deprecated finalization for removal and added `--finalization=disabled` so a run can prove it has no finalizer dependency; a later release removes the mechanism. Independently of the deprecation the guarantee was always weak: a finalizer may run late, on an arbitrary thread, or never at all, so a handle closed only in `finalize` can exhaust the file-descriptor limit. Use `AutoCloseable` with try-with-resources for the deterministic path, and `Cleaner` (Java 9) only as a backstop.

</details>

**Q5.** Trace the Security Manager from Java 17 to JDK 24.

<details><summary>Answer</summary>

JEP 411 (Java 17) deprecated it for removal and made `System.setSecurityManager` throw at run time unless the JVM was started with `-Djava.security.manager=allow`. JEP 486 (JDK 24) permanently disabled it: the manager cannot be set at all, and the `allow` value no longer exists. The types remain in `java.base`, which is exactly why the API still looks live. Note the attribution trap — JEP 486 is **24**, not 25; JDK 25 has no Security Manager JEP.

</details>

**Q6.** Which release ships compact object headers?

<details><summary>Answer</summary>

None of them alone — the answer spans three. JEP 450 (JDK 24) shipped them as an *experimental* feature, JEP 519 (JDK 25) promoted them to a product feature still opt-in via `-XX:+UseCompactObjectHeaders`, and JEP 534 (JDK 26) makes them the default. "24 or 25" has no single correct answer, which is what the question is testing.

</details>

**Q7.** A colleague mentions "the lazy `static final` fields JEP" and "JEP 500 as an unlanded proposal". Correct both.

<details><summary>Answer</summary>

There is no JEP titled "lazy static final fields": the work shipped as JEP 502 *Stable Values* (preview, JDK 25) and was renamed and re-scoped as JEP 526 *Lazy Constants* (second preview, JDK 26). A lazy constant is a holder computed at most once, so the JIT still constant-folds it while the initialisation cost stays off the class-init path. And JEP 500 *Prepare to Make Final Mean Final* has landed — in JDK 26, not 25. It warns at run time when deep reflection mutates a `final` field, `--add-opens` alone no longer silences it, and `--enable-final-field-mutation` grants it per module. A later release throws.

</details>

## Deferred

None.

## Open questions

Four attributions did not check out as given and are printed above in corrected form.

- **JEP 486 (Permanently Disable the Security Manager) is JDK 24, not 25.** JDK 25 has no Security Manager JEP; JEP 411 deprecated it for removal in 17.
- **Compact object headers span three releases:** experimental via JEP 450 (24), a product feature via JEP 519 (25, still opt-in), default via JEP 534 (26). "24 or 25" has no single answer.
- **JEP 500 has landed, and it is JDK 26,** titled *Prepare to Make Final Mean Final* — not an unlanded direction. It warns; a later release throws.
- **"Lazy static final fields" is not a JEP title.** The work shipped as JEP 502 *Stable Values* (preview, 25), renamed and re-scoped as JEP 526 *Lazy Constants* (second preview, 26).

Two further datings that are correct as printed and are the ones most often garbled: flexible constructor bodies previewed three times (JEP 447 in 22, JEP 482 in 23, JEP 492 in 24) before JEP 513 finalised them in 25; and Valhalla's JEP 401 *Value Classes and Objects* is a preview targeting JDK 28, not a shipped feature.

The one genuinely unverified number in this pair of files — the default of `-XX:StringTableSize` on Java 21 — sits with the Java 7 string-pool material in [version history, Java 1.0–17](04-internals-version-history.md#open-questions).

---

**Leaves covered:** 3.17.14–3.17.20 (7 leaves)
**Leaves deferred:** none
**Diagrams included:** D-129
**Target version:** Java 21 LTS
**Lines:** 353
