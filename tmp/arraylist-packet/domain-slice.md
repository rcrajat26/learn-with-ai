# QuizStakes — the slice this note set uses

Taken verbatim from the domain reference. **Use these spellings and these numbers
exactly.** Do not invent an entity, a status code, or a figure. Do not go looking
for the source file — everything the set needs is here.

QuizStakes is a regulated skill-based betting platform: onboarding with status
codes, compliance gates, restrictions, a bonus-and-cash ledger, deposits and
withdrawals, batched payment runs.

## Entities you may use

| Type | Shape | Notes |
|---|---|---|
| `Money` | `amount: Decimal`, `currency: Currency` | **Never floating point.** Value equality. Expressed as a record. Deliberately not `Comparable` across currencies. |
| `LedgerEntry` | `id`, `movementId`, `position: PositionRef`, `direction: DEBIT\|CREDIT`, `amount: Money`, `postedAt` | **Append-only. No setters, ever.** A record. |
| `Movement` | `id`, `idempotencyKey`, `entries: List<LedgerEntry>`, `reason: MovementReason`, `postedAt` | Entries sum to zero; atomic as a unit. **A movement has 2 to 4 entries.** |
| `Position` | `accountId?`, `type: PositionType`, `balance: Money`, `version: int` | Client positions never negative. Four bucket types: `CASH_AVAILABLE`, `CASH_RESERVED`, `BONUS_AVAILABLE`, `BONUS_RESERVED`. |
| `Restriction` | `key: RestrictionKey`, `clientId`, `scope`, `reason`, `appliedBy: Actor`, `appliedAt`, `expiresAt?`, `reversibleByOperator: boolean`, `state` | Additive and overlapping. Composite identity: `RestrictionKey` is `(type, source)`. |
| `PaymentRun` | `id`, `state`, `openedAt`, `signedOffBy: Actor?`, `authorisedBy: Actor?`, `fileRef?`, `itemIds: List<Id>` | A batch of approved bank withdrawals. `signedOffBy` must differ from `authorisedBy`. |
| `WithdrawalTransaction` | `id`, `accountId`, `instrumentId`, `amount: Money`, `state`, `runId?` | Lives in the rail's own schema. |
| `Application` | `id`, `clientId`, `status: StatusCode`, `version: int`, `jurisdiction`, `acceptedAgreements: Set<AgreementRef>` | Only legal transitions. |
| `Reservation` | `id`, `accountId`, `split: StakeSplit`, `purpose: STAKE\|WITHDRAWAL`, `externalRef`, `state`, `expiresAt` | |
| `StakeSplit` | `bonusPortion: Money`, `cashPortion: Money` | **Invariant: the two sum exactly to the stake.** |
| `ClientId` / `AccountId` / `MovementId` | `value: UUID` | Distinct types, not bare strings. |

## Status codes you may use — exact spellings

Onboarding / application: `AO-100`, `AO-400`, `AA-610`, `AA-700`, `AA-800`
Card deposit: `DEP-301 CAPTURED`, `DEP-400`
Bank deposit: `BDP-100`, `BDP-200`, `BDP-300`, `BDP-400`
Ledger / bonus states: `CLIENT_BONUS_RESERVED`, `LEDGER_POSTING_PENDING`

Numbered code structure: `XX-Nnn` where `XX` is the owning domain, `N` the phase,
and the middle digit is the disposition — `0` in progress, `1` success/advanced,
`5` referred to a human, `9` failed/blocked.

Restriction type names (use short forms in diagrams if space is tight):
`CASH_OUT_BLOCKED`, `STAKE_BLOCKED`, `DEPOSIT_BLOCKED`, `LOGIN_BLOCKED`,
`BONUS_BLOCKED`.

## Numbers — take these verbatim, never invent one

| Metric | Value |
|---|---|
| Registered clients | 2.4M |
| Monthly active clients | 380k |
| Concurrent sessions | 14k steady, 55k peak |
| Ledger entries / day | ~19.8M |
| Ledger entries / year | ~7.2B |
| Ledger row size | ~180 bytes |
| Sustained ledger write rate | 230/sec |
| Peak ledger write rate | 13,600/sec |
| Entries per movement | 2 (bonus grant) to 4 (stake reserved, stake won, card deposit, withdrawal) |
| Stake reservations | 2.8M/day, 1,200/sec peak |
| Stake settlements | 2.8M/day, 3,400/sec burst |
| Card deposits | 95k/day, 40/sec peak, avg value 65 |
| Card withdrawals | 11k/day, 12/sec, avg value 180 |
| Bank withdrawals | 7k/day, batch, avg value 260 |
| Restriction records | ~300 bytes, 38k/day applied and lifted |
| Bank statement file | 40k records; **500k at month end**; 1/day at 06:00 |
| Bank payout file | 1.8k records, 4/day |
| `ApplicationHistory` records | ~400 bytes, 2.6M/day |
| Document images | 2–6 MB, 24k uploads/day |
| Applications reaching `AO-400` / day | 7.2k steady, 24k peak |
| `AA-700` manual review rate | 11% of submissions, 19% peak |
| Operators on shift | 40 steady, 90 peak |

**Derived figure this set uses:** at ~19.8M ledger entries/day and 4 entries per
movement, that is ~4.95M movements/day, each holding a `List<LedgerEntry>`.

## Scenarios worth reaching for

| Concept | Scenario |
|---|---|
| Race condition | Client with 100 cash available submits a 100 stake and a 100 withdrawal at the same instant. Both read, both pass, both reserve. |
| Lost update | Two operators open the same `AA-700` case; both save a decision; the second overwrites. |
| Read–write asymmetry | Balance read on every screen, written only on movement. |
| Backpressure | A month-end file of 500,000 movements against workers that cannot keep up. |
| Producer–consumer | Bank deposit file ingestion produces records; matching workers consume them. |
| Composite read problem | "Show me all my withdrawals" spans two rail schemas and must be merged, ordered and paginated. |
| Reconciliation | Rebuild a day's entries and compare against the rail's own record. |
| Caching | The agreement cache is small, hot, and changes rarely — an LRU map. |
| Two read models | `BalanceView` is narrow and hot, read on every screen and every stake preview; `ProfileService` is wide and cold. **Neither is authoritative.** |

## Layering rule, if a file needs architectural framing

| Layer | Holds |
|---|---|
| Edge | Request shaping, token verification, validation of *form* |
| Application | Use-case orchestration, transaction boundary, idempotency check |
| Domain | Aggregates, state machines, invariants. **No framework, no IO.** |
| Ports | Interfaces the domain needs (`PspPort`, `IdvPort`, `RestrictionPort`) |
| Adapters | Vendor clients, repositories, publishers, consumers |

## Language-expression choices the domain already committed to

- `Money`, `LedgerEntry`, `StakeSplit` and all ids are **records**.
- `Verdict` is a **sealed interface plus records**, for exhaustive pattern matching.
- Bare-name machine states are **enums**.
- `Movement.entries` is an **immutable list** — append-only means no mutation.
- `Restriction` sets are keyed `Map<RestrictionKey, Restriction>` because the composite key is the identity.
- `InsufficientFundsException` is unchecked, or a result type — a refused withdrawal is expected business flow.

## The rule that keeps examples honest

The domain must not become the lesson. The concept stays the subject; QuizStakes
is the material it is demonstrated on. If an example needs three paragraphs of
domain setup before the concept appears, pick a smaller slice. Where a concept is
genuinely domain-free — a JVM constant, a bit trick — a minimal snippet with
honestly-named locals is fine. What is never fine is `Foo`, `thread1`,
`Dog extends Animal`, `MyClass`, `Employee`, `Shape`/`Circle`/`Square`, `Person`,
`test1`, or `doSomething()`.
