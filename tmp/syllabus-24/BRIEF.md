# Shared brief — syllabus pass for topic 24 (Design Patterns & Application Architecture)

You are one of six concurrent writers producing **one lane** of
`src/syllabus/24-design-patterns-architecture.md`. You write ONLY your own file under
`tmp/syllabus-24/`. The orchestrator concatenates the lanes and owns the overall totals table.
You cannot see the other writers, so this brief carries the full section inventory: use it to
cross-reference sections you do not own (`see §3.8`) without writing them.

Project root: `/Users/rajat.chikkodikar/Desktop/My-files/rough/`.

## What a syllabus is

A pure, exhaustive, **leaf-level enumeration** of everything the bible on this topic must cover.
Naming the concept is the deliverable; explaining it is a later pass's job. A leaf is one numbered
line (`2.8.14 …`), one to four lines long, naming a concept, an identifier, a number, a decision or
a claim — plus its tags. No prose paragraphs, no code fences, no explanations.

Granularity rule — **leaf level, and the leaves are named**:

- Every pattern appears with its GoF name AND the concrete JDK/Spring type that implements it
  (`Collections.unmodifiableList` as decorator, not "the decorator pattern in the JDK").
- Every constant, threshold and default appears with identifier and value
  (`IntegerCache.high = 127`, `spring.aop.proxy-target-class=true`).
- Every method/annotation/flag worth knowing appears by exact name
  (`Proxy.newProxyInstance`, `@TransactionalEventListener(phase = AFTER_COMMIT)`, `readResolve`).
- Every algorithm/mechanism appears by name (double dispatch, double-checked locking,
  class-initialisation lock, inline-cache degradation to megamorphic).
- Every misconception is a leaf tagged `[TRAP]`.

## Non-negotiable format

### Leaf lines

```
## §1.9 Builder — staged construction and the validation boundary

1.9.1 The problem statement: a constructor with 9 parameters of which 6 are optional produces
      2^6 telescoping overloads, and any two same-typed adjacent parameters are silently
      swappable at the call site. `[PROVE]`
1.9.2 `StakeReservation.Builder` — the nested-static-class form, `Builder` returning `this` for
      chaining, `build()` as the single validation point. `[API]`
...

*(14 leaves)*
```

Rules:
- Section heading is `## §N.M <title>`, exactly one `##` per section, in the order this brief gives.
- Leaf numbers are `N.M.K`, sequential from 1, no gaps, no re-use.
- Continuation lines are indented to align under the leaf text.
- Every section ends with an italic leaf count `*(N leaves)*` on its own line, and the count must
  be the true number of leaf lines in that section. Count them; do not estimate. A previous pass in
  this project shipped five wrong self-reported counts and every one was caught on disk.
- Blank line between leaves is optional; be consistent within a section.

### Tag legend (use these tags and no others)

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

Do not invent tags. If a leaf needs something no tag covers, use the closest and say why in your
lane's own notes block.

## Target version baseline (state versions; every version-dependent leaf carries a tag)

**Java 21 LTS** as the normative language level, with **JDK 22–25** deltas marked
`[VERSION-TRAP]`. **Spring Framework 6.2 / Spring Boot 3.5.x**. Hibernate ORM 6.6.
Resilience4j 2.x. ArchUnit 1.3+. GoF (1994), Fowler *Refactoring* 2e (2018),
Evans *DDD* (2003), Vernon *IDDD* (2013), Richards & Ford *Software Architecture: The Hard Parts* /
*Fundamentals of Software Architecture* 2e, Martin *Clean Architecture* (2017),
Cockburn's ports-and-adapters, Nygard *Release It!* 2e.

## The example domain

**Every example, service name, entity, status code, heap size, instance count, rate and budget
comes from the QuizStakes domain in `src/scenario/scenario.md`** (read-only — read it, never edit
it). The surfaces this topic keeps returning to:

`ClientRestrictions` — 4 GB heap, 8 instances, extreme request rate, trivial objects, synchronous on
every money path inside a **30 ms p99** budget. The strategy/rule-engine and megamorphic-dispatch
example.

`FundsLedger` — 12 GB heap, 3 instances, partition-affine by client id, **230 writes/sec sustained,
13,600/sec peak**, **19.8M ledger entries/day at ~180 bytes/row**. The aggregate-boundary,
optimistic-locking, event-sourcing and outbox example.

`DocumentVerification` — 8 GB heap, 6 instances, 2–6 MB document buffers, 24k uploads/day → 68 GB/day.
The state-machine, object-pool and adapter-to-third-party example.

`ApplicationGateway` — 2 GB heap, scaling 12 → 40 instances, terminates client TLS, strips the client
token. The chain-of-responsibility (filter chain), decorator, facade and BFF example.

`BankDeposits` — 6 GB heap, 2 instances, one daily 40k-record statement file (500k at month end) at
06:00, idle 23 hours. The template-method/batch-pipeline and anti-corruption-layer example.

`BankWithdrawal` — 6 GB heap, 2 instances, owns `PaymentRun` (1.8k records, 4 files/day),
operator-gated, drain-before-terminate. The command, saga and idempotency example.

`InternalPlatforms` — 4 GB heap, 3 instances, session-affine, 30–90 minute operator sessions, 40
operators on shift (90 at peak). The mediator, memento and CQRS-read-model example.

Constraining figures: **2.4M registered clients**, **14k concurrent sessions (55k peak)**, **95k card
deposits/day at 40/sec**, **2.8M stake reservations/day at 1,200/sec with 3,400/sec settlement
bursts**, a **30 ms restriction budget**, an **80 ms balance-read budget**, a **150 ms
stake-reservation budget**, a hard **500 ms self-exclusion budget**, and a card-PSP p99 of **11 s**
on authorise.

Never `Dog extends Animal`, never `Shape`/`Circle`/`Square`, never `Foo`, never `myapp`, never
`thread1`. The pattern literature's canonical toy examples are banned: if the concept is
"a duck that quacks", it is `PaymentMethod` with `CardDeposit`/`BankTransfer` instead.

## Scope boundary — what this topic owns and what it points at

Topic 24 owns **intra-service design**: patterns, principles, anti-patterns, smells, refactoring,
and the architecture of one deployable unit. Cross-reference rather than re-teach, with
`[X-REF nn]`, and state the mechanism in one paragraph before pointing:

- `05` — Java memory model, `volatile`, safe publication, executors (24 owns DCL and the holder
  idiom *as pattern idioms*, and states the JMM rule they depend on).
- `06` — JIT, inline caches, escape analysis, class loading (24 owns the *cost of indirection* and
  cites the mechanism).
- `07` — Spring container, bean lifecycle, AOP proxy model (24 owns the pattern reading of them).
- `08` — JPA/Hibernate mechanics (24 owns repository/aggregate/`@Version` as design).
- `12` — REST/API contracts. `13` — security. `14` — messaging, outbox, saga transport.
  `15` — caching. `16` — tests and test doubles. `20` — observability.
- `22` — system design as the **composition layer**: CAP, partitioning, cross-service topology,
  capacity. 24 stops at the service boundary; 22 starts there.
- `25` — Java performance measurement (JMH harness mechanics).

Concepts parked in a sibling still get a leaf here, tagged `[X-REF nn]`. A bible does not send the
reader away empty-handed.

## Research is mandatory before you enumerate

Run **6–10 distinct `WebSearch` queries for your lane**, varying the angle, then `WebFetch` the
sources worth reading in full. Angles: canonical reference (GoF/spec/javadoc), primary source
(actual implementation source, JEPs, release notes), expert deep-dive, curriculum (book tables of
contents, course syllabi), interview surface ("<topic> interview questions senior/staff"), failure
modes ("<topic> pitfalls / production incident / postmortem"), version delta, adversarial ("what
most people get wrong about <topic>"), completeness probe ("complete guide to <topic>" — mined
purely for concept names you have not listed yet).

Rules:
- Primary sources outrank blogs. A blog is a pointer to a primary source, not the authority.
- Research exists to **discover leaves you would not have thought of**. When a source names a
  concept absent from your list, add the leaf even if it looks minor. Pruning is not this pass's job.
- Do not copy prose. Extract the concept name, the identifier, the number.
- **Verify anything version-dependent against a current source.** If you cannot confirm a constant,
  the leaf still goes in — tagged `[RESEARCH]` — and the constant is named as unconfirmed in your
  lane's notes block. Never invent a citation, a URL, or a number.
- If `WebSearch` is exhausted or a fetch fails, say so in your lane's sources block. Silence is the
  one unacceptable outcome.

## Completeness discipline before you write

1. Read `src/topics/24-design-patterns-architecture.md` in full (1063 lines). **Every concept
   already there is a syllabus leaf. Nothing already covered may be dropped**, including every
   `**Trap:**` marker and every table row.
2. Read that file's `## Atomic concept checklist` (66 items, lines 996–1063). Every item in your
   lane's scope maps to at least one leaf.
3. Read `src/topics/00-index.md` for declared scope and the sibling guides.
4. Sweep for the classes of thing shallow pattern guides systematically miss, and confirm each is
   present in your lane or genuinely inapplicable:
   - the "why does this exist at all" origin, and what the pattern *replaced*
   - one master comparison table per family, with the disambiguating question stated
   - the **cost** of the pattern (allocation, indirection, dispatch, one more file to read)
   - the **when not to** case, named explicitly — a pattern catalogue without rejection criteria
     is how over-engineering gets taught
   - the concrete JDK/Spring implementation, by type name
   - the testability consequence
   - the version delta (records, sealed types, pattern matching, virtual threads have all made
     specific GoF patterns obsolete or reshaped them)
   - the failure mode in production, not just the design smell
5. Diff your list against every source you fetched: "does this name anything my leaves do not?"
   Any table of contents, cheat sheet or interview list you found is a checklist to run against —
   that is the whole reason to fetch it.

## What you output

One file, exactly at the path your lane brief gives, containing **only your lane's sections**, in
order, plus these three trailing blocks:

```
### Sources consulted — lane <X>

| Source (URL) | What it contributed |
|---|---|

### Gaps vs the current guide — lane <X>

| Syllabus leaf | In `src/topics/24-…` | Verdict |
|---|---|---|
| §2.8.14 | absent | missing |
| §1.9.3 | line 104, one clause | shallow |

### Notes for the orchestrator — lane <X>

- leaf count per section and the lane total (state the arithmetic)
- tag counts for the lane
- anything you could not verify, named, with the constant and the source that would settle it
- anything you judged out of this topic's scope, and where you sent it
```

Do NOT write: the document title, the target-version table, the scope-boundary section, the example
domain section, the tag legend, the diagram manifest, the overall totals table, or a footer. Lane A
owns the front matter; lane F owns the manifest; the orchestrator owns the totals. Writing them
twice creates a merge conflict.

## Sizing

Aim for the leaf target in your lane brief, ±15%. A section under 8 leaves is almost certainly
under-enumerated for this topic; a section over 25 wants splitting into the sub-sections the
inventory already names. Do not pad — a leaf that restates its neighbour is worse than no leaf.

---

# The full section inventory (all six lanes)

Cross-reference freely into sections you do not own. Do not write them.

## PART 1 — BASICS (lanes A, B)

Lane A:
- §1.1 Why patterns exist — Alexander, GoF 1994, what a pattern is a solution *to*
- §1.2 The pattern form: name, intent, problem, forces, structure, participants, collaborations, consequences, implementation, known uses, related patterns
- §1.3 Pattern vs idiom vs principle vs architectural style vs anti-pattern vs refactoring
- §1.4 The GoF classification: creational/structural/behavioural × class/object scope, and the full 23-pattern census
- §1.5 The variation-axis model, the rule of three, and premature abstraction as the default failure
- §1.6 Static factory methods
- §1.7 Factory method
- §1.8 Abstract factory
- §1.9 Builder
- §1.10 Singleton
- §1.11 Prototype and copy semantics
- §1.12 Object pool
- §1.13 Adapter
- §1.14 Facade
- §1.15 Proxy
- §1.16 Decorator
- §1.17 Composite
- §1.18 Bridge
- §1.19 Flyweight

Lane B:
- §1.20 Strategy
- §1.21 Template method
- §1.22 State
- §1.23 Observer
- §1.24 Command
- §1.25 Chain of responsibility
- §1.26 Visitor and double dispatch
- §1.27 Iterator
- §1.28 Mediator, memento, interpreter
- §1.29 The non-GoF vocabulary: null object, specification, servant, registry, value object, DTO, assembler, marker, module, monostate, RAII-equivalent (try-with-resources)
- §1.30 SOLID at vocabulary level — the five, stated as mechanisms
- §1.31 Layered architecture as the baseline every service starts from
- §1.32 Dependency injection and inversion of control as patterns, independent of Spring
- §1.33 The pattern census: where each of the 23 appears in the JDK, Spring, and QuizStakes

## PART 2 — INTERMEDIATE (lanes B, C, D)

Lane B (tail of its file):
- §2.1 The master pattern-selection table: force → pattern → seam location → cost
- §2.2 Creational decision procedure
- §2.3 Structural intent disambiguation — same interface? different intent?
- §2.4 Behavioural disambiguation — strategy vs state vs template vs command vs visitor
- §2.5 The confusable pairs, each with the one question that separates them

Lane C:
- §2.6 SRP in depth — axes of change, actors, coupled releases as the cost
- §2.7 OCP in depth — the seam, and who pays when the interface owner must change
- §2.8 LSP in depth — the contract rules (preconditions, postconditions, invariants, history), and the violations that compile
- §2.9 ISP in depth — role interfaces, and what `default` methods softened
- §2.10 DIP in depth — interface ownership, the "which module deletes to compile" test
- §2.11 The other principles: Law of Demeter, Tell-Don't-Ask, command-query separation, composition over inheritance, fragile base class, DRY/YAGNI/KISS as trade-offs, separation of concerns, Hollywood principle, principle of least astonishment, Postel's law, Hyrum's law
- §2.12 GRASP — all nine responsibility-assignment patterns
- §2.13 Package/component principles: REP, CCP, CRP, ADP, SDP, SAP; coupling and cohesion taxonomies; connascence (all nine kinds, static and dynamic, with strength/degree/locality)
- §2.14 The anti-pattern catalogue, each with its failure mechanism, not just its name

Lane D:
- §2.15 The code-smell catalogue (Fowler 2e, all of them), each mapped to its smallest safe move
- §2.16 The refactoring catalogue: the moves that produce patterns, and the moves that remove them
- §2.17 Architecture styles: layered, hexagonal, clean, onion, vertical slice, modular monolith, microservices, SOA, event-driven, pipeline, microkernel/plugin, space-based, serverless, actor
- §2.18 Architecture style comparison against quality attributes (the fitness table)
- §2.19 Package structure: by-layer vs by-feature vs by-component, and what the compiler can police
- §2.20 DDD strategic design: subdomains, bounded context, ubiquitous language, context map, and all the context-relationship patterns
- §2.21 DDD tactical patterns
- §2.22 Aggregate design — the invariant boundary and the design rules
- §2.23 CQRS
- §2.24 Event sourcing
- §2.25 Integration and decomposition patterns: outbox, saga (orchestration vs choreography), API composition, BFF, gateway, anti-corruption layer, strangler fig, branch-by-abstraction, sidecar/ambassador/adapter, shared-nothing
- §2.26 Resilience patterns, indexed by the failure they were invented for
- §2.27 Concurrency patterns: producer-consumer, thread pool, reactor, proactor, half-sync/half-async, active object, monitor object, immutable object, thread-specific storage, guarded suspension, balking, leader-follower, disruptor, scoped-value/structured-concurrency reshaping
- §2.28 The testability consequence of each pattern, and the test double it implies
- §2.29 Enforcement: ADRs, fitness functions, ArchUnit, JPMS, module boundaries in the build file
- §2.30 The cost model — what every pattern charges, and the migration/evolution ladder

## PART 3 — UNDER THE HOOD (lane E)

- §3.1 JVM dispatch: `invokevirtual`/`invokeinterface`, vtable/itable, monomorphic → bimorphic → megamorphic inline caches, and the measured cost of a strategy interface
- §3.2 Escape analysis and scalar replacement — why a builder's allocation is often free, and when it is not
- §3.3 Class initialisation: JVMS §5.5, the init lock, and the initialization-on-demand holder idiom
- §3.4 `volatile`, safe publication, final-field semantics, and why DCL needs the barrier
- §3.5 Enum singleton: the serialization mechanism, `readResolve`, and the reflection guard
- §3.6 `Cloneable`/`clone()` source walk, and copy-constructor/copy-factory alternatives
- §3.7 JDK dynamic proxy internals: `Proxy.newProxyInstance`, the generated class, caching, `equals`/`hashCode`/`toString`, default methods
- §3.8 Subclass proxying: CGLIB/ByteBuddy, Spring's proxy-vs-target-class decision, the interceptor chain, and the self-invocation bypass
- §3.9 Spring's own pattern implementations, source-walked
- §3.10 The JDK's own pattern implementations, source-walked
- §3.11 Filter chains: `ApplicationFilterChain` and the Spring Security chain
- §3.12 Records: what the compiler generates, and the immutability it does and does not give
- §3.13 Sealed types and exhaustive switch: `PermittedSubclasses`, `typeSwitch` bootstrap, `MatchException` — the mechanism that retires visitor
- §3.14 Immutability at JIT level: trusted finals, constant folding, and the safe-publication guarantee
- §3.15 Resilience4j internals: the state machine, the sliding windows, the CAS on state transition
- §3.16 Event-sourcing internals: the append-only log, version-based optimistic concurrency, snapshotting, upcasting
- §3.17 Outbox internals: same-transaction insert, polling vs CDC, ordering, dedup, relay idempotence
- §3.18 Optimistic locking as the aggregate's enforcement mechanism: `@Version`, the generated SQL, the exception path
- §3.19 Observer internals: `ApplicationEventMulticaster`, `@TransactionalEventListener` phases, `TransactionSynchronization`, the listener leak, the `ConcurrentModificationException`
- §3.20 Architecture enforcement mechanics: package-private, JPMS, ArchUnit rule evaluation, `jdeps`, build-module boundaries
- §3.21 Measuring design decisions: JMH on the indirection, async-profiler on the megamorphic site, the numbers that justify or kill an abstraction
- §3.22 Failure case studies: real postmortems where a design pattern or its absence was the root cause

## PART 4 — BUILD IT (lane F)

Each section is one implementation, and each ends with a **Diff vs the real one** table leaf.

- §4.1 A DI container: constructor injection, singleton scope, circular-dependency detection
- §4.2 A proxy-based interceptor chain
- §4.3 A plugin registry over `ServiceLoader`
- §4.4 A state-machine engine with guards, actions and illegal-transition rejection
- §4.5 An event bus with sync, async and after-commit modes
- §4.6 A circuit breaker with a sliding window
- §4.7 A retry with exponential backoff and full jitter
- §4.8 A bulkhead with `Semaphore`
- §4.9 An idempotency store enforced by a unique index
- §4.10 A transactional outbox and its relay
- §4.11 An event-sourced aggregate with snapshots
- §4.12 A CQRS projection with a measured lag metric
- §4.13 A specification combinator
- §4.14 A hexagonal vertical slice, end to end, with no framework type in the domain module
- §4.15 ArchUnit fitness functions that fail the build

## PART 5 — INTERVIEW & RETENTION (lane F)

- §5.1 The question bank — every question, tiered, each with the real probe behind it
- §5.2 The traps and the cold assertions — one line each, the wrong belief and the right one
- §5.3 The drills: whiteboard exercises, refactoring katas, the retention schedule
