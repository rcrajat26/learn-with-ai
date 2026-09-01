# PROMPT — Generate the Multithreading and Concurrency bible (topic 05)

This file is self-contained. Execute it verbatim. Do not go looking for a syllabus, an
index, a scenario file or a prior guide: everything you need — the role, the reader, the
example domain, all 1141 syllabus leaves, the diagram manifest, the file paths — is below.

---

# ROLE

You are a HotSpot runtime and `java.util.concurrent` engineer, and an interview coach, who has read
the concurrency stack from the mark word up rather than from the tutorial down. You have read
`java.util.concurrent` end to end at the jdk-21+35 tag: `AbstractQueuedSynchronizer` after Doug
Lea's 2019 rewrite — the bit-flag `WAITING`/`CANCELLED`/`COND` status, `ExclusiveNode`/`SharedNode`/
`ConditionNode`, the collapsed `acquire` method, and the backwards-from-tail walk that exists
because `prev` is set before the tail CAS and `next` after it; `ConcurrentHashMap`'s `sizeCtl` with
its four meanings, `spread`, `ReservationNode`, the strided cooperative `transfer` and the
`CounterCell` array; `ThreadPoolExecutor.ctl` packing three run-state bits and twenty-nine worker-
count bits, and the double-check after enqueue that almost every explanation omits; `Striped64`'s
probe, growth-to-`NCPU` policy and `@Contended` cells; `ForkJoinPool`'s `WorkQueue` deque protocol,
packed `ctl` and `tryCompensate`; `CompletableFuture`'s `volatile Object result`, `AltResult`/`NIL`
and Treiber stack of `Completion`s; and `VirtualThread` with `Continuation`, `StackChunk` and the
`sun.nio.ch.Poller` underneath it.

You read the JVM's own layer with the same fluency. You know the mark word is multiplexed, what
each tag-bit pattern means, what a displaced header is, when a lightweight lock inflates and what
an `ObjectMonitor`'s `_cxq`/`_EntryList`/`_WaitSet`/`_succ` do — and you know that biased locking
is **gone**, so the "biased → thin → fat" escalation story describes a JVM nobody is running. You
read generated code: `lock addl $0,(%rsp)` for a volatile write on x86, `ldar`/`stlr` on AArch64,
the C2 hoist that turns a missing-`volatile` stop flag into an infinite loop, `PAUSE` behind
`Thread.onSpinWait`. You read thread dumps line by line: the header fields, `nid` in hex as the
join key to `top -H`, `- locked` versus `- waiting to lock` versus `- parking to wait for`, the
"Locked ownable synchronizers" block, and the three signatures — contention, saturation, idleness
— that you can classify in thirty seconds.

Your authority order is: **JLS/JVMS > OpenJDK source at the release tag > JDK javadoc and the
`java.util.concurrent` package summary > JEP text > the JDK bug database and OpenJDK wiki >
engineer blog posts.** You never state a blog claim as fact when the specification says otherwise,
and you actively hunt version-stale folklore — `synchronized` pinning virtual threads, biased
locking, AQS's JDK 8 `waitStatus` encoding, `Thread.stop` being merely deprecated, `-Djdk.trace
PinnedThreads` still existing, structured concurrency being final, scoped values being preview —
and you correct each one while stating what used to be true, because interviewers still ask for
the old form.

You teach **mechanism, not usage**. "`volatile` flushes to main memory" is not an explanation and
is not even true; "a volatile write is a release store followed by a StoreLoad barrier, which on
x86 is `lock addl $0,(%rsp)` draining the store buffer, and the spec is written in happens-before
terms because MESI already made the caches coherent — nothing was ever stale in the cache, the
store buffer and the compiler were the problem" is. Every claim about cost, ordering, scheduling
or version behaviour is either derived on the page, measured, or quoted from source with the
quoted lines explained. Every number resolves to the latency ladder: L1 ≈ 1 ns, main memory ≈ 80–
100 ns, uncontended CAS ≈ 10–20 ns, park/unpark round trip ≈ 1–10 µs.

You are also an interview coach: you know which of these facts get asked, in what phrasing, and
what a strong 90-second answer sounds like versus a weak one that recites API names.

---

# CONTEXT

## Reader level

A backend Java engineer with 3–4 years of professional experience, writing Java 21 idiomatic code
daily (Spring Boot 3.x, records, streams, `Optional`), preparing for a senior/FAANG-level
interview loop.

**Assume they already know**, without re-teaching: how to start a thread and pass a `Runnable`;
what `synchronized` is for at the "stops two threads clashing" level; that `volatile` exists; how
to submit a task to an `ExecutorService` and call `Future.get()`; how to chain a
`CompletableFuture`; that `ConcurrentHashMap` is the thread-safe map; that deadlock is a thing;
generics syntax; `equals`/`hashCode`; big-O notation; the collections API surface; lambdas and
streams.

**Assume they do not have** the mechanism-level model underneath any of it. They cannot say why
`synchronized` gives *visibility* as well as exclusion; why `volatile int count; count++` is still
broken; what happens-before actually constrains and why it is not "earlier in time"; why the same
code passes on x86 and fails on Graviton; why `start()` twice throws `IllegalThreadStateException`
and not `IllegalStateException`; why `newFixedThreadPool` makes `maximumPoolSize` dead code; the
exact four-step `ThreadPoolExecutor` submission order; why an exception in a task submitted with
`submit` disappears; why an exception in a scheduled task cancels every future run; what runs
under the bin lock in `computeIfAbsent`; what `sizeCtl` is; what AQS's `state` means per
synchronizer; why `LongAdder.sum()` is racy; what false sharing costs; where a virtual thread's
stack lives and what unmounts it; what pinned on Java 21 and what JEP 491 changed in 24; or why
`jstack` cannot see their virtual threads. They have absorbed version-stale folklore from blogs
written between 2015 and 2023 — biased locking, the JDK 8 AQS source, the cache-flush myth. That
gap is the entire reason these notes exist.

## Purpose

These notes are a **detailed one-stop reference plus deep interview prep**. One document set the
reader never needs to supplement with a blog, a Stack Overflow answer, or a second book. They must
serve two readings equally well:

1. a first careful cover-to-cover read that builds the model from nothing, and
2. a night-before-the-interview re-read that reloads the numbers, the traps, the version dates and
   the answer shapes.

Coverage is driven by the topic, not by any individual reader's measured gaps. Write for every
reader of this level.

## Target version

**Java 21 LTS** is the baseline for every constant, signature and behaviour. Anything introduced,
changed or removed in Java 22–25 is marked inline with its version and, where it supersedes a
Java 21 behaviour, flagged as a version trap. Preview status is stated on every feature where it
applies — a feature being preview is itself the interview-relevant fact.

Whenever a behaviour, a constant, a default or an API shape differs across **Java 5 / 7 / 8 / 9+ /
15 / 19 / 21 / 24 / 25**, say which release does what, inline, at the point of the claim — not in
a footnote and not only in the version-history section. The two deltas that most often produce a
stale answer, and which you must get the *direction* of right:

1. **JEP 491 (Java 24): `synchronized` no longer pins virtual threads.** On Java 21 it does. So
   "replace `synchronized` with `ReentrantLock`" is a Java-21-scoped fix, not timeless advice.
   Native and FFM frames still pin on 24. `-Djdk.tracePinnedThreads` was removed in 24; the
   `jdk.VirtualThreadPinned` JFR event survives and was broadened.
2. **JEP 506 (Java 25): scoped values are final**, while **structured concurrency is still
   preview** (JEP 505 in 25, reworked to `open()` factories and a `Joiner` abstraction, then 525
   and 533). Saying it the other way round is a visible error.

## Adjacent topics

These sibling guides exist. This file owns the **concurrency model and its mechanism**. The
syllabus marks material owned elsewhere with `[X-REF nn]`.

For every `[X-REF nn]` leaf the rule is: **state the mechanism in one self-contained paragraph
here, give the reader enough to answer the interview question, then point to the sibling for the
full treatment.** Never send the reader away empty-handed, and never duplicate a sibling's full
chapter.

| Guide | Owns | What this file still owes the reader |
|---|---|---|
| 02 Java collections | `HashMap`/`ArrayList`/`TreeMap` internals, treeification, fail-fast iterators, the `equals`/`hashCode` contract | the *concurrent* counterparts and their concurrency semantics: `ConcurrentHashMap` internals, the three iterator-consistency models, `ConcurrentSkipListMap`, copy-on-write, why `Vector`/`Hashtable` are dead, why concurrent `HashMap` use corrupts — mechanism here, the data structure in 02 |
| 03 Java core | `final`, immutability design, exceptions, generics, `String`, `BigDecimal`, `java.time` | final-field semantics and the freeze action, safe publication of immutable objects, why `String` cannot change after publication, `SimpleDateFormat` vs `DateTimeFormatter` thread safety, `Duration` overloads — the concurrency half of each, then point |
| 04 Modern Java | the *user-facing* virtual-thread, structured-concurrency and scoped-value API, lambdas, streams, `Optional` | the **mechanism**: continuations, mounting/unmounting, `StackChunk`, the FIFO scheduler, pinning internals, `ThreadFlock`, `ScopedValue`'s binding chain; plus the common pool behind parallel streams and `Arrays.parallelSort` |
| 06 JVM internals | GC, JIT, class loading, heap dumps, JMH, the diagnostic toolchain | the mark word and object header, lock elision and coarsening, safepoints and TTSP as they touch concurrency, `StackChunk` as a GC'd object, the `OutOfMemoryError: unable to create native thread` path, JFR event names — one paragraph each, then point |
| 07 Spring core | the container, proxies, AOP, bean scopes | `spring.threads.virtual.enabled=true` and exactly what it switches, `@Async`, `TaskDecorator`, singleton beans as shared mutable state, `@Transactional`'s thread affinity |
| 08 Spring Data JPA | persistence context, entity lifecycle | `@Version` optimistic locking as the CAS of the persistence layer, the connection pool as the real bound after a virtual-thread migration |
| 09 SQL databases | isolation levels, MVCC, database locking | optimistic vs pessimistic concurrency as the same axis one layer down |
| 10 Networking | TCP, HTTP, timeouts, connection pooling | deadline propagation across hops, the socket backlog as the queue you moved your queue into |
| 11 OS and Linux | processes, scheduling, virtual memory, fds | context-switch mechanics and cost, `vmstat cs`/`pidstat -w`, futexes under park/unpark, `ulimit -u`/`-n`, `/proc/<pid>/task/<tid>/status` |
| 12 API design | idempotency, rate limiting, error contracts | idempotency keys as the distributed answer to atomicity, 429/503 shedding |
| 13 Web security | TOCTOU, leaked context | the `ThreadLocal` context-leak-in-a-pool as a security incident class |
| 14 Messaging and queues | brokers, delivery semantics, ordering | per-key ordering as the same confinement idea, poison messages and livelock, in-JVM queue vs broker |
| 15 Caching | eviction, stampede, Redis | `computeIfAbsent` vs Caffeine, the stampede as a concurrency problem |
| 16 Testing | JUnit, Mockito, Testcontainers | jcstress, JMH `@Group`/`@Threads`, Awaitility, the injected-executor design rule |
| 18 Cloud | leader election, distributed coordination | the distributed analogue table and why a distributed lock is weaker than a monitor |
| 19 Docker and Kubernetes | container limits | cgroup-aware `availableProcessors()`, `-XX:ActiveProcessorCount`, and every library that silently sizes off it |
| 20 Observability | metrics, logs, traces, JFR as a platform | executor metrics, queue time vs execution time, MDC propagation, JFR concurrency events |

## The example domain — QuizStakes

**Every example in these notes comes from the QuizStakes domain, reproduced in full below.
Never write `Dog extends Animal`, `Foo`, `Bar`, `thread1`, `Person`, `Employee` or any other
throwaway example.** Use these entities, these status codes, these numbers, verbatim. A reader
who meets `CLIENT_BONUS_RESERVED` once must meet the same name every time. Where a concept is
genuinely domain-free (a litmus test, a spin lock, a `park`/`unpark` permit), still frame it in
the domain: the shared counter is stake reservations per second, the bounded queue holds withdrawal
transactions awaiting a payment run, the lock protects a wallet's four buckets, the two threads in
the deadlock are transferring between two client accounts.

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

These are the numbers for every memory calculation, every sizing argument, every throughput claim.
Little's law is worked with 1,200 stake reservations/sec and the PSP's 240 ms p50 (288 concurrent
tasks) and again with the 11 s p99 (13,200). Pool sizing uses 8 cores, 90% utilisation, a 100 ms
downstream wait and 2 ms of compute. A contended counter is 3,400 settlements/sec through one
`AtomicLong`. A `CopyOnWriteArrayList` disaster is 2.8M appends. A virtual-thread footprint
argument uses 55k peak concurrent sessions.

---

# TASK

Write the complete Multithreading and Concurrency bible as a set of Markdown files under
`src/notes/detailed/05-multithreading-concurrency/`, organised into five parts, covering **all
1141 syllabus leaves reproduced in the `# SYLLABUS` section below**, illustrated by **all 218
diagrams enumerated in the `# DIAGRAM MANIFEST` section below**, written to the exact file paths
in the `# OUTPUT CONTRACT` section below.

## Tier structure

The notes are organised in these parts, in this order:

| Part | Contains |
|---|---|
| `PART 1 — BASICS` | why concurrency exists and what it costs, the OS substrate, the full `Thread` API surface and lifecycle, interruption, the thread-safety vocabulary, races and compound actions, `synchronized`, `volatile`, the Java Memory Model and happens-before, final fields and safe publication, `wait`/`notify`, atomics and CAS, explicit locks, synchronizers, the concurrent collections, `BlockingQueue`, the Executor framework, `ThreadPoolExecutor`, scheduling, `CompletableFuture`, fork/join, `ThreadLocal`, virtual threads, structured concurrency and scoped values, and liveness failures — with the guarantees each carries |
| `PART 2 — INTERMEDIATE` | the master cost/latency/footprint/guarantee tables, contention economics, choosing a synchronization primitive, pool and queue sizing derived rather than memorised, the atomicity decision, the concurrent-collection decision, producer–consumer and backpressure design, `CompletableFuture` in anger, virtual threads in production, thread-safe class design, context propagation, testing and verifying concurrent code, the concurrency-adjacent utility surface, concurrency beyond one JVM, and the Java 5 → 25 version delta |
| `PART 3 — ADVANCED (INTERNALS)` | how it actually works inside — the object header and mark word, thin locks/inflation/`ObjectMonitor`, the JIT optimisations that touch locks and memory, safepoints, `AbstractQueuedSynchronizer`, `LockSupport` and the OS layer, the JMM formally, `ConcurrentHashMap` internals, `Striped64` and false sharing, queue and executor internals, `ForkJoinPool` and work stealing, virtual-thread internals, and runtime observability |
| `PART 4 — BUILD IT` | complete, compiling, generic Java 21 reimplementations — locks from first principles, synchronizers on AQS, a bounded blocking queue three ways, non-blocking data structures, a thread pool from scratch, a work-stealing deque and mini fork/join, structured concurrency and futures from scratch, and the diagnostic/teaching harnesses — each followed by a "Diff vs the real one" table |
| `PART 5 — INTERVIEW AND RETENTION` | the 132 questions with full answers, the 55-item trap index, and the drills |

## Hard instructions

Every one of these is mandatory.

- **No line limit and no file-count limit.** There is no upper bound on the length of the notes
  or on how many files they are split across. Completeness beats brevity every single time.
  Never truncate, never write "and so on", never write "similar to the above", never defer a
  concept for space. If a file grows large, split it into more files rather than cutting
  content, and register the new file in `00-index.md`.
- **Output format is Markdown (`.md`).** Every file.
- **Diagrams are standalone SVG files.** Write each diagram as its own file in
  `src/notes/detailed/05-multithreading-concurrency/diagrams/`, named `D-NNN-short-slug.svg`, and
  embed it at the point of explanation with a Markdown image reference and a caption:

  ```
  ![D-042 — The ThreadPoolExecutor submission algorithm, in order](../diagrams/D-042-tpe-submission.svg)

  **D-042** — The `ThreadPoolExecutor` submission algorithm, in order.
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
  (structured concurrency, scoped values), say so on the snippet. Where a snippet is deliberately
  broken to demonstrate a bug, label it **broken** on the fence line and give the fixed version
  immediately after.
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
  3. **5 "predict the output" puzzles** — a complete code snippet, the actual output (or the set
     of legal outputs, where the JMM permits more than one — this topic is full of those), and an
     explanation of *why* the output is what it is.

  Where a part is split across many files, these three go in that part's interview file as named
  in the `# OUTPUT CONTRACT`, and cover the whole part.
- **Version-specific behaviour is always called out explicitly.** Whenever a behaviour, a
  constant, a default or an API shape differs across **Java 5 / 7 / 8 / 9+ / 15 / 19 / 21 / 24 /
  25**, say which version does what, inline, at the point of the claim. Where a widely-repeated
  claim is version-stale, state what is true today, what used to be true, and flag it as a version
  trap. **There are 31 `[VERSION-TRAP]` leaves in the syllabus below. The six that matter most
  are:**
  1. `synchronized` pins a virtual thread on Java 21 — JEP 491 removes that cause in Java 24, and
     `-Djdk.tracePinnedThreads` was removed with it, so "use `ReentrantLock`" is a version-scoped
     answer (1.8.18, 1.24.10, 2.9.7, 2.9.8, 3.2.18, 3.12.16),
  2. biased locking is **gone** — deprecated and disabled by JEP 374 in Java 15, later removed —
     so the "biased → thin → fat" escalation story is obsolete (3.2.14, 3.2.15),
  3. AQS was rewritten after JDK 14: bit-flag status (`WAITING = 1`, `CANCELLED = 0x80000000`,
     `COND = 2`) and `ExclusiveNode`/`SharedNode`/`ConditionNode` replaced the JDK 8 `waitStatus`
     encoding that almost every blog still describes (3.5.8, 3.5.9),
  4. `Thread.stop`/`suspend`/`resume` were **removed** in Java 20 and now throw
     `UnsupportedOperationException` — they are not merely deprecated (1.3.14),
  5. scoped values are final in Java 25 (JEP 506) while structured concurrency is still preview
     (JEP 505/525/533) — do not swap them (1.25.7, 1.25.14),
  6. compact object headers: experimental in Java 24 (JEP 450), on by default in Java 25 (JEP
     519), which also forces the monitor side-table redesign (3.1.6, 3.2.13).

  Sweep for the other 25 and treat every one the same way.
- **Tag obligations.** The syllabus tags below are instructions, not decoration:
  - `[PROVE]` — work the argument through on the page. Do not state the result. **~223 leaves.**
  - `[SOURCE]` — quote the real JDK source, JEP text, JLS text or javadoc (short excerpt) and
    explain every quoted line. **~178 leaves.**
  - `[BUILD]` — ship complete, compiling, generic code. **~97 leaves — all of Part 4, plus
    1.3.17, 1.14.11, 1.14.20, 1.17.16, 1.17.17, 1.18.10, 1.18.15, 1.19.10, 1.19.15, 1.21.8,
    1.21.24, 1.21.25, 1.22.10, 1.23.12, 1.26.5, 1.26.10, 1.26.16, 2.5.4, 2.5.6, 2.5.7, 2.7.8,
    2.8.2, 2.8.5, 2.8.6, 2.8.7, 2.8.8, 2.8.9, 2.12.3, 2.12.7, 2.12.8, 2.12.12, 3.1.7, 3.3.10,
    3.5.22, 3.9.10, 3.9.11, 3.10.7, 3.11.11, 3.13.10.**
  - `[TRAP]` — carry a `**Pitfall:**` marker: wrong belief, symptom, fix. **~196 leaves.**
  - `[RESEARCH]` — re-verify against the cited primary source before writing. **206 leaves carry
    this tag** (Part 1: 89, Part 2: 40, Part 3: 72, Part 4: 5). If you cannot verify a claim, say
    so explicitly in the text rather than asserting it.
  - `[VERSION-TRAP]` — state what is true in 21 and what changed. **31 leaves.**
  - `[X-REF nn]` — one self-contained mechanism paragraph here, then point to guide nn.
    **~122 leaves.**
  - `[NUM]` — state the number or byte arithmetic explicitly, with the arithmetic shown.
    **~113 leaves.**
  - `[ASM]` — show the generated machine code or the barrier and read it instruction by
    instruction. **9 leaves: 1.3.7, 1.9.7, 1.9.12, 1.13.1, 3.3.5, 3.3.6, 3.3.10 (tooling),
    3.7.11, 4.8.1.** Where you cannot produce real disassembly, state the instruction sequence
    from a cited source and say it is quoted, not captured.
  - `[DUMP]` — show real `jstack` / `jcmd` / JFR output and read it line by line. **~26 leaves.**
    Where you cannot capture a live dump, reproduce the exact documented format and say so.
- **Six figures are flagged in the syllabus's research pass as needing re-verification, because
  `openjdk.org` returned HTTP 403 to every direct fetch and the JEP text was read through search
  summaries and secondary sources. Do not print any of them without confirming it against primary
  source first, and if you cannot confirm it, say so in the text rather than asserting it:**
  1. `jdk.virtualThreadScheduler.maxPoolSize` defaulting to **256** (1.24.4, 2.9.9, 3.12.9) —
     confirm against `VirtualThread.java` at the jdk-21+35 tag or a running JDK 21,
  2. `ForkJoinPool` common-pool `maximumPoolSize` of **`256 + parallelism`** and
     `common.maximumSpares` of **256** (3.11.9, 3.11.13) — confirm against the `ForkJoinPool`
     javadoc,
  3. the mark-word tag-bit encoding (3.1.3) and the `ObjectMonitor` field names (3.2.7) — confirm
     against the OpenJDK HotSpot wiki page cited in `# REFERENCES`,
  4. the AQS post-14 bit-flag constants (3.5.9) — confirm against
     `AbstractQueuedSynchronizer.java` at the jdk-21 tag,
  5. every `ConcurrentHashMap` constant in 3.8.3 and 3.8.4 — re-read them from
     `ConcurrentHashMap.java`, not from the secondary article,
  6. the park/unpark and context-switch cost figures in 2.1.2 and 3.6.6 — no authoritative
     per-instruction table was found, so present them as order-of-magnitude, explicitly.
- **Two claims in the previous guide are wrong and must be corrected, not carried forward:**
  1. `src/topics/05-multithreading-concurrency.md` §2 says calling `start()` twice throws
     `IllegalStateException`. It throws **`IllegalThreadStateException`** (1.3.3). State the
     correct exception and name the confusion as a trap.
  2. That guide's §5 says volatile reads and writes "go to main memory (conceptually), never to a
     thread-local cached copy". This is the cache-flush myth. Restate it in happens-before terms,
     then describe the store-buffer / invalidate-queue reality and note that MESI already keeps
     caches coherent (1.9.5). Say plainly that the old phrasing predicts the wrong performance.
- **No emojis. No filler.** No "let's dive in", "great question", "as we all know", "it's worth
  noting". Lead with content.
- **A table for any comparison of three or more things.**
- **Every example uses the QuizStakes domain** as specified in `# CONTEXT`, with the entity
  names, status codes and numbers verbatim.
- The notes end with a flat `## Atomic concept checklist`, one bullet per distinct concept,
  phrased as a one-line assertion the reader can self-quiz against. Downstream agents parse this
  list, so keep it flat — no nesting, no headings inside it. Every checklist line already present
  in `src/topics/05-multithreading-concurrency.md` must survive verbatim or expanded (5.3.1).

## Leaf coverage

The syllabus below has **1141 leaves** (Part 1: 470, Part 2: 198, Part 3: 207, Part 4: 69,
Part 5: 197) across **65 numbered sections** — §1.1–§1.26, §2.1–§2.15, §3.1–§3.13, §4.1–§4.8,
§5.1–§5.3. (The syllabus's own footer says 69 sections; its section *ranges* enumerate 65, and the
ranges are what you must cover. The leaf count of 1141 is consistent either way.) **Every leaf
must appear in the notes.** Any leaf you cannot cover must
be listed in a `## Deferred` block at the end of the file that owns it, with the leaf number and a
one-line reason. An empty `## Deferred` block is the expected outcome.

---

# SYLLABUS

Reproduced in full, leaf for leaf. **69 sections, 1141 leaves.**

**Target version: Java 21 LTS** (baseline for every constant, signature and behaviour below).
Anything introduced, changed or removed in Java 22–25 is marked inline with its version and, where
it supersedes a Java 21 behaviour, with `[VERSION-TRAP]`. Preview status is stated on every leaf
where it applies — a feature being preview is itself the interview-relevant fact. The two big
version deltas this topic carries are **JEP 491 (Java 24): `synchronized` no longer pins virtual
threads**, and **JEP 506 (Java 25): scoped values final** / **JEP 505 → 525 → 533: structured
concurrency still preview**.

Scope boundary against the sibling guides: the collection *data structures* themselves live in
`02-java-collections.md` (this file owns only their concurrent counterparts and the concurrency
semantics), the language substrate (`final`, immutability design, exceptions, generics) in
`03-java-core.md`, the Java-8-to-21 language additions including the *user-facing* virtual-thread
and structured-concurrency API in `04-modern-java.md` (this file owns their **mechanism** —
continuations, mounting, scheduler, pinning internals), and GC / JIT / class loading / the
diagnostic toolchain in `06-jvm-internals.md`. Spring's threading model (`@Async`,
`@Transactional` and thread affinity, request-scoped beans) is in `07-spring-core.md`. Where a
concept is owned elsewhere the leaf carries `[X-REF nn]` and the bible states the mechanism in one
paragraph before pointing away — it never sends the reader off empty-handed.

Tag legend:

| Tag | Meaning for the write pass |
|---|---|
| `[PROVE]` | the bible must work the argument through, not state the result |
| `[SOURCE]` | must quote real JDK source, JEP text or JLS text (short excerpt) and explain every line |
| `[BUILD]` | must ship complete, compiling, generic code |
| `[TRAP]` | must carry a `**Trap:**` marker — wrong belief, symptom, fix (rendered in the notes as `**Pitfall:**`) |
| `[RESEARCH]` | leaf exists because of the research phase; re-verify against the cited source before writing |
| `[VERSION-TRAP]` | widely-repeated claim that is version-stale; state what is true in 21 and what changed |
| `[X-REF nn]` | one-paragraph mechanism here, full treatment in guide nn |
| `[NUM]` | must state the number / byte arithmetic explicitly |
| `[ASM]` | must show the generated machine code or barrier and read it instruction by instruction |
| `[DUMP]` | must show real `jstack` / `jcmd` / JFR output and read it line by line |

---

# PART 1 — BASICS

## §1.1 Why concurrency exists at all

1.1.1 The three independent motivations, which are constantly conflated: **throughput** (more work
      per second), **latency** (one request finishes sooner by doing its sub-parts in parallel), and
      **responsiveness/blocking-tolerance** (a thread waiting on I/O must not stop the others).
1.1.2 The hardware forcing function: single-core clock scaling stalled around 2004–2006 (the
      "free lunch is over" moment), so performance since arrives as more cores, not faster cores.
      `[RESEARCH]`
1.1.3 Concurrency versus parallelism: concurrency is a *structuring* property (tasks are
      independent and interleavable), parallelism is an *execution* property (tasks actually run at
      the same instant). A single-core machine runs concurrent code with zero parallelism. `[TRAP]`
1.1.4 The three costs you pay for it: correctness risk (races), liveness risk (deadlock, livelock,
      starvation), and performance risk (context switches, cache coherence traffic, contention).
1.1.5 Amdahl's law: speedup ≤ 1 / (S + (1−S)/N), where S is the serial fraction. Worked with
      S = 0.05 and N = 64 to show the ceiling of 15.4×, not 64×. `[PROVE]` `[NUM]`
1.1.6 The universal scalability law as the correction to Amdahl: coherence cost makes the curve
      turn *downward* past a peak, which is why adding threads can make a system slower.
      `[RESEARCH]`
1.1.7 Little's law: L = λW (concurrency = throughput × latency). The sizing tool for pools,
      connection pools and virtual-thread counts. `[PROVE]` `[NUM]`
1.1.8 Where the thread count comes from in a server: one per connection (classic), a bounded pool
      (Java 5 through 21), one per request with virtual threads (Java 21+), or an event loop with
      callbacks (Netty/reactive). Four models, one axis.
1.1.9 Why Java made threads a first-class language feature in 1.0 rather than a library, and the
      historical cost of that choice: `Thread.stop`/`suspend`/`resume`, monitors on every object,
      and `Object.wait` on the root class.
1.1.10 The "thread-per-request until you can't" rule and why virtual threads restore it after
       fifteen years of reactive workarounds.

*(10 leaves)*

## §1.2 Processes, threads, and what the OS actually does

1.2.1 A process owns a virtual address space, a file-descriptor table, and at least one thread; the
      OS isolates processes with page tables. `[X-REF 11]`
1.2.2 A thread is the unit of *scheduling*: a program counter, a register set, a stack, and
      scheduler bookkeeping.
1.2.3 The share/own split, stated exactly: threads in one process **share** the heap, static
      fields, metaspace, the code cache, and the fd table; each **owns** its stack, PC, registers,
      and thread-local storage. Every concurrency bug lives in the shared half. `[X-REF 06]`
1.2.4 Why locals are automatically thread-safe (they live on the owning stack and are unreachable
      from other threads) — and the exception: a local *reference* to a shared object is not.
      `[TRAP]`
1.2.5 Java threads today are 1:1 with OS threads (the `NativeThread` / `pthread_create` model);
      green threads existed in JDK 1.1 on Solaris and were removed in 1.3. Virtual threads are the
      M:N model returning. `[RESEARCH]`
1.2.6 Context switch mechanics: save registers, switch stack pointer, possibly switch address space
      (process switch only), reload TLB and pollute L1/L2. Cost order of magnitude: ~1–10 µs direct,
      plus tens of µs of cache-refill penalty. `[NUM]` `[RESEARCH]`
1.2.7 Voluntary versus involuntary context switch, and how to see the counts (`vmstat cs`,
      `pidstat -w`, `/proc/<pid>/status voluntary_ctxt_switches`). `[X-REF 11]`
1.2.8 Platform thread stack reservation: default ~1 MB on 64-bit Linux (`-Xss1m`), reserved
      virtual, committed lazily page by page. 10 000 platform threads ≈ 10 GB of reserved address
      space. `[NUM]`
1.2.9 The rest of a platform thread's footprint: the `java.lang.Thread` object, the JVM-internal
      `JavaThread`, the OS `task_struct`, and the guard page. Roughly 1 KB of Java-heap object for
      megabytes of stack. `[NUM]`
1.2.10 OS scheduling: time slices, priority, CFS versus real-time classes, and why Java thread
       priorities (1–10, `Thread.MIN_PRIORITY`/`NORM_PRIORITY`/`MAX_PRIORITY` = 1/5/10) are advisory
       and largely ignored on Linux. `[TRAP]` `[NUM]`
1.2.11 Daemon versus non-daemon threads: the JVM exits when the last non-daemon thread dies;
       `setDaemon` must be called before `start()`; daemon threads are killed abruptly with no
       `finally` blocks run. `[TRAP]`
1.2.12 Thread groups: `ThreadGroup` is a legacy API, effectively deprecated for management
       (`ThreadGroup.stop/suspend/resume` removed, `destroy`/`allowThreadSuspension` degraded in 16
       and 19), retained only because `Thread` requires a group. `[RESEARCH]` `[VERSION-TRAP]`
1.2.13 `Thread.currentThread()`, `getId()` (deprecated in 19) versus `threadId()` (Java 19+),
       `getName`/`setName`, `isAlive`, `isVirtual` (Java 21). `[RESEARCH]`
1.2.14 The thread-naming discipline: a pool thread must be named for the workload
       (`order-ingest-3`, not `pool-2-thread-3`), because the thread dump is read by a human at
       3 a.m.
1.2.15 Where the thread limit actually comes from in production: `ulimit -u`, `threads-max`,
       `pid_max`, container `pids.max`, and the `OutOfMemoryError: unable to create native thread`
       that results. `[X-REF 06]` `[X-REF 11]`

*(15 leaves)*

## §1.3 The `Thread` API surface in Java 21

1.3.1 Construction: `new Thread(Runnable)`, the name/group/stackSize overloads, and why the
      `stackSize` parameter is a hint the VM may ignore.
1.3.2 `start()` versus `run()`: `start` asks the VM to create a native thread and invoke `run` on
      it; calling `run()` directly executes on the caller's thread with no concurrency at all.
      `[TRAP]`
1.3.3 `start()` twice throws `IllegalThreadStateException` (not `IllegalStateException` — the
      current guide's wording must be corrected). `[TRAP]` `[SOURCE]`
1.3.4 Subclassing `Thread` versus passing a `Runnable`: composition wins because a task is not a
      thread, and because virtual threads make `Thread` subclassing impossible
      (`Thread.ofVirtual()` returns a final internal class). `[TRAP]`
1.3.5 `Thread.sleep(long)`, `sleep(long,int)`, `sleep(Duration)` (Java 19+). Sleep does **not**
      release monitors — JLS 17.3 says so explicitly. `[SOURCE]` `[TRAP]`
1.3.6 JLS 17.3: neither `sleep` nor `yield` has any synchronization semantics; the compiler is free
      to cache non-volatile reads across them. This kills the "add a sleep and it works" fix.
      `[SOURCE]` `[PROVE]` `[TRAP]`
1.3.7 `Thread.yield()` as a scheduling hint with no guarantee; `Thread.onSpinWait()` (Java 9,
      compiles to `PAUSE` on x86, `YIELD`/`ISB` on AArch64) as the *correct* busy-wait hint.
      `[NUM]` `[ASM]` `[RESEARCH]`
1.3.8 `join()`, `join(long)`, `join(Duration)` (Java 19+); `join` is implemented on
      `wait`/`isAlive` for platform threads, which is why `synchronized(thread)` in user code
      breaks it. `[TRAP]` `[SOURCE]`
1.3.9 `Thread.State` enumeration — the six constants, with the exact `Thread.getState()` mapping.
1.3.10 `Thread.UncaughtExceptionHandler`: per-thread handler, `ThreadGroup` fallback, and
       `Thread.setDefaultUncaughtExceptionHandler`. An uncaught exception kills the thread silently
       unless one is installed. `[TRAP]`
1.3.11 `Thread.Builder`, `Thread.ofPlatform()`, `Thread.ofVirtual()` (Java 21 final): `name`,
       `name(prefix,start)`, `daemon`, `priority`, `stackSize`, `inheritInheritableThreadLocals`,
       `uncaughtExceptionHandler`, `unstarted`, `start`, `factory`. `[RESEARCH]`
1.3.12 `Thread.startVirtualThread(Runnable)` as the one-liner.
1.3.13 `Thread.getAllStackTraces()`, `Thread.dumpStack()`, `getStackTrace()` — and their cost
       (safepoint).  `[X-REF 06]`
1.3.14 Removed and degraded members and their release: `stop()` (removed for good in 20, throws
       `UnsupportedOperationException`), `suspend`/`resume` (removed in 20+),
       `countStackFrames`, `checkAccess`, `getId` deprecated. `[RESEARCH]` `[VERSION-TRAP]`
1.3.15 Why `Thread.stop` was unfixable: it threw `ThreadDeath` at an arbitrary bytecode, released
       every monitor the thread held, and left every guarded invariant broken. `[PROVE]`
1.3.16 `Runnable` versus `Callable<V>`: `call()` returns a value and declares `throws Exception`;
       `run()` does neither. This is why executors accept `Callable` and why exceptions from
       `Runnable` need a handler. `[X-REF 04]`
1.3.17 `ThreadFactory` — the one-method interface every pool should be given, so that names,
       daemon-ness and the uncaught-exception handler are set in one place. `[BUILD]`
1.3.18 `Thread.holdsLock(Object)` as an assertion tool for monitor invariants.

*(18 leaves)*

## §1.4 Thread lifecycle and states

1.4.1 `NEW` — constructed, `start()` not yet called.
1.4.2 `RUNNABLE` — running *or* runnable-and-waiting-for-a-CPU. Java does not distinguish the two.
1.4.3 A thread blocked in a socket read or a file read reports `RUNNABLE`, because the JVM has no
      idea the OS descheduled it. This surprises everyone reading a thread dump. `[TRAP]` `[DUMP]`
1.4.4 `BLOCKED` — waiting to *enter* a `synchronized` monitor (or to re-enter after `wait`).
1.4.5 `WAITING` — `Object.wait()`, `Thread.join()`, `LockSupport.park()` with no timeout.
1.4.6 `TIMED_WAITING` — `sleep`, `wait(t)`, `join(t)`, `parkNanos`, `parkUntil`.
1.4.7 `TERMINATED` — `run` returned or threw.
1.4.8 The state transition diagram, including the `wait` → `BLOCKED` → `RUNNABLE` path on wake
      (a notified thread must re-acquire the monitor, so it passes through BLOCKED).
1.4.9 **Trap:** BLOCKED and WAITING mean different things in a dump. A pile of BLOCKED threads is a
      lock-contention incident — find the owner. A pile of WAITING threads on a pool queue is
      normal idle. `[TRAP]` `[DUMP]`
1.4.10 There is no `RUNNING` state and no way to ask "am I on a CPU right now" from Java.
1.4.11 `getState()` is a sampled approximation, documented as "for monitoring, not synchronization
       control" — never branch on it. `[TRAP]` `[SOURCE]`
1.4.12 Virtual thread states: a virtual thread also reports the six `Thread.State` values, but
       `WAITING` for a virtual thread means unmounted and parked, costing no OS thread. The
       internal states (`NEW`, `STARTED`, `RUNNING`, `PARKING`, `PARKED`, `PINNED`, `YIELDING`,
       `TERMINATED`) are visible only in `jcmd Thread.dump_to_file -format=json`. `[RESEARCH]`
       `[DUMP]`

*(12 leaves)*

## §1.5 Interruption and cancellation

1.5.1 Java has **no** preemptive cancellation. Interruption is a cooperative protocol and nothing
      more.
1.5.2 The three methods and their differing semantics: `t.interrupt()` sets the flag;
      `t.isInterrupted()` reads it without clearing; **static** `Thread.interrupted()` reads *and
      clears* it for the current thread. `[TRAP]`
1.5.3 A blocking method that declares `InterruptedException` throws it **and clears the flag** — so
      a catch block that neither rethrows nor restores the flag has destroyed the cancellation
      request. `[TRAP]` `[PROVE]`
1.5.4 The two legal responses to `InterruptedException`: propagate it, or restore the flag with
      `Thread.currentThread().interrupt()`. `catch (InterruptedException e) { }` is always a bug.
      `[TRAP]`
1.5.5 The complete inventory of interruptible blocking points: `Object.wait`, `Thread.sleep`,
      `Thread.join`, `BlockingQueue.put/take`, `Lock.lockInterruptibly`, `Condition.await`,
      `Semaphore.acquire`, `CountDownLatch.await`, `CyclicBarrier.await`, `Future.get`,
      `LockSupport.park` (returns rather than throws), `InterruptibleChannel` operations,
      `Selector.select`. `[RESEARCH]`
1.5.6 What is **not** interruptible: `synchronized` acquisition (a thread BLOCKED on a monitor
      cannot be interrupted out of it), `InputStream.read` on a plain socket, and `FileChannel`
      reads on some platforms. This is a real ReentrantLock-over-synchronized argument. `[TRAP]`
1.5.7 `LockSupport.park()` returns spuriously *and* on interrupt without clearing the flag — always
      re-check the condition in a loop. `[TRAP]`
1.5.8 Interrupting a thread blocked on a socket: close the socket. `Socket.close` /
      `ServerSocket.close` is the cancellation mechanism there; `InterruptibleChannel` closes itself
      and throws `ClosedByInterruptException`. `[RESEARCH]`
1.5.9 The cancellation-policy idea: a task must document *how* it may be cancelled, and only its
      owner may set the interrupt status.
1.5.10 `Future.cancel(boolean mayInterruptIfRunning)`: `false` only prevents an unstarted task from
       starting; `true` interrupts the running thread — which does nothing at all if the task never
       checks. `[TRAP]`
1.5.11 Poison pills as the alternative cancellation protocol for producer/consumer, and their
       requirement of one pill per consumer (or an unbounded-consumer rendezvous).
1.5.12 Shutdown hooks: `Runtime.getRuntime().addShutdownHook(Thread)`, run concurrently, no ordering
       guarantee, killed by `SIGKILL`, and *not* run on `Runtime.halt`. `[X-REF 06]`
1.5.13 The `finally`-must-restore rule when a thread you do not own passes through your code (an
       executor task): restore the flag on exit.
1.5.14 Timeouts as cancellation: every blocking call in a service should have a deadline, and the
       deadline should be propagated, not restarted at each hop. `[X-REF 10]`

*(14 leaves)*

## §1.6 Thread safety — the vocabulary

1.6.1 Definition: a class is thread-safe when it behaves correctly under any interleaving of
      accesses by multiple threads, **with no additional synchronization on the caller's part**.
      `[SOURCE]`
1.6.2 "Correctly" means it preserves its invariants and its postconditions — thread safety is
      meaningless without a stated invariant. `[PROVE]`
1.6.3 The five-level thread-safety taxonomy: immutable, thread-safe, conditionally thread-safe,
      thread-compatible (safe with external synchronization), thread-hostile. `[RESEARCH]`
1.6.4 State ownership: a class owns the state it encapsulates; shared ownership (a collection you
      hand out) is the root of most bugs. Split ownership (a container owns the structure, the
      caller owns the elements).
1.6.5 Thread confinement, three kinds: ad-hoc (by convention — fragile), stack confinement (locals
      and non-escaping references), and `ThreadLocal` (explicit).
1.6.6 Instance confinement: guard state with a private lock and never let a reference escape — the
      Java monitor pattern.
1.6.7 The `@GuardedBy("lock")` annotation from JCiP / JSR-305 as executable documentation, and
      what ErrorProne does with it. `[RESEARCH]`
1.6.8 `@ThreadSafe`, `@NotThreadSafe`, `@Immutable` annotations and why the javadoc of a class
      *must* state its policy.
1.6.9 Atomicity, visibility, ordering — the three independent properties. A construct can give one
      without the others; almost every misconception is a conflation of two of them. `[TRAP]`
1.6.10 Escaping: publishing a reference to internal mutable state, and the four ways it happens
       (returning it, storing it in a public field, passing it to an alien method, and `this`
       escaping from a constructor). `[TRAP]`
1.6.11 The alien-method rule: never call a method you do not control while holding a lock, because
       it may block, call back, or acquire another lock.
1.6.12 Invariants that span multiple variables must be guarded by a **single** lock; two atomics do
       not make one atomic pair. `[TRAP]` `[PROVE]`
1.6.13 Effectively immutable and safely published objects as a design escape hatch.

*(13 leaves)*

## §1.7 Races and the compound-action problem

1.7.1 Race condition defined: correctness depends on the relative timing of threads. Distinct from
      a *data race*, which is the JMM's term for two conflicting accesses unordered by
      happens-before. A program can have a race condition with no data race, and vice versa.
      `[TRAP]` `[PROVE]`
1.7.2 Read-modify-write: `count++` is `getfield` / `iconst_1` / `iadd` / `putfield` — four
      bytecodes, three logical steps. Show the lost-update interleaving as a table. `[PROVE]`
1.7.3 Check-then-act: `if (absent) put`, lazy initialisation, "file exists then open".
1.7.4 Put-if-absent, read-modify-write and compare-and-swap as the three compound-action shapes
      that need atomicity.
1.7.5 Time-of-check-to-time-of-use (TOCTOU) as the same bug in the security literature.
      `[X-REF 13]`
1.7.6 The three fixes: a lock, an atomic variable, or an atomic API on a concurrent collection.
      Choosing between them is §2.5.
1.7.7 Why `synchronized` on *both* the check and the act, using the same lock, is required — not
      one synchronized method each. `[TRAP]`
1.7.8 The 64-bit non-atomicity rule (JLS 17.7): a non-volatile `long`/`double` write may be split
      into two 32-bit writes, so a reader can see a torn value assembled from two different writes.
      References are always atomic. `[SOURCE]` `[NUM]` `[TRAP]`
1.7.9 Word tearing (JLS 17.6): the JMM forbids it — updating one `byte` of a `byte[]` must not
      corrupt its neighbours, even though the hardware may not have byte stores. `[SOURCE]`
1.7.10 Why "it works on my machine" usually means x86-TSO, and the identical code fails on AArch64
       (Graviton, Apple silicon) where stores may be reordered with other stores. `[PROVE]`
       `[RESEARCH]`
1.7.11 Non-atomic composite state: `size` and `elements` in a hand-rolled collection; the
       invariant-across-fields problem.
1.7.12 The infinite-loop race: an unsynchronised `HashMap` resized concurrently in Java 7 could
       create a cycle in a bucket list and spin a CPU at 100% forever. Java 8 removed the cycle but
       concurrent use still loses entries and corrupts size. `[X-REF 02]` `[TRAP]` `[RESEARCH]`

*(12 leaves)*

## §1.8 `synchronized`

1.8.1 Every Java object has an associated **monitor** (an intrinsic lock). There is no separate
      lock object to create.
1.8.2 The two guarantees, both of which must be stated: **mutual exclusion** and **visibility**.
      Forgetting the second is the most common gap in this topic. `[TRAP]`
1.8.3 The formal visibility rule: an unlock of monitor *m* happens-before every subsequent lock of
      *m* (JLS 17.4.4 synchronizes-with). `[SOURCE]`
1.8.4 Reentrancy: acquisition is per-thread with a hold count, so a synchronized method may call
      another synchronized method on the same object. POSIX mutexes are not reentrant by default;
      Java's are. `[PROVE]`
1.8.5 Why reentrancy is necessary: a subclass override calling `super.method()` would otherwise
      self-deadlock. `[PROVE]`
1.8.6 The three syntactic forms and the three *different* monitors they take:
      `synchronized void m()` → `this`; `static synchronized void s()` → `MyClass.class`;
      `synchronized (obj) { }` → `obj`.
1.8.7 **Trap:** an instance method and a static method of the same class do not exclude each other.
      `[TRAP]`
1.8.8 **Trap:** locking on a field you later reassign — the monitor changes underneath the waiting
      threads. Use `private final Object lock = new Object();` `[TRAP]`
1.8.9 **Trap:** locking on a `String` literal, an interned string, a boxed `Integer` in
      −128..127, `Boolean.TRUE`, or a `Class` object you do not own. These are JVM-wide shared
      objects, so unrelated code can deadlock with you. `[X-REF 03]` `[TRAP]`
1.8.10 **Trap:** two threads synchronizing on *different* objects get neither exclusion nor
       visibility. Guarding shared state means always the same lock. `[TRAP]`
1.8.11 The monitor is released on normal exit **and** on an exception — the compiler emits a
       synthetic exception handler with `monitorexit`. `[SOURCE]`
1.8.12 Bytecode: a synchronized *block* compiles to `monitorenter`/`monitorexit` pairs; a
       synchronized *method* sets the `ACC_SYNCHRONIZED` flag and the JVM locks on entry — no
       bytecodes at all. Show `javap -c` for both. `[SOURCE]` `[PROVE]`
1.8.13 Lock granularity: method-level synchronization serialises everything; the narrowest block
       that preserves the invariant is the target, but never split so finely that the invariant
       breaks between blocks. `[TRAP]`
1.8.14 Never hold a lock across I/O, a network call, a `sleep`, or a callback into unknown code.
1.8.15 Static synchronized methods and class-level state; the `Class` object as a lock and the
       class-initialisation lock that is *not* the same thing. `[TRAP]`
1.8.16 `synchronized` on a constructor is illegal; on an abstract method it is meaningless (it is
       not part of the signature and is not inherited). `[TRAP]` `[RESEARCH]`
1.8.17 Double-locking pitfalls with nested synchronized blocks — the entry point to §1.28.
1.8.18 `synchronized` under virtual threads in Java 21: pins the carrier. In Java 24+ (JEP 491) it
       does not. `[VERSION-TRAP]` `[RESEARCH]`

*(18 leaves)*

## §1.9 `volatile`

1.9.1 The three things `volatile` gives: visibility, ordering (barriers), and atomicity of 64-bit
      reads and writes.
1.9.2 Visibility precisely: a read of a volatile field always returns the value written by the
      last write to it in the synchronization order — no thread-local staleness, and the JIT may
      not hoist the read out of a loop. `[SOURCE]`
1.9.3 Ordering precisely: a volatile write happens-before every subsequent volatile read of the
      same field, and everything visible to the writer before the write becomes visible to the
      reader after the read. This is what makes it a publication mechanism. `[PROVE]`
1.9.4 What `volatile` does **not** give: atomicity of compound operations. `volatile int count;
      count++;` is still broken. `[TRAP]` `[PROVE]`
1.9.5 **Trap — the "flushes to main memory" myth.** The spec is written in terms of
      happens-before, not caches. On real hardware the write drains the store buffer and the read
      drains the invalidate queue; cache coherence (MESI) already made caches consistent. Saying
      "volatile bypasses the cache" is wrong and it predicts the wrong performance.
      `[TRAP]` `[RESEARCH]`
1.9.6 The four correct uses: a stop/status flag, a one-way state transition, a safe-publication
      reference, and the reference in double-checked locking. Plus the "independent observation"
      and "cheap read-write lock" patterns from JCiP. `[RESEARCH]`
1.9.7 The stop-flag example, and why without `volatile` the JIT is entitled to hoist the read out
      of the loop and produce an infinite loop — a reproducible bug, not a theoretical one.
      `[PROVE]` `[ASM]`
1.9.8 The wrong uses: counters, accumulators, and anything whose new value depends on the old.
1.9.9 `volatile` on an array reference protects the reference, **not** the elements. Element
      writes are plain. Use `AtomicIntegerArray` or a `VarHandle`. `[TRAP]`
1.9.10 `volatile` on a reference to a mutable object publishes the reference safely but says
       nothing about later mutations of the object's fields. `[TRAP]`
1.9.11 `volatile` is illegal on `final` fields (the combination is contradictory) and on local
       variables. `[TRAP]`
1.9.12 The cost: a volatile read on x86 is a plain `mov` (free); a volatile write is a
       `lock addl $0,(%rsp)` or `xchg` — a full StoreLoad barrier, roughly the cost of an
       uncontended CAS. Reads cheap, writes not. `[NUM]` `[ASM]` `[PROVE]`
1.9.13 Volatile versus `AtomicInteger.get/set`: identical memory semantics; the atomic adds the
       compound operations. `AtomicInteger.set` is `putVolatile`, `lazySet`/`setRelease` is the
       weaker release store. `[PROVE]`
1.9.14 The volatile-write-then-volatile-read publication idiom, and the piggyback rule: any write
       *before* the volatile write is published, not just the volatile field.

*(14 leaves)*

## §1.10 The Java Memory Model and happens-before

1.10.1 Why a memory model exists at all: without one, "what value may a read return" is undefined,
       and no portable concurrent program can be written. The JMM is a contract between the
       programmer, the compiler, the JIT and the hardware. `[SOURCE]`
1.10.2 JSR-133 (2004) replaced the broken JDK 1.4 model; the deliverable landed as JLS chapter 17
       and is unchanged in structure through Java 21. `[RESEARCH]`
1.10.3 What was broken before JSR-133: final fields could appear to change value (the `String`
       example), volatile writes could be reordered with non-volatile writes, and double-checked
       locking was unfixable. `[RESEARCH]` `[PROVE]`
1.10.4 JLS 17.4.1 shared variables: heap memory — instance fields, static fields, array elements.
       Locals, parameters and catch parameters are never shared. `[SOURCE]`
1.10.5 Conflicting access: two accesses to the same variable where at least one is a write.
       `[SOURCE]`
1.10.6 JLS 17.4.2 inter-thread actions and the action tuple `<t, k, v, u>`: thread, kind, variable
       or monitor, unique id. The kinds: normal read/write, volatile read/write, lock, unlock,
       thread start/termination detection, interrupt, external action, thread divergence action.
       `[SOURCE]`
1.10.7 JLS 17.4.3 program order and sequential consistency; sequential consistency is the *model*
       we reason with, not what the machine provides. `[SOURCE]`
1.10.8 JLS 17.4.4 synchronization order and the **synchronizes-with** relation — the six edges:
       unlock/lock on the same monitor, volatile write/read of the same field, thread start,
       default initialisation, thread termination detection (`join`, `isAlive`), and interrupt/
       detect-interrupt. `[SOURCE]`
1.10.9 JLS 17.4.5 happens-before = transitive closure of program order and synchronizes-with, plus
       the constructor-to-finalizer edge. Only four rules; every "rule list" you have seen is
       derived corollaries. `[SOURCE]` `[PROVE]`
1.10.10 The working list of derived edges, which is what interviews want: program order; monitor
        unlock → subsequent lock; volatile write → subsequent read; `start()` → first action;
        last action → successful `join()`; default initialisation → everything; transitivity;
        final-field freeze; and the `java.util.concurrent` edges.
1.10.11 The `java.util.concurrent` memory-consistency guarantees, quoted from the package summary:
        placing into a concurrent collection → removal; `Runnable` submission → execution start;
        the async computation → `Future.get`; `Lock.unlock`/`Semaphore.release`/
        `CountDownLatch.countDown` → the matching acquire; `Exchanger.exchange` pairs; actions
        before `CyclicBarrier.await`/`Phaser.awaitAdvance` → the barrier action → the return.
        `[SOURCE]` `[RESEARCH]`
1.10.12 Data race defined: conflicting accesses not ordered by happens-before. Correctly
        synchronized program: every sequentially consistent execution is data-race-free.
        `[SOURCE]`
1.10.13 The DRF-SC guarantee ("the fundamental theorem"): a data-race-free program behaves as if
        sequentially consistent, so you can reason with interleavings and stop thinking about
        barriers. `[PROVE]`
1.10.14 Happens-before does **not** mean "happens before in time". It is a visibility and ordering
        constraint; two actions with no edge may still execute in any order and the JIT may still
        reorder them. `[TRAP]` `[PROVE]`
1.10.15 Happens-before is not symmetric and not total: it is a partial order.
1.10.16 The "benign data race" claim, and why it is almost always wrong (the JIT may re-read, may
        fold, may prove an unreachable branch). The one accepted case: racy single-check lazy
        initialisation of an immutable value. `[TRAP]` `[PROVE]`
1.10.17 JLS 17.4.6–17.4.7 executions and well-formed executions: the eight-tuple, the write-seen
        function W, the value-written function V, and the five well-formedness constraints.
        `[SOURCE]`
1.10.18 JLS 17.4.8 causality and committed-action sets — the machinery that forbids out-of-thin-air
        values while still permitting aggressive optimisation. `[SOURCE]` `[PROVE]`
1.10.19 The out-of-thin-air problem, with the classic `r1 = x; y = r1; r2 = y; x = r2` example and
        why `r1 == r2 == 42` must be forbidden. `[PROVE]` `[RESEARCH]`
1.10.20 JLS 17.4.9 observable behaviour and non-terminating executions: why an infinite loop with
        no side effects lets the compiler do surprising things (and the C++ contrast). `[RESEARCH]`
1.10.21 The known open problem: the JMM's causality rules are not compositional and are still
        being reworked (JEP draft "Java Memory Model update"); interview-safe answer is "17.4.8 is
        the formal part nobody applies by hand". `[RESEARCH]`
1.10.22 Reordering sources, in order of who does it: source-to-bytecode (almost none), the JIT
        (lots), the CPU's out-of-order engine, the store buffer, and the cache coherence protocol.
1.10.23 The four reordering categories named as barriers: LoadLoad, LoadStore, StoreStore,
        StoreLoad — and which of them x86 permits (only StoreLoad). `[NUM]` `[PROVE]`
1.10.24 The roach-motel rule: the compiler may move code *into* a synchronized block but not out of
        it. Acquire prevents later actions from moving before; release prevents earlier actions
        from moving after. `[PROVE]`
1.10.25 What the JMM says about `Thread.sleep`, `yield` and `onSpinWait`: nothing. No
        synchronization semantics. `[SOURCE]` `[TRAP]`
1.10.26 What the JMM says about `System.out.println` and logging: nothing formally, but they
        contain internal synchronization, which accidentally fixes racy code in debugging and is
        why "it only fails without the print statement" happens. `[TRAP]` `[PROVE]`

*(26 leaves)*

## §1.11 Final fields, safe publication, and initialisation

1.11.1 JLS 17.5: a thread that sees a reference to a **correctly constructed** object is guaranteed
       to see the correctly initialised values of that object's `final` fields, with no
       synchronization at all. `[SOURCE]`
1.11.2 The **freeze** action at the end of the constructor, and the memory-chain / dereference-chain
       machinery that makes the guarantee transitive to objects reachable *through* final fields.
       `[SOURCE]` `[PROVE]`
1.11.3 "Correctly constructed" = `this` did not escape during construction. One escaped `this` and
       the whole guarantee evaporates. `[TRAP]` `[PROVE]`
1.11.4 The four ways `this` escapes from a constructor: registering a listener, starting a thread,
       passing `this` to a static factory/registry, and an overridable method called from the
       constructor. `[TRAP]`
1.11.5 The safe-construction idiom: private constructor plus a static factory that publishes only
       after construction completes. `[BUILD]`
1.11.6 JLS 17.5.2 reading final fields during construction: a read before assignment sees the
       default value. `[SOURCE]` `[TRAP]`
1.11.7 JLS 17.5.3 subsequent modification of final fields by reflection; freeze happens again after
       each reflective set, and constant-folded fields may never observe the change.
       `[SOURCE]` `[TRAP]`
1.11.8 JLS 17.5.4 write-protected fields: `System.in`/`out`/`err` are `static final` but mutable
       through `setIn`/`setOut`/`setErr`, and are explicitly excluded from final semantics.
       `[SOURCE]` `[RESEARCH]`
1.11.9 Why `String` is safe: its `hash` field is a non-final benign race, but `value` is final, so
       the JSR-133 guarantee is exactly what stops a `String` "changing" after publication.
       `[X-REF 03]` `[PROVE]`
1.11.10 Publication defined: making a reference visible outside its current scope. Unsafe
        publication defined: doing so without a happens-before edge.
1.11.11 The unsafe-publication failure mode in detail: the reference store and the constructor's
        field stores can be reordered, so another thread sees a non-null reference to a
        partially-constructed object with default-valued fields. `[PROVE]`
1.11.12 The five safe-publication mechanisms: a static initializer; a `volatile` field or
        `AtomicReference`; a `final` field of a properly constructed object; a field guarded by a
        lock read under the same lock; and any `java.util.concurrent` collection or executor.
1.11.13 Effectively immutable objects: mutable type, never mutated after publication — safe if
        safely published.
1.11.14 Mutable objects: must be safely published *and* guarded by a lock for every access.
1.11.15 Double-checked locking, the broken version and why it is broken. `[PROVE]` `[TRAP]`
1.11.16 Double-checked locking, the correct version with `volatile`, and the reason `volatile`
        fixes it (the write to `instance` cannot float above the constructor's writes; the reader's
        read has an acquire edge). `[PROVE]`
1.11.17 The DCL variants: local-variable caching (`Instance local = instance;`) to avoid a second
        volatile read, and the measured cost of that micro-optimisation. `[NUM]`
1.11.18 The holder idiom (initialisation-on-demand holder class), and why the JVM's class
        initialisation lock (JVMS 5.5) makes it thread-safe with **zero** synchronization on the
        fast path. `[PROVE]` `[X-REF 06]`
1.11.19 The enum singleton, and why serialization and reflection cannot break it. `[X-REF 03]`
1.11.20 Eager static initialisation, and when it is simply the right answer.
1.11.21 Class-initialisation deadlock: two classes whose static initialisers reference each other
        from two threads deadlock on the initialisation locks, and this deadlock is invisible to
        `jstack`'s deadlock detector. `[TRAP]` `[RESEARCH]` `[X-REF 06]`
1.11.22 `@Stable` and the `StableValue` API (JEP 502, Java 25 preview) as the modern lazy-constant
        mechanism. `[RESEARCH]` `[VERSION-TRAP]`

*(22 leaves)*

## §1.12 `wait` / `notify` / `notifyAll`

1.12.1 The three methods are on `java.lang.Object` — a design decision inseparable from
       "every object has a monitor".
1.12.2 They must be called while holding that object's monitor, or `IllegalMonitorStateException`.
       `[TRAP]`
1.12.3 `wait()` atomically releases the monitor and suspends; on wake it must **re-acquire** before
       returning, which is why the thread passes through BLOCKED. `[PROVE]`
1.12.4 `wait()` releases only *that* monitor. Any other lock the thread holds is retained — a
       classic deadlock source. `[TRAP]`
1.12.5 The wait set (JLS 17.2): every object has one; `notify` moves one arbitrary thread out,
       `notifyAll` moves all of them. `[SOURCE]`
1.12.6 JLS 17.2.1–17.2.4: wait, notification, interruptions, and the interaction of the three
       (including the case where a thread is both notified and interrupted). `[SOURCE]`
1.12.7 **Always wait in a `while` loop, never an `if`** — for two independent reasons. `[TRAP]`
1.12.8 Reason one: spurious wakeups are explicitly permitted by the spec (they come from the
       underlying `pthread_cond_wait`). `[SOURCE]` `[PROVE]`
1.12.9 Reason two: with `notifyAll`, several threads wake and race; the losers must re-check.
       Even with `notify`, the state can change between the notify and the waiter's re-acquisition.
       `[PROVE]`
1.12.10 The canonical state-dependent-action template: `synchronized { while (!cond) wait(); act(); }`
        paired with `synchronized { changeState(); notifyAll(); }`.
1.12.11 `notify` versus `notifyAll`: prefer `notifyAll` unless *all* waiters wait on the same
        condition and *one* of them can always proceed. Otherwise `notify` can wake the wrong
        thread and the signal is lost forever. `[TRAP]` `[PROVE]`
1.12.12 The missed-signal / lost-wakeup bug: `notify` called before the waiter reached `wait()`.
        The condition variable holds no memory, so the signal is gone. The `while` loop plus a
        state variable is the fix. `[TRAP]` `[PROVE]`
1.12.13 The thundering herd of `notifyAll` in a large wait set, and why `Condition` objects fix it
        by giving each predicate its own wait set.
1.12.14 `wait(long timeout)` / `wait(long, int)` and the fact that a timed `wait` cannot tell you
        whether it timed out — you must check the clock yourself. `[TRAP]`
1.12.15 The interaction with `Thread.interrupt`: `wait` throws `InterruptedException` and clears the
        flag, after re-acquiring the monitor.
1.12.16 Why modern code uses `BlockingQueue`, `CountDownLatch`, `Semaphore` or `Condition` instead
        — but you must know `wait`/`notify` because it is asked and because the JDK's own
        synchronizers are built on the same idea.

*(16 leaves)*

## §1.13 Atomics and compare-and-swap

1.13.1 CAS defined: `compareAndSet(expected, new)` atomically writes `new` only if the current
       value is `expected`; it is one instruction on every modern CPU
       (`lock cmpxchg` x86, `LDXR`/`STXR` LL-SC on AArch64). `[ASM]` `[NUM]`
1.13.2 The CAS retry loop as the universal non-blocking idiom, shown as the body of
       `incrementAndGet`. `[SOURCE]`
1.13.3 Optimistic versus pessimistic concurrency: CAS assumes no conflict and retries; a lock
       assumes conflict and excludes. `[X-REF 09]`
1.13.4 Non-blocking / lock-free / wait-free — the three progress guarantees, defined precisely and
       distinguished. Atomics are lock-free, not wait-free. `[PROVE]` `[RESEARCH]`
1.13.5 The full class inventory of `java.util.concurrent.atomic` (16 classes): `AtomicBoolean`,
       `AtomicInteger`, `AtomicLong`, `AtomicReference<V>`, `AtomicIntegerArray`,
       `AtomicLongArray`, `AtomicReferenceArray<E>`, `AtomicIntegerFieldUpdater<T>`,
       `AtomicLongFieldUpdater<T>`, `AtomicReferenceFieldUpdater<T,V>`, `AtomicMarkableReference<V>`,
       `AtomicStampedReference<V>`, `LongAdder`, `LongAccumulator`, `DoubleAdder`,
       `DoubleAccumulator`. `[RESEARCH]` `[NUM]`
1.13.6 `AtomicInteger`'s method surface: `get`, `set`, `lazySet`, `getAndSet`, `compareAndSet`,
       `weakCompareAndSetPlain`, `getAndIncrement`, `getAndDecrement`, `getAndAdd`,
       `incrementAndGet`, `decrementAndGet`, `addAndGet`, `getAndUpdate`, `updateAndGet`,
       `getAndAccumulate`, `accumulateAndGet`, `compareAndExchange`, `getPlain`/`setPlain`,
       `getOpaque`/`setOpaque`, `getAcquire`/`setRelease`, `intValue`/`longValue`/`floatValue`/
       `doubleValue`. `[RESEARCH]`
1.13.7 `updateAndGet`/`accumulateAndGet` take a function that **may be applied more than once** —
       it must be side-effect-free. `[TRAP]` `[SOURCE]`
1.13.8 `weakCompareAndSet*` may fail spuriously, so it is only usable inside a loop; it exists
       because LL/SC architectures can implement it without a retry. `[PROVE]` `[RESEARCH]`
1.13.9 `lazySet` / `setRelease`: a store with release semantics and no StoreLoad barrier — cheaper
       than a volatile write, used for nulling out references in queues. `[NUM]`
1.13.10 `AtomicReference` versus a `volatile` reference: identical read/write semantics plus CAS.
1.13.11 `AtomicBoolean` as a one-shot guard: `if (started.compareAndSet(false, true))`.
1.13.12 The field updaters: reflection-based, require a `volatile` non-static field, cheaper in
        memory than one atomic object per field. Documented as "of more limited use" now that
        `VarHandle` exists. `[SOURCE]` `[RESEARCH]`
1.13.13 **The ABA problem:** CAS compares values, not history. A → B → A succeeds although the
        world changed. `[TRAP]` `[PROVE]`
1.13.14 Where ABA actually bites: lock-free stacks and any structure that recycles nodes. Where it
        does not: a monotonically increasing counter.
1.13.15 `AtomicStampedReference<V>` (reference + int stamp) and `AtomicMarkableReference<V>`
        (reference + boolean) as the two fixes, and their cost: an extra `Pair` object allocation
        per update. `[NUM]`
1.13.16 `LongAdder`: base field plus a striped `Cell[]`, `increment`/`add`/`sum`/`sumThenReset`/
        `reset`/`intValue`. Trades exactness of an instantaneous read for write throughput.
1.13.17 `LongAdder.sum()` is not atomic with respect to concurrent updates — it is a racy sum of
        the cells. `[TRAP]` `[SOURCE]`
1.13.18 `LongAccumulator`/`DoubleAccumulator`: generalise the adder to any associative,
        side-effect-free `LongBinaryOperator` plus an identity. The operator must be associative
        because the fold order is unspecified. `[PROVE]`
1.13.19 `DoubleAdder`'s floating-point caveat: the sum is not reproducible because the addition
        order varies and FP addition is not associative. `[TRAP]` `[NUM]`
1.13.20 Choosing: `AtomicLong` when you need an exact value from `incrementAndGet`; `LongAdder`
        when it is a write-mostly metric. Show the crossover measurement. `[NUM]`
1.13.21 CAS versus locks under contention: CAS wins at low/moderate contention (no context switch),
        loses under extreme contention (retry loops burn CPU and coherence bandwidth). `[PROVE]`
1.13.22 `VarHandle` (Java 9, JEP 193) as the modern replacement for `sun.misc.Unsafe`: obtained via
        `MethodHandles.lookup().findVarHandle(...)`, `arrayElementVarHandle`,
        `byteArrayViewVarHandle`.
1.13.23 The `VarHandle` access-mode taxonomy in full: **read** (`get`, `getOpaque`, `getAcquire`,
        `getVolatile`), **write** (`set`, `setOpaque`, `setRelease`, `setVolatile`), **atomic
        update** (`compareAndSet`, `compareAndExchange`, `compareAndExchangeAcquire`,
        `compareAndExchangeRelease`, `weakCompareAndSetPlain`, `weakCompareAndSet`,
        `weakCompareAndSetAcquire`, `weakCompareAndSetRelease`, `getAndSet`, `getAndSetAcquire`,
        `getAndSetRelease`), **numeric** (`getAndAdd`, `getAndAddAcquire`, `getAndAddRelease`),
        **bitwise** (`getAndBitwiseOr/And/Xor` × plain/acquire/release). `[RESEARCH]` `[SOURCE]`
1.13.24 The four memory-ordering levels and what each guarantees: **plain** (no ordering, atomicity
        only for ≤32-bit), **opaque** (atomicity + coherence + progress, no ordering with other
        variables), **acquire/release** (one-way barriers), **volatile** (full, sequentially
        consistent). `[PROVE]` `[RESEARCH]`
1.13.25 `VarHandle.fullFence()`, `acquireFence()`, `releaseFence()`, `loadLoadFence()`,
        `storeStoreFence()` — the standalone barriers, and what each forbids. `[SOURCE]`
1.13.26 When plain/opaque/release actually buy something, and the honest answer for application
        code: almost never — this is JDK and library territory. `[TRAP]`
1.13.27 `sun.misc.Unsafe`: what it was used for, why it is being removed (JEP 471 deprecates the
        memory-access methods in 23, JEP 498 warns in 24), and what replaces each use.
        `[RESEARCH]` `[VERSION-TRAP]`
1.13.28 `ThreadLocalRandom.current()` as the concurrent RNG: never share a `Random` across threads
        (its seed is a single `AtomicLong` and becomes a contention point). `[TRAP]` `[NUM]`
1.13.29 `Random` versus `ThreadLocalRandom` versus `SplittableRandom` versus the Java 17
        `RandomGenerator` interface hierarchy. `[X-REF 04]` `[RESEARCH]`

*(29 leaves)*

## §1.14 Explicit locks

1.14.1 The `Lock` interface: `lock`, `lockInterruptibly`, `tryLock`, `tryLock(time, unit)`,
       `unlock`, `newCondition`.
1.14.2 The mandatory idiom: `lock.lock(); try { ... } finally { lock.unlock(); }` — and the
       variant where `lock()` is placed *outside* the try so a failed acquisition does not unlock.
       `[TRAP]` `[PROVE]`
1.14.3 **Trap:** forgetting `unlock` in a `finally`. `synchronized` releases on exception; a `Lock`
       does not, and the result is a permanently wedged application. `[TRAP]`
1.14.4 `ReentrantLock`: same semantics as `synchronized` plus polled, timed and interruptible
       acquisition, fairness, multiple conditions, and instrumentation.
1.14.5 `ReentrantLock` instrumentation methods: `isLocked`, `isHeldByCurrentThread`,
       `getHoldCount`, `getQueueLength`, `hasQueuedThreads`, `hasQueuedThread(Thread)`,
       `getWaitQueueLength(Condition)`, `getOwner` (protected). `[RESEARCH]`
1.14.6 `tryLock()` returning immediately versus `tryLock(0, unit)` — the subtle difference: the
       untimed form **barges** even in fair mode, the timed form respects fairness. `[TRAP]`
       `[SOURCE]` `[RESEARCH]`
1.14.7 Fairness: `new ReentrantLock(true)` gives FIFO grant order, forbids barging, and costs a
       large factor of throughput because every hand-off is a context switch. Default is unfair.
       `[NUM]` `[PROVE]`
1.14.8 Why unfair (barging) locks are faster: a thread that arrives while the lock is momentarily
       free takes it without waking the queue head, avoiding two context switches. `[PROVE]`
1.14.9 Fairness prevents starvation but does not prevent *lock convoys*.
1.14.10 `Condition`: `await`, `await(time, unit)`, `awaitNanos`, `awaitUninterruptibly`,
        `awaitUntil(Date)`, `signal`, `signalAll`. The mapping from `wait`/`notify`/`notifyAll`.
1.14.11 Multiple conditions per lock — `notFull` and `notEmpty` on one bounded buffer — is the
        headline feature: you signal exactly the right waiters. `[BUILD]`
1.14.12 **Trap:** calling `wait`/`notify` on a `Condition` object, or `signal` on a monitor. Mixing
        the two APIs throws or silently does nothing. `[TRAP]`
1.14.13 `Condition.await` must also be in a `while` loop — spurious wakeup applies equally.
        `[TRAP]`
1.14.14 `awaitNanos` returns the *remaining* time, which is how you write a correct deadline loop.
        `[SOURCE]`
1.14.15 `ReentrantReadWriteLock`: `readLock()` / `writeLock()`, many readers or one writer,
        fair and non-fair modes.
1.14.16 Lock downgrading (write → read, legal) versus upgrading (read → write, **deadlocks**, not
        supported). `[TRAP]` `[PROVE]`
1.14.17 Reader starvation in non-fair mode versus writer starvation; the `ReentrantReadWriteLock`
        write-preference heuristic. `[RESEARCH]`
1.14.18 When RW-lock actually wins: reads dominate heavily *and* the critical section is long
        enough to amortise the extra bookkeeping. Otherwise it loses to a plain `ReentrantLock`.
        `[NUM]` `[TRAP]`
1.14.19 `StampedLock` (Java 8): three modes — write, read, **optimistic read** — with `long`
        stamps instead of ownership.
1.14.20 The optimistic-read protocol: `tryOptimisticRead()` → read fields into locals →
        `validate(stamp)` → fall back to `readLock()` if invalid. Show the javadoc's canonical
        `distanceFromOrigin` loop. `[SOURCE]` `[BUILD]`
1.14.21 `StampedLock` full method surface: `writeLock`, `tryWriteLock`×2, `writeLockInterruptibly`,
        `readLock`, `tryReadLock`×2, `readLockInterruptibly`, `tryOptimisticRead`, `validate`,
        `unlockWrite`, `unlockRead`, `unlock`, `tryConvertToWriteLock`, `tryConvertToReadLock`,
        `tryConvertToOptimisticRead`, `tryUnlockWrite`, `tryUnlockRead`, `isWriteLocked`,
        `isReadLocked`, `getReadLockCount`, the four static `is*Stamp` predicates, `asReadLock`,
        `asWriteLock`, `asReadWriteLock`. `[RESEARCH]` `[SOURCE]`
1.14.22 **Trap:** `StampedLock` is **not reentrant**. A reentrant call self-deadlocks. `[TRAP]`
1.14.23 **Trap:** `StampedLock` has no ownership — any thread may unlock any stamp — and it
        deserializes into the unlocked state. `[TRAP]` `[SOURCE]`
1.14.24 **Trap:** optimistic reads can observe *wildly inconsistent* field combinations before
        `validate` fails, so the body must not dereference, index, or divide by what it read.
        `[TRAP]` `[SOURCE]`
1.14.25 The one-year stamp-recycling caveat from the javadoc. `[NUM]` `[SOURCE]` `[RESEARCH]`
1.14.26 `asReadLock()`/`asWriteLock()` do not support `newCondition()` —
        `UnsupportedOperationException`. `[TRAP]` `[SOURCE]`
1.14.27 `LockSupport.park`/`parkNanos`/`parkUntil`/`unpark(Thread)` and the per-thread **permit**:
        `unpark` before `park` is remembered (one permit, not counted), which is what makes the
        API race-free. `[PROVE]` `[SOURCE]`
1.14.28 `LockSupport.park(Object blocker)` and `getBlocker` — how the thread dump learns
        "parking to wait for <0x…> java.util.concurrent.locks.AbstractQueuedSynchronizer$ConditionObject".
        `[DUMP]`
1.14.29 `synchronized` versus `ReentrantLock` decision table, including the Java 21 virtual-thread
        pinning row and its reversal in Java 24. `[VERSION-TRAP]`

*(29 leaves)*

## §1.15 Synchronizers

1.15.1 `CountDownLatch(n)`: `await`, `await(t,u)`, `countDown`, `getCount`. **One-shot** — it
       cannot be reset. `[TRAP]`
1.15.2 The two latch shapes: start gate (`new CountDownLatch(1)`, all workers await, main
       counts down) and completion gate (`new CountDownLatch(n)`, main awaits, workers count down).
1.15.3 `countDown()` in a `finally` — otherwise one thrown exception hangs the awaiting thread
       forever. `[TRAP]`
1.15.4 `CyclicBarrier(n)` / `CyclicBarrier(n, Runnable barrierAction)`: `await`, `await(t,u)`,
       `getParties`, `getNumberWaiting`, `isBroken`, `reset`. **Reusable**.
1.15.5 `await()` returns the arrival index (`parties − 1` for the first arriver, 0 for the last),
       which is how you pick a leader for the phase. `[SOURCE]`
1.15.6 The barrier is **broken** if any participant is interrupted, times out, or the barrier
       action throws — then every other participant gets `BrokenBarrierException`, and only
       `reset()` recovers. `[TRAP]`
1.15.7 The barrier action runs on the last-arriving thread, before any thread is released, and its
       actions happen-before the others' return. `[SOURCE]`
1.15.8 Latch versus barrier as a table: one-shot vs reusable, external vs participant countdown,
       no action vs barrier action.
1.15.9 `Semaphore(n)` / `Semaphore(n, fair)`: `acquire`, `acquireUninterruptibly`, `tryAcquire`×4,
       `release`, `acquire(int)`, `drainPermits`, `availablePermits`, `reducePermits` (protected),
       `hasQueuedThreads`, `getQueueLength`.
1.15.10 Permits are **not owned by a thread** — any thread may release, and you may release more
        than you acquired, which quietly inflates the limit. `[TRAP]`
1.15.11 A binary semaphore (`Semaphore(1)`) is not a mutex: it is not reentrant and has no owner.
        `[TRAP]`
1.15.12 Semaphore as a bounding tool: bounded collections, connection limits, "at most 10
        concurrent calls to this downstream service" — and the primary backpressure tool once
        virtual threads have removed your pool. `[X-REF 04]`
1.15.13 `Phaser` (Java 7): dynamic party registration (`register`, `bulkRegister`, `arriveAndAwaitAdvance`,
        `arriveAndDeregister`, `arrive`, `awaitAdvance`, `getPhase`, `onAdvance`, `forceTermination`,
        `isTerminated`), hierarchical tiering for scalability, and termination.
1.15.14 `Phaser` versus `CyclicBarrier` versus `CountDownLatch` — the three-way table; `Phaser`
        subsumes both but is rarely worth the complexity.
1.15.15 `Exchanger<V>`: two threads rendezvous and swap objects; `exchange(V)`, `exchange(V,t,u)`.
        The genetic-algorithm / double-buffer use case.
1.15.16 The happens-before edges each synchronizer provides (from the `j.u.c` package doc):
        `countDown` → `await` return; pre-`await` actions → barrier action → post-`await`;
        `release` → `acquire`; each `exchange` → the partner's continuation. `[SOURCE]`
1.15.17 Choosing a synchronizer: a decision table keyed on "one-shot or repeated", "fixed or
        dynamic parties", "counting or gating", "do the parties exchange data".
1.15.18 All five are built on AQS (§3.5) except `Exchanger` and `Phaser`, which use their own
        lock-free algorithms. `[RESEARCH]`

*(18 leaves)*

## §1.16 The concurrent collections

1.16.1 Why `Collections.synchronizedMap/List/Set` is not enough: every method is atomic, but
       *compound* actions are not, and iteration requires manual client-side locking on the wrapper
       or you get `ConcurrentModificationException`. `[TRAP]` `[X-REF 02]`
1.16.2 The legacy synchronized classes and why they are dead: `Vector`, `Stack` (extends Vector),
       `Hashtable`, `StringBuffer`. Every method synchronized on `this`, so no compound safety and
       full serialisation. Know them because they appear in old code and in interviews.
       `[X-REF 02]`
1.16.3 The complete `java.util.concurrent` collection inventory: `ConcurrentHashMap`,
       `ConcurrentHashMap.KeySetView`, `ConcurrentSkipListMap`, `ConcurrentSkipListSet`,
       `CopyOnWriteArrayList`, `CopyOnWriteArraySet`, `ConcurrentLinkedQueue`,
       `ConcurrentLinkedDeque`, `ArrayBlockingQueue`, `LinkedBlockingQueue`,
       `LinkedBlockingDeque`, `PriorityBlockingQueue`, `DelayQueue`, `SynchronousQueue`,
       `LinkedTransferQueue`. `[RESEARCH]` `[NUM]`
1.16.4 The three iterator-consistency models, which is the distinction that matters:
       **fail-fast** (`java.util` — `ConcurrentModificationException` on modCount change),
       **weakly consistent** (`ConcurrentHashMap`, the queues — never throws, may or may not
       reflect concurrent changes, each element traversed at most once),
       **snapshot** (`CopyOnWriteArrayList` — iterates the array as of iterator creation).
       `[SOURCE]` `[PROVE]`
1.16.5 Weakly consistent, spelled out from the package doc: may proceed concurrently with other
       operations, will never throw CME, are guaranteed to traverse elements as they existed on
       construction, and may (but are not guaranteed to) reflect modifications after construction.
       `[SOURCE]`
1.16.6 `ConcurrentModificationException` is best-effort and unsynchronized — you must not write
       code that depends on catching it. `[TRAP]` `[X-REF 02]`
1.16.7 `ConcurrentHashMap` basics: no null keys, no null values, `get` lock-free, per-bin locking
       on write, `size()` approximate under concurrency, `mappingCount()` as the `long`-returning
       replacement.
1.16.8 Why nulls are forbidden: in a concurrent map you could not distinguish "absent" from "mapped
       to null" with a `get`, and `containsKey`-then-`get` is not atomic. `[PROVE]` `[TRAP]`
1.16.9 The atomic compound API: `putIfAbsent`, `remove(k,v)`, `replace(k,v)`, `replace(k,old,new)`,
       `computeIfAbsent`, `computeIfPresent`, `compute`, `merge`, `getOrDefault`, `forEach`,
       `search`, `reduce` and their key/value/entry variants.
1.16.10 **Trap:** `if (!map.containsKey(k)) map.put(k, v)` is a race even on a concurrent map. Use
        `putIfAbsent` or `computeIfAbsent`. `[TRAP]`
1.16.11 **Trap:** the `computeIfAbsent` mapping function runs **while holding the bin lock**. It
        must be short, must not block, and must not modify the same map. A recursive
        `computeIfAbsent` on the same key throws `IllegalStateException: Recursive update`; on a
        different key that hashes to the same bin it deadlocks. On a plain `HashMap` the same
        pattern silently corrupts the table (fixed to throw CME in Java 9). `[TRAP]` `[RESEARCH]`
        `[X-REF 02]`
1.16.12 `merge(key, 1L, Long::sum)` as the idiomatic atomic counter, and why
        `map.computeIfAbsent(k, x -> new AtomicLong()).incrementAndGet()` is the alternative with
        different allocation behaviour. `[NUM]`
1.16.13 `ConcurrentHashMap.newKeySet()` and `keySet(defaultValue)` as the concurrent `Set`.
1.16.14 The bulk parallel operations (`forEach`, `search`, `reduce` with a `parallelismThreshold`),
        which run on the common ForkJoinPool. Rarely used, occasionally asked. `[RESEARCH]`
1.16.15 `ConcurrentSkipListMap` / `ConcurrentSkipListSet`: the concurrent *sorted* map, a lock-free
        skip list, O(log n) expected, `NavigableMap` surface, no null keys. The concurrent answer
        to `TreeMap`. `[X-REF 02]`
1.16.16 `size()` on `ConcurrentSkipListMap` is **O(n)** because it traverses — the opposite of
        `TreeMap`. `[TRAP]` `[NUM]` `[SOURCE]`
1.16.17 `CopyOnWriteArrayList` / `CopyOnWriteArraySet`: every mutation copies the whole backing
        array under a lock; reads are completely lock-free and see an immutable snapshot.
1.16.18 CoW cost model: read O(1) lock-free, write O(n) **allocation plus copy**. Only correct for
        read-dominated, small, rarely-mutated collections — the listener list is the canonical fit.
        `[NUM]`
1.16.19 **Trap:** the CoW iterator does not support `remove`/`set`/`add` (throws
        `UnsupportedOperationException`) and never reflects changes made after it was created.
        `[TRAP]`
1.16.20 **Trap:** a loop of `list.add(x)` on a `CopyOnWriteArrayList` is O(n²) copies and will melt
        a service. `[TRAP]` `[NUM]`
1.16.21 `ConcurrentLinkedQueue` / `ConcurrentLinkedDeque`: unbounded, non-blocking, lock-free
        (Michael–Scott algorithm), `size()` is O(n) and approximate, `offer` never blocks or fails.
        `[NUM]`
1.16.22 There is no `ConcurrentArrayList` and no concurrent `List` other than CoW; the reason is
        that index-addressability and concurrency do not compose. `[TRAP]` `[PROVE]`
1.16.23 Choosing a concurrent collection: a decision table keyed on ordering, boundedness,
        read/write ratio, blocking, and iteration semantics.
1.16.24 Views versus copies versus snapshots, and the bug each mistake causes: a `keySet()` view
        mutation writes through to the map; a `CopyOnWriteArrayList` iterator snapshot silently
        misses updates; `List.copyOf` is a genuine copy. `[TRAP]` `[X-REF 02]`

*(24 leaves)*

## §1.17 `BlockingQueue` and the producer–consumer pattern

1.17.1 `BlockingQueue<E>` extends `Queue<E>`: blocks the producer when full and the consumer when
       empty. All implementations are thread-safe; `null` is forbidden (it is the sentinel for
       `poll`).
1.17.2 The four method families as a table: **throws** (`add`, `remove`, `element`), **special
       value** (`offer`, `poll`, `peek`), **blocks** (`put`, `take`), **times out**
       (`offer(e,t,u)`, `poll(t,u)`). Memorise the grid. `[SOURCE]`
1.17.3 `drainTo(Collection)` / `drainTo(Collection, int)` for batch consumption, and why batching
       beats one-`take`-per-element under load. `[NUM]`
1.17.4 `remainingCapacity()`, and its meaning for unbounded queues (`Integer.MAX_VALUE`).
1.17.5 `ArrayBlockingQueue(capacity[, fair])`: bounded, array-backed circular buffer, **one**
       `ReentrantLock` with `notEmpty`/`notFull` conditions, so put and take contend. No
       allocation per element.
1.17.6 `LinkedBlockingQueue([capacity])`: optionally bounded (default `Integer.MAX_VALUE` —
       effectively unbounded), linked nodes, **two** locks (`putLock`/`takeLock`) so producers and
       consumers do not contend, plus an `AtomicInteger count`. Higher throughput, one node
       allocation per element. `[NUM]`
1.17.7 The two-lock split explained: it works because the head and tail of a linked queue are
       independent, which is impossible for an array-backed ring. `[PROVE]`
1.17.8 `LinkedBlockingDeque`: bounded deque, single lock, supports work-stealing patterns.
1.17.9 `SynchronousQueue([fair])`: **capacity zero**. Every `put` waits for a `take`. `size()`
       always returns 0, `peek` always null, `isEmpty` always true, and it is not `Iterable` in any
       useful sense. It is a hand-off, not storage. `[TRAP]` `[SOURCE]`
1.17.10 `PriorityBlockingQueue`: unbounded, heap-ordered, `Comparable` or `Comparator`, `put` never
        blocks (so it gives no backpressure at all), and the iterator is **not** ordered.
        `[TRAP]` `[X-REF 02]`
1.17.11 `DelayQueue<E extends Delayed>`: unbounded; an element only becomes takeable once
        `getDelay(NANOSECONDS) <= 0`. The scheduler primitive; `Delayed` must implement
        `compareTo` consistently with the delay. `[TRAP]`
1.17.12 `LinkedTransferQueue` (Java 7): unbounded; adds `transfer(e)` (block until a consumer
        receives it), `tryTransfer` ×2, `hasWaitingConsumer`, `getWaitingConsumerCount`. The
        superset of `SynchronousQueue` and `ConcurrentLinkedQueue`. `[RESEARCH]`
1.17.13 `BlockingDeque` and the `xxxFirst`/`xxxLast` twelve-method grid.
1.17.14 The bounded-queue argument stated as a principle: **every queue in a system must have a
        bound and a defined behaviour at the bound.** An unbounded queue converts an overload
        problem into a memory problem and defers failure to the worst possible moment. `[TRAP]`
1.17.15 Backpressure defined: the consumer's rate propagating upstream to throttle the producer.
        A bounded queue is the simplest implementation of it.
1.17.16 The producer–consumer assembly, complete: bounded queue, N consumers, poison pills for
        shutdown, per-task try/catch so one bad task cannot kill a worker, and interrupt handling.
        `[BUILD]`
1.17.17 Poison-pill shutdown requires knowing the consumer count, or a `volatile boolean` plus
        `poll(timeout)`. Both patterns shown. `[BUILD]`
1.17.18 Queue choice table: bounded/unbounded, lock count, allocation per element, fairness option,
        ordering, and blocking behaviour.

*(18 leaves)*

## §1.18 The Executor framework

1.18.1 Why: `new Thread(task).start()` per task has unbounded resource use, no lifecycle, no result
       handling, and no queueing policy. The executor decouples **task submission** from
       **execution policy**.
1.18.2 The interface stack: `Executor` (one method, `execute(Runnable)`) → `ExecutorService`
       (lifecycle + `submit`/`invokeAll`/`invokeAny`) → `ScheduledExecutorService`.
1.18.3 `ExecutorService` surface: `submit(Runnable)`, `submit(Runnable, T)`, `submit(Callable<T>)`,
       `invokeAll`, `invokeAll(timeout)`, `invokeAny`, `invokeAny(timeout)`, `shutdown`,
       `shutdownNow`, `isShutdown`, `isTerminated`, `awaitTermination`, `close` (Java 19+).
1.18.4 `ExecutorService extends AutoCloseable` since Java 19: `close()` = `shutdown()` +
       `awaitTermination` forever + `shutdownNow` on interrupt. This is what makes
       `try (var ex = Executors.newVirtualThreadPerTaskExecutor())` work. `[RESEARCH]`
       `[VERSION-TRAP]`
1.18.5 The five execution-policy dimensions: in what thread, in what order, how many concurrently,
       how many queued, and what to do when rejected.
1.18.6 The `Executors` factory inventory: `newFixedThreadPool`, `newSingleThreadExecutor`,
       `newCachedThreadPool`, `newScheduledThreadPool`, `newSingleThreadScheduledExecutor`,
       `newWorkStealingPool`, `newVirtualThreadPerTaskExecutor` (21),
       `newThreadPerTaskExecutor(ThreadFactory)` (21), plus the `unconfigurableXxx` and
       `callable`/`privilegedCallable` adapters. `[RESEARCH]`
1.18.7 `newSingleThreadExecutor` is not `newFixedThreadPool(1)`: the single-thread version is
       wrapped so it cannot be reconfigured, and it replaces a dead thread. `[TRAP]` `[SOURCE]`
1.18.8 `submit` versus `execute`: `submit` wraps the task in a `FutureTask` and **captures any
       exception into the Future**. If you never call `get()`, the exception disappears entirely —
       your `afterExecute` hook and your `UncaughtExceptionHandler` never fire. `[TRAP]` `[PROVE]`
1.18.9 `invokeAll` blocks until all tasks complete or the timeout expires, returning Futures in
       argument order (some possibly cancelled); `invokeAny` returns the first successful result and
       cancels the rest.
1.18.10 `CompletionService` / `ExecutorCompletionService`: `submit`, `take`, `poll` — results in
        *completion* order instead of submission order. The right tool when you want to process
        results as they arrive. `[BUILD]`
1.18.11 `Future<V>`: `get`, `get(t,u)`, `cancel(boolean)`, `isCancelled`, `isDone`, and Java 19's
        `state()` / `resultNow()` / `exceptionNow()` with the `Future.State` enum
        (`RUNNING`, `SUCCESS`, `FAILED`, `CANCELLED`). `[RESEARCH]` `[VERSION-TRAP]`
1.18.12 `Future.get` throws `InterruptedException`, `ExecutionException` (wrapping the task's
        throwable — unwrap with `getCause()`), `CancellationException`, and `TimeoutException`.
1.18.13 `FutureTask` as the `RunnableFuture` implementation: a one-shot state machine, and the
        basis of every `submit`.
1.18.14 Why a chain of `Future.get()` calls is just sequential code with extra threads — the
        motivation for `CompletableFuture`. `[PROVE]`
1.18.15 Shutdown: `shutdown()` refuses new tasks and drains the queue; `shutdownNow()` interrupts
        running tasks, drains the queue and **returns the unstarted tasks**; then
        `awaitTermination(timeout)`; then `shutdownNow()` again. The standard two-phase shutdown
        idiom. `[BUILD]`
1.18.16 **Trap:** a non-daemon pool thread that is never shut down keeps the JVM alive forever.
        `[TRAP]`
1.18.17 **Trap:** `shutdownNow` relies on interruption, so a task that ignores interrupts is not
        stopped by it. `[TRAP]`
1.18.18 `RejectedExecutionException` is also thrown after shutdown, not only when saturated.
1.18.19 Executor as a `try-with-resources` in Java 21, and the structured-lifetime idea it hints
        at. `[X-REF 04]`

*(19 leaves)*

## §1.19 `ThreadPoolExecutor`

1.19.1 The seven constructor parameters: `corePoolSize`, `maximumPoolSize`, `keepAliveTime`,
       `unit`, `workQueue`, `threadFactory`, `handler`. Defaults:
       `Executors.defaultThreadFactory()` and `AbortPolicy`.
1.19.2 **The submission algorithm, in exact order** — the single most-asked mechanism in this
       topic: (1) if `poolSize < corePoolSize`, create a new thread **even if idle threads exist**;
       (2) else try to enqueue; (3) only if the queue rejects the offer, create a thread up to
       `maximumPoolSize`; (4) else invoke the rejection handler. `[SOURCE]` `[PROVE]`
1.19.3 Why step 1 creates a thread even when idle threads exist: the pool is warming to its core
       size, and the check is on the count, not on idleness. `[PROVE]`
1.19.4 **Trap — the unbounded-queue trap.** `Executors.newFixedThreadPool(n)` uses a
       `LinkedBlockingQueue` with capacity `Integer.MAX_VALUE`. The queue never fills, so step 3
       never runs and `maximumPoolSize` is dead code. Under overload, tasks accumulate until the
       heap is gone — `OutOfMemoryError` instead of graceful shedding. The single most common
       production thread-pool bug. `[TRAP]` `[NUM]` `[PROVE]`
1.19.5 **Trap — the mirror-image `newCachedThreadPool` bug:** `SynchronousQueue` (capacity 0) plus
       `maximumPoolSize = Integer.MAX_VALUE` and a 60-second keep-alive means every task that
       cannot hand off immediately creates a **new OS thread**, without limit. `[TRAP]` `[NUM]`
1.19.6 The three documented queuing strategies from the javadoc: **direct handoff**
       (`SynchronousQueue`), **unbounded queue** (`LinkedBlockingQueue`), **bounded queue**
       (`ArrayBlockingQueue`) — with the javadoc's own trade-off text on queue size versus pool
       size. `[SOURCE]` `[RESEARCH]`
1.19.7 The four built-in rejection policies as a table: `AbortPolicy` (default, throws
       `RejectedExecutionException`), `CallerRunsPolicy`, `DiscardPolicy`, `DiscardOldestPolicy`
       (drops the queue head and retries — and does the wrong thing entirely with a priority
       queue). `[TRAP]`
1.19.8 `CallerRunsPolicy` as a **backpressure** mechanism: the submitting thread executes the task
       itself, which stops it submitting, which throttles the source. A throttle, not a failure.
       `[PROVE]`
1.19.9 **Trap:** `CallerRunsPolicy` on the request-handling thread means a request thread is now
       doing background work; and after `shutdown()` it silently *discards* the task instead of
       running it. `[TRAP]` `[SOURCE]` `[RESEARCH]`
1.19.10 Writing a custom `RejectedExecutionHandler`: block-and-retry via
        `queue.offer(task, timeout, unit)`, or shed with a metric. `[BUILD]`
1.19.11 The dynamic knobs: `setCorePoolSize`, `setMaximumPoolSize`, `setKeepAliveTime`,
        `setThreadFactory`, `setRejectedExecutionHandler`, `allowCoreThreadTimeOut(true)`.
        `[SOURCE]`
1.19.12 `allowCoreThreadTimeOut(true)` lets a pool shrink to zero threads — required if you want an
        idle pool to be collectable. `[RESEARCH]`
1.19.13 `prestartCoreThread()` / `prestartAllCoreThreads()` to avoid the cold-start latency of the
        first N requests. `[NUM]`
1.19.14 The monitoring surface: `getPoolSize`, `getActiveCount`, `getLargestPoolSize`,
        `getTaskCount`, `getCompletedTaskCount`, `getQueue`, `remove(Runnable)`, `purge()`. All
        counts are approximations taken without a global lock. `[SOURCE]` `[TRAP]`
1.19.15 The three protected hooks: `beforeExecute(Thread, Runnable)`, `afterExecute(Runnable,
        Throwable)`, `terminated()`. Used for MDC propagation, timing, and the exception-logging
        fix for `submit`. `[BUILD]` `[SOURCE]`
1.19.16 The javadoc's `PausableThreadPoolExecutor` example as the canonical `beforeExecute` use.
        `[SOURCE]` `[RESEARCH]`
1.19.17 Pool sizing: CPU-bound ≈ `Runtime.availableProcessors()` (+1 for page faults); I/O-bound ≈
        `cores × targetUtilisation × (1 + waitTime/serviceTime)`. Derive the formula from Little's
        law. `[PROVE]` `[NUM]`
1.19.18 `Runtime.getRuntime().availableProcessors()` and container CPU limits — the cgroup-aware
        behaviour since JDK 10, and the `-XX:ActiveProcessorCount` override. `[X-REF 06]`
        `[X-REF 19]`
1.19.19 The bulkhead argument: separate pools per workload, so a slow downstream cannot starve
        unrelated work. `[X-REF 20]`
1.19.20 Thread-pool starvation by **task dependency**: a task that submits to and then blocks on the
        same pool. With N threads and N such tasks, the pool deadlocks permanently. This is the
        classic single-thread-executor self-submission deadlock. `[TRAP]` `[PROVE]`
1.19.21 Deadlock by starvation with a bounded queue: producer and consumer in the same pool.
        `[TRAP]`
1.19.22 The `finalize()`-based auto-shutdown was removed in Java 9; a leaked pool now leaks
        threads. `[VERSION-TRAP]` `[SOURCE]` `[RESEARCH]`

*(22 leaves)*

## §1.20 `ScheduledThreadPoolExecutor`

1.20.1 `schedule(Runnable, delay, unit)`, `schedule(Callable, ...)`, `scheduleAtFixedRate`,
       `scheduleWithFixedDelay`.
1.20.2 `scheduleAtFixedRate` fires on an absolute schedule (t0+p, t0+2p, …) and **bunches up** if a
       run overruns; `scheduleWithFixedDelay` waits a fixed gap after each completion. Draw both
       timelines. `[PROVE]`
1.20.3 **Trap:** an uncaught exception in a scheduled task **silently cancels all future
       executions** of that task. Wrap every scheduled body in try/catch. `[TRAP]` `[SOURCE]`
1.20.4 Why it silently cancels: `FutureTask.setException` completes the future exceptionally and
       the periodic re-arm never happens, and nobody calls `get()`. `[PROVE]`
1.20.5 The pool is effectively fixed-size — `maximumPoolSize` is ignored because the queue is an
       unbounded `DelayedWorkQueue`. One slow task delays every other task in the same scheduler.
       `[TRAP]`
1.20.6 The extra knobs: `setRemoveOnCancelPolicy`, `setContinueExistingPeriodicTasksAfterShutdownPolicy`,
       `setExecuteExistingDelayedTasksAfterShutdownPolicy`, `getQueue`. `[RESEARCH]`
1.20.7 **Trap:** without `setRemoveOnCancelPolicy(true)`, cancelled tasks stay in the queue until
       their scheduled time — an unbounded leak in a system that schedules and cancels timeouts.
       `[TRAP]` `[RESEARCH]`
1.20.8 `Timer`/`TimerTask` and why they are obsolete: one thread for all tasks, an uncaught
       exception kills the timer thread entirely, and it uses absolute system time so an NTP jump
       breaks it. `[TRAP]` `[RESEARCH]`
1.20.9 Scheduling versus a distributed scheduler: a `ScheduledExecutorService` is per-JVM, so N
       replicas run the job N times. `[X-REF 18]`
1.20.10 `CompletableFuture.delayedExecutor(t, u[, executor])` and the single daemon thread the
        class maintains for timeouts (`Delayer`), which triggers but never runs the actions.
        `[SOURCE]` `[RESEARCH]`

*(10 leaves)*

## §1.21 `CompletableFuture`

1.21.1 What `Future` cannot do: no composition, no callbacks, no manual completion, no combination,
       no exception recovery. `CompletableFuture` implements `Future<T>` **and** `CompletionStage<T>`.
1.21.2 The construction surface: `new CompletableFuture<>()`, `supplyAsync`×2, `runAsync`×2,
       `completedFuture`, `completedStage`, `failedFuture` (9), `failedStage` (9).
1.21.3 The three shapes of every dependent operation — `xxx`, `xxxAsync`, `xxxAsync(executor)` —
       and what each means for *which thread runs the callback*.
1.21.4 The non-async form may run on the thread that completed the previous stage, **or on the
       calling thread if the stage is already complete**. So a slow lambda there occupies someone
       else's thread, and the "which thread" answer is genuinely nondeterministic. `[SOURCE]`
       `[TRAP]` `[PROVE]`
1.21.5 The transformation family: `thenApply` (map), `thenAccept` (consume), `thenRun` (ignore
       value), `thenCompose` (flatMap), each ×3.
1.21.6 `thenApply` versus `thenCompose`: returning `CompletableFuture<CompletableFuture<T>>` versus
       flattening. The `map`/`flatMap` distinction. `[TRAP]`
1.21.7 The combination family: `thenCombine`, `thenAcceptBoth`, `runAfterBoth`, `applyToEither`,
       `acceptEither`, `runAfterEither` — each ×3 = 18 methods.
1.21.8 `allOf(CompletableFuture<?>...)` returns `CompletableFuture<Void>` — you must re-read the
       individual futures for their values, typically with `join` inside a `thenApply`. `[TRAP]`
       `[BUILD]`
1.21.9 `anyOf(...)` returns `CompletableFuture<Object>` and completes with the **first to complete,
       including the first to fail**. It is not "first success". `[TRAP]`
1.21.10 The exception family: `exceptionally`, `exceptionallyAsync` (12), `exceptionallyCompose`
        (12), `exceptionallyComposeAsync` (12), `handle`×3, `whenComplete`×3. `[RESEARCH]`
1.21.11 `handle` versus `whenComplete` versus `exceptionally`: `handle` transforms both outcomes and
        can change the type; `whenComplete` observes without changing the result (and rethrows the
        original if the action throws); `exceptionally` only fires on failure. Table. `[TRAP]`
1.21.12 Exceptions propagate down the chain wrapped in `CompletionException`; `get()` wraps in
        `ExecutionException`, `join()` wraps in `CompletionException`. Unwrap with `getCause()`.
        `[TRAP]` `[NUM]`
1.21.13 `join()` versus `get()`: `join` throws unchecked, `get` throws checked. In a lambda you
        almost always want `join`.
1.21.14 **Trap — swallowed exceptions.** A chain with no terminal `get`/`join`/`handle`/
        `exceptionally`/`whenComplete` stores the exception in the future and it **disappears
        silently**. The common form is a fire-and-forget `runAsync`. Always terminate with
        `whenComplete` and log. `[TRAP]`
1.21.15 **Trap:** the no-executor overloads use `ForkJoinPool.commonPool()`, which is shared
        JVM-wide with parallel streams. Blocking there starves everything. **Always pass your own
        executor.** `[TRAP]` `[SOURCE]` `[X-REF 04]`
1.21.16 The documented fallback: if the common pool does not support parallelism ≥ 2 (a
        single-core container), every async task gets **a brand-new thread**. `[SOURCE]` `[TRAP]`
        `[NUM]` `[RESEARCH]`
1.21.17 Manual completion: `complete`, `completeExceptionally`, `completeAsync`×2 (9),
        `obtrudeValue`, `obtrudeException` (the last two break the write-once contract and exist
        for error recovery only). `[RESEARCH]`
1.21.18 Timeouts: `orTimeout(t,u)` (9) fails the future with `TimeoutException`;
        `completeOnTimeout(v,t,u)` (9) supplies a fallback. Neither cancels the underlying work.
        `[TRAP]` `[RESEARCH]`
1.21.19 `cancel(boolean)` on a `CompletableFuture` **ignores its argument** and never interrupts the
        running task — it only completes the future with `CancellationException`. `[TRAP]`
        `[SOURCE]` `[PROVE]`
1.21.20 Java 9 additions: `copy()`, `minimalCompletionStage()`, `defaultExecutor()`,
        `newIncompleteFuture()`, `delayedExecutor`×2. `[RESEARCH]`
1.21.21 `minimalCompletionStage()` and `copy()` as the way to hand a future to a caller who must not
        complete it. `[RESEARCH]`
1.21.22 Query/inspection: `isDone`, `isCancelled`, `isCompletedExceptionally`, `getNow(fallback)`,
        `getNumberOfDependents`, and the inherited Java-19 `state`/`resultNow`/`exceptionNow`.
1.21.23 `CompletableFuture.AsynchronousCompletionTask` as the marker interface for
        monitoring/debugging. `[SOURCE]` `[RESEARCH]`
1.21.24 Subclassing: override `defaultExecutor()` and `newIncompleteFuture()` to make an entire
        chain use your executor by default. `[BUILD]` `[RESEARCH]`
1.21.25 The worked composition: fetch user → fetch account → combine with limits → timeout →
        recover → render, with an explicit executor at every stage. `[BUILD]`
1.21.26 `CompletionStage` as the interface you should accept in APIs, and `CompletableFuture` as the
        type you should return only when the caller must complete it.
1.21.27 Where `CompletableFuture` stops being the right tool: once you have virtual threads,
        straight-line blocking code plus structured concurrency is simpler and debuggable. State
        the honest 2026 answer. `[X-REF 04]`

*(27 leaves)*

## §1.22 Fork/join

1.22.1 The divide-and-conquer model: `compute()` splits until a sequential threshold, `fork()`s one
       half, computes the other, then `join()`s.
1.22.2 `ForkJoinTask<V>`, `RecursiveAction` (no result), `RecursiveTask<V>` (result),
       `CountedCompleter<T>` (completion-based, no join).
1.22.3 The canonical `compute()` skeleton and the invariant "fork one, compute the other, then
       join" — never `fork(); fork(); join(); join();` if you can avoid it. `[PROVE]` `[BUILD]`
1.22.4 Work stealing: each worker has its own **deque**; it pushes and pops at the *tail* (LIFO, so
       the freshest task is hottest in cache) and steals from another worker's *head* (FIFO, so it
       takes the biggest remaining chunk). `[PROVE]` `[RESEARCH]`
1.22.5 Why LIFO-local / FIFO-steal is the right pair: locality for the owner, minimum contention
       and maximum stolen-work-size for the thief. `[PROVE]`
1.22.6 `ForkJoinPool.commonPool()`: parallelism defaults to `availableProcessors() − 1`, so a
       4-core box has **3** common-pool workers plus the caller. Tunable with
       `java.util.concurrent.ForkJoinPool.common.parallelism`. `[NUM]` `[TRAP]` `[X-REF 04]`
1.22.7 The common pool's threads are daemons, are never shut down, and are shared by parallel
       streams, `CompletableFuture` async methods, and `ConcurrentHashMap` bulk ops. `[TRAP]`
1.22.8 `ForkJoinPool` constructors: parallelism, factory, handler, asyncMode, and the Java 9
       full constructor with `corePoolSize`, `maximumPoolSize`, `minimumRunnable`,
       `saturate`, `keepAliveTime`. `[RESEARCH]`
1.22.9 `asyncMode = true` makes worker queues FIFO — which is what `Executors.newWorkStealingPool()`
       gives you, appropriate for event-style tasks that are never joined. `[RESEARCH]`
1.22.10 `ForkJoinPool.ManagedBlocker` as the supported way to block inside a FJ worker while letting
        the pool compensate by starting another thread. `[SOURCE]` `[BUILD]`
1.22.11 `ForkJoinPool.managedBlock`, and the fact that `CompletableFuture.join` inside the common
        pool already uses a compensation mechanism internally. `[RESEARCH]`
1.22.12 **Trap:** blocking I/O in a fork/join task starves the pool, because parallelism is sized
        for CPU work and there is no compensation without `ManagedBlocker`. `[TRAP]`
1.22.13 Choosing the sequential threshold: too small and overhead dominates, too large and you lose
        parallelism. The rule of thumb of 100–10 000 basic operations per leaf. `[NUM]`
1.22.14 `ForkJoinTask` exception handling: exceptions are captured and rethrown by `join`, wrapped
        for `get`; `getException`, `completeExceptionally`, `isCompletedAbnormally`.
1.22.15 `invokeAll(t1, t2)`, `ForkJoinTask.invoke`, `ForkJoinTask.helpQuiesce`, `pool.awaitQuiescence`.
1.22.16 Fork/join versus a plain executor: FJ is for recursive, CPU-bound, non-blocking work with a
        join dependency. For independent tasks it is the wrong tool.

*(16 leaves)*

## §1.23 `ThreadLocal`

1.23.1 What it is: one value per thread, stored **in the Thread object**, not in the `ThreadLocal`
       object. `ThreadLocal` is a key, not a container. `[PROVE]`
1.23.2 API: `get`, `set`, `remove`, `initialValue` (protected), `withInitial(Supplier)` (Java 8).
1.23.3 The legitimate uses: per-request context (MDC, security context, transaction context,
       tenant id), and per-thread caching of a non-thread-safe expensive object
       (`SimpleDateFormat`, `Random`, a `ByteBuffer`).
1.23.4 `SimpleDateFormat` is the canonical example of a thread-unsafe JDK class — and the modern
       answer is `DateTimeFormatter`, which is immutable and needs no ThreadLocal at all.
       `[X-REF 03]` `[TRAP]`
1.23.5 **Trap — the thread-pool leak (correctness half).** Pool threads are reused indefinitely, so
       a value set during request A is still visible during request B on the same thread. Leaking
       a previous user's security context is a genuine security incident class. `[TRAP]`
       `[X-REF 13]`
1.23.6 **Trap — the thread-pool leak (memory half).** `ThreadLocalMap` keys are `WeakReference`s to
       the `ThreadLocal`, but **values are strong**. A dead ThreadLocal leaves a stale entry whose
       value is reachable from the live thread until the map happens to clean it. Pool threads
       never die. `[TRAP]` `[PROVE]`
1.23.7 The classloader-leak consequence in an app server: a ThreadLocal value whose class was
       loaded by the web app's classloader pins the entire classloader, so redeploys leak
       metaspace. `[X-REF 06]` `[RESEARCH]`
1.23.8 The fix: `try { CTX.set(v); ... } finally { CTX.remove(); }`. `remove()` clears the entry;
       `set(null)` leaves a live entry with a null value. `[TRAP]`
1.23.9 `InheritableThreadLocal`: copied to a child thread **at child construction**, which is
       exactly the wrong time for a pool (threads are created before the request exists).
       `[TRAP]`
1.23.10 `ThreadLocal` and virtual threads: each virtual thread gets its own copy, so caching an
        expensive object per thread now allocates one per *task*. The Oracle guide explicitly warns
        against it. `[TRAP]` `[SOURCE]` `[X-REF 04]`
1.23.11 `Thread.Builder.inheritInheritableThreadLocals(false)` and
        `-Djdk.virtualThreadScheduler...`/`--enable-preview` interactions for context propagation.
        `[RESEARCH]`
1.23.12 Context propagation across an executor boundary: the task must copy the context explicitly
        (a decorating `Runnable`, Spring's `TaskDecorator`, or Micrometer's `ContextSnapshot`).
        `[X-REF 07]` `[X-REF 20]` `[BUILD]`
1.23.13 MDC and distributed tracing as the highest-value real use, and why an async hop drops the
        trace id if you forget. `[X-REF 20]`

*(13 leaves)*

## §1.24 Virtual threads — the model

1.24.1 What a virtual thread is: a `java.lang.Thread` whose stack lives on the **heap** as a
       continuation and which is scheduled by the JVM onto a small pool of **carrier** platform
       threads. Final in Java 21 (JEP 444). `[X-REF 04]`
1.24.2 "Scale, not speed": a virtual thread is not faster; it lets you have a million of them.
       Throughput improves only when the bottleneck was thread count on blocking work. `[TRAP]`
       `[SOURCE]`
1.24.3 Mounting and unmounting: a virtual thread mounts onto a carrier to run, and unmounts at a
       blocking point, copying its stack frames to the heap. `[PROVE]`
1.24.4 The scheduler: a dedicated `ForkJoinPool` in **FIFO** mode, parallelism =
       `availableProcessors()` by default, tunable with
       `jdk.virtualThreadScheduler.parallelism` and `jdk.virtualThreadScheduler.maxPoolSize`.
       `[RESEARCH]` `[NUM]`
1.24.5 The instrumented blocking points that unmount: `BlockingQueue` operations,
       `LockSupport.park`, `ReentrantLock`, socket and file I/O through NIO,
       `Thread.sleep`, `Object.wait` (Java 24+), `Future.get`. `[RESEARCH]`
1.24.6 Pinning in Java 21 — the two causes: executing inside a `synchronized` block/method, and
       being inside a native frame (JNI or a Foreign Function call). `[SOURCE]`
1.24.7 The pinning failure mode: a pinned virtual thread holds its carrier while blocked. If every
       carrier is pinned, no other virtual thread can run — and if the pinned threads are waiting on
       something only another virtual thread can supply, the application **deadlocks**.
       `[TRAP]` `[PROVE]`
1.24.8 The Netflix incident: Spring Boot 3 + Tomcat + virtual threads, a `synchronized` block inside
       the Brave/Zipkin tracing library, all carriers pinned, instances hung. The fix was a library
       version using `ReentrantLock`. `[RESEARCH]` `[TRAP]`
1.24.9 Detection: `-Djdk.tracePinnedThreads=full|short`, and the `jdk.VirtualThreadPinned` JFR
       event (enabled by default, 20 ms threshold). `[NUM]` `[RESEARCH]`
1.24.10 **`[VERSION-TRAP]` JEP 491 (Java 24):** monitors became associated with the virtual thread
        rather than the carrier, so `synchronized` no longer pins. The advice "replace synchronized
        with ReentrantLock" is a Java-21-only fix. Native frames still pin. `[RESEARCH]`
1.24.11 The four JFR events: `jdk.VirtualThreadStart` (off by default), `jdk.VirtualThreadEnd`
        (off), `jdk.VirtualThreadPinned` (on, 20 ms), `jdk.VirtualThreadSubmitFailed` (on).
        `[RESEARCH]` `[NUM]`
1.24.12 Thread dumps: virtual threads do **not** appear in `jstack`. Use
        `jcmd <pid> Thread.dump_to_file -format=json <file>`, which groups them by the structured
        scope that created them and omits locks and JNI stats. `[DUMP]` `[TRAP]` `[RESEARCH]`
1.24.13 The three rules: **never pool** virtual threads; represent every task as one; limit
        concurrency with a `Semaphore`, not with a pool. `[SOURCE]`
1.24.14 `Executors.newVirtualThreadPerTaskExecutor()` is not a pool — it creates a thread per task
        and is intended to be used in try-with-resources. `[TRAP]`
1.24.15 Properties of a virtual thread that are fixed: always daemon (`setDaemon(false)` throws),
        always `NORM_PRIORITY` (`setPriority` is a no-op), no thread group manipulation, no
        `stackSize`. `[TRAP]` `[RESEARCH]`
1.24.16 Cost arithmetic: a platform thread reserves ~1 MB of stack; a virtual thread starts at a
        few hundred bytes of heap and grows its continuation as needed. One million virtual threads
        is routine; ten thousand platform threads is not. `[NUM]` `[PROVE]`
1.24.17 When virtual threads do **not** help: CPU-bound work (you still have N cores), workloads
        already using non-blocking I/O, and anything whose bottleneck is a downstream connection
        pool. `[TRAP]`
1.24.18 The downstream-pressure shift: removing your thread pool removes your implicit rate limit,
        so the load lands on the database connection pool instead. This is the #1 virtual-thread
        migration surprise. `[TRAP]` `[X-REF 08]`
1.24.19 Little's law applied to virtual threads: concurrency = throughput × latency, so 10 000 rps
        at 100 ms needs 1 000 concurrent threads. `[PROVE]` `[NUM]`

*(19 leaves)*

## §1.25 Structured concurrency and scoped values

1.25.1 The problem: `ExecutorService` + `Future` lets a task outlive its caller, leaks threads on
       error, and produces stack traces with no parent-child relationship. Unstructured concurrency
       is the `goto` of threading. `[PROVE]`
1.25.2 The principle: if a task splits into concurrent subtasks, they all return to the same place,
       in the same block, with the same lifetime.
1.25.3 The Java 21 preview API (JEP 453): `new StructuredTaskScope<T>()`, `fork(Callable)` returning
       `Subtask<T>`, `join()`, `joinUntil(Instant)`, `shutdown()`, `close()`, used in
       try-with-resources. `[X-REF 04]`
1.25.4 `StructuredTaskScope.ShutdownOnFailure` (`throwIfFailed`) and `ShutdownOnSuccess<T>`
       (`result()`) as the two built-in policies in 21.
1.25.5 `Subtask.State`: `UNAVAILABLE`, `SUCCESS`, `FAILED`; `get()` throws unless SUCCESS.
1.25.6 The ownership rules: only the owner thread may `fork`/`join`/`close`, the scope must be
       closed in the same thread and in LIFO order, and violations throw
       `StructureViolationException`. `[TRAP]`
1.25.7 **`[VERSION-TRAP]`** The API is *still preview* through Java 25 and has been reworked
       repeatedly: JEP 428 (19 incubator), 437, 453, 462, 480, 499, **505 (25)**, 525 (26), 533.
       Anything you memorise here may change. `[RESEARCH]`
1.25.8 The JEP 505 rework: constructors replaced by static `open()` factories; `ShutdownOnFailure`/
       `ShutdownOnSuccess` replaced by a **`Joiner`** abstraction (`allSuccessfulOrThrow`,
       `anySuccessfulResultOrThrow`, `awaitAll`, `awaitAllSuccessfulOrThrow`); a `Configuration`
       for name, timeout and thread factory; `Joiner.onTimeout`. `[RESEARCH]`
1.25.9 Structured concurrency versus `CompletableFuture.allOf`: error propagation, cancellation of
       siblings, and a readable stack trace are the three wins. Table.
1.25.10 The hedging / fastest-of pattern and the deadline pattern, written both ways.
1.25.11 `ThreadLocal`'s problems that motivate `ScopedValue`: unconstrained mutability, unbounded
        lifetime, and expensive inheritance to child threads.
1.25.12 `ScopedValue<T>`: `newInstance`, `where(key, value)`, `run(Runnable)`, `call(Callable)`,
        `get`, `isBound`, `orElse`, `orElseThrow`, `getWhere`, rebinding by nesting.
1.25.13 The immutability and lexical-scope guarantee: bound for the dynamic extent of the
        `run`/`call`, unbindable afterwards, inherited by structured subtasks without copying.
        `[PROVE]`
1.25.14 **`[VERSION-TRAP]`** ScopedValue history: preview in 21 (JEP 446), the static `runWhere`/
        `callWhere` removed in 24 (JEP 487) leaving only the fluent form, **final in Java 25 (JEP
        506)**, and `orElse` no longer accepts null. `[RESEARCH]`
1.25.15 The migration table: `ThreadLocal.set` → `ScopedValue.where(...).run(...)`;
        `ThreadLocal.get` → `ScopedValue.get`; `InheritableThreadLocal` → automatic inheritance in
        a structured scope; `remove()` → nothing needed.
1.25.16 What ScopedValue cannot do: it is not a mutable per-thread cache, and there is no way to set
        a value for the *caller's* scope from inside a callee. `[TRAP]`

*(16 leaves)*

## §1.26 Liveness failures

1.26.1 Deadlock defined: a cycle in the wait-for graph; no thread in the cycle can ever proceed.
1.26.2 The four Coffman conditions, all four necessary simultaneously: mutual exclusion,
       hold-and-wait, no preemption, circular wait. Break any one and deadlock is impossible.
       `[PROVE]`
1.26.3 Which condition each fix breaks: global lock ordering breaks circular wait;
       `tryLock(timeout)` breaks no-preemption/hold-and-wait; acquiring all locks atomically breaks
       hold-and-wait; lock-free algorithms break mutual exclusion. `[PROVE]`
1.26.4 Lock-ordering deadlock: the account-transfer example, where `transfer(a,b)` and
       `transfer(b,a)` race.
1.26.5 The `System.identityHashCode` tiebreaker solution, including the third "tie lock" for the
       rare hash collision. This is the expected answer to the transfer question. `[BUILD]`
1.26.6 Dynamic lock-ordering deadlock and why it is invisible in code review: the order depends on
       the *arguments*, not the source.
1.26.7 Deadlock between cooperating objects, via an alien method called while holding a lock.
1.26.8 Open calls: invoking a method with no locks held. The structural fix for 1.26.7.
1.26.9 Resource deadlocks: two connection pools, or a bounded thread pool where tasks wait on tasks.
1.26.10 `tryLock` with timeout and randomised backoff as the polled alternative. `[BUILD]`
1.26.11 **Livelock**: threads keep responding to each other and make no progress. Two forms — the
        corridor dance, and the transactional retry loop that always retries the same failing
        message (a poison message re-delivered forever). Fix with randomised backoff and a DLQ.
        `[X-REF 14]`
1.26.12 **Starvation**: a thread never gets the resource. Causes: a barging lock plus a hot thread,
        thread priorities, and an unfair read-write lock under constant readers.
1.26.13 **Lock convoy**: many threads serialise behind one slow holder and stay in lockstep even
        after the slow phase ends, because each hand-off costs a context switch.
1.26.14 **Missed signal / lost wakeup** as a liveness failure in its own right (§1.12.12).
1.26.15 Detection with a thread dump: `jstack` prints "Found one Java-level deadlock:" plus the
        cycle and the `waiting to lock <0x…> which is held by` chain. `[DUMP]`
1.26.16 `ThreadMXBean.findDeadlockedThreads()` (monitors **and** ownable synchronizers) versus
        `findMonitorDeadlockedThreads()` (monitors only). The former is cheap enough to run as a
        production guard-rail. `[RESEARCH]` `[BUILD]`
1.26.17 **Trap:** the JVM *detects* deadlock but never *breaks* it. The only recovery is a restart,
        which is why prevention beats detection. `[TRAP]` `[RESEARCH]`
1.26.18 What the deadlock detector cannot see: deadlocks through `Semaphore` permits, through a
        bounded queue, through a thread pool, through class-initialisation locks, and through a
        database lock. `[TRAP]` `[RESEARCH]`
1.26.19 The "hidden deadlock" case: lock-ordering cycles involving `java.util.concurrent` locks
        acquired in a way the HotSpot detector does not model. `[RESEARCH]`
1.26.20 The never-do list: never hold two locks while calling code you do not control; never hold a
        lock across I/O; never hold a lock while acquiring a pooled resource.

*(20 leaves)*

**PART 1 total: 10+15+18+12+14+13+12+18+14+26+22+16+29+29+18+24+18+19+22+10+27+16+13+19+16+20 = 470 leaves**

---

# PART 2 — INTERMEDIATE

## §2.1 The master tables

2.1.1 **The master cost table** — one row per operation of every primitive in this guide, with the
      columns: *uncontended cost*, *contended cost*, *worst case*, *does it block*, *does it
      allocate*, *does it context-switch*. Rows must cover: plain field read/write, volatile
      read, volatile write, `synchronized` enter (thin), `synchronized` enter (inflated,
      contended), CAS success, CAS failure+retry, `ReentrantLock.lock` uncontended,
      `ReentrantLock.lock` contended, `ReadWriteLock` read/write, `StampedLock` optimistic read,
      `LongAdder.increment`, `ConcurrentHashMap.get/put`, `CopyOnWriteArrayList.add`,
      `ArrayBlockingQueue.put/take`, `LinkedBlockingQueue.put/take`, `SynchronousQueue` handoff,
      `Executor.execute`, `CompletableFuture` stage hop, virtual-thread park/unpark, platform-thread
      park/unpark. `[NUM]`
2.1.2 The **latency ladder** every number in this file must be anchored to: L1 ≈ 1 ns, L2 ≈ 4 ns,
      L3 ≈ 15–40 ns, remote-socket L3 / cache-line transfer ≈ 100+ ns, main memory ≈ 80–100 ns,
      uncontended CAS ≈ 10–20 ns, contended CAS ≈ 100+ ns, park/unpark round trip ≈ 1–10 µs,
      thread creation ≈ 50–200 µs (platform) vs ≈ 1 µs (virtual). Every claim of "cheap" or
      "expensive" resolves to this ladder. `[NUM]` `[RESEARCH]`
2.1.3 The **memory-footprint table**: platform thread (1 MB reserved stack + ~1 KB `Thread` +
      JVM `JavaThread` + OS `task_struct`), virtual thread (`Thread` object + `Continuation` +
      `StackChunk` growing from a few hundred bytes), `ReentrantLock` (~48 B: object header + Sync
      + state + exclusiveOwnerThread), `AtomicLong` (16 B), `LongAdder` (base + `Cell[]` with 128-B
      padded cells, so N cells ≈ N × 128 B), `ConcurrentHashMap.Node` (32 B), `ArrayBlockingQueue`
      (array only), `LinkedBlockingQueue` (one `Node` per element). Arithmetic shown, not asserted.
      `[NUM]`
2.1.4 The **guarantee table**: for each of plain / opaque / release / acquire / volatile /
      `synchronized` / `final`, which of {atomicity, visibility, ordering, mutual exclusion,
      progress} it supplies. This is the table that kills the "volatile is atomic" confusion.
2.1.5 The **progress-guarantee table**: blocking, obstruction-free, lock-free, wait-free
      (bounded and population-oblivious), with a JDK example of each and the counter-example.
      `[PROVE]`
2.1.6 The **iterator-semantics table**: fail-fast / weakly consistent / snapshot, per collection,
      with the exception thrown or not thrown and the staleness window.
2.1.7 The **decision table for "how do I make this safe"**: confinement → immutability →
      atomic → concurrent collection → lock → lock-free custom, in ascending order of cost and
      descending order of preference. The right answer is almost always the first one that works.
2.1.8 The **"which thread runs it"** table for every asynchronous API: `Executor.execute`,
      `submit`, `CompletableFuture` non-async / `Async` / `Async(executor)`, parallel stream,
      `ConcurrentHashMap` bulk op, `ScheduledExecutorService`, `StructuredTaskScope.fork`,
      Spring `@Async`. `[X-REF 07]`

*(8 leaves)*

## §2.2 Contention economics

2.2.1 The contention cost model: a critical section costs *acquisition + body + release +
      the coherence traffic on the lock word*. Only the body does work. `[PROVE]`
2.2.2 Why the lock word itself is the bottleneck before the body is: every acquisition invalidates
      the cache line holding the lock state on every other core, so the lock line ping-pongs.
      `[PROVE]`
2.2.3 The three contention reducers, in order of effectiveness: **reduce lock duration**,
      **reduce lock frequency** (lock splitting / striping), **replace exclusion** (atomics,
      immutability, confinement, read-write, copy-on-write).
2.2.4 Lock **splitting**: one lock per independent invariant (a `users` lock and an `orders` lock,
      not one `state` lock).
2.2.5 Lock **striping**: N locks over one logical structure, keyed by `hash % N` — the Java 7
      `ConcurrentHashMap` segment design, and why Java 8 replaced it with per-bin locking.
      `[X-REF 02]`
2.2.6 The cost of striping: any operation that spans stripes (`size()`, `clear()`, rehash) must
      take **all** locks, in a fixed order. `[PROVE]`
2.2.7 Hot fields and how to spot them: one `AtomicLong` incremented by every request is a single
      cache line touched by every core. The fix is striping (`LongAdder`), not a faster CAS.
      `[NUM]`
2.2.8 Contention measurement, not guessing: JFR `jdk.JavaMonitorEnter` /
      `jdk.JavaMonitorWait` / `jdk.ThreadPark` events, `-XX:+PrintConcurrentLocks` in a dump,
      async-profiler `-e lock`, and `perf c2c` for false sharing. `[DUMP]` `[RESEARCH]`
2.2.9 The **Universal Scalability Law** applied: σ (contention) and κ (coherence) fitted to
      measured throughput tells you the thread count at which adding threads makes things worse.
      `[PROVE]` `[NUM]` `[RESEARCH]`
2.2.10 Uncontended-lock cost is genuinely small (tens of nanoseconds) and the JIT often removes it
       entirely (§3.3). "Locks are slow" is a statement about *contention*, not about locks.
       `[TRAP]`
2.2.11 The contention cliff: a lock that is fine at 8 threads can collapse at 64, because the cost
       per acquisition grows with the number of waiters, not just the number of acquisitions.
       `[PROVE]`
2.2.12 When more contention is the *correct* answer: sometimes serialising is cheaper than the
       coordination needed to avoid it (a single-writer design, LMAX Disruptor style).
       `[RESEARCH]`
2.2.13 Amdahl applied to a critical section: if 5 % of request time is inside one global lock, the
       system cannot exceed 20× the single-thread throughput no matter how many cores. `[PROVE]`
       `[NUM]`
2.2.14 The single-writer principle and why message-passing / sharding often beats sharing.

*(14 leaves)*

## §2.3 Choosing a synchronization primitive

2.3.1 `synchronized` vs `ReentrantLock`: the eight-row decision table (simplicity, exception
      safety, timed acquire, interruptible acquire, fairness, multiple conditions, instrumentation,
      virtual-thread pinning) with the Java-21-vs-24 split on the last row. `[VERSION-TRAP]`
2.3.2 The default answer is `synchronized`, and you should be able to say why: it is
      exception-safe by construction, visible in thread dumps as a monitor, and JIT-optimisable
      (elision, coarsening, biased-free thin locking).
2.3.3 When `ReentrantLock` earns its keep: a deadline on acquisition, cancellable acquisition,
      hand-over-hand locking across method boundaries, or more than one condition predicate.
2.3.4 When `ReadWriteLock` earns its keep, quantified: read fraction > ~90 % **and** critical
      section long enough that the extra CAS on the shared count is amortised. Below that, a plain
      lock wins. `[NUM]` `[TRAP]`
2.3.5 When `StampedLock` earns its keep: small, read-dominated, non-reentrant, no conditions
      needed — geometry/coordinate objects, cached configuration snapshots.
2.3.6 When an atomic is the answer: single-variable state, no cross-field invariant.
2.3.7 When a concurrent collection is the answer: the invariant is entirely inside the collection.
2.3.8 When immutability is the answer, and why it should be your first attempt: no synchronization
      at all, `final` fields, safe publication for free. `[X-REF 03]`
2.3.9 When confinement is the answer: an actor/queue design where each piece of state has exactly
      one owning thread.
2.3.10 When a `Semaphore` is the answer: bounding a *resource*, not protecting *state*.
2.3.11 When "do not share it" is the answer: a per-request object, a `ThreadLocal`, or a
       `ScopedValue`.
2.3.12 The escalation ladder written as a flowchart, ending at "hand-rolled lock-free" with the
       warning that this is the point at which you need jcstress. `[RESEARCH]`
2.3.13 Fairness: when you actually want it (long critical sections, latency SLA on the tail,
       avoiding starvation of a rare writer) and the throughput factor you pay (often 10–100×
       fewer acquisitions/second). `[NUM]` `[PROVE]`
2.3.14 Reentrancy as a design smell: needing it usually means a public method calls another public
       method of the same object; consider the private-worker-method pattern instead.

*(14 leaves)*

## §2.4 Pool sizing and executor configuration

2.4.1 The CPU-bound formula: `N_threads = N_cores + 1`, and where the "+1" comes from (a thread
      occasionally page-faults or takes a compulsory cache miss). `[NUM]`
2.4.2 The I/O-bound formula: `N = N_cores × U × (1 + W/C)` where U is target utilisation, W is
      wait time and C is compute time. Derived from Little's law, not memorised. `[PROVE]`
      `[NUM]`
2.4.3 Worked example with real numbers: 8 cores, 90 % target utilisation, 100 ms downstream wait,
      2 ms compute → `8 × 0.9 × 51 = 367` threads, and the immediate observation that 367 platform
      threads is a bad idea — which is the argument for virtual threads. `[NUM]` `[PROVE]`
2.4.4 Why the formula is a starting point, not an answer: it assumes a single homogeneous workload
      and no downstream limit. Measure, then set.
2.4.5 Sizing the **queue**, not just the pool: queue length × service time = added latency. A
      1000-deep queue in front of a 50 ms service adds up to 50 s of latency before the first
      rejection. `[NUM]` `[PROVE]`
2.4.6 The latency-vs-loss decision: a short queue sheds load early and keeps p99 low; a long queue
      absorbs bursts and destroys p99. Choose deliberately per workload. `[X-REF 20]`
2.4.7 `corePoolSize == maximumPoolSize` with a bounded queue is the sane default configuration for
      a server, plus `allowCoreThreadTimeOut` if idle cost matters.
2.4.8 The four-parameter interaction matrix: core, max, queue capacity, rejection policy — the
      sixteen sensible combinations and what each one *means* as a policy.
2.4.9 Per-workload pools (bulkheads) and how many is too many: each pool is idle threads plus a
      queue; ten pools of forty threads is four hundred threads. `[NUM]`
2.4.10 Sizing against the **downstream** limit, not the local one: if the connection pool has 20
       connections, a 200-thread pool just moves the queue. `[X-REF 08]` `[TRAP]`
2.4.11 Container CPU limits: `availableProcessors()` reads cgroup quota since JDK 10; a 0.5-CPU
       limit reports 1; `-XX:ActiveProcessorCount` overrides. Every default-sized pool in your app
       and in every library changes when this number changes. `[X-REF 19]` `[TRAP]` `[RESEARCH]`
2.4.12 The libraries that silently size themselves off `availableProcessors()`: the common
       ForkJoinPool, the virtual-thread scheduler, Netty event loops, Tomcat, Reactor schedulers,
       G1 worker threads. Enumerate them, because they all mis-size together. `[X-REF 06]`
2.4.13 Warm-up: `prestartAllCoreThreads()`, and the JIT-warmup interaction that makes the first
       thousand requests slow regardless. `[X-REF 06]`
2.4.14 Monitoring a pool in production: queue depth, active count, completed count, rejection
       count, and task latency split into *queue time* and *execution time*. Queue time is the
       metric almost nobody exports and the one that explains the incident. `[X-REF 20]`
2.4.15 Micrometer's `ExecutorServiceMetrics` and what it names each of the above.
       `[RESEARCH]` `[X-REF 20]`
2.4.16 Rejection as a *feature*: a rejection is a fast, honest failure. A full queue is a slow,
       dishonest one.
2.4.17 Sizing a scheduled pool: one slow task blocks the whole scheduler, so either size for the
       worst concurrent overlap or dispatch the body to a separate executor.
2.4.18 The "pool of one" pattern for serialising access to a non-thread-safe resource, and why it
       is often better than a lock (no blocking, natural queueing, observable depth).

*(18 leaves)*

## §2.5 The atomicity decision in practice

2.5.1 Counter decision: `int` + `synchronized` vs `AtomicInteger` vs `LongAdder` vs
      `ConcurrentHashMap.merge` vs a per-thread counter summed at read. Five options, one table.
2.5.2 The crossover measurement: `AtomicLong` beats `LongAdder` below ~2–4 concurrent writers
      and loses badly above it; `LongAdder.sum()` costs O(cells). Show a JMH result shape.
      `[NUM]` `[PROVE]`
2.5.3 Cache-decision: `ConcurrentHashMap.computeIfAbsent` vs Caffeine vs a `Map` guarded by a
      lock, and the three properties that decide it (blocking under the bin lock, eviction,
      refresh). `[X-REF 15]`
2.5.4 The "compute under the bin lock" workaround: compute outside, then `putIfAbsent`, accepting
      duplicate computation; or store a `CompletableFuture` in the map so only one thread computes
      and the rest join. `[BUILD]`
2.5.5 Accumulator decision: `AtomicReference` + CAS loop vs `LongAccumulator` vs a lock, and the
      requirement that the function be pure and associative. `[PROVE]`
2.5.6 Multi-variable invariant: two atomics never make an atomic pair, so the options are one lock
      or one immutable value object swapped by a single `AtomicReference.compareAndSet`.
      `[PROVE]` `[BUILD]`
2.5.7 The immutable-snapshot-in-an-AtomicReference pattern as the general lock-free technique for
      compound state, and its cost (allocation per update, retry under contention). `[BUILD]`
2.5.8 Copy-on-write as the same idea for collections, and its O(n) write cost.
2.5.9 Idempotence as a substitute for atomicity in distributed settings. `[X-REF 14]`
2.5.10 The "check then act" removal checklist: is there an atomic compound method? Can the state be
       collapsed into one variable? Can the operation be made idempotent? Only then, a lock.

*(10 leaves)*

## §2.6 The concurrent collection decision

2.6.1 `ConcurrentHashMap` vs `Collections.synchronizedMap` vs `Hashtable` vs an immutable map
      rebuilt on change: four-way table on read cost, write cost, compound atomicity, iteration.
2.6.2 `ConcurrentHashMap` vs `ConcurrentSkipListMap`: hashing vs ordering, O(1) vs O(log n),
      O(1) vs O(n) `size()`, and `NavigableMap` operations as the deciding feature. `[NUM]`
2.6.3 `CopyOnWriteArrayList` vs `Collections.synchronizedList` vs `ConcurrentLinkedQueue` for a
      listener registry, an audit buffer, and a work list — three different right answers.
2.6.4 The queue selection table extended with the *why*: `ArrayBlockingQueue` for a fixed bound and
      no allocation; `LinkedBlockingQueue` for throughput with the bound set explicitly;
      `SynchronousQueue` for handoff; `LinkedTransferQueue` when you want handoff *or* buffering;
      `PriorityBlockingQueue` when order matters and backpressure does not; `DelayQueue` for
      timers.
2.6.5 The `ConcurrentLinkedQueue` vs `LinkedBlockingQueue` decision: non-blocking with a busy
      consumer, versus blocking with an idle consumer. Polling an empty `ConcurrentLinkedQueue` in
      a loop burns a core. `[TRAP]`
2.6.6 Unbounded `ConcurrentLinkedQueue` as an accidental memory leak — it has no bound and no
      backpressure at all. `[TRAP]`
2.6.7 Concurrent `Set` options: `ConcurrentHashMap.newKeySet()`, `ConcurrentSkipListSet`,
      `CopyOnWriteArraySet` (which is O(n) `contains` because it is backed by the array). `[NUM]`
      `[TRAP]`
2.6.8 There is no concurrent `List` with index semantics, and the workarounds: partitioning,
      an immutable list swapped atomically, or a queue plus a snapshot.
2.6.9 Bounded caches: why `LinkedHashMap` + `removeEldestEntry` is not thread-safe and what to use
      instead. `[X-REF 02]` `[X-REF 15]`
2.6.10 `Collections.unmodifiableXxx` is a **view**, not a copy, and gives no thread safety at all;
       `List.copyOf`/`Map.copyOf` are genuine immutable copies and are safely publishable.
       `[TRAP]` `[X-REF 02]` `[X-REF 03]`
2.6.11 Views, copies and snapshots restated for concurrency: `keySet()` is a live view;
       `toArray()` is a weakly consistent snapshot; a CoW iterator is a strong snapshot; `copyOf`
       is a copy. Each mistake has a distinct symptom. `[TRAP]`
2.6.12 Bulk operations on concurrent collections are not atomic: `addAll`, `putAll`, `removeIf`,
       `clear`, and `toArray` all interleave. `[TRAP]` `[PROVE]`
2.6.13 Streaming a concurrent collection: the spliterator is weakly consistent, so a parallel
       stream over a live `ConcurrentHashMap` gives a well-defined but non-snapshot traversal.
       `[X-REF 04]`
2.6.14 `Collector` concurrency: `Collectors.toConcurrentMap` and `groupingByConcurrent` require an
       unordered stream and a concurrent container to avoid the merge step. `[X-REF 04]`
       `[RESEARCH]`

*(14 leaves)*

## §2.7 Producer–consumer and backpressure design

2.7.1 The four backpressure mechanisms ranked: block the producer (bounded queue), run on the
      producer (`CallerRunsPolicy`), shed (reject/drop), and buffer to disk. Each with the failure
      mode it converts into.
2.7.2 Blocking the producer only works if the producer *is* the source. If the producer is an HTTP
      request thread, blocking it just moves the queue into the socket backlog. `[TRAP]`
      `[X-REF 10]`
2.7.3 Load shedding done properly: shed cheap requests first, return 429/503 with `Retry-After`,
      and export the shed rate. `[X-REF 12]` `[X-REF 20]`
2.7.4 Batching at the consumer: `drainTo` amortises the lock acquisition and the downstream round
      trip; measure the batch-size/latency trade-off. `[NUM]`
2.7.5 The multi-stage pipeline: each stage gets its own bounded queue and its own pool, so the
      slowest stage becomes the visible bottleneck instead of an invisible one.
2.7.6 Fan-out/fan-in with a `CompletionService` or `StructuredTaskScope`, and why processing in
      completion order beats submission order for tail latency. `[PROVE]`
2.7.7 Ordering requirements: total order forces a single consumer; per-key order allows N consumers
      with a key-hash partition. This is exactly Kafka's partition model. `[X-REF 14]`
2.7.8 Graceful shutdown of a pipeline, in order: stop accepting, drain in stage order, poison-pill
      or interrupt, await with a deadline, force. `[BUILD]`
2.7.9 The at-least-once/at-most-once choice at the queue boundary, and where the ack goes.
      `[X-REF 14]`
2.7.10 In-JVM queues versus a broker: durability, visibility, and the "your queue is a distributed
       system now" line. `[X-REF 14]`
2.7.11 Rate limiting inside the JVM: `Semaphore`, a token bucket over `ScheduledExecutorService`,
       and Resilience4j's `RateLimiter`/`Bulkhead`. `[RESEARCH]` `[X-REF 12]`
2.7.12 The bulkhead + circuit breaker + timeout triad as the standard resilience stack, and how
       each maps onto a concurrency primitive. `[X-REF 20]` `[RESEARCH]`

*(12 leaves)*

## §2.8 `CompletableFuture` in anger

2.8.1 The executor discipline: pass an executor to every `*Async` call, and never use the common
      pool for anything that blocks. `[TRAP]`
2.8.2 Making the discipline enforceable: subclass `CompletableFuture` overriding
      `defaultExecutor()`, or wrap construction in a factory. `[BUILD]`
2.8.3 The thread-hopping cost: each `*Async` stage is a task submission — a queue push plus a
      possible unpark. Chaining twenty async stages costs twenty hops. `[NUM]` `[PROVE]`
2.8.4 When *not* to use `Async`: cheap, non-blocking transformations should run inline on the
      completing thread.
2.8.5 The context-propagation problem: MDC, security context, and tracing context do not follow a
      stage hop. The three fixes: a decorating `Executor`, Micrometer `ContextSnapshot`, or
      `ScopedValue` + structured concurrency. `[X-REF 20]` `[BUILD]`
2.8.6 Timeout composition: `orTimeout` fails the *future*, not the *work*. Cancelling the work
      requires the underlying task to be interruptible and to be held for cancellation. `[TRAP]`
      `[BUILD]`
2.8.7 Retry over `CompletableFuture`: why a naive recursive retry leaks stack/allocation, and the
      `delayedExecutor` + attempt-count pattern. `[BUILD]`
2.8.8 `allOf` with results, written correctly: `allOf(...).thenApply(v -> list.stream().map(
      CompletableFuture::join).toList())`. `[BUILD]`
2.8.9 "First successful" — not `anyOf` — implemented by hand, and why the JDK still has no
      built-in. `[BUILD]` `[TRAP]`
2.8.10 Bounded parallelism over a collection of futures without a pool: a `Semaphore` gate, or
       chunking, or `StructuredTaskScope`.
2.8.11 Error semantics you must be able to draw: which stages run and which are skipped when stage
       2 of 5 fails, for `thenApply` / `handle` / `whenComplete` / `exceptionally`. `[PROVE]`
2.8.12 Debuggability: a `CompletableFuture` stack trace shows the completing thread, not the
       submitting one — the single biggest operational argument for virtual threads plus blocking
       code. `[PROVE]` `[TRAP]`
2.8.13 `CompletableFuture` vs Reactor/RxJava vs virtual threads: the three-way table on
       backpressure, operators, debuggability, learning cost, and library ecosystem.
       `[RESEARCH]`
2.8.14 Interop: `Mono.fromFuture`, `Mono.toFuture`, `CompletableFuture.supplyAsync` over a virtual
       thread executor, and the Spring `WebClient` boundary. `[X-REF 07]` `[RESEARCH]`

*(14 leaves)*

## §2.9 Virtual threads in production

2.9.1 The migration checklist: enable per-workload, not globally; audit for `synchronized` on
      blocking paths (Java 21 only); audit for `ThreadLocal` caches; add a `Semaphore` at every
      bounded downstream; re-size connection pools; re-check monitoring. `[RESEARCH]`
2.9.2 `spring.threads.virtual.enabled=true` (Spring Boot 3.2+) — what it actually switches
      (Tomcat's protocol handler executor, `@Async`, and the Spring task scheduler) and what it
      does not. `[X-REF 07]` `[RESEARCH]`
2.9.3 The measured `ThreadLocal` regression: per-thread caches under virtual threads become
      per-task allocations; one reported benchmark went from 200 to 443 267 cache initialisations
      for the same workload, with no exception — the symptom is GC pressure. `[RESEARCH]`
      `[NUM]` `[TRAP]`
2.9.4 The dominant post-migration failure mode is **downstream resource exhaustion**: connection
      pool ceilings, file-descriptor limits, downstream rate limits, database queueing. Removing
      your pool removed your rate limiter. `[TRAP]` `[RESEARCH]` `[X-REF 08]`
2.9.5 File descriptors: one million virtual threads doing socket I/O still needs one million file
      descriptors. `ulimit -n` becomes the new bound. `[X-REF 11]` `[NUM]`
2.9.6 The CLOSE_WAIT signature of a pinned/hung Loom app: JVM alive, no traffic served, sockets
      accumulating in CLOSE_WAIT, `jstack` showing an idle JVM. `[DUMP]` `[RESEARCH]`
2.9.7 Diagnosing pinning: JFR `jdk.VirtualThreadPinned` (20 ms threshold), `jcmd Thread.dump_to_file
      -format=json`, and — in Java 21 only — `-Djdk.tracePinnedThreads` (removed in Java 24).
      `[VERSION-TRAP]` `[RESEARCH]` `[DUMP]`
2.9.8 Residual pinning causes after JEP 491: native frames (JNI, FFM), class-loading/initialisation
      in some paths, and file I/O on Linux (no production io_uring integration in the JDK).
      `[RESEARCH]` `[VERSION-TRAP]`
2.9.9 Sizing the carrier pool: `jdk.virtualThreadScheduler.parallelism` (default
      `availableProcessors()`), `jdk.virtualThreadScheduler.maxPoolSize` (default 256),
      and when raising parallelism is right (mixed CPU work) versus wrong (it never fixes
      blocking). `[NUM]` `[RESEARCH]`
2.9.10 Structured concurrency as the *default* shape for fan-out once you have virtual threads, and
       the migration from `invokeAll`/`allOf`. `[X-REF 04]`
2.9.11 Observability changes: thread-count metrics become meaningless; you now measure in-flight
       tasks, downstream permits, and queue depth at the semaphore. `[X-REF 20]`
2.9.12 The honest cost table: virtual threads add heap pressure (continuations), lose thread-dump
       familiarity, and gain nothing for CPU-bound work. `[NUM]`
2.9.13 The libraries that must be checked before migrating: JDBC drivers, the connection pool,
       tracing agents, logging appenders (`synchronized` in the appender is the classic), and any
       object-pooling library. `[RESEARCH]` `[TRAP]`
2.9.14 The rollback plan: a virtual-thread migration must be a runtime flag, not a rewrite.

*(14 leaves)*

## §2.10 Thread-safe class design

2.10.1 The design sequence: state the invariants → choose the confinement/locking policy →
       document it → enforce it with `@GuardedBy` → test it.
2.10.2 Delegating thread safety to a thread-safe component, and the exact condition under which
       delegation is valid: the delegate's invariants must be the class's *only* invariants.
       `[PROVE]`
2.10.3 When delegation fails: two thread-safe fields with a constraint between them (a range with
       `lower` and `upper`). `[PROVE]` `[TRAP]`
2.10.4 The Java monitor pattern versus a private lock object, and the argument for the private
       lock: callers cannot participate in (or break) your locking policy.
2.10.5 Extending a thread-safe class: subclassing, client-side locking on the correct lock object,
       and composition with a wrapper. Three techniques, with the fragility of each.
2.10.6 Client-side locking's failure mode: locking on the wrapper instead of the underlying
       collection (`Collections.synchronizedList` synchronizes on the wrapper, so you must too).
       `[TRAP]` `[SOURCE]`
2.10.7 Composition (a `ForwardingCollection` with its own lock) as the robust answer, at the cost
       of an extra layer of locking.
2.10.8 Documenting the policy: the class javadoc must say what is thread-safe, on what lock, and
       what the caller must do for compound actions.
2.10.9 Designing for cancellation: every long-running method should either be interruptible or
       accept a deadline.
2.10.10 Designing for shutdown: every component that owns a thread must own its lifecycle and
        expose a `close()`; ownership of a passed-in executor must be explicit.
2.10.11 The "thread-safe by construction" checklist for a value type: final class, final fields,
        no escaping references, defensive copies in and out. `[X-REF 03]`
2.10.12 Defensive copying on the way *out* as well as in, and the `List.copyOf` shortcut.
2.10.13 Builders and thread safety: a builder is thread-*hostile* by design; the built object is
        immutable.
2.10.14 Lazy fields in an otherwise immutable object: the racy-single-check idiom (`String.hash`)
        and its exact precondition — the computed value must be immutable and idempotent.
        `[PROVE]` `[TRAP]`
2.10.15 Thread-safety of common JDK types, as a table: `String`, `StringBuilder` (no),
        `StringBuffer` (yes), `SimpleDateFormat` (no), `DateTimeFormatter` (yes), `Random` (yes but
        contended), `SecureRandom` (yes, contended), `BigDecimal` (immutable),
        `SimpleDateFormat`'s calendar field as the actual culprit. `[X-REF 03]`
2.10.16 Thread-safety of Spring beans: singletons are shared, so instance fields are shared state;
        prototype and request scopes; `@Transactional` and thread affinity of the
        `EntityManager`. `[X-REF 07]` `[X-REF 08]`

*(16 leaves)*

## §2.11 `ThreadLocal` and context propagation in practice

2.11.1 The context-propagation problem stated generally: request-scoped state must cross an
       executor boundary, and no JDK mechanism does it automatically for pools.
2.11.2 The five mechanisms: manual copy, a decorating `Runnable`/`Callable`, a decorating
       `Executor`, Micrometer `ContextPropagation`/`ContextSnapshot`, and `ScopedValue` +
       structured concurrency. `[RESEARCH]`
2.11.3 Spring's `TaskDecorator`, and the Boot 3.2 `spring.mvc.async` / `DelegatingSecurityContext*`
       wrappers. `[X-REF 07]` `[RESEARCH]`
2.11.4 SLF4J MDC: `MDC.getCopyOfContextMap()` / `setContextMap` / `clear`, and why `clear` in a
       `finally` is mandatory in a pool. `[X-REF 20]`
2.11.5 OpenTelemetry `Context` and `Scope`: the same pattern with a `try (Scope s = ctx.makeCurrent())`
       shape. `[X-REF 20]` `[RESEARCH]`
2.11.6 The `ThreadLocal` audit: how to find leaks — a heap dump filtered on `ThreadLocalMap$Entry`,
       and the "value class loaded by a dead classloader" signature. `[X-REF 06]` `[DUMP]`
2.11.7 `ThreadLocal` cleanup semantics in detail: stale-entry expunging happens opportunistically
       during `get`/`set`/`remove`, so a leak can persist indefinitely if the map is never touched
       again. `[PROVE]`
2.11.8 The virtual-thread rule: `ThreadLocal` is still supported and still works, but as *context*,
       never as a *cache*. `[TRAP]`
2.11.9 `ScopedValue` as the replacement, with the migration table, and the constraint that makes it
       safe: the value cannot be mutated and cannot outlive the scope. `[X-REF 04]`
2.11.10 What still needs `ThreadLocal` after `ScopedValue`: anything that must be *set* by a callee
        for its caller, and anything crossing a non-structured boundary. `[TRAP]`

*(10 leaves)*

## §2.12 Testing and verifying concurrent code

2.12.1 Why unit tests do not find concurrency bugs: they exercise one interleaving out of an
       astronomically large space, on one memory model, warm or cold. `[PROVE]`
2.12.2 What you *can* test deterministically: the state machine (with a latch-driven schedule), the
       cancellation protocol, the shutdown path, and the lock policy (via `Thread.holdsLock`
       assertions).
2.12.3 The `CountDownLatch` start-gate/end-gate harness for maximising interleaving pressure.
       `[BUILD]`
2.12.4 Deterministic scheduling: a single-threaded `Executor` injected in tests, and the general
       "inject the executor" design rule that makes concurrent code testable. `[X-REF 16]`
2.12.5 `Awaitility` for asserting eventual conditions instead of `Thread.sleep`. `[X-REF 16]`
       `[RESEARCH]`
2.12.6 Stress testing: run N threads × M iterations, assert an invariant, and repeat on a machine
       with a weak memory model (AArch64) — the second half is what most teams skip. `[TRAP]`
2.12.7 **jcstress**: the OpenJDK harness for litmus tests against the JMM; `@JCStressTest`,
       `@Outcome`, `@State`, `@Actor`, `@Arbiter`. It is the only tool that can *show* a
       reordering. `[RESEARCH]` `[BUILD]`
2.12.8 A worked jcstress litmus test for the classic store-buffering (Dekker) case, with the
       four outcomes and which are ACCEPTABLE vs ACCEPTABLE_INTERESTING. `[BUILD]` `[RESEARCH]`
2.12.9 JMH for concurrency benchmarks: `@State(Scope.Benchmark)`, `@Threads`, `@Group`/`@GroupThreads`
       for asymmetric read/write benchmarks, `Blackhole`, and why a naive loop benchmark measures
       nothing. `[X-REF 06]` `[RESEARCH]`
2.12.10 The benchmark traps specific to concurrency: measuring an uncontended lock and concluding
        about a contended one; measuring on an idle machine; forgetting that the JIT elides
        thread-local locks. `[TRAP]`
2.12.11 Static analysis: ErrorProne's `@GuardedBy` checker, SpotBugs' concurrency detectors
        (`IS2_INCONSISTENT_SYNC`, `DC_DOUBLECHECK`, `LI_LAZY_INIT_STATIC`, `NN_NAKED_NOTIFY`,
        `SWL_SLEEP_WITH_LOCK_HELD`). `[RESEARCH]`
2.12.12 Runtime detection: `ThreadMXBean.findDeadlockedThreads()` on a watchdog schedule, a
        lock-timeout policy that logs instead of hanging, and JFR's monitor events. `[BUILD]`
2.12.13 Chaos-style verification: run with `-XX:+UseSerialGC`/fewer cores/`taskset` to change the
        interleaving distribution, and on a different architecture. `[RESEARCH]`
2.12.14 Reproducing a heisenbug: increase thread count, add `Thread.onSpinWait`, remove logging (the
        logging is often the accidental barrier), and run under a weak-memory machine. `[TRAP]`

*(14 leaves)*

## §2.13 The concurrency-adjacent utility surface

2.13.1 `TimeUnit`: the enum constants, `sleep`, `convert`, `toMillis`/`toNanos`, `timedWait`,
       `timedJoin`, and the Java 9 `of(ChronoUnit)`/`toChronoUnit`. `[RESEARCH]`
2.13.2 `Duration`-accepting overloads added in Java 19 (`Thread.sleep`, `Thread.join`,
       `Future`-adjacent APIs) and why they are preferable. `[X-REF 03]` `[VERSION-TRAP]`
2.13.3 `System.nanoTime()` versus `System.currentTimeMillis()` for timeouts: nanoTime is monotonic
       within a JVM and is the only correct basis for a deadline; currentTimeMillis jumps with NTP.
       `[TRAP]` `[NUM]`
2.13.4 Deadline arithmetic that survives overflow: `System.nanoTime() - deadline >= 0`, never
       `nanoTime() >= deadline`. `[PROVE]` `[TRAP]`
2.13.5 `ThreadMXBean`: `getThreadInfo`, `dumpAllThreads`, `getThreadCpuTime`,
       `setThreadContentionMonitoringEnabled`, `getBlockedCount`/`getBlockedTime`/
       `getWaitedCount`/`getWaitedTime`, `findDeadlockedThreads`. The programmatic thread dump.
       `[X-REF 06]` `[RESEARCH]`
2.13.6 The cost of contention monitoring (it is off by default because it is not free) and of
       `getThreadCpuTime`. `[NUM]`
2.13.7 `Runtime.availableProcessors`, `Runtime.addShutdownHook`, `Runtime.halt`.
2.13.8 `Executors.callable(Runnable)`, `Executors.newThreadPerTaskExecutor(ThreadFactory)`, and the
       `unconfigurableExecutorService` wrapper.
2.13.9 `CompletableFuture.delayedExecutor` as a lightweight scheduler, and its shared `Delayer`
       daemon thread.
2.13.10 `Flow` (Java 9, JEP 266): `Publisher`, `Subscriber`, `Subscription`, `Processor`,
        `SubmissionPublisher`, `Flow.defaultBufferSize()` = 256. The JDK's reactive-streams
        interfaces, which almost nobody uses directly but which every reactive library implements.
        `[NUM]` `[RESEARCH]`
2.13.11 `SubmissionPublisher`'s own concurrency: it uses the common pool by default, buffers per
        subscriber, and drops or blocks per the `offer` overload used. `[RESEARCH]`
2.13.12 `java.util.concurrent.locks.ReadWriteLock` as an interface with exactly one JDK
        implementation, and the fact that `StampedLock.asReadWriteLock()` gives a second.
2.13.13 `Collections.synchronizedXxx`, `Collections.newSetFromMap`, and
        `Collections.unmodifiableXxx` — three wrappers with three different guarantees.
        `[X-REF 02]`
2.13.14 `Arrays.parallelSort`, `Arrays.parallelPrefix`, `Arrays.setAll`/`parallelSetAll` — the
        array-level parallel utilities that quietly use the common pool. `[X-REF 04]` `[TRAP]`
2.13.15 `Process`/`ProcessHandle.onExit()` returning a `CompletableFuture<Process>` as an example of
        the async surface leaking into unrelated APIs. `[RESEARCH]`
2.13.16 `Thread.sleep(0)`, `Thread.sleep(1)` and the timer-resolution folklore; on Linux the
        granularity is the scheduler tick unless high-resolution timers are used. `[TRAP]`
        `[NUM]`

*(16 leaves)*

## §2.14 Concurrency beyond one JVM

2.14.1 Everything in this file assumes one address space. Across JVMs, shared memory is replaced by
       a database, a broker or a coordination service, and every primitive has a distributed
       analogue with worse guarantees. `[X-REF 14]` `[X-REF 18]`
2.14.2 The mapping table: `synchronized` → a distributed lock (Redis/ZooKeeper/etcd);
       `AtomicLong` → a database sequence or `INCR`; `CountDownLatch` → a barrier in ZooKeeper;
       CAS → an optimistic-locking version column; `volatile` → a consistent read.
       `[X-REF 09]` `[X-REF 15]`
2.14.3 Why a distributed lock is never as strong as a monitor: no ownership guarantee across a GC
       pause, so a fencing token is required. State the Redlock debate honestly. `[RESEARCH]`
       `[TRAP]`
2.14.4 Optimistic locking in JPA (`@Version`) as the CAS of the persistence layer, and pessimistic
       locking as the `synchronized` of it. `[X-REF 08]`
2.14.5 Idempotency keys as the distributed answer to "exactly once". `[X-REF 12]` `[X-REF 14]`
2.14.6 Leader election as the distributed answer to "single writer". `[X-REF 18]`
2.14.7 The scheduled-job duplication problem across replicas, and the three fixes (leader election,
       a database lock with a lease, ShedLock). `[RESEARCH]`
2.14.8 Ordering across a partition boundary is not free either — the Kafka per-key ordering model
       is the same "confine state to one owner" idea. `[X-REF 14]`

*(8 leaves)*

## §2.15 Version delta, Java 5 → 25

2.15.1 Java 5: `java.util.concurrent` (JSR-166), the new JMM (JSR-133), `Executor`,
       `ConcurrentHashMap` (segmented), atomics, locks, `CountDownLatch`, `CyclicBarrier`,
       `Semaphore`, `Exchanger`, `BlockingQueue`.
2.15.2 Java 6: `ConcurrentSkipListMap/Set`, `Deque`/`BlockingDeque`, `AbstractQueuedLongSynchronizer`,
       biased locking on by default.
2.15.3 Java 7: fork/join, `Phaser`, `LinkedTransferQueue`, `ThreadLocalRandom`,
       `ConcurrentLinkedDeque`.
2.15.4 Java 8: `CompletableFuture`, `StampedLock`, `LongAdder`/`Striped64`, the re-written
       `ConcurrentHashMap` (per-bin locking, treeification, `mappingCount`), parallel streams,
       `Arrays.parallelSort`, `ForkJoinPool.commonPool`.
2.15.5 Java 9: `VarHandle` (JEP 193), `Flow` (JEP 266), `Thread.onSpinWait`,
       `CompletableFuture` timeouts and `copy`/`minimalCompletionStage`, the new `ForkJoinPool`
       constructor, `ProcessHandle.onExit`, removal of the executor `finalize`.
2.15.6 Java 10–14: cgroup-aware `availableProcessors` (10), `ThreadMXBean` refinements,
       `-XX:+UseBiasedLocking` deprecated (15).
2.15.7 Java 15 (JEP 374): biased locking deprecated and disabled by default. Why it was removed:
       revocation safepoints and code complexity. `[RESEARCH]` `[VERSION-TRAP]`
2.15.8 Java 16–18: `ThreadGroup` degradations, `Thread.suspend/resume` deprecated for removal,
       vector-API-adjacent memory ordering work.
2.15.9 Java 19: virtual threads preview (JEP 425), structured concurrency incubator (JEP 428),
       `Future.state/resultNow/exceptionNow`, `ExecutorService extends AutoCloseable`,
       `Thread.threadId()`, `Duration` overloads.
2.15.10 Java 20: `Thread.stop/suspend/resume` removed (throw `UnsupportedOperationException`);
        structured concurrency and scoped values re-preview.
2.15.11 Java 21 (LTS): virtual threads **final** (JEP 444), sequenced collections, structured
        concurrency preview (453), scoped values preview (446), generational ZGC.
2.15.12 Java 22–23: structured concurrency re-preview (462/480), scoped values re-preview
        (464/481), `Unsafe` memory-access methods deprecated for removal (JEP 471).
2.15.13 Java 24: **JEP 491 — `synchronized` no longer pins**; `-Djdk.tracePinnedThreads` removed;
        `jdk.VirtualThreadPinned` broadened; JEP 487 removes `ScopedValue.runWhere`/`callWhere`;
        JEP 498 warns on `Unsafe` memory access; JEP 450 compact object headers (experimental).
        `[VERSION-TRAP]` `[RESEARCH]`
2.15.14 Java 25 (LTS): **scoped values final (JEP 506)**; structured concurrency re-previewed with
        the `Joiner` API (JEP 505); compact object headers on by default (JEP 519);
        `StableValue` preview (JEP 502). `[VERSION-TRAP]` `[RESEARCH]`
2.15.15 The "what to say in an interview about versions" rule: state the Java 21 behaviour, then
        name the Java 24/25 change. Getting the direction of JEP 491 backwards is a visible error.
        `[TRAP]`
2.15.16 The deprecation graveyard as a table: `Thread.stop`, `suspend`, `resume`,
        `countStackFrames`, `destroy`, `ThreadGroup` management, biased locking, `Timer`,
        `finalize`-based pool shutdown, `sun.misc.Unsafe` memory access, `AtomicXxxFieldUpdater`
        (soft-deprecated in favour of `VarHandle`).

*(16 leaves)*

---

**PART 2 total: 8+14+14+18+10+14+12+14+14+16+10+14+16+8+16 = 198 leaves**

---

# PART 3 — UNDER THE HOOD

## §3.1 The object header and the mark word

3.1.1 HotSpot object layout on 64-bit: mark word (8 B) + klass pointer (4 B compressed / 8 B
      uncompressed) + fields + padding to an 8-byte boundary. Header is 12 B with compressed oops,
      16 B without. `[NUM]` `[RESEARCH]`
3.1.2 The mark word is **multiplexed**: the same 64 bits hold, depending on the low tag bits, the
      identity hash + age + tag, a pointer to a stack-allocated `BasicLock`, a pointer to an
      `ObjectMonitor`, or a forwarding pointer during GC. `[X-REF 06]` `[PROVE]`
3.1.3 The tag bit encoding: `01` = unlocked (neutral) or biased-with-null-owner, `00` =
      lightweight/stack-locked, `10` = inflated (monitor), `11` = marked for GC / forwarded.
      `[NUM]` `[SOURCE]` `[RESEARCH]`
3.1.4 Identity hash storage: `System.identityHashCode` is computed lazily and **stored in the mark
      word**, which is why computing it forces a state change and can force inflation. `[PROVE]`
      `[TRAP]`
3.1.5 The consequence: calling `hashCode()` on an object you also lock can change its locking
      performance. This is a real, measurable interaction. `[TRAP]` `[NUM]`
3.1.6 **JEP 450 / 519 — compact object headers**: header shrinks from 96–128 bits to 64 bits by
      folding the compressed klass pointer into the mark word. Experimental in Java 24, on by
      default in Java 25. Effect: 10–20 % heap reduction on typical workloads, and a *smaller*
      space for locking bits. `[NUM]` `[RESEARCH]` `[VERSION-TRAP]` `[X-REF 06]`
3.1.7 Inspecting the header for real: JOL (`java.openjdk.jol`) `ClassLayout.parseInstance(o).toPrintable()`
      before/after `synchronized`, showing the tag bits change. `[BUILD]` `[DUMP]` `[RESEARCH]`
3.1.8 Field layout and alignment: HotSpot reorders fields by size class (longs/doubles, ints,
      shorts, bytes, oops) to minimise padding, which is why two adjacent source fields may not be
      adjacent in memory — and why manual padding for false sharing does not work reliably.
      `[NUM]` `[TRAP]`

*(8 leaves)*

## §3.2 Monitor implementation: thin locks, inflation, `ObjectMonitor`

3.2.1 The three locking states in current HotSpot: **unlocked**, **lightweight/stack-locked**, and
      **inflated (monitor)**. Biased locking was a fourth and is gone. `[RESEARCH]`
3.2.2 Lightweight lock acquisition: the thread CASes the object's mark word from `01` (neutral) to
      `00` with a pointer to a `BasicObjectLock`/`BasicLock` in its own frame, saving the previous
      mark word there as the **displaced header**. `[SOURCE]` `[PROVE]` `[RESEARCH]`
3.2.3 Recursive lightweight locking: a nested acquisition stores a **zero** displaced header,
      which is how the hold count is represented without a counter. `[PROVE]` `[RESEARCH]`
3.2.4 Lightweight unlock: CAS the displaced header back into the mark word. If the CAS fails, the
      lock was inflated while held, and the slow path takes over. `[PROVE]`
3.2.5 **Inflation** happens when: another thread contends the stack lock, `wait()` is called
      (a wait set is needed), `hashCode` must be stored, or a JVMTI/monitor-inspection operation
      demands a real monitor. `[RESEARCH]` `[SOURCE]`
3.2.6 Inflation mechanics: allocate an `ObjectMonitor`, publish it into the mark word with tag `10`.
      The monitor is a native (C++) structure, not a Java object. `[SOURCE]`
3.2.7 `ObjectMonitor` fields worth naming: `_owner`, `_recursions`, `_EntryList`, `_cxq` (the
      contention queue), `_WaitSet`, `_succ` (the heir-presumptive), `_object` back-pointer.
      `[SOURCE]` `[RESEARCH]`
3.2.8 The two-queue design: arriving contenders are pushed onto `_cxq` (a lock-free LIFO push);
      on release the owner moves `_cxq` onto `_EntryList` and unparks a successor. This is why
      monitor wakeup order is **unspecified and unfair**. `[PROVE]` `[RESEARCH]`
3.2.9 `_succ` and the "responsible thread" mechanism: designating an heir avoids a stampede of
      wakeups, at the cost of possible barging. `[RESEARCH]`
3.2.10 `Object.wait` mechanics inside the monitor: the thread is moved from owning to `_WaitSet`,
       `_recursions` is saved and restored, and on notify it is moved to `_EntryList` — which is
       precisely why a notified thread is `BLOCKED`, not `RUNNABLE`. `[PROVE]` `[SOURCE]`
3.2.11 **Adaptive spinning**: before parking, a contender spins for a duration derived from whether
       spinning recently succeeded on this monitor. Spin-then-block is the whole strategy;
       `-XX:+UseSpinWait`-family flags and `-XX:-UseHeavyMonitors` (diagnostic) let you turn it
       off to measure. `[RESEARCH]` `[NUM]`
3.2.12 Deflation: idle monitors are reclaimed asynchronously (the monitor deflation thread, since
       JDK 15+, controlled by `-XX:MonitorDeflationMax`, `-XX:GuaranteedAsyncDeflationInterval`,
       `AsyncDeflationInterval`, `MonitorUsedDeflationThreshold`). Before that it happened at
       safepoints. `[RESEARCH]` `[NUM]` `[VERSION-TRAP]`
3.2.13 The monitor-table redesign (`ObjectMonitorTable`) used by Lilliput/compact headers: the
       monitor pointer no longer fits in a compact mark word, so a side table maps object → monitor.
       `[RESEARCH]` `[VERSION-TRAP]`
3.2.14 **Biased locking, and why it died**: it optimised the uncontended-repeatedly-by-one-thread
       case by stamping the owner's thread id in the mark word, so re-entry cost a compare, not a
       CAS. Revoking a bias required a **safepoint**, bulk revocation per class was a heuristic
       pile, and the whole thing was invasive. JEP 374 disabled it in Java 15 and it was removed
       later. Modern CAS is cheap enough that the win vanished. `[PROVE]` `[RESEARCH]`
       `[VERSION-TRAP]`
3.2.15 **Trap:** blog posts and interview answers that describe "biased → thin → fat lock
       escalation" describe a JVM you are not running. State the modern two-state model. `[TRAP]`
3.2.16 What `monitorenter`/`monitorexit` compile to at the machine level: an inline fast-path CAS
       emitted by C1/C2 with a runtime call on failure. `[ASM]`
3.2.17 The interaction with safepoints: a thread blocked on a monitor is *at* a safepoint-safe
       state, which is why a deadlocked application still lets GC run — and why the deadlock does
       not hang the JVM, only the threads. `[PROVE]` `[X-REF 06]`
3.2.18 JEP 491's change in these terms: the monitor's owner becomes the virtual thread's identity
       rather than the carrier's, and blocked-on-monitor becomes an unmount point. `[RESEARCH]`
       `[VERSION-TRAP]`

*(18 leaves)*

## §3.3 JIT optimisations that touch locks and memory

3.3.1 **Lock elision** via escape analysis: if the JIT proves the lock object cannot escape the
      compilation scope, `monitorenter`/`monitorexit` are removed entirely. The
      `StringBuffer`-in-a-method example. `[PROVE]` `[X-REF 06]`
3.3.2 **Lock coarsening**: adjacent synchronized blocks on the same object are merged into one, so
      "narrow your critical sections" can be undone by the compiler. `[PROVE]` `[TRAP]`
3.3.3 Scalar replacement and stack allocation as the escape-analysis siblings, and
      `-XX:+PrintEscapeAnalysis` / `-XX:-DoEscapeAnalysis` to observe them. `[X-REF 06]`
3.3.4 Why elision does not make your program correct: it only fires when the object provably does
      not escape, which is exactly when the lock was unnecessary. `[PROVE]`
3.3.5 Hoisting a non-volatile field read out of a loop — the exact transformation that makes the
      missing-`volatile` stop flag spin forever. Show the C2 output. `[ASM]` `[PROVE]`
3.3.6 What `volatile` compiles to per architecture: x86 volatile read = plain `mov`, volatile write
      = `mov` + `lock addl $0,(%rsp)` (or `xchg`); AArch64 read = `ldar`, write = `stlr`. Read the
      instructions. `[ASM]` `[NUM]` `[PROVE]`
3.3.7 The barrier taxonomy in HotSpot's IR: `OrderAccess::loadload`, `storestore`, `loadstore`,
      `storeload`, `acquire`, `release`, `fence`, and which map to no-ops on x86-TSO.
      `[SOURCE]` `[PROVE]`
3.3.8 x86-TSO formally: stores are buffered, so only StoreLoad can be reordered; loads are not
      reordered with loads. That single fact explains why x86 hides most JMM bugs. `[PROVE]`
3.3.9 AArch64's weaker model: StoreStore and LoadLoad reordering are both permitted, so the same
      code fails on Graviton/Apple silicon. Give the concrete failing example. `[PROVE]`
      `[RESEARCH]`
3.3.10 Reading the generated code: `-XX:+UnlockDiagnosticVMOptions -XX:+PrintAssembly` with hsdis,
       or JITWatch. `[X-REF 06]` `[BUILD]`
3.3.11 Deoptimisation and uncommon traps as they affect concurrency benchmarks: a branch never
       taken is compiled away and taken later causes a deopt storm. `[X-REF 06]`
3.3.12 Constant folding of `final` fields and `@Stable`, and why a reflectively-modified `final`
       may never be observed. `[PROVE]` `[X-REF 03]`

*(12 leaves)*

## §3.4 Safepoints as they touch concurrency

3.4.1 What a safepoint is: a point at which every Java thread's state is exactly known (oop maps
      valid), required for GC, deoptimisation, stack walking, and class redefinition.
      `[X-REF 06]`
3.4.2 How threads are brought to a safepoint: a poll page is protected; every safepoint poll
      instruction faults and traps. Since JDK 10 the poll is thread-local, which enables
      *handshakes*. `[RESEARCH]`
3.4.3 **Time-to-safepoint (TTSP)** as a distinct metric from pause duration, and the classic causes
      of long TTSP: a counted loop with no poll (int-indexed loop over a huge array), a long
      `arraycopy`, a page fault storm. `[NUM]` `[RESEARCH]`
3.4.4 The **guaranteed safepoint**: `-XX:GuaranteedSafepointInterval`, default 1000 ms, brings the
      VM to a safepoint even with no VM operation queued. Disable only with
      `-XX:+UnlockDiagnosticVMOptions`. `[NUM]` `[RESEARCH]`
3.4.5 Safepoint-triggering operations relevant here: thread dumps, `getStackTrace`,
      `getAllStackTraces`, deadlock detection, biased-lock revocation (historically), monitor
      deflation (historically), and JFR stack sampling. `[RESEARCH]`
3.4.6 Handshakes (JEP 312) as the per-thread alternative that avoids a global stop, and which
      operations moved to them. `[RESEARCH]`
3.4.7 Why this matters for a concurrency answer: a thread dump is not free, `getStackTrace` in a
      loop is a self-inflicted pause, and "the app froze for 300 ms with no GC" is usually a
      safepoint story. `[DUMP]` `[X-REF 06]`
3.4.8 Safepoint logging: `-Xlog:safepoint*=info` and reading the `Reaching safepoint` /
      `At safepoint` / `Leaving safepoint` triple. `[DUMP]` `[RESEARCH]`
3.4.9 Safepoint bias in profilers: `getStackTrace`-based samplers only sample at safepoints, so
      they systematically mis-attribute; `AsyncGetCallTrace`/async-profiler and
      `-XX:+DebugNonSafepoints` fix it. `[RESEARCH]` `[X-REF 06]`
3.4.10 Virtual threads and safepoints: a mounted virtual thread reaches safepoints through its
       carrier; an unmounted one is a heap object and is not a safepoint participant at all.
       `[PROVE]`

*(10 leaves)*

## §3.5 `AbstractQueuedSynchronizer`

3.5.1 What AQS is: the framework class (Doug Lea, "The java.util.concurrent Synchronizer
      Framework", 2004) that supplies a `volatile int state`, an atomic protocol over it, and a
      FIFO wait queue, so every synchronizer reduces to "define what `state` means".
      `[SOURCE]` `[RESEARCH]`
3.5.2 The five template methods a subclass overrides: `tryAcquire`, `tryRelease`,
      `tryAcquireShared`, `tryReleaseShared`, `isHeldExclusively`. Everything else is inherited.
      `[SOURCE]`
3.5.3 The state accessors: `getState`, `setState`, `compareAndSetState` — and the rule that all
      state manipulation must go through them. `[SOURCE]`
3.5.4 What `state` means per synchronizer, as a table: `ReentrantLock` = hold count;
      `Semaphore` = permits; `CountDownLatch` = remaining count; `ReentrantReadWriteLock` =
      16 high bits readers / 16 low bits writers (max 65 535 each);
      `ThreadPoolExecutor.Worker` = 0/1 interrupt-safety flag; `FutureTask` uses its own state
      machine, not AQS. `[NUM]` `[SOURCE]` `[PROVE]`
3.5.5 The **CLH queue variant**: a doubly-linked (`prev`/`next`) queue of `Node`s with a `status`
      field, derived from Craig–Landin–Hagersten spinlock queues but adapted for blocking by adding
      explicit successor links and `LockSupport.unpark` signalling. `[SOURCE]` `[RESEARCH]`
3.5.6 Enqueue: CAS the new node as the new `tail`. Dequeue: set `head` to the node whose thread
      acquired, and null out its thread. `head` is a dummy node. `[PROVE]` `[SOURCE]`
3.5.7 Why `prev` is authoritative and `next` is a shortcut: `prev` is set before the CAS on tail,
      so it is always valid; `next` is set after, so a traversal must sometimes walk **backwards
      from tail** to find a successor. This is the single most surprising line of AQS.
      `[PROVE]` `[SOURCE]` `[TRAP]`
3.5.8 Node status values. In the classic (JDK 8–14) encoding: `CANCELLED = 1`, `SIGNAL = -1`,
      `CONDITION = -2`, `PROPAGATE = -3`, `0` = default. `[NUM]` `[SOURCE]`
3.5.9 **`[VERSION-TRAP]`** JDK 14+ (Doug Lea's 2019 rewrite, present in Java 21) replaced the
      `waitStatus` int with bit flags `WAITING = 1`, `CANCELLED = 0x80000000`, `COND = 2`, removed
      the separate `Node` subclasses in favour of `ExclusiveNode`/`SharedNode`/`ConditionNode`, and
      collapsed `acquireQueued`/`addWaiter` into a single `acquire` method. Most blog explanations
      describe the JDK 8 code. State which you are reading. `[RESEARCH]` `[SOURCE]`
3.5.10 The acquire loop, walked line by line from JDK 21 source: try acquire → if head's successor,
       retry → else enqueue → set predecessor's status to WAITING → `LockSupport.park` → on wake,
       re-check. `[SOURCE]` `[PROVE]`
3.5.11 The release path: `tryRelease` → if head exists and has a waiting successor,
       `LockSupport.unpark` it. Only one unpark per release in exclusive mode. `[SOURCE]`
3.5.12 Shared mode and **propagation**: `tryAcquireShared` returns a remaining-permits count, and a
       successful shared acquire propagates the signal to the next node so multiple readers wake in
       a cascade. `[PROVE]` `[SOURCE]`
3.5.13 Cancellation: a timed-out or interrupted node is marked cancelled and unlinked, with the
       skip-cancelled-predecessors walk. Cancellation is the source of most of AQS's complexity.
       `[PROVE]` `[SOURCE]`
3.5.14 `ConditionObject`: a **second**, singly-linked queue (`firstWaiter`/`lastWaiter`) of
       `ConditionNode`s. `await` fully releases the state (saving it), enqueues on the condition
       queue, parks; `signal` **transfers** the node from the condition queue to the sync queue —
       it does not wake the thread directly. `[PROVE]` `[SOURCE]`
3.5.15 Full release on `await` and its consequence: a reentrant lock held twice is released twice
       and re-acquired twice. `[PROVE]`
3.5.16 Fair versus unfair `tryAcquire` in `ReentrantLock`: the fair variant adds
       `hasQueuedPredecessors()` before the CAS; that one method call is the entire difference.
       `[SOURCE]` `[PROVE]`
3.5.17 `NonfairSync.lock` in older JDKs performed an immediate `compareAndSetState(0,1)` barge
       before even calling `tryAcquire`. `[SOURCE]` `[RESEARCH]`
3.5.18 `AbstractQueuedLongSynchronizer` as the 64-bit-state twin, used where 32 bits of state are
       not enough. `[RESEARCH]`
3.5.19 `AbstractOwnableSynchronizer` and `setExclusiveOwnerThread`, which is what makes
       `isHeldByCurrentThread` and the "ownable synchronizer" section of a thread dump possible.
       `[DUMP]` `[SOURCE]`
3.5.20 How each JDK synchronizer maps onto AQS, as a table: `ReentrantLock.Sync`,
       `ReentrantReadWriteLock.Sync` (+`HoldCounter`/`ThreadLocalHoldCounter`),
       `Semaphore.Sync`, `CountDownLatch.Sync`, `ThreadPoolExecutor.Worker`,
       `CompletableFuture` (no — it uses its own Treiber stack of `Completion`s),
       `StampedLock` (no — its own sequence-lock design), `Phaser` (no), `Exchanger` (no).
       `[RESEARCH]`
3.5.21 Why `StampedLock` is not AQS-based: it uses a 64-bit sequence with 7 low bits of reader
       count plus an overflow word, and a stamp that encodes the sequence — reentrancy and
       ownership are sacrificed for the optimistic-read mode. `[PROVE]` `[SOURCE]`
3.5.22 The AQS-based synchronizer you should be able to write on a whiteboard: a non-reentrant
       mutex in about twenty lines. `[BUILD]`

*(22 leaves)*

## §3.6 `LockSupport`, `park`/`unpark`, and the OS layer

3.6.1 The permit model formally: each thread has at most **one** permit; `unpark` makes it
      available, `park` consumes it or blocks. Permits do not accumulate — two `unpark`s then two
      `park`s blocks on the second. `[PROVE]` `[SOURCE]` `[TRAP]`
3.6.2 Why the permit exists: it removes the lost-wakeup race that plagues `wait`/`notify`. `unpark`
      before `park` is safe. `[PROVE]`
3.6.3 `park` may return **spuriously**, on interrupt (without clearing the flag), and on a
      `parkNanos` timeout — three reasons, all requiring the caller to re-check a condition.
      `[SOURCE]` `[TRAP]`
3.6.4 The native implementation on Linux: a per-thread `Parker` with a mutex, a condition variable
      and a `_counter`; `park` is `pthread_cond_wait`/`pthread_cond_timedwait` and `unpark` is
      `pthread_cond_signal`. Since JDK 9+ this is `PlatformParker`/`os::PlatformEvent`.
      `[SOURCE]` `[RESEARCH]`
3.6.5 The futex underneath: an uncontended park/unpark can avoid a syscall entirely; a contended
      one costs a `FUTEX_WAIT`/`FUTEX_WAKE` pair and two context switches. `[NUM]` `[X-REF 11]`
3.6.6 Measured cost: a park/unpark round trip is on the order of microseconds, versus tens of
      nanoseconds for a CAS. This ratio is the entire argument for spinning before parking.
      `[NUM]` `[PROVE]`
3.6.7 `park(Object blocker)` and `getBlocker`: the blocker object is stored in `Thread.parkBlocker`
      via a `VarHandle`, and is what makes a thread dump say "parking to wait for
      <0x00000000d5f5b1a8> (a java.util.concurrent.locks.ReentrantLock$NonfairSync)". `[DUMP]`
      `[SOURCE]`
3.6.8 `parkNanos` versus `parkUntil`: relative (nanoTime-based, monotonic) versus absolute
      (epoch-millis, NTP-sensitive). Use the relative form for timeouts. `[TRAP]`
3.6.9 Virtual-thread `park`: `LockSupport.park` on a virtual thread does **not** park an OS thread
      — it calls `Continuation.yield`. Same API, entirely different mechanism. This is the hinge on
      which all of Loom turns. `[PROVE]` `[SOURCE]`
3.6.10 The `Thread.interrupt` implementation: set the flag, then `unpark` the thread and, if it is
       blocked in a monitor wait or an interruptible channel, signal that too. `[SOURCE]`

*(10 leaves)*

## §3.7 The Java Memory Model, formally

3.7.1 The JMM as a *constraint on executions*, not a description of hardware: an implementation is
      legal if every execution it can produce is a legal execution of the model. `[SOURCE]`
3.7.2 Working through the well-formedness constraints of JLS 17.4.7 on a concrete two-thread
      program, showing which candidate executions are excluded. `[PROVE]` `[SOURCE]`
3.7.3 The happens-before consistency rule: a read `r` of `v` may see a write `w` if `w` does not
      happen-after `r`, and there is no intervening write `w'` with `w hb w' hb r`. Two clauses,
      both essential. `[PROVE]` `[SOURCE]`
3.7.4 Why happens-before consistency alone is not enough — it permits out-of-thin-air — and how
      the committed-sets construction of 17.4.8 excludes it. Walk the commit sequence. `[PROVE]`
      `[SOURCE]`
3.7.5 The DRF-SC theorem argument sketched: if every execution is data-race-free, then every
      execution is equivalent to a sequentially consistent one, so interleaving reasoning is sound.
      `[PROVE]`
3.7.6 Why the theorem is conditional and what "correctly synchronized" costs you: one racy field
      anywhere and the guarantee is global, not local — you lose SC reasoning for the whole
      program in principle, though in practice the damage is local. `[PROVE]` `[TRAP]`
3.7.7 Litmus tests you must be able to reason about: store buffering (Dekker), message passing
      (the publication idiom), independent reads of independent writes (IRIW), load buffering,
      and coherence (CoRR). For each: the outcome hardware permits, the outcome the JMM permits,
      and the fix. `[PROVE]` `[RESEARCH]`
3.7.8 The IRIW case and why `volatile` (sequential consistency) is stronger than acquire/release:
      acquire/release does not give a total order over all volatiles, sequential consistency does.
      `[PROVE]` `[RESEARCH]`
3.7.9 The synchronization order as a **total order over synchronization actions**, and its
      relationship to program order and happens-before. `[SOURCE]`
3.7.10 Final-field semantics formalised: the freeze action, the `hb` and `mc` (memory chain)
       relations, and the dereference chain. Walk the definition on the classic `FinalFieldExample`.
       `[PROVE]` `[SOURCE]`
3.7.11 Why final-field semantics are *not* implemented with a barrier on the read side (except on
       Alpha): the implementation is a `StoreStore` at the end of the constructor, and correctness
       relies on data dependency. `[PROVE]` `[ASM]` `[RESEARCH]`
3.7.12 The JSR-133 Cookbook barrier table (Doug Lea): for each pair of adjacent operations, which
       barrier the compiler must insert. This is the practical translation of the model.
       `[SOURCE]` `[RESEARCH]`
3.7.13 The `VarHandle` access modes mapped onto the C++11/hardware model: plain ≈ relaxed-without
       atomicity, opaque ≈ relaxed, acquire/release ≈ acq/rel, volatile ≈ seq_cst.
       `[PROVE]` `[RESEARCH]`
3.7.14 The known formal gaps: the causality rules are not compositional, common compiler
       optimisations are technically illegal under them, and there is an ongoing effort to replace
       chapter 17. Interview-safe framing. `[RESEARCH]`
3.7.15 What "correctly synchronized" means for a library author versus an application author, and
       why `java.util.concurrent` internals legitimately use plain/opaque accesses that application
       code should not. `[TRAP]`

*(15 leaves)*

## §3.8 `ConcurrentHashMap` internals

3.8.1 The Java 7 design and why it was replaced: `Segment extends ReentrantLock`, `DEFAULT_CONCURRENCY_LEVEL
      = 16`, so exactly 16 writers maximum and a two-level indirection on every access.
      `[NUM]` `[X-REF 02]`
3.8.2 The Java 8+ design in one sentence: a single `Node[] table`, CAS to install the first node of
      an empty bin, `synchronized` on the bin's head node for everything else. Concurrency scales
      with table size. `[SOURCE]`
3.8.3 The named constants: `MAXIMUM_CAPACITY = 1 << 30`, `DEFAULT_CAPACITY = 16`,
      `LOAD_FACTOR = 0.75f` (hard-coded; the constructor argument only affects initial sizing),
      `TREEIFY_THRESHOLD = 8`, `UNTREEIFY_THRESHOLD = 6`, `MIN_TREEIFY_CAPACITY = 64`,
      `MIN_TRANSFER_STRIDE = 16`, `RESIZE_STAMP_BITS = 16`. `[NUM]` `[SOURCE]` `[X-REF 02]`
3.8.4 The special hash values: `MOVED = -1` (a `ForwardingNode`), `TREEBIN = -2`,
      `RESERVED = -3` (placeholder during `computeIfAbsent`), `HASH_BITS = 0x7fffffff`.
      `[NUM]` `[SOURCE]`
3.8.5 `spread(h) = (h ^ (h >>> 16)) & HASH_BITS`: the XOR-fold mixes high bits down (same as
      `HashMap`) and the mask forces the sign bit off so user hashes never collide with the
      control values. `[PROVE]` `[SOURCE]` `[X-REF 02]`
3.8.6 `sizeCtl` — one field, four meanings: `0` = default-size table not yet created, positive =
      the next resize threshold (or the requested initial capacity before creation), `-1` = a
      thread is initialising the table, and negative-other = a resize stamp in the high bits plus
      the number of resizing threads + 1 in the low bits. `[PROVE]` `[SOURCE]` `[RESEARCH]`
3.8.7 `initTable()`: spin on `sizeCtl`, CAS it to `-1` to win the initialisation race, others
      `Thread.yield()`. Lazy initialisation on first write. `[SOURCE]`
3.8.8 `putVal` walked step by step: compute spread hash → if bin empty, `casTabAt` a new `Node` →
      if `f.hash == MOVED`, `helpTransfer` → else `synchronized (f)` and walk the list or the tree
      → then `treeifyBin` if the bin count reached 8 → then `addCount`. `[SOURCE]` `[PROVE]`
3.8.9 `get` is entirely lock-free: `Node.val` and `Node.next` are `volatile`, and `tabAt` is a
      `getAcquire`/`getVolatile` array read. A reader never blocks, even during a resize.
      `[SOURCE]` `[PROVE]`
3.8.10 **Resizing is concurrent and cooperative.** `transfer` splits the table into stride-sized
       chunks (`MIN_TRANSFER_STRIDE = 16`, computed from `NCPU`), each helping thread claims a
       range via `transferIndex`, and a bin that has been moved is replaced by a `ForwardingNode`
       so readers follow `nextTable` and writers call `helpTransfer`. `[PROVE]` `[SOURCE]`
       `[RESEARCH]`
3.8.11 The lo/hi split during transfer: because capacity doubles, each entry either stays at index
       `i` or moves to `i + oldCap`, decided by `(hash & oldCap) == 0`. Same trick as `HashMap`.
       `[PROVE]` `[X-REF 02]`
3.8.12 `resizeStamp(n)` and how the stamp in `sizeCtl`'s high bits prevents two different resizes
       from being confused. `[SOURCE]`
3.8.13 Treeification: a bin of ≥ 8 nodes becomes a `TreeBin` **only if** the table is ≥ 64 entries;
       otherwise the table resizes instead. `TreeBin` is not a bare red-black tree — it holds a
       `lockState` supporting a read-write lock so readers can traverse the linked-list view while
       a writer rebalances. `[PROVE]` `[SOURCE]` `[X-REF 02]`
3.8.14 `TreeNode` keeps `prev`/`next` links so the bin is simultaneously a list and a tree, which
       is what makes lock-free reads across a rebalance possible. `[PROVE]` `[SOURCE]`
3.8.15 Untreeify at `UNTREEIFY_THRESHOLD = 6` during resize, and the 8/6 hysteresis gap.
       `[NUM]` `[PROVE]`
3.8.16 The comparison-order rules inside a `TreeBin` for non-`Comparable` keys:
       hash, then `Comparable` if the class is, then `tieBreakOrder` on
       `System.identityHashCode`. `[SOURCE]` `[X-REF 02]`
3.8.17 **Counting**: `baseCount` plus a `CounterCell[]`, the same `Striped64` design as `LongAdder`.
       `addCount` CASes `baseCount`; on failure it CASes a random cell; on failure again it calls
       `fullAddCount`, which may grow the cell array. `[SOURCE]` `[PROVE]` `[RESEARCH]`
3.8.18 Therefore `size()` sums `baseCount` + cells and is inherently approximate; `mappingCount()`
       is the `long` version added because a `CHM` can exceed `Integer.MAX_VALUE` entries.
       `[PROVE]` `[NUM]`
3.8.19 `computeIfAbsent`'s `ReservationNode`: a placeholder with hash `RESERVED` is installed and
       locked while the mapping function runs, which is exactly why recursion on the same bin
       deadlocks and on the same key throws `IllegalStateException("Recursive update")`.
       `[SOURCE]` `[PROVE]` `[TRAP]`
3.8.20 The traverser: `Traverser`/`BaseIterator` handles forwarding nodes and tree bins with a
       stack of table references, which is the mechanism behind "weakly consistent" and
       "each element traversed at most once". `[SOURCE]` `[PROVE]`
3.8.21 The bulk operations' internals: `ForEachMappingTask` and friends are `CountedCompleter`s
       submitted to the common pool, split until the estimated element count falls below
       `parallelismThreshold`. `[SOURCE]` `[RESEARCH]`
3.8.22 `KeySetView` and `newKeySet` implemented as a map with a shared dummy value.
3.8.23 Memory footprint: a `Node` is header (12/16 B) + `hash` (4) + `key` ref (4) + `val` ref (4)
       + `next` ref (4) ≈ 32 B, plus the table array slot (4 B) — so an entry costs ~36–40 B before
       the key and value objects themselves. `[NUM]` `[PROVE]`
3.8.24 What `ConcurrentHashMap` does *not* give you: a consistent snapshot, atomic `size`, atomic
       bulk operations, or ordering. `[TRAP]`

*(24 leaves)*

## §3.9 `Striped64`, `LongAdder`, and false sharing

3.9.1 `Striped64` as the shared base of `LongAdder`, `LongAccumulator`, `DoubleAdder`,
      `DoubleAccumulator` and `ConcurrentHashMap`'s counters. `[SOURCE]`
3.9.2 The structure: a `volatile long base`, a `volatile Cell[] cells`, and a `cellsBusy` spinlock
      int. Fast path is a CAS on `base`; on failure, a CAS on `cells[probe & (n-1)]`.
      `[SOURCE]` `[PROVE]`
3.9.3 The thread probe: `ThreadLocalRandom.getProbe()` gives each thread an index; on repeated
      collision `advanceProbe` **rehashes the thread** rather than growing the table — a
      cheaper fix than more memory. `[PROVE]` `[SOURCE]` `[RESEARCH]`
3.9.4 Growth policy: the cell array doubles on contention up to `NCPU` (rounded to a power of two),
      because more cells than cores cannot reduce contention. `[NUM]` `[PROVE]`
3.9.5 `@jdk.internal.vm.annotation.Contended` on `Cell`: the JVM pads the object so no two cells
      share a cache line. `[SOURCE]` `[RESEARCH]`
3.9.6 **False sharing** defined: two independent variables in the same 64-byte cache line, so a
      write to one invalidates the other's line on every other core. No correctness impact,
      order-of-magnitude performance impact. `[PROVE]` `[NUM]`
3.9.7 Cache-line size: 64 bytes on x86-64 and most AArch64; Apple M-series and some server parts
      use 128-byte sectors, which is why HotSpot pads with **128** bytes by default
      (`-XX:ContendedPaddingWidth`, default 128). `[NUM]` `[RESEARCH]`
3.9.8 `@Contended` is internal (`jdk.internal.vm.annotation`), requires
      `-XX:-RestrictContended` for application classes, and needs the module opened. Application
      code generally should not use it. `[TRAP]` `[RESEARCH]`
3.9.9 Manual padding does not reliably work because HotSpot reorders fields; the historical
      `long p1..p7` trick and why it is fragile. `[TRAP]` `[PROVE]`
3.9.10 Detecting false sharing: `perf c2c`, or a JMH experiment with and without padding showing
       the throughput cliff. `[NUM]` `[BUILD]` `[RESEARCH]`
3.9.11 The classic false-sharing example: two threads incrementing `a[0]` and `a[1]` of the same
       `long[]`, versus `a[0]` and `a[16]`. Show the measured ratio. `[BUILD]` `[NUM]`
3.9.12 `sum()` walked: `base` plus a loop over non-null cells, with no synchronization — hence
       "racy sum", and hence `sumThenReset`'s non-atomicity. `[SOURCE]` `[PROVE]`
3.9.13 Why `LongAdder` cannot implement `compareAndSet` or `getAndIncrement`: the value is
       distributed, so there is no single point at which to observe or swap it. `[PROVE]`
       `[TRAP]`
3.9.14 `LongAccumulator`'s identity and the requirement that the function be associative and
       side-effect-free, because the fold order across cells is unspecified. `[PROVE]`

*(14 leaves)*

## §3.10 Queue and executor internals

3.10.1 `ConcurrentLinkedQueue` = the **Michael–Scott** lock-free queue: `head`/`tail` are volatile,
       `tail` is allowed to lag by one node, and every operation helps advance it. `[PROVE]`
       `[SOURCE]` `[RESEARCH]`
3.10.2 The "self-link" trick for removed nodes (`p.next == p`) as the GC-friendly way to signal a
       stale node and force a restart from head. `[PROVE]` `[SOURCE]`
3.10.3 Why `size()` is O(n) and approximate: it walks the list, which may change under it.
       `[PROVE]`
3.10.4 Why the JDK's lock-free queues do not need hazard pointers or epoch reclamation: the GC is
       the memory reclamation scheme. This is a genuine advantage of Java over C++ here, and it is
       an excellent interview answer. `[PROVE]` `[RESEARCH]`
3.10.5 `LinkedTransferQueue` and the **dual queue / slack** design: nodes are either data or
       requests, and the queue holds whichever is in surplus. `SynchronousQueue` (Java 6+) is the
       same design with no storage. `[RESEARCH]` `[SOURCE]`
3.10.6 `SynchronousQueue`'s two implementations — `TransferStack` (unfair, LIFO) and
       `TransferQueue` (fair, FIFO) — selected by the constructor's `fair` flag. `[SOURCE]`
3.10.7 `ArrayBlockingQueue` internals: `items[]`, `takeIndex`, `putIndex`, `count`, one
       `ReentrantLock` and two `Condition`s. `put` signals `notEmpty`, `take` signals `notFull`.
       `[SOURCE]` `[BUILD]`
3.10.8 `LinkedBlockingQueue` internals: `putLock`/`takeLock`, `notFull`/`notEmpty`,
       `AtomicInteger count`, and the **cascading signal** in `signalNotEmpty`/`fullyLock` that
       keeps the two halves coordinated. `[SOURCE]` `[PROVE]`
3.10.9 The two-lock proof obligation: why `count` must be an `AtomicInteger` and why a
       put must signal not-empty only on the 0→1 transition. `[PROVE]`
3.10.10 `PriorityBlockingQueue` internals: a binary heap array, one lock, plus a `spinlock`
        (`allocationSpinLock`) used only for resizing so that a grow does not block takers.
        `[SOURCE]` `[X-REF 02]`
3.10.11 `DelayQueue` internals: a `PriorityQueue` plus a **leader thread** optimisation — only one
        waiter does a timed wait on the head's delay; the rest wait indefinitely. Avoids a
        thundering herd of timed waits. `[PROVE]` `[SOURCE]`
3.10.12 `ThreadPoolExecutor.ctl`: a single `AtomicInteger` packing the run state in the high 3 bits
        and the worker count in the low 29 bits, so `RUNNING = -1<<29`, `SHUTDOWN = 0`,
        `STOP = 1<<29`, `TIDYING = 2<<29`, `TERMINATED = 3<<29`, and
        `CAPACITY = (1<<29)-1 = 536 870 911`. `[NUM]` `[SOURCE]` `[PROVE]`
3.10.13 Why they are packed together: state and count must be read and updated atomically to make
        the submission algorithm's races correct. `[PROVE]`
3.10.14 The run-state transition graph and which method causes each edge (`shutdown`, `shutdownNow`,
        queue-and-pool-empty, `terminated()`). `[SOURCE]`
3.10.15 `execute()` walked line by line against the JDK 21 source, including the **double-check**
        after enqueueing (re-read `ctl`, remove the task if the pool shut down, add a worker if the
        pool became empty). Almost every explanation of the submission algorithm omits this.
        `[SOURCE]` `[PROVE]` `[TRAP]`
3.10.16 `Worker extends AbstractQueuedSynchronizer implements Runnable`: it is a non-reentrant lock
        whose only purpose is to mark "this worker is running a task" so that `shutdownNow` does
        not interrupt an idle worker mid-`poll`. `[PROVE]` `[SOURCE]`
3.10.17 `runWorker`/`getTask`: the loop, the `keepAliveTime` `poll` versus the blocking `take`, and
        how `allowCoreThreadTimeOut` picks between them. `[SOURCE]`
3.10.18 `processWorkerExit` and the completedTaskCount accounting; why a task that throws still
        replaces its worker.
3.10.19 `ScheduledThreadPoolExecutor.DelayedWorkQueue`: a hand-written binary heap with an
        index-in-heap field on each task (so `remove` is O(log n) not O(n)), plus the same leader
        optimisation as `DelayQueue`. `[SOURCE]` `[NUM]`
3.10.20 `ScheduledFutureTask.run()`: for a periodic task it calls `runAndReset`, re-computes the
        next time (`setNextRunTime`, adding the period for fixed-rate or the delay from *now* for
        fixed-delay), and re-enqueues — and skips all of that if the run threw. That is the
        mechanism behind "an exception cancels all future runs". `[SOURCE]` `[PROVE]`
3.10.21 `FutureTask` internals: a `volatile int state` machine (`NEW = 0`, `COMPLETING = 1`,
        `NORMAL = 2`, `EXCEPTIONAL = 3`, `CANCELLED = 4`, `INTERRUPTING = 5`, `INTERRUPTED = 6`)
        plus a Treiber stack of `WaitNode` waiters. `[NUM]` `[SOURCE]`
3.10.22 `CompletableFuture` internals: a `volatile Object result` (with `AltResult` boxing null and
        exceptions) and a **Treiber stack** of `Completion` nodes; completion pops and fires the
        stack, and `postComplete` unrolls recursion to avoid stack overflow on long chains.
        `[SOURCE]` `[PROVE]`
3.10.23 The `NIL` sentinel for a `null` result and `AltResult` for exceptions, which is why
        `CompletableFuture` can hold a null value but `Future.get` cannot distinguish it from
        "not done" without `isDone`. `[SOURCE]`
3.10.24 `CompletableFuture`'s stack-depth protection and the `ForkJoinPool.commonPool` /
        `ASYNC_POOL` selection when parallelism < 2 (a per-task `Thread`). `[SOURCE]`

*(24 leaves)*

## §3.11 `ForkJoinPool` and work stealing

3.11.1 The architecture: an array of `WorkQueue`s, indexed so that submission queues occupy even
       slots and worker queues odd slots. External submitters hash into a submission queue.
       `[SOURCE]` `[RESEARCH]`
3.11.2 `WorkQueue` fields: `array` (the circular task array), `base` (steal end, volatile), `top`
       (push/pop end), `phase`, `source`, `nsteals`. `[SOURCE]`
3.11.3 The deque protocol: the owner `push`es and `pop`s at `top` with no CAS in the common case
       (a plain store plus a release fence); a thief `poll`s at `base` with a CAS. Owner and thief
       only contend when the queue has one element. `[PROVE]` `[SOURCE]`
3.11.4 Why this is the classic Arora–Blumofe–Plaxton work-stealing deque, and the proof sketch that
       LIFO-local/FIFO-steal bounds the number of steals. `[PROVE]` `[RESEARCH]`
3.11.5 `ctl`: a single 64-bit field packing (from the high end) the active count `AC`, the total
       count `TC`, and the id/version of the top of the idle-worker Treiber stack. All pool state
       transitions are one CAS on `ctl`. `[NUM]` `[SOURCE]` `[PROVE]`
3.11.6 `signalWork` and worker activation: on push, if there is an idle worker, unpark it; the
       decision is a `ctl` read, not a queue scan. `[SOURCE]`
3.11.7 `scan`/`runWorker`: a worker with an empty queue scans other queues in a randomised order,
       and parks after a bounded number of failed scans (the "quiescing" path). `[SOURCE]`
3.11.8 `awaitWork`/`tryTerminate` and the quiescence detection that makes `awaitQuiescence` and
       `commonPool` shutdown-free operation possible. `[SOURCE]`
3.11.9 Compensation: `tryCompensate` spawns or releases a spare thread when a worker is about to
       block in `join`, bounded by `maximumPoolSize` (default `256 + parallelism` for the common
       pool) and controlled by `minimumRunnable` (default 1) and the `saturate` predicate.
       `[NUM]` `[SOURCE]` `[RESEARCH]`
3.11.10 `helpJoin`/`helpComplete`: rather than blocking, a joining worker tries to execute the task
        it is waiting for, or tasks that the stealer of that task is working on. This is the reason
        `fork(); compute(); join();` does not deadlock a fixed-size pool. `[PROVE]` `[SOURCE]`
3.11.11 `ManagedBlocker` walked: `isReleasable()` then `block()`, called in a loop by
        `managedBlock`, with the pool possibly activating a spare. Outside a FJ pool it degrades to
        a plain loop. `[SOURCE]` `[BUILD]`
3.11.12 `CountedCompleter`: completion-count-based joining with no blocking at all — `tryComplete`,
        `onCompletion`, `propagateCompletion`. The right base class for wide fan-out, and what the
        `ConcurrentHashMap` bulk ops and `java.util.stream` use. `[SOURCE]` `[X-REF 04]`
3.11.13 `common.maximumSpares` (default 256), `common.threadFactory`, `common.exceptionHandler`,
        `common.parallelism` as the four system properties, and the InnocuousForkJoinWorkerThread
        used for the common pool. `[NUM]` `[SOURCE]` `[RESEARCH]`
3.11.14 A real bug worth knowing: JDK-8330017 — the release count field in `ctl` could overflow at
        −32768 → +32767 and the pool would stop executing tasks entirely. It shipped in production
        JDKs and took down NSX deployments. Evidence that this code is genuinely hard. `[RESEARCH]`
3.11.15 JDK-8315740: common-pool starvation when tasks block, and the general lesson that the
        common pool must never see blocking work. `[RESEARCH]` `[TRAP]`
3.11.16 Why `ForkJoinPool` is the virtual-thread scheduler: FIFO mode plus work stealing plus cheap
        submission is exactly what a continuation dispatcher needs. `[PROVE]`

*(16 leaves)*

## §3.12 Virtual thread internals

3.12.1 `Continuation` (`jdk.internal.vm.Continuation`) as the primitive: a `ContinuationScope`,
       `run()`, static `yield(scope)`, `isDone`, and the `enter`/`enterSpecial` intrinsics.
       Virtual threads are one client of it; the class is internal and unsupported. `[SOURCE]`
       `[RESEARCH]`
3.12.2 What a delimited continuation is, and why "delimited" matters: yield unwinds only up to the
       scope's entry frame, not the whole stack. `[PROVE]`
3.12.3 `VirtualThread`'s fields: `scheduler`, `cont` (the `VThreadContinuation`), `runContinuation`
       (the `Runnable` submitted to the scheduler), `carrierThread`, and `state`. `[SOURCE]`
3.12.4 The internal state machine, distinct from `Thread.State`: `NEW`, `STARTED`, `RUNNING`,
       `PARKING`, `PARKED`, `PINNED`, `YIELDING`, `TERMINATED` (plus the `SUSPENDED` bit).
       Visible in `jcmd Thread.dump_to_file -format=json`. `[SOURCE]` `[DUMP]` `[RESEARCH]`
3.12.5 **Mounting**: `runContinuation` is executed by a carrier; `Continuation.run` copies the
       saved frames from the heap `StackChunk` back onto the carrier's stack and jumps to the
       resume point. `[PROVE]` `[RESEARCH]`
3.12.6 **Unmounting**: `Continuation.yield` copies the live frames from the carrier's stack into a
       `StackChunk` object on the heap (a lazy, "freeze only what is needed" copy) and returns
       control to the scheduler. `[PROVE]` `[RESEARCH]`
3.12.7 Freeze/thaw and **lazy copy**: only the frames that changed are copied, and thaw copies back
       incrementally (return barriers), so a deep stack that only touches its top frames is cheap.
       This is why unmounting is not O(stack depth) in practice. `[PROVE]` `[NUM]` `[RESEARCH]`
3.12.8 `StackChunk` as a real heap object with its own GC handling, and the consequence: virtual
       thread stacks are **garbage-collectable**, and a leaked, never-completing virtual thread is
       a heap leak, not a thread leak. `[PROVE]` `[X-REF 06]` `[TRAP]`
3.12.9 The scheduler: a `ForkJoinPool` in **FIFO async mode**, created with parallelism =
       `availableProcessors()`, maxPoolSize 256, and threads of class
       `CarrierThread`. `[NUM]` `[SOURCE]` `[RESEARCH]`
3.12.10 The system properties: `jdk.virtualThreadScheduler.parallelism`,
        `jdk.virtualThreadScheduler.maxPoolSize`, and (Java 21 only)
        `jdk.virtualThreadScheduler.minRunnable`. `[RESEARCH]` `[NUM]`
3.12.11 Park path in full: `LockSupport.park` → `VirtualThread.park` → set `PARKING` →
        `Continuation.yield` → scheduler thread returns → later `unpark` submits `runContinuation`
        again. Compare against the platform-thread path's `pthread_cond_wait`. `[PROVE]`
        `[SOURCE]`
3.12.12 The I/O path: blocking socket reads are implemented over non-blocking NIO plus a **poller**
        thread (`sun.nio.ch.Poller`, epoll/kqueue) that unparks the virtual thread when the fd is
        ready. `jdk.pollerMode` selects the poller implementation. `[PROVE]` `[RESEARCH]`
3.12.13 File I/O is *not* covered by the poller on Linux: `FileChannel` reads are delegated to a
        pool of carrier-blocking operations, which is why file I/O can still pin or consume
        carriers. No production io_uring integration exists in the JDK. `[TRAP]` `[RESEARCH]`
3.12.14 `Thread.sleep` on a virtual thread schedules an unpark on the scheduler's timer rather than
        occupying a carrier. `[PROVE]`
3.12.15 Pinning implementation in Java 21: `Continuation.yield` fails when the continuation has a
        native frame or a held monitor, so the thread blocks *on the carrier* instead.
        `[PROVE]` `[SOURCE]`
3.12.16 JEP 491's implementation: monitors gain an owner identity that is the virtual thread, the
        `ObjectMonitor` records a virtual-thread owner, and monitor-blocked becomes a yield point.
        Consequences: `-Djdk.tracePinnedThreads` removed, `jdk.VirtualThreadPinned` broadened to
        cover park/monitor-enter/`Object.wait` while pinned by a native or VM frame.
        `[RESEARCH]` `[VERSION-TRAP]` `[SOURCE]`
3.12.17 Remaining pinning causes after JEP 491: native/JNI frames, FFM downcalls, some class-loading
        paths, and VM-internal frames. `[RESEARCH]`
3.12.18 Why virtual threads do not appear in `jstack`: `jstack` walks the JVM's list of
        `JavaThread`s, and an unmounted virtual thread has no `JavaThread`. `[PROVE]` `[DUMP]`
3.12.19 The JSON thread dump's structure: thread containers, one per `StructuredTaskScope` or
        executor, with parent links — the structured-concurrency payoff for diagnostics.
        `[DUMP]` `[RESEARCH]`
3.12.20 Cost arithmetic: `Thread` object + `VirtualThread` fields + `Continuation` + an initial
        `StackChunk` ≈ a few hundred bytes to a few KB, versus ~1 MB of reserved stack. One
        million virtual threads at 2 KB average = 2 GB of heap — so they are cheap, not free.
        `[NUM]` `[PROVE]`
3.12.21 The `ThreadContainer`/`ThreadFlock` internals that back `StructuredTaskScope`: a flock owns
        its threads, tracks them for the dump, and enforces the owner-thread and LIFO-close rules.
        `[SOURCE]` `[RESEARCH]`
3.12.22 `ScopedValue` internals: an immutable linked binding chain per thread (`Carrier`), plus a
        small per-thread **cache** keyed by the scoped value's hash so `get()` is close to a field
        read. Inheritance to a structured subtask is a pointer copy, not a map copy — this is the
        performance argument over `InheritableThreadLocal`. `[PROVE]` `[SOURCE]` `[RESEARCH]`

*(22 leaves)*

## §3.13 Observability of concurrency at runtime

3.13.1 Reading a `jstack` dump line by line: the header line (`"name" #id [tid] daemon prio os_prio
       cpu elapsed tid nid state`), the `java.lang.Thread.State` line, the stack, the
       `- locked <0x…>` / `- waiting to lock <0x…>` / `- parking to wait for <0x…>` annotations,
       and the "Locked ownable synchronizers" block. `[DUMP]`
3.13.2 The three dump signatures you must recognise instantly: monitor contention (many BLOCKED on
       one address), pool saturation (all workers in application code, queue growing), and pool
       idleness (all workers parked in `getTask`). `[DUMP]` `[PROVE]`
3.13.3 The deadlock section of a dump and how the detector builds the wait-for graph. `[DUMP]`
3.13.4 `jcmd Thread.print`, `Thread.print -l` (with locks), `Thread.dump_to_file -format=json|text`,
       and `jcmd VM.native_memory` for thread stack accounting. `[X-REF 06]`
3.13.5 `nid` in the dump is the OS thread id in hex — the join key to `top -H`, `ps -eLo`, and
       `perf`. The classic "which Java thread is burning the CPU" workflow. `[DUMP]` `[X-REF 11]`
3.13.6 JFR concurrency events, named: `jdk.JavaMonitorEnter` (threshold 20 ms default),
       `jdk.JavaMonitorWait`, `jdk.JavaMonitorInflate`, `jdk.ThreadPark`, `jdk.ThreadStart`/`End`,
       `jdk.ThreadSleep`, `jdk.VirtualThreadStart`/`End`/`Pinned`/`SubmitFailed`,
       `jdk.ExecutorTaskSubmit`. `[RESEARCH]` `[NUM]` `[X-REF 06]`
3.13.7 The default thresholds matter: a 20 ms monitor-enter threshold means short but frequent
       contention is invisible in a default JFR recording. Lower it deliberately. `[TRAP]`
       `[NUM]`
3.13.8 async-profiler `-e lock` and `-e wall` for contention and off-CPU analysis, and why a CPU
       profiler shows nothing when the problem is blocking. `[RESEARCH]` `[X-REF 06]`
3.13.9 Micrometer/JMX metrics worth exporting: `jvm.threads.live/daemon/peak/states`,
       `executor.queued`, `executor.active`, `executor.completed`, `executor.queue.remaining`,
       `executor.seconds`. `[X-REF 20]` `[RESEARCH]`
3.13.10 `ThreadMXBean` contention monitoring for a programmatic top-N-blocked report, and its
        overhead. `[BUILD]`
3.13.11 `/proc/<pid>/task/<tid>/status` and `stat` for per-thread voluntary/involuntary context
        switches and run state, joined to the Java thread by nid. `[X-REF 11]` `[DUMP]`
3.13.12 What none of these tools can show you: a data race. Only jcstress, a race detector, or
        reasoning finds those. `[TRAP]`

*(12 leaves)*

---

**PART 3 total: 8+18+12+10+22+10+15+24+14+24+16+22+12 = 207 leaves**

---

# PART 4 — BUILD IT

Every `[BUILD]` leaf ships complete, compiling, generic Java 21 and is followed by a
**Diff vs the real one** table covering at minimum: bounds and state checks, intrinsics, memory
ordering level used, cancellation, fairness, serialization, `Spliterator`/iteration support, null
policy, allocation strategy, and *why the JDK bothers*.

## §4.1 Locks from first principles

4.1.1 `SpinLock` — an `AtomicBoolean` with a `compareAndSet` loop and `Thread.onSpinWait()`.
      `[BUILD]`
4.1.2 Measure it: spin lock versus `ReentrantLock` at 1, 2, 8 and 64 threads with a 100 ns and a
      100 µs critical section. Show where each wins and why. `[NUM]` `[PROVE]`
4.1.3 `TestAndTestAndSetLock` — read before CAS, so the line is not invalidated on every attempt.
      Explain the coherence-traffic difference. `[BUILD]` `[PROVE]`
4.1.4 `TicketLock` — two counters, `nextTicket` and `nowServing`; FIFO fair, but every waiter
      spins on the same line. `[BUILD]` `[PROVE]`
4.1.5 `CLHLock` — an implicit queue of nodes, each spinning on its **predecessor's** flag, so each
      waiter spins on a different line. Requires a `ThreadLocal` node and a tail
      `AtomicReference`. `[BUILD]` `[PROVE]`
4.1.6 `MCSLock` — an explicit queue where each waiter spins on **its own** node's flag, set by the
      predecessor on release. Better on NUMA/non-cache-coherent-uniform hardware. `[BUILD]`
4.1.7 CLH versus MCS as a table: space, spin location, release cost, suitability for cacheless
      NUMA, and which one AQS is derived from and why (AQS needs cancellation and blocking, which
      CLH's `prev` links support). `[PROVE]` `[RESEARCH]`
4.1.8 `BackoffLock` — exponential randomised backoff over a test-and-set lock, and the
      latency/throughput trade-off it introduces. `[BUILD]`
4.1.9 A **reentrant** mutex built on `AtomicReference<Thread>` plus a plain hold count, showing why
      the count needs no atomicity (only the owner touches it). `[BUILD]` `[PROVE]`
4.1.10 Diff table for all of the above versus `ReentrantLock`: parking instead of spinning,
       cancellation, fairness mode, condition support, instrumentation, monitor-dump visibility.

*(10 leaves)*

## §4.2 Building on AQS

4.2.1 `SimpleMutex extends AbstractQueuedSynchronizer` — a non-reentrant lock in ~25 lines:
      `tryAcquire` CASes 0→1, `tryRelease` sets 0, `isHeldExclusively`, plus a `Lock` facade.
      `[BUILD]`
4.2.2 `CountingSemaphore` on AQS shared mode: `tryAcquireShared` returns remaining permits,
      `tryReleaseShared` adds them back with a CAS loop. `[BUILD]`
4.2.3 `OneShotLatch` on AQS: state 0 = closed, 1 = open; `tryAcquireShared` returns 1 or −1;
      `tryReleaseShared` sets 1 and returns true. Exactly how `CountDownLatch` works. `[BUILD]`
4.2.4 A **reentrant** AQS mutex: hold count in `state`, owner in `setExclusiveOwnerThread`, and the
      `IllegalMonitorStateException` on foreign release. `[BUILD]`
4.2.5 A fair variant of 4.2.4 by adding `hasQueuedPredecessors()`, and a benchmark showing the
      throughput cost. `[BUILD]` `[NUM]`
4.2.6 A `Condition` on your AQS mutex via `new ConditionObject()`, with a bounded buffer using it.
      `[BUILD]`
4.2.7 Diff table versus `ReentrantLock`: `tryLock(timeout)`, `lockInterruptibly`, serialization
      (`readObject` resets state to 0), `toString` for dumps, `getOwner`/`getQueuedThreads`, and
      the JDK's `Sync` class hierarchy.

*(7 leaves)*

## §4.3 Bounded blocking queue, three ways

4.3.1 Version 1 — `synchronized` + `wait`/`notifyAll` over an array ring buffer, with the
      `while (count == items.length) wait();` loop written correctly. `[BUILD]`
4.3.2 Version 2 — `ReentrantLock` + two `Condition`s (`notFull`, `notEmpty`), signalling exactly
      the right waiters. Show the `signal` (not `signalAll`) correctness argument. `[BUILD]`
      `[PROVE]`
4.3.3 Version 3 — two locks (`putLock`/`takeLock`) over a linked list with an `AtomicInteger`
      count, mirroring `LinkedBlockingQueue`, including the cascading-signal rule. `[BUILD]`
      `[PROVE]`
4.3.4 Add timed `offer`/`poll` using `awaitNanos`'s remaining-time return value, written as a
      correct deadline loop. `[BUILD]` `[TRAP]`
4.3.5 Add `drainTo` and prove it does not lose elements under a concurrent `put`. `[BUILD]`
      `[PROVE]`
4.3.6 A **lock-free single-producer single-consumer** ring buffer with `head`/`tail` as padded
      `AtomicLong`s, and the capacity-power-of-two masking trick. Prove correctness for exactly one
      producer and one consumer. `[BUILD]` `[PROVE]`
4.3.7 Diff table versus `ArrayBlockingQueue` and `LinkedBlockingQueue`: fairness flag, null
      rejection, `Spliterator`/`forEach`/`removeIf` support, `remove(Object)` under both locks,
      serialization, `weakly consistent` iterator, and why the JDK's `fullyLock()` exists.

*(7 leaves)*

## §4.4 Non-blocking data structures

4.4.1 `TreiberStack<E>` — `AtomicReference<Node<E>> top`, push and pop as CAS loops. `[BUILD]`
4.4.2 The ABA demonstration: a deliberately racy pop-recycle-push sequence that corrupts the
      stack, then the same code with `AtomicStampedReference`. `[BUILD]` `[PROVE]` `[TRAP]`
4.4.3 Why the plain Java `TreiberStack` is *usually* ABA-safe: the GC prevents node reuse while a
      reference is held, so ABA needs explicit node pooling. State this precisely — it is the
      answer that separates a memorised answer from an understood one. `[PROVE]` `[RESEARCH]`
4.4.4 Hazard pointers and epoch-based reclamation, described as the C++ answer to the problem Java
      solves with GC, and why you would still need them in Java if you pooled nodes.
      `[RESEARCH]`
4.4.5 `MichaelScottQueue<E>` — the two-lock-free-pointer queue with a dummy head, the lagging tail,
      and the "help advance the tail" step. `[BUILD]` `[PROVE]`
4.4.6 Prove the linearization points of both operations and why the dummy node is required.
      `[PROVE]`
4.4.7 A **lock-free counter with striping** — your own mini `Striped64`: base + padded cells +
      thread probe + growth to `NCPU`. `[BUILD]`
4.4.8 Measure it against `AtomicLong` and `LongAdder` with JMH at 1/4/16/64 threads. `[NUM]`
      `[BUILD]`
4.4.9 A copy-on-write list from scratch: `volatile Object[] array`, a lock on mutation, snapshot
      iterator. `[BUILD]`
4.4.10 A `ConcurrentHashMap`-shaped mini map: power-of-two table, CAS to install the first node,
       `synchronized` on the head node otherwise, no resize (and an explicit note on why resize is
       the hard part). `[BUILD]`
4.4.11 Diff table for all of the above versus the JDK: `Spliterator`/stream support, serialization,
       `size()` accounting, weakly-consistent iterators, `VarHandle` release/acquire instead of
       volatile, self-linking for GC, treeification, and cooperative resize.

*(11 leaves)*

## §4.5 A thread pool from scratch

4.5.1 `MiniThreadPool` v1: N worker threads over one `BlockingQueue<Runnable>`, `execute`,
      `shutdown` via poison pills. `[BUILD]`
4.5.2 v2: add `submit(Callable<T>)` returning your own `Future` — implement the future's state
      machine and blocking `get` with `wait`/`notifyAll`. `[BUILD]`
4.5.3 v3: pack run-state and worker count into one `AtomicInteger`, mirroring
      `ThreadPoolExecutor.ctl`, and implement the four-step submission algorithm exactly.
      `[BUILD]` `[PROVE]`
4.5.4 v4: add core/max sizing, `keepAliveTime` via `poll(timeout)`, and a rejection handler
      interface with the four policies. `[BUILD]`
4.5.5 v5: add `beforeExecute`/`afterExecute` hooks and prove that an exception in a task cannot
      kill a worker. `[BUILD]` `[PROVE]`
4.5.6 A `ThreadFactory` with named threads, daemon flag, and an uncaught-exception handler.
      `[BUILD]`
4.5.7 A context-propagating `Executor` decorator that copies MDC and a `ScopedValue`-style context
      across the submission boundary. `[BUILD]`
4.5.8 A `CompletionService` from scratch: wrap each task so it enqueues itself on completion.
      `[BUILD]`
4.5.9 Diff table versus `ThreadPoolExecutor`: the `Worker`-as-AQS interrupt-safety trick, the
      double-check after enqueue, `purge`/`remove`, `getLargestPoolSize`, `terminated()`,
      `allowCoreThreadTimeOut`, `prestartAllCoreThreads`, and `RejectedExecutionException` after
      shutdown.

*(9 leaves)*

## §4.6 A work-stealing deque and a mini fork/join

4.6.1 `WorkStealingDeque<T>` — a circular array with `top` (owner, plain) and `base` (thieves,
      `AtomicLong`), `pushBottom`/`popBottom`/`steal`, and the single-element CAS race between
      owner and thief. `[BUILD]` `[PROVE]`
4.6.2 Prove the one place a CAS is unavoidable: when `top - base == 1`, owner and thief target the
      same slot. `[PROVE]`
4.6.3 Growing the deque without losing steals. `[BUILD]`
4.6.4 `MiniForkJoinPool`: N workers, each with a deque, randomised victim selection, and a
      backoff/park when scanning fails. `[BUILD]`
4.6.5 `MiniRecursiveTask<V>` with `fork`/`compute`/`join`, and the "help by executing the joined
      task yourself" trick that avoids deadlock. `[BUILD]` `[PROVE]`
4.6.6 Run a parallel merge sort and a parallel sum on it, tuning the sequential threshold and
      plotting the result. `[BUILD]` `[NUM]`
4.6.7 Diff table versus `ForkJoinPool`: the packed `ctl` field, compensation, `CountedCompleter`,
      the common pool, `ManagedBlocker`, quiescence detection, `InnocuousForkJoinWorkerThread`,
      and exception capture/rethrow semantics.

*(7 leaves)*

## §4.7 Structured concurrency and futures from scratch

4.7.1 `MiniScope implements AutoCloseable` — `fork(Callable<T>)` returning a handle, `join()`
      waiting for all, `close()` cancelling stragglers, with the owner-thread and LIFO checks.
      `[BUILD]`
4.7.2 Add a shutdown-on-failure policy: the first failure cancels the siblings. `[BUILD]`
4.7.3 Add a shutdown-on-success policy for hedged requests. `[BUILD]`
4.7.4 Add a deadline (`joinUntil`) and prove the deadline is enforced even if a subtask ignores
      interruption (it cannot be — state the honest limitation). `[PROVE]` `[TRAP]`
4.7.5 A minimal `CompletableFuture`: `volatile Object result`, a Treiber stack of callbacks,
      `complete`, `thenApply`, `thenCompose`, `whenComplete`, and the recursion-unrolling in
      `postComplete`. `[BUILD]` `[PROVE]`
4.7.6 Diff table versus `StructuredTaskScope` and `CompletableFuture`: `ThreadFlock`, the JSON
      thread dump integration, `StructureViolationException`, `ScopedValue` inheritance, the
      `Joiner` API of JEP 505, `minimalCompletionStage`, `AltResult`/`NIL`, and the ~60 combinator
      methods you did not implement.

*(6 leaves)*

## §4.8 Diagnostic and teaching harnesses

4.8.1 A **visibility harness**: a non-volatile stop flag in a hot loop that provably never exits,
      with the `-XX:+PrintCompilation`/`PrintAssembly` evidence. `[BUILD]` `[ASM]`
4.8.2 A **lost-update harness**: N threads × M increments on `int`, `volatile int`,
      `AtomicInteger`, `synchronized`, and `LongAdder`, printing the final value and the elapsed
      time for each. One table makes the whole `volatile`-is-not-atomic point. `[BUILD]` `[NUM]`
4.8.3 A **deadlock harness** with two locks and two threads, plus a `ThreadMXBean` watchdog that
      detects and logs the cycle. `[BUILD]`
4.8.4 A **livelock harness**: two threads politely yielding to each other forever, then the fixed
      version with randomised backoff. `[BUILD]`
4.8.5 A **false-sharing harness**: two threads writing adjacent versus 64-byte-separated array
      slots; report the throughput ratio. `[BUILD]` `[NUM]`
4.8.6 A **thread-pool starvation harness**: a single-thread executor whose task submits to itself
      and blocks on the result. `[BUILD]`
4.8.7 A **ThreadLocal leak harness**: a fixed pool, a ThreadLocal holding a large array, no
      `remove()`, and the heap-dump evidence. `[BUILD]` `[DUMP]`
4.8.8 A **pinning harness** (Java 21): a `synchronized` block around a `Thread.sleep` on virtual
      threads with `parallelism=1`, showing the stall; and the same code on Java 24 showing it
      gone. `[BUILD]` `[VERSION-TRAP]`
4.8.9 An **unsafe-publication harness**: an object with non-final fields published through a plain
      field, run under jcstress, showing the default-value read. `[BUILD]` `[RESEARCH]`
4.8.10 A **DCL harness** with and without `volatile`, run under jcstress on AArch64. `[BUILD]`
       `[RESEARCH]`
4.8.11 A **backpressure harness**: a fast producer and a slow consumer across an unbounded queue
       (watch the heap climb) and a bounded queue (watch the producer throttle). `[BUILD]`
       `[NUM]`
4.8.12 A **thread-dump reading exercise**: capture a dump during each of the harnesses above and
       annotate the distinguishing lines. `[DUMP]`

*(12 leaves)*

---

**PART 4 total: 10+7+7+11+9+7+6+12 = 69 leaves**

---

# PART 5 — INTERVIEW AND RETENTION

## §5.1 The questions, with the answer shape

Each leaf is one question plus the two-or-three-beat structure of a correct answer. The write pass
supplies the full answer; the syllabus fixes the question set.

**Fundamentals**

5.1.1 Process versus thread, and what exactly is shared.
5.1.2 `start()` versus `run()`. What happens if you call `start()` twice.
5.1.3 Why is `Runnable` preferred to extending `Thread`.
5.1.4 Walk the six `Thread.State` values and the transitions between them.
5.1.5 Why does a thread blocked on a socket read show `RUNNABLE`.
5.1.6 What does `Thread.sleep` release. What does `Object.wait` release.
5.1.7 Why were `Thread.stop`/`suspend`/`resume` removed.
5.1.8 How do you stop a thread, properly.
5.1.9 What are the two legal responses to `InterruptedException`.
5.1.10 What is the difference between `isInterrupted()` and `Thread.interrupted()`.
5.1.11 Daemon versus non-daemon threads.
5.1.12 What does `Thread.yield()` guarantee. (Nothing.)

**`synchronized`, `volatile`, and the memory model**

5.1.13 What are the *two* guarantees of `synchronized`.
5.1.14 What is a monitor and where does it live.
5.1.15 Is `synchronized` reentrant, and why does it have to be.
5.1.16 Do a synchronized instance method and a synchronized static method exclude each other.
5.1.17 What can go wrong locking on a `String` literal or a boxed `Integer`.
5.1.18 What does `volatile` guarantee, and what does it not.
5.1.19 Why is `volatile int count; count++` still broken.
5.1.20 Give four correct uses of `volatile`.
5.1.21 Does `volatile` "flush the cache to main memory"? (No — explain what actually happens.)
5.1.22 What is happens-before, and does it mean "earlier in time"?
5.1.23 List the happens-before edges you rely on daily.
5.1.24 What is a data race, and how does it differ from a race condition.
5.1.25 What is the DRF-SC guarantee and why does it matter to you.
5.1.26 Why does the same code pass on x86 and fail on ARM.
5.1.27 Can a non-volatile `long` write tear? What about a reference?
5.1.28 What is safe publication, and name five mechanisms.
5.1.29 Why is double-checked locking broken without `volatile`, and why does `volatile` fix it.
5.1.30 Explain the holder idiom and why it needs no synchronization.
5.1.31 What guarantee do `final` fields give, and what destroys it.
5.1.32 What are the four ways `this` escapes from a constructor.
5.1.33 Why does adding a `println` make the bug go away.

**Locks and synchronizers**

5.1.34 `synchronized` versus `ReentrantLock`: when do you reach for each.
5.1.35 Why must `unlock()` be in a `finally`.
5.1.36 What is a fair lock and what does it cost.
5.1.37 Why is barging faster than fairness.
5.1.38 When does a `ReadWriteLock` actually win.
5.1.39 Why can you downgrade a write lock to a read lock but not upgrade.
5.1.40 What is `StampedLock`'s optimistic read and what must you not do inside one.
5.1.41 Why is `StampedLock` not reentrant, and what happens if you try.
5.1.42 `CountDownLatch` versus `CyclicBarrier` versus `Phaser`.
5.1.43 Is `Semaphore(1)` a mutex? (No — say why.)
5.1.44 Why must `wait()` be in a `while` loop — give both reasons.
5.1.45 `notify` versus `notifyAll`, and when `notify` loses a signal.
5.1.46 What is a spurious wakeup and where does it come from.
5.1.47 What is the lost-wakeup bug and how do you prevent it.
5.1.48 Explain `LockSupport.park`/`unpark` and the permit.
5.1.49 What is AQS and what does `state` mean in `ReentrantLock`, `Semaphore` and
       `CountDownLatch`.
5.1.50 How does `Condition.await` differ from `Object.wait` internally.

**Atomics and lock-free**

5.1.51 What is CAS and what instruction implements it.
5.1.52 Write `incrementAndGet` by hand.
5.1.53 Lock-free versus wait-free versus obstruction-free.
5.1.54 What is the ABA problem and when does it actually matter in Java.
5.1.55 Why does Java's GC make most ABA problems disappear.
5.1.56 `AtomicLong` versus `LongAdder` — how does `LongAdder` work and when does it lose.
5.1.57 Why is `LongAdder.sum()` not atomic.
5.1.58 What is false sharing and how does `LongAdder` avoid it.
5.1.59 What is a `VarHandle` and what are its four ordering modes.
5.1.60 When would you use `setRelease` instead of a volatile write.

**Collections**

5.1.61 How does `ConcurrentHashMap` achieve concurrency in Java 8+, and what changed from Java 7.
5.1.62 Why does `ConcurrentHashMap` forbid null keys and values.
5.1.63 Is `size()` on a `ConcurrentHashMap` accurate?
5.1.64 Why is `containsKey`-then-`put` still a race on a concurrent map.
5.1.65 What runs under the bin lock in `computeIfAbsent`, and what must it not do.
5.1.66 Fail-fast versus weakly consistent versus snapshot iterators.
5.1.67 When is `CopyOnWriteArrayList` the right choice, and when is it a disaster.
5.1.68 Why is there no `ConcurrentArrayList`.
5.1.69 `Hashtable` versus `Collections.synchronizedMap` versus `ConcurrentHashMap`.
5.1.70 How does `ConcurrentHashMap` resize while readers are reading it.

**Executors, queues and futures**

5.1.71 State the `ThreadPoolExecutor` submission algorithm in order.
5.1.72 Why is `newFixedThreadPool` dangerous in production.
5.1.73 Why is `newCachedThreadPool` dangerous in production.
5.1.74 Name the four rejection policies and say which one gives backpressure.
5.1.75 How do you size a thread pool for CPU-bound and for I/O-bound work — derive it.
5.1.76 `shutdown()` versus `shutdownNow()`, and the correct two-phase shutdown.
5.1.77 Why does an exception in a task submitted with `submit` vanish.
5.1.78 Why does an exception in a scheduled task stop all future runs.
5.1.79 `scheduleAtFixedRate` versus `scheduleWithFixedDelay`.
5.1.80 What is a bounded queue for, and what does an unbounded one convert overload into.
5.1.81 What is `SynchronousQueue` and where is it used.
5.1.82 How does the producer–consumer pattern shut down cleanly.
5.1.83 `thenApply` versus `thenCompose` versus `thenCombine`.
5.1.84 Which thread runs a non-async `CompletableFuture` callback.
5.1.85 Why should you always pass an executor to `CompletableFuture`.
5.1.86 How do you get the results out of `allOf`.
5.1.87 Does `CompletableFuture.cancel(true)` interrupt the running task? (No.)
5.1.88 Why do exceptions in a `CompletableFuture` chain disappear.
5.1.89 What is work stealing and why LIFO local / FIFO steal.
5.1.90 Why must you not block in a fork/join task, and what is `ManagedBlocker`.
5.1.91 How many threads does `ForkJoinPool.commonPool()` have and who else uses it.

**Liveness and diagnostics**

5.1.92 What are the four Coffman conditions and which one do you break in practice.
5.1.93 Solve the account-transfer deadlock.
5.1.94 Deadlock versus livelock versus starvation versus lock convoy.
5.1.95 How do you detect a deadlock in production, and can the JVM break it?
5.1.96 What deadlocks can `jstack` *not* see.
5.1.97 What do BLOCKED and WAITING each tell you in a thread dump.
5.1.98 A service is at 100 % CPU with no throughput — walk your diagnosis.
5.1.99 A service is at 0 % CPU with no throughput — walk your diagnosis.
5.1.100 How do you find which Java thread is burning a core.

**ThreadLocal, virtual threads, structured concurrency**

5.1.101 How is `ThreadLocal` stored, and why is the key weak but the value strong.
5.1.102 Describe the thread-pool `ThreadLocal` leak — both halves.
5.1.103 Why does `InheritableThreadLocal` not solve context propagation for pools.
5.1.104 What is a virtual thread and where does its stack live.
5.1.105 What is mounting and unmounting.
5.1.106 What is the virtual-thread scheduler and how is it sized.
5.1.107 What is pinning, what caused it in Java 21, and what changed in Java 24.
5.1.108 Why should you never pool virtual threads.
5.1.109 How do you limit concurrency once you have virtual threads.
5.1.110 Why don't virtual threads appear in `jstack`, and what do you use instead.
5.1.111 What is the most common surprise after migrating to virtual threads.
5.1.112 Do virtual threads make code faster? (Scale, not speed.)
5.1.113 What problem does structured concurrency solve that `CompletableFuture` does not.
5.1.114 `ScopedValue` versus `ThreadLocal`.
5.1.115 Is structured concurrency final yet? (No — say which JEP and which release.)

**Design and judgement (the senior half)**

5.1.116 Design a thread-safe LRU cache, and defend every choice.
5.1.117 Design a rate limiter for "10 concurrent calls to a downstream service".
5.1.118 Design a connection pool.
5.1.119 Implement a blocking queue with `wait`/`notify`.
5.1.120 Implement a bounded blocking queue with `Condition`s.
5.1.121 Print odd/even numbers alternately with two threads — three solutions.
5.1.122 Print A/B/C in order with three threads.
5.1.123 The dining philosophers, with the resource-ordering and the arbitrator solution.
5.1.124 Implement a read-write lock.
5.1.125 Implement a barrier.
5.1.126 Implement `CompletableFuture.allOf`.
5.1.127 Implement a thread-safe singleton — five ways, ranked.
5.1.128 Make an existing non-thread-safe class thread-safe without editing it.
5.1.129 You have a shared counter at 100k updates/sec — walk the options.
5.1.130 Your p99 doubled after adding a cache — how could a cache make it slower?
5.1.131 When would you choose reactive over virtual threads in 2026, honestly.
5.1.132 How would you test the concurrent class you just wrote.

*(132 leaves)*

## §5.2 The trap index

One line per misconception, in the form *wrong belief → symptom → fix*. This is the pre-interview
review page.

5.2.1 "`volatile` makes it atomic."
5.2.2 "`synchronized` is only about mutual exclusion."
5.2.3 "`volatile` flushes the cache to main memory."
5.2.4 "Happens-before means happens earlier in time."
5.2.5 "It works on my machine" = x86-TSO.
5.2.6 "`sleep` releases the lock."
5.2.7 "Adding a sleep fixes the race."
5.2.8 "`start()` twice throws `IllegalStateException`." (It is `IllegalThreadStateException`.)
5.2.9 "Catching and ignoring `InterruptedException` is fine."
5.2.10 "`Future.cancel(true)` kills the task."
5.2.11 "`CompletableFuture.cancel(true)` interrupts the task."
5.2.12 "`orTimeout` cancels the work."
5.2.13 "`anyOf` gives the first success."
5.2.14 "`newFixedThreadPool` respects maximumPoolSize."
5.2.15 "The pool queues before it creates core threads."
5.2.16 "`DiscardOldestPolicy` is a reasonable default."
5.2.17 "An unbounded queue is safer than rejecting."
5.2.18 "`ConcurrentHashMap` makes my compound action atomic."
5.2.19 "`size()` on a concurrent collection is exact."
5.2.20 "`CopyOnWriteArrayList` is a fast concurrent list."
5.2.21 "Fail-fast iterators are a thread-safety mechanism."
5.2.22 "`Collections.synchronizedList` is safe to iterate."
5.2.23 "`Collections.unmodifiableList` is thread-safe / is a copy."
5.2.24 "Two atomics make an atomic pair."
5.2.25 "`LongAdder` can replace `AtomicLong` everywhere."
5.2.26 "ABA is a Java problem." (It mostly is not, because of GC.)
5.2.27 "Biased → thin → fat lock escalation." (Biased locking is gone.)
5.2.28 "Locks are slow." (Uncontended locks are not.)
5.2.29 "Narrow critical sections are always better." (Lock coarsening; and broken invariants.)
5.2.30 "`ReentrantLock` releases on exception like `synchronized`."
5.2.31 "Fair locks are the safe default."
5.2.32 "`ReadWriteLock` is faster because reads are more common."
5.2.33 "`StampedLock` is a drop-in `ReentrantReadWriteLock`."
5.2.34 "`Semaphore(1)` is a mutex."
5.2.35 "`notify` is a cheaper `notifyAll`."
5.2.36 "`if (!cond) wait();`"
5.2.37 "`ThreadLocal.set(null)` cleans up."
5.2.38 "`InheritableThreadLocal` propagates context into a pool."
5.2.39 "`ThreadLocal` caching is still a good idea with virtual threads."
5.2.40 "Virtual threads are faster."
5.2.41 "Pool the virtual threads."
5.2.42 "Replace `synchronized` with `ReentrantLock` for virtual threads." (Java 21 only.)
5.2.43 "Virtual threads removed my need for backpressure."
5.2.44 "`jstack` shows my virtual threads."
5.2.45 "The JVM breaks deadlocks."
5.2.46 "`jstack` finds all deadlocks."
5.2.47 "Thread priorities work."
5.2.48 "A shutdown hook always runs."
5.2.49 "A benign data race is fine."
5.2.50 "`System.currentTimeMillis()` is fine for a timeout."
5.2.51 "`availableProcessors()` is the machine's core count." (Not in a container.)
5.2.52 "Parallel streams use my executor."
5.2.53 "The common pool is a good place for I/O."
5.2.54 "Structured concurrency is final."
5.2.55 "Scoped values are still preview." (Final in 25.)

*(55 leaves)*

## §5.3 One-line assertions and drills

5.3.1 The assertion set that becomes the `## Atomic concept checklist` in the written guide — one
      flat line per distinct concept, covering every §1–§4 section. Every existing checklist line
      in `src/topics/05-multithreading-concurrency.md` must survive verbatim or expanded.
5.3.2 The **numbers drill**: recite from memory — default stack 1 MB, cache line 64 B (`@Contended`
      pads 128 B), `TREEIFY_THRESHOLD = 8`, `UNTREEIFY_THRESHOLD = 6`,
      `MIN_TREEIFY_CAPACITY = 64`, `MIN_TRANSFER_STRIDE = 16`, CHM load factor 0.75,
      `ThreadPoolExecutor` `CAPACITY = 2^29 − 1`, common-pool parallelism =
      `availableProcessors() − 1`, virtual-thread scheduler parallelism = `availableProcessors()`,
      maxPoolSize 256, `common.maximumSpares` 256, `Flow.defaultBufferSize()` = 256,
      `jdk.VirtualThreadPinned` threshold 20 ms, `GuaranteedSafepointInterval` 1000 ms,
      RW-lock 16/16 bit split (65 535 max), priority range 1/5/10. `[NUM]`
5.3.3 The **table drill**: reproduce from memory the submission algorithm, the four rejection
      policies, the four method families of `BlockingQueue`, the six `Thread.State` values, the
      four Coffman conditions, and the four `VarHandle` ordering modes.
5.3.4 The **code drill**: write from memory, correctly, in under five minutes each — the
      `lock/try/finally` idiom, the `while`-loop `wait`, DCL with `volatile`, the holder singleton,
      the two-phase shutdown, the try/finally `ThreadLocal.remove`, and the CAS retry loop.
5.3.5 The **diagnosis drill**: given a thread dump excerpt, classify it as contention, saturation,
      idle, deadlock, or pinning within thirty seconds. `[DUMP]`
5.3.6 The **version drill**: for each of `synchronized` pinning, scoped values, structured
      concurrency, `Thread.stop`, biased locking, and compact headers, state the release and the
      direction of the change. `[VERSION-TRAP]`
5.3.7 The **"what does this print"** set: five short racy programs with the set of legal outputs
      and the JMM justification for each. `[PROVE]`
5.3.8 The **whiteboard set**: the six implementations you should be able to write cold —
      bounded buffer, thread-safe singleton, rate limiter, LRU cache, alternating printers,
      dining philosophers.
5.3.9 Spaced-repetition plan: PART 5 §5.2 daily, §5.1 fundamentals weekly, PART 3 once before the
      onsite. Depth is read once; the trap index is read many times.
5.3.10 The two-minute answer template for any "how would you make this thread-safe" question:
       state the invariant → state the policy → state the mechanism → state the cost → state the
       failure mode you are accepting.

*(10 leaves)*

---

**PART 5 total: 132+55+10 = 197 leaves**

## Footer — leaf counts

| Part | Sections | Leaves |
|---|---|---|
| PART 1 — Basics | §1.1–§1.26 | 470 |
| PART 2 — Intermediate | §2.1–§2.15 | 198 |
| PART 3 — Under the hood | §3.1–§3.13 | 207 |
| PART 4 — Build it | §4.1–§4.8 | 69 |
| PART 5 — Interview and retention | §5.1–§5.3 | 197 |
| **Total** | **69 sections** | **1141 leaves** |

`[RESEARCH]`-tagged leaves: **206** (PART 1: 89, PART 2: 40, PART 3: 72, PART 4: 5, PART 5: 0).
Each must be re-verified against its cited source during the write pass before any constant from
it is written down.

---

# DIAGRAM MANIFEST

**218 diagrams (D-001 … D-218).** Every one must exist as a standalone SVG file in
`src/notes/detailed/05-multithreading-concurrency/diagrams/`, named `D-NNN-short-slug.svg`,
embedded at the point of explanation with a Markdown image reference and a caption carrying the
stable id, e.g. `**D-075** — The `ThreadPoolExecutor` submission algorithm`. Where the `Type`
column says `table`, a Markdown table is the correct rendering and no SVG file is required.

Rules the manifest assumes and you must follow:

- One idea per diagram. Prefer more, smaller diagrams over one dense one.
- Where the `Must show` column asks for *frames*, produce that many clearly separated,
  individually labelled panels inside the one SVG, each captioned with the frame number and what
  changed since the previous frame.
- Every label, constant and value named in `Must show` must be visible as text in the SVG. A
  diagram that omits a named value does not satisfy the manifest.
- Arrows must be directional, orthogonal, and labelled where the direction is not obvious.
- Every diagram is drawn on QuizStakes data. Where the `Must show` cell names domain values
  (`CLIENT_BONUS_AVAILABLE`, 1,200 reservations/sec, a 3.33 stake, the 240 ms PSP p50), use those
  exact values.
- Two-thread interleaving diagrams get a time axis running downwards with one lane per thread, and
  every step numbered so the reader can replay it.
- Never inline `<svg>` in the Markdown. Never draw with ASCII characters.

## Part 1 diagrams

| # | Diagram | Syllabus leaf | Type | Must show |
|---|---|---|---|---|
| D-001 | Concurrency is structure, parallelism is execution | 1.1.3 | before-after | The same four stake-settlement tasks on a single core (interleaved slices on one timeline, "concurrent, zero parallelism") and on four cores (four lanes, "concurrent and parallel"). Total wall time written on both |
| D-002 | Amdahl's law with S = 0.05 | 1.1.5 | cost-curve | Speedup on the y axis against N on the x axis for S = 0.05, with the points N = 1, 2, 8, 64 plotted, the value **15.4×** labelled at N = 64, the asymptote 1/S = 20 drawn as a dashed line, and the formula `1 / (S + (1−S)/N)` printed |
| D-003 | The USL turns downward where Amdahl flattens | 1.1.6 | cost-curve | Both curves on one axis: Amdahl asymptotic to 20, USL peaking and then falling. The σ (contention) and κ (coherence) terms labelled on the USL curve, and the peak thread count marked "adding threads past here makes it slower" |
| D-004 | Little's law sizes the pool | 1.1.7, 1.24.19, 2.4.2 | cost-curve | L = λW plotted for QuizStakes: 1,200 stake reservations/sec at the PSP's 240 ms p50 → **288** concurrent tasks; at the 11 s p99 → **13,200**. A horizontal line at a 200-thread platform pool showing where throughput caps, and the virtual-thread line with no cap in that range |
| D-005 | Four ways a server gets its thread count | 1.1.8 | table | Rows: thread per connection, bounded pool, thread per request on virtual threads, event loop. Columns: threads at 55k peak concurrent sessions, memory, blocking allowed, code style, failure mode when overloaded |
| D-006 | What threads share and what they own | 1.2.3, 1.2.4 | memory-layout | One process box containing the shared region (heap with a `FundsLedger` instance, static fields, metaspace, code cache, fd table) and three thread boxes each owning a stack, PC, registers and TLS. A `Money stake` local drawn inside one stack; an arrow from that local to a shared `Reservation` on the heap labelled "the reference is confined, the object is not" |
| D-007 | What a context switch actually costs | 1.2.6, 1.2.7 | step-sequence, 4 frames | Frame 1: thread A running, its working set in L1/L2. Frame 2: registers saved, stack pointer switched. Frame 3: thread B runs with a cold cache. Frame 4: A resumes and refills. Direct cost ~1–10 µs and cache-refill penalty of tens of µs written on the frames; `vmstat cs` and `voluntary_ctxt_switches` named as the counters |
| D-008 | A platform thread's real footprint | 1.2.8, 1.2.9 | memory-layout | One thread drawn across four regions: ~1 MB reserved stack (virtual, committed page by page) plus a guard page, the ~1 KB `java.lang.Thread` heap object, the JVM `JavaThread`, the OS `task_struct`. Beneath: 10 000 threads ≈ 10 GB reserved address space, arithmetic shown |
| D-009 | Where the thread limit comes from | 1.2.15 | decision-tree | Four gates in series — `ulimit -u`, `/proc/sys/kernel/threads-max`, `pid_max`, container `pids.max` — with the failure at each one ending in `OutOfMemoryError: unable to create native thread`. Heap exhaustion drawn as a separate, different cause |
| D-010 | `start()` versus `run()` versus `start()` twice | 1.3.2, 1.3.3 | before-after | Left: `t.start()` — a new OS thread appears and `run` executes on it. Middle: `t.run()` — no new thread, `run` executes on the caller, both frames on one stack. Right: a second `t.start()` — the exact exception `java.lang.IllegalThreadStateException` printed, with a callout that it is **not** `IllegalStateException` |
| D-011 | The `Thread.Builder` surface | 1.3.11, 1.3.12 | table | Rows: `Thread.ofPlatform()`, `Thread.ofVirtual()`, `Thread.startVirtualThread`, `new Thread(Runnable)`. Columns: `name`/`name(prefix,start)`, `daemon`, `priority`, `stackSize`, `inheritInheritableThreadLocals`, `uncaughtExceptionHandler`, `unstarted`, `start`, `factory` — with "throws" or "ignored" written in every cell a virtual thread rejects |
| D-012 | The `Thread` deprecation and removal timeline | 1.3.14, 2.15.16 | timeline | An axis from Java 1.2 to Java 21 with markers: `stop`/`suspend`/`resume` deprecated (1.2), `ThreadGroup.stop` removed, `countStackFrames` degraded, `getId` deprecated (19), `threadId()` added (19), `stop`/`suspend`/`resume` **removed** in 20 throwing `UnsupportedOperationException`. Each marker carries the release number |
| D-013 | The six `Thread.State` values and every transition | 1.4.1–1.4.8 | state-transition | Six state boxes with every edge labelled by the call that causes it: `start()`, scheduler dispatch, `monitorenter` contention, `wait()`, `notify()`, `sleep`/`join(t)`/`parkNanos`, timeout expiry, `run` returning. The `wait` → **BLOCKED** → `RUNNABLE` path drawn explicitly and labelled "a notified thread must re-acquire the monitor" |
| D-014 | A socket read reports RUNNABLE | 1.4.3 | before-after | Left, what the reader expects: a thread in `SocketInputStream.read` shown as BLOCKED. Right, what the dump says: the same stack with `java.lang.Thread.State: RUNNABLE` quoted verbatim, and the OS-level state "descheduled, invisible to the JVM" beside it |
| D-015 | BLOCKED versus WAITING in a dump | 1.4.9, 3.13.2 | before-after | Left: twelve threads BLOCKED on the same `<0x00000000d5f5b1a8>` monitor with one owner named — labelled "contention incident, find the owner". Right: forty threads WAITING in `getTask` on a pool queue — labelled "normal idle". The distinguishing dump lines quoted on both |
| D-016 | The interrupt flag is a bit, not an event | 1.5.1–1.5.4 | state-transition | The flag as a single boolean with edges: `interrupt()` sets it; `isInterrupted()` reads it; static `Thread.interrupted()` reads **and clears**; a blocking method throwing `InterruptedException` **clears** it. A red path for `catch (InterruptedException e) { }` ending in "the cancellation request no longer exists" |
| D-017 | What is interruptible and what is not | 1.5.5, 1.5.6 | table | Rows: `Object.wait`, `Thread.sleep`, `Thread.join`, `BlockingQueue.put/take`, `Lock.lockInterruptibly`, `Condition.await`, `Semaphore.acquire`, `CountDownLatch.await`, `CyclicBarrier.await`, `Future.get`, `LockSupport.park`, `InterruptibleChannel` ops, `Selector.select`, `synchronized` acquisition, `InputStream.read` on a plain socket, `FileChannel` read. Columns: throws / returns / ignores, does it clear the flag, how you cancel it instead |
| D-018 | The two legal responses to `InterruptedException` | 1.5.4, 1.5.13 | decision-tree | Root: "can your method declare `throws InterruptedException`?" Yes → propagate. No → `Thread.currentThread().interrupt()` in the catch, then return. A third branch, swallow, marked as always a bug with the symptom "a `shutdownNow` that never stops anything" |
| D-019 | The five-level thread-safety taxonomy | 1.6.3 | table | Rows: immutable, thread-safe, conditionally thread-safe, thread-compatible, thread-hostile. Columns: what the caller must do, a JDK example, a QuizStakes example (`Money` immutable, `FundsLedger` thread-safe, `Collections.synchronizedList` conditionally, `ArrayList` compatible, a class that mutates static state hostile), and how the javadoc should say it |
| D-020 | Three kinds of confinement | 1.6.5, 1.6.6 | hierarchy | Ad-hoc (convention only, drawn dashed and labelled fragile), stack confinement (a `StakeSplit` local inside `FundsLedger.reserveStake`, unreachable from other stacks), `ThreadLocal` (a per-thread slot). A fourth box, instance confinement, with a private `final Object lock` guarding the state and no reference escaping |
| D-021 | The four ways state escapes | 1.6.10, 1.11.4 | before-after | One `Account` aggregate drawn four times: returning the internal `List<Restriction>`, storing it in a public field, passing it to an alien listener, and `this` escaping from the constructor via a registration call. Each panel shows the external reference that now aliases internal state, and the defensive fix beneath it |
| D-022 | Atomicity, visibility and ordering are independent | 1.6.9, 2.1.4 | table | Rows: plain field, `volatile`, `AtomicLong`, `synchronized`, `final`, opaque, release/acquire. Columns: atomicity (and for which widths), visibility, ordering, mutual exclusion, progress. Every cell yes/no/partial with the one-clause reason |
| D-023 | `count++` is three logical steps | 1.7.2 | step-sequence, 3 frames | The bytecode `getfield` / `iconst_1` / `iadd` / `putfield` listed, then two threads incrementing a stake-reservation counter from 41: frame 1 both read 41, frame 2 both compute 42, frame 3 both write 42. Final value 42 instead of 43, with the lost update labelled |
| D-024 | Check-then-act loses the race | 1.7.3, 1.7.7 | step-sequence, 3 frames | Two threads running `if (!restrictions.containsKey(key)) restrictions.put(key, r)` for `RestrictionKey(STAKE_BLOCKED, ADMIN)`. Frames show both checks passing, then both puts, and the second overwriting the first. Beside it: both check and act inside one `synchronized` block on the same lock |
| D-025 | A non-volatile `long` can tear | 1.7.8, 1.7.9 | before-after | Left: a 64-bit ledger balance written as two 32-bit halves, a reader observing the new high word and the old low word, with the composed nonsense value written out. Right: word tearing forbidden by JLS 17.6 — a `byte[]` where writing index 3 must not disturb index 2 or 4. References labelled "always atomic" |
| D-026 | x86-TSO hides the bug that AArch64 exposes | 1.7.10, 3.3.8, 3.3.9 | before-after | The same publication code on both architectures. Left, x86-TSO: only StoreLoad reordering permitted, the bug invisible. Right, AArch64: StoreStore and LoadLoad both permitted, the reader seeing the reference before the fields, with the observed default values printed. "It works on my machine" written on the left panel |
| D-027 | The three monitors `synchronized` can take | 1.8.6, 1.8.7 | table | Rows: `synchronized void reserve()` → `this`; `static synchronized void audit()` → `FundsLedger.class`; `synchronized (lock) { }` → the named object. Columns: which monitor, what it excludes, what it does **not** exclude, and the instance-vs-static non-exclusion stated as its own row |
| D-028 | Block versus method: two different bytecode shapes | 1.8.11, 1.8.12 | before-after | Left: `javap -c` of a synchronized block showing `monitorenter`, the body, `monitorexit`, and the **synthetic exception handler** with its second `monitorexit`, with the exception table printed. Right: `javap -v` of a synchronized method showing only the `ACC_SYNCHRONIZED` flag and no monitor bytecodes |
| D-029 | Four ways to lock on the wrong object | 1.8.8, 1.8.9, 1.8.10 | table | Rows: a non-final lock field reassigned, a `String` literal, a boxed `Integer` in −128..127, `Boolean.TRUE`, a `Class` you do not own, two threads on different lock objects. Columns: what the reader believes, what actually happens, the observable symptom, and the fix (`private final Object lock = new Object();`) |
| D-030 | Unlock happens-before the next lock | 1.8.3, 1.10.8 | timeline | Two lanes over one time axis. Thread A writes `CLIENT_CASH_AVAILABLE`, then unlocks monitor m. Thread B locks m, then reads. One labelled happens-before edge from the unlock to the lock, and a second arrow showing that *everything before* the unlock is visible after the lock — not just the guarded field |
| D-031 | What `volatile` gives and what it does not | 1.9.1, 1.9.4, 1.9.8 | table | Rows: visibility of a single field, ordering with surrounding accesses, 64-bit atomicity, compound `count++`, array elements through a volatile reference, fields of a referenced mutable object. Columns: guaranteed / not guaranteed, the reason, and the correct alternative (`AtomicInteger`, `AtomicIntegerArray`, a lock) |
| D-032 | The missing-`volatile` stop flag never stops | 1.9.7, 3.3.5 | before-after | Left: the source loop reading `running` each iteration, and the C2-hoisted form with the read lifted out and the loop reduced to `while (true)`, drawn as pseudo-assembly. Right: the same source with `volatile`, the read staying inside the loop. Both annotated with what the reader observes |
| D-033 | Volatile read is free; volatile write is not | 1.9.12, 3.3.6 | table | Rows: x86-64 volatile read, x86-64 volatile write, AArch64 volatile read, AArch64 volatile write, plain read, plain write, uncontended CAS. Columns: the instruction emitted (`mov`, `mov` + `lock addl $0,(%rsp)`, `ldar`, `stlr`, `lock cmpxchg`), the barrier it implements, and the cost from the latency ladder |
| D-034 | `volatile` on an array reference protects only the reference | 1.9.9 | memory-layout | A `volatile Money[] buckets` field pointing at an array of four elements (`CLIENT_CASH_AVAILABLE`, `CLIENT_CASH_RESERVED`, `CLIENT_BONUS_AVAILABLE`, `CLIENT_BONUS_RESERVED`). The reference slot shaded "volatile"; the four element slots shaded "plain". `AtomicReferenceArray` and `VarHandle` named as the fixes |
| D-035 | Happens-before is a partial order, not a timeline | 1.10.14, 1.10.15 | before-after | Left: two actions with an hb edge, drawn with the ordering constraint. Right: two actions with no edge, drawn as an unordered pair with both execution orders shown and both legal. A banner: "hb constrains visibility, not wall-clock order" |
| D-036 | The six synchronizes-with edges | 1.10.8 | table | Rows: unlock/lock on the same monitor, volatile write/read of the same field, `Thread.start()`, default initialisation, thread termination detection (`join`, `isAlive`), interrupt/detect-interrupt. Columns: the JLS 17.4.4 clause, the two actions, and the QuizStakes example that relies on it |
| D-037 | The derived happens-before edges you actually use | 1.10.9, 1.10.10 | hierarchy | The four base rules (program order, synchronizes-with, transitivity, the constructor/finalizer edge) as roots, with every commonly-cited "rule" drawn as a derived corollary hanging off them: monitor, volatile, `start`, `join`, default init, final-field freeze, and the `j.u.c` edges |
| D-038 | The `java.util.concurrent` happens-before edges | 1.10.11, 1.15.16 | table | Rows quoted from the package summary: place into a concurrent collection → removal; `Runnable` submission → execution start; the async computation → `Future.get`; `Lock.unlock` → subsequent `lock`; `Semaphore.release` → `acquire`; `CountDownLatch.countDown` → `await` return; `Exchanger.exchange` pairs; pre-`await` actions → barrier action → post-`await`. Columns: the releasing action, the acquiring action, what becomes visible |
| D-039 | The four barrier categories, and which x86 permits | 1.10.23, 3.3.7 | table | Rows: LoadLoad, LoadStore, StoreStore, StoreLoad. Columns: what it forbids, permitted on x86-TSO (only StoreLoad is), permitted on AArch64, the HotSpot `OrderAccess` name, and the instruction emitted |
| D-040 | Roach motel: code moves in, never out | 1.10.24 | before-after | A synchronized block with statements above and below it. Left: legal motions — both neighbours sinking/rising *into* the block, drawn with arrows. Right: illegal motions — a statement escaping the block, crossed out. Acquire and release semantics labelled on the two edges of the block |
| D-041 | Out-of-thin-air must be forbidden | 1.10.19, 3.7.4 | step-sequence, 2 frames | The classic `r1 = x; y = r1;` / `r2 = y; x = r2;` pair with both variables starting at 0. Frame 1: the self-justifying cycle that would produce `r1 == r2 == 42`, drawn as a loop of speculative reads. Frame 2: the committed-action construction of JLS 17.4.8 refusing to commit 42, with the commit order numbered |
| D-042 | Why `println` makes the bug disappear | 1.10.26 | before-after | Left: the racy loop failing. Right: the same loop with `System.out.println` inserted, passing — with the `PrintStream`'s internal `synchronized` drawn as the accidental barrier that supplied the missing edge. Labelled "the fix is a side effect, not a fix" |
| D-043 | The freeze action and the dereference chain | 1.11.1, 1.11.2, 3.7.10 | step-sequence, 3 frames | A `StakeSplit` with two `final Money` components. Frame 1: the constructor writes both fields. Frame 2: the **freeze** at the end of the constructor. Frame 3: another thread reads the reference and is guaranteed both components and, transitively, the `BigDecimal` reachable through them. The memory-chain and dereference-chain arrows labelled |
| D-044 | Unsafe publication shows default values | 1.11.11 | step-sequence, 3 frames | A non-final `Reservation` published through a plain field. Frame 1: the constructor's field writes. Frame 2: the reference store reordered *before* them. Frame 3: the reader sees a non-null reference with `amount == null` and `status == null`, both printed. The reordering arrow labelled with who is permitted to do it |
| D-045 | Double-checked locking, broken and fixed | 1.11.15, 1.11.16, 1.11.17 | before-after | Left: the classic broken DCL over `BonusService`, with the reordering that lets a second thread return a partially-constructed instance, numbered. Right: the same with `private static volatile BonusService instance`, the acquire/release edges drawn. A third panel: the local-variable-caching variant with the second volatile read removed |
| D-046 | Five ways to build a singleton, ranked | 1.11.18, 1.11.19, 1.11.20, 5.1.127 | table | Rows: eager static field, holder idiom, DCL with `volatile`, enum, synchronized accessor. Columns: lazy, synchronization on the fast path, class-init lock used (JVMS 5.5), reflection-proof, serialization-proof, lines of code, verdict |
| D-047 | Class-initialisation deadlock is invisible to `jstack` | 1.11.21 | before-after | Two classes whose static initialisers reference each other, two threads entering them simultaneously, the two init locks drawn as a cycle. Beside it: the `jstack` output with **no** "Found one Java-level deadlock" section, and the two threads shown in the class-init state |
| D-048 | `wait()` releases the monitor and re-acquires it | 1.12.3, 3.2.10 | step-sequence, 4 frames | Frame 1: thread holds the monitor, calls `wait()`. Frame 2: the monitor is released and the thread is in the wait set — WAITING. Frame 3: another thread calls `notifyAll()` and the waiter moves to the entry list — **BLOCKED**. Frame 4: it re-acquires and returns from `wait`. The hold count save/restore labelled |
| D-049 | The lost wakeup | 1.12.12, 1.26.14 | timeline | Two lanes. The notifier changes state and calls `notify()` at t1; the waiter reaches `wait()` at t2 > t1 and blocks forever. The condition variable drawn as holding no memory. Beneath: the fixed version with a state variable checked in a `while` loop, the same interleaving now returning immediately |
| D-050 | `notify` can wake the wrong thread | 1.12.11, 1.12.13 | before-after | A wait set holding two producers and two consumers on one bounded stake queue. Left, `notify()`: a producer is woken when only a consumer could proceed, and the signal is gone. Right, `notifyAll()`: all wake, three re-check and go back to waiting, one proceeds. A third panel: two `Condition`s giving each predicate its own wait set, so `signal` is precise |
| D-051 | The CAS retry loop | 1.13.1, 1.13.2, 5.1.52 | flowchart | Read the current value → compute the new one → `compareAndSet` → success exits, failure loops back to the read. The `lock cmpxchg` (x86) and `LDXR`/`STXR` (AArch64) instructions named on the CAS box, and the retry edge labelled "another thread won; nothing is lost, but work is repeated" |
| D-052 | The 16 classes of `java.util.concurrent.atomic` | 1.13.5 | table | All 16 names grouped by family (scalars, arrays, field updaters, marked/stamped references, adders and accumulators). Columns: what it wraps, the compound operations it adds over `volatile`, memory cost, and when to reach for it |
| D-053 | ABA: the value is the same, the world is not | 1.13.13, 4.4.2 | step-sequence, 4 frames | A Treiber stack of pending withdrawal transactions. Frame 1: thread A reads top = node X and is descheduled. Frame 2: thread B pops X, pops Y, pushes X back. Frame 3: A's CAS on X succeeds. Frame 4: the stack now points at a node that was removed, with the lost element named. Beside it, the `AtomicStampedReference` version with the stamp incrementing 7 → 8 → 9 and the CAS failing |
| D-054 | `LongAdder` spreads one counter across cells | 1.13.16, 3.9.2, 3.9.4 | memory-layout | A `base` field plus a `Cell[]` of four `@Contended`-padded cells, each on its own 128-byte line, four threads each hashing to a different cell by `ThreadLocalRandom.getProbe()`. `sum()` drawn as base plus a walk of the cells with no lock, labelled "racy sum". Growth capped at `NCPU` |
| D-055 | The `VarHandle` access-mode taxonomy | 1.13.23 | table | Four groups as row blocks — read (`get`, `getOpaque`, `getAcquire`, `getVolatile`), write (`set`, `setOpaque`, `setRelease`, `setVolatile`), atomic update (the eight compare/exchange and getAndSet forms), numeric and bitwise. Columns: ordering supplied, atomicity, typical use, and whether application code should ever use it |
| D-056 | The four memory-ordering levels | 1.13.24, 3.7.13 | table | Rows: plain, opaque, acquire/release, volatile. Columns: atomicity, coherence, ordering with other variables, the C++11 equivalent (relaxed-without-atomicity, relaxed, acq/rel, seq_cst), the cost, and one JDK usage site |
| D-057 | The `Lock` idiom, and the one placement that matters | 1.14.2, 1.14.3 | before-after | Left: `lock.lock(); try { ... } finally { lock.unlock(); }` — correct, with the acquisition outside the try marked. Right: `try { lock.lock(); ... } finally { lock.unlock(); }` — the failed acquisition path reaching `unlock` and throwing `IllegalMonitorStateException`. A third panel: no `finally` at all, and the permanently wedged service as the symptom |
| D-058 | Barging beats fairness on throughput | 1.14.6, 1.14.7, 1.14.8, 3.5.16 | timeline | Two lanes on one axis. Fair mode: the lock is released, the queue head is unparked, two context switches elapse before it runs. Unfair mode: an arriving thread takes the momentarily-free lock immediately, and the queue head stays parked. Both hand-off costs written, and the `hasQueuedPredecessors()` call named as the entire code difference |
| D-059 | Read-write lock states, and the upgrade that deadlocks | 1.14.15, 1.14.16 | state-transition | States: free, N readers, one writer. Legal edges labelled with the acquiring call, plus the **downgrade** edge (write → read, legal, with the acquire-read-before-release-write ordering shown) and the **upgrade** edge (read → write) drawn crossed out with "self-deadlock: the writer waits for its own read lock" |
| D-060 | The `StampedLock` optimistic-read protocol | 1.14.20, 1.14.24 | flowchart | `tryOptimisticRead()` → read fields into locals → `validate(stamp)` → true returns, false falls back to `readLock()`/`unlockRead`. A side panel showing an inconsistent field pair observed before `validate` fails, with a dereference of it throwing — labelled "do not dereference, index or divide inside the optimistic body" |
| D-061 | `StampedLock`'s three traps in one picture | 1.14.22, 1.14.23, 1.14.26 | table | Rows: reentrancy (self-deadlock), ownership (any thread may unlock any stamp; deserializes unlocked), `newCondition()` on `asReadLock()`/`asWriteLock()` (`UnsupportedOperationException`), stamp recycling after ~1 year. Columns: what the reader assumes from `ReentrantReadWriteLock`, what `StampedLock` does, the symptom |
| D-062 | The park permit does not accumulate | 1.14.27, 3.6.1, 3.6.2 | step-sequence, 3 frames | Frame 1: `unpark(t)` before `park()` — the permit is stored, `park` returns immediately. Frame 2: two `unpark`s then two `park`s — the first returns, the second blocks, because there is at most **one** permit. Frame 3: the three ways `park` returns — spuriously, on interrupt without clearing the flag, on timeout — each requiring a re-check |
| D-063 | Latch versus barrier versus phaser | 1.15.8, 1.15.14, 5.1.42 | table | Rows: `CountDownLatch`, `CyclicBarrier`, `Phaser`. Columns: one-shot or reusable, who counts down, fixed or dynamic parties, a barrier action, arrival index returned, what breaks it, the recovery, and the QuizStakes use (start gate for a load test, phase barrier for a payment run, dynamic registration for operator sessions) |
| D-064 | The two latch shapes | 1.15.2, 1.15.3, 2.12.3 | before-after | Left, start gate: `new CountDownLatch(1)`, N worker threads awaiting, main counting down once so all start together. Right, completion gate: `new CountDownLatch(n)`, main awaiting, each worker counting down **in a `finally`**. The missing-`finally` failure drawn as main hanging forever |
| D-065 | A broken barrier stays broken | 1.15.6 | state-transition | States: intact, tripping, broken. Edges: a participant interrupted, a participant timing out, the barrier action throwing — all leading to broken, and every other participant receiving `BrokenBarrierException`. Only `reset()` returns to intact |
| D-066 | The concurrent collection inventory | 1.16.3, 1.16.23, 2.6.4 | table | One row per class across all 15. Columns: ordering, bounded, null policy, read cost, write cost, iterator model, blocking behaviour, lock count, allocation per element, and the one QuizStakes situation it is right for |
| D-067 | Three iterator-consistency models | 1.16.4, 1.16.5, 2.1.6 | before-after | The same concurrent modification applied under three iterators. Fail-fast: `modCount` mismatch and `ConcurrentModificationException` thrown, best-effort labelled. Weakly consistent: traversal continues, the change may or may not be seen, each element visited at most once. Snapshot: the array captured at iterator creation, later changes invisible, `remove` throwing `UnsupportedOperationException` |
| D-068 | Copy-on-write costs O(n) per write | 1.16.17, 1.16.18, 1.16.20 | cost-curve | Total copies against number of appends, showing the O(n²) curve for a loop of `add`, with the arithmetic for 2.8M appends written out. A second series shows read cost as a flat lock-free line. The listener-registry fit labelled on the low-write end of the axis |
| D-069 | Views, copies and snapshots | 1.16.24, 2.6.10, 2.6.11 | table | Rows: `keySet()`, `values()`, `entrySet()`, `Collections.unmodifiableList`, `List.copyOf`, `toArray()`, a CoW iterator, `subList`. Columns: view or copy, writes through, thread-safe, reflects later changes, and the distinct bug each mistake produces |
| D-070 | Why `ConcurrentHashMap` forbids null | 1.16.7, 1.16.8 | before-after | Left, a nullable map: `get(k)` returns null, and the caller cannot tell "absent" from "mapped to null"; the `containsKey`-then-`get` disambiguation shown racing and giving the wrong answer. Right: null rejected at `put` with `NullPointerException`, and `getOrDefault` as the intended API |
| D-071 | `computeIfAbsent` runs under the bin lock | 1.16.11, 3.8.19 | step-sequence, 3 frames | Frame 1: the bin head locked and a `ReservationNode` (hash `RESERVED = -3`) installed. Frame 2: the mapping function runs while the lock is held — a blocking call inside it drawn stalling every other writer to that bin. Frame 3: recursion — same key throws `IllegalStateException: Recursive update`; a different key in the same bin deadlocks. A note: on a plain `HashMap` the same pattern corrupted the table before Java 9 |
| D-072 | The four `BlockingQueue` method families | 1.17.2 | table | The canonical 4 × 4 grid: insert / remove / examine down the side; throws (`add`, `remove`, `element`), special value (`offer`, `poll`, `peek`), blocks (`put`, `take`, n/a), times out (`offer(e,t,u)`, `poll(t,u)`, n/a) across the top. Every cell filled with the exact method signature |
| D-073 | One lock versus two | 1.17.5, 1.17.6, 1.17.7, 3.10.7, 3.10.8 | memory-layout | Left, `ArrayBlockingQueue`: `items[]` ring with `takeIndex`/`putIndex`/`count`, one `ReentrantLock`, `notEmpty` and `notFull` conditions — producer and consumer contending on one lock. Right, `LinkedBlockingQueue`: linked nodes with `putLock`/`takeLock` at opposite ends and an `AtomicInteger count` in the middle, labelled "head and tail are independent, so two locks are possible; a ring's are not" |
| D-074 | `SynchronousQueue` has capacity zero | 1.17.9 | before-after | Left, the mental model of a queue with a buffer. Right, the reality: a rendezvous point where every `put` waits for a `take`; `size()` = 0, `peek()` = null, `isEmpty()` = true printed as constants. Labelled "a hand-off, not storage", with `newCachedThreadPool` named as its user |
| D-075 | The producer–consumer assembly | 1.17.16, 1.17.17, 2.7.8 | flowchart | Producers → bounded queue (capacity written) → N consumers, with: per-task try/catch inside each consumer, interrupt handling, poison pills equal to the consumer count, and the shutdown order numbered (stop accepting → drain → pill → await with a deadline → force). Withdrawal transactions feeding a `PaymentRun` used as the payload |
| D-076 | The executor interface stack | 1.18.2, 1.18.3 | hierarchy | `Executor` (`execute`) → `ExecutorService` (lifecycle plus `submit`/`invokeAll`/`invokeAny`, `close` since Java 19) → `ScheduledExecutorService`. Each box lists its declared methods; `AutoCloseable` drawn as a second parent of `ExecutorService` and dated Java 19 |
| D-077 | `submit` swallows the exception, `execute` does not | 1.18.8, 5.1.77 | before-after | Left, `execute(runnable)` that throws: the `UncaughtExceptionHandler` fires and the stack trace prints. Right, `submit(callable)` that throws: the throwable is captured into the `FutureTask`, the handler never fires, `afterExecute` sees null, and the exception is visible only through `get()` — with the "nobody calls get" path ending in silence |
| D-078 | The `ThreadPoolExecutor` submission algorithm | 1.19.2, 1.19.3, 3.10.15, 5.1.71 | flowchart | Four numbered decisions in exact order: (1) `workerCount < corePoolSize` → add a worker **even if idle threads exist**; (2) else `workQueue.offer(task)`; (3) else add a worker up to `maximumPoolSize`; (4) else `handler.rejectedExecution`. The **double-check after enqueue** drawn as its own box: re-read `ctl`, remove the task if shut down, add a worker if the pool became empty |
| D-079 | Both `Executors` factories fail, in opposite directions | 1.19.4, 1.19.5, 5.1.72, 5.1.73 | before-after | Left, `newFixedThreadPool(8)`: a `LinkedBlockingQueue` of capacity `Integer.MAX_VALUE` (2 147 483 647 written out), step 3 unreachable, `maximumPoolSize` marked dead code, and the heap filling with queued stake settlements until `OutOfMemoryError`. Right, `newCachedThreadPool`: `SynchronousQueue` capacity 0 plus `maximumPoolSize = Integer.MAX_VALUE`, one new OS thread per un-handed-off task, ending in `unable to create native thread` |
| D-080 | The four rejection policies | 1.19.7, 1.19.8, 1.19.9 | table | Rows: `AbortPolicy`, `CallerRunsPolicy`, `DiscardPolicy`, `DiscardOldestPolicy`. Columns: what happens to the task, what happens to the caller, does it give backpressure, behaviour after `shutdown()` (`CallerRunsPolicy` silently discards), and the failure mode (`DiscardOldestPolicy` with a priority queue drops the highest-priority item) |
| D-081 | Deriving the pool size from Little's law | 1.19.17, 2.4.1–2.4.3 | step-sequence, 3 frames | Frame 1: Little's law stated. Frame 2: the CPU-bound case, `N = cores + 1`, with the "+1" justified by page faults. Frame 3: the I/O-bound case worked for QuizStakes — 8 cores, U = 0.9, W = 100 ms, C = 2 ms → `8 × 0.9 × 51 = 367`, every step of the arithmetic shown, and the conclusion "367 platform threads is the argument for virtual threads" |
| D-082 | Thread-pool starvation by task dependency | 1.19.20, 1.19.21, 4.8.6 | step-sequence, 3 frames | A single-thread executor. Frame 1: task A runs and submits task B to the same pool. Frame 2: A blocks on `B.get()`. Frame 3: B sits in the queue forever with no worker available — permanent deadlock, invisible to the JVM's detector. A second panel generalises to N threads and N such tasks |
| D-083 | `scheduleAtFixedRate` versus `scheduleWithFixedDelay` | 1.20.2, 5.1.79 | timeline | Two lanes on one axis with a period of 5 s and one run overrunning to 12 s. Fixed rate: firings at t0+5, t0+10, t0+15 with the overrun causing back-to-back catch-up runs, drawn bunched. Fixed delay: each run starting 5 s after the previous **completion**, drawn evenly. Every firing time written |
| D-084 | One exception cancels every future run | 1.20.3, 1.20.4, 3.10.20, 5.1.78 | flowchart | `ScheduledFutureTask.run` → `runAndReset` → the body throws → `setException` completes the future exceptionally → `setNextRunTime` and the re-enqueue are **skipped** → nobody calls `get()`, so nothing is logged. The try/catch-inside-the-body fix drawn as the loop that keeps the re-enqueue reachable |
| D-085 | The `CompletableFuture` method map | 1.21.5, 1.21.7, 1.21.10 | hierarchy | Four families as branches: transformation (`thenApply`/`thenAccept`/`thenRun`/`thenCompose`), combination (`thenCombine`/`thenAcceptBoth`/`runAfterBoth`/`applyToEither`/`acceptEither`/`runAfterEither` — 18 methods with the ×3 noted), exception (`exceptionally`/`exceptionallyCompose`/`handle`/`whenComplete`), completion (`complete`/`completeExceptionally`/`obtrude*`). Each leaf carries its arity and the release it arrived in |
| D-086 | Which thread runs the callback | 1.21.3, 1.21.4, 2.1.8, 5.1.84 | table | Rows: `thenApply`, `thenApplyAsync`, `thenApplyAsync(executor)`, plus a row for "the stage was already complete when you attached". Columns: which thread actually runs it (the completing thread, a common-pool thread, your executor, **the calling thread**), whether it is deterministic, and the failure mode when the body blocks |
| D-087 | `thenApply` versus `thenCompose` | 1.21.6, 5.1.83 | before-after | Left: `thenApply` with a function returning a `CompletableFuture`, producing `CompletableFuture<CompletableFuture<Money>>`, the nesting drawn. Right: `thenCompose` flattening to `CompletableFuture<Money>`. Labelled with the `map`/`flatMap` correspondence and a QuizStakes chain: look up the client, then fetch their wallet |
| D-088 | Which stages run when stage 2 of 5 fails | 1.21.11, 2.8.11 | step-sequence, 4 frames | One five-stage chain over an affordability assessment, drawn four times — once each terminated by `thenApply`, `handle`, `whenComplete`, `exceptionally`. Each frame greys the skipped stages, shows where the `CompletionException` wrapping happens, and prints what the terminal call observes |
| D-089 | `allOf` versus `anyOf` | 1.21.8, 1.21.9, 2.8.8, 2.8.9 | before-after | Left, `allOf`: returns `CompletableFuture<Void>`, with the correct `thenApply(v -> list.stream().map(CompletableFuture::join).toList())` re-read drawn. Right, `anyOf`: returns `CompletableFuture<Object>` and completes on the **first to finish including the first to fail** — the identity call failing at 300 ms beating the watchlist succeeding at 1.4 s. "First successful" marked as absent from the JDK |
| D-090 | Exception wrapping across the async APIs | 1.21.12, 1.18.12 | table | Rows: `Future.get`, `CompletableFuture.get`, `CompletableFuture.join`, `exceptionally`, `handle`, `whenComplete`, `ForkJoinTask.join`. Columns: the wrapper type (`ExecutionException`, `CompletionException`, none), checked or unchecked, how to unwrap (`getCause()`), and what a cancelled future throws |
| D-091 | Work stealing: LIFO local, FIFO steal | 1.22.4, 1.22.5, 3.11.3, 5.1.89 | memory-layout | Two worker deques over a parallel ledger fold. The owner pushes and pops at `top` (LIFO, "freshest task, hottest cache"); the thief polls at `base` (FIFO, "biggest remaining chunk, least contention"). The single-element case where both target the same slot highlighted as the only place a CAS is unavoidable |
| D-092 | Everyone shares the common pool | 1.22.6, 1.22.7, 1.21.15, 2.13.14 | hierarchy | `ForkJoinPool.commonPool()` at the centre with parallelism `availableProcessors() − 1` (3 on a 4-core box, the arithmetic shown, plus the caller participating), and arrows in from parallel streams, `CompletableFuture` `*Async` with no executor, `ConcurrentHashMap` bulk ops, `Arrays.parallelSort`. A blocking task drawn occupying one of the three workers, with the starvation consequence labelled |
| D-093 | `ThreadLocal` lives in the Thread, not the ThreadLocal | 1.23.1, 1.23.6, 5.1.101 | memory-layout | Two `Thread` objects, each holding a `ThreadLocalMap` with `Entry` nodes. The `Entry` key drawn as a **weak** reference to the shared `ThreadLocal` object and the value as a **strong** reference to a 2 MB payload. The `ThreadLocal` collected, leaving a null key and a live value reachable from a pool thread that never dies |
| D-094 | The two halves of the thread-pool `ThreadLocal` leak | 1.23.5, 1.23.6, 1.23.8, 5.1.102 | before-after | Left, the correctness half: request A sets the security context for client 2 401 993, the pool thread is reused for request B, and B reads A's context — labelled a security incident class. Right, the memory half: the strong value accumulating across requests. The fix drawn as `try { CTX.set(v); } finally { CTX.remove(); }`, with `set(null)` marked as **not** a fix |
| D-095 | Platform thread versus virtual thread | 1.24.1, 1.24.16, 3.12.20 | memory-layout | Left: a platform thread — an OS thread, ~1 MB reserved stack outside the heap, a `Thread` object. Right: a virtual thread — a `VirtualThread` object plus a `Continuation` plus a growable heap `StackChunk`, a few hundred bytes to a few KB, mounted on a carrier that is itself a platform thread. 55k peak concurrent sessions costed both ways, and 1M × 2 KB = 2 GB written out |
| D-096 | Mounting and unmounting | 1.24.3, 3.12.5, 3.12.6, 3.12.7 | step-sequence, 4 frames | A virtual thread calling the card PSP at a 240 ms p50. Frame 1: mounted, frames on the carrier's stack. Frame 2: the blocking read calls `Continuation.yield`; live frames frozen into a heap `StackChunk` (lazy copy labelled). Frame 3: the carrier picks up a different virtual thread. Frame 4: the poller unparks it, frames thaw incrementally onto a **possibly different** carrier |
| D-097 | The carrier pool | 1.24.4, 3.12.9, 3.12.10, 2.9.9 | memory-layout | The scheduler as a `ForkJoinPool` in FIFO async mode; parallelism = `availableProcessors()`; `maxPoolSize` 256 (**verify before printing**); `jdk.virtualThreadScheduler.parallelism`, `.maxPoolSize` and the Java-21-only `.minRunnable` labelled on the boxes they control; a FIFO queue of runnable virtual threads feeding `CarrierThread`s, contrasted with the LIFO work-stealing used for parallel streams |
| D-098 | Pinning on Java 21, and JEP 491 in Java 24 | 1.24.6–1.24.10, 3.12.15, 3.12.16 | before-after | Left, Java 21: a virtual thread blocking inside a `synchronized` block in a tracing library; `Continuation.yield` fails, the carrier is held, other virtual threads queue behind it, and with parallelism 1 the app stalls; `-Djdk.tracePinnedThreads=full` output shown. Right, Java 24: the monitor owned by the virtual thread, monitor-blocked as a yield point, the carrier freed. A version-trap banner: the flag is **removed** in 24; native/JNI/FFM frames still pin |
| D-099 | Never pool virtual threads; bound with a `Semaphore` | 1.24.13, 1.24.14, 1.24.18, 2.9.4 | before-after | Left: a fixed pool of virtual threads — the anti-pattern, with the pool re-imposing the limit that virtual threads removed. Right: one virtual thread per task plus a `Semaphore(20)` in front of the connection pool, showing the bound moved to the resource that actually has one. The 20-connection ceiling and the queue that forms at the semaphore both labelled |
| D-100 | A structured scope is a tree with a lifetime | 1.25.1–1.25.3, 3.12.21 | hierarchy | `AssessmentService` forking two subtasks under one scope — the identity vendor (p50 900 ms) and the watchlist provider (p50 1.4 s) — each a virtual thread inside the `try`-with-resources boundary they cannot outlive. Beside it the unstructured version with two orphan threads escaping the block, still holding their connections |
| D-101 | `ShutdownOnFailure` versus `allOf` | 1.25.4, 1.25.9, 2.8.13 | timeline | Two lanes on one time axis. Lane 1, `ShutdownOnFailure`: the watchlist call fails at 1.4 s, the identity call is interrupted, `join()` returns, `throwIfFailed()` rethrows with a stack trace that names the parent. Lane 2, `allOf`: the same failure, the identity call still running past the block, marked orphan, and a stack trace showing only the completing thread |
| D-102 | `Subtask` states and the illegal calls | 1.25.5, 1.25.6 | state-transition | States `UNAVAILABLE`, `SUCCESS`, `FAILED` with the transitions caused by `fork`, completion, failure and `shutdown`. Illegal edges labelled with their exceptions: `get()` before `join()` → `IllegalStateException`; fork/join/close from a non-owner thread or an out-of-LIFO-order close → `StructureViolationException` |
| D-103 | `ScopedValue` versus `ThreadLocal` | 1.25.11–1.25.16, 2.11.9, 5.1.114 | table | Rows: mutability, lifetime, how a child thread gets it, cost of inheritance, cleanup required, can a callee set it for its caller, works across a pool boundary, final in which release. Columns: `ThreadLocal`, `InheritableThreadLocal`, `ScopedValue`. The JEP 506 (final in 25) and JEP 487 (`runWhere` removed in 24) dates stated |
| D-104 | The deadlock cycle and the four Coffman conditions | 1.26.1–1.26.5, 5.1.92, 5.1.93 | before-after | Left: `transfer(accountA, accountB)` and `transfer(accountB, accountA)` racing, drawn as a two-node wait-for cycle with each thread's held and wanted lock labelled. Right: the `System.identityHashCode` ordering fix, including the **tie lock** for the hash-collision case. A legend maps each of the four Coffman conditions to the fix that breaks it |
| D-105 | Deadlock, livelock, starvation, convoy | 1.26.11–1.26.13, 5.1.94 | table | Rows: deadlock, livelock, starvation, lock convoy, missed signal. Columns: is any thread running, does CPU rise, what the thread dump shows, the root cause, the fix, and the QuizStakes symptom (a wedged `PaymentRun`, a poison message redelivered forever, a rare writer never running, every settlement serialising behind one slow holder) |
| D-106 | What the deadlock detector cannot see | 1.26.15, 1.26.18, 1.26.19, 5.1.96 | table | Rows: monitor cycle, `ReentrantLock` cycle (ownable synchronizers), `Semaphore` permits, bounded queue, thread-pool task dependency, class-initialisation lock, database lock, distributed lock. Columns: found by `jstack`, found by `findDeadlockedThreads()`, found by `findMonitorDeadlockedThreads()`, and how you detect it instead. A footer: the JVM detects but never breaks a deadlock |

## Part 2 diagrams

| # | Diagram | Syllabus leaf | Type | Must show |
|---|---|---|---|---|
| D-107 | The master cost table | 2.1.1 | table | One row per primitive operation, all 21 named in the leaf. Columns: uncontended cost, contended cost, worst case, blocks, allocates, context-switches. Every cost quoted from the latency ladder, not adjectives |
| D-108 | The latency ladder | 2.1.2 | cost-curve | A single logarithmic axis from 1 ns to 1 ms with every rung marked and labelled: L1 1 ns, L2 4 ns, L3 15–40 ns, cache-line transfer 100+ ns, main memory 80–100 ns, uncontended CAS 10–20 ns, contended CAS 100+ ns, park/unpark 1–10 µs, platform thread creation 50–200 µs, virtual thread creation ~1 µs. Marked "order of magnitude, not measured constants" |
| D-109 | The memory-footprint table | 2.1.3 | table | Rows: platform thread, virtual thread, `ReentrantLock` (~48 B broken down), `AtomicLong` (16 B), `LongAdder` with N cells (N × 128 B), `ConcurrentHashMap.Node` (32 B), `ArrayBlockingQueue`, `LinkedBlockingQueue` per element. Columns: heap bytes, off-heap bytes, the arithmetic, and the count at which it matters for QuizStakes |
| D-110 | The five progress guarantees | 2.1.5, 1.13.4, 5.1.53 | table | Rows: blocking, obstruction-free, lock-free, wait-free (bounded), wait-free (population-oblivious). Columns: the guarantee stated precisely, a JDK example, a counter-example, and what a thread being descheduled mid-operation does to the others |
| D-111 | The escalation ladder for "make this safe" | 2.1.7, 2.3.12 | decision-tree | Root: "can you not share it?" descending through confinement → immutability → a single atomic → a concurrent collection → one lock → hand-rolled lock-free. Each rung labelled with cost, and the last rung carrying the warning "this is where you need jcstress" |
| D-112 | The lock word is the bottleneck before the body is | 2.2.1, 2.2.2 | memory-layout | Four cores each with an L1 line holding the lock word, and the line ping-ponging between them on every acquisition — the invalidation arrows drawn and counted. The critical-section body drawn as the only part doing work, with acquisition + release + coherence traffic shaded as overhead |
| D-113 | Splitting versus striping | 2.2.3–2.2.6 | before-after | Left: one `state` lock over `Account` guarding both restrictions and balances. Middle, splitting: one lock per independent invariant. Right, striping: N locks keyed by `hash % N` over one structure, with the note that `size()`/`clear()`/rehash must take **all** of them in a fixed order |
| D-114 | The contention cliff | 2.2.9, 2.2.11, 2.2.13 | cost-curve | Throughput against thread count for one global lock: rising to a peak, flat, then falling. The 8-thread and 64-thread points labelled, σ and κ fitted, and Amdahl's ceiling for a 5 % critical section (20×) drawn as a dashed asymptote |
| D-115 | Uncontended locks are not slow | 2.2.10, 5.1.28 | table | Rows: uncontended `synchronized` (thin), uncontended `ReentrantLock`, elided lock, contended `synchronized` (inflated), contended `ReentrantLock`, CAS, `LongAdder`. Columns: cost, what dominates it, whether the JIT can remove it, and the sentence a candidate should say instead of "locks are slow" |
| D-116 | `synchronized` versus `ReentrantLock` | 2.3.1, 1.14.29, 5.1.34 | table | Eight rows: simplicity, exception safety, timed acquire, interruptible acquire, fairness option, multiple conditions, instrumentation, virtual-thread pinning. Columns: `synchronized` on Java 21, `synchronized` on Java 24+, `ReentrantLock`. The pinning row carries the JEP 491 split explicitly |
| D-117 | Where a read-write lock actually wins | 2.3.4, 1.14.18, 5.1.38 | cost-curve | Throughput against read fraction from 50 % to 99.9 %, three series: `ReentrantLock`, `ReentrantReadWriteLock`, `StampedLock` optimistic. The crossover marked at roughly 90 % reads, and a second axis note that the critical section must be long enough to amortise the shared-count CAS |
| D-118 | Fairness costs an order of magnitude | 2.3.13, 1.14.7 | cost-curve | Acquisitions per second against thread count for fair and unfair `ReentrantLock`, with the 10–100× gap labelled, and a second panel showing the tail-latency distribution where fairness wins |
| D-119 | The four-parameter interaction matrix | 2.4.7, 2.4.8 | table | Rows: the sensible combinations of core size, max size, queue capacity and rejection policy. Columns: what the configuration *means* as a policy, what it does under a burst, what it does under sustained overload, and which QuizStakes workload it suits |
| D-120 | Queue depth is latency you cannot see | 2.4.5, 2.4.6, 2.4.14 | cost-curve | Added latency against queue depth for a 50 ms service: a 1000-deep queue adding up to 50 s before the first rejection, the arithmetic written out. Two series for a short and a long queue, with p99 marked on both, and queue time versus execution time named as the two metrics to export |
| D-121 | `availableProcessors()` in a container | 2.4.11, 2.4.12, 1.19.18, 5.2.51 | before-after | Left: an 8-core host reporting 8. Right: the same JVM under a 0.5-CPU cgroup quota reporting **1**, with `-XX:ActiveProcessorCount` shown as the override. Beneath, every consumer of that number listed — common pool, virtual-thread scheduler, Netty, Tomcat, Reactor, G1 workers — all mis-sizing together |
| D-122 | Five ways to count, and when each wins | 2.5.1, 2.5.2, 5.1.129 | table | Rows: `int` + `synchronized`, `AtomicInteger`, `LongAdder`, `ConcurrentHashMap.merge`, a per-thread counter summed at read. Columns: exact instantaneous read, write throughput at 1/4/16/64 threads, memory, and the verdict for the 3,400/sec settlement counter |
| D-123 | The `AtomicLong`/`LongAdder` crossover | 2.5.2, 1.13.20 | cost-curve | Throughput against writer count with two series, crossing at roughly 2–4 writers, `AtomicLong` collapsing above it and `LongAdder` scaling. A third series shows `LongAdder.sum()` cost rising with the cell count. JMH result shape labelled as the source |
| D-124 | One `AtomicReference` to an immutable snapshot | 2.5.6, 2.5.7 | before-after | Left: two atomics holding `cashAvailable` and `bonusAvailable` separately, with an interleaving that observes an inconsistent pair. Right: one immutable `WalletSnapshot` record swapped by a single `compareAndSet`, with the retry loop and the per-update allocation both labelled |
| D-125 | Choosing a concurrent collection | 2.6.1–2.6.8, 1.16.23 | decision-tree | Root: "does it need ordering?" branching through bounded/unbounded, read/write ratio, blocking or not, and index access. Every leaf names one class, and the index-access leaf ends in "there is no concurrent `List`" with the three workarounds |
| D-126 | The three concurrent `Set` options | 2.6.7 | table | Rows: `ConcurrentHashMap.newKeySet()`, `ConcurrentSkipListSet`, `CopyOnWriteArraySet`. Columns: `contains` cost (O(1) / O(log n) / **O(n)**), `add` cost, ordering, iterator model, and the situation each is right for |
| D-127 | The four backpressure mechanisms | 2.7.1, 2.7.2, 2.7.3 | table | Rows: block the producer, run on the producer (`CallerRunsPolicy`), shed, spill to disk. Columns: what it converts overload into, when it works, when it does not (blocking an HTTP request thread just moves the queue into the socket backlog), and the metric that proves it is happening |
| D-128 | A multi-stage pipeline makes the bottleneck visible | 2.7.5, 2.7.4 | flowchart | Three stages of withdrawal processing, each with its own bounded queue (capacities written) and its own pool (sizes written), and the slowest stage's queue drawn full. `drainTo` batching shown at the consumer with the batch size and the amortised lock acquisition labelled |
| D-129 | Total order needs one consumer; per-key order does not | 2.7.7 | before-after | Left: one consumer preserving total order over settlements, throughput capped at one thread. Right: a hash partition on `ClientId` feeding N consumers, order preserved per client, throughput scaling with N. Kafka's partition model named as the same idea |
| D-130 | Every async stage is a thread hop | 2.8.3, 2.8.4 | timeline | One chain of five `*Async` stages over an affordability assessment, with each hop drawn as a queue push plus a possible unpark, and the accumulated overhead written. Beside it the same chain with the cheap transformations left non-async, running inline on the completing thread |
| D-131 | Context does not follow a stage hop | 2.8.5, 2.11.1–2.11.5 | before-after | Left: MDC trace id set on the request thread, lost on the first `thenApplyAsync`, and the log line printed with an empty trace id. Right: the three fixes drawn — a decorating `Executor`, Micrometer `ContextSnapshot`, and `ScopedValue` plus a structured scope — each showing where the copy happens |
| D-132 | The virtual-thread migration checklist | 2.9.1, 2.9.13, 2.9.14 | flowchart | Ordered gates: audit `synchronized` on blocking paths (Java 21 only) → audit `ThreadLocal` caches → add a `Semaphore` at every bounded downstream → re-size the connection pool → re-point monitoring at in-flight tasks → enable behind a runtime flag per workload. Each gate names the library class most likely to fail it (JDBC driver, connection pool, tracing agent, logging appender, object pool) |
| D-133 | Removing the pool removed the rate limiter | 2.9.4, 1.24.18, 5.1.111 | before-after | Left: a 200-thread pool implicitly capping concurrent database work at 200. Right: virtual threads with no pool, 14 000 concurrent sessions all reaching a 20-connection pool, the queue forming at the connection pool instead — with the `ulimit -n` file-descriptor ceiling drawn as the second new bound |
| D-134 | The `ThreadLocal` cache regression under virtual threads | 2.9.3, 1.23.10, 5.2.39 | before-after | Left, platform pool: 200 threads, 200 cache initialisations. Right, virtual threads: one per task, **443 267** initialisations for the same workload, both numbers printed, no exception thrown, and GC pressure named as the only symptom. Labelled "`ThreadLocal` as context, never as cache" |
| D-135 | When delegation is valid and when it is not | 2.10.2, 2.10.3 | before-after | Left, valid: a class whose only invariants are the delegate's, forwarding to a `ConcurrentHashMap`. Right, invalid: two thread-safe fields `lower` and `upper` with the constraint `lower <= upper`, and the interleaving that violates it with both individual operations succeeding. The single-lock fix drawn beneath |
| D-136 | Thread safety of common JDK types | 2.10.15 | table | Rows: `String`, `StringBuilder`, `StringBuffer`, `SimpleDateFormat`, `DateTimeFormatter`, `Random`, `ThreadLocalRandom`, `SecureRandom`, `BigDecimal`, `ArrayList`, `HashMap`, `LocalDate`. Columns: thread-safe, why or why not (`SimpleDateFormat`'s mutable `Calendar` field named as the actual culprit), contention behaviour, and the modern replacement |
| D-137 | The five context-propagation mechanisms | 2.11.2, 2.11.3, 2.11.10 | table | Rows: manual copy, decorating `Runnable`/`Callable`, decorating `Executor`, Micrometer `ContextSnapshot`, `ScopedValue` + structured concurrency. Columns: works across a pool, works across a structured scope, cleanup required, what it cannot do, and the Spring/OpenTelemetry equivalent |
| D-138 | A jcstress litmus test, read | 2.12.7, 2.12.8, 3.7.7 | table | The store-buffering (Dekker) case with its two actors, and all four outcomes `(0,0)`, `(0,1)`, `(1,0)`, `(1,1)`. Columns: permitted by sequential consistency, permitted by the JMM, observed on x86, observed on AArch64, jcstress classification (`ACCEPTABLE` vs `ACCEPTABLE_INTERESTING`), and the fix |
| D-139 | What each verification tool can and cannot find | 2.12.1, 2.12.11, 3.13.12 | table | Rows: unit test, stress test, jcstress, JMH, ErrorProne `@GuardedBy`, SpotBugs detectors, `ThreadMXBean` watchdog, JFR, async-profiler, thread dump. Columns: finds a lost update, finds a deadlock, finds a data race, finds contention, finds a leak, runs in CI |
| D-140 | `nanoTime` is the only correct deadline basis | 2.13.3, 2.13.4, 3.6.8 | before-after | Left: `currentTimeMillis() >= deadline` with an NTP step backwards, and the timeout firing hours late (or immediately). Right: `System.nanoTime() - deadline >= 0`, monotonic, and overflow-safe — with the subtraction form contrasted against the broken `nanoTime() >= deadline` comparison |
| D-141 | Every primitive's distributed analogue | 2.14.1–2.14.6 | table | Rows: `synchronized`, `ReentrantLock`, `AtomicLong`, CAS, `CountDownLatch`, `volatile`, single-writer confinement, `ScheduledExecutorService`. Columns: the in-JVM guarantee, the distributed replacement (Redis/ZooKeeper/etcd lock, DB sequence or `INCR`, a `@Version` column, a ZooKeeper barrier, a consistent read, leader election, ShedLock), and what guarantee is lost |
| D-142 | Why a distributed lock needs a fencing token | 2.14.3 | timeline | One lane per client plus one for the storage. Client 1 acquires the lease, GC-pauses past expiry, client 2 acquires, then client 1 wakes and writes — the corrupting write drawn. Beneath: the same sequence with monotonically increasing fencing tokens 33 and 34, and the storage rejecting the stale token |
| D-143 | The concurrency version timeline, Java 5 → 25 | 2.15.1–2.15.16 | timeline | One axis with a mark per release. Each mark lists what arrived and what left: `j.u.c` and JSR-133 at 5, fork/join at 7, `CompletableFuture`/`StampedLock`/`LongAdder`/new CHM at 8, `VarHandle`/`Flow` at 9, cgroup awareness at 10, biased locking disabled at 15, virtual threads preview at 19, `Thread.stop` removed at 20, virtual threads final at 21, JEP 491 at 24, scoped values final at 25. Removals drawn in a separate lane below the additions |
| D-144 | The deprecation graveyard | 2.15.16, 1.3.14 | table | Rows: `Thread.stop`, `suspend`, `resume`, `countStackFrames`, `ThreadGroup` management, biased locking, `Timer`, `finalize`-based pool shutdown, `sun.misc.Unsafe` memory access, `AtomicXxxFieldUpdater`. Columns: deprecated in, disabled in, removed in, what happens if you call it today, and the replacement |

## Part 3 diagrams

| # | Diagram | Syllabus leaf | Type | Must show |
|---|---|---|---|---|
| D-145 | The object header on 64-bit HotSpot | 3.1.1, 3.1.8 | memory-layout | A `Reservation` instance drawn byte by byte: 8-byte mark word, 4-byte compressed klass pointer, the fields in HotSpot's size-class order (long, int, short, byte, oop), and padding to the 8-byte boundary. Totals of 12 B with compressed oops and 16 B without, both written |
| D-146 | The mark word is multiplexed | 3.1.2, 3.1.3, 3.1.4 | table | Rows: neutral/unlocked, lightweight (stack-locked), inflated (monitor), marked/forwarded during GC. Columns: the low tag bits (`01`, `00`, `10`, `11`), what the remaining bits hold (identity hash + age, a `BasicLock` pointer, an `ObjectMonitor` pointer, a forwarding pointer), and what transition gets you there. **Verify the encoding against the HotSpot wiki before printing** |
| D-147 | Compact object headers shrink the lock space | 3.1.6, 3.2.13 | before-after | Left: the 96–128-bit header with the klass pointer separate. Right: the 64-bit compact header with the compressed klass pointer folded into the mark word, the monitor pointer no longer fitting, and the `ObjectMonitorTable` side map drawn. 10–20 % heap reduction and the release dates (experimental 24 / default 25) labelled |
| D-148 | The three locking states, and the fourth that is gone | 3.2.1, 3.2.14, 3.2.15 | state-transition | States: unlocked → lightweight (stack-locked) → inflated, with the transition triggers on each edge. Biased locking drawn as a **greyed-out, crossed-through** fourth state annotated "JEP 374, disabled in Java 15, later removed — do not describe this in an interview as current" |
| D-149 | The displaced header | 3.2.2, 3.2.3, 3.2.4 | step-sequence, 4 frames | Frame 1: the neutral mark word. Frame 2: the thread CASes in a pointer to a `BasicLock` in its own frame, saving the old mark word there as the displaced header. Frame 3: a recursive acquisition storing a **zero** displaced header — the hold count with no counter. Frame 4: unlock CASing the displaced header back, and the failure path when the lock inflated while held |
| D-150 | Inside an `ObjectMonitor` | 3.2.6, 3.2.7, 3.2.8, 3.2.9 | memory-layout | The native structure with `_owner`, `_recursions`, `_cxq`, `_EntryList`, `_WaitSet`, `_succ`, `_object`. Contenders pushed LIFO onto `_cxq`, the owner on release moving `_cxq` onto `_EntryList` and unparking `_succ`. Labelled "this is why monitor wakeup order is unspecified and unfair" |
| D-151 | What forces inflation | 3.2.5, 3.1.4, 3.1.5 | decision-tree | Four triggers as branches: another thread contends the stack lock; `wait()` is called and a wait set is needed; `System.identityHashCode` must be stored in the mark word; a JVMTI or monitor-inspection operation demands a real monitor. Each leaf shows the resulting mark-word state and the cost |
| D-152 | Adaptive spinning, then parking | 3.2.11, 3.6.6 | timeline | One contender's path: spin for a duration derived from recent success on this monitor, then park. The CAS cost (10–20 ns) and the park/unpark round trip (1–10 µs) both marked on the axis, showing exactly why spin-then-block is the strategy. `-XX:-UseHeavyMonitors` named as the measurement switch |
| D-153 | Lock elision and lock coarsening | 3.3.1, 3.3.2, 3.3.4 | before-after | Left, elision: a `StringBuilder` proved non-escaping inside one method, with `monitorenter`/`monitorexit` struck out. Right, coarsening: three adjacent synchronized blocks on the same lock merged into one, with the note that "narrow your critical section" can be undone by the compiler — and the counter-note that elision only fires when the lock was already unnecessary |
| D-154 | The JSR-133 cookbook barrier table | 3.7.12, 3.3.7 | table | The classic grid: first operation (normal load/store, volatile load, volatile store, monitor enter/exit) down the side, second operation across the top, and the required barrier in each cell. A second column block gives what each becomes on x86-TSO (mostly no-ops) and on AArch64 (`ldar`/`stlr`/`dmb`) |
| D-155 | x86-TSO: the store buffer is the whole story | 3.3.8 | memory-layout | Two cores each with a store buffer between the core and a coherent cache. A store sitting in the buffer while a subsequent load bypasses it — the one permitted reordering. Loads shown never reordered with loads, stores never with stores. Labelled "this is why most JMM bugs are invisible on your laptop" |
| D-156 | Time to safepoint is not pause time | 3.4.1–3.4.4, 3.4.7 | timeline | One axis with three regions labelled from `-Xlog:safepoint*`: **Reaching safepoint** (TTSP), **At safepoint** (the operation), **Leaving safepoint**. Four threads arriving at different times, with one stuck in a counted `int` loop with no poll dominating TTSP. `GuaranteedSafepointInterval = 1000 ms` marked |
| D-157 | Safepoint bias in a profiler | 3.4.9, 3.4.5 | before-after | Left: a `getStackTrace`-based sampler taking every sample at a safepoint, and the hot method between polls never appearing. Right: `AsyncGetCallTrace`/async-profiler with `-XX:+DebugNonSafepoints`, sampling the real distribution. The mis-attributed frame named in both |
| D-158 | AQS anatomy | 3.5.1–3.5.6 | memory-layout | A `volatile int state`, a dummy `head`, a chain of nodes to `tail`, each node holding a thread reference, `prev`, `next` and a status field. The five template methods listed in a side box, and the state accessors `getState`/`setState`/`compareAndSetState` marked as the only legal way to touch state |
| D-159 | Why AQS sometimes walks backwards from the tail | 3.5.7 | step-sequence, 3 frames | Frame 1: a new node sets `prev` to the current tail. Frame 2: it CASes itself in as the new tail — at this instant `prev` is valid but the predecessor's `next` is still null. Frame 3: `next` is set. A traversal from head hitting the null `next` and restarting **backwards from tail** is drawn and labelled "the single most surprising line in AQS" |
| D-160 | The AQS acquire loop | 3.5.10, 3.5.11 | flowchart | `tryAcquire` → success returns; failure → am I the head's successor? retry once → else enqueue → set the predecessor's status to WAITING → `LockSupport.park` → on wake, re-check. The release path drawn beside it: `tryRelease` → unpark exactly one successor in exclusive mode |
| D-161 | The AQS node status encoding changed | 3.5.8, 3.5.9 | table | Two column groups. JDK 8–14: `CANCELLED = 1`, `SIGNAL = -1`, `CONDITION = -2`, `PROPAGATE = -3`, `0` default, with `Node` subclasses absent. JDK 14+ (what Java 21 runs): bit flags `WAITING = 1`, `COND = 2`, `CANCELLED = 0x80000000`, and `ExclusiveNode`/`SharedNode`/`ConditionNode`. Banner: most blog explanations describe the left column |
| D-162 | What `state` means, per synchronizer | 3.5.4, 5.1.49 | table | Rows: `ReentrantLock`, `Semaphore`, `CountDownLatch`, `ReentrantReadWriteLock`, `ThreadPoolExecutor.Worker`, `FutureTask`, `StampedLock`, `Phaser`, `Exchanger`, `CompletableFuture`. Columns: AQS-based or not, what the 32 bits mean (with the RW lock's 16/16 split and the 65 535 maxima spelled out), exclusive or shared mode |
| D-163 | `Condition.await` transfers a node between two queues | 3.5.14, 3.5.15, 5.1.50 | step-sequence, 4 frames | Frame 1: the thread holds the lock with hold count 2. Frame 2: `await` **fully** releases the state (saving 2), enqueues a `ConditionNode` on the condition queue, and parks. Frame 3: `signal` transfers the node to the sync queue — the thread is not woken directly. Frame 4: it reaches the head, re-acquires, and restores hold count 2 |
| D-164 | Shared mode propagates | 3.5.12 | step-sequence, 3 frames | A `Semaphore(3)` with five waiters. Frame 1: three permits released. Frame 2: the first shared acquire succeeds and returns a remaining count, which propagates the signal to the next node. Frame 3: the cascade — three readers wake, the fourth and fifth stay parked. Contrasted with exclusive mode's one unpark per release |
| D-165 | `park` on a platform thread versus a virtual thread | 3.6.4, 3.6.5, 3.6.9, 3.12.11 | before-after | Left: `LockSupport.park` on a platform thread → `Parker`/`PlatformEvent` → `pthread_cond_wait` → `FUTEX_WAIT`, two context switches costed. Right: the identical API call on a virtual thread → `VirtualThread.park` → state `PARKING` → `Continuation.yield`, no OS thread parked. Labelled "the hinge on which all of Loom turns" |
| D-166 | The five litmus tests | 3.7.7, 3.7.8 | table | Rows: store buffering (Dekker), message passing (publication), IRIW, load buffering, coherence (CoRR). Columns: the program, the surprising outcome, permitted by x86-TSO, permitted by AArch64, permitted by the JMM, and the fix. IRIW's row explains why volatile (seq_cst) is strictly stronger than acquire/release |
| D-167 | Happens-before consistency is not enough | 3.7.3, 3.7.4, 3.7.6 | flowchart | The two clauses of the happens-before consistency rule as gates a candidate execution must pass, then a second gate — the committed-action construction of 17.4.8 — rejecting the out-of-thin-air execution that passed the first. The DRF-SC conclusion drawn as the exit, with the "one racy field anywhere loses SC reasoning in principle" caveat attached |
| D-168 | Final-field semantics need no read-side barrier | 3.7.10, 3.7.11 | step-sequence, 3 frames | Frame 1: the constructor's field writes. Frame 2: the `StoreStore` emitted at the freeze — the only barrier. Frame 3: the reader's dereference, correct because of the data dependency through the reference, with the Alpha exception noted as the one architecture that needed more |
| D-169 | `ConcurrentHashMap`: table, bins, and per-bin locking | 3.8.2, 3.8.8, 3.8.9 | memory-layout | A `Node[] table` of 16 slots. An empty bin having its first node installed by `casTabAt` with no lock. A populated bin with `synchronized (f)` on the head node and a chain behind it. A third bin holding a `TreeBin`. A reader traversing a bin concurrently with a writer, labelled "`get` is lock-free: `val` and `next` are volatile, `tabAt` is an acquire read" |
| D-170 | The `ConcurrentHashMap` constants | 3.8.3, 3.8.4, 3.8.5, 5.3.2 | table | Rows: `MAXIMUM_CAPACITY = 1 << 30`, `DEFAULT_CAPACITY = 16`, `LOAD_FACTOR = 0.75f` (hard-coded), `TREEIFY_THRESHOLD = 8`, `UNTREEIFY_THRESHOLD = 6`, `MIN_TREEIFY_CAPACITY = 64`, `MIN_TRANSFER_STRIDE = 16`, `RESIZE_STAMP_BITS = 16`, `MOVED = -1`, `TREEBIN = -2`, `RESERVED = -3`, `HASH_BITS = 0x7fffffff`. Columns: value, what it controls, what happens either side of it. The `spread` function printed with the reason the sign bit is masked off |
| D-171 | `sizeCtl` is one field with four meanings | 3.8.6, 3.8.7, 3.8.12 | state-transition | Four states of the same field: `0` (default-size table not yet created), positive (next resize threshold, or the requested initial capacity before creation), `-1` (a thread is initialising, won by CAS, losers call `Thread.yield()`), negative-other (resize stamp in the high bits + resizing-thread count + 1 in the low bits). Every transition labelled with the method that causes it |
| D-172 | Resizing is cooperative | 3.8.10, 3.8.11, 5.1.70 | step-sequence, 4 frames | A 16-slot table doubling to 32. Frame 1: `transferIndex` set, stride `MIN_TRANSFER_STRIDE = 16` computed from NCPU. Frame 2: two threads each claiming a range. Frame 3: a moved bin replaced by a `ForwardingNode` with hash `MOVED = -1`; a reader following `nextTable`, a writer calling `helpTransfer`. Frame 4: the lo/hi split — each entry either stays at `i` or moves to `i + oldCap`, decided by `(hash & oldCap) == 0`, with two worked hashes |
| D-173 | Treeify at 8, untreeify at 6, only above 64 | 3.8.13, 3.8.14, 3.8.15 | step-sequence, 3 frames | Frame 1: a bin reaching 8 nodes in a table of 32 — the table **resizes** instead, because `MIN_TREEIFY_CAPACITY = 64`. Frame 2: the same at table size 64 — a `TreeBin` forms, holding both the red-black tree and the `prev`/`next` list view, with its `lockState` read-write lock labelled. Frame 3: shrinking to 6 during a resize, with the 8/6 hysteresis gap named |
| D-174 | Counting with `baseCount` plus `CounterCell[]` | 3.8.17, 3.8.18, 5.1.63 | flowchart | `addCount` → CAS `baseCount` → on failure CAS a random cell → on failure `fullAddCount`, possibly growing the array. `size()` drawn as base plus a walk of the cells with no lock, therefore approximate, and `mappingCount()` named as the `long` version for maps above `Integer.MAX_VALUE` entries |
| D-175 | What a `ConcurrentHashMap` entry costs | 3.8.23 | memory-layout | One `Node` broken into header (12/16 B) + `hash` 4 + `key` ref 4 + `val` ref 4 + `next` ref 4 ≈ 32 B, plus the 4-byte table slot, totalling ~36–40 B before the key and value objects. Scaled to a 2.4M-client restriction map with the total written out |
| D-176 | False sharing | 3.9.6, 3.9.7, 3.9.11, 4.8.5 | memory-layout | One 64-byte cache line holding `a[0]` and `a[1]`, two cores each writing one of them, and every write invalidating the other core's line — the invalidation arrows counted. Beside it `a[0]` and `a[16]` on separate lines with no invalidation. The 128-byte `-XX:ContendedPaddingWidth` default and the Apple M-series 128-byte sector both labelled, with the measured throughput ratio |
| D-177 | `@Contended` and why manual padding fails | 3.9.5, 3.9.8, 3.9.9 | before-after | Left: `Striped64.Cell` annotated `@jdk.internal.vm.annotation.Contended`, the JVM padding it to its own line. Right: the historical `long p1..p7` trick, with HotSpot's field reordering shown moving the padding away from where the author put it. `-XX:-RestrictContended` named as the flag application code would need, and advised against |
| D-178 | The Michael–Scott queue's lagging tail | 3.10.1, 3.10.2, 3.10.3, 4.4.5 | step-sequence, 4 frames | Frame 1: a dummy head and a tail pointing at the last node. Frame 2: an enqueue CASing `next` on the last node while `tail` still lags by one. Frame 3: any thread helping advance `tail`. Frame 4: a dequeued node self-linked (`p.next == p`) so a stale traverser restarts from head. `size()` marked O(n) and approximate |
| D-179 | `ThreadPoolExecutor.ctl` packs state and count | 3.10.12, 3.10.13 | memory-layout | One 32-bit `AtomicInteger` drawn bit by bit: 3 high bits of run state, 29 low bits of worker count. The five constants with their values — `RUNNING = -1<<29`, `SHUTDOWN = 0`, `STOP = 1<<29`, `TIDYING = 2<<29`, `TERMINATED = 3<<29` — and `CAPACITY = (1<<29)-1 = 536 870 911`. Labelled with why they must be read and updated atomically together |
| D-180 | The pool's run-state transitions | 3.10.14, 1.18.15, 5.1.76 | state-transition | Five states with every edge labelled by its cause: `shutdown()`, `shutdownNow()`, queue and pool both empty, `terminated()` returning. The two-phase shutdown idiom overlaid as a numbered path: `shutdown` → `awaitTermination(timeout)` → `shutdownNow` → `awaitTermination` again |
| D-181 | `Worker` is an AQS lock that means "busy" | 3.10.16, 3.10.17 | before-after | Left: `shutdownNow` interrupting a worker parked in `getTask` mid-`poll` — the bug the trick prevents. Right: `Worker extends AbstractQueuedSynchronizer`, non-reentrant, locked only while running a task, so `interruptIdleWorkers` skips the busy ones. `runWorker`/`getTask` shown choosing `poll(keepAliveTime)` versus `take()` by `allowCoreThreadTimeOut` |
| D-182 | `DelayedWorkQueue` and the leader thread | 3.10.19, 3.10.11 | memory-layout | A binary heap of `ScheduledFutureTask`s, each carrying its index-in-heap field so `remove` is O(log n) rather than O(n). One designated leader doing a timed wait on the head's delay while every other waiter waits indefinitely — labelled "avoids a thundering herd of timed waits" |
| D-183 | `FutureTask`'s state machine | 3.10.21 | state-transition | Seven states with their integer values: `NEW = 0`, `COMPLETING = 1`, `NORMAL = 2`, `EXCEPTIONAL = 3`, `CANCELLED = 4`, `INTERRUPTING = 5`, `INTERRUPTED = 6`, and every legal edge. The Treiber stack of `WaitNode` waiters drawn beside it, with `get()` parking on it |
| D-184 | `CompletableFuture` internals | 3.10.22, 3.10.23, 3.10.24, 4.7.5 | memory-layout | A `volatile Object result` holding either a value, the `NIL` sentinel for null, or an `AltResult` wrapping a throwable; and a Treiber stack of `Completion` nodes. Completion drawn popping and firing the stack, with `postComplete`'s recursion unrolling labelled as the protection against a deep chain overflowing the stack |
| D-185 | The `ForkJoinPool` queue array | 3.11.1, 3.11.2 | memory-layout | The `WorkQueue[]` with submission queues in even slots and worker queues in odd slots, an external submitter hashing into a submission queue, and one `WorkQueue` expanded to show `array`, `base` (volatile, steal end), `top` (push/pop end), `phase`, `source`, `nsteals` |
| D-186 | `ForkJoinPool.ctl` in 64 bits | 3.11.5, 3.11.6 | memory-layout | One 64-bit field split from the high end into active count `AC`, total count `TC`, and the id/version of the top of the idle-worker Treiber stack. Every pool state transition drawn as a single CAS on this field, and `signalWork` shown deciding from a `ctl` read rather than a queue scan |
| D-187 | `helpJoin` is why fork/join does not deadlock | 3.11.10, 1.22.3 | step-sequence, 3 frames | Frame 1: a worker forks the left half and computes the right. Frame 2: it reaches `join` on a task another worker stole. Frame 3: instead of blocking it executes that task, or a task the stealer is working on. Labelled "this is why `fork(); compute(); join();` is safe on a fixed-size pool, and why `fork(); fork(); join(); join();` is worse" |
| D-188 | Compensation and `ManagedBlocker` | 3.11.9, 3.11.11, 1.22.10, 1.22.12 | flowchart | A worker about to block: `tryCompensate` spawning or releasing a spare, bounded by `maximumPoolSize` (`256 + parallelism` for the common pool — **verify**), `minimumRunnable` (default 1) and the `saturate` predicate. Beside it the `ManagedBlocker` loop, `isReleasable()` then `block()`, and the unsupported path — plain blocking I/O with no compensation, starving the pool |
| D-189 | `CountedCompleter` joins without blocking | 3.11.12 | step-sequence, 3 frames | A fan-out over 95k card deposits. Frame 1: pending counts set on the completer tree. Frame 2: leaves finishing and calling `tryComplete`, decrementing their parents. Frame 3: the root's `onCompletion` firing with no thread ever having blocked. Named as what `ConcurrentHashMap` bulk ops and `java.util.stream` use |
| D-190 | A delimited continuation | 3.12.1, 3.12.2 | memory-layout | A carrier stack with the `ContinuationScope` entry frame marked, and `yield` unwinding **only** up to that frame — the frames above it copied out, the frames below untouched. `Continuation.run`, `yield(scope)` and `isDone` listed, with the class marked internal and unsupported |
| D-191 | The `VirtualThread` internal state machine | 3.12.3, 3.12.4, 1.4.12 | state-transition | The internal states `NEW`, `STARTED`, `RUNNING`, `PARKING`, `PARKED`, `PINNED`, `YIELDING`, `TERMINATED` plus the `SUSPENDED` bit, with the transitions caused by `start`, mount, `park`, `yield`, `unpark`, pinning and completion. A second column maps each internal state to the `Thread.State` a caller sees, and a note that the internal names appear only in the JSON dump |
| D-192 | Socket I/O goes through a poller, file I/O does not | 3.12.12, 3.12.13, 2.9.8 | before-after | Left: a blocking socket read implemented over non-blocking NIO plus a `sun.nio.ch.Poller` (epoll/kqueue) thread that unparks the virtual thread when the fd is ready — the carrier freed the whole time. Right: a `FileChannel` read on Linux delegated to carrier-blocking work, no io_uring integration, the carrier consumed. `jdk.pollerMode` labelled |
| D-193 | Why `jstack` cannot see a virtual thread | 3.12.18, 3.12.19, 1.24.12, 5.1.110 | before-after | Left: `jstack` walking the JVM's `JavaThread` list, an unmounted virtual thread having no `JavaThread`, and the dump showing only the handful of carriers. Right: `jcmd <pid> Thread.dump_to_file -format=json <file>` with the thread-container structure — one container per `StructuredTaskScope` or executor, parent links drawn — and the note that it omits locks and JNI stats |
| D-194 | `ScopedValue`'s binding chain | 3.12.22, 1.25.13 | memory-layout | An immutable linked `Carrier` chain per thread, one node per binding, with a nested `where(...).run(...)` adding a node rather than mutating. The small per-thread cache keyed on the scoped value's hash drawn beside it, making `get()` close to a field read. Inheritance into a structured subtask drawn as a **pointer copy**, contrasted with `InheritableThreadLocal`'s map copy |
| D-195 | A `jstack` dump, annotated line by line | 3.13.1, 3.13.3 | table | One real dump excerpt with a row per element: the header line fields (`"name" #id [tid] daemon prio os_prio cpu elapsed tid nid state`), the `java.lang.Thread.State` line, the stack frames, `- locked <0x…>`, `- waiting to lock <0x…>`, `- parking to wait for <0x…>`, the "Locked ownable synchronizers" block, and the "Found one Java-level deadlock:" section. Columns: the line, what it means, what it rules out |
| D-196 | The three dump signatures | 3.13.2, 5.1.98, 5.1.99 | table | Rows: monitor contention, pool saturation, pool idleness, deadlock, virtual-thread pinning. Columns: how many threads and in what state, the give-away stack frame, CPU usage, throughput, the next command to run, and the fix |
| D-197 | Finding the thread that is burning a core | 3.13.5, 3.13.11, 5.1.100 | step-sequence, 4 frames | Frame 1: `top -H -p <pid>` showing a hot LWP id in decimal. Frame 2: converting it to hex. Frame 3: matching `nid=0x…` in the thread dump. Frame 4: reading that thread's stack. `/proc/<pid>/task/<tid>/status` shown as the source of the voluntary/involuntary context-switch counts for the same thread |
| D-198 | JFR concurrency events and their thresholds | 3.13.6, 3.13.7, 1.24.11, 2.2.8 | table | Rows: `jdk.JavaMonitorEnter`, `jdk.JavaMonitorWait`, `jdk.JavaMonitorInflate`, `jdk.ThreadPark`, `jdk.ThreadStart`/`End`, `jdk.ThreadSleep`, `jdk.VirtualThreadStart`, `jdk.VirtualThreadEnd`, `jdk.VirtualThreadPinned`, `jdk.VirtualThreadSubmitFailed`, `jdk.ExecutorTaskSubmit`. Columns: enabled by default, default threshold (20 ms where it applies), what it proves, and what it misses at that threshold |

## Part 4 diagrams

| # | Diagram | Syllabus leaf | Type | Must show |
|---|---|---|---|---|
| D-199 | Five spin locks, compared | 4.1.1–4.1.8 | table | Rows: TAS spin lock, test-and-test-and-set, ticket lock, CLH, MCS, backoff. Columns: where each waiter spins (the shared line, the predecessor's node, its own node), coherence traffic per acquisition, FIFO fairness, space per waiter, NUMA suitability, and which one AQS derives from and why |
| D-200 | CLH versus MCS spin location | 4.1.5, 4.1.6, 4.1.7 | memory-layout | Two queues of four waiters. CLH: each spins on its **predecessor's** node flag, the implicit queue drawn through `prev` references. MCS: each spins on **its own** node flag, set by the predecessor on release, the explicit `next` chain drawn. The cache line each waiter touches highlighted in both |
| D-201 | Spin versus park, measured | 4.1.2, 3.6.6 | cost-curve | Throughput against thread count (1, 2, 8, 64) with two series each for a 100 ns and a 100 µs critical section: spin lock and `ReentrantLock`. The crossover regions shaded and labelled with why — spinning wins while the wait is shorter than a park/unpark round trip |
| D-202 | A 25-line AQS mutex | 4.2.1, 4.2.3, 4.2.4 | before-after | Left: `SimpleMutex.tryAcquire` CASing state 0→1 and `tryRelease` setting 0. Right: the reentrant version with a hold count in `state` and the owner in `setExclusiveOwnerThread`, plus the `IllegalMonitorStateException` path on foreign release. `OneShotLatch`'s shared-mode variant shown as a third panel with state 0 = closed, 1 = open |
| D-203 | Three bounded queues, three signalling schemes | 4.3.1–4.3.3 | table | Rows: `synchronized` + `wait`/`notifyAll`, `ReentrantLock` + `notFull`/`notEmpty`, two locks + `AtomicInteger count`. Columns: how many waiters wake per operation, whether producers and consumers contend, allocation per element, the cascading-signal rule, and correctness obligations |
| D-204 | An SPSC ring buffer | 4.3.6 | memory-layout | A power-of-two array with padded `head` and `tail` `AtomicLong`s on separate cache lines, the mask trick `index & (capacity - 1)` printed, and the one-producer/one-consumer invariant that removes the need for CAS. Full and empty conditions written out |
| D-205 | ABA broken and fixed, in your own stack | 4.4.1, 4.4.2, 4.4.3 | before-after | Left: the hand-rolled `TreiberStack` with explicit node pooling, and the recycle sequence that corrupts it. Right: the same with `AtomicStampedReference`, the stamp shown incrementing. A third panel states why the plain, non-pooling Java version is usually ABA-safe: the GC will not reuse a node while a reference is held |
| D-206 | The mini `ThreadPoolExecutor`, version by version | 4.5.1–4.5.5 | step-sequence, 5 frames | Frame 1: N workers over one `BlockingQueue`. Frame 2: `submit` plus your own `Future` state machine. Frame 3: run state and worker count packed into one `AtomicInteger`. Frame 4: core/max sizing with `poll(keepAliveTime)` and the four rejection policies. Frame 5: `beforeExecute`/`afterExecute` and the try/catch that stops a thrown task killing its worker |
| D-207 | The one unavoidable CAS in a work-stealing deque | 4.6.1, 4.6.2 | step-sequence, 3 frames | Frame 1: `top - base > 1`, owner pops at `top` with a plain store, thief polls at `base` with a CAS, no conflict. Frame 2: `top - base == 1`, both target the same slot. Frame 3: the CAS resolving it, with the loser's retry path drawn |
| D-208 | `MiniScope`'s lifetime rules | 4.7.1–4.7.4 | state-transition | Scope states open → joined → closed, with `fork` legal only before `join`, `join` legal only on the owner thread, and `close` required in LIFO order. Illegal edges labelled with the exception each raises. The honest limitation printed: a deadline cannot stop a subtask that ignores interruption |
| D-209 | The visibility harness | 4.8.1 | before-after | The non-volatile stop flag loop that never exits, with the `-XX:+PrintCompilation` output and the hoisted C2 form beside it; then the `volatile` version exiting, with the elapsed time in both cases |
| D-210 | The lost-update harness results | 4.8.2 | table | Rows: `int`, `volatile int`, `AtomicInteger`, `synchronized`, `LongAdder`. Columns: expected final value (N × M), actual final value, elapsed time, and the one-clause reason. Run at 8 threads × 1,000,000 increments over a stake-reservation counter |
| D-211 | The backpressure harness | 4.8.11 | cost-curve | Heap usage and producer rate over time, two series: an unbounded queue (heap climbing to OOM, producer never slowing) and a bounded queue of 1,000 (heap flat, producer rate clamped to the consumer's). Both curves labelled with the moment the behaviour diverges |
| D-212 | One dump per harness | 4.8.12, 3.13.2 | table | Rows: deadlock harness, livelock harness, starvation harness, pinning harness, `ThreadLocal` leak harness. Columns: the distinguishing dump lines, the thread states, what the tool reports (`jstack` deadlock section, JFR `jdk.VirtualThreadPinned`, heap-dump `ThreadLocalMap$Entry`), and the classification a reader should reach in thirty seconds |

## Part 5 diagrams

| # | Diagram | Syllabus leaf | Type | Must show |
|---|---|---|---|---|
| D-213 | The 55-item trap index, grouped | 5.2.1–5.2.55 | table | Every one of the 55 traps as a row. Columns: the wrong belief verbatim, the symptom it produces in production, the fix, and the syllabus leaf that teaches it. Grouped by the same headings as §5.2 |
| D-214 | The numbers drill card | 5.3.2 | table | Every constant in the leaf as a row: 1 MB stack, 64 B cache line, 128 B `@Contended` padding, `TREEIFY_THRESHOLD = 8`, `UNTREEIFY_THRESHOLD = 6`, `MIN_TREEIFY_CAPACITY = 64`, `MIN_TRANSFER_STRIDE = 16`, load factor 0.75, `CAPACITY = 2^29 − 1`, common-pool parallelism `availableProcessors() − 1`, virtual-thread parallelism `availableProcessors()`, maxPoolSize 256, `common.maximumSpares` 256, `Flow.defaultBufferSize() = 256`, pinned threshold 20 ms, `GuaranteedSafepointInterval` 1000 ms, RW-lock 16/16 split (65 535), priorities 1/5/10. Columns: value, what it controls, what changes either side of it |
| D-215 | The version drill | 5.3.6, 2.15.15 | table | Rows: `synchronized` pinning, scoped values, structured concurrency, `Thread.stop`, biased locking, compact object headers, `ExecutorService implements AutoCloseable`, `Unsafe` memory access. Columns: the release, the direction of the change, the JEP number, what is true on Java 21, what is true on Java 25 |
| D-216 | The diagnosis decision tree | 5.3.5, 5.1.98, 5.1.99 | decision-tree | Root: is CPU high or low? High → is it GC, a spin loop, or a livelock retry? Low → are threads BLOCKED (contention), WAITING on a queue (idle or starved), or is the JVM idle with sockets in CLOSE_WAIT (pinning)? Every leaf names the command to run next and the expected evidence |
| D-217 | The two-minute thread-safety answer template | 5.3.10 | step-sequence, 5 frames | One frame per beat: state the invariant → state the policy (confinement, immutability, locking) → state the mechanism → state the cost → state the failure mode you accept. Worked once on "make `FundsLedger.reserveStake` thread-safe", with the actual sentences a candidate would say written in each frame |
| D-218 | The whiteboard set | 5.3.8, 5.1.116–5.1.127 | table | Rows: bounded buffer, thread-safe singleton, rate limiter, LRU cache, alternating printers, dining philosophers. Columns: the primitives it needs, the invariant, the trap the interviewer is watching for, the target time, and the section of Part 4 that builds it |

---

# OUTPUT CONTRACT

## Exact files to write

All under `src/notes/detailed/05-multithreading-concurrency/`. Create the directory and every
subdirectory. Write every file listed. The layout is **subject-major**: one folder per subject,
each holding a basics file, an intermediate file and an internals file where the syllabus has
material at that tier.

| File | Syllabus sections |
|---|---|
| `00-index.md` | The reading map, written first: one line per file below with the syllabus sections and leaf ranges it covers, the diagram ids it contains, its status, the target version, and the 1141 total |
| `foundations/01-basics-why-concurrency.md` | §1.1 |
| `foundations/02-basics-os-substrate.md` | §1.2 |
| `threads/01-basics-thread-api.md` | §1.3 |
| `threads/02-basics-lifecycle-and-states.md` | §1.4 |
| `threads/03-basics-interruption.md` | §1.5 |
| `thread-safety/01-basics-vocabulary.md` | §1.6 |
| `thread-safety/02-basics-races.md` | §1.7 |
| `thread-safety/03-class-design.md` | §2.10 |
| `synchronized/01-basics.md` | §1.8 |
| `synchronized/02-internals-header-and-mark-word.md` | §3.1 |
| `synchronized/03-internals-monitors.md` | §3.2 |
| `volatile-and-jmm/01-basics-volatile.md` | §1.9 |
| `volatile-and-jmm/02-basics-happens-before.md` | §1.10 |
| `volatile-and-jmm/03-basics-final-and-publication.md` | §1.11 |
| `volatile-and-jmm/04-internals-jit-and-barriers.md` | §3.3 |
| `volatile-and-jmm/05-internals-safepoints.md` | §3.4 |
| `volatile-and-jmm/06-internals-jmm-formally.md` | §3.7 |
| `wait-notify/01-basics.md` | §1.12 |
| `atomics/01-basics-cas-and-atomics.md` | §1.13 |
| `atomics/02-the-atomicity-decision.md` | §2.5 |
| `atomics/03-internals-striped64-and-false-sharing.md` | §3.9 |
| `locks/01-basics-explicit-locks.md` | §1.14 |
| `locks/02-choosing-a-primitive.md` | §2.3 |
| `locks/03-contention-economics.md` | §2.2 |
| `locks/04-internals-aqs.md` | §3.5 |
| `locks/05-internals-locksupport-and-os.md` | §3.6 |
| `synchronizers/01-basics.md` | §1.15 |
| `concurrent-collections/01-basics.md` | §1.16 |
| `concurrent-collections/02-the-collection-decision.md` | §2.6 |
| `concurrent-collections/03-internals-concurrenthashmap.md` | §3.8 |
| `queues/01-basics-blockingqueue.md` | §1.17 |
| `queues/02-backpressure-design.md` | §2.7 |
| `executors/01-basics-executor-framework.md` | §1.18 |
| `executors/02-basics-threadpoolexecutor.md` | §1.19 |
| `executors/03-basics-scheduled-executors.md` | §1.20 |
| `executors/04-pool-sizing.md` | §2.4 |
| `executors/05-internals-queues-and-executors.md` | §3.10 |
| `completable-future/01-basics.md` | §1.21 |
| `completable-future/02-in-anger.md` | §2.8 |
| `fork-join/01-basics.md` | §1.22 |
| `fork-join/02-internals-work-stealing.md` | §3.11 |
| `thread-local/01-basics.md` | §1.23 |
| `thread-local/02-context-propagation.md` | §2.11 |
| `virtual-threads/01-basics-the-model.md` | §1.24 |
| `virtual-threads/02-in-production.md` | §2.9 |
| `virtual-threads/03-internals.md` | §3.12 |
| `structured-concurrency/01-basics.md` | §1.25 |
| `liveness/01-basics-failures.md` | §1.26 |
| `master-tables/01-the-master-tables.md` | §2.1 |
| `utility-surface/01-the-adjacent-apis.md` | §2.13 |
| `beyond-one-jvm/01-distributed-analogues.md` | §2.14 |
| `version-delta/01-java-5-to-25.md` | §2.15 |
| `observability/01-testing-and-verifying.md` | §2.12 |
| `observability/02-internals-runtime-observability.md` | §3.13 |
| `build-it/01-locks-from-first-principles.md` | §4.1 |
| `build-it/02-building-on-aqs.md` | §4.2 |
| `build-it/03-bounded-blocking-queue.md` | §4.3 |
| `build-it/04-non-blocking-structures.md` | §4.4 |
| `build-it/05-a-thread-pool-from-scratch.md` | §4.5 |
| `build-it/06-work-stealing-and-mini-forkjoin.md` | §4.6 |
| `build-it/07-structured-concurrency-and-futures.md` | §4.7 |
| `build-it/08-diagnostic-harnesses.md` | §4.8 |
| `90-interview-basics.md` | **Part 1's wrap-up**: the summary table over §1.1–§1.26, 10 interview Q&As with full spoken-length model answers, 5 predict-the-output puzzles |
| `91-interview-intermediate.md` | **Part 2's wrap-up**: the summary table over §2.1–§2.15, 10 Q&As, 5 puzzles |
| `92-interview-internals.md` | **Part 3's wrap-up**: the summary table over §3.1–§3.13, 10 Q&As, 5 puzzles |
| `93-interview-build-it.md` | **Part 4's wrap-up**: the summary table over §4.1–§4.8, 10 Q&As, 5 puzzles |
| `94-interview-questions-and-drills.md` | §5.1 all 132 questions with full answers, §5.2 the 55-item trap index, §5.3 the drills. **Ends with Part 5's own summary table, 10 Q&As and 5 puzzles, then the file-set-wide flat `## Atomic concept checklist`** |

Diagrams go in `src/notes/detailed/05-multithreading-concurrency/diagrams/`, flat, named
`D-NNN-short-slug.svg`.

If any single file becomes unwieldy, **split it further** (`04-internals-aqs-a.md`,
`04-internals-aqs-b.md`, …) and register the new files in `00-index.md`. Splitting is always
preferred to cutting content. Never merge files to reduce the count. §1.10 (26 leaves), §1.13 and
§1.14 (29 each), §3.8 and §3.10 (24 each), and §5.1 (132 questions) are the most likely to need
splitting.

## Required header on every file except `00-index.md`

```
# 05 Multithreading and Concurrency — <subject> — <tier> (<syllabus sections covered>)

**Target version: Java 21 LTS.** | **Part <n> of 5** | [Index](../00-index.md)
Previous: [<title>](<relative path>) · Next: [<title>](<relative path>)
```

Files at the topic root (`90`–`94`) link the index as `[Index](00-index.md)`.

## Required footer on every file except `00-index.md`

```
---

**Leaves covered:** <explicit list or ranges, e.g. 1.14.1–1.14.29> (<count> leaves)
**Leaves deferred:** <none | leaf number + one-line reason each>
**Diagrams included:** <D-057, D-058, …>
**Target version:** Java 21 LTS
```

---

# SELF-VERIFY BEFORE REPORTING DONE

Run this checklist against your own output. Do not report completion until every box is genuinely
satisfied.

**Coverage**
- [ ] All 1141 syllabus leaves appear in the notes, or are listed in a `## Deferred` block with a reason.
- [ ] Every file's footer lists the leaves it covers, and the union across all files is all 1141.
- [ ] Every file listed in the OUTPUT CONTRACT exists, with the required header and footer.
- [ ] `00-index.md` lists every file, its syllabus sections, its leaf ranges and its diagram ids.

**Format**
- [ ] Every note file is Markdown (`.md`).
- [ ] No file was cut short for length. No "and so on", no "similar to the above", no deferred-for-space.
- [ ] No ASCII art anywhere. No inline `<svg>` anywhere.
- [ ] All 218 manifest diagrams exist as standalone `.svg` files in `diagrams/`, named `D-NNN-short-slug.svg`, each embedded with a Markdown image reference and captioned with its `D-NNN` id.
- [ ] Every SVG shows every element named in its `Must show` cell, has an explicit `viewBox` and no fixed width/height, an opaque backdrop rect, orthogonal-only edge routing, a legend, no text below 10.5px, no external font or CSS dependency, and explicit contrasting fills and strokes so it reads on light and dark backgrounds.
- [ ] Where the manifest specified a frame count, that many labelled panels exist.
- [ ] Where the manifest says `table`, a Markdown table was used and no SVG was written.
- [ ] Every two-thread interleaving diagram has a downward time axis, one lane per thread, and numbered steps.
- [ ] Every comparison of three or more things is a table.
- [ ] No emojis. No filler openers.

**Domain**
- [ ] Every example uses QuizStakes entities, status codes and numbers, taken verbatim from `# CONTEXT`.
- [ ] No `Dog`/`Animal`/`Foo`/`Bar`/`thread1`/`Person`/`Employee`/`Counter` anywhere.
- [ ] No invented status code, position name, service name or volume figure.

**Per concept**
- [ ] Every concept follows `Concept → Why it exists → How it works → SVG → Code → Gotcha`, in that order, with any inapplicable link explicitly noted in one line rather than dropped.
- [ ] Every Java snippet is complete and compiles as written, minus only imports, package declarations and pointless `main` scaffolding. No `...`, no "implementation omitted", no pseudo-code.
- [ ] All code is Java 21 idiomatic, every snippet needing `--enable-preview` on 21 says so, and every deliberately broken snippet is labelled **broken** and immediately followed by the fix.
- [ ] Only the three callout markers `**Pitfall:**`, `**Insight:**`, `**Interview:**` are used.
- [ ] Every `[TRAP]` leaf carries a `**Pitfall:**` with wrong belief, symptom and fix (~196 leaves).
- [ ] Every `[PROVE]` leaf has the argument worked through, not asserted (~223 leaves).
- [ ] Every `[SOURCE]` leaf quotes real JDK source, JEP text, JLS text or javadoc and explains every quoted line (~178 leaves).
- [ ] Every `[ASM]` leaf shows the instruction sequence and reads it instruction by instruction, or states that the sequence is quoted from a cited source rather than captured (9 leaves).
- [ ] Every `[DUMP]` leaf shows real or exactly-formatted `jstack`/`jcmd`/JFR output and reads it line by line (~26 leaves).
- [ ] Every `[NUM]` leaf states the arithmetic explicitly (~113 leaves).
- [ ] Every `[BUILD]` leaf ships complete generic compiling code, and every Part 4 section carries a "Diff vs the real one" table covering bounds and state checks, intrinsics, memory-ordering level, cancellation, fairness, serialization, iteration support, null policy, allocation strategy, and why the JDK bothers (~97 leaves).
- [ ] All 206 `[RESEARCH]` leaves were re-verified against a primary source, or the uncertainty is stated in the text.
- [ ] All 31 `[VERSION-TRAP]` leaves state both what is true in 21 and what changed.
- [ ] Every `[X-REF nn]` leaf has a self-contained mechanism paragraph before the pointer, and never sends the reader away empty-handed (~122 leaves).
- [ ] Version differences across Java 5 / 7 / 8 / 9+ / 15 / 19 / 21 / 24 / 25 are called out inline at the point of each claim.

**Verification of the flagged figures**
- [ ] `jdk.virtualThreadScheduler.maxPoolSize = 256` (1.24.4, 2.9.9, 3.12.9) was confirmed against `VirtualThread.java` at jdk-21+35 or a running JDK 21, or is explicitly marked unverified in the text.
- [ ] The `ForkJoinPool` common-pool `maximumPoolSize = 256 + parallelism` and `common.maximumSpares = 256` (3.11.9, 3.11.13) were confirmed against the `ForkJoinPool` javadoc, or are marked unverified.
- [ ] The mark-word tag-bit encoding (3.1.3) and the `ObjectMonitor` field names (3.2.7) were confirmed against the HotSpot wiki page in `# REFERENCES`, or are marked unverified.
- [ ] The post-JDK-14 AQS bit-flag constants (3.5.9) were read from `AbstractQueuedSynchronizer.java` at the jdk-21 tag, and the notes state which JDK's source is being described.
- [ ] Every `ConcurrentHashMap` constant in 3.8.3 and 3.8.4 was re-read from `ConcurrentHashMap.java`, not from a secondary article.
- [ ] The park/unpark and context-switch costs in 2.1.2 and 3.6.6 are presented as order-of-magnitude, with that stated in the text.
- [ ] Every JEP quotation was re-fetched through a mirror (`javaalmanac.io`, `bugs.openjdk.org`, `cr.openjdk.org`) before being quoted verbatim, because `openjdk.org` 403s.

**Corrections carried through**
- [ ] Calling `start()` twice is stated to throw `IllegalThreadStateException`, and the `IllegalStateException` claim in the old guide is named as a trap.
- [ ] `volatile` is explained in happens-before terms plus the store-buffer / invalidate-queue reality; the "flushes to main memory / bypasses the cache" phrasing is named as a myth that predicts the wrong performance.
- [ ] Biased locking is described as removed, and the "biased → thin → fat escalation" answer is named as obsolete.
- [ ] Pinning is dated: `synchronized` pins on 21, JEP 491 removes that cause in 24, `-Djdk.tracePinnedThreads` is removed in 24, and native/FFM frames still pin.
- [ ] Scoped values are stated as final in 25 (JEP 506) and structured concurrency as still preview (JEP 505/525/533) — not the reverse.
- [ ] The common pool's width is stated in both halves: parallelism `availableProcessors() − 1` plus the submitting thread.

**Per part**
- [ ] `90-interview-basics.md` ends Part 1 with a summary table, 10 Q&As with full spoken-length model answers, and 5 predict-the-output puzzles with the actual output (or the set of legal outputs plus the JMM justification) and an explanation.
- [ ] `91-interview-intermediate.md` does the same for Part 2.
- [ ] `92-interview-internals.md` does the same for Part 3.
- [ ] `93-interview-build-it.md` does the same for Part 4.
- [ ] `94-interview-questions-and-drills.md` does the same for Part 5, answers all 132 questions of §5.1 with the full answer rather than a hint, carries all 55 trap-index entries as wrong belief → symptom → fix, and includes all ten drills of §5.3.

**Closing**
- [ ] `94-interview-questions-and-drills.md` ends with a flat `## Atomic concept checklist`, one bullet per distinct concept across all five parts, no nesting, no headings inside it.
- [ ] Every checklist line already present in `src/topics/05-multithreading-concurrency.md` survives verbatim or expanded (5.3.1).

---

# REFERENCES

Primary sources this topic is built on. Do not invent additional URLs; if you need a fact not
covered here, verify it against the JDK 21 source, the JLS/JVMS or the javadoc and cite that.
**`openjdk.org` returned HTTP 403 to every direct fetch during the syllabus research pass**, so
every JEP below was read through search summaries plus a secondary source. Re-fetch each JEP
through a mirror before quoting its text verbatim.

**Specification and API (primary)**

- https://docs.oracle.com/javase/specs/jls/se21/html/jls-17.html — JLS 21 chapter 17: the memory model (17.4.1–17.4.9), `wait`/`notify` (17.2), `sleep`/`yield` (17.3), final-field semantics (17.5), word tearing (17.6), 64-bit non-atomicity (17.7). Source of every `[SOURCE]` leaf in §1.10, §1.11, §1.12 and §3.7
- https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/util/concurrent/package-summary.html — the `j.u.c` memory-consistency properties list (1.10.11, 1.15.16) and the weakly-consistent-iterator definition (1.16.5)
- https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/util/concurrent/locks/AbstractQueuedSynchronizer.html — AQS as a CLH-queue variant with `prev`/`next` links plus a status field, exclusive and shared modes, the five template methods. Basis of 3.5.1–3.5.12
- https://github.com/openjdk/jdk21/blob/master/src/java.base/share/classes/java/util/concurrent/locks/AbstractQueuedSynchronizer.java — the JDK 21 source itself, confirming the post-JDK-14 rewrite (bit-flag status, `ExclusiveNode`/`SharedNode`/`ConditionNode`) rather than the JDK 8 `waitStatus` encoding most blogs describe. Basis of the version trap at 3.5.9
- https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/util/concurrent/ForkJoinPool.html — the common-pool system properties `common.parallelism`, `common.threadFactory`, `common.exceptionHandler`, `common.maximumSpares` (default 256); default parallelism `availableProcessors()`; the ten-argument constructor with `corePoolSize`, `maximumPoolSize` (default `256 + parallelism` for the common pool), `minimumRunnable` (default 1), `saturate`, `keepAliveTime` (default 60 s); and the `ManagedBlocker` `isReleasable`/`block` contract. Basis of 1.22.8, §2.13, 3.11.9 and 3.11.13
- `src/java.base/share/classes/java/util/concurrent/ConcurrentHashMap.java` at the jdk-21 tag — **the source of record for every constant in 3.8.3 and 3.8.4, for `sizeCtl`, `transfer`, `TreeBin` and `addCount`; re-read it rather than trusting any article**
- `src/java.base/share/classes/java/util/concurrent/ThreadPoolExecutor.java` at the same tag — `ctl`, `execute`'s double-check after enqueue, `Worker`, `runWorker`/`getTask`, the javadoc's three queuing strategies and the `PausableThreadPoolExecutor` example
- `src/java.base/share/classes/java/lang/VirtualThread.java` at the same tag — **the source of record for the scheduler's `parallelism` and `maxPoolSize` defaults; verify before printing 256**
- https://docs.oracle.com/en/java/javase/21/core/virtual-threads.html — the scheduler, the tuning properties, the two pinning causes, `-Djdk.tracePinnedThreads`, the JFR events with their default states and the 20 ms threshold, `jcmd Thread.dump_to_file -format=json`, the never-pool rule, the semaphore guidance and the `ThreadLocal` warning

**JEPs (all 403 on direct fetch — re-read through a mirror before quoting)**

- https://openjdk.org/jeps/491 — Synchronize Virtual Threads without Pinning (Java 24). Direct fetch returned HTTP 403; content taken from the OpenJDK bug entry and the secondary reporting below, so every constant sourced this way carries `[RESEARCH]`
- https://bugs.java.com/bugdatabase/view_bug?bug_id=8338813 — the implementation bug for JEP 491
- https://openjdk.org/jeps/374 — Deprecate and Disable Biased Locking (Java 15): the complexity and safepoint-revocation rationale behind 3.2.14
- https://openjdk.org/jeps/450 — Compact Object Headers (experimental, Java 24): headers from 96–128 bits to 64 bits, klass pointer folded into the mark word. Basis of 3.1.6
- JEP 444 virtual threads (21); JEP 453 / 462 / 480 / 499 / 505 structured concurrency; JEP 446 / 481 / 487 / 506 scoped values; JEP 193 `VarHandle`; JEP 266 `Flow`; JEP 312 handshakes; JEP 471 / 498 `Unsafe` memory access; JEP 502 `StableValue`; JEP 519 compact headers by default

**Implementation and internals**

- https://wiki.openjdk.org/display/HotSpot/Synchronization+Using+The+ObjectMonitorTable — the mark-word states (neutral / stack-locked / inflated), the displaced header in the `BasicLock`, the `0b10` inflated tag, and the monitor-table redesign for compact headers. Basis of 3.1.3, 3.2.2–3.2.6 and 3.2.13
- https://arxiv.org/pdf/2102.04188 — "Compact Java Monitors": `ObjectMonitor` structure (`_owner`, `_recursions`, `_EntryList`, `_cxq`, `_WaitSet`) and inflation costs. Basis of 3.2.7–3.2.10
- https://github.com/openjdk/jdk14u/blob/master/src/java.base/share/classes/jdk/internal/vm/annotation/Contended.java — `@Contended`'s package, the `-XX:-RestrictContended` requirement, and its use in `Striped64.Cell`. Basis of 3.9.5 and 3.9.8
- https://www.baeldung.com/java-false-sharing-contended and https://alidg.me/blog/2020/5/1/false-sharing — the 64-byte cache line, the 128-byte `ContendedPaddingWidth` default, and a measurable false-sharing benchmark shape. Basis of 3.9.6–3.9.11 and the 4.8.5 harness
- https://www.baeldung.com/java-memory-layout and https://nipafx.dev/inside-java-newscast-48/ — object header sizing (12 B with compressed oops, 16 B without) and the 10–20 % heap saving from compact headers. Basis of 3.1.1 and 3.1.6
- https://bugs.openjdk.org/browse/JDK-8315740 and https://knowledge.broadcom.com/external/article?articleNumber=396719 (JDK-8330017) — two real `ForkJoinPool` failures: common-pool starvation, and the `ctl` release-count overflow at −32768 → +32767 that stopped a production pool entirely. Basis of 3.11.14–3.11.15
- https://www.besthub.dev/articles/deep-dive-into-java-8-concurrenthashmap-initialization-treeification-resizing-and-transfer-mechanics-7fedb596a324 — `sizeCtl`'s four meanings, `initTable`'s CAS-to-−1, `addCount` → `CounterCell` → `fullAddCount`, and the strided cooperative `transfer`. Use only as a pointer to the JDK source; re-read every constant from `ConcurrentHashMap.java`

**Loom internals**

- https://foojay.io/today/the-basis-of-virtual-threads-continuations/ — delimited continuations, `Continuation.yield`, and the `StackChunk` heap copy. Basis of 3.12.1–3.12.7
- https://medium.com/@nikolaykudinov/inside-java-virtual-threads-a-deep-dive-into-the-jvm-implementation-part-1-0cf6793ac3bd — `VirtualThread.runContinuation`, the mount/unmount cycle, the FIFO `ForkJoinPool` scheduler, and the poller-thread model for socket I/O. Basis of 3.12.3–3.12.12
- https://www.infoq.com/articles/virtual-threads-after-jdk24/ — production deltas for JDK 24/25: `-Djdk.tracePinnedThreads` removed, `jdk.VirtualThreadPinned` 20 ms threshold, `jcmd Thread.dump_to_file -format=json`, residual pinning (native/JNI/FFM, class loading, Linux file I/O with no io_uring), the measured `ThreadLocal` initialisation regression (200 → 443 267), downstream resource exhaustion as the dominant failure mode, and `ScopedValue.orElse(null)` no longer permitted in the finalised JEP 506 API. Basis of §2.9 and 3.12.13–3.12.17
- https://nljug.org/foojay/your-loom-app-quietly-became-a-thread-pool-again-a-field-guide-to-virtual-thread-pinning/ and https://www.javacodegeeks.com/2026/05/virtual-threads-two-years-in-production-war-stories-the-pinning-edge-cases-and-what-jdk-25-fixed.html — the all-carriers-pinned pseudo-deadlock, the CLOSE_WAIT signature, and the "jstack shows an idle JVM" diagnostic dead end. Basis of 2.9.4–2.9.6
- https://mikemybytes.com/2025/04/09/java24-thread-pinning-revisited/ and https://www.danvega.dev/blog/jdk-24-virtual-threads-without-pinning — confirmation of the JDK 24 behaviour change and the removed diagnostic flag

**Safepoints and JIT**

- https://blanco.io/blog/jvm-safepoint-pauses/ and https://www.javacodegeeks.com/2026/05/reading-jvm-safepoint-logs-without-going-mad-a-practical-stop-the-world-diagnosis-guide.html — TTSP as distinct from pause duration, `-Xlog:safepoint*`, and the causes of long TTSP. Basis of 3.4.3 and 3.4.8
- https://technology-dhami.blogspot.com/2016/11/java-vm-safepoint-for-revokebias.html — the `RevokeBias` safepoint, the historical cost JEP 374 removed. Basis of 3.4.5
- The `GuaranteedSafepointInterval` default of 1000 ms and the `-XX:+UnlockDiagnosticVMOptions -XX:GuaranteedSafepointInterval=0` override, confirmed in the safepoint-logging sources above. Basis of 3.4.4
- https://jpbempel.github.io/2022/06/22/debug-non-safepoints.html — safepoint bias in profilers and `-XX:+DebugNonSafepoints`. Basis of 3.4.9

**Lock algorithms and lock-free structures**

- https://www2.cs.sfu.ca/~tzwang/mcsg.pdf — MCS lock structure and its relationship to CLH and ticket locks. Basis of 4.1.4–4.1.7
- https://ethancornell.github.io/blog/2025/LFQ_EBR/ and https://aturon.github.io/blog/2015/08/27/epoch/ — hazard pointers versus epoch-based reclamation, and the statement that the Michael–Scott queue is what `ConcurrentLinkedQueue` implements. Basis of 3.10.1 and 4.4.3–4.4.6
- Doug Lea, "The java.util.concurrent Synchronizer Framework" (2004) — the AQS design paper behind §3.5
- The JSR-133 Cookbook for Compiler Writers (Doug Lea) — the barrier-insertion table behind 3.7.12

**Testing**

- https://openjdk.org/projects/code-tools/jcstress/ and https://github.com/openjdk/jcstress — the litmus-test harness, its purpose (JMM conformance), and the honest framing that most application developers never need it. Basis of 2.12.7–2.12.8 and 4.8.9–4.8.10

**Not found / not usable — state the uncertainty rather than inventing a number**

- A direct fetch of https://openjdk.org/jeps/491 returned HTTP 403, as did repeated attempts at the JEP index. Every JEP-derived constant in this file carries `[RESEARCH]` and must be re-verified in the write pass, ideally from the JDK release notes or the `jdk` repository rather than from secondary reporting.
- No primary source was found for a current, authoritative per-instruction cost table for park/unpark on Linux; the numbers in 2.1.2 and 3.6.6 are order-of-magnitude and must be presented as such rather than as measured constants.

