# IG Payments — Elicitation Record & Corrections

**Companion to:** `ig-payments-domain-model.md`
**Compiled:** September 2026

This document preserves the raw knowledge-capture trail: what was corrected, what was self-corrected, what was transcription noise, and a condensed record of every question and answer. The domain model is the polished output; this is the working record behind it.

---

# Part A — Corrections and clarifications

## A.1 Concepts clarified

### Stateless vs stateful

**Asked because:** the initial description said Payments Gateway "holds session transactions."

**Definition.** *Stateless* means a service keeps nothing about a request in its own memory between calls — any instance can serve any request, because everything needed is in the request itself or in a shared store. *Stateful* means an instance holds something locally, so follow-up calls must reach the *same* instance, forcing sticky sessions and making a node death mid-flow destructive.

**Resolution.** Payments Gateway is **stateless** — a pure front controller and router. CardPayments is the system of record for card transactions and holds all DB state. The original "holds session transactions" was inaccurate.

**Still unknown:** load balancer stickiness, and PG behaviour if an instance dies mid-flow (the scenario has not occurred).

---

### Card payout: refund vs push-to-card

**The question.** Paying money out to a card happens by one of two mechanisms, and they behave very differently:

| | **Refund** | **Push-to-card (OCT family)** |
|---|---|---|
| Relationship to deposit | Reverses a specific prior transaction | Independent credit, no link |
| Amount ceiling | Capped at the original deposit | Uncapped by any deposit |
| Expiry | Typically ~180 days | None |
| Implementation need | Must track remaining refundable amount per deposit | None |

**Resolution.** IG uses **CFT — Cardholder Funds Transfer**, which is the push-to-card family (Visa Direct / Mastercard MoneySend). "OCT" (Original Credit Transaction) is the scheme-level term for the same thing; CFT is the name used in your codebase, which is why the term didn't land initially.

**Why this matters:** it explains the withdrawal behaviour you described — a client who deposited £1,000 on a card can withdraw £3,000 to it, because the payout is not a reversal. Under a refund model that would be impossible. There is **no refund-reversal mechanism** in the client withdrawal path.

**Refunds do exist**, but for something else entirely: money that arrives and cannot be attributed to any client, handled manually by payments operations.

---

### The three CardPayments channels

Your channel list resolved a question I had asked separately about 3DS "frictionless" flow:

| Channel | Meaning | Use |
|---|---|---|
| **ECOM** | E-commerce | Client-initiated online deposit; 3DS2 enforced |
| **MOTO** | Mail Order / Telephone Order | Internal admin depositing on a client's behalf; 3DS2 waived |
| **CFT** | Cardholder Funds Transfer | Outbound push-to-card withdrawal |

**Clarification on "frictionless."** In 3DS2 terminology, *frictionless* normally means the issuer waives the challenge because risk data looks clean — an issuer decision. What you described is different: **MOTO**, where IG deliberately does not invoke 3DS2 because an authenticated internal admin is transacting. These are two distinct mechanisms that happen to share an outcome. 🟡 *Recorded as inference — worth confirming that internal deposits are submitted as MOTO rather than as an ECOM transaction with an exemption flag.*

Separately: in markets where 3DS2 is not enabled by default, ECOM and MOTO behave identically in this respect.

---

### Cross-source withdrawal — same-name vs same-instrument

**You flagged this as your own assumption and asked to be corrected.**

Your understanding: if card, bank and PayPal are all verified, the client can withdraw to any of them regardless of which funded the account. If instruments are not verified, funds return only to the original source.

**Industry position.** The binding AML principle is **same-name**, not same-instrument: funds must go to an instrument belonging to the account holder, and third-party payouts are prohibited. Restricting payout to the *original funding instrument* is the stricter posture firms adopt specifically when an instrument is **unverified** — because verification is what establishes the name match.

**Verdict.** What you described is coherent and consistent with standard practice. It is recorded in the domain model as **your team's rule, marked as your understanding**, with a note to confirm with the business. The per-instrument deposit tracking you mentioned (how much came in from each card, bank, PayPal) is exactly what a same-instrument fallback requires, which supports your reading.

---

## A.2 Answers you corrected yourself

| Topic | Initially said | Corrected to |
|---|---|---|
| PSP credentials storage | Unencrypted DB column | **Encrypted** DB column (plus AWS Parameter Store for cloud apps, HashiCorp Vault for Nomad) |
| Bank Maintenance scope | Does "add, delete and now credit operation" on client bank accounts | No credit operation exists — Bank Maintenance **only maintains bank account details**. Misspoken. |
| Notification delivery | "Sends the email in an async manner"… then "in a sync manner using AMQ" | Fully **asynchronous** via AMQ — CardPayments does not block on email |
| Webhook auth direction | "The PSP strips off that header and adds its own XST token" | **Payments Gateway's HTTP filter** calls PSP Integration Service to validate payload and header; on success PG strips the PSP header and stamps **PG's own** application token. The external PSP does nothing here. |
| Bank deposit timing | Bank deposits are instant | Instant **only when the browser redirect lands**. Otherwise the credit waits for file reconciliation or a manual admin posting. |
| IGCRY | Listed alongside IG US, IG AU, IG GB as an entity | **IGCRY is a product**, not a legal entity — alongside IGCFD, IGSTK, IGFNO |
| Deployment regions | Single UK region (DC pair, active/standby) | DC is UK-only, but the **AWS estate is deliberately multi-region**: Sydney, Tokyo, Ireland, Singapore |

---

## A.3 Corrections I made to my own inferences

| I assumed | Actual |
|---|---|
| Open Banking = UK/EU AIS/PIS, possibly for payment initiation | **IG US only, ACH, AIS-style verification, pre-transaction** — not in the payment path at all |
| Bank Deposits handles bank rails generally (SEPA, SWIFT, Faster Payments) | **Japan only.** SWIFT → Bank Postings. Australian Faster Payments → Australian Fast Payments. |
| CardPayments includes a frontend of the same name | Frontend is **FE-Payins** (React), shared across methods |
| The status list would separate lifecycle from decline reasons | **One column** holds both |
| Wallet Payments routes through CardPayments | Routes **directly to PSP Integration Service**, bypassing CardPayments |
| PayID might be per-client or per-transaction | **Per account ID** — because a client holds several product accounts |
| A card token might break when a market's PSP changes | Cards are registered against **all available PSP configurations** at registration time, each producing its own token, so PSP switches don't break stored cards |

---

## A.4 Transcription corrections

Voice-capture noise, resolved during the conversation:

| Captured as | Actual |
|---|---|
| "cut payments" | **card payments** |
| "fast payments… some PID… BJP feature" / "PID customers" | **PayID** (Australia) |
| "Aka mine the front" | **Akamai** at the edge |
| "BJP" | **Bill in Japan (BJP)** — Japanese bank deposit aggregator |
| "nextmail team" | **Ledger Service team** |
| "JWT will be only replacing 60" | replacing **XST** |
| "Zupay" | **Azupay** |
| "AutoRx" | **AutoRec** |
| "EngineX app" | **nginx** 🟡 |
| "Plunk" | **Splunk** |
| "Hashicott Nomad" | **HashiCorp Nomad** |
| "USD to GPP" | **GBP** |
| "if the radar comes, then it is instant" | if the **redirect** comes |
| "Asset notifications" | **async** notifications |
| "the verb resource card payments" | the **URI path segment** `/card-payments` |
| "this is like high level four" | high level **flow** |
| "no client adds his account ID" | the **client adds** his account ID to the reference |
| "the first lambda gives the CardPayments configuration" (Japan flow) | the **Bank Deposits** configuration |
| "under REALEX" (PSP list) | **Realex** 🟡 — possibly Global Payments |
| "Noire" | 🟡 possibly **Nuvei** — spelling unconfirmed |

---

# Part B — Condensed Q&A record

Organised by elicitation area. Answers compressed; full architectural detail lives in the domain model.

## Area 1 — Application inventory

- **18 applications** named: Payments Gateway, Card Payments, Bank Deposits, Bank Withdrawal, PayPal Payments, PayPal Withdrawal, Australian Fast Payments, Bank Maintenance, Open Banking, Card Validation Service, PSP Maintenance, PSP Integration Service, Wallet Payments, Cash In Transit, Bank Postings, Funds Transfer Service, ACH Payments, Payments Orchestrator.
- **Granularity:** microservice per payment method, no sharing. One application per method serving all countries, multiple instances each.
- **Country/method/priority config:** hardcoded in Payments Gateway, changed by code change. Rarely changes, so no config layer exists.
- **Frontends:** FE-Payins, My-IG, IGIP (Internal-platforms), Hydra, internet-monitor, Android, iOS, web trading platform. Internal admins and external clients hit the **same** gateway.
- **PG shape:** one application serving both deposits and withdrawals; front controller, delegates.
- **No monolith, no old/new world divide.** Enhancement is incremental. CardPayments handles JWT, XST and CST concurrently.

## Area 2 — Card deposit

- Flow: FE-Payins → PG (`/card-payments`) → CardPayments → validate → txn `INITIATED` → PSP Integration Service → PSP → 3DS2 OTP → webhook to PG `/deposit/event` → CardPayments → ledger post + async email.
- **Duplicate webhooks:** DB unique constraint.
- **Missing webhook:** batch job sweeps `INITIATED` and queries the PSP's status endpoint; urgent cases handled manually by ops.
- **Abandoned:** AutoRec day-end job marks stragglers abandoned/failed.
- **PAN:** never reaches the server; stored masked with BIN. FE-Payins in PCI scope because the browser handles the number.
- **Card tokens:** `card_token` table in CardPayments DB; one token per PSP per card.
- **Ledger:** async API call to Ledger Service, **fire and forget**. No retry, DLQ or reconciliation on the payments side — explicitly out of remit.
- **Risk checks:** min/max, daily caps, card-country vs account-country, BIN blocks, allowed card type (some markets bar credit cards), name validation.
- **Currency:** in-house conversion using fixed daily rates; no requirement that currencies match.

## Area 3 — Bank deposits (Japan)

- **Why rebuilt:** legacy Spring 3/4, many issues, Japan-critical (bank is the only money-in route).
- **Old app:** four endpoints — initiate, callback, manual deposit, config-out.
- **New:** three Lambdas on AWS Tokyo. Lambda A (Spring Boot + GraalVM native) serves config/initiate/redirect; Lambda B (Quarkus) DynamoDB Streams listener → ledger mark + email; Lambda C (Quarkus) file reconciliation against BJP files.
- **GraalVM rationale:** Java Lambda behind VPC cold-started 7–8s. POCs across Micronaut, Quarkus, Spring Boot + GraalVM.
- **Confirmation:** browser redirect only, no server-to-server webhook. Token + transaction ID issued at config time are matched on redirect.
- **Manual deposit endpoint:** admins with XST, used when a client calls in and cannot wait for reconciliation.
- **Duration:** 3–4 months, 2 engineers + ad hoc. Architecture from a senior tech specialist; implementation majority the author's.
- *(Deeper detail — Java/Spring Boot versions, DynamoDB table design, CI/CD, cutover strategy — deliberately skipped.)*

## Area 4 — Australian Fast Payments

- **PayID only**, no PayTo. **Deposit only.** Before this, card was the sole instant option.
- **Integrator:** Azupay → NPP → National Australia Bank.
- **PayID per account ID**, format `<number>@igau`, permanent until deregistration. Client registers it in their own online banking.
- **Two Lambda endpoints** behind AWS API Gateway: generate PayID (CST-authenticated) and PayID notifications (authenticated by a long-lived per-client transaction token Azupay echoes in the header).
- **Token rotation:** impossible in place — deregister/re-register is the only flush mechanism.
- **On webhook:** look up account ID in DynamoDB, name-match payer against KYC name, build `CreditNotification`, publish to Kafka topic `com-v3-finance` → Bank Postings → same reference-matching path as CAMT → ledger.
- **Edge cases:** wrong amount impossible (amount comes from Azupay). Name mismatch or any anomaly → manual queue, ops discretion.
- **Volume:** 2,000–3,000/day, low per-minute concurrency.
- **Adoption:** ~20% of active Australian clients in week one. No cost/interchange data available.
- **Team:** 2 core + 1 frontend + ad hoc; author led. **6–7 months.**
- **Hardest part:** learning AWS — the author was not a cloud-native developer at the time.
- **Regulatory:** none the author is aware of.

## Area 5 — Withdrawals

- **Card withdrawal** handled by CardPayments (CFT); **bank withdrawal** a separate app; **PayPal withdrawal** separate. Japan is bank-only.
- **Verification gate:** instruments must be verified before withdrawal.
- **Available-to-withdraw** comes from the **central order server**.
- **Card:** near-instant, normally auto-approved; problems → manual queue.
- **Bank:** always manual. Payments ops run a **payment run** per region via IGIP → **check 1** and **check 2** by two distinct admins → ready for authorisation → authorised → bank file → common network drive → MFT/GoAnywhere team → bank SFTP → IG's bank → client.
- **No PSP in bank payout.** File-based, bank-direct (HSBC, Standard Chartered, Lloyds, Westpac).
- **Ledger debited before money leaves**, fire and forget. Failed payouts are re-credited manually by ops.
- **Cancellation:** via ops before daily cut-off (~16:30 🟡).
- **Fraud/sanctions:** no automated screening known. Ops manually block and flag; the flag is checked in the withdrawal flow only.
- **Bank verification:** US via Plaid (near-instant); everywhere else manual document review by ops (1–2 business days). Proposed future: infer verification from a successful PayID credit.
- **Author's involvement:** built the new bank file format for **IGCRY** (crypto), which required onboarding **Westpac** because the incumbent bank could not support crypto for regulatory reasons, and Westpac's account identifier differs from the standard CFD/stockbroking ID. Shipped in one sprint.

## Area 6 — FX, shared services, ancillary apps

- **Funds Transfer Service** — one application, handles both inter-account movement and currency conversion.
- **Rates:** pulled from a central application outside the domain, revised daily. Spread/margin not visible from within payments. Currencies: GBP, USD, JPY, AED, SGD. **GBP is IG's core currency** — everything converts to GBP for bookkeeping.
- **PSPs:** Worldpay, Westpac, Noire, Realex.
- **PSP onboarding:** via **Hydra** (other team's tool) → writes credentials into PSP Maintenance → PSP attached to an IG company (IGUS, IGGB, IGAU…). Switching a market's PSP is a **config change**.
- **PSP failover:** manual. An incident is raised, diagnosed, and traffic migrated by config change if the issue is large.
- **Credentials:** encrypted DB column (legacy), AWS Parameter Store (cloud), HashiCorp Vault (Nomad).
- **Card Validation Service:** returns scheme, credit/debit, issuing country. BIN data supplied by **Worldpay** as a CSV, refreshed every 2–3 days by paste-commit-deploy with no delta review. Misclassifications overridden in a YAML file via Spring Cloud Config. Failures during the refresh window surface as incidents; clients are asked to retry.
- **Wallet Payments:** Apple Pay, deposit and withdrawal, straight to PSP Integration Service. Uses D-PAN. 3DS presumed bypassed via device authentication. Outside author's remit.
- **Cash In Transit:** ops judgement, deliberately — it is sensitive. One automated exception: Plaid-verified ACH fronts up to **$2,500** ($10,000 deposit → $2,500 now, $7,500 on settlement; $2,000 deposit → $2,000 in full).
- **Payments Orchestrator:** GDPR purge. Central orchestrator triggered by the admin team identifies dormant clients; the orchestrator garbles all PII in payments records. Audit data is purged beforehand; reconciliation is unaffected because the client has been inactive ~1 year.

## Area 7 — Auth and security

- **CST** (external clients, client security application) — staying. **XST** (internal, role-bearing, SSO service) — being replaced by **JWT**. All three concurrent today. **Application tokens** for service-to-service, also SSO-issued.
- **Kafka path** (Lambda → Bank Postings): no authentication the author is aware of.
- **Role enforcement:** at the gateway for most endpoints; additionally in the backend for particularly sensitive ones.
- **Role convention:** `ROLE_RG-IM-PAYMENTS-PAYMENTRUN`, `ROLE_RG-HYDRA-BANKPAYMENTS-CREATEBANKFILE`, `ROLE_RG-HYDRA-BANKPAYMENTS-CREDITSIGNOFF`, each with a `-DEV` variant valid only in TEST/UAT and granted to developers.
- **PG's stamped token on the webhook path is role-bearing**, and the author acknowledged it may be reachable from a compromised inbound webhook.
- **Audit:** `initiated by` / `DB created by user` column on every record; manual actions record the admin's shorthand username; retained forever.
- **PCI-DSS:** the entire domain is in scope. PG, CardPayments, Card Validation Service and PSP Integration Service sit in the **CDE**.

## Area 8 — Infrastructure

- **Three platforms:** UK on-prem DC (legacy, most apps, Oracle), **HashiCorp Nomad on-prem** (intermediate migration step, Vault), **AWS** (ECS Fargate, EC2, Lambda, SQS, SNS, API Gateway, DynamoDB, Parameter Store). Apps that can go straight to AWS do.
- **AWS regions:** Sydney, Ireland, Singapore, Tokyo (Bank Deposits).
- **Routers:** external and internal, believed nginx, owned by another team.
- **Environments:** no shared DEV (local only) — TEST, UAT, DEMO, LIVE. DEMO and LIVE run on **sister data centres with the active/standby assignment periodically flipped**, so standby capacity stays exercised.
- **Stack:** Java 8/11/17/21; Spring Boot 1 (legacy), 2 and 3 (modern), no 4; Quarkus; GraalVM; React frontend; Spring Cloud Config.
- **Messaging:** AMQ primary, Kafka new, FMQ nearly decommissioned, DynamoDB Streams / SQS / SNS in cloud apps.
- **CI/CD:** GitLab, blue-green. **Observability:** Splunk, Grafana. **Testing:** unit, integration, acceptance.
- **On-call:** own rota. Typical incidents: card payment not reflecting, bank withdrawal not gone through, ledger double-entry errors, PSP outages.

## Area 9 — Data, state, org

- **Card status:** one column carrying `APPROVED, DECLINED, BANK_DECLINED, AUTHENTICATION_FAILED, INSUFFICIENT_FUNDS, POSTCODE_DECLINED, CVV_DECLINED, ADDRESS_DECLINED, FAIL, PAYMENTS_SYSTEM_ERROR, REFERRAL, CV2AVS_DECLINED, 3DS_TXN_CANNOT_BE_AUTHORIZED, PENDING, CHALLENGE_REQUIRED, AUTHENTICATION_REQUIRED, PROCESSING`, plus `INITIATED` on receipt.
- **Ledger double-entry pattern:** a clearing ledger sits between account and bank ledgers. Group 1: account-ledger −, payment-request-clearing +. Group 2: payment-request-clearing −, bank-ledger +. 🟡 To be detailed.
- **Volumes:** card ~10,000–50,000/day depending on traffic; PayID 2,000–3,000/day.
- **Entities:** IG JP, IG US, IG AU, IG GB, IG FR, IG DE. **Products:** IGCFD, IGSTK, IGFNO, IGCRY.
- **Team:** 7–8 engineers. Most applications predate the current team; the team builds and maintains the newer ones. Author's role: **developer**, 3.5 years in the domain, has built multiple applications solo.

## Area 10 — Contributions

Captured in full in §11 of the domain model. Deferred items:

- CardPayments and Payments Gateway specific features/migrations — to recall
- Production incidents diagnosed or led — to recall
- Proudest two or three pieces of work — to share
- Webhook testing strategy — deferred
- Double-entry ledger detail — deferred

---

# Part C — Elicitation method

For reuse if this exercise is repeated for another domain. The sequence that worked:

1. **Read back before probing.** Restating the brain-dump surfaced the transcription errors and the PG-holds-state misconception immediately, before either could propagate.
2. **Inventory first, flows second.** Naming all 18 applications up front revealed which flows existed at all — including two (ACH Payments, Payments Orchestrator) that the initial list omitted.
3. **Ask what *doesn't* happen.** The most valuable answers came from failure-path questions: missing webhooks, duplicate callbacks, abandoned sessions, failed ledger posts. Happy paths were already well recalled; safety nets were not, and they turned out to be the actual architecture.
4. **Follow the money's direction.** Deposits and withdrawals looked symmetric in the brain-dump and turned out to be radically different — instant/automated versus batch/dual-signed. Withdrawals held most of the controls.
5. **Record boundaries as content.** "Not my team" answers (ledger, KYC, rates, MFT, routers) defined the domain's edges more precisely than any inside-the-boundary answer.
6. **Separate designed from implemented.** Asked explicitly per project, this produced the growth narrative that a flat contribution list would have hidden.
