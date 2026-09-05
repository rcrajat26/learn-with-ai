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

### Gaps vs the current guide — lane E

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