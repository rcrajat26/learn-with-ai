# Repository Discovery — payments-gateway

**Repository:** `_Codes/payments/payments-gateway` (module of the `payments` repo group)
**Date:** 2026-09-05
**Branch / HEAD:** `main` @ `7bd62abd`
**Analysis Depth:** ~1 session, evidence-based (all claims below cite a file)
**Size:** 768 `.java` files (499 main / 269 test), ~27.5k LOC main, 10 Maven modules

---

## 1. System Mental Model

payments-gateway is IG Group's **single HTTP front door for the entire payments estate**. It is a
Spring Boot 3.5 / Spring Cloud Gateway **MVC** (servlet, *not* reactive) application that does three
jobs: (a) **proxies** ~130 declared route groups to ~25 downstream payment services, (b) **authenticates
and authorises** every hop — inbound with client tokens (CST), staff tokens (XST) and service JWTs;
outbound by minting a fresh service JWT per call — and (c) hosts a **small set of its own aggregation
APIs** (`/functionalities`, `/withdrawaloptions`, `/paymentsPageUrl`, `/verification*`) that fan out to
many backends and compose a client-facing view of "what payment features can this client/account use
right now". It owns **no database and no message broker** — all state lives downstream — so its real
complexity is auth topology, per-path filter wiring, and ~40 JMX-controlled feature flags that gate
regional and per-account rollout.

---

## 2. Repository / Module Architecture

Maven aggregator, `packaging=pom`, parent `com.iggroup.wt.maven3:wt-maven-project:3.9.0`
(root `pom.xml:5-14`, modules `pom.xml:17-29`).

| Module | Java files (main) | Purpose |
|---|---|---|
| `service-api` | 12 | Published DTO contract for *other* apps (`ClientContextDTO`, `FunctionalityDTO`, withdrawal DTOs). No logic. |
| `domain` | ~120 | Business rules + **`port/` interfaces**. Zero Spring-web, zero HTTP. |
| `integration` | ~330 | Everything infrastructural: route config, filters, Feign clients, **`web/adapters/` port implementations**, controllers, feature flags, observability. **This is where 80% of the app lives.** |
| `war` | 0 | Packaging only (`WEB-INF/jsp/unauthorised.jsp`, `pendingpayment.jsp`). |
| `jar` | 2 | `PaymentsGatewayRunner` — `SpringApplication.run(...)` for local/embedded runs. |
| `resource` | 0 | Externalised property tree, assembled into per-env ZIPs (`resource/src/main/assembly`). |
| `acceptance` | 19 (test) | Cucumber + Testcontainers + WireMock black-box suite (74 feature files). |
| `post-deployment-tests` | 4 (test) | Smoke tests run per environment post-deploy, incl. `*-dark` profiles. |
| `docs` | — | PlantUML models + **`docs/bola/` — 30 security audit findings docs**. |
| `coverage` | — | JaCoCo aggregation module only. |

```
service-api  (published DTOs)
     ▲
     │
  domain  ──── port/*Port (16)  ◄──────┐  dependency inversion
     ▲        repository/port/*Port(4) │
     │                                 │
 integration ── web/adapters/*Adapter (18) implements the ports
     │        ── config/RouterConfig (routing)
     │        ── web/filter/* (servlet filters) + prefilters/* (route filters)
     ▼
  war / jar  (packaging + bootstrap)
```

**ARCHITECTURE DETECTED — Hexagonal (Ports & Adapters), partially applied.** See §5.

---

## 3. Maven / Dependency / BOM Behavior

| Aspect | Finding |
|---|---|
| Spring Boot | **3.5.16** (`pom.xml` `<spring-boot.version>`) |
| Spring Cloud | **2025.0.3** (`<spring-cloud.version>`) |
| Java level | **17** (`<java.version>`) |
| Parent POM | `com.iggroup.wt.maven3:wt-maven-project:3.9.0` — org-wide plugin/enforcer defaults |
| Version scheme | `${revision}` = `SNAPSHOT` locally; CI stamps a date-hash version (see downstream deps like `221219.060045-7087b`) |
| Key BOMs imported | `spring-boot-dependencies`, `spring-cloud-dependencies`, `jackson-bom` 2.21.4, `cucumber-bom` 7.18.0, `assertj-bom`, `testcontainers-bom` 1.21.4 |
| Notable plugins | `maven-igi-plugin` (IG internal), `jacoco` 0.8.15, `sortpom`, `extra-enforcer-rules` + `ossindex-maven-enforcer-rules` (**dependency-vuln enforcement at build time**), `maven-war-plugin`, `tomcat7-maven-plugin` (legacy local run) |
| Exclusion discipline | Explicit `<exclusions>` on org libs, e.g. `wt-sso-securedhttpclient` excludes `*:httpclient` (`pom.xml:178-187`) to force HttpClient 5 |

### **BOM / AUTO-CONFIGURATION discoveries**

- **`@SpringBootApplication(exclude = {LdapAutoConfiguration, DataSourceAutoConfiguration})`**
  (`integration/.../PaymentsGatewayApplication.java:9`). Both are excluded *because transitive org
  libraries drag `spring-boot-starter-data-jpa`/LDAP onto the classpath* — the app has no datasource.
  Without these exclusions startup fails on a missing JDBC URL. Also `ojdbc8` is in `<properties>` but
  no datasource exists — pure transitive-management residue.
- **`spring.main.allow-bean-definition-overriding: true`** (`common/application.yml:11`). Silently
  permits a later bean definition to win. Given ~10 `@Configuration` classes plus several `@Import`ed
  library configurations, **any duplicate bean name is resolved by load order, not by error.** This is
  a latent trap for anything added to `web/configuration/`.
- **`spring.main.web-application-type: servlet`** (`common/application.yml:12`) — forces the servlet
  stack even though `spring-cloud-gateway` also ships a WebFlux variant.
- Custom `BeanFactoryPostProcessor` (`config/CustomBeanExclusionProcessor.java`) reaches into the bean
  factory to force a **library-provided bean named `exporterCP` to `lazyInit=true`** — a workaround for
  an eagerly-initialising JMX exporter in an org starter. Undocumented as to which library.

---

## 4. Java / Spring Technology Usage

- **Spring Cloud Gateway Server MVC** — `spring.cloud.gateway.server.webmvc.enabled: true`,
  `http-client.type: AUTODETECT` (`common/application.yml:26-31`). Routing is `RouterFunction<ServerResponse>`
  beans with `HandlerFunctions.https(...)`, **not** the reactive `RouteLocator`.
- **Spring MVC** — 15 `@RestController`s (`web/controllers/`), plus JSP view resolution
  (`spring.mvc.view.prefix: /WEB-INF/jsp/`) purely for an `unauthorised.jsp` error page.
- **Spring Cloud OpenFeign** — 33 Feign interfaces in `web/external/api/`, enabled by
  `@EnableFeignClients(basePackages = "...web.external.api")` (`RestClientConfiguration.java`).
  **Circuit breaker explicitly disabled** for Feign (`spring.cloud.openfeign.circuitbreaker.enabled: false`).
- **Spring Security is NOT used.** Despite the readme's claim, there is no `SecurityFilterChain`, no
  `@EnableWebSecurity`, no `spring-boot-starter-security` config. `web/configuration/SecurityConfiguration.java`
  only builds a `JwtClaimsParser` from the internal *mantis* library. **All authentication is hand-rolled
  servlet `Filter`s + hand-wired route filters.**
- **Java features actually used:** `record` (`AccountOwnershipFilter.ValidatedIdentifier`), switch
  expressions (`AccountOwnershipFilter.isOwned`, `IGTelemetryClusterDetailsProvider`), `CompletableFuture`,
  `BiPredicate` enums (`SimpleClientAndAccountPredicates`, `CompositeClientAndAccountPredicates`),
  streams throughout. **No sealed types, no virtual threads, no reactive types.**
- **Lombok + MapStruct** — `@RequiredArgsConstructor`/`@Slf4j` are near-universal; MapStruct 1.6.3
  for `mappers/FunctionalityMapper`, with the lombok-mapstruct binding declared.

---

## 5. Architecture Detected

**Pattern: Hexagonal (Ports & Adapters) over a Gateway/Proxy core — high confidence, partially applied.**

**Evidence**
- `domain/.../port/` holds **16 outbound port interfaces** (`CardPaymentPort`, `AccountValuationPort`,
  `FeatureFlagPort`, `BonusWithdrawalLimitPort`, …) and `domain/.../repository/port/` a further 4
  (`ClientDetailsPort`, `AccountDetailsPort`, `PaymentsPort`, `TrialAndTaxAccountDetailsPort`).
- `integration/.../web/adapters/` holds **18 matching adapters**, each wrapping a Feign client.
  Dependency direction is strictly `integration → domain`; `domain` has no `org.springframework.web`
  or `feign` import.
- Domain services (`service/functionality/*`) are pure orchestration over ports.

**Where the hexagon leaks (all three matter):**
1. **A static service locator escapes DI.** `DomainUtilsRegistry` (`domain/.../repository/DomainUtilsRegistry.java`)
   is a mutable static holder populated by `PortAdapterRegistry.@PostConstruct` and read statically by
   `CSTAuthenticationFilter` via `getPortAdapterRegistry().getClientDetailsPort()`
   (`web/filter/CSTAuthenticationFilter.java:113`). This exists because servlet `Filter`s are registered
   as `FilterRegistrationBean`-wrapped `new` instances, so constructor injection wasn't available at the
   point the filter was written. **Consequence:** startup-order coupling (a request arriving before
   `@PostConstruct` NPEs), untestable statics, and an invisible `domain → integration` runtime edge.
   The newer `CstAuthorizationFilter` does **not** do this — it takes `ClientDetailsPort` via constructor.
2. **`domain` still contains DTOs and URL-building.** `domain/.../domain/clientmaintenance/dto/ClientDTO`
   and `UrlBuilderService`/`UrlGenerator` are transport/presentation concerns living in the core.
3. **Adapters carry business logic.** e.g. `web/transformers/*DTOTransformer` (9 classes) do domain
   mapping *and* eligibility shaping outside the domain module.

**Trade-offs**
- ✅ Domain rules (functionality eligibility, page-URL selection) are genuinely unit-testable without HTTP.
- ✅ Swapping a backend = new adapter, no domain change.
- ❌ The proxy half of the app (RouterConfig + filters) has no such structure: `RouterConfig.java` is a
  **1,865-line single class with 130 route beans** and is the de-facto architecture document.

---

## 6. Important Execution Flows

### Flow 1 — Proxied client request (the dominant path, e.g. `POST /cardpayments/api/internal/withdrawal`)

```
Client
 → Tomcat  (context-path /payments-gateway, access log w/ spanId+traceId)
 → SERVLET FILTER CHAIN  (FilterConfiguration.java, explicit setOrder)
     HIGHEST_PRECEDENCE      CORSFilter, UserAgentAuditFilter,
                             AllowOnlyInDevTestUatFilter, CacheRequestBodyFilter
     HIGHEST_PRECEDENCE+1    shiftJisCharacterEncodingFilter, ServiceAuthenticationFilter (JWT)
     HIGHEST_PRECEDENCE+2    CSTAuthenticationFilter, XSTAuthenticationFilter
     HIGHEST_PRECEDENCE+3    TransactionalTokenValidationFilter
     HIGHEST_PRECEDENCE+4/5  CardPayments 3DS / 3DS2 external authorisation
     HIGHEST_PRECEDENCE+6    JwtAuthorizationFilter
   (each filter's applicability = inclusion/exclusion URL lists in common/application.yml `servlet-filters`)
 → TracingSupportFilter  (OncePerRequestFilter → puts traceId/spanId on the request for logback + access log)
 → SPRING CLOUD GATEWAY RouterFunction  (RouterConfig bean, most specific @Order wins)
     .before(stripPrefix(1))          drop the /<service> segment
     .before(rewritePath(...))        for the "-internal" smart routes
     .filter(cstAuthorizationFilter)  route-scoped CST (newer path)
     .filter(xstInjectionFilter)      mint service JWT → X-SECURITY-TOKEN (outbound auth)
     .filter(accountIdInjectionFilter / clientIdInjectionFilter / userAgentInjectionFilter / …)
     .filter(gated(featureFlag::isXEnabled, accountOwnershipFilter))   BOLA check, JMX kill-switchable
 → RestClientProxyExchange → downstream service over https
```
**Key files:** `web/configuration/FilterConfiguration.java`, `config/RouterConfig.java`,
`resource/src/main/resources/properties/common/application.yml` (`servlet-filters:` §).
**Interesting detail:** there are **two independent CST implementations** running in the same app — see §20.1.

### Flow 2 — Gateway-owned aggregation API (`POST /functionalities`)

```
POST /functionalities
 → servlet filters (CST authenticates, sets RequestAttribute.CLIENT_ID + CLIENT_DTO)
 → FunctionalityController
 → FunctionalityRequestMapper (MapStruct) → domain FunctionalityRequest
 → FunctionalityProvider.getPaymentFunctionalities()
      streams over Collection<PaymentsFunctionality> (11 injected strategies:
      Deposit, Withdraw, CardList, CashInTransit, CurrencyConversion, TransferFunds,
      Verification, WithdrawalPassword, HowToDeposit, HowToWithdraw, …)
 → each PaymentsFunctionality.create() [Template Method]
      → additionalConditions(ctx, acc)      feature flags + client/account predicates
      → PageUrlProvider.get*Url(...)
           → PaymentsServiceFactory.getPaymentsService()  [first @Order-matching strategy wins]
 → FunctionalityMapper → List<FunctionalityDTO>
```
**Key files:** `domain/.../service/functionality/` (24 classes), `web/controllers/FunctionalityController.java`.
**Interesting detail:** each functionality calls the port layer independently, so a single
`/functionalities` call can fan out to many downstream services **serially**; there is no batching.

### Flow 3 — Aggregated verification requests (the only concurrent flow)

`GET /api/external/client/{clientId}/verificationRequests` →
`ExternalVerificationRequestsServiceImpl` fans out 3 Feign calls on a **dedicated 10-thread daemon pool**
with a **30s per-source timeout** and returns partial results plus a
`meta.sources = {bank: success|timeout|error, …}` map. See §12 for why its sibling class is worse.

---

## 7. Domain / Payment Concepts

This service **does not own the payment lifecycle** — no AUTH/CAPTURE/SETTLE, no ledger, no money
movement. Its domain is **entitlement and navigation**: *given this client + account + region + flags,
which payment functionalities are available and where do they live?*

**Key concepts**
| Concept | Where implemented |
|---|---|
| `ClientContext` / `ClientAccount` | `domain/.../domain/` — the two inputs every rule takes |
| `Functionality(name, enabled, config)` | `domain/.../domain/Functionality.java` — the unit of entitlement |
| `NavigationUrlType` / `PageKey` | destination kinds (`NONE` = "not available") |
| Eligibility predicates | `SimpleClientAndAccountPredicates` / `CompositeClientAndAccountPredicates` — enums implementing `BiPredicate<ClientContext, ClientAccount>`, composed into rules |
| `Money` / `Currency` | `domain/.../domain/deposit/` — value objects, gateway never arithmetics on them |
| `WithdrawalOption` / `DepositOption` / `DepositType` | the presented method list, priority-ordered by `igmarkets.product-configurations` YAML (`BANK 1, PAYID 2, CARD 3, APPLE_PAY 4`) |
| `FundingRestrictionType` | inbound from Client Maintenance, injected downstream by `FundingRestrictionInjectionFilter` |
| Regional variants | Japan (`domain/japanese/`, Shift-JIS encoding filter, `withdrawalPassword` for `igjp`), Singapore (PayNow/eGiro), Australia (PayID), US (ACH/OpenBanking) |

**Payment Lifecycle:** *Not present in this module.* Only **verification** request states exist, and they
are read-through from downstream (`VerificationStatus`, `BankVerificationResult`, `BankDepositVerificationResult`).

---

## 8. State Machines / Workflows

**NO STATE MACHINE DETECTED.** Deliberate and correct for a stateless proxy — verified by exhausting all
enums in `domain`/`integration`/`service-api` (30 enums, all classification/type enums, none with
transition tables or guarded setters).

The closest things to workflow are:

**(a) `PageUrlService` precedence chain** — a Chain-of-Responsibility resolved by explicit `@Order`,
first `applies()` wins (`PaymentsServiceFactory.getPaymentsService`):
```
@Order(10) DemoClientPageUrlService
@Order(20) RegistrationClientPageUrlService
@Order(30) FirstFundRequiredRoadblockPageUrlService
@Order(35) TrialActivePageUrlService
@Order(40) RoadblockPageUrlService
@Order(50) DocumentsRequiredPageUrlService
@Order(60) RegularClientPageUrlService   ← also the hard-coded fallback
```
Enforcement is *only* the `@Order` annotations — remove one and behaviour silently changes. Note the
double safety: `findFirst().orElse(regularClientPageUrlService)`, so `@Order(60)` is both last in the
chain and the explicit default.

**(b) `VerificationStatus.from(String)` fails quiet** — an unrecognised downstream status maps to
`NOT_ADDED`, not an exception (`domain/.../domain/VerificationStatus.java:14-21`). A downstream renaming
a status silently degrades a client's UI to "no payment method added" rather than erroring.

**(c) Light/dark deployment state** — `IGTelemetryClusterDetailsProvider.convertDarkLightState()` maps
`light|live → active`, `dark → standby`. `ResetOnSwitchGoldenSignalReporterProvider` **resets all golden-signal
metrics when the cluster flips** (`config/GoldenSignalsConfiguration.java:83-85`), so this is an
active/standby (blue-green) topology, confirmed by `post-deployment-tests/src/test/resources/application-{test,uat,demo,live}-dark.properties`.

---

## 9. Transactions / Consistency / Idempotency

### Transaction strategy
**There are zero `@Transactional` annotations in the module.** No datasource, no JPA
(`DataSourceAutoConfiguration` excluded). Nothing to roll back.

### Consistency model
- **No consistency guarantees are offered or needed** for proxied traffic — the gateway is a pass-through.
- **Gateway-owned aggregation APIs are read-only and eventually consistent by construction**: each
  functionality/withdrawal-option reads a different backend at a different instant. A `/functionalities`
  response can mix a stale balance with a fresh verification status. Nothing reconciles this.
- **Per-request memoisation is the only cache.** `ClientOwnershipChecker.resolveClientDTO` caches the
  Client Maintenance `ClientDTO` as a `RequestAttribute.CLIENT_DTO`, **wrapped in `Optional` so that a
  genuine "client not found" is also cached** (absent attribute = not fetched; present-empty = fetched,
  none). This guarantees ≤1 Client Maintenance call per HTTP request no matter how many identifiers a
  route validates (`ownership/ClientOwnershipChecker.java`). Both CST filters pre-populate it while
  authenticating so the first ownership check doesn't re-fetch.

### **NO IDEMPOTENCY MECHANISM DETECTED**
Searched exhaustively for `idempoten*`, dedup, request-id keying: nothing. `requestId` appears only as a
*downstream* verification-request identifier passed through in path variables. **The gateway is not
idempotent and does not make downstream calls idempotent.** Two consequences worth naming:

1. **`DynamicBankDepositsHandler` retries a failed cloud call against the legacy backend**
   (`config/DynamicBankDepositsHandler.java:46-49, 62-66`): `catch (Exception e) → handleLegacyRequest(...)`.
   For a `POST` that already reached the Nomad backend but failed on the response leg, this is a
   **double-submit of a deposit initiation** with no idempotency key to protect it. Same shape in
   `DynamicPspMaintenanceHandler`.
2. **`HttpClientParamsConfiguration.retryCount = 3`** with `requestSentRetryEnabled = false`
   (`config/HttpClientParamsConfiguration.java:23-32`) — the safe combination (only retry if the request
   was never sent), and it applies to the SSO client only.

---

## 10. Persistence / Caching

### Primary store
**None.** No JDBC, no JPA, no NoSQL, no ORM. Every piece of state is fetched over HTTP per request.

### Caching
| Layer | Finding |
|---|---|
| Spring Cache | **Not enabled.** Zero `@Cacheable`/`@CacheEvict`/`CacheManager` in the codebase. |
| Ehcache | `org.ehcache:ehcache` is a declared dependency (`integration/pom.xml:275`) and `resource/.../common/payments-gateway-ehcache.xml` configures a 300s TTL cache for `uk.co.igindex.singlesignon.remoting.client.CachedClientTokenServiceRemoteClient` — **but that class is never instantiated.** Its only reference is a *commented-out field* in `CSTAuthenticationFilter.java:51` and an unused `import` on line 14. **The CST verification cache is dead configuration.** (§20.4) |
| Per-request | `RequestAttribute.CLIENT_DTO` memoisation (§9). |
| Feature-flag account sets | `ConcurrentHashMap.newKeySet()` in `mbean/BankDepositsCloudMigrationFeatureFlag.java:21` — the only concurrent collection in the app. |
| LDAP permission cache | `security.ldap.cacheMaxLimit: 500`, `cacheExpiryMinutes: 30` (`common/application.yml`) — consumed by an org library, not by app code. |

**Consistency risk:** because CST verification is uncached, **every single authenticated request makes a
synchronous `PUT /clienttokentwofactorauth` call to SSO** (`sso/SsoClientTokenCaller.java:26-32`) plus, for
account-scoped routes, a Client Maintenance `getClientDTO`. SSO is therefore on the critical path of
100% of client traffic with a pool of 100 connections and a 6.5s socket timeout (§12).

---

## 11. External Integrations

### REST / HTTP — the entirety of the integration surface
- **33 Feign clients** (`web/external/api/`) — Card Payments, Payments, Wallet, PayPal deposit +
  withdrawal, Bank Withdrawal/Maintenance/Verification, ACH, Funds Transfer, PSP Integration + Maintenance,
  Account/Client Maintenance, Account Valuation, Tax Wrapper, Trial Trading, Welcome Bonus, Cash-in-Transit,
  Open Banking, JWT Service, SSO, IgOne (BFB), IgMarkets Crypto, External Ledger, Tasty Balance.
- **~25 proxied backends** via `RouterFunction` (`RouterConfig.java`), URLs all `@Value`-injected from
  `${*.target.url}` / `${*.service.baseUrl}`.
- **Timeouts** (`common/application.yml`):
  - Gateway/Feign default: `connectTimeout 10000`, `readTimeout 30000`
  - `AccountValuationSummaryApi`: `3000 / 3000` (deliberately tight — it's on the withdrawal-options path)
  - Legacy `feign.client.config.default`: `connectTimeout 3000`, `readTimeout 5000` — **note both
    `spring.cloud.openfeign.client.config` and the deprecated `feign.client.config` trees are present
    with different values.** Which wins depends on Spring Cloud's relaxed binding; this is ambiguous
    configuration and should be collapsed to one tree.
- **Outbound auth patterns, three of them:**
  1. `XstInjectionFilter` / `ServiceTokenInjectionFilter` — mint a service JWT per proxied request and set
     `X-SECURITY-TOKEN`. On failure → **500, request rejected** (fail-closed, correct).
  2. `ServiceTokenInjector` / `AuthorizationInterceptor` — Feign `RequestInterceptor`s for adapter calls.
  3. `IgOneBalanceSummaryApiInterceptor` — OAuth2 client-credentials against Microsoft login. **See §20.3
     — this one re-fetches a token on every request and logs the token response.**
- **CDE / NONCDE split** — separate `CDE.payments-gateway-config.properties` and
  `NONCDE.payments-gateway-config.properties` per environment, and CDE-specific hostnames
  (`cde-ip1`, `router-cde-int`, `cdenew-dealingproxy`). This is the **PCI-DSS Cardholder Data Environment
  boundary**: card/wallet traffic is routed to CDE hosts through dedicated proxies with their own credentials.

### Message brokers
**NONE.** No Kafka, AMQ, RabbitMQ, SQS/SNS — verified by exhaustive grep. Correct and worth stating
explicitly, because it means **no replay, no ordering, and no async retry exist anywhere in this app**:
every failure is a synchronous HTTP failure surfaced to the caller.

### Failure modes
| Mechanism | State |
|---|---|
| Resilience4j circuit breaker | Configured (`slidingWindowSize 40`, `failureRateThreshold 30%`, `waitDurationInOpenState 60s`) but **applied via `@CircuitBreaker` on only 2 of 18 adapters** — `BankMaintenanceAdapter`, `BankVerificationAdapter`. And `spring.cloud.openfeign.circuitbreaker.enabled: false` means Feign clients get none automatically. |
| Retry | `resilience4j.retry.instances.default.maxAttempts: 1` — i.e. **retry is configured off**. `@Retryable` on `ClientMaintenanceApi` is commented out (lines 17, 21). |
| Fallback | Only in the two `Dynamic*Handler`s (fall back to the legacy backend) and in the two verification services (partial results). |
| `ig.hystrix.incident` block | Leftover config for a **library no longer on the classpath** (`common/application.yml`) — Hystrix has been removed. |

---

## 12. Concurrency / Threads

### Thread model
The app is **fundamentally thread-per-request** (Tomcat), with three concurrency exceptions:

| Site | Executor | Timeout | Assessment |
|---|---|---|---|
| `ExternalVerificationRequestsServiceImpl` | **dedicated** `Executors.newFixedThreadPool(10)`, daemon threads named `verification-fetch`, `@PreDestroy` shutdown | **30s per source**, cancel + `meta.sources` status | ✅ The reference implementation |
| `VerificationRequestsServiceImpl` | **`ForkJoinPool.commonPool()`** (bare `CompletableFuture.supplyAsync`, 4 futures) | **`future.get()` with no timeout** | ❌ See below |
| `CardPaymentAdapter` / `PaypalWithdrawalAdapter` `getWithdrawalSummary` | **`ForkJoinPool.commonPool()`** | none at the future | ❌ Same problem |
| `GoldenSignalsConfiguration` | `Executors.newSingleThreadScheduledExecutor()` for metric reset on light/dark switch | n/a | fine |

**Concurrency risk 1 — common-pool starvation on blocking I/O.** `ForkJoinPool.commonPool()` is sized
`availableProcessors - 1`. On a 4-vCPU container that is **3 threads shared process-wide**. Three
concurrent `/verificationRequests` (v1) calls, each issuing 4 blocking Feign calls, saturate it; every
other `supplyAsync` in the JVM (including the withdrawal-summary adapters on the `/withdrawaloptions`
path) then queues behind blocking HTTP. `ManagedBlocker` is not used.

**Concurrency risk 2 — unbounded `future.get()`.** `VerificationRequestsServiceImpl.getResult` calls
`future.get()` with no timeout, so a wedged downstream holds the Tomcat request thread for as long as the
Feign read timeout allows — and if the deprecated `feign.client.config` tree does *not* win, that is the
30s gateway default, not 5s.

**Context propagation** — MDC/`ThreadLocal` is **not** propagated across any `supplyAsync` boundary. The
`reqId`/`callerReqId` set by `TracingSupportFilter` are **request attributes**, not MDC, so logs emitted
from pool threads lose correlation. `UserAgentInitializerInterceptor` + the `user-agent-spring` library
put user-agent context in a `ThreadLocal` that is likewise not propagated.

**VIRTUAL THREADS: not used.** Given the app is ~100% blocking-I/O-bound fan-out with no shared mutable
state, `spring.threads.virtual.enabled=true` on Boot 3.5 + Java 21 would be an unusually clean fit — this
is the single highest-leverage performance change available, but it needs the Java level lifted from 17.

---

## 13. Cross-Cutting / Security / Observability

### Authentication — four mechanisms, layered
| Mechanism | Filter | Applicability | Notes |
|---|---|---|---|
| **CST** (client session token, header or cookie `CLIENT_SECURITY_TOKEN`) | `web/filter/CSTAuthenticationFilter` (servlet) **and** `prefilters/CstAuthorizationFilter` (route) | `cstAuthentication.inclusions: /*` — **on by default**, minus a ~110-entry exclusion list | Validates token at SSO, then asserts the requested `accountId` belongs to the token's client |
| **XST** (staff/service token) | `web/filter/XSTAuthenticationFilter` | small explicit `xstAuthentication.inclusions` list; `exclusions: /*` | Also used *outbound* by `XstInjectionFilter` |
| **Service JWT** | `security/ServiceAuthenticationFilter` + `web/filter/JwtAuthorizationFilter` | `serviceAuthentication.inclusions` (~50 internal endpoints) | Tried **first**; falls back to CST on failure unless CST-excluded |
| **Internal user (LDAP + IGIP permissions)** | `prefilters/InternalUserAuthorisationFilter`, `VerifyInternalUserIdExistsFilter` | per-route | Roles in `permissions.igThirtyDayPermissions` (`RG-IGIP-Payments-Edit`, …) |

Plus **payment-specific authorisation**: `MFAWithdrawalAuthorisationFilter` / `CardWithdrawalMfaFilter`
(step-up auth for withdrawals), `SignatureVerificationFilter` /
`OpenBankingSignatureVerificationFilter` (webhook signature verification),
`TransactionalTokenValidationFilter`, and `CardPaymentsExternalAuthorisationFilter` (3DS callbacks).

### Authorisation — the BOLA programme (**the single most important thing in this repo right now**)
`docs/bola/` contains **30 audit documents** and a rollup
(`vulnerable-apis-exposed-cst-authenticated-summary.md`) recording **61 endpoints across 12 services
that are reachable through this gateway, CST-authenticated, and still vulnerable** — because *CST proves
who you are but never checked that the account/client id in the request is yours*.

The fix is a shared, declarative filter:
- `prefilters/AccountOwnershipFilter` — validates identifiers from `PATH_VARIABLE`, `QUERY_PARAM`, or a
  dotted `BODY_FIELD` path (with `[*]` array wildcard), as `ACCOUNT_ID` (must be one of the client's
  accounts) or `CLIENT_ID` (must *be* the client). 10 pre-wired bean variants in
  `config/AccountOwnershipFilterConfig`.
- `ownership/AccountOwnershipValidator` — the counterpart for the gateway's **own** `@RestController`s,
  which `RouterFunction` filters can't reach.
- `ownership/ClientOwnershipChecker` — the shared rule + per-request `ClientDTO` cache.
- `mbean/AccountOwnershipFeatureFlag` + `featureflag/AccountOwnershipFeatureMBean` — **12 JMX kill
  switches**, one per backend service plus one global for gateway APIs, all defaulting to `true`, so a
  bad check can be reverted in production without redeploy.
- **74 Cucumber feature files**, the majority named `<service>-bola-<endpoint>.feature`, proving each fix.
- Two **repo-local Claude skills** (`.claude/skills/gateway-bola-ownership-fix`,
  `gateway-bola-acceptance-test`) codify the remediation and proof workflow.

**Three deliberate design decisions inside `AccountOwnershipFilter` you must know before touching it:**
1. **It no-ops when `RequestAttribute.CLIENT_ID` is blank** — because some routes legitimately accept
   XST/JWT service callers with no CST identity. So it must be wired **after** the route's authenticating
   filter, and it provides **no protection at all on a route whose CST filter didn't run**.
2. **An absent identifier is skipped, not rejected** (`ACCOUNT_OWNERSHIP_SKIPPED` log). Only a
   *present-but-unowned* or *present-but-blank* value is a 401. An attacker who can move the identifier
   to a location the filter isn't configured for bypasses it.
3. **Reading a `BODY_FIELD` consumes the servlet input stream**, so the filter rebuilds the request via
   `ServerRequest.from(request).body(rawBody)` — see §17 for the coupled `cacheReqBody` requirement.

### Secrets
- Deploy-time token substitution: 12 `@@placeholder@@` markers (`@@jwtpaymentsGatewayPassword@@`,
  `@@ssoPaymentsGatewayPassword@@`, `@@igOneCdeProxyPassword@@`, …) replaced by the pipeline.
- ⚠️ **`ig.sso.password` in `resource/src/main/resources/properties/common/application.yml` (~line 91) is a
  literal committed credential**, not a placeholder, for the `svc_tomcat-sso` account.
  `prod/application-{LIVE,DEMO}.yml` override it with `@@ssoPaymentsGatewayPassword@@`, so **only DEV/TEST/UAT
  use the committed value** — but it is real, in git history, and the placeholder mechanism it should use
  already exists two files away. Also `openBanking.accountIds` and `newFundsTransfer.clientIds` embed
  real production account/client identifiers in `common/application.yml`.

### Observability
- **Logging** — Logback via `classpath:payments-gateway-logback.xml`, `wt-common-log` 1.54.0. Custom
  converters `DeploymentEnvironmentConverter`, `ServiceModeConverter` inject env + light/dark state into
  every line.
- **Tracing** — OpenTelemetry 1.62.0. `TracingSupportFilter` lifts `traceId`/`spanId` onto request
  attributes (consumed by the Tomcat access-log pattern) and echoes `X-REQUEST-ID` back to the caller.
- **Metrics** — `metrics-goldensignal` 2.0.8 → Prometheus, latency buckets
  `10,20,50,100,200,400,800,1200,2000,10000` ms, `/monitor/*` and `/actuator/*` excluded, tags include
  `SERVICE_MODE` (light/dark) and `DEPLOYMENT_SITE`.
- **Health** — `/monitor/version` (`VersionController` + `VersionMonitorConfiguration`), Actuator,
  `/actuator/prometheus`.
- **Endpoint hiding** — `mantis.conditional-endpoints-hiding` + `web/filter/ConditionalEndpointHidingFilter`
  + `ExternalRequestsCondition` (keyed on presence of the `True-Client-IP` header) hide `/actuator*` from
  externally-originating requests.

---

## 14. Errors / Failure / Resilience

### Exception hierarchy (`domain/.../exception/`)
`AccountOwnershipException` → 401 · `InvalidInputException` → 400 · `ExternalServiceException` → 502 ·
`ExternalServiceBadResponseException` → 502 · `ClientDTONotFoundException` · `InvalidEnvironmentException`
Translation happens in `web/controllers/ExceptionHandlerConfiguration.java` (`@ControllerAdvice`).

**Two important limits on that handler:**
1. **It only covers the gateway's own 15 controllers.** `RouterFunction` filters return
   `ServerResponse.status(...)` directly (`UNAUTHORIZED`, `FORBIDDEN`, `BAD_REQUEST`,
   `INTERNAL_SERVER_ERROR`) with **no body** and never reach `@ControllerAdvice`. So the same logical
   failure has two different response shapes depending on whether it happened on a proxied route or an
   owned API.
2. **`@ExceptionHandler(Exception.class)` puts `exception.getMessage()` into the response body.**
   For a Feign `FeignException` or a `RestClientException` that message contains the **downstream URL and
   response fragment** — internal-topology disclosure to an external caller.

### Failure modes, honestly assessed
| Failure | Behaviour |
|---|---|
| SSO unreachable | `CstAuthorizationFilter` catches → `null` → 401 (correct). `CSTAuthenticationFilter` does **not** catch, and dereferences a possibly-null DTO → **NPE → 500** (§20.1). |
| Downstream 5xx on a proxied route | Passed through by the proxy exchange. |
| Downstream slow | Held for the Feign read timeout; **no circuit breaker on 16 of 18 adapters**, no bulkhead, so slow downstreams consume Tomcat threads. |
| Service-JWT mint fails | `XstInjectionFilter` → 500, request rejected. Fail-closed. ✅ |
| Nomad/cloud backend fails | Silently retried against the legacy backend — **non-idempotent** (§9). |
| Partial fan-out failure | v2 verification service degrades gracefully with `meta.sources`; v1 returns `null` per source and logs. |
| Body read fails on ownership check | 400 `BAD_REQUEST`, request rejected. Fail-closed. ✅ |

---

## 15. Configuration / Infrastructure

### Three-tier + two-axis property layering
```
runtime.properties                     base
${environment}.environment.properties  DEV | TEST | UAT | LIVE | DEMO
${site}.site.properties                PROD1 | PROD2 | DEV | TEST | UAT
{CDE,NONCDE}.payments-gateway-config.properties   PCI zone
common/application.yml                 682 lines — routes' target URLs, filter
                                       inclusion/exclusion lists, ALL feature-flag
                                       allowlists (per IG company, per account id)
application-${environment}.yml         per-env overrides (LIVE 76 lines, DEMO 84)
application-${site}.yml                per-site overrides (PROD1/PROD2, 14 lines each)
```
Activated by `spring.profiles.include: [${environment}, ${site}]` (`common/application.yml:16-19`) —
i.e. **profiles are derived from `-Denvironment=` / `-Dsite=` JVM args**, and `resource/src/main/assembly`
zips `common/` + one env folder into each deployable.

**The consequential fact about this layering:** ~40 feature flags are expressed as **comma-separated
allowlists of IG company codes, account ids and client ids inside `common/application.yml`**, e.g.
`property.instantBankTransfer.enabledIgCompanies: 'iggb'` with
`accountIds: 'TZIL6,TZIL7,TZIL8'` and even `enabledClientIdEndingsForSD: '0,1,2,...,9'` (a percentage-rollout
mechanism implemented as last-digit matching). **Rollout is a property-file edit and redeploy**, with JMX
`@ManagedOperation`s as the no-redeploy escape hatch (41 `*FeatureMBean` / `*FeatureFlag` class pairs in
`featureflag/` + `mbean/`). Note `spring.jmx.default-domain: com.iggroup.wt`.

### Infrastructure
- **Deployment target: on-prem Tomcat**, not a container. `server.tomcat.basedir: /opt/projects/springboot/instance_1/`,
  access logs to `logs/` with 90-day retention. WAR + `PaymentsGatewayRunner` (embedded) both supported.
- **CI/CD: GitLab**, `.gitlab-ci.yml` (29.5 KB) + `.ci/payments-gateway-cd.yml`, with **29 stages**.
  Per-environment promotion is `create-crf → validate-crf → deploy-app → post-deployment-test → close-crf`
  for TEST → UAT → DEMO → LIVE — i.e. **ServiceNow change-request creation and closure are pipeline stages**.
  Shared templates: `ci-pret.yml`, `maven-security-gates.yml`, `maven-jacoco-coverage.yml`,
  `maven-static-analysis.yml`, `maven-gatling-on-prem.yml`, `on-prem-proxy-config.yml`.
  `workflow.rules: [{when: always}]` deliberately overrides the template to run pipelines on all branches.
- **Supply-chain scanning:** `.snyk`, `renovate.json5`, `ossindex-maven-enforcer-rules` (build fails on
  known-vulnerable deps), Snyk + static analysis as pipeline gates.
- **Performance testing:** Gatling, on-prem (`performance-tests/`, `performance-testing.md`).
- **`app-maturity.md`** tracks a `QU247-2025` Definition-of-Done scorecard (10 criteria, mostly
  "not assessed", CRF automation "blocked externally") — machine-updated between `<!-- ... -->` markers.

---

## 16. Testing Discoveries

269 test files (35% of the codebase). Three distinct tiers:

**1. Unit** — JUnit 5 + Mockito 5.2 + AssertJ, `make-it-easy` 4.0 test-data builders (`maker/` packages),
`junit-pioneer` (env-var/system-property manipulation), `datafaker` for random test data.

**2. Acceptance (`acceptance/`)** — Cucumber 7.18 + Testcontainers + WireMock, `@SpringBootTest(DEFINED_PORT)`
booting the **real `PaymentsGatewayApplication`** against the **real `common/application.yml`** loaded via a
custom `YamlPropertySourceFactory`, with `TestContainerInitializer` and a `TestDataStorage` "vault" cleared
per scenario (`AcceptanceScenarioSetup.java`). WireMock stubs live as JSON in
`acceptance/src/test/resources/wiremock/{mappings,__files}` and response templates in
`templates/<service>/<scenario>/`. **74 feature files**, dominated by `*-bola-*.feature`.

**3. Post-deployment (`post-deployment-tests/`)** — smoke tests per environment *and per light/dark side*
(`application-live-dark.properties` etc.), wired as pipeline stages.

### **UNUSUAL TESTING TECHNIQUES**
- **Consumer-driven contract tests without a broker** (`integration/src/test/java/.../contract/`, 3 ITs).
  `AccountValuationAdapterContractIT` boots the app with WireMock, exercises the adapter, then replays the
  captured `LoggedRequest` through Atlassian **`swagger-request-validator`** against the provider's real
  OpenAPI spec **downloaded from UAT and committed** to `src/test/resources/contracts/*-spec.json`. It
  proves *"we send what the provider's published spec says"* with no Pact broker.
  It also documents a genuine spec/wire mismatch and **downgrades one validation rule to `INFO`**
  (`validation.request.parameter.enum.invalid`) because the provider's spec lists logical enum names
  (`AVAILABLE_TO_WITHDRAW`) while the wire uses short codes (`b2`) — an honest, annotated concession.
- **`mockStatic`** in 5 test classes (`DynamicBankDepositsHandlerTest`, `CstAuthorizationFilterTest`,
  `AccountOwnershipFilterTest`, `TracingSupportFilterTest`, `DynamicPspMaintenanceHandlerTest`) — needed
  because production code calls `HandlerFunctions.https(...)` and `DomainUtilsRegistry.getPortAdapterRegistry()`
  statically. **The static locator of §5 is directly responsible for this.**
- **A per-test property override that reveals a config bug:** `AccountValuationAdapterContractIT` sets
  `spring.cloud.gateway.server.webflux.mvc.enabled=false` — the **wrong namespace** (`webflux`, where the
  app uses `server.webmvc`). It's inert; a leftover from the Boot 2 → 3 migration.
- **Coverage** is a dedicated aggregating Maven module (`coverage/`) with a `docs/coverage-plan.md`.

---

## 17. Custom Libraries / Implicit Behaviour

### Internal ("mantis" / "wt") libraries and what each silently contributes
| Library | Version | Behaviour it induces |
|---|---|---|
| `jwt-application-token-generation-spring` | 1.0.42 | `JwtApplicationTokenProvider` — **caches and auto-refreshes the service JWT**. The app only supplies a `JwtApplicationTokenGenerator` (`web/service/JwtService`, 18 lines); all caching/expiry/refresh logic is in the library and invisible here. |
| `mantis.conditional-endpoints-hiding` | 1.0.55 | Endpoint hiding driven by `RequestCondition` beans. |
| `metrics-goldensignal` | 2.0.8 | Golden-signal Prometheus metrics + `ResetOnSwitchGoldenSignalReporterProvider` (metric reset on light/dark flip). |
| `wt-common-log` | 1.54.0 | Logback appenders/pattern conventions. |
| `user-agent-spring` | 1.0.120 | `@ManagedResource` user-agent parsing + `ThreadLocal` context (`UserAgentParserConfig`, `UserAgentInitializerInterceptor`). |
| `ig-feign-spring-boot-starter` | 1.0.39 | Feign defaults/decoders (`FeignClientDecorator`). |
| `ig-sso-spring-boot` / `wt-sso-securedhttpclient` / `wt-singlesignon` | 1.0.10 / 230413 / 241029 | SSO DTOs + `ig.sso.filter` auto-registered authentication filter — **explicitly disabled** (`ig.sso.filter.enabled: false`) because the app hand-rolls CST instead. |
| `ig-web-spring-boot-starter`, `ig-swagger-spring-boot-starter` | 1.0.6 / 1.0.8 | Web + springdoc conventions. |
| `com.iggroup.filters.clusterdetails` | — | `IGClusterDetails` — reads light/dark, site, instance number from the host. |
| `ig-acceptance-test-step-defs` | 260226 | `TestContainerInitializer`, `TestDataStorage`, `YamlPropertySourceFactory` for the acceptance suite. |

### **IMPLICIT BEHAVIOUR — the trap you must know about**

**The `cacheReqBody` ↔ `BODY_FIELD AccountOwnershipFilter` coupling.** Documented in an unusually good
in-repo comment at `common/application.yml:181-189` and worth restating, because it is invisible from code:

> A `BODY_FIELD` `AccountOwnershipFilter` fully drains the raw servlet `InputStream` to read the
> ownership-checked field. The `ProxyExchangeHandlerFunction` that forwards to the backend
> (`RestClientProxyExchange`) reads the body straight off that **same raw `InputStream`** — not off the
> rebuilt `ServerRequest`. So without a `CachedBodyHttpServletRequest` wrapper, **the backend receives no
> body at all** (`HttpMessageNotReadableException: Required request body is missing`).

⇒ **Every route with a `BODY_FIELD` ownership check must also be listed under
`servlet-filters.cacheReqBody.inclusions`.** This is enforced by nothing but the comment. It has already
caused at least two production fixes (`b40010da CAMP-1264 Fix request body dropped on BODY_FIELD
AccountOwnershipFilter routes`, `75ca5d8e CAMP-1357 Add /payments/demo/deposit to cacheReqBody inclusions`).
It is the highest-probability future regression in this repo.

**Other implicit behaviours:**
- `allow-bean-definition-overriding: true` — silent last-one-wins bean resolution (§3).
- `CustomBeanExclusionProcessor` — forces library bean `exporterCP` lazy (§3).
- `DomainUtilsRegistry` static locator — an invisible runtime edge from `domain` back into `integration` (§5).
- `spring.web.resources.add-mappings: false` — no static-resource handler, so an unmatched path 404s
  rather than falling through to a resource lookup.
- **`HttpClientFactory.createRequestConfig` calls `setRedirectsEnabled(false)` and then
  `setRedirectsEnabled(true)` on the same builder** (`sso/HttpClientFactory.java:56-58`). The second call
  wins, so **redirects are enabled** on the SSO client despite the apparent intent — and `CustomRedirectStrategy`
  is what then governs them. Same method also contains a fully-built-but-unused local `keepAliveStrategy`
  lambda (lines 37-40), superseded by `CustomKeepAliveStrategy`.

---

## 18. Legacy / Historical Discoveries

The repo is a legible archaeology of four migrations, three complete and one abandoned:

1. **Zuul → Spring Cloud Gateway (complete in behaviour, incomplete in code).**
   `integration/.../web/zuul/filter/` still exists with `ZuulAction`, `ZuulPropertyConfiguration`,
   `FilterLogic`, `RequestUtils`, `CookieUtil`, `AuthorizationService`, `MFAWithdrawalAuthorizationService`.
   These are **live and load-bearing** — `BlockExternalRequestsFilter` and `XSTAuthenticationFilter` both
   depend on `FilterLogic` — but the package name and a commented-out `zuulFilterUtils.setResponseStatusCodeAndStopRequest(SC_FORBIDDEN)`
   in `BlockExternalRequestsFilter.java:32` mark the seam.

2. **Spring Boot 2 → 3 (complete, with fossils).** `jakarta.*` throughout, HttpClient 5, Tomcat 10.1.55.
   The fossils: `TASTYFX-1413` removed ~50 declarative YAML routes that had **duplicated the
   `RouterFunction` beans and been silently inert on Boot 3 because the YAML used the wrong
   `spring.cloud.gateway.server.webflux` namespace** — they survive as an 80-line commented table at
   `RouterConfig.java:26-79`. Also still present: `org.apache.commons.httpclient.HttpStatus`
   (Commons HttpClient **3.x**) imported in `XstInjectionFilter`, `slf4j.version` pinned to **1.7.2**
   in `<properties>` while logback is 1.5.36, `restassured` declared twice (2.8.0 and 5.3.0),
   `wiremock` twice (2.24.1 and 3.3.1), and `tomcat7-maven-plugin` for local runs of a Tomcat 10 app.

3. **Hystrix → Resilience4j (config not cleaned up).** `ig.hystrix.incident` still configures a
   rolling window and incident thresholds for a library that is no longer on the classpath.

4. **CST caching removed (abandoned).** The Ehcache `CachedClientTokenServiceRemoteClient` config and the
   `ehcache` dependency remain, but the client is commented out — so the cache is dead and **SSO is now
   called on every request** (§10, §20.4).

5. **The readme is materially stale.** `readme.md:19-23` claims "Spring Boot 2.x" and "Spring Security for
   authentication and authorisation"; the truth is Boot 3.5.16 and hand-rolled servlet filters with no
   Spring Security at all. `pymnts-gw-plan.md` (a working design note) is the accurate architecture
   description, and it explicitly documents the CST-vs-XST inclusion-list gotcha.

6. **Active revert churn on `main`.** `git log` shows `Revert "Merge branch 'revert-c9b14d62'"`,
   `Revert "Merge branch 'AP-12071'"`, `Revert "...TUKN-23275-Hide-transfer-fund..."` — i.e. **feature
   flags are not always sufficient and code-level reverts are used in anger.** Worth knowing before
   assuming `main` is linear.

---

## 19. Patterns & Conventions

### Design patterns detected
| Pattern | Evidence | Purpose |
|---|---|---|
| **Ports & Adapters** | `domain/port/*Port` ↔ `integration/web/adapters/*Adapter` (16+4 ports, 18 adapters) | keep domain HTTP-free |
| **Strategy + explicit `@Order` chain** | `PageUrlService` (7 impls, `@Order(10..60)`), `PaymentsServiceFactory.findFirst()` | client-type-specific navigation |
| **Template Method** | `PaymentsFunctionality.create()` final, `getUrls()`/`additionalConditions()` abstract | uniform functionality construction |
| **Registry / polymorphic collection injection** | `Collection<PaymentsFunctionality>`, `List<RequestCondition>`, `List<PageUrlService>` | add a feature by adding a `@Service` |
| **Decorator** | `CachedBodyHttpServletRequest extends HttpServletRequestWrapper`, `IGTelemetryClusterDetailsProvider` | re-readable body; state-name translation |
| **Chain of Responsibility** | ordered servlet filters + per-route `HandlerFilterFunction`s | layered auth |
| **Higher-order filter (feature-flag gate)** | `RouterConfig.gated(BooleanSupplier, filter)` at `RouterConfig.java:137-139` | one-line kill switch on any route filter |
| **Service Locator (anti-pattern)** | `DomainUtilsRegistry` | escape DI in a servlet filter — **do not copy** |
| **Enum-as-predicate** | `SimpleClientAndAccountPredicates`, `CompositeClientAndAccountPredicates : BiPredicate<...>` | named, composable eligibility rules |
| **Kill-switch pair** | 41 `*FeatureFlag` (`volatile` state) + `*FeatureMBean` (`@ManagedOperation`) pairs | runtime toggling without redeploy |

### Coding conventions
- **Indentation is 3 spaces** in older/`domain` code, 4 in newer `web/service` code. Match the file.
- Naming: `*Port` (domain interface) · `*Adapter` (implementation) · `*Api` (Feign) · `*Filter` (servlet)
  vs `*Filter` in `prefilters/` (route) · `*DTO`/`*Dto` (both spellings occur) · `*FeatureFlag` (state)
  vs `*FeatureMBean` (JMX) · `*ServiceImpl` for interface-backed services.
- **Structured logging is the house style:** `log.info("method=getAccountId accountId={}", accountId)` —
  `method=` prefix plus `key=value` pairs. Security events use SCREAMING_SNAKE markers:
  `ACCOUNT_OWNERSHIP_BLOCKED`, `ACCOUNT_OWNERSHIP_SKIPPED`, `ACCOUNT_OWNERSHIP_BODY_READ_FAILED`.
  ⚠️ Log level discipline is weak — `log.info` carries per-request detail including `accountId`,
  `clientId` and (in `IgOneBalanceSummaryApiInterceptor`) a **token response**.
- Jira keys prefix every commit (`CAMP-*` security, `AP-*` features, `PYMG-*`/`TUKN-*` legacy).
- **Comments explain *why*, and they are unusually good.** `AccountOwnershipFilter`,
  `ClientOwnershipChecker`, `AccountOwnershipFeatureFlag`, the `RouterConfig` legacy-routes table and the
  `cacheReqBody` note in `application.yml` all document rationale and hazards, not mechanics. Trust them.
- Route naming in `RouterConfig` abbreviates the backend: `cp*` = card-payments, `p*` = payments,
  `walletPayments*`, `paypal*`; `*OwnershipChecked` suffix marks a BOLA-fixed route;
  `*SmartRoute` marks a `-internal` prefix + `rewritePath` variant.

### Architectural conventions (rules to follow when changing this repo)
1. **Adding a proxied route** = new `@Bean RouterFunction<ServerResponse>` in `RouterConfig`, shape
   `route().<METHOD>(path, https(create(targetUrl))).before(stripPrefix(1)).filter(...).build()`.
2. **A more specific route must carry `@Order(Ordered.HIGHEST_PRECEDENCE)`** to beat a wildcard sibling.
   24 route beans already do. Forget it and a `/**` route swallows your path.
3. **Inbound auth is decided in `common/application.yml`, not in code** — `cstAuthentication.inclusions: /*`
   means CST is on by default; to use XST instead you must *add* to `xstAuthentication.inclusions` **and**
   *exclude* from `cstAuthentication`. (`pymnts-gw-plan.md` §2 spells this out.)
4. **Outbound auth is a filter** — add `xstInjectionFilter` (or `serviceTokenInjectionFilter`).
5. **Any `BODY_FIELD` ownership check requires a `cacheReqBody.inclusions` entry.** (§17)
6. **Every new ownership check needs a JMX kill switch and a Cucumber `*-bola-*.feature`.**
7. **Never reuse an `AccountOwnershipFilter` bean for a different `(location, fieldName)` pair** — define
   a new bean in `AccountOwnershipFilterConfig` (called out explicitly in the repo-local skill).

---

## 20. Important Discoveries (Ranked)

**1. Two parallel, non-equivalent CST authentication implementations — and only one is null-safe.**
`web/filter/CSTAuthenticationFilter` (servlet, path-list driven, legacy) and
`prefilters/CstAuthorizationFilter` (route-scoped, explicitly wired, current) contain near-identical
`isValidCST` / `isValidClientToken` / `getAccountId` / `populateAccountWithClientDTO` logic. They have
diverged:

| | `CSTAuthenticationFilter` | `CstAuthorizationFilter` |
|---|---|---|
| SSO call wrapped in try/catch | ❌ no | ✅ yes → 401 |
| Null `verificationResponseDTO` handled | ❌ `verificationResponseDTO.isVerified()` on line 71 after `isValidCST` | ✅ explicit null check → 401 |
| Missing token short-circuit | ❌ calls SSO with a null token | ✅ 401 before calling SSO |
| Gets ports via | ❌ static `DomainUtilsRegistry` | ✅ constructor-injected `ClientDetailsPort` |
| Injects `IG-CLIENT-ID`/`COMPANY_ID` headers | ❌ | ✅ |

`SsoClientTokenCaller.verifyAndExtendTwoFactorAuth` returns `restTemplate.exchange(...).getBody()`, which
**can be null**, and throws `RestClientException` on non-2xx. On the legacy path both produce a **500
instead of a 401** — and a 500 on an auth failure is both an operational false alarm and an information
leak. *Why it matters:* the migration to route-scoped CST is incomplete, so the weaker filter still guards
every path in `cstAuthentication.inclusions: /*` that hasn't been carved out to a `cstAuthorizationFilter`
route. Consolidating on one implementation is the highest-value refactor in the repo.

**2. An active, well-engineered BOLA remediation programme with 61 known-vulnerable endpoints outstanding.**
30 audit docs, a rollup table, a shared declarative `AccountOwnershipFilter`, an `AccountOwnershipValidator`
for owned APIs, 12 JMX kill switches, ~40 dedicated Cucumber features, and two repo-local Claude skills
encoding the workflow. *Why it matters:* this is the dominant workstream on `main` (CAMP-1264/1281/1285/1291/1357);
`docs/bola/vulnerable-apis-exposed-cst-authenticated-summary.md` is the correct entry point for any
security question — but the doc itself warns it has been stale and is "**not** ground truth". Also note
the rollup separates these 61 (CST=Y, still BOLA) from a *worse* class: routes exposed with **no gateway
auth at all** (e.g. `GET /bankwithdrawal/api/external/**`, `POST /bankwithdrawal/api/withdrawal/search`).

**3. `RouterConfig.java` is a 1,865-line, 130-bean single class where correctness depends on `@Order`.**
Route precedence between a specific path and a `/**` sibling is decided by `@Order(HIGHEST_PRECEDENCE)`
(used 24×) with no test asserting the resulting order. *Why it matters:* adding a route can silently
shadow or be shadowed by another, and the failure mode is "auth filter didn't run", not "404". This file
is also the only complete inventory of the payments estate's external surface — treat it as an
architecture artifact, not just config.

**4. The CST verification cache is dead, so SSO is on the critical path of 100% of client requests.**
`payments-gateway-ehcache.xml` still configures a 300s TTL cache for
`CachedClientTokenServiceRemoteClient`; that class is only referenced by a **commented-out field** and an
unused import in `CSTAuthenticationFilter`. Every authenticated request now makes a synchronous
`PUT /clienttokentwofactorauth`, and account-scoped routes add a Client Maintenance `getClientDTO`.
The SSO HttpClient runs on **undefined properties** (`sso.remoteexecutor.httpclient.*` appear nowhere in
`resource/`), so the code defaults apply: 100 connections, 1s connect, 1s pool-acquire, 6.5s socket read,
30s response timeout. *Why it matters:* SSO latency is gateway latency, and a 1s pool-acquire timeout at
100 connections is the first thing that will break under a traffic spike.

**5. `IgOneBalanceSummaryApiInterceptor` re-mints an OAuth2 token on every request and logs the response.**
`web/external/api/configs/IgOneBalanceSummaryApiInterceptor.java:31-37`: builds a
`grant_type=client_credentials` form, calls Microsoft login **inline in the interceptor** (no caching, no
expiry check), then `log.info("Azure token response: {}", azureTokenResponse)` — writing an
`IgOneAzureToken` (which holds `access_token`) to the application log. *Why it matters:* two distinct
defects in 8 lines — **a bearer token in plaintext logs**, and a synchronous extra round-trip to an
external IdP on every IgOne balance lookup. Contrast with `JwtApplicationTokenProvider`, which the app
already relies on for exactly this caching concern.

**6. The `cacheReqBody` ↔ `BODY_FIELD` ownership-check coupling is enforced only by a YAML comment.**
Because `RestClientProxyExchange` reads the body off the raw `InputStream` rather than the rebuilt
`ServerRequest`, any route whose ownership filter reads the body **silently forwards an empty body** unless
that route is also in `servlet-filters.cacheReqBody.inclusions`. *Why it matters:* it has already caused
two production fixes (`b40010da`, `75ca5d8e`), the coupling is across a Java-file/YAML boundary, and no
test or startup assertion catches it. A `@PostConstruct` cross-check of the two lists would eliminate an
entire class of incident.

**7. `ForkJoinPool.commonPool()` is used for blocking HTTP fan-out in three places.**
`VerificationRequestsServiceImpl` (4 futures, **`future.get()` with no timeout**), `CardPaymentAdapter`
and `PaypalWithdrawalAdapter`. The commonPool is `availableProcessors - 1` — 3 threads on a 4-vCPU host,
shared process-wide, with no `ManagedBlocker`. *Why it matters:* the fix already exists in the same
package — `ExternalVerificationRequestsServiceImpl` uses a dedicated 10-thread daemon pool, a 30s
per-source timeout, and returns partial results with a `meta.sources` status map. That is the pattern; the
other three should be migrated to it. Longer term, this app's blocking fan-out profile is close to an ideal
virtual-threads candidate, which needs Java 17 → 21.

**8. Resilience is configured but almost entirely unwired.**
Resilience4j circuit-breaker defaults exist (40-request window, 30% failure rate, 60s open) but
`@CircuitBreaker` appears on **2 of 18 adapters**; `spring.cloud.openfeign.circuitbreaker.enabled: false`;
`resilience4j.retry.instances.default.maxAttempts: 1` (retry off); `@Retryable` on `ClientMaintenanceApi`
is commented out; and the `ig.hystrix.incident` block configures a library that has been removed.
*Why it matters:* with no broker, no retry and no bulkhead, a single slow downstream consumes Tomcat
threads and degrades the whole gateway. Client Maintenance in particular is called on nearly every
account-scoped request and has neither breaker nor retry.

**9. Non-idempotent fallback in the cloud-migration routers.**
`DynamicBankDepositsHandler` and `DynamicPspMaintenanceHandler` implement per-account canary routing
(legacy vs "Nomad" cloud, `IG-ACCOUNT-ID`-keyed, with a global flag override) and on **any** exception —
including a failure *after* the Nomad backend received the request — fall back to replaying it against the
legacy backend. *Why it matters:* these routes include `POST /bankdeposits/api/quick-deposit/initiate`.
With no idempotency key anywhere in the system, that is a potential duplicate deposit initiation. The
fallback should be restricted to connection-establishment failures on idempotent methods.

**10. A real service-account credential is committed for DEV/TEST/UAT.**
`resource/src/main/resources/properties/common/application.yml` (~line 91) sets `ig.sso.password` to a
literal value for `svc_tomcat-sso`. `prod/application-LIVE.yml` and `application-DEMO.yml` correctly use
`@@ssoPaymentsGatewayPassword@@`, and 12 such placeholders exist — **so the mechanism to fix this is
already in the repo and simply wasn't used for the shared default.** Same file embeds real production
account/client ids (`property.openBanking.accountIds`, `property.newFundsTransfer.clientIds`).
*Why it matters:* it is in git history, so rotation — not just deletion — is required.

**11. `@ExceptionHandler(Exception.class)` returns the raw exception message to the caller.**
`ExceptionHandlerConfiguration.handleUnknownErrors` puts `exception.getMessage()` in the response body;
for a `FeignException`/`RestClientException` that message carries the internal downstream URL and response
fragment. Compounding this, the `@ControllerAdvice` covers **only** the 15 owned controllers — proxied
routes return bare `ServerResponse.status(...)` with no body, so the same failure has two shapes.

**12. Feign timeouts are configured twice, in two competing namespaces.**
`spring.cloud.openfeign.client.config.default` says `10000/30000`; the deprecated
`feign.client.config.default` says `3000/5000`. Both are present in `common/application.yml`. *Why it
matters:* the effective read timeout for every adapter is ambiguous from reading the config — and it is
the difference between a 5s and a 30s Tomcat-thread hold on the unbounded `future.get()` of finding #7.

---

## 21. Unknowns

1. **Which Feign timeout tree actually wins** (`spring.cloud.openfeign.client.config` vs legacy
   `feign.client.config`). Resolvable by logging the effective `Request.Options` per client at startup, or
   an `ApplicationContextRunner` test. Blocks a confident answer on worst-case request latency.
2. **Whether `ig.sso.password`'s committed value is still live in DEV/TEST/UAT.** Needs a credential-owner
   check; determines whether this is "clean up" or "rotate now".
3. **What library defines the `exporterCP` bean** that `CustomBeanExclusionProcessor` forces lazy, and
   whether the workaround is still needed after the Boot 3 upgrade. `mvn dependency:tree` + a bean-definition
   dump would settle it.
4. **Real light/dark switch behaviour** — `IGClusterDetails` reads it from the host, so the switch semantics
   (and whether in-flight requests drain) live in deployment tooling outside this repo.
5. **Actual concurrency ceiling.** Tomcat `maxThreads` is not set in `application.yml` (so Boot's 200
   default applies unless the on-prem Tomcat `server.xml` overrides it), and no downstream connection-pool
   sizes are configured except SSO's. The Gatling suite in `performance-tests/` presumably answers this —
   its results were not available here.
6. **Current true BOLA status.** The rollup doc self-describes as previously stale, and `git log` shows
   fixes landing continuously. Any count must be re-derived from the per-service
   `docs/bola/*-gateway-exposure-findings.md` tables against current `RouterConfig`.
7. **`payments-api-gateway`** is a separate sibling module in the same repo group. How responsibility is
   split between it and `payments-gateway` is not determinable from this module alone.
8. **Which of the 130 routes are actually receiving traffic.** With 24 `HIGHEST_PRECEDENCE` overrides and a
   documented case of a route whose pattern "requires a doubled `/payments-gateway` segment that no real
   caller sends" (`bank-maintenance-gateway-exposure-findings.md`), some routes are almost certainly dead.
   Only production access logs can tell.

---

## Investigation Checklist
- [x] Module structure explored
- [x] Maven configuration analyzed (BOMs, parent, exclusions, plugins)
- [x] Spring version and tech determined (Boot 3.5.16 / Cloud 2025.0.3 / Java 17 / Gateway MVC)
- [x] Entry points identified (130 route beans, 15 controllers, 34 endpoints)
- [x] Flows traced (proxy path, aggregation path, concurrent fan-out path)
- [x] State machines searched — **none exist** (30 enums audited)
- [x] Consistency mechanisms understood (per-request memoisation only; no transactions)
- [x] Persistence patterns mapped — **no datastore**; Ehcache config is dead
- [x] External integrations documented (33 Feign clients, ~25 proxied backends, no brokers)
- [x] Concurrency model understood (thread-per-request + 3 commonPool sites + 1 dedicated pool)
- [x] Security/observability reviewed (4 auth mechanisms, BOLA programme, OTel + golden signals)
- [x] Error handling analyzed (`@ControllerAdvice` scope limit, resilience gaps)
- [x] Configuration understood (5-axis property layering, ~40 flags, 29-stage pipeline)
- [x] Tests analyzed (3 tiers, contract-testing technique, `mockStatic` root cause)
- [x] Custom libraries identified (11 internal libs and what each induces)
- [x] Historical patterns noted (Zuul, Boot 2→3, Hystrix, CST cache, stale readme, revert churn)
- [x] Conventions documented (7 architectural rules for changing this repo)

---

## Files Referenced

**Routing & entry points**
- `integration/src/main/java/com/iggroup/wt/payments/gateway/config/RouterConfig.java` (1,865 lines; `gated()` at :137, legacy route table at :26-79)
- `integration/src/main/java/com/iggroup/wt/payments/gateway/PaymentsGatewayApplication.java`
- `jar/src/main/java/PaymentsGatewayRunner.java`
- `integration/src/main/java/com/iggroup/wt/payments/gateway/config/DynamicBankDepositsHandler.java`
- `integration/src/main/java/com/iggroup/wt/payments/gateway/config/DynamicPspMaintenanceHandler.java`
- `integration/src/main/java/com/iggroup/wt/payments/gateway/web/controllers/` (15 controllers)

**Auth & authorisation**
- `integration/src/main/java/com/iggroup/wt/payments/gateway/web/configuration/FilterConfiguration.java`
- `integration/src/main/java/com/iggroup/wt/payments/gateway/web/filter/CSTAuthenticationFilter.java`
- `integration/src/main/java/com/iggroup/wt/payments/gateway/prefilters/CstAuthorizationFilter.java`
- `integration/src/main/java/com/iggroup/wt/payments/gateway/prefilters/AccountOwnershipFilter.java`
- `integration/src/main/java/com/iggroup/wt/payments/gateway/ownership/{ClientOwnershipChecker,AccountOwnershipValidator}.java`
- `integration/src/main/java/com/iggroup/wt/payments/gateway/config/AccountOwnershipFilterConfig.java`
- `integration/src/main/java/com/iggroup/wt/payments/gateway/mbean/AccountOwnershipFeatureFlag.java`
- `integration/src/main/java/com/iggroup/wt/payments/gateway/featureflag/AccountOwnershipFeatureMBean.java`
- `integration/src/main/java/com/iggroup/wt/payments/gateway/prefilters/{XstInjectionFilter,BlockExternalRequestsFilter}.java`
- `integration/src/main/java/com/iggroup/wt/payments/gateway/web/zuul/filter/FilterLogic.java`
- `integration/src/main/java/com/iggroup/wt/payments/gateway/web/filter/{AbstractFilter,CacheRequestBodyFilter}.java`
- `integration/src/main/java/com/iggroup/wt/payments/gateway/model/CachedBodyHttpServletRequest.java`

**Domain**
- `domain/src/main/java/com/iggroup/wt/payments/gateway/port/` (16 ports)
- `domain/src/main/java/com/iggroup/wt/payments/gateway/repository/{DomainUtilsRegistry,PortAdapterRegistry}.java`
- `domain/src/main/java/com/iggroup/wt/payments/gateway/service/functionality/` (24 classes)
- `domain/src/main/java/com/iggroup/wt/payments/gateway/domain/VerificationStatus.java`

**Integration & clients**
- `integration/src/main/java/com/iggroup/wt/payments/gateway/web/adapters/` (18 adapters)
- `integration/src/main/java/com/iggroup/wt/payments/gateway/web/external/api/` (33 Feign clients)
- `integration/src/main/java/com/iggroup/wt/payments/gateway/web/external/api/configs/IgOneBalanceSummaryApiInterceptor.java`
- `integration/src/main/java/com/iggroup/wt/payments/gateway/sso/{SsoClientTokenCaller,SingleSignOnConfiguration,HttpClientFactory}.java`
- `integration/src/main/java/com/iggroup/wt/payments/gateway/config/{HttpClientParamsConfiguration,CustomKeepAliveStrategy,CustomBeanExclusionProcessor}.java`
- `integration/src/main/java/com/iggroup/wt/payments/gateway/web/service/{VerificationRequestsServiceImpl,ExternalVerificationRequestsServiceImpl,JwtService}.java`
- `integration/src/main/java/com/iggroup/wt/payments/gateway/web/controllers/ExceptionHandlerConfiguration.java`

**Observability**
- `integration/src/main/java/com/iggroup/wt/payments/gateway/config/GoldenSignalsConfiguration.java`
- `integration/src/main/java/com/iggroup/wt/payments/gateway/observability/{TracingSupportFilter,logging/IGTelemetryClusterDetailsProvider}.java`

**Configuration**
- `pom.xml` (root, 43 KB — properties, BOMs, dependencyManagement)
- `resource/src/main/resources/properties/common/application.yml` (682 lines — **the most important config file**; `cacheReqBody` comment at :181-189)
- `resource/src/main/resources/properties/{prod,test,uat,dev,it}/`
- `resource/src/main/resources/properties/common/payments-gateway-ehcache.xml` (dead cache config)
- `resource/src/main/assembly/*.xml`
- `.gitlab-ci.yml` (29 stages), `.ci/payments-gateway-cd.yml`, `.snyk`, `renovate.json5`

**Tests**
- `acceptance/src/test/java/com/iggroup/wt/payments/gateway/AcceptanceScenarioSetup.java`
- `acceptance/src/test/resources/features/` (74 feature files)
- `integration/src/test/java/com/iggroup/wt/payments/gateway/contract/AccountValuationAdapterContractIT.java`
- `integration/src/test/resources/contracts/*-spec.json`

**Docs (in-repo)**
- `docs/bola/` (30 findings docs + `vulnerable-apis-exposed-cst-authenticated-summary.md`)
- `pymnts-gw-plan.md` (accurate as-is architecture note), `readme.md` (**stale**), `app-maturity.md`
- `.claude/skills/gateway-bola-{ownership-fix,acceptance-test}/SKILL.md`
