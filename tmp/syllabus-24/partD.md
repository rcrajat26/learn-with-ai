## §2.15 The code-smell catalogue — Fowler *Refactoring* 2e, all twenty-four, each with its smallest safe move

2.15.1 The census claim to state before the list: *Refactoring* 2e chapter 3 "Bad Smells in Code" carries
      **24 smells**, in book order, and the 2e list is not the 1e list. Enumerate in book order so the
      reader can check off against the book. `[RESEARCH]` `[SOURCE]`
2.15.2 **Mysterious Name** — new in 2e, and Fowler puts it first deliberately. `ClientRestrictions.check()`
      that returns a `boolean` naming neither the action nor the polarity. Smallest move: *Rename Variable /
      Rename Field / Change Function Declaration* → `isBlockedFor(clientId, DEPOSIT)`. Test: none needed —
      a pure rename is compiler-verified, which is why it is the cheapest refactoring in the catalogue. `[SMELL]`
2.15.3 **Duplicated Code** — the same `SUSPENSE → CLIENT_CASH_AVAILABLE` matching arithmetic in
      `BankDeposits` and in the reconciliation job. Smallest move: *Extract Function*; if the duplicates sit
      in sibling subclasses, *Pull Up Method*; if they are structurally similar but not identical,
      *Slide Statements* first to align them, then extract. Test: a parameterised test over both call sites
      asserting identical output before the extraction. `[SMELL]`
2.15.4 **Long Function** — 2e renames 1e's *Long Method* because the book's examples are JavaScript
      functions. The 400-line `@Transactional` `settleStake` with nested `if`s over a status string.
      Smallest move: *Extract Function* per named intention; *Replace Temp with Query*; *Split Loop* before
      extracting so each extracted function does one thing. Test: existing behaviour test at the outer
      transactional boundary. `[SMELL]`
2.15.5 **Long Parameter List** — `reserveStake(clientId, amount, currency, bonusEligible, roundId,
      idempotencyKey, requestedAt, source, correlationId)`. Smallest move: *Introduce Parameter Object* →
      `record StakeReservationCommand(...)`; *Replace Parameter with Query* for anything derivable;
      *Preserve Whole Object* when the caller already holds the aggregate. Test: keep the old signature
      delegating to the new one so existing tests are untouched. `[SMELL]`
2.15.6 **Global Data** — new in 2e. A `static` mutable `Map<String, RestrictionType>` cache in
      `ClientRestrictions`, mutated at startup and read on the 30 ms money path. Smallest move:
      *Encapsulate Variable* — wrap in a getter/setter pair so every access is interceptable, then narrow
      the setter to zero callers and make the field `final`. Test: a test that mutates the global and
      asserts a second test still sees the pristine value (proves the order-dependence). `[SMELL]`
2.15.7 **Mutable Data** — new in 2e. A `WalletSnapshot` handed out of `BalanceView` with public setters,
      so a display caller can silently change what another caller reads. Smallest move: *Encapsulate
      Variable*, then *Replace Derived Variable with Query* for `stakeable`/`withdrawable` (which §11.1 of
      the scenario says are never stored), then convert to a `record`. Test: a test that mutates the
      returned object and asserts the source is unchanged. `[SMELL]`
2.15.8 **Divergent Change** — one class changed for two unrelated reasons. `PaymentService` changed both
      when a new rail arrives and when the AML pattern rules change. Smallest move: *Split Phase*, then
      *Extract Class* along the two reasons. Test: the two teams' test suites now live in separate files —
      that file split *is* the observable outcome. (§2.6) `[SMELL]`
2.15.9 **Shotgun Surgery** — the inverse: one change touches many classes. Adding one field to the
      onboarding capture touches controller, DTO, mapper, entity, migration, projection. Smallest move:
      *Move Function* / *Move Field* to pull the scattered parts together; *Combine Functions into Class*.
      Test: measure it — count files touched per feature commit before and after (`[NUM]` change
      amplification). `[SMELL]`
2.15.10 **Feature Envy** — a method in `PaymentService` that reads five fields off `Wallet` and one of its
      own. Smallest move: *Move Function* onto `Wallet`; if only part of it envies, *Extract Function*
      first, then move the extracted part. Test: the moved method's unit test needs no `PaymentService`
      instance — that is the proof the boundary was wrong. `[SMELL]`
2.15.11 **Data Clumps** — `(cashAmount, bonusAmount)` travelling together through six signatures because
      §11.3's win/void asymmetry needs both. Smallest move: *Extract Class* → `record StakeSplit(Money
      cash, Money bonus)`, then *Introduce Parameter Object* at the call sites. Test: an invariant test on
      the new type (`cash.plus(bonus).equals(stakeTotal)`) that had nowhere to live before. `[SMELL]`
2.15.12 **Primitive Obsession** — `String clientId, String currency, BigDecimal amount`. Smallest move:
      *Replace Primitive with Object* → `record ClientId(String value)` with validation in the compact
      constructor. Test: a compile-time test — the transposition `reserve(accountId, clientId)` stops
      compiling, which is a stronger guarantee than any assertion. (§1.29) `[SMELL]`
2.15.13 **Repeated Switches** — 2e renames 1e's *Switch Statements*, and the rename carries the meaning:
      one switch is fine, the *same* switch appearing in three places is the smell. `switch (restriction
      .source())` in the apply path, the lift path and the display path. Smallest move: *Replace Conditional
      with Polymorphism*, or a `sealed interface` + exhaustive switch if the set is closed. Test: a
      parameterised test over every enum constant asserting old and new agree. `[SMELL]`
2.15.14 **Loops** — new in 2e. An explicit `for` over `List<LedgerEntry>` accumulating four position
      totals. Smallest move: *Replace Loop with Pipeline* (`Collectors.groupingBy(LedgerEntry::position,
      reducing(...))`). Test: a golden-master test over a real day's 19.8M-row sample reduced to a fixture.
      `[SMELL]` `[VERSION-TRAP]` — this smell only exists because 2e assumes first-class collection
      pipelines; in Java it arrived with streams in 8, and a `for` loop is still faster for a 3-element list.
2.15.15 **Lazy Element** — 2e renames 1e's *Lazy Class* and widens it to functions too: a class or function
      that no longer earns its own existence. A `StakeAmountValidator` with one method that has one caller.
      Smallest move: *Inline Function*, *Inline Class*, *Collapse Hierarchy*. Test: existing tests move to
      the host and stay green. `[SMELL]`
2.15.16 **Speculative Generality** — `interface PayoutGateway` with one implementation and no second on the
      roadmap; an abstract `AbstractRestrictionRule` with one subclass. Smallest move: *Collapse Hierarchy*,
      *Inline Function*, *Remove Dead Code*, *Change Function Declaration* to drop unused parameters. Test:
      deletion is the test — if nothing breaks, the generality was speculative. `[SMELL]`
2.15.17 **Temporary Field** — a field on `PaymentRun` set only during file generation and null the rest of
      the time, so every reader must null-check. Smallest move: *Extract Class* for the transient cluster,
      then *Introduce Special Case* (null object) if callers still branch on absence. Test: a test
      constructing the object outside the file-generation path and asserting no `NullPointerException`. `[SMELL]`
2.15.18 **Message Chains** — `application.getClient().getAccount().getWallet().getCashAvailable()`.
      Smallest move: *Hide Delegate* — add `application.cashAvailable()` — and only then *Extract Function*
      + *Move Function* to push the behaviour to the owner. Test: an outer-boundary behaviour test; the
      chain's removal must not change output. (§2.11) `[SMELL]`
2.15.19 **Middle Man** — the opposite failure: a class that delegates *everything*. A `WalletFacade` whose
      every method is a one-line forward to `FundsLedger`. Smallest move: *Remove Middle Man* — let callers
      talk to the delegate; *Inline Function*; *Replace Superclass with Delegate* if the middle man arose
      from inheritance. Test: the call-site diff is mechanical; existing tests unchanged. `[SMELL]`
2.15.20 **Insider Trading** — 2e renames 1e's *Inappropriate Intimacy*. `BonusService` reaching into
      `FundsLedger`'s position rows to compute a bonus split, which §4.5 of the scenario forbids ("bonus
      balances — those are ledger positions"). Smallest move: *Move Function* / *Move Field* to put the
      logic on the owner; *Hide Delegate*; if two modules genuinely need shared knowledge, *Extract Class*
      into a third module both depend on. Test: an ArchUnit rule forbidding the package dependency
      (§2.29). `[SMELL]`
2.15.21 **Large Class** — the god object at class scale: `ClientRestrictions` service at 3,000 lines with
      40 injected dependencies. Smallest move: *Extract Class* along the field clusters (fields used
      together belong together), *Extract Superclass*, *Replace Type Code with Subclasses*. Test:
      dependency count in the constructor signature is the metric; assert it in an ArchUnit rule. `[SMELL]`
2.15.22 **Alternative Classes with Different Interfaces** — `CardWithdrawal` and `BankWithdrawal` share the
      state vocabulary of §12.4 but expose `submit()` vs `queueForRun()`. Smallest move: *Change Function
      Declaration* to align signatures, *Move Function* to level the surfaces, then *Extract Superclass*
      or a common interface. Test: one parameterised test suite run against both implementations — the
      shared suite *is* the contract. `[SMELL]`
2.15.23 **Data Class** — a class that is nothing but fields and accessors, with all behaviour elsewhere.
      Smallest move: *Encapsulate Record*, *Remove Setting Method*, then *Move Function* to pull behaviour
      in; if it genuinely has no behaviour, make it a `record` and stop apologising. Test: a test asserting
      an illegal field combination now throws at construction. (§6.2, anemic model) `[SMELL]`
2.15.24 **Refused Bequest** — a subclass that inherits methods it does not want. `SelfExclusionRestriction
      extends Restriction` inheriting `liftByOperator()` and throwing. Smallest move: *Push Down Method* /
      *Push Down Field* to move the unwanted parts to the siblings that need them; *Replace Subclass with
      Delegate*; *Replace Superclass with Delegate*. Test: an LSP test — a parameterised suite over every
      subtype calling every supertype method, asserting no `UnsupportedOperationException`. (§2.8) `[SMELL]`
2.15.25 **Comments** — the smell is a comment used as deodorant for code that should have said it itself.
      Smallest move: *Extract Function* with the comment as its name, *Change Function Declaration*,
      *Introduce Assertion* when the comment states a precondition. Test: the assertion introduced by
      *Introduce Assertion* is the test, promoted into production code. `[SMELL]`
2.15.26 The 1e→2e rename table, because interview material still quotes 1e names: *Long Method* →
      **Long Function**; *Lazy Class* → **Lazy Element**; *Inappropriate Intimacy* → **Insider Trading**;
      *Switch Statements* → **Repeated Switches**. Quoting the 1e name is not wrong, but knowing both
      signals which edition you read. `[VERSION-TRAP]` `[TABLE]`
2.15.27 The two smells **dropped in 2e**: *Parallel Inheritance Hierarchies* (a special case of Shotgun
      Surgery) and *Incomplete Library Class* (superseded by the ubiquity of wrapping/adapters). Name them
      because older curricula still test them, and say why each was folded away. `[RESEARCH]`
2.15.28 The four smells **added in 2e**: Mysterious Name, Global Data, Mutable Data, Loops. Three of the
      four are about *state and naming* rather than structure — the edition's centre of gravity moved from
      class-shape smells to data-flow smells. `[RESEARCH]`
2.15.29 Smells named by other catalogues that are worth carrying even though they are not Fowler's:
      *Bumpy Road* and *Deep Nesting* (CodeScene), *Tramp Data* (a parameter threaded through frames that
      do not use it), *Indecent Exposure*, *Inappropriate Static*, *Special Case*, *Hidden Dependencies*
      (a constructor that reaches for a global instead of receiving it), *Variable with Long Scope*,
      *Paragraph of Code*. `[RESEARCH]`
2.15.30 **Trap:** a smell is a *hint to look*, not a defect. Fowler's own framing — "no set of metrics
      rivals informed human intuition" — means a smell list used as a lint config produces churn without
      value. The decision rule: refactor a smell when it sits on the path of the change you are about to
      make, never as a standalone ticket. `[TRAP]` `[DECIDE]`

*(30 leaves)*

## §2.16 The refactoring catalogue — the moves that produce patterns, and the moves that remove them

2.16.1 The framing leaf: a design pattern is a *destination*, and Fowler's catalogue is the set of legal
      *edges* to it. Naming the move, not the pattern, is what separates "I would use Strategy" from
      "I would *Replace Conditional with Polymorphism* here, in three commits". `[SAY]`
2.16.2 **Replace Conditional with Polymorphism** → produces Strategy or State. `switch (restriction
      .source())` becomes one class per `SYSTEM_ONBOARDING` / `SYSTEM_COMPLIANCE` / `ADMIN` / `CLIENT` /
      `SYSTEM_LIFECYCLE`. Cost it buys: the unknown-key error moves from compile time to runtime (§2.1). `[API]`
2.16.3 **Replace Type Code with Subclasses** → produces the polymorphic hierarchy the previous move needs.
      The `RestrictionType` string column becomes a type. Precondition: the type code must be immutable for
      the object's life — if a restriction can change source, this move is illegal and *Replace Type Code
      with State/Strategy* (a delegate holding the varying part) is the correct one. `[DECIDE]`
2.16.4 **Replace Constructor with Factory Function** → produces Static Factory Method (§1.6) and is the
      prerequisite for Factory Method (§1.7): you cannot return a subtype or a cached instance until
      construction has a name. `Money.ofMinor(1250)` vs `new Money(...)`. `[API]`
2.16.5 **Replace Subclass with Delegate** → *de-patterns* inheritance into composition and is the exit from
      Refused Bequest (§2.15.24) and fragile base class (§2.11). `SelfExclusionRestriction extends
      Restriction` becomes `Restriction` holding a `ReversibilityPolicy`. `[API]`
2.16.6 **Replace Superclass with Delegate** → 1e called this *Replace Inheritance with Delegation*. Applies
      when the superclass was chosen for reuse rather than for `is-a`: a `BatchJob` extending
      `ScheduledTask` because it wanted the retry helper. `[VERSION-TRAP]`
2.16.7 **Introduce Parameter Object** → produces the Command object (§1.24) and the value-object cluster
      (§1.29). The nine-argument `reserveStake(...)` becomes `StakeReservationCommand`, and the moment it
      is an object it can be queued, logged and replayed. `[API]`
2.16.8 **Extract Class** → produces almost every structural pattern's collaborator, and is the move behind
      Data Clumps, Large Class and Divergent Change. The mechanical selection rule: fields that are *used
      together* by the same methods form the extraction boundary. `[PROVE]`
2.16.9 **Encapsulate Collection** → the precondition for the aggregate boundary (§2.22). `getEntries()`
      returning the live `List<LedgerEntry>` lets a caller add an unbalanced entry; return
      `List.copyOf(entries)` and add `addBalancedSet(...)` on the root. `[API]`
2.16.10 **Replace Primitive with Object** → produces Value Object (§1.29) and kills Primitive Obsession.
      The measured cost is an allocation per wrapper, mitigated by escape analysis (§3.2) and — one day —
      by value classes; do not claim the cost is zero. `[X-REF 06]` `[NUM]`
2.16.11 **Introduce Special Case** → 1e called this *Introduce Null Object*, and 2e's rename is the more
      honest name: the pattern generalises beyond null to "unknown client", "unmatched deposit". Produces
      Null Object (§1.29). `[VERSION-TRAP]`
2.16.12 **Replace Nested Conditional with Guard Clauses** → produces nothing, and that is the point: it is
      the move that most often makes a pattern *unnecessary*. Five levels of nesting in the withdrawal gate
      flatten into five early returns, and the "I need a Chain of Responsibility here" impulse evaporates. `[DECIDE]`
2.16.13 **Separate Query from Modifier** → produces command-query separation (§2.11) and is the
      precondition for caching, retry and idempotency: you cannot safely retry a call that both reads and
      writes. `[X-REF 12]`
2.16.14 **Parameterize Function** → collapses `applyDepositBlock()` / `applyStakeBlock()` /
      `applyWithdrawalBlock()` into `applyBlock(RestrictionType)`. The inverse move, *Remove Flag
      Argument*, is correct when the flag selects fundamentally different behaviour rather than a value. `[API]`
2.16.15 **Replace Function with Command** → produces Command (§1.24). Correct when the invocation needs
      state of its own, undo, queueing or authorisation. `PaymentRun` submission is the QuizStakes case:
      operator-gated, 4 files/day, drain-before-terminate. `[API]`
2.16.16 **Replace Command with Function** → the *de-patterning* inverse, and the one candidates never name.
      A `Command` class with one field, no undo, one caller and no queue is a function wearing a class.
      Naming this move out loud is the strongest available signal that you size solutions. `[SAY]`
2.16.17 **Inline Function / Inline Class / Collapse Hierarchy / Remove Middle Man / Remove Dead Code** —
      the de-patterning set. Every pattern in §1 has an exit, and the exit is a named catalogue move. A
      pattern catalogue taught without these is how over-engineering becomes permanent. `[TABLE]`
2.16.18 **Extract Function / Inline Function** as the *reversible pair* — Fowler's catalogue is built from
      inverse pairs (Extract/Inline, Pull Up/Push Down, Encapsulate/Remove, Parameterize/Remove Flag
      Argument). Knowing the inverse exists is what makes refactoring safe to attempt. `[TABLE]`
2.16.19 **Change Function Declaration** as the highest-frequency move in real work (rename + signature
      change) and the one the IDE can do transactionally. The mechanical property that makes it safe:
      the compiler enumerates every call site. `[PROVE]`
2.16.20 **Split Phase** → produces Pipeline (§2.17) and is the move behind CQRS at method scale: separate
      "work out what to do" from "do it". The `BankDeposits` 40k-record file at 06:00 splits into parse →
      match → post. `[API]`
2.16.21 Discipline leaf: **never change behaviour and structure in the same commit.** Mechanism of why it
      matters — `git bisect` answers "which commit broke this", and a mixed commit makes the answer
      useless. Two commits, two messages, two reviewable diffs. `[X-REF 17]`
2.16.22 Discipline leaf: **the protecting test comes first, and when legacy behaviour is unknown it is a
      characterisation (golden-master / approval) test.** You are protecting what the code *does*, not what
      it should do; a characterisation test that encodes a bug is correct and the bug is fixed in a
      separate behaviour commit. `[X-REF 16]`
2.16.23 Discipline leaf: **the move too large for one commit** — *branch by abstraction*. Introduce the
      abstraction, route all callers through it, build the new implementation behind it dark, switch
      callers cohort by cohort, delete the old one, remove the abstraction if it has no second
      implementation. Trunk stays green at every step. (§2.25)
2.16.24 Discipline leaf: **the Mikado Method** for a refactoring whose prerequisites are unknown — attempt
      the goal, note what breaks, revert, do the prerequisite first, repeat, building a dependency graph of
      moves. The revert is the essential step and the one people skip. `[RESEARCH]`
2.16.25 **Trap:** "refactoring" used to mean any code change. Fowler's definition is exact — a change to
      internal structure that does *not* alter observable behaviour. A rewrite is not a refactoring, and
      calling it one is how a two-week structural change gets approved with no test plan. `[TRAP]`

*(25 leaves)*

## §2.17 Architecture styles — what each optimises, its unit of modularity, and the symptom that means you chose wrong

2.17.1 The partition axis that organises the whole catalogue: **technical partitioning** (layers — grouped
      by what the code *is*) vs **domain partitioning** (grouped by what the code is *about*). Every style
      below is one of the two, and the choice determines whether a feature change is one directory or four.
      `[TABLE]`
2.17.2 The second axis: **monolithic** (layered, pipeline, microkernel, modular monolith, vertical slice)
      vs **distributed** (service-based, event-driven, space-based, orchestration-driven SOA,
      microservices, serverless, actor). The distributed set inherits every fallacy of distributed
      computing as a standing cost. `[X-REF 22]`
2.17.3 **Layered / n-tier** — optimises *initial simplicity and low cost*. Unit of modularity: the
      technical layer. Deployment shape: one unit. Trades away deployability, testability, elasticity and
      evolvability. Symptom you chose wrong: a one-field feature touches controller, DTO, service,
      repository, entity, migration — change amplification with a `[NUM]` files-per-feature count. `[TABLE]`
2.17.4 **Hexagonal (ports & adapters)** — Cockburn, 2005. Optimises *symmetry between driving and driven
      sides*: the application has one inside, and every outside actor (UI, test harness, DB, PSP) is an
      adapter behind a port. Unit of modularity: the port. The hexagon has no significance beyond "more
      than four sides" — it exists to stop people drawing a top and a bottom. `[SOURCE]`
2.17.5 **Clean architecture** — Martin, 2017. Optimises *the explicit Dependency Rule* ("source code
      dependencies point only inward") and makes **use cases first-class objects** in their own ring. Unit
      of modularity: the use case. This is the genuine difference from hexagonal: hexagonal says nothing
      about use-case objects. `[SOURCE]`
2.17.6 **Onion architecture** — Palermo, 2008. Optimises *ring-structured layering with domain services as
      a named ring* (domain model → domain services → application services → infrastructure). Unit of
      modularity: the ring. The genuine difference: onion is prescriptive about *layers inside the core*
      and comparatively silent on the technical mechanism of inversion. `[RESEARCH]`
2.17.7 The leaf that says what is genuinely the same across all three: **the dependency direction and the
      interface-ownership rule.** In all three, the abstraction is owned by the inner region and the
      implementation is outer, so the compile-time arrow points inward while control flows outward. If a
      candidate can only state one thing about the three, this is the one to state. (§2.10) `[SAY]`
2.17.8 **Trap:** "hexagonal, clean and onion are the same thing" — true about the dependency rule, false
      about the artefacts. Hexagonal gives you ports and adapters and *no opinion* on use cases; clean adds
      the use-case ring and the entity/use-case split; onion adds domain services and the ring diagram.
      They differ in *how many named regions you must create*, which is precisely the ceremony you are
      buying. `[TRAP]`
2.17.9 **Vertical slice architecture** — Bogard, ~2018. Optimises *cohesion along the axis of change*: one
      folder per use case containing its request, handler, validation and persistence, with layers allowed
      to differ per slice. Unit of modularity: the slice. Trades away consistency between slices and the
      single-place-to-change-a-cross-cutting-rule property. Symptom you chose wrong: the same rule
      implemented five slightly different ways in five slices. `[RESEARCH]`
2.17.10 **Modular monolith** — optimises *boundary enforcement without distribution cost*. Unit of
      modularity: the module (package root, or a JPMS module, or a build module). Deployment shape: one
      unit. Trades away independent deployability and independent scaling. Symptom you chose wrong:
      boundary erosion — a module reaching into another's internals because nothing failed the build. (§2.29)
2.17.11 **Microservices** — optimises *independent deployability*, and that is the only thing on the list it
      is uniquely good at. Unit of modularity: the bounded context, one per deployable. Trades away
      simplicity, overall cost, and performance (every in-process call becomes a network hop). Symptom you
      chose wrong: a coordinated release — two services that must ship together. `[TABLE]`
2.17.12 **Service-based architecture** — the under-taught middle: 4–12 coarse-grained domain services,
      often over a *shared* database, no per-service data ownership. Optimises *most of the deployability
      and testability benefit at a fraction of the cost*, and rates highest of the distributed styles on
      simplicity and cost. Symptom you chose wrong: the shared schema becomes the coupling that forces
      coordinated releases anyway. `[RESEARCH]` `[DECIDE]`
2.17.13 **Orchestration-driven SOA** — the historical style: enterprise service bus, a central
      orchestration engine, a shared canonical enterprise data model, business/enterprise/application/
      infrastructure service taxonomy. Optimises *enterprise-wide reuse*. It failed on deployability,
      testability and performance, and the reason is worth stating: the canonical data model made every
      change a cross-organisation change. Name it so "SOA" is not used as a synonym for microservices. `[RESEARCH]`
2.17.14 **Event-driven architecture** — optimises *responsiveness, elasticity and fault tolerance* by
      removing synchronous coupling. Unit of modularity: the event processor. Two topologies to name
      separately: **broker** (no central coordinator, chained events, highest decoupling, no workflow
      visibility) and **mediator** (a central event mediator owns the workflow, gains error handling and
      restart, loses decoupling). Symptom you chose wrong: no one can answer "where is deposit 4471 right
      now". `[X-REF 14]`
2.17.15 **Pipeline architecture** — optimises *composability of transformation steps*. Unit of modularity:
      the filter (producer / transformer / tester / consumer), connected by pipes with unidirectional flow.
      The `BankDeposits` 06:00 40k-record file (500k at month end) is the QuizStakes instance: parse →
      validate → match sender → post to suspense → attribute. Trades away elasticity and scalability — it
      is a batch shape. `[SOURCE]`
2.17.16 **Microkernel / plug-in architecture** — optimises *extensibility of a stable core*. Unit of
      modularity: the plug-in, reached through a registry and a plug-in contract. The
      `DocumentVerification` vendor set is the QuizStakes instance: one core verification workflow, one
      plug-in per identity vendor, so vendor churn does not ripple (§4.3 of the scenario). Symptom you
      chose wrong: a plug-in that needs to change the core contract every release. (§4.3)
2.17.17 **Space-based architecture** — optimises *extreme elasticity under unpredictable concurrent load*
      by removing the database from the request path: processing units hold a replicated in-memory data
      grid, and a data pump writes through asynchronously. Named components: processing unit, virtualised
      middleware (messaging grid, data grid, processing grid, deployment manager), data pump, data writer,
      data reader. Trades away simplicity and correctness-under-partition. Symptom you chose wrong: you
      need read-your-writes and the grid gives you eventual. `[RESEARCH]`
2.17.18 Why space-based is the wrong style for `FundsLedger` despite its 13,600/sec peak — the ledger's
      invariant ("sum across all positions is always zero") is a serialisation requirement, and §7.2 of the
      scenario already puts it on its own pause-sensitive instance. Elasticity is not the constraint;
      correctness is. `[DECIDE]` `[PROVE]`
2.17.19 **Serverless / FaaS** — optimises *cost at low and spiky duty cycle* and removes capacity planning.
      Unit of modularity: the function. Trades away latency predictability (cold start), long-running work
      (execution ceiling), and stateful connection reuse (connection-pool-per-instance explosion against
      the DB). `BankDeposits` — idle 23 hours a day, one 40k file at 06:00 — is the QuizStakes candidate,
      and the JVM cold-start cost is the reason it is only a candidate. `[X-REF 18]` `[NUM]`
2.17.20 **Actor model as an architecture style** — optimises *fault isolation and location transparency*.
      Unit of modularity: the actor, with a mailbox, single-threaded message processing (so no locks
      inside), a supervision hierarchy, and "let it crash" as the error strategy. Trades away
      debuggability and static reasoning: the call graph exists only at runtime. Java 21 relevance: virtual
      threads make an actor-per-entity feasible without a framework. `[X-REF 05]`
2.17.21 The **quality attribute each style is *for*** stated as one sentence per style, because the
      interview question is never "what is layered architecture" but "why would you pick it". `[TABLE]` `[SAY]`
2.17.22 The **unit of modularity** column stated on its own, because it is the single most diagnostic fact
      about a style: layer / port / use case / ring / slice / module / service / event processor / filter /
      plug-in / processing unit / function / actor. `[TABLE]`
2.17.23 The **deployment shape** column: one unit (layered, pipeline, microkernel, modular monolith,
      vertical slice), a few units (service-based, orchestration-driven SOA), many units (microservices,
      event-driven, space-based, actor), no units you manage (serverless). `[TABLE]`
2.17.24 The **symptom that means you chose wrong**, per style, as a single table — this is the leaf that
      turns the catalogue from memorisation into a diagnostic. `[TABLE]` `[DECIDE]`
2.17.25 **Hybrid is the normal case, not the exception.** QuizStakes is service-based at the top (22
      services, mostly schema-per-service on a shared instance), event-driven on the dotted arrows of §5,
      pipeline inside `BankDeposits`, microkernel inside `DocumentVerification`, and hexagonal inside
      `FundsLedger`. Naming a single style for a real system is the tell that the reader has not built one. `[SAY]`
2.17.26 **Trap:** treating an architecture style as an architecture. A style is a *topology and a set of
      constraints*; an architecture additionally names the components, the data ownership, the quality
      attribute targets and the trade-offs accepted. "We're microservices" answers none of those. `[TRAP]`
2.17.27 **Trap:** "microservices for scalability". Scalability is available in a monolith by running more
      instances behind a load balancer — `ApplicationGateway` scales 12 → 40 instances without being
      decomposed. What a monolith cannot do is scale *one component independently*: `FundsLedger` at 12 GB
      / 3 instances and `ClientRestrictions` at 4 GB / 8 instances have different resource profiles, and
      *that* is the scalability argument. `[TRAP]` `[PROVE]`
2.17.28 **Trap:** "serverless has no servers, therefore no capacity planning". You still plan concurrency
      limits, downstream connection counts and cold-start budgets — and against a card-PSP p99 of 11 s on
      authorise, a function's execution ceiling is a hard design constraint, not a footnote. `[TRAP]` `[NUM]`
2.17.29 The **decision procedure**: name the two quality attributes that dominate → name the partition axis
      the domain wants → name the deployment granularity the org can operate (CI/CD, on-call, tracing) →
      pick the cheapest style that satisfies all three → state the trigger that would move you to the next
      one. Explicit "do not use this when": do not pick a distributed style before you have per-service
      on-call and distributed tracing, because you have bought the failure modes without the observability
      to diagnose them. `[DECIDE]` `[X-REF 20]`
2.17.30 Conway's law as an architecture-selection input, not a slogan: the style you can *sustain* is the
      one whose module boundaries match team boundaries. 40 operators on shift (90 at peak) using
      `InternalPlatforms` is an organisational fact that shows up as a service boundary. `[SOURCE]`

*(30 leaves)*

## §2.18 The fitness table — architecture styles against quality attributes

2.18.1 The table's contract: rows are the styles of §2.17, columns are **deployability, testability,
      performance, scalability, elasticity, fault tolerance, evolvability, simplicity, overall cost**, and
      the cells are ratings taken from Richards & Ford, *Fundamentals of Software Architecture* (O'Reilly),
      which publishes a one-to-five-star scorecard per style. Ratings are **cited, not invented**; where
      the primary grid could not be read verbatim the cell is marked and the qualitative reading is given
      instead. `[TABLE]` `[SOURCE]` `[RESEARCH]`
2.18.2 **Layered** — simplicity high, overall cost low (i.e. cheapest), reliability medium; deployability
      low, testability low, performance low-to-medium, scalability low, elasticity low, fault tolerance
      poor. The shape to notice: it wins exactly two columns and loses the rest, which is why it survives —
      those two columns are the ones a new project actually optimises. `[TABLE]` `[RESEARCH]`
2.18.3 **Pipeline** — cost low, simplicity high, modularity high; deployability and testability medium;
      elasticity and scalability very low; fault tolerance and availability low. `[TABLE]` `[RESEARCH]`
2.18.4 **Microkernel** — simplicity high, cost low; deployability, testability, reliability, modularity and
      extensibility slightly above average; scalability and fault tolerance low. `[TABLE]` `[RESEARCH]`
2.18.5 **Service-based** — testability, deployability, fault tolerance, availability and evolvability all
      four of five; scalability three; elasticity two; and it is the cheapest and simplest of the
      distributed styles. This row is the argument for stopping here rather than going to microservices. `[TABLE]` `[RESEARCH]`
2.18.6 **Event-driven** — performance, scalability, elasticity, fault tolerance and evolvability high;
      simplicity and testability low. `[TABLE]` `[RESEARCH]`
2.18.7 **Space-based** — elasticity, scalability and performance highest of any style; simplicity, testability
      and overall cost worst. `[TABLE]` `[RESEARCH]`
2.18.8 **Orchestration-driven SOA** — some elasticity and scalability; performance poor; deployability and
      testability poor; cost high. The only style on the table that loses on nearly every axis, which is why
      it is a historical entry rather than a live option. `[TABLE]` `[RESEARCH]`
2.18.9 **Microservices** — scalability, elasticity, evolvability, fault tolerance and deployability highest;
      performance a named weakness (network hops, no in-process transactions); simplicity and overall cost
      worst alongside space-based. `[TABLE]` `[RESEARCH]`
2.18.10 How to *read* the table, which is the part candidates skip: no style wins, the columns are not
      independent (simplicity and cost move together; scalability and simplicity move opposite), and the
      correct use is to pick the two columns your requirements make non-negotiable and then take the
      cheapest row that scores well on both. `[DECIDE]`
2.18.11 The QuizStakes reading of the table, worked: hard columns are fault tolerance (money paths),
      elasticity (`ApplicationGateway` 12 → 40) and evolvability (regulatory cadence); simplicity is
      sacrificed knowingly; the resulting choice is service-based with event-driven edges, not full
      microservices — and the trigger to move is a component whose deploy cadence or resource profile
      diverges. `[PROVE]` `[DECIDE]`
2.18.12 **Trap:** treating the star ratings as measurements. They are the authors' calibrated judgement
      across many systems, published as a *comparison aid*; quoting "microservices score 5 for elasticity"
      as a measured fact misrepresents the source. Cite it as expert calibration and state your own
      constraints. `[TRAP]` `[SOURCE]`

*(12 leaves)*

## §2.19 Package structure — by-layer vs by-feature vs by-component, and what the compiler can police

2.19.1 **Package by layer** — `com.quizstakes.controller.*`, `.service.*`, `.repository.*`. Optimises
      "where do I put a new service class". The mechanical consequence is the whole argument against it. `[API]`
2.19.2 **Package by feature** — `com.quizstakes.restrictions.*`, `.ledger.*`, `.bonus.*`, `.paymentrun.*`.
      One directory per domain concept, all layers inside it. `[API]`
2.19.3 **Package by component** — Brown's variant: a `*Component` façade class is the only `public` type,
      and the web layer talks to components rather than to repositories; the repository is package-private
      inside the component. Distinct from by-feature in that it *names the deployable-shaped unit*. `[RESEARCH]`
2.19.4 The mechanical argument that decides it: **Java's access modifiers are package-scoped.** With
      package-by-layer every class the layer above calls must be `public`, so nothing can be hidden and
      every class is a legal dependency of every other class in the application. `[PROVE]`
2.19.5 With package-by-feature the feature's internals can be **package-private** and only the deliberately
      exposed entry point is `public`, so the boundary is enforced by `javac` rather than by a code-review
      convention. This is the only layout argument that does not reduce to taste. `[PROVE]` `[SAY]`
2.19.6 The cost of package-by-feature that must be stated: **no sub-packages without losing the
      enforcement**, because package-private does not nest — `ledger.internal.X` is not visible to
      `ledger.Y`. Large features therefore either go flat or accept `public` internals. `[TRAP]`
2.19.7 The `internal` package convention as the answer to that: `ledger.api` (public) + `ledger.internal`
      (public to the compiler, forbidden by convention and by an ArchUnit rule). The convention exists
      precisely because the compiler cannot express it — name that honestly rather than presenting it as
      enforcement. (§2.29)
2.19.8 **JPMS as the stronger form of the same layout choice** — a `module-info.java` that exports
      `com.quizstakes.ledger.api` and not `...internal` turns the convention of §2.19.7 into the only
      arrangement in Java where an unexported package is genuinely unreachable, reflection included. What
      it changes about *layout* is that the boundary is now declared in a file rather than implied by the
      package tree. Module-system mechanics: §3.20, `[X-REF 06]`. `[DECIDE]`
2.19.9 Why JPMS is nonetheless rare in Spring Boot services: the fat-jar/classpath deployment model, split
      packages across dependencies, and reflective frameworks needing `opens`. State the mechanism *and*
      the reason the industry mostly declined it. `[VERSION-TRAP]`
2.19.10 The **build module** as the third enforcement tier and the strongest practical one: a separate Maven/
      Gradle module for `domain` with no framework dependency in its build file. The dependency is now
      declared in a file a reviewer reads, and a violation is a build failure, not a lint warning. (§2.29)
2.19.11 The consequence chain of package-by-feature beyond enforcement: a feature change touches one
      directory (small reviewable diffs, low merge contention, mechanical code ownership); the package tree
      names the domain rather than the framework; and extracting the feature into its own service later is
      a directory move rather than an archaeology project. (§2.30)
2.19.12 **Trap:** package-by-layer defended as "clean separation of concerns". It separates concerns in the
      *file tree* while making every class globally reachable — the opposite of separation where it counts.
      The test to state: pick a random internal class and ask which packages *could* legally call it. Under
      by-layer, all of them. `[TRAP]`

*(12 leaves)*

## §2.20 DDD strategic design — subdomains, bounded contexts, and every context-relationship pattern by name

2.20.1 The distinction the whole section rests on: the **problem space** is divided into *domain and
      subdomains* (a fact about the business you discover), and the **solution space** is divided into
      *bounded contexts* (a design decision you make). Conflating the two is the most common DDD error. `[PROVE]`
2.20.2 **Core subdomain** — where the business differentiates and where your best people go. QuizStakes:
      the bonus/cash split arithmetic and the win/void asymmetry of §11.3 — nobody sells that, and getting
      it wrong creates or destroys money. `[DECIDE]`
2.20.3 **Supporting subdomain** — necessary, business-specific, not differentiating. QuizStakes:
      `DocumentRequirements` (the obligations model) and `ApplicationHistory`. Build, but plainly. `[DECIDE]`
2.20.4 **Generic subdomain** — solved problems you should buy. QuizStakes: identity-document verification,
      watchlist screening, card acquiring, JWT issuance. The scenario's §5.1 rule ("every external vendor
      sits behind exactly one owning service") is the generic-subdomain rule made operational. `[DECIDE]`
2.20.5 The investment rule that follows: effort per subdomain type is *not* equal, and a team that has
      hand-built a screening engine while the bonus arithmetic lives in a 400-line transaction script has
      inverted it. `[SAY]`
2.20.6 **Bounded context** — the boundary within which one model applies and every term has exactly one
      meaning. "Withdrawal" in `CardPayments` (a PSP-facing authorisation with an immediate refund path)
      and "Withdrawal" in `BankWithdrawal` (a record inside an operator-gated `PaymentRun`) share a state
      vocabulary and are *different models* — §7.3 of the scenario is exactly this. `[PROVE]`
2.20.7 The mechanism that makes separate models correct rather than duplicative: a single shared
      `Withdrawal` class would have to satisfy both invariant sets — "refund-to-source does not bounce" and
      "`RETURNED` is a real state" — and would therefore satisfy neither. `[PROVE]`
2.20.8 **Trap:** bounded context = microservice. A bounded context is a *model boundary*; a microservice is
      a *deployment boundary*. One context may be several services (`AccountOpening` + `PersonalDetails` +
      `ClientAgreements` + `AssessmentService` are one onboarding context) and one service may host two
      contexts early on. Deployment granularity is chosen for operational reasons, model granularity for
      linguistic ones. `[TRAP]`
2.20.9 **Trap:** "one bounded context per team". Team Topologies-style advice compresses to this, and it is
      an oversimplification in both directions: a team can own several small contexts, and a large core
      context may need several teams in a partnership relationship. What is true is the inverse — a context
      owned by *two* teams with no relationship pattern declared will drift. `[TRAP]`
2.20.10 **Ubiquitous language** — one language per context, used identically in conversation, code, tests,
      and the database. Not decoration: `CLIENT_BONUS_RESERVED` appearing verbatim as a position name, an
      enum constant and a spoken phrase is what removes the translation step where requirements get
      mistranslated. `[SAY]`
2.20.11 The mechanical test for ubiquitous language: take a sentence a compliance analyst said in the last
      meeting and grep the codebase for its nouns. `SELF_EXCLUDED`, `reversibleByOperator`, `SUSPENSE`,
      `PaymentRun` all hit; if the code says `flagB` and `status2`, the language is not ubiquitous. `[PROVE]`
2.20.12 **Context map** — the artefact that names every context, every integration, and the *relationship
      pattern* on each edge, with the power direction (upstream/downstream) marked. A context map without
      power direction is an architecture diagram, not a context map. `[DIAG]`
2.20.13 **Shared kernel** — two contexts share an explicitly delimited part of the model and change it only
      by joint agreement, with a shared test suite as the contract. Cost: continuous coordination. Correct
      for `Money` and `ClientId`; catastrophic for `Client`. `[SOURCE]`
2.20.14 **Customer/Supplier** — downstream is the customer, upstream the supplier, and the customer's needs
      are a planned input to the supplier's backlog. QuizStakes: `BalanceView` (customer) and `FundsLedger`
      (supplier). Requires organisational alignment to be real, not just a diagram arrow. `[SOURCE]`
2.20.15 **Conformist** — downstream adopts the upstream model wholesale with no translation, because it has
      no influence and translation is not worth the cost. QuizStakes: a card-scheme chargeback reason-code
      taxonomy adopted verbatim. The trade being made is explicit: zero mapping cost, total model coupling. `[DECIDE]`
2.20.16 **Anti-corruption layer** — downstream translates the upstream model into its own, so upstream
      changes stop at the translator. QuizStakes: `BankDeposits` ingesting the banking partner's statement
      file (40k records at 06:00) into internal `SUSPENSE` postings. Structurally this is Adapter (§1.13)
      at module scale — say that, because it connects the pattern catalogue to strategic design. (§1.13)
2.20.17 **Open Host Service** — upstream publishes a deliberately designed, stable protocol for *many*
      downstreams rather than a per-consumer interface. QuizStakes: `ClientRestrictions`' synchronous
      decision call, consumed by deposit, stake, withdrawal, instrument-add and login flows. `[SOURCE]`
2.20.18 **Published Language** — a shared, well-documented interchange schema that neither side owns
      privately (ISO 20022 for payments, a versioned Avro/JSON Schema event contract). Distinct from Open
      Host Service: OHS is *whose API*, published language is *whose vocabulary*. `[X-REF 14]`
2.20.19 **Separate Ways** — the decision *not* to integrate, duplicating instead. Legitimate and
      under-used: two contexts each keeping their own tiny notion of "country" beats a shared reference-data
      service. The `[DECIDE]` rule: choose it when the integration cost exceeds the duplication cost and
      the duplicated concept is small and stable. `[DECIDE]`
2.20.20 **Partnership** — two contexts with mutual dependency that succeed or fail together, coordinating
      releases deliberately. Honest label for `AccountActivation` and `DocumentVerification`; pretending
      they are customer/supplier hides the coupling instead of managing it. `[SOURCE]`
2.20.21 **Big Ball of Mud** — a named relationship pattern, not just an insult: it marks a region of the map
      with no discernible boundaries, and the correct strategy is to *draw a boundary around it* and put an
      anti-corruption layer between it and everything new. Naming the mud is what makes the strangler fig
      (§2.25) plannable. `[SOURCE]`
2.20.22 The relationship-pattern taxonomy in the three groups the literature uses: **upstream** (Open Host
      Service, Published Language), **downstream** (Customer/Supplier, Conformist, Anti-Corruption Layer),
      **symmetric/midway** (Shared Kernel, Partnership, Separate Ways) — plus Big Ball of Mud as a marker.
      Reciting the group tells the interviewer you know which end pays. `[TABLE]` `[RESEARCH]`
2.20.23 **Distillation** — the strategic-design move of progressively separating the core domain out of a
      large model: *Core Domain*, *Generic Subdomains*, *Domain Vision Statement*, *Highlighted Core*,
      *Cohesive Mechanisms*, *Segregated Core*, *Abstract Core*. Name all seven; they are the answer to
      "how do you actually get from a big ball of mud to a core domain". `[SOURCE]` `[RESEARCH]`
2.20.24 **Large-scale structure** patterns as the third strategic group: *Evolving Order*, *System
      Metaphor*, *Responsibility Layers*, *Knowledge Level*, *Pluggable Component Framework*. Less used than
      the context-map set and still on the exam. `[RESEARCH]`
2.20.25 **Trap:** strategic design treated as optional preamble to the tactical patterns. The tactical
      patterns (§2.21) are worthless applied across a wrong boundary — a beautifully modelled aggregate
      spanning two bounded contexts is a distributed transaction waiting to be discovered. Strategy first,
      tactics second, and say so in that order. `[TRAP]` `[SAY]`

*(25 leaves)*

## §2.21 DDD tactical patterns — each with its QuizStakes instance and the mechanical test for which one a class is

2.21.1 **Entity** — has identity that persists through state change; equality is by identifier, never by
      field values. QuizStakes: `Application` (an `AO-`/`AA-` lifecycle plus an audit trail). Mechanical
      test: *if two instances with identical fields are different things, it is an entity.* `[API]`
2.21.2 Entity implementation mechanics in Java: `equals`/`hashCode` on the identifier only, identifier
      assigned at construction (not by the database) so the object is valid before persistence, and
      `final` identifier field. `[X-REF 08]`
2.21.3 **Value object** — no identity, equality by value, immutable, side-effect-free operations, and freely
      replaceable rather than mutable. QuizStakes: `Money`, `ClientId`, `StakeSplit`, `DateRange`. A Java
      `record` is the exact shape. Mechanical test: *if you would happily replace the whole object rather
      than change one field, it is a value object.* `[API]`
2.21.4 The rounding rule of §11.4 as a value-object invariant, not a service rule: the bonus portion rounds
      *down* to the minor unit and cash covers the remainder, so the two legs always sum to exactly the
      stake. Put it in `StakeSplit`'s compact constructor and the "0.34 + 3.00 = 3.34 creates money" bug
      becomes unconstructable. `[PROVE]` `[NUM]`
2.21.5 **Aggregate** — a cluster of entities and value objects treated as one unit for data change, with a
      consistency boundary. Full treatment in §2.22; here only the vocabulary leaf.
2.21.6 **Aggregate root** — the single entity through which all external access to the cluster goes; the
      only member with a global identity and the only member a repository returns. QuizStakes:
      `PaymentRun` is the root, its 1.8k withdrawal records are internal members. Mechanical test: *the
      root is the object whose deletion should delete the rest.* `[API]`
2.21.7 **Repository** — a collection-like interface for *aggregate roots*, owned by the domain, returning
      aggregates rather than rows and never leaking query language outward. Mechanical test: *one
      repository per aggregate root, and no more.* A repository for a non-root member is the reliable tell
      that the aggregate boundary is wrong. `[API]` `[X-REF 08]`
2.21.8 Repository shapes: the collection-oriented form (`add`, `remove`, and mutation tracked by the
      persistence context) versus the persistence-oriented form (`save` explicitly called). Spring Data's
      `CrudRepository.save` is the latter; Hibernate's dirty checking makes the former possible, and mixing
      the two mental models is where "why wasn't my change saved" comes from. `[X-REF 08]` `[API]`
2.21.9 **Factory** — encapsulates the creation of a whole aggregate when construction is complex enough to
      be its own responsibility, and guarantees the aggregate is valid the instant it exists. QuizStakes:
      creating an `Application` at `AO-100` also creates a client, an account shell and a person, plus the
      three `SYSTEM_ONBOARDING` restrictions — that is a factory, not a constructor. (§1.6)
2.21.10 **Domain service** — stateless behaviour that belongs to the domain but to no single entity or value
      object, named in the ubiquitous language, taking and returning domain types. QuizStakes: the
      bonus/cash split calculation, which needs the wallet's four positions and the bonus rules and belongs
      to neither. Mechanical test: *if the operation needs two aggregates and mutates neither, it is a
      domain service.* `[API]`
2.21.11 **Application service** — orchestration only: opens the transaction, loads aggregates through
      repositories, calls domain behaviour, saves, publishes events, maps to DTOs. Contains **no business
      rules**. This is the layer `@Transactional` belongs on. Mechanical test: *if you deleted every
      framework annotation, would any business rule disappear? If yes, it is not an application service.* `[API]` `[X-REF 07]`
2.21.12 **Infrastructure service** — a technical capability with no domain meaning behind a domain-owned
      port: sending a notification, writing to the outbox, calling the PSP. QuizStakes: `CardPayments`'
      PSP client behind a `PayoutGateway` port. Mechanical test: *the interface is in the domain module,
      the implementation is not.* (§2.10)
2.21.13 The three-service table with the disambiguating question stated: *does it hold a business rule?*
      (domain) → *does it open a transaction and sequence steps?* (application) → *does it speak a
      technology?* (infrastructure). Getting this wrong is how the anemic model happens. `[TABLE]` `[DECIDE]`
2.21.14 **Domain event** — an immutable fact stated in the past tense, carrying identifiers, the occurrence
      time and the aggregate version, published by the aggregate and dispatched after commit. QuizStakes:
      `StakeSettled`, `RestrictionLifted`, `BonusClawedBack`. Mechanical test: *the name is a past-tense
      verb and the payload has no methods.* (§1.23) `[API]`
2.21.15 Domain event vs integration event: the domain event is internal to the context and may carry
      domain types; the integration event is a published-language contract with a version and a schema, and
      changing it breaks other teams. One is refactorable, the other is not. `[X-REF 14]`
2.21.16 Where an event is *raised* vs where it is *published*: raised by the aggregate into an in-memory
      list during the transaction, published by the application service after commit. Raising inside the
      aggregate is what keeps the causality with the state change; publishing after commit is what stops a
      rollback from having already told the world. (§3.19) `[FLOW]`
2.21.17 **Module** (Evans' term; "package" in Java) — a named division of the model that is part of the
      ubiquitous language, low-coupling/high-cohesion, and *not* organised by technical layer. This is
      Evans arriving independently at package-by-feature (§2.19).
2.21.18 **Specification** — a predicate object over a domain type, named in the ubiquitous language, and
      composable with `and`/`or`/`not`. QuizStakes: `EligibleForFirstDepositBonus` = valid coupon AND first
      deposit AND one-per-*identity*. Mechanical test: *it answers a yes/no question about one object and
      has a business name.* (§4.13)
2.21.19 Specification's three uses that justify the indirection: validation (is this object satisfactory),
      selection (query a repository by it), and construction-to-order. The Java tension worth naming: as a
      selection criterion it must be translatable to SQL/JPA `Criteria`, which is what pulls infrastructure
      knowledge back into an ostensibly pure domain object. `[TRAP]` `[X-REF 08]`
2.21.20 **Trap:** every noun becomes an entity. Most nouns are value objects, and choosing entity by default
      creates identity where none is needed, which means rows, IDs, lifecycles and equality bugs. Ask
      "does the business ever say *which* one" before granting identity. `[TRAP]`
2.21.21 **Trap:** the repository as a query API. Once a repository grows `findByStatusAndCreatedAtBetween
      AndSourceIn(...)` it is a DAO, and the aggregate has stopped being the unit of access. Reads that do
      not need an aggregate belong in a read model (§2.23), not on the repository. `[TRAP]`
2.21.22 **Trap:** domain service as dumping ground. A `RestrictionDomainService` with 40 methods is a
      transaction script wearing DDD vocabulary — the entities are anemic and the service holds every rule.
      The test: count business rules per class; if the entities have none, the pattern is decoration. (§6.2) `[TRAP]`
2.21.23 **Trap:** the JPA entity mistaken for the DDD entity. `@Entity` is a persistence mapping; a DDD
      entity is a model concept with invariants. They can be the same class — with public setters removed,
      a no-arg constructor kept `protected`, and collections encapsulated — and the moment you need
      `@Transient` gymnastics to keep the model honest, split them and pay the mapping cost. `[TRAP]` `[X-REF 08]`
2.21.24 The **assembler / DTO** boundary: aggregates never leave the application service. `ProfileService`
      assembling eight owners' data (§7.4 of the scenario) returns a DTO, and the leaf worth stating is
      *why* — an aggregate handed to a controller either gets mutated outside its transaction or drags
      lazy-loading into the view layer. (§1.29)
2.21.25 The full tactical checklist as one table — pattern, one-line definition, QuizStakes instance,
      mechanical test — so the reader can classify an unfamiliar class in under a minute. `[TABLE]`

*(25 leaves)*

## §2.22 Aggregate design — the invariant boundary and the sizing rules

2.22.1 The definition that does the work: an aggregate's boundary is **the set of invariants that must hold
      at the end of every transaction**. Not data ownership, not the UI screen, not the ER diagram —
      invariants. Everything else in this section follows mechanically. `[PROVE]`
2.22.2 The derivation, worked: "a `PaymentRun`'s total must equal the sum of its withdrawal records" is a
      transactional invariant → the records are *inside* the `PaymentRun` aggregate. "A client's
      restrictions must not contradict their account lifecycle" is *not* enforced transactionally → they are
      separate aggregates in separate services. `[PROVE]`
2.22.3 **Vernon's rule 1 — Protect true invariants in consistency boundaries.** The word doing the work is
      *true*: an invariant is a rule the business requires to hold *immediately*, not one it would prefer.
      QuizStakes' only genuinely non-negotiable one is self-exclusion taking effect before the next stake
      (§10.4), and the scenario says so explicitly. `[SOURCE]` `[RESEARCH]`
2.22.4 **Vernon's rule 2 — Design small aggregates.** Preferred size is a single entity plus its value
      objects. The reasoning is transactional and memory-bound, not aesthetic. `[SOURCE]`
2.22.5 **Vernon's rule 3 — Reference other aggregates only by identity.** `LedgerEntry` holds a `ClientId`,
      never a `Client` object. `[SOURCE]`
2.22.6 **Vernon's rule 4 — Use eventual consistency outside the boundary.** The mechanism: the aggregate
      publishes a domain event, a subscriber opens a *new* transaction and updates a *different* aggregate.
      The scenario's dotted arrows in §5 are exactly this set of edges. `[SOURCE]` `[X-REF 14]`
2.22.7 The corollary the four rules produce together: **one aggregate instance modified per transaction.**
      Two aggregates in one transaction is the design smell that says the boundary is drawn wrong, not that
      the rule is impractical. `[PROVE]`
2.22.8 The question that decides eventual vs immediate, stated as Vernon states it: *whose job is it to
      make the data consistent?* If the answer is the user who executed the command, immediate consistency
      inside one aggregate; if the answer is someone else or some other process, eventual consistency
      between aggregates. `[DECIDE]` `[SOURCE]`
2.22.9 **Reference by identity** — the four things it buys: the loaded object graph stays small, the
      transaction stays small, the aggregate can be moved to another service without a schema join, and
      serialisation for the outbox has a bounded payload. `[PROVE]`
2.22.10 What reference-by-identity costs, stated honestly: the "get the client's name for this ledger entry"
      query becomes two loads or an API composition (§2.25), and in JPA the temptation to add
      `@ManyToOne Client` for convenience is the single most common way an aggregate boundary is destroyed. `[TRAP]` `[X-REF 08]`
2.22.11 **The aggregate is the optimistic-locking unit.** A `@Version` column on the root means one
      compare-and-set protects the entire invariant set, including changes to child rows the version column
      does not live on. This is why the root, and only the root, carries `@Version`. `[X-REF 08]` `[API]`
2.22.12 The generated SQL as the proof: `update payment_run set ..., version=? where id=? and version=?`,
      zero rows affected → `OptimisticLockException`. Read the statement line by line; the `and version=?`
      clause *is* the invariant boundary expressed in SQL. `[DIAG]` `[SOURCE]` `[X-REF 08]`
2.22.13 The `FundsLedger` arithmetic that decides its aggregate size: **230 writes/sec sustained, 13,600/sec
      peak, 19.8M entries/day at ~180 bytes/row**, partition-affine by client id. A "Client" aggregate
      holding all positions and all entries would serialise every stake, deposit and settlement for that
      client through one version column. The per-client-position aggregate is what makes 13,600/sec
      possible. `[NUM]` `[PROVE]`
2.22.14 Sizing failure mode — **too large → contention.** Symptoms in order of appearance: rising
      `OptimisticLockException` rate, retry storms on the settlement path, p99 breaching the 150 ms
      stake-reservation budget while p50 is unchanged, and lock waits concentrated on a handful of client
      ids. `[INCIDENT]` `[NUM]`
2.22.15 Sizing failure mode — **too small → invariant leaks into the service layer.** If the bonus and cash
      positions are separate aggregates, "the two legs must sum to exactly the stake" can no longer be
      enforced by either one, so the check migrates into the application service, where a second caller, a
      batch job or a data-fix script will bypass it. The invariant is now a convention. `[INCIDENT]`
2.22.16 The diagnostic that distinguishes the two failure modes: too-large shows up as *contention metrics*
      (lock waits, version conflicts), too-small shows up as *duplicated validation* (the same rule grepped
      in three services). Different symptom, different fix, and confusing them makes it worse. `[DECIDE]`
2.22.17 **Trap:** designing aggregates from the UI. The composite operator screen of §7.4 needs eight
      owners' data on one page; that is a read-model requirement (§2.23), not an aggregate. Letting the
      screen define the aggregate produces the largest possible boundary. `[TRAP]`
2.22.18 **Trap:** designing aggregates from the ER diagram. Foreign keys express *referential* integrity;
      aggregates express *transactional* invariants. Every FK becoming a containment relationship yields
      one aggregate per database. `[TRAP]`
2.22.19 **Trap:** "eventual consistency between aggregates is a compromise we accepted". It is the design
      decision that makes the system scale, and it is chosen, not conceded. The `[SAY]` form: "consistency
      inside the boundary is immediate and consistency across boundaries is eventual with a stated window —
      here, under 2 s for the balance projection." `[TRAP]` `[SAY]` `[NUM]`
2.22.20 The aggregate-design procedure end to end: list the invariants → mark which must hold immediately →
      group the objects each immediate invariant spans → that grouping is the aggregate set → replace every
      cross-group object reference with an identifier → put `@Version` on each root → for every invariant
      you marked non-immediate, name the event and the consistency window. `[FLOW]` `[DECIDE]`

*(20 leaves)*

## §2.23 CQRS

2.23.1 The separation actually being made: **the model used to change state and the model used to answer
      questions are different models**, because the write side is optimised for invariants (normalised,
      aggregate-shaped, transactional) and the read side for query shape (denormalised, join-free,
      cache-friendly). One schema cannot be optimal for both. `[PROVE]`
2.23.2 What CQRS is *not*: it is not command-query *separation* (§2.11), which is a method-level rule about
      a function either returning a value or having an effect. Same origin word, different scope. Say the
      distinction, because interviewers use CQS and CQRS interchangeably and the correction scores. `[TRAP]` `[SAY]`
2.23.3 **Level 1 — same model, separate methods.** `FundsLedger` keeps one schema; command methods return
      `void` and query methods are `@Transactional(readOnly = true)`. Cost: nearly zero. Benefit: the read
      path stops loading aggregates it will not mutate. `[API]`
2.23.4 **Level 2 — separate models, one store.** `BalanceView` computes stakeable/withdrawable/total as
      derived views over `FundsLedger`'s positions (§11.1: "computed, never stored"), reading through
      projections or SQL views rather than through the aggregate. Cost: two mapping layers. `[API]`
2.23.5 **Level 3 — separate stores.** The read model gets its own database, updated asynchronously from the
      write side's events. Cost: projection lag becomes user-visible and a whole class of "my balance
      didn't update" tickets appears. `[NUM]`
2.23.6 **Level 4 — separate services.** `BalanceView` is its own deployable with its own scaling profile.
      §4.6 of the scenario gives the reason: `BalanceView` is narrow and hot (read on every screen and
      before every stake preview), `ProfileService` is wide and cold (eight owners, one operator at a
      time) — merging them would give the hot path the cold path's availability characteristics. `[PROVE]`
2.23.7 The escalation rule: each level costs more and buys more, and you go up a level only when a named
      metric forces it. Explicit "do not use this when": do not go past level 1 for a CRUD screen, and do
      not go to level 3 without a plan for read-your-writes. `[DECIDE]`
2.23.8 **Projection lag with a number attached.** The `80 ms balance-read budget` is the read-path SLO; the
      projection window is separate and must be stated as its own figure — a `StakeSettled` event committed
      at T is visible in `BalanceView` at T + lag, and the design target is sub-second with an alert at 2 s.
      "It's eventually consistent" is not an answer; a number is. `[NUM]` `[SAY]`
2.23.9 How the lag is *measured*, not assumed: stamp the event with its commit timestamp, stamp the
      projection row with its apply timestamp, and export the difference as a gauge — projection lag is an
      SLI, and it is the one metric that makes CQRS operable. (§4.12) `[X-REF 20]`
2.23.10 **Read-your-writes mitigation 1 — route the writer to the authority.** After a stake settles, serve
      that client's next balance read from `FundsLedger` rather than `BalanceView`, for a bounded window.
      Cost: the hot path occasionally hits the contended store. `[FLOW]`
2.23.11 **Read-your-writes mitigation 2 — version token.** The command response returns the aggregate
      version; the client sends it on the next read; the read side waits (bounded) for the projection to
      reach that version or returns a 409/`Retry-After`. Cost: the contract now carries a version. `[X-REF 12]` `[API]`
2.23.12 **Read-your-writes mitigation 3 — sticky/monotonic reads.** Pin the session to a replica that has
      already applied the write. `RouterInt`'s session affinity for `InternalPlatforms` is the same
      mechanism applied to operator sessions. `[X-REF 22]`
2.23.13 **Read-your-writes mitigation 4 — write-through the projection in the same transaction.** Legal at
      level 2, illegal at level 3+ (two stores, no shared transaction), and this is the exact point where
      the outbox (§2.25) becomes mandatory rather than optional. `[DECIDE]`
2.23.14 **Trap:** CQRS requires event sourcing. It does not, and the confusion is the single most damaging
      one in this area. CQRS needs *some* mechanism to update the read model — a database trigger, a
      materialised view refresh, a change-data-capture stream, a domain event, or a nightly rebuild. Event
      sourcing is one option and the most expensive. The converse *is* true: event sourcing makes CQRS
      mandatory, because you cannot query a log (§2.24). `[TRAP]` `[PROVE]`
2.23.15 **Trap:** the read model treated as authoritative. §9.4 of the scenario states the rule as a hard
      constraint — restrictions may be projected into `ProfileService` and `PendingActions` for *display*,
      and a display projection must never be the input to an authorisation. A stale projection authorising
      a stake for a self-excluded client is the worst outage this system can have. `[TRAP]` `[INCIDENT]`
2.23.16 **Trap:** one read model per screen, forever. Projections are cheap to add and expensive to keep
      correct; each one needs a rebuild procedure, a lag metric and an owner. Count them like you count
      indexes. `[TRAP]`
2.23.17 The projection **rebuild** requirement, which is what makes projections safe to change: a
      projection must be reconstructible from the source of truth at any time, idempotently, while the old
      one still serves traffic. If you cannot rebuild it, you cannot fix a bug in it. `[FLOW]`
2.23.18 The command/query *contract* consequences: commands are named imperatives that may be rejected
      (`ReserveStake` → 202/409), queries are safe, cacheable and idempotent, and the HTTP surface should
      make the distinction visible rather than POSTing everything. `[X-REF 12]` `[SAY]`

*(18 leaves)*

## §2.24 Event sourcing

2.24.1 The claim being made: **the ordered log of state-change events is the system of record, and current
      state is a fold over that log.** Not "we also store events" — that is an audit table, and calling it
      event sourcing is the most common misuse of the term. `[PROVE]` `[TRAP]`
2.24.2 The force that justifies it: the *history itself* is a business asset — regulatory audit, dispute
      resolution, temporal queries ("what was the balance when the stake was placed"), and retroactive rule
      changes. QuizStakes' `ApplicationHistory` (§4.3: append-only, every transition/actor/reason,
      write-once, never lose) is the requirement in the scenario's own words. `[SOURCE]`
2.24.3 Why `FundsLedger` is the natural candidate: double-entry bookkeeping *is already* event sourcing —
      a balanced set of entries appended, never updated, with positions as the fold. §11.1's "a stored
      total is a second source of truth that can disagree with the entries" is the event-sourcing argument
      stated in accounting terms. `[PROVE]` `[SAY]`
2.24.4 **The append-only write.** One `insert` per event, no `update`, no `delete`, and the primary key is
      `(aggregateId, version)` — which makes the unique index the concurrency-control mechanism. (§3.16) `[API]`
2.24.5 **Optimistic concurrency without a version column**: the expected version is part of the append call,
      and a duplicate-key violation on `(aggregateId, version)` *is* the conflict detection. Same guarantee
      as `@Version`, enforced by the index rather than by a `where` clause. `[PROVE]` `[X-REF 08]`
2.24.6 **Replay** — rebuild any aggregate, or any projection, by folding events from version 0. This is
      what makes a projection bug fixable and a new projection addable years later, and it is the single
      capability event sourcing has that nothing else does. `[FLOW]`
2.24.7 **Snapshotting** — persist the folded state at version N so replay starts at N+1. Cadence: the
      commonly cited range is every 100–500 events, tuned against event size and load latency; state the
      number you chose and the load-time budget it defends. `[NUM]` `[RESEARCH]`
2.24.8 The snapshot arithmetic for QuizStakes: 19.8M ledger entries/day at ~180 bytes/row across 2.4M
      clients is ~8 events/client/day, so a per-client position aggregate crosses 500 events in about two
      months — a snapshot cadence of 500 with a nightly snapshotter is sufficient, and *that* is how the
      number is derived rather than copied. `[NUM]` `[PROVE]`
2.24.9 **Snapshots are a cache, not a source of truth.** A snapshot must be deletable and regenerable, and
      any bug fixed by "we corrected the snapshot" has corrupted the system. `[TRAP]`
2.24.10 **Event versioning.** Every event schema ever written must stay deserialisable forever, because
      replay reads events from three years ago. The versioning strategies to name: weak schema (tolerant
      reader), explicit version field, and separate event types per version. `[X-REF 14]`
2.24.11 **Upcasting** — transform an old event's payload into the current shape as it is read, in a chain
      `v1 → v2 → v3`, so handlers only ever see the current version. The alternative, versioned handlers,
      spreads the version knowledge across every consumer. Upcasters are the maintainable choice and they
      are code you maintain for the life of the system. `[API]` `[RESEARCH]`
2.24.12 What upcasting cannot do: add information that was never captured. A v1 `StakeReserved` without the
      bonus/cash split cannot be upcast into one that has it — you can only default, and the default is a
      lie in the audit trail. This is why event payload design is a one-way door. `[TRAP]` `[PROVE]`
2.24.13 **GDPR erasure versus an immutable log.** The right to erasure and an append-only source of truth
      are in direct conflict, and "we just don't delete" is not a compliance position. `[PROVE]`
2.24.14 **Crypto-shredding** as the standard mitigation: encrypt each subject's personal data with a
      per-subject key, store the key separately, and delete the key on an erasure request — the events
      remain, the payload becomes unreadable. Cost: key management, per-subject key rotation, and encrypted
      payloads that plain storage never needed. `[RESEARCH]`
2.24.15 The honest caveat on crypto-shredding: regulators have not uniformly accepted that encrypted
      personal data with a destroyed key is erased, since encrypted personal data is still personal data.
      State it as *the standard mitigation with an unsettled legal status*, and name the alternative —
      keep PII in a separate mutable store (QuizStakes already does: `PersonalDetails` on its own instance
      with its own credentials, encryption and retention) and reference it from the event by id. `[TRAP]` `[RESEARCH]`
2.24.16 **Projections are mandatory.** You cannot query a log — "list this client's withdrawals" is not
      expressible as a fold over one aggregate's stream. Therefore event sourcing implies CQRS, and the
      read side's cost is part of event sourcing's cost, not a separate decision. `[PROVE]`
2.24.17 The operational surface event sourcing adds, enumerated so it can be priced: a projection rebuild
      runbook, a lag metric per projection, an upcaster test suite, a snapshot job, log growth and archival,
      and a "how do we fix a bad event" procedure (compensating event — never an update). `[TABLE]`
2.24.18 **The compensating event** as the only legal correction mechanism: a wrong `BonusGranted` is
      corrected by `BonusClawedBack`, not by editing history. §11.4's clawback shortfall path
      (unspent bonus first, remainder to `PROMOTIONAL_EXPENSE`) is a compensating-event design already. `[SAY]`
2.24.19 **`[DECIDE]` — the small set of cases where event sourcing pays**: (a) the audit trail is a
      regulatory deliverable and must be complete and tamper-evident; (b) the domain is already an
      append-only ledger; (c) temporal queries are a product feature; (d) retroactive recalculation is a
      business requirement. **Do not use it when** the requirement is "we might want history one day", when
      the team has never operated a projection, or when an audit table plus a change log satisfies the
      actual ask — which it usually does. `[DECIDE]`
2.24.20 **Trap:** adopting event sourcing because the architecture is event-*driven*. Event-driven
      communication (how services talk) and event sourcing (how one service persists) are independent
      decisions, and QuizStakes shows the split cleanly: the dotted arrows of §5 are event-driven, while
      only `FundsLedger` and `ApplicationHistory` have an event-sourcing case. `[TRAP]`

*(20 leaves)*

## §2.25 Integration and decomposition patterns — each stating the failure it prevents

2.25.1 **Transactional outbox** — prevents *the dual-write failure*: a database commit and a message
      publish cannot be atomic, so a crash between them either loses the event or announces a state that
      was rolled back. Mechanism: insert the event into an `outbox` table in the *same* transaction as the
      state change; a relay reads and publishes it afterwards. (§3.17) `[X-REF 14]`
2.25.2 Outbox relay mechanics to name: polling (`select ... where published_at is null order by id limit N
      for update skip locked`) versus change-data-capture on the transaction log; ordering by a monotonic
      sequence; consumer-side dedup by event id; and at-least-once delivery meaning the relay must be
      idempotent, not exactly-once. `[API]` `[X-REF 14]`
2.25.3 The outbox's cost, stated: one extra insert on every write path (on `FundsLedger`'s 13,600/sec peak
      that is 13,600 extra inserts/sec), a table that must be pruned, and a relay that is a new thing to
      monitor for lag. `[NUM]`
2.25.4 **Saga** — prevents *the distributed-transaction requirement*: there is no ACID transaction across
      `FundsLedger`, `BankWithdrawal` and the banking partner, so the business transaction becomes a
      sequence of local transactions with compensation. `[X-REF 14]`
2.25.5 **Orchestration** — a central coordinator (a saga orchestrator, e.g. `PaymentService`) tells each
      participant what to do and holds the state machine. Buys workflow visibility and centralised error
      handling; costs a coordinator that knows everyone. `[DECIDE]`
2.25.6 **Choreography** — each participant reacts to events and emits its own, with no coordinator. Buys
      decoupling; costs the ability to answer "where is withdrawal 4471 in its flow" without a trace, and
      makes cyclic dependencies easy to create accidentally. `[DECIDE]`
2.25.7 **Compensating action** — the semantic inverse of a completed step, not a rollback. `VoidStake`
      returning reserved funds *to their original buckets* (§2 of the scenario: bonus back to bonus, cash
      back to cash) is a compensating action whose correctness depends on the win/void asymmetry of §11.3. `[PROVE]`
2.25.8 The saga transaction taxonomy: **compensatable** transactions (can be undone), the **pivot**
      transaction (the go/no-go point — once it commits the saga must run to completion), and **retriable**
      transactions (after the pivot, guaranteed to eventually succeed). For a bank withdrawal, file
      submission to the banking partner is the pivot: past it, there is no compensation, only a return. `[RESEARCH]` `[DECIDE]`
2.25.9 **Semantic lock** — prevents *dirty reads between concurrent sagas*: a compensatable transaction
      marks the record it touched as pending (`CLIENT_CASH_RESERVED` rather than a decremented available
      balance), so other readers can see the money is committed-but-not-final. The scenario's
      reserved-positions model is a semantic lock built into the ledger. `[RESEARCH]` `[PROVE]`
2.25.10 The other saga countermeasures by name: **commutative updates** (design steps so order does not
      matter), **pessimistic view** (reorder steps so the risky update happens last), **reread value**
      (re-check before overwriting, an optimistic-offline-lock), **version file** (record out-of-order
      operations and reorder them), **by value** (route high-risk requests to a distributed transaction and
      low-risk ones to a saga). `[RESEARCH]` `[TABLE]`
2.25.11 **API composition** — prevents *the cross-service join*, which §5.1 rule 4 of the scenario forbids
      outright. Mechanism: an aggregator calls N owners and merges in memory. `ProfileService` over eight
      owners is the instance. `[X-REF 22]`
2.25.12 API composition's three named costs, all visible in §7.3: ordering must be imposed *after* the
      merge so pagination across two schemas is genuinely hard; availability multiplies across the fan-out;
      and the slowest owner sets the latency. `[PROVE]` `[NUM]`
2.25.13 **CQRS across services** — prevents *the fan-out cost of API composition on a hot path*: replace
      the runtime join with a maintained projection. `BalanceView` exists because the balance read (every
      screen, before every stake preview, 80 ms budget) cannot afford a fan-out. The trade is the
      projection's staleness. (§2.23) `[DECIDE]`
2.25.14 **Backend for frontend (BFF)** — prevents *one API serving two clients badly*: a per-client-type
      edge that aggregates and reshapes. `ApplicationGateway` (client edge, terminates TLS, strips the
      client token) and `InternalPlatforms` (operator edge, additionally checks roles) are two BFFs over
      the same services, and §6.3's table is the difference between them. `[X-REF 12]`
2.25.15 **API gateway** — prevents *every client knowing the internal topology*. Owns routing, inbound rate
      limiting, token verification and exchange — and per §4.1 owns *no* business state and no
      authorisation decision beyond token validity. That "must not own" column is what stops a gateway
      becoming a god service. `[X-REF 13]`
2.25.16 The gateway-vs-BFF distinction as one leaf: a gateway is *one* edge for *all* clients concerned with
      cross-cutting transport concerns; a BFF is *one edge per client type* concerned with payload shape.
      A single component can be both, and calling it a gateway hides the second responsibility. `[TRAP]`
2.25.17 **Anti-corruption layer** — prevents *a vendor's model leaking into yours*. `DocumentVerification`
      wrapping identity vendors and `BankDeposits` translating the statement file are the instances, and
      §5.1 rule 3 ("every external vendor sits behind exactly one owning service") is the ACL rule stated
      as an architecture constraint. (§2.20)
2.25.18 The ACL's measurable benefit: vendor churn is a one-module change. The test is mechanical — grep for
      the vendor's package outside the owning service; a single hit is a leak. (§2.29) `[PROVE]`
2.25.19 **Strangler fig** — prevents *the big-bang rewrite*. Mechanism: put a façade in front of the legacy
      system, route one capability at a time to the new implementation, and let the new system grow around
      the old until the old one is dead. Fowler, 2004; the metaphor is a fig that germinates in the host's
      branches and roots down around it. `[SOURCE]`
2.25.20 Strangler fig's preconditions, which is where it actually fails: you need an interception point
      (the façade), a way to route per capability, and the ability to run both systems against the same
      data or to split the data cleanly. Without the third, the pattern stalls at the first shared table. `[TRAP]`
2.25.21 **Branch by abstraction** — the in-code equivalent, for a replacement too large for one commit.
      Introduce an abstraction over the component, route all callers through it, build the new
      implementation behind a flag, migrate callers environment by environment then cohort by cohort,
      delete the old implementation, then remove the abstraction if it has no second implementation. Trunk
      stays green throughout. (§2.16) `[FLOW]`
2.25.22 **Parallel run** — prevents *cutting over on hope*. Call both implementations, return the old
      result, compare and log the difference, and cut over only when the divergence rate reaches your
      threshold. The `FundsLedger` case: run the new bonus-split calculation alongside the old for a week
      and assert both legs sum to the stake on every one of 2.8M daily reservations. `[NUM]` `[DECIDE]`
2.25.23 Parallel run's costs: double the downstream load (illegal against a PSP with side effects — you can
      parallel-run a *calculation*, not an *authorisation*), a comparison harness, and a decision about
      which result is authoritative during the run. `[TRAP]`
2.25.24 **Expand and contract (parallel change)** — the schema/API equivalent: add the new field or
      endpoint, write both, migrate readers, stop writing the old, remove it. Four deploys, never a
      breaking one. `[X-REF 12]`
2.25.25 **Sidecar** — prevents *reimplementing a cross-cutting concern per language and per service*. A
      co-located process handles TLS, retries, discovery and telemetry outside the app. Cost: an extra hop,
      extra memory per pod, and a second process to debug. `[X-REF 19]`
2.25.26 **Ambassador vs adapter vs sidecar**, disambiguated because they are routinely merged: *sidecar* is
      the deployment shape (co-located helper); *ambassador* is a sidecar that proxies the app's **outbound**
      calls; *adapter* (a.k.a. adapter/interface sidecar) is a sidecar that normalises the app's
      **inbound**-facing surface, most often metrics and health, into a standard the platform expects. `[TABLE]` `[RESEARCH]`
2.25.27 **Shared nothing** — prevents *a coordination bottleneck*: no shared mutable state between
      instances, so instances scale linearly and any instance serves any request. §6.4's honest caveat is
      the leaf worth carrying: partition affinity for `FundsLedger` buys nothing for correctness (the
      database serialises writes through position version columns regardless) and exists purely for
      in-memory state locality — and it costs the rebalancing problem when 3 instances become 4. `[PROVE]` `[TRAP]`
2.25.28 **The "shared database" tell** — the definitive diagnostic for a distributed monolith. It makes the
      schema a public API that no one owns, so any service's migration can break another, and independent
      deployability — the only unique benefit of decomposition — is gone. §7.2's rule ("no cross-schema
      joins, ever") exists precisely because a shared *instance* makes them physically possible. `[TRAP]` `[SAY]`
2.25.29 The other distributed-monolith diagnostics as a checklist: do two services write the same table;
      does a feature require a coordinated release; is there a service whose only job is to read another's
      data; does one use case fan out across five services in serial. Any yes means the boundary is wrong. `[DECIDE]`
2.25.30 Where transport and topology are owned rather than re-taught: message brokers, delivery semantics,
      partitions, consumer groups and ordering are `[X-REF 14]`; cross-service topology, CAP/PACELC,
      partitioning, quorum and capacity arithmetic are `[X-REF 22]`. This section owns the *pattern* and
      the failure it prevents; those guides own the mechanism. `[X-REF 14]` `[X-REF 22]`

*(30 leaves)*

## §2.26 Resilience patterns, indexed by the failure they were invented for

2.26.1 The table's contract and the reading order: **failure → pattern → mechanism → the parameter that is
      always wrong → what the pattern does *not* fix.** Indexed by failure, because in an interview the
      question is always a symptom, never a pattern name. `[TABLE]` `[SAY]`
2.26.2 The provenance leaf: most of this catalogue is Nygard, *Release It!* (2e), whose **stability
      patterns** are Timeouts, Circuit Breaker, Bulkheads, Steady State, Fail Fast, Let It Crash,
      Handshaking, Test Harnesses, Decoupling Middleware, Shed Load, Create Back Pressure, and Governor.
      Name the twelve; three of them (Let It Crash, Handshaking, Governor) are almost never taught and are
      free marks. `[SOURCE]` `[RESEARCH]`
2.26.3 The companion list — Nygard's **stability anti-patterns**: Integration Points, Chain Reactions,
      Cascading Failures, Users, Blocked Threads, Self-Denial Attacks, Scaling Effects, Unbalanced
      Capacities, Dogpile, Force Multiplier, Slow Responses, Unbounded Result Sets. Every pattern above
      exists to defeat a named member of this list, and pairing them is the strongest way to teach both. `[TABLE]` `[RESEARCH]`
2.26.4 **Retry** — failure: a transient blip (a dropped connection, a leader election, a brief 503).
      Mechanism: bounded attempts with exponential backoff. Parameter always wrong: no total attempt
      budget, so a 3-retry policy three layers deep is 27 calls. (§4.7) `[API]`
2.26.5 **Jitter** — failure: the *retry wave*. Without randomisation, every client that failed at T retries
      at T+1s together, producing a synchronised thundering herd on a recovering dependency. Mechanism:
      full jitter — `sleep = random(0, min(cap, base * 2^attempt))`. `[NUM]` `[X-REF 15]`
2.26.6 **Retry amplification / retry storm** — failure: retries multiplying load on a *struggling* (not
      dead) dependency until it dies. The arithmetic: a dependency at 80% capacity, given a 3× retry
      multiplier, receives 240% of capacity — the retry causes the outage. Mitigations: retry budgets (cap
      retries at a percentage of total requests), and retrying only at the outermost layer. `[PROVE]` `[NUM]`
2.26.7 **Trap:** retrying non-idempotent operations. Retrying a card authorise against a PSP with an 11 s
      p99 double-charges the client. Retry requires idempotency, and idempotency requires a key (2.26.16). `[TRAP]` `[NUM]`
2.26.8 **Trap:** retrying a 4xx. A 400 will fail identically forever; a 409 may or may not; a 429 must be
      retried only after `Retry-After`. Retry classification is per status code, not per exception type. `[TRAP]` `[X-REF 12]`
2.26.9 **Timeout** — failure: waiting forever, holding a thread, a connection and a database transaction.
      Mechanism: bound every remote call, and make the timeout **budget shrink** down the call chain so an
      inner timeout is always shorter than its caller's remaining budget. Parameter always wrong: an inner
      timeout longer than the outer one, which makes the inner one dead code. `[PROVE]`
2.26.10 The QuizStakes timeout arithmetic: a 30 ms restriction budget and a 500 ms hard self-exclusion
      budget mean the `ClientRestrictions` call inside the stake path cannot be given a 1 s socket timeout
      "to be safe" — the default that seems conservative is the one that breaks the SLO. `[NUM]` `[PROVE]`
2.26.11 **Circuit breaker** — failure: a dead or slow dependency consuming all caller threads on timeouts,
      turning its outage into yours (Nygard's *cascading failure*). Mechanism: count failures over a sliding
      window; **open** → fail fast without calling; after a wait duration **half-open** → allow a limited
      number of probe calls; success → **closed**, failure → **open**. (§3.15) `[API]`
2.26.12 The three states named exactly, plus Resilience4j's two additional ones — `DISABLED` and
      `FORCED_OPEN` — and the shape of the configuration surface: a window (count- or time-based) sized in
      calls or seconds, a minimum call count before the rate is evaluated at all, a failure-rate threshold,
      a *slow*-call rate and duration threshold, a wait duration in the open state, and a permitted probe
      count in half-open. **§3.15 is the single authority for the property names, their exact spellings and
      their documented defaults** — do not restate them here, and treat any default quoted in a tuning
      example as a chosen value rather than the library's. `[RESEARCH]`
2.26.13 **The open-state response requirement**: a breaker with no defined behaviour when open has only
      converted a slow failure into a fast one. Decide what open *returns* — a cached value, a degraded
      response, a 503 with `Retry-After`, or a queued command. For a self-exclusion check the only legal
      open-state answer is **deny**, because failing open would let a self-excluded client stake. `[DECIDE]` `[PROVE]`
2.26.14 **Bulkhead** — failure: one slow dependency exhausting a shared thread pool and taking down
      unrelated endpoints. Mechanism: a separate pool or semaphore per dependency. Parameter always wrong:
      the sum of all bulkheads exceeding what the box can run — each must be sized so all of them together
      fit. (§4.8) `[NUM]`
2.26.15 **Rate limiter** — failure: one caller consuming capacity that belongs to everyone. Mechanism: token
      bucket per key, at the edge (`ApplicationGateway` owns inbound rate limiting per §4.1). Distinguish
      *rate limiting* (a contractual quota, per client) from *load shedding* (a survival reflex, global). `[X-REF 12]`
2.26.16 **Load shedding** — failure: overload degrading everyone instead of rejecting some. Mechanism: drop
      the lowest-priority work first, and drop it *early*. The argument for shedding over queueing:
      a request that has already exceeded its deadline is wasted work, so serving it steals capacity from
      a request that could still succeed. `[PROVE]`
2.26.17 **Backpressure** — failure: a fast producer overwhelming a slow consumer. Mechanism: a **bounded**
      queue, so the producer blocks or is rejected and the pressure propagates to the source. `[X-REF 05]`
2.26.18 The leaf that must be its own: **an unbounded queue converts backpressure into an OOM.** A
      `ThreadPoolExecutor` with an unbounded `LinkedBlockingQueue` never creates threads beyond core size
      and never rejects, so overload is invisible until the heap dies — a 6 GB `BankWithdrawal` instance
      quietly accumulating a 500k-record month-end backlog is the concrete shape. `[TRAP]` `[NUM]` `[X-REF 05]`
2.26.19 **Hedged request** — failure: tail latency from an unlucky replica. Mechanism: after p95 elapses,
      send a duplicate request to a second replica and take the first response. Costs a bounded amount of
      extra load (typically ~5%) and is only legal for idempotent reads. `[NUM]` `[DECIDE]`
2.26.20 **Fallback, graceful degradation, and dead letter** as one leaf each on the failure they answer:
      *fallback* — the dependency is down but a stale or default answer is acceptable (a `BalanceView`
      cached balance for display, never for a stake decision); *graceful degradation* — shed a feature to
      keep the core path alive (disable bonus preview, keep stake reservation); *dead letter* — a message
      that cannot be processed must leave the queue with its failure reason, or it blocks the partition
      forever. `[X-REF 14]`
2.26.21 **Idempotency key enforced by a unique index** — failure: at-least-once delivery and client retries
      producing duplicate side effects. Mechanism: the client supplies a key, the server stores
      `(key, response)` under a **unique constraint** in the same transaction as the effect, and replays
      the stored response on a repeat. **Trap:** check-then-insert is a race; the unique index *is* the
      mechanism, and the duplicate-key exception is the happy path. (§4.9) `[TRAP]` `[X-REF 12]`
2.26.22 **Fail fast, steady state, and the one-policy rule.** *Fail fast* — validate everything you can
      before consuming a remote resource, so overload rejects cheaply. *Steady state* — every accumulation
      needs a reaper (outbox rows, event log archival, reservation expiry indexes, log files); a system
      that requires human intervention to keep running has none. And the rule that ties the section
      together: **retry, timeout and circuit breaker are one policy tuned together** — the breaker must
      count retried attempts, retries must be bounded before the breaker sees them, and the total retry
      budget must fit inside the caller's timeout. `[PROVE]` `[TRAP]` `[SAY]`

*(22 leaves)*

## §2.27 Concurrency patterns, and how Java 21 reshapes them

2.27.1 The provenance leaf: the catalogue is Schmidt et al., **POSA volume 2** (*Patterns for Concurrent and
      Networked Objects*), 17 patterns — Wrapper Facade, Acceptor-Connector, Extension Interface,
      Interceptor, Component Configurator, Reactor, Proactor, Asynchronous Completion Token, Scoped Locking,
      Strategized Locking, Thread-Safe Interface, Double-Checked Locking Optimization, Active Object,
      Monitor Object, Leader/Followers, Half-Sync/Half-Async, Thread-Specific Storage. Use POSA's names,
      not blog paraphrases. `[SOURCE]` `[RESEARCH]`
2.27.2 **Reactor** — failure it answers: thread-per-connection exhausting memory at 10k connections.
      Mechanism: one (or few) threads block on a readiness demultiplexer (`epoll`/`kqueue`, in Java
      `Selector.select()`), then dispatch to non-blocking handlers. Absolute constraint: a handler must
      never block. `[API]`
2.27.3 **Proactor** — the completion-based twin: the OS performs the I/O and notifies on *completion*
      rather than readiness. Java's `AsynchronousSocketChannel` + `CompletionHandler` is the proactor
      shape; `Selector` is the reactor shape. Naming both, and the readiness-vs-completion distinction, is
      the discriminating answer. `[API]`
2.27.4 **Asynchronous Completion Token** — how a completion handler knows which request completed: the
      initiator attaches state to the async call and gets it back with the completion. The `attachment`
      parameter of `AsynchronousSocketChannel.read(buffer, attachment, handler)` is the ACT, by name. `[API]`
2.27.5 **Half-sync / half-async** — failure: reactor handlers need to do blocking work. Mechanism: an async
      layer (the event loop) and a sync layer (a worker pool), separated by a **queueing layer**. Netty's
      boss/worker split is exactly this, and the queue between the layers is where backpressure must live. `[X-REF 05]`
2.27.6 **Leader/Followers** — failure: the hand-off cost of half-sync/half-async (a queue, a context switch,
      cache-line migration of the request data). Mechanism: a pool of threads takes turns being the single
      thread that waits on the demultiplexer; the leader promotes a follower before processing, so the
      request is handled by the thread that received it. Eliminates the queue and the hand-off. `[PROVE]`
2.27.7 **Active object** — failure: callers blocking on a method that must be serialised. Mechanism:
      decouple method *invocation* from method *execution* — a proxy enqueues a method request into a
      scheduler running on the object's own thread, and the caller gets a future. Java shape: a
      single-thread `ExecutorService` owned by the object, returning `CompletableFuture`. `[API]`
2.27.8 **Monitor object** — failure: concurrent access to one object's state. Mechanism: methods are
      serialised by the object's own lock, and callers wait on condition variables inside it. Java's
      `synchronized` + `wait`/`notifyAll` *is* the monitor object, built into the language — which is why
      Java programmers use the pattern without knowing its name. `[X-REF 05]`
2.27.9 Active object vs monitor object, disambiguated: the monitor runs the method **on the caller's
      thread** while holding a lock; the active object runs it **on its own thread** and returns
      immediately. Blocking versus asynchronous, same serialisation guarantee. `[TABLE]`
2.27.10 **Thread-specific storage** — failure: passing per-request context through every signature.
      Mechanism: a key that resolves to a different value per thread. `ThreadLocal`, and the leak: a
      long-lived pooled thread holds the last request's value forever, which is the cross-request data leak
      (one client's id visible in another's request). `[X-REF 05]` `[TRAP]`
2.27.11 **Guarded suspension** — failure: a method called when its precondition does not yet hold.
      Mechanism: block until the guard is satisfied (`while (!condition) wait();` — the `while`, not `if`,
      because of spurious wakeups). `BlockingQueue.take()` is guarded suspension. `[API]` `[X-REF 05]`
2.27.12 **Balking** — the opposite choice for the same situation: if the precondition does not hold, return
      immediately and do nothing rather than wait. `AtomicBoolean.compareAndSet(false, true)` guarding a
      once-only `PaymentRun` submission is balking; a second operator click does nothing instead of
      queueing. `[API]`
2.27.13 Guarded suspension vs balking as a `[DECIDE]`: block when the caller must eventually get the
      result and the wait is bounded; balk when the operation is idempotent-by-doing-nothing and a queue of
      waiting callers would itself be the problem. `[DECIDE]`
2.27.14 **Producer–consumer** — failure: a fast producer and a slow consumer. Mechanism: a bounded queue
      decouples their rates and makes the pressure explicit. Parameter always wrong: the queue bound (see
      §2.26.18). `[X-REF 05]`
2.27.15 **Thread pool** — failure: unbounded thread creation, and the per-thread ~1 MB stack reservation
      that makes 10k platform threads impossible in a 4 GB heap. Mechanism: a fixed set of workers pulling
      from a queue. `ThreadPoolExecutor`'s counter-intuitive ordering rule: it grows past `corePoolSize`
      only when the queue is **full**, so an unbounded queue means `maximumPoolSize` is never reached. `[NUM]` `[TRAP]` `[X-REF 05]`
2.27.16 **Immutable object** — failure: shared mutable state, in every form. Mechanism: no state changes
      after construction, so no synchronisation is needed and safe publication is guaranteed by final-field
      semantics. Java 21 shape: `record`, plus `List.copyOf`/`Map.copyOf` in the compact constructor to
      close the shallow-immutability gap. (§3.14)
2.27.17 **Disruptor / ring buffer** — failure: queue contention and allocation at the top of the throughput
      range. Mechanism: a pre-allocated power-of-two ring buffer, sequence numbers instead of locks,
      cache-line padding to prevent false sharing, and consumers tracking their own sequence. Named because
      it is the answer to "how do you go faster than `ArrayBlockingQueue`", and the honest follow-up is that
      almost nothing in a Spring service needs it. `[X-REF 25]` `[DECIDE]`
2.27.18 **Java 21 reshaping — virtual threads retire the reactor-for-scalability argument.** Reactor exists
      because a platform thread per connection costs ~1 MB of stack and a kernel scheduling entity; a
      virtual thread costs a heap-allocated continuation that grows on demand. Blocking a virtual thread
      unmounts it from its carrier, so thread-per-request scales to hundreds of thousands of connections
      *while staying blocking and debuggable*. `[VERSION-TRAP]` `[X-REF 05]`
2.27.19 What virtual threads do **not** retire, stated so the previous leaf is not over-claimed: they do not
      remove the need for bulkheads and rate limits (unbounded concurrency now means unbounded *downstream*
      load), they do not help CPU-bound work, and **pinning** — a virtual thread inside a `synchronized`
      block or a native frame cannot unmount — reintroduces the blocking problem. `[VERSION-TRAP]` `[TRAP]` `[X-REF 05]`
2.27.20 **Structured concurrency** (`StructuredTaskScope`, `Subtask`, `joinUntil`, and the
      `ShutdownOnFailure`/`ShutdownOnSuccess` policies of the preview API) reshapes fan-out: `ProfileService`
      calling eight owners becomes one scope with one deadline and automatic cancellation of siblings on
      first failure, replacing hand-rolled `CompletableFuture.allOf` + timeout + cancel bookkeeping.
      State the exact API shape against the baseline and mark the JDK 22–25 signature changes. `[API]` `[VERSION-TRAP]`
2.27.21 **Scoped values** (`ScopedValue.where(...).run(...)`) reshape thread-specific storage: immutable,
      bounded to a dynamic scope, inherited by structured-concurrency subtasks, and impossible to leak into
      a pooled thread — the direct replacement for `ThreadLocal` in a virtual-thread world where pooling
      threads is an anti-pattern anyway. `[API]` `[VERSION-TRAP]`
2.27.22 Where the semantics live rather than being re-taught: happens-before, `volatile`, safe publication,
      CAS, `ThreadPoolExecutor` queueing order, `CompletableFuture`, virtual-thread pinning and
      `ThreadLocal` leaks are all `[X-REF 05]`. This section owns the *pattern reading* of them — which
      named pattern each JDK construct implements, and which failure it was invented for. `[X-REF 05]`

*(22 leaves)*

## §2.28 The testability consequence of each pattern, and the test double it implies

2.28.1 The framing leaf: **testability is a design property, not a testing activity.** Every pattern in §1
      either creates a seam a test can substitute at or removes one, and the fastest review question for a
      design is "what would I have to stand up to test this in isolation". `[SAY]`
2.28.2 The five test doubles by Meszaros' names, because the industry uses them interchangeably and the
      distinction is a real interview discriminator: **dummy** (passed to satisfy a signature, never used),
      **stub** (returns canned answers to drive the test down a path), **spy** (a stub that additionally
      records the calls made, asserted afterwards), **mock** (has expectations set *before* execution and
      fails on an unexpected or missing call), **fake** (a real but simplified working implementation —
      an in-memory repository, H2 for Postgres). `[TABLE]` `[SOURCE]`
2.28.3 The state-vs-interaction axis that actually decides which one: stub and fake support **state
      verification** (assert on the result), spy and mock support **behaviour verification** (assert on the
      calls). Choose interaction verification only when the interaction *is* the requirement — "the outbox
      row was written" — and state verification everywhere else. `[DECIDE]`
2.28.4 Mockito's mapping onto those names, stated precisely because it blurs them: `mock()` produces
      something that behaves as a stub or a spy depending on whether you `when(...)` or `verify(...)`;
      `spy()` wraps a real object for partial stubbing; there is no separate dummy or fake construct. `[API]` `[X-REF 16]`
2.28.5 **Constructor injection is the testability lever**, and the mechanism is that the constructor
      signature is an *enumeration of the collaborators*. A test cannot forget to supply one, the compiler
      lists them, and a growing list is visible design feedback. Field injection removes all three
      properties. `[PROVE]` `[X-REF 07]`
2.28.6 **The static singleton is untestable, and here is exactly why**: `RateTable.getInstance()` is a
      dependency that appears in no signature, so a test has no substitution point; the instance is
      JVM-global, so state leaks between tests and makes them order-dependent; and the
      class-initialisation lock means the instance is created once per classloader, so there is no reset. A
      Spring singleton-*scoped bean* has none of these properties — it is an injected dependency with one
      instance per container. (§1.10) `[PROVE]`
2.28.7 **Strategy / DIP-shaped patterns** — best case for testability: the collaborator is an interface, the
      double is a stub, and the unit test needs no framework. This is the testability argument for
      hexagonal, stated as a mechanism rather than a preference. (§1.20)
2.28.8 **Template method** — worst case among the behavioural patterns: testing a hook means instantiating a
      subclass, so tests are coupled to the inheritance hierarchy, and the base class's `final` skeleton
      cannot be stubbed out. The fix is the same as the design fix — prefer composition. `[TRAP]`
2.28.9 **Decorator** — the easiest pattern in the catalogue to test: construct it around a stub delegate and
      assert the added behaviour plus the delegation. A retry decorator's test is "delegate throws twice,
      then succeeds; assert three calls and one result". (§1.16)
2.28.10 **Proxy and AOP** — the hardest, because the behaviour under test does not exist until the container
      wires it. Consequences: `@Transactional` and `@Cacheable` semantics cannot be unit-tested at all, the
      self-invocation bypass is invisible to a unit test and only appears in an integration test, and
      therefore proxy-based concerns need a slice test by construction. `[TRAP]` `[X-REF 07]`
2.28.11 **Observer** — needs a spy on the listener and a fake publisher, and the failure modes that matter
      (after-commit ordering, listener exceptions rolling back the publisher) are only reachable with a
      real transaction. `@TransactionalEventListener(phase = AFTER_COMMIT)` is untestable without one. (§3.19)
2.28.12 **Repository / aggregate** — the in-memory **fake** is the highest-value double in a domain-heavy
      codebase: a `Map`-backed `LedgerRepository` lets every domain test run in microseconds with no
      Testcontainer, and the JPA implementation is covered once by an integration test. State the boundary:
      a fake proves domain logic, never SQL. `[DECIDE]` `[X-REF 16]`
2.28.13 **Factory / builder** — testability is *why* they exist as much as ergonomics: a builder with sane
      defaults means a test names only the two fields it cares about, and a test-data builder is the
      standard cure for 200 lines of fixture setup. (§1.9)
2.28.14 **Trap: do not mock types you do not own.** Mocking the PSP SDK's client encodes your *belief* about
      its behaviour, and a green test against a wrong belief is worse than no test — the 11 s p99, the
      partial-failure modes and the retry semantics are all guesses. The correct shape is the one QuizStakes
      already mandates (§5.1 rule 3): wrap the vendor in an owned port, mock the *port*, and verify the
      adapter against the real thing with a contract test or a recorded fixture. `[TRAP]` `[X-REF 16]`
2.28.15 The corollary trap — **over-mocking**: a test with six mocks asserts the implementation's call
      sequence, so any refactoring breaks it while any behaviour change passes. The count of mocks in a test
      is a design metric; six mocks means the class under test has six collaborators, and *that* is the
      finding. `[TRAP]` `[SAY]`

*(15 leaves)*

## §2.29 Enforcement — ADRs, fitness functions, ArchUnit, JPMS, and the build file

2.29.1 The premise: **an architecture that is not enforced by a failing build is a suggestion.** Every
      boundary rule in §2.17–§2.25 either has a mechanical check or erodes, and the erosion is invisible
      until a feature costs five times its estimate. `[SAY]`
2.29.2 **ADR (architecture decision record)** — the format: Title, Status (proposed / accepted / deprecated
      / superseded by ADR-NNN), Context, Decision, Consequences. Numbered, immutable once accepted,
      superseded rather than edited, and stored in the repository next to the code so it moves with it. `[API]`
2.29.3 When a decision needs an ADR — the `[DECIDE]` rule: it is expensive to reverse, it constrains other
      teams, it was contested, or a future reader will otherwise ask "why on earth". Explicit "do not write
      one when": the decision is local, cheap to reverse, and has no external constraint — an ADR per
      library choice is how the practice dies. `[DECIDE]`
2.29.4 What an ADR is *for*, mechanically: it preserves the **context that made the decision correct**, so
      a successor can tell "still right" from "was right then". Without it, every inherited constraint looks
      arbitrary and gets removed by someone who does not know what it was defending. `[PROVE]`
2.29.5 **Fitness function** — Ford/Parsons/Kua's term: an objective, automated assessment of an
      architectural characteristic. Types to name: *atomic* (one characteristic, e.g. a package
      dependency rule) vs *holistic* (several interacting, e.g. latency under a security-scanning load);
      *triggered* (runs in CI) vs *continuous* (runs in production, e.g. a chaos experiment). `[SOURCE]`
2.29.6 The reframe worth stating out loud: **an ArchUnit test is a fitness function, and so is a p99 latency
      assertion in a load test, and so is a build-time dependency check.** The term is not a new tool; it
      is the name for treating an architectural rule as a test. `[SAY]`
2.29.7 **ArchUnit rule shape 1** — `classes().that().resideInAPackage("..domain..")
      .should().onlyDependOnClassesThat().resideInAnyPackage("..domain..", "java..")`. This is the
      hexagonal rule, expressed as a test, and it is the answer to "how do you *know* the domain is clean". `[API]` `[BUILD]`
2.29.8 **ArchUnit rule shape 2** — `noClasses().that().resideInAPackage("..domain..")
      .should().dependOnClassesThat().resideInAnyPackage("jakarta.persistence..",
      "org.springframework..")`. The negative form is the one that catches the framework leak, and
      `noClasses()` exists precisely because the positive form's allow-list is unmaintainable. `[API]` `[BUILD]`
2.29.9 **ArchUnit rule shape 3** — `slices().matching("com.quizstakes.(*)..")
      .should().beFreeOfCycles()`. The `(*)` marks the captured package segment used as the slice
      identifier; this single rule is the whole of §6.4 (circular dependencies) made mechanical. `[API]` `[BUILD]`
2.29.10 **ArchUnit rule shape 4** — the predefined architecture builders: `layeredArchitecture()
      .consideringAllDependencies().layer("Domain").definedBy("..domain..")
      .whereLayer("Domain").mayOnlyBeAccessedByLayers("Application")`, and `onionArchitecture()
      .domainModels(..).domainServices(..).applicationServices(..).adapter("psp", ..)`. Note the
      `consideringAllDependencies()` / `consideringOnlyDependenciesInLayers()` switch — the default
      changed across versions and a rule that passes for the wrong reason is worse than no rule. `[API]` `[VERSION-TRAP]`
2.29.11 **ArchUnit rule shape 5** — `FreezingArchRule.freeze(rule)`: records existing violations to a
      `ViolationStore` on first run (which therefore always passes) and fails only on *new* ones. This is
      the only way to introduce a rule into a legacy codebase without a 4,000-violation red build, and the
      violation store is a committed file that shrinks over time. `[API]` `[RESEARCH]`
2.29.12 The ArchUnit failure report read line by line: the rule text as written, then one line per
      violating dependency with the exact source class, target class, member and **line number**. It is a
      real artefact and reading one is what convinces a reader the rule is not magic. `[DIAG]`
2.29.13 The one property of ArchUnit a *rule author* must know, because it decides which rules are worth
      writing: rules are evaluated over the **bytecode** class graph, so a dependency that exists only
      through reflection, a string-configured bean name or SpEL is invisible to every rule above. Write
      rules against types, never against wiring. Importer and evaluation mechanics: §3.20. `[PROVE]` `[DECIDE]`
2.29.14 **The enforcement ladder, and where a module boundary sits on it** — convention (a code-review
      norm; zero enforcement), package-private (compiler-enforced, but does not nest, §2.19.6), ArchUnit
      (enforced by a test, and a test can be `@Disabled`), build module (a framework import is a compile
      error), JPMS (unreachable even by reflection). The `[DECIDE]` rule: climb only as far as the rule's
      blast radius justifies, because each rung costs restructuring — and a domain build module is the
      right rung for almost every service, with JPMS reserved for a published library. `exports`,
      `requires transitive`, `opens`, `--add-exports` and `jdeps` mechanics: §3.20. `[DECIDE]` `[X-REF 06]`
2.29.15 **The build-file test** — the simplest and strongest check in this section: *the domain module's
      build file has no framework dependency*. A separate Gradle/Maven module for `domain` with no
      `spring-boot-starter`, no `jakarta.persistence`, no Jackson means a framework import is a
      **compile error** rather than a test failure, and it is the verification for §2.17.4–7 that needs no
      tooling at all. `[BUILD]` `[SAY]`

*(15 leaves)*

## §2.30 The cost model — what every pattern charges, and the evolution ladder

2.30.1 The premise, stated as the section's thesis: **indirection must be paid for by a variation that
      exists.** Every leaf below is a line item on the invoice, and a candidate who can itemise it is the
      one who can also reject a pattern. `[SAY]`
2.30.2 **One more file to read.** The dominant cost of most patterns is not runtime, it is the number of
      hops between "where the request arrives" and "where the money moves". Measure it as *indirection
      depth* on the hot path, and state the number: a strategy behind a factory behind a facade is three
      hops to answer "what actually happens here". `[NUM]` `[PROVE]`
2.30.3 **One more allocation.** A wrapper, a parameter object, a value object per field, a `Optional` per
      return. Usually free — escape analysis and scalar replacement remove the allocation when the object
      does not escape — and *not* free when it does escape, or when the method is too large to inline, or
      when the allocation rate itself becomes the latency source. `[X-REF 06]` `[X-REF 25]`
2.30.4 **One more virtual call, and the inline-cache cost curve.** A monomorphic call site is inlined to
      nothing; bimorphic is a cheap type check; **megamorphic** degrades to a vtable/itable dispatch with
      no inlining, which also blocks every optimisation that inlining would have enabled. (§3.1) `[X-REF 06]`
2.30.5 The `ClientRestrictions` megamorphic case, because it is the one place in QuizStakes where this
      matters: a rule-engine strategy interface with a dozen implementations, called synchronously on every
      money path at an extreme request rate inside a **30 ms p99** budget on a 4 GB heap × 8 instances. That
      is the profile where a `switch` over a sealed interface beats a `Map<String, Strategy>` — and the
      leaf must say *measure it*, not assume either way. `[NUM]` `[DECIDE]` `[X-REF 25]`
2.30.6 **One more stack frame, and a worse stack trace.** Proxies and decorators insert frames whose names
      are not yours (`$Proxy47.reserveStake`, `CGLIB$$...`), so the trace that lands in the incident channel
      no longer names your logic. A real cost, paid at 3 a.m. (§3.7) `[DIAG]`
2.30.7 **One more place an error can surface.** Patterns move errors along the compile → startup → request
      axis, and moving right is always a cost. Strategy-by-map turns an unknown key from a compile-time
      exhaustiveness failure into a runtime one; the mitigation is a startup assertion that every key
      present in the data has a registered implementation. `[PROVE]` `[SAY]`
2.30.8 **One more thing to configure, and one more thing to monitor.** A circuit breaker is eight
      parameters and three metrics; an outbox is a table, a relay, a lag metric and a pruning job. Count
      operational surface as part of the pattern's price. `[X-REF 20]`
2.30.9 The cost table itself — pattern family × {files, allocations, dispatch, frames, error-surface shift,
      config/monitoring} — so the reader can price an unfamiliar design instead of judging it
      aesthetically. `[TABLE]`
2.30.10 **The monolith-vs-microservice arithmetic, item 1 — latency.** An in-process call is ≈**10 ns**; a
      same-AZ RPC is ≈**0.5 ms**. That is roughly five orders of magnitude, so a use case that touched four
      modules and now makes four serial network hops adds ≈2 ms of pure transport before any work — against
      a 30 ms restriction budget and a 150 ms stake-reservation budget. `[NUM]` `[PROVE]`
2.30.11 **Item 2 — multiplied availability.** Serial dependencies multiply: six services at 99.99% in one
      request path give 0.9999^6 ≈ **99.94%**, which is ~26 minutes of monthly downtime instead of ~4. Show
      the multiplication; the number is the argument. `[NUM]` `[PROVE]` `[X-REF 22]`
2.30.12 **Item 3 — saga instead of ACID.** A single transaction across modules becomes a saga with
      compensating actions, a pivot transaction past which there is no undo, semantic locks to prevent
      dirty reads, and intermediate states that are *visible to users* — `CLIENT_CASH_RESERVED` is a state a
      client can see and ask about. That support-visible intermediate state is the real cost, not the code. (§2.25)
2.30.13 **Item 4 — N× operational surface.** N services means N pipelines, N dashboards, N alert routes, N
      on-call rotations or one very tired one, and distributed tracing moves from nice-to-have to
      prerequisite. QuizStakes' 22 services is the honest scale of this bill. `[NUM]` `[X-REF 20]`
2.30.14 The **evolution ladder**, with the trigger for each step stated as a condition you could observe
      rather than a preference: **(1) layered monolith** — start here, always, unless a specific
      requirement forbids it. **Trigger to step up:** change amplification measured as files-touched per
      feature, plus merge contention on shared classes. **(2) modular monolith** — package-by-feature,
      package-private internals, ArchUnit slice rules, a domain build module with no framework dependency,
      in-process events across module boundaries. **Trigger to step up:** one module needs a different
      deploy cadence, a different resource profile, or a second team's independent ownership. **(3) extract
      one service** — the module with the strongest trigger, along a boundary that has been stable for
      months, with its data extracted first and an anti-corruption layer at the seam; strangler fig at the
      edge and branch by abstraction inside. **Stop after one** and re-measure. `[FLOW]` `[DECIDE]`
2.30.15 **Trap:** "start with microservices to avoid a rewrite later." First-attempt boundaries are wrong —
      that is not pessimism, it is what the DDD literature says about discovering contexts — and the cost
      of fixing a wrong boundary is a *refactor* in a monolith and a *migration* across services. The
      corollary trap is the mirror image: a modular monolith with no enforcement is a layered monolith with
      better folder names, so step 2 is only real if §2.29's rules fail the build. `[TRAP]` `[SAY]`

*(15 leaves)*

### Sources consulted — lane D

| Source (URL) | What it contributed |
|---|---|
| https://sammancoaching.org/reference/code_smells/ | Cross-check on the 2e smell names; flagged which entries on that page are *not* Fowler's (Bumpy Road, Deep Nesting, Paragraph of Code, Variable with Long Scope) → §2.15.29 |
| https://martinfowler.com/articles/refactoring-2nd-ed.html | The 1e→2e delta: four smells added (Mysterious Name, Global Data, Mutable Data, Loops), two removed (Parallel Inheritance Hierarchies, Incomplete Library Class), four renamed → §2.15.26–28 |
| https://github.com/ittus/Refactoring-summary-2nd-javascript | Chapter 3 smell list in **book order**, all 24, and the catalogue refactoring names used verbatim in §2.16 |
| https://martinfowler.com/books/refactoring.html | Fowler's definition of refactoring (behaviour-preserving) → §2.16.25 |
| https://www.dddcommunity.org/library/vernon_2011/ + Vernon_2011_1.pdf / Vernon_2011_2.pdf | *Effective Aggregate Design* parts I–II: the four rules of thumb, verbatim wording → §2.22.3–6 |
| https://www.archi-lab.io/infopages/ddd/aggregate-design-rules-vernon.html | Cross-check on the four rules and the "whose job is it to make the data consistent" decision question → §2.22.8 |
| https://www.infoq.com/news/2014/12/aggregates-ddd/ | Confirmation that rule 1 implies one-aggregate-per-transaction → §2.22.7 |
| https://pubs.opengroup.org/architecture/o-aa-standard/DDD-strategic-patterns.html | Context-map relationship patterns, grouped upstream / downstream / midway → §2.20.13–22 |
| https://contextmapper.org/docs/context-map/ + /docs/customer-supplier/ | Pattern definitions and the upstream/downstream power-direction convention → §2.20.12, §2.20.14 |
| https://deviq.com/domain-driven-design/context-mapping/ | Cross-check on Separate Ways, Big Ball of Mud as map markers → §2.20.19, §2.20.21 |
| https://bagerbach.com/books/fundamentals-of-software-architecture/ | Per-style architecture-characteristics ratings from Richards & Ford, *Fundamentals of Software Architecture* → §2.18.2–9; also service-based as the under-taught middle style → §2.17.12 |
| https://www.oreilly.com/library/view/fundamentals-of-software/9781492043447/ch12.html | Microkernel core/plug-in vocabulary and its scorecard shape → §2.17.16, §2.18.4 |
| https://software-architecture-guild.com/guide/architecture/fundamentals/architecture-styles/ | The monolithic/distributed split and the style census (incl. orchestration-driven SOA, service-based) → §2.17.2, §2.17.13 |
| https://milanjovanovic.tech/blog/clean-architecture-vs-onion-vs-hexagonal | The *actual* differences: clean = use cases first-class + explicit Dependency Rule; onion = rings + domain services; hexagonal = ports/adapters symmetry → §2.17.4–8 |
| https://milanjovanovic.tech/blog/vertical-slice-architecture | Vertical slice: cohesion along the axis of change, layers may differ per slice → §2.17.9 |
| https://microservices.io/patterns/data/saga.html | Compensatable / pivot / retriable taxonomy and the countermeasure list (semantic lock, commutative updates, pessimistic view, reread value, version file, by value) → §2.25.8–10 |
| https://learn.microsoft.com/en-us/azure/architecture/patterns/strangler-fig | Strangler fig façade-and-route mechanism → §2.25.19 |
| https://docs.getunleash.io/guides/feature-flags-for-migrations | Branch by abstraction, parallel run and expand-and-contract as the four flag-driven migration patterns → §2.25.21–24 |
| https://pragprog.com/titles/mnee2/release-it-second-edition/ | *Release It!* 2e stability-pattern list (12) and stability anti-pattern list → §2.26.2–3 |
| https://en.wikipedia.org/wiki/Bulkhead_pattern | Bulkhead provenance and the compartment analogy → §2.26.14 |
| https://www.dre.vanderbilt.edu/~schmidt/POSA/POSA2/ + Wiley/Goodreads POSA2 pages | The 17 POSA2 pattern names, verbatim, incl. Asynchronous Completion Token and Leader/Followers → §2.27.1–7 |
| https://en.wikipedia.org/wiki/Concurrency_pattern | Cross-check that guarded suspension and balking are catalogued outside POSA2 (Lea) → §2.27.11–12 |
| http://xunitpatterns.com/Test%20Double.html + /Mocks,%20Fakes,%20Stubs%20and%20Dummies.html | Meszaros' five test-double definitions and the state-vs-interaction verification axis → §2.28.2–3 |
| https://www.archunit.org/userguide/html/000_Index.html | `ArchRuleDefinition.classes()/noClasses()`, `slices().matching(..)` capture syntax, `layeredArchitecture()`, `onionArchitecture()`, `ClassFileImporter` → §2.29.7–13 |
| https://javadoc.io/doc/com.tngtech.archunit/archunit/latest/com/tngtech/archunit/library/freeze/FreezingArchRule.html | `FreezingArchRule.freeze(rule)` semantics and the `ViolationStore` → §2.29.11 |
| https://event-driven.io/en/gdpr_in_event_driven_architecture/ + https://world.hey.com/otar/challenges-of-building-gdpr-compliant-event-sourced-system-0db251d4 | Crypto-shredding, and the unsettled legal status of encrypted-with-destroyed-key as erasure → §2.24.14–15 |
| https://dzone.com/articles/event-sourcing-guide-when-to-use-avoid-pitfalls | Upcasting planned from day one; snapshot cadence commonly cited as every 100–500 events → §2.24.7, §2.24.11 |
| https://quality.arc42.org/approaches/event-sourcing | Event-sourcing quality trade-offs and the mandatory-projections consequence → §2.24.16–17 |

### Gaps vs the current guide — lane D

| Syllabus leaf | In `src/topics/24-…` | Verdict |
|---|---|---|
| §2.15.1–25 (the 24 smells by name) | line 948–956, a 6-row smell→move→test table | **shallow** — 6 of 24 smells, no Fowler 2e names, no book order |
| §2.15.26–28 (1e→2e delta) | absent | missing |
| §2.15.29 (non-Fowler catalogues) | absent | missing |
| §2.15.30 (smell ≠ defect, refactor on the path of change) | absent | missing |
| §2.16.2–20 (catalogue moves by name) | absent — the guide names moves descriptively ("introduce a builder", "extract a decorator") but uses no catalogue names | missing |
| §2.16.16 (Replace Command with Function, de-patterning) | absent | missing |
| §2.16.21–22 (behaviour/structure commit split, characterisation test) | line 957–960, two clauses | shallow |
| §2.16.23–24 (branch by abstraction, Mikado) | absent | missing |
| §2.17.3 (layered) | § 7.1, lines 756–765 | present, needs the unit-of-modularity/symptom framing |
| §2.17.4–8 (hexagonal vs clean vs onion, *actual* differences) | § 7.2, lines 767–790 — explicitly says "all three are the same idea with different diagrams" | **shallow, and partly wrong** — the dependency rule is shared, the artefacts are not |
| §2.17.9 (vertical slice) | absent | missing |
| §2.17.10–11 (modular monolith, microservices) | § 7.8 table, lines 889–893 | present |
| §2.17.12 (service-based) | absent | missing |
| §2.17.13 (orchestration-driven SOA) | absent | missing |
| §2.17.14 (event-driven, broker vs mediator) | absent as a style; § 4.4 covers in-process observer only | missing |
| §2.17.15–17 (pipeline, microkernel, space-based) | absent | missing |
| §2.17.19–20 (serverless, actor) | absent | missing |
| §2.17.25 (hybrid is normal) | absent | missing |
| §2.17.27 ("microservices for scalability" trap) | line 905–907, one clause on independent scaling | shallow |
| §2.17.29 (style decision procedure) | absent | missing |
| §2.18.1–12 (the fitness table) | absent — no styles × quality-attributes table anywhere | missing |
| §2.19.1–2, 4–5, 11 (by-layer vs by-feature, access modifiers) | § 7.3, lines 792–808 | **present and good** — the mechanical argument is already there |
| §2.19.3 (package by component) | absent | missing |
| §2.19.6 (package-private does not nest) | absent | missing |
| §2.19.7 (`internal` convention) | absent | missing |
| §2.19.8–10 (JPMS, build module) | line 785–786, one clause on the domain build file | shallow |
| §2.20.2–5 (core/supporting/generic subdomains) | absent | missing |
| §2.20.6–7 (bounded context) | § 7.6, lines 848–855 | present |
| §2.20.8–9 (context ≠ microservice; the per-team trap) | absent | missing |
| §2.20.10–11 (ubiquitous language, the grep test) | line 823–826, one bullet | shallow |
| §2.20.12–22 (context map + all nine relationship patterns) | line 853, one parenthetical on anti-corruption layer | **shallow** — 1 of 9 patterns |
| §2.20.23–24 (distillation, large-scale structure) | absent | missing |
| §2.21.1–4, 7, 10–11, 14, 17 (tactical patterns) | § 7.4, lines 812–826 | present, but no mechanical test per pattern |
| §2.21.6 (aggregate root as distinct from aggregate) | absent | missing |
| §2.21.8 (collection- vs persistence-oriented repository) | absent | missing |
| §2.21.9 (factory) | absent from § 7.4's list | missing |
| §2.21.12–13 (infrastructure service, the three-service table) | absent | missing |
| §2.21.15–16 (domain vs integration event; raise vs publish) | absent | missing |
| §2.21.18–19 (specification) | absent | missing |
| §2.21.20–24 (the five tactical traps) | § 6.2 covers anemic model only | shallow |
| §2.22.1–2, 9, 11 (invariant boundary, by-ID, `@Version`) | § 7.5, lines 828–846 | **present and good** |
| §2.22.3–8 (Vernon's four rules, by name) | absent — the rules are paraphrased, never named or attributed | missing |
| §2.22.12 (the generated SQL as proof) | absent | missing |
| §2.22.13 (the `FundsLedger` sizing arithmetic) | absent | missing |
| §2.22.14–16 (both sizing failure modes + the distinguishing diagnostic) | line 844–846, the too-large case only | shallow |
| §2.22.18 (ER-diagram trap) | absent | missing |
| §2.22.20 (the design procedure) | absent | missing |
| §2.23.1, 8 (CQRS separation, projection lag with a number) | § 7.7, lines 859–867 | present |
| §2.23.2 (CQRS ≠ CQS) | absent | missing |
| §2.23.3–7 (the four escalating levels) | absent | missing |
| §2.23.9 (lag as a measured SLI) | absent | missing |
| §2.23.10–13 (four read-your-writes mitigations) | line 865–866, two mitigations in one clause | shallow |
| §2.23.14 (CQRS does not require event sourcing) | absent as a trap; § 7.7 states the converse only | missing |
| §2.23.15 (read model must not authorise) | absent | missing |
| §2.23.17 (rebuild requirement) | absent | missing |
| §2.24.1–3 (log as source of truth; the ledger case) | line 869–872 | present |
| §2.24.4–5 (append-only insert, `(aggregateId, version)` unique index as concurrency control) | absent | missing |
| §2.24.6–9 (replay, snapshot cadence with arithmetic, snapshot-as-cache) | line 874–877, replay and snapshotting named, no numbers | shallow |
| §2.24.10–12 (versioning strategies, upcasting, what upcasting cannot do) | line 878–879, "versioned events plus upcasters" | shallow |
| §2.24.13–15 (GDPR, crypto-shredding, its unsettled status) | line 880–881, one clause | shallow |
| §2.24.17–18 (operational surface, compensating event) | absent | missing |
| §2.24.19 (the `[DECIDE]` case list) | line 883–885, the trap only, no positive criteria | shallow |
| §2.25.1–3 (outbox + relay mechanics + cost) | line 481–482, one clause pointing at guide 14 | shallow |
| §2.25.4–10 (saga, orchestration vs choreography, pivot/compensatable/retriable, semantic lock, all countermeasures) | line 900–901, one clause | **shallow** |
| §2.25.11–13 (API composition, its costs, CQRS-across-services) | absent | missing |
| §2.25.14–16 (BFF, gateway, and the distinction) | absent | missing |
| §2.25.17–18 (anti-corruption layer, the grep test) | line 853, one parenthetical | shallow |
| §2.25.19–24 (strangler fig, branch by abstraction, parallel run, expand-and-contract) | line 916–918, "start modular-monolith, extract along seams" | shallow |
| §2.25.25–26 (sidecar / ambassador / adapter disambiguated) | § 8 table row, sidecar/ambassador merged into one cell | shallow |
| §2.25.27 (shared nothing + the partition-affinity caveat) | absent | missing |
| §2.25.28–29 (shared database tell + the full diagnostic checklist) | lines 909–914 | **present and good** |
| §2.26.2–3 (Nygard's 12 stability patterns and 12 anti-patterns, by name) | absent — § 8 has 9 patterns, none attributed | missing |
| §2.26.4–8 (retry, jitter, amplification arithmetic, both retry traps) | § 8 table row | shallow — no amplification arithmetic |
| §2.26.9–10 (timeout, shrinking budget, the QuizStakes arithmetic) | § 8 table row | shallow — no numbers |
| §2.26.11–13 (breaker states + full Resilience4j config surface + open-state requirement) | § 8 table row | shallow — states named, no config names |
| §2.26.16 (load shedding as distinct from rate limiting) | § 8 merges them into one row | shallow |
| §2.26.19 (hedged request) | absent | missing |
| §2.26.20 (fallback / graceful degradation / dead letter) | absent | missing |
| §2.26.22 (fail fast, steady state, one-policy rule) | line 938–940 has the one-policy rule; fail fast and steady state absent | shallow |
| §2.27.1 (POSA2's 17 names) | absent | missing |
| §2.27.2–3 (reactor **and** proactor, readiness vs completion) | § 8 table row, reactor only | shallow |
| §2.27.4–13 (ACT, half-sync/half-async, leader/followers, active object, monitor object, TSS, guarded suspension, balking) | absent | missing |
| §2.27.15 (thread pool + the queue-full growth rule) | § 8 row, `ThreadPoolExecutor` trap present | present |
| §2.27.17 (disruptor / ring buffer) | absent | missing |
| §2.27.18–21 (virtual threads retiring reactor, pinning caveat, structured concurrency, scoped values) | absent | missing |
| §2.28.2–4 (Meszaros' five doubles, state vs interaction, Mockito's mapping) | absent | missing |
| §2.28.5 (constructor injection as the testability lever) | absent as a named mechanism | missing |
| §2.28.6 (why the static singleton is untestable) | lines 189–193, 742–744 | present |
| §2.28.7–13 (per-family testability consequence) | scattered single clauses (§ 7.2 "domain tests are plain JUnit") | shallow |
| §2.28.14–15 (do not mock what you do not own; over-mocking as a design metric) | absent | missing |
| §2.29.2–4 (ADR format and when one is needed) | absent | missing |
| §2.29.5–6 (fitness functions) | absent | missing |
| §2.29.7–13 (ArchUnit rule shapes by API name, freeze, the failure report, the bytecode mechanism) | line 786, "ArchUnit can assert it in a test" | **shallow** — no API names at all |
| §2.29.14 (JPMS) | absent | missing |
| §2.29.15 (the build-file test + `jdeps`) | line 785–786 | present |
| §2.30.2–9 (the itemised cost model) | lines 746–750, the indirection-cost paragraph | shallow |
| §2.30.5 (the `ClientRestrictions` megamorphic case) | absent | missing |
| §2.30.10–13 (the four-item arithmetic) | lines 895–903 | **present and good** |
| §2.30.14 (the three-rung evolution ladder with observable triggers) | line 918, one sentence | shallow |
| §2.30.15 (both directions of the trap) | line 916–918, one direction | shallow |

### Notes for the orchestrator — lane D

**Leaf counts per section, and the arithmetic.**

| Section | Leaves |
|---|---|
| §2.15 code smells | 30 |
| §2.16 refactoring catalogue | 25 |
| §2.17 architecture styles | 30 |
| §2.18 fitness table | 12 |
| §2.19 package structure | 12 |
| §2.20 DDD strategic | 25 |
| §2.21 DDD tactical | 25 |
| §2.22 aggregate design | 20 |
| §2.23 CQRS | 18 |
| §2.24 event sourcing | 20 |
| §2.25 integration & decomposition | 30 |
| §2.26 resilience | 22 |
| §2.27 concurrency patterns | 22 |
| §2.28 testability | 15 |
| §2.29 enforcement | 15 |
| §2.30 cost model | 15 |

30+25+30+12+12+25 = 134; 25+20+18+20+30 = 113 (running 247); 22+22+15+15+15 = 89 → **lane D total 336 leaves**
across 16 sections. Against the ≈300 target that is +12%, inside the ±15% band. Every count above was
taken from the numbered leaf lines on disk (`grep -c '^2\.NN\.'`), not estimated.

**Tag counts for the lane** (tag *occurrences* inside §2.15–§2.30 only, excluding these three trailing
blocks; a leaf may carry several tags, so the total exceeds the leaf count). Counted on disk, not
estimated. **452 tag occurrences across 336 leaves — 1.35 tags per leaf.**

| Tag | Count |
|---|---|
| `[X-REF nn]` — all sibling-guide, none intra-guide | 71 |
| `[TRAP]` | 48 |
| `[PROVE]` | 47 |
| `[DECIDE]` | 44 |
| `[API]` | 42 |
| `[RESEARCH]` | 37 |
| `[TABLE]` | 30 |
| `[NUM]` | 29 |
| `[SAY]` | 27 |
| `[SOURCE]` | 25 |
| `[SMELL]` | 24 |
| `[VERSION-TRAP]` | 10 |
| `[FLOW]` | 7 |
| `[DIAG]` | 4 |
| `[BUILD]` | 4 |
| `[INCIDENT]` | 3 |

`[X-REF nn]` targets by frequency: 05 (13), 14 (11), 08 (9), 12 (8), 22 (6), 06 (5), 16 (4), 20 (4),
07 (3), 25 (3), and one each to 13, 15, 17, 18, 19. Fifteen of the twenty-five sibling guides are
pointed at, which matches this lane's position as the architecture/DDD/resilience block.

**Intra-guide pointers are now bare `§N.M`, per the orchestrator's ruling.** All 43 were converted: 39
became a parenthetical `(§N.M)` sitting immediately before the leaf's tag run, and 4 were deleted outright
because the leaf text already carried the bare reference inline (§2.20.21, §2.21.5, §2.21.17, and the
folded continuation line in §2.15.24). `grep -c 'X-REF 24'` over the leaf sections now returns 0, so a
`grep` for `[X-REF` returns exactly the 71 real sibling-guide hand-offs — which was the point of the
ruling.

One note on tag usage: `[SMELL]` appears exactly 24 times, once per Fowler 2e smell, and all 24 sit in
§2.15 — a deliberate invariant the write pass can check with one `grep`.

**What I could not verify, named, with the constant and the source that would settle it.**

1. **The §2.18 fitness table's star ratings.** Richards & Ford publish a 1–5 star scorecard per style in
   *Fundamentals of Software Architecture* (O'Reilly; ch. 9–15 of the 1st ed.), but no source I could reach
   transcribes the full grid. `bagerbach.com`'s reading notes give the ratings **qualitatively** for every
   style (and numerically for service-based: testability/deployability/fault tolerance/availability/agility
   at 4 of 5, scalability 3, elasticity 2), which is what §2.18.2–9 encodes. Every one of those leaves
   carries `[RESEARCH]`. **What would settle it:** the per-style scorecard figures in the book itself
   (1st ed. ISBN 978-1-492-04345-4; 2nd ed. 978-1-098-17551-1) or the scorecard images on
   DeveloperToArchitect.com. The write pass must transcribe from the book, not from my leaves, and must
   confirm whether the 2nd edition changed any rating — I could not check that either.
2. **`[VERSION-TRAP]` on §2.27.20 (structured concurrency).** `StructuredTaskScope` was a preview API in
   Java 21 (JEP 453) and its signature changed in later JDKs — the `ShutdownOnFailure`/`ShutdownOnSuccess`
   subclasses were replaced by a `Joiner`-based API. I could not confirm the exact JDK release and final
   shape within this lane's research budget. **What would settle it:** the JEP history for structured
   concurrency (453 → 480 → 499 → 505) and the `java.util.concurrent.StructuredTaskScope` javadoc for the
   guide's stated JDK 22–25 delta range. The leaf is written to state the Java 21 shape and flag the
   delta; the write pass must fill in which release changed what.
3. **§2.26.12 Resilience4j — resolved by ownership, not by research.** Per the orchestrator, **§3.15 is
   the single authority** for the `CircuitBreakerConfig` property names, their spellings and their
   documented defaults; §2.26.12 no longer lists them. It now names the *shape* of the configuration
   surface (window type and size, minimum call count, failure-rate threshold, slow-call rate and duration,
   open-state wait, half-open probe count) plus the five states I assert (`CLOSED`, `OPEN`, `HALF_OPEN`,
   `DISABLED`, `FORCED_OPEN`), keeps its `[RESEARCH]` tag, and points at §3.15. It also carries the
   warning lane F raised — a default quoted in a tuning example (e.g. `minimumNumberOfCalls = 20`) is a
   chosen value, not the library's documented default. **What would settle the underlying facts:** the
   Resilience4j 2.x `CircuitBreakerConfig` javadoc and the `resilience4j.circuitbreaker.instances.*`
   Spring Boot property reference — for §3.15 to fetch, not this lane.
4. **§2.24.7 snapshot cadence.** "Every 100–500 events" is a widely repeated practitioner figure, sourced
   here from a DZone guide rather than a primary source; there is no canonical constant. The leaf states it
   as a *commonly cited range* and §2.24.8 derives the QuizStakes number from the scenario's own arithmetic
   instead, which is the defensible version. **What would settle it:** nothing — it is a tuning parameter,
   and the write pass should present it as such rather than as a constant.
5. **§2.20.23 distillation patterns.** The seven names are from Evans *DDD* (2003) part IV. I could not
   fetch a primary table of contents to confirm the exact set and spellings (particularly whether
   *Cohesive Mechanisms* and *Abstract Core* are both in the distillation group). Leaf carries
   `[RESEARCH]`. **What would settle it:** Evans, *Domain-Driven Design*, part IV chapter 15 contents.
6. **§2.15.29 non-Fowler smell attributions.** *Bumpy Road*, *Deep Nesting*, *Paragraph of Code* and
   *Variable with Long Scope* appear on sammancoaching.org, which states its entries are original prose
   with names "many of" which come from Fowler 2e — so which of those four are CodeScene/Tornhill coinages
   versus site-original is unconfirmed. The leaf presents them as "named by other catalogues", which is
   true regardless of which catalogue. **What would settle it:** Tornhill's *Software Design X-Rays* /
   CodeScene documentation for Bumpy Road and Deep Nesting.

**What I judged out of this topic's scope, and where I sent it.**

- Broker/partition/consumer-group/delivery-semantics mechanics behind the outbox and saga → `[X-REF 14]`,
  stated once in §2.25.30 as an explicit hand-off so §2.25 does not re-teach transport.
- CAP/PACELC, quorum `R+W>N`, consistent hashing and cross-service capacity arithmetic → `[X-REF 22]`.
  §2.17.2 and §2.25.30 point there; §2.30.11 keeps only the availability *multiplication* because it is a
  cost-model argument for decomposition, not a distributed-systems mechanism.
- JMH harness mechanics for §2.30.5's "measure the megamorphic site" claim → `[X-REF 25]`. This lane
  states *what to measure and why*, never how to build the harness.
- Inline-cache degradation, escape analysis and scalar replacement mechanics → `[X-REF 06]` and lane E's
  §3.1–3.2. §2.30.3–4 state the cost and cite; they do not explain the JIT.
- `@Version` SQL generation, dirty checking and the persistence-context lifecycle → `[X-REF 08]`.
  §2.22.11–12 own it *as aggregate design* and show the statement; the mechanism is guide 08's.
- Test-slice and Testcontainers mechanics behind §2.28.12's fake-vs-integration boundary → `[X-REF 16]`.
- Sidecar deployment mechanics (pod topology, resource overhead) → `[X-REF 19]`; §2.25.25–26 keep only the
  pattern distinction.
- Commit hygiene and `git bisect` mechanics behind §2.16.21 → `[X-REF 17]`.

**Two coordination notes.**

- §2.15's smell→move→test triples and §2.16's catalogue-move names must not be re-enumerated by lane C's
  §2.14 (anti-pattern catalogue). The boundary I assumed: lane C owns *anti-patterns* (god object, anemic
  model, distributed monolith — design-level failures with a failure mechanism), lane D owns *smells*
  (Fowler's code-level hints) and *moves*. §2.15.30 states the distinction explicitly so the merged
  document does not appear to contradict itself.
- §2.19 (package structure) and §2.29 (enforcement) both touched JPMS and the build module, and the
  overlap with lane E's §3.20 is now resolved per the orchestrator: **§3.20 owns all the machinery** —
  `exports`, `requires transitive`, `opens`, `--add-exports`, `jdeps`, and how ArchUnit's `ClassFileImporter`
  and `freeze()` actually work. Three leaves were rewritten in place, so no counts moved: §2.19.8 now
  states only what JPMS changes about *layout* (the boundary becomes a declared file rather than an implied
  package tree) and points at §3.20; §2.29.13 keeps only the one property a rule *author* needs — rules see
  bytecode, so reflection/bean-name/SpEL wiring is invisible, therefore write rules against types — and
  sends the importer mechanics to §3.20; §2.29.14 became the **enforcement ladder** decision leaf
  (convention → package-private → ArchUnit → build module → JPMS), with the `[DECIDE]` rule that you climb
  only as far as the rule's blast radius justifies and that a domain build module is the right rung for
  almost every service. §2.29.7–11 keep the ArchUnit rule *shapes* by API name, which the brief assigns
  here. `[API]` was dropped from those three leaves and `[DECIDE]` added, which is the whole of the tag
  delta: `[API]` 46 → 42, `[DECIDE]` 40 → 44.
