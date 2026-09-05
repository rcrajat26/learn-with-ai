## §1.20 Strategy — the switch relocated to wiring time

1.20.1 The force: one step of an algorithm varies, the surrounding workflow does not, and the
       choice must be made per request/per tenant/per row rather than per deployment. `[PROVE]`

1.20.2 What strategy replaced: a `switch` on a mode string inside the method that owns the
       workflow, duplicated at every call site that needed the same branch. `[PROVE]`

1.20.3 Structure and participants by name: `Context` (holds a reference), `Strategy` (the
       interface), `ConcreteStrategy` (one per algorithm), and the *selector* — the thing that
       maps a domain value to a strategy, which GoF leaves unnamed and which is where all the
       real design lives. `[API]`

1.20.4 QuizStakes implementation: `interface RestrictionRule { String key(); Verdict evaluate(ClientId c, Action a); }`
       with one `@Component` per entry in the §9.3 restriction catalog —
       `DEPOSIT_BLOCKED`, `DEPOSIT_LIMITED`, `WITHDRAWAL_HELD`, `SOURCE_OF_FUNDS_REQUIRED`,
       `ALL_BLOCKED`, `SELF_EXCLUDED`, `COOLING_OFF`, `DORMANT_FROZEN`. `[BUILD]`

1.20.5 The Spring registry idiom: `ClientRestrictions` takes `List<RestrictionRule>` in its
       constructor and folds it with
       `all.stream().collect(toMap(RestrictionRule::key, identity()))`. Adding a restriction
       type is one new `@Component` and zero edits to existing files. `[BUILD]`

1.20.6 `Map<String, RestrictionRule>` injected directly is also legal — Spring populates it
       keyed by **bean name**, per *Fine-tuning Annotation-based Autowiring with Qualifiers*.
       `[API] [RESEARCH]`

1.20.7 Why an explicit `key()` beats the bean name: a bean name is a Java identifier that a
       rename refactoring silently changes, it is not a domain value, and it cannot be the
       `type`+`source` **pair** that §9.3 says is the real restriction identity. `[DECIDE]`

1.20.8 The pair problem, stated concretely: `STAKE_BLOCKED` from `SYSTEM_ONBOARDING` lifts at
       `AA-801 ACTIVATED`; `STAKE_BLOCKED` from `ADMIN` does not. A bean-name key can hold one
       of those two; a `key()` returning `type + "/" + source` holds both. `[TRAP]`

1.20.9 `@Qualifier` on the injection point filters which beans land in the collection, which
       lets one service take *the deposit rules* and another take *the withdrawal rules* from
       the same bean type. `[API] [RESEARCH]`

1.20.10 Strategy **relocates** the switch, it does not remove it: the `Map.get` *is* the
        switch, evaluated at wiring time instead of at each call. `[TRAP]`

1.20.11 The consequence of relocating it: an unknown key becomes a **runtime**
        `UnknownRestrictionRuleException` where a `switch` over a sealed type or enum was a
        **compile-time** exhaustiveness check. The error moved from compile → request.
        `[PROVE] [TRAP]`

1.20.12 The mitigation that makes the relocation safe: a startup assertion that every
        `restriction_type`/`source` pair present in the `clientrestrictions` schema has a
        registered `RestrictionRule`, so the failure moves compile → **startup**, not
        compile → request. `[DECIDE] [BUILD]`

1.20.13 Cost — dispatch: the `RestrictionRule.evaluate` call site sees 11 receiver types on
        the hot path, so it degrades past bimorphic to a **megamorphic** inline cache and the
        JIT stops inlining it. Mechanism in §3.1. `[X-REF 06] [NUM]`

1.20.14 Cost — budget arithmetic: `ClientRestrictions` is synchronous on every money path
        inside a **30 ms p99** budget across **8 instances** on a **4 GB** heap; a
        non-inlined virtual call is single-digit nanoseconds, so the indirection is *not* the
        cost here and saying so is the honest answer. `[NUM] [PROVE]`

1.20.15 Cost — readability: each strategy is one more file, so "what happens for
        `SELF_EXCLUDED`" is a two-hop navigation and the stack trace names `RestrictionRule`
        rather than the rule. `[SMELL]`

1.20.16 `[DECIDE]` Do not use strategy when: the set is closed and you own it (a sealed
        interface + exhaustive switch is strictly better — compile-time checked, one place to
        read); there is exactly one implementation with no second on the roadmap; or the
        branches are one line each and share no state.

1.20.17 Testability consequence: each `ConcreteStrategy` is a plain JUnit test with no Spring
        context, and the `Context` is tested against a stub map — so strategy converts one
        wide integration test into N unit tests plus one wiring test. `[X-REF 16]`

1.20.18 JDK strategies by name: `java.util.Comparator`,
        `RejectedExecutionHandler` (`AbortPolicy`, `CallerRunsPolicy`, `DiscardPolicy`,
        `DiscardOldestPolicy`), `ThreadFactory`, `java.util.stream.Collector`.
        Spring: `PlatformTransactionManager`, `PasswordEncoder`, `ConversionService`,
        `CacheManager`, `HandlerMapping`. `[API]`

*(18 leaves)*

---

## §1.21 Template method — the skeleton that must be `final`

1.21.1 The force: the *sequence* of steps is the invariant and must not vary; individual steps
       vary, and the variation is per-subclass (compile time), not per-invocation. `[PROVE]`

1.21.2 Structure and participants: `AbstractClass` with one `final` template method, `abstract`
       primitive operations the subclass must supply, and non-abstract **hook** methods with a
       default the subclass may override. `[API]`

1.21.3 QuizStakes implementation: `BankDeposits` ingests one **40k-record** statement file
       (**500k at month end**) at **06:00** and is idle 23 hours; the skeleton is
       `public final Report run(StatementFileId id)` calling `load` → `validate` → `match` →
       `postToLedger` → `audit` → `report`, with `match` (sender matching against `SUSPENSE`)
       as the varying step. `[BUILD] [NUM]`

1.21.4 Why the skeleton must be `final`: the ordering *is* the business rule. Without `final`,
       a subclass can override `run` and post to the ledger before validating, and nothing in
       the type system objects. `final` is the only mechanism that makes the sequence
       enforceable. `[PROVE]`

1.21.5 The second reason for `final`: a proxied bean cannot have its `final` methods
       intercepted by CGLIB, so a `final` template method plus `@Transactional` on the
       template is a silent no-op. Name the interaction; mechanism in §3.8. `[TRAP]`

1.21.6 **Trap:** making the primitive operations `public` instead of `protected`. A public hook
       is callable out of sequence by any collaborator, which reintroduces exactly the
       ordering violation `final` was there to prevent. `[TRAP]`

1.21.7 **Trap:** a hook with a default implementation that does real work. Subclasses that
       override it without calling `super` silently drop that work — the fragile-base-class
       failure (§2.11) arriving through the pattern's front door. `[TRAP]`

1.21.8 Cost — coupling: the subclass inherits the base's **entire** protected surface and its
       self-call policy, which is the strongest coupling the language offers. `[PROVE]`

1.21.9 Cost — binding time: one subclass per variation, chosen at compile time, so a per-file
       or per-tenant choice needs a factory in front of it anyway. `[DECIDE]`

1.21.10 Cost — multiple varying steps: template method handles them *naturally* (several
        hooks) where strategy handles them badly (one object per step, or a wide interface).
        This is the one axis on which template method wins outright. `[TABLE]`

1.21.11 `[DECIDE]` Do not use template method when: the variation must be selected at runtime;
        the subclass needs a dependency the base does not have; the "skeleton" is two steps
        long; or you would need multiple inheritance to combine two variations. Prefer
        strategy-per-step or a functional callback.

1.21.12 The functional replacement in Java 21: pass the varying step as a lambda —
        `run(id, this::matchBySenderReference)` — which is composition, is runtime-selectable,
        and needs no subclass. Template method survives only where the base owns state or a
        lifecycle the callback cannot see. `[VERSION-TRAP]`

1.21.13 Testability consequence: the template can only be exercised through a concrete
        subclass, so tests must instantiate a test subclass; the strategy form lets you test
        the skeleton against a stub. Template method is the *less* testable of the two.
        `[X-REF 16]`

1.21.14 JDK/Spring template methods by name: `java.util.AbstractList`, `AbstractMap`,
        `AbstractCollection`, `HttpServlet.service()` dispatching to `doGet`/`doPost`,
        `JdbcTemplate` (with `ResultSetExtractor<T>` / `RowMapper<T>` /
        `RowMapperResultSetExtractor` as its callbacks), `TransactionTemplate`,
        `AbstractApplicationContext.refresh()`,
        `AbstractPlatformTransactionManager.getTransaction()`. `[API] [RESEARCH]`

*(14 leaves)*

---

## §1.22 State — the object that chooses its own successor

1.22.1 The force: an entity has a lifecycle, the legal transitions are a business rule, and
       that rule must be enforced in exactly one place regardless of which caller drives it.
       `[PROVE]`

1.22.2 Structure and participants: `Context` (holds the current `State`), `State` (interface
       with the lifecycle-sensitive operations), `ConcreteState` (one per stage, each knowing
       its permitted successors), and the transition itself performed by the state, not by
       the caller. `[API]`

1.22.3 The separator from strategy, stated as one sentence: **a strategy is chosen from
       outside and never changes itself; a state decides its own successor.** If the
       transition logic lives inside the object, it is State. `[SAY]`

1.22.4 The anti-pattern state replaces: boolean-flag sprawl —
       `boolean paid, shipped, cancelled, refunded` on one row. `[SMELL]`

1.22.5 The arithmetic of the sprawl: 4 booleans is **2⁴ = 16** representable combinations of
       which roughly 6 are legal, so 10 illegal states are *representable* and every method
       must defensively re-check the combination. `[NUM] [PROVE]`

1.22.6 The mechanism of the fix, named: **making illegal states unrepresentable** — one
       `status` field plus an explicit transition table, so the 10 illegal combinations stop
       existing rather than being guarded against. `[PROVE]`

1.22.7 QuizStakes: twelve state machines (§3.1 of the scenario), the phase-structured ones
       carrying numbered codes (`AO-nnn`, `AA-nnn`, `DEP-nnn`, `BDP-nnn`) and the short linear
       ones bare names (Restriction, Bonus, Stake, `PaymentRun`, account lifecycle, document
       requirement, instrument verification). `[API]`

1.22.8 The numbered-code structure as an encoded state design: `XX-Nnn` where `XX` is the
       owning domain, `N` the phase, and the middle digit the **disposition** —
       `0` in progress, `1` success/advanced, `5` referred to a human, `9` failed/blocked.
       The code itself tells you where you are. `[PROVE] [NUM]`

1.22.9 The enum-with-permitted-successors form:
       `enum PaymentRunStatus { DRAFT(Set.of(APPROVED, CANCELLED)), APPROVED(Set.of(SUBMITTED)), … }`
       with `assertCanMoveTo(next)` throwing `IllegalStateTransitionException`. `[BUILD]`

1.22.10 **Trap:** enforcing transitions in the application service instead of on the aggregate.
        A second service, the 06:00 `BankDeposits` batch, `InternalPlatforms` operator tooling,
        or a data-fix script then bypasses the guard entirely. `[TRAP]`

1.22.11 Where the guard belongs: **inside the aggregate's invariant boundary** — the transition
        method on the root, so there is no path to the field that skips it. Aggregate rules in
        §2.22. `[DECIDE]`

1.22.12 The terminal-state leaf: `AA-599 SCREENING_PROHIBITED` and `SELF_EXCLUDED` are
        deliberately **not escapable**, and `reversibleByOperator = false` is how that becomes
        a property of the *data* rather than a hope about behaviour. `[PROVE]`

1.22.13 Cost: one class or enum constant per state, and cross-cutting behaviour (audit every
        transition into `ApplicationHistory`) must be factored out or it is duplicated N times.
        `[SMELL]`

1.22.14 `[DECIDE]` Do not use full state-pattern objects when: the machine has ≤3 states and no
        per-state dependencies (an enum with a transition table is enough); or the "states" are
        really independent overlapping flags — §9.1's restrictions are **additive, overlapping,
        independently sourced** and correctly modelled as a *set*, not a state machine.

1.22.15 Testability consequence: the transition table is a table-driven parameterised test over
        every (from, to) pair, asserting exactly the legal set passes — the one design where
        exhaustive testing is cheap. `[X-REF 16]`

*(15 leaves)*

---

## §1.23 Observer — and the four ways in-process observers bite

1.23.1 The force: one thing happens, an open set of other things must react, and the source
       must not know them. `[PROVE]`

1.23.2 Structure and participants: `Subject` (keeps a listener list, iterates on event),
       `Observer` (the reaction), plus registration/deregistration. The coupling inverts —
       listeners depend on the event type, not the publisher on the listeners. `[API]`

1.23.3 QuizStakes: `FundsLedger` publishes `StakeSettled` and `BalanceView` invalidates its
       derived stakeable/withdrawable figures; `PendingActions` reacts to
       `SourceOfFundsRequirementRaised`; `NotificationService` reacts to `AccountActivated`.
       `[BUILD]`

1.23.4 Spring API by exact name: `ApplicationEventPublisher.publishEvent`,
       `ApplicationListener<E>`, `@EventListener`, and the dispatcher
       `SimpleApplicationEventMulticaster` behind the
       `ApplicationEventMulticaster` interface. Internals in §3.19. `[API]`

1.23.5 The default is **synchronous, on the publisher's thread, inside the publisher's
       transaction** — every failure mode below follows from that one sentence. `[PROVE]`

1.23.6 Failure mode 1 — **latency coupling.** Ten listeners at 50 ms each add 500 ms to the
       publishing request. Against the **150 ms stake-reservation budget** that is a 4×
       overshoot caused entirely by code the reserve path never calls by name. `[NUM] [INCIDENT]`

1.23.7 Failure mode 2 — **failure/rollback coupling.** A listener throwing propagates back into
       the publisher and rolls back its transaction: "the notification failed, so the stake was
       never reserved." `[INCIDENT]`

1.23.8 The phase detail that decides whether 1.23.7 can happen: at `BEFORE_COMMIT` the listener
       sees the publisher's thread-bound transaction and its exception **can** prevent the
       commit; at `AFTER_COMMIT`, `AFTER_ROLLBACK` and `AFTER_COMPLETION` the transaction is
       already resolved and a listener failure **cannot** roll it back. `[RESEARCH] [PROVE]`

1.23.9 The corollary nobody states: at `AFTER_COMMIT` the transactional resources may still be
       *active*, so data-access code in the listener participates in the original transaction
       but its changes are **never committed** — a silent lost write. `[RESEARCH] [TRAP]`

1.23.10 Failure mode 3 — **deadlock and reentrancy.** Publishing while holding a lock, with a
        listener that acquires the same locks in the opposite order, is the textbook in-process
        deadlock; and registering or removing a listener *during* iteration throws
        `ConcurrentModificationException`. `[X-REF 05] [TRAP]`

1.23.11 Failure mode 4 — **listener leak.** A registered listener is a strong reference from the
        long-lived subject to the short-lived observer, so a never-deregistered listener is a
        heap leak. `[PROVE]`

1.23.12 The leak has a name worth knowing: the **lapsed listener problem** — the canonical
        observer-pattern leak in garbage-collected languages, fixed by weak references or a
        `@PreDestroy` deregistration. `[RESEARCH] [SAY]`

1.23.13 The production shape, all three properties together: publish **after commit**
        (`@TransactionalEventListener(phase = AFTER_COMMIT)`), **asynchronously** (`@Async` plus
        a bounded executor), and **durably** for anything that must not be lost — the
        transactional **outbox**. Cross-referenced to §3.19 for the multicaster internals and
        §2.25/§3.17 for outbox mechanics. `[API] [X-REF 14]`

1.23.14 `@TransactionalEventListener` does **not** dispatch through
        `ApplicationEventMulticaster` the way plain `@EventListener` does — it registers a
        `TransactionSynchronization` instead. Naming this separates people who have read the
        source from people who have read a blog. `[RESEARCH] [SOURCE]`

1.23.15 **Trap:** treating in-process events as a delivery mechanism. An in-process event is
        lost on crash, has no retry, no ordering guarantee, no consumer lag metric and no
        redelivery. It decouples *within* one transaction boundary; it does not deliver.
        `[TRAP]`

1.23.16 The QuizStakes line that decides it: `FundsLedger` is the **sole writer of money**, so
        anything that must move money on reaction goes through the outbox, never through an
        in-process listener. `[DECIDE]`

1.23.17 Cost — traceability: the publisher's stack trace does not name the listener, so "who
        reacts to `StakeSettled`" is a repo-wide grep rather than a call-hierarchy lookup.
        This is the real reason event-heavy codebases are hard to onboard onto. `[SMELL]`

1.23.18 Cost — ordering: listener order is unspecified unless declared with `@Order`, so two
        listeners that both mutate `BalanceView` have a race that only appears under load.
        `[API] [TRAP]`

1.23.19 `[DECIDE]` Do not use observer when: there is exactly one reactor and it is not optional
        (call it directly — the indirection buys nothing and costs the stack trace); the
        reaction must be transactional with the cause; or the reaction must be guaranteed
        (use the outbox).

1.23.20 JDK observers by name: `java.util.Observer`/`Observable` (**deprecated since Java 9** —
        no thread safety, no event objects, no ordering; do not cite it as the modern answer),
        `java.beans.PropertyChangeListener`, `java.util.EventListener`,
        `java.util.concurrent.Flow.Subscriber`. `[VERSION-TRAP] [API]`

*(20 leaves)*

---

## §1.24 Command — the invocation reified as a value

1.24.1 The force: an operation must be treated as **data** — queued, logged, authorised,
       replayed or undone — rather than executed at the call site. `[PROVE]`

1.24.2 Structure and participants: `Command` (with `execute()`), `ConcreteCommand` (holding
       receiver + parameters), `Invoker` (holds and triggers), `Receiver` (does the work), and
       optionally `undo()`. `[API]`

1.24.3 The mechanism, stated exactly: reifying the invocation converts *control flow* into a
       *value*, and everything that works on values becomes available to it. `[SAY]`

1.24.4 The four capabilities that unlock, each named: **serialisation** (survives a restart),
       **queueing** (deferred execution), **logging** (an audit and replay log → event
       sourcing, §2.24), and **inversion** (`undo()`). `[PROVE]`

1.24.5 QuizStakes: `BankWithdrawal` owns `PaymentRun` — **1.8k records, 4 files/day**,
       operator-gated, drain-before-terminate. Each approved withdrawal is a command in the
       run; the run is the invoker; the file submission is the execution. `[BUILD] [NUM]`

1.24.6 The authorisation capability made concrete: `InternalPlatforms` records the operator
       *and the role used* on `ApproveWithdrawal`, which is only possible because the approval
       is an object with fields rather than a method call that has already returned. `[PROVE]`

1.24.7 The Java 21 shape: `sealed interface WithdrawalCommand permits Approve, Reject, Recall`
       of records, dispatched by an exhaustive pattern-matching `switch` — no `execute()` on
       the command at all, because the handler is now exhaustively checked. `[BUILD] [VERSION-TRAP]`

1.24.8 The trade-off inside 1.24.7: `execute()` on the command keeps behaviour with data and is
       open to new commands; the sealed + switch form is closed to new commands and open to new
       *handlers*. That is the expression problem again (§1.26). `[DECIDE]`

1.24.9 JDK commands by name: `Runnable`, `Callable<V>`, `java.awt.event.ActionListener`,
       `javax.swing.Action`. Spring: `TransactionCallback<T>`, `StatementCallback<T>`,
       `TaskExecutor.execute(Runnable)`, Spring Batch `Tasklet`. Every message on a queue is a
       command. `[API]`

1.24.10 Cost — the parameter object: the command must capture everything the receiver needs, so
        it duplicates a method signature as a type, and adding a parameter is now a schema
        change if the command is persisted. `[SMELL]`

1.24.11 **Trap:** an `undo()` that is not a true inverse. Undoing a settled stake cannot simply
        re-credit `CLIENT_CASH_AVAILABLE`, because §11.3's win/void asymmetry means reserved
        bonus returns as **cash** when won and as **bonus** when voided. A compensating command
        is a domain decision, not a mechanical reversal. `[TRAP] [PROVE]`

1.24.12 **Trap:** a persisted command that stores a Java class name. Renaming the class breaks
        replay of every historic command — the same versioning obligation event sourcing has
        (§2.24), arriving early and unannounced. `[TRAP]`

1.24.13 `[DECIDE]` Do not use command when: the operation executes immediately at the call site
        and is never deferred, logged as a value, or undone. A `Command` with one
        implementation and a synchronous `invoker.run(cmd)` is a method call wearing two extra
        types.

*(13 leaves)*

---

## §1.25 Chain of responsibility — the handler that may refuse to delegate

1.25.1 The force: a request passes a sequence of independent handlers, each of which may
       handle it, transform it, or pass it on, and the sequence must be reconfigurable without
       editing any handler. `[PROVE]`

1.25.2 The mechanism that distinguishes it from every other wrapper: the handler controls
       **both sides** of the delegation — code before the delegate call is request processing,
       code after it is response processing, and *not calling it at all* short-circuits the
       chain. `[PROVE]`

1.25.3 The real instance every backend engineer has already used: the **servlet filter chain**.
       `chain.doFilter(request, response)` is the pass-it-on call. `[API]`

1.25.4 Source-level identifiers in Tomcat's `org.apache.catalina.core.ApplicationFilterChain`:
       fields `ApplicationFilterConfig[] filters`, `int pos`, `int n`, `Servlet servlet`,
       and `public static final int INCREMENT = 10`; methods `doFilter`,
       `addFilter(ApplicationFilterConfig)`, `release()`. `[SOURCE] [API] [RESEARCH]`

1.25.5 The loop itself: `if (pos < n) { ApplicationFilterConfig filterConfig = filters[pos++];
       Filter filter = filterConfig.getFilter(); filter.doFilter(request, response, this); return; }`
       — the chain hands **itself** to the filter as the continuation, which is what makes the
       recursion work without a linked list of handlers. `[SOURCE] [FLOW]`

1.25.6 After the loop falls through (`pos == n`), the chain calls
       `servlet.service(request, response)` — so the servlet is the terminal handler, not a
       separate mechanism. `[SOURCE] [FLOW]`

1.25.7 The short-circuit as a security property: an authentication filter that returns 401
       **without** calling `doFilter` means the controller is never reached — which is why
       filter *order* is a security control and not a configuration detail. `[PROVE]`

1.25.8 QuizStakes: `ApplicationGateway` (2 GB heap, scaling **12 → 40 instances**) runs the
       chain — inbound rate limiting, client-token signature/expiry/session verification,
       **strip the client token**, attach the application token with `subject = clientId`,
       then route. The strip is a chain step, and a client token never travels past it.
       `[BUILD] [NUM]`

1.25.9 Spring's chains by exact name: `FilterChainProxy`, `SecurityFilterChain`,
       `HandlerExecutionChain` with `HandlerInterceptor.preHandle`/`postHandle`/`afterCompletion`,
       `ClientHttpRequestInterceptor`, and the AOP interceptor chain driven by
       `ReflectiveMethodInvocation.proceed()`. Internals in §3.11. `[API]`

1.25.10 The JDK's other chains, worth naming because they are the same shape:
        `java.lang.ClassLoader` parent-first delegation and
        `java.util.logging.Logger` parent handler delegation. `[API] [X-REF 06]`

1.25.11 **Trap:** confusing it with decorator. Both nest and both wrap the same interface. A
        decorator that skips its delegate is a **bug**; a chain handler that refuses to
        delegate is **doing its job** — termination is the point of the pattern. `[TRAP]`

1.25.12 **Trap:** an ordering bug that is invisible in code review. The order lives in
        configuration (`@Order`, `FilterRegistrationBean.setOrder`, the security DSL), not in
        the handlers, so a rate limiter accidentally placed after authentication lets unbounded
        unauthenticated traffic reach `JwtService`. `[TRAP] [INCIDENT]`

1.25.13 **Trap:** calling `doFilter` twice, or calling it after writing the response. Both
        produce `IllegalStateException: response already committed` and both come from
        forgetting the handler owns *both* sides of the delegation. `[TRAP]`

1.25.14 Cost: the request path is no longer readable in one place; a 12-filter chain means
        12 stack frames of framework code between the socket and your controller, and a
        latency regression has 12 candidate owners. `[SMELL] [X-REF 20]`

1.25.15 `[DECIDE]` Do not use chain of responsibility when: exactly one handler can ever apply
        and the choice is a lookup (use a strategy map — a chain that always runs to the end is
        an O(n) scan doing an O(1) job); or the handlers must run in a fixed order you own, in
        which case a straight-line method is more readable and cheaper to trace.

*(15 leaves)*

---

## §1.26 Visitor and double dispatch — and the mechanism that retired it

1.26.1 The force: many operations over a **stable** set of types, and you want to add operations
       without touching the types. `[PROVE]`

1.26.2 The mechanism Java lacks, stated first: Java's `invokevirtual` dispatches on the runtime
       type of the **receiver only**. There is no built-in dispatch on a *pair* of runtime
       types. `[PROVE] [X-REF 06]`

1.26.3 **Double dispatch**, named and traced: the client calls `node.accept(visitor)` — dispatch
       1, on the node's runtime type — and the node's `accept` body calls
       `visitor.visitPercentageFee(this)` — dispatch 2, on the visitor's runtime type, with the
       static type of `this` now known to the compiler. Two virtual calls compose into a
       dispatch on the pair. `[FLOW] [PROVE]`

1.26.4 Structure and participants: `Element` (declares `accept(Visitor)`), `ConcreteElement`
       (implements `accept` with the single correct `visitX` call), `Visitor` (one `visitX` per
       element type), `ConcreteVisitor` (one per operation), `ObjectStructure` (drives the
       traversal). `[API]`

1.26.5 The **expression problem**, named: a type hierarchy can be open to new *types* or open to
       new *operations*, and neither plain virtual methods nor visitor gives you both.
       `[SAY] [RESEARCH]`

1.26.6 The two halves stated as costs: visitor makes **adding an operation cheap** (one new
       class) and **adding a type expensive** (every visitor must change); a plain interface
       method does exactly the reverse. Choose by which axis actually changes. `[TABLE] [DECIDE]`

1.26.7 **Trap:** the failure mode when a type is added and the `Visitor` interface has a
       `default` method or the codebase uses an abstract base visitor — the new type is then
       silently *unvisited* at runtime instead of breaking the build. The safety of visitor
       depends on the interface having no defaults. `[TRAP]`

1.26.8 The Java 21 replacement: a `sealed interface` plus an exhaustive pattern-matching
       `switch`. The compiler reads the `permits` clause to decide exhaustiveness, so the
       "every operation handles every type" guarantee arrives with **no** `accept`/`visit`
       boilerplate. `[VERSION-TRAP] [RESEARCH]`

1.26.9 The version facts: sealed classes finalised in **Java 17** (JEP 409), pattern matching
       for `switch` finalised in **Java 21** (JEP 441). Before 21 this was a preview feature, so
       pre-21 codebases legitimately still have visitors. `[NUM] [RESEARCH]`

1.26.10 The mechanism behind the guarantee, cross-referenced: the `PermittedSubclasses`
        class-file attribute and the `typeSwitch` bootstrap method, with `MatchException` for
        the runtime gap. Full treatment in §3.13. `[X-REF 04]`

1.26.11 QuizStakes: `sealed interface FeeRule permits Percentage, Flat, Tiered, Composite` with
        `switch (rule) { case Percentage p -> …; case Composite c -> …; }` — adding `Tiered`
        breaks compilation at **every** switch, which is the same safety visitor gave and is
        visible in one place. `[BUILD]`

1.26.12 The exhaustiveness asymmetry that matters in practice: with visitor, adding a type
        breaks compilation only if the visitor interface has no defaults; with a sealed switch
        it *always* breaks compilation, and the compiler points at every site. `[PROVE]`

1.26.13 The strong-signal sentence: **"visitor is what you write when the language has no
        exhaustive pattern matching."** `[SAY]`

1.26.14 Cost of the sealed form, honestly: the permitted subtypes must live in the same module
        (and same package unless the module is named), so the type set becomes *closed by
        compilation unit* — which is the point, and which makes it unusable for a genuinely
        plugin-extensible type set. `[DECIDE] [API]`

1.26.15 `[DECIDE]` Do not use visitor when: the type set is open (every new type edits every
        visitor — this is the failure, not an inconvenience); there is one operation (write the
        method); or the language gives you exhaustive switch over a sealed hierarchy, in which
        case visitor is pure ceremony.

1.26.16 JDK/Spring visitors by exact name: `java.nio.file.FileVisitor` /
        `SimpleFileVisitor` driven by `Files.walkFileTree`,
        `javax.lang.model.element.ElementVisitor` / `SimpleElementVisitor`,
        `javax.lang.model.type.TypeVisitor`, `AnnotationValueVisitor`; Spring's
        `BeanDefinitionVisitor` and `org.springframework.asm.ClassVisitor`. `[API] [RESEARCH]`

1.26.17 Testability consequence: a visitor is directly unit-testable against a hand-built
        element tree with no framework; a sealed switch is testable only through the method
        that contains it, which is a small but real loss. `[X-REF 16]`

*(17 leaves)*

---

## §1.27 Iterator — externalised cursor state and the fail-fast contract

1.27.1 The force: traverse a collection without exposing its representation, and support more
       than one simultaneous traversal. `[PROVE]`

1.27.2 The mechanism: externalise the cursor into a separate object, so the collection's
       internals stay private and each traversal owns its own position. `[PROVE]`

1.27.3 Structure and participants: `Iterator` (`hasNext`, `next`, `remove`), `Aggregate`
       (`iterator()` as the factory method), and the *internal* vs *external* iterator
       distinction — `forEach`/`Iterable.forEach` is internal, `Iterator` is external. `[API]`

1.27.4 `java.util.Iterator` exact surface: `hasNext()`, `next()`, `remove()` (optional,
       `UnsupportedOperationException` on immutable views), and the Java 8 addition
       `forEachRemaining(Consumer)`. `[API]`

1.27.5 The fail-fast contract, mechanically: `AbstractList` and `HashMap` keep an `int modCount`
       incremented on every structural modification; the iterator snapshots it as
       `expectedModCount` and compares in `checkForComodification()`, throwing
       `ConcurrentModificationException`. `[SOURCE] [API]`

1.27.6 **Trap:** treating fail-fast as a thread-safety guarantee. `modCount` is a plain
       non-`volatile` `int`, so the check is **best-effort** — the javadoc says fail-fast
       behaviour "cannot be guaranteed" and must be used **only to detect bugs**. It is a bug
       detector, not a concurrency mechanism. `[TRAP] [SOURCE]`

1.27.7 The corollary: the absence of a `ConcurrentModificationException` proves nothing. A racy
       `HashMap` write can corrupt the table, spin forever in `get`, or produce a torn read and
       never throw. `[X-REF 05] [TRAP]`

1.27.8 The single-threaded case that actually causes it: removing from a collection inside a
       `for (X x : xs)` loop. The fix is `Iterator.remove()`, `Collection.removeIf(Predicate)`,
       or iterating a copy. `[TRAP] [API]`

1.27.9 The weakly-consistent contrast: `ConcurrentHashMap`'s iterators and
       `CopyOnWriteArrayList`'s snapshot iterator never throw `ConcurrentModificationException`
       and reflect *some* state at or after construction — a different contract, not a stronger
       one. `[API] [X-REF 05]`

1.27.10 QuizStakes: `BankDeposits` streams a **40k-record** statement file (**500k at month
        end**) at **06:00** on a **6 GB** heap across **2 instances**. A `List`-materialising
        read is the wrong shape; a cursor is the whole point of the pattern here.
        `[BUILD] [NUM]`

1.27.11 The persistence-side iterators by name: Spring Data's `CloseableIterator<T>`,
        `Streamable<T>`, `Slice`/`Page`, and JPA's `Query.getResultStream()` — all iterators
        whose `close()` is load-bearing because they hold a DB cursor. `[API]`

1.27.12 `Spliterator` as the parallel-decomposition variant: `trySplit()`,
        `estimateSize()`, and the characteristic flags `ORDERED`, `SIZED`, `IMMUTABLE`,
        `CONCURRENT`, `SORTED`, `NONNULL`, `DISTINCT` — which is why `Stream` needed a new
        abstraction rather than reusing `Iterator`. `[API] [X-REF 04]`

1.27.13 Cost: an iterator object per traversal (usually scalar-replaced by escape analysis —
        §3.2), plus the fact that the pattern is *invisible* in modern Java because the
        for-each loop desugars to it, which is why candidates fail to name it as a pattern at
        all. `[X-REF 06] [SMELL]`

*(13 leaves)*

---

## §1.28 Mediator, memento, interpreter

1.28.1 **Mediator** force: N components that all talk to each other, giving N(N−1)/2 edges —
       **for N = 8 that is 28 pairwise couplings**. `[NUM] [PROVE]`

1.28.2 Mediator mechanism: components talk only to the mediator, which encodes the interaction
       rules; the edge count drops from **28 to 8**. `[NUM] [PROVE]`

1.28.3 The cost, named exactly: the mediator accumulates every interaction rule and becomes a
       **god object** (§2.14) — you have traded N² edges for one high-risk node that every
       change touches. `[TRAP] [DECIDE]`

1.28.4 QuizStakes mediator: `InternalPlatforms` — **40 operators on shift (90 at peak)**,
       **30–90 minute session-affine** sessions on a **4 GB** heap across **3 instances** —
       mediating review queues, case assignment and approval surfaces so that
       `AccountActivation`, `AccountMaintenance`, `ClientRestrictions` and `BankWithdrawal`
       never talk to each other about a case. `[BUILD] [NUM]`

1.28.5 The mediator's second obligation, easy to miss: it owns the **segregation-of-duties**
       rule — a reviewer who also holds an approver role must not exercise both on one case —
       which is precisely the kind of cross-component rule that has no other home. `[PROVE]`

1.28.6 Mediator by exact name in the JDK/Spring: `java.util.concurrent.ExecutorService`
       (submitter and worker never reference each other), Spring's `DispatcherServlet` (front
       controller that mediates handler mapping, adapter, resolver and view), and
       `ApplicationEventMulticaster`. `[API]`

1.28.7 `[DECIDE]` Do not use mediator when: the components are 3 or fewer; or the interaction is
       a broadcast rather than a negotiation (use observer — the mediator's value is the
       *rules*, and a mediator with no rules is a message bus with extra steps).

1.28.8 **Memento** force: capture and restore an object's state without exposing its internals.
       `[PROVE]`

1.28.9 Memento mechanism and the three participants: `Originator` (produces and consumes the
       snapshot), `Memento` (opaque — a **narrow** interface to everyone else and a **wide**
       one to the originator), `Caretaker` (stores it without reading it). The
       wide/narrow-interface asymmetry *is* the pattern. `[PROVE] [API]`

1.28.10 QuizStakes memento: the `FundsLedger` **snapshot at version N** that bounds
        event-sourced replay. Without it, rebuilding a position over **19.8M ledger entries/day
        at ~180 bytes/row** means reading the whole history. Snapshot mechanics in §3.16.
        `[NUM] [X-REF 08]`

1.28.11 Other real mementos by name: database `SAVEPOINT`, editor undo stacks, Spring Batch's
        `ExecutionContext` (which is what makes a failed 06:00 run restartable rather than
        rerunnable), `java.io.Serializable`/`ObjectOutputStream`. `[API]`

1.28.12 **Trap:** a memento that stores mutable references instead of a copy. The caretaker then
        holds a view of the *current* state, and "restore" is a no-op that looks like it worked.
        `[TRAP]`

1.28.13 `[DECIDE]` Do not use memento when: the object is already an immutable record (the
        object *is* its own snapshot — `withX` copy-with is enough); or the state is large and
        the restore is rare, where re-deriving from the source of truth is cheaper than
        carrying snapshots.

1.28.14 **Interpreter** force: a recurring problem is best expressed in a small language, and the
        authors of the rules are not programmers. Mechanism: model the grammar as a composite of
        expression nodes (`AbstractExpression`, `TerminalExpression`, `NonterminalExpression`,
        `Context`) and evaluate recursively. `[API]`

1.28.15 Interpreter's real instances by name: `java.util.regex.Pattern`, `java.text.Format`,
        `javax.el.ExpressionFactory`, and Spring's SpEL — `SpelExpressionParser`,
        `ExpressionParser.parseExpression`, `StandardEvaluationContext`. `[API]`

1.28.16 `[DECIDE]` Do not build an interpreter: the cost is that you now own a **language** —
        its parser, its error messages, its tooling, its versioning, and its security surface
        (a rule expression is arbitrary code). QuizStakes' `BonusService` rules
        (**10% of first deposit capped at 100**, **14-day coupon validity**, **30-day expiry**)
        are configuration, not a language. Reach for an existing engine or a table before a
        grammar. `[TRAP] [DECIDE]`

*(16 leaves)*

---

## §1.29 The non-GoF vocabulary

1.29.1 Why this section exists: the patterns a backend engineer actually uses daily are mostly
       *not* in GoF, and naming them is what separates vocabulary from recall. `[PROVE]`

1.29.2 **Null object.** Force: callers litter `if (x == null)` and one path always forgets.
       Mechanism: a do-nothing implementation of the interface with neutral behaviour, so the
       null check disappears from every caller. `[PROVE]`

1.29.3 Null object in QuizStakes: `RestrictionRule.PERMISSIVE` returning `Verdict.ALLOW` for an
       unmapped action, so `ClientRestrictions` never branches on `null` inside the **30 ms
       p99** budget. `[BUILD] [NUM]`

1.29.4 **Trap:** a null object on a money path. A "no-op" `LedgerWriter` silently discards
       entries and the imbalance surfaces days later in reconciliation. Null object is correct
       for *optional collaborators* (metrics, notification), never for the writer of record.
       `[TRAP] [DECIDE]`

1.29.5 Null object's JDK relatives by name: `Collections.emptyList()`,
       `Optional.empty()`, `OutputStream.nullOutputStream()` (Java 11),
       `InputStream.nullInputStream()`, `Logger`'s no-op handlers. `[API]`

1.29.6 **Specification.** Force: a business predicate is needed in three places — validation,
       selection (query), and construction-to-order — and duplicating it lets the three drift.
       Named by Evans and Fowler in the *Specifications* paper. `[RESEARCH] [PROVE]`

1.29.7 Specification's operations by name: `isSatisfiedBy(candidate)`, boolean composition
       `and`/`or`/`not`, and the paper's three uses — **validation**, **selection**, and
       **building to order**; plus `remainderUnsatisfiedBy` for partial satisfaction and
       `asQuery`/`subsumes` for pushing the predicate into the database. `[API] [RESEARCH]`

1.29.8 The three named forms: **hard-coded** specification, **parameterised** specification, and
       **composite** specification (which is Composite, §1.17, applied to predicates).
       `[RESEARCH] [API]`

1.29.9 QuizStakes specification: `BonusEligibility` = `FirstDepositOnly.and(CouponValid)
       .and(OnePerIdentity)` — one object satisfying the §11.4 rule, reusable by `BonusService`
       for the grant decision and by `ProfileService` for the "why not" explanation. `[BUILD]`

1.29.10 The Java 21 realisation and its cost: `Predicate<T>` with `and`/`or`/`negate` gives the
        combinator algebra for free, but loses the *name* — and the name is what made the rule
        greppable and explainable to an auditor. A `record` implementing `Predicate<Client>` is
        the shape that keeps both. `[DECIDE] [VERSION-TRAP]`

1.29.11 **Trap:** a specification whose `isSatisfiedBy` runs in memory over a table the size of
        **2.4M registered clients**. Selection specifications must be translatable to a query
        (Spring Data's `Specification<T>` over the JPA Criteria API) or they are an N-row scan
        wearing a domain name. `[TRAP] [X-REF 08]`

1.29.12 **Value object.** No identity, equality by value, immutable. `record CouponCode(String value)`
        with validation in the compact constructor; a `record` is the exact Java shape. Direct
        cure for primitive obsession (§2.14). `[API]`

1.29.13 **DTO.** An object that carries data between processes, with **no business logic**;
        Fowler's PoEAA name. The **assembler** is its partner — the object that maps between
        DTO and domain objects, and the reason the mapping code has a home instead of being
        inlined in a controller. `[API] [RESEARCH]`

1.29.14 QuizStakes DTO/assembler: `ProfileService` assembles one screen from **eight owners**
        (application status, PII, document requirements, verdicts, screening, lifecycle,
        restrictions, balances across four buckets, and transactions from two schemas). The DTO
        is the response; the assembler is the fan-out and merge. `[BUILD] [NUM]`

1.29.15 **Trap:** DTO and entity as the same class. The wire format then binds to the schema, so
        adding a column changes the public API and Hyrum's law (§2.11) makes it permanent.
        `[TRAP]`

1.29.16 **Registry.** A well-known object other objects find things in — PoEAA's name for the
        thing the `Map<String, RestrictionRule>` of §1.20 actually is. Its hazard: a registry
        is global state, so a mutable registry is a singleton anti-pattern (§2.14) with a nicer
        name. `[API] [TRAP]`

1.29.17 **Servant.** Behaviour shared by a group of classes, factored into one object that takes
        them as parameters, rather than duplicated in each or forced into a common base — the
        composition-shaped alternative to a utility superclass. `[API]`

1.29.18 **Marker interface.** A type with no members, used to identify objects for different
        treatment: `java.io.Serializable`, `Cloneable`, `RandomAccess`,
        `java.rmi.Remote`. Compared with annotations: a marker interface is checkable by the
        **compiler** and usable as a bound in a method signature; an annotation is not.
        `[API] [PROVE]`

1.29.19 **Monostate.** All state `static`, instances behave identically — singleton's behaviour
        with an ordinary constructor, so callers cannot tell it is global. Listed because it is
        the *worst* form of hidden global state: invisible in the type signature and untestable.
        `[TRAP] [SMELL]`

1.29.20 **Module** (as a pattern, not JPMS): a named grouping with an explicit exported surface
        and hidden internals. Java's realisations are the package + `package-private` pair and
        JPMS `module-info.java` with `exports`/`requires`. Enforcement in §2.29 / §3.20.
        `[API]`

1.29.21 **RAII-equivalent: `try-with-resources` and `AutoCloseable`.** Force: a scope-bound
        resource must be released on every exit path including the exceptional one. Mechanism:
        the compiler generates the `finally` and calls `close()` in **reverse** declaration
        order. `[API] [PROVE]`

1.29.22 The details that make it more than syntax sugar: `AutoCloseable.close()` may throw
        (`Closeable.close()` narrows it to `IOException`); an exception from `close()` is
        **suppressed** and retrievable via `Throwable.getSuppressed()`; and Java 9 allows an
        effectively-final existing variable as the resource. `[API] [VERSION-TRAP]`

1.29.23 QuizStakes: `DocumentVerification` holds **2–6 MB** document buffers for
        **24k uploads/day → 68 GB/day** on an **8 GB** heap across **6 instances**. A leaked
        buffer here is an OOM within hours, which is why the buffer must be an `AutoCloseable`
        in a `try`-with-resources and not a field. `[NUM] [INCIDENT]`

*(23 leaves)*

---

## §1.30 SOLID at vocabulary level — the five stated as mechanisms

1.30.1 Why "vocabulary level" is a distinct pass: each principle has a *slogan* form that is
       unfalsifiable and a *mechanism* form that predicts a specific cost. This section names
       the mechanism; §2.6–§2.10 work each one through. `[PROVE]`

1.30.2 **SRP** — not "does one thing". **One axis of change / one set of stakeholders.** The
       mechanism: two actors editing one file means merge contention and **coupled releases**.
       Depth in §2.6. `[SAY]`

1.30.3 **OCP** — not "never modify existing code". Adding a *known kind* of variation should not
       require editing existing files, and that is only achievable where a polymorphic boundary
       **already exists** on the correct axis. Depth in §2.7. `[SAY]`

1.30.4 OCP's mechanism made concrete in one line: §1.20's `Map<String, RestrictionRule>` — a new
       restriction type is a new file and zero edits. `[PROVE]`

1.30.5 **LSP** — a subtype must be usable wherever the supertype is, **including its
       contracts**. The mechanism: compiling is not the test, because preconditions,
       postconditions and invariants are not in the type system. Depth in §2.8. `[SAY]`

1.30.6 LSP's canonical JDK violation, named at vocabulary level: `List.of(...)` returns a `List`
       whose every mutator throws `UnsupportedOperationException`; `Arrays.asList` is worse
       because `set` works and `add` throws. `[API] [TRAP]`

1.30.7 The consequence of an LSP violation, stated as the observable symptom: `instanceof`
       checks migrate into the **caller**, and once callers type-test, the polymorphism is gone
       and the abstraction is decorative. `[PROVE] [SMELL]`

1.30.8 **ISP** — an implementor must supply *every* method, so a wide interface forces stubs and
       each stub is a lie a caller can invoke. Symptom: a class where half the methods
       `return null` or throw. Depth in §2.9. `[SAY] [SMELL]`

1.30.9 ISP's second, less-quoted half: a wide interface breaks **OCP for the interface owner** —
       adding a method breaks every implementor. This is exactly what `default` methods on
       interfaces (Java 8) were introduced to soften. `[PROVE] [VERSION-TRAP]`

1.30.10 **DIP** — high-level policy must not depend on low-level detail; both depend on an
        abstraction **owned by the high-level module**. That last clause is the entire mechanism
        and the part everyone drops. Depth in §2.10. `[SAY]`

1.30.11 DIP's one-question test: **which module would you have to delete the other to compile?**
        If the domain would still compile with the JPA adapter deleted, the arrow is inverted;
        if not, you have interfaces without inversion. `[SAY] [DECIDE]`

*(11 leaves)*

---

## §1.31 Layered architecture — the correct default, and the symptom that it stopped being one

1.31.1 The structure: controller → service → repository → database, with all dependency arrows
       pointing **down**, and each layer permitted to call only the one beneath it. `[PROVE]`

1.31.2 The mechanism it buys: **technology** change is contained. Swapping the web framework
       touches the controller layer only, because nothing below it names a web type. `[PROVE]`

1.31.3 What it does **not** contain: **feature** change. A new field on a stake touches
       controller, service, repository, entity and schema — five files in four packages. That is
       change amplification, and it is structural, not a discipline failure. `[PROVE] [NUM]`

1.31.4 Why it is still the correct default for a small service, stated positively: it is the
       style with the lowest ceremony, every Java engineer already knows it, and Richards & Ford
       name it the right choice for small, simple applications and for tight budget/time
       constraints — explicitly as a **starting point**. `[DECIDE] [RESEARCH]`

1.31.5 QuizStakes services that are correctly layered and should stay that way:
       `ClientAgreements` (a legal evidence store), `ApplicationHistory` (append-only,
       write-once/read-rarely), `PersonalDetails` (per-field CRUD with access logging). Thin
       rules, no invariants worth a domain model. `[DECIDE]`

1.31.6 The exact symptom that means it has stopped being the right default, named:
       the **architecture sinkhole anti-pattern** — a request passes from layer to layer as
       pure pass-through with **no business logic, validation or transformation** performed in
       any of them. `[SMELL] [RESEARCH]`

1.31.7 The threshold, with the number: the **80/20 rule** — roughly 20% sinkhole requests is
       acceptable in any layered system; if ~80% of requests are pass-through, layered is the
       wrong style for the domain. `[NUM] [DECIDE] [RESEARCH]`

1.31.8 The second symptom, which is the one that actually bites: the domain ends up **depending
       on persistence** — the entities *are* JPA entities, so the domain cannot compile without
       Hibernate on the classpath. That is precisely what DIP (§1.30.10) forbids. `[TRAP]`

1.31.9 The third symptom: **shotgun surgery**, produced by layered *plus* package-by-layer
       (§2.19), because a feature's classes are scattered across four packages and every one of
       them must be `public`. `[SMELL]`

1.31.10 The mechanical consequence of package-by-layer, stated as the compiler fact: Java's
        access modifiers are **package-scoped**, so with package-by-layer every class must be
        `public` for the layer above to reach it and *nothing* can be hidden. `[PROVE]`

1.31.11 The "closed layers" rule and the escape hatch: layers are **closed** by default (you may
        not skip one), and an **open layer** is the deliberate, documented exception — a shared
        services layer everything may reach. An undocumented skip is erosion, not an open
        layer. `[API] [RESEARCH]`

1.31.12 The testability consequence: because the service layer depends on the repository
        interface *and* on the entity types, a service test needs either a database
        (Testcontainers) or heavy mocking. Hexagonal's payoff is that the domain test is plain
        JUnit with no Spring. `[X-REF 16] [DECIDE]`

1.31.13 The trigger to upgrade, stated as a sentence you say out loud: "layered now; I'd move to
        ports-and-adapters when the domain has invariants I need to test without a database, or
        when the sinkhole ratio says the layers aren't doing work." Styles compared in §2.17.
        `[SAY]`

*(13 leaves)*

---

## §1.32 Dependency injection and inversion of control, independent of Spring

1.32.1 The distinction to draw first: **IoC** is the general principle that the framework calls
       you (the Hollywood principle, §2.11); **DI** is one specific technique for achieving it,
       for the specific concern of *obtaining collaborators*. They are not synonyms and using
       them interchangeably is a tell. `[PROVE] [SAY]`

1.32.2 The force: a class that constructs its own collaborators has hard-coded them — the choice
       is invisible in the type signature, unswappable at runtime, and unsubstitutable in a
       test. `[PROVE]`

1.32.3 Fowler's three forms, by his names: **constructor injection**, **setter injection**, and
       **interface injection**. `[RESEARCH] [API]`

1.32.4 Constructor injection's two mechanical properties, in Fowler's own terms: it lets you
       "create valid objects at construction time" and it lets you make the fields `final` —
       so a half-wired object is unrepresentable and the object is safely publishable across
       threads. `[RESEARCH] [PROVE] [X-REF 05]`

1.32.5 Setter injection's stated case, also his: when there are a lot of constructor parameters
       "things can look messy". His recommendation is explicit — **start with constructor
       injection and be ready to switch to setter injection** when constructor complexity
       demands it. `[RESEARCH] [DECIDE]`

1.32.6 Interface injection's cost, in his words: "more invasive since you have to write a lot of
       interfaces" — which is why it effectively died. `[RESEARCH]`

1.32.7 **Field injection** as the fourth, non-Fowler form (`@Autowired` on a private field): no
       `final`, so no immutability; the dependency is invisible to any caller constructing the
       object; and it requires reflection to test. `[API] [SMELL]`

1.32.8 The field-injection consequence that is a design signal, not a style preference: a class
       with 12 field-injected dependencies looks the same in the constructor as one with 2, so
       field injection **hides the god-object smell** (§2.14) that a 12-argument constructor
       makes impossible to ignore. `[PROVE] [SMELL]`

1.32.9 The second field-injection consequence: it hides a circular dependency that constructor
       injection would fail loudly on at startup. `[TRAP] [X-REF 07]`

1.32.10 **Trap:** believing DI requires a container. `new StakeReservationService(new JpaLedger(em), clock)`
        in a test *is* dependency injection. The container is an assembly convenience; the
        pattern is the parameterisation. `[TRAP]`

1.32.11 The testability consequence, stated as the mechanism: with constructor injection the
        test supplies a fake and needs no framework; the test double implied is a **stub** for
        queries and a **mock** for commands (§2.28). `[X-REF 16]`

1.32.12 QuizStakes: `FundsLedger` takes `LedgerRepository`, `ReservationExpiryIndex` and
        `Clock` by constructor. Injecting the `Clock` is what makes the **30-day bonus expiry**
        and the **14-day coupon validity** testable without waiting. `[BUILD] [NUM]`

1.32.13 **Service locator** as DI's sibling: the object asks a well-known locator for its
        collaborators. Fowler's own distinction — with a service locator "application code asks
        for it explicitly by a message to the locator"; with injection "there is no explicit
        request, the service appears in the application class". `[RESEARCH] [API]`

1.32.14 **The honest correction Fowler himself makes**, and the reason this leaf exists: he
        argues there is "really no difference here between dependency injection and service
        locator: both are very amenable to stubbing." The usual interview claim that service
        locator is untestable is **wrong** — repeat his actual argument instead.
        `[VERSION-TRAP] [RESEARCH] [TRAP]`

1.32.15 The real difference, in his framing: "with a Service Locator every user of a service has
        a dependency to the locator" — so the locator is an extra coupling to an API that
        travels with the class. `[RESEARCH] [PROVE]`

1.32.16 His actual selection criteria, both directions: for **application-specific** code the
        service locator has "a slight edge due to its more straightforward behavior"; for
        **reusable components** DI is "a better choice" because it avoids depending on an
        external API. And the overarching point: the choice matters less than "separating
        service configuration from the use of services." `[RESEARCH] [DECIDE] [SAY]`

1.32.17 Cost of DI, named: the wiring is no longer in the code, so "what actually implements
        `RestrictionRule` here" is answered by configuration, profiles and classpath scanning
        rather than by the call graph — a startup-time failure class where you had a
        compile-time one. `[SMELL] [DECIDE]`

1.32.18 `[DECIDE]` Do not inject when: there is exactly one implementation, it is in the same
        module, and it will never be substituted in a test — a `Clock` yes, a `BigDecimal`
        rounding helper no. An interface + injection point per collaborator is how a 40-mock
        test suite is built.

*(18 leaves)*

---

## §1.33 The pattern census — where each of the 23 appears in the JDK, Spring, and QuizStakes

1.33.1 Why the census is a section and not a footnote: a pattern you cannot point at in code you
       already use is a pattern you have memorised, not learned. Every row below names a real
       type. `[PROVE]`

1.33.2 The census, all 23 GoF patterns. Cells marked **absent** where the pattern genuinely does
       not appear in that column. `[TABLE] [RESEARCH]`

| # | Pattern | JDK type | Spring type | QuizStakes use |
|---|---|---|---|---|
| 1 | Abstract factory | `DocumentBuilderFactory.newInstance()`, `TransformerFactory` | `BeanFactory`, `FactoryBean<T>`, `AbstractFactoryBean` | `PayoutRailFactory` producing a matched `RailClient` + `RailWebhookVerifier` pair per rail |
| 2 | Builder | `StringBuilder`, `Stream.Builder`, `Locale.Builder`, `HttpRequest.newBuilder()`, `Calendar.Builder` | `UriComponentsBuilder`, `BeanDefinitionBuilder`, `RestClient.builder()`, `MockMvcRequestBuilders` | `StakeReservation.Builder` — validation in `build()` |
| 3 | Factory method | `Calendar.getInstance()`, `Integer.valueOf`, `Collection.iterator()`, `Charset.forName`, `NumberFormat.getInstance` | `@Bean` methods, `FactoryBean.getObject()`, `ApplicationContext.getBean` | `LedgerEntry.of(position, amount, direction)` |
| 4 | Prototype | `Object.clone()`, `Cloneable`, `ArrayList.clone()` | `@Scope("prototype")`, `AbstractBeanDefinition.cloneBeanDefinition()` | `ScoringConfig.withWindow(...)` copy-with on a record |
| 5 | Singleton | `Runtime.getRuntime()`, `Desktop.getDesktop()` | default singleton scope, `DefaultSingletonBeanRegistry` | the `RestrictionCatalog` enum table in `ClientRestrictions` |
| 6 | Adapter | `Arrays.asList`, `Collections.enumeration`, `InputStreamReader`, `OutputStreamWriter` | `HandlerAdapter` / `RequestMappingHandlerAdapter`, `MessageListenerAdapter` | `DocumentVerification`'s adapter over the Identity Vendor SDK |
| 7 | Bridge | `java.sql.Driver` behind `DriverManager`; `java.util.logging` `Handler` × `Formatter` | `PlatformTransactionManager` abstraction × per-datasource implementor | `NotificationService`: notification kind × channel, M+N instead of M×N |
| 8 | Composite | `java.awt.Container`/`Component`, `javax.naming.CompositeName` | `CompositeCacheManager`, `CompositePropertySource`, `CompositeUriComponentsContributor` | `FeeRule.Composite`; the composite restriction predicate |
| 9 | Decorator | `BufferedInputStream`, `Collections.unmodifiableList`, `Collections.synchronizedMap` | `TransactionAwareCacheDecorator`, `ContentCachingRequestWrapper`, `DelegatingDataSource` | `RetryingPspClient` wrapping `MeteredPspClient` in `CardPayments` |
| 10 | Facade | `java.net.URL.openStream()`, `Executors` | `JdbcTemplate`, `TransactionTemplate`, `RestClient` | `PaymentService` over `CardPayments`/`BankDeposits`/`BankWithdrawal`/`FundsLedger`/`BonusService` |
| 11 | Flyweight | `Integer.valueOf` (`IntegerCache` −128..127), `String.intern()`, `Boolean.valueOf`, `Character` cache 0..127 | **absent** — Spring's annotation caches are caching, not intrinsic/extrinsic state splitting | interned `PositionCode`/`CurrencyCode` across 19.8M ledger rows/day |
| 12 | Proxy | `java.lang.reflect.Proxy.newProxyInstance`, RMI stubs | `JdkDynamicAopProxy`, `CglibAopProxy`, `TransactionInterceptor`, `ScopedProxyFactoryBean` | `@Transactional` on `FundsLedger`'s reserve path |
| 13 | Chain of responsibility | `jakarta.servlet.FilterChain` / Tomcat `ApplicationFilterChain`, `ClassLoader` parent delegation | `FilterChainProxy`, `SecurityFilterChain`, `HandlerExecutionChain`, `ReflectiveMethodInvocation.proceed()` | `ApplicationGateway`'s rate-limit → verify → strip-token → route chain |
| 14 | Command | `Runnable`, `Callable<V>`, `javax.swing.Action` | `TransactionCallback<T>`, `StatementCallback<T>`, Spring Batch `Tasklet` | `ApproveWithdrawal` from `InternalPlatforms`; `PaymentRun` items |
| 15 | Interpreter | `java.util.regex.Pattern`, `java.text.Format`, `javax.el.ExpressionFactory` | `SpelExpressionParser`, `ExpressionParser`, `StandardEvaluationContext` | **deliberately absent** — `BonusService` rules are a table, not a language (§1.28.16) |
| 16 | Iterator | `Iterator`, `Enumeration`, `ListIterator`, `Spliterator`, `Scanner` | Spring Data `CloseableIterator<T>`, `Streamable<T>`, `Slice`/`Page` | cursor over the 40k-record (500k month-end) `BankDeposits` statement file |
| 17 | Mediator | `java.util.concurrent.ExecutorService` | `DispatcherServlet`, `ApplicationEventMulticaster` | `InternalPlatforms` case assignment across 40 operators (90 peak) |
| 18 | Memento | `Serializable` + `ObjectOutputStream` | Spring Batch `ExecutionContext` | `FundsLedger` snapshot at version N bounding replay |
| 19 | Observer | `Flow.Subscriber`, `PropertyChangeListener`, `EventListener`, (`Observable`, deprecated 9) | `ApplicationListener`, `@EventListener`, `SimpleApplicationEventMulticaster`, `@TransactionalEventListener` | `StakeSettled` → `BalanceView` invalidation |
| 20 | State | **absent as a pattern** — `Thread.State` and `Matcher`'s internal state are state *values*, not state objects | **absent from core Spring**; Spring Statemachine (`StateMachine`, `StateMachineFactory`) is a separate project | the twelve state machines: `AO-`/`AA-` codes, `PaymentRun`, Bonus, Stake, Restriction, account lifecycle |
| 21 | Strategy | `Comparator`, `RejectedExecutionHandler`, `ThreadFactory`, `Collector` | `PlatformTransactionManager`, `PasswordEncoder`, `ConversionService`, `CacheManager`, `HandlerMapping` | `Map<String, RestrictionRule>` in `ClientRestrictions` under a 30 ms p99 budget |
| 22 | Template method | `AbstractList`, `AbstractMap`, `AbstractCollection`, `HttpServlet.service()` | `JdbcTemplate` (+`RowMapper<T>`, `ResultSetExtractor<T>`), `TransactionTemplate`, `AbstractApplicationContext.refresh()` | `BankDeposits`' `final run()` 06:00 ingestion skeleton |
| 23 | Visitor | `FileVisitor`/`SimpleFileVisitor` + `Files.walkFileTree`, `javax.lang.model.element.ElementVisitor` | `BeanDefinitionVisitor`, `org.springframework.asm.ClassVisitor` | **retired** — replaced by sealed `FeeRule` + exhaustive switch (§1.26.11) |

1.33.3 The three genuinely-absent cells and what each absence teaches: **flyweight has no Spring
       instance** because Spring's caches key on identity rather than splitting intrinsic from
       extrinsic state; **state has no JDK or core-Spring instance** because the JVM exposes
       state as enums and values, not as behaviour-carrying state objects; **interpreter is
       absent from QuizStakes by decision**, which is itself the lesson. `[PROVE] [DECIDE]`

1.33.4 The double-counting observation worth naming: `JdbcTemplate` is simultaneously a
       **facade** (one entry point over `DataSource`/`Connection`/`PreparedStatement`/`ResultSet`)
       and a **template method** (fixed skeleton, callback hooks). A type implementing two
       patterns is normal, and insisting on one label is the recall answer. `[PROVE] [TRAP]`

1.33.5 The multi-pattern types, listed: `JdbcTemplate` (facade + template method),
       `BeanFactory` (factory method + abstract factory + singleton registry),
       `Collections.unmodifiableList` (decorator + LSP violation, §1.30.6),
       `Integer.valueOf` (flyweight + static factory + `==` trap). `[TABLE]`

1.33.6 **Trap:** citing `java.util.Observable` as the JDK's observer without noting it was
       **deprecated in Java 9** — no thread safety, no event objects, no ordering. Naming the
       deprecation is what makes the citation current. `[VERSION-TRAP] [TRAP]`

1.33.7 **Trap:** citing `Arrays.asList` as the JDK's adapter without noting it is also the LSP
       violation of §1.30.6 (`set` works, `add` throws). The same line can be the good example
       and the bad one. `[TRAP]`

1.33.8 The patterns that Java 21 has materially reshaped, as a set: **visitor** (retired by
       sealed + exhaustive switch), **prototype** (retired by records + copy-with),
       **builder** (narrowed to ≥5 fields or optional fields, because records supply the
       immutable carrier), **template method** (narrowed by lambdas), **object pool**
       (narrowed by virtual threads and TLAB allocation). `[VERSION-TRAP] [TABLE]`

1.33.9 The census's interview use: when asked "give an example of pattern X", the scoring answer
       names the **JDK or Spring type first** and the domain use second, because the framework
       type proves you have read code and the domain use proves you have designed something.
       `[SAY]`

1.33.10 The counting caveat to state honestly: several of these mappings are community
        consensus rather than a claim the JDK authors made. `Collections.unmodifiableList` is
        documented as an unmodifiable *view*, not as "the decorator pattern" — the pattern
        reading is ours. `[RESEARCH] [TRAP]`

*(10 leaves)*

---

# PART 2 — INTERMEDIATE

Part 1 named the patterns. Part 2 owns the **judgement**: choosing between them, applying the
principles that explain why a choice is right, and recognising the smells, refactorings and
architectural styles that follow. It opens with the topic's decision apparatus (§2.1–§2.5) —
the tables and procedures that turn a force into a named pattern and separate the pairs that
look identical — then works each SOLID principle, the principle and component catalogues, the
anti-patterns and smells, the architecture styles, DDD, CQRS/event sourcing, the integration
and resilience families, testability, enforcement, and the cost model.

---

## §2.1 The master pattern-selection table: force → pattern → seam location → cost

2.1.1 The shape of the answer this table exists to produce: **"the varying thing here is X, the
      thing that must stay stable is Y, so I'd introduce Z, and the cost is W."** The table is
      indexed by X, not by Z, because an interviewer gives you a force and not a pattern name.
      `[SAY] [PROVE]`

2.1.2 The four columns and why each is mandatory: **force** (the recurring situation),
      **pattern** (the name), **seam location** (which file the polymorphic boundary lives in —
      the part candidates skip), **cost** (allocation, indirection, dispatch, one more file,
      error moved to runtime). `[TABLE]`

2.1.3 The master table. Read left to right; the interview answer is the whole row. `[TABLE]`

| Force (what varies) | Pattern | Seam location | Cost |
|---|---|---|---|
| Construction needs a name, a subtype, caching or pre-allocation failure | Static factory | A static method on the product type | Not overridable; not a substitution point at all |
| The concrete product type must be decided by a subclass of the creator | Factory method | An overridable instance method on the creator | Ties the choice to a class hierarchy, compile-time binding |
| A **family** of products must be mutually consistent | Abstract factory | One interface per family, one implementation per variant | One more type per product; redundant if DI already decides per deployment |
| Many parameters, several optional, must be immutable and valid on completion | Builder | A nested static `Builder` on the product | A second mutable type per product; ceremony below ~5 fields |
| Exactly one instance, lazily and safely initialised | Singleton (holder idiom / enum) | Private constructor + nested holder, or an enum constant | Global access is the anti-pattern half; untestable if `static` |
| Setup cost of a **non-heap** resource dominates | Object pool | A borrow/release facade over the resource | Borrow synchronisation, old-gen residency, dirty-state leakage |
| A third-party API does not fit your port | Adapter | One class per vendor, implementing your interface | One translation layer to maintain per vendor |
| A 6-call ceremony always happens together | Facade | A new, narrower interface you invent | Hides capability; becomes a god object if it grows |
| **Access** to the target must be controlled transparently | Proxy | Generated at runtime, or one hand-written wrapper | Self-invocation bypass; `final`/`private`/`static` uninterceptable |
| Optional **behaviours** must combine N-deep | Decorator | One wrapper class per behaviour, composed in wiring | N stack frames; order is now semantically significant |
| Clients must treat one item and a nested group identically | Composite | Container implements the leaf interface | Transparency-vs-safety LSP trade-off; unbounded recursion depth |
| **Two** dimensions vary independently | Bridge | An abstraction hierarchy holding an implementor hierarchy | Two hierarchies to navigate; M+N types instead of M×N |
| Millions of near-identical objects; **memory** is the constraint | Flyweight | An intrinsic-state pool + extrinsic parameters | A hash lookup per access; a net loss below millions |
| One **step** of a fixed workflow varies, chosen at runtime | Strategy | An interface + a keyed registry at the composition root | Unknown key is a runtime error; megamorphic dispatch |
| The **sequence** is the invariant; steps vary per subclass | Template method | A `final` template method in an abstract base | Inheritance coupling; compile-time binding only |
| Behaviour depends on a lifecycle stage that **transitions itself** | State | A transition table or state objects on the aggregate | One type per state; cross-cutting concerns duplicated |
| An open set of reactors must respond without the source knowing them | Observer | An event type + a publisher call | Latency/failure coupling, leak, unordered, untraceable |
| An invocation must become a value — queued, logged, replayed, undone | Command | A record per operation + one handler | A type per method signature; a persisted schema |
| A request passes handlers, any of which may terminate it | Chain of responsibility | An ordered handler list in configuration | Order is invisible in code; O(n) scan; deep stacks |
| Many operations over a **stable** type set | Visitor → sealed switch | A `visit` per type, or one exhaustive `switch` | Adding a type edits every visitor; sealed closes the module |
| Traverse without exposing representation | Iterator | An `iterator()` factory + a cursor object | Fail-fast is best-effort only; a cursor may hold a DB resource |
| N components with N² pairwise coupling | Mediator | One mediator holding the interaction rules | The mediator becomes the god object |
| State must be captured and restored opaquely | Memento | A snapshot type with a narrow public interface | Storage cost; a shallow snapshot restores nothing |
| Rules must be authored by non-programmers | Interpreter | A grammar of expression nodes | You now own a language, its errors and its security surface |
| Callers litter `if (x == null)` | Null object | A neutral implementation of the interface | Silences failures on paths where silence is wrong |
| One predicate is needed for validation, query and construction | Specification | A named predicate object with `and`/`or`/`not` | Must be query-translatable or it is a table scan |
| Collaborators must be substitutable and visible in the signature | Dependency injection | A constructor parameter + a composition root | Wiring leaves the call graph; failures move to startup |

2.1.4 How to read the **seam location** column, and why it is the discriminating one: the seam is
      the file that changes when the variation changes. If you cannot name that file, you have
      named a pattern without designing anything. `[SAY] [DECIDE]`

2.1.5 The cost taxonomy the last column draws from, enumerated so a cost can always be named:
      **allocation**, **indirection depth**, **dispatch cost**, **one more file to read**,
      **error moved later** (compile → startup → request), **stack-trace legibility**,
      **ordering becoming significant**, **a new schema/versioning obligation**. `[TABLE]`

2.1.6 The "error moved later" axis is the highest-value one to name out loud, because it is
      measurable: a `switch` over a sealed type fails at **compile** time, a registry with a
      startup assertion fails at **startup**, a bare registry fails at **request** time. Three
      designs, three different 3 a.m. experiences. `[SAY] [PROVE]`

2.1.7 The row that is missing from every pattern catalogue and belongs in this one:
      **force = "nothing varies yet"** → pattern = **none** → seam = **nowhere** →
      cost = **duplication, which is local and deletable**. `[DECIDE]`

2.1.8 The rule of three restated as the gate on this whole table: one case — write it inline;
      two — duplicate and wait; three — now the axis of variation is *observed* rather than
      guessed, and only now do you know where the seam goes. `[PROVE]`

2.1.9 Why a wrong seam is worse than duplication, stated as an asymmetry: duplication is local
      and deletable; a wrong abstraction is **load-bearing and referenced**, so removing it is a
      change to every caller. `[PROVE] [SAY]`

2.1.10 The QuizStakes worked row, end to end: force = the §9.3 restriction catalog grows on a
       regulatory cadence; stable thing = the deposit/stake/withdrawal flows must not change
       when one is added; pattern = strategy behind `Map<String, RestrictionRule>`; seam = one
       `@Component` per rule; cost = an unknown `type`/`source` pair is a runtime failure, so
       add the startup assertion. `[BUILD] [SAY]`

2.1.11 The second worked row, chosen because the answer is "no pattern": force = `BankDeposits`
       parses one statement file format from one banking partner; stable thing = nothing else
       depends on the parser; pattern = **none**, a private method; trigger to upgrade = a
       second banking partner. `[DECIDE] [SAY]`

2.1.12 `[DECIDE]` The rejection templates, verbatim, because rejecting a pattern scores higher
       than applying one: "there is one implementation and no roadmap for a second, so the
       indirection has nothing flowing through it"; "the set is closed and I own it, so a sealed
       interface with an exhaustive switch gives me compile-time safety a registry cannot";
       "the variation is per deployment, so a Spring profile does what this factory would do."

2.1.13 The trade-off vocabulary to use literally when naming a cost: coupling and cohesion;
       **binding time** (compile / deploy / startup / request); where the error surfaces;
       **change amplification** (files touched per feature); testability without a container;
       who owns the interface; blast radius; indirection depth. `[SAY]`

2.1.14 **Trap:** "pattern matching" as an interview strategy — hearing "many providers" and
       answering "Strategy". Named without the force it reads as recall, and the inevitable
       follow-up ("why not just a `switch`?") has no answer if the force was never articulated.
       `[TRAP]`

2.1.15 **Trap:** justifying a pattern with "more flexible" or "more maintainable". Both are
       unfalsifiable. Say instead which *specific future change* becomes a one-file change and
       which becomes harder — patterns buy flexibility on one axis by **freezing** the others.
       `[TRAP] [SAY]`

2.1.16 The freezing claim made concrete, because it is the strongest single sentence in this
       section: strategy makes new algorithms cheap and makes changing the strategy
       **interface** expensive, because every implementation must change. `[PROVE] [SAY]`

*(16 leaves)*

---

## §2.2 Creational decision procedure

2.2.1 The procedure exists because "how do I create this" has six candidate answers and the
      wrong one is either a 9-parameter constructor or an abstract factory that duplicates the
      container. `[PROVE]`

2.2.2 Step 1 — **is the choice of concrete type made per deployment or per request?** Per
      deployment → DI with a profile or `@Qualifier`; per request (from a tenant, a currency, a
      rail column on the row) → a factory or a keyed registry. This is the question DI
      genuinely cannot answer. `[DECIDE] [FLOW]`

2.2.3 Step 2 — **does construction need a name, a subtype, a cached instance, or to fail before
      allocating?** Yes → static factory method. These are the four things a constructor
      cannot do, and naming all four is the complete answer. `[DECIDE] [PROVE]`

2.2.4 The naming half made concrete: two constructors with the same erased signature are
      impossible, so `Money.ofMinor(1250)` and `Money.ofMajor(12.50)` can only exist as static
      factories. `[PROVE] [API]`

2.2.5 Step 3 — **how many parameters, and how many optional?** A constructor with 9 parameters
      of which 6 are optional implies **2⁶ = 64** telescoping overloads, and any two adjacent
      same-typed parameters are silently swappable at the call site. → builder. `[NUM] [PROVE]`

2.2.6 Step 3's threshold, stated as a rule rather than a feeling: **≥5 fields, or any optional
      field → builder; 2–3 fields → a record with static factories, where a builder is pure
      ceremony.** `[DECIDE] [NUM]`

2.2.7 Step 4 — **must the object be valid and immutable on completion?** Then validation lives
      in exactly one place: `build()` for a builder, the **compact constructor** for a record.
      Per-setter validation cannot check cross-field rules, because it runs before the other
      field is set. `[PROVE] [API]`

2.2.8 Step 5 — **do several products have to be mutually consistent?** Yes → abstract factory,
      and the test of whether it earned its place is whether the products are **obtainable
      separately**. If they are, the consistency guarantee is a comment. `[DECIDE] [PROVE]`

2.2.9 Step 6 — **is the resource non-heap with a real setup cost** (TCP connection, TLS
      handshake, OS thread, off-heap buffer)? Yes → pool. No → do not pool. `[DECIDE]`

2.2.10 Step 6's arithmetic, because it is the one creational decision with numbers: TLAB
       allocation is a pointer bump of a few nanoseconds and young-gen collection of dead
       objects is nearly free, whereas a pool adds borrow synchronisation, promotes objects into
       the old generation so they are **traced on every cycle**, and risks state leaking between
       borrowers. Pool connections, threads and off-heap buffers; never DTOs, entities or
       `StringBuilder`s. `[NUM] [PROVE] [X-REF 06]`

2.2.11 Step 7 — **exactly one instance?** Then choose by threat model: eager `static final` for
       always-needed (thread-safe by the class-initialisation lock); the
       **initialization-on-demand holder** idiom for lazy and lock-free after first use; an
       **enum** when serialization and reflection must not be able to produce a second instance.
       Never hand-rolled double-checked locking. `[DECIDE] [API]`

2.2.12 Step 7's separation that decides the "is singleton an anti-pattern" question: the
       **lifecycle** (one instance per container) is fine and ubiquitous; the **global static
       access** is the anti-pattern, because it is invisible in the constructor signature and no
       test can substitute it. `[SAY] [PROVE]`

2.2.13 The QuizStakes creational walk, all seven steps on one object: a `CardDeposit` is created
       per request from a rail chosen by the client's instrument (step 1 → registry), needs
       `ofMinorUnits` naming (step 2 → static factory), has 4 required and 3 optional fields
       (step 3 → builder), must satisfy the §11.4 rounding invariant on completion (step 4 →
       `build()`), has no product family (step 5 → no abstract factory), is a heap object (step
       6 → no pool), and is not a singleton (step 7). `[BUILD] [FLOW]`

2.2.14 `[DECIDE]` The creational "do not" list, each with its symptom: do not write an abstract
       factory when a Spring profile decides per deployment (a layer that only does what the
       container does); do not write a builder for a 2-field record (ceremony); do not pool heap
       objects (a pessimization); do not hand-write DCL (6 lines of subtlety to avoid a lock
       taken once); do not expose a `static getInstance()` (untestable global coupling).

*(14 leaves)*

---

## §2.3 Structural intent disambiguation — same interface? different intent?

2.3.1 Why this section is the highest-yield page in the topic: adapter, facade, proxy and
      decorator have nearly **identical structure** — an object holding a reference to another
      and forwarding calls. Interviewers probe exactly this boundary because it separates people
      who read the catalogue from people who have designed something. `[PROVE]`

2.3.2 The comparison table, with the disambiguating property in bold. `[TABLE]`

| | Interface vs target | Purpose | Composable | Who decides it is there | Owns target's lifecycle | Typical trigger |
|---|---|---|---|---|---|---|
| **Adapter** | **Different** (converts) | Make an incompatible API usable | No | The assembling code | No | A third-party SDK does not fit your port |
| **Facade** | **New, simpler, narrower** | Hide a subsystem behind one entry point | No | The assembling code | Sometimes | A 6-call ceremony that always happens together |
| **Proxy** | **Identical** | Control *access* — lazy, remote, security, caching, transactional | Rarely, and transparently | The framework/infrastructure, not the caller | Often (may create it lazily) | A cross-cutting concern, or an expensive/remote target |
| **Decorator** | **Identical** | Add *behaviour*, chosen at wiring time | **Yes, by design, N-deep** | The caller / assembling code | No — always handed a constructed target | Optional features in combination |

2.3.3 Discriminator 1, asked first because it splits the four into two pairs: **does the
      wrapper's interface equal the target's?** No → adapter or facade. Yes → proxy or
      decorator. `[FLOW] [DECIDE]`

2.3.4 Discriminator 2 — **adapter vs facade, the one question that separates them: does it
      target one object and translate, or several and simplify?** An adapter has an existing
      client interface it *must satisfy*; a facade **invents** one. `[SAY] [DECIDE]`

2.3.5 The corollary that settles arguments: an adapter's interface is imposed from outside, so
      it cannot be "improved"; a facade's interface is yours, so its risk is scope creep into a
      god object. Different pattern, different failure mode. `[PROVE]`

2.3.6 Discriminator 3 — **proxy vs decorator, the one question that separates them: does the
      client know the wrapper is there?** A decorator is *chosen by the assembling code* to add
      a feature and is meant to stack; a proxy is **transparent** — the client believes it holds
      the real thing. `[SAY] [DECIDE]`

2.3.7 The mechanical tie-breaker when intent is ambiguous, and the sharper of the two:
      **a decorator that skips its delegate is a bug; a proxy that skips its delegate — a cache
      hit, an access denial, a lazy no-op — is doing its job.** `[SAY] [PROVE]`

2.3.8 The second mechanical tie-breaker: a proxy typically **owns the target's lifecycle** and
      may create it lazily; a decorator is always handed a fully constructed target. `[PROVE]`

2.3.9 **Trap:** "a decorator and a proxy are the same thing, the difference is academic." They
      differ in the one thing an interviewer is testing: **intent visible in the wiring.**
      `new RetryingPspClient(new MeteredPspClient(real))` announces itself; `@Transactional`
      does not. `[TRAP]`

2.3.10 **Trap:** calling `@Transactional` a decorator. It is a proxy — you did not ask for it at
       the call site, two of them do not stack meaningfully, and it controls *whether and how*
       the target is invoked (including not at all, on a rollback-only path). `[TRAP]`

2.3.11 Discriminator 4 — **composite vs decorator**, since both nest on the same interface:
       **does the wrapper have one child or many?** A decorator has exactly one delegate and
       adds behaviour; a composite has a collection and **aggregates** their results. `[SAY]`

2.3.12 Discriminator 5 — **bridge vs strategy**, the pair most often merged: **is the split
       established up front as two hierarchies, or is one algorithm swapped inside an otherwise
       fixed class?** A bridge is a deliberate two-hierarchy split; strategy swaps one step.
       `[SAY] [DECIDE]`

2.3.13 Bridge's own force restated so 2.3.12 has teeth: `NotificationKind × Transport` as
       inheritance yields `EmailAccountActivated`, `SmsAccountActivated`, `EmailWithdrawalPaid`,
       … — an **M×N** class explosion that composition reduces to **M+N**. `[NUM] [PROVE]`

2.3.14 Discriminator 6 — **facade vs mediator**: a facade is **unidirectional** (callers → the
       subsystem, and the subsystem does not know the facade exists); a mediator is
       **bidirectional** (the components know the mediator and it knows them). `[SAY] [PROVE]`

2.3.15 Discriminator 7 — **flyweight vs singleton vs object pool**, since all three "reuse
       instances": flyweight shares **immutable intrinsic state** across millions of logical
       objects; singleton guarantees **one** instance; a pool **lends and reclaims** mutable
       instances. Sharing, uniqueness, lending. `[SAY] [TABLE]`

2.3.16 The QuizStakes structural walk, one per pattern so the intents are anchored:
       `DocumentVerification`'s Identity-Vendor wrapper is an **adapter** (their interface, not
       ours); `PaymentService` is a **facade** (an interface we invented over five services);
       `@Transactional` on `FundsLedger` is a **proxy** (transparent, may not invoke);
       `RetryingPspClient` over the **11 s p99** card PSP is a **decorator** (stacked
       deliberately in wiring). `[BUILD] [NUM]`

*(16 leaves)*

---

## §2.4 Behavioural disambiguation — strategy vs state vs template vs command vs visitor

2.4.1 Why the behavioural family needs its own table: the structural four share a *shape*, but
      the behavioural five share a *purpose* — "make behaviour vary" — and are told apart by
      **who chooses, when, and whether the object changes itself**. `[PROVE]`

2.4.2 The comparison table, with binding time and self-transition as the load-bearing columns.
      `[TABLE]`

| | What is encapsulated | Who chooses | Binding time | Self-transitioning | Multiple varying steps | Runtime swap |
|---|---|---|---|---|---|---|
| **Strategy** | An algorithm | The caller / the wiring, from **outside** | Runtime (injected object) | No | Awkward — one object per step, or a wide interface | Yes |
| **State** | State-dependent behaviour | The object itself | Runtime, and **it changes itself** | **Yes** | N/A — behaviour is keyed on a lifecycle stage | Yes, by itself |
| **Template method** | A fixed **sequence** with varying steps | The subclass author | **Compile time** (subclass) | No | **Natural** — several hooks | No |
| **Command** | An **invocation** (receiver + parameters) | Whoever constructs the command | Runtime, and it is **storable** | No | N/A | Yes |
| **Visitor** | An **operation** over a type set | The caller, per traversal | Runtime (which visitor), compile time (which types) | No | N/A | Yes |

2.4.3 The primary separator, asked first: **does the behaviour depend on a lifecycle stage the
      object owns?** Yes → state. No → continue. `[FLOW] [DECIDE]`

2.4.4 **Strategy vs state — the one question that separates them: is it chosen from outside, or
      does it transition itself?** If the transition logic lives in the object, it is State.
      `[SAY] [DECIDE]`

2.4.5 The commonly-repeated "stateless vs stateful" version of 2.4.4 is a weaker separator and
      worth being able to correct: a strategy may hold configuration (a rounding mode, a rate
      table) and still be a strategy. The discriminator is **self-transition**, not the presence
      of fields. `[VERSION-TRAP] [TRAP] [RESEARCH]`

2.4.6 **Strategy vs template method — the one question that separates them: composition or
      inheritance?** Strategy injects an object and can swap it at runtime; template method
      subclasses and is fixed at compile time. `[SAY]`

2.4.7 The second half of 2.4.6, which is the part usually dropped: **strategy varies the whole
      algorithm; template method varies specific parts of a fixed one.** Strategy replaces the
      body; template method fills the holes. `[PROVE] [RESEARCH]`

2.4.8 **Strategy vs command — the one question that separates them: does the object carry the
      arguments?** A strategy is a *how* invoked with parameters supplied per call; a command
      **captures its parameters**, which is what makes it storable, queueable and replayable.
      `[SAY] [PROVE]`

2.4.9 **Command vs observer — the one question that separates them: does the sender name the
      receiver?** A command has a known receiver and expresses an *intention* (imperative,
      "approve this withdrawal"); an event has unknown reactors and states a *fact* (past
      tense, `WithdrawalApproved`). `[SAY] [DECIDE]`

2.4.10 The naming rule that follows from 2.4.9, and it is a real code-review test: commands are
       imperative verbs, domain events are **past-tense facts**. `ApproveWithdrawal` vs
       `WithdrawalApproved`. A "command" named in the past tense is an event with a single
       consumer, and vice versa. `[SMELL] [SAY]`

2.4.11 **Visitor vs strategy — the one question that separates them: does the behaviour vary by
       the *type* being operated on, or by a *choice* independent of type?** Visitor dispatches
       on the element type; strategy dispatches on a selection. `[SAY]`

2.4.12 **Visitor vs iterator**, the pair confused because both traverse: an iterator externalises
       **position**; a visitor externalises **the operation performed at each position**. They
       compose — `Files.walkFileTree` is an iterator driving a visitor. `[SAY] [API]`

2.4.13 **Chain of responsibility vs strategy — the one question that separates them: may more
       than one handler apply?** Strategy selects exactly one; a chain offers the request to
       each in turn and any may terminate it. A chain where exactly one handler ever matches is
       an O(n) scan doing an O(1) job. `[SAY] [DECIDE]`

2.4.14 **Mediator vs observer — the one question that separates them: is there a rule, or only a
       broadcast?** A mediator's value is the interaction **rules** it holds; observer is
       fan-out with no rules. A mediator with no rules is a message bus with extra types.
       `[SAY]`

2.4.15 **Memento vs prototype**, both of which "copy an object": a memento's copy is **opaque**
       and exists to be restored *into the same object*; a prototype's copy is a **new usable
       object**. Same mechanism, opposite intent. `[SAY]`

2.4.16 **Template method vs chain of responsibility**, both of which sequence steps: a template
       method's sequence is fixed in code and every step runs; a chain's sequence is
       configuration and any step may terminate it. Fixed-and-total vs configured-and-abortable.
       `[SAY]`

2.4.17 The behavioural decision flow, as an ordered procedure. `[FLOW]`
       (1) Lifecycle stage that transitions itself → **state**.
       (2) Must the invocation be stored, queued, logged or undone → **command**.
       (3) Behaviour varies by element type over a stable type set → **visitor**, or a sealed
       switch if the language allows.
       (4) The sequence is the invariant and variation is per-subclass → **template method**.
       (5) One step varies and is chosen from outside at runtime → **strategy**.
       (6) Several independent handlers, any of which may terminate → **chain of responsibility**.
       (7) An open set of reactors that must not be known to the source → **observer**.
       (8) None of the above and nothing varies yet → **no pattern**.

2.4.18 The QuizStakes anchor for each of the five, so the table is not abstract:
       `PaymentRun`'s `DRAFT → APPROVED → SUBMITTED` is **state**; `ApproveWithdrawal` is
       **command**; `BankDeposits`' `final run()` is **template method**;
       `RestrictionRule` is **strategy**; the retired `FeeRule` traversal was **visitor**.
       `[BUILD]`

*(18 leaves)*

---

## §2.5 The confusable pairs, each with the one question that separates them

2.5.1 The purpose of this section and its format contract: every row reduces to **one question**
      whose answer names the pattern. A comparison you cannot compress to one question is a
      comparison you have not understood. `[SAY] [TABLE]`

2.5.2 The confusable-pairs table. The last column is the whole deliverable. `[TABLE]`

| Pair | The one question that separates them | Answer A → | Answer B → |
|---|---|---|---|
| Adapter / Facade | Does it wrap **one** object and translate, or **several** and simplify? | one → Adapter | several → Facade |
| Proxy / Decorator | Does the client **know** the wrapper is there? | no → Proxy | yes → Decorator |
| Proxy / Decorator (mechanical) | Is **skipping the delegate** a bug? | no, it is the job → Proxy | yes → Decorator |
| Decorator / Chain of responsibility | May a link **refuse to delegate**? | yes → Chain | no → Decorator |
| Decorator / Composite | One child or **many**? | many, aggregated → Composite | one → Decorator |
| Strategy / State | Chosen from **outside**, or does it **transition itself**? | outside → Strategy | itself → State |
| Strategy / Template method | **Composition** or **inheritance**? | composition → Strategy | inheritance → Template method |
| Strategy / Bridge | Is the two-hierarchy split established **up front**? | yes → Bridge | no, one step swapped → Strategy |
| Strategy / Command | Does the object **carry its arguments**? | yes → Command | no → Strategy |
| Strategy / Chain of responsibility | May **more than one** handler apply? | yes → Chain | exactly one → Strategy |
| Command / Observer | Does the sender **name the receiver**? | yes → Command | no → Observer |
| Command / Strategy (naming) | Is the type name an **imperative verb** or a **past-tense fact**? | imperative → Command | fact → domain event |
| Observer / Mediator | Is there an interaction **rule**, or only a broadcast? | rule → Mediator | broadcast → Observer |
| Facade / Mediator | Is the relationship **bidirectional**? | yes → Mediator | no, one-way → Facade |
| Visitor / Strategy | Does behaviour vary by the **type operated on**? | yes → Visitor | no → Strategy |
| Visitor / Iterator | Is **position** externalised, or the **operation**? | position → Iterator | operation → Visitor |
| Factory method / Abstract factory | One product, or a **consistent family**? | family → Abstract factory | one → Factory method |
| Static factory / Factory method | Is it **overridable**? | no, `static` → Static factory | yes, an instance method → Factory method |
| Abstract factory / Builder | Is the variation **which type**, or **which fields are set**? | which type → Abstract factory | which fields → Builder |
| Builder / Static factory | Are there **≥5 fields or any optional** field? | yes → Builder | no → Static factory |
| Prototype / Memento | Is the copy a **usable object** or an **opaque snapshot**? | usable → Prototype | opaque → Memento |
| Singleton / Flyweight / Pool | **One** instance, **shared immutable** state, or **lent mutable** instances? | one → Singleton | shared → Flyweight; lent → Pool |
| Flyweight / Cache | Is the split **intrinsic vs extrinsic** state, or just **key → value** reuse? | intrinsic/extrinsic → Flyweight | key→value → Cache |
| Template method / Chain of responsibility | Is the sequence **fixed in code and total**? | yes → Template method | configured and abortable → Chain |
| Interpreter / Composite | Is there a **grammar being evaluated**? | yes → Interpreter | just a nested structure → Composite |
| Null object / Optional | Is the caller **allowed to ignore** absence? | yes → Null object | no, must handle it → `Optional` |
| Specification / Strategy | Does it return a **boolean about a candidate**? | yes → Specification | no, it performs work → Strategy |
| DI / Service locator | Does the class **ask** for its collaborator? | yes → Service locator | no, it appears → DI |
| Registry / Singleton | Is the shared thing a **lookup of many**, or **one instance**? | lookup → Registry | one → Singleton |

2.5.3 The pair the table cannot settle, named honestly: **proxy vs decorator when the wrapper is
      hand-written and stacked but also controls access.** GoF's own answer is intent, and intent
      is not observable in the bytecode. Say "structurally identical; I'd call it a decorator
      because the wiring chose it and it always delegates" and move on. `[TRAP] [SAY]`

2.5.4 The second unsettleable pair: **bridge vs strategy in a codebase that grew into two
      hierarchies.** Bridge is a claim about *intent at design time*; if the second hierarchy
      appeared incrementally, it is a strategy that became a bridge, and both names are
      defensible. `[TRAP]`

2.5.5 Why the "one question" format is the deliverable and not a study aid: under interview
      pressure a table of six columns is unrecallable and one question is not. The candidate who
      answers "does it transition itself?" has demonstrably more usable knowledge than one who
      recites both catalogue entries. `[SAY]`

2.5.6 The failure mode this section is defending against, named: answering a disambiguation
      question by reciting **both** definitions and letting the interviewer do the comparison.
      That reads as recall regardless of accuracy. `[TRAP]`

2.5.7 The follow-up every disambiguation answer must survive, so prepare it: **"give me a case
      where you would choose the other one."** A separator you cannot invert is a memorised
      sentence. `[SAY]`

2.5.8 Worked inversion 1 — proxy/decorator: "decorator for the PSP retry because the wiring
      chose it and it must stack under the metrics wrapper; **proxy** if I needed the target
      created lazily or the call suppressed entirely, which is why `@Transactional` is a proxy."
      `[SAY] [BUILD]`

2.5.9 Worked inversion 2 — strategy/state: "strategy for `RestrictionRule` because
      `ClientRestrictions` picks the rule from the requested action; **state** for `PaymentRun`
      because `APPROVED` decides that `SUBMITTED` is the only legal successor." `[SAY] [BUILD]`

2.5.10 Worked inversion 3 — adapter/facade: "adapter for the Identity Vendor because their
       interface is imposed on us and `DocumentVerification` must satisfy an existing port;
       **facade** for `PaymentService` because we invented its interface over five services."
       `[SAY] [BUILD]`

2.5.11 The pairs that carry a **version** answer rather than an intent answer, listed because
       the right response is "neither, in Java 21": visitor/strategy → a sealed interface plus
       exhaustive switch; prototype/memento for a value → a record with `withX`;
       builder/static factory for ≤3 fields → the record's canonical constructor. `[VERSION-TRAP]`

2.5.12 **Trap:** treating a type as implementing exactly one pattern, so the disambiguation
       question is assumed to have a unique answer. `JdbcTemplate` is a facade **and** a
       template method (§1.33.4). The right answer is sometimes "both, and here is which reading
       matters for your question." `[TRAP]`

2.5.13 The three questions that resolve the largest number of pairs, worth memorising as a set
       because they cover most of the table: **(1) is the interface the same as the target's?
       (2) who chooses — the caller, the framework, or the object itself? (3) may the delegate
       be skipped?** `[SAY] [PROVE]`

2.5.14 The fourth question, added because it resolves the creational rows the first three miss:
       **what varies — which type, which fields, or how many instances?** `[SAY]`

2.5.15 How to use the table under pressure, as an ordered procedure: name the force first, then
       ask the one question out loud, then name the pattern, then name the cost. Naming the
       pattern first and justifying afterwards is the recall failure mode. `[FLOW] [SAY]`

2.5.16 The confusable pairs that are **not** patterns at all and must be separated before the
       table is useful: pattern vs idiom (`try-with-resources`), pattern vs principle (DIP),
       pattern vs architectural style (hexagonal), pattern vs anti-pattern (singleton-as-global),
       pattern vs refactoring (Replace Conditional with Polymorphism). Definitions in §1.3.
       `[TABLE]`

2.5.17 The QuizStakes calibration exercise: for each of `PaymentService`, `RetryingPspClient`,
       `@Transactional` on `FundsLedger`, the Identity Vendor wrapper, `RestrictionRule`,
       `PaymentRun`'s status machine, and `ApplicationGateway`'s filter chain — state the
       pattern and the **one question** that got you there. Seven objects, seven questions.
       `[BUILD]`

2.5.18 `[DECIDE]` When the pair genuinely does not matter: if two candidate names describe the
       same code and the same cost, the disambiguation is vocabulary rather than design. Say
       which you would call it, why, and spend the remaining time on the cost — that is where
       the signal is.

*(18 leaves)*

---

### Sources consulted — lane B

| Source (URL) | What it contributed |
|---|---|
| https://martinfowler.com/articles/injection.html | Primary source for §1.32: Fowler's three injection forms by his names, his exact constructor-injection claims ("create valid objects at construction time", hiding immutable fields), the setter-injection case, the "no difference … both are very amenable to stubbing" correction, the "every user of a service has a dependency to the locator" distinction, and his application-code-vs-reusable-component selection criteria. |
| https://raw.githubusercontent.com/apache/tomcat/main/java/org/apache/catalina/core/ApplicationFilterChain.java | Primary source for §1.25.4–§1.25.6: exact field names and types (`ApplicationFilterConfig[] filters`, `int pos`, `int n`, `Servlet servlet`, `public static final int INCREMENT = 10`), the `if (pos < n)` body including `filters[pos++]` and `filter.doFilter(request, response, this)`, `servlet.service(request, response)` as the terminal call, and `addFilter`/`release`. |
| https://docs.spring.io/spring-framework/reference/data-access/transaction/event.html + https://docs.spring.io/spring-framework/docs/current/javadoc-api/org/springframework/transaction/event/TransactionalEventListener.html | §1.23.8–§1.23.9, §1.23.14: the four `TransactionPhase` values, that `BEFORE_COMMIT` failures can prevent the commit while `AFTER_*` cannot, that resources may still be active at `AFTER_COMMIT` so data-access changes are never committed, and that `@TransactionalEventListener` does not dispatch through `ApplicationEventMulticaster`. |
| https://docs.spring.io/spring-framework/reference/core/beans/annotation-config/autowired-qualifiers.html | §1.20.6, §1.20.9: `Map<String, T>` injection keyed by bean name, and `@Qualifier` filtering which beans populate an injected collection. |
| https://www.oreilly.com/library/view/software-architecture-patterns/0642572221119/ch04.html (+ https://candost.blog/notes/45a/, https://www.oreilly.com/content/software-architecture-patterns/) | §1.31.6–§1.31.7, §1.31.11: the **architecture sinkhole anti-pattern** by name, the pass-through-with-no-logic definition, the **80/20 rule** threshold, closed vs open layers, and Richards & Ford's "layered is the right choice for small simple applications and tight budget/time constraints, particularly as a starting point". |
| https://openjdk.org/jeps/441 (+ https://openjdk.org/jeps/433) | §1.26.8–§1.26.9: pattern matching for `switch` finalised in Java 21, exhaustiveness derived from a sealed type's `permits` clause, and the JEP's own statement that without pattern matching such calculations require "the cumbersome visitor pattern". |
| https://www.baeldung.com/spring-framework-design-patterns | §1.21.14, §1.33 census: `JdbcTemplate` with `ResultSetExtractor<T>`, `RowMapper<T>`, `RowMapperResultSetExtractor`; `TransactionTemplate`; `BeanFactory.getBean` overloads; `ApplicationContext` implementations; `EnhancerBySpringCGLIB` naming. |
| https://en.wikipedia.org/wiki/Lapsed_listener_problem | §1.23.12: the **lapsed listener problem** as the canonical name for the observer leak — a leaf I would not have written without the research pass. |
| https://martinfowler.com/eaaCatalog/dataTransferObject.html (+ https://en.wikipedia.org/wiki/Data_transfer_object) | §1.29.13: DTO as "an object that carries data between processes" with no business logic, and the **assembler** as its server-side mapping partner. |
| https://github.com/masoud-bahrami/Specification-Pattern-Samples (+ https://grokipedia.com/page/Specification_pattern, https://enterprisecraftsmanship.com/posts/specification-pattern-always-valid-domain-model/) | §1.29.6–§1.29.8: the Evans/Fowler *Specifications* paper's three uses (validation, selection, building to order), boolean composition, and the hard-coded / parameterised / composite forms. |
| https://javarevisited.blogspot.com/2014/04/difference-between-state-and-strategy-design-pattern-java.html + https://www.oreilly.com/library/view/c-30-design/9780596527730/ch07s04.html | §2.4.5, §2.4.7: the widely-repeated "stateless vs stateful" strategy/state separator (recorded so §2.4.5 can correct it) and the "strategy varies the whole algorithm, template varies parts" formulation. |

**Fetches that failed, stated rather than silently dropped:**

- `https://stackoverflow.com/questions/1673841/examples-of-gof-design-patterns-in-javas-core-libraries` — the canonical crowd-sourced JDK pattern census. **Blocked** ("Claude Code is unable to fetch from stackoverflow.com"). The §1.33 JDK column was assembled from the Spring/JEP/Tomcat primary sources above plus my own knowledge of the JDK types, which is why §1.33.10 flags the pattern *readings* as community consensus rather than vendor claims.
- `https://martinfowler.com/apsupp/spec.pdf` — the Evans/Fowler *Specifications* paper itself. Fetched but returned unparseable binary PDF content. §1.29.7's `remainderUnsatisfiedBy` / `asQuery` / `subsumes` operation names therefore come from secondary sources and are tagged `[RESEARCH]` for re-verification against the PDF at write time.
- `http://sys0x.fit.subjects.gitlab.io/.../5.%20Non%20GoF%20design%20patterns/` — a curriculum page enumerating non-GoF patterns, intended as a completeness probe for §1.29. **TLS certificate hostname mismatch**; not fetched. §1.29's inventory follows the BRIEF's own list plus PoEAA base patterns.

### Gaps vs the current guide — lane B

| Syllabus leaf | In `src/topics/24-…` | Verdict |
|---|---|---|
| §1.20.1–§1.20.5 | lines 365–390, § 4.1 with the `Map<String, ScoringStrategy>` code | covered |
| §1.20.7 | line 394, one clause ("bean names are refactoring-fragile and not domain values") | shallow |
| §1.20.8 (the `type`+`source` pair as the real key) | absent | **missing** |
| §1.20.10–§1.20.11 | lines 396–401, the "Strategy relocates the switch" trap | covered |
| §1.20.12 (startup assertion moving the failure compile→startup) | line 973, one clause inside § 10's worked answer | shallow |
| §1.20.13–§1.20.14 (megamorphic degradation; the 30 ms budget arithmetic) | absent | **missing** |
| §1.20.16 (the explicit "do not use strategy when") | line 36, one clause | shallow |
| §1.20.17 (testability consequence) | absent | **missing** |
| §1.20.18 (JDK strategies by name) | absent | **missing** |
| §1.21.4 | line 408, one sentence ("the `final` is load-bearing") | covered |
| §1.21.5 (`final` template method + CGLIB = silent no-op) | absent | **missing** |
| §1.21.6–§1.21.7 (`public` hooks; hooks that do real work) | absent | **missing** |
| §1.21.10 | line 425, table row "Multiple varying steps" | covered |
| §1.21.12 (lambda as the modern replacement) | absent | **missing** |
| §1.21.14 (JDK/Spring template methods by name) | absent | **missing** |
| §1.22.3 | line 429, "State vs strategy is the sharpest distinction" | covered |
| §1.22.5 (2⁴ = 16 combinations, ~6 legal) | line 438, stated as "16 representable … maybe 6 legal" | covered |
| §1.22.8 (the `XX-Nnn` disposition digit as encoded state design) | absent | **missing** |
| §1.22.10–§1.22.11 | lines 454–456 | covered |
| §1.22.12 (`reversibleByOperator = false` as data, not convention) | absent | **missing** |
| §1.22.14 (restrictions as a *set*, not a state machine) | absent | **missing** |
| §1.22.15 (table-driven transition test) | absent | **missing** |
| §1.23.6–§1.23.11 (the four observer failure modes) | lines 466–478, all four present | covered |
| §1.23.8 (`BEFORE_COMMIT` can block the commit; `AFTER_*` cannot) | absent — the guide states the rollback coupling but not the phase that governs it | **missing** |
| §1.23.9 (`AFTER_COMMIT` data access participates but never commits) | absent | **missing** |
| §1.23.12 (the *lapsed listener problem* by name) | line 477, described but unnamed | shallow |
| §1.23.14 (`@TransactionalEventListener` bypasses the multicaster) | absent | **missing** |
| §1.23.15 | lines 484–486 | covered |
| §1.23.18 (listener order unspecified without `@Order`) | absent | **missing** |
| §1.23.20 (`Observable` deprecated in Java 9) | absent | **missing** |
| §1.24.1–§1.24.7 | lines 488–499, § 4.5 | covered |
| §1.24.6 (command as the carrier of the operator + role used) | absent | **missing** |
| §1.24.11 (undo is not a mechanical inverse — the win/void asymmetry) | absent from § 4.5; the asymmetry itself is in scenario §11.3 | **missing** |
| §1.24.12 (a persisted command's class name is a schema) | absent | **missing** |
| §1.25.3–§1.25.7 | lines 504–512 | covered |
| §1.25.4–§1.25.6 (`pos`, `n`, `INCREMENT`, `filters[pos++]`, `servlet.service`) | absent — the guide names the pattern, not the source | **missing** |
| §1.25.9 (`FilterChainProxy`, `HandlerExecutionChain`, `ReflectiveMethodInvocation.proceed()`) | absent | **missing** |
| §1.25.10 (`ClassLoader` / `Logger` parent delegation as chains) | absent | **missing** |
| §1.25.11 | lines 514–515 | covered |
| §1.25.12–§1.25.13 (ordering incident; double `doFilter`) | absent | **missing** |
| §1.26.2–§1.26.6 | lines 517–533 | covered |
| §1.26.7 (a `default` visit method makes a new type silently unvisited) | absent | **missing** |
| §1.26.9 (JEP 409 / JEP 441 version facts) | absent | **missing** |
| §1.26.14 (same-module restriction closes the type set) | absent | **missing** |
| §1.26.16 (`FileVisitor`, `ElementVisitor`, `BeanDefinitionVisitor`) | absent | **missing** |
| §1.27.5–§1.27.6 | line 552, one clause on `modCount` and "best-effort bug detector" | shallow |
| §1.27.7 (absence of CME proves nothing) | absent | **missing** |
| §1.27.9 (weakly-consistent iterators as a *different* contract) | absent | **missing** |
| §1.27.11–§1.27.12 (`CloseableIterator`, `Spliterator` characteristics) | absent | **missing** |
| §1.28.1–§1.28.3 | lines 556–558 | covered |
| §1.28.5 (segregation of duties as the mediator's rule) | absent | **missing** |
| §1.28.9 (the wide/narrow interface asymmetry *is* memento) | absent — line 559 says "opaque snapshot only it can interpret" | shallow |
| §1.28.11 (Spring Batch `ExecutionContext`) | absent | **missing** |
| §1.28.12 (a memento holding mutable references) | absent | **missing** |
| §1.28.14–§1.28.16 | lines 563–567 | covered |
| §1.29.2–§1.29.5 (null object) | absent entirely | **missing** |
| §1.29.6–§1.29.11 (specification) | absent entirely | **missing** |
| §1.29.12 | line 814, § 7.4 value object | covered |
| §1.29.13–§1.29.15 (DTO, assembler, DTO-as-entity trap) | absent | **missing** |
| §1.29.16–§1.29.20 (registry, servant, marker, monostate, module) | absent | **missing** |
| §1.29.21–§1.29.23 (`try-with-resources` as the RAII equivalent, suppressed exceptions) | absent | **missing** |
| §1.30.2–§1.30.11 | lines 573–632, § 5.1–5.5 — present but at depth, not at vocabulary level | covered (this lane states them as one-line mechanisms; §2.6–§2.10 own the depth) |
| §1.30.6 (`List.of` / `Arrays.asList` as the LSP example) | line 598 | covered |
| §1.30.9 (`default` methods soften the interface owner's OCP problem) | line 614 | covered |
| §1.31.1–§1.31.3 | lines 756–765, § 7.1 | covered |
| §1.31.4 (layered as the *correct default*, with the source) | line 789, one clause ("for a CRUD service … layered is the correct, cheaper answer") | shallow |
| §1.31.6–§1.31.7 (**architecture sinkhole**; the 80/20 threshold) | absent | **missing** |
| §1.31.11 (closed vs open layers) | absent | **missing** |
| §1.31.13 (the upgrade-trigger sentence) | line 991, generic version | shallow |
| §1.32.1 (IoC ≠ DI) | absent | **missing** |
| §1.32.3–§1.32.6 (Fowler's three forms, in his words) | absent | **missing** |
| §1.32.7–§1.32.9 (field injection: no `final`, hides god object, hides cycles) | line 717, one clause ("field injection hides it") | shallow |
| §1.32.10 (DI does not require a container) | absent | **missing** |
| §1.32.13–§1.32.16 (service locator, and Fowler's own correction) | absent | **missing** |
| §1.32.18 (do not inject when) | absent | **missing** |
| §1.33 (the 23 × 3 census) | scattered — flyweights at 352–356, proxies at 297–301, `Map<String,T>` at 375–389; no census table | **missing as a table** |
| §1.33.4–§1.33.5 (types implementing two patterns) | absent | **missing** |
| §1.33.8 (which patterns Java 21 reshaped, as a set) | partially — records/builder at 122–126, visitor at 531 | shallow |
| §2.1.3 (the master force → pattern → seam → cost table) | absent — § 10 gives the four-part *answer shape* at lines 966–974 but no table | **missing** |
| §2.1.5–§2.1.6 (the cost taxonomy; the compile/startup/request axis) | line 983, one clause in the trade-off vocabulary list | shallow |
| §2.1.8–§2.1.9 | lines 43–45, § 1's rule of three | covered |
| §2.1.12 (rejection templates) | lines 976–981 | covered |
| §2.1.14–§2.1.16 | lines 33–41, the two § 1 traps | covered |
| §2.2.2–§2.2.14 (the seven-step creational procedure) | ingredients present across § 2.1–2.5; the *procedure* absent | **missing as a procedure** |
| §2.2.5 (2⁶ = 64 telescoping overloads) | line 99, stated as "a constructor with 9 parameters is unreadable" without the arithmetic | shallow |
| §2.3.2 | lines 254–259, the four-way table | covered |
| §2.3.3–§2.3.8 | lines 261–270, the three discriminators | covered |
| §2.3.11–§2.3.15 (composite/decorator, bridge/strategy, facade/mediator, flyweight/singleton/pool) | bridge/strategy at line 342; the rest absent | shallow |
| §2.4.2 (the five-way behavioural table) | lines 423–427, three-way only (template/strategy/state) | shallow |
| §2.4.5 (correcting the "stateless vs stateful" separator) | absent | **missing** |
| §2.4.8–§2.4.10 (strategy/command; command/observer; the naming rule) | absent | **missing** |
| §2.4.12–§2.4.16 (visitor/iterator, chain/strategy, mediator/observer, memento/prototype, template/chain) | absent | **missing** |
| §2.4.17 (the ordered behavioural decision flow) | absent | **missing** |
| §2.5.2 (the 29-row confusable-pairs table with one question each) | absent — individual discriminators exist at 261–270 and 429–431 | **missing** |
| §2.5.3–§2.5.4 (the pairs that genuinely cannot be settled) | line 285, one clause | shallow |
| §2.5.7–§2.5.10 (the inversion follow-up and three worked inversions) | absent | **missing** |
| §2.5.13–§2.5.14 (the three/four questions that resolve most of the table) | absent | **missing** |

Count: 62 leaves or leaf-groups marked **missing**, 17 **shallow**, 24 **covered**. Every
`**Trap:**` marker in the guide's §§ 4.1–4.8, 5.1–5.5 and 7.1 that falls in this lane's scope is
carried forward — §1.20.10, §1.20.11, §1.21.6, §1.22.10, §1.23.15, §1.25.11, §1.26.7, §1.27.6,
§1.28.3, §1.28.12, §1.30.6, §1.31.8, §2.1.14, §2.1.15, §2.3.9, §2.3.10, §2.4.5, §2.5.3, §2.5.6,
§2.5.12. Atomic-checklist items in this lane's scope (guide lines 1022–1034, 1045 partial, plus
1023–1025) each map to at least one leaf: 1022→§1.20.5/§1.20.7, 1023→§1.20.10/§1.20.11,
1024→§1.21.4, 1025→§1.22.3/§2.4.4, 1026→§1.22.5/§1.22.11, 1027→§1.23.6–§1.23.11,
1028→§1.23.13/§1.23.15, 1029→§1.24.4, 1030→§1.25.3/§1.25.7, 1031→§1.26.3/§1.26.6,
1032→§1.26.8, 1033→§1.27.5/§1.27.6, 1034→§1.28.1–§1.28.3, 1045→§1.31.10.

### Notes for the orchestrator — lane B

**Leaf counts per section, and the arithmetic.**

| Section | Leaves |
|---|---|
| §1.20 Strategy | 18 |
| §1.21 Template method | 14 |
| §1.22 State | 15 |
| §1.23 Observer | 20 |
| §1.24 Command | 13 |
| §1.25 Chain of responsibility | 15 |
| §1.26 Visitor and double dispatch | 17 |
| §1.27 Iterator | 13 |
| §1.28 Mediator, memento, interpreter | 16 |
| §1.29 The non-GoF vocabulary | 23 |
| §1.30 SOLID at vocabulary level | 11 |
| §1.31 Layered architecture | 13 |
| §1.32 DI and IoC | 18 |
| §1.33 The pattern census | 10 |
| **PART 1 subtotal (§1.20–§1.33)** | **216** |
| §2.1 Master pattern-selection table | 16 |
| §2.2 Creational decision procedure | 14 |
| §2.3 Structural intent disambiguation | 16 |
| §2.4 Behavioural disambiguation | 18 |
| §2.5 The confusable pairs | 18 |
| **PART 2 subtotal (§2.1–§2.5)** | **82** |
| **Lane B total** | **298** |

Arithmetic: 18+14+15+20+13+15+17+13+16+23+11+13+18+10 = **216** for Part 1 (brief target ≈190,
so +13.7%, inside the ±15% band). 16+14+16+18+18 = **82** for Part 2 (brief target ≈80, +2.5%).
216 + 82 = **298** against a lane target of ≈270, i.e. **+10.4%** — inside ±15%. Counts were
verified on disk by counting lines matching `^[0-9]+\.[0-9]+\.[0-9]+ ` per section, not estimated.

Three sections exceed the brief's soft 25-leaf ceiling? No — the largest is §1.29 at 23. Three
sections sit at 10–11 (§1.33, §1.30), below the "almost certainly under-enumerated" threshold of
8 but close to it; both are deliberate. §1.33 is 10 leaves **plus a 23-row table**, so its real
content is ~33 named mappings; §1.30 is intentionally thin because §2.6–§2.10 (lane C) own SOLID
in depth and duplicating it here would create exactly the redundancy the brief warns about.

**Tag counts for the lane** (occurrences of each tag across all 298 leaves; a leaf may carry
several):

| Tag | Count |
|---|---|
| `[PROVE]` | 78 |
| `[API]` | 54 |
| `[SAY]` | 53 |
| `[DECIDE]` | 52 |
| `[TRAP]` | 46 |
| `[RESEARCH]` | 32 |
| `[NUM]` | 25 |
| `[BUILD]` | 24 |
| `[X-REF nn]` | 22 |
| `[SMELL]` | 16 |
| `[TABLE]` | 14 |
| `[VERSION-TRAP]` | 12 |
| `[FLOW]` | 9 |
| `[SOURCE]` | 6 |
| `[INCIDENT]` | 4 |
| `[DIAG]` | 0 |
| **Total tag occurrences** | **447** |

Counted on disk over the leaf region only (everything above `### Sources consulted`), so the tag
names appearing in this notes block are excluded. `[VERSION-TRAP]` is counted separately from
`[TRAP]` — the two are disjoint. Average 1.5 tags per leaf.

All 22 `[X-REF nn]` tags are genuine **sibling-guide** pointers (16×6, 06×5, 05×4, 08×2, 04×2,
20×1, 14×1, 07×1); there are **no intra-guide `[X-REF 24]` tags**, per the cross-lane convention
that an intra-guide pointer is a bare inline `(§N.M)`. Every leaf in the lane carries at least one
tag.

History: §2.5.16 was retagged `[X-REF 24]` → `[TABLE]` during the cross-lane `[X-REF]` sweep — its
text already named §1.3 inline so no parenthetical was needed, and `[TABLE]` is what the leaf
actually obliges (five parallel category/example pairs is a ≥3-item comparison).

`[DIAG]` is zero for this lane by design: it demands a real artefact (a decompiled proxy, an
ArchUnit failure report, a stack trace) and every such artefact in this topic belongs to
PART 3 (§3.7, §3.8, §3.13, §3.19, §3.20) or PART 4. A basics-tier leaf that promised a decompiled
class would duplicate lane E. `[INCIDENT]` is low (4) for the same reason — §3.22 owns the
postmortems; the four here are the ones whose *design* lesson is inseparable from the failure
(§1.23.6 latency coupling, §1.23.7 rollback coupling, §1.25.12 filter ordering,
§1.29.23 document-buffer OOM).

**Anything I could not verify, named, with the constant and the source that would settle it.**

1. **`ApplicationFilterChain.internalDoFilter` does not exist in current Tomcat.** Multiple
   secondary sources (and stack traces in the wild) reference
   `ApplicationFilterChain.internalDoFilter(ApplicationFilterChain.java:269)`, but the current
   `main` source I fetched has only `doFilter`. It appears the private method was inlined at some
   point. §1.25.4 therefore names only `doFilter`, `addFilter` and `release`. **What would settle
   it:** the Tomcat 9.0.x source tag, where `internalDoFilter` was present, versus 10.1.x/11.x.
   If the write pass wants to name it, it must state the Tomcat version.
2. **`INCREMENT = 10`** is confirmed as `public static final int` in the fetched source, but its
   *semantics* (the array-growth step in `addFilter`) I did not read the body of. Tagged `[API]`,
   not `[NUM]`, for that reason.
3. **The Evans/Fowler specification operation names** — `remainderUnsatisfiedBy`, `asQuery`,
   `subsumes`, and whether the paper says "building to order" or "generation" — come from
   secondary sources because `martinfowler.com/apsupp/spec.pdf` returned unparseable binary.
   §1.29.7 carries `[RESEARCH]`. **What would settle it:** the PDF itself, read as text.
4. **`IntegerCache` bounds in §1.33's flyweight row** are stated as −128..127, which is the
   documented default, but the **upper** bound is settable via
   `-XX:AutoBoxCacheMax=<high>` / `java.lang.Integer.IntegerCache.high`. Lane A owns §1.19
   (flyweight) and lane E owns §3.x; I have not duplicated the property name there. Flagging it so
   whichever lane owns the constant states the tunability rather than the bare 127.
5. **Whether `Observable`/`Observer` were removed** (not merely deprecated) in any current JDK.
   §1.23.20 and §1.33's row 19 say "deprecated since Java 9", which I am confident of; I did not
   verify against a JDK 25 API diff whether they are now marked for removal.
   **What would settle it:** the `java.util.Observable` javadoc for the JDK 25 API.
6. **Spring's flyweight cell is marked "absent"** — a judgement, not a verified fact. Spring's
   `ConcurrentReferenceHashMap`-backed annotation metadata caches are *caching*, not an
   intrinsic/extrinsic state split, which is why I called it absent. If the orchestrator prefers a
   populated cell, `org.springframework.core.annotation.AnnotationUtils`' caches are the closest
   candidate and the row should say "caching, not flyweight" rather than a bare type name.
7. **The 11-receiver-type megamorphic claim in §1.20.13.** The JIT's megamorphic threshold is a
   HotSpot implementation detail (the virtual-call inline cache degrades past **2** receiver
   types, and `-XX:TypeProfileWidth` defaults to 2), so "past bimorphic" is right and "11 types"
   is the count of §9.3's catalog rows, not a JIT constant. §3.1 (lane E) owns the constant; I
   have deliberately not stated a threshold number here.

**Anything I judged out of this topic's scope, and where I sent it.**

- Observer's `ApplicationEventMulticaster` internals, the `TransactionSynchronization` registration
  path, the listener-leak heap analysis, and the `ConcurrentModificationException` site → **§3.19**,
  cross-referenced from §1.23.4, §1.23.13 and §1.23.14. Lane B states the mechanism in one leaf and
  points.
- Inline-cache degradation, `TypeProfileWidth`, and the measured cost of a strategy interface →
  **§3.1** (lane E), cross-referenced from §1.20.13. See note 7 above.
- Iterator allocation being scalar-replaced → **§3.2**, cross-referenced from §1.27.13.
- `PermittedSubclasses`, the `typeSwitch` bootstrap and `MatchException` → **§3.13**,
  cross-referenced from §1.26.10.
- The `final`-method/CGLIB interaction and the self-invocation bypass → **§3.8** (guide `07`),
  cross-referenced from §1.21.5.
- Outbox mechanics, saga transport and delivery semantics → **§2.25**/**§3.17** and guide `14`,
  cross-referenced from §1.23.13 and §1.23.16.
- Snapshotting, upcasting and version-based optimistic concurrency → **§3.16**/**§3.18** and guide
  `08`, cross-referenced from §1.28.10.
- Aggregate boundary rules → **§2.22** (lane D), cross-referenced from §1.22.11.
- Package-by-layer vs by-feature in depth, and layered-vs-hexagonal-vs-clean as a fitness
  comparison → **§2.17**/**§2.19** (lane D), cross-referenced from §1.31.9 and §1.31.13. §1.31
  deliberately stops at "layered is the default, here is the symptom it stopped being one".
- SOLID in depth, GRASP, connascence, and the anti-pattern catalogue → **§2.6–§2.14** (lane C),
  cross-referenced from §1.30. §1.30 is vocabulary only, by the brief's own split.
- Test doubles per pattern → **§2.28** (lane D) and guide `16`, cross-referenced from §1.20.17,
  §1.21.13, §1.22.15, §1.26.17, §1.31.12 and §1.32.11.
- ArchUnit rules, JPMS enforcement and fitness functions → **§2.29**/**§3.20**, cross-referenced
  from §1.29.20.

**One format note the orchestrator should know:** §1.33 and §2.1–§2.5 each carry a large table
*inside* a leaf (§1.33.2, §2.1.3, §2.3.2, §2.4.2, §2.5.2). The table is the leaf's content, per
the `[TABLE]` tag, and is **not** counted as additional leaves. If the totals table wants a
"named mappings" figure separate from the leaf count, those five tables contribute 23 + 27 + 4 +
5 + 29 = **88** table rows on top of the 298 leaves.
