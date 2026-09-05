# IG Payments — Domain Model

**Version:** v1 (draft) · **Compiled:** September 2026
**Source:** Recollection-based knowledge capture, structured through guided elicitation.
**Author's remit:** ~3.5 years in the IG payments domain, developer, team of 7–8 engineers.

---

## 0. How to read this document

This document serves three purposes, and different sections matter for each:

| Purpose | Read |
|---|---|
| **Interview / experience showcase** | §1, §4 (flows you led), §11 (contribution ledger), §10 (improvement thinking) |
| **Team onboarding** | §1–§9 in order |
| **Architecture reference / handover** | §3 (estate), §5 (cross-cutting), §4 (flows), §8 (infra), §9 (data & state) |

**Confidence markers used throughout:**

- 🟢 **Confirmed** — first-hand knowledge, high confidence
- 🟡 **Believed** — recalled but not verified; check before relying on it
- 🔴 **Unknown / out of remit** — deliberately recorded as a boundary, not a gap
- ❓ **Open question** — listed in §12 for follow-up

---

## 1. Domain scope

### 1.1 What payments owns

Everything that moves money **into**, **out of**, and **between** client accounts at IG.

- **Money in (deposits)** — card, bank transfer, PayPal, Apple Pay, domestic fast-payment rails, ACH
- **Money out (withdrawals)** — push-to-card, bank payout, PayPal
- **Money between** — inter-account transfers across a client's products, including currency conversion for bookkeeping
- **Supporting concerns** — payment instrument storage and verification, PSP configuration and integration, BIN intelligence, inbound bank file ingestion, upfront crediting, GDPR data purge

### 1.2 What payments does *not* own

Recording these boundaries is as important as recording the estate — most production confusion happens at these seams.

| Concern | Owner |
|---|---|
| Ledger and client account balances | **Ledger Service team** (payments fires and forgets) |
| Available-to-withdraw balance | **Central order server** |
| KYC, account opening, account activation | Account opening domain |
| Token issuance (CST) | Client security application |
| Token issuance (XST, JWT) | SSO service |
| FX rate sourcing | Central rates application (revised daily) |
| Reconciliation of settlement | **AutoRec** + payments operations |
| Refunds (unattributable money) | Payments operations, manual |
| Fraud / sanctions blocking | Payments operations, manual flagging |
| Edge, routing, load balancing | Akamai + separate infrastructure team |
| Managed file transfer to bank SFTP | MFT / GoAnywhere team 🟡 |
| PSP credential entry UI (Hydra) | Separate internal tooling team |

**Consequence worth internalising:** payments is an *orchestration and integration* domain, not a system of record for money. The ledger is external. This shapes almost every failure mode in §10.

### 1.3 Legal entities and products

**Entities:** IG JP (Japan), IG US (USA), IG AU (Australia), IG GB (UK), IG FR (France), IG DE (Germany) — 🟡 list may be incomplete.

**Products (account types):** IGCFD (CFD), IGSTK (stockbroking), IGFNO (futures & options), IGCRY (crypto).

A single client holds **multiple account IDs**, one per product. This matters everywhere: PayIDs are issued per account ID, bank file references carry an account ID, and inter-account transfer exists precisely because of this fan-out.

### 1.4 Payment method availability by market

Availability is **country-driven**, with a **priority ordering** per country determining display order in the UI.

| Market | Deposit methods | Withdrawal methods |
|---|---|---|
| UK, Germany, France | Card, bank, PayPal, Apple Pay | Card (CFT), bank |
| USA | ACH (Plaid-verified), card 🟡 | Card, bank |
| Australia | Card, **PayID** (fast payments) | Card, bank (incl. Westpac for IGCRY) |
| Japan | **Bank only** — quick bank deposit via BJP | **Bank only** |

Notable constraints: Japan has no card support at all. Some countries prohibit **credit** cards (debit only), enforced via BIN type checks. Some countries do not have 3DS2 enabled by default.

---

## 2. Business flow at a glance

```
DEPOSIT
  Client → FE-Payins (deposit options) → picks method
        → Payments Gateway (auth + route)
        → method application (validate, limits, risk)
        → external provider (PSP / aggregator / bank)
        → confirmation (webhook OR redirect OR file)
        → ledger posting (async, fire-and-forget)
        → email notification (async, AMQ)

WITHDRAWAL
  Client → FE-Payins → instrument must be VERIFIED
        → available-to-withdraw checked (central order server)
        → CARD: CardPayments → PSP → near-instant (CFT)
        → BANK: queued → ops payment run → check 1 → check 2
                → authorisation → bank file → SFTP → IG's bank → client
```

---

## 3. Application estate

18 applications. Contribution column reflects the author's personal involvement.

| # | Application | Responsibility | Platform | Contribution |
|---|---|---|---|---|
| 1 | **Payments Gateway (PG)** | Front controller. Authenticates inbound requests, performs role checks, routes to method applications by URI resource. Serves deposit-options config. Ingress for PSP webhooks. | DC 🟡 | **Contributor** |
| 2 | **Card Payments** | Card deposits and withdrawals. Own DB (transactions, `card_token`). Limits, risk, BIN and name validation. Channels: ECOM, MOTO, CFT. | DC 🟡 | **Contributor** |
| 3 | **Bank Deposits** | Japan-only quick bank deposit via BJP aggregator. Config, initiate, redirect handling, file reconciliation, manual deposit. | **AWS (Tokyo)** — Lambda, DynamoDB | **Rebuilt end to end (led)** |
| 4 | **Bank Withdrawal** | Bank payout requests, ops payment run, dual sign-off, bank file generation. | DC 🟡 | **Contributor** (IGCRY/Westpac file format) |
| 5 | **PayPal Payments** | PayPal deposits. | 🔴 | None |
| 6 | **PayPal Withdrawal** | PayPal payouts. | 🔴 | None |
| 7 | **Australian Fast Payments** | PayID issuance and inbound credit notification via Azupay → NPP. | **AWS (Sydney)** — API Gateway, Lambda, DynamoDB, Kafka | **Built outright (led)** |
| 8 | **Bank Maintenance** | Client bank account records (add / delete / verified status). Carve-out from the legacy monolithic *Payments* app, for IG US initially. | Nomad or DC ❓ | **Contributor** (primarily via Open Banking side) |
| 9 | **Open Banking** | Plaid integration for IG US ACH — automated client bank account verification, **pre-transaction**. | 🟡 | **Contributor** (first project) |
| 10 | **Card Validation Service** | BIN lookup — scheme, credit/debit, issuing country. Worldpay-sourced BIN dataset, YAML override layer via Spring Cloud Config. | DC (CDE) | Familiar, minimal code |
| 11 | **PSP Maintenance** | PSP credentials (encrypted), entity→PSP mapping, PSP configuration. Fed by Hydra. | DC (CDE) | Familiar |
| 12 | **PSP Integration Service** | The only component that speaks to external PSPs. Also validates inbound webhook payloads/headers on PG's behalf. | DC (CDE) | Familiar |
| 13 | **Wallet Payments** | Apple Pay deposits and withdrawals. Talks to PSP Integration Service directly, bypassing CardPayments. Uses D-PAN. | 🔴 | None |
| 14 | **Cash In Transit** | Upfront crediting of funds not yet settled. Ops-judgement driven; automated $2,500 cap for Plaid-verified ACH. | 🔴 | None |
| 15 | **Bank Postings** | Ingests bulk bank files (CAMT, FIN) from HSBC, Lloyds, Standard Chartered and others. Matches reference fields to account IDs, validates, posts ledger. Also consumes PayID credit notifications. | DC 🟡 | **Point of contact**, strong knowledge |
| 16 | **Funds Transfer Service** | Inter-account movement (CFD ↔ stockbroking ↔ etc.) and currency conversion. | 🔴 | None |
| 17 | **ACH Payments** | US ACH deposits. | ❓ | ❓ |
| 18 | **Payments Orchestrator** | GDPR purge — garbles PII across payments datastores on instruction from a central orchestrator. | 🟡 | None |

### 3.1 Frontends and consumers

| Consumer | Audience | Notes |
|---|---|---|
| **FE-Payins** | External clients | React. Renders all payment screens including card entry. **PCI-DSS in scope** — handles raw card numbers client-side. |
| **My-IG** | External clients | Web account management |
| Web trading platform, iOS, Android | External clients | |
| **IGIP** / Internal-platforms | Internal admins | Manual deposits, payment runs, cancellations, manual queue handling |
| **Hydra** | Internal admins | PSP onboarding and credential management (other team's code) |
| **internet-monitor** | Internal | 🟡 |

**Architecturally significant:** internal and external traffic converge on the **same Payments Gateway**, differentiated only by token type (CST vs XST) and role claims.

### 3.2 External dependencies

| Provider | Role | Market |
|---|---|---|
| **Worldpay** | PSP; also the BIN data source | Multiple |
| **Noire** 🟡 | PSP | Multiple |
| **Realex** 🟡 | PSP | Multiple |
| **Westpac** | PSP / payout bank | Australia (incl. IGCRY) |
| **Azupay** | NPP/PayID aggregator, fronting National Australia Bank | Australia |
| **BJP (Bill in Japan)** | Bank deposit aggregator | Japan |
| **Plaid** | Bank account verification (AIS) | USA |
| **HSBC, Lloyds, Standard Chartered** | Banking partners — inbound CAMT/FIN files, outbound payout SFTP | Multiple |
| **Akamai** | Edge / CDN / WAF | All |

---

## 4. Payment flows

### 4.1 Card deposit (ECOM) 🟢

```
FE-Payins ──► Akamai ──► external router ──► Payments Gateway
                                                    │  auth: CST
                                                    │  route on /card-payments
                                                    ▼
                                            internal router ──► CardPayments
                                                                     │
                     ┌───────────────────────────────────────────────┤
                     │  validate · limits · risk · BIN · name        │
                     │  resolve client account                       │
                     │  persist txn = INITIATED                      │
                     ▼                                               │
        Card Validation Service (BIN)                                │
                                                                     ▼
                                      PSP Integration Service ──► PSP (Worldpay / …)
                                                    ▲                 │
                                      PSP Maintenance                 │ 3DS2 challenge
                                      (credentials, entity→PSP)       ▼
                                                                   Client enters OTP
                                                                      │
   PSP ──webhook──► Akamai ──► PG /deposit/event ──► CardPayments ◄───┘
                                     │  (see 5.3 for webhook auth)
                                     ▼
                        txn = APPROVED
                        ─► Ledger Service (async API, fire-and-forget)
                        ─► Email notification (async, AMQ)
```

**Key characteristics**

- PG holds **no transaction state**; it is a pure front controller. CardPayments is the system of record for card transactions.
- **Duplicate webhooks** are defended by a **DB unique constraint** — the second insert simply fails.
- **Missing webhook** is defended by a **batch job** that sweeps `INITIATED` transactions and queries the PSP's status endpoint to resolve them.
- **Urgent cases** bypass the batch: the client calls in, payments ops verifies with the PSP manually and posts on the client's behalf.
- **Day-end**, AutoRec verifies the day's transactions and marks anything still `INITIATED` as abandoned/failed.
- **PAN never reaches the server.** Stored masked plus BIN. FE-Payins is nonetheless in PCI scope because it touches the number in the browser.

### 4.2 Card deposit (MOTO) — internal admin on client's behalf 🟢

Same path, with two differences: the caller presents an **XST** token with an appropriate role, and **3DS2 is waived** (the "frictionless" path). In markets where 3DS2 is not enabled by default, ECOM and MOTO behave identically in this respect.

The transaction row records the acting admin (see §9.3).

### 4.3 Card withdrawal (CFT) 🟢

**CFT = Cardholder Funds Transfer** — a push-to-card credit, *not* a refund of the original deposit. This is why a client who deposited £1,000 on a card can withdraw £3,000 to it: the payout is an independent credit, uncapped by and unlinked to any prior deposit.

```
Client ─► FE-Payins ─► PG ─► CardPayments
                                │  instrument verified? ──── no ──► blocked
                                │  amount ≤ available-to-withdraw?
                                │     (central order server)
                                │  withdrawal-blocked flag set by ops? ──► blocked
                                ▼
                     Ledger debit (async, fire-and-forget)
                                ▼
                  PSP Integration Service ─► PSP ─► client's card
                                ▼
                        Email notification
```

Card withdrawals are **near-instant and normally auto-approved**. Problem cases drop to the **manual queue** for payments ops.

### 4.4 Bank deposit — Japan, via BJP 🟢 *(author rebuilt this)*

Japan is bank-only, so this is the primary money-in rail for IG JP. **BJP = Bill in Japan**, an aggregator fronting the supported Japanese banks.

**Target architecture (AWS, Tokyo region)**

```
FE-Payins (quick deposit)
     │
     │ 1. GET config
     ▼
┌─────────────────────────────────────────────┐
│ Lambda A — Spring Boot + GraalVM native     │
│   • returns available banks                 │
│   • returns transaction ID (journey key)    │
│   • returns token (verified on redirect)    │
│   • POST /initiate → txn = INITIATED        │
│   • GET  /result   → redirect landing       │
└─────────────────────────────────────────────┘
     │                              ▲
     │ 2. client picks bank,        │ 4. BJP browser redirect
     │    enters amount             │    (token + txnId matched)
     ▼                              │
  Bank page in popup ──► BJP ──► client's bank (credentials, payment)
     │
     ▼ 5. write to DynamoDB
┌─────────────────────────────────────────────┐
│ DynamoDB (Tokyo) — transactions             │
└──────────────────┬──────────────────────────┘
                   │ DynamoDB Streams
                   ▼
┌─────────────────────────────────────────────┐
│ Lambda B — Quarkus, Streams listener        │
│   • mark for ledger posting                 │
│   • send email                              │
└─────────────────────────────────────────────┘

┌─────────────────────────────────────────────┐
│ Lambda C — Quarkus, file reconciliation     │
│   • picks up INITIATED transactions         │
│   • verifies against BJP file               │
│   • posts ledger on confirmed success       │
└─────────────────────────────────────────────┘
```

**Design notes**

- **There is no server-to-server webhook.** The only real-time signal is the **browser redirect**, authenticated by matching the token and transaction ID issued at config time. If the client abandons the popup after paying, the deposit is not credited in real time — it waits for **file reconciliation** (Lambda C) or a **manual deposit** by an admin if the client calls in.
- So "instant" is conditional: instant *when the redirect lands*, otherwise next reconciliation cycle.
- **GraalVM native image** was adopted because Java Lambdas behind a VPC cold-started in ~7–8 seconds. POCs were run across Micronaut and Quarkus; the outcome was Spring Boot + GraalVM for Lambda A and Quarkus for Lambdas B and C.
- Locating data and compute in **Tokyo** removed the round trip to the UK data centre, materially improving latency for Japanese clients.
- Replaces a **Spring 3/4 era** application with four endpoints (config, callback, manual deposit, configuration-out).

### 4.5 Bank postings — inbound bank files 🟢

The generic inbound-credit rail for every market except Japan. Covers SWIFT and domestic transfers where the client **pushes** money to IG's bank account.

```
Client pushes money to IG's bank account,
quoting their ACCOUNT ID in the payment reference/comment
     │
     ▼
Bank (HSBC / Lloyds / Standard Chartered / …)
     │  CAMT (ISO 20022) or FIN (SWIFT MT) file
     ▼
Bank Postings
     │  • parse file
     │  • extract account ID from primary / secondary / related reference
     │  • validate
     │  • no match, or name mismatch → MANUAL QUEUE (payments ops)
     ▼
Ledger Service
```

**Not instant** — credit occurs only when the bank file arrives and is processed. Where the client needs money sooner, **Cash In Transit** may front it on ops judgement.

Unattributable money that cannot be matched to any client is handled as a **refund**, manually, by payments operations.

### 4.6 Australian Fast Payments — PayID 🟢 *(author built this)*

Deposit-only today (**PayID**, not PayTo). Before this existed, card was the only instant deposit method for Australian clients.

**Architectural insight:** PayID is deliberately **decoupled**, reusing the bank postings reference-matching pattern rather than inventing a new one. An inbound NPP credit is normalised into a `CreditNotification` and handed to Bank Postings, which treats it much as it treats a CAMT line.

```
                    REGISTRATION (once per account ID, permanent)
FE-Payins ─► API Gateway ─► Lambda: generate PayID        [auth: CST]
                                │
                                │ creates  <number>@igau
                                │ stores PayID → accountId mapping
                                ▼
                          DynamoDB (Sydney)
                                │
        Client registers that PayID in their own online banking
                                │
                    ─────────── PAYMENT (repeatable) ───────────
                                │
    Client's bank ─► NPP (via National Australia Bank) ─► Azupay
                                │
                                │ webhook + payer name
                                │ auth: long-lived per-client transaction token
                                ▼
              API Gateway ─► Lambda: PayID notifications
                                │  • look up accountId from DynamoDB
                                │  • name-match payer vs KYC name
                                │  • build CreditNotification (accountId stamped)
                                ▼
                          Kafka → topic com-v3-finance
                                ▼
                          Bank Postings
                                │  same reference→accountId→validate path
                                ▼
                          Ledger Service
```

**Design decisions and constraints**

- **One PayID per account ID**, not per client and not per transaction — because a client holds several product accounts. The PayID is permanent for the life of the registration.
- **Wrong-amount risk does not exist** — the amount is whatever Azupay reports as actually received, not something the client declares to IG in advance.
- **Name mismatch** (payer name vs KYC name) → **manual queue**, ops discretion. Same for any other anomaly. Money is never silently posted to a guessed account.
- **Webhook authentication is the known weak point.** Azupay echoes a per-client transaction token in the header on every notification. There is no mechanism to rotate it in place — the only remedy if it is compromised is **deregister and re-register** the client's PayID, which flushes the token.
- **Volume:** ~2,000–3,000 transactions/day; per-minute concurrency is low, so Lambda absorbs it comfortably with substantial idle time.
- **Adoption:** roughly **20% of active Australian clients onboarded in the first week**.

### 4.7 US ACH and Open Banking (Plaid) 🟢

Plaid operates **before** a transaction, not during one — this is the cleanest contrast with the PSP Integration Service, which sits in the transaction path.

```
Client adds US bank account
     │
     ▼
Open Banking ─► Plaid ─► verifies account ownership   [near-instant]
     │
     ▼
Bank Maintenance — account stored as VERIFIED
     │
     ▼
ACH Payments — deposit / withdrawal now permitted
     │
     └─► Cash In Transit fronts up to $2,500 immediately
         (or the full amount if smaller); remainder credited
         when the ACH funds actually settle
```

Before Plaid, verification required the client to submit documents, reviewed manually by payments ops — a **1–2 business day** delay. Plaid reduced this to near-instant.

There is also a migration path: legacy clients whose bank details lived in the old *Payments* application are moved to the new Bank Maintenance schema **only after** successful Plaid verification, and the old record is deleted only once the new one exists — deliberately ordered so a client is never left without a bank account, and never holds one in both schemas.

### 4.8 Bank withdrawal and the payment run 🟢

The most control-heavy flow in the domain, and entirely batch.

```
Client requests bank withdrawal
     │  instrument verified? · available-to-withdraw? · ops block flag?
     ▼
Bank Withdrawal — request queued
     │
     ▼  Ledger DEBITED (async, fire-and-forget) — before money leaves
     │
     ▼
PAYMENT RUN — payments ops, per region (e.g. Australia), via IGIP
     │
     ├─ CHECK 1  — admin A verifies transactions are sendable
     ├─ CHECK 2  — admin B independently verifies
     │             (roles: …CREDITSIGNOFF, …PAYMENTRUN)
     ▼
READY FOR AUTHORISATION ─► authorised
     │
     ▼
Bank file generated  (per-bank / per-product format)
     │
     ▼
Common network drive
     │
     ▼
MFT / GoAnywhere team ─► bank's SFTP server
     │
     ▼
IG's bank (HSBC / Lloyds / Standard Chartered / Westpac)
     │
     ▼
Client's bank account          ─► Email notification
```

**Notes**

- **No PSP is involved in bank payout.** Execution is file-based, bank-direct.
- **Cancellation** is possible via payments ops before the daily cut-off (~16:30 🟡).
- **Ledger is debited before the money moves.** If a payout subsequently fails, ops re-credit the client manually. There is no automated compensating transaction.
- **IGCRY required a new bank file format.** Because crypto was regulatorily unsupportable for the incumbent bank, Westpac was onboarded, and the Westpac account identifier differs from the standard CFD/stockbroking account ID — so file generation needed a new format with additional fields. Delivered in a single sprint.

### 4.9 Funds Transfer Service and currency conversion 🟡

- Handles movement between a client's own product accounts (CFD ↔ stockbroking ↔ others) and currency conversion.
- **GBP is IG's core currency.** Everything is ultimately expressed in GBP regardless of the client's market or the asset's currency. Conversion exists primarily for IG's bookkeeping.
- Currencies seen in conversion: GBP, USD, JPY, AED, SGD.
- **Rates** are pulled from a central rates application outside the payments domain, refreshed **daily**. Payments applies the rate as given; whether a spread or margin is embedded upstream is not visible from within the domain.
- There is **no requirement** that a client's deposit currency match their account currency.

### 4.10 Cash In Transit 🟡

Fronts money that has left the client but not yet settled to IG.

- Generally **ops judgement**, deliberately so — the exposure is real.
- **One automated exception:** Plaid-verified ACH deposits are fronted up to **$2,500**. A $10,000 deposit credits $2,500 immediately and $7,500 on settlement; a $2,000 deposit credits in full.

### 4.11 GDPR purge — Payments Orchestrator 🟡

A central orchestrator, triggered by the admin team, identifies clients due for purge (dormant, typically no login for ~1 year). Payments Orchestrator then **garbles PII** — name, contact number and similar fields — across payments datastores. Audit data is purged ahead of the GDPR sweep, and reconciliation is unaffected because the client has long been inactive.

---

## 5. Cross-cutting architecture

### 5.1 Request path

```
Client
  │
Akamai                          (edge, WAF, CDN — infra team)
  │
External router                 (nginx 🟡 — other team)
  │
Load balancer / proxy           (stickiness unknown 🔴)
  │
Payments Gateway  (one of N instances)
  │   • authenticate token
  │   • role check (gateway-level for most endpoints)
  │   • resolve target from URI resource, e.g. /card-payments
  │
Internal router                 (nginx 🟡 — other team)
  │   • selects an available instance of the target application
  │
Method application
```

Routing is **path-based on the second resource segment** of the URI. `router-in/card-payments` resolves to a CardPayments instance.

### 5.2 Token and authentication model 🟢

| Token | Subject | Issuer | Status |
|---|---|---|---|
| **CST** (Customer Security Token) | External clients | Client security application | Remaining long-term |
| **XST** (X Security Token) | Internal admins; carries roles | SSO service | Being replaced by JWT |
| **JWT** | Internal admins (newer) | SSO service | Rolling out |
| **Application token** | Service-to-service | SSO service | Active |

All three client-facing token types operate **concurrently** today. Role enforcement happens **at the gateway** for most endpoints, and **additionally in the backend application** for particularly sensitive ones.

**Role naming convention** — `ROLE_RG-<system>-<domain>-<capability>`, with a `-DEV` suffixed variant that is valid only in TEST/UAT and is granted to developers:

```
ROLE_RG-IM-PAYMENTS-PAYMENTRUN
ROLE_RG-HYDRA-BANKPAYMENTS-CREATEBANKFILE
ROLE_RG-HYDRA-BANKPAYMENTS-CREDITSIGNOFF
ROLE_RG-HYDRA-BANKPAYMENTS-CREDITSIGNOFF-DEV   ← non-prod only
```

### 5.3 Webhook ingress and authentication 🟢

Inbound PSP webhooks carry no IG token, so PG authenticates them by delegation. Configured per PSP as a distinct path, e.g. `/deposit/event`.

```
PSP webhook
     │
     ▼
Payments Gateway — HTTP filter
     │
     ├──► PSP Integration Service : validate payload + header against the PSP
     │◄── validated
     │
     │  strip PSP header
     │  stamp PG's own application token (role-bearing)
     ▼
Method application (e.g. CardPayments)
```

**Note for §10:** the token PG stamps on this path is role-bearing, which means the trust boundary between "an external provider called us" and "a privileged internal caller" is crossed inside PG.

### 5.4 Messaging

| Transport | Use | Status |
|---|---|---|
| **AMQ** | Primary messaging across the estate — email notifications, inter-application events | Standard |
| **Kafka** | New initiative. Currently the PayID → Bank Postings `CreditNotification` path (`com-v3-finance`). | Emerging |
| **DynamoDB Streams** | Intra-application event trigger in Bank Deposits | Cloud-native apps |
| **SQS / SNS** | AWS-hosted applications | Cloud-native apps |
| **FMQ** | Legacy | Nearly decommissioned |

### 5.5 Recurring architectural patterns

Worth naming explicitly, because they recur and a newcomer will meet all four:

1. **Front controller + path routing** — PG authenticates and delegates; it never holds state.
2. **Reference-matching for decoupled credits** — Bank Postings and PayID both match an inbound credit to an account ID carried in a reference field, then validate name, then post. The transport differs (CAMT file vs Kafka `CreditNotification`); the pattern is identical.
3. **Optimistic real-time signal with a batch safety net** — cards (webhook + status-polling sweeper), Japan (redirect + file reconciliation), everything (AutoRec day-end). No flow relies solely on its happy path.
4. **Manual queue as the universal fallback** — anything ambiguous becomes a payments ops decision rather than an automated guess. This is a deliberate design stance, not an absence of design.

---

## 6. Controls and validation

### 6.1 Deposit-side checks (per application, not centralised) 🟢

Each method application implements its own limits and risk logic — CardPayments for cards, Bank Deposits for Japan, and so on. There is no shared risk engine.

CardPayments performs at minimum:

- Minimum and maximum amount per transaction
- Daily caps
- Card country vs account country mismatch
- BIN blocklist
- Allowed card **type** (some markets prohibit credit cards)
- Cardholder name validation

### 6.2 Withdrawal-side controls 🟢

| Control | Mechanism |
|---|---|
| Instrument verification | Card and bank must be verified before payout |
| Available-to-withdraw | Fetched from central order server; hard ceiling |
| Ops block | A manual, ops-set flag checked only in the withdrawal flow |
| Dual sign-off | Check 1 + Check 2 by two distinct admins (bank only) |
| Authorisation | Separate step after both checks |
| Cut-off | Cancellable via ops before daily cut-off |

**Cross-source payout rule** 🟡 — *author's understanding, to be confirmed with the business.* Once a client's instruments are all verified, funds may be withdrawn to any of them regardless of which instrument funded the account (deposit £1,000 by card and £2,000 by bank, withdraw £3,000 to either). Where instruments are **not** verified, payout is restricted to the original funding source. Per-instrument deposit totals are tracked for card, bank and PayPal to support this.

*Industry context:* the binding AML principle is **same-name** rather than same-instrument — payouts must go to an instrument belonging to the account holder, and third-party payouts are prohibited. Restricting to the original instrument is the stricter posture firms adopt when an instrument is unverified, which is consistent with what is described above.

### 6.3 Bank account verification by market 🟢

| Market | Method | Latency |
|---|---|---|
| **USA** | Plaid via Open Banking | Near-instant |
| **All others** | Client submits documents; payments ops reviews manually | 1–2 business days |
| **Australia** (proposed) | Infer verification from a successful PayID credit — the money demonstrably came from the named client. Bank Postings would call Bank Maintenance to store the account as verified. | 🟡 Not yet delivered |

### 6.4 Fraud and sanctions 🟡

There is **no automated fraud scoring or sanctions screening** within the payments domain, as far as the author is aware. Payments ops manually block and flag clients; the flag is enforced in the withdrawal flow only. Any automated screening, if it exists, sits outside this domain.

---

## 7. Non-functional characteristics

| Dimension | Value |
|---|---|
| **Card volume** | ~10,000–50,000 transactions/day depending on traffic 🟡 |
| **PayID volume** | ~2,000–3,000/day; low per-minute concurrency |
| **Cold start (pre-GraalVM)** | ~7–8s for Java Lambda behind VPC |
| **Availability model** | DC pair — one active, one standby (on-prem) |
| **Deployment strategy** | Blue-green |
| **On-call** | Team runs its own rota |

**Typical incident classes**

1. Card deposit not reflecting in the client's account
2. Bank withdrawal not gone through
3. Ledger double-entry errors (see §9.2)
4. PSP outage — handled by manual traffic migration (§10)

---

## 8. Infrastructure and platforms

Three platforms coexist. Nomad is the deliberate intermediate step; applications that can go straight to AWS do so.

| Platform | Detail |
|---|---|
| **UK on-prem data centre** | Legacy. Hosts most applications. DC pair, active/standby. Oracle databases. |
| **HashiCorp Nomad (on-prem)** | Migration staging post. Secrets in **HashiCorp Vault**. |
| **AWS** | ECS Fargate, EC2, Lambda, SQS, SNS, API Gateway, DynamoDB. Secrets in **Parameter Store**. |

**AWS regions are deliberately regional**, not UK-centralised: Sydney (Australian Fast Payments), Tokyo (Bank Deposits), Ireland, Singapore.

### 8.1 Environments 🟢

| Environment | Purpose |
|---|---|
| **DEV** | Local machine only — no shared dev environment |
| **TEST** | Shared testing; `-DEV` roles valid here |
| **UAT** | Acceptance; `-DEV` roles valid here |
| **DEMO** | Client-facing practice accounts, no real money |
| **LIVE** | Real client money |

DEMO and LIVE run on the **sister data centres**, and the active/standby assignment is **flipped periodically** — DC1 serves LIVE while DC2 serves DEMO, then they swap. This makes standby capacity continuously exercised rather than cold.

### 8.2 Languages, frameworks, tooling

| Layer | Technology |
|---|---|
| **Java** | 8, 11, 17, 21 (all present across the estate) |
| **Spring Boot** | 1.x (legacy), 2.x and 3.x (modern). No 4.x. |
| **Quarkus** | Bank Deposits Lambdas B and C |
| **GraalVM** | Native image for Bank Deposits Lambda A |
| **Frontend** | React |
| **Config** | Spring Cloud Config (e.g. BIN override YAML) |
| **CI/CD** | GitLab, blue-green deployment |
| **Observability** | Splunk, Grafana |
| **Testing** | Unit, integration, acceptance |

### 8.3 PCI-DSS scope 🟢

The **entire payments domain** is in PCI-DSS scope. Payments Gateway, CardPayments, Card Validation Service and PSP Integration Service sit inside the **CDE** (Cardholder Data Environment). FE-Payins is in scope because raw card numbers are handled client-side.

---

## 9. Data and state

### 9.1 Card transaction status values 🟢

A **single status column** holds all of the following — meaning lifecycle state and PSP decline reason share one field:

```
Lifecycle-ish:      PENDING · PROCESSING · CHALLENGE_REQUIRED ·
                    AUTHENTICATION_REQUIRED · APPROVED · FAIL

PSP / issuer outcome:
                    DECLINED · BANK_DECLINED · AUTHENTICATION_FAILED ·
                    INSUFFICIENT_FUNDS · POSTCODE_DECLINED · CVV_DECLINED ·
                    ADDRESS_DECLINED · CV2AVS_DECLINED · REFERRAL ·
                    3DS_TXN_CANNOT_BE_AUTHORIZED

System:             PAYMENTS_SYSTEM_ERROR
```

Additionally, transactions are marked `INITIATED` on receipt and swept to abandoned/failed at day end by AutoRec.

*Recorded as-is rather than tidied. See §10 for why this conflation matters.*

### 9.2 Ledger posting pattern — double entry 🟡

Payments does not own the ledger, but it does construct the postings. A **clearing ledger** sits between the account ledger and the bank ledger, so a single money movement is expressed as two paired entries:

```
Group 1:   account-ledger                  −
           payment-request-clearing        +

Group 2:   payment-request-clearing        −
           bank-ledger                     +
```

Errors in this pairing are a recurring on-call theme. ❓ *To be detailed further.*

### 9.3 Audit trail 🟢

Every record carries an initiating-user column (`initiated by` / `DB created by user`). Manual actions record the acting admin's shorthand username. **Retained indefinitely.**

### 9.4 Key data stores

| Store | Contents |
|---|---|
| CardPayments DB (Oracle 🟡) | Card transactions, `card_token` (one token **per PSP** per card) |
| Bank Deposits DynamoDB (Tokyo) | Japan transactions |
| Aus Fast Payments DynamoDB (Sydney) | PayID → account ID mapping, per-client transaction token |
| Bank Maintenance schema | Client bank accounts + verified status (IG US carve-out) |
| PSP Maintenance DB | PSP credentials (**encrypted column**), entity→PSP mapping |
| Card Validation Service | Worldpay BIN dataset (CSV, deployed) + YAML override |

**Card tokenisation detail worth knowing:** a card registered against Worldpay receives a different token than the same card registered against Noire. On registration, the card is registered across **all available PSP configurations**, so switching a market's PSP does not break stored cards.

---

## 10. Known risks and improvement opportunities

Honest engineering observations. For interview use, these are strong material — they demonstrate systems judgement rather than just recall.

### 10.1 BIN data refresh — highest-value quick win

**Current state:** Worldpay supplies a BIN CSV every 2–3 days. The file is pasted in, committed, and deployed. No delta is examined. During the window between a BIN changing and the deploy landing, transactions fail and arrive as incidents; clients are asked to retry after the update. Misclassifications (a debit BIN marked credit) are corrected in a YAML override in Spring Cloud Config.

**Why it hurts:** reference data is being managed as source code, so a data change requires a release, and a data error becomes a client-facing decline.

**Proposed improvements, roughly in order of value:**

1. **Treat BIN data as data, not code.** Land the file in S3 or a database table with a version identifier; have the service load the active version at runtime. Refresh becomes a data operation, not a deployment.
2. **Hot reload the dataset.** Spring Cloud Config already reloads the override YAML — extend the same mechanism to the dataset itself, so a refresh needs no restart.
3. **Diff and report every delta before activation.** Produce an automated report of added, removed and reclassified BINs. Most refreshes are minimal, so a large diff becomes a signal worth investigating rather than a silent deploy.
4. **Fall back to a live BIN lookup on cache miss.** If a BIN is absent or the dataset is stale, query the PSP's real-time BIN API rather than declining. This removes the entire refresh-window failure class.
5. **Make the fail-open/fail-closed policy explicit.** An unknown BIN currently fails the transaction. Decide deliberately: fail open for permissive checks (type restrictions) and closed for blocklists, rather than defaulting to whichever the code does.
6. **Alert on decline-reason spikes.** A jump in BIN-related declines should page the team, not wait for a client to call.
7. **Auto-retire stale overrides.** When a refreshed file agrees with an existing YAML override, flag it — otherwise overrides accumulate as permanent unreviewed exceptions.
8. **Version and canary the dataset.** Activate a new version for a small traffic slice first, with automated rollback on decline-rate regression.

### 10.2 Other observations

| Risk | Observation | Direction |
|---|---|---|
| **Status column conflation** | Lifecycle state and PSP decline reason share one column, so "where is this transaction" and "why did the issuer refuse" are the same question. Makes valid-transition enforcement impossible and reporting fragile. | Split into `state` (enforced state machine) + `reason_code`. Introduce alongside, backfill, migrate readers. |
| **Fire-and-forget ledger posting** | If the async call to Ledger Service is lost, payments has taken money with no credit and no internal signal. Detection depends on the client noticing, or AutoRec. | Add an outbox with retry and DLQ, plus a daily assert that every APPROVED transaction has an acknowledged posting. Ownership of the ledger stays external; ownership of *delivery* becomes yours. |
| **PayID webhook token cannot be rotated** | The only remedy for a compromised per-client token is deregister/re-register. | Constrained by Azupay's protocol. Compensate with strict IP allowlisting, payload signature validation if available, and anomaly alerting on unexpected notification sources. |
| **PG stamps a role-bearing token on the webhook path** | An external-origin request acquires internal privileges inside PG. | Issue a narrowly-scoped token for webhook-originated traffic, carrying only the callback capability. |
| **Hardcoded country/method/priority config** | Changing a market's available methods or their display order requires a code change and release, despite being a commercial decision. | Externalise to configuration with an admin UI, as PSP mapping already is via Hydra. Low change frequency makes this low-priority but it is the same class of problem as 10.1. |
| **No automated PSP failover** | A PSP outage becomes an incident, a diagnosis, and a manual config change. | Health-check driven automatic failover to a configured secondary, with circuit breaking per PSP. |
| **No automated fraud/sanctions screening in-domain** | Enforcement is a manual ops flag, checked only on withdrawal. | Confirm whether screening exists upstream before treating this as a gap — it may be an account-opening-domain control. |
| **Kafka authentication unverified** | The Lambda → Bank Postings credit notification path traverses Kafka with no authentication the author is aware of. This path carries money-movement instructions. | Verify. If genuinely unauthenticated, mTLS/SASL is warranted given the payload. |
| **Japan has no server-to-server callback** | A paying client who closes the popup gets no real-time credit. | Ask BJP whether a webhook is available; if not, shorten the reconciliation cycle and consider client-side confirmation retry. |

---

## 11. Contribution ledger

For interview and CV use. Framed as situation → action → outcome, with honest attribution of what was and was not the author's own.

### 11.1 Australian Fast Payments (PayID) — built outright, led

| | |
|---|---|
| **Role** | Lead developer and de facto technical lead |
| **Team** | 2 core engineers + 1 frontend developer + ad hoc support |
| **Duration** | 6–7 months |
| **Platform** | Greenfield on AWS (Sydney) — API Gateway, Lambda, DynamoDB, Kafka |

**Situation.** Australian clients had exactly one instant deposit option: card. PayID/NPP was the dominant domestic instant rail — the Australian equivalent of UPI — and its absence was a competitive and cost gap.

**Action.** Led the project end to end: read and interpreted Azupay's integration documentation from scratch, designed the flow, and delivered it. The key design decision was to make PayID **decoupled** rather than transactional — reusing the existing Bank Postings reference-matching machinery by normalising Azupay's webhook into a `CreditNotification` on Kafka, rather than building a parallel credit-posting path. Also designed the per-account-ID PayID model (necessary because clients hold multiple product accounts), the DynamoDB PayID→account mapping, the CST-authenticated registration endpoint, and the name-matching and manual-queue fallback for anomalous credits.

**Outcome.** ~20% of active Australian clients onboarded in the first week. Now handles 2,000–3,000 transactions/day. Gave Australian clients a second instant deposit route and reduced dependence on card rails.

**Talking points if probed:** why decoupled beats transactional here; the Azupay token rotation constraint and how you'd mitigate it; why one PayID per account ID rather than per client.

### 11.2 Bank Deposits rebuild (Japan) — rebuilt end to end, led

| | |
|---|---|
| **Role** | Lead developer |
| **Team** | 2 engineers + ad hoc support; architecture from a senior tech specialist |
| **Duration** | 3–4 months |
| **Platform** | Spring 3/4 on-prem → AWS Lambda (Tokyo) |

**Situation.** Japan's only money-in route is bank deposit, so this application was business-critical for IG JP — and it was a Spring 3/4 era codebase with accumulated issues, running out of the UK data centre.

**Action.** Reverse-engineered the legacy application in full: behaviour, integration points, failure modes. Rebuilt it from scratch against an architecture handed over by a senior tech specialist (Lambda split, streams design), with the majority of implementation being the author's own. Split the monolithic four-endpoint app into three Lambdas — Spring Boot for config/initiate/redirect, Quarkus for the DynamoDB Streams listener, Quarkus for file reconciliation.

**The hard technical problem.** Java Lambdas behind a VPC cold-started in 7–8 seconds, unacceptable for a client-facing deposit flow. Ran POCs across **Micronaut**, **Quarkus** and **Spring Boot + GraalVM native image**, then committed deliberately: GraalVM native for the client-facing Lambda, Quarkus for the two background Lambdas. This was the author's principal contribution to the rebuild.

**Outcome.** Cold-start latency substantially reduced. Additional latency win from relocating compute and data to **Tokyo** and copying data into a regional DynamoDB table, eliminating the UK round trip entirely for Japanese clients. Legacy Spring 3/4 dependency retired.

**Talking points:** the GraalVM vs Quarkus vs Micronaut evaluation and why different answers for different Lambdas; why redirect-only confirmation is acceptable given file reconciliation; what you'd change (a server-to-server webhook, if BJP offered one).

### 11.3 Open Banking / Plaid — contributor (first project)

| | |
|---|---|
| **Role** | Developer; planning owned by a senior engineer |
| **Team** | 4 engineers |

**Situation.** IG US clients adding a bank account for ACH had to submit documents for manual review by payments ops — a **1–2 business day** delay before they could transact.

**Action.** Integrated multiple Plaid APIs, working from Plaid's documentation. The higher-level design — which applications participate, how the ACH flow should work end to end — was owned by a senior colleague; the author's contribution was API integration and implementation.

**Outcome.** Bank account verification moved from 1–2 business days to near-instant. Also unlocked the automated **$2,500 upfront credit** for Plaid-verified ACH deposits, since verified provenance made fronting the money acceptable.

**Honest framing:** worth presenting as "my first project, where I owned integration rather than design" — the contrast with PayID and Japan, where the author owned the design, is itself the growth narrative.

### 11.4 Bank Maintenance — contributor

**Situation.** Client bank details lived in a legacy application called *Payments*, which handled too many use cases and was not user-friendly.

**Action.** The bank-storage concern for IG US clients was carved out into a new Bank Maintenance schema. The author's contribution was primarily the **Open Banking side** of the migration; a colleague led Bank Maintenance itself.

**Design detail worth citing** — the migration was **verification-gated and ordered for safety**: existing clients moved to the new schema only after Plaid verification succeeded, and the old record was deleted **only after** the new one was written, so no client was ever left without a bank account or holding one in two schemas simultaneously.

### 11.5 IGCRY / Westpac bank file — delivered

**Situation.** IG launched a crypto product (IGCRY). The incumbent payout bank could not support crypto-related flows for regulatory reasons, so **Westpac** was onboarded for Australian IGCRY withdrawals. Westpac's account identifier differs from the standard CFD/stockbroking account ID.

**Action.** Designed and built a new bank file format for the payment run, adding the required fields and the new account identifier.

**Outcome.** Delivered within a single sprint. Gives the author full working knowledge of the bank withdrawal and payment run flow.

### 11.6 Payments Gateway and CardPayments — contributor

Contributions to both, in the PCI CDE. ❓ *Specific features, migrations and incidents to be recalled and added.*

### 11.7 Bank Postings — point of contact

Not a developer on it, but the designated point of contact, with strong working knowledge of CAMT/FIN parsing, reference matching, and the ledger posting path. This knowledge directly enabled the PayID design decision in 11.1.

### 11.8 Breadth summary

| Application | Level |
|---|---|
| Australian Fast Payments | Built outright, led |
| Bank Deposits (Japan) | Rebuilt end to end, led |
| Open Banking | Contributor |
| Bank Maintenance | Contributor |
| Bank Withdrawal | Contributor (IGCRY/Westpac) |
| Payments Gateway | Contributor |
| CardPayments | Contributor |
| Bank Postings | Point of contact, strong knowledge |
| Card Validation Service | Familiar |
| PSP Maintenance / PSP Integration | Familiar |
| PayPal Payments / Withdrawal | None |
| Wallet Payments | None |
| Cash In Transit | None |
| Funds Transfer Service | None |
| Payments Orchestrator | None |

**Technical range demonstrated:** legacy Spring on-prem → Nomad → AWS serverless; Java 8 through 21; Spring Boot 1–3, Quarkus, GraalVM native; Oracle and DynamoDB; AMQ and Kafka; PCI CDE; four distinct integration archetypes (synchronous PSP, browser redirect, webhook, batch file); and three markets with genuinely different rails (UK/EU cards, Japan bank-only, Australia NPP, US ACH).

---

## 12. Open questions

### To confirm
- [ ] Ledger double-entry model — full detail of the clearing-ledger pairing (§9.2) and what "double-entry errors" means concretely in incidents
- [ ] Cross-source withdrawal rule — confirm with the business whether it is same-name or same-instrument (§6.2)
- [ ] External and internal router technology and ownership (§5.1) — nginx assumed
- [ ] Kafka authentication on the Lambda → Bank Postings path (§10.2)
- [ ] PCI-DSS level and assessment cadence (§8.3)
- [ ] Load balancer stickiness, and PG behaviour if an instance dies mid-flow
- [ ] Bank withdrawal cut-off time (16:30 assumed)
- [ ] Complete PSP list and correct spellings — Noire (Nuvei?), Realex (Global Payments?)
- [ ] Full IG legal entity list
- [ ] Which applications sit on Nomad vs DC vs AWS — per-application mapping
- [ ] Card and bank postings daily volumes; peak behaviour during market volatility

### To fill in
- [ ] **ACH Payments** — responsibility detail and author's knowledge level
- [ ] **CardPayments and Payments Gateway** — specific features/migrations/incidents (§11.6)
- [ ] Production incidents diagnosed or led
- [ ] The two or three pieces of work the author is proudest of, and why
- [ ] Webhook testing strategy against external PSPs
- [ ] Whether any automated fraud/sanctions screening exists upstream of payments
