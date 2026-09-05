# Syllabus — 24 Design Patterns & Application Architecture

**Target version baseline (checked 2026-09-05).** Every version-dependent leaf carries
`[VERSION-TRAP]` or `[RESEARCH]`. Where a claim is true of Spring Boot but not of plain Spring
Framework, both are stated.

| Layer | Normative source this file targets |
|---|---|
| Language level | **Java 21 LTS** as the baseline; JDK 22–25 deltas called out explicitly (notably JEP 444 virtual threads in 21, JEP 491 `synchronized`-without-pinning in JDK 24) |
| Framework | **Spring Framework 6.2 / Spring Boot 3.5.x** — including Boot's CGLIB-by-default proxy decision (`spring.aop.proxy-target-class`, `matchIfMissing = true`) |
| Persistence | **Hibernate ORM 6.6** — lazy proxies, `@Version`, generated SQL |
| Resilience | **Resilience4j 2.x** — `CircuitBreaker`, `Retry`, `Bulkhead`, `TimeLimiter` state machines |
| Architecture tests | **ArchUnit 1.3+** — rule DSL, `ArchTest`, freezing store |
| Pattern catalogue | Gamma, Helm, Johnson, Vlissides, *Design Patterns: Elements of Reusable Object-Oriented Software*, Addison-Wesley, **1994** (23 patterns) |
| Pattern pre-history | Alexander, *A Pattern Language* (**1977**) and *The Timeless Way of Building* (**1979**) |
| Enterprise catalogue | Fowler, *Patterns of Enterprise Application Architecture*, **2002** |
| Refactoring | Fowler, *Refactoring* **2nd edition, 2018** (JavaScript examples; the smell and move names are the normative ones) |
| DDD | Evans, *Domain-Driven Design*, **2003**; Vernon, *Implementing Domain-Driven Design*, **2013** |
| Clean architecture | Martin, *Clean Architecture*, **2017** |
| Ports and adapters | Cockburn, *Hexagonal Architecture* (ports & adapters), original article **2005** |
| Production failure | Nygard, *Release It!* **2nd edition, 2018** |
| Architecture practice | Richards & Ford, *Fundamentals of Software Architecture* **2nd edition, 2025**; Ford, Richards, Sadalage & Dehghani, *Software Architecture: The Hard Parts*, **2021** |

## The deltas that most often produce a stale design-patterns answer

A 2026 candidate who repeats any of the following without qualification is dated. Each item states
what is true in the baseline above and what changed.

1. **"Records replaced the builder."** Partly true, mostly false. Records replaced the hand-written
   immutable carrier and its `equals`/`hashCode`/`toString`; they did **not** replace staged
   construction, because the canonical constructor is positional and all-args, so a 9-component
   record has exactly the telescoping problem a builder exists to solve. What records did retire is
   the builder-as-value-object-implementation — the builder is now assembly ergonomics over a record
   product. `[VERSION-TRAP]`
2. **"Visitor is how you add operations to a type hierarchy."** Sealed interfaces plus exhaustive
   `switch` pattern matching (final in Java 21) give the compiler-checked exhaustiveness that
   visitor manufactures with double dispatch, without `accept`/`visit`. Visitor is now what you
   write when the hierarchy is *not* sealed or *not* yours. `[VERSION-TRAP]`
3. **"You need a factory to decide which implementation to use."** Constructor injection plus
   `@Configuration` / `@Bean` / `@Profile` / `@ConditionalOnProperty` covers per-deployment
   selection, and `List<T>`/`Map<String,T>` injection covers per-request selection. The hand-rolled
   factory survives only for choices made from data (a rail code, a vendor column). The **service
   locator** — a static registry callers pull from — is an anti-pattern here, not an alternative: it
   hides dependencies from the constructor signature and defers failure from startup to request
   time. `[VERSION-TRAP]`
4. **"Pool your threads."** JEP 444 (Java 21) makes a thread cheap enough that a virtual-thread
   executor is a *concurrency limiter*, not a resource pool. JDK 24's JEP 491 removes pinning when a
   virtual thread blocks in `synchronized`, which eliminated the main remaining reason to keep a
   platform-thread pool in front of `synchronized`-heavy library code. Native and foreign-function
   frames still pin. `[VERSION-TRAP]`
5. **"Avoid allocation; pool objects."** C2's escape analysis scalar-replaces non-escaping
   allocations outright — the object is never created, so there is nothing to pool. TLAB allocation
   is a pointer bump; a copying young collection charges for survivors, not garbage. Object pooling
   of plain heap objects is a pessimization. `[VERSION-TRAP]`
6. **"Pooling reduces GC pressure."** With region-based concurrent collectors (G1, ZGC) the cost the
   collector pays scales with the **live set** it must mark and relocate. Long-lived pooled objects
   are permanently live, so pooling *moves work into* the concurrent phases it was supposed to
   avoid. `[VERSION-TRAP]`
7. **"Prototype means implement `Cloneable`."** `Cloneable` is still broken in Java 25 — no `clone`
   method on the interface, construction without a constructor, shallow by default, incompatible
   with `final` fields referencing mutables — and still taught as the Java prototype pattern.
   Nothing in Java 8–25 fixed it. `[VERSION-TRAP]`
8. **"Spring needs an interface to proxy your bean."** Spring Boot's
   `AopAutoConfiguration.CglibAutoProxyConfiguration` is conditional on
   `spring.aop.proxy-target-class` with `matchIfMissing = true` and enables
   `@EnableAspectJAutoProxy(proxyTargetClass = true)`, so **CGLIB subclass proxying is the Boot
   default since 2.0**. Plain Spring Framework still prefers a JDK dynamic proxy when the target
   implements an interface. Both statements are needed; only one is usually given. `[VERSION-TRAP]`
9. **"Use an application event for in-process decoupling."** A raw `ApplicationEventPublisher`
   listener runs synchronously on the publisher's thread inside the publisher's transaction, so a
   listener failure rolls back the publisher. `@TransactionalEventListener(phase = AFTER_COMMIT)` is
   the correct in-process shape; the transactional outbox is the correct cross-process one.
   `[VERSION-TRAP]`
10. **"Start with microservices."** The default reversed: modular-monolith-first with compiler- and
    ArchUnit-enforced boundaries, extracting along seams that have proven stable. The reason to
    split is independent deployability and independent scaling, never "cleaner code". `[VERSION-TRAP]`
11. **"Singleton means `getInstance()`."** The lifecycle is ubiquitous and fine; the static global
    access point is the anti-pattern. A container-managed singleton-scoped bean gives the same one
    instance, injected, substitutable, and visible in the constructor signature. `[VERSION-TRAP]`
12. **"The `Integer` cache is −128..127, full stop."** The lower bound is fixed; the **upper** bound
    is tunable with `-XX:AutoBoxCacheMax` (system property
    `java.lang.Integer.IntegerCache.high`, clamped to at least 127), so `==` identity for boxed
    values is configuration-dependent above 127 — which is the real reason never to depend on it.
    `[VERSION-TRAP]`

## Scope boundary against the sibling guides

This guide owns **intra-service design**: patterns, principles, anti-patterns, smells, refactoring,
and the architecture of one deployable unit. Where a mechanism belongs to a sibling, this guide
states the mechanism in one paragraph and then points — a bible does not send the reader away
empty-handed, so the concept still gets a leaf here, tagged.

Java memory model, `volatile`, safe publication and executors are `[X-REF 05]`: this guide owns
double-checked locking and the initialization-on-demand holder **as pattern idioms** and states the
JMM rule they depend on. JIT behaviour, inline caches, escape analysis and class loading are
`[X-REF 06]`: this guide owns the *cost of indirection* and cites the mechanism. The Spring
container, bean lifecycle and AOP proxy model are `[X-REF 07]`: this guide owns the pattern reading
of them. JPA/Hibernate mechanics are `[X-REF 08]`: this guide owns repository, aggregate and
`@Version` **as design**. REST and API contracts are `[X-REF 12]`; security is `[X-REF 13]`;
messaging, outbox and saga *transport* are `[X-REF 14]`; caching is `[X-REF 15]`; tests and test
doubles are `[X-REF 16]`; observability is `[X-REF 20]`; JMH harness mechanics are `[X-REF 25]`.

The split against guide 22 is the one worth stating explicitly: **24 stops at the service boundary;
22 starts there.** CAP and PACELC, partitioning and consistent hashing, cross-service topology,
quorum arithmetic, multi-region and capacity estimation are `[X-REF 22]`. Aggregate boundaries,
CQRS as a code structure, the outbox as a *design* obligation, and the monolith-versus-microservices
arithmetic that decides whether a boundary should exist at all are owned here.

## The example domain

Every example, service name, entity, status code, heap size, instance count, rate and budget comes
from the QuizStakes domain in `src/scenario/scenario.md` — read-only. The surfaces this topic keeps
returning to:

`ClientRestrictions` — 4 GB heap, 8 instances, extreme request rate, trivial objects, synchronous on
every money path inside a **30 ms p99** budget. The strategy / rule-engine and megamorphic-dispatch
example.

`FundsLedger` — 12 GB heap, 3 instances, partition-affine by client id, **230 writes/sec sustained,
13,600/sec peak**, **19.8M ledger entries/day at ~180 bytes/row**. The aggregate-boundary,
optimistic-locking, event-sourcing and outbox example.

`DocumentVerification` — 8 GB heap, 6 instances, 2–6 MB document buffers, 24k uploads/day → 68 GB/day.
The state-machine, object-pool and adapter-to-third-party example.

`ApplicationGateway` — 2 GB heap, scaling 12 → 40 instances, terminates client TLS, strips the client
token. The chain-of-responsibility (filter chain), decorator, facade and BFF example.

`BankDeposits` — 6 GB heap, 2 instances, one daily 40k-record statement file (500k at month end) at
06:00, idle 23 hours. The template-method / batch-pipeline and anti-corruption-layer example.

`BankWithdrawal` — 6 GB heap, 2 instances, owns `PaymentRun` (1.8k records, 4 files/day),
operator-gated, drain-before-terminate. The command, saga and idempotency example.

`InternalPlatforms` — 4 GB heap, 3 instances, session-affine, 30–90 minute operator sessions, 40
operators on shift (90 at peak). The mediator, memento and CQRS-read-model example.

Constraining figures used throughout: **2.4M registered clients**, **14k concurrent sessions
(55k peak)**, **95k card deposits/day at 40/sec**, **2.8M stake reservations/day at 1,200/sec with
3,400/sec settlement bursts**, a **30 ms restriction budget**, an **80 ms balance-read budget**, a
**150 ms stake-reservation budget**, a hard **500 ms self-exclusion budget**, and a card-PSP p99 of
**11 s** on authorise.

Never `Dog extends Animal`, never `Shape`/`Circle`/`Square`, never `Foo`, never `myapp`, never
`thread1`. The pattern literature's canonical toy examples are banned: if the concept is "a duck
that quacks", it is `PaymentMethod` with `CardDeposit`/`BankTransfer` instead.

## Tag legend

| Tag | Meaning for the write pass |
|---|---|
| `[PROVE]` | work the argument through; do not state the result and move on |
| `[SOURCE]` | quote real JDK/Spring/Resilience4j/ArchUnit source or spec text (short excerpt) and explain every line |
| `[BUILD]` | ship complete, compiling Java 21 code |
| `[TRAP]` | must carry a `**Trap:**` marker — wrong belief, symptom, fix |
| `[RESEARCH]` | leaf exists because of the research phase; re-verify against the cited source before writing |
| `[VERSION-TRAP]` | widely-repeated claim that is version-stale; state what is true in the baseline and what changed |
| `[X-REF nn]` | one-paragraph mechanism here, full treatment in guide nn |
| `[NUM]` | state the number, default, latency or byte arithmetic explicitly |
| `[API]` | must state the exact Java/Spring type, method signature, annotation or property name |
| `[TABLE]` | must be rendered as a table |
| `[FLOW]` | must be rendered as an ordered step-by-step trace |
| `[DIAG]` | must show a real artefact — a stack trace, a decompiled proxy class, a generated SQL line, an ArchUnit failure report — and read it line by line |
| `[SMELL]` | names a code smell; must give the smell, the smallest safe refactoring move, and the test that protects it |
| `[DECIDE]` | must give the decision procedure AND the explicit "do not use this when…" case |
| `[INCIDENT]` | must be framed as a production failure: symptom, diagnosis path, root cause, fix |
| `[SAY]` | interview phrasing — the sentence a strong candidate actually says out loud |

---

# PART 1 — BASICS

PART 1 owns the vocabulary and the individual patterns, one at a time. It establishes what a pattern
*is* and how to reject one (§1.1–§1.5), then walks the creational and structural families
(§1.6–§1.19) and the behavioural family and non-GoF vocabulary (§1.20–§1.33). Every pattern section
carries the same eight obligations: the force, the named participants, the concrete JDK/Spring/
QuizStakes implementation, the cost, the "do not use this when", the testability consequence, the
version delta, and at least one trap. Comparison, selection and disambiguation between patterns is
PART 2's job, not PART 1's.

## §1.1 Why patterns exist — Alexander, GoF 1994, what a pattern is a solution *to*

1.1.1 Christopher Alexander's origin: *A Pattern Language* (1977) and *The Timeless Way of Building*
      (1979) — a pattern as "a recurring problem in a context, plus the core of a solution to that
      problem", stated so it can be reused by someone who did not derive it. `[SOURCE]`

1.1.2 The 1994 GoF book: Gamma, Helm, Johnson, Vlissides, *Design Patterns: Elements of Reusable
      Object-Oriented Software*, Addison-Wesley — 23 patterns, C++ and Smalltalk examples, a
      catalogue rather than a method. `[SOURCE]`

1.1.3 What patterns replaced: the pre-1994 state in which every design review re-derived the same
      argument from scratch because there was no shared name for a structure. Patterns are a naming
      technology first and a design technology second. `[PROVE]`

1.1.4 The two claimed benefits, and which one survives: **shared vocabulary** (survives — two
      engineers can disagree precisely) and **reuse** (does not — a pattern is not a library, and
      nothing is reused but the argument).

1.1.5 A pattern is a solution to a **force**, never to a requirement. The deliverable of a pattern
      answer is the force; the name is a label for a force already resolved. `[SAY]`

1.1.6 The scoring sentence shape, memorised verbatim: "the varying thing here is X, the thing that
      must stay stable is Y, so I'd introduce Z, and the cost is W." `[SAY]`

1.1.7 The mechanism common to all 23: convert a **variation** into a **substitution point**, placed
      exactly on the axis along which requirements change.

1.1.8 **Trap:** the wrong-axis failure. A pattern applied off-axis leaves indirection with no
      variation flowing through it, which is strictly worse than the inline code it replaced —
      you now pay a file hop and a dispatch for nothing. `[TRAP]`

1.1.9 **Trap:** "pattern matching" as an interview strategy — hearing "many payout providers" and
      answering "Strategy". Named without the force it reads as recall, and the follow-up ("why not
      just a `switch`?") has no answer if the force was never articulated. `[TRAP]`

1.1.10 **Trap:** the unfalsifiable claims. "More flexible" and "more maintainable" cannot be checked.
       Replace with the specific future change that becomes a one-file change, and the specific
       change that becomes harder. `[TRAP]`

1.1.11 Patterns buy flexibility on one axis by **freezing** the others: Strategy makes a new
       algorithm cheap and makes changing the strategy *interface* expensive, because every
       implementation must change. `[PROVE]`

1.1.12 The mirror catalogue: Brown, Malveau, McCormick & Mowbray, *AntiPatterns* (1998) formalised
       the failure side — a named bad solution with a named failure mechanism and a stated refactored
       solution. Full treatment §2.14.

1.1.13 Pattern criticism worth being able to name: Peter Norvig's "Design Patterns in Dynamic
       Languages" argues 16 of the 23 are invisible or trivial in a language with first-class
       functions; the Java counter-argument is that Java only acquired those in 8 and 21, and half
       the catalogue is now exactly that vestigial. `[RESEARCH]`

*(13 leaves)*

## §1.2 The pattern form: name, intent, problem, forces, structure, participants, collaborations, consequences, implementation, known uses, related patterns

1.2.1 The full GoF template, all thirteen fields in order: pattern name and classification, intent,
      also known as, motivation, applicability, structure, participants, collaborations,
      consequences, implementation, sample code, known uses, related patterns. `[TABLE]`

1.2.2 The four-part interview compression and its weights: problem (high), **forces (highest)**,
      structure (low — memorisable, so it proves nothing), consequences (high). `[TABLE]`

1.2.3 **Intent** — one sentence naming what the pattern *achieves*, not how. Test: an intent that
      names a class is not an intent.

1.2.4 **Motivation / problem** — the recurring situation, stated in domain terms. QuizStakes form:
      "a new card PSP or banking partner arrives roughly quarterly, each with its own credentials
      and webhook format."

1.2.5 **Forces** — the competing constraints that make the problem hard: "adding a rail must not
      touch `FundsLedger`, but `CardPayments` and `BankWithdrawal` share no interface today."

1.2.6 **Applicability** — GoF's *use when* list. The field every guide prints and every candidate
      skips, and the only field that contains rejection criteria.

1.2.7 **Structure** — the class/object diagram. Diagrammable and therefore low-signal in an
      interview: it can be memorised without understanding.

1.2.8 **Participants** — the named roles: `Creator`, `ConcreteProduct`, `Subject`, `Handler`,
      `Originator`, `Caretaker`. Naming participants is what lets two engineers argue about a
      design with no whiteboard. `[API]`

1.2.9 **Collaborations** — the runtime message sequence between participants, distinct from
      structure because structure is static and collaboration is temporal. `[FLOW]`

1.2.10 **Consequences** — what you now pay: indirection depth, more types, longer stack traces, and
       errors moved from compile time to startup or request time.

1.2.11 **Implementation** — the language-specific notes. In GoF these are C++ notes about virtual
       destructors and templates, and they are the most stale part of the book. `[VERSION-TRAP]`

1.2.12 **Known uses** — GoF required at least three independent real-world uses before admitting a
       pattern to the catalogue. That is the rule of three at catalogue scale. `[NUM]`

1.2.13 **Related patterns** — the field that turns the catalogue from a list into a graph, and the
       origin of every confusable-pair question (§2.5).

*(13 leaves)*

## §1.3 Pattern vs idiom vs principle vs architectural style vs anti-pattern vs refactoring

1.3.1 **Pattern** — a named solution to a recurring problem in a context, at class/object scale,
      language-neutral by intent.

1.3.2 **Idiom** — a language-specific technique below pattern scale: try-with-resources as the
      RAII equivalent, `List.copyOf` as the defensive-copy move, the enum singleton. Idioms do not
      port between languages; patterns claim to.

1.3.3 The initialization-on-demand holder is an **idiom**, not a pattern: it exploits the JVM's
      class-initialisation lock and has no meaning outside a JVM. §1.10, §3.3.

1.3.4 **Principle** — a directional rule with no structure attached (SRP, DIP, Tell-Don't-Ask). A
      principle tells you where to cut; a pattern is a cut someone already made and named.
      §1.30, §2.6–§2.13.

1.3.5 **Architectural style** — a whole-system structural vocabulary (layered, hexagonal,
      event-driven, space-based). Chosen roughly once per deployable, not per class. §2.17.

1.3.6 `[DECIDE]` **Architectural pattern** vs style: a pattern solves one architectural problem
      *inside* a style (outbox, BFF, sidecar, strangler fig); a style constrains the whole
      dependency graph. If it can coexist with a different style, it is a pattern.

1.3.7 **Anti-pattern** — a recurring solution that looks right and reliably fails, carrying a named
      failure mechanism *and* a stated refactored solution. A merely bad idea with no mechanism is
      not an anti-pattern. §2.14.

1.3.8 **Code smell** — a *symptom* in code, not a diagnosis. Fowler's framing: a smell tells you
      where to look, never what to do. §2.15.

1.3.9 **Refactoring** — a behaviour-preserving structural change with a name, a mechanics list, and
      a test that protects it. Fowler, *Refactoring* 2e (2018). §2.16.

1.3.10 The relation between the four: smell → refactoring → pattern. Patterns are *destinations* of
       refactorings, which is why Kerievsky's *Refactoring to Patterns* (2004) is a book and
       "design in patterns up front" is a warning. `[SAY]`

1.3.11 **Trap:** presenting a **convention** as a pattern. Anything a linter or a build rule can
       enforce (package naming, `final` parameters, constructor-injection-only) carries no design
       decision and scores nothing. `[TRAP]`

1.3.12 **Framework** vs pattern: a framework is a set of patterns with the code already written and
       the control flow inverted (Hollywood principle, §2.11). Spring is the abstract factory,
       singleton registry and proxy machinery you would otherwise hand-roll. `[X-REF 07]`

1.3.13 **Trap:** calling everything a pattern — "the repository pattern" (a pattern, Fowler PoEAA),
       "the DTO pattern" (a pattern, PoEAA), "the service pattern" (a package name). Know which of
       the three each of your words is. `[TRAP]`

1.3.14 Fowler's *Patterns of Enterprise Application Architecture* (2002) as the second catalogue
       this guide draws on, by name: repository, unit of work, identity map, data mapper, active
       record, transaction script, domain model, table module, service layer, DTO, remote facade,
       lazy load, optimistic offline lock, pessimistic offline lock, special case. `[SOURCE]`

*(14 leaves)*

## §1.4 The GoF classification: creational/structural/behavioural × class/object scope, and the full 23-pattern census

1.4.1 Two classification axes: **purpose** (creational / structural / behavioural) × **scope**
      (class / object). Class scope means the variation is expressed with inheritance and fixed at
      compile time; object scope means composition, changeable at runtime. `[TABLE]`

1.4.2 The class-scope patterns, worth memorising precisely because everything else is object scope:
      factory method, adapter (class form), interpreter, template method. `[NUM]`

1.4.3 Creational, all five by name: abstract factory, builder, factory method, prototype,
      singleton. `[NUM]`

1.4.4 Structural, all seven by name: adapter, bridge, composite, decorator, facade, flyweight,
      proxy. `[NUM]`

1.4.5 Behavioural, all eleven by name: chain of responsibility, command, interpreter, iterator,
      mediator, memento, observer, state, strategy, template method, visitor. `[NUM]`

1.4.6 5 + 7 + 11 = 23. State the arithmetic; a candidate who says "about twenty" has not read the
      book, and the census is a two-second credibility check. `[NUM]`

1.4.7 `[DECIDE]` GoF's own two organising questions behind the taxonomy, which are also the two
      questions to ask of any candidate pattern: **what does this vary**, and **is the variation
      bound at compile time or at run time**.

1.4.8 What varies per family, one line each: creational varies *which class is instantiated*;
      structural varies *how objects are composed*; behavioural varies *an algorithm or an
      interaction between objects*. `[TABLE]`

1.4.9 GoF patterns effectively dead in modern Java, each with the thing that killed it: interpreter
      (use an existing rule engine), prototype (`Cloneable` is broken — §1.11), visitor (sealed
      types plus exhaustive switch — §1.26, §3.13). `[VERSION-TRAP]`

1.4.10 GoF patterns absorbed by the platform, so that writing them by hand is now the smell:
       singleton and abstract factory (the container — §1.32), iterator (`Iterable` behind
       `for-each` — §1.27), proxy (`Proxy.newProxyInstance` and Spring AOP — §1.15).

1.4.11 The census promise this guide keeps: every one of the 23 has a named JDK site, a named Spring
       site, and a named QuizStakes site. The full table is §1.33. `[TABLE]`

1.4.12 **Trap:** the patterns interviewers ask for that are **not** in GoF at all — static factory
       method, object pool, null object, specification, repository, DTO, registry, value object,
       dependency injection. Calling any of them "a GoF pattern" is a checkable error.
       §1.6, §1.12, §1.29. `[TRAP]`

1.4.13 **Trap:** the GoF names that are false friends in Java — "prototype" (unrelated to
       JavaScript prototypes), "proxy" (unrelated to an HTTP forward proxy), "facade" (unrelated to
       the facade *layer* of a layered app), "adapter" (unrelated to a Kubernetes adapter
       sidecar). `[TRAP]`

1.4.14 The also-known-as aliases worth recognising in a question: factory method = virtual
       constructor; adapter = wrapper; **decorator = wrapper too** (one alias, two patterns — the
       source of half of §2.3's confusion); command = action / transaction; memento = token;
       strategy = policy; bridge = handle/body. `[TABLE]`

1.4.15 Classification is a memorisation artefact, not a design tool. No interviewer scores "adapter
       is structural"; scoring comes from the force. Know the census, lead with the force. `[SAY]`

*(15 leaves)*

## §1.5 The variation-axis model, the rule of three, and premature abstraction as the default failure

1.5.1 The variation-axis model stated precisely: identify the dimension along which requirements
      change, then place a polymorphic boundary exactly on that dimension and nowhere else.

1.5.2 QuizStakes axes that are real, and axes that are not. Real: payment rail (card / bank),
      identity vendor, restriction type, notification channel, quiz scoring mode. Not real: currency
      (one), jurisdiction model (one), ledger schema (one). Seams on the second list are dead
      weight.

1.5.3 `[DECIDE]` **Rule of three**: one case — write it inline; two — duplicate and wait; three —
      the axis is now observable and only now do you know where the seam goes.

1.5.4 Why a seam at one case is guessing: duplication is *local and deletable*, a wrong abstraction
      is *load-bearing and referenced*. The asymmetry, not taste, is the argument. `[PROVE]`

1.5.5 The arithmetic of a wrong seam: N call sites routed through the abstraction must all change
      when its interface changes, whereas duplication changes only the copies that are actually
      wrong. Cost of a wrong seam scales with adoption; cost of duplication does not. `[NUM]`

1.5.6 **Trap:** premature abstraction as the default failure mode of a pattern-literate engineer.
      The failure is not ignorance of patterns; it is applying them with no variation flowing
      through, and it is the thing "hexagonal + CQRS + event sourcing on a CRUD problem" signals.
      `[TRAP]`

1.5.7 `[SMELL]` Detecting a dead seam: an interface with exactly one implementation, no test double
      using it, and no roadmap for a second. Smallest safe move — inline the implementation, delete
      the interface; the protecting test is the existing behaviour test at the outer boundary.

1.5.8 The three legitimate one-implementation interfaces, and only these: an outbound port at a
      module boundary owned by the domain (§2.10), a seam that exists for a test double (§2.28),
      and a published API you cannot change.

1.5.9 `[SMELL]` The `Impl` suffix: `ScoringServiceImpl` names nothing, which means the interface
      names nothing either — if no second name is available, no second implementation is coming.
      Move: rename to what it actually is, and the naming exercise usually deletes the interface.

1.5.10 `[SMELL]` **Speculative generality** (Fowler 2e) is premature abstraction found after the
       fact: an abstract class with one subclass, an unused parameter, a hook nobody calls, a
       type parameter used once. Move: collapse hierarchy / remove parameter / inline function.

1.5.11 The cost of indirection is measured, not asserted: a monomorphic virtual call is roughly a
       nanosecond and inlines away, a megamorphic site does not; the human cost is one file hop per
       layer. Mechanism §3.1, measurement §3.21, `[X-REF 06]`, `[X-REF 25]`.

1.5.12 The two-question rejection procedure, said out loud: "how many implementations exist today,
       and what event produces the second?" No answer to the second question means no seam.
       `[SAY]`

1.5.13 The upgrade trigger, stated as part of every answer rather than as a concession: "modular
       monolith now; I'd extract `DocumentVerification` when a second identity vendor forces
       independent release, or when its 2–6 MB buffers force a different heap profile from the
       rest." `[SAY]`

1.5.14 Rejecting a pattern out loud scores higher than applying one, because a rejection can only
       be produced force-first — it is unfakeable from a catalogue. `[SAY]`

*(14 leaves)*

## §1.6 Static factory methods

1.6.1 Not a GoF pattern. The reference is Bloch, *Effective Java* Item 1, "consider static factory
      methods instead of constructors" — the most-used creational technique in modern Java and the
      one most often omitted from pattern answers. `[SOURCE]`

1.6.2 Force: construction needs a **name**, a **decision**, a **cached result**, or a **subtype**,
      and a constructor can express none of the four.

1.6.3 Capability 1 — **a name.** Two constructors with the same erased signature are impossible, so
      `Money.ofMinor(1250L)` and `Money.ofMajor(new BigDecimal("12.50"))` cannot both be
      constructors of a one-argument shape; as static factories they coexist and read at the call
      site. `[API]`

1.6.4 Capability 2 — **return a subtype or an interface.** `List.of()` returns an
      `ImmutableCollections` implementation, and `EnumSet.of` returns `RegularEnumSet` up to 64
      constants and `JumboEnumSet` above. The caller names neither. `[API]` `[NUM]`

1.6.5 Capability 3 — **return a cached instance.** `Integer.valueOf`, `Boolean.valueOf`,
      `Optional.empty()`, `List.of()` all return shared instances; a constructor must allocate.
      §1.19. `[API]`

1.6.6 Capability 4 — **fail before allocation, with a domain message.**
      `RestrictionType.of("STAKE_BLOCKD")` rejects an unknown code before anything is half-built,
      naming the field and the value.

1.6.7 Capability 5 — **the returned type need not exist yet.** A static factory on an interface can
      be written before any implementation is chosen; this is the service-provider shape that
      `ServiceLoader` completes (§4.3). `[API]`

1.6.8 The JDK naming conventions, by exact name, because deviating from them costs the reader:
      `of`, `ofNullable`, `valueOf`, `from`, `copyOf`, `instance` / `getInstance`, `create` /
      `newInstance`, `getType`, `newType`. `[API]` `[TABLE]`

1.6.9 **Trap:** confusing `of` with `copyOf`. `List.of(a, b)` takes *elements*; `List.copyOf(c)`
      takes a *collection* and snapshots it. `List.of(someList)` compiles and produces a
      one-element list of lists. `[TRAP]`

1.6.10 Cost 1 — discoverability. A static factory is not reachable by typing `new` and waiting for
       autocompletion; the class must be found in Javadoc first.

1.6.11 Cost 2 — a static call is **not subclassable and not injectable**. It is a hard-coded
       dependency with no seam and no appearance in any constructor signature. §1.10, §2.10.

1.6.12 `[DECIDE]` Do not use a static factory when the caller must be able to substitute
       construction — per-tenant behaviour, a test fake, a per-request choice. That is a factory
       *object*, injected: §1.7, §1.8, §1.20.

1.6.13 Testability consequence: a static factory on a pure value type needs no seam and is free to
       test. A static factory that reaches a clock, a random source, a container or the network is
       untestable — inject `Clock` / `RandomGenerator` instead of hiding them behind `static`.
       `[X-REF 16]`

1.6.14 **Trap:** a static factory that caches **mutable** instances. `Integer.valueOf` is safe only
       because `Integer` is immutable; a cached `StakeReservation` handed to two callers is shared
       mutable state on the 150 ms stake path. `[TRAP]`

*(14 leaves)*

## §1.7 Factory method

1.7.1 Intent: define an interface for creating an object but let **subclasses** decide which class
      to instantiate. The variation point is a subclass of the creator. `[SOURCE]`

1.7.2 Participants by name: `Product`, `ConcreteProduct`, `Creator` (declares the factory method,
      optionally with a default implementation), `ConcreteCreator`. `[API]`

1.7.3 Force: a framework class owns a workflow and must let you swap *what it instantiates* without
      letting you rewrite the workflow. Factory method is template method (§1.21) applied to
      construction, which is why the two always appear together.

1.7.4 `[DECIDE]` Class scope, not object scope: the binding happens at compile time through
      inheritance, so it **cannot** vary per request, per tenant or per row. If the choice comes
      from data, this is the wrong pattern.

1.7.5 JDK sites by exact name: `Collection.iterator()` (every collection is a creator returning its
      own `Iterator`), `ThreadFactory.newThread(Runnable)`,
      `SocketFactory.createSocket(...)`, `DocumentBuilderFactory.newDocumentBuilder()`,
      `Calendar.getInstance()`. `[API]`

1.7.6 Spring sites by exact name: `FactoryBean<T>.getObject()`,
      `AbstractApplicationContext.createBeanFactory()`, `ObjectProvider<T>.getObject()` for
      lazy or per-call resolution, `AbstractRoutingDataSource.determineTargetDataSource()`.
      `[API]`

1.7.7 QuizStakes site: an abstract `DocumentIngestJob` declaring
      `protected abstract IdentityVendorClient newVendorClient();`, with one subclass per vendor
      supplying the client while the upload → extract → verdict → `AA-611`/`AA-650` skeleton stays
      in the base class.

1.7.8 Cost: one class per variation, **plus** inheritance coupling — the subclass now depends on the
      base class's internals and self-call policy, which is the fragile base class problem
      (§2.11).

1.7.9 `[DECIDE]` Do not use factory method when the choice is per request or per row (subclassing
      cannot vary at runtime; use an injected `Map<String, T>`, §1.20), and do not use it when
      only one product type exists and a static factory would do (§1.6).

1.7.10 `[DECIDE]` Do not hand-roll it when the container already decides: a `@Bean` method **is** a
       factory method whose creator is the container, so a parallel hand-written factory duplicates
       it and adds a second place to register a new vendor. §1.32. `[VERSION-TRAP]`

1.7.11 Testability consequence: the seam is a test subclass overriding the factory method, which
       means the unit under test becomes "base class + your test subclass" and the base can no
       longer be tested in isolation. Composition gives a cleaner double. `[X-REF 16]`

1.7.12 **Trap:** calling any method that returns a new object "the factory pattern".
       `static Foo create()` is a static factory (§1.6); GoF factory method is **virtual**, and the
       interviewer's next question is "who overrides it?" `[TRAP]`

*(12 leaves)*

## §1.8 Abstract factory

1.8.1 Intent: provide an interface for creating **families** of related or dependent objects without
      naming their concrete classes. The force is *consistency across products*, not
      substitutability of one. `[SOURCE]`

1.8.2 Participants by name: `AbstractFactory`, `ConcreteFactory`, `AbstractProduct`,
      `ConcreteProduct`, `Client`. `[API]`

1.8.3 The mechanism that earns the pattern: family members are **never obtainable separately**, so a
      mismatched pair is unrepresentable rather than merely discouraged. That is the whole
      difference from two independent factories.

1.8.4 `[BUILD]` QuizStakes shape: `PspIntegrationFactory` with `authorisationClient()`,
      `webhookSignatureVerifier()` and `refundClient()` — the verifier must match the client that
      issued the authorisation, or a callback is validated with the wrong key.

1.8.5 `[INCIDENT]` The failure the family prevents, concretely: pairing PSP-A's
      `authorisationClient` with PSP-B's signature verifier accepts a forged capture callback on the
      money path, crediting `CASH_AVAILABLE` for a deposit that never settled. Symptom is a
      reconciliation break on `PSP_RECEIVABLE`, days later.

1.8.6 JDK sites by exact name: `DocumentBuilderFactory`, `TransformerFactory`,
      `SSLContext` → (`getSocketFactory()`, `createSSLEngine()`), and `Charset` →
      (`newEncoder()`, `newDecoder()`) as a two-member family that must agree. `[API]`

1.8.7 Spring sites: a `@Configuration` class is an abstract factory at container scale — one class
      producing a mutually consistent family of beans, selected by `@Profile` or
      `@ConditionalOnProperty`. `[API]`

1.8.8 Cost, stated as the expression problem again (§1.26): adding a **product** to the family
      changes *every* factory implementation; adding a **family implementation** is cheap. Choose by
      which of the two actually happens. `[PROVE]`

1.8.9 `[DECIDE]` Do not use an abstract factory when the family has one member — that is a factory
      method or a strategy. One-member families are the single commonest over-engineering in the
      creational family.

1.8.10 `[DECIDE]` Do not use it when the selection is per deployment and DI already covers it:
       `@Profile("psp-a")` on a `@Configuration` gives the same consistency guarantee with no
       hand-written interface. The factory earns its place when the choice is made **per request**
       — from a `clientId`, a rail, or a provider column on the row. `[VERSION-TRAP]`

1.8.11 Testability consequence, and it is a positive one: a single stub factory returns a whole
       consistent set of fakes, which beats stubbing three collaborators independently — the family
       invariant holds in tests too, so a test cannot construct the mismatch production cannot.
       `[X-REF 16]`

1.8.12 **Trap:** explaining it as "a factory of factories". That describes the structure and hides
       the intent; the sentence that scores is "a family of products that must be used together."
       `[TRAP]` `[SAY]`

*(12 leaves)*

## §1.9 Builder — staged construction and the validation boundary

1.9.1 Intent (GoF): separate the construction of a complex object from its representation so the
      same process can build different representations. The dominant Java use is narrower — Bloch,
      *Effective Java* Item 2, a fluent builder for a many-parameter immutable value. State both.
      `[SOURCE]`

1.9.2 The telescoping-constructor arithmetic: a constructor with 9 parameters of which 6 are
      optional admits **2^6 = 64** distinct present/absent combinations; the conventional
      telescoping chain writes 7 of them, and the call site is already unreadable at 4.
      `[NUM]` `[PROVE]`

1.9.3 **Trap:** the silent-swap force. Any two same-typed adjacent parameters —
      `StakeReservation(String clientId, String stakeId, ...)` — are transposable with no compile
      error and no immediate runtime error; the defect surfaces as a reservation attributed to the
      wrong client at reconciliation. `[TRAP]`

1.9.4 The JavaBeans alternative and why it loses: setters make the object mutable forever and
      observable half-built, so there is no instant at which "valid" is a property of the type
      rather than a hope about call order. `[PROVE]`

1.9.5 Participants by name: `Builder` as a nested `static final` class, the accumulating mutable
      fields, the chaining setters returning `this`, and `build()`. GoF's `Director` participant is
      almost always absent in Java, and saying so is a small credibility win. `[API]`

1.9.6 **`build()` is the single validation point.** Cross-field invariants — "the bonus leg and the
      cash leg must sum to exactly the stake", "`bonusPortion` must be zero when
      `CLIENT_BONUS_AVAILABLE` is zero" — can only be checked once every field is set.
      `[PROVE]`

1.9.7 **Trap:** validation in the setters. A per-setter check runs before the other fields exist, so
      it *cannot* express a cross-field rule; a builder validated per-setter still produces invalid
      objects, and the invariant then has no single home. `[TRAP]`

1.9.8 `[BUILD]` **The collection-copy requirement.** If `build()` passes the builder's own `List`
      reference into the product, a later `builder.addLeg(...)` mutates the already-built object.
      `build()` must do `List.copyOf(legs)` / `Map.copyOf(...)`, and the compact constructor of the
      product should repeat it.

1.9.9 **Trap:** a builder reused after `build()`, or shared across threads. A builder is an
      unsynchronised mutable accumulator with no reset contract; treat it as single-use and
      thread-confined, and say so rather than assuming. `[TRAP]`

1.9.10 Records as the **product**: `record StakeReservation(...)` with the compact constructor as the
       invariant gate, plus a nested `Builder` for assembly. They compose; they do not compete.
       `[VERSION-TRAP]`

1.9.11 Why records did **not** retire the builder: the canonical constructor is positional and
       all-args, so a 9-component record has precisely the telescoping problem. What records did
       retire is the hand-written immutable carrier and its `equals`/`hashCode`/`toString` —
       builder-for-value-object-plumbing is gone, builder-for-assembly is not. `[VERSION-TRAP]`

1.9.12 `[DECIDE]` The threshold to state as a number: **≥5 fields, or any optional field** → builder.
       2–3 required fields → a record plus static factories; a builder there is ceremony. `[NUM]`

1.9.13 `[DECIDE]` Do not use a builder when the object is mutable anyway (the setters already are the
       builder), when all fields are required and few, or when a `with`-style copy method covers the
       real need (§1.11).

1.9.14 Cost: roughly one extra class and one method per field; a **second place** every new field
       must be added, which is the commonest builder bug (field added to the record, forgotten in
       `build()`); and one extra allocation, usually free by scalar replacement — §3.2. `[PROVE]`

1.9.15 `[DECIDE]` Generated builders and their real cost: Lombok `@Builder` (annotation processor,
       source you cannot read), Immutables, records-with-withers. The trade is less code for worse
       debuggability plus a build-time dependency inside the domain module — which fails the
       "no framework dependency in the domain build file" test of §2.10 if the domain must stay
       clean.

1.9.16 Testability consequence: a builder with sensible defaults **is** the test-data-builder
       pattern. `aStakeReservation().withBonusPortion(Money.ZERO).build()` removes the
       nine-argument noise from every test and makes the one varying field the subject of the test.
       `[X-REF 16]`

*(16 leaves)*

## §1.10 Singleton

1.10.1 Intent: ensure a class has exactly one instance **and provide a global point of access to
       it**. The second clause is what turned it into the catalogue's most-argued entry.
       `[SOURCE]`

1.10.2 Force: exactly one instance, plus controlled and possibly lazy initialisation, plus (in the
       original formulation) reachability from anywhere.

1.10.3 `[BUILD]` Idiom 1 — **eager static final**:
       `final class RateTable { static final RateTable INSTANCE = new RateTable(); }`. Thread-safe
       by the JVM's class-initialisation lock, with no synchronisation written by you.

1.10.4 The mechanism idiom 1 relies on: JVMS §5.5 gives every class an **initialisation lock**;
       `<clinit>` runs exactly once, and any thread reaching an already-initialised class is
       guaranteed to see its writes. Full treatment §3.3. `[SOURCE]`

1.10.5 `[BUILD]` Idiom 2 — **double-checked locking**: `private static volatile RateTable instance`,
       an unsynchronised first null check, a `synchronized (RateTable.class)` block, and a second
       null check inside it.

1.10.6 **Trap:** DCL without `volatile`. `instance = new RateTable()` is three steps — allocate, run
       the constructor, publish the reference — and without `volatile` there is no happens-before
       edge between the constructor's writes and another thread's unsynchronised read, so thread B
       can observe a **non-null reference to a partially constructed object** with `final` fields
       still at their default values. §3.4, `[X-REF 05]`. `[TRAP]` `[PROVE]`

1.10.7 What `volatile` actually buys here, stated as the barrier pair: a release on the write and an
       acquire on the read, which forbids the publication being reordered ahead of the
       constructor's field writes. Not mutual exclusion — ordering. `[PROVE]`

1.10.8 `[BUILD]` Idiom 3 — **initialization-on-demand holder**:
       `private static class Holder { static final RateTable INSTANCE = new RateTable(); }` returned
       from a `static get()`. Lazy because `Holder` is not initialised until first *referenced*;
       lock-free afterwards because the JVM takes the class-init lock once and never again. §3.3.
       `[PROVE]`

1.10.9 The holder idiom is **strictly better** than DCL — same laziness, zero synchronisation on the
       fast path, six lines of subtlety removed. Say this out loud immediately after describing DCL;
       knowing DCL and still preferring the holder is the signal. `[SAY]`

1.10.10 `[BUILD]` Idiom 4 — **enum singleton**: `enum ScoringClock { INSTANCE; }`. Serialization- and
        reflection-proof by JVM special-casing; *Effective Java* Item 3's recommended form.

1.10.11 The serialization attack idioms 1–3 lose to: deserialising a `Serializable` singleton creates
        a **second** instance unless the class declares
        `private Object readResolve() { return INSTANCE; }`. The exact method name, signature and
        `private` visibility all matter. Mechanism §3.5. `[API]`

1.10.12 The reflection attack: `Constructor.setAccessible(true)` then `newInstance()` invokes the
        private constructor. Guards are a flag or counter in the constructor that throws on the
        second call — or an enum, where `Constructor.newInstance` on an enum type throws
        `IllegalArgumentException` by specification. Mechanism §3.5. `[API]`

1.10.13 `[DECIDE]` Do not use `static getInstance()` in application code at all. Use a
        container-managed singleton-scoped bean: one instance per container, injected, therefore
        substitutable in tests and visible in the constructor signature. The idioms above are for
        library code and for the interview.

1.10.14 The distinction "is singleton an anti-pattern?" is actually testing: the **lifecycle** (one
        instance) is fine and ubiquitous; the **global static access point** is the anti-pattern.
        Answer in those two clauses. Full treatment §2.14. `[SAY]`

1.10.15 Why static access is the harm, mechanically and in four parts: it is invisible in the type
        signature (hidden coupling); no test can substitute it; static mutable state leaks between
        tests and makes them order-dependent; and it is shared mutable state across every request
        thread by construction.

1.10.16 **Trap:** a Spring singleton-scoped bean with mutable instance fields. Scope `singleton`
        means one instance shared by every request thread, so an instance field on
        `ClientRestrictions` is shared mutable state at its full request rate inside a 30 ms p99
        budget — a lost-update or torn-read bug that only appears under load.
        `[X-REF 07]`, `[X-REF 05]`. `[TRAP]` `[INCIDENT]`

1.10.17 **Trap:** "one instance" means one per **classloader**, not one per JVM and certainly not one
        per cluster. A cluster-wide singleton is a leader-election problem with a lease and a fencing
        token, not a pattern. `[X-REF 22]`. `[TRAP]`

1.10.18 Testability consequence and the test that protects it: an ArchUnit rule forbidding
        `getInstance`-shaped static accessors in the domain packages (§2.29), plus a test asserting
        two independent container refreshes produce independent instances. `[X-REF 16]`

*(18 leaves)*

## §1.11 Prototype and copy semantics

1.11.1 Intent: create new objects by copying a prototypical instance rather than by calling a
       constructor, when construction is expensive or the configuration you want already exists on
       an instance. `[SOURCE]`

1.11.2 Participants by name: `Prototype` (declares the copy operation), `ConcretePrototype`,
       `Client`. In Java the pattern is expressed through `Cloneable` and `Object.clone()`, and that
       expression is the problem. `[API]`

1.11.3 **`Cloneable` defect 1** — it is a **marker interface that declares no `clone` method**, and
       `Object.clone()` is `protected`, so implementing `Cloneable` does not make an object
       cloneable by any caller. `[SOURCE]` `[PROVE]`

1.11.4 **Defect 2** — `Object.clone()` creates the instance **without invoking any constructor**,
       copying field by field including `private` and `final` fields. Every invariant established in
       a constructor is bypassed. Bloch's word for the mechanism: extralinguistic. `[SOURCE]`

1.11.5 **Defect 3** — the copy is **shallow** by default: nested mutable state (a
       `List<StakeLeg>`, a `Map<String,Integer>`, a 2–6 MB document `byte[]`) is *shared* with the
       original, so mutating the copy mutates the original.

1.11.6 **Defect 4** — the architecture is incompatible with `final` fields referring to mutable
       objects: `clone` cannot reassign a `final` field that `super.clone()` has already set, so a
       correct deep `clone` forces fields to be non-`final`, which weakens the type everywhere
       else. `[PROVE]`

1.11.7 The unenforceable protocol: the class **and every superclass** must obey
       `super.clone()`-then-repair, a contract that is thinly documented, checked by nothing, and
       broken silently. Source walk §3.6. `[SOURCE]`

1.11.8 `Cloneable` remains broken in the Java 21–25 baseline and remains the answer most guides give
       for "the prototype pattern in Java". Nothing between Java 8 and 25 fixed it; it is permanent
       legacy surface. `[VERSION-TRAP]`

1.11.9 Replacement 1 — **copy constructor**: `StakeReservation(StakeReservation other)`. Runs the
       real constructor so invariants re-establish, and the class states copy depth explicitly
       rather than inheriting a default.

1.11.10 Replacement 2 — **copy factory**: `static StakeReservation copyOf(StakeReservation other)`,
        which can additionally return a subtype or an interned instance, and which matches the JDK
        naming convention of §1.6.8. `[API]`

1.11.11 `[BUILD]` Replacement 3 — **`with`-style derivation on a record**:
        `withExpiresAt(Instant)` returning a new record with one component changed. This is the
        actual modern prototype pattern — "one like that, but changed". `[VERSION-TRAP]`

1.11.12 **Trap:** calling a record "immutable" when it holds a `List`, a `Map`, a `Date` or an array.
        Records give **shallow** immutability: the component *reference* is final, the referent is
        not. `[TRAP]`

1.11.13 What actually closes the gap: `List.copyOf` / `Map.copyOf` / `Set.copyOf` in the compact
        constructor for collections, and a defensive `Arrays.copyOf` in the *accessor* for arrays —
        because there is no immutable array view, an array component costs a copy on every read or
        an accessor that returns a length instead. State the choice. `[API]` `[PROVE]`

1.11.14 `[DECIDE]` Do not implement copy semantics at all when the type can simply be immutable —
        the correct number of copies of an immutable object is one. Copy depth is a question you
        only owe for mutable types. §1.29 (value object), §3.14.

1.11.15 Testability consequence and the protecting test: copy, mutate the *original's* nested
        collection, assert the copy is unchanged. A deep-copy defect is invisible to an `equals`
        assertion, so equality tests do not catch it. `[X-REF 16]`

*(15 leaves)*

## §1.12 Object pool

1.12.1 Not a GoF pattern; it appears in the later pooling literature and as *resource pool* in Fowler
       PoEAA's discussion of connection handling. Intent: reuse expensive-to-create instances
       instead of creating and discarding them. `[SOURCE]`

1.12.2 Force restated correctly, because the usual statement is wrong: creation involves a
       **non-heap resource with a real setup cost** — a TCP connection, a TLS handshake, an OS
       thread, an off-heap or direct buffer, an SFTP session.

1.12.3 Mechanism: keep live instances, hand one out on borrow, take it back on release. The pool
       converts a *setup cost* into a *queue wait*, which is a different failure mode, not a smaller
       one.

1.12.4 `[PROVE]` The win condition, written as an inequality: pooling wins only when
       *setup cost ≫ borrow/return coordination cost*. Write the inequality on the whiteboard; it is
       the entire decision. `[NUM]`

1.12.5 `[PROVE]` **Pooling plain heap objects is a pessimization on a modern JVM.** TLAB allocation
       is a pointer bump of a few nanoseconds, and a copying young collection charges for
       *survivors* — dead objects cost nothing to reclaim. `[NUM]`

1.12.6 The three costs a pool adds back: synchronisation or CAS on every borrow and release; pooled
       objects surviving into the old generation so they are **traced on every cycle** instead of
       being dropped; and state leaking between borrowers. `[X-REF 06]`

1.12.7 Escape analysis makes "avoid the allocation" wrong more often than engineers expect: C2
       scalar-replaces non-escaping allocations entirely, so the object is never created and there
       is nothing to pool. Mechanism §3.2, `[X-REF 06]`. `[VERSION-TRAP]`

1.12.8 What defeats scalar replacement, so you know when an allocation is real: the object escapes
       (stored in a field, returned, published to another thread), a **control-flow merge** before
       the field access, an object identity operation, or a non-inlined instance call that the
       analysis cannot see through. §3.2. `[RESEARCH]`

1.12.9 Region-based concurrent collectors sharpen the argument: with G1 and ZGC the work scales with
       the **live set** that must be marked and relocated, and pooled objects are permanently live —
       so pooling moves work *into* the phases it was meant to avoid.
       `[X-REF 06]`, `[X-REF 25]`. `[VERSION-TRAP]`

1.12.10 The virtual-thread delta: JEP 444 (Java 21) makes a thread cheap enough that a
        virtual-thread executor is a **concurrency limiter**, not a resource pool; JDK 24's JEP 491
        removes pinning when a virtual thread blocks in `synchronized`, retiring the main remaining
        reason to front `synchronized`-heavy libraries with a platform-thread pool. Native and
        foreign-function frames still pin. `[X-REF 05]`. `[VERSION-TRAP]` `[RESEARCH]`

1.12.11 The one case where pooling is unambiguously correct: **a pool sized to a downstream
        bottleneck** — database connections for `FundsLedger`, PSP HTTP connections for
        `CardPayments`, SFTP sessions for the `BankWithdrawal` file drop. It is admission control
        wearing a pool's clothes, and its size is the downstream's capacity, not yours.

1.12.12 `[DECIDE]` Never pool DTOs, entities, `StringBuilder`s or `Money` values. Pool connections,
        threads and off-heap buffers — and for `DocumentVerification`'s 2–6 MB buffers at 24k
        uploads/day (68 GB/day) only after measuring, because short-lived buffers may genuinely be
        cheaper as garbage than as a pool with reset and leak risk.

1.12.13 **Trap:** a pool sized larger than the downstream can serve. 200 application connections
        against a database with `max_connections=100` moves the failure from your app to the shared
        database and makes it harder to see. Pool sizing is a **bottleneck** decision, not a
        throughput dial. `[X-REF 10]`, `[X-REF 25]`. `[TRAP]` `[NUM]`

1.12.14 **Trap:** returning a dirty object to the pool. Any pooled object with mutable state needs an
        explicit reset on release, or the next borrower inherits it — the classic cross-request
        leak, e.g. one client's `clientId` surviving in a pooled context object and being used for
        another client's `ClientRestrictions` decision, which is a regulatory incident, not a bug.
        `[X-REF 05]`. `[TRAP]` `[INCIDENT]`

1.12.15 Testability consequence: a pool is untestable through its happy path. The three tests that
        matter are **exhaustion** (borrow beyond capacity — does it block, throw, or grow?),
        **leak** (borrow without release must fail an assertion that the free count returns to
        baseline), and **reset** (borrow, dirty, release, borrow, assert clean). `[X-REF 16]`

*(15 leaves)*

## §1.13 Adapter

1.13.1 Intent: convert the interface of a class into another interface clients expect, so two things
       not designed together can work together. `[SOURCE]`

1.13.2 Participants by name: `Target` (the interface the client already uses), `Adaptee` (the thing
       that does not fit), `Adapter`, `Client`. `[API]`

1.13.3 The defining property, and the first question of §2.3's four-way disambiguation: **the
       adapter's interface differs from the adaptee's** — it converts. Same interface means proxy or
       decorator, not adapter.

1.13.4 Two forms: **object adapter** (composition — holds the adaptee, object scope, can adapt
       subclasses) and **class adapter** (multiple inheritance — in Java only by implementing the
       target *and* extending the adaptee, and impossible when the adaptee is `final`). Adapter is
       the one structural pattern GoF lists in both scopes. `[TABLE]`

1.13.5 Force in QuizStakes: `DocumentVerification` owns an outbound port shaped for our domain
       (`IdentityVendorPort.submit(DocumentBundle) → Verdict`) while the vendor SDK speaks multipart
       upload, polling, and its own status strings. The adapter is the single place where the
       vendor's `INCONCLUSIVE` becomes `AA-650 DOCUMENTS_REFERRED`.

1.13.6 Adapter at module scale **is** the anti-corruption layer (§2.25): the same translation applied
       to a whole bounded context rather than one type. Naming that equivalence out loud is a senior
       signal. `[SAY]`

1.13.7 JDK sites by exact name: `Arrays.asList(T...)` (array → `List`),
       `Collections.enumeration` / `Collections.list` (`Iterator` ↔ `Enumeration`),
       `InputStreamReader` and `OutputStreamWriter` (byte stream ↔ char stream),
       `Channels.newInputStream(ReadableByteChannel)`. `[API]`

1.13.8 Spring sites by exact name: `HandlerAdapter` (adapts a handler object to the dispatcher's
       calling convention), `HandlerMethodArgumentResolver`, `HttpMessageConverter`,
       `TaskExecutorAdapter` over a `java.util.concurrent.Executor`. `[API]`

1.13.9 Cost: one more type, and the **lossy-mapping** problem — a vendor status with no domain
       equivalent must still map to something, and choosing the default is a business decision
       hiding inside a `switch` in an infrastructure class.

1.13.10 `[DECIDE]` Do not write an adapter when you own **both** sides — change one interface
        instead. An adapter between two of your own types is usually an admission that a module
        boundary is in the wrong place, or that two teams disagreed and shipped both.

1.13.11 Testability consequence, which is the practical payoff of hexagonal: the adapter is the only
        class allowed to mention the vendor's types, so it is the only one needing a wire-level test
        (recorded fixtures, a sandbox, WireMock); everything inside the domain tests against the
        port with a plain in-memory fake and no Spring. `[X-REF 16]`, §2.17.

1.13.12 **Trap:** an adapter that leaks the adaptee's exception type. Throwing the SDK's
        `VendorHttpException` out through the port makes every caller depend on the vendor, so the
        adapter has adapted the data and not the failures — which is where the coupling actually
        bites during a vendor swap. `[TRAP]`

*(12 leaves)*

## §1.14 Facade

1.14.1 Intent: provide a unified, **narrower** interface to a set of interfaces in a subsystem,
       making the subsystem easier to use. `[SOURCE]`

1.14.2 Participants by name: `Facade`, the subsystem classes, `Client`. The facade **invents** its
       interface; unlike an adapter it has no existing client interface it must satisfy. `[API]`

1.14.3 The defining properties: the interface is new, simpler and narrower than the sum of what it
       hides, and the facade orchestrates **several** objects — an adapter targets one.

1.14.4 Force in QuizStakes: `PaymentService` in front of `CardPayments`, `BankDeposits`,
       `BankWithdrawal`, `BonusService` and `ClientRestrictions` — one place to reason about "did
       this payment succeed", regardless of rail, so the caller does not learn two state machines.

1.14.5 The detection rule: if the same five-or-six-call sequence appears at three call sites, that
       sequence is the facade's method. Rule of three again (§1.5), applied to call sequences rather
       than to types.

1.14.6 JDK and Spring sites by exact name: `java.net.URL` over sockets, streams and protocol
       handlers; `JdbcTemplate` over `Connection`/`Statement`/`ResultSet`/`SQLException`
       translation; `RestClient` over the HTTP client stack; `ObjectMapper` over the streaming
       parser. `[API]`

1.14.7 Cost: the facade does not *remove* the subsystem, it adds a type on top of it — and a facade
       that forwards one call to one object is pure ceremony with a plausible name.

1.14.8 `[DECIDE]` Do not add a facade when the subsystem already has one entry point, and do not add
       one you cannot name in the domain's language. An unnameable facade — `OrchestrationHelper`,
       `PaymentManager` — is a god object in its first week (§2.14).

1.14.9 `[SMELL]` **Trap:** the facade that grows into a god service. It accretes every new "while
       you're in there" call because it is the convenient place, and the mechanism of decay is that
       it has **no invariant of its own to defend**, so no change can be argued against. Detection:
       dependency count and git file churn; move: push each behaviour onto the subsystem type that
       owns the data. `[TRAP]`

1.14.10 **Trap:** conflating three different "facades" — GoF facade (hides complexity), the *facade
        layer* of a layered app (a naming convention), and Fowler's `RemoteFacade` (a coarse-grained
        interface built to reduce *network* round trips). The third has a different force entirely:
        chattiness, not complexity. `[TRAP]`

1.14.11 Testability consequence: a facade should be thin enough that a delegation test is all it
        needs. If it grows a behaviour suite of its own, the behaviour belongs in the subsystem or on
        a domain type, and the suite is telling you so. `[X-REF 16]`

*(11 leaves)*

## §1.15 Proxy

1.15.1 Intent: provide a surrogate for another object to **control access** to it. The client
       believes it holds the real thing — **transparency** is the defining property. `[SOURCE]`

1.15.2 Participants by name: `Subject` (the shared interface), `RealSubject`, `Proxy`. The proxy's
       interface is **identical** to the target's. `[API]`

1.15.3 GoF's four proxy kinds, all four by name: **virtual** (lazy creation), **remote** (marshalling
       across an address space), **protection** (access control), **smart reference** (reference
       counting, locking, caching). `[TABLE]`

1.15.4 A Java site for each: virtual → Hibernate's lazy entity proxy (`[X-REF 08]`); remote → RMI
       stubs and any generated gRPC or declarative HTTP client; protection → Spring Security's
       method-security interceptor; smart reference → `@Cacheable` and `@Transactional`. `[API]`

1.15.5 A proxy typically **owns the target's lifecycle** — it may create it lazily — whereas a
       decorator is always handed a fully constructed target. This is the cleanest structural
       discriminator of §2.3, and it is a fact about wiring, not about intent.

1.15.6 `[PROVE]` A proxy may legitimately **skip the delegate**: a cache hit, an access denial, a
       lazy no-op. A decorator that skips its delegate is a bug. That asymmetry is the sharpest
       behavioural difference between the two.

1.15.7 **JDK dynamic proxy**, pattern-level mechanics:
       `Proxy.newProxyInstance(ClassLoader, Class<?>[] interfaces, InvocationHandler)` generates a
       class implementing the given *interfaces*, and every call arrives at
       `InvocationHandler.invoke(Object proxy, Method method, Object[] args)`. Internals §3.7.
       `[API]`

1.15.8 **Trap:** the JDK-proxy requirement and its failure shape. The target must implement an
       interface, injection by concrete class fails with a cast error at startup rather than
       degrading, and anything not declared on the proxied interface is simply not intercepted.
       `[TRAP]`

1.15.9 **CGLIB / ByteBuddy subclass proxy** mechanics: a runtime **subclass** of the target with
       methods overridden. Requirements: a non-`final` class and a non-`private` constructor.
       Internals §3.8. `[API]`

1.15.10 `[TABLE]` What subclass proxying **cannot** intercept, exhaustively and from the Spring
        reference: `final` methods, `private` methods, `static` methods, and field access.
        Package-private methods declared in a superclass in a different package are effectively
        private and also un-advisable. `[SOURCE]`

1.15.11 **Trap:** what **neither** mechanism intercepts — **self-invocation**. `this.method()` inside
        the target runs against the raw target, not the proxy, so `@Transactional`, `@Cacheable`,
        `@Async`, `@Retryable` and custom AOP are silently *absent*. It does not error; it does
        nothing. The Spring reference states it plainly: calls the target makes on itself "are going
        to be invoked against the `this` reference, and not the proxy". §3.8, `[X-REF 07]`.
        `[TRAP]` `[INCIDENT]`

1.15.12 `[DECIDE]` The three fixes, ranked, with the framework's own ranking: move the method to
        another bean (correct); inject a self reference or an `ObjectProvider` (smell); use
        `AopContext.currentProxy()` with `exposeProxy = true` (Spring documents this as highly
        discouraged — it couples your code to Spring AOP). AspectJ load-time weaving avoids the
        problem entirely by rewriting bytecode rather than wrapping. `[API]`

1.15.13 **"Spring needs an interface to proxy your bean" is version-stale.** Spring Boot's
        `AopAutoConfiguration.CglibAutoProxyConfiguration` carries
        `@ConditionalOnProperty(prefix = "spring.aop", name = "proxy-target-class",
        havingValue = "true", matchIfMissing = true)` together with
        `@EnableAspectJAutoProxy(proxyTargetClass = true)`, so **CGLIB is the Boot default since
        2.0** and no interface is required. Plain Spring Framework still prefers a JDK proxy when the
        target implements an interface. State both halves. `[VERSION-TRAP]` `[API]` `[SOURCE]`

1.15.14 `[DECIDE]` Do not use a proxy where the caller should *see* the added behaviour — that is a
        decorator (§1.16). Do not hand-roll a proxy for a concern the container already proxies. And
        do not proxy a hot inner call: every proxied invocation costs at minimum one extra dispatch
        plus the handler hop, which is measurable on `ClientRestrictions`' path inside a 30 ms p99
        budget. §3.1, `[X-REF 25]`.

1.15.15 Testability consequence: proxied behaviour is **invisible to a plain unit test** — no
        container, no proxy, no interception — and is therefore untested by construction.
        `@Transactional` boundaries, `@Cacheable` key derivation and self-invocation regressions all
        need an integration slice, and the self-invocation regression test is the one nobody writes.
        `[X-REF 16]`

*(15 leaves)*

## §1.16 Decorator

1.16.1 Intent: attach additional responsibilities to an object dynamically, on the **same
       interface**, as an alternative to subclassing for extension. `[SOURCE]`

1.16.2 Participants by name: `Component` (the interface), `ConcreteComponent`, `Decorator` (holds a
       `Component`), `ConcreteDecorator`. The decorator both **is** and **has** a `Component`, and
       that recursion is exactly what makes stacking work. `[API]`

1.16.3 The three defining properties: the same interface as the target; **chosen by the assembling
       code**, so the intent is visible in the wiring; and designed to stack N-deep.

1.16.4 A decorator **always delegates**. Skipping the delegate is a bug — contrast §1.15.6, where a
       proxy skipping the delegate is doing its job.

1.16.5 `[BUILD]` QuizStakes wiring, and the order is semantic rather than cosmetic:
       `new RetryingPayoutClient(new MeteredPayoutClient(new TimeoutPayoutClient(real)))`. Metrics
       inside retry counts *attempts*; metrics outside retry counts *calls*. Both are defensible;
       only one is what your dashboard claims. `[PROVE]`

1.16.6 The ordering rule to state generally: for each layer ask what it *sees*. Retry inside a
       timeout retries within one shared budget; a timeout inside a retry gives every attempt its
       own budget — against a card PSP with an 11 s p99 that is the difference between one timeout
       and three. Cross-ref §2.26. `[NUM]`

1.16.7 JDK sites by exact name: `java.io` is the canonical stack — `BufferedInputStream`,
       `GZIPInputStream`, `DataInputStream` over any `InputStream`. And
       `Collections.unmodifiableList` / `synchronizedList` / `checkedList` are **decorators, not
       adapters**: same interface, added behaviour. `[API]`

1.16.8 Spring sites by exact name: `HttpServletRequestWrapper` / `HttpServletResponseWrapper`,
       `TransactionAwareCacheDecorator`, `ClientHttpRequestInterceptor` chains,
       `DelegatingFilterProxy`. `[API]`

1.16.9 Cost 1: N decorators mean N frames in every stack trace and N files to read to answer "what
       actually happens on this call". `java.io`'s reputation for unreadability *is* this cost at
       scale, and it is the honest argument against deep stacks.

1.16.10 Cost 2: **identity breaks.** A decorated object is not `==` its target and usually not
        `equals` to it, and `instanceof` on the concrete type fails. Anything relying on identity —
        a `HashSet`, a cache key, an `IdentityHashMap`, a `ThreadLocal` keyed by instance — sees a
        different object than the code that created it.

1.16.11 `[DECIDE]` Do not use a decorator when the behaviour is not optional and never varies (put it
        in the component), when the client must not know it is there (use a proxy), or when the
        interface is wide — Java has no delegation keyword, so a 20-method interface makes every
        decorator a 20-method hand-written forwarding class, and the forgotten forward is the bug.

1.16.12 **Trap:** calling `@Transactional` a decorator. You did not ask for it at the call site, you
        cannot stack two of them meaningfully, and it controls *whether and how* the target is
        invoked — it is a proxy. `[TRAP]`

1.16.13 Testability consequence: the decorator is the most testable structural pattern — construct it
        over a mock delegate and assert delegate call counts and pass-through. The test that protects
        `RetryingPayoutClient` asserts exactly `attempts` invocations against an always-failing
        delegate, and exactly one against a succeeding one. `[X-REF 16]`

*(13 leaves)*

## §1.17 Composite

1.17.1 Intent: compose objects into tree structures and let clients treat individual objects and
       compositions of objects **uniformly**. `[SOURCE]`

1.17.2 Participants by name: `Component` (the shared interface), `Leaf`, `Composite` (holds children
       and itself implements `Component`), `Client`. The recursion lives in the composite, not in any
       client. `[API]`

1.17.3 Force in QuizStakes: a restriction predicate or fee rule that may be one condition or an
       arbitrarily nested AND/OR of conditions, where `ClientRestrictions` must evaluate either
       without branching on which one it holds.

1.17.4 `[BUILD]` Java 21 shape: a `sealed interface FeeRule` with `record Percentage(BigDecimal pct)`
       and `record All(List<FeeRule> parts)` as permitted subtypes — the composite is itself a
       `FeeRule`, and the compiler now enumerates the cases (§3.13).

1.17.5 `[TABLE]` `[DECIDE]` The **transparency-versus-safety** trade-off, and there is no free
       version. The *transparent* form puts child management (`add`, `remove`, `getChild`) on the
       shared `Component` type, so clients stay uniform. The *safe* form puts it only on `Composite`,
       keeping type safety and losing uniformity.

1.17.6 `[PROVE]` Transparency is an **LSP violation baked into the pattern**: `Leaf.add(child)` must
       throw `UnsupportedOperationException`, which is structurally the same defect as
       `List.of(...).add(...)`. Full LSP treatment §2.8. `[TRAP]`

1.17.7 Name the trade-off out loud rather than choosing silently. Composite is one of the few
       patterns where "there is no correct answer, here is the axis and here is which side I take
       and why" *is* the scoring answer. `[SAY]`

1.17.8 JDK and Spring sites by exact name: `java.awt.Container` over `java.awt.Component`, the DOM's
       `org.w3c.dom.Node`, `CompositeCacheManager`, `CompositeHealthContributor`, and
       `Predicate.and` / `Predicate.or` as the functional composite. `[API]`

1.17.9 `[INCIDENT]` Cost 1 — **unbounded recursion**. A composite has no depth limit by construction:
       a cyclic parent/child link is a `StackOverflowError`, and an operator-authored 10,000-node
       rule tree is an unbounded evaluation inside a 30 ms restriction budget. Guard depth and node
       count at construction time, not at evaluation time. `[NUM]`

1.17.10 Cost 2 — **parent pointers**. Adding `parent()` for upward navigation makes the structure
        doubly linked, which makes it mutable, which makes it unshareable and un-cacheable. Every
        "just add a back-reference" request is this trade.

1.17.11 `[DECIDE]` Do not use a composite when the structure is genuinely flat, when leaf and
        container have materially different operations, or when `List<Rule>` plus a `reduce` already
        reads clearly — a two-level "tree" is a list with extra vocabulary.

1.17.12 Testability consequence: three tests carry the pattern — **leaf/composite equivalence** (a
        one-element composite must behave identically to its leaf), **depth-limit rejection**, and
        **empty-composite identity** (what does an empty AND return? an empty fee sum?). The third is
        a business decision that a test must pin down. `[X-REF 16]`

*(12 leaves)*

## §1.18 Bridge

1.18.1 Intent: decouple an abstraction from its implementation so the two can vary **independently**.
       GoF's alias: Handle/Body. `[SOURCE]`

1.18.2 Participants by name: `Abstraction` (holds a reference to an `Implementor`),
       `RefinedAbstraction`, `Implementor`, `ConcreteImplementor`. `[API]`

1.18.3 `[PROVE]` The force is **M×N class explosion**. Notification kind × transport as a single
       inheritance hierarchy gives `EmailActivationNotice`, `SmsActivationNotice`,
       `EmailWithdrawalPaid`, `SmsWithdrawalPaid`, … because inheritance can express only one axis
       at a time.

1.18.4 The arithmetic to state out loud: M kinds × N transports = **M×N** classes as a hierarchy
       versus **M+N** classes composed at runtime. At `NotificationService` with 9 notice kinds and 3
       channels that is 27 against 12, and every new channel costs 9 more classes in the first
       shape and 1 in the second. `[NUM]`

1.18.5 Mechanism: the abstraction hierarchy holds a reference to the implementor hierarchy, the two
       are wired at construction, and each is separately extensible without recompiling the other.

1.18.6 `[DECIDE]` Bridge versus strategy — structurally near-identical, separated by intent and by
       *scale*: a bridge is a deliberate **two-hierarchy split established up front** across a whole
       abstraction; a strategy swaps **one algorithm** inside an otherwise fixed class. §2.3, §2.5.

1.18.7 JDK sites by exact name: JDBC's `java.sql.Driver` / `Connection` as the implementor side
       behind the `DriverManager`-facing abstraction; SLF4J's API-versus-binding split;
       `java.awt.Component` ↔ `ComponentPeer`; `Charset` ↔ `CharsetEncoder`. `[API]`

1.18.8 Spring sites by exact name: `AbstractApplicationContext` as an abstraction over a
       `BeanFactory` implementor; `JdbcTemplate` over a `DataSource`; `CacheManager` over `Cache`;
       `AbstractResource` over the `Resource` protocol implementations. `[API]`

1.18.9 Cost: two hierarchies to hold in your head instead of one, one more indirection on every call,
       and the **unused-axis** risk — if one axis never gains a second member you have paid M+N
       structure to express M behaviour.

1.18.10 `[DECIDE]` Do not introduce a bridge until **both** axes have shown a second member — the rule
        of three applied per axis (§1.5). One axis varying is a strategy; neither varying is just a
        class.

1.18.11 **Trap:** naming "bridge" for anything with an interface between two things. The interviewer's
        test is whether you can name **both** axes and show each varies independently; if you can only
        name one, it is not a bridge and the follow-up will expose that. `[TRAP]` `[SAY]`

*(11 leaves)*

## §1.19 Flyweight

1.19.1 Intent: use sharing to support large numbers of fine-grained objects efficiently, when
       **memory** rather than CPU is the constraint. `[SOURCE]`

1.19.2 Participants by name: `Flyweight` (the shared interface), `ConcreteFlyweight` (holds only
       intrinsic state), `UnsharedConcreteFlyweight`, `FlyweightFactory` (the keyed pool), `Client`
       (holds the extrinsic state). `[API]`

1.19.3 `[PROVE]` The state split, which *is* the pattern: **intrinsic** state is shared, immutable and
       held once in the pool; **extrinsic** state is passed in per call and never stored. Only
       intrinsic state deduplicates, so the pattern's win is bounded by how much of the object is
       intrinsic.

1.19.4 **Trap:** a mutable flyweight. Immutability is a hard precondition, not a style preference — a
       mutable shared instance is shared mutable state across every client that ever looked it up,
       with no lock anywhere. `[TRAP]`

1.19.5 **`Integer.valueOf` cache** — `IntegerCache.low = -128` and `IntegerCache.high = 127` by
       default, both inclusive. Autoboxing is specified to route through `valueOf`, so boxed values
       in that range are shared instances. `[NUM]` `[API]` `[SOURCE]`

1.19.6 `[PROVE]` The `==` consequence: `Integer a = 127, b = 127; a == b` is `true`, and the same with
       `128` is `false`. The JLS *requires* the identity behaviour for −128..127; above that it is
       explicitly unspecified. `[X-REF 03]`. `[TRAP]`

1.19.7 The upper bound is **tunable**: `-XX:AutoBoxCacheMax=<n>`, surfaced as the system property
       `java.lang.Integer.IntegerCache.high` and clamped to at least 127. So `==` identity above 127
       is configuration-dependent, which is the real reason never to depend on it — and the lower
       bound is *not* tunable. `[API]` `[NUM]` `[VERSION-TRAP]`

1.19.8 `new Integer(127)` is never cached, and the boxing constructors have been deprecated for
       removal since Java 9 — which is the deeper reason this trap is slowly dying rather than being
       fixed. `[API]` `[VERSION-TRAP]`

1.19.9 The JDK's other real flyweights, by exact name: `Boolean.valueOf` (`Boolean.TRUE` /
       `Boolean.FALSE`), `Character.valueOf` cache 0..127, `Short.valueOf` / `Long.valueOf` caches
       −128..127, `Byte.valueOf` for all 256 values, and the **String pool** — compile-time constants
       and `String.intern()` are pooled, `new String("x")` is not. `[NUM]` `[API]`

1.19.10 `Long.valueOf` and `Short.valueOf` have **no** `AutoBoxCacheMax` equivalent: only `Integer`'s
        cache upper bound is tunable. Naming that asymmetry is a strong detail and a good check that
        the reader understood the mechanism rather than memorising a range. `[RESEARCH]` `[NUM]`

1.19.11 QuizStakes site: `ClientRestrictions` at extreme request rate with `RestrictionType` and
        `RestrictionSource` as `enum`s rather than `String`s. An enum constant *is* a flyweight
        interned at class initialisation, and it removes both the allocation and the string
        comparison from the 30 ms path — and, per §9.3 of the domain, it is the *pair* of type and
        source that is identity, which an enum pair expresses and two strings do not.

1.19.12 `[PROVE]` Cost: the pattern trades an allocation for a **hash lookup plus a pointer chase**,
        which is worse for cache locality than a freshly TLAB-allocated object adjacent to its
        caller's other data. It wins when the object count is in the millions; below that the lookup
        is a net loss. `[NUM]`

1.19.13 **Trap:** claiming flyweight "makes things faster". It reduces *footprint*. On a modern JVM the
        CPU effect is frequently negative, and the memory win must be netted against the live-set
        cost the collector pays for permanently reachable pool entries (§1.12.9). `[TRAP]`

1.19.14 `[DECIDE]` Do not use a flyweight when the pool would be unbounded or keyed by
        client-supplied data. An interning cache keyed by a 2.4M-cardinality `clientId` is not a
        flyweight pool; it is a memory leak with a factory in front of it.

1.19.15 Testability consequence: assert instance identity for in-range keys **and non-identity outside
        the range**, so that a change to `-XX:AutoBoxCacheMax` or to a pool bound fails a test rather
        than production. The negative assertion is the one that catches the configuration drift.
        `[X-REF 16]`

*(15 leaves)*

---

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
      invariant ("sum across all positions is always zero") is a serialisation requirement, and scenario §7.2
      already puts it on its own pause-sensitive instance. Elasticity is not the constraint;
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
2.22.17 **Trap:** designing aggregates from the UI. The composite operator screen of scenario §7.4 needs eight
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
2.25.12 API composition's three named costs, all visible in scenario §7.3: ordering must be imposed *after* the
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
      deployability — the only unique benefit of decomposition — is gone. scenario §7.2's rule ("no cross-schema
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
2.26.12 The three states named exactly, plus Resilience4j's three additional ones — `DISABLED`,
      `FORCED_OPEN` and `METRICS_ONLY`, **six** `State` constants in total, of which `METRICS_ONLY` is
      the one routinely missed; §3.15.3 quotes all six with each one's `(order, allowPublish)` pair —
      and the shape of the configuration surface: a window (count- or time-based) sized in
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

---

# PART 3 — UNDER THE HOOD

PART 3 owns the mechanism underneath every pattern PART 1 named and every principle PART 2 argued
about. Its unit of work is the source walk: the class, the method, the field, the branch and the
constant that make a pattern real at runtime — JVM dispatch and inline caches, class initialisation,
proxy generation, the JDK's and Spring's own pattern implementations, records and sealed types as
pattern-retiring language features, and the runtime internals of the resilience, event-sourcing and
outbox patterns. It ends with the measurement that decides whether an indirection costs anything and
the incidents where a design decision was the documented root cause.

Where PART 1 says "a strategy is an interface with implementations", PART 3 says which bytecode the
call emits, how wide HotSpot's type profile is before it gives up, and what that costs against
`ClientRestrictions`' 30 ms p99. Nothing here is allowed to say "the JVM optimises it" without naming
the flag.

## §3.1 JVM dispatch: `invokevirtual`/`invokeinterface`, vtable/itable, monomorphic → bimorphic → megamorphic inline caches, and the measured cost of a strategy interface

3.1.1 The five invocation bytecodes and which Java construct emits each: `invokestatic` (static method),
      `invokespecial` (constructor, `private` method, `super.m()`), `invokevirtual` (instance method on
      a class type), `invokeinterface` (instance method on an interface type), `invokedynamic`
      (lambda, record `equals`/`hashCode`/`toString`, `typeSwitch`, string concat). `[API]`

3.1.2 `invokevirtual` resolves to a **vtable index** fixed at class-load time: the receiver's
      `Klass` holds a vtable whose slot for a given method is the same index in every subclass, so
      dispatch is one load of the klass pointer plus one indexed load plus an indirect jump. `[SOURCE]`

3.1.3 `invokeinterface` cannot use a fixed index, because a class implementing two interfaces has no
      single consistent slot numbering — so it searches an **itable**: the receiver's itable is scanned
      for the interface's `Klass`, then the method is fetched at the offset within that interface's
      block. Two levels of indirection plus a linear scan over implemented interfaces. `[SOURCE]`

3.1.4 The itable-scan cost is what makes interface dispatch measurably worse than class dispatch when
      it is *not* inlined; Shipilev's dispatch measurements show C1 interface cases at ~136.2 ns/op
      against ~120.5 ns/op for abstract-class cases at bias=0.5. `[NUM]` `[RESEARCH]`

3.1.5 The **inline cache** sits in front of both: HotSpot patches the call site with the observed
      receiver `Klass` and a direct branch to that klass's method, guarded by a klass compare. State
      machine: **unresolved (clean) → monomorphic → megamorphic (vtable/itable stub)**. `[SOURCE]`

3.1.6 The flag that switches the mechanism off for experiment, quoted from
      `src/hotspot/share/runtime/globals.hpp`: `product(bool, UseInlineCaches, true, "Use Inline Caches
      for virtual calls ")`. `-XX:-UseInlineCaches` degrades every virtual call to a full vtable/itable
      dispatch, which is how you measure what the cache is worth. `[SOURCE]` `[API]` `[NUM]`

3.1.7 The interpreter and C1 record receiver types into `ReceiverTypeData` in the method's
      `MethodData` (the profile), one row per observed type. `[SOURCE]`

3.1.8 `-XX:TypeProfileWidth` — **default 2**, range 0–8 — "number of receiver types to record in
      call/cast profile". It is the number of rows in `ReceiverTypeData`, and therefore the width at
      which the profile stops being useful. The value and range are from the OpenJDK HotSpot wiki's
      TypeProfile page; the declaration is in neither `runtime/globals.hpp` nor `opto/c2_globals.hpp`
      as fetched, so the **declaring file is unconfirmed** — see the notes block. `[NUM]` `[API]` `[RESEARCH]`

3.1.9 The consequence of width 2: C2 supports **monomorphic** and **bimorphic** guarded inlining, and
      **declares any call site with three or more observed receiver types megamorphic**. Three is the
      cliff, not "many". `[NUM]` `[PROVE]`

3.1.10 A **polluted profile** is the specific failure: the profile holds the first ≤ 2 types with low
       counts while the *total* count is high, which is C2's signal that `ReceiverTypeData` overflowed
       and none of the recorded types can be trusted — so it uses none of them. `[TRAP]`

3.1.11 What C2 does with a **monomorphic** strategy interface: Class Hierarchy Analysis (CHA) or the
       type profile proves one receiver, so C2 emits a klass guard and **inlines the implementation
       body**, then constant-folds, scalar-replaces and dead-code-eliminates across the former call
       boundary. The indirection disappears entirely. `[PROVE]`

3.1.12 What C2 does with a **bimorphic** site: two klass guards, both bodies inlined, an uncommon trap
       on the fall-through. Still no dispatch cost, but roughly double the inlined code and pressure
       on the inlining budget. `[NUM]`

3.1.13 What C2 does with a **megamorphic** site: no inlining at all — C2 emits a **vtable or itable
       stub** call. Nothing downstream can be optimised through it, which is the real cost: not the
       jump, the lost inlining. `[PROVE]`

3.1.14 The measured spread, stated honestly: monomorphic ~2.816 ns/op, bimorphic ~3.258 ns/op,
       megamorphic ~4.896 ns/op in the DZone/insightfullogic measurement, with the inlinable
       monomorphic case collapsing far below and the megamorphic case staying ~4.278 ns/op even when
       the target is trivially inlinable. `[NUM]` `[RESEARCH]`

3.1.15 The **uncommon trap and deoptimisation** consequence: a call site that was monomorphic for
       hours and then sees a second type traps, deoptimises, and recompiles — so a rarely-exercised
       rule implementation deployed at 09:00 costs a recompile storm on the first request that uses it.
       `[X-REF 06]` `[X-REF 25]`

3.1.16 `-XX:+PrintInlining` output shapes to recognise: `inline (hot)`, `too big`,
       `not inlineable`, `megamorphic call`, and `type profile` — the last is the direct evidence a
       site went megamorphic. `[DIAG]` `[API]`

3.1.17 The conclusion for `ClientRestrictions`: 8 instances, extreme request rate, a **30 ms p99**
       budget, and a rule-strategy interface. Even a fully megamorphic site at ~5 ns costs ~5 ns —
       0.000017% of the budget. A `List<RestrictionRule>` of 11 rule types evaluated per decision is
       ~55 ns of dispatch against 30,000,000 ns. **Dispatch is not the cost.** `[NUM]` `[PROVE]`

3.1.18 The shape where it *is* the cost, named precisely: a megamorphic call **inside a hot loop over
       19.8M `FundsLedger` entries**, where the lost inlining blocks bounds-check elimination and
       scalar replacement across millions of iterations — not one call, a billion. `[DECIDE]`

*(18 leaves)*

## §3.2 Escape analysis and scalar replacement — why a builder's allocation is often free, and when it is not

3.2.1 Escape analysis is a C2 analysis, not a GC feature. The three escape states, in the OpenJDK
      HotSpot wiki's own words: **GlobalEscape** — "an object escapes the method and thread (stored
      into a static field or stored into a field of an escaped object or returned as the result of the
      current method)"; **ArgEscape** — "an object passed as argument or referenced by argument but not
      globally escape during a call"; **NoEscape** — "a scalar replaceable object". `[SOURCE]`

3.2.2 The flag declarations, quoted from `src/hotspot/share/opto/c2_globals.hpp`:
      `product(bool, DoEscapeAnalysis, true, "Perform escape analysis")`. On by default;
      `-XX:-DoEscapeAnalysis` is the A/B switch for proving a claim in a benchmark. `[SOURCE]` `[API]` `[NUM]`

3.2.3 **Scalar replacement** is the payoff, and it is not "stack allocation" — the wiki says so
      explicitly: "C2 does NOT replace a heap allocation with a stack allocation for non globally
      escaping objects." A NoEscape object is *deleted* and its fields become SSA values in registers.
      There is no object, so there is no allocation, no header, no GC pressure, no write barrier.
      `[TRAP]` `[SOURCE]` `[PROVE]`

3.2.4 `product(bool, EliminateAllocations, true, "Use escape analysis to eliminate allocations")` — the
      scalar-replacement switch, on by default and separately disableable from the analysis itself.
      `[SOURCE]` `[API]` `[NUM]`

3.2.5 `product(intx, EliminateAllocationArraySizeLimit, 64, "Array size (number of elements) limit for
      scalar replacement")` — the hard ceiling nobody quotes: an array of more than **64** elements is
      never scalar-replaced, however provably local it is. `[SOURCE]` `[NUM]`

3.2.6 `[TRAP]` The evidence flag is not available in the JVM you ship:
      `develop(bool, PrintEliminateAllocations, false, "Print out when allocations are eliminated")` and
      `develop(bool, PrintEscapeAnalysis, false, "Print the results of escape analysis")` are
      **`develop`**, not `product` — so they exist only in a fastdebug/slowdebug build and
      `-XX:+PrintEliminateAllocations` on a release JDK is an "Unrecognized VM option" launch failure.
      On a product build the observable proxy is the allocation rate itself (`-XX:+PrintGC`, JFR
      `jdk.ObjectAllocationSample`, or async-profiler `-e alloc`). `[SOURCE]` `[DIAG]`

3.2.7 **Lock elision/coarsening** is the second payoff:
      `product(bool, EliminateLocks, true, "Coarsen locks when possible")`, which is why `StringBuffer`
      inside one method costs what `StringBuilder` costs. `[SOURCE]` `[X-REF 05]`

3.2.8 Failure condition 1 — **the object escapes a non-inlined call**. Escape analysis runs *after*
      inlining and only over what was inlined. Pass the builder to a method C2 declined to inline
      (too big, megamorphic, `@DontInline`) and it becomes ArgEscape at best. `[PROVE]`

3.2.9 Failure condition 2 — **a merge point**. If a reference is assigned in two branches
      (`var b = cond ? new Builder() : cached`), C2's allocation elimination gives up on the phi;
      the historical limitation is that scalar replacement does not survive control-flow merges of
      distinct allocations. `[RESEARCH]`

3.2.10 Failure condition 3 — **`synchronized` on the object, or `Object.hashCode()`/identity use**,
      forces a real header and therefore a real object. Identity is the thing a scalar cannot have.
      `[PROVE]`

3.2.11 Failure condition 4 — the object is **stored into a field or a collection**, or **returned**.
      `StakeReservation.Builder.build()` returning the built record makes the *record* GlobalEscape;
      the *builder* can still be NoEscape, which is exactly the case that matters. `[PROVE]`

3.2.12 Verdict on builder allocation for `StakeReservation`: at **2.8M reservations/day, 1,200/sec**,
       the builder is method-local, never synchronised, never stored — the canonical NoEscape shape,
       so the builder is genuinely free and the argument "a builder allocates, so use a telescoping
       constructor" is measuring nothing. `[PROVE]` `[NUM]`

3.2.13 Verdict on **object pooling** given the same mechanism: pooling *defeats* escape analysis by
       construction — a pooled object is reachable from the pool, therefore GlobalEscape, therefore a
       real allocation that also survives into old generation and gets traced on every cycle. Pooling
       plain heap objects is strictly worse than allocating them. `[DECIDE]` `[X-REF 06]`

3.2.14 The one case pooling still wins in QuizStakes, with the mechanism: `DocumentVerification`'s
       **2–6 MB document buffers** at 24k uploads/day → 68 GB/day. These cross the G1 humongous
       threshold, are not scalar-replaceable at any size, and their cost is region allocation and
       zeroing, not header overhead. Pool the buffer; never pool the DTO. `[NUM]` `[DECIDE]`

*(14 leaves)*

## §3.3 Class initialisation: JVMS §5.5, the init lock, and the initialization-on-demand holder idiom

3.3.1 The five triggers for initialisation (JVMS §5.5): first `new`, first `getstatic`/`putstatic` of a
      non-constant static field, first `invokestatic`, reflective initialisation
      (`Class.forName(name)` with `initialize=true`), and initialisation of a subclass. `[SOURCE]`

3.3.2 **The `static final` constant exemption is the trap**: reading a `static final` field of a
      primitive or `String` type initialised with a compile-time constant expression is resolved by
      `javac` into the constant pool of the *reading* class, so it does **not** trigger initialisation
      of the declaring class. `[TRAP]` `[SOURCE]`

3.3.3 Step 1 of §5.5: "Synchronize on the initialization lock, **LC**, for C." The spec's own note:
      **"The initialization lock is the `Class` object for C."** `[SOURCE]`

3.3.4 Step 2: if the `Class` object indicates initialisation is in progress **by some other thread**,
      release LC and **block until notified**, then go to step 11 — this is the mechanism that makes
      the holder idiom thread-safe with no `synchronized` in the source. `[SOURCE]` `[PROVE]`

3.3.5 Step 3: if initialisation is in progress **by the current thread**, this is a recursive request —
      release LC and **complete normally**. This is why a `<clinit>` cycle does not deadlock and why it
      can observe *partially initialised* state. `[SOURCE]` `[TRAP]`

3.3.6 Step 4: already complete → release LC, complete normally. This is the fast path taken on every
      call after the first, and it is not a lock acquisition in practice — HotSpot checks the klass
      init state inline and the JIT folds it away once the class is initialised. `[PROVE]`

3.3.7 Step 5: state **erroneous** → release LC and throw `NoClassDefFoundError`. The class is
      permanently unusable; a second call does **not** re-run `<clinit>`. `[SOURCE]` `[TRAP]`

3.3.8 Step 6: record "in progress by the current thread", **release LC**. The lock is held only across
      the state transition, not across `<clinit>` execution.

3.3.9 Step 7: recursively initialise the direct superclass SC; abrupt completion marks C erroneous,
      notifies waiters, and propagates the same exception. `[SOURCE]`

3.3.10 Step 8: determine enabled assertions from the defining class loader. Step 9: **execute
       `<clinit>`**. `[SOURCE]`

3.3.11 Step 10: normal completion → acquire LC, label **fully initialized**, notify all threads waiting
       on LC, release LC. The `notifyAll` on LC is what releases the threads parked in step 2.
       `[SOURCE]`

3.3.12 Step 11: `<clinit>` threw E. If E is not an `Error`, wrap it in `ExceptionInInitializerError`
       with E as the cause (or substitute an `OutOfMemoryError` if the wrapper cannot be allocated);
       mark erroneous, notify, rethrow. Step 12: acquire LC, release LC. `[SOURCE]`

3.3.13 The holder idiom, mechanism stated end to end: `Holder` is a distinct class, so its
       initialisation is deferred to the **first `getstatic Holder.INSTANCE`** — laziness from the class
       loader — and the JVM's own §5.5 procedure supplies mutual exclusion, publication and
       happens-before. Zero synchronisation appears in the source because the synchronisation is the
       spec's. `[PROVE]` `[SOURCE]`

3.3.14 Why it beats DCL concretely: the guard the JIT emits after initialisation is *nothing* — the
       klass-init check is constant-folded — whereas DCL keeps a `volatile` read on the fast path
       forever. `[PROVE]` `[X-REF 06]`

*(14 leaves)*

## §3.4 `volatile`, safe publication, final-field semantics, and why DCL needs the barrier

3.4.1 `instance = new RateTable()` is three operations at bytecode level — `new` (allocate,
      header written, fields zeroed), `invokespecial <init>` (constructor writes), `putstatic`
      (publish) — and the JMM permits the third to be observed before the second by another thread.
      `[PROVE]` `[SOURCE]`

3.4.2 The **partially-constructed-object publication hazard** stated exactly: thread B's
      unsynchronised read can see a **non-null reference** whose `final` fields still read as their
      default values (`0`, `null`, `false`). Not a torn object — a fully-typed object with default
      fields. `[TRAP]`

3.4.3 JLS §17.4.4: a `volatile` **write** and a subsequent `volatile` **read of the same variable**
      form a synchronizes-with edge, hence a happens-before edge. That edge is the entire fix. `[SOURCE]`

3.4.4 The release/acquire reading: the `volatile` write is a **release** (all prior writes are visible
      to anyone who acquires), the `volatile` read is an **acquire** (nothing after it may be hoisted
      above it). `[X-REF 05]`

3.4.5 The hardware realisation on x86-64: the `volatile` store compiles to a plain `mov` followed by a
      `lock addl $0,(%rsp)` (a full StoreLoad fence); the `volatile` load is a plain `mov` because x86
      is already TSO. So on x86 the *read* side is free and the *write* side is not. `[NUM]` `[RESEARCH]`

3.4.6 **Why DCL without `volatile` appears to work** — the reason it survives code review and testing:
      on x86-64 with TSO the reordering that breaks it is a *compiler* reordering, not a hardware one,
      and it requires the constructor's stores to be sunk past the publish, which C2 only does under
      specific inlining shapes. It works in every test and fails once, in production, on one
      architecture or after one JIT decision changes. `[TRAP]` `[PROVE]`

3.4.7 The second, subtler failure with a non-`volatile` field: the first check can read `null` on the
      fast path even after another thread published, so the lock is taken again — a correctness-neutral
      but performance-relevant staleness. `[PROVE]`

3.4.8 `[TRAP]` The "DCL is fixed by making the *object's* fields `final`" claim. Final-field freeze
      helps *only* if the reference itself is safely published; a racy read of the reference is outside
      the freeze's guarantee.

3.4.9 JLS **§17.5** final-field semantics: there is a **freeze** action at the end of the constructor,
      and a thread that reads a reference written after the freeze is guaranteed to see the correctly
      initialised `final` fields — **provided** it did not obtain the reference through a race.
      `[SOURCE]`

3.4.10 §17.5's **`this`-escape** exclusion: publishing `this` from inside the constructor (registering
       a listener, starting a thread, passing `this` to a collaborator) voids the freeze guarantee for
       every reader that got the reference that way. `[TRAP]`

3.4.11 The five safe-publication idioms, named: static initialiser (§3.3's holder), `volatile` or
       `AtomicReference` field, `final` field of a properly constructed object, a field guarded by a
       lock held by both writer and reader, and a `java.util.concurrent` collection.
       `[TABLE]` `[X-REF 05]`

3.4.12 `record` and the freeze: a record's components are `final`, so a record published through any of
       the five idioms is safe; a record published through a racy non-`volatile` field is **not**, and
       "records are immutable so they're thread-safe" is the same DCL error one level up. `[TRAP]`

3.4.13 Enum singletons and DCL are the *same* mechanism: `enum` constants are `static final` fields
       initialised in `<clinit>`, so §3.3's init lock does the publication. There is nothing to get
       wrong. `[PROVE]`

3.4.14 The `SELF_EXCLUDED` restriction as the QuizStakes stake: a **hard 500 ms** effectiveness budget
       on a regulatory control means the restriction set must be safely published to the reading thread
       or the system can serve a stake to a self-excluded client. This is the one place in the domain
       where a publication race is a regulatory breach, not a latency blip. `[NUM]` `[SAY]`

3.4.15 `[VERSION-TRAP]` "Java 5 fixed `volatile`, so DCL is now fine" — true and misleading. JSR-133
       made DCL *correct with* `volatile`; it did not make the `volatile` optional, and pre-JSR-133
       advice that DCL is unfixable is equally stale.

3.4.16 `[SAY]` "DCL is correct with `volatile` and broken without it, but I'd still write the holder
       idiom — the JVM's class-init lock gives me the same laziness and publication with no
       synchronisation on the fast path and six fewer lines to get wrong."

*(16 leaves)*

## §3.5 Enum singleton: the serialization mechanism, `readResolve`, and the reflection guard

3.5.1 `Enum` implements `Serializable`, but its serialized form is **special-cased**: an enum constant
      is written as its **name** only, not its fields. `ObjectOutputStream.writeEnum` emits
      `TC_ENUM`, the class descriptor, and the result of `name()`. `[SOURCE]` `[API]`

3.5.2 `ObjectInputStream.readEnum` resolves the constant with `Enum.valueOf(clazz, name)` — it never
      allocates. Deserialisation therefore *cannot* produce a second instance; it returns the
      canonical constant or throws. `[SOURCE]` `[PROVE]`

3.5.3 The consequence that makes enum-as-singleton airtight: `Enum` declares `clone()` to throw
      `CloneNotSupportedException`, and its `writeObject`/`readObject`/`writeReplace`/`readResolve`
      are `private final` no-ops that throw `InvalidObjectException` — the JDK closes every hole
      rather than documenting it. `[SOURCE]` `[RESEARCH]`

3.5.4 Enum fields are **not serialized**, which is the cost nobody states: a mutable field on an enum
      singleton is silently not round-tripped. `[TRAP]`

3.5.5 `[TRAP]` `Enum.valueOf` throwing `IllegalArgumentException` on an unknown name is how a renamed
      constant becomes an unreadable message three years later — the enum's serialized form is its
      *name*, so renaming a constant is a wire-format breaking change. Directly relevant to the
      `AO-`/`AA-` status vocabulary.

3.5.6 For a **non-enum** singleton, `readObject` allocates a fresh instance without running the
      constructor, breaking the invariant. The fix is `private Object readResolve() { return INSTANCE; }`
      — invoked by `ObjectInputStream` after the object graph is read, its return value replacing the
      deserialized instance. `[API]` `[SOURCE]`

3.5.7 `readResolve` mechanics that matter: it must be declared `readResolve` exactly, may be `private`
      (found reflectively), and must return `Object`. A `private readResolve` is **not** inherited by
      subclasses — for an inheritable class it must be at least package-private. `[API]` `[TRAP]`

3.5.8 The second half of the `readResolve` fix, always omitted: every non-`transient` field of a
      `readResolve`-protected singleton must be `transient`, or a **stolen-reference attack** can
      extract the field's value from the discarded instance before `readResolve` replaces it.
      `[TRAP]` `[SOURCE]`

3.5.9 The reflection attack on a non-enum singleton:
      `var c = RateTable.class.getDeclaredConstructor(); c.setAccessible(true); c.newInstance();`
      — the private constructor runs and a second instance exists. The only in-language defence is a
      constructor guard that throws on second invocation. `[BUILD]` `[TRAP]`

3.5.10 The **reflection guard that makes enums immune**, named exactly:
       `Constructor.newInstance` tests `(clazz.getModifiers() & Modifier.ENUM) != 0` and throws
       `IllegalArgumentException("Cannot reflectively create enum objects")`. It is a check in the
       reflection layer, not a language rule. `[SOURCE]` `[API]`

3.5.11 The known bypass, stated so the claim is honest: obtaining the internal `ConstructorAccessor`
       reflectively sidesteps the `Modifier.ENUM` check. "Reflection-proof" means "proof against
       `Constructor.newInstance`", and under JPMS strong encapsulation the bypass now needs
       `--add-opens java.base/java.lang.reflect=ALL-UNNAMED`. `[RESEARCH]` `[VERSION-TRAP]`

3.5.12 Bloch, *Effective Java* item 3: "a single-element enum type is often the best way to implement a
       singleton." The stated limitation: an enum singleton cannot extend a class other than `Enum`.
       `[SOURCE]` `[DECIDE]`

*(12 leaves)*

## §3.6 `Cloneable`/`clone()` source walk, and copy-constructor/copy-factory alternatives

3.6.1 `Object.clone` is declared `protected native Object clone() throws CloneNotSupportedException`
      — `native`, so there is no Java source to read; the VM allocates an object of the same class and
      copies the instance fields bitwise. `[SOURCE]` `[API]`

3.6.2 `Cloneable` is `public interface Cloneable {}` — **empty**. It declares no `clone` method. It is
      a marker whose sole runtime effect is to change `Object.clone`'s behaviour from throwing to
      copying. `[SOURCE]` `[TRAP]`

3.6.3 The interface therefore inverts the normal contract: implementing `Cloneable` modifies the
      behaviour of a `protected` method on the **superclass**, which Bloch calls "extralinguistic".
      `[SOURCE]`

3.6.4 `CloneNotSupportedException` is a **checked** exception thrown by `Object.clone` when the class
      does not implement `Cloneable` — so every `clone()` override must either catch an exception that
      provably cannot happen or redeclare it. Boilerplate with no information content. `[TRAP]`

3.6.5 `clone` **bypasses constructors**: no compact-constructor validation, no `final`-field
      assignment, no invariant establishment. A `StakeReservation` whose constructor guarantees
      `bonusLeg + cashLeg == total` gets no such guarantee from `clone`. `[PROVE]`

3.6.6 `ArrayList.clone` source walk: it calls `super.clone()`, then
      `v.elementData = Arrays.copyOf(elementData, size)` and `v.modCount = 0`. So the *array* is
      copied but the **elements are the same references** — a textbook one-level-deep copy that reads
      as deep because a new array appeared. `[SOURCE]` `[TRAP]`

3.6.7 `HashMap.clone` and `TreeMap.clone` are the same shape: new table/nodes, shared keys and values.
      `Arrays.copyOf` and `System.arraycopy` are shallow by definition. `[SOURCE]`

3.6.8 The shallow/deep taxonomy as three levels, not two: **reference copy** (`b = a`), **shallow copy**
      (new object, shared referents), **deep copy** (new object, recursively new referents) — plus the
      practical fourth, **shallow copy of an immutable graph**, which is deep enough and costs nothing.
      `[TABLE]`

3.6.9 `clone` and `final` fields are incompatible: `clone` cannot assign a `final` field, so a class
      with a `final` mutable field cannot deep-copy it in `clone` at all. This is a hard language-level
      block, not a style preference. `[PROVE]`

3.6.10 Arrays are the one place `clone` is idiomatic and correct: `int[] copy = original.clone()` is
       typed, fast, and has no invariant to break. Bloch: "arrays are the sole compelling use of the
       clone facility." `[SOURCE]` `[DECIDE]`

3.6.11 The Bloch alternative (*Effective Java* item 13): a **copy constructor**
      (`public StakeReservation(StakeReservation other)`) or a **copy factory**
      (`static StakeReservation copyOf(StakeReservation other)`). Advantages named: no `Cloneable`, no
      checked exception, no `final`-field problem, constructors run so invariants hold, and the
      parameter type can be an **interface** — `new ArrayList<>(someCollection)`, `Map.copyOf`,
      `List.copyOf`, `EnumSet.copyOf`. `[SOURCE]` `[API]`

3.6.12 The record idiom that replaces prototype entirely: a `withX` method returning a new record via
       the canonical constructor, plus `Map.copyOf`/`List.copyOf` in the compact constructor to close
       the shallow-immutability gap (see §3.12.13). `[BUILD]`

*(12 leaves)*

## §3.7 JDK dynamic proxy internals: `Proxy.newProxyInstance`, the generated class, caching, `equals`/`hashCode`/`toString`, default methods

3.7.1 `public static Object newProxyInstance(ClassLoader loader, Class<?>[] interfaces,
      InvocationHandler h)` — the whole public surface. It resolves (or generates) the proxy class,
      then invokes its single constructor `$Proxy0(InvocationHandler)`. `[API]` `[SOURCE]`

3.7.2 `public static Class<?> getProxyClass(ClassLoader loader, Class<?>... interfaces)` — **deprecated**
      in current JDKs in favour of `newProxyInstance`, because a proxy class obtained separately can be
      instantiated in ways that bypass the intended access checks. `[API]` `[VERSION-TRAP]`

3.7.3 The **proxy class cache**: "if a proxy class for the same permutation of interfaces has already
      been defined by the class loader, then the existing proxy class will be returned." Keyed by
      (class loader, ordered interface list) — the cache is `Proxy.proxyClassCache`, a
      `WeakCache<ClassLoader, Class<?>[], Class<?>>`. `[SOURCE]` `[API]` `[RESEARCH]`

3.7.4 Class-name reservation: "class names beginning with `$Proxy` are reserved for proxy classes."
      `$Proxy0`, `$Proxy1`, … numbered per definition, not per interface. `[SOURCE]`

3.7.5 Generated class shape: `final class $Proxy0 extends java.lang.reflect.Proxy implements
      <your interfaces>`. Extending `Proxy` consumes the single inheritance slot — **which is the
      mechanism-level reason a JDK proxy can never proxy a class**. `[PROVE]` `[DIAG]`

3.7.6 The generated body: one `private static final java.lang.reflect.Method` field per proxied method,
      initialised in `<clinit>` via `Class.forName(...).getMethod(...)`, so the `Method` lookup is paid
      once at class-init rather than per call. `[SOURCE]` `[DIAG]`

3.7.7 The `m0`–`m3` naming convention: `m0` = `hashCode`, `m1` = `equals`, `m2` = `toString`, then
      interface methods from `m3` upward in declaration order. This is `ProxyGenerator`'s emission
      order, not a specified contract — do not build on it, but recognise it in a decompiled proxy.
      `[RESEARCH]` `[DIAG]`

3.7.8 Each generated method body is the same four lines: load `super.h`, load `this`, load the static
      `Method`, box the arguments into an `Object[]`, `invokeinterface InvocationHandler.invoke`,
      unbox/cast the result. The **boxing of every primitive argument** is the per-call cost. `[NUM]`

3.7.9 `equals`, `hashCode` and `toString` are **routed to the handler** — the javadoc: they are
      "encoded and dispatched to the invocation handler's `invoke` method", with the `Method` object's
      **declaring class being `java.lang.Object`**, and they "logically precede all proxy interfaces".
      `[SOURCE]` `[API]`

3.7.10 `[TRAP]` The consequence: a handler that does not special-case `equals`/`hashCode`/`toString`
       forwards them to the target, so `proxy.equals(proxy)` may be `false` and the proxy is unusable
       as a `HashMap` key. Symptom: a bean vanishing from a `Set`. Fix: handle the three
       `Object` methods before delegating.

3.7.11 The remaining `Object` methods — `getClass`, `notify`, `notifyAll`, `wait`, and `clone`/`finalize`
       — are **not** intercepted: `getClass` is `final`, so `proxy.getClass()` returns `$Proxy0`, never
       the target's class. `[TRAP]`

3.7.12 Method resolution across duplicate interfaces: when two proxied interfaces declare the same
       name and parameter signature, **interface order becomes significant** and the `Method` passed is
       from the **foremost** interface in the list, "regardless of the reference type through which it
       was invoked". `[SOURCE]` `[TRAP]`

3.7.13 **Default methods**: a proxy overrides them like any other interface method, so an
       `InvocationHandler` intercepts them too — the default body does **not** run unless the handler
       invokes it. `[TRAP]` `[API]`

3.7.14 Invoking the default body from a handler is `InvocationHandler.invokeDefault(proxy, method,
       args)` — **added in JDK 16**. Before that it required a `MethodHandles.Lookup`
       `findSpecial`/`unreflectSpecial` dance with `--add-opens`. `[VERSION-TRAP]` `[API]`

3.7.15 `Proxy.isProxyClass(Class<?>)` and `Proxy.getInvocationHandler(Object)` (throws
       `IllegalArgumentException` for a non-proxy) — the only supported introspection. Spring's
       `AopUtils.isJdkDynamicProxy` is a thin wrapper. `[API]`

3.7.16 JDK 9+ module and package placement, as four rules: all interfaces public and in
       exported/open packages → proxy is **public** in an unspecified unconditionally-exported non-open
       package; any non-public interface → proxy is **non-public in that interface's package and
       module** (and all non-public interfaces must share one); any interface in a non-exported package
       → the proxy lands in a non-exported non-open package of a **dynamic module**. The pre-9
       `com.sun.proxy.$Proxy0` name is therefore no longer universal. `[SOURCE]` `[VERSION-TRAP]` `[TABLE]`

*(16 leaves)*

## §3.8 Subclass proxying: CGLIB/ByteBuddy, Spring's proxy-vs-target-class decision, the interceptor chain, and the self-invocation bypass

3.8.1 CGLIB generates a **subclass** of the target at runtime and overrides each non-`final` method.
      Since Spring 3.2 it is **repackaged inside `spring-core`** as
      `org.springframework.cglib.*` — there is no separate `cglib` dependency to add, and the classic
      "add cglib to the pom" advice is stale. `[VERSION-TRAP]` `[API]`

3.8.2 The generated subclass name shape: `Target$$SpringCGLIB$$0` in Spring 6.x (it was
      `Target$$EnhancerBySpringCGLIB$$<hash>` in 5.x) — recognising it in a stack trace or a
      `getClass().getName()` log line is the diagnostic skill. `[DIAG]` `[VERSION-TRAP]`

3.8.3 **Byte Buddy** is the alternative bytecode generator (Mockito's engine, Hibernate's
      bytecode provider); Spring Framework itself uses its own repackaged CGLIB, not Byte Buddy.
      Getting this attribution right matters because "Spring uses Byte Buddy" is a common wrong answer.
      `[TRAP]` `[RESEARCH]`

3.8.4 `DefaultAopProxyFactory.createAopProxy(AdvisedSupport)` is the decision point, and the branch is
      readable in one sentence: if `config.isOptimize() || config.isProxyTargetClass() ||
      hasNoUserSuppliedProxyInterfaces(config)`, then — unless the target class is itself an
      **interface**, a **proxy class**, or a **lambda class** — return `new ObjenesisCglibAopProxy(config)`;
      otherwise return `new JdkDynamicAopProxy(config)`. `[SOURCE]` `[FLOW]` `[API]`

3.8.5 The three escape hatches in that branch, each with its reason: target is an interface → a JDK
      proxy is the only sane choice; target is already a `$Proxy` → subclassing a proxy is pointless;
      target is a **lambda class** (hidden class, JDK 15+) → CGLIB cannot subclass it. `[SOURCE]`

3.8.6 `ObjenesisCglibAopProxy` uses **Objenesis** to instantiate the generated subclass **without
      calling any constructor**, which is why a CGLIB-proxied bean's field initialisers and constructor
      side effects do not run on the proxy instance — and why reading a field through the proxy
      reference returns `null`. `[PROVE]` `[TRAP]`

3.8.7 `[TRAP]` The field-access corollary: `proxy.someField` is `null` even though
      `proxy.getSomeField()` works, because the field lives on the *target*, not the subclass. Every
      "my `@Value` field is null in one place" bug of this shape is this mechanism.

3.8.8 Boot's default, confirmed against `AopAutoConfiguration` at the **v3.5.0** tag: the CGLIB branch
      is `@ConditionalOnBooleanProperty(name = "spring.aop.proxy-target-class", matchIfMissing = true)`
      carrying `@EnableAspectJAutoProxy(proxyTargetClass = true)`, and the JDK-proxy branch is
      `@ConditionalOnBooleanProperty(name = "spring.aop.proxy-target-class", havingValue = false)`.
      The whole class sits behind `@ConditionalOnBooleanProperty(name = "spring.aop.auto",
      matchIfMissing = true)`. So **`spring.aop.proxy-target-class` is effectively `true` when absent**
      and Boot applications get CGLIB proxies unless told otherwise — the opposite of plain Spring
      Framework's historical interface-first default. `[SOURCE]` `[NUM]` `[API]` `[VERSION-TRAP]`

3.8.9 `[VERSION-TRAP]` The condition annotation itself changed: Boot **3.4** introduced
       `@ConditionalOnBooleanProperty`, and `AopAutoConfiguration` uses it at 3.5.x. Older sources
       (and older Boot) show `@ConditionalOnProperty(prefix = "spring.aop", name =
       "proxy-target-class", havingValue = "true", matchIfMissing = true)`. Same effective default,
       different annotation — do not "correct" one to the other. `[API]`

3.8.10 `@EnableAspectJAutoProxy(proxyTargetClass = true)` and
      `@EnableTransactionManagement(proxyTargetClass = true)` as the per-concern overrides. `[API]`

3.8.11 `[TRAP]` The failure the default prevents: with a JDK proxy, injecting the **concrete class**
       (`@Autowired OrderService` where `OrderService` is a class implementing `OrderPort`) fails at
       startup with "bean is expected to be of type X but was actually of type `com.sun.proxy.$Proxy42`"
       — a `BeanNotOfRequiredTypeException`, not a `ClassCastException`. `[DIAG]`

3.8.12 `ReflectiveMethodInvocation implements ProxyMethodInvocation` is the chain driver. Its state:
       `List<?> interceptorsAndDynamicMethodMatchers` and `int currentInterceptorIndex` (initialised to
       `-1`). `[SOURCE]` `[API]`

3.8.13 `ReflectiveMethodInvocation.proceed()` walks it: if
       `currentInterceptorIndex == interceptorsAndDynamicMethodMatchers.size() - 1`, call
       `invokeJoinpoint()` (reflective call on the target); otherwise take
       `++currentInterceptorIndex` and call `interceptor.invoke(this)`. Each `MethodInterceptor` calls
       `invocation.proceed()` to continue. `[SOURCE]` `[FLOW]`

3.8.14 That shape is **chain of responsibility with an index instead of a linked list** — the same
       mechanism as `ApplicationFilterChain`'s `pos` counter (§3.11.2). Naming the shared shape is the
       senior-level observation. `[X-REF 07]`

3.8.15 `MethodInterceptor extends Interceptor extends Advice` (AOP Alliance types
       `org.aopalliance.intercept.*`) — Spring reuses a 2003 standard interface rather than defining
       its own. `[API]`

3.8.16 The worked example: `TransactionInterceptor extends TransactionAspectSupport implements
       MethodInterceptor`. Its `invoke` calls `invokeWithinTransaction(...)`, which resolves the
       `TransactionAttribute`, calls `createTransactionIfNecessary`, invokes `proceed()` inside a
       try/catch, then `completeTransactionAfterThrowing` or `commitTransactionAfterReturning`.
       `@Transactional` is that method, and nothing else. `[SOURCE]` `[FLOW]` `[API]`

3.8.17 Advice ordering is by `Ordered`/`@Order`; the constants that matter:
       `Ordered.LOWEST_PRECEDENCE = Integer.MAX_VALUE` and `Ordered.HIGHEST_PRECEDENCE =
       Integer.MIN_VALUE`. `TransactionInterceptor` sits at `LOWEST_PRECEDENCE` by default, so a
       custom aspect at default order runs **outside** the transaction. `[NUM]` `[API]` `[TRAP]`

3.8.18 What subclass proxying **cannot intercept**, each with the mechanism: `final` methods (cannot be
       overridden), `private` methods (not virtual — the subclass's override is a different method),
       `static` methods (no receiver), constructors (Objenesis skips them), and `final` **classes**
       (cannot be subclassed at all — startup failure, not a silent degradation). `[TABLE]` `[PROVE]`

3.8.19 What **neither** proxy kind sees: **self-invocation**. Interception happens on the call *through
       the proxy reference*; `this.settle(...)` inside the target compiles to `invokevirtual` on the raw
       target, so the interceptor chain is never entered. It does not error — the concern is silently
       absent. `[TRAP]` `[PROVE]`

3.8.20 The full silent-failure list for the QuizStakes services: `@Transactional`, `@Cacheable`,
       `@Async`, `@Retryable`, `@PreAuthorize`, `@Timed`, and every custom `@Around` aspect. A
       `FundsLedger` method that self-calls its own `@Transactional` posting method writes ledger
       entries **outside a transaction**. `[INCIDENT]` `[NUM]`

3.8.21 `AopContext.currentProxy()` returns the proxy from a `ThreadLocal`, and requires
       `@EnableAspectJAutoProxy(exposeProxy = true)`; without it, `IllegalStateException("Cannot find
       current proxy: Set 'exposeProxy' property on Advised to 'true' to make it available")`.
       `[API]` `[DIAG]` `[SMELL]`

3.8.22 Self-injection as the other workaround: `@Autowired @Lazy private LedgerService self;` (the
       `@Lazy` is required to break the constructor cycle) — one field of pure coupling to the proxy
       mechanism, and a smell for the same reason `AopContext` is. The correct move is to extract the
       inner method to a second bean so the call crosses a proxy boundary. `[SMELL]` `[DECIDE]`

3.8.23 **AspectJ weaving as the real fix**: load-time weaving (`-javaagent:aspectjweaver.jar` +
       `@EnableLoadTimeWeaving` + `META-INF/aop.xml`) or compile-time weaving rewrites the target's own
       bytecode, so interception is inside the method and self-invocation, `final` and `private` all
       work. Cost: a build/agent step, harder debugging, and a second AOP model in the project.
       `[DECIDE]` `[X-REF 07]`

*(23 leaves)*

## §3.9 Spring's own pattern implementations, source-walked

3.9.1 `BeanFactory` (interface) / `AbstractBeanFactory` (abstract class) — **abstract factory** at the
      interface and **template method** at the class: `getBean(String)` → `doGetBean(...)` which
      handles alias resolution, the singleton cache, and the parent-factory fallback, then delegates the
      actual instantiation to the abstract `createBean(String, RootBeanDefinition, Object[])`,
      implemented by `AbstractAutowireCapableBeanFactory`. The skeleton is fixed; the creation step is
      the hook. `[SOURCE]` `[API]`

3.9.2 `DefaultSingletonBeanRegistry.getSingleton(String, ObjectFactory<?>)` and its three maps —
      `singletonObjects`, `earlySingletonObjects`, `singletonFactories` — are the **registry** pattern
      plus the circular-dependency escape hatch. `[SOURCE]` `[X-REF 07]`

3.9.3 `FactoryBean<T>` — the **factory method** pattern surfaced *as a bean*: `getObject()`,
      `getObjectType()`, `isSingleton()`. Registering a `FactoryBean` under name `x` makes `getBean("x")`
      return `getObject()` and `getBean("&x")` return the factory itself; `BeanFactory.FACTORY_BEAN_PREFIX
      = "&"`. `[API]` `[SOURCE]` `[NUM]`

3.9.4 `ObjectProvider<T>` (extends `ObjectFactory<T>`) — deferred and optional lookup:
      `getIfAvailable()`, `getIfUnique()`, `stream()`, `orderedStream()`. This is the type that makes
      per-request strategy selection possible without a hand-rolled factory, and it is the answer to
      §1.9's "when does DI make a factory redundant". `[API]` `[DECIDE]`

3.9.5 `BeanPostProcessor` — a **chain of decorators over bean instances**:
      `postProcessBeforeInitialization` and `postProcessAfterInitialization`, the latter being where
      `AbstractAutoProxyCreator` **returns a proxy instead of the bean**. Every proxy in a Spring app
      is created by a `BeanPostProcessor` returning a different object than it was given. `[SOURCE]`
      `[PROVE]`

3.9.6 `BeanFactoryPostProcessor` vs `BeanDefinitionRegistryPostProcessor` — the same chain one phase
      earlier, operating on **definitions** rather than instances;
      `ConfigurationClassPostProcessor` (which processes `@Configuration`) and
      `PropertySourcesPlaceholderConfigurer` are the two that matter. `[API]`

3.9.7 `ApplicationEventMulticaster` (interface) / `SimpleApplicationEventMulticaster` (implementation) —
      **observer**. `addApplicationListener`, `removeApplicationListener`, `multicastEvent`. Full
      internals in §3.19. `[API]`

3.9.8 `AbstractApplicationEventMulticaster`'s `ListenerRetriever` cache, keyed by
      (event type, source type) — the observer pattern with a memoised subscriber lookup, because
      resolving `ApplicationListener<T>`'s generic type per publish would be prohibitive. `[SOURCE]`

3.9.9 `JdbcTemplate` — **template method + callback**: `execute(ConnectionCallback<T>)` owns
      acquire/release/translate-exception, and the varying step is the callback
      (`StatementCallback`, `PreparedStatementCallback`, `RowMapper`, `ResultSetExtractor`). The
      inversion is the point: the template controls the resource lifecycle so the caller cannot leak it.
      `[SOURCE]` `[API]`

3.9.10 `TransactionTemplate.execute(TransactionCallback<T>)` — the same shape for transactions, and the
       **programmatic alternative to `@Transactional`** that is immune to self-invocation (§3.8.19).
       Naming this as the escape hatch is a strong answer. `[API]` `[DECIDE]`

3.9.11 `RestClient` (Spring 6.1+) / `WebClient` / the deprecated `RestTemplate` — template method with
       a fluent builder; `ClientHttpRequestInterceptor` and `ExchangeFilterFunction` are the
       **decorator/chain** seams where retry, tracing and auth headers attach. `[API]` `[VERSION-TRAP]`

3.9.12 `SQLExceptionTranslator` / `SQLErrorCodeSQLExceptionTranslator` — **strategy**, converting a
       vendor `SQLException` into Spring's `DataAccessException` hierarchy. This is also an
       **anti-corruption layer** in DDD vocabulary: one type system translated into another at the
       boundary. `[API]`

3.9.13 `HandlerMapping` (strategy: URL → handler) and `HandlerAdapter` (**adapter**: an arbitrary
       handler object invoked through a uniform interface). `RequestMappingHandlerMapping` +
       `RequestMappingHandlerAdapter` are the `@Controller` pair; `DispatcherServlet.doDispatch` is the
       algorithm that composes them. `[SOURCE]` `[API]`

3.9.14 `HandlerInterceptor` (`preHandle`/`postHandle`/`afterCompletion`) vs `Filter` — the same
       chain-of-responsibility shape at two different layers, which is why "should this be a filter or
       an interceptor" is a boundary question, not a taste question. `[DECIDE]` `[X-REF 13]`

3.9.15 `HandlerMethodArgumentResolver` and `HttpMessageConverter` — **chain of strategies** selected by
       `supportsParameter`/`canRead`; `MappingJackson2HttpMessageConverter` is one link, not the
       mechanism. `[API]`

3.9.16 `Resource` / `ResourceLoader` — **strategy over location syntax**: `ClassPathResource`,
       `FileSystemResource`, `UrlResource`, `ByteArrayResource`, selected by prefix
       (`classpath:`, `file:`, `http:`) in `DefaultResourceLoader.getResource`. `[API]` `[SOURCE]`

3.9.17 `PlatformTransactionManager` — **strategy**: `getTransaction(TransactionDefinition)`, `commit`,
       `rollback`, with `DataSourceTransactionManager`, `JpaTransactionManager` and
       `JtaTransactionManager` as the implementations. `AbstractPlatformTransactionManager` is again
       template method: propagation and synchronisation live in the base, `doBegin`/`doCommit`/
       `doRollback` are the hooks. `[API]` `[SOURCE]`

3.9.18 `Environment` / `PropertySource` / `MutablePropertySources` — **composite + chain of
       responsibility**: `getProperty` walks the ordered `PropertySource` list and returns the first
       hit, which *is* Boot's documented property-precedence order. `[SOURCE]` `[API]`

3.9.19 `ConversionService` / `GenericConversionService` / `Converter<S,T>` /
       `ConverterRegistry` — **registry + strategy** with a `Map<ConvertiblePair, GenericConverter>`
       lookup and a converter cache. `Formatter` and `ConversionService` together replace the
       `PropertyEditor` model. `[API]` `[VERSION-TRAP]`

3.9.20 `@Conditional` / `Condition.matches(ConditionContext, AnnotatedTypeMetadata)` — the
       **specification** pattern, with `@ConditionalOnClass`, `@ConditionalOnMissingBean`,
       `@ConditionalOnProperty` as composable specifications and `AnyNestedCondition`/`AllNestedConditions`
       as the combinators. Boot's entire auto-configuration is specification evaluation at startup.
       `[API]` `[SOURCE]`

*(20 leaves)*

## §3.10 The JDK's own pattern implementations, source-walked

3.10.1 `Collections.unmodifiableList(List<T>)` returns `UnmodifiableList extends UnmodifiableCollection`
       — a **decorator** that forwards every read and throws `UnsupportedOperationException` from every
       mutator. `[SOURCE]` `[API]`

3.10.2 `[TRAP]` It is a **view, not a copy**: the wrapper holds `final Collection<? extends E> c`, so
       mutating the *original* list changes what the "unmodifiable" view reports. `List.copyOf` /
       `List.of` are the actual immutable forms. The distinction between *unmodifiable* and *immutable*
       is exactly this field.

3.10.3 The same decorator, the same LSP hole (§2.8): every mutator on the shared `List` interface is a
       method the decorator cannot honour — the JDK's own canonical LSP violation, shipped
       deliberately. `[PROVE]`

3.10.4 The `java.io` **decorator stack**, source-walked: `FilterInputStream` holds
       `protected volatile InputStream in` and forwards; `BufferedInputStream` adds `byte[] buf` with
       `DEFAULT_BUFFER_SIZE = 8192`; `DataInputStream` adds typed reads; `GZIPInputStream` adds
       inflation. `new DataInputStream(new BufferedInputStream(new FileInputStream(f)))` is three
       decorators and the reason the stack order matters. `[SOURCE]` `[NUM]`

3.10.5 `[TRAP]` The decorator-order bug in the same stack: buffering *outside* the decompressor and
       buffering *inside* it are different performance profiles, and forgetting `close()` on the
       outermost wrapper loses buffered bytes. Try-with-resources on the outermost only is correct
       because `close` cascades.

3.10.6 `Integer.valueOf(int)` — **flyweight**: `if (i >= IntegerCache.low && i <= IntegerCache.high)
       return IntegerCache.cache[i + (-IntegerCache.low)];` with `low = -128` and `high = 127` by
       default. `[SOURCE]` `[NUM]`

3.10.7 `-XX:AutoBoxCacheMax=<n>` (read by `IntegerCache`'s `<clinit>` from the internal property
       `java.lang.Integer.IntegerCache.high`) raises the upper bound only. The lower bound `-128` is
       **not** configurable. `[NUM]` `[API]` `[TRAP]`

3.10.8 `Boolean.valueOf` returns `TRUE`/`FALSE`; `Character.valueOf` caches `0..127`;
       `Byte`/`Short`/`Long` cache `-128..127`; `Float` and `Double` cache **nothing**. So
       `Double.valueOf(1.0) == Double.valueOf(1.0)` is always `false`. `[NUM]` `[TABLE]`

3.10.9 `String` interning: compile-time constant expressions are interned by `javac` into the class
       file's constant pool and resolved to the pool instance; `new String("x")` is a distinct object;
       `String.intern()` is a **native** method backed by the VM's `StringTable` (a hash table sized by
       `-XX:StringTableSize`, moved from PermGen to native memory in JDK 7/8). `[SOURCE]` `[VERSION-TRAP]`

3.10.10 `AbstractList` and `modCount` — the **iterator** pattern plus its fail-fast contract:
        `Itr.checkForComodification()` compares `modCount != expectedModCount` and throws
        `ConcurrentModificationException`. `modCount` is a plain `int`, not `volatile`, which is why
        fail-fast is documented as **best-effort** and is a bug detector, not a thread-safety
        mechanism. `[SOURCE]` `[TRAP]`

3.10.11 `AbstractList.iterator()` returning a private inner `Itr` is the textbook iterator; the
        template-method half is `AbstractList` implementing every `List` method in terms of abstract
        `get(int)`/`size()`. `[SOURCE]`

3.10.12 `Comparator` **combinators**: `comparing`, `thenComparing`, `reversed`, `nullsFirst`,
        `nullsLast`, `comparingInt`. Each returns a new `Comparator` wrapping the previous one — a
        decorator chain built by `default` methods, which is what made `Comparator` extensible without
        breaking implementors (§2.9). `[API]` `[SOURCE]`

3.10.13 `ServiceLoader<S>` — **provider/service-locator** with a **lazy iterator**:
        `ServiceLoader.load(Class<S>)`, `iterator()`, `stream()` (returning
        `Stream<Provider<S>>` so a provider's type can be inspected before instantiation), and
        `reload()`. Providers are discovered from `META-INF/services/<fqn>` files or, since JDK 9,
        `provides ... with ...` in `module-info.java`. `[API]` `[SOURCE]` `[VERSION-TRAP]`

3.10.14 `ServiceLoader`'s `LazyClassPathLookupIterator` instantiates each provider only when
        `next()` is called and **caches instantiated providers**, so a failing provider surfaces as a
        `ServiceConfigurationError` mid-iteration rather than at load time. `[TRAP]` `[SOURCE]`

3.10.15 `Charset.forName` / `CharsetProvider` and `Locale` / `LocaleServiceProvider` — the same
        provider pattern with an SPI; `-Djava.locale.providers=CLDR,COMPAT` and the JDK 9 switch of the
        default locale data from JRE to **CLDR** is the version delta that has broken date formats in
        real migrations. `[VERSION-TRAP]` `[API]`

3.10.16 `Calendar.getInstance()` — **static factory selecting an implementation** by locale
        (`GregorianCalendar`, `JapaneseImperialCalendar`, `BuddhistCalendar`). The reason it is worth
        naming is that it is a factory whose *return type is the abstract class*, so the caller cannot
        tell which it got — and `java.time` replaced the whole thing. `[API]` `[VERSION-TRAP]`

3.10.17 `Executors` — a **static factory** over one product: every method returns a configured
        `ThreadPoolExecutor` (or `ForkJoinPool`, or since JDK 21
        `newVirtualThreadPerTaskExecutor()`). `newFixedThreadPool` passes an **unbounded**
        `LinkedBlockingQueue`, which is the factory hiding the single most dangerous parameter in the
        JDK. `[TRAP]` `[X-REF 05]`

3.10.18 `Stream`'s pipeline is a **decorator/visitor hybrid**: `AbstractPipeline` links stages;
        each stateless intermediate op contributes a `Sink.ChainedReference` whose `accept` calls
        `downstream.accept` (decorator); `Spliterator.tryAdvance`/`forEachRemaining` is the traversal
        (iterator/visitor); the terminal op supplies the `TerminalOp` and `evaluate` runs it. `[SOURCE]`

3.10.19 `Spliterator`'s characteristic bits as the strategy inputs: `ORDERED`, `DISTINCT`, `SORTED`,
        `SIZED`, `NONNULL`, `IMMUTABLE`, `CONCURRENT`, `SUBSIZED` — the flags that let the pipeline
        skip work (e.g. `distinct()` on a `DISTINCT` source). `[API]` `[NUM]`

3.10.20 `EnumSet.noneOf(Class<E>)` — a **factory choosing a representation**: it reads the enum's
        universe and returns `RegularEnumSet` (one `long` bit vector) if `universe.length <= 64`,
        otherwise `JumboEnumSet` (`long[]`). Also `ThreadLocalRandom.current()` as
        thread-specific-storage-as-factory, and `Collections.emptyList()`/`Comparator.naturalOrder()`
        as **null-object/singleton** factories. `[SOURCE]` `[NUM]` `[API]`

*(20 leaves)*

## §3.11 Filter chains: `ApplicationFilterChain` and the Spring Security chain

3.11.1 `org.apache.catalina.core.ApplicationFilterChain` fields, read off the source:
       `private ApplicationFilterConfig[] filters = new ApplicationFilterConfig[0]`,
       `private int pos = 0` (current position), `private int n = 0` (number of filters),
       `private Servlet servlet = null`, `private boolean servletSupportsAsync = false`,
       `private boolean dispatcherWrapsSameObject = false`, and
       `public static final int INCREMENT = 10`. The chain is an **array plus a counter**, not a linked
       list. `[SOURCE]` `[API]`

3.11.2 `public void doFilter(ServletRequest request, ServletResponse response)` is the whole public
       entry point in current Tomcat: `if (pos < n) { var filterConfig = filters[pos++]; var filter =
       filterConfig.getFilter(); filter.doFilter(request, response, this); return; }` — then, after the
       array is exhausted, `servlet.service(request, response)`. `[SOURCE]` `[FLOW]` `[API]`

3.11.3 `[VERSION-TRAP]` **`internalDoFilter` — the frame you will see in stack traces and will not find
       in the source.** Verified per release: `private void internalDoFilter(ServletRequest,
       ServletResponse)` **exists in Tomcat 9.0.x and 10.1.x** and **does not exist in Tomcat 11.0.x or
       `main`**, where `doFilter` holds the loop directly. The cause is traceable: in 9.0.x/10.1.x
       `doFilter` was a thin wrapper that branched on `Globals.IS_SECURITY_ENABLED` and, when set, ran
       `AccessController.doPrivileged((PrivilegedExceptionAction<Void>) () -> { internalDoFilter(req,
       res); return null; })`. Tomcat 11 dropped SecurityManager support, the `doPrivileged` wrapper
       went with it, and the private method had no remaining reason to exist. So a
       `ApplicationFilterChain.internalDoFilter` frame in a stack trace dates the server at ≤ 10.1.x —
       and every blog citing it is describing a version the reader may not be running.
       `[SOURCE]` `[DIAG]`

3.11.4 The mechanism worth stating out loud: **`this` is passed as the `FilterChain`**, so the chain is
       re-entered by the filter calling `chain.doFilter(...)`, and `pos++` has already advanced. The
       recursion is on the stack, which is why a 20-filter chain is 20 nested frames in every stack
       trace. `[PROVE]` `[DIAG]`

3.11.5 `INCREMENT = 10` is the array growth step in `addFilter`: when `n == filters.length`, a new array
       of `n + INCREMENT` is allocated and copied. Linear growth, not doubling — trivia, but it is the
       evidence the structure is a plain array sized for a handful of filters. `[SOURCE]` `[NUM]`

3.11.6 The `static final ThreadLocal<ServletRequest> lastServicedRequest` /
       `lastServicedResponse` pair (exposed by `getLastServicedRequest`/`getLastServicedResponse`) is
       populated only when `ApplicationDispatcher.WRAP_SAME_OBJECT` is enabled — a debugging affordance,
       and a `ThreadLocal` on a pooled request thread, which is the leak shape from §1.12.
       `[SOURCE]` `[TRAP]`

3.11.7 Not calling `chain.doFilter` is the **short-circuit**, and it is the entire mechanism by which an
       auth filter returns 401 without the controller ever existing. Code before the call is request
       processing; code after it is response processing. `[PROVE]`

3.11.8 `[TRAP]` Writing to the response *after* `chain.doFilter` returns fails with
       `IllegalStateException: Cannot call sendError() after the response has been committed` — the
       downstream already committed. Response-side filter logic must run before commit or wrap the
       response.

3.11.9 Spring Security is **one servlet filter**: `DelegatingFilterProxy` (registered with the
       container) → `FilterChainProxy` (the Spring bean) → a `List<SecurityFilterChain>`, each a
       `RequestMatcher` plus its own filter list. `[SOURCE]` `[API]` `[X-REF 13]`

3.11.10 `FilterChainProxy.doFilterInternal` selects the **first** matching `SecurityFilterChain` via
        `getFilters(request)` and builds a `VirtualFilterChain` over it. First match wins — a broader
        matcher declared earlier silently shadows a narrower one declared later. `[SOURCE]` `[TRAP]`

3.11.11 `FilterChainProxy.VirtualFilterChain` is the private inner chain driver: fields
        `List<Filter> additionalFilters`, `int currentPosition`, `FilterChain originalChain`. When
        `currentPosition == size`, it delegates to `originalChain.doFilter` — handing control back to
        Tomcat's `ApplicationFilterChain`. Two nested chain-of-responsibility implementations of the
        same shape, one array-and-counter, one list-and-counter. `[SOURCE]` `[PROVE]`

3.11.12 `OncePerRequestFilter.doFilter` skips when the request already carries the attribute named by
        `getAlreadyFilteredAttributeName()` — by default `getFilterName() + ALREADY_FILTERED_SUFFIX`,
        where the suffix constant's value is `".FILTERED"`. Plus `shouldNotFilter(request)`,
        `shouldNotFilterAsyncDispatch()` (returns `true` by default) and
        `shouldNotFilterErrorDispatch()` (returns `true` by default). `[SOURCE]` `[API]` `[RESEARCH]`

3.11.13 The ordering mechanisms, all three and which wins where: `@Order`/`Ordered` on a `Filter` bean,
        `FilterRegistrationBean.setOrder(int)` in Boot, and `HttpSecurity`'s fixed
        `FilterOrderRegistration` inside a `SecurityFilterChain` (where you insert relative to a known
        filter with `addFilterBefore`/`addFilterAfter`, not by number). `[TABLE]` `[API]`

3.11.14 Why order is a **security property**, stated as the `ApplicationGateway` case: it terminates
        client TLS and **strips the client token** (§6.2), so a logging filter ordered before the
        stripping filter writes client tokens to disk. Order is not configuration; it is the control.
        `[INCIDENT]` `[X-REF 13]`

*(14 leaves)*

## §3.12 Records: what the compiler generates, and the immutability it does and does not give

3.12.1 A `record` is a `final` class extending `java.lang.Record` (abstract, in `java.lang`), and it
       cannot extend anything else. `Record` declares `equals`, `hashCode` and `toString` as
       **abstract**, which is how the compiler is forced to provide them. `[SOURCE]` `[API]`

3.12.2 `javac` generates one `private final` field per component and one **accessor named exactly like
       the component** — `stakeId()`, not `getStakeId()`. The accessor is `public final`. `[SOURCE]`

3.12.3 The **canonical constructor** takes all components positionally in declaration order. It is
       `public` if the record is `public`; you may not weaken its access. `[API]` `[TRAP]`

3.12.4 The **compact constructor** (`public StakeReservation { ... }`, no parameter list) is the
       validation and normalisation hook: the parameters are mutable locals, and `javac` appends
       `this.x = x;` for every component **after** your body. So assigning `weights = Map.copyOf(weights)`
       in the body is what actually stores the copy. `[SOURCE]` `[PROVE]`

3.12.5 `[TRAP]` Writing `this.weights = Map.copyOf(weights)` inside a *compact* constructor is a compile
       error ("cannot assign a value to final variable" / instance field assignment not allowed) — you
       assign the **parameter**, not the field. This is the single most common record mistake.

3.12.6 `equals`, `hashCode` and `toString` are **not** emitted as bytecode bodies: each is a one-line
       `invokedynamic` against `java.lang.runtime.ObjectMethods.bootstrap`. `[SOURCE]` `[API]`

3.12.7 `ObjectMethods.bootstrap(MethodHandles.Lookup lookup, String methodName, TypeDescriptor type,
       Class<?> recordClass, String names, MethodHandle... getters)` — "a bootstrap method to generate
       the `Object.equals`, `Object.hashCode` and `Object.toString` methods, based on a description of
       the component names and accessor methods, for either invokedynamic call sites or dynamic
       constant pool entries". `methodName` must be one of `"equals"`, `"hashCode"`, `"toString"`.
       `[SOURCE]` `[API]`

3.12.8 The consequence of the indy indirection: the *first* call links the method handle chain
       (a one-time cost), and thereafter it is JIT-inlined like handwritten code — so "records are
       slower because of invokedynamic" is a startup-cost claim, not a steady-state one.
       `[TRAP]` `[X-REF 25]`

3.12.9 `equals` semantics: component-wise, using `==` for primitives (with `Float.compare`/
       `Double.compare` for floating point, so `NaN` equals `NaN` and `+0.0 != -0.0`) and
       `Objects.equals` for references. `hashCode` is derived from the components but its exact
       algorithm is **unspecified** and may change between releases — never persist a record's hash.
       `[TRAP]` `[SOURCE]`

3.12.10 You may **override** an accessor or `equals`/`hashCode`/`toString`; `@Override` on an accessor
        is legal and is the recommended marker. Overriding an accessor to return a defensive copy is
        the sanctioned way to close the array-component hole. `[API]` `[DECIDE]`

3.12.11 What you may **not** do: declare an instance field, declare a non-`static` initialiser block,
        make the record non-`final`, extend a class, or declare a native method. `[TABLE]`

3.12.12 The reflection surface: `Class.isRecord()`, `Class.getRecordComponents()` returning
        `RecordComponent[]`, and `RecordComponent.getName()`/`getType()`/`getAccessor()`/
        `getGenericType()`/`getAnnotations()`. This is what Jackson's and Hibernate's record support is
        built on. `[API]`

3.12.13 **Shallow immutability, with the exact gap**: the component *references* are `final`; the
        referents are not. `record Reservation(String id, List<Leg> legs)` — `r.legs().add(...)`
        mutates a "immutable" record. Closed by `List.copyOf(legs)` in the compact constructor.
        `[TRAP]` `[PROVE]`

3.12.14 The **array component** is the gap `copyOf` does not close by itself: an array component is
        copied by `clone()` in the constructor *and* must be copied again in the accessor, because
        otherwise the caller holds the internal array. Also: `equals` on an array component uses
        `Objects.equals`, i.e. **reference identity**, so two records with equal array contents are not
        equal. `[TRAP]` `[PROVE]`

*(14 leaves)*

## §3.13 Sealed types and exhaustive switch: `PermittedSubclasses`, `typeSwitch` bootstrap, `MatchException` — the mechanism that retires visitor

3.13.1 `sealed interface RestrictionOutcome permits Allowed, Blocked, Limited` — `sealed` plus an
       explicit `permits` clause. The `permits` clause may be **omitted** when all permitted subtypes
       are in the same source file, in which case `javac` infers it. `[API]` `[SOURCE]`

3.13.2 Every permitted subclass must be `final`, `sealed`, or explicitly `non-sealed`. There is no
       fourth option — `non-sealed` exists precisely so a hierarchy can be deliberately reopened at one
       point. `[API]` `[TRAP]`

3.13.3 The same-module/same-package rule: a sealed type and its permitted subclasses must be in the
       same **module**, or, if in an unnamed module, the same **package**. This is the JPMS-level
       enforcement (see §3.20). `[SOURCE]` `[X-REF 04]`

3.13.4 The class-file mechanism: `javac` writes a **`PermittedSubclasses`** attribute on the sealed
       class — a list of constant-pool class references. `Class.isSealed()` and
       `Class.getPermittedSubclasses()` read it. The *class file*, not an annotation, carries the
       constraint. `[SOURCE]` `[API]`

3.13.5 The **JVM** enforces it at class load: defining a class that names a sealed class as its
       supertype without appearing in that class's `PermittedSubclasses` fails verification with an
       `IncompatibleClassChangeError`. Sealing is not a compiler convention. `[SOURCE]` `[PROVE]`

3.13.6 Exhaustive `switch` over a sealed hierarchy: `javac` proves exhaustiveness from
       `PermittedSubclasses` and **allows the omission of `default`**. Adding a permitted subtype then
       breaks compilation at every such switch — the "every visitor must handle every type" guarantee,
       enforced by the compiler instead of by an `accept`/`visit` pair. `[PROVE]`

3.13.7 A pattern `switch` on a reference type compiles to `invokedynamic` against
       `java.lang.runtime.SwitchBootstraps.typeSwitch(MethodHandles.Lookup, String, MethodType,
       Object... labels)` — "a bootstrap method for linking an invokedynamic call site that implements
       a switch on a target of a reference type". `[SOURCE]` `[API]`

3.13.8 The `labels` static arguments must be non-null and of type `String`, `Integer`, `Class`, or
       `EnumDesc`. The call site returns the **index** of the first matching label (or the number of
       labels if none matched, or `-1` for a `null` target), and `javac` emits a `tableswitch` on that
       int. So a pattern switch is: one indy call returning an index, then a dense integer switch.
       `[SOURCE]` `[PROVE]` `[NUM]`

3.13.9 `SwitchBootstraps.enumSwitch` is the sibling bootstrap for enum patterns. Both are in
       `java.lang.runtime`, both were preview in 17–20 and final in **21** (JEP 441). `[API]`
       `[VERSION-TRAP]`

3.13.10 The linear-scan cost: the generated matcher tests labels **in order**, so a hot pattern switch
        over 11 restriction types averages ~5.5 `instanceof`-equivalent tests. On `ClientRestrictions`'
        30 ms budget this is noise; in a per-ledger-entry loop it is worth ordering the common case
        first. `[NUM]` `[DECIDE]`

3.13.11 **`MatchException`** (`java.lang.MatchException`, `extends RuntimeException`, `final`) is what
        an exhaustive switch throws at run time when no label applies. Introduced in the pattern-switch
        preview and final in JDK 21. `[API]` `[SOURCE]`

3.13.12 **The release boundary, stated explicitly because this project has had it backwards:**
        `MatchException` is the JDK 21 baseline answer. **JEP 433 (JDK 20, fourth preview)** carried the
        release note: *"An exhaustive switch (i.e., a switch expression or a pattern switch statement)
        over an enum class **now throws `MatchException` rather than `IncompatibleClassChangeError`** if
        no switch label applies at run time."* Before JDK 20, an exhaustive **enum** switch threw
        `IncompatibleClassChangeError`. From JDK 20 preview / **JDK 21 final** onward it throws
        `MatchException`, for enum, sealed and pattern switches alike. `[SOURCE]` `[VERSION-TRAP]` `[NUM]`

3.13.13 `IncompatibleClassChangeError` has **not** disappeared — it remains the error for genuine
        incompatible class changes, including the sealing violation in §3.13.5 and older
        separately-compiled-switch scenarios. The two are not synonyms and the boundary is
        "no label applied" (`MatchException`) versus "the class shape is illegal" (`ICCE`).
        `[TRAP]` `[PROVE]`

3.13.14 The scenario that produces `MatchException` in production: a library ships
        `sealed interface RestrictionOutcome permits Allowed, Blocked`; a consumer compiles an
        exhaustive switch; the library adds `Limited` and is upgraded **without recompiling the
        consumer**. The consumer's switch was exhaustive at compile time and is not at run time.
        `[INCIDENT]` `[FLOW]`

3.13.15 The mitigation from OpenJDK's own exhaustiveness guide: for a sealed API you expect to evolve,
        either keep a `default` (giving up the compile-time check for forward compatibility) or treat
        adding a permitted subtype as a **binary-incompatible change** and version accordingly. There
        is no option that is both exhaustive and forward-compatible. `[SOURCE]` `[DECIDE]`

3.13.16 The conclusion for visitor: for a **closed** hierarchy, sealed + exhaustive switch delivers
        visitor's guarantee with no `accept`, no `visit`, no double dispatch, and the errors at compile
        time; for an **open** hierarchy it delivers nothing and visitor (or a plain interface method)
        remains the answer. The discriminator is `permits`, not taste. `[DECIDE]` `[SAY]`

*(16 leaves)*

## §3.14 Immutability at JIT level: trusted finals, constant folding, and the safe-publication guarantee

3.14.1 `static final` fields of constant-expression primitive/`String` type are folded by **`javac`**
       into the reading class's constant pool — before the JVM is involved (§3.3.2). `[SOURCE]`

3.14.2 `static final` fields of *reference* type are folded by **C2**: once the holder class is
       initialised, the field's value is a known constant, so C2 treats it as such and can then
       devirtualise calls on it and fold its own `final` fields transitively. `[PROVE]`

3.14.3 Non-static `final` fields are **not** trusted by default. HotSpot's default trust set is:
       `java/lang/invoke` and `sun/invoke` packages, VM/hidden classes, **record classes**, all boxed
       classes, `java.lang.String`, and the `Atomic*FieldUpdater` implementations. `[SOURCE]` `[NUM]`

3.14.4 `-XX:+TrustFinalNonStaticFields` — an **experimental** flag (requires
       `-XX:+UnlockExperimentalVMOptions`), **off by default**, that extends that trust to all `final`
       instance fields. `[API]` `[NUM]`

3.14.5 Shipilev's measurement of the effect: without the flag, `_static_final` = **4.202 ± 0.002 ns/op**
       and `_inst_final` = **4.317 ± 0.002 ns/op**; with the flag, `_static_final` drops to
       **1.901 ± 0.001 ns/op**. `[NUM]` `[SOURCE]` `[PROVE]`

3.14.6 Why it is not on by default, in the JDK's own terms: frameworks mutate `final` fields through
       reflection, `Unsafe` and JNI in violation of the JLS, and "the potential breakage from
       misbehaving applications may severely dampen" the gain. The flag is a bet on your dependencies'
       hygiene. `[SOURCE]` `[DECIDE]`

3.14.7 That **record classes are in the default trust set** is the load-bearing fact for this topic: it
       is a JIT-level reward for using records as value objects, not just an ergonomic one.
       `[PROVE]` `[SAY]`

3.14.8 The second JIT consequence of immutability: no write barrier. A field that is never written after
       construction never pays the G1 card-marking / SATB barrier that a mutable field pays on every
       store — which at `FundsLedger`'s 19.8M entries/day is a real allocation-path cost.
       `[NUM]` `[X-REF 06]`

3.14.9 The third: an immutable object needs no defensive copy at any boundary, so the copies that
       *would* have been allocated are not allocated, and the ones that remain are usually NoEscape
       (§3.2). Immutability's biggest performance effect is the allocations it deletes, not the field
       reads it speeds up. `[PROVE]`

3.14.10 The safe-publication guarantee restated as the JIT's precondition: C2 may fold a `final` field
        only because §17.5's freeze forbids observing it pre-initialisation — so a `this`-escape
        (§3.4.10) is not merely a JMM bug, it invalidates a compiler assumption. `[PROVE]` `[X-REF 06]`

*(10 leaves)*

## §3.15 Resilience4j internals: the state machine, the sliding windows, the CAS on state transition

3.15.1 `io.github.resilience4j.circuitbreaker.internal.CircuitBreakerStateMachine implements
       CircuitBreaker` is the whole implementation. Fields:
       `private final String name`, `private final AtomicReference<CircuitBreakerState>
       stateReference`, `private final CircuitBreakerConfig circuitBreakerConfig`,
       `private final Map<String, String> tags`, `private final CircuitBreakerEventProcessor
       eventProcessor`, `private final Clock clock`, `private final SchedulerFactory schedulerFactory`,
       `private final Function<Clock, Long> currentTimestampFunction`,
       `private final TimeUnit timestampUnit`, `private final ReentrantLock lock`. `[SOURCE]` `[API]`

3.15.2 The state is an **object, not an enum**: `CircuitBreakerState` is an abstract class with the
       inner implementations `ClosedState`, `OpenState`, `HalfOpenState`, `DisabledState`,
       `ForcedOpenState`, `MetricsOnlyState`. Each holds its own `CircuitBreakerMetrics`. That is the
       **State pattern**, and the state object decides its own successor — §1.22's discriminator made
       concrete. `[SOURCE]` `[PROVE]`

3.15.3 The public `CircuitBreaker.State` enum, quoted from `CircuitBreaker.java` — **six** constants,
       not three, each carrying `(order, allowPublish)`: `DISABLED(3, false)`, `METRICS_ONLY(5, true)`,
       `CLOSED(0, true)`, `OPEN(1, true)`, `FORCED_OPEN(4, false)`, `HALF_OPEN(2, true)`. The
       `allowPublish` flag is the mechanism by which `DISABLED` and `FORCED_OPEN` emit no events, and
       `METRICS_ONLY` is the "measure before you enforce" rollout mode most teams do not know exists:
       its javadoc says it is "collecting metrics, publishing events and allowing all requests through
       but is not transitioning to other states". `[SOURCE]` `[API]` `[NUM]`

3.15.4 The companion `CircuitBreaker.StateTransition` enum enumerates the legal transitions explicitly
        (`CLOSED_TO_OPEN`, `HALF_OPEN_TO_CLOSED`, …) — **33** named constants over the 6 states, which
        is the state machine's transition table expressed as a type rather than as `if`s. This is
        §1.22's "make illegal states unrepresentable" applied to the *transitions*, not the states.
        `[SOURCE]` `[NUM]`

3.15.5 Transitions go through `stateReference.compareAndSet(current, next)` /
       `getAndUpdate(...)`, so a losing thread's transition is simply dropped rather than applied
       twice. The transition methods, named: `transitionToClosedState()`, `transitionToOpenState()`,
       `transitionToOpenStateFor(Duration)`, `transitionToOpenStateUntil(Instant)`,
       `transitionToHalfOpenState()`, `transitionToDisabledState()`,
       `transitionToMetricsOnlyState()`, `transitionToForcedOpenState()`. `[SOURCE]` `[API]`

3.15.6 The `ReentrantLock` alongside the `AtomicReference` is the detail that catches people out: CAS
       guards the state *value*, the lock serialises the *event publication and callback* so listeners
       see transitions once and in order. Lock-free state, locked notification. `[SOURCE]` `[PROVE]`

3.15.7 `ClosedState`'s constructor calls `CircuitBreakerMetrics.forClosed(getCircuitBreakerConfig())`;
       `HalfOpenState` uses `forHalfOpen(permittedNumberOfCallsInHalfOpenState, config)`. The metrics
       object is **per state instance**, which is why a transition resets the window. `[SOURCE]` `[PROVE]`

3.15.8 The window implementations, by name: count-based → `FixedSizeSlidingWindowMetrics` (and
       `LockFixedSizeSlidingWindowMetrics`); time-based → `SlidingTimeWindowMetrics` (and
       `LockFreeSlidingTimeWindowMetrics`). `CircuitBreakerMetrics` holds
       `private final Metrics metrics` and `private int minimumNumberOfCalls`. `[SOURCE]` `[API]`

3.15.9 `[VERSION-TRAP]` The **ring-bit-buffer / `RingBitSet`** representation — a `BitSet` of 16 `long`s
       storing 1024 call outcomes as 0 = success, 1 = failure — is **Resilience4j 0.x/1.0-era**.
       Verified: `RingBitSet` appears **nowhere** in current `CircuitBreaker.java` or
       `CircuitBreakerMetrics.java` on `master`. From 1.x onward the count-based window is
       `FixedSizeSlidingWindowMetrics`: a circular `Measurement[]` of `slidingWindowSize` entries
       holding duration and outcome, with a running `TotalAggregation`. Every blog describing the ring
       bit buffer — and Resilience4j's own older readme.io pages — is describing a version you are not
       running. `[SOURCE]`

3.15.10 `FixedSizeSlidingWindowMetrics.record(...)` is O(1): it moves the head, **subtracts** the evicted
       measurement from the total aggregation and **adds** the new one. It does not rescan the window —
       which is why `slidingWindowSize` costs memory, not CPU. `[PROVE]` `[NUM]`

3.15.11 `SlidingTimeWindowMetrics` is a circular array of **per-second partial aggregations** of size
        `slidingWindowSize` (in seconds), each rotated and zeroed as the clock advances. So a
        60-second window is 60 buckets, and the resolution is 1 second — not continuous. `[NUM]` `[SOURCE]`

3.15.12 **The authoritative config surface for this whole syllabus** — every default quoted from the
        `DEFAULT_*` constants in
        `resilience4j-circuitbreaker/src/main/java/io/github/resilience4j/circuitbreaker/CircuitBreakerConfig.java`
        on `master`. Any other section quoting a default defers to this leaf. `[SOURCE]` `[NUM]` `[API]` `[TABLE]`

        | Builder property | Constant | Value |
        |---|---|---|
        | `failureRateThreshold` | `DEFAULT_FAILURE_RATE_THRESHOLD` | `50` (percent) |
        | `slowCallRateThreshold` | `DEFAULT_SLOW_CALL_RATE_THRESHOLD` | `100` (percent) |
        | `slowCallDurationThreshold` | `DEFAULT_SLOW_CALL_DURATION_THRESHOLD` | `60` (seconds) |
        | `waitDurationInOpenState` | `DEFAULT_WAIT_DURATION_IN_OPEN_STATE` | `60` (seconds) |
        | `permittedNumberOfCallsInHalfOpenState` | `DEFAULT_PERMITTED_CALLS_IN_HALF_OPEN_STATE` | `10` |
        | `maxWaitDurationInHalfOpenState` | `DEFAULT_WAIT_DURATION_IN_HALF_OPEN_STATE` | `0` (wait indefinitely) |
        | `minimumNumberOfCalls` | `DEFAULT_MINIMUM_NUMBER_OF_CALLS` | `100` |
        | `slidingWindowSize` | `DEFAULT_SLIDING_WINDOW_SIZE` | `100` |
        | `slidingWindowType` | `DEFAULT_SLIDING_WINDOW_TYPE` | `SlidingWindowType.COUNT_BASED` |
        | `transitionToStateAfterWaitDuration` | `DEFAULT_TRANSITION_TO_STATE_AFTER_WAIT_DURATION` | `State.OPEN` |
        | `writableStackTraceEnabled` | `DEFAULT_WRITABLE_STACK_TRACE_ENABLED` | `true` |

        `public enum SlidingWindowType { TIME_BASED, COUNT_BASED }` — two constants, and the enum is
        nested in `CircuitBreakerConfig`.

3.15.13 Two properties that are **not** in the `DEFAULT_*` block, so their defaults are field
         initialisers I did not read: `automaticTransitionFromOpenToHalfOpenEnabled` (believed `false`)
         and `maxWaitDurationInHalfOpenState`'s interaction with
         `DEFAULT_WAIT_DURATION_IN_HALF_OPEN_STATE = 0`. The `= 0` is confirmed and means "no time
         limit — wait for `permittedNumberOfCallsInHalfOpenState` calls however long that takes",
         which is the mechanism behind §3.15.17. The `automaticTransition...` default is
         **unconfirmed**; see the notes block. `[RESEARCH]` `[API]`

3.15.14 `[NUM]` The arithmetic that makes the defaults dangerous, stated once: `minimumNumberOfCalls =
         100` **and** `slidingWindowSize = 100` means the breaker needs 100 calls *in the window* before
         it computes a rate at all, and the window is **per breaker instance, per JVM**. Across
         `DocumentVerification`'s 6 instances that is 600 estate-wide calls before any instance can
         open. Every incident in §3.22.6 follows from these two numbers being equal and large.

3.15.15 `minimumNumberOfCalls` is the gate, and the source shows the mechanism exactly:
        `if (bufferedCalls == 0 || bufferedCalls < minimumNumberOfCalls) return -1.0f;` — the
        **`-1.0f` sentinel** — and `checkIfThresholdsExceeded()` maps `-1` to
        `Result.BELOW_MINIMUM_CALLS_THRESHOLD`, which prevents any transition. `[SOURCE]` `[NUM]` `[PROVE]`

3.15.16 `[TRAP]` The default pairing `minimumNumberOfCalls = 100` with `slidingWindowSize = 100` is the
        breaker-that-never-opens configuration for a low-traffic path: the identity-vendor call in
        `DocumentVerification` at 24k uploads/day spread over 6 instances may not reach 100 calls in a
        window before the outage ends. Symptom: the dependency is dead, the breaker is `CLOSED`, and
        every call burns its full 38 s p99. `[INCIDENT]` `[NUM]`

3.15.17 `[TRAP]` The breaker-that-never-closes mirror: with
        `automaticTransitionFromOpenToHalfOpenEnabled` **off** (believed the default — see §3.15.13),
        the transition to `HALF_OPEN` happens **on the next call attempt**, not on a timer, because
        `OpenState` only checks its wait-duration clock when a call asks permission. If upstream has
        also given up calling (or a bulkhead is rejecting first), the breaker sits `OPEN` indefinitely
        and recovery never gets probed. `[INCIDENT]` `[NUM]`

3.15.18 `HalfOpenState` admits exactly `permittedNumberOfCallsInHalfOpenState` calls and rejects the
        rest with `CallNotPermittedException`; when that many results are in, it evaluates the failure
        rate and transitions to `CLOSED` or back to `OPEN`. Note that **rejections are not failures** —
        `CallNotPermittedException` is not recorded in the window, or the breaker would feed itself.
        `[PROVE]` `[API]`

3.15.19 **Decorator composition order.** `Decorators.ofSupplier(...)` applies in the order
        `Bulkhead → TimeLimiter → RateLimiter → CircuitBreaker → Retry`, i.e. **`Retry` is the
        outermost**, so each retry attempt is a separate call *through* the breaker and is counted by
        it. That is the order you want: the breaker sees the amplified load and can open. Put `Retry`
        **inside** the breaker and the breaker counts one logical call per N attempts, so it opens
        N times too late while the dependency takes N times the load — the retry-amplification
        mechanism in §3.22.1. `[DECIDE]` `[PROVE]` `[NUM]`

*(19 leaves)*

## §3.16 Event-sourcing internals: the append-only log, version-based optimistic concurrency, snapshotting, upcasting

3.16.1 The event-store table shape, column by column: `aggregate_id UUID`, `version BIGINT`,
       `event_type VARCHAR`, `payload JSONB/BYTEA`, `metadata JSONB` (correlation id, causation id,
       actor, role — §6.3), `occurred_at TIMESTAMPTZ`, `global_sequence BIGSERIAL`. `[API]` `[BUILD]`

3.16.2 `UNIQUE (aggregate_id, version)` **is** the optimistic concurrency control. There is no separate
       lock, no `SELECT ... FOR UPDATE`, no version column to compare: two concurrent commands both
       read version 47, both try to insert version 48, and the database rejects one with a unique-key
       violation. `[PROVE]` `[SOURCE]`

3.16.3 The Java-side translation: Postgres SQLSTATE **23505** (`unique_violation`) →
       `DataIntegrityViolationException` → caught and rethrown as a domain
       `ConcurrentModificationException`/`OptimisticLockException`, then retried by reloading and
       re-deciding. Catching the *right* exception is the whole implementation. `[API]` `[DIAG]`

3.16.4 The append is **insert-only** — no `UPDATE`, no `DELETE`. Enforced, not hoped for: a
       `BEFORE UPDATE OR DELETE` trigger that raises, or a role with `INSERT, SELECT` grants only.
       An append-only log that the application *could* update is not a log. `[BUILD]` `[DECIDE]`

3.16.5 `global_sequence` gives a total order for projections to follow, but it is **not gap-free**: a
       `BIGSERIAL` advances on rolled-back transactions, so a projection that assumes contiguity stalls
       forever on a gap. Consume by "greater than my last seen", never "equals last + 1".
       `[TRAP]` `[PROVE]`

3.16.6 The replay loop, as a flow: `SELECT payload, event_type, version FROM events WHERE aggregate_id
       = ? AND version > ? ORDER BY version` → deserialise → `for (e : events) state = apply(state, e)`
       → set `state.version` to the last event's version. `apply` must be **pure and total** — no I/O,
       no clock, no random, and no throwing on an old event. `[FLOW]` `[PROVE]`

3.16.7 `[TRAP]` Validation inside `apply`. The command handler validates; `apply` only folds. An
       `apply` that rejects a historically-valid event makes the aggregate permanently unloadable —
       the event happened, and the past is not negotiable.

3.16.8 Snapshotting: a `snapshots(aggregate_id, version, state, created_at)` row; load = latest
       snapshot + events with `version > snapshot.version`. The snapshot is a **memento** (§1.28) and
       must be treated as a cache — deletable and rebuildable, never the source of truth. `[PROVE]`

3.16.9 The snapshot-cadence arithmetic for `FundsLedger`: **19.8M entries/day** across
       **2.4M registered clients** is ~8 events/client/day, so a client's position aggregate reaches
       ~2,900 events/year. At a 4-entry stake reservation and a monthly-active base of 380k, the
       *active* client accrues ~52 events/day → ~19k/year. A snapshot every **200 events** bounds
       replay at 200 rows × 180 bytes = **36 KB** and one index seek. `[NUM]` `[PROVE]`

3.16.10 The cadence trade stated as the decision procedure: snapshot every N events where N × row-read
        cost ≤ your load-latency budget. Against the **80 ms balance-read budget**, 200 events is two
        orders of magnitude of headroom; against the **150 ms stake-reservation budget** with a write
        in the same transaction, it is still comfortable. Snapshot on a *schedule* instead and the
        worst case is unbounded. `[DECIDE]` `[NUM]`

3.16.11 `[TRAP]` The snapshot that embeds the serialised domain object (Java serialization, or Jackson
        with default typing) welds the store to a class shape. Snapshots must serialise a **versioned
        DTO**, or the next refactor makes every snapshot unreadable — and unlike events, that is
        survivable only because you can delete them all and replay.

3.16.12 Event versioning strategies, all four, with the cost of each: (1) **weak schema** — additive-only
        fields with defaults; (2) **upcasting** — an `EventUpcaster` chain transforming v1 payload → v2
        at read time; (3) **multiple versions in the type name** (`StakeReserved.v2`) with a handler per
        version; (4) **copy-and-replace** — a one-off migration writing a new stream. `[TABLE]` `[DECIDE]`

3.16.13 The upcaster mechanism concretely: registered as an ordered chain keyed by
        (event type, version), each step raising the payload one version, so a v1 event read in 2029
        passes through three upcasters before reaching `apply`. The chain must be **kept forever**, and
        it is code with no tests unless you keep a corpus of old payloads. `[PROVE]` `[BUILD]`

3.16.14 `[INCIDENT]` The schema-evolution failure mode: a developer **renames** a field on
        `StakeReserved` (or changes `amount` from minor units to a decimal string) and deploys. Symptom:
        replay of aggregates last touched before the deploy throws `MismatchedInputException` /
        yields `null` amounts; positions load as zero; balance reads return wrong money. Diagnosis path:
        the failure is version-correlated (only old streams break), the error is in deserialisation not
        in business logic, and `occurred_at` on failing events all precede the deploy. Root cause: a
        field rename is a **wire-format** change on an immutable log. Fix: revert, add an upcaster,
        redeploy — and add a test that deserialises a frozen corpus of every historical payload shape.

3.16.15 GDPR erasure against an append-only log, mechanism named: **crypto-shredding** — encrypt each
        subject's PII payload fields with a per-subject key held in a separate keystore, and delete the
        key. The events remain, the plaintext does not. The cost is that replay of a shredded stream
        yields events with unreadable fields, so `apply` must tolerate them. `[DECIDE]` `[X-REF 13]`

3.16.16 Why CQRS is **not optional** here (the constraint, not a preference): the log answers exactly
        one query — "events for aggregate X in version order". "All withdrawals for client Y" (scenario §7.3) is
        unanswerable against it, so a projection is mandatory and its lag is a permanent property of
        the design. `[PROVE]` `[X-REF 22]`

*(16 leaves)*

## §3.17 Outbox internals: same-transaction insert, polling vs CDC, ordering, dedup, relay idempotence

3.17.1 The problem the outbox exists to solve, stated as the impossibility: a database write and a
       broker publish cannot be made atomic without a distributed transaction, so any code that does
       both has a window where one succeeded and the other did not. The outbox removes the second
       resource from the transaction rather than coordinating it. `[PROVE]`

3.17.2 The table: `outbox(id UUID PK, aggregate_type, aggregate_id, event_type, payload JSONB,
       created_at TIMESTAMPTZ, processed_at TIMESTAMPTZ NULL, attempts INT DEFAULT 0)`. Plus the index
       that makes the relay query sargable: `CREATE INDEX ON outbox (created_at) WHERE processed_at IS
       NULL` — a **partial index**, so it stays small as the table grows. `[API]` `[BUILD]` `[NUM]`

3.17.3 The same-transaction insert is the entire correctness argument: the ledger entries and the
       outbox row are inserted **in one local ACID transaction**, so the event exists if and only if
       the state change committed. `[PROVE]`

3.17.4 `[TRAP]` The version that looks identical and is broken: publishing in an
       `@TransactionalEventListener(phase = AFTER_COMMIT)` (§3.19). The commit succeeded, the publish
       is outside it, and a crash between them loses the event silently. After-commit publication is
       *better* than in-transaction publication and is still **not** an outbox.

3.17.5 The relay's polling query: `SELECT * FROM outbox WHERE processed_at IS NULL ORDER BY created_at
       FOR UPDATE SKIP LOCKED LIMIT 100`. `FOR UPDATE` takes row locks; **`SKIP LOCKED`** is what lets
       N relay instances poll the same table concurrently without blocking each other or double-sending.
       `[SOURCE]` `[API]` `[PROVE]`

3.17.6 `SKIP LOCKED` semantics that matter: it skips rows locked by *any* transaction, so a relay
       instance that hangs mid-batch holds its rows until its transaction ends — the rows are not lost
       but they are delayed by the hung instance's transaction lifetime, not by the poll interval.
       `[TRAP]` `[PROVE]`

3.17.7 `NOWAIT` and plain `FOR UPDATE` as the wrong choices here: `NOWAIT` errors instead of skipping;
       plain `FOR UPDATE` serialises the relays. Naming why the alternatives fail is the source-level
       answer. `[DECIDE]`

3.17.8 **CDC / Debezium** as the other relay: it reads the Postgres **WAL** through a logical
       replication slot rather than polling, so there is no query load, no poll interval, and no
       `processed_at` update. Costs: a replication slot that **retains WAL** if the connector stalls
       (a disk-full outage mechanism), Kafka Connect to operate, and payload shape dictated by the
       table rather than by you. `[DECIDE]` `[API]` `[X-REF 14]`

3.17.9 The Debezium **outbox event router** (`io.debezium.transforms.outbox.EventRouter`) as the
       middle path: still an outbox table, but CDC-read, with `aggregate_id` routed to the Kafka message
       key and `payload` unwrapped into the value. `[API]` `[RESEARCH]`

3.17.10 The delivery guarantee is **at-least-once**, and the mechanism is unavoidable: the relay
        publishes, then marks `processed_at`. A crash between the two republishes. Making it
        exactly-once would need the same atomicity the outbox exists because you cannot have.
        `[PROVE]` `[TRAP]`

3.17.11 Therefore **consumer idempotence is mandatory, not defensive**: a `processed_events(event_id
        PK)` table inserted in the consumer's own transaction, with the primary-key violation as the
        duplicate detector. The **unique index is the mechanism** — check-then-insert is a race.
        `[BUILD]` `[X-REF 12]`

3.17.12 Ordering, precisely: ordering **within an aggregate** is achievable — key the Kafka message by
        `aggregate_id` so all its events land on one partition and are consumed in order.
        Ordering **globally** is not, without a single partition, which caps throughput at one
        consumer. State which one the domain needs. `[DECIDE]` `[PROVE]` `[X-REF 14]`

3.17.13 `[TRAP]` The subtler ordering break: `ORDER BY created_at` with `LIMIT 100` and multiple relay
        instances can still publish aggregate A's event 2 before event 1 if they land in different
        batches on different instances. The fix is to make the *ordering unit* the aggregate: either one
        relay, or `SKIP LOCKED` over a hash-partitioned claim so one aggregate is only ever handled by
        one instance.

3.17.14 The poll-interval-vs-latency trade with the domain's numbers: `FundsLedger` at **230 writes/sec
        sustained** and a **13,600/sec peak**. A 1-second poll adds up to 1 s of event latency and runs
        86,400 queries/day/instance; a 100 ms poll adds ≤ 100 ms and runs 864,000. Against a
        **24-hour** withdrawal-to-bank budget, 1 s is free; against `PendingActions` banner freshness it
        is visible. Pick the interval from the *consumer's* budget. `[NUM]` `[DECIDE]`

3.17.15 `[INCIDENT]` The relay-as-bottleneck failure. Symptom: `outbox` row count climbing
        monotonically, consumer lag flat because nothing is being published, and the *write* path
        perfectly healthy — the transaction still commits. Diagnosis path: `SELECT count(*) FROM outbox
        WHERE processed_at IS NULL` growing; the relay's own poll-to-publish duration flat; the partial
        index still small. Root cause: at the 13,600/sec settlement burst the relay's batch of 100 per
        1-second poll drains 100/sec against 13,600/sec of arrivals. Fix: raise `LIMIT`, shorten the
        interval, add relay instances (safe because of `SKIP LOCKED`), and **alert on outbox depth and
        oldest-unprocessed age** — the two metrics that make this visible before it is an incident.

3.17.16 The retention half nobody implements: `processed_at IS NOT NULL` rows must be deleted or
        partitioned away, or the outbox table outgrows the ledger it serves. A daily
        `DELETE ... WHERE processed_at < now() - interval '7 days'` — or a partitioned table with
        `DETACH PARTITION`, because a large `DELETE` on a hot table is its own incident.
        `[NUM]` `[DECIDE]`

*(16 leaves)*

## §3.18 Optimistic locking as the aggregate's enforcement mechanism: `@Version`, the generated SQL, the exception path

3.18.1 `jakarta.persistence.@Version` on an `int`/`Integer`/`long`/`Long`/`short`/`Short`/
       `java.sql.Timestamp` field. Exactly one per entity; it must be on the **primary table**; and it
       must **not** be updated by application code. `[API]` `[SOURCE]`

3.18.2 The generated SQL is the entire mechanism:
       `UPDATE positions SET cash_available = ?, version = ? WHERE id = ? AND version = ?`
       — the old version in the `WHERE`, the new version in the `SET`. No lock is taken anywhere.
       `[SOURCE]` `[DIAG]`

3.18.3 Hibernate compares the **row count returned by the JDBC driver** to 1. Zero rows affected means
       someone else has already incremented the version, and Hibernate raises
       `StaleStateException`/`StaleObjectStateException`. `[SOURCE]` `[PROVE]`

3.18.4 The exception chain, exactly and in order: Hibernate's `StaleObjectStateException` →
       JPA's `jakarta.persistence.OptimisticLockException` → Spring's
       `ObjectOptimisticLockingFailureException` (a `ConcurrencyFailureException`, itself a
       `DataAccessException`). Which one you catch depends on which layer you are in, and catching the
       Spring one is what keeps the domain free of JPA. `[API]` `[TRAP]`

3.18.5 **When** it is thrown is the detail that surprises people: at **flush**, which for a
       `@Transactional` method is usually at commit — so the exception surfaces *after* the method
       body returned, and a `try/catch` inside the method never sees it. `[TRAP]` `[PROVE]`

3.18.6 The version increment happens on flush of a **dirty** entity, so a transaction that only *reads*
       does not bump it. `LockModeType.OPTIMISTIC_FORCE_INCREMENT` is how you bump the root's version
       for a change to a **child** — which is exactly how the aggregate boundary gets enforced when the
       modified row is not the root's. `[API]` `[PROVE]`

3.18.7 `@Version` on the **aggregate root** is therefore the boundary enforcement, not a row-level
       nicety: one version check protects the whole invariant set, because every write to any member of
       the aggregate goes through the root and forces its increment. `[PROVE]` `[X-REF 08]`

3.18.8 The contrast with pessimistic locking, stated as a decision: `LockModeType.PESSIMISTIC_WRITE`
       (`SELECT ... FOR UPDATE`) serialises at the database and holds a lock for the transaction's
       duration; optimistic holds nothing and pays only on conflict. Use pessimistic when the conflict
       rate is high enough that retry cost exceeds lock cost. `[DECIDE]` `[TABLE]`

3.18.9 The conflict arithmetic for `FundsLedger`: **partition-affine by client id**, so contention is
       per-client, and a client's writes are naturally serial — except at the **3,400/sec settlement
       burst**, where many clients settle at once but each client's position is still touched once.
       Optimistic is correct here precisely because the *hot row* is per-client, not global.
       `[NUM]` `[PROVE]`

3.18.10 The retry policy that **must** accompany `@Version`, or the mechanism is just a failure mode:
        retry on `ObjectOptimisticLockingFailureException` only, **reload the aggregate** (a retry that
        reuses the stale entity re-fails forever), cap attempts (3), and back off with jitter.
        `@Retryable(retryFor = ObjectOptimisticLockingFailureException.class, maxAttempts = 3,
        backoff = @Backoff(delay = 20, multiplier = 2, random = true))` — and the retry must be on a
        **new transaction**, so it belongs on an outer bean (§3.8.19). `[BUILD]` `[API]` `[DECIDE]`

3.18.11 `[TRAP]` Retrying inside the failed transaction. The persistence context is poisoned after a
        flush failure — JPA requires the transaction be rolled back — so the retry must span
        transactions. Symptom: a second exception complaining the transaction is marked rollback-only.
        `[DIAG]`

3.18.12 `[TRAP]` Sending the version to the client and trusting it back is correct and is *also* how
        you get a silent lost update: if the client omits the version, JPA treats a `null` version as a
        new entity (`persist` rather than `merge`) or skips the check entirely. Validate the version's
        presence at the API boundary, and return `409 Conflict` rather than `500` when it fails.
        `[X-REF 12]`

*(12 leaves)*

## §3.19 Observer internals: `ApplicationEventMulticaster`, `@TransactionalEventListener` phases, `TransactionSynchronization`, the listener leak, the `ConcurrentModificationException`

3.19.1 `ApplicationEventPublisher.publishEvent(Object)` → `AbstractApplicationContext.publishEvent`
       → `getApplicationEventMulticaster().multicastEvent(event, eventType)`. The context is the
       subject; the multicaster is the listener registry. `[SOURCE]` `[API]`

3.19.2 `SimpleApplicationEventMulticaster.multicastEvent` iterates
       `getApplicationListeners(event, type)` and for each either calls `invokeListener(listener,
       event)` directly or, if `getTaskExecutor() != null`, submits it to the executor. The default
       executor is **`null`**, which the javadoc describes as equivalent to `SyncTaskExecutor`.
       `[SOURCE]` `[NUM]`

3.19.3 So the default is: **all listeners run synchronously, on the publishing thread, inside the
       publisher's transaction, in listener order**. Every one of §1.23's four failure modes is a direct
       consequence of that one default. `[PROVE]`

3.19.4 `setTaskExecutor(Executor)` and `setErrorHandler(ErrorHandler)` are the two knobs.
       `invokeListener` wraps the call in the `ErrorHandler` if one is set — **and swallows the
       exception**, so setting an error handler converts failure coupling into silent failure unless the
       handler logs and meters. `[API]` `[TRAP]`

3.19.5 The javadoc's own warning about the executor: asynchronous execution "will not participate in the
       caller's thread context (class loader, transaction context) unless the `TaskExecutor` explicitly
       supports this". So an async listener has **no transaction and no `SecurityContext`** — and
       `TransactionalApplicationListener` implementations always run in the original publishing thread
       regardless of the executor. `[SOURCE]` `[TRAP]`

3.19.6 `AbstractApplicationEventMulticaster` caches subscriber resolution in a
       `Map<ListenerCacheKey, CachedListenerRetriever>` keyed by (event type, source type), because
       resolving each listener's `ApplicationListener<T>` generic type per publish would dominate.
       `retrieveApplicationListeners` and `supportsEvent` are the resolution path. `[SOURCE]`

3.19.7 `@EventListener` is not the multicaster: `EventListenerMethodProcessor` (a
       `SmartInitializingSingleton`) scans beans after singleton instantiation and registers an
       `ApplicationListenerMethodAdapter` per annotated method — **adapter**, turning a method into a
       listener. `condition` is a SpEL expression evaluated before invocation. `[SOURCE]` `[API]`

3.19.8 `@EventListener` returning a non-`void` value **publishes the result as a new event** (or each
       element, for a collection/array). Powerful and a genuine surprise — an accidental return type
       creates an event loop. `[TRAP]` `[API]`

3.19.9 `@TransactionalEventListener` attributes, exactly: `phase` (default **`AFTER_COMMIT`**),
       `fallbackExecution` (default **`false`**), `id`, `classes`/`value`, `condition`. `[API]` `[SOURCE]`

3.19.10 `TransactionPhase`'s four constants: **`BEFORE_COMMIT`**, **`AFTER_COMMIT`**,
        **`AFTER_ROLLBACK`**, **`AFTER_COMPLETION`**. `AFTER_COMPLETION` fires for both commit and
        rollback, so it is the "always" phase; `AFTER_COMMIT` and `AFTER_ROLLBACK` are mutually
        exclusive subsets of it. `[API]` `[TABLE]`

3.19.11 The mechanism: `TransactionalApplicationListenerMethodAdapter` registers a
        `TransactionSynchronization` with `TransactionSynchronizationManager.registerSynchronization(...)`,
        and the phases map onto that interface's callbacks — `beforeCommit(boolean)`,
        `afterCommit()`, `afterCompletion(int status)` with
        `STATUS_COMMITTED`/`STATUS_ROLLED_BACK`/`STATUS_UNKNOWN`. The event is not published at
        `publishEvent` time; it is **deferred into a transaction callback**. `[SOURCE]` `[FLOW]` `[API]`

3.19.12 `fallbackExecution = false` means: with **no active transaction**, the event is silently
        **discarded**. This is the most-reported "my `@TransactionalEventListener` never fires" bug, and
        the cause is usually a caller without `@Transactional` — or self-invocation (§3.8.19) meaning
        there was never a transaction at all. `[TRAP]` `[DIAG]` `[SOURCE]`

3.19.13 Why an `AFTER_COMMIT` listener has **no transaction of its own**, in the javadoc's words: "the
        transaction will have been committed or rolled back already, but the transactional resources
        might still be active and accessible… any data access code triggered at this point will still
        *participate* in the original transaction, but changes will **not** be committed". So a save in
        an `AFTER_COMMIT` listener runs, appears to work, and is discarded. `[SOURCE]` `[TRAP]` `[PROVE]`

3.19.14 The fix for wanting to write in `AFTER_COMMIT`: `@Transactional(propagation =
        Propagation.REQUIRES_NEW)` on the listener, which starts a genuinely new transaction. And the
        honest framing: if the write must not be lost, this is not the mechanism — the outbox (§3.17)
        is. `[DECIDE]`

3.19.15 `BEFORE_COMMIT` is the one phase that **can** still affect the transaction: it runs inside it,
        so throwing rolls the whole thing back. That makes it the right phase for a final invariant
        check and the wrong phase for anything with a side effect outside the database. `[DECIDE]`

3.19.16 The two in-process observer failure mechanisms, at source level. **Listener leak:** a
        programmatically-registered `ApplicationListener` is a strong reference held by the multicaster
        for the container's lifetime, so a per-session listener in `InternalPlatforms`
        (30–90 minute sessions, 40 operators, 90 at peak) accumulates in a 4 GB heap until OOM; the fix
        is `removeApplicationListener` in a `finally`, or a `@Bean`-scoped listener that the container
        owns. **`ConcurrentModificationException`:** a listener that registers or removes a listener
        during notification mutates the collection being iterated — `AbstractList`'s `modCount` check
        (§3.10.10) fires mid-publish, and the symptom is an exception in the *publisher*, naming a class
        that never appears in the stack trace's business frames.
        `[INCIDENT]` `[NUM]` `[DIAG]`

*(16 leaves)*

## §3.20 Architecture enforcement mechanics: package-private, JPMS, ArchUnit rule evaluation, `jdeps`, build-module boundaries

3.20.1 **Package-private (default) access is the only boundary the `javac` compiler enforces for free**,
       and it is enforced at compile *and* run time (the JVM checks access on resolution). Everything
       else in this section is a tool you have to add. `[PROVE]` `[SOURCE]`

3.20.2 The mechanism that makes package-by-feature (§2.19) work: with `com.quizstakes.restrictions.*`,
       only `RestrictionDecisionService` need be `public`; `RestrictionRuleEvaluator`,
       `RestrictionRow` and the JPA repository can be package-private and are then **uncompilable**
       from another package. With package-by-layer every class must be `public` and nothing can be
       hidden. `[PROVE]` `[DECIDE]`

3.20.3 The two holes in package-private, named: Java packages are **not hierarchical** for access
       (`com.quizstakes.restrictions.internal` is a *different* package with no privileged access to its
       parent), and **reflection** plus `setAccessible(true)` ignores it entirely unless a module
       forbids it. `[TRAP]`

3.20.4 JPMS `module-info.java`: `exports <pkg>` (compile+runtime access), `exports <pkg> to <module>`
       (qualified), `opens <pkg>` (deep reflection, for Jackson/Hibernate), `requires <module>`,
       `requires transitive`, `requires static` (compile-only), `uses`/`provides ... with`
       (`ServiceLoader`, §3.10.13). `[API]` `[SOURCE]`

3.20.5 What JPMS gives that package-private cannot: a **non-exported package is invisible across the
       module boundary at run time**, enforced by the module system, and the module graph is checked at
       startup — a missing `requires` is a launch failure, not a `NoClassDefFoundError` on the unlucky
       code path. `[PROVE]`

3.20.6 `--add-exports <module>/<pkg>=<target>` and `--add-opens <module>/<pkg>=<target>` as the escape
       hatches, plus the version delta that matters: **JDK 16 made illegal reflective access denied by
       default** (`--illegal-access=deny`) and **JDK 17 removed the option**, so the "it warns" era is
       over. `[VERSION-TRAP]` `[API]`

3.20.7 The honest verdict on JPMS for a Spring Boot service: the fat-jar/classpath deployment model
       means most Boot applications run on the **unnamed module** and get none of this, so JPMS is real
       enforcement for libraries and largely aspirational for services. Say so rather than recommending
       it reflexively. `[DECIDE]` `[TRAP]`

3.20.8 **How ArchUnit actually works**, mechanism first: it does **not** use reflection to walk your
       classes. `ClassFileImporter` reads `.class` **bytecode** with its own ASM-based importer and
       builds an in-memory `JavaClasses` model — `JavaClass`, `JavaMethod`, `JavaField`,
       `JavaMethodCall`, `JavaFieldAccess`, `JavaAnnotation`. Dependencies are read from the constant
       pool and the code attributes. `[SOURCE]` `[PROVE]`

3.20.9 Why reading bytecode rather than reflecting is the load-bearing design choice: it means ArchUnit
       sees **method-call edges**, not just type signatures, so "no class in `..domain..` may call a
       method annotated `@Transactional`" is expressible; and it needs no class loading, so an
       unsatisfiable dependency does not break the analysis. `[PROVE]`

3.20.10 Missing classes: ArchUnit **creates stubs** for types it did not import, populated with what the
        bytecode revealed (fully-qualified name, methods called) but lacking superclasses and
        annotations. So a rule about a type outside the import scope can silently under-report — set
        the import scope deliberately. `[TRAP]` `[SOURCE]`

3.20.11 The evaluation API: `ArchRuleDefinition.classes()/noClasses()` starts the fluent chain,
        `ArchRule.check(JavaClasses)` throws `AssertionError` on violation, and
        `ArchRule.evaluate(JavaClasses)` returns an `EvaluationResult` carrying the failure report
        without throwing — which is what you use to build a custom fitness-function report.
        `[API] [SOURCE]`

3.20.12 The rule types that matter for §2.17's architectures: `layeredArchitecture()` with
        `.layer(...).definedBy(...)` and `.whereLayer(...).mayOnlyBeAccessedByLayers(...)`;
        `onionArchitecture()` with `.domainModels/.domainServices/.applicationServices/.adapter`;
        `slices().matching("..(*)..").should().beFreeOfCycles()` — the direct test for §2.14's circular
        dependency; and `SlicesRuleDefinition` for package cycles. `[API]`

3.20.13 `ArchRule.freeze(rule)` (`com.tngtech.archunit.library.freeze.FreezingArchRule`): on first run
        it records all current violations into a **`ViolationStore`** — by default text files under
        `archunit_store/`, configurable with `freeze.store.default.path` and
        `freeze.store.default.allowStoreCreation` — and thereafter fails only on **new** violations
        while allowing the recorded ones. This is the mechanism for adopting a rule on a legacy codebase
        without a big-bang refactor, and the store file must be committed. `[API]` `[SOURCE]` `[DECIDE]`

3.20.14 `[DIAG]` A real ArchUnit failure report, read line by line:
        ```
        java.lang.AssertionError: Architecture Violation [Priority: MEDIUM] -
        Rule 'no classes that reside in a package '..domain..' should depend on classes that
        reside in a package '..jakarta.persistence..'' was violated (2 times):
        Field <com.quizstakes.funds.domain.Position.id> has type
          <java.util.UUID> annotated with <jakarta.persistence.Id>
          in (Position.java:0)
        Method <com.quizstakes.funds.domain.Position.legs()> has generic return type
          <java.util.List<jakarta.persistence.Tuple>> in (Position.java:0)
        ```
        What each line is: the rule text is the *description*, verbatim from the fluent chain, so a
        badly-named rule produces an unreadable failure; `(2 times)` is the violation count, and the
        freeze store would contain exactly these two strings; each violation names the **`JavaField`**
        or **`JavaMethod`** and the source line, which is `:0` because bytecode carries no line number
        for a field or a signature. The fix is not to suppress it — it is that `Position` is a JPA
        entity masquerading as a domain object, which is §2.10's DIP violation caught mechanically.
        Plus the tooling around it: `jdeps --dot-output`/`-summary`/`-jdkinternals` for a
        dependency graph from jars, Maven's multi-module `<dependency>` graph and Gradle's
        `implementation` vs `api` (an `implementation` dependency is **not** on the consumer's compile
        classpath — the build tool's own package-private) as the coarse, build-time enforcement that
        makes a wrong import fail before any test runs.

*(14 leaves)*

## §3.21 Measuring design decisions: JMH on the indirection, async-profiler on the megamorphic site, the numbers that justify or kill an abstraction

3.21.1 The claim under test, stated so it can be falsified: "replacing this `switch` with a
       `Map<String, RestrictionRule>` of 11 strategy beans costs measurable latency on the 30 ms
       restriction path." Anything vaguer than that cannot be benchmarked. `[PROVE]` `[SAY]`

3.21.2 The JMH harness shape for a dispatch benchmark: `@BenchmarkMode(Mode.AverageTime)`,
       `@OutputTimeUnit(NANOSECONDS)`, `@State(Scope.Benchmark)`, `@Fork(3)`, `@Warmup(iterations = 5)`,
       `@Measurement(iterations = 10)`, and a `@Param` over the receiver-type count 1, 2, 3, 11 so the
       monomorphic/bimorphic/megamorphic transition is *in the results table*. `[BUILD]` `[X-REF 25]`

3.21.3 **Dead-code elimination** is the hazard that makes a naive dispatch benchmark report zero: C2
       proves the result unused and deletes the call. Reported effect sizes of **8–12×** faster than
       reality. Defence: return the value from the `@Benchmark` method, or `Blackhole.consume(...)`.
       `[TRAP]` `[NUM]`

3.21.4 **Constant folding** is the second: a hard-coded input, or a `final` `@State` field, lets C2
       compute the answer at compile time. Defence: non-`final` `@State` fields, inputs from state, and
       `@CompilerControl(DONT_INLINE)` where the boundary is the thing under test. `[TRAP]` `[API]`

3.21.5 **Loop unrolling and hoisting** is the third, and it is the specific reason a hand-rolled
       dispatch benchmark says indirection is free: a manual loop over an array of strategies gets
       unrolled, the invariant type check hoisted out, and the call inlined once — a shape that never
       occurs in the real caller. Defence: one operation per `@Benchmark` invocation, and
       `@OperationsPerInvocation` if you must batch. `[TRAP]` `[PROVE]`

3.21.6 The fourth, specific to this measurement and the one that makes naive benchmarks *lie in the
       favourable direction*: a benchmark that constructs its strategy list in `@Setup` with one
       implementation profiles **monomorphic**, so it measures the best case and reports it as the
       general case. The `@Param` in 3.21.2 exists to prevent exactly this. `[TRAP]` `[PROVE]`

3.21.7 `Blackhole`'s own cost (~1–2 ns/op) is a floor: a measurement of a 5 ns call through a blackhole
       cannot resolve a 1 ns difference. Know the noise floor before believing the delta.
       `[NUM]` `[X-REF 25]`

3.21.8 `-XX:+UnlockDiagnosticVMOptions -XX:+PrintInlining` as the evidence that the *mechanism* is what
       you claim: the line `@ 12 RestrictionRule::evaluate (18 bytes) inline (hot)` proves inlining;
       `failed to inline: megamorphic call` proves it did not. Read the tree, do not infer it from the
       number. `[DIAG]` `[API]`

3.21.9 `-XX:+PrintCompilation` for the coarser signal — repeated `made not entrant` / `made zombie`
       lines on the same method are the **deopt storm** (§3.1.15), which is a different problem from
       megamorphism and has a different fix. `[DIAG]` `[API]`

3.21.10 **async-profiler** on the real service, not the harness: `-e cpu` for a wall-free CPU flame
        graph, `-e alloc` to attribute allocation to the abstraction, and `--all-user` / `-t` for
        per-thread. The signature of a megamorphic site in a flame graph is a **wide frame with many
        thin children** and no inlined callee frames beneath it — the inlining that would have merged
        them did not happen. `[DIAG]` `[X-REF 25]`

3.21.11 Why async-profiler and not a JFR/hprof sampler for this question: safepoint-biased samplers
        attribute time to the safepoint poll rather than the call, so they systematically *hide*
        dispatch cost. The tool choice is part of the measurement's validity. `[PROVE]` `[X-REF 25]`

3.21.12 **The honest conclusion, and it is the point of this section.** For almost all code the
        indirection is not the cost: at ~5 ns for a fully megamorphic dispatch against a **30 ms**
        restriction budget, an **80 ms** balance read or a **150 ms** stake reservation, the abstraction
        is six orders of magnitude below the budget, and the real costs are the network hop, the
        serialisation, the query and the log line. The shapes where it *is* the cost, named specifically:
        (1) a megamorphic call inside a loop over millions of elements, where the lost inlining blocks
        bounds-check elimination and scalar replacement; (2) an interface call on the allocation path
        that prevents escape analysis (§3.2.8) and turns a free object into a real one;
        (3) a `Comparator` or hash function called O(n log n) times inside a sort; (4) an indirection
        that adds an **allocation** per call rather than a dispatch — a boxed argument, a `Stream` per
        invocation, an exception used for control flow. In every one of those the mechanism is *lost
        optimisation or added allocation*, never the jump. Reject an abstraction for **cognitive** cost
        with a straight face; reject it for **dispatch** cost only with a JMH result and a
        `PrintInlining` line. `[DECIDE]` `[PROVE]` `[NUM]` `[SAY]`

*(12 leaves)*

## §3.22 Failure case studies: real postmortems where a design pattern or its absence was the root cause

3.22.1 `[INCIDENT]` **Retry amplification — AWS DynamoDB, us-east-1, 20 September 2015**
       (`aws.amazon.com/message/5467D2`). Symptom: elevated DynamoDB error rates in us-east-1
       cascading into EC2, SQS and other services; ~3 hours; manual intervention required to recover.
       Diagnosis path: storage nodes were failing their membership checks against the internal
       **metadata service** and taking themselves out of service. Root cause: a brief network
       disruption made storage nodes **re-request their partition assignments simultaneously**, at a
       moment when a new feature (Global Secondary Indexes) had made those membership requests larger
       and slower; the metadata service could not keep up, nodes timed out and retried, and the retries
       were the load. A retry policy is a *design* decision and this is its failure mode: the retry made
       an unavailable dependency **more** unavailable. Fix: AWS increased metadata-service capacity,
       reduced the membership-request size, and — the design fix — **decoupled** the membership check
       so a storage node does not need the metadata service to keep serving.

3.22.2 `[INCIDENT]` **Retry storms in a service graph, amplification arithmetic.** The mechanism, from
       the Amazon Builders' Library *Timeouts, retries, and backoff with jitter*: three retries per hop
       across a four-hop chain is 3⁴ = **81×** the load on the deepest service at exactly the moment it
       is least able to serve it. Symptom: the leaf service's load rising while the front-door request
       rate is flat or falling. Root cause: retry budgets composed multiplicatively because each layer
       owned its own policy. Fix: retry **at one layer only** (usually the outermost), a **token-bucket
       retry budget** so retries can never exceed a fraction of first attempts, and jitter — the
       library's line is that backoff without jitter merely spaces the synchronised waves further apart.
       `[NUM]` `[X-REF 10]`

3.22.3 `[INCIDENT]` **Slack, 4 January 2021** (`slack.engineering/slacks-outage-on-january-4th-2021/`).
       Symptom: clients unable to connect, 10:14–15:10 ET. Diagnosis path: the load-balancing tier
       showed an extremely high rate of health-check failures against web application instances.
       Root cause: network saturation, with the recovery itself contended — provisioning more instances
       took longer than usual *because* the network was unhealthy. The design detail worth stealing:
       the load balancers had a **"panic mode"** that, when too many instances fail health checks,
       balances across **all** instances rather than none. That is a deliberate fail-open decision in a
       health-check strategy, and without it aggressive health checking removes the entire fleet — a
       resilience pattern whose default behaviour is a total outage. Fix: capacity and scaling changes,
       and the acknowledgement that circuit breaking + retries + panic mode had to work *together*.

3.22.4 `[INCIDENT]` **A monitoring system that depended on the thing it monitored — Roblox, 28–31
       October 2021** (`about.roblox.com/newsroom/2022/01/roblox-return-to-service-10-28-10-31-2021`).
       Symptom: 73 hours of downtime affecting ~50M users. Root cause: two compounding issues — enabling
       a **new Consul streaming feature** under unusually high read/write load caused excessive
       contention, and those load conditions triggered a pathological performance bug in **BoltDB**,
       whose write-ahead-log pages are marked free but never returned to disk. Contributing factors,
       and these are the *design* findings: **a single Consul cluster served multiple workloads**
       (no bulkhead), and **critical monitoring depended on Consul** — the observability that would
       have diagnosed it was inside the blast radius. Fix: separate clusters per workload, and
       telemetry with an independent failure domain. The transferable rule: an observability system that
       shares a dependency with the system it observes is not an observability system.

3.22.5 `[INCIDENT]` **Thundering herd on cache expiry (cache stampede).** Symptom: a periodic latency
       and error spike at a fixed interval matching a TTL, with database CPU saturating for seconds
       while the application's own request rate is unchanged. Diagnosis path: the spike period equals
       the TTL; the database shows N identical queries in the same millisecond where N is the concurrent
       request count. Root cause: one popular key expires and every concurrent request misses
       simultaneously — the cache-aside *pattern* with a synchronised expiry is the cause, not the
       traffic. Fixes, in order of preference: **request coalescing / single-flight** (one loader per
       key, the rest wait), **jittered TTLs** so keys do not expire together, **probabilistic early
       recomputation** (refresh-ahead with a random window), and **stale-while-revalidate** (serve the
       old value while one thread refreshes). Against QuizStakes: agreement documents (~180 versions,
       cached for days) are the exposed surface, and the `ClientRestrictions` decision is deliberately
       **never cached**, which is why it has no stampede but also no cache headroom. `[X-REF 15]` `[NUM]`

3.22.6 `[INCIDENT]` **A circuit breaker configured so it never opened.** Constructed against QuizStakes
       (see notes) with the real defaults from §3.15.12. Symptom: the **watchlist provider** is in a
       multi-hour full outage (its documented characteristic failure); `AA-500 SCREENING_IN_PROGRESS`
       backs up; the breaker metric reports `CLOSED` throughout, and every call burns its 30 s timeout.
       Diagnosis path: the breaker's own `resilience4j_circuitbreaker_state` gauge shows `CLOSED`, and
       `resilience4j_circuitbreaker_buffered_calls` shows **fewer than `minimumNumberOfCalls`**. Root
       cause: `minimumNumberOfCalls = 100` (default) with `slidingWindowSize = 100` against a call rate
       of a few per minute across 6 instances — the failure rate is never computed at all, the
       `-1.0f` sentinel (§3.15.15) returns `BELOW_MINIMUM_CALLS_THRESHOLD`, and the breaker is
       decorative. Compounding: the window is **per instance**, so the effective rate per breaker is
       1/6 of the estate's. Fix: `minimumNumberOfCalls` proportional to the *actual* per-instance rate
       (5–10 here), `slidingWindowType = TIME_BASED` for low-traffic paths, and an alert on
       "dependency error rate high **and** breaker `CLOSED`" — the assertion that the breaker is
       working. `[NUM]`

3.22.7 `[INCIDENT]` **A circuit breaker that never closed.** Symptom: a dependency recovered 40 minutes
       ago and the caller still fails fast; the breaker gauge reads `OPEN` indefinitely. Root cause:
       `automaticTransitionFromOpenToHalfOpenEnabled` left **off** (believed the default, §3.15.13)
       means the `OPEN → HALF_OPEN`
       transition is evaluated **on the next call attempt**, and the upstream had itself stopped calling
       (its own bulkhead rejecting, or a queue drained). No call, no probe, no recovery. Fix: enable
       automatic transition, or ensure a synthetic probe keeps calling. The general lesson: a breaker's
       recovery path is **call-driven**, so any pattern that stops calls also stops recovery. `[NUM]`

3.22.8 `[INCIDENT]` **An unbounded queue turning backpressure into an OOM.** Symptom: heap grows
       monotonically under load, `java.lang.OutOfMemoryError: Java heap space`, and the heap dump's
       dominator tree is a single `LinkedBlockingQueue$Node` chain holding request objects. Diagnosis
       path: latency rises long before the OOM (queue wait, not service time), and thread count is flat
       at core size. Root cause: `Executors.newFixedThreadPool(n)` passes an **unbounded**
       `LinkedBlockingQueue` (§3.10.17), so the pool never grows past `corePoolSize`, never rejects, and
       absorbs overload into the heap. Against `DocumentVerification`: an 8 GB heap and **2–6 MB**
       document buffers means ~1,500 queued uploads is the entire heap — an OOM in minutes, not hours,
       at 24k uploads/day. Fix: a **bounded** `ArrayBlockingQueue` sized from Little's law plus an
       explicit `RejectedExecutionHandler` (`AbortPolicy` and a 503, or `CallerRunsPolicy` to push
       backpressure up the stack), and a queue-depth metric. `[NUM]` `[X-REF 05]`

3.22.9 `[INCIDENT]` **A distributed monolith's coupled deploy.** Symptom: a one-field change requires a
       coordinated release across five services, a release train, and a rollback plan that is itself a
       distributed transaction; every incident review names "we deployed X but not Y". Diagnosis path,
       as three yes/no questions: do two services write the same table? does a feature require a
       coordinated release? is there a service whose only job is to read another's data? Root cause:
       services split by **layer or entity table** rather than by bounded context, so every use case
       fans out. Against QuizStakes the tell is explicit: **"show me all my withdrawals" is not a
       query** (scenario §7.3) — it is a fan-out to `cardpayments` and `bankwithdrawal`. That is a *correct*
       decomposition with an aggregator; the anti-pattern is the version where the two share a schema.
       Fix: recombine into a modular monolith along the wrong seam and re-extract along the bounded
       context, or introduce an explicit anti-corruption layer and stop the cross-schema access. `[DIAG]`

3.22.10 `[INCIDENT]` **An anemic model that let an invariant break under concurrency.** Constructed
        against QuizStakes (see notes). Symptom: a reconciliation break — the sum of ledger entries for
        one client is non-zero, and `CLIENT_BONUS_AVAILABLE` is **negative** for 3 clients out of a
        day's 2.8M reservations. Diagnosis path: the ledger's own zero-sum invariant check fails at the
        nightly run; the affected clients all had two `ReserveStake` calls within the same
        millisecond; both reservations passed the "enough bonus" check. Root cause: the check
        (`min(BONUS_AVAILABLE, 10% of stake)`, §11.4) lived in a **service method** reading a
        `Position` field bag with public setters, so two threads read the same available balance and
        both wrote. Nothing in the `Position` type could refuse it. Fix: move the invariant into the
        aggregate (`position.reserve(amount)` returning the split or throwing), make the setters
        private, and add `@Version` on the root (§3.18.7) so the second write fails rather than
        succeeding. The generalisation: an anemic model does not *cause* a race, it removes the only
        place a race could have been prevented. `[NUM]`

3.22.11 `[INCIDENT]` **An over-abstracted plugin framework nobody could change.** Constructed against
        QuizStakes (see notes). Symptom: adding one restriction type — a regulator-mandated change with
        a fixed date — takes 11 days and touches an abstract factory, a strategy interface, a decorator
        chain and an XML rule descriptor; two of the three engineers who understood it have left.
        Diagnosis path: `git log` shows the framework's extension points have received **one**
        implementation each in three years; the indirection depth from controller to the actual
        `if (restriction.type() == SELF_EXCLUDED)` is seven hops. Root cause: seams introduced at the
        first case rather than the third (the rule of three, §1.5) — indirection with no variation
        flowing through it. Fix: **inline** the single-implementation abstractions (each inlining is a
        mechanical, behaviour-preserving refactor protected by the existing tests), keep the one seam
        that has genuinely varied, and record the decision as an ADR so the next engineer knows the
        collapse was deliberate. `[SMELL]` `[NUM]`

3.22.12 `[INCIDENT]` **Fallback that made the outage worse** (Amazon Builders' Library, *Avoiding
        fallback in distributed systems*). Symptom: the primary path fails, the fallback path is
        exercised for the first time in production at the worst possible moment, and it fails too —
        or succeeds and hides the failure until capacity runs out. Root cause: a fallback is a code path
        with **no production traffic**, therefore untested, therefore broken; and a fallback that adds
        load (retry, re-read, recompute) is a positive feedback loop. Fix, as stated by the library:
        prefer **proactive** redundancy — always make the redundant request so a failure adds no load —
        or remove the fallback and let the operation fail cleanly. The pattern-level lesson: a
        resilience pattern that only runs during an incident is a pattern you have never tested.
        `[DECIDE]`

3.22.13 The cross-cutting pattern in every one of these, stated once: the root cause is almost never a
        *missing* pattern. It is a pattern present but **configured on assumptions that stopped holding**
        (3.22.6, 3.22.7), **composed with another pattern that inverts its effect** (3.22.2, 3.22.8),
        or **sharing a failure domain with the thing it protects** (3.22.4, 3.22.12). `[PROVE]` `[SAY]`

3.22.14 `[SAY]` The interview delivery for this section: "The design failures I've seen in postmortems
        aren't missing abstractions — they're a retry policy that multiplied across four hops, a
        breaker whose `minimumNumberOfCalls` meant it never opened, and monitoring that lived inside
        the blast radius. So when I add a resilience pattern I state the number that makes it fire, and
        I add the alert that asserts it fired."

*(14 leaves)*

---

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
       the six states including `DISABLED`, `FORCED_OPEN` and `METRICS_ONLY`,
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

**Cross-lane merge — 5.2.108 onward.** Leaves 5.2.1–5.2.107 restate the `**Trap:**` markers
carried by the flat guide. Everything below is a `[TRAP]` leaf raised by PARTS 1–3 that had no
counterpart there, restated in one line and grouped by where the material arises. Origin
section is given so a reader who fails a line knows which section to reread.

**From §1.1–§1.19 — patterns, creational, structural.**

5.2.108 "A team convention is a pattern" → anything a linter or a build rule can enforce
        (package naming, constructor-injection-only) carries no design decision, so naming it
        as a pattern scores nothing. `[TRAP]` — §1.3.11

5.2.109 "Everything with a name is a GoF pattern" → repository and DTO are patterns but
        Fowler's (PoEAA), and "the service pattern" is a package name. Know which of the three
        you are naming. `[TRAP]` — §1.3.13

5.2.110 "The 23 GoF patterns are the vocabulary" → the ones interviewers actually ask for
        include static factory method, object pool, null object, specification, repository, DTO,
        registry, value object and dependency injection, none of them GoF. `[TRAP]` — §1.4.12

5.2.111 "The GoF names mean what they mean elsewhere" → prototype is unrelated to JavaScript
        prototypes, proxy to an HTTP forward proxy, facade to a layered app's facade *layer*.
        `[TRAP]` — §1.4.13

5.2.112 "`List.of(someList)` snapshots it" → `of` takes *elements* and `copyOf` takes a
        *collection*, so `List.of(someList)` compiles into a one-element list of lists.
        `[TRAP]` — §1.6.9

5.2.113 "A caching static factory is always safe" → `Integer.valueOf` is safe only because
        `Integer` is immutable; a cached mutable `StakeReservation` handed to two callers is
        shared mutable state. `[TRAP]` — §1.6.14

5.2.114 "Any method that returns a new object is the factory pattern" → a `static` creator is a
        static factory; GoF factory method is **virtual**, overridden by a subclass of the
        creator. `[TRAP]` — §1.7.12

5.2.115 "Abstract factory is a factory of factories" → that describes the structure and hides
        the intent; the sentence that scores is "a family of products that must be used
        together". `[TRAP]` — §1.8.12

5.2.116 "A Spring singleton bean may hold instance fields" → scope `singleton` means one
        instance shared by every request thread, so a mutable instance field is shared mutable
        state on each of `ClientRestrictions`' 8 instances. `[TRAP]` — §1.10.16

5.2.117 "A singleton is one instance per JVM" → one per **classloader**; cluster-wide
        uniqueness is a leader-election problem with a lease and a fencing token, not a pattern.
        `[TRAP]` — §1.10.17

5.2.118 "The adapter's job is done once the data is converted" → an adapter that lets the SDK's
        `VendorHttpException` escape through the port has adapted the data and not the failure,
        and every caller now depends on the vendor. `[TRAP]` — §1.13.12

5.2.119 "A facade cannot become a god object" → it has no invariant of its own, so it accretes
        every "while you're in there" call and is the most reliable route to one.
        `[TRAP]` — §1.14.9

5.2.120 "There is one thing called a facade" → three: GoF facade (hides complexity), the facade
        *layer* of a layered app (a naming convention), and Fowler's `RemoteFacade` (a
        coarse-grained remote interface). `[TRAP]` — §1.14.10

5.2.121 "A JDK dynamic proxy can be injected by concrete class" → it implements the *interfaces*
        only, so concrete-class injection fails at startup with a cast error rather than
        degrading. `[TRAP]` — §1.15.8, §3.8.11

5.2.122 "Anything with an interface between two things is a bridge" → the test is whether you
        can name **both** axes and show each varies independently; one axis means it is
        strategy. `[TRAP]` — §1.18.11

5.2.123 "A flyweight can be mutable if callers are careful" → immutability is a hard
        precondition; a mutable shared instance is shared mutable state across every client that
        ever looked it up, with no lock anywhere. `[TRAP]` — §1.19.4

**From §1.20–§2.5 — behavioural, vocabulary, selection and disambiguation.**

5.2.124 "A `final` method is safe" → a `final` template method on a proxied bean cannot be
        intercepted by CGLIB, so `@Transactional` on the skeleton is a silent no-op.
        `[TRAP]` — §1.21.5

5.2.125 "Template hooks can be `public`" → a public hook is callable out of sequence by any
        collaborator, reintroducing exactly the ordering violation `final` was protecting.
        `[TRAP]` — §1.21.6

5.2.126 "A default hook implementation is a convenience" → a default that does real work is
        silently dropped by any subclass overriding without calling `super` — fragile base class
        arriving through the pattern's front door. `[TRAP]` — §1.21.7

5.2.127 "An `AFTER_COMMIT` listener runs in its own transaction" → the transactional resources
        may still be active, so data-access code participates in the original transaction and
        its changes are **never committed**. `[TRAP]` — §1.23.9, §3.19.13

5.2.128 "Publishing an event cannot deadlock" → publishing while holding a lock, with a listener
        that takes the same locks in the opposite order, is the textbook in-process deadlock.
        `[TRAP]` — §1.23.10

5.2.129 "Listeners run in declaration order" → order is unspecified unless declared with
        `@Order`, so two listeners that both mutate `BalanceView` race only under load.
        `[TRAP]` — §1.23.18

5.2.130 "`undo()` is the inverse of `execute()`" → not automatically: undoing a settled stake
        cannot just re-credit `CLIENT_CASH_AVAILABLE`, because §11.3's win/void asymmetry sends
        reserved bonus to cash on a win and to bonus on a void. `[TRAP]` — §1.24.11

5.2.131 "A persisted command can store its Java class name" → renaming the class breaks replay
        of every historic command; commands carry the same versioning obligation as events.
        `[TRAP]` — §1.24.12

5.2.132 "Calling `doFilter` twice is harmless" → that, and writing to the response after it
        returns, both produce `IllegalStateException: response already committed`; the handler
        owns both sides of the delegation. `[TRAP]` — §1.25.13, §3.11.8

5.2.133 "A `default` method on the `Visitor` interface is a safe convenience" → a newly added
        type is then silently *unvisited* at runtime instead of breaking the build, which
        destroys the one guarantee visitor had. `[TRAP]` — §1.26.7

5.2.134 "No `ConcurrentModificationException` means no concurrent modification" → its absence
        proves nothing; a racy `HashMap` write can corrupt the table, spin forever in `get`, or
        return a torn read and never throw. `[TRAP]` — §1.27.7

5.2.135 "You can remove from a collection inside a for-each loop" → that is the *single-threaded*
        cause of CME; use `Iterator.remove()`, `Collection.removeIf`, or iterate a copy.
        `[TRAP]` — §1.27.8

5.2.136 "A memento can hold references to the originator's state" → then the caretaker holds a
        view of the *current* state and "restore" is a no-op that looks like it worked.
        `[TRAP]` — §1.28.12

5.2.137 "A null object is a safe default everywhere" → not on a money path: a no-op
        `LedgerWriter` silently discards entries and the imbalance surfaces days later in
        reconciliation. Null object suits optional collaborators, not writers.
        `[TRAP]` — §1.29.4

5.2.138 "A specification is just a predicate" → a *selection* specification running
        `isSatisfiedBy` in memory over 2.4M registered clients is a table scan; selection
        specifications must be translatable to a query. `[TRAP]` — §1.29.11, §2.21.19

5.2.139 "One class can serve as entity and DTO" → then the wire format binds to the schema,
        adding a column changes the public API, and Hyrum's law makes it permanent.
        `[TRAP]` — §1.29.15

5.2.140 "A registry is just a map" → it is global state, so a mutable registry is a
        shared-mutable-state hazard and an invisible dependency. `[TRAP]` — §1.29.16

5.2.141 "Monostate is a tidier singleton" → all-`static` state behind an ordinary constructor is
        the *worst* form of hidden global, because callers cannot tell it is global at all.
        `[TRAP]` — §1.29.19

5.2.142 "Layered architecture's problem is ceremony" → its problem is that the domain ends up
        **depending on persistence** — the entities *are* JPA entities, so the domain cannot
        compile without Hibernate on the classpath. `[TRAP]` — §1.31.8

5.2.143 "DI requires a container" → `new StakeReservationService(new JpaLedger(em), clock)` in a
        test *is* dependency injection; the container is an assembly convenience.
        `[TRAP]` — §1.32.10

5.2.144 "Service locator is untestable and DI is testable" → Fowler's own correction is that
        both are amenable to testing; the real difference is that a constructor signature
        documents the dependency and a locator hides it. `[TRAP]` — §1.32.14

5.2.145 "`java.util.Observable` is the JDK's observer" → it was **deprecated in Java 9** for
        having no thread safety, no event objects and no ordering; naming the deprecation is
        what makes the citation credible. `[VERSION-TRAP]` — §1.33.6

5.2.146 "Every pattern-to-JDK-type mapping is authoritative" → several are community consensus
        rather than a claim the JDK authors made; `Collections.unmodifiableList` is documented
        as an unmodifiable *view*, not as a decorator. `[TRAP]` — §1.33.10

5.2.147 "Strategy is stateless and state is stateful" → a weaker separator worth being able to
        correct: a strategy may hold configuration (a rounding mode, a rate table) and still be
        a strategy. The separator is who chooses the successor. `[TRAP]` — §2.4.5

5.2.148 "Every disambiguation question has a clean answer" → proxy vs decorator is genuinely
        unsettleable when the wrapper is hand-written, stacked *and* controls access; GoF's own
        answer is intent, and intent is not observable in the code. `[TRAP]` — §2.5.3

5.2.149 "Two hierarchies means bridge" → bridge is a claim about intent *at design time*; a
        second hierarchy that appeared incrementally is strategy that grew, whatever the diagram
        now looks like. `[TRAP]` — §2.5.4

5.2.150 "Reciting both definitions answers a disambiguation question" → it reads as recall and
        makes the interviewer do the comparison; lead with the one discriminating question.
        `[TRAP]` `[SAY]` — §2.5.6

5.2.151 "A type implements exactly one pattern" → `JdbcTemplate` is a facade **and** a template
        method, so the right answer to "which pattern is this" is sometimes two, named.
        `[TRAP]` — §2.5.12, §1.33.4

**From §2.6–§2.14 — principles and anti-patterns.**

5.2.152 "Extract-method is applying SRP" → SRP is about who requests the change to the enclosing
        module; a 200-line method with one stakeholder violates the long-function smell, not SRP.
        `[TRAP]` — §2.6.13

5.2.153 "SRP — or GRASP's Pure Fabrication — justifies a `*Helper`/`*Manager` layer" → renaming a
        god object into three helpers that all take the same 12 dependencies moves the violation
        without fixing it; a legitimate fabrication has a cohesive responsibility and a domain
        name. `[TRAP]` — §2.6.19, §2.12.12

5.2.154 "`Arrays.asList` is immutable" → it is **fixed-size, not immutable**: `set(i, v)`
        succeeds and writes through to the backing array, and only `add`/`remove` throw.
        `[TRAP]` — §2.8.15

5.2.155 "LSP means a subtype must not throw" → it may throw anything the base's contract permits
        on the base's documented failure conditions; what it must not do is introduce a failure
        mode callers were never told about. `[TRAP]` — §2.8.22

5.2.156 "ISP means small interfaces" → size is not the criterion: a 12-method interface every
        client calls in full is fine, and a 2-method interface where each client uses one is
        not. `[TRAP]` — §2.9.2

5.2.157 "ISP fragments the implementation" → one class may implement many role interfaces; ISP
        splits the *declared dependency*, not the class, so "but then I have four classes" is a
        misreading. `[TRAP]` — §2.9.10

5.2.158 "`default` methods fixed the fat-interface problem" → a default body is a *behavioural
        guess* on behalf of every implementor: `default boolean isBlocking() { return false; }`
        silently gives every new restriction the wrong answer. `[TRAP]` — §2.9.14

5.2.159 "Least astonishment is a style preference" → it is a design rule with concrete Java
        violations: a `getX()` that mutates, an overload that changes semantics, a constructor
        that starts a thread. `[TRAP]` — §2.11.31

5.2.160 "Information Expert says put the behaviour where the data is" → applied blindly it puts
        persistence and rendering on the entity too; it is bounded by low coupling and by SRP.
        `[TRAP]` — §2.12.4

5.2.161 "Reaching for the familiar technology is pragmatism" → golden hammer: the design's forces
        are never articulated, because the answer preceded the question. `[TRAP]` — §2.14.16

5.2.162 "Many small classes is good design" → ravioli code is what over-applied SRP produces: no
        single file shows the use case, so understanding it means holding twenty files at once.
        `[TRAP]` — §2.14.21

5.2.163 "Moving logic into configuration avoids a deploy" → soft code trades a deployment problem
        for the loss of type checking, tests, review, version history and stack traces.
        `[TRAP]` — §2.14.42

5.2.164 "Copying a reference architecture is a safe default" → cargo cult: `@Transactional` on
        every method, a `Repository` per entity, a DTO per layer — the structure imported without
        its force. `[TRAP]` — §2.14.47

5.2.165 "`context.getBean(Foo.class)` is equivalent to injection" → service locator / ambient
        context hides the dependency from the constructor signature, so the type stops
        documenting what it needs and a missing dependency fails at call time, not at startup.
        `[TRAP]` — §2.14.58

**From §2.15–§2.30 — smells, styles, DDD, CQRS, integration, resilience, cost.**

5.2.166 "A smell is a defect" → it is a *hint to look*; Fowler's own framing is that no set of
        metrics rivals informed human intuition, so a smell list used as a lint config produces
        churn without value. `[TRAP]` — §2.15.30

5.2.167 "Refactoring means improving the code" → Fowler's definition is exact: a change to
        internal structure that does **not** alter observable behaviour. A rewrite is not a
        refactoring. `[TRAP]` — §2.16.25

5.2.168 "Hexagonal, clean and onion are the same thing" → true about the dependency rule, false
        about the artefacts: hexagonal gives ports and adapters and no opinion on use cases,
        clean adds explicit use-case objects and can double the class count. `[TRAP]` — §2.17.8

5.2.169 "We have chosen an architecture" → a style is a topology and a set of constraints; an
        architecture additionally names the components, the data ownership and the
        quality-attribute targets. `[TRAP]` — §2.17.26

5.2.170 "Microservices for scalability" → scalability is available in a monolith by running more
        instances: `ApplicationGateway` scales 12 → 40 without being decomposed.
        `[TRAP]` — §2.17.27

5.2.171 "Serverless has no servers, so no capacity planning" → you still plan concurrency limits,
        downstream connection counts and cold-start budgets, and an 11 s card-PSP p99 does not
        get shorter. `[TRAP]` — §2.17.28

5.2.172 "The style-comparison star ratings are measurements" → they are the authors' calibrated
        judgement published as a comparison aid; quoting "microservices score 5 for elasticity"
        as data is a misuse. `[TRAP]` — §2.18.12

5.2.173 "Package-by-feature lets me use sub-packages freely" → package-private does not nest, so
        `ledger.internal.X` is invisible to `ledger.Y`; sub-packages cost you the enforcement
        that motivated the layout. `[TRAP]` — §2.19.6, §3.20.3

5.2.174 "Package-by-layer is clean separation of concerns" → it separates concerns in the *file
        tree* while making every class globally reachable — the opposite of separation where it
        counts. `[TRAP]` — §2.19.12

5.2.175 "A bounded context is a microservice" → a context is a *model* boundary and a service is
        a *deployment* boundary; one context can be several services, and one service can host
        two contexts badly. `[TRAP]` — §2.20.8

5.2.176 "One bounded context per team" → an oversimplification in both directions: a team can own
        several small contexts, and a large core context can need more than one team.
        `[TRAP]` — §2.20.9

5.2.177 "Strategic design is preamble; the tactical patterns are the substance" → the tactical
        patterns are worthless applied across a wrong boundary. `[TRAP]` — §2.20.25

5.2.178 "Every domain noun is an entity" → most are value objects, and choosing entity by default
        creates identity where none is needed — and with it rows, ids, lifecycles and equality
        bugs. `[TRAP]` — §2.21.20

5.2.179 "A repository is where the queries go" → once it grows
        `findByStatusAndCreatedAtBetweenAndSourceIn(...)` it is a DAO, and the aggregate has
        stopped being the unit of access. `[TRAP]` — §2.21.21

5.2.180 "A domain service is where behaviour spanning entities goes" → true, and a
        `RestrictionDomainService` with 40 methods is a transaction script wearing DDD
        vocabulary. `[TRAP]` — §2.21.22

5.2.181 "A JPA `@Entity` is a DDD entity" → `@Entity` is a persistence mapping and a DDD entity is
        a model concept with invariants; they can be one class only with the public setters
        removed. `[TRAP]` — §2.21.23

5.2.182 "Reference-by-identity is free" → "get the client's name for this ledger entry" becomes
        two loads or an API composition, and the JPA temptation to add `@ManyToOne` is exactly
        how the boundary erodes. `[TRAP]` — §2.22.10

5.2.183 "Foreign keys show me the aggregates" → FKs express *referential* integrity and
        aggregates express *transactional* invariants; every FK treated as containment yields one
        enormous aggregate. `[TRAP]` — §2.22.18

5.2.184 "Eventual consistency between aggregates is a compromise we accepted" → it is the
        decision that makes the system scale, chosen rather than conceded: immediate inside the
        boundary, eventual between. `[TRAP]` — §2.22.19

5.2.185 "CQRS is command-query separation" → same origin word, different scope: CQS is a
        method-level rule about a function either returning a value or having an effect.
        `[TRAP]` — §2.23.2

5.2.186 "A read model can be authoritative if it is fresh enough" → the scenario states it as a
        hard constraint: restrictions may be projected for *display* and never as the input to an
        authorisation. `[TRAP]` — §2.23.15

5.2.187 "Projections are cheap, so add one per screen" → cheap to add and expensive to keep
        correct; each one needs a rebuild procedure, a lag metric and an owner. Count them like
        you count indexes. `[TRAP]` — §2.23.16

5.2.188 "We store events, so we are event-sourced" → if current state is the system of record and
        events are written alongside it, that is an audit table; event sourcing means state is a
        fold over the log. `[TRAP]` — §2.24.1

5.2.189 "Upcasters solve schema evolution" → they cannot add information that was never captured:
        a v1 `StakeReserved` with no bonus/cash split can only be defaulted, and the default is a
        lie about history. `[TRAP]` — §2.24.12

5.2.190 "Crypto-shredding solves erasure on an immutable log" → regulators have not uniformly
        accepted that encrypted personal data with a destroyed key is erased, since encrypted
        personal data is still personal data. It is the usual answer, not a settled one.
        `[TRAP]` — §2.24.15

5.2.191 "A gateway and a BFF are the same edge" → a gateway is one edge for *all* clients handling
        cross-cutting transport concerns; a BFF is one edge *per client type* handling payload
        shape. `[TRAP]` — §2.25.16

5.2.192 "Strangler fig is the safe migration" → only with its preconditions: an interception
        point, per-capability routing, and the ability to run both systems against the same data.
        Without them it is a rewrite with a facade in front. `[TRAP]` — §2.25.20

5.2.193 "Parallel run de-risks the cutover" → it doubles downstream load and is illegal against a
        dependency with side effects; you can parallel-run a *calculation*, never an
        *authorisation*. `[TRAP]` — §2.25.23

5.2.194 "Partition affinity is a correctness mechanism" → it buys in-memory state locality only —
        the database serialises writes through position version columns regardless — and it costs
        you the rebalancing problem when 3 instances become 4. `[TRAP]` — §2.25.27

5.2.195 "Retry a 4xx in case the client was unlucky" → a 400 fails identically forever, a 409 may
        or may not, and a 429 must wait for `Retry-After`. Classification is per status code, not
        per exception type. `[TRAP]` — §2.26.8

5.2.196 "Resilience is about handling failure" → half of it is *steady state*: every accumulation
        — sessions, caches, log files, idempotency keys, outbox rows — needs a reaper, or the
        system dies of success. `[TRAP]` — §2.26.22

5.2.197 "`ThreadLocal` is a clean way to pass request context" → on a pooled thread the value
        outlives the request, and the leak is a long-lived pool carrying one client's tenant id
        into another's request. `[TRAP]` — §2.27.10

5.2.198 "Threads are cheap, so size the pool generously" → a platform thread reserves ~1 MB of
        stack, so 10k of them do not fit alongside a 4 GB heap. `[TRAP]` `[NUM]` — §2.27.15

5.2.199 "Virtual threads retire the thread pool, so bulkheads and rate limits go with it" → they
        do not: unbounded cheap concurrency means unbounded *downstream* concurrency, and the
        600/min identity-vendor cap does not move. `[VERSION-TRAP]` — §2.27.19

5.2.200 "Template method is as testable as strategy" → it is the worst of the behavioural
        patterns for testing: exercising a hook means instantiating a subclass, so the tests
        couple to the inheritance hierarchy. `[TRAP]` — §2.28.8

5.2.201 "I can unit-test my `@Transactional` semantics" → the behaviour does not exist until the
        container wires the proxy, so proxy and AOP semantics need an integration slice, not a
        unit test. `[TRAP]` — §2.28.10

5.2.202 "Mock the vendor SDK to test the adapter" → do not mock types you do not own: the mock
        encodes your *belief* about the vendor, and a green test against a wrong belief is worse
        than no test. `[TRAP]` — §2.28.14

5.2.203 "More mocks means better isolation" → six mocks asserts the implementation's call
        sequence, so refactoring breaks the test while a behaviour change passes it. Mock count
        is a design signal. `[TRAP]` — §2.28.15

**From §3.1–§3.21 — mechanism-level traps. These had no counterpart in the flat guide.**

5.2.204 "A megamorphic site is just one with many receiver types" → the specific signal is a
        **polluted profile**: the profile holds the first ≤2 types with low counts while the
        *total* count is high, which is how C2 records that the receiver-type data overflowed.
        `[TRAP]` — §3.1.10

5.2.205 "Escape analysis stack-allocates the object" → C2 does **scalar replacement**, decomposing
        the object into fields and never allocating it; the HotSpot wiki states explicitly that
        it does not stack-allocate. `[TRAP]` — §3.2.3

5.2.206 "I can prove elimination with `-XX:+PrintEliminateAllocations`" → that and
        `PrintEscapeAnalysis` are `develop`-only flags, absent from a product JVM; you need a
        fastdebug build or an indirect measurement. `[TRAP]` — §3.2.6

5.2.207 "Reading a `static final` field triggers class initialisation" → not for a primitive or
        `String` initialised with a compile-time constant expression: `javac` inlines the value
        and the class may never initialise at all. `[TRAP]` — §3.3.2

5.2.208 "A `<clinit>` cycle deadlocks" → if initialisation is already in progress *on the current
        thread* the request is recursive and completes normally, which is why a cycle proceeds
        and can hand out a half-initialised class. `[TRAP]` — §3.3.5

5.2.209 "A failed class initialisation retries on the next call" → the class enters the
        **erroneous** state permanently and every subsequent use throws `NoClassDefFoundError`;
        `<clinit>` never re-runs. `[TRAP]` — §3.3.7

5.2.210 "DCL without `volatile` works — I tested it" → on x86-64 with TSO the breaking reorder is
        a *compiler* transformation, not a hardware one, so it survives review and testing and
        appears under a different JIT decision in production. `[TRAP]` — §3.4.6

5.2.211 "Making the object's fields `final` fixes DCL" → the final-field freeze helps only if the
        *reference* is safely published; a racy read of the reference is outside the guarantee.
        `[TRAP]` — §3.4.8

5.2.212 "A constructor that completes has frozen its final fields" → not if `this` escaped from
        inside it: registering a listener, starting a thread, or passing `this` to a collaborator
        voids the freeze for every reader. `[TRAP]` — §3.4.10

5.2.213 "Records are automatically safe to publish" → a record's components are `final`, so it is
        safe through any correct publication idiom and **not** safe through a racy non-`volatile`
        field. `[VERSION-TRAP]` — §3.4.12

5.2.214 "An enum singleton round-trips its state" → enum fields are **not** serialized, so a
        mutable field on an enum singleton is silently lost. `[TRAP]` — §3.5.4

5.2.215 "Renaming an enum constant is a refactoring" → the enum's serialized form is its **name**,
        so a rename turns every persisted value into an `IllegalArgumentException` from
        `Enum.valueOf`. `[TRAP]` — §3.5.5

5.2.216 "`readResolve` is a normal method" → it must be named exactly that, may be `private`
        (it is found reflectively), must return `Object`, and a `private readResolve` is **not**
        inherited by subclasses. `[TRAP]` — §3.5.7

5.2.217 "`readResolve` makes a singleton serialization-proof" → only with every non-`transient`
        field also marked `transient`; otherwise a stolen-reference attack extracts the field
        values from the discarded instance. `[TRAP]` — §3.5.8

5.2.218 "A private constructor guarantees one instance" → `getDeclaredConstructor()` plus
        `setAccessible(true)` plus `newInstance()` runs it and a second instance exists. Only
        enums are protected by the JVM against this. `[TRAP]` — §3.5.9

5.2.219 "`clone()` throws nothing I have to handle" → `CloneNotSupportedException` is **checked**,
        so every override either catches an exception it can prove cannot happen or propagates it
        into every caller. `[TRAP]` — §3.6.4

5.2.220 "`ArrayList.clone()` gives me an independent list" → it copies the *array*
        (`Arrays.copyOf`) and resets `modCount`, but the **elements are the same references** —
        it is a shallow copy. `[TRAP]` — §3.6.6

5.2.221 "A proxy behaves like the target for `equals`" → not unless the handler special-cases
        `equals`/`hashCode`/`toString`; forwarded to the target, `proxy.equals(proxy)` can be
        `false` and the proxy is unusable as a map key. `[TRAP]` — §3.7.10

5.2.222 "A dynamic proxy intercepts everything" → `getClass` is `final`, so `proxy.getClass()`
        returns `$Proxy0` and never the target's type; `notify`/`notifyAll`/`wait` are not
        intercepted either. `[TRAP]` — §3.7.11

5.2.223 "Interface order in `newProxyInstance` is cosmetic" → when two proxied interfaces declare
        the same name and parameter signature, order decides which `Method` the handler receives.
        `[TRAP]` — §3.7.12

5.2.224 "Interface `default` methods run their default body through a proxy" → the proxy overrides
        them like any other interface method, so the handler intercepts them and the default body
        runs only if the handler invokes it. `[TRAP]` — §3.7.13

5.2.225 "Spring uses Byte Buddy" → Spring Framework uses its own repackaged CGLIB; Byte Buddy is
        Mockito's engine and Hibernate's bytecode provider. The attribution gets asked.
        `[TRAP]` — §3.8.3

5.2.226 "A CGLIB proxy runs the target's constructor" → `ObjenesisCglibAopProxy` instantiates the
        generated subclass **without calling any constructor**, so field initialisers and
        constructor side effects do not run on the proxy. `[TRAP]` — §3.8.6

5.2.227 "A field read through a proxy works because the getter does" → `proxy.someField` is `null`
        because the field lives on the *target*, not the subclass. Every "my `@Value` field is
        null in one place only" bug is this. `[TRAP]` — §3.8.7

5.2.228 "Advice order is arbitrary" → it is `Ordered`/`@Order`, with
        `HIGHEST_PRECEDENCE = Integer.MIN_VALUE` and `LOWEST_PRECEDENCE = Integer.MAX_VALUE`, and
        where `TransactionInterceptor` sits relative to your advice changes behaviour.
        `[TRAP]` `[API]` — §3.8.17

5.2.229 "`Collections.unmodifiableList` returns an immutable copy" → it is a **view** over the
        original reference, so mutating the original changes what the "unmodifiable" list
        reports. `List.copyOf` is the copy. `[TRAP]` — §3.10.2

5.2.230 "Stream decorator order is a style choice" → buffering outside versus inside a
        decompressor are different performance profiles, and forgetting `close()` on the
        **outermost** wrapper loses buffered output. `[TRAP]` — §3.10.5

5.2.231 "`-XX:AutoBoxCacheMax` widens the `Integer` cache" → it raises only the **upper** bound;
        `-128` is not configurable. `[TRAP]` `[NUM]` — §3.10.7

5.2.232 "`ServiceLoader` validates the providers when I load it" → instantiation is lazy and
        cached per provider, so a broken provider surfaces as a `ServiceConfigurationError`
        mid-iteration rather than at load. `[TRAP]` — §3.10.14

5.2.233 "`FilterChainProxy` applies every matching chain" → it selects the **first** match and
        builds a `VirtualFilterChain` over it, so a broader matcher declared earlier silently
        shadows a narrower one. `[TRAP]` — §3.11.10

5.2.234 "A record's canonical constructor can be made private" → it is `public` if the record is,
        and you may not weaken its access; the compact constructor is where you validate, not
        where you restrict. `[TRAP]` — §3.12.3

5.2.235 "You assign `this.field` in a compact constructor" → that is a compile error; you assign
        the **parameter**, and the compiler emits the field write after your body.
        `[TRAP]` — §3.12.5

5.2.236 "Records are slower because of `invokedynamic`" → the indy indirection is a one-time
        linkage of the method-handle chain, and thereafter it JIT-inlines like handwritten code.
        `[VERSION-TRAP]` — §3.12.8

5.2.237 "Record `equals` is `Objects.equals` on every component" → primitives use `==`, but
        floating point uses `Float.compare`/`Double.compare`, so `NaN` equals `NaN` and `+0.0`
        does not equal `-0.0`. `[TRAP]` — §3.12.9

5.2.238 "Copying an array component in the constructor closes the gap" → it must be copied
        **again in the accessor**, or the caller mutates the record's own array.
        `[TRAP]` — §3.12.14

5.2.239 "A sealed interface's permitted subclasses are unconstrained" → each must be `final`,
        `sealed`, or explicitly `non-sealed`; there is no fourth option. `[TRAP]` — §3.13.2

5.2.240 "`MatchException` replaced `IncompatibleClassChangeError`" → it did not:
        `IncompatibleClassChangeError` remains the error for genuine incompatible class changes,
        including a sealing violation. `[VERSION-TRAP]` — §3.13.13

5.2.241 "The Resilience4j defaults are a safe starting point" → `minimumNumberOfCalls = 100` with
        `slidingWindowSize = 100` is the breaker-that-never-opens on a low-traffic path such as
        the identity-vendor call. `[TRAP]` `[NUM]` — §3.15.16

5.2.242 "An open breaker closes itself after the wait duration" → with
        `automaticTransitionFromOpenToHalfOpenEnabled` off, the move to `HALF_OPEN` happens on
        the **next call attempt**, so a path with no traffic stays open indefinitely.
        `[TRAP]` — §3.15.17

5.2.243 "A `BIGSERIAL` global sequence is gap-free" → it advances on rolled-back transactions, so
        a projection assuming contiguity stalls forever on a gap that will never be filled.
        `[TRAP]` — §3.16.5

5.2.244 "Validate in the aggregate's `apply`" → `apply` only folds and the command handler
        validates; an `apply` that rejects a historically valid event makes the aggregate
        permanently unloadable. `[TRAP]` — §3.16.7

5.2.245 "A snapshot can serialise the domain object" → that welds the store to a class shape, so
        the next refactoring invalidates every snapshot. Snapshots serialise a **versioned DTO**.
        `[TRAP]` — §3.16.11

5.2.246 "Publishing in `@TransactionalEventListener(AFTER_COMMIT)` is the outbox" → the commit
        succeeded and the publish is outside it, so a crash between them loses the event. That is
        the version that looks identical and is broken. `[TRAP]` — §3.17.4

5.2.247 "`SKIP LOCKED` means no relay ever blocks another" → it skips rows locked by *any*
        transaction, so a relay that hangs mid-batch holds its rows until its transaction ends —
        they are not lost, they are stalled. `[TRAP]` — §3.17.6

5.2.248 "The outbox can be made exactly-once" → it cannot: the relay publishes, then marks
        `processed_at`, and a crash between the two republishes. At-least-once plus an idempotent
        consumer is the design, not a shortfall. `[TRAP]` — §3.17.10

5.2.249 "`ORDER BY created_at LIMIT n` preserves order" → with multiple relay instances,
        aggregate A's event 2 can publish before event 1 if they land in different batches on
        different instances. `[TRAP]` — §3.17.13

5.2.250 "Optimistic locking throws `OptimisticLockException`" → the chain is Hibernate's
        `StaleObjectStateException` → JPA's `OptimisticLockException` → Spring's
        `ObjectOptimisticLockingFailureException`, and you catch the one your layer sees.
        `[TRAP]` `[API]` — §3.18.4

5.2.251 "The optimistic-lock failure surfaces at the failing `save()`" → it surfaces at **flush**,
        which for a `@Transactional` method is usually at commit — after the method body
        returned, which is why a `try/catch` around the save catches nothing. `[TRAP]` — §3.18.5

5.2.252 "Catch the optimistic-lock failure and retry in place" → the persistence context is
        poisoned after a flush failure and JPA requires a rollback, so the retry must span
        transactions. `[TRAP]` — §3.18.11

5.2.253 "Round-tripping the version through the client is safe" → if the client omits it, JPA
        treats a `null` version as a new entity and you get a silent lost update.
        `[TRAP]` — §3.18.12

5.2.254 "`setErrorHandler` lets me log listener failures" → `invokeListener` wraps the call in the
        handler **and swallows the exception**, so setting one converts a failure into a log line
        the publisher never sees. `[TRAP]` — §3.19.4

5.2.255 "An async listener sees the caller's context" → the javadoc says it will not participate
        in the caller's thread context — classloader or transaction — unless the `TaskExecutor`
        explicitly supports it. `[TRAP]` — §3.19.5

5.2.256 "An `@EventListener` method may return a value harmlessly" → a non-`void` return
        **publishes the result as a new event** (or each element of a collection), so an
        accidental return type creates an event loop. `[TRAP]` — §3.19.8

5.2.257 "JPMS will enforce our module boundaries" → a Boot fat jar runs on the **unnamed module**
        and gets none of it; JPMS is real enforcement only for a jlink/JPMS-native deployment.
        `[TRAP]` — §3.20.7

5.2.258 "ArchUnit sees the whole graph" → it **creates stubs** for types it did not import,
        carrying the name and called methods but no superclasses or annotations, so a rule about
        an annotation on an unimported type silently passes. `[TRAP]` — §3.20.10

5.2.259 "My microbenchmark shows the indirection is free" → dead-code elimination is the first
        reason: C2 proves the result unused and deletes the call, which has been reported as an
        8–12× overstatement. Consume the result. `[TRAP]` `[NUM]` — §3.21.3

5.2.260 "A hard-coded benchmark input is fine" → constant folding lets C2 compute the answer at
        compile time; inputs must come from non-`final` `@State` fields. `[TRAP]` — §3.21.4

5.2.261 "A loop over an array of strategies measures dispatch" → unrolling and hoisting turn it
        into something else entirely, which is the specific reason hand-rolled dispatch
        benchmarks report that indirection costs nothing. `[TRAP]` — §3.21.5

5.2.262 "Building the strategy list in `@Setup` is neutral" → with one implementation present the
        site stays monomorphic, so the benchmark lies in the *favourable* direction. Populate
        every implementation you claim to measure. `[TRAP]` — §3.21.6

5.2.263 "A benchmark that survives all four JIT hazards is trustworthy" → it is trustworthy about
        *that* call site only; the design question is whether the measured delta is large against
        the operation's real budget — 2.8 ns of dispatch against a 30 ms restriction path is
        noise, and against a 100 ns cache lookup it is not. `[PROVE]` `[NUM]` — §3.21.3–§3.21.6

*(263 leaves)*

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

Leaf refs are leaf-level and were checked against the merged file's actual leaf text; a range
means the diagram genuinely spans those leaves. Where a `must show` disagreed with what the
anchored leaf says, the `must show` was corrected — the leaves are the authority.

| id | leaf ref | type | must show |
|---|---|---|---|
| D-01 | §1.4.1–§1.4.5, §1.4.9–§1.4.10 | svg | The pattern-family map: the purpose × scope axes of §1.4.1, the class-scope patterns of §1.4.2 marked as such, all 23 placed by family (5 + 7 + 11), and two overlays — the patterns §1.4.9 calls dead in modern Java with the feature that killed each, and the ones §1.4.10 says the platform absorbed |
| D-02 | §2.3.2, §2.3.3–§2.3.4, §1.13.1, §1.14.1, §1.15.1, §1.16.3 | table | Adapter / facade / proxy / decorator by interface-vs-target, purpose, stackability and trigger — the §2.3.2 table, with the intent line of each pattern taken verbatim from its own §1.13.1/§1.14.1/§1.15.1/§1.16.3 intent leaf, and §2.3.3's interface-equality question shown as the first split before intent is consulted |
| D-03 | §1.16.4–§1.16.5 | svg | The decorator stack as §1.16.5 wires it, descending call and ascending response, each layer's added behaviour labelled — and the order marked as semantic rather than cosmetic, with §1.16.4's rule (a decorator always delegates; skipping is a bug) annotated on one layer |
| D-04 | §1.10.3–§1.10.8, §3.3.3–§3.3.7, §3.4.1–§3.4.2 | svg | Two threads through all three singleton idioms: §1.10.3's eager static final resolved by the §3.3.3 initialisation lock LC, §1.10.5's DCL with §3.4.1's allocate/construct/publish split and §3.4.2's partially-constructed read marked as the hazard window, and §1.10.8's holder taking LC once. Include §3.3.4's in-progress-by-another-thread wait and §3.3.7's erroneous terminal state |
| D-05 | §3.7.1, §3.7.3, §3.8.6 | svg | Two call paths side by side: caller → generated `$Proxy0` (§3.7.1's `newProxyInstance` signature, §3.7.3's per-loader-per-interface-permutation cache) → `InvocationHandler` → target, against caller → CGLIB subclass instantiated by §3.8.6's Objenesis with **no constructor call** → super method. Mark the no-constructor step as the difference that surprises people |
| D-06 | §3.8.12, §3.8.14, §3.8.19, §4.2.5 | svg | The interceptor chain as §3.8.12's `ReflectiveMethodInvocation` holds it — an index into a list, not a linked list, per §3.8.14 — with the external call traversing every interceptor and §3.8.19's `this.settle(...)` arriving at the raw target with the chain greyed out. §4.2.5's assertion (count 1, not 2) as the caption |
| D-07 | §1.26.3, §3.13.6–§3.13.7 | svg | Double dispatch as §1.26.3 traces it — `node.accept(visitor)` then `visitor.visitX(this)`, two virtual calls giving dispatch on a pair — against §3.13.7's single `invokedynamic` `typeSwitch` bootstrap, with §3.13.6's compile-time exhaustiveness proof shown as the guarantee that replaces the visitor interface |
| D-08 | §1.22.6, §4.4.2, §4.4.4 | svg | The `DocumentVerification` machine of §4.4.2: `AA-600` → `AA-610` → {`AA-611`, `AA-650`, `AA-690`} → `AA-699` → `AA-700` → `AA-710` → {`AA-711`, `AA-799`}, with §4.4.4's two guards (attempt < 3, inside the 14-day window) on the re-upload edge and §1.22.6's illegal-states-unrepresentable framing as the caption |
| D-09 | §1.23.6, §1.23.7, §1.23.10, §1.23.11, §3.19.3 | svg | One publisher and its listener list, with §3.19.3's default (synchronous, publishing thread, inside the publisher's transaction) as the frame, and each of the four failure modes drawn on it: §1.23.6's accumulating latency, §1.23.7's throwing listener rolling the publisher's transaction back, §1.23.10's reentrant registration and lock inversion, §1.23.11's retained reference |
| D-10 | §2.17.3–§2.17.7 | svg | Four panels — §2.17.3 layered, §2.17.4 hexagonal, §2.17.5 clean, §2.17.6 onion — each labelled with the thing its own leaf says it optimises and every dependency arrow drawn, plus §2.17.7's caption naming what is genuinely identical across all four (the dependency direction) so the panels are not read as four different rules |
| D-11 | §2.19.1–§2.19.2, §2.19.4–§2.19.5, §2.19.10 | svg | The same six classes arranged by layer (§2.19.1) and by feature (§2.19.2), with §2.19.4's mechanical argument shown rather than asserted: `public` forced on every class in the first, package-private possible in the second per §2.19.5. Add §2.19.10's build-module tier as the third and strongest column |
| D-12 | §2.22.1–§2.22.2, §2.22.5 | svg | The boundary derived, not drawn: §2.22.2's worked derivation from the `PaymentRun` total invariant, with the enclosed entities inside one transaction and the aggregates referenced by id outside it per §2.22.5, and §2.22.1's definition (the invariants that must hold at the end of every transaction) as the line's label |
| D-13 | §2.23.3–§2.23.5, §2.23.9, §4.12.3 | svg | The three CQRS levels of §2.23.3–§2.23.5 as three stacked bands so the reader sees that level 1 needs no second store, then the write → event → projection → read flow for `InternalPlatforms`' operator queue, with §4.12.3's checkpoint row and §2.23.9's two timestamps marked at the point the lag is actually measured |
| D-14 | §2.24.4–§2.24.5, §2.24.7, §3.16.1–§3.16.2 | svg | The append-only log with §3.16.1's exact column set, §3.16.2's `UNIQUE (aggregate_id, version)` drawn as the concurrency control itself (no separate version column, per §2.24.5), a snapshot at version N per §2.24.7, and the tail replay from N+1 to head |
| D-15 | §2.25.1–§2.25.2, §3.17.2–§3.17.3, §3.17.10 | svg | One transaction enclosing the ledger rows and the §3.17.2 outbox row — §3.17.3's same-transaction insert is the whole correctness argument and must be the visual emphasis — then the poller, the broker, and the consumer's dedup index, with §3.17.10's publish-then-mark gap marked as the point at-least-once becomes unavoidable |
| D-16 | §2.25.4–§2.25.5, §2.25.8 | svg | Saga both ways: §2.25.5's central orchestrator issuing steps and compensations, against the choreographed version where services react to each other's events, running the same `DEP-301 → DEP-400` failure through both — and §2.25.8's compensatable / pivot / retriable classification shaded onto each step, since the pivot is what decides whether compensation is even possible |
| D-17 | §3.15.1–§3.15.5, §3.15.8–§3.15.11, §4.6.2 | svg | The breaker as §3.15.1's `CircuitBreakerStateMachine` really is: §3.15.3's **six** `State` constants (not three), state as an object per §3.15.2, §3.15.4's legal transitions, and §3.15.5's `compareAndSet` on the transition. Alongside it both window implementations — §3.15.10's O(1) `FixedSizeSlidingWindowMetrics` head-move-and-subtract and §3.15.11's per-second partial aggregates — with §4.6.2's thresholds annotated |
| D-18 | §2.26.14, §4.8.2, §4.8.7 | svg | Three semaphore compartments sized from §4.8.2's real dependency figures (identity vendor 600/min, watchlist 200/min, PSP 500/sec) drawing on one instance, one saturated and the others unaffected per §2.26.14 — and §4.8.7's second constraint drawn as a memory bar, because on `DocumentVerification` the bulkhead is bounded by 2–6 MB buffers before it is bounded by concurrency |
| D-19 | §2.25.19–§2.25.20 | svg | The facade in front of the legacy path with traffic shifting per capability across four stages, and §2.25.20's three preconditions drawn as gates the migration must pass — interception point, per-capability routing, both systems against the same data — since that leaf says the preconditions are where it actually fails |
| D-20 | §3.1.5, §3.1.9, §3.1.13–§3.1.15 | svg | Monomorphic → bimorphic → megamorphic for a strategy interface: §3.1.5's patched call site, §3.1.9's width-2 limit as the reason bimorphic is the last inlined shape, §3.1.13's fall-back to a vtable/itable load with no inlining, §3.1.14's measured spread on the axis as real numbers, and §3.1.15's deopt arrow back from a widened site |
| D-21 | §2.13.2–§2.13.5 | svg | REP, CCP and CRP at the vertices with §2.13.5's tension made explicit: REP and CCP pull components larger, CRP pulls them smaller, and each edge labelled with what you give up moving toward that vertex |
| D-22 | §2.13.22–§2.13.32 | svg | The nine kinds ordered by strength: §2.13.23's five static kinds weakest-first (CoN, CoT, CoM, CoP, CoA) then §2.13.29's dynamic kinds (CoE, CoTi, CoV, CoI), which that leaf says are uniformly stronger — so the static/dynamic split *is* the strength axis. **Correction to the original wish-list:** §2.13 enumerates strength and the static/dynamic split but carries no locality-or-degree leaf, so the locality axis is diagram-only and must be labelled as Page-Jones' third property rather than cited to a leaf |
| D-23 | §2.2.2–§2.2.3 | svg | The creational procedure as a flowchart following §2.2's ordered steps exactly: §2.2.2's per-deployment-or-per-request split first (it is the one that eliminates the most options), then §2.2.3's name / subtype / cached instance / fail-before-allocation test, then field count and optionality. Terminals are the six candidate answers §2.2.1 says the question has |
| D-24 | §2.4.2, §2.4.4, §2.4.17 | table | Strategy / state / template / command / visitor by binding time and self-transition — §2.4.2's table, whose two load-bearing columns those are — with §2.4.4's single separator (chosen from outside, or chooses its own successor) called out, and the table's row order following §2.4.17's eight-step decision flow so the table can be read as a procedure |
| D-25 | §2.18.1–§2.18.2, §2.18.12 | table | One row per §2.17 style against §2.18.1's declared columns (deployability, testability, performance, scalability, simplicity, cost, and the rest), each cell taken from that style's own §2.18.x leaf — and §2.18.12's caveat printed in the figure itself, so the ratings are labelled as the authors' calibrated judgement and not as measurements |
| D-26 | §1.33.2–§1.33.3, §1.33.5 | table | §1.33.2's full 23-row census — pattern, classification, JDK site, Spring site, QuizStakes site — with §1.33.3's three genuinely-absent cells marked **absent** rather than left blank, and §1.33.5's multi-pattern types flagged so a reader does not treat one row as one pattern per type |
| D-27 | §2.15.1–§2.15.29, §2.16 | table | Smell → smallest safe move → the protecting test, one row per smell. **Correction:** §2.15 has no single table leaf — it enumerates one smell per leaf (§2.15.2 onward, the count stated in §2.15.1) and the moves live in §2.16, so this table is assembled across the two sections. Include §2.15.26's 1e→2e rename column, since interview material still quotes the 1e names, and mark §2.15.27's two dropped and §2.15.28's four added smells |
| D-28 | §2.26.5, §4.7.2–§4.7.3 | svg | Attempt-arrival distribution for 500 clients after one PSP blip: plain exponential backoff as three sharp spikes against full jitter as a flat spread, same axes and same total attempt count, with §4.7.3's arithmetic printed alongside and §2.26.5's name for the failure — the retry wave — as the title |
| D-29 | §4.1.5 | svg | The resolution walk for `StakeReservationService` with the creation stack shown at each depth, and the containment check firing on the third frame *before* the recursive call — the ordering §4.1.5 has to prove, since it is what makes the failure a `CircularDependencyException` with a path rather than a `StackOverflowError` |
| D-30 | §4.14.1, §4.14.3 | svg | The three modules as a dependency graph: `ledger-domain` with zero outbound edges (§4.14.1's build file is the artefact), `ledger-application` → domain, `ledger-adapters` → both, and §4.14.3's deleted-module test annotated as the arrow that must not exist |
| D-31 | §2.26.1, §2.26.4–§2.26.21 | table | Failure → pattern → mechanism → the parameter that is always wrong → the trap, in §2.26.1's declared reading order, one row per pattern. **Correction:** §2.26 has no table leaf; the catalogue is one pattern per leaf, so this table is assembled from §2.26.4 onward. Add §2.26.3's Nygard stability-anti-pattern names as a companion column, since each pattern exists against one of them |
| D-32 | §2.30.2–§2.30.9 | table | §2.30.9's cost table itself — pattern family × files, allocations, dispatch, stack frames, error-surface shift, configuration and monitoring surface — with each column's meaning taken from its own leaf (§2.30.2 files, §2.30.3 allocations, §2.30.4 dispatch, §2.30.8 configuration and monitoring) |
| D-33 | §2.5.2–§2.5.4 | table | The confusable-pairs table of §2.5.2, whose last column — the one question that separates the pair — is the whole deliverable. **New entry:** lane B flagged this 29-row table and the original wish-list had no manifest slot for it. §2.5.3's proxy-vs-decorator and §2.5.4's bridge-vs-strategy rows must be marked *unsettleable from the code* rather than given an answer, because both leaves say intent is not observable |

*(33 manifest entries)*

---

---

## Overall leaf totals

Counted from this file by script, not carried over from the six drafting lanes: every
`*(N leaves)*` marker was re-derived from the leaf lines beneath it, and the part sums below are
the sums of those markers. Any future edit must re-run that check rather than trust this table.

| Part | Sections | Leaves | Share |
|---|---|---|---|
| PART 1 — BASICS | 33 | 476 | 23.6% |
| PART 2 — INTERMEDIATE | 30 | 676 | 33.4% |
| PART 3 — UNDER THE HOOD | 22 | 338 | 16.7% |
| PART 4 — BUILD IT | 15 | 143 | 7.1% |
| PART 5 — INTERVIEW & RETENTION | 3 | 388 | 19.2% |
| **Total** | **103** | **2021** | **100%** |

### Tag counts

Occurrences in the leaf region (a leaf may carry more than one tag).

| Tag | Count |
|---|---|
| `[TRAP]` | 470 |
| `[API]` | 277 |
| `[PROVE]` | 259 |
| `[SOURCE]` | 223 |
| `[X-REF]` | 189 |
| `[DECIDE]` | 166 |
| `[BUILD]` | 154 |
| `[NUM]` | 153 |
| `[SAY]` | 107 |
| `[TABLE]` | 82 |
| `[VERSION-TRAP]` | 68 |
| `[SMELL]` | 68 |
| `[RESEARCH]` | 57 |
| `[INCIDENT]` | 40 |
| `[DIAG]` | 28 |
| `[FLOW]` | 19 |

Total tag occurrences: **2360** across 2021 leaves (**1.17** per leaf).

### `[X-REF]` targets

Every pointer is to a sibling guide; there are no self-referential pointers. A leaf tagged
`[X-REF nn]` states the mechanism in one paragraph here and sends the reader to guide `nn` for the
full treatment.

| Guide | Pointers |
|---|---|
| `03` | 3 |
| `04` | 4 |
| `05` | 29 |
| `06` | 18 |
| `07` | 11 |
| `08` | 15 |
| `09` | 1 |
| `10` | 2 |
| `12` | 11 |
| `13` | 5 |
| `14` | 15 |
| `15` | 2 |
| `16` | 27 |
| `17` | 2 |
| `18` | 1 |
| `19` | 1 |
| `20` | 6 |
| `22` | 13 |
| `25` | 16 |
| `26` | 12 |
---

## Sources consulted

### Front matter and PART 1 §1.1–§1.19 — the pattern frame, creational and structural patterns
| Source (URL) | What it contributed |
|---|---|
| https://openjdk.org/jeps/491 (via search summary) | JEP 491 "Synchronize Virtual Threads without Pinning", JDK 24: monitors tracked per virtual thread rather than per carrier, so blocking in `synchronized` no longer pins; native/foreign frames still pin. Fed §1.12.10 and delta 4. |
| https://inside.java/2024/11/21/newscast-80/ | Confirmed JDK 24 as the release and "almost all" pinning cases removed; the residual native-frame case. |
| https://docs.spring.io/spring-framework/reference/core/aop/proxying.html | Primary source for §1.15.10 and §1.15.11–12: JDK proxy when an interface exists, CGLIB otherwise; `final`/`private`/`static`/field non-interception; effectively-private package-private superclass methods; the self-invocation quote ("invoked against the `this` reference, and not the proxy"); the ranked fixes including `AopContext.currentProxy()` + `exposeProxy=true` described as highly discouraged; `@EnableAspectJAutoProxy(proxyTargetClass = true)`, `@EnableTransactionManagement(proxyTargetClass = true)`. |
| https://docs.spring.io/spring-boot/docs/current/api/org/springframework/boot/autoconfigure/aop/AopAutoConfiguration.CglibAutoProxyConfiguration.html (via search summary) | The exact `@ConditionalOnProperty(prefix="spring.aop", name="proxy-target-class", havingValue="true", matchIfMissing=true)` annotation and the Boot-2.0-onward CGLIB default. Fed §1.15.13 and delta 8. |
| https://nipafx.dev/java-visitor-pattern-pointless/ | Expert deep-dive supporting delta 2 and §1.4.9: sealed types + pattern switch supply the exhaustiveness that visitor's double dispatch manufactures. |
| https://www.javacodegeeks.com/2026/04/sealed-classes-and-exhaustive-pattern-matching-how-they-change-api-design-not-just-syntax.html | Current (2026) framing of exhaustiveness as an API-design change rather than syntax; used for delta 2's wording. |
| https://www.vojtechruzicka.com/java-cloning-problems/ and https://programming.guide/java/clone-and-cloneable.html | Effective Java Item 13's four defects, restated and cross-checked: no `clone` on the marker interface with `Object.clone()` protected; construction without a constructor including `private`/`final` fields; shallow by default; incompatible with `final` fields referencing mutables. Fed §1.11.3–§1.11.7. |
| https://codeql.github.com/codeql-query-help/java/java-missing-clone-method/ | Independent confirmation that "implements `Cloneable` without a public `clone`" is a checkable defect class, i.e. defect 1 is real and tooled. |
| https://shipilev.net/jvm/anatomy-quarks/18-scalar-replacement/ | Primary-grade expert source for §1.12.7–§1.12.8: HotSpot does scalar replacement of aggregates, not true stack allocation; the named defeaters are control-flow merges before the access, non-inlined instance calls, and identity-dependent code. |
| https://cr.openjdk.org/~cslucas/escape-analysis/EscapeAnalysis.html | OpenJDK-hosted background on EA/SRA status; supported the claim that C2's EA is flow-insensitive and that Graal uses partial EA. |
| https://dzone.com/articles/java-integer-cache-why-integervalueof127-integerva and https://nataliiadziubenko.com/2024/10/13/Java-integer-caching-how-and-why.html | `IntegerCache.low = -128` / `high = 127`, autoboxing routing through `valueOf`, `-XX:AutoBoxCacheMax` mapping to `java.lang.Integer.IntegerCache.high` with a `Math.max(..., 127)` clamp, and that the constructor never caches. Fed §1.19.5–§1.19.8. |
| https://bugs.openjdk.org/browse/JDK-6968657 | Primary source (OpenJDK issue) establishing that the **low** bound is deliberately not configurable — the basis for the asymmetry leaf §1.19.10. |
| https://blog.ploeh.dk/2010/02/03/ServiceLocatorisanAnti-Pattern/ and https://deviq.com/design-patterns/service-locator-pattern/ | Service locator as anti-pattern: dependencies hidden from the constructor signature, static access, failure deferred from startup to request time. Fed delta 3. |
| https://www.oreilly.com/library/view/fundamentals-of-software/9781098175504/ | Confirmed *Fundamentals of Software Architecture* 2nd edition = **2025** (1st edition February 2020) for the baseline table. |
| https://pragprog.com/titles/mnee2/release-it-second-edition/ | Confirmed *Release It!* 2e = **2018**. |
| https://www.amazon.com/Software-Architecture-Trade-Off-Distributed-Architectures/dp/1492086894 | Confirmed *Software Architecture: The Hard Parts* = **2021** (Ford, Richards, Sadalage, Dehghani). |
| https://www.geeksforgeeks.org/system-design/top-design-patterns-interview-questions/ and https://github.com/aershov24/design-patterns-interview-questions | Interview-surface completeness probe, mined only for concept names. Contributed the "not in GoF but asked anyway" list (§1.4.12) and the also-known-as aliases (§1.4.14). Nothing was taken as authority. |

### PART 1 §1.20–§1.33 and PART 2 §2.1–§2.5 — behavioural patterns, the non-GoF vocabulary, selection and disambiguation
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

### PART 2 §2.6–§2.14 — SOLID in depth, the other principles, GRASP, component principles, the anti-pattern catalogue
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

### PART 2 §2.15–§2.30 — smells, refactoring, architecture styles, DDD, CQRS, integration, resilience, enforcement
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

### PART 3 §3.1–§3.22 — internals and source walks
| Source (URL) | What it contributed |
|---|---|
| https://docs.oracle.com/javase/specs/jvms/se21/html/jvms-5.html | JVMS §5.5 initialization: the 12-step procedure verbatim, "the initialization lock is the `Class` object for C", the erroneous→`NoClassDefFoundError` and `<clinit>`→`ExceptionInInitializerError` paths. §3.3 in full. |
| https://wiki.openjdk.org/spaces/HotSpot/pages/13729943/TypeProfile | `TypeProfileWidth` default **2**, range 0–8, "number of receiver types to record in call/cast profile"; `ReceiverTypeData` rows; the polluted-profile mechanism (first N types with low counts, high total). §3.1.7–3.1.10. |
| https://shipilev.net/blog/2015/black-magic-method-dispatch/ | Measured dispatch figures across C1/C2 and receiver counts; itable vs vtable cost; interface dispatch being worse than abstract-class dispatch when not inlined (136.2 vs 120.5 ns/op at C1, bias 0.5). §3.1.3–3.1.4. |
| https://dzone.com/articles/too-fast-too-megamorphic-what and http://insightfullogic.com/2014/May/12/fast-and-megamorphic-what-influences-method-invoca/ | Monomorphic 2.816 / bimorphic 3.258 / megamorphic 4.896 ns/op; C2 supports bimorphic inline caches and treats ≥3 receiver types as megamorphic; megamorphic sites are not inlined. §3.1.9, §3.1.14. |
| https://mail.openjdk.org/pipermail/hotspot-compiler-dev/2020-February/036955.html | Confirmation that PIC gates inlining/escape-analysis/type-directed optimisation, and that C2 implements no polymorphic inline cache beyond bimorphic. §3.1.11–3.1.13. |
| https://shipilev.net/jvm/anatomy-quarks/17-trust-nonstatic-final-fields/ | `-XX:+TrustFinalNonStaticFields` (experimental, off by default); the default trust set (`java/lang/invoke`, `sun/invoke`, hidden classes, boxed classes, `String`, `Atomic*FieldUpdater`, record classes); 4.202→1.901 ns/op; the reason it is not default. §3.14 in full. |
| https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/lang/reflect/Proxy.html | `newProxyInstance`/`getProxyClass` signatures, `getProxyClass` deprecation, the four module/package placement rules, `$Proxy` name reservation, `equals`/`hashCode`/`toString` dispatched with `java.lang.Object` as declaring class, duplicate-interface foremost rule, `isProxyClass`, `getInvocationHandler`, per-loader caching. §3.7. |
| https://www.baeldung.com/jdk-com-sun-proxy | `ProxyGenerator` moving from `sun.misc` to `java.lang.reflect` in JDK 9; generated class extends `Proxy` and is `final`; delegation shape. §3.7.5, §3.7.16. |
| https://docs.spring.io/spring-framework/docs/current/javadoc-api/org/springframework/aop/framework/DefaultAopProxyFactory.html and https://docs.spring.io/spring-framework/reference/core/aop/proxying.html | The `createAopProxy` branch (interface / proxy class / **lambda class** → `JdkDynamicAopProxy`, else `ObjenesisCglibAopProxy`), `optimize`/`proxyTargetClass`/`hasNoUserSuppliedProxyInterfaces` conditions, CGLIB repackaged into `spring-core`. §3.8.1–3.8.6. |
| https://github.com/spring-projects/spring-framework/issues/17468 | Historical context for the JDK-proxy handling in `DefaultAopProxyFactory` (SPR-12870) — confirms the branch has changed shape across versions, which is why §3.8.4 states it against 6.2. |
| https://houbb.github.io/2023/03/07/exception-springboot-proxy | The real `BeanNotOfRequiredTypeException` text ("expected to be of type … but was actually of type `com.sun.proxy.$Proxy`") used verbatim in §3.8.11. |
| https://raw.githubusercontent.com/resilience4j/resilience4j/master/resilience4j-circuitbreaker/src/main/java/io/github/resilience4j/circuitbreaker/internal/CircuitBreakerStateMachine.java | Field list including `AtomicReference<CircuitBreakerState> stateReference` **and** `ReentrantLock lock`; the six state names; all eight `transitionTo*` methods; `compareAndSet`/`getAndUpdate`; `CircuitBreakerMetrics.forClosed(...)` in `ClosedState`. §3.15.1–3.15.6. |
| https://raw.githubusercontent.com/resilience4j/resilience4j/master/resilience4j-circuitbreaker/src/main/java/io/github/resilience4j/circuitbreaker/internal/CircuitBreakerMetrics.java | `FixedSizeSlidingWindowMetrics` / `LockFixedSizeSlidingWindowMetrics` / `SlidingTimeWindowMetrics` / `LockFreeSlidingTimeWindowMetrics`; `private final Metrics metrics`; `private int minimumNumberOfCalls`; the `-1.0f` sentinel and `Result.BELOW_MINIMUM_CALLS_THRESHOLD`. §3.15.8, §3.15.15. |
| https://resilience4j.readme.io/docs/circuitbreaker and https://medium.com/@storozhuk.b.m/circuit-breaker-implementation-in-resilience4j-992af908c413 | Config property names and defaults; the count-based circular array of N measurements; **and** the 0.x-era `RingBitSet`/ring-bit-buffer description that §3.15.9 marks as version-stale. |
| https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/lang/runtime/SwitchBootstraps.html | `typeSwitch(MethodHandles.Lookup, String, MethodType, Object...)`; label types `String`/`Integer`/`Class`/`EnumDesc`; index-returning semantics; `enumSwitch` sibling. §3.13.7–3.13.9. |
| https://bugs.openjdk.org/browse/JDK-8294285 | **The release boundary.** JEP 433, delivered in **JDK 20**: "An exhaustive switch … over an `enum` class now throws `MatchException` rather than `IncompatibleClassChangeError` if no switch label applies at run time." Settles §3.13.12. |
| https://openjdk.org/jeps/441 and https://openjdk.org/projects/amber/guides/exhaustiveness-guide | JEP 441 finalising pattern switch in 21; `MatchException` thrown when a separately-recompiled sealed hierarchy makes a compile-time-exhaustive switch non-exhaustive at run time; the guidance on evolving sealed APIs. §3.13.11, §3.13.14–3.13.15. |
| https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/lang/runtime/ObjectMethods.html | `bootstrap(Lookup, String, TypeDescriptor, Class, String, MethodHandle...)`; `methodName` restricted to `"equals"`/`"hashCode"`/`"toString"`; "for either invokedynamic call sites or dynamic constant pool entries". §3.12.6–3.12.7. |
| https://docs.oracle.com/javase/tutorial/reflect/special/enumTrouble.html and https://notes.highlysuspect.agency/blog/enum_reflection/ | `Constructor.newInstance`'s `(clazz.getModifiers() & Modifier.ENUM) != 0` check and the exact message `"Cannot reflectively create enum objects"`; the `ConstructorAccessor` bypass that makes "reflection-proof" a qualified claim. §3.5.10–3.5.11. |
| `apache/tomcat` `ApplicationFilterChain.java` fetched at **four** refs — `main`, `11.0.x`, `10.1.x`, `9.0.x` (raw.githubusercontent.com) | The full field list (`filters = new ApplicationFilterConfig[0]`, `pos = 0`, `n = 0`, `servlet`, `servletSupportsAsync`, `dispatcherWrapsSameObject`, `public static final int INCREMENT = 10`, the `lastServicedRequest`/`lastServicedResponse` `ThreadLocal`s); the complete method list at each ref; and **the `internalDoFilter` release boundary** — present in 9.0.x and 10.1.x with the `Globals.IS_SECURITY_ENABLED` + `AccessController.doPrivileged` wrapper, absent in 11.0.x and `main`. §3.11.1–3.11.6. |
| https://docs.spring.io/spring-framework/docs/current/javadoc-api/org/springframework/web/filter/OncePerRequestFilter.html | `ALREADY_FILTERED_SUFFIX`, `getAlreadyFilteredAttributeName()`, `shouldNotFilter`, `shouldNotFilterAsyncDispatch()`/`shouldNotFilterErrorDispatch()` both defaulting to `true`, and the skip decision order. §3.11.12. |
| https://docs.spring.io/spring-framework/docs/current/javadoc-api/org/springframework/context/event/SimpleApplicationEventMulticaster.html | `setTaskExecutor`/`setErrorHandler`/`multicastEvent`/`invokeListener`; the default being caller-thread and "equivalent to `SyncTaskExecutor`"; the warning that async execution does not participate in the caller's class loader or **transaction context**; `TransactionalApplicationListener` always running in the publishing thread; `AbstractApplicationEventMulticaster`'s `ListenerRetriever` cache. §3.19.2–3.19.6. |
| https://docs.spring.io/spring-framework/docs/current/javadoc-api/org/springframework/transaction/event/TransactionalEventListener.html | Attributes `phase` (default `AFTER_COMMIT`), `fallbackExecution` (default `false`), `id`, `classes`/`value`, `condition`; "the event is discarded" with no transaction; and the exact warning that data access in an `AFTER_COMMIT` listener participates in the original transaction but **is not committed**. §3.19.9, §3.19.12–3.19.13. |
| https://github.com/TNG/ArchUnit/blob/main/archunit/src/main/java/com/tngtech/archunit/core/importer/ClassFileImporter.java and https://www.archunit.org/userguide/html/000_Index.html | `ClassFileImporter` reading **bytecode** into a `JavaClasses` model; `ArchRuleDefinition` as the fluent entry; `check()` vs `evaluate()`→`EvaluationResult`; stub creation for un-imported classes; `layeredArchitecture()`/`onionArchitecture()`/`slices()`; `freeze()` and the `ViolationStore`. §3.20.8–3.20.13. |
| https://aws.amazon.com/message/5467D2 | The DynamoDB 20 Sep 2015 postmortem: simultaneous partition-membership re-requests against the metadata service, GSI-enlarged requests, cascade into EC2/SQS, ~3 hours, manual recovery. §3.22.1. |
| https://aws.amazon.com/builders-library/timeouts-retries-and-backoff-with-jitter and https://aws.amazon.com/blogs/architecture/exponential-backoff-and-jitter/ | Retry amplification across hops; "backoff alone preserves synchronisation"; jitter as the fix; retry budgets. §3.22.2. |
| https://aws.amazon.com/builders-library/avoiding-fallback-in-distributed-systems (via https://lumigo.io/blog/amazon-builders-library-in-focus-3-avoiding-fallback-in-distributed-systems/) | Fallback paths as untested code exercised only during incidents; proactive redundancy as the alternative. §3.22.12. |
| https://slack.engineering/slacks-outage-on-january-4th-2021/ | The 10:14–15:10 ET window; health-check failures at the load-balancing tier; load-balancer **panic mode** as a deliberate fail-open; provisioning slowed by the unhealthy network. §3.22.3. |
| https://about.roblox.com/newsroom/2022/01/roblox-return-to-service-10-28-10-31-2021 | The 73-hour outage; Consul streaming under high read/write load; the BoltDB free-page pathology; single Consul cluster for multiple workloads; **monitoring dependent on Consul**. §3.22.4. |
| https://redis.io/blog/how-to-tame-the-thundering-herd-problem/ and https://redisson.pro/glossary/thundering-herd-problem.html | Cache-stampede mechanism and the four mitigations (single-flight/coalescing, TTL jitter, probabilistic early recomputation, stale-while-revalidate). §3.22.5. |
| https://raw.githubusercontent.com/openjdk/jdk/master/src/hotspot/share/opto/c2_globals.hpp | Verbatim flag declarations: `product(bool, DoEscapeAnalysis, true, "Perform escape analysis")`, `product(bool, EliminateAllocations, true, …)`, `product(bool, EliminateLocks, true, "Coarsen locks when possible")`, `product(intx, EliminateAllocationArraySizeLimit, 64, …)`, and — the correction — `PrintEscapeAnalysis`/`PrintEliminateAllocations` being **`develop`**, not `product`. §3.2.2–3.2.6. |
| https://raw.githubusercontent.com/openjdk/jdk/master/src/hotspot/share/runtime/globals.hpp | `product(bool, UseInlineCaches, true, "Use Inline Caches for virtual calls ")`. Also the negative result that `TypeProfileWidth` is **not** declared here. §3.1.6, §3.1.8. |
| https://wiki.openjdk.org/display/HotSpot/EscapeAnalysis | The three escape states quoted verbatim, and "C2 does NOT replace a heap allocation with a stack allocation for non globally escaping objects" — the primary-source basis for §3.2.3's `[TRAP]`. |
| https://raw.githubusercontent.com/resilience4j/resilience4j/master/resilience4j-circuitbreaker/src/main/java/io/github/resilience4j/circuitbreaker/CircuitBreakerConfig.java | **The authoritative default table.** All eleven `DEFAULT_*` constants with literal values, and `public enum SlidingWindowType { TIME_BASED, COUNT_BASED }`. §3.15.12. |
| https://raw.githubusercontent.com/resilience4j/resilience4j/master/resilience4j-circuitbreaker/src/main/java/io/github/resilience4j/circuitbreaker/CircuitBreaker.java | The `State` enum verbatim with `(order, allowPublish)` per constant; the 33-constant `StateTransition` enum; and the confirmation that **`RingBitSet` appears nowhere**. §3.15.3–3.15.4, §3.15.9. |
| https://raw.githubusercontent.com/spring-projects/spring-boot/v3.5.0/…/autoconfigure/aop/AopAutoConfiguration.java | Pinned at the **v3.5.0 tag**: `@ConditionalOnBooleanProperty(name = "spring.aop.proxy-target-class", matchIfMissing = true)` + `@EnableAspectJAutoProxy(proxyTargetClass = true)`, the `havingValue = false` JDK-proxy branch, and `spring.aop.auto` with `matchIfMissing = true`. §3.8.8–3.8.9. |
| https://github.com/rucek/jmh-demo and https://www.oracle.com/technical-resources/articles/java/architect-benchmarking.html | The three canonical JMH hazards — dead-code elimination, constant folding, loop optimisation — with `Blackhole`, non-`final` `@State` fields and "no manual loops" as the defences; the 8–12× dead-code figure. §3.21.3–3.21.5. |

**Fetches attempted and their status.** All `WebFetch` calls returned content. Two returned
*incomplete* content and are flagged in the notes block below: the OpenJDK exhaustiveness guide (did
not cover the enum/ICCE history, so JDK-8294285 was fetched to settle it) and the
`TransactionalEventListener` javadoc summary (returned only three `TransactionPhase` constants,
omitting `BEFORE_COMMIT`). Two returned useful **negative** results that changed leaves: the OpenJDK
EscapeAnalysis wiki names no flags at all (so the flag declarations were taken from `c2_globals.hpp`
instead), and `runtime/globals.hpp` does not declare `TypeProfileWidth` (so §3.1.8 now says the
declaring file is unconfirmed rather than implying one). `WebSearch` was not exhausted; **24** distinct
queries and fetches were run for this lane against the brief's minimum of 6–10, of which 8 were the
verification round described in the notes block.

### PART 4, PART 5 and the diagram manifest
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

---

## Gaps vs the current guide

The work order for the write pass.

### Front matter and PART 1 §1.1–§1.19 — the pattern frame, creational and structural patterns
| Syllabus leaf | In `src/topics/24-…` | Verdict |
|---|---|---|
| §1.1.1 (Alexander 1977/1979 origin) | absent | missing |
| §1.1.2 (GoF 1994 bibliographic fact) | absent | missing |
| §1.1.3 (what patterns replaced) | absent | missing |
| §1.1.5–1.1.7 (force-first, scoring sentence, variation→substitution) | lines 8–30, § 1 and § 10 | present, well covered |
| §1.1.12 (*AntiPatterns* 1998) | absent | missing |
| §1.1.13 (Norvig critique) | absent | missing |
| §1.2.1 (the 13 GoF template fields) | absent — the guide gives 4 of them (lines 20–26) | shallow |
| §1.2.8–1.2.9 (participants, collaborations as named fields) | absent | missing |
| §1.2.12 (GoF's three-known-uses admission rule) | absent | missing |
| §1.3.1–1.3.14 (whole taxonomy: idiom/principle/style/anti-pattern/smell/refactoring/framework, PoEAA catalogue) | absent as a section; terms used without definition throughout | missing |
| §1.4.1–1.4.8 (classification axes, the 23-name census, the 5+7+11 arithmetic) | absent | missing |
| §1.4.12–1.4.14 (non-GoF patterns asked anyway; false friends; aliases) | absent | missing |
| §1.5.3–1.5.5 (rule of three with the wrong-seam arithmetic) | line 42–45, one paragraph, no arithmetic | shallow |
| §1.5.7–1.5.10 (dead-seam detection, `Impl` smell, speculative generality) | absent | missing |
| §1.6.1–1.6.8 (static factory: five capabilities, JDK naming conventions) | lines 56–59, three capabilities in one sentence | shallow |
| §1.6.9 (`of` vs `copyOf`) | absent | missing |
| §1.6.11–1.6.14 (no seam, `[DECIDE]`, testability, mutable-cache trap) | absent | missing |
| §1.7.2 (factory-method participants by name) | absent | missing |
| §1.7.5–1.7.6 (JDK/Spring factory-method sites by name) | absent | missing |
| §1.7.8–1.7.11 (inheritance cost, decision procedure, testability) | line 90–94 covers the DI-redundancy case only | shallow |
| §1.8.4–1.8.5 (family shape and the forged-callback incident) | lines 67–82 give a family example, no failure framing | shallow |
| §1.8.6–1.8.8 (JDK/Spring sites, expression-problem cost) | absent | missing |
| §1.9.2 (2^6 = 64 arithmetic) | line 99, "9 parameters is unreadable", no arithmetic | shallow |
| §1.9.5 (participants incl. absent `Director`) | absent | missing |
| §1.9.6–1.9.9 (`build()` as single validation point, setter-validation trap, collection copy, reuse) | lines 100–136 — all four present | present, well covered |
| §1.9.12 (the ≥5-fields / any-optional threshold as a number) | line 123, "≥5 fields or optional" | present |
| §1.9.15 (Lombok/Immutables cost, domain-module dependency) | absent | missing |
| §1.9.16 (test-data-builder) | absent | missing |
| §1.10.4 (JVMS §5.5 init lock cited as spec) | line 158 cites "JLS 12.4.2" | shallow — and the citation should be checked (see notes) |
| §1.10.11–1.10.12 (`readResolve` by exact signature; reflection guard) | lines 185–187, one sentence, no method name | shallow |
| §1.10.16 (singleton bean with mutable fields) | absent | missing |
| §1.10.17 (one per classloader, not per cluster) | absent | missing |
| §1.10.18 (ArchUnit rule as the protecting test) | absent | missing |
| §1.11.3–1.11.7 (the four `Cloneable` defects, separated and named) | lines 200–203, three of four in one sentence; defect 4 (`final` fields) absent | shallow |
| §1.11.13 (arrays have no immutable view — accessor copy) | absent | missing |
| §1.11.14 (do not implement copy at all if immutable) | absent | missing |
| §1.12.4 (the win inequality) | line 225–226, stated as prose | shallow |
| §1.12.7–1.12.10 (escape analysis, EA defeaters, live-set cost, JEP 444/491) | absent | missing |
| §1.12.11 (pool sized to a bottleneck as the one correct case) | line 235–237 as a trap, not as the positive case | shallow |
| §1.12.15 (exhaustion/leak/reset tests) | absent | missing |
| §1.13.2 (adapter participants), §1.13.4 (object vs class adapter) | absent | missing |
| §1.13.6 (adapter = ACL at module scale) | line 852, one clause inside § 7.6 | shallow |
| §1.13.7–1.13.8 (JDK/Spring adapter sites) | absent | missing |
| §1.13.12 (leaked adaptee exception) | absent | missing |
| §1.14.1–1.14.11 (facade as its own section) | only a table row at line 257 | shallow |
| §1.14.10 (GoF facade vs facade layer vs `RemoteFacade`) | absent | missing |
| §1.15.3 (GoF's four proxy kinds) | absent | missing |
| §1.15.10 (the exhaustive CGLIB non-interception list incl. package-private-in-superclass) | line 300 lists four of five | shallow |
| §1.15.13 (Boot's CGLIB default; "needs an interface" is stale) | lines 299–312 state the *opposite* implication | **wrong as written — correct in the write pass** |
| §1.15.14 (proxy dispatch cost on the 30 ms path) | absent | missing |
| §1.16.5–1.16.6 (decorator ordering semantics) | line 272–282 shows a stack, says nothing about order | missing |
| §1.16.10 (identity/`equals` breakage) | absent | missing |
| §1.16.11 (wide-interface forwarding cost, no delegation keyword) | absent | missing |
| §1.17.5–1.17.7 (transparency vs safety as a named trade-off) | lines 329–332 — present and good | present, well covered |
| §1.17.9–1.17.10 (unbounded recursion, parent pointers) | absent | missing |
| §1.18.4 (the M×N vs M+N arithmetic with numbers) | lines 335–343, stated without numbers | shallow |
| §1.18.7–1.18.8 (JDBC/SLF4J/AWT bridge sites) | absent | missing |
| §1.18.10 (both axes must have shown a second member) | absent | missing |
| §1.19.5–1.19.8 (`IntegerCache` constants, `AutoBoxCacheMax`, deprecated constructors) | lines 352–356 give the range and the `==` effect only | shallow |
| §1.19.10 (`Long`/`Short` have no tunable) | absent | missing |
| §1.19.14 (unbounded interning pool) | absent | missing |
| Checklist items 998–1021 (all of PART 1 lane A's scope) | mapped | every one maps to at least one leaf above |

### PART 1 §1.20–§1.33 and PART 2 §2.1–§2.5 — behavioural patterns, the non-GoF vocabulary, selection and disambiguation
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

### PART 2 §2.6–§2.14 — SOLID in depth, the other principles, GRASP, component principles, the anti-pattern catalogue
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

### PART 2 §2.15–§2.30 — smells, refactoring, architecture styles, DDD, CQRS, integration, resilience, enforcement
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

### PART 3 §3.1–§3.22 — internals and source walks
| Syllabus leaf | In `src/topics/24-…` | Verdict |
|---|---|---|
| §3.1.1–3.1.18 (dispatch, vtable/itable, inline-cache states, `TypeProfileWidth`, the 30 ms conclusion) | absent — the guide's only dispatch content is § 4.7's "Java dispatches on the runtime type of the receiver only" (line 522) | missing |
| §3.2.1–3.2.14 (escape analysis, scalar replacement, the flag declarations, the `develop`-only print flags, the four failure conditions) | line 227, one clause: "a modern JVM allocates in the TLAB by bumping a pointer" | shallow |
| §3.3.1–3.3.12 (JVMS §5.5's 12 steps, the LC lock, the `static final` exemption) | line 157, one clause: "class initialisation … is guarded by a per-class initialisation lock (JLS 12.4.2)" — and it cites the **JLS**, not JVMS §5.5 | shallow |
| §3.3.13–3.3.14 (holder idiom mechanism, JIT-folded init check) | lines 146–161 | shallow |
| §3.4.1–3.4.8 (the three-step publication, the release/acquire pair, why DCL *appears* to work) | lines 177–183 state the hazard correctly but not why it passes tests | shallow |
| §3.4.9–3.4.12 (JLS §17.5 freeze, `this`-escape, the five safe-publication idioms, records and the freeze) | absent | missing |
| §3.5.1–3.5.4 (`ObjectOutputStream.writeEnum`/`readEnum`, name-based resolution, `Enum`'s sealed serialization hooks) | line 185, one clause: "The JVM special-cases enums against both" | shallow |
| §3.5.6–3.5.8 (`readResolve` mechanics, the non-inheritance of a private `readResolve`, the stolen-reference attack and `transient`) | absent | missing |
| §3.5.10–3.5.11 (the `Modifier.ENUM` check, the exact message, the `ConstructorAccessor` bypass) | absent | missing |
| §3.6.1–3.6.7 (`clone` as `native`, empty `Cloneable`, `ArrayList.clone`'s `Arrays.copyOf` + `modCount = 0`) | lines 200–203 name the three defects but walk no source | shallow |
| §3.6.9–3.6.11 (`final`-field incompatibility, arrays as the sole compelling use, copy constructor/factory taking an interface) | absent | missing |
| §3.7.1–3.7.16 (all of JDK proxy internals) | line 299, one table row: "`Proxy.newProxyInstance` generates a class implementing the *interfaces*" | shallow |
| §3.7.9–3.7.13 (`Object`-method routing, the `HashMap`-key trap, `getClass` not intercepted, default methods, `invokeDefault`) | absent | missing |
| §3.8.1–3.8.11 (CGLIB repackaging, the `DefaultAopProxyFactory` branch, Objenesis, Boot's `proxy-target-class=true` default pinned at 3.5.0, the field-`null` trap) | line 300, one table row | shallow |
| §3.8.12–3.8.16 (`ReflectiveMethodInvocation`, `currentInterceptorIndex`, `proceed()`, `TransactionInterceptor`, advice ordering constants) | absent | missing |
| §3.8.19–3.8.22 (self-invocation mechanism, the full silent-failure list, `exposeProxy`, self-injection, AspectJ weaving) | lines 303–308 state the trap and name the fixes without the mechanism | shallow |
| §3.9.1–3.9.20 (Spring's own pattern implementations, source-walked) | absent — the guide names `@Bean` (line 88) and the `Map<String, Strategy>` idiom (lines 376–389) only | missing |
| §3.10.1–3.10.5, §3.10.10–3.10.20 (JDK decorators, `AbstractList`/`modCount`, `Comparator` combinators, `ServiceLoader`, `Stream`'s `Sink`, `EnumSet` representation choice) | line 552 mentions `modCount` and fail-fast in one sentence; the rest absent | missing |
| §3.10.6–3.10.9 (`IntegerCache` source, `AutoBoxCacheMax`, the per-type cache table, `StringTable`) | lines 353–356 name the caches and the `==` consequence but not the source, the flag, or `Float`/`Double` having none | shallow |
| §3.11.1–3.11.14 (all of filter-chain internals, incl. the `internalDoFilter` release boundary) | lines 509–512, four lines on the servlet filter chain as chain-of-responsibility | shallow |
| §3.12.1–3.12.14 (record codegen, `ObjectMethods.bootstrap`, compact-constructor assignment semantics, `RecordComponent`, the array-component gap) | lines 122–125 and 213–216 state shallow immutability and the compact constructor; the generated shape and the indy bootstrap absent | shallow |
| §3.13.1–3.13.16 (`permits`, `PermittedSubclasses`, class-load enforcement, `typeSwitch`, `MatchException` vs `ICCE` and the release boundary) | lines 531–545 present sealed+switch as visitor's replacement with no mechanism and no exception discussion | shallow |
| §3.14.1–3.14.10 (trusted finals, the flag, the measured delta, write barriers, records in the trust set) | absent | missing |
| §3.15.1–3.15.19 (all of Resilience4j internals, incl. the authoritative default table) | line 930, one table row describing the breaker's states in prose | shallow |
| §3.16.1–3.16.16 (event-store shape, `(aggregate_id, version)` as the OCC, the replay loop, snapshot arithmetic, upcasting chains) | lines 872–885 name replay, snapshotting, upcasters and GDPR without the table, the constraint, or a number | shallow |
| §3.17.1–3.17.16 (all of outbox internals: `SKIP LOCKED`, CDC, ordering, dedup, the relay-bottleneck incident, retention) | line 482 defers entirely to `14-messaging-queues.md`; line 934 covers idempotency keys | missing |
| §3.18.1–3.18.12 (`@Version`, the generated SQL, the exception chain, flush timing, `OPTIMISTIC_FORCE_INCREMENT`, the retry policy) | lines 841–842, one clause: "Optimistic locking with a `@Version` on the root protects the whole invariant set with one check" | shallow |
| §3.19.1–3.19.16 (multicaster internals, all four phases, `TransactionSynchronization`, `fallbackExecution`, the leak, the CME) | lines 464–486 name all four failure modes and `AFTER_COMMIT` correctly, with no mechanism | shallow |
| §3.20.1–3.20.14 (package-private as the only free enforcement, JPMS, ArchUnit's importer/model/freeze, `jdeps`, build-module boundaries) | lines 799–808 make the package-private argument well; line 786 mentions ArchUnit in passing; JPMS, `freeze`, `jdeps` absent | shallow |
| §3.21.1–3.21.12 (JMH on the indirection, the four hazards, `PrintInlining`, async-profiler, the honest conclusion) | line 750, one clause: "indirection must be paid for by a variation that exists" — asserted, never measured | missing |
| §3.22.1–3.22.14 (documented postmortems) | absent — the guide's failure content is design-smell reasoning (§ 6) with no cited incident | missing |

### PART 4, PART 5 and the diagram manifest
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

---

## Footer

| Field | Value |
|---|---|
| Syllabus | `src/syllabus/24-design-patterns-architecture.md` |
| Source guide | `src/topics/24-design-patterns-architecture.md` (1,063 lines, 10 sections, 66-item checklist) |
| Sections | 103 (§1.1–§1.33, §2.1–§2.30, §3.1–§3.22, §4.1–§4.15, §5.1–§5.3) |
| Leaves | 2021 |
| Tag occurrences | 2360 |
| `[RESEARCH]` leaves | 57 — re-verify each against its cited source before writing |
| Diagram manifest | 33 entries, `D-01`–`D-33`, all anchored to leaf level |
| Target baseline | Java 21 LTS, Spring Framework 6.2 / Boot 3.5.x, Hibernate ORM 6.6, Resilience4j 2.x, ArchUnit 1.3+ |
| Written | 2026-09-05 |
| Next stage | `prompt-builder` → `src/metadata/prompts/24-design-patterns-architecture-prompt.md` |

**This file is a work order, not a citable source.** The write pass re-verifies every
`[RESEARCH]` leaf and every version-dependent constant against a primary source and flags
divergence inline rather than conforming to what is written here. The authority order is
official docs and specification text > observed behaviour of the installed runtime > the
implementation's own source > secondary writeups.
