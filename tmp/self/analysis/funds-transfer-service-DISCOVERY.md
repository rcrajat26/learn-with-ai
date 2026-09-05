# funds-transfer-service — Discovery Record

**Analysed:** 2026-09-05
**Repo:** `_Codes/payments/funds-transfer-service` (read-only)
**HEAD:** `1bebf759` (2026-08-21) · 498 commits · 4.25 MiB pack · `master`
**Scale:** 733 Java files, 14 Maven modules, 12 MB working tree
**Legend:** `[OBS]` observed in code · `[INF]` inferred · `[UNK]` unknown / needs owner input

---

## 1. What this service is

Spring Boot **1.5.9.RELEASE** WAR (Java 8, Spring Cloud **Dalston**), deployed to Tomcat on-prem
under context `/funds-transfer-service`. It is the **inter-account money-movement hub** for IG:
moves cash between a client's own IG accounts, between IG and the **Tasty / TastyFX** custodian
(Apex), performs currency conversion, and reconciles daily **net settlement** batches with Tasty.

Four inbound surfaces `[OBS]`:
1. **HTTP** — 12 `@RestController`s, ~60 mappings (client transfers, omnibus transfers, TastyFX
   transfers, internal transaction history, Tasty deposit/withdrawal, ledger posting).
2. **Kafka** — 8 hand-built `KafkaMessageListenerContainer` beans on cluster `peach`.
3. **JMS/AMQ** — one `DefaultMessageListenerContainer` on `mario` for balance-adjustment responses.
4. **JMX** — 3 MBeans (feature flag, Flyway, rate-limit window).

Persistence: Oracle schema **`FUNDS_TRANS`**, 9 JPA entities, 41 Flyway `V` migrations + 10
repeatable `R__*` trigger scripts (audit + GoldenGate replication triggers per table).

**Same generation as `bank-postings`** (Boot 1.5.9 WAR, mantis Zookeeper leader election, ports
package) — but roughly 4× the surface area and with far more money-mutating paths.

### Module map `[OBS]`

| Module | .java | Role |
|---|---:|---|
| `integration` | 389 | **Everything infrastructural**: controllers, adapters, JPA, Kafka, AMQ, Feign, config |
| `domain` | 183 | `FundsTransferService` god-service, 3 specification families, `port` interfaces |
| `tasty-payments` | 77 | Tasty payment/settlement/withdrawal domain + its own specs & ports |
| `currency-conversion` | 30 | CC domain, `CurrencyConversion` aggregate with real transition methods |
| `service-api` | 29 | DTOs only (published API contract) |
| `tests` | 13 | Cucumber runners + a local `main()` runner |
| `observability` | 5 | Logback converters, blue/green cluster detail provider |
| `resource`, `war`, `docs`, `coverage`, `component-tests`, `post-deployment-tests`, `performance-tests` | 0 | packaging / config / reports |

**ARCHITECTURE DETECTED — "hexagonal by vocabulary, layered in practice"** `[OBS]`
- 39 `*Port` interfaces across three `port` packages; ~40 `*Adapter` implementations in `integration`.
- Dependency direction holds one way (`integration → domain → tasty-payments`), **but the domain
  modules are not framework-free**: `domain/pom.xml` depends on `spring-boot-starter-web`, and the
  specifications carry `@Component`, `@Order`, `@Value`, `@Service`. `currency-conversion` depends
  on the vendor client `ct-ledger-service-api`. So ports/adapters give testability, not isolation.
- `integration` has **no internal layering** — 76 sub-packages including a full parallel `tasty/`
  subtree (`tasty/adapter`, `tasty/inbound/kafka`, `tasty/outbound/http`, `tasty/service`, …) that
  duplicates the top-level `adapter`/`inbound`/`outbound`/`service` structure. `[INF]` two eras of
  development that were never merged; see §5.

---

## 2. Highest-severity findings (ranked)

### 2.1 🔴 Every message-processing failure is silent data loss

`[OBS]` The global Kafka error handler is three lines:

```java
// integration/.../tasty/inbound/kafka/errorhandler/KafkaErrorHandler.java
public void handle(Exception e, ConsumerRecord<?, ?> consumerRecord) {
   log.warn("method=handle Error while processing Kafka message with consumerRecord={}", consumerRecord, e);
}
```

It is wired into **all 8** containers via `buildContainerProperties(...)`, which also sets
`containerProperties.setAckMode(BATCH)` (`KafkaConfiguration.java:558-561`). BATCH commits offsets
after each poll batch regardless of listener outcome. There is **no DLQ, no retry, no
`consumer.seek()`, no `SeekToCurrentErrorHandler`**.

Every listener *additionally* swallows on its own — the pattern is uniform across
`TastyPaymentFTSEventListener`, `CurrencyConversionFTSEventListener`, `SettlementBatchEventListener`,
`SettlementBatchEventListenerV2`, `TastyPaymentEventListener`, …:

```java
try { handler.processEvent(event); }
catch (Exception e) { log.error("Failed to process ... error=", ..., e); }
log.info("Processed ... offset={}", ...);   // logged even when processing threw
```

The JMS side is worse — `BalanceAdjustmentResponseListener.onMessage` catches **`Throwable`**, and
`handleBalanceAdjustmentResponse` catches `Exception` again. The container is
`sessionTransacted=false` (default), so the message is acked and gone.

**Consequence:** a transient Oracle blip, a schema-registry hiccup, or an NPE during a Tasty payment,
currency conversion, settlement batch, or balance-adjustment response results in the event being
**permanently discarded**, with the only trace a WARN/ERROR log line. Combined with `auto-offset-reset:
latest` on every topic, the event can never be replayed. `[INF]` For the balance-adjustment saga
(§3.2) a lost credit response leaves the client **debited but not credited**, indefinitely.

Compounding: the prod Logback `AsyncAppender` uses `queueSize=1000` with `discardingThreshold=20`,
so under load the INFO trail of what *was* processed is dropped (WARN/ERROR survive — that part is fine).

### 2.2 🔴 Settlement replay double-posts a custodian ledger — the dedup branch is unreachable

`BatchIdGeneratorService.generateNextBatchId(String currentTastyBatchId, String websiteId)` contains
what is clearly meant to be the settlement idempotency guard `[OBS]`:

```java
if (tastyBatchEntity.getPreviousTastyBatchId() != null
      && tastyBatchEntity.getPreviousTastyBatchId().equals(currentTastyBatchId)) {
   log.info("Batch ID already generated for this settlement batch, returning current batch id, ...");
   return tastyBatchEntity.getCurrentBatchId();
} else if (!currentTastyBatchId.equalsIgnoreCase(tastyBatchEntity.getCurrentBatchId())) {
   log.error("YOU ARE DOING SOMETHING WRONG IF YOU SEE THIS LOG");
   throw new BatchGenerationException(...);
} else { /* roll the batch */ }
```

The parameter name and the column name (`previous_tasty_batch_id`) say this should be **Tasty's
`clearingBatchId`**. But both call sites pass IG's own batch id `[OBS]`:

```java
// NetSettlementEventProcessor, both process(...) overloads
String igBatchId = batchIdGeneratorService.getCurrentBatchId(websiteId);
batchIdGeneratorService.generateNextBatchId(igBatchId, websiteId);   // return value discarded
```

Trace it: first delivery — `previous=X_old`, `current=X`, caller passes `X`. Branch 1 false, branch 2
false (`X == X`), so it rolls: `current=Y`, `previous=X`. **Replay of the same Kafka event** —
`getCurrentBatchId()` now returns `Y`; caller passes `Y`; branch 1 compares `previous(X)` to `Y` →
false; branch 2 compares `Y` to `current(Y)` → equal → rolls again.

**The dedup branch can never fire from production code**, because it requires the caller to pass the
*previous* id while the `else if` guard requires it to pass the *current* one. So a redelivered
settlement batch: creates a fresh `TASTY_SETTLEMENT_BATCH` row, and calls
`custodianLedgerPostingService.postCustodianTransferLedger(...)` / `postThirdPartyTransferLedger(...)`
a **second time for the same Tasty clearing batch**. Given §2.1 there is no retry that would trigger
this — but Kafka at-least-once redelivery (rebalance, leader failover, container restart mid-batch)
will. `[INF]` high severity, low-ish frequency.

### 2.3 🔴 Settlement reconciliation failure is recorded as COMPLETE

`[OBS]` In both `NetSettlementEventProcessor.process` overloads:

```java
if (!SUCCESS.equals(settlementValidationResult)) {
   log.warn("NetSettlement validation failed, validationResult={}, still proceeding to post custodian transfer ledger with igSettlementAmount={}", ...);
   settlementBatch.markBatchProcessingAsIncomplete();
   settlementPort.upsert(settlementBatch);
}
...
String systemReference = custodianLedgerPostingService.postCustodianTransferLedger(tastyRegion, igSettlementAmount, ...);
settlementBatch.markBatchProcessingAsComplete();      // <-- overwrites INCOMPLETE
settlementBatch.updateLedgerSystemReference(systemReference);
settlementPort.upsert(settlementBatch);
```

Two problems, both deliberate-looking:
1. When IG's computed settlement amount **disagrees with Tasty's**, the ledger is posted anyway
   using **IG's** figure ("still proceeding" is in the log message, so this is intentional).
2. The `INCOMPLETE` marker written on the previous line is **unconditionally overwritten with
   `COMPLETE`** a few statements later, in the same method. `SettlementBatch.Status` is only
   `{RECEIVED, INCOMPLETE, COMPLETE}` and there is no history column beyond the audit trigger.

`[INF]` Net effect: a reconciliation break leaves **no durable evidence in the database** — the row
reads COMPLETE. The only artefact is a WARN line and the notification email to
`PaymentOps@ig.com` / `DLUSFinance@…`. For a financial reconciliation control this is the finding
most likely to matter to an auditor.

### 2.4 🔴 Broken Object Level Authorization — account ids are attacker-controlled

`[OBS]` Authentication *is* present: `ig.sso.filter.authenticationFilter.urlPatterns: ['/*']` with
`excludeUris: ['/error']` in **every** environment file (DEV/TEST/UAT/DEMO/LIVE), via the
`ig-sso-spring-boot` starter. `docs/dod-coverage.md` confirms this is why post-deployment tests only
hit `/monitor/version`.

**Authorization is entirely absent** — zero `@EnableWebSecurity`, zero `@PreAuthorize`, zero
`@Secured`, zero `@Profile`, no ownership check anywhere. Account identity comes straight off the wire:

| Endpoint | Account source | Check performed |
|---|---|---|
| `GET /api/clients/funds-transfer/presentation` | `IG-Account-Id` **request header** | none — returns balances for whatever id is sent |
| `GET /api/clients/tastytrade/transactions` | `IG-Account-Id` **request header** | none |
| `POST /api/clients/funds-transfer` | `fromAccount`/`toAccount` in **body** | `ClientAccountsSpecification` only checks the two accounts belong to the *same client* |
| `GET /internal/api/transactions?fromAccountIds=…` | **query param `List<String>`** | none, and the **list length is not capped** (only `size` is, at 100) |

`ClientAccountsSpecification` prevents cross-client theft, but nothing binds the request to the
authenticated caller. `[INF]` Any principal that can reach the service can (a) read any client's
account balances and transfer history, (b) bulk-enumerate history for an arbitrary number of accounts
in one request, and (c) move an arbitrary client's money between that client's own linked accounts.
Same class as the active BOLA remediation programme noted for `payments-gateway`.

Also: `ClientAccountsSpecification` runs at `@Order(HIGHEST_PRECEDENCE + 11)` — **after** the
external-balance, MT4, available-to-withdraw and tax-wrapper specifications. Rejecting an
unauthorised account pair therefore costs a fan-out of upstream calls first.

### 2.5 🟠 Zero transactions on the core money path

`[OBS]` `@Transactional` appears **9 times in 733 files** — 7 in `BalanceAdjustmentService`, 2 in
`TransferRateLimitAdapter`. `@Version` / `LockModeType` / `@Lock`: **zero occurrences repo-wide**.

`FundsTransferService.doClientFundsTransfer` (the main HTTP transfer path) is not transactional and
performs, in order `[OBS]`:

1. 18 specification calls (each potentially an outbound HTTP call)
2. `transferRateLimitPort.tryAcquire(...)` — separate `REQUIRES_NEW` transaction
3. `clientFundsTransferPort.upsert(status = INITIATED)` — DB write, own auto-commit
4. `ledgerPostingPort.buildLedgerReference(...)` then `paymentsPort.checkAndStoreLedgerReference(...)` — remote lock
5. `ledgerPostingPort.postToLedgerTransactions(...)` — **the actual money movement, external**
6. `upsert(status = COMPLETED)` — DB write
7. if destination is Tasty: `tastyDepositService.performDeposit(...)` — **after** COMPLETED is written

Step 7 carries an in-code admission `[OBS]`:
```java
// TODO make sure this request is successful or have a manual retry mechanism
```

`[INF]` A crash between 5 and 6 leaves the ledger posted with the row stuck at `INITIATED`. A failure
in 7 leaves the row at `COMPLETED` with the Tasty deposit never made. Nothing sweeps either state —
there are **no `@Scheduled` methods anywhere in the codebase** (verified: zero matches).

**Last-write-wins persistence** `[OBS]` — `ClientFundsTransferAdapter.upsert` constructs a **brand new
detached `ClientFundsTransferEntity`** from the domain object and calls `save()`, so Hibernate
`merge`s and overwrites *every* column. With no `@Version`, a concurrent HTTP request and JMS response
handler touching the same row silently clobber each other's `ledgerReference` /
`*BalanceAdjustmentId` fields.

### 2.6 🟠 Committed plaintext credentials (DEV tier)

`[OBS]` TEST/UAT/DEMO/LIVE correctly use `@@placeholder@@` token substitution. DEV does not:

| Location | Secret |
|---|---|
| `tests/src/main/java/…/FundsTransferServiceRunner.java:44` | Oracle `FUNDS_TRANS` / `Dl6p4VDez!_Y71ojpK?l` + full TNS descriptor for `vrdevora111` / `DEALDEV1` |
| `resource/…/dev/application-DEV.yml:22` | SSO `svc_fundtrs_test_sso` / `?6a#a&HT?B$Aj8%=PgDCpVn88%wT&QX5` |
| `resource/…/dev/application-DEV.yml:48` | Fiorano `mxWH-pKnk-uQu4Sp0LLixg` |
| `resource/…/dev/application-DEV.yml:121` | JWT service `PS6oa7TzTsLU6l48LDCpHtXtKtINNAJg` |
| `resource/…/dev/kafka-DEV.properties:2` | `peach.sasl.password=SAi7iAvFcf` |
| `resource/…/dev/amq-DEV.properties` | **the same password `SAi7iAvFcf` for all 8 brokers** (banjo, clank, kazooie, luigi, mario, ratchet, sonic, tails) |

Two aggravating factors: the credential-bearing `FundsTransferServiceRunner` is under `src/**main**`
of a **published jar** (`funds-transfer-service-tests`, no `maven.deploy.skip`), and the password
`SAi7iAvFcf` is shared across every DEV broker. `[INF]` **Rotate, don't just delete** — they are in
498 commits of history. `.gitlab-ci.yml` runs GitGuardian, which `docs/dod-coverage.md` reports as
"passing" — `[INF]` these are presumably allow-listed or the scan is diff-only.

### 2.7 🟠 Reflection into Avro's private class cache, to dodge a production livelock

`[OBS]` `BalanceAdjustmentConfiguration` reaches into Avro internals at bean-creation time:

```java
log.info("Pre-loading Avro classes for balance adjustment messages to avoid ConcurrentHashMap livelock on first message");
preloadAvroSchemas(Request.SCHEMA$, Response.SCHEMA$);
...
Field field = SpecificData.class.getDeclaredField("classCache");
field.setAccessible(true);
return (ConcurrentMap<String, Class>) field.get(SpecificData.get());
// on failure: throw new IllegalStateException("Cannot access SpecificData.classCache — Avro internal API may have changed", e);
```

`[INF]` This is a real, diagnosed production incident encoded as a workaround: `SpecificData`'s
recursive `Class.forName` inside `computeIfAbsent` on a `ConcurrentHashMap` can livelock. The fix is
sound but **fails the whole application start** if Avro 1.11.3's private field is ever renamed. This
is the single most valuable piece of institutional knowledge in the repo and it is documented only
in that log string.

Same file, two more items: the schema caches are set to `31557600` seconds (**1 year**) so schema
evolution needs a restart; and the listener's `CachingConnectionFactory` is created inside a private
method rather than as a bean, so its `destroy()` is never called on shutdown.

---

## 3. Mechanisms

### 3.1 STATE MACHINE DETECTED — documented, unenforced, and 7/21 states are dead

`FundsTransfer.Status` (`domain/…/domain/client/FundsTransfer.java`) has **21 constants** and a
block comment documenting **5 named transition flows** `[OBS]`. There is no transition table and no
guard — `updateStatus(Status)` assigns unconditionally.

Grepping for actual writers `[OBS]`, these constants are **never assigned in production code**:
`FUNDS_TRANSFERRED`, `CURRENCY_CONVERSION_INITIATED`, `CURRENCY_CONVERSION_SUCCEEDED`,
`CURRENCY_CONVERSION_FAILED`, `TASTY_PAYMENT_SUCCEEDED`, `TASTY_PAYMENT_FAILED`,
`TASTY_PAYMENT_INITIATED`.

Every one of the 5 documented flows is built from those constants. So **the documented state machine
describes a system that does not exist**; the real transitions are:

```
HTTP transfer:    INITIATED ──────────────────────────────────► COMPLETED | FAILED
UP transfer:      INITIATED → BALANCE_ADJUSTMENT_DEBIT_INITIATED → …_DEBIT_COMPLETED
                            → …_CREDIT_INITIATED → …_CREDIT_COMPLETED → LEDGER_POSTED → COMPLETED
                  (credit fails) → …_CREDIT_FAILED → …_DEBIT_REVERSAL_INITIATED
                            → …_REVERSAL_COMPLETED → FAILED | …_REVERSAL_FAILED (manual)
```

`fromValue()` maps anything unparseable to `UNKNOWN` rather than failing — so a hand-edited status
column degrades quietly. Three sibling enums (`TastyfxTransferRequest.Status`,
`CurrencyConversion.Status`, `SettlementBatch.Status`) repeat the same shape; only
`CurrencyConversion` exposes intent-named mutators (`markAsTastyPaymentSucceeded()` etc.) instead of
a raw setter, and it too has a comment-only flow spec.

### 3.2 SAGA DETECTED — `BalanceAdjustmentService`, the "UP" transfer flow

`[OBS]` The newest flow (`POST /api/clients/up-funds-transfer`) abandons synchronous ledger posting
for an asynchronous request/response saga over AMQ `mario`:

```
initiateBalanceAdjustment  →  publish debit Request      (com_ig_trade_v1_balance_adjustment_request)
                    ┌─ handleDebitSuccess   → publish credit Request
  response topic ───┤
                    └─ handleDebitFailure   → publish FAILURE WebMessage, stop

                    ┌─ handleCreditSuccess  → post inter-account ledger → LEDGER_POSTED
                    │                       → publish SUCCESS WebMessage → COMPLETED
                    └─ handleCreditFailure  → publish reversal Request (compensation)
                                            → handleReversalSuccess → FAILED
                                            → handleReversalFailure → "MANUAL INTERVENTION REQUIRED"
```

This is the only genuinely compensating flow in the service. Mechanisms and gaps:

- **Routing is by DB status, not by message content** `[OBS]`.
  `BalanceAdjustmentResponseListener.determineResponseType(response, currentStatus)` switches on the
  funds-transfer row's *current* status to decide whether an incoming response is a debit, credit or
  reversal reply. `[INF]` This accidentally provides redelivery protection — a replayed debit
  response arriving at status `CREDIT_INITIATED` is routed to `handleCreditSuccess`, whose
  `getByCreditBalanceAdjustmentId(debitId)` finds nothing → NPE → swallowed. So no double credit,
  but the mechanism is a lookup miss rather than an idempotency check. If status has already advanced
  to `COMPLETED`, `determineResponseType` throws `IllegalStateException` → swallowed → dropped.
- **Dual write inside the transaction** `[OBS]`. Every handler is `@Transactional` and calls
  `balanceAdjustmentPublisher.sendBalanceAdjustmentRequest(...)` / `publishWebMessage(...)` *inside*
  it. The `JmsTemplate` is not `sessionTransacted`, so the message leaves immediately. `[INF]`
  Commit failure after publish ⇒ an order-server debit request with no DB record; and because
  `entityManager.flush()` flushes but does not commit, a **fast response can arrive before the
  initiating transaction commits** — `findOne`/`findBy*` return `null`, `toFundsTransfer(null)`
  NPEs, and the response is swallowed. The saga then hangs forever (no scheduled sweeper).
- **Non-deterministic correlation ids** `[OBS]`:
  `fundsTransferId + "-" + type + "-" + UUID.randomUUID()…substring(0,12)`. Because they embed a
  random component they cannot be used to detect retries; and
  `ClientFundsTransferAdapter.getByBalanceAdjustmentId` recovers the phase by **substring matching
  the id** (`contains("-debit-")`, `"-credit-"`, `"-reversal-"`), making the string format
  load-bearing with an `IllegalArgumentException` fallback.
- `handleCreditSuccess` publishes the SUCCESS `WebMessage` **before** setting `COMPLETED`, so the
  client-facing LightStreamer notification is built from a row whose status is `LEDGER_POSTED`.

### 3.3 IDEMPOTENCY DETECTED — four mechanisms, three failure policies, no shared design

| # | Mechanism | Scope | Failure policy | Notes |
|---|---|---|---|---|
| 1 | `transfer_rate_limit` Oracle `MERGE` | per `from_account`, 30 s window | **fail-OPEN** | see below |
| 2 | `paymentsPort.checkAndStoreLedgerReference` | remote lock in payments service | **fail-CLOSED** (throws → HTTP 429) | skipped entirely when `sourceAccount.isExternalBrokerAccount()` |
| 3 | `FundsTransferCompletionService` status check | Kafka `TastyPayment` COMPLETED events | n/a | the only *explicit* Kafka dedup guard |
| 4 | `BatchIdGeneratorService` previous-batch check | settlement batches | n/a | **unreachable — see §2.2** |

**(1) The DB rate limiter** — genuinely clever, and the closest thing to a designed duplicate guard:

```sql
MERGE INTO transfer_rate_limit trl USING (SELECT :fromAccount FROM DUAL) src
  ON (trl.from_account = src.from_account)
WHEN MATCHED THEN UPDATE SET trl.last_transfer = SYSTIMESTAMP
   WHERE trl.last_transfer < SYSTIMESTAMP - NUMTODSINTERVAL(:windowSeconds,'SECOND')
WHEN NOT MATCHED THEN INSERT (from_account, last_transfer) VALUES (src.from_account, SYSTIMESTAMP)
```

`rowsAffected > 0` ⇒ acquired. Run in `@Transactional(REQUIRES_NEW)`, so the commit is immediate and
the second of two concurrent requests genuinely sees the new timestamp and gets 0 rows. Correct.

Three caveats `[OBS]`:
- **TOCTOU by design.** `RateLimitSpecification` (order 0) calls the read-only `isRateLimited()`, but
  the `MERGE` only happens in `tryAcquire()` *after all 18 specifications have run*. The window
  between check and acquire spans the entire upstream fan-out. The `MERGE` closes it correctly, so
  this is wasted work rather than a correctness hole — but the early check buys nothing.
- **Fail-open on error**: `catch (Exception e) { log.error("… allowing transfer (fail-open)"); return true; }`.
  A duplicate-suppression control that disables itself when the database is unhealthy.
- **Wrong error surfaced**: a rate-limited double-click returns `FUNDS_TRANSFER_SERVICE_UNAVAILABLE`,
  so a client double-submit is indistinguishable from an outage in both the response and the metrics.
- Live-tunable via `RateLimitMbean.updateWindowSeconds` — honestly documented as
  *"Resets to application.yml value on restart."* and per-JVM only.

**(3) The good one** `[OBS]`, and the only place duplicate handling is stated as intent:
```java
if (FundsTransfer.Status.COMPLETED.name().equals(fundsTransfer.status())) {
   log.info("Funds transfer completed previously, skipping processing of duplicate kafka message, sourceId={}", sourceId);
   return;
}
```
Read-check-act with no lock or transaction, and status-only: any non-`COMPLETED` status re-runs the
whole flow, re-posting ledgers and re-calling `performDeposit`.

### 3.4 SPECIFICATION PATTERN DETECTED ×5 — five parallel implementations

`[OBS]` Five independent specification families, each with its own interface, its own `AndSpecification`,
and its own `ValidationResult`:

| Family | Interface | Composition | Count |
|---|---|---|---|
| omnibus | `Specification` | hand-chained `.and()` in the constructor | 4 used (+2 helpers) |
| interaccount | `InterAccountSpecification` | **Spring-injected `List<>` ordered by `@Order`** | 18 |
| tastyfx | `TastyfxTransferSpecification` | hand-chained `.and()` in the constructor | 7 |
| tasty-payments | `…domain.specification.{deposit,withdrawal,settlement}` | separate module | — |
| currency-conversion | `CurrencyConversionSpecification` | `static build()` factory | 1 |

**Three distinct `ValidationResult` enums** exist (`…domain.ValidationResult` with 2 constants,
`…validation.ValidationResult` with **47**, `…tasty.payments.domain.ValidationResult` with 6), all
compared by `!=` / `.equals` against a `SUCCESS` constant. Being enums, reference comparison is safe.

**Order collisions in the injected chain** `[OBS]`:
- `BaseCurrencySpecification` and `RateLimitSpecification` are **both** `@Order(HIGHEST_PRECEDENCE)`
- `NonBrokerIgcrySpecification` and `IRASpecification` are **both** `@Order(HIGHEST_PRECEDENCE + 6)`

`InterAccountSpecificationOrderingTest` asserts the exact class at each of indices 0–17, with the
comment *"order of validators matter, because it may happen that your request will be rejected by
another validator and provide an unrelated response"*. `[INF]` Spring's `AnnotationAwareOrderComparator`
is a stable sort, so ties fall back to bean-registration order = classpath scan order. The pinned
test is therefore asserting an ordering that is **not fully determined by the annotations** — it can
diverge between machines/JDKs, and prod validation order can differ from what the test locks in.

**Dead specification** `[OBS]`: `domain/…/specification/interaccount/CurrencyConversionSpecification`
implements `InterAccountSpecification` but has **no `@Component`**, so it is never in the injected
list, and nothing else references it (the identically-named class used by
`CurrencyConversionDomainConfiguration` lives in the `currency-conversion` module in a different
package). Consistent with the ordering test asserting exactly 18 beans.

### 3.5 CONCURRENCY / DEPLOYMENT MODEL — leader election gates all async work

`[OBS]` `LeaderElectionConfiguration` imports mantis `ZookeeperConfiguration` +
`LeadershipElectionInBlueGreenConfiguration`; latch id `funds-transfer-service-leader-election`,
path `/application/funds-transfer-service/leader`, blue/green state root
`/bgstate/tomcat/funds-transfer-service/live`.

Every Kafka container is created with `container.setAutoStartup(false); // Only leader will listen to
messages`, and the JMS container likewise. `KafkaLeaderElectionListener.onTakeLeadership()` starts
them; `onAbandonLeadership()` stops them. **HTTP endpoints are not gated** — all nodes serve HTTP.

Notable details:
- `JmsListenerEndpointRegistry` is injected into `KafkaLeaderElectionListener` and **never used**.
  `[INF]` Harmless today precisely because there are **zero `@JmsListener`/`@KafkaListener`
  annotations in the codebase** (verified) — every container is hand-built. But `@EnableJms` is on
  `BalanceAdjustmentConfiguration`, so if anyone adds a `@JmsListener` it will start on **every**
  node, outside leader election, and silently process messages twice.
- `container.start()` / `stop()` are individually wrapped in `try/catch` that logs
  *"Unable to start container"* (the same message on the stop path — copy-paste). A container that
  fails to start is logged and skipped, so the node holds leadership while consuming nothing.
- `ProducerConfig.RETRIES_CONFIG, 0` on **every** Kafka producer (`buildKafkaProperties`) — currency
  conversion, tasty payment, crypto cash ledger and web-message events are published with **no
  retries**. A transient broker error loses the event.
- Every listener `extends java.util.Observable` `[OBS]` — deprecated, no observers ever registered
  anywhere. Cargo-culted across all 8 listeners.

### 3.6 AUDIT MECHANISM DETECTED — SSO username pushed into the Oracle session

`[OBS]` The most non-obvious mechanism in the repo, in the typo'd package
`integration/…/service/**adap**/` (note: sibling to the real `adapter/`):

```java
@AfterReturning(value = "execution(java.sql.Connection javax.sql.DataSource.getConnection(..))",
                returning = "connection")
public Connection prepare(Connection connection) { oracleSessionIdentifierFunction.execute(connection); }
```
```java
Principal principle = RequestContext.getPrinciple();          // SSO filter ThreadLocal
if (principle != null && principle != OUTAGE_BYPASS_PRINCIPAL) {
   CallableStatement cs = connection.prepareCall("{ call DBMS_SESSION.SET_IDENTIFIER(?) }");
   cs.setString(1, principle.getName()); cs.execute();
}
```

The `R__*_audit_trigger.sql` / `R__*_gg_trigger.sql` scripts then pick this up as `AUD_USER_ID`, so
Oracle audit rows and GoldenGate replication carry the human SSO username. This is why
`DataSourceConfiguration` wraps the JNDI `DataSource` in a `DelegatingDataSource` — the class Javadoc
explains it: *"it doesn't work with the JNDI DataSource, so it needs to be wrapped"*.

`[INF]` **Audit-integrity gap.** `RequestContext.getPrinciple()` is request-scoped ThreadLocal state.
On Kafka/JMS listener threads and inside `IGClusterDetails`' scheduled thread there is no principal,
so `SET_IDENTIFIER` is **not called** — and because `DBMS_SESSION.SET_IDENTIFIER` is session-scoped
and persists for the pooled physical connection, the connection retains whatever identifier the
*previous HTTP request* set. Async money movement (the whole balance-adjustment saga, all settlement
processing) is therefore liable to be attributed in the audit trail to an unrelated named user.

Also surfaced here: `OUTAGE_BYPASS_PRINCIPAL` — the IG SSO filter has an outage-bypass path, so
during an SSO outage requests proceed with a sentinel principal and no audit identifier.

### 3.7 Custom string primary keys — 4 near-identical generators

`[OBS]` `ClientFundsTransferIdGenerator`, `TastyPaymentIdGenerator`, `TastySettlementBatchIdGenerator`,
`TastyCurrencyConversionIdGenerator` (plus `BatchIdGeneratorService`) are byte-for-byte identical
`SequenceStyleGenerator` subclasses differing **only in a two-character prefix** — `FT`, `TP`, `TS`,
`CC`, `TB`. Each does `Long.toString(seq, 36)`, `leftPad(…, 8, "0")`, `toUpperCase()`, prefix.

`[INF]` Result is exactly **10 characters** (`FT0000001Z`), and `client_funds_transfer.id` is
`VARCHAR2(10)` — a perfect fit with **zero headroom**. `leftPad` does not truncate, so past 36⁸
(≈2.8 × 10¹²) sequence values ids become 11 chars and inserts fail. Not a near-term risk, but any
change to prefix length or padding breaks the schema silently.

---

## 4. Integration surface

### 4.1 Outbound HTTP — three client stacks, one with no timeout

| Client | Stack | Connect / read timeout |
|---|---|---|
| AccountMaintenance, ClientMaintenance, LedgerPosting, Payments, TaxWrapper, CardPayments | `@SingleSignOnFeignClient` (Spring Cloud Feign) | **none set — Feign defaults 10 s / 60 s** |
| AccountValuationQuery, ExternalLedger, ExternalToken, CryptoCashBalance, JwtService | hand-built `Feign.builder()` | 2 s / 2 s |
| Tasty, TastyFX, IgOne | Feign + OkHttp via HTTP proxy | OkHttp defaults 10 s each phase, **no `callTimeout`** |

`[OBS]` `FeignConfig` declares `@Bean @Scope("prototype") Feign.Builder feignBuilder()` with **no
`.options(...)`**. In Spring Cloud Dalston this overrides `FeignClientsConfiguration`'s
`@ConditionalOnMissingBean` builder, and no `Request.Options` bean exists in the client contexts.

`[OBS]` **Hystrix is off**: `ig.feign.hystrix.enabled: false`, while `application.yml` still carries
`hystrix.command.default.execution.isolation.thread.timeoutInMilliseconds: 5000` — dead config.
So there is **no circuit breaker anywhere**. `[INF]` A slow LedgerPosting or AccountMaintenance can
hold a Tomcat worker up to 60 s; `doClientFundsTransfer` makes many such calls per request through
the 18-specification chain, so upstream latency converts directly into thread-pool exhaustion.
`readme.md`'s claim of *"Hystrix circuit breakers"* is stale.

### 4.2 Kafka — two consumer groups on the same topics, processing everything twice

`[OBS]` Topics are subscribed by **regex `Pattern.compile(topicName)`**, not by name. `[INF]` A
typo'd or absent topic silently consumes nothing (pattern subscriptions never fail), and any regex
metacharacter in a topic name would widen the match.

Group ids come from `GROUP_ID_CONFIG`, and there are **two different values**:

| Container | Topic property | Group id | Listener |
|---|---|---|---|
| `tastyPaymentKafkaMessageListenerContainer` | `tasty-payment.name` | `<app>_TASTY` | `TastyPaymentEventListener` |
| `fundsTransferServiceTastyPaymentListenerContainer` | **same topic** | `<app>` | `TastyPaymentFTSEventListener` |
| `currencyConversionStatusKafkaMessageListenerContainer` | `currency-conversion.name` | `<app>_TASTY` | `CurrencyConversionEventListener` |
| `fundsTransferServiceCurrencyConversionListenerContainer` | **same topic** | `<app>` | `CurrencyConversionFTSEventListener` |

`[INF]` Two independent consumer groups on the same topic inside one JVM ⇒ **every tasty-payment and
currency-conversion event is delivered twice and processed by two different code paths**. The FTS
listeners filter on `FUNDS_TRANSFER_SOURCE.contains(event.getSource())`, so the split is by event
`source`, not by group — this is the seam between the older `tasty/` pipeline and the newer
`inbound/kafka/` + `event/processor/` pipeline (§5), running side by side.

Settlement batch runs V1 and V2 containers simultaneously (different topics), with
`FeatureFlagService.isNewSettlementBatchTopicEnabled()` deciding which one actually processes:
`SettlementBatchEventListener` acts only when the flag is **false**, `…V2` only when **true**.
`[OBS]` Default is `true` in `application.yml` and LIVE. The V1 container still runs and still
commits offsets while doing nothing, so flipping the flag back resumes from the current offset,
having silently skipped everything in between.

`[OBS]` **The feature flag is in-memory per JVM.** `FeatureFlagConfiguration` is a plain
`@ConfigurationProperties` bean (registered via `ApplicationConfiguration`'s
`@EnableConfigurationProperties`), mutated through `FeatureFlagMbean.enableV2TopicProcessor()`.
`[INF]` Flipping it on one node does not affect the other, and it silently reverts to the YAML value
on restart — so on a blue/green flip or leader failover the **settlement-batch processing version can
change underneath you**.

### 4.3 Brokers and topics `[OBS]`

- **AMQ (`mario`)** — publishes `com_ig_trade_v0_legacy_ledger_transaction` and
  `com_ig_trade_v1_balance_adjustment_request`; consumes `…_balance_adjustment_response` via a
  **shared durable topic subscription** (`setSubscriptionShared(true)`, `setSubscriptionDurable(true)`,
  subscription name `<responseTopic>/<applicationName>`) — belt-and-braces with leader election.
- **AMQ (`sonic`)** — `com_ig_platform_v0_communication_event` (Salesforce client comms).
- **Kafka (`peach`)** — 7 topics, all `auto-offset-reset: latest`. `[INF]` A fresh consumer group, or
  a gap longer than retention, **skips** events rather than replaying them.
- 8 broker connections are configured in `amq-DEV.properties`; only `mario`, `sonic`, `kazooie` are
  enabled in `application.yml`. `banjo`, `clank`, `luigi`, `ratchet`, `tails` are dead config.

### 4.4 Tasty auth token `[OBS]`

`AuthTokenGenerator` mints an **HS512 JWT** from the config secret (`Keys.hmacShaKeyFor(secret.getBytes(UTF_8))`
— which requires the deployed secret to be ≥ 64 bytes or it throws `WeakKeyException`), 2-hour
expiry, refreshed every 30 min at a 50 % threshold. It then re-parses the token it just created:

```java
// Just for debug purpose, remove when not necessary
... log.info("iat={} eat={}", iat, eat);
```

`[INF]` Left in production; verifies the signature on every generation for a log line.

The Tasty Feign client sets `Logger.Level.FULL` `[OBS]`, which logs request/response **headers and
bodies** — including the `Authorization` header injected by `AuthTokenInjector`. Feign logs at DEBUG,
and prod/test root level is `info`, so this is dormant in LIVE. **But** UAT's root level is `debug`,
and every Logback config carries `<configuration scan="true" scanPeriod="1 minutes">` — so a
level change on a prod box puts **Tasty JWTs and full payment payloads into the log file within a
minute**, no restart needed.

---

## 5. Two eras in one codebase `[INF]`

The `integration` module contains two complete, coexisting pipelines. The evidence:

| | Older `tasty/` era | Newer FTS era |
|---|---|---|
| Listeners | `tasty/inbound/kafka/*EventListener` | `inbound/kafka/*FTSEventListener` |
| Processors | `tasty/event/processor/*EventProcessor` | `event/processor/*EventHandler` |
| Kafka group | `<app>_TASTY` | `<app>` |
| Feign | `tasty/outbound/http/` + OkHttp + proxy | `outbound/http/` + `@SingleSignOnFeignClient` |
| Money movement | synchronous `postToLedgerTransactions` | asynchronous balance-adjustment saga (§3.2) |
| Endpoint | `POST /api/clients/funds-transfer` | `POST /api/clients/up-funds-transfer` |
| Settlement | V1 `SettlementBatch`, `partner`/`region` hardcoded `"IG"`/`"GBR"` | V2 `Batch`, loops `RegionalObligation`s per region |

The V1→V2 settlement rationale is legible from the code `[OBS]`: `process(v1 SettlementBatch)` opens
with `String partner = "IG"; String region = "GBR";` as **hardcoded locals**, so it can only ever
settle the UK/IG region. `process(v2 Batch)` reads `event.getPartner()` and iterates
`event.getRegionalObligations()`, branching to `postThirdPartyTransferLedger` for TastyFX (US) vs
`postCustodianTransferLedger` otherwise. V2 exists because V1 could not express multi-region
settlement.

The newer pipeline is visibly unfinished `[OBS]` — `TastyPaymentEventHandler`:

```java
case DEPOSIT:
   // handle deposit
   break;                                   // deposits are not handled at all
...
case FAILED:
   // TODO - What should happen here?       // Tasty withdrawal FAILURE is silently ignored
   break;
```

`[INF]` The `FAILED` gap matters: `doClientFundsTransfer` marks the row `COMPLETED` **before** the
Tasty deposit/withdrawal is confirmed (§2.5 step 7), so a Tasty rejection arrives as a
`TastyPayment` event with status `FAILED`, hits an empty `case`, and nothing reverses the IG-side
ledger. The same file also carries `import static javax.management.remote.JMXConnectionNotification.FAILED;`
— an unused JMX constant imported into a payment handler (an IDE auto-import accident; the `case`
labels resolve against the Avro enum).

---

## 6. Testing and pipeline

`[OBS]` 3 Cucumber runners (`Component`, `Functional`, `Acceptance`), Mockito 4.5.1 + mockito-inline,
JUnit 5 with the vintage engine, `make-it-easy` object makers, WireMock via
`spring-cloud-contract-wiremock`, embedded Artemis + HSQLDB/H2 for functional runs.

`docs/dod-coverage.md` is an unusually **honest** in-repo document and should be read before
re-deriving anything. It states plainly: *"Acceptance tests (`tests/acceptance/`) — placeholder tests,
end-to-end HTTP tests for transfer flows pending"*, and *"Component tests … placeholder tests, to be
expanded."* Real automated coverage of the money paths = **50 domain + 118 integration unit tests**.
The single functional test checks `/monitor/version`; the two post-deployment tests also check
`/monitor/version` — justified in the doc because everything else is behind SSO.

Pipeline (`.gitlab-ci.yml`, 12.5 KB, includes shared `ci-pret.yml` templates) `[OBS]`:
- `workflow: rules: - when: always` — deliberately overrides ci-pret so **pipelines run on all
  branches**. `GIT_SSL_NO_VERIFY: "true"` globally.
- `MAVEN_CLI_OPTS` carries `-DskipITs=true` and `-Dmaven.install.skip=true` — **integration tests
  never run in CI**, only surefire unit tests.
- Coverage gate is a hand-rolled bash loop summing columns 4/5 of every `jacoco.csv` — i.e.
  **instruction** coverage, project-wide, threshold 75.
- **Doc/config mismatch:** `docs/dod-coverage.md` claims the coverage gate is
  `allow_failure: true` "during ramp-up". It is not — `allow_failure` appears only on the two
  Gatling jobs (lines 216, 229). **The coverage gate blocks the pipeline.**
- **`SNYK_POLICY_PATH: "./.snyk"` but there is no `.snyk` file in the repo.** Masked only by
  `SNYK_ALLOW_FAILURE: "true"`. The doc claims a `.snyk` policy file exists.
- `anfr/anfr.yml` is an empty stub (`exempted_from:` / `run_extra:` with no values).
- DEMO+LIVE share one CRF (`DEMO_AND_LIVE_COMBINED_CRF: "true"`) with a 3670 s lead time;
  `ROLLING_DELAY: "1"` minute between nodes.
- `tests/pom.xml` comments still describe **Bamboo** (*"the bamboo plan runs the acceptance tests
  against that branch"*) though the repo is on GitLab CI.

---

## 7. Odds and ends worth knowing

`[OBS]`
- **`tests/src/main/java/com.iggroup.wt.funds.transfer.service/`** — a directory literally named
  with **dots** instead of nested folders, holding `FundsTransferServiceRunner.java`. Maven passes
  explicit source file lists so javac accepts it, but it breaks IDE package resolution and any tool
  that infers packages from paths. It is also the file holding the Oracle credential (§2.6).
- **Three mock controllers ship to production, unconditionally.** `MockController` (`/mock/**`),
  `MockDepositController` (`/mock/deposit/**`), `MockCashRestrictionsController`
  (`/mock/cashRestrictions/**`). There are **zero `@Profile` annotations in the whole codebase**, so
  these register in LIVE. They are behind SSO, but `POST /mock/publishClientComms` can fabricate a
  payment-notification `GenericEvent` to Salesforce for **any** account id/amount/status, and
  `POST /mock/card/trigger/tastyEvent` injects arbitrary payment events into the pipeline. A mock
  OAuth token endpoint (`POST /common/oauth2/v2.0/token`) is also mapped.
- **`FundsTransferService` is a 577-line god-service with a 30-parameter constructor**, composing all
  three HTTP-facing specification families and orchestrating 6 distinct transfer flows.
- **`FundsTransfer.websiteId` is dead**: no `website_id` column on `client_funds_transfer` (V7),
  no field on `ClientFundsTransferEntity`, never set in `upsert`, never read in `toFundsTransfer`,
  never populated by any builder call. The public `websiteId()` accessor always returns `null`.
- `findOne(id)` / `findBy*` (Spring Data 1.x) return **null** when absent, and every one feeds
  straight into `toFundsTransfer(entity)` which dereferences it. Unknown/early ids ⇒ NPE ⇒ swallowed
  by the listener (§2.1). This is the concrete manifestation of the §3.2 commit race.
- Two write paths for the same table: `clientFundsTransferPort.upsert(...)` everywhere, versus
  `updateStatusForTastyfxTransfer(id, status)` in the TastyFX completion branch.
- `getClientAccount(...)` throws a **bare `RuntimeException("Account not found in Client Accounts")`**
  which the `@ExceptionHandler(Exception.class)` turns into HTTP 500 `FUNDS_TRANSFER_FAILED`.
- `IGClusterDetails`' constructor starts a daemon `ScheduledExecutorService` that **reads a file
  (`OVlivedark`) from disk once per second, forever**, to track blue/green light/dark state. Never
  shut down.
- Full request DTOs are logged at INFO on every money endpoint
  (`log.info("Received request for Client Funds Transfer request={}", fundsTransferRequestDTO)`) —
  account ids, amounts, FX rates in application logs.
- Error responses are uniform `FundsTransferResponseDTO` for *all* controllers via one
  `@ControllerAdvice`, including the Tasty endpoints that otherwise return `TastyResponseDTO<T>` —
  so error payload shape differs from success payload shape on those routes. `IllegalArgumentException`
  → HTTP 400 with `ex.getMessage()` echoed to the caller.
- `flyway.baseline-on-migrate: true` with `enabled: true` — migrations run on **every** node at
  startup (both blue and green); relies on Flyway's own lock. A `FlywayMbean` exists for manual
  intervention.
- `readme.md` is `[OBS]` **AI-generated and partly stale** — it self-identifies
  (*"Documentation Version: Generated with Claude Code"*), claims Hystrix circuit breakers (disabled),
  claims "real-time fraud detection and risk assessment" and "multi-level approval workflows for
  high-value transfers" (**no such code exists**), and lists a `FUNDS_TRANSFER` table that is
  superseded by `CLIENT_FUNDS_TRANSFER`. Its integration/broker/topic inventory, however, is accurate.
- `docs/src/` holds a `.docx` (`Omnibus.docx`), PlantUML sources, and two PNG flow diagrams for
  TastyFX — worth opening before re-deriving those flows.

---

## 8. Suggested reading order for the next person

1. `docs/dod-coverage.md` — accurate, honest, and explains the test/pipeline posture.
2. `docs/src/tastyfx/ICT.md` + the two PNGs — the TastyFX flows.
3. `domain/…/FundsTransferService.java` — every HTTP money path starts here.
4. `integration/…/balance/BalanceAdjustmentService.java` + `listener/BalanceAdjustmentResponseListener.java`
   — the newest and most interesting design (§3.2).
5. `integration/…/tasty/event/processor/NetSettlementEventProcessor.java` +
   `tasty/service/BatchIdGeneratorService.java` — settlement, and the §2.2/§2.3 findings.
6. `integration/…/tasty/config/KafkaConfiguration.java` — 560 lines, the whole async topology.
7. `integration/…/adap/` (both files) — the audit mechanism nobody would guess (§3.6).
8. Treat `readme.md` as an orientation sketch, not a specification.

## 9. Open questions for the owners `[UNK]`

1. Is the `KafkaErrorHandler` swallow deliberate (upstream is assumed to re-drive) or an oversight?
   Nothing else in the repo compensates for a dropped event.
2. Should `generateNextBatchId` be receiving `clearingBatchId` rather than `igBatchId`? Passing the
   Tasty id would make the dedup branch reachable — but would make the `else if` guard throw, so the
   fix is not a one-liner.
3. Is `markBatchProcessingAsComplete()` after a failed validation intended, or should the
   `INCOMPLETE` status survive?
4. Which team owns the BOLA exposure (§2.4) — is this in scope for the same remediation programme as
   `payments-gateway`?
5. Are the `/mock/**` controllers relied on operationally in LIVE, or can they be `@Profile`-gated?
6. Is the V1 settlement listener still needed, given the flag has defaulted to V2 for some time?
