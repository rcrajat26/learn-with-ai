## The example domain

**Every example comes from QuizStakes**, the shared fictional domain in
`src/scenario/scenario.md`. It is a regulated skill-based betting platform:
onboarding with status codes, compliance gates, restrictions, a bonus-and-cash
ledger, deposits and withdrawals, batched payment runs.

**Banned outright:** `Dog extends Animal`, `Foo` / `Bar` / `Baz`, `thread1` /
`thread2`, `MyClass`, `Employee`, `Shape` / `Circle` / `Square`, `Person`,
`test1`, `doSomething()`. A throwaway name in a code block is a defect, not a
style choice — re-dispatch the file.

**Where to take each thing from:**

| What you need | Where in `src/scenario/scenario.md` |
|---|---|
| A scenario for a concept | §15 Example Bank — 15.1 concurrency, 15.2 distributed/consistency, 15.3 data & storage, and the sections after |
| Vocabulary and status codes | §3 Glossary and §3.1 Status Code Index — `AA-610`, `DEP-301 CAPTURED`, `CLIENT_BONUS_RESERVED` |
| Services and their boundaries | §4 Service Catalog, §5 High-Level Architecture |
| Entities, fields, relationships | Appendix C — value types, aggregates, layering |
| Any number — volume, latency, size, lifetime | Appendix A. **Take the figure; never invent one.** |
| Money, buckets, ledger invariants | §11 Funds & Ledger Model |
| Flows worth walking end to end | §12 Client Payment Flows, §8 Onboarding Journey |
| Infrastructure or deployment naming | Appendix B |

**Rules that keep it honest:**

- Take names, status codes, and numbers **verbatim**. A reader who has met
  `CLIENT_BONUS_RESERVED` once must meet the same spelling every time.
- Reach for the Example Bank row that matches the concept before inventing a
  scenario. If §15 has no row for it, extend the domain in the same register —
  a new operation on an existing service, not a new universe.
- **Do not edit `src/scenario/scenario.md`.** It is read-only for this pipeline.
- The domain must not become the lesson. The concept stays the subject; QuizStakes
  is the material it is demonstrated on. If the example needs three paragraphs of
  domain setup before the concept appears, pick a smaller slice of the domain.
- **Where the concept is genuinely domain-free** — a language mechanic, a JVM
  constant, a bit trick — a minimal snippet with honestly-named locals is fine.
  Do not bolt a betting platform onto `Integer` caching. What is never fine is
  `Foo` and `thread1`.
- §1's reading-order table maps topic areas to the sections worth reading first.
  Use it when choosing a row's example assignment.

---

## The domain, reproduced in full (from the topic prompt's `# CONTEXT`)

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
