## §2.6 SRP in depth — axes of change, actors, coupled releases as the cost

2.6.1 The precise statement and its source: Martin, *Agile Software Development: Principles, Patterns,
      and Practices* (2002) — "a class should have only one reason to change" — re-sharpened in
      *Clean Architecture* (2017) ch. 7 to "a module should be responsible to one, and only one,
      actor". The 2017 wording is the one to quote, because it names *who* supplies the reason. `[SOURCE]`

2.6.2 "Responsibility" is defined as *a source of change*, and a source of change is a human role
      (compliance officer, payments product owner, operations lead), not a verb in a method name. `[SAY]`

2.6.3 **Trap:** SRP as "a class does one thing" or "one method per class". Unfalsifiable at any
      granularity — `saveAndNotify` does one thing called "save and notify" — and it drives the
      opposite failure, a 40-class shatter where every class is one method and the actor boundary is
      still crossed. `[TRAP]`

2.6.4 The mechanical test, stated as a procedure: list the last 10 commits that touched the file, name
      the requesting stakeholder for each, and count distinct stakeholders. Two or more distinct
      stakeholders on one file is the violation, measured rather than asserted. `[PROVE]`

2.6.5 The second mechanical test — git churn correlation: two regions of one file that never change in
      the same commit are two responsibilities that happen to share a `.java`. `[X-REF 17]`

2.6.6 The cost is **coupled releases and merge contention**, not aesthetics: one file edited by the
      restrictions team and the ledger team means one release train, one review queue, and a rollback
      that reverts both teams' work. `[PROVE]`

2.6.7 The second cost — **accidental duplication's inverse**: an SRP violation makes the class's test
      setup require every actor's dependencies, so a pricing-rule test must construct a report
      formatter. `[X-REF 16]`

2.6.8 The QuizStakes violation, named: a `ClientRestrictionsService` that (a) evaluates whether an
      action is blocked, (b) renders the restriction set for `ProfileService`'s display projection, and
      (c) writes the audit row to `ApplicationHistory`. Three actors — compliance, front-end product,
      audit. `[BUILD]`

2.6.9 The refactoring for 2.6.8: split into `RestrictionDecisionService` (the policy decision point),
      `RestrictionViewAssembler` (display projection), `RestrictionAuditWriter`; the three share a
      `Restriction` record and nothing else. `[BUILD]`

2.6.10 The compiling violation #1 — a `WagerSettlement` entity carrying `toCsvRow()` for the
       `BankWithdrawal` file generator: the domain type now changes when the bank's file format
       changes. `[BUILD]`

2.6.11 The compiling violation #2 — a `FundsLedgerEntry` carrying both JPA mapping annotations and
       Jackson `@JsonProperty` names: the persistence schema and the wire contract become one change
       unit, so an API rename is a migration. `[API]`

2.6.12 The compiling violation #3 — `@Transactional` on a method that both mutates the ledger and
       calls the card PSP: the transaction boundary actor (persistence) and the remote-call actor
       (integration) share one method, and the 11 s PSP p99 now holds a DB connection. `[NUM]`

2.6.13 SRP at method level: extract-method is *not* SRP — SRP is about who requests the change to the
       enclosing module. A 200-line method with one stakeholder does not violate SRP; it violates
       the long-method smell (see §2.15). `[TRAP]`

2.6.14 SRP's own cost, named honestly: more files, more constructor wiring, and a use case that now
       spans three classes so "where does this happen" needs three opens. Indirection is charged even
       when the split is right. `[DECIDE]`

2.6.15 The "do not split" case: two responsibilities that are always requested by the same actor and
       always change together should stay in one class — splitting them creates a two-file change for
       every requirement and buys nothing. `[DECIDE]`

2.6.16 SRP's relationship to CCP (§2.13): SRP is CCP applied at class scope — "gather together the
       things that change for the same reason, separate those that change for different reasons" is
       one statement at two granularities. `[PROVE]`

2.6.17 The god-object end state: an SRP violation left unfixed compounds, because every new actor adds
       to the file that already knows everything. Failure mechanism in §2.14.1. `[SMELL]`

2.6.18 Detection tooling: `LCOM4` (lack of cohesion of methods) as the numeric proxy — disjoint method
       clusters sharing no field are the actor split made measurable; and ArchUnit rules asserting a
       class does not depend on two named packages. `[API]`

2.6.19 **Trap:** using SRP to justify a layer of `*Manager`/`*Helper` classes. Renaming the god object
       to three `Helper`s that all take the same 12 dependencies moves the violation without fixing
       it; the test is whether each new class's dependency set shrank. `[TRAP]`

2.6.20 The interview sentence: "SRP for me is one actor per module — I check it by asking who signs off
       on the change; if two stakeholder groups edit one file, their releases are coupled and that's
       the cost I'm avoiding, not tidiness." `[SAY]`

*(20 leaves)*

## §2.7 OCP in depth — the seam, and who pays when the interface owner must change

2.7.1 The precise statement and source: Bertrand Meyer, *Object-Oriented Software Construction*
      (1988) — "a module should be open for extension but closed for modification"; Martin's
      polymorphic reading (abstract base / interface as the closure mechanism) is the one in use
      today and differs from Meyer's original inheritance-based one. `[SOURCE]`

2.7.2 Meyer's original mechanism was **implementation inheritance** — a closed module is reused by
      subclassing it. Martin's is **abstract interfaces plus DIP**. Conflating the two is why OCP
      discussions drift into inheritance-vs-composition. `[VERSION-TRAP]`

2.7.3 **Trap:** OCP as "never modify existing code". You modify existing code constantly. OCP says a
      *predicted kind of variation* should be addable without editing the modules that consume it —
      it says nothing about bug fixes, refactorings, or unanticipated change. `[TRAP]`

2.7.4 The mechanical test: name the next change of the class you claim to be open to, and count the
      files edited to make it. One new file plus zero edits = open. Any edit to an existing consumer =
      not open on that axis. `[PROVE]`

2.7.5 "Open on an axis" is the whole idea — OCP is never global. A `Map<String, ScoringStrategy>`
      registry is open to new scoring modes and *closed* to a change in the `ScoringStrategy`
      interface itself. Naming the axis is the answer; claiming openness is not. `[SAY]`

2.7.6 The seam is a *pre-existing polymorphic boundary*. OCP cannot be achieved retroactively for free
      — you get it only where the variation axis was predicted correctly, which is why the rule of
      three (§1.5) precedes it. `[PROVE]`

2.7.7 Who pays when the interface owner must change — the arithmetic: adding one method to an
      interface with N implementations is N+1 edited files, all of which must ship together. OCP for
      the consumer is bought with fragility for the abstraction's owner. `[NUM]`

2.7.8 Consequence: an interface is a *commitment with a per-implementation change tax*, so the
      interface should be the narrowest thing the consumer needs — which is ISP (§2.9) as the
      counterweight to OCP, not an unrelated principle. `[PROVE]`

2.7.9 The QuizStakes seam that works: `PayoutRail` as an outbound port with `CardRail` and
      `BankRail` adapters, selected per withdrawal row by rail code. A third rail is one new
      `@Component`; `PaymentService` is untouched. `[BUILD]`

2.7.10 The QuizStakes seam that fails: a `RestrictionEvaluator` interface with one implementation and
       no second on the roadmap. The indirection has no variation flowing through it, so every
       reader pays one extra hop for nothing. `[DECIDE]`

2.7.11 Violation that compiles #1 — the `switch` on `restriction.type()` duplicated in
       `PaymentService`, `FundsLedger` and the login path: adding `SOURCE_OF_FUNDS_REQUIRED` edits
       three files in three services, and one of them will be missed. `[BUILD]`

2.7.12 Violation that compiles #2 — `if (rail instanceof CardWithdrawal c)` in the application service:
       a type test in the consumer is the definitive symptom that the seam is in the wrong place. `[SMELL]`

2.7.13 Violation that compiles #3 — an `enum` with behaviour bodies plus a consumer `switch` over it
       *as well*: the enum is the closed set (fine) but the switch outside it re-opens the edit. `[BUILD]`

2.7.14 The refactoring move: replace-conditional-with-polymorphism, keeping the switch as the *map
       lookup* at wiring time, plus a startup assertion that every code present in the database has a
       registered implementation (§2.16). `[BUILD]`

2.7.15 The startup assertion is the part candidates skip: OCP-by-registry converts a compile-time
       exhaustiveness error into a **runtime** `UnknownRailException`, and the fix is to move it back
       to *startup* with an `@EventListener(ApplicationReadyEvent.class)` check. `[API]`

2.7.16 The closed-set alternative, and when it wins: a `sealed interface` + exhaustive `switch` gives
       compile-time exhaustiveness — strictly better than a registry when you own the set and it is
       small. Adding a permitted subtype breaks compilation everywhere it must. `[X-REF 04]`

2.7.17 `default` methods on interfaces as OCP-for-the-interface-owner: a new method with a default body
       adds capability without breaking N implementations — bought at the price of a default that may
       be wrong for some implementor. `[API]`

2.7.18 OCP's cost model: one interface, one registry, one more indirection hop per call, plus a
       megamorphic call site if implementations exceed the inline-cache limit — the dispatch cost is
       real and measured in §3.1. `[X-REF 06]`

2.7.19 The "do not use this when" case: a variation that has occurred exactly once, a set owned
       entirely by you, or a variation axis you are guessing at. A wrong seam is more expensive than
       duplication because it is load-bearing and referenced. `[DECIDE]`

2.7.20 The interview sentence: "I'd make it open to new payout rails and explicitly closed to a change
       in the rail interface — adding a rail is one file, changing the interface is N files, and I'd
       rather pay the second cost rarely than the first cost quarterly." `[SAY]`

*(20 leaves)*

## §2.8 LSP in depth — the contract rules (preconditions, postconditions, invariants, history), and the violations that compile

2.8.1 The precise statement and source: Liskov's 1987 OOPSLA keynote ("Data Abstraction and
      Hierarchy") and Liskov & Wing, *A Behavioral Notion of Subtyping* (ACM TOPLAS, 1994): if S is a
      subtype of T, objects of type T may be replaced with objects of type S without altering any
      property of the program provable about T. `[SOURCE]`

2.8.2 The distinction that makes LSP non-trivial: **signature subtyping is what the compiler checks;
      behavioural subtyping is what LSP demands.** Every LSP violation therefore compiles by
      construction. `[PROVE]`

2.8.3 **Contract rule 1 — preconditions cannot be strengthened in the subtype.** The override must
      demand no more than the base. Formally: `pre_T ⇒ pre_S`. `[SOURCE]`

2.8.4 **Contract rule 2 — postconditions cannot be weakened in the subtype.** The override must
      promise no less than the base. Formally: `post_S ⇒ post_T`. `[SOURCE]`

2.8.5 **Contract rule 3 — invariants of the supertype must be preserved** by every subtype method,
      including methods the subtype introduces. `[SOURCE]`

2.8.6 **Contract rule 4 — the history rule (history constraint).** A subtype may not permit state
      changes the supertype's contract forbids. This was Liskov & Wing's novel contribution and the
      rule that new subtype methods break: adding a mutator to a subtype of an immutable type
      violates LSP even though every inherited method is correct. `[SOURCE]`

2.8.7 The signature-level shadow of rules 1 and 2 in a language without contracts: parameter types
      must be **contravariant**, return types **covariant**, thrown checked exceptions must not widen.
      Java enforces covariant returns and non-widening checked throws, and forbids contravariant
      parameters (a wider parameter type is an overload, not an override). `[API]`

2.8.8 Consequence of 2.8.7: Java's compiler polices roughly one third of LSP and silently permits the
      rest — precondition strengthening, postcondition weakening, unchecked exceptions, and history
      violations are all invisible to it. `[PROVE]`

2.8.9 Violation that compiles #1 — **strengthened precondition.** `FundsLedger.reserve(Money)` accepts
      any positive amount; a `PartitionAffineLedger` override throws when the client is not on this
      instance's partition. Existing callers now fail on valid input. `[BUILD]`

2.8.10 Violation that compiles #2 — **weakened postcondition.** Base `restrictionsFor(clientId)`
       guarantees a set containing every active restriction; a caching override returns a set that may
       be up to 30 s stale, so `SELF_EXCLUDED` can be missing — the one restriction §10.4 says cannot
       be eventually consistent. `[INCIDENT]`

2.8.11 Violation that compiles #3 — **new unchecked exception.** An adapter override throws
       `IllegalStateException` where the port documented only `InsufficientFundsException`; every
       caller's catch block is now incomplete and the failure surfaces as a 500. `[BUILD]`

2.8.12 Violation that compiles #4 — **invariant broken by a subtype field.** A subtype of
       `WagerSettlement` adding a mutable `List<Leg>` breaks the "legs' stakes sum to the total"
       invariant the base's compact constructor established. `[BUILD]`

2.8.13 Violation that compiles #5 — **history rule.** `record LedgerEntry` is append-only by contract;
       a subtype (or a wrapper claiming the same type role) exposing `void setAmount(Money)` permits a
       state transition the supertype forbids, violating invariant 7 of §11.7. `[PROVE]`

2.8.14 `UnsupportedOperationException` as the JDK's own institutionalised LSP violation:
       `List.of(...)`, `Collections.unmodifiableList`, `Map.of`, `Set.copyOf` all satisfy the mutating
       half of their interface by throwing. The interface promises `add`; the object refuses. `[API]`

2.8.15 `Arrays.asList` is the worse case, and the distinction is the interview point: it is
       **fixed-size, not immutable** — `set(i, v)` succeeds and writes through to the backing array,
       `add`/`remove` throw. Two different subsets of the contract, both surprising. `[TRAP]`

2.8.16 The JDK's structural fix attempt: `Collection` javadoc marks mutators "optional operations",
       which *documents* the violation rather than removing it — the contract was weakened to make the
       implementations legal. Sealed/immutable collection interfaces are what would actually fix it. `[SOURCE]`

2.8.17 **Covariant arrays** — Java's own hole in its type system: `Object[] a = new String[1];
       a[0] = Integer.valueOf(42);` compiles and throws `ArrayStoreException` at runtime. `String[]`
       is a subtype of `Object[]` for assignment but not for writes. `[BUILD]`

2.8.18 Why generics are invariant as a direct consequence: `List<String>` is *not* a `List<Object>`,
       precisely so the array mistake cannot recur; PECS/wildcards are the opt-in variance. `[X-REF 03]`

2.8.19 **`equals` symmetry breaking under inheritance:** a subclass adding a field and an `instanceof`
       -based `equals` gives `sub.equals(base) == false` while `base.equals(sub) == true`, so
       `List.contains` returns different answers depending on argument order. `getClass()`-based
       `equals` restores symmetry and destroys substitutability instead — there is no version that
       satisfies both. `[PROVE]`

2.8.20 The `equals` corollary from *Effective Java* item 10: "there is no way to extend an
       instantiable class and add a value component while preserving the `equals` contract" — the fix
       is composition (hold the base, expose a view), not inheritance. `[SOURCE]`

2.8.21 The consequence to name in an interview: LSP violations migrate into `instanceof` checks in the
       **caller**, and once callers type-test, polymorphism is gone and the abstraction is decorative. `[SAY]`

2.8.22 **Trap:** "LSP means a subclass must not throw." It may throw anything the base's contract
       permits, including the base's own declared exceptions on the base's documented failure
       conditions. What it must not do is throw on inputs the base accepted, or throw a type the base
       never documented. Stating the rule as "no new exceptions" fails on the follow-up. `[TRAP]`

*(22 leaves)*

## §2.9 ISP in depth — role interfaces, and what `default` methods softened

2.9.1 The precise statement and source: Martin, from the Xerox printer-driver work later written up in
      *Agile Software Development* (2002) — "clients should not be forced to depend upon interfaces
      that they do not use." The subject of the sentence is the **client**, not the interface. `[SOURCE]`

2.9.2 **Trap:** ISP as "small interfaces are good" or "no more than N methods". Size is not the
      criterion — a 12-method interface every client calls in full is fine, and a 2-method interface
      where each client uses one is a violation. The criterion is *unused dependency per client*. `[TRAP]`

2.9.3 The mechanical test: for each caller, list the methods it actually invokes. Any caller invoking a
      strict subset means that caller recompiles and re-tests when methods it never calls change. `[PROVE]`

2.9.4 The cost being avoided is **compile/deploy coupling through an unused surface** — in Java,
      changing a method signature on a fat interface recompiles and retests every client, including
      the ones that never touch it. `[PROVE]`

2.9.5 The second cost — **stub lies.** An implementor must supply every method, so a wide interface
      forces `return null` / `throw new UnsupportedOperationException()` bodies, and each one is an
      LSP violation (§2.8.14) that a caller can reach. `[PROVE]`

2.9.6 Fowler's **role interface** vs the header interface: a role interface is defined by what one
      collaboration needs (`StakeReserver`), a header interface mirrors a class's whole public surface
      (`FundsLedgerInterface`). Header interfaces are the ISP anti-pattern in its commonest Java form. `[SOURCE]`

2.9.7 The corollary nobody states: **the client should own or at least shape the interface**, which is
      where ISP meets DIP (§2.10). An interface extracted from an implementation is a header
      interface by construction. `[PROVE]`

2.9.8 The QuizStakes violation: one `LedgerPort` with `reserve`, `settle`, `void_`, `credit`, `debit`,
      `positionsFor`, `entriesBetween`, `replayFrom`. `BalanceView` calls only `positionsFor`; the
      Quiz boundary calls only `reserve`/`settle`/`void_`; the reconciliation job calls only
      `entriesBetween`. `[BUILD]`

2.9.9 The refactoring for 2.9.8 — split into role interfaces `StakeReservations`,
      `LedgerPostings`, `PositionReader`, `EntryStream`, all implemented by the one `FundsLedger`
      class. Zero runtime change; the change is entirely in what recompiles and what a test must
      stub. `[BUILD]`

2.9.10 The key mechanical fact: **one class may implement many role interfaces.** ISP does not
       fragment the implementation, only the declared dependency — so the "but then I have 4 classes"
       objection is a misunderstanding. `[TRAP]`

2.9.11 Violation that compiles #2 — an `OperatorAction` interface with `approve`, `reject`, `waive`,
       `override` where `WaiveRequirementAction` throws on three of the four. The compiler is
       satisfied; the operator console can call a method that always 500s. `[BUILD]`

2.9.12 Violation that compiles #3 — a `NotificationChannel` interface carrying `sendSms`, `sendEmail`
       and `sendPush`, forcing each channel to no-op two methods, instead of one `send(Message)` with
       three implementations. The fat interface here is a *missing* abstraction, not too small a one. `[SMELL]`

2.9.13 What `default` methods (Java 8) softened: adding a method to an interface used to break every
       implementor at compile time — a hard OCP violation for the interface owner (§2.7.8). A
       `default` body makes the addition source- and binary-compatible. `[X-REF 04]`

2.9.14 What `default` methods did **not** fix, and this is the trap: a default body is a *behavioural*
       guess on behalf of every implementor. `default boolean isBlocking() { return false; }` on a
       restriction interface silently makes every existing restriction non-blocking. The compile break
       was information. `[TRAP]`

2.9.15 The second thing `default` did not fix: implementors still *inherit* the method, so the
       interface's surface still grows for every client — ISP is about the client's view, and a
       default method is still a method the client sees. `[PROVE]`

2.9.16 `default` mechanics worth naming exactly: the diamond rule (a class inheriting conflicting
       defaults must override), `Interface.super.method()` for explicit selection, class-wins-over-
       interface resolution, and that `private`/`static` interface methods (Java 9) let a default body
       share helpers without exporting them. `[API]`

2.9.17 The JDK's own ISP story: `Collection`'s "optional operations" are what you get *instead of* ISP
       — one wide interface with documented refusals. `SequencedCollection` (Java 21, JEP 431) is the
       counter-example, adding a role rather than widening `List`. `[VERSION-TRAP]`

2.9.18 ISP's cost: more interface files, an extra naming decision per role, and a reader who must
       follow a role interface to its single implementation to see what actually happens. `[DECIDE]`

2.9.19 The "do not use this when" case: one client, one implementation, no second consumer on the
       roadmap. Splitting a 3-method interface used by one caller into three is ceremony; the
       recompile blast radius it protects is a single file. `[DECIDE]`

2.9.20 The interview sentence: "ISP is per-client, not per-method-count — `BalanceView` only reads
       positions, so it depends on a `PositionReader`, and it doesn't recompile when the settlement
       signature changes. Same `FundsLedger` class implements all four roles." `[SAY]`

*(20 leaves)*

## §2.10 DIP in depth — interface ownership, the "which module deletes to compile" test

2.10.1 The precise statement and source: Martin, *C++ Report* (1996) "The Dependency Inversion
       Principle" — (a) high-level modules should not depend on low-level modules; both should depend
       on abstractions; (b) abstractions should not depend on details; details should depend on
       abstractions. `[SOURCE]`

2.10.2 The clause everyone drops: the abstraction is **owned by the high-level module**. Without that
       clause DIP is satisfied by any interface anywhere, which is why "we use interfaces" is not DIP. `[PROVE]`

2.10.3 **Trap:** DIP as "always inject an interface". Injection is *dependency injection*, a wiring
       mechanism (§1.32); inversion is about which module the abstraction *belongs to*. You can
       constructor-inject a concrete `JdbcTemplate` (DI, no inversion) or `new` up an adapter behind a
       domain-owned port (inversion, no DI). `[TRAP]`

2.10.4 The **"which module deletes and still compiles"** ownership test, stated as a procedure: delete
       the adapter module from the build. If the domain module still compiles, the domain owns the
       abstraction and the dependency is inverted. If the domain fails to compile, the arrow points
       outward and nothing was inverted. `[PROVE]`

2.10.5 The inverse half of the test: delete the *domain* module and the adapter must fail to compile.
       Both halves must hold; only one holding means you have a shared "common" module, which is a
       different (and often worse) shape. `[PROVE]`

2.10.6 The mechanism in two arrows: at **compile time** domain → port ← adapter; at **runtime** the
       container injects the adapter so control flows domain → adapter. Dependency and control point
       in opposite directions — that opposition is what the word "inversion" names. `[FLOW]`

2.10.7 The build-file test, which is the mechanical version and the strongest thing to say out loud:
       **the domain module's `pom.xml`/`build.gradle` has no framework dependencies** — no
       `spring-boot-starter-*`, no `jakarta.persistence-api`, no Jackson, no driver. `[API]`

2.10.8 The package-location test for a single-module codebase: `interface WagerRepository` lives in
       `com.quizstakes.funds.domain`, not `com.quizstakes.funds.persistence`. Moving that one file
       into the persistence package converts a hexagonal app into a layered one with hexagonal
       vocabulary, with zero behaviour change. `[PROVE]`

2.10.9 DIP is the mechanism **hexagonal architecture is built out of**: a *port* is precisely a
       domain-owned abstraction, an *adapter* is precisely the detail that depends on it. Hexagonal,
       clean and onion are DIP applied at module scale with different ring diagrams (§2.17). `[PROVE]`

2.10.10 Inbound vs outbound ports, distinguished by who calls whom: an inbound port is a use case the
        outside invokes (`ReserveStake`), an outbound port is a capability the domain requires
        (`PayoutRail`, `RestrictionQuery`). Both are domain-owned; only outbound ones are the
        classic DIP shape. `[API]`

2.10.11 The QuizStakes worked case: `FundsLedger`'s domain declares `interface RestrictionQuery` with
        the one method it needs; the `ClientRestrictions` HTTP client implements it in an adapter
        module. The ledger domain compiles with no HTTP client on the classpath. `[BUILD]`

2.10.12 The anti-corruption-layer reading: when the outbound port's shape is dictated by the *vendor*
        (`DocumentVerification`'s identity-vendor SDK), DIP is what keeps the vendor's types out of
        the domain — the adapter translates, the port speaks the domain's language (§2.25). `[PROVE]`

2.10.13 Violation that compiles #1 — the port interface declares
        `Page<WagerEntity> findAll(Pageable p)`. The signature imports Spring Data types, so the
        abstraction depends on a detail; rule (b) is broken even though rule (a) looks satisfied. `[BUILD]`

2.10.14 Violation that compiles #2 — a domain method throwing or catching
        `DataIntegrityViolationException`: the *exception type* is a detail leaking through the
        abstraction. The adapter must translate it into a domain exception. `[API]`

2.10.15 Violation that compiles #3 — a use case returning a JPA `@Entity` to the controller. The
        entity is the detail; every consumer is now coupled to the persistence model, and
        `LazyInitializationException` becomes an API failure mode. `[X-REF 08]`

2.10.16 Violation that compiles #4 — `@Component`/`@Transactional` on a domain class. One annotation
        puts a framework artefact in the module that must not have one, and the build-file test
        (2.10.7) catches it while a code review usually does not. `[SMELL]`

2.10.17 The enforcement mechanism, so DIP is not left to discipline: an ArchUnit rule —
        `noClasses().that().resideInAPackage("..domain..").should().dependOnClassesThat()
        .resideInAnyPackage("org.springframework..", "jakarta.persistence..")` — failing the build
        (§2.29). `[API]`

2.10.18 DIP's cost, stated honestly: a mapping layer between domain objects and entities/DTOs, one more
        type per boundary, and for a CRUD service with no invariants the mapping is pure overhead —
        layered is then the cheaper correct answer. `[DECIDE]`

2.10.19 The "do not use this when" case: a service whose domain *is* the schema (`BankDeposits`
        ingesting a statement file into rows), where inverting the persistence dependency buys
        isolation from a technology you will never swap. `[DECIDE]`

2.10.20 The interview sentence: "DIP for me is an ownership question, not an interface question — the
        port lives in the domain package, the domain's build file has no Spring in it, and I check it
        by deleting the persistence module and seeing whether the domain still compiles." `[SAY]`

*(20 leaves)*

## §2.11 The other principles: Law of Demeter, Tell-Don't-Ask, command-query separation, composition over inheritance, fragile base class, DRY/YAGNI/KISS as trade-offs, separation of concerns, Hollywood principle, principle of least astonishment, Postel's law, Hyrum's law

2.11.1 **Law of Demeter** — origin: proposed at Northeastern University in autumn 1987 by Ian Holland
       during the Demeter Project; also called the principle of least knowledge, motto "only talk to
       your friends". `[SOURCE]`

2.11.2 The formal object form: a method `m` of object `O` may call methods only of — `O` itself, `m`'s
       parameters, objects `m` creates, `O`'s direct component objects, and (in the class form)
       globals accessible to `O`. Anything else is a stranger. `[SOURCE]`

2.11.3 The mechanism of harm in `a.getB().getC().doThing()`: each dot is an undeclared dependency on a
       *structural* fact. A change to `B`'s internals breaks a line that never states `B`'s purpose,
       and the compiler cannot tell you the dependency existed. `[PROVE]`

2.11.4 The fix mechanism: `a.doThing()` — move the behaviour to the owner of the data. The train wreck
       is the clearest symptom of an anemic model (§2.14.2): the behaviour lives at the end of the
       chain in the *caller*. `[SMELL]`

2.11.5 **Trap:** the naive dot-counting form. Fluent builders (`StakeReservation.builder().stake(...)
       .build()`), streams, and `Optional` chains return *the same conceptual object* or a value, not
       a graph traversal, and are not Demeter violations. Counting dots flags them and misses
       `wager.getClient().getRestrictions().isBlocked()`, which is the real one. `[TRAP]`

2.11.6 The discriminator to state: is the chain **navigating someone else's structure** (violation) or
       **configuring/transforming one thing** (fine)? Getter-chains through domain aggregates are the
       violation class; builder and stream chains are not. `[SAY]`

2.11.7 Demeter's cost, named: delegating methods multiply — the "middle man" smell is Demeter applied
       past its useful point, and `wager.clientCountryIsoCode()` on the aggregate is a worse API than
       one honest traversal in one place. `[DECIDE]`

2.11.8 **Tell-Don't-Ask** — origin: the Portland Pattern Repository / Pragmatic Programmers
       formulation. State the mechanism: send the object a command that carries the intent and let it
       decide, rather than pulling its state out and deciding on its behalf. `[SOURCE]`

2.11.9 Tell-Don't-Ask in QuizStakes: `wager.settle(payout, WON)` instead of
       `if (wager.getStatus()==OPEN) { wager.setStatus(SETTLED); wager.setPayout(p); }`. The
       invariant check has one home and cannot be forgotten by a second caller. `[BUILD]`

2.11.10 The legitimate exception: queries genuinely exist — `balanceView.stakeable(clientId)` is an
        ask, and a read model whose whole job is to be asked is not a Tell-Don't-Ask violation. `[DECIDE]`

2.11.11 **Command-query separation (CQS)** — origin: Bertrand Meyer, *Object-Oriented Software
        Construction* / Eiffel. Every method is either a **command** that mutates and returns nothing,
        or a **query** that returns a value and has no observable side effect. Never both. `[SOURCE]`

2.11.12 CQS's payoff mechanism: a query is safe to call twice, safe to call in an assertion, safe to
        call in a log statement, and cacheable. A method that mutates *and* returns loses all four
        properties. `[PROVE]`

2.11.13 CQS violations in the JDK, named because they are the ones you will be asked about:
        `Iterator.next()`, `Map.put` (returns the previous value), `AtomicInteger.getAndIncrement()`,
        `List.remove(int)`, `Queue.poll()`. Each is a deliberate atomicity trade — the combined
        operation cannot be split without a race. `[API]`

2.11.14 **CQS is not CQRS.** CQS is a *method-level naming/side-effect rule* (Meyer, 1988); CQRS
        (Greg Young, c. 2010, from Fowler's write-up) is an *architectural* split of the write model
        from the read model, often with separate stores and a projection lag. Same intuition, three
        orders of magnitude apart in blast radius. Full treatment in §2.23. `[SOURCE]`

2.11.15 **Composition over inheritance** — the mechanism: inheritance is the strongest coupling the
        language offers, because the subclass depends on the superclass's *implementation*, including
        which of its own public methods it calls internally. `[PROVE]`

2.11.16 **Fragile base class, mechanically:** `HashSet.addAll` internally calls `add`. A
        `CountingSet extends HashSet` overriding both to increment a counter counts 3 elements as 6.
        Nothing in the public contract told you about the self-call. `[BUILD]`

2.11.17 The **self-use documentation problem**: the only defence is for the base to document its own
        self-calls ("this implementation invokes `add` for each element"), which turns an
        implementation detail into a permanent contract the base can never change. `[SOURCE]`

2.11.18 *Effective Java* item 19 — "design and document for inheritance or else prohibit it": document
        self-use, provide `protected` hooks only where needed, never call an overridable method from a
        constructor, and otherwise make the class `final` or the constructor private. `[SOURCE]`

2.11.19 *Effective Java* item 18 — "favor composition over inheritance": the forwarding-wrapper form
        (`ForwardingSet` holding a `Set` and forwarding every method) is immune to base self-calls
        because you own every entry point. Its cost is the boilerplate and the callback/`SELF` problem. `[SOURCE]`

2.11.20 The other consequences of inheritance to name: single inheritance is a budget you spend once;
        the binding is compile-time while composition is runtime-swappable; and a subclass inherits
        its parent's *entire* public surface including methods that make no sense for it (an LSP
        hazard, §2.8). `[PROVE]`

2.11.21 When inheritance is still correct: genuine `is-a` with a base designed for it — `sealed`
        hierarchies, `abstract` template-method skeletons (§1.21), and JDK abstract adapters
        (`AbstractList`, `OncePerRequestFilter`). `[DECIDE]`

2.11.22 **DRY** — origin: Hunt & Thomas, *The Pragmatic Programmer* (1999): "every piece of
        **knowledge** must have a single, unambiguous, authoritative representation within a system".
        The subject is knowledge, not characters. `[SOURCE]`

2.11.23 The mechanism of false DRY: two identical blocks encoding two *different* rules that currently
        agree must stay separate. Merging them creates coupling with no shared cause, and the next
        requirement change to one breaks the other. `[PROVE]`

2.11.24 The worst DRY failure is deduplicating **across bounded contexts**: a shared `Client` class
        used by `PersonalDetails` and `FundsLedger` binds two teams' release cycles forever and must
        satisfy both invariant sets, so it satisfies neither (§2.20). `[INCIDENT]`

2.11.25 The **wrong-abstraction cost argument** — Sandi Metz, "The Wrong Abstraction" (2016), stated at
        RailsConf 2014: "duplication is far cheaper than the wrong abstraction", and once an
        abstraction is proved wrong the correct move is to **re-inline it** — re-introduce the
        duplication and let it show you the right seam. `[SOURCE]`

2.11.26 The arithmetic behind it: duplication is *local and deletable* (cost scales with copies), a
        wrong abstraction is *load-bearing and referenced* (cost scales with callers, plus each caller
        adds a parameter or flag until the abstraction is a switch statement with a bad name). `[PROVE]`

2.11.27 **YAGNI** — origin: Extreme Programming / Ron Jeffries, "you aren't gonna need it". The
        mechanism is that speculative generality costs three times: to build, to read, and to remove
        once wrong. Connects directly to the rule of three (§1.5). `[SOURCE]`

2.11.28 **KISS**'s operational meaning, phrased so it is falsifiable: complexity is paid at 03:00 by
        whoever is on call. A design you cannot explain in five minutes cannot be debugged under
        pressure — so "how many hops from the HTTP entry point to the money movement" is the metric. `[SAY]`

2.11.29 **Separation of concerns** — origin: Dijkstra, "On the role of scientific thought" (1974). The
        mechanism: reason about one aspect at a time by making the aspects textually separate; the
        modern instances are layers, cross-cutting concerns via AOP, and hexagonal's ring split. `[SOURCE]`

2.11.30 **Hollywood principle** — "don't call us, we'll call you", traced to c. 1988 and used as the
        informal name for inversion of control: the framework owns the main loop and calls your code,
        which is what makes template method, filter chains, and the whole Spring lifecycle work. `[SOURCE]`

2.11.31 **Principle of least astonishment** — the design rule that a component's behaviour should match
        what its name and the surrounding conventions imply. Concrete Java violations to name: a
        `getX()` that mutates, an `equals` that ignores a field, a `Comparator` inconsistent with
        `equals` (which silently breaks `TreeSet` semantics). `[TRAP]`

2.11.32 **Postel's law / the robustness principle** — Jon Postel, in the early TCP/IP specifications
        (RFC 760/761, 1980; restated in RFC 1122 §1.2.2): "be conservative in what you do, be liberal
        in what you accept from others". Its known failure mode: leniency entrenches other people's
        bugs as de-facto contract, so modern API guidance narrows it to "reject unknown fields at your
        own boundary, ignore unknown fields from upstream". `[RESEARCH]`

*(32 leaves)*

## §2.12 GRASP — all nine responsibility-assignment patterns

2.12.1 Origin and framing: Craig Larman, *Applying UML and Patterns* (1st ed. 1997) — GRASP is
      **General Responsibility Assignment Software Patterns**, nine answers to the question "which
      class should get this responsibility?", one level below GoF (which answers "what structure"). `[SOURCE]`

2.12.2 The distinction from GoF worth stating: GoF patterns are structures you build; GRASP patterns
      are *decision heuristics* applied before any structure exists. Naming GRASP in a design round is
      how you justify a class boundary rather than assert it. `[SAY]`

2.12.3 **Information Expert** — question answered: "who should do this?" Answer: the class that has the
      information needed. QuizStakes assignment: the bonus/cash split
      `min(BONUS_AVAILABLE, 10% of stake)` belongs on the ledger position holder, not on
      `PaymentService`, because only the ledger holds both balances. `[BUILD]`

2.12.4 Information Expert's failure mode: applied blindly it puts persistence and rendering on the
      entity too, because the entity "has the data". It is bounded by low coupling and by SRP
      (§2.6.10). `[TRAP]`

2.12.5 **Creator** — question: "who creates an instance of X?" Answer: the class that aggregates,
      contains, records, or has the initialising data for X. QuizStakes assignment: `PaymentRun`
      creates its `PaymentRunItem`s (it aggregates them); `BankWithdrawal` does not create them from
      outside. `[BUILD]`

2.12.6 **Controller** — question: "who handles a system event / use-case request?" Answer: either a
      facade controller representing the whole system or a use-case controller per use case.
      QuizStakes assignment: `ReserveStakeHandler` as a use-case controller, not one
      `LedgerController` with 30 methods. `[BUILD]`

2.12.7 Controller's named failure — the **bloated controller**: one controller for all use cases
      accumulates orchestration until it is a god object (§2.14.1). Larman states the split rule:
      more than one use case's worth of state or logic means split by use case. `[SMELL]`

2.12.8 **Low Coupling** — question: "how do I keep change local?" It is an *evaluative* pattern, applied
      as a tie-breaker between two candidate assignments rather than as a construction rule.
      Measurable via the coupling taxonomy in §2.13. `[PROVE]`

2.12.9 **High Cohesion** — question: "how do I keep a class comprehensible and focused?" Also
      evaluative, and in permanent tension with low coupling: pushing a responsibility away to raise
      cohesion adds an edge and raises coupling. GRASP says decide the pair together, not separately. `[DECIDE]`

2.12.10 **Polymorphism** — question: "how do I handle behaviour that varies by type?" Answer: assign the
        varying behaviour to the types themselves via a polymorphic operation, never a type test in
        the caller. QuizStakes assignment: `PayoutRail.dispatch()` per rail, not
        `if (rail == CARD)`. `[BUILD]`

2.12.11 **Pure Fabrication** — question: "where does behaviour go when no domain class is a good home,
        and forcing it onto one would wreck cohesion?" Answer: invent a class that is not in the domain
        model. QuizStakes assignment: `LedgerEntryWriter`, `IdempotencyKeyStore`,
        `StatementFileParser`. `[BUILD]`

2.12.12 Pure Fabrication's failure mode, named: it is the licence under which `*Utils`, `*Helper` and
        `*Manager` dumping grounds are created. A legitimate fabrication has a *cohesive*
        responsibility and a domain-meaningful name; `LedgerUtils` has neither (§2.14.60). `[TRAP]`

2.12.13 **Indirection** — question: "how do I avoid direct coupling between two things that should not
        know each other?" Answer: assign the mediating responsibility to an intermediate object.
        QuizStakes assignment: `RouterInt` between callers and instances; `PaymentService` between the
        client request and the rails. Cost: one more hop per call, always. `[DECIDE]`

2.12.14 **Protected Variations** — question: "how do I keep a predicted point of instability from
        rippling?" Answer: wrap it in a stable interface. This is the *generalisation* that OCP, DIP,
        polymorphism and indirection are all instances of — the umbrella pattern, and the honest
        framing of "which pattern" answers. `[PROVE]`

2.12.15 Protected Variations' explicit boundary condition, from Larman: protect against variations that
        are **predicted with evidence**, because speculative protection is speculative generality
        (§2.14.11). The evidence is the rule of three or a named roadmap item. `[DECIDE]`

*(15 leaves)*

## §2.13 Package/component principles: REP, CCP, CRP, ADP, SDP, SAP; coupling and cohesion taxonomies; connascence

2.13.1 Source and scope: Martin's package principles, first published in the *C++ Report* (1996–97),
      collected in *Agile Software Development* (2002) and restated in *Clean Architecture* (2017)
      parts IV. A "component" there is the unit of independent deployment — a jar, a Gradle module, a
      Maven artefact. `[SOURCE]`

2.13.2 **REP — Reuse/Release Equivalence Principle:** the granule of reuse is the granule of release.
      Classes grouped into a component must be releasable together, with a version number and release
      notes, and every class in the release must make sense as part of it. `[SOURCE]`

2.13.3 **CCP — Common Closure Principle:** gather into one component the classes that change for the
      same reasons and at the same times; separate those that change for different reasons. CCP is SRP
      at component scope (§2.6.16). `[SOURCE]`

2.13.4 **CRP — Common Reuse Principle:** do not force users of a component to depend on things they do
      not need. Its practical form is the contrapositive — classes that are not reused together should
      not be in the same component. CRP is ISP at component scope. `[SOURCE]`

2.13.5 The **cohesion tension triangle**: REP and CCP are *inclusive* (they make components larger),
      CRP is *exclusive* (it makes them smaller). Over-weighting REP+CCP gives too many irrelevant
      releases for your users; over-weighting CRP gives too many components to version and too many
      release cascades. There is no simultaneous optimum, and the balance shifts with project maturity
      — early projects favour CCP (developability), mature ones favour REP+CRP (reusability). `[DECIDE]`

2.13.6 **ADP — Acyclic Dependencies Principle:** "allow no cycles in the component dependency graph."
      The mechanism of harm: a cycle is the real module, so no member of it can be built, tested,
      versioned or deployed independently, and the "morning after syndrome" returns. `[SOURCE]`

2.13.7 ADP's two break moves, both stated: (a) apply DIP — insert an interface owned by one side and
      point the other at it; (b) create a new component that both depend on, holding the shared
      concept. A third move specific to services: invert one direction with a domain event so the
      caller becomes a reactor. `[PROVE]`

2.13.8 **SDP — Stable Dependencies Principle:** "depend in the direction of stability" — for
      `A → B`, require `I(B) ≤ I(A)`. Depend on things harder to change than you are. `[SOURCE]`

2.13.9 The instability metric, with the exact formula: `Fan-in` = incoming dependencies (classes
      outside the component depending on classes inside it, Martin's `Ca`, afferent coupling);
      `Fan-out` = outgoing (`Ce`, efferent coupling); **`I = Fan-out / (Fan-in + Fan-out)`**, range
      0..1. `I = 0` is maximally stable (everyone depends on it, it depends on nobody); `I = 1` is
      maximally unstable. `[NUM]`

2.13.10 **SAP — Stable Abstractions Principle:** a component should be as abstract as it is stable. A
        stable component must be abstract so its stability does not prevent extension; an unstable
        component should be concrete because its instability makes concrete code easy to change. SAP is
        the component-level statement of DIP. `[SOURCE]`

2.13.11 The abstractness metric: **`A = Na / Nc`**, where `Na` = number of abstract classes and
        interfaces in the component and `Nc` = the *total* number of classes in it. Range 0..1.
        **Trap:** secondary sources frequently render `Nc` as "number of concrete classes", which
        makes `A` unbounded; Martin's definition is total classes. `[NUM]`

2.13.12 The **main sequence** and the distance metric: the desirable locus is the line `A + I = 1`,
        running from (0,1) maximally-unstable-and-concrete to (1,0) maximally-stable-and-abstract.
        Distance is **`D = |A + I − 1|`** (Martin also defines a non-normalised
        `D = |A + I − 1| / √2`; the normalised form is what tools report), range 0..1, and any
        component with `D` near 1 is in a **zone of exclusion**. `[NUM]`

2.13.13 The two zones of exclusion named: the **zone of pain** at (0,0) — highly stable *and* concrete,
        the classic rigid database schema or utility jar everyone depends on and nobody can change;
        and the **zone of uselessness** at (1,1) — highly abstract with nobody depending on it, i.e.
        dead abstractions. `[PROVE]`

2.13.14 The QuizStakes reading: a `quizstakes-domain` module should sit near `A=0.7, I=0.1`
        (`D ≈ 0.2`); a `bankwithdrawal-file-adapter` near `A=0.0, I=0.9` (`D ≈ 0.1`). A shared
        `quizstakes-common` module with 40 concrete DTOs and 22 dependents lands at
        `A≈0.05, I≈0.1` → `D ≈ 0.85` — the zone of pain, which is the metric explaining why every
        "common" module rots. `[NUM]`

2.13.15 Tooling that computes these, by name: `jdeps` for the raw graph, JDepend and `pdepend` for
        `A`/`I`/`D`, SonarQube/NDepend for the abstractness-instability chart, ArchUnit's
        `slices().should().beFreeOfCycles()` for ADP as a failing test. `[API]`

2.13.16 The **coupling taxonomy** — Stevens, Myers & Constantine, "Structured Design" (*IBM Systems
        Journal*, 1974); Yourdon & Constantine (1979). Worst to best: **content** (one module alters
        another's internals), **common** (both refer to the same global/shared mutable state),
        **control** (one passes a flag that decides the other's behaviour), **stamp** (a whole
        structure is passed where a field would do), **data** (only the parameters needed), and
        **no coupling**. `[TABLE]`

2.13.17 The taxonomy's Java instances, each named: content = reflection into private fields or
        `setAccessible(true)`; common = a `static` mutable registry; control = `process(boolean
        isBankRail)`; stamp = passing the whole `Wager` aggregate to a method that reads only
        `stake()`; data = passing `Money`. `[BUILD]`

2.13.18 Control coupling deserves its own leaf because it is the commonest and least recognised: a
        boolean or enum parameter that selects a branch inside the callee means the caller knows the
        callee's internal structure, and the fix is two methods or a strategy (§2.14.61). `[SMELL]`

2.13.19 Two modern coupling axes the 1974 taxonomy predates, and 24 must name: **temporal coupling**
        (A must be called before B, unenforced by types — §2.14.37) and **deployment coupling** (two
        components that must ship together, the definitive distributed-monolith test — §2.14.62). `[PROVE]`

2.13.20 The **cohesion taxonomy** — same lineage, worst to best: **coincidental** (grouped for no
        reason — `Utils`), **logical** (grouped by category, selected by a flag), **temporal** (grouped
        because they run at the same time — `startup()`), **procedural** (a fixed call order),
        **communicational** (operate on the same data), **sequential** (each output feeds the next),
        **functional** (all contribute to exactly one well-defined task). `[TABLE]`

2.13.21 The cohesion taxonomy's QuizStakes readings: `LedgerUtils` = coincidental;
        `NotificationChannel.sendSms/sendEmail/sendPush` behind a flag = logical;
        `ApplicationStartupTasks` = temporal; the `SettlementJob` load→validate→settle→audit pipeline
        = sequential; `StakeReservation.reserve()` = functional. `[BUILD]`

2.13.22 **Connascence** — origin: Meilir Page-Jones, *What Every Programmer Should Know About
        Object-Oriented Design* (1995) / *Fundamentals of Object-Oriented Design in UML* (1999). Two
        components are connascent if a change in one requires a matching change in the other for
        overall correctness. It refines "coupling" from a binary into a *graded taxonomy with
        refactoring directions*. `[SOURCE]`

2.13.23 **Static connascence** — detectable by reading the code / at compile time. Five kinds, weakest
        to strongest, and each must appear with its own leaf below: name, type, meaning, position,
        algorithm. `[TABLE]`

2.13.24 **CoN — connascence of name:** multiple components must agree on a name. The weakest and most
        desirable form, and the one every IDE rename refactoring handles safely. Instance: every
        caller of `FundsLedger.reserve`. `[API]`

2.13.25 **CoT — connascence of type:** components must agree on the type of an entity. Instance:
        `reserve(Money, ClientId)` — the compiler enforces it, which is exactly why converting
        stronger forms *into* CoT is the standard refactoring (primitive obsession → value objects). `[BUILD]`

2.13.26 **CoM — connascence of meaning / convention:** components must agree on the *meaning* of
        particular values. Instance: `status = 1` meaning success, or `restrictionCode = "SE"` meaning
        self-excluded, or a `-1` sentinel return. Fix: replace the magic value with a named constant or
        enum, converting CoM → CoN. `[SMELL]`

2.13.27 **CoP — connascence of position:** components must agree on the order of values. Instances:
        positional constructor arguments (two adjacent `String`s are swappable without a compile
        error), the field order of a CSV statement row, the order of a `Object[]` varargs log payload.
        Fix: builder or record with named components, converting CoP → CoN. `[BUILD]`

2.13.28 **CoA — connascence of algorithm:** components must agree on a particular algorithm. Instances:
        an idempotency-key hash computed independently in `PaymentService` and `FundsLedger`; a
        checksum written by the file generator and verified by the bank; a password hash. Fix: a single
        shared implementation, converting CoA → CoN. `[INCIDENT]`

2.13.29 **Dynamic connascence** — only observable at runtime, and therefore uniformly stronger than
        every static form. Four kinds: execution, timing, value, identity. `[TABLE]`

2.13.30 **CoE — connascence of execution (order):** the order of execution matters. Instance:
        `reservation.lock()` must be called before `reservation.post()`; a builder whose `build()`
        must follow every setter. Also the temporal-coupling smell (§2.14.37). `[SMELL]`

2.13.31 **CoTi — connascence of timing:** the *timing* of execution matters. Instances: a reservation
        expiry index assuming settlement arrives within N seconds; a race between a client's cancel
        and the `PaymentRun` pick-up (§12.4); any sleep-based test. `[INCIDENT]`

2.13.32 **CoV — connascence of value** and **CoI — connascence of identity:** CoV = several values must
        change together (the four ledger positions whose sum must stay zero; a `@Version` field and
        the row it guards) — the reason a transaction boundary and an aggregate boundary coincide.
        CoI = two components must reference *the same instance* (two threads sharing one
        `ConcurrentHashMap`; a listener list identity). Both are the strongest forms and CoI is the
        hardest to see. Plus the three properties — **strength** (how hard the dependency is to detect
        and change: static < dynamic, name < type < meaning < position < algorithm < execution <
        timing < value < identity), **degree** (how many components share it), **locality** (how close
        they are) — and the two refactoring rules they imply: (1) convert strong connascence into
        weaker connascence; (2) where you cannot weaken it, **increase locality** — move the connascent
        elements closer together, because strong connascence inside one class is acceptable and the
        same connascence across two services is a defect. `[PROVE]`

*(32 leaves)*

## §2.14 The anti-pattern catalogue, each with its failure mechanism, not just its name

2.14.1 **God object / god service.** Mechanism: every actor's change lands in one file, so merge
       contention is continuous, the unit test needs 40 mocks, and nobody can hold the class in their
       head — so all changes are made *additively and defensively* rather than by editing, which
       accelerates the growth. Detection: dependency count, git churn, fan-in/fan-out, LCOM4. `[SMELL]`

2.14.2 **Anemic domain model.** Mechanism: entities are field bags with public setters, so *any*
       caller can put the object into any field combination. Invariants therefore cannot be enforced
       at the object, so validation is duplicated into every service, and one path always forgets. The
       object has data but no *guarantees*, so you cannot reason locally about validity. `[PROVE]`

2.14.3 **Anemic model — when it is still defensible.** For CRUD-shaped domains with thin rules
       (`ClientAgreements`' acceptance records, `ApplicationHistory`' append-only rows), anemic plus
       transaction script is a legitimate deliberate choice: fewer types, less mapping, and no
       invariant to protect. What loses interview points is not knowing you chose it, or defending it
       for `FundsLedger`, where there are nine named invariants (§11.7). `[DECIDE]`

2.14.4 **Service layer as transaction script.** Mechanism of decay: business rules accumulate as
       conditionals inside procedural methods rather than as domain concepts, so the same rule appears
       in three scripts with drifting details and there is nowhere to put the *concept*. Symptom: a
       400-line `@Transactional` method with nested `if`s over a status string. `[SMELL]`

2.14.5 **Circular dependencies.** Mechanism: `funds → bonus → funds` means neither can be compiled,
       tested, versioned, or deployed alone — the cycle is the real module and it is bigger than
       either package. At bean level Spring resolves a constructor cycle only by failing (or lazy
       proxying), and field injection *hides* it. Break with DIP or a third module (§2.13.7). `[X-REF 07]`

2.14.6 **Primitive obsession.** Mechanism: with `String clientId, String currency, BigDecimal amount`
       the compiler cannot distinguish a `clientId` from a `wagerId`, so argument transposition is a
       runtime bug; and "currency is a 3-letter ISO code" has no home, so it is re-validated or
       skipped at every boundary. Fix: value objects — connascence of meaning → of type (§2.13.25). `[BUILD]`

2.14.7 **Feature envy.** Mechanism: a method that reads mostly another object's data puts behaviour on
       the wrong side of a boundary, so every change to the data's *shape* ripples into the envious
       method. Move the method to the data's owner. `[SMELL]`

2.14.8 **Leaky abstraction.** Mechanism: the interface is clean but the *failure modes and performance*
       are not, so callers must know the implementation anyway. Instances: a repository returning
       entities that throw `LazyInitializationException` outside the session; a "transparent" cache
       whose staleness callers must reason about; a port whose timeout is the vendor's 11 s p99. `[X-REF 08]`

2.14.9 **Singleton as global mutable state.** Mechanism: `static` mutable state is invisible in
       constructor signatures (so coupling is undeclared), defeats substitution in tests, makes tests
       order-dependent because state leaks between them, and is a shared-mutable-state concurrency
       hazard by construction. The *lifecycle* is fine; the *global static access path* is the
       anti-pattern. `[PROVE]`

2.14.10 **Over-engineering with patterns.** Mechanism: an abstract factory producing a strategy
        consumed by a decorator chain, for one implementation that has never changed. Each indirection
        costs a hop when reading, so "where does this actually happen" takes 20 minutes instead of 20
        seconds, and stack traces stop naming your logic. `[INCIDENT]`

2.14.11 **Speculative generality.** Mechanism distinct from 2.14.10: a hook, a type parameter, or an
        `abstract` method added for a requirement that never arrived. It is dead weight the compiler
        cannot prove is dead, so it survives every cleanup, and its unused branch is untested and
        therefore wrong by the time it is needed. `[SMELL]`

2.14.12 **Poltergeist.** Mechanism: a short-lived stateless class whose only job is to call another
        class — a `StakeReservationInvoker` that constructs a `StakeReservation` and calls it. It adds
        a name, a file, and a stack frame while adding no responsibility, so it is pure reading cost. `[SMELL]`

2.14.13 **Yo-yo problem.** Mechanism: an inheritance chain so deep that following one call requires
        flipping between many class definitions, because each level implements part of the behaviour.
        The cost is not aesthetic — the reader cannot determine which override actually runs without
        executing it. `[SMELL]`

2.14.14 **Lava flow.** Mechanism: dead or low-quality code retained because removing it is expensive or
        its blast radius is unknown. It hardens: each release makes it older, more referenced, and
        less understood, so the removal cost rises monotonically while the value stays zero. `[SMELL]`

2.14.15 **Big ball of mud.** Mechanism (Foote & Yoder, 1997): a system with no perceivable
        architecture — every module reachable from every other, so the *cost of any change is
        unbounded and unpredictable*, which is the actual failure, not the ugliness. Its cause is
        expedient local decisions, each individually rational. `[SOURCE]`

2.14.16 **Golden hammer.** Mechanism: a familiar technology applied obsessively regardless of fit, so
        the design's forces are never articulated — the answer preceded the question. Symptom in
        interviews: proposing Kafka, or event sourcing, before the requirements are stated. `[TRAP]`

2.14.17 **Magic strings.** Mechanism: a literal string used for comparison or dispatch
        (`if ("SELF_EXCLUDED".equals(code))`) creates connascence of meaning across every file that
        repeats it, with no compiler check and no rename support. A typo is a silently-false branch,
        not an error. `[SMELL]`

2.14.18 **Magic numbers.** Mechanism: an unexplained literal (`if (attempts > 3)`, `amount * 0.10`)
        encodes a business rule with no name and no single home, so the rule cannot be found, changed,
        or tested as itself. In QuizStakes the bonus 10% and cap 100, the 3 document attempts and the
        14-day coupon window are all named constants or config, never literals. `[NUM]`

2.14.19 **Boat anchor.** Mechanism: a component retained with no current use — a purchased library, a
        staging service, an unused abstraction layer — that still costs CVE patching, build time,
        upgrade blocking and onboarding confusion. The cost is *ongoing* and the benefit is zero,
        which is what distinguishes it from lava flow (whose removal is risky). `[SMELL]`

2.14.20 **Spaghetti code.** Mechanism: control flow, not structure, is the problem — deep nesting,
        early mutation, and jumps mean the reader must simulate the program to know the state at any
        line, so the number of paths to test grows multiplicatively. Cyclomatic complexity is the
        proxy metric. `[SMELL]`

2.14.21 **Ravioli code.** Mechanism: the opposite failure and the one over-applied SRP produces — many
        tiny well-formed classes with no visible composition, so no single file shows the use case and
        understanding it requires traversing fifteen one-method classes. Named to prevent 2.14.20's
        cure from becoming the disease. `[TRAP]`

2.14.22 **Shotgun surgery.** Mechanism: one conceptual change requires edits in many files, because the
        concept has no single owner. In a package-by-layer codebase adding one field to a withdrawal
        touches controller, DTO, mapper, service, entity, repository, migration — seven files for one
        idea. Change amplification is the metric; package-by-feature is the structural fix. `[SMELL]`

2.14.23 **Inner-platform effect.** Mechanism: a system made so configurable that it becomes a poor
        re-implementation of the platform it is built on — a database-driven rule engine that grows
        variables, conditionals and loops until it is an untyped, undebuggable, unprofilable
        programming language with no tooling. The tell: someone asks for "an else branch" in the
        config. `[INCIDENT]`

2.14.24 **Accidental complexity.** Mechanism (Brooks, "No Silver Bullet", 1986): complexity introduced
        by the solution rather than inherent in the problem. It is the measurement that matters —
        subtract the essential complexity (the domain's real invariants) and everything left is
        accidental and in principle removable. `[SOURCE]`

2.14.25 **Stringly-typed code.** Mechanism: domain concepts represented as `String`/`Map<String,
        Object>` so that every read is a parse, every write is unvalidated, and every rename is a
        text search. It is primitive obsession's extreme, and it moves all errors from compile time to
        the request path. `[SMELL]`

2.14.26 **Exception swallowing.** Mechanism: `catch (Exception e) {}` or `catch (Exception e)
        { log.debug(...); }` destroys the failure signal, so the system continues on corrupt state and
        the eventual symptom appears far from the cause. In a money path it converts a failed ledger
        post into a silent balance discrepancy discovered at reconciliation, days later. `[INCIDENT]`

2.14.27 **`catch (Exception)` as flow control.** Mechanism: using exceptions for expected outcomes
        (catching `NumberFormatException` to test whether a string is numeric) costs stack-trace
        capture per occurrence, hides the real path from the reader, and catches unrelated failures
        that happen to share the type. Fix: a predicate, `Optional`, or a result type. `[X-REF 03]`

2.14.28 **Premature optimisation.** Mechanism: optimising before measuring changes the design to serve
        a bottleneck that is not the bottleneck, and the design change is permanent while the
        performance claim is unverified. The precise cost is that it forecloses the *actual* fix —
        an object pool of DTOs (§1.12) makes the allocation path worse and the GC path worse. `[X-REF 25]`

2.14.29 **Copy-paste programming.** Mechanism: the copies diverge silently, so a bug fixed in one is
        still live in four, and there is no artefact recording that they were once the same. Distinct
        from deliberate duplication (§2.11.25), which is a *decision* pending the third case. `[SMELL]`

2.14.30 **Reinventing the wheel.** Mechanism: a hand-written retry, circuit breaker, or JSON parser
        carries all the edge cases the library already solved, but none of the tests, fuzzing, CVE
        process, or documentation. The cost is not the writing, it is the *maintenance and the
        unknown-unknowns*. `[DECIDE]`

2.14.31 **Reinventing the square wheel.** Mechanism: the same as 2.14.30 but where the custom version
        performs measurably worse than the existing one — worth its own leaf because it is the case
        that survives review ("ours is faster") without a benchmark. `[SMELL]`

2.14.32 **Vendor lock-in by leakage.** Mechanism: the vendor's types are not confined to an adapter, so
        `com.stripe.model.Charge` or `com.amazonaws.*` appears in domain signatures and the switching
        cost becomes proportional to the codebase, not to the integration. The QuizStakes rule "every
        external vendor sits behind exactly one owning service" (§5.1) is the structural defence. `[PROVE]`

2.14.33 **Abstraction inversion.** Mechanism: a rich primitive is hidden behind a poorer interface, so
        clients re-implement the missing capability *on top of* the wrapper — a repository exposing
        only `findById` forces callers to loop it N times, re-creating the N+1 problem the underlying
        query language could have avoided. `[SMELL]`

2.14.34 **Base bean.** Mechanism: inheriting from a utility class to gain its methods rather than
        delegating to it. The subtype now `is-a` something it is not, spends its single inheritance
        slot, and exposes the utility's whole surface as its own public API. `[SMELL]`

2.14.35 **Call super.** Mechanism: a base class whose contract requires overrides to invoke
        `super.method()`, an obligation the compiler cannot enforce, so forgetting it produces a
        silent partial execution. Fix: template method — a `final` skeleton that calls a `protected
        abstract` hook, making the call site the base's business (§1.21). `[BUILD]`

2.14.36 **Circle–ellipse problem (square/rectangle).** Mechanism: subtyping on *value* subsets rather
        than behaviour. A mutable `Ellipse.setWidth` cannot be inherited by `Circle` without breaking
        the circle's invariant — the canonical proof that `is-a` in the domain is not `is-a` in the
        type system when mutators exist. Immutability dissolves it. `[PROVE]`

2.14.37 **Sequential / temporal coupling.** Mechanism: a class requiring its methods to be called in a
        particular order (`open()` then `write()` then `close()`; `reserve()` before `settle()`) with
        no type-level enforcement, so an out-of-order call is a runtime failure or a leak. Connascence
        of execution (§2.13.30). Fix: staged builders returning a different type per stage, or one
        method that does the sequence. `[BUILD]`

2.14.38 **Object orgy.** Mechanism: encapsulation not enforced — public fields, public setters,
        package-wide `public` classes — so any invariant is only a convention. This is what
        package-by-layer *forces*, because the layer above needs `public` to reach in. `[PROVE]`

2.14.39 **Object cesspool.** Mechanism: reusing pooled objects whose state was not reset, so the next
        borrower inherits the previous user's data — the classic cross-request leak (a pooled
        buffer or `ThreadLocal`-carrying object leaking one client's tenant context into another's
        request). `[X-REF 05]`

2.14.40 **Constant interface.** Mechanism: an interface holding only `static final` constants
        (`interface RestrictionCodes`), implemented purely to import them. The constants become part
        of the implementor's exported API forever, and the implements clause is a lie about type.
        *Effective Java* item 22. Fix: a `final` class with a private constructor, or an enum. `[SOURCE]`

2.14.41 **Database as IPC.** Mechanism: using a table as a message queue between services. It couples
        both to a schema neither owns, gives no delivery semantics, and turns polling load into
        baseline database load. Distinguish carefully from the *transactional outbox*, which is the
        legitimate form because the table is owned by the producer and read by exactly one relay. `[X-REF 14]`

2.14.42 **Soft code.** Mechanism: business logic pushed into configuration to avoid a deploy, so the
        logic loses type checking, tests, review, version history and stack traces — you have traded
        a deployment pipeline for an untested one. The near neighbour of 2.14.23. `[TRAP]`

2.14.43 **Hard code.** Mechanism: the inverse — environment assumptions embedded in source (a hostname,
        a currency, a jurisdiction), so a legitimate per-environment difference requires a code change
        and every environment's build differs. `[SMELL]`

2.14.44 **Input kludge.** Mechanism: ad-hoc handling of invalid input at each site instead of a
        specified validation boundary, so each site is differently wrong and the domain receives
        values no invariant covers. The fix is a single parse-don't-validate boundary that produces
        already-valid value objects. `[BUILD]`

2.14.45 **Interface bloat.** Mechanism: an interface made so capable that implementing it fully is
        impractical, so every implementation is partial (§2.8.14) and every client must know which
        parts work. ISP (§2.9) is the corrective, and `Collection`'s "optional operations" is the JDK
        living with the consequence. `[PROVE]`

2.14.46 **Loop-switch sequence.** Mechanism: encoding a fixed sequence of steps as a `switch` inside a
        `for` over a step counter. The ordering becomes data the compiler cannot check, adding a step
        means renumbering, and the reader must simulate the loop to recover the sequence. Fix:
        template method or an explicit pipeline. `[SMELL]`

2.14.47 **Cargo cult programming.** Mechanism: copying a structure without its force — `@Transactional`
        on every method, a `Repository` interface per entity, a DTO per layer — because a reference
        architecture had them. The structure's cost is paid and its benefit is absent, and nobody can
        justify removing it because nobody knows why it is there. `[TRAP]`

2.14.48 **Coding by exception.** Mechanism: adding a special-case branch per newly discovered input
        rather than fixing the model, so complexity grows linearly with bug reports and each branch
        is reachable only by the one input that motivated it. The `if (clientId.equals("legacy-…"))`
        family. `[SMELL]`

2.14.49 **Action at a distance.** Mechanism: unexpected interaction between widely separated parts via
        shared mutable state — a `static` config object, a `ThreadLocal`, a mutated shared collection
        — so a change here produces a failure there with no path between them in the source. Common
        coupling (§2.13.16) made concrete. `[INCIDENT]`

2.14.50 **Blind faith.** Mechanism: shipping a fix or trusting a subroutine's result without a check —
        the specific failure being the missing *assertion*, so a wrong answer propagates. In money
        paths it is the absent post-condition: a movement's entries must sum to zero and nothing
        verifies it. `[PROVE]`

2.14.51 **Busy spin.** Mechanism: burning CPU polling for a condition instead of blocking on it, so a
        thread that should cost nothing costs a core, and under load the polling competes with the
        work it is waiting for. Fix: a `BlockingQueue`, a condition variable, or `onSpinWait()` where
        spinning is genuinely right. `[X-REF 05]`

2.14.52 **Gold plating.** Mechanism: continuing to work past the point where extra effort adds value.
        Distinct from speculative generality: gold plating is *finished* work nobody asked for, and it
        still must be maintained, documented and tested forever. `[SMELL]`

2.14.53 **Dependency hell / JAR hell.** Mechanism: transitive version conflicts where two dependencies
        require incompatible versions of a third, and the classpath resolves it by *first wins* —
        producing `NoSuchMethodError` at runtime rather than a build failure. Detection: `mvn
        dependency:tree`, `gradle dependencyInsight`, enforcer rules. `[API]`

2.14.54 **Stovepipe system.** Mechanism: a barely maintainable assemblage of ill-related components
        integrated point-to-point, so every pair has its own bespoke contract and the integration
        count grows as N². Its organisational twin (siloed teams) is Conway's law producing the
        architecture. `[SMELL]`

2.14.55 **`Utils`/`Helper` dumping ground.** Mechanism: a class with coincidental cohesion (§2.13.20)
        that becomes the default home for anything without an obvious owner, so it acquires every
        module's dependencies and every module depends on it — maximum fan-in and fan-out at once,
        landing in the zone of pain (§2.13.13). `[SMELL]`

2.14.56 **Boolean trap / flag parameter.** Mechanism: `submit(withdrawal, true)` is unreadable at the
        call site and is control coupling (§2.13.18) — the caller is selecting a branch inside the
        callee, so the callee's internal structure is now part of its contract. Fix: two named
        methods, or an enum parameter. `[BUILD]`

2.14.57 **Static cling.** Mechanism: a static call to a collaborator (`LedgerClient.post(...)`,
        `Instant.now()`) is an undeclared dependency that no test can substitute without a bytecode
        agent, so the unit under test drags the real collaborator in. Fix: inject the collaborator —
        a `Clock` bean rather than `Instant.now()`. `[X-REF 16]`

2.14.58 **Service locator / ambient context.** Mechanism: `context.getBean(Foo.class)` hides the
        dependency from the constructor signature, so the type no longer documents what it needs and
        a missing dependency becomes a runtime failure at first use instead of a startup failure.
        Fowler's own comparison names DI as preferable for exactly this. `[TRAP]`

2.14.59 **Hexagonal in name only.** Mechanism: the vocabulary adopted without the dependency direction
        — the port interface lives in the infrastructure package, the domain imports
        `jakarta.persistence`, or the use case returns an entity. You now pay the mapping cost and
        the extra types while getting none of the isolation. Test: §2.10.4 and §2.10.7. `[TRAP]`

2.14.60 **Big-bang rewrite / second-system effect.** Mechanism (Brooks): the replacement is specified
        against the *current* understanding while the original keeps changing, so the two diverge and
        the cutover date recedes. The alternative is named: strangler fig plus branch-by-abstraction
        (§2.25), which keeps every intermediate state shippable. `[DECIDE]`

2.14.61 **Log-and-rethrow.** Mechanism: catching, logging, and rethrowing at every layer multiplies one
        failure into N stack traces in the log, so the on-call engineer cannot tell whether there was
        one incident or five, and log volume spikes exactly when the system is unhealthy. Rule: handle
        or propagate, log once at the boundary that decides the response. `[X-REF 20]`

2.14.62 **Distributed monolith.** Mechanism: services split by layer or by entity table rather than by
        bounded context, so every use case fans out across five services, they share a database, and
        they must be deployed together. Every microservices cost is paid and no benefit is bought.
        Diagnostics: do two services write the same table? Does a feature require a coordinated
        release? Is there a service whose only job is to read another's data? **Shared database is the
        definitive tell** — it makes the schema a public API that nobody owns. `[X-REF 22]`

2.14.63 **Entity service.** Mechanism: a service per database table (`ClientService`, `AddressService`)
        rather than per business capability, so no service owns a use case and every use case is an
        orchestration across many. It guarantees 2.14.62, because a capability's data is spread across
        services and the only way to join it is a shared database or a chatty fan-out. `[X-REF 22]`

2.14.64 **Nanoservice.** Mechanism: decomposition past the point where a service's own operational
        overhead (pipeline, dashboard, alert set, deployment, on-call) exceeds the value of its
        independent deployability. The arithmetic is the argument: a 200-line service still needs the
        full N-per-service ops surface. `[X-REF 22]`

2.14.65 **Chatty service.** Mechanism: a granularity mismatch converting one in-process call graph into
        many remote calls, so latency is additive and availability is multiplicative — a use case that
        touched 4 modules at ~10 ns each now costs 4 serial hops at 0.5–1 ms, and six 99.99% services
        in series give 99.94%. Fixes: coarser-grained operations, API composition, or a read model. `[X-REF 22]`

2.14.66 **Death-star architecture.** Mechanism: every service calling every other, so the dependency
        graph has no direction and no layer — the N² edge count means no service can be reasoned
        about, deployed, or blast-radius-bounded independently, and one slow node's backpressure
        reaches everywhere. This is ADP (§2.13.6) violated at service scale. `[X-REF 22]`

2.14.67 **Design by committee.** Mechanism: many contributors and no unifying vision, so every
        stakeholder's requirement is added rather than traded off — the design accumulates the union
        of all preferences and satisfies none of the forces. The architectural tell is an interface
        that is the union of every consumer's wish list (§2.14.45), and the Staff-level defence is a
        named decision owner plus an ADR recording what was *rejected*. `[X-REF 26]`

2.14.68 **Mythical man-month / Brooks' law.** Mechanism (Brooks, 1975): "adding manpower to a late
        software project makes it later", because communication paths grow as `n(n−1)/2` and new
        people consume the time of the people who already understand the system. The design
        consequence 24 owns: a module with no clear boundary cannot absorb a new engineer in
        parallel, so *architecture is the constraint on how fast a team can be grown*. `[X-REF 26]`

2.14.69 **Analysis paralysis.** Mechanism: disproportionate effort in analysis, driven by trying to
        pick the seam before the third case exists (§1.5). It fails because the information needed to
        place the seam is only produced by shipping, so more analysis cannot converge — the exit
        condition is a reversible decision, not a complete one. `[X-REF 26]`

2.14.70 **Not-invented-here (NIH) syndrome.** Mechanism: rejecting external solutions on ownership
        grounds rather than on evaluated fit, so the build/buy decision is made by identity instead
        of by cost. The technical sibling is §2.14.30–2.14.31; this leaf is the *organisational*
        cause, and it is why the same team rebuilds a circuit breaker every two years. `[X-REF 26]`

2.14.71 **Escalation of commitment / sunk-cost fallacy.** Mechanism: continued investment justified by
        what has already been spent rather than by remaining expected value, which is exactly what
        keeps a wrong abstraction (§2.11.25) and a big-bang rewrite (§2.14.60) alive past the point of
        evidence. The counter-mechanism is a pre-registered kill criterion stated when the work
        starts, because it cannot be set credibly afterwards. `[X-REF 26]`

2.14.72 **Silver bullet.** Mechanism (Brooks, "No Silver Bullet", 1986): believing one technology or
        process removes the *essential* complexity of the problem, when by construction it can only
        reduce accidental complexity (§2.14.24). Every claimed order-of-magnitude win is therefore
        bounded by the accidental share, which is the arithmetic that kills the claim. `[X-REF 26]`

2.14.73 **Ambiguous viewpoint.** Mechanism: presenting a model without stating whose view it is —
        conceptual, specification, or implementation — so readers silently disagree about whether a
        box is a class, a deployable, or a business capability. It is the commonest whiteboard failure
        in a design round, and the fix is one sentence naming the viewpoint before drawing. `[X-REF 26]`

2.14.74 **Programming by permutation (trial-and-error coding).** Mechanism: converging on behaviour by
        successively perturbing code until the symptom disappears, without a model of why. It
        terminates on a passing test rather than on a correct mechanism, so the defect survives as a
        latent one and the "fix" is unexplainable in review. The counter is a stated hypothesis before
        each change. `[X-REF 26]`

2.14.75 **Organisational silos / stovepipe organisation.** Mechanism: a structure carrying data up and
        down but not across, so cross-team integration contracts are negotiated once and never
        revisited. Conway's law then makes it an architecture — team boundaries become service
        boundaries whether or not they match bounded contexts, which is the organisational cause of
        the entity-service split (§2.14.63). `[X-REF 26]`

2.14.76 **Moral hazard.** Mechanism: insulating a decision-maker from the consequences of the decision,
        so the party choosing the design does not carry its operational cost. The concrete instance:
        a team that ships without being on call optimises for delivery date over debuggability, and
        no amount of review corrects an incentive. `[X-REF 26]`

2.14.77 **Cash cow.** Mechanism: a profitable legacy product funds complacency, so its architecture is
        never paid down and the revenue that justifies leaving it alone is the same revenue that makes
        any change high-risk. The tell is a system nobody is allowed to refactor and nobody is allowed
        to replace. `[X-REF 26]`

*(77 leaves)*

### Sources consulted — lane C

| Source (URL) | What it contributed |
|---|---|
| https://en.wikipedia.org/wiki/Connascence | Connascence origin (Page-Jones), the three properties strength/degree/locality, static-vs-dynamic split, the locality refactoring rule. Did **not** define all nine kinds individually. |
| https://connascence.io/ | Confirmed the exact nine-kind census and its grouping: static = name, type, meaning, position, algorithm; dynamic = execution, timing, value, identity. Used for §2.13.23–2.13.32. |
| https://github.com/serodriguez68/clean-architecture/blob/master/part-4-component-principles.md | Verified `I = Fan-out/(Fan-in+Fan-out)` with Fan-in/Fan-out definitions and the I=0/I=1 endpoints; exact ADP wording ("allow no cycles in the component dependency graph"), SDP ("depend in the direction of stability"); the REP/CCP inclusive vs CRP exclusive tension triangle. Did not carry the A and D formulas. |
| https://www.codeproject.com/Articles/1007524/Object-oriented-metrics-by-Robert-Martin (via search summary) | `A = Na/Nc`, `D = |A + I − 1|`, both 0..1, and the main sequence as the line `A + I = 1`. Also the `Ca`/`Ce` naming for afferent/efferent coupling. |
| https://en.wikipedia.org/wiki/Liskov_substitution_principle + Liskov & Wing *A Behavioral Notion of Subtyping* (1994) via search | The four contract rules by name, including the **history constraint** as Liskov & Wing's novel element; the contravariant-parameter / covariant-return signature shadow; that behavioural subtyping is strictly stronger than signature subtyping. |
| https://www.hillelwayne.com/post/lsp/ | Confirmed the history-rule framing (new subtype methods can permit forbidden state changes) used in §2.8.6 and §2.8.13. |
| http://www.ccs.neu.edu/home/lieber/LoD.html + https://en.wikipedia.org/wiki/Law_of_Demeter | Law of Demeter origin — Ian Holland, Northeastern, autumn 1987, Demeter Project — and the formal "only talk to your friends" unit rules used verbatim in §2.11.1–2.11.2. |
| https://en.wikipedia.org/wiki/GRASP_(object-oriented_design) | The nine-pattern census and Larman 1997 attribution; the responsibility question each answers; the bloated-controller split rule. |
| https://en.wikipedia.org/wiki/Command%E2%80%93query_separation + https://martinfowler.com/bliki/CQRS.html | CQS as Meyer/Eiffel, method-level; CQRS as Greg Young c. 2010, architectural; the explicit statement that they are different in scope (§2.11.14). |
| https://en.wikipedia.org/wiki/Anti-pattern + https://en.wikipedia.org/wiki/Category:Anti-patterns | Named definitions for poltergeist, god object, big ball of mud, magic number; the category index used as the completeness checklist. |
| https://www.bipinpaulbedi.com/57-counterproductive-software-design-practices-anti-patterns/ | The completeness probe that produced §2.14.33–2.14.54: abstraction inversion, base bean, call super, circle–ellipse, constant interface, sequential coupling, object orgy, object cesspool, database as IPC, soft code, hard code, input kludge, interface bloat, loop-switch sequence, cargo cult, coding by exception, action at a distance, blind faith, busy spin, gold plating, dependency hell, stovepipe, reinventing the square wheel — none of which were on my pre-research list. |
| https://en.wikipedia.org/wiki/Yo-yo_problem | Yo-yo mechanism stated as "cannot follow control flow without flipping between definitions", used for §2.14.13. |
| https://en.wikipedia.org/wiki/Robustness_principle | Postel's law wording and its known failure mode (leniency entrenching a de-facto standard). Attribution split between RFC 760 (IP) and 761 (TCP), both 1980 — flagged below. |
| https://www.hyrumslaw.com/ + Winters/Wright, *Software Engineering at Google* via search | Hyrum's law wording and attribution (Hyrum Wright, Google, c. 2011–12; named by Titus Winters). Cited in §2.11 and in the leaky-abstraction leaf. |
| https://sandimetz.com/blog/2016/1/20/the-wrong-abstraction | "Duplication is far cheaper than the wrong abstraction" (RailsConf 2014, blog 2016) and the re-inline prescription — §2.11.25. |
| https://blog.ndepend.com/solid-design-the-single-responsibility-principle-srp/ + https://www.adesso.de/en/news/blog/the-solid-design-principles.jsp | Adversarial angle: the documented commonest misreadings of SRP ("one task"), ISP ("many small interfaces"), DIP ("inversion, not injection") — became the `[TRAP]` leaves 2.6.3, 2.9.2, 2.10.3. |
| https://fpalomba.github.io/pdf/Journals/J16.pdf + https://coupling.dev/posts/related-topics/module-coupling/ | The Stevens/Myers/Constantine (1974) coupling ladder content→common→control→stamp→data→none and the seven cohesion levels including Yourdon & Constantine's later *procedural* addition — §2.13.16 and §2.13.20. |
| https://www.designgurus.io/blog/10-common-microservices-anti-patterns + https://www.infoq.com/articles/cloud-native-architecture-adoption-part2/ | Distributed monolith, chatty services, death star and nanoservice mechanisms for §2.14.62–2.14.66. **Entity service** was not confirmed under that name in any fetched source — see notes. |

### Gaps vs the current guide — lane C

| Syllabus leaf | In `src/topics/24-…` | Verdict |
|---|---|---|
| §2.6.1 (Martin's two wordings, 2002 vs 2017 actor form) | § 5.1, one clause | shallow |
| §2.6.3 (SRP-as-"one thing" trap) | § 5.1 parenthetical "(unfalsifiable)" | shallow |
| §2.6.4–2.6.5 (git-churn / stakeholder-count tests) | absent | missing |
| §2.6.16 (SRP = CCP at class scope) | absent | missing |
| §2.6.18 (LCOM4, ArchUnit detection) | absent | missing |
| §2.7.1–2.7.2 (Meyer 1988 vs Martin's polymorphic reading) | absent | missing |
| §2.7.7 (N+1 files when the interface owner changes) | § 1 "freezing the others", one clause | shallow |
| §2.7.15 (startup assertion moving the error back from request to boot) | § 10 step 4, one clause | shallow |
| §2.7.17 (`default` as OCP for the interface owner) | § 5.4, one clause | shallow |
| §2.8.1 (Liskov 1987 / Liskov & Wing 1994 citation) | absent | missing |
| §2.8.3–2.8.6 (the four contract rules by name, incl. the history rule) | § 5.3 gives two of four informally; history rule absent | shallow/missing |
| §2.8.7–2.8.8 (contravariant params / covariant returns; how much of LSP javac checks) | absent | missing |
| §2.8.15 (`Arrays.asList` fixed-size vs immutable) | § 5.3, one clause | shallow |
| §2.8.16 (`Collection`'s "optional operations" as documented weakening) | absent | missing |
| §2.8.19–2.8.20 (`equals` symmetry under inheritance, *EJ* item 10) | absent | missing |
| §2.8.22 (the "subclass must not throw" misreading) | absent | missing |
| §2.9.1 (ISP's client-side subject; Xerox origin) | § 5.4, implied | shallow |
| §2.9.6–2.9.7 (role vs header interface; client shapes the interface) | absent | missing |
| §2.9.10 (one class implements many role interfaces) | absent | missing |
| §2.9.14–2.9.16 (what `default` did *not* fix; diamond rule, `Interface.super`) | § 5.4 names `default` only as a softener | shallow |
| §2.9.17 (`SequencedCollection`, JEP 431, as ISP done right) | absent | missing |
| §2.10.1 (Martin, *C++ Report* 1996, both clauses quoted) | § 5.5, paraphrased | shallow |
| §2.10.3 (DIP ≠ DI) | absent | missing |
| §2.10.5 (the *inverse* half of the delete test) | § 5.5 gives one half | shallow |
| §2.10.10 (inbound vs outbound ports) | § 7.2, one bullet | shallow |
| §2.10.13–2.10.16 (four compiling DIP violations: Spring Data types in the port, exception leakage, entity returned, `@Component` on a domain class) | § 7.2 trap covers two informally | shallow |
| §2.10.17 (the literal ArchUnit rule) | § 7.2, "ArchUnit can assert it" | shallow |
| §2.11.1–2.11.2 (LoD origin and the formal unit rules) | § 5.6, no origin, no formal rules | shallow |
| §2.11.5–2.11.6 (dot-counting trap; the navigate-vs-configure discriminator) | § 5.6 exception clause | shallow |
| §2.11.7 (Demeter's own cost — middle man) | absent | missing |
| §2.11.8–2.11.10 (Tell-Don't-Ask as a named principle, with its legitimate exception) | § 5.6, one clause | shallow |
| §2.11.11–2.11.14 (CQS: Meyer, the four properties it buys, the JDK violations, CQS≠CQRS) | absent | missing |
| §2.11.17–2.11.19 (self-use documentation problem; *EJ* items 18 and 19 by number) | § 5.7 gives the mechanism, not the citations | shallow |
| §2.11.22 (DRY's actual Hunt & Thomas wording) | § 5.8, paraphrased | shallow |
| §2.11.25–2.11.26 (Metz attribution; the re-inline prescription; the cost arithmetic) | § 5.8, one clause | shallow |
| §2.11.27 (YAGNI attribution) | § 5.8, name only | shallow |
| §2.11.29–2.11.32 (separation of concerns/Dijkstra, Hollywood principle, least astonishment, Postel's law) | absent — the guide names Hyrum's law only, in § 6.6 | missing |
| §2.12.1–2.12.15 (all of GRASP) | absent entirely | missing |
| §2.13.2–2.13.5 (REP, CCP, CRP and the tension triangle) | absent | missing |
| §2.13.6–2.13.7 (ADP by name and its two break moves) | § 6.4 gives the break moves without the principle's name | shallow |
| §2.13.8–2.13.14 (SDP, SAP, `I`, `A`, `D`, main sequence, zone of pain / uselessness) | absent | missing |
| §2.13.15 (`jdeps`, JDepend, ArchUnit slice cycle rule) | § 7.2 mentions ArchUnit generally | shallow |
| §2.13.16–2.13.21 (both 1974 taxonomies, with Java instances) | § 10 lists "coupling and cohesion" as vocabulary only | shallow |
| §2.13.22–2.13.32 (connascence in full) | absent entirely | missing |
| §2.14.11, .12, .13, .14, .15, .16, .19, .20, .21, .22, .23, .24, .25, .27, .29, .30, .31, .33–.61 | absent | missing |
| §2.14.1–2.14.9 (god object → singleton-as-global) | § 6.1–6.7, present with mechanisms | covered — leaves preserve the guide's wording |
| §2.14.62 (distributed monolith, shared-DB tell) | § 7.8 trap, in full | covered |
| §2.14.63–2.14.66 (entity service, nanoservice, chatty, death star) | absent | missing |

### Notes for the orchestrator — lane C

**Leaf count per section and the arithmetic.** §2.6 = 20; §2.7 = 20; §2.8 = 22; §2.9 = 20;
§2.10 = 20; §2.11 = 32; §2.12 = 15; §2.13 = 32; §2.14 = 77.
`20 + 20 = 40`; `+22 = 62`; `+20 = 82`; `+20 = 102`; `+32 = 134`; `+15 = 149`; `+32 = 181`;
`+77 = 258`. **Lane total = 258 leaves** against a 240 target (+7.5%, inside the ±15% band).
Counts were verified on disk by counting lines matching `^2\.<n>\.` per section, not estimated.

§2.14 carries 77 rather than the brief's ~65 because the orchestrator restored the process and
organisational anti-patterns as §2.14.67–2.14.77, all `[X-REF 26]`. §2.14 is therefore three
sub-blocks: intra-service (2.14.1–2.14.61), distributed at the boundary (2.14.62–2.14.66,
`[X-REF 22]`), organisational (2.14.67–2.14.77, `[X-REF 26]`). The write pass should keep that
grouping visible, because the third sub-block is pointed-at material and must not be developed at
the same depth as the first.

**Tag counts for the lane** (occurrences of each tag across all 247 leaves; a leaf may carry only
one tag, and every leaf carries exactly one):

| Tag | Count |
|---|---|
| `[PROVE]` | 40 |
| `[SOURCE]` | 37 |
| `[X-REF nn]` | 32 |
| `[BUILD]` | 32 |
| `[SMELL]` | 31 |
| `[TRAP]` | 20 |
| `[DECIDE]` | 18 |
| `[API]` | 15 |
| `[SAY]` | 10 |
| `[INCIDENT]` | 8 |
| `[NUM]` | 7 |
| `[TABLE]` | 4 |
| `[VERSION-TRAP]` | 2 |
| `[RESEARCH]` | 1 |
| `[FLOW]` | 1 |
| `[DIAG]` | 0 |
| **Total** | **258** |

The total equals the leaf total exactly, which is the check that every leaf carries one and only one
terminating tag. `[DIAG]` is deliberately unused in this lane, per the orchestrator: lane E owns the
ArchUnit failure report at §3.20 and lane F owns the manifest, so §2.10.17 needs no promotion.

The `[X-REF nn]` breakdown by target guide, all sibling-guide pointers, no intra-guide pointers
remaining: 26 ×11, 22 ×5, 03 ×2, 04 ×2, 05 ×2, 08 ×2, 16 ×2, 06 ×1, 07 ×1, 14 ×1, 17 ×1, 20 ×1,
25 ×1 — **32 occurrences, all 32 terminating.** The one former in-line `[X-REF nn]` (§2.6.13, where
the tag was used mid-sentence as a noun) is gone with this sweep.

**History trace, so the retagging is recoverable.** Five leaves lost their only tag to the
self-referential `[X-REF 24]` sweep and were retagged on approval, each by what the leaf obliges the
write pass to do: §2.7.14 → `[BUILD]` (a refactoring move plus a startup assertion to write);
§2.10.9 → `[PROVE]` and §2.10.12 → `[PROVE]` (port/adapter as DIP is an argument to work through);
§2.10.17 → `[API]` (the leaf is a literal ArchUnit rule expression); §2.11.14 → `[SOURCE]`
(Meyer 1988 and Young c. 2010 are both quotable). No other leaf's tag was touched by the sweep.

The intra-guide pointers those tags became: §2.6.13 → §2.15 (already inline, tag deleted);
§2.7.14 → §2.16; §2.10.9 → §2.17 (already inline, tag deleted); §2.10.12 → §2.25; §2.10.17 → §2.29;
§2.11.14 → §2.23 (already inline, tag deleted). Three were already named inline and three were not,
against the orchestrator's estimate of four and three.

**What I could not verify, named with the constant and the source that would settle it:**

1. **Martin's `D` normalisation.** Sources agree on `D = |A + I − 1|` (range 0..1) and separately
   report a non-normalised `D = |A + I − 1| / √2`. I could not open Martin's own 1996 *C++ Report*
   paper — `https://staff.cs.utu.fi/~jounsmed/doos_06/material/DesignPrinciplesAndPatterns.pdf`
   failed with a TLS error ("unable to verify the first certificate"). §2.13.12 states both forms
   and marks the normalised one as what tools report. **Settled by:** *Agile Software Development:
   Principles, Patterns, and Practices* (2002), ch. 20, "Distance from the Main Sequence".
2. **`A = Na/Nc` denominator.** Secondary sources split between `Nc` = *total* classes (correct,
   keeps `A` in 0..1) and `Nc` = *concrete* classes (makes `A` unbounded). I have asserted "total"
   and made the misstatement itself a trap in §2.13.11. **Settled by:** the same chapter.
3. **Postel's law's RFC number.** Wikipedia's robustness-principle article attributes it to the
   early TCP/IP specifications; the search summary said "the 1979 IPv4 specification". RFC 760 (IP)
   and RFC 761 (TCP) are both January 1980, and RFC 1122 §1.2.2 restates it. §2.11.32 cites
   "RFC 760/761, 1980" and carries `[RESEARCH]`. **Settled by:** reading RFC 761 §2.10 directly.
4. **"Entity service" as a named anti-pattern.** No fetched source used that exact name; the
   concept (a service per table rather than per capability) is well attested under other names.
   §2.14.63 is written with the mechanism, but the *name*'s attribution is unconfirmed. **Settled
   by:** Richards, *Microservices AntiPatterns and Pitfalls* (O'Reilly, 2016), which the brief's
   version baseline implies is the intended source.
5. **`LCOM4` (§2.6.18)** — I have named it as the cohesion proxy metric; I did not verify which
   tools still compute it (SonarQube removed LCOM4 from its default profile at some point).
   Flagged so the write pass does not promise a Sonar rule that no longer exists.

**Judged out of this topic's scope, and where I sent it:**

- **Resolved by the orchestrator, no longer out of scope.** I had dropped the process and
  organisational anti-patterns on the grounds that no sibling owned process; guide 26
  (`26-behavioral-leadership.md`) does. They are restored as §2.14.67–2.14.77 with one-line
  mechanisms and `[X-REF 26]`: design by committee, Brooks' law / mythical man-month, analysis
  paralysis, NIH syndrome, escalation of commitment, silver bullet, ambiguous viewpoint,
  programming by permutation, organisational silos/stovepipe, moral hazard, cash cow. Two of these
  now have technical siblings inside the lane and are cross-referenced to them rather than
  duplicating: NIH → §2.14.30–2.14.31, escalation of commitment → §2.11.25 and §2.14.60.
- Still dropped from the same completeness probe, as project-management folklore with no design
  mechanism to state: *the corncob*, *blowhard jamboree*, *viewgraph engineering*, *death by
  planning*, *fear of success*, *fire drill*, *the feud*, *smoke and mirrors*, *throw it over the
  wall*, *irrational management*, *intellectual violence*, *e-mail is dangerous*, *tester-driven
  development*. If guide 26 wants any of them it should source them itself; they would be
  name-only leaves here.
- *Stovepipe **system*** (the technical one, point-to-point integration with N² bespoke contracts)
  is §2.14.54; *stovepipe **organisation*** (Conway's law producing that architecture) is
  §2.14.75. Deliberately two leaves, because the mechanism differs.
- *DLL hell* — not a JVM concern; the JVM analogue (*JAR hell*) is folded into §2.14.53.
- *Race hazard* and *busy spin* belong mechanically to guide 05. Busy spin is kept as §2.14.51 with
  `[X-REF 05]` because it is a design-level choice; *race hazard* is dropped as pure 05 territory.
- The **fitness-function / ArchUnit enforcement** treatment that §2.10.17 and §2.13.15 point at is
  lane D's §2.29. I state the rule text in one leaf each and do not develop it.
- **Fowler's smell catalogue** overlaps §2.14 at four points (feature envy, shotgun surgery, middle
  man, primitive obsession). I kept the four leaves because the brief's inventory assigns them to
  §2.14, and wrote them as *failure mechanisms*; lane D's §2.15 should treat the same four as
  *smells with a smallest-safe-move*, which is a different cut of the same concept. **Flagging the
  overlap so the orchestrator does not de-duplicate them into one.**
