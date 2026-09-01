# 04 Modern Java — index and file plan

**Target version: Java 21 LTS.** Anything introduced or changed in Java 22–26 is marked inline
with its version. Preview status is stated on every feature where it applies.

| | |
|---|---|
| Topic | 04 — Modern Java (Java 8 → 21 additions) |
| Source prompt | `src/metadata/prompts/04-modern-java-prompt.md` |
| Prompt SHA-256 | `9607419455fa0ffff7dcc05b333516f8965b9ff7a02ff8c7f33be5f3d4a31ece` |
| Prompt last modified | 2026-08-30 13:39:51 |
| Syllabus leaves | **984** (Part 1: 410 · Part 2: 190 · Part 3: 210 · Part 4: 65 · Part 5: 109) |
| Diagram manifest | **182** (D-001 … D-182); 46 are `table` type and render as Markdown tables, 136 are standalone SVGs |
| Note files planned | **69** plus this index |

On resume: if the prompt's SHA-256 no longer matches the value above, every row reverts to
`planned` and the set is rebuilt. Otherwise dispatch only the rows marked `planned` or
`blocked`.

**Deviation from the prompt's `# OUTPUT CONTRACT`, recorded here as required.** The contract
names 62 note files. Five of them were split at planning time because their leaf and tag load
puts them over the 600-line hard split, which the contract explicitly permits ("If any single
file becomes unwieldy, split it further and register the new files in `00-index.md`"):

| Contract file | Split into | Reason |
|---|---|---|
| `collectors/01-basics.md` | `collectors/01-basics-a.md`, `01-basics-b.md` | §1.10 is 30 leaves with 16 `[PROVE]`/`[SOURCE]` obligations and 6 diagrams; split at the `mapping`/`groupingBy` concept boundary |
| `records/01-basics.md` | `records/01-basics-a.md`, `01-basics-b.md` | §1.13 is 28 leaves; split between declaration/constructors and immutability/generated-members |
| `94-interview-questions-and-drills.md` | `94-interview-questions-a.md`, `-b.md`, `-c.md`, `95-traps-drills-and-checklist.md` | §5.1 alone is 95 questions at spoken answer length; §5.2–§5.3 plus the Part 5 wrap-up and the atomic concept checklist form the fourth file |

The flat `## Atomic concept checklist` lives at the end of the last file of the set,
`95-traps-drills-and-checklist.md`, as the prompt requires. `92-interview-internals.md`
carries a pointer to it rather than a second copy.

### Per-file length: a deliberate, measured deviation

The generator's house style targets 250–450 lines per note file and treats 600 as a hard split
point. **The files in this set run 700–1,150 lines, and that is intentional.** The reason is
measured rather than assumed: the first six files were written to the plan above, and they came
back at 773, 863, 895, 947, 1029 and 1081 lines against estimates of 326–558. Plotting actual
length against leaf count shows the length is almost independent of how many leaves a file
carries — roughly `700 + 12 × leaves`. The ~700 lines of fixed cost come from what the prompt
mandates on *every* file regardless of size:

- `## Pitfalls` written wrong-then-right, each entry carrying two working code blocks;
- a cheat-sheet table;
- 5–10 self-test questions with the full answer, not a hint;
- the eight-beat treatment of every primary concept, in which beats 5 and 6 are an embedded
  diagram and a complete, compiling, QuizStakes-domain code example.

Because that cost is fixed, splitting a 900-line file in two produces two files of roughly 770 —
splitting does not bring the halves under 600. The 600-line rule and the prompt's per-concept and
per-file requirements cannot both be satisfied, and the prompt is explicit about which way to
resolve it: *"No line limit and no file-count limit. Completeness beats brevity every single time.
Never truncate, never write 'and so on', never defer a concept for space."*

So the rule was relaxed rather than the content thinned: writers were given a target of
`700 + 12 × leaves + 8 × diagrams` lines with a re-split trigger at **1,200**. Five rows were
still split at planning time on leaf and tag load, as recorded above. The `Est. lines` column
below carries the recalibrated figures. Anyone re-running the size check on this topic should
compare against those, not against 600.

---

## File plan

One sealed row per file. `Leaves` is authoritative: every one of the 984 leaves appears in
exactly one row.

| # | File | Subject | Part / tier | Leaves | Count | Primary concepts | Diagrams | Examples (QuizStakes slice) | Prev | Next | Est. lines | Status | Lines |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | `platform-and-releases/01-basics.md` | platform and releases | Part 1 — BASICS | 1.1.1–1.1.12 | 12 | the six-month release train; LTS as a commercial not technical property; preview/incubator/experimental as three maturity ladders; `--release` vs `-source`/`-target`; class-file major versions | D-001, D-002, D-003, D-004 | The QuizStakes estate itself: which JDK `PaymentService` and `FundsLedger` run on, and a `BalanceView` call to `List.of(...)` compiled `-source 8` that `NoSuchMethodError`s in production | — (first) | `platform-and-releases/02-migration.md` | 876 | written | 895 |
| 2 | `platform-and-releases/02-migration.md` | platform and releases | Part 2 — INTERMEDIATE | 2.14.1–2.14.14 | 14 | what breaks at 9/11/16/17/18/21; JEP 400 UTF-8 as the silent behaviour change; the library floor; the mechanical refactors worth doing; the safe rollout order | D-122, D-123 | Migrating `FundsLedger` and `DocumentVerification` from 8 to 21: `String.getBytes()` on a payout file at 18, and `getFirst()` clashing on a hand-rolled sequenced type at 21 | `platform-and-releases/01-basics.md` | `platform-and-releases/03-internals-version-delta.md` | 884 | written | 773 |
| 3 | `platform-and-releases/03-internals-version-delta.md` | platform and releases | Part 3 — INTERNALS | 3.16.1–3.16.22 | 22 | the release-by-release delta 8 to 25; the consolidated feature-to-version table; the removed-or-disabled table; how to answer "what is new in Java N" | D-166, D-167 | Dating every claim in the guide against the release QuizStakes actually runs; §12 payment flows as the code being upgraded | `platform-and-releases/02-migration.md` | `platform-and-releases/04-internals-observability.md` | 980 | written | 1029 |
| 4 | `platform-and-releases/04-internals-observability.md` | platform and releases | Part 3 — INTERNALS | 3.17.1–3.17.12 | 12 | `javap -c -p -v` as the evidence for every desugaring claim; `jshell` experiments; JFR for this topic; the JSON thread dump; JMH discipline; static analysis rules | D-168 | Verifying the guide's own claims on the `FundsLedger` classes: `-Xlog:class+load=info` while a stake-reservation pipeline warms up | `platform-and-releases/03-internals-version-delta.md` | `functional-interfaces/01-basics.md` | 852 | written | 863 |
| 5 | `functional-interfaces/01-basics.md` | functional interfaces | Part 1 — BASICS | 1.2.1–1.2.20 | 20 | the SAM definition and the `Object`-method exclusion; the six core shapes and their narrowings; the 43-interface inventory and its naming scheme; why the primitive specialisations exist; the shapes the JDK withholds | D-005, D-006, D-007, D-008 | `Function<LedgerEntry, Money>`, `Predicate<Restriction>`, `Supplier<IdempotencyKey>`; a domain-named `StakeRule` beating `Function<Reservation, Money>`; §15 Example Bank rows on restriction evaluation | `platform-and-releases/04-internals-observability.md` | `lambdas/01-basics.md` | 972 | written | 1081 |
| 6 | `lambdas/01-basics.md` | lambdas | Part 1 — BASICS | 1.3.1–1.3.22 | 22 | lambda syntax forms; the poly expression and target typing; `this` and lexical transparency; capture by value and effectively-final; loop-variable capture; the recursion and checked-exception limits | D-009, D-010, D-011, D-012, D-013, D-014 | `BonusService` registering a `Runnable`; `FundsLedger.reserveStake` capturing a `Money stake`; iterating `reservations` versus a classic `for` index | `functional-interfaces/01-basics.md` | `lambdas/02-cost-and-choice.md` | 1012 | written | 947 |
| 7 | `lambdas/02-cost-and-choice.md` | lambdas | Part 2 — INTERMEDIATE | 2.2.1–2.2.14 | 14 | first-call linkage cost versus steady state; non-capturing caching versus per-evaluation allocation; the anonymous-class alternative; megamorphic call sites; composition; the four checked-exception workarounds | D-094, D-095, D-170 | A composite `Predicate<Restriction>` reduced from a list of restriction rules; an `IOException`-throwing payout-file read inside a `map` over 7k bank withdrawals | `lambdas/01-basics.md` | `lambdas/03-internals-translation.md` | 892 | written | 1200 |
| 8 | `lambdas/03-internals-translation.md` | lambdas | Part 3 — INTERNALS | 3.1.1–3.1.18 | 18 | `lambda$` desugaring; `invokedynamic` and `LambdaMetafactory.metafactory`'s six parameters; static versus dynamic arguments; `InnerClassLambdaMetafactory` and hidden classes; the method-reference shortcut; serializable lambdas | D-125, D-126, D-127, D-128, D-129 | `javap -c -p` on a `FundsLedger` class holding one capturing and one non-capturing lambda over `Reservation` | `lambdas/02-cost-and-choice.md` | `lambdas/04-internals-capture-and-identity.md` | 956 | written | 1181 |
| 9 | `lambdas/04-internals-capture-and-identity.md` | lambdas | Part 3 — INTERNALS | 3.2.1–3.2.10 | 10 | capture by value into a spun field; capturing `this` versus capturing a field read; the listener-registry leak; lambda identity and why `==` is meaningless; what the JIT does with a lambda call site | D-130 | A static `NotificationService` registry holding a lambda that reads a `ProfileService` instance field, and the retained subgraph that follows | `lambdas/03-internals-translation.md` | `method-references/01-basics.md` | 828 | written | 1506 |
| 10 | `method-references/01-basics.md` | method references | Part 1 — BASICS | 1.4.1–1.4.16 | 16 | the six forms; unbound receiver becoming the first parameter; receiver evaluation at capture time; the ambiguity cases; constructor references to records; the bytecode difference from a lambda | D-015, D-016, D-017 | `Money::of`, `ledger::append`, `Reservation::amount`, `StakeSplit::new`; a `ledger::flush` reference captured then the variable reassigned | `lambdas/04-internals-capture-and-identity.md` | `streams/01-basics-the-model.md` | 916 | written | 1347 |
| 11 | `streams/01-basics-the-model.md` | streams | Part 1 — BASICS | 1.5.1–1.5.18 | 18 | the javadoc's five properties; source/intermediate/terminal anatomy; laziness and fusion; short-circuiting; encounter order; non-interference and statelessness; single consumption; closing | D-018, D-019, D-020, D-021, D-022 | A pipeline over 95k card deposits per day; the two exact `IllegalStateException` messages; `Files.lines(paymentRunFile)` needing a close | `method-references/01-basics.md` | `streams/02-sources.md` | 956 | written | 1841 |
| 12 | `streams/02-sources.md` | streams | Part 1 — BASICS | 1.6.1–1.6.18 | 18 | every stream source and its guarantees; `IntStream.range` as the best-splitting source; `Stream.iterate`'s two forms; `Stream.concat`'s left-deep tree; `StreamSupport` as the escape hatch; the sources that need closing | D-023, D-024 | `ledgerEntries.stream()`, `IntStream.range(0, 2_800_000)` over a day of stake reservations, `Files.lines(paymentRunFile)`, and a hand-written JDBC bridge for `ResultSet` | `streams/01-basics-the-model.md` | `streams/03-intermediate-operations.md` | 932 | written | 1567 |
| 13 | `streams/03-intermediate-operations.md` | streams | Part 1 — BASICS | 1.7.1–1.7.24 | 24 | every intermediate operation with its flags; `flatMap` versus `mapMulti`; `takeWhile` as a prefix not a test; `sorted` as a barrier that throws at terminal time; `peek` elision; the absent `zip`/windowing; operation order as cost | D-025, D-026, D-027, D-028, D-029, D-030 | Stake amounts `[4.20, 3.33, 12.00, 2.10, 1.05]` under `amount < 5`; `.sorted(byAmount).limit(10)` over 2.8M stake reservations; `Movement` values holding zero, one or three `LedgerEntry`s | `streams/02-sources.md` | `streams/04-terminal-operations.md` | 1036 | written | 1389 |
| 14 | `streams/04-terminal-operations.md` | streams | Part 1 — BASICS | 1.8.1–1.8.26 | 26 | the three `reduce` overloads and their contracts; identity and associativity in parallel; `collect` versus `reduce` versus `forEach`; `count()`'s Java 9 bypass; vacuous `allMatch`; `findFirst` versus `findAny`; the null policy across the list-producing paths | D-031, D-032, D-033, D-034, D-035 | Summing `Money` over 95k card deposits; subtraction over `[65, 480, 42, 180]`; a four-leaf task tree over 2.8M reservations | `streams/03-intermediate-operations.md` | `streams/05-primitive-streams.md` | 1052 | written | 1571 |
| 15 | `streams/05-primitive-streams.md` | streams | Part 1 — BASICS | 1.9.1–1.9.16 | 16 | the three primitive streams and the conversions between the four shapes; why there is no `CharStream`; `OptionalInt`'s deliberately thinner API; `IntStream.sum()` overflow; the memory arithmetic for boxed versus primitive | D-036, D-037, D-038 | 2.8M stake amounts in minor units as `int[]` versus `List<Integer>`; the `int` total wrapping past 2 147 483 647 | `streams/04-terminal-operations.md` | `streams/06-cost-model.md` | 916 | written | 1311 |
| 16 | `streams/06-cost-model.md` | streams | Part 2 — INTERMEDIATE | 2.3.1–2.3.16 | 16 | what a pipeline costs against a loop; the allocation profile before the first element moves; debuggability and stack depth; ordering as optimisation; `sorted().findFirst()` versus `min`; when to use a loop and when a stream | D-096, D-097, D-098, D-169 | A three-stage pipeline over card deposits; comparator-invocation counts at N = 95,000; the accidental O(n·m) from re-streaming restrictions inside a loop over clients | `streams/05-primitive-streams.md` | `streams/07-parallel-streams.md` | 924 | written | 1492 |
| 17 | `streams/07-parallel-streams.md` | streams | Part 2 — INTERMEDIATE | 2.4.1–2.4.16 | 16 | the common pool and its true effective width; the four preconditions and the N×Q heuristic; source splitting quality; ordering and merge costs; shared mutable state; why collectors are safe; the default answer in a server | D-099, D-100, D-101, D-102 | The identity vendor's 38 s p99 blocking every common-pool worker; `parallelStream().forEach(list::add)` over ledger entries; 40 deposits/sec versus 2.8M reservations/day | `streams/06-cost-model.md` | `streams/08-internals-pipeline.md` | 924 | written | 1927 |
| 18 | `streams/08-internals-pipeline.md` | streams | Part 3 — INTERNALS | 3.3.1–3.3.20 | 20 | `AbstractPipeline`'s twelve fields and the stage chain; `Sink`'s four-method protocol; `opWrapSink` and `wrapSink` walking backwards; `copyInto`/`copyIntoWithCancel`; the `StreamOpFlag` lattice; how `count()` bypasses the pipeline | D-131, D-132, D-133, D-134 | `deposits.stream().filter(...).map(...).collect(...)` walked stage by stage with `depth` 0/1/2; the two `linkedOrConsumed` messages verbatim | `streams/07-parallel-streams.md` | `streams/09-internals-spliterator.md` | 972 | written | 1826 |
| 19 | `streams/09-internals-spliterator.md` | streams | Part 3 — INTERNALS | 3.4.1–3.4.14 | 14 | the eight characteristics with their hex bits; `SIZED` versus `SUBSIZED`; `trySplit` returning the prefix; the per-collection spliterators; the `IteratorSpliterator` batching fallback; writing one that splits well | D-135, D-136, D-137, D-138 | An `ArrayList` of 95,000 card deposits split 0–47,499 / 47,500–94,999; `LinkedList` and `Files.lines(paymentRunFile)` as the batching cases | `streams/08-internals-pipeline.md` | `streams/10-internals-parallel-execution.md` | 900 | written | 1264 |
| 20 | `streams/10-internals-parallel-execution.md` | streams | Part 3 — INTERNALS | 3.5.1–3.5.14 | 14 | `AbstractTask` and the leaf-size target; the op implementation classes; `ReduceTask` and the combine tree; `ForEachTask` versus `ForEachOrderedTask`; `SliceOps` ordering; the common pool, work stealing and `ManagedBlocker`; exception propagation | D-139, D-140, D-141, D-142 | An `AbstractTask` tree over 2.8M reservations on an 8-core box, with the leaf count and leaf size worked out | `streams/09-internals-spliterator.md` | `collectors/01-basics-a.md` | 900 | written | 1469 |
| 21 | `collectors/01-basics-a.md` | collectors | Part 1 — BASICS | 1.10.1–1.10.16 | 16 | the five-function `Collector` contract and the three characteristics; the `toX` family; `toMap`'s duplicate-key and null-value failures; `joining`; the summing/averaging/summarizing family and Kahan summation; `mapping`/`filtering`/`flatMapping`/`collectingAndThen` | D-039, D-040 | Collecting 95k card deposits by rail; `toMap` on `(ClientId, Money)` with a duplicate identity; `summingDouble` over deposits averaging 65 | `streams/10-internals-parallel-execution.md` | `collectors/01-basics-b.md` | 908 | written | 1143 |
| 22 | `collectors/01-basics-b.md` | collectors | Part 1 — BASICS | 1.10.17–1.10.30 | 14 | `groupingBy`'s three overloads and the types it really returns; the null-classifier NPE; `partitioningBy` always carrying both keys; `groupingByConcurrent` and the three conditions for a concurrent reduction; `teeing`; hand-writing a collector; the collector inventory | D-041, D-042, D-043, D-044 | `groupingBy(Deposit::rail, mapping(Deposit::amount, toList()))`; `partitioningBy` over an empty reservation stream; `teeing` for min-and-max withdrawal in one pass | `collectors/01-basics-a.md` | `collectors/02-in-anger.md` | 900 | written | 1598 |
| 23 | `collectors/02-in-anger.md` | collectors | Part 2 — INTERMEDIATE | 2.5.1–2.5.14 | 14 | multi-level grouping and reading the nested type; `filtering` versus a pre-`filter`; choosing the map implementation; `toMap` merge strategies; `teeing`; a bounded top-N collector; a boxing-free statistics collector; three routes to an immutable result | D-103, D-104 | Top-3 withdrawals by amount (180, 260, 92) merged across two leaves; grouping card deposits by rail where one rail has nothing above 100 | `collectors/01-basics-b.md` | `collectors/03-internals-collectors.md` | 884 | written | 1018 |
| 24 | `collectors/03-internals-collectors.md` | collectors | Part 3 — INTERNALS | 3.6.1–3.6.10 | 10 | `CollectorImpl` and the six pre-built characteristic sets; `toList`'s three functions and the O(n) combine tree; `groupingBy`'s `computeIfAbsent` and its unchecked-cast finisher; Kahan compensation in `summingDouble`; what `IDENTITY_FINISH` saves | D-143, D-144, D-145 | Summing 95,000 card deposits averaging 65 as `double`s, naive total against compensated total | `collectors/02-in-anger.md` | `optional/01-basics.md` | 844 | written | 1104 |
| 25 | `optional/01-basics.md` | optional | Part 1 — BASICS | 1.11.1–1.11.24 | 24 | the return-type-only purpose and the javadoc API note; value-based and not `Serializable`; the full method table by version; `orElse`'s eager argument; the `isPresent`+`get` anti-pattern; the four places it must never appear; `map`'s null-mapper behaviour | D-045, D-046, D-047, D-048 | `findClient(id)` chained `Client` to `Account` to `Wallet` to `Money.ZERO`; a `loadDefaultFromDatabase()` call counter proving eager evaluation | `collectors/03-internals-collectors.md` | `optional/02-discipline.md` | 1020 | written | 1632 |
| 26 | `optional/02-discipline.md` | optional | Part 2 — INTERMEDIATE | 2.6.1–2.6.12 | 12 | the rule set in one place; the chain style; `orElse`/`orElseGet`/`orElseThrow` decision table; `or` for a fallback chain; `Optional` inside a stream; the Spring Data and Jackson contracts; the four absence strategies compared | D-105, D-106 | `findById` on a client repository versus `getReferenceById`; `Money.ZERO` as a constant default against a database fallback against a `RestrictedActionException` | `optional/01-basics.md` | `optional/03-internals-optional.md` | 860 | written | 1069 |
| 27 | `optional/03-internals-optional.md` | optional | Part 3 — INTERNALS | 3.7.1–3.7.8 | 8 | the single `value` field and the shared `EMPTY`; `@jdk.internal.ValueBased` and what it forbids; `map`'s one-line body; `get` and `orElseThrow` being identical; the 16-byte cost and when escape analysis removes it; the Valhalla trajectory | D-146 | An `Optional<Client>` on the heap; a five-`map` chain over a client lookup with and without escape analysis | `optional/02-discipline.md` | `var/01-basics.md` | 804 | written | 910 |
| 28 | `var/01-basics.md` | var | Part 1 — BASICS | 1.12.1–1.12.16 | 16 | `var` as compile-time-only inference and a reserved type name; where it is legal and where it is not; `var x = null` and the array shorthand; the diamond inferring `Object`; poly expressions; non-denotable types; when `var` hurts | D-049, D-050 | `var positions = new ArrayList<>()` losing `Position`; `var total = 0` as an accumulator over minor-unit stake amounts | `optional/03-internals-optional.md` | `var/02-in-practice.md` | 908 | written | 1245 |
| 29 | `var/02-in-practice.md` | var | Part 2 — INTERMEDIATE | 2.7.1–2.7.10 | 10 | a style policy defensible in review; the cases where `var` clearly wins; the interface-versus-implementation trap; numeric-literal width; `var` in lambda parameters; what refactoring does to a `var` local | D-107 | Iterating `Map.Entry<RestrictionKey, Restriction>`; a `Map<String, List<Map<String, Integer>>>` of per-rail counts | `var/01-basics.md` | `var/03-internals-inference.md` | 828 | written | 1362 |
| 30 | `var/03-internals-inference.md` | var | Part 3 — INTERNALS | 3.8.1–3.8.8 | 8 | standalone type plus upward projection; the `LocalVariableTable` as the only trace; why a field or parameter could never work; diamond inference with no target type; anonymous-class initialisers | D-147, D-148 | `List<? extends Money> amounts; var first = amounts.get(0);` projecting the capture variable away to `Money` | `var/02-in-practice.md` | `records/01-basics-a.md` | 812 | written | 1066 |
| 31 | `records/01-basics-a.md` | records | Part 1 — BASICS | 1.13.1–1.13.15 | 15 | a record as a nominal tuple; the generated members and implicit modifiers; the canonical and compact constructors; validation by reassigning the parameter; alternate constructors and accessibility; generic, local and nested records | D-051, D-052 | `record StakeSplit(Money bonusPortion, Money cashPortion)` with the compact constructor enforcing that the two sum exactly to the stake, worked on the 3.33 = 0.33 + 3.00 split | `var/03-internals-inference.md` | `records/01-basics-b.md` | 896 | written | 1023 |
| 32 | `records/01-basics-b.md` | records | Part 1 — BASICS | 1.13.16–1.13.28 | 13 | shallow immutability and the defensive-copy fix; the array-component `equals` failure; the generated `equals`/`hashCode`/`toString` semantics; `NaN` and `-0.0` inside a record; reflection; record serialization closing the validation hole; the record cliff | D-053, D-054, D-055 | `record PaymentRun(RunId id, List<WithdrawalTransaction> items)` constructed from a caller-held `ArrayList`; a `Money` component's `BigDecimal` versus a raw `double` price component | `records/01-basics-a.md` | `records/02-in-practice.md` | 880 | written | 1317 |
| 33 | `records/02-in-practice.md` | records | Part 2 — INTERMEDIATE | 2.8.1–2.8.16 | 16 | records as DTOs at an HTTP boundary; Jackson and Spring binding and the `-parameters` flag; Bean Validation targets; why a record cannot be a JPA entity but is an excellent projection; compound map keys; local records; the wither pattern; floating-point components | D-108, D-109 | A `DepositRequest`/`DepositResponse` pair at the `ApplicationGateway`; `RestrictionKey(RestrictionType, RestrictionSource)` as a compound map key | `records/01-basics-b.md` | `records/03-internals-records.md` | 908 | written | 1179 |
| 34 | `records/03-internals-records.md` | records | Part 3 — INTERNALS | 3.9.1–3.9.14 | 14 | the `Record` class-file attribute and its `record_component_info` entries; `ObjectMethods.bootstrap` behind the three generated methods; why the `hashCode` algorithm is unspecified; the compact-constructor desugaring in `javap`; record serialization and the ignored hooks; blocked `setAccessible` | D-149, D-150, D-151 | `javap -v` on `StakeSplit`, with the component-name string `"bonusPortion;cashPortion"` and one `MethodHandle` getter per component | `records/02-in-practice.md` | `sealed-types/01-basics.md` | 892 | written | 1140 |
| 35 | `sealed-types/01-basics.md` | sealed types | Part 1 — BASICS | 1.14.1–1.14.18 | 18 | `sealed` and `permits`; the final/sealed/non-sealed obligation on every permitted subtype; the same-module rule and direct extension; the two ADT shapes; sealed versus enum; what sealing buys you and the compiler; the cost across an API boundary | D-056, D-057, D-058, D-059 | `sealed interface Verdict permits DocumentVerdict, ScreeningVerdict, ReviewVerdict, WealthVerdict`; `RestrictionType` as the enum that should stay an enum | `records/03-internals-records.md` | `sealed-types/02-data-oriented-programming.md` | 948 | written | 1653 |
| 36 | `sealed-types/02-data-oriented-programming.md` | sealed types | Part 2 — INTERMEDIATE | 2.9.1–2.9.12 | 12 | sum of products; data-oriented programming as Goetz frames it; Visitor replaced by a sealed interface plus a pattern switch; the expression problem; a state machine and a `Result` type as sealed hierarchies; sealed types across a published API; serialising a sealed hierarchy | D-110, D-111, D-112 | The `Verdict` hierarchy against a `VerdictVisitor`; the account lifecycle (`PENDING_VERIFICATION`, `ACTIVE`, `DORMANT`, `CLOSING`, `CLOSED`) as a sealed interface of records | `sealed-types/01-basics.md` | `sealed-types/03-internals-sealed.md` | 868 | written | 1423 |
| 37 | `sealed-types/03-internals-sealed.md` | sealed types | Part 3 — INTERNALS | 3.10.1–3.10.8 | 8 | the `PermittedSubclasses` attribute and the absence of `ACC_SEALED`; `non-sealed` emitting nothing; load-time enforcement surviving bytecode manipulation; the same-module check; narrowing reference conversion; the separate-compilation hazard | D-152 | The `Verdict` class file with four constant-pool indices, and a bytecode-manipulated fifth subclass rejected at load time | `sealed-types/02-data-oriented-programming.md` | `pattern-matching/01-basics.md` | 804 | written | 944 |
| 38 | `pattern-matching/01-basics.md` | pattern matching | Part 1 — BASICS | 1.15.1–1.15.24 | 24 | a pattern as test, extraction and binding; flow scoping including negation and `&&`/`||`; `case null` and the NPE without it; `when` guards; record patterns and nesting; exhaustiveness and the exempt legacy selector types; `MatchException`; dominance | D-060, D-061, D-062, D-063, D-064, D-065 | Switching over `Verdict`; `case Movement(LedgerEntry(Position from, Money amount), LedgerEntry to)` as the nested deconstruction | `sealed-types/03-internals-sealed.md` | `pattern-matching/02-in-anger.md` | 1036 | written | 1321 |
| 39 | `pattern-matching/02-in-anger.md` | pattern matching | Part 2 — INTERMEDIATE | 2.10.1–2.10.12 | 12 | refactoring an `instanceof` chain step by step; record deconstruction replacing getter-plus-condition; guards versus nested switches; naming the total pattern; handling null explicitly; migration risk and exhaustiveness drift; the `typeSwitch` cost model; the readability limit | D-113, D-114 | The `Verdict` `if`/`else if` chain converted in four steps; a fifth `Verdict` case added and only the hierarchy redeployed | `pattern-matching/01-basics.md` | `pattern-matching/03-internals-pattern-matching.md` | 860 | written | 1332 |
| 40 | `pattern-matching/03-internals-pattern-matching.md` | pattern matching | Part 3 — INTERNALS | 3.11.1–3.11.12 | 12 | `instanceof` patterns compiling to plain bytecode; flow scoping as a compile-time analysis; `SwitchBootstraps.typeSwitch` returning an index into a `tableswitch`; the bootstrap's static arguments; deconstruction as ordered accessor calls; exhaustiveness and dominance in the JLS; null routing | D-153, D-154 | The `javap -c` listing for a pattern switch over `Verdict`, and an accessor throwing during deconstruction wrapped in `MatchException` | `pattern-matching/02-in-anger.md` | `switch/01-basics.md` | 860 | written | 1828 |
| 41 | `switch/01-basics.md` | switch | Part 1 — BASICS | 1.16.1–1.16.18 | 18 | switch expressions and the arrow form; `yield` and why `return` is illegal; exhaustiveness in expressions and in Java 21 pattern statements; the colon form and fall-through; the permitted selector types; the `default`-in-an-enum-switch trade-off | D-066, D-067, D-068 | Dispatching on `RestrictionType`; a colon switch over restriction sources with a missing `break` | `pattern-matching/03-internals-pattern-matching.md` | `switch/03-internals-switch-compilation.md` | 940 | written | 997 |
| 42 | `switch/03-internals-switch-compilation.md` | switch | Part 3 — INTERNALS | 3.12.1–3.12.8 | 8 | `tableswitch` versus `lookupswitch` and the density heuristic; the two-stage `String` switch; `$SwitchMap` protecting a separately compiled enum switch; the arrow form compiling identically; the operand stack at the join point; the synthetic default in an exhaustive enum switch expression | D-155, D-156, D-157 | `$SwitchMap$RestrictionType` contents shown, and the enum reordered without recompiling the switch | `switch/01-basics.md` | `text-blocks/01-basics.md` | 820 | written | 1270 |
| 43 | `text-blocks/01-basics.md` | text blocks | Part 1 — BASICS | 1.17.1–1.17.16 | 16 | the syntax and the opening-delimiter rule; the three compile-time steps in order; incidental-whitespace computation including the closing delimiter; trailing-whitespace stripping; `\s` and `\` line continuation; the runtime siblings; text blocks as constant expressions | D-069, D-070, D-071, D-072 | The SQL text block that reads `CLIENT_CASH_AVAILABLE` positions from the ledger, with the closing delimiter moved four columns left | `switch/03-internals-switch-compilation.md` | `text-blocks/02-in-practice.md` | 924 | written | 1492 |
| 44 | `text-blocks/02-in-practice.md` | text blocks | Part 2 — INTERMEDIATE | 2.11.1–2.11.8 | 8 | SQL with bound parameters rather than interpolation; JSON fixtures with `formatted`; regex where the text block loses; trailing-newline discipline; text blocks in annotations and `case` labels; the absence of interpolation in Java 21 | D-115 | The ledger-balance SQL as a text block with `?` placeholders; a `DEP-301 CAPTURED` webhook JSON fixture | `text-blocks/01-basics.md` | `text-blocks/03-internals-compilation.md` | 804 | written | 1266 |
| 45 | `text-blocks/03-internals-compilation.md` | text blocks | Part 3 — INTERNALS | 3.13.1–3.13.6 | 6 | the whole transformation happening in `javac`; the specified three-step algorithm; the exact minimal-indent computation; the result as a `CONSTANT_String_info` and therefore interned; `String.stripIndent()` as the runtime sibling; `==` on a text block and an equal literal | D-158 | The `javap -v` constant pool for the ledger SQL text block, already stripped | `text-blocks/02-in-practice.md` | `virtual-threads/01-basics.md` | 780 | written | 1003 |
| 46 | `virtual-threads/01-basics.md` | virtual threads | Part 1 — BASICS | 1.18.1–1.18.24 | 24 | a virtual thread as a `Thread` scheduled by the runtime; Little's law as the framing; carriers and the scheduler properties; mounting and unmounting and what triggers each; the cost arithmetic; the creation API; what a virtual thread refuses to do; `ThreadLocal` economics; pinning and its diagnosis; the three standing rules | D-073, D-074, D-075, D-076, D-077, D-078, D-079 | 55k peak concurrent sessions; 1,200 stake reservations/sec at the card PSP's 240 ms p50 needing 288 concurrent tasks, and 13,200 at the 11 s p99 | `text-blocks/03-internals-compilation.md` | `virtual-threads/02-in-production.md` | 1044 | written | 1324 |
| 47 | `virtual-threads/02-in-production.md` | virtual threads | Part 2 — INTERMEDIATE | 2.12.1–2.12.18 | 18 | the thread-per-request model restored and what the Spring flag switches; losing the pool means losing the queue; the bottleneck moving downstream; pinning drivers; `ThreadLocal` and MDC costs; thread dumps and the four JFR events; what to measure now; memory sizing; the migration checklist | D-116, D-117, D-118, D-119 | Tomcat at `maxThreads=200` against 55k peak sessions; 14k concurrent virtual threads arriving at a 20-connection JDBC pool | `virtual-threads/01-basics.md` | `virtual-threads/03-internals-virtual-threads.md` | 948 | written | 1197 |
| 48 | `virtual-threads/03-internals-virtual-threads.md` | virtual threads | Part 3 — INTERNALS | 3.14.1–3.14.18 | 18 | the three layers and `Continuation`; frame copying to and from a heap `StackChunk`; the nine-state machine; the FIFO scheduler and its verified defaults; the instrumented and non-instrumented blocking points; pinning as a continuation property and JEP 491; no preemption and pool compensation | D-159, D-160, D-161, D-162, D-163 | A virtual thread blocking on the card PSP's 240 ms p50 across four mount/unmount frames; the heap arithmetic for 1,000,000 virtual threads | `virtual-threads/02-in-production.md` | `structured-concurrency/01-basics.md` | 956 | written | 1132 |
| 49 | `structured-concurrency/01-basics.md` | structured concurrency | Part 1 — BASICS | 1.19.1–1.19.16 | 16 | the leak/cancellation/dump problem; the structured principle; the Java 21 `StructuredTaskScope` shape with `Subtask`; `ShutdownOnFailure` and `ShutdownOnSuccess`; `joinUntil`; the ownership and try-with-resources discipline; cancellation by interrupt; the comparison with `allOf` and `invokeAll`; scoped values | D-080, D-081, D-082, D-083 | `AssessmentService` forking the identity vendor (900 ms p50) and the watchlist provider (1.4 s p50, 25 s p99) under one scope | `virtual-threads/03-internals-virtual-threads.md` | `structured-concurrency/02-in-practice.md` | 924 | written | 1641 |
| 50 | `structured-concurrency/02-in-practice.md` | structured concurrency | Part 2 — INTERMEDIATE | 2.13.1–2.13.10 | 10 | the fan-out call with one deadline and one failure policy; hedged requests; timeouts at scope versus subtask level; which exception surfaces; nesting scopes; scoped values for request context; rebinding as shadowing; what to say in an interview | D-120, D-121 | A 2 s `joinUntil` deadline cutting off the watchlist provider; tenant, principal and trace id carried as scoped values instead of MDC `ThreadLocal`s | `structured-concurrency/01-basics.md` | `structured-concurrency/03-internals.md` | 836 | written | 1048 |
| 51 | `structured-concurrency/03-internals.md` | structured concurrency | Part 3 — INTERNALS | 3.15.1–3.15.8 | 8 | `StructuredTaskScope` on virtual threads plus a per-thread scope stack; the ownership check; `StructureViolationException` and the stack discipline; `shutdown()` versus `close()`; `ScopedValue`'s immutable binding snapshot and its cache; why it is cheaper than `ThreadLocal`; the 19-to-26 churn table | D-164, D-165 | The `AssessmentService` scope tree in a JSON thread dump; a nested `where` shadowing a tenant binding | `structured-concurrency/02-in-practice.md` | `library-additions/01-basics.md` | 812 | written | 1194 |
| 52 | `library-additions/01-basics.md` | library additions | Part 1 — BASICS | 1.20.1–1.20.24 | 24 | the collection factories and their null hostility; the Java 9 stream and `Optional` additions; the Java 11 `String` and `Files` surface and `HttpClient`; `teeing`; `Stream.toList` and `mapMulti`; `RandomGenerator`; JEP 400's UTF-8 default; sequenced collections and the retrofit; `reversed()` as a view | D-084, D-085, D-086 | A `LinkedHashMap` of restriction keys reversed as a view; `Map.of` iteration order changing between JVM runs while listing gates | `structured-concurrency/03-internals.md` | `cost-model/02-master-tables.md` | 1012 | written | 1544 |
| 53 | `cost-model/02-master-tables.md` | cost model | Part 2 — INTERMEDIATE | 2.1.1–2.1.8 | 8 | the master stream cost table; the feature-by-version table; the lambda/method-reference/anonymous-class table; the absence-representation table; the data-carrier table; the concurrency-model table; the list-factory table | D-087, D-088, D-089, D-090, D-091, D-092, D-093 | Every cost quoted against 2.8M stake reservations and 95k card deposits per day | `library-additions/01-basics.md` | `which-construct/02-which-construct.md` | 852 | written | 1017 |
| 54 | `which-construct/02-which-construct.md` | which construct | Part 2 — INTERMEDIATE | 2.15.1–2.15.10 | 10 | the ten construct decisions, each with a default answer and the condition that overrides it | D-124 | Each decision resolved on a real QuizStakes call: the payment-run batch, the assessment fan-out, the restriction evaluation, the ledger projection | `cost-model/02-master-tables.md` | `build-it/01-functional-toolkit.md` | 828 | written | 1214 |
| 55 | `build-it/01-functional-toolkit.md` | build it | Part 4 — BUILD IT | 4.1.1–4.1.8 | 8 | `MyFunction` and `MyPredicate` with composition; `CheckedFunction` plus `unchecked`/`sneaky`; a `Result<T,E>` sealed type; a memoising decorator and the `computeIfAbsent` recursion deadlock; curry/partial; `TriFunction` | — | Composition over `Money` fee-then-rounding on the 3.33 stake; an `IOException`-throwing payout-file read routed through `Result` | `which-construct/02-which-construct.md` | `build-it/02-mystream.md` | 796 | written | 1130 |
| 56 | `build-it/02-mystream.md` | build it | Part 4 — BUILD IT | 4.2.1–4.2.10 | 10 | `MySink`'s four methods; `MyStream` fused through a sink chain; proving fusion, short-circuiting and the stateful barrier; reproducing the consumed-stream exception; a `SIZED` flag reproducing `peek` elision; a trivial parallel evaluation; a JMH comparison | D-171, D-172 | A `MyStream` over stake reservations traced element by element for the first three reservations | `build-it/01-functional-toolkit.md` | `build-it/03-collectors-and-myoptional.md` | 836 | written | 1567 |
| 57 | `build-it/03-collectors-and-myoptional.md` | build it | Part 4 — BUILD IT | 4.3.1–4.3.7, 4.4.1–4.4.6 | 13 | `MyCollector` and the five-function contract; `toList`/`joining`/`groupingBy` with correct combiners; a bounded top-N and a boxing-free statistics collector; a `CONCURRENT` collector harness; `MyOptional` with the shared `EMPTY`; eager-versus-lazy and allocation harnesses | — | Top-3 withdrawals (180, 260, 92); a `long[]` statistics accumulator over 2.8M stake minor-unit amounts | `build-it/02-mystream.md` | `build-it/04-records-sealed-patterns.md` | 856 | written | 1146 |
| 58 | `build-it/04-records-sealed-patterns.md` | build it | Part 4 — BUILD IT | 4.5.1–4.5.8 | 8 | the hand-written pre-record equivalent counted in lines; a `List` component written three ways; an array component's `equals` failure and its fixes; a sealed hierarchy with an exhaustive switch and the exact error a fourth case produces; Visitor side by side; an expression-tree interpreter; a reflective wither | — | `StakeSplit` hand-written against the one-line record; `PaymentRun`'s `List<WithdrawalTransaction>` and `byte[] signature` | `build-it/03-collectors-and-myoptional.md` | `build-it/05-concurrency-builds.md` | 796 | written | 1343 |
| 59 | `build-it/05-concurrency-builds.md` | build it | Part 4 — BUILD IT | 4.6.1–4.6.8 | 8 | the echo server written twice and measured; a pinning reproducer and its `ReentrantLock` fix; a `ThreadLocal` memory harness; a `Semaphore`-bounded client; `ShutdownOnFailure` against `allOf` with a deliberate failure; a hedge; a common-pool starvation reproducer | D-173, D-174, D-175, D-176 | 1, 1,000 and 50,000 concurrent connections; a fan-out to the identity vendor and the watchlist provider with one deliberate failure | `build-it/04-records-sealed-patterns.md` | `build-it/06-filling-the-21-gaps.md` | 828 | written | 1278 |
| 60 | `build-it/06-filling-the-21-gaps.md` | build it | Part 4 — BUILD IT | 4.7.1–4.7.6 | 6 | fixed-window batching via a custom `Spliterator`; `zip` via a paired spliterator; `scan` and `distinctBy` as stateful mappers with their parallel failure demonstrated; `takeUntil` and a `mapConcurrent` on virtual threads; the `Gatherers` diff | D-177 | Fixed windows of 100 ledger entries out of the ~19.8M written per day | `build-it/05-concurrency-builds.md` | `build-it/07-diagnostic-harnesses.md` | 780 | written | 1280 |
| 61 | `build-it/07-diagnostic-harnesses.md` | build it | Part 4 — BUILD IT | 4.8.1–4.8.12 | 12 | the fifteen-snippet puzzler set; stream-versus-loop and parallel-versus-sequential JMH sweeps; a source-splitting benchmark; a lambda-startup harness; a capture identity harness; a `javap` walk; a collector-combiner cost harness; exhaustiveness drift; record serialization; text-block indentation; a migration smoke harness | D-178 | Every harness run over QuizStakes data: 2.8M reservations, 95k deposits, the `Verdict` hierarchy, the ledger SQL text block | `build-it/06-filling-the-21-gaps.md` | `90-interview-basics.md` | 852 | written | 1505 |
| 62 | `90-interview-basics.md` | 90 interview basics.md | Part 1 — INTERVIEW | — | 0 | Part 1 wrap-up: the summary table over the whole basics tier, 10 spoken-length Q&As, 5 predict-the-output puzzles | — | Puzzles drawn from the ledger and reservation examples used across Part 1 | `build-it/07-diagnostic-harnesses.md` | `91-interview-intermediate.md` | 760 | written | 699 |
| 63 | `91-interview-intermediate.md` | 91 interview intermediate.md | Part 2 — INTERVIEW | — | 0 | Part 2 wrap-up: the summary table over the whole intermediate tier, 10 spoken-length Q&As, 5 predict-the-output puzzles | — | Puzzles drawn from the parallel-stream, collector and virtual-thread examples used across Part 2 | `90-interview-basics.md` | `92-interview-internals.md` | 760 | written | 620 |
| 64 | `92-interview-internals.md` | 92 interview internals.md | Part 3 — INTERVIEW | — | 0 | Part 3 wrap-up: the summary table over the whole internals tier, 10 spoken-length Q&As, 5 predict-the-output puzzles | — | Puzzles drawn from the pipeline, record and pattern-switch internals examples used across Part 3 | `91-interview-intermediate.md` | `93-interview-build-it.md` | 760 | written | 720 |
| 65 | `93-interview-build-it.md` | 93 interview build it.md | Part 4 — INTERVIEW | — | 0 | Part 4 wrap-up: the summary table over every build, 10 spoken-length Q&As, 5 predict-the-output puzzles | — | Puzzles drawn from `MyStream`, `MyOptional` and the concurrency builds | `92-interview-internals.md` | `94-interview-questions-a.md` | 760 | written | 816 |
| 66 | `94-interview-questions-a.md` | 94 interview questions a.md | Part 5 — INTERVIEW | 5.1.1–5.1.32 | 32 | questions 5.1.1–5.1.32 with the full answer shape: functional interfaces, lambdas, method references, the stream model, laziness and the intermediate operations | — | Every answer grounded in the ledger, reservation and deposit examples the earlier files built | `93-interview-build-it.md` | `94-interview-questions-b.md` | 1008 | written | 1198 |
| 67 | `94-interview-questions-b.md` | 94 interview questions b.md | Part 5 — INTERVIEW | 5.1.33–5.1.64 | 32 | questions 5.1.33–5.1.64 with the full answer shape: reduction, parallel streams, spliterators, `Optional`, `var`, records | — | Every answer grounded in the collector, parallel-stream and record examples the earlier files built | `94-interview-questions-a.md` | `94-interview-questions-c.md` | 1008 | written | 1754 |
| 68 | `94-interview-questions-c.md` | 94 interview questions c.md | Part 5 — INTERVIEW | 5.1.65–5.1.95 | 31 | questions 5.1.65–5.1.95 with the full answer shape: sealed types, pattern matching, switch, text blocks, virtual threads, structured concurrency, sequenced collections | — | Every answer grounded in the `Verdict` hierarchy, the pinning JDBC driver and the assessment fan-out | `94-interview-questions-b.md` | `95-traps-drills-and-checklist.md` | 994 | written | 1504 |
| 69 | `95-traps-drills-and-checklist.md` | 95 traps drills and checklist.md | Part 5 — INTERVIEW | 5.2.1–5.2.5, 5.3.1–5.3.9 | 14 | the trap index; the version-stale claims table; the five most expensive mistakes and the five interview-losing answers; the seven drills and the spaced-repetition schedule; Part 5's own summary table, 10 Q&As and 5 puzzles; the flat atomic concept checklist | D-179, D-180, D-181, D-182 | The trap index rows cite the QuizStakes example each pitfall was argued on | `94-interview-questions-c.md` | — (last) | 900 | written | 2289 |

**Totals:** 69 files · 984 leaves · 182 diagram ids assigned · 27806 estimated lines.

---

## Diagram ownership

Each `D-NNN` is embedded at the point of explanation in the file below. A `table`-type id is
rendered as a Markdown table in that file and has no SVG; every other id is a standalone SVG in
`diagrams/D-NNN-short-slug.svg`.

| Id | Title | Type | SVG? | Owning file |
|---|---|---|---|---|
| D-001 | The release train and where 21 sits | timeline | yes | `platform-and-releases/01-basics.md` |
| D-002 | Three maturity ladders: preview, incubator, experimental | table | no — Markdown table | `platform-and-releases/01-basics.md` |
| D-003 | Class-file major versions and `UnsupportedClassVersionError` | table | no — Markdown table | `platform-and-releases/01-basics.md` |
| D-004 | `--release` restricts the API; `-source`/`-target` do not | before-after | yes | `platform-and-releases/01-basics.md` |
| D-005 | The six function shapes and their narrowings | hierarchy | yes | `functional-interfaces/01-basics.md` |
| D-006 | The 43 interfaces of `java.util.function` | table | no — Markdown table | `functional-interfaces/01-basics.md` |
| D-007 | `andThen` and `compose` run in opposite orders | step-sequence, 2 frames | yes | `functional-interfaces/01-basics.md` |
| D-008 | What counts toward the single abstract method | decision-tree | yes | `functional-interfaces/01-basics.md` |
| D-009 | Every lambda syntax form | table | no — Markdown table | `lambdas/01-basics.md` |
| D-010 | A lambda is a poly expression | before-after | yes | `lambdas/01-basics.md` |
| D-011 | `this` in a lambda versus an anonymous class | before-after | yes | `lambdas/01-basics.md` |
| D-012 | Capture is by value, and only of effectively-final locals | memory-layout | yes | `lambdas/01-basics.md` |
| D-013 | Which loop variable is capturable | before-after | yes | `lambdas/01-basics.md` |
| D-014 | Four ways to mutate from inside a lambda, and the one that is right | table | no — Markdown table | `lambdas/01-basics.md` |
| D-015 | The six method-reference forms | table | no — Markdown table | `method-references/01-basics.md` |
| D-016 | Unbound receiver becomes the first parameter | before-after | yes | `method-references/01-basics.md` |
| D-017 | A bound method reference evaluates its receiver at capture time | timeline | yes | `method-references/01-basics.md` |
| D-018 | Stream anatomy: source, intermediates, terminal | step-sequence, 3 frames | yes | `streams/01-basics-the-model.md` |
| D-019 | Fusion: one element through the whole chain | before-after | yes | `streams/01-basics-the-model.md` |
| D-020 | Laziness, statefulness and short-circuiting, per operation | table | no — Markdown table | `streams/01-basics-the-model.md` |
| D-021 | A stream is consumed once | state-transition | yes | `streams/01-basics-the-model.md` |
| D-022 | Which streams must be closed | decision-tree | yes | `streams/01-basics-the-model.md` |
| D-023 | The stream source catalogue | table | no — Markdown table | `streams/02-sources.md` |
| D-024 | `Stream.concat` in a loop builds a left-deep tree | before-after | yes | `streams/02-sources.md` |
| D-025 | Intermediate operation inventory | table | no — Markdown table | `streams/03-intermediate-operations.md` |
| D-026 | `map` vs `flatMap` vs `mapMulti` | step-sequence, 3 frames | yes | `streams/03-intermediate-operations.md` |
| D-027 | `takeWhile` is a prefix, `filter` is a test | before-after | yes | `streams/03-intermediate-operations.md` |
| D-028 | Why `peek` may never run | flowchart | yes | `streams/03-intermediate-operations.md` |
| D-029 | Operation order changes both the answer and the cost | before-after | yes | `streams/03-intermediate-operations.md` |
| D-030 | `sorted()` is a barrier | step-sequence, 3 frames | yes | `streams/03-intermediate-operations.md` |
| D-031 | Terminal operation inventory | table | no — Markdown table | `streams/04-terminal-operations.md` |
| D-032 | The three `reduce` overloads | table | no — Markdown table | `streams/04-terminal-operations.md` |
| D-033 | What a non-associative reduce does in parallel | step-sequence, 3 frames | yes | `streams/04-terminal-operations.md` |
| D-034 | `findFirst` versus `findAny` in parallel | before-after | yes | `streams/04-terminal-operations.md` |
| D-035 | Null policy across the list-producing paths | table | no — Markdown table | `streams/04-terminal-operations.md` |
| D-036 | The four stream shapes and the conversions between them | hierarchy | yes | `streams/05-primitive-streams.md` |
| D-037 | `int[]` versus `List<Integer>` for 2.8M stake amounts | memory-layout | yes | `streams/05-primitive-streams.md` |
| D-038 | `IntStream.sum()` overflows silently | step-sequence, 3 frames | yes | `streams/05-primitive-streams.md` |
| D-039 | The `Collector` contract's five functions | step-sequence, 4 frames | yes | `collectors/01-basics-a.md` |
| D-040 | Collector inventory | table | no — Markdown table | `collectors/01-basics-a.md` |
| D-041 | What `groupingBy` actually returns | memory-layout | yes | `collectors/01-basics-b.md` |
| D-042 | `partitioningBy` always has both keys | before-after | yes | `collectors/01-basics-b.md` |
| D-043 | The three conditions for a concurrent reduction | decision-tree | yes | `collectors/01-basics-b.md` |
| D-044 | Why `collect(toList())` is safe in parallel and `forEach(list::add)` is not | before-after | yes | `collectors/01-basics-b.md` |
| D-045 | `Optional`'s API by version | table | no — Markdown table | `optional/01-basics.md` |
| D-046 | `orElse` evaluates eagerly even when the value is present | step-sequence, 2 frames | yes | `optional/01-basics.md` |
| D-047 | Where `Optional` belongs | decision-tree | yes | `optional/01-basics.md` |
| D-048 | The `Optional` chain versus the null check | before-after | yes | `optional/01-basics.md` |
| D-049 | Where `var` is legal and where it is not | table | no — Markdown table | `var/01-basics.md` |
| D-050 | `var` plus the diamond infers `Object` | before-after | yes | `var/01-basics.md` |
| D-051 | What a record generates | before-after | yes | `records/01-basics-a.md` |
| D-052 | The compact constructor desugars | before-after | yes | `records/01-basics-a.md` |
| D-053 | A record is shallowly immutable | step-sequence, 3 frames | yes | `records/01-basics-b.md` |
| D-054 | An array component breaks `equals` | before-after | yes | `records/01-basics-b.md` |
| D-055 | The record cliff | decision-tree | yes | `records/01-basics-b.md` |
| D-056 | A sealed hierarchy | hierarchy | yes | `sealed-types/01-basics.md` |
| D-057 | Every permitted subtype must choose one of three modifiers | decision-tree | yes | `sealed-types/01-basics.md` |
| D-058 | Sealed interface vs enum vs open polymorphism | table | no — Markdown table | `sealed-types/01-basics.md` |
| D-059 | Sealing is a module/package boundary | before-after | yes | `sealed-types/01-basics.md` |
| D-060 | A pattern is a test, an extraction and a binding | before-after | yes | `pattern-matching/01-basics.md` |
| D-061 | Flow scoping is not a block rule | flowchart | yes | `pattern-matching/01-basics.md` |
| D-062 | How a pattern switch routes a value, including null | flowchart | yes | `pattern-matching/01-basics.md` |
| D-063 | Dominance and label order | before-after | yes | `pattern-matching/01-basics.md` |
| D-064 | Nested record deconstruction | hierarchy | yes | `pattern-matching/01-basics.md` |
| D-065 | The pattern-matching lineage | timeline | yes | `pattern-matching/01-basics.md` |
| D-066 | Switch forms compared | table | no — Markdown table | `switch/01-basics.md` |
| D-067 | Fall-through, and how the arrow form makes it unwritable | before-after | yes | `switch/01-basics.md` |
| D-068 | Exhaustive enum switch expression versus one with `default` | before-after | yes | `switch/01-basics.md` |
| D-069 | The three text-block compile steps, in order | step-sequence, 3 frames | yes | `text-blocks/01-basics.md` |
| D-070 | How incidental whitespace is computed | step-sequence, 4 frames | yes | `text-blocks/01-basics.md` |
| D-071 | Moving the closing delimiter changes the string | before-after | yes | `text-blocks/01-basics.md` |
| D-072 | `\s` as a trailing-space fence | before-after | yes | `text-blocks/01-basics.md` |
| D-073 | Platform thread versus virtual thread | memory-layout | yes | `virtual-threads/01-basics.md` |
| D-074 | Mounting and unmounting | step-sequence, 4 frames | yes | `virtual-threads/01-basics.md` |
| D-075 | The carrier pool | memory-layout | yes | `virtual-threads/01-basics.md` |
| D-076 | Little's law sets the thread count | cost-curve | yes | `virtual-threads/01-basics.md` |
| D-077 | Pinning on Java 21 | before-after | yes | `virtual-threads/01-basics.md` |
| D-078 | The virtual-thread creation API | table | no — Markdown table | `virtual-threads/01-basics.md` |
| D-079 | What a virtual thread refuses to do | table | no — Markdown table | `virtual-threads/01-basics.md` |
| D-080 | A structured task scope is a tree | hierarchy | yes | `structured-concurrency/01-basics.md` |
| D-081 | `ShutdownOnFailure` versus `CompletableFuture.allOf` | timeline | yes | `structured-concurrency/01-basics.md` |
| D-082 | `ShutdownOnSuccess` as a hedge | timeline | yes | `structured-concurrency/01-basics.md` |
| D-083 | `Subtask` states and the illegal calls | state-transition | yes | `structured-concurrency/01-basics.md` |
| D-084 | Sequenced collections and the retrofit | hierarchy | yes | `library-additions/01-basics.md` |
| D-085 | `reversed()` is a view | before-after | yes | `library-additions/01-basics.md` |
| D-086 | Library additions by release, 9 → 21 | table | no — Markdown table | `library-additions/01-basics.md` |
| D-087 | The master stream cost table | table | no — Markdown table | `cost-model/02-master-tables.md` |
| D-088 | Feature by version, with its JEP and its trap | table | no — Markdown table | `cost-model/02-master-tables.md` |
| D-089 | Lambda vs method reference vs anonymous class vs inner class | table | no — Markdown table | `cost-model/02-master-tables.md` |
| D-090 | Six ways to say "absent" | table | no — Markdown table | `cost-model/02-master-tables.md` |
| D-091 | Five ways to carry data | table | no — Markdown table | `cost-model/02-master-tables.md` |
| D-092 | Four concurrency models | table | no — Markdown table | `cost-model/02-master-tables.md` |
| D-093 | Seven ways to get a `List` | table | no — Markdown table | `cost-model/02-master-tables.md` |
| D-094 | The first call to a lambda call site | timeline | yes | `lambdas/02-cost-and-choice.md` |
| D-095 | Monomorphic versus megamorphic lambda call sites | before-after | yes | `lambdas/02-cost-and-choice.md` |
| D-096 | What exists before the first element moves | memory-layout | yes | `streams/06-cost-model.md` |
| D-097 | `sorted().findFirst()` versus `min(comparator)` | cost-curve | yes | `streams/06-cost-model.md` |
| D-098 | Stream or loop | decision-tree | yes | `streams/06-cost-model.md` |
| D-099 | One blocking parallel stream starves the whole JVM | before-after | yes | `streams/07-parallel-streams.md` |
| D-100 | Source splitting quality, ranked | table | no — Markdown table | `streams/07-parallel-streams.md` |
| D-101 | `parallelStream().forEach(list::add)` corrupts the list | step-sequence, 3 frames | yes | `streams/07-parallel-streams.md` |
| D-102 | Where parallel starts paying | cost-curve | yes | `streams/07-parallel-streams.md` |
| D-103 | `filtering(p, toList())` versus `filter(p)` before `groupingBy` | before-after | yes | `collectors/02-in-anger.md` |
| D-104 | A top-N collector's combiner | step-sequence, 3 frames | yes | `collectors/02-in-anger.md` |
| D-105 | `orElse` vs `orElseGet` vs `orElseThrow` | table | no — Markdown table | `optional/02-discipline.md` |
| D-106 | Four absence strategies compared | table | no — Markdown table | `optional/02-discipline.md` |
| D-107 | A `var` policy you can defend in review | decision-tree | yes | `var/02-in-practice.md` |
| D-108 | Records across the framework boundary | table | no — Markdown table | `records/02-in-practice.md` |
| D-109 | Defensive copying, in and out | before-after | yes | `records/02-in-practice.md` |
| D-110 | Sum of products | hierarchy | yes | `sealed-types/02-data-oriented-programming.md` |
| D-111 | Visitor versus sealed interface plus pattern switch | before-after | yes | `sealed-types/02-data-oriented-programming.md` |
| D-112 | The expression problem | table | no — Markdown table | `sealed-types/02-data-oriented-programming.md` |
| D-113 | Refactoring an `instanceof` chain into a pattern switch | step-sequence, 4 frames | yes | `pattern-matching/02-in-anger.md` |
| D-114 | Exhaustiveness drift after a partial redeploy | timeline | yes | `pattern-matching/02-in-anger.md` |
| D-115 | Text block, resource file, or constant | decision-tree | yes | `text-blocks/02-in-practice.md` |
| D-116 | A Spring Boot request path, before and after virtual threads | before-after | yes | `virtual-threads/02-in-production.md` |
| D-117 | The bottleneck moves downstream | before-after | yes | `virtual-threads/02-in-production.md` |
| D-118 | A pinning JDBC driver under load | step-sequence, 3 frames | yes | `virtual-threads/02-in-production.md` |
| D-119 | What to measure once threads are free | table | no — Markdown table | `virtual-threads/02-in-production.md` |
| D-120 | A fan-out with one deadline | timeline | yes | `structured-concurrency/02-in-practice.md` |
| D-121 | Scoped-value bindings versus a `ThreadLocal` map | before-after | yes | `structured-concurrency/02-in-practice.md` |
| D-122 | What breaks at each release, 9 → 21 | timeline | yes | `platform-and-releases/02-migration.md` |
| D-123 | The safe upgrade order | flowchart | yes | `platform-and-releases/02-migration.md` |
| D-124 | The which-construct index | table | no — Markdown table | `which-construct/02-which-construct.md` |
| D-125 | How `javac` desugars a lambda | step-sequence, 3 frames | yes | `lambdas/03-internals-translation.md` |
| D-126 | Reading a `BootstrapMethods` entry | memory-layout | yes | `lambdas/03-internals-translation.md` |
| D-127 | Non-capturing versus capturing at link time | before-after | yes | `lambdas/03-internals-translation.md` |
| D-128 | A method reference has no `lambda$` method | before-after | yes | `lambdas/03-internals-translation.md` |
| D-129 | `FLAG_SERIALIZABLE` and the serializable-lambda path | flowchart | yes | `lambdas/03-internals-translation.md` |
| D-130 | A captured `this` keeps the enclosing object alive | memory-layout | yes | `lambdas/04-internals-capture-and-identity.md` |
| D-131 | The pipeline as a doubly linked list of stages | memory-layout | yes | `streams/08-internals-pipeline.md` |
| D-132 | `wrapSink` walks backwards | step-sequence, 4 frames | yes | `streams/08-internals-pipeline.md` |
| D-133 | `StreamOpFlag` | table | no — Markdown table | `streams/08-internals-pipeline.md` |
| D-134 | How `count()` bypasses the pipeline | flowchart | yes | `streams/08-internals-pipeline.md` |
| D-135 | The eight spliterator characteristics | table | no — Markdown table | `streams/09-internals-spliterator.md` |
| D-136 | `trySplit` returns the prefix | step-sequence, 3 frames | yes | `streams/09-internals-spliterator.md` |
| D-137 | `SIZED` but not `SUBSIZED` | before-after | yes | `streams/09-internals-spliterator.md` |
| D-138 | Why an `Iterator`-derived stream parallelises badly | step-sequence, 3 frames | yes | `streams/09-internals-spliterator.md` |
| D-139 | The parallel task tree | hierarchy | yes | `streams/10-internals-parallel-execution.md` |
| D-140 | The combine tree costs O(n) overall | step-sequence, 3 frames | yes | `streams/10-internals-parallel-execution.md` |
| D-141 | `ForEachTask` versus `ForEachOrderedTask` | before-after | yes | `streams/10-internals-parallel-execution.md` |
| D-142 | Work stealing in the common pool | memory-layout | yes | `streams/10-internals-parallel-execution.md` |
| D-143 | `CollectorImpl` and its pre-built characteristic sets | table | no — Markdown table | `collectors/03-internals-collectors.md` |
| D-144 | Kahan compensated summation inside `summingDouble` | step-sequence, 3 frames | yes | `collectors/03-internals-collectors.md` |
| D-145 | `IDENTITY_FINISH` skips a whole pass | before-after | yes | `collectors/03-internals-collectors.md` |
| D-146 | Inside `Optional` | memory-layout | yes | `optional/03-internals-optional.md` |
| D-147 | Upward projection | step-sequence, 3 frames | yes | `var/03-internals-inference.md` |
| D-148 | Where `var` leaves a trace in the class file | before-after | yes | `var/03-internals-inference.md` |
| D-149 | The `Record` class-file attribute | memory-layout | yes | `records/03-internals-records.md` |
| D-150 | `ObjectMethods.bootstrap` behind `equals`, `hashCode` and `toString` | flowchart | yes | `records/03-internals-records.md` |
| D-151 | Record deserialization runs the canonical constructor | before-after | yes | `records/03-internals-records.md` |
| D-152 | `PermittedSubclasses` is enforced at load time | step-sequence, 3 frames | yes | `sealed-types/03-internals-sealed.md` |
| D-153 | A pattern switch compiles to `typeSwitch` plus `tableswitch` | step-sequence, 4 frames | yes | `pattern-matching/03-internals-pattern-matching.md` |
| D-154 | Record deconstruction is accessor calls in order | step-sequence, 3 frames | yes | `pattern-matching/03-internals-pattern-matching.md` |
| D-155 | `tableswitch` versus `lookupswitch` | before-after | yes | `switch/03-internals-switch-compilation.md` |
| D-156 | `$SwitchMap` protects a separately compiled enum switch | before-after | yes | `switch/03-internals-switch-compilation.md` |
| D-157 | The synthetic default in an exhaustive enum switch expression | before-after | yes | `switch/03-internals-switch-compilation.md` |
| D-158 | A text block is a constant, folded at compile time | before-after | yes | `text-blocks/03-internals-compilation.md` |
| D-159 | The three layers of a virtual thread | hierarchy | yes | `virtual-threads/03-internals-virtual-threads.md` |
| D-160 | Stack chunks live on the heap | memory-layout | yes | `virtual-threads/03-internals-virtual-threads.md` |
| D-161 | `VirtualThread`'s state machine | state-transition | yes | `virtual-threads/03-internals-virtual-threads.md` |
| D-162 | FIFO for virtual threads, LIFO for parallel streams | before-after | yes | `virtual-threads/03-internals-virtual-threads.md` |
| D-163 | Pinning is a property of the continuation | before-after | yes | `virtual-threads/03-internals-virtual-threads.md` |
| D-164 | Scoped values and structured concurrency are one mechanism | hierarchy | yes | `structured-concurrency/03-internals.md` |
| D-165 | Structured concurrency and scoped values, release by release | table | no — Markdown table | `structured-concurrency/03-internals.md` |
| D-166 | The consolidated feature → version table | table | no — Markdown table | `platform-and-releases/03-internals-version-delta.md` |
| D-167 | The consolidated removed-or-disabled table | table | no — Markdown table | `platform-and-releases/03-internals-version-delta.md` |
| D-168 | The tooling map for this topic | table | no — Markdown table | `platform-and-releases/04-internals-observability.md` |
| D-169 | What a stream stack trace actually looks like | before-after | yes | `streams/06-cost-model.md` |
| D-170 | Where the JIT can and cannot help | table | no — Markdown table | `lambdas/02-cost-and-choice.md` |
| D-171 | `MyStream`'s sink chain next to the JDK's | before-after | yes | `build-it/02-mystream.md` |
| D-172 | Proving fusion with a print in every stage | step-sequence, 3 frames | yes | `build-it/02-mystream.md` |
| D-173 | Platform threads versus virtual threads on the echo server | cost-curve | yes | `build-it/05-concurrency-builds.md` |
| D-174 | The pinning reproducer, before and after | before-after | yes | `build-it/05-concurrency-builds.md` |
| D-175 | The orphan that `allOf` leaves behind | before-after | yes | `build-it/05-concurrency-builds.md` |
| D-176 | Common-pool starvation, reproduced | timeline | yes | `build-it/05-concurrency-builds.md` |
| D-177 | Hand-rolled batching versus `Gatherers.windowFixed` | before-after | yes | `build-it/06-filling-the-21-gaps.md` |
| D-178 | The fifteen puzzlers and their mechanisms | table | no — Markdown table | `build-it/07-diagnostic-harnesses.md` |
| D-179 | The trap index | table | no — Markdown table | `95-traps-drills-and-checklist.md` |
| D-180 | The version-stale claims table | table | no — Markdown table | `95-traps-drills-and-checklist.md` |
| D-181 | The numbers card | table | no — Markdown table | `95-traps-drills-and-checklist.md` |
| D-182 | The spaced-repetition schedule | timeline | yes | `95-traps-drills-and-checklist.md` |

### Substitutions and frame splits

No `D-NNN` was reported unrenderable, so there are no table substitutions. Four manifest ids
called for a frame series and were authored as one file per frame, which the diagram spec
permits. The owning file embeds **every** frame file listed here, in order:

| Manifest id | Authored as | Frames |
|---|---|---|
| D-018 | `D-018a-…`, `D-018b-…`, `D-018c-…` | 3 |
| D-038 | `D-038a-…`, `D-038b-…`, `D-038c-…` | 3 |
| D-039 | `D-039a-…`, `D-039b-…`, `D-039c-…`, `D-039d-…` | 4 |
| D-046 | `D-046a-…`, `D-046b-…` | 2 |

---

## Diagram manifest (from the prompt, verbatim)

Reproduced so a resumed run never needs the prompt to know what a `D-NNN` depicts.

## Part 1 diagrams

| # | Diagram | Syllabus leaf | Type | Must show |
|---|---|---|---|---|
| D-001 | The release train and where 21 sits | 1.1.1–1.1.3 | timeline | A horizontal axis from Java 8 (March 2014) to Java 25 with a tick every six months; LTS releases 8, 11, 17, 21, 25 as taller marks with their dates; the six-month cadence labelled "JEP 322"; the features this guide owns pinned to their final release (lambdas/streams 8, `var` 10, switch expressions 14, text blocks 15, records 16, sealed 17, pattern switch and virtual threads and record patterns 21, gatherers 24, scoped values 25) |
| D-002 | Three maturity ladders: preview, incubator, experimental | 1.1.5–1.1.7 | table | Rows: preview language/API feature, incubator module, experimental VM option. Columns: how you enable it (`--enable-preview` at compile *and* run, `--add-modules jdk.incubator.x`, `-XX:+UnlockExperimentalVMOptions`), what the class file records (minor version 65535 for preview, nothing for the others), whether it runs on a *different* release, and the guide's example of each (structured concurrency 21, Vector API 21, generational ZGC 21) |
| D-003 | Class-file major versions and `UnsupportedClassVersionError` | 1.1.10 | table | Rows for Java 8/9/11/17/21/25 with major versions 52/53/55/61/65/69; a column showing the exact `UnsupportedClassVersionError` text for a class compiled at 65 run on a 55 JVM, with both numbers highlighted; a final column giving the `java -version`/`Runtime.version()` check |
| D-004 | `--release` restricts the API; `-source`/`-target` do not | 1.1.9 | before-after | Left: `javac -source 8 -target 8` on `BalanceView` calling `List.of(...)` — compiles clean, then `NoSuchMethodError` at runtime on a Java 8 JVM, with the error text. Right: `javac --release 8` on the same source — a compile error naming `List.of` as not available at release 8. Label which of the two the build should use |
| D-005 | The six function shapes and their narrowings | 1.2.8, 1.2.9 | hierarchy | `Function<T,R>`, `BiFunction<T,U,R>`, `Predicate<T>`, `Consumer<T>`, `Supplier<T>` as roots; `UnaryOperator<T> extends Function<T,T>` and `BinaryOperator<T> extends BiFunction<T,T,T>` drawn as arrows to their parents; each box carries its abstract method signature and one QuizStakes instantiation (`Function<LedgerEntry, Money>`, `Predicate<Restriction>`, `Supplier<IdempotencyKey>`) |
| D-006 | The 43 interfaces of `java.util.function` | 1.2.7, 1.2.13 | table | Every one of the 43 names grouped by shape family (Function, BiFunction, Predicate, Consumer, Supplier, Operator) with columns for the object form and each primitive specialisation (`IntX`, `LongX`, `DoubleX`, `ToIntX`, `XToYFunction`, `ObjIntConsumer`, `BooleanSupplier`). The total 43 stated in the caption |
| D-007 | `andThen` and `compose` run in opposite orders | 1.2.11 | step-sequence, 2 frames | One `Function<Money, Money> applyFee` and one `Function<Money, Money> applyRounding` over a 3.33 stake. Frame 1: `applyFee.andThen(applyRounding)` — arrows showing fee first, then rounding, with the intermediate value. Frame 2: `applyFee.compose(applyRounding)` — rounding first, then fee, with a different intermediate and a different result. Both final values printed |
| D-008 | What counts toward the single abstract method | 1.2.1–1.2.5 | decision-tree | Root: "is this method abstract?" Branches: overrides a public `Object` method (`equals`, `hashCode`, `toString`) → does not count, with `Comparator` named; `default`/`static`/`private` → does not count; declares its own type parameters → counts but makes the interface unusable as a lambda target; otherwise → counts. Leaf boxes state "functional" / "not functional" / "functional but not lambda-implementable" |
| D-009 | Every lambda syntax form | 1.3.1–1.3.4, 1.3.20 | table | Rows: `() -> expr`, `x -> expr`, `(x, y) -> expr`, `(Type x) -> {...}`, `(var x) -> ...`, `(final @NonNull var x) -> ...`, block body with `return`. Columns: since which release, parameter typing (implicit/explicit/`var`), whether mixing is allowed, and a QuizStakes example for each |
| D-010 | A lambda is a poly expression | 1.3.5–1.3.8 | before-after | The same source text `r -> r.amount().compareTo(MAX_STAKE) > 0` used at three sites with three different target types (`Predicate<Reservation>`, a custom `StakeRule`, a `Function<Reservation, Boolean>` that does *not* compile). Beside them: `Object o = () -> {};` marked "compile error: target type is not a functional interface" and `Object o = (Runnable) () -> {};` marked "compiles". Each site annotated with the target type that supplied the interface |
| D-011 | `this` in a lambda versus an anonymous class | 1.3.10, 1.3.11 | before-after | The same `Runnable` registered from inside `BonusService`, written twice. Left, anonymous class: `this` points at the anonymous instance, plus a synthetic `this$0` arrow to `BonusService`; generated name `BonusService$1`. Right, lambda: `this` points straight at the `BonusService` instance, no extra object; synthetic method `lambda$register$0`. Both arrows labelled |
| D-012 | Capture is by value, and only of effectively-final locals | 1.3.13, 3.2.1–3.2.3 | memory-layout | A stack frame for `FundsLedger.reserveStake` holding `Money stake` (effectively final) and `this`; the spun lambda object on the heap with one field per captured value; an arrow from the field to the same `Money` object. A second panel: an instance field `dailyTotal` read inside the lambda — no field copy, only a `this` capture, so a later write to `dailyTotal` *is* visible. Both cases annotated with "copied at capture" / "read through `this` at invocation" |
| D-013 | Which loop variable is capturable | 1.3.15 | before-after | Left: `for (int i = 0; i < 3; i++)` — one variable, reassigned, so `i` is not effectively final and the lambda does not compile; the single slot drawn once with three values over time. Right: `for (Reservation r : reservations)` — a fresh variable per iteration, three separate slots, three lambdas each capturing its own. The compile error text quoted on the left |
| D-014 | Four ways to mutate from inside a lambda, and the one that is right | 1.3.14 | table | Rows: one-element array hack, `AtomicInteger`, `reduce`, a collector, a plain loop. Columns: compiles, thread-safe in parallel, allocation cost, readability, verdict. The QuizStakes case is counting reservations over `STAKE_BLOCKED` clients |
| D-015 | The six method-reference forms | 1.4.1–1.4.7 | table | Rows: `Type::staticMethod`, `instance::method`, `Type::instanceMethod`, `Type::new`, `String[]::new`, `super::method`, `Outer.this::method`. Columns: the equivalent lambda written out, what the receiver is, when the receiver is evaluated, and a QuizStakes example (`Money::of`, `ledger::append`, `Reservation::amount`, `StakeSplit::new`) |
| D-016 | Unbound receiver becomes the first parameter | 1.4.4 | before-after | Left: `Reservation::amount` as a `Function<Reservation, Money>` — the arrow showing the stream element becoming the receiver. Right: the equivalent lambda `r -> r.amount()` with the same arrow. A third panel shows `Money::compareTo` as a `Comparator`-shaped two-argument function, first argument receiver, second argument parameter |
| D-017 | A bound method reference evaluates its receiver at capture time | 1.4.10, 1.4.11 | timeline | Three points on one axis: (1) `Runnable r = ledger::flush` evaluates `ledger` now and stores the reference; (2) `ledger = otherLedger` reassigns the *variable*, not the captured value; (3) `r.run()` still calls `flush` on the original object. A second lane repeats it with `ledger = null` before the reference is created, and the NPE thrown at point (1) with nothing ever invoked |
| D-018 | Stream anatomy: source, intermediates, terminal | 1.5.3, 1.5.4 | step-sequence, 3 frames | A pipeline over 95k card deposits: `deposits.stream().filter(...).map(...).collect(toList())`. Frame 1: the source `Spliterator` bound. Frame 2: two stage objects created, nothing traversed, "0 elements have moved" labelled. Frame 3: the terminal operation triggers traversal. Each frame lists which objects exist so far |
| D-019 | Fusion: one element through the whole chain | 1.5.5, 3.3.11 | before-after | Left, the wrong mental model: three passes over the whole collection with two intermediate lists materialised, sizes labelled. Right, the real model: one element at a time entering `filter`, then `map`, then the collector, with a numbered trace for the first three deposits (65, 480, 65) and no intermediate collection anywhere |
| D-020 | Laziness, statefulness and short-circuiting, per operation | 1.5.4, 1.5.6, 1.5.7, 1.7.18, 1.7.19 | table | One row per intermediate operation. Columns: lazy (always yes), stateless/stateful, short-circuiting, buffering required, encounter-order sensitive. A second block does terminal operations with eager/lazy and short-circuiting |
| D-021 | A stream is consumed once | 1.5.13, 3.3.12 | state-transition | Three states — unconsumed, linked (an intermediate op attached), consumed/closed — with the transitions labelled by the call that causes them and the two exact exception messages on the illegal edges: `"stream has already been operated upon or closed"` and `"source already consumed or closed"` |
| D-022 | Which streams must be closed | 1.5.14, 1.5.15, 1.6.10 | decision-tree | Root: "does the source hold an OS resource?" Yes branch lists `Files.lines`, `Files.walk`, `Files.list`, `Files.find`, `Files.newDirectoryStream` → try-with-resources required, with the file-descriptor leak as the symptom. No branch lists `Collection.stream`, `Arrays.stream`, `IntStream.range` → closing is a no-op. `onClose(Runnable)` shown on the yes branch |
| D-023 | The stream source catalogue | 1.6.1–1.6.17 | table | One row per source. Columns: since which release, finite/infinite, ordered, `SIZED`/`SUBSIZED`, split quality (excellent/good/serial), needs closing, and the QuizStakes use (`ledgerEntries.stream()`, `IntStream.range(0, 2_800_000)`, `Files.lines(paymentRunFile)`) |
| D-024 | `Stream.concat` in a loop builds a left-deep tree | 1.6.7 | before-after | Left: five successive `concat` calls drawn as a left-leaning binary tree five levels deep, with the recursion depth labelled and `StackOverflowError` at traversal. Right: the same five sources collected into a `List` and flat-mapped, one level deep. Depths written on both |
| D-025 | Intermediate operation inventory | 1.7.24 | table | One row per intermediate operation (`filter`, `map`, the four `mapToX`, `boxed`, `flatMap`, the three `flatMapToX`, `mapMulti` and its three primitive forms, `distinct`, `sorted` ×2, `limit`, `skip`, `takeWhile`, `dropWhile`, `peek`, `parallel`, `sequential`, `unordered`, `onClose`). Columns: version added, stateful, short-circuiting, and its effect (SET/CLEAR/PRESERVE) on each of `SIZED`, `ORDERED`, `DISTINCT`, `SORTED` |
| D-026 | `map` vs `flatMap` vs `mapMulti` | 1.7.2, 1.7.4, 1.7.6, 1.7.7 | step-sequence, 3 frames | The same input of three `Movement`s each holding zero, one or three `LedgerEntry` values. Frame 1: `map` produces three `List`s — cardinality 1:1. Frame 2: `flatMap` allocates one inner `Stream` per element and flattens — the three allocations drawn explicitly. Frame 3: `mapMulti` pushes into a `Consumer` with zero allocations — the same output. Allocation counts written on each frame |
| D-027 | `takeWhile` is a prefix, `filter` is a test | 1.7.13 | before-after | The same ordered input of stake amounts `[4.20, 3.33, 12.00, 2.10, 1.05]` with the predicate `amount < 5`. Left, `filter`: output `[4.20, 3.33, 2.10, 1.05]`, every element tested. Right, `takeWhile`: output `[4.20, 3.33]`, traversal stops at 12.00 — the stop point marked and the untested elements greyed with a label |
| D-028 | Why `peek` may never run | 1.7.16, 3.3.14, 3.3.15 | flowchart | Decision nodes for `count()`: is `SIZED` still set? did any stateful op clear it? does anything short-circuit? If all clear, the answer comes from the source's size and the sink chain is never built — the `peek` consumer boxed and marked "never called". A parallel branch shows the same pipeline with a `filter` added, clearing `SIZED`, and `peek` running. A VERSION TRAP banner: always ran before Java 9 |
| D-029 | Operation order changes both the answer and the cost | 1.7.20, 2.3.8 | before-after | Left: `.sorted(byAmount).limit(10)` over 2.8M stake reservations — the full buffer and sort drawn, cost O(n log n), elements buffered = 2.8M. Right: `.limit(10).sorted(byAmount)` — a different answer, the ten elements shown. A third panel: `filter` before `map` versus after, with the number of mapper invocations counted for both |
| D-030 | `sorted()` is a barrier | 1.7.9, 1.7.10 | step-sequence, 3 frames | Frame 1: elements streaming into `sorted` and accumulating in its buffer, downstream stages idle. Frame 2: source exhausted, TimSort runs over the full buffer. Frame 3: elements released downstream. A side panel: a non-`Comparable` element producing `ClassCastException` at frame 2 — i.e. at terminal time, not at the `sorted()` call site |
| D-031 | Terminal operation inventory | 1.8.26 | table | One row per terminal operation. Columns: version added, return type, eager or lazy, short-circuiting, parallel-friendly, ordering-sensitive, returns `Optional` and why |
| D-032 | The three `reduce` overloads | 1.8.6–1.8.8 | table | Rows: `reduce(BinaryOperator)`, `reduce(identity, BinaryOperator)`, `reduce(identity, accumulator, combiner)`. Columns: return type, what the empty stream yields, the contracts you must satisfy (identity, associativity, compatibility of accumulator and combiner), and the QuizStakes example (summing `Money` over a day's 95k deposits) |
| D-033 | What a non-associative reduce does in parallel | 1.8.9, 1.8.10 | step-sequence, 3 frames | Subtraction over `[65, 480, 42, 180]`. Frame 1: the sequential left fold with its result. Frame 2: the same operator split across two leaves and combined, with the different result written out. Frame 3: the same argument for string concatenation with a non-identity seed. Both wrong answers and the correct sequential answers labelled |
| D-034 | `findFirst` versus `findAny` in parallel | 1.8.14, 1.8.15, 3.5.7 | before-after | A four-leaf task tree over 2.8M reservations. Left, `findAny`: the first leaf to succeed wins and the rest cancel — no coordination arrows. Right, `findFirst`: leaves must report in encounter order, so later leaves' results are held until earlier leaves resolve — the coordination arrows drawn and labelled with the cost |
| D-035 | Null policy across the list-producing paths | 1.8.25, 2.1.7, 2.5.11 | table | Rows: `Stream` elements, `Stream.toList()`, `Collectors.toList()`, `Collectors.toUnmodifiableList()`, `Collectors.toMap` key, `Collectors.toMap` value, `List.of`, `List.copyOf`, `Arrays.asList`, `new ArrayList<>()`. Columns: nulls permitted, mutable, structurally modifiable, `set` in place, exception thrown on violation |
| D-036 | The four stream shapes and the conversions between them | 1.9.1, 1.9.3, 1.9.4, 1.7.3 | hierarchy | Four boxes — `Stream<T>`, `IntStream`, `LongStream`, `DoubleStream` — with every conversion arrow labelled by its method (`mapToInt`, `mapToObj`, `boxed`, `asLongStream`, `asDoubleStream`, `mapToLong`, `mapToDouble`). A note box: no `CharStream`, `BooleanStream` or `FloatStream`, and which primitives widen into which |
| D-037 | `int[]` versus `List<Integer>` for 2.8M stake amounts | 1.9.14, 1.9.10 | memory-layout | Top: `int[] stakeMinorUnits = new int[2_800_000]` — 16-byte header plus 11.2 MB contiguous. Bottom: the boxed equivalent — a 24-byte list, a 16-byte array header, 11.2 MB of 4-byte references, and 2.8M × 16-byte `Integer` objects. Both totals and the ratio written out |
| D-038 | `IntStream.sum()` overflows silently | 1.9.11 | step-sequence, 3 frames | Summing 2.8M stake amounts in minor units. Frame 1: the running `int` total approaching 2 147 483 647. Frame 2: the wrap to a negative value, with the exact arithmetic. Frame 3: `mapToLong(i -> i).sum()` producing the correct total. All three totals printed |
| D-039 | The `Collector` contract's five functions | 1.10.1, 1.10.2, 3.6.1 | step-sequence, 4 frames | A `groupingBy(deposit -> deposit.rail(), counting())` over card and bank deposits. Frame 1: `supplier()` creates the container. Frame 2: `accumulator()` folds each element in. Frame 3: `combiner()` merges two containers in the parallel case. Frame 4: `finisher()` transforms to the result type, with `IDENTITY_FINISH` shown as the skip path. The three `Characteristics` values listed in a legend |
| D-040 | Collector inventory | 1.10.29, 1.10.3 | table | One row per collector factory across all 30 names and 54 overloads. Columns: version added, result type, mutability of the result, null policy, characteristics, parallel behaviour, and the one trap if it has one |
| D-041 | What `groupingBy` actually returns | 1.10.17, 1.10.18, 3.6.5 | memory-layout | The result of `groupingBy(Deposit::rail, mapping(Deposit::amount, toList()))` over card and bank deposits: a `HashMap` with its bucket table, two entries, each value an `ArrayList`. Both concrete types labelled "not guaranteed by the contract", with `TreeMap::new` and `LinkedHashMap::new` drawn as the ordered alternatives |
| D-042 | `partitioningBy` always has both keys | 1.10.21 | before-after | Over an empty stream of reservations. Left, `groupingBy(r -> r.amount().compareTo(MAX) > 0)`: an empty map, `get(true)` returns null. Right, `partitioningBy(...)`: a two-entry map with `false → []` and `true → []`. The NPE the left produces on unboxing drawn as the consequence |
| D-043 | The three conditions for a concurrent reduction | 1.10.25, 1.10.20, 2.4.13 | decision-tree | Root: `collect` called. Node 1: is the stream parallel? Node 2: is the collector `CONCURRENT`? Node 3: is the stream unordered *or* the collector `UNORDERED`? All three yes → one shared container, no combiner. Any no → per-leaf containers and a combiner tree. Both outcomes drawn with their container counts |
| D-044 | Why `collect(toList())` is safe in parallel and `forEach(list::add)` is not | 1.10.26, 2.4.11, 2.4.12 | before-after | Left: four leaves each with their own `ArrayList`, merged pairwise up a combiner tree — no shared state, arrows labelled with sizes. Right: four leaves all calling `add` on one `ArrayList`, with the three observable symptoms named: lost elements, interspersed nulls, and `ArrayIndexOutOfBoundsException` from inside `ArrayList.add` |
| D-045 | `Optional`'s API by version | 1.11.5–1.11.10 | table | One row per method across all 20. Columns: signature, release added (15 at 1.8, `ifPresentOrElse`/`or`/`stream` at 9, `orElseThrow()` at 10, `isEmpty` at 11), eager or lazy in its argument, what it does on empty, and whether it is on `OptionalInt`/`OptionalLong`/`OptionalDouble` too |
| D-046 | `orElse` evaluates eagerly even when the value is present | 1.11.11, 2.6.3 | step-sequence, 2 frames | A `findClient(id)` returning a present `Optional`. Frame 1: `orElse(loadDefaultFromDatabase())` — the database call runs first, its result is discarded, with a call counter showing 1. Frame 2: `orElseGet(this::loadDefaultFromDatabase)` — the supplier is never invoked, counter 0. Both results identical; both costs different |
| D-047 | Where `Optional` belongs | 1.11.1, 1.11.14–1.11.18, 2.6.1 | decision-tree | Root: "where does this Optional live?" Branches: return type → correct; field → wrong (not `Serializable`, extra indirection), use null or a default; parameter → wrong, overload instead; collection element → wrong, filter it out; map value → wrong, omit the key; `Optional<List<T>>` → wrong, return an empty list. Every wrong leaf carries the replacement |
| D-048 | The `Optional` chain versus the null check | 1.11.13, 1.11.21, 2.6.2 | before-after | Left: nested `if (x != null)` navigation from `Client` → `Account` → `Wallet` → `Money`, four levels. Right: `findClient(id).map(Client::account).map(Account::wallet).map(Wallet::withdrawable).orElse(Money.ZERO)`. Beneath, the anti-pattern `if (opt.isPresent()) opt.get()` marked as the left-hand version plus one allocation |
| D-049 | Where `var` is legal and where it is not | 1.12.3, 1.12.4 | table | Rows: local with initialiser, enhanced-`for` variable, classic `for` index, try-with-resources resource, lambda parameter, field, method parameter, return type, `catch` parameter, local without initialiser, `var x = null`, array-initialiser shorthand, generic type argument. Columns: legal, since which release, the compile error text where illegal, and the reason in one clause |
| D-050 | `var` plus the diamond infers `Object` | 1.12.7, 3.8.7 | before-after | Left: `var positions = new ArrayList<>();` inferring `ArrayList<Object>`, with the later `positions.get(0).amount()` compile error shown. Right: `var positions = new ArrayList<Position>();` inferring `ArrayList<Position>`. The inference step drawn: no target type → the diamond resolves to `Object` |
| D-051 | What a record generates | 1.13.3, 1.13.4, 1.13.6 | before-after | Left: `record StakeSplit(Money bonusPortion, Money cashPortion) {}` — one line. Right: everything the compiler adds: two `private final` fields, the canonical constructor, two accessors named `bonusPortion()`/`cashPortion()`, `equals`, `hashCode`, `toString`, the implicit `final`, and `extends java.lang.Record`. Each generated member labelled with its exact signature |
| D-052 | The compact constructor desugars | 1.13.9, 1.13.10, 3.9.9 | before-after | Left: the compact form validating that `bonusPortion.add(cashPortion)` equals the stake and normalising scale, with the parameters reassigned. Right: the desugared canonical constructor with the same body plus `this.bonusPortion = bonusPortion; this.cashPortion = cashPortion;` appended. An error panel: assigning the field instead of the parameter inside the compact form, and the compile error |
| D-053 | A record is shallowly immutable | 1.13.16, 1.13.17, 2.8.13 | step-sequence, 3 frames | `record PaymentRun(RunId id, List<WithdrawalTransaction> items)`. Frame 1: constructed from a caller-held `ArrayList` — one list object, two references. Frame 2: the caller mutates their list; the record's contents change. Frame 3: the fix — `List.copyOf` in the compact constructor, drawn as a separate list object, plus copy-out with `clone()` for an array component |
| D-054 | An array component breaks `equals` | 1.13.18, 4.5.3 | before-after | Left: `record Batch(byte[] payload)` with two instances holding equal contents — `equals` false, hashes differ, the reference comparison labelled. Right: the same with `List<Byte>` (or a `record` wrapping `ByteBuffer`) — `equals` true. A third panel: the hand-written `Arrays.equals` override if the array is unavoidable |
| D-055 | The record cliff | 1.13.27, 1.13.28, 2.8.16 | decision-tree | Root: "should this be a record?" Branches for needing a mutable field, an internal representation different from the API, inheritance, a no-arg constructor for a framework — each terminating in "not a record, and you lose every generated member at once", with JPA entities named. The yes-leaves list DTOs, value objects, compound map keys, multiple return values, sealed cases, pipeline scratch types |
| D-056 | A sealed hierarchy | 1.14.1, 1.14.2, 1.14.9, 1.14.10 | hierarchy | `sealed interface Verdict permits DocumentVerdict, ScreeningVerdict, ReviewVerdict, WealthVerdict`, each permitted subtype a record with its components listed. Each subtype box labelled `final`. A legend maps the shape to "sum type" for the interface and "product type" for each record |
| D-057 | Every permitted subtype must choose one of three modifiers | 1.14.3, 1.14.4, 1.14.7, 1.14.8 | decision-tree | Root: a permitted subtype. Three legal branches: `final` (closed), `sealed` (closed with its own permits list), `non-sealed` (reopened). A fourth branch — no modifier — ends in the compile error, quoted. Two further error leaves: an anonymous or local class (no canonical name to write in `permits`) and a grandchild that does not *directly* extend the sealed type |
| D-058 | Sealed interface vs enum vs open polymorphism | 1.14.11, 1.14.18, 2.9.9 | table | Rows: closed set of instances vs closed set of types vs open, per-case data, exhaustiveness in a switch, who can add a case, cost of adding a case, cross-module extensibility, reflection support. Columns: enum, sealed interface, `final` class, package-private constructor, open interface. The QuizStakes mapping: `RestrictionType` as an enum, `Verdict` as sealed |
| D-059 | Sealing is a module/package boundary | 1.14.6, 1.14.15, 3.10.5 | before-after | Left: sealed type and permitted subtypes in the same named module — compiles. Right: a permitted subtype in another module — compile error, text quoted. A third panel for the unnamed module, where the rule becomes same-package. A note: you cannot permit a type you do not control |
| D-060 | A pattern is a test, an extraction and a binding | 1.15.1, 1.15.2, 1.15.22 | before-after | Left: the pre-16 form — `if (v instanceof DocumentVerdict) { DocumentVerdict d = (DocumentVerdict) v; ... }` with the three steps numbered. Right: `if (v instanceof DocumentVerdict d)` with the same three steps collapsed, and below it the record-pattern form `if (v instanceof DocumentVerdict(var outcome, var reason, var at, var by))` |
| D-061 | Flow scoping is not a block rule | 1.15.3–1.15.5 | flowchart | Four panels over one method. (1) `if (v instanceof DocumentVerdict d) { … }` — `d` in scope inside. (2) `if (!(v instanceof DocumentVerdict d)) return;` — `d` in scope for the *rest of the method*, that region shaded. (3) `x instanceof T t && t.foo()` — in scope on the right of `&&`. (4) `x instanceof T t || t.foo()` — not in scope, compile error quoted. Each panel annotates "where the compiler can prove the test succeeded" |
| D-062 | How a pattern switch routes a value, including null | 1.15.7, 1.15.8, 3.11.12 | flowchart | Entry with the selector. First decision: is the selector null? If a `case null` label exists → that arm. If not → `NullPointerException` thrown before any label is tested, drawn explicitly. Otherwise → the `typeSwitch` indy returns an index → `tableswitch` → the arm. `case null, default ->` shown as a merged target |
| D-063 | Dominance and label order | 1.15.18–1.15.20 | before-after | Left: `case Verdict v ->` written before `case DocumentVerdict d ->` — compile error, text quoted, the general label shown swallowing the specific one. Right: the specific label first, compiling. A third panel: a guarded case `case DocumentVerdict d when d.outcome() == REFERRED` placed before its unguarded twin, with the note that the guard removes it from dominance analysis. A fourth: a total type pattern plus `default` — compile error |
| D-064 | Nested record deconstruction | 1.15.11, 1.15.12, 2.10.11 | hierarchy | `case Movement(LedgerEntry(Position from, Money amount), LedgerEntry(Position to, Money _))` drawn as a tree from the outer record down to each bound variable, with each accessor call labelled on its edge in declaration order. A depth marker at level three labelled "the readability limit" |
| D-065 | The pattern-matching lineage | 1.15.2, 1.15.6, 1.15.10, 1.15.13, 1.15.24 | timeline | An axis from Java 14 to Java 25 with three tracks: `instanceof` patterns (JEP 305 preview 14, 375 second preview 15, 394 final 16), pattern switch (17, 18, 19, 20 previews, JEP 441 final 21), record patterns (JEP 405 preview 19, 432 preview 20, 440 final 21). Two removal/withdrawal markers: record patterns in enhanced-`for` removed before 21, `&&` guards replaced by `when` at 21. A "still preview" column for primitive patterns (JEP 455/507) |
| D-066 | Switch forms compared | 1.16.1–1.16.11, 1.16.16 | table | Rows: colon statement, arrow statement, colon expression with `yield`, arrow expression. Columns: fall-through, produces a value, `break` allowed, `yield` allowed, `return` allowed, exhaustiveness required, mixing allowed with the others. The QuizStakes example is dispatching on `RestrictionType` |
| D-067 | Fall-through, and how the arrow form makes it unwritable | 1.16.2, 1.16.17 | before-after | Left: a colon switch over restriction sources with a missing `break`, the execution path falling through two arms drawn as one continuous arrow, and the wrong outcome named. Right: the same logic in arrow form, one arm executed, no `break` written or needed |
| D-068 | Exhaustive enum switch expression versus one with `default` | 1.16.6, 1.16.15, 3.12.7, 3.12.8 | before-after | Left: an exhaustive switch expression over `RestrictionType` with no `default`; adding `DORMANT_FROZEN` to the enum produces a compile error, quoted. Right: the same with `default ->`; adding the constant compiles and silently takes the default. A third panel shows the synthetic default the compiler still emits, throwing `IncompatibleClassChangeError` when the enum changed after separate compilation |
| D-069 | The three text-block compile steps, in order | 1.17.4, 1.17.11, 3.13.2 | step-sequence, 3 frames | A SQL text block reading `CLIENT_CASH_AVAILABLE` positions. Frame 1: CRLF line terminators normalised to `\n`, both forms shown as visible characters. Frame 2: incidental whitespace removed. Frame 3: escape sequences translated, with a `\n` the author wrote surviving frame 1 untouched and a `\s` surviving frame 2. Order labelled "and no other order" |
| D-070 | How incidental whitespace is computed | 1.17.6, 1.17.8, 3.13.3 | step-sequence, 4 frames | A four-line JSON fixture. Frame 1: trailing whitespace stripped from every line, the stripped characters marked. Frame 2: blank lines excluded from the minimum. Frame 3: the closing delimiter's line *included* in the minimum, its indentation marked. Frame 4: the common prefix removed, the result shown with a left margin ruler and column numbers |
| D-071 | Moving the closing delimiter changes the string | 1.17.7 | before-after | The same SQL text block drawn twice with a column ruler: closing `"""` aligned with the content, and closing `"""` four columns to the left. The two resulting strings printed with a visible left-margin marker per line and the extra four spaces highlighted |
| D-072 | `\s` as a trailing-space fence | 1.17.9, 1.17.10 | before-after | A fixed-width payload line whose trailing spaces are significant. Left: without `\s` — the trailing spaces stripped, the field width wrong, both lengths printed. Right: with `\s` at the end — the space survives, the width correct. A second row shows `\` at end of line suppressing the terminator |
| D-073 | Platform thread versus virtual thread | 1.18.1, 1.18.10, 3.14.10 | memory-layout | Left: a platform thread — an OS thread, a 1 MB reserved stack outside the heap, a `Thread` object. Right: a virtual thread — a `VirtualThread` object of a few hundred bytes plus a growable `StackChunk` on the heap, mounted on a carrier that is itself a platform thread. Byte figures on both, and 55k peak concurrent sessions costed each way |
| D-074 | Mounting and unmounting | 1.18.7, 3.14.2, 3.14.3 | step-sequence, 4 frames | A virtual thread calling the card PSP with a p50 of 240 ms. Frame 1: mounted, frames on the carrier's stack. Frame 2: the blocking socket read triggers `Continuation.yield`; frames copied to the heap `StackChunk`. Frame 3: the carrier picks up a different virtual thread — the carrier reused, labelled. Frame 4: the response arrives, frames copied back, execution resumes on a possibly *different* carrier |
| D-075 | The carrier pool | 1.18.5, 1.18.6, 3.14.5–3.14.7 | memory-layout | The default scheduler as a `ForkJoinPool` in FIFO async mode; parallelism = `availableProcessors()`; `maxPoolSize` (**verify the 256 default before printing it**); `jdk.virtualThreadScheduler.parallelism` and `jdk.virtualThreadScheduler.maxPoolSize` labelled on the boxes they control; a queue of runnable virtual threads feeding the carriers FIFO, with a note contrasting the LIFO work-stealing used by parallel streams |
| D-076 | Little's law sets the thread count | 1.18.3 | cost-curve | Concurrency = throughput × latency plotted for QuizStakes: 1,200 stake reservations/sec at a 240 ms p50 needs 288 concurrent tasks; at the 11 s p99 it needs 13,200. A horizontal line at a 200-thread platform pool shows where throughput is capped; the virtual-thread line has no cap in that range. All four numbers written on the plot |
| D-077 | Pinning on Java 21 | 1.18.21–1.18.23, 3.14.13 | before-after | Left: a virtual thread blocking inside a `synchronized` block in a JDBC driver — the continuation cannot yield, the carrier is held, other virtual threads queue behind it; `-Djdk.tracePinnedThreads=full` output shown. Right: the same code with `ReentrantLock` — the thread unmounts and the carrier is freed. A VERSION TRAP banner: JEP 491 removes the `synchronized` cause in Java 24; native frames still pin |
| D-078 | The virtual-thread creation API | 1.18.11–1.18.14 | table | Rows: `Thread.startVirtualThread(Runnable)`, `Thread.ofVirtual().name(...).start(...)`, `Thread.ofVirtual().unstarted(...)`, `Thread.ofVirtual().factory()`, `Executors.newVirtualThreadPerTaskExecutor()`, `Thread.ofPlatform()`. Columns: returns, started immediately, nameable, usable with try-with-resources (and the Java 19 `ExecutorService implements AutoCloseable` change), what `close()` waits for |
| D-079 | What a virtual thread refuses to do | 1.18.15–1.18.18 | table | Rows: `setDaemon(false)`, `setPriority`, thread group, `getName()` default, `stop`, `suspend`, `resume`. Columns: behaviour on a platform thread, behaviour on a virtual thread (throws / silently ignored / fixed value / empty string), and the operational consequence — an unnamed virtual thread being unfindable in a dump |
| D-080 | A structured task scope is a tree | 1.19.1–1.19.3, 3.15.1 | hierarchy | An `AssessmentService` call forking two subtasks — the identity vendor (p50 900 ms) and the watchlist provider (p50 1.4 s) — under one scope, each subtask a virtual thread. The `try`-with-resources block drawn as the boundary the subtasks cannot outlive. Beside it the unstructured version with two orphan threads escaping the block |
| D-081 | `ShutdownOnFailure` versus `CompletableFuture.allOf` | 1.19.5, 1.19.11, 2.13.4 | timeline | Two lanes on one time axis. Lane 1, `ShutdownOnFailure`: the watchlist call fails at 1.4 s, the identity call is interrupted, `join()` returns, `throwIfFailed()` rethrows. Lane 2, `allOf`: the same failure, the identity call keeps running past the block's end, marked "orphan", still holding its connection. Both end states labelled |
| D-082 | `ShutdownOnSuccess` as a hedge | 1.19.6, 2.13.2 | timeline | Two replicas of the watchlist provider, one responding at 1.4 s and one at 25 s. One axis, two lanes: the fast one completes, the scope cancels the slow one at 1.4 s, the total latency marked. A comparison line shows the un-hedged p99 of 25 s |
| D-083 | `Subtask` states and the illegal calls | 1.19.8, 1.19.9, 3.15.2, 3.15.3 | state-transition | States `UNAVAILABLE`, `SUCCESS`, `FAILED`, with the transitions caused by `fork`, task completion, task failure and `shutdown`. Illegal edges labelled with their exceptions: `get()` before `join()` → `IllegalStateException`; a call from a non-owner thread or an out-of-order close → `StructureViolationException` |
| D-084 | Sequenced collections and the retrofit | 1.20.19, 1.20.20 | hierarchy | `SequencedCollection`, `SequencedSet`, `SequencedMap` as new interfaces; arrows showing `List` and `Deque` gaining `SequencedCollection`, `LinkedHashSet` implementing `SequencedSet`, `SortedSet` extending `SequencedSet`, `LinkedHashMap` implementing `SequencedMap`, `SortedMap` extending `SequencedMap`. Every new method listed on the interface that declares it |
| D-085 | `reversed()` is a view | 1.20.21, 1.20.22 | before-after | A `LinkedHashMap` of restriction keys in insertion order. Left: `reversed()` drawn as a view object pointing at the same entries, with a write through the view changing the source — both drawn. Right: an explicit copy, with the write isolated. A side note: `getFirst()` on an empty sequenced collection throws `NoSuchElementException`, it does not return null |
| D-086 | Library additions by release, 9 → 21 | 1.20.1–1.20.24 | table | One row per release from 9 to 21. Columns: collection factories, `String` methods, `Files`/IO, stream and `Optional` additions, language additions, and the one behaviour change that breaks existing code (JEP 400's UTF-8 default at 18 highlighted) |

## Part 2 diagrams

| # | Diagram | Syllabus leaf | Type | Must show |
|---|---|---|---|---|
| D-087 | The master stream cost table | 2.1.1 | table | One row per stream operation. Columns: per-element cost, allocations per stage, stateful, buffering (none / bounded / whole stream), parallel behaviour, amortised cost, worst case. Costs quoted against 2.8M stake reservations |
| D-088 | Feature by version, with its JEP and its trap | 2.1.2, 3.16.20 | table | One row per feature this guide owns. Columns: feature, JEP number, first preview release, final release, what it replaced, and the one trap that ships with it |
| D-089 | Lambda vs method reference vs anonymous class vs inner class | 2.1.3, 2.2.5, 2.2.6 | table | Columns for each of the four. Rows: class files generated at compile time, classes created at runtime, allocations per evaluation, capture semantics, meaning of `this`, first-call linkage cost, serialization story, stack-trace readability, when it is the right answer |
| D-090 | Six ways to say "absent" | 2.1.4, 2.6.10 | table | Rows: `Optional`, `null`, a thrown exception, an empty collection, a null object, a sentinel value. Columns: caller must acknowledge, allocation cost, works in a field, works as a parameter, framework support, and the QuizStakes case each is correct for |
| D-091 | Five ways to carry data | 2.1.5 | table | Columns: record, `final` class, enum, interface, `Map<String,Object>`. Rows: immutability, generated members, pattern deconstruction, extensibility, serialization, framework support, per-instance memory, when to choose |
| D-092 | Four concurrency models | 2.1.6, 2.12.17 | table | Columns: platform threads, virtual threads, reactive (WebFlux/Reactor), structured concurrency. Rows: throughput ceiling, latency, stack traces, debugger, profiler, backpressure, cancellation, library support, team learning cost |
| D-093 | Seven ways to get a `List` | 2.1.7 | table | Rows: `new ArrayList<>()`, `Arrays.asList`, `List.of`, `List.copyOf`, `Collectors.toList`, `Collectors.toUnmodifiableList`, `Stream.toList`. Columns: mutable, structurally modifiable, `set` in place, nulls permitted, concrete type guaranteed, since which release |
| D-094 | The first call to a lambda call site | 2.2.1, 3.1.8, 3.1.13 | timeline | One axis for one call site. Point 1: `invokedynamic` reached, unlinked. Point 2: `LambdaMetafactory.metafactory` bootstrap runs. Point 3: `InnerClassLambdaMetafactory` spins a hidden class. Point 4: `CallSite` linked, target bound. Point 5: every subsequent call is an ordinary interface invocation. The one-off cost band shaded and labelled in microseconds |
| D-095 | Monomorphic versus megamorphic lambda call sites | 2.2.8, 3.2.10 | before-after | Left: one `Function` implementation at a call site — the JIT inlines through the interface call, the inlined body drawn. Right: twenty different lambdas assigned to the same `Function` field — the inline cache overflows to megamorphic, no inlining, the order-of-magnitude slowdown labelled |
| D-096 | What exists before the first element moves | 2.3.4, 3.3.3 | memory-layout | A three-stage pipeline over card deposits: the source spliterator, three `AbstractPipeline` stage objects doubly linked, three lambda instances (one non-capturing shared, two capturing), and the terminal op. Object count and approximate bytes totalled, then compared with a `for` loop's zero |
| D-097 | `sorted().findFirst()` versus `min(comparator)` | 2.3.9 | cost-curve | Two curves over N from 10 to 2.8M: O(n log n) for sort-then-take-first and O(n) for `min`. Both plotted with the comparator-invocation counts at N = 95,000 (one day of card deposits) written on the curves. The identical answer noted |
| D-098 | Stream or loop | 2.3.14, 2.3.15, 2.15.2 | decision-tree | Root: "what does the code need to do?" Branches to loop for side effects, early exit carrying several values, index arithmetic, in-place mutation, checked exceptions, a measured hot path. Branches to stream for transformation chains, grouping and aggregation, laziness over an expensive or infinite source, one-line parallelism over a splittable source |
| D-099 | One blocking parallel stream starves the whole JVM | 2.4.2, 2.4.5, 3.5.9 | before-after | Left: the common pool with `availableProcessors() - 1` workers plus the submitting thread — the effective width equal to the core count, both halves labelled. All workers blocked on the identity vendor's 38 s p99. Right: an unrelated library's parallel stream queued behind them, its latency inflated. The fix — a dedicated executor — drawn as a third panel |
| D-100 | Source splitting quality, ranked | 2.4.8, 3.4.5–3.4.9 | table | Rows: `int[]`, `ArrayList`, `IntStream.range`, `HashMap`, `HashSet`, `TreeMap`, `LinkedList`, `Files.lines`, `Stream.iterate`, `BufferedReader.lines`. Columns: characteristics reported, how `trySplit` divides, balance of the halves, verdict (excellent / good but uneven / effectively serial) |
| D-101 | `parallelStream().forEach(list::add)` corrupts the list | 2.4.11 | step-sequence, 3 frames | Two carrier threads adding to one `ArrayList` of ledger entries. Frame 1: both read `size` as 40. Frame 2: both write to index 40 — one entry lost. Frame 3: a grow racing with a write producing `ArrayIndexOutOfBoundsException` from inside `ArrayList.add`, plus the interspersed-null case. All three symptoms named |
| D-102 | Where parallel starts paying | 2.4.6, 2.4.7 | cost-curve | Sequential and parallel curves over N with the split/merge overhead as a constant band; the crossover marked near the N×Q ≈ 10,000 heuristic; three QuizStakes points plotted — 40 deposits/sec (never worth it), 95k deposits/day (marginal), 2.8M reservations/day with expensive per-element work (worth it) |
| D-103 | `filtering(p, toList())` versus `filter(p)` before `groupingBy` | 2.5.3 | before-after | Grouping card deposits by rail where one rail has no deposit above 100. Left, `filter` before `groupingBy`: that rail's key is absent from the map entirely. Right, `filtering` as a downstream: the key is present with an empty list. Both result maps drawn key by key |
| D-104 | A top-N collector's combiner | 2.5.8, 4.3.3 | step-sequence, 3 frames | Top-3 withdrawals by amount over two parallel leaves. Frame 1: each leaf maintains a bounded `PriorityQueue` of size 3, contents shown. Frame 2: the combiner merges the two heaps and re-bounds to 3 — the discarded elements marked. Frame 3: the finisher sorts descending. Actual withdrawal amounts (180, 260, 92) used |
| D-105 | `orElse` vs `orElseGet` vs `orElseThrow` | 2.6.3 | table | Rows for the three (plus `ifPresentOrElse` and `or`). Columns: argument type, evaluated when, cost when the value is present, what it returns on empty, and the QuizStakes case each fits (a constant `Money.ZERO`, a database fallback, a `RestrictedActionException`) |
| D-106 | Four absence strategies compared | 2.6.10 | table | Columns: `Optional`, nullability annotations plus NullAway, the null-object pattern, an exception. Rows: enforced by the compiler, allocation cost, works in a field, works across an API boundary, tooling support, failure mode when ignored |
| D-107 | A `var` policy you can defend in review | 2.7.1, 2.7.6, 2.7.9, 1.12.16 | decision-tree | Root: "does the initialiser already name the type?" Yes → `var` is fine, with the builder, try-with-resources and `Map.Entry` cases as leaves. No → write the type, with the opaque-factory, accumulator-width and interface-vs-implementation leaves. Each "no" leaf carries the concrete failure: `var total = 0` overflowing, `var list = new ArrayList<String>()` pinning the local's type to `ArrayList` |
| D-108 | Records across the framework boundary | 2.8.2–2.8.6, 2.8.14 | table | Rows: Jackson serialisation, Jackson deserialisation, Spring `@RequestBody`, Spring `@ConfigurationProperties`, Spring `@ModelAttribute`, Bean Validation, JPA entity, JPA `@Embeddable`, Spring Data projection, Lombok `@Value` equivalence. Columns: works, minimum version, what it needs (`-parameters`, `@JsonProperty`, `@JsonCreator`, a `@Target` including `RECORD_COMPONENT`), and the failure symptom when it does not |
| D-109 | Defensive copying, in and out | 2.8.13, 1.13.17 | before-after | `record PaymentRun(RunId id, List<WithdrawalTransaction> items, byte[] signature)`. Left: no copies — the caller's list and array both shared and mutable through the accessor. Right: `List.copyOf` in the compact constructor and `signature.clone()` on both copy-in and copy-out, with four distinct objects drawn and the mutation attempts shown failing |
| D-110 | Sum of products | 2.9.1, 2.9.5, 2.9.7 | hierarchy | The `Verdict` sealed interface as the sum; each record case expanded into its components as the product. Beside it a second worked shape: the account lifecycle state machine as a sealed interface of records with the transitions drawn as labelled edges between the case boxes |
| D-111 | Visitor versus sealed interface plus pattern switch | 2.9.3, 4.5.5 | before-after | Left: the Visitor implementation — a `VerdictVisitor` interface with four methods, an `accept` in each case class, and the double dispatch arrows; line count stated. Right: the sealed interface plus one pattern switch; line count stated. Underneath, a two-row table: "to add a case, edit here" and "to add an operation, edit here" for both designs |
| D-112 | The expression problem | 2.9.4 | table | A 2×2: adding a case versus adding an operation, against sealed hierarchy versus open polymorphism. Each cell states what must change and where the compiler helps you. A fifth column names the QuizStakes axis of change that decides it |
| D-113 | Refactoring an `instanceof` chain into a pattern switch | 2.10.1, 2.10.2 | step-sequence, 4 frames | Frame 1: the original `if`/`else if` chain of `instanceof` + cast over `Verdict`. Frame 2: type patterns replacing the casts. Frame 3: converted to a pattern switch, `default` still present. Frame 4: `default` removed once the type is sealed, so exhaustiveness is checked. Each frame states what the compiler now guarantees that it did not before |
| D-114 | Exhaustiveness drift after a partial redeploy | 2.10.9, 3.10.8, 4.8.9 | timeline | Three points: (1) both the sealed hierarchy and the switch site compiled together, exhaustive; (2) a fifth `Verdict` case added and only the hierarchy recompiled and deployed; (3) at runtime the switch matches nothing and throws `MatchException` (or `IncompatibleClassChangeError`). The class-file states at each point drawn, and the note that this is not a link error |
| D-115 | Text block, resource file, or constant | 2.11.3, 2.11.8, 2.15.8 | decision-tree | Root: "what is the payload?" Branches for SQL and JSON fixtures (text block), a payload another tool must lint/format/diff (resource file), a short single-line value (constant), and regex (text block loses — `\` still escapes, every backslash doubles, shown with an example). Trailing-newline discipline noted on the file-comparison leaf |
| D-116 | A Spring Boot request path, before and after virtual threads | 2.12.1–2.12.3 | before-after | Left: Tomcat with `maxThreads=200` — 200 platform threads, requests queueing behind them, `maxThreads` acting as the accidental rate limiter, 55k peak sessions against a 200-wide gate. Right: `spring.threads.virtual.enabled=true` — a virtual thread per request, no concurrency cap at the container, and the queue gone. What the flag switches (servlet executor, `@Async`) and what it does not, labelled |
| D-117 | The bottleneck moves downstream | 2.12.4, 2.12.5 | before-after | Left: the pool as the implicit limiter, with the JDBC pool of 20 comfortably behind 200 request threads. Right: 14k concurrent virtual threads arriving at the same 20-connection pool, the queue now at the connection pool and the database's max-connections ceiling. The deliberate fix — a `Semaphore` sized on purpose — drawn as the third panel |
| D-118 | A pinning JDBC driver under load | 2.12.6, 2.12.9, 2.12.10 | step-sequence, 3 frames | Frame 1: eight carriers, each running a virtual thread that enters the driver's `synchronized` block and blocks on the network. Frame 2: all carriers pinned; new virtual threads cannot run; the JFR `jdk.VirtualThreadPinned` event fires past its 20 ms threshold. Frame 3: the JSON thread dump from `jcmd <pid> Thread.dump_to_file -format=json` showing the pinned frames, with a note that `jstack` shows none of it |
| D-119 | What to measure once threads are free | 2.12.10–2.12.12 | table | Rows: live threads gauge, in-flight requests, semaphore permits in use, connection-pool saturation, `jdk.VirtualThreadStart`/`End`, `jdk.VirtualThreadPinned`, `jdk.VirtualThreadSubmitFailed`, heap occupied by stack chunks. Columns: what it meant before, what it means now, default JFR state (enabled/disabled) and threshold, and the alert worth setting |
| D-120 | A fan-out with one deadline | 2.13.1, 2.13.3 | timeline | One `joinUntil(Instant)` deadline drawn as a vertical line at 2 s across two subtask lanes: the identity vendor (900 ms p50, completes) and the watchlist provider (25 s p99, cut off). The scope's return marked, the cancelled subtask's interrupt arrow drawn, and the alternative of per-subtask timeouts shown as a second pair of lanes |
| D-121 | Scoped-value bindings versus a `ThreadLocal` map | 2.13.6–2.13.8, 3.15.5, 3.15.6 | before-after | Left: `ThreadLocal` — one map per thread, an inheritance copy into each child, and a `remove()` obligation, with the leak drawn when it is skipped. Right: `ScopedValue` — an immutable linked binding snapshot shared structurally, unbound automatically by stack unwinding, inherited by forked subtasks. A nested `where` drawn as shadowing, not mutation |
| D-122 | What breaks at each release, 9 → 21 | 2.14.1–2.14.6 | timeline | An axis with a marker per breaking release: 9 (strong encapsulation of internals, split packages), 11 (Java EE and CORBA modules removed), 16 (encapsulation on by default, `--add-opens`), 17 (`strictfp` no-op, Security Manager deprecated, illegal reflective access denied), 18 (UTF-8 default, JEP 400), 21 (pattern-switch exhaustiveness, sequenced-collection method-name clashes on `getFirst`/`reversed`/`putFirst`). Each marker carries the symptom you would actually see |
| D-123 | The safe upgrade order | 2.14.10, 2.14.11 | flowchart | Step 1: run on the new JDK with the old `--release`. Step 2: fix what breaks at runtime, with `jdeps --jdk-internals` and `jdeprscan` as the inputs. Step 3: raise `--release`. Step 4: fix compile errors. Step 5: adopt features. Each step has a rollback edge back to the previous, and a gate condition written on it |
| D-124 | The which-construct index | 2.15.1–2.15.10 | table | One row per question in §2.15. Columns: the question, the default answer, the condition that overrides the default, and the section of these notes that argues it |

## Part 3 diagrams

| # | Diagram | Syllabus leaf | Type | Must show |
|---|---|---|---|---|
| D-125 | How `javac` desugars a lambda | 3.1.1–3.1.3 | step-sequence, 3 frames | Frame 1: the source lambda inside `FundsLedger.reserveStake`. Frame 2: the private synthetic method `lambda$reserveStake$0`, marked `static` because it does not capture `this`. Frame 3: the call site replaced by `invokedynamic #N` with `LambdaMetafactory.metafactory` as the bootstrap. The `javap -c -p` text shown alongside each frame |
| D-126 | Reading a `BootstrapMethods` entry | 3.1.4–3.1.7, 3.1.17 | memory-layout | One `invokedynamic` entry annotated field by field: the bootstrap `LambdaMetafactory.metafactory` with its six parameters named (`caller`, `interfaceMethodName`, `factoryType`, `interfaceMethodType`, `implementation`, `dynamicMethodType`); the static arguments in the constant pool; the dynamic arguments on the operand stack. An arrow from `factoryType`'s parameter list to the captured locals, labelled "this is exactly what was captured" |
| D-127 | Non-capturing versus capturing at link time | 3.1.10, 3.1.11, 2.2.3, 2.2.4 | before-after | Left: a non-capturing lambda — the spun hidden class holds one instance in a static field, the bootstrap returns a `ConstantCallSite`, one allocation for the JVM's lifetime. Right: a capturing lambda — the spun class has one field per captured value and a constructor, and the call site allocates per evaluation. Allocation counts over 2.8M reservations written on both |
| D-128 | A method reference has no `lambda$` method | 3.1.14, 1.4.16 | before-after | Left: `r -> r.amount()` — a synthetic `lambda$…$0` method plus the indy. Right: `Reservation::amount` — no synthetic method, `implementation` is a direct method handle to `Reservation.amount`. Both `javap -c -p` listings shown with the differing lines highlighted |
| D-129 | `FLAG_SERIALIZABLE` and the serializable-lambda path | 3.1.5, 3.1.15 | flowchart | `altMetafactory` with its three flags and their values (`FLAG_SERIALIZABLE = 1`, `FLAG_MARKERS = 2`, `FLAG_BRIDGES = 4`); the serialization path through `SerializedLambda` and the compiler-generated `$deserializeLambda$`; each hop labelled with its cost, and the refactoring-fragility failure named at the end |
| D-130 | A captured `this` keeps the enclosing object alive | 3.2.4 | memory-layout | A static `NotificationService` registry holding one lambda that reads an instance field of `ProfileService`. The captured `this` arrow drawn to the `ProfileService` instance, which retains its aggregated objects. Retained bytes labelled on the whole subgraph; the fix (capture only the needed value into a local) drawn beside it with the reduced retained set |
| D-131 | The pipeline as a doubly linked list of stages | 3.3.1–3.3.4, 3.3.10 | memory-layout | The `AbstractPipeline` chain for `deposits.stream().filter(...).map(...).collect(...)`: three stage objects with all twelve fields named on the source stage (`sourceStage`, `previousStage`, `sourceOrOpFlags`, `nextStage`, `depth`, `combinedFlags`, `sourceSpliterator`, `sourceSupplier`, `linkedOrConsumed`, `sourceAnyStateful`, `sourceCloseAction`, `parallel`), `depth` values 0, 1, 2, and the `StatelessOp`/`StatefulOp` subtype labelled on each |
| D-132 | `wrapSink` walks backwards | 3.3.5–3.3.9 | step-sequence, 4 frames | Frame 1: the terminal op's sink created. Frame 2: the `map` stage's `opWrapSink` wraps it. Frame 3: the `filter` stage wraps that. Frame 4: `copyInto` calls `begin`, `forEachRemaining`, `end` on the outermost sink, and one element traverses the whole chain. `Sink`'s four methods listed in a legend, and the `copyIntoWithCancel` variant noted on frame 4 |
| D-133 | `StreamOpFlag` | 3.3.13, 3.3.16, 3.3.17, 3.4.14 | table | Rows: `DISTINCT`, `SORTED`, `ORDERED`, `SIZED`, `SHORT_CIRCUIT`. Columns: the bit position, what it means, what the stream position/op position/terminal-op position each encode (SET/CLEAR/PRESERVE), which operations set it, which clear it, and which optimisation it unlocks (`sorted()` becoming a no-op, `distinct()` using adjacent comparison, `count()` bypassing the pipeline) |
| D-134 | How `count()` bypasses the pipeline | 3.3.14, 3.3.15, 1.8.12 | flowchart | Start at `count()`. Check `SIZED` still set in `combinedFlags` → check no stateful op cleared it → check nothing short-circuits → return the source's exact size without building a sink chain. The `peek` stage boxed on the bypassed path and labelled "never invoked". A second path with a `filter` present, clearing `SIZED`, taking the full traversal. VERSION TRAP: Java 9 changed this |
| D-135 | The eight spliterator characteristics | 3.4.1, 3.4.2 | table | One row per characteristic with its hex bit value: `DISTINCT 0x01`, `SORTED 0x04`, `ORDERED 0x10`, `SIZED 0x40`, `NONNULL 0x100`, `IMMUTABLE 0x400`, `CONCURRENT 0x1000`, `SUBSIZED 0x4000`. Columns: meaning, which JDK sources report it, which stream optimisation it enables, and which operation clears it. The eight `Spliterator` methods listed in a legend |
| D-136 | `trySplit` returns the prefix | 3.4.4, 3.4.5 | step-sequence, 3 frames | An `ArrayList` of 95,000 card deposits. Frame 1: one spliterator over indices 0–94,999. Frame 2: `trySplit` returns a spliterator over 0–47,499 (the prefix) and leaves the original covering 47,500–94,999 — both ranges labelled. Frame 3: the recursion continuing to a leaf below the target size. Index bounds written at every level |
| D-137 | `SIZED` but not `SUBSIZED` | 3.4.3 | before-after | Left: an array-backed source — the total size is known and every split's size is known, so both flags are reported. Right: a balanced tree — the total is known (`SIZED`) but the subtree sizes are not (`not SUBSIZED`), drawn with the unknown subtree counts marked. The javadoc's own framing quoted in the caption |
| D-138 | Why an `Iterator`-derived stream parallelises badly | 3.4.7, 3.4.8, 3.4.9 | step-sequence, 3 frames | `IteratorSpliterator`'s batching fallback. Frame 1: the first `trySplit` pulls a batch of 1024 elements into an array. Frame 2: the next batch doubles. Frame 3: the tail remains unsplittable and never reports `SUBSIZED`. Batch sizes written on each frame; `LinkedList` and `Files.lines` named as the cases |
| D-139 | The parallel task tree | 3.5.1–3.5.3 | hierarchy | An `AbstractTask` tree over 2.8M reservations on an 8-core box: `LEAF_TARGET = ForkJoinPool.getCommonPoolParallelism() << 2` and `suggestTargetSize = sizeEstimate / LEAF_TARGET` written as formulas with the arithmetic worked, roughly four tasks per core; the resulting leaf count and leaf size labelled. **Mark both formulas as requiring verification against `AbstractTask.java` before the numbers are printed** |
| D-140 | The combine tree costs O(n) overall | 3.5.5, 3.6.4, 3.6.9 | step-sequence, 3 frames | Four leaves each with their own `ArrayList` of results. Frame 1: leaf accumulation, sizes shown. Frame 2: the first pairwise merges, each copying the right half into the left. Frame 3: the final merge copying half the total. Element-copy counts summed across the tree, and the same picture repeated for `joining()`'s `StringBuilder` append |
| D-141 | `ForEachTask` versus `ForEachOrderedTask` | 3.5.6, 1.8.1, 1.8.2 | before-after | Left, `forEach` in parallel: four leaves emitting as they finish, output interleaved, no buffering. Right, `forEachOrdered`: completed subtrees buffered until their predecessors finish, the buffers drawn with their contents, and the lost parallel win labelled |
| D-142 | Work stealing in the common pool | 3.5.11, 3.5.13, 3.5.14 | memory-layout | Four workers each with a deque; each pushes and pops at its own head; an idle worker steals from the tail of another, the steal arrow labelled. A second panel: a nested parallel stream inside a parallel stream's lambda producing the starvation shape. A third: two exceptions racing to the joining task, the first winning and the second discarded |
| D-143 | `CollectorImpl` and its pre-built characteristic sets | 3.6.1, 3.6.2 | table | Rows: `CH_CONCURRENT_ID`, `CH_CONCURRENT_NOID`, `CH_ID`, `CH_UNORDERED_ID`, `CH_UNORDERED_NOID`, `CH_NOID`. Columns: which of `CONCURRENT`/`UNORDERED`/`IDENTITY_FINISH` each contains, which collectors use it, and what the framework does differently as a result |
| D-144 | Kahan compensated summation inside `summingDouble` | 3.6.7, 3.6.8, 1.10.12 | step-sequence, 3 frames | Summing 95,000 card deposits averaging 65 as `double`s. Frame 1: the three-element `double[]` accumulator with the running sum, the compensation term and the simple sum. Frame 2: a small addend lost to a naive `+`, recovered into the compensation slot — the arithmetic written. Frame 3: the compensation added back in the finisher, with the naive total and the compensated total printed side by side. A note that `summingInt` uses a `long[]` and needs none of this |
| D-145 | `IDENTITY_FINISH` skips a whole pass | 3.6.10 | before-after | Left, a collector without `IDENTITY_FINISH`: the accumulation container built, then the finisher walks it to produce the result — two passes drawn. Right, with `IDENTITY_FINISH`: the container is cast and returned directly, one pass. The saved work stated in element counts over 95,000 deposits |
| D-146 | Inside `Optional` | 3.7.1–3.7.3, 3.7.6 | memory-layout | An `Optional<Client>` on the heap: 16-byte object header plus the single `value` reference field, the total written out; the shared `private static final Optional<?> EMPTY` drawn once with two `Optional.empty()` calls pointing at it and `==` annotated true; the `@jdk.internal.ValueBased` annotation labelled on the class with the "do not synchronize, do not depend on identity" consequence |
| D-147 | Upward projection | 3.8.1, 3.8.4 | step-sequence, 3 frames | `List<? extends Money> amounts; var first = amounts.get(0);`. Frame 1: the standalone type of the initialiser, containing a capture variable. Frame 2: upward projection replacing the capture variable with `Money`. Frame 3: the inferred local type. A second panel: an anonymous class initialiser where the inferred type is genuinely non-denotable and its extra members remain callable |
| D-148 | Where `var` leaves a trace in the class file | 3.8.2, 3.8.3, 1.12.1 | before-after | Left: the source with `var`. Right: the `javap -l` output showing `LocalVariableTable`/`LocalVariableTypeTable` carrying the inferred type, and the bytecode being byte-for-byte identical to the explicitly typed version — both listings shown. A note explaining why a field or parameter could never work: separate compilation |
| D-149 | The `Record` class-file attribute | 3.9.1, 3.9.2, 3.9.11 | memory-layout | The class file of `StakeSplit` with its `Record` attribute expanded: two `record_component_info` entries, each with a name index, a descriptor index and its own attributes (`Signature`, `RuntimeVisibleAnnotations`, `RuntimeVisibleTypeAnnotations`). The `private final` fields, the public accessors, and `extends java.lang.Record` (itself abstract, declaring abstract `equals`/`hashCode`/`toString`) all labelled |
| D-150 | `ObjectMethods.bootstrap` behind `equals`, `hashCode` and `toString` | 3.9.3–3.9.6 | flowchart | The three generated methods each compiling to an `invokedynamic` against `java.lang.runtime.ObjectMethods.bootstrap`, with the static arguments drawn: the record class, the semicolon-separated component-name string `"bonusPortion;cashPortion"`, and one `MethodHandle` getter per component. A consequence box: the `hashCode` algorithm is unspecified and may change between releases — never persist it |
| D-151 | Record deserialization runs the canonical constructor | 3.9.12, 3.9.13, 4.8.10 | before-after | Left: a hand-written class — deserialization allocates and populates fields directly, bypassing the constructor, so the validation never runs and an invalid `StakeSplit` (portions not summing to the stake) exists. Right: the record — the stream's component values are passed to the canonical constructor, the compact constructor's validation throws. A note listing the ignored hooks (`writeObject`, `readObject`, `readObjectNoData`, `writeExternal`, `readExternal`, `serialPersistentFields`) and the default `serialVersionUID` of 0 |
| D-152 | `PermittedSubclasses` is enforced at load time | 3.10.1–3.10.4 | step-sequence, 3 frames | Frame 1: the `Verdict` class file with its `PermittedSubclasses` attribute listing four constant-pool indices; no `ACC_SEALED` flag exists, labelled. Frame 2: a bytecode-manipulated fifth subclass produced at runtime. Frame 3: the JVM's load-time check failing it. A note that `non-sealed` emits no attribute at all |
| D-153 | A pattern switch compiles to `typeSwitch` plus `tableswitch` | 3.11.3–3.11.6, 2.10.10 | step-sequence, 4 frames | Frame 1: the source switch over `Verdict`. Frame 2: the `invokedynamic` to `SwitchBootstraps.typeSwitch` with its static arguments — the label list of `Class` objects, `String`/`Integer` constants and `EnumDesc` entries. Frame 3: the bootstrap returning the index of the first matching label. Frame 4: an ordinary `tableswitch` on that index. The `javap -c` listing beside the frames, and a cost note: closer to an optimised if-chain than to a jump table |
| D-154 | Record deconstruction is accessor calls in order | 3.11.8, 3.11.9 | step-sequence, 3 frames | `case Movement(LedgerEntry(Position from, Money amount), LedgerEntry to)`. Frame 1: the outer type test. Frame 2: accessors invoked in declaration order, short-circuiting on the first component mismatch — the skipped calls marked. Frame 3: an accessor throwing, wrapped in `MatchException` with the original as its cause |
| D-155 | `tableswitch` versus `lookupswitch` | 3.12.1, 3.12.2 | before-after | Left: dense case labels compiling to `tableswitch` with the jump table drawn. Right: sparse labels compiling to `lookupswitch` with the key/offset pairs drawn. Beneath, the two-stage `String` switch: `lookupswitch` on `hashCode`, `equals` to confirm, then a second switch on a synthetic index — worked on a restriction-type name |
| D-156 | `$SwitchMap` protects a separately compiled enum switch | 3.12.3 | before-after | Left: a switch over `RestrictionType` compiled with the synthetic `$SwitchMap$RestrictionType` `int[]` mapping `ordinal()` to a stable case index — the array contents shown. Right: the enum reordered and recompiled without recompiling the switch — the map absorbs the change and the correct arm still runs. The failure that would occur without it drawn as a third panel |
| D-157 | The synthetic default in an exhaustive enum switch expression | 3.12.7, 3.12.8 | before-after | Left: the source with no `default`. Right: the `javap -c` output with the synthetic default arm that throws `IncompatibleClassChangeError`. Beneath, the scenario that reaches it: a constant added to the enum after the switch's class was compiled. A VERSION TRAP note that the thrown type has changed shape across releases |
| D-158 | A text block is a constant, folded at compile time | 3.13.1, 3.13.4, 3.13.6 | before-after | Left: the source text block. Right: the `javap -v` constant pool showing a single `CONSTANT_String_info` with the final, already-stripped content — nothing of the algorithm surviving to runtime. Beneath: a text block and an equal string literal compared with `==`, both pointing at the same interned constant, with the caution that this is not a habit to build |
| D-159 | The three layers of a virtual thread | 3.14.1, 3.14.11 | hierarchy | `java.lang.VirtualThread` on top, `jdk.internal.vm.Continuation` beneath it, the FIFO `ForkJoinPool` scheduler beneath that, and platform carrier threads at the bottom. `Thread.currentThread()` drawn returning the `VirtualThread`, with the carrier marked reachable only through internal API |
| D-160 | Stack chunks live on the heap | 3.14.2, 3.14.3, 3.14.10, 2.12.12 | memory-layout | One carrier's native stack with three mounted frames; the heap holding `StackChunk` objects for the unmounted threads; arrows for the copy in both directions labelled "mount" and "unmount", with the lazy/partial copying noted. The heap arithmetic for 1,000,000 virtual threads written out and contrasted with 1,000,000 × 1 MB of reserved platform stack |
| D-161 | `VirtualThread`'s state machine | 3.14.4 | state-transition | The nine states — `NEW`, `STARTED`, `RUNNABLE`, `RUNNING`, `PARKING`, `PARKED`, `PINNED`, `YIELDING`, `TERMINATED` — with every transition labelled by the event that causes it (`start`, schedule, mount, blocking call, successful yield, failed yield while pinned, unpark, completion) |
| D-162 | FIFO for virtual threads, LIFO for parallel streams | 3.14.7, 3.5.11 | before-after | Left: the virtual-thread scheduler in FIFO async mode — independent tasks, fairness prioritised, the queue drawn head-first. Right: the common pool's LIFO work-stealing — recursively split subtasks, locality prioritised, own-head push/pop with tail stealing. The reason for each choice written under each panel |
| D-163 | Pinning is a property of the continuation | 3.14.13, 3.14.14, 3.14.17, 3.14.18 | before-after | Left, Java 21: a held monitor or a native frame on the continuation's stack makes `yield` impossible — both frames marked on a drawn stack. Right, Java 24 (JEP 491): monitors are continuation-aware and the monitor case disappears; the native frame still pins. A third panel: no preemption — a CPU-bound virtual thread holding its carrier indefinitely, and the carrier pool growing toward `maxPoolSize` as compensation |
| D-164 | Scoped values and structured concurrency are one mechanism | 3.15.1–3.15.4, 3.15.7 | hierarchy | A scope stack per owning thread; each `fork` starting one virtual thread with the scoped-value binding snapshot inherited; `shutdown()` interrupting unfinished subtasks and `close()` joining, drawn as two distinct arrows. The ownership check labelled on `fork`/`join`/`shutdown`/`close`, with `StructureViolationException` on the illegal edges |
| D-165 | Structured concurrency and scoped values, release by release | 3.15.8, 1.19.14, 1.19.16 | table | Rows: Java 19, 20, 21, 22, 23, 24, 25, and in flight. Columns: JEP number, package, status (incubator/preview/final), the API shape (constructors vs `open()` factories, `ShutdownOnFailure` vs `Joiner`, `runWhere` vs `where(...).run`), and whether published examples from that release still compile on 21 |
| D-166 | The consolidated feature → version table | 3.16.20 | table | One row per feature this guide covers. Columns: first preview release, final release, JEP numbers for each stage, whether it is still preview on 21, and the one-line summary |
| D-167 | The consolidated removed-or-disabled table | 3.16.21 | table | Rows: Nashorn, the Java EE modules, CORBA, applets, the Security Manager, finalization, the 32-bit x86 port, `sun.misc.Unsafe` memory access. Columns: deprecated in, removed or disabled in, the replacement, and the symptom on upgrade |
| D-168 | The tooling map for this topic | 3.17.1–3.17.12 | table | One row per tool. Columns: the command or flag exactly as typed, what claim it verifies, what its output looks like, and the section of these notes that uses it. Covers `javap -c -p -v`, `jshell`, `-Djdk.internal.lambda.dumpProxyClasses`, `-Xlog:class+load=info`, the four JFR events, `jcmd Thread.dump_to_file -format=json`, `jcmd Thread.print`, async-profiler, JMH, IntelliJ's stream debugger, ErrorProne/SpotBugs/Sonar/NullAway rules, `-XX:+PrintFlagsFinal`, `System.getProperties()`, `ForkJoinPool.getCommonPoolParallelism()` |
| D-169 | What a stream stack trace actually looks like | 2.3.5, 2.3.6, 3.17.8 | before-after | Left: the exception stack trace from an NPE thrown inside a `map` over card deposits — the synthetic `lambda$process$2` frame, the `ReferencePipeline$3$1.accept` frames, the `AbstractPipeline.copyInto` frame, all labelled with what each one is. Right: the same failure inside a `for` loop, four frames deep. A note on the `StackOverflowError` risk from a long pipeline plus recursion plus `flatMap` |
| D-170 | Where the JIT can and cannot help | 2.2.2, 2.3.2, 3.2.10, 3.7.6 | table | Rows: a monomorphic lambda call site, a megamorphic one, an `Optional` chain that inlines end to end, an `Optional` chain crossing a non-inlined boundary, a boxed pipeline, a primitive pipeline. Columns: inlined, escape analysis applies, allocations eliminated, observed cost, and how you confirm it (JMH, an allocation profiler, `-XX:+PrintInlining`) |

## Part 4 diagrams

| # | Diagram | Syllabus leaf | Type | Must show |
|---|---|---|---|---|
| D-171 | `MyStream`'s sink chain next to the JDK's | 4.2.1, 4.2.2, 4.2.10 | before-after | Left: `MyStream`'s `MySink` chain with `begin`/`accept`/`cancellationRequested`/`end`, three stages, one traversal. Right: the JDK's equivalent objects for the same pipeline, with the extra machinery named (four stream shapes, `StreamOpFlag`, `Spliterator`, ForkJoin integration, closing, exception semantics) so the gap is explicit |
| D-172 | Proving fusion with a print in every stage | 4.2.3, 4.2.4 | step-sequence, 3 frames | Frame 1: the expected (wrong) stage-by-stage output. Frame 2: the actual interleaved per-element trace, printed line by line for the first three stake reservations. Frame 3: the same with `limit(2)` and `findFirst`, showing the source never fully traversed and `cancellationRequested` returning true |
| D-173 | Platform threads versus virtual threads on the echo server | 4.6.1 | cost-curve | Connections on the x-axis at 1, 1,000 and 50,000; throughput and memory on two y-axes; one line per implementation. The platform-thread line flattening and then failing at the thread limit, the virtual-thread line continuing. Measured numbers written at each of the three points |
| D-174 | The pinning reproducer, before and after | 4.6.2 | before-after | Left: `synchronized` around a blocking sleep on Java 21, with the `-Djdk.tracePinnedThreads=full` output printed and each line explained, plus the measured throughput. Right: the `ReentrantLock` version with the trace empty and the re-measured throughput. Both numbers stated |
| D-175 | The orphan that `allOf` leaves behind | 4.6.5 | before-after | Left: `StructuredTaskScope.ShutdownOnFailure` with a deliberate failure — the sibling interrupted, the thread count returning to baseline, both drawn. Right: `CompletableFuture.allOf` with the same failure — the sibling still running after the method returns, visible in the thread dump, still holding its connection |
| D-176 | Common-pool starvation, reproduced | 4.6.7 | timeline | Two lanes on one axis: a blocking parallel stream occupying every common-pool worker, and an innocent parallel stream submitted afterwards, its start delayed by the full blocking duration. Both timings written. A third lane repeats the innocent stream against a dedicated executor, starting immediately |
| D-177 | Hand-rolled batching versus `Gatherers.windowFixed` | 4.7.1, 4.7.6 | before-after | Left: the Java 21 custom `Spliterator` for fixed windows of 100 ledger entries, with `estimateSize` and the absent `SUBSIZED` claim labelled. Right: the Java 24 `Gatherers.windowFixed(100)` one-liner, with the `Gatherer` contract (`initializer`, `integrator`, `combiner`, `finisher`) and greedy-vs-short-circuiting integrators listed |
| D-178 | The fifteen puzzlers and their mechanisms | 4.8.1 | table | One row per puzzler: `peek` elision, stream reuse, `toList` immutability, `toMap` null value, `groupingBy` null key, `orElse` eagerness, `Optional.empty()` identity, `var` diamond, record array `equals`, pattern-switch NPE, text-block indentation, bound method-reference NPE, `allMatch` on empty, `IntStream.sum` overflow, parallel `forEach` corruption. Columns: what a reader predicts, what actually happens, the mechanism, and the syllabus leaf |

## Part 5 diagrams

| # | Diagram | Syllabus leaf | Type | Must show |
|---|---|---|---|---|
| D-179 | The trap index | 5.2.1 | table | One row per `**Pitfall:**` in the whole file. Columns: the wrong belief, the symptom in production, the fix, and the file and leaf where it is argued. This is the single pre-interview scan sheet |
| D-180 | The version-stale claims table | 5.2.2, 5.2.5 | table | One row per stale claim listed in leaf 5.2.2. Columns: what people still say, what was true and until when, what is true on Java 21, what changed after 21, and the release that changed it |
| D-181 | The numbers card | 5.3.1 | table | Every constant in the guide with its value and its source: 43 function interfaces, 30 collectors across 54 overloads, common-pool parallelism `n − 1` plus the submitting thread, `LEAF_TARGET = parallelism << 2`, the 20 ms `VirtualThreadPinned` threshold, `maxPoolSize` 256 (**marked as requiring verification**), class-file majors 52/53/55/61/65/69, the eight spliterator characteristic bits with their hex values, `FLAG_SERIALIZABLE = 1`/`FLAG_MARKERS = 2`/`FLAG_BRIDGES = 4`, preview minor version 65535 |
| D-182 | The spaced-repetition schedule | 5.3.8 | timeline | A 21-day axis with four marked points: day 1 full read, day 3 atomic concept checklist, day 7 numbers and mechanism drills, day 14 code-reading and symptom drills, day 21 build two Part 4 items. Each point lists the specific files to revisit |


---

## Leaf ledger

Every syllabus section, its leaf count and the file that owns it. The leaf *text* is in the
prompt at the SHA-256 recorded above; this ledger fixes ownership, which is what a resumed run
needs. An unassigned leaf is a planning bug, not a deferral — the assertion that the union is
exactly 984 with no leaf owned twice is checked by the generator that wrote this file.

| Section | Title | Leaves | Leaf ids | Owning file |
|---|---|---|---|---|
| §1.1 | Why "modern Java" is a topic at all | 12 | 1.1.1–1.1.12 | `platform-and-releases/01-basics.md` |
| §2.14 | Migration, 8 → 21 | 14 | 2.14.1–2.14.14 | `platform-and-releases/02-migration.md` |
| §3.16 | Version-by-version delta | 22 | 3.16.1–3.16.22 | `platform-and-releases/03-internals-version-delta.md` |
| §3.17 | Observability and tooling | 12 | 3.17.1–3.17.12 | `platform-and-releases/04-internals-observability.md` |
| §1.2 | Functional interfaces | 20 | 1.2.1–1.2.20 | `functional-interfaces/01-basics.md` |
| §1.3 | Lambda expressions | 22 | 1.3.1–1.3.22 | `lambdas/01-basics.md` |
| §2.2 | Lambda cost and choice | 14 | 2.2.1–2.2.14 | `lambdas/02-cost-and-choice.md` |
| §3.1 | Lambda translation | 18 | 3.1.1–3.1.18 | `lambdas/03-internals-translation.md` |
| §3.2 | Lambda capture and identity | 10 | 3.2.1–3.2.10 | `lambdas/04-internals-capture-and-identity.md` |
| §1.4 | Method references | 16 | 1.4.1–1.4.16 | `method-references/01-basics.md` |
| §1.5 | The stream model | 18 | 1.5.1–1.5.18 | `streams/01-basics-the-model.md` |
| §1.6 | Stream sources | 18 | 1.6.1–1.6.18 | `streams/02-sources.md` |
| §1.7 | Intermediate operations, exhaustively | 24 | 1.7.1–1.7.24 | `streams/03-intermediate-operations.md` |
| §1.8 | Terminal operations, exhaustively | 26 | 1.8.1–1.8.26 | `streams/04-terminal-operations.md` |
| §1.9 | Primitive streams | 16 | 1.9.1–1.9.16 | `streams/05-primitive-streams.md` |
| §2.3 | Streams: the cost model, and when not to use one | 16 | 2.3.1–2.3.16 | `streams/06-cost-model.md` |
| §2.4 | Parallel streams | 16 | 2.4.1–2.4.16 | `streams/07-parallel-streams.md` |
| §3.3 | Stream pipeline internals | 20 | 3.3.1–3.3.20 | `streams/08-internals-pipeline.md` |
| §3.4 | `Spliterator` | 14 | 3.4.1–3.4.14 | `streams/09-internals-spliterator.md` |
| §3.5 | Parallel execution internals | 14 | 3.5.1–3.5.14 | `streams/10-internals-parallel-execution.md` |
| §1.10 | Collectors | 16 | 1.10.1–1.10.16 | `collectors/01-basics-a.md` |
| §1.10 | Collectors | 14 | 1.10.17–1.10.30 | `collectors/01-basics-b.md` |
| §2.5 | Collectors in anger | 14 | 2.5.1–2.5.14 | `collectors/02-in-anger.md` |
| §3.6 | Collector internals | 10 | 3.6.1–3.6.10 | `collectors/03-internals-collectors.md` |
| §1.11 | Optional | 24 | 1.11.1–1.11.24 | `optional/01-basics.md` |
| §2.6 | Optional discipline | 12 | 2.6.1–2.6.12 | `optional/02-discipline.md` |
| §3.7 | `Optional` internals | 8 | 3.7.1–3.7.8 | `optional/03-internals-optional.md` |
| §1.12 | `var` | 16 | 1.12.1–1.12.16 | `var/01-basics.md` |
| §2.7 | `var` in practice | 10 | 2.7.1–2.7.10 | `var/02-in-practice.md` |
| §3.8 | `var` and inference internals | 8 | 3.8.1–3.8.8 | `var/03-internals-inference.md` |
| §1.13 | Records | 15 | 1.13.1–1.13.15 | `records/01-basics-a.md` |
| §1.13 | Records | 13 | 1.13.16–1.13.28 | `records/01-basics-b.md` |
| §2.8 | Records in practice | 16 | 2.8.1–2.8.16 | `records/02-in-practice.md` |
| §3.9 | Record internals | 14 | 3.9.1–3.9.14 | `records/03-internals-records.md` |
| §1.14 | Sealed types | 18 | 1.14.1–1.14.18 | `sealed-types/01-basics.md` |
| §2.9 | Sealed types and data-oriented programming | 12 | 2.9.1–2.9.12 | `sealed-types/02-data-oriented-programming.md` |
| §3.10 | Sealed internals | 8 | 3.10.1–3.10.8 | `sealed-types/03-internals-sealed.md` |
| §1.15 | Pattern matching | 24 | 1.15.1–1.15.24 | `pattern-matching/01-basics.md` |
| §2.10 | Pattern matching in anger | 12 | 2.10.1–2.10.12 | `pattern-matching/02-in-anger.md` |
| §3.11 | Pattern matching internals | 12 | 3.11.1–3.11.12 | `pattern-matching/03-internals-pattern-matching.md` |
| §1.16 | `switch` expressions and statements | 18 | 1.16.1–1.16.18 | `switch/01-basics.md` |
| §3.12 | `switch` compilation | 8 | 3.12.1–3.12.8 | `switch/03-internals-switch-compilation.md` |
| §1.17 | Text blocks | 16 | 1.17.1–1.17.16 | `text-blocks/01-basics.md` |
| §2.11 | Text blocks in practice | 8 | 2.11.1–2.11.8 | `text-blocks/02-in-practice.md` |
| §3.13 | Text block compilation | 6 | 3.13.1–3.13.6 | `text-blocks/03-internals-compilation.md` |
| §1.18 | Virtual threads — the model | 24 | 1.18.1–1.18.24 | `virtual-threads/01-basics.md` |
| §2.12 | Virtual threads in production | 18 | 2.12.1–2.12.18 | `virtual-threads/02-in-production.md` |
| §3.14 | Virtual thread internals | 18 | 3.14.1–3.14.18 | `virtual-threads/03-internals-virtual-threads.md` |
| §1.19 | Structured concurrency | 16 | 1.19.1–1.19.16 | `structured-concurrency/01-basics.md` |
| §2.13 | Structured concurrency and scoped values in practice | 10 | 2.13.1–2.13.10 | `structured-concurrency/02-in-practice.md` |
| §3.15 | Structured concurrency and scoped values internals | 8 | 3.15.1–3.15.8 | `structured-concurrency/03-internals.md` |
| §1.20 | The library additions, 9 → 21 | 24 | 1.20.1–1.20.24 | `library-additions/01-basics.md` |
| §2.1 | The master tables | 8 | 2.1.1–2.1.8 | `cost-model/02-master-tables.md` |
| §2.15 | Which construct | 10 | 2.15.1–2.15.10 | `which-construct/02-which-construct.md` |
| §4.1 | A functional toolkit from scratch | 8 | 4.1.1–4.1.8 | `build-it/01-functional-toolkit.md` |
| §4.2 | `MyStream` — a lazy fused pipeline | 10 | 4.2.1–4.2.10 | `build-it/02-mystream.md` |
| §4.3 | Collectors from scratch | 7 | 4.3.1–4.3.7 | `build-it/03-collectors-and-myoptional.md` |
| §4.4 | `MyOptional` | 6 | 4.4.1–4.4.6 | `build-it/03-collectors-and-myoptional.md` |
| §4.5 | Records, sealed types and patterns from scratch | 8 | 4.5.1–4.5.8 | `build-it/04-records-sealed-patterns.md` |
| §4.6 | Concurrency builds | 8 | 4.6.1–4.6.8 | `build-it/05-concurrency-builds.md` |
| §4.7 | Filling the Java 21 gaps | 6 | 4.7.1–4.7.6 | `build-it/06-filling-the-21-gaps.md` |
| §4.8 | Diagnostic harnesses | 12 | 4.8.1–4.8.12 | `build-it/07-diagnostic-harnesses.md` |
| §5.1 | The questions, with the answer shape | 32 | 5.1.1–5.1.32 | `94-interview-questions-a.md` |
| §5.1 | The questions, with the answer shape | 32 | 5.1.33–5.1.64 | `94-interview-questions-b.md` |
| §5.1 | The questions, with the answer shape | 31 | 5.1.65–5.1.95 | `94-interview-questions-c.md` |
| §5.2 | The trap index | 5 | 5.2.1–5.2.5 | `95-traps-drills-and-checklist.md` |
| §5.3 | One-line assertions and drills | 9 | 5.3.1–5.3.9 | `95-traps-drills-and-checklist.md` |

Part wrap-up files (`90`–`93`) own no leaves of their own: each summarises its part and adds
that part's 10 Q&As and 5 puzzles, as the prompt's output contract specifies.

---

## Verified figures

The prompt flagged three figures as unverified because `openjdk.org` returned HTTP 403 during
the syllabus research pass. All three were re-fetched from primary source before any writer was
dispatched. Two of them needed correcting.

**1. The virtual-thread scheduler's `maxPoolSize` — verified, and the flat "256" is wrong.**
`VirtualThread.createDefaultScheduler()` at the `jdk-21+35` tag
(`raw.githubusercontent.com/openjdk/jdk/jdk-21+35/src/java.base/share/classes/java/lang/VirtualThread.java`):

```java
String parallelismValue = System.getProperty("jdk.virtualThreadScheduler.parallelism");
String maxPoolSizeValue = System.getProperty("jdk.virtualThreadScheduler.maxPoolSize");
String minRunnableValue = System.getProperty("jdk.virtualThreadScheduler.minRunnable");
if (parallelismValue != null) {
    parallelism = Integer.parseInt(parallelismValue);
} else {
    parallelism = Runtime.getRuntime().availableProcessors();
}
if (maxPoolSizeValue != null) {
    maxPoolSize = Integer.parseInt(maxPoolSizeValue);
    parallelism = Integer.min(parallelism, maxPoolSize);
} else {
    maxPoolSize = Integer.max(parallelism, 256);
}
if (minRunnableValue != null) {
    minRunnable = Integer.parseInt(minRunnableValue);
} else {
    minRunnable = Integer.max(parallelism / 2, 1);
}
Thread.UncaughtExceptionHandler handler = (t, e) -> { };
boolean asyncMode = true; // FIFO
return new ForkJoinPool(parallelism, factory, handler, asyncMode,
             0, maxPoolSize, minRunnable, pool -> true, 30, SECONDS);
```

So: parallelism defaults to `availableProcessors()`; `maxPoolSize` defaults to
`Integer.max(parallelism, 256)` — **256 is a floor, not a flat default**, and on a machine with
more than 256 available processors `maxPoolSize` equals parallelism. `minRunnable` defaults to
`max(parallelism / 2, 1)`. `asyncMode = true` with the source's own `// FIFO` comment is the
evidence for the FIFO claim. Setting `maxPoolSize` below the processor count also clamps
parallelism down to it.

**2. `LEAF_TARGET` and `suggestTargetSize` — verified, and "rounded up" is wrong.**
`AbstractTask` at the same tag:

```java
private static final int LEAF_TARGET = ForkJoinPool.getCommonPoolParallelism() << 2;

public static int getLeafTarget() {
    Thread t = Thread.currentThread();
    if (t instanceof ForkJoinWorkerThread) {
        return ((ForkJoinWorkerThread) t).getPool().getParallelism() << 2;
    }
    else {
        return LEAF_TARGET;
    }
}

public static long suggestTargetSize(long sizeEstimate) {
    long est = sizeEstimate / getLeafTarget();
    return est > 0L ? est : 1L;
}
```

`LEAF_TARGET` is as the prompt states. `suggestTargetSize` is **floored integer division,
clamped to a minimum of 1** — not rounded up. And the target is not fixed to the common pool:
`getLeafTarget()` uses the *current* pool's parallelism when the calling thread is a ForkJoin
worker, which is why a stream submitted into your own pool decomposes against that pool's
width. The class javadoc states the intent: "To allow load balancing, we over-partition,
currently to approximately four tasks per processor, which enables others to help out if leaf
tasks are uneven or some processors are otherwise busy."

**3. The LVTI style guide's `G1`–`G7` — verified, printable.**
`openjdk.org/projects/amber/guides/lvti-style-guide` returned 200 on re-fetch. Principles:
**P1** reading code is more important than writing code; **P2** code should be clear from local
reasoning; **P3** code readability shouldn't depend on IDEs; **P4** explicit types are a
tradeoff. Guidelines: **G1** choose variable names that provide useful information; **G2**
minimize the scope of local variables; **G3** consider `var` when the initializer provides
sufficient information to the reader; **G4** use `var` to break up chained or nested
expressions with local variables; **G5** don't worry too much about "programming to the
interface" with local variables; **G6** take care when using `var` with diamond or generic
methods; **G7** take care when using `var` with literals.

---

## Corrections carried through from the previous guide

The prompt names three claims in `src/topics/04-modern-java.md` that must be corrected rather
than carried forward. Each is fixed at every point it appears:

1. **Pinning is dated.** `synchronized` pins a virtual thread on Java 21; JEP 491 makes object
   monitors continuation-aware in Java 24 and removes that cause. Native and foreign frames
   still pin, so the `jdk.VirtualThreadPinned` JFR event survives and the diagnostic does not
   disappear. "Use `ReentrantLock`" is therefore a version-scoped answer, not a permanent rule.
2. **The common pool's width is stated in both halves.** `ForkJoinPool.commonPool()`'s default
   parallelism is `availableProcessors() - 1`, *and* the thread that submits the terminal
   operation participates in the computation, so the effective width equals the core count.
3. **Structured concurrency is named at both shapes.** Java 21 (JEP 453, preview): `fork`
   returns `Subtask<T>`, with `ShutdownOnFailure` and `ShutdownOnSuccess` as the policies,
   inside a try-with-resources block on the owning thread. Java 25 (JEP 505): public
   constructors are replaced by static `open()` factories and the two shutdown policies by a
   composable `Joiner`.

---

## Reading order

### First careful pass, cover to cover

Read in file-plan order, 1 to 69. It is built so that nothing depends on a later file: the
release model comes before any version claim, the surface of a feature before its cost model,
and its cost model before its internals.

If you want the shorter first pass, read every `01-basics*` and `02-*` file and skip the
`03-internals*` files and Part 4 on the first pass. That is the whole of Parts 1 and 2 —
the surface plus the judgement — and it stands on its own.

### Night-before re-read

In this order, and nothing else:

1. `95-traps-drills-and-checklist.md` — the trap index (D-179), the version-stale table
   (D-180) and the numbers card (D-181). These three tables are the highest density in the set.
2. `cost-model/02-master-tables.md` — the seven master comparison tables.
3. `which-construct/02-which-construct.md` — ten decisions, one line each.
4. The four `9x` part wrap-ups, for the summary tables and the puzzles only.
5. `94-interview-questions-a/b/c.md` — skim the 95 question headings; read the answer only
   where the heading does not already trigger it.
6. The `## Cheat sheet` section of any subject you are shaky on, and nothing else from that
   file.

---

## Open questions

Populated as writer and illustrator envelopes return `unverified` lines.

1. **D-036** — one unavoidable line crossing. `LongStream`'s `boxed`/`mapToObj` return edge
   crosses the `mapToDouble` narrowing edge, because `LongStream` sits directly beneath
   `Stream<T>` between the two side-routed primitive streams. One crossing, reported, within the
   diagram spec's allowance.
2. **D-062** — one unavoidable line crossing, where the "no (non-null)" flow arrow out of the
   null-check decision passes the top of the `invokedynamic`/`tableswitch` corridor.
3. **D-077** — the `-Djdk.tracePinnedThreads=full` block is the documented output *format*, not a
   live capture. This machine runs JDK 25, which already implements JEP 491, so `synchronized` no
   longer pins here: running the reproducer with the flag produced no trace output at all (exit 0,
   empty stderr, verified). Settling it would need a real JDK 21 runtime. The diagram is labelled
   as Java 21 behaviour, which is what the notes target.
4. **D-081 / D-082** — the cancellation and hedging illustrations put the identity vendor and the
   watchlist replica at tail latencies rather than their p50s. Every figure used is verbatim from
   the domain (identity vendor p99 38 s, watchlist provider p99 25 s) and the diagrams say
   on their face that these are tail instances; no number was invented.

### Resolved during the run

- **D-052** carried a javac diagnostic reproduced from memory. Compiled the case: the real message
  is `error: cannot assign a value to final variable bonusPortion`. The SVG was corrected and
  re-rendered.
- **Syllabus leaf 3.12.7 is inverted and has been corrected everywhere it lands.** The prompt says
  an exhaustive enum switch expression's synthetic default throws `IncompatibleClassChangeError`
  on Java 21, having replaced older `MatchException` shapes. Verified by separate compilation on
  this machine, it is the other way round: `IncompatibleClassChangeError` through `--release 17`
  and `--release 14`, `java.lang.MatchException` from `--release 21`, emitted as
  `new java/lang/MatchException` + `athrow` in `javap -c`. Every writer packet touching §1.16,
  §3.12 or §1.15 carries the verified evidence.

---

## Deferred

No leaves deferred. Every one of the 984 is owned by exactly one row above.
