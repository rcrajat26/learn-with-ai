# Repository Discovery: bank-postings

**Repository:** `_Codes/payments/bank-postings` (`ig.client.payments.wt.bank.postings:bank-postings`)
**Date:** 2026-09-05
**Analysis Depth:** ~3h deep read (Layers 1–15)
**Scale:** 699 Java files, ~45.9k LOC main+test, 11 Maven modules, 127 Flyway migrations
**HEAD:** `b700f9d5` — *Merge branch 'PYMEEM-977'* (SICIP approve/reject logging)

---

## 1. System Mental Model

Bank Postings is the **inbound money ingestion and auto-approval engine** for IG's payment
platform. It has two independent front doors onto the same domain core: (a) a **file pipeline** that
polls S3 for bank statement files (SWIFT MT910 `.fin` and ISO 20022 CAMT.052), parses each credit
into a `BankPostingRequest`, and (b) an **event pipeline** that consumes Kafka payment/SIP-deposit
events for real-time rails (PayNow, PayID, eGIRO, EDDA, LeanTech, TrueLayer, BVNK stablecoin, SICIP
instant payments). Every request runs through a **Specification-pattern validation chain** (AML risk
score, account status, payer-name match, deposit limits, banned/high-risk country, tax wrapper, 30-day
rule, third-party transfer, currency match, value/receipt date). A pass **posts a credit to the ledger
over AMQ and marks the deposit APPROVED**; a fail either **REJECTS** it or drops it into a **MANUAL
queue** for a human credit-risk agent to approve/reject through the IGIP screen. It is a
**WAR on Tomcat 7, Java 8, Spring Boot 1.5.9 / Spring Cloud Dalston**, with **Zookeeper leader
election** ensuring only one node in the blue/green pair actually consumes work.

---

## 2. Repository / Module Architecture

11 modules; only 3 hold Java main code.

| Module | Java files (main) | Role |
|--------|------|------|
| `domain` | 268 | Domain model, services, **ports**, validation specifications. Framework-light. |
| `integration` | 375 | **Adapters**, JPA entities/repos, Flyway migrations, Kafka/JMS/S3 config, controllers, JMX. |
| `service-api` | 28 | Shared DTOs + Swagger-annotated API interfaces (contract only, no logic). |
| `schemas` | 0 | Avro `.avsc` schema definitions. |
| `resource` | 0 | Per-environment `application-<ENV>.yml`, logback, Tomcat `context.xml`, bundled `ojdbc8.jar`. |
| `war` | 0 | WAR packaging + `tomcat7:run` entry point. |
| `docs` | 0 | Swagger doc generation. |
| `component-tests` | 22 (test) | Cucumber **black-box** acceptance tests against a deployed container. |
| `post-deployment-tests` | 6 (test) | Cucumber smoke tests against a live environment. |
| `coverage` | 0 | JaCoCo aggregate report. |
| `terraform` / `load-test` / `mocks` / `openspec` | — | Acceptance infra, Locust load tests, docker-compose local stack, spec-driven-dev artefacts. |

```
service-api (DTOs) ──────────┐
                             ▼
            domain ────► port/*  (30 interfaces, outbound)
               ▲                        ▲
               │ (services, specs)      │ implements
               │                        │
         integration ────────► adapter/* (30 classes)
               │                    └─► jpa / kafka / jms / feign / s3
               ▼
             war  (packaging only)
```

Dependency direction is **inward**: `integration` depends on `domain`; `domain` never imports
`integration`. `domain` is Spring-annotated (`@Service`, `@Component`) but has no JPA, no Kafka,
no HTTP — those live behind ports.

---

## 3. Maven / Dependency / BOM Behavior

| Aspect | Finding |
|--------|---------|
| Parent POM | `com.iggroup.wt.maven3:wt-maven-project:3.9.0` — IG-internal corporate parent (supplies plugin mgmt, deploy config, repo layout) |
| Spring Boot | **1.5.9.RELEASE** — EOL since 2019 |
| Spring Cloud | **Dalston.RELEASE** — EOL; supplies Feign under the *pre-rename* package `org.springframework.cloud.netflix.feign` |
| Java level | **8** (`maven.compiler` 3.8.1); Maven 3.9.9 |
| Version strategy | `${revision}` flattened, default `SNAPSHOT`; CI rewrites with `mvn versions:set -DnewVersion=$NEXT_VERSION` |
| Key BOMs | Spring Boot 1.5.9, Spring Cloud Dalston. **~55 pinned versions in root `<properties>`** override BOM defaults extensively |
| Notable pins | Jackson 2.8.5, Kafka clients **0.11.0.2**, Artemis 2.13.0-redhat, Spring Integration 4.3.13, spring-integration-aws 1.1.0, AWS SDK 1.11.83, Prowide SWIFT SRU2019-8.0.2, ojdbc8 18.3, Flyway 5.0.7, Caffeine 2.8.5, OpenTelemetry 1.15.0, Lombok 1.18.30, Hystrix (transitive via Dalston) |
| IG internal libs | `wt-common-log` 1.54.0, `wt-singlesignon` 1.81.1, `ig-feign-spring-boot-starter` 1.0.39, `ig-sso-spring-boot-starter` 1.0.6, `ig-web`/`ig-swagger` starters, `mantis-leader-election` 1.0.84, `metrics-goldensignal` 1.99.0, `ct-ledger`, `enterprise-message-bus-kafka` 1.1.27, data-pod clients (client/payments/finance) |
| Local jar | `resource/src/main/jars/ojdbc8.jar` — Oracle driver checked into the repo, assembled into the deployable |
| Plugins | tomcat7-maven-plugin 2.2, maven-war-plugin 3.2.0, failsafe 2.22.1, surefire 2.22.0, jacoco 0.8.10 |

### **BOM / AUTO-CONFIGURATION BEHAVIOR**
1. **Hystrix wraps every Feign call, implicitly.** Spring Cloud Dalston enables
   `feign.hystrix.enabled` and the code never wires a circuit breaker — but
   `resource/.../common/application.yml:135-136` sets `feign.hystrix.enabled: true` and `:184-196`
   configures `hystrix.command.default.execution.isolation.thread.timeoutInMilliseconds: 3000`, with a
   per-command override of **45000 ms** for `BankAccountVerificationApi#verifyBankAccount`.
   `TaxWrapperAdapter.java:38` catching `HystrixBadRequestException` is the only place in Java code that
   reveals Hystrix is in the call path. **Every external HTTP call therefore runs on a Hystrix thread
   pool with a 3s wall-clock budget** — implicit bulkheading nobody declared in code.
2. **`@EnableAsync` with no `TaskExecutor` bean.** `BankPostingsApplication.java:14` enables async;
   a repo-wide grep finds **zero** `TaskExecutor`/`AsyncConfigurer` definitions. Spring Boot 1.5
   therefore falls back to `SimpleAsyncTaskExecutor`, which **creates a new unbounded thread per
   invocation**. The only `@Async` method is `BankFilePostProcessor.backupAndDeleteFile` — see §12.
3. **Flyway auto-configuration is on** (`flyway.table: FLYWAY_METADATA`) *and* re-exposed manually
   through `FlywayMbean` for operator-triggered migrate/repair (documented in README).
4. `@EnableCaching`, `@EnableIntegration` and `@EnableAsync` are each declared **twice** (application
   class + a `@Configuration`) — harmless, but a sign of accreted config.

---

## 4. Java / Spring Technology Usage

- **Spring MVC**, not WebFlux. Entirely imperative/blocking. No `Mono`/`Flux`, no reactive types.
- **Spring Integration 4.3** is the file pipeline backbone: `@InboundChannelAdapter` + `@Poller`,
  `@Filter`, `@Transformer`, `@ServiceActivator`, `QueueChannel`/`DirectChannel`.
- **Spring Data JPA** (Hibernate, `Oracle10gDialect` against Oracle 19c) via `JpaRepository`;
  data source injected by **JNDI** (`ig/jdbc/datasource/bank_postings`) from Tomcat.
- **Spring Cloud Netflix Feign** (Dalston package) for 2 declarative clients; the remaining external
  calls go through IG-supplied generated clients (`wt-client-maintenance-client`,
  `wt-accountmaintenance`, `wt-taxwrapper-client-intf`, `funds-transfer-service`).
- **Spring JMS** (`@JmsListener`, `JmsTemplate`) over ActiveMQ Artemis; **Spring Kafka** with
  hand-built `KafkaMessageListenerContainer` beans (not `@KafkaListener`).
- **Spring Cache** with Caffeine (`CacheConfiguration.java`).
- **Java 8 features only**: streams, `Optional`, `java.time`, lambdas. Lombok carries the weight
  (`@Slf4j`, `@Builder`, `@RequiredArgsConstructor`, `@Getter/@Setter`, `@EqualsAndHashCode`).
  **No records, no sealed types, no `CompletableFuture`, no virtual threads.**
- **`java.util.Observable`** (deprecated since Java 9) is still the fan-out mechanism for three Kafka
  listeners — see §18.

---

## 5. Architecture Detected

**Pattern:** **Hexagonal / Ports & Adapters, consistently applied** — high confidence.

**Evidence:**
- `domain/.../port/` contains **30 outbound port interfaces**: `LedgerPostingPort`,
  `BankPostingRequestPort`, `ClientMaintenancePort`, `AmlRiskScorePort`, `CurrencyConversionPort`,
  `SipOutboundPublisherPort`, `TaxWrapperPort`, `EventPublisherPort`, …
- `integration/.../adapter/` contains **30 matching implementations** with near-1:1 naming
  (`LedgerPostingAdapter implements LedgerPostingPort`, `BankPostingRequestAdapter implements
  BankPostingRequestPort`, …).
- Dependency direction verified: `domain` has no import of `com.iggroup.wt.bank.postings.jpa`,
  `.kafka`, `.jms`, `.adapter`, or `.external`. JPA entities live only in `integration`, with
  `transformers/*` mapping entity ⇄ domain at the boundary.
- Two composite sub-patterns inside the hexagon:
  - **Specification pattern** for business rules (§7) — `Specification.isSatisfiedBy(...)`,
    `AndSpecification`, `CompositeSpecification`.
  - **Pipes-and-filters** for file ingestion via Spring Integration channels (§6).

**Trade-offs:**
- ✅ Domain logic and validation rules are testable without Spring context or a DB; 94 unit tests in
  `domain` prove it. Swapping MT910→CAMT or AMQ→Kafka touches only adapters.
- ✅ New payment rails (SICIP, BVNK, LeanTech) plug in as new ports+adapters without touching the
  approval core.
- ❌ **Leaky abstraction on the transaction boundary.** Because persistence is behind a port, no
  caller can open a transaction spanning two port calls — and the codebase duly has essentially no
  transaction management at all (§9). The hexagon's purity is bought at the cost of atomicity.
- ❌ Duplication drift: `port/BankAccountPort.java` **and** `port/bankaccount/BankAccountPort.java`
  both exist, with two corresponding adapters. Two `CurrencyConversion` port packages likewise.

---

## 6. Important Execution Flows

### Flow 1: MT910 / CAMT file → ledger credit (the primary flow)

```
S3 bucket PENDING/ or CAMTPENDING/
  → @InboundChannelAdapter S3StreamingMessageSource        [S3ObjectPoller.java:50,60]
      poller.fin.fixed-delay=20000ms | poller.camt.fixed-delay=10000ms
      filter: S3PersistentAcceptOnceFileListFilter + S3RegexPatternFileListFilter(.fin)
  → QueueChannel "s3Channel"
  → @Filter LeaderOnlyFilter.accept()                      [jms/LeaderOnlyFilter.java:34]
      drops + closes stream unless this node holds the Zookeeper leader latch
  → DirectChannel "leaderFilterChannel"
  → @Transformer BankCreditMessageManager.doProcess()      [jms/BankCreditMessageManager.java:29]
      routes on extension: *.fin → Mt910CreditMessage (Prowide SWIFT), else Camt052V02CreditMessage (JAXB)
      → BankPostingData { fileName, List<BankPostingRequest>, corrupted }
  → DirectChannel "processRequest"
  → @ServiceActivator BankPostingRequestsProcessor
        .processExtractedRequests()                        [filemanager/BankPostingRequestsProcessor.java:29]
      1. filterOutPoolTransfers        (bankTransactionDomainCode == BANK_TRANSACTION_CODE)
      2. filterOutUnknownRecipientBankAccount (null recipient a/c)
      3. filterOutPaymentsForIgnoredBank (bank ignore-list property)
      4. bankPostingRequestPort.insertBankPostingRequest(list)   → status RECEIVED + dedup (§9)
      5. bankFilePostProcessor.backupAndDeleteFile(data)         → @ASYNC, fire-and-forget
      6. forEach → TransactionProcessingService.processTransaction
  → TransactionProcessingService.processTransaction()      [service/TransactionProcessingService.java:38]
      persistTransactionDetails → TransactionDetails(status=PROCESSING)
      → BankPostingRequestService.processBankPostingRequest()
  → BankPostingRequestService.processBankPostingRequest() [service/BankPostingRequestService.java:48]
      setBankAccountDetails (resolve recipient bank via BankAccountPort)
      → runInitialValidation (InitialRulesSpecification)  → fail ⇒ REJECT
      → accountExtractionService.extractAccountInformation (client + account lookup)
      → validateDeposit (main Specification chain)
      → handleDepositValidationResult:
           SUCCESS               ⇒ approveBankPostingRequest
           HISTORIC_RECEIPT_DATE ⇒ rejectBankPostingRequest
           anything else         ⇒ moveBankPostingRequestToManual
  → BankPostingRequestProcessor.approveBankPostingRequest() [service/BankPostingRequestProcessor.java:41]
      createLedger → LedgerPostingPort.postLedgerItem → AMQ topic com_ig_trade_v0_legacy_ledger_transaction
      then: TransactionDetails=COMPLETED, request=APPROVED, success email event,
            persist, tastyDepositService, leanDepositService,
            AMQ com_ig_payments_v1_bank_posting notification, clientBankService.addVerifiedBankAccount
```

**Interesting detail — the write ordering is inverted for safety.** The ledger is credited
*before* the local DB is updated (`approveBankPostingRequest` calls `createLedger()` first, persists
last). Nothing binds the two. See §9 for the consequences.

### Flow 2: Manual queue approve/reject (human-in-the-loop)

```
IGIP screen → POST /bankpostingrequests/... (BankPostingRequestController)
  → @HasRole("${bank.postings.manualReview.editRole}") → AuthorisationAspect (AspectJ @Before)
  → BankPostingServiceImpl.approveOrRejectRequest()      [service/BankPostingServiceImpl.java:106]
      getBankPostingRequest(reqIds)
      .filter(status == MANUAL)          ← guard: only MANUAL requests are actionable
      if action == APPROVED:
         .filter(BankPostingRequest::isApproveAllowed)
         updateStatus(list, APPROVING)   ← latch written to DB before the ledger call
         updateApprovedRequests(...)     ← refresh account/currency data
         forEach → approveBankPostingRequest(...) → ledger + APPROVED
                 → whitelistVerifiedBankDetails(...)  (only for NAME_VALIDATION_FAILED holds)
      else:
         updateStatus(list, REJECTING)
         forEach → rejectBankPostingRequest(...) → REJECTED
```

**Interesting detail:** `whitelistVerifiedBankDetails` has an explicit, well-commented business
rule — only deposits held for a **payer-name mismatch** get the payer's bank details whitelisted,
because only in that case has the agent actually verified them. Approvals for AML score, deposit
limit or account status deliberately leave name validation armed for future deposits
(`BankPostingServiceImpl.java:140-158`).

### Flow 3: SICIP / SIP instant payment (two-phase, newest subsystem)

```
Kafka com_ig_payments_v1_payment--live (encrypted JSON)
  → SipDepositEventListener.onMessage()                   [listener/SipDepositEventListener.java:46]
      reads sip-trace-id header → MDC (cleared in finally)
      SipDepositDecryptingDeserializer.decrypt() → SipMessage
      dispatch by messageType across List<SipMessageService> (strategy list)
  → InstantPaymentServiceImpl.initiateInstantPayment()
      isDuplicate(transactionId, UETR) ⇒ drop
      insert BankPostingRequest(status=PROCESSING)
      validateSIPDepositPreAcceptance
        fail ⇒ REJECTED + SIP rejection event + finance/compliance emails
        pass ⇒ publish ACCP ack on SIP outbound topic
  ... later, a second Kafka message ...
  → InstantPaymentServiceImpl.completeInstantPayment()   [service/InstantPaymentServiceImpl.java:101]
      fetch by (transactionId, UETR)
      if status != PROCESSING ⇒ log + return       ← idempotency latch
      switch clrSysRef:
         SETTLEMENT   + txStatus ACSC ⇒ processBankPostingRequestForInstantPayment → SipValidationChain → approve/manual
         CANCELLATION ⇒ REJECTED + finance email
         REJECTION    ⇒ REJECTED + finance email
```

### Flow 4: Operator-driven batch re-drive (JMX)

`TransactionProcessingMbean.processTransaction()` → `TransactionProcessingService.processTransactions()`
→ fetches **all** requests with status `RECEIVED` and re-runs the full processing pipeline, returning
a `{result → count}` histogram in the logs. **There is no `@Scheduled` anywhere in the codebase** —
this is the only re-drive mechanism, and it is invoked by hand over JMX.

---

## 7. Domain / Payment Concepts

**Deposit lifecycle** (`domain/Status.java`): see §8.

**Key domain concepts and where they live:**

| Concept | Location |
|---------|----------|
| `BankPostingRequest` | `domain/domain/BankPostingRequest.java` — the aggregate root: money, remitter, recipient bank, client, status, validation reason, transaction details |
| `TransactionDetails` | Child record holding `ledgerReference`, amount, currency, `completedBy`, own status. **`ledger_reference` is the only UNIQUE constraint in the schema** (`V2__Transaction_Details.sql:17`) |
| `LedgerRequest` | Money + accountId + bankId + subtype + depositReference + feeMoney |
| `Money` | Amount + currency + valueDate; `gbpEquivalent` computed via cached FX (§10) |
| `DepositValidationRequest` | Flattened request+account+flags projection built by `ValidationRequestBuilder`, fed to specifications |
| Payment rails (`dto/Type.java`) | PAYNOW, PAYID, LEANTECH, TRUELAYER, EGIRO, EDDA, BANK_TRANSFER, SICIP (+ BVNK by string in `BankPostingRequestProcessor`) |
| `InstantPaymentTransactionStatus` | ACCP / ACSC / RJCT (ISO 20022 SIP codes) |

### Specification catalogue (the real business logic — 23 rules)

**Initial rules** (`validation/specification/initial/`, run before any client lookup):
`IgnoreClientSpecification`, `CurrencyMismatchSpecification`, `MatchingWithdrawalSpecification`,
`ReceiptDateSpecification`, `ValueDateSpecification`, `TastyDepositSpecification`.

**Main deposit rules** (`validation/specification/`):
`AutomatedFlowFlagSpecification` (global kill switch, §15), `AccountStatusSpecification`,
`AmlRiskScoreSpecification`, `BankAccountNameValidationSpecification` +
`CompositeNameValidationSpecification` + `NameValidationSpecification` (payer-name matching),
`BrokerBankAccountSpecification`, `DepositFromBannedCountrySpecification`,
`DepositFromHighRiskCountrySpecification`, `FundingStatusSpecification`,
`MatchBankAndAccountLegalEntitySpecification`, `MaxDepositAmountSpecification`,
`MaxDepositPerDayLimitSpecification`, `Mt4CurrencySpecification`, `SouthAfricanCurrencySpecification`,
`TaxWrapperSubscriptionSpecification`, `ThirdPartyTransferSpecification`,
`ThirtyDayRuleNonCompliantClientSpecification`, `TrialTradingDepositLimitSpecification`,
`SipAccountStatusSpecification`.

The banned/high-risk country lists are **configuration, not code** —
`resource/.../common/application.yml:250+` under `deposit-validation.banned-countries`, each entry
commented with the country name.

---

## 8. State Machines / Workflows

### **STATE MACHINE DETECTED — `BankPostingRequest.Status`**

Single enum, 9 states, **no formal state-machine library and no transition table**. Transitions are
enforced implicitly by `if`/`filter` guards spread across three classes.

```
                      ┌──────────────── file pipeline / event pipeline ─────────────────┐
                      ▼                                                                  ▼
                  RECEIVED                                                          PROCESSING
       (Mt910/Camt052 transformers,                                        (InstantPaymentRequestTransformer,
        BankPostingRequestAdapter.insert)                                   SICIP two-phase flow)
                      │                                                                  │
       ┌──────────────┼──────────────┐                          ┌───────────────────────┼──────────────┐
       ▼              ▼              ▼                          ▼                       ▼              ▼
   REJECTED       APPROVED        MANUAL                    APPROVED               REJECTED       (skipped:
 (initial-rule  (all specs pass, (any other spec fail,    (clrSysRef=SETTLEMENT   (CANCELLATION /   status
  fail, or       ledger posted)   or ledger post threw)     & txStatus=ACSC)       REJECTION)      != PROCESSING)
  HISTORIC_
  RECEIPT_DATE)                       │
                                      │  operator action via IGIP screen
                          ┌───────────┴───────────┐
                          ▼                       ▼
                      APPROVING               REJECTING          ← intent latches, persisted
                          │                       │
                          ▼                       ▼
                      APPROVED                REJECTED

 TransactionDetails (child) has its own 3-state track:  PROCESSING ──► COMPLETED  (FAILED unused)
```

**Enforcement points (all of them):**

| Guard | Location | Enforces |
|-------|----------|----------|
| `.filter(this::isManualRequest)` → `MANUAL == status` | `BankPostingServiceImpl.java:163` | Only MANUAL requests can be approved/rejected by an operator |
| `.filter(BankPostingRequest::isApproveAllowed)` | `BankPostingServiceImpl.java:113` | Business precondition on manual approval |
| `updateStatus(list, APPROVING/REJECTING)` before the ledger call | `BankPostingServiceImpl.java:115,127` | Latches intent so a concurrent second approval is filtered out by the MANUAL guard |
| `if (!Status.PROCESSING.equals(bankPostingStatus)) return;` | `InstantPaymentServiceImpl.java:110` | Second/replayed SIP settlement message is a no-op |
| `if (ledgerReference.isPresent())` | `BankPostingRequestProcessor.java:44` | APPROVED is only reachable when the ledger accepted the credit |
| `findAllByStatusEntityAndSenderAndDbCreatedTspBefore(..., now-20s)` | `BankPostingRequestAdapter.java:113-115` | **Stale filter**: SICIP requests stuck in PROCESSING are only surfaced after 20s (`STALE_THRESHOLD_SECONDS`) — added by PYMEEM-962, so the manual queue doesn't show in-flight instant payments |

**Side effects on transition:**
- **→ APPROVED**: ledger credit posted to AMQ; `TransactionDetails` → COMPLETED with `ledgerReference`
  and `completedBy`; `completedTime` stamped; success email event published; Tasty deposit handling;
  Lean deposit handling (marks the `PaymentRequest` COMPLETED); AMQ bank-posting notification
  published to `com_ig_payments_v1_bank_posting`; payer bank account added to the client's verified list.
- **→ REJECTED**: `TransactionDetails` → COMPLETED, `acceptOrRejectReason` + `completedBy` +
  `completedTime` set. **No ledger activity, no compensation needed.**
- **→ MANUAL**: `validationFailReason` recorded; request persisted; nothing published.
- **→ APPROVING / REJECTING**: DB write only — pure latch.

**No state transition is validated against a whitelist.** `Status` is a bare enum with no
`canTransitionTo`, and `BankPostingRequest.setStatus` is a plain Lombok setter. An illegal transition
(e.g. `APPROVED → MANUAL`) is prevented only by the fact that no code path currently performs it.
`Status.FAILED` is declared and, in main code, **never assigned** — dead state.

---

## 9. Transactions / Consistency / Idempotency

### **CONSISTENCY MECHANISM — the headline finding: there is almost none**

| Probe | Result |
|-------|--------|
| `@Transactional` in main code | **1 occurrence** — `BankDetailsWhitelistAdapter.java:73` |
| `@Version` / optimistic locking | **0** |
| `@Lock` / `LockModeType` / pessimistic locking | **0** |
| `PlatformTransactionManager` / `TransactionTemplate` / `EntityManager` | **0** |
| JTA / XA / `sessionTransacted` on JMS | **0** — `DefaultJmsListenerContainerFactory` left at default (auto-ack, non-transacted) |
| Kafka `enable.auto.commit` | `false`, `AckMode.BATCH` (`KafkaConfiguration.java`) — offsets committed per batch, after the listener returns |

Every write therefore runs in its **own auto-commit Hibernate transaction per
`repository.save()` call**. There is no unit of work spanning the ledger post and the DB update, nor
spanning `bank_posting_requests` and `transaction_details` (they are saved together only because of
`cascade = ALL` on the `@OneToOne`).

**Concrete exposure — non-atomic approval (`BankPostingRequestProcessor.approveBankPostingRequest`):**
```
1. postLedgerItem(...)   → AMQ send, client credited      ← external, irreversible
2. mutate in-memory state to APPROVED / COMPLETED
3. sendSuccessEmailToClient(...)                          ← event published
4. persistBankPostingRequestWithTransactionDetails(...)   ← DB write
5..8. tasty / lean / AMQ notification / verified-bank-account
```
If step 4 fails (DB blip, constraint, connection loss), the money is on the ledger and the client has
the email, while the local row remains `RECEIVED` (or `APPROVING`). The JMX re-drive
(`processTransactions()` over status `RECEIVED`) would then **post the ledger credit a second time**,
because the ledger reference is minted fresh per attempt:
`ledgerReferenceFactory.newLedgerReference(type, accountId, 1)` in
`LedgerPostingAdapter.buildClientLedgerRequest` — the downstream ledger has no way to recognise a retry.
Steps 5–8 also each fail independently; only step 7 has a try/catch, the others propagate and abort
the remainder.

**Compensation, where it exists:** `createLedger()` catches any ledger exception and calls
`moveBankPostingRequestToManual(request, LEDGER_POSTING_FAILED)` from *inside* the private helper,
then returns `Optional.empty()` so the caller's `if (present)` skips the approve block
(`BankPostingRequestProcessor.java:83-93`). This is correct for a *rejected* send, but for a
**timed-out or lost-response send** the credit may have landed while the deposit sits in MANUAL —
and a subsequent operator approval posts it again.

### **IDEMPOTENCY DETECTED — three separate, inconsistent mechanisms**

**(a) File-level "accept once" — in-memory only.**
`S3ObjectPoller.java:66,74` builds `S3PersistentAcceptOnceFileListFilter(new SimpleMetadataStore(), "streaming")`.
Despite the class name, `SimpleMetadataStore` is a **`ConcurrentHashMap`** — the "persistent" filter is
given a non-persistent store, so the seen-file set is **lost on every restart and is per-JVM**.
Durable dedup actually comes from `BankFilePostProcessor.backupAndDeleteFile` moving the object to
`PROCESSED`/`FAILED` and deleting it from `PENDING` — but that method is `@Async` and swallows every
exception (`catch (Exception e) { log.error(...) }`, `BankFilePostProcessor.java:53`), so a failed move
silently leaves the file in `PENDING` for the next poll.

**(b) Request-level dedup — application-only, no DB backstop.**
`BankPostingRequestAdapter.insertBankPostingRequest` (`:39-72`):
```
for each request:
   fetchBankPostingRequestsByReferenceSince(requestReference, receiptTime.minusWeeks(2))
   if any found → getIfNotDuplicate(): match on
        recipientBankAccountNumber ∧ valueDate ∧ currency ∧ amount
      → match ⇒ treat as already processed, drop from the returned list
   else save(); catch DataIntegrityViolationException ⇒ drop
```
Notable properties:
- The lookback is a hard **2 weeks** (`TWO_WEEKS = 2L`). A genuine duplicate arriving later is
  re-processed and re-credited.
- **`bank_posting_requests.request_id` has no UNIQUE constraint.** The only unique index in the whole
  schema is `TRANSACTION_DETAILS.ledger_reference` (`V2__Transaction_Details.sql:17`). The PK is the
  surrogate `ID` (`PK_BANK_POSTING_REQUESTS`) — see the schema at `mocks/db-initial-setup/schema.sql:68-110`.
  So the `catch (DataIntegrityViolationException)` branch **cannot fire for a duplicate reference**;
  it only catches NOT NULL / FK / length violations. Dedup rests entirely on the read-then-write above,
  with no lock — two concurrent inserts of the same credit both pass the check.
- The outer `catch (Exception e)` (`:66`) wraps the *whole loop*. A failure on request *n* aborts the
  loop but the method still returns the remaining un-inserted requests as if persisted — and the caller
  proceeds to `processTransaction` on rows with `id == null`.

**(c) SIP/SICIP — the strongest of the three.**
`InstantPaymentServiceImpl.isDuplicate` checks the composite `(transactionId, UETR)` via
`findByRequestReferenceAndRelatedReference` before insert, and `completeInstantPayment` refuses to act
unless status is exactly `PROCESSING`. This is a proper idempotency-key + state-latch pair — it is just
not applied to the file pipeline.

### Consistency model summary
- **Strong (single-row) consistency**: each individual `save()`.
- **Eventual consistency**: ledger balance vs. `bank_posting_requests.status`; convergence is
  **manual** — an operator inspects the MANUAL queue and/or triggers the JMX re-drive. There is no
  reconciler job in this repo for bank postings (there *is* a `FastPaymentReconciliationMBean`).
- **Stale-tolerant reads**: FX rates and currency ISO codes, cached 24h (§10).

---

## 10. Persistence / Caching

### Primary store
- **Oracle 19c** (Hibernate dialect pinned to `Oracle10gDialect`), datasource by JNDI
  `ig/jdbc/datasource/bank_postings`, schema owned by user `BANK_POSTINGS`.
- **14 JPA entities**; key ones: `BankPostingRequestEntity`, `TransactionDetailsEntity`,
  `StatusEntity` (status lookup table), `AmlRiskScoreEntity`, `BankAccountEntity`,
  `BankAccountLeMappingEntity`, `BankDetailsWhitelistEntity`, `PaymentRequestEntity`,
  `CurrencyEntity`, `BillerCodeDetailsEntity`.
- IDs from **Oracle sequences** with `allocationSize = 1` (no ID caching → one sequence round-trip per
  insert; safe but chatty).
- **127 Flyway migrations**, `V1`…`V123` plus 4 repeatable `R__` scripts, table `FLYWAY_METADATA`.

### **DB-level audit trail via triggers — invisible from Java**
16 migrations create triggers. Shadow audit tables (`bank_posting_requests_au`,
`transaction_details_au`, `payment_request_au`) are maintained by Oracle triggers, plus **GoldenGate
("GG") replication triggers** (`R__Audit_and_GG_triggers.sql`,
`R__Bank_Posting_Requests_Audit_GG_Trigger.sql`, `R__Transaction_details_Audit_GG_Trigger.sql`,
`R__Payment_Request_Audit_And_GG_triggers.sql`). Every schema change that adds a column must add it to
the `_AU` table *and* re-emit the trigger — visible in e.g.
`V119__AP-12092_Add_Remitting_Bank_Code.sql` and `V123__PYMEEM-1116_Add_Client_Town_Postcode.sql`,
which each ALTER both the base and `_au` table.
**Implication:** the financial audit trail is a database concern; reading the Java code gives no hint
that mutations are being journalled. `db_created_tsp` / `db_modified_tsp` /
`db_created_user_id` / `db_modified_user_id` are populated by triggers, which is why
`BankPostingRequestEntity.dbCreatedTsp` is mapped `insertable = false, updatable = false`.

### Stored procedure
`ObfuscateSensitiveInformationStoredProcedure` + `OracleArraySqlTypeValue` + `ObfuscateRowMapper` —
GDPR erasure is executed as an Oracle stored procedure taking an Oracle **array type** of client IDs,
driven by the `AmqEligibleClientListener` GDPR queue consumer.

### Query patterns / risks
- `BankPostingRequestEntity.transactionDetailsEntity` is `@OneToOne(fetch = EAGER, cascade = ALL)`.
  Every list-returning query (`findAllByStatusEntity`, `fetchApprovedAndRejectedRequests`,
  `fetchApprovedAndManualRequests`, …) therefore eagerly joins/loads transaction details.
  `statusEntity` is a further `@OneToOne` at default EAGER. **N+1 risk** on the manual-queue listing
  endpoints, which fetch by status with no pagination.
- Only `fetchByAccountIdAndDateRangeWithPagination` paginates; the manual-queue and
  approved/rejected fetches return unbounded lists.
- `fetchBankPostingRequestSummaries` uses a **projection interface** (`jpa/projection/`) — the one
  place the eager-graph problem is avoided.
- `fetchBankPostingRequestById(Long)` uses `getOne(id)` → returns a **lazy proxy**, throwing
  `EntityNotFoundException` on access rather than returning null.

### **Lombok `@EqualsAndHashCode` on a bidirectional `@OneToOne` — infinite recursion**
`BankPostingRequestEntity` (`:15`) and `TransactionDetailsEntity` (`:13`) both carry a bare
`@EqualsAndHashCode` covering *all* fields, and they reference each other
(`BankPostingRequestEntity.transactionDetailsEntity` ⇄ `TransactionDetailsEntity.bankPostingRequest`).
Calling `equals`/`hashCode` on either — e.g. putting one in a `HashSet`, or `List.removeAll` /
`List.contains` — recurses until `StackOverflowError`. It also force-initialises the `LAZY`
back-reference. Note `@ToString` *was* given an exclusion list (for PII), but `@EqualsAndHashCode`
was not given one. `BankPostingRequestsProcessor` and `insertBankPostingRequest` both use
`List.removeIf`/`removeAll` — on *domain* objects, not entities, which is why this has not yet bitten.

### Caching
- **Caffeine**, `CacheConfiguration.java`: two caches, `currencies` and `gbpFxRates`, spec
  `maximumSize=50000,expireAfterWrite=1d`.
- Only two `@Cacheable` methods, both on `CurrencyAdapter`: `getIsoCode(symbol)` and
  `getGbpFxRate(isoCode)`.
- **No `@CacheEvict` anywhere.** Invalidation is purely the 1-day TTL.
- **Consistency risk with business impact:** `gbpFxRates` feeds the GBP-equivalent used by
  `MaxDepositAmountSpecification` and `MaxDepositPerDayLimitSpecification`. A rate updated in the DB
  is not honoured for up to 24 hours, and each node caches independently, so the blue and green
  instances can evaluate the *same* deposit limit differently.

---

## 11. External Integrations

### REST / HTTP
| Target | Client | Config |
|--------|--------|--------|
| Client Maintenance (`https://router-int/clientmaintenance`) | IG generated client `wt-client-maintenance-client` | — |
| Account Maintenance (`http://router-int/accountmaintenance`) | IG generated `wt-accountmaintenance` | — |
| Tax Wrapper (`http://router-int/taxwrapper`) | `wt-taxwrapper-client-intf`, Hystrix-wrapped | 3s Hystrix budget |
| Payments API (`https://router-int/payments`) | `@FeignClient PaymentClientApi` | connect/read 5000ms |
| Bank Maintenance | `@FeignClient(name="BankMaintenance")` | connect/read 5000ms |
| Bank Account Verification (`https://router-int/bav-service`) | `@FeignClient(name="BankAccountVerification")` | connect 5000 / **read 35000**, Hystrix override **45000ms** |
| Currency Conversion & Tasty (`https://router-int/funds-transfer-service`) | `funds-transfer-service` client | 3s Hystrix budget |
| Trial Trading Validation | `@FeignClient TrialTradingValidationApi` | default |

**Resilience posture:** entirely inherited from Spring Cloud Dalston — Hystrix thread isolation with a
**3000 ms default command timeout** and Ribbon connect/read timeouts. **No `@Retryable`, no
`spring-retry`, no explicit `CircuitBreaker` bean, no declared fallbacks.** A Hystrix trip surfaces as
an exception, which the adapters translate to `ExternalServiceException` / `BankPostingException`, which
`TransactionProcessingService.processTransaction` converts into **status MANUAL** — i.e. *the manual
queue is this system's circuit-breaker fallback.* A downstream outage does not lose deposits; it
converts them into human work.
`AccountMaintenancePort.fetchAccountDetailsGracefully` (used in `LedgerPostingAdapter`) is the one
soft-fail path, returning `Optional.empty()` rather than throwing.

### Message brokers

**AMQ / ActiveMQ Artemis 2.13 ("kazooie") — outbound**, `AmqJmsConfiguration.java`:
- `com_ig_trade_v0_legacy_ledger_transaction` — ledger credits, via `ct-ledger`'s
  `JmsLedgerTransactionsSender` + `LedgerTransactionService`, **JSON** content type,
  generating system `MW`, on a `CachingConnectionFactory`.
- `com_ig_payments_v1_bank_posting` — bank posting notifications, plain `JmsTemplate`,
  `pubSubDomain = true`, `receiveTimeout = 3000ms`.
- `com_ig_platform_v0_communication_event` — email requests to the comms platform.
- **Inbound**: one `@JmsListener` (`AmqEligibleClientListener`, GDPR erasure queue) on a
  **durable shared subscription** (`setSubscriptionDurable(true)`, `setSubscriptionShared(true)`,
  `setAutoStartup(false)`) with Avro-over-JMS serdes against the schema registry.
- Sessions are **not transacted** → auto-acknowledge. A listener exception after a partial side effect
  loses the message.
- `configureJmsListeners` wraps registration in `try/catch` and only **logs** on failure — the app
  starts healthy with no GDPR consumer attached.

**Kafka 0.11.0.2 ("peach") — 4 hand-built containers**, `KafkaConfiguration.java`:
| Container | Topic | Payload |
|-----------|-------|---------|
| `riskScoreKafkaMessageListenerContainer` | `com_ig_client_v1_aml_riskscore` | Avro `RiskScore` |
| `fastPaymentsKafkaMessageListenerContainer` | `com_ig_payments_v1_payment--live` | Avro `CreditNotification` |
| `sipDepositKafkaMessageListenerContainer` | SIP deposit topic | encrypted JSON String |
| (producer) `paymentProducer` | `com_ig_payments_v1_payment--live` | Avro `Payment` |

- Topics are subscribed by **compiled regex pattern** built from `topic` / `topic.ignore` /
  `topic.pattern` properties (`compileTopicPattern`) — a topic can be excluded by config without a
  code change.
- `groupId` = `ig.kafka.applicationName`; `clientId` derived from hostname + Catalina instance.
- `enable.auto.commit=false`, `AckMode.BATCH`, `auto.offset.reset` default `latest`.
- **`container.setAutoStartup(false)` on all three consumers** — they are started/stopped exclusively
  by the leader-election listener (§12).
- `SipDepositEncryptingSerializer` / `SipDepositDecryptingDeserializer` — **application-level
  payload encryption** on the SIP topic, keys under `opt/encryptionkeys` and `mocks/encryptionkeys`.
- `KafkaErrorHandler` handles listener exceptions; `SipDepositEventListener` additionally
  catches everything itself and logs — **so a poison SIP message is skipped, not retried, and the
  offset advances.** Note it logs `payload={consumerRecord.value()}` on failure, which is the
  *encrypted* value, so no PII leaks.

### S3 (Cohesity-backed)
Bucket layout `PENDING` / `CAMTPENDING` / `PROCESSED` / `FAILED` / `INVALID`, `s3.readTimeout=100000`.
`BankFileDownloader.downloadFromCohesityS3` calls `listBuckets()` **on every download** to confirm the
bucket exists before `getObject` — an unnecessary account-wide API call per file, and one that requires
broader IAM permission than reading the object.

### Zookeeper
Curator 2.12 via `mantis-leader-election` 1.0.84. Latch id `bank-postings-leader-election`, path
`/application/bank-postings/leader`, blue/green state root `/bgstate/tomcat/bank-postings/live`.

---

## 12. Concurrency / Threads

### **CONCURRENCY — leader election is the concurrency model**

There is no application-level parallelism to speak of; correctness relies on **only one node doing
anything at all**.

- `LeaderElectionConfiguration` imports `ZookeeperConfiguration` +
  `LeadershipElectionInBlueGreenConfiguration` from the `mantis` library.
- `KafkaLeaderElectionListener.onTakeLeadership()` **starts** all three Kafka containers;
  `onAbandonLeadership()` **stops** them. Combined with `setAutoStartup(false)`, a non-leader node
  consumes nothing.
- `LeaderOnlyFilter` (a Spring Integration `@Filter` on `s3Channel`) drops every polled S3 file on a
  non-leader, and carefully closes both the payload `InputStream` and the S3 session
  (`closeStream` + `closeTheSession`) to avoid leaking connections on the discarded path.
- Escape hatch: `mantis.leaderelection.enabled` — when `false`, `isLeader` is forced true
  (`LeaderOnlyFilter.java:36`). Set `true` in `common/application.yml:153-155`.
- `LeaderElectionController` exposes leadership state over HTTP; `AmqDarkLightStateListener` and
  `IGClusterDetails` track the blue/green dark/light state (the latter with its own single-thread
  `ScheduledExecutorService` polling a state file every second, purely for log enrichment).

### Thread model
- Request threads: Tomcat 7 connector pool (container-configured, not in this repo).
- File pipeline: Spring Integration `defaultPoller` — `PeriodicTrigger(10)` (10 ms!) as the *default*
  poller; the two S3 adapters override with `fixedDelay` 20000 ms (`.fin`) and 10000 ms (CAMT), and
  `maxMessagesPerPoll = MESSAGE_PER_POLL`. Downstream channels are `DirectChannel`, so
  transform → insert → validate → ledger-post all run **on the poller thread**, serially.
  The `s3Channel` is a `QueueChannel`, so files buffer in memory between poll and processing.
- Kafka: one thread per `KafkaMessageListenerContainer`, `concurrency` not set → single consumer each.
- JMS: `DefaultJmsListenerContainerFactory` defaults (1 concurrent consumer).
- `@Async`: exactly one method, on `SimpleAsyncTaskExecutor` (§3) — **a new unbounded thread per file
  post-processed**. At normal file volumes this is invisible; during a backlog drain it is unbounded
  thread creation.

### Race conditions / concurrency risks
1. **Manual approve is read-then-write with no lock.** `approveOrRejectRequest` reads by id, filters
   `status == MANUAL`, then writes `APPROVING`. Two operators (or a double-clicked button) acting
   inside that window both see MANUAL and both proceed to `approveBankPostingRequest` → **two ledger
   credits**. No `@Version`, no `@Transactional`, no `SELECT … FOR UPDATE`, and the ledger reference is
   regenerated per call so the downstream cannot dedup. This is the highest-severity concurrency finding.
2. **`AutoPostingsControlService.isAutomationEnabled` is a mutable, non-`volatile` instance field**
   (`AutoPostingsControlService.java:14`) written from the **JMX thread**
   (`toggleAutomationFlag`) and read from **poller and Kafka threads** via
   `ValidationRequestBuilder`. No happens-before edge → the kill switch may not be observed by
   processing threads. It is also **per-JVM and in-memory**: the toggle is lost on redeploy (reverting
   to `auto.bank.postings.enabled`) and must be flipped separately on the blue and green nodes.
3. **`@Async` file deletion races the processing loop.** `processExtractedRequests` calls
   `backupAndDeleteFile` (async) *before* `forEach(processTransaction)`. The S3 object can be moved and
   deleted while the requests it produced are still being validated. Combined with the in-memory
   accept-once filter, a crash mid-loop can leave requests inserted-but-unprocessed *and* the file gone.
4. **MDC leaks on the exception path.** `BankPostingRequestsProcessor.processExtractedRequests`
   (`:30`, `:39`) and `BankCreditMessageManager.doProcess` (`:33`, `:35`) call `MDC.put` … `MDC.remove`
   with **no `finally`**. An exception mid-flow leaves `file=` bound to the pooled poller thread and
   mislabels subsequent log lines. `SipDepositEventListener` gets this right — `finally { MDC.remove }`
   (`:63`). `LeaderOnlyFilter` removes on both branches but also without `finally`.
5. **`SimpleMetadataStore` is per-instance**, so during a leadership handover the new leader has an
   empty seen-set (mitigated in practice by the PENDING→PROCESSED move, itself best-effort).

### Context propagation
- **MDC** carries `file` (`MDC_FILE`) through the file pipeline and `sip-trace-id` through the SIP flow;
  the logback pattern emits `sipTraceId=` in all environments (documented in README, Honeycomb dataset
  `bankpostings`).
- **OpenTelemetry 1.15.0**: `TracingSupportFilter` for HTTP; `SipDepositEventListener` implements a
  hand-rolled `TextMapGetter<Headers>` to extract trace context from Kafka headers — note it reads the
  `sip-trace-id` header directly rather than invoking the OTel propagator, so the W3C trace context is
  not actually joined; correlation is by business trace id, not by span parentage.
- **`RequestContext.getPrinciple()`** (IG SSO `ThreadLocal`) is read deep inside
  `LedgerPostingAdapter.getUsernameFromRequest()` to stamp `internalUser` on the ledger entry. On the
  *file/Kafka* paths there is no HTTP request, so this ThreadLocal is empty and `internalUser` is
  `null` — a hidden coupling between the presentation layer and the ledger payload. It also filters
  out `*-sso` app usernames deliberately.
- **No context propagation across the `@Async` hop** — the file post-processor logs without the
  `file` MDC value it would need.

**No virtual threads** (Java 8), **no `CompletableFuture`**, **no `ExecutorService`** outside the
logging helper.

---

## 13. Cross-Cutting / Security / Observability

### Security
- **Authentication:** IG SSO via `wt-singlesignon` 1.81.1 + `ig-sso-spring-boot-starter`;
  `X-Security-Token` header (visible in the README curl example). `RequestContext` is the SSO
  `ThreadLocal`. **No Spring Security** — no `@EnableWebSecurity`, no filter chain in this repo.
- **Authorization: a custom `@HasRole` annotation + AspectJ aspect** (`config/HasRole.java`,
  `config/AuthorisationAspect.java`). The aspect resolves the role through
  `Environment.resolvePlaceholders(...)`, so the role name is a property
  (`bank.postings.manualReview.editRole` → e.g. `RG-IGIP-CREDITRISK-BANKPOSTINGS-MANUALREVIEW-EDIT-DEV`)
  and differs per environment. Failure throws `UnauthorizedException` → HTTP 403.
- **Coverage is thin: `@HasRole` appears 4 times** — twice on `BankPostingRequestController`
  (`:86`, `:103`) and twice on `BankDetailsWhitelistController` (`:47`, `:66`) — across
  **~28 controllers**. Everything else (including `AdminController`, `BankPostingController`,
  `ExternalBankPostingRequestController`, `InstantPaymentController`, and the account/bank lookup
  endpoints that accept an `accountId` parameter) relies on authentication alone, with **no
  object-level ownership check**. This is the same BOLA-shaped exposure tracked in the
  payments-gateway remediation programme — worth cross-referencing rather than re-deriving.
- The aspect pointcut `execution(* *.*(..)) && @annotation(hasRole)` is evaluated on **Spring AOP
  proxies**, so an internal self-invocation of an annotated method bypasses the check entirely.
- **Secrets:** JDBC credentials come from the Tomcat JNDI datasource; SIP payload encryption keys
  from `opt/encryptionkeys` (mounted, not committed). `.snyk` and a GitGuardian CI component are
  present. No credentials found in the repo.
- **PII handling is deliberate:** `@ToString(exclude = {...})` on `BankPostingRequestEntity` masks
  `remittingName`, `clientName`, `clientResidentialCountry`, `clientTown`, `clientPostalCode`,
  `sender`, `remittingIban`, `recipientBankAccountNumber`. **But** `BankPostingRequestValidator`
  logs `bankPostingRequest={}` on the *domain* object (`:27`, `:32`) and
  `BankPostingRequestsProcessor.filterOutUnknownRecipientBankAccount` logs `request={}` (`:45`) —
  whether these leak PII depends on the *domain* class's `@ToString`, which is a gap worth checking
  before touching those log lines. `LedgerPostingAdapter:66` logs the full `ledgerRequest`.
- **GDPR erasure** is implemented end-to-end: AMQ eligible-client queue → `EligibleClient` /
  `ClientDeletionStatus` → Oracle obfuscation stored procedure → `ObfuscationFailedClientController`
  for failures.

### Observability
- **Logging:** SLF4J + Logback 1.2.2, `wt-common-log`, per-environment `bank-postings-logback.xml`.
  Custom converters `DeploymentEnvironmentConverter` and `ServiceModeConverter` inject
  environment/dark-light state into every line. **A strong, consistent convention:
  `log.info("method=<name> ...", args)`** — grep-able by method name across all environments.
- **Metrics:** `metrics-goldensignal` 1.99.0 — `GoldenSignalsConfiguration` + `GoldenSignalsFilterConfig`
  + `PrometheusScrapeEndpointController` (imported directly on the application class).
- **Tracing:** OpenTelemetry 1.15.0, Honeycomb dataset `bankpostings`, `sip.trace_id` as the query key.
- **Health:** `/bank-postings/monitor/version` (README).
- **JMX is a first-class operational surface — 8 MBeans:** `FlywayMbean` (migrate/repair by hand),
  `TransactionProcessingMbean` (re-drive all RECEIVED), `AutoPostingsControlMBean` (toggle
  AUTOMATED/MANUAL), `BankPostingRequestMbean`, `AutoVerifiedBankPostingMBean`,
  `FastPaymentReconciliationMBean`, `S3OperationsMbean`, `FeatureFlagMBean`. The README documents
  driving these with `jmxterm`. **This is where the "scheduler" went** — batch work is operator-initiated.

---

## 14. Errors / Failure / Resilience

### Exception hierarchy
16 custom exceptions in `domain/exceptions/`, all carrying `(errorCode, errorMessage)`:
`BankPostingException` (the general base used by the pipeline), `LedgerPostingException`,
`ExternalServiceException`, `BankFileNotFoundException`, `FastPaymentsException`, `TastyException`,
`SipNotificationException`, `EncryptionException` / `DecryptionException`, `IbanNotFoundException`,
`IllegalCurrencyException`, `InvalidAccountIdException`, `InvalidDateTimeRangeException`,
`InvalidStatusException`, `BillerCodeException`, `UnauthorizedException`.
Error codes are centralised in `common/BankPostingErrorCodes` (enum with message text).

`ExceptionResponseEntityHandler` (`@ControllerAdvice`) maps them to `ErrorResponseDTO`; almost
everything becomes **400**, with a catch-all `@ExceptionHandler(Exception.class)` and a special case
for Tomcat's `ClientAbortException` ("An established connection was aborted").

### Failure modes and what actually happens
| Failure | Behaviour |
|---------|-----------|
| Downstream HTTP timeout / 5xx | Hystrix trips (3s) → adapter throws → `processTransaction` catches `BankPostingException` → **status MANUAL** with the reason recorded. Deposit preserved as human work. |
| Ledger post throws | `createLedger` catches → MANUAL with `LEDGER_POSTING_FAILED`; `Optional.empty()` suppresses the approve block. **Unsafe if the send actually landed.** |
| Ledger post lost/timed out but delivered | Silent divergence: credited on the ledger, MANUAL locally. Later operator approval double-credits. **No reconciler for this in the repo.** |
| DB write fails mid-approval | Money on the ledger, row not APPROVED. Re-drive double-credits. |
| Corrupt/unparseable bank file | `BankPostingData.corrupted = true` → file moved to `FAILED/`; `CustomErrorHandler` (`@ServiceActivator(inputChannel="errorHandlerChannel")`) handles poller-thrown errors. |
| S3 move/delete fails | Logged at ERROR only; file stays in `PENDING` → re-polled after restart → dedup falls back to the 2-week reference check. |
| Poison Kafka message | `SipDepositEventListener` catches everything and logs; **offset advances, message dropped**. Other containers delegate to `KafkaErrorHandler`. |
| JMS listener throws | Non-transacted session → already acknowledged → **message lost**. |
| Zookeeper session loss | `onAbandonLeadership` stops all consumers; the node goes quiet (correct fail-safe). |
| Downstream side effects after approval (tasty/lean/notification/whitelist) | `sendNotificationAboutBankPosting` and `whitelistVerifiedBankDetails` are individually try/caught with an explicit "the deposit remains approved" comment; `tastyDepositService` and `leanDepositService` are **not** — a throw there aborts the remaining steps after the ledger credit. |

### Recovery strategies
- **Retry:** none declarative. Recovery = MANUAL queue + JMX re-drive.
- **Circuit breaker:** Hystrix, implicit, default thresholds; no fallback methods.
- **Fallback:** the human operator. Explicitly designed for — `AutoPostingsControlMBean` exists to
  flip the whole system into manual mode when auto-approval must stop.

---

## 15. Configuration / Infrastructure

### Configuration management
- YAML per environment in `resource/src/main/properties/`: `common/application.yml` (the base, ~260
  lines) plus `application-{LOCAL,DEV,TEST,UAT,DEMO,LIVE,PE}.yml`, each with
  `<ENV>.environment.java.properties`, `bank-postings-logback.xml`, `amq.properties`,
  `kafka.properties`, and a Tomcat `context.xml`.
- Environment is selected at **build time**, not runtime: `war/pom.xml` properties
  `<tomcat-env>` and `<tomcat-props-path>` (README instructs editing these to switch to LOCAL).
- **Business rules live in configuration**, which is the single most important thing to know before
  changing behaviour:
  - `deposit-validation.banned-countries` / `high-risk-countries` (long, comment-annotated ISO lists)
  - `deposit-validation.manual-review-bank-account-ids` (e.g. `LLOY136`)
  - `auto.bank.postings.enabled` — global auto-approval switch (JMX-togglable, §12)
  - `bank.postings.manualReview.editRole` — the authorization role, per environment
  - `bank.fastPaymentsBanks.{nab,westpac}.<LEGAL_ENTITY>` → bank account id mapping
  - bank ignore-list / automation-list / third-party-transfer-list, read via `BankProperties`
  - `poller.fin.fixed-delay` = 20000, `poller.camt.fixed-delay` = 10000
  - `mantis.leaderelection.*`, `hystrix.command.*`, `feign.client.config.*`
- Cloud-config-backed property beans exist too (`NameValidationCloudProperties`,
  `IgnoreClientListCloudProperties`) — so some flags (e.g. `isBankDetailsWhitelistEnabled`) are
  changeable without redeploy.
- `AutomatedFlowFlagSpecification` shows a **SIP bypass**: `if (SIP_NETWORK_TYPE.equals(networkType))
  return SUCCESS;` — SIP/SICIP deposits ignore the global auto-posting kill switch and the
  per-bank automation list.

### Infrastructure
- **Deployment:** WAR into Tomcat 7 on Nomad (`nomad login -method=gitlab-ci` in CI), blue/green
  ("dark/light") with Zookeeper-coordinated leadership.
- **IaC:** `terraform/acceptance/` provisions the acceptance environment, including an Oracle
  `000_schema.sql`.
- **CI (`.gitlab-ci.yml`, 8.6k):** includes IG shared templates (`ci-pret-v2`,
  `common-security-steps`, `common-code-quality-steps`), local `internal-static-analysis.yml` and
  `code-quality.yml`, plus **GitGuardian secret scanning** and a **Locust load-test** component.
  Jobs: `build` (`mvn deploy -P coverage`, surefire + JaCoCo artifacts) → `acceptance test` →
  `acceptance-performance-deploy`. Snyk config in `.snyk`.
- **Local dev:** `mocks/docker-compose.yml` brings up MockServer, Adobe S3Mock, Oracle 19c
  (ARM64/AMD64 image choice called out), Zookeeper, Kafka, Artemis, and a Hortonworks schema registry.

---

## 16. Testing Discoveries

**Inventory:** 254 unit/integration test classes (94 `domain`, 160 `integration`), 22 Cucumber
step/support classes, 23 `.feature` files, 6 post-deployment tests. `service-api` has **no tests**
(DTO-only). Naming convention `{scenario}_{expectedOutcome}` per repo CLAUDE.md.

### **UNUSUAL TESTING TECHNIQUE 1 — out-of-process black-box acceptance tests**
`component-tests` does **not** use `@SpringBootTest`. CI builds and publishes a Docker image of the
app, then GitLab CI starts it **as a `services:` sibling** alongside real MockServer 5.15,
Adobe S3Mock 4.12, ActiveMQ Artemis 2.43, Zookeeper 7.8, Kafka 7.8 and the IG Hortonworks schema
registry (`.gitlab-ci.yml:89-148`). Cucumber then drives the running container over HTTP/Kafka/AMQ/S3
and asserts against the real Oracle schema. Support classes: `CucumberApplicationTests`
(JUnit Platform suite), `CucumberConfiguration`, `TestDatabaseConfig` + `TestDatabaseSetup`,
`SetupMocks`, `KafkaTestHelper`, `KafkaTestConsumer`, `SipTestConsumer`, `AdminApiClient`,
`XmlTestHelper`, `GlobalHooks`, and **`AwaitilityConfiguration`** — Awaitility is essential because
the pipeline is asynchronous and eventually consistent, so assertions poll.
Profile `component-tests-pipeline`; reports as GitLab artifacts (`cucumber-reports`, `failsafe-reports`).
**Trade-off:** genuinely end-to-end, catches wiring/serialisation/schema-registry bugs that mocks
cannot — but slow, gated (`ENABLE_INTEGRATION_TESTS` / MR / tag only), and **requires manually
pre-seeded `BANK_ACCOUNT_LE_MAPPING` rows**, listed verbatim as ~18 INSERT statements in
`component-tests/README.md` with the note *"We are planning to move this into setup stage"*.

### **UNUSUAL TESTING TECHNIQUE 2 — `make-it-easy` Maker DSL**
`make-it-easy` 4.0.1 (Nat Pryce's test-data-builder library) with hand-written Makers:
`BankAccountMaker`, `BankAccountMappingMaker`, `BankAccountEntityMaker`,
`DepositValidationRequestMaker`, `BankPostingRequestEntityMaker`. Gives
`make(a(BankAccount, with(currency, "GBP")))`-style construction — an uncommon choice today
(most codebases would use Lombok `@Builder` directly) and a deliberate one, since Lombok `@Builder`
is available on these very classes.

### Other test infrastructure
- **HSQLDB 2.5.0** as an in-test database for repository tests (`BankPostingRepositoryTest`).
- **WireMock** via `spring-cloud-contract-wiremock` 1.1.0 for adapter tests.
- **JUnit 5** (5.4.2) + `spring-junit5` 1.2.0 bridge (needed because Spring Boot 1.5 predates JUnit 5
  support) + JUnit 4.12 still on the classpath.
- **Mockito 3.4.6** — plain mocks; no `mockStatic`/inline mock maker, no PowerMock.
- Feature files map ~1:1 onto specifications (`MaxDepositAmountSpecification.feature`,
  `ThirtyDayRuleNonCompliantClientSpecification.feature`, `NameValidation.feature`,
  `AutoApproval.feature`, `AutoApprovalCamtFile.feature`, `SipDepositSpecification.feature`,
  `SicipPaymentTypeFilter.feature`, …) — **the acceptance suite is organised by business rule, not by
  endpoint**, which is the clearest signal that the specifications *are* the product.
- `post-deployment-tests` run with `mvn verify -pl post-deployment-tests -P dev` against a live server.

---

## 17. Custom Libraries / Implicit Behavior

| Library | What it provides / induces |
|---------|---------------------------|
| `mantis-leader-election` 1.0.84 (+ `mantis-goldensignal`) | `ZookeeperConfiguration`, `LeadershipElectionInBlueGreenConfiguration`, `LeadershipApplicationState`, `LeaderElectionListener`. **Implicitly wires Curator, the ZK latch and blue/green state** from two `@Import`s. |
| `ct-ledger` (`com.ig.ct.ledger`) | `LedgerTransactionService`, `JmsLedgerTransactionsSender`, `LedgerReferenceFactory`, and the event types `BankLedgerPayment`, `BvnkPayment`, `BvnkFeeCharged`. **Owns the ledger reference format and the AMQ wire contract** — the single most business-critical dependency. |
| `enterprise-message-bus-kafka` 1.1.27 / `-jms` / `-security` | `AvroEnterpriseMessageBusProvider`, `DefaultConsumerFactory`, `RegistryAvroSerdesConnectionFactory`, `ConnectionFactoryBuilder`. **Injects schema-registry Avro serdes and broker security transparently**; `CLUSTER_NAME_CONFIG`/`APPLICATION_NAME_CONFIG` resolve brokers by logical cluster name ("peach"/"kazooie") rather than bootstrap URLs. |
| `ig-sso-spring-boot-starter` 1.0.6 / `wt-singlesignon` 1.81.1 | SSO filter chain + `RequestContext` ThreadLocal. Authentication happens with **no security code in this repo**. |
| `ig-feign-spring-boot-starter` 1.0.39 | Feign defaults, interceptors, error decoding. |
| `ig-web-` / `ig-swagger-spring-boot-starter` | Web + Swagger conventions. |
| `wt-common-log` 1.54.0 | Logback layout/appender conventions and the environment/service-mode converters. |
| `metrics-goldensignal` 1.99.0 | Prometheus scrape endpoint + golden-signal servlet filter, enabled by two `@Import`s on the application class. |
| Prowide SWIFT SRU2019-8.0.2 | MT910 parsing (`Mt910CreditMessage`). |
| data-pod clients (client / payments / finance) | Generated Avro types: `com.ig.client.v1.aml.RiskScore`, `com.ig.payments.v1.Payment`, `com.ig.payments.v1.fastpayments.CreditNotification`, `com.ig.finance.v3.crypto.cash.Event`. **Topic schemas are owned outside this repo.** |
| Fiorano MQ (`ig-fiorano-spring-boot-starter` 1.0.31) | Legacy broker, `FioranoConfiguration` — see §18. |

---

## 18. Legacy / Historical Discoveries

1. **`REQUEST_ID` was once the primary key.** The schema still carries
   `comment on column BANK_POSTING_REQUESTS.REQUEST_ID is 'Primary key of the table'`
   (`mocks/db-initial-setup/schema.sql:112`), and `V13__Alter_Trans_Details_tbl.sql:4` created
   `FK_TD$BANK_POSTING_REQ FOREIGN KEY (request_id) REFERENCES BANK_POSTING_REQUESTS (request_id)`.
   The current PK is the surrogate `ID` sequence, and `TransactionDetailsEntity` now joins on
   `bank_posting_request_id → id`. **The stale comment is actively misleading** — it is why the
   `catch (DataIntegrityViolationException)` dedup branch in `insertBankPostingRequest` reads as if a
   unique constraint protects `request_id` when none does (§9b).
2. **`V11__Alter_Bank_Posting_tbl.sql` begins with `DELETE FROM BANK_POSTING_REQUESTS;` and
   `DELETE FROM TRANSACTION_DETAILS;`** — an early migration that discarded all data to enable a
   schema change. Fine historically; a landmine for anyone replaying migrations against real data.
3. **`java.util.Observable`** — `AmlRiskScoreEventListener`, `FastPaymentsEventListener` and
   `SipEventListener` all `extends Observable`, using the JDK observer mechanism (deprecated in Java 9)
   for fan-out, alongside a modern strategy-list dispatch in the newer `SipDepositEventListener`.
   Two generations of event handling coexist.
4. **Fiorano MQ** (`FioranoConfiguration`, `ig-fiorano-spring-boot-starter`) — the pre-Artemis
   broker. Main config remains; the only substantial coverage is
   `FioranoConfigurationTest` (~8 client-id cases). A migration remnant.
5. **RESTEasy 3.0.9 + `jsr311-api`** are still declared, with an explicit `jsr311-api` exclusion on
   `bank-postings-service-api` in root `dependencyManagement` — a JAX-RS layer being displaced by
   Spring MVC `@RestController`s, with the version conflict papered over.
6. **Three READMEs:** `README.md` (current, 14.8k), `README.txt` (5.5k) and `readme.md.old` (1.7k),
   all still present. `README.md` states "Spring Boot 2.x with Java 8" in its Technology Stack
   section — **incorrect**; the POM pins 1.5.9.RELEASE. `CLAUDE.md` has it right.
7. **`wt-featureflag` is commented out** in root `pom.xml` (`<!-- <wt-featureflag.version>2.1.15 -->`),
   yet `FeatureFlagMBean` remains — feature flags moved to cloud properties + JMX.
8. **`Status.FAILED`** is declared but never assigned in main code; the `STATUS` table comment
   ("can be PROCESSING,COMPLETED,FAILED for transaction details Or MANUAL,APPROVED,REJECTED for bank
   posting request") predates `RECEIVED`, `APPROVING` and `REJECTING`.
9. **Duplicated ports/adapters** (`port/BankAccountPort` vs `port/bankaccount/BankAccountPort`;
   two `CurrencyConversion` packages) — an in-flight, unfinished repackaging.
10. Commented-out `log.info` lines left in `BankPostingRequestAdapter.java:82-83`.
11. **`openspec/`** — spec-driven-development artefacts (`proposal.md`, `design.md`, `tasks.md`,
    `spec.md` per change, plus `factory/metrics.jsonl`), with an archive folder. The two tracked
    changes (`add-stale-sicip-processing-filter`, `sip-deposit-account-status-scenarios`) match the
    most recent commits. Alongside `.claude/agents/*` (Jira card lifecycle skills) and
    `.claude/commands/summarise.md`, this is an **agent-assisted development workflow**, newer than
    most of the code.

---

## 19. Patterns & Conventions

### Design patterns detected
| Pattern | Evidence | Purpose |
|---------|----------|---------|
| **Ports & Adapters** | 30 `*Port` interfaces in `domain`, 30 `*Adapter` in `integration` | Keep domain framework-free |
| **Specification** | `Specification.isSatisfiedBy` + `AndSpecification`/`CompositeSpecification`; 23 rule classes | Composable, individually testable business rules |
| **Pipes & Filters** | Spring Integration channels `s3Channel → leaderFilterChannel → processRequest` | Decouple poll / authorise / parse / process |
| **Strategy (list injection)** | `List<SipMessageService>` filtered by `supports(messageType)`; `List<Specification>` in `SipValidationChain` | Add a SIP message type or rule by adding a bean |
| **Transformer/Mapper** | `transformers/*` (entity⇄domain), `Mt910ToBankPostingRequestTransformer`, `Camt052V02ToBankPostingRequestTransformer` | Boundary mapping, static methods |
| **Test Data Builder** | `make-it-easy` Makers | Readable fixtures |
| **Latch / intent state** | `APPROVING`/`REJECTING`, `PROCESSING` guard | Poor-man's concurrency + idempotency control |
| **Operator control plane** | 8 JMX MBeans | Manual re-drive, kill switch, migrations |

### Two *different* validation semantics — know which you are in
- `AndSpecification.isSatisfiedBy` **short-circuits** on the first non-SUCCESS and returns that single
  result. Used for the classic file/deposit flow — the deposit gets *one* failure reason.
- `SipValidationChain.validateAll` runs **every** specification and collects **all** failures into a
  `SipValidationResult`, which `SipValidationFailureTrigger` then fans out to distinct
  finance / compliance / account-opening email audiences before deciding the manual-queue outcome
  (`BankPostingRequestService.handleSipValidationResult`).
  **Adding a specification to the SIP chain can therefore trigger emails that the same specification
  in the AND chain never would.**

### Coding conventions
- **Logging: `log.info("method=<methodName> <text> key={}", value)`** — near-universal, and the basis
  of Honeycomb/Splunk queries. Follow it exactly.
- Constructor injection via `@RequiredArgsConstructor` with `final` fields (CLAUDE.md mandates `final`).
  `LedgerPostingAdapter` is the exception with an explicit `@Autowired` constructor.
- `@Slf4j` everywhere; no `System.out`.
- 3-space indentation in `domain`/`integration` (some newer files use 4 — mixed).
- Static imports used heavily for enum constants (`import static ...Status.APPROVING`).
- Error codes centralised in the `BankPostingErrorCodes` enum; exceptions always
  `(errorCode, errorMessage)`.
- Migrations named `V<n>__<TICKET>_<Description>.sql`; repeatable audit/GG triggers as `R__*.sql`.
- Branches `{BOARD}-<ticket>`, commits `[{BOARD}-XXX]: description` (PYMEEM, PYMG, AP, CAMP boards).

### Architectural conventions for adding code
- **New external dependency** → port in `domain/port`, adapter in `integration/adapter`, never a
  client type in `domain`.
- **New business rule** → a `CompositeSpecification` subclass + a new `DepositValidationResult` enum
  constant + a `.feature` file; wire it into the chain (and decide AND-chain vs SIP-chain, see above).
- **New payment rail** → a `Type` enum constant, a transformer, a `getLedgerSubtype`/
  `getDepositReference` case in `BankPostingRequestProcessor`, and a `SipMessageService` if
  event-driven.
- **New operator action** → a JMX MBean, not a scheduled job.
- **Anything that must not run twice per cluster** → gate it on
  `LeadershipApplicationState.isLeader()`.

### Convention smell worth knowing
`BankPostingRequest.fileName` is **overloaded**: for file-sourced deposits it is a real S3 key, but for
event-sourced rails it holds the *rail name* (`PAYID`, `PAYNOW`, `EGIRO`, `EDDA`, `LEANTECH`,
`TRUELAYER`, `BVNK`). Both `BankPostingRequestProcessor.getLedgerSubtype(fileName)` and
`getDepositReference(fileName)` `switch` on it, defaulting to `BANK_TRANSFER` / `"Bank Deposit"` for
real filenames. A `switch` on a **null** `fileName` throws NPE, and the DB column is `NOT NULL`, so the
invariant holds today only by construction. Any new rail must remember to set `fileName` to its rail
name or it will be ledgered as a plain bank transfer.

---

## 20. Important Discoveries (Ranked)

1. **No transaction management and no locking in a money-moving system.** One `@Transactional` in
   ~700 files; zero `@Version`, zero `@Lock`, non-transacted JMS. `approveBankPostingRequest` posts
   the ledger credit *before* persisting APPROVED, with 4 further un-guarded side effects after the
   DB write, and the ledger reference is regenerated on every attempt so the downstream cannot dedup.
   **A DB failure between the credit and the status update, or the JMX re-drive of a stuck RECEIVED
   request, double-credits the client.** *Implication:* any change touching
   `BankPostingRequestProcessor` must preserve the existing ordering and null-check discipline;
   the durable fix is a stable idempotency key on the ledger event, not a `@Transactional`.

2. **Manual approval has a read-then-write race with no lock.** `approveOrRejectRequest` filters
   `status == MANUAL`, then writes `APPROVING`. Two operators (or one double-click) inside that window
   both post to the ledger. The `APPROVING`/`REJECTING` latch was clearly *intended* as the guard but
   is not atomic. *Implication:* highest-value hardening target; a conditional update
   (`UPDATE … SET status=APPROVING WHERE id=? AND status=MANUAL` checking the affected-row count)
   closes it without restructuring anything.

3. **Request dedup is application-only and has no database backstop.**
   `bank_posting_requests.request_id` has **no unique constraint** (the only unique index in the
   schema is `TRANSACTION_DETAILS.ledger_reference`), while the code catches
   `DataIntegrityViolationException` as if one existed. Dedup = an unlocked read of the last
   **2 weeks** matched on (recipient a/c, value date, currency, amount). *Implication:* duplicates
   older than two weeks, or arriving concurrently, are re-credited. The SIP flow gets this right
   via `(transactionId, UETR)` — that is the model to copy.

4. **Leader election *is* the concurrency model.** All three Kafka containers are
   `autoStartup=false` and started/stopped only by `KafkaLeaderElectionListener`; every S3 file is
   dropped on non-leaders by `LeaderOnlyFilter`. *Implication:* horizontal scaling is impossible by
   design, `mantis.leaderelection.enabled=false` in a multi-node environment would cause duplicate
   processing, and any new consumer or poller must be added to the leadership lifecycle or it will
   run on both blue and green.

5. **The MANUAL queue is the system's circuit-breaker fallback.** Every downstream failure — Hystrix
   trip, ledger reject, validation error — converges on `status = MANUAL` with a recorded reason.
   *Implication:* the system is fail-safe rather than fail-fast; a downstream outage manifests as a
   growing human work queue, not as lost deposits or errors. Manual-queue depth is the real health
   signal, and `AutoPostingsControlMBean` exists so operators can force everything down this path.

6. **Business rules live in YAML, not code.** Banned/high-risk country lists, per-bank automation and
   ignore lists, the manual-review role, deposit-limit and fast-payment bank mappings, and the global
   auto-approval switch are all configuration. *Implication:* reading the specifications alone tells
   you the *shape* of a rule, never its current effect — always read
   `resource/src/main/properties/common/application.yml` plus the environment overlay.

7. **Hystrix is silently in the path of every external call, with a 3-second budget.** Inherited from
   Spring Cloud Dalston; the only in-code trace is one `HystrixBadRequestException` catch.
   *Implication:* a downstream that is merely slow (>3s) is indistinguishable from one that is down,
   and both land the deposit in MANUAL. The 45s per-command override for bank account verification
   shows the team has already hit this.

8. **`@EnableAsync` with no `TaskExecutor` → `SimpleAsyncTaskExecutor`, unbounded threads**, and the
   one `@Async` method (`backupAndDeleteFile`) both swallows all exceptions and **races the processing
   loop that follows it**. *Implication:* during a backlog drain this creates one thread per file and
   can delete an S3 object while its requests are still being validated.

9. **`AutoPostingsControlService.isAutomationEnabled` is a non-`volatile` mutable field** toggled from
   the JMX thread and read from poller/Kafka threads; it is also per-JVM and lost on redeploy.
   *Implication:* the emergency kill switch may not be visible to the threads it is meant to stop,
   and must be flipped on both blue and green.

10. **The financial audit trail is implemented entirely in Oracle triggers** (`*_au` shadow tables +
    GoldenGate triggers, 16 migrations, 4 repeatable). *Implication:* invisible from Java, and every
    column addition must also touch the `_au` table and re-emit the trigger — the pattern to follow is
    `V119` / `V123`.

11. **JMX is the operational control plane and there is no scheduler.** No `@Scheduled` anywhere;
    batch re-drive, Flyway migrate/repair, the automation kill switch, S3 operations and fast-payment
    reconciliation are all `@ManagedOperation`s driven by `jmxterm`. *Implication:* recovery is a
    documented human runbook, not an automated loop.

12. **`gbpFxRates` is cached for 24 hours with no eviction**, and it feeds the deposit-limit
    specifications. *Implication:* limit decisions can use a day-old rate, and blue/green nodes can
    disagree on the same deposit.

13. **`@EqualsAndHashCode` on both sides of a bidirectional `@OneToOne`** →
    `StackOverflowError` on any `equals`/`hashCode` of `BankPostingRequestEntity` or
    `TransactionDetailsEntity`, plus forced initialisation of the `LAZY` back-reference. Latent only
    because collection operations happen on domain objects. *Implication:* never put these entities
    in a `Set`/`Map` or call `contains`/`removeAll` on a list of them.

14. **Authorization coverage is 4 annotations across ~28 controllers**, via a custom `@HasRole` +
    AspectJ aspect (bypassable by self-invocation), with no object-level ownership checks on
    account-scoped endpoints. *Implication:* same BOLA-shaped exposure as the payments-gateway
    remediation programme — cross-reference that work rather than re-analysing.

15. **Acceptance tests run against a real deployed container** with real Kafka/AMQ/Oracle/S3Mock as
    GitLab CI services, driven by Cucumber + Awaitility, and are organised **by business rule**
    (23 feature files ≈ the specification catalogue). *Implication:* the feature files are the most
    reliable specification of current behaviour; they also require manually pre-seeded
    `BANK_ACCOUNT_LE_MAPPING` rows, so a new bank account in a test needs a README INSERT too.

16. **EOL stack with a modern edge.** Java 8 / Spring Boot 1.5.9 / Spring Cloud Dalston / Kafka client
    0.11 / Tomcat 7, while the newest code (SICIP, BVNK, `openspec/`, `.claude/agents/`) is 2026-era.
    *Implication:* new work must stay inside Java 8 and Boot 1.5 idioms — no records, no
    `CompletableFuture`-based composition, no `@KafkaListener`, JUnit 5 only via the `spring-junit5`
    bridge.

---

## 21. Unknowns

- **Does the ledger deduplicate?** `ct-ledger`'s `LedgerReferenceFactory.newLedgerReference(type,
  accountId, 1)` mints a fresh reference per call, which strongly suggests the ledger keys on that
  reference and therefore *cannot* recognise a retry. Confirming this in the `ct-ledger` /
  legacy-ledger service would settle whether findings #1–#3 are theoretical or live financial risk.
  **This is the single highest-value follow-up.**
- **Is the double-credit path observed in production?** Whether a reconciliation exists *outside*
  this repo (a finance-side break report against `com_ig_trade_v0_legacy_ledger_transaction`) is not
  determinable from the code. `FastPaymentReconciliationMBean` covers fast payments only.
- **`isApproveAllowed` semantics.** Computed by `BankPostingRequestUtil.isApproveAllowed` and gating
  every manual approval; the rule itself was not read in this pass. Worth reading before touching
  the manual flow.
- **Actual Hystrix behaviour per command.** Only the default (3s) and one override are in
  `common/application.yml`; per-environment overlays were not exhaustively diffed, and thread-pool
  sizes/circuit thresholds are all at Hystrix defaults, whose real-world effect depends on call volume.
- **Tomcat connector/thread pool and datasource pool sizing** live in the container's `context.xml`
  and the deployment layer, so the true concurrency ceiling of the HTTP surface is not visible here.
- **PII in logs.** `BankPostingRequestValidator` and `BankPostingRequestsProcessor` log whole domain
  objects; whether that leaks depends on the *domain* `BankPostingRequest.@ToString` exclusions,
  which were not verified. The entity is correctly masked.
- **Whether the two duplicated `BankAccountPort` / `CurrencyConversion` package pairs are both live**
  (two beans of similar type risk ambiguous injection) or one is dead code awaiting deletion.
- **Blue/green leadership handover semantics** — whether the `mantis` latch guarantees the old leader
  has fully drained before the new one starts consuming, or whether both can briefly be active.
  Determines whether finding #4's duplicate-processing window is real.
- **Kafka `AckMode.BATCH` failure semantics** with a listener that catches its own exceptions: the
  offset is committed for messages that were logged-and-dropped, so a poison message is permanently
  lost. Whether a DLQ exists at the platform level is not visible in this repo.

---

## Investigation Checklist
- [x] Module structure explored
- [x] Maven configuration analyzed (parent, BOMs, ~55 pinned versions, implicit Hystrix/Feign)
- [x] Spring version and tech determined (Boot 1.5.9, Cloud Dalston, MVC, Integration 4.3, Java 8)
- [x] Entry points identified (2 S3 pollers, 4 Kafka containers, 1 JMS listener, ~28 controllers, 8 MBeans)
- [x] Flows traced (file→ledger, manual approve/reject, SICIP two-phase, JMX re-drive)
- [x] State machines found — 9-state `Status` + 3-state `TransactionDetails`, all enforcement points mapped
- [x] Consistency mechanisms understood — effectively absent; documented with evidence
- [x] Persistence patterns mapped (Oracle/JNDI, 14 entities, EAGER OneToOne, trigger-based audit, stored proc)
- [x] External integrations documented (8 HTTP, 3 AMQ out + 1 in, 3 Kafka in + 1 out, S3, Zookeeper)
- [x] Concurrency model understood — leader election, 5 named race risks
- [x] Security/observability reviewed (`@HasRole` aspect, SSO, golden signals, OTel, MDC/sip-trace-id)
- [x] Error handling analyzed (16 exceptions, `@ControllerAdvice`, MANUAL-queue-as-fallback)
- [x] Configuration understood (7 environments, build-time selection, rules-in-YAML)
- [x] Tests analyzed (out-of-process Cucumber, make-it-easy, HSQLDB, WireMock, Awaitility)
- [x] Custom libraries identified (mantis, ct-ledger, enterprise-message-bus, SSO, common-log)
- [x] Historical patterns noted (11 items, incl. PK migration and the misleading schema comment)
- [x] Conventions documented

---

## Files Referenced

**Domain — services & orchestration**
- `domain/src/main/java/com/iggroup/wt/bank/postings/service/BankPostingRequestService.java`
- `domain/src/main/java/com/iggroup/wt/bank/postings/service/BankPostingRequestProcessor.java` ← approve/reject/manual + ledger
- `domain/src/main/java/com/iggroup/wt/bank/postings/service/BankPostingServiceImpl.java` ← manual queue, APPROVING/REJECTING
- `domain/src/main/java/com/iggroup/wt/bank/postings/service/TransactionProcessingService.java`
- `domain/src/main/java/com/iggroup/wt/bank/postings/service/InstantPaymentServiceImpl.java` ← SICIP two-phase
- `domain/src/main/java/com/iggroup/wt/bank/postings/service/BankPostingRequestValidator.java`
- `domain/src/main/java/com/iggroup/wt/bank/postings/service/ValidationRequestBuilder.java`
- `domain/src/main/java/com/iggroup/wt/bank/postings/service/AutoPostingsControlService.java` ← non-volatile kill switch

**Domain — model & validation**
- `domain/src/main/java/com/iggroup/wt/bank/postings/domain/Status.java`
- `domain/src/main/java/com/iggroup/wt/bank/postings/domain/InstantPaymentTransactionStatus.java`
- `domain/src/main/java/com/iggroup/wt/bank/postings/validation/specification/{Specification,AndSpecification,CompositeSpecification,AutomatedFlowFlagSpecification}.java`
- `domain/src/main/java/com/iggroup/wt/bank/postings/validation/specification/sip/SipValidationChain.java`
- `domain/src/main/java/com/iggroup/wt/bank/postings/port/` (30 ports)

**Integration — pipeline**
- `integration/src/main/java/com/iggroup/wt/bank/postings/config/S3ObjectPoller.java`
- `integration/src/main/java/com/iggroup/wt/bank/postings/jms/LeaderOnlyFilter.java`
- `integration/src/main/java/com/iggroup/wt/bank/postings/jms/BankCreditMessageManager.java`
- `integration/src/main/java/com/iggroup/wt/bank/postings/filemanager/{BankPostingRequestsProcessor,BankFileDownloader,BankFilePostProcessor}.java`

**Integration — adapters & persistence**
- `integration/src/main/java/com/iggroup/wt/bank/postings/adapter/BankPostingRequestAdapter.java` ← dedup
- `integration/src/main/java/com/iggroup/wt/bank/postings/adapter/LedgerPostingAdapter.java` ← ledger reference minting
- `integration/src/main/java/com/iggroup/wt/bank/postings/adapter/CurrencyAdapter.java` ← cached FX
- `integration/src/main/java/com/iggroup/wt/bank/postings/jpa/entity/{BankPostingRequestEntity,TransactionDetailsEntity}.java`
- `integration/src/main/resources/db/migration/` (127 scripts; note `V2`, `V11`, `V13`, `V119`, `V123`, `R__*`)

**Integration — config & infra**
- `integration/src/main/java/com/iggroup/wt/bank/postings/BankPostingsApplication.java`
- `integration/src/main/java/com/iggroup/wt/bank/postings/config/{LeaderElectionConfiguration,KafkaLeaderElectionListener,AmqJmsConfiguration,LedgerJmsConfiguration,CacheConfiguration,RestClientConfiguration,AuthorisationAspect,HasRole}.java`
- `integration/src/main/java/com/iggroup/wt/bank/postings/config/kafka/{KafkaConfiguration,KafkaErrorHandler,SipDepositDecryptingDeserializer,SipDepositEncryptingSerializer}.java`
- `integration/src/main/java/com/iggroup/wt/bank/postings/listener/{SipDepositEventListener,AmlRiskScoreEventListener,FastPaymentsEventListener,SipEventListener,AmqEligibleClientListener,AmqDarkLightStateListener}.java`
- `integration/src/main/java/com/iggroup/wt/bank/postings/jmx/` (8 MBeans)
- `integration/src/main/java/com/iggroup/wt/bank/postings/exceptionmapper/ExceptionResponseEntityHandler.java`
- `integration/src/main/java/com/iggroup/wt/bank/postings/storedproc/ObfuscateSensitiveInformationStoredProcedure.java`

**Config, build, tests**
- `resource/src/main/properties/common/application.yml` ← business rules, Hystrix/Feign, poller, leader election
- `pom.xml` (root, 41k) · `.gitlab-ci.yml` · `CLAUDE.md` · `README.md`
- `component-tests/README.md` · `component-tests/src/test/resources/features/` (23 feature files)
- `mocks/db-initial-setup/schema.sql` · `terraform/acceptance/resources/oracle/000_schema.sql`
- `openspec/changes/add-stale-sicip-processing-filter/`
