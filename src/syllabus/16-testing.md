# Syllabus — 16 Testing

**Currency anchor: Q3 2026 state of practice (checked 2026-09-03).** The write brief for this file
named JUnit 5.14.x / Mockito 5.x / AssertJ 3.27.x / Testcontainers 1.21.x / Spring Boot 3.5.x. The
research phase found that **three of those five lines are a generation behind GA**, so this syllabus
targets the current releases and covers the named ones as the previous generation, because that is
what most codebases are actually on. Both are stated everywhere it matters:

| Layer | Release this file targets | Previous generation, also covered |
|---|---|---|
| JUnit | **6.1.3** (7 Aug 2026). 6.0.0 GA 30 Sep 2025; 6.0.3 (15 Feb 2026); 6.1.0 (20 May 2026); 6.1.1 (29 Jun 2026). Single unified version across Platform + Jupiter + Vintage; **Java 17 runtime baseline** | **JUnit 5.14.x** — separate Platform 1.x / Jupiter 5.x / Vintage 5.x version streams |
| Mockito | **5.23.0** (12 Mar 2026). Java 11 baseline; **inline mock maker is the default since 5.0** | Mockito 4.11 (subclass mock maker default, `mockito-inline` an opt-in artifact) |
| AssertJ | **3.27.7** (24 Jan 2026) — a security patch release; 3.27.6 (22 Sep 2025) is what Boot 4.0 manages. **4.0.0-M1** exists (10 Mar 2025) but is not GA | 3.24/3.25/3.26 lines |
| Testcontainers for Java | **2.0.5** (20 Apr 2026). 2.0.3 (15 Dec 2025), 2.0.4 (19 Mar 2026). **2.0 is a breaking major**: artifact renames, JUnit 4 removed, no no-arg container constructors | **1.21.4** (16 Dec 2025) — the last 1.x, and the version the brief named |
| Spring Boot | **4.1.1** (20 Aug 2026); 4.1.0 GA 10 Jun 2026; 4.0.0 GA 20 Nov 2025. Java 17 baseline, supported through Java 26 | **3.5.x** — the generation most production code is on |
| Spring Framework | **7.0.x** (7.0 GA Nov 2025; 7.0.9 is the reference this file cites for listener order) | 6.2.x |
| Awaitility | **4.3.0** (the version Boot 4.0 manages) | 4.2.x |
| Hamcrest | **3.0** (managed by Boot 4.0) | 2.2 |
| jqwik | **1.10.1** | 1.9.x |
| PIT (pitest) | current release line; mutator set as documented at pitest.org | — |
| JaCoCo | current release line; on-the-fly ASM instrumentation | — |
| Pact | Pact Specification **V4** (V2/V3 still selectable in pact-jvm) | — |
| Java runtime | **Java 21 LTS** for all code in the bible | — |

**The fourteen deltas that most often produce a stale answer in a 2026 testing interview**, each
marked `[VERSION-TRAP]` at its leaf:

1. **JUnit 6 exists and is GA.** 6.0.0 shipped 30 Sep 2025; 6.1.3 is current. Any answer that says
   "JUnit 5 is the latest" is a 2025 answer. The single most visible change is **one version number
   for Platform, Jupiter and Vintage** — the old `junit-platform` 1.x / `junit-jupiter` 5.x split that
   candidates are routinely asked to explain is gone. `[RESEARCH]`
2. **JUnit 6 raised the runtime baseline to Java 17** and removed `junit-platform-runner` (the JUnit 4
   `@RunWith(JUnitPlatform.class)` bridge) and `junit-platform-jfr` (folded into
   `junit-platform-launcher`). `[RESEARCH]`
3. **`@ParameterizedClass` / `@ClassTemplate` is new**, and it brought two new extension callbacks:
   `BeforeClassTemplateInvocationCallback` and `AfterClassTemplateInvocationCallback`. The canonical
   "list the Jupiter callback order" answer is now **18 steps, not 14**. `[RESEARCH]`
4. **Testcontainers 2.0 renamed every artifact.** `org.testcontainers:junit-jupiter` →
   `org.testcontainers:testcontainers-junit-jupiter`, `postgresql` → `testcontainers-postgresql`, and
   container classes moved to module-specific packages. A BOM version bump alone does not compile.
   `[RESEARCH]`
5. **Testcontainers 2.0 removed the no-arg container constructor.** `new PostgreSQLContainer<>()` no
   longer exists; the image must be explicit. `DockerComposeContainer` → `ComposeContainer`;
   `getContainerIpAddress()` → `getHost()`; JUnit 4 support is gone entirely. `[RESEARCH]`
6. **`@MockBean` and `@SpyBean` are not just deprecated, they are replaced by *Framework* annotations.**
   `@MockitoBean` / `@MockitoSpyBean` live in `org.springframework.test.context.bean.override.mockito`
   — they are Spring Framework 6.2+, not Spring Boot. `@MockBean` was deprecated in Boot 3.4.
7. **Bean overrides now support non-singleton beans.** In Framework 7 / Boot 4, `@MockitoBean`,
   `@MockitoSpyBean` and `@TestBean` can override prototype- and custom-scoped beans; before that they
   were singleton-only. `[RESEARCH]`
8. **`TestRestTemplate` is deprecated in favour of `RestTestClient`**, and it now needs
   `@AutoConfigureRestTestClient` / `@AutoConfigureTestRestTemplate` explicitly rather than arriving
   with `@SpringBootTest`. `[RESEARCH]`
9. **`MockMvcTester` is the AssertJ-native MockMvc surface** and is auto-configured by `@WebMvcTest`
   when AssertJ is on the classpath. The `mvc.perform(get(...)).andExpect(...)` idiom every tutorial
   teaches is now the older of two supported styles.
10. **Spring Boot 4 pauses cached contexts instead of only caching them.** Beans implementing
    `Lifecycle`/`SmartLifecycle` are stopped when a cached context goes idle and restarted on reuse;
    `SmartLifecycle#isPauseable()` opts out, and a `ContextPausedEvent` is published. Any answer that
    says "a cached context stays fully running" is pre-4.0. `[RESEARCH]`
11. **`SpringExtension` now uses a test-method-scoped `ExtensionContext`** rather than a
    class-scoped one; `@SpringExtensionConfig(useTestClassScopedExtensionContext = true)` restores the
    old behaviour. Custom `TestExecutionListener`s and extensions that stashed state in the class-level
    store can break silently. `[RESEARCH]`
12. **`spring-boot-starter-web` was renamed `spring-boot-starter-webmvc`**, and the test starters were
    modularised (`spring-boot-starter-webmvc-test`, `spring-boot-starter-restclient-test`). A Boot 4
    upgrade changes your test dependency block, not just your version. `[RESEARCH]`
13. **Mockito's inline mock maker is the default, and its self-attaching agent is on notice.** Since
    Mockito 5.0 `mock-maker-inline` is the default mock maker — final classes and static methods are
    mockable out of the box, no `mockito-inline` artifact. Mockito self-attaches a Byte Buddy agent,
    which future JDKs will refuse without `-javaagent`; the JDK already warns. `[RESEARCH]`
14. **JUnit's Vintage engine is deprecated in the Boot 4 / Framework 7 world** and `SpringRunner`
    emits deprecation warnings. "We still run some JUnit 4 tests via Vintage" is now a migration
    debt statement, not a neutral one. `[RESEARCH]`

**Scope boundary against the sibling guides.** This file owns **the test as an artifact**: what a
given test proves, what it costs, what makes it deterministic, how the frameworks that run it
actually work, and every way a suite decays. Owned elsewhere:

- The Spring container itself — bean lifecycle, dependency injection styles, scopes, the **proxy
  model and self-invocation**, AOP advice ordering, `@Conditional` and auto-configuration mechanics —
  lives in `07-spring-core.md`. This guide owns the *test-time* container: the `TestContext`
  framework, the context cache, bean overrides, and why a proxy makes `@Transactional` tests lie.
  `[X-REF 07]`
- Persistence context and entity states, dirty checking, `LazyInitializationException`, N+1, fetch
  strategies, transaction **propagation and isolation semantics**, locking and ID generation live in
  `08-spring-data-jpa.md`. That guide currently cross-references Testcontainers and Mockito *to here*
  — this file owns them. This guide owns `@DataJpaTest`, `TestEntityManager`, rollback-per-test, and
  the flush that transactional tests skip. `[X-REF 08]`
- SQL dialects, indexes, query plans, ACID, isolation-level anomalies, MVCC and deadlocks live in
  `09-sql-databases.md`. This guide owns why H2-in-Postgres-mode is a false witness and what a
  database test must assert. `[X-REF 09]`
- The Java memory model, `volatile`, happens-before, CAS, `ThreadPoolExecutor` queueing,
  `CompletableFuture`, `CountDownLatch` and virtual threads live in `05-multithreading-concurrency.md`.
  This guide owns **testing** concurrency: Awaitility, deterministic executors, jcstress, and the
  proof obligations a thread-safety claim carries. `[X-REF 05]`
- Bytecode, classloading, `java.lang.instrument` agents, JIT warmup, GC and the diagnostic toolkit
  live in `06-jvm-internals.md`. This guide owns instrumentation *as used by* Mockito, JaCoCo and
  PIT, and JMH as a measurement tool with a testing boundary. `[X-REF 06]`
- REST resource modelling, verbs, status codes, idempotency, versioning, pagination and
  backward-compatible evolution live in `12-api-design.md`. This guide owns how a contract is
  *verified* — Pact, Spring Cloud Contract, and schema compatibility as a build gate. `[X-REF 12]`
- Images, layers, the Docker daemon, resource limits, and CI runners live in
  `19-docker-kubernetes.md`. This guide owns Docker *as a test dependency*: socket access,
  Docker-in-Docker, rootless, and the CI cost model. `[X-REF 19]`
- Metrics, logs, traces, Micrometer, SLI/SLO and postmortems live in
  `20-observability-operations.md`. This guide owns test-suite observability: flake rate, duration
  distribution, and the build as a monitored system. `[X-REF 20]`
- Kafka/RabbitMQ mechanics, delivery semantics, consumer groups, DLQs and the outbox live in
  `14-messaging-queues.md`. This guide owns `@EmbeddedKafka` vs a Kafka container, and how you assert
  on an asynchronous consumer without sleeping. `[X-REF 14]`
- Cache mechanics, eviction and invalidation live in `15-caching.md`; that guide's § 2.17 explicitly
  parks "how to test a cache" here. This guide owns the four cache assertions and the `Ticker`
  injection that replaces sleeping. `[X-REF 15]`
- AuthN/AuthZ, OAuth flows, JWT and the OWASP list live in `13-web-security.md`. This guide owns
  `spring-security-test` (`@WithMockUser`, `SecurityMockMvcRequestPostProcessors`) and the trap of
  disabling filters in a controller test. `[X-REF 13]`
- Generics erasure, `equals`/`hashCode`, `BigDecimal` and `java.time` live in `03-java-core.md`; the
  `Clock` injection pattern's *type* semantics are theirs. This guide owns injecting it for
  determinism. `[X-REF 03]`
- `HashMap`/`HashSet` iteration order, and why asserting on it is a latent flake, live in
  `02-java-collections.md`. `[X-REF 02]`
- Records, sealed types, pattern matching and `Optional` discipline live in `04-modern-java.md`; the
  bible's code uses them, this guide does not teach them. `[X-REF 04]`
- Git hooks and pre-commit gating live in `17-git-craft.md`. `[X-REF 17]`
- "How would you test this design" as an interview move lives in `22-system-design.md`. This guide
  owns the testability properties a design must have. `[X-REF 22]`
- Big-O and the complexity of the code under test live in `01-dsa-fundamentals.md`. `[X-REF 01]`

Where a concept is owned elsewhere the leaf carries `[X-REF nn]`, and the bible states the mechanism
in **one paragraph** before pointing away — it never sends the reader off empty-handed.

**Every example, entity, status code and number comes from the QuizStakes domain in
`src/scenario/scenario.md`.** The services are `ApplicationGateway`, `RouterInt`, `JwtService`,
`AccountOpening`, `PersonalDetails`, `ClientAgreements`, `AssessmentService`, `AccountActivation`,
`DocumentVerification`, `DocumentRequirements`, `ScreeningService`, `ApplicationHistory`,
`AccountMaintenance`, `ClientRestrictions`, `InternalPlatforms`, `PaymentService`, `FundsLedger`,
`CardPayments`, `BankDeposits`, `BankWithdrawal`, `BonusService`, `BalanceView`, `ProfileService`,
`PendingActions`, `NotificationService`. Test classes are named for them —
`FundsLedgerStakeReservationTest`, `ClientRestrictionsDecisionIT`, `AccountOpeningStateMachineTest`,
`AgreementVersionContractTest` — never `OrderServiceTest`, `FooTest`, `Dog extends Animal`, or
`thread1`. The current guide uses `OrderService`, `OrderRepository`, `PaymentGateway`,
`SubscriptionService`, `Account.withdraw` and `PostgreSQLContainer` against an `orders` table
throughout; **every one of those must be re-domained by the write pass.**

**The domain facts the bible's tests must be written against**, taken from scenario Appendix A:
2.4M registered clients; 380k monthly active; 14k concurrent sessions, 55k peak; 12k
registrations/day (40k on campaign launch); 7.2k applications reaching `AO-400`/day, 24k peak; 95k
card deposits/day at 40/sec; **2.8M stake reservations/day at 1,200/sec**; 2.8M settlements/day with
3,400/sec bursts; 19.8M ledger entries/day at 230 writes/sec sustained and **13,600/sec peak**,
~180 bytes/row; 24k document uploads/day at 2–6 MB; ~180 agreement document versions at 40–900 KB;
a **30 ms** restriction-decision budget, a **150 ms** stake-reservation budget, a **hard 500 ms**
self-exclusion budget, a **4 s** card-deposit end-to-end budget; the identity vendor at **600/min
estate-wide** with p50 900 ms / p99 38 s.

**The scenario rules that constrain what the test suite must prove**, restated at the point of use:

- **Invariant 8: self-exclusion takes effect before the next stake** — "the most serious client-harm
  failure possible", hard 500 ms budget. This is the invariant that must have a *test that cannot be
  deleted*, and the one that justifies a property-based and a concurrency test rather than an
  example-based one.
- **Invariant 12: restriction decisions are read live, never from a cache or token.** A test that
  stubs `ClientRestrictions` and asserts a stake succeeds proves nothing about the invariant; the
  bible must show the test that actually pins it.
- **Only `FundsLedger` writes money**, and **balances are always derived from positions, never
  stored** (assumption #20) — which makes the ledger the one place where a property-based invariant
  test (sum of positions == derived balance) is worth more than any number of example tests.
- **`BalanceView` must never be the source for a stake or withdrawal decision** — an architectural
  rule that only an architecture test (ArchUnit) can enforce continuously.
- **No cross-schema joins** — enforceable in tests, and the reason `ProfileService` composition is
  integration-tested rather than unit-tested.
- The identity vendor's **600/min** cap is why the suite may never call it: every test that touches
  `ScreeningService` uses a stub server, and the bible must say what breaks if one does not.

Tag legend:

| Tag | Meaning for the write pass |
|---|---|
| `[PROVE]` | work the argument through; do not state the result and move on |
| `[SOURCE]` | quote real documentation, spec text, javadoc or library source (short excerpt) and explain every line |
| `[BUILD]` | ship complete, compiling Java 21 code (or a complete runnable artifact where the artifact is config/CLI) |
| `[TRAP]` | must carry a `**Trap:**` marker — wrong belief, symptom, fix |
| `[RESEARCH]` | leaf exists because of the research phase; re-verify against the cited source before writing |
| `[VERSION-TRAP]` | widely-repeated claim that is version-stale; state what is true now and what changed |
| `[CURRENCY]` | version number, release date or vendor limit that drifts; state the date it was checked |
| `[X-REF nn]` | one-paragraph mechanism here, full treatment in guide nn |
| `[NUM]` | state the number, default value or time/byte arithmetic explicitly |
| `[CFG]` | give the exact configuration property/parameter name and its default value |
| `[API]` | give the exact Java type, method signature or annotation attribute |
| `[CLI]` | show the exact command (`mvn …`, `gradle …`, `docker …`) and read its output |
| `[METRIC]` | name the exact metric and what a bad value looks like |
| `[FLOW]` | must be rendered as an ordered step-by-step trace, not prose |
| `[DIAG]` | must show real output — a failure message, a stack trace, a log line — and read it line by line |
| `[TABLE]` | must be rendered as a table |
| `[SPEC]` | cite the specific section/paper/RFC, not just the document |
| `[STUDY]` | cite the empirical study by author, venue and year, with its sample size |

---

# PART 1 — BASICS

## §1.1 Why automated tests exist at all, and what one actually buys

1.1.1 The origin problem stated as a trade, not a virtue: a test spends **authoring time, execution
      time and maintenance coupling** to buy **regression confidence and change velocity**. Naming
      what you spend is the whole discipline, and it is the sentence that separates a senior answer
      from "tests are good practice". `[PROVE]`
1.1.2 The five distinct things a test buys, separated because they have different justifications and
      different tests satisfy them: **regression detection**, **design pressure** (a hard-to-test
      class is telling you about coupling), **executable specification**, **defect localisation**,
      and **refactoring licence**. `[TABLE]`
1.1.3 The sixth, usually unnamed: **onboarding**. A test suite is the only documentation that fails
      when it goes out of date.
1.1.4 The cost side, itemised honestly: authoring time, CI wall-clock, CI money, flake triage time,
      and **the option value you destroy** when a test asserts on an implementation detail you now
      want to change. `[TABLE]`
1.1.5 **A test is a liability as well as an asset**, and the balance flips when the test asserts more
      than the behaviour requires. This is the frame for every over-specification trap in the file.
      `[PROVE]`
1.1.6 The precondition that makes testing work at all: **determinism**. A non-deterministic test
      does not have a lower value than a deterministic one — past a threshold it has a *negative*
      value, because it trains the team to ignore red. `[PROVE]`
1.1.7 The arithmetic behind that claim: a suite of 2,000 tests where each independently fails
      spuriously with probability 0.0005 fails the build 63% of the time
      (`1 − 0.9995^2000 ≈ 0.632`). Per-test flakiness that looks negligible is a broken build at
      suite scale. `[PROVE]` `[NUM]`
1.1.8 The second-order consequence: once the build is red by default, **the signal is gone**, and the
      team's response is to add retries, which hides the race that will surface in production.
      `[TRAP]`
1.1.9 **Feedback latency as the governing variable.** A 10-second suite is run on every save; a
      10-minute suite is run before a push; a 40-minute suite is run by CI after you have moved on.
      Each threshold changes developer behaviour, not just wall-clock. `[NUM]` `[PROVE]`
1.1.10 The QuizStakes numbers that set the bar: 2.8M stake reservations/day at 1,200/sec means a
      one-in-a-million ordering bug fires **~3 times a day**. Tests are the only affordable way to
      probe that space before production does. `[NUM]`
1.1.11 **When not to write a test**, enumerated: throwaway spikes, generated code with no logic,
      configuration with no branch, a getter, and anything where the test would restate the
      implementation line for line. `[TABLE]`
1.1.12 The mirror: **what must always have a test** — every invariant with a client-harm consequence
      (scenario invariants 8 and 12), every bug ever fixed, every boundary in money arithmetic, and
      every state transition in `AccountOpening`. `[PROVE]`
1.1.13 **"Tests slow us down" is usually true of a specific kind of test**, and naming which kind is
      the credible answer: broad, slow, heavily-mocked tests coupled to structure. Fast behavioural
      tests speed teams up; the argument is not about testing, it is about test design.
1.1.14 The regression-test-as-bug-report rule: every production defect gets a **failing test first**,
      then the fix. The test is the proof the defect is understood, not a formality. `[FLOW]`
1.1.15 Testing's relationship to types: a stronger type makes a class of test unnecessary. A
      `record StakeAmount(BigDecimal value)` with a validating constructor removes every "negative
      stake" test from every caller. Prefer eliminating a test to writing one. `[X-REF 03]`
1.1.16 The verification-vs-validation distinction: tests verify you built the thing right;
      acceptance and exploratory testing validate you built the right thing. Automated tests cannot
      do the second, and claiming they do is a common interview overreach. `[TRAP]`
1.1.17 What a test suite categorically cannot prove: absence of bugs (Dijkstra), performance under
      real load, operability, and anything about the environment it does not run in. `[PROVE]`
1.1.18 **The one-sentence framing to give an interviewer**: "a test is a claim about behaviour that
      the build enforces; I choose the cheapest test that enforces the claim I actually care about."

## §1.2 The vocabulary, stated once

1.2.1 **Test case** vs **test method** vs **test class** vs **test suite** vs **test run** — five
      words, routinely conflated, and JUnit's own model gives them precise meanings (§ 3.2).
      `[TABLE]`
1.2.2 **System under test (SUT)** vs **collaborator** vs **fixture** vs **test double** — the four
      roles every test has, and naming them is how you decide what to fake. `[TABLE]`
1.2.3 **Arrange / Act / Assert** vs **Given / When / Then** — the same three phases in two
      vocabularies, one from xUnit and one from BDD.
1.2.4 **Unit** as the most abused word in testing: a unit is a *unit of behaviour*, not a class. The
      "one test class per production class" reading is the source of most over-mocking. `[TRAP]`
1.2.5 **Sociable** vs **solitary** unit test (Fowler's terms) — whether real collaborators
      participate. This is the distinction the word "unit" hides. `[SPEC]`
1.2.6 **Integration test** vs **integrated test** vs **system test** vs **end-to-end test** —
      four scopes, and the industry uses all four names for all four things. Define yours in the
      repo. `[TABLE]`
1.2.7 **Component test**, **service test**, **slice test**, **narrow/broad integration test** — the
      middle of the pyramid's competing vocabularies, mapped onto each other. `[TABLE]`
1.2.8 **Contract test** vs **schema test** vs **compatibility check** — three different guarantees
      (§ 2.13). `[TABLE]`
1.2.9 **Smoke test** vs **sanity test** vs **canary check** vs **synthetic monitor** — post-deploy
      vocabulary, where "test" and "monitoring" merge. `[X-REF 20]`
1.2.10 **Acceptance test** vs **acceptance criteria** vs **specification by example** — a test, a
      requirement, and a practice.
1.2.11 **Regression test** vs **characterization test** vs **golden master / approval test** — all
      three pin current behaviour; only one claims it is correct. `[TABLE]`
1.2.12 **Deterministic** vs **repeatable** vs **idempotent** vs **isolated** vs **order-independent**
      — five properties a test can have, and they are not the same. JUnit guarantees *repeatable*
      lifecycle-method order without guaranteeing *specified* order (§ 3.4). `[PROVE]`
1.2.13 **Flaky** vs **broken** vs **brittle** vs **fragile** — non-determinism, a real failure,
      over-coupling, and environment sensitivity. `[TABLE]`
1.2.14 **Test double** as the umbrella term, with **dummy / stub / spy / mock / fake** as the five
      members (§ 1.4). "Mock" as a synonym for all five is the single most common vocabulary error in
      testing interviews. `[TRAP]` `[SPEC]`
1.2.15 **Stubbing** vs **mocking** vs **faking** vs **spying** as *verbs*, and **state verification**
      vs **behaviour verification** as the two things you can assert. `[SPEC]`
1.2.16 **Classical / Detroit / Chicago** vs **mockist / London** TDD — two schools, and the terms are
      used interchangeably in pairs that candidates mix up. `[TABLE]` `[SPEC]`
1.2.17 **Inside-out / middle-out** vs **outside-in** design direction, and why the school and the
      direction correlate but are not the same axis. `[PROVE]`
1.2.18 **Seam** (Feathers) — a place where you can change behaviour without editing the code there.
      Object seam, link seam, preprocessing seam. The single most useful concept for legacy code.
      `[SPEC]`
1.2.19 **Coverage** vs **line coverage** vs **branch coverage** vs **path coverage** vs **mutation
      score** — four metrics and one that measures something different in kind. `[TABLE]`
1.2.20 **Mutant**, **killed**, **survived**, **no-coverage**, **timed out**, **equivalent mutant** —
      PIT's result vocabulary, needed to read its report. `[TABLE]`
1.2.21 **Property**, **generator/arbitrary**, **shrinking**, **falsifying example**, **seed** — the
      property-based testing vocabulary (§ 2.14).
1.2.22 **Fixture** vs **factory** vs **builder** vs **object mother** vs **test data builder** — five
      ways to make test data, with different failure modes. `[TABLE]`
1.2.23 **Setup** vs **teardown** vs **fresh fixture** vs **shared fixture** vs **immutable shared
      fixture** — and which one leaks state.
1.2.24 **Quarantine** vs **skip** vs **disable** vs **delete** — four responses to a failing test,
      only two of which are honest.
1.2.25 **Test selection** vs **test prioritisation** vs **test sharding** vs **test parallelism** —
      four different CI techniques, often all called "speeding up tests". `[TABLE]`
1.2.26 **Hermetic** as the property CI actually needs: the test brings its own world. This is the
      word that justifies Testcontainers over a shared staging database. `[PROVE]`
1.2.27 **Test pyramid** vs **testing trophy** vs **testing honeycomb** vs **test ice-cream cone** —
      three prescriptions and one anti-pattern (§ 1.3). `[TABLE]`
1.2.28 **Assertion** vs **expectation** vs **verification** — a check on state, a pre-programmed
      demand, and a check on interaction.
1.2.29 **Soft assertion** vs **hard assertion**, and `assertAll` / AssertJ `SoftAssertions` as the
      two Java implementations.
1.2.30 **Arrange-time failure** vs **assertion failure** vs **error** — JUnit reports the last two
      differently, and the distinction changes how you read a red build. `[DIAG]`

## §1.3 The ladder of test types, the pyramid, and the arguments against it

1.3.1 The full type ladder as a table with **scope / real dependencies / typical wall-clock / what it
      proves**, carried forward from the current guide's § 1 and extended: unit (solitary), unit
      (sociable), slice, narrow integration, broad integration, contract, component, end-to-end,
      smoke, acceptance, exploratory, performance, security, chaos. `[TABLE]` `[NUM]`
1.3.2 The pyramid's **four degrading properties**, preserved verbatim from the current guide and then
      proved individually: **speed**, **determinism**, **failure localisation**, **maintenance cost**.
      `[PROVE]`
1.3.3 Failure localisation made concrete: a unit failure names the bug; an E2E failure names
      "registration broke". Quantify it — mean time to diagnose is the variable, and it is where E2E
      suites actually cost you. `[PROVE]`
1.3.4 The combinatorial argument for pushing tests down: covering *n* independent branches at the
      unit level costs *n* tests; covering them through an HTTP endpoint costs a multiplicative
      product of the layers' branch counts. `[PROVE]` `[NUM]`
1.3.5 **Google's small / medium / large sizing**, which classifies by *what a test is allowed to do*
      rather than by what it is called: small = single process, no I/O, no sleep; medium = single
      machine, localhost network allowed; large = multi-machine. The target mix quoted as roughly
      **70 / 20 / 10**. `[STUDY]` `[NUM]` `[RESEARCH]`
1.3.6 Why the size-based definition is better than the name-based one: it is *enforceable* by the test
      runner (deny network, deny sleep, cap wall-clock) whereas "unit test" is enforceable only by
      review. `[PROVE]`
1.3.7 **The testing trophy** (Dodds): integration tests carry the best confidence-per-cost for typical
      web backends, because most real defects live in the seams — SQL, serialization, transaction
      boundaries, HTTP mapping — that solitary unit tests mock away. Preserve the current guide's
      framing. `[SPEC]`
1.3.8 **The testing honeycomb** (Spotify): for a microservice, the widest band is integration, with
      thin implementation-detail and integrated bands. The rationale is that a service's value is
      almost entirely in its edges. `[RESEARCH]`
1.3.9 **The ice-cream cone** as the anti-pattern: many manual/E2E tests, few unit tests. Name its
      symptom — a two-hour suite with a 30% flake rate and a QA gate.
1.3.10 **The pyramid is a heuristic about cost, not a quota.** The steelmanned version: shape your
      suite by where your defects actually come from, measured. If your last twenty incidents were
      all SQL and mapping bugs, a wider integration band is the *correct* response, and saying so is
      a strong interview answer. `[PROVE]`
1.3.11 The synthesis the current guide already states and that must survive: **unit-test logic,
      integration-test integration, and don't unit-test glue code by mocking it into meaninglessness.**
1.3.12 **The test-type decision procedure** as an ordered set of questions: is the risk in the logic
      or the wiring? does the behaviour cross a process boundary? is the dependency ours? can the
      dependency be run hermetically? Each answer eliminates rungs. `[FLOW]`
1.3.13 The QuizStakes suite shape derived, not asserted: stake-reservation arithmetic and the
      `AccountOpening` state machine are unit; `FundsLedger` SQL and locking are integration on a real
      Postgres; the `ClientRestrictions` decision path is integration *because invariant 12 forbids
      the stub*; `ProfileService`'s eight-owner composition is component; registration end-to-end gets
      exactly one E2E. `[TABLE]` `[PROVE]`
1.3.14 The counter-case for E2E kept honestly: exactly one test that proves the deployed system's
      happy path is worth more than its cost, because it is the only test that exercises
      configuration, service discovery, and the network. One, not two hundred. `[PROVE]`
1.3.15 **Ratio targets are a smell.** "30% unit, 60% integration" as a policy produces tests written
      to satisfy the ratio. Measure escaped-defect origin instead. `[TRAP]` `[METRIC]`
1.3.16 The naming/placement convention that makes the ladder operational: `*Test` for fast tests run
      by Surefire, `*IT` for integration tests run by Failsafe, JUnit `@Tag` for cross-cutting splits.
      `[CFG]`
1.3.17 The **cost-per-confidence table** for QuizStakes with real numbers: a solitary unit test of
      stake arithmetic at ~2 ms; a `@DataJpaTest` slice on a cached context at ~40 ms; a
      Testcontainers Postgres integration test at ~120 ms after a 2–4 s first-container cost; a
      `@SpringBootTest` with a real port at ~1.5 s; a full E2E through `ApplicationGateway` at
      ~25 s. `[TABLE]` `[NUM]` `[RESEARCH]`

## §1.4 Test doubles — the taxonomy done precisely

1.4.1 The five doubles as Meszaros defined them and Fowler popularised them, with the definitions
      quoted rather than paraphrased: **dummy** (passed to fill a parameter list, never used),
      **fake** (a working implementation with a production-disqualifying shortcut), **stub** (canned
      answers, no response to anything unprogrammed), **spy** (a stub that records how it was
      called), **mock** (pre-programmed with expectations that form a specification of the calls it
      should receive). `[TABLE]` `[SOURCE]` `[SPEC]`
1.4.2 The discriminator that actually matters, preserved from the current guide: **a stub feeds input
      to the test; a mock asserts on output you cannot otherwise see.** `[PROVE]`
1.4.3 **State verification** vs **behaviour verification** stated as Fowler does: only mocks *require*
      behaviour verification; every other double is normally used with state verification. `[SOURCE]`
1.4.4 The corollary rule: if you can assert on a returned value or resulting state, stub and assert on
      that — it is strictly less brittle. Reserve `verify()` for side effects with no observable
      result (a `NotificationService` email, a published event). Preserve verbatim.
1.4.5 Why the taxonomy is asked about at all: the whole vocabulary collapses into "mock" in everyday
      speech because Mockito's factory method is called `mock()` and produces a thing that is
      *usually a stub*. Say this out loud in an interview. `[TRAP]`
1.4.6 **A Mockito `mock` is a stub-and-spy hybrid**, not a Meszaros mock: it returns canned answers,
      records every invocation, and only becomes a mock when you call `verify()`. `[PROVE]` `[TRAP]`
1.4.7 **A Mockito `@Spy` is a partial mock**, which is a different thing again from a Meszaros spy: it
      wraps a *real* instance and delegates unstubbed calls to it. The naming collision is a genuine
      trap. `[TRAP]`
1.4.8 **Fake** given its full weight, because it is the underused member: an in-memory
      `Map`-backed `FundsLedgerRepository` behaves like a repository — reads see writes — with none of
      the stubbing noise, and it is reusable across every test in the module. `[BUILD]`
1.4.9 The fake's cost, stated honestly: it is production code you must maintain, and a fake that
      drifts from the real thing produces green tests and a broken system. The mitigation is a
      **shared contract test run against both** the fake and the real implementation. `[PROVE]`
1.4.10 **Dummy** as the member nobody uses deliberately, and the modern replacements: `null` where
      the signature allows it, `Mockito.mock()` with no stubbing, or a record with default values.
1.4.11 The decision table: **which double for which situation**, keyed on *is the collaborator
      stateful? / do I care what was sent to it? / is it slow or non-deterministic? / do I own its
      interface?* `[TABLE]` `[FLOW]`
1.4.12 **When to mock, and when not to** — the current guide's five rules preserved and each given a
      mechanism: mock boundaries you own; wrap third-party clients and mock the wrapper; never mock
      pure logic or value objects; never mock the thing under test; prefer a fake for anything
      stateful.
1.4.13 "Don't mock what you don't own" argued rather than asserted: a vendor SDK's fluent builder
      encodes *their* API shape, so a refactor on their side reddens your suite with zero behaviour
      change — and worse, a stubbed SDK cannot tell you their semantics changed. An adapter interface
      you own is the seam, and the adapter itself gets an integration test. `[PROVE]` `[SPEC]`
1.4.14 The nuance that makes it credible: this rule is about *stability and knowledge*, not
      ownership per se. Mocking `java.time.Clock` is fine — it is a value-like interface with
      permanent semantics that you cannot get wrong.
1.4.15 **Never mock value objects.** Mocking a `BigDecimal`, a `record StakeAmount`, or a mapper tests
      your mock configuration and nothing else. `[TRAP]`
1.4.16 **Never mock the class under test.** `@Spy` on the SUT with partial stubbing is almost always a
      signal the class does two things and should be split; name the refactoring (extract the
      stubbed-out responsibility into a collaborator). Preserve verbatim. `[TRAP]`
1.4.17 The **over-mocking failure mode** stated with its symptom, preserved verbatim: tests that pass
      while the system is broken, because every collaborator returns exactly what the test told it to.
      Plus the heuristic — if the setup is longer than the code under test, the design or the test
      approach is wrong. `[TRAP]`
1.4.18 The second-order cost of over-mocking: the test encodes the current call sequence, so the
      suite **opposes** refactoring. A suite that opposes refactoring is a suite that will be deleted.
      `[PROVE]`
1.4.19 **Self-initialising fake / record-and-replay** as the technique nobody names: capture real
      responses once, replay them thereafter. Where it is legitimate (a stable third-party payload
      shape) and where it rots (anything with dates or ids in it).
1.4.20 The QuizStakes double-selection worked end to end: `NotificationService` → mock (side effect,
      no observable result); `FundsLedgerRepository` → fake (stateful, reads must see writes);
      identity vendor client → stub server, never a Mockito mock (§ 2.12), because the wire format is
      the risk; `Clock` → a fixed `Clock`, not a mock; `ClientRestrictions` → **neither**, because
      invariant 12 means the real decision path is the thing under test. `[TABLE]` `[PROVE]`

## §1.5 The anatomy, naming and readability of a single test

1.5.1 **Arrange–Act–Assert with blank lines between the three phases**, one logical assertion per
      test, and why the blank lines are load-bearing: they let a reader find the act in one second.
      Preserve the current guide's framing.
1.5.2 **One logical assertion** clarified — one *behaviour*, which may need three `assertThat` calls
      on the same result object. The rule is not "one assert statement". `[TRAP]`
1.5.3 The **behaviour-statement naming convention** with the current guide's example re-domained:
      `reserveStake_throwsInsufficientFunds_whenCashAvailableBelowStake()`. The test is
      `subject_expectedOutcome_condition`. `[API]`
1.5.4 The naming test: **a failing test name should tell you what broke without opening the file.**
      Preserve verbatim. This is also the argument for `@DisplayName` on the harder cases.
1.5.5 The competing conventions, so the reader can defend a choice: `should…`, `given…when…then…`,
      `snake_case_sentences`, and `@Nested` classes with `@DisplayName` sentences. `[TABLE]`
1.5.6 **`@DisplayName`** and the `@DisplayNameGeneration` / `DisplayNameGenerator` surface —
      `ReplaceUnderscores`, `Simple`, `IndicativeSentences`, and the
      `junit.jupiter.displayname.generator.default` configuration parameter. `[API]` `[CFG]`
      `[RESEARCH]`
1.5.7 **Test the behaviour, not the implementation** — the property that makes a suite an asset. The
      current guide's contrast preserved: "this private method was called" blocks refactoring;
      "withdrawing 20 from a balance of 10 throws" survives any rewrite.
1.5.8 The operational test of that principle: **could you rewrite the class's internals and keep the
      test?** If not, the test is coupled to structure. `[PROVE]`
1.5.9 **Do not test private methods.** Either the behaviour is reachable through the public surface
      (test it there) or the private method is a hidden responsibility (extract it to a collaborator
      with its own public surface). Reflection-based private-method tests are a design smell with a
      maintenance bill. `[TRAP]`
1.5.10 The exception worth conceding: a genuinely complex pure algorithm inside a class with a narrow
      public surface can justify package-private visibility plus a same-package test. Say the
      trade-off, do not pretend it never happens.
1.5.11 **No logic in tests** — no `if`, no loop, no `try/catch`, no computed expected value. A test
      with a branch has untested branches. Parameterized tests are the sanctioned replacement for the
      loop. `[TRAP]`
1.5.12 **Literal expected values over computed ones.** `assertThat(fee).isEqualTo(new BigDecimal("2.50"))`
      catches a formula error; `assertThat(fee).isEqualTo(stake.multiply(rate))` restates it.
      `[PROVE]` `[TRAP]`
1.5.13 **Obvious test data.** Use values that make the assertion legible — a stake of `100.00`, a
      cash-available of `50.00` — and never `42`, `"test"`, or a random UUID where the number matters.
1.5.14 **No shared mutable state between tests**, and the JUnit default that gives it to you for free:
      a **new test instance per test method** (§ 1.6). Static fields defeat it.
1.5.15 **Assertion messages**: when a failure message would not identify the case, add one — but
      prefer a library whose default message already does (§ 1.8).
1.5.16 The **`assertEquals(expected, actual)` argument order** trap preserved verbatim: reversing it
      produces backwards failure messages that waste debugging time, and AssertJ sidesteps it
      entirely — which is a good reason to standardise on AssertJ. `[TRAP]`
1.5.17 **Test code is production code** — same review bar, same refactoring, same naming discipline —
      with one deliberate difference: prefer **duplication over indirection** in tests, because a test
      you cannot read in isolation cannot be trusted. `[PROVE]`
1.5.18 The corollary that surprises people: DRY is a *weaker* value in test code than in production
      code. An over-abstracted test base class is the mystery-guest smell (§ 2.23). `[TRAP]`
1.5.19 The **test-reading checklist** to apply in review: can I see the input? can I see the act? can I
      see the expected output? would the failure message name the bug? does it depend on any other
      test? `[FLOW]`

## §1.6 JUnit architecture and the module surface

1.6.1 The three-part architecture named exactly: **JUnit Platform** (the launcher and the engine SPI),
      **JUnit Jupiter** (the programming and extension model plus its engine), **JUnit Vintage** (an
      engine that runs JUnit 3/4 tests). The bible must be able to say which layer any given class
      belongs to. `[TABLE]` `[SOURCE]`
1.6.2 The point of the split, argued: the Platform is what IDEs and build tools integrate with, so
      alternative test languages (Spock, Cucumber, jqwik, Kotest, ArchUnit) get IDE support for free
      by shipping a `TestEngine`. JUnit 4 had no such boundary, and that is why it could not be
      extended. `[PROVE]`
1.6.3 **The version-numbering change, and why the classic interview question is now stale:** in JUnit 5
      the artifacts had *different* version streams — Platform 1.x, Jupiter 5.x, Vintage 5.x. In
      **JUnit 6 all three share one version** (6.1.3). `[VERSION-TRAP]` `[CURRENCY]` `[RESEARCH]`
1.6.4 The artifact map, by exact coordinates: `org.junit.jupiter:junit-jupiter-api`,
      `junit-jupiter-engine`, `junit-jupiter-params`, the aggregator `junit-jupiter`;
      `org.junit.platform:junit-platform-commons`, `junit-platform-engine`,
      `junit-platform-launcher`, `junit-platform-suite`, `junit-platform-console`,
      `junit-platform-reporting`, `junit-platform-testkit`; `org.junit.vintage:junit-vintage-engine`;
      and the `org.junit:junit-bom` that pins them all. `[TABLE]` `[API]`
1.6.5 **`junit-jupiter-api` is compile-scoped, `junit-jupiter-engine` is runtime-scoped**, and getting
      that wrong produces the classic "no tests found" with no error. `[TRAP]` `[DIAG]`
1.6.6 **Modules removed in JUnit 6**: `junit-platform-runner` (the `@RunWith(JUnitPlatform.class)`
      bridge that let JUnit 4 runners execute Jupiter tests) and `junit-platform-jfr` (its JFR events
      moved into `junit-platform-launcher`). `[VERSION-TRAP]` `[RESEARCH]`
1.6.7 **Java baseline: JUnit 6 requires Java 17 at runtime**; JUnit 5 required Java 8. State it,
      because it is the practical blocker for a JUnit 6 upgrade on an older service. `[NUM]`
      `[SOURCE]`
1.6.8 **JSpecify nullability annotations** adopted across the JUnit API in 6.x — relevant because it
      changes what a Kotlin or null-checked consumer sees. `[RESEARCH]`
1.6.9 The **Vintage engine** as a migration tool: it runs your JUnit 4 tests inside a JUnit 5 run, so
      migration is incremental. It is deprecated in the Boot 4 / Framework 7 world, and `SpringRunner`
      now warns. `[VERSION-TRAP]`
1.6.10 The JUnit 4 → 5 annotation map as a table, because it is asked directly: `@Before`→`@BeforeEach`,
      `@After`→`@AfterEach`, `@BeforeClass`→`@BeforeAll`, `@AfterClass`→`@AfterAll`,
      `@Ignore`→`@Disabled`, `@Category`→`@Tag`, `@RunWith`→`@ExtendWith`, `@Rule`/`@ClassRule`→
      extensions or `@RegisterExtension`, `@Test(expected=)`→`assertThrows`,
      `@Test(timeout=)`→`@Timeout`, `@Parameters`→`@ParameterizedTest`. `[TABLE]` `[API]`
1.6.11 `@Rule` and `@TestRule` have **no direct replacement** — the extension model is more general and
      the mapping is not mechanical. `junit-jupiter-migrationsupport` provides
      `@EnableRuleMigrationSupport` for a subset (`ExternalResource`, `Verifier`, `TestWatcher`).
      `[API]` `[RESEARCH]`
1.6.12 **`junit-platform.properties`** on the test classpath as the single configuration file, and the
      precedence order for a configuration parameter: explicit `LauncherDiscoveryRequest` →
      JVM system property → `junit-platform.properties`. `[CFG]` `[RESEARCH]`
1.6.13 **`org.junit.jupiter.api.Constants`** (new in JUnit 6) as the canonical place to look up
      configuration-parameter names instead of copying strings from blogs. `[API]` `[RESEARCH]`
1.6.14 **`@Suite`** and `junit-platform-suite` — declarative suites via `@SelectPackages`,
      `@SelectClasses`, `@IncludeTags`, `@ExcludeTags`, `@IncludeClassNamePatterns`. The replacement
      for JUnit 4's `@RunWith(Suite.class)`. `[API]`
1.6.15 **`ConsoleLauncher`** as the runner of last resort, and its `--fail-fast` mode added in JUnit 6.
      `[CLI]` `[RESEARCH]`
1.6.16 **`junit-platform-testkit`** — the API for testing your own extensions and engines by asserting
      on the recorded events. The tool that makes § 4's extension builds verifiable. `[API]`
1.6.17 **Experimental API policy**: `@API(status = EXPERIMENTAL | STABLE | DEPRECATED | INTERNAL)` on
      JUnit types, and the practical rule — do not build shared infrastructure on `EXPERIMENTAL`.
      `[API]`
1.6.18 **Memory-cleanup mode** (experimental, 6.1.0) for very large suites, with the engine-exclusion
      configuration parameter. Named because it is exactly the knob a 30,000-test monorepo needs.
      `[CFG]` `[RESEARCH]`

## §1.7 Jupiter's lifecycle and the core annotation surface

1.7.1 The lifecycle in order: `@BeforeAll` (static, once per class) → **new test instance** →
      `@BeforeEach` → `@Test` → `@AfterEach` → … → `@AfterAll`. Preserve the current guide's framing
      and then extend it with the extension callbacks in § 3.4. `[FLOW]`
1.7.2 **A new test instance per test method by default**, so instance fields are naturally isolated.
      This is the JUnit 4 → 5 behaviour change people trip on, and it is why `@BeforeAll` must be
      static. `[PROVE]`
1.7.3 **`@TestInstance(Lifecycle.PER_CLASS)`** changes that: one instance for the whole class,
      `@BeforeAll`/`@AfterAll` may be non-static, and **you own the isolation problem**. Legitimate
      uses (an expensive immutable fixture) and the failure mode (leaked mutable state). `[API]`
      `[TRAP]`
1.7.4 The configuration-parameter form of the same knob:
      `junit.jupiter.testinstance.lifecycle.default` (default `per_method`). `[CFG]`
1.7.5 **`@Test`** — Jupiter's own annotation, in `org.junit.jupiter.api`, with **no attributes**. The
      JUnit 4 `expected` and `timeout` attributes are gone by design. `[API]` `[TRAP]`
1.7.6 **`@Disabled`** with a reason, and the rule the current guide already states: a reason **and a
      ticket**, or delete the test. A permanently disabled test is worse than no test — it is a
      false claim of coverage. `[TRAP]`
1.7.7 **`@Tag`** and its syntax rules (no whitespace, no reserved characters), plus tag *expressions*
      in the build: `!slow`, `integration & !flaky`. `[API]` `[CFG]`
1.7.8 **`@Nested`** for grouping by scenario with shared setup, and the mechanics: an inner
      **non-static** class, outer `@BeforeEach` runs before inner, and nesting gives you a
      hierarchical `@DisplayName` in the report. `[API]`
1.7.9 The `@Nested` ordering change in JUnit 6: **deterministic ordering of nested classes**, plus
      `ClassOrderer.Default` / `MethodOrderer.Default` applying to nested classes and
      `@TestMethodOrder` now being inherited by enclosed classes. `[VERSION-TRAP]` `[RESEARCH]`
1.7.10 **`@RepeatedTest`** with its `value`, `name`, and `failureThreshold` attributes, plus
      `RepetitionInfo` injection — and the honest note that a repeated test is a *terrible* way to
      chase a race (§ 2.3). `[API]` `[TRAP]`
1.7.11 **`@TestFactory` / dynamic tests** — `DynamicTest.dynamicTest(name, executable)`,
      `DynamicContainer`, returning a `Stream`/`Iterable`. Generated at runtime, therefore **no
      lifecycle callbacks per dynamic test**, which is the distinction from `@ParameterizedTest`.
      `[API]` `[PROVE]` `[TRAP]`
1.7.12 **`@TestTemplate`** as the extension point both `@ParameterizedTest` and `@RepeatedTest` are
      built on, requiring a `TestTemplateInvocationContextProvider`. `[API]`
1.7.13 **`@Timeout`** — its `value`/`unit`, class-level application, and the configuration parameters
      `junit.jupiter.execution.timeout.default`,
      `junit.jupiter.execution.timeout.test.method.default`, and the per-lifecycle-phase variants.
      `[CFG]` `[RESEARCH]`
1.7.14 **`@Timeout` vs `assertTimeout` vs `assertTimeoutPreemptively`**: the first two run the code on
      the calling thread and report afterwards; **`assertTimeoutPreemptively` runs it on a different
      thread**, which breaks anything thread-bound — `ThreadLocal`, the Spring test transaction, the
      security context. `[TRAP]` `[SOURCE]` `[PROVE]`
1.7.15 Built-in **conditional execution** annotations, all of them:
      `@EnabledOnOs`/`@DisabledOnOs`, `@EnabledOnJre`/`@DisabledOnJre`,
      `@EnabledForJreRange`/`@DisabledForJreRange`, `@EnabledInNativeImage`/`@DisabledInNativeImage`,
      `@EnabledIfSystemProperty`/`@DisabledIfSystemProperty`,
      `@EnabledIfEnvironmentVariable`/`@DisabledIfEnvironmentVariable`,
      `@EnabledIf`/`@DisabledIf`. `[TABLE]` `[API]`
1.7.16 `junit.jupiter.conditions.deactivate` as the escape hatch that disables conditions by pattern —
      the knob for "run the tests we normally skip on this OS". `[CFG]`
1.7.17 **`Assumptions`** — `assumeTrue`, `assumeFalse`, `assumingThat` — and the semantic difference
      from a condition: an assumption **aborts** the test (reported as skipped) rather than failing
      it. The trap is using assumptions to hide an environment problem. `[API]` `[TRAP]`
1.7.18 The three test outcomes Jupiter reports — **successful / failed / aborted** — plus *skipped* at
      the container level, and how each shows up in a Surefire report. `[DIAG]`
1.7.19 **Ordering**: `@TestMethodOrder` with `MethodOrderer.OrderAnnotation` / `DisplayName` /
      `MethodName` / `Random` / `Default`, and `@Order`. Then the policy: **ordering is for
      readability of the report, never for correctness**; a test that needs an order is an
      order-dependent test (§ 2.17). `[API]` `[TRAP]`
1.7.20 **`ClassOrderer`** — `ClassName`, `DisplayName`, `OrderAnnotation`, `Random`, `Default` — and
      the configuration parameter `junit.jupiter.testclass.order.default`. The genuine use: run the
      fast classes first so a failure arrives sooner. `[CFG]` `[API]`
1.7.21 **`MethodOrderer.Random` / `ClassOrderer.Random` with a fixed seed
      (`junit.jupiter.execution.order.random.seed`)** as the deliberate technique for *exposing*
      order dependence, plus how to reproduce a failure from the logged seed. `[CFG]` `[PROVE]`
1.7.22 **Built-in parameter injection** into test and lifecycle methods: `TestInfo`,
      `TestReporter`, `RepetitionInfo`, `TestInstances` — resolved by built-in `ParameterResolver`s
      (§ 3.5). `[API]`
1.7.23 **`TestWatcher`** as the hook for "do something on pass/fail/abort/disable" — the honest place
      to build a flake reporter, rather than wrapping every test. `[API]`
1.7.24 **Meta-annotations and composed annotations**: Jupiter annotations are themselves
      `@Retention(RUNTIME)`-meta-annotatable, so `@IntegrationTest` can bundle `@Tag("integration")`
      + `@SpringBootTest` + `@Testcontainers`. This is the single highest-leverage tidiness technique
      in a large suite. `[BUILD]` `[API]`
1.7.25 **Kotlin `suspend` functions as test methods** (JUnit 6) — named for completeness because a
      polyglot codebase will hit it. `[RESEARCH]` `[VERSION-TRAP]`
1.7.26 **`@BeforeAll`/`@AfterAll` in an interface with `default` methods**, and `@Nested` inheritance:
      the two mechanisms for sharing setup without a base class. `[API]`
1.7.27 The **`@ExtendWith` on a field vs `@RegisterExtension` on a field** distinction: the former is
      declarative and static-only in effect, the latter lets you configure the extension
      programmatically and gives you a reference to it in the test. `[API]` `[PROVE]`

## §1.8 Assertions — JUnit, AssertJ, Hamcrest, and custom

1.8.1 The three assertion libraries a Java codebase realistically has, and the honest recommendation:
      **standardise on AssertJ**, keep JUnit's `assertThrows`/`assertAll`, and treat Hamcrest as
      legacy or as the price of a library that demands it (MockMvc's `andExpect`, `awaitility`'s
      matcher overloads). `[TABLE]`
1.8.2 The **JUnit `Assertions`** surface in full: `assertEquals`/`assertNotEquals`,
      `assertSame`/`assertNotSame`, `assertTrue`/`assertFalse`, `assertNull`/`assertNotNull`,
      `assertArrayEquals`, `assertIterableEquals`, `assertLinesMatch`, `assertThrows`,
      `assertThrowsExactly`, `assertDoesNotThrow`, `assertTimeout`, `assertTimeoutPreemptively`,
      `assertAll`, `assertInstanceOf`, `fail`. `[TABLE]` `[API]`
1.8.3 **`assertEquals` on `double`/`float` needs a delta** overload, and the reason is IEEE-754, not
      JUnit. `[X-REF 03]` `[TRAP]`
1.8.4 **`assertThrows`**, preserved verbatim from the current guide including the rule: never
      `try { …; fail(); } catch (E e) {}`. `assertThrows` returns the exception so you can assert on
      it. `[API]`
1.8.5 **`assertThrowsExactly`** vs `assertThrows` — subclass tolerance. Asserting the exact type is
      usually over-specification; asserting the *message or a field* is usually what you meant.
1.8.6 Asserting on an exception properly: type, message content, and — for a domain exception — the
      **error code the API contract promises** (`AO-400`, the `type` field of a Problem Details
      response). `[X-REF 12]`
1.8.7 **`assertAll`** — reports every failed assertion instead of stopping at the first. Preserve the
      current guide's line. The mechanism: it collects `Executable`s and throws a
      `MultipleFailuresError`. `[API]` `[SOURCE]`
1.8.8 **AssertJ's core idea**: one entry point (`assertThat`) whose return type is
      assertion-class-specific, so the IDE offers only the assertions that make sense for the type.
      This is why its failure messages are better — it knows what it is looking at. `[PROVE]`
1.8.9 The AssertJ surface a backend engineer needs, by exact method: `isEqualTo`,
      `isEqualByComparingTo`, `isCloseTo(…, within(…))`, `isNotNull`, `isInstanceOf`,
      `hasSize`, `contains`, `containsExactly`, `containsExactlyInAnyOrder`, `containsOnly`,
      `extracting`, `flatExtracting`, `filteredOn`, `allSatisfy`, `anySatisfy`, `satisfies`,
      `hasFieldOrPropertyWithValue`, `usingRecursiveComparison`, `hasMessageContaining`,
      `hasRootCauseInstanceOf`, `isPresent`/`hasValue` for `Optional`. `[TABLE]` `[API]`
1.8.10 The current guide's two AssertJ examples preserved and re-domained: the
      `extracting(…).containsExactly(…)` chain over a ledger-entry list, and the
      `usingRecursiveComparison().ignoringFields("id","createdAt")` comparison of a
      `ClientAgreementSnapshot`.
1.8.11 **`usingRecursiveComparison`** in depth — `ignoringFields`, `ignoringFieldsOfTypes`,
      `ignoringCollectionOrder`, `withComparatorForType`, `comparingOnlyFields` — and the trap: it
      compares *everything* by default, so a new field silently enters your assertion. `[API]`
      `[TRAP]`
1.8.12 **AssertJ `SoftAssertions`** and `assertSoftly`, and when to prefer them over `assertAll`.
1.8.13 **`assertThatThrownBy` / `catchThrowable` / `assertThatExceptionOfType`** as AssertJ's
      exception surface, and `assertThatNoException`. `[API]`
1.8.14 **`BigDecimal` comparison** — the current guide's flagship trap, preserved verbatim and then
      proved: `new BigDecimal("10.00").equals(new BigDecimal("10.0"))` is `false` because `equals`
      compares scale as well as unscaled value, while `compareTo` does not. Therefore
      `isEqualByComparingTo("10.00")`. This is the highest-frequency money-test bug in the language.
      `[TRAP]` `[PROVE]` `[X-REF 03]`
1.8.15 The QuizStakes instance that makes it bite: `FundsLedger` sums 180-byte rows into a
      `BigDecimal` whose scale depends on the JDBC driver and the column type, so an equality
      assertion on a derived balance is a scale assertion in disguise. `[NUM]`
1.8.16 **Doubles get a tolerance, always** — `isCloseTo(x, within(0.001))` or `Offset`/`Percentage`.
      Preserve the current guide's line.
1.8.17 Asserting on **`java.time`**: `isBefore`/`isAfter`/`isEqualTo`, truncation
      (`truncatedTo(ChronoUnit.SECONDS)`) as the standard fix for a nanosecond-precision mismatch
      after a database round trip, and `isCloseTo(…, within(1, ChronoUnit.SECONDS))`. `[X-REF 03]`
      `[TRAP]`
1.8.18 Asserting on **collections without asserting on order** — `containsExactlyInAnyOrder` — and the
      current guide's rule preserved: never assume `HashMap`/`HashSet` iteration order. `[X-REF 02]`
      `[TRAP]`
1.8.19 Asserting on **JSON**: JSONAssert (`JSONCompareMode.LENIENT` vs `STRICT`), AssertJ's
      `JsonPathAssert`/`JsonContentAssert`, Boot's `JacksonTester`, and the choice — lenient
      comparison is the right default because a contract test should not break when the provider adds
      a field. `[PROVE]` `[X-REF 12]`
1.8.20 **Custom assertions** as the readability lever: an `assertThat(ledgerEntry)` returning a
      `LedgerEntryAssert extends AbstractAssert<LedgerEntryAssert, LedgerEntry>` with domain methods
      (`isSettled()`, `hasStakeOf("100.00")`). Complete with the `assertj-assertions-generator` note.
      `[BUILD]` `[API]`
1.8.21 **Hamcrest** for what it still is: `assertThat(actual, matcher)`, the matcher library (`is`,
      `hasItem`, `hasProperty`, `allOf`), and its structural weakness — matcher composition is not
      type-directed, so the IDE cannot help you. `[API]`
1.8.22 Where Hamcrest is unavoidable: `MockMvcResultMatchers` (`jsonPath("$.title", is("Not Found"))`),
      and Awaitility's matcher overloads. Know it well enough to read it. `[X-REF 12]`
1.8.23 **`org.hamcrest:hamcrest` 3.0** is the current artifact; `hamcrest-all` and `hamcrest-core` are
      superseded, and a stale `hamcrest-core` on the classpath causes `NoSuchMethodError`s that look
      like framework bugs. `[VERSION-TRAP]` `[DIAG]` `[RESEARCH]`
1.8.24 The **failure-message quality comparison** rendered as a table: the same failing assertion
      written in JUnit, Hamcrest and AssertJ, with the actual message each produces. This is the
      argument for AssertJ, made by evidence rather than assertion. `[TABLE]` `[DIAG]`
1.8.25 **`fail()` as a legitimate tool** in exactly two places: an unreachable branch in a switch
      over a sealed type, and a "not yet implemented" marker on a test you are about to write.
1.8.26 **AssertJ's `as("…")` describedAs** and `withFailMessage` — for the case where the value alone
      does not identify which of 200 parameterized cases failed. `[API]`
1.8.27 **ArchUnit** as an assertion library for architecture, introduced here and used in § 2.24:
      `classes().that().resideInAPackage("..balanceview..").should().onlyBeAccessed()…` is how the
      scenario's "`BalanceView` must never authorise a stake" rule becomes a build failure rather
      than a code-review convention. `[BUILD]` `[PROVE]`

## §1.9 Parameterized, data-driven and generated tests

1.9.1 The trigger rule, preserved from the current guide: **parameterize the moment you would
      copy-paste a test and change one literal** — especially for boundary cases.
1.9.2 **`@ParameterizedTest`** and its `name` attribute with the placeholders `{index}`,
      `{argumentsWithNames}`, `{0}`, `{1}`, `{displayName}`. `[API]` `[CFG]`
1.9.3 **`@ValueSource`** — `ints`, `longs`, `doubles`, `strings`, `chars`, `booleans`, `classes` — and
      its limit: one parameter only. `[API]`
1.9.4 **`@CsvSource`** with the current guide's example re-domained to the stake-fee table, plus its
      attributes: `delimiter`/`delimiterString`, `nullValues`, `emptyValue`, `quoteCharacter`,
      `useHeadersInDisplayName`, `textBlock`, and (new in JUnit 6) a configurable **comment
      character**. `[API]` `[RESEARCH]`
1.9.5 **`@CsvSource(textBlock = """…""")`** with a Java 21 text block as the readable form of a
      wide truth table — the single biggest readability win in parameterized testing. `[BUILD]`
1.9.6 **`@CsvFileSource`** — `resources`, `files`, `numLinesToSkip`, `encoding`, `lineSeparator` — and
      the trade-off: an external fixture file is the **mystery guest** smell unless it is small and
      adjacent. `[API]` `[TRAP]`
1.9.7 **JUnit 6 replaced its CSV parsing with FastCSV.** Quoting, escaping and whitespace edge cases
      can behave differently from JUnit 5. Anything relying on the old parser's quirks needs
      re-checking on upgrade. `[VERSION-TRAP]` `[RESEARCH]`
1.9.8 **`@MethodSource`** — a static factory returning `Stream<Arguments>`/`Iterable`, the
      same-class default and the `"fqcn#method"` form, and why it is the right source for *objects*
      rather than literals. `[API]`
1.9.9 **`@EnumSource`** with `names`, `mode` (`INCLUDE`, `EXCLUDE`, `MATCH_ALL`, `MATCH_ANY`,
      `MATCH_NONE`) — and the highest-value use in this domain: iterate every `AccountOpening` status
      (`AO-100` … `AO-400`) so **a new status breaks the test**, which is the point. `[API]` `[PROVE]`
1.9.10 **`@NullSource`, `@EmptySource`, `@NullAndEmptySource`** and their composition with
      `@ValueSource` for the "blank input" family. `[API]`
1.9.11 **`@FieldSource`** (JUnit 5.11+/6.x) — arguments from a static field, for the case where a
      constant list already exists. `[API]` `[RESEARCH]`
1.9.12 **`@ArgumentsSource` + `ArgumentsProvider`** as the general escape hatch, and
      `@ParameterizedTest`'s SPI trio: `ArgumentsProvider`, `ArgumentConverter`
      (`SimpleArgumentConverter`, `TypedArgumentConverter`, `@ConvertWith`), and
      `ArgumentsAggregator` (`@AggregateWith`, `ArgumentsAccessor`). `[API]`
1.9.13 **Implicit argument conversion**: `String` → enum, `String` → `java.time` types, `String` →
      `UUID`, and the factory-method/constructor fallback. This is why `@CsvSource` can feed a
      `BigDecimal` parameter directly — and why an unparseable literal fails with a conversion
      error rather than an assertion failure. `[PROVE]` `[DIAG]`
1.9.14 **`@ParameterizedClass` / `@ClassTemplate`** (new in JUnit 6) — the whole class is instantiated
      once per argument set, so shared setup runs per case. This is what people were faking with
      `@Nested` + `@MethodSource` before. `[VERSION-TRAP]` `[API]` `[RESEARCH]`
1.9.15 The two new extension callbacks it introduced —
      `BeforeClassTemplateInvocationCallback` / `AfterClassTemplateInvocationCallback` — which change
      the canonical callback-order answer (§ 3.4). `[RESEARCH]`
1.9.16 **`@ParameterizedTest` vs `@TestFactory`**: the parameterized test is declarative and gets full
      lifecycle callbacks per invocation; the dynamic test is computed at runtime and does not. Pick
      the factory only when the cases genuinely cannot be enumerated at compile time. `[PROVE]`
      `[TABLE]`
1.9.17 The parameterization trap: a case table that grows to 60 rows is often a **missing abstraction
      or a property-based test** (§ 2.14). If the expected value is computed by a formula in the
      table, you have written the implementation twice. `[TRAP]`
1.9.18 The other trap: a parameterized test where **one row needs different setup** invariably grows an
      `if` in the test body. Split it. `[TRAP]`
1.9.19 The QuizStakes truth tables that must be parameterized in the bible: the stake-eligibility
      matrix (cash available × restriction state × agreement version), the `AO-*` state-transition
      table, and the deposit-limit boundary set (`0.00`, `0.01`, limit−`0.01`, limit, limit+`0.01`).
      `[TABLE]` `[NUM]`

## §1.10 Mockito — the basic surface

1.10.1 The setup, re-domained from the current guide's example:
      `@ExtendWith(MockitoExtension.class)` with `@Mock FundsLedgerRepository`,
      `@Mock NotificationService`, `@InjectMocks StakeReservationService`. `[BUILD]` `[API]`
1.10.2 The three ways to create a mock and when each is right: `Mockito.mock(Type.class)` (explicit,
      works anywhere), `@Mock` + `MockitoExtension` (declarative, gives you strict stubs), and
      `@Mock` + `MockitoAnnotations.openMocks(this)` (manual, for a non-JUnit runner). `[TABLE]`
      `[API]`
1.10.3 **`MockitoExtension`** in detail: it initialises `@Mock`/`@Spy`/`@Captor`/`@InjectMocks`,
      injects mocks as **test-method parameters**, validates framework usage after each test, and
      applies `Strictness.STRICT_STUBS` by default. `[API]` `[SOURCE]` `[RESEARCH]`
1.10.4 **`@MockitoSettings(strictness = …)`** to change it per class, and `Mockito.lenient()` /
      `@Mock(lenient = true)` to change it per stubbing. `[API]`
1.10.5 The three strictness levels named exactly — `Strictness.LENIENT`, `Strictness.WARN`,
      `Strictness.STRICT_STUBS` — and what each does. `[TABLE]` `[API]`
1.10.6 **Strict stubs is a feature, not an obstacle**, preserved from the current guide: failing on
      unused stubbings catches tests that have drifted from the code. `[PROVE]`
1.10.7 The two exceptions strict stubs throws, both by exact name:
      **`UnnecessaryStubbingException`** (a stubbing no test used) and
      **`PotentialStubbingProblem`** (a stubbed method called with different arguments). Reading each
      message correctly is the skill. `[DIAG]` `[API]` `[RESEARCH]`
1.10.8 The nuance that trips people: a stubbing in `@BeforeEach` used by only some test methods
      triggers `UnnecessaryStubbingException` under `MockitoExtension` — and the fix is to move the
      stubbing into the tests that need it, not to go lenient. `[TRAP]` `[RESEARCH]`
1.10.9 **`when(...).thenReturn(...)` vs `doReturn(...).when(...)`** — the current guide's explanation
      preserved verbatim and then made mechanical: `when(mock.foo())` **actually invokes** `foo()` on
      the mock to record the stubbing, which on a plain mock is harmless but on a `@Spy` executes the
      real method with real side effects, and which cannot work for `void`. `[PROVE]` `[TRAP]`
1.10.10 The selection rule, preserved: `when/thenReturn` for plain mocks (type-safe);
      `doReturn/doThrow/doNothing/doAnswer … when` for spies, `void` methods, and consecutive-call
      stubbing on spies. `[TABLE]`
1.10.11 **Consecutive stubbing**: `thenReturn(a, b, c)` and chained `.thenReturn(a).thenThrow(…)`, and
      the semantics of the last value repeating. `[API]`
1.10.12 **`thenThrow`** and the checked-exception rule: Mockito refuses to stub a checked exception the
      method does not declare, and the error message says so. `[DIAG]`
1.10.13 **`thenAnswer` / `Answer<T>`** — computing a return from the arguments via
      `InvocationOnMock`, and the honest warning: an `Answer` with logic in it is a fake written
      badly. Prefer a real fake. `[TRAP]`
1.10.14 **`thenCallRealMethod`** and where it is legitimate (an abstract class's concrete template
      method).
1.10.15 **Argument matchers**: `any()`, `anyLong()`, `anyString()`, `eq()`, `isNull()`, `isNotNull()`,
      `argThat(…)`, `same()`, `contains()`, `startsWith()`, `intThat(…)`. `[TABLE]` `[API]`
1.10.16 **Matchers are all-or-nothing** — the current guide's trap preserved with its exception name:
      `when(repo.find(anyLong(), "SETTLED"))` throws `InvalidUseOfMatchersException`; use
      `eq("SETTLED")`. `[TRAP]` `[DIAG]`
1.10.17 Why that restriction exists at all, which is the answer that shows understanding: matchers are
      recorded on a **thread-local stack** during the recording call, not passed as values, so
      Mockito cannot tell a literal from a matcher by position — it can only count. `[PROVE]`
      `[X-REF 05]`
1.10.18 The consequence: a matcher used *outside* a stubbing or verification corrupts that stack and
      the failure surfaces in an unrelated later test. This is a real and confusing failure mode.
      `[TRAP]` `[DIAG]`
1.10.19 **`anyString()` does not match `null`** and `any()` does — a small asymmetry that produces
      "stubbing didn't apply" mysteries. `[TRAP]` `[RESEARCH]`
1.10.20 **Verification**: `verify(mock).method(args)`, `verify(mock, times(n))`, `never()`,
      `atLeastOnce()`, `atLeast(n)`, `atMost(n)`, `only()`, `calls(n)`, `timeout(ms)`, `after(ms)`.
      `[TABLE]` `[API]` `[SOURCE]`
1.10.21 **`verifyNoInteractions`** vs **`verifyNoMoreInteractions`** vs the removed
      `verifyZeroInteractions`, and the current guide's rule preserved: blanket
      `verifyNoMoreInteractions` makes every test maximally brittle. `[TRAP]`
1.10.22 **`InOrder`** verification, and the warning: asserting call *order* is asserting an
      implementation detail unless the order is part of the contract (write-then-publish in an outbox
      is; two independent repository reads are not). `[PROVE]` `[TRAP]`
1.10.23 **`ArgumentCaptor`** — the current guide's example re-domained to
      `verify(ledgerRepository).save(captor.capture())` on a `LedgerEntry`, and the selection rule
      preserved verbatim: a captor when you want to assert on *properties* of the argument, an
      `eq`/`argThat` matcher when you want the verification itself to be the assertion; the captor's
      failure message is much better. `[API]` `[PROVE]`
1.10.24 `@Captor` vs `ArgumentCaptor.forClass`, and `getAllValues()` for multi-invocation capture.
      `[API]`
1.10.25 **`@InjectMocks`** and the honest assessment: it silently does nothing when it cannot resolve a
      dependency, leaving a `null` field and an NPE that looks unrelated. With **constructor
      injection and a `record`-like service**, plain `new StakeReservationService(repo, clock)` is
      clearer and fails at compile time. `[TRAP]` `[PROVE]`
1.10.26 **`@Spy`** — partial mocking of a real instance — with the current guide's rule preserved
      (a spy on the SUT is a design smell) and the one legitimate case named (a legacy class you
      cannot yet split, with a documented seam).
1.10.27 **The `verify` anti-pattern**, preserved verbatim: `verify(repo).save(entry)` in a test that
      already asserts on the returned entry is redundant and welds the test to the implementation —
      change `save` to `saveAll` and the test fails though behaviour is identical. `[TRAP]`
1.10.28 **`reset(mock)`** and why its presence in a test almost always means the test does two things.
      `[TRAP]`
1.10.29 **Default answers** on an unstubbed method: `null` for objects, `0`/`false` for primitives, an
      **empty collection** for collection types, `Optional.empty()` for `Optional`. Knowing this
      prevents half of all "why is it null" test debugging. `[TABLE]` `[NUM]` `[PROVE]`
1.10.30 The alternative default answers by exact constant: `RETURNS_DEFAULTS`, `RETURNS_SMART_NULLS`,
      `RETURNS_MOCKS`, `RETURNS_DEEP_STUBS`, `CALLS_REAL_METHODS`, `RETURNS_SELF`. `[TABLE]`
      `[SOURCE]`
1.10.31 **`RETURNS_DEEP_STUBS` is a smell detector**: needing `when(a.getB().getC().getD())` means the
      test is reaching through three objects, which is a Law-of-Demeter violation in the production
      code. `[TRAP]` `[PROVE]`
1.10.32 **`RETURNS_SMART_NULLS`** as a debugging aid — it returns a placeholder that throws with the
      location of the unstubbed call — and why it is not the default.
1.10.33 **`@Mock` vs `@MockitoBean` vs the deprecated `@MockBean`** — the current guide's paragraph
      preserved and corrected: `@Mock` is plain Mockito with no Spring and microsecond cost;
      `@MockitoBean` replaces a bean **in the Spring context** and therefore changes the context cache
      key. Note that `@MockitoBean` is a **Spring Framework** annotation, not a Boot one. `[TRAP]`
      `[VERSION-TRAP]`
1.10.34 The cost consequence preserved verbatim and then quantified in § 2.7: **each distinct set of
      mock beans creates and caches a new application context** — twenty test classes with slightly
      different sets means twenty context startups and a build that takes minutes. `[NUM]`
1.10.35 What Mockito **cannot** mock, stated precisely so the answer is not folklore: `private`
      methods, `native` methods, package-visible methods of `java.*`, `equals`/`hashCode`, and
      (without the inline mock maker) `final` classes and `static` methods. `[TABLE]` `[SOURCE]`
      `[RESEARCH]`
1.10.36 `Mockito.mockingDetails(obj)` and `MockUtil` for asking "is this a mock, and what has it seen"
      — the diagnostic tool for a confusing failure. `[API]`

## §1.11 Spring Boot testing — the basic surface

1.11.1 What `spring-boot-starter-test` actually brings, enumerated: JUnit Jupiter, Spring Test +
      Spring Boot Test, AssertJ, Hamcrest, Mockito, JSONassert, JsonPath, XMLUnit, and Awaitility in
      Boot 4. Knowing the list stops people adding duplicate dependencies at conflicting versions.
      `[TABLE]` `[RESEARCH]`
1.11.2 **The Boot 4 starter reorganisation**: `spring-boot-starter-web` → `spring-boot-starter-webmvc`,
      and per-area test starters (`spring-boot-starter-webmvc-test`,
      `spring-boot-starter-restclient-test`). `[VERSION-TRAP]` `[RESEARCH]`
1.11.3 **`@SpringBootTest`** — what it does: finds the primary configuration by searching *up the
      package hierarchy* for `@SpringBootConfiguration`/`@SpringBootApplication`, then loads the whole
      context. `[SOURCE]` `[FLOW]`
1.11.4 The consequence of that search, which surprises people: a test in a package *above* the
      application class finds nothing and fails with "Unable to find a @SpringBootConfiguration".
      `[TRAP]` `[DIAG]`
1.11.5 **`webEnvironment`** with all four values and exactly what each loads: `MOCK` (default — a
      mock servlet environment, **no server started**), `RANDOM_PORT` (real server, random port),
      `DEFINED_PORT` (real server, the configured port or 8080), `NONE` (no web environment at all).
      `[TABLE]` `[SOURCE]` `[CFG]`
1.11.6 `@SpringBootTest(properties = …)` and `args = …` for per-test overrides — and the note that
      **both change the context cache key** (§ 2.7). `[API]` `[PROVE]`
1.11.7 **`@LocalServerPort`** / `@Value("${local.server.port}")` for a `RANDOM_PORT` test, and why a
      random port is the correct default in CI (port collisions under parallelism — § 2.17).
      `[PROVE]`
1.11.8 **The nineteen test slices, enumerated exactly** as the Boot reference appendix lists them:
      `@DataCassandraTest`, `@DataCouchbaseTest`, `@DataElasticsearchTest`, `@DataJdbcTest`,
      `@DataJpaTest`, `@DataLdapTest`, `@DataMongoTest`, `@DataNeo4jTest`, `@DataR2dbcTest`,
      `@DataRedisTest`, `@GraphQlTest`, `@JdbcTest`, `@JooqTest`, `@RestClientTest`,
      `@WebClientTest`, `@WebFluxTest`, `@WebMvcTest`, `@WebServiceClientTest`,
      `@WebServiceServerTest` — plus `@JsonTest`. The current guide lists five. `[TABLE]` `[SOURCE]`
      `[RESEARCH]`
1.11.9 The slice mechanism in one sentence: a slice annotation is a **type-filtered
      auto-configuration subset** — it applies only the auto-configurations relevant to that layer and
      component-scans only that layer's stereotypes. `[PROVE]`
1.11.10 **`@WebMvcTest`** — what is in the slice, by exact type: `@Controller`, `@ControllerAdvice`,
      `@JacksonComponent` (and the deprecated `@JsonComponent`), `Converter`, `GenericConverter`,
      `Filter`, `HandlerInterceptor`, `WebMvcConfigurer`, `WebMvcRegistrations`,
      `HandlerMethodArgumentResolver`, plus `WebSecurityConfigurer` beans. What is **not**: regular
      `@Component`s, `@Service`s, repositories, and `@ConfigurationProperties` unless
      `@EnableConfigurationProperties` is present. `[TABLE]` `[SOURCE]`
1.11.11 The direct consequence: the controller's collaborator is missing, so you must provide it with
      `@MockitoBean`. The current guide's `@WebMvcTest` example preserved and re-domained to
      `AccountOpeningController` + `@MockitoBean AccountOpening`. `[BUILD]`
1.11.12 **`@WebMvcTest` auto-configures both `MockMvc` and `MockMvcTester`** (the latter when AssertJ
      is present). `[RESEARCH]` `[VERSION-TRAP]`
1.11.13 **`@DataJpaTest`** — `@Entity` scanning, Spring Data repositories, `TestEntityManager`, an
      **embedded database by default**, and `@Transactional` with rollback per test. `[SOURCE]`
1.11.14 **`@AutoConfigureTestDatabase(replace = NONE)`** as the switch that stops the embedded-database
      substitution — the single line that makes `@DataJpaTest` run against a Testcontainers Postgres
      instead of H2. This is the most important one-line fix in the whole Spring testing surface.
      `[CFG]` `[API]` `[PROVE]`
1.11.15 **`@JsonTest`** — Jackson `JsonMapper`, `@JacksonComponent` beans, Gson and JSONB support, and
      the testers: `JacksonTester`, `GsonTester`, `JsonbTester`, `BasicJsonTester`, configured by
      `@AutoConfigureJsonTesters`. `[SOURCE]` `[API]`
1.11.16 **`@RestClientTest`** — a `RestClient.Builder`/`RestTemplateBuilder` wired to
      `MockRestServiceServer`, for testing an outbound client's URL building, headers and error
      mapping without a network. `[API]`
1.11.17 **`@JdbcTest` vs `@DataJdbcTest` vs `@DataJpaTest` vs `@JooqTest`** — four database slices with
      different contents; picking the wrong one is why "my repository bean doesn't exist". `[TABLE]`
1.11.18 **Slices do not compose.** You cannot put `@WebMvcTest` and `@DataJpaTest` on one class; the
      documented answer is to pick one and add the individual `@AutoConfigure…` annotations you need.
      `[SOURCE]` `[TRAP]`
1.11.19 **`@TestConfiguration`** — the current guide omits it entirely. As a **static inner class** it
      is added to the primary configuration automatically; as a **top-level class** it is *not*
      picked up by component scanning and must be `@Import`ed. That asymmetry is the whole reason it
      exists (it stops test config leaking into production scans). `[SOURCE]` `[PROVE]` `[TRAP]`
1.11.20 **`@TestConfiguration` vs `@Configuration` in a test** — the latter *replaces* the primary
      configuration; the former *supplements* it. Getting this backwards produces a context with
      nothing in it. `[TRAP]`
1.11.21 **Test property sources**, all four mechanisms with their precedence:
      `@TestPropertySource(properties/locations)`, `@SpringBootTest(properties)`,
      `@ActiveProfiles` + `application-test.yml`, and `@DynamicPropertySource`. `[TABLE]` `[CFG]`
1.11.22 **`@DynamicPropertySource`** — a `static void` method taking `DynamicPropertyRegistry`, whose
      values are `Supplier`s evaluated **lazily** so a container's mapped port is available. The
      mechanism that made Testcontainers usable before `@ServiceConnection`. `[API]` `[PROVE]`
1.11.23 `DynamicPropertyRegistry` as an **injectable bean** in newer Framework versions — the
      non-static alternative. `[RESEARCH]`
1.11.24 **`@ActiveProfiles`** and the discipline: a `test` profile is fine, a `test`/`test-ci`/
      `test-local` split multiplies your context cache keys (§ 2.7). `[TRAP]`
1.11.25 **`@Sql` and `@SqlMergeMode`** — declarative script execution before/after a test method,
      run by `SqlScriptsTestExecutionListener`. The right tool for a fixture too big for a builder
      and too specific for a migration. `[API]`
1.11.26 **`@DirtiesContext`** and its `ClassMode` values (`BEFORE_CLASS`, `AFTER_CLASS`,
      `BEFORE_EACH_TEST_METHOD`, `AFTER_EACH_TEST_METHOD`) and `MethodMode`. Then the rule the current
      guide already states: avoid it unless you genuinely mutated the context, because it **destroys
      the cached context** for everyone. `[SOURCE]` `[TRAP]`
1.11.27 **`@MockitoBean` / `@MockitoSpyBean` / `@TestBean`** — the three bean-override annotations, in
      `org.springframework.test.context.bean.override.*`, with `@TestBean` being the "replace with a
      real hand-built instance" option that nobody uses and often should. `[API]` `[TABLE]`
1.11.28 In Framework 7 / Boot 4 these **support non-singleton beans**; previously singleton-only.
      `[VERSION-TRAP]` `[RESEARCH]`
1.11.29 **`@MockBean`/`@SpyBean` are deprecated** (Boot 3.4) in favour of the Framework annotations.
      Both still appear in every tutorial. `[VERSION-TRAP]`
1.11.30 **`@ServiceConnection`** — the annotation that replaces most `@DynamicPropertySource` blocks by
      deriving connection properties from a container directly (§ 2.6). `[API]`
1.11.31 **`spring-boot-testcontainers`** and `@ImportTestcontainers` / `@TestcontainersConfiguration`
      as the Boot-side integration surface. `[API]` `[RESEARCH]`
1.11.32 **`ApplicationContextRunner`** / `WebApplicationContextRunner` /
      `ReactiveWebApplicationContextRunner` — the *fast* way to test auto-configuration and
      conditionals without starting a context per case. Almost nobody knows it exists; it is the
      right answer to "how would you test a Spring Boot starter". `[API]` `[BUILD]` `[X-REF 07]`
1.11.33 **`@AutoConfigureMockMvc(addFilters = false)`** — the current guide's warning preserved: use it
      only when you deliberately want to skip security, otherwise your controller tests will not
      catch an auth misconfiguration. `[TRAP]` `[X-REF 13]`
1.11.34 **`spring-security-test`**: `@WithMockUser`, `@WithAnonymousUser`, `@WithUserDetails`,
      `@WithSecurityContext`, and `SecurityMockMvcRequestPostProcessors.csrf()` / `jwt()` /
      `oauth2Login()`. One paragraph on the mechanism (a `TestExecutionListener` populating the
      `SecurityContextHolder`), then point away. `[X-REF 13]`
1.11.35 **`@ApplicationEvents` and `ApplicationEvents`** injection — asserting on published events
      without a mock, backed by `ApplicationEventsTestExecutionListener`. The clean way to test
      "an event was published" in the outbox pattern. `[API]` `[X-REF 14]`
1.11.36 **`OutputCaptureExtension` / `CapturedOutput`** — asserting on log output when the log *is* the
      contract (an audit line). With the caveat that asserting on log text is brittle by nature.
      `[API]` `[TRAP]`
1.11.37 **`@JsonTest` + a golden JSON file** as the cheapest possible guard on a serialization
      contract, and its relationship to real contract testing (§ 2.13). `[X-REF 12]`

## §1.12 The build surface — how tests actually get run

1.12.1 **Maven Surefire vs Failsafe** — the same engine, different phases and different failure
      semantics: Surefire runs in `test` and fails the build immediately; Failsafe runs in
      `integration-test`, defers failure to `verify`, so `post-integration-test` teardown still runs.
      That deferral is the entire reason Failsafe exists. `[PROVE]` `[CFG]`
1.12.2 Their default include patterns, exactly: Surefire takes `**/Test*.java`, `**/*Test.java`,
      `**/*Tests.java`, `**/*TestCase.java`; Failsafe takes `**/IT*.java`, `**/*IT.java`,
      `**/*ITCase.java`. This is why the `*Test` / `*IT` convention is not arbitrary. `[NUM]`
      `[CFG]` `[RESEARCH]`
1.12.3 **`forkCount` / `reuseForks` / `argLine`** in Surefire, and what each buys: process-level
      parallelism, JVM reuse (fast but leaks static state between classes), and the JVM flags —
      including the `${argLine}` that the JaCoCo agent injects, and the classic bug of overwriting it.
      `[CFG]` `[TRAP]` `[DIAG]`
1.12.4 Surefire's own `parallel` / `threadCount` / `useUnlimitedThreads` settings vs **JUnit
      Platform's** parallel execution (§ 3.6) — two independent parallelism mechanisms that can be
      enabled at once, with confusing results. `[TRAP]` `[TABLE]`
1.12.5 **Gradle's `Test` task**: `useJUnitPlatform { includeTags/excludeTags }`, `maxParallelForks`,
      `forkEvery`, `systemProperty`, `testLogging`, and Gradle's build cache / **up-to-date checks**
      skipping the test task entirely — which is a feature until you are debugging a flake. `[CFG]`
      `[TRAP]`
1.12.6 Gradle's `test` vs a separate `integrationTest` source set / **JVM test suites plugin**, and
      why a separate source set beats tag filtering for a slow suite. `[CFG]`
1.12.7 **Tag-based splitting in the build** as the current guide's `@Tag` advice made concrete, in
      both Maven (`groups`/`excludedGroups`) and Gradle (`includeTags`). `[CFG]` `[CLI]`
1.12.8 **Reports**: the Surefire XML schema, `junit-platform-reporting`'s **Open Test Reporting**
      format, and why CI systems parse the XML — which is what makes flake detection possible at all
      (§ 2.22). `[DIAG]`
1.12.9 **`junit-platform.properties` as the place for suite-wide policy**: parallelism, default
      timeouts, display-name generator, test-instance lifecycle. One file, checked in, reviewed.
      `[CFG]` `[BUILD]`
1.12.10 **Running a single test from the CLI** in both tools — `mvn test -Dtest=ClassName#method`,
      `gradle test --tests "…"` — because an interviewer asking "how do you debug one failing test"
      expects fluency, not an IDE click. `[CLI]`
1.12.11 **The build as the definition of the suite**: if a test only runs in someone's IDE, it does not
      exist. Correspondingly, if the build skips tests by default (`-DskipTests` in a profile), the
      suite does not exist either. `[TRAP]`
1.12.12 `-DfailIfNoSpecifiedTests`, `--fail-fast`, and `-Dsurefire.failIfNoTests` — the flags that stop
      "0 tests run" from being reported as success. The silent-zero-tests build is a real and
      embarrassing failure mode. `[CFG]` `[TRAP]` `[DIAG]`
1.12.13 **Test JVM memory and container limits**: forked test JVMs each take a heap, and a CI container
      with a 2 GB limit and `forkCount=4` gets OOM-killed. The arithmetic, shown. `[NUM]` `[X-REF 19]`
      `[X-REF 06]`
1.12.14 **Pinning locale, timezone and encoding in the build** —
      `-Duser.timezone=UTC -Duser.language=en -Dfile.encoding=UTF-8` — as the standing fix for an
      entire flake category (§ 2.2). One line in `argLine`, permanently. `[CFG]` `[PROVE]`

---

# PART 2 — INTERMEDIATE

## §2.1 The master cost model of a test suite

2.1.1 **The master cost table** — every test type against **first-run cost / steady-state cost /
      what dominates it / what makes it slower**, with real numbers for a QuizStakes module. This is
      the one table in the file to be able to redraw from memory. `[TABLE]` `[NUM]`
2.1.2 The decomposition that makes the table honest: total suite time is
      `JVM start + classpath scan + (context builds × context cost) + (containers × container cost)
      + Σ per-test cost`, and for a typical Spring service the middle two terms dominate by an order
      of magnitude. `[PROVE]` `[NUM]`
2.1.3 **Fixed vs marginal cost** as the frame: a Spring context is a fixed cost you pay per *distinct
      configuration*; a test is a marginal cost. Therefore the lever is almost never "write fewer
      tests" — it is "have fewer distinct configurations". `[PROVE]`
2.1.4 The arithmetic worked: 400 tests across 40 classes sharing **one** context (4 s) at 30 ms each
      = 16 s. The same 400 tests across 40 classes each with a distinct `@MockitoBean` set = 40 × 4 s
      + 12 s = **172 s**, a 10.75× regression with identical test code. `[NUM]` `[PROVE]`
2.1.5 The Testcontainers equivalent: a Postgres container at ~2.5 s started **once per JVM** (static
      singleton) vs once per class across 20 classes = 2.5 s vs 50 s. `[NUM]` `[PROVE]`
2.1.6 **Amdahl's law applied to a test suite**: if 30% of the wall-clock is a single serialised
      container startup, perfect parallelism of everything else caps the speedup at 3.3×. Measure the
      serial fraction before buying CI cores. `[PROVE]` `[NUM]`
2.1.7 **Little's Law applied to CI**: with an arrival rate of 40 pipelines/hour and a 12-minute
      suite, you need ≥ 8 concurrent runners just to avoid a queue — the queue, not the suite, is
      often the developer-visible latency. `[PROVE]` `[NUM]` `[X-REF 22]`
2.1.8 **The feedback-latency budget** as a design target, stated as thresholds with the behaviour each
      produces: < 10 s (run on save), < 2 min (run before push), < 10 min (CI gate is tolerable),
      > 20 min (people batch changes and stop trusting the gate). `[TABLE]` `[NUM]`
2.1.9 **The cost of a flake, quantified**: at a 2% suite-level flake rate and 40 pipelines/day, that
      is ~0.8 spurious failures a day; at 15 minutes of a developer's attention each, ~50 hours a
      year per team. This is the number that funds flake work. `[NUM]` `[PROVE]`
2.1.10 The **confidence-per-second** metric as the honest optimisation target, and why it explains
      the trophy: an integration test that costs 40× a unit test but catches the SQL and mapping
      defects that actually escape can still win. `[PROVE]`
2.1.11 What is **not** worth optimising: assertion-library speed, mock creation, and anything measured
      in microseconds. Profile the suite before optimising it — the answer is almost always context
      count or container count. `[TRAP]`
2.1.12 How to actually measure it: Surefire/Gradle timing reports, Gradle build scans, JUnit
      Platform's JFR events (now in `junit-platform-launcher`), and the Spring
      `spring.test.context.cache` statistics logged at DEBUG. `[CLI]` `[DIAG]` `[METRIC]`

## §2.2 Determinism I — time, randomness, identity, locale

2.2.1 The general diagnosis, preserved and generalised from the current guide: **untestable code is
      usually code that reaches out to a global.** `Instant.now()`, `new Random()`,
      `UUID.randomUUID()`, `System.getenv`, `System.currentTimeMillis`, `LocalDate.now()`,
      `InetAddress.getLocalHost()`, the default locale, the default timezone, the file system, the
      network. `[TABLE]` `[PROVE]`
2.2.2 The general fix: **inject it**, so the global becomes a constructor parameter. Every leaf below
      is an instance of that one move. `[PROVE]`
2.2.3 **`java.time.Clock`** — the current guide's example preserved and re-domained to
      `AccountMaintenance` deciding whether an agreement acceptance has expired, with
      `Clock.systemUTC()` in production and `Clock.fixed(Instant.parse("2026-03-01T00:00:00Z"),
      ZoneOffset.UTC)` in the test. `[BUILD]` `[API]`
2.2.4 The point that `Clock` exists in `java.time` **precisely for this**, and the payoff preserved
      verbatim: you can test the leap-year, month-end, and DST cases that are otherwise unreachable.
      `[X-REF 03]`
2.2.5 The `Clock` factory surface, all of it: `systemUTC`, `systemDefaultZone`, `system(zone)`,
      `fixed`, `offset`, `tick`, `tickSeconds`, `tickMinutes`. `[API]`
2.2.6 **A mutable test clock** as the thing `Clock.fixed` cannot do — a `MutableClock extends Clock`
      you can advance by a `Duration` — needed to test "the deposit limit window rolled over".
      `[BUILD]`
2.2.7 **`Clock` vs mocking `Instant.now()`** — mocking a static is available (§ 2.10) and is the wrong
      answer: it is global, it hides the dependency, and it does not survive a refactor. Inject.
      `[TRAP]` `[PROVE]`
2.2.8 **The `Thread.sleep`-to-move-the-clock trap**, preserved verbatim from the current guide: it is
      slow and still racy. `[TRAP]`
2.2.9 **Randomness**: inject a `Random` with a fixed seed, or a `RandomGenerator` (Java 17+), so a
      failure is reproducible. The seed goes in the failure output. `[API]` `[X-REF 04]`
2.2.10 **Identity generation**: a `Supplier<UUID>` or an `IdGenerator` interface, so a `LedgerEntry`
      id is predictable and the assertion can name it. `[API]`
2.2.11 The alternative when injection is impractical: assert on the *shape* rather than the value —
      `assertThat(id).isNotNull()` plus a recursive comparison that ignores `id`. Weaker, but honest.
2.2.12 **Locale** as a hidden global: `String.format`, `toUpperCase()`, `DecimalFormat` and
      `Collator` all read the default locale, so a decimal comma turns a passing money test red on a
      German developer's laptop. `[TRAP]` `[PROVE]`
2.2.13 **Timezone** as the bigger one: `LocalDate.now()` under `Australia/Sydney` is tomorrow's date
      relative to UTC, so a "today's deposits" query fails for eight hours a day in one region.
      `[TRAP]` `[NUM]`
2.2.14 The two fixes and the preference order: **pin it in the build** (§ 1.12.14) for the whole
      suite, and additionally use `@DefaultLocale`/`@DefaultTimeZone` (JUnit 6.1) for the tests that
      deliberately vary it. `[CFG]` `[API]` `[RESEARCH]` `[VERSION-TRAP]`
2.2.15 JUnit 6.1's **system-property management extension** as the sanctioned replacement for the
      `System.setProperty`-in-`@BeforeEach`-and-forget-to-restore pattern. `[API]` `[RESEARCH]`
2.2.16 **File-system and working-directory assumptions**: `@TempDir` (with its `cleanup`/`factory`
      attributes) as the correct tool, and the trap of a test that writes to `target/` and passes only
      on the second run. `[API]` `[TRAP]`
2.2.17 **`@TempDir` on a static field vs an instance field** — per-class vs per-test directory, and the
      Windows file-locking failure that makes cleanup fail. `[TRAP]` `[RESEARCH]`
2.2.18 **Hostname, network interfaces and DNS** as globals a test must not touch, and the CI symptom:
      passes locally, fails in a container with no `/etc/hosts` entry. `[X-REF 10]`
2.2.19 **The "determinism audit"** as a reviewable procedure: grep the module for `now()`, `random`,
      `UUID.`, `getenv`, `getProperty`, `sleep`, and `Locale.getDefault`, and justify each hit.
      `[CLI]` `[FLOW]`
2.2.20 The scenario case that makes all of this concrete: the **daily deposit limit** resets at
      midnight in the client's jurisdiction, against 95k card deposits/day. Every boundary of that
      rule is untestable without an injected clock and a pinned timezone, and it is exactly the rule
      whose failure is a regulatory finding. `[NUM]` `[PROVE]`

## §2.3 Determinism II — asynchrony and concurrency

2.3.1 The taxonomy of async boundaries you might be testing, because the right technique differs for
      each: `@Async`/`TaskExecutor`, `CompletableFuture`, a message consumer, a scheduled job, a
      transaction-synchronisation callback, a reactive pipeline, and a virtual-thread task.
      `[TABLE]` `[X-REF 05]`
2.3.2 The first move, and the one people skip: **make the boundary injectable and remove it in the
      test.** Inject a `TaskExecutor` and bind `SyncTaskExecutor` in tests so the whole flow becomes
      synchronous and deterministic. Preserve the current guide's advice verbatim. `[PROVE]`
2.3.3 The corollary preserved verbatim: **test the asynchrony itself once, separately**, rather than
      in every test that happens to cross it. `[PROVE]`
2.3.4 **Awaitility** — the current guide's `await().atMost(…).pollInterval(…).untilAsserted(…)` example
      preserved and re-domained to a settlement reaching `SETTLED`, plus the reason it beats a sleep:
      fast when the work finishes quickly, and it fails with the *assertion's* message rather than a
      bare timeout. `[BUILD]` `[API]`
2.3.5 The Awaitility surface: `await()`, `atMost`, `atLeast`, `pollInterval`, `pollDelay`,
      `pollInSameThread`, `until(Callable<Boolean>)`, `untilAsserted`, `untilAtomic`,
      `ignoreExceptions`, `alias`, `with().conditionEvaluationListener(…)`, and
      `Awaitility.setDefaultTimeout`. `[TABLE]` `[API]`
2.3.6 **`untilAsserted` vs `until`** — the first reports *why* the state was wrong, the second reports
      only that it never became true. Prefer `untilAsserted`. `[PROVE]` `[DIAG]`
2.3.7 **`pollDelay` defaults to the poll interval**, which means a naive `await()` waits before its
      first check — a small but real fixed cost multiplied across a suite.
      `pollDelay(Duration.ZERO)` fixes it. `[NUM]` `[TRAP]` `[RESEARCH]`
2.3.8 **Awaitility's timeout is not a performance assertion.** `atMost(5, SECONDS)` passing does not
      mean the operation takes under 5 seconds; a test that asserts on latency is a benchmark
      (§ 2.20) and belongs elsewhere. `[TRAP]`
2.3.9 **`Thread.sleep` in a test**, given the full treatment it deserves: always slow, still flaky on
      a loaded CI box, and it encodes an assumption about machine speed that CI will violate. There
      is no case where `sleep` is the best available tool — enumerate the alternative for each
      situation. `[TRAP]` `[TABLE]` `[PROVE]`
2.3.10 **`CountDownLatch` / `CyclicBarrier` / `Phaser` / `SynchronousQueue`** as the deterministic
      alternatives when you control the code, and the pattern: the production code signals, the test
      awaits with a timeout. `[API]` `[X-REF 05]`
2.3.11 **`CompletableFuture` in tests**: `join()` with a timeout via `orTimeout`/`get(timeout, unit)`,
      never a bare `get()` — a bare `get()` turns a bug into a hung build. `[TRAP]` `[X-REF 05]`
2.3.12 **`ExecutorService` shutdown assertions**: `awaitTermination` with a bounded timeout, and the
      leak symptom — a test JVM that will not exit and a CI job that times out at 60 minutes.
      `[DIAG]` `[TRAP]`
2.3.13 **Spring's `@Async` in tests**: it needs a proxy, so a self-invoked `@Async` method runs
      synchronously and the test silently passes for the wrong reason. One paragraph, then point to
      the proxy model. `[TRAP]` `[X-REF 07]`
2.3.14 **`TransactionSynchronizationManager` / `@TransactionalEventListener(AFTER_COMMIT)`** as the
      async boundary that never fires in a rolled-back test — a specific, common, and very confusing
      false negative. `[TRAP]` `[X-REF 08]`
2.3.15 **Message consumers**: the assertion target is the *effect*, not the delivery — poll the
      repository with Awaitility, or use a `CountDownLatch` injected into the listener. `[X-REF 14]`
2.3.16 **`@EmbeddedKafka` vs a Kafka Testcontainer** — the trade-off table: startup cost, fidelity of
      rebalancing behaviour, and whether your broker version matches production. `[TABLE]`
      `[X-REF 14]`
2.3.17 **Reactive testing**: `StepVerifier` (`expectNext`, `expectComplete`, `expectError`,
      `thenAwait`, `withVirtualTime`) as the deterministic-by-construction option, and
      `VirtualTimeScheduler` as the reactive analogue of a fixed `Clock`. `[API]`
2.3.18 **Testing thread safety is different from testing async**, and the distinction matters: async
      is about *when*, thread safety is about *interleaving*. A passing concurrent test proves almost
      nothing about the second. `[PROVE]`
2.3.19 Why the naive "spawn 100 threads and assert the counter" test is weak: it explores a vanishing
      fraction of the interleaving space, and it passes on x86 while failing on ARM because the
      memory model differs. `[PROVE]` `[TRAP]` `[X-REF 05]`
2.3.20 **`@RepeatedTest(1000)` as a race detector is a bad tool** — it is a lottery, and a green run
      is not evidence. Say what is: a linearizability or interleaving checker. `[TRAP]`
2.3.21 **jcstress** (the OpenJDK Java Concurrency Stress harness) as the actual tool: it enumerates
      outcomes across enormous iteration counts under `@JCStressTest`, `@Outcome`, `@State`, and
      classifies results as `ACCEPTABLE` / `FORBIDDEN` / `ACCEPTABLE_INTERESTING`. This is what a
      memory-model claim is tested with. `[API]` `[RESEARCH]` `[X-REF 05]` `[X-REF 06]`
2.3.22 **Lincheck** as the modern alternative for linearizability checking of a data structure —
      named so the reader knows the option exists. `[RESEARCH]`
2.3.23 **`ThreadSafe`/`ErrorProne`/SpotBugs static analysis** as the cheap complement: a static
      checker finds unsynchronised access that no test will.
2.3.24 The honest conclusion for an interview: **you do not prove thread safety with tests, you argue
      it with the memory model and then use tests to find the cases your argument missed.** `[PROVE]`
      `[X-REF 05]`
2.3.25 The QuizStakes case that demands all of this: **invariant 8**, self-exclusion effective before
      the next stake, at 1,200 stake reservations/sec with a hard 500 ms budget. The bible must show
      the deterministic test (a latch-coordinated interleaving of self-exclude and reserve) and say
      explicitly what it does and does not prove. `[NUM]` `[PROVE]` `[BUILD]`

## §2.4 Test data — fixtures, builders, and object mothers

2.4.1 The problem stated: a `LedgerEntry` with fourteen required fields makes every test a
      construction exercise, and the construction noise hides the one field the test is about.
      `[PROVE]`
2.4.2 **The four strategies** compared on readability, coupling to the constructor, and what happens
      when a field is added: inline construction, a shared fixture object, an **Object Mother**
      (named factory methods), and a **Test Data Builder** (fluent, with defaults). `[TABLE]`
2.4.3 **Object Mother** — `LedgerEntries.settledStake()`, `Clients.selfExcluded()`. Cheap, very
      readable, and it degenerates into a class of forty near-identical methods. `[BUILD]`
2.4.4 **Test Data Builder** — `aLedgerEntry().withStake("100.00").settled().build()` — with sane
      defaults so a test names only what it cares about. The pattern that scales. `[BUILD]`
2.4.5 The two combined, which is what mature suites actually do: mothers returning **pre-configured
      builders**, so `Clients.selfExcluded().withCashAvailable("50.00").build()` reads as a sentence.
      `[BUILD]` `[PROVE]`
2.4.6 **The one-obvious-difference rule**: every value a test does not name should be a default, and
      every value it names should matter. If a test sets a field it does not assert on, ask why.
      `[PROVE]`
2.4.7 **Records as test data** (Java 21): a record's canonical constructor is positional and
      unforgiving, which is exactly when a builder earns its keep. `[X-REF 04]`
2.4.8 **Builders must produce valid objects by default**, or every test starts with a fix-up. Validity
      belongs in the builder's defaults, not in each test.
2.4.9 **Unique-per-test data** as the standing fix for the leaked-unique-key flake: derive an id or an
      email from the test's own name via `TestInfo`, not from a counter (which breaks under
      parallelism). `[PROVE]` `[TRAP]`
2.4.10 **Shared mutable fixture** as the smell, with its exact failure: the second test sees the first
      test's mutation and passes or fails depending on order (§ 2.17).
2.4.11 **Immutable shared fixture** as the legitimate exception — a parsed 900 KB agreement document
      loaded once in `@BeforeAll` and never mutated is a real optimisation. `[NUM]`
2.4.12 **`@TestInstance(PER_CLASS)` + an immutable fixture** as the sanctioned combination, and the
      review rule that makes it safe: the field must be `final` and its type immutable.
2.4.13 **Fixture-in-a-SQL-file** (`@Sql`) vs fixture-in-a-builder: the SQL file is faster and further
      from the code, the builder is slower and closer. Prefer the builder for behaviour, the SQL file
      for volume. `[TABLE]`
2.4.14 **The mystery-guest smell** named precisely: a test whose inputs live in an external file or a
      shared setup so the reader cannot see them. Every fixture strategy above has a version of this
      failure. `[TRAP]` `[SPEC]`
2.4.15 **Random test data (Instancio, EasyRandom, `@Fuzz`)** — the honest assessment: it eliminates
      construction noise and introduces non-determinism and unreadable failures. Acceptable for
      *irrelevant* fields, never for the field under test, and only with a logged seed. `[TRAP]`
      `[PROVE]`
2.4.16 **The QuizStakes canonical fixture set** the bible should define once and reuse: a
      `Client` at `AO-400` with cash available `500.00`; a self-excluded client; a client with an
      outstanding `DocumentRequirements` item; the current `ClientAgreements` version and the
      superseded one; a reserved-but-unsettled stake. Six fixtures cover most of the suite.
      `[TABLE]` `[BUILD]`

## §2.5 Database testing — schema, cleanup, and what to assert

2.5.1 What a database test is actually for, enumerated so the tests can be aimed: **the SQL is valid
      and does what you think**, the mapping round-trips, the constraints fire, the transaction
      boundary is where you think it is, the index is used, and the migration applies. `[TABLE]`
      `[PROVE]`
2.5.2 **H2 vs a real database** — the current guide's § 8 preserved in full, because it is one of its
      strongest passages: H2 "also **lies**", with a different SQL dialect, different type coercion,
      no native `JSONB`/arrays/`ON CONFLICT` nuances, different locking and isolation behaviour, no
      real query planner, and different constraint error messages. Tests pass; production fails on
      the exact query you thought you had tested. `[TRAP]` `[PROVE]`
2.5.3 Each of those divergences given a concrete failure: an `ON CONFLICT DO UPDATE` upsert for the
      idempotent settlement, a `JSONB` column on `ApplicationHistory`, `SELECT … FOR UPDATE SKIP
      LOCKED` on the outbox, a `citext` email column, a window function in the balance derivation.
      `[TABLE]` `[X-REF 09]`
2.5.4 The concession the current guide already makes and that must survive: H2 is defensible only for
      tests that do not exercise real queries at all — and in that case, prefer not touching a
      database.
2.5.5 **The intermediate position nobody names**: `@DataJpaTest` on H2 for *mapping* tests, Postgres
      for *query* tests. Defensible, and it doubles your context count — say the cost. `[PROVE]`
2.5.6 **Schema management in tests**, the three options: Hibernate `ddl-auto: create-drop` (fast,
      **tests a schema you do not deploy**), the real migrations (slow, correct), and a
      pre-migrated container image (fast and correct, with a build step). `[TABLE]` `[PROVE]`
2.5.7 **`ddl-auto: create-drop` in tests is a false witness**, and this is the highest-value
      database-testing trap: your production schema comes from Flyway/Liquibase, so a test against a
      Hibernate-generated schema cannot catch a missing migration, a wrong column type, or a missing
      index. `[TRAP]` `[PROVE]`
2.5.8 **Flyway in tests**: `spring.flyway.enabled`, `spring.flyway.locations` with a test-only
      `db/testdata` location, `clean-disabled`, and out-of-order migrations. The recommended posture:
      **run the real migrations, add test data separately**. `[CFG]` `[FLOW]`
2.5.9 **Testing a migration itself** — the test nobody writes and everybody needs: apply migrations to
      a container seeded with *production-shaped* data and assert the result, because a migration
      that works on an empty table can lock a 19.8M-row table for minutes. `[NUM]` `[PROVE]`
      `[X-REF 09]`
2.5.10 **Liquibase contrasts**: changelog `contexts`/`labels` to include test-only data, and rollback
      testing as a first-class capability Flyway Community lacks. `[RESEARCH]`
2.5.11 **Cleanup strategy 1 — transactional rollback**: fast, automatic, and it changes the semantics
      of the thing you are testing (§ 2.9). `[TABLE]`
2.5.12 **Cleanup strategy 2 — truncate between tests**: `TRUNCATE … RESTART IDENTITY CASCADE` on the
      touched tables, driven by a `TestExecutionListener` or a JUnit extension. Slower, honest, and it
      lets you test commit behaviour. `[BUILD]` `[CLI]`
2.5.13 **Cleanup strategy 3 — drop and recreate the schema / restart the container**: correct and far
      too slow to do per test; the right granularity is per suite. `[NUM]`
2.5.14 **Cleanup strategy 4 — unique data per test, no cleanup**: no coordination, works under
      parallelism, and the table grows across the run. Excellent for read-heavy tests, useless when
      you assert on a count. `[PROVE]`
2.5.15 **Cleanup strategy 5 — a database template / snapshot restore**, and the Postgres mechanism
      (`CREATE DATABASE … TEMPLATE`) that makes it fast. The technique that scales best for large
      fixtures. `[RESEARCH]` `[X-REF 09]`
2.5.16 The **cleanup decision table**: speed, isolation strength, whether commit behaviour is
      testable, and whether it survives parallel execution. `[TABLE]`
2.5.17 **Asserting on the database, not through the ORM**: after saving via a repository, read back
      with `JdbcTemplate`/`JdbcClient` so the assertion sees what is actually in the column — the
      only way to catch a wrong `@Column` type or a lost timezone. `[PROVE]` `[BUILD]`
2.5.18 **`TestEntityManager`** — `persistAndFlush`, `flush`, `clear`, `find`, `getId` — and the current
      guide's point preserved: `@DataJpaTest` rolls back per test, so you **never see the flush**
      unless you force it. `[API]` `[X-REF 08]`
2.5.19 What that hides, itemised: constraint violations, `@PostPersist`/`@PreUpdate` callbacks,
      generated ids, dirty-checking behaviour, and optimistic-lock `@Version` increments. Each
      produces a green test and a production failure. `[TABLE]` `[TRAP]` `[X-REF 08]`
2.5.20 **Testing the N+1** — the assertion nobody writes: install a Hibernate statement inspector or
      `datasource-proxy`/`p6spy` and assert the **query count**, so the fix cannot silently regress.
      This is the single highest-value JPA test. `[BUILD]` `[PROVE]` `[X-REF 08]`
2.5.21 **Testing isolation-level behaviour** and pessimistic locking: two connections, one test, a
      latch — and the note that this is only possible on the real engine (§ 2.5.2). `[X-REF 09]`
2.5.22 **Testing an index is used** — capture `EXPLAIN` output in the test and assert on the plan node.
      Fragile across planner versions; worth it for the query on the 19.8M-row ledger. `[PROVE]`
      `[X-REF 09]`
2.5.23 The QuizStakes database test set derived: the stake-reservation upsert's idempotency, the
      derived-balance query against 180-byte rows, the `SKIP LOCKED` outbox claim, the
      `ApplicationHistory` JSONB round trip, and the unique constraint that makes double-settlement
      impossible. `[TABLE]`

## §2.6 Testcontainers

2.6.1 What it is mechanically, in one sentence: a Java library that starts throwaway Docker
      containers, waits for them to be ready, exposes their **mapped ports**, and cleans them up —
      turning "the real database" into a test dependency. `[PROVE]`
2.6.2 The current guide's example preserved, **corrected to Testcontainers 2.x**, and re-domained:
      `@Testcontainers` + `@Container static PostgreSQLContainer<?> db = new
      PostgreSQLContainer<>("postgres:16-alpine")` for `FundsLedgerRepositoryIT`. `[BUILD]`
2.6.3 **`@Testcontainers` + `@Container`** semantics: a **static** field is started once per class and
      stopped after; an **instance** field is started and stopped per test method. The current guide
      states the first correctly; the bible must state both and the cost difference. `[NUM]` `[PROVE]`
2.6.4 **The singleton-container pattern** — a `static` container in an abstract base class, started
      once per **JVM**, never stopped, cleaned up by Ryuk. The current guide alludes to it; the bible
      must show it, because it is what makes integration tests fast enough to be the default.
      `[BUILD]` `[PROVE]`
2.6.5 **`@DynamicPropertySource`** wiring, preserved from the current guide, with the reason it must be
      `static` and why the values are `Supplier`s. `[API]`
2.6.6 **`@ServiceConnection`** as the modern replacement: annotate the container bean and Boot derives
      `spring.datasource.*` (or the Kafka/Redis/Mongo equivalents) itself. Less code, and it works for
      containers whose property names you would have to look up. `[API]` `[PROVE]`
2.6.7 The `@ServiceConnection` mechanism in one paragraph: a `ContainerConnectionDetailsFactory` per
      supported container type contributes a `ConnectionDetails` bean that the auto-configuration
      prefers over properties. `[RESEARCH]` `[X-REF 07]`
2.6.8 **`@ImportTestcontainers`** and a `@TestConfiguration` holding `@Bean @ServiceConnection`
      containers — the pattern that shares one container definition across the whole suite while
      keeping the context cache key stable. `[BUILD]` `[PROVE]`
2.6.9 **Testcontainers at development time** — `SpringApplication.from(App::main).with(TestConfig.class)`
      to run the app locally against containers. Named because it converts test infrastructure into
      developer infrastructure. `[API]` `[RESEARCH]`
2.6.10 **The JDBC URL scheme** — `jdbc:tc:postgresql:16:///quizstakes` — which starts a container from
      the URL with no Java code at all, plus `TC_INITSCRIPT`, `TC_INITFUNCTION`, `TC_DAEMON`, and
      `TC_REUSABLE`. `[CFG]` `[API]`
2.6.11 **Wait strategies**, all of them, because "the container started" is not "the service is
      ready": `Wait.forListeningPort()`, `forHttp(path)` with `forStatusCode`, `forLogMessage(regex,
      times)`, `forHealthcheck()`, `forSuccessfulCommand()`, and `waitingFor` + `withStartupTimeout`.
      `[TABLE]` `[API]`
2.6.12 The failure this prevents: a port is listening before Postgres finishes recovery, so the first
      connection fails intermittently — a classic CI-only flake. `[TRAP]` `[DIAG]`
2.6.13 **Module containers** worth naming for a backend Java suite: `PostgreSQLContainer`,
      `MySQLContainer`, `KafkaContainer`, `GenericContainer` for Redis, `MongoDBContainer`,
      `ElasticsearchContainer`, `LocalStackContainer`, `MockServerContainer`,
      `MongoDBAtlasLocalContainer`, `ComposeContainer`, and `GenericContainer` as the escape hatch.
      `[TABLE]` `[RESEARCH]`
2.6.14 **`ComposeContainer`** (renamed from `DockerComposeContainer` in 2.0) for a multi-service
      topology, and the honest warning: a compose-based test is a small E2E and inherits its costs.
      `[VERSION-TRAP]` `[RESEARCH]`
2.6.15 **`Network` and container-to-container communication**: `withNetwork`, `withNetworkAliases`, and
      the crucial distinction that **inside the network you use the container port; from the JVM you
      use the mapped port**. Getting this wrong is the most common Testcontainers configuration bug.
      `[TRAP]` `[PROVE]` `[X-REF 19]`
2.6.16 **`withCopyFileToContainer` / `withFileSystemBind` / `withClasspathResourceMapping`** for
      seeding config, and why the first is preferred (bind mounts break in Docker-in-Docker).
      `[API]` `[TRAP]`
2.6.17 **Reusable containers** — the exact configuration, verified: `withReuse(true)` on the container
      **plus** opt-in via `TESTCONTAINERS_REUSE_ENABLE=true` or `testcontainers.reuse.enable=true` in
      `~/.testcontainers.properties`. The classpath properties file is explicitly **not** supported
      for this flag. `[CFG]` `[SOURCE]` `[RESEARCH]`
2.6.18 The reuse contract, quoted: "To reuse a container, the container configuration **must be the
      same**" — Testcontainers hashes the configuration, so changing any `with…` call produces a new
      container rather than reusing the old one. `[SOURCE]` `[PROVE]`
2.6.19 The reuse rules that make it work: you must call `start()` yourself and must **not** call
      `stop()` (so no try-with-resources), and the container is excluded from Ryuk's cleanup.
      `[SOURCE]` `[PROVE]`
2.6.20 The documented warnings, stated as warnings: reuse is **experimental**, is **not for CI**
      (containers persist after the run), and resource cleanup and networking features do not fully
      work. `[SOURCE]` `[TRAP]` `[CURRENCY]`
2.6.21 The failure mode that follows and is widely reported: **zombie containers** accumulating on a
      developer machine until Docker runs out of disk. The mitigation and the cleanup command.
      `[TRAP]` `[CLI]` `[RESEARCH]`
2.6.22 **Ryuk, the resource reaper** — a privileged sidecar container with the Docker socket that
      watches the JVM's TCP connection and deletes every **labelled** container, network and volume
      shortly after the JVM disconnects. This is what makes "throwaway" true even when the JVM is
      killed. `[PROVE]` `[RESEARCH]`
2.6.23 Disabling it: `ryuk.disabled=true` in `.testcontainers.properties` or
      `TESTCONTAINERS_RYUK_DISABLED=true` (the environment variable takes precedence). The legitimate
      reason is a CI platform that forbids privileged containers and cleans up itself. `[CFG]`
      `[SOURCE]` `[RESEARCH]`
2.6.24 **Testcontainers configuration surface**: `~/.testcontainers.properties`,
      `TESTCONTAINERS_HUB_IMAGE_NAME_PREFIX` for an internal registry mirror,
      `DOCKER_HOST`/`TESTCONTAINERS_DOCKER_SOCKET_OVERRIDE`, `checks.disable`, and
      `TESTCONTAINERS_HOST_OVERRIDE`. `[TABLE]` `[CFG]` `[RESEARCH]`
2.6.25 **Docker in CI**, the real constraint: it needs a daemon. The four options with their
      trade-offs — a Docker socket mounted into the build container, Docker-in-Docker (privileged),
      a remote daemon over TLS, and Testcontainers Cloud. `[TABLE]` `[X-REF 19]`
2.6.26 **Rootless Docker, Podman and Colima** as the common developer setups that need explicit
      socket configuration, and the "Could not find a valid Docker environment" error that results.
      `[DIAG]` `[TRAP]` `[RESEARCH]`
2.6.27 **Image pull as the hidden first-run cost** — a cold CI runner pulls `postgres:16-alpine`
      before it starts anything. Pin digests, mirror to an internal registry, and pre-pull in the
      runner image. `[NUM]` `[PROVE]` `[X-REF 19]`
2.6.28 **Pin the image tag, and prefer a digest.** `postgres:16-alpine` moves; `postgres:16.4-alpine`
      does not; `postgres@sha256:…` cannot. An unpinned image makes your suite non-reproducible in a
      way that surfaces as a mystery failure months later. `[TRAP]` `[PROVE]`
2.6.29 **The startup-cost budget**, measured: container create + start + wait strategy for Postgres
      ~1.5–3 s, Kafka ~5–10 s, LocalStack ~5–15 s, on a warm image. These numbers drive the singleton
      decision. `[NUM]` `[TABLE]` `[RESEARCH]`
2.6.30 **Testcontainers 2.0 as a breaking upgrade**, enumerated: every artifact renamed with a
      `testcontainers-` prefix, container classes moved into module-specific packages, **JUnit 4
      support removed**, **no parameterless container constructors**, `DockerComposeContainer` →
      `ComposeContainer`, `getContainerIpAddress()` → `getHost()`. A BOM bump alone will not compile.
      `[VERSION-TRAP]` `[TABLE]` `[RESEARCH]`
2.6.31 The migration path: the **OpenRewrite recipe** `org.openrewrite.java.testing.testcontainers.Testcontainers2Migration`,
      named because hand-editing imports across a large suite is not the right answer. `[CLI]`
      `[RESEARCH]`
2.6.32 The honest trade-off, preserved from the current guide: Testcontainers needs a Docker daemon in
      CI and adds seconds of startup; it is worth it for anything touching SQL.
2.6.33 **When Testcontainers is the wrong answer**: a pure-logic test, a test of a dependency you do
      not own the container for, and a CI environment where Docker genuinely is not available (in
      which case the honest response is to change the CI environment, not the tests). `[PROVE]`

## §2.7 Spring context caching — the economics and the mechanics

2.7.1 The claim to prove: **context caching is the single largest lever on Spring test suite
      duration**, and almost every slow Spring suite is slow for this one reason. `[PROVE]`
2.7.2 The mechanism in one sentence: the TestContext framework builds an `ApplicationContext` per
      distinct **`MergedContextConfiguration`** and keeps it in a static `ContextCache` for the whole
      JVM, so the second test with an identical configuration pays nothing. `[PROVE]`
2.7.3 **The cache key, enumerated exactly** — all ten attributes of `MergedContextConfiguration`, from
      the Spring reference: `locations`, `classes`, `contextInitializerClasses`, `contextCustomizers`,
      `contextLoader`, `parent`, `activeProfiles`, `propertySourceDescriptors`,
      `propertySourceProperties`, `resourceBasePath`. The current guide says "configuration key"
      without enumerating it; the bible must enumerate. `[TABLE]` `[SOURCE]` `[NUM]`
2.7.4 The fourth entry is the one that bites: **`contextCustomizers` includes `@DynamicPropertySource`
      methods, bean overrides (`@TestBean`, `@MockitoBean`, `@MockitoSpyBean`) and Spring Boot's own
      testing features.** That is the documented reason a mock bean changes the key. `[SOURCE]`
      `[PROVE]`
2.7.5 **The default cache size is 32, with LRU eviction**, configurable by the JVM system property
      **`spring.test.context.cache.maxSize`** or the `SpringProperties` mechanism. Quote the
      documentation. `[NUM]` `[CFG]` `[SOURCE]`
2.7.6 What eviction actually costs: an evicted context is **closed**, so the next test that needs it
      rebuilds it *and* the singletons' `@PreDestroy` runs — which can shut down a connection pool
      other tests were using if you cached one statically. `[PROVE]` `[TRAP]`
2.7.7 The consequence of 32 + LRU that nobody anticipates: a suite with **35 distinct configurations**
      thrashes the cache and can rebuild contexts it already built, so suite time becomes superlinear
      in configuration count. `[PROVE]` `[NUM]` `[TRAP]`
2.7.8 **The context-count audit** as an actionable procedure: enable `DEBUG` on
      `org.springframework.test.context.cache` and read the logged hit/miss/size statistics after a
      run. The number of misses is the number of contexts you built. `[CLI]` `[DIAG]` `[METRIC]`
2.7.9 **Everything that forks a context**, enumerated as a checklist to review a suite against:
      a different slice annotation, a different `classes`, `@MockitoBean` on a different type or set,
      `@MockitoSpyBean`, `@TestBean`, `@TestPropertySource`, `@SpringBootTest(properties=)`,
      `@ActiveProfiles`, `@ContextConfiguration(initializers=)`, `@DynamicPropertySource`,
      `@AutoConfigureTestDatabase(replace=…)`, `@WebAppConfiguration`'s base path, and
      `@DirtiesContext` (which destroys rather than forks). `[TABLE]` `[PROVE]`
2.7.10 **The fix, stated as policy**: standardise the test configuration. One base class per *tier*
      (`AbstractIntegrationTest`, `AbstractWebSliceTest`), with the mock-bean set and the properties
      declared **on the base class**, so every subclass shares one key. `[BUILD]` `[PROVE]`
2.7.11 The corollary that people resist: **it is often cheaper to mock a bean everywhere than to mock
      it in half the classes.** A uniform superset of mock beans shares one context; two different
      subsets need two. `[PROVE]` `[TRAP]`
2.7.12 The stronger fix: **push the test down**. A test that needs a bespoke mock set usually does not
      need a Spring context at all — it needs plain Mockito and a constructor. Preserve the current
      guide's advice. `[PROVE]`
2.7.13 **`@DirtiesContext` is not a cleanup tool**, it is a cache invalidation. Every use costs the
      rebuild for the next consumer, and a class-level `AFTER_EACH_TEST_METHOD` on a
      `@SpringBootTest` is a suite-killing line. `[TRAP]` `[NUM]`
2.7.14 The legitimate uses of `@DirtiesContext`, so the reader is not left with "never": a test that
      mutates a singleton's state irreversibly, a test that closes a resource in the context, and a
      test of the context's own startup.
2.7.15 **Boot 4 / Framework 7 context pausing** — the mechanism verified from the release notes:
      cached contexts that are not in use have their `Lifecycle`/`SmartLifecycle` beans **stopped**
      and restarted on reuse, with `SmartLifecycle#isPauseable()` returning `false` to opt out and a
      `ContextPausedEvent` published. `[VERSION-TRAP]` `[RESEARCH]` `[API]`
2.7.16 Why that matters practically: it reclaims connection pools and thread pools from idle cached
      contexts, which is what let large suites raise the cache size without exhausting file
      descriptors — and it introduces a new failure class for beans that assume they are never
      stopped. `[PROVE]` `[TRAP]`
2.7.17 **`@ContextHierarchy`** and `parent` in the cache key — rare, but the reason a hierarchy test's
      contexts multiply. `[API]`
2.7.18 **`@Nested` test classes inherit the configuration**, which is a free way to share a context
      across many scenarios — and `@NestedTestConfiguration` controls whether that inheritance
      happens. `[API]` `[RESEARCH]`
2.7.19 **AOT / native-image test support**: `spring-boot-maven-plugin`'s `process-test-aot`, and the
      constraint it imposes — the set of contexts must be knowable ahead of time, so
      `@DynamicPropertySource` and dynamic customizers are hostile to it. `[RESEARCH]`
2.7.20 The QuizStakes arithmetic worked end to end: 18 integration test classes, currently 11 distinct
      configurations at 3.8 s each = 41.8 s of context building; consolidated to 2 configurations =
      7.6 s. Same tests, **34 seconds returned per pipeline**, 40 pipelines/day. `[NUM]` `[PROVE]`

## §2.8 MockMvc, WebTestClient, RestTestClient, RestAssured — testing the web layer

2.8.1 The four options placed on one axis — **does a real server start, and does a real socket
      carry the request?** `MockMvc` (no server, no socket), `WebTestClient` bound to a controller (no
      server), `WebTestClient`/`RestTestClient` against a running server, and RestAssured (always a
      real socket). `[TABLE]` `[PROVE]`
2.8.2 **What `MockMvc` actually is**: the real `DispatcherServlet` handling a `MockHttpServletRequest`
      in-process. So it exercises mapping, argument resolution, validation, content negotiation,
      `@ControllerAdvice` and filters — **and does not exercise** the servlet container, HTTP
      parsing, connection handling, or anything about the wire. `[PROVE]` `[TABLE]`
2.8.3 The consequence, which is the point of the whole section: a `MockMvc` test cannot catch a
      container-level misconfiguration (max header size, path encoding, HTTP/2 behaviour), and a test
      that needs to is not a `MockMvc` test. `[PROVE]` `[TRAP]`
2.8.4 The `MockMvc` API surface: `perform`, `MockMvcRequestBuilders` (`get`/`post`/`multipart`,
      `contentType`, `content`, `header`, `param`, `with`), `andExpect`, `andExpectAll`, `andDo`,
      `andReturn`, and `MockMvcResultMatchers` (`status()`, `content()`, `jsonPath()`, `header()`,
      `cookie()`, `redirectedUrl()`, `view()`, `model()`). `[TABLE]` `[API]`
2.8.5 **`MockMvcResultHandlers.print()`** as the debugging move that resolves most "why is this a
      400" questions in one line, and `alwaysDo(print())` on the builder. `[CLI]` `[DIAG]`
2.8.6 **`MockMvcTester`** — the AssertJ-native surface, auto-configured when AssertJ is present:
      `assertThat(mvc.get().uri("/clients/{id}/agreements", id)).hasStatusOk().bodyJson()…`. Better
      failure messages, and it composes with `SoftAssertions`. `[API]` `[VERSION-TRAP]` `[RESEARCH]`
2.8.7 The current guide's `@WebMvcTest` 404 example preserved and re-domained: `AccountOpening`
      throwing `NotFoundException`, asserting `status().isNotFound()` and
      `jsonPath("$.title").value("Not Found")` against the Problem Details contract. `[BUILD]`
      `[X-REF 12]`
2.8.8 **`standaloneSetup` vs `webAppContextSetup`** — `MockMvcBuilders.standaloneSetup(controller)`
      needs no Spring context at all and is therefore very fast, at the cost of not testing your
      actual MVC configuration. The right tool for a validation-annotation test. `[API]` `[PROVE]`
2.8.9 **`WebTestClient`** — reactive, fluent, works both bound-to-a-context and against a live port,
      with `expectStatus`, `expectHeader`, `expectBody(Class)`, `expectBodyList`, `jsonPath`,
      `consumeWith`, and `returnResult`. `[API]`
2.8.10 **`RestTestClient`** (Boot 4) as the replacement for `TestRestTemplate`, requiring
      `@AutoConfigureRestTestClient`, with a fluent API that works against both MockMvc and a live
      server. `[VERSION-TRAP]` `[API]` `[RESEARCH]`
2.8.11 **`TestRestTemplate`** for what it still is in Boot 3.x — a `RestTemplate` that does not throw
      on 4xx/5xx, so you can assert on the status — and the fact that it is now deprecated and needs
      `@AutoConfigureTestRestTemplate` in Boot 4. `[VERSION-TRAP]` `[API]`
2.8.12 **RestAssured** — `given().…when().get(…).then().statusCode(…).body("…", equalTo(…))` — and
      where it earns its place: testing a *deployed* service from outside, where you have no Spring
      context at all. Its Hamcrest-based body assertions and its JSON-path dialect differences from
      Spring's. `[API]` `[TABLE]`
2.8.13 **The selection rule**: `MockMvc`/`MockMvcTester` for controller behaviour (fast, in-process);
      `RestTestClient`/`WebTestClient` on `RANDOM_PORT` for the one test that must cross a socket;
      RestAssured for black-box tests of a running deployment. `[FLOW]` `[TABLE]`
2.8.14 **Testing validation**: `@Valid` + a `MethodArgumentNotValidException` mapped by
      `@ControllerAdvice`, asserted as a 400 with a field-error body. The parameterized boundary table
      belongs here (§ 1.9). `[BUILD]` `[X-REF 12]`
2.8.15 **Testing error contracts**: one test per documented error shape, asserting the
      `application/problem+json` body — because the error contract is the part of an API that gets
      broken silently. `[PROVE]` `[X-REF 12]`
2.8.16 **Testing security in the web slice**: `@WithMockUser`, `csrf()`, and the current guide's
      `addFilters = false` warning. A controller test with filters disabled cannot catch a missing
      `@PreAuthorize`. `[TRAP]` `[X-REF 13]`
2.8.17 **Testing content negotiation and serialization together** vs separating them into `@JsonTest`:
      the slice test proves the endpoint returns the right shape, the JSON test proves the mapper is
      configured — and only the second one is fast enough to run per field.
2.8.18 **Async controller testing**: `asyncDispatch(mvcResult)`, `MvcResult.getAsyncResult()`, and
      testing an SSE/streaming endpoint. `[API]` `[RESEARCH]`
2.8.19 **File upload** testing with `multipart()` and `MockMultipartFile` — needed because
      `DocumentVerification` accepts 2–6 MB uploads and the size limit is part of the contract.
      `[NUM]` `[API]`
2.8.20 The trap that closes the section: **a green `MockMvc` suite plus a green service-layer suite
      does not prove the endpoint works**, because nothing tested the two together with real
      serialization and a real transaction. That gap is what the one integration test is for.
      `[TRAP]` `[PROVE]`

## §2.9 `@Transactional` in tests — the convenience and what it hides

2.9.1 The mechanism, precisely: `TransactionalTestExecutionListener` starts a transaction before the
      test method and **rolls it back afterwards by default**. It is a *test-managed* transaction,
      distinct from Spring-managed and application-managed ones. `[SOURCE]` `[PROVE]`
2.9.2 What that buys: no cleanup code, perfect isolation between tests, and no ordering dependence —
      which is why `@DataJpaTest` turns it on for you.
2.9.3 **`@Rollback` / `@Commit`** and their class-level and method-level interaction, plus the
      `TestTransaction` API (`flagForCommit`, `end`, `start`, `isActive`) for a test that needs to
      commit mid-way. `[API]` `[SOURCE]`
2.9.4 **`@BeforeTransaction` / `@AfterTransaction`** — code that runs *outside* the test transaction,
      which is the only place you can verify pre-test and post-rollback database state. In Jupiter
      these methods can take injected parameters. `[API]` `[SOURCE]`
2.9.5 **Which `@Transactional` attributes are actually honoured on a test**, from the reference, as a
      table: `value`/`transactionManager` **yes**; `propagation` only `NOT_SUPPORTED` and `NEVER`;
      `isolation` **no**; `timeout` **no**; `readOnly` **no**; `rollbackFor`/`noRollbackFor` **no**
      (use `TestTransaction`). Most people assume all of them work. `[TABLE]` `[SOURCE]` `[TRAP]`
2.9.6 **`@Transactional` is not supported on `@BeforeAll`/`@AfterAll`**, while `@BeforeEach`/`@AfterEach`
      run *inside* the test transaction. `[SOURCE]` `[TRAP]`
2.9.7 **Hidden thing 1 — the flush never happens.** The current guide states this; the bible must
      prove it: without a flush, the persistence context holds the entity, so no SQL is issued, so no
      constraint is checked. Hence `TestEntityManager.flush()`/`clear()`. `[PROVE]` `[TRAP]`
      `[X-REF 08]`
2.9.8 The documented false positive, quoted: a test that updates an entity in the session **passes
      without throwing** because the exception would only arise at flush time in production. This is
      the exact shape of the bug. `[SOURCE]` `[DIAG]`
2.9.9 **Hidden thing 2 — lifecycle callbacks do not fire.** `@PostPersist`, `@PostUpdate`, `@PostLoad`
      require a flush/clear, so a test can assert on state a production run would never see.
      `[SOURCE]` `[TRAP]`
2.9.10 **Hidden thing 3 — the first-level cache answers your assertion.** A read-back after a save
      returns the *same instance* from the persistence context, so the assertion proves nothing about
      the column mapping. `clear()` then re-find, or read with `JdbcClient`. `[PROVE]` `[TRAP]`
      `[X-REF 08]`
2.9.11 **Hidden thing 4 — `@TransactionalEventListener(AFTER_COMMIT)` never fires** because there is
      no commit. Every outbox and post-commit notification path is silently untested. `[TRAP]`
      `[X-REF 14]`
2.9.12 **Hidden thing 5 — propagation and rollback semantics are different.** A `REQUIRES_NEW` inner
      transaction behaves differently inside a test transaction, so a test of "the audit row survives
      the rollback" can pass or fail for reasons unrelated to the code. `[TRAP]` `[X-REF 08]`
2.9.13 **Hidden thing 6 — concurrency is impossible.** Two threads cannot see the test transaction's
      uncommitted data, so a locking or isolation test *must* commit. `[PROVE]`
2.9.14 **Hidden thing 7 — `RANDOM_PORT`/`DEFINED_PORT` tests do not roll back**, because the server
      handles the request on a different thread with its own transaction. The documentation says so
      explicitly, and it is the most surprising item on the list: your `@Transactional
      @SpringBootTest(webEnvironment=RANDOM_PORT)` test **commits**. `[SOURCE]` `[TRAP]` `[PROVE]`
2.9.15 **Hidden thing 8 — `assertTimeoutPreemptively` breaks it.** The test body runs on another
      thread, so the test-managed transaction does not apply and **changes commit despite the
      expected rollback**. Quoted from the reference. `[SOURCE]` `[TRAP]`
2.9.16 The decision, stated as a rule: **`@Transactional` for tests about mapping and queries;
      committed transactions with explicit truncation for tests about transactional behaviour,
      locking, events and concurrency.** Say which kind each test is. `[FLOW]` `[PROVE]`
2.9.17 The QuizStakes application: the derived-balance query is a rollback test; the
      **stake-reservation-then-settlement outbox flow is not**, because the whole point is what
      happens after commit. `[PROVE]`
2.9.18 **`@Sql` scripts run outside or inside the transaction** depending on `executionPhase` and
      `SqlConfig.transactionMode` — the detail that explains "my `@Sql` data disappeared". `[API]`
      `[TRAP]` `[RESEARCH]`

## §2.10 Mockito — the intermediate and advanced surface

2.10.1 **`MockedStatic`** — `try (var mocked = mockStatic(Instant.class)) { … }` — with the mandatory
      try-with-resources and the reason it is mandatory: the mock is registered **for the current
      thread** and leaks into every later test in that thread if not closed. `[API]` `[PROVE]`
      `[TRAP]`
2.10.2 The thread-scoping consequence: a static mock does **not** apply to code running on another
      thread, so a static mock plus an async boundary silently does nothing. `[TRAP]` `[PROVE]`
2.10.3 **`MockedConstruction`** — `mockConstruction(HttpClient.class, (mock, ctx) -> …)` — intercepting
      `new`, with the same scoping rules, and the honest verdict: it is a tool for legacy code with no
      seam, not a design choice. `[API]` `[TRAP]`
2.10.4 **Why mocking statics is a smell rather than a feature**: the dependency is invisible in the
      signature, the mock is global, and it defeats the constructor-injection habit that makes the
      rest of the suite fast. Reach for it when refactoring is genuinely blocked, and record why.
      `[PROVE]` `[TRAP]`
2.10.5 **`mockStatic` cannot mock `java.*` package-visible or native methods** — and cannot mock
      `System.exit` usefully. State the boundary. `[SOURCE]` `[RESEARCH]`
2.10.6 **`Answer` in anger**: `doAnswer(inv -> { var e = inv.getArgument(0, LedgerEntry.class); … })`
      for the case where the return depends on the input, plus `AdditionalAnswers.returnsFirstArg()`,
      `answersWithDelay`, `answerVoid`, and `delegatesTo`. `[API]`
2.10.7 **`AdditionalMatchers`** — `and`, `or`, `not`, `gt`, `lt`, `geq`, `leq`, `cmpEq`,
      `aryEq` — the half of the matcher surface nobody knows exists. `[API]`
2.10.8 **`ArgumentMatcher` + `argThat`** with a named implementation class, so the failure message
      says something. A lambda `argThat` produces a message you cannot act on. `[TRAP]` `[DIAG]`
2.10.9 **`ArgumentCaptor` vs `argThat` decided by failure message quality**, extending the current
      guide's rule with the actual messages each produces. `[DIAG]` `[TABLE]`
2.10.10 **`MockSettings`** via `withSettings()`: `name`, `defaultAnswer`, `extraInterfaces`,
      `serializable`, `verboseLogging`, `invocationListeners`, `strictness`, `stubOnly`. `[API]`
      `[TABLE]`
2.10.11 **`verboseLogging()` and `invocationListeners`** as the diagnostic for "the stub is not
      matching" — it prints every invocation and what it matched. This is the tool that ends
      guesswork. `[CLI]` `[DIAG]`
2.10.12 **`MockitoSession`** — `Mockito.mockitoSession().initMocks(this).strictness(…).startMocking()`
      — which is what `MockitoExtension` uses internally, and the manual API for a non-JUnit context.
      `[API]`
2.10.13 **`mockito-junit-jupiter`** as a separate artifact from `mockito-core`, and the classic
      "MockitoExtension not found" caused by omitting it. `[TRAP]` `[DIAG]`
2.10.14 **`@Mock` as a test-method parameter** — `void test(@Mock ScreeningClient client)` — which
      scopes the mock to one test and removes a field. Underused and strictly better where it
      applies. `[API]`
2.10.15 **Mocking a `final` class or a `record`**: works out of the box since Mockito 5 because the
      inline mock maker is the default; needed `mockito-inline` before that. This is the single most
      commonly stale Mockito fact. `[VERSION-TRAP]` `[PROVE]` `[RESEARCH]`
2.10.16 **The mock-maker choice is configuration, not code**:
      `src/test/resources/mockito-extensions/org.mockito.plugins.MockMaker` containing
      `mock-maker-inline` or `mock-maker-subclass`. Naming the file path is the checkable form of the
      answer. `[CFG]` `[API]` `[RESEARCH]`
2.10.17 **The self-attaching-agent warning**: Mockito attaches its Byte Buddy agent dynamically, and
      recent JDKs warn that dynamic agent loading will be disallowed; the fix is
      `-javaagent:…/byte-buddy-agent.jar` in `argLine`. This will become a hard failure, so it belongs
      in a 2026 answer. `[VERSION-TRAP]` `[CFG]` `[DIAG]` `[RESEARCH]`
2.10.18 **`mockito-inline` is obsolete as a dependency** and having it *and* Mockito 5 can produce
      confusing double-registration. `[VERSION-TRAP]` `[TRAP]`
2.10.19 **Mockito with virtual threads** — the inline mock maker's per-thread state and what that
      implies for a test that mocks statics inside a virtual-thread task. Flag as unverified.
      `[RESEARCH]` `[X-REF 04]`
2.10.20 **Kotlin object/singleton stubbing** support added in Mockito 5.22 — named for polyglot
      codebases. `[RESEARCH]` `[CURRENCY]`
2.10.21 **`BDDMockito`** — `given(…).willReturn(…)`, `then(mock).should()` — for suites that want
      given/when/then vocabulary end to end. `[API]`
2.10.22 **`Mockito.framework().addListener(…)`** and `MockitoFramework` for building suite-wide
      policy (e.g. failing a build on any use of `RETURNS_DEEP_STUBS`). `[API]` `[RESEARCH]`
2.10.23 **Mockito's alternatives**, so the reader can place it: EasyMock (record/replay), JMockit
      (agent-based, can mock anything, unmaintained-ish), PowerMock (the pre-Mockito-2 way to mock
      statics — now legacy and a red flag on a CV), Spock's built-in mocks, and MockK for Kotlin.
      `[TABLE]` `[RESEARCH]`
2.10.24 **PowerMock as a signal**: its presence usually means untestable static-heavy legacy code and
      a locked-in old Mockito. The migration is to Mockito 5's inline mock maker. `[VERSION-TRAP]`
2.10.25 **`Mockito.verify` with a timeout** (`verify(mock, timeout(1000)).send(…)`) as the
      Mockito-native way to verify an asynchronous interaction — and why Awaitility on the *effect*
      is usually better than a timeout on the *call*. `[PROVE]` `[TRAP]`
2.10.26 **`stubOnly()`** as a memory optimisation for mocks that receive millions of calls — named for
      completeness, because it is the answer to "my test JVM OOMs when I mock a hot path".
      `[RESEARCH]`

## §2.11 Mocking policy — the decisions that make a suite maintainable

2.11.1 The policy stated as a single rule to write on a whiteboard: **mock a boundary, never a
      neighbour.** A boundary is a process, a network, a clock, or a vendor; a neighbour is a class in
      the same module that you could just construct. `[PROVE]`
2.11.2 The **hexagonal/ports-and-adapters framing** that makes the rule mechanical: mock at the ports,
      run the domain for real. If your architecture has no ports, mocking decisions are arbitrary and
      that is the actual problem. `[PROVE]` `[X-REF 22]`
2.11.3 **The wrap-the-vendor pattern**, with the code: a `ScreeningClient` interface you own, a
      `VendorScreeningClient implements ScreeningClient` adapter, unit tests mocking the interface,
      and **one integration test of the adapter against a stub server**. `[BUILD]` `[PROVE]`
2.11.4 Why that split is not bureaucracy: it puts the "does the vendor's JSON parse" risk in exactly
      one test, and the "does our logic branch correctly" risk in fast tests. `[PROVE]`
2.11.5 **The mock-count heuristic**: more than three mocks in a test usually means the SUT has too
      many collaborators, which is a design finding, not a test finding. `[NUM]` `[TRAP]`
2.11.6 **The stub-return-shape heuristic**: if a stub must return an object graph three levels deep,
      the SUT is reaching through objects (§ 1.10.31). `[TRAP]`
2.11.7 **When a fake beats a mock**, argued with the current guide's example: an in-memory repository
      gives you reads-see-writes, no stubbing noise, and one implementation reused across the module.
      `[PROVE]`
2.11.8 **The fake's contract test** — the technique that stops fake drift: one abstract test class of
      repository behaviour, run against both the fake and the real Testcontainers-backed
      implementation. `[BUILD]` `[PROVE]`
2.11.9 **Don't mock the framework.** Mocking `EntityManager`, `JdbcTemplate`, `RestTemplate` or
      `KafkaTemplate` tests your understanding of their API rather than your code. Use the real thing
      against a container or a stub server. `[TRAP]` `[PROVE]`
2.11.10 **Don't mock what the type system already guarantees.** A mocked mapper, a mocked
      `record` accessor, or a mocked `Comparator` adds a failure mode and removes a check. `[TRAP]`
2.11.11 **Mocking `Clock` vs injecting a fixed `Clock`** — the second is strictly better: cheaper,
      more readable, and it cannot be mis-stubbed. A concrete instance beats a double whenever one
      exists. `[PROVE]`
2.11.12 **The general form of that rule**: prefer a real object → a fake → a stub → a mock, in that
      order, and only move down the list when the one above is impractical. `[FLOW]` `[PROVE]`
2.11.13 **Verification policy**, extending the current guide: `verify` only for side effects with no
      observable trace; never `verify` something an assertion already covers; never
      `verifyNoMoreInteractions` by default; `never()` is legitimate and valuable (proving an email
      was *not* sent to a self-excluded client). `[TABLE]` `[PROVE]`
2.11.14 The QuizStakes `never()` test that earns its place: `verify(notificationService,
      never()).send(any())` when the client is self-excluded — asserting on the absence of a side
      effect, which no state assertion can do. `[BUILD]` `[PROVE]`
2.11.15 **Mocking across a transaction boundary** as a specific error: a mocked repository means no
      transaction, no flush, no constraint, so a test of "the save rolls back" with a mocked
      repository is meaningless. `[TRAP]` `[X-REF 08]`
2.11.16 **The "mock the database" anti-pattern** and its cost, quantified: it moves every SQL and
      mapping defect from the test suite to production, which is precisely the defect class the
      trophy argument is about. `[PROVE]` `[TRAP]`
2.11.17 **The mocking policy as a written artifact**: a short `TESTING.md` stating what this codebase
      mocks and what it does not, so the decision is made once rather than per pull request.
      `[BUILD]`
2.11.18 The interview form of the whole section: **"I mock the things I cannot afford to run and own
      the interface to; everything else I run for real, and I say what each test therefore proves."**

## §2.12 HTTP stubbing — WireMock, MockWebServer, MockRestServiceServer

2.12.1 The problem this solves and that a Mockito mock cannot: **the risk in an outbound HTTP call is
      the wire** — the URL, the headers, the serialization, the status handling, the timeout. A
      mocked client stubs all of that away. `[PROVE]`
2.12.2 The three tools placed: **`MockRestServiceServer`** (Spring, in-process, binds to a
      `RestTemplate`/`RestClient`), **`MockWebServer`** (OkHttp, a real localhost socket, tiny),
      **WireMock** (a real HTTP server with a matching DSL, record/replay, fault injection, and a
      standalone/Testcontainers mode). `[TABLE]`
2.12.3 **`MockRestServiceServer`** with `@RestClientTest`: `expect(requestTo(…))`,
      `andExpect(method(POST))`, `andRespond(withSuccess(json, APPLICATION_JSON))`, `verify()`,
      `ExpectedCount`, and `reset()`. `[API]` `[BUILD]`
2.12.4 Its boundary: it intercepts at the `ClientHttpRequestFactory`, so it does **not** test
      connection handling, TLS, DNS or timeouts. `[PROVE]` `[TRAP]`
2.12.5 **WireMock's matching DSL**: `stubFor(get(urlPathEqualTo(…)).withHeader(…).withRequestBody(
      matchingJsonPath(…)).willReturn(aResponse().withStatus(…).withBodyFile(…)))`, plus scenarios
      (stateful stubs), priorities, and `verify(postRequestedFor(…))`. `[API]` `[TABLE]`
2.12.6 **WireMock's fault and latency injection** — `withFixedDelay`, `withUniformRandomDelay`,
      `withChunkedDribbleDelay`, `withFault(CONNECTION_RESET_BY_PEER | EMPTY_RESPONSE |
      MALFORMED_RESPONSE_CHUNK | RANDOM_DATA_THEN_CLOSE)`. This is the **only** practical way to test
      your retry, timeout and circuit-breaker configuration. `[TABLE]` `[API]` `[PROVE]`
      `[X-REF 10]`
2.12.7 The QuizStakes test that requires it: the identity vendor at **p99 38 s** against a
      restriction-decision budget of **30 ms** — the timeout, the fallback and the circuit breaker are
      the behaviour under test, and only a delaying stub server can drive them. `[NUM]` `[PROVE]`
2.12.8 **The 600/min estate-wide vendor cap** as the reason no test may ever call the real vendor: a
      CI run with 40 pipelines/day and a handful of calls each would consume the production quota.
      State the consequence, not just the rule. `[NUM]` `[PROVE]`
2.12.9 **WireMock registration options**: the JUnit 5 extension (`@WireMockTest`), a
      `@RegisterExtension` instance for per-test configuration, `WireMockServer` managed manually, and
      **`WireMockContainer`** via Testcontainers for a language-agnostic setup. `[TABLE]` `[API]`
2.12.10 **Wiring the stub's port into Spring**: `@DynamicPropertySource` mapping the vendor base URL to
      `wireMockRuntimeInfo.getHttpBaseUrl()`, and why a fixed port is a parallelism hazard.
      `[BUILD]` `[TRAP]`
2.12.11 **Record and playback** (`--record-mappings`, `--proxy-all`) as the fast way to capture a real
      vendor payload once — and the discipline it needs: scrub PII, pin the recording, and review it
      like code, because a recorded stub silently encodes yesterday's contract. `[TRAP]` `[PROVE]`
2.12.12 **Stub drift** as the fundamental limitation: a stub is *your belief* about the provider. It
      cannot tell you the provider changed. That gap is exactly what contract testing closes
      (§ 2.13). `[PROVE]` `[TRAP]`
2.12.13 **Response templating** (`{{request.path.[1]}}`) as the feature that lets one stub serve many
      cases, and the warning that a templated stub with logic in it is an unversioned second
      implementation of the provider. `[TRAP]`
2.12.14 **`MockWebServer`**'s different model — `enqueue(new MockResponse()…)` in FIFO order and
      `takeRequest()` for assertions — which is better for a strict request-sequence test and worse
      for a many-endpoints test. `[API]` `[TABLE]`
2.12.15 **`MockServerContainer`** and `LocalStackContainer` as the equivalents for a general stub
      server and for AWS services. `[X-REF 18]`
2.12.16 **The never-call-a-real-service rule**, preserved from the current guide's flake table and
      generalised: a test that reaches the internet is not a test, it is a monitor with a build gate
      attached. Enforce it — deny network in the small-test tier (§ 1.3.5). `[PROVE]` `[TRAP]`

## §2.13 Contract testing

2.13.1 The problem stated exactly as the current guide does, because it is well put: service A mocks
      service B in its tests, B changes its response shape, **both suites are green**, production
      breaks. E2E tests would catch it but are slow and require deploying everything. Preserve
      verbatim.
2.13.2 The general shape of the solution: replace "both sides have their own belief" with **one
      artifact both sides verify against**, and make each side's build fail independently.
      `[PROVE]`
2.13.3 **Consumer-driven contract testing (CDC)** — the four-step flow, preserved from the current
      guide and rendered as an ordered trace: consumer test against a mock provider generates a pact
      → pact published to a broker → provider replays the pact's requests against the real provider
      under declared **provider states** → the provider's build fails if it would break a real
      consumer. `[FLOW]` `[PROVE]`
2.13.4 The **three key properties** preserved verbatim, because they are the answer to "why not just
      run E2E": the contract states only what the consumer **actually uses** (so the provider is free
      to add fields), no shared environment or simultaneous deployment is needed, and each side runs
      independently in its own pipeline.
2.13.5 **`can-i-deploy`** as the release gate — the Pact Broker CLI query that answers "is this
      consumer version compatible with every provider version currently deployed in the target
      environment". Preserve the current guide's mention and give the command. `[CLI]` `[RESEARCH]`
2.13.6 **Provider states** in detail: a named precondition (`"a settled stake 88421 exists for client
      31007"`), a state handler on the provider that seeds it, and the discipline that state handlers
      must be as few and as coarse as possible or they become a second fixture system. `[PROVE]`
      `[TRAP]`
2.13.7 **Pact matchers** — `like`, `eachLike`, `regex`, `term`, `integer`, `decimal`, `datetime` — and
      the core rule: match on **type, not value**, or the contract breaks whenever the provider's test
      data changes. `[API]` `[TRAP]`
2.13.8 **Pact specification versions** — V2, V3, V4 — and what each adds (V3: provider states with
      parameters, message pacts; V4: plugins, synchronous messages). Selectable in pact-jvm via
      `PactSpecVersion`. `[TABLE]` `[RESEARCH]`
2.13.9 **pact-jvm's JUnit 5 surface**: `@ExtendWith(PactConsumerTestExt.class)`, `@Pact(consumer=…)`,
      `@PactTestFor(providerName, pactMethod, port)` on the consumer side; `@Provider`, `@PactBroker`,
      `@State`, `PactVerificationInvocationContextProvider` and `@TestTemplate` on the provider side.
      `[API]` `[RESEARCH]`
2.13.10 **Pact Broker vs PactFlow vs a git repository of pact files** — three ways to move the
      artifact, with the trade-off being who can see compatibility across the estate. `[TABLE]`
2.13.11 **Consumer version selectors and `WIP`/pending pacts** — the mechanism that stops a new
      consumer contract from breaking the provider's build on day one. This is the operational detail
      that decides whether CDC survives contact with a real organisation. `[RESEARCH]` `[PROVE]`
2.13.12 **Spring Cloud Contract** as the **producer-driven** alternative: the provider writes contracts
      (Groovy DSL or YAML), the plugin **generates provider verification tests** from them and
      publishes **stubs**, and consumers run those stubs via `@AutoConfigureStubRunner`
      (`ids`, `repositoryRoot`, `stubsMode`, `stubsPerConsumer`). `[API]` `[FLOW]` `[RESEARCH]`
2.13.13 The **base class** mechanism in Spring Cloud Contract — generated tests extend a base class you
      supply that sets up the context and mocks — and `baseClassMappings` when it differs per
      contract package. `[API]` `[RESEARCH]`
2.13.14 **Producer-driven vs consumer-driven**, compared honestly on: who writes the contract, whose
      build breaks first, whether unused fields are protected, organisational fit, and messaging
      support. Spring Cloud Contract can run consumer-driven too, so the distinction is about default
      workflow, not capability. `[TABLE]` `[PROVE]`
2.13.15 **Contract testing for messaging**: message pacts / Spring Cloud Contract's messaging DSL,
      verifying the *payload shape* on a topic rather than an HTTP response. The often-forgotten half.
      `[X-REF 14]`
2.13.16 **Schema-based compatibility as the third option**: a schema registry with
      `BACKWARD`/`FORWARD`/`FULL`/`TRANSITIVE` compatibility checks in CI. Cheaper than CDC,
      structurally weaker — it proves the schema evolves safely, not that any consumer's needs are
      met. `[TABLE]` `[PROVE]` `[X-REF 14]`
2.13.17 **OpenAPI-based contract checks**: validating requests/responses against the spec in tests
      (`atlassian-swagger-request-validator`), and spec-diff tooling in CI. The pragmatic middle:
      nearly free, catches shape breaks, misses semantics. `[X-REF 12]`
2.13.18 **What contract testing does not do**, said plainly: it does not verify behaviour, only the
      interface. A provider can honour the contract and return the wrong number. `[TRAP]` `[PROVE]`
2.13.19 **The cost of CDC**, stated so the recommendation is credible: a broker to run, provider states
      to maintain, a second CI gate, and organisational agreement. For two teams it is usually worth
      it; for one team owning both sides, an integration test is cheaper and stronger. `[PROVE]`
2.13.20 The QuizStakes contract map: `ApplicationGateway` → `RouterInt` (HTTP, high churn, CDC);
      `PaymentService` → `FundsLedger` (HTTP, one owner each side, CDC with strict states);
      `FundsLedger` → the settlement topic (message contract + schema registry);
      `ScreeningService` → the external identity vendor (**no contract test possible** — they will not
      run your pacts, so you get a stub plus a monitored canary). That last row is the honest answer
      to "what about third parties". `[TABLE]` `[PROVE]`

## §2.14 Property-based testing

2.14.1 The idea: instead of "for this input, expect this output", assert **a property that must hold
      for all inputs**, and let the framework generate hundreds of inputs and shrink any failure to
      a minimal counterexample. `[PROVE]`
2.14.2 Why it belongs in a backend engineer's toolkit rather than being academic: money arithmetic,
      serialization round trips, state machines and idempotency are all naturally expressed as
      properties, and all four exist in this domain. `[PROVE]`
2.14.3 **jqwik** as the JUnit-Platform-native option (its own `TestEngine`, so it runs alongside
      Jupiter), current version **1.10.1**. `[API]` `[CURRENCY]` `[RESEARCH]`
2.14.4 The jqwik surface: `@Property`, `@ForAll`, `@Provide` + `Arbitraries`, `@Domain`,
      `@StatisticsReport`, `Assume.that(…)`, `@Property(tries = …, seed = …, shrinking = …)`,
      `ShrinkingMode.FULL/BOUNDED/OFF`, and `@PropertyDefaults`. `[TABLE]` `[API]` `[RESEARCH]`
2.14.5 **Arbitraries** as generators: `Arbitraries.integers().between(…)`, `.strings()`, `.of(enum)`,
      `combine(…)`, `flatMap`, `filter`, `injectNull`, `list().ofMinSize`, and building a domain
      arbitrary for a `StakeAmount`. `[API]` `[BUILD]`
2.14.6 **Shrinking** explained mechanically, because it is the feature that makes PBT usable: on
      failure the framework searches for a smaller input that still fails, so you get `stake=0.01`
      rather than `stake=738104.29`. `[PROVE]`
2.14.7 **The seed** as the reproducibility contract: jqwik reports the failing seed, and re-running
      with `@Property(seed = "…")` reproduces it exactly. Without this, PBT would be a flake factory.
      `[PROVE]` `[TRAP]`
2.14.8 **The five property archetypes** every engineer can apply immediately: **round trip**
      (`deserialize(serialize(x)) == x`), **invariant** (a derived balance always equals the sum of
      positions), **idempotence** (`settle(settle(x)) == settle(x)`), **commutativity/associativity**
      (order of independent deposits does not change the balance), and **test oracle** (the new fast
      implementation agrees with the old slow one). `[TABLE]` `[PROVE]`
2.14.9 The **model-based / stateful** archetype: generate a random sequence of `AccountOpening`
      transitions and assert the state machine never reaches an illegal state — jqwik's `Action`/
      `ActionSequence` API. This is the highest-value property in the domain. `[API]` `[BUILD]`
2.14.10 The QuizStakes properties worth writing, named: derived balance == Σ positions (assumption
      #20); a settlement is idempotent; a self-excluded client can never reserve a stake (invariant
      8, as a property over arbitrary interleavings of operations); a deposit sequence never exceeds
      the daily limit; and JSON round-trips for every `ApplicationHistory` payload. `[TABLE]`
      `[PROVE]`
2.14.11 **PBT vs parameterized testing**: parameterized is *you* choosing the cases; PBT is the machine
      choosing them, including the ones you would never think of (empty, maximal, unicode,
      `BigDecimal` with 40 digits of scale). `[TABLE]` `[PROVE]`
2.14.12 **PBT's costs**, stated: slower (hundreds of tries), a failure needs interpretation, generators
      are code you maintain, and a badly-chosen property tests nothing (`assertThat(result).isNotNull()`
      for all inputs). `[TRAP]`
2.14.13 **The tautology trap**: a property that restates the implementation
      (`assertThat(fee(x)).isEqualTo(x.multiply(RATE))`) always passes and proves nothing. Properties
      must be *independently derived* from the requirement. `[TRAP]` `[PROVE]`
2.14.14 **Alternatives**: **QuickTheories**, **junit-quickcheck**, Kotest's property module, and the
      historical `ScalaCheck`/Haskell `QuickCheck` lineage worth naming for credibility. `[TABLE]`
2.14.15 **jqwik and JUnit 6** — a version-compatibility question the reader must check rather than
      assume, since jqwik ships its own engine against the Platform API. Flagged rather than
      asserted. `[VERSION-TRAP]` `[RESEARCH]`
2.14.16 **Fuzzing** as the adjacent discipline (Jazzer for the JVM, OSS-Fuzz), and the boundary: PBT
      checks properties of your logic, fuzzing hunts crashes and security failures on untrusted
      input. `[X-REF 13]` `[RESEARCH]`

## §2.15 Coverage — what it measures, and what it cannot

2.15.1 The definition that resolves most confusion: **coverage measures which code executed, not
      whether anything was asserted.** Preserve the current guide's framing verbatim, then prove it
      with a test that has no assertions and reports 100%. `[PROVE]` `[TRAP]` `[BUILD]`
2.15.2 **The coverage criteria hierarchy**, with what each subsumes: statement/line → branch/decision
      → condition → condition/decision → **modified condition/decision coverage (MC/DC)** → path.
      Each is strictly stronger and strictly more expensive. `[TABLE]` `[PROVE]`
2.15.3 Why **path coverage is infeasible**: a method with a loop has unbounded paths, and even
      loop-free code with *n* independent conditions has 2^n paths. The arithmetic, shown. `[PROVE]`
      `[NUM]`
2.15.4 **Line coverage vs branch coverage**, with the canonical counterexample: `if (a && b) return
      x;` on one line reaches 100% line coverage from a single test while leaving three of four
      condition combinations unexercised. `[PROVE]` `[NUM]` `[TRAP]`
2.15.5 The practical rule that follows: **quote branch coverage, not line coverage**, and be suspicious
      of any tool report that leads with lines. `[PROVE]`
2.15.6 **JaCoCo's counters, all six, exactly as documented**: **instructions** (the smallest unit,
      bytecode instructions — C0), **branches** (`if` and `switch` only — C1), **cyclomatic
      complexity** (`v(G) = B − D + 1`), **lines** (a line is covered when at least one instruction
      assigned to it executed), **methods** (covered when at least one instruction executed), and
      **classes** (covered when at least one method executed). `[TABLE]` `[SOURCE]` `[NUM]`
2.15.7 The three documented limitations that change how you read the report: **exception handling is
      excluded from branch counting and does not raise complexity**; **line coverage requires debug
      information** in the class files; and class totals cannot be derived by summing method totals
      because a line can span methods. `[SOURCE]` `[TRAP]`
2.15.8 The consequence for a `try/catch`-heavy service: JaCoCo will report high branch coverage on
      code whose error paths are entirely untested, because the catch is not a branch. This single
      fact invalidates a lot of coverage-gate confidence. `[PROVE]` `[TRAP]`
2.15.9 **Instruction coverage as JaCoCo's most honest number** — independent of formatting and of
      debug info — and why nobody quotes it. `[PROVE]`
2.15.10 **Goodhart's law applied**, preserved from the current guide: use coverage as a *floor* to find
      untested areas, never as a target; a mandated 90% produces getter tests. `[PROVE]` `[TRAP]`
2.15.11 What a coverage **gate** can legitimately do, so the section is not purely negative: fail on a
      **decrease** on changed lines (patch coverage), which is a genuine ratchet, rather than on an
      absolute project number. `[PROVE]` `[CFG]`
2.15.12 **JaCoCo's Maven/Gradle surface**: `prepare-agent`, `report`, `check` with `RULE`/`LIMIT`
      counters and `COVEREDRATIO`, `jacocoTestReport`, `jacocoTestCoverageVerification`, and the
      `${argLine}` interaction (§ 1.12.3). `[CFG]` `[CLI]`
2.15.13 **Exclusions done honestly**: excluding generated code, DTOs and configuration classes is
      legitimate and must be reviewable in the build file; excluding a package because it is
      untested is fraud. `[TRAP]`
2.15.14 **`@Generated` / `lombok.addLombokGeneratedAnnotation`** and JaCoCo's filters for synthetic
      code, `equals`/`hashCode`, and default constructors — the reason a record shows odd coverage.
      `[CFG]` `[RESEARCH]`
2.15.15 **Multi-module and aggregate reports**: `jacoco:report-aggregate`, and why cross-module
      coverage of a shared library reads as zero until you aggregate. `[CFG]` `[DIAG]`
2.15.16 **Coverage of integration tests** — a separate exec file merged with the unit-test one — and
      the honest observation that "our coverage went up when we added E2E tests" is usually a sign
      the metric is measuring the wrong thing. `[TRAP]`
2.15.17 **Coverage is a directional tool**: it answers "what have I not run at all", which is a genuine
      and useful question. A 0%-covered class is a real finding; the difference between 82% and 86% is
      not. `[PROVE]`
2.15.18 **Coverage vs mutation score** as the transition to § 2.16: coverage measures execution,
      mutation measures verification. Preserve the current guide's line. `[PROVE]`
2.15.19 The interview answer in one sentence: **"I use coverage to find untested code and mutation
      testing to find unverified code, and I gate on patch coverage rather than a project
      percentage."**

## §2.16 Mutation testing

2.16.1 The premise: **mutate the code, and if no test fails, no test was actually checking that
      behaviour.** Preserve the current guide's framing — PIT mutates the bytecode (flips `>` to
      `>=`, returns null, removes a call) and checks whether a test fails. `[PROVE]`
2.16.2 The vocabulary precisely: a mutant is **killed** (a test failed — good), **survived** (no test
      failed — a gap), **no coverage** (no test even executed the line), **timed out** (the mutation
      caused an infinite loop — counts as killed), or **non-viable/equivalent**. `[TABLE]`
2.16.3 **Mutation score** = killed / (total mutants generated), and the more useful variant **test
      strength** = killed / (mutants with coverage), which separates "untested" from "unverified".
      `[NUM]` `[PROVE]`
2.16.4 A surviving mutant, in the current guide's words to be preserved: **a line your tests execute
      but do not verify.** `[PROVE]`
2.16.5 **PIT's default mutator set, enumerated exactly** from the documentation: Conditionals
      Boundary, Increments, Invert Negatives, Math, Negate Conditionals, Void Method Calls, Empty
      Returns, False Returns, True Returns, Null Returns, Primitive Returns. Eleven operators.
      `[TABLE]` `[SOURCE]` `[NUM]` `[RESEARCH]`
2.16.6 **PIT's optional and experimental mutators, enumerated**: Constructor Calls, Inline Constant,
      Non Void Method Calls, Remove Conditionals, Remove Increments, Arithmetic Operator Replacement
      (AOR), Arithmetic Operator Deletion (AOD), Constant Replacement (CRCR), Bitwise Operator
      (OBBN), Relational Operator Replacement (ROR), Unary Operator Insertion (UOI), Negation (ABS),
      Experimental Switch, Experimental Argument Propagation, Experimental Big Integer, Experimental
      Naked Receiver, Experimental Member Variable. `[TABLE]` `[SOURCE]` `[RESEARCH]`
2.16.7 **Why the defaults are a subset**: the excluded operators generate large numbers of equivalent
      or unkillable mutants, which cost runtime and produce noise. Enabling `ALL` is a common
      first-time mistake. `[PROVE]` `[TRAP]`
2.16.8 **Reading a PIT report** — the HTML line-by-line view, the mutation annotations per line, and
      the workflow: look at surviving mutants in the domain layer, and either write the missing
      assertion or accept the mutant with a reason. `[DIAG]` `[FLOW]`
2.16.9 **The equivalent-mutant problem** as the theoretical limit: some mutants are semantically
      identical to the original and cannot be killed by any test. This is undecidable in general, so
      100% mutation score is not a target. `[PROVE]` `[TRAP]`
2.16.10 **The empirical case for mutation testing**, cited rather than asserted: Just et al. (FSE
      2014) studied **357 real faults across 5 open-source applications totalling 321,000 lines** and
      found a statistically significant correlation between mutant detection and real-fault
      detection **independent of code coverage**, with a coupling effect for **73% of real faults**.
      `[STUDY]` `[NUM]` `[RESEARCH]`
2.16.11 **Google's operational finding**, cited: showing developers surviving mutants leads them to
      write more and better tests, and Google's system deliberately generates **a single mutant per
      line** to keep the signal actionable. This is the design lesson for adopting it. `[STUDY]`
      `[PROVE]` `[RESEARCH]`
2.16.12 **The cost model**: naively, runtime is `O(mutants × tests)`. PIT reduces it with
      **coverage-driven test selection** (only run tests that cover the mutated line), mutant-level
      timeouts, and parallel threads. This is the mechanism that makes it tractable at all (§ 3.15).
      `[PROVE]` `[NUM]`
2.16.13 **`withHistory` / incremental analysis** and **`scmMutationCoverage`** (mutate only changed
      files) — the two features that make mutation testing viable in a per-commit pipeline. `[CFG]`
      `[RESEARCH]`
2.16.14 The deployment recommendation, preserved from the current guide and refined: run it on the
      **domain layer** or on changed files per commit, and the full run nightly. Never the whole
      codebase per commit. `[PROVE]`
2.16.15 **`mutationThreshold` / `coverageThreshold`** as build gates, and the same Goodhart warning as
      coverage — with the difference that mutation score is much harder to game, because the only way
      to raise it is to assert more. `[PROVE]` `[CFG]`
2.16.16 **What mutation testing cannot do**: it cannot invent a missing requirement, cannot detect a
      missing feature, and cannot evaluate integration tests cheaply (they are too slow per mutant).
      `[TRAP]`
2.16.17 **PIT's practical friction**, stated honestly: `pitest-junit5-plugin` needed for Jupiter,
      long runtimes on wide modules, trouble with dynamic frameworks and Lombok-generated code, and
      confusing behaviour with Spring contexts (which is another argument for running it against the
      domain layer only). `[TRAP]` `[RESEARCH]`
2.16.18 **Alternatives**: `pitest-descartes` (extreme mutation — replace whole method bodies, far
      cheaper, coarser signal) and the research direction of LLM-generated mutants. Named for
      completeness. `[RESEARCH]`
2.16.19 The QuizStakes target for a first mutation run: the stake-eligibility decision, the
      deposit-limit accumulator, the fee calculation, and the `AccountOpening` transition table — four
      classes, all pure, where a surviving mutant is a real and cheap finding. `[TABLE]`

## §2.17 Flaky tests

2.17.1 The definition to use: **a test that passes and fails on the same code**. Not "a test that
      fails sometimes" — the code being identical is the whole point. `[PROVE]`
2.17.2 The current guide's opening claim preserved verbatim: **a flaky test is worse than no test — it
      trains the team to ignore red builds.** `[PROVE]`
2.17.3 **The empirical taxonomy**, cited rather than invented: Luo et al.'s study of **201 flaky
      tests** identified ten root causes, with **async wait (~45%), concurrency (~20%) and test order
      dependency (~12%)** dominating, followed by resource leak, network, time, I/O, randomness,
      floating point, and unordered collections. `[STUDY]` `[NUM]` `[TABLE]` `[RESEARCH]`
2.17.4 The language-dependence finding, which matters for a Java answer: order dependency dominates in
      Python, concurrency in JavaScript and Android. For a JVM backend suite, async wait and shared
      state are the two to look for first. `[STUDY]` `[RESEARCH]`
2.17.5 **The cause × symptom × fix table** — the current guide's § 7 preserved in full, every row
      kept, and each row extended with a *detection* method. The ten current rows: shared mutable
      state, test order dependence, timing/`Thread.sleep`, real async without synchronisation,
      wall-clock/date logic, unseeded randomness, port/resource collisions, external network calls,
      leaked DB state, and iteration-order assumptions. `[TABLE]`
2.17.6 The rows the current guide is missing, each with symptom and fix: **container/image pull
      timeouts**, **wait-strategy races in Testcontainers** (§ 2.6.12), **Spring context eviction
      under cache pressure** (§ 2.7.7), **static state in a reused Surefire fork**, **`ThreadLocal`
      leaks across tests**, **file-system case sensitivity and path separators**, **CI resource
      starvation making a timeout fire**, **JIT warmup affecting a timing assertion**, **GC pause
      exceeding an Awaitility timeout**, **DNS/`/etc/hosts` differences**, **assertion on a
      `HashSet`'s `toString`**, **floating-point accumulation order**, **daylight-saving transitions**,
      and **test-order-dependent id sequences**. `[TABLE]`
2.17.7 **Order dependence as its own subject**: victim/polluter/brittle/state-setter terminology, and
      the detection technique — run with `MethodOrderer.Random` and a logged seed, and run each test
      class in isolation. `[PROVE]` `[RESEARCH]`
2.17.8 **The isolation bisect** as the concrete debugging procedure for a suite-only failure: run the
      failing class alone (passes) → run the whole suite (fails) → bisect the class list to find the
      polluter. `[FLOW]` `[CLI]`
2.17.9 **Detection at scale**: re-run the suite N times on unchanged code and record per-test failure
      rates; or run the suite against the same commit nightly. This is how you get a *list* rather
      than anecdotes. `[FLOW]` `[METRIC]`
2.17.10 **The flake-rate metric** defined so it is checkable: failures on unchanged code ÷ total runs,
      per test and per suite, tracked over time. A per-suite rate above ~1% means the gate is no
      longer a gate. `[METRIC]` `[NUM]`
2.17.11 **Quarantine as a policy, not an act**: move the flake out of the gating suite, **file a ticket
      with an owner and a deadline**, keep running it in a non-gating job so the data keeps
      accumulating, and delete it at the deadline. `[FLOW]` `[PROVE]`
2.17.12 The current guide's rule preserved verbatim: **quarantine, then fix or delete — never `@Retry`
      as the resolution. A retried test hides a real race that will surface in production.**
      `[TRAP]`
2.17.13 The steelmanned counter-argument, because a senior answer engages with it: automatic retry at
      the *suite* level is defensible for a genuinely non-hermetic E2E tier where the flakiness is in
      the environment, **provided the retry is recorded and reported as a flake**. Retrying silently
      is what makes it dishonest. `[PROVE]`
2.17.14 **`maven-surefire`'s `rerunFailingTestsCount` and Gradle's `test-retry` plugin** — named,
      because they exist and the reader will meet them, with the reporting requirement attached.
      `[CFG]` `[TRAP]`
2.17.15 **The flake is often a real bug.** An async-wait flake in a stake-settlement test is telling
      you that the settlement is not synchronised, which at 3,400 settlements/sec bursts is a
      production defect with a client-money consequence. Treat the flake as a bug report until proven
      otherwise. `[PROVE]` `[NUM]`
2.17.16 **The prevention checklist**, as build-level policy rather than per-test vigilance: pin
      timezone/locale/encoding; forbid `Thread.sleep` in tests (a checkstyle rule); random ports
      everywhere; unique data per test; no static mutable state; deny network in the unit tier; run
      in random order in CI. Seven rules that eliminate most of the taxonomy. `[TABLE]` `[FLOW]`
2.17.17 **The one-hour flake triage** procedure: reproduce with the logged seed → check the taxonomy
      → determine if it is a product bug or a test bug → fix or quarantine with a ticket. Having a
      procedure is what stops flakes accumulating. `[FLOW]`
2.17.18 **Flakiness in CI vs locally** as a diagnostic signal in itself: CI-only means resource
      contention, parallelism, or a missing environment assumption; local-only means machine state.
      `[PROVE]` `[DIAG]`

## §2.18 TDD and BDD as practices

2.18.1 **Red-green-refactor** stated as a loop with a purpose for each step: red proves the test can
      fail (and therefore that it tests something), green proves the behaviour, refactor is where the
      design happens. Skipping red is the most common way to write a test that cannot fail. `[FLOW]`
      `[PROVE]`
2.18.2 **The "watch it fail" discipline** as a standalone rule: a test you never saw fail is not
      evidence. Its practical form — mutate the production code by hand and confirm the test reddens
      — is a manual mutation test. `[PROVE]`
2.18.3 **The three laws of TDD** (Martin) and the honest framing: they are a *training* constraint for
      building the habit, not a permanent operating rule. `[SPEC]`
2.18.4 What TDD actually buys, argued: it forces you to state the expected behaviour before you have
      an implementation to be biased by, it guarantees testability by construction, and it produces
      the minimum design that satisfies the tests. `[PROVE]`
2.18.5 What TDD does not buy: a good architecture (it optimises locally), a good test suite (you can
      TDD your way to an over-mocked one), or speed on a problem you do not yet understand.
      `[TRAP]`
2.18.6 **When TDD is the wrong tool**: exploratory spikes, UI layout, performance work, and anything
      where you cannot state the expected result yet. Say this — an interviewer asking "do you always
      TDD" is usually probing for dogma. `[PROVE]`
2.18.7 **Test-after done well** vs test-after done badly: writing the test after the code is fine if
      you make it fail first; it is not fine if you write the test to match what the code happens to
      do (which is a characterization test presented as a specification). `[PROVE]` `[TRAP]`
2.18.8 **Chicago / Detroit / classical TDD** — inside-out from the domain, real collaborators wherever
      practical, state verification, doubles only for awkward collaborations. Fowler's definition
      quoted. `[SOURCE]` `[SPEC]`
2.18.9 **London / mockist TDD** — outside-in from the entry point, mock any collaborator with
      interesting behaviour, behaviour verification, "tell don't ask" design pressure. `[SOURCE]`
2.18.10 The trade-off table, from Fowler, reproduced with its four axes: **design approach**
      (middle-out vs outside-in), **coupling to implementation** (lower vs higher), **defect
      isolation** (cascading vs localised failures), and **setup overhead** (fixture complexity vs
      per-test mock creation). `[TABLE]` `[SOURCE]`
2.18.11 The synthesis a senior engineer should give: **outside-in for discovering the interfaces,
      classical for the domain core.** The schools are tools, not identities, and the choice is
      per-layer. `[PROVE]`
2.18.12 **Where London-style goes wrong in practice**: it produces the over-mocked suite of § 1.4.17,
      because "any collaborator with interesting behaviour" includes the ones you own and could just
      construct. `[TRAP]` `[PROVE]`
2.18.13 **Where Chicago-style goes wrong**: sociable tests over a deep object graph give you a slow
      "unit" test whose failure names ten classes, and fixture setup that grows without bound.
      `[TRAP]`
2.18.14 **BDD as a communication practice, not a test framework**: the deliverable is a shared
      vocabulary and examples agreed with a non-engineer, and Gherkin is a notation for that
      agreement. `[PROVE]`
2.18.15 **Gherkin and Cucumber-JVM**: `Feature`/`Scenario`/`Given`/`When`/`Then`/`And`/`Background`/
      `Scenario Outline`/`Examples`, step definitions with `@Given("…")` regex or Cucumber
      expressions, hooks (`@Before`/`@After`), tags, and the `cucumber-junit-platform-engine` that
      makes it a Platform engine (§ 1.6.2). `[API]` `[TABLE]`
2.18.16 **When Cucumber earns its cost**: when a non-engineer actually reads or writes the scenarios.
      When they do not, you have added a regex indirection layer and a step-definition maintenance
      burden for nothing — and that is the common case. Say so. `[PROVE]` `[TRAP]`
2.18.17 **Spock** as the JVM's most ergonomic alternative: Groovy, `given/when/then` blocks, `where:`
      data tables, built-in mocks with a much better syntax, and **power assertions** whose failure
      output shows every subexpression's value. Its cost is a second language in the build.
      `[API]` `[TABLE]`
2.18.18 **`@DisplayName` + `@Nested` as "BDD without the framework"** — nested classes named
      `WhenTheClientIsSelfExcluded` containing `thenReserveStakeIsRejected`. All of Gherkin's
      readability, none of its indirection. This is the recommendation. `[BUILD]` `[PROVE]`
2.18.19 **ATDD / specification by example** as the outer loop around TDD's inner loop, and the
      "double-loop" diagram: an acceptance test drives a feature, unit tests drive each class inside
      it. `[FLOW]`
2.18.20 **The practice questions an interviewer actually asks** and what a good answer looks like: "do
      you write tests first?" (sometimes, and here is when I do not), "what do you do when TDD feels
      slow?" (spike then delete then TDD), "how do you test-drive a bug fix?" (reproduce first).
      `[TABLE]`

## §2.19 Testing legacy code

2.19.1 The defining problem, in Feathers's terms: **legacy code is code without tests**, and the
      dependency-breaking problem is circular — you cannot test it without changing it, and you
      should not change it without tests. `[SPEC]` `[PROVE]`
2.19.2 **The seam** as the resolution: a place where you can alter behaviour without editing in that
      place. **Object seam** (override a method / inject a collaborator), **link seam** (swap a jar
      or a classpath entry), **preprocessing seam** (not available in Java). Naming the seam type is
      the skill. `[SPEC]` `[TABLE]`
2.19.3 **The enabling point** of a seam — where you choose which behaviour applies — and why a seam
      without a reachable enabling point is useless. `[SPEC]`
2.19.4 **Characterization tests**, preserved from the current guide in full: before changing code with
      no tests and unclear behaviour, write tests that assert what it *currently* does — **including
      the bugs**. They are not correctness tests; they are a change-detector that turns "I hope this
      refactor is safe" into "the build tells me". `[PROVE]`
2.19.5 The mechanical procedure for writing one when you do not know the expected value: assert
      something obviously wrong, run it, read the actual value from the failure message, paste it in.
      This is legitimate and fast. `[FLOW]` `[DIAG]`
2.19.6 Then the current guide's next step preserved: refactor, then fix the bug as a **deliberate,
      visible test change** — the diff on the test is the record of the behaviour change.
2.19.7 **Approval / golden-master testing** — preserved from the current guide and given its
      mechanism: snapshot the output for many inputs, store the approved file, and diff on each run.
      `ApprovalTests` for Java, `assertj`'s file comparison, or a plain resource file. `[API]`
2.19.8 When golden-master is the right tool: a large output (a generated statement PDF, an
      `ApplicationHistory` export) where enumerating assertions is impractical but a diff is
      meaningful. `[PROVE]`
2.19.9 Its cost: an approved file nobody reviews becomes a rubber stamp, and a formatting change
      reddens everything. Mitigate with normalisation (sort keys, mask ids and timestamps). `[TRAP]`
2.19.10 **The dependency-breaking techniques catalogue**, named so the reader can reach for one:
      Extract Interface, Extract and Override Call, Extract and Override Factory Method, Parameterize
      Constructor, Parameterize Method, Introduce Instance Delegator, Adapt Parameter, Subclass and
      Override Method, Expose Static Method, Break Out Method Object. `[TABLE]` `[SPEC]`
2.19.11 **Sprout Method / Sprout Class / Wrap Method / Wrap Class** as the four ways to add behaviour
      to untested code *without* touching it — the techniques for "I need to ship this Tuesday".
      `[TABLE]` `[SPEC]`
2.19.12 **The static-dependency problem** as the most common concrete blocker (`Instant.now()`,
      `SomeUtil.calculate()`, `new SomeClient()` inside a method) and the ladder of fixes: inject →
      Extract and Override → `mockConstruction`/`mockStatic` as the last resort with a comment saying
      why. `[FLOW]` `[PROVE]`
2.19.13 **Testing around a god class**: identify the one behaviour you need, extract it with its
      minimal dependencies, test the extraction, leave the rest. Incremental, and the only approach
      that finishes. `[PROVE]`
2.19.14 **The scratch-refactoring technique**: refactor freely to *understand* the code, then throw it
      away and do it properly with tests. Named because it is counterintuitive and effective.
      `[SPEC]`
2.19.15 **Coverage as a legacy map**: a coverage report on a legacy module tells you where to start
      (the 0% classes with the highest change frequency), which is the one legitimate coverage-driven
      decision. `[PROVE]` `[METRIC]`
2.19.16 **Change-coupled coverage**: cross-reference coverage with git churn to find the untested code
      that changes most. That intersection is the priority list. `[X-REF 17]` `[PROVE]`
2.19.17 **The strangler pattern's testing implication**: the new implementation gets contract tests
      against the old one's behaviour (a **parallel-run / shadow comparison**), which is a
      characterization test at the system level. `[X-REF 22]`
2.19.18 The honest framing for an interview: **"I do not try to get legacy code to 80% coverage. I get
      a seam, a characterization test, and then I refactor the part I need to change."** `[PROVE]`

## §2.20 Performance, load and the boundary with testing

2.20.1 The boundary stated first: **a functional test must never assert on latency**, because CI
      machines are shared and the assertion will flake. Performance verification is a different
      activity with different tooling and a different failure policy. `[PROVE]` `[TRAP]`
2.20.2 The four distinct activities, separated because people conflate them: **microbenchmark**
      (nanoseconds, one method), **load test** (throughput and latency of a service under concurrent
      users), **stress test** (behaviour past capacity), **soak/endurance test** (leaks and drift over
      hours). Plus **spike** and **capacity** tests. `[TABLE]`
2.20.3 **JMH** as the only credible JVM microbenchmark harness, and *why* a hand-rolled
      `System.nanoTime()` loop is invalid: JIT warmup, dead-code elimination, constant folding,
      on-stack replacement, and loop unrolling all conspire to measure nothing. `[PROVE]`
      `[X-REF 06]`
2.20.4 The JMH surface: `@Benchmark`, `@State(Scope.Benchmark|Thread)`, `@Setup`/`@TearDown` with
      `Level.Trial|Iteration|Invocation`, `@Warmup`, `@Measurement`, `@Fork`, `@BenchmarkMode`
      (`Throughput`, `AverageTime`, `SampleTime`, `SingleShotTime`, `All`), `@OutputTimeUnit`, and
      **`Blackhole`** to defeat dead-code elimination. `[TABLE]` `[API]` `[X-REF 06]`
2.20.5 **JMH does not belong in the test suite**: separate source set, separate task, run deliberately
      and compared against a recorded baseline. A JMH run in CI is a 10-minute job that fails
      randomly. `[PROVE]`
2.20.6 **Gatling and k6** for load: a scenario DSL, an injection profile (`rampUsers`,
      `constantUsersPerSec`), assertions on percentiles rather than means, and the requirement that
      the load generator not be the bottleneck. `[TABLE]` `[X-REF 22]`
2.20.7 **Percentiles, not averages** — and specifically p99, because at 1,200 stake reservations/sec a
      p99 breach affects 12 clients every second. `[NUM]` `[PROVE]` `[X-REF 20]`
2.20.8 **Coordinated omission** as the measurement error that makes most homegrown load tests wrong:
      if the client waits for a slow response before sending the next request, the slow period is
      under-sampled and the latency distribution is optimistic. Name it; it is a strong signal in an
      interview. `[PROVE]` `[TRAP]` `[RESEARCH]`
2.20.9 **Load-testing against the SLO, not against a number**: the QuizStakes budgets — 30 ms
      restriction decision, 150 ms stake reservation, 4 s card deposit, hard 500 ms self-exclusion —
      are the assertions. `[NUM]` `[X-REF 20]`
2.20.10 **The environment problem**: a load test on a laptop, against H2, with one instance, proves
      nothing about 8 instances of `ClientRestrictions` at 4 GB heap. State the fidelity requirement
      or state the limitation. `[PROVE]` `[NUM]`
2.20.11 **Performance regression gating** done sustainably: track a metric over time with a wide band
      and alert on trend, rather than failing a build on a single noisy measurement. `[METRIC]`
      `[PROVE]`
2.20.12 **The one performance-ish assertion that is legitimate in a functional test**: a **query
      count** (§ 2.5.20) or an **allocation count** — deterministic proxies for performance that do
      not depend on machine speed. This is the technique that gets you a regression gate without
      flakiness. `[PROVE]` `[BUILD]`
2.20.13 **Chaos and resilience testing** as the adjacent discipline: fault injection at the stub layer
      (§ 2.12.6) in tests, and Chaos Monkey / Chaos Mesh in an environment. The testing-owned part is
      the WireMock fault test. `[X-REF 22]`
2.20.14 **Testing timeouts and retries** as a *functional* concern that people misfile as performance:
      "on a 5-second vendor delay, we return a cached decision" is a functional assertion, driven by
      a delaying stub, and it belongs in the normal suite. `[PROVE]` `[BUILD]`

## §2.21 CI — selection, sharding, ordering, and build time

2.21.1 The CI-specific goals, which differ from local ones: **fail fast**, **fail informatively**,
      **fail reproducibly**, and **cost per pipeline**. Optimising suite duration without the other
      three is how you get a fast useless gate. `[TABLE]`
2.21.2 **The pipeline tier structure** that most teams converge on: compile + static analysis → unit
      tier (< 2 min) → slice/integration tier (< 8 min) → contract verification → deploy to an
      environment → smoke tier. Each tier gates the next. `[FLOW]`
2.21.3 **Fail-fast ordering**: run the fast tier first so a compile error or a unit failure does not
      wait behind a container startup. `ClassOrderer` and tier separation are the mechanisms.
      `[PROVE]` `[CFG]`
2.21.4 **Sharding** — split the test set across N runners — with the three splitting strategies:
      by class name hash (simple, unbalanced), by **recorded historical duration** (balanced, needs a
      timing store), and dynamic work-stealing via a queue (best, most infrastructure). `[TABLE]`
      `[PROVE]`
2.21.5 The sharding arithmetic and its ceiling: with a 12-minute suite, 4 shards give ~3 min + fixed
      overhead per shard (JVM start, image pulls, context builds), so the fixed cost dominates
      quickly. Compute the break-even shard count. `[NUM]` `[PROVE]`
2.21.6 The sharding hazard: **shared external state**. Four shards each truncating the same database
      is a race. Sharding requires per-shard isolation — its own container, its own schema, or its own
      namespace. `[TRAP]` `[PROVE]`
2.21.7 **In-JVM parallelism** as the cheaper first move (§ 3.6), because it amortises the JVM and the
      Spring context across threads rather than duplicating them. Do this before sharding. `[PROVE]`
2.21.8 **Test selection / test impact analysis**: run only the tests affected by the change, derived
      from a per-test coverage map. Powerful, and it fails silently when the map is stale — so the
      full suite must still run on a schedule and before merge. `[PROVE]` `[TRAP]`
2.21.9 The tools that do it, named: Gradle Enterprise / Develocity Predictive Test Selection, Maven's
      `-Dsurefire.includes` driven by a diff, and `pitest`'s SCM mode as an analogue. `[RESEARCH]`
2.21.10 **Caching** in CI: the Maven/Gradle dependency cache, the Gradle build cache and
      configuration cache, and Docker layer/image caching for Testcontainers images. Each of these is
      usually worth more than a test-code optimisation. `[PROVE]` `[X-REF 19]`
2.21.11 **Gradle's up-to-date checks and build cache can skip the test task entirely** — a genuine
      speedup and a genuine debugging trap (`--rerun-tasks`). `[TRAP]` `[CLI]`
2.21.12 **Randomised order in CI, fixed order locally** as the standing policy: CI exposes order
      dependence with a logged seed; local runs stay reproducible. `[CFG]` `[PROVE]`
2.21.13 **Resource limits on CI runners** and their test consequences: fewer cores than
      `availableProcessors()` reports in a container (§ 3.6), a memory limit that OOM-kills a forked
      JVM, and a disk quota that a Testcontainers image pull exhausts. `[NUM]` `[X-REF 19]`
      `[X-REF 06]`
2.21.14 **`availableProcessors()` under cgroups** as a specific, high-value trap: JUnit's dynamic
      parallelism strategy multiplies it, so a mis-detected core count either serialises the suite or
      oversubscribes it into timeouts. `[TRAP]` `[PROVE]` `[X-REF 19]`
2.21.15 **Artifacts to publish on failure**, because a red CI build with no evidence costs a rerun:
      the Surefire XML, container logs (`container.getLogs()`), a thread dump on timeout, the failing
      seed, and screenshots for UI tests. `[TABLE]` `[DIAG]`
2.21.16 **Required checks and branch protection** as the mechanism that makes the gate real, and the
      failure mode of making a flaky suite required (people acquire the habit of re-running until
      green). `[X-REF 17]` `[PROVE]`
2.21.17 **Pre-commit / pre-push hooks** as the fast local subset — and the rule that they must be
      fast enough not to be bypassed, or they will be. `[X-REF 17]`
2.21.18 **The nightly job's distinct purpose**: the full E2E tier, mutation testing, a soak test, and
      a flake-detection re-run loop. Things that are too slow to gate but too valuable to skip.
      `[TABLE]`
2.21.19 The QuizStakes pipeline worked as a concrete target: unit tier 90 s, slice tier 3 min on two
      shared contexts, integration tier 5 min on a singleton Postgres + Kafka, contract verification
      40 s, one smoke test post-deploy — a **~10 minute** gate, with mutation testing and E2E
      nightly. `[NUM]` `[TABLE]`

## §2.22 Test-suite observability

2.22.1 The frame: a test suite is a **production system your team depends on daily**, and it deserves
      the same instrumentation as a service. Nobody treats it that way, which is why suites decay
      invisibly. `[PROVE]` `[X-REF 20]`
2.22.2 **The metric set worth collecting**, each with what a bad value looks like: suite duration
      (p50 and p95, not mean), per-test duration distribution, flake rate per test, failure rate by
      cause, context-build count, container-start count, and queue time before the run starts.
      `[TABLE]` `[METRIC]`
2.22.3 **Duration distribution over mean**: a 6-minute suite that is one 4-minute test is a completely
      different problem from 400 tests at 900 ms, and the mean hides which one you have. `[PROVE]`
      `[NUM]`
2.22.4 **The slowest-20 list** as the highest-value report you can produce, and the fact that both
      Surefire XML and Gradle scans already contain it. `[CLI]` `[DIAG]`
2.22.5 **Flake dashboards** built from the JUnit XML across runs: per-test pass/fail history keyed by
      commit, which is what makes "unchanged code" detectable. `[METRIC]` `[FLOW]`
2.22.6 **`TestWatcher` and JUnit Platform listeners** as the in-process hook for emitting these
      metrics yourself — `TestExecutionListener` on the launcher, `TestWatcher` per test. `[API]`
      `[BUILD]`
2.22.7 **JUnit Platform's JFR events** (folded into `junit-platform-launcher` in JUnit 6) as the
      zero-code way to profile a suite's discovery and execution phases. `[VERSION-TRAP]` `[CLI]`
      `[RESEARCH]`
2.22.8 **Open Test Reporting** as the format that replaces the Surefire XML's limitations (it can
      carry structured metadata and hierarchy), via `junit-platform-reporting`. `[RESEARCH]`
2.22.9 **Container logs as first-class test output**: `container.getLogs()`, a
      `Slf4jLogConsumer`, and `withLogConsumer` — because "the test failed and the database said why"
      is a solved problem people leave unsolved. `[API]` `[DIAG]`
2.22.10 **Reading a Spring test failure**: the context-startup stack trace is long and the real cause
      is at the bottom (`NoSuchBeanDefinitionException`, a failed `@Bean` method, a property
      placeholder). Read a real one line by line. `[DIAG]` `[BUILD]`
2.22.11 **Reading a Mockito failure**: the `Argument(s) are different!` diff, the
      `PotentialStubbingProblem` message with its list of registered stubbings, and the
      `UnnecessaryStubbingException`'s location list. Each names the fix if you read it. `[DIAG]`
2.22.12 **Reading an AssertJ recursive-comparison failure**, which is verbose and precise: the field
      path, the two values, and the comparison configuration in force. `[DIAG]`
2.22.13 **Reading a Testcontainers failure**: "Could not find a valid Docker environment", a wait
      strategy timeout with the container's last log lines, and an image pull failure. Three
      messages, three completely different fixes. `[DIAG]` `[TABLE]`
2.22.14 **The build-time budget as an SLO** with an owner: "the gating suite stays under 10 minutes"
      as an explicit commitment, with a dashboard and an alert when it drifts. Without this, suite
      duration only ever increases. `[METRIC]` `[PROVE]` `[X-REF 20]`
2.22.15 **Test-suite postmortems**: when a defect escapes, ask which test *should* have caught it and
      why it did not. That question, asked consistently, is what shapes the suite correctly over
      time — and it is what § 1.3.10's "measure your defect origins" needs as input. `[FLOW]`
      `[X-REF 20]`

## §2.23 The anti-pattern catalogue

2.23.1 The framing: these have names because they recur. Meszaros's *xUnit Test Patterns* catalogues
      test smells as **code smells**, **behaviour smells** and **project smells** — a three-way split
      worth keeping because the remedy differs by category. `[SPEC]` `[TABLE]` `[RESEARCH]`
2.23.2 **Assertion Roulette** — multiple unlabelled assertions in one test, so a failure does not say
      which. Symptom: "expected true but was false" with no context. Fix: `assertAll` with
      descriptions, AssertJ's `as(…)`, or split the test. `[TRAP]`
2.23.3 **Mystery Guest** — the test depends on external data (a file, a shared database row, a shared
      fixture) the reader cannot see. Symptom: the test is unreadable in isolation and breaks when
      unrelated data changes. `[TRAP]`
2.23.4 **Eager Test** — one test exercising many behaviours. Symptom: the name has "and" in it, and
      a failure in step one hides steps two to five. `[TRAP]`
2.23.5 **Fragile Test / Sensitive Equality** — the test breaks on changes that do not alter behaviour:
      asserting on a whole `toString()`, on field order in JSON, or on an exact log line. `[TRAP]`
2.23.6 **Erratic Test** — the umbrella smell for flakiness, with Meszaros's sub-smells: interacting
      tests, test run war, unrepeatable test, resource optimism, and resource leakage. `[TRAP]`
      `[SPEC]`
2.23.7 **Slow Tests** as a named smell with the causal chain: slow suite → run less often → longer
      feedback → bigger changes → harder debugging. It is a compounding smell, not an inconvenience.
      `[PROVE]`
2.23.8 **Obscure Test** and its sub-forms: eager test, mystery guest, general fixture, irrelevant
      information, hard-coded test data, indirect testing. `[SPEC]`
2.23.9 **General Fixture** — one big setup serving every test, most of which need a fraction of it.
      Symptom: a 60-line `@BeforeEach` and tests that read as unrelated to their setup. `[TRAP]`
2.23.10 **Test Code Duplication** vs **the DRY-in-tests over-correction** (§ 1.5.18) — both are smells,
      and the resolution is builders and named helpers, not inheritance chains. `[TRAP]`
2.23.11 **Conditional Test Logic** — an `if` or a loop in a test (§ 1.5.11). `[TRAP]`
2.23.12 **Test Logic in Production** — a production `if (isTest)` branch, an `@Profile("test")` bean
      that changes behaviour rather than wiring, or a test-only public method. The worst of these,
      because it means production behaves differently from what you tested. `[TRAP]` `[PROVE]`
2.23.13 **Over-specification / Over-mocked Test** — asserting on interactions the contract does not
      require (§ 1.10.27, § 1.4.17). `[TRAP]`
2.23.14 **Testing the mock** — every assertion traces back to something the test stubbed, so the test
      is a tautology. The detection question: *could this test fail if the production code were
      deleted and replaced by a stub?* `[TRAP]` `[PROVE]`
2.23.15 **Testing implementation details** — asserting private state via reflection, asserting the
      number of calls to an internal helper, asserting on a field name. `[TRAP]`
2.23.16 **The 100%-coverage test** — a test written to hit a line with no assertion on the outcome
      (§ 2.15.1). `[TRAP]`
2.23.17 **The getter/setter test** and the constructor test — zero information, real maintenance cost.
      `[TRAP]`
2.23.18 **Happy-path-only** — a suite where every test succeeds, so no error branch, timeout,
      constraint violation or concurrent conflict is exercised. Extremely common and directly
      responsible for production incidents. `[TRAP]` `[PROVE]`
2.23.19 **Ignored/disabled test rot** — `@Disabled` without a reason or a ticket (§ 1.7.6), and the
      metric that catches it: count disabled tests over time. `[METRIC]` `[TRAP]`
2.23.20 **Commented-out tests** — worse than disabled ones, because no report counts them. `[TRAP]`
2.23.21 **The manual step** — a "test" whose instructions include a human action. It is a checklist,
      not a test, and it should be labelled as one. `[TRAP]`
2.23.22 **The shared staging environment as a test dependency** — non-hermetic, contended, and
      permanently flaky. The reason Testcontainers exists. `[PROVE]` `[TRAP]`
2.23.23 **The unreviewed test** — tests excluded from code review, which is how every other smell on
      this list accumulates. `[PROVE]`
2.23.24 **The "we'll add tests later" ticket** as a project smell, with the observation that the ticket
      is never done because the code was not designed to be testable.
2.23.25 **Buggy Test / Production Bug** as Meszaros's project-level smells, and the diagnostic value of
      the ratio between them. `[SPEC]` `[RESEARCH]`
2.23.26 **The smell → cause → fix master table**, all of the above in one place, as the review
      checklist. `[TABLE]`

## §2.24 Choosing — the decision procedures

2.24.1 **Decision 1: what kind of test should this be?** An ordered question list ending in a single
      answer, driven by where the risk lives (§ 1.3.12). `[FLOW]` `[TABLE]`
2.24.2 **Decision 2: what should I fake?** The real → fake → stub → mock ladder (§ 2.11.12) with the
      question that moves you down it. `[FLOW]`
2.24.3 **Decision 3: real database or not?** Query/constraint/lock/migration risk → real engine via
      Testcontainers; mapping-only → embedded is defensible; no persistence in the behaviour → no
      database. `[FLOW]`
2.24.4 **Decision 4: `@SpringBootTest` or a slice or neither?** Wiring risk → slice; cross-layer flow
      → full context; pure logic → neither, and that is the most common correct answer. `[FLOW]`
2.24.5 **Decision 5: assert on state or on interaction?** Observable result → state; invisible side
      effect → interaction; both available → state. `[FLOW]`
2.24.6 **Decision 6: parameterized, property-based, or separate tests?** A finite enumerable set →
      parameterized; a universal claim → property; genuinely different behaviours → separate.
      `[FLOW]`
2.24.7 **Decision 7: contract test, schema check, or integration test?** Two teams → CDC; one team
      both sides → integration; a message topic with many consumers → schema registry. `[FLOW]`
2.24.8 **Decision 8: is this flake a product bug or a test bug?** The triage tree (§ 2.17.17).
      `[FLOW]`
2.24.9 **Decision 9: should this test exist at all?** The deletion criteria, which nobody writes down:
      it duplicates another test's coverage, it asserts an implementation detail, it has never failed
      for a real reason, or it is permanently disabled. **Deleting a test is a legitimate,
      reviewable engineering act.** `[PROVE]` `[TABLE]`
2.24.10 **Decision 10: what do we gate on?** Compile + unit + slice always; integration if under
      budget; contract verification always; E2E and mutation nightly. `[TABLE]`
2.24.11 **The testability properties a design must have**, derived from everything above: dependencies
      injected, time and randomness injected, I/O at the edges, pure domain logic, an interface per
      external system, and no static mutable state. A design with these is cheap to test; a design
      without them cannot be rescued by test tooling. `[TABLE]` `[PROVE]` `[X-REF 22]`
2.24.12 The reverse reading, which is the strongest argument for testing: **the practices that make
      code testable are the practices that make it modular.** Testability is a proxy for coupling.
      `[PROVE]`
2.24.13 **The QuizStakes testing strategy on one page** — the artifact to produce in a design review:
      per-service test tier, what is faked, what is real, what is contract-tested, the never-mock
      list (restriction decisions), the gating tiers, and the budget. `[TABLE]` `[BUILD]`

---

# PART 3 — UNDER THE HOOD

## §3.1 The JUnit Platform launcher and the `TestEngine` SPI

3.1.1 The architecture in one sentence: the **Platform** discovers and executes tests via the
      `TestEngine` SPI; **Jupiter** is one engine among several; the IDE and the build tool talk only
      to the Platform. `[PROVE]`
3.1.2 **`LauncherFactory.create()`** and the `Launcher` interface — `discover(request)` and
      `execute(request, listeners…)` — as the entire public entry point. Everything an IDE does goes
      through these two methods. `[API]` `[SOURCE]`
3.1.3 **`LauncherDiscoveryRequestBuilder`** and the **selector** types, enumerated:
      `ClasspathRootSelector`, `PackageSelector`, `ClassSelector`, `MethodSelector`,
      `UniqueIdSelector`, `FileSelector`, `DirectorySelector`, `ModuleSelector`, `UriSelector`,
      `IterationSelector`. Each is how one caller says "run this". `[TABLE]` `[API]`
3.1.4 **Filters** as the second half of discovery: `ClassNameFilter`, `PackageNameFilter`,
      `TagFilter`, and engine filters (`EngineFilter.includeEngines/excludeEngines`) — plus the rule
      that **`PostDiscoveryFilter`s run after** engines have built their trees. `[API]` `[PROVE]`
3.1.5 The selector/filter distinction proved: selectors *add* candidates, filters *remove* them, so a
      tag filter cannot make a test run that no selector selected. This explains a surprising number
      of "my test doesn't run" cases. `[PROVE]` `[TRAP]`
3.1.6 **The `TestEngine` interface itself** — `getId()`, `discover(EngineDiscoveryRequest, UniqueId)`
      returning a `TestDescriptor`, and `execute(ExecutionRequest)`. Three methods, and everything
      from Jupiter to Cucumber to ArchUnit to jqwik implements them. `[API]` `[SOURCE]`
3.1.7 **Engine registration via `ServiceLoader`**: `META-INF/services/org.junit.platform.engine.TestEngine`
      on the classpath. This is why adding `junit-vintage-engine` as a dependency is the entire
      configuration needed to run JUnit 4 tests. `[CFG]` `[PROVE]`
3.1.8 The engines a Java engineer will actually meet: `junit-jupiter`, `junit-vintage`,
      `jqwik`, `cucumber`, `spock` (via its own runner), `archunit`, `testng` (partially), and
      Kotest. Each gets IDE support for free (§ 1.6.2). `[TABLE]`
3.1.9 **`TestExecutionListener`** on the launcher side — `testPlanExecutionStarted`,
      `dynamicTestRegistered`, `executionSkipped`, `executionStarted`, `executionFinished`,
      `reportingEntryPublished` — and the fact that this, not Jupiter's extension model, is where a
      build tool's reporting hooks in. Do not confuse it with Spring's `TestExecutionListener`
      (§ 3.10), which is an unrelated interface with the same name. `[API]` `[TRAP]`
3.1.10 **`TestPlan`** as the immutable result of discovery — the thing an IDE renders as a tree before
      anything runs, and the reason a syntax error in one test class can break discovery for the
      whole module. `[API]` `[DIAG]`
3.1.11 **`TestIdentifier` and `UniqueId`** — the string form
      `[engine:junit-jupiter]/[class:com.quizstakes.FundsLedgerTest]/[method:reservesStake()]` — and
      what it is for: re-running exactly one test, and correlating a report entry back to a node.
      `[API]` `[WIRE]` `[SOURCE]`
3.1.12 **`LauncherSession` and `LauncherSessionListener`** — the once-per-JVM hook, which is the
      correct place to start a singleton Testcontainer for a whole run rather than a static
      initialiser. Almost nobody knows this exists. `[API]` `[PROVE]` `[BUILD]`
3.1.13 **`LauncherInterceptor`** as the hook for wrapping the entire launcher invocation (for example
      to install a classloader). `[API]` `[RESEARCH]`
3.1.14 **Configuration parameter resolution** in the launcher:
      `LauncherDiscoveryRequest` parameters → system properties → `junit-platform.properties`, and
      `LauncherConfigurationParameters` as the implementation. `[CFG]` `[PROVE]`
3.1.15 **`junit-platform-launcher` now carries the JFR events** that `junit-platform-jfr` used to
      provide — the module removal from § 1.6.6, seen from the inside. `[VERSION-TRAP]` `[RESEARCH]`
3.1.16 **Why this SPI is the reason JUnit 5 was a rewrite rather than a release**: JUnit 4's `Runner`
      was a single extension point that could not compose, so `@RunWith(SpringRunner)` and
      `@RunWith(MockitoJUnitRunner)` were mutually exclusive. The extension model (§ 3.4) exists to
      make composition possible, and the engine SPI exists to make *tooling* independent of it.
      `[PROVE]` `[X-REF 07]`

## §3.2 Discovery and the `TestDescriptor` tree

3.2.1 **`TestDescriptor`** as the tree node: `getUniqueId`, `getDisplayName`, `getTags`, `getSource`,
      `getType` (`CONTAINER`, `TEST`, `CONTAINER_AND_TEST`), `getParent`, `getChildren`, `addChild`,
      `removeFromHierarchy`, `prune`. `[API]` `[SOURCE]`
3.2.2 The tree's shape for a real class, drawn: engine → class descriptor → nested-class descriptor →
      method descriptor → (for a template) invocation descriptors. This is the structure an IDE's
      test tree renders and the structure `UniqueId` encodes. `[FLOW]` `[DIAG]`
3.2.3 **`CONTAINER_AND_TEST`** as the type that explains `@TestFactory` and `@Nested` reporting
      oddities. `[API]`
3.2.4 **`TestSource`** — `ClassSource`, `MethodSource`, `FileSource`, `UriSource` — which is how a
      failure in the report becomes a clickable line in the IDE. `[API]`
3.2.5 **Jupiter's discovery walk**, step by step: resolve selectors → for each candidate class check
      `IsTestClassWithTests` → build a `ClassTestDescriptor` → resolve `@Test`,
      `@TestFactory`, `@TestTemplate`, `@ParameterizedTest`, `@Nested` members → apply
      `PostDiscoveryFilter`s → prune empty containers. `[FLOW]` `[PROVE]`
3.2.6 **`EngineDiscoveryRequestResolver` and `SelectorResolver`** as the modern extension points
      Jupiter uses internally, and the practical consequence: discovery is **classpath scanning plus
      reflection**, which is why it is measurably slow on a large module and why the classpath size
      matters. `[PROVE]` `[NUM]`
3.2.7 **Why "no tests found" happens**, enumerated by cause: engine not on the runtime classpath, the
      class does not match the build's include pattern, no method carries a recognised annotation, an
      `ExecutionCondition` disabled everything, a tag filter excluded it, the class is abstract, or
      the class is not public where the tool requires it. Seven causes, one symptom. `[TABLE]`
      `[DIAG]` `[TRAP]`
3.2.8 **Discovery-time vs execution-time failure**: an exception during discovery is reported against
      the *engine* or the class, not the test, which is why it looks like a build error rather than a
      test failure. `[DIAG]` `[PROVE]`
3.2.9 **`@Nested` resolution and instance nesting**: the outer instance is constructed first and the
      inner class holds a reference to it, so `TestInstances` gives you the whole chain — which is how
      an extension can reach the outer test instance. `[API]` `[PROVE]`
3.2.10 **Pruning** and why an empty container disappears from the report rather than being reported as
      skipped.
3.2.11 The performance consequence worth knowing: discovery cost scales with **classpath entries ×
      candidate classes**, so a monorepo module with 400 dependencies pays a fixed second or two per
      JVM before any test runs — and `forkEvery=1` pays it per class. `[NUM]` `[PROVE]`

## §3.3 Execution — the node hierarchy and the executor service

3.3.1 **`HierarchicalTestEngine`** as the base class Jupiter extends, and the `Node` interface it
      executes: `prepare`, `shouldBeSkipped`, `before`, `execute`, `around`, `after`, `nodeFinished`,
      `cleanUp`. Every lifecycle guarantee in § 1.7 is implemented by these methods. `[API]`
      `[SOURCE]`
3.3.2 **`EngineExecutionContext`** as the immutable state passed down the tree, and how Jupiter's
      `JupiterEngineExecutionContext` carries the `ExtensionRegistry`, the `TestInstancesProvider`
      and the `ExtensionContext` — so a child node sees its parent's extensions but not its
      siblings'. `[PROVE]` `[API]`
3.3.3 **`ExtensionRegistry` inheritance** as the mechanism behind extension inheritance: each node
      creates a *child* registry, so a class-level `@ExtendWith` is visible to every method and a
      method-level one is not visible to siblings. `[PROVE]`
3.3.4 **`Node.around()`** as the wrapping hook that makes `InvocationInterceptor` and
      `@ResourceLock` possible. `[API]`
3.3.5 **`HierarchicalTestExecutorService`** — the SPI that executes nodes, with the two shipped
      implementations `SameThreadHierarchicalTestExecutorService` and
      `ForkJoinPoolHierarchicalTestExecutorService`. In JUnit 6 this is **configurable**
      (`junit.jupiter.execution.parallel.config.executor-service`, default `fork_join_pool`).
      `[API]` `[CFG]` `[VERSION-TRAP]` `[RESEARCH]`
3.3.6 **`ThrowableCollector`** and how a failure in `@BeforeEach` suppresses the test but still runs
      `@AfterEach` — the mechanism behind "why did teardown run when setup failed". `[PROVE]`
      `[API]`
3.3.7 **Failure aggregation**: multiple failures across the test and its `@AfterEach` methods are
      reported with the first as primary and the rest as **suppressed** exceptions. Reading a real
      stack trace with suppressed entries. `[DIAG]` `[PROVE]`
3.3.8 **`TestInstanceFactory`** and the default instantiation path — the constructor is invoked
      reflectively with `ParameterResolver`-resolved arguments, which is why constructor injection
      works in a test class. `[PROVE]` `[API]`
3.3.9 **`TestInstancePostProcessor`** as where field injection happens — this is the hook
      `MockitoExtension` uses to populate `@Mock` fields and Spring uses to autowire. Knowing this
      makes the whole framework legible. `[PROVE]` `[API]`
3.3.10 **`TestInstancePreDestroyCallback`** (JUnit 5.6+, prominent in 6.x) as the counterpart, and what
      it enables: closing per-test resources held in fields. `[API]` `[RESEARCH]`
3.3.11 **`InvocationInterceptor`** — `interceptTestMethod`, `interceptBeforeEachMethod`,
      `interceptTestFactoryMethod`, `interceptDynamicTest`, and the mandatory `invocation.proceed()`.
      The most powerful and most misused extension point (an interceptor that forgets to proceed
      silently skips the test). `[API]` `[TRAP]`
3.3.12 **Reporting from inside a test**: `TestReporter.publishEntry` → `reportingEntryPublished` on the
      launcher listener → the build report. The sanctioned way to attach diagnostic data to a
      failure. `[API]` `[FLOW]`

## §3.4 The Jupiter extension model — resolution order and the store

3.4.1 **The full extension point list, by exact interface name**: `TestInstanceFactory`,
      `TestInstancePostProcessor`, `TestInstancePreDestroyCallback`, `BeforeAllCallback`,
      `BeforeEachCallback`, `BeforeTestExecutionCallback`, `AfterTestExecutionCallback`,
      `AfterEachCallback`, `AfterAllCallback`, `BeforeClassTemplateInvocationCallback`,
      `AfterClassTemplateInvocationCallback`, `ExecutionCondition`, `ParameterResolver`,
      `TestTemplateInvocationContextProvider`, `InvocationInterceptor`,
      `TestExecutionExceptionHandler`, `LifecycleMethodExecutionExceptionHandler`, `TestWatcher`.
      `[TABLE]` `[SOURCE]` `[API]`
3.4.2 **The documented callback order — all 18 steps, in order**, quoted from the reference:
      `BeforeAllCallback` → `@BeforeAll` → `LifecycleMethodExecutionExceptionHandler` (for
      `@BeforeAll`) → `BeforeClassTemplateInvocationCallback` → `BeforeEachCallback` → `@BeforeEach`
      → `LifecycleMethodExecutionExceptionHandler` (for `@BeforeEach`) → `BeforeTestExecutionCallback`
      → **`@Test`** → `TestExecutionExceptionHandler` → `AfterTestExecutionCallback` → `@AfterEach` →
      `LifecycleMethodExecutionExceptionHandler` (for `@AfterEach`) → `AfterEachCallback` →
      `AfterClassTemplateInvocationCallback` → `@AfterAll` →
      `LifecycleMethodExecutionExceptionHandler` (for `@AfterAll`) → `AfterAllCallback`. `[FLOW]`
      `[SOURCE]` `[NUM]` `[RESEARCH]`
3.4.3 The two `ClassTemplate` steps are **new in JUnit 6** and are exactly why the canonical
      interview answer has changed (§ 1.9.15). `[VERSION-TRAP]` `[RESEARCH]`
3.4.4 **`BeforeEachCallback` runs before `@BeforeEach`, but `BeforeTestExecutionCallback` runs after
      it** — a distinction that matters because a `BeforeTestExecutionCallback` can observe the state
      the user's setup produced. This is the pair people get backwards. `[PROVE]` `[TRAP]`
3.4.5 **The wrapping guarantee, quoted**: "any 'before' callbacks implemented by Extension1 are
      guaranteed to execute **before** any 'before' callbacks implemented by Extension2", and the
      'after' callbacks in the mirror order. Extensions nest like an onion. `[SOURCE]` `[PROVE]`
3.4.6 **The non-guarantee, quoted**: "JUnit Jupiter does **not** guarantee the execution order of
      multiple lifecycle methods that are declared within a *single* test class" — the order is
      unspecified but repeatable. A suite that depends on two `@BeforeEach` methods' relative order
      is relying on undefined behaviour. `[SOURCE]` `[TRAP]` `[PROVE]`
3.4.7 **Extension registration, all four mechanisms**: declarative `@ExtendWith` (on class, method,
      field, parameter, or a meta-annotation), programmatic `@RegisterExtension` on a field,
      **automatic** via `ServiceLoader` (`META-INF/services/org.junit.jupiter.api.extension.Extension`)
      gated by the configuration parameter `junit.jupiter.extensions.autodetection.enabled` (default
      **`false`**), and Jupiter's own built-ins. `[TABLE]` `[CFG]` `[NUM]` `[RESEARCH]`
3.4.8 **Extension ordering**: `@Order` on a `@RegisterExtension` field controls the registration order
      (and therefore the wrapping order); `@ExtendWith` order is the declaration order; automatically
      registered extensions come first. Getting this right matters when Spring's and Mockito's
      extensions must nest in a particular way. `[PROVE]` `[API]` `[RESEARCH]`
3.4.9 **Extension inheritance**: a class-level extension is inherited by subclasses and by `@Nested`
      classes — which is what makes `AbstractIntegrationTest` work. `[PROVE]`
3.4.10 **Extensions must be stateless across tests**, because one instance may serve many tests. State
      belongs in the `ExtensionContext.Store`, and a mutable field in an extension is a
      cross-test-pollution bug waiting for parallel execution. `[TRAP]` `[PROVE]`
3.4.11 **`ExtensionContext`** — `getElement`, `getTestClass`, `getTestInstance`, `getTestMethod`,
      `getDisplayName`, `getTags`, `getExecutionException`, `getConfigurationParameter`, `getParent`,
      `getRoot`, `getStore`, `publishReportEntry`. `[API]` `[SOURCE]`
3.4.12 **The context hierarchy** mirrors the descriptor tree: engine → class → nested class → method.
      An extension gets the context for the *level it is invoked at*, and `getParent()`/`getRoot()`
      let it reach up. `[PROVE]`
3.4.13 **`ExtensionContext.Store`** and **`Namespace`** — `Namespace.create(Object… parts)` for
      collision-free keys, `get`, `put`, `getOrComputeIfAbsent`, `remove`, and the crucial property:
      **a store is scoped to its context, and values are inherited from parent contexts for reads but
      written at the current level.** `[API]` `[PROVE]` `[SOURCE]`
3.4.14 **`getOrComputeIfAbsent` as the canonical singleton-per-scope idiom**: put it in the **root**
      context's store and it is computed once per launcher run — which is the correct way to start
      one Testcontainer for the whole suite. `[BUILD]` `[PROVE]`
3.4.15 **`CloseableResource` / `AutoCloseable` in the store**: a stored value implementing it is closed
      when its context ends, in **reverse insertion order**. This is JUnit's resource-management
      mechanism, and it is how a store-based container gets stopped. Note the shift toward plain
      `AutoCloseable` support in recent versions and the
      `junit.jupiter.extensions.testinstantiation.extensioncontextscope.default`-era changes.
      `[API]` `[PROVE]` `[RESEARCH]`
3.4.16 **The root-context store as the run-scoped cache** — with the warning that it lives for the
      whole JVM, so anything you put there is a global. `[TRAP]`
3.4.17 **`ExecutionCondition`** and `ConditionEvaluationResult.enabled/disabled(reason)` — the
      interface behind every `@EnabledIf…` annotation, and the extension point for "skip unless
      Docker is available". `[API]` `[BUILD]`
3.4.18 **`TestExecutionExceptionHandler`** vs **`LifecycleMethodExecutionExceptionHandler`**: the first
      can swallow or translate a test failure, the second does the same for setup/teardown. The
      legitimate use is translating a vendor exception into a readable one; the illegitimate use is
      swallowing failures. `[API]` `[TRAP]`
3.4.19 **`TestWatcher`**'s four methods — `testSuccessful`, `testAborted`, `testFailed`,
      `testDisabled` — and the caveat that it observes but cannot influence. `[API]`
3.4.20 **Spring's `SpringExtension` as a case study**, because it uses almost every hook:
      `BeforeAllCallback` (build the `TestContextManager`), `TestInstancePostProcessor` (autowire the
      instance), `BeforeEachCallback`/`AfterEachCallback` (drive the listeners),
      `ParameterResolver` (inject beans into test method parameters), and `ExecutionCondition`
      (`@EnabledIf` on Spring profiles). `[PROVE]` `[SOURCE]` `[X-REF 07]`
3.4.21 **The Framework 7 change to `SpringExtension`'s store scope**: it now uses a **test-method
      scoped `ExtensionContext`** rather than a class-scoped one, restorable with
      `@SpringExtensionConfig(useTestClassScopedExtensionContext = true)`. Extensions or listeners
      that read Spring's store at class level break. `[VERSION-TRAP]` `[RESEARCH]`
3.4.22 **Extension composition in practice**: `MockitoExtension` + `SpringExtension` +
      `@Testcontainers` on one class, and what determines the order in which they see the test. This
      is the composability JUnit 4 could not provide (§ 3.1.16). `[PROVE]`
3.4.23 **Testing your own extension** with `junit-platform-testkit`:
      `EngineTestKit.engine("junit-jupiter").selectors(…).execute().testEvents().assertStatistics(…)`.
      `[API]` `[BUILD]`

## §3.5 `ParameterResolver` — how injection actually works

3.5.1 **The interface**: `supportsParameter(ParameterContext, ExtensionContext)` and
      `resolveParameter(…)` — two methods that implement every form of injection into a test.
      `[API]` `[SOURCE]`
3.5.2 **`ParameterContext`** — `getParameter`, `getIndex`, `getTarget`, `isAnnotated`,
      `findAnnotation` — and the fact that a resolver decides based on the **annotation or the type**,
      which is the whole design. `[API]`
3.5.3 **Where resolution applies**: test-class constructors, `@Test` methods, all lifecycle methods,
      and `@BeforeTransaction`/`@AfterTransaction` in Spring. Not fields — fields are
      `TestInstancePostProcessor`'s job (§ 3.3.9). `[PROVE]` `[TRAP]`
3.5.4 **Exactly one resolver may claim a parameter.** Two matching resolvers produce a
      `ParameterResolutionException`, and none produces the same exception with a different message.
      Reading both messages. `[DIAG]` `[TRAP]`
3.5.5 **The built-in resolvers**: `TestInfoParameterResolver`, `TestReporterParameterResolver`,
      `RepetitionInfoParameterResolver`, and Jupiter's parameterized-test resolver. `[API]`
3.5.6 **`@TempDir`'s resolver** as a worked example of a resolver that also owns a resource lifecycle
      via the store. `[PROVE]`
3.5.7 **Mockito's parameter resolution** (`@Mock` on a test-method parameter — § 2.10.14) and
      **Spring's** (a bean or `@Autowired` on a test-method parameter) as the two you meet daily.
      `[PROVE]`
3.5.8 **Why parameter injection is better than a field** where it applies: the dependency is visible
      in the signature, it is scoped to the one test that needs it, and it cannot leak. `[PROVE]`
3.5.9 **`ArgumentsAccessor` and `@AggregateWith`** as parameterized-testing's use of the same
      machinery — a resolver that reads from the invocation context rather than the environment.
      `[API]`
3.5.10 **Building a resolver** for the domain: a `@TestClient` annotation that resolves a fully-built
      QuizStakes test client with a seeded id, so every test that needs one gets it in the signature.
      `[BUILD]`

## §3.6 Parallel execution and resource locks

3.6.1 **The whole configuration surface with verified defaults**, as one table:
      `junit.jupiter.execution.parallel.enabled` = **`false`**;
      `junit.jupiter.execution.parallel.mode.default` = **`same_thread`**;
      `junit.jupiter.execution.parallel.mode.classes.default` = **`same_thread`**;
      `junit.jupiter.execution.parallel.config.executor-service` = **`fork_join_pool`**;
      `junit.jupiter.execution.parallel.config.strategy` = **`dynamic`**. `[TABLE]` `[CFG]`
      `[SOURCE]` `[NUM]`
3.6.2 **The dynamic strategy**: parallelism = available processors × `…config.dynamic.factor`
      (default **`1.0`**), with `…dynamic.max-pool-size-factor` and `…dynamic.saturate` (default
      **`true`**). `[CFG]` `[SOURCE]` `[NUM]`
3.6.3 **The fixed strategy**: `…config.fixed.parallelism` (**required**),
      `…config.fixed.max-pool-size`, `…config.fixed.saturate` (default **`true`**). `[CFG]`
      `[SOURCE]`
3.6.4 **The custom strategy**: `…config.custom.class` naming a
      `ParallelExecutionConfigurationStrategy` implementation. `[CFG]` `[API]` `[SOURCE]`
3.6.5 **The two-knob design explained**: `mode.default` governs *nodes in general* and
      `mode.classes.default` governs *top-level classes*, which is what lets you run classes in
      parallel while keeping the methods within each class sequential — the safest useful
      configuration and the one to recommend. `[PROVE]` `[TABLE]`
3.6.6 The four combinations of those two knobs, tabulated with what each actually parallelises and
      what it breaks. `[TABLE]` `[PROVE]`
3.6.7 **`@Execution(SAME_THREAD | CONCURRENT)`** for per-node override, with the documented semantics:
      `SAME_THREAD` forces execution in the parent's thread; `CONCURRENT` executes concurrently
      "unless a resource lock forces execution in the same thread". `[SOURCE]` `[API]`
3.6.8 **`@Isolated`** — quoted: tests in such classes "are executed sequentially without any other
      tests running at the same time". The escape hatch for the one class that mutates a global.
      `[SOURCE]` `[API]`
3.6.9 **`@ResourceLock`** and the built-in `Resources` constants, enumerated exactly:
      `SYSTEM_PROPERTIES`, `SYSTEM_OUT`, `SYSTEM_ERR`, `LOCALE`, `TIME_ZONE` (plus the
      global lock key). `[TABLE]` `[SOURCE]` `[API]`
3.6.10 **`ResourceAccessMode.READ` vs `READ_WRITE`** as a readers-writer lock: many `READ` holders may
      run together, a `READ_WRITE` holder runs alone. This is the mechanism for "these ten tests read
      the same fixture, this one mutates it". `[PROVE]` `[API]`
3.6.11 **The lock's timing, quoted**: "the lock will be acquired before any `@BeforeEach` methods are
      executed and released after all `@AfterEach` methods have been executed" — so setup and teardown
      are inside the critical section. `[SOURCE]` `[PROVE]`
3.6.12 **`@ResourceLock(target = ResourceLockTarget.CHILDREN)`** to apply locking to direct children
      rather than the node itself. `[API]` `[SOURCE]` `[RESEARCH]`
3.6.13 **Custom resource keys** as the real-world use: `@ResourceLock("db:ledger")` on every test that
      truncates the ledger table, so those tests serialise against each other while the rest of the
      suite runs in parallel. This is the single most useful parallelism technique for a Spring
      suite. `[BUILD]` `[PROVE]`
3.6.14 **What breaks under parallel execution**, enumerated: static mutable state, `System.setProperty`
      / `Locale.setDefault` / `TimeZone.setDefault`, `MockedStatic` (thread-scoped, § 2.10.2), shared
      database rows, fixed ports, `SecurityContextHolder` (a `ThreadLocal`), `MDC`, shared
      `@TempDir`, `@MockitoBean` on a shared context, `TestTransaction`, and any test that asserts on
      a global count. `[TABLE]` `[TRAP]`
3.6.15 **Why `@MockitoBean` and parallel execution are a hazard**: the mock is a singleton in a
      **shared cached context**, so two tests stubbing it concurrently interfere. The fix is
      `@ResourceLock` on the bean or `@Execution(SAME_THREAD)` on those classes. `[PROVE]` `[TRAP]`
3.6.16 **`availableProcessors()` in a container** and the JUnit consequence (§ 2.21.14): the dynamic
      strategy reads the JVM's view, which under cgroup quotas may be the host's core count — leading
      to a 64-thread pool on a 2-core runner and timeout cascades. Verify with
      `-XX:ActiveProcessorCount` or a fixed strategy in CI. `[NUM]` `[TRAP]` `[X-REF 19]`
      `[X-REF 06]`
3.6.17 **The work-stealing subtlety**: with `fork_join_pool`, a blocked test thread can have its
      parent's continuation stolen, so a thread-confined assumption (a `ThreadLocal` set in
      `@BeforeAll`) can be violated in ways that look impossible. This is why `saturate` and
      `max-pool-size` exist. `[PROVE]` `[RESEARCH]`
3.6.18 **The adoption procedure**, ordered, because turning parallelism on wholesale reddens a suite:
      enable classes-only concurrency → fix what breaks → add `@ResourceLock` for shared resources →
      only then consider method-level concurrency. `[FLOW]` `[PROVE]`
3.6.19 **The measured payoff**: for a suite dominated by container and context waits (i.e. most Spring
      suites), classes-in-parallel is often a 2–3× wall-clock win at zero infrastructure cost, which
      beats sharding. `[NUM]` `[PROVE]`
3.6.20 **Surefire/Gradle process parallelism vs JUnit thread parallelism**, compared: processes give
      real isolation and duplicate every fixed cost; threads share the JVM, the class data and the
      Spring context and share every hazard in § 3.6.14. `[TABLE]` `[PROVE]`

## §3.7 Mockito internals — bytecode, mock makers, and the agent

3.7.1 The question that organises the section: **how does a Java object with final methods and no
      interface become a mock at runtime?** Two answers, and Mockito ships both. `[PROVE]`
3.7.2 **The subclass mock maker** (`ByteBuddyMockMaker`, default up to Mockito 4): generate a subclass
      at runtime with **Byte Buddy**, override every non-final method to delegate to a
      `MockHandler`, and instantiate it **without calling a constructor** using Objenesis. `[PROVE]`
      `[RESEARCH]`
3.7.3 The constructor-bypass detail and its consequences: field initialisers do not run, so every
      field is at its default value — which is why a spy created from a class rather than an instance
      behaves strangely. `[PROVE]` `[TRAP]`
3.7.4 The subclass maker's limits, derived rather than memorised: you cannot subclass a `final` class,
      you cannot override a `final` or `static` or `private` method, and therefore none of those can
      be mocked. Every "Mockito cannot mock final" claim reduces to this. `[PROVE]`
3.7.5 **The inline mock maker** (`InlineByteBuddyMockMaker`/`InlineDelegateByteBuddyMockMaker`), the
      default since Mockito 5: it uses the **`java.lang.instrument` Instrumentation API** to
      **retransform already-loaded classes**, weaving an advice into every method body so the method
      itself checks whether the receiver is a mock. `[PROVE]` `[RESEARCH]` `[X-REF 06]`
3.7.6 **`MockMethodAdvice`** as the woven code's entry point, with `MockMethodDispatcher` as the
      thread-safe lookup that decides "is this instance a mock, and is this call stubbed?" — and
      `WeakConcurrentMap` holding the mock registry so mocks can be garbage collected. `[SOURCE]`
      `[API]` `[RESEARCH]`
3.7.7 Why retransformation beats subclassing: the check happens **inside the real method**, so
      `final`, `static` and even constructor behaviour become interceptable without changing the type
      hierarchy. `[PROVE]`
3.7.8 The cost side, which explains a real symptom: retransforming classes is slower than generating
      a subclass, so the inline maker has a measurable per-class first-use cost and a larger
      metaspace footprint. This is why some large suites still pin `mock-maker-subclass`. `[NUM]`
      `[PROVE]` `[RESEARCH]`
3.7.9 **`InlineBytecodeGenerator.preload()`** and the type-caching (`TypeCachingBytecodeGenerator`)
      that stops the same class being instrumented repeatedly. `[RESEARCH]`
3.7.10 **How the agent gets attached**: Mockito **self-attaches** the Byte Buddy agent to the running
      JVM at first use. Recent JDKs warn about dynamic agent loading and future ones will refuse it,
      making `-javaagent:byte-buddy-agent.jar` mandatory. This is a live migration issue in 2026.
      `[VERSION-TRAP]` `[DIAG]` `[CFG]` `[RESEARCH]`
3.7.11 **Selecting the maker** — the `mockito-extensions/org.mockito.plugins.MockMaker` resource
      (§ 2.10.16) — read by Mockito's `PluginLoader`, which is a `ServiceLoader`-like mechanism also
      used for `StackTraceCleanerProvider`, `InstantiatorProvider2` and `MockitoLogger`. `[CFG]`
      `[API]` `[RESEARCH]`
3.7.12 **`mockStatic` internals**: the inline maker's advice checks a **thread-local** registry of
      mocked static types, which is precisely why static mocks are thread-scoped and must be closed
      (§ 2.10.1–2.10.2). The implementation explains the API constraint. `[PROVE]`
3.7.13 **`mockConstruction` internals**: the advice intercepts the constructor's exit, registers the
      new instance as a mock, and applies the initialiser — again thread-scoped. `[PROVE]`
3.7.14 **How stubbing is recorded**, step by step, because it explains three separate traps:
      `when(mock.find(1L))` → the *real* proxied call runs the advice → the advice records an
      `Invocation` on the `MockingProgress` **thread-local** → `when()` reads the last invocation and
      returns an `OngoingStubbing` → `thenReturn` attaches an answer. `[FLOW]` `[PROVE]`
3.7.15 The three traps that fall out of that trace: `when` on a spy executes the real method
      (§ 1.10.9); matchers live on a separate thread-local stack and must match the argument count
      (§ 1.10.17); and a mock invoked from another thread during recording corrupts the progress
      state. `[PROVE]` `[TRAP]`
3.7.16 **`ArgumentMatcherStorage`** as that matcher stack, and `validateState()` — invoked by
      `MockitoExtension` after each test — as the thing that turns a corrupted stack into a readable
      error instead of a mystery in the next test. `[PROVE]` `[API]`
3.7.17 **How verification works**: the recorded `InvocationContainer` per mock is searched by the
      `VerificationMode`, which is why `verify` is a query over history rather than a pre-registered
      expectation — the structural difference from EasyMock/JMock's record-replay model. `[PROVE]`
      `[TABLE]`
3.7.18 **`@Mock` field injection**, mechanically: `MockitoExtension` implements
      `TestInstancePostProcessor` and delegates to `MockitoAnnotations`/`DefaultInjectionEngine`,
      which scans the test instance's fields (including inherited ones) and creates mocks with the
      field's name as the mock name. The **mock name is why failure messages say
      `fundsLedgerRepository.save(…)`**. `[PROVE]` `[SOURCE]`
3.7.19 **`@InjectMocks`'s resolution algorithm**, in the order Mockito actually tries it:
      **constructor injection** (the biggest constructor it can satisfy) → **property/setter
      injection** → **field injection**, matching by **type** and, when several fields share a type,
      by **name**. `[FLOW]` `[PROVE]` `[RESEARCH]`
3.7.20 The failure modes that algorithm produces, and the reason § 1.10.25 recommends against it: an
      unsatisfiable constructor leaves fields `null` **silently**; two same-typed fields are matched
      by name, so renaming a field breaks injection; and a new constructor parameter changes which
      constructor is chosen. `[TRAP]` `[PROVE]`
3.7.21 **Mockito's stack-trace cleaning** (`StackTraceCleaner`) — why a Mockito failure's stack starts
      at your test rather than in generated bytecode, and the flag to disable it when you need the
      real frames. `[DIAG]` `[RESEARCH]`
3.7.22 **Serialisable mocks** (`withSettings().serializable()`) and why they need special handling —
      named because a mock stored in a session or a Spring context sometimes must serialise.
      `[RESEARCH]`
3.7.23 **Memory behaviour**: mocks retain every invocation for later verification, so a mock on a hot
      path in a long test accumulates unbounded history — the reason `stubOnly()` exists
      (§ 2.10.26). `[PROVE]` `[NUM]`
3.7.24 **Byte Buddy as the shared substrate**: the same library underlies Mockito's mock makers, many
      APM agents and several Spring features, so a Byte Buddy version conflict on the test classpath
      produces `IllegalStateException: Byte Buddy could not instrument…`. Reading that error.
      `[DIAG]` `[TRAP]` `[X-REF 06]`

## §3.8 The Spring TestContext framework

3.8.1 The object model, in the order the framework builds it: `TestContextManager` → a
      `TestContextBootstrapper` → a `TestContext` holding a `MergedContextConfiguration` → a
      `ContextLoader` that builds the `ApplicationContext` → a chain of `TestExecutionListener`s.
      Six types, and knowing them makes every Spring test error legible. `[FLOW]` `[TABLE]`
      `[API]`
3.8.2 **`TestContextManager`** as the entry point `SpringExtension` drives, with its hook methods:
      `beforeTestClass`, `prepareTestInstance`, `beforeTestMethod`, `beforeTestExecution`,
      `afterTestExecution`, `afterTestMethod`, `afterTestClass`. These map one-to-one onto Jupiter's
      callbacks (§ 3.4.20). `[API]` `[PROVE]`
3.8.3 **`TestContextBootstrapper`** — `DefaultTestContextBootstrapper`,
      `WebTestContextBootstrapper`, and Boot's **`SpringBootTestContextBootstrapper`** — which is
      where `@SpringBootTest`'s magic lives: it finds the primary configuration, adds Boot's
      customizers, and decides the web environment. `[API]` `[PROVE]`
3.8.4 **`ContextCustomizerFactory`** as the extension point registered via `spring.factories`, and
      the customizers that matter for the cache key: `MockitoContextCustomizer`,
      `PropertyMappingContextCustomizer`, `DynamicPropertySourceContextCustomizer`,
      `ImportsContextCustomizer`, and Boot's `ExcludeFilterContextCustomizer`. This is § 2.7.4 seen
      from the inside. `[API]` `[PROVE]` `[RESEARCH]`
3.8.5 **`MergedContextConfiguration` as the cache key**, and specifically its `equals`/`hashCode` over
      the ten attributes of § 2.7.3 — the concrete reason a single extra property forks a context.
      `[PROVE]` `[SOURCE]`
3.8.6 **`ContextLoader` / `SmartContextLoader`** — `DelegatingSmartContextLoader`,
      `AnnotationConfigContextLoader`, `SpringBootContextLoader` — and what each does with `classes`
      vs `locations`. `[API]`
3.8.7 **`CacheAwareContextLoaderDelegate`** as the indirection that consults the `ContextCache` before
      loading — the actual implementation of caching. `[API]` `[PROVE]`
3.8.8 **`DefaultContextCache`** internals: a `LinkedHashMap`-backed LRU with `maxSize` **32**, hit and
      miss counters, and `logStatistics()` — which is exactly what § 2.7.8's DEBUG logging prints.
      `[NUM]` `[SOURCE]` `[PROVE]`
3.8.9 **Eviction closes the context**, running `@PreDestroy` and `close()` on every singleton — the
      mechanism behind § 2.7.6's warning, and the reason a statically-held connection pool can die
      mid-suite. `[PROVE]` `[TRAP]`
3.8.10 **`@DirtiesContext`'s implementation**: `DirtiesContextBeforeModesTestExecutionListener` and
      `DirtiesContextTestExecutionListener` call `markContextDirty`, which **removes and closes** the
      entry. Two listeners exist because "before" and "after" modes must run at different points in
      the chain. `[PROVE]` `[API]`
3.8.11 **The twelve default `TestExecutionListener`s, in exact registration order** (Spring Framework
      7.0.9): `ServletTestExecutionListener`, `DirtiesContextBeforeModesTestExecutionListener`,
      `ApplicationEventsTestExecutionListener`, `BeanOverrideTestExecutionListener`,
      `DependencyInjectionTestExecutionListener`,
      `MicrometerObservationRegistryTestExecutionListener`, `DirtiesContextTestExecutionListener`,
      `CommonCachesTestExecutionListener`, `TransactionalTestExecutionListener`,
      `SqlScriptsTestExecutionListener`, `EventPublishingTestExecutionListener`,
      `MockitoResetTestExecutionListener`. `[TABLE]` `[SOURCE]` `[NUM]` `[RESEARCH]`
3.8.12 Reading that order for meaning, which is the point of memorising it: bean overrides are applied
      **before** dependency injection (so the mock is what gets injected); `@DirtiesContext`-before
      runs before injection and `@DirtiesContext`-after runs late; the transaction starts **after**
      injection; `@Sql` scripts run inside that transaction; mocks are reset **last**. Every ordering
      question about Spring tests is answered by this list. `[PROVE]` `[FLOW]`
3.8.13 **`MockitoResetTestExecutionListener`** as the answer to "why don't my `@MockitoBean` stubbings
      leak between tests" — and its `MockReset.BEFORE`/`AFTER` setting. `[API]` `[PROVE]`
3.8.14 **Listener ordering and merging**: sorted by `AnnotationAwareOrderComparator` (honouring
      `Ordered` and `@Order`), and `@TestExecutionListeners` **replaces** the defaults unless
      `mergeMode = MERGE_WITH_DEFAULTS`. The documented gotcha: declaring one custom listener
      silently removes all twelve. `[SOURCE]` `[TRAP]` `[PROVE]`
3.8.15 **Automatic listener discovery** via `META-INF/spring.factories` under the key
      `org.springframework.test.context.TestExecutionListener`, which is how Spring Boot, Spring
      Security and Spring Cloud Contract each add theirs without you configuring anything. `[CFG]`
      `[SOURCE]` `[PROVE]`
3.8.16 **`BeanOverrideTestExecutionListener` and the bean-override infrastructure**:
      `BeanOverrideHandler`, `BeanOverrideProcessor`, and the `BeanOverrideRegistry` — the Framework
      6.2+ replacement for Boot's old `MockitoPostProcessor`. It is a `BeanFactoryPostProcessor`
      that **replaces a bean definition** (or wraps an instance, for a spy) before the context
      refreshes. `[PROVE]` `[API]` `[RESEARCH]`
3.8.17 Why it must be a `BeanFactoryPostProcessor` and not a runtime swap: singletons are injected at
      refresh time, so a mock introduced later would not reach the collaborators that already hold a
      reference. This is also why `@MockitoBean` cannot avoid changing the cache key. `[PROVE]`
      `[X-REF 07]`
3.8.18 **`@MockitoSpyBean`'s different mechanism**: the real bean is created and then **wrapped** in a
      Mockito spy, which requires the bean to be proxyable — and interacts with Spring's own AOP
      proxies in ways that produce "cannot spy on a JDK proxy" errors. `[PROVE]` `[TRAP]`
      `[X-REF 07]`
3.8.19 **The non-singleton support** added in Framework 7 (§ 1.11.28), and what it changed internally.
      `[VERSION-TRAP]` `[RESEARCH]`
3.8.20 **`TransactionalTestExecutionListener`** internals: it looks up the `PlatformTransactionManager`,
      starts a transaction in `beforeTestMethod`, records the rollback flag, and rolls back in
      `afterTestMethod` — which is why the `@Transactional` attribute support is so limited
      (§ 2.9.5); most attributes are properties of a transaction *definition* the listener does not
      honour. `[PROVE]` `[SOURCE]`
3.8.21 **`TestContextTransactionUtils`** and the transaction-manager lookup order (by name, by
      qualifier, by type, then the primary one) — the mechanism behind "which transaction manager did
      my test use" in a two-datasource application. `[PROVE]` `[RESEARCH]`
3.8.22 **`Boot 4`'s context pausing implementation**: the cache stops `Lifecycle` beans on eviction
      from active use and restarts them on retrieval, publishing `ContextPausedEvent`, with
      `SmartLifecycle#isPauseable()` as the opt-out. Trace the new state machine: active → paused →
      active → closed. `[VERSION-TRAP]` `[FLOW]` `[RESEARCH]`
3.8.23 **AOT test support**: `TestContextAotGenerator` pre-computes context configurations at build
      time, which is what makes native-image tests possible and why dynamic customizers are hostile
      to it (§ 2.7.19). `[RESEARCH]`
3.8.24 **`@BootstrapWith`** as the raw extension point under every `@SpringBootTest`-like annotation —
      named because it is how a framework builds its own test annotation. `[API]`

## §3.9 Spring Boot's slice machinery

3.9.1 The mechanism behind every slice, in one sentence: a **type-filtered auto-configuration
      import** plus a **component-scan filter**, both driven by annotations. `[PROVE]`
3.9.2 **`@AutoConfigureTestSlice`-style composition**, concretely: `@WebMvcTest` is a meta-annotation
      bundling `@BootstrapWith(WebMvcTestContextBootstrapper.class)`, `@OverrideAutoConfiguration`,
      `@TypeExcludeFilters(WebMvcTypeExcludeFilter.class)`, `@AutoConfigureCache`,
      `@AutoConfigureWebMvc`, `@AutoConfigureMockMvc`, and `@ImportAutoConfiguration`. Reading that
      list *is* reading what the slice contains. `[SOURCE]` `[PROVE]` `[RESEARCH]`
3.9.3 **`spring-boot-test-autoconfigure`'s `spring.factories`-style resource files**
      (`META-INF/spring/…AutoConfiguration.imports` per slice) as the actual list of
      auto-configurations each slice applies — the authoritative answer to "what does `@DataJpaTest`
      load". `[CFG]` `[PROVE]` `[RESEARCH]`
3.9.4 **`TypeExcludeFilter`** and the per-slice subclasses (`WebMvcTypeExcludeFilter`,
      `DataJpaTypeExcludeFilter`, …) as the component-scan half — which is why a `@Service` is
      excluded from `@WebMvcTest` but a `@ControllerAdvice` is not. `[PROVE]` `[API]`
3.9.5 **`@OverrideAutoConfiguration(enabled = false)`** as the switch that turns off *all*
      auto-configuration so the slice can import only what it wants. `[API]` `[PROVE]`
3.9.6 **`@ImportAutoConfiguration`** vs `@EnableAutoConfiguration` — explicit list vs discovery — and
      why slices use the first. `[API]` `[X-REF 07]`
3.9.7 **Why slices do not compose** (§ 1.11.18), now derivable: two slices mean two conflicting
      `@OverrideAutoConfiguration` + `@TypeExcludeFilters` sets, and there is no merge rule.
      `[PROVE]`
3.9.8 **`@AutoConfigureTestDatabase`** internals: a `BeanFactoryPostProcessor` that replaces the
      `DataSource` bean definition with an embedded one, and `replace = NONE`/`AUTO_CONFIGURED`/
      `ANY` as the three modes. `[API]` `[PROVE]`
3.9.9 **`TestEntityManager`** as a thin wrapper over `EntityManagerFactory` that obtains the
      *transaction-bound* `EntityManager` — which is why it works inside the test transaction and a
      manually-created `EntityManager` does not. `[PROVE]` `[X-REF 08]`
3.9.10 **`MockRestServiceServer`'s mechanism**: it replaces the `ClientHttpRequestFactory` on the
      builder, so it intercepts below the client API and above the transport (§ 2.12.4). `[PROVE]`
3.9.11 **`MockMvc`'s mechanism**: a real `DispatcherServlet` plus `MockHttpServletRequest`/`Response`
      and a `MockFilterChain`, driven by `TestDispatcherServlet` which also captures the async
      result. `[PROVE]` `[SOURCE]`
3.9.12 **`ConnectionDetails` and `ContainerConnectionDetailsFactory`** — `@ServiceConnection`'s
      implementation: a factory per container type contributes a `ConnectionDetails` bean, and the
      auto-configuration prefers it over properties. This also explains why an unsupported container
      type silently does nothing. `[PROVE]` `[TRAP]` `[RESEARCH]`
3.9.13 **`spring.test.constructor.autowire.mode`** and `@TestConstructor` — the switch that makes test
      class constructor parameters autowired by default, which enables constructor injection in tests
      and removes `@Autowired` fields. `[CFG]` `[API]` `[RESEARCH]`
3.9.14 **`ApplicationContextRunner`'s mechanism**: it builds and closes a context per `run(…)` call
      **without** the TestContext framework or the cache, which is why it is fast and why it is the
      right tool for auto-configuration tests (§ 1.11.32). `[PROVE]` `[X-REF 07]`

## §3.10 Testcontainers internals

3.10.1 **Docker environment discovery**, in order: `DOCKER_HOST` → the default socket
      (`/var/run/docker.sock`) → Docker Desktop's socket → a rootless socket → Colima/Podman paths →
      Testcontainers Cloud, each validated by a ping. The "Could not find a valid Docker environment"
      error is this list exhausting. `[FLOW]` `[DIAG]` `[RESEARCH]`
3.10.2 **`DockerClientFactory`** and the startup checks (`checks.disable`), plus the
      `TESTCONTAINERS_DOCKER_SOCKET_OVERRIDE` and `TESTCONTAINERS_HOST_OVERRIDE` escape hatches for
      DinD and remote daemons. `[CFG]` `[RESEARCH]`
3.10.3 **The container start sequence, step by step**: resolve the image (pull if absent) → create the
      container with labels, exposed ports and environment → start it → run the **wait strategy** →
      execute `containerIsStarted` hooks → expose mapped ports. `[FLOW]` `[PROVE]`
3.10.4 **Port mapping** as the core abstraction: the container's port is published to an **ephemeral
      host port**, retrieved with `getMappedPort(5432)` and `getHost()`. This is why nothing in a
      Testcontainers test may hard-code a port, and why it is parallel-safe by construction.
      `[PROVE]` `[NUM]`
3.10.5 **`getHost()`** replacing `getContainerIpAddress()` in 2.0, and why the value is not always
      `localhost` (Docker Machine, remote daemons, DinD). `[VERSION-TRAP]` `[RESEARCH]`
3.10.6 **The labels Testcontainers attaches** — `org.testcontainers=true`, a session id, a reuse hash
      — and the fact that **Ryuk matches on these labels**. Labels are the whole cleanup contract.
      `[PROVE]` `[WIRE]` `[RESEARCH]`
3.10.7 **Ryuk's protocol**, mechanically: Testcontainers starts `testcontainers/ryuk` as a
      **privileged** container with the Docker socket bound, opens a TCP connection to it, and sends
      **label filters** ("the death note"); Ryuk holds the connection and, once it drops, waits a
      short grace period (~10 s) then deletes every matching container, network and volume. `[FLOW]`
      `[PROVE]` `[RESEARCH]`
3.10.8 Why the design is a *connection* rather than a shutdown hook: a `kill -9`, an IDE stop button
      or a CI timeout never runs your shutdown hook, but it does close the socket. This is the
      elegant part and worth being able to explain. `[PROVE]`
3.10.9 **`ResourceReaper`** on the Java side as the class that manages that connection and the
      registered filters. `[API]` `[RESEARCH]`
3.10.10 **Disabling Ryuk** (`ryuk.disabled=true` / `TESTCONTAINERS_RYUK_DISABLED=true`, env wins) and
      the two legitimate reasons: a platform that forbids privileged containers, and a CI runner that
      destroys the whole VM anyway. `[CFG]` `[SOURCE]`
3.10.11 The consequence of disabling it without an alternative: leaked containers, then a full Docker
      disk, then unrelated failures across the whole runner. `[TRAP]` `[DIAG]`
3.10.12 **Reuse internals**: `withReuse(true)` makes Testcontainers compute a **hash of the container
      configuration**, label the container with it, and on the next run look for a running container
      with the same hash instead of creating one. The hash is why "the configuration must be the
      same" (§ 2.6.18) is a mechanism, not a guideline. `[PROVE]` `[SOURCE]`
3.10.13 Reuse's interaction with Ryuk: reusable containers are **labelled to be excluded** from the
      reaper, which is exactly why they survive — and exactly why they leak. `[PROVE]`
3.10.14 **`~/.testcontainers.properties`** as the per-developer configuration file, and the deliberate
      decision that `testcontainers.reuse.enable` is **not** readable from the classpath — so a
      developer opts in, a repository cannot opt in on their behalf, and CI cannot accidentally
      inherit it. `[SOURCE]` `[PROVE]` `[CFG]`
3.10.15 **`@Testcontainers`'s implementation**: a JUnit extension implementing `BeforeAllCallback`/
      `AfterAllCallback`/`BeforeEachCallback`/`AfterEachCallback` that reflects over `@Container`
      fields and starts/stops them by static-ness. `[PROVE]` `[API]`
3.10.16 **`@Testcontainers(disabledWithoutDocker = true)`** as an `ExecutionCondition` — the clean way
      to skip integration tests on a machine without Docker rather than failing. `[API]` `[PROVE]`
3.10.17 **Wait strategies as the readiness contract**, and `WaitAllStrategy` /
      `AbstractWaitStrategy.withStartupTimeout`; the JDBC modules layer their own strategy (a real
      `SELECT 1`), which is why `PostgreSQLContainer` is more reliable than a `GenericContainer` on
      port 5432. `[PROVE]`
3.10.18 **`ContainerState` and lifecycle hooks**: `containerIsCreated`, `containerIsStarting`,
      `containerIsStarted`, `containerIsStopping`, `containerIsStopped` — the extension points a
      custom container class implements (and where `PostgreSQLContainer` runs its init script).
      `[API]`
3.10.19 **`ImageNameSubstitutor`** and `TESTCONTAINERS_HUB_IMAGE_NAME_PREFIX` — the mechanism for
      redirecting every image to a corporate registry mirror, which is the answer to Docker Hub rate
      limits in CI. `[CFG]` `[PROVE]` `[X-REF 19]`
3.10.20 **`DockerImageName.asCompatibleSubstituteFor`** — the mechanism behind "this image is not
      supported by this module" and how to override it safely. `[API]` `[DIAG]`
3.10.21 **The JDBC URL driver** (`jdbc:tc:…`) as a real JDBC `Driver` implementation that starts a
      container on `connect()` — which explains `TC_DAEMON` and why it can be used from a
      non-Java tool. `[PROVE]`
3.10.22 **Startup cost decomposition**, measured: image pull (network-bound, once), container create
      (~50–150 ms), start (~200 ms), wait strategy (the dominant term — Postgres recovery, Kafka
      broker election), plus Ryuk's one-time ~1 s. Knowing which term dominates tells you what to
      optimise. `[NUM]` `[TABLE]` `[RESEARCH]`
3.10.23 **The 2.0 internals changes** to be aware of on upgrade: module-per-package layout, the
      removal of the JUnit 4 `TestRule` implementation (which is *why* `@Rule` support disappeared),
      and mandatory explicit image names (which removes a class of "it pulled the wrong version"
      bugs). `[VERSION-TRAP]` `[PROVE]` `[RESEARCH]`
3.10.24 **Testcontainers Cloud / `TESTCONTAINERS_CLOUD_TOKEN`** as the managed remote-daemon option,
      named with the commercial caveat. `[CURRENCY]` `[RESEARCH]`

## §3.11 JaCoCo internals

3.11.1 **On-the-fly instrumentation** as the mechanism, quoted: JaCoCo "creates instrumented versions
      of the original class definitions" at class-load time using a Java agent and the **ASM**
      library — an approach chosen because it is "very fast, can be implemented in pure Java and
      works with every Java VM". `[SOURCE]` `[PROVE]` `[X-REF 06]`
3.11.2 **The probe array**: JaCoCo inserts a `boolean[]` into each instrumented class, and each probe
      is a single array store at a strategic point in the control flow. Coverage is then "which
      probes are true". `[SOURCE]` `[PROVE]`
3.11.3 **Probe placement** — probes go at the *ends* of basic blocks rather than on every instruction,
      which is why instruction counts are derived from a small number of probes and why the runtime
      overhead is low. `[PROVE]` `[RESEARCH]`
3.11.4 **The class identity**: a **CRC64 hash of the raw class definition** identifies each class, so
      coverage data can be matched to bytecode even across multiple classloaders (OSGi). The
      documentation notes there is no cryptographic guarantee against collisions, only a very low
      probability. `[SOURCE]` `[NUM]` `[PROVE]`
3.11.5 The consequence that produces a real, confusing error: if the class file used for the report
      differs by even one byte from the one that ran, the ids do not match and coverage shows as
      zero. Recompiling with different flags, or reporting against a shaded jar, does exactly this.
      `[TRAP]` `[DIAG]` `[PROVE]`
3.11.6 **How the instrumented code reaches the runtime without a classloader dependency**: JaCoCo
      retrieves the probe array through a trick using **only JRE APIs — `Object.equals()`** — because
      a direct reference to a JaCoCo class would break in restricted or isolated classloaders. This
      is the cleverest detail in the tool. `[SOURCE]` `[PROVE]`
3.11.7 **Agent class renaming**: the agent's own classes are relocated to
      `org.jacoco.agent.rt_<randomid>` to avoid clashing with an application's own ASM or JaCoCo
      dependency. `[SOURCE]` `[PROVE]`
3.11.8 **Offline instrumentation** as the alternative for environments where an agent cannot run, and
      its cost (a separate instrumented artifact and a runtime dependency). `[RESEARCH]`
3.11.9 **The `.exec` file** as the output — probe data plus class ids, mergeable across JVMs — and the
      report step that combines it with the class files and the sources. Three inputs, and the report
      is wrong if any one is stale. `[FLOW]` `[PROVE]`
3.11.10 **Where branch coverage comes from**: probes on each outgoing edge of `if` and `switch`
      instructions, which is precisely why exception edges are excluded (they are not branch
      instructions in the bytecode). § 2.15.7's limitation is a consequence of the implementation,
      not a choice. `[PROVE]`
3.11.11 **Why source formatting distorts line coverage**: lines map to instructions via the
      `LineNumberTable` debug attribute, so a multi-statement line is one line with several
      instructions, and a lambda body is attributed to its declaration line. Compile without `-g` and
      line coverage disappears entirely. `[PROVE]` `[SOURCE]`
3.11.12 **Filters** applied at report time for synthetic and generated constructs: default
      constructors, `finally` block duplication, `enum` `values`/`valueOf`, string-switch bridging,
      Lombok's `@Generated`, and record accessors. Each exists because bytecode does not correspond
      to source. `[TABLE]` `[SOURCE]` `[RESEARCH]`
3.11.13 The documented consequence, quoted: "some Java language constructs get compiled to byte code
      that produces unexpected highlighting results, especially in case of implicitly generated code
      like default constructors or control structures for finally statements". This is why a
      `try/finally` shows partial coverage on a line with no branch in it. `[SOURCE]` `[DIAG]`
3.11.14 **Cyclomatic complexity from bytecode**: `v(G) = B − D + 1` computed over branch instructions,
      with the documented note that exception handling does not increase complexity — so a
      `try/catch`-heavy method reads as simple. `[SOURCE]` `[NUM]` `[PROVE]`
3.11.15 **The `${argLine}` mechanism**: the `prepare-agent` goal sets a property that Surefire's
      `argLine` must include, which is why hard-coding `argLine` silently disables coverage and why
      the report is then empty. The most common JaCoCo misconfiguration. `[CFG]` `[TRAP]` `[DIAG]`
3.11.16 **Runtime overhead**, honestly: typically low single-digit percent for the agent, plus report
      generation time — small enough that leaving it on for the whole suite is normal, unlike
      mutation testing. `[NUM]` `[PROVE]`
3.11.17 **Coverage under parallel execution and multiple forks**: probe arrays are per-class-per-JVM
      and merged from multiple `.exec` files, which works — and silently loses data if a fork is
      killed before it writes. `[PROVE]` `[TRAP]`
3.11.18 **`dump`/`reset` over TCP** (`output=tcpserver`) for collecting coverage from a long-running
      or remote JVM — the mechanism behind "coverage from a deployed environment". `[CFG]`
      `[RESEARCH]`

## §3.12 PIT internals

3.12.1 **The pipeline**, step by step: analyse the classes → run the test suite once with **line-level
      coverage** instrumentation and record which tests cover which lines and how long each took →
      generate mutants → for each mutant, start (or reuse) a **minion JVM**, load the mutated class,
      and run **only the tests that cover the mutated line**, fastest first → stop at the first
      failure (the mutant is killed). `[FLOW]` `[PROVE]`
3.12.2 **Coverage-driven test selection** as the central optimisation, and the arithmetic that shows
      why it is essential: without it, cost is `mutants × tests`; with it, cost is
      `Σ over mutants of (tests covering that line)`, which for well-factored code is a tiny
      fraction. `[PROVE]` `[NUM]`
3.12.3 **Fastest-test-first ordering** as the second optimisation: the goal is to kill the mutant, so
      running the cheapest covering test first minimises expected cost. `[PROVE]`
3.12.4 **Mutant timeouts**: `timeoutConstant` + `timeoutFactor` × the test's recorded normal runtime,
      and the rule that a **timed-out mutant counts as killed** (the mutation caused a non-terminating
      loop, which a test *did* detect). `[CFG]` `[PROVE]` `[NUM]` `[RESEARCH]`
3.12.5 **Bytecode-level mutation** as the design choice, with its consequences: no source parsing,
      language-version independence, and mutants that do not correspond to any source edit (which is
      why a report sometimes shows a mutation you cannot express in Java). `[PROVE]` `[TRAP]`
3.12.6 **How each default operator is implemented at the bytecode level**, for the three most
      instructive: Negate Conditionals swaps the jump opcode (`IFEQ`↔`IFNE`, `IF_ICMPLT`↔`IF_ICMPGE`);
      Conditionals Boundary swaps `IF_ICMPLT`↔`IF_ICMPLE`; Void Method Calls removes the
      `INVOKEVIRTUAL` and pops its arguments. `[SOURCE]` `[PROVE]` `[RESEARCH]`
3.12.7 **Return-value mutators as a family** (Empty/False/True/Null/Primitive Returns) replacing the
      older `ReturnValsMutator`, and why they were split: the older single operator produced
      unkillable and confusing mutants. A version-history detail that explains an old blog's mutator
      list. `[VERSION-TRAP]` `[RESEARCH]`
3.12.8 **Why `Inline Constant` and `Remove Conditionals` are off by default**: they generate very
      large numbers of mutants, many equivalent, on constant-heavy code. Turning them on is a
      deliberate cost decision. `[PROVE]`
3.12.9 **Minion JVM reuse and isolation**: PIT runs mutants in child JVMs with a custom classloader so
      a mutated class can be loaded repeatedly; a mutant that corrupts static state can poison
      subsequent mutants, which is why isolation exists and why it costs. `[PROVE]` `[RESEARCH]`
3.12.10 **Incremental analysis (`withHistory`)**: a history file records each mutant's previous status
      and the hash of the class and the covering tests, so unchanged code is not re-mutated. This is
      what makes per-commit mutation testing possible (§ 2.16.13). `[CFG]` `[PROVE]`
3.12.11 **`scmMutationCoverage`** using the SCM status to mutate only changed/added files —
      the same idea driven by git rather than a history file. `[CLI]` `[X-REF 17]`
3.12.12 **Why PIT struggles with Spring contexts**: each mutant run pays the context startup, so a
      mutation run over `@SpringBootTest`-covered code is arithmetically hopeless. This is the
      mechanical reason for § 2.16.14's "domain layer only" recommendation. `[PROVE]` `[NUM]`
3.12.13 **`pitest-junit5-plugin`** as a required separate dependency for a Jupiter suite, because PIT's
      core speaks to test frameworks through a plugin SPI. Omitting it produces "no tests found".
      `[CFG]` `[DIAG]` `[TRAP]`
3.12.14 **`pitest-descartes`** as an alternative mutation engine plugged into the same pipeline —
      extreme mutation (whole method bodies replaced), far fewer mutants, coarser signal. `[RESEARCH]`
3.12.15 **The report format**: HTML with per-line mutation annotations plus an XML/CSV output for CI
      consumption, and the mutation-score threshold gate. `[DIAG]` `[CFG]`

## §3.13 AssertJ and assertion-library internals

3.13.1 **The type-directed design**: `Assertions.assertThat` is an overloaded family returning
      type-specific assertion classes (`AbstractBigDecimalAssert`, `AbstractIterableAssert`, …), all
      extending `AbstractAssert<SELF, ACTUAL>` with the self-type generic that makes fluent chaining
      type-safe. This generic trick is worth understanding on its own. `[PROVE]` `[API]`
      `[X-REF 03]`
3.13.2 **`Objects`/`Iterables`/`Strings` internal helper classes** and `Failures`/`WritableAssertionInfo`
      as the failure-message machinery — the reason messages are consistent across assertion types.
      `[RESEARCH]`
3.13.3 **`usingRecursiveComparison` internals**: field-by-field graph traversal by reflection with
      cycle detection, configurable comparators per type and per field, and the resulting
      `ComparisonDifference` list that produces the verbose failure output. `[PROVE]` `[DIAG]`
3.13.4 Its two failure modes that follow from the mechanism: **new fields are silently included**
      (§ 1.8.11), and a lazily-initialised JPA proxy in the graph triggers loading or throws
      `LazyInitializationException` inside an assertion. `[TRAP]` `[X-REF 08]`
3.13.5 **`SoftAssertions`** internals: a proxy per assertion object collecting failures into an error
      list, with `assertAll()` throwing a `SoftAssertionError` — which is why a soft assertion needs
      `assertSoftly` or an explicit `assertAll` and silently passes without it. `[PROVE]` `[TRAP]`
3.13.6 **JUnit's `assertAll`** by contrast collects `Executable`s eagerly and throws
      `MultipleFailuresError` — no proxying, so it cannot chain. The two mechanisms compared.
      `[TABLE]` `[PROVE]`
3.13.7 **Custom assertion classes** — extending `AbstractAssert`, using `isNotNull()` then
      `failWithMessage(…)` — and the `assertj-assertions-generator` that writes them from your domain
      classes. `[BUILD]` `[API]`
3.13.8 **Why `assertEquals(expected, actual)`'s order is unenforceable** and AssertJ's is: with one
      argument and a method name that says `isEqualTo`, there is no order to get wrong. A small,
      elegant example of API design removing a class of error. `[PROVE]`
3.13.9 **`assertj-core` 3.27.7 as a security patch** (CVE-2026-24400 addressed in the 3.27.7 line per
      the openSUSE advisory) — a reminder that test-scope dependencies are still dependencies and
      still get scanned. `[CURRENCY]` `[RESEARCH]` `[X-REF 13]`
3.13.10 **AssertJ 4.0 on the horizon** (4.0.0-M1, Mar 2025) — do not write against it yet, but know
      it is coming. `[VERSION-TRAP]` `[CURRENCY]` `[RESEARCH]`

## §3.14 Proofs

3.14.1 **[PROVE] The suite-level flake probability**: with *n* independent tests each failing
      spuriously with probability *p*, the build's spurious failure rate is `1 − (1−p)^n`. Work the
      numbers for `p = 0.0005, n = 2000` → 63.2%, and note the linear-in-`np` approximation for small
      `p`. `[NUM]`
3.14.2 **[PROVE] Why retry masks rather than fixes**: a test with per-run failure probability *p*
      retried *k* times fails with probability `p^k`, so a 5% flake retried three times reports a
      0.0125% failure rate — the *test* looks fixed while the underlying race is unchanged. The
      arithmetic is the argument. `[NUM]`
3.14.3 **[PROVE] The context-count cost model**: `T = C·b + n·t` where `C` is distinct
      configurations, `b` the build cost, `n` tests, `t` per-test cost. Differentiate the developer's
      intuition ("fewer tests") from the real lever (`C`), and show the § 2.1.4 numbers.
3.14.4 **[PROVE] Superlinearity past the cache limit**: with `C > 32` and LRU eviction under an
      interleaved class order, the number of context *builds* can exceed `C`. Construct the
      worst-case access sequence that rebuilds every context on every access (the classic LRU
      thrashing sequence). `[NUM]`
3.14.5 **[PROVE] Amdahl's law for a test suite** (§ 2.1.6), with the serial fraction identified as
      container startup plus discovery.
3.14.6 **[PROVE] The combinatorial explosion of testing through layers** (§ 1.3.4): `Π b_i` versus
      `Σ b_i` for *k* layers with `b_i` branches each, worked for a 3-layer service with 4/3/5
      branches — 60 end-to-end cases versus 12 unit cases. `[NUM]`
3.14.7 **[PROVE] Path coverage is infeasible**: 2^n paths for *n* independent conditions, unbounded
      for a loop. Contrast with MC/DC's `n+1` test minimum, which is why avionics standards chose it.
      `[NUM]`
3.14.8 **[PROVE] Line coverage does not imply branch coverage**: the `if (a && b)` single-line
      counterexample, with the four condition combinations and the one test that reaches 100% line
      coverage. `[NUM]`
3.14.9 **[PROVE] Branch coverage does not imply correctness**: a test that executes both branches
      with no assertion, and a mutant that survives it. The bridge from § 2.15 to § 2.16.
3.14.10 **[PROVE] 100% mutation score is unattainable in general**: equivalent mutants exist and
      detecting them reduces to program equivalence, which is undecidable. Therefore mutation score
      is a comparative metric, not a target.
3.14.11 **[PROVE] Why mutation score is hard to game**: the only way to kill a mutant is an assertion
      that distinguishes the mutated behaviour, whereas the only way to raise coverage is to execute
      a line. Contrast the incentive gradients. `[PROVE]`
3.14.12 **[PROVE] The mutant/real-fault coupling result** as evidence rather than assertion: Just et
      al.'s 357 faults, 73% coupling, correlation independent of coverage — and what "independent of
      coverage" means statistically (they controlled for it). `[STUDY]` `[NUM]`
3.14.13 **[PROVE] Test order dependence is a graph property**: with a polluter *P* and a victim *V*,
      the failure depends only on whether *P* precedes *V*, so random ordering finds it with
      probability ~0.5 per run — hence `1 − 0.5^k` over *k* randomised runs. Randomised ordering is
      therefore a *very* effective detector. `[NUM]`
3.14.14 **[PROVE] Sharding's diminishing returns**: `T(N) = f + S/N` with fixed cost `f` per shard,
      minimised in *cost* terms differently from *latency* terms; find the *N* past which added
      shards buy under 10%. `[NUM]`
3.14.15 **[PROVE] Little's Law applied to the CI queue** (§ 2.1.7), with the runner-count conclusion.
3.14.16 **[PROVE] Why a `MockMvc` test cannot prove an endpoint works**: enumerate the layers it
      exercises versus the layers a request traverses in production, and identify the set difference
      (servlet container, HTTP parsing, TLS, connection management, filters registered outside the
      slice). The gap is the proof. `[TABLE]`
3.14.17 **[PROVE] Why a mocked repository cannot prove a transaction rolls back**: with no real
      transaction manager there is no transaction, so the assertion is about the mock's recorded
      calls, not about the database. State the invariant being claimed and show nothing in the test
      establishes it.
3.14.18 **[PROVE] Why the transactional test hides the flush**: trace the persistence context's
      write-behind semantics to the point where the SQL would be issued, and show that rollback
      elides it. `[X-REF 08]`
3.14.19 **[PROVE] Why a passing concurrent test is weak evidence**: the interleaving space of *k*
      operations across *t* threads is combinatorially large, execution samples it
      non-uniformly (the scheduler is not adversarial), and the JMM permits reorderings that a
      strongly-ordered x86 will not exhibit. Therefore green means "not observed", not "impossible".
      `[X-REF 05]`
3.14.20 **[PROVE] Why the extension wrapping order must be an onion**: show that any other order
      breaks the resource-acquisition invariant — an extension that acquires in `before` must release
      in `after` *after* every inner extension has finished using it. The guarantee is forced by
      resource safety, not chosen for elegance.
3.14.21 **[PROVE] Why the store must be scoped and inherited-for-read**: an extension needs per-test
      state and per-class state simultaneously; a flat map cannot provide both without collisions,
      and a non-inheriting scope cannot share the class-level container.
3.14.22 **[PROVE] Why `@MockitoBean` must change the cache key**: a cached context has already
      injected its singletons; replacing a bean afterwards cannot reach existing references.
      Therefore the mock must be present at refresh, therefore the configuration differs, therefore
      the key differs. A three-step argument that settles the question. `[X-REF 07]`
3.14.23 **[PROVE] Why Ryuk's connection-based design is strictly better than a shutdown hook**:
      enumerate the termination modes (normal exit, exception, `System.exit`, `SIGKILL`, IDE stop, CI
      timeout, OOM kill) and show the hook covers the first three while the socket covers all seven.
      `[TABLE]`
3.14.24 **[PROVE] Why coverage-driven test selection makes mutation testing tractable** (§ 3.12.2),
      with the arithmetic for a real module: 800 mutants × 400 tests = 320,000 test executions
      naively, versus ~4,000 with selection at an average of 5 covering tests per line. `[NUM]`
3.14.25 **[PROVE] Why the inline mock maker can mock `final` methods and the subclass maker cannot**:
      one rewrites the method body, the other relies on dynamic dispatch, and `final` removes dynamic
      dispatch. The capability difference is a direct consequence of the mechanism.
3.14.26 **[PROVE] Why JaCoCo's class id must be content-derived**: a name-based id cannot distinguish
      two versions of a class across classloaders, and coverage attributed to the wrong bytecode is
      worse than no coverage. Then show why this makes stale-class-file reports read as zero.
3.14.27 **[PROVE] Why a fake needs a shared contract test**: without one, the fake's behaviour is
      unconstrained, so every test using it verifies against an assumption rather than a
      specification — the same failure as a stubbed provider in § 2.12.12. The fake and the real
      implementation must be shown to satisfy the same tests.
3.14.28 **[PROVE] Why "don't mock what you don't own" follows from stability, not ownership**: model
      the cost of a test as `P(interface changes) × (tests to fix)`, and show that ownership is a
      proxy for the first term. This also explains the `Clock` exception (§ 1.4.14).

## §3.15 The failure catalogue — symptom → cause → diagnostic → fix

3.15.1 The catalogue's purpose: a symptom-indexed lookup, because in practice you meet the symptom
      first. Every entry names the **diagnostic** as well as the fix. `[TABLE]`
3.15.2 **"No tests were found"** — the seven causes of § 3.2.7, with the diagnostic (check the runtime
      classpath for the engine, check the include pattern, run with `-X`). `[DIAG]`
3.15.3 **"0 tests run, build successful"** — a filtered-out tag or a skipped module; fix with
      `failIfNoTests`. `[DIAG]`
3.15.4 **`NoSuchBeanDefinitionException` at context startup** — the slice does not contain the bean;
      the fix is `@MockitoBean` or the right slice. `[DIAG]`
3.15.5 **"Unable to find a @SpringBootConfiguration"** — the test package is above the application
      class (§ 1.11.4). `[DIAG]`
3.15.6 **`IllegalStateException: Failed to load ApplicationContext`** — read to the **root cause at
      the bottom**; the top of the stack is never the problem. `[DIAG]`
3.15.7 **A suite that gets slower with each added test class** — context forking (§ 2.7.9); diagnose
      with the cache statistics. `[DIAG]` `[METRIC]`
3.15.8 **A suite that fails only when run whole** — order dependence or shared state; diagnose with
      the isolation bisect (§ 2.17.8). `[DIAG]`
3.15.9 **A test that fails only in CI** — resource contention, parallelism, timezone, or a missing
      environment assumption (§ 2.17.18). `[DIAG]`
3.15.10 **`UnnecessaryStubbingException`** — a drifted test; the fix is to delete the stubbing, not to
      go lenient (§ 1.10.8). `[DIAG]`
3.15.11 **`PotentialStubbingProblem`** — argument mismatch; read the listed registered stubbings
      against the actual call. `[DIAG]`
3.15.12 **`InvalidUseOfMatchersException` in an apparently unrelated test** — a corrupted matcher stack
      from an earlier misuse (§ 1.10.18). `[DIAG]`
3.15.13 **`WrongTypeOfReturnValue`** — usually `when()` on a spy invoking the real method, or a
      mismatched generic. `[DIAG]`
3.15.14 **`NotAMockException`** — verifying a real object, typically because `@InjectMocks` overwrote a
      field or the mock was never initialised. `[DIAG]`
3.15.15 **"Mockito cannot mock this class"** — a `final` class under `mock-maker-subclass`, or an
      agent-attachment failure (§ 3.7.10). `[DIAG]`
3.15.16 **`IllegalStateException: Could not initialize plugin: MockMaker`** — a Byte Buddy or Objenesis
      version conflict (§ 3.7.24). `[DIAG]`
3.15.17 **"Could not find a valid Docker environment"** — the discovery list of § 3.10.1 exhausted.
      `[DIAG]`
3.15.18 **A Testcontainers wait-strategy timeout** — read the container's captured log tail, which is
      in the exception. `[DIAG]`
3.15.19 **Docker disk exhaustion on a developer machine** — leaked reusable containers or a disabled
      Ryuk (§ 3.10.11); `docker system prune` plus a policy. `[CLI]` `[DIAG]`
3.15.20 **Docker Hub rate limit in CI** — `TESTCONTAINERS_HUB_IMAGE_NAME_PREFIX` and a registry mirror
      (§ 3.10.19). `[DIAG]`
3.15.21 **An empty JaCoCo report** — the `${argLine}` clobbered (§ 3.11.15) or stale class files
      (§ 3.11.5). `[DIAG]`
3.15.22 **Coverage inexplicably zero for one module** — an aggregate-report configuration issue
      (§ 2.15.15). `[DIAG]`
3.15.23 **A test that passes but the entity was never saved** — the transactional test's missing flush
      (§ 2.9.7). `[DIAG]`
3.15.24 **A `@TransactionalEventListener` that never fires** — no commit in a rolled-back test
      (§ 2.9.11). `[DIAG]`
3.15.25 **A `@SpringBootTest(RANDOM_PORT)` test that leaves rows behind** — the documented
      no-rollback-across-threads behaviour (§ 2.9.14). `[DIAG]`
3.15.26 **`LazyInitializationException` inside an assertion** — a recursive comparison walking a JPA
      proxy (§ 3.13.4). `[DIAG]`
3.15.27 **A `BigDecimal` assertion failing on visibly equal numbers** — scale (§ 1.8.14). `[DIAG]`
3.15.28 **A `java.time` assertion failing by nanoseconds** — database precision truncation
      (§ 1.8.17). `[DIAG]`
3.15.29 **A test that hangs forever** — an unbounded `Future.get()`, an executor that was never shut
      down, or a container waiting on a strategy with no timeout; diagnose with a thread dump on the
      test JVM. `[DIAG]` `[CLI]` `[X-REF 06]`
3.15.30 **The test JVM being OOM-killed** — `forkCount` × heap exceeding the container limit
      (§ 1.12.13), or unbounded mock invocation history (§ 3.7.23). `[DIAG]` `[X-REF 19]`
3.15.31 **A `NoSuchMethodError` in a test only** — a duplicated library at two versions on the test
      classpath (`hamcrest-core`, Byte Buddy, Jackson); diagnose with `mvn dependency:tree`.
      `[DIAG]` `[CLI]`
3.15.32 **Parallel execution reddening a previously green suite** — the § 3.6.14 list, in the order to
      check it. `[DIAG]`
3.15.33 **The master failure table**, all of the above in one lookup, with the diagnostic command for
      each. `[TABLE]`

## §3.16 Version history and the migration surface

3.16.1 **JUnit's lineage** with what each generation changed and why: JUnit 3 (naming convention,
      `TestCase` inheritance), JUnit 4 (annotations, `Runner`, `@Rule`), JUnit 5 (Platform + Jupiter,
      the extension model, Java 8), **JUnit 6** (unified versioning, Java 17, module removals,
      `@ParameterizedClass`). `[TABLE]` `[NUM]`
3.16.2 **The JUnit 5 → 6 migration checklist**: Java 17 baseline, single BOM version, remove
      `junit-platform-runner` usages, re-check CSV parsing behaviour (FastCSV), verify custom
      extensions against the new callback list and store scoping, and audit `@Nested` ordering
      assumptions. `[FLOW]` `[VERSION-TRAP]` `[RESEARCH]`
3.16.3 **JUnit 5's own notable increments** worth knowing because most code is still on them:
      `@TempDir`, `@Timeout`, `@Nested` improvements, `ClassOrderer` (5.8), `@FieldSource` and
      `@ParameterizedTest` argument-source improvements (5.11+), `TestInstancePreDestroyCallback`
      (5.6), `LauncherSessionListener` (1.8). `[TABLE]` `[CURRENCY]` `[RESEARCH]`
3.16.4 **Mockito's lineage**: Mockito 1 (`Matchers`, `anyObject`), Mockito 2 (strictness, Java 8,
      `ArgumentCaptor` improvements, `verifyZeroInteractions` deprecated), Mockito 3 (strict stubs as
      the JUnit-integration default), **Mockito 4** (removals of long-deprecated API), **Mockito 5**
      (inline mock maker as default, Java 11 baseline), 5.22 (Kotlin singletons), 5.23 (Android
      dexmaker change). `[TABLE]` `[CURRENCY]` `[RESEARCH]`
3.16.5 **The Mockito 4 → 5 migration**: expect *more* mockable code (finals) and expect the
      agent-attachment warning; audit for `mockito-inline` as a now-redundant dependency, and for
      tests that depended on final classes *not* being mockable. `[FLOW]` `[VERSION-TRAP]`
3.16.6 **PowerMock's obsolescence** as a version-history fact with a practical consequence: code that
      needed PowerMock for statics now needs only Mockito 5, so a PowerMock dependency is a
      removal candidate rather than a constraint. `[VERSION-TRAP]`
3.16.7 **Spring test history**: `SpringJUnit4ClassRunner`/`SpringRunner` → `SpringExtension` (Spring
      4.3/5.0) → `@MockBean` (Boot 1.4) → slices (Boot 1.4) → `@DynamicPropertySource` (5.2.5) →
      `@ServiceConnection` (Boot 3.1) → `@MockitoBean`/`@TestBean` (Framework 6.2) → **context
      pausing, `RestTestClient`, non-singleton overrides, method-scoped extension context**
      (Framework 7 / Boot 4). `[TABLE]` `[CURRENCY]` `[RESEARCH]`
3.16.8 **The Boot 3.x → 4.x test migration checklist**: starter renames, `@MockBean`→`@MockitoBean`,
      `TestRestTemplate`→`RestTestClient` (plus the new `@AutoConfigure…` requirement), JUnit 6
      adoption, Vintage deprecation, `SpringExtension` store-scope change, `Lifecycle` beans becoming
      pauseable, and Testcontainers 2.x renames arriving at the same time. Eight items, and they land
      together. `[FLOW]` `[TABLE]` `[VERSION-TRAP]` `[RESEARCH]`
3.16.9 **Testcontainers 1.x → 2.x** as a separate checklist (§ 2.6.30–2.6.31). `[FLOW]`
      `[VERSION-TRAP]`
3.16.10 **AssertJ's 3.x line and the 4.0 milestone**, plus the security-patch point of § 3.13.9.
      `[CURRENCY]`
3.16.11 **Hamcrest 2.2 → 3.0** and the `hamcrest-core`/`hamcrest-all` artifact history that still
      poisons classpaths. `[VERSION-TRAP]`
3.16.12 **The dependency-alignment rule** that prevents most of this pain: import the `junit-bom`, the
      `mockito-bom`, the `testcontainers-bom` and Boot's dependency management, and never pin a
      single artifact by hand. `[CFG]` `[PROVE]`
3.16.13 **The upgrade-order recommendation** when several of these land together: Java baseline →
      Spring Framework/Boot → JUnit → Mockito → Testcontainers, with the suite green at each step.
      `[FLOW]` `[PROVE]`
3.16.14 **How to answer a version question you are not sure about** in an interview: state the
      mechanism, state the version you last verified and when, and say the number should be checked.
      That is a stronger answer than a confident wrong constant — and it is the discipline this whole
      file is built on. `[PROVE]`

---

# PART 4 — BUILD IT

Every item ships complete, compiling Java 21 against the versions in the header, and every one is
followed by a **Diff vs the real one** table. Where the artifact is configuration rather than code,
the deliverable is the complete file.

4.1.1 **`InMemoryFundsLedgerRepository`** — a complete `Map`-backed fake implementing the real
      repository interface, with generated ids, reads-see-writes semantics, and a
      `findByClientIdAndStatus` that actually filters. `[BUILD]`
4.1.2 Diff vs the real Spring Data JPA repository: no transactions, no flush semantics, no
      constraints, no locking, no query derivation, no pagination `count` query, iteration order, and
      why each of those absences matters for what the fake can prove. `[TABLE]`
4.2.1 **`FundsLedgerRepositoryContract`** — the abstract JUnit 5 test class that both the fake and the
      Testcontainers-backed implementation extend, so the fake cannot drift (§ 2.11.8). `[BUILD]`
4.2.2 Diff vs a hand-written pair of test classes: the shared-contract approach catches fake drift,
      costs one abstraction, and cannot express engine-specific behaviour — enumerate what must stay
      in the subclass. `[TABLE]`
4.3.1 **`MutableClock`** — a complete `Clock` subclass with `advance(Duration)` and `set(Instant)`,
      thread-safe, satisfying `Clock`'s contract including `withZone`. `[BUILD]`
4.3.2 Diff vs `Clock.fixed` and vs mocking `Instant.now()`: what each can express, what each costs,
      and why the mutable clock is the right default for window-boundary tests. `[TABLE]`
4.4.1 **`LedgerEntryBuilder` + `LedgerEntries` object mother** — the full test-data-builder pair of
      § 2.4.5, with valid defaults and fluent overrides for every field the suite varies. `[BUILD]`
4.4.2 Diff vs Instancio/EasyRandom: determinism, readability of the failure, maintenance cost when a
      field is added, and where random data is acceptable. `[TABLE]`
4.5.1 **`LedgerEntryAssert`** — a complete AssertJ custom assertion extending
      `AbstractAssert<LedgerEntryAssert, LedgerEntry>` with `isSettled()`, `hasStakeOf(String)` using
      `compareTo`, and `belongsTo(clientId)`. `[BUILD]`
4.5.2 Diff vs chained generic AssertJ calls: message quality, discoverability, and the cost of the
      extra class. `[TABLE]`
4.6.1 **`@IntegrationTest`** — a composed meta-annotation bundling `@Tag("integration")`,
      `@SpringBootTest`, `@Testcontainers`, `@ActiveProfiles("test")` and the shared container
      configuration, so every integration test shares one cache key (§ 2.7.10). `[BUILD]`
4.6.2 Diff vs repeating the annotations per class: cache-key uniformity, the single point of change,
      and the loss of per-class flexibility (and why that loss is the point). `[TABLE]`
4.7.1 **`AbstractIntegrationTest`** — the singleton-container base class: `static
      PostgreSQLContainer` + `static KafkaContainer` started once, wired with `@ServiceConnection`,
      plus a `@BeforeEach` truncation hook driven by `JdbcClient`. `[BUILD]`
4.7.2 Diff vs `@Container` per class and vs `withReuse(true)`: startup count, CI safety, developer
      ergonomics, and the exact conditions under which each is correct. `[TABLE]`
4.8.1 **`SingletonContainerLauncherSessionListener`** — the same container started from a
      `LauncherSessionListener` (§ 3.1.12) with `ServiceLoader` registration, so it starts once per
      JVM before any engine runs and is closed at session end. `[BUILD]`
4.8.2 Diff vs the static-field approach: lifecycle precision, no reliance on class initialisation
      order, works across engines — and the extra registration file. `[TABLE]`
4.9.1 **`DatabaseCleanerExtension`** — a JUnit 5 extension implementing `BeforeEachCallback` that
      truncates a declared table set, using `ExtensionContext.Store.getOrComputeIfAbsent` on the
      **root** context to derive the table list once from the metadata. `[BUILD]`
4.9.2 Diff vs `@Sql` scripts, `@DirtiesContext` and `@Transactional`: speed, what commit behaviour
      each permits, and parallel-execution safety. `[TABLE]`
4.10.1 **`DockerAvailableCondition`** — an `ExecutionCondition` that disables integration tests with a
      readable reason when no Docker environment is present (§ 3.4.17). `[BUILD]`
4.10.2 Diff vs `@Testcontainers(disabledWithoutDocker = true)` and vs `assumeTrue`: reporting quality,
      scope, and where each belongs. `[TABLE]`
4.11.1 **`TestClientParameterResolver`** — a `ParameterResolver` for a `@TestClient` annotation that
      injects a fully-seeded QuizStakes client into a test method signature (§ 3.5.10). `[BUILD]`
4.11.2 Diff vs a `@BeforeEach` field: visibility of the dependency, scoping, and interaction with
      parallel execution. `[TABLE]`
4.12.1 **`QueryCountExtension`** — a Hibernate `StatementInspector` (or `datasource-proxy` listener)
      wired into the test context, with an `assertQueryCount(n)` API, so the N+1 fix is guarded
      (§ 2.5.20). `[BUILD]`
4.12.2 Diff vs asserting on latency and vs reading the log: determinism, precision, and why a query
      count is the only performance-adjacent assertion safe to gate on. `[TABLE]`
4.13.1 **`FlakeReportingTestWatcher`** — a `TestWatcher` + launcher `TestExecutionListener` pair that
      emits per-test outcome and duration as JSON lines for the § 2.22.5 dashboard. `[BUILD]`
4.13.2 Diff vs parsing the Surefire XML after the fact: liveness, structured metadata, and the cost of
      running inside the test JVM. `[TABLE]`
4.14.1 **`junit-platform.properties`** — the complete suite policy file: parallel execution with
      classes concurrent and methods same-thread, the fixed strategy for CI, a default timeout,
      `ReplaceUnderscores` display names, and random class ordering with a logged seed. `[BUILD]`
      `[CFG]`
4.14.2 Diff vs configuring the same things in Surefire/Gradle: portability across build tools and
      IDEs, and what genuinely belongs in the build instead. `[TABLE]`
4.15.1 **The complete Maven build block** for the tiering of § 2.21.2: Surefire with the unit tier and
      the pinned timezone/locale/encoding, Failsafe with the `*IT` pattern, JaCoCo with
      `prepare-agent`/`report`/`check` on patch coverage, PIT scoped to the domain package with
      history, and the Byte Buddy `-javaagent` for Mockito. `[BUILD]` `[CFG]`
4.15.2 Diff vs the equivalent Gradle configuration (JVM test suites, `useJUnitPlatform`,
      `maxParallelForks`, the build cache): what Gradle does better, what Maven does more
      predictably. `[TABLE]`
4.16.1 **`StakeReservationServiceTest`** — the canonical solitary unit test: constructor-injected
      collaborators, a fixed `Clock`, a fake repository, one mock for `NotificationService`,
      parameterized boundary cases from a text-block CSV, and a `never()` assertion for the
      self-excluded case. `[BUILD]`
4.16.2 Diff vs the typical service test in the wild: no `@SpringBootTest`, no `@InjectMocks`, no
      `verify` on the repository, no `Thread.sleep`, and an assertion on state rather than
      interaction. `[TABLE]`
4.17.1 **`AccountOpeningStateMachinePropertyTest`** — a jqwik model-based test over arbitrary
      `AO-*` transition sequences asserting no illegal state is reachable (§ 2.14.9). `[BUILD]`
4.17.2 Diff vs the parameterized transition table: what the property covers that the table cannot,
      runtime cost, and how a failure is reported and shrunk. `[TABLE]`
4.18.1 **`FundsLedgerBalancePropertyTest`** — the invariant property `derivedBalance == Σ positions`
      over generated position sets, including negative amounts and 40-digit scales (§ 2.14.10).
      `[BUILD]`
4.18.2 Diff vs example-based tests of the same method: which bugs each finds, and why the property
      needs an independently-derived oracle rather than the implementation's own formula. `[TABLE]`
4.19.1 **`SelfExclusionConcurrencyTest`** — the deterministic interleaving test for invariant 8: a
      `CountDownLatch`-coordinated self-exclude against a stake reservation on a real Postgres, with a
      committed transaction and an explicit statement of what it proves and what it does not
      (§ 2.3.25). `[BUILD]`
4.19.2 Diff vs `@RepeatedTest(1000)` and vs a jcstress harness: coverage of the interleaving space,
      runtime, and evidentiary strength. `[TABLE]`
4.20.1 **`AccountOpeningControllerTest`** — a `@WebMvcTest` using `MockMvcTester`, `@MockitoBean` for
      the service, assertions on status, Problem Details body and headers, with security filters
      **enabled** and `@WithMockUser`. `[BUILD]`
4.20.2 Diff vs the `mvc.perform(...).andExpect(...)` style and vs a full `@SpringBootTest`: failure
      messages, speed, and what each additionally proves. `[TABLE]`
4.21.1 **`ScreeningClientIT`** — the adapter integration test against WireMock with a delay
      (`withFixedDelay`) and a fault (`CONNECTION_RESET_BY_PEER`), asserting the timeout, the
      fallback and the circuit-breaker transition against the 30 ms budget (§ 2.12.7). `[BUILD]`
4.21.2 Diff vs mocking the client interface: what the wire test catches (serialization, headers, URL,
      timeout configuration) that a Mockito mock structurally cannot. `[TABLE]`
4.22.1 **`AgreementVersionPactTest` + `AgreementVersionProviderTest`** — both sides of a consumer-driven
      contract: the consumer test generating the pact with type matchers, and the provider
      verification with a `@State` handler. `[BUILD]`
4.22.2 Diff vs an integration test across both services: independence of deployment, what the contract
      does not verify (§ 2.13.18), and the broker/CI machinery it requires. `[TABLE]`
4.23.1 **`ArchitectureRulesTest`** — ArchUnit rules encoding the scenario's invariants as build
      failures: `BalanceView` may not be referenced from any decision path, no cross-schema
      repository access, only `FundsLedger` writes money, and no `Instant.now()` outside an adapter
      (§ 1.8.27). `[BUILD]`
4.23.2 Diff vs a code-review convention and vs a checkstyle rule: expressiveness, false positives, and
      the maintenance burden of the rule set. `[TABLE]`
4.24.1 **`CacheBehaviourTest`** — the four cache assertions § 15's syllabus parks here: the cache is
      used (origin invoked once for two reads), it is invalidated on write, it fails open when the
      cache is down, and concurrent misses coalesce — driven by an injected `Ticker` and a
      Testcontainers Redis, with no `Thread.sleep`. `[BUILD]` `[X-REF 15]`
4.24.2 Diff vs the typical cache test in the wild: no sleeping, no shared static cache, and an
      assertion on origin invocation count rather than on latency. `[TABLE]`
4.25.1 **`FlywayMigrationIT`** — applying the real migration set to a container seeded with
      production-shaped volumes and asserting the resulting schema and the elapsed lock behaviour
      (§ 2.5.9). `[BUILD]`
4.25.2 Diff vs `ddl-auto: create-drop`: which defects each can catch, and why the migration test is
      the only one that can catch a missing migration. `[TABLE]`
4.26.1 **`CharacterizationTest` for a legacy `BonusService`** — the pin-current-behaviour procedure of
      § 2.19.5 executed end to end, including an approval-style golden file with ids and timestamps
      normalised. `[BUILD]`
4.26.2 Diff vs a specification test: what each claims, how each should be changed when the behaviour
      is deliberately corrected, and how the diff on the test file becomes the audit record.
      `[TABLE]`
4.27.1 **`StakeFeeBenchmark`** — a complete JMH benchmark with `@State`, `@Warmup`, `@Measurement`,
      `@Fork`, `Blackhole` and `@BenchmarkMode(Throughput)`, in its own source set with its own task.
      `[BUILD]` `[X-REF 06]`
4.27.2 Diff vs a `System.nanoTime()` loop in a JUnit test: JIT warmup, dead-code elimination, fork
      isolation, and why the naive version measures nothing. `[TABLE]`
4.28.1 **`TESTING.md`** — the written mocking and tiering policy of § 2.11.17 and § 2.24.13 as a
      complete, reviewable document for the QuizStakes repository. `[BUILD]`
4.28.2 Diff vs leaving it to convention: how a written policy changes code review, and the failure mode
      of a policy document nobody reads (keep it under one page). `[TABLE]`

---

# PART 5 — INTERVIEW & RETENTION

## §5.1 The questions, with the answer shape

5.1.1 "Walk me through the test pyramid." — the ladder, the four degrading properties, then the
      trophy/honeycomb counter-position and the "measure your defect origins" synthesis. Leading
      with the counter-position is what distinguishes a senior answer.
5.1.2 "What is the difference between a mock and a stub?" — **the question this topic is most often
      opened with.** The five doubles, then the discriminator: a stub feeds input, a mock asserts an
      unobservable call.
5.1.3 "What is a fake, and when would you use one over a mock?" — stateful collaborators,
      reads-see-writes, and the shared contract test that stops drift.
5.1.4 "When do you use `verify()`?" — side effects with no observable trace, and `never()`. Then the
      anti-pattern.
5.1.5 "Why is over-mocking bad?" — tests pass while the system is broken, and the suite opposes
      refactoring.
5.1.6 "Would you mock the database?" — no, and the trophy argument for why, plus what H2 hides.
5.1.7 "Don't mock what you don't own — why?" — stability not ownership, the adapter as the seam, and
      the `Clock` exception that shows you understand the rule rather than reciting it.
5.1.8 "How does Mockito mock a final class?" — the inline mock maker, instrumentation-based method
      rewriting, and the fact that it is the default since Mockito 5.
5.1.9 "Why does `when()` on a spy call the real method?" — the recording mechanism, and therefore
      `doReturn/when`.
5.1.10 "Why must all arguments be matchers or none?" — the thread-local matcher stack and positional
      counting.
5.1.11 "What is strict stubbing and why is it on?" — the two exceptions, and the drift it catches.
5.1.12 "`ArgumentCaptor` or `argThat`?" — assertion on properties versus verification as the
      assertion, decided by failure message.
5.1.13 "What does JUnit create per test method?" — a new instance, and what `PER_CLASS` changes.
5.1.14 "Explain the JUnit 5 architecture." — Platform, Jupiter, Vintage; the engine SPI; why the split
      exists; and the JUnit 6 unified version number.
5.1.15 "Name the Jupiter extension points and their order." — the 18-step list, the wrapping guarantee,
      and the non-guarantee within a single class.
5.1.16 "Where does an extension keep state?" — the `ExtensionContext.Store` with a `Namespace`, scoped
      to the context, `getOrComputeIfAbsent` at the root for a per-run singleton.
5.1.17 "How do you inject something into a test method?" — `ParameterResolver`, and why fields are a
      different hook.
5.1.18 "How would you write an extension that starts a container once?" — the store at root scope, or
      a `LauncherSessionListener`.
5.1.19 "How do you run tests in parallel in JUnit?" — the five properties with their defaults, the
      classes-concurrent/methods-same-thread recommendation, and `@ResourceLock` for the shared
      resource.
5.1.20 "What breaks under parallel execution?" — the § 3.6.14 list, led by static state and
      `MockedStatic`'s thread scoping.
5.1.21 "`@ParameterizedTest` or `@TestFactory`?" — lifecycle callbacks per invocation versus runtime
      generation.
5.1.22 "How do you test an exception?" — `assertThrows`, assert on the exception, never try/fail/catch.
5.1.23 "Why did my `BigDecimal` assertion fail?" — scale, `equals` vs `compareTo`,
      `isEqualByComparingTo`. **The highest-frequency single gotcha in the topic.**
5.1.24 "Why AssertJ over JUnit assertions?" — type-directed API, better messages, and the argument-order
      problem it eliminates.
5.1.25 "How do you make a test deterministic?" — inject the clock, the randomness and the id source;
      pin timezone, locale and encoding in the build.
5.1.26 "How do you test asynchronous code?" — remove the asynchrony where you can, Awaitility
      `untilAsserted` where you cannot, never `Thread.sleep`.
5.1.27 "How do you test thread safety?" — you argue it with the memory model and probe it with
      jcstress; a green concurrent test is weak evidence. **The answer that separates levels.**
5.1.28 "Name six causes of flaky tests and the fix for each." — the taxonomy with the empirical
      ranking: async wait, concurrency, order dependence first.
5.1.29 "A test fails once a week in CI. What do you do?" — quarantine with a ticket and an owner, keep
      collecting data, fix or delete; never retry as the resolution. Then: treat it as a product bug
      until proven otherwise.
5.1.30 "Is it ever acceptable to retry a test?" — the steelmanned answer: at the E2E tier, recorded and
      reported as a flake, never silently.
5.1.31 "Why is my Spring test suite slow?" — context count, the ten cache-key attributes, the 32-entry
      LRU, and the base-class consolidation fix. **The highest-value practical answer in the topic.**
5.1.32 "What exactly forks a Spring context?" — the checklist, led by bean overrides and property
      sources.
5.1.33 "Why does `@MockitoBean` change the cache key?" — the three-step argument from singleton
      injection at refresh time.
5.1.34 "`@MockBean` or `@MockitoBean`?" — the latter, and note it is a Framework annotation now.
5.1.35 "What does `@WebMvcTest` load?" — the type list, and what it deliberately excludes.
5.1.36 "What does `MockMvc` not test?" — the servlet container, HTTP parsing, TLS, connection
      handling; the set-difference proof.
5.1.37 "Why can't I combine `@WebMvcTest` and `@DataJpaTest`?" — conflicting
      `@OverrideAutoConfiguration` and type-exclude filters, with no merge rule.
5.1.38 "What does `@DataJpaTest` hide?" — the missing flush, the callbacks, the first-level cache
      answering your assertion, and the post-commit listener that never fires.
5.1.39 "Which `@Transactional` attributes work on a test?" — the table; most do not.
5.1.40 "Does a `@Transactional` `@SpringBootTest(RANDOM_PORT)` test roll back?" — **no**, because the
      server handles the request on another thread. A genuinely surprising fact that lands well.
5.1.41 "Name the default Spring `TestExecutionListener`s in order." — the twelve, and what the order
      *means* (overrides before injection, transaction after injection, mock reset last).
5.1.42 "H2 or Testcontainers?" — the dialect/type/locking/planner divergences, each with a concrete
      query that behaves differently.
5.1.43 "How does Testcontainers clean up if I kill the JVM?" — Ryuk, labels, and the connection-based
      design; then the seven termination modes a shutdown hook would miss.
5.1.44 "How do you make Testcontainers fast enough to be the default?" — a static singleton container,
      one context, and `@ServiceConnection`; reuse only locally, and why not in CI.
5.1.45 "How do you run Docker-dependent tests in CI?" — socket mount, DinD, remote daemon, or a
      managed service, with the trade-offs.
5.1.46 "Why did Testcontainers stop compiling after the upgrade?" — the 2.0 artifact renames and the
      removed no-arg constructors.
5.1.47 "How do you stub an outbound HTTP call?" — WireMock at the wire, not a mocked client, and the
      fault/delay injection that is the only way to test retries and timeouts.
5.1.48 "How do you know your stub matches the provider?" — you don't; that is what contract testing is
      for.
5.1.49 "Explain consumer-driven contract testing." — the four-step flow, the three key properties, and
      `can-i-deploy` as the gate.
5.1.50 "Pact or Spring Cloud Contract?" — consumer-driven vs producer-driven default workflow, and the
      organisational fit argument.
5.1.51 "What does a contract test not prove?" — behaviour. The interface can be honoured with the
      wrong number in it.
5.1.52 "What is wrong with a coverage target?" — Goodhart, coverage measures execution not assertion,
      and a suite with no assertions can hit 100%.
5.1.53 "Line coverage or branch coverage?" — branch, with the `if (a && b)` counterexample.
5.1.54 "How does JaCoCo work?" — an ASM agent inserting a `boolean[]` probe array, CRC64 class ids, and
      the `Object.equals()` trick for probe retrieval.
5.1.55 "Why does my JaCoCo report show high branch coverage on untested error paths?" — exception edges
      are not branches.
5.1.56 "What is mutation testing and why is it better than coverage?" — a surviving mutant is a line
      you execute but do not verify; the score is hard to game.
5.1.57 "Name PIT's default mutators." — the eleven, and why the rest are off by default.
5.1.58 "How is mutation testing fast enough to run at all?" — coverage-driven test selection,
      fastest-test-first, mutant timeouts, and incremental history.
5.1.59 "Is there evidence mutation testing correlates with real bugs?" — Just et al., 357 real faults,
      73% coupling, independent of coverage. **Citing a study is a strong differentiator here.**
5.1.60 "What is your coverage number?" — the honest answer: I gate on patch coverage and I run mutation
      testing on the domain layer; the project percentage is not a target.
5.1.61 "TDD — do you do it?" — sometimes, here is when I do not, and here is what red-green-refactor
      actually buys.
5.1.62 "London or Chicago?" — outside-in to discover interfaces, classical for the domain core; the
      schools are tools, not identities.
5.1.63 "Where would you use property-based testing here?" — the five archetypes, then the specific
      invariant (derived balance == Σ positions) and why it beats examples.
5.1.64 "How do you test legacy code with no tests?" — get a seam, write a characterization test, then
      refactor. Not "get to 80% coverage".
5.1.65 "What is a seam?" — a place to change behaviour without editing there, plus its enabling point.
5.1.66 "How do you speed up a 40-minute suite?" — profile first; then context consolidation, singleton
      containers, in-JVM parallelism, and only then sharding. In that order, because that is the
      order of return on effort.
5.1.67 "How do you decide what to test at which level?" — the decision procedure, driven by where the
      risk lives.
5.1.68 "How do you test that a self-excluded client cannot stake?" — the domain synthesis question:
      invariant 8, a real restriction path (invariant 12 forbids the stub), a deterministic
      interleaving test, a property test over operation sequences, and an ArchUnit rule that stops the
      display projection being used for the decision.
5.1.69 "What would you never test with a mock in this system?" — the restriction decision, and the
      invariant that forbids it.
5.1.70 "Design the test strategy for this service." — the one-page artifact of § 2.24.13. The synthesis
      question.
5.1.71 "What would you delete from this test suite?" — the deletion criteria; being willing to answer
      is itself the signal.
5.1.72 "How do you know your test suite is any good?" — escaped-defect origin analysis, flake rate,
      mutation score on the domain, and gate duration. Four measurable things, not an opinion.
5.1.73 **The three-axis trade-off drills**, each with a full answer: (a) *solitary unit + integration*
      vs *sociable unit only* — speed, defect localisation, refactoring resistance; (b) *transactional
      rollback* vs *committed + truncate* — speed, what commit behaviour is testable, parallel
      safety; (c) *contract testing* vs *shared E2E environment* — independence, coverage of
      semantics, operational cost. `[TABLE]`
5.1.74 The **60-second verbal answer** to "how would you test a regulated payments platform", using
      QuizStakes end to end and leading with the two things that must never be faked.
5.1.75 **Fifteen self-quiz questions whose answers are numbers or exact names**, so recall is testable:
      the context cache default size and its property name; the number of `MergedContextConfiguration`
      attributes; the number of default Spring `TestExecutionListener`s; the number of steps in the
      Jupiter callback order; `junit.jupiter.execution.parallel.enabled`'s default;
      `…config.dynamic.factor`'s default; `…config.strategy`'s default; the five built-in
      `@ResourceLock` resources; the number of Boot test slices; PIT's default mutator count;
      JaCoCo's six counters; the flake taxonomy's top three causes and their percentages; the
      mutant/real-fault coupling percentage; Google's small/medium/large mix; and the JUnit 6 Java
      baseline. `[NUM]` `[TABLE]`

## §5.2 The trap list — the wrong belief, then the correction

5.2.1 Tests prove the code is correct. **They prove the cases you wrote do what you asserted.**
      `[TRAP]`
5.2.2 More tests are better. **A test that asserts implementation details has negative value.**
      `[TRAP]`
5.2.3 A flaky test is a minor annoyance. **Past ~1% it destroys the signal and the team stops reading
      red.** `[TRAP]`
5.2.4 Retrying fixes a flake. **It reduces the reported rate to `p^k` and changes nothing about the
      race.** `[TRAP]`
5.2.5 A unit test tests one class. **A unit is a unit of behaviour; the one-class reading is the root
      of over-mocking.** `[TRAP]`
5.2.6 "Mock" means any test double. **Five distinct kinds, and a Mockito `mock()` is usually a
      stub.** `[TRAP]`
5.2.7 A Mockito `@Spy` is a Meszaros spy. **It is a partial mock over a real instance.** `[TRAP]`
5.2.8 You should mock every collaborator. **Prefer real → fake → stub → mock, in that order.**
      `[TRAP]`
5.2.9 Mocking the repository tests the repository. **It tests your stub configuration.** `[TRAP]`
5.2.10 `@InjectMocks` is safe. **It fails silently, leaving `null` fields and an unrelated NPE.**
      `[TRAP]`
5.2.11 `when(spy.foo())` is harmless. **It executes the real method with real side effects.** `[TRAP]`
5.2.12 You can mix matchers and literals. **All or none —`InvalidUseOfMatchersException`.** `[TRAP]`
5.2.13 `anyString()` matches `null`. **It does not; `any()` does.** `[TRAP]` `[RESEARCH]`
5.2.14 An unstubbed mock returns `null` for everything. **Collections come back empty and `Optional`
      comes back empty.** `[TRAP]`
5.2.15 `RETURNS_DEEP_STUBS` is a convenience. **It is a Law-of-Demeter violation detector.** `[TRAP]`
5.2.16 `UnnecessaryStubbingException` should be silenced with `lenient()`. **It is telling you the
      test drifted from the code.** `[TRAP]`
5.2.17 Mockito cannot mock final classes. **It has been the default capability since Mockito 5.**
      `[TRAP]` `[VERSION-TRAP]`
5.2.18 You need `mockito-inline` for final classes. **It is redundant on Mockito 5 and can conflict.**
      `[TRAP]` `[VERSION-TRAP]`
5.2.19 Mockito's agent attaches fine forever. **Dynamic agent attachment is being disallowed by the
      JDK; add `-javaagent`.** `[TRAP]` `[VERSION-TRAP]`
5.2.20 A `MockedStatic` applies everywhere. **It is thread-scoped and must be closed.** `[TRAP]`
5.2.21 Mocking statics is a normal technique. **It hides the dependency and is a last resort.**
      `[TRAP]`
5.2.22 `verify` makes a test stronger. **It usually makes it more brittle without adding
      information.** `[TRAP]`
5.2.23 `verifyNoMoreInteractions` is good hygiene. **It welds the test to every future call.**
      `[TRAP]`
5.2.24 Asserting call order is thorough. **It asserts an implementation detail unless order is part of
      the contract.** `[TRAP]`
5.2.25 JUnit 5 is the current version. **JUnit 6.1.3 is; 6.0.0 shipped September 2025.** `[TRAP]`
      `[VERSION-TRAP]`
5.2.26 The Platform is 1.x and Jupiter is 5.x. **JUnit 6 uses one version for all three modules.**
      `[TRAP]` `[VERSION-TRAP]`
5.2.27 JUnit runs on Java 8. **JUnit 6 requires Java 17 at runtime.** `[TRAP]` `[VERSION-TRAP]`
5.2.28 `@Test` has `expected` and `timeout`. **Those are JUnit 4; Jupiter's `@Test` has no
      attributes.** `[TRAP]`
5.2.29 One test instance serves the whole class. **A new instance per method, unless `PER_CLASS`.**
      `[TRAP]`
5.2.30 Lifecycle methods within a class run in declaration order. **Explicitly unspecified —
      repeatable but not defined.** `[TRAP]`
5.2.31 `BeforeTestExecutionCallback` runs before `@BeforeEach`. **It runs after.** `[TRAP]`
5.2.32 The Jupiter callback order has 14 steps. **18, since `@ClassTemplate` added two.** `[TRAP]`
      `[VERSION-TRAP]`
5.2.33 Extensions can hold state in fields. **One instance may serve many tests; use the store.**
      `[TRAP]`
5.2.34 The extension store is a global map. **It is scoped to a context, inherited for reads.**
      `[TRAP]`
5.2.35 ServiceLoader extensions are picked up automatically. **Only with
      `junit.jupiter.extensions.autodetection.enabled=true`; the default is `false`.** `[TRAP]`
      `[CFG]`
5.2.36 `assertTimeoutPreemptively` is the safe timeout. **It runs on another thread and breaks
      `ThreadLocal`s, transactions and security contexts.** `[TRAP]`
5.2.37 `@Timeout` catches a hang. **It reports after the fact; it does not interrupt by default.**
      `[TRAP]` `[RESEARCH]`
5.2.38 `assumeTrue` and a disabled condition are the same. **An assumption aborts; a condition
      skips.** `[TRAP]`
5.2.39 Test ordering makes a suite reliable. **A test that needs an order is an order-dependent
      test.** `[TRAP]`
5.2.40 Random ordering is risky. **It is the cheapest detector of order dependence, at ~50% per run
      per polluter pair.** `[TRAP]`
5.2.41 Parallel execution is a switch you flip. **It reddens a suite with static state; adopt it
      class-by-class.** `[TRAP]`
5.2.42 JUnit parallelism is on by default. **`junit.jupiter.execution.parallel.enabled` defaults to
      `false`.** `[TRAP]` `[CFG]`
5.2.43 The dynamic strategy is safe in a container. **It multiplies `availableProcessors()`, which
      cgroups can misreport.** `[TRAP]`
5.2.44 `@Isolated` and `@ResourceLock` are the same. **One serialises against everything, the other
      against a named resource.** `[TRAP]`
5.2.45 `assertEquals(actual, expected)` is fine. **The order is `(expected, actual)` and reversing it
      inverts every message.** `[TRAP]`
5.2.46 `new BigDecimal("10.00").equals(new BigDecimal("10.0"))`. **`false` — `equals` includes
      scale.** `[TRAP]`
5.2.47 Comparing doubles with `isEqualTo` is fine. **Always use a tolerance.** `[TRAP]`
5.2.48 `usingRecursiveComparison` is a safe shortcut. **It silently includes every new field.**
      `[TRAP]`
5.2.49 `SoftAssertions` reports automatically. **Without `assertAll`/`assertSoftly` it silently
      passes.** `[TRAP]`
5.2.50 A `HashMap`'s iteration order is stable enough. **Assert with
      `containsExactlyInAnyOrder`.** `[TRAP]`
5.2.51 `@SpringBootTest` is the default way to test a service. **It is the most expensive one; most
      logic needs no context at all.** `[TRAP]`
5.2.52 Spring caches one context per suite. **One per distinct `MergedContextConfiguration`, capped at
      32 with LRU.** `[TRAP]`
5.2.53 The cache key is "the configuration". **Ten specific attributes, including context
      customizers.** `[TRAP]`
5.2.54 A property override is free. **It forks a context.** `[TRAP]`
5.2.55 `@DirtiesContext` cleans up. **It destroys the cached context for everyone downstream.**
      `[TRAP]`
5.2.56 More cached contexts is always better. **Past 32 you thrash and can rebuild more than you
      cached.** `[TRAP]`
5.2.57 A cached context keeps running. **In Boot 4 its `Lifecycle` beans are paused.** `[TRAP]`
      `[VERSION-TRAP]`
5.2.58 `@MockBean` is current. **Deprecated in Boot 3.4; use `@MockitoBean`.** `[TRAP]`
      `[VERSION-TRAP]`
5.2.59 `@MockitoBean` is a Spring Boot annotation. **It is Spring Framework's.** `[TRAP]`
5.2.60 Bean overrides only work on singletons. **Non-singletons are supported from Framework 7.**
      `[TRAP]` `[VERSION-TRAP]`
5.2.61 `@TestConfiguration` as a top-level class is picked up automatically. **Only inner classes are;
      top-level ones need `@Import`.** `[TRAP]`
5.2.62 `@Configuration` in a test adds to the config. **It replaces the primary configuration.**
      `[TRAP]`
5.2.63 You can stack two test slices. **You cannot; pick one and add `@AutoConfigure…`.** `[TRAP]`
5.2.64 `@WebMvcTest` includes your services. **It excludes `@Component`/`@Service` and
      repositories.** `[TRAP]`
5.2.65 `@DataJpaTest` runs against your real database. **It substitutes an embedded one unless
      `@AutoConfigureTestDatabase(replace = NONE)`.** `[TRAP]`
5.2.66 `ddl-auto: create-drop` in tests is fine. **It tests a schema you do not deploy.** `[TRAP]`
5.2.67 A transactional test proves the save worked. **Without a flush no SQL is issued and no
      constraint is checked.** `[TRAP]`
5.2.68 Reading back after a save proves the mapping. **The first-level cache returns the same
      instance.** `[TRAP]`
5.2.69 `@Transactional` on a test honours `isolation` and `timeout`. **It honours neither.** `[TRAP]`
5.2.70 A `@Transactional` `RANDOM_PORT` test rolls back. **It commits — the server runs on another
      thread.** `[TRAP]`
5.2.71 `@TransactionalEventListener(AFTER_COMMIT)` fires in a rolled-back test. **There is no
      commit.** `[TRAP]`
5.2.72 H2 in PostgreSQL mode is close enough. **Different dialect, types, locking, planner and error
      messages.** `[TRAP]`
5.2.73 `MockMvc` starts a server. **It does not; there is no socket and no servlet container.**
      `[TRAP]`
5.2.74 `@AutoConfigureMockMvc(addFilters = false)` is a convenience. **It removes security from the
      test.** `[TRAP]`
5.2.75 A green controller test plus a green service test proves the endpoint. **Nothing tested them
      together with real serialization and a real transaction.** `[TRAP]`
5.2.76 `@Container` on a static field starts it per test. **Static is per class; instance is per
      test.** `[TRAP]`
5.2.77 Testcontainers cleans up in a shutdown hook. **Ryuk watches a socket, which survives
      `SIGKILL`.** `[TRAP]`
5.2.78 `withReuse(true)` is enough. **It also needs the user-level opt-in, and the classpath
      properties file is not honoured for it.** `[TRAP]`
5.2.79 Reuse is a CI optimisation. **The documentation says it is not for CI; containers persist.**
      `[TRAP]`
5.2.80 Disabling Ryuk is harmless. **You get leaked containers and a full Docker disk.** `[TRAP]`
5.2.81 `postgres:16-alpine` is a pinned version. **The tag moves; pin a patch version or a digest.**
      `[TRAP]`
5.2.82 A container that started is ready. **Use a wait strategy; a listening port is not
      readiness.** `[TRAP]`
5.2.83 Inside the Docker network you use the mapped port. **You use the container port; the mapped
      port is for the JVM.** `[TRAP]`
5.2.84 A Testcontainers BOM bump upgrades you to 2.x safely. **Every artifact id and several packages
      changed.** `[TRAP]` `[VERSION-TRAP]`
5.2.85 `new PostgreSQLContainer<>()` still works. **2.0 removed the no-arg constructors.** `[TRAP]`
      `[VERSION-TRAP]`
5.2.86 A stub server proves the integration works. **It proves your belief about the provider is
      self-consistent.** `[TRAP]`
5.2.87 Mocking the HTTP client is equivalent to stubbing the wire. **It skips serialization, headers,
      URL building and timeouts.** `[TRAP]`
5.2.88 A contract test verifies behaviour. **It verifies the interface only.** `[TRAP]`
5.2.89 A consumer-driven contract constrains the provider's whole API. **Only what the consumer
      actually uses.** `[TRAP]`
5.2.90 Pact matchers should match values. **Match types, or the contract breaks on test-data
      changes.** `[TRAP]`
5.2.91 Coverage measures test quality. **It measures execution; a suite with no assertions can reach
      100%.** `[TRAP]`
5.2.92 100% line coverage means every branch is tested. **`if (a && b)` on one line disproves it.**
      `[TRAP]`
5.2.93 JaCoCo counts exception paths as branches. **It does not, and they do not raise complexity
      either.** `[TRAP]`
5.2.94 A zero-coverage report means the tests did not run. **It often means stale class files or a
      clobbered `argLine`.** `[TRAP]`
5.2.95 A mutation score of 100% is the goal. **Equivalent mutants make it unattainable in general.**
      `[TRAP]`
5.2.96 Mutation testing is too slow to use. **Coverage-driven selection plus incremental history makes
      it viable on changed files.** `[TRAP]`
5.2.97 A timed-out mutant is inconclusive. **It counts as killed.** `[TRAP]`
5.2.98 Enabling all PIT mutators gives a better signal. **It floods you with equivalent mutants.**
      `[TRAP]`
5.2.99 Mutation testing works on `@SpringBootTest`-covered code. **Each mutant would pay a context
      startup.** `[TRAP]`
5.2.100 Mutants are not like real bugs. **73% of 357 real faults were coupled to at least one
      mutant.** `[TRAP]` `[STUDY]`
5.2.101 TDD guarantees a good design. **It optimises locally; architecture is a separate activity.**
      `[TRAP]`
5.2.102 Writing tests after the code is wrong. **It is fine if you make them fail first.** `[TRAP]`
5.2.103 London-style mocking is more rigorous. **It produces the over-mocked, refactor-hostile suite.**
      `[TRAP]`
5.2.104 Cucumber makes tests readable. **It adds indirection unless a non-engineer actually reads
      them.** `[TRAP]`
5.2.105 A property-based test replaces example tests. **It complements them, and a tautological
      property tests nothing.** `[TRAP]`
5.2.106 Random test data improves coverage. **It trades determinism for convenience; log the seed or
      do not use it.** `[TRAP]`
5.2.107 `@RepeatedTest(1000)` finds races. **It is a lottery; green is not evidence.** `[TRAP]`
5.2.108 `Thread.sleep(2000)` is acceptable "just here". **It is always slow and still racy.** `[TRAP]`
5.2.109 Awaitility's `atMost` asserts performance. **It bounds waiting, it does not measure latency.**
      `[TRAP]`
5.2.110 Awaitility polls immediately. **`pollDelay` defaults to the poll interval.** `[TRAP]`
      `[RESEARCH]`
5.2.111 A latency assertion belongs in the unit suite. **It will flake on a shared runner; use a query
      or allocation count instead.** `[TRAP]`
5.2.112 A `System.nanoTime()` loop benchmarks a method. **JIT, dead-code elimination and OSR make it
      meaningless; use JMH.** `[TRAP]`
5.2.113 A load test on a laptop tells you about production. **Not at 1,200/sec across 8 instances.**
      `[TRAP]`
5.2.114 Averages are fine for latency. **Report percentiles, and beware coordinated omission.**
      `[TRAP]`
5.2.115 Legacy code needs 80% coverage before you touch it. **It needs a seam and a characterization
      test for the part you are changing.** `[TRAP]`
5.2.116 A characterization test asserts correct behaviour. **It asserts current behaviour, bugs
      included.** `[TRAP]`
5.2.117 An approved golden file is a test. **Only if someone reviews it; otherwise it is a rubber
      stamp.** `[TRAP]`
5.2.118 A disabled test still documents intent. **Without a reason and a ticket it is a false claim of
      coverage.** `[TRAP]`
5.2.119 Deleting a test is always a regression. **A duplicated or implementation-coupled test is worth
      deleting, and that is an engineering decision.** `[TRAP]`
5.2.120 Test code is exempt from review. **That exemption is how every other smell on this list
      accumulates.** `[TRAP]`
5.2.121 DRY applies to tests as it does to production code. **Readability beats reuse in tests; an
      over-abstracted base class is the mystery-guest smell.** `[TRAP]`
5.2.122 Sharding is the way to speed up CI. **Fix context count and enable in-JVM parallelism first;
      sharding duplicates every fixed cost.** `[TRAP]`
5.2.123 Test impact analysis is safe to gate on alone. **A stale map silently skips the test that would
      have caught it; run the full suite before merge.** `[TRAP]`
5.2.124 A shared staging environment is a reasonable test dependency. **Non-hermetic, contended and
      permanently flaky.** `[TRAP]`
5.2.125 `@Profile("test")` beans that change behaviour are fine. **You have made production behave
      differently from what you tested.** `[TRAP]`
5.2.126 Restriction state can be stubbed for a stake test. **Invariant 12 means the live decision path
      *is* the thing under test.** `[TRAP]`
5.2.127 `BalanceView` can be the fixture for an authorisation test. **It serves display only; the
      ledger serves decisions.** `[TRAP]`
5.2.128 Calling the real identity vendor in one CI test is harmless. **The cap is 600/min estate-wide
      and it is shared with production.** `[TRAP]` `[NUM]`

## §5.3 The one-line assertions to recall under pressure

5.3.1 The **cheat sheet** of every constant, default and exact name in the file on one screen, grouped
      by system: JUnit (parallelism properties and defaults, timeout properties, autodetection
      default, the 18-step callback order, the five `Resources` constants), Spring (cache size 32,
      the ten key attributes, the twelve listeners in order, the twenty test slices, the
      `@Transactional` attribute support table), Mockito (verification modes, `Answers` constants,
      strictness levels, the mock-maker resource path), Testcontainers (reuse and Ryuk properties),
      JaCoCo (six counters, the complexity formula), PIT (the eleven default mutators). `[TABLE]`
      `[NUM]`
5.3.2 The **master cost table**, reproduced. `[TABLE]`
5.3.3 The **test-double taxonomy table**, reproduced — the one table to be able to redraw from memory.
      `[TABLE]`
5.3.4 The **flakiness cause × symptom × detection × fix table**, reproduced. `[TABLE]`
5.3.5 The **"what forks a Spring context" checklist**, on one page. `[TABLE]`
5.3.6 The **decision tree from a requirement to a test type**, on one page. `[FLOW]`
5.3.7 The **never-fake list** for QuizStakes, with the invariant that forbids each item. `[TABLE]`
5.3.8 The **failure symptom → cause → diagnostic table**, reproduced. `[TABLE]`
5.3.9 The **version-delta table** — what changed in JUnit 6, Mockito 5, Testcontainers 2 and Boot 4 —
      as the currency answer. `[TABLE]`
5.3.10 The **seven sentences that carry the whole topic**: a test spends maintenance coupling to buy
      change velocity, so it must assert behaviour and nothing more; a stub feeds input and a mock
      asserts an unobservable call, and everything else should be real; the defects that escape live
      in the seams, so integration-test the seams and unit-test the logic; determinism is a
      precondition, so inject the clock, the randomness and the ids and pin the environment; a flaky
      test is a product bug until proven otherwise and never a retry; Spring test suites are slow
      because of context count, not test count; and coverage tells you what you ran while mutation
      testing tells you what you verified.
5.3.11 The **anti-checklist**: seven things to say you would *not* do — mock the database, gate on a
      project coverage percentage, retry a flake, put a latency assertion in the unit suite, use
      `@SpringBootTest` for pure logic, stub the restriction decision, or keep a disabled test without
      a ticket. Refusing the wrong test is the strongest signal in a testing interview.

---

## Sources consulted

| Source | URL | What it contributed |
|---|---|---|
| JUnit release notes (current) | https://docs.junit.org/current/release-notes/index.html | **6.1.3 as current (7 Aug 2026)** and the 6.x timeline (6.0.0 GA 30 Sep 2025, 6.0.3 15 Feb 2026, 6.1.0 20 May 2026, 6.1.1 29 Jun 2026); Java 17 runtime baseline; unified version numbering across Platform/Jupiter/Vintage; removal of `junit-platform-runner` and `junit-platform-jfr` (JFR folded into `junit-platform-launcher`); JSpecify adoption; `@DefaultLocale`/`@DefaultTimeZone` and the system-property extension (6.1.0); `TestInstancePreDestroyCallback`; deterministic `@Nested` ordering, `MethodOrderer.Default`/`ClassOrderer.Default` for nested classes and `@TestMethodOrder` inheritance; configurable `HierarchicalTestExecutorService`; Kotlin `suspend` test methods; `@ParameterizedClass`/`@ClassTemplate`; `--fail-fast` in ConsoleLauncher; FastCSV replacing the previous CSV handling; `org.junit.jupiter.api.Constants`; the experimental memory-cleanup mode |
| JUnit user guide — overview | https://docs.junit.org/current/user-guide/ | "JUnit 6.1.3 = JUnit Platform + JUnit Jupiter + JUnit Vintage"; the Java 17 runtime requirement; the chapter structure used to locate the pages below |
| JUnit user guide — Parallel Execution | https://docs.junit.org/6.1.3/writing-tests/parallel-execution.html | **Every parallel property with its default**: `…parallel.enabled=false`, `…mode.default=same_thread`, `…mode.classes.default=same_thread`, `…config.executor-service=fork_join_pool`, `…config.strategy=dynamic`, `…config.dynamic.factor=1.0`, `…dynamic.max-pool-size-factor`, `…dynamic.saturate=true`, `…fixed.parallelism` (required), `…fixed.max-pool-size`, `…fixed.saturate=true`, `…custom.class`; `@Execution(SAME_THREAD|CONCURRENT)` semantics quoted; `@Isolated` quoted; `@ResourceLock` with `SYSTEM_PROPERTIES`/`SYSTEM_OUT`/`SYSTEM_ERR`/`LOCALE`/`TIME_ZONE`, `READ`/`READ_WRITE`, `target = CHILDREN`, and the "lock acquired before `@BeforeEach`, released after `@AfterEach`" rule |
| JUnit user guide — Relative Execution Order of User Code and Extensions | https://docs.junit.org/6.1.3/extensions/relative-execution-order-of-user-code-and-extensions.html | The **complete 18-step callback order**, including the new `BeforeClassTemplateInvocationCallback`/`AfterClassTemplateInvocationCallback`; the wrapping guarantee quoted verbatim; the explicit non-guarantee of lifecycle-method order within a single class |
| Spring Framework reference — Context Caching | https://docs.spring.io/spring-framework/reference/testing/testcontext-framework/ctx-management/caching.html | **The ten `MergedContextConfiguration` cache-key attributes enumerated**, including `contextCustomizers` covering `@DynamicPropertySource`, `@TestBean`/`@MockitoBean`/`@MockitoSpyBean` and Boot testing features; **default max size 32**; LRU eviction; `spring.test.context.cache.maxSize` and the `SpringProperties` alternative — all quoted |
| Spring Framework reference — TestExecutionListener configuration | https://docs.spring.io/spring-framework/reference/testing/testcontext-framework/tel-config.html | **The twelve default `TestExecutionListener`s in exact registration order** (Framework 7.0.9): Servlet, DirtiesContextBeforeModes, ApplicationEvents, BeanOverride, DependencyInjection, MicrometerObservationRegistry, DirtiesContext, CommonCaches, Transactional, SqlScripts, EventPublishing, MockitoReset; `AnnotationAwareOrderComparator` ordering; `@TestExecutionListeners` replacing defaults unless `mergeMode = MERGE_WITH_DEFAULTS`; `spring.factories` discovery under `org.springframework.test.context.TestExecutionListener`; the AOT interaction |
| Spring Framework reference — Transaction management in tests | https://docs.spring.io/spring-framework/reference/testing/testcontext-framework/tx.html | `TransactionalTestExecutionListener` and the `TestTransaction` API (`flagForCommit`, `end`, `start`, `isActive`); default rollback; `@Rollback`/`@Commit`; `@BeforeTransaction`/`@AfterTransaction` with parameter injection; **the supported-attribute table** (`value`/`transactionManager` yes; `propagation` only `NOT_SUPPORTED`/`NEVER`; `isolation`, `timeout`, `readOnly`, `rollbackFor`/`noRollbackFor` no); `@Transactional` unsupported on `@BeforeAll`/`@AfterAll`; the **`assertTimeoutPreemptively` breaks test-managed transactions** warning; the **ORM flush false-positive** example; `@PostPersist` requiring a flush; the **`RANDOM_PORT`/`DEFINED_PORT` no-rollback** caveat |
| Spring Boot reference — Testing Spring Boot applications | https://docs.spring.io/spring-boot/reference/testing/spring-boot-applications.html | `@SpringBootTest`'s configuration search up the package hierarchy; **all four `webEnvironment` values with their semantics**; the slice contents for `@WebMvcTest` (`@Controller`, `@ControllerAdvice`, `@JacksonComponent`, `Converter`, `GenericConverter`, `Filter`, `HandlerInterceptor`, `WebMvcConfigurer`, `WebMvcRegistrations`, `HandlerMethodArgumentResolver`, `WebSecurityConfigurer`) and the exclusions; `@JsonTest`'s testers and `@AutoConfigureJsonTesters`; `@DataJpaTest`'s contents; `MockMvcTester` auto-configuration when AssertJ is present; `RestTestClient` + `@AutoConfigureRestTestClient`; `TestRestTemplate` + `@AutoConfigureTestRestTemplate`; `WebTestClient` + `@AutoConfigureWebTestClient`; `@MockitoBean`/`@MockitoSpyBean`; **`@TestConfiguration`'s inner-vs-top-level asymmetry**; `@DynamicPropertySource`; `@ServiceConnection`; `@DirtiesContext` class modes; the **"including multiple slices is not supported"** rule |
| Spring Boot reference — Test slices appendix | https://docs.spring.io/spring-boot/appendix/test-auto-configuration/slices.html | **The nineteen slice annotations enumerated exactly**: `@DataCassandraTest`, `@DataCouchbaseTest`, `@DataElasticsearchTest`, `@DataJdbcTest`, `@DataJpaTest`, `@DataLdapTest`, `@DataMongoTest`, `@DataNeo4jTest`, `@DataR2dbcTest`, `@DataRedisTest`, `@GraphQlTest`, `@JdbcTest`, `@JooqTest`, `@RestClientTest`, `@WebClientTest`, `@WebFluxTest`, `@WebMvcTest`, `@WebServiceClientTest`, `@WebServiceServerTest` |
| rieckpil — What's New for Testing in Spring Boot 4.0 and Spring Framework 7 | https://rieckpil.de/whats-new-for-testing-in-spring-boot-4-0-and-spring-framework-7/ | `RestTestClient` replacing the deprecated `TestRestTemplate` and its package `org.springframework.boot.resttestclient.autoconfigure`; **context pausing** (`Lifecycle`/`SmartLifecycle` stopped when idle, `SmartLifecycle#isPauseable()`, `ContextPausedEvent`); **bean overrides supporting non-singleton beans**; JUnit 6 adoption with JUnit 4/`SpringRunner`/Vintage deprecation; `spring-boot-starter-web` → `spring-boot-starter-webmvc` and the new test starters; Testcontainers 2.0's `testcontainers-` prefixes and JUnit 4 removal; **`SpringExtension` moving to a test-method-scoped `ExtensionContext`** with `@SpringExtensionConfig(useTestClassScopedExtensionContext = true)`; the managed library versions in Boot 4.0 (Mockito 5.20, AssertJ 3.27.6, Awaitility 4.3.0, HtmlUnit 4.17, Hamcrest 3.0, Selenium 4.37). **Secondary source — every claim taken from it is tagged `[RESEARCH]` and must be re-verified against docs.spring.io before the write pass commits it** |
| Spring Boot 4.1.1 / 4.1.0 release announcements | https://spring.io/blog/2026/08/20/spring-boot-4-1-1-available-now/ and https://spring.io/blog/2026/06/10/spring-boot-4/ | Boot **4.1.1 (20 Aug 2026)** as current, **4.1.0 GA 10 Jun 2026**, 4.0.0 GA 20 Nov 2025; Spring Framework 7 baseline; Java 17 minimum with support through Java 26; 4.1.x OSS support to 31 Jul 2027 |
| Testcontainers for Java — Reusable containers | https://java.testcontainers.org/features/reuse/ | `TESTCONTAINERS_REUSE_ENABLE=true` / `testcontainers.reuse.enable=true` in `~/.testcontainers.properties`; **the classpath properties file is explicitly not supported for this flag**; `withReuse(true)` plus manual `start()` and no `stop()`; "the container configuration **must be the same**" quoted; `TC_REUSABLE=true` in a JDBC URL; the documented warnings — experimental, **not for CI**, incomplete resource-cleanup and networking support, no automatic cleanup |
| Testcontainers Java releases / Maven metadata | https://github.com/testcontainers/testcontainers-java/releases and https://mvnrepository.com/artifact/org.testcontainers/testcontainers | **2.0.5 (20 Apr 2026)** as current; 2.0.4 (19 Mar 2026), 2.0.3 (15 Dec 2025); **1.21.4 (16 Dec 2025)** as the last 1.x. `[RESEARCH]` — dates taken from repository metadata and must be re-checked |
| Testcontainers 2.x migration material (OpenRewrite recipe + upgrade write-ups) | https://docs.openrewrite.org/recipes/java/testing/testcontainers/testcontainers2migration and https://blog.doubleslash.de/en/software-technologien/coding-and-frameworks/testcontainers-2-an-upgrade-worth-it/ | The 2.0 breaking-change set: **`testcontainers-` artifact prefixes**, module-specific packages, **JUnit 4 support removed**, **no parameterless container constructors**, `getContainerIpAddress()` → `getHost()`, `DockerComposeContainer` → `ComposeContainer`, and the fact that a BOM-only bump does not suffice. **Secondary sources — the write pass must confirm each item against the Testcontainers changelog** |
| Testcontainers Ryuk material (`ResourceReaper` source + garbage-collector docs + configuration docs) | https://github.com/testcontainers/testcontainers-java/blob/main/core/src/main/java/org/testcontainers/utility/ResourceReaper.java , https://golang.testcontainers.org/features/garbage_collector/ , https://java.testcontainers.org/features/configuration/ | Ryuk as a privileged sidecar with the Docker socket that watches the JVM's connection and removes labelled containers/networks/volumes after it drops (~10 s grace); label-based matching as the cleanup contract; reused containers labelled to be excluded from reaping; **`ryuk.disabled=true` in `.testcontainers.properties` or `TESTCONTAINERS_RYUK_DISABLED=true`, with the environment variable taking precedence**; the privileged-container constraint in restricted CI. **The Go docs were used for the garbage-collector mechanism; the Java specifics and the exact grace period must be confirmed from `ResourceReaper.java` before a number is committed** |
| JaCoCo — Implementation design | https://www.jacoco.org/jacoco/trunk/doc/implementation.html | **On-the-fly bytecode instrumentation via ASM** quoted ("very fast, can be implemented in pure Java and works with every Java VM"); the inserted **`boolean[]` probe array**; the **CRC64 hash of the raw class definition** as the class id and the multi-classloader/OSGi rationale plus the no-cryptographic-guarantee caveat; the **`Object.equals()`-only probe-retrieval trick** to avoid classloader coupling; agent class relocation to `org.jacoco.agent.rt_<randomid>`; the documented limitation that implicitly generated code (default constructors, `finally` structures) produces unexpected highlighting |
| JaCoCo — Coverage counters | https://www.jacoco.org/jacoco/trunk/doc/counters.html | **All six counters and their computation**: instructions (C0), branches (C1, `if`/`switch` only, **exception handling excluded**), cyclomatic complexity as **`v(G) = B − D + 1`** with exception handling not increasing complexity, lines ("executed when at least one instruction assigned to this line has been executed", requiring debug information, not summable across methods), methods ("at least one instruction has been executed", including constructors and static initialisers), classes ("at least one of its methods has been executed") |
| PIT — Mutators reference | https://pitest.org/quickstart/mutators/ | **The eleven default mutators** (Conditionals Boundary, Increments, Invert Negatives, Math, Negate Conditionals, Void Method Calls, Empty Returns, False Returns, True Returns, Null Returns, Primitive Returns) and **the optional/experimental set** (Constructor Calls, Inline Constant, Non Void Method Calls, Remove Conditionals, Remove Increments, AOR, AOD, CRCR, OBBN, ROR, UOI, ABS, Experimental Switch, Argument Propagation, Big Integer, Naked Receiver, Member Variable), each with what it changes |
| Martin Fowler — *Mocks Aren't Stubs* | https://martinfowler.com/articles/mocksArentStubs.html | **The five test doubles with Meszaros's definitions quoted** (dummy, fake, stub, spy, mock); **state verification vs behaviour verification** and the fact that only mocks mandate the latter; **classical/Detroit vs mockist/London TDD** and the four-axis trade-off (middle-out vs outside-in design, coupling to implementation, defect isolation vs cascading failures, fixture complexity vs per-test mock creation) |
| Mockito javadoc (`org.mockito.Mockito`, served via site.mockito.org) | https://site.mockito.org/javadoc/current/org/mockito/Mockito.html | **The verification modes** (`times(n)`, `atLeast`, `atLeastOnce`, `atMost`, `never()` as `times(0)`, `only()`, `timeout(ms)`, `after(ms)`, `calls(n)` as non-greedy in-order); **the `Answers` constants** (`RETURNS_DEFAULTS`, `RETURNS_SMART_NULLS`, `RETURNS_MOCKS`, `RETURNS_DEEP_STUBS`, `CALLS_REAL_METHODS`, `RETURNS_SELF`); matchers including lambda `argThat`; the inline mock maker's documented limits (**cannot mock package-visible methods of `java.*`, cannot mock native methods**, requires instrumentation). **The page served was an older javadoc version (2.2.7 content) — every item is tagged `[RESEARCH]` and must be re-verified against the 5.23.0 javadoc before the write pass quotes it** |
| Mockito releases / javadoc index | https://github.com/mockito/mockito/releases and https://javadoc.io/doc/org.mockito/mockito-core/latest/ | **5.23.0 (12 Mar 2026)** as current; Mockito 5's switch to **`mockito-inline` as the default mock maker** and the **Java 11 baseline**; 5.22's Kotlin `object` singleton mocking/stubbing; 5.23's dexmaker-mockito-inline Android change and the `mockSingleton`/`AbstractList` `StackOverflowError` fix |
| Mockito inline mock-maker internals (source + PR + class references) | https://github.com/mockito/mockito/pull/648/files and the `org.mockito.internal.creation.bytebuddy` class references (`InlineByteBuddyMockMaker`, `MockMethodAdvice`, `MockMethodDispatcher`, `InlineBytecodeGenerator`, `TypeCachingBytecodeGenerator`) | The inline maker combining **the Java instrumentation API with subclassing** to mock final types and methods; a **dynamically loaded Byte Buddy agent via self-attachment**, with the documented warning that self-attaching "will no longer work in future releases of the JDK"; `MockMethodAdvice` bound during mock creation with a `WeakConcurrentMap` of mocks; `MockMethodDispatcher.set()`; the registered instrumentation transformer; `InlineBytecodeGenerator.preload()` and type caching. **Class-level detail read from source references, not from official prose — all tagged `[RESEARCH]`** |
| Mockito strict-stubbing issues and javadoc | https://github.com/mockito/mockito/issues/1540 , https://github.com/mockito/mockito/issues/1522 , https://www.javadoc.io/static/org.mockito/mockito-core/2.8.9/org/mockito/exceptions/misusing/UnnecessaryStubbingException.html | `Strictness.STRICT_STUBS` as the default from Mockito 3.x onwards for the JUnit integrations; `@MockitoSettings(strictness = …)`; `UnnecessaryStubbingException` semantics and the `@BeforeEach`-stubbing-used-by-some-tests case; `PotentialStubbingProblem` as the stubbing-argument-mismatch signal and the fail-early rationale. **Version boundary for "default since 3.x" needs confirmation against the 5.x javadoc** |
| AssertJ releases / Maven metadata and a security advisory | https://github.com/assertj/assertj/releases , https://mvnrepository.com/artifact/org.assertj/assertj-core , https://linuxsecurity.com/advisories/opensuse/assertj-core-3-27-7-1-2026-24400 | **3.27.7 (24 Jan 2026)** as current, 3.27.6 (22 Sep 2025), 3.27.5, 3.27.4; **4.0.0-M1 (10 Mar 2025)** as a non-GA milestone; CVE-2026-24400 addressed in the 3.27.7 line. **The CVE identifier and its scope must be re-checked against the NVD entry before the bible states it** |
| Luo, Hariri, Eloussi & Marinov — *An Empirical Analysis of Flaky Tests* (FSE 2014) | https://www.cs.cornell.edu/courses/cs5154/2021sp/resources/LuoETAL14FlakyTestsAnalysis.pdf and https://dl.acm.org/doi/10.1145/2635868.2635920 | **201 flaky tests analysed, ten root-cause categories** — async wait, concurrency, test order dependency, resource leak, network, time, I/O, randomness, floating point, unordered collections — with **async wait ~45%, concurrency ~20%, order dependency ~12%** as the leading causes. Plus the language/domain-dependence findings from the follow-up JavaScript, Python and Android studies. **The percentage figures were reported via search summary of the paper and must be read out of the paper itself before publication** |
| Just, Jalali, Inozemtseva, Ernst, Holmes & Fraser — *Are Mutants a Valid Substitute for Real Faults in Software Testing?* (FSE 2014) | https://homes.cs.washington.edu/~rjust/publ/mutants_real_faults_fse_2014.pdf | **357 real faults across 5 open-source applications, 321,000 lines**; a statistically significant correlation between mutant detection and real-fault detection **controlling for code coverage**; a coupling effect for **73% of real faults** |
| Petrović & Ivanković et al. — *State of Mutation Testing at Google* / *Does mutation testing improve testing practices?* (ICSE 2021) | https://homes.cs.washington.edu/~rjust/publ/mutation_testing_practices_icse_2021.pdf | Surfacing mutants to developers leads to more and better tests; Google's design choice of **a single mutant per line** to keep the signal actionable |
| Mike Bland — *Small, Medium, Large* (Google test sizes) | https://mike-bland.com/2011/11/01/small-medium-large.html | Google's size-based classification — "a test's size is determined not by its number of lines of code, but by how it runs, what it is allowed to do, and how many resources it consumes" — and the **~70/20/10 small/medium/large** target mix. **The exact resource restrictions per size need confirmation from Google's own testing-blog posts before the bible enumerates them** |
| Test-pyramid critique material (testing trophy / honeycomb) | https://www.qase.io/blog/the-test-pyramid-and-its-discontents/ and https://web.dev/articles/ta-strategies | The trophy and Spotify's **honeycomb** as the microservice-oriented adaptation with a widened integration band and thinned implementation-detail and integrated bands; the "shape your suite to how the software is built and deployed" framing. **Secondary sources used as a completeness probe only** |
| Meszaros — *xUnit Test Patterns* smell catalogue | http://xunitpatterns.com/Test%20Smells.html (fetch failed — socket closed on two attempts) and https://dl.acm.org/doi/10.1145/1869542.1869622 | The three-way **code / behaviour / project** smell taxonomy and the existence of a catalogue of ~18 named smells. **The individual smell names in § 2.23 (Assertion Roulette, Mystery Guest, Eager Test, Fragile Test, Erratic Test, Obscure Test, General Fixture, Test Code Duplication, Conditional Test Logic, Test Logic in Production, Slow Tests, Buggy Test, Production Bug) are from recall, not from a fetched source — every one is tagged `[RESEARCH]` and must be verified against xunitpatterns.com or the book before the bible presents them as Meszaros's terms** |
| jqwik user guide | https://jqwik.net/docs/current/user-guide.html | **1.10.1** as the documented current version; `@Property`, `@ForAll`, `@Provide`, `Arbitraries`, `Assume.that`; `@Property(tries, seed, shrinking)`, `ShrinkingMode.FULL/BOUNDED/OFF`, `@PropertyDefaults`; result shrinking to a minimal failing case; the seed as the reproducibility mechanism. **jqwik's compatibility with JUnit 6 was not established and is flagged `[VERSION-TRAP]` `[RESEARCH]`** |
| Pact documentation — consumer tests, versioning, `can-i-deploy` | https://docs.pact.io/consumer and https://docs.pact.io/getting_started/versioning_in_the_pact_broker | The consumer test writing a pact via a mock service; the broker as the transport; **`can-i-deploy`** answering whether a consumer version is compatible with all of its providers in a target environment; **provider states** as named preconditions with provider-side handlers; Pact Specification **V2 / V3 / V4** selectability |
| Spring Cloud Contract reference | https://docs.spring.io/spring-cloud-contract/docs/current/reference/htmlsingle/ and https://docs.spring.io/spring-cloud-contract/reference/getting-started/cdc.html | The Groovy/YAML contract DSL and `value(client(...), server(...))` dynamic properties; generated provider verification tests and the **base class** mechanism (including per-package `baseClassMappings`); `@AutoConfigureStubRunner` with `ids`, `repositoryRoot`, `stubsMode`, `stubsPerConsumer`; the producer-driven default workflow and the consumer-driven variant |
| Interview-surface probes | https://interviewkickstart.com/blogs/interview-questions/junit-interview-questions , https://javarevisited.blogspot.com/2022/07/mockito-interview-questions-with-answers.html , https://medium.com/@AlexanderObregon/common-java-spring-boot-testing-and-validation-interview-questions-and-answers-b2da17b01ccc | Used purely as a **completeness probe** against § 5.1: the questions that actually get asked — `@Mock` vs `@InjectMocks`, `@Mock` vs `@Spy`, mocking void methods, asserting exceptions, Hamcrest matchers, testing private and protected methods, why mocking is needed, `@SpringBootTest` vs `@WebMvcTest`, running JUnit from the command line, coverage and cyclomatic complexity. Several of these are *badly framed* questions (testing private methods) and the bible must answer the question **and** correct the framing |

**Searches and fetches that failed or returned nothing usable.**

1. **`http://xunitpatterns.com/Test%20Smells.html` failed twice with "Socket is closed."** The smell
   catalogue in § 2.23 is therefore **recall-based**. Every smell name attributed to Meszaros must be
   verified before the bible presents it as his terminology, or the attribution must be softened.
2. **The JUnit extension-model chapter index could not be fetched** — `/6.1.3/extensions/index.html`,
   `/6.1.3/extension-model.html` and `/current/user-guide/extensions/index.html` all returned 404, and
   the anchored single-page URLs returned only the overview. The **extension-point list in § 3.4.1**
   is therefore assembled from the callback-order page (which names most of them) plus recall. The
   full list — in particular `TestInstanceFactory`, `InvocationInterceptor`,
   `TestTemplateInvocationContextProvider`, `TestWatcher`, `ExecutionCondition`, `ParameterResolver`
   and the exact `ServiceLoader` auto-registration property name and default — must be read from
   `https://docs.junit.org/6.1.3/extensions/` (the correct path shape is
   `docs.junit.org/<version>/<chapter>/<page>.html`) or from the single-page export at
   `https://docs.junit.org/6.1.3/_exports/junit-user-guide-6.1.3.html` before the write pass.
3. **The parameterized-tests chapter could not be fetched** (two 404s). `@ValueSource`'s type list,
   `@CsvSource`'s full attribute set, the new comment-character attribute, `@FieldSource`,
   `@ParameterizedClass`'s exact attributes, and the display-name placeholder set are **recall-based**
   and tagged `[RESEARCH]`.
4. **The `org.mockito.Mockito` 5.23.0 javadoc could not be fetched at any URL tried** —
   `javadoc.io/doc/…/latest/…`, `javadoc.io/doc/…/5.23.0/…` and `javadoc.io/static/…/5.23.0/…` all
   returned navigation-only pages or 404. The verification-mode and `Answers` lists come from an
   **older javadoc version served by site.mockito.org**; the content is very likely unchanged but
   must be confirmed against 5.23.0.
5. **No first-party, attributable engineering postmortem of a test-suite failure** (a flake outbreak,
   a coverage-gate incident, a contract-test escape) was located with citable figures. § 3.15 must
   therefore present the failure catalogue as **mechanisms**, not as an incident narrative, and must
   not invent one.
6. **No canonical university syllabus for "software testing" as it maps to this file's scope** was
   located; the curriculum angle was covered instead by the JUnit/Spring/Boot documentation's own
   chapter ordering and by the Boot test-slices appendix.
7. **Testcontainers startup-cost figures** (§ 2.6.29, § 3.10.22) are **experience-level estimates, not
   measured or sourced numbers.** They must be either measured on the target hardware or presented
   explicitly as order-of-magnitude.

**Carried-forward unverified items — the write pass must re-check every one before writing a number
or an exact name:**

1. The complete Jupiter **extension-point interface list** and the `ServiceLoader` auto-registration
   parameter name and default (§ 3.4.1, § 3.4.7).
2. **`@ParameterizedTest` source annotations and their attributes**, including `@FieldSource` and the
   JUnit 6 CSV comment character (§ 1.9.3–1.9.14).
3. **Timeout configuration parameter names** and defaults (§ 1.7.13), and whether `@Timeout` interrupts
   (§ 5.2.37).
4. **`junit.jupiter.displayname.generator.default`**, `junit.jupiter.testclass.order.default`,
   `junit.jupiter.execution.order.random.seed`, `junit.jupiter.conditions.deactivate`,
   `junit.jupiter.testinstance.lifecycle.default` (§ 1.5.6, § 1.7.4, § 1.7.20, § 1.7.21).
5. The **JUnit 6.1 memory-cleanup mode**'s exact parameter names (§ 1.6.18).
6. **`junit-jupiter-migrationsupport`**'s exact supported rule set (§ 1.6.11).
7. **Surefire/Failsafe default include patterns** (§ 1.12.2) — verify against the current plugin docs.
8. **Mockito's verification modes and `Answers` constants** against the 5.23.0 javadoc (§ 1.10.20,
   § 1.10.30).
9. **`Strictness.STRICT_STUBS` as `MockitoExtension`'s default** and the exact version from which
   (§ 1.10.3, § 1.10.5).
10. **`anyString()` vs `any()` null-matching behaviour** (§ 1.10.19, § 5.2.13).
11. **`@InjectMocks`'s resolution algorithm order** (§ 3.7.19) — read from `DefaultInjectionEngine`.
12. **The inline mock maker's per-class cost and metaspace impact** (§ 3.7.8) — currently
    unquantified.
13. **`MockedStatic`/`MockedConstruction` thread-scoping** as documented behaviour rather than
    inference (§ 2.10.1–2.10.3, § 3.7.12–3.7.13).
14. **Mockito's mock-maker resource path** (`mockito-extensions/org.mockito.plugins.MockMaker`) and the
    plugin SPI names (§ 2.10.16, § 3.7.11).
15. **Boot 4's `@MockitoBean` non-singleton support** and the exact `SpringExtensionConfig` attribute
    name (§ 1.11.28, § 3.4.21, § 3.8.19) — from docs.spring.io, not the secondary blog.
16. **`ContextPausedEvent` and `SmartLifecycle#isPauseable()`** exact names and semantics (§ 2.7.15,
    § 3.8.22).
17. **The `@WebMvcTest` meta-annotation composition** (§ 3.9.2) and each slice's
    `AutoConfiguration.imports` contents (§ 3.9.3) — read from the `spring-boot-test-autoconfigure`
    jar.
18. **`spring.test.constructor.autowire.mode`**'s exact values (§ 3.9.13).
19. **`@Sql`'s `executionPhase`/`SqlConfig.transactionMode` interaction** (§ 2.9.18).
20. **Ryuk's exact grace period** and the label keys it matches (§ 3.10.6–3.10.7).
21. **Testcontainers Docker-discovery order** (§ 3.10.1) — read from `DockerClientProviderStrategy`.
22. **Testcontainers 2.0's exact artifact/package renames** (§ 2.6.30) — from the changelog, not the
    migration blog.
23. **Testcontainers startup-cost figures** (§ 2.6.29, § 3.10.22) — measure or label as estimates.
24. **JaCoCo's probe-placement algorithm** (§ 3.11.3) and its filter list (§ 3.11.12).
25. **JaCoCo's runtime overhead figure** (§ 3.11.16) — currently unsourced.
26. **PIT's `timeoutConstant`/`timeoutFactor` defaults** (§ 3.12.4) and the bytecode-level operator
    implementations (§ 3.12.6).
27. **The flaky-test root-cause percentages** (§ 2.17.3) — read from the Luo et al. paper directly.
28. **Google's small/medium/large resource restrictions** (§ 1.3.5).
29. **The xUnit test-smell names and their three-way categorisation** (§ 2.23).
30. **jqwik's JUnit 6 compatibility** (§ 2.14.15).
31. **Awaitility's `pollDelay` default** (§ 2.3.7).
32. **Hamcrest 3.0's artifact coordinates and the `hamcrest-core` conflict symptom** (§ 1.8.23).
33. **CVE-2026-24400's identifier and scope** (§ 3.13.9) — check the NVD entry.
34. **`spring-boot-starter-test`'s exact transitive contents in Boot 4.1** (§ 1.11.1).
35. **Every version number and date in the header table**, all tagged `[CURRENCY]` and checked
    2026-09-03.

---

## Gaps vs the current guide

`src/topics/16-testing.md` is **408 lines** across **13 numbered sections** plus a 27-item
`## Atomic concept checklist`. It is a strong short guide — its test-doubles section, its flakiness
table, its H2 critique and its contract-testing walkthrough are all better than typical — and **every
concept in it survives as a leaf.** The table below is the work order.

| Syllabus area | Present in `src/topics/16-testing.md` | Missing | Shallow |
|---|---|---|---|
| §1.1 why tests exist | the opening framing only ("testing interviews probe what a test proves and what it costs") | the whole section: the five things a test buys, the cost itemisation, test-as-liability, the flake-probability arithmetic, feedback-latency thresholds, when *not* to test, types-instead-of-tests, verification vs validation | the "what it proves / what it costs" frame is present as a sentence and must become the section's spine |
| §1.2 vocabulary | scattered; the double taxonomy is defined in § 2 | the whole section: sociable vs solitary, the four scope words, deterministic/repeatable/isolated separated, flaky vs brittle vs fragile, seam, the coverage-criteria vocabulary, PIT's result vocabulary, the fixture vocabulary, hermetic, test selection vs sharding vs parallelism | — |
| §1.3 the ladder and the pyramid | § 1 — the seven-row ladder table, the four degrading properties, the trophy counter-position, the synthesis sentence | Google's size-based classification and the 70/20/10 mix; the honeycomb; the ice-cream cone; the combinatorial argument for pushing tests down; the "measure your defect origins" reframing; the decision procedure; the `*Test`/`*IT` convention; the cost-per-confidence table with real numbers; the one-E2E argument | the ladder's "typical time" column has no arithmetic behind it and the rungs below "unit" are undifferentiated (solitary vs sociable) |
| §1.4 test doubles | § 2 — the five-row table, the stub-vs-mock discriminator, the five mock/don't-mock rules, the over-mocking trap | Meszaros/Fowler quoted rather than paraphrased; state vs behaviour verification named as such; **a Mockito `mock` is a stub-and-spy hybrid**; the `@Spy`-vs-Meszaros-spy naming collision; the fake given full weight plus its shared contract test; the double-selection decision table; "stability not ownership"; the refactoring-opposition argument; the QuizStakes double-selection worked end to end | "wrap third-party clients" is one bullet and needs the adapter code plus the one integration test |
| §1.5 anatomy and naming | § 11 — given-when-then, one logical assertion, the behaviour-statement name, test-the-behaviour-not-the-implementation | one-logical-assertion clarified; the competing naming conventions; `@DisplayName`/`@DisplayNameGeneration`; don't-test-private-methods with the design argument; no-logic-in-tests; literal over computed expected values; duplication-over-indirection and the DRY inversion; the review checklist | § 11 is 10 lines for a subject that carries the readability of the whole suite |
| §1.6 JUnit architecture | absent — § 4 goes straight to lifecycle | **the entire subject**: Platform/Jupiter/Vintage, the engine SPI and why the split exists, the artifact map, api-vs-engine scoping, the JUnit 4→5 annotation map, `@Suite`, `ConsoleLauncher`, `junit-platform.properties`, `junit-platform-testkit`, the `@API` status policy — **and the JUnit 6 unified-versioning and Java 17 facts, which invalidate the standard interview answer** | — |
| §1.7 lifecycle and annotations | § 4 — the lifecycle order, new-instance-per-method, `@TestInstance(PER_CLASS)`, `assertThrows`, `assertAll`, `@DisplayName`, `@Nested`, `@Tag`, `@Disabled` with a reason | `@RepeatedTest`, `@TestFactory`/dynamic tests, `@TestTemplate`, `@Timeout` and the three timeout mechanisms with the preemptive trap, all fourteen conditional annotations, `Assumptions`, the three outcomes, `@TestMethodOrder`/`ClassOrderer` and random-order-with-seed, built-in parameter injection, `TestWatcher`, composed meta-annotations, `@RegisterExtension` vs `@ExtendWith` | the lifecycle is four lines; `@Tag` "+ build filtering" has no configuration |
| §1.8 assertions | § 5 — AssertJ's fluent chain, `extracting`, `usingRecursiveComparison`, the BigDecimal trap, the double tolerance, the `assertEquals` argument order | the full JUnit `Assertions` surface; `assertThrowsExactly`; the full AssertJ surface; `usingRecursiveComparison`'s configuration and its silent-new-field trap; `SoftAssertions` vs `assertAll`; `assertThatThrownBy`; `java.time` assertions and precision truncation; order-independent collection assertions; JSON assertion options; **custom assertion classes**; Hamcrest's place and the 3.0 artifact trap; the failure-message comparison table; **ArchUnit as an assertion library** | the BigDecimal trap is excellent and must survive verbatim; everything around it is one example each |
| §1.9 parameterized and generated | § 4 — `@ParameterizedTest` with `@CsvSource`, the source list, the copy-paste trigger rule | every source's attributes; `@CsvSource(textBlock)`; `@CsvFileSource` and the mystery-guest caveat; **FastCSV in JUnit 6**; `@FieldSource`; the SPI trio (`ArgumentsProvider`/`ArgumentConverter`/`ArgumentsAggregator`); implicit conversion; **`@ParameterizedClass`**; parameterized vs `@TestFactory`; the two parameterization traps; the QuizStakes truth tables | the source list is a single line naming five annotations |
| §1.10 Mockito basics | § 3 — the setup, `when` vs `doReturn` with the spy explanation, all-or-nothing matchers, `ArgumentCaptor`, `@Mock` vs `@MockBean`/`@MockitoBean`, the `verify` anti-pattern, strict stubs | the three creation mechanisms; `MockitoExtension`'s full behaviour; the three strictness levels; **both strict-stubbing exceptions by name**; the `@BeforeEach`-stubbing nuance; consecutive stubbing; `thenThrow`'s checked-exception rule; `thenAnswer`/`thenCallRealMethod`; the full matcher list; **why matchers are all-or-nothing (the thread-local stack)**; all verification modes; `verifyNoInteractions` vs `verifyNoMoreInteractions`; `InOrder`; `@Captor`/`getAllValues`; **`@InjectMocks`'s silent failure**; `@Spy`; `reset`; **the default-answer table**; all six `Answers` constants; `RETURNS_DEEP_STUBS` as a smell detector; what Mockito cannot mock; `mockingDetails` | the `@MockBean` context-cache paragraph is the guide's best insight and needs the arithmetic behind it |
| §1.11 Spring Boot basics | § 9 — a five-row slice table, the `@WebMvcTest` example, the cost model paragraph, `addFilters = false`, the `@DataJpaTest` flush note | `spring-boot-starter-test`'s contents; **all nineteen slices** (the guide lists five); the slice mechanism; `webEnvironment`'s four values; `@AutoConfigureTestDatabase(replace = NONE)`; `@JsonTest`'s testers; **`@TestConfiguration` and its inner-vs-top-level asymmetry**; the four property-source mechanisms and their precedence; `@DynamicPropertySource`; `@Sql`; `@DirtiesContext`'s modes; `@TestBean`; `@ServiceConnection`; **`ApplicationContextRunner`**; `spring-security-test`; `@ApplicationEvents`; `OutputCaptureExtension`; `MockMvcTester`; `RestTestClient` | the slice table's "Loads" column is a phrase per row where the reference gives an exact type list |
| §1.12 the build surface | absent | **the entire subject**: Surefire vs Failsafe and *why* deferral matters, the default include patterns, `forkCount`/`reuseForks`/`argLine`, Surefire vs Platform parallelism, Gradle's `Test` task and test suites, tag filtering in both tools, report formats, `junit-platform.properties` as policy, single-test CLI invocation, the silent-zero-tests failure, fork memory arithmetic, **pinning timezone/locale/encoding** | — |
| §2.1 the cost model | § 9's "cost model" paragraph | **the master cost table**; the `C·b + n·t` decomposition; fixed vs marginal cost; the context and container arithmetic; Amdahl and Little for a suite; the feedback-latency thresholds; the cost of a flake in hours/year; confidence-per-second; what is *not* worth optimising; how to measure | the paragraph asserts caching matters without a single number |
| §2.2 time and randomness | § 6 — the reach-out-to-a-global diagnosis, the `Clock` example, `Supplier<UUID>`/seeded `Random`/`IdGenerator`, the leap-year payoff, the sleep trap | the full globals list; the `Clock` factory surface; **a mutable test clock**; `Clock` vs mocking a static; **locale and timezone as separate hazards with their failure arithmetic**; `@DefaultLocale`/`@DefaultTimeZone`; the JUnit 6 system-property extension; `@TempDir` and its static/instance and Windows-cleanup traps; hostname/DNS; the determinism audit; the QuizStakes daily-limit boundary case | § 6 is strong on `Clock` and silent on everything else |
| §2.3 async and concurrency | § 10 — Awaitility's `untilAsserted` example, the sleep comparison, the injectable-executor advice, "test the asynchrony once" | the async-boundary taxonomy; Awaitility's full surface and `pollDelay`'s default; `untilAsserted` vs `until`; timeout-is-not-a-performance-assertion; the deterministic primitives; `CompletableFuture` timeouts; executor-shutdown leaks; **`@Async` self-invocation**; **`@TransactionalEventListener` never firing**; message consumers; `@EmbeddedKafka` vs a container; `StepVerifier`/virtual time; **thread safety as a distinct problem**; why a green concurrent test is weak; `@RepeatedTest` as a bad race detector; **jcstress**; Lincheck; static analysis; the invariant-8 test | § 10 is 18 lines and is the guide's only treatment of concurrency in tests |
| §2.4 test data | absent | **the entire subject**: the four strategies compared, object mothers, test data builders, the two combined, the one-obvious-difference rule, records as test data, unique-per-test data, shared vs immutable fixtures, `@Sql` vs builders, the mystery-guest smell, random data generators, the QuizStakes canonical fixture set | — |
| §2.5 database testing | § 8 — the H2 critique (excellent, must survive verbatim), the Testcontainers example, the static-container note, the honest trade-off; § 9's `@DataJpaTest` flush note | what a database test is *for*; each H2 divergence with a concrete query; the intermediate H2/Postgres position; **schema management and the `ddl-auto` false witness**; Flyway in tests; **testing a migration**; Liquibase contrasts; **the five cleanup strategies and the decision table**; asserting via `JdbcClient` not the ORM; `TestEntityManager`'s full surface; **the seven things rollback hides**; **the query-count assertion for N+1**; isolation and locking tests; `EXPLAIN` assertions; the QuizStakes database test set | the H2 section is excellent; everything about *how to organise* database tests is missing |
| §2.6 Testcontainers | § 8 — the annotation example, `@DynamicPropertySource`, static-container-per-class, the reusable-containers mention, the Docker-in-CI trade-off | **the code must be corrected for Testcontainers 2.x**; static vs instance `@Container` costs; the singleton base class shown; **`@ServiceConnection`** and its mechanism; `@ImportTestcontainers`; development-time containers; the JDBC URL scheme; **all wait strategies and the readiness race**; the module list; `ComposeContainer`; **container-port vs mapped-port**; file copying vs bind mounts; **reuse's exact configuration, hash contract, rules and documented warnings**; **zombie containers**; **Ryuk**; the configuration surface; the four Docker-in-CI options; rootless/Podman/Colima; image pull cost; **pinning digests**; the startup-cost budget; **the 2.0 breaking-change list and the OpenRewrite recipe**; when Testcontainers is wrong | "the reusable containers flag" is four words for a feature with a hash contract and three documented warnings |
| §2.7 context caching | § 9's cost-model paragraph — caching by configuration key, the four things that change it, "the number-one cause of slow Spring test suites", the standardise advice | **the ten cache-key attributes enumerated**; **the 32-entry LRU and its property name**; what eviction costs; **superlinearity past 32**; the DEBUG-statistics audit; **the full fork checklist (13 items vs the guide's 4)**; the base-class consolidation pattern; the uniform-superset counter-intuition; `@DirtiesContext`'s legitimate uses; **Boot 4 context pausing**; `@ContextHierarchy`; `@Nested` inheritance; AOT constraints; the QuizStakes arithmetic | the guide names the problem correctly and quantifies none of it |
| §2.8 the web-layer clients | § 9's `@WebMvcTest` example only | **the entire subject**: the four options on the server/socket axis, **what `MockMvc` actually is and what it cannot catch**, the full `MockMvc` surface, `print()`, **`MockMvcTester`**, `standaloneSetup` vs `webAppContextSetup`, `WebTestClient`, **`RestTestClient`**, `TestRestTemplate`'s deprecation, RestAssured, the selection rule, validation and error-contract tests, security in the slice, async and multipart, and the closing green-suites-prove-nothing trap | — |
| §2.9 `@Transactional` in tests | § 9's one sentence ("rolls back each test, which is convenient but means you never see the flush") | **the mechanism**; `@Rollback`/`@Commit`/`TestTransaction`; `@BeforeTransaction`/`@AfterTransaction`; **the supported-attribute table**; the `@BeforeAll` restriction; **all eight hidden behaviours** — flush, callbacks, the first-level cache answering your assertion, post-commit listeners, propagation, concurrency, **`RANDOM_PORT` not rolling back**, **`assertTimeoutPreemptively`** — the decision rule, and `@Sql`'s phase interaction | one sentence for the single most consequential Spring testing behaviour |
| §2.10 Mockito advanced | absent | **the entire subject**: `MockedStatic`/`MockedConstruction` and their thread scoping, why static mocking is a smell, `Answer` in anger and `AdditionalAnswers`, `AdditionalMatchers`, named `ArgumentMatcher`s, `MockSettings`, **`verboseLogging`**, `MockitoSession`, mocks as method parameters, **final classes and the mock-maker resource**, **the self-attaching-agent warning**, `mockito-inline`'s obsolescence, virtual threads, `BDDMockito`, framework listeners, the alternatives, **PowerMock as a signal**, `verify(timeout)`, `stubOnly` | — |
| §2.11 mocking policy | § 2's when-to-mock bullets | the policy as one rule; the ports-and-adapters framing; **the wrap-the-vendor pattern with code**; the mock-count and stub-shape heuristics; **the fake's shared contract test**; don't-mock-the-framework; don't-mock-what-types-guarantee; concrete-over-double; **the real→fake→stub→mock ladder**; the verification policy table; the `never()` test that earns its place; mocking across a transaction boundary; the quantified cost of mocking the database; **`TESTING.md` as an artifact** | the bullets are correct and unargued |
| §2.12 HTTP stubbing | § 7's flake-table row ("WireMock/MockWebServer; never call real services in CI") | **the entire subject**: why a mocked client is not enough, the three tools compared, `MockRestServiceServer`'s surface and boundary, **WireMock's matching DSL**, **fault and latency injection as the only way to test retries and timeouts**, the identity-vendor test, **the 600/min cap as a hard prohibition**, registration options, wiring the port into Spring, record/playback and its discipline, **stub drift as the fundamental limit**, response templating, `MockWebServer`, `MockServerContainer`/LocalStack | one table row |
| §2.13 contract testing | § 13 — the problem statement, the four-step CDC flow, the three key properties, `can-i-deploy` (all strong, all must survive) | the one-artifact framing; **provider states in depth**; **Pact matchers and match-on-type**; specification versions; **pact-jvm's JUnit 5 surface**; broker options; **WIP/pending pacts**; **Spring Cloud Contract as producer-driven, with the base-class mechanism**; the producer-vs-consumer comparison; messaging contracts; **schema-registry compatibility as the third option**; OpenAPI validation; **what contract testing does not prove**; its real cost; the QuizStakes contract map including "no contract test possible" for the vendor | § 13 is a good four-step explanation with no API, no matchers and no tooling |
| §2.14 property-based testing | absent | **the entire subject**: the idea, why it fits backend work, jqwik's surface, arbitraries, **shrinking**, **the seed as the reproducibility contract**, **the five archetypes**, model-based testing, the QuizStakes properties, PBT vs parameterized, its costs, **the tautology trap**, the alternatives, JUnit 6 compatibility, fuzzing as the adjacent discipline | — |
| §2.15 coverage | § 12 — "coverage measures which lines executed, not whether anything was asserted", the no-assertion 100% point, floor-not-target, Goodhart, the getter-test consequence | the criteria hierarchy and subsumption; **why path coverage is infeasible**; **line vs branch with the `if (a && b)` counterexample**; **JaCoCo's six counters as documented**; **exception paths excluded from branches** and what that invalidates; instruction coverage as the honest number; **patch coverage as a legitimate gate**; the Maven/Gradle surface and the `argLine` trap; honest exclusions; Lombok/record filters; aggregate reports; integration-test coverage; the one-sentence interview answer | § 12's coverage paragraph is three sentences and is the guide's best-value-per-line passage; it needs the mechanism underneath it |
| §2.16 mutation testing | § 12 — the premise, the mutation examples, "a surviving mutant is a line your tests execute but do not verify", the run-it-nightly advice | the result vocabulary; **mutation score vs test strength**; **PIT's eleven default mutators enumerated**; the optional set; why the defaults are a subset; reading a report; **the equivalent-mutant limit**; **the Just et al. and Google findings with their numbers**; **the cost model and coverage-driven selection**; incremental/SCM modes; threshold gates; what it cannot do; PIT's practical friction; descartes; the QuizStakes first-run target | four sentences for a subject with a citable evidence base |
| §2.17 flaky tests | § 7 — the ten-row cause/symptom/fix table and the quarantine rule (both excellent, both must survive) | the definition sharpened; **the empirical taxonomy with percentages and its language-dependence**; **a detection column on every row**; **fourteen additional causes**; order dependence with victim/polluter vocabulary; **the isolation bisect**; detection at scale; **the flake-rate metric with a threshold**; quarantine as a policy with an owner and a deadline; **the steelmanned retry argument**; the retry tooling; **the flake-is-often-a-real-bug argument with the settlement example**; the seven-rule prevention checklist; the triage procedure; CI-vs-local as a diagnostic | the table is the guide's strongest artifact and needs only extension, never replacement |
| §2.18 TDD and BDD | absent | **the entire subject**: red-green-refactor with a purpose per step, **watch-it-fail**, the three laws, what TDD does and does not buy, when it is the wrong tool, test-after done well, **Chicago vs London with Fowler's four-axis table**, the per-layer synthesis, where each school fails, **BDD as communication not tooling**, Gherkin/Cucumber's surface and when it earns its cost, Spock, **`@DisplayName` + `@Nested` as BDD without the framework**, ATDD's double loop, the practice questions | — |
| §2.19 legacy code | § 12 — characterization tests (definition, purpose, the change-detector framing, the deliberate-fix step) and approval/golden-master (all must survive) | **the seam and its enabling point**; the write-a-wrong-assertion procedure; approval testing's mechanism, right use and normalisation; **the dependency-breaking catalogue**; sprout/wrap; **the static-dependency ladder**; testing around a god class; scratch refactoring; coverage as a legacy map; change-coupled coverage; the strangler's shadow comparison; the interview framing | characterization testing is well explained in five lines and has no technique catalogue behind it |
| §2.20 performance boundaries | absent | **the entire subject**: the never-assert-latency rule, the four activities separated, **JMH and why a hand-rolled loop is invalid**, JMH's surface and `Blackhole`, keeping it out of the suite, Gatling/k6, percentiles, **coordinated omission**, testing against the SLO budgets, the environment-fidelity problem, regression gating, **query/allocation counts as the one safe deterministic proxy**, chaos testing, and timeouts/retries as a *functional* concern | — |
| §2.21 CI | § 4's `@Tag` "+ build filtering" mention only | **the entire subject**: the CI goals, the tier structure, fail-fast ordering, **sharding's three strategies and its arithmetic ceiling**, the shared-state hazard, in-JVM parallelism first, **test impact analysis and its silent failure**, caching, Gradle's up-to-date trap, randomised order in CI, **runner resource limits and `availableProcessors()` under cgroups**, failure artifacts, required checks, hooks, the nightly job, the QuizStakes 10-minute target | — |
| §2.22 test observability | absent | **the entire subject**: the suite as a monitored system, the metric set with bad values, distribution over mean, the slowest-20 report, flake dashboards from JUnit XML, `TestWatcher`/launcher listeners, **JFR events**, Open Test Reporting, container logs as test output, **reading a Spring / Mockito / AssertJ / Testcontainers failure line by line**, build time as an SLO, **test-suite postmortems** | — |
| §2.23 anti-patterns | § 2's over-mocking trap, § 11's implementation-coupling point, § 12's coverage-target point | **the entire named catalogue**: Meszaros's three-way split, Assertion Roulette, Mystery Guest, Eager Test, Fragile/Sensitive Equality, Erratic Test and its sub-smells, Slow Tests as a compounding smell, Obscure Test, General Fixture, duplication vs the DRY over-correction, Conditional Test Logic, **Test Logic in Production**, over-specification, **testing the mock and the could-this-fail test**, the 100%-coverage test, getter tests, **happy-path-only**, disabled-test rot, commented-out tests, the manual step, the shared staging environment, the unreviewed test, the "tests later" ticket, and the master table | the traps that exist are correct and unnamed — naming them is what makes them recallable |
| §2.24 choosing | § 1's synthesis sentence and § 2's mocking bullets | the ten decision procedures as explicit flows; **the deletion criteria**; **the testability properties a design must have**; testability-as-a-coupling-proxy; the QuizStakes one-page strategy | — |
| §3.1–3.3 Platform internals | absent | **the entire subject**: `LauncherFactory`/`Launcher`, all ten selector types, filters and the selector-vs-filter proof, **the `TestEngine` SPI and `ServiceLoader` registration**, the engine list, launcher `TestExecutionListener` (and its name collision with Spring's), `TestPlan`, `UniqueId`'s wire form, **`LauncherSession`/`LauncherSessionListener`**, `LauncherInterceptor`, configuration resolution, the JFR move, **why JUnit 4's `Runner` forced the rewrite**; the descriptor tree, `TestSource`, the discovery walk, **the seven causes of "no tests found"**, discovery-vs-execution failures, `@Nested` instance nesting, pruning, discovery cost; `HierarchicalTestEngine`'s `Node` interface, `ExtensionRegistry` inheritance, `HierarchicalTestExecutorService`, `ThrowableCollector` and suppressed exceptions, `TestInstanceFactory`/`TestInstancePostProcessor` as where injection happens, `InvocationInterceptor`, `TestReporter`'s path to the report | — |
| §3.4–3.6 extensions and parallelism | absent | **the entire subject**: the extension-point list, **the 18-step order with the wrapping guarantee and the intra-class non-guarantee**, the two new `ClassTemplate` callbacks, the `BeforeEach`-vs-`BeforeTestExecution` pair, **all four registration mechanisms with the autodetection default**, extension ordering and inheritance, extensions-must-be-stateless, `ExtensionContext`'s surface and hierarchy, **`Store`/`Namespace`/`getOrComputeIfAbsent`/`CloseableResource`**, the root-store singleton idiom, `ExecutionCondition`, both exception handlers, `TestWatcher`, **`SpringExtension` as a case study**, the Framework 7 store-scope change, extension composition, `EngineTestKit`; `ParameterResolver`'s full mechanics; **every parallel property with its verified default**, the two-knob design and its four combinations, `@Execution`/`@Isolated`/`@ResourceLock` with the built-in resources and lock timing, custom resource keys, **the fourteen things that break under parallelism**, the `@MockitoBean` hazard, `availableProcessors()` under cgroups, work-stealing subtleties, the adoption procedure, the measured payoff, process-vs-thread parallelism | — |
| §3.7 Mockito internals | § 3's mechanics are all API-level | **the entire subject**: subclass vs inline mock maker, Objenesis constructor bypass and its consequences, **the instrumentation-based method rewriting**, **`MockMethodAdvice`/`MockMethodDispatcher`/`WeakConcurrentMap`**, why retransformation beats subclassing, its cost, type caching, **the self-attaching agent and the JDK deprecation**, the plugin SPI, `mockStatic`/`mockConstruction` thread-local internals, **the stubbing-recording trace and the three traps it explains**, `ArgumentMatcherStorage` and `validateState`, verification as a query over history, **`@Mock` injection via `TestInstancePostProcessor`**, **`@InjectMocks`'s three-stage algorithm and its silent failures**, stack-trace cleaning, serialisable mocks, memory behaviour, **Byte Buddy conflicts** | — |
| §3.8–3.9 Spring test internals | § 9's "caches contexts by configuration key" | **the entire subject**: the six-type object model, `TestContextManager`'s hooks, `TestContextBootstrapper` and Boot's subclass, **`ContextCustomizerFactory` and the customizers that matter**, `MergedContextConfiguration`'s `equals`, the loaders, `CacheAwareContextLoaderDelegate`, **`DefaultContextCache`'s LRU and statistics**, eviction closing contexts, `@DirtiesContext`'s two listeners, **the twelve default listeners in order and what the order means**, `MockitoResetTestExecutionListener`, **listener merging and the silent-removal gotcha**, `spring.factories` discovery, **the bean-override infrastructure and why it must be a `BeanFactoryPostProcessor`**, `@MockitoSpyBean`'s wrapping and its AOP conflict, non-singleton support, `TransactionalTestExecutionListener`'s internals, the transaction-manager lookup order, **context pausing's state machine**, AOT, `@BootstrapWith`; and the whole slice machinery — meta-annotation composition, `AutoConfiguration.imports`, `TypeExcludeFilter`, `@OverrideAutoConfiguration`, **why slices cannot compose**, `@AutoConfigureTestDatabase`'s mechanism, `TestEntityManager`'s transaction binding, `MockRestServiceServer`'s and `MockMvc`'s mechanisms, **`ConnectionDetails`/`ContainerConnectionDetailsFactory`**, `@TestConstructor`, `ApplicationContextRunner`'s mechanism | — |
| §3.10 Testcontainers internals | absent | **the entire subject**: Docker discovery order, `DockerClientFactory` and the overrides, the start sequence, **port mapping as the parallel-safety mechanism**, `getHost()`, **the labels and their role in cleanup**, **Ryuk's protocol and why a connection beats a shutdown hook**, `ResourceReaper`, disabling Ryuk and the consequence, **the reuse hash**, reuse's Ryuk exclusion, **why the reuse flag is deliberately not classpath-readable**, `@Testcontainers`'s implementation, `disabledWithoutDocker`, wait strategies as the readiness contract, lifecycle hooks, `ImageNameSubstitutor` and registry mirrors, `asCompatibleSubstituteFor`, the JDBC driver, **startup-cost decomposition**, the 2.0 internals changes, Testcontainers Cloud | — |
| §3.11–3.13 tooling internals | absent | **the entire subject**: JaCoCo's ASM agent, the `boolean[]` probe array and probe placement, **the CRC64 class id and the stale-class-file consequence**, **the `Object.equals()` probe-retrieval trick**, agent relocation, offline instrumentation, the `.exec` file, **where branch coverage comes from and why exception edges are excluded**, `LineNumberTable` dependence, the filter list, complexity from bytecode, **the `${argLine}` trap**, overhead, parallel merging, TCP dump; PIT's pipeline, **coverage-driven selection and fastest-test-first**, timeouts counting as kills, bytecode mutation's consequences, **three operators at the bytecode level**, the return-mutator split, minion JVMs, incremental history, SCM mode, **why Spring contexts make PIT hopeless**, the JUnit 5 plugin, descartes; AssertJ's self-type generics, recursive comparison internals and its two failure modes, `SoftAssertions`'s proxying vs `assertAll`'s collection, custom assertions, why AssertJ's API removes the argument-order error, the security patch, 4.0 | — |
| §3.14 proofs | none — the current guide asserts throughout | all 28 proofs: the flake-probability arithmetic, retry masking, the context cost model and LRU thrashing, Amdahl for a suite, the layer-combinatorics argument, path-coverage infeasibility, line-does-not-imply-branch, branch-does-not-imply-correct, the equivalent-mutant undecidability, why mutation score resists gaming, the coupling result, order-dependence detection probability, sharding's diminishing returns, Little's Law for the queue, **why `MockMvc` cannot prove an endpoint works**, why a mocked repository cannot prove a rollback, why the transactional test hides the flush, why a green concurrent test is weak, **why extension wrapping must be an onion**, why the store must be scoped, **why `@MockitoBean` must change the cache key**, **why Ryuk's design beats a shutdown hook**, why selection makes mutation testing tractable, why inline can mock finals, why JaCoCo's id must be content-derived, why a fake needs a contract test, and why "don't mock what you don't own" is about stability | — |
| §3.15 failure catalogue | symptoms scattered across §§ 3, 7, 9 | a consolidated **33-entry** symptom → cause → diagnostic → fix catalogue, with the real error text for each | — |
| §3.16 version history | § 3's "`@MockBean` (deprecated in Boot 3.4 for `@MockitoBean`)" — the guide's only version statement | **the entire subject**: JUnit's four generations, **the 5→6 migration checklist**, JUnit 5's own increments, Mockito's five generations, **the 4→5 migration**, PowerMock's obsolescence, Spring test history through Framework 7, **the Boot 3→4 eight-item test-migration checklist**, Testcontainers 1→2, AssertJ's lines, Hamcrest's artifact history, **the BOM-alignment rule**, the upgrade order, and how to answer a version question honestly | — |
| §4 build it | § 3, § 5, § 6, § 8, § 9, § 10, § 13 have illustrative fragments (all correct, all partial) | all 28 implementations and their 28 Diff-vs-the-real-one tables | the existing fragments must be absorbed and completed, never deleted — and every one re-domained from `OrderService`/`Order`/`Account` to QuizStakes |
| §5 interview & retention | the 27-item atomic checklist | the 75 questions with answer shapes, the 128-item trap list, the cheat sheet, the reproduced master tables, the two decision trees, the three-axis drills, the 60-second verbal answer, the fifteen numeric self-quiz items, the anti-checklist | the checklist is strong and must be carried forward **expanded**, never trimmed |

### Must survive verbatim (or verbatim-plus-expansion)

These passages are the current guide's best work and the bible must keep the exact framing:

1. The opening frame: **"Testing interviews probe whether you can articulate *what a given test
   proves* and *what it costs*."** Plus the identification of the two places candidates lose points —
   the test-doubles taxonomy and flakiness ("naming the cause, not just 'we retry it'").
2. The **pyramid rationale's four properties**: "the reason isn't dogma, it's four properties that
   degrade as you go up: **speed**, **determinism**, **failure localisation**, and **maintenance
   cost**" — including the "a unit failure names the bug; an E2E failure names 'checkout broke'"
   contrast (re-domained to "registration broke").
3. The **testing-trophy paragraph**, including "most real bugs live in the seams (SQL, serialization,
   transaction boundaries) that unit tests mock away".
4. The synthesis: **"unit-test logic, integration-test integration, and don't unit-test glue code by
   mocking it into meaninglessness."**
5. The **five-row test-double table** and the discriminator: **"a stub feeds input to the test; a mock
   asserts on output you can't otherwise see."**
6. **"Reserve `verify()` for genuine side effects with no observable result (an email was sent, an
   event was published)."**
7. The five **when-to-mock rules**, each in its current wording: mock at the boundaries you own; wrap
   third-party clients and mock the wrapper ("when they refactor, your tests break without any
   behaviour changing. An adapter interface you own is the seam"); never mock pure logic or value
   objects; never mock what you're testing ("almost always a sign the class does two things and
   should be split"); prefer a fake over a mock for anything stateful ("reads see writes — with none
   of the stubbing noise").
8. The **over-mocking trap**: "over-mocking produces tests that pass while the system is broken,
   because every collaborator returns exactly what the test told it to. If a test's setup is longer
   than the code under test, the design or the test approach is wrong."
9. The **`when` vs `doReturn` explanation**: "`when(mock.foo())` **actually calls** `foo()` on the
   mock to record the stubbing. On a plain mock that's harmless. On a `@Spy` (a real object) it
   executes the real method — with real side effects."
10. **"Argument matchers are all-or-nothing"** with `InvalidUseOfMatchersException` named.
11. The **`ArgumentCaptor` selection rule**: "Use a captor when you want to assert on *properties* of
    the argument; use an `eq`/argThat matcher when you want the verification itself to be the
    assertion. A captor's failure message is much better."
12. The **`@MockBean` context-cache paragraph**, which is the guide's single best practical insight:
    "**each distinct set of mock beans creates and caches a new application context.** Twenty test
    classes with slightly different `@MockBean` sets means twenty context startups and a build that
    takes minutes. Keep the mock-bean configuration uniform, or push the test down to plain
    Mockito."
13. The **`verify` anti-pattern paragraph**, including "refactor `save` to `saveAll` and the test
    fails though behaviour is identical" and "`verifyNoMoreInteractions` on everything makes every
    test maximally brittle".
14. **"Strict stubs … fail the test on unused stubbings — that's a feature; it catches tests that have
    drifted from the code."**
15. **"A new test instance per method by default, so instance fields are naturally isolated."**
16. **"Parameterized tests are the right tool the moment you'd copy-paste a test and change one
    literal — especially for boundary cases."**
17. **"Never `try { ...; fail(); } catch (E e) {}`"** and "`assertAll(...)` reports every failed
    assertion instead of stopping at the first."
18. **`@Disabled` with a reason and a ticket.**
19. The **BigDecimal paragraph** in full: "`BigDecimal.equals` compares scale as well as value. Use
    `isEqualByComparingTo("10.00")`, which uses `compareTo`. This is a favourite gotcha", plus the
    doubles-need-a-tolerance rule.
20. The **`assertEquals` argument-order paragraph**: "Reversing it produces backwards failure messages
    ('expected 5 but was 3' when it's the other way round) that waste debugging time. AssertJ
    sidesteps this entirely, which is a good reason to standardise on it."
21. **"Untestable code is usually code that reaches out to a global."** Plus **"`Clock` is in
    `java.time` precisely for this"** and the payoff sentence: "you can test the leap-year,
    month-end, and DST cases that are otherwise unreachable."
22. **"Trap: `Thread.sleep` in a test to 'wait for the clock to move'. It's slow and still racy."**
23. **"A flaky test is worse than no test — it trains the team to ignore red builds."**
24. **The entire ten-row flakiness table**, every row's cause, symptom and fix.
25. **"Quarantine, then fix or delete — never `@Retry` as the resolution. A retried test hides a real
    race that will surface in production."**
26. The **H2 paragraph** in full: "It also **lies**. It has a different SQL dialect, different type
    coercion, no native `JSONB`/arrays/`ON CONFLICT` nuances, different locking and isolation
    behaviour, no real query planner, and different constraint error messages. Tests pass; production
    fails on the exact query you thought you'd tested. That false confidence is the reason to avoid
    it."
27. **"H2 is defensible only for tests that don't exercise real queries at all — and in that case,
    prefer not touching a database."**
28. **"`static` container + JUnit's per-class lifecycle means one startup shared across the class"**
    and the singleton/reusable point: "which is what keeps this fast enough to be the default."
29. **"Testcontainers needs a Docker daemon in CI and adds seconds of startup. Worth it for anything
    touching SQL."**
30. The **context-caching cost paragraph**: "Anything that changes the key — `@MockBean`/`@MockitoBean`,
    `@TestPropertySource`, active profiles, `@DirtiesContext` — forces a new context. **That is the
    number-one cause of slow Spring test suites.** Standardise your test configuration; avoid
    `@DirtiesContext` unless you genuinely mutated the context."
31. **"Add `@AutoConfigureMockMvc(addFilters = false)` only when you deliberately want to skip
    security — otherwise your controller tests won't catch an auth misconfiguration."**
32. **"`@DataJpaTest` rolls back each test, which is convenient but means you never see the flush."**
33. The **Awaitility paragraph**: "Awaitility polls a condition with a timeout — fast when the work
    finishes quickly, and it fails with the *assertion's* message rather than a bare timeout.
    `Thread.sleep(2000)` is strictly worse: always slow, and still flaky on a loaded CI machine."
34. **"Test the *asynchrony* itself once, separately, rather than in every test that happens to cross
    it."**
35. **"A failing test name should tell you what broke without opening the file."**
36. **"Test the behaviour, not the implementation … This is the property that makes a test suite an
    asset rather than a liability."**
37. **"Coverage measures which lines executed, not whether anything was asserted. A test suite with no
    assertions can hit 100%. Use it as a *floor* to find untested areas, never as a target — Goodhart's
    law applies immediately, and a mandated 90% produces getter tests."**
38. **"A surviving mutant is a line your tests execute but do not verify."**
39. The **characterization-test paragraph**: "write tests that assert what it *currently* does —
    including the bugs. They are not correctness tests; they're a change-detector that turns 'I hope
    this refactor is safe' into 'the build tells me'. Then refactor, then fix the bug as a deliberate,
    visible test change."
40. The **contract-testing problem statement**: "service A mocks service B in its tests, B changes its
    response shape, both suites are green, production breaks. E2E tests would catch it but are slow
    and require deploying everything."
41. The **four-step CDC flow** and the **three key properties**: "the contract states only what the
    consumer **actually uses** (so the provider is free to add fields), no shared environment or
    simultaneous deployment is needed, and each side runs independently in its own pipeline. That is
    what makes it viable where E2E isn't."
42. All **27 atomic-checklist lines**, expanded rather than replaced.

### Corrections the write pass must make to existing text

These are not additions — the current file is wrong, stale, off-domain or imprecise here:

1. **Every example must be re-domained.** §§ 3, 5, 6, 8, 9, 10 use `OrderService`, `OrderRepository`,
   `PaymentGateway`, `Order`, `SHIPPED`, `PROCESSED`, `NEW`/`PAID`, `SubscriptionService`,
   `Subscription`, `Account.withdraw`, `InsufficientFundsException`, `OrderController`, `/orders/9`,
   `OrderRepositoryIT` and an `orders` table. The pipeline's rule is QuizStakes only:
   `FundsLedger`, `LedgerEntry`, `StakeReservationService`, `ClientRestrictions`,
   `NotificationService`, `AccountOpening`, `AccountOpeningController`, `/clients/{id}/agreements`,
   `AO-100`…`AO-400`, `CASH_AVAILABLE`, `SETTLED`.
2. **§ 3's Mockito example is truncated** — the code fence opens a class and never closes it. The
   bible's version must compile.
3. **§ 8's Testcontainers code is Testcontainers 1.x and will not compile on 2.x.**
   `new PostgreSQLContainer<>("postgres:16-alpine")` still works (an explicit image is now
   *mandatory*), but the artifact coordinates, the package, and `DockerComposeContainer` have all
   changed. State the version the code targets.
4. **§ 8's `postgres:16-alpine` tag is unpinned.** The bible must pin a patch version or a digest and
   say why (§ 2.6.28).
5. **§ 8's "the **reusable containers** flag"** must be corrected and expanded: it requires
   `withReuse(true)` **and** a user-level opt-in that is **deliberately not readable from the
   classpath**, it is documented as **experimental and not for CI**, and it interacts with Ryuk. As
   written, a reader would enable it in CI and leak containers.
6. **§ 9's slice table lists five slices; there are twenty** (nineteen in the appendix plus
   `@JsonTest`). The table must be complete or must say explicitly that it is the common subset.
7. **§ 9's `@WebMvcTest` "Loads" cell** ("MVC layer, converters, `@ControllerAdvice`, security
   filters") must be replaced with the documented type list, which includes `Filter`,
   `HandlerInterceptor`, `WebMvcConfigurer`, `WebMvcRegistrations` and
   `HandlerMethodArgumentResolver`, and must state the `@ConfigurationProperties` exclusion.
8. **§ 9's `@DataJpaTest` row says "an embedded DB by default"** without naming the switch. Add
   `@AutoConfigureTestDatabase(replace = NONE)`, which is the single line that reconciles § 8's
   Testcontainers advice with § 9's slice advice — as written, the two sections contradict each
   other.
9. **§ 9's `@RestClientTest` row says `RestTemplate`/`RestClient`.** In Boot 3.2+ `RestClient` is the
   forward-looking option and `RestTemplate` is in maintenance; say which one new code should use.
10. **§ 9's cost-model paragraph names four things that change the cache key; there are at least
    thirteen**, and the key itself is ten specific attributes. Enumerate.
11. **§ 3's `@MockBean` parenthetical** ("deprecated in Boot 3.4 for `@MockitoBean`") is correct but
    understates it: `@MockitoBean` is a **Spring Framework** annotation in
    `org.springframework.test.context.bean.override.mockito`, and `@TestBean` and `@MockitoSpyBean`
    are part of the same replacement. Also note the Framework 7 non-singleton support.
12. **§ 4's parameterized-source list** must add `@FieldSource`, `@ArgumentsSource`, and
    `@ParameterizedClass`, and must note the JUnit 6 CSV-parser change.
13. **§ 4's lifecycle description** must add the extension callbacks, because the interview question is
      about the *combined* order (§ 3.4.2).
14. **§ 5's `usingRecursiveComparison` example** must gain the warning that it includes every field by
    default, so adding a field silently changes what the test asserts.
15. **§ 6's `Instant.now(clock)` example** is correct but the service reads `Instant.now(clock)` inside
    a method whose parameter is `Subscription s` — re-domain and also show the mutable-clock variant,
    since `Clock.fixed` cannot test a window rollover.
16. **§ 7's flake table row "Timing / `Thread.sleep`"** should name Awaitility's `pollDelay` default,
    since a naive `await()` introduces its own fixed delay.
17. **§ 7's "Port/resource collisions" row** says `webEnvironment = RANDOM_PORT` — correct, and it must
    add that Testcontainers' mapped ports are random **by construction**, which is why they are
    parallel-safe.
18. **§ 10's `SyncTaskExecutor` advice** must add the `@Async` self-invocation caveat and the
    `@TransactionalEventListener(AFTER_COMMIT)` caveat, because both make an async test pass for the
    wrong reason.
19. **§ 12's coverage paragraph** must add the branch-vs-line distinction; as written it says
    "which lines executed", which understates the problem — branch coverage is also gameable and
    JaCoCo excludes exception paths from it entirely.
20. **§ 12's PIT description** ("it mutates the bytecode (flips `>` to `>=`, returns null, removes a
    call)") maps exactly onto three named default operators — Conditionals Boundary, Null Returns,
    Void Method Calls — and should name them, plus state the eleven-operator default set.
21. **§ 12's "run it on the domain layer or nightly, not per commit"** is right and must gain the
    *reason* (§ 3.12.12: each mutant would pay a Spring context startup) and the modern refinement
    (incremental/SCM mode makes per-commit viable on changed files).
22. **§ 13's CDC flow** must name the artifacts and tools: `@Pact`/`@PactTestFor` on the consumer,
    `@Provider`/`@State` on the provider, the specification version, and **match-on-type matchers** —
    without which a reader would write a value-matched contract that breaks on every data change.
23. **§ 13 must state what contract testing does not prove** (behaviour), and must name the
    producer-driven alternative (Spring Cloud Contract) and the schema-registry option, since the
    section currently reads as though CDC is the only answer.
24. **The whole file states no target versions.** That is why several of its claims have quietly aged
    (JUnit 5 as current, Testcontainers 1.x code, `@MockBean` framing, five slices). The bible must
    carry the header version table and mark every version-dependent claim.

---

## Footer

**File size — disk-verified: 4,587 lines.** Counted with `Grep` pattern `^` (`output_mode: count`)
against the written file. Every number below was produced the same way, and the pattern used is
stated so each one is independently reproducible.

**Leaf counts — disk-verified.** Counted with the per-part pattern `^<part>\.[0-9]+\.[0-9]+ `
(`output_mode: count`, which counts matching **lines**; every leaf begins on its own line, so
lines = leaves). The total is independently confirmed by `^[1-5]\.[0-9]+\.[0-9]+ ` = **1,312**, which
equals the sum of the parts. Section counts come from `^## §` = **55**:

| Part | Sections | Leaves | Pattern |
|---|---|---|---|
| PART 1 — Basics (§1.1–§1.12) | 12 | **282** | `^1\.[0-9]+\.[0-9]+ ` |
| PART 2 — Intermediate (§2.1–§2.24) | 24 | **464** | `^2\.[0-9]+\.[0-9]+ ` |
| PART 3 — Under the hood (§3.1–§3.16) | 16 | **296** | `^3\.[0-9]+\.[0-9]+ ` |
| PART 4 — Build it (4.1–4.28) | 1 block, no `## §` heading | **56** | `^4\.[0-9]+\.[0-9]+ ` |
| PART 5 — Interview & retention (§5.1–§5.3) | 3 | **214** | `^5\.[0-9]+\.[0-9]+ ` |
| **Total** | **55** numbered sections + 1 build block | **1,312** | `^[1-5]\.[0-9]+\.[0-9]+ ` |

The PART 4 figure enumerates its members rather than asserting a total: `^4\.[0-9]+\.1 ` = **28**
implementations, each followed by exactly one `4.N.2` Diff table, so 28 + 28 = 56. PART 5's figure
likewise decomposes as **75** questions (§5.1) + **128** traps (§5.2) + **11** recall items (§5.3) =
214. PART 3 contains **28** proofs (§3.14) and a **33**-entry failure catalogue (§3.15).

**Tag inventory — disk-verified.** Each figure is the number of **lines containing at least one
occurrence** of the tag (`output_mode: count` on the escaped literal, e.g. `\[TRAP\]`). A line
carrying the same tag twice counts once. Each count includes **exactly one line from the tag-legend
table**, and for `[RESEARCH]`, `[CURRENCY]`, `[VERSION-TRAP]`, `[X-REF nn]`, `[SOURCE]`, `[NUM]` and
`[STUDY]` a number of lines in the header prose, the scope-boundary list, the sources table and the
gap table. Subtract accordingly when auditing leaf-attached tags:

| Tag | Lines containing it | Pattern |
|---|---|---|
| `[PROVE]` | 411 | `\[PROVE\]` |
| `[TRAP]` | 337 | `\[TRAP\]` |
| `[API]` | 200 | `\[API\]` |
| `[TABLE]` | 199 | `\[TABLE\]` |
| `[RESEARCH]` | 183 | `\[RESEARCH\]` |
| `[X-REF nn]` | 124 | `\[X-REF` |
| `[NUM]` | 94 | `\[NUM\]` |
| `[SOURCE]` | 91 | `\[SOURCE\]` |
| `[DIAG]` | 89 | `\[DIAG\]` |
| `[BUILD]` | 78 | `\[BUILD\]` |
| `[CFG]` | 71 | `\[CFG\]` |
| `[VERSION-TRAP]` | 61 | `\[VERSION-TRAP\]` |
| `[FLOW]` | 57 | `\[FLOW\]` |
| `[CLI]` | 23 | `\[CLI\]` |
| `[SPEC]` | 23 | `\[SPEC\]` |
| `[CURRENCY]` | 16 | `\[CURRENCY\]` |
| `[METRIC]` | 14 | `\[METRIC\]` |
| `[STUDY]` | 10 | `\[STUDY\]` |
| `[WIRE]` | 3 | `\[WIRE\]` |

`[WIRE]` at 3 lines is the weakest tag in the file and is honest about it: testing has little raw
protocol surface. The three uses are `UniqueId`'s string form, Testcontainers' container labels, and
Ryuk's filter protocol. The write pass should not manufacture more.

**`[RESEARCH]` clustering.** The `[RESEARCH]` marks concentrate in exactly the places where recall is
least trustworthy and where the fetch phase failed: the **Jupiter extension-point list and the
autodetection property** (the extension-model chapter 404'd), the **`@ParameterizedTest` source
attributes** (the parameterized chapter 404'd), **Mockito's verification modes and `Answers`
constants** (only an older javadoc was reachable), **Mockito's inline-maker internals** (read from
source references, not prose), **every Boot 4 / Framework 7 testing change** (taken from a secondary
blog and needing docs.spring.io confirmation), **Testcontainers 2.0's rename list and Ryuk's grace
period and label keys**, **Testcontainers startup-cost figures** (estimates, not measurements),
**the xUnit test-smell names** (the catalogue would not fetch), **the flaky-test root-cause
percentages** (search summary, not the paper), **PIT's timeout defaults and bytecode-level operator
implementations**, **JaCoCo's probe-placement algorithm and overhead figure**, **jqwik's JUnit 6
compatibility**, **Awaitility's `pollDelay` default**, and **every version number and release date in
the header**. All 35 carried-forward items are listed above. **Every one must be re-fetched from its
cited source before the write pass commits a number or an exact name.**

**Target version restated for the write pass:** JUnit **6.1.3** (with JUnit 5.14.x deltas called out
as the previous generation), Mockito **5.23.0** with the inline mock maker as default, AssertJ
**3.27.7**, Hamcrest **3.0**, Awaitility **4.3.0**, jqwik **1.10.1**, Testcontainers for Java
**2.0.5** (with 1.21.4 deltas called out), Spring Boot **4.1.1** / Spring Framework **7.0.x** (with
Boot 3.5.x deltas called out, since that is what most codebases run), Pact Specification **V4**,
current PIT and JaCoCo release lines, **Java 21 LTS** for all code. State the baseline in the
bible's header and mark every version-dependent claim with `[CURRENCY]` or `[VERSION-TRAP]`. Where
the write pass cannot re-verify a version, it must say so rather than state a number.

**Split guidance.** At 1,312 leaves the bible will substantially exceed ~2,500 lines. Split into
`src/topics/16-testing.md` (PARTS 1–2 — the vocabulary, the pyramid, the doubles, JUnit and Mockito
as APIs, assertions, Spring test slices and context economics, Testcontainers, HTTP stubbing,
contract testing, coverage and mutation testing as practices, flakiness, TDD/BDD, legacy code, CI,
and the decision procedures) and `src/topics/16-testing-internals.md` (PARTS 3–5 — the Platform
launcher and engine SPI, the extension model and the store, parallel execution, Mockito's bytecode
internals, the Spring `TestContext` framework and the slice machinery, Testcontainers and Ryuk,
JaCoCo and PIT internals, the 28 proofs, the 33-entry failure catalogue, the version history, the 28
builds, and the interview layer). Cross-link both at the top, keep an `## Atomic concept checklist`
in each, add the new file to `src/topics/00-index.md`, and update topic 16's scope line — which
currently reads "The test pyramid, JUnit 5 mechanics, Mockito…, Spring Boot test slices,
Testcontainers, contract testing, flaky-test causes, mutation testing, and what coverage does and
does not tell you" — to match what the files then actually contain, including the JUnit 6 / Boot 4 /
Testcontainers 2 currency, the internals, the proofs and the builds.
