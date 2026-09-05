# Repository Discovery — card-validation-service

**Repository:** `_Codes/payments/card-validation-service` (`com.iggroup.wt.cardvalidation:pay-cardvalidation`)
**Date:** 2026-09-05
**Analysis depth:** deep single pass (211 Java files, 7 Maven modules, all config tiers, CI, in-repo docs)
**HEAD:** `cdb571c` — *Merge branch 'springboot4_migration' into 'master'*

> Legend: **[OBS]** = observed in code/config · **[INF]** = inferred, reasoning given · **[UNK]** = not determined

---

## 1. System Mental Model

A **card BIN classification and admission-control service**. Callers hand it a card number (or an
Apple/Google Pay dPAN) and a website id; it answers *what kind of card is this* (scheme, type,
product, issuer, issuer country) and *are we allowed to take money from it on this site*.

It has **two entirely separate validation engines living in one WAR-shaped app**:

| | Modern path | Legacy path |
|---|---|---|
| Routes | `POST /validate/card`, `POST /validate/wallet` | `POST /controller?action=validateCard` |
| 60-day traffic | 27,562 + 6,555 | **1,129** |
| Data source | one 114 MB Worldpay BIN CSV in the classpath, loaded into a Guava `TreeRangeMap` | DataCash `CardInfo*.bin` binaries + `master-bindb.csv` + 4 per-PSP CSVs |
| Rules | 6-rule chain over Spring Cloud Config lists | ~1,900 lines of imperative cascade + reclassification |
| Response | JSON `BinInformationResponseDTO` | JDOM-rendered XML `<ig-card-validation-reponse>` (sic) |
| Covered by the 75 % gate | yes | **no — explicitly excluded** |

Everything is read-only reference data. **No database writes, no transactions, no state machine, no
idempotency concerns** — the only Oracle access is two read-only stored procedures for banned
countries. The service is pure classification, so a wrong answer is a *business* failure (a card
wrongly accepted or wrongly refused), never a data-integrity one.

---

## 2. Repository / Module Architecture

```
pay-cardvalidation (pom)
├── resource            → zips per-env property/CSV/BIN files into a distributable
├── intf                → DTOs, enums, abstract CardValidationService (has XML-rendering behaviour!)
├── impl        ← intf  → all controllers, services, config, filters, vendored com.datacash.*
├── coverage    ← impl  → JaCoCo aggregate + 75 % gate (unit)
├── jar         ← impl  → @SpringBootApplication main class + spring-boot-maven-plugin
├── acceptance-test     → Cucumber + Testcontainers + WireMock, real-socket
└── acceptance-coverage → second JaCoCo aggregate + regression gate (unit ⊕ acceptance)
```

Not hexagonal. This is the older IG `wt-maven-project` **`intf` / `impl` split** — an interface
artifact other repos can depend on without pulling the implementation. **[OBS]** The split leaks:
`intf/.../service/CardValidationService.java` is an *abstract class* that owns the `createXml()`
response renderer and the restricted-country override, so `intf` is not a pure port package.

**[OBS] There is no `war` module** — `<modules>` lists 7 and none is `war`. Yet:
- root `pom.xml:99` still declares `pay-cardvalidation-war` in `<dependencyManagement>`,
- `impl/.../CardValidationServiceApplicationInitializer` still `extends SpringBootServletInitializer`,
- `run_application.sh` / `.bat` / `README.md` all `cd war` and run `tomcat7:run` / `cargo:run`.

**[INF]** The app was converted from an external-Tomcat WAR to an executable Spring Boot jar and the
WAR scaffolding was never cleaned up. This has a real consequence — see §13 (filters).

---

## 3. Maven / Dependency / BOM Behaviour

| Aspect | Finding |
|---|---|
| Parent POM | `com.iggroup.wt.maven3:wt-maven-project:3.9.0` (IG-internal) |
| Spring Boot | **4.1.1** (BOM *imported*, not parent) |
| Spring Cloud | **2025.1.2** |
| Spring Framework | 7.x (via SB4) |
| Java | 17 source/target |
| Jackson | **dual classpath** — Jackson 3.1.5 (app) + Jackson 2.21.x (pinned, transitive only) |
| Notable | Guava 33.3.1 (`RangeMap` is load-bearing), Ehcache/JSR-107, JDOM2, **Apache ORO** regex (retired 2010), `oracle.jdbc`, `org.mozilla:rhino` |

**[OBS] The most instructive comment in the repo is in the root pom**, and it is a correct piece of
Maven knowledge worth reusing:

> `spring-boot-dependencies` / `spring-cloud-dependencies` are only *imported*, not our `<parent>`,
> so their own `${logback.version}`-style properties are already resolved by the time they're
> imported — overriding same-named properties here has no effect. These must be pinned via explicit
> `dependencyManagement` entries instead.

Hence `logback-fixed.version`, `tomcat-fixed.version`, `httpclient5-fixed.version`,
`jackson3-fixed.version` etc. — a naming convention that exists purely to avoid colliding with BOM
property names. **[INF]** Anyone "tidying" those back to the canonical property names would silently
re-open the Snyk findings.

**Dependency hygiene gaps [OBS]:**
- `impl` declares `com.opencsv:opencsv` — **zero `com.opencsv` imports anywhere**. Leftover from the
  evaluation recorded in `BinFileLoader`'s comment ("OpenCSV 5.11.2 took ~345 seconds on this file —
  do not use it here"). The rejection was documented; the dependency was not removed.
- `netty-bom` pinned to `4.2.17.Final` ahead of the SB4 BOM, for an Ehcache cache-region fix
  (TASTYFX-1414). Comment says remove once the BOM catches up.
- `rhino` must be managed explicitly because `spring-cloud-config-server` pulls it in for JS template
  evaluation and the SB4 BOM doesn't manage it.

---

## 4. Java / Spring Technology Usage

- **Spring MVC** (servlet, `spring-boot-starter-webmvc` — the SB4 artifact rename). No WebFlux, no
  reactive, no virtual threads.
- **Spring Cloud Config — as a *server*, embedded in the business app.** `@EnableConfigServer` on the
  app class; `spring.cloud.config.server.git.uri` points at
  `git.iggroup.local/scm/pay/payments-configuration.git`, `searchPaths: CardValidationService`,
  `bootstrap: true`, `prefix: spring/config`. The app therefore **boots a config server and then
  bootstraps itself from it**. `spring-cloud-starter-bootstrap` is present to keep the legacy
  bootstrap context alive. **[INF]** This is why the acceptance tests need their own `bootstrap.yml`
  to disable the remote-git self-bootstrap (documented in `docs/acceptance-testing/limitations-and-future-work.md`).
- **No Spring Security at all.** No starter, no `@EnableWebSecurity`, no `@PreAuthorize`. Every route,
  including `/actuator/refresh`, is unauthenticated at the application layer.
- **Spring Data: none.** `spring-jdbc` `StoredProcedure` subclasses only.
- **Spring Cache** over Ehcache 3 via JSR-107.
- **Spring JMS** — a hand-built `DefaultMessageListenerContainer`, no `@JmsListener`.
- Java features: `record` (`WorldpayBinInformation`), pattern `switch` (`Scheme.getScheme`), Lombok
  everywhere including `@SneakyThrows`. Alongside 2007-vintage code using raw `Map`, `Hashtable`,
  `Enumeration`, `StringBuffer`, and `assert` for argument validation.

---

## 5. Architecture Detected

**Pattern: layered `intf`/`impl` service with a Chain-of-Responsibility rules engine bolted onto a
legacy Command/Action servlet dispatcher.** Confidence: high.

**Evidence**
- Chain: `config/BinValidationConfig` assembles `List<ValidationRule>` in a fixed order and hands it
  to `BinValidationService`, which short-circuits on the first non-`SUCCESS`.
- Command: `application/command/CardCommand` (abstract, © 2007) + `ValidateCardCommand`, dispatched by
  `?action=` string comparison in `application/action/verify/CardValidationController`.
- Strategy-ish per-PSP lookups: `service/{datacash,noire,streamline,aib,masterbindb,worldpaybindb}`.

**Trade-offs**
- (+) The modern rule chain is genuinely clean, testable, and config-driven — adding a brand is a YAML
  edit in `payments-configuration`, not a release.
- (−) The chain **short-circuits and returns only the first failure**, and `blockedBins` is checked
  **last**. A blocked BIN that also has a disallowed brand is reported as `CARD_BRAND_NOT_ALLOWED`.
  Any consumer inferring "is this BIN blocked?" from the result code will be wrong. **[OBS]**
- (−) Two engines, two answer shapes, two block lists (§7), zero shared code between them.

---

## 6. Important Execution Flows

### Flow 1 — `POST /cardvalidation/validate/card` (27.5 k / 60 days)

```
POST /validate/card {cardNumberOrDpan, websiteId}
  → bean validation: @Pattern ^[0-9]{8,19}$
  → BinUtils.getBinNumber()            = substring(0,8)
  → BinLookupService.getBinInformation(bin)
       1. BinConfig.overriddenBinRangeMap.get(lowerRange)   ← Spring Cloud Config overrides win
       2. BinFileLoader.binRangeMap.get(lowerRange)         ← exact range match
       3. binRangeMap.subRangeMap([lower,upper]).values().findFirst()   ← prefix fallback
       4. else throw BinInformationNotFoundException → HTTP 400
  → BinValidationService.validate()  (6 rules, first failure wins)
       CardCountry → CardBrand → CardType → ProductType → RestrictedCountries → BlockedBins
  → BinInformationResponseDTO {binInformation + validationResult}   HTTP 200 always if BIN was found
```

**Key files:** `application/Controller/BinValidationController.java`,
`service/worldpaybindb/BinLookupService.java`, `validations/*.java`, `config/BinConfig.java`

**Interesting details [OBS]**
- The 8-digit BIN is turned into a range key by **right-padding**: `getLowerRange` pads with `'0'` and
  `getUpperRange` with `'9'` to `MAX_CARD_LENGTH = 18`. So a "card number" inside
  `ValidateCardRequest` is actually an 18-digit synthetic range floor, not a PAN.
- `MAX_CARD_LENGTH = 18` while the request DTO accepts **19** digits. Consistent internally (only used
  for range keys) but the constant does not describe reality for 19-digit PANs.
- Step 3 takes `findFirst()` of possibly several overlapping ranges — **an arbitrary (lowest-range)
  winner when the Worldpay file has overlapping entries inside one 8-digit prefix window**. No warning
  is logged when the sub-range has >1 match; the count is logged but not flagged.
- A *successful* response and a *rejected* response are both HTTP 200 with a `validationResult` field.
  Only "BIN unknown" and bean-validation failures are 400.

### Flow 2 — `POST /cardvalidation/validate/wallet` (6.5 k / 60 days)

Identical, except `BinUtils.getDPanBinNumber()` = `substring(0, 9)`.

**[OBS] Defect:** the DTO permits a **minimum of 8** digits, but this route needs **9**. An 8-digit
`cardNumberOrDpan` on `/validate/wallet` throws `StringIndexOutOfBoundsException`, which is swallowed
by `@ExceptionHandler(Exception.class)` into an **empty HTTP 400 with no body** (§14).

### Flow 3 — `POST /cardvalidation/controller?action=validateCard` (1.1 k / 60 days)

```
POST /controller?action=validateCard&pan=…&expiryDate=…&site=…
  → CardValidationController: string-compares action, else logs a warning and returns null (HTTP 200, empty)
  → ValidateCardCommand.execute()
       parseRequest() → createCardDetails():  pan = pan.substring(0, 6)      ← OUTSIDE the try/catch
  → DataCashCardValidation.validateCard(cardDetails, site)
       1. Noire / ChinaPay CSV            → if hit, RETURN (short-circuit, nothing else consulted)
       2. hard-coded BLOCK_BIN_LIST       → if hit, reject
       3. IG master BIN DB (30 MB CSV)    → prepaid/commercial exclusions, VISA/MCI reclassification
       4. DataCash CardInfo1/2.bin        → the real accept/reject, via the vendored 2007 client
       5. if DataCash rejected → QuickGateway test-card CSV  ← can flip isValid back to TRUE
       6. if DataCash accepted → AIB CSV  → scheme override only
       7. Streamline CSV                  → AUS/NZ/SG VISA→DELTA, AUS MCI→DEBIT_MASTERCARD
  → CardValidationService.validate(): restricted-country check can flip isValid to false
  → createXml() → JDOM → XML string written straight to the response Writer
```

**[OBS] `pan` is truncated to 6 digits before any validation happens.** Consequences that follow from
that single line (`ValidateCardCommand:69`):
1. `BasicCardNumberValidation.isValidCardNumber()` ends with
   `return cardNumber.length() == 6 || isValidluhnCheck(cardNumber);` — because the HTTP path always
   supplies exactly 6 digits, **the Luhn check is unreachable on this route**. It is a deliberate
   accommodation of the truncation, not dead code by accident.
2. `QuickGatewayCardValidator` compares `cardDetails.pan.equals(cardValues[0])` against **full 16-digit
   test PANs** — a 6-digit value can never match. **The QuickGateway test-card branch is unreachable
   via HTTP.** (Reachable only by a direct in-process call to `execute(CardDetails, site)`.)
3. `expiryDate`, `cv2`, address lines and postcode are parsed, carried into a
   `com.datacash.client.CardDetails`, and never used for a decision — the DataCash request document is
   built but, per the code's own comment, *"no request is actually dispatched"*.

---

## 7. Domain Concepts

No payment lifecycle and no money movement. The domain is **classification + admission**.

**Concepts and where they live**

| Concept | Implementation |
|---|---|
| BIN → card facts | `WorldpayBinInformation` record ← 24-field Worldpay CSV (fields 1,2,3,4,5,6,8,9 retained) |
| Scheme | `domain/Scheme` (6 values, unknown → `OTHER`) vs legacy `intf/domain/CardScheme` vs `service/psp/domain/CardBrand` — **three overlapping scheme vocabularies** |
| Card type | `CardType` {DEBIT, CREDIT, PREPAID, …} ← Worldpay `CardClass` via `WorldpayCardClassToDomainCardType` |
| Product type | `ProductType` {CONSUMER, …} — only `CONSUMER` is allowed in config |
| Site | `websiteId` → Oracle proc → `SiteType` {CFD, SPREAD_BETTING} |
| Prepaid allow-list | `validation-config.allowedPrepaidIssuers` — prepaid is refused *unless* the issuer is Revolut / Postepay / Intesa / UniCredit / Fineco |

### **TWO INDEPENDENT BLOCK LISTS — same three BINs, two mechanisms [OBS]**

| | Value | Refresh | Used by |
|---|---|---|---|
| `application.yml → validation-config.blockedBins` | 487132, 434176, 487139 | `/actuator/refresh` or config-server | modern path (`BlockedBinsValidationRule`) |
| `CardValidationConstants.BLOCK_BIN_LIST` (hard-coded `asList`) | 487132, 434176, 487139 | **code change + release** | legacy path (`DataCashCardValidation.isBlockBin`) |

They currently agree. Nothing keeps them in agreement. **[INF]** Blocking a fraudulent BIN in an
incident would be a YAML refresh for one route and a release for the other.

**[OBS] A second mismatch inside the modern list:** `BlockedBinsValidationRule` compares an
**8-character** prefix with `cardNumber::startsWith`, so any `blockedBins` entry **longer than 8
digits can never match** — it would be silently inert. All current entries are 6 digits, so this is
latent, not live.

---

## 8. State Machines / Workflows

**None.** No status enum, no transition table, no persisted state, nothing resembling a workflow.
Every request is independent and side-effect-free.

The nearest thing to a workflow is **CI/CD**: `.gitlab-ci.yml` + `.ci/card-validation-service-cd.yml`
implement a ServiceNow CRF gate per environment —
`test:create-crf → validate → close`, then `uat:*`, then `demo-and-live:create-crf →
demo:validate → live:validate → close`. Deployment, not runtime.

---

## 9. Transactions / Consistency / Idempotency

- **`@Transactional`: zero occurrences.** Correct — the only DB access is two read-only stored procs.
- **Idempotency: not applicable and correctly absent.** All endpoints are pure functions of
  (request, reference data). The one JMS consumer performs an idempotent cache flush.
- **Consistency is entirely "stale-until-told".** Four independent refresh mechanisms, no TTL on any
  of them:

| Reference data | Loaded | Refreshed by | If refresh is missed |
|---|---|---|---|
| Worldpay BIN CSV (114 MB) | `@PostConstruct` | **restart only** | stale BINs until next deploy |
| DataCash / master-bindb / Noire / AIB / Streamline CSVs | constructor / lazy | **restart only** | same |
| `validation-config` lists + `overridenBins` | config server | `POST /actuator/refresh` (`@RefreshScope`) | stale allow/block lists |
| banned countries + overrides | Oracle proc at `afterPropertiesSet` | JMS topic `com_ig_client_v0_banned_countries_update` | **stale indefinitely** |

**[OBS] The banned-countries staleness has no backstop.** `BannedCountriesMessageListener.onMessage`
catches `Exception`, logs it, and returns normally — so the message is **acked even when the reset
failed**. The subscription is durable+shared, so a *missed* message is safe; a *failed* one is not.
There is no TTL, no scheduled re-read, and no health indicator over cache age. A single failed reset
leaves sanctions-relevant country data stale until the next restart or the next update message.
This is the highest-consequence consistency gap in the service.

**[OBS] `README.md` names the wrong bean for refresh.** It instructs operators to refresh
"the CVS bean (`BinValidationConfig`)". `BinValidationConfig` is a plain `@Configuration` with **no
`@RefreshScope`** — it merely assembles the rule list. The `@RefreshScope` bean that actually re-reads
config-server values is **`BinConfig`**. The documented procedure works by luck (the whole context's
refresh scope is rebuilt), and the bean name in the runbook is wrong.

---

## 10. Persistence / Caching

### Primary store: **the classpath**, not a database
`impl/src/main/resources/WP_341BIN_V03_20260427_001.CSV` — **114 MB, 799,716 lines, 799,714 data
rows, all exactly 24 fields (verified)**. Loaded whole into `TreeRangeMap<Long, WorldpayBinInformation>`.

**[INF] Heap:** ~800 k `Range` objects + 800 k records × 6 retained `String`s, with **no interning** —
issuer name and country name repeat massively across rows but each row gets its own `String`. Rough
order of magnitude: several hundred MB of live heap held for the process lifetime. Not measured here;
**[UNK]** the configured `-Xmx` (would be in the deployment templates, not this repo).

**[OBS] Repo weight:** `.git` is **517 MB**. Working tree holds ~180 MB of near-identical
`master-bindb.csv` (30 MB × 6 copies: prod, uat, test, dev, it, and test-data) plus the 114 MB
Worldpay CSV. `.gitattributes` (175 lines) marks these `-text` but **there is no Git LFS**. Every BIN
refresh commit (`CAMP-360` was the last) appends another full ~114 MB blob to history, permanently.

### Oracle
One `@Primary` Tomcat JDBC pool, deliberately tiny and defensive
(`max-active: 3`, `max-wait: 4000`, `test-on-borrow`, `remove-abandoned` at 120 s,
`oracle.jdbc.ReadTimeout=5000`, `CONNECT_TIMEOUT=3` in the URL with primary/standby failover).
**[INF]** The `CAMP-546` commits ("Fixes DB stale connection issue", "Fixes connection timeout issue")
are why this config is so explicit. Two read-only procs:
`MW_COUNTRIES.GET_BANNED_COUNTRIES`-style ref-cursors and `MW_WEB_SITE.GET_WEB_SITE_ATTRS`.

### Ehcache 3 / JSR-107 — three caches, all unbounded in time
`bannedCountriesCache` (heap 500) and `bannedCountriesOverrideCache` (heap 500) each hold **exactly one
entry** — `@Cacheable` with no arguments, so the key is `SimpleKey.EMPTY` and the value is the entire
map. `siteTypeCache` (heap 200, `String → SiteType`) is the only one with real keys.
`CacheConfig` builds the JSR-107 manager by hand (no `ehcache.xml`) and closes it in `@PreDestroy`.

---

## 11. External Integrations

**[OBS] There are no outbound HTTP calls of any kind.** No `RestTemplate`, no `WebClient`, no
`@FeignClient`. "PSP integration" here means *reading a file that a PSP sent us*. The DataCash client
SDK is vendored into the source tree and used purely as an **offline BIN-file parser**.

| Integration | Mechanism |
|---|---|
| Worldpay | 114 MB CSV, emailed by the File Transfer team, committed to git |
| DataCash | `CardInfo1.bin` / `CardInfo2.bin` (4.7 MB) via vendored `com.datacash.*` (32 classes) |
| Noire / ChinaPay, AIB, Streamline AUS | per-PSP CSVs in the `resource` module |
| IG master BIN DB | `master-bindb.csv` + `cardvalidation-masterbindb-config.xml` |
| Oracle (`dealuat`/`deal`) | 2 stored procedures, read-only |
| ActiveMQ Artemis (cluster `banjo`) | 1 durable shared topic subscription |
| Spring Cloud Config | self-hosted config server reading `payments-configuration` git repo |

### Message consumer
```java
container.setDestinationName("com_ig_client_v0_banned_countries_update");
container.setPubSubDomain(true);
container.setSubscriptionName(topic + "/" + appName);   // appName = cardvalidation-cde
container.setSubscriptionShared(true);
container.setSubscriptionDurable(true);
container.setReceiveTimeout(1000L);
```
Durable **shared** subscription — so multiple instances **share** the subscription and a given update
message is delivered to **exactly one instance in the cluster**. **[INF] This is very likely wrong for
a cache-invalidation fanout:** each instance has its own in-JVM Ehcache, so all of them need the
message. With `setSubscriptionShared(true)` and a name that is per-application rather than
per-instance, only one node flushes and the others keep serving stale banned-country data until they
restart. Worth confirming against Artemis behaviour and the intended deployment topology
(**[UNK]** instance count per site).

`spring.jms` is left at `DEBUG` in `application.yml` **[OBS]** — permanent debug logging in production.

---

## 12. Concurrency / Threads

### **The BIN loader's thread pool is worse than no thread pool [OBS]**

`service/worldpaybindb/BinFileLoader.readAndInsertRangesConcurrently`:

```java
ExecutorService executor = Executors.newFixedThreadPool(4);
while ((line = reader.readLine()) != null) {
   final String[] parts = line.split(",", -1);
   if (parts[0].equalsIgnoreCase("01")) {
      … validate field count, parse the two longs …
      executor.submit(() -> {
         synchronized (binRangeMap) {                       // ← every task takes the SAME lock
            binRangeMap.put(Range.closed(startRange, endRange),
                            WorldpayBinInfoTransformer.convertToBinInfo(parts));
         }
      });
   }
}
```

Three separable problems:

1. **Zero parallelism.** All CPU work that could be parallelised (`split`, `parseLong`) already
   happens on the reader thread; the only thing handed to the pool is a `put` that is fully
   serialised on one monitor. Four threads contend for one lock 800 k times and accomplish exactly
   what one thread would, plus context-switching and queueing overhead.
2. **Unbounded queue holding full rows.** `newFixedThreadPool` uses an unbounded
   `LinkedBlockingQueue`, and each lambda captures `parts` — **the whole 24-element `String` array**.
   The producer is far faster than the lock-serialised consumers, so the queue grows; at peak it can
   hold hundreds of thousands of `Runnable`s each pinning 24 strings. **[INF] Startup peak heap is
   materially higher than the steady-state map itself**, and it is invisible in any profile taken
   after startup.
3. **The reported timing is wrong.** `binFileLoadEndTime` is captured **before** `awaitTermination`,
   so `"Successfully loaded … timeTaken={} ms"` measures *reading and submitting*, not *loading*. The
   log line understates real load time, which is the metric anyone tuning this would trust.

A single-threaded loop would be simpler, use less peak memory, and log a truthful duration. The
`awaitTermination(10, MINUTES)` timeout → `RuntimeException` path and the field-count/number-format
guards are good defensive additions (**[INF]** added during the recent hardening work); the executor
around them is the part that earns nothing.

### **`CardValidator` lazy init is not thread-safe [OBS]**

`DataCashCardValidation` is a singleton `@Service`; `createCardValidator()` is a plain
check-then-act with **no synchronisation and a non-`volatile` field**:

```java
private void createCardValidator() {
   if (this.cardValidator != null) return;
   this.cardValidator = new CardValidator(binFile, configFile, excludedCardsFile);  // reads 4.7 MB + XML
}
```
Two concurrent first requests each build a `CardValidator` (duplicate file parsing, one instance
discarded), and — because the field is not `volatile` — a second thread can observe a **non-null but
not-fully-constructed** `CardValidator` and see empty `excludedCountries` / `acceptedSchemes` /
`msgMap` maps. **[INF]** That would silently *weaken* the exclusion rules for the duration of a race.
Low probability (one narrow window after each restart, on a route taking ~19 calls/day) but the
failure is a wrong accept, not an exception.

### Other
- `QuickGatewayCardValidator` is `new`-ed **per request** and opens the CSV with
  `new FileInputStream(relativePath)` — filesystem-relative, so resolution depends on the process CWD,
  and `IOException` is handled with `e.printStackTrace()`. (Moot today: the branch is unreachable, §6.)
- No `@Async`, no `@Scheduled`, no `CompletableFuture`, no MDC propagation code of its own — request
  correlation comes from the IG tracing filter and the `spanId`/`traceId` access-log pattern.

---

## 13. Cross-Cutting / Security / Observability

### Security
- **No authentication or authorisation in the application.** **[INF]** Enforcement must live upstream
  (payments-gateway / network). Unauthenticated at the app layer, this includes
  **`POST /actuator/refresh`**, which is explicitly exposed in `bootstrap.yml` alongside `caches`,
  `health`, `info`, `metrics`, `scheduledtasks`, `prometheus`. Anyone who can reach the port can force
  a config-server re-read.

- **`SECRET` — committed Oracle credential.** `impl/src/main/resources/application-DEV.yml`,
  `application-TEST.yml` and `application-UAT.yml` each contain
  `username: MIDDLEWARE` / `password: "Fjdj3od#sjk3f0Y"` against `dealuat-{pri,sby}.iggroup.local`.
  Non-production, but a live shared credential in git history. **Rotation is required, not deletion** —
  it is in every clone and in the 517 MB history. (Same class of finding as
  `payments-gateway`'s committed SSO service account — see `[[payments_gateway_analysis]]`.)
  `application-LIVE.yml` and `application-DEMO.yml` are **empty**, so production credentials come from
  the config server. Good — and it shows the right pattern was available and not used for non-prod.
  A GitGuardian scan component *is* wired into `.gitlab-ci.yml`; **[UNK]** whether these are
  allow-listed or simply predate it.

- **Cardholder data in logs and error messages [OBS]:**
  - `CardCommand.getRequestMap()` logs **every request parameter at INFO**, special-casing only `pan`
    (truncated to 6). So `cv2`, `expiryDate`, `postCode` and address lines are written verbatim to
    the application log on the legacy route. CVV must never be stored — this is a PCI-DSS 3.2 issue.
  - `CardCommand.get()` logs `parameter=value` at INFO with no special-casing at all.
  - `DataCashCardValidation:~300` builds
    `" trying to validate card (" + cardDetails.pan + "): " + e.getMessage()`, then both `log.error`s
    it **and returns it to the caller** inside `cardValidationResult.errors[0]` → straight into the
    XML response. (`pan` is 6 digits on the HTTP path, so the live exposure is BIN + internal exception
    text, not a full PAN — but the code as written will emit whatever `pan` holds, and a direct
    in-process caller passes the full number.)
  - `ValidateCardCommand.writeResponse(Exception, Writer)` writes `e.getMessage()` raw to the client —
    unfiltered internal error text on a public route.
  - `BinValidationController` logs the full `BinInformationResponseDTO` at INFO on **every** successful
    request (issuer, country, scheme, BIN) — ~34 k records/60 days of card metadata into logs.
  - The legacy flow emits ~15 separate `log.info` lines per validation, several of which are a single
    bare `"Y"`/`"N"`.

- **`HeaderOverrideHttpMethodFilter` — `@Deprecated`, mapped to `/*`, and a real bypass primitive.**
  Any request may set `_method` as a **parameter or header** to rewrite its own HTTP verb, and the
  wrapper additionally **forces `Accept: application/json`**. That defeats any method-based control at
  a proxy/WAF (`GET` past a rule, arrive as `POST`). **[INF]** It also explains the README's
  `GET …/controller?action=validateCard` example against a `@PostMapping` endpoint.

- **XXE hardening is present and correct** in `CardValidator` — `disallow-doctype-decl` plus both
  external-entity features disabled, with the failure escalated to `JDOMException`. **[INF]** Applied
  during recent security work; worth keeping as the pattern for the other XML readers.

### **The three `@WebFilter`s are dead [OBS]**
`VersionFilter`, `HeaderOverrideHttpMethodFilter` and `LogIGClusterDetailsFilter` are annotated
`@WebFilter("/*")`. There is **no `@ServletComponentScan` anywhere in the repo**, and there is **no
WAR module** for a servlet container to scan (§2). Spring Boot ignores `@WebFilter` without
`@ServletComponentScan`, so **none of the three is registered**. Only `TracingSupportFilter`
(`@Component`) and `AttributesToAccessLogFilter` are live.

Corroboration from inside the repo: `.coverage-baseline-acceptance.properties` excludes
"unregistered observability filters" from the coverage denominator — the team observed the symptom
(no test can drive them) without recording the cause. **[INF]** The version header and IG cluster
details are silently absent from responses/logs, and the method-override bypass above is currently
*inert* — but re-adding `@ServletComponentScan` to fix the first two would re-arm the third.

### Observability
- **Logback** with custom converters (`DeploymentEnvironmentConverter`, `ServiceModeConverter`) and
  per-environment `card-validation-service-logback.xml` in the `resource` module.
- **Micrometer via IG `metrics-goldensignal-autoconfiguration` 2.0.8**, tagged
  `application: CardValidationServiceCDE`, latency buckets 10 ms–10 s, excluding
  `/monitor/**,/actuator/**,/swagger/**`. Prometheus export is **disabled** in `bootstrap.yml`
  (`management.prometheus.metrics.export.enabled: false`) while `prometheus` is in the exposure list —
  **[INF]** contradictory; scraping is off.
- OpenTelemetry pinned to 1.62.0 for a Snyk fix; `TracingSupportFilter` + `IGTelemetryClusterDetailsProvider`.
- **`/monitor/version` is the highest-traffic route in the service — 242,995 calls in 60 days, 9× the
  business traffic.** It returns `project.version` from a `PropertiesFactoryBean` over
  `application-metadata.properties`. **[INF]** It gates deployments and backs liveness probes.
- `git log` shows `5b43193 Revert "TASTYFX-883: Observability config for CVS."` — **[UNK]** why the
  observability config was reverted.

---

## 14. Errors / Failure / Resilience

### **Every server-side failure is reported to the caller as an empty HTTP 400 [OBS]**

```java
@ExceptionHandler(NullPointerException.class) @ResponseStatus(BAD_REQUEST)
void handleNullPointerException(final NullPointerException e) { log.warn(…); }

@ExceptionHandler(Exception.class) @ResponseStatus(BAD_REQUEST)
void handleException(final Exception e) { log.error(…); }
```

`void` return, so **no body**. An NPE, a `StringIndexOutOfBoundsException`, an Oracle timeout, a
`SQLException` from the banned-countries proc — all become `400 Bad Request` with an empty payload.
Consequences:
- Callers cannot distinguish "your card number is malformed" from "this service is broken".
- **Server-side incidents are invisible in HTTP status metrics** — the 5xx rate stays at zero, and the
  golden-signal error dashboards for this service will look healthy through an outage.
- The 60-day route table shows 87 × 400 on `/validate/card`; **[INF]** an unknown share of those are
  server faults, not client faults.

This is, in my judgement, the single most important operational finding: it converts every
availability problem into a silent correctness problem for the caller.

### Fail-open vs fail-closed — mapped
| Situation | Behaviour | Direction |
|---|---|---|
| BIN not in file or overrides | `BinInformationNotFoundException` → 400 | closed ✓ |
| Unknown scheme string | `Scheme.OTHER` → not in `cardBrands` → rejected | closed ✓ |
| `blockedBins` empty/absent | `return SUCCESS` — nothing blocked | **open** |
| `cardBrands`/`cardTypes`/`productTypes` absent | NPE → 400 | closed ✓ (by accident) |
| `websiteId` blank | `RestrictedCountriesValidationRule` skips the whole banned-country check | **open** — mitigated only by `@NotNull` on the DTO and by `CardCountryValidationRule` running first |
| **`websiteId` unknown to Oracle** | proc extractor returns `""` → `"".equalsIgnoreCase("C")` is false → **`SPREAD_BETTING`** | **silent misclassification** |
| BIN file row malformed | `IOException` → **caught and only logged** → app starts with a **partially loaded** BIN map | **degraded, silently** |
| Banned-countries reset throws | logged, message acked, stale data retained | **open** |

**[OBS] The `""` → `SPREAD_BETTING` default in `GetSiteTypeStoredProcedureImpl` deserves attention:** a
typo'd or newly-provisioned `websiteId` is evaluated against the *spread-betting* banned-country list
rather than the CFD one, with no warning logged. `siteTypeString` is also dereferenced without a null
check, so an absent out-parameter is an NPE → empty 400.

**[OBS] The partial-BIN-load path:** `readWorldPayMasterBin` wraps everything in
`try { … } catch (IOException e) { log.error(…); }` and returns normally. The field-count and
number-format guards throw `IOException` deliberately — so **the guard's own trigger aborts the load
and the app still starts serving**, answering `BIN_INFORMATION_NOT_FOUND` (→ 400) for every BIN after
the offending row. I verified the current file is clean (all 799,714 rows have exactly 24 fields), so
this is a risk carried by the *next* file drop, not a live defect. Given that BIN files arrive by
email and are hand-copied (§15), promoting this to a startup failure would be cheap insurance —
and `docs/updating-worldpay-bin-file.md` already *claims* that is what happens (§15), so the fix would
make the code match the documentation rather than the reverse.

### Resilience
No retry, no circuit breaker, no bulkhead, no fallback anywhere. Justifiable: all reference data is
local and the only remote dependency is Oracle, guarded by short timeouts. **[INF]** Note that the
Oracle failure mode is *silent over-restriction or under-restriction*, not a visible error — see the
fail-open table.

### Known defects in dead or near-dead code
- **`BannedCountriesDaoImpl:~110` copy-paste bug:**
  ```java
  if (bannedCountry.isCfdApplicationBanned()) {
     cfdApp2LetterCountryCode.add(bannedCountry.getCountryCode2());
     cfdApp3LetterCountryCode.add(bannedCountry.getCountryCode2());   // should be getCountryCode3()
  }
  ```
  The CFD *application* 3-letter list is filled with 2-letter codes. The card path uses the
  `PAYMENT` keys (correct), and `getApplicationsBannedCountriesList` has **no production caller** in
  this repo — so this is latent. It would fail open (no 3-letter code ever matches) for anyone who
  starts using it.
- `application/action/verify/CardValidationController` returns `null` (→ HTTP 200, empty body) for any
  `action` other than `validateCard`, logging only a warning.
- `ValidateCardCommand.execute` opens with a loop that iterates all parameter names and assigns to an
  unused local — a no-op.
- `ValidateCardCommand` still contains a `!POST → 405 + HTML "Use POST instead!"` branch, unreachable
  under `@PostMapping`.
- `AbstractFileWatcher` / `DEFAULT_FILE_WATCH_INTERVAL` — hot-reload machinery that is never wired up;
  only `FileWatcherException` survives, in `throws` clauses.

---

## 15. Configuration / Infrastructure

### Four-layer precedence [OBS]
```
1. bootstrap.yml            → app name, profile = ${environment} + ${site}, config-server git coords
2. Spring Cloud Config      → payments-configuration/CardValidationService/application-<ENV>.yaml
                              (the authoritative validation-config lists + overridenBins in prod)
3. application.yml + application-<ENV>.yml   (in the WAR/jar classpath)
4. @PropertySource("classpath:${ig.card-validation.config-file}")
                            → cardvalidation-config.properties (per-env, from the resource module)
```
Profiles come from **`-Denvironment=` and `-Dsite=`** system properties (see the debug instructions:
`-Denvironment=dev -Dsite=blue -Dcatalina.instance=99`), not `SPRING_PROFILES_ACTIVE`.

`property.worldpay.binFilePath` lives in `application.yml`, **not** in
`cardvalidation-config.properties` — so the Worldpay file is the one BIN source that is *not*
per-environment. All the others (`master-bindb.csv`, `noire-binranges.csv`, `aib-binranges.csv`,
`streamline-aus-masterdebit-binranges.csv`, `CardInfo1/2.bin`, `quickgateway-testcard.csv`) exist as
per-tier copies under `resource/src/main/resources/properties/{prod,uat,test,dev,it}/`.

### **The `resource` assembly is broken for two tiers [OBS]**
`resource/src/main/assembly/resources.xml` has 8 `<fileSet>`s. Four point at directories that do not
exist:
```
${basedir}/src/main/resources/properties/common   ← no `common` dir exists (prod, uat, test, dev, it only)
${basedir}/src/main/properties/common             ← wrong base path (missing /resources)
${basedir}/src/main/properties/dev                ← wrong base path
```
Net effect: `prod` and `uat` get their tier files (their `common` overlay is a silent no-op), `test`
gets its tier files, and **`dev` gets nothing at all** — its only two fileSets both use the wrong base
path. `it` is not in the assembly. There is no separate `demo`/`live` tier: **`prod/` serves DEMO and
LIVE**, which is why `DEMO.environment.java.properties` and `LIVE.environment.java.properties` sit
side by side in the same directory.

### **README vs reality: the BIN-file runbook is wrong [OBS]**
`README.md` — the operational procedure for the recurring Worldpay BIN update — says:

> Copy the **V03 version** … to `resource/src/main/properties/dev` … Replace the existing BIN file
> … in **DEV**, **TEST**, **UAT**, **PROD**.

Reality: there is **exactly one** Worldpay BIN file, at `impl/src/main/resources/WP_…CSV`, on the
shared classpath for every environment. `resource/src/main/properties/` does not exist — the path in
the runbook is the same wrong path as the two broken assembly fileSets, **[INF]** suggesting both were
written against an older layout and drifted together. Anyone following the runbook literally would
create a new directory, commit 114 MB into a path nothing reads, and leave the real file untouched.

The rest of the README runbook is genuinely valuable and hard to reconstruct: the file arrives **by
email from the File Transfer team**, is fetched from
`\\igi.ig.local\root → T:\LON\Credit\Worldpay_Bin_Files\<year>`, ships in **V03 and V04 variants of
which only V03 is used**, and the per-environment bean refresh runs through named Bamboo plans
(`PAY-CCRT` / `PAY-CCR` / `PAY-CCRLD`).

**[OBS] `docs/updating-worldpay-bin-file.md` is the correct, current replacement** and should be
treated as authoritative over the README section. It has the right path
(`impl/src/main/resources/`), the right one-line change (`property.worldpay.binFilePath` in
`application.yml`, read by both the app and `BinFileLoaderIT`), the SMB path for Mac, and three good
warnings: all `01` rows must have exactly 24 fields; review `WorldpayBinInfoTransformer` field indices
if Worldpay ships V04+; and `BinFileLoaderIT` enforces a **15-second load threshold**. The README's
version should be deleted and replaced with a pointer to it.

**[OBS] One claim in that doc is wrong, and it matters:** it states that on a schema change
*"`BinFileLoader` will throw an `IOException` at startup and the IT will fail"*. The `IOException` is
**caught and only logged** by `readWorldPayMasterBin` — the application starts normally with a
partially loaded map. Only the IT fails. The doc describes the behaviour everyone would want; the code
does not implement it. Making the load failure fatal would align the two and close the risk in §14.

### **The QuickGateway test-card bypass is disabled by an empty file, not by code [OBS]**
| Tier | `quickgateway-testcard.csv` |
|---|---|
| **prod** | **0 lines (empty)** |
| uat / test / dev / it | 44 lines of full test PANs + expiry + CVV + scheme |

The design intent is documented in the class: *"If the test file is empty. It will return a false."*
So a code path that can flip a DataCash **rejection into an acceptance** is gated in production solely
by a zero-byte file — no profile check, no `@ConditionalOnProperty`, no assertion. It is *currently*
also unreachable because of the 6-digit PAN truncation (§6), so **two independent accidents** are what
keep it safe. Neither is a control anyone would design on purpose.

Also note the non-prod CSVs contain **CVV values alongside PANs** (`4564710000000004,02/19,847,Visa,aus`).
Test data, but the shape is exactly what must never be persisted for real cards.

### Snyk policy
**[OBS] Both `.snyk` ignores expired 2026-07-29 — over a month ago (today is 2026-09-05).** They cover
CVE-2026-54515 in Jackson 2 and Jackson 3 (`SNYK-JAVA-COMFASTERXMLJACKSONCORE-17457695`,
`SNYK-JAVA-TOOLSJACKSONCORE-17457696`), with the reasoning "upstream fix unpublished; exploit
preconditions not met (no `@JsonIgnoreProperties`/`@JsonFormat`/case-insensitive mapping)". The
`snyk-test` CI job will now fail or flag these again. Either the upstream fix has shipped (bump and
delete the ignores) or the expiry needs re-justifying.

### CI/CD
`.gitlab-ci.yml` includes IG's `continuous-delivery` common steps + a GitGuardian scan component.
Stages: `get-version → build → commit-cycle → tag → acceptance-cycle` then the ServiceNow CRF ladder
per environment. `build` publishes surefire + jacoco-aggregate; `acceptance-test` runs
`mvn verify -Pacceptance-test` and then a separate `-pl acceptance-coverage -am install` aggregation
whose failure is **deliberately non-fatal** with an unusually candid operator message:

> `WARNING - acceptance-coverage aggregation failed. acceptance-jacoco-coverage-report will fail
> downstream because of THIS, not its own logic.`

`renovate.json5` (4 lines) and `bom.yml` (2 lines) are present but minimal.

---

## 16. Testing Discoveries

### Two coverage gates with different denominators
| | `coverage` module | `acceptance-coverage` module |
|---|---|---|
| Scope | unit only | unit ⊕ acceptance, merged |
| Gate | **75 % line + 75 % branch** minimum (`QU247-2049`) | **no metric may drop >2 points** below a seeded baseline |
| Baseline | — | instruction 77.13 / branch 61.84 / line 77.45 / complexity 61.18 / method 76.57 (seeded 2026-09-01, suite 31/31 green) |

### **The 75 % gate excludes the entire legacy engine [OBS]**
`coverage/pom.xml` `<excludes>` removes, among others:
```
service/datacash/*        service/masterbindb/*     service/aib/*       service/streamline/*
application/command/*     application/action/verify/*                   domain/*
BinFileLoader.class       observability/**          **/*Config.class    **/*Configuration.class
service/noire/NoireCardValidationServiceImpl.class
```
So the ~1,900-line DataCash cascade — the code that reclassifies schemes, holds the second block
list, can put `pan` into a client-visible error string, and contains the non-thread-safe lazy init —
is outside the gate, and `service/datacash` has only 2 test classes. The `.coverage-baseline-acceptance.properties`
header is admirably honest about the effect: *"line sits at ~77% (vs ~52% with no excludes / a ~59%
no-excludes ceiling)."* **[INF] The real project-wide line coverage is ~52 %**, and the 77 % figure
describes the reachable modern surface only. That is a defensible way to run a gate — but the number
means something narrower than it looks.

### Acceptance suite (`CAMP-1327`, 31 scenarios, 4 `.feature` files)
Cucumber 7.18 + Testcontainers 2.0.5 (Oracle, Flyway-seeded) + WireMock 3.3.1 + RestAssured +
Artemis client + `ig-acceptance-test` framework + datafaker + json-unit. Claims **100 % route
coverage** of the four routes in the 60-day traffic CSV. Notably it also covers the **JMS
banned-countries invalidation flow**, which is not an HTTP route.

**Unusual techniques [OBS]**
- **Route discovery from production telemetry.** `docs/acceptance-testing/route-inventory.md` is built
  from a `last60daysAPI.csv` export of `http.route` with call counts and status splits — tests were
  scoped by *observed* traffic rather than by reading the controllers. This is why the traffic figures
  in this document exist at all.
- **Test-scoped config-server override**: `acceptance-test/src/test/resources/bootstrap.yml` disables
  the embedded config server's remote-git self-bootstrap. Flagged in-repo as a divergence that must be
  kept in sync with the production `bootstrap.yml`.
- **A custom step-def escapes the declarative framework**: `LegacyControllerStepDefs` does direct
  real-socket calls because the framework requires a body template for POST and resolves query params
  from test-data storage — neither fits a parameter-driven bodyless POST.
- **The repo's own limitations doc declines to encode a bug as a test:** the missing-`pan` → HTTP 500
  defect is documented with the note *"no negative test asserts that behaviour yet (it would encode a
  bug)"*. Good discipline, and it independently confirms the §6 finding.
- `BinFileLoaderIT` defines a load-time threshold, referenced from `BinFileLoader`'s
  do-not-use-OpenCSV comment as the gate any future parser change must pass.
- Known env issue recorded in `learnings.md`: acceptance tests fail locally with
  `Protocol handler start failed` (port bind) — must be validated in CI.

---

## 17. Custom Libraries / Implicit Behaviour

### Vendored / in-tree third-party code
- **`com.datacash.*` — 32 classes** (`client`, `client.errors` (25 error types), `errors`, `util`) of a
  2007-era DataCash gateway SDK, copied into `impl/src/main/java`. Used **only** to parse
  `CardInfo*.bin` offline. Excluded from both coverage denominators.
- **`com.iggroup.external.*`** — vendored IG infrastructure: `wt.countries` (banned-countries DAO +
  Oracle `StoredProcedure` subclasses), `uk.co.igindex.property.util` (file watcher, unused),
  `uk.co.igindex.shared.command.HttpCommand`.
- **`uk.co.igindex.shared.util.Strings`** in `intf` — a hand-rolled `isEmpty`/`notNull` in a project
  that already has Guava, Commons Lang and Spring's `StringUtils`. All four are used in different files.

### **Implicit behaviour worth knowing [OBS]**
1. **`com.iggroup.external.*` is outside the component-scan root.** `@SpringBootApplication` sits on
   `com.iggroup.wt.cardvalidation.CardValidationServiceApplicationInitializer`, so scanning covers
   `com.iggroup.wt.cardvalidation` only. `BannedCountriesDaoImpl` and `BannedCountriesServiceImpl`
   carry `@Component` **which is inert** — they exist as beans solely because `CountriesConfig`
   declares them explicitly. Two consequences: (a) the `@Component` annotations are misleading
   decoration; (b) moving the scan root or adding `scanBasePackages` would create **duplicate beans**
   and make the by-type `BannedCountriesService` injection in `RestrictedCountriesValidationRule`
   ambiguous — it currently resolves by parameter-name coincidence.
2. **`@EnableConfigServer` + `bootstrap: true` in a business app** — the app serves and consumes its
   own config. Every test context and every local run must deal with the git self-bootstrap.
3. **`@ConfigurationPropertiesScan(basePackageClasses = BinConfig.class)`** is how `BinConfig` becomes
   a bean; `BinConfig` *also* carries a redundant class-level `@ConfigurationPropertiesScan`.
4. **`@RefreshScope` + `@PostConstruct` is the override-map mechanism.** `BinConfig.post()` rebuilds
   `overriddenBinRangeMap` from the bound `overridenBins` map on every refresh, because a refresh
   re-creates the bean. Elegant — and completely undiscoverable from the runbook, which names the
   wrong bean (§9).
5. **`@WebFilter` without `@ServletComponentScan` silently registers nothing** (§13). Reusable trap.
6. **`DmlcErrorLoggingAutoConfiguration` is explicitly excluded** from `@SpringBootApplication`
   — an IG EMB JMS auto-config deliberately switched off. **[UNK]** why.
7. **`metrics-goldensignal-autoconfiguration` excludes `com.iggroup.mantis:filters-spring`** in the
   root pom — **[INF]** to avoid clashing with this app's own filters.
8. `BinConfig` is a Lombok `@Data`, so `overriddenBinRangeMap` (a derived field) has a public setter
   and is nominally bindable as a config property. Harmless today; a trap for a future binder change.

---

## 18. Legacy / Historical Discoveries

**Two decades visible in one tree.** Datable strata:

| Era | Evidence |
|---|---|
| 2007 | `CardCommand` header: *"@Author: Omar Yasseen, @Date: 2 May 2007"*, `Copyright (c) 2007`; `CardInfoHelper` SVN keyword `$Id: … 26332 2007-04-25 … yasseeno $` |
| 2010s | `BasicCardNumberValidation` `$Id: … 2014-07-18 … rajur $` linking to a **VersionOne** story URL; Apache ORO (retired 2010); `Hashtable`/`Enumeration`; raw `Map` fields |
| ~2020 | Bamboo build links; `mvn tomcat7:run`; `cargo-maven2-plugin` |
| ~2023–24 | Spring Boot migration; JDOM2; Lombok; the `intf`/`impl` split |
| 2025–26 | Records, pattern switch, Guava `RangeMap`, springdoc, Testcontainers, **Spring Boot 4.1.1** |

**Incomplete migrations, all still load-bearing or visibly broken:**
- WAR → executable jar: `SpringBootServletInitializer`, the `pay-cardvalidation-war` DM entry, the
  `cd war` run scripts, and the three `@WebFilter`s are all residue (§2, §13).
- `README.md` documents a **Bamboo** build under a heading that links to **GitLab pipelines**, and
  gives a `GET` example for a `@PostMapping` route.
- `.gitattributes` (175 lines) lists paths under
  `resource/src/main/resources/{dev,test,production,demoproduction}/properties/cardvalidation/…` — a
  directory layout that no longer exists (it is now `properties/<tier>/`). A third artefact of the same
  drift as §15.
- `run_application.sh` still calls `tomcat7:run`; the README's own Debug section instructs replacing
  `cargo-maven2-plugin` with `cargo-maven3-plugin` — advice for a `war/pom.xml` that no longer exists.

**Evolution clue:** the modern path was clearly built as a *replacement* for the legacy one (Worldpay
BIN DB supersedes DataCash + master-bindb + per-PSP CSVs), but the cutover stalled. 1,129 calls in 60
days keep ~1,900 lines of the riskiest code, 180 MB of CSVs, a 32-class vendored SDK, and a second
block list alive.

### The Spring Boot 4 migration (just merged at HEAD)
`docs/spring_boot4_migration/` — 13 documents, a 5-phase process with a scored risk register, a
learnings log, a deprecation register and per-dependency assessments. Substance worth keeping:
- **The migration was a verification pass, not a code change.** `learnings.md`: *"This app was already
  on the final target (Boot 4.1.0 / Spring Cloud 2025.1.2 / Spring 7.0.8 / Jackson 3.1.5 / Jakarta EE
  11 / Hibernate 7.4.1) before Phases 3–4 ran … Do NOT execute Phase 4's literal 3.3→4.1 climb on an
  app already at target (it would mean downgrading to 3.3 first)."*
- **An escalation was raised and then withdrawn.** The `jakarta-jms-*` family was ruled `ESCALATE`
  (compiled against Spring 6 / Jackson 2.15.4), then closed: *"Initial ESCALATE verdict was wrong …
  Always cross-check sister repos before escalating an internal lib"* — `wallet-payments`
  `CAMP-782-pr15` already ran `250506.080526-cb1ef` on SB4.1.1.
- **Three reusable Snyk/Axis false-positive patterns**: check a library's *parent* POM Spring Boot
  version before trusting a bytecode scanner's Jackson-2 flag (`springdoc-openapi-starter-common:3.0.3`
  and `swagger-core-jakarta:2.2.47` are SB4-targeted; `tools.jackson.core:jackson-databind:3.1.5`'s
  dep on `jackson-core/2.21.0` is the Jackson 3→2 compatibility shim, not a real Jackson 2 dep).
- **The permanent accepted state**: 4 × Jackson 2.x Snyk pins held only because
  `jakarta-jms-metrics-common` drags Jackson 2.15.4 in transitively. App source has **zero** Jackson 2
  imports. Removal condition: EMB rebuilds that artifact against Jackson 3.
- Also: `dependency_list.csv` was stale in Phase 1 — regenerate before treating it as ground truth;
  and read BOM POMs from `~/.m2` directly rather than trusting the effective-POM's merged
  `<dependencyManagement>`.

---

## 19. Patterns & Conventions

### Design patterns
- **Chain of Responsibility** — `BinValidationService` over `List<ValidationRule>`, assembled in
  `BinValidationConfig`. First failure wins. The one genuinely clean design in the repo.
- **Command** — `CardCommand`/`ValidateCardCommand` + `?action=` dispatch (2007 vintage).
- **Static one-way transformers** — `<From>to<To>` classes with a single static `transform`
  (`BinInformationRequestDTOtoValidateCardRequest`, `WorldpayToDomainTransformer`,
  `WorldpayCardClassToDomainCardType`). Consistent, testable, no MapStruct/ModelMapper.
- **Value objects** — `record WorldpayBinInformation` for hot-path data; Lombok `@Builder` elsewhere.
- **Anti-corruption layer** — `com.iggroup.external.*` / `com.datacash.*` as explicit "not ours"
  packages, aligned with the coverage excludes. A convention worth preserving.

### Conventions
- **Naming**: `intf` = contracts + DTOs (`*DTO`) + shared enums; `impl` = everything else.
  `service/<psp-or-source>/` groups by *data source*, not by capability.
- **Logging**: structured `key=value` in newer code (`method=getBinInformation, binNumber={}`),
  string concatenation in older code (`"the site is " + site`). INFO is the default for
  request-scoped detail throughout.
- **Errors**: modern path → typed exception + `@ExceptionHandler` → `RestError` DTO; legacy path →
  `String[] errors` on a mutable public-field result object, rendered into XML.
- **Mutable result objects**: `CardValidationResult` has public non-final fields mutated across a dozen
  methods and constructed with a **14-argument positional constructor**. The chief readability tax on
  the legacy path.
- **Indentation**: 3 spaces in newer files, 4 in older ones. `lombok.config` present.

---

## 20. Important Discoveries (Ranked)

1. **Every server-side error becomes an empty HTTP 400.** `@ExceptionHandler(Exception.class)` and
   `@ExceptionHandler(NullPointerException.class)` both return `void` with `@ResponseStatus(BAD_REQUEST)`.
   Callers cannot separate bad input from a broken service, and **the 5xx rate — the primary error
   signal in the golden-signal dashboards — stays at zero during an outage**. Highest-impact fix:
   let unexpected exceptions be 5xx with a correlation id.

2. **Committed Oracle credential.** `MIDDLEWARE` / `Fjdj3od#sjk3f0Y` against `dealuat` in
   `application-{DEV,TEST,UAT}.yml`, present throughout a 517 MB git history. **Rotate, don't just
   delete.** LIVE/DEMO already do this correctly (empty files, config server), so the fix pattern is
   in the repo already.

3. **Cardholder data at INFO on the legacy route.** `CardCommand.getRequestMap()` logs every request
   parameter except `pan` — which means **`cv2` is written to the application log**. PCI-DSS 3.2. Plus
   `pan` interpolated into a client-visible error string in `DataCashCardValidation`, raw
   `e.getMessage()` written to the response, and the full BIN response DTO logged per request.

4. **The 114 MB BIN CSV, and the loader around it.** 799,714 rows in one heap-resident
   `TreeRangeMap`; `.git` is 517 MB and grows ~114 MB per BIN refresh with no LFS; the "concurrent"
   loader achieves zero parallelism, holds every row in an unbounded task queue, and mis-measures its
   own duration; and a single malformed row aborts the load while the app **still starts and serves
   400s**. The current file is clean (verified: all 799,714 rows exactly 24 fields), so this is a
   next-file-drop risk, not a live defect.

5. **The legacy engine is 1,129 calls/60 days but carries the concentrated risk** — ~1,900 lines,
   a 32-class vendored 2007 SDK, the second block list, the PAN-in-error-string, the non-thread-safe
   `CardValidator` init, **and it is excluded from the 75 % coverage gate**. Real project-wide line
   coverage is ~52 %; the 77 % baseline describes the modern surface only (the repo says so
   explicitly, to its credit). Decommissioning this route is the single highest-leverage piece of
   work available.

6. **Two independent accidents are what keep the test-card bypass safe.** `QuickGatewayCardValidator`
   can turn a DataCash **rejection into an acceptance**; in production it is gated only by a **zero-byte
   CSV**, and it is separately unreachable only because `pan` is truncated to 6 digits before it is
   compared against 16-digit test PANs. Neither is a control anyone chose.

7. **Two block lists for the same three BINs** — one hot-reloadable via config server, one a
   hard-coded `asList` requiring a release. Nothing keeps them in sync, and each route reads only one.

8. **Three `@WebFilter`s are silently unregistered** (no `@ServletComponentScan`, no WAR). The version
   header and IG cluster-detail logging are absent from production; the `@Deprecated`
   `_method` HTTP-verb-override filter is inert **and would be re-armed by the obvious fix**.

9. **Unknown `websiteId` silently defaults to `SPREAD_BETTING`** (`"".equalsIgnoreCase("C")` → false),
   so a typo'd or newly-provisioned site is checked against the wrong banned-country list with no
   warning logged. Banned-countries data itself can also go **stale indefinitely** — a failed JMS
   reset is logged, acked, and never retried, with no TTL and no cache-age health check.

10. **Documentation and build config have drifted together, along one shared wrong path.** The
    `resource` assembly's `dev`/`common` fileSets, the README's BIN-update runbook, and
    `.gitattributes` all reference `src/main/properties/…` layouts that no longer exist — so the
    dev tier ships **no properties at all** and the documented BIN-update procedure would write 114 MB
    into a directory nothing reads. Also: `README.md` names the wrong refresh bean
    (`BinValidationConfig`, which has no `@RefreshScope`; it is `BinConfig`); `/monitor/version` is the
    busiest route in the service (243 k calls, 9× the business traffic); `opencsv` is a dependency with
    zero usage; and **both `.snyk` ignores expired 2026-07-29**, over a month ago.

---

## 21. Unknowns

- **`-Xmx` and the real heap cost of the BIN map.** Sizing lives in deployment templates outside this
  repo. Worth a heap histogram after startup — the string duplication across 800 k rows suggests
  interning or a `String` pool would pay for itself.
- **Is the shared durable JMS subscription intentional?** With `setSubscriptionShared(true)` and a
  per-*application* subscription name, a banned-countries update reaches one instance, but every
  instance has its own Ehcache. Needs confirming against the deployed instance count per site (§11).
- **Who calls `/controller`, and can it be retired?** 1,129 calls/60 days. Identifying the ~2 callers
  would unlock the largest cleanup in the repo.
- **Why was `TASTYFX-883: Observability config for CVS` reverted** (`5b43193`)?
- **Why is `DmlcErrorLoggingAutoConfiguration` excluded?**
- **Do the committed non-prod credentials have a GitGuardian allow-list entry**, or do they predate the
  scan component?
- **Is `@EnableConfigServer` serving other clients**, or only self-bootstrapping this app? `searchPaths`
  is scoped to `CardValidationService`, which suggests self-only, but `prefix: spring/config` implies a
  served API surface.
- **The `it` tier is absent from the `resource` assembly** — how do integration-test properties reach
  the runtime? (Probably classpath-only via `application-it.yml`; not traced.)
- **Overlapping Worldpay BIN ranges**: how often does the `subRangeMap` fallback find >1 match, and is
  the lowest-range winner the intended answer? The count is logged but never flagged.

---

## Investigation Checklist
- [x] Module structure explored
- [x] Maven configuration analyzed
- [x] Spring version and tech determined
- [x] Entry points identified (4 routes + 1 JMS topic, cross-checked against 60-day traffic)
- [x] Flows traced (all 3 validation flows)
- [x] State machines found — **none exist**
- [x] Consistency mechanisms understood (4 refresh paths, no TTL anywhere)
- [x] Persistence patterns mapped (classpath-as-database + 2 read-only procs)
- [x] External integrations documented (all file-based; zero outbound HTTP)
- [x] Concurrency model understood (BIN loader, lazy `CardValidator`)
- [x] Security/observability reviewed
- [x] Error handling analyzed (fail-open/closed table)
- [x] Configuration understood (4-layer precedence, broken assembly)
- [x] Tests analyzed (2 gates, different denominators)
- [x] Custom libraries identified (`com.datacash.*`, `com.iggroup.external.*`)
- [x] Historical patterns noted (2007 → 2026 strata)
- [x] Conventions documented

---

## Files Referenced

**Entry points**
- `impl/src/main/java/com/iggroup/wt/cardvalidation/application/Controller/BinValidationController.java`
- `impl/src/main/java/com/iggroup/wt/cardvalidation/application/action/verify/CardValidationController.java`
- `impl/src/main/java/com/iggroup/wt/cardvalidation/application/command/ValidateCardCommand.java`
- `intf/src/main/java/com/iggroup/wt/cardvalidation/application/command/CardCommand.java`
- `impl/src/main/java/com/iggroup/wt/cardvalidation/application/Controller/config/VersionController.java`
- `impl/src/main/java/com/iggroup/wt/cardvalidation/listener/BannedCountriesMessageListener.java`

**Modern BIN path**
- `impl/src/main/java/com/iggroup/wt/cardvalidation/service/worldpaybindb/BinFileLoader.java`
- `impl/src/main/java/com/iggroup/wt/cardvalidation/service/worldpaybindb/BinLookupService.java`
- `impl/src/main/java/com/iggroup/wt/cardvalidation/validations/*.java` (6 rules + chain)
- `impl/src/main/java/com/iggroup/wt/cardvalidation/config/{BinConfig,BinValidationConfig}.java`
- `impl/src/main/java/com/iggroup/wt/cardvalidation/utils/{BinUtils,CardValidationUtils}.java`
- `impl/src/main/java/com/iggroup/wt/cardvalidation/domain/worldpay/WorldpayBinInformation.java`

**Legacy path**
- `impl/src/main/java/com/iggroup/wt/cardvalidation/service/datacash/DataCashCardValidation.java` (544 lines)
- `impl/src/main/java/com/iggroup/wt/cardvalidation/service/datacash/{CardValidator,QuickGatewayCardValidator,BasicCardNumberValidation}.java`
- `intf/src/main/java/com/iggroup/wt/cardvalidation/service/{CardValidationService,CardValidationConstants}.java`
- `impl/src/main/java/com/iggroup/wt/cardvalidation/service/{noire,streamline,aib,masterbindb}/`

**Countries / persistence**
- `impl/src/main/java/com/iggroup/external/wt/countries/eai/dao/BannedCountriesDaoImpl.java`
- `impl/src/main/java/com/iggroup/external/wt/countries/eai/dao/jdbc/GetSiteTypeStoredProcedureImpl.java`
- `impl/src/main/java/com/iggroup/wt/cardvalidation/config/{CacheConfig,DataSourceConfiguration,CountriesConfig}.java`

**Config / infra**
- `impl/src/main/resources/{bootstrap.yml,application.yml,application-{DEV,TEST,UAT,LIVE,DEMO,it}.yml}`
- `resource/src/main/assembly/resources.xml`
- `resource/src/main/resources/properties/{prod,uat,test,dev,it}/`
- `pom.xml`, `coverage/pom.xml`, `.snyk`, `.gitlab-ci.yml`, `.ci/card-validation-service-cd.yml`
- `.coverage-baseline-acceptance.properties`, `.gitattributes`

**In-repo documentation (read this before re-deriving anything)**
- `docs/spring_boot4_migration/{learnings.md,risk-register.md,phase5-complete.md,deprecation-register.md}`
- `docs/acceptance-testing/{route-inventory.md,limitations-and-future-work.md,code-coverage-and-gate.md}`
- `docs/updating-worldpay-bin-file.md` (**authoritative** BIN-update runbook), `README.md` (materially stale — see §15)
