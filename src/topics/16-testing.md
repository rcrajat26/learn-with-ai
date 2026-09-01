# 16 — Testing

Testing interviews probe whether you can articulate *what a given test proves* and *what it costs*.
The two places candidates lose points are the test-doubles taxonomy (mock vs stub vs fake, and where
mocking is legitimate) and flakiness (naming the cause, not just "we retry it"). Both get full
sections here.

---

## 1. The ladder of test types

| Type | Scope | Dependencies | Typical time | Proves |
|---|---|---|---|---|
| **Unit** | one class/function | none real | <10ms | the logic is correct |
| **Slice** | one Spring layer (`@WebMvcTest`, `@DataJpaTest`) | partial context | 0.1–2s | the wiring in that layer works |
| **Integration** | several components + real infra | DB, broker via Testcontainers | 1–30s | the pieces fit together and the SQL is valid |
| **Contract** | the interface between two services | none (a pact file) | fast | consumer and provider agree |
| **End-to-end** | the whole deployed system | everything | minutes | a user journey works |
| **Smoke** | a handful of critical paths post-deploy | production/staging | seconds | the deploy isn't broken |
| **Acceptance** | a business scenario, business language | varies | varies | we built what was asked |

**Pyramid rationale.** Many fast unit tests, fewer integration tests, very few E2E. The reason isn't
dogma, it's four properties that degrade as you go up: **speed** (feedback loop), **determinism**
(more moving parts, more flakiness), **failure localisation** (a unit failure names the bug; an E2E
failure names "checkout broke"), and **maintenance cost** (E2E tests break on every UI tweak).

The counter-position worth knowing: the "testing trophy" argues integration tests carry the best
confidence-per-cost for typical web backends, because most real bugs live in the seams (SQL,
serialization, transaction boundaries) that unit tests mock away. A good answer acknowledges both:
**unit-test logic, integration-test integration, and don't unit-test glue code by mocking it into
meaninglessness.**

---

## 2. Test doubles — the taxonomy

Meszaros's terms. Interviewers ask this specifically because "mock" is used sloppily for all five.

| Double | What it is |
|---|---|
| **Dummy** | passed to satisfy a signature, never used |
| **Stub** | returns canned answers to calls; **state verification** — you assert on the result |
| **Spy** | a real object that also records how it was called |
| **Mock** | pre-programmed with expectations; **behaviour verification** — you assert it *was called* |
| **Fake** | a real, working, simplified implementation (in-memory repository, H2, a hash map) |

The practically important distinction: **a stub feeds input to the test; a mock asserts on output
you can't otherwise see.** If you can assert on the returned value or the resulting state, stub and
assert on that — it's less brittle. Reserve `verify()` for genuine side effects with no observable
result (an email was sent, an event was published).

### When to mock, and when not to

- **Mock at the boundaries you own** — your `PaymentGateway` interface, your `Repository` interface.
  Cheap and stable, because you control the signature.
- **Wrap third-party clients and mock the wrapper.** Mocking a vendor SDK's fluent builder ties your
  test to their API shape; when they refactor, your tests break without any behaviour changing. An
  adapter interface you own is the seam.
- **Never mock pure logic or value objects.** Mocking a `BigDecimal`, a mapper, or a pure calculator
  tests nothing but your mock configuration.
- **Never mock what you're testing** (`@Spy` on the class under test with partial stubbing is almost
  always a sign the class does two things and should be split).
- **Prefer a fake over a mock for anything stateful.** An in-memory `Map`-backed repository gives you
  a repository that actually behaves like one — reads see writes — with none of the stubbing noise.

**Trap:** over-mocking produces tests that pass while the system is broken, because every collaborator
returns exactly what the test told it to. If a test's setup is longer than the code under test, the
design or the test approach is wrong.

---

## 3. Mockito mechanics

```java
@ExtendWith(MockitoExtension.class)
class OrderServiceTest {
    @Mock OrderRepository repo;
    @Mock PaymentGateway payments;
    @InjectMocks OrderService service;
```

**`when(...).thenReturn(...)` vs `doReturn(...).when(...)`.** `when(mock.foo())` **actually calls**
`foo()` on the mock to record the stubbing. On a plain mock that's harmless. On a `@Spy` (a real
object) it executes the real method — with real side effects. It also fails when the method is `void`
or when the return type doesn't match. `doReturn(x).when(spy).foo()` never invokes the method, so:

- `when/thenReturn` — default, type-safe, use for plain mocks.
- `doReturn/when` — required for spies, `void` methods (`doNothing`, `doThrow`), and consecutive-call
  stubbing on spies.

**Argument matchers are all-or-nothing.** `when(repo.find(anyLong(), "ACTIVE"))` throws
`InvalidUseOfMatchersException`; use `eq("ACTIVE")`.

**`ArgumentCaptor`** — for asserting on what was passed to a void/side-effecting collaborator:

```java
var captor = ArgumentCaptor.forClass(Order.class);
verify(repo).save(captor.capture());
assertThat(captor.getValue().getStatus()).isEqualTo(SHIPPED);
```

Use a captor when you want to assert on *properties* of the argument; use an `eq`/argThat matcher when
you want the verification itself to be the assertion. A captor's failure message is much better.

**`@Mock` vs `@MockBean` vs `@MockitoBean`.** `@Mock` is plain Mockito — no Spring, microseconds.
`@MockBean` (deprecated in Boot 3.4 for `@MockitoBean`) replaces a bean **in the Spring context**,
which means the context no longer matches any cached one — **each distinct set of mock beans creates
and caches a new application context.** Twenty test classes with slightly different `@MockBean` sets
means twenty context startups and a build that takes minutes. Keep the mock-bean configuration
uniform, or push the test down to plain Mockito.

**The `verify` anti-pattern.** `verify(repo).save(order)` on a test that already asserts the returned
order is redundant, and it welds the test to the implementation: refactor `save` to `saveAll` and the
test fails though behaviour is identical. Verify side effects with no other observable trace; assert
on state everywhere else. Similarly, `verifyNoMoreInteractions` on everything makes every test
maximally brittle.

Strict stubs (the default with `MockitoExtension`) fail the test on unused stubbings — that's a
feature; it catches tests that have drifted from the code.

---

## 4. JUnit 5

Lifecycle: `@BeforeAll` (static, once per class) → `@BeforeEach` → `@Test` → `@AfterEach` →
`@AfterAll`. A **new test instance per method** by default, so instance fields are naturally isolated
(`@TestInstance(PER_CLASS)` changes that and lets `@BeforeAll` be non-static).

```java
@ParameterizedTest
@CsvSource({"100, 0.0, 100", "100, 0.1, 90", "0, 0.5, 0"})
void appliesDiscount(BigDecimal price, BigDecimal rate, BigDecimal expected) { ... }
```

Sources: `@ValueSource`, `@CsvSource`, `@MethodSource` (a static factory of `Arguments`, for objects),
`@EnumSource`, `@NullAndEmptySource`. Parameterized tests are the right tool the moment you'd
copy-paste a test and change one literal — especially for boundary cases.

```java
var ex = assertThrows(InsufficientFundsException.class, () -> account.withdraw(200));
assertThat(ex.getMessage()).contains("balance");
```

Never `try { ...; fail(); } catch (E e) {}` — `assertThrows` also lets you assert on the exception.
`assertAll(...)` reports every failed assertion instead of stopping at the first.

Other useful pieces: `@DisplayName` for readable reports, `@Nested` to group by scenario with shared
setup, `@Tag` + build filtering to split fast/slow suites, `@Disabled` **with a reason and a ticket**.

---

## 5. AssertJ, and comparing BigDecimal

AssertJ's fluent chain gives far better failure messages than JUnit's assertions:

```java
assertThat(orders)
    .hasSize(3)
    .extracting(Order::getStatus)
    .containsExactly(NEW, PAID, SHIPPED);

assertThat(order)
    .usingRecursiveComparison()
    .ignoringFields("id", "createdAt")
    .isEqualTo(expected);
```

**BigDecimal:** `assertThat(total).isEqualTo(new BigDecimal("10.00"))` **fails** against
`new BigDecimal("10.0")` — `BigDecimal.equals` compares scale as well as value. Use
`isEqualByComparingTo("10.00")`, which uses `compareTo`. This is a favourite gotcha and it comes
straight from `03-java-core.md`'s money section. For doubles, always assert with a tolerance
(`isCloseTo(x, within(0.001))`).

**`assertEquals` argument order is `(expected, actual)`.** Reversing it produces backwards failure
messages ("expected 5 but was 3" when it's the other way round) that waste debugging time. AssertJ
sidesteps this entirely, which is a good reason to standardise on it.

---

## 6. Controlling time and randomness

Untestable code is usually code that reaches out to a global: `Instant.now()`, `new Random()`,
`UUID.randomUUID()`, `System.getenv`. **Inject them.**

```java
@Service
class SubscriptionService {
    private final Clock clock;
    SubscriptionService(Clock clock) { this.clock = clock; }

    boolean isExpired(Subscription s) { return s.getEndsAt().isBefore(Instant.now(clock)); }
}

// production
@Bean Clock clock() { return Clock.systemUTC(); }
// test
var clock = Clock.fixed(Instant.parse("2026-03-01T00:00:00Z"), ZoneOffset.UTC);
```

`Clock` is in `java.time` precisely for this. Same pattern for `Supplier<UUID>`, a seeded `Random`,
and an `IdGenerator`. The payoff is not just testability — you can test the leap-year, month-end, and
DST cases that are otherwise unreachable.

**Trap:** `Thread.sleep` in a test to "wait for the clock to move". It's slow and still racy.

---

## 7. Flaky tests: cause × fix

A flaky test is worse than no test — it trains the team to ignore red builds. Diagnose by cause:

| Cause | Symptom | Fix |
|---|---|---|
| **Shared mutable state between tests** | fails only in a certain order, or only in the full suite | reset state in `@AfterEach`; `@DirtiesContext` sparingly; no static caches |
| **Test order dependence** | passes alone, fails in suite | make each test set up its own data; randomise order deliberately to expose it |
| **Timing / `Thread.sleep`** | fails on a loaded CI box | Awaitility polling with a condition, not a fixed sleep |
| **Real async without synchronisation** | intermittent nulls | await the future, use a deterministic executor, or `CountDownLatch` |
| **Wall-clock / date logic** | fails at month end, midnight, DST, or in another TZ | inject `Clock`; pin the timezone and locale in the build |
| **Unseeded randomness** | fails 1 in 50 | seed it, or inject the generator |
| **Port/resource collisions** | fails when tests run in parallel | random ports (`webEnvironment = RANDOM_PORT`), Testcontainers' mapped ports |
| **External network calls** | fails when a third party is down | WireMock/MockWebServer; never call real services in CI |
| **Leaked DB state** | second run fails on a unique key | transactional rollback per test, or truncate/recreate; unique data per test |
| **Iteration order assumptions** | fails after an unrelated change | don't assume `HashMap`/`HashSet` order; assert with `containsExactlyInAnyOrder` |

Rule: **quarantine, then fix or delete — never `@Retry` as the resolution.** A retried test hides a
real race that will surface in production.

---

## 8. H2 vs Testcontainers

H2 (or any in-memory DB in "PostgreSQL mode") is fast and needs no Docker. It also **lies**. It has a
different SQL dialect, different type coercion, no native `JSONB`/arrays/`ON CONFLICT` nuances,
different locking and isolation behaviour, no real query planner, and different constraint error
messages. Tests pass; production fails on the exact query you thought you'd tested. That false
confidence is the reason to avoid it.

**Testcontainers runs the real database in Docker:**

```java
@Testcontainers
@SpringBootTest
class OrderRepositoryIT {
    @Container
    static PostgreSQLContainer<?> db = new PostgreSQLContainer<>("postgres:16-alpine");

    @DynamicPropertySource
    static void props(DynamicPropertyRegistry r) {
        r.add("spring.datasource.url", db::getJdbcUrl);
        r.add("spring.datasource.username", db::getUsername);
        r.add("spring.datasource.password", db::getPassword);
    }
}
```

`static` container + JUnit's per-class lifecycle means one startup shared across the class; the
**reusable containers** flag or a singleton-container base class shares it across the whole suite,
which is what keeps this fast enough to be the default. Same approach for Kafka, Redis, LocalStack.

The honest trade-off: Testcontainers needs a Docker daemon in CI and adds seconds of startup. Worth
it for anything touching SQL. H2 is defensible only for tests that don't exercise real queries at all
— and in that case, prefer not touching a database.

---

## 9. Spring Boot test slices

| Annotation | Loads | Use for |
|---|---|---|
| `@WebMvcTest(OrderController.class)` | MVC layer, converters, `@ControllerAdvice`, security filters — **no services or repositories** | controller mapping, validation, status codes, JSON shape |
| `@DataJpaTest` | JPA, repositories, an embedded DB by default, **transactional and rolled back per test** | queries, mappings, custom `@Query` |
| `@JsonTest` | Jackson only | serialization contracts |
| `@RestClientTest` | `RestTemplate`/`RestClient` + `MockRestServiceServer` | outbound HTTP clients |
| `@SpringBootTest` | the **whole** context | integration and E2E-ish tests |

```java
@WebMvcTest(OrderController.class)
class OrderControllerTest {
    @Autowired MockMvc mvc;
    @MockitoBean OrderService service;   // the collaborator isn't in the slice, so provide it

    @Test void returns404() throws Exception {
        when(service.find(9L)).thenThrow(new NotFoundException("nope"));
        mvc.perform(get("/orders/9"))
           .andExpect(status().isNotFound())
           .andExpect(jsonPath("$.title").value("Not Found"));
    }
}
```

**Cost model:** slices start a smaller context and Spring **caches contexts by configuration key**, so
the second test with an identical configuration is nearly free. Anything that changes the key —
`@MockBean`/`@MockitoBean`, `@TestPropertySource`, active profiles, `@DirtiesContext` — forces a new
context. That is the number-one cause of slow Spring test suites. Standardise your test
configuration; avoid `@DirtiesContext` unless you genuinely mutated the context.

Add `@AutoConfigureMockMvc(addFilters = false)` only when you deliberately want to skip security —
otherwise your controller tests won't catch an auth misconfiguration.

`@DataJpaTest` rolls back each test, which is convenient but means you **never see the flush**. Add
`TestEntityManager.flush()`/`clear()` when you want to test what actually hits the database, or your
constraint violations and dirty-checking behaviour go untested (see `08-spring-data-jpa.md`).

---

## 10. Testing async code

```java
service.processAsync(orderId);

await().atMost(Duration.ofSeconds(5))
       .pollInterval(Duration.ofMillis(50))
       .untilAsserted(() -> assertThat(repo.findById(orderId)).get()
                              .extracting(Order::getStatus).isEqualTo(PROCESSED));
```

Awaitility polls a condition with a timeout — fast when the work finishes quickly, and it fails with
the *assertion's* message rather than a bare timeout. `Thread.sleep(2000)` is strictly worse: always
slow, and still flaky on a loaded CI machine.

Better still where possible: make the async boundary injectable. Inject a `TaskExecutor` and use a
`SyncTaskExecutor` in tests, so the whole flow becomes deterministic and synchronous. Test the
*asynchrony* itself once, separately, rather than in every test that happens to cross it.

---

## 11. Structure and naming

**Given–When–Then** (Arrange–Act–Assert) with blank lines separating the three, one logical assertion
per test. Name tests as behaviour statements:
`withdraw_throwsInsufficientFunds_whenBalanceBelowAmount()` — a failing test name should tell you
what broke without opening the file.

**Test the behaviour, not the implementation.** A test that asserts "this private method was called"
blocks refactoring; a test that asserts "given a balance of 10, withdrawing 20 throws" survives any
rewrite. This is the property that makes a test suite an asset rather than a liability.

---

## 12. Coverage, mutation testing, and legacy code

**Coverage measures which lines executed, not whether anything was asserted.** A test suite with no
assertions can hit 100%. Use it as a *floor* to find untested areas, never as a target — Goodhart's
law applies immediately, and a mandated 90% produces getter tests.

**Mutation testing (PIT)** actually measures test quality: it mutates the bytecode (flips `>` to
`>=`, returns null, removes a call) and checks whether a test fails. A surviving mutant is a line
your tests execute but do not verify. Slow, so run it on the domain layer or nightly, not per commit.

**Characterization tests for legacy code.** Before changing code with no tests and unclear behaviour:
write tests that assert what it *currently* does — including the bugs. They are not correctness
tests; they're a change-detector that turns "I hope this refactor is safe" into "the build tells me".
Then refactor, then fix the bug as a deliberate, visible test change. Pair with an approval/golden-
master test (snapshot the output for many inputs) when the output is large.

---

## 13. Contract testing

The problem: service A mocks service B in its tests, B changes its response shape, both suites are
green, production breaks. E2E tests would catch it but are slow and require deploying everything.

**Consumer-driven contracts (Pact, Spring Cloud Contract):**

1. The **consumer** writes a test against a mock provider, declaring the request it sends and the
   response fields it needs. This generates a **pact file** — the contract.
2. The pact is published to a broker.
3. The **provider** runs **provider verification** in its own build: the pact's requests are replayed
   against the real provider (with defined states, e.g. "an order 42 exists"), and the responses are
   checked against the contract.
4. The provider's build fails if it would break a real consumer. `can-i-deploy` gates the release on
   every consumer's contract passing.

The key properties: the contract states only what the consumer **actually uses** (so the provider is
free to add fields), no shared environment or simultaneous deployment is needed, and each side runs
independently in its own pipeline. That is what makes it viable where E2E isn't.

---

## Atomic concept checklist

- [ ] I can place unit, slice, integration, contract, E2E, smoke, and acceptance tests on a ladder by scope and cost.
- [ ] I can justify the pyramid with speed, determinism, failure localisation, and maintenance cost — and I know the testing-trophy counter-argument.
- [ ] I can define dummy, stub, spy, mock, and fake, and state that a stub feeds input while a mock asserts an unobservable call.
- [ ] I mock boundaries I own, wrap and mock third-party clients, and never mock pure logic or value objects.
- [ ] I prefer a fake over a mock for stateful collaborators.
- [ ] I know `when(mock.foo())` really invokes the method, so spies and void methods need `doReturn/doThrow ... when`.
- [ ] I know argument matchers are all-or-nothing and need `eq()` for literals.
- [ ] I use `ArgumentCaptor` to assert on the properties of a captured argument.
- [ ] I know `@MockBean`/`@MockitoBean` changes the context cache key and multiplies context startups.
- [ ] I treat blanket `verify()` as an anti-pattern and assert on state where state is observable.
- [ ] I know JUnit 5 creates a new test instance per method by default.
- [ ] I use `@ParameterizedTest` with `@CsvSource`/`@MethodSource` instead of copy-pasted near-identical tests.
- [ ] I use `assertThrows` and assert on the exception, never try/fail/catch.
- [ ] I compare BigDecimal with `isEqualByComparingTo` because `equals` includes scale.
- [ ] I know `assertEquals(expected, actual)` argument order and why reversing it wastes debugging time.
- [ ] I inject `Clock` and any random/UUID source so time and randomness are deterministic in tests.
- [ ] I can name at least six causes of flakiness and the specific fix for each, and I never resolve flakiness with a retry.
- [ ] I know H2 gives false confidence through dialect, type, locking, and planner differences, and I use Testcontainers for anything touching SQL.
- [ ] I know a static Testcontainer plus context caching is what keeps integration tests fast enough to be the default.
- [ ] I can pick the right slice — `@WebMvcTest`, `@DataJpaTest`, `@JsonTest`, `@RestClientTest`, `@SpringBootTest` — and say what each loads.
- [ ] I know Spring caches contexts by configuration key and that `@DirtiesContext` and ad-hoc mock beans destroy that caching.
- [ ] I know `@DataJpaTest` rolls back per test, so I flush explicitly to test what really hits the database.
- [ ] I test async with Awaitility's `untilAsserted`, or by injecting a synchronous executor — never `Thread.sleep`.
- [ ] I write given-when-then with behaviour-describing test names that explain a failure without opening the file.
- [ ] I know coverage measures execution, not assertion, and that mutation testing measures whether tests actually verify.
- [ ] I use characterization tests to pin existing behaviour, bugs included, before refactoring legacy code.
- [ ] I can explain consumer-driven contract testing: consumer generates the pact, provider verification runs in the provider's build, `can-i-deploy` gates release.