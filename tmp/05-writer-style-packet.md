# WRITER STYLE PACKET — topic 05 Multithreading and Concurrency

This file is read-only shared context for every writer on this note set. Read it in full before
writing. Your dispatch message carries your row: the file path, the syllabus leaves, the primary
concepts, the diagrams, the nav links, the example assignment and the target size. This file
carries everything that is the same for every writer.

You write exactly one file. You do not create any other file. You do not touch `00-index.md`.
You do not add a leaf that is not in your row. If you believe your row is wrong, under-scoped, or
that you cannot write it honestly, return `blocked` in your envelope rather than fixing it
yourself.

---

## Target version

**Java 21 LTS** is the baseline for every constant, signature and behaviour. Anything introduced,
changed or removed in Java 22–25 is called out inline at the point of the claim, marked
`[VERSION-TRAP]`, stating what is true in 21 and what changed.

The six version deltas that matter most across this topic:

1. `synchronized` pins a virtual thread on Java 21 — JEP 491 removes that cause in Java 24, and
   `-Djdk.tracePinnedThreads` was removed with it, so "use `ReentrantLock` instead" is a
   version-scoped answer.
2. Biased locking is **gone** — deprecated and disabled by JEP 374 in Java 15, later removed — so
   the "biased → thin → fat" escalation story is obsolete.
3. AQS was rewritten after JDK 14: bit-flag status (`WAITING = 1`, `CANCELLED = 0x80000000`,
   `COND = 2`) and `ExclusiveNode`/`SharedNode`/`ConditionNode` replaced the JDK 8 `waitStatus`
   encoding that almost every blog still describes.
4. `Thread.stop`/`suspend`/`resume` were **removed** in Java 20 and now throw
   `UnsupportedOperationException` — they are not merely deprecated.
5. Scoped values are final in Java 25 (JEP 506) while structured concurrency is still preview
   (JEP 505 → 525 → 533). Do not swap them.
6. Compact object headers: experimental in Java 24 (JEP 450), on by default in Java 25 (JEP 519),
   which also forces the monitor side-table redesign.

---

## The example domain

**Every example comes from QuizStakes**, the shared fictional domain in
`/Users/rajat.chikkodikar/Desktop/My-files/rough/src/scenario/scenario.md`. It is a regulated
skill-based betting platform: onboarding with status codes, compliance gates, restrictions, a
bonus-and-cash ledger, deposits and withdrawals, batched payment runs. That file is **read-only**
— open it for domain detail beyond what your dispatch pasted, never edit it.

**Banned outright:** `Dog extends Animal`, `Foo` / `Bar` / `Baz`, `thread1` / `thread2`,
`MyClass`, `Employee`, `Shape` / `Circle` / `Square`, `Person`, `test1`, `doSomething()`. A
throwaway name in a code block is a defect, not a style choice.

Where a concept is genuinely domain-free — a litmus test, a spin lock, a `park`/`unpark` permit —
still frame it in the domain: the shared counter is stake reservations per second, the bounded
queue holds withdrawal transactions awaiting a payment run, the lock protects a wallet's four
buckets, the two threads in the deadlock are transferring between two client accounts. Do not
bolt a betting platform onto a bit trick, but never fall back on `Foo` or `thread1`.

The domain must not become the lesson. The concept stays the subject; QuizStakes is the material
it is demonstrated on. If the example needs three paragraphs of domain setup before the concept
appears, pick a smaller slice.

### QuizStakes, reproduced

A regulated skill-based betting platform. A prospect registers, supplies personal details,
address, employment and income; is scored for affordability; accepts agreements; uploads identity
documents which an automated vendor verifies (inconclusive cases fall to human review); and on
approval the account is activated. The client deposits by card or bank transfer. A first deposit
with a valid coupon earns a bonus: **10% of the deposit, capped at 100**. Bonus money is stakeable
but never directly withdrawable. Each stake draws proportionally from bonus before cash. Winnings
credit as cash. Withdrawals go out by card (immediately, via the PSP) or by bank transfer
(batched, with operator sign-off). The Quiz Engine is a black box exposing exactly three
operations: `ReserveStake`, `SettleStake`, `VoidStake`.

**Vocabulary (use exactly these words).** Prospect (has begun registration; account shell,
every money action restricted). Client (activated account). Application (the onboarding case).
Account (created at registration, not at activation). Account shell. Wallet (client-facing view;
four buckets, two derived totals). Ledger (double-entry, sole source of truth for money). Cash
(from a deposit or a win; stakeable and withdrawable). Bonus (promotional; stakeable, never
directly withdrawable; converts to cash only by winning). Stakeable (cash available + bonus
available; derived, never stored). Withdrawable (cash available only; derived). Reserved (funds
committed to an open stake or a pending withdrawal). Rail (card deposit, bank deposit, card
withdrawal, bank withdrawal). Instrument (a specific card or bank account). Closed loop
(withdrawals return to the instrument the money came from, up to the deposited amount). Gate (a
compliance condition that must hold before a transition is permitted). Restriction (a block on a
specific client action; additive, overlapping, sourced, individually lifted). Requirement (an
outstanding document obligation). Referral (a case a machine could not decide). PaymentRun (a
batch of approved bank withdrawals with operator sign-off). Suspense (a holding position for
money received but not yet attributable).

**Services you may name:** `ApplicationGateway`, `RouterInt`, `JwtService`, `AccountOpening`,
`PersonalDetails`, `ClientAgreements`, `AssessmentService`, `AccountActivation`,
`DocumentVerification`, `DocumentRequirements`, `ScreeningService`, `ApplicationHistory`,
`AccountMaintenance`, `ClientRestrictions`, `InternalPlatforms`, `PaymentService`, `FundsLedger`,
`CardPayments`, `BankDeposits`, `BankWithdrawal`, `BonusService`, `BalanceView`, `ProfileService`,
`PendingActions`, `NotificationService`.

**Status codes (verbatim — never invent one).**

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
`SUBMITTED`, `SATISFIED`, `WAIVED`, `EXPIRED`; bonus `GRANTED`, `ACTIVE`, `CONSUMED`, `EXPIRED`,
`CLAWED_BACK`.

**Restrictions:** `DEPOSIT_BLOCKED`, `STAKE_BLOCKED`, `WITHDRAWAL_BLOCKED`, `DEPOSIT_LIMITED`,
`WITHDRAWAL_HELD`, `SOURCE_OF_FUNDS_REQUIRED`, `ALL_BLOCKED`, `SELF_EXCLUDED`, `COOLING_OFF`,
`DORMANT_FROZEN`. Sources: `SYSTEM_ONBOARDING`, `SYSTEM_COMPLIANCE`, `SYSTEM_LIFECYCLE`, `ADMIN`,
`CLIENT`. **Restriction identity is the pair (type, source), not the type alone** —
`STAKE_BLOCKED` from `SYSTEM_ONBOARDING` lifts automatically at `AA-801`; the same type from
`ADMIN` does not. `SELF_EXCLUDED` carries `reversibleByOperator = false`.

**Ledger positions:** `CLIENT_CASH_AVAILABLE`, `CLIENT_CASH_RESERVED`, `CLIENT_BONUS_AVAILABLE`,
`CLIENT_BONUS_RESERVED`, `SUSPENSE`, `PSP_RECEIVABLE`, `BANK_SETTLEMENT`, `HOUSE_REVENUE`,
`PROMOTIONAL_EXPENSE`, `FEES`, `CHARGEBACK_LOSS`. Derived, never stored: **Stakeable** =
`CASH_AVAILABLE + BONUS_AVAILABLE`; **Withdrawable** = `CASH_AVAILABLE`; **Total** = all four
client buckets. The win/void asymmetry, the domain's sharpest edge: reserved bonus returns as
**cash** on a win, as **bonus** on a void, and goes to `HOUSE_REVENUE` on a loss.

**Bonus rules (exact numbers):** grant 10% of the first deposit capped at 100; first deposit only,
one per identity, valid coupon; coupon valid 14 days from registration; expiry 30 days from grant,
unspent reverses to `PROMOTIONAL_EXPENSE`; no wagering requirement; stake consumption
`min(BONUS_AVAILABLE, 10% of stake)` with the remainder from cash; the bonus portion **rounds
down** to the minor unit and cash covers the remainder; clawback takes unspent bonus first and
sends the shortfall to `PROMOTIONAL_EXPENSE`. The canonical rounding example: a stake of **3.33**
splits as **0.33 bonus + 3.00 cash**; rounding the other way gives 0.34 + 3.00 = 3.34, which
creates money.

**Types you may declare.** Value types: `Money(BigDecimal amount, Currency currency)`, `ClientId`,
`ApplicationId`, `AccountId`, `PersonId`, `RoundId` (each wrapping a `UUID`),
`IdempotencyKey(String value)`, `StatusCode(domain, phase, disposition, variant)`,
`Jurisdiction(country, subdivision)`, `AgreementRef(documentId, version)`,
`LimitSet(dailyDeposit, maxStake, monthlyLoss)`, `StakeSplit(Money bonusPortion, Money
cashPortion)` — **invariant: the two sum exactly to the stake** — `Verdict(outcome, reason,
decidedAt, decidedBy)` as a sealed hierarchy (`DocumentVerdict`, `ScreeningVerdict`,
`ReviewVerdict`, `WealthVerdict`), `RestrictionKey(RestrictionType type, RestrictionSource
source)`. Aggregates: `Application`, `Account`, `Restriction`, `LedgerEntry`, `Movement`,
`Position`, `Reservation`, `Bonus`, `PaymentIntent`, `WithdrawalTransaction`, `PaymentRun`,
`InstrumentVerification`, `DocumentRequirement`, `GateSet`, `ReviewCase`. Exceptions you may
define: `InsufficientFundsException`, `RestrictedActionException`, `IllegalTransitionException`,
`LedgerImbalanceException`, `BonusIneligibleException`.

**Numbers you may quote — take the figure, never invent one.**

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

Little's law is worked with 1,200 stake reservations/sec and the PSP's 240 ms p50 (288 concurrent
tasks) and again with the 11 s p99 (13,200). Pool sizing uses 8 cores, 90% utilisation, a 100 ms
downstream wait and 2 ms of compute. A contended counter is 3,400 settlements/sec through one
`AtomicLong`. A `CopyOnWriteArrayList` disaster is 2.8M appends. A virtual-thread footprint
argument uses 55k peak concurrent sessions.

---

## How a concept is written

### Which concepts get the full treatment

Not every concept carries the full sequence. **Sort first.**

A **primary concept** is one that satisfies any of: it has a cost or performance claim; it has a
diagram in the manifest; it has a sibling it must be chosen against; a reader could plausibly be
asked about it for five minutes in an interview. Your row names its primary concepts explicitly.

Primary concepts get **all eight beats, in order, with a `###` heading**.

A **supporting fact** is everything else — a convenience method, a constant, an API shape with no
tradeoff. Supporting facts get **three beats only**: mechanism, gotcha if one exists, and the
boxed definition. Three to ten lines. No diagram, no separate heading, no manufactured analogy.
Forcing the full sequence onto a supporting fact produces exactly the filler the house rules ban.

### The eight beats

For primary concepts. They need not be labelled, but they must be present and in this sequence.

1. **Mental model first.** Open with the picture: what shape this thing is, what it is doing
   under the hood, the one analogy that makes the rest fall out. Not a definition. Never open
   with "X is a class in `java.util.concurrent` that…".
2. **Why it exists** — the problem it solves, and what people did before it.
3. **When to reach for it, and when not.** Explicit. Name the sibling that wins in the cases
   where this one loses.
4. **How it works** — the mechanism, at the depth the tier demands. In an INTERNALS file this is
   a source walk with real named constants and their values.
5. **The diagram, embedded inline in the flow.** The `D-NNN` from your row, embedded at the point
   in the explanation where the reader needs the picture — immediately after the mechanism it
   illustrates, before the code. Never collected into a gallery at the end, never pushed to an
   appendix, never merely linked as "see diagram D-007". Embed form, exactly:

   ```
   ![D-042 — The ThreadPoolExecutor submission algorithm, in order](../diagrams/D-042-tpe-submission.svg)

   **D-042** — The `ThreadPoolExecutor` submission algorithm, in order.
   ```

   Files at the topic root (`90`–`94`) use `diagrams/D-NNN-slug.svg` with no `../`.
   **Never inline `<svg>` in the Markdown. Never ASCII art.** Where your row says a `D-NNN` is
   `table` type, render a Markdown table at that point instead of an embed, still captioned
   `**D-NNN** — …`, and list the id in the footer's `**Diagrams included:**`.
6. **A minimal concrete example** — real, complete, runnable code from the QuizStakes domain.
   Full method bodies, real generics, real edge cases. Strip only imports, package lines, and
   empty `main` scaffolding. **No `...` elisions, no "implementation omitted", no pseudo-code.**
   Quoted JDK source may be excerpted to the relevant lines, but every line quoted must then be
   explained. Where a snippet needs `--enable-preview` on Java 21 (structured concurrency, scoped
   values), say so on the snippet. Where a snippet is deliberately broken to demonstrate a bug,
   label it **broken** on the fence line and give the fixed version immediately after.
7. **The gotcha.**
8. **The definition, last** — one crisp sentence, boxed as a blockquote, now that the reader has
   earned it.

If a beat genuinely does not apply, say so in one line rather than dropping it silently.

### Hierarchy before details

Any file that introduces a family opens with the hierarchy — as a diagram where one is in your
row, as a table otherwise. The reader sees the map before the streets.

### Tradeoff, not fact

"`ConcurrentHashMap` is O(1) lookup" is documentation. Notes say: O(1) lookup, **but** no
cross-bucket atomicity, **and** each bin degrades to O(log n) after treeify — which is precisely
why a `ConcurrentSkipListMap` still earns its place when you need sorted iteration. Every
performance claim carries its cost and its escape hatch.

### Tables for siblings

Three or more things doing a similar job get a comparison table, always. Never three paragraphs
describing them one after another.

### Callouts

Exactly three markers, bolded, inline where they belong. Do not invent others.

- `**Pitfall:**` — the wrong belief, the symptom it produces, the fix.
- `**Insight:**` — the non-obvious mechanism that makes the rest click.
- `**Interview:**` — how this is actually asked, and the one-line answer.

Every syllabus leaf tagged `[TRAP]` must carry a `**Pitfall:**`.

### Syllabus tag obligations

The tags on your leaves are instructions, not decoration:

- `[PROVE]` — work the argument through on the page. Do not state the result.
- `[SOURCE]` — quote the real JDK source, JEP text, JLS text or javadoc (short excerpt) and
  explain every quoted line.
- `[BUILD]` — ship complete, compiling, generic code.
- `[TRAP]` — carry a `**Pitfall:**`: wrong belief, symptom, fix.
- `[RESEARCH]` — re-verify against a current primary source before writing. If you cannot verify
  it, say so in the text rather than asserting it.
- `[VERSION-TRAP]` — state what is true in 21 and what changed.
- `[X-REF nn]` — one self-contained mechanism paragraph here, then point to guide nn. Never send
  the reader off empty-handed.
- `[NUM]` — state the number or byte arithmetic explicitly, with the arithmetic shown.
- `[ASM]` — show the generated machine code or the barrier and read it instruction by
  instruction. Where you cannot produce real disassembly, state the instruction sequence from a
  cited source and say it is quoted, not captured.
- `[DUMP]` — show real `jstack` / `jcmd` / JFR output and read it line by line. Where you cannot
  capture a live dump, reproduce the exact documented format and say so.

---

## Research protocol

Search when it changes the answer:

- **Search:** version-sensitive behaviour, API changes and deprecations, current best practice,
  library and runtime versions, benchmark figures, anything where a specific number appears in the
  notes. Verify rather than recall. Every `[RESEARCH]` leaf and every version-dependent constant
  must be checked against a current primary source. **Prefer the JDK release notes or the
  `openjdk/jdk` repository on GitHub — `openjdk.org` JEP pages returned HTTP 403 during the prompt
  build.** Mirrors that work: `javaalmanac.io`, `bugs.openjdk.org`, `cr.openjdk.org`,
  `github.com/openjdk/jdk`.
- **Do not search:** stable fundamentals. How a hash table works, what amortised O(1) means, why
  red-black trees rebalance.

**Present park/unpark and context-switch costs as order-of-magnitude, explicitly stated as such,
never as measured constants.** No authoritative per-instruction table exists.

**When research is still insufficient after searching**, do not invent and do not quietly soften
the claim. Instead:

1. Mark the claim inline as `**Unverified:**` with what you could not confirm.
2. Record it in a `## Open questions` block at the foot of your file.
3. Report every one of them on the `unverified:` line of your return envelope.

If a missing fact blocks the whole file — the section cannot be written honestly without it — do
not write the file. Return `blocked` in your envelope, naming what is missing and what would
settle it.

---

## Every file ends the same way

In this order, after the body and before the footer.

1. `## Pitfalls` — **wrong-then-right**, one entry per pitfall:

   ```
   ### Assuming a second start() throws IllegalStateException

   **Wrong**
   <code showing the belief in action, and the output that surprises>

   **Right**
   <code that actually gets the guarantee, and why>

   **Why people believe it:** <the plausible-sounding reason>
   ```

2. `## Cheat sheet` — a one-screen table. Everything on it must be recallable at a glance the
   night before an interview. No prose.

3. `## Self-test` — **5 to 10 questions** (this range is checked mechanically; fewer than 5 or
   more than 10 fails), answers folded below each:

   ```
   **Q3.** Why does a notified thread go to BLOCKED before RUNNABLE?

   <details><summary>Answer</summary>

   <the full answer, not a hint>

   </details>
   ```

4. `## Deferred` — only if you could not cover a leaf, with the leaf number and a one-line
   reason. An empty `## Deferred` block is the expected outcome, so omit the heading entirely
   when every leaf is covered.

5. `## Open questions` — only if you have `**Unverified:**` claims.

---

## Header and footer on every note file

Header, exactly this shape:

```
# 05 Multithreading and Concurrency — <subject> — <tier> (<syllabus sections covered>)

**Target version: Java 21 LTS.** | **Part <n> of 5** | [Index](../00-index.md)
Previous: [<title>](<relative path>) · Next: [<title>](<relative path>)
```

Files at the topic root (`90`–`94`) link the index as `[Index](00-index.md)`.

Your dispatch gives you the finished `Previous:` / `Next:` line — use it verbatim. The first file
in the set omits `Previous:` entirely and the last omits `Next:`. Never emit a link to a file that
does not exist, and never write `Previous: none`.

Footer, exactly this shape:

```
---

**Leaves covered:** <explicit list or ranges, e.g. 1.14.1–1.14.29> (<count> leaves)
**Leaves deferred:** <none | leaf number + one-line reason each>
**Diagrams included:** <D-057, D-058, …>
**Target version:** Java 21 LTS
**Lines:** <count>
```

---

## House rules

- No emojis. No filler — no "let's dive in", "great question", "in this section we will", "as we
  all know", "it's worth noting". Lead with content.
- **No line limit on completeness.** Never truncate, never write "and so on", never write
  "similar to the above", never defer a concept for space.
- **600 lines is a firm cap and your row has been sized to fit inside it.** Aim for the target
  your row gives you; landing anywhere in 400–600 is a good outcome.

  The way you fit is **sorting, not cutting**. Your row names two to six primary concepts: those
  and only those get the eight beats. Every other leaf in your row is a supporting fact and gets
  three beats in three to ten lines — mechanism, gotcha if one exists, boxed definition. No
  separate `###` heading, no manufactured analogy, no diagram, no "why it exists" paragraph. A
  first draft that overruns is almost always a draft that gave eight beats to a supporting fact.

  Never drop a leaf, never thin a primary concept's mechanism or code, never cut below five
  self-test questions, and never write "and so on" to save room. Only return `blocked` if, after
  sorting correctly, all of your leaves genuinely still cannot be covered honestly inside 600
  lines. Do not split on your own.
- Markdown only. Java code is Java 21 idiomatic: records, sealed interfaces, pattern-matching
  `switch`, text blocks, `var` sparingly, modern Spring Boot 3.x where Spring appears at all.
- A table for any comparison of three or more things.
- Every syllabus leaf in your row appears in the file, or in the `## Deferred` block with a
  reason.
- Two corrections that must never be carried forward: calling `start()` twice throws
  **`IllegalThreadStateException`**, not `IllegalStateException`; and `volatile` does not "flush
  to main memory" — that is the cache-flush myth, and MESI already keeps caches coherent. State
  visibility in happens-before terms, then describe the store-buffer / invalidate-queue reality.

---

## Return envelope

Return only this, nothing else:

```
path: <relative path written>
lines: <wc -l>
leaves: <ids covered>
diagrams: <D-NNN embedded>
unverified: <none | one line per unverified claim>
blocked: <none | what is missing and what would settle it>
```
