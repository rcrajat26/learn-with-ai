# payment-listeners — Discovery Record

**Analysed:** 2026-09-05
**Repo:** `_Codes/payments/payment-listeners` (read-only)
**HEAD:** `703bdb3` (2026-06-16) · 174 commits · 3.5 MiB pack · `master`
**Scale:** 34 main + 42 test Java files, 10 Maven modules, 4.6 MB working tree
**Legend:** `[OBS]` observed in code · `[INF]` inferred · `[UNK]` unknown / needs owner input

---

## 1. What this service is

A **Spring Boot WAR on Java 8**, deployed to on-prem Tomcat under context `/payment-listeners`,
blue/green (`IS_BLUE_GREEN: "true"`). It is not a service in the request/response sense — it is a
**message-driven side-effect emitter**: it consumes payment events and turns them into two outbound
effects only.

| Effect | Downstream | Protocol |
|---|---|---|
| Send a templated customer email | ExactTarget / Salesforce Marketing Cloud | SOAP (CXF, WS-Security UsernameToken), via `dealingproxycore:8080` |
| Push a screen message to a logged-in client | InVision (`mrds001:7091`) | proprietary TCP, base64 payload, `fid=10002` |

It owns **no database of its own writes** — the Oracle JNDI datasource
(`ig/jdbc/datasource/payment_listeners_con`) is consumed by the framework's `TranslationCache`
(language strings, currency names, reject codes) `[INF from usage]`, not by any code in this repo.
There is not one `@Transactional`, JPA entity, or repository in the module. `[OBS]`

**ARCHITECTURE DETECTED — "thin adapter on a rented framework"** `[OBS]`
Almost all machinery lives in **`com.ig.enterprise.message.bus:ig-messaging-tomcat-framework`
(v210427.063641)** — an internal Fiorano/JMS listener host. This repo contributes only
`ListenerInterface` implementations plus YAML declaring them. The parent POM is
`jms-spring-boot-parent` (v200722), i.e. the *build* is also rented.

The application class is a 9-line shim: `Application.main` → `prepareEnvironment()` →
`SpringApplication.run(IgMessagingApplication.class)` — the framework's class, not this repo's.
`ApplicationStartupListener` implements the framework's startup hook, autowires three framework
services (`MessageInjector`, `MessageListenerService`, `BrokerService`) — and its
`onApplicationStartup()` body is **empty**. `[OBS]` Three beans injected, zero used: an
abandoned extension point.

### Module map `[OBS]`

| Module | .java (main/test) | Role |
|---|---|---|
| `impl` | 34 / 34 | all listeners, Marketing Cloud SOAP client, FEMessage, observability |
| `integration-test` | 0 / 2 | Testcontainers Kafka + Schema Registry, the *only* end-to-end test |
| `acceptance` | 0 / 5 | Cucumber; one scenario: `/monitor/version` returns 200 |
| `post-deployment-tests` | 0 / 3 | same check again, via raw `SimpleHttpClient` |
| `resource` | 0 | env properties, listener YAML, logback, invision.ini, certs |
| `war`, `docs`, `coverage`, `endorsed` | 0 | packaging / diagrams / jacoco aggregation / Tomcat endorsed jars |

---

## 2. The central finding: two generations of pipeline, drifting apart

**DUAL-PIPELINE DETECTED** `[OBS]` — every business function exists **twice**, once on JMS
(Fiorano, ~2013-era) and once on Kafka (added 2025-06 / 2025-08). Both are live in LIVE.

| Function | Legacy (JMS/Fiorano) | New (Kafka `peach`) |
|---|---|---|
| Email | `EmailsListener` ← `IG.3G.EMAILS.1` | `KafkaEmailsListener` ← `com_ig_payments_v1_email_event--{env}--pii` |
| Web message | `WebMessageListener` ← `IG.3G.WEB_MESSAGES.1` | `KafkaWebMessageListener` ← `com_ig_payments_v1_webmessage--{env}` |

Git provenance `[OBS]`: `865f650` (2025-06-11, AP-2650) added the Kafka email consumer;
`cb97272` (2025-08-20, AP-4699) added the Kafka web-message consumer. Both listener pairs share
the *same* `MarketingCloudServiceFactory` / `InvisionService` downstream, so a message arriving on
both transports fires the effect twice with no cross-transport dedup. `[OBS]`

`[UNK]` Whether producers currently dual-publish. If they do, customers get two emails per event —
nothing in this repo would prevent or detect it (see §5, no idempotency anywhere).

### 2a. The Kafka web-message path emits a *different wire format* — with evidence

`WebMessageListener` (JMS) delegates reply construction to **`FEMessage`** (711 lines), which for a
FundAccount message produces `createArsResponse` / `createMessageResponse`:

```
"MSG status=" + messageId.substring(0,2) + "|" + <translated text>
```

A captured production fixture is checked into the repo —
`impl/src/test/resources/data/webMessagingData.xml`, a real UAT capture from 2019-03-22. Its
base64 `msg` field decodes to: `[OBS]`

```
MSG status=13|Sorry, we are unable to accept this request at the moment. Please call us to fund your account.
```

for an input with `<MessageId>132999</MessageId>`. So the first two digits of the message id **are
the outcome code** — `13` = rejection, `12` = success — and the body is bare translated prose.

`KafkaWebMessageListener.generateFundAccountReply()` instead hand-rolls: `[OBS]`

```java
reply.append("MSG").append(" ")
     .append("status").append(fieldDelim).append("12").append(recordDelim) // Success status
     .append("DisplayMessage").append(fieldDelim).append(displayMessage).append(recordDelim)
     .append("AccountId").append(fieldDelim).append(webMessage.getAccountId()).append(recordDelim)
```

Three concrete divergences:
1. **`status` is hardcoded `"12"`** — the success code. A funding *rejection* (msgId `13xxxx`)
   arriving over Kafka is reported to the client's screen as a **success**. `[OBS]`
2. **Field names are added** (`DisplayMessage=`, `AccountId=`, `BankReference=`) where the JMS
   payload carries bare text. Notably `FEMessage` holds an *unused* constant
   `BACK_ONLY_CLOSE_PREFIX = "DisplayMessage="` `[OBS]` — the prefix belongs to a different,
   older channel shape, not to this one.
3. **`responseType` is ignored.** `FEMessage.createReply` switches on `ALT` / `MSG` / `INV` / `ARS`
   (the 2019 fixture is `ARS`); the Kafka path always emits `MSG`. The Avro `WebMessage` schema
   *has* a `responseType` field — the test sets it to `"MSG"` — and the listener never reads it. `[OBS]`

The Kafka format is **canonicalised in the acceptance test**
(`CashFundAccountWebMessageIntegrationTest`, `d2e2598`), which asserts the exact string
`MSG status=12|DisplayMessage=…|AccountId=T2325|BankReference=REF-1|`. `[OBS]` The test locks in
the divergence rather than detecting it — it was written from the implementation, not from the
legacy contract.

`[UNK]` Whether InVision / the front end tolerates both shapes. If it parses positionally after
`status=`, the Kafka reply renders the literal text `DisplayMessage=…` to the customer.

### 2b. Reliability guarantees differ per transport, in the direction you would not want

`resource/src/main/properties/common/listeners/emails.yml` — the JMS email listener declares a
genuine reliability envelope `[OBS]`:

```yaml
messageLogging:
  sensitiveFields: 'To'
  obfuscateSensitiveMessage: true
  maskStrategy: '*****'
inbound:
  clientAcknowledge: true
  retryAttemps: 2
  enableDeadLetterQueue: true
  fmq: { deadLetterQueue: 'SYSTEM.DEAD.LETTER.QUEUE' }
```

The Kafka path has **none of it**. `ConfigManager` builds containers by hand: `[OBS]`

```java
consumerProperties.setProperty(ENABLE_AUTO_COMMIT_CONFIG, "true");
consumerProperties.put(AUTO_OFFSET_RESET_CONFIG, "latest");
...
container.setAckMode(AbstractMessageListenerContainer.AckMode.RECORD);
container.setErrorHandler(new KafkaErrorHandler());
container.setAutoStartup(true);
```

**Consequences:**
- `enable.auto.commit=true` **and** `AckMode.RECORD` are contradictory — with broker-side auto
  commit the container's ack mode is moot. Offsets advance on a timer, independent of whether the
  email was actually sent. `[OBS→INF]`
- `KafkaErrorHandler` is 8 lines: `log.error(...)`. Nothing else. `[OBS]` So a failed email is
  logged once and its offset is committed anyway. **No retry, no DLQ, no alerting hook, no
  poison-message quarantine** — the JMS path's three safety nets all absent.
- `auto.offset.reset=latest` means any consumer-group reset skips the backlog silently rather than
  replaying it (and see §3 — the group id changes on blue/green colour).
- The `sensitiveFields: 'To'` masking is a *framework* feature driven by listener YAML. The Kafka
  listeners are plain `MessageListener` beans outside the framework, so recipient addresses on the
  `--pii` topic get no masking treatment. `[INF]`

Also asymmetric: the JMS listeners are individually gated by
`listener.{Name}.AUTOSTART` per environment (`false` everywhere in DEV), but the Kafka containers
hardcode `setAutoStartup(true)`. `[OBS]` **There is no way to disable a Kafka listener by
configuration** — a DEV box with every JMS listener off still joins the `--demo--pii` topic and
sends live-ish emails.

### 2c. Retry semantics differ, and "not retryable" is retried anyway

Both email listeners share this loop verbatim (copy-paste, not extracted): `[OBS]`

```java
while ((resend = isResendEmail(marketingCloudEmail)) && retryCount++ < maxRetry) {
   Thread.sleep(retryPause);   // retry.delay = 30000
}
```

- `isResendEmail` catches **only `MCRetryableException`**. `[OBS]`
- Attempts are `maxRetry + 1` (send happens in the loop condition before the counter test), so
  `RetryCount: '2'` means three attempts, blocking the listener thread for 60 s. With
  `threadCount: '2'`, two stuck messages stall the entire email pipeline. `[OBS→INF]`
- `emailMessage` is declared, never assigned, then interpolated into the failure log — the warning
  always reads `Failed to send Email after N attempts (null)`. `[OBS]`

`MCExceptionFactory` classifies MC error codes `[OBS]`: maintenance (9), unplanned outage (10),
DB failure (13) → **retryable**; subscriber-processing (18006), invalid subscriber (180008),
invalid trigger-send id (18002) → **not** retryable; **`default` → not retryable**. So the
*majority* of MC failures are non-retryable and escape `isResendEmail` uncaught. What happens then
depends on transport:

- **JMS:** falls to `catch (Exception e) { listenerContext.rollback(); }` → JMS redelivery →
  `retryAttemps: 2` → DLQ. A message the factory explicitly labelled *not retryable* is redelivered
  twice before being parked. `[OBS→INF]`
- **Kafka:** `catch (Exception e) { throw new RuntimeException(e); }` → `KafkaErrorHandler` logs →
  offset already auto-committing → **message gone**. `[OBS→INF]`

`INVALID_SUBSCRIBER_ERROR_CODE = 180008` — the real ExactTarget code is `18008`. `[OBS]` An extra
`0`, so genuine invalid-subscriber responses fall through to `default` (still non-retryable, so the
outcome is accidentally similar — but the WARN/ERROR level and message differ).

**Poison-message handling in the JMS email path is a silent drop**, deliberately: `[OBS]`

```java
try { email = xmlFactory.retrieveObject(message, Email.class, emailUnmarshaller); }
catch (IGException listenerEx) { log.error(...); listenerContext.commit(); return; }
```

`commit()` on a parse failure — unparseable email requests are acknowledged and discarded, never
reaching the configured DLQ.

---

## 3. Blue/green is the load-bearing correctness mechanism — and it is wired twice

**STATE MACHINE DETECTED (deployment-level)** `[OBS]` Both Kafka listeners begin with the same
guard:

```java
if (IGClusterDetails.getLightDarkState().equalsIgnoreCase("dark")) {
   log.info("Ignoring the message as it is dark instance");
} else { ...actually do the work... }
```

This is the **only** thing preventing the standby cluster from sending duplicate customer emails.
It is a runtime string comparison, evaluated per message, against a value read from a file. Notes:

- **Two independent `IGClusterDetails` classes exist.** `[OBS]`
  - `uk.co.igindex.commons.bluegreen.IGClusterDetails` — *static* accessors; used by the listeners'
    guard and by `GroupIdUtil`. From an external library.
  - `uk.co.igindex.igmessaging.observability.logging.IGClusterDetails` — *instance* based, local to
    this repo, feeds the logback `%sm` conversion word. Reads a file named `OVlivedark`
    (overridable via `-Dlight.dark.state.file`) on a **1-second** `scheduleAtFixedRate`, and
    republishes it as the system property `light.dark.state`.

  So the state the logs report and the state the listeners act on come from different code paths.
  `[INF]` They can disagree; a log line saying `service.mode="standby"` is not proof the guard fired.

- `lightDarkState` is written by the scheduler thread and read by logging threads with **no
  `volatile` / no synchronization**. `[OBS]` Benign-ish for a log field, but it is also pushed into
  a global system property.

- **Executor leak on logback reload.** `ServiceModeConverter`'s no-arg constructor does
  `new IGTelemetryClusterDetailsProvider(new IGClusterDetails())`, and `IGClusterDetails`'
  constructor spawns its own `newSingleThreadScheduledExecutor` which is **never shut down**.
  `payment-listeners-logback.xml` sets `scan="true" scanPeriod="1 minutes"` `[OBS]` — every
  reconfiguration instantiates a fresh converter, hence a fresh 1 Hz daemon thread, and the old one
  keeps polling the file forever. `[OBS→INF]`

- `IGTelemetryClusterDetailsProvider` maps `light`/`live` → `active`, `dark` → `standby` for
  telemetry `[OBS]`. Note the listener guard tests only the literal `"dark"`; the provider's
  awareness of a `"live"` synonym implies the file can hold values the guard does not anticipate.
  Anything other than exactly `dark` (including `UNKNOWN`, the initial value) means **process the
  message**. `[OBS]` Fail-open, not fail-safe.

### The Kafka consumer group is derived from the cluster colour

```java
// GroupIdUtil
join("_", applicationName, IGClusterDetails.getClusterColour(), "payment_listener")
```

and `clusterColour` is read from the **`spring.profiles.active`** system property `[OBS]`.
Two consequences:

1. **Blue and green are separate consumer groups**, so *both* clusters receive every record and the
   dark side discards its copies. Consumption is doubled; correctness rests entirely on the §3
   guard. `[OBS→INF]`
2. **A colour flip creates a brand-new consumer group.** With `auto.offset.reset=latest`, that group
   starts at the tail. Any record produced while the newly-promoted cluster had no committed offset
   is **skipped, not replayed** — invisible email loss during deploys. `[OBS→INF]`

Also: the two consumer factories use *different* group ids —
`payment-listeners_<colour>_payment_listener` for email, and
`payment-listeners-webmessage_<colour>_payment_listener` for web messages `[OBS]` — but
`emailDefaultConsumerFactory()` is a hand-inlined duplicate of the private
`createDefaultConsumerFactory()` helper `[OBS]`, so the two paths must be kept in sync by hand.
`kafkaEmailEventListenerContainer` is likewise a copy of `createMessageListenerContainer`.

---

## 4. Environment configuration: the highest-risk area found

### 4a. UAT consumes the LIVE PII topics

`resource/src/main/properties/uat/application-UAT.properties` `[OBS]`:

```
kafka.emails.topic.name   = com_ig_payments_v1_email_event--live--pii
kafka.webmessage.topic.name = com_ig_payments_v1_webmessage--live
```

Identical to `application-LIVE.properties`. The repo README states this as intent ("`--live` for
UAT/LIVE environments"), so it is deliberate `[OBS]` — but the consequences are worth stating:

- UAT reads **production customer PII** (recipient email addresses) off the `--pii` topic.
- UAT's `email.url` is the **real** `https://webservice.exacttarget.com/Service.asmx` with the same
  service account — nothing in the code points non-prod at a sandbox. `[OBS]`
- UAT's protection against emailing real customers is *only* the light/dark guard of §3, i.e.
  whether the UAT box happens to be dark. `[INF]`
- Group id = `payment-listeners_<spring.profiles.active>_payment_listener`. If UAT and LIVE ever run
  the same profile string as their colour, they **share a consumer group and steal each other's
  records**. `[OBS→INF]` `[UNK]` What `spring.profiles.active` actually holds per environment —
  needs a deployment-side answer.

### 4b. XML validation is off in production only

| Env | `VALIDATE_XML` |
|---|---|
| DEV | `true` |
| TEST | `true` `[OBS]` |
| UAT | `true` |
| **LIVE** | **`false`** |

`[OBS]` This flag drives `xmlFactory.createUnmarshaller(..., validateXML)` in both JMS listeners.
Production is the *only* environment that accepts schema-invalid messages, so a malformed message
that fails loudly in UAT proceeds silently in LIVE, surfacing later as an NPE inside `FEMessage`.

### 4c. Console authorisation is granted to a different team's LDAP group

README documents `RG-IGIL-PaymentListeners-Testing` / `RG-IGIL-PaymentListeners-PROD`. The actual
config `[OBS]`:

```yaml
# application-TEST.yml
ig: { messaging: { access: {
      # change to the group one when done
      roles: 'ROLE_RG-IGEMB-JMSMIGRATIONMONITOR-AMQBRIDGEFLOWS-EDIT' } } }
#     roles: 'RG-IGIL-PaymentListeners-Testing'

# application-LIVE.yml
      roles: 'ROLE_RG-IGEMB-AMQBridgeFlows-PROD'
```

The documented groups are commented out; LIVE console access (start/stop listeners) is governed by
the **AMQ Bridge Flows** production group, with an unresolved `# change to the group one when done`
TODO. The README and the deployed reality disagree.

### 4d. Credentials committed in plaintext — while the correct mechanism exists in the same folder

`fiorano-jndi.properties` uses deploy-time token substitution — the right pattern: `[OBS]`
```
fmq.broker.principal=@@fioranoIGMessaginguser@@
fmq.broker.credentials=@@fioranoIGMessagingpasswd@@
```
`application.yml` does the same for SSO (`@@ssoPaymentListenersuser@@`). Yet, in adjacent files:

| File | Secret `[OBS]` |
|---|---|
| `common/email.properties` **and** `listeners/emails.yml` | Marketing Cloud password for `SFMCE2IGConnector@ig.com`, duplicated in both — and it is the username **reversed** (`@rotcennoCGI2ECMFS`) |
| `dev/kafka_properties/kafka.properties` | `peach` SASL password for the `payment-listeners` principal |
| `dev/amq_properties/amq.properties` | one shared password reused across all six AMQ brokers (banjo/kazooie/luigi/mario/sonic/tails) |
| `context/dev/context.xml` | Oracle `PAYMENT_LISTENERS_CON` password + full TNS descriptor (`butol21/22`) |
| `dev/application-DEV.properties` | `CARD_PAYMENTS_REST_PASSWORD` (32-hex) |
| `application.yml` | `security.user.password: admin` |

Two further notes: the MC password is stored **twice** (JMS listener YAML + Kafka
`email.properties`), so a rotation must touch both or the two pipelines diverge on credentials
`[OBS]`; and the password being a trivial transform of the username defeats the point of the
secret. LIVE/UAT `CARD_PAYMENTS_REST_PASSWORD` is empty, suggesting Pret injection *is* available
for these keys and simply was not used for the rest.

CI does run `SNYK_TEST: "true"` and GitGuardian (`scan-mr` component) — but
`SNYK_ALLOW_FAILURE: "true"` and `allow_failure: true` on both Snyk jobs `[OBS]`, so nothing blocks.

---

## 5. Idempotency and consistency: absent, and structurally so

**IDEMPOTENCY: NONE FOUND** `[OBS]` — no `idempotencyKey`, `requestId`, dedup cache, seen-message
store, or conditional write anywhere in the module. Grepping the standard markers returns nothing.
Given:
- Kafka at-least-once with timer-based auto-commit → redelivery on rebalance/restart is expected;
- the internal retry loop calling MC up to 3 times, where a *timeout* is wrapped as
  `MCRetryableException` by `handleUnexpectedError` even though the send may have succeeded server
  side `[OBS→INF]`;
- both clusters consuming every record;

…**duplicate customer emails are a structural outcome, not an edge case.** The only mitigation is
Marketing Cloud's own TriggeredSend behaviour. `[UNK]`

**No transaction spans the two InVision writes.** Both web-message listeners do: `[OBS]`
```java
invisionService.send(channelId, encode(reply), fid);
invisionService.send(channelId, encode("INV"), fid);
```
The second `"INV"` is a terminator/flush the front end expects (visible in the 2019 fixture as
base64 `SU5W`). If the first succeeds and the second throws, the client screen is left mid-message.
On Kafka this then throws → logged → offset committed → no replay.

`LedgerTransactionsListener` (README: *decommissioned*) fans one message to a queue **and** a topic
with no transaction — partial-publish on failure. `[OBS]` It is still a live `@Component`, and
`listener.LedgerTransactions.AUTOSTART=true` in **LIVE and UAT** — but there is no
`ledgertransactions.yml` under `resource/.../listeners/`, only `emails.yml` and `webmessaging.yml`.
`[OBS]` So the framework never instantiates it: dead class + dead prod config + a README table that
disagrees with both.

---

## 6. Fossils — the repo carries a decommissioned card-payments service inside it

The README's "Decommissioned Listeners" table lists Payment Failure, Card Auth Routing, DataCash
Card Auth Handler, and Ledger Service. Their **dependencies and configuration remain**: `[OBS]`

- `impl/pom.xml` still pulls `com.datacash:datacash:2.1.1`, `wt-cardpayments-client:1.8.0`,
  `wt-common-oxm` — with 8 hand-written `<exclusion>`s on the cardpayments artifact alone
  (bouncycastle, activemq, xercesImpl, orderserver-client, ojdbc6) to stop it dragging in a second
  application's stack.
- `ContextConstants` — 17 constants, **all unused in this repo**: `DATA_CASH_HOST`,
  `WEST_PAC_MERCHANT_ID`, `REALEX_TIMEOUT`, `PAYMENTS_CLIENT_SPRING_CONFIG`…
- Every environment properties file still configures DataCash (`mars`/`venus.transaction.datacash.com`),
  Westpac (`ccapi.client.qvalent.com`, cert file paths under `/opt/mqlsnr/thirdpartycerts/`), and
  `IS_PRE_VALIDATE_CARD=true` — **in LIVE**.
- `impl/src/test/resources/spring/Payments-messaging-test.xml` wires JAXB marshallers for
  `IgCardAuthRequest`, `IgCardAuthResult`, and Realex request/response.
- `Formatter` (Marketing Cloud) declares `throws SalesforceServiceException` from
  `uk.co.igindex.salesforceservice` — a leftover from a prior Salesforce integration library.

**`FEMessage` is the largest fossil.** 711 lines, but `WebMessageListener` explicitly rejects every
message kind except `FUND_ACCOUNT`: `[OBS]`
```java
case ACCEPT: case REJECT:
   throw new IGException("MessageType " + messageType + "not supported by: " + msgStr, ...);
case FUND_ACCOUNT: break;
```
Only the `FundAccount` branch of `translateMessage` is reachable — which also means `mapperKey`
stays `null`, so `retrieveDisplayValue` returns early and the entire **602-line
`elementmappings.xml`** (Mappers, Convert tables, Display formats, scaling factors) is loaded and
never consulted. `[OBS→INF]` Dead with it: `translateReject`, `translateAttributeList`,
`retrieveRejectSubstitution`, `findFailedCheck`, the price-improvement / `ScalingHelper` arithmetic,
L2 / IM / Charts channel branches, `AttributeOrderComparator` (constructed in `initialise`, applied
only inside `translateAttributeList`), and the `wt-price-impl` dependency it needs.

Roughly **500 of 711 lines of the most intricate class in the repo are unreachable in production**,
yet carry ~2,000 lines of tests (`FEMessageTest`, `FEMessageAdvancedTest`, `FEMessageEdgeCasesTest`)
that exercise the dead paths and so make the class look well-covered and load-bearing.

An in-house **data-driven test harness has been fully abandoned in place**: `[OBS]`
`ListenersTest` is `@Ignore` with its `@RunWith` commented out; `IGMessagingTestRunner` retains only
a constructor with ~180 commented-out lines; `TestFrameworkConfiguration` has every `@Bean`
commented out. It captured real production traffic and replayed it against listeners with assertions
on InVision publishes, Oracle statements, and JMS sessions — the `webMessagingData.xml` fixture used
as evidence in §2a is a surviving artefact (`emailsData.xml` is **0 bytes**). This is the only
mechanism the repo ever had for validating listener behaviour end to end, and its replacement
(§2a's Testcontainers test) covers one of four listeners.

---

## 7. Observability, health, and the coverage gate

- **`TracingSupportFilter`** sets `callerReqId` / `reqId` as **request attributes** (not MDC) and
  echoes the trace id back in an `X-REQUEST-ID` response header `[OBS]`. But the logback pattern
  reads `%X{trace_id}` / `%X{span_id}` — **MDC** keys populated by the OTel javaagent, not by this
  filter. `[OBS→INF]` The filter's attributes are consumed by nothing in this repo. It also only
  covers HTTP requests; the message-driven paths (the actual work) get no correlation id at all,
  so a customer email cannot be traced from event to send.

- **`HealthController`** `[OBS]`:
  ```java
  @GetMapping("/health")  // returns 200 "Payment Listener service is running" — unconditionally
  @GetMapping("/log")     // emits two log.error lines, returns 200
  ```
  `/api/health` inspects **nothing** — not broker connectivity, not Kafka assignment, not MC
  reachability. Its `try/catch` wraps a `ResponseEntity.ok()` and is unreachable. A process with
  every listener detached still reports healthy. `/api/log` is a deliberate synthetic
  ERROR-log canary for the OV alerting pipeline `[INF]` — an unauthenticated endpoint that lets any
  caller inject `ERROR` lines into the alerting stream.

- **`FEMessage.translate()` logs at INFO for every single lookup** `[OBS]`:
  ```java
  log.info("Key :: " + s.trim() + langCode);
  log.info("Translated :: " + translated);
  ```
  Two INFO lines per token per message, and for FundAccount the substituted values (account id,
  bank reference, currency) pass through `translate()` — so customer-identifying values land in
  `payment-listeners.log` at the root level (`<root level="info">`). The async appender's
  `discardingThreshold` of 20% then silently drops INFO under burst, making the log both noisy and
  lossy.

- **Coverage gate is enforced against a heavily narrowed denominator.** `COVERAGE_THRESHOLD: "75"`
  in CI, but the jacoco excludes in `impl/pom.xml` (and duplicated in `coverage/pom.xml`) remove
  `**/*Message.class` — i.e. **`FEMessage` itself** — plus `**/*Factory.class`
  (`MCExceptionFactory`, the error-classification logic), `**/*ErrorHandler.class`
  (`KafkaErrorHandler`), `**/*Filter.class`, `**/*Exception.class`, and `**/*$*.class` — which
  drops `MarketingCloudEmailExceptionHandler`, the inner class holding all Marketing Cloud error
  handling. `[OBS]` Nearly every component identified above as risky is excluded from the metric
  that is supposed to police it.

- `.modernise/state/PaymentListeners-pipeline-analysis.yaml` (2026-05-21) records the golden-pipeline
  adoption and is candid about gaps: `acceptance_tests: MISSING`, `contract_testing: MISSING`,
  `post_deployment_validation: MISSING`, `unit_test_coverage: PARTIAL`. `[OBS]` `contract_testing`
  is the one that matters most given §2a — there is no contract test between this consumer and the
  Avro producers, nor between it and InVision.

---

## 8. Notable smaller observations

- **`MarketingCloudLoginImpl.getService()` — the session refresh never fires.** `[OBS]`
  ```java
  private static final long NEXT_LOGIN_TIME = 470;
  ...
  if (System.currentTimeMillis() < NEXT_LOGIN_TIME) {
     synchronized (this) { logger.info("Session expired. Login now..."); this.marketingCloudService = createSoapBinding(); }
  }
  ```
  `System.currentTimeMillis()` is ~1.8e12; `470` looks like an intended 470-*second* session TTL that
  was never converted into a deadline. The comparison is **always false**, so the SOAP proxy is
  built once in the constructor and reused for the process lifetime, and `"Session expired"` can
  never be logged. `[OBS→INF]` If the MC session does expire, every subsequent send fails until the
  Tomcat is restarted — and those failures arrive as generic exceptions → `default` in
  `MCExceptionFactory` → **non-retryable**. The `synchronized` block guards a non-volatile field and
  would be insufficient even if reachable.

- **`MarketingCloudProperties` is a Lombok `@Data`** holding `emailPassword` `[OBS]`, so a generated
  `toString()` will print the credential if the object is ever logged. `MarketingCloudEmail`, by
  contrast, deliberately exposes only `log()` → `templateId=%s` — a considered PII decision `[OBS]`.
  But `KafkaEmailsListener`/`EmailsListener` then do
  `log.debug("Generated message: " + marketingCloudEmail)` `[OBS]`, and `MarketingCloudEmail` has
  **no `toString()` override** — so that resolves to the default identity hash, not the safe `log()`.
  Harmless as written, but the safe accessor is bypassed at both call sites.

- **`spring-kafka` is pinned to `1.0.0.M2`** — a 2015 *milestone* build — in `dependencyManagement`
  `[OBS]`. That is why `ConfigManager` uses the long-removed `ErrorHandler` interface and the
  `KafkaMessageListenerContainer(factory, Pattern)` constructor. Production Kafka consumers for
  customer email are running on a pre-release artifact, on Java 8, with `kafka-spring 1.4.5`
  layered on top.

- **Kafka topics are subscribed by regex.** `Pattern.compile(topic)` where `topic` is e.g.
  `com_ig_payments_v1_email_event--live--pii` `[OBS]`. It happens to match literally, but as a
  pattern subscription it would also match any future topic containing that substring, and pattern
  subscriptions add metadata-refresh-driven rebalances the code does not account for.

- `KafkaWebMessageListener` logs `log.info("Processing WebMessage: {}", webMessage)` — the **entire
  Avro record** at INFO, including `accountId`, `bankReference`, `phoneNumber` `[OBS]`.

- `KafkaWebMessageListener` swallows non-`FUND_ACCOUNT` types with a `log.warn` and returns, whereas
  `WebMessageListener` **throws** for `ACCEPT`/`REJECT` `[OBS]`. Same input, opposite disposition.

- `SimpleDateFormat` and `DecimalFormat` are instance fields of `FEMessage` `[OBS]` — safe only
  because a `FEMessage` is constructed per message; a future attempt to cache or reuse the object
  across the 2 listener threads would corrupt timestamps.

- `endorsed/` module exists to ship JAXB/JAX-WS jars into Tomcat's endorsed dir `[OBS]` — a Java 6/7
  era mechanism, ignored by Java 9+. It pins the deployment to Java 8 as firmly as the code does.

- The `docs/` module carries PlantUML `component.puml` / `deployment.puml` rendered to PNG `[OBS]`;
  neither depicts the Kafka listeners added in 2025.

---

## 9. Open questions for owners `[UNK]`

1. **Are the JMS and Kafka pipelines both receiving traffic today, or is Kafka shadow-only?** This
   single answer determines whether §2a is a latent defect or an active customer-facing one.
2. **Does InVision/the front end accept the Kafka `DisplayMessage=`/`status=12` shape?** And is a
   FundAccount *rejection* (msgId `13xxxx`) currently reachable over the Kafka topic?
3. **What is `spring.profiles.active` in UAT vs LIVE?** If they collide, UAT and LIVE share a Kafka
   consumer group on `--live--pii`.
4. **Is emailing real customers from UAT prevented by anything other than UAT being dark?**
5. **Why is `VALIDATE_XML=false` in LIVE alone?** Historical performance concern, or drift?
6. **Which LDAP group is intended to hold LIVE console access** — the README's
   `RG-IGIL-PaymentListeners-PROD` or the configured `ROLE_RG-IGEMB-AMQBridgeFlows-PROD`?
7. **Is duplicate-email suppression expected from Marketing Cloud TriggeredSend?** Nothing on this
   side prevents duplicates.
8. **Can `FEMessage` + `elementmappings.xml` + the `datacash`/`wt-cardpayments`/`wt-price-impl`
   dependencies be deleted?** ~500 dead lines and three dependency trees rest on the answer.

---

## 10. One-paragraph summary

`payment-listeners` is a thin, ageing adapter — 34 main classes on Java 8 — whose entire job is to
turn payment events into customer emails (Marketing Cloud SOAP) and on-screen messages (InVision).
Its defining characteristic is that **every function exists twice**: a 2013-era Fiorano/JMS path
that inherits real reliability machinery from the in-house `ig-messaging-tomcat-framework`
(client-ack, retry counts, dead-letter queue, sensitive-field masking, per-listener autostart), and
a 2025 Kafka path built by hand that has **none of it** — auto-commit, `auto.offset.reset=latest`,
an 8-line error handler that only logs, no DLQ, no dedup, no way to switch it off. The two paths
have already drifted in observable behaviour: the Kafka web-message listener re-implements reply
construction from scratch and emits a hardcoded `status=12` ("success") in a different wire format,
which a repo-committed 2019 production capture shows should be `status=13` for a rejection — and the
new acceptance test locks the divergence in rather than catching it. Correctness under blue/green
rests entirely on a per-message `getLightDarkState().equalsIgnoreCase("dark")` string check that
fails **open**, is fed by one of two independent cluster-detail implementations, and sits alongside
a consumer-group id derived from cluster colour that silently skips the backlog on every flip.
Layered on that: UAT points at the LIVE PII topics and the real ExactTarget endpoint, production is
the only environment with XML validation disabled, LIVE console access is granted to another team's
LDAP group over an unresolved TODO, six sets of credentials sit in plaintext beside files that
demonstrate the correct `@@token@@` injection pattern, and the 75% coverage gate excludes — by
filename pattern — `FEMessage`, the error-classification factory, and the Marketing Cloud exception
handler. Roughly 500 of `FEMessage`'s 711 lines and all 602 lines of `elementmappings.xml` are
unreachable in production but heavily tested, and the only harness that ever validated listeners
against captured production traffic is commented out in place.
