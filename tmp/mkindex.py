#!/usr/bin/env python3
"""Generates 00-index.md for topic 04 modern-java from the prompt's own tables."""
import re, json, os

ROOT = "/Users/rajat.chikkodikar/Desktop/My-files/rough"
PROMPT = f"{ROOT}/src/metadata/prompts/04-modern-java-prompt.md"
OUT = f"{ROOT}/src/notes/detailed/04-modern-java/00-index.md"
HASH = "9607419455fa0ffff7dcc05b333516f8965b9ff7a02ff8c7f33be5f3d4a31ece"

lines = open(PROMPT).read().split('\n')
secs = json.load(open('/tmp/secs.json'))

# ---- diagram manifest, parsed and (separately) sliced verbatim ----
diag = {}
for l in lines:
    m = re.match(r'^\| (D-\d{3}) \| (.*?) \| (.*?) \| (.*?) \| (.*) \|$', l)
    if m:
        did, title, leaf, typ, must = m.groups()
        diag[did] = dict(title=title.strip(), leaf=leaf.strip(),
                         type=typ.strip(), must=must.strip())
        toks = re.findall(r'\d+\.\d+\.\d+', leaf)
        diag[did]['secs'] = list(dict.fromkeys(
            re.match(r'(\d+\.\d+)\.', t).group(1) for t in toks))
assert len(diag) == 182, len(diag)
MANIFEST_VERBATIM = '\n'.join(lines[2783:2990])   # "## Part 1 diagrams" .. D-182 row

# ---- syllabus leaf id list per section (for leaf ranges) ----
leafids = {}
cur = None
for l in lines[505:2760]:
    m = re.match(r'^## §(\d+\.\d+)', l)
    if m:
        cur = m.group(1); leafids[cur] = []
    m2 = re.match(r'^(\d+\.\d+\.\d+) ', l)
    if m2 and cur and m2.group(1).startswith(cur + '.'):
        leafids[cur].append(m2.group(1))
for s, ids in leafids.items():
    assert len(ids) == secs[s]['leaves'], (s, len(ids), secs[s]['leaves'])

# ---- the file plan: (path, [sections], leaf-slice override, primary concepts, examples) ----
# leaf-slice override: None = whole section(s); else (section, first_idx, last_idx) inclusive 0-based
P = []
def add(path, sect, part, tier, concepts, examples, slice_=None, subject=None):
    P.append(dict(file=path, secs=sect, part=part, tier=tier,
                  concepts=concepts, examples=examples, slice=slice_,
                  subject=subject or path.split('/')[0].replace('-', ' ')))

add('platform-and-releases/01-basics.md', ['1.1'], 1, 'BASICS',
    'the six-month release train; LTS as a commercial not technical property; preview/incubator/experimental as three maturity ladders; `--release` vs `-source`/`-target`; class-file major versions',
    'The QuizStakes estate itself: which JDK `PaymentService` and `FundsLedger` run on, and a `BalanceView` call to `List.of(...)` compiled `-source 8` that `NoSuchMethodError`s in production')
add('platform-and-releases/02-migration.md', ['2.14'], 2, 'INTERMEDIATE',
    'what breaks at 9/11/16/17/18/21; JEP 400 UTF-8 as the silent behaviour change; the library floor; the mechanical refactors worth doing; the safe rollout order',
    'Migrating `FundsLedger` and `DocumentVerification` from 8 to 21: `String.getBytes()` on a payout file at 18, and `getFirst()` clashing on a hand-rolled sequenced type at 21')
add('platform-and-releases/03-internals-version-delta.md', ['3.16'], 3, 'INTERNALS',
    'the release-by-release delta 8 to 25; the consolidated feature-to-version table; the removed-or-disabled table; how to answer "what is new in Java N"',
    'Dating every claim in the guide against the release QuizStakes actually runs; §12 payment flows as the code being upgraded')
add('platform-and-releases/04-internals-observability.md', ['3.17'], 3, 'INTERNALS',
    '`javap -c -p -v` as the evidence for every desugaring claim; `jshell` experiments; JFR for this topic; the JSON thread dump; JMH discipline; static analysis rules',
    'Verifying the guide\'s own claims on the `FundsLedger` classes: `-Xlog:class+load=info` while a stake-reservation pipeline warms up')
add('functional-interfaces/01-basics.md', ['1.2'], 1, 'BASICS',
    'the SAM definition and the `Object`-method exclusion; the six core shapes and their narrowings; the 43-interface inventory and its naming scheme; why the primitive specialisations exist; the shapes the JDK withholds',
    '`Function<LedgerEntry, Money>`, `Predicate<Restriction>`, `Supplier<IdempotencyKey>`; a domain-named `StakeRule` beating `Function<Reservation, Money>`; §15 Example Bank rows on restriction evaluation')
add('lambdas/01-basics.md', ['1.3'], 1, 'BASICS',
    'lambda syntax forms; the poly expression and target typing; `this` and lexical transparency; capture by value and effectively-final; loop-variable capture; the recursion and checked-exception limits',
    '`BonusService` registering a `Runnable`; `FundsLedger.reserveStake` capturing a `Money stake`; iterating `reservations` versus a classic `for` index')
add('lambdas/02-cost-and-choice.md', ['2.2'], 2, 'INTERMEDIATE',
    'first-call linkage cost versus steady state; non-capturing caching versus per-evaluation allocation; the anonymous-class alternative; megamorphic call sites; composition; the four checked-exception workarounds',
    'A composite `Predicate<Restriction>` reduced from a list of restriction rules; an `IOException`-throwing payout-file read inside a `map` over 7k bank withdrawals')
add('lambdas/03-internals-translation.md', ['3.1'], 3, 'INTERNALS',
    '`lambda$` desugaring; `invokedynamic` and `LambdaMetafactory.metafactory`\'s six parameters; static versus dynamic arguments; `InnerClassLambdaMetafactory` and hidden classes; the method-reference shortcut; serializable lambdas',
    '`javap -c -p` on a `FundsLedger` class holding one capturing and one non-capturing lambda over `Reservation`')
add('lambdas/04-internals-capture-and-identity.md', ['3.2'], 3, 'INTERNALS',
    'capture by value into a spun field; capturing `this` versus capturing a field read; the listener-registry leak; lambda identity and why `==` is meaningless; what the JIT does with a lambda call site',
    'A static `NotificationService` registry holding a lambda that reads a `ProfileService` instance field, and the retained subgraph that follows')
add('method-references/01-basics.md', ['1.4'], 1, 'BASICS',
    'the six forms; unbound receiver becoming the first parameter; receiver evaluation at capture time; the ambiguity cases; constructor references to records; the bytecode difference from a lambda',
    '`Money::of`, `ledger::append`, `Reservation::amount`, `StakeSplit::new`; a `ledger::flush` reference captured then the variable reassigned')
add('streams/01-basics-the-model.md', ['1.5'], 1, 'BASICS',
    'the javadoc\'s five properties; source/intermediate/terminal anatomy; laziness and fusion; short-circuiting; encounter order; non-interference and statelessness; single consumption; closing',
    'A pipeline over 95k card deposits per day; the two exact `IllegalStateException` messages; `Files.lines(paymentRunFile)` needing a close')
add('streams/02-sources.md', ['1.6'], 1, 'BASICS',
    'every stream source and its guarantees; `IntStream.range` as the best-splitting source; `Stream.iterate`\'s two forms; `Stream.concat`\'s left-deep tree; `StreamSupport` as the escape hatch; the sources that need closing',
    '`ledgerEntries.stream()`, `IntStream.range(0, 2_800_000)` over a day of stake reservations, `Files.lines(paymentRunFile)`, and a hand-written JDBC bridge for `ResultSet`')
add('streams/03-intermediate-operations.md', ['1.7'], 1, 'BASICS',
    'every intermediate operation with its flags; `flatMap` versus `mapMulti`; `takeWhile` as a prefix not a test; `sorted` as a barrier that throws at terminal time; `peek` elision; the absent `zip`/windowing; operation order as cost',
    'Stake amounts `[4.20, 3.33, 12.00, 2.10, 1.05]` under `amount < 5`; `.sorted(byAmount).limit(10)` over 2.8M stake reservations; `Movement` values holding zero, one or three `LedgerEntry`s')
add('streams/04-terminal-operations.md', ['1.8'], 1, 'BASICS',
    'the three `reduce` overloads and their contracts; identity and associativity in parallel; `collect` versus `reduce` versus `forEach`; `count()`\'s Java 9 bypass; vacuous `allMatch`; `findFirst` versus `findAny`; the null policy across the list-producing paths',
    'Summing `Money` over 95k card deposits; subtraction over `[65, 480, 42, 180]`; a four-leaf task tree over 2.8M reservations')
add('streams/05-primitive-streams.md', ['1.9'], 1, 'BASICS',
    'the three primitive streams and the conversions between the four shapes; why there is no `CharStream`; `OptionalInt`\'s deliberately thinner API; `IntStream.sum()` overflow; the memory arithmetic for boxed versus primitive',
    '2.8M stake amounts in minor units as `int[]` versus `List<Integer>`; the `int` total wrapping past 2 147 483 647')
add('streams/06-cost-model.md', ['2.3'], 2, 'INTERMEDIATE',
    'what a pipeline costs against a loop; the allocation profile before the first element moves; debuggability and stack depth; ordering as optimisation; `sorted().findFirst()` versus `min`; when to use a loop and when a stream',
    'A three-stage pipeline over card deposits; comparator-invocation counts at N = 95,000; the accidental O(n·m) from re-streaming restrictions inside a loop over clients')
add('streams/07-parallel-streams.md', ['2.4'], 2, 'INTERMEDIATE',
    'the common pool and its true effective width; the four preconditions and the N×Q heuristic; source splitting quality; ordering and merge costs; shared mutable state; why collectors are safe; the default answer in a server',
    'The identity vendor\'s 38 s p99 blocking every common-pool worker; `parallelStream().forEach(list::add)` over ledger entries; 40 deposits/sec versus 2.8M reservations/day')
add('streams/08-internals-pipeline.md', ['3.3'], 3, 'INTERNALS',
    '`AbstractPipeline`\'s twelve fields and the stage chain; `Sink`\'s four-method protocol; `opWrapSink` and `wrapSink` walking backwards; `copyInto`/`copyIntoWithCancel`; the `StreamOpFlag` lattice; how `count()` bypasses the pipeline',
    '`deposits.stream().filter(...).map(...).collect(...)` walked stage by stage with `depth` 0/1/2; the two `linkedOrConsumed` messages verbatim')
add('streams/09-internals-spliterator.md', ['3.4'], 3, 'INTERNALS',
    'the eight characteristics with their hex bits; `SIZED` versus `SUBSIZED`; `trySplit` returning the prefix; the per-collection spliterators; the `IteratorSpliterator` batching fallback; writing one that splits well',
    'An `ArrayList` of 95,000 card deposits split 0–47,499 / 47,500–94,999; `LinkedList` and `Files.lines(paymentRunFile)` as the batching cases')
add('streams/10-internals-parallel-execution.md', ['3.5'], 3, 'INTERNALS',
    '`AbstractTask` and the leaf-size target; the op implementation classes; `ReduceTask` and the combine tree; `ForEachTask` versus `ForEachOrderedTask`; `SliceOps` ordering; the common pool, work stealing and `ManagedBlocker`; exception propagation',
    'An `AbstractTask` tree over 2.8M reservations on an 8-core box, with the leaf count and leaf size worked out')
add('collectors/01-basics-a.md', ['1.10'], 1, 'BASICS',
    'the five-function `Collector` contract and the three characteristics; the `toX` family; `toMap`\'s duplicate-key and null-value failures; `joining`; the summing/averaging/summarizing family and Kahan summation; `mapping`/`filtering`/`flatMapping`/`collectingAndThen`',
    'Collecting 95k card deposits by rail; `toMap` on `(ClientId, Money)` with a duplicate identity; `summingDouble` over deposits averaging 65',
    slice_=('1.10', 0, 15))
add('collectors/01-basics-b.md', ['1.10'], 1, 'BASICS',
    '`groupingBy`\'s three overloads and the types it really returns; the null-classifier NPE; `partitioningBy` always carrying both keys; `groupingByConcurrent` and the three conditions for a concurrent reduction; `teeing`; hand-writing a collector; the collector inventory',
    '`groupingBy(Deposit::rail, mapping(Deposit::amount, toList()))`; `partitioningBy` over an empty reservation stream; `teeing` for min-and-max withdrawal in one pass',
    slice_=('1.10', 16, 29))
add('collectors/02-in-anger.md', ['2.5'], 2, 'INTERMEDIATE',
    'multi-level grouping and reading the nested type; `filtering` versus a pre-`filter`; choosing the map implementation; `toMap` merge strategies; `teeing`; a bounded top-N collector; a boxing-free statistics collector; three routes to an immutable result',
    'Top-3 withdrawals by amount (180, 260, 92) merged across two leaves; grouping card deposits by rail where one rail has nothing above 100')
add('collectors/03-internals-collectors.md', ['3.6'], 3, 'INTERNALS',
    '`CollectorImpl` and the six pre-built characteristic sets; `toList`\'s three functions and the O(n) combine tree; `groupingBy`\'s `computeIfAbsent` and its unchecked-cast finisher; Kahan compensation in `summingDouble`; what `IDENTITY_FINISH` saves',
    'Summing 95,000 card deposits averaging 65 as `double`s, naive total against compensated total')
add('optional/01-basics.md', ['1.11'], 1, 'BASICS',
    'the return-type-only purpose and the javadoc API note; value-based and not `Serializable`; the full method table by version; `orElse`\'s eager argument; the `isPresent`+`get` anti-pattern; the four places it must never appear; `map`\'s null-mapper behaviour',
    '`findClient(id)` chained `Client` to `Account` to `Wallet` to `Money.ZERO`; a `loadDefaultFromDatabase()` call counter proving eager evaluation')
add('optional/02-discipline.md', ['2.6'], 2, 'INTERMEDIATE',
    'the rule set in one place; the chain style; `orElse`/`orElseGet`/`orElseThrow` decision table; `or` for a fallback chain; `Optional` inside a stream; the Spring Data and Jackson contracts; the four absence strategies compared',
    '`findById` on a client repository versus `getReferenceById`; `Money.ZERO` as a constant default against a database fallback against a `RestrictedActionException`')
add('optional/03-internals-optional.md', ['3.7'], 3, 'INTERNALS',
    'the single `value` field and the shared `EMPTY`; `@jdk.internal.ValueBased` and what it forbids; `map`\'s one-line body; `get` and `orElseThrow` being identical; the 16-byte cost and when escape analysis removes it; the Valhalla trajectory',
    'An `Optional<Client>` on the heap; a five-`map` chain over a client lookup with and without escape analysis')
add('var/01-basics.md', ['1.12'], 1, 'BASICS',
    '`var` as compile-time-only inference and a reserved type name; where it is legal and where it is not; `var x = null` and the array shorthand; the diamond inferring `Object`; poly expressions; non-denotable types; when `var` hurts',
    '`var positions = new ArrayList<>()` losing `Position`; `var total = 0` as an accumulator over minor-unit stake amounts')
add('var/02-in-practice.md', ['2.7'], 2, 'INTERMEDIATE',
    'a style policy defensible in review; the cases where `var` clearly wins; the interface-versus-implementation trap; numeric-literal width; `var` in lambda parameters; what refactoring does to a `var` local',
    'Iterating `Map.Entry<RestrictionKey, Restriction>`; a `Map<String, List<Map<String, Integer>>>` of per-rail counts')
add('var/03-internals-inference.md', ['3.8'], 3, 'INTERNALS',
    'standalone type plus upward projection; the `LocalVariableTable` as the only trace; why a field or parameter could never work; diamond inference with no target type; anonymous-class initialisers',
    '`List<? extends Money> amounts; var first = amounts.get(0);` projecting the capture variable away to `Money`')
add('records/01-basics-a.md', ['1.13'], 1, 'BASICS',
    'a record as a nominal tuple; the generated members and implicit modifiers; the canonical and compact constructors; validation by reassigning the parameter; alternate constructors and accessibility; generic, local and nested records',
    '`record StakeSplit(Money bonusPortion, Money cashPortion)` with the compact constructor enforcing that the two sum exactly to the stake, worked on the 3.33 = 0.33 + 3.00 split',
    slice_=('1.13', 0, 14))
add('records/01-basics-b.md', ['1.13'], 1, 'BASICS',
    'shallow immutability and the defensive-copy fix; the array-component `equals` failure; the generated `equals`/`hashCode`/`toString` semantics; `NaN` and `-0.0` inside a record; reflection; record serialization closing the validation hole; the record cliff',
    '`record PaymentRun(RunId id, List<WithdrawalTransaction> items)` constructed from a caller-held `ArrayList`; a `Money` component\'s `BigDecimal` versus a raw `double` price component',
    slice_=('1.13', 15, 27))
add('records/02-in-practice.md', ['2.8'], 2, 'INTERMEDIATE',
    'records as DTOs at an HTTP boundary; Jackson and Spring binding and the `-parameters` flag; Bean Validation targets; why a record cannot be a JPA entity but is an excellent projection; compound map keys; local records; the wither pattern; floating-point components',
    'A `DepositRequest`/`DepositResponse` pair at the `ApplicationGateway`; `RestrictionKey(RestrictionType, RestrictionSource)` as a compound map key')
add('records/03-internals-records.md', ['3.9'], 3, 'INTERNALS',
    'the `Record` class-file attribute and its `record_component_info` entries; `ObjectMethods.bootstrap` behind the three generated methods; why the `hashCode` algorithm is unspecified; the compact-constructor desugaring in `javap`; record serialization and the ignored hooks; blocked `setAccessible`',
    '`javap -v` on `StakeSplit`, with the component-name string `"bonusPortion;cashPortion"` and one `MethodHandle` getter per component')
add('sealed-types/01-basics.md', ['1.14'], 1, 'BASICS',
    '`sealed` and `permits`; the final/sealed/non-sealed obligation on every permitted subtype; the same-module rule and direct extension; the two ADT shapes; sealed versus enum; what sealing buys you and the compiler; the cost across an API boundary',
    '`sealed interface Verdict permits DocumentVerdict, ScreeningVerdict, ReviewVerdict, WealthVerdict`; `RestrictionType` as the enum that should stay an enum')
add('sealed-types/02-data-oriented-programming.md', ['2.9'], 2, 'INTERMEDIATE',
    'sum of products; data-oriented programming as Goetz frames it; Visitor replaced by a sealed interface plus a pattern switch; the expression problem; a state machine and a `Result` type as sealed hierarchies; sealed types across a published API; serialising a sealed hierarchy',
    'The `Verdict` hierarchy against a `VerdictVisitor`; the account lifecycle (`PENDING_VERIFICATION`, `ACTIVE`, `DORMANT`, `CLOSING`, `CLOSED`) as a sealed interface of records')
add('sealed-types/03-internals-sealed.md', ['3.10'], 3, 'INTERNALS',
    'the `PermittedSubclasses` attribute and the absence of `ACC_SEALED`; `non-sealed` emitting nothing; load-time enforcement surviving bytecode manipulation; the same-module check; narrowing reference conversion; the separate-compilation hazard',
    'The `Verdict` class file with four constant-pool indices, and a bytecode-manipulated fifth subclass rejected at load time')
add('pattern-matching/01-basics.md', ['1.15'], 1, 'BASICS',
    'a pattern as test, extraction and binding; flow scoping including negation and `&&`/`||`; `case null` and the NPE without it; `when` guards; record patterns and nesting; exhaustiveness and the exempt legacy selector types; `MatchException`; dominance',
    'Switching over `Verdict`; `case Movement(LedgerEntry(Position from, Money amount), LedgerEntry to)` as the nested deconstruction')
add('pattern-matching/02-in-anger.md', ['2.10'], 2, 'INTERMEDIATE',
    'refactoring an `instanceof` chain step by step; record deconstruction replacing getter-plus-condition; guards versus nested switches; naming the total pattern; handling null explicitly; migration risk and exhaustiveness drift; the `typeSwitch` cost model; the readability limit',
    'The `Verdict` `if`/`else if` chain converted in four steps; a fifth `Verdict` case added and only the hierarchy redeployed')
add('pattern-matching/03-internals-pattern-matching.md', ['3.11'], 3, 'INTERNALS',
    '`instanceof` patterns compiling to plain bytecode; flow scoping as a compile-time analysis; `SwitchBootstraps.typeSwitch` returning an index into a `tableswitch`; the bootstrap\'s static arguments; deconstruction as ordered accessor calls; exhaustiveness and dominance in the JLS; null routing',
    'The `javap -c` listing for a pattern switch over `Verdict`, and an accessor throwing during deconstruction wrapped in `MatchException`')
add('switch/01-basics.md', ['1.16'], 1, 'BASICS',
    'switch expressions and the arrow form; `yield` and why `return` is illegal; exhaustiveness in expressions and in Java 21 pattern statements; the colon form and fall-through; the permitted selector types; the `default`-in-an-enum-switch trade-off',
    'Dispatching on `RestrictionType`; a colon switch over restriction sources with a missing `break`')
add('switch/03-internals-switch-compilation.md', ['3.12'], 3, 'INTERNALS',
    '`tableswitch` versus `lookupswitch` and the density heuristic; the two-stage `String` switch; `$SwitchMap` protecting a separately compiled enum switch; the arrow form compiling identically; the operand stack at the join point; the synthetic default in an exhaustive enum switch expression',
    '`$SwitchMap$RestrictionType` contents shown, and the enum reordered without recompiling the switch')
add('text-blocks/01-basics.md', ['1.17'], 1, 'BASICS',
    'the syntax and the opening-delimiter rule; the three compile-time steps in order; incidental-whitespace computation including the closing delimiter; trailing-whitespace stripping; `\\s` and `\\` line continuation; the runtime siblings; text blocks as constant expressions',
    'The SQL text block that reads `CLIENT_CASH_AVAILABLE` positions from the ledger, with the closing delimiter moved four columns left')
add('text-blocks/02-in-practice.md', ['2.11'], 2, 'INTERMEDIATE',
    'SQL with bound parameters rather than interpolation; JSON fixtures with `formatted`; regex where the text block loses; trailing-newline discipline; text blocks in annotations and `case` labels; the absence of interpolation in Java 21',
    'The ledger-balance SQL as a text block with `?` placeholders; a `DEP-301 CAPTURED` webhook JSON fixture')
add('text-blocks/03-internals-compilation.md', ['3.13'], 3, 'INTERNALS',
    'the whole transformation happening in `javac`; the specified three-step algorithm; the exact minimal-indent computation; the result as a `CONSTANT_String_info` and therefore interned; `String.stripIndent()` as the runtime sibling; `==` on a text block and an equal literal',
    'The `javap -v` constant pool for the ledger SQL text block, already stripped')
add('virtual-threads/01-basics.md', ['1.18'], 1, 'BASICS',
    'a virtual thread as a `Thread` scheduled by the runtime; Little\'s law as the framing; carriers and the scheduler properties; mounting and unmounting and what triggers each; the cost arithmetic; the creation API; what a virtual thread refuses to do; `ThreadLocal` economics; pinning and its diagnosis; the three standing rules',
    '55k peak concurrent sessions; 1,200 stake reservations/sec at the card PSP\'s 240 ms p50 needing 288 concurrent tasks, and 13,200 at the 11 s p99')
add('virtual-threads/02-in-production.md', ['2.12'], 2, 'INTERMEDIATE',
    'the thread-per-request model restored and what the Spring flag switches; losing the pool means losing the queue; the bottleneck moving downstream; pinning drivers; `ThreadLocal` and MDC costs; thread dumps and the four JFR events; what to measure now; memory sizing; the migration checklist',
    'Tomcat at `maxThreads=200` against 55k peak sessions; 14k concurrent virtual threads arriving at a 20-connection JDBC pool')
add('virtual-threads/03-internals-virtual-threads.md', ['3.14'], 3, 'INTERNALS',
    'the three layers and `Continuation`; frame copying to and from a heap `StackChunk`; the nine-state machine; the FIFO scheduler and its verified defaults; the instrumented and non-instrumented blocking points; pinning as a continuation property and JEP 491; no preemption and pool compensation',
    'A virtual thread blocking on the card PSP\'s 240 ms p50 across four mount/unmount frames; the heap arithmetic for 1,000,000 virtual threads')
add('structured-concurrency/01-basics.md', ['1.19'], 1, 'BASICS',
    'the leak/cancellation/dump problem; the structured principle; the Java 21 `StructuredTaskScope` shape with `Subtask`; `ShutdownOnFailure` and `ShutdownOnSuccess`; `joinUntil`; the ownership and try-with-resources discipline; cancellation by interrupt; the comparison with `allOf` and `invokeAll`; scoped values',
    '`AssessmentService` forking the identity vendor (900 ms p50) and the watchlist provider (1.4 s p50, 25 s p99) under one scope')
add('structured-concurrency/02-in-practice.md', ['2.13'], 2, 'INTERMEDIATE',
    'the fan-out call with one deadline and one failure policy; hedged requests; timeouts at scope versus subtask level; which exception surfaces; nesting scopes; scoped values for request context; rebinding as shadowing; what to say in an interview',
    'A 2 s `joinUntil` deadline cutting off the watchlist provider; tenant, principal and trace id carried as scoped values instead of MDC `ThreadLocal`s')
add('structured-concurrency/03-internals.md', ['3.15'], 3, 'INTERNALS',
    '`StructuredTaskScope` on virtual threads plus a per-thread scope stack; the ownership check; `StructureViolationException` and the stack discipline; `shutdown()` versus `close()`; `ScopedValue`\'s immutable binding snapshot and its cache; why it is cheaper than `ThreadLocal`; the 19-to-26 churn table',
    'The `AssessmentService` scope tree in a JSON thread dump; a nested `where` shadowing a tenant binding')
add('library-additions/01-basics.md', ['1.20'], 1, 'BASICS',
    'the collection factories and their null hostility; the Java 9 stream and `Optional` additions; the Java 11 `String` and `Files` surface and `HttpClient`; `teeing`; `Stream.toList` and `mapMulti`; `RandomGenerator`; JEP 400\'s UTF-8 default; sequenced collections and the retrofit; `reversed()` as a view',
    'A `LinkedHashMap` of restriction keys reversed as a view; `Map.of` iteration order changing between JVM runs while listing gates')
add('cost-model/02-master-tables.md', ['2.1'], 2, 'INTERMEDIATE',
    'the master stream cost table; the feature-by-version table; the lambda/method-reference/anonymous-class table; the absence-representation table; the data-carrier table; the concurrency-model table; the list-factory table',
    'Every cost quoted against 2.8M stake reservations and 95k card deposits per day')
add('which-construct/02-which-construct.md', ['2.15'], 2, 'INTERMEDIATE',
    'the ten construct decisions, each with a default answer and the condition that overrides it',
    'Each decision resolved on a real QuizStakes call: the payment-run batch, the assessment fan-out, the restriction evaluation, the ledger projection')
add('build-it/01-functional-toolkit.md', ['4.1'], 4, 'BUILD IT',
    '`MyFunction` and `MyPredicate` with composition; `CheckedFunction` plus `unchecked`/`sneaky`; a `Result<T,E>` sealed type; a memoising decorator and the `computeIfAbsent` recursion deadlock; curry/partial; `TriFunction`',
    'Composition over `Money` fee-then-rounding on the 3.33 stake; an `IOException`-throwing payout-file read routed through `Result`')
add('build-it/02-mystream.md', ['4.2'], 4, 'BUILD IT',
    '`MySink`\'s four methods; `MyStream` fused through a sink chain; proving fusion, short-circuiting and the stateful barrier; reproducing the consumed-stream exception; a `SIZED` flag reproducing `peek` elision; a trivial parallel evaluation; a JMH comparison',
    'A `MyStream` over stake reservations traced element by element for the first three reservations')
add('build-it/03-collectors-and-myoptional.md', ['4.3', '4.4'], 4, 'BUILD IT',
    '`MyCollector` and the five-function contract; `toList`/`joining`/`groupingBy` with correct combiners; a bounded top-N and a boxing-free statistics collector; a `CONCURRENT` collector harness; `MyOptional` with the shared `EMPTY`; eager-versus-lazy and allocation harnesses',
    'Top-3 withdrawals (180, 260, 92); a `long[]` statistics accumulator over 2.8M stake minor-unit amounts')
add('build-it/04-records-sealed-patterns.md', ['4.5'], 4, 'BUILD IT',
    'the hand-written pre-record equivalent counted in lines; a `List` component written three ways; an array component\'s `equals` failure and its fixes; a sealed hierarchy with an exhaustive switch and the exact error a fourth case produces; Visitor side by side; an expression-tree interpreter; a reflective wither',
    '`StakeSplit` hand-written against the one-line record; `PaymentRun`\'s `List<WithdrawalTransaction>` and `byte[] signature`')
add('build-it/05-concurrency-builds.md', ['4.6'], 4, 'BUILD IT',
    'the echo server written twice and measured; a pinning reproducer and its `ReentrantLock` fix; a `ThreadLocal` memory harness; a `Semaphore`-bounded client; `ShutdownOnFailure` against `allOf` with a deliberate failure; a hedge; a common-pool starvation reproducer',
    '1, 1,000 and 50,000 concurrent connections; a fan-out to the identity vendor and the watchlist provider with one deliberate failure')
add('build-it/06-filling-the-21-gaps.md', ['4.7'], 4, 'BUILD IT',
    'fixed-window batching via a custom `Spliterator`; `zip` via a paired spliterator; `scan` and `distinctBy` as stateful mappers with their parallel failure demonstrated; `takeUntil` and a `mapConcurrent` on virtual threads; the `Gatherers` diff',
    'Fixed windows of 100 ledger entries out of the ~19.8M written per day')
add('build-it/07-diagnostic-harnesses.md', ['4.8'], 4, 'BUILD IT',
    'the fifteen-snippet puzzler set; stream-versus-loop and parallel-versus-sequential JMH sweeps; a source-splitting benchmark; a lambda-startup harness; a capture identity harness; a `javap` walk; a collector-combiner cost harness; exhaustiveness drift; record serialization; text-block indentation; a migration smoke harness',
    'Every harness run over QuizStakes data: 2.8M reservations, 95k deposits, the `Verdict` hierarchy, the ledger SQL text block')
add('90-interview-basics.md', ['1.1', '1.20'], 1, 'INTERVIEW',
    'Part 1 wrap-up: the summary table over the whole basics tier, 10 spoken-length Q&As, 5 predict-the-output puzzles',
    'Puzzles drawn from the ledger and reservation examples used across Part 1')
add('91-interview-intermediate.md', ['2.1', '2.15'], 2, 'INTERVIEW',
    'Part 2 wrap-up: the summary table over the whole intermediate tier, 10 spoken-length Q&As, 5 predict-the-output puzzles',
    'Puzzles drawn from the parallel-stream, collector and virtual-thread examples used across Part 2')
add('92-interview-internals.md', ['3.1', '3.17'], 3, 'INTERVIEW',
    'Part 3 wrap-up: the summary table over the whole internals tier, 10 spoken-length Q&As, 5 predict-the-output puzzles',
    'Puzzles drawn from the pipeline, record and pattern-switch internals examples used across Part 3')
add('93-interview-build-it.md', ['4.1', '4.8'], 4, 'INTERVIEW',
    'Part 4 wrap-up: the summary table over every build, 10 spoken-length Q&As, 5 predict-the-output puzzles',
    'Puzzles drawn from `MyStream`, `MyOptional` and the concurrency builds')
add('94-interview-questions-a.md', ['5.1'], 5, 'INTERVIEW',
    'questions 5.1.1–5.1.32 with the full answer shape: functional interfaces, lambdas, method references, the stream model, laziness and the intermediate operations',
    'Every answer grounded in the ledger, reservation and deposit examples the earlier files built',
    slice_=('5.1', 0, 31))
add('94-interview-questions-b.md', ['5.1'], 5, 'INTERVIEW',
    'questions 5.1.33–5.1.64 with the full answer shape: reduction, parallel streams, spliterators, `Optional`, `var`, records',
    'Every answer grounded in the collector, parallel-stream and record examples the earlier files built',
    slice_=('5.1', 32, 63))
add('94-interview-questions-c.md', ['5.1'], 5, 'INTERVIEW',
    'questions 5.1.65–5.1.95 with the full answer shape: sealed types, pattern matching, switch, text blocks, virtual threads, structured concurrency, sequenced collections',
    'Every answer grounded in the `Verdict` hierarchy, the pinning JDBC driver and the assessment fan-out',
    slice_=('5.1', 64, 94))
add('95-traps-drills-and-checklist.md', ['5.2', '5.3'], 5, 'INTERVIEW',
    'the trap index; the version-stale claims table; the five most expensive mistakes and the five interview-losing answers; the seven drills and the spaced-repetition schedule; Part 5\'s own summary table, 10 Q&As and 5 puzzles; the flat atomic concept checklist',
    'The trap index rows cite the QuizStakes example each pitfall was argued on')

# ---- leaf ranges per file ----
for p in P:
    ids = []
    if p['slice']:
        s, a, b = p['slice']
        ids = leafids[s][a:b+1]
    elif p['tier'] == 'INTERVIEW' and p['file'][0] == '9' and p['file'] < '94':
        ids = []                      # part wrap-ups own no leaves
    else:
        for s in p['secs']:
            ids += leafids[s]
    p['leafids'] = ids
    p['nleaves'] = len(ids)

owned = [i for p in P for i in p['leafids']]
assert len(owned) == 984, len(owned)
assert len(set(owned)) == 984, "leaf owned twice"

# ---- diagram assignment: primary owner is the first section that a file owns ----
sec2files = {}
for p in P:
    if p['tier'] == 'INTERVIEW' and p['file'] < '94':
        continue
    for s in p['secs']:
        sec2files.setdefault(s, []).append(p)
for p in P:
    p['diagrams'] = []
for did in sorted(diag):
    d = diag[did]
    owner = None
    for s in d['secs']:
        for cand in sec2files.get(s, []):
            # if the file is a slice, the diagram's leaf must fall inside it
            toks = [t for t in re.findall(r'\d+\.\d+\.\d+', d['leaf'])
                    if t.startswith(s + '.')]
            if any(t in cand['leafids'] for t in toks):
                owner = cand; break
        if owner: break
    if owner is None:               # fall back: first file owning any listed section
        for s in d['secs']:
            if sec2files.get(s):
                owner = sec2files[s][0]; break
    assert owner, did
    owner['diagrams'].append(did)
    d['owner'] = owner['file']
assert sum(len(p['diagrams']) for p in P) == 182

# ---- nav chain, est lines ----
tags = json.load(open('/tmp/tags.json'))
for i, p in enumerate(P):
    p['prev'] = P[i-1]['file'] if i else None
    p['next'] = P[i+1]['file'] if i < len(P)-1 else None
    heavy = 0
    for s in p['secs']:
        t = tags.get(s)
        if not t: continue
        frac = (p['nleaves'] / secs[s]['leaves']) if secs[s]['leaves'] else 1
        heavy += (t['PROVE'] + t['SOURCE'] + t['BYTECODE'] + 2*t['BUILD']) * frac
    est = int(14*p['nleaves'] + 6*heavy + 10*len(p['diagrams']) + 130)
    if p['tier'] == 'INTERVIEW' and p['file'] < '94':
        est = 420
    p['est'] = min(max(est, 250), 560)

def relpath(frm, to):
    dfrm = os.path.dirname(frm)
    return os.path.relpath(to, dfrm) if dfrm else to
for p in P:
    p['prevlink'] = relpath(p['file'], p['prev']) if p['prev'] else None
    p['nextlink'] = relpath(p['file'], p['next']) if p['next'] else None
    p['indexlink'] = '../00-index.md' if '/' in p['file'] else '00-index.md'

def rng(ids):
    if not ids: return '—'
    out = []; start = prev = ids[0]
    def num(x): return int(x.split('.')[-1])
    for i in ids[1:]:
        if num(i) == num(prev) + 1 and i.rsplit('.',1)[0] == prev.rsplit('.',1)[0]:
            prev = i; continue
        out.append(start if start == prev else f"{start}–{prev}")
        start = prev = i
    out.append(start if start == prev else f"{start}–{prev}")
    return ', '.join(out)
for p in P:
    p['range'] = rng(p['leafids'])

json.dump({'plan': P, 'diag': diag}, open('/tmp/plan2.json', 'w'), indent=1)

# ================= write 00-index.md =================
w = []
A = w.append
A("# 04 Modern Java — index and file plan")
A("")
A("**Target version: Java 21 LTS.** Anything introduced or changed in Java 22–26 is marked inline")
A("with its version. Preview status is stated on every feature where it applies.")
A("")
A("| | |")
A("|---|---|")
A("| Topic | 04 — Modern Java (Java 8 → 21 additions) |")
A("| Source prompt | `src/metadata/prompts/04-modern-java-prompt.md` |")
A(f"| Prompt SHA-256 | `{HASH}` |")
A("| Prompt last modified | 2026-08-30 13:39:51 |")
A("| Syllabus leaves | **984** (Part 1: 410 · Part 2: 190 · Part 3: 210 · Part 4: 65 · Part 5: 109) |")
A("| Diagram manifest | **182** (D-001 … D-182); 46 are `table` type and render as Markdown tables, 136 are standalone SVGs |")
A(f"| Note files planned | **{len(P)}** plus this index |")
A("")
A("On resume: if the prompt's SHA-256 no longer matches the value above, every row reverts to")
A("`planned` and the set is rebuilt. Otherwise dispatch only the rows marked `planned` or")
A("`blocked`.")
A("")
A("**Deviation from the prompt's `# OUTPUT CONTRACT`, recorded here as required.** The contract")
A("names 62 note files. Five of them were split at planning time because their leaf and tag load")
A("puts them over the 600-line hard split, which the contract explicitly permits (\"If any single")
A("file becomes unwieldy, split it further and register the new files in `00-index.md`\"):")
A("")
A("| Contract file | Split into | Reason |")
A("|---|---|---|")
A("| `collectors/01-basics.md` | `collectors/01-basics-a.md`, `01-basics-b.md` | §1.10 is 30 leaves with 16 `[PROVE]`/`[SOURCE]` obligations and 6 diagrams; split at the `mapping`/`groupingBy` concept boundary |")
A("| `records/01-basics.md` | `records/01-basics-a.md`, `01-basics-b.md` | §1.13 is 28 leaves; split between declaration/constructors and immutability/generated-members |")
A("| `94-interview-questions-and-drills.md` | `94-interview-questions-a.md`, `-b.md`, `-c.md`, `95-traps-drills-and-checklist.md` | §5.1 alone is 95 questions at spoken answer length; §5.2–§5.3 plus the Part 5 wrap-up and the atomic concept checklist form the fourth file |")
A("")
A("The flat `## Atomic concept checklist` lives at the end of the last file of the set,")
A("`95-traps-drills-and-checklist.md`, as the prompt requires. `92-interview-internals.md`")
A("carries a pointer to it rather than a second copy.")
A("")
A("---")
A("")
A("## File plan")
A("")
A("One sealed row per file. `Leaves` is authoritative: every one of the 984 leaves appears in")
A("exactly one row.")
A("")
A("| # | File | Subject | Part / tier | Leaves | Count | Primary concepts | Diagrams | Examples (QuizStakes slice) | Prev | Next | Est. lines | Status | Lines |")
A("|---|---|---|---|---|---|---|---|---|---|---|---|---|---|")
for i, p in enumerate(P, 1):
    dl = ', '.join(p['diagrams']) if p['diagrams'] else '—'
    A(f"| {i} | `{p['file']}` | {p['subject']} | Part {p['part']} — {p['tier']} | {p['range']} | {p['nleaves']} | "
      f"{p['concepts']} | {dl} | {p['examples']} | "
      f"{'`'+p['prev']+'`' if p['prev'] else '— (first)'} | {'`'+p['next']+'`' if p['next'] else '— (last)'} | "
      f"{p['est']} | planned | |")
A("")
A(f"**Totals:** {len(P)} files · 984 leaves · 182 diagram ids assigned · "
  f"{sum(p['est'] for p in P)} estimated lines.")
A("")
A("---")
A("")
A("## Diagram ownership")
A("")
A("Each `D-NNN` is embedded at the point of explanation in the file below. A `table`-type id is")
A("rendered as a Markdown table in that file and has no SVG; every other id is a standalone SVG in")
A("`diagrams/D-NNN-short-slug.svg`.")
A("")
A("| Id | Title | Type | SVG? | Owning file |")
A("|---|---|---|---|---|")
for did in sorted(diag):
    d = diag[did]
    svg = 'no — Markdown table' if d['type'] == 'table' else 'yes'
    A(f"| {did} | {d['title']} | {d['type']} | {svg} | `{d['owner']}` |")
A("")
A("### Substitutions")
A("")
A("None recorded. Any `D-NNN` an illustrator reports as not renderable is logged here with a")
A("one-line reason before the writer pass, and that writer is then instructed to render a Markdown")
A("table at that point instead of an embed.")
A("")
A("---")
A("")
A("## Diagram manifest (from the prompt, verbatim)")
A("")
A("Reproduced so a resumed run never needs the prompt to know what a `D-NNN` depicts.")
A("")
A(MANIFEST_VERBATIM)
A("")
A("---")
A("")
A("## Leaf ledger")
A("")
A("Every syllabus section, its leaf count and the file that owns it. The leaf *text* is in the")
A("prompt at the SHA-256 recorded above; this ledger fixes ownership, which is what a resumed run")
A("needs. An unassigned leaf is a planning bug, not a deferral — the assertion that the union is")
A("exactly 984 with no leaf owned twice is checked by the generator that wrote this file.")
A("")
A("| Section | Title | Leaves | Leaf ids | Owning file |")
A("|---|---|---|---|---|")
for p in P:
    if not p['leafids']: continue
    for s in p['secs']:
        ids = [i for i in p['leafids'] if i.startswith(s + '.')]
        if not ids: continue
        A(f"| §{s} | {secs[s]['title']} | {len(ids)} | {rng(ids)} | `{p['file']}` |")
A("")
A("Part wrap-up files (`90`–`93`) own no leaves of their own: each summarises its part and adds")
A("that part's 10 Q&As and 5 puzzles, as the prompt's output contract specifies.")
A("")
A("---")
A("")
A("## Verified figures")
A("")
A("The prompt flagged three figures as unverified because `openjdk.org` returned HTTP 403 during")
A("the syllabus research pass. All three were re-fetched from primary source before any writer was")
A("dispatched. Two of them needed correcting.")
A("")
A("**1. The virtual-thread scheduler's `maxPoolSize` — verified, and the flat \"256\" is wrong.**")
A("`VirtualThread.createDefaultScheduler()` at the `jdk-21+35` tag")
A("(`raw.githubusercontent.com/openjdk/jdk/jdk-21+35/src/java.base/share/classes/java/lang/VirtualThread.java`):")
A("")
A("```java")
A('String parallelismValue = System.getProperty("jdk.virtualThreadScheduler.parallelism");')
A('String maxPoolSizeValue = System.getProperty("jdk.virtualThreadScheduler.maxPoolSize");')
A('String minRunnableValue = System.getProperty("jdk.virtualThreadScheduler.minRunnable");')
A("if (parallelismValue != null) {")
A("    parallelism = Integer.parseInt(parallelismValue);")
A("} else {")
A("    parallelism = Runtime.getRuntime().availableProcessors();")
A("}")
A("if (maxPoolSizeValue != null) {")
A("    maxPoolSize = Integer.parseInt(maxPoolSizeValue);")
A("    parallelism = Integer.min(parallelism, maxPoolSize);")
A("} else {")
A("    maxPoolSize = Integer.max(parallelism, 256);")
A("}")
A("if (minRunnableValue != null) {")
A("    minRunnable = Integer.parseInt(minRunnableValue);")
A("} else {")
A("    minRunnable = Integer.max(parallelism / 2, 1);")
A("}")
A("Thread.UncaughtExceptionHandler handler = (t, e) -> { };")
A("boolean asyncMode = true; // FIFO")
A("return new ForkJoinPool(parallelism, factory, handler, asyncMode,")
A("             0, maxPoolSize, minRunnable, pool -> true, 30, SECONDS);")
A("```")
A("")
A("So: parallelism defaults to `availableProcessors()`; `maxPoolSize` defaults to")
A("`Integer.max(parallelism, 256)` — **256 is a floor, not a flat default**, and on a machine with")
A("more than 256 available processors `maxPoolSize` equals parallelism. `minRunnable` defaults to")
A("`max(parallelism / 2, 1)`. `asyncMode = true` with the source's own `// FIFO` comment is the")
A("evidence for the FIFO claim. Setting `maxPoolSize` below the processor count also clamps")
A("parallelism down to it.")
A("")
A("**2. `LEAF_TARGET` and `suggestTargetSize` — verified, and \"rounded up\" is wrong.**")
A("`AbstractTask` at the same tag:")
A("")
A("```java")
A("private static final int LEAF_TARGET = ForkJoinPool.getCommonPoolParallelism() << 2;")
A("")
A("public static int getLeafTarget() {")
A("    Thread t = Thread.currentThread();")
A("    if (t instanceof ForkJoinWorkerThread) {")
A("        return ((ForkJoinWorkerThread) t).getPool().getParallelism() << 2;")
A("    }")
A("    else {")
A("        return LEAF_TARGET;")
A("    }")
A("}")
A("")
A("public static long suggestTargetSize(long sizeEstimate) {")
A("    long est = sizeEstimate / getLeafTarget();")
A("    return est > 0L ? est : 1L;")
A("}")
A("```")
A("")
A("`LEAF_TARGET` is as the prompt states. `suggestTargetSize` is **floored integer division,")
A("clamped to a minimum of 1** — not rounded up. And the target is not fixed to the common pool:")
A("`getLeafTarget()` uses the *current* pool's parallelism when the calling thread is a ForkJoin")
A("worker, which is why a stream submitted into your own pool decomposes against that pool's")
A("width. The class javadoc states the intent: \"To allow load balancing, we over-partition,")
A("currently to approximately four tasks per processor, which enables others to help out if leaf")
A("tasks are uneven or some processors are otherwise busy.\"")
A("")
A("**3. The LVTI style guide's `G1`–`G7` — verified, printable.**")
A("`openjdk.org/projects/amber/guides/lvti-style-guide` returned 200 on re-fetch. Principles:")
A("**P1** reading code is more important than writing code; **P2** code should be clear from local")
A("reasoning; **P3** code readability shouldn't depend on IDEs; **P4** explicit types are a")
A("tradeoff. Guidelines: **G1** choose variable names that provide useful information; **G2**")
A("minimize the scope of local variables; **G3** consider `var` when the initializer provides")
A("sufficient information to the reader; **G4** use `var` to break up chained or nested")
A("expressions with local variables; **G5** don't worry too much about \"programming to the")
A("interface\" with local variables; **G6** take care when using `var` with diamond or generic")
A("methods; **G7** take care when using `var` with literals.")
A("")
A("---")
A("")
A("## Corrections carried through from the previous guide")
A("")
A("The prompt names three claims in `src/topics/04-modern-java.md` that must be corrected rather")
A("than carried forward. Each is fixed at every point it appears:")
A("")
A("1. **Pinning is dated.** `synchronized` pins a virtual thread on Java 21; JEP 491 makes object")
A("   monitors continuation-aware in Java 24 and removes that cause. Native and foreign frames")
A("   still pin, so the `jdk.VirtualThreadPinned` JFR event survives and the diagnostic does not")
A("   disappear. \"Use `ReentrantLock`\" is therefore a version-scoped answer, not a permanent rule.")
A("2. **The common pool's width is stated in both halves.** `ForkJoinPool.commonPool()`'s default")
A("   parallelism is `availableProcessors() - 1`, *and* the thread that submits the terminal")
A("   operation participates in the computation, so the effective width equals the core count.")
A("3. **Structured concurrency is named at both shapes.** Java 21 (JEP 453, preview): `fork`")
A("   returns `Subtask<T>`, with `ShutdownOnFailure` and `ShutdownOnSuccess` as the policies,")
A("   inside a try-with-resources block on the owning thread. Java 25 (JEP 505): public")
A("   constructors are replaced by static `open()` factories and the two shutdown policies by a")
A("   composable `Joiner`.")
A("")
A("---")
A("")
A("## Reading order")
A("")
A("### First careful pass, cover to cover")
A("")
A("Read in file-plan order, 1 to %d. It is built so that nothing depends on a later file: the" % len(P))
A("release model comes before any version claim, the surface of a feature before its cost model,")
A("and its cost model before its internals.")
A("")
A("If you want the shorter first pass, read every `01-basics*` and `02-*` file and skip the")
A("`03-internals*` files and Part 4 on the first pass. That is the whole of Parts 1 and 2 —")
A("the surface plus the judgement — and it stands on its own.")
A("")
A("### Night-before re-read")
A("")
A("In this order, and nothing else:")
A("")
A("1. `95-traps-drills-and-checklist.md` — the trap index (D-179), the version-stale table")
A("   (D-180) and the numbers card (D-181). These three tables are the highest density in the set.")
A("2. `cost-model/02-master-tables.md` — the seven master comparison tables.")
A("3. `which-construct/02-which-construct.md` — ten decisions, one line each.")
A("4. The four `9x` part wrap-ups, for the summary tables and the puzzles only.")
A("5. `94-interview-questions-a/b/c.md` — skim the 95 question headings; read the answer only")
A("   where the heading does not already trigger it.")
A("6. The `## Cheat sheet` section of any subject you are shaky on, and nothing else from that")
A("   file.")
A("")
A("---")
A("")
A("## Open questions")
A("")
A("Populated as writer envelopes return `unverified` lines. Empty is the expected outcome.")
A("")
A("- none recorded yet")
A("")
A("---")
A("")
A("## Deferred")
A("")
A("No leaves deferred. Every one of the 984 is owned by exactly one row above.")

open(OUT, 'w').write('\n'.join(w) + '\n')
print("wrote", OUT, len(w), "lines")
print("files:", len(P), "diagram svgs:", sum(1 for d in diag.values() if d['type'] != 'table'))
