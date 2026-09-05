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

### Sources consulted — lane A

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

### Gaps vs the current guide — lane A

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

### Notes for the orchestrator — lane A

**Leaf counts per section, with the arithmetic.**

Conceptual frame: §1.1 = 13, §1.2 = 13, §1.3 = 14, §1.4 = 15, §1.5 = 14 → 13+13+14+15+14 = **69**.

Creational: §1.6 = 14, §1.7 = 12, §1.8 = 12, §1.9 = 16, §1.10 = 18, §1.11 = 15, §1.12 = 15 →
14+12+12+16+18+15+15 = **102**.

Structural: §1.13 = 12, §1.14 = 11, §1.15 = 15, §1.16 = 13, §1.17 = 12, §1.18 = 11, §1.19 = 15 →
12+11+15+13+12+11+15 = **89**.

**Lane total: 69 + 102 + 89 = 260 leaves** across 19 sections (target 250, +4.0%, inside ±15%).
Front matter is not leaf-counted. No section is under 8 or over 25. Every `*(N leaves)*` marker was
counted on disk with `grep -c` per section range, not estimated.

**Tag counts for the lane**, counted on disk over the §1.1–§1.19 body only (front matter and these
trailing blocks excluded; a leaf may carry more than one tag):
`[API]` 42, `[TRAP]` 32, `[X-REF nn]` 32, `[DECIDE]` 25, `[SOURCE]` 24, `[PROVE]` 23, `[NUM]` 21,
`[VERSION-TRAP]` 14, `[SAY]` 13, `[TABLE]` 11, `[BUILD]` 9, `[INCIDENT]` 5, `[RESEARCH]` 4,
`[SMELL]` 4, `[FLOW]` 1, `[DIAG]` 0.

The 32 `[X-REF nn]` markers break down as: 16 → 13, 25 → 4, 06 → 4, 05 → 4, 07 → 3, and one each
to 22, 10, 08, 03. Guide 16 dominating is a consequence of the brief's "testability consequence"
obligation on every pattern section — one marker per pattern.

`[DIAG]` is unused in lane A by design — a decompiled proxy class, an ArchUnit failure report and a
generated SQL line all belong to PART 3 and PART 4. If the orchestrator wants `[DIAG]` represented in
PART 1, the natural host is §1.15 (a decompiled `$Proxy0`), but it duplicates §3.7 and I left it
there.

**Things I could not verify, named, with the constant and the source that would settle it.**

1. **`Long.valueOf` / `Short.valueOf` have no tunable cache bound** (§1.19.10). I confirmed from
   JDK-6968657 that the `Integer` cache's **low** bound is deliberately not configurable and that
   `AutoBoxCacheMax` applies to `Integer`, but I did not fetch `Long.java` / `Short.java` to prove
   no equivalent property exists. Tagged `[RESEARCH]`. Settled by reading `LongCache` and
   `ShortCache` in the JDK 21 `java.lang` sources.
2. **JEP 491's exact shipping release and residual pinning cases** (§1.12.10). Search results
   consistently say JDK 24 and "native code / foreign functions still pin", and I read the JEP
   summary, but I did not fetch openjdk.org/jeps/491 in full. Tagged `[RESEARCH]`. Settled by the
   JEP text itself plus the JDK 24 release notes.
3. **Scalar-replacement defeaters as an exhaustive list** (§1.12.8). Shipilev's quark names
   control-flow merges, non-inlined instance calls and identity-dependent code, and explicitly does
   *not* discuss `-XX:+DoEscapeAnalysis`, `-XX:+EliminateAllocations` or
   `EliminateAllocationArraySizeLimit`. I therefore did **not** state any flag or numeric limit.
   Tagged `[RESEARCH]`. Settled by `c2_globals.hpp` in the HotSpot sources if the write pass wants
   the flag names and defaults.
4. **The class-initialisation-lock citation.** The current guide (line 158) cites **JLS 12.4.2**; my
   §1.10.4 cites **JVMS §5.5**. Both describe the same mechanism from different specs (JLS 12.4.2 is
   the language-level detailed initialisation procedure; JVMS 5.5 is the JVM-level one with the
   init lock). This is not a contradiction, but the write pass and §3.3 must pick one primary
   citation and use it consistently across §1.10, §1.3.3 and §3.3, or the reader will think one is
   wrong. My recommendation: cite **JVMS §5.5** for the lock and **JLS §12.4.2** for the
   "initialised on first active use" rule.
5. **`spring.aop.proxy-target-class` in Spring Boot 3.5.x specifically.** The
   `matchIfMissing = true` condition is documented on the Boot 2.1 Javadoc page I found and is
   widely reported as unchanged through 3.x, but I did not read the 3.5.x source of
   `AopAutoConfiguration`. §1.15.13 is tagged `[VERSION-TRAP]` `[API]` `[SOURCE]` and the write pass
   must quote the 3.5.x class. Settled by
   `spring-boot-autoconfigure/src/main/java/org/springframework/boot/autoconfigure/aop/AopAutoConfiguration.java`
   at the 3.5.x tag.

**One correction the orchestrator should route to whoever owns the write pass.** Lines 293–312 of
`src/topics/24-design-patterns-architecture.md` imply that a JDK dynamic proxy is what Spring
reaches for and that CGLIB is the fallback. That is true of plain Spring Framework and **false of
Spring Boot**, where CGLIB is the default. §1.15.13 exists to fix it, and the guide's current
wording is the exact stale claim delta 8 targets.

**Judged out of scope, and where I sent it.** The JMM barrier semantics behind `volatile` (§1.10.6–7)
→ `[X-REF 05]` with the mechanism stated in one paragraph. Inline-cache degradation and the measured
cost of a virtual call (§1.5.11, §1.15.14) → `[X-REF 06]` for mechanism and §3.1 / §3.21 for the
numbers, with `[X-REF 25]` for the JMH harness. Collector live-set accounting (§1.12.9) →
`[X-REF 06]`. Connection-pool sizing arithmetic (§1.12.13) → `[X-REF 10]`. `Integer` cache as a
language-substrate fact (§1.19.6) → `[X-REF 03]`, kept here as the flyweight instance. Cluster-wide
singleton / leader election (§1.10.17) → `[X-REF 22]`. Every one of these still has a leaf here, per
the brief's rule that a bible does not send the reader away empty-handed.

**Cross-references I emitted into sections I do not own**, so the orchestrator can check they exist:
§1.20 (strategy), §1.21 (template method), §1.26 (visitor/expression problem), §1.27 (iterator),
§1.29 (non-GoF vocabulary), §1.30 (SOLID), §1.32 (DI/IoC), §1.33 (the census table), §2.3
(structural disambiguation), §2.5 (confusable pairs), §2.8 (LSP), §2.10 (DIP), §2.11 (other
principles / fragile base class), §2.14 (anti-patterns), §2.15 (smells), §2.16 (refactorings), §2.17
(architecture styles), §2.25 (integration patterns / ACL), §2.26 (resilience), §2.28 (testability),
§2.29 (enforcement/ArchUnit), §3.1 (dispatch), §3.2 (escape analysis), §3.3 (class init), §3.4
(volatile/DCL), §3.5 (enum singleton/`readResolve`), §3.6 (`Cloneable` source walk), §3.7 (JDK proxy
internals), §3.8 (CGLIB/self-invocation), §3.13 (sealed types), §3.14 (immutability at JIT level),
§3.21 (measuring design decisions), §4.3 (`ServiceLoader` plugin registry).
