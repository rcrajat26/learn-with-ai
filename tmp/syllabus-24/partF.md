---

# PART 4 — BUILD IT

PART 4 owns the from-scratch implementations. Every pattern PARTS 1–3 named as structure is
built here as compiling Java 21 against QuizStakes types, small enough to read in one sitting
and complete enough to run. Each section names the types, the method signatures, the policy
constants, the edge cases and the concurrency requirement the write pass must ship — and ends
with a table diffing the toy against the production library it imitates.

## §4.1 A DI container — constructor injection, singleton scope, circular-dependency detection

4.1.1 Target API: `final class MiniContainer` with `void register(Class<?> impl)`,
      `void registerInstance(Object bean)`, `void refresh()`, `<T> T get(Class<T> type)`.
      Registration is separate from instantiation so the whole graph is known before any
      object exists. `[BUILD]` `[API]`

4.1.2 `record BeanDefinition(Class<?> type, Constructor<?> injectionPoint,
      List<Class<?>> dependencies, Scope scope)` — built once in `refresh()` from
      `type.getDeclaredConstructors()`; `enum Scope { SINGLETON, PROTOTYPE }`. `[BUILD]` `[API]`

4.1.3 Constructor-selection rule: exactly one non-default constructor → use it; several →
      require a `@Inject`-equivalent marker; none → the no-arg constructor. State the rule as
      code, not prose, because this is the one place Spring's behaviour is version-dependent
      (single-constructor autowiring is implicit since Spring 4.3). `[BUILD]` `[VERSION-TRAP]`

4.1.4 Singleton scope: `Map<Class<?>, Object> singletons` plus `Set<Class<?>> inCreation`.
      The wiring target is `StakeReservationService(FundsLedgerPort, ClientRestrictionsPort,
      IdempotencyStore)` — three constructor parameters, all interfaces, all singletons.
      `[BUILD]` `[API]`

4.1.5 Cycle detection: a `Deque<Class<?>> creationStack` pushed before recursion and popped
      after. Prove that the containment check happens *before* the recursive `get()` call, so
      `ClientRestrictionsAdapter → FundsLedgerAdapter → ClientRestrictionsAdapter` throws
      `CircularDependencyException` carrying the full path rather than exhausting the stack
      with `StackOverflowError`. `[PROVE]` `[BUILD]`

4.1.6 Multi-binding: injecting `List<RestrictionRule>` (every registered implementation) and
      `Map<String, PayoutRail>` keyed by an explicit `key()` method rather than by bean name —
      the §1.20 strategy-registry idiom, now implemented rather than described. `[BUILD]`

4.1.7 Edge cases the implementation must reject or resolve by name: a port with no registered
      adapter; two adapters for one port with no qualifier; a `PROTOTYPE` bean injected into a
      `SINGLETON` (the scope-mismatch trap); `get()` called before `refresh()`; a bean whose
      constructor throws. `[BUILD]` `[TRAP]`

4.1.8 Concurrency requirement: `get()` called from 8 `ClientRestrictions` request threads must
      produce exactly one instance. Show why `computeIfAbsent` on a `ConcurrentHashMap`
      deadlocks here (recursive update during the mapping function) and why the correct shape
      is a per-definition lock plus a double-check on the singleton map. `[PROVE]` `[BUILD]`

4.1.9 Eager vs lazy instantiation: `refresh()` instantiates every singleton so a missing
      adapter fails at startup, not on the first stake — the "where does the error surface"
      axis from §2.30, made a one-line policy decision. `[DECIDE]`

4.1.10 Diff vs the real one — this container against Spring's
       `DefaultListableBeanFactory`: `BeanPostProcessor`, `ObjectFactory`/`@Lazy` cycle
       breaking, the three-level `singletonObjects`/`earlySingletonObjects`/`singletonFactories`
       caches, `FactoryBean`, `@DependsOn`, scoped proxies, `AbstractBeanFactory.doGetBean`'s
       creation-status tracking, and `spring.main.allow-circular-references=false` as the
       Boot 2.6+ default. `[TABLE]` `[API]` `[VERSION-TRAP]`

*(10 leaves)*

## §4.2 A proxy-based interceptor chain

4.2.1 Target API: `interface MethodInterceptor { Object invoke(Invocation inv) throws
      Throwable; }` and `record Invocation(Object target, Method method, Object[] args,
      List<MethodInterceptor> chain, int index)` with `Object proceed()`. The chain is a
      cursor over an immutable list, not a linked list of wrappers. `[BUILD]` `[API]`

4.2.2 `ProxyFactory.create(Class<T> port, T target, List<MethodInterceptor> chain)` over
      `Proxy.newProxyInstance(loader, new Class[]{port}, handler)` — the JDK dynamic-proxy
      path from §3.7, now called rather than described. `[BUILD]` `[API]`

4.2.3 The three interceptors to ship, in the order they must run around
      `ClientRestrictionsPort.decide(ClientId, Action)`: `TimingInterceptor` (records against
      the 30 ms p99 budget), `TransactionInterceptor` (begin/commit/rollback), and
      `RetryInterceptor` — and the argument for why timing must be outermost if the metric is
      to include the retries. `[BUILD]` `[NUM]` `[PROVE]`

4.2.4 `equals`, `hashCode` and `toString` must be handled explicitly in the handler or the
      proxy's identity is the handler's; `Object`-declared methods and interface `default`
      methods take different paths (`InvocationHandler.invokeDefault` since Java 16).
      `[BUILD]` `[API]` `[VERSION-TRAP]`

4.2.5 Self-invocation: demonstrate the bypass by having the target's
      `reserveAndSettle()` call `this.reserve()` and showing the interceptor count is 1, not
      2. This is the §3.8 trap turned into an executable assertion. `[PROVE]` `[TRAP]`

4.2.6 Edge cases: an interceptor that never calls `proceed()` (short-circuit — legal, and how
      it differs from a decorator that skips its delegate); an interceptor that calls
      `proceed()` twice; exception translation and preserving the original stack trace;
      `InvocationTargetException` unwrapping. `[BUILD]` `[TRAP]`

4.2.7 Concurrency requirement: one proxy instance serves all threads, so `Invocation` must be
      per-call — prove that holding the cursor `index` as mutable state on the handler
      produces cross-request interference under the 1,200/sec stake rate. `[PROVE]` `[BUILD]`

4.2.8 Cost measurement: the added nanoseconds per hop, and the arithmetic against the 30 ms
      restriction budget that shows why interceptor depth is a non-issue here and would not be
      on a 100 ns in-memory lookup. `[NUM]` `[X-REF 25]`

4.2.9 Diff vs the real one — against Spring's `ReflectiveMethodInvocation` and
      `JdkDynamicAopProxy`: `AdvisedSupport`, pointcut matching and its cache,
      `MethodInterceptor` ordering via `@Order`/`Ordered`, `ProxyFactory.setProxyTargetClass`,
      `ExposeInvocationInterceptor`, and CGLIB's `MethodProxy.invokeSuper` fast path.
      `[TABLE]` `[API]`

*(9 leaves)*

## §4.3 A plugin registry over `ServiceLoader`

4.3.1 Target API: `interface DocumentVendorAdapter { String vendorId(); Verdict
      verify(DocumentUpload upload); }` discovered at runtime, plus
      `final class VendorRegistry { Optional<DocumentVendorAdapter> byId(String); Set<String>
      known(); }`. `[BUILD]` `[API]`

4.3.2 The two declaration mechanisms and the one that is current:
      `META-INF/services/quizstakes.docs.DocumentVendorAdapter` (classpath) versus
      `provides ... with ...` in `module-info.java` (JPMS). State both; state that the
      classpath form still works and is what a Boot fat jar uses. `[API]` `[VERSION-TRAP]`

4.3.3 `ServiceLoader.load(DocumentVendorAdapter.class, classLoader)` versus
      `ServiceLoader.load(Class)` — the thread-context-classloader difference and why it
      matters in a container. Iterate with `stream()` and `Provider::type` to inspect
      candidates without instantiating them. `[BUILD]` `[API]`

4.3.4 Eager-index-at-startup policy: build the `Map<String, DocumentVendorAdapter>` in the
      constructor, fail on a duplicate `vendorId()`, and assert that every vendor id present
      in `DocumentVerification`'s configuration has a provider — the startup assertion §10 of
      the current guide only names in passing. `[BUILD]` `[DECIDE]`

4.3.5 Edge cases: a provider whose constructor throws (`ServiceConfigurationError`, and that
      iteration is lazy so the error arrives mid-loop); an entry naming a class not on the
      classpath; a provider not implementing the interface; two jars each providing the same
      `vendorId`. `[BUILD]` `[TRAP]`

4.3.6 Concurrency requirement: `ServiceLoader` is explicitly not thread-safe for iteration,
      so discovery happens once on one thread and the resulting map is published as
      `Map.copyOf(...)` in a `final` field — the safe-publication rule from `05`, applied.
      `[PROVE]` `[X-REF 05]`

4.3.7 Hot-swap boundary: `ServiceLoader.reload()` exists and does not give you plugin
      reloading, because the old classes stay loaded until their loader is unreachable. Name
      the child-first-`ClassLoader`-per-plugin design as the real answer and stop there.
      `[TRAP]` `[X-REF 06]`

4.3.8 Diff vs the real one — against Spring's `SpringFactoriesLoader` and Boot's
      `AutoConfiguration.imports`: `META-INF/spring/…AutoConfiguration.imports` replacing
      `spring.factories` in Boot 2.7/3.0, argument resolution, `@ConditionalOnClass`,
      ordering, and why Boot needed its own mechanism rather than `ServiceLoader`.
      `[TABLE]` `[API]` `[VERSION-TRAP]`

*(8 leaves)*

## §4.4 A state-machine engine with guards, actions and illegal-transition rejection

4.4.1 Target API: `final class StateMachine<S extends Enum<S>, E>` with
      `Builder<S,E> transition(S from, E on, S to)`, `.guard(Predicate<Context>)`,
      `.action(Consumer<Context>)`, and `S fire(S current, E event, Context ctx)`. `[BUILD]` `[API]`

4.4.2 The machine to encode is `DocumentVerification`'s document states verbatim from the
      scenario: `AA-600 DOCUMENTS_REQUESTED` → `AA-610 DOCUMENTS_UPLOADED` →
      {`AA-611 DOCUMENTS_VERIFIED`, `AA-650 DOCUMENTS_REFERRED`, `AA-690 DOCUMENTS_REJECTED`},
      `AA-690` → `AA-610` (re-upload), `AA-699 DOCUMENTS_EXHAUSTED`, `AA-700 REVIEW_QUEUED`,
      `AA-710`, `AA-711`, `AA-799`. `[BUILD]` `[API]`

4.4.3 Transition-table representation: `EnumMap<S, Map<E, Transition<S>>>` — chosen over a
      `Set<String>` of allowed names because the key domain is small, fixed and enum-typed,
      and lookup is an array index. State the alternative (a nested `switch`) and what it
      loses. `[BUILD]` `[DECIDE]`

4.4.4 Guards as data, with the two real ones: re-upload is permitted only while
      `attemptCount < 3`, and only within the 14-day requirement window — the two conditions
      that produce `AA-699 DOCUMENTS_EXHAUSTED`. A guard returning false is a *rejected*
      transition, not a silent no-op. `[BUILD]` `[NUM]`

4.4.5 Actions and their transactional placement: the action fires after the state field is
      set and before the transaction commits, so `DocumentVerdictIssued` is published
      after-commit (§4.5) rather than from inside the action. `[BUILD]` `[FLOW]`

4.4.6 `IllegalStateTransitionException(S from, E event, S to)` carrying all three, plus the
      set of events that *were* legal from `from` — the error message is the deliverable,
      because this exception is what an operator reads at 3 a.m. `[BUILD]` `[DIAG]`

4.4.7 Edge cases: a terminal state (`AA-799`) receiving any event; the same event legal from
      two states with different targets; an event arriving twice (the vendor callback
      delivered five times); an unknown event; a self-transition. `[BUILD]` `[TRAP]`

4.4.8 Concurrency requirement: `fire()` is pure — it takes the current state and returns the
      next — so the machine holds no per-entity mutable state and one instance serves 6
      `DocumentVerification` instances. Enforcement of "one winner" is the aggregate's
      `@Version`, not a lock in the engine. `[PROVE]` `[X-REF 08]`

4.4.9 The engine belongs inside the aggregate, not in the service layer — restating the §1.22
      trap as a structural property of this implementation: `DocumentCase.apply(event)` calls
      `fire()`; no service does. `[TRAP]` `[BUILD]`

4.4.10 Diff vs the real one — against Spring State Machine and a hand-rolled enum guard:
       persisted machine context, hierarchical and parallel regions, `StateMachineListener`,
       distributed state via ZooKeeper, junction/choice pseudostates, and the argument that a
       200-line engine beats a framework for 12 states. `[TABLE]` `[DECIDE]`

*(10 leaves)*

## §4.5 An event bus with sync, async and after-commit modes

4.5.1 Target API: `interface DomainEvent {}`, `interface Listener<T extends DomainEvent> {
      void on(T event); }`, and `final class EventBus { <T extends DomainEvent> void
      subscribe(Class<T>, Listener<T>, Mode); void publish(DomainEvent); }` with
      `enum Mode { SYNC, ASYNC, AFTER_COMMIT }`. `[BUILD]` `[API]`

4.5.2 The events are QuizStakes events verbatim: `AccountActivated`, `RestrictionApplied`,
      `LedgerMovementPosted`, `DocumentVerdictIssued` — each a record of ids plus
      `Instant occurredAt`, never an entity reference. `[BUILD]` `[API]`

4.5.3 Listener lookup by type: `Map<Class<?>, List<Registration>>` plus supertype walking so
      a `Listener<DomainEvent>` receives everything; the cost of the walk and why the result
      is cached per concrete event class. `[BUILD]`

4.5.4 `SYNC` mode: iterate on the publisher's thread over a snapshot
      (`CopyOnWriteArrayList` or `List.copyOf` at publish time) — prove this is what removes
      the `ConcurrentModificationException` when a listener subscribes during dispatch.
      `[PROVE]` `[BUILD]`

4.5.5 `ASYNC` mode: a bounded `ThreadPoolExecutor` with an explicit
      `ArrayBlockingQueue(capacity)` and `CallerRunsPolicy`, plus the leaf that names the
      alternative and its failure — an unbounded `LinkedBlockingQueue` converts backpressure
      into an OOM on `ClientRestrictions`' 4 GB heap. `[BUILD]` `[TRAP]` `[NUM]`

4.5.6 `AFTER_COMMIT` mode: register a `TransactionSynchronization` on the current transaction
      and dispatch in `afterCommit()`; if no transaction is active, the mode degrades to
      `SYNC` — and the decision of whether that degradation is a silent fallback or an
      exception. `[BUILD]` `[DECIDE]` `[X-REF 07]`

4.5.7 Failure isolation: a listener throwing must not fail the publisher in `ASYNC`/
      `AFTER_COMMIT`, and *must* in `SYNC` — the four observer failure modes of §1.23 become
      four assertions: latency coupling, rollback coupling, reentrancy/CME, and listener leak.
      `[PROVE]` `[BUILD]`

4.5.8 The listener leak, implemented: hold registrations weakly, or require
      `unsubscribe(Registration)` and prove with a heap assertion that a 30–90 minute
      `InternalPlatforms` operator session that registers and never deregisters retains its
      session state for the container's lifetime. `[PROVE]` `[INCIDENT]`

4.5.9 Edge cases: an event published from inside a listener (reentrancy depth limit); ordering
      guarantees across modes (there are none between `ASYNC` listeners); a listener
      registered twice; publishing after `close()`. `[BUILD]` `[TRAP]`

4.5.10 Diff vs the real one — against Spring's `SimpleApplicationEventMulticaster` and
       `@TransactionalEventListener`: `ApplicationEventPublisher`, the
       `ResolvableType`-based listener resolution, `setTaskExecutor` for async,
       `TransactionPhase.{BEFORE_COMMIT, AFTER_COMMIT, AFTER_ROLLBACK, AFTER_COMPLETION}`,
       `fallbackExecution = true`, and `@EventListener(condition = "...")` SpEL.
       `[TABLE]` `[API]`

*(10 leaves)*

## §4.6 A circuit breaker with a sliding window

4.6.1 Target API: `final class CircuitBreaker { <T> T execute(Supplier<T> call) throws
      CallNotPermittedException; State state(); Metrics metrics(); }` fronting
      `CardPspPort.authorise(...)` — the dependency whose p99 is **11 s** with a 15 s timeout
      and a 500/sec rate limit. `[BUILD]` `[API]` `[NUM]`

4.6.2 `enum State { CLOSED, OPEN, HALF_OPEN }` and the config record:
      `failureRateThreshold = 50%`, `slidingWindowSize = 100`, `minimumNumberOfCalls = 20`,
      `waitDurationInOpenState = 30s`, `permittedNumberOfCallsInHalfOpenState = 10`,
      `slowCallDurationThreshold = 3s`, `slowCallRateThreshold = 100%`. Every one of these is a
      leaf because every one of them is a tuning question. `[BUILD]` `[NUM]` `[API]`

4.6.3 Count-based sliding window: a circular `Outcome[] ring` of size N with a head index and
      running aggregate counters, so recording a call is O(1) rather than a rescan. Show the
      aggregate-update arithmetic that subtracts the evicted slot. `[BUILD]` `[PROVE]`

4.6.4 Time-based sliding window: N partial aggregates, one per second, with the head bucket
      advanced on read; and the reason the two window kinds answer different questions —
      "last 100 calls" versus "last 60 seconds", which diverge completely between the
      1,200/sec stake path and the 40/sec deposit path. `[BUILD]` `[DECIDE]` `[NUM]`

4.6.5 `minimumNumberOfCalls` is the guard against opening on a 1-of-1 failure — prove that
      without it, the first timed-out `authorise` at 06:00 (when `BankDeposits` wakes and
      traffic is near zero) trips the breaker for every subsequent deposit. `[PROVE]` `[NUM]`

4.6.6 The state transition must be a CAS, not a `synchronized` block around the whole
      `execute` — `AtomicReference<StateHolder>` with compare-and-set, so 40 concurrent
      deposit threads produce exactly one CLOSED→OPEN transition and exactly one
      `onStateTransition` event. `[PROVE]` `[BUILD]` `[X-REF 05]`

4.6.7 The open-state response is a required decision, not a default: for a card deposit the
      answer is a `DEP-900 FAILED` with a retry-later contract; for a restriction decision the
      answer is fail-closed (refuse the stake). Name both and state that a breaker with no
      defined open-state behaviour only makes failure faster. `[DECIDE]` `[TRAP]`

4.6.8 Edge cases: an exception the breaker must *not* count (a `DEP-290 AUTH_DECLINED` is a
      business outcome, not a failure) via `recordExceptions`/`ignoreExceptions`; a slow but
      successful call; the half-open probe that is itself slow; clock movement in the
      time-based window. `[BUILD]` `[TRAP]`

4.6.9 Interaction with retry and timeout: retries must be bounded *inside* the breaker's unit
      of work or the window counts one logical failure three times — and the timeout must be
      shorter than the caller's budget or the breaker never sees the failure at all. `[PROVE]`
      `[DECIDE]`

4.6.10 Diff vs the real one — against Resilience4j's `CircuitBreakerStateMachine`:
       the six states including `DISABLED`, `FORCED_OPEN` and `METRICS_ONLY`, `RingBitSet`/
       `FixedSizeSlidingWindowMetrics` versus `SlidingTimeWindowMetrics`, per-state
       independent metrics storage, `CircuitBreakerConfig` builder defaults,
       `EventPublisher`, and the decorator-composition order
       `Retry(CircuitBreaker(TimeLimiter(Bulkhead(call))))`. `[TABLE]` `[SOURCE]` `[API]`

*(10 leaves)*

## §4.7 A retry with exponential backoff and full jitter

4.7.1 Target API: `final class Retry { <T> T call(Supplier<T> op); }` with
      `record RetryPolicy(int maxAttempts, Duration base, Duration cap,
      Predicate<Throwable> retryable, Duration totalBudget)`. `[BUILD]` `[API]`

4.7.2 The three named backoff formulas, each stated as arithmetic: fixed
      (`base`), exponential (`min(cap, base * 2^n)`), and **full jitter**
      (`random(0, min(cap, base * 2^n))`); plus equal jitter and decorrelated jitter as the
      variants worth naming. `[BUILD]` `[NUM]`

4.7.3 Prove full jitter de-correlates: with `base = 100 ms`, `cap = 20 s` and 500 clients
      retrying after one PSP blip, plain exponential backoff produces 500 simultaneous
      attempts at t = 100 ms, 300 ms, 700 ms; full jitter spreads attempt *n* uniformly over
      `[0, 2^n · 100 ms)`, so expected concurrent load at any instant falls by the window
      width. Work the arithmetic, do not assert it. `[PROVE]` `[NUM]`

4.7.4 The total-attempt budget: retries must be bounded by wall-clock as well as count,
      because 3 attempts against a dependency with an 11 s p99 can consume 33 s inside a
      client request whose end-to-end budget is **4 s**. `[NUM]` `[DECIDE]`

4.7.5 The retryable predicate is the correctness boundary, and it is domain knowledge, not
      config: retry `DEP-390 CAPTURE_FAILED` **only with the same idempotency key**; never
      retry `DEP-290 AUTH_DECLINED`; never blind-retry a card *capture* whose timeout does not
      tell you whether money moved (PSP capture p50 180 ms, p99 6 s, timeout 10 s).
      `[TRAP]` `[NUM]` `[BUILD]`

4.7.6 Interruption and cancellation: the sleep must be interruptible, `Thread.interrupted()`
      must be restored, and the retry loop must not swallow `InterruptedException` — the
      drain-before-terminate requirement on `BankWithdrawal` depends on it. `[BUILD]` `[TRAP]`

4.7.7 Edge cases: `maxAttempts = 1` (no retry, and the API must not silently mean two);
      `base > cap`; a non-monotonic clock; the last attempt's exception being the one thrown;
      exhausted-budget versus exhausted-attempts as distinguishable outcomes. `[BUILD]`

4.7.8 Virtual threads reshape the cost model: a blocking `Thread.sleep` in a retry loop costs
      a platform thread on a 6-instance service and costs nothing on a virtual thread — state
      the mechanism (unmounting at the sleep) and the one place it does not hold (pinning
      inside `synchronized`). `[VERSION-TRAP]` `[X-REF 05]`

4.7.9 Diff vs the real one — against Resilience4j `Retry`/`IntervalFunction` and Spring
      Retry's `@Retryable`: `IntervalFunction.ofExponentialRandomBackoff`, `RetryConfig`
      defaults (`maxAttempts = 3`, `waitDuration = 500 ms`),
      `retryOnResult`, `failAfterMaxAttempts`, `@Recover`, and Spring Retry's proxy-based
      self-invocation hole. `[TABLE]` `[API]`

*(9 leaves)*

## §4.8 A bulkhead with `Semaphore`

4.8.1 Target API: `final class Bulkhead { <T> T execute(Supplier<T> call) throws
      BulkheadFullException; int available(); }` built on
      `new Semaphore(maxConcurrentCalls, /* fair */ false)`. `[BUILD]` `[API]`

4.8.2 The compartments to size, from the scenario's dependency table: identity vendor
      (p99 38 s, 600/min estate-wide cap), watchlist provider (p99 25 s, 200/min), card PSP
      authorise (p99 11 s, 500/sec). Three bulkheads, three very different numbers. `[NUM]`
      `[API]`

4.8.3 The sizing arithmetic, worked with Little's law: to sustain 600/min = 10/sec against a
      dependency whose p99 is 38 s you need ~380 concurrent permits — which is more than the
      estate cap allows, so the correct answer is a *distributed* limiter and a local bulkhead
      that is deliberately smaller. Show the numbers colliding. `[PROVE]` `[NUM]` `[X-REF 25]`

4.8.4 `tryAcquire(timeout)` versus `acquire()` versus `tryAcquire()`: the wait-duration
      parameter is the whole design, because a zero wait sheds load and an unbounded wait
      reintroduces the queue the bulkhead exists to remove. `[DECIDE]` `[API]`

4.8.5 `release()` must be in a `finally`, and the leaf must show the leak: an exception between
      acquire and the try block permanently loses a permit, and 6
      `DocumentVerification` instances converge on zero available permits over hours — a
      failure that looks like a slow vendor. `[INCIDENT]` `[TRAP]` `[BUILD]`

4.8.6 Semaphore bulkhead versus thread-pool bulkhead: the semaphore variant runs on the
      caller's thread (no context switch, no `ThreadLocal` loss, no timeout enforcement) and
      the pool variant can enforce a timeout and isolate the stack. Name which one the 30 ms
      restriction path wants and why. `[TABLE]` `[DECIDE]`

4.8.7 The global constraint: all bulkheads together must fit the box. Sum the permits against
      `DocumentVerification`'s 8 GB heap and 2–6 MB document buffers to show that 380 permits
      × 6 MB is 2.3 GB of in-flight buffers — the bulkhead is a *memory* bound here, not just
      a concurrency one. `[PROVE]` `[NUM]`

4.8.8 Edge cases: fairness and the starvation it prevents versus the throughput it costs;
      permit count changed at runtime; a call that never returns; nested bulkheads.
      `[BUILD]` `[TRAP]`

4.8.9 Diff vs the real one — against Resilience4j's `SemaphoreBulkhead` and
      `FixedThreadPoolBulkhead`: `BulkheadConfig.maxWaitDuration`, `writableStackTraceEnabled`,
      the `ThreadPoolBulkheadConfig` core/max/queue triple, metrics, and Hystrix's
      thread-isolation default as the historical contrast. `[TABLE]` `[API]`

*(9 leaves)*

## §4.9 An idempotency store enforced by a unique index

4.9.1 Target API: `interface IdempotencyStore { <T> T once(IdempotencyKey key, String
      operation, Supplier<T> body); }` — the signature is the design: the store owns the
      call, so no caller can forget the check. `[BUILD]` `[API]`

4.9.2 The schema is the mechanism: `create table idempotency_record (key varchar(64) not
      null, operation varchar(64) not null, status varchar(16) not null, response jsonb,
      created_at timestamptz not null, constraint uq_idem unique (key, operation))` — the
      composite unique index, because `IdempotencyKey` is scoped per operation type
      (Appendix C.1). `[BUILD]` `[API]` `[SOURCE]`

4.9.3 The correct flow, as an ordered trace: insert the record first inside the caller's
      transaction; on `DuplicateKeyException` read the existing row and replay its stored
      response; on success update to `COMPLETED` with the response. `[FLOW]` `[BUILD]`

4.9.4 Prove that check-then-insert is a race and the unique index is not: two 40/sec deposit
      threads with the same key both `select` and find nothing, both `insert`, and exactly one
      gets the constraint violation. Show the interleaving. `[PROVE]` `[TRAP]`

4.9.5 The in-flight case is the hard one: a row in `IN_PROGRESS` means either a concurrent
      call or a crashed one, and the two need different answers — return `409` with a
      retry-after for the first, and take over after a lease expiry for the second. State the
      lease duration and why it is a business decision. `[DECIDE]` `[NUM]`

4.9.6 The cache is not the guarantee: a `ConcurrentHashMap` with TTL in front of the table is
      a fast path that fails *open* under eviction or partition, and failing open on a card
      capture double-charges. Restate the scenario's own conclusion (Appendix B.2) as code.
      `[TRAP]` `[BUILD]`

4.9.7 Response replay must be byte-identical, including the status code and the
      `Location`/rail reference — a replayed `DEP-301 CAPTURED` that returns a fresh
      `railRef` is a second truth. `[BUILD]` `[TRAP]`

4.9.8 Retention: keys must expire (a `created_at` index plus a delete job), and the retention
      window must exceed the longest possible client retry — for card capture that is the PSP
      timeout plus the client's own retry budget, not "24 hours because that seemed fine".
      `[NUM]` `[DECIDE]`

4.9.9 Edge cases: the same key with a different request body (a client bug — must be rejected,
      not replayed); a key reused across operations; a `SERIALIZABLE` versus
      `READ COMMITTED` isolation difference in what the duplicate insert throws; the outbox
      relay reusing the store. `[BUILD]` `[X-REF 09]`

4.9.10 Diff vs the real one — against Stripe's idempotency-key semantics and Spring's
       `@Idempotent`-style community filters: 24-hour key lifetime, request-fingerprint
       mismatch behaviour, `409 Conflict` on concurrent identical keys, and why the HTTP layer
       is the wrong place for the ledger's `Movement.idempotencyKey`. `[TABLE]` `[X-REF 12]`

*(10 leaves)*

## §4.10 A transactional outbox and its relay

4.10.1 Target API: `interface OutboxWriter { void append(DomainEvent e); }` called from inside
       the same transaction that posts a `Movement`, plus `final class OutboxRelay implements
       Runnable` that drains and publishes. `[BUILD]` `[API]`

4.10.2 The table: `outbox_message(id bigserial, aggregate_type, aggregate_id, event_type,
       payload jsonb, created_at, published_at null, attempts int, partition_key)` — and the
       reason `partition_key` is the client id: per-client ordering is the scenario's stated
       guarantee, and it is also the whale hot-partition problem. `[BUILD]` `[API]` `[NUM]`

4.10.3 The single non-negotiable property: the insert is in the *same* transaction as the
       `LedgerEntry` rows, so `LedgerMovementPosted` cannot exist without the money movement
       and cannot be lost after it. Prove at-least-once and prove it is *not* at-most-once:
       the publish and the `published_at` update are two operations, so a crash between them
       re-publishes — which is why consumers must be idempotent (§4.9). `[PROVE]` `[BUILD]`

4.10.4 Polling relay: `select ... where published_at is null order by id limit 100 for update
       skip locked` — `SKIP LOCKED` is what lets more than one relay instance run without
       double-publishing, and `order by id` is what preserves ordering within a batch.
       `[BUILD]` `[API]` `[SOURCE]`

4.10.5 The polling-interval arithmetic: `FundsLedger` sustains 230 movements/sec with a
       13,600/sec peak, so a 1-second poll at `limit 100` cannot keep up — state the batch
       size and interval that can, and the lag metric that reveals when it cannot. `[NUM]`
       `[PROVE]`

4.10.6 Polling versus CDC: log-tailing (Debezium on the WAL) removes the poll latency and the
       write amplification, and adds an operational component, a schema-coupled connector and
       a new failure mode. Give the decision procedure and the "do not use this when" case.
       `[DECIDE]` `[X-REF 14]`

4.10.7 Ordering, honestly: ordering holds per partition key, not globally, and only if the
       relay publishes serially per key. Show the failure the scenario already names —
       `RestrictionApplied(SELF_EXCLUDED)` arriving after `PaymentStatusChanged(CREDITED)` —
       and what the partition key buys against it. `[PROVE]` `[INCIDENT]`

4.10.8 Relay idempotence and the dedup store on the consumer side: a `(source, message_id)`
       unique index, sized against 19.8M ledger entries/day. `[BUILD]` `[NUM]`

4.10.9 Edge cases: a payload that fails to serialise (poison message, and the DLQ column);
       `attempts` exceeding a threshold; the relay crashing mid-batch; a message whose
       aggregate has since been corrected by a compensating movement; table growth and the
       partition-detach archival policy. `[BUILD]` `[TRAP]`

4.10.10 Diff vs the real one — against Debezium's outbox event router and the
        `spring-modulith-events` outbox: `OutboxEventRouter` SMT and its expected column
        names, `@Externalized`, `EventPublicationRegistry`,
        `spring.modulith.events.republish-outstanding-events-on-restart`, and Axon's
        `TrackingEventProcessor` token store. `[TABLE]` `[API]`

*(10 leaves)*

## §4.11 An event-sourced aggregate with snapshots

4.11.1 Target API: `sealed interface LedgerEvent`, `final class ClientPositionAggregate` with
       `void apply(LedgerEvent e)`, `List<LedgerEvent> decide(Command c)`, and
       `static ClientPositionAggregate rehydrate(Snapshot s, List<LedgerEvent> tail)`.
       `[BUILD]` `[API]`

4.11.2 The event set, from §11.2 verbatim: `StakeReserved(cash, bonus)`, `StakeWon(payout)`,
       `StakeLost`, `StakeVoided`, `BonusGranted(amount)`, `BonusExpired`,
       `DepositCredited(amount)`, `WithdrawalReserved`, `WithdrawalPaid`,
       `WithdrawalReturned`, `ChargebackReceived`. Each a record; the interface `sealed` so
       the fold is an exhaustive switch. `[BUILD]` `[API]`

4.11.3 The fold is the state: four positions — `CASH_AVAILABLE`, `CASH_RESERVED`,
       `BONUS_AVAILABLE`, `BONUS_RESERVED` — and the three derived views (`Stakeable`,
       `Withdrawable`, `Total`) computed, never stored. Reproduce the §11.6 worked example as
       the test: six movements, states A through E, ending Total 900 / Stakeable 900 /
       Withdrawable 850. `[BUILD]` `[NUM]` `[PROVE]`

4.11.4 The win/void asymmetry is the invariant the event model must encode: `StakeWon` returns
       reserved bonus as **cash**, `StakeVoided` returns it as **bonus**. Two events, same
       reserved amount, different fold — and the test that catches getting it backwards.
       `[PROVE]` `[BUILD]`

4.11.5 Optimistic concurrency on the append: `insert into event_log(aggregate_id, version,
       …) values (?, ?, …)` with a unique index on `(aggregate_id, version)` — the version
       *is* the concurrency control, and a duplicate-key violation is the concurrent-writer
       signal. `[BUILD]` `[PROVE]` `[API]`

4.11.6 Snapshot policy with the numbers: at 2.8M stake reservations/day a heavy client
       accumulates thousands of events, so snapshot every N events (state N and how it was
       chosen) and store `Snapshot(aggregateId, version, positionsJson)`. Show the replay-cost
       arithmetic with and without it against the **150 ms** stake-reservation budget.
       `[NUM]` `[PROVE]` `[DECIDE]`

4.11.7 Snapshots are a *memento* (§1.28) and are derived, never authoritative: deleting every
       snapshot must change performance and nothing else, and the test asserts exactly that.
       `[PROVE]` `[BUILD]`

4.11.8 Schema evolution: an `eventVersion` field, an `Upcaster` chain
       (`v1 StakeReserved` without a bonus leg → `v2` with `bonusPortion = 0`), and the rule
       that upcasters are append-only forever. `[BUILD]` `[API]`

4.11.9 Edge cases: an empty stream (a client with no movements); a snapshot newer than the
       requested version; an event type no longer deployed; the GDPR erasure collision and
       crypto-shredding as the answer; replaying into a *new* projection shape. `[BUILD]`
       `[TRAP]`

4.11.10 Diff vs the real one — against Axon Framework's `EventSourcingRepository` and
        `AggregateSnapshotter`: `@AggregateIdentifier`, `@EventSourcingHandler`,
        `@CommandHandler`, `EventStore.readEvents`, `SnapshotTriggerDefinition`,
        `Snapshotter`, `AggregateNotFoundException`, and the argument that a ledger with 9
        stated invariants may not want a framework at all. `[TABLE]` `[DECIDE]`

*(10 leaves)*

## §4.12 A CQRS projection with a measured lag metric

4.12.1 Target API: `interface Projection { void handle(DomainEvent e); long lastProcessedId();
       }` and `final class OperatorCaseQueueProjection implements Projection` — the read model
       feeding `InternalPlatforms`' operator review queue. `[BUILD]` `[API]`

4.12.2 The read model's shape is dictated by the screen, not the write model: one row per
       `ReviewCase` carrying `applicationId`, `gateInQuestion`, `queuedAt`, `assignedTo`,
       `clientDisplayName`, `waitingMinutes` — a denormalised join across
       `AccountActivation`, `DocumentVerification` and `PersonalDetails` that no query could
       do, because §5.1 forbids cross-schema joins. `[BUILD]` `[API]`

4.12.3 The checkpoint table: `projection_checkpoint(projection_name primary key,
       last_event_id, last_event_at, updated_at)`, updated in the *same* transaction as the
       read-model write — which is what makes the projection restartable and exactly-once
       *in effect*. `[BUILD]` `[PROVE]`

4.12.4 The lag metric, defined three ways because they answer different questions: event-count
       lag (`maxEventId − lastProcessedId`), time lag (`now − lastEventAt`), and
       processing lag (`now − event.occurredAt` at handle time). State which one alerts and
       which one is a red herring when the source is idle. `[NUM]` `[DECIDE]` `[X-REF 20]`

4.12.5 Rebuild: truncate the read model, reset the checkpoint to 0, replay. Prove idempotence
       of every handler by asserting that replaying the same event twice produces the same row
       — an `upsert` keyed on the case id, never an `insert`. `[PROVE]` `[BUILD]`

4.12.6 The read-your-writes mitigation with a number: after an operator saves a decision, the
       queue screen must not still show the case. Either read that operator's own row from the
       write model, or return the event id and have the client poll until
       `lastProcessedId >= id`. State the observed window in milliseconds, not "eventually".
       `[DECIDE]` `[NUM]`

4.12.7 Edge cases: an out-of-order event (the projection must be commutative or version-gated);
       a projection that throws on one event and blocks the whole stream versus one that
       DLQs it and continues; a schema change to the read model mid-stream; 40 operators on
       shift (90 at peak) all reading while the projection writes. `[BUILD]` `[TRAP]`

4.12.8 The projection must not be authoritative: assert in a test that no code path takes a
       decision from this table — the scenario's `BalanceView`/`ProfileService` rule, encoded
       as an ArchUnit rule in §4.15. `[BUILD]` `[TRAP]`

4.12.9 Diff vs the real one — against Axon's `TrackingEventProcessor` plus `TokenStore` and
       Kafka Streams' state stores: segment claims and multi-node token splitting,
       `replay` markers and `@ResetHandler`, `SequencingPolicy`, backpressure, changelog
       topics, and the operational difference between a projection you can rebuild in 20
       minutes and one that takes 8 hours. `[TABLE]` `[API]`

*(9 leaves)*

## §4.13 A specification combinator

4.13.1 Target API: `interface Specification<T> { boolean isSatisfiedBy(T candidate); default
       Specification<T> and(Specification<T> other); default Specification<T> or(...); default
       Specification<T> not(); }` — the non-GoF specification pattern of §1.29, built.
       `[BUILD]` `[API]`

4.13.2 The concrete specifications are `ClientRestrictions`' real rules:
       `NoBlockingRestriction(Action)`, `WithinDailyDepositLimit(Money)`,
       `InstrumentVerified(Rail)`, `WithinClosedLoopCap(Money)`,
       `NotSelfExcluded`, `NotDormantFrozen`. Each a record implementing the interface.
       `[BUILD]` `[API]`

4.13.3 Composition as data: the withdrawal gate from §9.4 expressed as
       `NotSelfExcluded.and(new NoBlockingRestriction(WITHDRAWAL)).and(new
       InstrumentVerified(rail)).and(new WithinClosedLoopCap(amount))` — one expression that
       reads like the compliance table. `[BUILD]`

4.13.4 Why a boolean is not enough: `isSatisfiedBy` loses *why*, and a refused withdrawal must
       tell the client which gate failed. Ship the second signature —
       `Result evaluate(T candidate)` returning a `sealed interface Result { record
       Satisfied(); record Refused(List<ReasonCode> reasons); }` — and state the cost of
       carrying reasons through `and`/`or`. `[BUILD]` `[DECIDE]` `[API]`

4.13.5 Short-circuit versus collect-all is a product decision, not an optimisation: fail-fast
       gives one reason and the 30 ms budget; collect-all gives the client every blocker in
       one round trip. Name both and the case for each. `[DECIDE]`

4.13.6 The two-worlds problem: an in-memory `Specification` and a database predicate are
       different things, and translating between them is the whole difficulty. Show the
       `toPredicate(Root, CriteriaQuery, CriteriaBuilder)` bridge and state plainly when the
       in-memory form stops being viable (5B-row scans). `[TRAP]` `[X-REF 08]`

4.13.7 Composite is the same shape (§1.17): `AndSpecification` holds a `List<Specification<T>>`
       and is itself a `Specification<T>`. Say so once — the recognition is the point.
       `[SAY]`

4.13.8 Edge cases: the empty conjunction (must be `true`, and why the identity element
       matters); `not(not(x))`; a specification with a side effect (forbidden); ordering when
       one specification is 100× more expensive than another. `[BUILD]` `[TRAP]`

4.13.9 Diff vs the real one — against Spring Data JPA's
       `org.springframework.data.jpa.domain.Specification`: the `toPredicate` signature,
       `Specification.where`, `allOf`/`anyOf` (Spring Data 3.x), `JpaSpecificationExecutor`,
       and the fact that Spring's version is a *query* builder while Evans' is a *predicate
       on an object* — the same name for two different patterns. `[TABLE]` `[API]`
       `[VERSION-TRAP]`

*(9 leaves)*

## §4.14 A hexagonal vertical slice, end to end, with no framework type in the domain module

4.14.1 The slice is `FundsLedger`'s stake reservation: three Gradle/Maven modules —
       `ledger-domain`, `ledger-application`, `ledger-adapters` — and the build file of
       `ledger-domain` declares **zero** dependencies beyond the JDK. That build file is the
       deliverable, not the diagram. `[BUILD]` `[PROVE]`

4.14.2 Domain module contents: `record Money(BigDecimal amount, Currency currency)`,
       `record ClientId(UUID value)`, `record StakeSplit(Money bonusPortion, Money
       cashPortion)`, `final class ClientPositions` with
       `StakeSplit reserve(Money stake)` enforcing
       `bonus = min(BONUS_AVAILABLE, 10% of stake)` and cash-covers-remainder with
       round-down on the bonus leg. `[BUILD]` `[API]` `[NUM]`

4.14.3 Outbound ports, owned by the domain: `interface PositionRepository { ClientPositions
       load(ClientId); void save(ClientPositions); }`, `interface RestrictionPort { Decision
       decide(ClientId, Action); }`, `interface Clock { Instant now(); }`. The DIP test from
       §2.10 applied: deleting `ledger-adapters` leaves `ledger-domain` compiling.
       `[BUILD]` `[PROVE]`

4.14.4 Inbound port and application service: `interface ReserveStakeUseCase { StakeSplit
       reserve(ReserveStakeCommand); }` implemented by
       `StakeReservationService` — which owns the transaction boundary, the idempotency check
       (§4.9) and the event append (§4.10), and contains **no** arithmetic. `[BUILD]` `[API]`

4.14.5 Adapters, one per technology: `StakeController` (REST), `JpaPositionRepository`
       (persistence, with its own `PositionEntity` distinct from `ClientPositions`),
       `HttpRestrictionAdapter`, `SystemClock`. Every framework annotation lives here.
       `[BUILD]`

4.14.6 The mapping code is the price, and the leaf must state it honestly: `PositionEntity ↔
       ClientPositions` is ~40 lines of translation that buys the domain test suite running in
       milliseconds with no Spring context and no database. Give both numbers. `[NUM]`
       `[DECIDE]`

4.14.7 The test pyramid that falls out: `ClientPositionsTest` is plain JUnit asserting the
       §11.6 numbers; `StakeReservationServiceTest` uses in-memory fakes of the three ports;
       one `@SpringBootTest` slice with Testcontainers proves the adapters wire. Name what
       each layer can and cannot catch. `[BUILD]` `[X-REF 16]`

4.14.8 Edge cases and the traps this structure exists to prevent: a `jakarta.persistence`
       import in the domain; a port interface declared in the adapters module; a use case
       returning `PositionEntity` to the controller; `BigDecimal` scale mismatch across the
       boundary; a domain class with a no-arg constructor added "for Hibernate". `[TRAP]`
       `[BUILD]`

4.14.9 The "when not to" case, stated in the section itself: for a CRUD service with no
       invariants — `PendingActions`, say — this structure is three modules and a mapper for
       nothing, and layered is the correct cheaper answer. `[DECIDE]`

4.14.10 Diff vs the real one — against a Spring Modulith application and a conventional
        single-module Boot app: `@ApplicationModule`, `ApplicationModules.verify()`,
        `spring-modulith-docs` C4 generation, named interfaces versus package-private
        internals, and what a build-tool module boundary enforces that a package boundary
        cannot. `[TABLE]` `[API]`

*(10 leaves)*

## §4.15 ArchUnit fitness functions that fail the build

4.15.1 The harness: `@AnalyzeClasses(packages = "quizstakes.ledger", importOptions =
       DoNotIncludeTests.class)` with `@ArchTest static final ArchRule …` fields — and the
       fact that a violated `ArchRule` fails as a JUnit assertion, which is what makes it a
       build gate rather than a document. `[BUILD]` `[API]`

4.15.2 The domain-purity rule, which is the one that matters:
       `noClasses().that().resideInAPackage("..ledger.domain..")
       .should().dependOnClassesThat().resideInAnyPackage("org.springframework..",
       "jakarta.persistence..", "com.fasterxml..")` — §2.10's "which module deletes to
       compile" test, executable. `[BUILD]` `[API]` `[PROVE]`

4.15.3 The layer rule via the Library API: `layeredArchitecture().consideringOnlyDependenciesInLayers()
       .layer("Adapters").definedBy("..adapters..").layer("Application").definedBy("..application..")
       .layer("Domain").definedBy("..domain..").whereLayer("Domain").mayOnlyBeAccessedByLayers("Application",
       "Adapters")` — and `onionArchitecture()` as the alternative preset with
       `domainModels`, `domainServices`, `applicationServices`, `adapter`. `[BUILD]` `[API]`

4.15.4 The cycle rule: `slices().matching("quizstakes.(*)..").should().beFreeOfCycles()` —
       §2.13's ADP as a test, and the failure output that names the cycle's edges rather than
       just asserting one exists. `[BUILD]` `[DIAG]`

4.15.5 Domain-specific rules only this codebase can have: no class outside
       `..ledger.domain..` may construct a `LedgerEntry`; nothing may call
       `BalanceView`'s client from a package that also imports `ReserveStakeUseCase` (the
       "read model is never authoritative" rule from §4.12.8); every
       `@Transactional` method must be `public` (or the proxy silently skips it); no field
       injection anywhere. `[BUILD]` `[TRAP]`

4.15.6 Reading a real failure report line by line: the rule text, the offending class, the
       specific dependency, the source line, and the count — the `[DIAG]` deliverable, because
       an unreadable architecture failure gets `@Disabled` within a week. `[DIAG]`

4.15.7 `FreezingArchRule.freeze(rule)` and the `ViolationStore`: how to introduce a rule to a
       codebase with 300 existing violations without blocking every merge, and the failure
       mode of freezing — a stored violation nobody ever unfreezes. `[BUILD]` `[TRAP]` `[API]`

4.15.8 Performance and where these belong in the pipeline: class import cost over a large
       codebase, the class cache, and the decision of unit-test module versus a separate
       `architecture-test` module run once per pipeline. `[NUM]` `[DECIDE]`

4.15.9 The complementary mechanisms, named so the reader knows ArchUnit is not the only tool:
       package-private visibility (the compiler, free, strongest), JPMS `module-info` with
       `exports`/`requires`, `jdeps --check`, Maven Enforcer's banned dependencies, and
       Modulith's `verify()`. Rank them by what enforces at compile time. `[TABLE]` `[X-REF 16]`

4.15.10 Diff vs the real one — against ArchUnit's own rule library:
        `GeneralCodingRules.NO_CLASSES_SHOULD_USE_FIELD_INJECTION`,
        `NO_CLASSES_SHOULD_ACCESS_STANDARD_STREAMS`,
        `NO_CLASSES_SHOULD_THROW_GENERIC_EXCEPTIONS`,
        `NO_CLASSES_SHOULD_USE_JAVA_UTIL_LOGGING`,
        `DEPRECATED_API_SHOULD_NOT_BE_USED`, `layeredArchitecture()`/`onionArchitecture()`,
        `slices()`, `metrics()` for cumulative component dependency, and `ArchCondition`
        for the rules the library does not have. `[TABLE]` `[API]`

*(10 leaves)*

---

# PART 5 — INTERVIEW & RETENTION

PART 5 owns the exam surface. §5.1 is the question bank with the real probe behind each
question, because answering the literal question and missing the probe is how strong
candidates lose design rounds. §5.2 is the one-line trap sheet — the fastest-reading and
highest-yield part of this bible, and the last thing to read before an interview. §5.3 is the
active-recall layer: whiteboard exercises, refactoring katas, and the schedule that keeps the
atomic-concept checklist warm.

## §5.1 The question bank — every question, tiered, each with the real probe behind it

5.1.1 **[basics]** "What is a design pattern?" *Probe: whether the answer is
      problem-forces-structure-consequences or just "a reusable solution".* `[SAY]`

5.1.2 **[basics]** "How many GoF patterns are there and how are they classified?"
      *Probe: 23, and creational/structural/behavioural × class/object scope — a pure recall
      question used only to calibrate before the real ones.*

5.1.3 **[basics]** "What does a static factory method give you that a constructor cannot?"
      *Probe: four specific mechanisms — a name, a subtype return, a cached instance, failure
      before allocation.*

5.1.4 **[basics]** "Factory method versus abstract factory." *Probe: whether the candidate
      knows one is a subclass hook for one product and the other is an object producing a
      consistent family.*

5.1.5 **[basics]** "Records exist now. Is the builder pattern dead?" *Probe: whether the
      candidate can say the record is the product and the builder is the assembly ergonomics,
      and name the ≥5-fields / optional-fields threshold.* `[SAY]`

5.1.6 **[basics]** "Where does a builder's validation go, and why?" *Probe: `build()`, because
      per-setter validation cannot see cross-field rules.*

5.1.7 **[basics]** "Write a thread-safe singleton." *Probe: whether the first answer is the
      initialization-on-demand holder idiom or a `synchronized getInstance()`.*

5.1.8 **[basics]** "Why does double-checked locking need `volatile`?" *Probe: the
      partially-constructed-object publication, stated as a happens-before argument rather
      than "for visibility".* `[SAY]`

5.1.9 **[basics]** "Why is an enum singleton preferred?" *Probe: serialization and
      reflection, named as the two attacks the other forms lose to.*

5.1.10 **[basics]** "Is singleton an anti-pattern?" *Probe: whether the candidate separates
       singleton-as-lifecycle from singleton-as-global-static-access. A flat yes or no fails
       either way.* `[SAY]`

5.1.11 **[basics]** "What is wrong with `Cloneable`?" *Probe: no `clone` method on the
       interface, constructor bypass, shallow by default — three mechanisms, not "it's
       discouraged".*

5.1.12 **[basics]** "Are records immutable?" *Probe: shallow immutability, and whether the
       candidate volunteers `Map.copyOf` in the compact constructor unprompted.*

5.1.13 **[basics]** "When is object pooling a pessimization?" *Probe: TLAB pointer-bump
       allocation and free young-gen reclamation versus promotion and tracing.*

5.1.14 **[basics]** "Adapter, facade, proxy, decorator — separate them." *Probe: the
       interface-equality question first, then intent. Candidates who lead with intent
       ramble.* `[SAY]`

5.1.15 **[basics]** "Is `@Transactional` a decorator?" *Probe: no — it is a proxy; the client
       did not ask for it and it controls whether the target runs.*

5.1.16 **[basics]** "Name a decorator in the JDK." *Probe: whether the answer is a real type —
       `BufferedInputStream`, `Collections.unmodifiableList`, `Collections.synchronizedMap` —
       or a hand-wave.*

5.1.17 **[basics]** "What is the difference between strategy and template method?"
       *Probe: binding time — runtime composition versus compile-time subclassing.*

5.1.18 **[basics]** "Strategy versus state." *Probe: the single sharpest discriminator — a
       state object decides its own successor; a strategy is chosen from outside.* `[SAY]`

5.1.19 **[basics]** "Why must a template method's skeleton be `final`?" *Probe: without it a
       subclass overrides the sequence and the invariant ordering the pattern exists to
       protect is gone.*

5.1.20 **[basics]** "Give a real chain of responsibility." *Probe: the servlet filter chain,
       and that not calling `doFilter` is the short-circuit.*

5.1.21 **[basics]** "What is the iterator's fail-fast contract?" *Probe: `modCount`, and that
       it is a bug detector rather than a thread-safety guarantee.*

5.1.22 **[basics]** "State the five SOLID principles." *Probe: whether each is stated as a
       mechanism or as its slogan. Slogans score nothing.*

5.1.23 **[intermediate]** "You have a `switch` on payment rail in four places. What do you
       do?" *Probe: whether the candidate reaches for strategy automatically or first asks
       whether the set is closed and owned.*

5.1.24 **[intermediate]** "Does strategy remove the switch?" *Probe: no — it relocates it to
       wiring time, and moves an unknown key from a compile error to a runtime one.* `[SAY]`

5.1.25 **[intermediate]** "When is a `switch` over a sealed interface better than a strategy
       registry?" *Probe: closed set you own, plus the compiler's exhaustiveness check.*

5.1.26 **[intermediate]** "Adapter versus anti-corruption layer." *Probe: the same pattern at
       two scales, and whether the candidate says so.*

5.1.27 **[intermediate]** "Proxy versus decorator — which one may skip the delegate?"
       *Probe: a decorator that skips is a bug; a proxy that skips is doing its job.*

5.1.28 **[intermediate]** "Facade versus adapter." *Probe: an adapter satisfies an existing
       client interface over one target; a facade invents a new interface over several.*

5.1.29 **[intermediate]** "What is composite's transparency-versus-safety trade-off?"
       *Probe: `addChild` on the shared interface forces leaves to throw — an LSP violation
       baked into the pattern, with no free version.*

5.1.30 **[intermediate]** "Why does bridge exist when strategy looks the same?" *Probe: M×N
       class explosion across two independently varying hierarchies, established up front.*

5.1.31 **[intermediate]** "Where is flyweight in the JDK?" *Probe: `Integer.valueOf` −128..127,
       the string pool, `Boolean.valueOf` — and the `==` consequence at 127 versus 128.*

5.1.32 **[intermediate]** "Name the in-process observer failure modes." *Probe: all four —
       latency coupling, failure/rollback coupling, deadlock/CME, listener leak. Three of four
       is a partial.*

5.1.33 **[intermediate]** "Are in-process events a substitute for messaging?" *Probe: no
       durability, no retry, no ordering, no consumer visibility.* `[SAY]`

5.1.34 **[intermediate]** "What is visitor's double dispatch?" *Probe: two virtual calls
       producing dispatch on a pair of types, and the expression-problem trade-off.*

5.1.35 **[intermediate]** "Has Java 21 retired visitor?" *Probe: sealed interface plus
       exhaustive switch gives the same guarantee with compile-time checking — and saying
       "visitor is what you write when the language has no pattern matching" is the senior
       framing.* `[SAY]`

5.1.36 **[intermediate]** "Restate SRP so it is falsifiable." *Probe: one axis of change / one
       set of stakeholders, with coupled releases and merge contention as the cost.*

5.1.37 **[intermediate]** "Does OCP mean never modifying existing code?" *Probe: no — it says
       adding a *known kind* of variation should not require modification.*

5.1.38 **[intermediate]** "Give three LSP violations that compile." *Probe:
       strengthened precondition, weakened postcondition,
       `UnsupportedOperationException` on `List.of`, covariant arrays and
       `ArrayStoreException`.*

5.1.39 **[intermediate]** "What did interface `default` methods soften, and what did they
       break?" *Probe: they soften the interface-owner's OCP problem and they weaken ISP by
       making fat interfaces painless to grow.*

5.1.40 **[intermediate]** "We use interfaces everywhere — do we follow DIP?" *Probe: interface
       ownership. The follow-up is the "which module would you delete to break the other's
       compile" test.* `[SAY]`

5.1.41 **[intermediate]** "Is `a.getB().getC().doThing()` always a Demeter violation?"
       *Probe: no — fluent builders and streams chain on the same conceptual object.*

5.1.42 **[intermediate]** "Explain the fragile base class with a concrete example."
       *Probe: `HashSet.addAll` internally calling `add`, and a counting subclass
       double-counting.*

5.1.43 **[intermediate]** "Is DRY about duplicated code?" *Probe: duplicated *knowledge*; and
       the worst case is deduplicating a type across bounded contexts.*

5.1.44 **[intermediate]** "Why is a wrong abstraction more expensive than duplication?"
       *Probe: duplication is local and deletable; an abstraction is load-bearing and
       referenced.* `[SAY]`

5.1.45 **[intermediate]** "What is the rule of three and why three?" *Probe: two cases do not
       reveal the axis of variation; a seam placed at one case is a guess.*

5.1.46 **[internals]** "What does `invokeinterface` cost compared to `invokevirtual`?"
       *Probe: itable search versus vtable index, and whether the candidate then says the
       inline cache usually erases the difference.*

5.1.47 **[internals]** "What is a megamorphic call site and when does a strategy interface
       become one?" *Probe: monomorphic → bimorphic → megamorphic degradation past the
       receiver-type threshold, and that `ClientRestrictions`' rule engine is the shape that
       gets there.*

5.1.48 **[internals]** "Is a builder's allocation free?" *Probe: escape analysis and scalar
       replacement when it does not escape — and the cases where it does (stored in a field,
       passed to a non-inlined method, the method is too big to inline).*

5.1.49 **[internals]** "What exactly guarantees the holder idiom's thread safety?"
       *Probe: the per-class initialisation lock, JVMS §5.5 / JLS 12.4.2, taken once and never
       again.*

5.1.50 **[internals]** "Walk the reordering that breaks DCL without `volatile`."
       *Probe: allocate / construct / publish, and that the publish can be observed before the
       construct's field writes.* `[SAY]`

5.1.51 **[internals]** "How does the JVM stop reflection creating a second enum instance?"
       *Probe: `Constructor.newInstance` explicitly rejects enum types; and `readResolve` /
       the enum-specific serialization path for deserialization.*

5.1.52 **[internals]** "What class does `Proxy.newProxyInstance` actually create?"
       *Probe: a generated `$Proxy0` implementing the given interfaces, cached per
       loader+interface set, dispatching every method to `InvocationHandler.invoke`.*

5.1.53 **[internals]** "What can CGLIB not intercept, and why?" *Probe: `final` methods,
       `private` methods, `static` methods and fields — because interception is method
       overriding in a generated subclass.*

5.1.54 **[internals]** "Why does `@Cacheable` do nothing when I call the method from the same
       class?" *Probe: the self-invocation bypass, and that it fails silently rather than
       throwing. The follow-up is which fixes are correct and which are smells.* `[SAY]`

5.1.55 **[internals]** "How does Spring decide between a JDK proxy and a CGLIB subclass?"
       *Probe: interface presence, `proxyTargetClass`,
       `spring.aop.proxy-target-class=true`, and that Boot defaults to class-based proxying.*

5.1.56 **[internals]** "What does the compiler generate for a record?" *Probe: `final` class,
       `private final` fields, accessors, `equals`/`hashCode`/`toString`, the canonical
       constructor, and `Record` as the supertype — plus what it does *not* give you.*

5.1.57 **[internals]** "How does an exhaustive `switch` over a sealed interface work at
       bytecode level?" *Probe: `PermittedSubclasses`, the `typeSwitch` bootstrap via
       `invokedynamic`, and `MatchException` when the hierarchy changed after compilation.*

5.1.58 **[internals]** "What is a trusted final and why does it matter for immutability?"
       *Probe: constant folding of `final` fields and the safe-publication guarantee that
       makes immutable objects shareable without synchronisation.*

5.1.59 **[internals]** "How does Resilience4j's circuit breaker count failures?" *Probe: the
       sliding window — count-based ring versus time-based buckets, per-state metrics, and the
       CAS on state transition.*

5.1.60 **[internals]** "How does an event-sourced aggregate prevent two concurrent writers?"
       *Probe: a unique index on `(aggregate_id, version)`, so the append itself is the
       optimistic lock.*

5.1.61 **[internals]** "Show me the SQL `@Version` generates." *Probe: `update … set version =
       ? where id = ? and version = ?`, a zero row count, and
       `OptimisticLockingFailureException`.*

5.1.62 **[internals]** "Why does the outbox insert have to be in the same transaction?"
       *Probe: it is the only way to make "money moved" and "event exists" atomic without a
       distributed transaction — and it buys at-least-once, never exactly-once.*

5.1.63 **[internals]** "What does `for update skip locked` do for an outbox relay?"
       *Probe: lets N relay instances drain disjoint batches without double-publishing.*

5.1.64 **[internals]** "What are `@TransactionalEventListener`'s phases?" *Probe:
       `BEFORE_COMMIT`, `AFTER_COMMIT`, `AFTER_ROLLBACK`, `AFTER_COMPLETION`, and the
       silent no-op when no transaction is active unless `fallbackExecution = true`.*

5.1.65 **[internals]** "How would you measure whether an abstraction costs anything?"
       *Probe: JMH on the indirection with the right benchmark mode, async-profiler on the
       call site, and a number attached to the decision.*

5.1.66 **[architecture-judgement]** "Draw the layers of this service." *Probe: whether the
       dependency arrows are drawn *and* whether the domain ends up depending on
       persistence.*

5.1.67 **[architecture-judgement]** "What does layered architecture actually contain, and what
       does it not?" *Probe: it contains technology change, not feature change — a new field
       still touches all four layers.*

5.1.68 **[architecture-judgement]** "Define port and adapter precisely." *Probe: who owns the
       interface. Everything else about hexagonal follows from that one answer.* `[SAY]`

5.1.69 **[architecture-judgement]** "Hexagonal, clean and onion — are they different?"
       *Probe: same idea, different ring counts and ceremony; and whether the candidate can
       name the extra cost of clean's explicit use-case objects.*

5.1.70 **[architecture-judgement]** "How would you *prove* an architecture is hexagonal
       rather than hexagonal-shaped?" *Probe: no framework dependency in the domain module's
       build file, asserted by a test.* `[SAY]`

5.1.71 **[architecture-judgement]** "Package by layer or by feature, and why?" *Probe: Java's
       access modifiers are package-scoped, so by-feature is the structure the compiler can
       police. Taste-based answers fail.*

5.1.72 **[architecture-judgement]** "Distinguish entity, value object, aggregate, repository,
       domain service and application service." *Probe: seven definitions, and specifically
       that the repository is owned by the domain and returns aggregates.*

5.1.73 **[architecture-judgement]** "What defines an aggregate's boundary?" *Probe: the
       invariants that must hold at the end of every transaction — not data ownership, not a
       UI screen.* `[SAY]`

5.1.74 **[architecture-judgement]** "Why do aggregates reference each other by id?"
       *Probe: it keeps the transaction and the loaded object graph small, and makes
       cross-aggregate consistency an explicit eventual decision.*

5.1.75 **[architecture-judgement]** "One transaction spans three aggregates. What is wrong?"
       *Probe: whether the candidate identifies widened lock scope and obscured consistency
       levels, and proposes an event instead.*

5.1.76 **[architecture-judgement]** "What is a bounded context and how do two of them
       integrate?" *Probe: translation at the boundary, never a shared type. The follow-up is
       the context-relationship patterns by name.*

5.1.77 **[architecture-judgement]** "Does CQRS require event sourcing?" *Probe: no — and the
       inverse also holds. This is the most reliable myth-detector in the DDD question set.*
       `[SAY]`

5.1.78 **[architecture-judgement]** "Does CQRS require two databases or eventual
       consistency?" *Probe: neither. The same database with a different read query is CQRS.*

5.1.79 **[architecture-judgement]** "What is projection lag and how do you handle
       read-your-writes?" *Probe: whether a number is attached, and whether the mitigation is
       named (route that user to the write model, or wait on a version).*

5.1.80 **[architecture-judgement]** "When is event sourcing worth it?" *Probe: history as a
       business asset. If the answer is "it's event-driven", the candidate has conflated a
       persistence strategy with a communication style.*

5.1.81 **[architecture-judgement]** "Name event sourcing's four standing costs." *Probe:
       snapshotting, event versioning and upcasters, erasure versus an immutable log,
       mandatory projections.*

5.1.82 **[architecture-judgement]** "Monolith or microservices?" *Probe: the correct shape is
       arithmetic, not preference — 10 ns versus 0.5–1 ms per hop, multiplied availability,
       saga instead of ACID, N× ops surface — plus the trigger that would change the answer.*
       `[SAY]`

5.1.83 **[architecture-judgement]** "How do you diagnose a distributed monolith?"
       *Probe: shared database as the definitive tell, plus coordinated releases and a service
       whose only job is reading another's data.*

5.1.84 **[architecture-judgement]** "Should we start with microservices to avoid a rewrite?"
       *Probe: whether the candidate says the first boundaries are wrong and fixing one is a
       refactor in a monolith and a migration across services.*

5.1.85 **[architecture-judgement]** "What failure was each resilience pattern invented for?"
       *Probe: whether the answer is indexed by failure or is a list of pattern names.*

5.1.86 **[architecture-judgement]** "Tune a circuit breaker for a dependency with an 11 s p99
       inside a 4 s user budget." *Probe: whether the candidate notices the budget is already
       breached by the dependency and moves the work off the request path.* `[NUM]`

5.1.87 **[architecture-judgement]** "What happens when retry sits inside a circuit breaker?"
       *Probe: load multiplication on a struggling dependency, and that timeout, retry and
       breaker are one policy tuned together.*

5.1.88 **[architecture-judgement]** "How do you make a consumer idempotent?" *Probe: a unique
       index, not check-then-insert; and the stored-response replay.*

5.1.89 **[staff "would you"]** "Would you introduce an abstraction here?" *Probe: the
       rejection answer. "There is one implementation and no roadmap for a second, so the
       indirection has nothing flowing through it" scores higher than any pattern name.*
       `[SAY]`

5.1.90 **[staff "would you"]** "Would you adopt event sourcing for this ledger?" *Probe:
       whether the candidate weighs the existing audit table against the replay and erasure
       cost, and can say no with reasons.* `[SAY]`

5.1.91 **[staff "would you"]** "Would you split this module into a service?" *Probe: whether
       the trigger is named — independent deployability, independent scaling, or a second team
       — rather than "cleaner code".* `[SAY]`

5.1.92 **[staff "would you"]** "Would you let the domain model be anemic here?" *Probe:
       whether the candidate can defend anemic-plus-transaction-script as a deliberate choice
       for a CRUD-shaped domain. Knowing you chose it is the signal.* `[SAY]`

5.1.93 **[staff "would you"]** "Would you enforce this rule with a code review or a test?"
       *Probe: fitness functions over conventions, and the honest cost of a rule the team
       disables.*

5.1.94 **[staff "would you"]** "A team wants to use hexagonal on a 6-endpoint CRUD service.
       What do you say?" *Probe: influence without a veto — naming the mapping cost, offering
       the cheaper structure, and the trigger that would justify upgrading.* `[SAY]`

5.1.95 **[staff "would you"]** "How would you migrate a god service without a freeze?"
       *Probe: branch by abstraction, strangler fig, characterisation tests first, and never
       changing behaviour and structure in one commit.*

5.1.96 **[staff "would you"]** "How do you decide when a pattern has become the problem?"
       *Probe: indirection depth as a measurable — files touched per feature, time to answer
       "where does this happen".*

5.1.97 **[staff "would you"]** "What would you write in the ADR for this decision?"
       *Probe: context, options, decision, consequences — and specifically the consequences
       section, which is where weak ADRs stop.*

5.1.98 **[staff "would you"]** "Tell me about a design decision you got wrong."
       *Probe: whether the candidate owns a *decision* rather than a circumstance, and whether
       the fix was systemic.* `[SAY]` `[X-REF 26]`

5.1.99 **[staff "would you"]** "How would you get a team to stop over-engineering?"
       *Probe: rule of three as a team norm, a review question ("what variation flows through
       this seam?"), and a fitness function rather than an opinion.*

5.1.100 **[staff "would you"]** "Which pattern would you use here?" — the closing question, and
        the four-part answer shape it demands: name the force, name what must stay stable,
        name the pattern and the seam location, name the cost. *Probe: whether the candidate
        has a repeatable structure at all.* `[SAY]`

*(100 leaves)*

## §5.2 The traps and the cold assertions — one line each, the wrong belief and the right one

5.2.1 "Naming the pattern is the answer" → the answer is force → stable thing → seam → cost;
      a bare name reads as recall. `[TRAP]`

5.2.2 "This pattern makes the code more flexible/maintainable" → both are unfalsifiable; name
      the specific future change that becomes a one-file change and the one that gets harder.
      `[TRAP]`

5.2.3 "Patterns add flexibility" → they buy flexibility on one axis by freezing the others;
      strategy makes new algorithms cheap and changing the strategy *interface* expensive.
      `[TRAP]`

5.2.4 "Introduce the seam as soon as you see the possibility" → rule of three; a seam placed
      at one case is a guess and a wrong seam is load-bearing. `[TRAP]`

5.2.5 "More patterns means better design" → indirection must be paid for by a variation that
      exists; unpaid indirection is the over-engineering anti-pattern. `[TRAP]`

5.2.6 "Write an abstract factory for the payout providers" → if the choice is per deployment
      the container already is the factory; a factory earns its place when the choice is per
      request, per tenant or per row. `[TRAP]`

5.2.7 "Records killed the builder" → the record is the immutable product, the builder is the
      assembly ergonomics for ≥5 or optional fields; they compose. `[VERSION-TRAP]`

5.2.8 "Validate in the builder's setters" → per-setter validation runs before the other fields
      exist and cannot check cross-field rules; `build()` is the single gate. `[TRAP]`

5.2.9 "`build()` can hand over its own collection" → then a later `builder.add(...)` mutates
      the already-built object; `build()` must `List.copyOf`. `[TRAP]`

5.2.10 "A builder is reusable after `build()`" → only if it copies everything; otherwise reuse
       aliases the product's state. `[TRAP]`

5.2.11 "`synchronized getInstance()` is the thread-safe singleton" → it pays a lock forever
       for an initialisation that happens once; the holder idiom is lazy and lock-free after
       first use. `[TRAP]`

5.2.12 "DCL without `volatile` is fine on modern JVMs" → it can still publish a reference to a
       partially constructed object; the fix in 2026 is the holder idiom, not more cleverness.
       `[VERSION-TRAP]`

5.2.13 "`volatile` makes the increment atomic" → `volatile` gives visibility and ordering, not
       atomicity; the DCL case needs the ordering, nothing else. `[TRAP]`

5.2.14 "A singleton is a singleton" → a Spring singleton-scoped bean is an injected dependency
       with one instance per container; a `static getInstance()` is a hidden global. `[TRAP]`

5.2.15 "Singleton is an anti-pattern" → the lifecycle is fine and common; the global static
       access is the anti-pattern. `[TRAP]`

5.2.16 "Prototype means `Cloneable`" → `Cloneable` declares no `clone`, bypasses constructors
       and is shallow; a copy constructor or a record `with…` method is the modern form.
       `[TRAP]`

5.2.17 "Records are immutable" → shallowly; a record holding a `List` or a `Date` is mutable
       through the referent until the compact constructor copies it. `[TRAP]`

5.2.18 "Pooling objects is an optimisation" → for plain heap objects it is a pessimization —
       TLAB allocation is a pointer bump, dead young objects cost nothing, and pooling adds
       synchronisation plus old-gen tracing. `[VERSION-TRAP]`

5.2.19 "A bigger pool is a faster pool" → a pool larger than the downstream's capacity moves
       the failure to the downstream and hides it; pool size is a bottleneck decision.
       `[TRAP]`

5.2.20 "A pooled object can be returned as-is" → any mutable pooled state must be reset on
       release, or the next borrower inherits the previous request's data. `[TRAP]`

5.2.21 "Adapter, facade, proxy and decorator differ by structure" → they are structurally
       near-identical; the discriminator is interface equality first, then intent. `[TRAP]`

5.2.22 "Decorator and proxy are the same thing academically" → a decorator that skips its
       delegate is a bug; a proxy that skips its target is doing its job. `[TRAP]`

5.2.23 "`@Transactional` is a decorator" → it is a proxy: the call site did not ask for it,
       stacking two is meaningless, and it controls whether the target runs. `[TRAP]`

5.2.24 "An adapter and a facade are interchangeable" → an adapter satisfies an *existing*
       client interface over one target; a facade *invents* an interface over several.
       `[TRAP]`

5.2.25 "Spring needs an interface to proxy a bean" → CGLIB/ByteBuddy subclass proxying needs
       no interface, and Spring Boot defaults to class-based proxies. `[VERSION-TRAP]`

5.2.26 "`final` classes are safe and therefore faster" → they simply fail to be proxied, often
       degrading a feature silently rather than throwing. `[TRAP]`

5.2.27 "CGLIB can intercept anything a subclass can see" → not `final`, `private` or `static`
       methods, and never field access. `[TRAP]`

5.2.28 "My `@Transactional`/`@Cacheable`/`@Async` annotation is on the method, so it runs" →
       not when the call came from `this` inside the same bean; the proxy is bypassed and
       nothing errors. `[TRAP]`

5.2.29 "`AopContext.currentProxy()` fixes self-invocation" → it works and it is a smell; moving
       the method to another bean is the correct fix, and AspectJ weaving avoids the problem
       entirely. `[TRAP]`

5.2.30 "The transparent composite is the good one" → putting `addChild` on the shared
       interface forces leaves to throw `UnsupportedOperationException`; there is no free
       version, only a named trade-off. `[TRAP]`

5.2.31 "Bridge is just strategy" → bridge is a deliberate two-hierarchy split established up
       front to avoid an M×N explosion; strategy swaps one algorithm inside a fixed class.
       `[TRAP]`

5.2.32 "Flyweight makes things faster" → it trades allocation for a hash lookup and worse
       locality; it wins in the millions of objects and loses below that. `[TRAP]`

5.2.33 "`Integer` caching is an implementation detail I can ignore" → `a == b` is `true` at 127
       and `false` at 128, and that is a real production bug class. `[TRAP]`

5.2.34 "`new String("x")` is pooled" → only compile-time constants are; `new` always allocates,
       and `intern()` is the explicit opt-in. `[TRAP]`

5.2.35 "Strategy removes the switch" → it relocates it to wiring time; the map lookup *is* the
       switch, and an unknown key moves from a compile error to a runtime one. `[TRAP]`

5.2.36 "Inject `Map<String, Strategy>` and let Spring key it by bean name" → bean names are
       refactoring-fragile and are not domain values; key by an explicit `key()` method.
       `[TRAP]`

5.2.37 "A registry is always better than a `switch`" → for a closed set you own, a sealed
       interface with an exhaustive switch gives compile-time safety a registry cannot.
       `[TRAP]`

5.2.38 "Template method and strategy are interchangeable" → template method binds at compile
       time via inheritance and inherits base internals; strategy binds at runtime through an
       interface. `[TRAP]`

5.2.39 "The skeleton method does not need to be `final`" → without `final`, a subclass
       overrides the sequence and the ordering invariant the pattern exists for is gone.
       `[TRAP]`

5.2.40 "Booleans are fine for a lifecycle" → four booleans is 16 representable combinations of
       which most are illegal; one status enum plus a transition table makes illegal states
       unrepresentable. `[TRAP]`

5.2.41 "Enforce the transition in the service" → then a second service, a batch job or a
       data-fix script bypasses it; the guard belongs inside the aggregate. `[TRAP]`

5.2.42 "A rejected transition can be a silent no-op" → it must be a named exception carrying
       from-state, event and the events that *were* legal, because that message is what an
       operator reads during an incident. `[TRAP]`

5.2.43 "In-process events decouple the publisher" → synchronous listeners on the publisher's
       thread inside its transaction couple latency and failure both ways. `[TRAP]`

5.2.44 "A listener failure is contained" → with Spring's default synchronous publisher a
       throwing listener rolls back the publisher's transaction: "the email failed, so the
       order was not placed". `[TRAP]`

5.2.45 "Registering a listener is free" → it is a strong reference from a long-lived subject to
       a short-lived observer; never-deregistered listeners are a textbook heap leak. `[TRAP]`

5.2.46 "Modifying the listener list during dispatch is fine" → it throws
       `ConcurrentModificationException`; dispatch must iterate a snapshot. `[TRAP]`

5.2.47 "In-process events are a delivery mechanism" → they are lost on crash, have no retry, no
       ordering guarantee and no consumer visibility; after-commit plus async plus the outbox
       is the production shape. `[TRAP]`

5.2.48 "`@TransactionalEventListener` always fires" → with no active transaction it silently
       does nothing unless `fallbackExecution = true`. `[TRAP]`

5.2.49 "Command is about undo" → it is about reifying an invocation so it can be queued,
       logged, authorised, replayed or reversed; undo is one consequence of many. `[TRAP]`

5.2.50 "Chain of responsibility is a decorator chain" → a decorator always delegates; a chain
       handler may refuse to delegate, and termination is the point. `[TRAP]`

5.2.51 "Filter order is a configuration detail" → in a security filter chain, order is a
       security property. `[TRAP]`

5.2.52 "Visitor is the way to add operations over a type hierarchy" → in Java 21 a sealed
       interface with an exhaustive switch gives the same guarantee without accept/visit, and
       adding a type breaks compilation where it matters. `[VERSION-TRAP]`

5.2.53 "Visitor is strictly better than an interface method" → visitor makes adding
       *operations* cheap and adding *types* expensive; a plain interface method does the
       reverse. `[TRAP]`

5.2.54 "The fail-fast iterator makes collections thread-safe" → `modCount` is a best-effort bug
       detector, not a guarantee. `[TRAP]`

5.2.55 "A mediator reduces coupling, full stop" → it trades N² edges for one node that
       accumulates all the interaction logic and tends toward a god object. `[TRAP]`

5.2.56 "Write your own interpreter for business rules" → you now own a language, its errors, its
       tooling and its versioning; an existing engine is usually the answer. `[TRAP]`

5.2.57 "SRP means a class does one thing" → unfalsifiable; it means one axis of change and one
       set of stakeholders, and the cost is coupled releases. `[TRAP]`

5.2.58 "SRP means one class per object/one method per class" → SRP says nothing about object
       creation or method count. `[TRAP]`

5.2.59 "OCP means never modifying existing code" → you modify code constantly; OCP says a
       *known kind* of variation should not require it. `[TRAP]`

5.2.60 "OCP can be retrofitted anywhere" → only where the variation axis was predicted
       correctly; the polymorphic boundary has to already be in the right place. `[TRAP]`

5.2.61 "It compiles, so LSP holds" → strengthened preconditions, weakened postconditions, new
       unchecked exceptions and `UnsupportedOperationException` all compile fine. `[TRAP]`

5.2.62 "`List.of(...)` is a `List`" → every mutating method throws, which is the JDK's own LSP
       violation; `Arrays.asList` is worse — `set` works and `add` throws. `[TRAP]`

5.2.63 "Java arrays are safely covariant" → `Object[] a = new String[1]; a[0] = 42;` compiles
       and throws `ArrayStoreException`, which is why generics are invariant. `[TRAP]`

5.2.64 "LSP violations are a purity concern" → they surface as `instanceof` checks in callers,
       and once callers type-test the polymorphism is gone and the abstraction is fake.
       `[TRAP]`

5.2.65 "A wide interface is harmless if implementors use `default`" → `default` methods soften
       the interface owner's problem and make fat interfaces painless to grow; the stub is
       still a lie a caller can invoke. `[TRAP]`

5.2.66 "An interface per class satisfies DIP" → interfaces owned by the implementation side
       invert nothing; the test is which module you would delete to break the other's compile.
       `[TRAP]`

5.2.67 "DIP means using interfaces" → it means the high-level module *owns* the abstraction, so
       the compile-time arrow points inward while control flows outward. `[TRAP]`

5.2.68 "Every chained call is a Demeter violation" → fluent builders and streams chain on the
       same conceptual object and are not train wrecks. `[TRAP]`

5.2.69 "Inheritance is code reuse" → it is the strongest coupling in the language: the subclass
       depends on which of the base's own public methods it calls internally. `[TRAP]`

5.2.70 "Overriding both `add` and `addAll` is safe" → `HashSet.addAll` routes through `add`, so
       a counting subclass double-counts; the self-call policy was never in the contract.
       `[TRAP]`

5.2.71 "DRY means no duplicated characters" → it means no duplicated *knowledge*; two rules that
       currently agree must stay separate. `[TRAP]`

5.2.72 "Sharing a `Customer` class between teams is DRY" → deduplicating a type across bounded
       contexts binds two release cycles forever, and the shared class satisfies neither set of
       invariants. `[TRAP]`

5.2.73 "Duplication is the expensive option" → duplication is local and deletable; a wrong
       abstraction is load-bearing and referenced. `[TRAP]`

5.2.74 "A god service is a code-quality problem" → it is a *delivery* problem: every team edits
       one file, the unit needs 40 mocks, and nobody can hold it in their head. `[TRAP]`

5.2.75 "Entities are persistence; logic belongs in services" → the most common senior false
       confidence; anemic-plus-transaction-script is defensible for CRUD-shaped domains and
       wrong where real invariants exist — the failure is not knowing you chose it. `[TRAP]`

5.2.76 "Circular dependencies are a warning, not an error" → the cycle is the real module and it
       is bigger than either package; neither side can be compiled, tested or deployed alone.
       `[TRAP]`

5.2.77 "Field injection is a style choice" → it hides constructor cycles that constructor
       injection would fail on, and Boot 2.6+ disallows circular references by default.
       `[VERSION-TRAP]`

5.2.78 "`String customerId, String orderId` is fine" → the compiler cannot distinguish them, so
       transposition is a runtime bug and validation has no home; a value-object record makes it
       a compile error. `[TRAP]`

5.2.79 "A clean interface means a good abstraction" → not if the failure modes and performance
       leak: `LazyInitializationException` from a repository, staleness from a "transparent"
       cache. `[TRAP]`

5.2.80 "Undocumented behaviour is not part of the contract" → Hyrum's law: with enough
       consumers every observable behaviour is part of the contract. `[TRAP]`

5.2.81 "Layered architecture contains change" → it contains *technology* change; a new field
       still touches all four layers, which is what produces shotgun surgery. `[TRAP]`

5.2.82 "We have a hexagon on the whiteboard, so we are hexagonal" → not if the domain imports
       `jakarta.persistence`, the port interface lives in infrastructure, or a use case returns
       a JPA entity; the mechanical test is the domain module's build file. `[TRAP]`

5.2.83 "Hexagonal means three modules" → it means the dependency direction; the module count is
       an enforcement choice, and the hexagon holds application logic as well as domain.
       `[TRAP]`

5.2.84 "There must be six ports" → the hexagon's six sides mean nothing; a pentagon would do.
       `[TRAP]`

5.2.85 "Domain-to-entity mapping is pure overhead" → it is the price of the isolation, and for a
       CRUD service with no invariants layered is the correct cheaper answer. `[TRAP]`

5.2.86 "Package-by-feature is a matter of taste" → Java's access modifiers are package-scoped,
       so by-feature is the only structure the compiler can police. `[TRAP]`

5.2.87 "The aggregate boundary follows the data or the screen" → it follows the invariants that
       must hold at the end of every transaction; large aggregates mean large transactions and
       write contention on one row. `[TRAP]`

5.2.88 "Aggregates can hold object references to each other" → they reference by id, or the
       transaction and the object graph grow without bound. `[TRAP]`

5.2.89 "Two bounded contexts should share a `Customer` type" → they integrate by translation —
       an anti-corruption layer, which is Adapter at module scale. `[TRAP]`

5.2.90 "CQRS needs event sourcing" → it needs neither event sourcing, nor two databases, nor
       eventual consistency; separating the read path is the whole pattern. `[VERSION-TRAP]`

5.2.91 "Event sourcing follows from being event-driven" → event-driven communication and event
       sourcing are unrelated decisions; adopting the latter without an audit requirement buys
       operational cost for nothing. `[TRAP]`

5.2.92 "The event log is queryable" → it is not, so projections are mandatory, so CQRS is not
       optional once you event-source. `[TRAP]`

5.2.93 "Event sourcing gives you deletion for free" → you cannot delete; erasure requirements
       collide with the log, and crypto-shredding is the usual answer. `[TRAP]`

5.2.94 "Snapshots are the state" → snapshots are derived; deleting every snapshot must change
       performance and nothing else. `[TRAP]`

5.2.95 "Microservices are the default in 2026" → the reason to split is independent
       deployability and independent scaling, usually driven by team autonomy — never "cleaner
       code", which a modular monolith gives for free. `[VERSION-TRAP]`

5.2.96 "Start with microservices to avoid a rewrite later" → the first boundaries are wrong, and
       fixing a boundary is a refactor in a monolith and a migration across services. `[TRAP]`

5.2.97 "We split the services, so we are decoupled" → services split by layer or table produce a
       distributed monolith; a shared database is the definitive tell. `[TRAP]`

5.2.98 "An in-process call and an RPC are comparable" → ~10 ns versus ~0.5–1 ms is five orders of
       magnitude, and serial availability multiplies: six 99.99% services give 99.94%. `[TRAP]`
       `[NUM]`

5.2.99 "An unbounded queue smooths bursts" → it converts backpressure into an OOM, and a
       `ThreadPoolExecutor` with an unbounded `LinkedBlockingQueue` never grows past its core
       size. `[TRAP]`

5.2.100 "A circuit breaker fixes the outage" → without a defined open-state response it only
        converts a slow failure into a fast one; decide what open *returns*. `[TRAP]`

5.2.101 "Retry is a safe default" → not for non-idempotent operations and not for a 400; a
        timed-out card capture retried without the original idempotency key double-charges.
        `[TRAP]`

5.2.102 "Exponential backoff is enough" → without jitter the retries stay synchronised and
        arrive as a wave; full jitter is what de-correlates them. `[TRAP]`

5.2.103 "Set a generous inner timeout to be safe" → an inner timeout longer than the outer one
        is dead code; the budget must shrink down the call chain. `[TRAP]`

5.2.104 "Check whether the idempotency key exists, then insert" → that is a race; the unique
        index is the mechanism and the cache is only the fast path. `[TRAP]`

5.2.105 "Resilience patterns can be chosen independently" → timeout, retry and circuit breaker
        are one policy tuned together, and the breaker must see bounded retried attempts.
        `[TRAP]`

5.2.106 "The most sophisticated answer is the strongest answer" → "hexagonal + CQRS + event
        sourcing + microservices" on a CRUD problem reads as inability to size a solution.
        `[TRAP]`

5.2.107 "Refactoring and behaviour change can share a commit" → then a bisect cannot tell you
        which broke; and characterisation tests must be written before touching unknown legacy
        behaviour. `[TRAP]`

*(107 leaves)*

## §5.3 The drills: whiteboard exercises, refactoring katas, the retention schedule

5.3.1 **Whiteboard — the hexagon.** Draw `FundsLedger` as ports and adapters from memory, then
      name what crosses each boundary and in which direction: `ReserveStakeCommand` inward,
      `StakeSplit` outward, `PositionRepository` and `RestrictionPort` as domain-owned
      outbound ports. Score yourself on whether any arrow points outward from the domain.

5.3.2 **Whiteboard — cut the god service.** Given a 3,000-line `PaymentService` with 40
      dependencies, produce the seam list in ten minutes: group methods by which data they
      read, name the two aggregates that fall out, and name the one method that belongs
      nowhere and needs a domain service.

5.3.3 **Whiteboard — the aggregate boundary.** For `Movement` and `LedgerEntry`, argue the
      boundary from invariant 1 ("entries sum to zero") alone, then argue why `Position` is a
      *separate* aggregate despite being touched by the same transaction.

5.3.4 **Whiteboard — the four-panel.** Draw layered, hexagonal, clean and onion side by side and
      label the centre of each; then state, in one sentence per panel, the testing consequence.

5.3.5 **Whiteboard — the CQRS flow.** Draw the write path, the event, the projection and the
      read path for `InternalPlatforms`' operator queue, then annotate where the lag is measured
      and what read-your-writes mitigation you would add.

5.3.6 **Whiteboard — the resilience stack.** Draw the decorator order around
      `CardPspPort.authorise` (timeout inside retry inside breaker inside bulkhead) and defend
      the order against a colleague proposing the reverse.

5.3.7 **Whiteboard — the outbox.** Draw the transaction boundary, the outbox row, the relay and
      the consumer's dedup index, and mark the exact point where at-least-once becomes visible.

5.3.8 **Whiteboard — the state machine.** Reproduce the `AA-6xx`/`AA-7xx` document machine from
      memory including the three-attempt and 14-day guards, then name the two states an operator
      can be blocked in.

5.3.9 **Refactoring kata — the 400-line `switch`.** Take a `settle(Stake, Outcome)` method
      switching on a status string in five places. Move: extract each branch behind an
      interface, keep the switch as a keyed lookup. Protecting test: a parameterised test over
      every key asserting old and new produce identical output.

5.3.10 **Refactoring kata — the boolean-flag entity.** `boolean reserved, settled, voided,
       orphaned` on `Reservation`. Move: add the enum, derive it from the booleans, migrate
       readers, then drop the booleans. Protecting test: a golden-master over all 16 flag
       combinations taken *before* the change.

5.3.11 **Refactoring kata — the anemic aggregate.** `ClientPositions` with public setters and
       the reserve arithmetic in a service. Move: make one setter private and add
       `reserve(Money)` with its invariant. Protecting test: the illegal transition now throws.

5.3.12 **Refactoring kata — the leaky repository.** A `WagerRepository` returning JPA entities
       that throw `LazyInitializationException` outside the session. Move: return a domain
       aggregate assembled inside the transaction. Protecting test: a test that consumes the
       result with the session closed.

5.3.13 **Refactoring kata — the train wreck.** `intent.getAccount().getPositions().getCash()`
       across eleven call sites. Move: add the delegating method on the owner, inline at one
       call site, repeat. Protecting test: the existing behaviour test at the outer boundary.

5.3.14 **Refactoring kata — the duplicated wrapper.** Retry-plus-logging-plus-metrics
       hand-written at every PSP call site. Move: extract a decorator and wire it once.
       Protecting test: the decorator in isolation with a mock delegate, asserting delegate
       call counts.

5.3.15 **Refactoring kata — the 9-parameter constructor.** Move: introduce a builder, keep the
       old constructor delegating and deprecated. Protecting test: existing tests unchanged.

5.3.16 **Established katas worth running once each, by name:** Gilded Rose (conditional
       sprawl), Tennis (state and naming), Trip Service (dependency-breaking and seams),
       Theatrical Players (Fowler's own refactoring worked example), Ugly Trivia
       (characterisation testing), Parallel Change (branch by abstraction), Tell-Don't-Ask
       (Demeter). `[RESEARCH]`

5.3.17 **Drill — name the pattern in this JDK class.** Timed, 20 items, one line each:
       `InputStreamReader`, `BufferedInputStream`, `Collections.unmodifiableList`,
       `Collections.synchronizedMap`, `Arrays.asList`, `Integer.valueOf`,
       `Proxy.newProxyInstance`, `Iterator`, `Comparator`, `Runnable`, `Callable`,
       `ThreadPoolExecutor.RejectedExecutionHandler`, `Executors`, `Stream.collect`/
       `Collector`, `AbstractList`, `Calendar.getInstance`, `StringBuilder`, `Cloneable`,
       `ServiceLoader`, `Filter`/`FilterChain`.

5.3.18 **Drill — name the pattern in this Spring class.** `BeanFactory`, `FactoryBean`,
       `BeanPostProcessor`, `JdbcTemplate`, `RestTemplate`/`RestClient`,
       `ApplicationEventPublisher`, `HandlerInterceptor`, `TransactionTemplate`,
       `AbstractPlatformTransactionManager`, `Environment`/`PropertySource`,
       `ConversionService`, `@Conditional`, `ProxyFactoryBean`, `SimpleApplicationEventMulticaster`,
       `FilterChainProxy`.

5.3.19 **Drill — reject a pattern out loud.** Five prompts (a factory for one implementation,
       event sourcing on a CRUD table, microservices for a 4-endpoint service, an interface per
       class, CQRS for a 200-row admin screen), 30 seconds each, spoken. The output is the
       rejection sentence, and the sentence is the artefact. `[SAY]`

5.3.20 **Drill — the four-part answer.** Ten "which pattern would you use" prompts drawn from
       the QuizStakes domain, answered aloud in the fixed shape: force / stable thing / pattern
       and seam / cost. Time-boxed to 90 seconds each. `[SAY]`

5.3.21 **Drill — spot the bug.** Six code snippets shown for 60 seconds each: DCL missing
       `volatile`; a builder validating in setters; a `@Transactional` method called via `this`;
       a composite with `addChild` on the leaf interface; check-then-insert on an idempotency
       key; a listener registered and never removed.

5.3.22 **Drill — the disambiguation pairs, timed.** Adapter/facade, proxy/decorator,
       strategy/state, strategy/template, decorator/chain, bridge/strategy, mediator/facade,
       composite/decorator, CQRS/event sourcing, saga/2PC — one discriminating question each,
       15 seconds each.

5.3.23 **Drill — the arithmetic, from memory.** 10 ns in-process call, 0.5–1 ms same-AZ RPC,
       six 99.99% services in series → 99.94%, `Integer` cache −128..127, the 30 ms restriction
       budget, the 11 s PSP p99, 230/sec sustained and 13,600/sec peak ledger writes. `[NUM]`

5.3.24 **Retention schedule, mapped to the atomic-concept checklist.** Day 1 read the tier;
       day 2 re-derive the checklist items for it from memory; day 4, day 8, day 15 and day 30
       re-quiz only the items missed; the whole checklist once a week thereafter. The unit of
       repetition is a checklist assertion, not a section.

5.3.25 **Pre-interview 40-minute sequence.** §5.2 in full (it is one line per item by design),
       then the atomic concept checklist, then five §5.1 questions answered aloud in the
       four-part shape, then the reject-a-pattern drill. Never re-read PART 3 the night before —
       internals do not decay in a day and re-reading them displaces the phrasing practice that
       does. `[SAY]`

*(25 leaves)*

## Diagram manifest

| id | leaf ref | type | must show |
|---|---|---|---|
| D-01 | §1.4 | svg | The pattern-family map: creational / structural / behavioural bands, class vs object scope, all 23 GoF patterns placed, with the four Java-21-reshaped ones marked |
| D-02 | §1.13–§1.16, §2.3 | table | Adapter / facade / proxy / decorator: interface-vs-target, purpose, stackable, typical trigger, and the one discriminating question per row |
| D-03 | §1.16 | svg | The decorator stack: `RetryingPayoutClient(MeteredPayoutClient(TimedPayoutClient(RealPsp)))` with the call descending and the response ascending, each layer's added behaviour labelled |
| D-04 | §1.10, §3.3, §3.4 | svg | The DCL and holder init sequence: two threads, the allocate/construct/publish split, the reordering window without `volatile`, and the class-initialisation lock taken once in the holder variant |
| D-05 | §3.7, §3.8 | svg | JDK-proxy vs CGLIB call path side by side: caller → `$Proxy0` → `InvocationHandler` → target, against caller → generated subclass → `MethodProxy.invokeSuper` → super method |
| D-06 | §3.8, §4.2 | svg | The interceptor chain with the self-invocation bypass: external call traversing all interceptors, internal `this.method()` arriving at the target directly with the chain greyed out |
| D-07 | §1.26, §3.13 | svg | Double dispatch vs sealed switch: `accept`/`visit` two-hop dispatch on the left, `typeSwitch` bootstrap with the compiler's exhaustiveness check on the right |
| D-08 | §1.22, §4.4 | svg | The `DocumentVerification` state machine: `AA-600` → `AA-610` → {`AA-611`, `AA-650`, `AA-690`} → `AA-699` → `AA-700` → `AA-710` → {`AA-711`, `AA-799`}, with the 3-attempt and 14-day guards on the re-upload edge |
| D-09 | §1.23, §3.19, §4.5 | svg | The four observer failure modes on one publisher: latency accumulation, a throwing listener rolling back the publisher's transaction, reentrant registration causing CME, and a retained listener reference |
| D-10 | §2.17, §7.2 | svg | Four-panel layered / hexagonal / clean / onion, each with its centre labelled and every dependency arrow drawn, plus a "what a domain test needs" caption per panel |
| D-11 | §2.19 | svg | Package-by-layer vs package-by-feature: the same six classes arranged both ways, with `public` forced in the first and package-private possible in the second |
| D-12 | §2.22 | svg | The aggregate boundary: `Movement` root enclosing its 2–4 `LedgerEntry` rows inside one transaction, `Position` outside it referenced by id, and the invariant that defines the line |
| D-13 | §2.23, §4.12 | svg | The CQRS write / event / projection / read flow for `InternalPlatforms`' operator queue, with the checkpoint table and the lag measurement point marked |
| D-14 | §2.24, §3.16, §4.11 | svg | Event sourcing with snapshots: the append-only log, the unique `(aggregate_id, version)` index, a snapshot at version N, and the tail replay from N to head |
| D-15 | §2.25, §3.17, §4.10 | svg | The outbox and its relay: one transaction spanning the ledger rows and the outbox row, then the poller with `skip locked`, the broker, and the consumer's dedup index |
| D-16 | §2.25 | svg | Saga, both flavours: orchestrated (a coordinator issuing steps and compensations) against choreographed (services reacting to each other's events), same `DEP-301 → DEP-400` failure in both |
| D-17 | §2.26, §3.15, §4.6 | svg | The circuit-breaker state machine with its windows: CLOSED / OPEN / HALF_OPEN, the count-based ring and time-based buckets, the failure-rate and slow-call thresholds, and the half-open probe budget |
| D-18 | §2.26, §4.8 | svg | The bulkhead: three semaphore compartments (identity vendor, watchlist, PSP) drawing from one 8 GB instance, one compartment saturated and the others unaffected |
| D-19 | §2.25 | svg | The strangler fig: the facade in front, traffic percentage shifting from the legacy path to the new one over four stages, with the seam where behaviour is compared |
| D-20 | §3.1 | svg | Inline-cache degradation: monomorphic → bimorphic → megamorphic for a strategy interface, with the receiver-type count on the x-axis and the dispatch mechanism at each stage |
| D-21 | §2.13 | svg | The component-principle tension triangle: REP / CCP / CRP at the vertices, with what you give up as you move toward each |
| D-22 | §2.13 | svg | Connascence: the nine kinds ordered by strength on one axis and locality on the other, with a QuizStakes example plotted at three points |
| D-23 | §2.2 | svg | The creational decision procedure as a flowchart: how many products, is the choice per deployment or per request, is the object immutable, how many optional fields |
| D-24 | §2.4 | table | Behavioural disambiguation: strategy / state / template / command / visitor by binding time, who chooses, self-transitioning, and the one question that separates each pair |
| D-25 | §2.18 | table | Architecture styles against quality attributes: deployability, testability, performance, scalability, simplicity, evolvability — one row per style, ratings plus the deciding constraint |
| D-26 | §1.33 | table | The 23-pattern census: pattern, GoF classification, JDK instance by type name, Spring instance by type name, QuizStakes instance |
| D-27 | §2.15 | table | Smell → smallest safe move → the test that protects it, one row per Fowler 2e smell |
| D-28 | §2.26, §4.7 | svg | Retry attempt distribution: 500 clients under plain exponential backoff (three sharp spikes) against full jitter (flat), same axes, same attempt count |
| D-29 | §4.1 | svg | The DI container's resolution walk for `StakeReservationService`, with the creation stack shown at each depth and the cycle-detection check firing on the third frame |
| D-30 | §4.14 | svg | The hexagonal vertical slice as a module dependency graph: `ledger-domain` with zero outbound edges, `ledger-application` → domain, `ledger-adapters` → both, and the deleted-module test annotated |
| D-31 | §2.26 | table | Resilience pattern → the failure it was invented for → mechanism → key parameter → the trap, one row per pattern |
| D-32 | §2.30 | table | The cost model: pattern → allocation cost → indirection depth → extra types → where errors move to → testability effect |

*(32 manifest entries)*

---

### Sources consulted — lane F

| Source (URL) | What it contributed |
|---|---|
| https://github.com/Devinterview-io/software-architecture-interview-questions | Fetched the full README question list (15 titles visible of a stated 85). Contributed the coupling/cohesion, Law-of-Demeter-as-architecture, cross-cutting-concerns, publish-subscribe and quality-attribute question shapes to §5.1; confirmed the monolith-vs-microservices and SOLID questions are standard openers rather than staff-level probes |
| https://www.kore1.com/system-design-interview-questions/ | Confirmed the 2026 senior/staff interview surface is trade-off articulation over solution recall, and that payment-processing with idempotency and saga is a standard prompt — shaped §5.1's probe wording and §5.1.82/5.1.86 |
| https://mentorcruise.com/questions/solutions-architect/ , https://www.curotec.com/interview-questions/125-software-architect-interview-questions/ | Curriculum/completeness probe for architecture question lists; contributed the ADR question (§5.1.97) and the "enforce by review or by test" question (§5.1.93) |
| https://www.geeksforgeeks.org/system-design/difference-between-the-facade-proxy-adapter-and-decorator-design-patterns/ , https://javarevisited.blogspot.com/2015/01/adapter-vs-decorator-vs-facade-vs-proxy-pattern-java.html | Confirmed the four-way structural disambiguation is asked as one question rather than four, and that "same structure, different intent" is the expected framing — §5.1.14, D-02, §5.2.21 |
| https://www.secondtalent.com/interview-guide/ddd/ , https://devinterview.io/blog/domain-driven-design-interview-questions/ , https://www.fullstack.cafe/blog/domain-driven-design-interview-questions | DDD interview surface: aggregate-as-transaction-boundary, "only aggregates are publicly accessible", repositories return aggregates only, and the transaction-spanning-aggregates code-review question — §5.1.72–5.1.76 |
| https://www.kurrent.io/blog/cqrs-dispelling-the-myths/ , https://lostechies.com/jimmybogard/2012/08/22/busting-some-cqrs-myths/ , https://codeopinion.com/greg-young-answers-your-event-sourcing-questions/ | The CQRS myth set, primary-adjacent: CQRS needs neither event sourcing, nor separate databases, nor eventual consistency; and ES does not imply CQRS. Added §5.2.90 and §5.1.77–5.1.78 as distinct questions |
| https://medium.com/@gara.mohamed/hexagonal-architectures-common-misconceptions-9aa2380c13c0 , https://jmgarridopaz.github.io/content/hexagonalarchitecture.html , https://alistair.cockburn.us/hexagonal-architecture | Hexagonal misconceptions I had not listed: the hexagon holds application *and* domain logic (not domain alone), six sides mean nothing, it is not a folder structure, application logic must not be duplicated across two adapters of one port — §5.2.83, §5.2.84, §5.1.68–5.1.70 |
| https://deepwiki.com/resilience4j/resilience4j/2-circuit-breaker , https://resilience4j.readme.io/docs/circuitbreaker , https://medium.com/@storozhuk.b.m/circuit-breaker-implementation-in-resilience4j-992af908c413 | `CircuitBreakerStateMachine` as the class name, the six states (CLOSED/OPEN/HALF_OPEN plus METRICS_ONLY/DISABLED/FORCED_OPEN), `RingBitSet` and the circular-array count-based window vs time-based buckets, per-state independent metrics storage — §4.6.10, D-17 |
| https://deepwiki.com/TNG/ArchUnit/2.3-library-api , https://www.baeldung.com/java-archunit-intro , https://www.codecentric.de/en/knowledge-hub/blog/archunit-in-practice-keep-your-architecture-clean , https://www.infoq.com/articles/fitness-functions-architecture/ | ArchUnit Library API surface: `layeredArchitecture()`, `onionArchitecture()`, `slices()`, `FreezingArchRule`/`ViolationStore`, `GeneralCodingRules`, and fitness-function framing — §4.15 throughout |
| https://kata-log.rocks/refactoring , https://www.codurance.com/publications/intermediate-refactoring-katas , https://understandlegacycode.com/blog/5-coding-exercises-to-practice-refactoring-legacy-code/ , https://github.com/emilybache/GildedRose-Refactoring-Kata | The named kata list — Gilded Rose, Tennis, Trip Service, Theatrical Players, Ugly Trivia, Parallel Change, Tell-Don't-Ask, Supermarket Receipt — §5.3.16 |
| https://www.baeldung.com/java-singleton-double-checked-locking , https://java-design-patterns.com/patterns/double-checked-locking/ , https://www.java67.com/2016/04/why-double-checked-locking-was-broken-before-java5.html | The DCL "spot the bug" framing (missing `volatile`) as an actual interview shape, plus Doug Lea's position that DCL is now an anti-pattern because its motivating forces are gone — §5.1.8, §5.1.50, §5.2.12, §5.3.21 |
| https://medium.com/@mahmoudosman1819/... , https://bytecrafted.dev/solid-principles-interview-questions/ , https://javatechonline.com/solid-principles-interview-questions-and-answers/ | The SRP misconception "one class → one object" (SRP says nothing about object creation), and the "start with YAGNI, refactor to SOLID" framing — §5.2.58, §5.1.36 |

Fetch note: only one `WebFetch` was attempted (the Devinterview README) and it succeeded but
returned 15 of the stated 85 questions, the remainder being paywalled on devinterview.io. No
fetch failed. `WebSearch` was not exhausted; nine distinct queries were run across the
interview-surface, disambiguation, DDD, SOLID-trap, primary-source (Resilience4j, ArchUnit),
curriculum (katas), adversarial (hexagonal misconceptions) and completeness-probe angles.

### Gaps vs the current guide — lane F

| Syllabus leaf | In `src/topics/24-…` | Verdict |
|---|---|---|
| §4.1–§4.15 (all 143 leaves) | absent — the guide has no build-it content at all | missing |
| §4.1.5 cycle detection before recursion | absent; § 6.4 names cycles as an anti-pattern only | missing |
| §4.2.5 self-invocation as an executable assertion | line 305, one `**Trap:**` paragraph, no code | shallow |
| §4.3 `ServiceLoader` / `SpringFactoriesLoader` | absent entirely | missing |
| §4.4 state-machine engine with guards | § 4.3 lines 443–451 give a 9-line enum, no guards, no actions, no engine | shallow |
| §4.5.5 bounded async queue and `CallerRunsPolicy` | § 8 table row names the unbounded-queue OOM in one clause | shallow |
| §4.6.2 the seven breaker constants with values | § 8 table describes the breaker in one sentence; no numbers at all | missing |
| §4.7.2–§4.7.3 the jitter formulas and the de-correlation proof | § 8 table says "plus random jitter"; no formula, no proof | shallow |
| §4.8.3 bulkhead sizing by Little's law against the 600/min cap | § 8 says "small enough that all of them together fit the box" | shallow |
| §4.9.2 the composite unique index DDL | § 8 table names "the unique index *is* the mechanism"; no schema | shallow |
| §4.10.3 at-least-once proof, §4.10.4 `skip locked` | outbox mentioned in § 4.4 and § 7.7 as a pointer to `14`; no mechanism | missing |
| §4.11.3 the §11.6 worked numbers as the fold's test | absent; § 7.7 names snapshotting in one bullet | missing |
| §4.12.4 the three lag definitions | § 7.7 says "say eventual consistency window of ~X ms" without defining the measurement | shallow |
| §4.13 specification combinator | absent; specification is not named anywhere in the guide | missing |
| §4.14.1 the domain module's build file as the artefact | line 786 states the test in one clause; no module layout, no code | shallow |
| §4.15.2–§4.15.10 ArchUnit rules by name | line 786 mentions "ArchUnit can assert it in a test"; zero rule names | missing |
| §5.1 (100 questions with probes) | § 10 gives the four-part answer shape and three rejection templates; no question bank | missing |
| §5.1.46–5.1.65 the internals tier | absent from the guide's interview section entirely | missing |
| §5.2 (107 one-line traps) | 31 `**Trap:**` markers exist as paragraphs; none in one-line recall form, and none consolidated | shallow |
| §5.2.7, .18, .25, .52, .77, .90, .95 the version-stale beliefs | absent as a category; the guide states current truth without naming the stale belief | missing |
| §5.2.58 "SRP means one class per object" | absent | missing |
| §5.2.83–§5.2.84 hexagon-means-three-modules, six-ports | absent | missing |
| §5.2.92 the event log is not queryable | line 881, one clause | shallow |
| §5.3.1–§5.3.8 whiteboard exercises | absent | missing |
| §5.3.9–§5.3.16 refactoring katas | § 9 gives a six-row smell/move/test table but no exercises and no named katas | shallow |
| §5.3.17–§5.3.18 name-the-pattern-in-this-class drills | absent; the guide names JDK flyweights only | missing |
| §5.3.19–§5.3.20 spoken drills | § 10 gives three rejection templates, unrehearsed | shallow |
| §5.3.24 spaced-repetition schedule over the 66-item checklist | absent; the checklist exists with no schedule | missing |
| D-01–D-32 | the guide has no diagrams of any kind | missing |

### Notes for the orchestrator — lane F

**Leaf counts and the arithmetic.** Counted on disk with
`grep -cE '^[0-9]+\.[0-9]+\.[0-9]+ '` per section, not estimated.

PART 4: §4.1 = 10, §4.2 = 9, §4.3 = 8, §4.4 = 10, §4.5 = 10, §4.6 = 10, §4.7 = 9, §4.8 = 9,
§4.9 = 10, §4.10 = 10, §4.11 = 10, §4.12 = 9, §4.13 = 9, §4.14 = 10, §4.15 = 10.
Sum: 10+9+8+10+10+10+9+9+10+10+10+9+9+10+10 = **143**.

PART 5: §5.1 = 100, §5.2 = 107, §5.3 = 25. Sum: 100+107+25 = **232**.

Lane F leaf total: 143 + 232 = **375**. Plus 32 diagram-manifest rows, which are table entries
and are deliberately not counted as leaves. File length: 1,851 lines.

**Deviation from the brief's sizing, stated explicitly.** The brief asked for ≈110 leaves in
PART 4 and I shipped 143 (+30%), outside the ±15% band. The cause is the "name the parts the
write pass has to ship" instruction colliding with the ≈7-per-section budget: each section
needs, at minimum, an API leaf, a data-structure leaf, a policy/constants leaf, a proof leaf, an
edge-case leaf, a concurrency leaf and the diff table — seven before any section-specific
mechanism. Sections with a real proof obligation (§4.6 windows, §4.10 at-least-once, §4.11 the
win/void asymmetry) needed nine or ten. §5.2 is 107 against ≈90 because the current guide
carries 31 `**Trap:**` markers plus six embedded in the § 8 resilience table, and the brief
required every one restated plus the eight version-stale beliefs; 107 is the count after
merging near-duplicates, not before. **If the orchestrator needs the totals table to match the
brief's ≈110/≈90, tell me which sections to compress and I will cut rather than have you
renumber.** I did not pad: no leaf restates its neighbour.

**Tag counts for the lane** (counted on disk over the leaf sections only, excluding these
trailing blocks): `[TRAP]` 126, `[BUILD]` 92, `[API]` 51, `[PROVE]` 31, `[NUM]` 30,
`[SAY]` 29, `[DECIDE]` 23, `[TABLE]` 17, `[X-REF nn]` 16, `[VERSION-TRAP]` 15, `[DIAG]` 4,
`[INCIDENT]` 3, `[SOURCE]` 3, `[FLOW]` 2, `[RESEARCH]` 1, `[SMELL]` 0. Tags exceed leaf
counts because most leaves carry two or three.

`[SMELL]` is zero in this lane by design — smells belong to §2.15 (lane D). The §5.3 refactoring
katas each carry a smell, a smallest move and a protecting test in the leaf body, but they are
drills rather than catalogue entries, so I left them untagged rather than mis-tag them `[SMELL]`
and duplicate lane D's catalogue.

**Things I could not verify, named with the constant and the source that would settle it.**

1. **Resilience4j 2.x `CircuitBreakerConfig` defaults.** I state
   `failureRateThreshold = 50`, `slidingWindowSize = 100`, `minimumNumberOfCalls = 100`
   (documented) versus the `20` I used in §4.6.2 as a *tuned* value for this domain — the
   documented default is 100 and I chose 20 deliberately for the 40/sec deposit path. The
   `waitDurationInOpenState = 60s` default and `permittedNumberOfCallsInHalfOpenState = 10`
   were not confirmed against a 2.x source. Settled by
   `resilience4j-circuitbreaker/src/main/java/io/github/resilience4j/circuitbreaker/CircuitBreakerConfig.java`
   on the 2.x tag. §4.6.2 is tagged `[NUM]`; the write pass must re-read that file before
   printing any of these numbers as "the default".
2. **`RingBitSet` as the current count-based window implementation.** Secondary sources
   (DeepWiki, Storozhuk's article) name it; the class may have been superseded by
   `FixedSizeSlidingWindowMetrics` in 1.x→2.x. Settled by the
   `io.github.resilience4j.core.metrics` package listing on the 2.x tag. Leaf §4.6.10 names
   both and is tagged `[SOURCE]` so the write pass must quote the real one.
3. **Spring Data JPA `Specification.allOf` / `anyOf` availability.** I attribute them to Spring
   Data 3.x in §4.13.9; not verified against a release note. Settled by the Spring Data JPA
   3.x javadoc for `org.springframework.data.jpa.domain.Specification`. Tagged
   `[VERSION-TRAP]`.
4. **`InvocationHandler.invokeDefault` since Java 16.** Stated in §4.2.4 from memory of
   JDK-8159746 / JEP-adjacent work; not re-verified. Settled by the `java.lang.reflect.InvocationHandler`
   javadoc's `@since` tag.
5. **Debezium `OutboxEventRouter` expected column names.** §4.10.10 names the SMT but I did not
   confirm the current default column set (`aggregatetype`, `aggregateid`, `type`, `payload`).
   Settled by the Debezium outbox-event-router transformation docs for the deployed version.
6. **Devinterview's remaining 70 questions.** The README exposes 15; the rest are behind the
   site. §5.1 is therefore complete against my own coverage frame and against nine other
   sources, but not against that specific list. If completeness against a published bank
   matters, that fetch needs an authenticated or alternative route.

**Out of scope, and where I sent it.** JMH harness mechanics for §4.2.8 and §4.6 cost
measurement → `25` via `[X-REF 25]`. Kafka delivery semantics and consumer-group mechanics
behind §4.10 → `14`. `@Version` SQL generation and `LazyInitializationException` mechanics
behind §4.13.6 and §4.14.8 → `08`. Safe publication and CAS mechanics behind §4.1.8, §4.3.6 and
§4.6.6 → `05`. ClassLoader-per-plugin design behind §4.3.7 → `06`. Testcontainers and test-slice
mechanics behind §4.14.7 → `16`. The behavioural framing of §5.1.98 ("a design decision you got
wrong") → `26`. Cross-service saga transport and distributed-transaction topology → `22`, which
owns everything past the service boundary; §4.10 and §4.16-adjacent leaves stop at the outbox
table and the relay.

**One cross-lane dependency worth flagging.** §5.2 restates traps that lanes A–E own as
paragraphs. I wrote it from `src/topics/24-…` rather than from the other lanes' output, which I
cannot see. If any lane introduces a `[TRAP]` leaf that is not already a `**Trap:**` marker in
the current guide, it will be missing from §5.2 and the orchestrator should hand me the list to
append rather than leaving §5.2 incomplete — §5.2's stated contract is that *every* `[TRAP]` any
lane produces appears there in one line.

**Manifest placement caveat.** D-01 through D-32 reference sections in lanes A–E by number from
the brief's inventory, not from those lanes' written output, so a leaf ref like `§2.13` names the
section rather than a specific leaf. If the orchestrator wants leaf-level refs (`§2.13.7`), that
needs a second pass after the lanes merge.
