# PROMPT — Generate the Java Core bible (topic 03)

This file is self-contained. Execute it verbatim. Do not go looking for a syllabus, an
index, a scenario file or a prior guide: everything you need — the role, the reader, the
example domain, all 933 syllabus leaves, the diagram manifest, the file paths — is below.

---

# ROLE

You are a JDK platform engineer and interview coach who works at the level of the
specification and the source. You have read JLS 21 and JVMS 21 chapter by chapter, and
`java.lang`/`java.math`/`java.time` line by line across JDK 7, 8, 11, 17 and 21:
`String.hashCode` with its `hash`/`hashIsZero` pair, `String.equals`' coder short-circuit,
`StringLatin1`/`StringUTF16` delegation, `AbstractStringBuilder.newCapacity` routing through
`ArraysSupport.newLength`, `StringConcatFactory.makeConcatWithConstants`, `IntegerCache` with
its `low`/`high`/`archivedCache` fields, `Enum`'s `name`/`ordinal` finals and the generated
`$VALUES`/`$SwitchMap`, `Throwable.fillInStackTrace` and the lazy `backtrace`,
`BigDecimal.intCompact` with `INFLATED = Long.MIN_VALUE`, `Instant`'s `long seconds` +
`int nanos`.

You read bytecode fluently. `javap -c -p -v` is your default evidence for any claim about
what the language *compiles to*: `i = i++`, compound-assignment narrowing, string switch,
enum switch, enhanced-for desugaring, `invokedynamic` concatenation, bridge methods,
`this$0`/`val$x` capture fields, the `Code` attribute's exception table, `finally`
duplication, try-with-resources' `$closeResource`.

Your authority order is: **JLS/JVMS > OpenJDK source > JDK javadoc > JEP text > JDK bug
database and peer-reviewed papers > engineer blog posts.** You never state a blog claim as
fact when the specification says otherwise, and you actively hunt version-stale folklore —
`strictfp` being meaningful, the string pool living in PermGen, `substring` sharing its
backing array, `+` compiling to `StringBuilder`, `access$000` bridges, reflection mutating
`final` fields, the platform-dependent default charset, helpful NPEs being off by default,
`super()` having to be the first statement, inner classes being unable to hold static
members — and you correct each one while stating what used to be true, because interviewers
still ask for the old form.

You teach **mechanism, not usage**. "`Integer` caches small values" is not an explanation;
"`Integer.valueOf` returns `IntegerCache.cache[i + 128]` when `i` is between `IntegerCache.low`
and `IntegerCache.high`, and the JLS mandates only −128..127, which is why the boundary between
127 and 128 flips `==`" is. Every claim about cost, memory, ordering or initialization is either
derived on the page or quoted from source with the quoted lines explained.

You are also an interview coach: you know which of these facts get asked, in what phrasing, and
what a strong 90-second answer sounds like versus a weak one.

---

# CONTEXT

## Reader level

A backend Java engineer with 3–4 years of professional experience, writing Java 21 idiomatic
code daily (Spring Boot 3.x, records, streams), preparing for a senior/FAANG-level interview
loop.

**Assume they already know**, without re-teaching: how to declare classes, interfaces, enums
and records; how to write a `for` loop, a `switch`, a `try`/`catch`; generics syntax and the
diamond; lambdas, method references and basic streams; that `String` is immutable; that
`equals` and `hashCode` should be overridden together; that `BigDecimal` exists and `double`
is wrong for money; that autoboxing happens; big-O notation.

**Assume they do not have** the mechanism-level model underneath any of it. They cannot say
why `Math.abs(Integer.MIN_VALUE)` is negative, what a compound assignment's hidden cast does,
why `flag ? 1 : nullInteger` throws even when `flag` is true, what `$VALUES` is, when a class
is initialized and when reading a constant does not initialize it, what the `Code` attribute's
exception table costs at runtime, why a bridge method throws `ClassCastException` with no cast
in their source, why `2.0` and `2.00` are unequal `BigDecimal`s, or why `Duration.ofDays(1)`
and `Period.ofDays(1)` diverge across a DST boundary. They have absorbed version-stale folklore
from blogs. That gap is the entire reason these notes exist.

## Purpose

These notes are a **detailed one-stop reference plus deep interview prep**. One document set the
reader never needs to supplement with a blog, a Stack Overflow answer, or a second book. They
must serve two readings equally well:

1. a first careful cover-to-cover read that builds the model from nothing, and
2. a night-before-the-interview re-read that reloads the numbers, the traps and the answer shapes.

Coverage is driven by the topic, not by any individual reader's measured gaps. Write for every
reader of this level.

## Target version

**Java 21 LTS** is the baseline for every constant, signature and behaviour. Anything introduced
or changed in Java 22–26 is marked inline with its version. Anything that changed *away from*
what older material still claims is flagged as a version trap, stating both what is true in 21
and what used to be true.

## Adjacent topics

These sibling guides exist. For each, the rule is: **state the mechanism in one self-contained
paragraph here, give the reader enough to answer the question, then point to the sibling for the
full treatment.** Never send the reader away empty-handed, and never duplicate a sibling's full
chapter.

| Guide | Owns | What this file still owes the reader |
|---|---|---|
| 01 DSA fundamentals | big-O, amortised analysis as a technique, hashing theory | the amortised argument for `StringBuilder` growth, stated in full here |
| 02 Java collections | `HashMap`/`ArrayList`/`TreeMap` internals, iterators, the collections API | how `equals`/`hashCode`, erasure, boxing and enum keys land in a hash table — one paragraph each, then point |
| 04 Modern Java | lambdas, streams, `Optional`, records, sealed types, pattern matching, text blocks, virtual threads | the language-substrate half: `invokedynamic` for lambdas, record `Object`-method generation, `var` inference rules, why a captured local must be effectively final |
| 05 Concurrency | the memory model, happens-before, locks, `ThreadLocal`, CAS | `final`-field freeze semantics, safe publication of immutables, class-init locking and deadlock, `synchronized` on a boxed value, the `InterruptedException` protocol — mechanism here, model in 05 |
| 06 JVM internals | GC, JIT, class loaders, heap dumps, JMH, object layout tooling | the language-visible slice: object header arithmetic, escape analysis of a box, `<clinit>` vs `<init>`, `ExceptionInInitializerError` diagnosis, `javap` reading |
| 07 Spring core | the container, proxies, AOP | why annotations do nothing without a reader, why `getClass()` on a proxy surprises you, what `-parameters` buys Spring |
| 08 Spring Data JPA | persistence context, entity lifecycle | `equals`/`hashCode` on entities, `BigDecimal` column mapping, why records are wrong for entities |
| 09 SQL databases | schema and query mechanics | how to store money (`NUMERIC(19,4)`) and time (`TIMESTAMP WITH TIME ZONE`) |
| 12 API design | REST contracts, JSON | ISO-8601 on the wire, enum codes on the wire, error contracts that do not leak stack traces |
| 13 Web security | OWASP, crypto, deserialization gadget chains | Java serialization as an RCE surface, hash flooding, ReDoS, `char[]` for passwords |
| 16 Testing | JUnit, Mockito, Testcontainers | `Clock` injection for testable time, `assertThrows`, why `BigDecimal.equals` breaks assertions |
| 20 Observability | metrics, logs, traces | log-the-throwable discipline, `{}` placeholders, JFR exception events |

## The example domain — QuizStakes

**Every example in these notes comes from the QuizStakes domain, reproduced in full below.
Never write `Dog extends Animal`, `Foo`, `Bar`, `thread1`, `Person`, `Employee` or any other
throwaway example.** Use these entities, these status codes, these numbers, verbatim. A reader
who meets `CLIENT_BONUS_RESERVED` once must meet the same name every time. Where a concept is
genuinely domain-free (`i = i++`, shift masking, `0.1 + 0.2`), still frame it in the domain:
the loop counter is over stake reservations, the shifted value is a restriction bit mask, the
floating-point sum is a bonus balance.

### What QuizStakes is

A regulated skill-based betting platform. A prospect registers, supplies personal details,
address, employment and income; is scored for affordability; accepts agreements; uploads
identity documents which an automated vendor verifies (inconclusive cases fall to human
review); and on approval the account is activated. The client deposits by card or bank
transfer. A first deposit with a valid coupon earns a bonus: **10% of the deposit, capped at
100**. Bonus money is stakeable but never directly withdrawable. Each stake draws
proportionally from bonus before cash. Winnings credit as cash. Withdrawals go out by card
(immediately, via the PSP) or by bank transfer (batched, with operator sign-off). The Quiz
Engine itself is a black box exposing exactly three operations: `ReserveStake`, `SettleStake`,
`VoidStake`.

### Vocabulary (use exactly these words)

| Term | Meaning |
|---|---|
| **Prospect** | Has begun registration. Has an application and an account shell; every money action is restricted. |
| **Client** | Has an activated account. |
| **Application** | The onboarding case. Has a lifecycle, a status, an audit trail. |
| **Account** | Created at registration, not at activation. Activation is a status change. |
| **Account shell** | An account that exists but carries system restrictions on every money action. |
| **Wallet** | The client-facing view of their money. Four buckets, two derived totals. |
| **Ledger** | The double-entry record. Sole source of truth for money. |
| **Cash** | Money from a deposit or a win. Stakeable and withdrawable. |
| **Bonus** | Promotional money. Stakeable, never directly withdrawable. Converts to cash only by winning. |
| **Stakeable** | Cash available + bonus available. Derived, never stored. |
| **Withdrawable** | Cash available only. Derived, never stored. |
| **Reserved** | Funds committed to an open stake or a pending withdrawal. |
| **Rail** | A mechanism for moving money: card deposit, bank deposit, card withdrawal, bank withdrawal. |
| **Instrument** | A specific card or bank account belonging to a client. |
| **Closed loop** | Withdrawals return to the instrument the money came from, up to the deposited amount. |
| **Gate** | A compliance condition that must hold before a transition is permitted. |
| **Restriction** | A block on a specific client action. Additive, overlapping, sourced, individually lifted. |
| **Requirement** | An outstanding document obligation. |
| **Referral** | A case a machine could not decide, routed to a human. |
| **PaymentRun** | A batch of approved bank withdrawals with operator sign-off. |
| **Suspense** | A holding position for money received but not yet attributable to a client. |

### Services you may name

`ApplicationGateway`, `RouterInt`, `JwtService`, `AccountOpening`, `PersonalDetails`,
`ClientAgreements`, `AssessmentService`, `AccountActivation`, `DocumentVerification`,
`DocumentRequirements`, `ScreeningService`, `ApplicationHistory`, `AccountMaintenance`,
`ClientRestrictions`, `InternalPlatforms`, `PaymentService`, `FundsLedger`, `CardPayments`,
`BankDeposits`, `BankWithdrawal`, `BonusService`, `BalanceView`, `ProfileService`,
`PendingActions`, `NotificationService`.

### Status codes (verbatim — never invent one)

Application capture (`AO-`): `AO-099 UNIQUENESS_FAILED`, `AO-100 IDENTITY_CREATED`,
`AO-110 CONTACT_VERIFICATION_PENDING`, `AO-111 CONTACT_VERIFIED`, `AO-115 DOB_PHONE_PENDING`,
`AO-116 DOB_PHONE_CAPTURED`, `AO-119 AGE_INELIGIBLE`, `AO-120 ADDRESS_PENDING`,
`AO-121 ADDRESS_CAPTURED`, `AO-129 JURISDICTION_INELIGIBLE`, `AO-135 DUPLICATE_CHECK_PENDING`,
`AO-136 DUPLICATE_CHECK_CLEAR`, `AO-139 DUPLICATE_IDENTITY`, `AO-140 WEALTH_PENDING`,
`AO-141 WEALTH_ACCEPTABLE`, `AO-145 WEALTH_REFERRED`, `AO-149 WEALTH_REJECTED`,
`AO-200 AGREEMENTS_PENDING`, `AO-201 AGREEMENTS_ACCEPTED`, `AO-290 AGREEMENTS_SUPERSEDED`,
`AO-300 PROFILE_COMPLETE`, `AO-400 SUBMITTED`.

Activation (`AA-`): `AA-500 SCREENING_IN_PROGRESS`, `AA-501 SCREENING_CLEAR`,
`AA-550 SCREENING_POTENTIAL_MATCH`, `AA-599 SCREENING_PROHIBITED`, `AA-600 DOCUMENTS_REQUESTED`,
`AA-610 DOCUMENTS_UPLOADED`, `AA-611 DOCUMENTS_VERIFIED`, `AA-650 DOCUMENTS_REFERRED`,
`AA-690 DOCUMENTS_REJECTED`, `AA-699 DOCUMENTS_EXHAUSTED`, `AA-700 REVIEW_QUEUED`,
`AA-710 REVIEW_IN_PROGRESS`, `AA-711 REVIEW_APPROVED`, `AA-799 REVIEW_DECLINED`,
`AA-800 ACTIVATING`, `AA-801 ACTIVATED`, `AA-900 DECLINED`, `AA-910 ABANDONED`,
`AA-920 WITHDRAWN`.

Card deposit uses `DEP-nnn` (e.g. `DEP-301 CAPTURED`); bank deposit uses `BDP-nnn`. The
numbered-code structure is `XX-Nnn` where `N` is the phase and the middle digit is the
disposition: `0` in progress, `1` success, `5` referred to a human, `9` failed or blocked.

Bare-name machines: account lifecycle `PENDING_VERIFICATION`, `ACTIVE`, `DORMANT`, `CLOSING`,
`CLOSED`; restriction `ACTIVE`, `LIFTED`, `EXPIRED`; document requirement `REQUIRED`,
`SUBMITTED`, `SATISFIED`, `WAIVED`, `EXPIRED`; bonus `GRANTED`, `ACTIVE`, `CONSUMED`,
`EXPIRED`, `CLAWED_BACK`.

### Restrictions

`DEPOSIT_BLOCKED`, `STAKE_BLOCKED`, `WITHDRAWAL_BLOCKED`, `DEPOSIT_LIMITED`, `WITHDRAWAL_HELD`,
`SOURCE_OF_FUNDS_REQUIRED`, `ALL_BLOCKED`, `SELF_EXCLUDED`, `COOLING_OFF`, `DORMANT_FROZEN`.
Sources: `SYSTEM_ONBOARDING`, `SYSTEM_COMPLIANCE`, `SYSTEM_LIFECYCLE`, `ADMIN`, `CLIENT`.
**Restriction identity is the pair (type, source), not the type alone** — `STAKE_BLOCKED` from
`SYSTEM_ONBOARDING` lifts automatically at `AA-801`; the same type from `ADMIN` does not.
`SELF_EXCLUDED` carries `reversibleByOperator = false`.

### Ledger positions

`CLIENT_CASH_AVAILABLE`, `CLIENT_CASH_RESERVED`, `CLIENT_BONUS_AVAILABLE`,
`CLIENT_BONUS_RESERVED`, `SUSPENSE`, `PSP_RECEIVABLE`, `BANK_SETTLEMENT`, `HOUSE_REVENUE`,
`PROMOTIONAL_EXPENSE`, `FEES`, `CHARGEBACK_LOSS`.

Derived, never stored: **Stakeable** = `CASH_AVAILABLE + BONUS_AVAILABLE`; **Withdrawable** =
`CASH_AVAILABLE`; **Total** = all four client buckets.

The win/void asymmetry, which is the domain's sharpest edge: reserved bonus returns as **cash**
on a win, as **bonus** on a void, and goes to `HOUSE_REVENUE` on a loss.

### Bonus rules (use these exact numbers)

| Rule | Value |
|---|---|
| Grant | 10% of the first deposit, capped at 100 |
| Eligibility | First deposit only, one per identity, valid coupon |
| Coupon validity | 14 days from registration |
| Expiry | 30 days from grant; unspent reverses to `PROMOTIONAL_EXPENSE` |
| Wagering requirement | None |
| Stake consumption | `min(BONUS_AVAILABLE, 10% of stake)`; remainder from cash |
| Rounding | Bonus portion **rounds down** to the minor unit; cash covers the remainder |
| Clawback | Unspent bonus first; shortfall to `PROMOTIONAL_EXPENSE` |

The canonical rounding example: a stake of **3.33** splits as **0.33 bonus + 3.00 cash**.
Rounding the other way gives 0.34 + 3.00 = 3.34, which creates money. Use this example wherever
rounding, `BigDecimal` scale, `RoundingMode` or integer division is being taught.

### Types you may declare (from the domain's type sketch)

Value types: `Money(BigDecimal amount, Currency currency)`, `ClientId`, `ApplicationId`,
`AccountId`, `PersonId`, `RoundId` (each wrapping a `UUID`), `IdempotencyKey(String value)`,
`StatusCode(domain, phase, disposition, variant)`, `Jurisdiction(country, subdivision)`,
`AgreementRef(documentId, version)`, `LimitSet(dailyDeposit, maxStake, monthlyLoss)`,
`StakeSplit(Money bonusPortion, Money cashPortion)` — **invariant: the two sum exactly to the
stake** — `Verdict(outcome, reason, decidedAt, decidedBy)` as a sealed hierarchy
(`DocumentVerdict`, `ScreeningVerdict`, `ReviewVerdict`, `WealthVerdict`),
`RestrictionKey(RestrictionType type, RestrictionSource source)`.

Aggregates: `Application`, `Account`, `Restriction`, `LedgerEntry`, `Movement`, `Position`,
`Reservation`, `Bonus`, `PaymentIntent`, `WithdrawalTransaction`, `PaymentRun`,
`InstrumentVerification`, `DocumentRequirement`, `GateSet`, `ReviewCase`.

Exceptions you may define: `InsufficientFundsException`, `RestrictedActionException`,
`IllegalTransitionException`, `LedgerImbalanceException`, `BonusIneligibleException`.

### Numbers you may quote (never invent new ones)

| Metric | Value |
|---|---|
| Registered clients | 2.4M |
| Monthly active clients | 380k |
| Concurrent sessions | 14k steady, 55k peak |
| Registrations started/day | 12k steady, 40k peak |
| Applications reaching `AO-400`/day | 7.2k steady, 24k peak |
| Manual review rate | 11% of submissions (19% on poor document quality) |
| Operators on shift | 40 steady, 90 peak; 22 cases per operator per hour |
| Card deposits | 95k/day, 40/sec peak, avg value 65 |
| Bank deposits | 6.5k/day, batch, avg value 480 |
| Bonus grants | 3.1k/day, 8/sec, avg value 42 |
| Card withdrawals | 11k/day, 12/sec, avg value 180 |
| Bank withdrawals | 7k/day, batch, avg value 260 |
| Stake reservations | 2.8M/day, 1,200/sec peak, avg value 4.20 |
| Stake settlements | 2.8M/day, 3,400/sec burst |
| Chargebacks raised | 140/day, avg value 92 |
| Ledger entries | ~19.8M/day, ~7.2B/year, ~180 bytes/row, ~1.3 TB/year |
| Ledger write rate | 230/sec sustained, 13,600/sec peak |
| Ledger hot window / retention | 90 days / 7 years |
| Identity vendor | p50 900ms, p99 38s, 600/min estate-wide cap |
| Watchlist provider | p50 1.4s, p99 25s, 30s timeout, 200/min |
| Card PSP authorise / capture / payout | p50 240ms / 180ms / 400ms; p99 11s / 6s / 9s |
| Banking partner payout file | p50 2s, p99 45s, 4 windows/day |

These are the numbers for every memory calculation, every allocation count, every "how many
`Integer` objects does this loop create" arithmetic. A boxing example iterates 2.8M stake
reservations; a `String` footprint example counts 7.2B ledger entries; a `BigDecimal` example
adds up 95k card deposits at 65 each.

---

# TASK

Write the complete Java Core bible as a set of Markdown files under
`src/notes/detailed/03-java-core/`, organised into five parts, covering **all 933 syllabus
leaves reproduced in the `# SYLLABUS` section below**, illustrated by **all 139 diagrams
enumerated in the `# DIAGRAM MANIFEST` section below**, written to the exact file paths in the
`# OUTPUT CONTRACT` section below.

## Tier structure

The notes are organised in these parts, in this order:

| Part | Contains |
|---|---|
| `PART 1 — BASICS` | why the language substrate is a topic, the mental model, the vocabulary, the full surface — primitives, conversions, operators, control flow, wrappers, `String`, the `Object` methods, classes and initialization, modifiers, inheritance, interfaces, nested classes, enums, exceptions, generics, arrays, packages and modules, annotations, the `java.lang` inventory — and the guarantees each carries |
| `PART 2 — INTERMEDIATE` | cost models, `String` performance and text processing, immutability design, numbers and money, date and time, exceptions in practice, generics in anger, copying and composite equality, object lifecycle and references, serialization, null discipline, reflection, pass-by-value, the design idioms, and the "which construct do I reach for" decisions |
| `PART 3 — ADVANCED (INTERNALS)` | how it actually works inside — the `javac` pipeline and the full desugaring catalogue with `javap` evidence, `String`/`StringBuilder`/boxing/erasure internals, class loading and initialization, method dispatch (vtable, itable, the five invoke instructions, inline caches), object layout and memory arithmetic, exception mechanics, enum internals, nested-class internals, `final` semantics and constant folding, `hashCode` internals, `BigDecimal`/`BigInteger` internals, floating-point internals, `java.time` internals, the version history, and the observability toolkit |
| `PART 4 — BUILD IT` | complete, compiling, generic Java 21 reimplementations — `MyString`, `MyStringBuilder`, `MyInteger`, the generic constructs, enum-shaped builds, exception and resource builds, value-object and money builds, and the diagnostic harnesses — each followed by a "Diff vs the real one" table |
| `PART 5 — INTERVIEW AND RETENTION` | the 80 questions with answer shapes, the consolidated trap index, the version-stale table, and the drills |

## Hard instructions

Every one of these is mandatory.

- **No line limit and no file-count limit.** There is no upper bound on the length of the notes
  or on how many files they are split across. Completeness beats brevity every single time.
  Never truncate, never write "and so on", never write "similar to the above", never defer a
  concept for space. If a file grows large, split it into more files rather than cutting
  content, and register the new file in `00-index.md`.
- **Output format is Markdown (`.md`).** Every file.
- **Diagrams are standalone SVG files.** Write each diagram as its own file in
  `src/notes/detailed/03-java-core/diagrams/`, named `D-NN-short-slug.svg`, and embed it at the
  point of explanation with a Markdown image reference and a caption:

  ```
  ![D-07 — Two's complement and why Math.abs(Integer.MIN_VALUE) is negative](../diagrams/D-07-twos-complement.svg)

  **D-07** — Two's complement and why `Math.abs(Integer.MIN_VALUE)` is negative.
  ```

  **Never inline `<svg>` in the Markdown** — GitHub and VS Code strip it. **Never use ASCII
  art** — it deforms across renderers and fonts. Where the manifest's `Type` column says
  `table`, a Markdown table is the correct rendering and no SVG is required. Every SVG must
  have:
  - an explicit `viewBox` and no `width`/`height` that forces a fixed pixel size,
  - no text smaller than 11px,
  - no reliance on external fonts or CSS (use `font-family="sans-serif"` and presentation
    attributes, not classes),
  - fills and strokes legible against both light and dark backgrounds: give every filled shape
    an explicit contrasting `stroke`, set an explicit `fill` on every `<text>`, and never rely
    on black-on-transparent text alone,
  - every label, constant and value named in the manifest's `Must show` cell visible as text.
- **Every concept follows this exact chain, in this order:**
  `Concept → Why it exists → How it works → SVG → Code → Gotcha`.
  All six links. If a link genuinely does not apply to a concept, say so in one line ("No
  gotcha: the rule has no surprising edge.") rather than silently dropping it.
- **Java code is complete and runnable as written.** Full class and method bodies, real field
  names, real generics, real edge cases, real QuizStakes types. Strip only the trivia: `import`
  statements, `package` declarations, and `main`-method scaffolding where it adds nothing.
  **No `...` elisions, no "implementation omitted", no pseudo-code standing in for real code.**
  Quoted JDK source may be excerpted to the relevant lines, but every line quoted must then be
  explained. All code is Java 21 idiomatic: records, sealed interfaces, pattern-matching
  `switch`, text blocks, `var` sparingly.
- **Callouts.** Use exactly these three markers, bolded, inline at the point they belong. Do not
  invent others.
  - `**Pitfall:**` — the wrong belief, the symptom it produces, the fix.
  - `**Insight:**` — the non-obvious mechanism that makes the rest click.
  - `**Interview:**` — how this is actually asked, and the one-line answer.

  Every syllabus leaf tagged `[TRAP]` must carry a `**Pitfall:**`.
- **Every part ends with all three of these:**
  1. a **summary table** covering that part's concepts,
  2. **10 interview Q&As** with full model answers — not hints, the answer a candidate would
     actually say out loud, at speaking length,
  3. **5 "predict the output" puzzles** — a complete code snippet, the actual output, and an
     explanation of *why* the output is what it is.

  Where a part is split across many files, these three go in that part's interview file as named
  in the `# OUTPUT CONTRACT`, and cover the whole part.
- **Version-specific behaviour is always called out explicitly.** Whenever a behaviour, a
  constant, a default or an API shape differs across Java 7 / 8 / 9+ / 21, say which version
  does what, inline, at the point of the claim. Where a widely-repeated claim is version-stale,
  state what is true today, what used to be true, and flag it as a version trap. **There are 17
  `[VERSION-TRAP]` leaves in the syllabus below; the three that matter most are `strictfp` being
  a no-op since Java 17 (JEP 306), helpful NPE messages being on by default since Java 15, and
  the default charset being UTF-8 since Java 18 (JEP 400). Sweep for the rest and treat every
  one the same way.**
- **Tag obligations.** The syllabus tags below are instructions, not decoration:
  - `[PROVE]` — work the argument through on the page. Do not state the result.
  - `[SOURCE]` — quote the real JDK source or spec text (short excerpt) and explain every line.
  - `[BUILD]` — ship complete, compiling, generic code.
  - `[TRAP]` — carry a `**Pitfall:**` marker: wrong belief, symptom, fix.
  - `[RESEARCH]` — re-verify against the JDK 21 source, javadoc, JLS/JVMS or the named JEP before
    writing. **131 leaves carry this tag.** If you cannot verify a claim, say so explicitly in the
    text rather than asserting it.
  - `[VERSION-TRAP]` — state what is true in 21 and what used to be true.
  - `[X-REF nn]` — one self-contained mechanism paragraph here, then point to guide nn.
  - `[NUM]` — state the number or byte arithmetic explicitly, with the arithmetic shown.
  - `[BYTECODE]` — show the `javap -c` output and read it instruction by instruction.
- **Three claims are explicitly unverified in the syllabus's research pass. Do not print a number
  for any of them without confirming it first, and if you cannot confirm it, say so in the text
  rather than asserting it:**
  1. the default of `-XX:StringTableSize` (leaf 3.2.11) — confirm against
     `java -XX:+PrintFlagsFinal -version` on a real JDK 21 before printing 65536,
  2. the default of `-XX:MaxJavaStackTraceDepth` (leaf 3.9.10) — same, before printing 1024,
  3. the *Effective Java* item-number mapping (leaf 2.14.11) — verify item numbers against the
     book, or name the item by its title without a number.
- **No emojis. No filler.** No "let's dive in", "great question", "as we all know", "it's worth
  noting". Lead with content.
- **A table for any comparison of three or more things.**
- **Every example uses the QuizStakes domain** as specified in `# CONTEXT`, with the entity
  names, status codes and numbers verbatim.
- The notes end with a flat `## Atomic concept checklist`, one bullet per distinct concept,
  phrased as a one-line assertion the reader can self-quiz against. Downstream agents parse this
  list, so keep it flat — no nesting, no headings inside it.

## Leaf coverage

The syllabus below has **933 leaves** (Part 1: 291, Part 2: 232, Part 3: 257, Part 4: 61,
Part 5: 92). **Every leaf must appear in the notes.** Any leaf you cannot cover must be listed in
a `## Deferred` block at the end of the file that owns it, with the leaf number and a one-line
reason. An empty `## Deferred` block is the expected outcome.

---

# SYLLABUS

**Target version: Java 21 LTS** (baseline for every constant, signature and behaviour below).
Anything introduced or changed in Java 22–26 is marked inline with its version. Anything that
changed *away from* what older material still claims (notably `strictfp`, which has been a no-op
since Java 17, and `new String(...)`-era pool geography) is marked `[VERSION-TRAP]`.

Tag legend:

| Tag | Meaning for the write pass |
|---|---|
| `[PROVE]` | the bible must work the argument through, not state the result |
| `[SOURCE]` | must quote real JDK source or spec text (short excerpt) and explain every line |
| `[BUILD]` | must ship complete, compiling, generic code |
| `[TRAP]` | must carry a `**Trap:**` marker — wrong belief, symptom, fix |
| `[RESEARCH]` | leaf exists because of the research phase; re-verify against the cited source before writing |
| `[VERSION-TRAP]` | widely-repeated claim that is version-stale; state what is true in 21 and what used to be true |
| `[X-REF nn]` | one-paragraph mechanism here, full treatment in guide nn |
| `[NUM]` | must state the number/byte arithmetic explicitly |
| `[BYTECODE]` | must show `javap -c` output and read it instruction by instruction |

In these notes the `[TRAP]` marker is rendered as `**Pitfall:**`, per the hard instructions above.

---

## PART 1 — BASICS

### §1.1 Why the language substrate is a topic at all

1.1.1 Java's 1995 design goals: memory safety, portability, garbage collection, no pointer
      arithmetic, single inheritance of implementation, dynamic linking.
1.1.2 Source → `javac` → class file → JVM: which behaviour is decided by the compiler and which by
      the runtime. Every "why does Java do X" answer sits on one side of that line. `[X-REF 06]`
1.1.3 The three normative documents: JLS (language semantics), JVMS (class file and runtime), API
      javadoc (library contract) — and which one to cite for which claim. `[RESEARCH]`
1.1.4 JLS 21 chapter map, all 19 chapters, so you know where an answer lives: 3 lexical,
      4 types/values/variables, 5 conversions and contexts, 6 names, 7 packages/modules, 8 classes,
      9 interfaces, 10 arrays, 11 exceptions, 12 execution, 13 binary compatibility,
      14 blocks/statements/patterns, 15 expressions, 16 definite assignment, 17 threads and locks,
      18 type inference. `[RESEARCH]` `[SOURCE]`
1.1.5 Why primitives exist at all: 1995 performance versus "everything is an object", and Project
      Valhalla's plan to erase the distinction with value classes. `[RESEARCH]`
1.1.6 Static typing with mostly-unreified generics: checked at compile time, erased at runtime, and
      the consequences that follow all the way down this file.
1.1.7 Backward compatibility as the organising constraint — why `clone`, `finalize`,
      `java.util.Date`, `Vector` and `Hashtable` are still shipping. `[TRAP]`
1.1.8 Binary compatibility (JLS 13) vs source compatibility vs behavioural compatibility, with one
      example of each being broken.
1.1.9 The release train: 6-month feature releases, LTS at 8/11/17/21/25, preview features and
      `--enable-preview`, incubator modules, and why a preview feature is not interview material
      but knowing it is preview is. `[RESEARCH]`
1.1.10 What "Java 21" means for this file, and how to check what you are actually running
       (`java -version`, `Runtime.version()`, `System.getProperty("java.version")`).

*(10 leaves)*

### §1.2 Lexical structure and literals

1.2.1 Unicode source: the compiler reads UTF-16 code points; identifiers may be non-ASCII.
1.2.2 Unicode escapes `\uXXXX` are processed **before** tokenisation — so a backslash-u-000A
      escape written inside a line comment ends the comment and can break compilation. The write
      pass must show the exact escape sequences in a fenced block, not inline. `[TRAP]` `[SOURCE]`
1.2.3 Identifiers: rules, `$` convention reserved for generated code, `_` alone is a keyword since
      Java 9. `[RESEARCH]`
1.2.4 The keyword list, plus the contextual keywords added later: `var`, `yield`, `record`,
      `sealed`, `permits`, `non-sealed`, `when`. Why they are contextual, not reserved. `[RESEARCH]`
1.2.5 Integer literals: decimal, hex `0x`, octal `0`, binary `0b` (Java 7), `L` suffix.
1.2.6 Leading-zero octal literals: `int x = 010;` is 8. `[TRAP]`
1.2.7 Underscores in numeric literals (Java 7) and where they are illegal (adjacent to the decimal
      point, at either end, before an `L`).
1.2.8 Floating-point literals: `d`/`f` suffixes, exponent form, hex float literals `0x1p-3`.
1.2.9 `float f = 1.1;` does not compile — a bare decimal literal is a `double`. `[TRAP]`
1.2.10 Character literals, escape sequences, `'A'`, and `\s` (Java 15) for a significant space.
1.2.11 String literals, and the fact that a literal is a constant expression that gets interned.
1.2.12 Text blocks (Java 15): triple-quote delimiter, incidental-whitespace stripping,
       `\` line-continuation, `\s`, `stripIndent`/`translateEscapes` as the underlying methods.
       `[X-REF 04]`
1.2.13 `null` is a literal with the null type; there is no `Null` class.
1.2.14 Separators and operators; the full operator table by precedence.
1.2.15 Comments, and the `/** */` doc comment as an input to `javadoc` and to IDE inference.

*(15 leaves)*

### §1.3 Primitive types, exactly

1.3.1 The eight primitives and the two other value kinds in the JVM but not the language
      (`returnAddress`, `boolean` as `int` in bytecode). `[RESEARCH]` `[NUM]`
1.3.2 Bit widths, ranges and default values in one table: `byte` 8, `short` 16, `char` 16 unsigned,
      `int` 32, `long` 64, `float` 32, `double` 64, `boolean` unspecified. `[NUM]`
1.3.3 Field defaults (0/0L/0.0f/0.0d/' '/false/null) versus locals, which have **no** default
      and are subject to definite assignment. `[TRAP]`
1.3.4 `char` is an unsigned 16-bit UTF-16 **code unit**, not a character. `[TRAP]`
1.3.5 Two's complement: why `Integer.MIN_VALUE` has no positive counterpart and
      `Math.abs(Integer.MIN_VALUE)` is negative. `[PROVE]` `[TRAP]` `[NUM]`
1.3.6 Silent integer overflow; `Math.addExact`/`subtractExact`/`multiplyExact`/`incrementExact`/
      `negateExact`/`toIntExact` and `ArithmeticException`.
1.3.7 `Math.floorDiv`/`floorMod` vs `/` and `%` for negative operands — `-7 % 3 == -1` but
      `Math.floorMod(-7, 3) == 2`. `[TRAP]` `[NUM]`
1.3.8 Integer division truncates toward zero: `1/2 == 0`, `-1/2 == 0`. `[TRAP]`
1.3.9 Division by zero: `ArithmeticException` for integers, `Infinity`/`NaN` for floating point.
      `[TRAP]`
1.3.10 Shifts: `<<`, `>>` (arithmetic, sign-extending), `>>>` (logical). No `<<<`.
1.3.11 Shift distance is masked: `x << 32 == x` for `int` (mask 0x1f), `x << 64 == x` for `long`
       (mask 0x3f). `[TRAP]` `[PROVE]` `[NUM]`
1.3.12 `>>>` on a `byte`/`short` promotes to `int` first, so `b >>> 1` on a negative byte is not
       what you expect. `[TRAP]`
1.3.13 `float`/`double` are IEEE 754 binary32/binary64: sign, exponent, mantissa layout. `[NUM]`
1.3.14 `0.1 + 0.2 != 0.3`; `Float.MIN_VALUE` is the smallest positive, not the most negative.
       `[TRAP]`
1.3.15 `NaN != NaN`; `Double.NaN == Double.NaN` is false but `Double.valueOf(NaN).equals(...)` is
       true, and `Double.compare` orders NaN above everything. `[TRAP]` `[PROVE]`
1.3.16 `+0.0 == -0.0` is true, but `Double.compare(0.0, -0.0) > 0` and
       `Double.valueOf(0.0).equals(-0.0)` is false — the three-way inconsistency. `[TRAP]` `[PROVE]`
1.3.17 `boolean` has no defined size in the JVM; in arrays it is one byte, in fields typically one
       byte after alignment. `[NUM]` `[RESEARCH]`
1.3.18 `void` and `Void`: the pseudo-type and the uninstantiable placeholder class.
1.3.19 Choosing a primitive: `int` by default, `long` for IDs/timestamps/accumulators, `byte`/`short`
       only in arrays and wire formats, never `float` for anything you care about.
1.3.20 The unsigned story: Java has no unsigned types, but `Integer.toUnsignedLong`,
       `Integer.divideUnsigned`, `Integer.remainderUnsigned`, `Integer.compareUnsigned`,
       `Byte.toUnsignedInt` and `Long.toUnsignedString` exist since Java 8. `[RESEARCH]`
1.3.21 `byte b = (byte) 200;` is −56 — the sign-extension bug that eats binary protocol code.
       `[TRAP]` `[NUM]`

*(21 leaves)*

### §1.4 Reference types and the object model

1.4.1 The four reference kinds: class, interface, array, type variable. Enums and records are
      classes; annotations are interfaces.
1.4.2 A reference variable holds an address (or a compressed oop); the object lives on the heap.
      `[X-REF 06]`
1.4.3 Stack slot vs heap object vs static field: where each variable kind lives.
1.4.4 `null` semantics: assignable to every reference type, `instanceof null` is false,
      `(String) null` is legal, `null.toString()` is an NPE, `String.valueOf(null)` is ambiguous.
      `[TRAP]`
1.4.5 The `Object` root, and that arrays and interfaces also inherit `Object`'s methods.
1.4.6 Object identity vs equality vs equivalence — three different questions.
1.4.7 The subtyping relation: `extends`, `implements`, array covariance, `Object` at the top,
      the null type at the bottom.
1.4.8 Intersection types (`<T extends A & B>`) and where you meet one in an error message.
1.4.9 Value-based classes: the `@jdk.internal.ValueBased` annotation on the wrappers, `Optional`
      and the `java.time` types, and what "do not synchronize on, do not depend on identity" means
      in practice. `[RESEARCH]` `[TRAP]`
1.4.10 `synchronized (integerLock)` on a boxed `Integer` is a real bug and now produces a warning.
       `[TRAP]` `[RESEARCH]` `[X-REF 05]`

*(10 leaves)*

### §1.5 Variables, scope, and definite assignment

1.5.1 The seven variable kinds (JLS 4.12.3): class, instance, array component, method parameter,
      constructor parameter, exception parameter, local. `[SOURCE]`
1.5.2 Local variables are not default-initialised; definite assignment (JLS 16) is a compile-time
      dataflow analysis. `[PROVE]`
1.5.3 Definite assignment across `if`/`else`, `while (true)`, `switch`, and try/catch — the cases
      where the compiler refuses a `final` blank local.
1.5.4 Blank finals: a `final` field assigned exactly once in every constructor path, and a `final`
      local assigned once.
1.5.5 Scope and shadowing: a parameter shadowing a field, a local shadowing a field, `this.x = x`.
      `[TRAP]`
1.5.6 Obscuring: a variable name hiding a type name.
1.5.7 Hiding: a subclass field with the same name as a superclass field — two fields exist, and
      access is by static type. `[TRAP]` `[PROVE]`
1.5.8 `var` (Java 10) is inference, not dynamic typing; where it is banned (fields, parameters,
      return types, `var x = null`, array initialisers). `[X-REF 04]`
1.5.9 `var` and the anonymous-class / intersection type it can capture, which you cannot spell.
       `[RESEARCH]`
1.5.10 Effectively final: the definition, the compiler rule, and where it is required (lambda and
       anonymous-class capture, try-with-resources resource expression, multi-catch parameter,
       enhanced-for variable in a capture).
1.5.11 Instance initializer blocks and their ordering relative to field initialisers and the
       constructor body.
1.5.12 Static initializer blocks, textual ordering, and the "illegal forward reference" rule.
       `[TRAP]`
1.5.13 Local variable table, slot reuse, and why a debugger loses variable names without `-g`.
       `[X-REF 06]` `[RESEARCH]`

*(13 leaves)*

### §1.6 Operators and expression evaluation

1.6.1 Full precedence and associativity table.
1.6.2 Left-to-right evaluation of operands is **guaranteed** (JLS 15.7) — unlike C. `[SOURCE]`
1.6.3 Evaluation order of the receiver, the arguments, and the actual call in
      `a().b(c(), d())`.
1.6.4 `i = i++` leaves `i` unchanged. `[PROVE]` `[TRAP]` `[BYTECODE]`
1.6.5 `i++ + ++i` and why the answer is well defined in Java and undefined in C.
1.6.6 Compound assignment has a **hidden narrowing cast**: `byte b = 10; b += 300;` compiles;
      `b = b + 300;` does not. `[TRAP]` `[PROVE]` `[SOURCE]`
1.6.7 `char c = 'a'; c += 1;` works; `c = c + 1;` does not.
1.6.8 Short-circuit `&&`/`||` vs non-short-circuit `&`/`|` on booleans; when the eager form is a bug.
      `[TRAP]`
1.6.9 Bitwise `&`, `|`, `^`, `~` on integral types; common masks and flags idioms.
1.6.10 The conditional operator `?:`: its type is computed by a table of promotion rules, not by
       the branch taken. `[TRAP]`
1.6.11 `flag ? 1 : nullInteger` throws NPE even when `flag` is true, because the expression type is
       `int` and the other branch is unboxed. `[PROVE]` `[TRAP]`
1.6.12 `Object o = true ? Integer.valueOf(1) : Double.valueOf(2.0);` yields `1.0`. `[TRAP]`
       `[PROVE]`
1.6.13 `instanceof` and pattern `instanceof` (Java 16), flow scoping of the binding variable.
       `[X-REF 04]`
1.6.14 Cast expressions: upcast (always safe), downcast (checked at runtime, `ClassCastException`),
       primitive cast (may truncate).
1.6.15 `==` on primitives compares values; on references compares identity; mixed operand types
       force unboxing. `[TRAP]`
1.6.16 String concatenation `+` as an operator with its own conversion context (JLS 5.4);
       `"" + null` is `"null"`, and `char + int` is arithmetic not concatenation. `[TRAP]`
1.6.17 `System.out.println('a' + 1)` prints 98; `println("" + 'a' + 1)` prints "a1". `[TRAP]`
1.6.18 The `new` operator, array creation expressions, and method-reference/lambda expressions as
       poly expressions with no standalone type. `[X-REF 04]`
1.6.19 Constant expressions (JLS 15.29): what qualifies, and the three places it changes semantics
       (`case` labels, `switch` on strings, `static final` inlining, unreachable-code analysis).
       `[SOURCE]`

*(19 leaves)*

### §1.7 Conversions and contexts (JLS 5)

1.7.1 The eleven conversion kinds: identity, widening primitive, narrowing primitive, widening and
      narrowing reference, boxing, unboxing, unchecked, capture, string, and the forbidden ones.
      `[SOURCE]` `[RESEARCH]`
1.7.2 The six contexts: assignment, invocation (strict/loose/variable-arity), string, casting,
      numeric (unary and binary promotion), and which conversions each permits. `[SOURCE]`
      `[RESEARCH]`
1.7.3 Widening primitive conversions `byte→short→int→long→float→double`, `char→int`, and the two
      that **lose precision**: `int→float` and `long→float`/`long→double`. `[TRAP]` `[PROVE]`
      `[NUM]`
1.7.4 `(float) 16_777_217` is 16777216.0 — a widening conversion that loses data. `[PROVE]` `[NUM]`
1.7.5 Narrowing conversions require an explicit cast and truncate high-order bits silently.
1.7.6 The constant-narrowing exception: `byte b = 10;` is legal because 10 is a constant expression
      in range; `byte b = i;` is not. `[TRAP]`
1.7.7 Unary numeric promotion: anything narrower than `int` becomes `int`. `-b` on a `byte` yields
      an `int`.
1.7.8 Binary numeric promotion: `double > float > long > int`, and everything narrower becomes
      `int`. `[SOURCE]`
1.7.9 `short + short` is an `int`, so `s = s + s;` does not compile. `[TRAP]`
1.7.10 `long` arithmetic done in `int` and then widened: `long ms = 24 * 60 * 60 * 1000 * 1000;`
       overflows before the assignment. `[TRAP]` `[PROVE]` `[NUM]`
1.7.11 `float`/`double` to integral conversion: truncates toward zero, saturates at MIN/MAX,
       NaN becomes 0. `[TRAP]` `[NUM]`
1.7.12 `(int) 1e20` is `Integer.MAX_VALUE`; `(int) Double.NaN` is 0. `[NUM]`
1.7.13 Boxing and unboxing conversions, and the exact valueOf call each inserts.
1.7.14 Widening then boxing is allowed; boxing then widening is not — `Long l = 3;` does not
       compile. `[TRAP]` `[PROVE]`
1.7.15 String conversion: how any value becomes a `String` in a concatenation, including `null`
       and `char[]`.
1.7.16 Unchecked conversion and where the `unchecked` warning comes from.
1.7.17 Capture conversion: what `capture of ? extends E` in an error message means.

*(17 leaves)*

### §1.8 Control flow

1.8.1 `if`/`else`, the dangling-else binding rule, and why braces are not optional in practice.
1.8.2 `while`, `do-while`, the three-part `for`, and the enhanced `for`.
1.8.3 Enhanced-for desugaring: `Iterator` for `Iterable`, index loop for arrays. `[X-REF 02]`
      `[BYTECODE]`
1.8.4 `break`, `continue`, and labelled forms; the only legal use of a label in Java.
1.8.5 `return`, and abrupt completion as a specified concept (JLS 14.1).
1.8.6 Classic `switch` statement: fall-through, `default` position, the permitted selector types
      (`byte`/`short`/`char`/`int`, their wrappers, `String` since 7, enums, and patterns since 21).
1.8.7 Missing `break` fall-through as a bug class, and why `-Xlint:fallthrough` exists. `[TRAP]`
1.8.8 `switch` on `String` compiles to a two-stage `hashCode` switch plus `equals`. `[BYTECODE]`
      `[SOURCE]`
1.8.9 `switch` on an enum compiles to a switch over a synthetic `$SwitchMap` int array, not over
      `ordinal()` directly — and why. `[SOURCE]` `[PROVE]`
1.8.10 A `null` selector throws NPE in a classic `switch`; pattern switch can have a `case null`.
       `[TRAP]` `[X-REF 04]`
1.8.11 Arrow-form `switch` and `switch` expressions (Java 14), `yield`, exhaustiveness. `[X-REF 04]`
1.8.12 Pattern matching for `switch` and record patterns (Java 21), `MatchException`. `[X-REF 04]`
1.8.13 `assert` statements, `-ea`, and why assertions are off by default and must not carry side
       effects. `[TRAP]`
1.8.14 `synchronized` blocks and statements as control flow. `[X-REF 05]`
1.8.15 `try`/`catch`/`finally`/try-with-resources as control flow, forward-referenced to §1.20.
1.8.16 Unreachable-statement rules: `while (true)` with code after it is a compile error, but
       `if (true)` with code after it is not. `[TRAP]` `[PROVE]`

*(16 leaves)*

### §1.9 Wrappers, autoboxing, and the caches

1.9.1 The eight wrapper classes, their `Number`/`Comparable` supertypes, and `Character`/`Boolean`
      not being `Number`.
1.9.2 Autoboxing (Java 5) inserts `Integer.valueOf(int)`; unboxing inserts `intValue()`.
      `[BYTECODE]`
1.9.3 `Integer.valueOf` caches −128..127; the cache is built in the `IntegerCache` static nested
      class at class initialization. `[SOURCE]` `[NUM]`
1.9.4 The upper bound is tunable with `-XX:AutoBoxCacheMax=<n>` /
      `-Djava.lang.Integer.IntegerCache.high`; the lower bound is fixed at −128 by the JLS.
      `[NUM]` `[RESEARCH]`
1.9.5 In modern JDKs the `IntegerCache` array can be loaded from the CDS archive
      (`CDS.initializeFromArchive`, the `archivedCache` field) rather than built at startup.
      `[SOURCE]` `[RESEARCH]`
1.9.6 Which wrappers cache what: `Byte` all 256, `Short` and `Long` −128..127, `Character` 0..127,
      `Boolean` both values (`Boolean.TRUE`/`FALSE`), `Float` and `Double` nothing. `[NUM]`
1.9.7 `Integer a = 127, b = 127; a == b` is true; at 128 it is false. `[TRAP]` `[PROVE]`
1.9.8 `==` on wrappers is reference comparison — the bug that passes tests and fails in production.
      `[TRAP]`
1.9.9 Unboxing `null` throws NPE at a line with no visible method call
      (`int n = map.get("missing")`). `[TRAP]`
1.9.10 Mixed `==` between a primitive and a wrapper unboxes the wrapper, so it becomes a value
       comparison — the asymmetry that makes the rule hard to remember. `[TRAP]` `[PROVE]`
1.9.11 `equals` across wrapper types is always false: `Integer.valueOf(1).equals(Long.valueOf(1))`
       is false. `[TRAP]`
1.9.12 Boxing in a loop: `Long sum = 0L; sum += i;` allocates one `Long` per iteration. `[NUM]`
       `[PROVE]`
1.9.13 The deprecated-for-removal wrapper constructors (`new Integer(1)`, Java 9 deprecated,
       Java 16 terminally) and why `valueOf` is the only correct form. `[RESEARCH]`
1.9.14 Wrapper statics worth knowing: `MIN_VALUE`/`MAX_VALUE`/`SIZE`/`BYTES`/`TYPE`, `parseInt`,
       `valueOf(String)`, `decode`, `toBinaryString`/`toHexString`/`toOctalString`,
       `toString(int, radix)`, `compare`, `sum`/`min`/`max`, `signum`, `bitCount`, `reverse`,
       `highestOneBit`, `numberOfLeadingZeros`, `numberOfTrailingZeros`, `rotateLeft`.
       `[RESEARCH]`
1.9.15 `Integer.parseInt` vs `Integer.valueOf(String)` — primitive vs boxed, and both throwing
       `NumberFormatException`.
1.9.16 `Double.parseDouble("")` throws; `Double.parseDouble("NaN")` and `"Infinity"` succeed.
       `[TRAP]`
1.9.17 `Boolean.parseBoolean` is case-insensitive and never throws — anything not "true" is false.
       `[TRAP]`
1.9.18 `Integer.hashCode()` is the value itself; `Long.hashCode()` is an xor fold;
       `Double.hashCode` goes through `doubleToLongBits`; `Boolean.hashCode()` is 1231/1237.
       `[NUM]` `[X-REF 02]`
1.9.19 Wrapper memory cost: `Integer` = 16 bytes, `Long` = 24 bytes, versus 4 and 8 for the
       primitive. `[NUM]` `[PROVE]` `[X-REF 06]`
1.9.20 When boxing is unavoidable (collections, generics, `Optional`, nullable columns) and the
       primitive-specialised escape hatches (`IntStream`, `OptionalInt`, `int[]`, `fastutil`).
       `[X-REF 02]`

*(20 leaves)*

### §1.10 `String`: the API surface

1.10.1 `String` is `final`, `Serializable`, `Comparable<String>`, `CharSequence`, and (Java 12+)
       `Constable`/`ConstantDesc`. `[RESEARCH]`
1.10.2 Immutability: `private final byte[] value`, never mutated after construction. `[SOURCE]`
1.10.3 What immutability buys: thread safety without synchronisation, safe map key, cached hash,
       safe sharing, interning, security of class names and file paths. `[PROVE]`
1.10.4 Construction forms: literal, `new String(...)`, `String.valueOf`, `copyValueOf`,
       `char[]`/`byte[]`+`Charset` constructors, `String.valueOf(char[])` vs
       `String.valueOf(Object)`.
1.10.5 `new String("x")` always allocates, and is almost always wrong. `[TRAP]`
1.10.6 Reading methods: `length`, `charAt`, `codePointAt`, `isEmpty`, `isBlank` (11), `chars`,
       `codePoints`, `toCharArray`, `getBytes(Charset)`.
1.10.7 Searching: `indexOf` ×4, `lastIndexOf` ×4, `contains`, `startsWith`, `endsWith`, `matches`.
1.10.8 Comparing: `equals`, `equalsIgnoreCase`, `compareTo`, `compareToIgnoreCase`,
       `contentEquals`, `regionMatches` ×2.
1.10.9 Producing: `substring`, `concat`, `replace(char,char)`, `replace(CharSequence,...)`,
       `replaceAll`, `replaceFirst`, `toUpperCase`/`toLowerCase` (with and without `Locale`),
       `trim`, `strip`/`stripLeading`/`stripTrailing` (11), `repeat` (11), `indent` (12),
       `stripIndent` (15), `translateEscapes` (15), `formatted` (15), `transform` (12).
1.10.10 `trim()` strips only code points ≤ U+0020; `strip()` uses `Character.isWhitespace` and is
        Unicode-aware. `[TRAP]` `[RESEARCH]`
1.10.11 `toUpperCase()` without a `Locale` uses the default locale — the Turkish dotless-i bug.
        `[TRAP]` `[PROVE]`
1.10.12 Splitting and joining: `split(String)`, `split(String,int)`, `String.join` ×2, `lines()`
        (11).
1.10.13 `split` takes a **regex**, not a literal: `"a.b".split(".")` returns an empty array.
        `[TRAP]`
1.10.14 `split` drops trailing empty strings unless the limit is negative. `[TRAP]` `[NUM]`
1.10.15 Formatting: `String.format`, `formatted`, the format-specifier grammar, and
        `Locale`-sensitivity of `%f`/`%,d`.
1.10.16 `String.format` is slow relative to concatenation and to `StringBuilder`; where that matters.
        `[NUM]`
1.10.17 `String.valueOf(null)` is ambiguous and resolves to the `char[]` overload → NPE, while
        `String.valueOf((Object) null)` returns `"null"`. `[TRAP]` `[PROVE]`
1.10.18 `substring` since Java 7 **copies**; before 7 it shared the backing array and leaked.
        `[VERSION-TRAP]` `[NUM]`
1.10.19 `String.hashCode` = `s[0]*31^(n-1) + ... + s[n-1]`, cached in `hash` with a `hashIsZero`
        flag (Java 13+). `[SOURCE]` `[NUM]` `[X-REF 02]`
1.10.20 `String.equals` short-circuits on identity, then compares `coder`, then compares the byte
        arrays. `[SOURCE]`
1.10.21 `compareTo` is UTF-16 code-unit order, not locale collation; use `Collator` for
        human-visible sorting. `[TRAP]` `[X-REF 02]`
1.10.22 `CharSequence` as the abstraction over `String`/`StringBuilder`/`CharBuffer`, and why
        `CharSequence.equals` is not defined. `[TRAP]`
1.10.23 `String` in `switch`, and the null-selector NPE.
1.10.24 `String.intern()` — what it returns and what it costs. Forward reference to §3.2.

*(24 leaves)*

### §1.11 The string pool

1.11.1 Literals are interned at class-load time into a JVM-managed pool.
1.11.2 The pool moved from PermGen to the heap in Java 7 — so old "PermGen OOM from intern" advice
       is stale. `[VERSION-TRAP]` `[RESEARCH]`
1.11.3 `"hello" == "hello"` is true across classes and even across class loaders in the same JVM.
1.11.4 `new String("hello") != "hello"`; `.intern()` recovers the pooled instance.
1.11.5 Compile-time constant folding: `"hel" + "lo" == "hello"` is true;
       `"hel" + variable == "hello"` is false. `[PROVE]` `[BYTECODE]`
1.11.6 `final String s = "hel";` makes `s + "lo"` a constant expression; dropping `final` breaks it.
       `[TRAP]` `[PROVE]`
1.11.7 When to intern deliberately (huge numbers of repeated parsed strings) and when not to
       (unbounded user input — it is effectively a leak until GC of the pool). `[TRAP]`
1.11.8 Alternatives to interning: a `HashMap<String,String>` canonicaliser you control, or G1 string
       deduplication.
1.11.9 `==` on strings works often enough (literals) to hide the bug and fails on strings from I/O,
       parsing, or a database row. Never compare strings with `==`. `[TRAP]`

*(9 leaves)*

### §1.12 `==` versus `equals`, and the `Object` methods

1.12.1 `==` compares the two slots: value for primitives, identity for references.
1.12.2 `Object.equals` defaults to identity — a class with no override gains nothing from `equals`.
1.12.3 The `equals` contract: reflexive, symmetric, transitive, consistent, `x.equals(null)` false.
       `[X-REF 02]`
1.12.4 The `hashCode` contract and the equal⇒equal-hash requirement. `[PROVE]` `[X-REF 02]`
1.12.5 `Objects.equals`, `Objects.hash`, `Objects.hashCode`, `Objects.toString`,
       `Objects.requireNonNull` ×3, `Objects.requireNonNullElse`, `Objects.isNull`/`nonNull`,
       `Objects.checkIndex`, `Objects.compare`, `Objects.equals` vs `Objects.deepEquals`.
1.12.6 Arrays use identity `equals`; use `Arrays.equals` / `Arrays.deepEquals` and
       `Arrays.hashCode` / `Arrays.deepHashCode`. `[TRAP]`
1.12.7 `getClass()` vs `instanceof` in `equals`: symmetry versus Liskov. `[TRAP]` `[X-REF 02]`
1.12.8 Overloading `equals(MyType)` instead of overriding `equals(Object)`; `@Override` as the
       cheap defence. `[TRAP]`
1.12.9 `toString`: override it on anything that appears in a log; the default
       `ClassName@1b6d3586` is `getClass().getName() + "@" + Integer.toHexString(hashCode())`.
       `[SOURCE]`
1.12.10 `getClass()` is `final`; `getClass()` on a proxy or a lambda does not return what you
        expect. `[TRAP]` `[X-REF 07]`
1.12.11 `hashCode()` default is an identity hash from the JVM, stored in the mark word, and it is
        **not** the memory address. `[TRAP]` `[X-REF 06]`
1.12.12 `clone` and `Cloneable`: a marker interface, a `protected` method, shallow by default,
        bypasses constructors, awkward with `final` fields. `[TRAP]`
1.12.13 `CloneNotSupportedException` as a checked exception on a method nobody wants to call.
1.12.14 Copy constructors and static copy factories as the replacement for `clone`.
1.12.15 `finalize()` — deprecated for removal (JEP 421, Java 18), never guaranteed to run, can
        resurrect objects, delays reclamation by at least one GC cycle. `[TRAP]` `[RESEARCH]`
1.12.16 `--finalization=disabled` as the pre-removal test switch. `[RESEARCH]`
1.12.17 `Cleaner` (Java 9) and `PhantomReference` as the correct replacements, plus `AutoCloseable`
        as the better answer than either. `[RESEARCH]`
1.12.18 `wait`, `notify`, `notifyAll` on `Object`, and why they are here at all. `[X-REF 05]`
1.12.19 The complete list of `Object`'s eleven members and which are `final`.

*(19 leaves)*

### §1.13 Classes, constructors, and initialization order

1.13.1 Class declaration anatomy: modifiers, name, type parameters, `extends`, `implements`,
       `permits`.
1.13.2 Field declarations, instance vs static, initialisers.
1.13.3 Method declarations: modifiers, return type, throws clause, varargs, generic methods.
1.13.4 Constructors: no return type, the implicit no-arg constructor, and its disappearance the
       moment you declare any constructor. `[TRAP]`
1.13.5 `this(...)` and `super(...)` must be the first statement — relaxed in Java 22+ by
       JEP 447/482 (flexible constructor bodies), final in 25. `[RESEARCH]` `[VERSION-TRAP]`
1.13.6 The exact initialization order for a `new`: superclass constructor chain → instance field
       initialisers and instance initialiser blocks in textual order → constructor body.
       `[PROVE]` `[SOURCE]`
1.13.7 Calling an overridable method from a constructor: the subclass override runs before the
       subclass fields are initialised and sees `null`/0. `[TRAP]` `[PROVE]`
1.13.8 Static initialization order: static fields and static blocks in textual order, once, at
       class initialization.
1.13.9 The class initialization triggers (JVMS 5.5): `new`, `getstatic`/`putstatic` on a non-constant
       field, `invokestatic`, reflection, subclass initialization, main class. `[SOURCE]`
       `[RESEARCH]`
1.13.10 Reading a `static final` compile-time constant does **not** trigger initialization, because
        it was inlined. `[TRAP]` `[PROVE]`
1.13.11 `Class.forName(name)` initialises; `Class.forName(name, false, loader)` and
        `loader.loadClass(name)` do not. `[TRAP]`
1.13.12 Class initialization is thread-safe and happens exactly once — the basis of the holder-class
        singleton idiom. `[PROVE]` `[X-REF 05]`
1.13.13 An exception in a static initialiser becomes `ExceptionInInitializerError`, and every
        subsequent use of the class throws `NoClassDefFoundError` with no root cause in sight.
        `[TRAP]` `[PROVE]` `[X-REF 06]`
1.13.14 Initialization cycles between two classes leave one of them observing default values.
        `[TRAP]` `[RESEARCH]`
1.13.15 Long-running work in a static initialiser: startup latency, deadlock risk, and why the
        holder idiom is preferable. `[RESEARCH]`
1.13.16 Object construction cost, escape analysis and scalar replacement as the reason "allocation
        is cheap" is sometimes literally true. `[X-REF 06]`
1.13.17 The `record` compact constructor and canonical constructor as a contrast. `[X-REF 04]`

*(17 leaves)*

### §1.14 Modifiers: `static`, `final`, and the rest

1.14.1 `static` binds a member to the class: one copy, shared, no `this`.
1.14.2 Static methods are dispatched on the **compile-time** type — "overriding" a static method
       hides it. `[TRAP]` `[PROVE]`
1.14.3 Calling a static method through an instance reference (`obj.staticMethod()`) compiles and is
       resolved statically, including when `obj` is null. `[TRAP]`
1.14.4 Static nested classes, static imports, static factories, static utility classes with a
       private constructor.
1.14.5 `final` in three positions: variable (no reassignment), method (no override), class (no
       subclass).
1.14.6 `final` is not immutability — a `final` reference to a mutable object gives you nothing but
       a fixed pointer. `[TRAP]`
1.14.7 `static final` primitives and `String` constants are compile-time constants and get **inlined
       into every calling class**; changing the constant without recompiling callers leaves stale
       values. `[TRAP]` `[PROVE]` `[BYTECODE]`
1.14.8 The fix: make the constant a method call or a non-constant initialiser
       (`static final int X = Integer.valueOf(5);`) when it must stay dynamic. `[RESEARCH]`
1.14.9 `final` fields carry a JMM freeze guarantee: safe publication without synchronisation.
       `[X-REF 05]`
1.14.10 Effectively final, and why lambda capture requires it.
1.14.11 `final` on parameters and locals: no runtime effect, only a readability and
        capture-eligibility effect.
1.14.12 The access modifiers: `public`, `protected`, package-private (default), `private` — the full
        4×4 visibility table including "same package, different module".
1.14.13 `protected` means "subclass **or** same package", and a subclass may only access the
        protected member through a reference of its own type. `[TRAP]` `[PROVE]`
1.14.14 `abstract`: on classes and methods; illegal combinations (`abstract final`,
        `abstract private`, `abstract static`).
1.14.15 `synchronized` on a method vs a block, and what object it locks in each case. `[X-REF 05]`
1.14.16 `volatile` and `transient` as field modifiers. `[X-REF 05]`
1.14.17 `native` and `strictfp`.
1.14.18 `strictfp` has been a no-op since Java 17 (JEP 306 restored always-strict semantics).
        `[VERSION-TRAP]` `[RESEARCH]`
1.14.19 `sealed`/`non-sealed`/`permits` (Java 17). `[X-REF 04]`
1.14.20 The legal modifier combinations for each declaration kind, in one table.

*(20 leaves)*

### §1.15 Inheritance, overriding, and dispatch

1.15.1 Single inheritance of implementation, multiple inheritance of type.
1.15.2 `extends` semantics, implicit `extends Object`, the constructor chain.
1.15.3 Overriding rules: same name and parameter types after erasure, covariant return type,
       no broader checked exceptions, no weaker access, cannot override `final`/`static`/`private`.
1.15.4 Covariant return types (Java 5) and the bridge method the compiler emits for them.
       `[SOURCE]`
1.15.5 Overloading is compile-time; overriding is runtime. The single most consequential distinction
       in the section. `[PROVE]`
1.15.6 Overload resolution in three phases (JLS 15.12.2): phase 1 no boxing/no varargs, phase 2
       boxing allowed, phase 3 varargs allowed; then "most specific" selection. `[SOURCE]`
       `[RESEARCH]`
1.15.7 A widening overload beats a boxing overload beats a varargs overload — the classic
       `f(int)`/`f(long)`/`f(Integer)`/`f(int...)` question. `[TRAP]` `[PROVE]`
1.15.8 `null` argument selects the most specific reference overload, and is ambiguous when two are
       unrelated. `[TRAP]`
1.15.9 Dynamic dispatch: `invokevirtual` resolves against the receiver's runtime class through the
       vtable; `invokeinterface` uses the itable. `[SOURCE]` `[RESEARCH]` `[X-REF 06]`
1.15.10 `invokestatic`, `invokespecial` (constructors, `private`, `super.`), `invokedynamic`
        (lambdas, string concat, records' `Object` methods). `[BYTECODE]` `[RESEARCH]`
1.15.11 Monomorphic / bimorphic / megamorphic call sites and inline caches — why an interface with
        one implementation is free and one with twenty is not. `[RESEARCH]` `[X-REF 06]`
1.15.12 Fields are **not** polymorphic: field access is resolved by the static type. `[TRAP]`
        `[PROVE]`
1.15.13 `super.method()` and why it compiles to `invokespecial`.
1.15.14 `this` escaping during construction. `[TRAP]` `[X-REF 05]`
1.15.15 Composition over inheritance: the fragile base class problem, and the concrete
        `HashSet` + counting-subclass example where `addAll` calls `add`. `[PROVE]` `[X-REF 02]`
1.15.16 Design for inheritance or prohibit it: document self-use, or make the class `final`.
1.15.17 `@Override` as the only defence against a silent overload. `[TRAP]`
1.15.18 Liskov substitution as the informal rule behind the overriding constraints.

*(18 leaves)*

### §1.16 Interfaces versus abstract classes

1.16.1 The comparison table: multiple inheritance, state, constructors, method bodies, access
       modifiers, fields, instantiation.
1.16.2 Interface fields are implicitly `public static final`; interface methods implicitly `public
       abstract` unless `default`/`static`/`private`.
1.16.3 `default` methods (Java 8): why they exist — interface evolution without breaking
       implementors, e.g. `Collection.stream`, `Iterable.forEach`, `Comparator.reversed`.
1.16.4 `static` interface methods (Java 8) and `private`/`private static` interface methods
       (Java 9).
1.16.5 Diamond resolution: class beats interface; most specific sub-interface beats super-interface;
       otherwise compile error, disambiguated by `Interface.super.method()`. `[PROVE]`
1.16.6 Default methods cannot override `Object` methods — the compiler rejects a default
       `equals`/`hashCode`/`toString`. `[TRAP]` `[PROVE]`
1.16.7 `default` methods are not "multiple inheritance of state" — no fields, so no diamond of
       state. `[TRAP]`
1.16.8 Marker interfaces (`Serializable`, `Cloneable`, `RandomAccess`) versus marker annotations,
       and why the interface form can be used in a type check.
1.16.9 Functional interfaces, `@FunctionalInterface`, and the single-abstract-method rule (methods
       matching `Object`'s public methods do not count). `[X-REF 04]`
1.16.10 Constant interface anti-pattern; use a utility class or an enum. `[TRAP]`
1.16.11 Choosing: interface for a capability contract, abstract class for shared state or a
        template lifecycle; skeletal implementation (`AbstractX`) as the combination. `[X-REF 02]`
1.16.12 Adding an abstract method to an interface is a binary-incompatible change; adding a default
        method is not. `[PROVE]`

*(12 leaves)*

### §1.17 Nested, inner, local and anonymous classes

1.17.1 The four kinds and their exact definitions: static nested, inner (non-static member), local,
       anonymous.
1.17.2 Static nested class: no enclosing instance; the default choice.
1.17.3 Inner class: holds a synthetic `this$0` reference to the enclosing instance;
       `Outer.this` syntax; `outer.new Inner()`.
1.17.4 An inner class cannot declare static members other than constants — relaxed in Java 16.
       `[VERSION-TRAP]` `[RESEARCH]`
1.17.5 Local classes: scope, capture rules, and why they are rare.
1.17.6 Anonymous classes: declared and instantiated in one expression; can extend a class or
       implement one interface; no constructor, so instance initialiser blocks are the workaround.
1.17.7 The double-brace initialisation idiom and why it is a leak and a serialization hazard.
       `[TRAP]`
1.17.8 A non-static inner or anonymous class stored somewhere long-lived keeps the entire enclosing
       object alive — listener registries, static caches, executor tasks. `[TRAP]` `[PROVE]`
1.17.9 Lambdas differ: no class file per instance, no implicit enclosing reference unless `this` or
       an instance member is used; `this` inside a lambda is the enclosing instance, inside an
       anonymous class it is the anonymous instance. `[TRAP]` `[X-REF 04]`
1.17.10 Captured locals must be effectively final because the value is copied. `[PROVE]`
1.17.11 The workaround people reach for (a one-element array, an `AtomicInteger`) and when it is
        legitimate. `[TRAP]`
1.17.12 Generated class file names: `Outer$Inner`, `Outer$1`, `Outer$1Local`, and reading them in a
        stack trace. `[RESEARCH]`
1.17.13 When each kind is the right answer, in one table.

*(13 leaves)*

### §1.18 Enums

1.18.1 An enum is a class with a fixed set of instances created at class initialization;
       `java.lang.Enum` is the implicit superclass, so an enum cannot extend anything else.
1.18.2 The JVM-uniqueness guarantee: serialization, reflection and multiple class loaders cannot
       produce a second instance of a constant. `[PROVE]`
1.18.3 Enums as the correct singleton (Effective Java item 3). `[PROVE]`
1.18.4 Fields, constructors (implicitly private), and methods on an enum.
1.18.5 Constant-specific class bodies, and the abstract-method-per-constant pattern.
1.18.6 The implicit members: `values()`, `valueOf(String)`, `name()`, `ordinal()`, `compareTo`,
       `getDeclaringClass`, `describeConstable` (12+). `[RESEARCH]`
1.18.7 `values()` returns a **defensive clone of the `$VALUES` array on every call** — cache it, or
       use `EnumSet.allOf`. `[SOURCE]` `[NUM]` `[TRAP]`
1.18.8 `ordinal()` is the declaration index; never persist it, never use it as a database value,
       never do arithmetic on it. `[TRAP]`
1.18.9 `valueOf` throws `IllegalArgumentException`, not returning null — wrap it in a lookup map for
       tolerant parsing. `[TRAP]`
1.18.10 Enum `hashCode` is identity-based and varies per JVM run, so `HashMap` iteration order over
        enum keys is not reproducible. `[TRAP]` `[X-REF 02]`
1.18.11 `EnumMap` and `EnumSet` — array- and bit-vector-backed, dramatically faster than the hash
        equivalents. `[X-REF 02]`
1.18.12 Enums in `switch`: unqualified constant labels, exhaustiveness in switch **expressions**,
        and the `default` versus exhaustive-without-default trade-off for future constants. `[TRAP]`
1.18.13 Enums implementing an interface, and the strategy-enum pattern.
1.18.14 Enum with a stable persisted code field plus a static `Map<code, constant>` lookup — the
        production pattern. `[BUILD]`
1.18.15 Enum singletons and `readResolve`: enum serialization ignores `writeReplace`/`readResolve`
        by specification. `[RESEARCH]` `[SOURCE]`
1.18.16 Enum constants cannot be created reflectively — `Constructor.newInstance` throws
        `IllegalArgumentException`. `[PROVE]`
1.18.17 The typesafe-enum pattern that predates Java 5, and what the language feature actually
        automates. `[BUILD]`

*(17 leaves)*

### §1.19 Records and sealed types (bridged here, owned by 04)

1.19.1 A record is a final class with final components, a canonical constructor, accessors, and
       generated `equals`/`hashCode`/`toString`. `[X-REF 04]`
1.19.2 Records give you immutability rules 1–3 but **not** defensive copying — a record with a
       `List` or array component still needs a compact constructor. `[TRAP]` `[X-REF 04]`
1.19.3 Record `equals` is component-wise, so an array component compares by identity. `[TRAP]`
1.19.4 Records generate `equals`/`hashCode`/`toString` through `invokedynamic` to
       `ObjectMethods.bootstrap`, not as inline bytecode. `[SOURCE]` `[RESEARCH]` `[X-REF 04]`
1.19.5 Sealed interfaces and classes, `permits`, and exhaustive pattern switches. `[X-REF 04]`
1.19.6 Where a record is the right replacement for a hand-written value class, and where it is not
       (JPA entities, mutable DTOs, classes needing inheritance). `[X-REF 08]`

*(6 leaves)*

### §1.20 Exceptions: the model

1.20.1 The hierarchy: `Throwable` → `Error` / `Exception` → `RuntimeException`.
1.20.2 Checked vs unchecked: the compile-time rule (JLS 11.2), not a runtime distinction.
1.20.3 The catch-or-declare requirement and how it propagates through every intermediate signature.
1.20.4 `Error` is JVM-level and should not be caught: `OutOfMemoryError`, `StackOverflowError`,
       `NoClassDefFoundError`, `LinkageError`, `AssertionError`. `[X-REF 06]`
1.20.5 The common unchecked exceptions and what each actually means: `NullPointerException`,
       `IllegalArgumentException`, `IllegalStateException`, `ClassCastException`,
       `IndexOutOfBoundsException`, `ArithmeticException`, `UnsupportedOperationException`,
       `ConcurrentModificationException`, `NumberFormatException`, `ArrayStoreException`.
1.20.6 The common checked exceptions: `IOException`, `SQLException`, `InterruptedException`,
       `ClassNotFoundException`, `CloneNotSupportedException`, `TimeoutException`.
1.20.7 `Throwable` API: `getMessage`, `getLocalizedMessage`, `getCause`, `initCause`,
       `getStackTrace`, `setStackTrace`, `fillInStackTrace`, `printStackTrace`, `addSuppressed`,
       `getSuppressed`, and the four-argument protected constructor.
1.20.8 Exception chaining: always pass the cause, or the root cause disappears from the log.
       `[TRAP]`
1.20.9 `try`/`catch`/`finally` semantics, catch-clause ordering (most specific first), and the
       compile error for an unreachable catch.
1.20.10 Multi-catch (Java 7): `catch (IOException | SQLException e)`, `e` is implicitly final and
        typed as the least upper bound.
1.20.11 Precise rethrow (Java 7): `catch (Exception e) { throw e; }` can be declared as the narrower
        set the body actually throws. `[RESEARCH]`
1.20.12 try-with-resources (Java 7): `AutoCloseable`, closed in reverse declaration order, before
        `catch` and `finally`.
1.20.13 Effectively-final resource expressions in try-with-resources (Java 9).
1.20.14 Suppressed exceptions: the body's exception wins, the `close()` exception is attached via
        `addSuppressed`. `[PROVE]`
1.20.15 The old `finally { conn.close(); }` form loses the original exception when close throws —
        the reason try-with-resources exists. `[TRAP]` `[PROVE]`
1.20.16 `return` inside `finally` discards both the in-flight exception and the `try` block's
        return value. `[TRAP]` `[PROVE]` `[BYTECODE]`
1.20.17 A `finally` block that throws replaces the original exception the same way.
1.20.18 `catch (Exception e) {}` swallows bugs; log with the throwable as an argument
        (`log.error("msg", e)`), never `e.getMessage()`. `[TRAP]`
1.20.19 Catching `InterruptedException` and doing nothing clears the interrupt flag and breaks
        cancellation — rethrow or `Thread.currentThread().interrupt()`. `[TRAP]` `[X-REF 05]`
1.20.20 Never catch `Throwable` or `Error`; the one exception is a top-level thread/executor
        handler that logs and re-raises. `[TRAP]`
1.20.21 `System.exit` in a `try` block skips `finally` entirely. `[TRAP]` `[PROVE]`
1.20.22 Shutdown hooks (`Runtime.addShutdownHook`) as the only "finally" for the process.
1.20.23 `Thread.UncaughtExceptionHandler` and the default behaviour of an exception escaping `run()`.
        `[X-REF 05]`
1.20.24 Helpful NullPointerException messages (JEP 358, Java 14; on by default since Java 15) —
        "Cannot invoke \"X.y()\" because \"a.b\" is null". `[RESEARCH]` `[VERSION-TRAP]`

*(24 leaves)*

### §1.21 Generics: the basics

1.21.1 Why generics exist: the pre-5 `List` of `Object` plus casts, and the `ClassCastException`
       that arrived far from the bug.
1.21.2 Generic classes, generic interfaces, generic methods, and the syntax of each.
1.21.3 Type parameter naming conventions: `E`, `K`, `V`, `T`, `R`, `U`, `S`, `N`.
1.21.4 Bounded type parameters: `<T extends Number>`; multiple bounds `<T extends Number &
       Comparable<T>>`, class bound first.
1.21.5 Generic method declaration and explicit type witness `Collections.<String>emptyList()`.
1.21.6 The diamond `<>` (Java 7) and its extension to anonymous classes (Java 9). `[RESEARCH]`
1.21.7 Erasure, stated once: type arguments are checked then discarded; casts are inserted at use
       sites; the `Signature` attribute keeps them for reflection only. `[SOURCE]`
1.21.8 Consequences: `List<String>` and `List<Integer>` are one class at runtime; no `new T[]`;
       no `new T()`; no `instanceof List<String>`; no overload on erased signatures; static fields
       are shared across parameterisations.
1.21.9 Generics are **invariant**: `List<String>` is not a `List<Object>`. `[PROVE]` `[TRAP]`
1.21.10 Arrays are **covariant**, which is why `ArrayStoreException` exists — and why generic arrays
        are illegal. `[PROVE]` `[TRAP]`
1.21.11 Wildcards: `? extends T` (producer), `? super T` (consumer), unbounded `?`.
1.21.12 PECS: Producer Extends, Consumer Super, with `Collections.copy` as the canonical signature.
        `[X-REF 02]`
1.21.13 You cannot `add` to a `List<? extends Number>` except `null`. `[PROVE]`
1.21.14 Reading from a `List<? super T>` gives `Object`. `[PROVE]`
1.21.15 Raw types: allowed for compatibility, disable all generic checking including on unrelated
        methods, and let an `Integer` into a `List<String>`. `[TRAP]` `[PROVE]`
1.21.16 `List<Object>` vs `List<?>` vs raw `List` — the three-way distinction. `[TRAP]`
1.21.17 Reifiable vs non-reifiable types, and the exact list of what is reifiable. `[RESEARCH]`
1.21.18 Heap pollution, generic varargs, and `@SafeVarargs` — only annotate methods that never write
        to the varargs array. `[TRAP]` `[PROVE]`
1.21.19 `@SuppressWarnings("unchecked")` discipline: narrowest possible scope, with a comment
        explaining why it is safe.
1.21.20 Recursive type bounds: `<T extends Comparable<? super T>>` and how to read it. `[PROVE]`
1.21.21 The typesafe heterogeneous container pattern (`Map<Class<?>, Object>` +
        `Class.cast`). `[BUILD]`

*(21 leaves)*

### §1.22 Arrays

1.22.1 Arrays are objects: they have a `length` field, inherit `Object`, implement `Cloneable` and
       `Serializable`, and have a synthesized class.
1.22.2 Declaration forms `int[] a` vs `int a[]`, and the multi-dimensional forms.
1.22.3 Creation: `new int[n]`, initialiser syntax, and the fact that `new int[n]` zero-fills.
1.22.4 Multi-dimensional arrays are arrays of arrays and may be jagged; `new int[3][]` is legal.
1.22.5 Array covariance and `ArrayStoreException` at runtime. `[TRAP]` `[PROVE]`
1.22.6 Arrays are always mutable; a `final` array is not a constant. `[TRAP]`
1.22.7 `array.clone()` is a shallow copy; nested arrays are shared. `[TRAP]`
1.22.8 `Arrays.copyOf`, `copyOfRange`, `fill`, `setAll`, `sort`, `parallelSort`, `binarySearch`,
       `equals`, `deepEquals`, `hashCode`, `deepHashCode`, `toString`, `deepToString`, `mismatch`,
       `compare`, `asList`, `stream`. `[X-REF 02]`
1.22.9 `Arrays.asList(intArray)` gives a `List<int[]>` of size 1. `[TRAP]` `[X-REF 02]`
1.22.10 `System.arraycopy` as the intrinsic behind everything, and its parameter order.
1.22.11 Array memory layout: 16-byte header (12 header + 4 length), contiguous elements, alignment.
        `[NUM]` `[X-REF 06]`
1.22.12 Maximum array length: `Integer.MAX_VALUE` in theory, `Integer.MAX_VALUE - 8` in practice
        (`SOFT_MAX_ARRAY_LENGTH`). `[NUM]` `[RESEARCH]` `[X-REF 02]`
1.22.13 Bounds checking on every access, and bounds-check elimination by the JIT. `[X-REF 06]`
1.22.14 Varargs are arrays: `f(T... args)` allocates an array per call; passing an array directly
       avoids it; `f()` gets a zero-length array, not null. `[TRAP]`
1.22.15 Ambiguity between `f(Object)` and `f(Object...)`, and `f(null)` selecting the array form.
        `[TRAP]`
1.22.16 When to use an array instead of a `List`: primitives, fixed size, hot loops, interop.

*(16 leaves)*

### §1.23 Packages, access control, and modules

1.23.1 Package declaration, the directory mapping, and the unnamed package.
1.23.2 Import forms: single-type, on-demand, static single, static on-demand; imports have no
       runtime cost and no ordering significance.
1.23.3 An on-demand import that collides with another on-demand import is an error only at the use
       site. `[TRAP]`
1.23.4 Fully qualified names vs canonical names.
1.23.5 The classpath, the class file layout, and how a class is located. `[X-REF 06]`
1.23.6 JPMS (Java 9): `module-info.java`, `requires`, `exports`, `opens`, `requires transitive`,
       `uses`/`provides`. `[RESEARCH]`
1.23.7 Strong encapsulation: `InaccessibleObjectException` from reflective access to a
       non-`opens` package, and `--add-opens` as the escape hatch. `[TRAP]` `[RESEARCH]`
1.23.8 Illegal-access has been denied by default since Java 16/17 — "it worked on Java 8" is the
       most common migration failure. `[VERSION-TRAP]` `[RESEARCH]`
1.23.9 The classpath vs module path, the unnamed module, and automatic modules.
1.23.10 `sun.misc.Unsafe` memory-access methods deprecated for removal (JEP 471, Java 23) and the
        integrity-by-default direction; `MemorySegment`/`VarHandle` as the replacement.
        `[RESEARCH]`
1.23.11 Split packages and why they break the module path.

*(11 leaves)*

### §1.24 Annotations

1.24.1 What an annotation is: an interface, compiled to a class file attribute, with element
       methods and defaults.
1.24.2 Declaring one: `@interface`, element types allowed (primitives, `String`, `Class`, enums,
       annotations, arrays of those).
1.24.3 Meta-annotations: `@Retention` (SOURCE/CLASS/RUNTIME), `@Target`, `@Documented`,
       `@Inherited`, `@Repeatable` (Java 8).
1.24.4 `RetentionPolicy.CLASS` is the default and is **not** visible to reflection. `[TRAP]`
1.24.5 The built-in annotations: `@Override`, `@Deprecated` (with `since`/`forRemoval`),
       `@SuppressWarnings`, `@SafeVarargs`, `@FunctionalInterface`.
1.24.6 `@Inherited` only applies to class-level annotations and only to class inheritance — not
       interfaces, not methods. `[TRAP]`
1.24.7 Type annotations (`ElementType.TYPE_USE`, Java 8) and how nullability checkers use them.
1.24.8 Reading annotations reflectively: `isAnnotationPresent`, `getAnnotation`,
       `getAnnotationsByType`, `getDeclaredAnnotations`.
1.24.9 Annotation processing at compile time (`javax.annotation.processing`, Lombok, MapStruct)
       versus at runtime (Spring, JPA). `[X-REF 07]`
1.24.10 Annotations have no behaviour: something must read them. The single most common
        misunderstanding. `[TRAP]`

*(10 leaves)*

### §1.25 The `java.lang` inventory you should be able to name

1.25.1 The core interfaces: `Comparable`, `Iterable`, `Runnable`, `CharSequence`, `AutoCloseable`,
       `Cloneable`, `Appendable`, `Readable`.
1.25.2 The core classes: `Object`, `String`, `StringBuilder`, `StringBuffer`, `Math`, `StrictMath`,
       `System`, `Runtime`, `Thread`, `ThreadLocal`, `Class`, `ClassLoader`, `Enum`, `Record`,
       `Number`, `Void`, `Package`, `Module`, `StackWalker`, `StackTraceElement`, `ProcessBuilder`.
       `[RESEARCH]`
1.25.3 The full `Throwable` inventory in `java.lang`: 30 exceptions and 23 errors, and which you
       will actually see. `[RESEARCH]`
1.25.4 `System`: `out`/`err`/`in`, `currentTimeMillis` vs `nanoTime`, `arraycopy`,
       `identityHashCode`, `getProperty`/`getenv`, `lineSeparator`, `exit`, `gc` (a hint, not a
       command). `[TRAP]`
1.25.5 `System.nanoTime()` is monotonic and has no epoch meaning; `currentTimeMillis` can jump
       backwards. Never subtract wall-clock times to measure elapsed time. `[TRAP]` `[PROVE]`
1.25.6 `Math` essentials: `abs`, `max`/`min`, `round` (and its half-up-toward-positive-infinity
       rule), `floor`, `ceil`, `rint`, `pow`, `sqrt`, `random`, `floorDiv`/`floorMod`, the `*Exact`
       family, `Math.fma` (Java 9), `Math.toIntExact`. `[RESEARCH]`
1.25.7 `Math.round(-2.5)` is −2, not −3. `[TRAP]` `[NUM]`
1.25.8 `Math` vs `StrictMath`: reproducibility vs speed. `[RESEARCH]`
1.25.9 `Math.random()` vs `Random` vs `ThreadLocalRandom` vs `SecureRandom` vs the Java 17
       `RandomGenerator` interface family. `[RESEARCH]` `[X-REF 13]`
1.25.10 `Character`: `isDigit`, `isLetter`, `isWhitespace`, `isJavaIdentifierPart`, `toUpperCase`,
        `getNumericValue`, `codePointAt`, `isSurrogate`, `toChars`.
1.25.11 `Runtime`: `availableProcessors`, `totalMemory`/`freeMemory`/`maxMemory`, `addShutdownHook`,
        `Runtime.version()`. `[X-REF 06]`
1.25.12 `Runtime.freeMemory()` deltas are a bad way to measure object size. `[TRAP]` `[X-REF 06]`
1.25.13 `StackWalker` (Java 9) as the cheap, lazy replacement for `Thread.currentThread()
        .getStackTrace()`. `[RESEARCH]`

*(13 leaves)*

---

**PART 1 total: 291 leaves**

---

## PART 2 — INTERMEDIATE

### §2.1 The master semantics-and-cost table

2.1.1 One table over the core operations: `String` concat, `StringBuilder.append`, `substring`,
      `equals`, `hashCode`, `intern`, boxing, unboxing, `instanceof`, cast, virtual call,
      interface call, reflective call, exception creation, exception throw/catch, array access,
      field access, `BigDecimal.add`, `BigDecimal.divide`, `LocalDate.plusDays`,
      `Instant.now`, `System.currentTimeMillis`, `System.nanoTime`. Columns: complexity,
      allocation, and rough nanoseconds. `[NUM]`
2.1.2 Allocation cost model: TLAB bump-pointer allocation, escape analysis, scalar replacement —
      why "objects are expensive" is only sometimes true. `[X-REF 06]`
2.1.3 Which of the above the JIT can eliminate entirely and which it cannot. `[X-REF 06]`
2.1.4 Exception creation is proportional to stack depth; throw/catch itself is cheap. `[PROVE]`
      `[RESEARCH]`
2.1.5 Reflection is roughly an order of magnitude slower than a direct call before inlining, and
      close to free after warmup for a monomorphic `MethodHandle`. `[RESEARCH]`
2.1.6 Amortised versus average versus worst case, restated for `StringBuilder` growth. `[PROVE]`
2.1.7 What is JMH-measurable here and what is not; dead-code elimination and constant folding
      destroying naive microbenchmarks of `String` operations. `[X-REF 06]`

*(7 leaves)*

### §2.2 String performance and text processing

2.2.1 `+` in a loop is O(n²): a new builder, a new array and a full copy per iteration. `[PROVE]`
      `[BYTECODE]`
2.2.2 `+` in a single expression compiles to `invokedynamic`/`StringConcatFactory` since Java 9 and
      is usually **faster** than a hand-written `StringBuilder`. `[RESEARCH]` `[VERSION-TRAP]`
2.2.3 `StringBuilder`: default capacity 16, or 16 + the initial string's length; growth
      `2 * old + 2` via `ArraysSupport.newLength`. `[SOURCE]` `[NUM]`
2.2.4 Pre-sizing a `StringBuilder` when you know the output length, and what it saves. `[NUM]`
2.2.5 `StringBuffer` is the synchronized legacy version; the lock is never what you want. `[TRAP]`
2.2.6 `StringBuilder` API: `append` overloads, `insert`, `delete`, `deleteCharAt`, `replace`,
      `reverse`, `setLength`, `setCharAt`, `ensureCapacity`, `trimToSize`, `capacity`, `chars`,
      `compareTo` (11), `isEmpty` (15). `[RESEARCH]`
2.2.7 `sb.reverse()` on a string containing surrogate pairs — it preserves pairs, but not combining
      marks. `[TRAP]` `[RESEARCH]`
2.2.8 `StringBuilder.append(null)` appends `"null"`; `append((Object) null)` too; `append(char[])`
      with a null array throws. `[TRAP]`
2.2.9 `String.join`, `StringJoiner` (prefix/suffix/delimiter/`setEmptyValue`), and
      `Collectors.joining`. `[X-REF 04]`
2.2.10 `String.format` / `Formatter` grammar, `%s %d %f %n %,d %-10s %08.2f`, and argument index
       `%1$s`.
2.2.11 `%n` versus `\n`, and `System.lineSeparator()`. `[TRAP]`
2.2.12 `MessageFormat` and why logging frameworks use `{}` placeholders instead of concatenation —
       the log statement that formats even when the level is disabled. `[TRAP]` `[X-REF 20]`
2.2.13 Regex essentials as they appear in `String`: `matches` anchors the whole input,
       `replaceAll` treats `$` and `\` in the replacement specially (`Matcher.quoteReplacement`).
       `[TRAP]`
2.2.14 `Pattern.compile` once into a `static final` field; `String.matches` recompiles every call.
       `[TRAP]` `[NUM]`
2.2.15 Catastrophic backtracking / ReDoS as a real production failure. `[X-REF 13]`
2.2.16 `Pattern.quote`, `Pattern.split`, named groups, `Matcher.results()` (Java 9).
2.2.17 Character encoding: `String` is UTF-16 internally; `getBytes(Charset)` and
       `new String(bytes, Charset)` are where encoding actually happens.
2.2.18 The no-arg `getBytes()`/`new String(byte[])` use the default charset — which is UTF-8 from
       Java 18 (JEP 400) and platform-dependent before. `[VERSION-TRAP]` `[TRAP]` `[RESEARCH]`
2.2.19 `file.encoding`, `native.encoding`, and `-Dfile.encoding=UTF-8` as the legacy fix.
       `[RESEARCH]`
2.2.20 Unicode: code point vs code unit vs grapheme cluster; `length()` counts code units.
       `[TRAP]` `[NUM]`
2.2.21 Surrogate pairs: an emoji has `length() == 2`, `charAt` returns half of it,
       `codePointCount` is the right count. `[TRAP]` `[PROVE]`
2.2.22 Iterating text correctly: `codePoints()`, `offsetByCodePoints`, and `BreakIterator` for
       grapheme clusters. `[RESEARCH]`
2.2.23 Normalisation (`Normalizer`, NFC/NFD) and why two visually identical strings can be unequal.
       `[TRAP]` `[RESEARCH]`
2.2.24 Case-insensitive comparison: `equalsIgnoreCase` vs
       `toLowerCase(Locale.ROOT)` vs `Collator` — and the locale trap again.
2.2.25 Text blocks for embedded JSON/SQL and their incidental-whitespace rules. `[X-REF 04]`

*(25 leaves)*

### §2.3 Immutability design

2.3.1 The five rules: final class, private final fields, no mutators, defensive copy in, defensive
      copy out.
2.3.2 Rule 1 alternative: private constructor plus static factories, which also enables caching and
      subclass control.
2.3.3 Defensive copy in the constructor **after** the null check and **before** the validity check —
      the TOCTOU window if you order it the other way. `[TRAP]` `[PROVE]`
2.3.4 Defensive copy on the way out of getters, or return an unmodifiable view — and which to pick.
2.3.5 `List.copyOf`/`Map.copyOf`/`Set.copyOf` versus `Collections.unmodifiableList` for both
      directions. `[X-REF 02]`
2.3.6 Shallow versus deep immutability: an immutable holder of mutable elements. `[TRAP]`
2.3.7 Mutable JDK types that force copies: `Date`, `Calendar`, arrays, `java.util` collections,
      `SimpleDateFormat`.
2.3.8 `java.time` types, `String`, wrappers, `BigDecimal`, `BigInteger`, `UUID`, `Locale` as
      already-immutable building blocks.
2.3.9 Benefits: thread safety with no synchronisation, safe map key, safe caching and sharing, no
      defensive copying by callers, failure atomicity.
2.3.10 Costs: allocation per change, and the `withX` copy-constructor idiom for "modification".
2.3.11 Records as rules 1–3 for free, plus a compact constructor for 4 and an accessor override
       for 5. `[BUILD]` `[X-REF 04]`
2.3.12 Immutable class with a lazily computed, cached derived field (`hash`) — and why that does
       not break immutability. `[PROVE]`
2.3.13 The JMM `final` field freeze that makes an immutable object safe to publish by a data race.
       `[X-REF 05]`
2.3.14 An immutable class that is still unsafe: a non-final field, or `this` escaping the
       constructor. `[TRAP]` `[X-REF 05]`
2.3.15 Builder pattern for immutables with many components. `[BUILD]`
2.3.16 Interning/caching immutable values (`Integer.valueOf`, `Boolean.valueOf`,
       `BigDecimal.ZERO`) and when to do it in your own type.

*(16 leaves)*

### §2.4 Numbers: floating point, `BigDecimal`, and money

2.4.1 Why `double` cannot represent 0.1: binary fractions and the exact stored value.
      `[PROVE]` `[NUM]`
2.4.2 `0.1 + 0.2 == 0.30000000000000004`; `1.03 - 0.42 == 0.6100000000000001`. `[NUM]`
2.4.3 Accumulated error in a loop; `Kahan` summation and `DoubleStream.sum`'s compensated
      summation. `[RESEARCH]`
2.4.4 Comparing doubles with an epsilon, and why a fixed epsilon is wrong across magnitudes;
      `Math.ulp`. `[PROVE]` `[RESEARCH]`
2.4.5 `Double.compare` vs `<`/`==` for NaN and −0.0. `[TRAP]`
2.4.6 `float` versus `double`: never use `float` unless memory dominates.
2.4.7 `BigDecimal` structure: an arbitrary-precision unscaled integer plus a 32-bit `scale`; value
      is `unscaled × 10^(−scale)`. `[SOURCE]` `[NUM]`
2.4.8 Immutability: every operation returns a new instance; ignoring the return value is a silent
      no-op. `[TRAP]`
2.4.9 `new BigDecimal(0.1)` inherits the double's error; `new BigDecimal("0.1")` and
      `BigDecimal.valueOf(0.1)` do not. Always construct from a `String` or `valueOf`. `[TRAP]`
      `[NUM]`
2.4.10 `BigDecimal.valueOf(double)` goes via `Double.toString`, so it is "what you typed", not
       "what is stored". `[PROVE]`
2.4.11 `equals` compares value **and** scale — `2.0` is not `equal` to `2.00`; `compareTo` ignores
       scale. `[TRAP]` `[PROVE]`
2.4.12 Consequences: `BigDecimal` is a hazardous `HashMap`/`HashSet` key and a hazardous
       `assertEquals` argument; `TreeSet` and `HashSet` disagree about duplicates. `[TRAP]`
       `[X-REF 02]` `[X-REF 16]`
2.4.13 `divide` without a rounding mode throws `ArithmeticException` on a non-terminating result;
       always pass scale and `RoundingMode`. `[TRAP]`
2.4.14 The eight `RoundingMode`s, and `HALF_UP` vs `HALF_EVEN` (banker's rounding) for money.
       `[PROVE]`
2.4.15 `setScale`, `stripTrailingZeros` (and its scientific-notation surprise on `100.0`),
       `toPlainString` vs `toString`, `precision`, `scale`, `signum`, `movePointLeft`. `[TRAP]`
       `[RESEARCH]`
2.4.16 `MathContext` and `DECIMAL32`/`DECIMAL64`/`DECIMAL128`/`UNLIMITED`; when precision-based
       rounding beats scale-based. `[RESEARCH]`
2.4.17 `BigDecimal.ZERO`/`ONE`/`TEN` constants and cheap-zero checks (`signum() == 0`, not
       `equals(ZERO)`). `[TRAP]`
2.4.18 The minor-units `long` alternative (store cents), its speed and exactness, and its cost:
       the scale lives in your head. `[NUM]`
2.4.19 A `Money` type with a currency and a scale, and why `BigDecimal` alone is not a money type.
       `[BUILD]`
2.4.20 Money in the database: `NUMERIC(19,4)` versus `DOUBLE`, and the JDBC/JPA mapping.
       `[X-REF 08]` `[X-REF 09]`
2.4.21 `BigInteger`: arbitrary precision integers, `mod`/`modPow`/`gcd`/`isProbablePrime`, and its
       use in crypto. `[X-REF 13]`
2.4.22 `BigDecimal`/`BigInteger` are 10–100× slower than primitives and allocate per operation.
       `[NUM]`
2.4.23 Parsing user-entered numbers: `NumberFormat`/`DecimalFormat` with an explicit `Locale`, and
       the comma-versus-dot decimal separator bug. `[TRAP]`
2.4.24 `DecimalFormat` is **not** thread-safe. `[TRAP]`

*(24 leaves)*

### §2.5 Date and time

2.5.1 Why `java.util.Date`/`Calendar`/`SimpleDateFormat` were replaced: mutability, zero-based
      months, 1900-based years, no zone/instant distinction, no thread safety.
2.5.2 `SimpleDateFormat` is not thread-safe; a shared static instance silently produces wrong dates
      under load. `[TRAP]` `[PROVE]`
2.5.3 `java.time` (JSR-310, Joda-Time lineage, Stephen Colebourne): immutable, thread-safe,
      null-hostile, ISO-8601, fluent `of`/`from`/`parse`/`with`/`plus`/`minus`/`to`/`at` naming.
      `[RESEARCH]`
2.5.4 The type table: `Instant`, `LocalDate`, `LocalTime`, `LocalDateTime`, `ZonedDateTime`,
      `OffsetDateTime`, `OffsetTime`, `Year`, `YearMonth`, `MonthDay`, `Duration`, `Period`,
      `ZoneId`, `ZoneOffset`, `Clock`, `DayOfWeek`, `Month`, `InstantSource` (17). `[RESEARCH]`
2.5.5 `LocalDateTime` is not an instant: no zone, so it does not identify a moment and cannot be
      converted to epoch millis without one. `[TRAP]`
2.5.6 Store `Instant` (or `TIMESTAMP WITH TIME ZONE`) for event times; store `LocalDate` for
      birthdays and invoice dates. `[X-REF 09]`
2.5.7 `Duration` (time-based, seconds+nanos) versus `Period` (date-based, years/months/days).
2.5.8 `Duration.ofDays(1)` is exactly 24 hours; `Period.ofDays(1)` is one calendar day — they
      differ across a DST boundary. `[TRAP]` `[PROVE]`
2.5.9 DST gaps and overlaps: a local time that does not exist (spring forward) or occurs twice
      (fall back), and how `ZonedDateTime` resolves each by documented rule instead of throwing.
      `[TRAP]` `[PROVE]`
2.5.10 `withEarlierOffsetAtOverlap`/`withLaterOffsetAtOverlap` and `ZoneRules.getValidOffsets`.
       `[RESEARCH]`
2.5.11 `ZoneId.of("Europe/London")` versus `ZoneOffset.ofHours(1)` — a region versus a fixed offset,
       and why you must store the region for future scheduling. `[TRAP]`
2.5.12 `ZoneId.systemDefault()` as an implicit dependency on the host; a container without `TZ` set
       is UTC and your laptop is not. `[TRAP]` `[X-REF 19]`
2.5.13 The IANA tzdb ships inside the JDK and changes several times a year; `TZUpdater`, and stale
       zone rules as a real incident class. `[RESEARCH]`
2.5.14 Arithmetic: `plusDays`, `plusMonths` and the end-of-month clamping rule (Jan 31 + 1 month =
       Feb 28). `[TRAP]` `[PROVE]`
2.5.15 `TemporalAdjusters`: `firstDayOfMonth`, `lastDayOfMonth`, `next`, `nextOrSame`,
       `firstInMonth`, and writing your own. `[RESEARCH]`
2.5.16 `ChronoUnit.between`, `Period.between`, `Duration.between` and their truncation semantics.
2.5.17 `truncatedTo`, `ChronoField`, `TemporalAccessor`, `TemporalQuery` — the SPI layer under the
       concrete types. `[RESEARCH]`
2.5.18 `DateTimeFormatter`: immutable and thread-safe; `ISO_INSTANT`, `ISO_LOCAL_DATE`,
       `ISO_OFFSET_DATE_TIME`, `RFC_1123_DATE_TIME`, `ofPattern`, `ofLocalizedDateTime`,
       `DateTimeFormatterBuilder`.
2.5.19 Pattern-letter traps: `YYYY` (week-based year) versus `yyyy`, `DD` versus `dd`, `mm` versus
       `MM`, `hh` versus `HH` — the New Year's Eve bug. `[TRAP]` `[PROVE]` `[RESEARCH]`
2.5.20 Parsing strictness: `ResolverStyle.STRICT`/`SMART`/`LENIENT`, and why `SMART` is the default.
       `[RESEARCH]`
2.5.21 `DateTimeParseException` and how to report the error index.
2.5.22 Interop: `Date.toInstant`, `Date.from(Instant)`, `Calendar.toInstant`,
       `GregorianCalendar.toZonedDateTime`, `Timestamp` and its nanosecond field. `[X-REF 08]`
2.5.23 `Clock`: `systemUTC`, `system(zone)`, `fixed`, `offset`, `tick` — inject a `Clock` so time is
       testable, never call `Instant.now()` inside domain logic. `[BUILD]` `[X-REF 16]`
2.5.24 Precision: `Instant.now()` gives microseconds on Java 9+ (nanoseconds where the OS allows),
       not milliseconds as on Java 8 — a test-equality trap when round-tripping through a database.
       `[TRAP]` `[VERSION-TRAP]` `[RESEARCH]`
2.5.25 Leap seconds: java.time ignores them (the "Java time-scale"); leap years, and
       `Year.isLeap`. `[RESEARCH]`
2.5.26 `Instant` versus `System.currentTimeMillis` versus `System.nanoTime` for the three different
       questions they answer.
2.5.27 Storing and transmitting: ISO-8601 strings on the wire, epoch millis where compactness wins,
       and never a locale-formatted string. `[X-REF 12]`

*(27 leaves)*

### §2.6 Exceptions in practice

2.6.1 Checked versus unchecked as a design decision: recoverable condition versus programming error.
2.6.2 Why modern practice leans unchecked: no composition with lambdas and streams, signature
      pollution, and empty catch blocks.
2.6.3 The lambda problem concretely: you cannot throw a checked exception from a `Function`, and the
      four workarounds (wrap, sneaky-throw, custom functional interface, `Result` type). `[BUILD]`
      `[X-REF 04]`
2.6.4 Sneaky throws: the generic-erasure trick, Lombok's `@SneakyThrows`, and why it is a loaded
      gun. `[PROVE]` `[TRAP]`
2.6.5 Spring's translation of `SQLException` into the unchecked `DataAccessException` hierarchy as
      the canonical example of the argument. `[X-REF 07]` `[X-REF 08]`
2.6.6 Exception translation: wrap a low-level exception in a domain exception, always preserving
      the cause.
2.6.7 Designing an exception hierarchy: one base per bounded context, carry data as fields rather
      than formatted into the message, no exception per error code. `[BUILD]`
2.6.8 When to use `IllegalArgumentException` versus `IllegalStateException` versus
      `NullPointerException` versus a custom type.
2.6.9 `Objects.requireNonNull` at the top of every public method, and fail-fast in general.
2.6.10 Failure atomicity: an object must be usable after a failed operation.
2.6.11 Exceptions as control flow is an anti-pattern — except where it is the only option
       (parsing, `NumberFormatException`), and then measure. `[TRAP]`
2.6.12 Stack-trace cost, `fillInStackTrace`, and the stackless-exception override for
       high-frequency control-flow exceptions. `[NUM]` `[RESEARCH]`
2.6.13 `-XX:-OmitStackTraceInFastThrow`: C2 replaces hot implicit exceptions (NPE, AIOOBE, CCE)
       with a preallocated stackless instance, which is why production NPEs sometimes have empty
       stack traces. `[TRAP]` `[RESEARCH]` `[X-REF 06]`
2.6.14 Logging discipline: log **or** rethrow, never both; log the throwable object, not
       `getMessage()`. `[TRAP]` `[X-REF 20]`
2.6.15 Never swallow, never `printStackTrace()` in production code.
2.6.16 Exceptions across API boundaries: a REST error contract, `@ControllerAdvice`, and not leaking
       stack traces to clients. `[X-REF 12]` `[X-REF 13]`
2.6.17 `try`-with-resources with multiple resources, a resource that is null, and a
       `close()` that must be idempotent.
2.6.18 Custom `AutoCloseable`: declaring `close()` without `throws` so callers are not forced into
       a catch. `[BUILD]`
2.6.19 `Thread.interrupt` and the `InterruptedException` protocol restated as an exception-design
       example. `[X-REF 05]`
2.6.20 `StackOverflowError` from recursion, and the absence of tail-call optimisation in the JVM.
       `[PROVE]` `[X-REF 06]`
2.6.21 `OutOfMemoryError` variants and why catching one rarely helps. `[X-REF 06]`
2.6.22 Assertions versus exceptions versus validation frameworks (`jakarta.validation`).
       `[X-REF 07]`
2.6.23 Testing exceptions: `assertThrows`, asserting the message versus asserting the type.
       `[X-REF 16]`

*(23 leaves)*

### §2.7 Generics in anger

2.7.1 Generic method versus wildcard: when to name the type variable and when a wildcard is enough.
2.7.2 The wildcard-capture helper method idiom for `swap(List<?>, int, int)`. `[PROVE]` `[BUILD]`
2.7.3 PECS applied to real signatures: `Collection.addAll`, `Collections.copy`,
      `Comparator<? super T>`, `Stream.map(Function<? super T, ? extends R>)`. `[X-REF 02]`
2.7.4 Never use a wildcard as a return type. `[PROVE]`
2.7.5 `Class<T>` as a type token, `Class.cast`, `asSubclass`, and the typesafe heterogeneous
      container.
2.7.6 Super type tokens (`TypeReference`, Jackson, Spring's `ParameterizedTypeReference`) and how
      they defeat erasure through an anonymous subclass's `Signature` attribute. `[PROVE]`
      `[RESEARCH]`
2.7.7 Recovering generic type arguments at runtime: `getGenericSuperclass`,
      `ParameterizedType.getActualTypeArguments` — only where they were captured in a class file.
      `[RESEARCH]`
2.7.8 Generic arrays: `(T[]) new Object[n]` with a documented `@SuppressWarnings`, versus
      `Array.newInstance(componentType, n)` with a `Class<T>`. `[PROVE]` `[BUILD]`
2.7.9 The `ArrayStoreException` you get when a `(T[]) new Object[]` escapes as `String[]`. `[TRAP]`
      `[PROVE]`
2.7.10 Generic bounds and self-referential types: the builder pattern with
       `<T extends Builder<T>>` (CRTP). `[BUILD]`
2.7.11 Type inference (JLS 18) in the cases you meet: diamond, generic method arguments, target
       typing of lambdas and method references, `var`, and conditional expressions. `[RESEARCH]`
2.7.12 Inference failure messages and the explicit type witness as the fix.
2.7.13 Overloading and generics: two methods whose erasures clash do not compile, even with
       different type arguments. `[TRAP]`
2.7.14 A generic class cannot have a static member using the class's type parameter, cannot be
       thrown or caught, and cannot extend `Throwable`. `[PROVE]`
2.7.15 `instanceof` with generics: only unbounded wildcards allowed; pattern matching does not
       change this. `[TRAP]`
2.7.16 Migration compatibility and raw types: how Java 5 kept `List` and `List<String>` in the same
       system, and the cost we still pay.
2.7.17 `Optional<T>` and generics: never a field, never a parameter, never in a collection.
       `[X-REF 04]`
2.7.18 Reading a hard JDK signature end to end, e.g.
       `static <T, K, U, M extends Map<K,U>> Collector<T,?,M> toMap(Function<? super T, ? extends K>,
       Function<? super T, ? extends U>, BinaryOperator<U>, Supplier<M>)`. `[PROVE]` `[X-REF 04]`

*(18 leaves)*

### §2.8 Copying, cloning and equality of composite objects

2.8.1 Reference copy versus shallow copy versus deep copy, with the exact aliasing each leaves.
2.8.2 `clone()` mechanics: `Object.clone` is native, allocates without a constructor, copies fields
      bitwise, and throws `CloneNotSupportedException` unless `Cloneable` is present. `[SOURCE]`
2.8.3 Why `clone` is broken: no constructor invariants, shallow by default, `final` fields cannot
      be reassigned in it, the contract is "no constructors are called" but not enforced, and a
      superclass that does not support it poisons the subclass. `[TRAP]` `[PROVE]`
2.8.4 Correct `clone` if you must: covariant return, call `super.clone()`, deep-copy the mutable
      fields. `[BUILD]`
2.8.5 Copy constructor and static copy factory as the recommended replacement, including the
      "conversion constructor" variant. `[BUILD]`
2.8.6 Deep copy strategies: manual, serialization round-trip (slow, and a security hazard), Jackson
      round-trip, and a `copy()` method per type. `[NUM]`
2.8.7 Arrays: `clone`, `Arrays.copyOf`, `System.arraycopy` — all shallow. `[TRAP]`
2.8.8 Collections: `new ArrayList<>(other)` is shallow; `List.copyOf` is shallow and immutable.
      `[X-REF 02]`
2.8.9 `Comparable` versus `Comparator`, the `compareTo` contract, and consistency with `equals`.
      `[X-REF 02]`
2.8.10 Never subtract to compare: `a - b` overflows. Use `Integer.compare`. `[PROVE]` `[TRAP]`
2.8.11 `compareTo` returning a sign, not a magnitude, and why TimSort throws "Comparison method
       violates its general contract". `[X-REF 02]`
2.8.12 `equals`/`hashCode` for a class with a mutable field used in the hash — the stranded-key bug.
       `[TRAP]` `[X-REF 02]`
2.8.13 `equals`/`hashCode` on JPA entities: id-based, business-key-based, or `getClass` versus
       Hibernate proxies. `[TRAP]` `[X-REF 08]`
2.8.14 Lombok `@Data`/`@EqualsAndHashCode`/`@Value` and their pitfalls: `callSuper`, lazy fields,
       generated setters on an intended value type. `[TRAP]` `[X-REF 08]`

*(14 leaves)*

### §2.9 Object lifecycle and references

2.9.1 Object creation, reachability, and garbage collection at the level the language exposes.
      `[X-REF 06]`
2.9.2 The reference strength ladder: strong → soft → weak → phantom, and the `ReferenceQueue`.
      `[X-REF 06]`
2.9.3 `SoftReference` for caches (and why you should use a real cache library instead),
      `WeakReference` for canonical maps and listeners, `PhantomReference` for cleanup.
      `[X-REF 02]` `[X-REF 15]`
2.9.4 `Cleaner`: registering a runnable that must **not** capture the referent, or nothing is ever
      collected. `[TRAP]` `[PROVE]` `[RESEARCH]`
2.9.5 `finalize` deprecation timeline and the migration path. `[RESEARCH]`
2.9.6 `try`-with-resources as the primary resource discipline; `close()` idempotency and
      exception behaviour.
2.9.7 Resource leaks that the language cannot help with: unclosed streams, connections, executors,
      `ThreadLocal`s. `[X-REF 05]` `[X-REF 06]`
2.9.8 `ThreadLocal` leaks in a pooled-thread environment, and `remove()` in a `finally`.
      `[TRAP]` `[X-REF 05]`
2.9.9 Static collections as an unbounded cache — the archetypal Java leak. `[TRAP]` `[X-REF 02]`
2.9.10 `System.gc()` is a hint; `-XX:+DisableExplicitGC`. `[TRAP]`
2.9.11 Object resurrection in a finaliser, and why `finalize` delays reclamation by a full cycle.
       `[PROVE]`

*(11 leaves)*

### §2.10 Serialization

2.10.1 `Serializable` as a marker; the default protocol writes the whole reachable object graph.
2.10.2 `serialVersionUID`: what it is, when it is generated, and how an incompatible change breaks
       deserialization with `InvalidClassException`. `[TRAP]` `[NUM]`
2.10.3 `transient` fields, static fields, and what the default protocol skips.
2.10.4 The magic methods: `writeObject`, `readObject`, `readObjectNoData`, `writeReplace`,
       `readResolve`, and their exact private signatures. `[SOURCE]` `[RESEARCH]`
2.10.5 `readObject` is effectively a hidden public constructor that bypasses all your validation.
       `[TRAP]` `[PROVE]`
2.10.6 The serialization proxy pattern as the safe form. `[BUILD]`
2.10.7 `readResolve` for singletons, and enum serialization ignoring all of these hooks by
       specification. `[RESEARCH]` `[PROVE]`
2.10.8 `Externalizable` and why it is worse, not better.
2.10.9 Record serialization: components are serialized and reconstructed through the canonical
       constructor, so validation runs. `[RESEARCH]` `[X-REF 04]`
2.10.10 Deserialization of untrusted data as a remote-code-execution class (gadget chains,
        `ysoserial`), and why Java serialization is Java's largest attack surface. `[X-REF 13]`
2.10.11 JEP 290 serialization filters, `ObjectInputFilter`, `jdk.serialFilter`, and the limitation
        that filters only cover `ObjectInputStream` — not Jackson, SnakeYAML, Kryo. `[RESEARCH]`
        `[TRAP]`
2.10.12 The practical rule: do not use Java serialization for persistence or wire formats; use
        JSON/Protobuf/Avro. `[X-REF 12]` `[X-REF 14]`
2.10.13 Serialization compatibility rules: which changes are compatible (adding a field, adding a
        class) and which are not (changing a type, removing a field's semantics).
2.10.14 Serializing a lambda: possible, fragile, and dependent on `invokedynamic` metadata.
        `[TRAP]` `[RESEARCH]`

*(14 leaves)*

### §2.11 Null discipline

2.11.1 The billion-dollar mistake; where nulls legitimately come from in Java.
2.11.2 `Optional` as a return type only: not a field, not a parameter, not a collection element,
       not serialized. `[X-REF 04]`
2.11.3 `Optional.get` without `isPresent` is just an NPE with more steps; `orElseThrow` as the
       honest form.
2.11.4 `orElse` versus `orElseGet` — `orElse` evaluates its argument eagerly. `[TRAP]` `[PROVE]`
2.11.5 Null-object pattern, empty collections instead of null, and never returning `null` from a
       method returning a collection or array. `[X-REF 02]`
2.11.6 `Objects.requireNonNullElse`, `Optional.ofNullable`, `Map.getOrDefault`.
2.11.7 Nullability annotations: JSR-305 `@Nullable`/`@NonNull`, JSpecify, and IDE/compiler
       enforcement. `[RESEARCH]`
2.11.8 `@NonNullApi`/package-level defaults and Kotlin interop. `[RESEARCH]`
2.11.9 Reading a helpful NPE message to find which link in the chain was null. `[RESEARCH]`
2.11.10 Null in collections: which types allow it and which throw. `[X-REF 02]`
2.11.11 Null and `switch`, `equals`, `==`, string concatenation, and autoboxing — the four places it
        behaves differently.

*(11 leaves)*

### §2.12 Reflection and dynamic access

2.12.1 `Class` objects: `X.class`, `obj.getClass()`, `Class.forName`, and array/primitive class
       objects.
2.12.2 `getName` vs `getSimpleName` vs `getCanonicalName` vs `getTypeName` — the four different
       answers for an inner class and an array. `[TRAP]` `[NUM]`
2.12.3 Field/Method/Constructor lookup: `getX` (public, inherited) vs `getDeclaredX` (all, not
       inherited). `[TRAP]`
2.12.4 `setAccessible(true)`, module encapsulation, and `InaccessibleObjectException`.
       `[RESEARCH]`
2.12.5 Reflective invocation cost and the JIT's inability to inline it before it is warm.
       `[NUM]` `[RESEARCH]`
2.12.6 `MethodHandle`/`VarHandle`/`LambdaMetafactory` as the faster, safer modern layer.
       `[RESEARCH]`
2.12.7 Dynamic proxies: `java.lang.reflect.Proxy`, `InvocationHandler`, interface-only limitation,
       and CGLIB/ByteBuddy subclass proxies. `[X-REF 07]`
2.12.8 Where reflection actually shows up in your stack: Spring, Jackson, JPA, JUnit, Mockito.
2.12.9 Reflection and generics: what survives erasure and what does not.
2.12.10 Setting a `final` field reflectively: it worked, it stopped working for records and hidden
        classes, and JEP 500 proposes to end it entirely. `[VERSION-TRAP]` `[RESEARCH]` `[TRAP]`
2.12.11 Reflection as a security surface, and the removal of the Security Manager (JEP 486, Java 24).
        `[RESEARCH]` `[X-REF 13]`

*(11 leaves)*

### §2.13 Pass-by-value and parameter semantics

2.13.1 Java is always pass-by-value; for a reference type the copied value is the reference.
2.13.2 Mutating through the copied reference is visible to the caller; reassigning the parameter is
       not. `[PROVE]`
2.13.3 Why a `swap(a, b)` method is impossible in Java. `[PROVE]`
2.13.4 Passing a `String` and calling `toUpperCase()` changes nothing, because there is no mutation
       path at all.
2.13.5 The "Java passes objects by reference" claim, why it is wrong, and the precise
       counterexample. `[TRAP]`
2.13.6 Arrays as the mutable out-parameter workaround, and why an explicit result object is better.
2.13.7 Varargs as arrays again: mutating the varargs array inside the method.
2.13.8 Defensive copying at the parameter boundary, restated from §2.3 as a parameter-semantics
       consequence.
2.13.9 `final` parameters: no effect on the caller, only on the method body.

*(9 leaves)*

### §2.14 Design idioms the interview expects

2.14.1 Static factory methods over constructors: naming, caching, subtype return, no name
       collision. `[BUILD]`
2.14.2 The builder pattern for many parameters, and the telescoping-constructor anti-pattern it
       replaces. `[BUILD]`
2.14.3 Singleton: enum, holder class, eager static, double-checked locking with `volatile` — and
       which to use. `[PROVE]` `[X-REF 05]`
2.14.4 Double-checked locking without `volatile` is broken; the exact reordering that breaks it.
       `[TRAP]` `[PROVE]` `[X-REF 05]`
2.14.5 Utility class with a private constructor that throws.
2.14.6 Dependency injection over hardwired resources, even without a framework. `[X-REF 07]`
2.14.7 Favour composition and delegation over inheritance; the forwarding-class idiom. `[X-REF 02]`
2.14.8 Program to interfaces; minimise accessibility; make classes immutable when you can.
2.14.9 Prefer primitives to boxed primitives; avoid creating unnecessary objects; know when
       object pooling is wrong. `[NUM]`
2.14.10 Return empty collections, not nulls; validate parameters; document thread safety.
2.14.11 The `Effective Java` items this file's traps map to, as a cross-index. `[RESEARCH]`
2.14.12 Where each idiom is over-applied: builders for 2-field types, interfaces with one
        implementation, defensive copies in a hot path. `[TRAP]`

*(12 leaves)*

### §2.15 Which construct do I reach for

2.15.1 Value type: record vs class vs enum vs `Map<String,Object>`.
2.15.2 Contract: interface vs abstract class vs functional interface vs sealed hierarchy.
2.15.3 Constant: `static final` vs enum vs config property.
2.15.4 Error signalling: return value vs `Optional` vs checked vs unchecked vs `Result` type.
2.15.5 Number: `int` vs `long` vs `BigDecimal` vs `long` minor units vs `double`.
2.15.6 Text: `String` vs `StringBuilder` vs `char[]` (passwords) vs `byte[]`. `[X-REF 13]`
2.15.7 Time: `Instant` vs `LocalDate` vs `ZonedDateTime` vs epoch millis.
2.15.8 Copying: view vs shallow copy vs deep copy vs immutable rebuild.
2.15.9 Nested type: static nested vs inner vs local vs anonymous vs lambda.
2.15.10 The consolidated decision table.

*(10 leaves)*

---

**PART 2 total: 232 leaves**

---

## PART 3 — ADVANCED (INTERNALS / UNDER THE HOOD)

### §3.1 The `javac` pipeline and the desugaring catalogue

3.1.1 The compiler phases: parse → enter → annotation processing → attribute → flow → desugar →
      generate. `[RESEARCH]`
3.1.2 The class file structure: magic `0xCAFEBABE`, minor/major version, constant pool, access
      flags, fields, methods, attributes. `[SOURCE]` `[NUM]` `[X-REF 06]`
3.1.3 Major version numbers: 52 = Java 8, 55 = 11, 61 = 17, 65 = 21, and
      `UnsupportedClassVersionError`. `[NUM]` `[RESEARCH]`
3.1.4 `--release` versus `-source`/`-target`, and why `-target` alone produces class files that
      reference APIs the target JDK does not have. `[TRAP]` `[RESEARCH]`
3.1.5 The constant pool: `CONSTANT_Utf8`, `Class`, `String`, `Fieldref`, `Methodref`,
      `InvokeDynamic`, `MethodHandle`, `Dynamic`. `[SOURCE]`
3.1.6 The full desugaring catalogue, each with the `javap` evidence: enhanced for, varargs, boxing,
      string concat, string switch, enum switch, inner-class capture, lambdas, assertions,
      try-with-resources, records' `Object` methods, generics casts, bridge methods. `[BYTECODE]`
3.1.7 Attributes that carry information erasure would otherwise lose: `Signature`,
      `LocalVariableTable`, `LineNumberTable`, `MethodParameters`, `RuntimeVisibleAnnotations`,
      `NestHost`/`NestMembers`, `PermittedSubclasses`, `Record`, `BootstrapMethods`. `[RESEARCH]`
3.1.8 `-g`, `-parameters`, and what Spring/Jackson lose without them. `[TRAP]` `[X-REF 07]`
3.1.9 `-Xlint` categories worth turning on: `all`, `-Xlint:unchecked`, `rawtypes`, `fallthrough`,
      `serial`, `overloads`, `this-escape` (Java 21). `[RESEARCH]`
3.1.10 The `this-escape` warning added in Java 21 and what it detects. `[RESEARCH]`
3.1.11 `javap -c -p -v` as the tool for every claim in this part. `[BYTECODE]`
3.1.12 What the compiler does **not** do: no inlining, no loop optimisation, no constant
       propagation beyond constant expressions — all of that is the JIT's job. `[TRAP]`
       `[X-REF 06]`
3.1.13 The stack-based bytecode model: operand stack, local variable array, and reading a simple
       method's instructions. `[BYTECODE]` `[X-REF 06]`
3.1.14 The Class-File API (JEP 484, final in Java 24) replacing ASM for tooling. `[RESEARCH]`

*(14 leaves)*

### §3.2 `String` internals

3.2.1 The field set: `@Stable private final byte[] value`, `private final byte coder`,
      `private int hash`, `private boolean hashIsZero`, `static final boolean COMPACT_STRINGS`,
      `serialVersionUID = -6849794470754667710L`. `[SOURCE]` `[NUM]`
3.2.2 Compact strings (JEP 254, Java 9): `byte[]` + `coder` instead of `char[]`; `LATIN1 = 0`,
      `UTF16 = 1`; one byte per character for Latin-1 content. `[SOURCE]` `[NUM]` `[RESEARCH]`
3.2.3 The measured heap saving and the counter-case: an application that is mostly UTF-16 pays a
      small cost. `[NUM]` `[RESEARCH]`
3.2.4 `StringLatin1` and `StringUTF16` as the two implementation classes every `String` method
      delegates to, and the intrinsics that replace them at runtime. `[SOURCE]` `[RESEARCH]`
3.2.5 `-XX:-CompactStrings` to turn it off, and when that is ever right. `[RESEARCH]`
3.2.6 `hashCode()` source, line by line: the `hash`/`hashIsZero` double field, and why the empty
      string and `"\0"`-like inputs need the flag. `[SOURCE]` `[PROVE]`
3.2.7 The `31 *` multiplier: odd prime, `31*i == (i << 5) - i`, and the distribution argument.
      `[PROVE]` `[NUM]` `[X-REF 02]`
3.2.8 Colliding strings: `"Aa"`/`"BB"`, `"FB"`/`"Ea"`, and the hash-collision DoS that led to
      `HashMap` treeification. `[NUM]` `[X-REF 02]` `[X-REF 13]`
3.2.9 `equals()` source: identity short-circuit, `coder` comparison, then `StringLatin1.equals` on
      the raw bytes for both coders. `[SOURCE]` `[PROVE]`
3.2.10 `compareTo` source and the four coder combinations. `[SOURCE]`
3.2.11 The StringTable: a native fixed-size hash table, `-XX:StringTableSize` (default 65536 in
       modern JDKs, 1009 historically), `-XX:+PrintStringTableStatistics`. `[NUM]` `[RESEARCH]`
3.2.12 `intern()` is a native call into the StringTable, and its cost grows when the table is
       undersized. `[NUM]` `[RESEARCH]`
3.2.13 The pool moved from PermGen to the heap in Java 7, so interned strings are now collectable.
       `[VERSION-TRAP]` `[RESEARCH]`
3.2.14 G1 string deduplication (JEP 192, 8u20): `-XX:+UseStringDeduplication`,
       `-XX:StringDeduplicationAgeThreshold` (default 3), the concurrent dedup thread, and how it
       differs from interning. `[RESEARCH]` `[NUM]`
3.2.15 An interned string is deduplicated before entering the table and never deduplicated again.
       `[RESEARCH]`
3.2.16 Memory arithmetic for a `String`: 12-byte header + 4 (`value` ref) + 4 (`hash`) + 1
       (`coder`) + 1 (`hashIsZero`) + padding = 24 bytes, plus the byte array's 16-byte header and
       payload. A 10-char ASCII string ≈ 48 bytes. `[NUM]` `[PROVE]` `[X-REF 06]`
3.2.17 `substring` allocation since Java 7, and the deliberate loss of the O(1) sharing form.
       `[NUM]`
3.2.18 `String` as a value-based-ish class: `@Stable`, constant folding of `final String` fields,
       and the JIT's ability to fold `"abc".length()`. `[RESEARCH]` `[X-REF 06]`
3.2.19 `String.describeConstable`/`ConstantDesc` and condy-based constant folding. `[RESEARCH]`

*(19 leaves)*

### §3.3 `StringBuilder` and indified concatenation

3.3.1 `AbstractStringBuilder` fields: `byte[] value`, `byte coder`, `boolean maybeLatin1`,
      `int count`, `EMPTYVALUE`. `[SOURCE]`
3.3.2 Default capacity 16; `new StringBuilder(String s)` starts at `s.length() + 16`. `[NUM]`
      `[SOURCE]`
3.3.3 `ensureCapacityInternal` and `newCapacity`: `oldLength + (2 << coder)` as the preferred
      growth, routed through `ArraysSupport.newLength`, i.e. "twice the old capacity plus two".
      `[SOURCE]` `[NUM]` `[PROVE]`
3.3.4 The `<< coder` and `>> coder` arithmetic: capacity is in characters, the array is in bytes.
      `[PROVE]` `[NUM]`
3.3.5 Coder inflation: appending a non-Latin-1 character converts the whole buffer to UTF-16,
      doubling it. `[PROVE]` `[NUM]` `[TRAP]`
3.3.6 `toString()` copies the buffer — so `sb.toString()` in a loop is the same O(n²) mistake in
      disguise. `[TRAP]`
3.3.7 Growth arithmetic worked through for appending 1,000,000 characters: the number of
      reallocations and total bytes copied. `[PROVE]` `[NUM]`
3.3.8 `StringBuffer` is the same class hierarchy with `synchronized` methods and a
      `toStringCache` field. `[SOURCE]`
3.3.9 Pre-Java-9 `+` compilation: `new StringBuilder().append(...).toString()`, visible in `javap`.
      `[BYTECODE]` `[VERSION-TRAP]`
3.3.10 JEP 280 (Java 9): `javac` emits `invokedynamic` bound to
       `StringConcatFactory.makeConcatWithConstants`; the bootstrap runs once and installs a
       `CallSite`. `[SOURCE]` `[RESEARCH]` `[BYTECODE]`
3.3.11 Why: the strategy can change without recompiling, and the runtime can size the result
       exactly. `[PROVE]` `[RESEARCH]`
3.3.12 The strategies (`BC_SB`, `BC_SB_SIZED`, `MH_INLINE_SIZED_EXACT`) and the
       `-Djava.lang.invoke.stringConcat` switch; the MethodHandle strategy is the default.
       `[RESEARCH]`
3.3.13 The cost: bootstrap latency at first execution, which is why startup-sensitive code and
       AOT/CDS work has revisited it. `[RESEARCH]` `[X-REF 06]`
3.3.14 What indified concat does **not** fix: concatenation inside a loop is still one
       `invokedynamic` per iteration and still O(n²). `[TRAP]` `[PROVE]`
3.3.15 Measuring it: `javap -c` before and after, and a JMH comparison of `+`, `StringBuilder`,
       `String.format`, `String.join`, `StringJoiner`. `[NUM]` `[X-REF 06]`

*(15 leaves)*

### §3.4 Boxing internals

3.4.1 `Integer.valueOf` source: the cache bounds check and the `new Integer(i)` fallback.
      `[SOURCE]`
3.4.2 `IntegerCache`: `static final int low = -128`, a configurable `high`, the `Integer[] cache`
      array built in a static block, and the JLS requirement that −128..127 be cached.
      `[SOURCE]` `[NUM]`
3.4.3 The system property path: `java.lang.Integer.IntegerCache.high` /
      `-XX:AutoBoxCacheMax`, parsed via `VM.getSavedProperty`. `[SOURCE]` `[RESEARCH]`
3.4.4 The CDS archive path: `CDS.initializeFromArchive(IntegerCache.class)` and `archivedCache`,
      so the cache can be mapped rather than constructed. `[SOURCE]` `[RESEARCH]`
3.4.5 `Byte`/`Short`/`Long`/`Character`/`Boolean` cache classes and their fixed bounds. `[SOURCE]`
      `[NUM]`
3.4.6 `Long.valueOf` has no tunable upper bound — the asymmetry with `Integer`. `[TRAP]`
      `[RESEARCH]`
3.4.7 Boxing bytecode: `invokestatic Integer.valueOf`, unboxing: `invokevirtual intValue`.
      `[BYTECODE]`
3.4.8 Escape analysis can scalar-replace a box that never escapes, which is why some boxing
      benchmarks show zero cost. `[PROVE]` `[X-REF 06]`
3.4.9 Where escape analysis fails: the box is stored in a collection, returned, or the method is
      too big to inline. `[X-REF 06]`
3.4.10 `Integer` memory: 12-byte header + 4-byte `int` = 16 bytes, plus a 4-byte reference to reach
       it, versus 4 bytes for an `int`. `[NUM]` `[PROVE]`
3.4.11 `Long`: 12 + 4 padding + 8 = 24 bytes. `[NUM]`
3.4.12 The million-element comparison: `int[]` ≈ 4 MB versus `List<Integer>` ≈ 20 MB. `[NUM]`
       `[PROVE]` `[X-REF 02]`
3.4.13 Why `synchronized` on a boxed value is a correctness bug (a shared cached instance) as well
       as a Valhalla-forward-compatibility bug. `[TRAP]` `[RESEARCH]` `[X-REF 05]`
3.4.14 Valhalla value classes as the eventual fix, and what "flattened" would mean for the numbers
       above. `[RESEARCH]`

*(14 leaves)*

### §3.5 Generics erasure internals

3.5.1 What erasure actually emits: type variables replaced by their leftmost bound (or `Object`),
      casts inserted at every read site. `[SOURCE]` `[BYTECODE]`
3.5.2 The `Signature` attribute preserves the generic declaration for reflection and for
      separate compilation — erasure is not total. `[SOURCE]` `[PROVE]`
3.5.3 Bridge methods: why `class IntegerStack extends Stack<Integer>` gets a synthetic
      `push(Object)` that casts and delegates. `[SOURCE]` `[PROVE]` `[BYTECODE]` `[RESEARCH]`
3.5.4 Bridge methods for covariant return types.
3.5.5 Bridge methods and reflection: `Method.isBridge`, and why a naive
      `getDeclaredMethods` loop finds a method twice. `[TRAP]` `[RESEARCH]`
3.5.6 `ClassCastException` thrown from inside a bridge method with no cast in your source. `[TRAP]`
      `[PROVE]`
3.5.7 Reifiable types, precisely: primitives, non-generic types, raw types, unbounded-wildcard
      parameterisations, and arrays of reifiable types. `[SOURCE]` `[RESEARCH]`
3.5.8 Why `new T[n]` is illegal, and how `ArrayList` gets away with `Object[]` plus a suppressed
      unchecked cast in `elementData(int)`. `[SOURCE]` `[X-REF 02]`
3.5.9 Heap pollution: the exact sequence that puts a `String` into a `List<Integer>` through a
      generic varargs parameter. `[PROVE]` `[TRAP]`
3.5.10 `@SafeVarargs` and the three conditions for it being honest.
3.5.11 Erased overload clash: `f(List<String>)` and `f(List<Integer>)` produce "have the same
       erasure". `[PROVE]`
3.5.12 Static fields shared across parameterisations, demonstrated. `[PROVE]`
3.5.13 Capture conversion and the compiler-generated `CAP#1` type in error messages. `[RESEARCH]`
3.5.14 Why Java chose erasure (migration compatibility with 1.4 collections) and what C# and
       Valhalla-specialised generics do instead. `[PROVE]` `[RESEARCH]`
3.5.15 What reification would have bought and cost: `new T[]`, `instanceof List<String>`, per-
       instantiation classes, and code bloat.
3.5.16 Super type tokens: how an anonymous subclass's `Signature` attribute survives erasure and
       lets Jackson recover `List<Foo>`. `[SOURCE]` `[PROVE]` `[BUILD]`

*(16 leaves)*

### §3.6 Class loading, linking and initialization

3.6.1 The three phases: loading, linking (verification, preparation, resolution), initialization
      (JVMS 5). `[SOURCE]` `[X-REF 06]`
3.6.2 Preparation sets static fields to default values; initialization runs `<clinit>`. `[PROVE]`
3.6.3 `<clinit>` is the synthesized method containing static initialisers and static field
      initialisers in textual order. `[SOURCE]` `[BYTECODE]`
3.6.4 `<init>` is the constructor; the difference between the two in a stack trace. `[TRAP]`
3.6.5 The six active-use triggers for initialization, verbatim from JVMS 5.5. `[SOURCE]`
      `[RESEARCH]`
3.6.6 Compile-time constants are inlined and therefore never trigger initialization. `[PROVE]`
      `[BYTECODE]`
3.6.7 Initialization is guarded by a per-class lock and an initialization state machine, giving the
      exactly-once guarantee and the possibility of a class-init deadlock. `[PROVE]` `[X-REF 05]`
3.6.8 The class-initialization deadlock: two classes whose static initialisers reference each
      other from two threads. `[TRAP]` `[PROVE]` `[RESEARCH]`
3.6.9 Initialization cycles in one thread: the recursive-initialization rule lets the second entry
      through and it observes default values. `[TRAP]` `[SOURCE]` `[RESEARCH]`
3.6.10 `ExceptionInInitializerError` on first use, then `NoClassDefFoundError` forever after, with
       no cause attached — the diagnosis workflow. `[TRAP]` `[X-REF 06]`
3.6.11 `ClassNotFoundException` (a checked exception from a lookup) versus `NoClassDefFoundError`
       (a linkage error). `[TRAP]` `[X-REF 06]`
3.6.12 Class loader delegation, the bootstrap/platform/application loaders, and context class
       loaders. `[X-REF 06]`
3.6.13 Class identity is (name, defining loader) — two loaders give two incompatible classes and a
       confusing `ClassCastException`. `[TRAP]` `[PROVE]` `[X-REF 06]`
3.6.14 `Class.forName` initialisation semantics versus `loadClass`. `[TRAP]`
3.6.15 The holder-class idiom and why it is the cheapest correct lazy singleton. `[PROVE]`
       `[BUILD]`
3.6.16 The JEP draft for lazy static final fields and what problem it addresses. `[RESEARCH]`
3.6.17 Startup cost of class initialization, CDS/AppCDS, and AOT class loading in Java 24+
       (JEP 483). `[RESEARCH]` `[X-REF 06]`

*(17 leaves)*

### §3.7 Method dispatch internals

3.7.1 The five invocation instructions and exactly when `javac` emits each. `[BYTECODE]`
      `[SOURCE]`
3.7.2 `invokestatic` for statics, `invokespecial` for constructors, `private` methods (pre-11) and
      `super.` calls, `invokevirtual` for normal instance methods, `invokeinterface` for interface
      receivers, `invokedynamic` for lambdas/string concat/record `Object` methods. `[RESEARCH]`
3.7.3 Since Java 11, private instance methods use `invokevirtual` rather than `invokespecial`
      because of nestmates. `[RESEARCH]` `[VERSION-TRAP]`
3.7.4 vtable: a per-class array of method pointers built at link time; `invokevirtual` is an index
      into it. `[PROVE]` `[RESEARCH]`
3.7.5 itable: interface method tables, and why `invokeinterface` is slightly more expensive.
      `[PROVE]` `[RESEARCH]`
3.7.6 Devirtualisation: the JIT's class hierarchy analysis, monomorphic and bimorphic inline
      caches, megamorphic fallback, and uncommon-trap deoptimisation. `[RESEARCH]` `[X-REF 06]`
3.7.7 `final` and `private` methods do not make dispatch faster in practice, because the JIT
      already devirtualises the monomorphic case. `[TRAP]` `[PROVE]` `[RESEARCH]`
3.7.8 Static dispatch of overloads is decided entirely at compile time and is baked into the
      constant-pool `Methodref`. `[BYTECODE]` `[PROVE]`
3.7.9 Field access (`getfield`/`putfield`, `getstatic`/`putstatic`) is always statically resolved —
      the mechanism behind field hiding. `[BYTECODE]` `[PROVE]`
3.7.10 `invokedynamic` for lambdas: `LambdaMetafactory`, the bootstrap, the per-call-site
       `CallSite`, and why a non-capturing lambda is a singleton. `[RESEARCH]` `[X-REF 04]`
3.7.11 `AbstractMethodError`, `NoSuchMethodError`, `IncompatibleClassChangeError` as the runtime
       symptoms of a binary-incompatible recompile. `[TRAP]` `[PROVE]`
3.7.12 Reading a stack trace: synthetic frames, lambda frames (`lambda$main$0`), bridge frames,
       and proxy frames. `[TRAP]` `[X-REF 07]`

*(12 leaves)*

### §3.8 Object layout and memory

3.8.1 Object header: 8-byte mark word + 4-byte compressed class word = 12 bytes; 16 without
      compressed class pointers. `[NUM]` `[RESEARCH]` `[X-REF 06]`
3.8.2 The mark word's contents: identity hash, GC age, biased/locking bits, and what
      `System.identityHashCode` writes into it. `[PROVE]` `[X-REF 05]`
3.8.3 Computing an identity hash **inflates** the mark word usage and interacts with locking —
      a real reason not to call it casually. `[TRAP]` `[RESEARCH]`
3.8.4 Array header = object header + 4-byte length = 16 bytes. `[NUM]`
3.8.5 8-byte alignment and `-XX:ObjectAlignmentInBytes`. `[NUM]`
3.8.6 Compressed oops: 4-byte references below ~32 GB heap, 8 above — the heap-size cliff.
      `[NUM]` `[X-REF 06]`
3.8.7 Field reordering by the JVM (longs/doubles first, then ints, then shorts, then bytes, then
      references) and why source order does not determine layout. `[PROVE]` `[RESEARCH]`
3.8.8 False sharing and `@Contended`. `[X-REF 05]`
3.8.9 Worked footprints: `Object` = 16, `Integer` = 16, `Long` = 24, `String("hello")` ≈ 40–48,
      `int[10]` = 56, `Object[10]` = 56, an empty `ArrayList` = 24. `[NUM]` `[PROVE]`
3.8.10 Measuring with JOL: `ClassLayout.parseInstance(x).toPrintable()` and
       `GraphLayout.parseInstance(x).totalSize()`. `[X-REF 06]`
3.8.11 Project Lilliput / compact object headers (`-XX:+UseCompactObjectHeaders`, experimental in
       24, product in 25): headers drop from 12 to 8 bytes and every number above shifts.
       `[RESEARCH]` `[NUM]`
3.8.12 Where an object's fields actually live: heap only; primitives inside the object, references
       pointing out. `[X-REF 06]`
3.8.13 Stack frames, the local variable array, and where a primitive local lives. `[X-REF 06]`

*(13 leaves)*

### §3.9 Exception mechanics

3.9.1 The `Code` attribute's exception table: start PC, end PC, handler PC, catch type — there is
      no runtime cost to entering a `try`. `[SOURCE]` `[BYTECODE]` `[PROVE]`
3.9.2 `athrow` and the handler search up the frame stack. `[PROVE]`
3.9.3 `finally` is compiled by **duplicating** the block into every exit path (plus a synthetic
      `any` handler), which is why a `return` in `finally` swallows the exception. `[BYTECODE]`
      `[PROVE]` `[SOURCE]`
3.9.4 try-with-resources desugaring: the synthetic `$closeResource` / primary-exception local, the
      null check, and the `addSuppressed` call. `[BYTECODE]` `[SOURCE]` `[PROVE]`
3.9.5 Multi-catch compiles to one handler entry per exception type pointing at the same handler.
      `[BYTECODE]`
3.9.6 `Throwable` construction calls `fillInStackTrace`, which walks the stack — cost is
      proportional to depth. `[SOURCE]` `[NUM]` `[PROVE]`
3.9.7 The lazy `backtrace`/`stackTrace` fields: `StackTraceElement[]` is materialised only when
      `getStackTrace`/`printStackTrace` is called. `[SOURCE]` `[RESEARCH]`
3.9.8 The four-argument `Throwable` constructor with `writableStackTrace = false`, and overriding
      `fillInStackTrace` for a stackless exception — roughly an order of magnitude cheaper.
      `[SOURCE]` `[NUM]` `[RESEARCH]` `[BUILD]`
3.9.9 `-XX:-OmitStackTraceInFastThrow`: C2 replaces repeatedly-thrown implicit exceptions with a
      preallocated stackless instance after a threshold, so the trace disappears. Enabled by
      default. `[TRAP]` `[RESEARCH]`
3.9.10 `-XX:MaxJavaStackTraceDepth` (default 1024) truncating long traces. `[NUM]` `[RESEARCH]`
3.9.11 Helpful NPE (JEP 358): computed lazily from the bytecode of the failing instruction; needs
       `-g` for local variable names; on by default since Java 15 via `JDK-8233014`. `[SOURCE]`
       `[RESEARCH]`
3.9.12 The security consideration in JEP 358: NPE messages can leak internal structure into
       user-visible error output. `[RESEARCH]` `[X-REF 13]`
3.9.13 Suppressed exceptions in the trace format (`Suppressed:`) and the `Caused by:` chain, read
       bottom-up. `[TRAP]`
3.9.14 `StackOverflowError`: frame size, `-Xss`, the default stack size, and why the trace is
       truncated and repetitive. `[NUM]` `[X-REF 06]`
3.9.15 Exception performance measured: create+throw+catch at depth 1 versus depth 1000, versus a
       stackless exception, versus a boolean return. `[NUM]` `[PROVE]` `[RESEARCH]`
3.9.16 `StackWalker` with `RETAIN_CLASS_REFERENCE` as the cheap way to inspect a few frames.
       `[RESEARCH]`
3.9.17 JFR's `jdk.ExceptionStatistics` / `jdk.JavaExceptionThrow` events for finding the code
       throwing millions of exceptions you never see. `[RESEARCH]` `[X-REF 20]`

*(17 leaves)*

### §3.10 Enum internals

3.10.1 What `javac` generates for an enum: a `final class X extends Enum<X>` with `public static
       final` constants, a `private static final X[] $VALUES`, and a static initialiser.
       `[SOURCE]` `[BYTECODE]`
3.10.2 `values()` is a generated method returning `$VALUES.clone()` — the allocation per call.
       `[SOURCE]` `[NUM]` `[PROVE]`
3.10.3 `valueOf(String)` delegates to `Enum.valueOf(Class, String)`, which uses a lazily built
       `enumConstantDirectory` map on `Class`. `[SOURCE]` `[RESEARCH]`
3.10.4 An enum with constant bodies becomes an abstract class plus one anonymous subclass per
       constant (`X$1`, `X$2`), so the class is not `final`. `[PROVE]` `[BYTECODE]`
3.10.5 `Enum` fields: `private final String name`, `private final int ordinal`; both `final` and
       both set by the compiler-generated constructor call. `[SOURCE]`
3.10.6 `Enum.equals` and `Enum.hashCode` are `final` and identity-based; `compareTo` is `final` and
       ordinal-based; `clone` throws. `[SOURCE]` `[PROVE]`
3.10.7 Enum serialization is by `name` only and cannot be customised — the specification ignores
       `writeReplace`/`readResolve`/`readObject`. `[SOURCE]` `[RESEARCH]` `[PROVE]`
3.10.8 Reflection cannot construct an enum constant: `Constructor.newInstance` throws
       `IllegalArgumentException` for an enum class. `[PROVE]`
3.10.9 `switch` on an enum generates a synthetic `$SwitchMap$X` int array in a nested holder class,
       mapping `ordinal()` to a dense case index, so that recompiling the enum does not break the
       switch's binary compatibility. `[SOURCE]` `[PROVE]` `[BYTECODE]`
3.10.10 `EnumSet`: `RegularEnumSet` (≤64 constants, one `long` bit vector) and `JumboEnumSet`
        (`long[]`); bulk operations become single bitwise instructions. `[NUM]` `[X-REF 02]`
3.10.11 `EnumMap`: ordinal-indexed `Object[] vals` plus a cached `keyUniverse`, `NULL` sentinel for
        null values, ordinal iteration order. `[NUM]` `[X-REF 02]`
3.10.12 Memory: an enum constant is one object; `EnumSet` of 64 constants is one object with 8
        bytes of payload; `EnumMap` costs 4 bytes per declared constant regardless of occupancy.
        `[NUM]` `[PROVE]`
3.10.13 Adding a constant is source-compatible but can silently change behaviour in a `switch` with
        a `default`, and breaks an exhaustive switch expression at compile time — which is the
        point. `[TRAP]`
3.10.14 Enums across a wire or a database: persist `name()` or an explicit code, never `ordinal()`,
        and handle unknown values on read. `[TRAP]` `[X-REF 08]` `[X-REF 12]`

*(14 leaves)*

### §3.11 Nested class internals

3.11.1 Each nested class is its own class file: `Outer$Inner.class`. `[PROVE]`
3.11.2 The synthetic `final Outer this$0` field and the constructor parameter that sets it.
       `[SOURCE]` `[BYTECODE]`
3.11.3 Captured locals become synthetic constructor parameters and `val$x` fields — the reason
       capture must be effectively final. `[PROVE]` `[BYTECODE]`
3.11.4 Pre-Java-11: private member access across the nest went through synthetic
       package-private `access$000` bridge methods, which widened accessibility and were a real
       (if minor) security surface. `[SOURCE]` `[PROVE]` `[VERSION-TRAP]`
3.11.5 JEP 181 nestmates (Java 11): `NestHost`/`NestMembers` attributes, direct private access, no
       more `access$` bridges. `[RESEARCH]` `[SOURCE]`
3.11.6 `Class.getNestHost`, `getNestMembers`, `isNestmateOf`. `[RESEARCH]`
3.11.7 The retained-heap consequence of `this$0`, measured on a listener held in a static registry.
       `[NUM]` `[PROVE]` `[TRAP]`
3.11.8 Anonymous class naming (`Outer$1`), local class naming (`Outer$1Local`), and how they appear
       in heap dumps and stack traces. `[RESEARCH]`
3.11.9 Lambdas generate no class file at compile time: `invokedynamic` +
       `LambdaMetafactory.metafactory` spins a hidden class at first execution. `[RESEARCH]`
       `[X-REF 04]`
3.11.10 Non-capturing lambdas are cached as a singleton; capturing lambdas allocate per evaluation.
        `[PROVE]` `[NUM]` `[X-REF 04]`
3.11.11 Hidden classes (JEP 371) and why a lambda's class does not appear in the class histogram
        under a normal name. `[RESEARCH]` `[X-REF 06]`
3.11.12 Method references: the four kinds and which allocate. `[X-REF 04]`

*(12 leaves)*

### §3.12 `final` semantics and constant folding

3.12.1 `static final` compile-time constants are copied into the constant pool of every caller —
       shown with two class files and `javap`. `[BYTECODE]` `[PROVE]`
3.12.2 The exact rule for what is a compile-time constant: `static final` of a primitive type or
       `String`, initialised with a constant expression. `[SOURCE]`
3.12.3 The stale-constant binary-compatibility hazard, and how a build system hides it until a
       partial deploy. `[TRAP]` `[PROVE]`
3.12.4 JMM final field semantics: the freeze at the end of the constructor, and the guarantee that
       any thread seeing a reference to a properly constructed object sees its final fields.
       `[PROVE]` `[X-REF 05]`
3.12.5 The escape clause: `this` escaping the constructor voids the guarantee. `[TRAP]`
       `[X-REF 05]`
3.12.6 `@Stable` (JDK-internal) and the JIT's trusting of final field values for constant folding.
       `[RESEARCH]` `[X-REF 06]`
3.12.7 The JIT trusts `static final` fields; it does **not** unconditionally trust instance final
       fields, which is why `final` on an instance field is not automatically a performance win.
       `[TRAP]` `[RESEARCH]`
3.12.8 Mutating a `final` field: reflection with `setAccessible` (historically), `Unsafe`, and
       `VarHandle` — and why serialization and deserialization frameworks need it. `[RESEARCH]`
3.12.9 It no longer works for records, hidden classes, and `java.lang` value-based classes; JEP 500
       proposes to make `final` mean final everywhere, with
       `--illegal-final-field-access` as the transition switch. `[RESEARCH]` `[VERSION-TRAP]`
3.12.10 The consequence for libraries that mutate finals (older Mockito, some ORM and DI tooling)
        and what a migration looks like. `[RESEARCH]` `[X-REF 16]`
3.12.11 `final` on a local or parameter: no bytecode difference at all. `[PROVE]` `[BYTECODE]`

*(11 leaves)*

### §3.13 `hashCode`, identity, and equality internals

3.13.1 Identity hash generation modes (`-XX:hashCode=`), the default in HotSpot, and its storage in
       the mark word. `[RESEARCH]` `[NUM]`
3.13.2 Why identity hash is stable for an object's lifetime even though the object moves during GC.
       `[PROVE]`
3.13.3 `System.identityHashCode` versus an overridden `hashCode`, and `IdentityHashMap`.
       `[X-REF 02]`
3.13.4 The equal⇒equal-hash proof: what breaks in a hash table when it is violated. `[PROVE]`
       `[X-REF 02]`
3.13.5 `Objects.hash` allocates a varargs array; the hand-written `31 * h + f` loop does not.
       `[NUM]` `[X-REF 02]`
3.13.6 Record `hashCode`: `ObjectMethods.bootstrap` builds a `MethodHandle` chain over the
       components; the exact combination is unspecified. `[SOURCE]` `[RESEARCH]` `[TRAP]`
3.13.7 Wrapper `hashCode` implementations, each stated with its formula. `[NUM]` `[X-REF 02]`
3.13.8 Caching a hash in an immutable class, and the `hashIsZero` pattern for the
       legitimately-zero case. `[PROVE]`
3.13.9 Hash-flooding as an attack: `String` collisions, the 2011 `HashMap` DoS, and the mitigations
       that followed. `[RESEARCH]` `[X-REF 02]` `[X-REF 13]`

*(9 leaves)*

### §3.14 `BigDecimal` and `BigInteger` internals

3.14.1 `BigDecimal` fields: `BigInteger intVal`, `int scale`, `int precision`, `String
       stringCache`, and `long intCompact`. `[SOURCE]` `[RESEARCH]`
3.14.2 The compact representation: `intCompact` holds the unscaled value while it fits in a `long`;
       `INFLATED = Long.MIN_VALUE` is the sentinel meaning "look in `intVal`". `[SOURCE]` `[NUM]`
       `[RESEARCH]`
3.14.3 Which constructors produce the compact form and which always inflate
       (`new BigDecimal(BigInteger, int)` always inflates). `[RESEARCH]` `[TRAP]` `[NUM]`
3.14.4 Memory: a compact `BigDecimal` ≈ 40 bytes; an inflated one adds a `BigInteger` (≈ 40 bytes)
       plus its `int[] mag`. `[NUM]` `[PROVE]` `[RESEARCH]`
3.14.5 `new BigDecimal(double)` and the exact 55-digit expansion of 0.1. `[NUM]` `[PROVE]`
3.14.6 `add`/`subtract` need scale alignment first; `multiply` adds scales; `divide` must be told
       the result scale. `[PROVE]` `[NUM]`
3.14.7 `equals` versus `compareTo` at the field level: `equals` compares `intCompact`/`intVal`
       **and** `scale`. `[SOURCE]` `[PROVE]`
3.14.8 `hashCode` includes the scale, which is why `2.0` and `2.00` land in different buckets.
       `[SOURCE]` `[PROVE]`
3.14.9 `stripTrailingZeros` on `100` returns `1E+2`, and `toPlainString` is the fix. `[TRAP]`
       `[NUM]`
3.14.10 `BigInteger`: sign-magnitude `int[] mag`, Karatsuba and Toom-Cook thresholds for
        multiplication, Schönhage–Strassen-free implementation. `[NUM]` `[RESEARCH]`
3.14.11 `BigInteger.valueOf` caches −16..16. `[NUM]` `[RESEARCH]`
3.14.12 Performance versus `long`: order-of-magnitude numbers for add and multiply. `[NUM]`
3.14.13 When to use `long` cents instead, with the overflow bound worked out
        (`Long.MAX_VALUE` cents ≈ 9.2 × 10^16 units). `[NUM]` `[PROVE]`

*(13 leaves)*

### §3.15 Floating point internals

3.15.1 IEEE 754 binary64 layout: 1 sign bit, 11 exponent bits, 52 mantissa bits, implicit leading
       1. `[NUM]` `[PROVE]`
3.15.2 The exact bits of 0.1 and why the nearest double is 0.1000000000000000055511151231257827.
       `[NUM]` `[PROVE]`
3.15.3 `Double.doubleToLongBits` vs `doubleToRawLongBits` — NaN canonicalisation. `[SOURCE]`
       `[TRAP]`
3.15.4 Denormals, `Double.MIN_NORMAL`, `Double.MIN_VALUE`, and the performance cliff on some
       hardware. `[NUM]` `[RESEARCH]`
3.15.5 Infinities, NaN payloads, and the arithmetic rules that produce each.
3.15.6 `Math.ulp` and the spacing of doubles at different magnitudes. `[NUM]` `[PROVE]`
3.15.7 Round-to-nearest-even as the default rounding mode. `[RESEARCH]`
3.15.8 `Double.toString`'s "shortest string that round-trips" contract, and why it prints `0.1`.
       `[PROVE]` `[RESEARCH]`
3.15.9 `strictfp` and JEP 306: before Java 17 the JVM could use x87 80-bit intermediates on some
       platforms; since 17 all FP is strict and the keyword is a no-op. `[VERSION-TRAP]`
       `[RESEARCH]`
3.15.10 `Math` versus `StrictMath`: `Math` may use intrinsics with a documented error bound;
        `StrictMath` is bit-for-bit reproducible via fdlibm. `[RESEARCH]`
3.15.11 `Math.fma` for a single-rounding multiply-add. `[RESEARCH]`
3.15.12 Compensated summation and why `DoubleStream.sum()` differs from a naive loop. `[PROVE]`
        `[RESEARCH]` `[X-REF 04]`
3.15.13 `float` to `double` widening is exact; `double` to `float` narrowing is not. `[PROVE]`
3.15.14 Where floating point is the correct choice (physics, ML, statistics) and where it is not
        (money, counters, identifiers).

*(14 leaves)*

### §3.16 `java.time` internals

3.16.1 `Instant`: `private final long seconds` (from the 1970 epoch) + `private final int nanos`
       (0..999,999,999). `[SOURCE]` `[NUM]` `[RESEARCH]`
3.16.2 `LocalDate`: `int year`, `short month`, `short day` — 24 bytes, no epoch conversion stored.
       `[NUM]` `[RESEARCH]`
3.16.3 `LocalTime`: hour/minute/second/nano as `byte`/`byte`/`byte`/`int`, plus a cached constant
       array for whole hours. `[RESEARCH]` `[NUM]`
3.16.4 `ZonedDateTime` = `LocalDateTime` + `ZoneOffset` + `ZoneId`, and why both the offset and the
       zone are stored. `[PROVE]` `[RESEARCH]`
3.16.5 `ZoneRules`: transition lists, transition rules for future years, and
       `getValidOffsets`/`getTransition` for the gap and overlap cases. `[RESEARCH]`
3.16.6 The tzdb file inside the JDK (`$JAVA_HOME/lib/tzdb.dat`), its version string, and how to
       check it (`ZoneRulesProvider.getVersions`). `[RESEARCH]`
3.16.7 The proleptic ISO calendar, `Chronology`/`ChronoLocalDate`, and why comparing across
       chronologies is a compile-time-invisible bug. `[TRAP]` `[RESEARCH]`
3.16.8 `Temporal`/`TemporalAccessor`/`TemporalField`/`TemporalUnit`/`TemporalAdjuster`/
       `TemporalAmount` — the extension SPI and how `plus(1, ChronoUnit.DAYS)` resolves.
       `[RESEARCH]`
3.16.9 `DateTimeFormatter` immutability: a parsed printer/parser tree built once by
       `DateTimeFormatterBuilder`, hence thread safety by construction. `[PROVE]`
3.16.10 The `java.time` types are `@ValueBased` — do not synchronise on them, do not rely on
        identity, and `==` is never correct. `[TRAP]` `[RESEARCH]`
3.16.11 Instant precision: the underlying clock's resolution (`Clock.systemUTC` uses microsecond
        precision on Java 9+), and the truncation that breaks round-trip equality tests.
        `[TRAP]` `[RESEARCH]` `[X-REF 16]`
3.16.12 Conversion arithmetic: `toEpochMilli` overflow for extreme instants, `Instant.MIN`/`MAX`.
        `[NUM]`
3.16.13 The Java time-scale definition and the deliberate omission of leap seconds. `[RESEARCH]`
3.16.14 Legacy bridging internals: `Date` is a `long` millis wrapper; `Timestamp` extends `Date`
        and breaks `equals` symmetry with it. `[TRAP]` `[PROVE]`

*(14 leaves)*

### §3.17 Version history of the language and core library

3.17.1 Java 1.0–1.4: the language as most of this file describes it; `assert` (1.4), regex (1.4),
       `StringBuffer`, `Vector`, `Hashtable`.
3.17.2 Java 5: generics, enums, autoboxing, varargs, annotations, enhanced for, static import,
       `java.util.concurrent`, `Scanner`, covariant returns, `StringBuilder`.
3.17.3 Java 6: minor library work, `@Override` on interface implementations allowed.
3.17.4 Java 7: diamond, strings in switch, try-with-resources, multi-catch, precise rethrow,
       binary literals and underscores, `Objects`, `invokedynamic`, the string pool moved to the
       heap, `substring` stopped sharing. `[RESEARCH]`
3.17.5 Java 8: lambdas, method references, default and static interface methods, streams,
       `Optional`, `java.time`, repeatable annotations, type annotations, `Base64`,
       `StampedLock`, `LongAdder`, PermGen removed. `[RESEARCH]`
3.17.6 Java 9: modules, `List.of`, private interface methods, compact strings (JEP 254), indified
       concat (JEP 280), `Cleaner`, `StackWalker`, try-with-resources on effectively final,
       `Optional.stream`, diamond with anonymous classes, deprecated wrapper constructors.
       `[RESEARCH]`
3.17.7 Java 10: `var`, `List.copyOf`, `Optional.orElseThrow()`, application CDS.
3.17.8 Java 11 (LTS): `String.isBlank`/`lines`/`strip`/`repeat`, `Files.readString`, HTTP client,
       nestmates (JEP 181), single-file source launch, `Collection.toArray(IntFunction)`,
       removal of Java EE modules. `[RESEARCH]`
3.17.9 Java 12–13: `String.indent`/`transform`, switch expressions (preview), text blocks
       (preview), `Files.mismatch`, `String.hashIsZero` caching detail. `[RESEARCH]`
3.17.10 Java 14: switch expressions final, records preview, helpful NPEs (JEP 358), pattern
        `instanceof` preview, `finalize` further discouraged.
3.17.11 Java 15: text blocks final, sealed preview, helpful NPEs on by default, `String.stripIndent`
        /`translateEscapes`/`formatted`, biased locking deprecated. `[RESEARCH]`
3.17.12 Java 16: records and pattern `instanceof` final, static members in inner classes, strong
        encapsulation by default, wrapper constructors terminally deprecated, `Stream.toList`.
        `[RESEARCH]`
3.17.13 Java 17 (LTS): sealed classes final, always-strict floating point (JEP 306), pseudorandom
        generator interfaces, Security Manager deprecated, `Map.Entry.copyOf`. `[RESEARCH]`
3.17.14 Java 18: UTF-8 by default (JEP 400), finalization deprecated for removal (JEP 421),
        simple web server, `@snippet`. `[RESEARCH]`
3.17.15 Java 19–20: virtual threads and structured concurrency preview, record patterns preview,
        pattern switch preview. `[X-REF 04]`
3.17.16 Java 21 (LTS): virtual threads, record patterns, pattern matching for switch, sequenced
        collections, string templates preview, unnamed patterns/variables preview, the
        `this-escape` lint, generational ZGC. `[RESEARCH]` `[X-REF 04]`
3.17.17 Java 22–23: unnamed variables and patterns final, statements before `super()`
        (preview), primitive types in patterns (preview), `sun.misc.Unsafe` memory access
        deprecated (JEP 471), Class-File API preview, Markdown javadoc. `[RESEARCH]`
3.17.18 Java 24–25: flexible constructor bodies final, Class-File API final, compact object
        headers, scoped values final, Security Manager permanently disabled (JEP 486),
        `synchronized` no longer pinning virtual threads, module import declarations, compact
        source files and instance `main`. `[RESEARCH]` `[X-REF 04]`
3.17.19 Announced-but-not-landed direction relevant to this guide: Valhalla value classes,
        JEP 500 "final means final", lazy static final fields. `[RESEARCH]`
3.17.20 The consolidated "what changed in which release" table, so a claim can be dated.

*(20 leaves)*

### §3.18 Observability for language-level questions

3.18.1 `javap -c -p -v` for every desugaring claim in this part. `[BYTECODE]`
3.18.2 `jshell` for a 10-second experiment (Integer cache, string identity, ternary unboxing).
3.18.3 A decompiler (CFR, Fernflower, Procyon) to see the desugared **source**, and where it lies
       to you by re-sugaring. `[TRAP]`
3.18.4 JOL for object layout and retained size. `[X-REF 06]`
3.18.5 `-verbose:class` and `-Xlog:class+load` to see initialization order and who triggered it.
       `[RESEARCH]` `[X-REF 06]`
3.18.6 `-Xlog:class+init` for the exact `<clinit>` sequence. `[RESEARCH]`
3.18.7 `jcmd VM.system_properties`, `VM.flags`, `GC.class_histogram`. `[X-REF 06]`
3.18.8 `-XX:+PrintFlagsFinal` to confirm `UseCompressedOops`, `AutoBoxCacheMax`,
       `StringTableSize`, `UseCompactObjectHeaders` before trusting any byte arithmetic.
       `[X-REF 06]`
3.18.9 JFR events for exceptions, string deduplication and allocation. `[X-REF 20]`
3.18.10 async-profiler `--alloc` to attribute boxing and string allocation to a call site.
        `[X-REF 06]`
3.18.11 A heap dump plus Eclipse MAT for "who is retaining this enclosing instance". `[X-REF 06]`
3.18.12 Static analysis that catches this file's traps: ErrorProne
        (`ReferenceEquality`, `BoxedPrimitiveEquality`, `BadShiftAmount`, `SelfEquals`),
        SpotBugs, NullAway, SonarQube. `[RESEARCH]`
3.18.13 IDE inspections worth enabling and the ones worth disabling.

*(13 leaves)*

---

**PART 3 total: 257 leaves**

---

## PART 4 — BUILD IT

Every item is `[BUILD]`: complete, compiling, generic Java 21, followed by a
**Diff vs the real one** table covering at minimum edge cases, intrinsics, serialization, null
policy, thread safety, allocation tricks, and why the JDK bothers.

### §4.1 `MyString` — an immutable value type done properly

4.1.1 `final class MyString implements CharSequence, Comparable<MyString>` over a private
      `final char[]`, with a defensive copy in the constructor.
4.1.2 A cached `hash` field with the `hashIsZero` trick, and the proof that lazy caching does not
      break immutability under a data race. `[PROVE]`
4.1.3 `equals`, `hashCode`, `compareTo`, `toString`, `length`, `charAt`, `subSequence`.
4.1.4 A tiny intern pool over a `HashMap`, and the leak it creates without weak keys. `[PROVE]`
4.1.5 A Latin-1/UTF-16 coder field to mirror compact strings, and the byte arithmetic. `[NUM]`
4.1.6 Diff vs `java.lang.String` (intrinsics, `@Stable`, StringTable, `Constable`, serialization,
      the 60+ methods omitted).

*(6 leaves)*

### §4.2 `MyStringBuilder`

4.2.1 `char[] value`, `int count`, capacity 16, growth `2 * old + 2`.
4.2.2 `append` overloads for `String`, `char`, `int`, `Object`, `null`.
4.2.3 `insert`, `delete`, `reverse`, `setLength`, `ensureCapacity`, `trimToSize`, `toString`.
4.2.4 The growth trace for 1,000,000 appends: number of grows and total bytes copied, measured
      against the theoretical amortised bound. `[PROVE]` `[NUM]`
4.2.5 A benchmark of `MyStringBuilder` vs `StringBuilder` vs `+` in a loop vs `+` in one
      expression. `[NUM]`
4.2.6 Diff vs `java.lang.StringBuilder` (compact strings, `ArraysSupport.newLength`,
      `AbstractStringBuilder` sharing with `StringBuffer`, intrinsified `arraycopy`).

*(6 leaves)*

### §4.3 `MyInteger` and a boxing cache

4.3.1 A `valueOf` factory with a static cache array over a configurable range.
4.3.2 A demonstration harness printing `==` results either side of the boundary. `[PROVE]`
4.3.3 A tunable bound read from a system property, mirroring `IntegerCache`.
4.3.4 An allocation count for a boxing loop with the cache on and off. `[NUM]`
4.3.5 Diff vs `java.lang.Integer` (CDS archive, `@IntrinsicCandidate`, `Number`/`Comparable`,
      the parsing and bit-twiddling surface).

*(5 leaves)*

### §4.4 Generic constructs from scratch

4.4.1 `Pair<A,B>` and `Either<L,R>` with correct `equals`/`hashCode`/`toString` and static
      factories.
4.4.2 A `Result<T,E>` type as the checked-exception alternative, with `map`/`flatMap`/`fold`.
4.4.3 `MyOptional<T>`: `of`, `ofNullable`, `empty`, `map`, `flatMap`, `filter`, `orElse`,
      `orElseGet`, `orElseThrow`, `ifPresentOrElse` — and the `orElse` eager-evaluation trap
      demonstrated in code. `[PROVE]`
4.4.4 A typesafe heterogeneous container: `Map<Class<?>, Object>` with `Class.cast`, plus the
      generic-array-and-raw-type hole it must defend against. `[PROVE]`
4.4.5 A generic `Stack<E>` over `(E[]) new Object[]`, with the documented unchecked cast and the
      `ArrayStoreException` demonstration of the alternative. `[PROVE]`
4.4.6 A self-referential generic builder (`<T extends Builder<T>>`) for an immutable value class.
4.4.7 A super type token (`TypeRef<T>`) recovering `List<Foo>` at runtime through
      `getGenericSuperclass`. `[PROVE]`
4.4.8 `copy(List<? super T> dest, List<? extends T> src)` written from scratch, then the same
      method attempted without wildcards to show what fails to compile. `[PROVE]`
4.4.9 A heap-pollution demonstration with generic varargs, and the `@SafeVarargs` fix. `[PROVE]`
4.4.10 Diff table: what the JDK's equivalents (`Optional`, `Map.Entry`, `Collections.copy`) do
       differently and why.

*(10 leaves)*

### §4.5 Enum-shaped builds

4.5.1 The pre-Java-5 typesafe enum pattern: private constructor, public static final instances,
      a private static `VALUES` list, `readResolve` for serialization. `[PROVE]`
4.5.2 A modern enum with a persisted code, a static `Map<String, X>` lookup, and a
      tolerant `fromCode` returning `Optional`.
4.5.3 A strategy enum with per-constant bodies and an interface.
4.5.4 A state machine as an enum with a `transition(Event)` method and an `EnumMap` transition
      table.
4.5.5 An enum-based singleton and the reflection/serialization attacks it defeats, each attempted
      in code. `[PROVE]`
4.5.6 A `values()` caching helper and a benchmark of the allocation it saves. `[NUM]`
4.5.7 Diff vs the compiler's generated enum (`$VALUES`, `$SwitchMap`, `Enum` superclass,
      constructor injection of name and ordinal).

*(7 leaves)*

### §4.6 Exception and resource builds

4.6.1 A domain exception hierarchy with a base class carrying an error code and structured
      context, not a formatted message.
4.6.2 A stackless exception via the four-argument `Throwable` constructor, plus a JMH comparison
      against a normal one at depth 1 and depth 500. `[NUM]` `[PROVE]`
4.6.3 A custom `AutoCloseable` with an idempotent `close()`, used in a try-with-resources with two
      resources, printing the close order and the suppressed exception. `[PROVE]`
4.6.4 The same scenario written with `finally` to show the original exception being destroyed.
      `[PROVE]`
4.6.5 A `CheckedFunction<T,R,E extends Exception>` functional interface plus an `unchecked(...)`
      adapter, so a checked exception can cross a stream boundary. `[X-REF 04]`
4.6.6 A sneaky-throw utility, with a written argument for why it should not be used. `[PROVE]`
4.6.7 A `Cleaner`-based resource holder, written correctly (a static nested `State` runnable that
      does not capture the outer instance) and then incorrectly, with the leak demonstrated.
      `[PROVE]` `[TRAP]`
4.6.8 A `finally`-return demonstration harness that prints the swallowed exception. `[PROVE]`
4.6.9 Diff table: how the JDK's own resource classes handle these cases.

*(9 leaves)*

### §4.7 Value-object and money builds

4.7.1 An immutable `Money` record with `BigDecimal amount` + `Currency currency`, a compact
      constructor enforcing scale, and arithmetic that rejects mixed currencies.
4.7.2 The same in minor units as a `long`, with an overflow-checked `plus`. `[NUM]`
4.7.3 An allocation and precision comparison between the two, plus a rounding-bias experiment
      over 1,000,000 `HALF_UP` versus `HALF_EVEN` roundings. `[PROVE]` `[NUM]`
4.7.4 A mutable-input value class showing the two escape bugs (no copy in, no copy out), then
      fixed. `[PROVE]`
4.7.5 An immutable class with a `List` component built three ways — `List.copyOf`,
      `unmodifiableList` over a copy, and the broken direct assignment. `[PROVE]`
4.7.6 A deep-copy utility for a nested object graph, and a benchmark against a serialization
      round-trip. `[NUM]`
4.7.7 A `Clock`-injected `InvoiceService` plus a `Clock.fixed` test, and the same service written
      untestably with `Instant.now()`. `[X-REF 16]`
4.7.8 Diff table versus what a `record` gives you for free.

*(8 leaves)*

### §4.8 Diagnostic harnesses

4.8.1 A Java Puzzlers-style harness: 15 snippets, each printing something surprising, with the
      mechanism named — `i = i++`, `char + int`, ternary unboxing, `Integer` cache, `long`
      overflow before assignment, `Math.abs(MIN_VALUE)`, `split(".")`, `0.1 + 0.2`,
      `BigDecimal.equals`, `"" + null`, shift masking, compound-assignment narrowing,
      `Math.round(-2.5)`, static hiding, field hiding. `[PROVE]`
4.8.2 A constructor-calls-overridable-method demonstration printing the null field. `[PROVE]`
4.8.3 A class-initialization-order harness printing the exact sequence for a two-level hierarchy.
      `[PROVE]`
4.8.4 A class-initialization deadlock reproduced with two threads. `[PROVE]`
4.8.5 A `static final` constant-inlining demonstration: compile two classes, change one, recompile
      only it, show the stale value. `[PROVE]` `[BYTECODE]`
4.8.6 An inner-class retention demonstration with a heap dump before and after making the class
      `static`. `[NUM]` `[PROVE]`
4.8.7 A pass-by-value harness covering mutate, reassign, swap-attempt and `String`. `[PROVE]`
4.8.8 An overload-resolution harness printing which of `f(int)`/`f(long)`/`f(Integer)`/`f(int...)`
      wins for each argument form. `[PROVE]`
4.8.9 A `SimpleDateFormat` race reproduced with 8 threads, then the `DateTimeFormatter` version
      that does not fail. `[PROVE]`
4.8.10 A DST harness printing the gap and overlap behaviours of `ZonedDateTime` and the
       `Duration`/`Period` divergence. `[PROVE]`

*(10 leaves)*

---

**PART 4 total: 61 leaves**

---

## PART 5 — INTERVIEW AND RETENTION

### §5.1 The questions, with the answer shape

5.1.1 "What is the difference between `==` and `equals`?" — the 30-second and the 5-minute answer.
5.1.2 "Why does `Integer a = 127, b = 127; a == b` print true but 128 print false?"
5.1.3 "Can you change the Integer cache range? What is the lower bound?"
5.1.4 "Why is `String` immutable, and why is it also `final`?"
5.1.5 "Where does the string pool live, and what changed in Java 7?"
5.1.6 "What does `intern()` do, and when would you call it?"
5.1.7 "Is `\"hel\" + \"lo\" == \"hello\"` true? What if one side is a variable? What if it is a
      `final` variable?"
5.1.8 "How is `+` on strings compiled, and what changed in Java 9?"
5.1.9 "Why is string concatenation in a loop O(n²)?"
5.1.10 "How does `String.hashCode` work and why 31?"
5.1.11 "What is compact strings?"
5.1.12 "Explain the `equals`/`hashCode` contract and what breaks when you violate it."
5.1.13 "`getClass()` or `instanceof` in `equals`?"
5.1.14 "What does `final` actually guarantee? Is a `final` list immutable?"
5.1.15 "What happens if you change a `public static final int` and only recompile its class?"
5.1.16 "What is the difference between `final`, `finally` and `finalize`?"
5.1.17 "Why is `finalize` deprecated and what replaces it?"
5.1.18 "Walk me through the exact initialization order of a `new` on a subclass."
5.1.19 "What is wrong with calling an overridable method from a constructor?"
5.1.20 "When is a class initialized? Does reading a constant initialize it?"
5.1.21 "What is `ExceptionInInitializerError` and why does the next call throw
       `NoClassDefFoundError`?"
5.1.22 "`ClassNotFoundException` vs `NoClassDefFoundError`."
5.1.23 "Checked vs unchecked exceptions — which would you use and why?"
5.1.24 "How does try-with-resources work, and what is a suppressed exception?"
5.1.25 "What happens if you `return` inside `finally`?"
5.1.26 "Is `finally` always executed?"
5.1.27 "What does catching `InterruptedException` and ignoring it break?"
5.1.28 "Why do some production NPEs have no stack trace?"
5.1.29 "How expensive is throwing an exception?"
5.1.30 "What is type erasure and what are its consequences?"
5.1.31 "Why can't you do `new T[10]`?"
5.1.32 "Why are generics invariant when arrays are covariant?"
5.1.33 "Explain PECS with a real signature."
5.1.34 "What is a bridge method?"
5.1.35 "What is heap pollution and what does `@SafeVarargs` promise?"
5.1.36 "How does Jackson know the element type of a `List<Foo>` at runtime?"
5.1.37 "Interface with default methods vs abstract class — when do you pick which?"
5.1.38 "Why were default methods added? Resolve a diamond for me."
5.1.39 "Can a default method override `toString`?"
5.1.40 "Static nested vs inner class — which do you use and why?"
5.1.41 "How can an anonymous inner class cause a memory leak?"
5.1.42 "Why must a captured local be effectively final?"
5.1.43 "What is `this` inside a lambda versus inside an anonymous class?"
5.1.44 "Why is an enum the best singleton?"
5.1.45 "What does `values()` actually return, and why should you cache it?"
5.1.46 "Why should you never persist `ordinal()`?"
5.1.47 "What does the compiler generate for an enum, and what is `$SwitchMap`?"
5.1.48 "How do you write a genuinely immutable class? Both defensive copies, please."
5.1.49 "Do records give you immutability?"
5.1.50 "Why is `0.1 + 0.2 != 0.3`?"
5.1.51 "Why is `new BigDecimal(0.1)` wrong?"
5.1.52 "Why is `new BigDecimal(\"2.0\").equals(new BigDecimal(\"2.00\"))` false?"
5.1.53 "How do you store money in Java and in the database?"
5.1.54 "What is `HALF_EVEN` and why does a bank care?"
5.1.55 "Why is `SimpleDateFormat` dangerous?"
5.1.56 "`LocalDateTime` vs `Instant` vs `ZonedDateTime` — what do you store for an event?"
5.1.57 "`Duration.ofDays(1)` vs `Period.ofDays(1)` across DST."
5.1.58 "How do you make time testable?"
5.1.59 "Is Java pass-by-value or pass-by-reference? Prove it."
5.1.60 "Why can't you write a `swap(a, b)` method?"
5.1.61 "What is autoboxing, and where does it bite you?"
5.1.62 "What does `Math.abs(Integer.MIN_VALUE)` return?"
5.1.63 "What does `i = i++` do?"
5.1.64 "Why does `byte b = 10; b += 300;` compile?"
5.1.65 "Why does `short s = 1; s = s + 1;` not compile?"
5.1.66 "Explain overload resolution when both `f(long)` and `f(Integer)` exist."
5.1.67 "Overloading vs overriding — which is resolved when?"
5.1.68 "Are fields polymorphic?"
5.1.69 "What bytecode instruction does an interface call use, and does it matter?"
5.1.70 "What is `invokedynamic` used for in ordinary code you write?"
5.1.71 "How much memory does an `Integer` cost versus an `int`?"
5.1.72 "What is in an object header?"
5.1.73 "How do you serialize safely, and why is Java serialization a security problem?"
5.1.74 "What is `serialVersionUID` for?"
5.1.75 "What does `readResolve` do, and why do enums not need it?"
5.1.76 "What is `strictfp` and is it still meaningful?"
5.1.77 "What is `var` and where can't you use it?"
5.1.78 "What changed in Java 21 that you actually use?"
5.1.79 "How would you find out whether a boxing allocation is happening in a hot loop?"
5.1.80 "Given a stack trace with `Caused by` and `Suppressed`, tell me the sequence of events."

*(80 leaves)*

### §5.2 The trap index

5.2.1 One table of every `**Trap:**` in the file, with the wrong belief, the symptom, and the fix
      — usable as a pre-interview scan.
5.2.2 The version-stale claims table: `strictfp` (no-op since 17), string pool in PermGen
      (moved in 7), `substring` sharing (stopped in 7), `+` compiling to `StringBuilder`
      (invokedynamic since 9), `access$000` bridges (gone since 11), reflection on `final` fields
      (restricted, and JEP 500 pending), default charset (UTF-8 since 18), helpful NPE off by
      default (on since 15), `super()` must be first (relaxed in 25), inner classes cannot have
      static members (relaxed in 16).
5.2.3 The five most expensive real-world mistakes from this guide: `double` for money,
      shared `SimpleDateFormat`, `==` on boxed values or strings from I/O, swallowing
      `InterruptedException`, and `LocalDateTime` stored as an event timestamp.
5.2.4 The five most common interview-losing wrong answers: "Java passes objects by reference",
      "`final` makes it immutable", "checked exceptions are always better", "`String` is immutable
      so `==` is fine", "generics are checked at runtime".

*(4 leaves)*

### §5.3 One-line assertions and drills

5.3.1 The numbers drill: recite every constant with its value (−128..127, 31, 16, `2n+2`,
      `0xCAFEBABE`, class-file 65, 12-byte header, 16-byte `Integer`, 24-byte `Long`, 1231/1237,
      `Integer.MAX_VALUE - 8`, tzdb, 52 mantissa bits, `INFLATED = Long.MIN_VALUE`).
5.3.2 The conversion drill: state the result of 15 conversion/promotion expressions from memory.
5.3.3 The mechanism drill: explain in one sentence each — erasure, bridge method, `$VALUES`,
      `$SwitchMap`, `this$0`, `val$x`, `<clinit>`, `invokedynamic` concat, `IntegerCache`,
      `hashIsZero`, `intCompact`, exception table, `fillInStackTrace`, final field freeze,
      nestmates.
5.3.4 The code-reading drill: ten snippets, say what each prints and why it is not what it looks
      like.
5.3.5 The "which construct" drill: 15 scenarios → the right language feature, one word each.
5.3.6 The traps drill: given a symptom (wrong date under load, NPE with no call on the line,
      `ClassCastException` with no cast, stale constant, empty stack trace), name the mechanism.
5.3.7 Spaced-repetition schedule for this file: day 1 read, day 3 checklist, day 7 numbers and
      conversion drills, day 14 code-reading drill, day 21 build two items from Part 4.
5.3.8 `## Atomic concept checklist` — every existing checklist line from the current guide, plus
      one line per new concept.

*(8 leaves)*

---

**PART 5 total: 92 leaves**

---

## Leaf counts

| Part | Leaves |
|---|---|
| PART 1 — Basics | 291 |
| PART 2 — Intermediate | 232 |
| PART 3 — Under the hood | 257 |
| PART 4 — Build it | 61 |
| PART 5 — Interview & retention | 92 |
| **Total** | **933** |

Leaves carrying `[RESEARCH]`: **131**.
Leaves carrying `[VERSION-TRAP]`: **17**.
Leaves carrying `[PROVE]`: **~120**. `[SOURCE]`: **~60**. `[BYTECODE]`: **~30**.
`[BUILD]`: **61** (all of Part 4, plus 1.18.14, 1.18.17, 1.21.21, 2.3.11, 2.3.15, 2.4.19, 2.5.23,
2.6.3, 2.6.7, 2.6.18, 2.7.2, 2.7.8, 2.7.10, 2.8.4, 2.8.5, 2.10.6, 2.14.1, 2.14.2, 3.6.15, 3.9.8,
3.5.16).

---

# DIAGRAM MANIFEST

**139 diagrams (D-001 … D-139).** Every one must exist as a standalone SVG file in
`src/notes/detailed/03-java-core/diagrams/`, named `D-NNN-short-slug.svg`, embedded at the point
of explanation with a Markdown image reference and a caption carrying the stable id, e.g.
`**D-026** — The IntegerCache on the heap`. Where the `Type` column says `table`, a Markdown
table is the correct rendering and no SVG file is required.

Rules the manifest assumes and you must follow:

- One idea per diagram. Prefer more, smaller diagrams over one dense one.
- Where the `Must show` column asks for *frames*, produce that many clearly separated,
  individually labelled panels inside the one SVG, each captioned with the frame number and what
  changed since the previous frame.
- Every label, constant and value named in `Must show` must be visible as text in the SVG. A
  diagram that omits a named value does not satisfy the manifest.
- Arrows must be directional and labelled where the direction is not obvious.
- Every diagram is drawn on QuizStakes data. Where the `Must show` cell names domain values
  (`CLIENT_BONUS_AVAILABLE`, `AA-801`, a 3.33 stake, a 65-unit deposit), use those exact values.
- Never inline `<svg>` in the Markdown. Never draw with ASCII characters.

## Part 1 diagrams

| # | Diagram | Syllabus leaf | Type | Must show |
|---|---|---|---|---|
| D-001 | Which side of the line decides the behaviour | 1.1.2, 1.1.6 | before-after | One `StakeSplit` source snippet in the middle. Left column "decided by `javac`": overload selection, constant folding, erasure, boxing insertion, string concat call site, definite assignment. Right column "decided by the JVM": virtual dispatch, class initialization, exception handler search, GC, JIT inlining. Each item as a labelled box with an arrow to the source line it governs |
| D-002 | The three normative documents and what each owns | 1.1.3, 1.1.4 | hierarchy | Three root boxes — JLS 21, JVMS 21, API javadoc — each with the questions it answers listed underneath (JLS: conversions ch.5, expressions ch.15, definite assignment ch.16, initialization ch.12, binary compatibility ch.13; JVMS: class file, `<clinit>`, dispatch, verification; javadoc: method contracts, null policy). All 19 JLS chapter numbers and titles visible |
| D-003 | The release train and where 21 sits | 1.1.9, 1.1.10 | timeline | A horizontal axis from Java 8 to Java 25 with a tick every 6 months; LTS releases at 8, 11, 17, 21, 25 drawn as taller marks; the five features this guide flags as version traps pinned to their release (substring copy 7, indy concat 9, nestmates 11, helpful NPE default 15, strictfp no-op 17, UTF-8 default 18) |
| D-004 | Unicode escapes are processed before tokenisation | 1.2.2 | step-sequence, 3 frames | Frame 1: the raw source characters of a line comment about the 14-day coupon window, ending with a backslash-u-000A escape followed by `stake();` — drawn as a character stream, escape shown as six literal characters. Frame 2: the unicode-escape translation pass turning that escape into a real line terminator, before any token exists. Frame 3: the tokeniser now seeing `stake();` as live code outside the comment. Label the pass order "escape translation → line terminators → tokens". Write the escape in the SVG as the six characters, never as an actual newline |
| D-005 | Every integer and floating literal form | 1.2.5–1.2.9 | table | Rows: decimal, hex `0x`, octal leading zero, binary `0b`, `L` suffix, underscore-separated, `d`/`f` suffix, exponent, hex float. Columns: example written as a QuizStakes constant (e.g. `MAX_BONUS = 100`, `RESTRICTION_MASK = 0b0000_1011`), its value in decimal, and the trap if any (`010` is 8; `float rate = 1.1;` does not compile) |
| D-006 | The eight primitives: width, range, default | 1.3.2, 1.3.3, 1.3.19 | table | One row per primitive. Columns: bits, min, max, field default, whether a local gets a default (always "no"), and the QuizStakes use (`long` for `ledgerEntryId`, `int` for a retry count capped at 3, `byte`/`short` only in wire formats, `char` never for money) |
| D-007 | Two's complement and the asymmetric range | 1.3.5, 1.3.21 | step-sequence, 3 frames | Frame 1: a 32-bit box showing `Integer.MIN_VALUE = 0x80000000` and the bit pattern. Frame 2: negation as invert-plus-one applied to it, producing the same bit pattern — the arithmetic written out. Frame 3: `Math.abs(Integer.MIN_VALUE) = -2147483648`. A fourth panel repeats the argument at 8 bits for `(byte) 200 = -56` with the bits `11001000` labelled |
| D-008 | Shift distances are masked | 1.3.11, 1.3.12 | step-sequence, 3 frames | A restriction bit mask `int mask = 1` (bit for `DEPOSIT_BLOCKED`). Frame 1: `mask << 31` with the shift count `31 & 0x1f = 31`. Frame 2: `mask << 32` with `32 & 0x1f = 0`, result unchanged — the mask arithmetic shown. Frame 3: the same for `long` with `& 0x3f`. A side panel: a negative `byte` under `>>> 1` promoted to `int` first, both bit patterns drawn |
| D-009 | IEEE 754 binary64 field layout | 1.3.13, 3.15.1 | memory-layout | A 64-bit strip split 1 / 11 / 52 with sign, exponent (bias 1023), mantissa (implicit leading 1) labelled; the same strip filled in for the value 4.20 (the average stake) with the actual field values written beneath |
| D-010 | NaN and −0.0: the three-way inconsistency | 1.3.15, 1.3.16, 2.4.5 | table | Rows: `x == y`, `Double.compare(x,y)`, `Double.valueOf(x).equals(y)`. Columns: `(NaN, NaN)`, `(0.0, -0.0)`, `(1.0, 1.0)`. Every cell filled with the actual result, and a footnote naming which one a `TreeSet` of bonus amounts uses |
| D-011 | Where each variable kind lives | 1.4.2, 1.4.3, 3.8.13 | memory-layout | A stack frame for `FundsLedger.reserveStake` holding `int attempt`, `Money stake` (a reference), and `this`; the heap holding the `Money` object with its `BigDecimal amount` reference; the class-static area holding `static final BigDecimal MAX_BONUS`. Arrows from every reference slot to its object. Label which arrow crosses a GC boundary |
| D-012 | Definite assignment as a dataflow analysis | 1.5.2, 1.5.3, 1.5.4 | flowchart | A method computing a `StakeSplit`: a blank `final Money bonusPortion;` assigned in an if/else. Two variants side by side — one with an `else`, one without — with each edge annotated "assigned / not assigned" and the merge point marked "definitely assigned" vs "compile error: variable may not have been initialized" |
| D-013 | Shadowing, obscuring, and hiding are three different things | 1.5.5, 1.5.6, 1.5.7 | before-after | Three panels over `Account`/`ShellAccount`. Shadowing: a constructor parameter `limits` hiding the field, `this.limits = limits` drawn as the fix. Obscuring: a local named `Money` hiding the type name. Hiding: `Account.status` and `ShellAccount.status` as two distinct slots in one object, with two reads through an `Account`-typed and a `ShellAccount`-typed reference resolving to different slots |
| D-014 | The order of instance initialisation | 1.5.11, 1.13.6 | step-sequence, 5 frames | `Reservation extends LedgerRecord`. Frame 1: `new Reservation(...)` allocates and zeroes all fields. Frame 2: `super(...)` runs `LedgerRecord`'s field initialisers then its body. Frame 3: `Reservation`'s field initialisers and instance blocks in textual order. Frame 4: `Reservation`'s constructor body. Frame 5: the reference returned. Each frame lists the current value of every field |
| D-015 | Operator precedence and associativity | 1.6.1, 1.2.14 | table | All precedence levels from postfix down to assignment, one row each, with operators, associativity, and one QuizStakes expression per level that would be misread without parentheses |
| D-016 | `i = i++` on the operand stack | 1.6.4, 1.6.5 | step-sequence, 4 frames | `int attempt = 2;` then `attempt = attempt++;`. Frame 1: `iload` pushes 2. Frame 2: `iinc` bumps the local to 3 without touching the stack. Frame 3: `istore` writes the stacked 2 back. Frame 4: final value 2. The `javap -c` listing printed alongside with each instruction matched to its frame |
| D-017 | Compound assignment hides a narrowing cast | 1.6.6, 1.6.7 | before-after | Left: `byte retries = 10; retries += 300;` compiles — expanded to `retries = (byte)(retries + 300)` with the truncated result shown in bits. Right: `retries = retries + 300;` fails to compile, with the error text. A second row does the same for `char` |
| D-018 | The conditional operator computes its own type | 1.6.10, 1.6.11, 1.6.12 | flowchart | Decision nodes for the ternary typing rules; three worked leaves using domain values: `flag ? 0 : nullBonusCount` typed `int` → NPE even when `flag` is true; `true ? Integer.valueOf(1) : Double.valueOf(2.0)` → `1.0`; `flag ? bonus : cash` where both are `Money` → `Money`. Each leaf shows the unboxing/promotion that produced it |
| D-019 | Eleven conversions across six contexts | 1.7.1, 1.7.2 | table | Rows: identity, widening primitive, narrowing primitive, widening reference, narrowing reference, boxing, unboxing, unchecked, capture, string, forbidden. Columns: assignment, strict invocation, loose invocation, variable-arity invocation, string, casting, numeric promotion. Each cell "permitted / not permitted", with the JLS 5.x subsection number |
| D-020 | The widening ladder and its two lossy rungs | 1.7.3, 1.7.4, 3.15.13 | hierarchy | `byte → short → int → long → float → double` and `char → int` as arrows; the `int → float`, `long → float` and `long → double` arrows drawn in a distinct style and labelled "lossy"; a worked value `(float) 16_777_217 == 16777216.0` shown on the `int → float` arrow, and a `ledgerEntryId` of 7,200,000,001 losing precision on `long → float` |
| D-021 | `int` arithmetic overflows before the widening | 1.7.10 | step-sequence, 3 frames | `long window = 24 * 60 * 60 * 1000 * 1000;` for a reservation expiry window. Frame 1: all four multiplications performed in `int`. Frame 2: the wrap point with the actual overflowed `int` value shown. Frame 3: that wrong value widened to `long`. Beside it the fix `24L * 60 * 60 * 1000 * 1000` with the correct value |
| D-022 | Floating-to-integral conversion saturates | 1.7.11, 1.7.12 | table | Rows: a normal value, a value above `Integer.MAX_VALUE`, a value below `Integer.MIN_VALUE`, `NaN`, `+Infinity`, `-Infinity`, `-0.9`. Columns: `(int)`, `(long)`, `Math.round`. Every cell holds the exact result, including `(int) 1e20 = 2147483647` and `(int) Double.NaN = 0` |
| D-023 | `switch` on a `String` is two stages | 1.8.8, 1.10.23 | step-sequence, 3 frames | A switch over the restriction type name `"SELF_EXCLUDED"`. Frame 1: `hashCode()` computed and switched on, with the actual hash value. Frame 2: `equals` confirming the match, because two names could collide. Frame 3: the second switch on the dense index selecting the case body. The `javap -c` listing shown with both `lookupswitch`/`tableswitch` instructions labelled |
| D-024 | Unreachable code: `while (true)` versus `if (true)` | 1.8.16 | before-after | Left: a `while (true)` reservation-expiry loop with a statement after it — compile error, error text quoted. Right: `if (true) { return; }` with a statement after it — compiles, because the rule is deliberately blind to `if`. A note naming conditional compilation as the reason |
| D-025 | The `IntegerCache` on the heap | 1.9.3, 1.9.7, 3.4.2 | memory-layout | The `IntegerCache.cache` array spanning indices 0..255 for values −128..127; two `Integer` references holding a retry count of 127 pointing at the *same* cached object; two references holding 128 pointing at two distinct objects; `low = -128`, the configurable `high`, and `==` results annotated true and false |
| D-026 | Which wrapper caches what | 1.9.6, 3.4.5 | table | One row per wrapper: `Byte`, `Short`, `Integer`, `Long`, `Character`, `Boolean`, `Float`, `Double`. Columns: cached range, number of cached instances, tunable (yes only for `Integer`), and the flag/property name |
| D-027 | Unboxing NPE at a line with no method call | 1.9.9, 1.9.10, 2.11.11 | step-sequence, 3 frames | `int reserved = positionsByType.get(CLIENT_BONUS_RESERVED);` where the key is absent. Frame 1: `get` returns `null`. Frame 2: the compiler-inserted `intValue()` on `null`. Frame 3: the NPE, with the helpful-NPE message text shown. A side panel: `nullInteger == 5` unboxing and throwing, versus `nullInteger == otherInteger` comparing references and not throwing |
| D-028 | `Integer` versus `int` in bulk | 1.9.19, 3.4.10, 3.4.12 | memory-layout | Top: `int[] stakeMinorUnits = new int[2_800_000]` — 16-byte header plus 11.2 MB contiguous. Bottom: `List<Integer>` of the same 2.8M daily stake amounts — a 24-byte list, a 16-byte array header, 11.2 MB of 4-byte references, and 2.8M × 16-byte `Integer` objects. Totals and the ratio written out |
| D-029 | Inside a `String` | 1.10.2, 1.10.19, 3.2.1, 3.2.16 | memory-layout | A `String` holding the status name `"SCREENING_IN_PROGRESS"`: 12-byte header, `value` reference, `hash` int, `coder` byte, `hashIsZero` boolean, padding to 24 bytes; the `byte[]` it points at with a 16-byte header and 21 Latin-1 bytes padded to 40; the total. `COMPACT_STRINGS`, `LATIN1 = 0` and `serialVersionUID = -6849794470754667710L` labelled |
| D-030 | `substring`: copy since 7, shared before | 1.10.18, 3.2.17 | before-after | Left, Java 6: a 4 KB bank-statement line with `substring(0, 8)` sharing the same `char[]` via `offset`/`count`, the whole 4 KB retained. Right, Java 7+: an independent 8-char `byte[]`, the parent collectable. Bytes retained labelled on both. A prominent VERSION TRAP banner |
| D-031 | `split` is a regex, and it eats trailing empties | 1.10.13, 1.10.14 | step-sequence, 3 frames | A bank-deposit reference `"BDP-101.ACME.  "`. Frame 1: `split(".")` returning a zero-length array because `.` matches everything. Frame 2: `split("\\.")` returning the three parts. Frame 3: `split(",", -1)` versus `split(",")` on `"65,,"` showing 3 elements versus 1, with the limit rule written out |
| D-032 | The string pool | 1.11.1–1.11.4, 3.2.13 | memory-layout | The heap with a pool region; two classes both referring to the literal `"AA-801"` pointing at one pooled object; `new String("AA-801")` as a separate object with its own header, and `.intern()` drawn as an arrow back to the pooled instance; `==` results on every pair annotated. A VERSION TRAP note that the pool left PermGen in Java 7 |
| D-033 | Constant folding depends on `final` | 1.11.5, 1.11.6, 1.6.19 | before-after | Left: `final String prefix = "AA-";` then `prefix + "801" == "AA-801"` is true, with the folded literal shown in the constant pool. Right: the same without `final` — an `invokedynamic` concat at runtime and a fresh object, `==` false. The `javap -c` for both |
| D-034 | Equal objects with unequal hashes are unreachable | 1.12.3, 1.12.4, 3.13.4 | step-sequence, 3 frames | A `RestrictionKey(type, source)` used as a map key. Frame 1: `put` computes hash A and lands in a bucket. Frame 2: an equal key computes hash B (because `hashCode` forgot `source`) and probes a different bucket. Frame 3: the entry is present but not found — label "`equals` is never even called" |
| D-035 | `getClass()` versus `instanceof` in `equals` | 1.12.7 | before-after | `Restriction` and a subclass `TimedRestriction` carrying an `expiresAt`. Left panel with `instanceof`: `r.equals(t)` true, `t.equals(r)` false, the asymmetry arrow drawn. Right panel with `getClass()`: both false, symmetric, with the Liskov cost annotated |
| D-036 | `clone()` is shallow | 1.12.12, 2.8.1, 2.8.7 | before-after | A `Movement` holding a `List<LedgerEntry>`. Before: one movement, one list, four entries. After `clone()`: two `Movement` objects pointing at the *same* list object; a mutation through the clone visible through the original. The deep-copy fix drawn beside it |
| D-037 | `finalize` versus `Cleaner` versus `AutoCloseable` | 1.12.15–1.12.17, 2.9.4, 2.9.11 | timeline | Three lanes over one time axis for a `LedgerFileHandle`. `AutoCloseable`: closed deterministically at the end of the try block. `Cleaner`: cleaned after the referent becomes unreachable and the cleaner thread runs — the gap shaded. `finalize`: reachable → finalizable → finalized → collectable, spanning at least two GC cycles, with the resurrection edge drawn |
| D-038 | The full initialization order of a `new` | 1.13.6, 1.13.7 | step-sequence, 6 frames | `new BankWithdrawalTransaction(...)` extending `WithdrawalTransaction`. The six frames: allocation and default-zeroing; superclass field initialisers; superclass constructor body, which calls an overridable `validate()`; the subclass override of `validate()` running with its own fields still null/0 — highlighted; subclass field initialisers and instance blocks; subclass constructor body. Every field's value printed in each frame |
| D-039 | What triggers class initialization | 1.13.9, 1.13.10, 3.6.5, 3.6.6 | decision-tree | Root: "you touched a class". Branches for `new`, `getstatic`/`putstatic` on a non-constant field, `invokestatic`, reflection, subclass initialization, being the main class — each ending in "runs `<clinit>`". A separate branch for reading a `static final` compile-time constant ending in "no initialization: the value was inlined at compile time", with `MAX_BONUS = 100` as the example |
| D-040 | `ExceptionInInitializerError`, then silence | 1.13.13, 3.6.10 | timeline | Three calls to `BonusRules.grantFor(...)`. Call 1: `<clinit>` throws while parsing a coupon-window property → `ExceptionInInitializerError` with the real cause attached. Call 2 and 3: the class is in the erroneous state → `NoClassDefFoundError: Could not initialize class BonusRules`, with no cause. Label where the root cause was visible and where it is gone forever |
| D-041 | Access modifier visibility | 1.14.12, 1.14.13 | table | Rows: `public`, `protected`, package-private, `private`. Columns: same class, same package, subclass in another package, unrelated class in another package, another module without `exports`. Every cell yes/no. A footnote worked on `Restriction`: a subclass in another package may access a `protected` member only through a reference of its own type |
| D-042 | A `static final` constant is copied into every caller | 1.14.7, 3.12.1, 3.12.3 | before-after | Two class files. Before: `BonusRules.MAX_BONUS = 100` and `BonusService` with the literal `100` already baked into its constant pool, shown in `javap -v` output. After: `BonusRules` recompiled with 150, `BonusService` not recompiled — still using 100. Label the deploy scenario that produces it |
| D-043 | Overload resolution in three phases | 1.15.6, 1.15.7, 1.15.8 | flowchart | Candidates `reserve(int)`, `reserve(long)`, `reserve(Integer)`, `reserve(int...)`. Phase 1 (no boxing, no varargs) → picks `reserve(int)` for an `int` argument and `reserve(long)` for an `int` where `reserve(int)` is absent. Phase 2 (boxing allowed) → `reserve(Integer)`. Phase 3 (varargs) → `reserve(int...)`. Each phase box lists which candidates are applicable, and the winner is marked. A side note on `reserve(null)` |
| D-044 | Static hiding versus instance overriding | 1.14.2, 1.15.5 | before-after | `PaymentRail` and `CardRail`, each with a `static String name()` and an instance `String label()`. A `PaymentRail`-typed reference holding a `CardRail`: the static call resolves to `PaymentRail.name()`, the instance call to `CardRail.label()`. Both bytecode instructions (`invokestatic`, `invokevirtual`) labelled |
| D-045 | Fields are not polymorphic | 1.15.12, 3.7.9 | memory-layout | One `CardWithdrawal` object containing both `WithdrawalTransaction.state` and `CardWithdrawal.state` slots; two references of different static types reading the object; each read annotated with the `getfield` constant-pool entry it compiles to and the slot it hits |
| D-046 | The fragile base class | 1.15.15 | step-sequence, 3 frames | A `CountingRestrictionSet extends HashSet<RestrictionKey>` that increments a counter in `add` and in `addAll`. Frame 1: `addAll` of three keys increments by 3. Frame 2: the superclass `addAll` internally calls `add` three times. Frame 3: the count is 6. The forwarding-composition fix drawn beside it |
| D-047 | Interface versus abstract class | 1.16.1, 1.16.11 | table | Rows: multiple inheritance, instance state, constructors, method bodies, allowed member access, fields, instantiation, evolution cost, when to choose. Columns: interface, abstract class, sealed interface + records. The QuizStakes examples: `RestrictionPort` as an interface, `AbstractRailAdapter` as an abstract class, `Verdict` as a sealed hierarchy |
| D-048 | Diamond resolution for default methods | 1.16.5, 1.16.6 | hierarchy | `Auditable` and `Restrictable` both declaring `default String describe()`; `ClientAction` implementing both — the compile error shown, then the fix `Restrictable.super.describe()`. Two further cases drawn: a class method beating an interface default, and a sub-interface beating its super-interface. A note that a default `toString` is rejected outright |
| D-049 | The four nested-class kinds | 1.17.1, 1.17.13 | table | Rows: static nested, inner, local, anonymous, plus lambda for contrast. Columns: enclosing instance held, can declare static members (and the Java 16 change), capture rules, generated class file name, `this` meaning, when it is the right answer, with a QuizStakes example for each (`StakeSplit` calculator as static nested, a `Reservation` iterator as inner, a comparator as a lambda) |
| D-050 | `this$0` keeps the whole enclosing object alive | 1.17.8, 3.11.2, 3.11.7 | memory-layout | A static `NotificationService` listener registry holding one inner-class listener; the synthetic `this$0` arrow from the listener to its enclosing `ProfileService` instance, which retains eight aggregated owner objects. Retained bytes labelled on the whole subgraph, and the same picture after making the class `static` with the retained set reduced to the listener alone |
| D-051 | `this` in a lambda versus an anonymous class | 1.17.9 | before-after | The same `Runnable` body registered from inside `BonusService`, written twice. Left, anonymous class: `this` points at the anonymous instance, and a `this$0` arrow points at `BonusService`. Right, lambda: `this` points directly at the `BonusService` instance and there is no extra object. Both drawn with their arrows and their generated names (`BonusService$1` versus `lambda$register$0`) |
| D-052 | `values()` clones on every call | 1.18.7, 3.10.2 | step-sequence, 3 frames | The `RestrictionType` enum with 10 constants. Frame 1: the `private static final RestrictionType[] $VALUES` array holding the 10 references. Frame 2: `values()` returning `$VALUES.clone()` — a fresh 10-element array, 56 bytes, allocated. Frame 3: 2.8M stake reservations each calling `values()` in a loop, with the total allocation computed; the cached-array and `EnumSet.allOf` fixes beside it |
| D-053 | The `Throwable` hierarchy | 1.20.1, 1.20.4, 1.20.5, 1.20.6 | hierarchy | `Throwable` at the root; `Error` and `Exception`; `RuntimeException` under `Exception`; the checked branch (`IOException`, `SQLException`, `InterruptedException`, `TimeoutException`) and the unchecked branch (`NullPointerException`, `IllegalArgumentException`, `IllegalStateException`, `ClassCastException`, `IndexOutOfBoundsException`, `ArithmeticException`, `UnsupportedOperationException`, `ConcurrentModificationException`, `NumberFormatException`, `ArrayStoreException`); the `Error` branch (`OutOfMemoryError`, `StackOverflowError`, `NoClassDefFoundError`, `LinkageError`, `AssertionError`). The QuizStakes exceptions placed on the unchecked branch |
| D-054 | try-with-resources: close order and suppression | 1.20.12, 1.20.14, 1.20.15 | step-sequence, 4 frames | A `PaymentRunFileWriter` and a `LedgerConnection` opened in one `try`. Frame 1: both opened in declaration order. Frame 2: the body throws `LedgerImbalanceException`. Frame 3: the resources closed in reverse order; the writer's `close()` also throws. Frame 4: the resulting exception — the body's exception primary, the close exception attached under `Suppressed:`. Beside it, the same scenario with a hand-written `finally`, where the primary exception is destroyed |
| D-055 | `return` inside `finally` swallows everything | 1.20.16, 3.9.3 | before-after | A method returning a `StakeSplit`: the `try` computes a value and the `finally` returns a default. Left: the source. Right: the `javap -c` listing with the `finally` block duplicated into the normal-exit path and the synthetic `any` handler, showing the in-flight exception being discarded. Both the returned value and the lost exception named |
| D-056 | Generics are invariant; arrays are covariant | 1.21.9, 1.21.10, 1.22.5 | before-after | Left, arrays: `LedgerEntry[] entries = new CashEntry[2]` accepted at compile time, then `entries[0] = new BonusEntry(...)` throwing `ArrayStoreException` at runtime — the runtime element-type check drawn as a gate. Right, generics: `List<LedgerEntry> l = new ArrayList<CashEntry>()` rejected at compile time. Label "runtime error" versus "compile error" |
| D-057 | PECS on a real signature | 1.21.11–1.21.14, 2.7.3 | flowchart | A box `FundsLedger.post(Collection<? super LedgerEntry> sink, Collection<? extends LedgerEntry> source)`. The `source` arrow labelled PRODUCES — reads give `LedgerEntry`, `add` barred; the `sink` arrow labelled CONSUMES — writes accepted, reads give `Object`. The capture type `capture#1 of ? extends LedgerEntry` named on the rejected `add` |
| D-058 | An array in memory | 1.22.11, 3.8.4 | memory-layout | `LedgerEntry[] batch = new LedgerEntry[10]`: 12-byte object header + 4-byte length + 10 × 4-byte compressed references = 56 bytes, drawn to scale with each region labelled and the total arithmetic written out. Beside it `long[] amounts = new long[10]` at 96 bytes with the same arithmetic |
| D-059 | Varargs allocate an array per call | 1.22.14, 1.22.15 | step-sequence, 3 frames | `void audit(String action, Object... context)` called once per stake reservation. Frame 1: the call site with three arguments. Frame 2: the compiler-synthesised `new Object[]{...}` allocation. Frame 3: 2.8M calls per day, one array each, total bytes computed. A side panel: `audit("x")` receiving a zero-length array, not null, and `audit(null)` selecting the array overload |
| D-060 | Module strong encapsulation | 1.23.6, 1.23.7, 1.23.8 | flowchart | A reflective `setAccessible(true)` call from a serialization library into `com.quizstakes.ledger.internal`. Decision nodes: is the package `exports`ed, is it `opens`ed, is `--add-opens` present. Terminals: success, `IllegalAccessException`, `InaccessibleObjectException`. The `module-info.java` fragment shown, and a VERSION TRAP note that this has been deny-by-default since Java 16/17 |
| D-061 | Retention decides who can see an annotation | 1.24.3, 1.24.4, 1.24.10 | timeline | A `@AuditedTransition` annotation across four stages: source, class file, class loading, runtime reflection. Three lanes for `SOURCE`, `CLASS` (the default) and `RUNTIME`, each ending where the annotation stops existing. A final box: "nothing happens until something reads it" naming the annotation processor and the Spring/Jackson reflective reader |
| D-062 | `nanoTime` versus `currentTimeMillis` | 1.25.5, 2.5.26 | timeline | One axis of real time with an NTP correction jumping the wall clock backwards mid-interval. Two tracks: `currentTimeMillis` showing a negative elapsed time for a card-capture measurement, `nanoTime` showing the correct monotonic elapsed value. Both computed elapsed values written out, and the epoch-meaning column noted for each |
| D-063 | `Math.round`, `floor`, `ceil`, `rint`, truncation | 1.25.7, 1.3.8, 1.3.7 | table | Rows: 2.5, −2.5, 2.4, −2.4, 0.5, −0.5, and the bonus split 0.335. Columns: `(long)` cast, `Math.round`, `Math.floor`, `Math.ceil`, `Math.rint`, `Math.floorDiv`/`floorMod` where integral. Every cell holds the exact result; `Math.round(-2.5) = -2` highlighted |

## Part 2 diagrams

| # | Diagram | Syllabus leaf | Type | Must show |
|---|---|---|---|---|
| D-064 | The master cost table | 2.1.1 | table | One row per operation listed in leaf 2.1.1. Columns: complexity, allocations per call, rough nanoseconds, whether the JIT can eliminate it, and the QuizStakes hot path where it appears (stake reserve at 1,200/sec, settlement burst at 3,400/sec, ledger write at 13,600/sec peak) |
| D-065 | Concatenation in a loop is quadratic | 2.2.1, 3.3.14 | cost-curve | x = number of ledger entries appended to a reconciliation report (10 → 100,000, log scale), y = bytes copied. Two curves: `+=` in a loop growing as n², a single `StringBuilder` growing as n. The crossover annotated; the total bytes copied for a 19.8M-entry day written out for both |
| D-066 | `StringBuilder` growth is `2 × old + 2` | 2.2.3, 3.3.3, 3.3.7 | cost-curve | A step plot of capacity against character count: 16 → 34 → 70 → 142 → 286 → 574 → 1150 …, each step labelled with `newCapacity = oldCapacity + (2 << coder)` routed through `ArraysSupport.newLength` and the resulting value. A table beneath: appending 1,000,000 characters — the number of reallocations and total bytes copied |
| D-067 | Code unit, code point, grapheme cluster | 2.2.20, 2.2.21, 1.3.4 | memory-layout | A client display name containing an emoji and a combining accent. Three aligned rows: UTF-16 code units with `length()` = the count; code points with `codePointCount()` = the count; grapheme clusters with what the user perceives. `charAt` on the surrogate half shown returning an unusable value |
| D-068 | Where encoding actually happens | 2.2.17, 2.2.18, 2.2.19 | before-after | A bank-statement file read as bytes → `new String(bytes, charset)` → an in-memory UTF-16 `String` → `getBytes(charset)` → bytes out. The two conversion points highlighted as the only places a charset matters. Two panels: the no-arg form on Java 17 (platform default, mojibake shown) and on Java 18+ (UTF-8 by default, JEP 400). VERSION TRAP banner |
| D-069 | The five immutability rules | 2.3.1–2.3.5, 2.3.9 | flowchart | A `Movement` value class taken through the five rules in order: final class, private final fields, no mutators, defensive copy of the `List<LedgerEntry>` in, defensive copy or unmodifiable view out. Each rule shown as a gate with the specific bug it closes drawn as an arrow that the gate blocks |
| D-070 | Defensive copy ordering and the TOCTOU window | 2.3.3 | step-sequence, 3 frames | A `PaymentRun` constructor taking a mutable `List<Id> itemIds`. Frame 1: validate-then-copy — an attacker thread mutates the list between the check and the copy, and the invalid item lands in the run. Frame 2: copy-then-validate — the check runs on the private copy. Frame 3: the two field states side by side. Label the correct order explicitly |
| D-071 | Why `double` cannot hold 0.1 | 2.4.1, 2.4.2, 3.15.2 | step-sequence, 3 frames | Frame 1: 0.1 expanded as a repeating binary fraction. Frame 2: the nearest binary64, with the full 0.1000000000000000055511151231257827 expansion and its bit pattern. Frame 3: `0.1 + 0.2` producing 0.30000000000000004, with a bonus-balance framing: 3.1k bonus grants per day accumulating the error |
| D-072 | `BigDecimal` is an unscaled integer plus a scale | 2.4.7, 3.14.1, 3.14.2 | memory-layout | Three `BigDecimal` values from the domain — 3.33 (stake), 0.33 (bonus portion), 100 (bonus cap). For each: `intCompact`, `intVal`, `scale`, `precision`, and the value as `unscaled × 10^(−scale)`. `INFLATED = Long.MIN_VALUE` labelled on the one inflated example, with the `new BigDecimal(BigInteger, int)` path marked as always inflating |
| D-073 | `equals` sees scale; `compareTo` does not | 2.4.11, 2.4.12, 3.14.7, 3.14.8 | before-after | `new BigDecimal("2.0")` and `new BigDecimal("2.00")` with their `intCompact` and `scale` fields drawn. Left: `equals` false, `hashCode` different, both landing in different `HashSet` buckets — the duplicate bonus amount stored twice. Right: `compareTo` zero, so a `TreeSet` stores one. The two collections' contents printed side by side |
| D-074 | `HALF_UP` versus `HALF_EVEN` over a million roundings | 2.4.14 | cost-curve | x = number of bonus-split roundings (0 → 1,000,000), y = cumulative bias in minor units. Two lines: `HALF_UP` drifting steadily upward, `HALF_EVEN` oscillating around zero. The final bias for each written out, and the 3.33-stake split used as the per-operation example |
| D-075 | The `java.time` type map | 2.5.4, 2.5.7 | hierarchy | Three groups: instantaneous (`Instant`, `InstantSource`, `Clock`), local (`LocalDate`, `LocalTime`, `LocalDateTime`, `Year`, `YearMonth`, `MonthDay`), zoned (`ZonedDateTime`, `OffsetDateTime`, `OffsetTime`, `ZoneId`, `ZoneOffset`); amounts (`Duration`, `Period`) shown separately with the time-based/date-based distinction. Each type annotated with the QuizStakes field that uses it (`Movement.postedAt` → `Instant`, client DoB → `LocalDate`, `PaymentRun` window → `ZonedDateTime`) |
| D-076 | Three types, three questions | 2.5.5, 2.5.6, 2.5.11 | table | Rows: `Instant`, `LocalDateTime`, `ZonedDateTime`, `OffsetDateTime`, epoch millis. Columns: identifies a moment, survives a zone change, correct for a stake settlement timestamp, correct for a client date of birth, correct for a scheduled future `PaymentRun`, database column type. Every cell filled |
| D-077 | The DST gap and the DST overlap | 2.5.9, 2.5.10, 3.16.5 | timeline | A local-time axis across a spring-forward and a fall-back transition in `Europe/London`. The gap hour shaded with the documented shift-forward resolution shown for a `PaymentRun` scheduled inside it; the overlap hour shaded with both valid offsets drawn and `withEarlierOffsetAtOverlap`/`withLaterOffsetAtOverlap` selecting between them |
| D-078 | `Duration.ofDays(1)` versus `Period.ofDays(1)` | 2.5.8 | before-after | A bonus granted at 23:00 the night before a spring-forward, expiring "in 1 day". Left: `Duration.ofDays(1)` adds exactly 24 hours and lands at 00:00 local. Right: `Period.ofDays(1)` adds one calendar day and lands at 23:00 local. Both resulting instants and local times written out, and the one-hour divergence labelled |
| D-079 | End-of-month clamping | 2.5.14 | step-sequence, 3 frames | A 30-day bonus expiry computed with `plusMonths(1)` from January 31. Frame 1: the target month has 28 days. Frame 2: the clamp to February 28. Frame 3: `plusMonths(1).plusMonths(1)` versus `plusMonths(2)` giving different answers, both printed |
| D-080 | The `SimpleDateFormat` race | 2.5.2, 2.4.24 | timeline | One shared static `SimpleDateFormat` and eight threads formatting `Movement.postedAt` concurrently at the 3,400/sec settlement burst. The internal `Calendar` field shown being written by thread A and read by thread B; two wrong output strings printed. Beside it the same picture with a `DateTimeFormatter`, immutable, no shared mutable state |
| D-081 | Checked or unchecked | 2.6.1, 2.6.2, 2.6.8 | decision-tree | Root: "can the immediate caller do something about it". Branches to `IllegalArgumentException`, `IllegalStateException`, a domain unchecked exception, a checked exception, and a `Result` type. Every leaf carries a QuizStakes case: an insufficient balance, a restriction block, a PSP timeout, a malformed coupon code, a ledger imbalance |
| D-082 | Exception translation preserves the cause | 2.6.6, 1.20.8, 3.9.13 | step-sequence, 3 frames | A `SQLException` from the ledger schema. Frame 1: caught and wrapped in a domain `LedgerImbalanceException` with the cause passed. Frame 2: wrapped again at the service boundary. Frame 3: the printed trace read bottom-up, showing the `Caused by:` chain and a `Suppressed:` entry from a failed `close()`. The variant that drops the cause shown with the root cause missing |
| D-083 | The reference strength ladder | 2.9.2, 2.9.3 | hierarchy | Strong, soft, weak, phantom as four rungs; for each: when the GC clears it, whether `get()` can return the referent, the `ReferenceQueue` interaction, and the QuizStakes use (agreement-text cache as soft with the note to use a real cache library, a canonicalising map of `RestrictionKey` as weak, a `Cleaner` on a ledger file handle as phantom) |
| D-084 | The `Cleaner` capture trap | 2.9.4 | before-after | Left, broken: a `LedgerFileHandle` registering a lambda that captures `this`, drawn as an arrow from the cleaning action back to the referent, making it permanently reachable and never cleaned. Right, correct: a `static` nested `State` holding only the file descriptor, with no arrow back. Both object graphs drawn |
| D-085 | `readObject` is a constructor that skips your validation | 2.10.5, 2.10.6 | step-sequence, 3 frames | A `StakeSplit` whose compact constructor enforces bonus + cash = stake. Frame 1: normal construction, the invariant checked. Frame 2: a hand-crafted byte stream deserialised through `readObject`, bypassing the constructor and producing 0.34 + 3.00 for a 3.33 stake — money created. Frame 3: the serialization-proxy form, where reconstruction goes through the canonical constructor and the invariant holds |
| D-086 | `orElse` evaluates eagerly | 2.11.4 | before-after | `findActiveBonus(clientId).orElse(computeDefaultBonus())` versus `.orElseGet(this::computeDefaultBonus)`. Both drawn as call sequences with the present-value case highlighted: the eager form still calls `computeDefaultBonus()` and still hits the ledger; the lazy form does not. Call counts over 380k monthly active clients written out |
| D-087 | `getX` versus `getDeclaredX` | 2.12.2, 2.12.3 | table | Rows: `getFields`, `getDeclaredFields`, `getMethods`, `getDeclaredMethods`, `getConstructors`, `getDeclaredConstructors`. Columns: includes private, includes inherited, includes synthetic/bridge, requires `setAccessible`. A second block on the same figure: `getName`, `getSimpleName`, `getCanonicalName`, `getTypeName` for `Movement`, an inner class, `LedgerEntry[]`, and `int[][]` — four rows, four different strings each |
| D-088 | Pass-by-value: mutate, reassign, swap | 2.13.1–2.13.3, 2.13.5 | step-sequence, 4 frames | A caller holding a `Reservation` reference and an `int attempt`. Frame 1: the callee's parameter slot holding a *copy* of the reference, both arrows pointing at one object. Frame 2: mutation through the copy — visible to the caller. Frame 3: reassignment of the parameter — invisible to the caller. Frame 4: an attempted `swap(a, b)` showing only the local slots exchanged. The caller's variables printed after each frame |
| D-089 | Which construct do I reach for | 2.15.1–2.15.10 | decision-tree | Root: what are you modelling. Branches for value type, contract, constant, error signal, number, text, time, copy, nested type. Every leaf a concrete construct with the QuizStakes instance: `Money` as a record, `Verdict` as a sealed interface, `RestrictionType` as an enum, `InsufficientFundsException` as unchecked, minor-unit `long` versus `BigDecimal`, `char[]` for a password, `Instant` for `postedAt`, `List.copyOf` for a copy, a lambda for a comparator |

## Part 3 diagrams

Internals leaves tagged `[SOURCE]`, `[PROVE]` or `[BYTECODE]` almost always need a step-sequence
or before/after picture. The manifest below assigns one to each such cluster; do not skip any.

| # | Diagram | Syllabus leaf | Type | Must show |
|---|---|---|---|---|
| D-090 | The `javac` pipeline | 3.1.1, 3.1.12 | flowchart | Seven boxes: parse, enter, annotation processing, attribute, flow, desugar, generate — each annotated with what it decides for a `StakeSplit` class (syntax tree, symbol table, generated sources, types and overloads, definite assignment and reachability, the desugarings, the class file). A closing box listing what `javac` deliberately does **not** do: no inlining, no loop optimisation, no constant propagation beyond constant expressions |
| D-091 | Inside a class file | 3.1.2, 3.1.3, 3.1.5 | memory-layout | The byte layout of `Movement.class`: magic `0xCAFEBABE`, minor version, major version 65 (Java 21), constant pool count and a few entries (`CONSTANT_Utf8`, `Class`, `String`, `Fieldref`, `Methodref`, `InvokeDynamic`, `MethodHandle`, `Dynamic`), access flags, this/super class, interfaces, fields, methods, attributes. The version table 52/55/61/65 and `UnsupportedClassVersionError` labelled |
| D-092 | The desugaring catalogue | 3.1.6, 3.1.7 | table | One row per desugaring: enhanced for, varargs, boxing, string concat, string switch, enum switch, inner-class capture, lambda, assertion, try-with-resources, record `Object` methods, generic cast insertion, bridge method. Columns: what you wrote, what `javac` emits, the `javap -c` instruction or synthetic member that proves it, and the class-file attribute involved (`Signature`, `BootstrapMethods`, `NestHost`, `Record`, `MethodParameters`) |
| D-093 | Compact strings: one byte per Latin-1 character | 3.2.2, 3.2.3, 3.2.4, 3.2.5 | before-after | The status name `"DOCUMENTS_VERIFIED"` stored two ways. Left, Java 8 `char[]`: 2 bytes per character with the totals. Right, Java 9+ `byte[]` + `coder`: 1 byte per character, `LATIN1 = 0` labelled, with `StringLatin1` named as the delegate. A third panel shows a non-Latin-1 client name forcing `UTF16 = 1` and `StringUTF16`, with the byte count doubling |
| D-094 | `String.hashCode` and the `hashIsZero` flag | 3.2.6, 3.2.7, 1.10.19 | step-sequence, 3 frames | Frame 1: the hash of a short domain string computed digit by digit as `31 * h + c`, with the running total after each character and the identity `31 * i == (i << 5) - i` written out. Frame 2: the `hash` field going from 0 to that value on first call. Frame 3: a string whose hash genuinely is 0, with `hashIsZero = true` (Java 13+) preventing recomputation on every call |
| D-095 | Two different strings, one hash | 3.2.8, 3.13.9 | step-sequence, 2 frames | Frame 1: `"Aa"` and `"BB"` computed side by side, both reaching 2112, arithmetic shown. Frame 2: the doubling family `"AaAa"`, `"BBBB"`, `"AaBB"`, `"BBAa"` as a tree, with the count `2^k` for length `2k` labelled and the hash-flooding attack on a map keyed by client-supplied coupon codes named |
| D-096 | `String.equals`, line by line | 3.2.9, 3.2.10, 1.10.20 | flowchart | The four checks in order: reference identity, `instanceof String`, `coder` equality, then `StringLatin1.equals`/`StringUTF16.equals` on the raw bytes. Each node annotated with the JDK source line it corresponds to and the early-exit it enables. A note on why two strings with different coders can never be equal |
| D-097 | The StringTable and `intern()` | 3.2.11, 3.2.12, 1.11.7 | memory-layout | The native fixed-size hash table with its bucket array; three interned status-code strings placed in buckets; a fourth `intern()` call shown probing and inserting. `-XX:StringTableSize` and `-XX:+PrintStringTableStatistics` labelled as the flags — and the diagram must mark the default value as **to be confirmed against `-XX:+PrintFlagsFinal`**, not asserted. A cost curve inset: intern latency rising as the table becomes undersized |
| D-098 | Deduplication is not interning | 3.2.14, 3.2.15, 1.11.8 | before-after | Left: three distinct `String` objects for the same repeated bank-deposit reference, each with its own `byte[]`. Right, after G1 string deduplication: three `String` objects sharing one `byte[]`. `-XX:+UseStringDeduplication` and `StringDeduplicationAgeThreshold = 3` labelled, the concurrent dedup thread drawn, and the contrast with interning (which collapses the `String` objects themselves) stated on the figure |
| D-099 | `newCapacity` and the coder shift | 3.3.3, 3.3.4, 3.3.5 | step-sequence, 3 frames | A `StringBuilder` building a reconciliation line. Frame 1: capacity 16 in characters, a `byte[16]` at `coder = LATIN1`. Frame 2: growth to `oldLength + (2 << coder)` with the `<< coder` and `>> coder` conversions between characters and bytes shown numerically. Frame 3: appending a non-Latin-1 character inflating the whole buffer to UTF-16 and doubling its byte length, with both totals |
| D-100 | `+` before and after Java 9 | 3.3.9, 3.3.10, 3.3.11, 2.2.2 | before-after | The same one-expression concatenation of a client id and a status code. Left, Java 8: the `javap -c` listing with `new StringBuilder`, three `append` calls and `toString`. Right, Java 9+: a single `invokedynamic` to `StringConcatFactory.makeConcatWithConstants`, the bootstrap method entry in `BootstrapMethods`, and the installed `CallSite` drawn as running once. VERSION TRAP banner |
| D-101 | Indified concat does not fix the loop | 3.3.14, 2.2.1 | step-sequence, 3 frames | A loop appending 19.8M ledger entry ids with `+=`. Frame 1: one `invokedynamic` per iteration. Frame 2: each producing a fresh `String` with a full copy. Frame 3: the total bytes copied, quadratic, computed. The `StringBuilder` alternative's total beside it |
| D-102 | Three ways `IntegerCache` gets filled | 3.4.1–3.4.4, 1.9.4, 1.9.5 | flowchart | Branches from `IntegerCache.<clinit>`: (a) the default −128..127 array built in the static block; (b) `high` raised via `java.lang.Integer.IntegerCache.high` / `-XX:AutoBoxCacheMax`, read through `VM.getSavedProperty`; (c) `CDS.initializeFromArchive(IntegerCache.class)` mapping `archivedCache` instead of constructing. `low = -128` marked as fixed by the JLS on all three paths |
| D-103 | Escape analysis erases a box | 3.4.8, 3.4.9, 2.1.2 | before-after | A method summing 2.8M stake minor units through an `Integer` accumulator. Left, no escape: the box scalar-replaced, zero heap allocation, drawn as fields living in registers. Right, escaping: the same box stored into a `List<Integer>` on the ledger's audit path, one 16-byte object per iteration, total allocation computed |
| D-104 | What erasure emits | 3.5.1, 3.5.2, 1.21.7 | before-after | Source `class Repository<T extends LedgerEntry>` with a `T find(Id)`. Right: the emitted signature `LedgerEntry find(Id)`, the inserted `checkcast` at every call site, and the `Signature` attribute retaining `<T extends LedgerEntry>` for reflection. `javap -v` output for both the method and the attribute |
| D-105 | Why a bridge method exists, and how it throws | 3.5.3, 3.5.4, 3.5.5, 3.5.6 | step-sequence, 3 frames | `class CashEntryStore extends AbstractStore<CashEntry>` overriding `save(CashEntry)`. Frame 1: the synthetic `save(LedgerEntry)` bridge emitted, with `ACC_BRIDGE ACC_SYNTHETIC` in the `javap` output. Frame 2: a raw-typed caller passing a `BonusEntry` through the bridge. Frame 3: the `checkcast` inside the bridge throwing `ClassCastException` with no cast anywhere in the source, and the bridge frame visible in the stack trace |
| D-106 | Heap pollution through generic varargs | 3.5.9, 3.5.10, 1.21.18 | step-sequence, 4 frames | Frame 1: a `@SafeVarargs`-less `List<Money>... batches` parameter and its `Object[]` runtime array. Frame 2: the array widened to `Object[]` and written to. Frame 3: a `List<String>` stored into it. Frame 4: the `ClassCastException` at an unrelated read site. The three conditions for `@SafeVarargs` being honest listed on the figure |
| D-107 | Loading, linking, initialization | 3.6.1, 3.6.2, 3.6.3, 3.6.4 | step-sequence, 3 frames | `BonusRules` taken through the phases. Frame 1: loading — bytes to a `Class` object. Frame 2: linking — verification, preparation (static fields set to defaults, shown as 0/null), resolution. Frame 3: initialization — `<clinit>` running the static initialisers in textual order and overwriting the defaults. `<clinit>` versus `<init>` named, with how each appears in a stack trace |
| D-108 | The class-initialization state machine and its deadlock | 3.6.7, 3.6.8, 3.6.9, 1.13.12 | state-transition | States: unlinked, linked, being-initialized (owner thread recorded), initialized, erroneous. Transitions labelled with the acquiring/releasing of the per-class lock. A second panel: two threads initializing `BonusRules` and `LedgerPositions`, each static initialiser referencing the other, drawn as a cycle with both locks held — the deadlock. A third panel: the single-thread recursive case, where the second entry is allowed through and observes default values |
| D-109 | The five invoke instructions | 3.7.1, 3.7.2, 3.7.3, 1.15.10 | table | Rows: `invokestatic`, `invokespecial`, `invokevirtual`, `invokeinterface`, `invokedynamic`. Columns: what `javac` emits it for, resolution time, dispatch mechanism, a QuizStakes call site that produces it, and the Java-11 nestmate change for private instance methods (VERSION TRAP) |
| D-110 | vtable and itable | 3.7.4, 3.7.5, 1.15.9 | memory-layout | A `CardRail` class with its vtable — an array of method pointers with inherited slots at fixed indices, `invokevirtual` shown as an index into it. Beside it the itable for `PaymentRailPort`, showing the extra indirection `invokeinterface` pays. Both index computations written out |
| D-111 | Monomorphic, bimorphic, megamorphic | 3.7.6, 3.7.7, 1.15.11 | state-transition | One call site `rail.authorise(...)` observed over time. State 1: one receiver type, inline cache hit, inlined and devirtualised. State 2: a second type appears, bimorphic guard. State 3: a third type, megamorphic fallback to a real vtable lookup. The transitions labelled with what the JIT does, and an uncommon-trap deoptimisation edge back from state 1 |
| D-112 | The object header and field reordering | 3.8.1, 3.8.2, 3.8.5, 3.8.7, 3.8.9 | memory-layout | A `LedgerEntry` instance drawn byte by byte: 8-byte mark word, 4-byte compressed class word, then fields reordered by the JVM as longs/doubles, ints, shorts, bytes, references — with the source declaration order shown beside it to make the reordering visible — then padding to the 8-byte alignment. Total size computed. The mark word's contents (identity hash, GC age, locking bits) exploded in a callout |
| D-113 | The exception table costs nothing to enter | 3.9.1, 3.9.2, 3.9.5 | memory-layout | The `Code` attribute of a stake-reservation method with its exception table: rows of start PC, end PC, handler PC, catch type, including two rows from one multi-catch pointing at the same handler. Beside it the instruction stream with the guarded range bracketed, and a note that entering the `try` emits no instruction at all. An `athrow` shown walking frames to find the first matching row |
| D-114 | `finally` is duplicated into every exit path | 3.9.3, 3.9.4, 1.20.16 | before-after | Left: source with a `try` that returns, a `catch`, and a `finally`. Right: the `javap -c` listing with the `finally` body appearing on the normal-return path, the catch path, and the synthetic `any` handler — three copies, each highlighted. A second panel does the same for try-with-resources, showing the synthetic close, the null check, the primary-exception local and the `addSuppressed` call |
| D-115 | `fillInStackTrace` dominates exception cost | 3.9.6, 3.9.7, 3.9.8, 3.9.15 | cost-curve | x = stack depth (1 → 1000), y = nanoseconds to construct-and-throw. Three curves: a normal exception rising with depth, a stackless exception (four-argument `Throwable` constructor, `writableStackTrace = false`) flat, and a boolean return as a baseline. The lazy `backtrace` → `StackTraceElement[]` materialisation marked at the point `getStackTrace` is called. The insufficient-funds path at 1,200 stake reservations/sec named as the case that matters |
| D-116 | Why a production NPE has no stack trace | 3.9.9, 2.6.13 | timeline | One implicit NPE site executed repeatedly. Early throws: full trace. After the C2 threshold: the preallocated stackless instance substituted, trace empty. `-XX:-OmitStackTraceInFastThrow` marked as the diagnostic switch, and the fact that it is on by default stated on the figure |
| D-117 | What `javac` generates for an enum | 3.10.1, 3.10.4, 3.10.5, 3.10.6 | before-after | Left: the `RestrictionSource` enum source with five constants, one carrying a constant-specific body. Right: the generated shape — `class RestrictionSource extends Enum<RestrictionSource>`, five `public static final` fields, `private static final RestrictionSource[] $VALUES`, the `<clinit>`, the compiler-injected `name`/`ordinal` constructor arguments, and `RestrictionSource$1` as the anonymous subclass for the constant body (so the class is not `final`) |
| D-118 | `$SwitchMap` and why it exists | 3.10.9, 1.8.9 | step-sequence, 3 frames | A switch over `RestrictionType`. Frame 1: the synthetic holder class with `int[] $SwitchMap$RestrictionType` built in its `<clinit>`, mapping each `ordinal()` to a dense case index — the actual array contents shown. Frame 2: the `tableswitch` running over the mapped index. Frame 3: a constant reordered in the enum and only the enum recompiled — the map absorbs the change, so the switch stays binary-compatible. The `javap -c` for the switch shown |
| D-119 | `EnumSet` as a bit vector, `EnumMap` as an array | 3.10.10, 3.10.11, 3.10.12, 1.18.11 | memory-layout | A single 64-bit `long` with bit positions labelled by `RestrictionType` ordinal and name; `add(SELF_EXCLUDED)` shown as `elements |= 1L << ordinal`; a union drawn as one `|` instruction with both bit patterns and the result. Beside it an `EnumMap<GateType, Verdict>` as an ordinal-indexed `Object[]` with the `keyUniverse` and the `NULL` sentinel, and the "4 bytes per declared constant regardless of occupancy" arithmetic |
| D-120 | `this$0` and `val$x` in the class file | 3.11.2, 3.11.3, 1.17.10 | before-after | Left: an inner class and a lambda inside `BonusService`, capturing a local `couponCode`. Right: the generated `BonusService$GrantTask` with a synthetic `final BonusService this$0` field, a synthetic `final String val$couponCode` field, and a constructor taking both — the `javap -p` output shown. The copy semantics named as the reason capture must be effectively final |
| D-121 | `access$000` bridges versus nestmates | 3.11.4, 3.11.5, 3.11.6 | before-after | Left, Java 8: an inner class reading a private field of its enclosing class through a synthetic package-private `access$000` method, drawn as the widened access path. Right, Java 11+: `NestHost`/`NestMembers` attributes in both class files and a direct `getfield`, no bridge. `Class.getNestHost`/`getNestMembers`/`isNestmateOf` named. VERSION TRAP banner |
| D-122 | The `final` field freeze | 3.12.4, 3.12.5, 2.3.13 | timeline | Two threads and one `Money` object. Thread A: field writes inside the constructor, then the freeze at the constructor's end, then publication of the reference by a plain write. Thread B: reads the reference and is guaranteed to see the frozen final fields. A second panel: `this` escaping the constructor before the freeze, and thread B observing a zero amount |
| D-123 | `static final` is trusted; instance `final` is not | 3.12.1, 3.12.6, 3.12.7, 3.12.11 | table | Rows: `static final` primitive/`String` constant, `static final` object reference, instance `final` field, `@Stable` field, `final` local, `final` parameter. Columns: inlined into callers at compile time, constant-folded by the JIT, any bytecode difference, mutable by reflection today, affected by JEP 500 |
| D-124 | The identity hash lives in the mark word | 3.13.1, 3.13.2, 3.13.3, 1.12.11 | step-sequence, 3 frames | Frame 1: a fresh object with no identity hash in its mark word. Frame 2: `System.identityHashCode` called — the hash generated and written into the mark word, with the bit fields drawn. Frame 3: the object relocated by GC to a new address, hash unchanged. Label explicitly "not the address", and note the interaction with locking bits |
| D-125 | `intCompact` versus `intVal` | 3.14.2, 3.14.3, 3.14.4 | before-after | Left: a compact `BigDecimal` for a 65-unit deposit — `intCompact = 6500`, `intVal = null`, `scale = 2`, ~40 bytes. Right: an inflated one built via `new BigDecimal(BigInteger, int)` — `intCompact = INFLATED (Long.MIN_VALUE)`, an attached `BigInteger` with its `int[] mag`, total bytes computed. The constructors that inflate listed |
| D-126 | `Math.ulp` and the spacing of doubles | 3.15.6, 3.15.4, 2.4.4 | cost-curve | x = magnitude on a log axis from `Double.MIN_NORMAL` to 1e18, y = `Math.ulp(x)` on a log axis. Points marked at the average stake 4.20, the average card deposit 65, the daily ledger entry count 19.8M, and 7.2B. A callout: a fixed epsilon of 1e-9 is far below the ulp at 7.2B, so the comparison is meaningless there |
| D-127 | The `java.time` field layouts | 3.16.1, 3.16.2, 3.16.3, 3.16.4 | memory-layout | Four objects drawn to scale: `Instant` (`long seconds`, `int nanos` 0..999,999,999), `LocalDate` (`int year`, `short month`, `short day`, 24 bytes), `LocalTime` (`byte`/`byte`/`byte`/`int`), `ZonedDateTime` (a `LocalDateTime` reference, a `ZoneOffset`, a `ZoneId`) with an explanation of why both the offset and the zone are stored |
| D-128 | `ZoneRules` resolves gaps and overlaps | 3.16.5, 3.16.6, 2.5.13 | step-sequence, 3 frames | Frame 1: the transition list for `Europe/London` plus the future-year transition rules, loaded from `$JAVA_HOME/lib/tzdb.dat`. Frame 2: `getValidOffsets` returning zero offsets for a local time inside the spring gap. Frame 3: two offsets for a local time inside the autumn overlap, and which one `ZonedDateTime.of` picks. `ZoneRulesProvider.getVersions()` named as the way to check the tzdb version |
| D-129 | What changed in which release | 3.17.1–3.17.20, 5.2.2 | table | One row per release from Java 5 to Java 25. Columns: language features, core-library changes relevant to this guide, and the version traps introduced or resolved. The ten version-stale claims from leaf 5.2.2 each pinned to their row |

## Part 4 diagrams

| # | Diagram | Syllabus leaf | Type | Must show |
|---|---|---|---|---|
| D-130 | `MyString` field layout versus `java.lang.String` | 4.1.1, 4.1.5, 4.1.6 | before-after | `MyString` with `private final char[] value`, a cached `hash`, a `hashIsZero` flag and a `coder` byte, drawn byte by byte with its total; `java.lang.String` beside it with `@Stable byte[] value`, `coder`, `hash`, `hashIsZero`. Both totals for the same 18-character status name, and the difference attributed |
| D-131 | `MyStringBuilder` growth trace | 4.2.1, 4.2.4, 4.2.5 | cost-curve | Capacity against appended characters for `2 * old + 2`, plotted to 1,000,000; a table under the plot listing every reallocation with its old and new capacity and the bytes copied, and the grand total against the theoretical amortised bound of roughly 2n |
| D-132 | `MyInteger` cache boundary | 4.3.1, 4.3.2, 4.3.4 | before-after | The cache array with a configurable bound; two references at the boundary value pointing at the same object, two just above pointing at distinct objects, `==` results annotated. Allocation counts for a 2.8M-iteration boxing loop with the cache on and off |
| D-133 | `Result<T,E>` versus a checked exception | 4.4.2, 2.6.3 | flowchart | The same `reserveStake` operation modelled twice: as a checked exception crossing a `Function` boundary (blocked, with the four workarounds branching off — wrap, sneaky-throw, custom functional interface, `Result`) and as a `Result<StakeSplit, InsufficientFunds>` composing through `map`/`flatMap`/`fold` |
| D-134 | The enum state machine and its `EnumMap` transition table | 4.5.4 | state-transition | The bonus lifecycle `GRANTED → ACTIVE → CONSUMED / EXPIRED / CLAWED_BACK`, with `CONSUMED → CLAWED_BACK` for the shortfall case, every edge labelled with its event. Beside it the `EnumMap<BonusState, EnumMap<Event, BonusState>>` transition table drawn as a grid with the ordinal-indexed arrays visible |
| D-135 | `Money` two ways | 4.7.1, 4.7.2, 4.7.3, 2.4.18 | before-after | Left: `Money(BigDecimal, Currency)` — object graph, byte total, allocations for one 3.33-stake split. Right: minor-unit `long` — one primitive field, byte total, allocations. Both showing the same 0.33 + 3.00 split, with the `Long.MAX_VALUE` cents overflow bound (~9.2 × 10^16 units) written out on the right |

## Part 5 diagrams

| # | Diagram | Syllabus leaf | Type | Must show |
|---|---|---|---|---|
| D-136 | The trap index | 5.2.1 | table | One row per `**Pitfall:**` in the whole file. Columns: the wrong belief, the symptom in production, the fix, the leaf number. Ordered by part |
| D-137 | The version-stale claims table | 5.2.2 | table | Ten rows, one per stale claim. Columns: what older material says, what is true in Java 21, the release that changed it, the JEP or bug id, and the phrasing an interviewer is likely to use |
| D-138 | The five most expensive real-world mistakes | 5.2.3 | table | Five rows: `double` for money, shared `SimpleDateFormat`, `==` on boxed values or strings from I/O, swallowed `InterruptedException`, `LocalDateTime` as an event timestamp. Columns: the QuizStakes flow it breaks, the observable symptom, the detection method, the fix |
| D-139 | The numbers drill card | 5.3.1 | table | Every constant this file names, one per row, with its value and the mechanism it belongs to: −128..127, 31, 16, `2n + 2`, `0xCAFEBABE`, class-file 65, 12-byte header, 16-byte array header, 16-byte `Integer`, 24-byte `Long`, 1231/1237, `Integer.MAX_VALUE - 8`, 52 mantissa bits, `INFLATED = Long.MIN_VALUE`, `LATIN1 = 0`/`UTF16 = 1`, `StringDeduplicationAgeThreshold = 3`, `BigInteger.valueOf` cache −16..16 |

---

# OUTPUT CONTRACT

## Exact files to write

All under `src/notes/detailed/03-java-core/`. Create the directory and every subdirectory. Write
every file listed. The layout is **subject-major**: one folder per subject, each holding a basics
file, an intermediate file and an internals file where the syllabus has material at that tier.

| File | Syllabus sections |
|---|---|
| `00-index.md` | The reading map, written first: one line per file below with the syllabus sections and leaf ranges it covers, the diagram ids it contains, its status, the target version, and the 933 total |
| `language-substrate/01-basics.md` | §1.1, §1.2 |
| `language-substrate/02-packages-modules-annotations.md` | §1.23, §1.24, §1.25 |
| `language-substrate/03-internals-javac-and-class-file.md` | §3.1 |
| `language-substrate/04-internals-version-history.md` | §3.17 |
| `language-substrate/05-internals-observability.md` | §3.18 |
| `primitives-and-conversions/01-basics.md` | §1.3 |
| `primitives-and-conversions/02-operators-and-expressions.md` | §1.6 |
| `primitives-and-conversions/03-conversions-and-contexts.md` | §1.7 |
| `control-flow/01-basics.md` | §1.8 |
| `wrappers-and-boxing/01-basics.md` | §1.9 |
| `wrappers-and-boxing/03-internals-boxing.md` | §3.4 |
| `strings/01-basics.md` | §1.10, §1.11 |
| `strings/02-performance-and-text.md` | §2.2 |
| `strings/03-internals-string.md` | §3.2 |
| `strings/04-internals-stringbuilder-and-concat.md` | §3.3 |
| `objects-equality-and-lifecycle/01-basics.md` | §1.4, §1.12 |
| `objects-equality-and-lifecycle/02-copying-and-composite-equality.md` | §2.8 |
| `objects-equality-and-lifecycle/03-lifecycle-and-references.md` | §2.9 |
| `objects-equality-and-lifecycle/04-internals-hashcode-and-identity.md` | §3.13 |
| `objects-equality-and-lifecycle/05-internals-object-layout.md` | §3.8 |
| `classes-and-initialization/01-basics.md` | §1.5, §1.13 |
| `classes-and-initialization/02-modifiers.md` | §1.14 |
| `classes-and-initialization/03-internals-class-loading-and-init.md` | §3.6 |
| `classes-and-initialization/04-internals-final-and-constant-folding.md` | §3.12 |
| `inheritance-and-dispatch/01-basics.md` | §1.15, §1.16 |
| `inheritance-and-dispatch/02-nested-classes.md` | §1.17 |
| `inheritance-and-dispatch/03-internals-dispatch.md` | §3.7 |
| `inheritance-and-dispatch/04-internals-nested-classes.md` | §3.11 |
| `enums/01-basics.md` | §1.18 |
| `enums/03-internals-enums.md` | §3.10 |
| `records-and-sealed/01-basics.md` | §1.19 |
| `exceptions/01-basics.md` | §1.20 |
| `exceptions/02-in-practice.md` | §2.6 |
| `exceptions/03-internals-exception-mechanics.md` | §3.9 |
| `generics/01-basics.md` | §1.21 |
| `generics/02-in-anger.md` | §2.7 |
| `generics/03-internals-erasure.md` | §3.5 |
| `arrays/01-basics.md` | §1.22 |
| `cost-model/02-master-cost-table.md` | §2.1 |
| `immutability-and-design/02-immutability.md` | §2.3 |
| `immutability-and-design/03-pass-by-value.md` | §2.13 |
| `immutability-and-design/04-design-idioms.md` | §2.14 |
| `immutability-and-design/05-which-construct.md` | §2.15 |
| `numbers-and-money/02-numbers-and-money.md` | §2.4 |
| `numbers-and-money/03-internals-bigdecimal.md` | §3.14 |
| `numbers-and-money/04-internals-floating-point.md` | §3.15 |
| `date-and-time/02-date-and-time.md` | §2.5 |
| `date-and-time/03-internals-java-time.md` | §3.16 |
| `serialization/02-serialization.md` | §2.10 |
| `null-discipline/02-null-discipline.md` | §2.11 |
| `reflection/02-reflection.md` | §2.12 |
| `build-it/01-mystring-and-mystringbuilder.md` | §4.1, §4.2 |
| `build-it/02-myinteger-and-generics.md` | §4.3, §4.4 |
| `build-it/03-enums-exceptions-resources.md` | §4.5, §4.6 |
| `build-it/04-value-objects-and-money.md` | §4.7 |
| `build-it/05-diagnostic-harnesses.md` | §4.8 |
| `90-interview-basics.md` | **Part 1's wrap-up**: the summary table over §1.1–§1.25, 10 interview Q&As with full spoken-length model answers, 5 predict-the-output puzzles |
| `91-interview-intermediate.md` | **Part 2's wrap-up**: the summary table over §2.1–§2.15, 10 Q&As, 5 puzzles |
| `92-interview-internals.md` | **Part 3's wrap-up**: the summary table over §3.1–§3.18, 10 Q&As, 5 puzzles |
| `93-interview-build-it.md` | **Part 4's wrap-up**: the summary table over §4.1–§4.8, 10 Q&As, 5 puzzles |
| `94-interview-questions-and-drills.md` | §5.1 all 80 questions with answer shapes, §5.2 the trap index and version-stale table, §5.3 the drills. **Ends with Part 5's own summary table, 10 Q&As and 5 puzzles, then the file-set-wide flat `## Atomic concept checklist`** |

Diagrams go in `src/notes/detailed/03-java-core/diagrams/`, flat, named `D-NNN-short-slug.svg`.

If any single file becomes unwieldy, **split it further** (`03-internals-string-a.md`,
`03-internals-string-b.md`, …) and register the new files in `00-index.md`. Splitting is always
preferred to cutting content. Never merge files to reduce the count.

## Required header on every file except `00-index.md`

```
# 03 Java Core — <subject> — <tier> (<syllabus sections covered>)

**Target version: Java 21 LTS.** | **Part <n> of 5** | [Index](../00-index.md)
Previous: [<title>](<relative path>) · Next: [<title>](<relative path>)
```

Files at the topic root (`90`–`94`) link the index as `[Index](00-index.md)`.

## Required footer on every file except `00-index.md`

```
---

**Leaves covered:** <explicit list or ranges, e.g. 1.10.1–1.10.24, 1.11.1–1.11.9> (<count> leaves)
**Leaves deferred:** <none | leaf number + one-line reason each>
**Diagrams included:** <D-029, D-030, …>
**Target version:** Java 21 LTS
```

---

# SELF-VERIFY BEFORE REPORTING DONE

Run this checklist against your own output. Do not report completion until every box is genuinely
satisfied.

**Coverage**
- [ ] All 933 syllabus leaves appear in the notes, or are listed in a `## Deferred` block with a reason.
- [ ] Every file's footer lists the leaves it covers, and the union across all files is all 933.
- [ ] Every file listed in the OUTPUT CONTRACT exists, with the required header and footer.
- [ ] `00-index.md` lists every file, its syllabus sections, its leaf ranges and its diagram ids.

**Format**
- [ ] Every note file is Markdown (`.md`).
- [ ] No file was cut short for length. No "and so on", no "similar to the above", no deferred-for-space.
- [ ] No ASCII art anywhere. No inline `<svg>` anywhere.
- [ ] All 139 manifest diagrams exist as standalone `.svg` files in `diagrams/`, named `D-NNN-short-slug.svg`, each embedded with a Markdown image reference and captioned with its `D-NNN` id.
- [ ] Every SVG shows every element named in its `Must show` cell, has an explicit `viewBox`, no text below 11px, no external font or CSS dependency, and explicit contrasting fills so it reads on light and dark backgrounds.
- [ ] Where the manifest specified a frame count, that many labelled panels exist.
- [ ] Where the manifest says `table`, a Markdown table was used and no SVG was written.
- [ ] Every comparison of three or more things is a table.
- [ ] No emojis. No filler openers.

**Domain**
- [ ] Every example uses QuizStakes entities, status codes and numbers, taken verbatim from `# CONTEXT`.
- [ ] No `Dog`/`Animal`/`Foo`/`Bar`/`thread1`/`Person`/`Employee` anywhere.
- [ ] No invented status code, position name, service name or volume figure.

**Per concept**
- [ ] Every concept follows `Concept → Why it exists → How it works → SVG → Code → Gotcha`, in that order, with any inapplicable link explicitly noted in one line rather than dropped.
- [ ] Every Java snippet is complete and compiles as written, minus only imports, package declarations and pointless `main` scaffolding. No `...`, no "implementation omitted", no pseudo-code.
- [ ] All code is Java 21 idiomatic.
- [ ] Only the three callout markers `**Pitfall:**`, `**Insight:**`, `**Interview:**` are used.
- [ ] Every `[TRAP]` leaf carries a `**Pitfall:**` with wrong belief, symptom and fix.
- [ ] Every `[PROVE]` leaf has the argument worked through, not asserted.
- [ ] Every `[SOURCE]` leaf quotes real JDK source or spec text and explains every quoted line.
- [ ] Every `[BYTECODE]` leaf shows `javap -c` output read instruction by instruction.
- [ ] Every `[NUM]` leaf states the arithmetic explicitly.
- [ ] Every `[BUILD]` leaf ships complete generic compiling code, and every Part 4 item carries a "Diff vs the real one" table covering edge cases, intrinsics, serialization, null policy, thread safety, allocation tricks, and why the JDK bothers.
- [ ] All 131 `[RESEARCH]` leaves were re-verified against a primary source, or the uncertainty is stated in the text.
- [ ] All 17 `[VERSION-TRAP]` leaves state both what is true in 21 and what used to be true.
- [ ] `-XX:StringTableSize` (3.2.11), `-XX:MaxJavaStackTraceDepth` (3.9.10) and the *Effective Java* item numbers (2.14.11) were confirmed before any number was printed, or are explicitly marked unverified.
- [ ] Every `[X-REF nn]` leaf has a self-contained mechanism paragraph before the pointer.
- [ ] Version differences across Java 7 / 8 / 9+ / 21 are called out inline at the point of each claim.

**Per part**
- [ ] `90-interview-basics.md` ends Part 1 with a summary table, 10 Q&As with full spoken-length model answers, and 5 predict-the-output puzzles with actual output and explanation.
- [ ] `91-interview-intermediate.md` does the same for Part 2.
- [ ] `92-interview-internals.md` does the same for Part 3.
- [ ] `93-interview-build-it.md` does the same for Part 4.
- [ ] `94-interview-questions-and-drills.md` does the same for Part 5, and answers all 80 questions of §5.1 with the answer shape, not a hint.

**Closing**
- [ ] `94-interview-questions-and-drills.md` ends with a flat `## Atomic concept checklist`, one bullet per distinct concept across all five parts, no nesting, no headings inside it.

---

# REFERENCES

Primary sources this topic is built on. Do not invent additional URLs; if you need a fact not
covered here, verify it against the JDK 21 source, the JLS/JVMS or the javadoc and cite that.

**Specifications**

- https://docs.oracle.com/javase/specs/jls/se21/html/index.html — JLS 21, all 19 chapters; the map used for §1.1.4 and for locating conversions (ch. 5), definite assignment (ch. 16), expressions (ch. 15), execution and initialization (ch. 12), binary compatibility (ch. 13)
- https://docs.oracle.com/javase/specs/jls/se21/html/jls-5.html — the eleven conversion kinds and the six conversion contexts, verbatim structure for §1.7.1–1.7.2
- https://docs.oracle.com/javase/8/docs/platform/serialization/spec/input.html — the exact magic-method signatures and the statement that enum serialization ignores `writeReplace`/`readResolve`/`readObject`

**JDK 21 source (`jdk-21+35` tag)**

Browse at `https://raw.githubusercontent.com/openjdk/jdk/jdk-21%2B35/src/java.base/share/classes/<path>`.

- `java/lang/String.java` — `@Stable byte[] value`, `byte coder`, `int hash`, `boolean hashIsZero`, `COMPACT_STRINGS`, `serialVersionUID = -6849794470754667710L`, and the `hashCode`/`equals`/`compareTo` bodies quoted in §3.2.6–3.2.10
- `java/lang/Integer.java` — `IntegerCache` with `low = -128`, the configurable `high`, the `java.lang.Integer.IntegerCache.high` property, `CDS.initializeFromArchive`/`archivedCache`, `hashCode` returning the value, the unsigned and bit-twiddling surface
- `java/lang/AbstractStringBuilder.java` — `value`/`coder`/`count`/`maybeLatin1`/`EMPTYVALUE`, `ensureCapacityInternal`, and `newCapacity` delegating to `ArraysSupport.newLength(oldLength, growth, oldLength + (2 << coder))`
- `java/lang/Throwable.java` — `fillInStackTrace`, the lazy `backtrace`/`stackTrace` fields, the four-argument protected constructor with `writableStackTrace`
- `java/lang/Enum.java` — `private final String name`, `private final int ordinal`, the `final` `equals`/`hashCode`/`compareTo`, the throwing `clone`, and `Enum.valueOf` via `enumConstantDirectory`
- `java/math/BigDecimal.java` — `intVal`, `scale`, `precision`, `stringCache`, `intCompact`, `INFLATED = Long.MIN_VALUE`, and the `equals`/`hashCode` scale sensitivity
- `java/time/Instant.java`, `java/time/LocalDate.java`, `java/time/ZonedDateTime.java` — the field layouts quoted in §3.16.1–3.16.4

**JEPs**

- https://openjdk.org/jeps/254 — compact strings: `byte[]` + `coder`, LATIN1/UTF16, `StringLatin1`/`StringUTF16`
- https://openjdk.org/jeps/280 — indified string concatenation: `makeConcatWithConstants`, the `CallSite`, the strategies
- https://openjdk.org/jeps/192 — G1 string deduplication, `-XX:+UseStringDeduplication`, `StringDeduplicationAgeThreshold`
- https://openjdk.org/jeps/358 — helpful NullPointerExceptions, and https://bugs.openjdk.org/browse/JDK-8233014 for the default-on change in JDK 15
- https://openjdk.org/jeps/181 — nestmates: `NestHost`/`NestMembers`, the elimination of `access$000`
- https://openjdk.org/jeps/306 — always-strict floating point; `strictfp` as a no-op since Java 17
- https://openjdk.org/jeps/421 — finalization deprecated for removal, `--finalization=disabled`, the `Cleaner`/`PhantomReference`/`AutoCloseable` replacements
- https://openjdk.org/jeps/290 — serialization filters and `ObjectInputFilter`
- https://openjdk.org/jeps/400 — UTF-8 by default
- https://openjdk.org/jeps/500 — "Prepare to Make Final Mean Final", `--illegal-final-field-access`
- https://openjdk.org/jeps/471 — `sun.misc.Unsafe` memory-access deprecation

**Javadoc and migration notes**

- https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/lang/package-summary.html — the complete `java.lang` inventory used for §1.25
- https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/time/package-summary.html — the full `java.time` type list including `InstantSource`, `MonthDay`, `YearMonth`, `OffsetTime`, and the design principles
- https://docs.oracle.com/en/java/javase/24/migrate/significant-changes-jdk-24.html — the integrity-by-default direction

**Measurement and analysis**

- https://shipilev.net/jvm/objects-inside-out/ — 12-byte header, 16-byte array header, 8-byte alignment, `Integer` 16 B, `Long` 24 B, compressed oops
- https://shipilev.net/jvm/anatomy-quarks/10-string-intern/ — the StringTable as a fixed-size native hash table and the intern cost curve
- https://shipilev.net/blog/2014/exceptional-performance/ — `fillInStackTrace` dominating exception cost and the stackless-exception comparison
- https://shipilev.net/blog/2015/black-magic-method-dispatch/ — the five invoke instructions, vtable/itable, inline caches, and the measured cost of each dispatch shape
- https://wiki.sei.cmu.edu/confluence/spaces/java/pages/88487756/DCL00-J.+Prevent+class+initialization+cycles — initialization cycles observing default values
- https://wiki.sei.cmu.edu/confluence/spaces/java/pages/88487795/DCL57-J.+Avoid+ambiguous+overloading+of+variable+arity+methods — the three-phase applicability algorithm and varargs ordering
- https://dev.java/learn/generics/type-erasure/ — bound substitution, cast insertion, bridge emission
- http://www.javapuzzlers.com/java-puzzlers-sampler.pdf — the trap taxonomy behind §4.8.1 and much of §1.6

**Not available at syllabus time**

The *Effective Java* table of contents could not be retrieved in full, so the item-number mapping
at leaf 2.14.11 must be verified against the book before any item number is printed; name the item
by its title if you cannot verify the number.

