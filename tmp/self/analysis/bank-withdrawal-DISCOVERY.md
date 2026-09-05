# Repository Discovery: bank-withdrawal

**Repo:** `/Users/rajat.chikkodikar/Desktop/My-files/Tasks/_Codes/payments/bank-withdrawal`
**Analysed:** 2026-09-05 | **HEAD:** `1867049f4` (master, tag `260904.023103.18670`, 2026-09-04)
**Scale:** 1833 Java files, 13 Maven modules, 4340 lines of Oracle PL/SQL, 1443 lines of Spring XML
**Sibling analyses:** `payments-gateway-DISCOVERY.md`, `bank-postings-DISCOVERY.md`

Evidence convention: **OBSERVED** = read in the code at the cited `file:line`. **INFERRED** = deduced,
stated as such. **UNKNOWN** = not determinable from this repo.

---

## 1. System Mental Model

**bank-withdrawal is the money-*out* service.** Where `bank-postings` ingests inbound bank credits and
`payments-gateway` fronts card/wallet rails, this service takes a client's request to move funds from
their IG trading account to their external bank account and drives it all the way to a payment
instruction a bank will act on.

It is the **oldest and largest** of the three modules examined so far, and the only one where a
**human approval workflow is the primary path**. Two fundamentally different journeys coexist in one
WAR:

1. **Manual review (the legacy path, ~2014 vintage).** Request lands → `SUBMITTED` queue → Credit
   Sign Off 1 → Credit Sign Off 2 → Bank File → Ready For Pre Auth → Ready For Auth → a regional
   **bank file** is generated and shipped. Movement between stages is driven by back-office operators
   in a UI, each transition role-gated, each request individually **locked** while a user works on it.
   The unit of work is a **payment run** — a per-region batch that operators walk forward together.
2. **Automated withdrawal (ABW/IBW, actively being built out 2025-2026).** Request lands → a 12-rule
   engine decides whether it is safe to automate → if yes, a `TMS_PAYMENT` row is written and either
   batched into a CSV for the treasury system (TMS) or published as a **direct bank payment** to
   Lloyds (LBG) or to Swiss SIC-IP (SICIP/SIP) over Kafka; if any rule or field validation fails, the
   request **silently falls back into the manual queue**.

Everything about the codebase is explained by that duality: the state machine has both a
`MANUAL_REVIEW_STAGES` set and an `AUTOMATED` terminal stage; there are two independent rule engines;
there are two persistence styles (stored procedures for the legacy tables, `JdbcTemplate`/JPA-ish
views for the new TMS tables); and the newest work carries feature flags in a database table while
the oldest behaviour is wired in Spring XML.

**Regions are first-class.** UK, Italy (×2 legal entities), Europe (×2), South Africa, Switzerland,
Singapore, Australia (×3), Dubai, Japan, US, China, New Zealand. Region determines the withdrawal
*type* rule chain, the bank file format, the payment run, and the customer-service email address.
Japan is so different it has its own Maven module (`impl-japanese`, 118 files).

---

## 2. Repository / Module Architecture

```
wt-bankwithdrawal (pom, com.iggroup.wt.bankwithdrawal, parent wt-maven-project:3.9.0)
├── schemas              0 java   — pacs.008.001.08.ch.02 + pacs.002.001.10.ch.02 XSDs (Swiss SIC-IP)
├── client-intf        101 java   — DTOs + service contracts published to consumers
├── impl              1373 java   — everything: domain, application services, adapters, rules, bank files
├── impl-japanese      118 java   — Japan-only ports/adapters/services/emails (separate module, not a package)
├── client              19 java   — REST/HTTP client for other services to call this one
├── feature-flag        21 java   — Togglz feature manager, 9 features, 8 custom activation strategies
├── resource             0 java   — per-environment properties + common.yaml (the real business config)
├── war                129 java   — controllers, exception handler, filters, and ALL Spring XML wiring
├── functional-tests    24 java   — Cucumber, out-of-process
├── acceptance-test     19 java
├── component-tests      6 java
├── contract-test       11 java   — Java 17 island
├── post-deployment-tests 12 java — Java 17 island
├── coverage             0 java   — aggregation-only module
└── db-health-check      0 java
```

**ARCHITECTURE DETECTED — layered hexagonal, with the layers named `eai`.**
Inside `impl/src/main/java/com/iggroup/wt/bankwithdrawal/`:

| Package | Role | Notes |
|-|-|-|
| `domain/**` | entities, value objects, repository *interfaces*, rule engines, state classes | 14 sub-packages: `bankwithdrawal`, `paymentrun`, `processstates`, `account`, `archive`, `payment`, `currencyconversion`, `surcharge`, `japanese`, … |
| `application/service/**` | use-case orchestration | `BankWithdrawalServiceImpl`, `PaymentRunServiceImpl`, `WithdrawalRequestUpdateServiceImpl`, `WithdrawalProcessStateFactory`, `RoleServiceImpl` |
| `service/**` | supporting domain services | `bankfile`, `batch`, `batching`, `ledger`, `validator`, `scheduler`, `automation`, `listener`, `publisher`, `transformer`, `email`, `metatrader`, `currency`, `country`, `aspects` |
| `eai/**` | **the adapter layer** — "Enterprise Application Integration" | `jdbc/sproc` (stored-proc objects), `dao`, `persistence` (JdbcTemplate + entity views), `http`, `jms`, `jmx`, `socket`, `tms`, `security` |
| `kafka/**` | Kafka listeners + publishers | `payment`, `sip`, `aml`, `error` |
| `adapters/**`, `feignclient/**`, `interceptor/**` | outbound HTTP (OpenFeign) | 15 Feign APIs |
| `configuration/**` | the Java-config half | `datasource`, `feign`, `scheduler`, `observability`, `amq`, `leaderelection`, `kafka`, `flyway` |

`domain` declares repository interfaces (`BankWithdrawalProcessRepository`,
`PaymentRunRepository`, `PaymentRunProcessLockRepository`, `ArchivedRequestRepository`, …) that
`eai/jdbc/repository/*JdbcRepository` implement — the ports/adapters inversion is real, not nominal.

**But one adapter reaches back into the domain's behaviour** (see §8): the persistence layer
constructs the domain's state object.

**Convention: no Spring Boot.** `war/src/main/webapp/WEB-INF/web.xml` is a servlet 2.5 descriptor with
a `DispatcherServlet` on `/*`, three `DelegatingFilterProxy` filters, plus separate `monitor` and
`swagger` dispatcher servlets. Bean wiring is **half XML, half annotation** — see §17.

---

## 3. Maven / Dependency / BOM Behaviour

Root `pom.xml` is **68 KB / ~1700 lines** — the single largest configuration artefact in the repo. It
carries every version as a property and every dependency in `<dependencyManagement>` (the pattern the
legacy `README.txt` prescribes: "New dependencies should be added to the parent pom.xml in the section
`<dependencyManagement>`").

**Version reality check — the README lies about Java.**
`README.md` claims "Java 17+". `pom.xml:20` says `<java.version>1.8</java.version>`, and
`maven.compiler.source/target` derive from it (`pom.xml:117`). Only two modules escape:

- `contract-test/pom.xml:17-18` → `java.version` 17
- `post-deployment-tests/pom.xml:18` → `maven.compiler.source` 17
- `feature-flag/pom.xml:16` → explicitly pins back to `8`

**So the production artefact is Java 8 bytecode.** Two test modules compile at 17. That mixed-target
build is a real trap for anyone reaching for `var`, records, or `List.of` in `impl`.

**Framework versions — a very wide spread:**

| Component | Version | Comment |
|-|-|-|
| Spring Framework | **4.1.6.RELEASE** | 2015. No Boot. `spring-beans-3.0.xsd` still referenced in `bankwithdrawal-domain.xml:5` |
| Spring Integration | 4.1.3 | |
| Spring Boot Actuator | 2.2.11.RELEASE | actuator *only*, bolted onto a Spring 4 context |
| Jackson (org.codehaus) | **1.9.11** | `jackson.version` — the pre-2.x package |
| Jackson (com.fasterxml) | 2.11.4 | `fasterxml-jackson.version` — **both live in the same WAR** |
| Oracle JDBC | 18.3.0.0.0 | |
| Hibernate Validator | 5.2.4 | javax.validation 1.1.0 |
| Lombok | 1.18.30 | |
| MapStruct | 1.5.5.Final | |
| OpenFeign | 12.0 | + `feign-okhttp` 11.10, okhttp 3.14.9 |
| Micrometer | 1.11.12 | + OTLP registry |
| OpenTelemetry | 1.26.0 | |
| Artemis (AMQ) | 2.13.0.redhat-00006 | |
| Fiorano JMS | 10.2.0.10544 | legacy broker, still wired |
| Zookeeper / Curator | 3.4.6 / 2.11.0 | leader election |
| Flyway | 9.8.1 | |
| Quartz | 2.2.1 | declared; `@Scheduled` is what's actually used |
| EhCache | 2.10.0 | |
| Mockito | **5.23.0** | Mockito 5 requires Java 11+ at runtime — tests must run on a newer JRE than the compile target |
| JUnit | 5.14.0 | alongside JUnit 4 runners still in use (`MockitoJUnitRunner` in `RoleServiceImplTest`) |
| Tomcat/catalina | 6.0.53 (provided) | but `ClientAbortException` from `org.apache.catalina.connector` is caught in the exception handler |

### **BOM / IMPLICIT BEHAVIOUR**

- **`<revision>SNAPSHOT</revision>`** + `flatten-maven-plugin` 1.7.3 — CI-friendly versioning; the
  release version is injected, so `mvn` locally always produces `SNAPSHOT`.
- **`skipITs=true` and `skip-failsafe=true` are the pom defaults** (`pom.xml`, properties block).
  Integration tests do not run unless CI explicitly flips them. See §16.
- **`jacoco.coverage.minimum=50`, `jacoco.haltOnFailure=false`** — coverage is measured, reported, and
  **cannot fail the build**.
- Both `clover-maven-plugin` 4.4.1 and `jacoco-maven-plugin` 0.8.14 are configured — a half-completed
  migration from Clover to JaCoCo.
- `ossindex-maven-enforcer-rules` + `extra-enforcer-rules` + a `.snyk` file → dependency vulnerability
  gating happens at build time.
- `verify-properties-plugin-java7` — an IG in-house plugin that validates the per-environment
  `.properties` files are complete. This is why a missing property fails the *build*, not startup.

---

## 4. Java / Spring Technology Usage

**Spring features in play:** XML bean definitions (1443 lines across 17 files), component scanning
(`bankwithdrawal-component-scan.xml`), `@Configuration` classes, AOP (`@Aspect`, 2 aspects),
`cache:annotation-driven` + EhCache, `@Transactional` with a `DataSourceTransactionManager`,
`@Scheduled` + `@EnableScheduling`, `ApplicationEvent`/`ApplicationListener` with a **custom
multicaster**, `@Profile`, JMX via `@ManagedResource`, Spring JDBC `StoredProcedure` objects, Spring
Kafka `MessageListenerContainer`, Spring JMS, `OncePerRequestFilter`, `@ControllerAdvice`.

**Java-8-era idioms throughout:** `Optional`, streams, `BiFunction` in the state factory,
`Comparator.comparingInt` for rule ordering, method references as factories (`SubmittedState::new`).
No `var`, no records, no `CompletableFuture` chains.

**Lombok is used selectively** — `@Slf4j` on newer classes, `@Getter`/`@Setter`/`@Builder` on DTOs and
entities; the old core domain classes (`BankWithdrawalProcess`, 297 lines) are hand-written getters and
setters. `lombok.config` exists at the root. You can date a class by whether it uses `@Slf4j` or a
hand-declared `private static final Logger LOGGER`.

**Two logging idioms coexist:** `LoggerFactory.getLogger(X.class)` named `LOGGER` (old) vs `@Slf4j`
`log` (new). Both use the structured `method=name key=value` convention consistently — that convention
is the single most reliable thing in this codebase and log-based debugging depends on it.

---

## 5. Architecture Detected

### Patterns present, with the class that proves it

| Pattern | Where | Notes |
|-|-|-|
| **State (GoF)** | `domain/processstates/*` — 14 classes implementing `WithdrawalProcessState` | Not an enum-with-switch. Each state is a class holding the aggregate + `RoleService`; unsupported transitions throw `UnsupportedOperationException` from interface `default` methods |
| **Template Method** | `domain/paymentrun/stages/AbstractPaymentRunStage.java:38` | `progressPaymentRunStage` is `final`; 5 hooks, 4 of them no-op by default |
| **Chain of Responsibility** | `domain/bankwithdrawal/rules/withdrawaltype/*` | Each rule holds `nextRule`; chains assembled in XML per region |
| **Strategy + registry** | `WithdrawalTypeRuleEngineFactory`, `PaymentRunBehaviorFactory`, `WithdrawalProcessStateFactory`, `BatchingServiceFactory` | All map-keyed lookups |
| **Rules engine (ordered, fail-fast)** | `domain/.../automatedwithdrawal/validation/RuleEngine.java` | 12 `ValidationRule` beans auto-collected by `List<ValidationRule>` injection and sorted by `getOrder()` |
| **Builder** | `*Builder` classes everywhere (`BankWithdrawalProcessBuilder`, `UpdateReasonDetailsBuilder`, `ArchivedRequestBuilder`, …) | Hand-written fluent builders predating Lombok `@Builder` |
| **Repository / Port-Adapter** | `domain/**Repository` interfaces ← `eai/jdbc/repository/*JdbcRepository` | |
| **Stored-procedure object** | 114 classes under `eai/jdbc/sproc` + `eai/dao` extending `org.springframework.jdbc.object.StoredProcedure` | One class per PL/SQL procedure |
| **Domain events** | `domain/events/{PaymentRunCompleted,WithdrawalRequestRejected}`, `events/BankWithdrawalRequestReceivedEvent` | Dispatched through the custom multicaster |
| **Decorator** | `TransactionalEventPublisher` wraps `ApplicationEventPublisher` | Defers publication to after-commit |
| **Lazy loading via Supplier** | `BankWithdrawalProcess.setBankWithdrawalRequestSupplier(...)` | The aggregate holds a `Supplier<BankWithdrawalRequest>` that the repository injects — hand-rolled lazy association without an ORM |

### What is *not* here
No CQRS, no saga/compensation framework, no event sourcing, no reactive stack, no Spring Boot
auto-configuration (so almost nothing is implicit — every bean is either scanned or declared).

---

## 6. Important Execution Flows

### Flow 1 — Client withdrawal request (the front door)

Entry: `POST /funds/withdrawal` (also `/funds/withdrawal/desktop`, `/mobiles`,
`/internal/withdrawfunds`, `/manualWithdrawFunds`) → `BankWithdrawalController` →
`FundsWithdrawalService` → `BankWithdrawalServiceImpl.addBankWithdrawalRequest`
(`application/service/BankWithdrawalServiceImpl.java:118`, `@Transactional`).

1. `checkPaymentServiceAvailability()` — global kill switch, via `PaymentStatusService`. Throws
   `PAYMENTS_UNAVAILABLE`.
2. `bankWithdrawalRequestService.createWithdrawalRequest(...)` — builds the aggregate; also resolves
   the **withdrawal type** through the region-keyed rule chain (§7) and the surcharge.
3. `validateBankWithdrawalRequest(...)` — runs **18 pre-validators then 1 post-validator**, order
   fixed in `war/src/main/resources/bankwithdrawal-domain.xml:93-130`. First failure wins; the
   exception carries a `WithdrawalValidationResult` enum which is the *entire* branching key for the
   rest of the method.
4. Branch on the result:
   - **Multi-currency case** — if `isMultiCurrencyWithdrawalAllowed(...)` and the failure was exactly
     `BANK_ACCOUNT_AND_BASE_CURRENCY_DIFFERENT`, call the **currency-conversion service over HTTP**,
     require `"COMPLETED"`, then proceed. *A validation failure is converted into a success path.*
   - `SUCCESS` → proceed.
   - `EXPIRED_CARD_NOT_VERIFIED` → proceed but stamp a manual note.
   - anything else → `handleBankWithdrawalValidationFailure(...)`: ~12-branch cascade that either
     emails customer service, emails the client, or maps to a `BankWithdrawalResult` with a
     region-specific minimum amount.
5. `initiateBankWithdrawalProcess(...)` (`:379`):
   a. **rate-limit acquire** — `withdrawalRateLimitAdapter.tryAcquire(accountId)` unless internal
      channel. Failure → `RECENTLY_WITHDRAWAL_FROM_OTHER_SOURCES`.
   b. **IG One reservation hold** — for `IGONE_WEBSITE_IDS` + valid product code, `createHold(...)`
      against the ABS service; failure → `UNABLE_TO_PROCESS`.
   c. `withdrawalStatusService.registerSuccessFullWithdrawalRequest(accountId, ledgerReference)` —
      writes to the **external Payments service cache**.
   d. `withdrawalRequestProcessor.processWithdrawalRequest(...)` — persist + ledger + route to
      automation or manual queue.
   e. `messageSender.sendWithdrawalInitiationEmailToClient(accountId)`.

**CONSISTENCY HAZARD (OBSERVED):** steps 4 (HTTP currency conversion), 5b (HTTP hold creation),
5c (HTTP cache write) and 5e (SMTP) all execute **inside** the `@Transactional` boundary opened at
`:118`. A single withdrawal therefore holds an Oracle connection across at least three synchronous
remote calls and an SMTP send. A rollback after 5c leaves the remote Payments cache marked as
"recently withdrawn" and, if 5b ran, an ABS hold on the client's balance with no local record.

### Flow 2 — Automated withdrawal decision (ABW/IBW)

`service/automation/AutomationService.process(request, process)` — `@Transactional`.

```
processInternal():
  resolve IG bank account (legalEntity, branch, segregated?, currency)  → bic6, bankName
  automationStage = FeatureFlagService.getTmsAutomationStage(accountId, legalEntity, bic6, amount)
  metrics.recordTotalRequest(commonTags)
  Phase 1: ruleEngine.execute(request)        → invalid ⇒ return false (manual review)
  Phase 2: tmsPaymentBuilder.build(...)       → FieldValidationException ⇒ return false
  Phase 3: if (!automationStage.isEnabled())  ⇒ metric only, no automation
           if (stage.shouldGoToManualReview())⇒ persist TMS_PAYMENT, queue manual
           else if (LBG enabled && Lloyds FAST payment):
                  lloydsPaymentValidator.validate(...)   → invalid ⇒ return false
                  updateIbwReference(request, txRef)
                  process → AUTOMATED / DIRECT_BANK_PAYMENT_INITIATED ; persist
                  lloydsBankPaymentEventPublisher.publishPaymentRequest(...)   ← Kafka
           else: persist TMS_PAYMENT ; process → AUTOMATED / READY_FOR_TMS
  catch (Throwable e) → log.warn, return false
process(): if processInternal() returned false → stage=SUBMITTED, status=SUBMITTED, persist
```

**Design note (OBSERVED, and it is the right call):** every failure mode — rule failure, field
validation failure, Lloyds validation failure, *any* `Throwable* — degrades to the manual review
queue. The automated path can never lose a request by erroring; it can only fail to automate it.

**Hazard (OBSERVED):** the Kafka publish at Phase 3 happens *inside* the `@Transactional` method. The
DB status is written before the publish, which is the correct order, but the publish is not
transactional — if the enclosing transaction later rolls back, a payment instruction has been sent to
Lloyds for a withdrawal the database will show as never initiated. Contrast `TransactionalEventPublisher`
(§11), which exists precisely to solve this for *internal* events but is not used here.

### Flow 3 — Manual review: one operator action

Entry: `POST /check-request | /amend-request | /reject-request | /reset/{id}` →
`WithdrawalRequestUpdateController` → `WithdrawalRequestUpdateServiceImpl`.

```
@Transactional(noRollbackFor = ProcessLockException.class)
@Lockable                                       ← custom annotation, not Spring's
checkRequest(WithdrawalUpdateDetails d):
    ── BankWithdrawalAspect.withdrawalRequestLockingAdvice intercepts ──
       load process, getWithdrawalRequestLock(processId, user)   ← must ALREADY exist, else throws
       try { proceed } finally { unlockWithdrawalRequest(lockId, processId) }
    ── advised method body ──
       process = repo.getWithdrawalProcessById(id)   ← repository sets currentState here
       process.check(details)                        ← delegates to the State object
       repo.add(process)                             ← upsert + history row
       return getCurrentBankWithdrawalProcess(id)
```

The State object performs the **role check** and mutates stage/status/reason/audit. E.g.
`SubmittedState.reject` (`domain/processstates/SubmittedState.java:32`) calls
`roleService.isAllowedToRejectAtSubmittedQueue(user)` then sets `COMPLETED`/`REJECTED`.

### Flow 4 — Payment run progression (operator walks the whole region forward)

Entry: `POST /process-credit-sign-off-one/{regionId}` … `/process-send-to-bank/{regionId}/{bankId}`,
`/reject-payment-run/{regionId}`, `/clear-payment-run/{regionId}` → `PaymentRunController` /
`PaymentRunWorkflowController` → `PaymentRunServiceImpl` (all methods `@Transactional`) →
`PaymentRunBehaviorFactory.getPaymentRunBehavior(stage)` → the `PaymentRunStage` for that stage →
`AbstractPaymentRunStage.progressPaymentRunStage` template:

```
1 loadCurrentPaymentRunDetails(regionId)      — payment run + all IN-PROGRESS processes
2 validateCurrentPaymentRun(...)              — abstract; role + four-eyes checks
3 updatePaymentRunStage(...)                  — advance the run (or jump to COMPLETED if all rejected)
4 updateWithdrawalRequests(...)               — abstract; advance each request's state
5 performStageSpecificOperations(run, bankId) — e.g. BankFileStage generates the file
```

`isSameUserProcessedPreviousOperation(paymentRun, user)` (`:96`) is the **four-eyes primitive**:
subclasses use it to refuse a second sign-off by the same operator.

### Flow 5 — Swiss SIC-IP (SIP) instant payment response — the newest subsystem

`kafka/sip/SipWithdrawalEventListener.onMessage` (a raw `MessageListener<String,String>`, not
`@KafkaListener`):

1. Read the `sipTraceId` header → `MDC` (so the whole downstream log line set is correlated).
2. `decryptor.decrypt(record.value())` — payload is **encrypted** (`kafka/payment/crypto/SipMessageDecryptor`).
3. `objectMapper.readValue(json, SipMessage.class)` — note: a **`new ObjectMapper()` per listener
   instance**, constructed in the constructor, not injected.
4. `Pacs002SipWithdrawalMessageService.process(sipMessage)`:
   - `xmlDocumentParser.parseBase64(payload, DocumentCHPacs002.class)` — JAXB against the
     `pacs.002.001.10.ch.02` XSD in the `schemas` module.
   - takes **`txStatuses.get(0)` only**; throws if the list is empty. (The Swiss scheme mandates
     exactly one — `SipFailureCode` code `207` is literally "Number of transactions must be equal to 1".)
   - `orgnlTxId` must start with `SIP_TX_ID_PREFIX`; the remainder is parsed as the
     `bankWithdrawalRequestId` (`Long.parseLong`). **The withdrawal ID is embedded in the scheme's
     transaction reference** — that is the correlation mechanism, there is no lookup table.
   - **Idempotency guard:** if the current process status is not `DIRECT_BANK_PAYMENT_INITIATED`, log
     and **return** (`Pacs002SipWithdrawalMessageService.java`, `resolveCurrentProcess` + status check).
     This is the one clean status-based idempotency check in the module.
   - map `TxSts`: `ACSC`→`DIRECT_BANK_PAYMENT_SUCCEEDED`, `RJCT`→`REJECTED`, `CANC`→`CANCELLED`;
     unknown → `log.warn` and **return without changing anything**.
   - write a process-history row, then:
     - success → `createBankLedger(...)` + `archiveRequest(...)`
     - failure → `createWithdrawalReversalLedger` + `createSurchargeReversalLedger` + persist +
       publish `WithdrawMultipleRejectedRequests` through `TransactionalEventPublisher`
5. Back in the listener: **`catch (Exception e) → log.error`**. Nothing rethrown.

**FAILURE MODE (OBSERVED):** `Pacs002SipWithdrawalMessageService` has **no `@Transactional`**, and the
listener swallows every exception. So a partial application is directly reachable: history row written,
then `createBankLedger` throws → the offset is committed anyway, the withdrawal is left showing
`DIRECT_BANK_PAYMENT_SUCCEEDED` in its history with **no ledger entry**, and the `!= DIRECT_BANK_PAYMENT_INITIATED`
guard means a replay of the same message will now be skipped. Reversal-ledger failures are even
quieter: `createWithdrawalReversalLedger` catches `LedgerException` and **returns `null`**, which is
then stored as the `cancelledLedgerReference`.

### Flow 6 — TMS batch generation (scheduled)

`service/scheduler/BatchGenerationScheduler` — three `@Scheduled` crons (BAT 14:15, PILOT 14:45,
FULL_AUTOMATION hourly 00:00-20:00, all Mon-Fri, from `common.yaml`). Each checks
`leadershipApplicationState.isLeader()` and returns early if not leader. Then
`BatchGenerationService.generateBatches(stage)` computes the file-name prefix from the feature flag
stage and **hands the work to a single-thread executor** (`tmsBatchGenerationExecutor`,
`Executors.newSingleThreadExecutor`, thread name `tms-batch-generator`).

`generateBatchesInternal` groups unbatched `TMS_PAYMENT` rows by `BatchKey` (BIC6 + payment format
type) and produces a CSV per key (`TmsCsvFileGenerator`), then `PostBatchProcessingService`.

**Two concurrency observations (OBSERVED):**
1. The leader check runs on the **scheduler** thread; the work runs on the **executor** thread. If
   leadership is lost between submission and execution, the batch still runs.
2. `Executors.newSingleThreadExecutor` has an **unbounded queue**. The FULL_AUTOMATION cron fires
   hourly; if one run exceeds an hour, runs pile up and execute back-to-back rather than being skipped.

### Flow 7 — GDPR client obfuscation

AMQ `com_ig_payments_v1_gdpr_client_eligible` → `AmqEligibleClientListener.onMessage` → JMS
`ObjectMessage` deserialised to `Eligible` → `ObfuscateSensitiveInformationStoredProcedure.obfuscateSensitiveData(accounts)`
(Oracle array parameter via `OracleArraySqlTypeValue`) → returns failed account list → publishes
`DeletionStatus` to `com_ig_payments_v1_gdpr_client_deletion_status`. Failures per-account are
reported, not thrown. `catch (JMSException) → log.error` only. Manual re-drive path:
`POST /obfuscate` on `ObfuscationFailedClientController`.

---

## 7. Domain / Payment Concepts

**`BankWithdrawalRequest`** — the client's ask: account, money (currency + amount), client bank
details, region, channel, withdrawal type, surcharge, ledger reference, FX details, IBW reference.
**`BankWithdrawalProcess`** — the workflow position: stage, status, payment run id, update-reason
details, audit pair, batch number/total, file name, lock holder, ledger references for
cancel/amend/surcharge-cancel, plus the current `WithdrawalProcessState` and a lazy `Supplier` back to
the request. One-to-one (`BANK_WITHDRAWAL_REQUEST ||--o| BANK_WITHDRAWAL_PROCESS`, `docs/db_schema.mmd:8`).
**`PaymentRun`** — per-region batch of processes walked through the stages together.
**`PaymentRunProcessLock`** — application-level pessimistic lock row (`WITHDRAWAL_REQUEST` or `PAYMENT_RUN`).
**`TmsPayment` / `TmsBatch`** — the automated path's payment instruction and its batch.
**`ArchivedRequest`** — point-in-time snapshot (balances, banned flag, broker code, bet dates) captured at completion.

### The withdrawal *type* rule chains — region-keyed Chain of Responsibility

Wired in `war/src/main/resources/bankwithdrawal-domain.xml:168-283`. `WithdrawalTypeRuleEngineFactory`
maps a **region name string** to a `List<WithdrawalTypeRuleEngine>`:

| Region key | Chain |
|-|-|
| `UK` | *two* engines: `ukLloydsWithdrawalTypeRuleEngine` then `ukRbsWithdrawalTypeRuleEngine` |
| ↳ Lloyds chain | FastPay → Chaps → EuroMoneyMover → InternationalMoneyMover |
| ↳ RBS chain | StandardRBS → UrgentRBS → InternationalRBS |
| `IGM Italy` | MultibankEuroMoneyMover → InternationalMoneyMover |
| `IGE Italy`, `IGM Europe`, `IGE Europe`, `Dubai` | the **UK Lloyds** FastPay chain (reused) |
| `South Africa` | MultiBankInternationalMoneyMover |
| `Switzerland` | BankTransfer |
| `Singapore` | SingaporeFastPay → SingaporeRtgs → (BT → Ach → Tt) |
| `Australia`, `IGAU Australia`, `IGAUSTRALIA CRYPTO` | AustraliaTypeRule |

**Two traps here (OBSERVED):**
1. The keys are **display strings** (`"IGM Italy"`, `"IGAUSTRALIA CRYPTO"`). `getWithdrawalTypeRuleEngine`
   returns `null` for an unmapped region with no error — a new region silently NPEs at the call site.
2. `SingaporeFastPayRule` has **no `<constructor-arg>` in XML** but does have
   `@Autowired public SingaporeFastPayRule(SingaporeRtgsRule nextRule)`. The chain past FastPay is
   assembled by **annotation-driven constructor injection into an XML-declared bean** — the XML reads
   as if `rtgsRule`/`btRule`/`achRule`/`ttRule` are orphans, and they are not. Do not "clean up"
   those bean definitions.
3. Thresholds are **hardcoded in the rules**, e.g. `SingaporeFastPayRule.MAX_AMOUNT = 200000` with
   `SGD`/`SG` literals.

### The automated-withdrawal rule catalogue — 12 rules, explicit order

`RuleEngine` injects `List<ValidationRule>` and sorts by `getOrder()`. Fail-fast (`execute`) is what
production uses; `executeAll` (collect-all) exists for the test endpoint.

| Order | Rule | Failure code | Threshold source |
|-|-|-|-|
| 1 | `OnOffPaymentRule` | `ONE_OFF_PAYMENT` | — |
| 2 | `BannedRule` | `BANNED_ACCOUNT` | — |
| 3 | `CountryRiskRule` | `HIGH_RISK_OR_BANNED_COUNTRY` | content DB (cached 1h) |
| 4 | `HighAmlUnverifiedBankRule` | `HIGH_RISK_UNVERIFIED_BANK` | AML score from Kafka |
| 5 | `NewBankDetailsRule` | `NEW_BANK_DETAILS_UNVERIFIED` | — |
| 6 | `NewClientUnverifiedFundingRule` | `NEW_CLIENT_UNVERIFIED_FUNDING` | card-payments service |
| 7 | `NotTradedRule` | `NOT_TRADED_HIGH_VALUE` | `common.yaml` `not-traded.threshold: 500` |
| 8 | `StatusCodeRule` | `INVALID_ACCOUNT_STATUS_CODE` | `common.yaml` allow-list (35 codes) + IGCH invalid list (29 codes) |
| 9 | `HighRiskHighValueRule` | `HIGH_RISK_HIGH_VALUE` | `common.yaml` `50000` |
| 10 | `HighAmlHighValueRule` | `HIGH_AML_HIGH_VALUE` | `common.yaml` `100000` |
| 11 | `HighValueRule` | `HIGH_VALUE` | `common.yaml` `250000` |
| **999** | `CumulativeWithdrawalLimitRule` | `CUMULATIVE_WITHDRAWAL_LIMIT_EXCEEDED` | **Togglz** `CUMULATIVE_WITHDRAWAL_CAP` params (`capAmount=250000`, `timePeriodHours=24`) |

The `999` is deliberate: the cumulative rule sums historical ABW + IBW withdrawals across **all the
client's accounts**, normalises to GBP, and adds the current request — the most expensive check, run last.
Its parameters live in the **database** (Togglz row), not in `common.yaml`.

### The 18 pre-validators + 1 post-validator

Order is the XML list order at `bankwithdrawal-domain.xml:93-130`:
`rateLimit → ira → igUsClientGrossDeposit → australiaMinAmount → igMarketsAmount → bankAccount →
clientAccountMandatoryField → southAfricaAccount → withdrawalAmount → restrictedAccount →
bannedAccount → metatrader → clientStatus → currencyMismatch → australianAccount → chinaUnionPayAmount →
usWithdrawAmount → tastyWithdrawal`, then post: `subsequentWithdrawalValidationRule`.

**The comment at `bankwithdrawal-domain.xml:126` is load-bearing:**
`<!-- subsequentWithdrawalValidationRule must always be at the end as its non-idempotent -->`.
It is accurate: `SubsequentWithdrawalValidationRule.validate` calls
`withdrawalStatusService.isSubsequentWithdrawalV2(accountId, ledgerReference)` which invokes
`paymentsApi.checkAndUpdateSubsequentWithdrawal(...)` — a remote **check-and-update**. Running the
validator twice, or reordering it before a validator that can throw, changes remote state.

---

## 8. State Machines / Workflows

### **STATE MACHINE DETECTED — `WithdrawalStage` × `WithdrawalStatus`, realised as the State pattern**

Two enums, deliberately separate:

**`WithdrawalStage`** (`domain/paymentrun/WithdrawalStage.java`) — 9 values, dated
`Created by manoham on 01-10-2014`:
`RECEIVED` → `AUTOMATED` (terminal) | `SUBMITTED` → `FIRST_CREDIT_SIGNOFF` → `SECOND_CREDIT_SIGNOFF`
→ `BANK_FILE` → `READY_FOR_PRE_AUTH` → `READY_FOR_AUTH` → `COMPLETED` (terminal).
`MANUAL_REVIEW_STAGES` = everything except `RECEIVED` and `AUTOMATED`.

**`WithdrawalStatus`** — 17 values, partitioned into four *overlapping-by-design* sets plus three
disjoint buckets:

```
RECEIVED
  automated:  READY_FOR_TMS → SENT_TO_TMS (terminal)
              DIRECT_BANK_PAYMENT_INITIATED → DIRECT_BANK_PAYMENT_{SUCCEEDED,FAILED}
  manual:     SUBMITTED → READY_FIRST_CREDIT_SIGNOFF → READY_SECOND_CREDIT_SIGNOFF
              → READY_FOR_BANK_FILE → READY_FOR_UPLOAD → READY_FOR_PRE_AUTHORISE
              → READY_AUTHORISE → COMPLETED | REJECTED_AT_READY_FOR_AUTH
  terminal:   REJECTED | CANCELLED | COMPLETED | SENT_TO_TMS
```

### **CLASSLOAD-TIME INVARIANT — `validateStatusBuckets()`**

`WithdrawalStatus`'s static initialiser calls `validateStatusBuckets()`, which asserts every enum
constant appears in **exactly one** of `IN_PROGRESS_STATUSES` / `SUCCESS_STATUSES` / `FAILED_STATUSES`
and throws `IllegalStateException` otherwise. Because it runs in `<clinit>`, adding a status without
bucketing it produces an `ExceptionInInitializerError` at **first touch of the enum**, i.e. context
startup — not a subtle downstream bug. This is the single best piece of defensive design in the module
and should be preserved.

The buckets drive the public API contract: `mapToBankWithdrawalStatusDTO(rawStatus)` collapses 17
internal statuses into 3 external ones (`COMPLETED` / `REJECTED` / `IN_PROGRESS`) and **defaults an
unparseable status to `IN_PROGRESS`** — a stuck withdrawal reads as "in progress" to consumers forever.

### The State classes and the transition table

`WithdrawalProcessState` (`domain/processstates/WithdrawalProcessState.java`) declares 8 operations,
**all `default`-throwing `UnsupportedOperationException`**: `amend`, `check`, `reject`,
`validateReset`, `completeReject`, `completeAmend`, `completeCheck`, `gotoReadyForBankFile`,
`gotoReadyForSecondCreditSignOff`. A state therefore only needs to override what it permits — the
"illegal transition" behaviour is inherited, not written 14 times.

`WithdrawalProcessStateFactory` keys on the triple **(stage, status, updateAction)** — the third
element is what lets a request in the *same* stage+status behave differently depending on the pending
operator action:

| stage | status | action | state class |
|-|-|-|-|
| SUBMITTED | SUBMITTED | DEFAULT / CHECK | `SubmittedState` |
| FIRST_CREDIT_SIGNOFF | READY_FIRST_CREDIT_SIGNOFF | DEFAULT | `ReadyForCreditSignOffOne` |
| FIRST_CREDIT_SIGNOFF | READY_FIRST_CREDIT_SIGNOFF | CHECK | `CheckedAtCreditSignOffOne` |
| FIRST_CREDIT_SIGNOFF | READY_FIRST_CREDIT_SIGNOFF | AMEND | `AmendedAtCreditSignOffOne` |
| FIRST_CREDIT_SIGNOFF | REJECTED | REJECT | `RejectedAtCreditSignOffOne` |
| SECOND_CREDIT_SIGNOFF | READY_SECOND_CREDIT_SIGNOFF | DEFAULT / CHECK / AMEND | `ReadyForCreditSignOffTwo` / `CheckedAtCreditSignOffTwo` / `AmendedAtCreditSignOffTwo` |
| SECOND_CREDIT_SIGNOFF | REJECTED | REJECT | `RejectedAtCreditSignOffTwo` |
| BANK_FILE | READY_FOR_UPLOAD | DEFAULT | `ReadyForUpload` |
| BANK_FILE | READY_FOR_BANK_FILE | DEFAULT | `ReadyForBankFile` |
| AUTOMATED | READY_FOR_TMS | DEFAULT | `ReadyForTmsState` |

**13 entries for 14 state classes.** `BankFileState` implements `WithdrawalProcessState` but has no
entry in the factory map — it is constructed elsewhere or is dead. An unmapped triple throws
`IllegalStateException("Unable to find the current state of the withdrawal process %d with criteria %s")`,
so the failure is loud (good), but it means **`READY_FOR_PRE_AUTHORISE` and `READY_AUTHORISE` have no
state class at all** — those stages are driven exclusively by the payment-run `PaymentRunStage`
classes, not by per-request state objects.

### **LAYERING VIOLATION — the persistence adapter constructs the domain's state**

`eai/jdbc/repository/BankWithdrawalProcessJdbcRepository.java:73`:

```java
BankWithdrawalProcess withdrawalProcess = getWithdrawalProcess.getWithdrawalProcessById(id);
final WithdrawalProcessState processState = withdrawalProcessStateFactory.createWithdrawalProcessState(withdrawalProcess);
withdrawalProcess.setCurrentState(processState);
```

The repository owns state rehydration. Consequences, all OBSERVED:

- Only `getWithdrawalProcessById` and `CreditSignOffStage`/`RejectionListenerForUpdatingRemainingRequests`
  (which call the factory directly) produce a state-bearing aggregate.
- `getSubmittedRequest(regionId)` (`:62`) and `getInProgressWithdrawalRequests(paymentRunId)` (`:89`)
  set only the lazy request `Supplier` and **leave `currentState` null**. Calling `process.check(...)`
  / `.reject(...)` / `.amend(...)` on an aggregate obtained from either method NPEs. `AbstractPaymentRunStage.loadCurrentPaymentRunDetails`
  uses `getInProgressWithdrawalRequests`, which is precisely why `CreditSignOffStage:69` has to call
  the factory itself before touching state.
- A domain object's behaviour is unavailable unless you loaded it through the one blessed method. Any
  new query method must remember to attach the state.

### Payment-run stage machine (the second, coarser state machine)

`PaymentRunBehaviorFactory` maps `WithdrawalStage` → `PaymentRunStage`: `SUBMITTED`→`SubmittedStage`,
`FIRST_CREDIT_SIGNOFF`→`FirstCreditSignOff`, `SECOND_CREDIT_SIGNOFF`→`SecondCreditSignOff`,
`BANK_FILE`→`BankFileStage`, `READY_FOR_PRE_AUTH`→`ReadyForPreAuth`, `READY_FOR_AUTH`→`ReadyForAuth`.

**BUG (OBSERVED) — `PaymentRunBehaviorFactory.java:40`:**

```java
if (paymentRunStage == null) {
   new PaymentRunException("Invalid Withdrawal stage " + withdrawalStage);   // constructed, never thrown
}
return paymentRunStage;                                                      // returns null
```

The exception is instantiated and discarded. An unmapped stage (`RECEIVED`, `AUTOMATED`, `COMPLETED`)
returns `null` and the caller NPEs instead of getting `PaymentRunException("Invalid Withdrawal stage …")`.
This is a one-word fix (`throw`) and worth doing.

Rollback exists as a first-class operation: `PaymentRunStage.rollbackPaymentRunStage` defaults to
`throw new PaymentRunException("Not Supported ")`, and `AbstractPaymentRunStage.rollbackPaymentRunStage`
runs the mirror-image template (validate → update requests → update run → stage-specific).

---

## 9. Transactions / Consistency / Idempotency

### **CONSISTENCY MECHANISM — real transactions, unlike `bank-postings`**

31 `@Transactional` annotations across `impl` (vs **one** in the whole of `bank-postings`). A
`DataSourceTransactionManager` is declared in `war/src/main/resources/bankwithdrawal-jdbc.xml`. This
module genuinely brackets its writes.

Distribution:

| Class | Count | Notable |
|-|-|-|
| `PaymentRunServiceImpl` | 10 | every operator operation |
| `WithdrawalRequestUpdateServiceImpl` | 7 | all `noRollbackFor = ProcessLockException` |
| `LloydsPaymentResponseService` | 3 | |
| `PaymentRunProcessLockServiceImpl` | 3 | 2 × `REQUIRES_NEW` |
| `BankWithdrawalServiceImpl` | 2 | wraps HTTP + SMTP (§6 Flow 1) |
| `WithdrawalRateLimitAdapter` | 2 | both `REQUIRES_NEW`, one `readOnly` |
| `AutomationService`, `BankFileServiceImpl`, `BankWithdrawalProcessJdbcRepository`, `FundsWithdrawalService`, `PaymentRunPresentationServiceImpl` | 1 each | |

**Three deliberate propagation choices, each with a stated reason:**

1. **`noRollbackFor = ProcessLockException`** on every `WithdrawalRequestUpdateServiceImpl` method.
   The lock is released in an aspect `finally` block *outside* the transaction; a lock-expiry failure
   must not undo a legitimate business write. Combined with the aspect ordering this means: business
   change commits, lock complaint surfaces to the operator.
2. **`REQUIRES_NEW` on `lockPaymentRunProcess` / `purgeLock`** — a lock row must survive the rollback
   of the work it was guarding, otherwise a failed payment run would silently release its own lock.
3. **`REQUIRES_NEW` on `WithdrawalRateLimitAdapter.tryAcquire`** — with the reason written in the code
   (`WithdrawalRateLimitAdapter.java:43`): *"the rate-limit record must persist even if the outer
   withdrawal transaction rolls back, so that failed attempts still count toward the cooldown window."*

**Where transactions are absent and it matters:**
- `Pacs002SipWithdrawalMessageService` — none. Multi-write SIP settlement (§6 Flow 5).
- `SipWithdrawalEventListener` — swallows all exceptions, so no broker-level retry either.
- `AmqEligibleClientListener` — none; GDPR obfuscation + status publish are independent.

### **IDEMPOTENCY DETECTED — four separate mechanisms, none shared**

**(1) Local rate-limit table — `withdrawal_rate_limit`** (`V39__Create_withdrawal_rate_limit_table.sql`):
one row per account, PK `account_id`, single column `last_withdrawal`. Window default 30 s
(`property.rateLimit.windowSeconds:30`), mutable at runtime through `WithdrawalRateLimitMbean`.

The acquire is a single Oracle `MERGE` (`WithdrawalRateLimitRepository.MERGE_RATE_LIMIT`):
```sql
MERGE INTO withdrawal_rate_limit wrl USING (SELECT :accountId FROM DUAL) src
  ON (wrl.account_id = src.account_id)
WHEN MATCHED THEN UPDATE SET wrl.last_withdrawal = SYSTIMESTAMP
     WHERE wrl.last_withdrawal < SYSTIMESTAMP - NUMTODSINTERVAL(:windowSeconds,'SECOND')
WHEN NOT MATCHED THEN INSERT (account_id, last_withdrawal) VALUES (src.account_id, SYSTIMESTAMP)
```
`rowsAffected > 0` ⇒ acquired. This is **atomic and correct**: the `WHERE` on the matched branch is
the compare-and-swap, and a concurrent insert raises `DataIntegrityViolationException`, which
`tryAcquire` catches and reports as *denied*. Good design.

Two caveats, both OBSERVED and both intentional per the code comments:
- **Fail-open.** Any other exception on read *or* write returns "not limited" / "acquired". A DB
  outage disables the guard rather than blocking all withdrawals.
- **Check-then-act split.** `RateLimitPreValidator` calls `isRateLimited` (a read) as validator #1;
  `initiateBankWithdrawalProcess` calls `tryAcquire` (the CAS) much later. The read is only a fast-path
  rejection; the CAS is the real gate, so the TOCTOU window is harmless — but the pre-validator will
  reject requests the CAS would have allowed and vice versa, producing two different error paths for
  the same condition. Internal channels bypass both (`ChannelUtils.internalChannel`).
- The table is **never pruned** — it accumulates one permanent row per account that has ever withdrawn.

**(2) Remote "subsequent withdrawal" check — owned by the Payments service.**
`WithdrawalStatusServiceImpl.isSubsequentWithdrawalV2` → `paymentsApi.checkAndUpdateSubsequentWithdrawal(accountId, ledgerReference)`,
compared against `REQUESTED_RECENTLY`. Note the method name: **check *and update***. There is also a
v1 (`withdrawalStatusClient.isSubsequentWithdrawal(accountId)`) still present and a separate
`registerSuccessFullWithdrawalRequest(accountId, ledgerReference)` write. So the authoritative
"has this client just withdrawn?" state lives in **another service's cache**, is written from two
places here, and is read through two different clients.

**(3) Status-guard idempotency in the SIP path** — `if (DIRECT_BANK_PAYMENT_INITIATED != currentProcess.getProcessStatus()) return;`
The only place a replay is explicitly reasoned about. Effective for duplicate pacs.002 deliveries;
ineffective if the first delivery half-applied (§6 Flow 5).

**(4) Upsert semantics at the persistence layer** — `UpsertBankWithdrawProcessRequest`,
`UpsertPaymentRunProcessLock`, `tmsPaymentDao.upsert`, `paymentRunRepository.upsert` all take an
in/out id parameter: null ⇒ insert, non-null ⇒ update. Re-running a step with the same aggregate
updates rather than duplicating — but the id is held in memory, so a retry that reconstructs the
aggregate from scratch inserts a second row.

### **The application-level lock table is the real concurrency control**

`PaymentRunProcessLock` rows in `BANK_WITHDRAWALS.BW_PROCESS_LOCK`, two kinds
(`LockedObjectType.WITHDRAWAL_REQUEST`, `PAYMENT_RUN`), driven by
`PaymentRunProcessLockServiceImpl` and enforced by `BankWithdrawalAspect` on the custom `@Lockable`
annotation.

**Acquisition is read-all-then-insert:**
```java
List<PaymentRunProcessLock> locks = getAllProcessLocks();                    // full table scan
processLockValidationService.validateForWithdrawalRequestLockCreation(ids, regionId, locks);
createProcessLock(ids, WITHDRAWAL_REQUEST, user);                            // then insert
```
`validateForPaymentLockCreation(regionId)` doesn't even receive the list — it re-reads. **No `@Version`,
no `SELECT … FOR UPDATE`, and no unique constraint on `(object_id, object_type)` visible in the
migrations** (the only `unique` hits in `db.migration/*.sql` are javadoc comments about primary keys).
Two operators clicking simultaneously can both pass validation and both insert a lock row for the same
withdrawal — INFERRED from the read-then-write shape plus the absent constraint; the PL/SQL
`BW_PROCESS_LOCK.UPSERT` body was not read line-by-line, so a constraint *inside* the package cannot
be ruled out. Worth checking before relying on the lock for a new operation.

Locks expire and are swept by `ProcessLockPurgeSchedulerJob` (`property.processLock.period = 5`
minutes, cron `0 0/1 * * * ?` — checked every minute, leader only).

### **SELF-INVOCATION DEFEATS `@Lockable` ON THE BULK OPERATIONS**

`WithdrawalRequestUpdateServiceImpl.checkMultipleRequest` / `amendMultipleRequest` /
`rejectMultipleRequest` are `@Transactional` but **not** `@Lockable`, and they call
`this.checkRequest(...)` in a loop. Because Spring AOP is proxy-based, the internal call bypasses
`BankWithdrawalAspect` entirely — so the per-request `@Lockable` advice on `checkRequest` **never runs
for bulk operations**. The bulk methods compensate with `unlockAllRequests(...)` in a `finally`,
which only works because the caller (UI) created the locks up-front via `POST /lock-withdrawal-request`.
The single-request path acquires-and-releases; the bulk path assumes-and-releases. Both are internally
consistent; the asymmetry is invisible from the method signatures.

### Consistency model summary

| Concern | Mechanism | Verdict |
|-|-|-|
| Local DB writes per operator action | `@Transactional` + upsert + history row | Sound |
| Local DB + external HTTP in one unit | none — HTTP inside the transaction | **Unsound**; no compensation |
| Local DB + Kafka publish | none for Lloyds/SIP outbound | **Unsound**; `TransactionalEventPublisher` exists but is used only for internal events |
| Duplicate submission | `withdrawal_rate_limit` MERGE (atomic, fail-open) + remote Payments cache | Sound but split-brain across two owners |
| Duplicate inbound settlement | status guard | Sound for whole-message replay, not partial |
| Concurrent operator edits | lock table, read-then-insert | Probably racy; see above |
| Cross-node duplication of scheduled work | Zookeeper leader election, checked in-method | Sound at submission, not for the duration |

---

## 10. Persistence / Caching

### Two datasources, two access styles

Per `README.md` and `configuration/datasource`: primary Oracle via JNDI
`ig/jdbc/datasource/bankwithdrawal`, plus a **content** schema via `ig/jdbc/datasource/bankwithdrawalcon`
(read-only account/banned-country/website-override data, `eai/dao/content`). `bankwithdrawal-external-jdbc.xml`
wires the second.

| Style | Where | Count |
|-|-|-|
| Spring `StoredProcedure` objects (one class per PL/SQL proc) | `eai/jdbc/sproc/**`, `eai/dao/**` | 114 classes |
| `JdbcTemplate` / `NamedParameterJdbcTemplate` | `eai/persistence/repository/**` (the newer TMS + rate-limit work) | part of 78 files touching JDBC |
| Entity classes (view-backed, not JPA-managed) | `eai/persistence/entity/{AuditableEntity,BankEntity,IgBankAccountView,TmsBatchEntity,TmsPaymentEntity}` | 5 |

The generational split is visible: legacy tables are reached only through PL/SQL packages; the
automated-withdrawal tables (`TMS_PAYMENT`, `TMS_BATCH`, `IG_BANK_ACCOUNT`, `withdrawal_rate_limit`)
are reached with plain SQL.

### **BUSINESS LOGIC IN THE DATABASE — 4340 lines of PL/SQL under Flyway**

`impl/src/main/resources/db.migration/` — 42 versioned + 14 repeatable migrations, Flyway 9.8.1,
driven by `configuration/flyway/FlywayConfiguration` + `service/flyway/FlywayMigrationService` and
manually triggerable through `FlywayMbean`.

Repeatable (`R__`) scripts are the interesting half — they *are* the PL/SQL packages:

| Script | Lines | Contains |
|-|-|-|
| `R__bw_bank_withdrawal_request_package.sql` | 698 | the request table's CRUD + queries |
| `R__bw_pending_request_package.sql` | 611 | the pending-queue query (has an "optimised" variant behind a feature flag) |
| `R__audit_triggers.sql` | 535 | **row-level audit triggers** |
| `R__bw_bank_withdrawal_archive_package.sql` | 485 | archival |
| `R__bw_payment_run_package.sql` | 453 | payment run lifecycle |
| `R__bw_bank_withdrawal_process_package.sql` | 412 | process lifecycle |
| `R__bw_active_request_account_package.sql` | 406 | |
| `R__tms_automation_package.sql` | 180 | automated-withdrawal queries |
| `R__bw_ig_bank_account_package.sql` | 155 | |
| `R__active_request_account_au.sql` | 145 | Australia-specific |
| `R__gg_triggers.sql`, `R__payment_request_gg_trigger.sql` | 88 + 20 | **GoldenGate replication triggers** |
| `R__payment_request_audit_trigger.sql` | 88 | |
| `R__create_tms_batch_function.sql` | 64 | |

**Implications (OBSERVED):**
- **Audit history is partly invisible from Java.** `R__audit_triggers.sql` writes audit rows on DML.
  Reading the Java repositories does not tell you what is audited.
- **GoldenGate triggers** mean rows here are replicated downstream; schema changes have consumers
  outside this repo.
- Because `R__` scripts are *repeatable*, editing one re-runs it on the next deploy — the package
  bodies are effectively deployed from source on every release. `V38__recomplile_bw_dependencies.sql`
  exists to force recompilation of dependent objects after such a change.
- **Feature flags are seeded and mutated by Flyway migrations**: `V9__create_togglz_tables.sql`,
  `V11__add_feature.sql`, `V22__add_new_feature_flag.sql`, `V32__add_direct_bank_payment_feature_flag.sql`
  (`LBG_PAY_TO_API` disabled by default), `V33__update_lbg_pay_to_api_feature_flag_strategy.sql`,
  `V35__add_cumulative_cap_feature_flag_strategy.sql`, `V41__add_sip_withdrawal_feature.sql`,
  `V42__update_sip_withdrawal_strategy.sql` (switches `SIP_WITHDRAWAL_ENABLED` to the
  `sip-account-allowlist` strategy with an empty allowlist). **A migration is a behaviour change.**
- Two migrations exist purely to fix production data: `V31__mark_testbc_as_rejected.sql` and
  `V34__mark_testbc_as_rejected.sql` (the same job, twice).
- `V36__update_igx_from_hsbc_to_scb.sql` — a bank switch (HSBC → Standard Chartered) done as a
  migration, matching `property.hsbc.enabled=false` in `prod/runtime.properties`.

### **CACHING — reference data is cached forever**

`war/src/main/resources/ehcache.xml`, EhCache 2.10 via `cache:annotation-driven` +
`EhCacheCacheManager` (`bankwithdrawal-domain.xml:133-140`, `shared="true"`).

**11 of 14 caches are `eternal="true"`** with no TTL and no TTI:
`getRegions`, `getOffice`, `getOfficesByLegalEntityId`, `getRegionById`, `getRegionsForOffice`,
`getPaymentTypes`, `getCurrencies`, `getAccountPresentation`, `getProducts`, `getRegionBankDetail`,
`getCountries`, plus `defaultCache`. Eviction is LFU at 500 or 1000 entries only.

**Consequence (OBSERVED):** regions, offices, payment types, currencies, products, **region-bank
details** and countries are read once and never refreshed. Changing a region's bank in the database
does not take effect until the Tomcat instance restarts — which is exactly why
`RegionBankDetailsOperationsMBean` and `BankSwiftCodeOperationsMBean` exist (§13). `getAccountPresentation`
being eternal is worse: it is **per-account** data in an LFU cache of 1000 with no expiry.

Only three caches have a TTL, all 3600 s and all sourced from the content schema:
`getBackOfficeCountries`, `getBannedCountries`, `getWebsiteOverrides`. So banned-country changes
propagate within an hour; region-bank changes never do.

### Schema shape

`docs/db_schema.mmd` (558 lines) is a complete Mermaid ER diagram, and `docs/db_schema.pdf` its
render. Core clusters: withdrawal flow, bank/region structure, IG bank structure, account information,
process-type mappings, and a `PROJECT/DEPLOYMENT/DEPLOYED_ITEM/WORK_ITEM_STAGE` cluster (a deployment
tracker living in the same schema — likely shared/legacy, INFERRED).

---

## 11. External Integrations

This is the most integration-heavy of the three modules analysed.

### Outbound HTTP — 15 OpenFeign clients

`feignclient/`: `AccountMaintenanceApi`, `AccountValuationSummaryApi`, `BackOfficeFunctionsApi`,
`CardPaymentsApi`, `ClientMaintenanceApi`, `CryptoCashBalanceApi`, `CurrencyConversionApi`,
`ExternalLedgerServiceApi`, `FxRateApi`, `IgOneAccountSummaryApi`, `IgOneAzureTokenApi`,
`JwtServiceApi`, `PaymentsApi`, `TastyApi`, `WalletPaymentsApi`.
Config in `configuration/feign/{FeignConfig,JwtConfiguration,ProxyConfig}`; Feign over OkHttp.

Auth is injected by **interceptors**, not by the clients: `JwtTokenInjectorInterceptor`,
`XstTokenInjectorInterceptor`, plus per-API interceptors (`AccountBalanceSummaryApiInterceptor`,
`ExternalLedgerServiceApiInterceptor`, `IgOneBalanceSummaryApiInterceptor`). So an API's effective
credentials are not visible in its interface — check the interceptor list.

Legacy HTTP also survives: `uk.co.igindex.springrest` `RequestProxyImpl` for the SSO token service,
Apache HttpClient 4.4 pools, and `com.iggroup.wt.http.client` factories.

**Circuit breakers** are IG's own (`com.iggroup.wt.service.circuit.breaker.CircuitBreakerTemplate`),
declared as an `abstract` parent bean in `bankwithdrawal-security.xml:63` and inherited per client:
`exceptionThreshold` 10, `timeout` 3000 ms, and — importantly — `handledExceptions` is a **one-element
list containing only `ConnectTimeoutException`**. The breaker therefore opens on connect timeouts and
*not* on socket-read timeouts or 5xx responses. Token-service client: 20 connections, 2 s connect,
2 s pool timeout, **`retryCount 0`**.

### Non-HTTP outbound

- **RMI** to Back Office Services — `property.bos.bankWithdrawal.url` lists **27 RMI endpoints**
  (`bosi001-003` × ports 11501-11509) as a single comma-separated property. Plus Order Server
  (`osi001-005:10991-10995`, `order.server.version` 2.104.20).
- **Raw socket** — `eai/socket/clientbankwizard/*`: BankWizard sort-code/account validation over a
  socket on `property.bankwizard.port = 8555`, with `AccountNumberValidationType`.
- **SMTP** — `TomcatEmailSender` with `ContinuousConnectionStrategy` / `ReconnectConnectionStrategy`
  (two hand-rolled connection strategies), `mailhost:25`. Recipients are per-office
  (`OfficeCodeBasedCustomerServiceEmailAddresss` — note the typo'd class name, 3 s's — keyed
  `MEL`/`SGX`/`DEFAULT`/`ALL`).
- **MetaTrader** — `service/metatrader`, `mt4-client-cash-transfer` / `mt4-client-cash-balance` 1.0.2,
  `property.mt4.hostname = mt4adm`.
- **GoAnywhere** — managed file transfer for bank files; `property.goanywhere.bankfile.directory=/opt/projects/goanywhere_files/live/outbound`,
  per-stage filename prefixes (`FS-Payments-ukpayments-` for BAT/PILOT, `EXT-FIS-` for full automation).

### Message brokers — three of them

**Kafka (`cluster-peach`)** — publishers: `com_ig_payments_v1_payment--live`,
`com_ig_payments_v1_currency_conversion--live`, `com_ig_payments_v1_tasty_payment--live`.
Listeners (all `MessageListenerContainer`s, all `autoStartup` off until leadership):
`kafkaAMLRiskScoreEventListenerContainer`, `currencyConversionEventConsumerContainer`,
`tastyPaymentEventConsumerContainer`, `lloydsPaymentResponseEventConsumerContainer`,
`sipWithdrawalKafkaMessageListenerContainer`. Avro Schema Registry at
`schema-registry.iggroup.local:9090`, with `avro-serdes` and `data-pod-*` schema artefacts.
`kafka/error/DefaultKafkaListenerErrorHandler` is the shared error handler.

**ActiveMQ Artemis** — consumers: GDPR eligible-client (`banjo`), legacy ledger transaction (`mario`),
platform communication event (`mario`), account event (`kazooie`), AML risk score (`kazooie`).
Producer: GDPR deletion status (`banjo`). Wired in `bankwithdrawal-jms.amq.xml`.

**Fiorano JMS** — the legacy bus, still wired (`bankwithdrawal-jms.xml`, `fiorano-jndi.properties`
per environment, queue `AS.LEDGER_TRANS.TRANSACTION.1`).

### **DUAL LEDGER TRANSPORT BEHIND A FEATURE FLAG**

`war/src/main/resources/double-entry-ledger.xml` declares **two** `com.ig.ct.ledger.LedgerTransactionService`
beans — one over Fiorano, one over Artemis — and a `FeatureFlaggedLTS` that picks between them at
runtime from `featureFlagStatus`. The switch is `property.bankwithdrawal.doubleentryledger` (`true` in
prod) and `property.japanese.bankwithdrawal.doubleentryledger`, surfaced as
`DoubleEntryLedgerRouting` and as two JMX beans (`BankWithdrawalDoubleEntryLedgerFeatureFlag`,
`JapaneseBankWithdrawalDoubleEntryLedgerFeatureFlag`).

**Ledger references are host-derived:** `LedgerReferenceFactory` is constructed with
`#{hostnameSegments[0]}` and `#{systemProperties['catalina.instance']}`. Uniqueness of a ledger
reference depends on hostname + Tomcat instance name — the same pattern seen in `bank-postings`, and
the same implication: two instances with the same derived identity can mint colliding references.

### Spring Integration

`bankwithdrawal-springintegration.xml` is only 32 lines — unlike `bank-postings`, Spring Integration
is a bit-part here, not the file-pipeline backbone.

---

## 12. Concurrency / Threads

### **Leader election is Zookeeper-based and blue/green aware**

`configuration/leaderelection/`:
- `ZookeeperConfiguration` + Curator 2.11 / ZK 3.4.6, `LeaderElectionACLProvider` (digest ACL on every path).
- `LeadershipElectionInBlueGreenConfiguration` — `@Profile("!dev")`, uses IG's `mantis` library
  (`leader-election-core` 1.99.0): `ZookeeperLeaderElectionService`, `LeaderElectionOnBlueGreenClusterService`,
  `DarkLightClusterApplicationState`, `TreeCache` over `${ig.zookeeper.root.path}` (the b/g state
  ZNode, e.g. `/bgstate/tomcat/application/live`) and `${ig.zookeeper.leader.path}`.
- Election is started/stopped by `LeaderElectionContextRefreshedEventListener` /
  `LeaderElectionContextClosedEventListener`, each wrapping a `Runnable`.

**Two different enforcement styles, both present:**

1. **Container start/stop** (as in `bank-postings`): `CustomLeaderElectionListenerForKafka` starts all
   five Kafka listener containers `onTakeLeadership()` and stops them `onAbandonLeadership()`.
   `CustomLeaderElectionListenerForAmq` does the same for AMQ.
2. **In-method guard** (new here): `BatchGenerationScheduler` and `ProcessLockPurgeSchedulerJob` each
   call `leadershipApplicationState.isLeader()` at the top of the `@Scheduled` method.

Style 2 is only correct for the *instant* of the check. `BatchGenerationScheduler` then submits to an
executor, so the actual work is unguarded (§6 Flow 6). Style 1 is stronger — abandoning leadership
stops consumption.

**The important difference from `bank-postings`: HTTP is not leader-gated.** All 26 controllers serve
on every node. Only consumers and schedulers are single-leader. So this service *does* scale
horizontally for the request path, and the concurrency control for operator actions is the lock table
(§9), not leadership.

### Thread pools

| Pool | Where | Config |
|-|-|-|
| `ThreadPoolTaskScheduler` `scheduler-*` | `SchedulerConfig.taskScheduler()` | **poolSize 10**, `waitForTasksToCompleteOnShutdown=true`, `awaitTerminationSeconds=20` |
| `tmsBatchGenerationExecutor` `tms-batch-generator` | `SchedulerConfig` | `Executors.newSingleThreadExecutor`, **unbounded queue**, plain `Thread` factory (non-daemon, no uncaught-exception handler) |
| async event multicaster | `DistributiveEventMulticaster` (async half) | pool configured in `bankwithdrawal-event-handler.xml` |
| golden-signal reporter reset | `GoldenSignalsConfiguration` | `Executors.newSingleThreadScheduledExecutor` |
| Kafka listener containers | `KafkaConfiguration` | 5 containers |
| Tomcat request threads | container | |

Only 4 `@Scheduled` methods exist in the entire module — 3 batch-generation crons and the lock purge.
There is no `@Async`; asynchrony is achieved through the event multicaster and the batch executor.

### **CUSTOM EVENT MULTICASTER — sync/async routing by annotation**

`service/listener/DistributiveEventMulticaster` **replaces Spring's default
`ApplicationEventMulticaster`** (registered in `bankwithdrawal-event-handler.xml`). It holds two
delegate multicasters and routes each listener to one of them based on whether the listener class
carries the module's own `@AsyncListener` annotation — checked both by class
(`addApplicationListener`) and by bean name via `applicationContext.getType(...)`
(`addApplicationListenerBean`).

Two consequences worth knowing:
- **Whether a listener runs on the caller's thread — and therefore inside the caller's transaction —
  is decided by a single annotation on the listener class**, invisible from the publisher.
  `RejectionListenerForArchiving`, `RejectionListenerForEmail`,
  `RejectionListenerForPaymentRunCompletion`, `RejectionListenerForUpdatingRemainingRequests` and
  `PaymentRunCompletionListenerForArchive` are all reached this way; check each for `@AsyncListener`
  before assuming ordering.
- `hasAsyncAnnotation` swallows exceptions and defaults to **sync** (`catch (Exception e) { /* Ignore
  - default to sync is fine */ }`). A bean-type resolution failure silently changes threading.

Paired with `TransactionalEventPublisher` (`eai/jdbc/TransactionalEventPublisher`), which registers a
`TransactionSynchronizationAdapter.afterCommit` callback when a transaction is active and publishes
immediately otherwise. So a listener's actual timing is the product of *two* independent decisions:
after-commit vs immediate (publisher side) and async vs sync (listener side). Four combinations exist.

### Context propagation

- `TracingSupportFilter` (`OncePerRequestFilter`) reads the current OpenTelemetry `SpanContext`, puts
  `callerReqId` (traceId) and `reqId` (spanId) on the **request attributes** (not MDC), and echoes the
  traceId back as the `X-REQUEST-ID` response header.
- `SipWithdrawalEventListener` puts `SipConstants.SIP_TRACE_ID` into **MDC** and removes it in `finally`
  — the only explicit MDC management found.
- `WithdrawalUserProvider.setContext(...)` / `clearContext()` — a **ThreadLocal** carrying the
  `WithdrawalContext` (accountId, legalEntity, igBank, amount, region) that Togglz activation
  strategies read. Every `FeatureFlagService` method sets it and clears it in a `finally`. Correct as
  written, but it means **feature-flag evaluation is thread-context-dependent**: evaluating a flag on
  a thread where the context was not set (e.g. the batch executor, or an async listener) yields a
  different answer than on the request thread.

### Race conditions / concurrency risks (ranked)

1. **Lock-table acquisition** is read-then-insert with no observed unique constraint (§9).
2. **Batch generation** runs off-leader-check on an unbounded single-thread queue (§6 Flow 6).
3. **`new ObjectMapper()` per listener** — safe (thread-safe once configured), but a needless
   per-instance allocation and an inconsistency with the injected `ObjectMapper` used elsewhere.
4. **Non-daemon `tms-batch-generator` thread with no uncaught-exception handler** — an `Error` kills
   the thread silently and all subsequent batch generation stops until restart. INFERRED from
   `Executors.newSingleThreadExecutor` semantics (a new thread *is* created on the next submit, so the
   impact is limited to the in-flight task) — worth verifying if batch generation ever "just stops".
5. **`withdrawal_rate_limit` window is mutable at runtime via JMX** on a single node
   (`WithdrawalRateLimitMbean.setWindowSeconds`) — the `AtomicLong` is per-JVM, so nodes can disagree
   about the window.

---

## 13. Cross-Cutting / Security / Observability

### Security

**Authentication** — IG single-sign-on. `war/src/main/resources/bankwithdrawal-security.xml`:
`uk.co.igindex.singlesignon.filters.AuthenticationFilter` with app name `bankWithdrawal`, backed by
`TokenServiceClientImpl` → `RequestProxyImpl(${bankWithdrawal.sso.domain}, /singlesignon/token)` over
a circuit-broken HttpClient. Mapped in `web.xml` on `/*` via `DelegatingFilterProxy`.

Two settings matter:
- **`securityBypassedWhenInfrastructureFails = false`** — if the SSO service is down, requests are
  **rejected**, not let through. Correct, and worth knowing when the service looks "down".
- **`requestExclusionStrategy`** = `PathBasedRequestExclusionStrategy` over `${filter.exclude.uri}`:
  prod = `/monitor`; test/uat = `/monitor,/swagger,/swagger-html`. **Swagger is authenticated in prod
  but anonymous in test/UAT.**

`PrincipalPopulateFilter` (module-local) and `PrincipalFactory` build the `com.iggroup.wt.security.domain.Principal`
that controllers receive as a method argument.

### **AUTHORISATION — the policy is a class name in a property, and in prod it only logs**

`bankwithdrawal-security.xml:72-77`:
```xml
<bean id="principalFactory" class="uk.co.igindex.singlesignon.filters.PrincipalFactory">
    <constructor-arg ref="authorisationPolicy"/>
</bean>
<bean id="authorisationPolicy" class="com.iggroup.wt.bankwithdrawal.spring.SpringDynamicFactoryBean">
    <property name="targetClass" value="${bankWithdrawal.authorisation.policy}"/>
</bean>
```
and in **every** environment, including `resource/src/main/properties/prod/runtime.properties:2`:
```
bankWithdrawal.authorisation.policy = com.iggroup.wt.security.domain.LogAuthorisationPolicy
```

The authorisation policy is loaded reflectively from a config string, and the configured
implementation is named `Log…`. **INFERRED** (the class lives in the external `wt-singlesignon`
artefact and was not read): this policy *records* authorisation decisions rather than enforcing them.
If that inference holds, framework-level authorisation is advisory in production and **all real
authorisation in this service is the in-application `RoleService`**. This is the same shape as the
BOLA exposure tracked for `payments-gateway` and `bank-postings`; worth confirming against the
`wt-singlesignon` source before acting on it.

**The in-application authorisation that does run** — `RoleServiceImpl`, six roles from properties
(`prod/runtime.properties:65-70`):

| Property | Prod value | Checked by |
|-|-|-|
| `property.reject.submitted.role` | `ROLE_RG-HYDRA-BANKPAYMENTS-REJECTSUBMITTEDREQUEST` | `SubmittedState.reject` |
| `property.credit.queue.operations.role` | `…-CREDITSIGNOFF` | `ReadyForCreditSignOffOne/Two` (amend/check/reject) |
| `property.send.bankfile.role` | `…-SENDTOBANK` | `isAllowedOperationAtReadyForAuthorization` |
| `property.initiate.paymentrun.role` | `…-INITIATEPAYMENTRUN` | payment run initiation |
| `property.generate.bankfile.role` | `…-CREATEBANKFILE` | `isAllowedOperationsAtBankFileStage` |
| `property.multiple.operation.role` | `…-MULTIPLE-OPERATION` | `isAllowedMultipleOperations` |

Coverage is **narrow and state-scoped**: the checks live inside the State classes and the
`PaymentRunStage` validators, so they protect *workflow transitions*. Query, presentation, archive,
region-admin, feature-flag and batch-generation endpoints have **no role check** — only
authentication. Notably unprotected by role:
`GET /api/external/client/{clientId}/withdrawals` (any authenticated caller can read any client's
withdrawal history — a textbook object-level authorisation gap), `POST /obfuscate`,
`POST /generate-all/{automationStage}`, `POST /generate/{bic6}/{automationStage}`,
`PUT /features/{featureName}`.

**Dev-only authorisation bypass, correctly fenced** — `service/aspects/AuthorizationEnablerAspect`
advises `RoleServiceImpl.is*(..)` and returns `true` unconditionally **iff**
`property.shouldSkipAuthorization` is true **and** `property.bankwithdrawal.environment` equals `dev`.
The environment conjunct is what makes this safe; do not remove it.

**Locking can be globally disabled** — `BankWithdrawalAspect` reads
`property.locking.disabled:false` and, when true, skips lock acquisition entirely for both the
withdrawal-request and payment-run advice. A single property turns off all operator concurrency
control.

### **Runtime mutation surfaces**

**11 JMX MBeans** (`jmx/`, wired in `bankwithdrawal-jmx.xml`): `BankSwiftCodeOperationsMBean`,
`RegionBankDetailsOperationsMBean` (cache-refresh levers for the eternal caches),
`FlywayMbean` (run migrations on demand), `GoAnyWhereFeaturesMbean`,
`BankWithdrawalDoubleEntryLedgerFeatureFlag`, `JapaneseBankWithdrawalDoubleEntryLedgerFeatureFlag`,
`MultiCurrencyWithdrawalFeatureFlag`, `SipWithdrawalOperationsMBean`, `WithdrawalRateLimitMbean`,
`WithdrawalRequestInternalFailureMBean`, `WithdrawalRequestLedgerMBean`.
`eai/jmx/README.txt` contains the module's own advice: *"Look to use Spring's out the box config based
JMX support, rather than having to write your own MBean info etc."*

**`PUT /features/{featureName}`** (`feature-flag/.../TogglzApiController`) — mutates feature flags at
runtime: `enabled`, `strategyId`, and arbitrary strategy parameters, persisted through the Togglz
`FeatureManager` into the `TOGGLZ` table. `FeatureFlagValidationService.validate` checks the parameter
*values*, and the user is **logged** (`principal.getName()`), but there is **no role check**. Any
authenticated principal can enable `TMS_AUTOMATION`, widen `SIP_WITHDRAWAL_ENABLED`'s account
allowlist, or raise `CUMULATIVE_WITHDRAWAL_CAP.capAmount`. Given that these flags gate whether
withdrawals are auto-approved and how much can leave in 24 hours, this is the highest-leverage
unprotected endpoint in the module.

**Endpoints that look like they should not be in a production WAR:**
- `POST /test/rule-engine/validate` — `TestRuleEngineController`, carrying
  `// TODO ABW remove this once signed off`. Builds a synthetic `BankWithdrawalRequest` from a JSON
  body and runs the live automation rule engine against it. Read-only, but it is an oracle for the
  exact risk thresholds and status-code allow-lists.
- `POST /mock/publish` — `BankWithdrawalController:224`. Takes a `BankWithdrawalRequestDTO` and calls
  `paymentEventPublisher.publishMessage(...)` directly, i.e. **publishes an arbitrary caller-supplied
  payment event to the live Kafka payment topic**, with no validation, no persistence and no role check.
- `POST /lloyds-payment/{withdrawalRequestId}/resolve` — `LloydsPaymentOverrideController`, a manual
  override for stuck direct-bank payments.

### Observability

**Structured logging** — logback via `LogbackConfigListener` (`web.xml`), per-environment
`bankwithdrawal-logback.xml` in `resource/src/main/properties/{env}/`. Two custom converters,
`DeploymentEnvironmentConverter` and `ServiceModeConverter`, stamp environment and blue/green
("light/dark") state onto every line; `IGTelemetryClusterDetailsProvider` and `IGClusterDetails`
supply that state.

**Metrics** — Micrometer with an **OTLP registry** (`GoldenSignalsConfiguration.otlpMeterRegistry`,
`@Profile("!dev")`, `@Primary`) exporting to `${otel.exporter.otlp.endpoint}` every 15 s with resource
attributes `service.namespace=Payments`, `service.name=BankWithdrawal`, `deployment.environment`.
In `dev` a `LoggingMeterRegistry` is `@Primary` instead. Common tag `SERVICE_MODE` is re-evaluated
per-publish via `MeterFilter.replaceTagValues(... clusterDetailsProvider::getLightDarkState)` so
metrics follow a blue/green switch, and `ResetOnSwitchGoldenSignalReporterProvider` resets the
reporters on switch. `@PreDestroy` stops and closes the registry.

**Golden signals** — IG's `mantis` golden-signal library: a `GoldenSignalsFilter` (mapped in
`web.xml`) wrapped in a `UrlExclusionFilterDecorator`, plus a `TrafficReporterHandlerInterceptor`
`MappedInterceptor` at `@Order(1)` over `/**`. Saturation is process CPU load via
`OperatingSystemMXBean::getProcessCpuLoad` tagged `cpu_usage_ratio`.

**Domain metrics** — `observability/RequestMetricsService` is the automated-withdrawal funnel,
instrumented end to end with a consistent tag set (`CommonTags`: automation stage, legal entity,
IG bank BIC6, client bank country, currency, value range):
`application.withdrawal.requests.total`, `…automation.rule` (with `status` and `error.code`),
plus timers and counters for TMS validation, TMS payment persisted, manual-review queued,
direct-bank automated, fully automated, TMS feature disabled, and successful request time.
**This is the right way to observe the automation rollout** — the `error.code` tag maps 1:1 to the 12
`ValidationResultCode`s, so "why aren't withdrawals automating?" is a single query.

**Tracing** — OpenTelemetry 1.26 (agent-attached, INFERRED — no SDK bootstrap in the repo);
`TracingSupportFilter` bridges it into request attributes and the `X-REQUEST-ID` response header.

**Actuator** — Spring Boot Actuator 2.2.11 on a Spring 4 context, plus a dedicated `monitor`
DispatcherServlet at `/monitor/*` (the only path excluded from authentication in prod) and a
`db-health-check` module.

---

## 14. Errors / Failure / Resilience

### Exception hierarchy

Domain exceptions live next to their aggregate: `BankWithdrawalException`,
`WithdrawalRequestUpdateException`, `FundsWithdrawalException`, `ProcessLockException`,
`InvalidWithdrawalTypeException`, `ExternalServiceBadResponseException` (all in
`domain/bankwithdrawal/`), `PaymentRunException` (`domain/paymentrun/`), `AccountException`,
`LedgerException`, `SurchargeException`, `CurrencyException`, `BankWithdrawalValidationException`
(`service/validator/exception/`), `ObfuscateSensitiveInformationException`, `FieldValidationException`
(`eai/tms/exception/`).
Technical exceptions in `exception/`: `AccountNotFoundException`, `ClientNotFoundException`,
`CurrencyNotFoundException`, `DecryptionException`, `ExternalServiceException`, `Pacs002ParseException`,
`PaymentRunUnAuthorisedException`, `ServiceException`, `SipDecryptionException`,
`SipEncryptionException`, `SIPFailureException`, `SipPublishException`.
Error codes are enums: `BankWithdrawalErrorCodes`, `PaymentRunErrorCodes`, `WithdrawalValidationResult`,
`ValidationResultCode`, `SipFailureCode`.

**`SipFailureCode`** deserves a mention on its own: ~60 constants mapping Swiss SIC-IP reason codes
(`RR04`, `AG01`, `TM01`, `ED05`, and numeric `102`…`235`+) to human descriptions, with
`descriptionFor(code)` used to build the operator-visible note. It is the scheme's error dictionary,
transcribed. Anyone debugging a rejected Swiss payment starts here.

### `@ControllerAdvice` — `BankWithdrawalExceptionHandler`

Extends `ResponseEntityExceptionHandler`; ~15 typed handlers each returning a `RestErrorDTO`
(`errorCode` + `errorMessage`). Notable choices:
- Every handler logs at **`warn`**, including the catch-all — there is no `error`-level logging from
  the web layer, so alerting on ERROR misses all HTTP-surfaced failures.
- The catch-all `@ExceptionHandler(Exception.class)` returns **`ex.getMessage()` to the caller** as
  `errorMessage` with code `EXCEPTION_HANDLER`. Internal messages (and, for SQL exceptions, potentially
  schema details) are echoed to clients.
- `ClientAbortException` is imported and handled — a nod to long-running responses over flaky links.
- `getRootCauseMessage` + `containsIgnoreCase` are imported, i.e. **string-matching on root-cause
  messages** to classify errors somewhere in the handler. Fragile by construction.

### Failure modes and what actually happens

| Failure | Handling | Net effect |
|-|-|-|
| Payments service disabled | `checkPaymentServiceAvailability` throws `PAYMENTS_UNAVAILABLE` | Clean rejection; global kill switch |
| Any pre/post validator fails | `BankWithdrawalValidationException` → `WithdrawalValidationResult` → 12-branch response builder | Client sees a specific reason; may trigger a CS or client email |
| Currency conversion not `COMPLETED` | `throw new BankWithdrawalException("Currency conversion failed")` | Rolls back — **but the remote conversion may have happened** |
| IG One hold creation fails | `UNABLE_TO_PROCESS` | Clean rejection |
| Rate limit not acquired | `RECENTLY_WITHDRAWAL_FROM_OTHER_SOURCES` | Clean rejection |
| Rate-limit DB down | **fail-open** (documented) | Guard silently disabled |
| Automation rule fails / TMS field invalid / Lloyds fields invalid / any `Throwable` | `AutomationService` returns false | **Falls back to manual review** — never loses the request |
| Manual-review enqueue itself throws | `catch (Exception) → log.error` | Request left in `RECEIVED`; **stranded**, no retry |
| SIP pacs.002 unknown `TxSts` | `log.warn` + return | Withdrawal stays `DIRECT_BANK_PAYMENT_INITIATED` forever |
| SIP pacs.002 partial failure | no transaction, listener swallows | Inconsistent state, offset committed, replay blocked by the status guard |
| Reversal ledger creation fails | `catch (LedgerException) → log.warn; return null` | `cancelledLedgerReference` stored as **null** |
| SIP archive fails | `catch (Exception) → log.error` | Payment stands, archive row missing |
| GDPR obfuscation per-account failure | reported in `DeletionStatus.isDeleted=false` | Re-drive via `POST /obfuscate` |
| Kafka listener throws | `DefaultKafkaListenerErrorHandler` / per-listener catch | Mostly log-and-continue |
| Connect timeout to a dependency | IG circuit breaker (threshold 10, timeout 3 s) | Opens — **only** for `ConnectTimeoutException` |
| Read timeout / 5xx from a dependency | *not* in `handledExceptions` | Breaker never opens; retryCount is 0 |
| SSO infrastructure down | `securityBypassedWhenInfrastructureFails=false` | All requests rejected |
| Unmapped region | `WithdrawalTypeRuleEngineFactory` returns null | NPE |
| Unmapped payment-run stage | factory returns null (exception discarded) | NPE instead of `PaymentRunException` |
| State triple not in factory map | `IllegalStateException` with the criteria | Loud and diagnosable |
| New `WithdrawalStatus` not bucketed | `IllegalStateException` in `<clinit>` | Fails at startup |

### Recovery strategies

- **Operator re-drive** — `reset/{withdrawalProcessId}` restores the *previous* process state
  (`getPreviousProcessState`, i.e. history-driven undo), `rollbackPaymentRunStage` walks a payment run
  back, `clear-payment-run/{regionId}` abandons one.
- **JMX** — `WithdrawalRequestInternalFailureMBean`, `WithdrawalRequestLedgerMBean`,
  `SipWithdrawalOperationsMBean`, `FlywayMbean`.
- **HTTP admin** — `POST /obfuscate`, `POST /generate-all/{automationStage}`,
  `POST /generate/{bic6}/{automationStage}`, `POST /generate-csv/batch/{batchId}`,
  `POST /lloyds-payment/{id}/resolve`.
- **Data migrations** — `V31`/`V34__mark_testbc_as_rejected.sql` show that some recovery is done by
  shipping SQL.

---

## 15. Configuration / Infrastructure

### **CONFIGURATION IS A FOUR-LAYER STACK, AND TWO OF THE LAYERS DON'T KNOW ABOUT EACH OTHER**

`war/src/main/java/com/iggroup/wt/bankwithdrawal/config/AppConfig.java` declares **two independent
placeholder configurers**:

```java
// order 1 — legacy .properties
PropertyPlaceholderConfigurer:
    runtime.properties
    ${environment}.environment.properties     // LIVE | DEMO | TEST | UAT | DEV
    ${site}.site.properties                   // PROD1 | PROD2 | …
    kafka.properties
    setSearchSystemEnvironment(true)
    SYSTEM_PROPERTIES_MODE_OVERRIDE
    setIgnoreResourceNotFound(false)          // a missing file fails startup
    setIgnoreUnresolvablePlaceholders(true)   // an unknown ${key} is LEFT AS-IS

// order 2 — YAML
PropertySourcesPlaceholderConfigurer:
    common.yaml
    application-${environment}.yaml
    setIgnoreUnresolvablePlaceholders(false)  // an unknown ${key} FAILS startup
```

Behavioural consequences, all OBSERVED:

1. **`.properties` and YAML are resolved in two separate passes.** Pass 1 leaves anything it cannot
   resolve untouched; pass 2 then resolves YAML keys and **fails on anything still unresolved**. So a
   typo in a `.properties` placeholder surfaces as a confusing pass-2 startup failure, not as a
   missing-property error.
2. **`SYSTEM_PROPERTIES_MODE_OVERRIDE` + `searchSystemEnvironment(true)`** means any `-D` system
   property or environment variable **silently overrides every file-based property**. That is the
   operational lever for production flips (the legacy `README.txt` describes exactly this:
   *"The below will be switched automatically by the tomcat container as system properties are defined,
   thus allowing quick production flip."*) — and it means the files are not the last word.
3. **`YamlPropertiesFactoryBean` with an ordered resource array: later wins.** `application-${env}.yaml`
   overrides `common.yaml`. This is live: `common.yaml` sets `sip.ig-member-id: "088482"` while
   `prod/application-LIVE.yaml` sets `sip.ig-member-id: "08848"` (the git log confirms —
   `PYMEEM-1100: Update sip ig member id for prod`). **Reading `common.yaml` alone gives you the wrong
   SIC-IP member id for production.**
4. **`environment` and `site` become Spring profiles.** `ProfileAwareContextLoaderListener.customizeContext`
   appends both (lower-cased) to the active profiles, so `-Dspring.profiles.active=blue` + `environment=prod`
   + `site=prod1` yields `blue,prod,prod1`. This is what drives `@Profile("!dev")` on leader election
   and the OTLP registry, and it is why `dev` behaves structurally differently, not just numerically.

### **The business rules live in `common.yaml`, not in Java**

`resource/src/main/properties/common/common.yaml`:

```yaml
automated-withdrawal:
  high-value.threshold:          250000     # HighValueRule
  high-risk-high-value.threshold: 50000     # HighRiskHighValueRule
  high-aml-high-value.threshold: 100000     # HighAmlHighValueRule
  not-traded.threshold:             500     # NotTradedRule
  status-code.allowed:     "1,6,19,23,26,29,30,34,41,42,43,45,48,49,50,51,52,54,55,56,57,58,60,61,63,69,70,71,74,75,76,78,82,84,86"
  status-code.igch-invalid: "6,8,10,13,15,16,24,25,26,32,44,46,64,67,68,71,72,73,74,77,78,79,80,88,89,93,95,97,98"
  batch-generation:
    timestamp-format: "ddMMyy_HHmmssSSS"
    file-name-format: "{bic6}_CLIENT_{date_time}.csv"
    bat:             { batch-prefix: "TMS_BAT_",   goanywhere-prefix: "FS-Payments-ukpayments-", cron: "0 15 14 ? * MON-FRI" }
    pilot:           { batch-prefix: "TMS_PILOT_", goanywhere-prefix: "FS-Payments-ukpayments-", cron: "0 45 14 ? * MON-FRI" }
    full-automation: { batch-prefix: "",           goanywhere-prefix: "EXT-FIS-",                cron: "0 0 0-20 ? * MON-FRI" }
min-withdrawal-limit-by-product-code: { eucry: 10 }
min-withdrawal-limit.uk: { amount: 10, legal-entity-ids: "IGI,IGM,IGTI", site-ids: "" }
sip: { ig-member-id: "088482", six-member-id: "099200" }
```

**Reading the rule classes alone tells you nothing about current risk appetite.** `HighValueRule`,
`HighRiskHighValueRule`, `HighAmlHighValueRule`, `NotTradedRule` and `StatusCodeRule` are all
`@Value`-injected shells around these numbers. `CumulativeWithdrawalLimitRule` is worse — its cap and
window live in the **database** (Togglz `STRATEGY_PARAMS`), not here.

The `min-withdrawal-limit.uk` block carries an unusually good inline comment (CAMP-1117) explaining
that this service never held the old GBP 100 UK minimum, enforces only a GBP 0.01 global floor via
`WithdrawalAmountPreValidator`, and that the GBP 100 enforcement lives in the card/wallet services —
and that scoping is by legal entity because IG company classification alone does not identify UK
clients. Keep that comment.

Also in `common/`: `payment-mapping-config.json` (the automated-withdrawal payment mapping —
`domain/bankwithdrawal/rules/automatedwithdrawal/paymentmapping`).

### **Feature flags — Togglz in an Oracle table, with eight custom strategies**

Table `TOGGLZ` (`V9__create_togglz_tables.sql`); manager in
`feature-flag/.../config/TogglzFeatureManagerConfig`; context via the `WithdrawalUserProvider`
ThreadLocal; wired in `war/src/main/resources/bankwithdrawal-featureflag.xml`.

`WithdrawalFeatures` — 9 features, each with a `@DefaultActivationStrategy`:

| Feature | Strategy id | Parameters |
|-|-|-|
| `TMS_AUTOMATION_QA` | `tms-qa-composite` | accountIds, legalEntities, igBanks |
| `TMS_AUTOMATION_BAT` | `tms-stage-bank-only` | igBanks, minValues |
| `TMS_AUTOMATION_PILOT` | `tms-stage-bank-only` | igBanks, minValues |
| `TMS_AUTOMATION` | `tms-stage-bank-only` | igBanks, minValues |
| `OPTIMISED_GET_PENDING_WITHDRAWAL_SPROC` | `region-based` | regions |
| `LBG_PAY_TO_API` | `business-hours` | clientIds, maxAmount, startTime, endTime (`HH:mm`; blank = 24/7) |
| `CUMULATIVE_WITHDRAWAL_CAP` | `cumulative-cap` | capAmount=250000, timePeriodHours=24 |
| `WITHDRAWAL_RESERVATION_HOLD` | `withdrawal-reservation-hold` | accountIds, enabled=false, websiteIds |
| `SIP_WITHDRAWAL_ENABLED` | `sip-account-allowlist` | accountIds |

Strategy implementations: `TmsAutomationStageStrategy`, `TmsAutomationQaStrategy`,
`RegionActivationStrategy`, `ClientIdActivationStrategy`, `BusinessHoursActivationStrategy`,
`CumulativeCapActivationStrategy`, `WithdrawalReservationHoldStrategy`, `SipWithdrawalActivationStrategy`.

**Two behaviours worth internalising:**
1. **The `@DefaultActivationStrategy` annotations are only defaults for a *new* row.** Once a row
   exists in `TOGGLZ`, the DB wins — and Flyway migrations rewrite those rows (`V33`, `V35`, `V42`).
   The annotation's parameter values are therefore *not* the running configuration.
2. **`FeatureFlagService.getTmsAutomationStage` cascades highest-to-lowest**:
   `TMS_AUTOMATION` (full) → `TMS_AUTOMATION_PILOT` → `TMS_AUTOMATION_BAT` → `TMS_AUTOMATION_QA` →
   `NONE`. Enabling the broadest flag makes the narrower ones unreachable. Rollout is *not* additive
   staging; it is a priority ladder.

Older, coarser flags remain as plain properties: `property.bankwithdrawal.doubleentryledger`,
`property.japanese.bankwithdrawal.doubleentryledger`, `property.goanywhere.feature.flag`,
`property.bankwizard.feature.flag`, `property.hsbc.enabled`, `property.locking.disabled`,
`property.shouldSkipAuthorization`. **Three feature-flag mechanisms coexist**: properties, JMX beans,
and Togglz rows.

### Infrastructure

WAR on Tomcat (`catalina.version` 6.0.53 as a provided dep; `catalina.instance` system property used
for ledger references), Oracle via JNDI, Zookeeper for leadership and blue/green, Kafka
(`cluster-peach`) + Artemis (`banjo`/`mario`/`kazooie`) + Fiorano, GoAnywhere MFT for bank files,
27 RMI back-office endpoints, OTLP metrics collector. Build/CI: GitLab (`.gitlab-ci.yml`, 8 KB) —
Bamboo links in `README.md` are stale relative to that. Snyk for dependency scanning.
`.gitattributes` is **136 KB**, which strongly suggests Git-LFS or a very long generated
line-ending/binary manifest (UNKNOWN which).

Operational scripts at the root: `run_application.sh`, `run_application.bat`, `debug_application.bat`.

---

## 16. Testing Discoveries

**Nine distinct test layers.** Test code is spread across five `src/test` trees plus seven dedicated
modules, and they differ not in scope but in *what infrastructure they touch*.

| Layer | Where | Runner | What it actually exercises |
|-|-|-|-|
| A | `impl/src/test` (405 files), `impl-japanese`, `war`, `client`, `client-intf`, `feature-flag` | JUnit 4 `MockitoJUnitRunner` **mixed with** JUnit 5 (`junit-bom` 5.14.0, Mockito 5.23 `MockedStatic`) | Pure unit tests: mocks, no Spring context, no DB, no broker |
| B | `impl/src/test/.../ContentJdbcRepositoryIntegrationTest`, `GetAccountDetailsFromContentForAccountIntegrationTest` | `SpringJUnit4ClassRunner` + `@ContextConfiguration("classpath:jdbc-config.xml")` | **A live Oracle schema.** Asserts hardcoded dates (`2025-09-09`, `2025-09-08`) against account `"OXBG5"` |
| C | `component-tests` | Cucumber **1.2.2** (`info.cukes`) + JUnit 4 vintage, `ComponentTestRunner` | In-process Spring context, **Japanese impl only** (depends on `wt-bankwithdrawal-impl-japanese`) |
| D | `functional-tests` | Cucumber **1.1.8** + Codehaus **Cargo** deploying the real WAR to embedded **Tomcat 7** | Out-of-process HTTP against a locally deployed WAR + WireMock 1.56; real remote Oracle for the TEST/UAT profiles |
| E | `acceptance-test` | JUnit 5 `@Suite @IncludeEngines("cucumber")` + Cucumber-Spring + **Testcontainers** via `ig-acceptance-test-framework` | **Full containerised stack** — Oracle, Kafka, Artemis, Fiorano, Zookeeper, schema-registry, WireMock, and a Tomcat container running the actually-built `war/target/bankwithdrawal.war`. Genuine black-box, no VPN |
| F | `acceptance-test` (second mechanism, same module) | Declarative YAML scenario DSL | `application-test.yml` `acceptance.test.configs.test-cases.*` defines ~20 named HTTP scenarios as (url-path, method, request `.ftl`, response `.ftl`) tuples resolved against Freemarker templates |
| G | `contract-test` | JUnit 5 + a **home-grown** consumer-contract framework (`swagger-parser` + `openapi-diff-core`) — **not** Pact, not Spring Cloud Contract | `SpecDownloader` fetches each provider's live OpenAPI spec and `OpenApiCompare.fromSpecifications` diffs it against a committed baseline, scoped to the paths this service's Feign clients actually consume (`consumedPaths()` per test class) |
| H | `post-deployment-tests` (Java 17) | JUnit 5 + Failsafe, `SimpleHttpClient` | Real HTTP against an **already-deployed** environment (test/uat/demo/live-dark) with real operator credentials |
| I | `db-health-check` | **Node.js** (`db-health-check.mjs`, `oracledb` thick mode) — not Maven, not JUnit | Queries `ALL_OBJECTS` for `INVALID` triggers/packages/procedures/functions in the `BANK_WITHDRAWALS` schema against a real Oracle |

### **WHAT ACTUALLY GATES A MERGE: layer A and layer C. That is all.**

Root pom defaults: `skip-failsafe=true` (`pom.xml:119`), `skipITs=true` (`pom.xml:127`).
CI (`.gitlab-ci.yml`) runs the `build` job with `MAVEN_CLI_OPTS: "-s $MAVEN_SETTINGS_XML_NEW -Pjacoco -q"`
— **only `-Pjacoco`**, no `-DskipITs=false`, no `-Dskip-failsafe=false`, no other profile.

| Layer | Runs in CI? | Gates the merge? |
|-|-|-|
| A unit tests | yes, in `build` | **yes** |
| B real-Oracle `*IntegrationTest` in `impl` | **never** — `skip-failsafe` stays `true` | no (dead in the pipeline) |
| C `component-tests` | yes — profile `component_tests` is `activeByDefault=true` and binds to `integration-test` via **surefire** (not failsafe), including only `**/ComponentTestRunner.java` | **yes** |
| D `functional-tests` | **never** — activation requires a `functional_tests` system property that no CI job passes; `skipTests=true` by default | no |
| E/F `acceptance-test` | yes, job `acceptance-test` (stage `acceptance-cycle`) | no — `allow_failure: true` |
| G `contract-test` | yes, `-pl contract-test -am -Pcontract-test verify` | no — `allow_failure: true` |
| H `post-deployment-tests` | yes, in `test-critical-sign-off` / `uat-critical-sign-off` with `-Dgroups=critical-sign-off -Dfailsafe.excludedGroups=` | no — `allow_failure: true` |
| I `db-health-check` | yes, `test:db-sign-off` / `uat:db-sign-off` | no — `allow_failure: true` |
| Snyk dependency + code scan | yes | no — `SNYK_ALLOW_FAILURE: "true"` |
| `coverage-report` | yes | no — `allow_failure: true` |

**A green MR pipeline therefore proves only that unit tests and the Japanese component tests passed.**
Everything downstream is advisory. Note also a dead-config detail: the root failsafe block sets
`<skip>${skip-failsafe}</skip>` *and* hardcodes `<skipITs>false</skipITs>` in the same block
(`pom.xml:1598-1599`) — `<skip>` wins, so the inner `skipITs=false` never has an effect.

### **UNUSUAL TESTING TECHNIQUE 1 — a home-grown OpenAPI-diff contract framework**

`contract-test/.../BaseContractTest.java:37-71`. Instead of Pact, each `*ContractIT` names the paths
this service's Feign clients consume (e.g. `FundsTransferServiceContractIT`: `/withdrawal/tasty/validate`,
`/api/currencies/conversionRate`, `/api/currencyConversion/initiate`), the framework downloads the
provider's **live** OpenAPI spec at test time, and `openapi-diff-core` reports breaking changes scoped
to just those paths. It is a genuinely good idea — consumer-scoped, no broker, no pact files to
publish — and it runs `allow_failure: true`, so a provider can break this service's contract and the
pipeline stays green.

### **UNUSUAL TESTING TECHNIQUE 2 — Mockito mocks as XML-declared Spring singletons**

`impl/src/test/resources/rules-engine-test-config.xml:13-15,139-141`:
```xml
<bean class="org.mockito.Mockito" factory-method="mock">
   <constructor-arg value="…RepositoryClass" type="java.lang.Class"/>
</bean>
```
A Spring-4/XML-era trick: `Mockito.mock()` output injected as a genuine managed singleton, letting a
real Spring context be assembled with mocked repositories.

### **UNUSUAL TESTING TECHNIQUE 3 — a Kafka "wait for assignment" harness with the reasoning written down**

`acceptance-test/.../KafkaTestUtil.java` has `awaitConsumerGroupAssignedToTopic` and
`subscribeWithInitialAssignment` (a throwaway poll purely to force partition assignment) that exist
specifically to avoid the `auto.offset.reset=latest` race where publishing before assignment is
visible silently drops the message. The author documented the trap inline. Copy this pattern rather
than rediscovering it.

### **UNUSUAL TESTING TECHNIQUE 4 — a pre-baselined Oracle container image**

`acceptance-test/.../application-test.yml`, per its own comment: the Oracle testcontainer image
"pre-seeds `FLYWAY_METADATA` with a single BASELINE row at V35; Flyway treats V1-V35 as below-baseline
(skipped) and only runs `R__` + V>35" (`baseline-on-migrate: true`, `baseline-version: 38`). Container
startup avoids replaying 35 migrations. **Consequence:** the acceptance suite never exercises V1-V35,
so a defect in an early migration is invisible to it.

### Other test infrastructure

- **Static mocking for time freezing** — `feature-flag/.../BusinessHoursActivationStrategyTest.java:44`:
  `mockStatic(ZonedDateTime.class, CALLS_REAL_METHODS)`. **No PowerMock anywhere** (repo-wide grep
  confirms) — Mockito 5 inline mock maker only.
- **Reflection into privates** — `WithdrawalRequestJdbcRepositoryTest.java:43` and
  `ClientBankDetailsValidationServiceTest.java:48` both use `setAccessible(true)` to test private
  fields/methods directly.
- **`make-it-easy` Maker fixtures** (`com.natpryce`) in `functional-tests` and `component-tests` — the
  same test-data-builder DSL seen in `bank-postings`.
- **JAXB-generated bank-format fixtures** — `impl/pom.xml` `maven-jaxb2-plugin` executions `hypobank`
  and `hsbchkbank` generate classes from `Document.xsd`/`HSBCHK.xsd` at build time, so bank-file XML
  tests use strongly-typed fixtures rather than hand-built strings.
- **Custom HTML report generator** — `com.iggroup.wt.bankwithdrawal.pdt.ReportGenerator` is invoked
  directly with `java -cp …` in the CI script (not via a Maven plugin) to produce
  `test-sign-off-report.html` / `uat-sign-off-report.html`.

### Coverage — measured everywhere, enforced nowhere

- JaCoCo: `jacoco.coverage.minimum = 50` (INSTRUCTION/COVEREDRATIO at `PACKAGE` level),
  **`jacoco.haltOnFailure = false`** (`pom.xml:106-107, 1544-1565`). The gate cannot fail a build.
- **A second, stricter, dormant tool**: `impl/pom.xml:531-593` has an OpenClover `codeQuality` profile
  with `targetPercentage="75.0%"` and its own exclude list. It has **no `<activation>` block and is
  never passed via `-P`** in CI. Anyone grepping for "coverage threshold" finds the 75% first and
  concludes wrongly.
- The `coverage` module aggregates JaCoCo exec data from `impl`, `impl-japanese`, `feature-flag`,
  `client`, `client-intf` (`report-aggregate` + `merge`) into `coverage/target/site/jacoco-aggregate`,
  which is the `JACOCO_XML_PATH` the `coverage-report` job reads. Its exclude list deliberately
  **mirrors** the per-module excludes (DTOs, entities, Feign interfaces/interceptors, config classes,
  sproc wrappers, row mappers, exceptions, Kafka wiring) with a comment explaining that this stops the
  aggregate badge counting boilerplate the per-module check already ignores. That is a well-maintained,
  intentional strategy, not drift.

### CI pipeline shape

Includes org-level templates from the `continuous-delivery` project (`ci-pret.yml`,
`common-code-quality-steps.yml`) plus a GitGuardian secret-scanning component (`gitguardian@1.1.2`).
**The job bodies for `.build`, `.acceptance_test` and `.coverage_report` are not in this repo** — their
exact `mvn` invocations are UNKNOWN beyond what `MAVEN_CLI_OPTS` reveals.

Stages: `get-version → build → commit-cycle → tag → acceptance-cycle → test:{create-crf, validate-crf,
deploy-app, close-crf, critical-sign-off} → uat:* → demo:* → demo-and-live:* → live:*`.
The workflow rule restricts the pipeline to `merge_request_event` (never on tags).

Deployment is **blue/green** (`IS_BLUE_GREEN: true`) driven by CRF (Change Request Form) automation per
environment. `UAT_AUTOMATED_CRF`, `DEMO_AUTOMATED_CRF`, `LIVE_AUTOMATED_CRF` are all `false` — UAT,
Demo and Live promotion require manual approval; `DEMO_AND_LIVE_COMBINED_CRF: true` merges those two.

### Gaps and traps a newcomer will hit

1. **The real-Oracle `impl` integration tests are dead in CI** (`skip-failsafe` is always `true`).
   Running `mvn verify -Dskip-failsafe=false -DskipITs=false` locally without VPN/DB gives connection
   failures with no CI precedent to compare against.
2. **`functional-tests` looks alive and is not.** Cargo + Tomcat 7 + Cucumber 1.1.8, activated by a
   system property no job passes. It is a legacy layer superseded by `acceptance-test`. Don't invest
   in fixing it without checking whether it is meant to exist.
3. **Real IG hostnames and credential placeholders are baked into `functional-tests/pom.xml`** —
   literal `dealtst-pri.iggroup.local` / `dealuat-pri.iggroup.local` datasource strings and
   `{{insert_username_for_bank_withdrawal_app}}` tokens. VPN-only.
4. **`ContentJdbcRepositoryIntegrationTest` is a time bomb.** It asserts exact dates (`9/9/2025`,
   `8/9/2025`) against account `"OXBG5"` in a shared Oracle schema, and its `@Before` only wires the
   repository — **the fixture data is managed out of band**. Any reset or re-seed of that environment
   breaks the test with no code change.
5. **CONFIRMED TEST-FIXTURE DRIFT with a real coverage hole.**
   `impl/src/test/resources/rules-engine-test-config.xml:30-36` wires
   `withdrawalTypeRuleEngineFactory` with **7** region keys: `UK, Italy, South Africa, Switzerland,
   Singapore, Australia, IGAU Australia`. Production
   (`war/src/main/resources/bankwithdrawal-domain.xml:173-184`) has **12**: `UK, IGM Italy, IGE Italy,
   South Africa, Switzerland, Singapore, IGM Europe, IGE Europe, Australia, IGAU Australia, Dubai,
   IGAUSTRALIA CRYPTO`.
   The test config's plain `"Italy"` key **matches neither** production key, and there is **no Dubai
   entry at all** even though `dubaiWithdrawalTypeRuleEngine` exists in production
   (`bankwithdrawal-domain.xml:286`). So `WithdrawalTypeServiceImplTest` and
   `SingaporeWithdrawalTypeServiceTest` **do not exercise the Dubai route or the Italy/Europe legal-entity
   split at all** — a silent, concrete coverage gap caused by duplicated wiring, not a hypothetical one.
6. **`.snyk` excludes a crypto class from scanning** — `SipMessageDecryptor.java` is listed in
   `.snyk:1-4` with no documented reason. A security pass that trusts Snyk output misses that file
   entirely.
7. **`post-deployment-tests` credential system properties are named after a person** —
   `harish_operation_username` / `harish_operation_password`. Functionally fine; invisible to anyone
   grepping for "operator" or "admin".
8. **`acceptance-test` needs substantial local Docker** — eight containers, and the fixed network name
   `igg-acceptance-test_bank-withdrawal-network` implies a shared-network expectation.

---

## 17. Custom Libraries / Implicit Behaviour

### IG in-house libraries this module depends on

| Artefact | Role |
|-|-|
| `com.iggroup.wt.maven3:wt-maven-project:3.9.0` | parent POM: plugin versions, enforcer rules, deploy conventions |
| `uk.co.igindex.singlesignon` (`wt-singlesignon` 1.67.0) | `AuthenticationFilter`, `PrincipalFactory`, `TokenServiceClientImpl`, `SecureTokenManagerImpl`, and the pluggable **authorisation policy** |
| `com.iggroup.wt.security.domain` | `Principal`, `LogAuthorisationPolicy` |
| `com.iggroup.mantis.zookeeper.leadership.election` (`leader-election-core` 1.99.0) | `ZookeeperLeaderElectionService`, `LeadershipApplicationState`, `DarkLightClusterApplicationState`, `LeaderElectionOnBlueGreenClusterService` |
| `com.iggroup.mantis.goldensignal` (`metrics-goldensignal` 1.99.0) | golden-signals filter/interceptor/reporter, `SaturationProvider`, tag config |
| `com.iggroup.filters.clusterdetails` | `IGClusterDetails`, `ClusterDetailsProvider` (blue/green state) |
| `com.iggroup.wt.http.client` (1.18.0) | `HttpClientWithCircuitBreakerFactory`, `HttpClientParamsConfiguration` |
| `com.iggroup.wt.service.circuit.breaker` | `CircuitBreakerTemplate` |
| `com.ig.ct.ledger` | `LedgerTransactionService`, `LedgerReferenceFactory`, `JmsLedgerTransactionsSender`, `FeatureFlaggedLTS` |
| `uk.co.igindex.payments.client.cache` | `WithdrawalStatusClient` — the remote duplicate-withdrawal cache |
| `com.ig.payments.v1.*`, `com.ig.trade.v0.*`, `com.ig.account.v0.*`, `com.ig.client.v1.*` (`data-pod-*`, `messagedefinition`) | Avro/JMS message contracts |
| `wt-3genterprise` 9.62.0, `wt-statements` 3.19.0, `bos.client` 1.50.23, `order.server` 2.104.20, `wt-backofficefunctions`, `wt-taxwrapper`, `wt-product-offering`, `wt-featureflag` 2.0.37, `wt-clientmaintenance`, `wt-accountmaintenance`, `wt-payment`, `wt-ledger`, `user-content-service` | domain service clients |
| `com.iggroup.wt.bankwithdrawal.spring.SpringDynamicFactoryBean` | module-local: instantiates a bean from a class-name **property** |
| `make-it-easy`-style `*Maker` fixtures | see §16 |

### **IMPLICIT BEHAVIOUR — the things that will surprise you**

1. **XML-declared beans still get `@Autowired` constructor injection.** `SingaporeFastPayRule` is
   declared with no `<constructor-arg>` yet receives `SingaporeRtgsRule` by type. Because
   annotation-config is active, `AutowiredAnnotationBeanPostProcessor` completes XML bean definitions.
   Reading the XML alone under-reports the wiring; reading the constructors alone under-reports it too.
2. **List injection assembles the automation rule engine.** `RuleEngine(List<ValidationRule> rules)`
   picks up **every** `ValidationRule` bean in the context and sorts by `getOrder()`. Adding a
   `@Component ValidationRule` anywhere changes production risk policy with no XML edit and no
   registration step. Conversely, the pre-validator list is explicit XML — **the two rule engines have
   opposite registration models**.
3. **Spring's event multicaster is replaced.** Sync vs async is decided by `@AsyncListener` on the
   listener class (§12), and resolution failures default to sync.
4. **Events may fire after commit or immediately**, depending on whether a transaction is active when
   `TransactionalEventPublisher.publishEvent` is called.
5. **The authorisation policy is a reflective class-name lookup** (`SpringDynamicFactoryBean` +
   `${bankWithdrawal.authorisation.policy}`). Changing security posture is a property edit.
6. **`environment` and `site` are Spring profiles**, so `@Profile` conditions key off deployment
   coordinates.
7. **System properties override all file config** (`SYSTEM_PROPERTIES_MODE_OVERRIDE`).
8. **YAML resource order decides overrides** (`application-${env}.yaml` beats `common.yaml`).
9. **Togglz DB rows beat the `@DefaultActivationStrategy` annotations.**
10. **Repeatable Flyway scripts re-run on change**, so PL/SQL package bodies deploy from source.
11. **DB triggers write audit rows and drive GoldenGate replication** — invisible from Java.
12. **`WithdrawalStatus` self-validates at classload** and will fail startup if a status is unbucketed.
13. **The persistence layer attaches domain state** — an aggregate from the wrong query method has a
    null `currentState`.
14. **Feature-flag evaluation depends on a ThreadLocal** — off the request thread, the context may be
    empty and the answer different.
15. **Two Jackson generations in one classpath** (`org.codehaus.jackson` 1.9.11 and
    `com.fasterxml.jackson` 2.11.4). Which one serialises a given payload depends on the
    `HttpMessageConverter`/annotation lineage of that class. Mixing `@JsonProperty` imports is a real
    hazard here.
16. **Mockito 5 on a Java 8 target** — tests need a JDK 11+ runtime even though `impl` compiles to 8.

---

## 18. Legacy / Historical Discoveries

- **`WithdrawalStage` is stamped `Created by manoham on 01-10-2014`** — the manual-review state machine
  is ~12 years old and still the primary path.
- **Two withdrawal-type engines for the UK** (`ukLloydsWithdrawalTypeRuleEngine`,
  `ukRbsWithdrawalTypeRuleEngine`) preserve a bank migration that never finished: RBS chain
  (Standard/Urgent/International) alongside the Lloyds chain (FastPay/Chaps/Euro/International).
- **Fiorano JMS survives beside Artemis** with a runtime switch (`FeatureFlaggedLTS`) — a broker
  migration in progress.
- **HSBC → Standard Chartered** (`V36__update_igx_from_hsbc_to_scb.sql`, `property.hsbc.enabled=false`)
  with `application/service/hsbc/` still in the tree.
- **`jackson.version = 1.9.11`** — the Codehaus generation is still on the classpath.
- **Clover *and* JaCoCo** both configured.
- **Quartz declared, `@Scheduled` used** — a scheduler migration that left its dependency behind.
- **`swagger-html/` checked into `war/src/main/webapp`** — the whole Swagger UI 2.x distribution as
  source files, plus a RESTdoclet profile in `war/pom.xml` (per `README.txt`) that generates docs from
  javadoc. Two documentation mechanisms, both stale-prone.
- **`README.md` vs `README.txt`** — the `.md` is a modern, partly-inaccurate overview (Java 17 claim,
  Bamboo links, a "Process States" list that does not match either enum); the `.txt` is the original
  generated project skeleton doc and is the more accurate source on *configuration* mechanics.
- **`v1` and `v2` of the subsequent-withdrawal check both live** in `WithdrawalStatusServiceImpl`,
  against two different clients.
- **`/archive/{date}`, `/archive/v1/...`, `/archive/v2/...`** — three generations of the archive API
  served simultaneously.
- **`OfficeCodeBasedCustomerServiceEmailAddresss`** — three trailing s's; a typo frozen into a bean class.
- **`web.xml` is servlet 2.5** with no `<web-app>` metadata-complete, on a Tomcat 6 dependency.
- **`domain/bankwithdrawal/rules/automatedwithdrawal/validation/OnOffPaymentRule`** — the name is
  "one-off payment" (`ONE_OFF_PAYMENT`, "One off payment"), spelled `OnOff`. Do not read it as an
  on/off switch.
- **`web/controllers/automatedwithdrwal/`** — package name misspelled ("withdrwal"); contains
  `BannedCountryController`, `BatchGenerationController`, `CsvFileGenerationController`.
- **`war/src/main/java/.../web/controllers/japanese/migrated/`** — a `migrated` sub-package holding the
  newer `/api/japanese` controllers beside the older ones. Both are live.

---

## 19. Patterns & Conventions

### Conventions that hold across the codebase

- **Structured logging**: `log.info("method=doThing key={} key2={}", a, b)`, with `- start` / `- end`
  bracketing on significant operations. Universal and reliable; build log queries on it.
- **Builders for every aggregate**, named `aFoo()` / `anFoo()` static entry points
  (`BankWithdrawalProcessBuilder.aBankWithdrawalProcess()`, `UpdateReasonDetailsBuilder.anUpdateReasonDetails()`).
- **One `StoredProcedure` subclass per PL/SQL procedure**, with the proc name as a `PROC_NAME` constant
  (`"BANK_WITHDRAWALS.BW_PROCESS_LOCK.UPSERT"`) and `p_`-prefixed parameter-name constants; parameters
  declared in the constructor then `compile()`.
- **Repository interface in `domain`, implementation in `eai`**, suffixed `JdbcRepository`.
- **Enums carry a display `value`** plus a `getX(String)` reverse lookup that throws
  `IllegalArgumentException` on miss. The DB stores the *display* string (`"Ready for Credit Sign Off 1"`),
  not the enum name — so **renaming an enum constant is safe; changing its `value` is a data migration.**
- **Error codes are enums with `MessageFormat` patterns** (`ValidationResultCode`,
  `"Withdrawal amount exceeds high value threshold of {0}"`).
- 3-space indentation in older files, 4-space in some newer ones; `pom.xml` uses 3.

### Two validation models — know which one you are in

| | Pre/post validators | Automation rule engine |
|-|-|-|
| Interface | `WithdrawalRequestPreValidator` / `…PostValidator` | `ValidationRule` |
| Signals failure by | **throwing** `BankWithdrawalValidationException` | **returning** `ValidationResult.failure(code)` |
| Registration | explicit `<list>` in `bankwithdrawal-domain.xml` | `List<ValidationRule>` autowiring, sorted by `getOrder()` |
| Ordering | XML list order | `getOrder()` integer |
| On failure | client-facing rejection (or a converted success path) | **fall back to manual review** |
| Adding one | edit XML | just add a bean |

Mixing them up is the most likely way to break this module: a new `ValidationRule` silently changes
what gets auto-approved; a new pre-validator that throws will reject client requests outright.

### Architectural conventions for adding code

- New **operator transition** → add a `WithdrawalProcessState` class **and** its `(stage, status, action)`
  entry in `WithdrawalProcessStateFactory`, **and** a role method on `RoleService` if it needs gating.
- New **payment-run stage** → subclass `AbstractPaymentRunStage`, register in `PaymentRunBehaviorFactory`,
  add the `WithdrawalStage` value.
- New **`WithdrawalStatus`** → add it to exactly one of the three buckets or startup fails.
- New **region** → add a rule-engine chain and a `withdrawalTypeRuleEngineFactory` map entry keyed by
  the exact region display string, a bank-file writer, and a `BatchingService`.
- New **automation rule** → implement `ValidationRule`, pick an unused `getOrder()`, add a
  `ValidationResultCode`, and put the threshold in `common.yaml` (not in the class).
- New **feature flag** → add to `WithdrawalFeatures`, write an activation strategy if needed, **and
  ship a Flyway migration to seed the `TOGGLZ` row**.
- New **outbound HTTP** → a Feign interface in `feignclient/`, an interceptor for auth, a circuit
  breaker inheriting `parentCircuitBreakerTemplate`, and connection params in `runtime.properties`.
- New **query method on a process repository** → remember to attach the state and the request `Supplier`.

### Convention smells worth knowing

- `getPaymentRunBehavior` constructs an exception it never throws (§8) — a real bug.
- Factories return `null` for unknown keys (`WithdrawalTypeRuleEngineFactory`, `PaymentRunBehaviorFactory`)
  while `WithdrawalProcessStateFactory` throws. Inconsistent, and the throwing one is the good one.
- The catch-all `@ExceptionHandler` leaks `ex.getMessage()` to callers and logs at `warn`.
- `catch (Throwable)` in `AutomationService.processInternal`.
- The `@Transactional` boundary in `BankWithdrawalServiceImpl` spans HTTP and SMTP.
- Bulk operations lose their `@Lockable` advice to self-invocation (§9).
- Test-only Spring XML (`impl/src/test/resources/rules-engine-test-config.xml`) duplicates production
  wiring and has already drifted — see §16.

---

## 20. Important Discoveries (Ranked)

**1. The manual-review workflow is a genuine GoF State machine, and the persistence layer owns state
rehydration.** 14 state classes keyed on `(stage, status, updateAction)`; role checks live *inside* the
states; unsupported transitions throw from interface `default` methods. But `currentState` is attached
by `BankWithdrawalProcessJdbcRepository.getWithdrawalProcessById` only — aggregates loaded via
`getSubmittedRequest` or `getInProgressWithdrawalRequests` have a **null state** and NPE on any
transition. Any new query method must attach it. (§8)

**2. Every automated-withdrawal failure degrades to the manual queue — including `Throwable`.** This is
the module's core safety property and it is deliberate: `AutomationService.processInternal` returns
`false` on rule failure, TMS field validation failure, Lloyds validation failure, or any exception, and
`process()` then enqueues to `SUBMITTED`. The automated path cannot lose money; it can only fail to
automate. The one hole: if the *enqueue itself* throws, the `catch (Exception) → log.error` leaves the
request stranded in `RECEIVED` with no retry. (§6 Flow 2, §14)

**3. Risk appetite lives in `common.yaml` and the `TOGGLZ` table, not in the rule classes.** High value
250 000, high-risk high value 50 000, high-AML high value 100 000, not-traded 500, and two
status-code lists are `@Value`-injected into otherwise empty rule shells. The cumulative 24-hour cap
(250 000) is a **database row**. Reading `HighValueRule.java` tells you nothing about production
policy, and `application-LIVE.yaml` overrides `common.yaml` (proven by `sip.ig-member-id`
`088482` → `08848`). (§15)

**4. `PUT /features/{featureName}` mutates production risk controls with authentication but no
authorisation.** Any authenticated principal can enable `TMS_AUTOMATION` (auto-approve withdrawals),
extend `SIP_WITHDRAWAL_ENABLED`'s account allowlist, or raise `CUMULATIVE_WITHDRAWAL_CAP.capAmount`.
The change persists to the `TOGGLZ` table. The user is logged; the action is not gated. (§13)

**5. Framework authorisation appears to be log-only in production.**
`bankWithdrawal.authorisation.policy = com.iggroup.wt.security.domain.LogAuthorisationPolicy` in every
environment including prod, loaded reflectively via `SpringDynamicFactoryBean`. **INFERRED** from the
class name — the implementation lives in `wt-singlesignon` and was not read. If it holds, all real
authorisation is the six-role `RoleService`, which only guards *workflow transitions*: query,
presentation, archive, admin, batch-generation and feature-flag endpoints have none. Same shape as the
BOLA programme tracked for `payments-gateway` and `bank-postings`. Verify against `wt-singlesignon`
before acting. (§13)

**6. Two endpoints do not belong in a production WAR.** `POST /mock/publish`
(`BankWithdrawalController:224`) publishes a caller-supplied `BankWithdrawalRequestDTO` straight to the
live Kafka payment topic — no validation, no persistence, no role check. `POST /test/rule-engine/validate`
(`TestRuleEngineController`, carrying `// TODO ABW remove this once signed off`) runs the live automation
rule engine against synthetic input, which makes it an oracle for the exact risk thresholds. (§13)

**7. The Swiss SIC-IP settlement path has no transaction and swallows every exception.**
`Pacs002SipWithdrawalMessageService.process` writes a history row, then creates a bank ledger, then
archives — with no `@Transactional` — and `SipWithdrawalEventListener` does `catch (Exception) →
log.error`. A mid-sequence failure commits the Kafka offset, leaves `DIRECT_BANK_PAYMENT_SUCCEEDED` in
history with no ledger entry, and the `!= DIRECT_BANK_PAYMENT_INITIATED` idempotency guard then blocks
any replay. Reversal-ledger failures are stored as `null` references. (§6 Flow 5, §9, §14)

**8. Four independent duplicate-suppression mechanisms, with the authoritative one in another
service.** (a) local `withdrawal_rate_limit` MERGE — atomic, correct, **fail-open**, 30 s window
mutable per-node via JMX, table never pruned; (b) remote `paymentsApi.checkAndUpdateSubsequentWithdrawal`
— a *check-and-update* owned by the Payments service, which is why the XML comment says the post-validator
is non-idempotent and must run last; (c) the SIP status guard; (d) upsert-by-id at the persistence layer.
Nothing reconciles them. (§9)

**9. Transactions exist and are used thoughtfully — but they wrap remote calls.** 31 `@Transactional`
annotations with three deliberate propagation decisions, each with a stated reason
(`noRollbackFor = ProcessLockException`, `REQUIRES_NEW` for locks, `REQUIRES_NEW` for the rate limiter
so failed attempts still count). Yet `BankWithdrawalServiceImpl.addBankWithdrawalRequest` holds the
transaction across currency conversion, ABS hold creation, a remote cache write and an SMTP send; and
`AutomationService.process` publishes to Kafka inside its transaction. `TransactionalEventPublisher`
solves exactly this for *internal* events and is not used for outbound integration. (§9)

**10. `WithdrawalStatus` validates its own invariants at classload.** `validateStatusBuckets()` in the
static initialiser asserts every status is in exactly one of IN_PROGRESS/SUCCESS/FAILED and throws
`IllegalStateException` otherwise — so a half-added status fails context startup instead of quietly
mis-reporting. Best defensive design in the module; preserve it. Its counterpart is the public
`mapToBankWithdrawalStatusDTO`, which defaults an *unparseable* status to `IN_PROGRESS`. (§8)

**11. Reference data is cached forever.** 11 of 14 EhCache caches are `eternal="true"` with no TTL —
including `getRegionBankDetail`, `getProducts`, `getCurrencies`, `getCountries` and the per-account
`getAccountPresentation`. Changing a region's bank in the database has **no effect until restart**,
which is precisely why `RegionBankDetailsOperationsMBean` and `BankSwiftCodeOperationsMBean` exist.
Only the three content-schema caches (banned countries, back-office countries, website overrides) have
a 1-hour TTL. (§10)

**12. 4340 lines of PL/SQL, deployed by Flyway, are part of the application.** 14 repeatable `R__`
package scripts (largest: 698 lines for the request package, 611 for the pending-request query),
535 lines of audit triggers, and GoldenGate replication triggers. Because `R__` scripts re-run on
change, package bodies ship from source every release; `V38__recomplile_bw_dependencies.sql` exists to
force dependent recompilation. Audit history and downstream replication are invisible from Java. (§10)

**13. Feature flags are seeded and rewritten by Flyway migrations — a migration is a behaviour change.**
`V32` inserts `LBG_PAY_TO_API` disabled, `V33` changes its strategy, `V35` adds the cumulative-cap
strategy, `V41`/`V42` add and then re-strategise `SIP_WITHDRAWAL_ENABLED` to an empty account
allowlist. The `@DefaultActivationStrategy` annotations only apply to a row that does not yet exist.
And `getTmsAutomationStage` is a **priority ladder**, not additive staging: enabling `TMS_AUTOMATION`
makes PILOT/BAT/QA unreachable. (§15)

**14. Leader election guards consumers and schedulers but not HTTP — and the batch guard is
submission-only.** Kafka and AMQ containers are started/stopped by leadership listeners (strong);
`@Scheduled` methods call `isLeader()` in-method (weak — the check is instantaneous, and
`BatchGenerationService` then hands work to an unbounded single-thread executor, so the work runs even
if leadership is lost). Unlike `bank-postings`, the request path *does* scale horizontally; operator
concurrency is controlled by the lock table instead. (§12)

**15. The operator lock is an application-level table acquired read-then-insert, with no unique
constraint visible in the migrations** — and the bulk operations lose their `@Lockable` AOP advice to
Spring proxy self-invocation (`checkMultipleRequest` → `this.checkRequest(...)`). The bulk path works
only because the UI creates locks up-front via `POST /lock-withdrawal-request`. A single property,
`property.locking.disabled`, turns all of it off. (§9)

**16. Spring's `ApplicationEventMulticaster` is replaced, and listener threading is decided by an
annotation on the listener.** `DistributiveEventMulticaster` routes by the module's own
`@AsyncListener`, and its bean-type resolution failure path silently defaults to **sync**. Combined
with `TransactionalEventPublisher`'s after-commit deferral, a listener's actual timing is the product
of two independent, non-local decisions. (§12)

**17. Config resolution is two independent placeholder passes with opposite failure policies.**
`.properties` (order 1, `ignoreUnresolvablePlaceholders=true`, system properties override everything)
then YAML (order 2, `ignoreUnresolvablePlaceholders=false`). A `.properties` typo surfaces as a
baffling pass-2 startup failure. `environment` and `site` also become Spring profiles, which is what
turns leader election and OTLP metrics off in `dev`. (§15)

**18. Java 8 is the production target despite the README's "Java 17+"** — with `contract-test` and
`post-deployment-tests` compiling at 17 and `feature-flag` pinned back to 8. Mockito 5.23 requires a
Java 11+ *runtime* for tests. Both Jackson generations (Codehaus 1.9.11 and FasterXML 2.11.4) are on
the classpath. (§3, §17)

**19. `PaymentRunBehaviorFactory.getPaymentRunBehavior` constructs a `PaymentRunException` and never
throws it**, returning `null` for any unmapped stage so the caller NPEs. One-word fix. Its siblings are
inconsistent too: `WithdrawalTypeRuleEngineFactory` returns `null` for an unmapped region (and the keys
are display strings like `"IGM Italy"`, `"IGAUSTRALIA CRYPTO"`), while `WithdrawalProcessStateFactory`
correctly throws with the offending criteria. (§8, §19)

**20. XML-declared beans still receive `@Autowired` constructor injection**, which is how the Singapore
withdrawal-type chain is assembled past `SingaporeFastPayRule` — the `rtgsRule`/`btRule`/`achRule`/`ttRule`
beans look like orphans in `bankwithdrawal-domain.xml` and are not. Neither the XML nor the
constructors alone describe the wiring. (§7, §17)

**21. The two rule engines have opposite registration models.** The 12 automation rules are collected
by `List<ValidationRule>` autowiring — adding a `@Component` changes production risk policy with no
registration step. The 18 pre-validators are an explicit XML `<list>` whose order is load-bearing, with
a comment (`must always be at the end as its non-idempotent`) that is literally true because the last
one makes a remote check-and-update call. (§7, §19)

---

## 21. Unknowns

Things this pass could **not** determine from the repository alone:

1. **What `com.iggroup.wt.security.domain.LogAuthorisationPolicy` actually does.** The class is in the
   external `wt-singlesignon` artefact. Discovery #5 rests on its name. **Verify this first** — it
   changes the severity of the whole §13 authorisation picture.
2. **Whether `BANK_WITHDRAWALS.BW_PROCESS_LOCK` has a unique constraint** on `(object_id, object_type)`.
   No `CREATE TABLE` for it appears in `db.migration/` (it predates Flyway adoption here), and the
   PL/SQL package body was not read line-by-line. This decides whether the lock is actually racy (§9).
3. **Where bank files are written and how they are shipped.** `property.bankfile.directory = ukpayments`
   and `property.goanywhere.bankfile.directory = /opt/projects/goanywhere_files/live/outbound` are
   known; the writer-side details are in the bank-file subsystem — see §16/§22 for the dedicated pass.
4. **Whether the `PROJECT/DEPLOYMENT/DEPLOYED_ITEM/WORK_ITEM_STAGE` tables in `docs/db_schema.mmd` are
   used by this application** or are a shared/legacy schema tenant. No Java references them.
5. **Which `@AsyncListener`-annotated listeners actually exist.** The mechanism is confirmed; the
   per-listener annotations on the five `service/listener/**` classes were not individually checked, and
   they determine transaction participation.
6. **Whether `BankFileState` is reachable.** It implements `WithdrawalProcessState` but has no entry in
   `WithdrawalProcessStateFactory`'s map.
7. **What the 136 KB `.gitattributes` is for** — Git-LFS manifest, or a very large explicit
   binary/eol list.
8. **Runtime Kafka consumer configuration** (group ids, `auto.offset.reset`, ack mode, concurrency).
   `kafka.properties` is referenced by `AppConfig` but is not in `resource/src/main/properties/`
   — it is presumably injected at deploy time. Since the SIP listener swallows exceptions, ack mode
   determines whether anything is ever redelivered.
9. **The actual PL/SQL semantics of the pending-request "optimised" variant**
   (`OPTIMISED_GET_PENDING_WITHDRAWAL_SPROC`, region-gated) versus the original — a behavioural
   difference behind a feature flag, in the database.
10. **Whether `impl-japanese` duplicates or extends the main flows.** 118 files, its own ports/adapters/
    email/validation/JMX, its own double-entry-ledger flag, and both "migrated" and legacy controllers.
    Not analysed in this pass.
11. **Whether the Fiorano→Artemis ledger migration is complete in production.**
    `property.bankwithdrawal.doubleentryledger=true` in prod, but which branch of `FeatureFlaggedLTS`
    `true` selects was not traced.
12. **`SipMessageDecryptor` key management** — where the SIP payload keys come from and how they rotate.

---

## Investigation Checklist

| Area | Status |
|-|-|
| Module / Maven structure | ✅ |
| Framework versions, BOM behaviour | ✅ |
| Architecture + layering | ✅ |
| State machines (both) | ✅ |
| Primary + automated withdrawal flows | ✅ |
| Manual review + payment run flows | ✅ |
| SIP / pacs.002 flow | ✅ |
| TMS batch generation flow | ✅ |
| GDPR obfuscation flow | ✅ |
| Transactions / consistency / idempotency | ✅ |
| Locking + concurrency | ✅ (one open question, §21.2) |
| Persistence, PL/SQL, Flyway | ✅ |
| Caching | ✅ |
| External integrations | ✅ |
| Security / authorisation | ✅ (one open question, §21.1) |
| Observability | ✅ |
| Error handling / resilience | ✅ |
| Configuration / feature flags | ✅ |
| Rule engines (both) | ✅ |
| Bank file generation | ✅ (§22) |
| Testing / CI | ✅ (§16) |
| `impl-japanese` | ❌ not analysed (§21.10) |
| `client` / `client-intf` published contract | ⚠️ enumerated only |

---

## 22. Bank File Generation Subsystem

The end of the manual-review workflow. A bank file is the physical artefact a bank acts on, so this
subsystem is where a defect becomes real money moving wrongly. It is also the least uniform part of the
codebase.

### End-to-end flow

**Trigger** — `POST /generate-bank-file/{regionId}` on `PaymentRunController.java:164-177`.
The line directly above it (`:163`) is a bare `//TODO needed here` with no explanation, sitting on top
of the single most consequential entry point in the module.

**Locking** — `BankFileServiceImpl.generateBankFile` is `@Lockable` (`:60`) and matched by
`BankWithdrawalAspect`'s `paymentRunService()` pointcut (`:46-49, 69-86`). The advice acquires
`lockPaymentRunProcess(regionId, user)` (a `REQUIRES_NEW` DB row insert) and `purgeLock`s in `finally`.
So the lock is **a DB row scoped to `regionId`**, held only for the duration of one call.

**Orchestration** — `service/bankfile/BankFileServiceImpl.generateBankFile` (`:61-73`), `@Transactional`:

1. `paymentRunRepository.getPaymentRunDetails(regionId)` — loads the current `PaymentRun`. **No
   workflow-stage assertion in this method.**
2. `BankFileDataProviderFactory.getBankFileDataProvider(regionId)` — resolves the region name, then a
   static `Map<String, List<AbstractBankFileDataProvider>>` built in the factory constructor (`:41-55`).
   **One region can map to several providers**, each emitting its own file(s) — e.g. UK →
   `[CommonRegionsBankFileDataProvider, RBSBankFileDataProvider, LloydsUkRegionBankFileDataProvider]`.
3. `ensureBankFileRowsEqualToRequestCount` (`:90-102`) — **row-count reconciliation**: total rows across
   a provider's `BankFileData` objects must equal `paymentRun.getBankWithdrawalProcessList().size()`,
   else `PaymentRunException`. The only consistency check in the whole flow.
4. `generateBankFile(bankFileDataList)` (`:104-111`) — dispatches each `BankFileData` to the
   `BankFileGenerator` for its `DocumentType`: `CSVGenerator` or `XMLGenerator`, passing
   `goAnyWhereFeaturesMbean.isEnabled()` to choose the output directory.
5. `updateWithdrawalRequestsToReadyForUpload` — every in-progress process for the run moves to
   `READY_FOR_UPLOAD`; `updatePaymentRunAudit` stamps the generating user and timestamp.

**Output destination — chosen by a live JMX flag, not per-region config.**
`GoAnyWhereFeaturesMbean.isEnabled()` (default `property.goanywhere.feature.flag=true`) selects:
- GoAnywhere: `/opt/projects/goanywhere_files/live/outbound` (absolute, prod).
- MoveIt: `property.bankfile.directory = ukpayments` — **a relative path in prod** (dev is the absolute
  `c:\dev\ukpayments`). Files land relative to the process working directory; no absolute override was
  found. Worth verifying against the deployment (UNKNOWN whether the container pins CWD).

Both channels are plain filesystem writes (`Files.newBufferedWriter` for CSV,
`new FileOutputStream` for XML). **There is no SFTP client, no DB blob, no checksum, no manifest and no
acknowledgement handling anywhere in this subsystem.** Delivery to the bank is entirely delegated to
external GoAnywhere/MoveIt agents that sweep those directories — outside this repo's visibility.

### **THERE IS NO FILE SEQUENCE NUMBER**

- The general filename mechanism (`AbstractBankFileDataProvider.createFileName` /
  `createFileNameBasedOnPaymentType`, `:26-34`) is **prefix + formatted now() + suffix**, e.g.
  `RBS_UK_yyyyMMdd_HHmmss.txt`, using `property.bankfile.datepattern = yyyyMMdd_HHmmss` —
  **second granularity**.
- Where a file header carries a "sequence number", it is fabricated per write. For the four Lloyds
  providers (UK / IGM Europe / Italy / Dubai), `HeaderDataRow.sequenceNumber` is
  `BankFileDataUtil.getEpochSecond()` = `Instant.now().getEpochSecond()` (`:189-192`). **Two files
  generated in the same UTC second get the same header sequence number.** It is not a counter at all.
- The only DB-backed reference in the subsystem is `FileReferenceRepository` /
  `GetFileReferenceDetail` / `UpsertFileReferenceDetail` (`BANK_WITHDRAWALS.BW_REFERENCE_DETAIL.GET`
  and `.UPSERT`, the only two bank-file beans wired in XML at `bankwithdrawal-jdbc.xml:129,133`), and
  it is used **exclusively** by the two Australia-China generators. Nothing else touches that table,
  and the value never appears in a filename — only inside the header (`"ACH" + referenceId`).

### Regional formats actually implemented

Two mechanisms only: **BeanIO** (CSV and fixed-width, template XML per format) and **JAXB** (XML).

| Region / bank | Provider class | Mechanism | Notable hardcoded constants |
|-|-|-|-|
| UK (common) | `CommonRegionsBankFileDataProvider` | BeanIO, `uk-italy-dubai-southafrica-mapping.xml` | debit account name literal `"IG"` (`:134`) |
| UK (RBS) | `RBSBankFileDataProvider` | BeanIO, `rbs-mapping.xml` | `ACCOUNT_NUMBER_LENGTH=8` zero-left-pad (`:52,128`); record types `"01"`/`"02"`/`"04"` (`:147-152`) |
| UK (Lloyds) | `LloydsUkRegionBankFileDataProvider` | BeanIO, `igm-europe-uk-mapping.xml` (32-column generic row) | `TRAILER_RECORD_TYPE="T"`, `PAYMENT_TYPE_EUR="EURURG"`, `SHA`, name lengths 35 / 18 (BACS), `CDNS_CURRENCIES=[CHF,DKK,NOK,SEK,SGD,HKD]` |
| Italy (IGM) | `LloydsItalyRegionBankFileDataProvider` + Common | BeanIO, `italy-dubai-region-mapping.xml` | `PAYMENT_TYPE="MB"`; dead constants `OTHER`/`IBAN` |
| Dubai | `LloydsDubaiRegionBankFileDataProvider` + Common | BeanIO, same template as Italy | `PAYMENT_TYPE="INT"`; AED value-date rule Thu→+3d, Fri→+2d, else +1d |
| South Africa | `CommonRegionsBankFileDataProvider` | BeanIO | — |
| Europe (IGM) | `LloydsIGMEuropeRegionBankFileDataProvider` + Common | BeanIO, shares `igm-europe-uk-mapping.xml` with UK | `CDNS_CURRENCIES=[CHF,DKK,NOK,SEK]` — **SGD and HKD missing vs the UK list** |
| IGE Italy / IGE Europe | `HYPOBankFileDataProvider` (XML/JAXB) + `LloydsIGEEuropeRegionsBankFileDataProvider` (BeanIO) | both | the Lloyds-IGE provider is a near byte-for-byte clone of `CommonRegionsBankFileDataProvider` |
| Switzerland | `SwissBankFileDataProvider` | BeanIO, `swiss-bank-file-mapping.xml`, **2 files per run** (SWD disclosed / SWI non-disclosed) | `SWISS_PAYMENT_TYPE="103"`, `SWISS_BANK_OPERATION_CODE="CRED"`, `CHARGES="OUR"`, BIC padded to 11 with `'X'` |
| Singapore | `SingaporeBankFileDataProvider` | BeanIO, `singapore-bank-file-mapping.xml` + `singapore-fast-bank-file-mapping.xml`, **up to 3 files per run** (FAST / RTGS / other) | `SCB="SCB"`; FAST ACH value date Fri→+3d else +1d |
| US ACH | `USACHBankFileDataProvider` | BeanIO, `us-ach-mapping.xml` | filename `BMOHarris_<region>_<date>` |
| US Wire | `USWireTransferBankFileDataProvider` | BeanIO, `us-wire-transfer-mapping.xml` | `FED="FED"` on every row |
| Hong Kong (HSBC, IGX) | `HSBCIGXHKBankFileDataProvider` + `HSBCHKXMLBankFileGenerator` | **JAXB**, splits FPS + RTGS | `FPS_AMOUNT_LIMIT=1,000,000` HKD; initiating party `ABC56595001`; `REGULATORY_REPORTING_INFO="/ORDERRES/HK//OTHR"` |
| HYPO (Germany / SEPA) | `HYPOBankFileDataProvider` + `HYPOXMLBankFileGenerator` | **JAXB**, splits `_DOMESTIC.xml` + `_CB.xml` | BIC `HYVEDEMMXXX`; a 23-country EUR-domestic whitelist **duplicated** from a separate 49-country Europe whitelist |
| Australia (main) | `AustraliaBankFileDataProvider` → `AustraliaFileServiceDelegator` → `AustralianFileServiceImpl` / `AustralianWestpacFileServiceImpl`, switched by `property.hsbc.enabled` | fixed-width BeanIO | APCA user IDs `313798` / `427910` |
| IGAU Australia | `IGAUAustraliaBankFileDataProvider` → `IgauAustraliaWestPacFileServiceImpl` | fixed-width BeanIO, DE + APT family, **no CUP** | APCA `604123` / `427866` |
| IGDAAU Australia Crypto | `IGDAAUAustraliaCryptoBankFileDataProvider` → `IgdaauAustraliaCryptoWestPacFileServiceImpl` | fixed-width BeanIO, **DE only** | APCA `677101` |

**Australia detail** (the most complex region by far):
- **APT** (`AptFileDataGenerator`) — header `recordType="01"`, `paymentTypeNumber="3"`,
  `bankCode="AU03"`; rows `recordType="06"`. `AptRules` routes **13 currency/segregation variants**,
  each with a 2-letter filename prefix (CU/RU/CN/RN/CI/RI/CH/RH/CG/RG/CE/RE/CD).
- **APT-RTGS** (`AptRtgsFileDataGenerator`) — `paymentTypeNumber="2"`, rows `recordType="07"`; a single
  inline rule (AUD + bank country AU + non-NZ resident). Hardcodes its template instead of sourcing it
  from `RulesDetailProvider` like its siblings.
- **NZ APT** (`nz/NzAptFileDataGenerator`) — a duplicate of `AptFileDataGenerator`; only the header
  bank code differs (`"NZFC"` vs `"AU03"`).
- **Westpac APT** (`hsbc/AptWestpacFileDataGenerator`) — a **third** copy of the same logic, carrying
  the *verbatim* stale comment `// TODO: Change the logic to get the IG bank details in Header itself`
  present in both `AptFileDataGenerator.java:116` and `AptWestpacFileDataGenerator.java:115`, which
  proves one was forked from the other and neither was fixed. It also adds an **undocumented
  divergence**: if any beneficiary address line contains Han-script characters, **all three address
  lines are silently blanked** rather than sent.
- **SGD APT** (`AptSgdCurrencyDataGenerator`) — breaks the declarative pattern by hardcoding
  `singapore-bank-file-mapping.xml`; the corresponding `AptRules.getAptSgdSegregatedDetails()` leaves
  its template field `null` because routing special-cases SGD first. A trap for anyone adding a
  currency by copying the "normal" pattern.
- **Direct Entry (DE) family** — `DeFileDataGenerator`, `igau/IgauAustraliaDeFileDataGenerator`,
  `igdaau/IgdaauAustraliaCryptoDeFileDataGenerator`: near-identical BSB logic (`getBsbNumber` splits
  `"NNN-NNNNN"` **only** if the raw code is exactly 6 digits with no hyphen, otherwise returns it
  unmodified with no validation). `AustraliaEFTCommonUtils` hardcodes bank `"WBC"`,
  `reelSequenceNumber(1)` **always** (single-reel APCA convention, not a counter), `bsbFormat="999-999"`.
- **NZ DE** (`nz/NzDeFileDataGenerator`) — a *different and more fragile* style: raw character-index
  slicing (`branchCode.charAt(3..6)`) with **no length check** (uncaught
  `StringIndexOutOfBoundsException`), and account-suffix parsing that splits on `"-"` and throws
  `ArrayIndexOutOfBoundsException` if absent. `NzDeRules` sets an **empty** APCA identification number
  for both its variants, unlike every AU/IGAU/IGDAAU DE rule.
- **CUP** (`CUPFileDataGenerator` / `CUPFileRule`) — gated by `property.cup.enabled`, reachable only
  from main-AU routes. Its filter requires an **empty** SWIFT/bank code plus website `CNM`/`CN4` and
  currency `CNY`/`CNH` — an inverted-looking "only fire when there is no bank code" condition worth
  confirming against business intent. The header row bakes literal column-header text (`"Batch ID"`,
  `"Beneficiary Name"`, …) into the data model rather than template metadata.
- **ACH China / PP China** (`AchChinaFileDataGenerator` / `PPChinaFileDataGenerator`) — share
  `china-ach-mapping.xml` and the DB-backed reference token below.

### **Idempotency — there is no reliable guard, and CSV re-generation can corrupt a file**

1. **No prior-generation check.** `BankFileServiceImpl.generateBankFile` never asks whether a file has
   already been produced for this run; it reloads whatever processes are attached and regenerates.
   `ensureBankFileRowsEqualToRequestCount` checks row *parity*, not "has this already run".
2. **`CSVGenerator` does not truncate.** `CSVGenerator.java:42`:
   ```java
   try (BufferedWriter fileWriter = Files.newBufferedWriter(filePath, CREATE)) {
   ```
   `Files.newBufferedWriter` delegates to `newOutputStream`, whose contract is: with **no** options it
   behaves as `CREATE, TRUNCATE_EXISTING, WRITE`; with an explicit option array that contains neither
   `APPEND` nor `TRUNCATE_EXISTING`, only `WRITE` is added. Passing `CREATE` alone therefore opens the
   existing file **without truncating**. If a regeneration lands on an existing filename — trivially
   reachable given `yyyyMMdd_HHmmss` second-granularity naming and a double-click — and the new content
   is **shorter** than the old, **the tail of the previous file survives** and a bank file goes out with
   stale trailing records appended to valid ones. **This affects every CSV/BeanIO format**: UK, RBS, the
   four Lloyds variants, Switzerland, Singapore, US ACH, US Wire and all Australia fixed-width formats —
   i.e. the majority of the subsystem's output. Verified against the JDK contract; a one-token fix
   (`CREATE, TRUNCATE_EXISTING`).
3. **The XML path is safe** — `HYPOXMLBankFileGenerator` and `HSBCHKXMLBankFileGenerator` use
   `new FileOutputStream(path)`, whose default constructor truncates. Asymmetric robustness for what
   should be one guarantee.
4. **The Australia-China reference token is a slow-rotating global value, not a per-file sequence** —
   back-to-back regenerations reuse the same `"ACH<id>"` string. No double-allocation risk, but no
   per-file uniqueness either.
5. **The lock prevents concurrent double-submission for a region, not a sequential re-run.** It is
   acquired and released inside one `generateBankFile` call; nothing stops the same operator calling
   the endpoint again five minutes later, and neither the controller nor the service checks.

### Concurrency

- Coordination is entirely the shared Oracle lock row scoped to `regionId`
  (`PaymentRunProcessLockServiceImpl.lockPaymentRunProcess`, `REQUIRES_NEW`;
  `ProcessLockValidationServiceImpl.validateForPaymentLockCreation:70-82` throws if a region lock
  exists **or** if any withdrawal request in the run is individually locked). This does correctly
  protect against concurrent generation across app instances — for the duration of one call, per region.
- **No shared mutable formatter state.** `SimpleDateFormat` is consistently constructed *locally per
  call* (`RBSBankFileDataProvider.getValueDate`, `CommonRegionsBankFileDataProvider.getValueDate`,
  `SwissBankFileDataProvider.createBankFileDataRow`, `BankFileDataUtil.getValueDate`) — the classic
  non-thread-safe-formatter bug does **not** apply here. `SwissBankFileDataProvider.cleanIBANorBIC` is
  `static` but pure. No static counters.
- The one genuine cross-invocation shared resource is the `FileReferenceDetails` row, which is
  **global, not region-scoped**. Concurrent generation for two different regions that both reach
  ACH-China/PP-China would race unprotected. Today only the single AU region reaches them, so the
  window is closed — **incidentally, not by design.**

### Failure handling

- **CSV** — try-with-resources; an `IOException` becomes a `PaymentRunException` and propagates, but
  **the partially written file is never deleted**. With the truncation gap above, a mid-write failure
  leaves a partial file on disk with no cleanup and no incomplete-marker.
- **XML — a genuine silent-failure bug.** `HYPOXMLBankFileGenerator.generateXML` catches `IOException`,
  logs, closes the stream and `new File(path).delete()`s the target (a real compensation step) — and
  then the **caller** `generateXMLFIle` (sic) catches `IOException` and only logs
  (`:100-102`; same shape in `HSBCHKXMLBankFileGenerator:144-149`). Neither `XMLGenerator.generateBankFile`
  nor `BankFileServiceImpl` can tell that generation failed, so **the payment run still advances every
  withdrawal request to `READY_FOR_UPLOAD` as if the file existed.** An HYPO or HSBC-HK file can fail
  to write, be deleted, log an error, and the workflow proceeds. (Nuance: `Jaxb2Marshaller.marshal`
  raises unchecked `XmlMappingException`, which is *not* caught here and would propagate — so the
  swallow specifically covers I/O failures, which is the likely class for a full disk or a bad mount.)
- **Australia** — no `catch` blocks anywhere under `service/bankfile/australia/**`; failures propagate
  and (given `generateBankFile`'s `@Transactional`) roll back the DB-side workflow changes. But files
  already written to disk by earlier providers in the same loop are **not** removed — there is no
  compensating delete across the whole call, only the two XML writers cleaning up their own single file.
- **No checksums, manifests or acknowledgements** anywhere; delivery confirmation is external.

### Surprising findings

1. **`//TODO needed here` above the generation endpoint** (`PaymentRunController.java:163`) — no
   explanation. Given the idempotency gaps, plausibly a known-unfixed gap.
2. **Systemic week-year bug: `"YYYY"` instead of `"yyyy"`.** Seven occurrences confirmed:
   `BankFileDataUtil.java:152` (`SimpleDateFormat("YYYYMMdd")`), `:204`, `:215`, `:266`
   (`DateTimeFormatter.ofPattern("YYYYMMdd")`), `AchChinaFileDataGenerator.java:131` and
   `PPChinaFileDataGenerator.java:126` (`"YYYY/MM/dd"`), `CUPFileRule.java:76` (`"YYYYMMddHHmmss"`).
   `YYYY` is the **ISO week-based year**. Around a year boundary — e.g. a value date landing in the last
   ISO week of December, which is exactly what the Dubai/Singapore "+1/+2/+3 day" value-date rules
   produce — these emit **the wrong year** in `valueDate` and `fileCreationDate` fields sent to banks.
   The same files use lowercase `"yyyyMMdd"` correctly elsewhere, so this is intra-file inconsistency,
   not a convention. It survives because it is untriggerable in mid-year testing.
3. **The Lloyds header "sequence number" is `Instant.now().getEpochSecond()`** — collides within a
   second and is disconnected from the one real DB reference mechanism.
4. **The DB-backed file reference has an arithmetically wrong rotation policy and is a single global row.**
   `GetFileReferenceDetail` reads `fileReferenceDetails.get(0)` (no `WHERE` visible in Java). The
   refresh check is:
   ```java
   Period p = Period.between(today, referenceDate);
   return (p.getMonths() + p.get(ChronoUnit.DAYS)) > MIN_MONTH_FOR_UNIQUE_REFERENCE; // 3
   ```
   It **sums the months component and the days component of the same `Period` as if they were one unit**.
   Exactly 3 months + 0 days gives `3 > 3 = false` (no refresh at the boundary the constant name
   implies); 2 months + 15 days gives `17 > 3 = true` (refresh far earlier). The reference token in
   Australia-China bank-file headers therefore rotates unpredictably rather than on any documented
   cadence — and most banks expect a unique reference per submission, which this is neither.
5. **Confirmed near-duplicate classes.** `LloydsIGEEuropeRegionsBankFileDataProvider` ≈
   `CommonRegionsBankFileDataProvider`. `AptFileDataGenerator` ≈ `NzAptFileDataGenerator` ≈
   `AptWestpacFileDataGenerator` (three forks). The DE family is a fourth instance. Fixing a bug in one
   requires finding the other two or three.
6. **Copy-paste residue in production code** — `PPChinaFileDataGenerator` logs
   `"AchChinaFileDataGenerator method=createBankFileData"` and still declares
   `UNIQUE_REFERENCE_PREFIX = "ACH"`.
7. **Unexplained divergence between near-identical regions** — the "CDNS currency" list that drives a
   formatting split is `[CHF,DKK,NOK,SEK,SGD,HKD]` for UK-Lloyds and `[CHF,DKK,NOK,SEK]` for
   IGM-Europe-Lloyds. Same concept, no shared constant, nothing documents why.
8. **Dead / misleading code** — `BatchHeaderDataRow` is wired through `BankFileData`,
   `BankFileDataBuilder` and `CSVGenerator.createBatchHeader` but **no provider sets it**;
   `LloydsItalyRegionBankFileDataProvider.OTHER` / `.IBAN` are unreferenced;
   `HYPOBankFileDataProvider.US_ACH_BANK_FILE_TEMPLATE` is named for US ACH but holds
   `hypo-bank-mapping.xml` and is never consumed because HYPO is JAXB, not BeanIO.
9. **The pacs.008 / pacs.002 XSDs are NOT part of bank-file generation.** `schemas/src/main/resources/xsd/`
   is consumed only by the real-time Kafka SIP path (`service/transformer/Pacs008Assembler`,
   `kafka/sip/Pacs002SipWithdrawalMessageService`, `service/SIPWithdrawalService`,
   `kafka/sip/SipWithdrawalEventListener`) — no `BankFileGenerator`, provider or template references
   them. Easy to conflate "ISO 20022 XML" with the batch-file channel; they are unrelated transports.
10. **This subsystem is *not* XML-wired**, despite the module's XML-config character. Only the two
    stored-procedure beans appear in `bankwithdrawal-jdbc.xml:129,133`; the `Jaxb2Marshaller` beans
    (`hypoBankMarshaller`, `hsbcHkBankMarshaller`), `BankFileLocationService` and every
    `AbstractBankFileDataProvider` subclass are component-scanned. (The `@Configuration` class producing
    the marshallers was not located in this pass — UNKNOWN.)
11. **Environment-divergent output config**, relevant to anyone testing regeneration:
    `property.bankfile.batchThreshold` 200 (prod) vs 3 (dev);
    `property.australia.bankfile.batchThreshold` 99 (prod) vs 3 (dev);
    `property.bankfile.directory` relative `ukpayments` (prod) vs absolute `c:\dev\ukpayments` (dev).

---

## 23. Addenda to the Ranked Discoveries

These emerged from the bank-file and testing passes and rank alongside §20.

**A. `CSVGenerator` opens bank files with `StandardOpenOption.CREATE` and no `TRUNCATE_EXISTING`
(`CSVGenerator.java:42`).** Regenerating onto an existing filename leaves the tail of the previous file
in place when the new content is shorter — a corrupted bank file, on the majority of formats
(all CSV/BeanIO regions), reachable by a double-click within the same second given `yyyyMMdd_HHmmss`
naming. Highest-severity correctness defect found in this pass; one-token fix. (§22)

**B. Seven `"YYYY"` (ISO week-year) date patterns in bank-file date fields** —
`BankFileDataUtil.java:152,204,215,266`, `AchChinaFileDataGenerator.java:131`,
`PPChinaFileDataGenerator.java:126`, `CUPFileRule.java:76`. Around the New Year these emit the wrong
year in `valueDate`/`fileCreationDate` sent to banks, and the Dubai/Singapore value-date rules push
dates across exactly that boundary. Invisible in mid-year testing. (§22)

**C. HYPO and HSBC-HK XML file-generation I/O failures are swallowed and the workflow still advances.**
The inner method deletes the failed file (real compensation) but the caller catches `IOException` and
only logs, so `BankFileServiceImpl` marks every request `READY_FOR_UPLOAD` for a file that does not
exist. (§22)

**D. A green merge pipeline proves only that unit tests and the Japanese component tests passed.**
Acceptance, contract, critical-sign-off, DB health-check, Snyk and coverage jobs are all
`allow_failure: true`; `functional-tests` never runs; and `impl`'s real-Oracle integration tests never
run because `skip-failsafe` stays `true`. Coverage cannot fail a build (`haltOnFailure=false`), and the
stricter 75% Clover profile is dormant. (§16)

**E. Test-fixture drift has already cost real coverage.** `impl/src/test/resources/rules-engine-test-config.xml`
duplicates the production `withdrawalTypeRuleEngineFactory` map with **7** region keys against
production's **12** — plain `"Italy"` matches neither `"IGM Italy"` nor `"IGE Italy"`, and Dubai is
absent entirely. The Dubai route and the Italy/Europe legal-entity split are **not exercised** by
`WithdrawalTypeServiceImplTest`. (§16)

**F. Bank-file delivery is fire-and-forget onto a filesystem, and in prod the MoveIt path is a relative
directory.** No SFTP, no checksum, no manifest, no acknowledgement; `property.bankfile.directory = ukpayments`
resolves against the process working directory. Confirm what pins CWD in the deployment. (§22)

**G. The one DB-backed file reference rotates on arithmetic that sums a `Period`'s month and day
components as if they were one unit**, so the "3-monthly" cadence is neither 3-monthly nor
unique-per-submission — and the row is global rather than per-region/bank/file. (§22)

**H. `contract-test` is a well-built, consumer-scoped OpenAPI-diff framework that cannot fail the
build.** It downloads each provider's live spec and diffs only the paths this service's Feign clients
consume — exactly the right granularity — and runs `allow_failure: true`. Making it blocking is the
single cheapest integration-safety win available. (§16)

---

## Files Referenced (primary evidence)

**Build / config**
`pom.xml` · `contract-test/pom.xml` · `post-deployment-tests/pom.xml` · `feature-flag/pom.xml` ·
`impl/pom.xml` · `coverage/pom.xml` · `component-tests/pom.xml` · `functional-tests/pom.xml` ·
`.gitlab-ci.yml` · `.snyk` · `bom.yml` · `lombok.config` · `README.md` · `README.txt`

**Spring wiring (`war/src/main/resources/`)**
`bankwithdrawal.xml` · `bankwithdrawal-domain.xml` · `bankwithdrawal-service.xml` ·
`bankwithdrawal-jdbc.xml` · `bankwithdrawal-external-jdbc.xml` · `bankwithdrawal-security.xml` ·
`bankwithdrawal-jms.xml` · `bankwithdrawal-jms.amq.xml` · `bankwithdrawal-jmx.xml` ·
`bankwithdrawal-featureflag.xml` · `bankwithdrawal-event-handler.xml` ·
`bankwithdrawal-component-scan.xml` · `bankwithdrawal-springintegration.xml` ·
`bankwithdrawal-japanese-service.xml` · `bankwithdrawal-japanese-email-service.xml` ·
`double-entry-ledger.xml` · `ehcache.xml` · `webapp/WEB-INF/web.xml`

**Configuration (`resource/src/main/properties/`)**
`common/common.yaml` · `common/payment-mapping-config.json` · `prod/runtime.properties` ·
`prod/application-LIVE.yaml` · `prod/LIVE.environment.properties` · `prod/PROD1.site.properties`

**Domain / state**
`domain/paymentrun/WithdrawalStage.java` · `domain/paymentrun/WithdrawalStatus.java` ·
`domain/bankwithdrawal/BankWithdrawalProcess.java` · `domain/bankwithdrawal/BankWithdrawalStatus.java` ·
`domain/processstates/WithdrawalProcessState.java` · `domain/processstates/SubmittedState.java` ·
`domain/processstates/ReadyForCreditSignOffOne.java` (+ 11 sibling state classes) ·
`domain/paymentrun/stages/AbstractPaymentRunStage.java` · `domain/paymentrun/stages/PaymentRunStage.java` ·
`domain/paymentrun/stages/PaymentRunBehaviorFactory.java`

**Rules**
`domain/bankwithdrawal/rules/automatedwithdrawal/validation/RuleEngine.java` · `ValidationRule.java` ·
`ValidationResultCode.java` · `HighValueRule.java` · `CumulativeWithdrawalLimitRule.java` ·
`CountryRiskRule.java` · `NewBankDetailsRule.java` ·
`domain/bankwithdrawal/rules/withdrawaltype/WithdrawalTypeRuleEngineImpl.java` ·
`WithdrawalTypeRuleEngineFactory.java` · `singapore/SingaporeFastPayRule.java`

**Application services**
`application/service/BankWithdrawalServiceImpl.java` · `WithdrawalRequestUpdateServiceImpl.java` ·
`PaymentRunProcessLockServiceImpl.java` · `ProcessLockValidationService.java` ·
`WithdrawalProcessStateFactory.java` · `RoleServiceImpl.java` ·
`WithdrawalStatus/WithdrawalStatusServiceImpl.java`

**Automation / batch**
`service/automation/AutomationService.java` · `service/batch/BatchGenerationService.java` ·
`service/scheduler/BatchGenerationScheduler.java` · `service/scheduler/ProcessLockPurgeSchedulerJob.java`

**Bank files**
`service/bankfile/BankFileServiceImpl.java` · `CSVGenerator.java` · `AbstractBankFileDataProvider.java` ·
`BankFileDataUtil.java` · `BankFileDataProviderFactory.java` · `xml/HYPOXMLBankFileGenerator.java` ·
`xml/HSBCHKXMLBankFileGenerator.java` · `australia/AptFileDataGenerator.java` ·
`australia/hsbc/AptWestpacFileDataGenerator.java` · `australia/nz/NzDeFileDataGenerator.java` ·
`australia/AchChinaFileDataGenerator.java` · `australia/PPChinaFileDataGenerator.java` ·
`australia/CUPFileRule.java`

**Persistence**
`eai/jdbc/repository/BankWithdrawalProcessJdbcRepository.java` ·
`eai/jdbc/sproc/lock/UpsertPaymentRunProcessLock.java` ·
`eai/persistence/repository/WithdrawalRateLimitRepository.java` ·
`eai/jdbc/TransactionalEventPublisher.java` ·
`impl/src/main/resources/db.migration/**` (42 `V__` + 14 `R__` scripts) · `docs/db_schema.mmd`

**Messaging / integration**
`kafka/sip/SipWithdrawalEventListener.java` · `kafka/sip/Pacs002SipWithdrawalMessageService.java` ·
`kafka/sip/SipFailureCode.java` · `configuration/kafka/CustomLeaderElectionListenerForKafka.java` ·
`service/listener/amq/AmqEligibleClientListener.java` · `service/listener/DistributiveEventMulticaster.java`

**Cross-cutting**
`adapters/WithdrawalRateLimitAdapter.java` · `service/validator/RateLimitPreValidator.java` ·
`service/validator/SubsequentWithdrawalValidationRule.java` · `service/aspects/BankWithdrawalAspect.java` ·
`service/aspects/AuthorizationEnablerAspect.java` · `configuration/scheduler/SchedulerConfig.java` ·
`configuration/leaderelection/*.java` · `configuration/observability/GoldenSignalsConfiguration.java` ·
`observability/RequestMetricsService.java` · `observability/TracingSupportFilter.java` ·
`war/src/main/java/.../config/AppConfig.java` · `war/.../config/ProfileAwareContextLoaderListener.java` ·
`war/.../exceptionhandler/BankWithdrawalExceptionHandler.java`

**Controllers**
`war/.../web/controllers/BankWithdrawalController.java` · `TestRuleEngineController.java` ·
`admin/PaymentRunController.java` · `admin/WithdrawalRequestUpdateController.java` ·
`feature-flag/.../web/TogglzApiController.java`

**Feature flags**
`feature-flag/.../feature/WithdrawalFeatures.java` · `feature-flag/.../service/FeatureFlagService.java` ·
`feature-flag/.../strategy/*.java`

**Tests**
`impl/src/test/resources/rules-engine-test-config.xml` ·
`impl/src/test/.../ContentJdbcRepositoryIntegrationTest.java` ·
`contract-test/.../BaseContractTest.java` · `acceptance-test/.../AcceptanceIT.java` ·
`acceptance-test/src/test/resources/application-test.yml` · `acceptance-test/.../KafkaTestUtil.java` ·
`feature-flag/src/test/.../BusinessHoursActivationStrategyTest.java` ·
`post-deployment-tests/.../EnvironmentConfig.java` · `db-health-check/db-health-check.mjs`
