# conversation.md

Near-verbatim transcript of the knowledge-elicitation session that produced `ig-payments-domain-model.md` and `ig-payments-elicitation-record.md`.

Order is chronological: each of my inputs, followed by the questions and clarifications given back to me.

---

## Turn 1 — Me (initial brain dump)

> I want to explain the project flow here. Um, I work in the payments domain. Anything that our payments stand is handled by us. Uh, there can be deposits, withdrawals, or currency conversions between the two accounts and stuff like that. Uh, that all comes under us. The payments can be cut payments, bank payments, PayPal, fast payments, which is, like, a, you know, popular in Australia. The way we have UPI in India. So all that sits in the front end and get supported by a common gateway called payments gateway in the back end. The work of payments gateway is to authenticate, uh, the request that is coming from the user structure header and the application executing token or, you know, JWT token in the newer models, um, as we call it, uh, and pass it on to the respective applications. So now let me go to a little... no. Go go to little details. Um, we have two modes, deposit and withdrawal. For deposits, uh, what will happen is we'll have to, you know, give different options based on the country. IG supports several countries, so certain modes will be popular in certain countries. Card is pretty much popular in UK, US, and many other countries. Um, but, you know, on the other hand, Japan doesn't have the card. It only supports bank. While you know Australia, we have been on your PID feature, which is, like, equivalent of UPI. So depending on the country, we'll be supplying with the payment methods that are there. Um, also, there can be multiple modes of payment for a given country. So, you know, depending on whichever is popular, we'll, you know, assign priority number to that one. Um, all these have to be supplied by the payments gateway, uh, depending on the region. So what all is available along with the priorities gets supplied. When the deposit button is clicked, they'll see the UI, uh, which all options have... they have available. Now the payments gateway's job is to redirect the request based on whichever request the guys pressing on. Let's say, you know, he presses some PID. Um, so we go to the next screen, which is related to PID. This application needs to redirect to the PID's back end application. There are certain validations are done and everything is fine. The money will be credited to the, uh, guys' account. This is, like, high level four. So going a little deep, now we have Aka mine the front. Um, if it allows, then, you know, um, depending on that router, um, I check proxy. Uh, now we'll send the request out to one of the instances of the payments gateway. once payments get we receives it, it sees, like, you know, which request the guy is making. So let's say it is card payments, it will send the request next to the internal router, which, you know, again, sees, like, whichever application is available. And, you know, it redirects to that particular instance. So that way, you know... and, yeah, there is the, like, you know, the... and, yeah, the URL will be, like, router hyphen in slash card payments. So depending on, like, the verb resource card payments, it will figure out that, you know, this request has to go to card payments.
>
> This is my project domain from the mind map that I could immediately recollect. Identify what all I've missed, probe me more to create a detailed layout of my work domain. Please note I've not built all these apps but I've significant contribution in many of these.
>
> The end goal is to find and share the entire domain model that I've worked on.
>
> If my instructions are unclear and you have several paths to go about this, please ask questions first get good clarity and move further don't assume anything. This is very important part

---

## Turn 2 — Claude (read-back, gap list, framing questions)

Good starting point. Let me first read back what I actually captured, so you can correct my understanding before we go deeper.

**What I have so far**

- **Domain**: payments for IG — deposits, withdrawals, and currency conversion between accounts. Anything money-in/money-out sits with your team.
- **Payment methods**: card, bank transfer, PayPal, and local fast-payment rails (PayID/NPP in Australia, analogous to UPI).
- **Payments Gateway (PG)** is the common backend entry point. Two jobs: (a) authenticate the inbound request — session token in older flows, JWT in newer ones — and (b) route to the right downstream payment application.
- **Method availability is country-driven**: card in UK/US, bank-only in Japan, PayID in Australia. Multiple methods per country, each with a priority number. PG serves the eligible-methods list + priorities to the frontend, which renders the deposit options.
- **Routing path**: Akamai at the edge → external router / proxy → one instance of PG → internal router → the specific payment app instance. Path-based routing, e.g. `router-in/card-payments`.
- On success, funds are credited to the client's account.

**Gaps I can already see** — not asking you to answer these now, just so you know where I'd push:

1. **Withdrawals** — you named the mode but the flow is untold. Payout rails, back-to-source rules, approval queues, batching.
2. **Currency conversion** — in scope but unexplained. Rate source, spread, multi-currency accounts.
3. **Who actually moves the money** — PSPs/acquirers behind card, 3DS/SCA, tokenisation, PCI scope.
4. **Async reality** — PSP callbacks/webhooks, pending states, the payment state machine, idempotency, retries, timeouts.
5. **Money truth** — ledger, balance service, reconciliation, settlement files.
6. **Compliance gating** — KYC tiers, AML/sanctions, fraud engine, deposit/withdrawal limits, client-money rules.
7. **Refunds, chargebacks, disputes.**
8. **Eligibility beyond country** — currency, account type, retail vs pro, amount limits.
9. **Stack and infra** — languages, messaging, datastores, multi-region/DR, observability.
10. **Back-office** — what finance ops/treasury tooling touches your systems.
11. **Your actual footprint** — which apps you contributed to and what you specifically owned.

Before I start probing properly, three things fork the path significantly:

*[Interactive questions presented]*

1. What's this domain model ultimately for? — Interview prep / Onboarding doc / Personal knowledge map / Architecture reference
2. How deep should the final model go? — System-level / Per-application / APIs, data models, state machines / As deep as I can recall
3. How do you want to work through it? — Area by area / Everything at once / Brain-dump more first

---

## Turn 3 — Me (framing answers)

> **Q: What's this domain model ultimately for?**
> A: 1, 2, 4 — Interview prep / showcasing my experience; Onboarding doc for my team; Architecture reference / handover doc
>
> **Q: How deep should the final model go?**
> A: As deep as I can recall
>
> **Q: How do you want to work through it?**
> A: You ask me questions area by area

---

## Turn 4 — Claude (agenda + Area 1)

Good — that combination means the final artifact needs to be technically accurate, readable by a newcomer, *and* clearly mark what you personally owned versus what you touched. I'll keep track of that distinction as we go.

**Proposed agenda** (I'll work through these in order, adjusting as your answers reveal new territory):

1. Application inventory & landscape
2. Deposit flow, end to end
3. Withdrawal flow, end to end
4. Currency conversion / multi-currency
5. PSP & external integrations
6. Async behaviour, state machines, failure handling
7. Money truth: ledger, balances, reconciliation, settlement
8. Compliance, risk, fraud gating
9. Auth & security model
10. Infrastructure, stack, deployment topology
11. Back-office & ops tooling
12. Non-functional characteristics (scale, SLAs, incidents)
13. Your specific contributions & projects

One request: when you don't know something, say "don't know" or "not my area" rather than skipping it. For an onboarding/handover doc, the boundaries of your remit are useful content, not a gap.

**Area 1 — Application inventory & landscape**

1. **Name the actual services** as you'd call them internally. You've given me Payments Gateway, card payments, bank payments, PayPal, PayID. What else exists in the estate? I'd expect things like an eligibility/config service, a ledger or balance service, a refunds service, a reconciliation service, a notification service, a back-office admin app. Rough list, real names if you recall them.
2. **Granularity of the payment apps** — is it one app per payment method globally (one card-payments service serving all countries), or per method-plus-region, or do several methods share one app?
3. **Where does the country → method → priority config actually live?** Hardcoded in PG, a separate config/product service, a database table, a feature-flag system? And who changes it — engineers via deployment, or ops/commercial teams through a UI?
4. **Frontends** — how many consumers does PG have? Web trading platform, iOS, Android, mobile webviews, partner/white-label? Do all of them go through PG, or do some paths bypass it?
5. **Is Payments Gateway one deployable or a family?** E.g. separate deposit and withdrawal gateways. And is it stateless, or does it hold session/transaction state?
6. **Deployment regions** — is the estate stood up per region (UK, EU, APAC, US) with separate instances and data residency, or is it one global stack with country logic inside it?
7. **Legacy vs modern split** — you hinted at session tokens giving way to JWT. Is there a broader old-world/new-world divide? A monolith being decomposed, a strangler migration, two generations of payment apps running side by side?
8. **Your footprint on this list** — for each service you named, which bucket: built it, owned it, contributed features, occasional changes, or just consumed it?

---

## Turn 5 — Me (application estate)

> 1. we call the applications:
>    1. Payments gateway
>    2. Card payments
>    3. Bank deposits
>    4. Bank withdrawal
>    5. PayPal payments
>    6. PayPal withdrawal
>    7. Australian fast payments
>    8. Bank maintenance
>    9. Open banking
>    10. Card validation service
>    11. PSP maintenance
>    12. PSP integration service
>    13. Wallet payments
>    14. Cash In transit
>    15. Bank postings
>    16. Funds transfer service
> 2. Yes, there is only one common application that serves all the countries, but there are several instances of it. There is no sharing. CardPayments has its own application, PayPal has its own application, and PayPal withdrawal has its own application. It's a microservice architecture.
> 3. Under Payments Gateway, we have deposit options, and in that, we have the country method priority config, which is where lives. It's hard-coded in Payments Gateway. It is changed by the code change. There is no configuration as such. As this is not that frequently changed
> 4. There is "My-IG" (web), then there is "Internal-platforms" also called "IGIP", then we have Hydra and internet-monitor, which are internal. There are also Android, iOS, and web trading platform. It's worth noting that external and internal clients, or internal admins, come to the same payment gateway.
> 5. Payments gateway is one application which handles both withdrawal and deposits. It's a front controller, and it delegates the request work to the applications. I don't know what you mean by stateless. It holds session transactions. I need to know more about this. Please ask a follow-up question.
> 6. Traditionally, there is a single data center that is there in the UK. I mean, it's a data center pair: one active, one on standby, but the region is just one single UK region.
> 7. There is no world divide. It's an enhancement that is being done internally. Let's ignore this. It's fine. There is no monolith. CardPayments is a microservice that handles both JWT, XST, and CST.
> 8. I've contributed to:
>    * payments gateway
>    * CardPayments
>    * I have now completely redeveloped bank deposits.
>    * worked on bank withdrawal
>    * PayPal withdrawal, PayPalPayments - I have not worked on.
>    * Australian fast payments, which is entirely built by me.
>    * Bank maintenance: I was a major contributor.
>    * Open banking: I was a major contributor.
>    * Card validation service: I have not made much of a contribution, but I have a pretty good idea of it.
>    * PSP maintenance and PSP integration: I have a pretty good idea of them.
>    * Wallet payments: I don't have much of an idea of it.
>    * Cash in transit: I don't have much of an idea of it.
>    * Bank postings: I haven't developed it, but I was the point of contact for this one, so I have a pretty good knowledge of it.
>    * Funds transfer service: I don't have much of an idea of it.

---

## Turn 6 — Claude (stateless explained + Area 1 continued)

Noted the contribution map — I'll tag every component in the final doc with your involvement level.

**On "stateless" (your follow-up)**

Stateless means the service keeps nothing about a request in its own memory between calls. Any instance can serve any request, because everything needed is either in the request itself or fetched from a shared store (DB, cache, session service). Stateful means an instance holds something in local memory — a session map, an in-progress transaction — so the *same* instance must handle follow-up calls, which forces sticky sessions and makes a node dying mid-flow destructive.

You said PG "holds session transactions", so the question splits three ways:

- **1a.** When a deposit spans multiple calls (options screen → amount entry → PSP redirect → callback), does PG hold that in-progress transaction in local memory, or write it to a database/cache (Redis, Hazelcast, Coherence) that all instances can read?
- **1b.** Does the load balancer use sticky sessions / affinity, so a client stays pinned to one PG instance? Or can call 2 land on a different instance than call 1?
- **1c.** If a PG instance is killed mid-deposit, does the user's deposit die, or does it recover on another instance?

**Area 1, continued**

Your list has 16 apps, several of which I can't infer the responsibility of, and a few things I'd expect are conspicuously absent.

**Define the ones I can't guess** — one or two lines each on what it does and who calls it:

2. **Bank maintenance** — is this CRUD over the client's saved bank accounts (add/verify/delete), or maintenance of *IG's* banking config (which bank accounts IG holds per currency/country)?
3. **Open banking** — is this the UK/EU AIS/PIS integration? Used for deposit initiation (PIS), account verification, or both?
4. **PSP maintenance** vs **PSP integration service** — what's the split? One sounds like config/onboarding of providers, the other like the actual outbound calling. Which is which?
5. **Card validation service** — BIN lookups, card eligibility rules, 3DS, or something else?
6. **Wallet payments** — which wallets? Apple Pay/Google Pay, or e-money wallets like Skrill/Neteller?
7. **Cash in transit** — my guess: tracking funds that have left the client but aren't yet settled. Right?
8. **Bank postings** — is this the accounting/ledger side, posting entries to the client's trading account and the general ledger?
9. **Funds transfer service** — is this the internal account-to-account movement, including the currency conversion between two accounts you mentioned at the start?

**Absent from the list** — for each, tell me whether it exists under a name you didn't mention, sits in another team, or doesn't exist:

10. **Currency conversion / FX rates** — who sources rates and applies the spread?
11. **Refunds and chargebacks** — where do those live?
12. **Reconciliation** — matching PSP settlement files against internal records.
13. **Limits, risk, and fraud checks** — per-transaction and cumulative deposit limits, fraud scoring, sanctions/AML screening.
14. **KYC / account status** — what gates whether a client is even allowed to deposit or withdraw?
15. **Notifications** — deposit-confirmation emails, failure alerts.

Finally:

16. **Internal admins hit the same PG as external clients** — this is interesting and I want it accurate. Do IGIP/Hydra/internet-monitor use the same endpoints with elevated privileges, different endpoints on the same app, or the same endpoints with a different auth token type? And what do admins actually do through it — manual deposits, refunds, forcing a stuck payment, viewing history?

---

## Turn 7 — Me (card flow + application definitions)

> Payments gateway only acts as a router, so it doesn't hold any state as such, if I'm not wrong. What happens is it sends the data to CardPayments. CardPayments will figure out whose client account this is and stuff like that, and make that transaction to the ledger, so CardPayments maintains all the DB records.
>
> To explain this, we have a frontend application called CardPayments, which renders all the screens. When the client clicks on card, we give the popup to enter the card details. And also, he enters the amount. The call to add card and deposit goes to the CardPayments, depending on the second resource name /CardPayments. Now, the CardPayments application does some verification. If all is good, then it makes a call to PSP through the PSP integration service. The PSP details themselves are obtained from the PSP maintenance. Once the PSP integration service receives that, it gives the challenge screen wherein the client has to enter the OTP. Once OTP is entered, PSP does a webhook callback, which again goes through the payments gateway and comes to CardPayments. Once the successful message has been received, CardPayments does the ledger posting. Once ledger posting is done, it immediately sends the email in an async manner. While it has received the request for the first time from the payments gateway, it will mark the transaction in the initiated state. When the webhook has been received, the transactions will be marked as completed.
>
> I'm not aware of the load balancer, whether it is a sticky one or not. It is out of our domain.
> I don't know what happens when the payment gateway dies is in between. This scenario has never come.
>
> * Bank maintenance maintains the record of a client's bank account. This is necessary for withdrawal, so it adds, deletes, and now does the credit operation on the bank account of the client.
> * Open banking: this is the equivalent of PSP in the bank environment. It talks to the integrator of banks, where the verification, which usually used to be done manually, will be done through a third-party provider called Plaid
> * PSP maintenance maintains the credentials of the PSP, which country should go to which PSP, and other configurations like that. While the PSP integration service does the actual talking between CardPayments and external PSPs, it is the integration point between CardPayments and external PSPs.
> * Yes card validation service is for bin lookup.
> * Currently, wallet payments only allow Apple Pay.
> * Cash in transit is like some payments take 2 to 3 days for a certain amount. When the person gives proof of payment, we upfront credit them, and once the money is back in, we get the money.
> * Bank postings are like the bulk batch deposit of money, wherein we have integrated with several banks (HSBC, Lloyds, Standard Chartered, etc.), which gives us a bulk file. We read through those files and post the ledger to the ledger team using the bank transfer.
> * Yes, this is the account movement between CFD account, stock broking account, etc.
> * Yes, there is a separate fund application for currency conversion.
> * Refunds can happen only when we are not aware of the client to whose account we should associate this money. This will be done manually by the operations team.
> * Reconciliation is done by an application called AutoRec, and it is also taken care of by the operations team.
> * Each application does its limits, risk, and fraud checks. Let's say:
>    * CardPayments does for CardPayments
>    * Bank Deposit does for Bank Deposits
>    * PayPal does for PayPal
> * KYC account status is done outside this payments domain, so it will be like the account opening domain is there, which will already have activated the account. Upon that only, we get the payment requests.
> * Asset notifications will also be taken care of by the individual application. Upon doing the ledger transaction/ledger posting, it also sends out the email notification in a sync manner using AMQ.
> * For the internal admins part, we have two kinds of tokens:
>    * Customer Security Token (CST)
>    * X Security Token (XST)
>  External guys who are coming will come with the CST token that gets verified, and they'll be allowed access to all the external points. XST users will be coming with the XST token and will have the associated roles and can only access if the required role is there in the token.

---

## Turn 8 — Claude (card flow read-back + Area 2 deep dive)

Now I have a proper picture. Let me play back the card deposit flow as I understand it, then probe the edges.

**Card deposit, as I now hold it**

1. Client hits the deposit options screen. PG serves the eligible methods + priorities from its hardcoded country/method/priority config.
2. Client picks card → card frontend renders the card-entry popup (card details + amount).
3. Add-card / deposit call → Akamai → external router → PG instance → internal router → CardPayments, routed on the second path resource `/card-payments`.
4. CardPayments does its own validation, limits, risk/fraud checks. Resolves which client account this belongs to. Writes the transaction as **INITIATED** in its own DB.
5. CardPayments → PSP integration service → external PSP. PSP credentials and country→PSP mapping come from PSP maintenance. BIN lookup via card validation service.
6. PSP returns a challenge screen; client enters OTP.
7. PSP fires a **webhook** → back in through PG → CardPayments.
8. On success: CardPayments marks the transaction **COMPLETED**, posts to the ledger, and fires an email notification over AMQ.

Two things I want to flag before questions. First, PG is doing double duty — client-facing router *and* inbound webhook receiver, which are very different trust boundaries. Second, "initiated" and "completed" is only two states, and the interesting engineering is in everything that isn't those two.

**Area 2 — Deposit flow, deep dive**

*Naming*
1. You said "a frontend application called CardPayments" and also CardPayments as the backend service. Are these two separate deployables sharing a name, or one app serving both UI and API? Same question for bank deposits.

*The webhook path — where I most want detail*
2. A PSP webhook arrives with no CST/XST token. How does PG authenticate it? IP allowlisting at Akamai, mTLS, HMAC signature, shared secret, basic auth?
3. Does the webhook hit a different PG endpoint/path than client traffic, or the same one?
4. **Duplicate webhooks** — PSPs retry. If the same success callback arrives twice, what stops the ledger being posted twice? Idempotency key, DB unique constraint, state check on the transaction row, something else?
5. **Missing webhook** — client completes the OTP, PSP takes the money, but the callback never arrives (network drop, PG down, PSP bug). The transaction sits at INITIATED forever. What catches it? A polling job that queries the PSP for status, a timeout sweeper, AutoRec picking it up next day, or does someone raise a ticket?
6. **Client abandons** — they close the browser at the OTP screen. Does anything clean up the INITIATED row?

*State machine*
7. What's the **full set of states** a card deposit transaction can be in? Beyond INITIATED and COMPLETED I'd expect at least FAILED, REJECTED, PENDING, CANCELLED, EXPIRED. Give me the real ones you use, and which transitions are legal.
8. Is the state stored as a column on the transaction row, or is there an event/audit table recording every transition?

*Ledger posting*
9. **How** does CardPayments post to the ledger? Synchronous REST call to a ledger service, an AMQ message, a DB write?
10. This is the sharpest failure mode in the whole flow: the PSP has taken the money, the webhook succeeded, then **ledger posting fails**. Money left the client, nothing credited. What happens? Retry loop, dead-letter queue, compensating transaction, ops alert and manual posting?
11. Is the ledger owned by your team or by a separate "ledger team"? You mentioned posting "to the ledger team", which sounds external.

*Card specifics*
12. **Does CardPayments ever see the raw PAN?** Or is the card-entry popup a PSP-hosted iframe / tokenised field, so the PAN never touches your servers? This determines your PCI-DSS scope and I want it right.
13. **Stored cards** — clients can add a card. Where does the token live, yours or the PSP's? Can a stored card be reused across PSPs?
14. **3DS / SCA** — is the OTP challenge 3DS2, or a PSP-proprietary step? Do you handle frictionless flow and exemptions?

*Money mechanics*
15. **Currency** — if the client's card is USD and their trading account is GBP, who converts? The PSP, your funds/FX application, or is the deposit rejected?
16. **Limits and risk in CardPayments** — what are the actual checks? Min/max per transaction, daily/monthly cumulative, velocity, card-country vs account-country mismatch, blocked BINs, first-deposit rules?

*One correction to confirm*
17. You said notifications go out "in a sync manner using AMQ" but earlier said async. AMQ implies fire-and-forget async. Which is it — does CardPayments block waiting for the email to send, or drop a message and move on?

---

## Turn 9 — Me (Area 2 answers)

> * there is no frontend application for CardPayments that could have been a mess
> * Frontend application is called FE-Payins.
> * So, the webhook doesn't carry any XST or CST, as said. How the payments gateway does this is that it makes a call out to the PSP integration service. The PSP integration service validates the given details with the respective PSP, and if that is valid, it will return back with the validation rule. The PSP then strips off that header, adds its own application XST or JWT token, and forwards it to the CardPayments.
> * In each of the PSPs, we'll have configured the webhook callback URL, which will be a different token that goes like /deposit/event.
> * DB unique constraint blocks the duplicates.
> * When the transaction remains in the initiated stage, there is a batch job that runs and picks all the initiated transactions. It verifies against the PSP-specific endpoint, where we can verify if this transaction has gone through, and we update that. It's a batch job, but if there is anyone who immediately wants that, they call in the operations team. The operations team checks that manually and posts on the customer's behalf.
> * There is a day-end job which Autorx takes up and verifies all the transactions of the given day. If there is anything that is pending in the initiated state, it marks that as abandoned or failed.
> * States: APPROVED, DECLINED, BANK_DECLINED, AUTHENTICATION_FAILED, INSUFFICIENT_FUNDS, POSTCODE_DECLINED, CVV_DECLINED, ADDRESS_DECLINED, FAIL, PAYMENTS_SYSTEM_ERROR, REFERRAL, CV2AVS_DECLINED, 3DS_TXN_CANNOT_BE_AUTHORIZED, PENDING, CHALLENGE_REQUIRED, AUTHENTICATION_REQUIRED, PROCESSING
> * Yes, it is stored as a state on the DB transaction table.
> * An asynchronous API call is made to the ledger service team, which takes care of adding the ledger to accounts, the given account ID, and stuff like that.
> * This is out of scope of our application, so we fire and forget. It is the Ledger team's job to ensure that money goes to the client.
> * This ledger is owned by the nextmail team.
> * Pan never comes to the server, so is stored/logged always as a masked number along with the bin number that will get it. However, we do handle the card numbers in the frontend, hence our application needs to be PCI compliant.
> * The added card gets a token that is stored in the `card_token` table in the CardPayments application itself in its DB.
> * It is a 3DS2. Yes, we also have frictionless flow. Whenever an internal user tries to deposit on a user's behalf, it is a frictionless flow.
> * Currency conversion happens in-house. We have a few fixed rates for USD to GPP. We use that, and we convert currency using that.
> * A sync is actually a sync. CardPayments doesn't wait for any email to get sent out. It immediately continues with its next task. It's an async job.

---

## Turn 10 — Claude (five confirmations + Area 3, bank deposits)

Useful. Several things there change my picture materially. Let me tighten those, then move to the flows you built yourself — I'm reordering the agenda, because bank deposits, Australian fast payments and open banking are your signature work and deserve the most space in the final doc.

**Five things to confirm or correct**

1. **The webhook auth chain.** My reading: PG receives the callback on `/deposit/event`, calls the PSP integration service to validate it against the PSP, the *integration service* strips the PSP header and stamps on its own XST/JWT, then forwards to CardPayments. You wrote "the PSP then strips off that header" — I assume you meant the PSP integration service, not the external PSP. Correct?
2. **That state list is mostly PSP outcomes, not lifecycle states.** DECLINED, CVV_DECLINED, POSTCODE_DECLINED, INSUFFICIENT_FUNDS, CV2AVS_DECLINED are reasons a card was refused. But earlier you described INITIATED → COMPLETED, and the sweeper marks things ABANDONED/FAILED. So: is there **one status column** holding all of these values mixed together, or **two** — a lifecycle state plus a separate PSP result/reason code? This matters a lot for how I draw the state machine.
3. **Fire-and-forget ledger call.** You've said the async API call to the ledger service is out of your scope and it's the ledger team's job. As written, that means a dropped ledger call is invisible to your side. Is that actually true, or is there a safety net — retry, DLQ, or does AutoRec's day-end reconciliation catch a deposit marked complete with no matching ledger entry?
4. **"nextmail team"** — I suspect that's a transcription slip. What's the real name of the ledger-owning team or system?
5. **Frictionless flow.** In 3DS2, "frictionless" normally means the issuer waves the challenge because risk data looks clean. You've described it as what happens when an internal user deposits on a client's behalf. Are those the same mechanism — an SCA exemption flag you set for internal deposits — or are you describing two different things?

**Also still open on cards**
6. What are the actual **limits and risk checks** CardPayments applies? Min/max amount, daily or monthly cumulative caps, velocity checks, card-country vs account-country mismatch, blocked BINs, first-deposit-must-match-name rules?
7. Can a `card_token` be used across multiple PSPs, or is a token bound to the PSP that issued it? (If a country's PSP mapping changes in PSP maintenance, do stored cards break?)

**Area 3 — Bank deposits (you rebuilt this end to end)**

8. **Why the rebuild?** What was wrong with the old one, what was the scope of the redevelopment, and roughly when/how long? This is the kind of thing that carries weight in an interview, so I want the story, not just the architecture.
9. **The flow.** Walk me through a bank deposit the way you did for cards: client clicks bank transfer → what screens, what does the app do, where does the money physically go, when does the ledger get posted?
10. **Which bank rails?** Faster Payments, SEPA, SWIFT, domestic transfers per country? And is this push (client pushes money to IG's account and quotes a reference) or pull (direct debit)?
11. **Reference matching.** If the client pushes money to IG's bank account, something has to match that incoming credit to a client. Is that where **bank postings** and the bulk bank files (HSBC, Lloyds, Standard Chartered) come in? Draw me the line between bank deposits and bank postings — right now they feel adjacent and I don't know where one ends.
12. **Timing.** A bank deposit isn't instant. Is the client's account credited immediately on intent, or only when the money actually lands in the file? Is **cash in transit** the mechanism that bridges that gap?
13. **Open banking's role.** Is open banking / Plaid used *within* the bank deposit flow to initiate the payment (PIS) and skip the manual reference-quoting, or is it purely for verifying that a bank account belongs to the client (AIS) as part of bank maintenance?
14. **Your rebuild's tech choices** — language, framework, datastore, messaging, anything you introduced that the old version didn't have. Tests, migration strategy, how you cut over without dropping live deposits.

---

## Turn 11 — Me (Area 3 answers)

> 1. No, it's the other way around. In the HTTP filter, the payments gateway calls the PSP integration service to validate the payload and the header. If they are fine, the call comes back to the HTTP filter. It sees it as validated, and then in the next step, we remove that filter and add PG's XST token.
> 2. There is only one column holding all these states.
> 3. No, job is not on our end. Only the Ledger team or other teams take care of this. We just fire and forget.
> 4. It is the ledger service team.
> 5. Generally, we enforce the 3DS2 mechanism for almost all the cards. We waive it only in the frictionless flow, that is, by an internal user. But yeah, there are certain countries wherein 3DS2 is not enabled by default, and there is no frictionless flow. In those cases, it is the same for both.
> 6. Yes, minimum/maximum amount, daily caps, card country, account country mismatch, all those things are done. Bin blocks are also checked. It also checks allowed types. In a few countries, credit cards are not allowed, so all those checks are also done. Name validation is also done.
> 7. For every given PSP, there will be a different token associated. For Worldpay, there will be one. The same card registered on Noire will have a different one, the cards won't break, while registering. We'll register it for all the available psp configurations.
> 8. Bank deposits was specifically for Japan. The old one was legacy code, and it had lots of issues. It wasn't even a Spring Boot application; it was Spring 3 or 4, I believe. That was how old it was. So, further, what we did was we recreated the application as it was a small one and very specific to Japan. We migrated that onto the cloud. The scope to entirely redevelop the application it took nearly 3 to 4 months for us to rebuild this application. Ask if you need any further information.
> 9. In Japan, there are only banks allowed, so quick bank deposit is the major money-in there are several supported banks which we display on our FE-Payins application for Japanese folks. Among the available banks, the client chooses the one in which he has an account. And you know the money he wants to deposit. Further, the BJP is the aggregator. The call goes to the external pop-up, which is opened, and the call goes to BJP. The client logs in with his bank credentials. And he does a payment, and the redirection goes to BJP, and BJP calls our application. Once we receive the redirection, all we'll have to do is post the ledger transaction and send the email out. I can give more details if that is needed.
> 10. The bank deposits: we only handle Japanese clients. SEPA/SWIFT faster payments were handled in different applications. Faster payments were specifically for Australia, it's handled in Australia fast payments. SWIFT is handled using bank postings.
> 11. Yes, bank postings come into that picture. The client has to add his account ID as a reference in his payment in the comments so that it appears in the bank postings file. The files are CAMT and FIN. In one of the references (like secondary reference, primary reference, or related reference), the account ID will have been captured. And against that, we run some validations, and if everything is fine, we post the ledger to the ledger service. Bank deposits are specifically for Japan, and bank postings are for any other country.
> 12. Bank deposits are instant, but bank postings are not. Bank postings will only happen whenever we receive a bank file from the respective banks.
> 13. Open banking is specifically used for IG US clients during the ACH flow. We'll have to verify the client's bank account details. For that, we used to have it done manually by the admins, Which used to delay a lot, and now we have Plaid, which auto-verifies the bank account. Unlike the PSP integration service, this is not during the transaction, but before the transaction, when we want to verify the bank account.
> 14. The old version was a Spring framework application. The application had mainly four endpoints:
>    1. To initiate the transaction
>    2. To hear the callback
>    3. For manual deposit
>    4. For giving the configuration out to clients...The configuration was which all banks are available and stuff like that. What is the transaction ID that the current flow is associated with? I can give more information if needed

---

## Turn 12 — Claude (carry-forwards + Area 4, Australian fast payments)

Two things there are significant beyond the immediate answers: you've got a **hybrid estate** (data-centre pair in the UK plus cloud, since you migrated bank deposits there), and the **single status column** mixing lifecycle and PSP decline reasons — I'll represent that faithfully rather than tidying it up, but flag it as a known wart if this doc is for onboarding.

**Carry-forwards I still need**

1. **Your new bank deposits app — the tech.** You gave me the old app's four endpoints. I want the rebuild: Spring Boot version, Java version, which cloud (AWS? which services — ECS, EKS, Lambda?), datastore, messaging, CI/CD, test strategy. And the **cutover** — how did you switch Japan over without dropping live deposits? Big bang, dark launch, parallel run, feature flag?
2. **"BJP"** — I don't recognise this aggregator, and I suspect a transcription slip. What's the actual name?
3. **Japan flow gap.** BJP redirects back to your app and you post the ledger. Is there also a **server-to-server webhook**, or is the browser redirect your *only* signal that money moved? If it's redirect-only, a client closing the popup after paying is a lost deposit — how is that handled?
4. **Manual deposit endpoint.** Who calls it (IGIP admins with XST?), in what circumstances, and what stops abuse — dual approval, audit trail, amount ceiling?
5. **Open banking / Plaid.** So this is **IG US, ACH**. Which raises: is there a **US ACH deposit/withdrawal application** in the estate? It's not in your 16. Does ACH ride on CardPayments, bank postings, or something outside your team?

**Area 4 — Australian fast payments (you built this outright)**

This is the one you own end to end, so I want it in the most depth.

6. **Which rails exactly?** PayID, or the full NPP/PayTo set? Is it deposit-only, or withdrawal too?
7. **Why was it built** — what triggered the project, what did Australian clients use before, what was the business case?
8. **The flow** — screen by screen, service by service, the way you did for cards and Japan. Where does the client's money physically go, and what's your signal that it arrived?
9. **The integrator.** Is there an aggregator/PSP in the middle (Zepto, Monoova, Cuscal, Azupay?), or do you talk to a bank directly? Does it go through the PSP integration service, or does this app have its own outbound integration?
10. **PayID mechanics.** Does IG issue a PayID per client, per transaction, or one shared PayID with a reference? This determines how you match an inbound credit to a client, and it's the crux of the design.
11. **Speed and confirmation.** NPP settles in seconds. Is the credit truly real-time, and do you post the ledger synchronously on receipt?
12. **Failure and edge cases you had to design for** — client sends the wrong amount, sends from a bank account not in their name, sends to a stale PayID, duplicate payments, money arrives with no matching reference. What did you build for these?
13. **Regulatory constraints** — anything AUSTRAC / ASIC specific that shaped the design?
14. **Scale** — rough volume of Australian fast payments transactions per day, and what your app's throughput/latency profile looks like.
15. **What was hardest**, technically, and what would you build differently now? For the interview-prep angle this is often the most valuable single answer in the whole document.

---

## Turn 13 — Me (Area 4 answers + Japan architecture)

> 1. The old Spring Boot/Spring Framework application was Spring 3 or 4, so we had to redesign the entire application. The application had four endpoints, so it was pretty much simpler to divide that. The main functionality was to display the configuration along with the associated transaction ID. When a transaction is made across that, we would mark the transaction as initiated in our DB, and upon listening for a redirect call to /result, we would proceed to do the transaction manually. There could be a few failed transactions. For that, we had a manual deposit endpoint also. As this was a smaller application, we divided the application into multiple lambdas. One was Spring Boot Lambda, which was giving the CardPayments configuration, listening to the initiate call and also listening to the redirect for the webhook. Then we had another lambda for for reconciliation of the files, which was being done in the same Spring Boot application, we rather split it up, and it was there in a separate Lambda. For this lambda, we used Quarkus. The architecture goes like this: in the frontend, the client selects quick deposit transactions. The call is made to the first lambda, which gives the configuration of which all banks are available, along with a token which later will be verified when the redirect comes back. A transaction ID with which you now will be referring to the entire journey then the client selects the bank account and enters the amount. The bank page is opened in a new pop-up. While the bank page is being opened, we also do an /initiate call to our lambda. The client enters his credentials. And logs into his bank account and does the transaction once the transaction is done, BJP (that is, Billing Japan) will send us the redirect back the same lambda will be listening on that redirect call. And adds the transaction to the DynamoDB table. When a transaction is added to a DynamoDB table, a streams call is made to a new Lambda, which is called a DynamoDB streams listener. Which is in Quarkus its job is to simply read that transaction and mark it for posting to the ledger. And send email. The other lambda which I seid for file reconciliation, will pick the transactions which are in the initiated state. Against the received file from Billing Japan, it verifies if the transaction has succeeded. Upon success, we post the ledger to the ledger service.
> 2. BJP stands for Bill in Japan.
> 3. There is no server-to-server webhook. It's just a browser redirect. During the redirect, we will have gotten the token which was shared during the configuration that we had loaded. If the transactionId matches, then we'll go for the posting of the ledger.
> 4. Yes, admins with access tokens call that only when you know customer calls in, and he can't wait for the reconciliation to run. At that time, an internal admin user verifies the transaction and does the posting on his behalf.
> 5. Yes, there are US ACH deposits also. The application name is called ACH Payments.
> 6. Currently, we only support PayID and no PayTo. Yes, it is deposit only.
> 7. Before Fast Payments, PID customers were using only card, which was the only instant mode. With Fast Payments, there are two instant modes now.
> 8. PayID, unlike other modes, is a little decoupled. Similar to how bank postings work in bank postings, no client adds his account ID to the transaction and does the transaction. We then, in a decoupled way, match for that account ID when we receive the file, and we post the money to the client. In a similar manner, PayID works. Whenever a user clicks on the PayID screen, we generate a new PayID for his account, which goes like some number@igau once this PayID is registered for a client and IG the client then goes to his bank account and registers this PayID. And from that point onwards, he can make the transaction. The transaction goes and hits Azupay. Azupay talks to NPP. Which is supported by National Australian Bank. Once the transaction goes through Azupay sends us the webhook callback back. This application is also built on the cloud. There are two endpoints on the Lambda: first - Generating the PayID, which renders the PayID onto the frontend. second - the PayID notifications endpoint, which listens to the webhook call from Azupay. Both these sit on AWS API Gateway. For the first endpoint, CST is the validation mechanism. And for the second one, we add a transaction token for a particular client for all the upcoming transactions. Azupay keeps sending this back for every transaction if the transaction ID is compromised. We'll have to Refresh this. Unfortunately, this is the only mechanism because Azupay keeps sending this in the header, and there is no way we can keep sending a new transaction for the given client. Once registered, this header is permanently there with the client till the client deregisters and re-registers. This is what we do when we want to flush the transactionId. Once on the PayID notification endpoint, we receive a webhook callback. We prepare a CreditNotification request and we send it out to Kafka. Kafka reads this credit notification and sends it to the com-v3-finance topic. Which then reaches bank postings postings from the credit notification bills bank postings request object which is sort of similar to how it happens during the CAMT file-to-bank postings request object. Then the flow remains exactly the same: we fetch it from one of the reference objects, match it to a given account ID, and then we send it. In this case, account ID is set by the Lambda which receives the webhook call. It knows to which account ID the PayID belongs. It has its mapping in the DynamoDB table, and referring to that, it adds the respective account ID onto the credit notification before sending it out to bank postings.
> 9. We use Azupay as the integrator.
> 10. PayIDs shared per client. We have several account IDs associated with the client, like a CFD stockbroker. For each of those account IDs, we'll have an individual PayID. This PayID is for life till the client deregisters.
> 11. Yes, we post the ledger asynchronously, but it is nearly real-time. We get it within seconds.
> 12. The wrong amount scenario doesn't come because the webhook callback comes from Azupay. Name validation is done. If there is no name matching, we send it to the manual postings, which the internal admin team takes care of later on. For any other scenario, we still drop it to the manual queue. It is at the discretion of the payments operations team and internal admin team to determine what to do with the money.
> 13. No regulatory constraints as such, at least that I am not aware of.
> 14. We get nearly 2,000 to 3,000 transactions per day, as its lambda per minute scale is also a little less, and we have a lot of idle time. Lambda handles it fine.
> 15. Knowing AWS was hardest, as I was not a cloud-native developer.

---

## Turn 14 — Claude (structural observations + Area 5, withdrawals)

Now I have the shape of both cloud rebuilds. Two important structural facts have emerged that I want to record explicitly: **PayID reuses the bank postings machinery** via a CreditNotification on Kafka (`com-v3-finance`), so inbound reference-matching is a shared pattern across SWIFT/CAMT and NPP; and **Japan is redirect-only with no server-to-server callback**, with file reconciliation as the real safety net.

**Corrections and carry-forwards**

1. In the Japan flow you said the first lambda gives "the CardPayments configuration" — I'm reading that as the *bank deposits* configuration (list of available Japanese banks + transaction ID + token). Confirm?
2. Earlier you said bank deposits are **instant**. But the credit depends on the browser redirect, and anything without a redirect waits for the Billing Japan file. So "instant" = instant *when the redirect lands*, otherwise next file cycle. Fair?
3. **Japan rebuild, still open**: Java version, Spring Boot version, DynamoDB table design, CI/CD, testing approach, and the **cutover** — how did you move Japan from the old Spring app to the lambdas without dropping live deposits?
4. **PayID name validation** — who supplies the payer name, Azupay in the webhook? And you match it against the IG account holder name?
5. **PayID auth is worth being precise about**: endpoint 1 (generate PayID) is CST-validated; endpoint 2 (notifications) authenticates on a long-lived per-client transaction token that Azupay echoes in the header, rotatable only by deregister/re-register. Right? And is that token stored in the same DynamoDB table as the PayID→accountId mapping?
6. **ACH Payments** is a 17th application not in your original list. Are there others you forgot? Worth a second pass over the estate.
7. **Kafka** — is it used elsewhere in payments, or only for the PayID → bank postings credit notification path? And where does AMQ sit versus Kafka?
8. **Australia withdrawals** — PayID is deposit-only, so how does an Australian client get money out? Bank withdrawal app over which rail?

**Area 5 — Withdrawals**

Completely unexplored, and it's usually where the interesting controls live.

9. **Which apps handle withdrawal, and which rails?** You listed bank withdrawal and PayPal withdrawal. Is there **card withdrawal** (refund-to-source), or do all card depositors get paid out to bank?
10. **The flow.** Client clicks withdraw → what screens, what validations, what happens in the backend, when does the ledger get debited, when does money actually leave? Same treatment as the deposit flows.
11. **Where does the withdrawable amount come from?** Trading account balance isn't withdrawable cash — margin, unrealised P&L, and pending settlements all reduce it. Does bank withdrawal call out to a balance/margin service, or does it get a single "available to withdraw" figure from someone?
12. **Approval.** Are withdrawals auto-approved, or is there a manual queue? If there's a threshold, what's the rule? Who approves — payments ops via IGIP?
13. **Back-to-source.** Is there a rule that funds must return to the original funding instrument? That's standard AML practice for brokers, and if you have it, where is it enforced?
14. **Bank account trust.** Withdrawal targets come from **bank maintenance**. How is a newly added bank account verified before it can receive money — Plaid (US only), micro-deposit, statement upload, manual admin check? And is there a cooling-off period after adding one?
15. **Bank maintenance's "credit operation"** — you mentioned it now does a credit operation on the client's bank account. What is that, a micro-deposit verification?
16. **Ledger direction.** For deposits you fire-and-forget to the ledger service. For withdrawals the order matters enormously: do you debit the ledger *before* sending the payment instruction, or after confirmation? What happens if the debit succeeds and the payout fails?
17. **Payout execution.** Does bank withdrawal talk to a PSP, to IG's banks directly, or does it produce an outbound file (batch payment run) that treasury releases?
18. **Cancellation.** Can a client cancel a withdrawal in flight? Until what point?
19. **Fraud and sanctions on the way out** — any screening step before money leaves, and is that yours or another team's?
20. **Your involvement** — you said you "worked on" bank withdrawal. What specifically? And is PayPal withdrawal genuinely a black box to you, or do you know its shape?

---

## Turn 15 — Me (Area 5 answers)

> 1. Yes, that is bank deposits configuration.
> 2. Yes, if the radar comes, then it is instant. Otherwise, we'll have to wait for the reconciliation or admin team to post it manually.
> 3. Let's skip this part. Let's not go that deep.
> 4. Yes, Azupay supplies in the workbook. And we match it against the IG's KYC done name.
> 5. Yes, everything is right
> 6. Probably this much. I have covered most of them. There is one more called payment orchestrator, which does the GDPR cleanup. Whenever the client has not logged in for a certain time, there is a central orchestrator that figures out for which client we need to do a GDPR cleanup. What this application does is it will garble up the name, number, everything, and that gets taken care of by the payments orchestrator.
> 7. We majorly use AMQ everywhere. Kafka is a new initiative that we are taking up, so it is a variation of PayID.
> 8. Bank withdrawal is from where they'll get the money back.
> 9. CardPayments itself handles the card withdrawal. Bank withdrawal is a separate application that helps with the bank withdrawal. And also, there is PayPal withdrawal. If all the fund sources, like card and bank, are verified, then the client can withdraw his bank money into card and card money into bank, and vice versa, or in any manner he wants. (These are my assumptions about cross withdrawal. Correct me if there is any other standard that is followed in the domain)
> 10. For almost every region, there are only two possible ways of withdrawal: card and bank, and for Japan, it is only bank. The guy, go ahead and request the money. The first thing that is checked is whether the card and bank are verified or not. If the card and bank are verified, the guy can enter the amount he wants to withdraw. Depending on whether card or banked, the call goes to CardPayments or bank withdrawal. Card is instant if all the verifications are fine. PS: the call is made to the PSP, and the money goes out to the given client. While in the case of bank, the transactions happen in batches at a given point in time, probably at the end of the day. The payments ops guys do a payment run for a given region, let's say Australia. We verify all the transactions, whether that is sendable or not. There will be two internal admin guys who will be doing this verification, so there are check 1 and check 2. If both check 1 and check 2 have passed, then we mark it as ready for authorization. Once authorization is done, a bank file is generated. A bank file is added to a common network drive. That drive, manage file transfer team, or go anywhere team sends it out to the SFTP server of the respective bank. This bank is IG's bank from where the money goes out to the respective client's bank account, the details of which is given in the bank file. In both cases, we send out the email for both card and bank.
> 11. There is a central order server which handles all the balances. The available-to-withdraw balance is fetched from there, and only that balance is allowed to be withdrawn.
> 12. Card is almost always auto-approved. If there is any issue, then it is added to the manual queue, while bank is always manual. Yes, it is done by the payments ops team via IGIP.
> 13. If the card and bank are not verified, this is enforced. We have a in the For every card, we know how much money has been credited from that card, and also, for the bank, how much money has been credited from the bank. Similarly, for PayPal. If the withdrawal options are not verified, only the money can be given back to the same source. This is my understanding. If there is anything else that is running in the domain, please let me know. I'll get it clarified.
> 14. For every other region, the person has to manually send the verification documents requested by the payments ops team. With that, the bank will be marked as verified. In a recent development, we are thinking of verifying via PayID, as we know that the money is coming from that verified client. When the request goes to bank postings, we make a call to bank maintenance to add the bank account details as verified in the bank maintenance schema.
> 15. This could be misquoted from what I have said. I guess there is no such credit operation that is done by bank maintenance. Bank maintenance only maintains the bank account details.
> 16. This is also fire and forget. We immediately deduct the ledger, and then money is sent to the client. If there is any discrepancy, the money is added back if the client has not received the money by the operations team.
> 17. There is no PSP involved in the payout execution. We upload the file to the SFTP servers of respective banks like HSBC, Standard Chartered, Lloyds, etc.
> 18. For bank, yes, they can call in to the ops team, and the ops team will cancel that using the internal tools. This should be done before the cutoff timing, generally 4:30 pm of that day, so that, before that time, if the client calls in, the transactions can be marked cancelled.
> 19. I'm not aware of such things. We generally do a certain set of validations, but I don't think there are any fraud sanctions on that. If there is anything, the payments ops team manually blocks the client and flags him for non-withdrawal. That flag is checked alone in the withdrawal flow. There is no automated way of checking for fraud or sanctions.
> 20. For a newer added product for Australia, we had to create a new format of bank file. I created that and added the respective product. The product is IGCRY, which stands for IG Crypto. For this, we were supporting the withdrawal using Westpac. The Westpac account ID was different from the usual CFD or stock broking account ID of the IG side. While generating the file, we had to create a new file with the new account ID, hence I am aware of the bank withdrawal flow completely.

---

## Turn 16 — Claude (AML grounding, refund vs OCT, Area 6)

Two of your assumptions are worth grounding, since you flagged them.

**On cross-source withdrawal** — your understanding is a common industry pattern, not a universal rule. The hard AML principle is **same-name**, not same-instrument: money must go back to an instrument belonging to the account holder, and third-party payouts are prohibited. Restricting payouts to the *original* funding instrument is the stricter interpretation firms apply when an instrument is unverified. Once instruments are verified and name-matched, allowing cross-source is normal. So what you described is coherent — I'll record it as your team's rule and mark it as your understanding rather than confirmed policy.

**On card payouts, one thing worth checking**, because it's a real distinction and a good detail to have right: paying out to a card happens by one of two mechanisms. A **refund** reverses the original deposit transaction, is capped at the original amount, and expires after a window (typically 180 days). An **Original Credit Transaction (OCT)** is an independent push-to-card credit with no link to a prior deposit. Which does CardPayments use? If refunds, there must be logic tracking remaining refundable amount per deposit and handling expiry — which would explain your "how much has been credited from that card" tracking.

**Area 6 — FX, internal transfers, and the shared services**

*Currency conversion / funds transfer*
1. You mentioned a **separate funds application for currency conversion** and **funds transfer service** for movement between CFD / stockbroking accounts. Are these the same app or two? Real names?
2. **Fixed USD→GBP rates** — where do those fixed rates live, who sets them, how often are they revised? And is there a spread/margin applied, or is it rate-only?
3. Which currency pairs are supported? What happens for an unsupported pair?
4. Is the conversion a ledger-only operation (two postings, no money moving externally), or does treasury actually execute an FX trade behind it?
5. Does deposit-time conversion exist — client's card is USD, trading account is GBP — or must currency always match, with conversion only as a separate client-initiated action?

*PSP integration service & PSP maintenance*
6. How many PSPs are integrated, and which? You've named Worldpay and "Noire" (Nuvei?). Others?
7. Is PSP integration a **single service with per-PSP adapters**, or one deployment per PSP? How much work is onboarding a new PSP?
8. Does PSP maintenance hold anything beyond credentials and country→PSP mapping — retry rules, fallback PSP if primary is down, per-PSP limits, enabled card schemes?
9. **PSP failover** — if Worldpay is down for UK cards, does traffic shift automatically, or is it a config change and deploy?
10. Where are PSP **credentials** actually stored — vault, KMS, encrypted DB column?

*Card validation service*
11. Beyond BIN lookup, what does it return — scheme, type (credit/debit/prepaid), issuing country, commercial flag? Is the BIN data licensed from a provider, and is it cached?

*Wallet payments (Apple Pay)*
12. Deposit only? Does it route through CardPayments and the PSP integration service, or is it fully independent? Does Apple Pay bypass 3DS via its own device authentication?

*Cash in transit*
13. Who decides to front the money — automated rule or ops judgement? Is there an exposure cap? What happens if the funds never arrive — is the ledger reversed, and does the client go negative?

*Payments orchestrator / GDPR*
14. What triggers the cleanup, which fields get garbled, and across which applications — does the orchestrator write into each app's DB, or call an endpoint each app exposes? And how do you keep garbling from breaking reconciliation or audit obligations, given financial records must be retained for years?

---

## Turn 17 — Me (Area 6 answers + channels)

> * We have channels in CardPayments like ECOM, CFT and MOTO however, I'm not sure about this OCT. I definitely don't think there is a refund mechanism that we are using, which reverses, because that is capped at the money in. The guy can easily withdraw the all money which he has deposited. Let's say he has deposited 1,000 from a card and 2,000 from the bank, then he can withdraw 3,000 altogether. Or let's say there are two cards, and he has deposited 1,000. He can withdraw all 2,000 into one card, provided all the cards and the bank are verified.
>
> 1. This is the same application. The application name is Funds Transfer Service.
> 2. There is a common application. I'm not aware of that. That is not in our domain. There, we store these currency conversions. We just pull that, use it, and do the currency conversion. They are revised every day. I'm not aware whether the spread or margin is applied. We just use the rate only.
> 3. Multiple currency conversions are supported: yen, pounds, US dollars, AED dirhams, singaporean dollars (SGD)
> 4. Everything is eventually converted to GBP, as the core currency of IG is GBP. It is maintained across countries, so everything is talked about in terms of GBP, whether it is USD or whatever.
> 5. There is no rule that currencies must match. While money is moving out and moving in, everything is mapped to GBP. Before that, or during the trade, the asset can be USD or JPY or anything of that sort. Conversion is just for bookkeeping of IG.
> 6. Majorly have Worldpay, WestPAC, Noire, and under REALEX
> 7. It's a single service. I've never onboarded a service, but it should be pretty straightforward. There is an internal tool called Hydra. Which is entirely managed by a different team. We don't touch on that code. In this Hydra application We'll have to add the details and credentials which updates that in PSP maintenance service and with this created PSP, we'll have to attach it to a given IG company. Let's say IGUS, IGGB, or IGAU. Whenever a deposit for that company comes, we'll ask IGAU to use Worldpay instead of the earlier configured WestPAC. It's a configuration change. This can even happen during any outage with the PSP, which rarely occurs, but there is an option for us to switch between the PSPs.
> 8. I guess only this much. I'm not aware of any other things that can go into this. Probe me if you feel anything is there. I'll let you know.
> 9. The traffic does not shift automatically. There is an incident raised to us. We check why the PSP is failing. If there is a small issue, we fix it. If it's a bigger issue, we migrate the traffic to a new PSP manually. It's just a config change.
> 10. It is stored in an unencrypted DB column. For the newer ones which are on cloud, we are using parameter store in AWS, and for the few ones which are on Nomad, we are using Hashicorp Vault.
> 11. Yes, it returns scheme type, whether it is credit or debit, issuing country. I'm not aware of the commercial flag. The bin data is given from Worldpay. It is cached and replenished every 2 to 3 days based on the newer models that are given to us, so we don't check what the delta is. We paste the file, commit the changes, and deploy it. The changes are very, very minimal. During that time, if any transactions are failing, we get the incident, and we ask the client to retry after updating the CSV file for the bin numbers. You also have an override wherein the CSV given by Worldpay differs from what the actual client is. Sometimes a bin number is marked as a credit card, but it's a debit card. In those cases, we override whatever is given from the CSV in a YAML file which is there in the card validation application. And this is a Spring Cloud config, so it can be replenished very easily.
> 12. Wallet payments are entirely out of my domain. I've not worked on it and haven't even checked the code much, but it is both deposit and withdrawal. It works with the underlying PSP integration service itself. It doesn't hit CardPayments, but only the PSP integration service. Not aware if it bypasses 3DS verification, but I guess yes, it does. We use terms like D-PAN (that is, device PAN) and stuff like that, so I'm guessing it goes that way.
> 13. It is ops judgment. Cash in transit is very sensitive, so it is always ops judgment. Only for the Plaid-integrated ACH deposit, we upfront give $2,500, irrespective of how much money is given in. Let's say there is a $10,000 deposit that is coming in from a client. We upfront deposit $2,500 for him and $7,500 later on when the deposit actually comes in. If the money is less than $2,500, let's say $2,000, we deposit all $2,000.
> 14. There is a central orchestrator app which gets triggered by the admin team to purge the data once that request has reached the payments orchestrator, which does the job. Every PI data that is there in the database record gets garbled out. Reconciliation doesn't come into play, as you know the client has not been logging in for the last one year. Audit data is purged before the GDPR sweep is done.

---

## Turn 18 — Claude (CFT resolved + Areas 7 & 8)

**Closing the card-payout loop** — your channel list answers it. **CFT** is Cardholder Funds Transfer: the push-to-card payout mechanism (Visa Direct / Mastercard MoneySend family), which is the OCT family under a different name. So CardPayments does push-to-card, not refund-reversal, which is exactly why a client can withdraw £3,000 to one card having deposited £1,000 on it. That resolves the discrepancy cleanly. And your three channels map neatly:

- **ECOM** — client-initiated online deposit, 3DS2 enforced
- **MOTO** — Mail Order / Telephone Order, the internal admin depositing on a client's behalf, which is what your "frictionless flow" actually is
- **CFT** — outbound push-to-card withdrawal

Two things I'll flag in the final doc as risk observations rather than facts: **PSP credentials in an unencrypted DB column** on the legacy estate, and **BIN data refreshed by committing a CSV and deploying**, with a YAML override in Spring Cloud Config for misclassified BINs. Both are honest engineering realities and both are the kind of thing that reads well in an interview *if* framed as "here's what I'd improve and why."

**Area 7 — Auth, security, and the request path**

1. **Token types.** CST (external clients), XST (internal admins, role-bearing), JWT (newer). Is JWT replacing CST, XST, or both? Do all three work concurrently today, and does each application validate them independently, or does PG validate once and downstream apps trust PG's stamped token?
2. **Who issues tokens?** A central auth/session service? Is it your team's or another's?
3. **Service-to-service auth** — CardPayments → PSP integration service, lambda → bank postings. Is that authenticated, or is it open on the internal network?
4. **PG's XST stamping.** For the webhook path PG replaces the PSP header with its own XST token. Does that token carry a role, and could a compromised inbound webhook therefore reach privileged endpoints?
5. **Role model** — what roles exist for internal admins (payments ops, check-1 approver, check-2 approver, manual deposit)? Enforced in the token, in PG, or in each app?
6. **Audit trail** — when an admin does a manual deposit or approves a payment run, where is that recorded and for how long?
7. **PCI-DSS** — you said the frontend handles card numbers so it's in scope. Which level, what's the assessment cadence, and is FE-Payins the only in-scope component?

**Area 8 — Infrastructure and deployment topology**

8. **Three platforms, it seems**: the legacy UK data-centre pair, **Nomad** (Vault-backed), and **AWS** (lambdas, DynamoDB, API Gateway, Parameter Store). Map each application to its platform — which are still DC, which are on Nomad, which are cloud-native?
9. **Nomad** — is that HashiCorp Nomad running on-prem or in cloud? Is it the intermediate step between DC and AWS?
10. **The routers.** "External router" and "internal router" — what are they actually? Nginx, an in-house Java app, a service mesh, Nomad's own routing?
11. **AWS region** for the cloud apps — eu-west-1/2? Same UK-only data residency constraint, or does IGAU/IGUS data sit elsewhere?
12. **Datastores** — legacy apps on Oracle, SQL Server, Postgres? And DynamoDB for the new ones.
13. **CI/CD** — Jenkins, GitLab, Concourse? Release cadence, and is deployment self-service or release-managed?
14. **Observability** — Splunk, Datadog, Grafana, ELK? How do you actually debug a stuck deposit at 2am?
15. **Languages and frameworks across the estate** — Java version(s), Spring Boot, Quarkus for the lambdas. Anything else, and any frontend stack detail for FE-Payins (React? Angular?).
16. **On-call** — does your team run its own rota, and what are the typical incidents?

---

## Turn 19 — Me (Areas 7 & 8 answers)

> * its not unencrypted, its encrypted column.
> * Tell me how you'd improve BIN data refresh later in the final document
>
> 1. JWT will be only replacing 60. CST will remain. Yes, all three work concurrently today. There is a common client security application for CST and single sign-on service for JWT and XST
> 2. For clients, the token is issued by the client service, and for internal users by the SSO service. It is maintained by a different team.
> 3. Yes, internal service calls are also authenticated using an application token. Which is also handled in the SSO service. Lambda to bank posting goes through Kafka, so there is no authentication that is happening there, as far as I understand. If there is any authentication mechanism on Kafka, I'm not aware of that.
> 4. It is an application token. Yes, it has roles. Yes, it may so happen.
> 5. Roles are like: ROLE_RG-IM-PAYMENTS-PAYMENTRUN, ROLE_RG-HYDRA-BANKPAYMENTS-CREATEBANKFILE, ROLE_RG-HYDRA-BANKPAYMENTS-CREDITSIGNOFF etc. Each individual role will have its own -DEV (ex: ROLE_RG-HYDRA-BANKPAYMENTS-CREDITSIGNOFF-DEV) version, which is assigned to only developers and is only working in UAT and test environments. The roles without -DEV work in prod environment. The role will be part of the token. The role check will generally be done at the gateway level. But for some very sensitive endpoints, it is done at a backend application level also.
> 6. Each record will have an "initiated by" or "DB created by user" column. If it is done manually, then the user's shorthand name is assigned to that DB row. It is persistent, so it is maintained forever.
> 7. No, not just FE-Payins, but the entire domain happens to be in the PCI DSS scope. For that reason, payments gateway, CardPayments, card validation service, and PSP integration service all happen to be in the CDE environment.
> 8. Yes, the UK data center is legacy on-prem, which hosts most of the applications. Recent migrations have started. A few have been moved to Nomad, and a few are already built in AWS.
> 9. It's Hashicott Nomad running on-prem. This is an intermediate step between DC and AWS. However, a few applications which can be directly brought onto AWS have already been done.
> 10. I'm not entirely aware. I believe it is the EngineX app, which is owned by a different team, so I'm not entirely sure. I'll get these details later on if possible.
> 11. We use multiple. A few are in Australia (Sydney). A few are in the Ireland region. A few are in the Singapore region. And one is in Tokyo for the bank deposits.
> 12. Yes, we use Oracle for the legacy applications. There is an on-prem database that is present.
> 13. We use GitLab for CI/CD. Using blue-green architecture
> 14. We use Plunk and Grafana.
> 15. We use majorly Java 8, 11, 17, and 21. Spring Boot is generally 1 in legacy, 2 and 3 in the modern ones. We have not used Spring Boot 4. Frontend stack is React. We have legacy FMQ that is almost decommissioned. We majorly have AMQ, and then we also have Kafka. On AWS, we are using:
>    * ECS Fargate
>    * EC2 instances
>    * Lambda
>    * SQS
>    * SNS
>    * API Gateway
>    * DynamoDB
> 16. Yes, we have our own rota. The typical issues are:
>    * The card payment is not reflecting.
>    * The bank withdrawal hasn't gone through.
>  Usually, the issues are related to double-entry errors. Sometimes we get to know that the critical applications, like the PSP, are down, but that's pretty much it.

---

## Turn 20 — Claude (Area 9 + contributions)

Corrected: encrypted column. And I'll include BIN refresh improvements in the final doc.

Also noting: **not UK-only** — Sydney, Ireland, Singapore, Tokyo AWS regions, which suggests data residency is deliberately regional for the cloud estate. That contradicts my earlier "single UK region" note, so I'll record the DC as UK-only and cloud as multi-region.

**Area 9 — Final gaps before I draft**

1. **"JWT will be only replacing 60"** — transcription slip. Replacing what? I'd guess XST.
2. **Double-entry errors** as a top on-call issue — what does that mean concretely? Same deposit posted twice to the ledger, or a mismatch between your transaction record and the ledger's?
3. **Environments** — DEV/UAT/TEST/PROD? Do you have PSP sandboxes for all providers, or do some require testing against live?
4. **Testing** — unit/integration/contract tests, and how do you test a webhook flow that depends on an external PSP?
5. **Volumes** — you gave me 2–3k/day for PayID. Rough daily transaction volume for cards and for bank postings? Peak periods (market volatility)?
6. **IG entities** — you've named IGGB, IGAU, IGUS, IGCRY. Full list of entities/companies your systems serve, and which countries/brands (Nadex? tastytrade? Spectrum?).
7. **Team shape** — how many engineers, how is work split across these 18 apps, your role/title and seniority, how long in the domain.

**Now the important part — your contributions**

For the interview and CV angle, the architecture alone won't carry it. I need the achievement layer, and I'd rather ask than invent.

8. **Australian fast payments** — you built it outright. What was the delivery timeline, how large was the team (just you?), what was the measurable outcome? Adoption rate, share of Australian deposits shifted off cards, cost saved on card interchange, reduction in failed deposits?
9. **Bank deposits rebuild (Japan)** — 3–4 months. Was that you solo or a team, and what was your specific slice? What improved measurably — incident volume, deployment frequency, latency, cost, manual posting rate?
10. **IGCRY / Westpac bank file** — new file format for a new product. What was the business context, what was tricky about it, and did it ship on time?
11. **Open banking / Plaid** — you were a major contributor. What did you build, and what was the impact? You mentioned it removed manual admin verification that "used to delay a lot" — do you have a before/after number? That's a strong metric if you can approximate it.
12. **Bank maintenance** — major contributor. What did you build there?
13. **CardPayments and Payments Gateway** — you contributed. Any specific features, migrations, or incidents you led that are worth naming?
14. **Anything not yet mentioned** — performance work, cost reduction, a nasty production incident you diagnosed, mentoring, cross-team leadership, a design you pushed through.
15. **Your own view**: of everything here, which two or three pieces of work are you proudest of, and why?

---

## Turn 21 — Me (Area 9 + contribution answers)

> 1. Yes, I meant XST
> 2. I'll get back to you on double-entry ledgers. Let's just keep it aside for now. On a high level, it is like there is a middle ledger in between the account ledger and bank ledger, so there is a -ve account-ledger. And then there is a +ve payment-request-clearing-ledger. This goes as one group, first entry transaction. Then we do another ledger, which is like -ve payment-request-clearing. And +ve bank this is the second ledger.
> 3. There is no specific dev environment. The dev environment refers to the local machine. We have TEST, UAT, DEMO, and LIVE. DEMO and LIVE are sister data centers, wherein a DEMO account can be created by a user, him to try out IG's products meanwhile, the other data center acts as live, which handles the actual products with actual money. For some time, data center 1 acts as live DC2 acts as DEMO, and then we flip, and data center 2 becomes live, and vice versa. While the prod is also called live, which handles the actual genuine requests from the client in an actual account
> 4. We do unit integration and acceptance testing. Let's ignore the webhook part as of now. We'll deal with it later.
> 5. Not exactly sure, but card goes almost 10, 15, 20, 30, and 50,000, depending on the traffic.
> 6. There are several:
>    * IG JP for Japan
>    * IG US for USA
>    * IG AU for Australia
>    * IG GB for UK
>    * IG FR for France
>    * IG DE for Germany
>  IGCRY actually is a product, it's not a country. Similar to IGCRY, we have IGCFD, IGSTK, IGFNO.
> 7. We nearly have 7 to 8 engineers. All of these applications were developed a pretty long time back, so we only developed and maintain the newer applications. My role is developer. I have built a couple of applications by myself. I've been in this domain for the past 3.5 years.
> 8. It was a 2-3 member team. We had 2 core members, one frontend developer. We had ad hoc support from one more member. I was the one who was leading this project entirely. Had to read through Zupay's documentation and deliver the product. The delivery timeline was around 6-7 months. As Australian fast payments was the primary mode for many of the users, initial adoption was very high. Nearly 20% of the active clients got onboarded within the first week. Later on, we do not have much data around this. It was not shared with the deputy. The details, like cost saved and all, are not known to me.
> 9. This was also a two-member team with one more person supporting ad hoc whenever needed. This also I led majorly, so I had to figure out the entire bank deposit application:
>    * what all was happening
>    * what all were the integration points
>    * what all challenges we could see
>  I had developed this entirely from scratch. Architecture was built by a senior tech specialist who handed us the architecture diagram of splitting Lambda and stuff like that, but major development was done by me, especially the GraalVM part. Lambda is sensitive to Java applications. It doesn't boot up quickly. It takes around 7 to 8 seconds to boot up. When it is behind VPC (Virtual Private Cloud) We pivoted to GraalVM. I tested a few POCs before we committed to Spring Boot with GraalVM, and also we checked what the other possibilities are. I tried with Micronaut and then eventually ended up with Quarkus for the other two lambdas. The latency was improved very much, as the AWS data center was now very near to Japanese folks. We had entirely removed the context of the UK data center by copying the data onto Japanese Dynamo DB, so we had a pretty good latency improvement.
> 10. Whenever a usual product gets added, the same bank supports it, but in this case, as it was a crypto product, it was regulatorily difficult for the existing bank to support. We had to onboard a new bank for us to have this money sent out. It was not that tricky. We could ship it in just one sprint, as it was just an addition of a few fields in the file.
> 11. Open banking was my first project in IG. I was a secondary contributor. I was a developer, but the planning was done by another senior person. I integrated several APIs with Plaid. I analyzed the documentation, but for a major portion of it, the planning part, as I have done in bank postings and Australian Fast Payments, I didn't do that. It was mainly done by my senior member. Immediately develop the APIs in this case. By planning, I mean which all applications are involved, how ACH payment should happen, and all those things were taken care of by the senior member. It was a four-member team with this one. I don't have a clear before-and-after number, but bank verification by the client used to take 1-2 business days. However, this was near-instant.
> 12. The earlier application was called Payments. This was not very user-friendly. It had too many use cases being handled, so we pulled out the bank-storing part for IGUS clients alone into the new bank maintenance schema. The older guys who had already had their bank accounts still stayed in bank postings. Once they started going via Plaid, Plaid verification was mandatory. Once the verification was done via Plaid, automatically, one by one, the clients were moved to the new bank maintenance schema. This was a two-step flow from payments:
>    1. We had to delete the bank account.
>    2. We had to verify using Open Banking.
>  Once verified, we had to add it to the new verification schema. We used to delete it only after the verification is done, so that we will not remove his bank account in between and he doesn't have a bank account in both the schemas. I majorly contributed on the open banking side. Bank maintenance was majorly done by another colleague of mine.
> 13. I don't exactly remember. I'll recollect it later on.
> 14. I'll recollect the production incidents later on.
> 15. I'll share this later on.

---

## Turn 22 — Claude (delivered `ig-payments-domain-model.md`)

That's v1 — 12 sections covering all 18 applications, 11 flows, the cross-cutting architecture, and your contribution ledger. Everything is confidence-marked so you can see at a glance what's solid versus what needs checking.

Three things I'd draw your attention to:

**§5.5 names four recurring patterns.** You described flows individually, but they share architecture: reference-matching for decoupled credits, optimistic real-time signal with a batch safety net, manual queue as universal fallback, front controller with path routing. Being able to state these out loud is worth more in an interview than reciting any single flow, because it shows you see the estate rather than just your corner of it.

**§10.1 has the BIN refresh improvements** you asked for — eight of them, ordered by value. The most useful framing is that reference data is currently managed as source code, so a data change needs a release and a data error becomes a client-facing decline. The live-lookup fallback is the one that eliminates the whole failure class.

**§11 separates what you designed from what you implemented.** PayID and Japan you led and designed; Open Banking you implemented against someone else's design. I've kept that honest rather than flattening it, because the contrast is your growth story — first project as an integrator, latest as the person reading Azupay's docs and deciding the architecture.

Twelve open items in §12. Three would strengthen the document most:

1. **The double-entry ledger detail** — it's your top recurring incident class and currently the thinnest section.
2. **Your proudest work and the production incidents** — the interview layer is thin without them.
3. **The per-application platform mapping** (DC vs Nomad vs AWS) — a newcomer can't navigate the estate without it.

Want me to keep going on any of those, or would an architecture diagram of the full estate be more useful next?

---

## Turn 23 — Me

> Document the full conversation if needed concise or correct my answer whichever is cheap for you

---

## Turn 24 — Claude (delivered `ig-payments-elicitation-record.md`)

Both in one document. Three parts:

**Part A — corrections.** Four concepts clarified (stateless, refund vs push-to-card, the ECOM/MOTO/CFT channels, same-name vs same-instrument AML), seven answers you corrected yourself, seven inferences of mine that turned out wrong, and twenty transcription fixes.

The two worth remembering: **CFT is the push-to-card family, not a refund** — that's what makes withdrawing £3,000 against a £1,000 card deposit possible. And **MOTO is what you were calling "frictionless flow."** True 3DS2 frictionless is an issuer decision; yours is IG deliberately not invoking 3DS2 for an authenticated admin. Same outcome, different mechanism — flagged to confirm.

**Part B — condensed Q&A** across all ten areas, so the raw answers survive independently of the polished model.

**Part C — the method**, in case you do this for another domain. The point that generalised best: asking what *doesn't* happen produced more architecture than asking what does. Your happy paths were well recalled; the safety nets — webhook sweepers, file reconciliation, AutoRec, the manual queue — weren't, and they turned out to be the real design.

One thing I'd still push on when you have time: **whether internal deposits are submitted as MOTO or as ECOM with an exemption flag.** It's a small detail, but it's the kind of thing an interviewer who knows cards will ask, and getting it exactly right signals you understand the scheme rules rather than just your codebase.

---

## Turn 25 — Me

> Create "conversation.md" and write the answers/inputs I gave followed by the questions/clarifications you asked/gave. Let it be as near to our conversation as possible

---

## Turn 26 — Claude

*[This document.]*

---

## Deliverables produced from this conversation

| File | Contents |
|---|---|
| `ig-payments-domain-model.md` | The polished domain model — 12 sections, 18 applications, 11 flows, cross-cutting architecture, risks and improvements, contribution ledger, open questions |
| `ig-payments-elicitation-record.md` | Corrections and clarifications, condensed Q&A record, elicitation method notes |
| `conversation.md` | This near-verbatim transcript |
