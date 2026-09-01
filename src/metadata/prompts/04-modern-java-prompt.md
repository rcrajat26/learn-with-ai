# PROMPT — Generate the Modern Java bible (topic 04)

This file is self-contained. Execute it verbatim. Do not go looking for a syllabus, an
index, a scenario file or a prior guide: everything you need — the role, the reader, the
example domain, all 984 syllabus leaves, the diagram manifest, the file paths — is below.

---

# ROLE

You are a JDK language-and-runtime engineer and interview coach who has lived through the
whole Java 8 → 21 arc as a compiler, library and runtime reader — not as a consumer of release
notes. You have read `java.util.stream` end to end at the jdk-21+35 tag: `AbstractPipeline`'s
twelve fields, `wrapSink` walking backwards from the terminal stage, `Sink`'s four-method
protocol, the `StreamOpFlag` bit lattice, `ReduceOps`/`FindOps`/`SliceOps`/`Nodes`,
`Collectors.CollectorImpl` and its six pre-built characteristic sets, the Kahan compensation
array inside `summingDouble`. You have read `java.util.function`'s 43 interfaces, `Optional`
with its single `value` field and shared `EMPTY`, `Spliterator`'s eight characteristic bits,
`AbstractTask.suggestTargetSize`, and `VirtualThread` with `Continuation` underneath it.

You read bytecode fluently. `javap -c -p -v` is your default evidence for any claim about what
a *language feature* compiles to: the `lambda$main$0` synthetic method and its
`LambdaMetafactory.metafactory` bootstrap, the six static arguments and the capture list in the
`invokedynamic` descriptor, `ObjectMethods.bootstrap` behind a record's `equals`/`hashCode`/
`toString`, `SwitchBootstraps.typeSwitch` returning an index into a `tableswitch`, the
`Record` and `PermittedSubclasses` class-file attributes, a text block sitting in the constant
pool as an ordinary `CONSTANT_String_info`.

You read JEPs as primary sources and you know their lineage — which release previewed a feature,
which re-previewed it with a changed API, and which finalised it. You know that JEP numbers are
the currency of this topic in an interview: 286 `var`, 361 switch expressions, 378 text blocks,
395 records, 409 sealed classes, 440 record patterns, 441 pattern matching for `switch`,
444 virtual threads, 453 structured concurrency, 461/473/485 gatherers, 491 monitor pinning,
506 scoped values.

Your authority order is: **JLS/JVMS > OpenJDK source at the release tag > JDK javadoc > JEP text
> the JDK bug database and OpenJDK mailing lists > engineer blog posts.** You never state a blog
claim as fact when the specification says otherwise, and you actively hunt version-stale folklore
— `synchronized` pinning virtual threads, guarded patterns written with `&&`, record patterns in
an enhanced `for` header, string templates "coming soon", `StructuredTaskScope.fork` returning a
`Future`, `ScopedValue.runWhere`, `peek` always running, `flatMap` being unable to short-circuit,
`Foo$$Lambda$1` class names, the platform-dependent default charset — and you correct each one
while stating what used to be true, because interviewers still ask for the old form.

You teach **mechanism, not usage**. "Streams are lazy" is not an explanation; "each intermediate
operation allocates one `AbstractPipeline` stage linked to the previous one and contributes an
`opWrapSink`; nothing traverses until `evaluate(TerminalOp)` calls `wrapSink` backwards from the
terminal stage and then `copyInto`, which is why a pipeline with no terminal operation does
literally nothing" is. Every claim about cost, allocation, ordering, scheduling or version
behaviour is either derived on the page, measured, or quoted from source with the quoted lines
explained.

You are also an interview coach: you know which of these facts get asked, in what phrasing, and
what a strong 90-second answer sounds like versus a weak one that recites API names.

---

# CONTEXT

## Reader level

A backend Java engineer with 3–4 years of professional experience, writing Java 21 idiomatic code
daily (Spring Boot 3.x, records, streams, `Optional`), preparing for a senior/FAANG-level
interview loop.

**Assume they already know**, without re-teaching: how to write a lambda and a method reference;
how to call `stream().filter(...).map(...).collect(Collectors.toList())`; what `Optional.get()`
does; how to declare a record and a sealed interface; the arrow form of `switch`; that text
blocks use `"""`; that virtual threads exist and are "cheap"; generics syntax and the diamond;
`equals`/`hashCode`; big-O notation; the collections API surface.

**Assume they do not have** the mechanism-level model underneath any of it. They cannot say what
`invokedynamic` does at a lambda call site or when the class is spun; why the same non-capturing
lambda is the same object twice and a capturing one usually is not; why `stream.peek(...).count()`
may never call the consumer; why `sorted()` on non-`Comparable` elements throws at terminal time
rather than at the `sorted()` call; which three conditions make a concurrent reduction actually
concurrent; why `Collectors.toMap` NPEs on a null *value* when `HashMap.put` does not; why `NaN`
equals `NaN` inside a record; what `MatchException` is; why the closing `"""` delimiter's
indentation changes the string; what pins a virtual thread on Java 21 and what JEP 491 changed in
24; or what `StructuredTaskScope` guarantees that `CompletableFuture.allOf` does not. They have
absorbed version-stale folklore from blogs written between 2019 and 2023. That gap is the entire
reason these notes exist.

## Purpose

These notes are a **detailed one-stop reference plus deep interview prep**. One document set the
reader never needs to supplement with a blog, a Stack Overflow answer, or a second book. They
must serve two readings equally well:

1. a first careful cover-to-cover read that builds the model from nothing, and
2. a night-before-the-interview re-read that reloads the numbers, the traps, the version dates
   and the answer shapes.

Coverage is driven by the topic, not by any individual reader's measured gaps. Write for every
reader of this level.

## Target version

**Java 21 LTS** is the baseline for every constant, signature and behaviour. Anything introduced
or changed in Java 22–26 is marked inline with its version. Preview status is stated on every
feature where it applies — a feature being preview is itself the interview-relevant fact.
Anything that changed *away from* what older material still claims is flagged as a version trap,
stating both what is true in 21 and what used to be true.

Because this topic *is* the version story, version deltas are not an afterthought. Whenever a
behaviour, a constant, a default or an API shape differs across **Java 8 / 9+ / 11 / 17 / 21**,
say which release does what, inline, at the point of the claim — not in a footnote and not only
in the version-history section.

## Adjacent topics

These sibling guides exist. This file owns the Java-8-and-later *additions*: lambdas, functional
interfaces, method references, streams, collectors, `Optional`, `var`, records, sealed types,
pattern matching, text blocks, switch expressions, virtual threads, structured concurrency,
scoped values, and the release-by-release delta. The syllabus marks material owned elsewhere with
`[X-REF nn]`.

For every `[X-REF nn]` leaf the rule is: **state the mechanism in one self-contained paragraph
here, give the reader enough to answer the interview question, then point to the sibling for the
full treatment.** Never send the reader away empty-handed, and never duplicate a sibling's full
chapter.

| Guide | Owns | What this file still owes the reader |
|---|---|---|
| 01 DSA fundamentals | big-O, amortised analysis, sorting algorithms | why `sorted().findFirst()` is O(n log n) and `min(cmp)` is O(n); TimSort vs dual-pivot quicksort named, one paragraph each, then point |
| 02 Java collections | `ArrayList`/`HashMap`/`LinkedList`/`TreeMap` internals, iterators, the collections API, `Comparator` fluency | how each collection's spliterator splits and why that decides parallel quality; what `groupingBy` returns and why its ordering is unspecified; the sequenced-collections retrofit; `List.of` null-hostility — mechanism here, container internals in 02 |
| 03 Java core | erasure, `==` vs `equals`, initialisation order, exceptions, `java.time`, boxing, the string pool, `switch` on `String`/enum bytecode | poly expressions and target typing, effectively-final capture, value-based classes, `Float`/`Double` equality semantics inside a record, constant expressions and interning for text blocks, checked exceptions in lambdas — the modern-Java half of each, then point |
| 05 Multithreading and concurrency | the memory model, happens-before, `ExecutorService`, locks, `ThreadLocal`, `CompletableFuture`, `ForkJoinPool` as a framework | virtual threads as `Thread`s and what unmounts them, `Semaphore` as the replacement for pool sizing, `ReentrantLock` vs `synchronized` for pinning, `StructuredTaskScope` vs `allOf`, `ManagedBlocker` — mechanism here, the concurrency model in 05 |
| 06 JVM internals | GC, JIT, class loading, hidden classes as a runtime feature, heap dumps, JMH, escape analysis | first-call linkage cost of an `invokedynamic` site, why a megamorphic lambda site stops inlining, why escape analysis usually removes an `Optional`, heap sizing for a million stack chunks — one paragraph each, then point |
| 07 Spring core | the container, proxies, AOP, configuration binding | `spring.threads.virtual.enabled=true` and exactly what it switches, `-parameters` and constructor binding for records, `@Async` on virtual threads |
| 08 Spring Data JPA | persistence context, entity lifecycle, projections | why a record cannot be an entity or an `@Embeddable`, why it is excellent as a projection, `findById` returning `Optional` vs `getReferenceById` |
| 09 SQL databases | query mechanics, JDBC | why JDBC has no `ResultSet` stream and what a hand-written bridge must close |
| 10 Networking | HTTP/1.1 vs 2 vs 3, connection pooling, timeouts | the Java 11 `HttpClient`'s synchronous and `CompletableFuture` forms as the virtual-thread-friendly client |
| 12 API design | REST contracts, versioning, error shapes | records as request/response DTOs, and sealed hierarchies as a compatibility promise you cannot retract |
| 13 Web security | injection, deserialization, polymorphic typing | why you bind SQL parameters even inside a text block, and the `DefaultTyping` caveat when serialising a sealed hierarchy |
| 16 Testing | JUnit, Mockito, JMH discipline, Testcontainers | how to test behaviour expressed as a lambda, how to test exhaustiveness (the test is that it compiles), driving a test from `getPermittedSubclasses()` |
| 17 Git craft | toolchain and build hygiene | only the Maven/Gradle toolchain declaration for a JDK upgrade |
| 20 Observability | metrics, logs, traces, JFR as a platform | the four virtual-thread JFR events, the JSON thread dump, MDC's cost per task, what a "live threads" gauge means now |

## The example domain — QuizStakes

**Every example in these notes comes from the QuizStakes domain, reproduced in full below.
Never write `Dog extends Animal`, `Foo`, `Bar`, `thread1`, `Person`, `Employee` or any other
throwaway example.** Use these entities, these status codes, these numbers, verbatim. A reader
who meets `CLIENT_BONUS_RESERVED` once must meet the same name every time. Where a concept is
genuinely domain-free (`peek` elision, text-block indentation, `Optional.empty()` identity),
still frame it in the domain: the stream is over stake reservations, the text block is the SQL
that reads the ledger, the `Optional` is a client lookup.

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

These are the numbers for every memory calculation, every allocation count, every throughput
argument. A parallel-stream benchmark runs over 2.8M stake reservations; a virtual-thread
sizing argument uses 55k peak concurrent sessions; a `groupingBy` example groups 95k card
deposits by rail; Little's law is worked with 1,200 reservations/sec and the PSP's 240ms p50.

---

# TASK

Write the complete Modern Java bible as a set of Markdown files under
`src/notes/detailed/04-modern-java/`, organised into five parts, covering **all 984 syllabus
leaves reproduced in the `# SYLLABUS` section below**, illustrated by **all 182 diagrams
enumerated in the `# DIAGRAM MANIFEST` section below**, written to the exact file paths in the
`# OUTPUT CONTRACT` section below.

## Tier structure

The notes are organised in these parts, in this order:

| Part | Contains |
|---|---|
| `PART 1 — BASICS` | why "modern Java" is a topic, the release model, the mental model and vocabulary, and the full surface of every feature: functional interfaces, lambdas, method references, the stream model, sources, every intermediate and terminal operation, primitive streams, every collector, `Optional`, `var`, records, sealed types, pattern matching, switch expressions, text blocks, virtual threads, structured concurrency, and the library additions 9 → 21 — with the guarantees each carries |
| `PART 2 — INTERMEDIATE` | cost models and the master comparison tables, lambda cost and choice, when a stream is wrong, parallel streams and their preconditions, collectors in anger, `Optional` discipline, `var` style, records and sealed types in real systems, pattern matching in anger, text blocks in practice, virtual threads in production, structured concurrency in practice, the 8 → 21 migration, and the "which construct do I reach for" decisions |
| `PART 3 — ADVANCED (INTERNALS)` | how it actually works inside — lambda translation through `LambdaMetafactory` and hidden classes, capture and identity, the stream pipeline (`AbstractPipeline`, `Sink`, `StreamOpFlag`), `Spliterator`, parallel execution (`AbstractTask`, `LEAF_TARGET`, the op classes), collector internals, `Optional` internals, `var` inference and upward projection, record class-file attributes and `ObjectMethods`, `PermittedSubclasses`, `SwitchBootstraps.typeSwitch`, switch compilation, text-block compilation, virtual threads (`Continuation`, `StackChunk`, the state machine, the scheduler), structured concurrency and scoped values internals, the version-by-version delta, and the observability toolkit |
| `PART 4 — BUILD IT` | complete, compiling, generic Java 21 reimplementations — a functional toolkit, `MyStream` as a lazy fused pipeline, collectors from scratch, `MyOptional`, records/sealed/patterns from scratch, the concurrency builds, the Java 21 gap-fillers, and the diagnostic harnesses — each followed by a "Diff vs the real one" table |
| `PART 5 — INTERVIEW AND RETENTION` | the 95 questions with answer shapes, the consolidated trap index, the version-stale table, and the drills |

## Hard instructions

Every one of these is mandatory.

- **No line limit and no file-count limit.** There is no upper bound on the length of the notes
  or on how many files they are split across. Completeness beats brevity every single time.
  Never truncate, never write "and so on", never write "similar to the above", never defer a
  concept for space. If a file grows large, split it into more files rather than cutting
  content, and register the new file in `00-index.md`.
- **Output format is Markdown (`.md`).** Every file.
- **Diagrams are standalone SVG files.** Write each diagram as its own file in
  `src/notes/detailed/04-modern-java/diagrams/`, named `D-NNN-short-slug.svg`, and embed it at
  the point of explanation with a Markdown image reference and a caption:

  ```
  ![D-028 — Why stream.peek(...).count() may never call the consumer](../diagrams/D-028-peek-elision.svg)

  **D-028** — Why `stream.peek(...).count()` may never call the consumer.
  ```

  **Never inline `<svg>` in the Markdown** — GitHub and VS Code strip it. **Never use ASCII
  art** — it deforms across renderers and fonts. Where the manifest's `Type` column says
  `table`, a Markdown table is the correct rendering and no SVG is required. Every SVG must
  have:
  - an explicit `viewBox` and no `width`/`height` that forces a fixed pixel size,
  - an opaque backdrop rect so it survives dark mode,
  - orthogonal edge routing only — no diagonals, no curves,
  - a legend,
  - no text smaller than 10.5px,
  - no reliance on external fonts or CSS (use `font-family="sans-serif"` and presentation
    attributes, not classes),
  - explicit contrasting `stroke` on every filled shape and an explicit `fill` on every
    `<text>`,
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
  `switch`, text blocks, `var` sparingly. Where a snippet needs `--enable-preview` on Java 21
  (structured concurrency, scoped values, string templates), say so on the snippet.
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
  constant, a default or an API shape differs across **Java 8 / 9+ / 11 / 17 / 21**, say which
  version does what, inline, at the point of the claim. Where a widely-repeated claim is
  version-stale, state what is true today, what used to be true, and flag it as a version trap.
  **There are 22 `[VERSION-TRAP]` leaves in the syllabus below. The five that matter most are:**
  1. `synchronized` pins a virtual thread on Java 21 — JEP 491 removes that cause in Java 24, so
     "use `ReentrantLock`" is a version-scoped answer,
  2. guarded patterns use `when` in final Java 21 syntax — the earlier previews used `&&`,
  3. record patterns were removed from the enhanced-`for` header before Java 21 shipped,
  4. string templates were previewed in 21 and 22 and **withdrawn** in 23 — Java has no
     interpolation,
  5. `peek` may be elided since Java 9 because `count()` can answer from the source's size.

  Sweep for the other 17 and treat every one the same way.
- **Tag obligations.** The syllabus tags below are instructions, not decoration:
  - `[PROVE]` — work the argument through on the page. Do not state the result. **~150 leaves.**
  - `[SOURCE]` — quote the real JDK source, JEP text or spec text (short excerpt) and explain
    every quoted line. **~75 leaves.**
  - `[BUILD]` — ship complete, compiling, generic code. **65 leaves (all of Part 4), plus
    1.2.20, 1.10.24, 1.13.17, 2.2.9, 2.2.11, 2.2.12, 2.5.8, 2.5.9, 2.8.13, 3.4.11, 3.4.12.**
  - `[TRAP]` — carry a `**Pitfall:**` marker: wrong belief, symptom, fix. **~135 leaves.**
  - `[RESEARCH]` — re-verify against the JDK 21 source at the jdk-21+35 tag, the javadoc, the
    JLS/JVMS or the named JEP before writing. **202 leaves carry this tag.** If you cannot verify
    a claim, say so explicitly in the text rather than asserting it.
  - `[VERSION-TRAP]` — state what is true in 21 and what used to be true. **22 leaves.**
  - `[X-REF nn]` — one self-contained mechanism paragraph here, then point to guide nn.
  - `[NUM]` — state the number or byte arithmetic explicitly, with the arithmetic shown.
    **~85 leaves.**
  - `[BYTECODE]` — show the `javap -c` output and read it instruction by instruction.
    **~30 leaves.**
- **Three figures are explicitly unverified in the syllabus's research pass, because
  `openjdk.org` returned HTTP 403 to every direct fetch and the JEP text was read through search
  summaries and secondary sources. Do not print any of them without confirming it against
  primary source first, and if you cannot confirm it, say so in the text rather than asserting
  it:**
  1. `jdk.virtualThreadScheduler.maxPoolSize` defaulting to **256** (leaf 3.14.5) — confirm
     against `VirtualThread.java` at the jdk-21+35 tag, or against
     `System.getProperties()`/`-XX:+PrintFlagsFinal` on a real JDK 21,
  2. `LEAF_TARGET = ForkJoinPool.getCommonPoolParallelism() << 2` and
     `suggestTargetSize(sizeEstimate) = sizeEstimate / LEAF_TARGET` rounded up (leaves 3.5.2,
     3.5.3) — confirm against `AbstractTask.java` at the same tag,
  3. the OpenJDK LVTI style guide's guideline identifiers **G1–G7** (leaf 1.12.15) — the guide
     403'd, so state its principles in substance and print the `G`-numbers only after verifying
     them at the source.

  The same caution applies to every JEP quotation: **re-fetch the JEP through a mirror**
  (`javaalmanac.io`, `bugs.openjdk.org`, or the `cr.openjdk.org` spec drafts) before quoting JEP
  text verbatim.
- **Three claims in the previous guide must be corrected, not carried forward:**
  1. pinning inside `synchronized` is "fixed in Java 24, still live on 21" — correct, but cite
     JEP 491 and state that the `jdk.VirtualThreadPinned` JFR event survives for native-frame
     pinning, so the diagnostic does not disappear,
  2. the common pool's parallelism is `availableProcessors() - 1` — true, but the submitting
     thread also participates, so the effective width is the core count. State both halves,
  3. structured concurrency's "API is still evolving" — name the actual Java 21 shape (`fork` →
     `Subtask`, `ShutdownOnFailure`/`ShutdownOnSuccess`, preview) *and* the Java 25 rework
     (`open()` static factories, a composable `Joiner`).
- **No emojis. No filler.** No "let's dive in", "great question", "as we all know", "it's worth
  noting". Lead with content.
- **A table for any comparison of three or more things.**
- **Every example uses the QuizStakes domain** as specified in `# CONTEXT`, with the entity
  names, status codes and numbers verbatim.
- The notes end with a flat `## Atomic concept checklist`, one bullet per distinct concept,
  phrased as a one-line assertion the reader can self-quiz against. Downstream agents parse this
  list, so keep it flat — no nesting, no headings inside it.

## Leaf coverage

The syllabus below has **984 leaves** (Part 1: 410, Part 2: 190, Part 3: 210, Part 4: 65,
Part 5: 109). **Every leaf must appear in the notes.** Any leaf you cannot cover must be listed
in a `## Deferred` block at the end of the file that owns it, with the leaf number and a one-line
reason. An empty `## Deferred` block is the expected outcome.

---

# SYLLABUS

**Target version: Java 21 LTS** (baseline for every constant, signature and behaviour below).
Anything introduced or changed in Java 22–26 is marked inline with its version and, where it
supersedes a Java 21 behaviour, with `[VERSION-TRAP]`. Preview status is stated on every leaf where
it applies — a feature being preview is itself the interview-relevant fact.

Scope boundary against the sibling guides: the collections themselves live in
`02-java-collections.md`, the language substrate (erasure, `==`/`equals`, initialisation order,
exceptions, `java.time`) in `03-java-core.md`, the memory model and the executor framework in
`05-multithreading-concurrency.md`, JIT/GC/class loading in `06-jvm-internals.md`. This file owns the
Java-8-and-later *additions*: lambdas, streams, `Optional`, `var`, records, sealed types, pattern
matching, text blocks, switch expressions, virtual threads, structured concurrency, and the
release-by-release delta. Where a concept is owned elsewhere the leaf carries `[X-REF nn]` and the
bible states the mechanism in one paragraph before pointing away — it never sends the reader off
empty-handed.

Tag legend:

| Tag | Meaning for the write pass |
|---|---|
| `[PROVE]` | the bible must work the argument through, not state the result |
| `[SOURCE]` | must quote real JDK source, JEP text or spec text (short excerpt) and explain every line |
| `[BUILD]` | must ship complete, compiling, generic code |
| `[TRAP]` | must carry a `**Trap:**` marker — wrong belief, symptom, fix (rendered in the notes as `**Pitfall:**`) |
| `[RESEARCH]` | leaf exists because of the research phase; re-verify against the cited source before writing |
| `[VERSION-TRAP]` | widely-repeated claim that is version-stale; state what is true in 21 and what changed |
| `[X-REF nn]` | one-paragraph mechanism here, full treatment in guide nn |
| `[NUM]` | must state the number/byte arithmetic explicitly |
| `[BYTECODE]` | must show `javap -c` output and read it instruction by instruction |

---

# PART 1 — BASICS

## §1.1 Why "modern Java" is a topic at all

1.1.1 Java 8 (March 2014) as the discontinuity: lambdas, streams, default methods, `Optional` and
      `java.time` landed together and changed the idiom, not just the API surface.
1.1.2 The six-month release train since Java 9 (JEP 322, time-based releases), and what it replaced
      — the multi-year mega-release with feature-driven slips. `[RESEARCH]`
1.1.3 LTS releases: 8, 11, 17, 21, 25. What LTS means commercially (vendor support window) versus
      technically (nothing — the JDK is the same code). `[RESEARCH]`
1.1.4 The vendor matrix: Oracle JDK, Eclipse Temurin, Amazon Corretto, Azul Zulu, BellSoft Liberica,
      IBM Semeru, Microsoft Build of OpenJDK — and why the answer to "which JDK" is a licensing
      question, not a technical one. `[RESEARCH]`
1.1.5 Preview features (JEP 12): `--enable-preview` at both compile and run, the class file's minor
      version set to 65535, and the rule that a preview class file will not load on a *different*
      release. `[RESEARCH]` `[NUM]`
1.1.6 Incubator modules (`jdk.incubator.*`) versus preview features versus experimental VM options
      (`-XX:+UnlockExperimentalVMOptions`) — three different maturity ladders. `[RESEARCH]`
1.1.7 Why "it is still preview" is the interview-relevant fact: it means the API will change and you
      must not build a published contract on it.
1.1.8 Three kinds of change, and which require what: language features (recompile with a new
      `--release`), library features (recompile or not, depending on the call), runtime features
      (just run on the new JVM). `[X-REF 06]`
1.1.9 `--release N` versus `-source`/`-target`: only `--release` also restricts the *API* to that
      release, which is why `-source 8 -target 8` silently lets you call Java 17 methods that
      `NoSuchMethodError` at runtime. `[TRAP]` `[PROVE]`
1.1.10 Class file major versions: 52 = 8, 53 = 9, 55 = 11, 61 = 17, 65 = 21, 69 = 25 — and how to
       read `UnsupportedClassVersionError` from them. `[NUM]` `[RESEARCH]`
1.1.11 `jdeps`, `jdeprscan` and `jlink` as the migration toolchain. `[X-REF 06]`
1.1.12 What "Java 21" means for this file, and how to check what you are actually running:
       `java -version`, `Runtime.version()` and its `feature()`/`interim()`/`update()`/`patch()`
       accessors, `System.getProperty("java.version")`. `[RESEARCH]`

*(12 leaves)*

## §1.2 Functional interfaces

1.2.1 Definition (JLS 9.8): an interface with exactly one abstract method — the SAM. `[SOURCE]`
1.2.2 `@FunctionalInterface` is optional. It documents intent and makes the compiler enforce the
      one-abstract-method rule; a lambda works without it. `[TRAP]`
1.2.3 Methods that override a `public` method of `Object` do not count toward the SAM count —
      `Comparator` declares both `compare` and `equals` and is still functional. `[PROVE]` `[SOURCE]`
1.2.4 `default`, `static` and `private` interface methods do not count either. `[X-REF 03]`
1.2.5 A generic method (one with its own type parameters) cannot be implemented by a lambda, so an
      interface whose only abstract method is generic is not usable as a lambda target. `[TRAP]`
1.2.6 The vocabulary of a function shape: arity, parameter types, return type, declared exceptions.
1.2.7 `java.util.function` contains exactly **43** interfaces in Java 21. `[NUM]` `[RESEARCH]`
1.2.8 The six core shapes: `Function<T,R>`, `BiFunction<T,U,R>`, `Predicate<T>`, `Consumer<T>`,
      `Supplier<T>`, and the operator specialisations.
1.2.9 `UnaryOperator<T> extends Function<T,T>`; `BinaryOperator<T> extends BiFunction<T,T,T>` —
      they are narrowings, not new shapes.
1.2.10 `Predicate`'s surface: `and`, `or`, `negate`, `isEqual(Object)`, and `not(Predicate)`
       (Java 11). `[RESEARCH]`
1.2.11 `Function.identity()`, `andThen`, `compose` — and the reversed argument order between the
       last two. `[TRAP]` `[PROVE]`
1.2.12 `Consumer.andThen`, `BiFunction.andThen`, `BinaryOperator.minBy`/`maxBy`,
       `BiPredicate.and`/`or`/`negate`.
1.2.13 The primitive-specialisation naming scheme, with the full 43-name inventory: `IntX`,
       `ToIntX`, `XToYFunction`, `ObjIntConsumer`, `BooleanSupplier`. `[RESEARCH]`
1.2.14 Why the specialisations exist: one `Integer.valueOf` per element per stage in a hot pipeline.
       `[NUM]` `[X-REF 03]`
1.2.15 The shapes the JDK does **not** give you: no `TriFunction`, no primitive `BiFunction` beyond
       `ToXBiFunction`, no checked-exception variant of anything. `[TRAP]`
1.2.16 Functional interfaces outside `java.util.function`: `Runnable`, `Callable<V>`,
       `Comparator<T>`, `ThreadFactory`, `Executor`, `InvocationHandler`, `FileFilter`,
       `Iterable` is *not* one (it has a `default forEach` but one abstract `iterator`, so it is).
       Enumerate and correct. `[RESEARCH]`
1.2.17 `Comparator` as the most-used functional interface in practice: `comparing`,
       `comparingInt/Long/Double`, `thenComparing` ×3, `reversed`, `naturalOrder`, `reverseOrder`,
       `nullsFirst`, `nullsLast`. `[X-REF 02]`
1.2.18 `Callable<V>` versus `Supplier<T>`: `Callable.call()` declares `throws Exception`,
       `Supplier.get()` does not — which is why executors take `Callable`. `[X-REF 05]`
1.2.19 Declaring your own functional interface, and when it beats the JDK one: naming the domain
       concept (`PriceRule`, `RetryPolicy`) instead of `Function<Order, BigDecimal>`.
1.2.20 A functional interface with a `throws` clause is perfectly legal, and is the cleanest of the
      four checked-exception workarounds. `[BUILD]`

*(20 leaves)*

## §1.3 Lambda expressions

1.3.1 The syntax forms: `() -> expr`, `x -> expr`, `(x, y) -> expr`, `(Type x) -> { ... }`,
      `(var x) -> ...` (Java 11).
1.3.2 Implicitly typed versus explicitly typed parameter lists; you may not mix the two in one
      lambda. `[TRAP]`
1.3.3 `var` in lambda parameters (Java 11, JEP 323) exists only so you can attach an annotation or
      `final` to an otherwise implicitly typed parameter. `[RESEARCH]`
1.3.4 Expression body versus block body; a block body must `return` on every completing path.
1.3.5 A lambda is a **poly expression**: it has no standalone type, and the target type supplies the
      functional interface. `[PROVE]` `[SOURCE]` `[X-REF 03]`
1.3.6 The target-typing contexts: assignment, method invocation argument, cast, `return`, ternary
      branches, array initialiser, lambda body.
1.3.7 `Object o = () -> {};` does not compile; `Object o = (Runnable) () -> {};` does. `[TRAP]`
      `[PROVE]`
1.3.8 The same lambda source text can implement different interfaces at different sites — the
      lambda has no intrinsic type. `[PROVE]`
1.3.9 Overload ambiguity between two functional-interface parameters (`Runnable` versus
      `Callable<T>`): void-compatible versus value-compatible bodies, and when javac gives up.
      `[TRAP]` `[PROVE]`
1.3.10 A lambda body does **not** introduce a new scope for `this`, `super`, or names — it is
       lexically transparent, unlike an anonymous class body. `[TRAP]` `[X-REF 03]`
1.3.11 `this` inside a lambda is the *enclosing* instance; inside an anonymous class it is the
       anonymous instance. The single most consequential difference when porting. `[TRAP]`
1.3.12 A lambda parameter may not shadow an enclosing local — redeclaring `x` is a compile error,
       whereas an anonymous class may shadow freely. `[TRAP]` `[PROVE]`
1.3.13 Capture is by value and requires effectively-final locals; instance fields are not captured
       at all, the enclosing `this` is. `[PROVE]` `[X-REF 03]`
1.3.14 Wanting to mutate a captured counter: the one-element-array hack, `AtomicInteger`, and why
       `reduce`, a collector, or a plain loop is the actual answer. `[TRAP]`
1.3.15 Capturing a loop variable: the enhanced-`for` variable is a fresh variable per iteration and
       is capturable; the classic `for` index is one variable and is not. `[TRAP]` `[PROVE]`
1.3.16 A checked exception thrown inside a lambda whose SAM does not declare it is a compile error;
       the four workarounds, forward-referenced to §2.2.
1.3.17 Recursion: a lambda cannot reference the local variable it is being assigned to; use a field,
       a two-step assignment, or a method reference. `[TRAP]` `[PROVE]`
1.3.18 Lambdas and generics: the SAM's type variables are instantiated by the target type; a lambda
       itself cannot declare type parameters.
1.3.19 Serializable lambdas: the intersection cast `(Runnable & Serializable) () -> ...`, the
       `SerializedLambda` form, and why this is slow and brittle. `[RESEARCH]`
1.3.20 Lambda parameters may be annotated and declared `final`.
1.3.21 Return-type inference for expression bodies; a void-compatible block body versus a
       value-compatible one, and an expression body that is both (a method call returning a value
       used in a `Consumer`). `[PROVE]`
1.3.22 Debugging a lambda: the synthetic frame `Foo.lambda$main$0` in a stack trace, and the
       `Foo$$Lambda/0x...` class name. `[RESEARCH]` `[VERSION-TRAP]`

*(22 leaves)*

## §1.4 Method references

1.4.1 The four documented kinds plus the two extra forms: static, bound instance, unbound instance,
      constructor, `super::method`, `Outer.this::method`. `[RESEARCH]`
1.4.2 `Type::staticMethod` — e.g. `Integer::parseInt`, `Math::max`.
1.4.3 `instance::method` — bound receiver, e.g. `System.out::println`.
1.4.4 `Type::instanceMethod` — unbound; the receiver becomes the first parameter, e.g.
      `String::length`, `String::compareTo`.
1.4.5 `Type::new` for constructors, and `int[]::new` / `String[]::new` for array constructors.
1.4.6 `super::method` inside an instance method, and where it is the only way to express the call.
1.4.7 `Outer.this::method` from inside an inner class. `[X-REF 03]`
1.4.8 Ambiguity when both a static and an unbound-instance form would apply (`Integer::toString`)
      — a compile error, resolved by writing the lambda. `[TRAP]` `[PROVE]`
1.4.9 `String::valueOf` and which of the eleven overloads the target type selects. `[TRAP]`
      `[X-REF 03]`
1.4.10 A bound method reference evaluates its receiver expression **at capture time**, once —
       `list::size` captures the current `list` object, not the variable. `[TRAP]` `[PROVE]`
1.4.11 A bound method reference on a null receiver throws NPE at capture time, even if the function
       is never invoked. `[TRAP]` `[PROVE]`
1.4.12 Method references to varargs methods, and to generic methods with an explicit type argument
       (`Type::<String>method`).
1.4.13 When a method reference is clearer than a lambda, and when it hides the argument order
       (`Map.Entry::comparingByValue` vs a written comparator). `[TRAP]`
1.4.14 A constructor reference to a record's canonical constructor, and to a compact-constructor
       record that validates.
1.4.15 A method reference to an overloaded method: the target type disambiguates; when it cannot,
       the compile error names all candidates.
1.4.16 In bytecode a method reference produces the same `invokedynamic` as a lambda but with a
       direct method handle as `implMethod` and **no** synthetic `lambda$` method. `[BYTECODE]`
       `[PROVE]`

*(16 leaves)*

## §1.5 The stream model

1.5.1 The javadoc definition: a stream "conveys elements from a source through a pipeline of
      computational operations"; it is not a data structure. `[SOURCE]`
1.5.2 The five stated properties: no storage, functional in nature, laziness-seeking, possibly
      unbounded, consumable. `[SOURCE]`
1.5.3 Anatomy: a source, zero or more intermediate operations, exactly one terminal operation.
1.5.4 Intermediate operations are **always lazy** and return a stream; terminal operations are eager
      except `iterator()` and `spliterator()`. `[SOURCE]`
1.5.5 Fusion: elements flow one at a time through the entire chain, not stage by stage. `[PROVE]`
1.5.6 Short-circuiting: intermediate (`limit`, `takeWhile`) versus terminal (`findFirst`,
      `anyMatch`); the javadoc's statement that short-circuiting is "necessary, but not sufficient"
      for an infinite pipeline to terminate. `[SOURCE]` `[PROVE]`
1.5.7 Stateless versus stateful intermediate operations; a stateful op may require a full pass and
      significant buffering, and a pipeline of only stateless ops needs one pass with minimal
      buffering. `[SOURCE]`
1.5.8 Encounter order: defined by the source. `List` and arrays have it; `HashSet` does not.
      `[SOURCE]` `[X-REF 02]`
1.5.9 `unordered()` as a hint that relaxes ordering constraints and legitimises reordering.
      `[SOURCE]`
1.5.10 Non-interference: the source must not be modified while the pipeline executes;
       `ConcurrentModificationException` (or worse, silent wrong answers) is the symptom. `[TRAP]`
       `[X-REF 02]`
1.5.11 Behavioural parameters must be **stateless**; the javadoc's own `Set<Integer> seen`
       counter-example. `[SOURCE]` `[TRAP]`
1.5.12 Side effects are discouraged and may be elided entirely; only `forEach` and `forEachOrdered`
       are documented to rely on them. `[SOURCE]` `[TRAP]`
1.5.13 A stream is consumed once: the second terminal operation throws
       `IllegalStateException: stream has already been operated upon or closed`. `[SOURCE]` `[TRAP]`
1.5.14 Streams are `AutoCloseable`, but only I/O-backed streams (`Files.lines`, `Files.walk`,
       `Files.find`, `Files.list`) actually need closing. `[TRAP]`
1.5.15 `onClose(Runnable)` and the try-with-resources form for a file-backed stream.
1.5.16 `BaseStream` and the four concrete stream types: `Stream<T>`, `IntStream`, `LongStream`,
       `DoubleStream`.
1.5.17 A stream is not a collection: no `size()`, no random access, no reuse, no `get(i)` — and the
       places that hurts.
1.5.18 What a stream buys (composition, laziness, one-line parallelism, declarative aggregation)
       and what it costs (debuggability, stack depth, allocation, no checked exceptions).

*(18 leaves)*

## §1.6 Stream sources

1.6.1 `Collection.stream()` and `Collection.parallelStream()` as `default` methods added to
      `Collection` in Java 8 — the canonical example of why default methods exist. `[X-REF 03]`
1.6.2 `Stream.of(T...)`, `Stream.of(T)`, `Stream.empty()`.
1.6.3 `Arrays.stream(T[])`, `Arrays.stream(T[], from, to)`, and the `int[]`/`long[]`/`double[]`
      overloads.
1.6.4 `Stream.iterate(seed, next)` — infinite; `Stream.iterate(seed, hasNext, next)` (Java 9) — the
      three-argument for-loop form. `[RESEARCH]`
1.6.5 `Stream.generate(Supplier)` — infinite and unordered, so `limit` on it in parallel is
      nondeterministic. `[TRAP]`
1.6.6 `IntStream.range` / `rangeClosed`, and why they are the best-splitting source in the JDK
      (`SIZED | SUBSIZED | ORDERED`). `[NUM]`
1.6.7 `Stream.concat(a, b)` — and why `concat` inside a loop builds a left-deep tree that
      `StackOverflowError`s on traversal. `[TRAP]` `[RESEARCH]`
1.6.8 `Stream.ofNullable(T)` (Java 9) — a zero-or-one stream, the cleanest null bridge.
1.6.9 `Optional.stream()` (Java 9) and the `.map(this::find).flatMap(Optional::stream)` idiom.
1.6.10 `Files.lines(Path)`, `Files.lines(Path, Charset)`, `Files.walk`, `Files.list`, `Files.find`,
       `Files.newDirectoryStream` — all hold a file handle and all must be closed. `[TRAP]`
1.6.11 `BufferedReader.lines()`, `String.lines()` (Java 11), `String.chars()`, `String.codePoints()`.
       `[X-REF 03]`
1.6.12 `Pattern.splitAsStream`, `Matcher.results()` (Java 9), `Scanner.tokens()` (Java 9).
       `[RESEARCH]`
1.6.13 `Random.ints/longs/doubles`, and the Java 17 `RandomGenerator` interface's stream methods.
       `[RESEARCH]`
1.6.14 `Map` has no `stream()`; you stream `entrySet()`, `keySet()` or `values()`. `[TRAP]`
       `[X-REF 02]`
1.6.15 `StreamSupport.stream(Spliterator, boolean)` as the general escape hatch, and
       `Spliterators.spliteratorUnknownSize(Iterator, characteristics)` for an `Iterator`. `[NUM]`
1.6.16 `JarFile.stream()`, `ZipFile.stream()`, `ServiceLoader.stream()`; `ResultSet` has none, so
       JDBC needs a hand-written bridge. `[X-REF 09]`
1.6.17 `Stream.builder()` and when it beats collecting into a list first.
1.6.18 Any infinite source requires a short-circuiting operation; `sorted()` or `distinct()` on an
       infinite stream never terminates. `[TRAP]`

*(18 leaves)*

## §1.7 Intermediate operations, exhaustively

1.7.1 `filter(Predicate)` — stateless, 1:0-or-1.
1.7.2 `map(Function)` — stateless, 1:1.
1.7.3 `mapToInt` / `mapToLong` / `mapToDouble` / `mapToObj` / `boxed` / `asLongStream` /
      `asDoubleStream` — the conversions between the four stream shapes.
1.7.4 `flatMap(Function<T, Stream<R>>)` — 1:N; each inner stream is closed after it is consumed.
1.7.5 `flatMapToInt` / `flatMapToLong` / `flatMapToDouble`.
1.7.6 `mapMulti` and `mapMultiToInt/Long/Double` (Java 16): a push-style `flatMap` taking a
      `BiConsumer<T, Consumer<R>>`, avoiding one `Stream` allocation per element. `[RESEARCH]`
      `[NUM]`
1.7.7 When `mapMulti` beats `flatMap`: few or zero outputs per element, primitive outputs, or
      output produced imperatively. `[RESEARCH]`
1.7.8 `distinct()` — stateful, uses `equals`/`hashCode`, preserves encounter order for ordered
      streams, and holds every distinct element in memory. `[X-REF 02]`
1.7.9 `sorted()` and `sorted(Comparator)` — a full barrier: buffers the whole stream, then sorts
      with TimSort. `[X-REF 01]` `[X-REF 02]`
1.7.10 `sorted()` on non-`Comparable` elements throws `ClassCastException` at *terminal* time, not
       at the `sorted()` call — the laziness surprise. `[TRAP]` `[PROVE]`
1.7.11 `limit(n)` — short-circuiting, cheap sequentially, expensive on an ordered parallel stream.
       `[TRAP]`
1.7.12 `skip(n)` — stateful, with the same parallel-ordering cost.
1.7.13 `takeWhile(Predicate)` / `dropWhile(Predicate)` (Java 9) — **prefix** semantics, not `filter`
       semantics: they stop at the first failure, they do not test every element. `[TRAP]`
1.7.14 `takeWhile`/`dropWhile` on an unordered stream are nondeterministic by specification.
       `[TRAP]` `[SOURCE]`
1.7.15 `peek(Consumer)` — documented as being "mainly to support debugging". `[SOURCE]`
1.7.16 `peek` may be skipped entirely: since Java 9 `count()` can answer from the source's size
       without traversing, so `stream.peek(...).count()` may never call the consumer. `[TRAP]`
       `[PROVE]` `[SOURCE]` `[VERSION-TRAP]`
1.7.17 `parallel()`, `sequential()`, `unordered()`, `onClose()` — `BaseStream` operations that
       change the pipeline rather than the elements.
1.7.18 The stateful/stateless classification table for every intermediate operation.
1.7.19 The short-circuiting classification table.
1.7.20 Operation order is semantics **and** cost: `filter` before `map`, `limit` before `sorted`
       gives a different answer than after. `[PROVE]` `[NUM]`
1.7.21 There is no `zip` in the JDK; the three workarounds (`IntStream.range` over indices, paired
       iterators, a custom `Spliterator`) and why none is pleasant. `[TRAP]`
1.7.22 There is no windowing, batching, `scan` or `distinctBy` in Java 21 — Stream Gatherers
       (JEP 461 preview 22, JEP 473 preview 23, JEP 485 final in 24) fill exactly this gap.
       `[RESEARCH]` `[VERSION-TRAP]`
1.7.23 `flatMap` and short-circuiting: prior to Java 10 a `flatMap` inner stream was fully consumed
       even when the downstream had short-circuited (JDK-8075939). `[VERSION-TRAP]` `[RESEARCH]`
1.7.24 The intermediate-operation inventory table: name, version, laziness, statefulness,
       short-circuiting, effect on `SIZED`/`ORDERED`/`DISTINCT`/`SORTED` flags.

*(24 leaves)*

## §1.8 Terminal operations, exhaustively

1.8.1 `forEach(Consumer)` — no encounter-order guarantee on a parallel stream, by specification.
      `[TRAP]` `[SOURCE]`
1.8.2 `forEachOrdered(Consumer)` — restores encounter order and largely erases the parallel win.
      `[NUM]`
1.8.3 `toArray()` returning `Object[]`, and `toArray(IntFunction<A[]>)` with `String[]::new`.
      `[TRAP]`
1.8.4 `collect(Collector)` and the three-argument `collect(supplier, accumulator, combiner)`.
1.8.5 `toList()` (Java 16) — returns an **unmodifiable** list that *does* permit nulls, unlike
      `Collectors.toUnmodifiableList()`. `[TRAP]` `[NUM]`
1.8.6 `reduce(BinaryOperator)` → `Optional<T>`.
1.8.7 `reduce(identity, BinaryOperator)` → `T`.
1.8.8 `reduce(identity, accumulator, combiner)` → `U`, and its three documented contracts.
      `[SOURCE]` `[PROVE]`
1.8.9 The identity and associativity requirements, and exactly what goes wrong in parallel when
      they are violated (subtraction, string concatenation with a non-identity seed). `[PROVE]`
1.8.10 `reduce` with a mutable accumulator is a bug — that is what `collect` exists for. `[TRAP]`
       `[PROVE]`
1.8.11 `min(Comparator)` / `max(Comparator)` → `Optional<T>`.
1.8.12 `count()` — and the Java 9 change that lets it bypass the pipeline when the size is known.
       `[VERSION-TRAP]` `[SOURCE]`
1.8.13 `anyMatch` / `allMatch` / `noneMatch` — short-circuiting, and the vacuous truth of `allMatch`
       and `noneMatch` on an empty stream (both `true`). `[TRAP]` `[PROVE]`
1.8.14 `findFirst()` versus `findAny()`: `findAny` is nondeterministic by design and is the
       parallel-friendly one.
1.8.15 `findFirst()` on an ordered parallel stream forces cross-task coordination. `[NUM]`
1.8.16 `iterator()` and `spliterator()` — the two lazy escape hatches, and the only terminal
       operations that are not eager. `[SOURCE]`
1.8.17 `sum()`, `average()`, `min()`, `max()`, `summaryStatistics()` on the primitive streams.
1.8.18 `IntSummaryStatistics` / `LongSummaryStatistics` / `DoubleSummaryStatistics`: count, sum,
       min, average, max — and that `DoubleSummaryStatistics` uses compensated summation.
       `[RESEARCH]` `[NUM]`
1.8.19 Which terminal operations return `Optional` and why (the empty-stream case has no answer).
1.8.20 Terminal-operation flags: `StreamOpFlag.SHORT_CIRCUIT` declared by the `TerminalOp`, and how
       it changes `copyInto` to `copyIntoWithCancel`. `[SOURCE]`
1.8.21 A pipeline with no terminal operation does **nothing at all**, silently — no warning, no
       error. `[TRAP]` `[PROVE]`
1.8.22 An exception thrown from a behavioural parameter propagates out of the terminal operation;
       in parallel, one arbitrary exception wins and the others are lost. `[TRAP]`
1.8.23 `collect` versus `reduce` versus `forEach`: the decision rule in one sentence each.
1.8.24 Boxing cost of `collect(toList())` applied to a primitive stream, and `boxed()` as the
       explicit, visible step. `[NUM]`
1.8.25 Null policy across terminal operations: `Stream` itself permits nulls, `Collectors.toMap`
       rejects null values, `Collectors.toUnmodifiableList` rejects null elements, `Stream.toList`
       permits them. `[TRAP]` `[NUM]`
1.8.26 The terminal-operation inventory table: name, version, return type, short-circuiting,
       parallel friendliness, ordering sensitivity.

*(26 leaves)*

## §1.9 Primitive streams

1.9.1 `IntStream`, `LongStream`, `DoubleStream` — and why there is no `CharStream`, `BooleanStream`
      or `FloatStream` (`char`/`short`/`byte`/`float` widen into the three that exist). `[TRAP]`
      `[RESEARCH]`
1.9.2 `String.chars()` returns an `IntStream` of UTF-16 code units, so `forEach(System.out::println)`
      prints numbers. `[TRAP]` `[PROVE]` `[X-REF 03]`
1.9.3 `boxed()`, `mapToObj`, `asLongStream()`, `asDoubleStream()` as the ways back out.
1.9.4 `mapToInt` / `mapToLong` / `mapToDouble` as the ways in from an object stream.
1.9.5 `IntStream.range(a, b)` versus `rangeClosed(a, b)`, and the empty-range case when `a >= b`.
1.9.6 `sum()` → `int`/`long`/`double`; `average()` → `OptionalDouble`; `max()`/`min()` →
      `OptionalInt`/`OptionalLong`/`OptionalDouble`; `count()` → `long`.
1.9.7 `summaryStatistics()` and its four (five with average) accessors.
1.9.8 `OptionalInt` / `OptionalLong` / `OptionalDouble` have **no** `map`, `flatMap` or `filter` —
      a deliberately thinner API that forces you back to the primitive. `[TRAP]` `[RESEARCH]`
1.9.9 `IntStream.of`, `Arrays.stream(int[])`, `IntStream.iterate`, `IntStream.generate`,
      `IntStream.concat`, `IntStream.empty`.
1.9.10 `Collectors.summingInt` versus `IntStream.sum()`: the boxing difference, measured. `[NUM]`
1.9.11 `IntStream.sum()` returns `int` and silently overflows past 2 147 483 647; `mapToLong(i -> i)
       .sum()` is the fix. `[TRAP]` `[NUM]` `[PROVE]` `[X-REF 03]`
1.9.12 `average()` on an empty stream is `OptionalDouble.empty()`, not `0.0`. `[TRAP]`
1.9.13 Sorting a primitive stream uses the primitive dual-pivot quicksort, not TimSort — different
       complexity guarantees and no stability question. `[X-REF 01]` `[X-REF 02]`
1.9.14 `IntStream.toArray()` versus `boxed().toArray(Integer[]::new)`: 4 bytes per element versus
       16 bytes per `Integer` plus a 4-or-8-byte reference. `[NUM]` `[PROVE]` `[X-REF 03]`
1.9.15 The primitive functional interfaces that pair with each stream type (`IntPredicate`,
       `IntUnaryOperator`, `IntToLongFunction`, `ObjIntConsumer`, …).
1.9.16 When to reach for a primitive stream: hot loops, large N, pure numeric aggregation — and
       when the boxed form is fine.

*(16 leaves)*

## §1.10 Collectors

1.10.1 The `Collector<T, A, R>` contract: `supplier()`, `accumulator()`, `combiner()`, `finisher()`,
       `characteristics()`. `[SOURCE]`
1.10.2 `Collector.Characteristics`: `CONCURRENT`, `UNORDERED`, `IDENTITY_FINISH`. `[SOURCE]`
1.10.3 `Collectors` exposes **30** distinct static factory methods across **54** overloads in
       Java 21. `[NUM]` `[RESEARCH]`
1.10.4 `toList()`, `toUnmodifiableList()`, `toSet()`, `toUnmodifiableSet()`,
       `toCollection(Supplier)`.
1.10.5 `Collectors.toList()` returns an `ArrayList` in the current implementation, but the contract
       promises neither the type nor mutability — code that casts it is broken by construction.
       `[TRAP]` `[SOURCE]`
1.10.6 `toMap` ×4: `(k,v)`, `(k,v,merge)`, `(k,v,merge,mapFactory)`, plus the concurrent sibling.
1.10.7 `toMap` throws `IllegalStateException: Duplicate key ...` when two elements map to the same
       key and no merge function is supplied. `[TRAP]` `[SOURCE]`
1.10.8 `toMap` throws `NullPointerException` on a null **value**, unlike `HashMap.put` — because it
       is implemented with `map.merge`. `[TRAP]` `[PROVE]` `[SOURCE]`
1.10.9 `toUnmodifiableMap` ×2 and `toConcurrentMap` ×4.
1.10.10 `joining()` ×3: no-arg, delimiter, delimiter+prefix+suffix.
1.10.11 `counting()`, `summingInt/Long/Double`, `averagingInt/Long/Double`,
        `summarizingInt/Long/Double`.
1.10.12 `averagingInt` returns `Double`; `summingDouble` and `averagingDouble` use Kahan compensated
        summation internally, which is why they can disagree with a naive loop. `[RESEARCH]` `[NUM]`
        `[SOURCE]`
1.10.13 `minBy(Comparator)` / `maxBy(Comparator)` → `Optional<T>`.
1.10.14 `reducing` ×3, and why it is the least-used collector (`reduce` on the stream is clearer
        unless it is a downstream).
1.10.15 `mapping(mapper, downstream)`, `flatMapping` (Java 9), `filtering` (Java 9).
1.10.16 `collectingAndThen(downstream, finisher)` — the unmodifiable-wrap and the
        collapse-to-a-single-value idioms.
1.10.17 `groupingBy` ×3: `(classifier)`, `(classifier, downstream)`,
        `(classifier, mapFactory, downstream)`.
1.10.18 `groupingBy` returns a `HashMap` with `ArrayList` values — no ordering guarantee at either
        level. Supply `TreeMap::new` / `LinkedHashMap::new` when order matters. `[TRAP]`
1.10.19 The classifier must not return null — `groupingBy` NPEs on a null key. `[TRAP]` `[PROVE]`
1.10.20 `groupingByConcurrent` ×3, and the three conditions under which it actually runs
        concurrently. `[SOURCE]`
1.10.21 `partitioningBy` ×2 — always returns a two-entry map containing both `false` and `true`,
        even for an empty stream, which is the one thing `groupingBy(pred)` does not give you.
        `[TRAP]` `[PROVE]`
1.10.22 `teeing(c1, c2, merger)` (Java 12) — run two collectors in one pass and merge. `[RESEARCH]`
1.10.23 Nested downstreams three levels deep: `groupingBy → groupingBy → mapping → toSet`.
1.10.24 Hand-writing a collector with `Collector.of(...)` ×2 overloads. `[BUILD]`
1.10.25 The three conditions for a genuine concurrent reduction: the stream is parallel, the
        collector is `CONCURRENT`, and the stream is unordered or the collector is `UNORDERED`.
        `[SOURCE]` `[PROVE]`
1.10.26 Why ordinary `collect(toList())` parallelises correctly without `CONCURRENT`: per-leaf
        containers plus a combiner tree. `[PROVE]`
1.10.27 `joining()` in parallel: the combiner is an O(n) copy at every merge, so it is a poor
        parallel collector. `[NUM]` `[PROVE]`
1.10.28 Collectors that return `Optional` (`minBy`, `maxBy`, `reducing(BinaryOperator)`) and why.
1.10.29 The collector inventory table: name, version, result type, mutability, null policy,
        characteristics, parallel behaviour.
1.10.30 Collectors that do not exist and what to use instead: no `toSortedMap`, no `toBiMap`, no
        `toEnumMap` shortcut, no `countingLong`-by-key beyond `groupingBy(…, counting())`.

*(30 leaves)*

## §1.11 Optional

1.11.1 Purpose: model "a value may be absent" in a **return type**, forcing the caller to
       acknowledge absence at the type level.
1.11.2 The javadoc API note: "primarily intended for use as a method return type where there is a
       clear need to represent 'no result'". Quote it. `[SOURCE]`
1.11.3 `Optional` is a value-based class: do not synchronize on it, do not depend on its identity.
       `[SOURCE]` `[TRAP]` `[X-REF 03]`
1.11.4 `Optional` is **not** `Serializable`, which is the concrete reason it does not belong in a
       field. `[TRAP]`
1.11.5 Construction: `of(T)` (NPE on null), `ofNullable(T)`, `empty()`.
1.11.6 Interrogation: `isPresent()`, `isEmpty()` (11), `get()`, `orElseThrow()` (10),
       `orElseThrow(Supplier)`.
1.11.7 Transformation: `map`, `flatMap`, `filter`, `or(Supplier)` (9), `stream()` (9).
1.11.8 Consumption: `ifPresent(Consumer)`, `ifPresentOrElse(Consumer, Runnable)` (9).
1.11.9 Defaults: `orElse(T)`, `orElseGet(Supplier)`.
1.11.10 The full method table with the version each was added: 15 methods at 1.8, three at 9
        (`ifPresentOrElse`, `or`, `stream`), one at 10 (`orElseThrow()`), one at 11 (`isEmpty`).
        `[NUM]` `[RESEARCH]`
1.11.11 `orElse` evaluates its argument **eagerly, even when a value is present**. `[TRAP]`
        `[PROVE]`
1.11.12 `get()` without a presence check throws `NoSuchElementException: No value present` and
        defeats the point; `orElseThrow()` is the same code with a self-documenting name. `[TRAP]`
1.11.13 `if (opt.isPresent()) { opt.get() }` is the null check you were replacing, plus one
        allocation. `[TRAP]`
1.11.14 `Optional` in a field: not serializable, one extra object and one extra dereference per
        access. `[TRAP]` `[NUM]`
1.11.15 `Optional` as a method parameter: overload the method or accept null instead. `[TRAP]`
1.11.16 `Optional` as a collection element or a map value: use an empty collection or an absent key.
        `[TRAP]`
1.11.17 Never return `null` from a method declared to return `Optional`. `[TRAP]`
1.11.18 `Optional<List<T>>` is almost always wrong; return an empty list. `[TRAP]`
1.11.19 `map` internally does `ofNullable(mapper.apply(value))`, so a mapper returning null yields
        `empty()` rather than an NPE. `[SOURCE]` `[PROVE]`
1.11.20 `flatMap` versus `map` when the mapper already returns an `Optional` — and the compile error
        that tells you which you needed.
1.11.21 Chained null-safe navigation: `a.map(A::b).map(B::c).filter(...).orElseGet(...)`.
1.11.22 `OptionalInt` / `OptionalLong` / `OptionalDouble`: `getAsInt`/`getAsLong`/`getAsDouble`, no
        `map`, and why you usually convert with `stream()` or `orElse`. `[TRAP]`
1.11.23 `Optional` in frameworks: Spring Data repository `findById`, Jackson's `Jdk8Module`,
        `@JsonInclude(NON_ABSENT)`, and the serialised shape you get without the module. `[TRAP]`
        `[RESEARCH]` `[X-REF 08]`
1.11.24 `Optional`'s allocation cost in a hot loop, why escape analysis usually removes it, and
        Valhalla's plan to make it genuinely free. `[NUM]` `[RESEARCH]` `[X-REF 06]`

*(24 leaves)*

## §1.12 `var`

1.12.1 Local variable type inference (Java 10, JEP 286). Compile-time only; Java stays statically
       typed and there is no runtime cost. `[PROVE]` `[BYTECODE]`
1.12.2 `var` is not `Object`, not `dynamic`, and not a keyword — it is a reserved *type name*, so a
       variable or method may still be called `var`. `[TRAP]` `[RESEARCH]` `[X-REF 03]`
1.12.3 Where `var` is legal: a local with an initialiser, the enhanced-`for` variable, the classic
       `for` index, a try-with-resources resource, and a lambda parameter (Java 11).
1.12.4 Where `var` is illegal: fields, method parameters, return types, `catch` parameters, a local
       without an initialiser, `var x = null`, an array-initialiser shorthand, and as a generic
       type argument. `[TRAP]`
1.12.5 `var x = null;` does not compile — the null type is not denotable. `[PROVE]`
1.12.6 `var arr = {1, 2, 3};` does not compile; `var arr = new int[]{1, 2, 3};` does.
1.12.7 `var list = new ArrayList<>();` infers `ArrayList<Object>` — the diamond has no target type
       to work from. `[TRAP]` `[PROVE]`
1.12.8 `var` with a ternary works; with a lambda or a method reference it does not, because those
       are poly expressions with no standalone type. `[TRAP]` `[PROVE]`
1.12.9 `var` can capture non-denotable types: an anonymous class type, an intersection type, a
       capture variable — types you cannot write down. `[PROVE]` `[X-REF 03]`
1.12.10 `var` and numeric literals: `var x = 1` is `int`, `var y = 1L` is `long`, `var f = 1.0` is
        `double`, `var b = (byte) 1` is `byte`. `[NUM]`
1.12.11 `var` in an enhanced-`for` over a raw or wildcard-typed collection, and what gets inferred.
1.12.12 `final var` is legal; `var` alone is **not** implicitly final.
1.12.13 You cannot annotate the inferred type, which is precisely why `(var x) -> ...` exists in
        lambda parameter lists.
1.12.14 JEP 323 (Java 11): `var` in lambda parameters is all-or-nothing across the parameter list.
        `[RESEARCH]`
1.12.15 The OpenJDK LVTI style guide's principles: reading code matters more than writing it; code
        should be clear from local reasoning; readability should not depend on an IDE; explicit
        types are a trade-off, not a virtue. `[RESEARCH]`
1.12.16 When `var` hurts: an opaque factory call, an accumulator whose width matters, and pinning
        the concrete implementation type into the local's static type
        (`var list = new ArrayList<String>()` makes `list` an `ArrayList`, not a `List`). `[TRAP]`

*(16 leaves)*

## §1.13 Records

1.13.1 A record is a transparent, shallowly immutable carrier for data — JEP 359 preview (14),
       JEP 384 second preview (15), JEP 395 final (16). `[RESEARCH]`
1.13.2 Brian Goetz's framing: records are "nominal tuples". Why the name matters and what it rules
       out. `[RESEARCH]`
1.13.3 The header declares the components; everything else is derived by the compiler.
1.13.4 Generated members: one `private final` field per component, a canonical constructor, an
       accessor per component, `equals`, `hashCode`, `toString`.
1.13.5 Accessors are `name()`, not `getName()` — which is exactly what older bean-convention
       frameworks fail on. `[TRAP]`
1.13.6 Implicit modifiers: the class is `final`, extends `java.lang.Record`, and therefore cannot
       extend anything else.
1.13.7 A record may not declare additional instance fields; it may declare static fields, static
       and instance methods, static initialisers, nested types, and it may implement interfaces.
1.13.8 The canonical constructor: implicit, or declared explicitly with the full parameter list.
1.13.9 The compact constructor: no parameter list, no explicit field assignment; you validate or
       reassign the parameters and the compiler assigns them at the end. `[PROVE]`
1.13.10 Validation and normalisation belong in the compact constructor, and the fix is always
        *reassigning the parameter*, never assigning the field. `[TRAP]`
1.13.11 Alternate constructors must delegate to the canonical one via `this(...)`.
1.13.12 An explicit canonical constructor must be at least as accessible as the record itself.
1.13.13 You may override an accessor, `equals`, `hashCode` or `toString` — and you then own the
        contracts, including the equal-implies-equal-hash rule. `[TRAP]` `[X-REF 03]`
1.13.14 Generic records, and how their type parameters appear in record patterns.
1.13.15 Local records (Java 16), nested records (implicitly static), and records declared inside an
        interface.
1.13.16 A record is **shallowly** immutable: a `List` or array component is still mutable, and the
        accessor hands out the live reference. `[TRAP]` `[PROVE]`
1.13.17 The fix: `List.copyOf` / `Map.copyOf` / `Set.copyOf` in the compact constructor, plus
        `clone()` on copy-out for array components. `[BUILD]`
1.13.18 An array component silently breaks `equals`/`hashCode`, because the generated code uses
        reference equality for arrays. Use a `List`. `[TRAP]` `[PROVE]`
1.13.19 Generated `equals` compares primitives with `==`, `float`/`double` with
        `Float.equals`/`Double.equals` semantics, and references with `Objects.equals`. `[SOURCE]`
        `[PROVE]`
1.13.20 Therefore inside a record `NaN` equals `NaN` and `0.0` does **not** equal `-0.0` — the
        opposite of `==`. `[TRAP]` `[PROVE]` `[X-REF 03]`
1.13.21 The generated `hashCode` algorithm is deliberately unspecified; never persist it, never
        assume stability across releases. `[TRAP]` `[SOURCE]`
1.13.22 `toString` format: `Point[x=1, y=2]`.
1.13.23 Records and null: components may be null unless you reject them;
        `Objects.requireNonNull` in the compact constructor is the convention.
1.13.24 Reflection: `Class.isRecord()`, `Class.getRecordComponents()`, and `RecordComponent`'s
        `getName`/`getType`/`getGenericType`/`getAccessor`/`getAnnotations`. `[RESEARCH]`
1.13.25 Record serialization: the components govern the serialised form, and deserialization goes
        through the canonical constructor. `[SOURCE]` `[RESEARCH]` `[X-REF 03]`
1.13.26 That closes the classic "deserialization bypasses the constructor and therefore your
        validation" hole. `[PROVE]` `[RESEARCH]`
1.13.27 Where records fit: DTOs, value objects, compound map keys, multiple return values, sealed
        hierarchy cases, and short-lived intermediate shapes inside a pipeline.
1.13.28 Where they do not, and the "record cliff": the moment you need a mutable field, an internal
        representation different from the API, or inheritance, you lose every generated member at
        once. JPA entities are the canonical example. `[TRAP]` `[RESEARCH]` `[X-REF 08]`

*(28 leaves)*

## §1.14 Sealed types

1.14.1 `sealed` restricts which types may extend or implement a type — JEP 360 preview (15),
       JEP 397 second preview (16), JEP 409 final (17). `[RESEARCH]`
1.14.2 Syntax: `public sealed interface Shape permits Circle, Rectangle, Triangle {}`.
1.14.3 Every permitted subtype must itself be `final`, `sealed`, or explicitly `non-sealed` — there
       is no default. `[TRAP]`
1.14.4 `non-sealed` reopens one branch of the hierarchy, and is the only hyphenated modifier in the
       language.
1.14.5 The `permits` clause may be omitted when all permitted subtypes are declared in the same
       source file. `[RESEARCH]`
1.14.6 Permitted subtypes must be in the same module as the sealed type, or — in the unnamed module
       — in the same package. `[RESEARCH]` `[TRAP]` `[X-REF 03]`
1.14.7 Every permitted subclass must **directly** extend or implement the sealed type; a
       grandchild is not permitted by the grandparent. `[RESEARCH]` `[PROVE]`
1.14.8 Anonymous classes and local classes can never be permitted subtypes — they have no canonical
       name to write in `permits`. `[TRAP]` `[RESEARCH]`
1.14.9 A sealed abstract class with record subclasses, versus a sealed interface implemented by
       records — the two ADT shapes and when each reads better.
1.14.10 Sealed interfaces plus records give Java algebraic data types: a sum of products.
1.14.11 Sealed versus enum: an enum is a closed set of *instances*, a sealed type is a closed set of
        *types*. Use an enum when the cases carry no per-case data. `[X-REF 03]`
1.14.12 What sealing buys you: exhaustiveness in a pattern switch, so adding a case turns every
        consumer into a compile error instead of a runtime fall-through. `[PROVE]`
1.14.13 What sealing buys the compiler: narrowing reference conversion can be rejected at compile
        time when the sealed hierarchy proves the cast impossible. `[RESEARCH]` `[PROVE]`
1.14.14 The cost: adding a permitted subtype is a source-incompatible change for every exhaustive
        switch over the hierarchy — a feature internally, a breaking change across an API boundary.
        `[TRAP]`
1.14.15 You cannot permit a type you do not control, which is what makes sealing a within-module
        design tool.
1.14.16 `sealed` + `non-sealed` as a controlled framework extension point.
1.14.17 Reflection: `Class.isSealed()` and `Class.getPermittedSubclasses()`. `[RESEARCH]`
1.14.18 The three ways to restrict extension compared: `final`, a package-private constructor, and
        `sealed` — visibility, granularity, and what the compiler can prove from each.

*(18 leaves)*

## §1.15 Pattern matching

1.15.1 A pattern is three things at once: a type test, a conditional extraction, and a binding.
1.15.2 Type patterns in `instanceof` — JEP 305 preview (14), JEP 375 (15), JEP 394 final (16):
       `if (o instanceof String s)`. `[RESEARCH]`
1.15.3 Flow scoping: the binding variable is in scope exactly where the compiler can prove the test
       succeeded — not a lexical block rule. `[PROVE]` `[X-REF 03]`
1.15.4 Flow scoping with negation: `if (!(o instanceof String s)) return;` puts `s` in scope for the
       rest of the method. `[PROVE]` `[TRAP]`
1.15.5 Flow scoping with `&&` (binding available on the right) versus `||` (it is not). `[TRAP]`
       `[PROVE]`
1.15.6 Type patterns in `switch` — four previews (17, 18, 19, 20), final as JEP 441 in Java 21.
       `[RESEARCH]`
1.15.7 `case null` and `case null, default` — `switch` is no longer null-hostile. `[RESEARCH]`
1.15.8 Without a `case null`, a pattern switch throws `NullPointerException` on a null selector,
       matching the historical behaviour. `[TRAP]` `[PROVE]`
1.15.9 Guarded patterns use `when` in the final syntax; the earlier previews used `&&`, so older
       material is wrong. `[VERSION-TRAP]` `[RESEARCH]`
1.15.10 Record patterns — JEP 405 preview (19), JEP 432 (20), JEP 440 final (21):
        `case Circle(double r)`. `[RESEARCH]`
1.15.11 Nested record patterns: `case Line(Point(int x1, int y1), Point(int x2, int y2))`.
1.15.12 `var` inside a record pattern component, and generic record pattern inference — the compiler
        infers the type arguments so you can drop them. `[RESEARCH]` `[PROVE]`
1.15.13 Record patterns in the header of an enhanced `for` were **removed** before Java 21 shipped;
        code and articles showing them do not compile on 21. `[VERSION-TRAP]` `[RESEARCH]`
1.15.14 Exhaustiveness is required of any `switch` that uses a pattern or null label, or whose
        selector type is not one of the legacy types. `[SOURCE]` `[RESEARCH]`
1.15.15 The legacy selector types that do **not** require exhaustiveness: `char`, `byte`, `short`,
        `int`, `Character`, `Byte`, `Short`, `Integer`, `String`, and enum types. `[SOURCE]`
        `[RESEARCH]`
1.15.16 Type coverage over a sealed hierarchy: the compiler reads `permits` to decide exhaustiveness,
        so omitting `default` is what makes future additions loud. `[PROVE]`
1.15.17 `MatchException` (new in 21): thrown when an exhaustive switch matches nothing at runtime —
        the separate-compilation drift case — and when a record accessor throws during
        deconstruction. `[RESEARCH]` `[TRAP]`
1.15.18 Dominance: writing a more general label before a more specific one is a compile error, not a
        silent shadow. `[PROVE]` `[SOURCE]`
1.15.19 A guarded case must precede its unguarded twin; the guard removes it from the dominance
        analysis. `[TRAP]` `[PROVE]`
1.15.20 A total type pattern dominates everything including `default`, so you cannot write both.
        `[TRAP]` `[RESEARCH]`
1.15.21 Patterns and generics: `case Box<String> b` is only allowed where it is provably safe;
        otherwise you get an unchecked-pattern error. `[X-REF 03]`
1.15.22 Record patterns in `instanceof`, outside a switch:
        `if (o instanceof Point(int x, int y))`.
1.15.23 Qualified enum constant labels in a pattern switch (`case Suit.HEARTS`) — new in 21.
        `[RESEARCH]`
1.15.24 What patterns still do not do in 21: no primitive type patterns (JEP 455/507, still
        preview), no array patterns, no deconstruction of non-record classes, no alternation
        (`or`) patterns, no unnamed patterns (final in 22). `[RESEARCH]` `[VERSION-TRAP]`

*(24 leaves)*

## §1.16 `switch` expressions and statements

1.16.1 Switch expressions — JEP 325 preview (12), JEP 354 (13), JEP 361 final (14): `switch`
       produces a value. `[RESEARCH]`
1.16.2 The arrow form `case L ->`: no fall-through, no `break`.
1.16.3 Multiple labels per arm: `case MONDAY, TUESDAY, WEDNESDAY ->`.
1.16.4 Block-bodied arms and `yield`.
1.16.5 `return` inside a switch **expression** is illegal; `yield` is the only way out. `[TRAP]`
1.16.6 A switch expression must be exhaustive; an enum switch expression without `default` fails to
       compile the moment a constant is added — which is the point. `[PROVE]`
1.16.7 The colon form with `yield` (a switch expression in legacy syntax) is legal and rare.
1.16.8 You may not mix arrow arms and colon arms in one `switch`. `[TRAP]`
1.16.9 Switch **statements** in the colon form keep the historical fall-through semantics, and
       `-Xlint:fallthrough` still exists for them. `[X-REF 03]`
1.16.10 Arrow-form switch statements: no fall-through, and no value produced.
1.16.11 Exhaustiveness in Java 21 applies to pattern switch *statements* as well as expressions —
        the rule is about the labels, not the form. `[RESEARCH]` `[TRAP]`
1.16.12 Definite assignment through a switch expression: every arm must yield a value or complete
        abruptly. `[X-REF 03]`
1.16.13 The permitted selector types: `char`, `byte`, `short`, `int` and their boxes, `String`,
        enums, and (21) any reference type with patterns. Never `long`, `float`, `double`,
        `boolean`. `[TRAP]`
1.16.14 Enum constants in an arrow switch are unqualified; in a pattern switch they may be
        qualified. `[RESEARCH]`
1.16.15 The `default`-in-an-enum-switch trade-off: silence on new constants versus a compile error.
        `[TRAP]`
1.16.16 A switch expression is an expression: assignable, returnable, passable as an argument, and
        nestable inside another switch arm.
1.16.17 The classic missing-`break` fall-through bug, and how the arrow form makes it unwritable.
1.16.18 When a switch expression beats a `Map<K, Supplier<V>>` lookup table and when it does not.

*(18 leaves)*

## §1.17 Text blocks

1.17.1 Text blocks — JEP 355 preview (13), JEP 368 (14), JEP 378 final (15). The result is an
       ordinary `java.lang.String`. `[RESEARCH]`
1.17.2 Syntax: opening delimiter `"""` followed by optional whitespace and a line terminator, then
       the content, then the closing `"""`.
1.17.3 Content may not begin on the opening delimiter's line — that is a compile error. `[TRAP]`
1.17.4 Three compile-time steps, in this order: normalise line terminators to `\n`, remove
       incidental whitespace, translate escape sequences. `[SOURCE]` `[RESEARCH]`
1.17.5 Normalisation means a CRLF source file still yields `\n` in the string — text blocks are
       platform-deterministic. `[PROVE]` `[RESEARCH]`
1.17.6 Incidental whitespace: the common prefix is computed over all non-blank content lines **plus
       the closing delimiter's line**. `[SOURCE]` `[PROVE]`
1.17.7 Therefore the closing delimiter's indentation controls the result — moving it left adds
       indentation to every line. `[TRAP]` `[PROVE]`
1.17.8 Trailing whitespace is stripped from every line, always. `[TRAP]`
1.17.9 `\s` (Java 15) is a space that survives stripping — the "fence" idiom for preserving trailing
       spaces. `[RESEARCH]`
1.17.10 `\` at end of line suppresses the line terminator (line continuation).
1.17.11 Escapes are processed **after** stripping, so a literal `\n` you wrote is not a candidate for
        normalisation and `\s` is not a candidate for stripping. `[PROVE]` `[RESEARCH]`
1.17.12 Ending without a trailing newline: put the closing delimiter at the end of the last content
        line.
1.17.13 `"` and `""` need no escaping inside a text block; three consecutive quotes need one `\"`.
1.17.14 The runtime siblings: `String.stripIndent()`, `String.translateEscapes()`,
        `String.formatted(Object...)`, `String.indent(int)` — all Java 12–15. `[RESEARCH]`
        `[X-REF 03]`
1.17.15 A text block is a constant expression: interned, usable as a `case` label and as an
        annotation value. `[PROVE]` `[X-REF 03]`
1.17.16 Where they earn their keep: SQL, JSON, HTML, GraphQL — and where they do not: regex, where
        `\` is still an escape and everything doubles. `[TRAP]`

*(16 leaves)*

## §1.18 Virtual threads — the model

1.18.1 JEP 425 preview (19), JEP 436 (20), JEP 444 final (21): a virtual thread is a
       `java.lang.Thread` scheduled by the Java runtime rather than the operating system.
       `[RESEARCH]`
1.18.2 The problem being solved: the thread-per-request model capped by platform thread count, and
       the async/reactive workaround's loss of readable stack traces, debuggers and profilers.
       `[RESEARCH]`
1.18.3 Little's law framing: concurrency = throughput × latency, so the thread count was the
       throughput cap. `[PROVE]` `[NUM]`
1.18.4 Virtual threads deliver **scale (throughput), not speed (latency)** — the javadoc's own
       phrasing. `[SOURCE]` `[TRAP]`
1.18.5 Carrier threads: a dedicated `ForkJoinPool` in FIFO mode, with default parallelism equal to
       the number of available processors. `[RESEARCH]` `[NUM]`
1.18.6 `jdk.virtualThreadScheduler.parallelism` and `jdk.virtualThreadScheduler.maxPoolSize` as the
       system properties that tune it. `[RESEARCH]` `[NUM]`
1.18.7 Mounting and unmounting: on a blocking call the continuation's stack is copied to the heap
       and the carrier is released; on resumption it is copied back. `[PROVE]`
1.18.8 What triggers an unmount: the JDK-instrumented blocking points — socket and channel I/O,
       `Thread.sleep`, `LockSupport.park`, `BlockingQueue`, `java.util.concurrent` locks,
       `HttpClient`, `Selector`, `Process.waitFor`. `[X-REF 05]`
1.18.9 What does not: file I/O on most platforms, `Object.wait` before Java 24, and any native
       frame. `[TRAP]` `[RESEARCH]`
1.18.10 Cost: a few hundred bytes plus a growable heap-resident stack, versus a platform thread's
        typically 1 MB reserved stack and an OS thread. `[NUM]`
1.18.11 `Thread.ofVirtual()` / `Thread.ofPlatform()` and the `Thread.Builder` API: `name(String)`,
        `name(prefix, start)`, `unstarted`, `start`, `factory`. `[RESEARCH]`
1.18.12 `Thread.startVirtualThread(Runnable)` as the one-liner.
1.18.13 `Executors.newVirtualThreadPerTaskExecutor()` — a new virtual thread per task, not a pool;
        `close()` waits for every submitted task. `[RESEARCH]`
1.18.14 `ExecutorService` is `AutoCloseable` since Java 19, which is what makes the
        try-with-resources form work. `[RESEARCH]`
1.18.15 Virtual threads are always daemon threads; `setDaemon(false)` throws. `[TRAP]` `[RESEARCH]`
1.18.16 Priority is fixed at `NORM_PRIORITY` and `setPriority` is silently a no-op. `[TRAP]`
        `[RESEARCH]`
1.18.17 They belong to a single fixed thread group, and `getName()` is the empty string unless you
        name them — which is why an unnamed virtual thread is hard to find in a dump. `[TRAP]`
1.18.18 `stop`, `suspend` and `resume` are unsupported and throw `UnsupportedOperationException`.
        `[RESEARCH]`
1.18.19 `ThreadLocal` still works, but its economics invert: a per-thread cache is now a per-task
        cache, and a million of them is a heap problem. `[TRAP]` `[SOURCE]`
1.18.20 `Thread.Builder.allowSetThreadLocals(boolean)` and
        `inheritInheritableThreadLocals(boolean)`. `[RESEARCH]`
1.18.21 Pinning: a virtual thread that cannot unmount holds its carrier. On Java 21 the two causes
        are blocking inside a `synchronized` block or method, and blocking inside a native or
        foreign frame. `[TRAP]` `[RESEARCH]`
1.18.22 Diagnosing pinning: `-Djdk.tracePinnedThreads=full|short`, and the `jdk.VirtualThreadPinned`
        JFR event, which is enabled by default with a 20 ms threshold. `[NUM]` `[RESEARCH]`
1.18.23 The fix on 21 is `ReentrantLock` around any blocking section; JEP 491 removes the
        `synchronized` cause entirely in Java 24, so "use ReentrantLock" is a version-scoped
        answer. `[VERSION-TRAP]` `[RESEARCH]` `[X-REF 05]`
1.18.24 Three standing rules: do not pool virtual threads, do not expect them to help CPU-bound
        work, and use a `Semaphore` — not a pool — to limit concurrency. `[TRAP]` `[SOURCE]`

*(24 leaves)*

## §1.19 Structured concurrency

1.19.1 The problem: unstructured concurrency leaks threads, loses cancellation, and produces
       thread dumps with no parent-child relationship. `[RESEARCH]`
1.19.2 The principle: a task split into concurrent subtasks returns to the same block, so the
       subtasks cannot outlive it — the concurrency analogue of structured programming.
1.19.3 The Java 21 shape (JEP 453, preview): `StructuredTaskScope` with `fork`, `join`, `close`, and
       `Subtask<T>`. `[RESEARCH]`
1.19.4 `fork` returns `Subtask<T>`, not `Future<T>` — JEP 453 changed this from the incubator form,
       so older articles are wrong. `[VERSION-TRAP]` `[RESEARCH]`
1.19.5 `StructuredTaskScope.ShutdownOnFailure`: cancel all siblings on the first failure;
       `join()` then `throwIfFailed()`.
1.19.6 `StructuredTaskScope.ShutdownOnSuccess`: cancel the rest on the first success — hedged
       requests.
1.19.7 `joinUntil(Instant)` for one deadline across the whole scope.
1.19.8 `Subtask.state()` (`UNAVAILABLE`, `SUCCESS`, `FAILED`), `get()`, `exception()`, and the
       `IllegalStateException` from calling `get()` before `join()`. `[TRAP]` `[RESEARCH]`
1.19.9 The scope must be created, forked into, joined and closed on the same thread, inside a
       try-with-resources block; violating that throws `StructureViolationException`. `[RESEARCH]`
1.19.10 Cancellation propagates by interrupt, so a subtask that swallows `InterruptedException`
        still leaks. `[TRAP]` `[X-REF 05]`
1.19.11 Versus `CompletableFuture.allOf`: there a failure leaves the siblings running and
        cancellation is advisory. `[PROVE]` `[X-REF 05]`
1.19.12 Versus `ExecutorService.invokeAll`: that does cancel on return, but the executor's lifetime
        has no relationship to the calling block.
1.19.13 On Java 21 this needs `--enable-preview`; the package moved from `jdk.incubator.concurrent`
        to `java.util.concurrent` at 21. `[TRAP]` `[RESEARCH]`
1.19.14 The API was reworked in Java 25 (JEP 505): public constructors replaced by static `open()`
        factories, and `ShutdownOnFailure`/`ShutdownOnSuccess` replaced by a composable `Joiner`.
        `[VERSION-TRAP]` `[RESEARCH]`
1.19.15 Scoped values — JEP 429 incubator (20), previews at 21/22/23/24, final as JEP 506 in
        Java 25: an immutable, bounded-lifetime, inheritable replacement for `ThreadLocal`.
        `[RESEARCH]`
1.19.16 `ScopedValue.where(KEY, value).run(...)` / `.call(...)`; the static `runWhere`/`callWhere`
        forms were removed in Java 24, so most published examples no longer compile.
        `[VERSION-TRAP]` `[RESEARCH]`

*(16 leaves)*

## §1.20 The library additions, 9 → 21

1.20.1 Java 9: `List.of` / `Set.of` / `Map.of` / `Map.ofEntries` — immutable, null-hostile, and with
       deliberately randomised iteration order for `Set`/`Map` per JVM run. `[TRAP]` `[X-REF 02]`
1.20.2 Java 10: `List.copyOf` / `Set.copyOf` / `Map.copyOf`, and
       `Collectors.toUnmodifiableList/Set/Map`.
1.20.3 Java 9 stream and `Optional` additions: `takeWhile`, `dropWhile`, `ofNullable`, the
       three-argument `iterate`, `Optional.stream`, `Optional.or`, `Optional.ifPresentOrElse`.
1.20.4 Java 9 language additions: private interface methods, effectively-final resources in
       try-with-resources, the diamond on anonymous classes, `@SafeVarargs` on private methods.
       `[X-REF 03]`
1.20.5 Java 9 platform: JPMS, JShell, jlink, multi-release JARs. `[X-REF 03]` `[X-REF 06]`
1.20.6 Java 9 APIs: the `Process` API (`pid`, `info`, `children`, `onExit`), `Flow` (the reactive
       streams SPI), `VarHandle`, `StackWalker`. `[X-REF 05]` `[X-REF 06]`
1.20.7 Java 9 runtime: compact strings and indified string concatenation — invisible but the two
       biggest string performance changes of the era. `[X-REF 03]`
1.20.8 Java 11 `String`: `isBlank`, `strip`, `stripLeading`, `stripTrailing`, `lines`, `repeat`.
       `[X-REF 03]`
1.20.9 Java 11 utility: `Files.readString`, `Files.writeString`, `Path.of`,
       `Collection.toArray(IntFunction)`, `Predicate.not`.
1.20.10 Java 11: the standard `HttpClient` (HTTP/2, WebSocket, synchronous and `CompletableFuture`
        forms) — the replacement for `HttpURLConnection`. `[X-REF 10]`
1.20.11 Java 11: single-file source-code launch (`java Foo.java`) and the shebang form.
1.20.12 Java 12: `Collectors.teeing`, `String.indent`, `String.transform`, `Files.mismatch`,
        `CompactNumberFormat`.
1.20.13 Java 14: helpful `NullPointerException` messages (JEP 358), on by default since 15.
        `[X-REF 03]`
1.20.14 Java 15: `String.stripIndent`, `translateEscapes`, `formatted`; `CharSequence.isEmpty`.
1.20.15 Java 16: `Stream.toList`, `Stream.mapMulti`, `Period`/`Duration` additions,
        day-period formatting in `DateTimeFormatter` (`B`). `[X-REF 03]`
1.20.16 Java 17: the `RandomGenerator` interface family and `RandomGeneratorFactory` (JEP 356),
        replacing the `java.util.Random`-only world. `[RESEARCH]`
1.20.17 Java 18: UTF-8 as the default charset (JEP 400) — the single most behaviour-changing library
        change of the decade for existing code. `[TRAP]` `[X-REF 03]`
1.20.18 Java 19/20: virtual threads, structured concurrency, record patterns and pattern switch all
        in preview or incubator — the "everything landed in 21" story starts here.
1.20.19 Java 21 sequenced collections (JEP 431): `SequencedCollection`, `SequencedSet`,
        `SequencedMap`, with `getFirst`, `getLast`, `addFirst`, `addLast`, `removeFirst`,
        `removeLast`, `reversed`, and on the map `putFirst`, `putLast`, `firstEntry`, `lastEntry`,
        `pollFirstEntry`, `pollLastEntry`, `sequencedKeySet`, `sequencedValues`,
        `sequencedEntrySet`. `[RESEARCH]` `[X-REF 02]`
1.20.20 The retrofit: `List` and `Deque` gain `SequencedCollection` as a superinterface;
        `LinkedHashSet` implements `SequencedSet`; `SortedSet` extends `SequencedSet`;
        `LinkedHashMap` implements `SequencedMap`; `SortedMap` extends `SequencedMap`.
        `[RESEARCH]` `[X-REF 02]`
1.20.21 `reversed()` returns a **view**, not a copy — writing through it writes through to the
        source. `[TRAP]` `[X-REF 02]`
1.20.22 `getFirst()` on an empty sequenced collection throws `NoSuchElementException`; it does not
        return null. `[TRAP]`
1.20.23 Java 21 smaller additions: `Math.clamp`, `StringBuilder.repeat`, `Character.isEmoji` and
        friends, `Thread.threadId()`, `Runtime.availableProcessors` container awareness.
        `[RESEARCH]`
1.20.24 Java 21 items named here only so you can place them: generational ZGC, the KEM API, the
        Vector API (sixth incubator), the FFM API (third preview). `[RESEARCH]` `[X-REF 06]`

*(24 leaves)*

---

**PART 1 total: 410 leaves**

---

# PART 2 — INTERMEDIATE

## §2.1 The master tables

2.1.1 **The master cost table**: every stream operation with per-element cost, allocation per stage,
      statefulness, buffering, and parallel behaviour — amortised and worst case split out. `[NUM]`
2.1.2 The master feature-by-version table: feature, JEP number, first preview, final release, what
      it replaced, and the one trap that comes with it.
2.1.3 The lambda vs anonymous class vs inner class vs method reference table: class files generated,
      allocations, capture semantics, `this`, startup cost, serialization, debuggability. `[NUM]`
2.1.4 The absence-representation table: `Optional`, `null`, an exception, an empty collection, a
      null object, a sentinel — with the case each is correct for.
2.1.5 The data-carrier table: record vs final class vs enum vs interface vs `Map<String,Object>`.
2.1.6 The concurrency-model table: platform threads, virtual threads, reactive, structured
      concurrency — throughput, latency, debuggability, backpressure, library support, team cost.
2.1.7 The list-factory table: `new ArrayList<>()`, `Arrays.asList`, `List.of`, `List.copyOf`,
      `Collectors.toList`, `Collectors.toUnmodifiableList`, `Stream.toList` — mutability, null
      policy, structural modification, set-in-place. `[TRAP]` `[NUM]` `[X-REF 02]`
2.1.8 The one-page "which construct" index for the whole topic, forward-referenced to §2.15.

*(8 leaves)*

## §2.2 Lambda cost and choice

2.2.1 Startup cost: the first execution of a lambda call site links an `invokedynamic` and spins a
      hidden class — hundreds of microseconds, once per site. `[NUM]` `[PROVE]`
2.2.2 Steady-state cost: after linking, invoking a lambda is an ordinary interface call and inlines
      like one. `[X-REF 06]`
2.2.3 A non-capturing lambda is instantiated **once** and cached in a static field of the spun
      class — the same object is returned every time. `[PROVE]` `[SOURCE]`
2.2.4 A capturing lambda allocates per evaluation; escape analysis usually scalar-replaces it, and
      "usually" is where the surprise lives. `[NUM]` `[X-REF 06]`
2.2.5 An anonymous class costs one class file per site, one allocation per instance, and a synthetic
      `this$0` reference to the enclosing instance. `[NUM]` `[X-REF 03]`
2.2.6 When an anonymous class is still the right answer: needing fields, needing more than one
      method, needing its own `this`, needing a name in a stack trace.
2.2.7 Lambda count and JVM startup: thousands of distinct lambdas measurably slow startup, and
      AppCDS/dynamic CDS archiving of the spun classes is the mitigation. `[RESEARCH]` `[NUM]`
      `[X-REF 06]`
2.2.8 Megamorphic call sites: a `Function` field assigned twenty different lambdas will not inline,
      and the pipeline slows by an order of magnitude. `[TRAP]` `[X-REF 06]`
2.2.9 Composition: `andThen`/`compose` on `Function`, `and`/`or`/`negate` on `Predicate`, and
      building a composite predicate by reducing a list with `Predicate::and`. `[BUILD]`
2.2.10 Currying and partial application in Java (`Function<A, Function<B, C>>`) and why it reads
       badly enough to avoid outside a DSL.
2.2.11 Checked exceptions in lambdas, workaround 1: a custom `@FunctionalInterface` that declares
       `throws E`. `[BUILD]`
2.2.12 Workarounds 2–4: an `unchecked(...)` adapter that wraps into a `RuntimeException`; the
       sneaky-throw generic cast; a `Result`/`Either` return type. Each with its cost. `[BUILD]`
       `[TRAP]` `[X-REF 03]`
2.2.13 Why `Stream` has no checked-exception story at all, and what that means for I/O inside a
       pipeline. `[TRAP]`
2.2.14 Testing behaviour expressed as a lambda: extract it to a named method or a named constant so
       it can be asserted on directly. `[X-REF 16]`

*(14 leaves)*

## §2.3 Streams: the cost model, and when not to use one

2.3.1 What a pipeline costs versus a `for` loop: the pipeline stage objects, the sink chain, the
      megamorphic dispatch, and the boxing. `[NUM]`
2.3.2 Where streams are effectively free: a monomorphic pipeline over an `ArrayList` that the JIT
      inlines end to end. `[NUM]` `[X-REF 06]`
2.3.3 Where they are not: primitive-heavy inner loops, collections of ten elements, deeply nested
      `flatMap`.
2.3.4 The allocation profile of a three-stage pipeline: how many objects exist before the first
      element flows. `[NUM]` `[PROVE]`
2.3.5 Debuggability: what a stream stack trace looks like, and why a breakpoint inside a lambda is
      not the same as a breakpoint inside a loop body. `[TRAP]`
2.3.6 Stack depth: a long pipeline plus recursion plus `flatMap` can `StackOverflowError` where the
      loop version would not. `[TRAP]`
2.3.7 Short-circuiting as the case where a stream genuinely beats the naive loop.
2.3.8 Ordering as optimisation: filter early, map late, and never `sorted()` before `limit()` when
      the comparator is expensive. `[PROVE]` `[NUM]`
2.3.9 `sorted().findFirst()` is O(n log n); `min(comparator)` is O(n). The same answer, different
      class of algorithm. `[PROVE]` `[NUM]` `[X-REF 01]`
2.3.10 `distinct()` cost, its memory profile, and its total dependence on a correct
       `equals`/`hashCode`. `[X-REF 02]` `[X-REF 03]`
2.3.11 Streaming a `LinkedList`: the spliterator reports no useful size and splits by batching, so
       both traversal and parallelism are poor. `[X-REF 02]`
2.3.12 Re-streaming inside a loop — the accidental O(n·m), and the fix (build a `Map` index once).
       `[TRAP]` `[NUM]`
2.3.13 Grouping in one pass versus collecting to a map and iterating it.
2.3.14 When to use a loop: side effects, early exit carrying several values, index arithmetic,
       in-place mutation, checked exceptions, and measured hot paths. `[TRAP]`
2.3.15 When to use a stream: transformation chains, grouping and aggregation, laziness over an
       expensive or infinite source, and one-line parallelism over a splittable source.
2.3.16 Readability rules that survive review: one operation per line, extract predicates to named
       methods, never nest a pipeline inside another pipeline's argument, name the intermediate
       collection when it clarifies.

*(16 leaves)*

## §2.4 Parallel streams

2.4.1 `.parallel()` / `.parallelStream()`: the pipeline becomes a ForkJoin task tree over the
      source `Spliterator`.
2.4.2 The shared `ForkJoinPool.commonPool()`, whose default parallelism is
      `availableProcessors() - 1` — because the submitting thread also participates. `[NUM]`
      `[PROVE]`
2.4.3 `-Djava.util.concurrent.ForkJoinPool.common.parallelism=N` as the only supported knob, and
      that it is process-global. `[RESEARCH]` `[NUM]`
2.4.4 Submitting the terminal operation to your own `ForkJoinPool` makes the stream use that pool —
      but this is emergent behaviour of `ForkJoinTask.fork`, not a documented API. `[TRAP]`
      `[RESEARCH]` `[PROVE]`
2.4.5 Blocking I/O inside a parallel stream starves the common pool for the entire JVM, including
      every other library that uses it. `[TRAP]`
2.4.6 The four preconditions for parallel to pay: large N, expensive per-element work, a cheaply
      splittable `SIZED`/`SUBSIZED` source, and no shared mutable state.
2.4.7 The N×Q heuristic: roughly 10 000 total "units of work" before the split/merge overhead is
      repaid. `[NUM]` `[RESEARCH]`
2.4.8 Source splitting quality, ranked: `int[]`/`ArrayList`/`IntStream.range` (excellent) →
      `HashMap`/`HashSet`/`TreeMap` (good but uneven) → `LinkedList`/`Files.lines`/
      `Stream.iterate`/`BufferedReader.lines` (effectively serial). `[NUM]` `[X-REF 02]`
2.4.9 Ordering costs: `limit`, `skip`, `findFirst` and `forEachOrdered` all force cross-task
      coordination on an ordered parallel stream. `[NUM]`
2.4.10 Merge cost: `toList` and `joining` both have O(n) combiners, and a bad combiner can dominate
       the whole run. `[PROVE]` `[NUM]`
2.4.11 Shared mutable state: `parallelStream().forEach(list::add)` corrupts the list — lost
       elements, nulls, or `ArrayIndexOutOfBoundsException` from inside `ArrayList.add`. `[TRAP]`
       `[PROVE]` `[X-REF 02]`
2.4.12 Collectors are safe because each leaf gets its own container and the combiner merges them —
       no shared state is ever touched. `[PROVE]`
2.4.13 `groupingByConcurrent` and the three conditions for it to actually reduce concurrently.
       `[SOURCE]`
2.4.14 Parallel streams inside a request thread, and the interaction with virtual threads: the
       common pool is still platform threads and still global. `[TRAP]`
2.4.15 Measuring: JMH with warm-up and a blackhole, never `System.nanoTime` around a cold loop.
       `[X-REF 06]` `[X-REF 16]`
2.4.16 The default answer in a server application: do not use parallel streams; use an executor you
       own and can size, name and monitor. `[TRAP]`

*(16 leaves)*

## §2.5 Collectors in anger

2.5.1 Multi-level grouping: `groupingBy(a, groupingBy(b, counting()))` and reading the resulting
      nested map type.
2.5.2 Downstream shaping: `mapping`, `filtering`, `flatMapping`, `collectingAndThen`, `reducing`.
2.5.3 `filtering(p, toList())` keeps empty groups; a `filter(p)` before `groupingBy` removes them —
      two different answers from code that looks equivalent. `[TRAP]` `[PROVE]`
2.5.4 Choosing the map implementation: `TreeMap::new` for order, `LinkedHashMap::new` for encounter
      order, `EnumMap::new` for enum keys. `[X-REF 02]`
2.5.5 `toMap` merge strategies: last-wins `(a, b) -> b`, first-wins `(a, b) -> a`, and combining
      `(a, b) -> a.merge(b)`.
2.5.6 Building an index and an inverted index in one pass each.
2.5.7 `teeing` for min-and-max, count-and-sum, or two independent aggregates in a single traversal.
2.5.8 A bounded top-N collector written with `Collector.of` over a `PriorityQueue`, with a correct
      combiner. `[BUILD]` `[X-REF 02]`
2.5.9 A boxing-free statistics collector over a `long[]` accumulator. `[BUILD]` `[NUM]`
2.5.10 Which characteristics to declare on a custom collector and what each unlocks.
2.5.11 Three ways to an immutable result — `toUnmodifiableList()`,
       `collectingAndThen(toList(), List::copyOf)`, and `Stream.toList()` — with three different
       null policies. `[TRAP]` `[NUM]`
2.5.12 Collectors that return `Optional`, and how to flatten that away with `collectingAndThen`.
2.5.13 Collecting into a record instead of a nested map — the readability upgrade that also gives
       you a name for the aggregate.
2.5.14 A `Collector` is a stateless factory of state, so a `static final Collector` field is safe to
       share across threads. `[PROVE]`

*(14 leaves)*

## §2.6 Optional discipline

2.6.1 The rule set in one place: return type only; never a field, parameter, collection element or
      map value; never null.
2.6.2 The chain style: `map`/`flatMap`/`filter`/`or`/`orElseGet`, never `isPresent` + `get`.
2.6.3 `orElse` vs `orElseGet` vs `orElseThrow`: the decision table, with the eager-evaluation cost
      spelled out. `[NUM]`
2.6.4 `ifPresentOrElse` for the genuine two-branch case.
2.6.5 `or(Supplier)` for a fallback lookup chain (cache → database → default).
2.6.6 `Optional` inside a stream: `.map(this::find).flatMap(Optional::stream)`.
2.6.7 Spring Data: `findById` returns `Optional`, `getReferenceById` returns a proxy and throws
      later — a different contract with the same shape. `[TRAP]` `[X-REF 08]`
2.6.8 Jackson: serialising an `Optional` field without the `Jdk8Module` produces
      `{"present":true}`; with it, the unwrapped value or `null`. `[TRAP]` `[RESEARCH]`
2.6.9 `Optional` as a builder argument or a constructor parameter: the anti-pattern, and the
      overload alternative. `[TRAP]`
2.6.10 The four absence strategies compared: `Optional`, nullability annotations
       (`@Nullable`/`@NonNull` + NullAway), the null-object pattern, and an exception. `[X-REF 03]`
2.6.11 `Optional.of(1).equals(Optional.of(1))` is true (it delegates to the value's `equals`);
       `Optional.empty().equals(null)` is false. `[PROVE]`
2.6.12 `Optional` in a hot loop: one allocation per call, why the JIT usually removes it, and how to
       confirm with an allocation profiler. `[NUM]` `[X-REF 06]`

*(12 leaves)*

## §2.7 `var` in practice

2.7.1 A style policy you can defend in review: use `var` when the initialiser already names the
      type, and only then.
2.7.2 `var` with builders and fluent chains, where the type is both long and obvious.
2.7.3 `var` with try-with-resources.
2.7.4 `var` in an enhanced-`for` over `Map.Entry<K, V>` — the single biggest readability win.
2.7.5 `var` for deeply generic types (`Map<String, List<Map<String, Integer>>>`).
2.7.6 `var` and the interface-versus-implementation question: the local's static type becomes the
      concrete class, which changes what compiles later. `[TRAP]` `[PROVE]`
2.7.7 `var` and numeric literals: `var total = 0` is an `int` accumulator, and the overflow is
      yours. `[TRAP]` `[NUM]` `[X-REF 03]`
2.7.8 `var` in lambda parameters: only worth it for an annotation.
2.7.9 `var` and refactoring: changing a method's return type silently retypes every `var` local —
      sometimes a compile error where you want one, sometimes a behaviour change where you do not.
      `[TRAP]`
2.7.10 Team conventions, and why both "never use var" and "always use var" fail the style guide's
       own test.

*(10 leaves)*

## §2.8 Records in practice

2.8.1 Records as request/response DTOs at an HTTP boundary, with the validated compact constructor.
      `[X-REF 12]`
2.8.2 Records with Jackson: the canonical constructor is used from 2.12 onward; `@JsonProperty` on
      components; `@JsonCreator` when parameter names are unavailable. `[TRAP]` `[RESEARCH]`
2.8.3 `-parameters` as a compile flag: what stops working without it (Spring constructor binding,
      Jackson name inference, some validation messages). `[X-REF 07]`
2.8.4 Records with Bean Validation: the annotation must have a `@Target` including
      `RECORD_COMPONENT` or `PARAMETER`/`FIELD` for it to land where the validator looks. `[TRAP]`
      `[RESEARCH]`
2.8.5 Records with Spring: `@ConfigurationProperties` constructor binding, `@RequestBody`,
      and the limits with `@ModelAttribute` form binding. `[RESEARCH]` `[X-REF 07]`
2.8.6 Records with JPA: not entities (no no-arg constructor, no proxying, no dirty checking), not
      `@Embeddable` for the same reason — but excellent as JPQL constructor-expression projections
      and Spring Data DTO projections. `[TRAP]` `[X-REF 08]`
2.8.7 Records as compound map keys: correct `equals`/`hashCode` for free, which is the whole
      problem with hand-written keys. `[X-REF 02]`
2.8.8 Records as multiple return values, replacing an out-parameter, an array, or a `Pair`.
2.8.9 Local records as scratch types inside a stream pipeline — declare, use, discard.
2.8.10 The "wither" pattern: hand-written `withX` methods returning a new instance, and the fact
       that derived record creation is still not a language feature. `[RESEARCH]`
2.8.11 Builders for records with many components, and when the builder earns its boilerplate.
2.8.12 Records and inheritance: a sealed interface for the family, composition for the shared state.
2.8.13 Defensive copying, done properly: copy-in in the compact constructor and copy-out in the
       accessor for arrays. `[BUILD]`
2.8.14 Records versus Lombok `@Value`: what each generates, and what a record gives that Lombok
       cannot (pattern deconstruction, the `Record` attribute, serialization through the
       constructor). `[RESEARCH]`
2.8.15 Floating-point components: `Double.equals` semantics inside a record mean `NaN` matches and
       `-0.0` does not — a real bug in a price or coordinate type. `[TRAP]` `[PROVE]`
2.8.16 Migrating an existing value class to a record: the checklist, and the four things that block
       it (mutability, inheritance, a hidden representation, a framework requiring a no-arg
       constructor).

*(16 leaves)*

## §2.9 Sealed types and data-oriented programming

2.9.1 Algebraic data types in Java: sealed types are the sum, records are the product.
2.9.2 Data-oriented programming as Brian Goetz frames it: model data as immutable data, keep
      behaviour separate, make illegal states unrepresentable, use exhaustive pattern matching.
      `[RESEARCH]`
2.9.3 The Visitor pattern replaced by a sealed interface plus a pattern switch — with the line
      count and the coupling comparison. `[PROVE]`
2.9.4 The expression problem: sealed hierarchies make adding *operations* easy and adding *cases*
      loud; open polymorphic hierarchies do the exact opposite. Pick per axis of change. `[PROVE]`
2.9.5 A state machine as a sealed interface of records, with transitions as a pattern switch.
2.9.6 A result type: `sealed interface Result<T> permits Ok, Err` and why it beats an exception for
      expected failures. `[X-REF 03]`
2.9.7 A parse tree, a protocol message set, and a domain event stream — the three canonical shapes.
2.9.8 Sealed types across a published API boundary: exhaustiveness becomes a compatibility promise
      you cannot take back. `[TRAP]`
2.9.9 When an enum is better (no per-case data), and when open polymorphism is better (third
      parties must extend). `[TRAP]`
2.9.10 One worked domain model combining sealed interfaces, records, pattern switch and text blocks.
2.9.11 Testing exhaustiveness: the test is that it compiles; there is nothing to assert. `[X-REF 16]`
2.9.12 Serialising a sealed hierarchy: Jackson polymorphic typing with `@JsonTypeInfo` /
       `@JsonSubTypes`, and the security caveat on `DefaultTyping`. `[RESEARCH]` `[X-REF 13]`

*(12 leaves)*

## §2.10 Pattern matching in anger

2.10.1 Refactoring an `if`/`else if` chain of `instanceof` + cast into a pattern switch, step by
       step.
2.10.2 Replacing getter-plus-condition code with record deconstruction.
2.10.3 Guards versus nested switches: which one the dominance rules make readable.
2.10.4 Naming the total pattern instead of writing `default`, so the case is documented.
2.10.5 Handling `null` explicitly at the top of a switch, and when `case null, default ->` is right.
2.10.6 Pattern matching over a JSON-shaped sealed model (`JsonValue` → `JsonObject`, `JsonArray`,
       `JsonString`, `JsonNumber`, `JsonNull`).
2.10.7 Pattern matching inside a stream: a switch expression as the body of a `map`.
2.10.8 A pattern switch **statement** over a non-sealed type still requires a `default`. `[TRAP]`
2.10.9 Migration risk: adding a permitted subtype breaks downstream compilation, and recompiling
       only one side produces `MatchException` or `IncompatibleClassChangeError` at runtime.
       `[TRAP]` `[PROVE]`
2.10.10 Performance: a pattern switch compiles to a single `invokedynamic` `typeSwitch` returning an
        index, not a chain of `instanceof` tests. `[PROVE]`
2.10.11 The readability limit: three levels of nested deconstruction is where it stops helping.
2.10.12 Testing a pattern switch across every permitted subclass, driven by
        `getPermittedSubclasses()`. `[X-REF 16]`

*(12 leaves)*

## §2.11 Text blocks in practice

2.11.1 SQL in a text block — and why you still bind parameters rather than interpolating.
       `[X-REF 13]` `[X-REF 09]`
2.11.2 JSON fixtures in tests, with `.formatted(...)` for the varying parts. `[X-REF 16]`
2.11.3 Regex in a text block: `\` is still an escape, so every pattern backslash doubles. `[TRAP]`
2.11.4 HTML, GraphQL and YAML payloads, and the indentation discipline each needs.
2.11.5 Trailing-newline discipline when comparing a text block against a file's contents. `[TRAP]`
2.11.6 Text blocks in annotations and `case` labels, because they are constant expressions.
2.11.7 There is no interpolation in Java 21: `formatted`, `MessageFormat`, or a template library.
       String templates were previewed in 21 and 22 and then **withdrawn** in 23. `[VERSION-TRAP]`
       `[RESEARCH]`
2.11.8 When a text block is worse than a resource file: anything a non-Java tool should be able to
       lint, format or diff.

*(8 leaves)*

## §2.12 Virtual threads in production

2.12.1 The thread-per-request model restored: what actually changes in a Spring Boot service.
       `[X-REF 07]`
2.12.2 `spring.threads.virtual.enabled=true` (Spring Boot 3.2+) and what it switches — the servlet
       container's executor and `@Async`, but not everything you might assume. `[RESEARCH]`
       `[X-REF 07]`
2.12.3 Tomcat and Jetty virtual-thread executors: `maxThreads` stops being the concurrency cap,
       which means it stops being the accidental rate limiter. `[TRAP]`
2.12.4 Losing the pool means losing the queue: add a `Semaphore`, a bounded queue, or a
       rate limiter deliberately. `[TRAP]` `[X-REF 05]`
2.12.5 The new bottleneck is downstream: the JDBC connection pool, the HTTP client's connection
       limit, the database's max connections. Size them on purpose. `[TRAP]` `[X-REF 08]`
2.12.6 Drivers and libraries that use `synchronized` internally pin on Java 21 — JDBC drivers are
       the common offender. `[TRAP]` `[RESEARCH]`
2.12.7 Libraries with `ThreadLocal` caches or their own thread pools built on the assumption that
       threads are expensive.
2.12.8 Logging and MDC: MDC is a `ThreadLocal`, so it still works, but the copy cost is now per
       task. Scoped values are the eventual answer. `[X-REF 20]`
2.12.9 Thread dumps: `jcmd <pid> Thread.dump_to_file -format=json <file>` includes virtual threads
       and the structured-concurrency tree; `jstack` does not show them. `[TRAP]` `[RESEARCH]`
2.12.10 JFR events: `jdk.VirtualThreadStart` and `jdk.VirtualThreadEnd` (disabled by default),
        `jdk.VirtualThreadPinned` (enabled, 20 ms threshold), `jdk.VirtualThreadSubmitFailed`
        (enabled). `[NUM]` `[RESEARCH]` `[X-REF 20]`
2.12.11 Metrics: what a "live threads" gauge means now, and what to measure instead (in-flight
        requests, semaphore permits, pool saturation). `[X-REF 20]`
2.12.12 Memory sizing: a million virtual threads is a heap question, not a stack question. `[NUM]`
        `[X-REF 06]`
2.12.13 Debugging: breakpoints work, stepping across a mount boundary works, but the debugger's
        thread list becomes useless at scale.
2.12.14 CPU-bound work still needs a bounded executor sized to the cores. `[TRAP]`
2.12.15 The migration checklist: audit `synchronized` around blocking calls, audit `ThreadLocal`
        caches, resize downstream pools, add explicit backpressure, name your threads.
2.12.16 When not to migrate: an application that never approaches ten thousand concurrent tasks
        will see no benefit — the JDK's own guidance. `[SOURCE]`
2.12.17 Virtual threads versus reactive (WebFlux/Reactor): you regain stack traces, debuggers,
        profilers and straight-line code; you still lack declarative backpressure and operator
        fusion. `[X-REF 07]`
2.12.18 Virtual threads and `CompletableFuture`: composition is still useful, and the executor
        behind it is now cheap. `[X-REF 05]`

*(18 leaves)*

## §2.13 Structured concurrency and scoped values in practice

2.13.1 The fan-out call: two remote lookups, one deadline, one failure policy, one return.
2.13.2 Hedged requests with `ShutdownOnSuccess` against two replicas.
2.13.3 Timeouts: `joinUntil(Instant)` for the scope versus per-subtask timeouts inside each task.
2.13.4 Error handling: which exception surfaces from `throwIfFailed()`, and how to see the others
       via each `Subtask.exception()`.
2.13.5 Nesting scopes, and what the resulting task tree looks like in a JSON thread dump.
       `[RESEARCH]`
2.13.6 Scoped values for request context — tenant, principal, trace id — instead of `ThreadLocal`.
       `[X-REF 20]`
2.13.7 Rebinding: a scoped value is immutable within its scope, and a nested `where` shadows rather
       than mutates. `[PROVE]`
2.13.8 Scoped values are inherited by subtasks forked in a `StructuredTaskScope`, which is what
       makes the pair usable together. `[RESEARCH]`
2.13.9 Preview risk: the API changed in every release from 19 to 26 — do not expose it in a library
       signature. `[TRAP]` `[RESEARCH]`
2.13.10 What to actually say in an interview: name the guarantee (subtasks cannot outlive the
        block), name the comparison (`allOf` leaves orphans), name the status (preview on 21,
        reworked in 25).

*(10 leaves)*

## §2.14 Migration, 8 → 21

2.14.1 What breaks at 9: strong encapsulation of JDK internals, split packages, and the
       `--illegal-access` escape hatch that was removed in 17. `[X-REF 03]` `[X-REF 06]`
2.14.2 What breaks at 11: `java.xml.bind`, `java.activation`, CORBA and the other Java EE modules
       are gone; the `javax` → `jakarta` rename is a separate, later axis. `[RESEARCH]`
2.14.3 What breaks at 16: strong encapsulation on by default, so reflective access into
       `java.base` needs `--add-opens`. `[X-REF 06]`
2.14.4 What breaks at 17: `strictfp` becomes a no-op, the Security Manager is deprecated, and
       illegal reflective access is denied. `[X-REF 03]`
2.14.5 What breaks at 18: the default charset becomes UTF-8, so `new FileReader(f)`,
       `String.getBytes()` and `PrintStream` change behaviour silently on a non-UTF-8 platform.
       `[TRAP]` `[X-REF 03]`
2.14.6 What breaks at 21: pattern-switch exhaustiveness for previously-compiling code, and
       sequenced-collection method-name clashes for classes that already declare `getFirst`,
       `reversed` or `putFirst`. `[TRAP]` `[RESEARCH]` `[X-REF 02]`
2.14.7 The library floor: Lombok, Mockito, ByteBuddy, ASM, Groovy and Spring each have a hard
       minimum version per JDK, and bytecode-manipulating libraries fail loudest. `[X-REF 16]`
2.14.8 The mechanical refactors worth doing: anonymous class → lambda, manual loops building strings
       → `Collectors.joining`, `Date`/`Calendar` → `java.time`, `if`/`else instanceof` → pattern
       switch, hand-written value classes → records.
2.14.9 The refactors not worth doing: rewriting every loop as a stream, adopting `var` everywhere,
       converting working DTOs to records for their own sake. `[TRAP]`
2.14.10 Toolchain: `--release`, `jdeps --jdk-internals`, `jdeprscan`, and the Maven/Gradle toolchain
        declaration. `[X-REF 17]`
2.14.11 The safe rollout order: run on the new JDK with the old `--release` first, then raise the
        language level, then adopt features.
2.14.12 Performance changes to check on the way through: G1 defaults, string deduplication, compact
        strings, JIT and GC behaviour changes. `[X-REF 06]`
2.14.13 The deprecated-for-removal watch list relevant to this guide: finalization, the Security
        Manager, `sun.misc.Unsafe` memory access, the 32-bit x86 port. `[X-REF 03]`
2.14.14 A "which JDK does my team actually run" checklist, because every version-specific claim in
        an interview must be dated.

*(14 leaves)*

## §2.15 Which construct

2.15.1 Lambda, method reference, or anonymous class?
2.15.2 Stream or loop?
2.15.3 Parallel stream, your own executor, or virtual threads?
2.15.4 `Optional`, `null`, an exception, or an empty collection?
2.15.5 Record, final class, enum, or interface?
2.15.6 Sealed interface, enum, or open polymorphism?
2.15.7 Pattern switch or virtual dispatch?
2.15.8 Text block, resource file, or constant?
2.15.9 Virtual thread, platform thread, or reactive?
2.15.10 Structured concurrency, `CompletableFuture`, or `invokeAll`?

*(10 leaves)*

---

**PART 2 total: 190 leaves**

---

# PART 3 — UNDER THE HOOD

## §3.1 Lambda translation

3.1.1 `javac` desugars the lambda body into a private synthetic method named
      `lambda$<enclosingMethod>$<n>`. `[SOURCE]` `[BYTECODE]` `[RESEARCH]`
3.1.2 That method is `static` when the lambda does not capture `this`, and an instance method when
      it does. `[PROVE]` `[BYTECODE]`
3.1.3 The call site becomes `invokedynamic` with `LambdaMetafactory.metafactory` as the bootstrap
      method. `[BYTECODE]` `[SOURCE]`
3.1.4 `metafactory`'s six parameters: `MethodHandles.Lookup caller`, `String interfaceMethodName`,
      `MethodType factoryType`, `MethodType interfaceMethodType`, `MethodHandle implementation`,
      `MethodType dynamicMethodType`. `[SOURCE]` `[RESEARCH]`
3.1.5 `altMetafactory` and its flags: `FLAG_SERIALIZABLE = 1`, `FLAG_MARKERS = 2`,
      `FLAG_BRIDGES = 4`. `[SOURCE]` `[NUM]` `[RESEARCH]`
3.1.6 Static versus dynamic argument lists: the static arguments live in the constant pool; the
      captured values are the dynamic arguments pushed onto the operand stack at capture time.
      `[SOURCE]` `[RESEARCH]`
3.1.7 Therefore `factoryType`'s return type is the functional interface, and its parameter types are
      exactly the captured values — reading the `invokedynamic` descriptor tells you what was
      captured. `[PROVE]` `[BYTECODE]`
3.1.8 `InnerClassLambdaMetafactory` spins a class implementing the interface at first linkage.
      `[SOURCE]` `[RESEARCH]`
3.1.9 Since Java 15 that class is a **hidden class** (JEP 371), which replaced
      `Unsafe.defineAnonymousClass`. `[RESEARCH]` `[VERSION-TRAP]`
3.1.10 Non-capturing lambda: the spun class holds a single instance in a static field and the
       bootstrap returns a `ConstantCallSite` over it — one allocation for the life of the JVM.
       `[PROVE]` `[SOURCE]`
3.1.11 Capturing lambda: the spun class gets one field per captured value plus a constructor, and
       the `CallSite` target is that constructor — one allocation per evaluation. `[PROVE]`
3.1.12 Why not inner classes: separating the binary form (an `invokedynamic` recipe) from the
       runtime strategy lets the JDK change the strategy — to hidden classes, to Valhalla, to
       whatever — without changing a single class file. `[SOURCE]` `[RESEARCH]`
3.1.13 What that choice costs: first-call linkage latency and a JVM startup profile that is
       sensitive to the number of distinct lambda call sites. `[NUM]`
3.1.14 A method reference skips the `lambda$` method entirely — `implementation` is a direct method
       handle to the referenced method. `[BYTECODE]` `[PROVE]`
3.1.15 Serializable lambdas: the compiler emits a `$deserializeLambda$` synthetic method, capture is
       recorded in a `SerializedLambda`, and the whole path is slow, reflective, and refactoring-
       fragile. `[SOURCE]` `[TRAP]` `[RESEARCH]`
3.1.16 Bridge methods: `FLAG_BRIDGES` exists for functional interfaces that inherit generic bridge
       methods, so the spun class implements all of them. `[RESEARCH]` `[X-REF 03]`
3.1.17 Reading it yourself: `javap -c -p` on a class containing one capturing and one non-capturing
       lambda, with the `BootstrapMethods` attribute read line by line. `[BYTECODE]`
3.1.18 The runtime class name — `Foo$$Lambda/0x0000000801…` since Java 21, `Foo$$Lambda$1` before
       it — and what it tells you in a stack trace, a heap dump, or a `getClass().getName()` log.
       `[RESEARCH]` `[VERSION-TRAP]`

*(18 leaves)*

## §3.2 Lambda capture and identity

3.2.1 Capture is by value: the captured value is copied into a field of the spun instance. `[PROVE]`
3.2.2 Effectively-final is required precisely so the copy can never diverge from the original.
      `[PROVE]` `[X-REF 03]`
3.2.3 Reading an instance field inside a lambda captures `this`, not the field — so the lambda sees
      later writes to the field. `[PROVE]` `[TRAP]`
3.2.4 A lambda stored in a long-lived structure that captures `this` keeps the whole enclosing
      object alive — the listener-registry leak, identical to the anonymous-class one. `[TRAP]`
      `[PROVE]` `[X-REF 03]` `[X-REF 06]`
3.2.5 Identity: two evaluations of the same non-capturing lambda expression yield the same object;
      two evaluations of a capturing one usually do not. The specification promises **neither**.
      `[TRAP]` `[SOURCE]`
3.2.6 Consequently `==` on lambdas is meaningless, and `removeListener(x -> ...)` never removes
      anything. `[TRAP]` `[PROVE]`
3.2.7 `equals` and `hashCode` on a lambda are `Object`'s — identity based.
3.2.8 `toString()` on a lambda is `Foo$$Lambda/0x...@1b6d3586` — useless in a log, so log the intent
      instead. `[TRAP]`
3.2.9 Reflection on a lambda: `getClass().getInterfaces()` works, the implementing method does not
      appear where you expect, and there is no supported way to recover the source form.
3.2.10 The JIT: a monomorphic lambda call site inlines through the interface call; a
       lambda-heavy pipeline that goes megamorphic deoptimises and stays slow. `[X-REF 06]`

*(10 leaves)*

## §3.3 Stream pipeline internals

3.3.1 The class hierarchy: `BaseStream` → `Stream`/`IntStream`/`LongStream`/`DoubleStream`;
      `AbstractPipeline` → `ReferencePipeline`/`IntPipeline`/`LongPipeline`/`DoublePipeline`.
      `[SOURCE]`
3.3.2 `AbstractPipeline`'s fields, verbatim: `sourceStage`, `previousStage`, `sourceOrOpFlags`,
      `nextStage`, `depth`, `combinedFlags`, `sourceSpliterator`, `sourceSupplier`,
      `linkedOrConsumed`, `sourceAnyStateful`, `sourceCloseAction`, `parallel`. `[SOURCE]`
      `[RESEARCH]`
3.3.3 Every intermediate operation allocates exactly one new pipeline stage object, doubly linked to
      the previous — that is the cost of building a pipeline before any element moves. `[NUM]`
      `[PROVE]`
3.3.4 `ReferencePipeline.StatelessOp` and `ReferencePipeline.StatefulOp` as the two op base classes.
      `[SOURCE]`
3.3.5 `Sink<T> extends Consumer<T>` with `begin(long size)`, `accept(T)`, `cancellationRequested()`,
      `end()` — the four-method protocol that makes fusion and short-circuiting possible.
      `[SOURCE]`
3.3.6 `Sink.ChainedReference` as the standard downstream-forwarding base class. `[SOURCE]`
3.3.7 `opWrapSink(int flags, Sink downstream)` is where each operation's behaviour actually lives;
      `map`'s is a one-line `accept` that calls the mapper and forwards. `[SOURCE]` `[PROVE]`
3.3.8 `wrapSink` walks **backwards** from the terminal stage to depth 0, wrapping each stage's sink
      around the one after it. `[SOURCE]` `[PROVE]`
3.3.9 `copyInto(sink, spliterator)`: `begin`, `forEachRemaining`, `end` — and
      `copyIntoWithCancel` when the pipeline can short-circuit. `[SOURCE]`
3.3.10 `evaluate(TerminalOp)`: assert the shape, set `linkedOrConsumed`, then dispatch to
       `evaluateSequential` or `evaluateParallel`. `[SOURCE]`
3.3.11 That is the entire fusion story: one sink chain, one traversal, no intermediate collections.
       `[PROVE]`
3.3.12 `linkedOrConsumed` and its two messages — `"stream has already been operated upon or
       closed"` and `"source already consumed or closed"` — verbatim from the source. `[SOURCE]`
3.3.13 `StreamOpFlag`: the `DISTINCT`/`SORTED`/`ORDERED`/`SIZED`/`SHORT_CIRCUIT` bit set, each with
       SET/CLEAR/PRESERVE encodings across the stream, op and terminal-op positions. `[SOURCE]`
       `[NUM]` `[RESEARCH]`
3.3.14 How the flags let `count()` skip the pipeline: `SIZED` survives, no stateful op cleared it,
       nothing short-circuits — so the answer is the source's size. `[PROVE]` `[SOURCE]`
3.3.15 That is exactly why `peek` may never run, and exactly why the behaviour changed in Java 9.
       `[PROVE]` `[VERSION-TRAP]`
3.3.16 `sorted()` is a no-op when `SORTED` is already set with the same comparator. `[PROVE]`
       `[SOURCE]`
3.3.17 `distinct()` on a `SORTED` stream uses adjacent comparison instead of a `HashSet`. `[PROVE]`
       `[SOURCE]`
3.3.18 Lazy source binding: `sourceSupplier` versus `sourceSpliterator`, late binding, and the
       interference window that makes `ConcurrentModificationException` a terminal-time event.
       `[PROVE]` `[X-REF 02]`
3.3.19 Closing: `sourceCloseAction`, `onClose`, and the composed close chain across concatenated
       streams.
3.3.20 The file map of `java.util.stream` — about forty classes, and the five worth actually reading
       (`AbstractPipeline`, `ReferencePipeline`, `Sink`, `StreamOpFlag`, `ReduceOps`). `[RESEARCH]`

*(20 leaves)*

## §3.4 `Spliterator`

3.4.1 The interface: `tryAdvance`, `forEachRemaining`, `trySplit`, `estimateSize`,
      `getExactSizeIfKnown`, `characteristics`, `hasCharacteristics`, `getComparator`. `[SOURCE]`
3.4.2 The eight characteristics with their bit values: `ORDERED 0x10`, `DISTINCT 0x01`,
      `SORTED 0x04`, `SIZED 0x40`, `NONNULL 0x100`, `IMMUTABLE 0x400`, `CONCURRENT 0x1000`,
      `SUBSIZED 0x4000`. `[SOURCE]` `[NUM]` `[RESEARCH]`
3.4.3 `SIZED` versus `SUBSIZED`: a balanced tree reports `SIZED` (the total is known) but not
      `SUBSIZED` (the subtree sizes are not) — the javadoc's own example. `[SOURCE]` `[PROVE]`
      `[RESEARCH]`
3.4.4 `trySplit` returns null when splitting is impossible or not worthwhile, and the returned
      spliterator covers the **prefix**. `[SOURCE]`
3.4.5 `ArrayList`'s spliterator: index-range halving, `ORDERED | SIZED | SUBSIZED` — the ideal
      parallel source. `[SOURCE]` `[X-REF 02]`
3.4.6 `HashMap`'s spliterator: splits over ranges of the bucket table, `SIZED` but with unevenly
      populated halves. `[X-REF 02]`
3.4.7 `LinkedList`'s spliterator: batch-based with a doubling batch size, never `SUBSIZED`, so
      parallelism is nearly worthless. `[NUM]` `[SOURCE]` `[X-REF 02]`
3.4.8 `IteratorSpliterator` and `Spliterators.spliteratorUnknownSize` use the same batching
      fallback — this is why any `Iterator`-derived stream parallelises badly. `[NUM]`
3.4.9 `Files.lines`' spliterator and why line-oriented file input is effectively serial.
3.4.10 Late-binding spliterators and the exact window in which a concurrent modification is
       detectable. `[X-REF 02]`
3.4.11 `Spliterators.AbstractSpliterator` and `AbstractIntSpliterator` as bases for a hand-written
       one. `[BUILD]`
3.4.12 Writing a spliterator that splits well: implement `trySplit` genuinely and report
       `SIZED | SUBSIZED`. `[BUILD]` `[PROVE]`
3.4.13 `Spliterator.OfInt`/`OfLong`/`OfDouble` and the primitive traversal path.
3.4.14 The characteristics-to-optimisation map: which stream optimisation each characteristic
       unlocks, and which operation clears it. `[PROVE]`

*(14 leaves)*

## §3.5 Parallel execution internals

3.5.1 `AbstractTask`: a `CountedCompleter` that recursively splits the spliterator until each leaf
      is below a target size. `[SOURCE]`
3.5.2 `suggestTargetSize(sizeEstimate)` = `sizeEstimate / LEAF_TARGET`, rounded up — aiming at
      roughly four tasks per core. `[NUM]` `[PROVE]` `[RESEARCH]`
3.5.3 `LEAF_TARGET = ForkJoinPool.getCommonPoolParallelism() << 2`. `[NUM]` `[SOURCE]` `[RESEARCH]`
3.5.4 The op implementations: `ForEachOps`, `ReduceOps`, `FindOps`, `MatchOps`, `SliceOps`,
      `SortedOps`, `DistinctOps`, `WhileOps`, `Nodes`. `[SOURCE]`
3.5.5 `ReduceTask`: accumulate per leaf into a local container, then combine pairwise up the tree —
      which is why the combiner's cost is O(log n) merges of growing size. `[PROVE]` `[NUM]`
3.5.6 `ForEachTask` versus `ForEachOrderedTask`: the ordered variant buffers completed subtrees to
      restore encounter order. `[PROVE]` `[NUM]`
3.5.7 `SliceOps` (`limit`/`skip`) on an ordered parallel stream must count in order, so it cannot
      simply discard work. `[PROVE]`
3.5.8 `Nodes` and the flat/conc-tree node structures used to accumulate parallel results before
      flattening into an array. `[SOURCE]` `[NUM]`
3.5.9 The common pool: `ForkJoinPool.commonPool()`, parallelism `availableProcessors() - 1`, plus
      the submitting thread, so effective width equals the core count. `[NUM]` `[PROVE]`
3.5.10 Common-pool threads are daemon threads and the pool is never shut down; a task left running
       at exit is simply abandoned. `[RESEARCH]` `[TRAP]`
3.5.11 Work stealing: each worker owns a deque, pushes and pops at its own head, and steals from the
       tail of another. `[X-REF 05]`
3.5.12 `ForkJoinPool.ManagedBlocker` as the sanctioned way to block inside a ForkJoin worker, and
       the fact that parallel streams do not use it for you. `[RESEARCH]` `[X-REF 05]`
3.5.13 Exception propagation: the first exception to reach the joining task wins; the rest are
       discarded. `[TRAP]` `[PROVE]`
3.5.14 A parallel stream inside a parallel stream's lambda: nested tasks on the same pool, the
       starvation shape, and the rare true deadlock. `[TRAP]` `[PROVE]`

*(14 leaves)*

## §3.6 Collector internals

3.6.1 `Collectors.CollectorImpl<T, A, R>`: a small private class holding the five functions plus the
      characteristics set. `[SOURCE]`
3.6.2 The pre-built characteristic sets: `CH_CONCURRENT_ID`, `CH_CONCURRENT_NOID`, `CH_ID`,
      `CH_UNORDERED_ID`, `CH_UNORDERED_NOID`, `CH_NOID`. `[SOURCE]` `[NUM]` `[RESEARCH]`
3.6.3 `toList()`'s three functions: `ArrayList::new`, `List::add`, and a combiner that `addAll`s the
      right into the left. `[SOURCE]` `[PROVE]`
3.6.4 The combiner is O(size of the right half) at every merge, so parallel `collect` pays an
      O(n) copy overall — which is why it needs a large N to win. `[NUM]` `[PROVE]`
3.6.5 `groupingBy`'s implementation: a `HashMap`, `computeIfAbsent` for the container, and the
      downstream accumulator applied to it. `[SOURCE]`
3.6.6 `groupingBy`'s finisher when the downstream has one: an in-place rewrite of every map value
      through an unchecked cast — the reason the intermediate type `A` is not the result type `R`.
      `[SOURCE]` `[PROVE]`
3.6.7 `summingDouble` and `averagingDouble` accumulate into a three-element `double[]` using Kahan
      compensated summation, then add the compensation back at the end. `[SOURCE]` `[NUM]`
      `[PROVE]` `[RESEARCH]` `[X-REF 03]`
3.6.8 `averagingInt`/`summingInt` accumulate into a `long[]`, so no compensation is needed. `[SOURCE]`
3.6.9 `joining()`'s combiner appends one `StringBuilder` to another — O(n) per merge, O(n log n)
      across the tree. `[PROVE]` `[NUM]`
3.6.10 Why `IDENTITY_FINISH` matters: the framework skips the finisher entirely and returns the
       accumulation container itself, saving a full pass. `[PROVE]` `[SOURCE]`

*(10 leaves)*

## §3.7 `Optional` internals

3.7.1 The class: `public final class Optional<T>` with a single `private final T value` field and a
      `private static final Optional<?> EMPTY`. `[SOURCE]`
3.7.2 Annotated `@jdk.internal.ValueBased`, which is where the "do not synchronize, do not depend on
      identity" warnings come from. `[SOURCE]` `[RESEARCH]` `[X-REF 03]`
3.7.3 `Optional.empty()` returns the shared `EMPTY`, so `Optional.empty() == Optional.empty()` is
      true — and relying on that is exactly the identity dependence the annotation forbids.
      `[PROVE]` `[TRAP]`
3.7.4 `map` is `isEmpty() ? empty() : Optional.ofNullable(mapper.apply(value))` — one line that
      explains the null-mapper behaviour. `[SOURCE]` `[PROVE]`
3.7.5 `get()` and `orElseThrow()` have identical bodies; `get` was very nearly deprecated and was
      kept only for compatibility. `[SOURCE]` `[RESEARCH]`
3.7.6 Memory: a 16-byte object plus the reference field; escape analysis removes it in an inlined
      chain and does not when the chain is megamorphic or crosses a non-inlined boundary. `[NUM]`
      `[X-REF 06]`
3.7.7 Not `Serializable` by design, and the value-based contract means a future Valhalla value class
      can replace it without changing semantics. `[PROVE]`
3.7.8 Valhalla: `Optional` as a value class removes the allocation entirely; that is the stated
      plan, and it is the honest answer to "isn't Optional slow?". `[RESEARCH]` `[X-REF 06]`

*(8 leaves)*

## §3.8 `var` and inference internals

3.8.1 `javac` takes the initialiser's **standalone** type and then applies *upward projection* to
      remove non-denotable capture variables. `[RESEARCH]` `[PROVE]`
3.8.2 The inferred type is written into `LocalVariableTable`/`LocalVariableTypeTable` and nowhere
      else — `var` leaves no other trace in the class file. `[BYTECODE]` `[PROVE]`
3.8.3 Why `var` cannot be a field or parameter type: separate compilation would make a signature
      depend on an initialiser that is not part of the signature. `[PROVE]`
3.8.4 Upward projection worked through: `var x = list.get(0)` where `list` is `List<? extends
      Number>` infers `Number`, not the capture variable. `[RESEARCH]` `[PROVE]`
3.8.5 Poly expressions have no standalone type, which is the formal reason a lambda or method
      reference cannot initialise a `var`. `[PROVE]`
3.8.6 `var` with an anonymous class initialiser infers the anonymous type, so its extra members are
      callable — a rare legitimate use of a type you cannot write. `[PROVE]`
3.8.7 Diamond inference with no target type resolves to `Object`, which is why
      `var l = new ArrayList<>()` is `ArrayList<Object>`. `[PROVE]` `[TRAP]`
3.8.8 Surfacing the inferred type: IDE inlay hints, `javap -l`, and `-Xlint` where it applies.

*(8 leaves)*

## §3.9 Record internals

3.9.1 The class file gains a `Record` attribute containing one `record_component_info` per
      component: name index, descriptor index, and its own attributes (`Signature`,
      `RuntimeVisibleAnnotations`, `RuntimeVisibleTypeAnnotations`). `[SOURCE]` `[RESEARCH]`
3.9.2 The generated accessors are ordinary public methods; the backing fields are `private final`.
      `[BYTECODE]`
3.9.3 `equals`, `hashCode` and `toString` are emitted as `invokedynamic` to
      `java.lang.runtime.ObjectMethods.bootstrap`. `[SOURCE]` `[BYTECODE]` `[RESEARCH]`
3.9.4 `ObjectMethods.bootstrap`'s static arguments: the record class, a semicolon-separated
      component-name string, and one `MethodHandle` getter per component. `[SOURCE]` `[RESEARCH]`
3.9.5 Why `invokedynamic` rather than inline bytecode: smaller class files, and the JDK retains the
      right to change the algorithm. `[PROVE]`
3.9.6 The consequence: the `hashCode` algorithm is **unspecified** and may change between releases,
      so it must never be persisted or used across JVMs. `[TRAP]` `[PROVE]`
3.9.7 The generated `equals` compares primitives with `==`, `float`/`double` with
      `Float.compare`/`Double.compare`-style bit semantics, and references with `Objects.equals`.
      `[SOURCE]` `[PROVE]`
3.9.8 Hence `NaN` equals `NaN` and `0.0` does not equal `-0.0` inside a record, the reverse of `==`.
      `[TRAP]` `[PROVE]` `[X-REF 03]`
3.9.9 The compact constructor desugars to the canonical constructor with `this.x = x;` appended for
      every component — visible in `javap`. `[BYTECODE]` `[PROVE]`
3.9.10 Reflection: `Class.isRecord()`, `Class.getRecordComponents()`, and `RecordComponent`'s
       `getName`, `getType`, `getGenericType`, `getAccessor`, `getAnnotations`. `[RESEARCH]`
3.9.11 `java.lang.Record` is an abstract class declaring abstract `equals`, `hashCode` and
       `toString`, and it cannot be extended directly. `[SOURCE]` `[PROVE]`
3.9.12 Record serialization: the serialised form is the component values; deserialization invokes
       the canonical constructor, so validation and normalisation always run. `[SOURCE]` `[PROVE]`
       `[RESEARCH]`
3.9.13 Record serialization ignores `writeObject`, `readObject`, `readObjectNoData`, `writeExternal`,
       `readExternal` and `serialPersistentFields`; the default `serialVersionUID` is 0.
       `[SOURCE]` `[RESEARCH]` `[TRAP]` `[NUM]`
3.9.14 `setAccessible` on a record's field is blocked, so reflection-based mutation frameworks
       (some ORMs, some mocking libraries) simply do not work on records. `[TRAP]` `[RESEARCH]`

*(14 leaves)*

## §3.10 Sealed internals

3.10.1 The class file gains a `PermittedSubclasses` attribute listing the permitted classes by
       constant-pool index. `[SOURCE]` `[RESEARCH]`
3.10.2 There is no `ACC_SEALED` access flag — sealing is an attribute, and a class with the
       attribute is sealed regardless of its other modifiers. `[RESEARCH]` `[PROVE]`
3.10.3 `non-sealed` produces no attribute at all; it is a source-level acknowledgement that the
       compiler requires and then discards. `[PROVE]`
3.10.4 Load-time enforcement: the JVM checks that a subclass appears in its superclass's
       `PermittedSubclasses`, so sealing survives bytecode manipulation. `[PROVE]` `[RESEARCH]`
3.10.5 Same-module (or same-package in the unnamed module) enforcement, and where the check happens.
       `[RESEARCH]` `[X-REF 03]`
3.10.6 Narrowing reference conversion over a sealed hierarchy: `javac` can prove a cast impossible
       and reject it at compile time, which it cannot do for an open hierarchy. `[PROVE]`
       `[RESEARCH]`
3.10.7 `Class.isSealed()` and `Class.getPermittedSubclasses()`, and their use in a test that iterates
       every case. `[RESEARCH]`
3.10.8 The separate-compilation hazard: recompiling the sealed hierarchy without its switch sites
       yields `MatchException` or `IncompatibleClassChangeError` at runtime, not a link error.
       `[TRAP]` `[PROVE]`

*(8 leaves)*

## §3.11 Pattern matching internals

3.11.1 `instanceof` with a type pattern compiles to `instanceof` + `checkcast` + `astore` — no
       runtime machinery at all. `[BYTECODE]` `[PROVE]`
3.11.2 Flow scoping is a compile-time analysis in the same family as definite assignment; nothing
       about it exists at runtime. `[PROVE]` `[X-REF 03]`
3.11.3 A pattern switch compiles to `invokedynamic` against
       `java.lang.runtime.SwitchBootstraps.typeSwitch`, which returns the **index** of the first
       matching label. `[SOURCE]` `[BYTECODE]` `[RESEARCH]`
3.11.4 The bootstrap's static arguments are the label list: `Class` objects for type patterns,
       `String`/`Integer` for constants, and `EnumDesc` for qualified enum labels. `[SOURCE]`
       `[RESEARCH]`
3.11.5 The generated code then does an ordinary `tableswitch` on the returned index. `[BYTECODE]`
       `[PROVE]`
3.11.6 Cost model: the bootstrap builds a chain of method handles that tests labels in order, and
       the JIT collapses the hot ones — so a pattern switch is closer to an if-chain than to a jump
       table, but a well-optimised one. `[RESEARCH]` `[NUM]`
3.11.7 `SwitchBootstraps.enumSwitch` for switches over enum constants with qualified labels.
       `[RESEARCH]`
3.11.8 Record deconstruction compiles to accessor calls in declaration order, short-circuiting on
       the first component mismatch. `[PROVE]` `[BYTECODE]`
3.11.9 If a record accessor throws during deconstruction, the exception is wrapped in a
       `MatchException` with the original as its cause. `[RESEARCH]` `[TRAP]`
3.11.10 Exhaustiveness is computed over the transitive `permits` closure plus the declared labels;
        the algorithm lives in JLS 14.11.1.1. `[SOURCE]` `[RESEARCH]`
3.11.11 Dominance is a compile-time subsumption check over label order, specified in JLS 14.11.1.
        `[SOURCE]`
3.11.12 Null handling: the compiler emits an explicit null test before the `invokedynamic` unless a
        `case null` label is present, in which case null is routed to that index. `[PROVE]`
        `[BYTECODE]`

*(12 leaves)*

## §3.12 `switch` compilation

3.12.1 `tableswitch` versus `lookupswitch`, and the density heuristic `javac` uses to choose.
       `[BYTECODE]` `[NUM]` `[X-REF 03]`
3.12.2 `switch` on `String`: a `lookupswitch` on `hashCode`, then `equals` to confirm, then a second
       switch on a synthetic index. `[BYTECODE]` `[X-REF 03]`
3.12.3 `switch` on an enum: a synthetic `$SwitchMap$...` `int[]` mapping `ordinal()` to a stable
       case index — which exists so that reordering the enum does not silently rewire a
       separately-compiled switch. `[PROVE]` `[X-REF 03]`
3.12.4 The arrow form compiles to the same instructions as a colon form with `break` after every
       arm — there is no runtime difference. `[PROVE]` `[BYTECODE]`
3.12.5 Switch expressions and the operand stack: every arm leaves exactly one value at the join
       point. `[BYTECODE]`
3.12.6 `yield` compiles as a branch to the join point with the value on the stack.
3.12.7 An exhaustive enum switch **expression** still emits a synthetic default that throws
       `IncompatibleClassChangeError` (Java 21+; `IncompatibleClassChangeError` replaced the older
       `NoSuchFieldError`/`MatchException` shapes across releases). `[PROVE]` `[RESEARCH]` `[TRAP]`
       `[VERSION-TRAP]`
3.12.8 Why that guard exists: an enum constant added after your class was compiled would otherwise
       fall off the end of an expression that must produce a value. `[PROVE]`

*(8 leaves)*

## §3.13 Text block compilation

3.13.1 A text block is a constant expression: the entire transformation happens in `javac` and
       nothing survives to runtime. `[PROVE]` `[BYTECODE]`
3.13.2 The three-step algorithm as specified: normalise line terminators, remove incidental white
       space, interpret escape sequences — in that order and no other. `[SOURCE]`
3.13.3 The exact minimal-indent computation: blank lines are excluded from the minimum, the closing
       delimiter's line is included, and trailing whitespace is removed from every line first.
       `[PROVE]` `[SOURCE]`
3.13.4 The result is a `CONSTANT_String_info` in the constant pool, and therefore interned.
       `[PROVE]` `[X-REF 03]`
3.13.5 `String.stripIndent()` implements the same algorithm at runtime, minus the closing-delimiter
       line. `[SOURCE]`
3.13.6 A text block and an equal string literal are `==` because both are interned constants — the
       one case where `==` on strings is reliable, and still not a habit to build. `[PROVE]`
       `[TRAP]` `[X-REF 03]`

*(6 leaves)*

## §3.14 Virtual thread internals

3.14.1 The three layers: `java.lang.VirtualThread`, `jdk.internal.vm.Continuation`, and the
       scheduler. `[RESEARCH]`
3.14.2 `Continuation`: `enter`/`yield`, with the JVM copying stack frames between the carrier's
       stack and a heap-resident `StackChunk`. `[RESEARCH]` `[PROVE]`
3.14.3 Mount copies frames from the heap chunk onto the carrier stack; unmount copies them back.
       Lazy/partial copying is what keeps the common case cheap. `[NUM]` `[RESEARCH]`
3.14.4 `VirtualThread`'s state machine: `NEW`, `STARTED`, `RUNNABLE`, `RUNNING`, `PARKING`,
       `PARKED`, `PINNED`, `YIELDING`, `TERMINATED`. `[RESEARCH]`
3.14.5 The default scheduler is a `ForkJoinPool` created in FIFO async mode, with parallelism equal
       to `availableProcessors()` and a `maxPoolSize` defaulting to 256. `[NUM]` `[RESEARCH]`
3.14.6 `jdk.virtualThreadScheduler.parallelism` and `jdk.virtualThreadScheduler.maxPoolSize`, and
       how to confirm the effective values at runtime. `[NUM]` `[RESEARCH]`
3.14.7 Why FIFO rather than the LIFO work-stealing used for parallel streams: virtual threads are
       independent tasks, not recursively split subtasks, so fairness matters more than locality.
       `[PROVE]`
3.14.8 The instrumented blocking points, enumerated: `java.net` sockets, NIO channels and
       `Selector`, `HttpClient`, `Thread.sleep`, `LockSupport.park`, `java.util.concurrent` locks
       and queues, `Process.waitFor`. `[X-REF 05]`
3.14.9 The non-instrumented ones: most file I/O (delegated to a carrier or an internal pool),
       `Object.wait` before Java 24, and any JNI frame. `[TRAP]` `[RESEARCH]`
3.14.10 Stack chunks live in the heap and are ordinary garbage-collected objects — which is why a
        million threads is a heap-sizing exercise, not a virtual-address-space one. `[NUM]`
        `[X-REF 06]`
3.14.11 `Thread.currentThread()` inside a virtual thread returns the `VirtualThread`; the carrier is
        only reachable through internal API. `[RESEARCH]`
3.14.12 Thread-local storage is per virtual thread, so a `ThreadLocal` cache is now a per-task cache
        with per-task allocation. `[NUM]` `[PROVE]`
3.14.13 Pinning is a property of the continuation: it cannot yield while a native frame or a held
        monitor is on its stack. `[PROVE]` `[RESEARCH]`
3.14.14 JEP 491 (Java 24) makes object monitors continuation-aware, so `synchronized` no longer
        pins; native frames still do. Every "use ReentrantLock" answer must be dated. `[VERSION-TRAP]`
        `[RESEARCH]`
3.14.15 `-Djdk.tracePinnedThreads` was introduced by JEP 444 and is superseded by the
        `jdk.VirtualThreadPinned` JFR event, which carries both the pinning reason and the carrier's
        identity. `[RESEARCH]` `[VERSION-TRAP]`
3.14.16 Thread dumps: `jcmd <pid> Thread.dump_to_file -format=json` includes virtual threads and
        the structured-concurrency tree, but omits object addresses, lock information and JNI
        statistics. `[RESEARCH]` `[TRAP]`
3.14.17 There is no preemption: a CPU-bound virtual thread holds its carrier until it blocks or
        finishes, so one runaway loop can occupy a core indefinitely. `[TRAP]` `[PROVE]`
3.14.18 Compensation: the carrier pool may grow toward `maxPoolSize` when threads pin or use a
        `ManagedBlocker`, which is why the pool has a max at all. `[RESEARCH]` `[NUM]`

*(18 leaves)*

## §3.15 Structured concurrency and scoped values internals

3.15.1 `StructuredTaskScope` is built on virtual threads plus a per-thread scope stack; every `fork`
       starts one virtual thread. `[RESEARCH]`
3.15.2 The ownership check: `fork`, `join`, `shutdown` and `close` must all be called by the owning
       thread. `[RESEARCH]`
3.15.3 `StructureViolationException` and the stack-discipline invariant that scopes must close in
       reverse order of opening. `[RESEARCH]`
3.15.4 Cancellation: `shutdown()` interrupts every unfinished subtask and prevents further forks;
       `close()` then joins. `[PROVE]`
3.15.5 `ScopedValue`'s implementation: an immutable linked binding snapshot per thread plus a small
       fixed-size per-thread cache keyed by the value's hash. `[RESEARCH]` `[NUM]`
3.15.6 Why scoped values are cheaper than `ThreadLocal`: no map, no `remove()` discipline, no
       inheritance copy — the bindings are shared structurally and unbound by stack unwinding.
       `[PROVE]` `[RESEARCH]`
3.15.7 Inheritance into forked subtasks is what makes scoped values and structured concurrency a
       pair rather than two independent features. `[RESEARCH]`
3.15.8 The version-by-version API churn table for both features, 19 → 26, so any code sample can be
       dated. `[RESEARCH]` `[VERSION-TRAP]`

*(8 leaves)*

## §3.16 Version-by-version delta

3.16.1 Java 8 (2014): lambdas, method references, functional interfaces, streams, default and static
       interface methods, `Optional`, `java.time`, `CompletableFuture`, `StringJoiner`, `Base64`,
       `Arrays.parallelSort`, repeating and type annotations, PermGen replaced by Metaspace,
       Nashorn. `[RESEARCH]` `[X-REF 03]` `[X-REF 06]`
3.16.2 Java 9: JPMS, `List/Set/Map.of`, `Optional.stream/or/ifPresentOrElse`,
       `Stream.takeWhile/dropWhile/ofNullable/iterate(3)`, private interface methods, JShell, jlink,
       `Flow`, `VarHandle`, `StackWalker`, compact strings, indified concatenation, G1 by default,
       `finalize` deprecated.
3.16.3 Java 10: `var`, `List/Set/Map.copyOf`, `Collectors.toUnmodifiable*`,
       `Optional.orElseThrow()`, application class-data sharing, parallel full GC for G1.
3.16.4 Java 11 (LTS): `HttpClient`, `String.isBlank/lines/strip/repeat`,
       `Files.readString/writeString`, `Predicate.not`, `var` in lambda parameters, single-file
       source launch, ZGC and Epsilon experimental, Java EE and CORBA modules removed, Nashorn
       deprecated, Flight Recorder open-sourced.
3.16.5 Java 12: `Collectors.teeing`, `String.indent/transform`, `Files.mismatch`, Shenandoah,
       switch expressions (preview), `CompactNumberFormat`.
3.16.6 Java 13: text blocks (preview), switch expressions (second preview), dynamic CDS archives,
       ZGC uncommit.
3.16.7 Java 14: switch expressions **final**, records (preview), pattern `instanceof` (preview),
       helpful NPE messages, JFR event streaming, `jpackage` (incubator), CMS removed.
3.16.8 Java 15: text blocks **final**, sealed (preview), records (second preview), hidden classes
       (JEP 371), ZGC and Shenandoah production, EdDSA, Nashorn removed, helpful NPE on by default.
       `[RESEARCH]`
3.16.9 Java 16: records **final**, pattern `instanceof` **final**, `Stream.toList`,
       `Stream.mapMulti`, static members in inner classes, strong encapsulation by default,
       Unix-domain sockets, `jpackage` final, Vector API and FFM incubating. `[RESEARCH]`
3.16.10 Java 17 (LTS): sealed classes **final**, pattern switch (preview), `RandomGenerator`
        (JEP 356), always-strict floating point (JEP 306), context-specific deserialization
        filters, Security Manager deprecated, applet API deprecated, macOS/AArch64 port.
        `[RESEARCH]`
3.16.11 Java 18: UTF-8 by default (JEP 400), simple web server, `@snippet` in javadoc, internet
        address resolution SPI, finalization deprecated for removal (JEP 421), pattern switch
        (second preview). `[RESEARCH]`
3.16.12 Java 19: virtual threads (preview), structured concurrency (incubator), record patterns
        (preview), pattern switch (third preview), FFM (preview), Linux/RISC-V port.
3.16.13 Java 20: all four re-previewed; scoped values (incubator); no final language features.
3.16.14 Java 21 (LTS): virtual threads **final**, record patterns **final**, pattern matching for
        switch **final**, sequenced collections, generational ZGC, key encapsulation API; preview:
        string templates, structured concurrency, scoped values, unnamed patterns and variables,
        unnamed classes and instance `main`. `[RESEARCH]`
3.16.15 Java 22: unnamed variables and patterns **final**, FFM **final**, multi-file source launch,
        statements before `super()` (preview), stream gatherers (preview), string templates
        (second preview), region pinning for G1. `[RESEARCH]`
3.16.16 Java 23: string templates **withdrawn**, gatherers (second preview), primitive types in
        patterns (preview), Markdown javadoc, generational ZGC by default, `sun.misc.Unsafe`
        memory-access methods deprecated (JEP 471). `[RESEARCH]`
3.16.17 Java 24: stream gatherers **final** (JEP 485), JEP 491 removes `synchronized` pinning,
        Class-File API **final**, scoped values and structured concurrency re-previewed, AOT class
        loading and linking, compact object headers (experimental), Security Manager permanently
        disabled (JEP 486). `[RESEARCH]`
3.16.18 Java 25 (LTS): scoped values **final** (JEP 506), compact source files and instance `main`
        **final** (JEP 512), module import declarations **final** (JEP 511), flexible constructor
        bodies **final** (JEP 513), structured concurrency fifth preview (JEP 505), primitive types
        in patterns third preview (JEP 507), stable values (preview), PEM encodings, generational
        Shenandoah. `[RESEARCH]`
3.16.19 Still in flight as of this file's date: structured concurrency (sixth/seventh preview via
        JEP 525/533), primitive patterns, stable values, Valhalla value classes, derived record
        creation, and a redesigned string-template proposal. `[RESEARCH]`
3.16.20 The consolidated feature → version table, so every claim in this guide can be dated in one
        lookup.
3.16.21 The consolidated removed-or-disabled table: Nashorn, Java EE modules, CORBA, applets,
        Security Manager, finalization, the 32-bit x86 port, `Unsafe` memory access.
3.16.22 How to answer "what is new in Java N" in an interview: three features, the problem each
        solves, one trap each, and the release you personally run in production.

*(22 leaves)*

## §3.17 Observability and tooling

3.17.1 `javap -c -p -v` for every desugaring claim in this part: the lambda indy, the record indy,
       the pattern-switch indy, and the text block constant. `[BYTECODE]`
3.17.2 `jshell` for a ten-second experiment: `peek` elision, `Optional.empty()` identity, text-block
       indentation, `Stream.toList` immutability.
3.17.3 `-Djdk.internal.lambda.dumpProxyClasses=<dir>` to write the spun lambda classes to disk and
       decompile them. `[RESEARCH]` `[VERSION-TRAP]`
3.17.4 `-Xlog:class+load=info` to watch the hidden classes appear at the first invocation of each
       lambda call site. `[X-REF 06]`
3.17.5 JFR for this topic: `jdk.VirtualThreadStart/End/Pinned/SubmitFailed`, plus
       `jdk.ObjectAllocationSample` for boxing and `jdk.JavaExceptionThrow`. `[X-REF 20]`
3.17.6 `jcmd <pid> Thread.dump_to_file -format=json <file>` for virtual threads and scope trees.
       `[RESEARCH]`
3.17.7 `jcmd <pid> Thread.print` for platform threads, monitors and deadlock detection. `[X-REF 06]`
3.17.8 async-profiler, and the frame names you will actually see for lambdas, stream stages and
       ForkJoin leaves. `[X-REF 06]`
3.17.9 JMH for every stream-versus-loop or parallel-versus-sequential claim: warm-up, forks,
       `Blackhole`, and why a microbenchmark without them lies. `[X-REF 16]`
3.17.10 IDE support worth using: IntelliJ's stream debugger and "trace current stream chain", and
        the inlay hints that show a `var`'s inferred type.
3.17.11 Static analysis for this topic: ErrorProne (`OptionalUsedAsFieldOrParameterType`,
        `StreamResourceLeak`, `ReturnValueIgnored`, `OptionalNotPresent`), SpotBugs, SonarQube's
        stream and `Optional` rules, NullAway. `[RESEARCH]`
3.17.12 Confirm before you quote: `-XX:+PrintFlagsFinal` for VM flags,
        `System.getProperties()` for the scheduler properties,
        `ForkJoinPool.getCommonPoolParallelism()` for the pool width. `[X-REF 06]`

*(12 leaves)*

---

**PART 3 total: 210 leaves**

---

# PART 4 — BUILD IT

Every item is `[BUILD]`: complete, compiling, generic Java 21, followed by a **Diff vs the real one**
table covering at minimum edge cases, intrinsics, serialization, null policy, thread safety,
allocation tricks, and why the JDK bothers.

## §4.1 A functional toolkit from scratch

4.1.1 `MyFunction<T,R>` with `andThen`, `compose` and `identity`, plus a harness that proves the
      two composition orders differ. `[PROVE]`
4.1.2 `MyPredicate<T>` with `and`, `or`, `negate`, `not`, and a short-circuit demonstration using a
      side-effecting predicate. `[PROVE]`
4.1.3 `CheckedFunction<T,R,E extends Exception>` plus `unchecked(...)` and `sneaky(...)` adapters,
      used to put an `IOException`-throwing call inside a `map`. `[X-REF 03]`
4.1.4 A `Result<T,E>` sealed interface with `Ok` and `Err` records, `map`/`flatMap`/`fold`/
      `orElseThrow`, as the type-level alternative to checked exceptions in a pipeline.
4.1.5 A memoizing `Function` decorator over a `ConcurrentHashMap`, including the
      `computeIfAbsent`-recursion deadlock and its fix. `[TRAP]` `[PROVE]` `[X-REF 05]`
4.1.6 A curry/partial-application helper for `BiFunction`, with an honest note on when it stops
      being readable.
4.1.7 A `TriFunction` the JDK does not provide, and the argument for why the JDK stops at two.
4.1.8 Diff vs `java.util.function`: 43 interfaces, the primitive specialisations,
      `@FunctionalInterface` enforcement, the deliberate absence of a checked variant, and why
      arity stops at two.

*(8 leaves)*

## §4.2 `MyStream` — a lazy fused pipeline

4.2.1 `MySink<T>` with `begin(long)`, `accept(T)`, `cancellationRequested()`, `end()`.
4.2.2 `MyStream<T>` over an iterator source, with `filter`, `map` and a terminal `forEach`, fused
      through a sink chain rather than staged through collections.
4.2.3 Proving fusion: a print statement in each stage, showing interleaved per-element traversal
      rather than three sequential passes. `[PROVE]`
4.2.4 Adding `limit` and `findFirst` via `cancellationRequested`, proving short-circuiting on an
      infinite source. `[PROVE]`
4.2.5 Adding `sorted` as a stateful barrier, and demonstrating exactly where laziness stops.
      `[PROVE]`
4.2.6 Adding a `linkedOrConsumed` flag and reproducing
      `IllegalStateException: stream has already been operated upon or closed`. `[PROVE]`
4.2.7 A minimal flags mechanism (`SIZED`) that lets `count()` bypass the pipeline — reproducing the
      real `peek`-elision behaviour in fifty lines. `[PROVE]`
4.2.8 A trivial parallel evaluation over a splittable array source with a leaf-size threshold and
      `ForkJoinTask`. `[NUM]`
4.2.9 A JMH comparison of `MyStream`, `java.util.stream`, and a plain `for` loop over 1 000 000
      elements. `[NUM]`
4.2.10 Diff vs `java.util.stream`: four stream shapes, thirty-odd operations, the full
       `StreamOpFlag` lattice, the `Spliterator` contract, ForkJoin integration, primitive
       specialisation, closing, and exception semantics.

*(10 leaves)*

## §4.3 Collectors from scratch

4.3.1 `MyCollector<T,A,R>` mirroring the five-function contract and the characteristics set.
4.3.2 `toList`, `joining` and `groupingBy` implemented on it, with correct combiners.
4.3.3 A bounded top-N collector over a `PriorityQueue`, with a combiner that merges two heaps
      correctly. `[PROVE]` `[X-REF 02]`
4.3.4 A frequency/mode collector returning a record of `(value, count)`.
4.3.5 A boxing-free statistics collector over a `long[]` accumulator, benchmarked against
      `Collectors.summarizingInt`. `[NUM]`
4.3.6 A `CONCURRENT` collector plus a harness proving it only reduces concurrently when all three
      conditions hold. `[PROVE]`
4.3.7 Diff vs `java.util.stream.Collectors`: `CollectorImpl`, the pre-built characteristic sets,
      Kahan compensated summation, the `IDENTITY_FINISH` fast path, and the unchecked casts the JDK
      uses to keep `A` hidden.

*(7 leaves)*

## §4.4 `MyOptional`

4.4.1 `MyOptional<T>` with `of`, `ofNullable`, `empty`, `map`, `flatMap`, `filter`, `or`, `stream`,
      `ifPresent`, `ifPresentOrElse`, `orElse`, `orElseGet`, `orElseThrow` ×2.
4.4.2 A shared `EMPTY` instance, and a demonstration that `empty() == empty()` — followed by the
      argument for why you must not depend on it. `[PROVE]`
4.4.3 A counter-based harness proving `orElse` evaluates eagerly and `orElseGet` does not. `[PROVE]`
4.4.4 An allocation count for a five-`map` chain, run with and without `-XX:-DoEscapeAnalysis`.
      `[NUM]` `[PROVE]`
4.4.5 A null-returning mapper, matched against the JDK's `empty()` behaviour. `[PROVE]`
4.4.6 Diff vs `java.util.Optional`: `@ValueBased`, the absence of `Serializable`, the primitive
      variants, the intended-use API note, and the Valhalla trajectory.

*(6 leaves)*

## §4.5 Records, sealed types and patterns from scratch

4.5.1 The hand-written pre-record equivalent of a three-component record — constructor, accessors,
      `equals`, `hashCode`, `toString`, defensive copies — counted in lines against the one-line
      record. `[NUM]` `[PROVE]`
4.5.2 A record with a `List` component written three ways — no copy, copy-in only, copy-in and
      copy-out — each with a mutation test that either passes or fails. `[PROVE]` `[TRAP]`
4.5.3 A record with an array component demonstrating the `equals`/`hashCode` failure, then the
      `List` fix, then the `Arrays.equals` override if the array is unavoidable. `[PROVE]`
4.5.4 A `sealed interface Shape` with record cases, an exhaustive pattern switch, and the exact
      compile error produced when a fourth case is added. `[PROVE]`
4.5.5 The same hierarchy expressed as a Visitor, side by side, with a line count and a "where do I
      edit to add a case / add an operation" table. `[PROVE]`
4.5.6 An expression-tree interpreter over a sealed record hierarchy using nested deconstruction and
      guards.
4.5.7 A reflective "wither" helper built from `getRecordComponents()` and the canonical constructor
      — and the argument for why you should not ship it. `[TRAP]`
4.5.8 Diff vs the compiler's output: the `Record` attribute, `ObjectMethods` indy,
      `PermittedSubclasses`, `SwitchBootstraps.typeSwitch` indy, and `MatchException`.

*(8 leaves)*

## §4.6 Concurrency builds

4.6.1 A blocking echo server written twice — one platform thread per connection, then one virtual
      thread per connection — measured at 1, 1 000 and 50 000 concurrent connections. `[NUM]`
      `[PROVE]`
4.6.2 A pinning reproducer: `synchronized` around a blocking sleep, run on Java 21 with
      `-Djdk.tracePinnedThreads=full`, the output read line by line, then the `ReentrantLock` fix
      and the re-measurement. `[PROVE]` `[TRAP]`
4.6.3 A `ThreadLocal`-cache memory harness at 10 000 and 1 000 000 virtual threads, with heap
      numbers. `[NUM]`
4.6.4 A `Semaphore`-bounded virtual-thread client demonstrating precisely what removing the thread
      pool removed. `[PROVE]`
4.6.5 A fan-out written with `StructuredTaskScope.ShutdownOnFailure` and again with
      `CompletableFuture.allOf`, with a deliberate failure, showing the orphaned task in one and
      not the other. `[PROVE]` `[TRAP]`
4.6.6 A hedged request with `ShutdownOnSuccess` against two simulated backends of different
      latency.
4.6.7 A common-pool starvation reproducer: one blocking parallel stream and one innocent one, both
      timed, then the same with a dedicated executor. `[PROVE]` `[TRAP]`
4.6.8 Diff vs the JDK: `Continuation` and `StackChunk`, the FIFO ForkJoin scheduler, the JEP 505
      `Joiner` API shape, `ManagedBlocker`, and the JFR instrumentation.

*(8 leaves)*

## §4.7 Filling the Java 21 gaps

4.7.1 A fixed-window batching intermediate operation on Java 21 via a custom `Spliterator`, matching
      what `Gatherers.windowFixed` does in Java 24. `[RESEARCH]`
4.7.2 A `zip` over two streams via a paired spliterator, with the correct `estimateSize` and no
      `SUBSIZED` claim.
4.7.3 A running-total `scan` via a stateful mapper, with the explicit warning that it is illegal in
      parallel — and a demonstration of it producing wrong answers there. `[TRAP]` `[PROVE]`
4.7.4 `distinctBy(keyExtractor)` via a `Set`-capturing predicate, with the same warning and the same
      demonstration. `[TRAP]` `[PROVE]`
4.7.5 A `takeUntil`, and a `mapConcurrent` equivalent built on virtual threads plus a semaphore.
4.7.6 Diff vs `Gatherers` (Java 24): the `Gatherer` contract (`initializer`, `integrator`,
      `combiner`, `finisher`), greedy versus short-circuiting integrators, and the built-ins
      `fold`, `scan`, `windowFixed`, `windowSliding`, `mapConcurrent`. `[RESEARCH]`

*(6 leaves)*

## §4.8 Diagnostic harnesses

4.8.1 A fifteen-snippet puzzler set, each printing something surprising with the mechanism named:
      `peek` elision, stream reuse, `toList` immutability, `toMap` null value, `groupingBy` null
      key, `orElse` eagerness, `Optional.empty()` identity, `var` diamond, record array `equals`,
      pattern-switch NPE, text-block indentation, bound method-reference NPE, `allMatch` on an
      empty stream, `IntStream.sum` overflow, parallel `forEach` corruption. `[PROVE]`
4.8.2 A stream-versus-loop JMH benchmark at N = 10, 1 000 and 1 000 000, boxed and primitive.
      `[NUM]` `[X-REF 16]`
4.8.3 A parallel-versus-sequential JMH sweep across N and per-element cost, locating the crossover
      empirically rather than quoting the rule of thumb. `[NUM]` `[PROVE]`
4.8.4 A source-splitting benchmark: `int[]`, `ArrayList`, `LinkedList`, `HashSet`, `Files.lines` and
      `IntStream.range`, all under `.parallel()`. `[NUM]` `[PROVE]`
4.8.5 A lambda-startup harness with 1, 100 and 10 000 distinct call sites, measuring class-loading
      count and first-call latency. `[NUM]` `[PROVE]`
4.8.6 A capturing-versus-non-capturing lambda identity and allocation harness. `[PROVE]` `[NUM]`
4.8.7 A `javap` walk of one class containing a lambda, a method reference, a record, a pattern
      switch and a text block, reading each `BootstrapMethods` entry. `[BYTECODE]` `[PROVE]`
4.8.8 A collector-combiner cost harness: `toList` versus `joining` versus `groupingBy` in parallel
      at increasing N. `[NUM]`
4.8.9 An exhaustiveness-drift harness: compile a switch, add a permitted subtype, recompile only the
      hierarchy, and catch the resulting `MatchException` / `IncompatibleClassChangeError`.
      `[PROVE]` `[TRAP]`
4.8.10 A record-serialization harness proving the canonical constructor runs on deserialization and
       that validation cannot be bypassed — contrasted with the same class written as a plain class.
       `[PROVE]`
4.8.11 A text-block indentation harness printing each result with visible markers for four different
       closing-delimiter positions. `[PROVE]`
4.8.12 A migration smoke harness: the same program compiled with `--release` 8, 11, 17 and 21,
       diffing observable behaviour (default charset, NPE messages, `toList` mutability, iteration
       order of `Set.of`). `[PROVE]` `[NUM]`

*(12 leaves)*

---

**PART 4 total: 65 leaves**

---

# PART 5 — INTERVIEW AND RETENTION

## §5.1 The questions, with the answer shape

5.1.1 "What is a functional interface? Does it need `@FunctionalInterface`?"
5.1.2 "`Comparator` declares two abstract-looking methods — why is it still functional?"
5.1.3 "Is a lambda just syntactic sugar for an anonymous inner class?" — the 30-second and the
      5-minute answer.
5.1.4 "What bytecode does a lambda compile to? Walk me through the `invokedynamic`."
5.1.5 "What is `LambdaMetafactory` and when does it run?"
5.1.6 "Is the same lambda expression the same object every time?"
5.1.7 "What does `this` mean inside a lambda?"
5.1.8 "Why must a captured local be effectively final?"
5.1.9 "How do I increment a counter from inside a lambda?" — and why the question is the bug.
5.1.10 "Name the four kinds of method reference and give an example of each."
5.1.11 "When does a bound method reference evaluate its receiver?"
5.1.12 "How do you throw a checked exception from inside a `map`?"
5.1.13 "What is a stream, and how is it different from a collection?"
5.1.14 "Explain laziness. What runs when, in `list.stream().filter(f).map(g).findFirst()`?"
5.1.15 "Does a stream process stage by stage or element by element? Prove it."
5.1.16 "Can you reuse a stream? What exactly happens if you try?"
5.1.17 "What does `peek` do and when is it not called?"
5.1.18 "Which stream operations are stateful, and why does that matter?"
5.1.19 "What is encounter order, and which operations depend on it?"
5.1.20 "Difference between `findFirst` and `findAny`?"
5.1.21 "What does `allMatch` return on an empty stream?"
5.1.22 "`map` vs `flatMap` vs `mapMulti`."
5.1.23 "`takeWhile` vs `filter`."
5.1.24 "How would you batch a stream into windows of 100 on Java 21?"
5.1.25 "How would you zip two streams?"
5.1.26 "`collect(toList())` vs `stream.toList()` — name three differences."
5.1.27 "What does `Collectors.toMap` do on a duplicate key? On a null value?"
5.1.28 "What map and list types does `groupingBy` return?"
5.1.29 "`groupingBy(p)` vs `partitioningBy(p)` — what is different about the empty case?"
5.1.30 "Write a collector that gives the top 3 by salary per department."
5.1.31 "Explain the `Collector` contract's five functions."
5.1.32 "When is `reduce` wrong and `collect` right?"
5.1.33 "Why must a `reduce` combiner be associative?"
5.1.34 "How does a parallel stream decide how many tasks to create?"
5.1.35 "Which thread pool does a parallel stream use, and how big is it?"
5.1.36 "What happens if I do blocking I/O inside a parallel stream?"
5.1.37 "Can I give a parallel stream my own pool? Is that supported?"
5.1.38 "When is a parallel stream faster? Give me the four conditions."
5.1.39 "Why is `parallelStream().forEach(list::add)` broken but `collect(toList())` fine?"
5.1.40 "What is a `Spliterator` and what do its characteristics do?"
5.1.41 "Why does a `LinkedList` parallelise badly?"
5.1.42 "What is `Optional` for, and where should it never appear?"
5.1.43 "`orElse` vs `orElseGet` — show me the bug."
5.1.44 "Why is `isPresent()` + `get()` an anti-pattern?"
5.1.45 "Why is `Optional` not `Serializable`?"
5.1.46 "What happens if `map`'s function returns null?"
5.1.47 "Is `Optional.empty() == Optional.empty()` true? Should you rely on it?"
5.1.48 "What is `var`, and where can you not use it?"
5.1.49 "Does `var` have a runtime cost?"
5.1.50 "What does `var list = new ArrayList<>()` infer?"
5.1.51 "Why can't you write `var f = () -> 1;`?"
5.1.52 "What does a record generate for you?"
5.1.53 "What is a compact constructor and what is it for?"
5.1.54 "Are records immutable?"
5.1.55 "Why is an array component in a record a bug?"
5.1.56 "How do you make a record with a `List` component genuinely immutable?"
5.1.57 "Can you persist a record's `hashCode`?"
5.1.58 "Can a record be a JPA entity? Why not?"
5.1.59 "How does record deserialization differ from ordinary Java serialization?"
5.1.60 "How are a record's `equals`/`hashCode`/`toString` actually implemented in bytecode?"
5.1.61 "What does `sealed` do, and what must every permitted subtype declare?"
5.1.62 "Can an anonymous class be a permitted subtype?"
5.1.63 "What is the difference between `sealed` and `final`?"
5.1.64 "Sealed interface or enum — how do you choose?"
5.1.65 "What does a sealed hierarchy buy a `switch`?"
5.1.66 "Why would you deliberately omit `default` from a switch?"
5.1.67 "What is flow scoping? Why is `s` in scope after `if (!(o instanceof String s)) return;`?"
5.1.68 "What happens when a pattern switch gets a null?"
5.1.69 "What is `MatchException` and when have you seen one?"
5.1.70 "Explain dominance. Why must a guarded case come first?"
5.1.71 "What are record patterns and how deep can they nest?"
5.1.72 "How does a pattern switch compile? Is it a chain of `instanceof`?"
5.1.73 "Switch statement vs switch expression — name three differences."
5.1.74 "`yield` vs `return` inside a switch."
5.1.75 "What is `$SwitchMap` and why does it exist?"
5.1.76 "How does a text block decide indentation?"
5.1.77 "What does `\\s` do in a text block, and why would you need it?"
5.1.78 "Are text blocks interned?"
5.1.79 "Does Java have string interpolation?"
5.1.80 "What is a virtual thread and how is it scheduled?"
5.1.81 "Walk me through mounting and unmounting."
5.1.82 "What is pinning? What causes it on Java 21, and what changed in 24?"
5.1.83 "How do you detect pinning in production?"
5.1.84 "Should you pool virtual threads?"
5.1.85 "Do virtual threads help CPU-bound work?"
5.1.86 "You removed the thread pool. What did you also remove?"
5.1.87 "What breaks in a Spring Boot app when you turn virtual threads on?"
5.1.88 "How many virtual threads can you create, and what limits it?"
5.1.89 "What does `ThreadLocal` cost now?"
5.1.90 "What is structured concurrency and what does it guarantee?"
5.1.91 "How is `StructuredTaskScope` different from `CompletableFuture.allOf`?"
5.1.92 "Is structured concurrency final? What changed in 25?"
5.1.93 "What are scoped values and why not just use `ThreadLocal`?"
5.1.94 "What are sequenced collections and which types got them?"
5.1.95 "What is the single most useful thing added between Java 8 and 21, and why?"

*(95 leaves)*

## §5.2 The trap index

5.2.1 One table of every `**Trap:**` in the file: the wrong belief, the symptom you would see in
      production, and the fix — usable as a single pre-interview scan.
5.2.2 The version-stale claims table: `synchronized` pins virtual threads (fixed in 24), guarded
      patterns use `&&` (became `when` in 21), record patterns work in enhanced `for` (removed
      before 21 shipped), string templates are coming (withdrawn in 23),
      `StructuredTaskScope.fork` returns a `Future` (it returns `Subtask` since 21),
      `ShutdownOnFailure` is the API (replaced by `Joiner` in 25), `ScopedValue.runWhere` exists
      (removed in 24), `peek` always runs (elidable since 9), `flatMap` cannot short-circuit (fixed
      in 10), the default charset is platform-dependent (UTF-8 since 18), `Foo$$Lambda$1` naming
      (changed in 21).
5.2.3 The five most expensive real-world mistakes from this guide: blocking I/O in a parallel
      stream, mutable state in a record component, `Optional` in an entity field, pooling virtual
      threads, and shipping a public API over a preview feature.
5.2.4 The five most common interview-losing wrong answers: "a lambda is an anonymous class",
      "streams are faster than loops", "parallel streams use all your cores so they are free",
      "records are immutable", "virtual threads make everything faster".
5.2.5 The five claims that are true but must be dated: pinning, the toList mutability rule, the
      default charset, the exhaustiveness rules, and the structured-concurrency API shape.

*(5 leaves)*

## §5.3 One-line assertions and drills

5.3.1 The numbers drill: recite every constant with its value — 43 function interfaces, 30
      collectors / 54 overloads, common-pool parallelism `n − 1`, `LEAF_TARGET = parallelism << 2`,
      the 20 ms `VirtualThreadPinned` threshold, `maxPoolSize` 256, class-file majors 52/55/61/65,
      the eight spliterator characteristic bits, `FLAG_SERIALIZABLE = 1`.
5.3.2 The mechanism drill: explain in one sentence each — `invokedynamic`, `LambdaMetafactory`,
      hidden class, `Sink`, `StreamOpFlag`, `Spliterator.trySplit`, `CollectorImpl`,
      `ObjectMethods.bootstrap`, `PermittedSubclasses`, `SwitchBootstraps.typeSwitch`,
      `Continuation`, `StackChunk`, `MatchException`, `StructureViolationException`.
5.3.3 The code-reading drill: ten snippets, say what each prints and why it is not what it looks
      like.
5.3.4 The "which construct" drill: fifteen scenarios → the right feature, one line each.
5.3.5 The symptom drill: given a symptom (a request storm that pegs one core, a corrupted list after
      a refactor, an `UnsupportedOperationException` after a library upgrade, a duplicate-key
      `IllegalStateException` at 3 a.m., a `MatchException` after a partial redeploy), name the
      mechanism.
5.3.6 The dating drill: for each of ten features, state the release it became final and the release
      it was first previewed.
5.3.7 The refactor drill: rewrite five imperative snippets as streams, then argue which two should
      be left alone.
5.3.8 Spaced-repetition schedule for this file: day 1 read, day 3 checklist, day 7 numbers and
      mechanism drills, day 14 code-reading and symptom drills, day 21 build two items from Part 4.
5.3.9 `## Atomic concept checklist` — every one of the 25 existing checklist lines from the current
      guide, preserved verbatim in substance, plus one line per new concept in this syllabus.

*(9 leaves)*

---

**PART 5 total: 109 leaves**

---

## Leaf counts

| Part | Leaves |
|---|---|
| PART 1 — Basics | 410 |
| PART 2 — Intermediate | 190 |
| PART 3 — Under the hood | 210 |
| PART 4 — Build it | 65 |
| PART 5 — Interview & retention | 109 |
| **Total** | **984** |

Leaves carrying `[RESEARCH]`: **202**.
Leaves carrying `[VERSION-TRAP]`: **22**.
Leaves carrying `[TRAP]`: ~**135**. `[PROVE]`: ~**150**. `[SOURCE]`: ~**75**.
`[BYTECODE]`: ~**30**. `[NUM]`: ~**85**.
`[BUILD]`: **65** (all of Part 4), plus 1.2.20, 1.10.24, 1.13.17, 2.2.9, 2.2.11, 2.2.12, 2.5.8,
2.5.9, 2.8.13, 3.4.11, 3.4.12.

**Every one of these 984 leaves must appear in the notes**, or be listed in a `## Deferred` block
with the leaf number and a one-line reason.

---

# DIAGRAM MANIFEST

**182 diagrams (D-001 … D-182).** Every one must exist as a standalone SVG file in
`src/notes/detailed/04-modern-java/diagrams/`, named `D-NNN-short-slug.svg`, embedded at the point
of explanation with a Markdown image reference and a caption carrying the stable id, e.g.
`**D-028** — Why `peek` may never run`. Where the `Type` column says `table`, a Markdown table is
the correct rendering and no SVG file is required.

Rules the manifest assumes and you must follow:

- One idea per diagram. Prefer more, smaller diagrams over one dense one.
- Where the `Must show` column asks for *frames*, produce that many clearly separated,
  individually labelled panels inside the one SVG, each captioned with the frame number and what
  changed since the previous frame.
- Every label, constant and value named in `Must show` must be visible as text in the SVG. A
  diagram that omits a named value does not satisfy the manifest.
- Arrows must be directional, orthogonal, and labelled where the direction is not obvious.
- Every diagram is drawn on QuizStakes data. Where the `Must show` cell names domain values
  (`CLIENT_BONUS_AVAILABLE`, `AA-801`, a 3.33 stake, 2.8M stake reservations), use those exact
  values.
- Never inline `<svg>` in the Markdown. Never draw with ASCII characters.

## Part 1 diagrams

| # | Diagram | Syllabus leaf | Type | Must show |
|---|---|---|---|---|
| D-001 | The release train and where 21 sits | 1.1.1–1.1.3 | timeline | A horizontal axis from Java 8 (March 2014) to Java 25 with a tick every six months; LTS releases 8, 11, 17, 21, 25 as taller marks with their dates; the six-month cadence labelled "JEP 322"; the features this guide owns pinned to their final release (lambdas/streams 8, `var` 10, switch expressions 14, text blocks 15, records 16, sealed 17, pattern switch and virtual threads and record patterns 21, gatherers 24, scoped values 25) |
| D-002 | Three maturity ladders: preview, incubator, experimental | 1.1.5–1.1.7 | table | Rows: preview language/API feature, incubator module, experimental VM option. Columns: how you enable it (`--enable-preview` at compile *and* run, `--add-modules jdk.incubator.x`, `-XX:+UnlockExperimentalVMOptions`), what the class file records (minor version 65535 for preview, nothing for the others), whether it runs on a *different* release, and the guide's example of each (structured concurrency 21, Vector API 21, generational ZGC 21) |
| D-003 | Class-file major versions and `UnsupportedClassVersionError` | 1.1.10 | table | Rows for Java 8/9/11/17/21/25 with major versions 52/53/55/61/65/69; a column showing the exact `UnsupportedClassVersionError` text for a class compiled at 65 run on a 55 JVM, with both numbers highlighted; a final column giving the `java -version`/`Runtime.version()` check |
| D-004 | `--release` restricts the API; `-source`/`-target` do not | 1.1.9 | before-after | Left: `javac -source 8 -target 8` on `BalanceView` calling `List.of(...)` — compiles clean, then `NoSuchMethodError` at runtime on a Java 8 JVM, with the error text. Right: `javac --release 8` on the same source — a compile error naming `List.of` as not available at release 8. Label which of the two the build should use |
| D-005 | The six function shapes and their narrowings | 1.2.8, 1.2.9 | hierarchy | `Function<T,R>`, `BiFunction<T,U,R>`, `Predicate<T>`, `Consumer<T>`, `Supplier<T>` as roots; `UnaryOperator<T> extends Function<T,T>` and `BinaryOperator<T> extends BiFunction<T,T,T>` drawn as arrows to their parents; each box carries its abstract method signature and one QuizStakes instantiation (`Function<LedgerEntry, Money>`, `Predicate<Restriction>`, `Supplier<IdempotencyKey>`) |
| D-006 | The 43 interfaces of `java.util.function` | 1.2.7, 1.2.13 | table | Every one of the 43 names grouped by shape family (Function, BiFunction, Predicate, Consumer, Supplier, Operator) with columns for the object form and each primitive specialisation (`IntX`, `LongX`, `DoubleX`, `ToIntX`, `XToYFunction`, `ObjIntConsumer`, `BooleanSupplier`). The total 43 stated in the caption |
| D-007 | `andThen` and `compose` run in opposite orders | 1.2.11 | step-sequence, 2 frames | One `Function<Money, Money> applyFee` and one `Function<Money, Money> applyRounding` over a 3.33 stake. Frame 1: `applyFee.andThen(applyRounding)` — arrows showing fee first, then rounding, with the intermediate value. Frame 2: `applyFee.compose(applyRounding)` — rounding first, then fee, with a different intermediate and a different result. Both final values printed |
| D-008 | What counts toward the single abstract method | 1.2.1–1.2.5 | decision-tree | Root: "is this method abstract?" Branches: overrides a public `Object` method (`equals`, `hashCode`, `toString`) → does not count, with `Comparator` named; `default`/`static`/`private` → does not count; declares its own type parameters → counts but makes the interface unusable as a lambda target; otherwise → counts. Leaf boxes state "functional" / "not functional" / "functional but not lambda-implementable" |
| D-009 | Every lambda syntax form | 1.3.1–1.3.4, 1.3.20 | table | Rows: `() -> expr`, `x -> expr`, `(x, y) -> expr`, `(Type x) -> {...}`, `(var x) -> ...`, `(final @NonNull var x) -> ...`, block body with `return`. Columns: since which release, parameter typing (implicit/explicit/`var`), whether mixing is allowed, and a QuizStakes example for each |
| D-010 | A lambda is a poly expression | 1.3.5–1.3.8 | before-after | The same source text `r -> r.amount().compareTo(MAX_STAKE) > 0` used at three sites with three different target types (`Predicate<Reservation>`, a custom `StakeRule`, a `Function<Reservation, Boolean>` that does *not* compile). Beside them: `Object o = () -> {};` marked "compile error: target type is not a functional interface" and `Object o = (Runnable) () -> {};` marked "compiles". Each site annotated with the target type that supplied the interface |
| D-011 | `this` in a lambda versus an anonymous class | 1.3.10, 1.3.11 | before-after | The same `Runnable` registered from inside `BonusService`, written twice. Left, anonymous class: `this` points at the anonymous instance, plus a synthetic `this$0` arrow to `BonusService`; generated name `BonusService$1`. Right, lambda: `this` points straight at the `BonusService` instance, no extra object; synthetic method `lambda$register$0`. Both arrows labelled |
| D-012 | Capture is by value, and only of effectively-final locals | 1.3.13, 3.2.1–3.2.3 | memory-layout | A stack frame for `FundsLedger.reserveStake` holding `Money stake` (effectively final) and `this`; the spun lambda object on the heap with one field per captured value; an arrow from the field to the same `Money` object. A second panel: an instance field `dailyTotal` read inside the lambda — no field copy, only a `this` capture, so a later write to `dailyTotal` *is* visible. Both cases annotated with "copied at capture" / "read through `this` at invocation" |
| D-013 | Which loop variable is capturable | 1.3.15 | before-after | Left: `for (int i = 0; i < 3; i++)` — one variable, reassigned, so `i` is not effectively final and the lambda does not compile; the single slot drawn once with three values over time. Right: `for (Reservation r : reservations)` — a fresh variable per iteration, three separate slots, three lambdas each capturing its own. The compile error text quoted on the left |
| D-014 | Four ways to mutate from inside a lambda, and the one that is right | 1.3.14 | table | Rows: one-element array hack, `AtomicInteger`, `reduce`, a collector, a plain loop. Columns: compiles, thread-safe in parallel, allocation cost, readability, verdict. The QuizStakes case is counting reservations over `STAKE_BLOCKED` clients |
| D-015 | The six method-reference forms | 1.4.1–1.4.7 | table | Rows: `Type::staticMethod`, `instance::method`, `Type::instanceMethod`, `Type::new`, `String[]::new`, `super::method`, `Outer.this::method`. Columns: the equivalent lambda written out, what the receiver is, when the receiver is evaluated, and a QuizStakes example (`Money::of`, `ledger::append`, `Reservation::amount`, `StakeSplit::new`) |
| D-016 | Unbound receiver becomes the first parameter | 1.4.4 | before-after | Left: `Reservation::amount` as a `Function<Reservation, Money>` — the arrow showing the stream element becoming the receiver. Right: the equivalent lambda `r -> r.amount()` with the same arrow. A third panel shows `Money::compareTo` as a `Comparator`-shaped two-argument function, first argument receiver, second argument parameter |
| D-017 | A bound method reference evaluates its receiver at capture time | 1.4.10, 1.4.11 | timeline | Three points on one axis: (1) `Runnable r = ledger::flush` evaluates `ledger` now and stores the reference; (2) `ledger = otherLedger` reassigns the *variable*, not the captured value; (3) `r.run()` still calls `flush` on the original object. A second lane repeats it with `ledger = null` before the reference is created, and the NPE thrown at point (1) with nothing ever invoked |
| D-018 | Stream anatomy: source, intermediates, terminal | 1.5.3, 1.5.4 | step-sequence, 3 frames | A pipeline over 95k card deposits: `deposits.stream().filter(...).map(...).collect(toList())`. Frame 1: the source `Spliterator` bound. Frame 2: two stage objects created, nothing traversed, "0 elements have moved" labelled. Frame 3: the terminal operation triggers traversal. Each frame lists which objects exist so far |
| D-019 | Fusion: one element through the whole chain | 1.5.5, 3.3.11 | before-after | Left, the wrong mental model: three passes over the whole collection with two intermediate lists materialised, sizes labelled. Right, the real model: one element at a time entering `filter`, then `map`, then the collector, with a numbered trace for the first three deposits (65, 480, 65) and no intermediate collection anywhere |
| D-020 | Laziness, statefulness and short-circuiting, per operation | 1.5.4, 1.5.6, 1.5.7, 1.7.18, 1.7.19 | table | One row per intermediate operation. Columns: lazy (always yes), stateless/stateful, short-circuiting, buffering required, encounter-order sensitive. A second block does terminal operations with eager/lazy and short-circuiting |
| D-021 | A stream is consumed once | 1.5.13, 3.3.12 | state-transition | Three states — unconsumed, linked (an intermediate op attached), consumed/closed — with the transitions labelled by the call that causes them and the two exact exception messages on the illegal edges: `"stream has already been operated upon or closed"` and `"source already consumed or closed"` |
| D-022 | Which streams must be closed | 1.5.14, 1.5.15, 1.6.10 | decision-tree | Root: "does the source hold an OS resource?" Yes branch lists `Files.lines`, `Files.walk`, `Files.list`, `Files.find`, `Files.newDirectoryStream` → try-with-resources required, with the file-descriptor leak as the symptom. No branch lists `Collection.stream`, `Arrays.stream`, `IntStream.range` → closing is a no-op. `onClose(Runnable)` shown on the yes branch |
| D-023 | The stream source catalogue | 1.6.1–1.6.17 | table | One row per source. Columns: since which release, finite/infinite, ordered, `SIZED`/`SUBSIZED`, split quality (excellent/good/serial), needs closing, and the QuizStakes use (`ledgerEntries.stream()`, `IntStream.range(0, 2_800_000)`, `Files.lines(paymentRunFile)`) |
| D-024 | `Stream.concat` in a loop builds a left-deep tree | 1.6.7 | before-after | Left: five successive `concat` calls drawn as a left-leaning binary tree five levels deep, with the recursion depth labelled and `StackOverflowError` at traversal. Right: the same five sources collected into a `List` and flat-mapped, one level deep. Depths written on both |
| D-025 | Intermediate operation inventory | 1.7.24 | table | One row per intermediate operation (`filter`, `map`, the four `mapToX`, `boxed`, `flatMap`, the three `flatMapToX`, `mapMulti` and its three primitive forms, `distinct`, `sorted` ×2, `limit`, `skip`, `takeWhile`, `dropWhile`, `peek`, `parallel`, `sequential`, `unordered`, `onClose`). Columns: version added, stateful, short-circuiting, and its effect (SET/CLEAR/PRESERVE) on each of `SIZED`, `ORDERED`, `DISTINCT`, `SORTED` |
| D-026 | `map` vs `flatMap` vs `mapMulti` | 1.7.2, 1.7.4, 1.7.6, 1.7.7 | step-sequence, 3 frames | The same input of three `Movement`s each holding zero, one or three `LedgerEntry` values. Frame 1: `map` produces three `List`s — cardinality 1:1. Frame 2: `flatMap` allocates one inner `Stream` per element and flattens — the three allocations drawn explicitly. Frame 3: `mapMulti` pushes into a `Consumer` with zero allocations — the same output. Allocation counts written on each frame |
| D-027 | `takeWhile` is a prefix, `filter` is a test | 1.7.13 | before-after | The same ordered input of stake amounts `[4.20, 3.33, 12.00, 2.10, 1.05]` with the predicate `amount < 5`. Left, `filter`: output `[4.20, 3.33, 2.10, 1.05]`, every element tested. Right, `takeWhile`: output `[4.20, 3.33]`, traversal stops at 12.00 — the stop point marked and the untested elements greyed with a label |
| D-028 | Why `peek` may never run | 1.7.16, 3.3.14, 3.3.15 | flowchart | Decision nodes for `count()`: is `SIZED` still set? did any stateful op clear it? does anything short-circuit? If all clear, the answer comes from the source's size and the sink chain is never built — the `peek` consumer boxed and marked "never called". A parallel branch shows the same pipeline with a `filter` added, clearing `SIZED`, and `peek` running. A VERSION TRAP banner: always ran before Java 9 |
| D-029 | Operation order changes both the answer and the cost | 1.7.20, 2.3.8 | before-after | Left: `.sorted(byAmount).limit(10)` over 2.8M stake reservations — the full buffer and sort drawn, cost O(n log n), elements buffered = 2.8M. Right: `.limit(10).sorted(byAmount)` — a different answer, the ten elements shown. A third panel: `filter` before `map` versus after, with the number of mapper invocations counted for both |
| D-030 | `sorted()` is a barrier | 1.7.9, 1.7.10 | step-sequence, 3 frames | Frame 1: elements streaming into `sorted` and accumulating in its buffer, downstream stages idle. Frame 2: source exhausted, TimSort runs over the full buffer. Frame 3: elements released downstream. A side panel: a non-`Comparable` element producing `ClassCastException` at frame 2 — i.e. at terminal time, not at the `sorted()` call site |
| D-031 | Terminal operation inventory | 1.8.26 | table | One row per terminal operation. Columns: version added, return type, eager or lazy, short-circuiting, parallel-friendly, ordering-sensitive, returns `Optional` and why |
| D-032 | The three `reduce` overloads | 1.8.6–1.8.8 | table | Rows: `reduce(BinaryOperator)`, `reduce(identity, BinaryOperator)`, `reduce(identity, accumulator, combiner)`. Columns: return type, what the empty stream yields, the contracts you must satisfy (identity, associativity, compatibility of accumulator and combiner), and the QuizStakes example (summing `Money` over a day's 95k deposits) |
| D-033 | What a non-associative reduce does in parallel | 1.8.9, 1.8.10 | step-sequence, 3 frames | Subtraction over `[65, 480, 42, 180]`. Frame 1: the sequential left fold with its result. Frame 2: the same operator split across two leaves and combined, with the different result written out. Frame 3: the same argument for string concatenation with a non-identity seed. Both wrong answers and the correct sequential answers labelled |
| D-034 | `findFirst` versus `findAny` in parallel | 1.8.14, 1.8.15, 3.5.7 | before-after | A four-leaf task tree over 2.8M reservations. Left, `findAny`: the first leaf to succeed wins and the rest cancel — no coordination arrows. Right, `findFirst`: leaves must report in encounter order, so later leaves' results are held until earlier leaves resolve — the coordination arrows drawn and labelled with the cost |
| D-035 | Null policy across the list-producing paths | 1.8.25, 2.1.7, 2.5.11 | table | Rows: `Stream` elements, `Stream.toList()`, `Collectors.toList()`, `Collectors.toUnmodifiableList()`, `Collectors.toMap` key, `Collectors.toMap` value, `List.of`, `List.copyOf`, `Arrays.asList`, `new ArrayList<>()`. Columns: nulls permitted, mutable, structurally modifiable, `set` in place, exception thrown on violation |
| D-036 | The four stream shapes and the conversions between them | 1.9.1, 1.9.3, 1.9.4, 1.7.3 | hierarchy | Four boxes — `Stream<T>`, `IntStream`, `LongStream`, `DoubleStream` — with every conversion arrow labelled by its method (`mapToInt`, `mapToObj`, `boxed`, `asLongStream`, `asDoubleStream`, `mapToLong`, `mapToDouble`). A note box: no `CharStream`, `BooleanStream` or `FloatStream`, and which primitives widen into which |
| D-037 | `int[]` versus `List<Integer>` for 2.8M stake amounts | 1.9.14, 1.9.10 | memory-layout | Top: `int[] stakeMinorUnits = new int[2_800_000]` — 16-byte header plus 11.2 MB contiguous. Bottom: the boxed equivalent — a 24-byte list, a 16-byte array header, 11.2 MB of 4-byte references, and 2.8M × 16-byte `Integer` objects. Both totals and the ratio written out |
| D-038 | `IntStream.sum()` overflows silently | 1.9.11 | step-sequence, 3 frames | Summing 2.8M stake amounts in minor units. Frame 1: the running `int` total approaching 2 147 483 647. Frame 2: the wrap to a negative value, with the exact arithmetic. Frame 3: `mapToLong(i -> i).sum()` producing the correct total. All three totals printed |
| D-039 | The `Collector` contract's five functions | 1.10.1, 1.10.2, 3.6.1 | step-sequence, 4 frames | A `groupingBy(deposit -> deposit.rail(), counting())` over card and bank deposits. Frame 1: `supplier()` creates the container. Frame 2: `accumulator()` folds each element in. Frame 3: `combiner()` merges two containers in the parallel case. Frame 4: `finisher()` transforms to the result type, with `IDENTITY_FINISH` shown as the skip path. The three `Characteristics` values listed in a legend |
| D-040 | Collector inventory | 1.10.29, 1.10.3 | table | One row per collector factory across all 30 names and 54 overloads. Columns: version added, result type, mutability of the result, null policy, characteristics, parallel behaviour, and the one trap if it has one |
| D-041 | What `groupingBy` actually returns | 1.10.17, 1.10.18, 3.6.5 | memory-layout | The result of `groupingBy(Deposit::rail, mapping(Deposit::amount, toList()))` over card and bank deposits: a `HashMap` with its bucket table, two entries, each value an `ArrayList`. Both concrete types labelled "not guaranteed by the contract", with `TreeMap::new` and `LinkedHashMap::new` drawn as the ordered alternatives |
| D-042 | `partitioningBy` always has both keys | 1.10.21 | before-after | Over an empty stream of reservations. Left, `groupingBy(r -> r.amount().compareTo(MAX) > 0)`: an empty map, `get(true)` returns null. Right, `partitioningBy(...)`: a two-entry map with `false → []` and `true → []`. The NPE the left produces on unboxing drawn as the consequence |
| D-043 | The three conditions for a concurrent reduction | 1.10.25, 1.10.20, 2.4.13 | decision-tree | Root: `collect` called. Node 1: is the stream parallel? Node 2: is the collector `CONCURRENT`? Node 3: is the stream unordered *or* the collector `UNORDERED`? All three yes → one shared container, no combiner. Any no → per-leaf containers and a combiner tree. Both outcomes drawn with their container counts |
| D-044 | Why `collect(toList())` is safe in parallel and `forEach(list::add)` is not | 1.10.26, 2.4.11, 2.4.12 | before-after | Left: four leaves each with their own `ArrayList`, merged pairwise up a combiner tree — no shared state, arrows labelled with sizes. Right: four leaves all calling `add` on one `ArrayList`, with the three observable symptoms named: lost elements, interspersed nulls, and `ArrayIndexOutOfBoundsException` from inside `ArrayList.add` |
| D-045 | `Optional`'s API by version | 1.11.5–1.11.10 | table | One row per method across all 20. Columns: signature, release added (15 at 1.8, `ifPresentOrElse`/`or`/`stream` at 9, `orElseThrow()` at 10, `isEmpty` at 11), eager or lazy in its argument, what it does on empty, and whether it is on `OptionalInt`/`OptionalLong`/`OptionalDouble` too |
| D-046 | `orElse` evaluates eagerly even when the value is present | 1.11.11, 2.6.3 | step-sequence, 2 frames | A `findClient(id)` returning a present `Optional`. Frame 1: `orElse(loadDefaultFromDatabase())` — the database call runs first, its result is discarded, with a call counter showing 1. Frame 2: `orElseGet(this::loadDefaultFromDatabase)` — the supplier is never invoked, counter 0. Both results identical; both costs different |
| D-047 | Where `Optional` belongs | 1.11.1, 1.11.14–1.11.18, 2.6.1 | decision-tree | Root: "where does this Optional live?" Branches: return type → correct; field → wrong (not `Serializable`, extra indirection), use null or a default; parameter → wrong, overload instead; collection element → wrong, filter it out; map value → wrong, omit the key; `Optional<List<T>>` → wrong, return an empty list. Every wrong leaf carries the replacement |
| D-048 | The `Optional` chain versus the null check | 1.11.13, 1.11.21, 2.6.2 | before-after | Left: nested `if (x != null)` navigation from `Client` → `Account` → `Wallet` → `Money`, four levels. Right: `findClient(id).map(Client::account).map(Account::wallet).map(Wallet::withdrawable).orElse(Money.ZERO)`. Beneath, the anti-pattern `if (opt.isPresent()) opt.get()` marked as the left-hand version plus one allocation |
| D-049 | Where `var` is legal and where it is not | 1.12.3, 1.12.4 | table | Rows: local with initialiser, enhanced-`for` variable, classic `for` index, try-with-resources resource, lambda parameter, field, method parameter, return type, `catch` parameter, local without initialiser, `var x = null`, array-initialiser shorthand, generic type argument. Columns: legal, since which release, the compile error text where illegal, and the reason in one clause |
| D-050 | `var` plus the diamond infers `Object` | 1.12.7, 3.8.7 | before-after | Left: `var positions = new ArrayList<>();` inferring `ArrayList<Object>`, with the later `positions.get(0).amount()` compile error shown. Right: `var positions = new ArrayList<Position>();` inferring `ArrayList<Position>`. The inference step drawn: no target type → the diamond resolves to `Object` |
| D-051 | What a record generates | 1.13.3, 1.13.4, 1.13.6 | before-after | Left: `record StakeSplit(Money bonusPortion, Money cashPortion) {}` — one line. Right: everything the compiler adds: two `private final` fields, the canonical constructor, two accessors named `bonusPortion()`/`cashPortion()`, `equals`, `hashCode`, `toString`, the implicit `final`, and `extends java.lang.Record`. Each generated member labelled with its exact signature |
| D-052 | The compact constructor desugars | 1.13.9, 1.13.10, 3.9.9 | before-after | Left: the compact form validating that `bonusPortion.add(cashPortion)` equals the stake and normalising scale, with the parameters reassigned. Right: the desugared canonical constructor with the same body plus `this.bonusPortion = bonusPortion; this.cashPortion = cashPortion;` appended. An error panel: assigning the field instead of the parameter inside the compact form, and the compile error |
| D-053 | A record is shallowly immutable | 1.13.16, 1.13.17, 2.8.13 | step-sequence, 3 frames | `record PaymentRun(RunId id, List<WithdrawalTransaction> items)`. Frame 1: constructed from a caller-held `ArrayList` — one list object, two references. Frame 2: the caller mutates their list; the record's contents change. Frame 3: the fix — `List.copyOf` in the compact constructor, drawn as a separate list object, plus copy-out with `clone()` for an array component |
| D-054 | An array component breaks `equals` | 1.13.18, 4.5.3 | before-after | Left: `record Batch(byte[] payload)` with two instances holding equal contents — `equals` false, hashes differ, the reference comparison labelled. Right: the same with `List<Byte>` (or a `record` wrapping `ByteBuffer`) — `equals` true. A third panel: the hand-written `Arrays.equals` override if the array is unavoidable |
| D-055 | The record cliff | 1.13.27, 1.13.28, 2.8.16 | decision-tree | Root: "should this be a record?" Branches for needing a mutable field, an internal representation different from the API, inheritance, a no-arg constructor for a framework — each terminating in "not a record, and you lose every generated member at once", with JPA entities named. The yes-leaves list DTOs, value objects, compound map keys, multiple return values, sealed cases, pipeline scratch types |
| D-056 | A sealed hierarchy | 1.14.1, 1.14.2, 1.14.9, 1.14.10 | hierarchy | `sealed interface Verdict permits DocumentVerdict, ScreeningVerdict, ReviewVerdict, WealthVerdict`, each permitted subtype a record with its components listed. Each subtype box labelled `final`. A legend maps the shape to "sum type" for the interface and "product type" for each record |
| D-057 | Every permitted subtype must choose one of three modifiers | 1.14.3, 1.14.4, 1.14.7, 1.14.8 | decision-tree | Root: a permitted subtype. Three legal branches: `final` (closed), `sealed` (closed with its own permits list), `non-sealed` (reopened). A fourth branch — no modifier — ends in the compile error, quoted. Two further error leaves: an anonymous or local class (no canonical name to write in `permits`) and a grandchild that does not *directly* extend the sealed type |
| D-058 | Sealed interface vs enum vs open polymorphism | 1.14.11, 1.14.18, 2.9.9 | table | Rows: closed set of instances vs closed set of types vs open, per-case data, exhaustiveness in a switch, who can add a case, cost of adding a case, cross-module extensibility, reflection support. Columns: enum, sealed interface, `final` class, package-private constructor, open interface. The QuizStakes mapping: `RestrictionType` as an enum, `Verdict` as sealed |
| D-059 | Sealing is a module/package boundary | 1.14.6, 1.14.15, 3.10.5 | before-after | Left: sealed type and permitted subtypes in the same named module — compiles. Right: a permitted subtype in another module — compile error, text quoted. A third panel for the unnamed module, where the rule becomes same-package. A note: you cannot permit a type you do not control |
| D-060 | A pattern is a test, an extraction and a binding | 1.15.1, 1.15.2, 1.15.22 | before-after | Left: the pre-16 form — `if (v instanceof DocumentVerdict) { DocumentVerdict d = (DocumentVerdict) v; ... }` with the three steps numbered. Right: `if (v instanceof DocumentVerdict d)` with the same three steps collapsed, and below it the record-pattern form `if (v instanceof DocumentVerdict(var outcome, var reason, var at, var by))` |
| D-061 | Flow scoping is not a block rule | 1.15.3–1.15.5 | flowchart | Four panels over one method. (1) `if (v instanceof DocumentVerdict d) { … }` — `d` in scope inside. (2) `if (!(v instanceof DocumentVerdict d)) return;` — `d` in scope for the *rest of the method*, that region shaded. (3) `x instanceof T t && t.foo()` — in scope on the right of `&&`. (4) `x instanceof T t || t.foo()` — not in scope, compile error quoted. Each panel annotates "where the compiler can prove the test succeeded" |
| D-062 | How a pattern switch routes a value, including null | 1.15.7, 1.15.8, 3.11.12 | flowchart | Entry with the selector. First decision: is the selector null? If a `case null` label exists → that arm. If not → `NullPointerException` thrown before any label is tested, drawn explicitly. Otherwise → the `typeSwitch` indy returns an index → `tableswitch` → the arm. `case null, default ->` shown as a merged target |
| D-063 | Dominance and label order | 1.15.18–1.15.20 | before-after | Left: `case Verdict v ->` written before `case DocumentVerdict d ->` — compile error, text quoted, the general label shown swallowing the specific one. Right: the specific label first, compiling. A third panel: a guarded case `case DocumentVerdict d when d.outcome() == REFERRED` placed before its unguarded twin, with the note that the guard removes it from dominance analysis. A fourth: a total type pattern plus `default` — compile error |
| D-064 | Nested record deconstruction | 1.15.11, 1.15.12, 2.10.11 | hierarchy | `case Movement(LedgerEntry(Position from, Money amount), LedgerEntry(Position to, Money _))` drawn as a tree from the outer record down to each bound variable, with each accessor call labelled on its edge in declaration order. A depth marker at level three labelled "the readability limit" |
| D-065 | The pattern-matching lineage | 1.15.2, 1.15.6, 1.15.10, 1.15.13, 1.15.24 | timeline | An axis from Java 14 to Java 25 with three tracks: `instanceof` patterns (JEP 305 preview 14, 375 second preview 15, 394 final 16), pattern switch (17, 18, 19, 20 previews, JEP 441 final 21), record patterns (JEP 405 preview 19, 432 preview 20, 440 final 21). Two removal/withdrawal markers: record patterns in enhanced-`for` removed before 21, `&&` guards replaced by `when` at 21. A "still preview" column for primitive patterns (JEP 455/507) |
| D-066 | Switch forms compared | 1.16.1–1.16.11, 1.16.16 | table | Rows: colon statement, arrow statement, colon expression with `yield`, arrow expression. Columns: fall-through, produces a value, `break` allowed, `yield` allowed, `return` allowed, exhaustiveness required, mixing allowed with the others. The QuizStakes example is dispatching on `RestrictionType` |
| D-067 | Fall-through, and how the arrow form makes it unwritable | 1.16.2, 1.16.17 | before-after | Left: a colon switch over restriction sources with a missing `break`, the execution path falling through two arms drawn as one continuous arrow, and the wrong outcome named. Right: the same logic in arrow form, one arm executed, no `break` written or needed |
| D-068 | Exhaustive enum switch expression versus one with `default` | 1.16.6, 1.16.15, 3.12.7, 3.12.8 | before-after | Left: an exhaustive switch expression over `RestrictionType` with no `default`; adding `DORMANT_FROZEN` to the enum produces a compile error, quoted. Right: the same with `default ->`; adding the constant compiles and silently takes the default. A third panel shows the synthetic default the compiler still emits, throwing `IncompatibleClassChangeError` when the enum changed after separate compilation |
| D-069 | The three text-block compile steps, in order | 1.17.4, 1.17.11, 3.13.2 | step-sequence, 3 frames | A SQL text block reading `CLIENT_CASH_AVAILABLE` positions. Frame 1: CRLF line terminators normalised to `\n`, both forms shown as visible characters. Frame 2: incidental whitespace removed. Frame 3: escape sequences translated, with a `\n` the author wrote surviving frame 1 untouched and a `\s` surviving frame 2. Order labelled "and no other order" |
| D-070 | How incidental whitespace is computed | 1.17.6, 1.17.8, 3.13.3 | step-sequence, 4 frames | A four-line JSON fixture. Frame 1: trailing whitespace stripped from every line, the stripped characters marked. Frame 2: blank lines excluded from the minimum. Frame 3: the closing delimiter's line *included* in the minimum, its indentation marked. Frame 4: the common prefix removed, the result shown with a left margin ruler and column numbers |
| D-071 | Moving the closing delimiter changes the string | 1.17.7 | before-after | The same SQL text block drawn twice with a column ruler: closing `"""` aligned with the content, and closing `"""` four columns to the left. The two resulting strings printed with a visible left-margin marker per line and the extra four spaces highlighted |
| D-072 | `\s` as a trailing-space fence | 1.17.9, 1.17.10 | before-after | A fixed-width payload line whose trailing spaces are significant. Left: without `\s` — the trailing spaces stripped, the field width wrong, both lengths printed. Right: with `\s` at the end — the space survives, the width correct. A second row shows `\` at end of line suppressing the terminator |
| D-073 | Platform thread versus virtual thread | 1.18.1, 1.18.10, 3.14.10 | memory-layout | Left: a platform thread — an OS thread, a 1 MB reserved stack outside the heap, a `Thread` object. Right: a virtual thread — a `VirtualThread` object of a few hundred bytes plus a growable `StackChunk` on the heap, mounted on a carrier that is itself a platform thread. Byte figures on both, and 55k peak concurrent sessions costed each way |
| D-074 | Mounting and unmounting | 1.18.7, 3.14.2, 3.14.3 | step-sequence, 4 frames | A virtual thread calling the card PSP with a p50 of 240 ms. Frame 1: mounted, frames on the carrier's stack. Frame 2: the blocking socket read triggers `Continuation.yield`; frames copied to the heap `StackChunk`. Frame 3: the carrier picks up a different virtual thread — the carrier reused, labelled. Frame 4: the response arrives, frames copied back, execution resumes on a possibly *different* carrier |
| D-075 | The carrier pool | 1.18.5, 1.18.6, 3.14.5–3.14.7 | memory-layout | The default scheduler as a `ForkJoinPool` in FIFO async mode; parallelism = `availableProcessors()`; `maxPoolSize` (**verify the 256 default before printing it**); `jdk.virtualThreadScheduler.parallelism` and `jdk.virtualThreadScheduler.maxPoolSize` labelled on the boxes they control; a queue of runnable virtual threads feeding the carriers FIFO, with a note contrasting the LIFO work-stealing used by parallel streams |
| D-076 | Little's law sets the thread count | 1.18.3 | cost-curve | Concurrency = throughput × latency plotted for QuizStakes: 1,200 stake reservations/sec at a 240 ms p50 needs 288 concurrent tasks; at the 11 s p99 it needs 13,200. A horizontal line at a 200-thread platform pool shows where throughput is capped; the virtual-thread line has no cap in that range. All four numbers written on the plot |
| D-077 | Pinning on Java 21 | 1.18.21–1.18.23, 3.14.13 | before-after | Left: a virtual thread blocking inside a `synchronized` block in a JDBC driver — the continuation cannot yield, the carrier is held, other virtual threads queue behind it; `-Djdk.tracePinnedThreads=full` output shown. Right: the same code with `ReentrantLock` — the thread unmounts and the carrier is freed. A VERSION TRAP banner: JEP 491 removes the `synchronized` cause in Java 24; native frames still pin |
| D-078 | The virtual-thread creation API | 1.18.11–1.18.14 | table | Rows: `Thread.startVirtualThread(Runnable)`, `Thread.ofVirtual().name(...).start(...)`, `Thread.ofVirtual().unstarted(...)`, `Thread.ofVirtual().factory()`, `Executors.newVirtualThreadPerTaskExecutor()`, `Thread.ofPlatform()`. Columns: returns, started immediately, nameable, usable with try-with-resources (and the Java 19 `ExecutorService implements AutoCloseable` change), what `close()` waits for |
| D-079 | What a virtual thread refuses to do | 1.18.15–1.18.18 | table | Rows: `setDaemon(false)`, `setPriority`, thread group, `getName()` default, `stop`, `suspend`, `resume`. Columns: behaviour on a platform thread, behaviour on a virtual thread (throws / silently ignored / fixed value / empty string), and the operational consequence — an unnamed virtual thread being unfindable in a dump |
| D-080 | A structured task scope is a tree | 1.19.1–1.19.3, 3.15.1 | hierarchy | An `AssessmentService` call forking two subtasks — the identity vendor (p50 900 ms) and the watchlist provider (p50 1.4 s) — under one scope, each subtask a virtual thread. The `try`-with-resources block drawn as the boundary the subtasks cannot outlive. Beside it the unstructured version with two orphan threads escaping the block |
| D-081 | `ShutdownOnFailure` versus `CompletableFuture.allOf` | 1.19.5, 1.19.11, 2.13.4 | timeline | Two lanes on one time axis. Lane 1, `ShutdownOnFailure`: the watchlist call fails at 1.4 s, the identity call is interrupted, `join()` returns, `throwIfFailed()` rethrows. Lane 2, `allOf`: the same failure, the identity call keeps running past the block's end, marked "orphan", still holding its connection. Both end states labelled |
| D-082 | `ShutdownOnSuccess` as a hedge | 1.19.6, 2.13.2 | timeline | Two replicas of the watchlist provider, one responding at 1.4 s and one at 25 s. One axis, two lanes: the fast one completes, the scope cancels the slow one at 1.4 s, the total latency marked. A comparison line shows the un-hedged p99 of 25 s |
| D-083 | `Subtask` states and the illegal calls | 1.19.8, 1.19.9, 3.15.2, 3.15.3 | state-transition | States `UNAVAILABLE`, `SUCCESS`, `FAILED`, with the transitions caused by `fork`, task completion, task failure and `shutdown`. Illegal edges labelled with their exceptions: `get()` before `join()` → `IllegalStateException`; a call from a non-owner thread or an out-of-order close → `StructureViolationException` |
| D-084 | Sequenced collections and the retrofit | 1.20.19, 1.20.20 | hierarchy | `SequencedCollection`, `SequencedSet`, `SequencedMap` as new interfaces; arrows showing `List` and `Deque` gaining `SequencedCollection`, `LinkedHashSet` implementing `SequencedSet`, `SortedSet` extending `SequencedSet`, `LinkedHashMap` implementing `SequencedMap`, `SortedMap` extending `SequencedMap`. Every new method listed on the interface that declares it |
| D-085 | `reversed()` is a view | 1.20.21, 1.20.22 | before-after | A `LinkedHashMap` of restriction keys in insertion order. Left: `reversed()` drawn as a view object pointing at the same entries, with a write through the view changing the source — both drawn. Right: an explicit copy, with the write isolated. A side note: `getFirst()` on an empty sequenced collection throws `NoSuchElementException`, it does not return null |
| D-086 | Library additions by release, 9 → 21 | 1.20.1–1.20.24 | table | One row per release from 9 to 21. Columns: collection factories, `String` methods, `Files`/IO, stream and `Optional` additions, language additions, and the one behaviour change that breaks existing code (JEP 400's UTF-8 default at 18 highlighted) |

## Part 2 diagrams

| # | Diagram | Syllabus leaf | Type | Must show |
|---|---|---|---|---|
| D-087 | The master stream cost table | 2.1.1 | table | One row per stream operation. Columns: per-element cost, allocations per stage, stateful, buffering (none / bounded / whole stream), parallel behaviour, amortised cost, worst case. Costs quoted against 2.8M stake reservations |
| D-088 | Feature by version, with its JEP and its trap | 2.1.2, 3.16.20 | table | One row per feature this guide owns. Columns: feature, JEP number, first preview release, final release, what it replaced, and the one trap that ships with it |
| D-089 | Lambda vs method reference vs anonymous class vs inner class | 2.1.3, 2.2.5, 2.2.6 | table | Columns for each of the four. Rows: class files generated at compile time, classes created at runtime, allocations per evaluation, capture semantics, meaning of `this`, first-call linkage cost, serialization story, stack-trace readability, when it is the right answer |
| D-090 | Six ways to say "absent" | 2.1.4, 2.6.10 | table | Rows: `Optional`, `null`, a thrown exception, an empty collection, a null object, a sentinel value. Columns: caller must acknowledge, allocation cost, works in a field, works as a parameter, framework support, and the QuizStakes case each is correct for |
| D-091 | Five ways to carry data | 2.1.5 | table | Columns: record, `final` class, enum, interface, `Map<String,Object>`. Rows: immutability, generated members, pattern deconstruction, extensibility, serialization, framework support, per-instance memory, when to choose |
| D-092 | Four concurrency models | 2.1.6, 2.12.17 | table | Columns: platform threads, virtual threads, reactive (WebFlux/Reactor), structured concurrency. Rows: throughput ceiling, latency, stack traces, debugger, profiler, backpressure, cancellation, library support, team learning cost |
| D-093 | Seven ways to get a `List` | 2.1.7 | table | Rows: `new ArrayList<>()`, `Arrays.asList`, `List.of`, `List.copyOf`, `Collectors.toList`, `Collectors.toUnmodifiableList`, `Stream.toList`. Columns: mutable, structurally modifiable, `set` in place, nulls permitted, concrete type guaranteed, since which release |
| D-094 | The first call to a lambda call site | 2.2.1, 3.1.8, 3.1.13 | timeline | One axis for one call site. Point 1: `invokedynamic` reached, unlinked. Point 2: `LambdaMetafactory.metafactory` bootstrap runs. Point 3: `InnerClassLambdaMetafactory` spins a hidden class. Point 4: `CallSite` linked, target bound. Point 5: every subsequent call is an ordinary interface invocation. The one-off cost band shaded and labelled in microseconds |
| D-095 | Monomorphic versus megamorphic lambda call sites | 2.2.8, 3.2.10 | before-after | Left: one `Function` implementation at a call site — the JIT inlines through the interface call, the inlined body drawn. Right: twenty different lambdas assigned to the same `Function` field — the inline cache overflows to megamorphic, no inlining, the order-of-magnitude slowdown labelled |
| D-096 | What exists before the first element moves | 2.3.4, 3.3.3 | memory-layout | A three-stage pipeline over card deposits: the source spliterator, three `AbstractPipeline` stage objects doubly linked, three lambda instances (one non-capturing shared, two capturing), and the terminal op. Object count and approximate bytes totalled, then compared with a `for` loop's zero |
| D-097 | `sorted().findFirst()` versus `min(comparator)` | 2.3.9 | cost-curve | Two curves over N from 10 to 2.8M: O(n log n) for sort-then-take-first and O(n) for `min`. Both plotted with the comparator-invocation counts at N = 95,000 (one day of card deposits) written on the curves. The identical answer noted |
| D-098 | Stream or loop | 2.3.14, 2.3.15, 2.15.2 | decision-tree | Root: "what does the code need to do?" Branches to loop for side effects, early exit carrying several values, index arithmetic, in-place mutation, checked exceptions, a measured hot path. Branches to stream for transformation chains, grouping and aggregation, laziness over an expensive or infinite source, one-line parallelism over a splittable source |
| D-099 | One blocking parallel stream starves the whole JVM | 2.4.2, 2.4.5, 3.5.9 | before-after | Left: the common pool with `availableProcessors() - 1` workers plus the submitting thread — the effective width equal to the core count, both halves labelled. All workers blocked on the identity vendor's 38 s p99. Right: an unrelated library's parallel stream queued behind them, its latency inflated. The fix — a dedicated executor — drawn as a third panel |
| D-100 | Source splitting quality, ranked | 2.4.8, 3.4.5–3.4.9 | table | Rows: `int[]`, `ArrayList`, `IntStream.range`, `HashMap`, `HashSet`, `TreeMap`, `LinkedList`, `Files.lines`, `Stream.iterate`, `BufferedReader.lines`. Columns: characteristics reported, how `trySplit` divides, balance of the halves, verdict (excellent / good but uneven / effectively serial) |
| D-101 | `parallelStream().forEach(list::add)` corrupts the list | 2.4.11 | step-sequence, 3 frames | Two carrier threads adding to one `ArrayList` of ledger entries. Frame 1: both read `size` as 40. Frame 2: both write to index 40 — one entry lost. Frame 3: a grow racing with a write producing `ArrayIndexOutOfBoundsException` from inside `ArrayList.add`, plus the interspersed-null case. All three symptoms named |
| D-102 | Where parallel starts paying | 2.4.6, 2.4.7 | cost-curve | Sequential and parallel curves over N with the split/merge overhead as a constant band; the crossover marked near the N×Q ≈ 10,000 heuristic; three QuizStakes points plotted — 40 deposits/sec (never worth it), 95k deposits/day (marginal), 2.8M reservations/day with expensive per-element work (worth it) |
| D-103 | `filtering(p, toList())` versus `filter(p)` before `groupingBy` | 2.5.3 | before-after | Grouping card deposits by rail where one rail has no deposit above 100. Left, `filter` before `groupingBy`: that rail's key is absent from the map entirely. Right, `filtering` as a downstream: the key is present with an empty list. Both result maps drawn key by key |
| D-104 | A top-N collector's combiner | 2.5.8, 4.3.3 | step-sequence, 3 frames | Top-3 withdrawals by amount over two parallel leaves. Frame 1: each leaf maintains a bounded `PriorityQueue` of size 3, contents shown. Frame 2: the combiner merges the two heaps and re-bounds to 3 — the discarded elements marked. Frame 3: the finisher sorts descending. Actual withdrawal amounts (180, 260, 92) used |
| D-105 | `orElse` vs `orElseGet` vs `orElseThrow` | 2.6.3 | table | Rows for the three (plus `ifPresentOrElse` and `or`). Columns: argument type, evaluated when, cost when the value is present, what it returns on empty, and the QuizStakes case each fits (a constant `Money.ZERO`, a database fallback, a `RestrictedActionException`) |
| D-106 | Four absence strategies compared | 2.6.10 | table | Columns: `Optional`, nullability annotations plus NullAway, the null-object pattern, an exception. Rows: enforced by the compiler, allocation cost, works in a field, works across an API boundary, tooling support, failure mode when ignored |
| D-107 | A `var` policy you can defend in review | 2.7.1, 2.7.6, 2.7.9, 1.12.16 | decision-tree | Root: "does the initialiser already name the type?" Yes → `var` is fine, with the builder, try-with-resources and `Map.Entry` cases as leaves. No → write the type, with the opaque-factory, accumulator-width and interface-vs-implementation leaves. Each "no" leaf carries the concrete failure: `var total = 0` overflowing, `var list = new ArrayList<String>()` pinning the local's type to `ArrayList` |
| D-108 | Records across the framework boundary | 2.8.2–2.8.6, 2.8.14 | table | Rows: Jackson serialisation, Jackson deserialisation, Spring `@RequestBody`, Spring `@ConfigurationProperties`, Spring `@ModelAttribute`, Bean Validation, JPA entity, JPA `@Embeddable`, Spring Data projection, Lombok `@Value` equivalence. Columns: works, minimum version, what it needs (`-parameters`, `@JsonProperty`, `@JsonCreator`, a `@Target` including `RECORD_COMPONENT`), and the failure symptom when it does not |
| D-109 | Defensive copying, in and out | 2.8.13, 1.13.17 | before-after | `record PaymentRun(RunId id, List<WithdrawalTransaction> items, byte[] signature)`. Left: no copies — the caller's list and array both shared and mutable through the accessor. Right: `List.copyOf` in the compact constructor and `signature.clone()` on both copy-in and copy-out, with four distinct objects drawn and the mutation attempts shown failing |
| D-110 | Sum of products | 2.9.1, 2.9.5, 2.9.7 | hierarchy | The `Verdict` sealed interface as the sum; each record case expanded into its components as the product. Beside it a second worked shape: the account lifecycle state machine as a sealed interface of records with the transitions drawn as labelled edges between the case boxes |
| D-111 | Visitor versus sealed interface plus pattern switch | 2.9.3, 4.5.5 | before-after | Left: the Visitor implementation — a `VerdictVisitor` interface with four methods, an `accept` in each case class, and the double dispatch arrows; line count stated. Right: the sealed interface plus one pattern switch; line count stated. Underneath, a two-row table: "to add a case, edit here" and "to add an operation, edit here" for both designs |
| D-112 | The expression problem | 2.9.4 | table | A 2×2: adding a case versus adding an operation, against sealed hierarchy versus open polymorphism. Each cell states what must change and where the compiler helps you. A fifth column names the QuizStakes axis of change that decides it |
| D-113 | Refactoring an `instanceof` chain into a pattern switch | 2.10.1, 2.10.2 | step-sequence, 4 frames | Frame 1: the original `if`/`else if` chain of `instanceof` + cast over `Verdict`. Frame 2: type patterns replacing the casts. Frame 3: converted to a pattern switch, `default` still present. Frame 4: `default` removed once the type is sealed, so exhaustiveness is checked. Each frame states what the compiler now guarantees that it did not before |
| D-114 | Exhaustiveness drift after a partial redeploy | 2.10.9, 3.10.8, 4.8.9 | timeline | Three points: (1) both the sealed hierarchy and the switch site compiled together, exhaustive; (2) a fifth `Verdict` case added and only the hierarchy recompiled and deployed; (3) at runtime the switch matches nothing and throws `MatchException` (or `IncompatibleClassChangeError`). The class-file states at each point drawn, and the note that this is not a link error |
| D-115 | Text block, resource file, or constant | 2.11.3, 2.11.8, 2.15.8 | decision-tree | Root: "what is the payload?" Branches for SQL and JSON fixtures (text block), a payload another tool must lint/format/diff (resource file), a short single-line value (constant), and regex (text block loses — `\` still escapes, every backslash doubles, shown with an example). Trailing-newline discipline noted on the file-comparison leaf |
| D-116 | A Spring Boot request path, before and after virtual threads | 2.12.1–2.12.3 | before-after | Left: Tomcat with `maxThreads=200` — 200 platform threads, requests queueing behind them, `maxThreads` acting as the accidental rate limiter, 55k peak sessions against a 200-wide gate. Right: `spring.threads.virtual.enabled=true` — a virtual thread per request, no concurrency cap at the container, and the queue gone. What the flag switches (servlet executor, `@Async`) and what it does not, labelled |
| D-117 | The bottleneck moves downstream | 2.12.4, 2.12.5 | before-after | Left: the pool as the implicit limiter, with the JDBC pool of 20 comfortably behind 200 request threads. Right: 14k concurrent virtual threads arriving at the same 20-connection pool, the queue now at the connection pool and the database's max-connections ceiling. The deliberate fix — a `Semaphore` sized on purpose — drawn as the third panel |
| D-118 | A pinning JDBC driver under load | 2.12.6, 2.12.9, 2.12.10 | step-sequence, 3 frames | Frame 1: eight carriers, each running a virtual thread that enters the driver's `synchronized` block and blocks on the network. Frame 2: all carriers pinned; new virtual threads cannot run; the JFR `jdk.VirtualThreadPinned` event fires past its 20 ms threshold. Frame 3: the JSON thread dump from `jcmd <pid> Thread.dump_to_file -format=json` showing the pinned frames, with a note that `jstack` shows none of it |
| D-119 | What to measure once threads are free | 2.12.10–2.12.12 | table | Rows: live threads gauge, in-flight requests, semaphore permits in use, connection-pool saturation, `jdk.VirtualThreadStart`/`End`, `jdk.VirtualThreadPinned`, `jdk.VirtualThreadSubmitFailed`, heap occupied by stack chunks. Columns: what it meant before, what it means now, default JFR state (enabled/disabled) and threshold, and the alert worth setting |
| D-120 | A fan-out with one deadline | 2.13.1, 2.13.3 | timeline | One `joinUntil(Instant)` deadline drawn as a vertical line at 2 s across two subtask lanes: the identity vendor (900 ms p50, completes) and the watchlist provider (25 s p99, cut off). The scope's return marked, the cancelled subtask's interrupt arrow drawn, and the alternative of per-subtask timeouts shown as a second pair of lanes |
| D-121 | Scoped-value bindings versus a `ThreadLocal` map | 2.13.6–2.13.8, 3.15.5, 3.15.6 | before-after | Left: `ThreadLocal` — one map per thread, an inheritance copy into each child, and a `remove()` obligation, with the leak drawn when it is skipped. Right: `ScopedValue` — an immutable linked binding snapshot shared structurally, unbound automatically by stack unwinding, inherited by forked subtasks. A nested `where` drawn as shadowing, not mutation |
| D-122 | What breaks at each release, 9 → 21 | 2.14.1–2.14.6 | timeline | An axis with a marker per breaking release: 9 (strong encapsulation of internals, split packages), 11 (Java EE and CORBA modules removed), 16 (encapsulation on by default, `--add-opens`), 17 (`strictfp` no-op, Security Manager deprecated, illegal reflective access denied), 18 (UTF-8 default, JEP 400), 21 (pattern-switch exhaustiveness, sequenced-collection method-name clashes on `getFirst`/`reversed`/`putFirst`). Each marker carries the symptom you would actually see |
| D-123 | The safe upgrade order | 2.14.10, 2.14.11 | flowchart | Step 1: run on the new JDK with the old `--release`. Step 2: fix what breaks at runtime, with `jdeps --jdk-internals` and `jdeprscan` as the inputs. Step 3: raise `--release`. Step 4: fix compile errors. Step 5: adopt features. Each step has a rollback edge back to the previous, and a gate condition written on it |
| D-124 | The which-construct index | 2.15.1–2.15.10 | table | One row per question in §2.15. Columns: the question, the default answer, the condition that overrides the default, and the section of these notes that argues it |

## Part 3 diagrams

| # | Diagram | Syllabus leaf | Type | Must show |
|---|---|---|---|---|
| D-125 | How `javac` desugars a lambda | 3.1.1–3.1.3 | step-sequence, 3 frames | Frame 1: the source lambda inside `FundsLedger.reserveStake`. Frame 2: the private synthetic method `lambda$reserveStake$0`, marked `static` because it does not capture `this`. Frame 3: the call site replaced by `invokedynamic #N` with `LambdaMetafactory.metafactory` as the bootstrap. The `javap -c -p` text shown alongside each frame |
| D-126 | Reading a `BootstrapMethods` entry | 3.1.4–3.1.7, 3.1.17 | memory-layout | One `invokedynamic` entry annotated field by field: the bootstrap `LambdaMetafactory.metafactory` with its six parameters named (`caller`, `interfaceMethodName`, `factoryType`, `interfaceMethodType`, `implementation`, `dynamicMethodType`); the static arguments in the constant pool; the dynamic arguments on the operand stack. An arrow from `factoryType`'s parameter list to the captured locals, labelled "this is exactly what was captured" |
| D-127 | Non-capturing versus capturing at link time | 3.1.10, 3.1.11, 2.2.3, 2.2.4 | before-after | Left: a non-capturing lambda — the spun hidden class holds one instance in a static field, the bootstrap returns a `ConstantCallSite`, one allocation for the JVM's lifetime. Right: a capturing lambda — the spun class has one field per captured value and a constructor, and the call site allocates per evaluation. Allocation counts over 2.8M reservations written on both |
| D-128 | A method reference has no `lambda$` method | 3.1.14, 1.4.16 | before-after | Left: `r -> r.amount()` — a synthetic `lambda$…$0` method plus the indy. Right: `Reservation::amount` — no synthetic method, `implementation` is a direct method handle to `Reservation.amount`. Both `javap -c -p` listings shown with the differing lines highlighted |
| D-129 | `FLAG_SERIALIZABLE` and the serializable-lambda path | 3.1.5, 3.1.15 | flowchart | `altMetafactory` with its three flags and their values (`FLAG_SERIALIZABLE = 1`, `FLAG_MARKERS = 2`, `FLAG_BRIDGES = 4`); the serialization path through `SerializedLambda` and the compiler-generated `$deserializeLambda$`; each hop labelled with its cost, and the refactoring-fragility failure named at the end |
| D-130 | A captured `this` keeps the enclosing object alive | 3.2.4 | memory-layout | A static `NotificationService` registry holding one lambda that reads an instance field of `ProfileService`. The captured `this` arrow drawn to the `ProfileService` instance, which retains its aggregated objects. Retained bytes labelled on the whole subgraph; the fix (capture only the needed value into a local) drawn beside it with the reduced retained set |
| D-131 | The pipeline as a doubly linked list of stages | 3.3.1–3.3.4, 3.3.10 | memory-layout | The `AbstractPipeline` chain for `deposits.stream().filter(...).map(...).collect(...)`: three stage objects with all twelve fields named on the source stage (`sourceStage`, `previousStage`, `sourceOrOpFlags`, `nextStage`, `depth`, `combinedFlags`, `sourceSpliterator`, `sourceSupplier`, `linkedOrConsumed`, `sourceAnyStateful`, `sourceCloseAction`, `parallel`), `depth` values 0, 1, 2, and the `StatelessOp`/`StatefulOp` subtype labelled on each |
| D-132 | `wrapSink` walks backwards | 3.3.5–3.3.9 | step-sequence, 4 frames | Frame 1: the terminal op's sink created. Frame 2: the `map` stage's `opWrapSink` wraps it. Frame 3: the `filter` stage wraps that. Frame 4: `copyInto` calls `begin`, `forEachRemaining`, `end` on the outermost sink, and one element traverses the whole chain. `Sink`'s four methods listed in a legend, and the `copyIntoWithCancel` variant noted on frame 4 |
| D-133 | `StreamOpFlag` | 3.3.13, 3.3.16, 3.3.17, 3.4.14 | table | Rows: `DISTINCT`, `SORTED`, `ORDERED`, `SIZED`, `SHORT_CIRCUIT`. Columns: the bit position, what it means, what the stream position/op position/terminal-op position each encode (SET/CLEAR/PRESERVE), which operations set it, which clear it, and which optimisation it unlocks (`sorted()` becoming a no-op, `distinct()` using adjacent comparison, `count()` bypassing the pipeline) |
| D-134 | How `count()` bypasses the pipeline | 3.3.14, 3.3.15, 1.8.12 | flowchart | Start at `count()`. Check `SIZED` still set in `combinedFlags` → check no stateful op cleared it → check nothing short-circuits → return the source's exact size without building a sink chain. The `peek` stage boxed on the bypassed path and labelled "never invoked". A second path with a `filter` present, clearing `SIZED`, taking the full traversal. VERSION TRAP: Java 9 changed this |
| D-135 | The eight spliterator characteristics | 3.4.1, 3.4.2 | table | One row per characteristic with its hex bit value: `DISTINCT 0x01`, `SORTED 0x04`, `ORDERED 0x10`, `SIZED 0x40`, `NONNULL 0x100`, `IMMUTABLE 0x400`, `CONCURRENT 0x1000`, `SUBSIZED 0x4000`. Columns: meaning, which JDK sources report it, which stream optimisation it enables, and which operation clears it. The eight `Spliterator` methods listed in a legend |
| D-136 | `trySplit` returns the prefix | 3.4.4, 3.4.5 | step-sequence, 3 frames | An `ArrayList` of 95,000 card deposits. Frame 1: one spliterator over indices 0–94,999. Frame 2: `trySplit` returns a spliterator over 0–47,499 (the prefix) and leaves the original covering 47,500–94,999 — both ranges labelled. Frame 3: the recursion continuing to a leaf below the target size. Index bounds written at every level |
| D-137 | `SIZED` but not `SUBSIZED` | 3.4.3 | before-after | Left: an array-backed source — the total size is known and every split's size is known, so both flags are reported. Right: a balanced tree — the total is known (`SIZED`) but the subtree sizes are not (`not SUBSIZED`), drawn with the unknown subtree counts marked. The javadoc's own framing quoted in the caption |
| D-138 | Why an `Iterator`-derived stream parallelises badly | 3.4.7, 3.4.8, 3.4.9 | step-sequence, 3 frames | `IteratorSpliterator`'s batching fallback. Frame 1: the first `trySplit` pulls a batch of 1024 elements into an array. Frame 2: the next batch doubles. Frame 3: the tail remains unsplittable and never reports `SUBSIZED`. Batch sizes written on each frame; `LinkedList` and `Files.lines` named as the cases |
| D-139 | The parallel task tree | 3.5.1–3.5.3 | hierarchy | An `AbstractTask` tree over 2.8M reservations on an 8-core box: `LEAF_TARGET = ForkJoinPool.getCommonPoolParallelism() << 2` and `suggestTargetSize = sizeEstimate / LEAF_TARGET` written as formulas with the arithmetic worked, roughly four tasks per core; the resulting leaf count and leaf size labelled. **Mark both formulas as requiring verification against `AbstractTask.java` before the numbers are printed** |
| D-140 | The combine tree costs O(n) overall | 3.5.5, 3.6.4, 3.6.9 | step-sequence, 3 frames | Four leaves each with their own `ArrayList` of results. Frame 1: leaf accumulation, sizes shown. Frame 2: the first pairwise merges, each copying the right half into the left. Frame 3: the final merge copying half the total. Element-copy counts summed across the tree, and the same picture repeated for `joining()`'s `StringBuilder` append |
| D-141 | `ForEachTask` versus `ForEachOrderedTask` | 3.5.6, 1.8.1, 1.8.2 | before-after | Left, `forEach` in parallel: four leaves emitting as they finish, output interleaved, no buffering. Right, `forEachOrdered`: completed subtrees buffered until their predecessors finish, the buffers drawn with their contents, and the lost parallel win labelled |
| D-142 | Work stealing in the common pool | 3.5.11, 3.5.13, 3.5.14 | memory-layout | Four workers each with a deque; each pushes and pops at its own head; an idle worker steals from the tail of another, the steal arrow labelled. A second panel: a nested parallel stream inside a parallel stream's lambda producing the starvation shape. A third: two exceptions racing to the joining task, the first winning and the second discarded |
| D-143 | `CollectorImpl` and its pre-built characteristic sets | 3.6.1, 3.6.2 | table | Rows: `CH_CONCURRENT_ID`, `CH_CONCURRENT_NOID`, `CH_ID`, `CH_UNORDERED_ID`, `CH_UNORDERED_NOID`, `CH_NOID`. Columns: which of `CONCURRENT`/`UNORDERED`/`IDENTITY_FINISH` each contains, which collectors use it, and what the framework does differently as a result |
| D-144 | Kahan compensated summation inside `summingDouble` | 3.6.7, 3.6.8, 1.10.12 | step-sequence, 3 frames | Summing 95,000 card deposits averaging 65 as `double`s. Frame 1: the three-element `double[]` accumulator with the running sum, the compensation term and the simple sum. Frame 2: a small addend lost to a naive `+`, recovered into the compensation slot — the arithmetic written. Frame 3: the compensation added back in the finisher, with the naive total and the compensated total printed side by side. A note that `summingInt` uses a `long[]` and needs none of this |
| D-145 | `IDENTITY_FINISH` skips a whole pass | 3.6.10 | before-after | Left, a collector without `IDENTITY_FINISH`: the accumulation container built, then the finisher walks it to produce the result — two passes drawn. Right, with `IDENTITY_FINISH`: the container is cast and returned directly, one pass. The saved work stated in element counts over 95,000 deposits |
| D-146 | Inside `Optional` | 3.7.1–3.7.3, 3.7.6 | memory-layout | An `Optional<Client>` on the heap: 16-byte object header plus the single `value` reference field, the total written out; the shared `private static final Optional<?> EMPTY` drawn once with two `Optional.empty()` calls pointing at it and `==` annotated true; the `@jdk.internal.ValueBased` annotation labelled on the class with the "do not synchronize, do not depend on identity" consequence |
| D-147 | Upward projection | 3.8.1, 3.8.4 | step-sequence, 3 frames | `List<? extends Money> amounts; var first = amounts.get(0);`. Frame 1: the standalone type of the initialiser, containing a capture variable. Frame 2: upward projection replacing the capture variable with `Money`. Frame 3: the inferred local type. A second panel: an anonymous class initialiser where the inferred type is genuinely non-denotable and its extra members remain callable |
| D-148 | Where `var` leaves a trace in the class file | 3.8.2, 3.8.3, 1.12.1 | before-after | Left: the source with `var`. Right: the `javap -l` output showing `LocalVariableTable`/`LocalVariableTypeTable` carrying the inferred type, and the bytecode being byte-for-byte identical to the explicitly typed version — both listings shown. A note explaining why a field or parameter could never work: separate compilation |
| D-149 | The `Record` class-file attribute | 3.9.1, 3.9.2, 3.9.11 | memory-layout | The class file of `StakeSplit` with its `Record` attribute expanded: two `record_component_info` entries, each with a name index, a descriptor index and its own attributes (`Signature`, `RuntimeVisibleAnnotations`, `RuntimeVisibleTypeAnnotations`). The `private final` fields, the public accessors, and `extends java.lang.Record` (itself abstract, declaring abstract `equals`/`hashCode`/`toString`) all labelled |
| D-150 | `ObjectMethods.bootstrap` behind `equals`, `hashCode` and `toString` | 3.9.3–3.9.6 | flowchart | The three generated methods each compiling to an `invokedynamic` against `java.lang.runtime.ObjectMethods.bootstrap`, with the static arguments drawn: the record class, the semicolon-separated component-name string `"bonusPortion;cashPortion"`, and one `MethodHandle` getter per component. A consequence box: the `hashCode` algorithm is unspecified and may change between releases — never persist it |
| D-151 | Record deserialization runs the canonical constructor | 3.9.12, 3.9.13, 4.8.10 | before-after | Left: a hand-written class — deserialization allocates and populates fields directly, bypassing the constructor, so the validation never runs and an invalid `StakeSplit` (portions not summing to the stake) exists. Right: the record — the stream's component values are passed to the canonical constructor, the compact constructor's validation throws. A note listing the ignored hooks (`writeObject`, `readObject`, `readObjectNoData`, `writeExternal`, `readExternal`, `serialPersistentFields`) and the default `serialVersionUID` of 0 |
| D-152 | `PermittedSubclasses` is enforced at load time | 3.10.1–3.10.4 | step-sequence, 3 frames | Frame 1: the `Verdict` class file with its `PermittedSubclasses` attribute listing four constant-pool indices; no `ACC_SEALED` flag exists, labelled. Frame 2: a bytecode-manipulated fifth subclass produced at runtime. Frame 3: the JVM's load-time check failing it. A note that `non-sealed` emits no attribute at all |
| D-153 | A pattern switch compiles to `typeSwitch` plus `tableswitch` | 3.11.3–3.11.6, 2.10.10 | step-sequence, 4 frames | Frame 1: the source switch over `Verdict`. Frame 2: the `invokedynamic` to `SwitchBootstraps.typeSwitch` with its static arguments — the label list of `Class` objects, `String`/`Integer` constants and `EnumDesc` entries. Frame 3: the bootstrap returning the index of the first matching label. Frame 4: an ordinary `tableswitch` on that index. The `javap -c` listing beside the frames, and a cost note: closer to an optimised if-chain than to a jump table |
| D-154 | Record deconstruction is accessor calls in order | 3.11.8, 3.11.9 | step-sequence, 3 frames | `case Movement(LedgerEntry(Position from, Money amount), LedgerEntry to)`. Frame 1: the outer type test. Frame 2: accessors invoked in declaration order, short-circuiting on the first component mismatch — the skipped calls marked. Frame 3: an accessor throwing, wrapped in `MatchException` with the original as its cause |
| D-155 | `tableswitch` versus `lookupswitch` | 3.12.1, 3.12.2 | before-after | Left: dense case labels compiling to `tableswitch` with the jump table drawn. Right: sparse labels compiling to `lookupswitch` with the key/offset pairs drawn. Beneath, the two-stage `String` switch: `lookupswitch` on `hashCode`, `equals` to confirm, then a second switch on a synthetic index — worked on a restriction-type name |
| D-156 | `$SwitchMap` protects a separately compiled enum switch | 3.12.3 | before-after | Left: a switch over `RestrictionType` compiled with the synthetic `$SwitchMap$RestrictionType` `int[]` mapping `ordinal()` to a stable case index — the array contents shown. Right: the enum reordered and recompiled without recompiling the switch — the map absorbs the change and the correct arm still runs. The failure that would occur without it drawn as a third panel |
| D-157 | The synthetic default in an exhaustive enum switch expression | 3.12.7, 3.12.8 | before-after | Left: the source with no `default`. Right: the `javap -c` output with the synthetic default arm that throws `IncompatibleClassChangeError`. Beneath, the scenario that reaches it: a constant added to the enum after the switch's class was compiled. A VERSION TRAP note that the thrown type has changed shape across releases |
| D-158 | A text block is a constant, folded at compile time | 3.13.1, 3.13.4, 3.13.6 | before-after | Left: the source text block. Right: the `javap -v` constant pool showing a single `CONSTANT_String_info` with the final, already-stripped content — nothing of the algorithm surviving to runtime. Beneath: a text block and an equal string literal compared with `==`, both pointing at the same interned constant, with the caution that this is not a habit to build |
| D-159 | The three layers of a virtual thread | 3.14.1, 3.14.11 | hierarchy | `java.lang.VirtualThread` on top, `jdk.internal.vm.Continuation` beneath it, the FIFO `ForkJoinPool` scheduler beneath that, and platform carrier threads at the bottom. `Thread.currentThread()` drawn returning the `VirtualThread`, with the carrier marked reachable only through internal API |
| D-160 | Stack chunks live on the heap | 3.14.2, 3.14.3, 3.14.10, 2.12.12 | memory-layout | One carrier's native stack with three mounted frames; the heap holding `StackChunk` objects for the unmounted threads; arrows for the copy in both directions labelled "mount" and "unmount", with the lazy/partial copying noted. The heap arithmetic for 1,000,000 virtual threads written out and contrasted with 1,000,000 × 1 MB of reserved platform stack |
| D-161 | `VirtualThread`'s state machine | 3.14.4 | state-transition | The nine states — `NEW`, `STARTED`, `RUNNABLE`, `RUNNING`, `PARKING`, `PARKED`, `PINNED`, `YIELDING`, `TERMINATED` — with every transition labelled by the event that causes it (`start`, schedule, mount, blocking call, successful yield, failed yield while pinned, unpark, completion) |
| D-162 | FIFO for virtual threads, LIFO for parallel streams | 3.14.7, 3.5.11 | before-after | Left: the virtual-thread scheduler in FIFO async mode — independent tasks, fairness prioritised, the queue drawn head-first. Right: the common pool's LIFO work-stealing — recursively split subtasks, locality prioritised, own-head push/pop with tail stealing. The reason for each choice written under each panel |
| D-163 | Pinning is a property of the continuation | 3.14.13, 3.14.14, 3.14.17, 3.14.18 | before-after | Left, Java 21: a held monitor or a native frame on the continuation's stack makes `yield` impossible — both frames marked on a drawn stack. Right, Java 24 (JEP 491): monitors are continuation-aware and the monitor case disappears; the native frame still pins. A third panel: no preemption — a CPU-bound virtual thread holding its carrier indefinitely, and the carrier pool growing toward `maxPoolSize` as compensation |
| D-164 | Scoped values and structured concurrency are one mechanism | 3.15.1–3.15.4, 3.15.7 | hierarchy | A scope stack per owning thread; each `fork` starting one virtual thread with the scoped-value binding snapshot inherited; `shutdown()` interrupting unfinished subtasks and `close()` joining, drawn as two distinct arrows. The ownership check labelled on `fork`/`join`/`shutdown`/`close`, with `StructureViolationException` on the illegal edges |
| D-165 | Structured concurrency and scoped values, release by release | 3.15.8, 1.19.14, 1.19.16 | table | Rows: Java 19, 20, 21, 22, 23, 24, 25, and in flight. Columns: JEP number, package, status (incubator/preview/final), the API shape (constructors vs `open()` factories, `ShutdownOnFailure` vs `Joiner`, `runWhere` vs `where(...).run`), and whether published examples from that release still compile on 21 |
| D-166 | The consolidated feature → version table | 3.16.20 | table | One row per feature this guide covers. Columns: first preview release, final release, JEP numbers for each stage, whether it is still preview on 21, and the one-line summary |
| D-167 | The consolidated removed-or-disabled table | 3.16.21 | table | Rows: Nashorn, the Java EE modules, CORBA, applets, the Security Manager, finalization, the 32-bit x86 port, `sun.misc.Unsafe` memory access. Columns: deprecated in, removed or disabled in, the replacement, and the symptom on upgrade |
| D-168 | The tooling map for this topic | 3.17.1–3.17.12 | table | One row per tool. Columns: the command or flag exactly as typed, what claim it verifies, what its output looks like, and the section of these notes that uses it. Covers `javap -c -p -v`, `jshell`, `-Djdk.internal.lambda.dumpProxyClasses`, `-Xlog:class+load=info`, the four JFR events, `jcmd Thread.dump_to_file -format=json`, `jcmd Thread.print`, async-profiler, JMH, IntelliJ's stream debugger, ErrorProne/SpotBugs/Sonar/NullAway rules, `-XX:+PrintFlagsFinal`, `System.getProperties()`, `ForkJoinPool.getCommonPoolParallelism()` |
| D-169 | What a stream stack trace actually looks like | 2.3.5, 2.3.6, 3.17.8 | before-after | Left: the exception stack trace from an NPE thrown inside a `map` over card deposits — the synthetic `lambda$process$2` frame, the `ReferencePipeline$3$1.accept` frames, the `AbstractPipeline.copyInto` frame, all labelled with what each one is. Right: the same failure inside a `for` loop, four frames deep. A note on the `StackOverflowError` risk from a long pipeline plus recursion plus `flatMap` |
| D-170 | Where the JIT can and cannot help | 2.2.2, 2.3.2, 3.2.10, 3.7.6 | table | Rows: a monomorphic lambda call site, a megamorphic one, an `Optional` chain that inlines end to end, an `Optional` chain crossing a non-inlined boundary, a boxed pipeline, a primitive pipeline. Columns: inlined, escape analysis applies, allocations eliminated, observed cost, and how you confirm it (JMH, an allocation profiler, `-XX:+PrintInlining`) |

## Part 4 diagrams

| # | Diagram | Syllabus leaf | Type | Must show |
|---|---|---|---|---|
| D-171 | `MyStream`'s sink chain next to the JDK's | 4.2.1, 4.2.2, 4.2.10 | before-after | Left: `MyStream`'s `MySink` chain with `begin`/`accept`/`cancellationRequested`/`end`, three stages, one traversal. Right: the JDK's equivalent objects for the same pipeline, with the extra machinery named (four stream shapes, `StreamOpFlag`, `Spliterator`, ForkJoin integration, closing, exception semantics) so the gap is explicit |
| D-172 | Proving fusion with a print in every stage | 4.2.3, 4.2.4 | step-sequence, 3 frames | Frame 1: the expected (wrong) stage-by-stage output. Frame 2: the actual interleaved per-element trace, printed line by line for the first three stake reservations. Frame 3: the same with `limit(2)` and `findFirst`, showing the source never fully traversed and `cancellationRequested` returning true |
| D-173 | Platform threads versus virtual threads on the echo server | 4.6.1 | cost-curve | Connections on the x-axis at 1, 1,000 and 50,000; throughput and memory on two y-axes; one line per implementation. The platform-thread line flattening and then failing at the thread limit, the virtual-thread line continuing. Measured numbers written at each of the three points |
| D-174 | The pinning reproducer, before and after | 4.6.2 | before-after | Left: `synchronized` around a blocking sleep on Java 21, with the `-Djdk.tracePinnedThreads=full` output printed and each line explained, plus the measured throughput. Right: the `ReentrantLock` version with the trace empty and the re-measured throughput. Both numbers stated |
| D-175 | The orphan that `allOf` leaves behind | 4.6.5 | before-after | Left: `StructuredTaskScope.ShutdownOnFailure` with a deliberate failure — the sibling interrupted, the thread count returning to baseline, both drawn. Right: `CompletableFuture.allOf` with the same failure — the sibling still running after the method returns, visible in the thread dump, still holding its connection |
| D-176 | Common-pool starvation, reproduced | 4.6.7 | timeline | Two lanes on one axis: a blocking parallel stream occupying every common-pool worker, and an innocent parallel stream submitted afterwards, its start delayed by the full blocking duration. Both timings written. A third lane repeats the innocent stream against a dedicated executor, starting immediately |
| D-177 | Hand-rolled batching versus `Gatherers.windowFixed` | 4.7.1, 4.7.6 | before-after | Left: the Java 21 custom `Spliterator` for fixed windows of 100 ledger entries, with `estimateSize` and the absent `SUBSIZED` claim labelled. Right: the Java 24 `Gatherers.windowFixed(100)` one-liner, with the `Gatherer` contract (`initializer`, `integrator`, `combiner`, `finisher`) and greedy-vs-short-circuiting integrators listed |
| D-178 | The fifteen puzzlers and their mechanisms | 4.8.1 | table | One row per puzzler: `peek` elision, stream reuse, `toList` immutability, `toMap` null value, `groupingBy` null key, `orElse` eagerness, `Optional.empty()` identity, `var` diamond, record array `equals`, pattern-switch NPE, text-block indentation, bound method-reference NPE, `allMatch` on empty, `IntStream.sum` overflow, parallel `forEach` corruption. Columns: what a reader predicts, what actually happens, the mechanism, and the syllabus leaf |

## Part 5 diagrams

| # | Diagram | Syllabus leaf | Type | Must show |
|---|---|---|---|---|
| D-179 | The trap index | 5.2.1 | table | One row per `**Pitfall:**` in the whole file. Columns: the wrong belief, the symptom in production, the fix, and the file and leaf where it is argued. This is the single pre-interview scan sheet |
| D-180 | The version-stale claims table | 5.2.2, 5.2.5 | table | One row per stale claim listed in leaf 5.2.2. Columns: what people still say, what was true and until when, what is true on Java 21, what changed after 21, and the release that changed it |
| D-181 | The numbers card | 5.3.1 | table | Every constant in the guide with its value and its source: 43 function interfaces, 30 collectors across 54 overloads, common-pool parallelism `n − 1` plus the submitting thread, `LEAF_TARGET = parallelism << 2`, the 20 ms `VirtualThreadPinned` threshold, `maxPoolSize` 256 (**marked as requiring verification**), class-file majors 52/53/55/61/65/69, the eight spliterator characteristic bits with their hex values, `FLAG_SERIALIZABLE = 1`/`FLAG_MARKERS = 2`/`FLAG_BRIDGES = 4`, preview minor version 65535 |
| D-182 | The spaced-repetition schedule | 5.3.8 | timeline | A 21-day axis with four marked points: day 1 full read, day 3 atomic concept checklist, day 7 numbers and mechanism drills, day 14 code-reading and symptom drills, day 21 build two Part 4 items. Each point lists the specific files to revisit |

---

# OUTPUT CONTRACT

## Exact files to write

All under `src/notes/detailed/04-modern-java/`. Create the directory and every subdirectory. Write
every file listed. The layout is **subject-major**: one folder per subject, each holding a basics
file, an intermediate file and an internals file where the syllabus has material at that tier.

| File | Syllabus sections |
|---|---|
| `00-index.md` | The reading map, written first: one line per file below with the syllabus sections and leaf ranges it covers, the diagram ids it contains, its status, the target version, and the 984 total |
| `platform-and-releases/01-basics.md` | §1.1 |
| `platform-and-releases/02-migration.md` | §2.14 |
| `platform-and-releases/03-internals-version-delta.md` | §3.16 |
| `platform-and-releases/04-internals-observability.md` | §3.17 |
| `functional-interfaces/01-basics.md` | §1.2 |
| `lambdas/01-basics.md` | §1.3 |
| `lambdas/02-cost-and-choice.md` | §2.2 |
| `lambdas/03-internals-translation.md` | §3.1 |
| `lambdas/04-internals-capture-and-identity.md` | §3.2 |
| `method-references/01-basics.md` | §1.4 |
| `streams/01-basics-the-model.md` | §1.5 |
| `streams/02-sources.md` | §1.6 |
| `streams/03-intermediate-operations.md` | §1.7 |
| `streams/04-terminal-operations.md` | §1.8 |
| `streams/05-primitive-streams.md` | §1.9 |
| `streams/06-cost-model.md` | §2.3 |
| `streams/07-parallel-streams.md` | §2.4 |
| `streams/08-internals-pipeline.md` | §3.3 |
| `streams/09-internals-spliterator.md` | §3.4 |
| `streams/10-internals-parallel-execution.md` | §3.5 |
| `collectors/01-basics.md` | §1.10 |
| `collectors/02-in-anger.md` | §2.5 |
| `collectors/03-internals-collectors.md` | §3.6 |
| `optional/01-basics.md` | §1.11 |
| `optional/02-discipline.md` | §2.6 |
| `optional/03-internals-optional.md` | §3.7 |
| `var/01-basics.md` | §1.12 |
| `var/02-in-practice.md` | §2.7 |
| `var/03-internals-inference.md` | §3.8 |
| `records/01-basics.md` | §1.13 |
| `records/02-in-practice.md` | §2.8 |
| `records/03-internals-records.md` | §3.9 |
| `sealed-types/01-basics.md` | §1.14 |
| `sealed-types/02-data-oriented-programming.md` | §2.9 |
| `sealed-types/03-internals-sealed.md` | §3.10 |
| `pattern-matching/01-basics.md` | §1.15 |
| `pattern-matching/02-in-anger.md` | §2.10 |
| `pattern-matching/03-internals-pattern-matching.md` | §3.11 |
| `switch/01-basics.md` | §1.16 |
| `switch/03-internals-switch-compilation.md` | §3.12 |
| `text-blocks/01-basics.md` | §1.17 |
| `text-blocks/02-in-practice.md` | §2.11 |
| `text-blocks/03-internals-compilation.md` | §3.13 |
| `virtual-threads/01-basics.md` | §1.18 |
| `virtual-threads/02-in-production.md` | §2.12 |
| `virtual-threads/03-internals-virtual-threads.md` | §3.14 |
| `structured-concurrency/01-basics.md` | §1.19 |
| `structured-concurrency/02-in-practice.md` | §2.13 |
| `structured-concurrency/03-internals.md` | §3.15 |
| `library-additions/01-basics.md` | §1.20 |
| `cost-model/02-master-tables.md` | §2.1 |
| `which-construct/02-which-construct.md` | §2.15 |
| `build-it/01-functional-toolkit.md` | §4.1 |
| `build-it/02-mystream.md` | §4.2 |
| `build-it/03-collectors-and-myoptional.md` | §4.3, §4.4 |
| `build-it/04-records-sealed-patterns.md` | §4.5 |
| `build-it/05-concurrency-builds.md` | §4.6 |
| `build-it/06-filling-the-21-gaps.md` | §4.7 |
| `build-it/07-diagnostic-harnesses.md` | §4.8 |
| `90-interview-basics.md` | **Part 1's wrap-up**: the summary table over §1.1–§1.20, 10 interview Q&As with full spoken-length model answers, 5 predict-the-output puzzles |
| `91-interview-intermediate.md` | **Part 2's wrap-up**: the summary table over §2.1–§2.15, 10 Q&As, 5 puzzles |
| `92-interview-internals.md` | **Part 3's wrap-up**: the summary table over §3.1–§3.17, 10 Q&As, 5 puzzles |
| `93-interview-build-it.md` | **Part 4's wrap-up**: the summary table over §4.1–§4.8, 10 Q&As, 5 puzzles |
| `94-interview-questions-and-drills.md` | §5.1 all 95 questions with answer shapes, §5.2 the trap index and version-stale table, §5.3 the drills. **Ends with Part 5's own summary table, 10 Q&As and 5 puzzles, then the file-set-wide flat `## Atomic concept checklist`** |

Diagrams go in `src/notes/detailed/04-modern-java/diagrams/`, flat, named `D-NNN-short-slug.svg`.

If any single file becomes unwieldy, **split it further** (`03-intermediate-operations-a.md`,
`03-intermediate-operations-b.md`, …) and register the new files in `00-index.md`. Splitting is
always preferred to cutting content. Never merge files to reduce the count.

## Required header on every file except `00-index.md`

```
# 04 Modern Java — <subject> — <tier> (<syllabus sections covered>)

**Target version: Java 21 LTS.** | **Part <n> of 5** | [Index](../00-index.md)
Previous: [<title>](<relative path>) · Next: [<title>](<relative path>)
```

Files at the topic root (`90`–`94`) link the index as `[Index](00-index.md)`.

## Required footer on every file except `00-index.md`

```
---

**Leaves covered:** <explicit list or ranges, e.g. 1.7.1–1.7.24> (<count> leaves)
**Leaves deferred:** <none | leaf number + one-line reason each>
**Diagrams included:** <D-025, D-026, …>
**Target version:** Java 21 LTS
```

---

# SELF-VERIFY BEFORE REPORTING DONE

Run this checklist against your own output. Do not report completion until every box is genuinely
satisfied.

**Coverage**
- [ ] All 984 syllabus leaves appear in the notes, or are listed in a `## Deferred` block with a reason.
- [ ] Every file's footer lists the leaves it covers, and the union across all files is all 984.
- [ ] Every file listed in the OUTPUT CONTRACT exists, with the required header and footer.
- [ ] `00-index.md` lists every file, its syllabus sections, its leaf ranges and its diagram ids.

**Format**
- [ ] Every note file is Markdown (`.md`).
- [ ] No file was cut short for length. No "and so on", no "similar to the above", no deferred-for-space.
- [ ] No ASCII art anywhere. No inline `<svg>` anywhere.
- [ ] All 182 manifest diagrams exist as standalone `.svg` files in `diagrams/`, named `D-NNN-short-slug.svg`, each embedded with a Markdown image reference and captioned with its `D-NNN` id.
- [ ] Every SVG shows every element named in its `Must show` cell, has an explicit `viewBox` and no fixed width/height, an opaque backdrop rect, orthogonal-only edge routing, a legend, no text below 10.5px, no external font or CSS dependency, and explicit contrasting fills and strokes so it reads on light and dark backgrounds.
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
- [ ] All code is Java 21 idiomatic, and every snippet needing `--enable-preview` on 21 says so.
- [ ] Only the three callout markers `**Pitfall:**`, `**Insight:**`, `**Interview:**` are used.
- [ ] Every `[TRAP]` leaf carries a `**Pitfall:**` with wrong belief, symptom and fix (~135 leaves).
- [ ] Every `[PROVE]` leaf has the argument worked through, not asserted (~150 leaves).
- [ ] Every `[SOURCE]` leaf quotes real JDK source, JEP text or spec text and explains every quoted line (~75 leaves).
- [ ] Every `[BYTECODE]` leaf shows `javap -c` output read instruction by instruction (~30 leaves).
- [ ] Every `[NUM]` leaf states the arithmetic explicitly (~85 leaves).
- [ ] Every `[BUILD]` leaf ships complete generic compiling code, and every Part 4 item carries a "Diff vs the real one" table covering edge cases, intrinsics, serialization, null policy, thread safety, allocation tricks, and why the JDK bothers.
- [ ] All 202 `[RESEARCH]` leaves were re-verified against a primary source, or the uncertainty is stated in the text.
- [ ] All 22 `[VERSION-TRAP]` leaves state both what is true in 21 and what used to be true.
- [ ] Every `[X-REF nn]` leaf has a self-contained mechanism paragraph before the pointer, and never sends the reader away empty-handed.
- [ ] Version differences across Java 8 / 9+ / 11 / 17 / 21 are called out inline at the point of each claim.

**Verification of the three unconfirmed figures**
- [ ] `jdk.virtualThreadScheduler.maxPoolSize = 256` (3.14.5) was confirmed against `VirtualThread.java` at jdk-21+35 or a running JDK 21, or is explicitly marked unverified in the text.
- [ ] `LEAF_TARGET = ForkJoinPool.getCommonPoolParallelism() << 2` and `suggestTargetSize` (3.5.2, 3.5.3) were confirmed against `AbstractTask.java`, or are explicitly marked unverified.
- [ ] The LVTI style guide's `G1`–`G7` identifiers (1.12.15) were verified at the source, or the principles are stated in substance with no `G`-numbers printed.
- [ ] Every JEP quotation was re-fetched through a mirror (`javaalmanac.io`, `bugs.openjdk.org`, `cr.openjdk.org`) before being quoted verbatim, because `openjdk.org` 403s.

**Corrections carried through**
- [ ] Pinning is dated: `synchronized` pins on 21, JEP 491 removes that cause in 24, and the `jdk.VirtualThreadPinned` JFR event survives for native-frame pinning.
- [ ] The common pool's width is stated in both halves: parallelism `availableProcessors() - 1` plus the submitting thread, giving an effective width equal to the core count.
- [ ] Structured concurrency names the actual Java 21 shape (`fork` → `Subtask`, `ShutdownOnFailure`/`ShutdownOnSuccess`, preview) and the Java 25 rework (`open()` factories, `Joiner`).

**Per part**
- [ ] `90-interview-basics.md` ends Part 1 with a summary table, 10 Q&As with full spoken-length model answers, and 5 predict-the-output puzzles with actual output and explanation.
- [ ] `91-interview-intermediate.md` does the same for Part 2.
- [ ] `92-interview-internals.md` does the same for Part 3.
- [ ] `93-interview-build-it.md` does the same for Part 4.
- [ ] `94-interview-questions-and-drills.md` does the same for Part 5, and answers all 95 questions of §5.1 with the answer shape, not a hint.

**Closing**
- [ ] `94-interview-questions-and-drills.md` ends with a flat `## Atomic concept checklist`, one bullet per distinct concept across all five parts, no nesting, no headings inside it.

---

# REFERENCES

Primary sources this topic is built on. Do not invent additional URLs; if you need a fact not
covered here, verify it against the JDK 21 source, the JLS/JVMS or the javadoc and cite that.
**`openjdk.org` returned HTTP 403 to every direct fetch during the syllabus research pass**, so
every JEP below was read through search summaries plus a secondary source. Re-fetch each JEP
through a mirror before quoting its text verbatim.

**JDK 21 javadoc and guides**

- https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/util/stream/package-summary.html — the normative stream vocabulary: the five properties, laziness, short-circuiting, stateless/stateful, non-interference, statelessness of behavioural parameters, side-effect elision, encounter order, the reduction and mutable-reduction contracts, associativity, and the three conditions for a concurrent reduction
- https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/util/function/package-summary.html — the complete 43-interface inventory and the naming scheme
- https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/util/stream/Collectors.html — the 30 distinct static factory methods across 54 overloads
- https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/util/stream/Collector.html — the five-function contract and the three `Characteristics` values
- https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/util/Optional.html — the complete method list with the release each was added, the "primarily intended for use as a method return type" API note, and the value-based-class warning
- https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/util/Spliterator.html — the eight characteristics, the `SIZED`-but-not-`SUBSIZED` balanced-tree example, and the `trySplit` contract
- https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/lang/invoke/LambdaMetafactory.html — the `metafactory`/`altMetafactory` signatures, the static-vs-dynamic argument distinction, and the desugar-plus-indy translation strategy
- https://docs.oracle.com/en/java/javase/21/core/virtual-threads.html — the scheduler, the tuning properties, the two pinning causes, `-Djdk.tracePinnedThreads`, the four JFR events with their default states and the 20 ms threshold, `jcmd Thread.dump_to_file -format=json`, the `Thread.ofVirtual`/`Thread.Builder` API, "scale not speed", the never-pool rule, the semaphore guidance, the `ThreadLocal` warning, and the 10,000-threads rule of thumb
- https://docs.oracle.com/en/java/javase/21/core/creating-sequenced-collections-sets-and-maps.html — the three interfaces, their exact method sets, and the retrofit list
- https://docs.oracle.com/en/java/javase/21/language/pattern-matching-switch.html — exhaustiveness rules, the legacy selector types exempt from them, `MatchException`, the sealed-`permits` coverage check, and the relaxation of null-hostility
- https://docs.oracle.com/en/java/javase/17/text-blocks/index.html — the text-block compile-time algorithm and the re-indentation rule
- https://docs.oracle.com/en/java/javase/24/core/stream-gatherers.html — the `Gatherer` contract and the built-ins `fold`, `scan`, `windowFixed`, `windowSliding`, `mapConcurrent`
- https://docs.oracle.com/en/java/javase/16/docs/specs/records-serialization.html — the record serialization specification: components govern the form, the canonical constructor deserialises, the custom hooks are ignored

**OpenJDK source at the jdk-21+35 tag**

- https://raw.githubusercontent.com/openjdk/jdk/jdk-21%2B35/src/java.base/share/classes/java/util/stream/AbstractPipeline.java — the twelve fields, the two exception messages verbatim, and the bodies of `wrapSink`, `copyInto` and `evaluate`
- https://github.com/openjdk/jdk/blob/master/src/java.base/share/classes/java/util/stream/ReferencePipeline.java — `StatelessOp`/`StatefulOp`, `opWrapSink` per operation, and the `Sink.ChainedReference` pattern
- `src/java.base/share/classes/java/util/stream/AbstractTask.java` at the same tag — **the source of record for `LEAF_TARGET` and `suggestTargetSize`; verify before printing either formula**
- `src/java.base/share/classes/java/lang/VirtualThread.java` at the same tag — **the source of record for the scheduler's `parallelism` and `maxPoolSize` defaults; verify before printing 256**
- `src/java.base/share/classes/java/util/stream/Collectors.java` — `CollectorImpl`, the six pre-built characteristic sets, and the Kahan compensation array
- `src/java.base/share/classes/java/util/Optional.java` — the single `value` field, the shared `EMPTY`, the `@jdk.internal.ValueBased` annotation, and the identical bodies of `get()` and `orElseThrow()`

**Specifications and design documents**

- https://cr.openjdk.org/~briangoetz/lambda/lambda-translation.html — the full lambda translation strategy: `lambda$N` naming, capturing vs non-capturing instantiation, `SerializedLambda` and `$deserializeLambda$`, the bridge-method flag, and the explicit "why not inner classes" argument
- https://cr.openjdk.org/~gbierman/jep409/jep409-20210507/specs/sealed-classes-jls.html — the sealed-classes JLS text: the same-module/same-package rule, the direct-extension requirement, the final/sealed/non-sealed obligation, and the extension of narrowing reference conversion
- https://openjdk.org/projects/amber/guides/text-blocks-guide — the three-step algorithm in order, the closing-delimiter rule, `\s` as a fence, and `\` line continuation
- JLS 21 §14.11.1 and §14.11.1.1 — dominance and exhaustiveness for pattern switches
- JLS 21 §9.8 — the functional-interface definition and the `Object`-method exclusion

**JEPs (all 403 on direct fetch — re-read through a mirror before quoting)**

- JEP 286 `var`; JEP 323 `var` in lambda parameters; JEP 361 switch expressions; JEP 378 text blocks; JEP 394 pattern matching for `instanceof`; JEP 395 records; JEP 409 sealed classes; JEP 431 sequenced collections; JEP 440 record patterns; JEP 441 pattern matching for `switch`; JEP 444 virtual threads; JEP 453 structured concurrency; JEP 356 `RandomGenerator`; JEP 400 UTF-8 by default; JEP 371 hidden classes; JEP 461/473/485 stream gatherers; JEP 491 monitor pinning removed; JEP 505 structured concurrency reworked; JEP 506 scoped values
- https://javaalmanac.io/features/stringtemplates/ and https://bugs.openjdk.org/browse/JDK-8329949 — string templates previewed as JEP 430 (21) and JEP 459 (22), JEP 465 withdrawn, feature removed in 23 with no replacement
- https://inside.java/2024/11/21/newscast-80/ — JEP 491's effect on pinning and what the `jdk.VirtualThreadPinned` event retains

**Design commentary**

- https://nipafx.dev/inside-java-newscast-29/ and https://inside.java/u/BrianGoetz/ — records as nominal tuples, sealed plus records as algebraic data types, and the "record cliff" framing
- https://www.happycoders.eu/java/structured-concurrency-structuredtaskscope/ — the incubator→preview lineage (JEPs 428, 437, 453, 462, 480, 499, 505, 525, 533) and the Java 25 `Joiner` rework
- https://www.jrebel.com/blog/parallel-java-streams and https://dzone.com/articles/think-twice-using-java-8 — the production failure modes of parallel streams: common-pool sharing, I/O starvation, the unsupported custom-pool workaround, and the N×Q threshold







