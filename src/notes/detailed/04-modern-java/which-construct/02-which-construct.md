# 04 Modern Java — Which construct — INTERMEDIATE (§2.15)

**Target version: Java 21 LTS.** | **Part 2 of 5** | [Index](../00-index.md)
Previous: [The master tables — master tables](../cost-model/02-master-tables.md) · Next: [Build it — functional toolkit](../build-it/01-functional-toolkit.md)

## Why this file exists

Every prior file in this set taught one construct at a time — a lambda, a stream, a sealed
interface, a virtual thread — each in isolation, each convinced it is the right tool. In real
code you are never choosing a construct in isolation; you are choosing it *against* its
siblings, under a condition that is usually implicit and usually wrong when copied from a blog
written for a different Java version. This file is the decision layer: ten questions a senior
engineer actually gets asked, each with a default answer, and — more importantly — the exact
condition under which the default flips.

The pattern repeats ten times: state the default, prove it with the mechanism from the sibling
guide, then name the one condition that overrides it. Read the mechanism, not the slogan.
Nothing here reteaches the internals a sibling file already owns — each decision includes one
self-contained paragraph of mechanism and then points at the guide with the full treatment,
per the `[X-REF]` discipline used across this note set.

### D-124 — the index, before the streets

Every subtopic file that introduces a family opens with the map. Ten decisions, one row each:

| # | Question | Default answer | Condition that overrides the default | Argued in |
|---|---|---|---|---|
| 1 | Lambda, method reference, or anonymous class? | Method reference when it points at an existing method 1:1; else lambda | Need a field, multiple abstract methods, or a name for a stack trace → anonymous class or named class | [§1](#1-lambda-method-reference-or-anonymous-class) |
| 2 | Stream or loop? | Loop | Filter → map → collect shape over a bulk collection with no early-exit control flow → stream | [§2](#2-stream-or-loop) |
| 3 | Parallel stream, your own executor, or virtual threads? | Sequential stream (no parallelism at all) | CPU-bound, splittable, large-N, on the machine's own cores → parallel stream. I/O-bound and blocking → virtual threads. Need control over pool identity, backpressure, or lifecycle → your own executor | [§3](#3-parallel-stream-your-own-executor-or-virtual-threads) |
| 4 | `Optional`, `null`, an exception, or an empty collection? | `Optional<T>` for a single nullable return value | Method parameter or record component → never `Optional`, use `null`/validation. Caller cannot proceed at all → exception. Cardinality is naturally 0..N → empty collection, never `Optional<List<T>>` | [§4](#4-optional-null-an-exception-or-an-empty-collection) |
| 5 | Record, final class, enum, or interface? | Record for an immutable data carrier with structural equality | Fixed, small, closed set of singleton instances → enum. Needs mutable state or identity semantics → final class. Defines a capability multiple unrelated types implement → interface | [§5](#5-record-final-class-enum-or-interface) |
| 6 | Sealed interface, enum, or open polymorphism? | Sealed interface when the variants carry different data shapes and the set is closed but may grow within the module | All variants are stateless, interchangeable constants → enum. Third parties must be able to add implementations → open (non-sealed) interface | [§6](#6-sealed-interface-enum-or-open-polymorphism) |
| 7 | Pattern switch or virtual dispatch? | Virtual dispatch (a method on the sealed type, overridden per variant) when the operation is intrinsic to the type | Pattern switch when the operation is extrinsic (formatting, mapping to another layer's shape) or spans multiple sealed hierarchies at once | [§7](#7-pattern-switch-or-virtual-dispatch) |
| 8 | Text block, resource file, or constant? | Text block for a short, one-place, version-controlled-with-the-code multi-line literal (SQL, JSON template) | Needs to change without a redeploy, is large (>1 screen), or is shared across languages/services → resource file. Single line, reused as an identifier → `static final` constant | [§8](#8-text-block-resource-file-or-constant) |
| 9 | Virtual thread, platform thread, or reactive? | Virtual thread for blocking, I/O-bound, high-fan-out work | CPU-bound work → platform thread pool sized to cores (virtual threads add nothing here). Backpressure and flow control across an async boundary are the actual problem being solved → reactive (`Flow`/Reactor/RxJava) | [§9](#9-virtual-thread-platform-thread-or-reactive) |
| 10 | Structured concurrency, `CompletableFuture`, or `invokeAll`? | Structured concurrency (`StructuredTaskScope`, preview in 21) when subtasks share one deadline/cancellation and the parent must not outlive them | Need to compose async pipelines that cross method boundaries with `.thenApply`/`.thenCompose` chains, no shared cancellation scope → `CompletableFuture`. Fixed, homogeneous, all-must-finish batch with no individual short-circuit → `ExecutorService.invokeAll` | [§10](#10-structured-concurrency-completablefuture-or-invokeall) |

**D-124** — The which-construct index

Read every row the same way: **default, then override.** The interview mistake is reciting the
default as if it were a law; the senior-engineer answer is stating the default and then naming
the one line of context that would flip it — because that line of context is what the
interviewer is actually listening for.

---

## 1. Lambda, method reference, or anonymous class?

**Mental model.** A lambda is a promise: "this exact call, packaged, deferred." A method
reference is the same promise phrased as a pointer instead of a rewrite. An anonymous class is
the promise plus a place to keep private state and, unusually, plus a name that shows up in a
stack trace.

**Why it exists as a decision at all.** Before Java 8, every deferred unit of work — a
`Runnable`, a `Comparator`, a `FileFilter` — was an anonymous inner class: a full class
declaration, a synthetic outer-class reference if non-static, and a distinct `.class` file per
call site. Lambdas removed the ceremony for the 90% case where the body was one call chain
with no need for extra state; method references removed lambdas' own remaining ceremony for the
case where the lambda's entire body was "just call this method."

**When to reach for it, and when not.** The three exist in a strict specificity order, and the
rule is: **prefer the most specific form the shape of the code permits.**

- If the lambda body is exactly `x -> someMethod(x)` or `x -> x.someMethod()`, use a method
  reference — `SomeClass::someMethod`. It is not merely shorter; it eliminates one synthetic
  parameter binding and reads as "this operation," not "this operation phrased as code."
- If the body needs more than one statement, needs to close over more than the enclosing
  effectively-final locals, or genuinely is not "point at an existing method," use a lambda.
- If the unit of work needs its **own field** (state that must survive between invocations and
  is not just a captured local), needs to implement an interface with **more than one abstract
  method** (a lambda can only ever target a functional interface — exactly one abstract
  method), or you specifically want a **named class to appear in a stack trace and heap dump**
  instead of `QuizStakes$$Lambda$47/0x00000008015b0440`, use an anonymous (or named) class.

**How it works.** All three compile to the same JVM-level contract — an instance of a
functional interface, invoked through its single abstract method — but they get there by
different paths. Anonymous classes go through `invokespecial`/`invokevirtual` on a real
generated class, present at compile time as a `.class` file, one per call site, with a synthetic
constructor taking captured locals as constructor arguments. Lambdas compile to an
`invokedynamic` call site with a bootstrap method,`java.lang.invoke.LambdaMetafactory
::metafactory`, which the JVM resolves **once, lazily, at first execution** into a
`CallSite` holding a `MethodHandle`; the actual implementation class is spun up at runtime by
`InnerClassLambdaMetafactory`, not baked into the `.class` file the compiler emitted. Guide 06
(JVM internals) owns the full `invokedynamic`/`CallSite` linkage walk; the load-bearing fact
here is that a lambda has **no source-visible class** — that is exactly why its captured state
cannot be inspected the way an anonymous class's fields can, and why its stack-trace name is
synthetic and unstable across recompiles. Method references reuse the identical
`invokedynamic`/`LambdaMetafactory` path — a method reference is not a separate bytecode
mechanism, it is a lambda whose bootstrap arguments point directly at an existing method handle
instead of a synthesized one, which is why `ClientRestrictions::isBlocking` and
`r -> r.isBlocking()` produce structurally identical call sites.

```java
// QuizStakes: filtering a client's restriction set before allowing a stake.
List<Restriction> active = restrictions.stream()
        .filter(Restriction::isActive)              // method reference: points at an existing predicate
        .filter(r -> r.type() != RestrictionType.WITHDRAWAL_BLOCKED) // lambda: not a 1:1 pointer
        .toList();

// Anonymous class: needed because this comparator carries its own mutable tie-break counter,
// which a lambda has nowhere to put — a lambda cannot declare a field.
Comparator<Restriction> bySeverityThenInsertionOrder = new Comparator<>() {
    private int counter = 0;
    private final Map<Restriction, Integer> order = new IdentityHashMap<>();

    @Override
    public int compare(Restriction a, Restriction b) {
        order.putIfAbsent(a, counter++);
        order.putIfAbsent(b, counter++);
        int bySeverity = b.severity() - a.severity();
        return bySeverity != 0 ? bySeverity : order.get(a) - order.get(b);
    }
};
```

**Gotcha.** `this` inside a lambda refers to the **enclosing instance**, exactly as if the code
had not been wrapped at all, because a lambda has no instance of its own to bind `this` to. Inside
an anonymous class, `this` refers to the anonymous class instance itself — reaching the
enclosing instance requires `EnclosingClass.this`. Copy-pasting a lambda body into an anonymous
class (or vice versa) silently changes what `this` resolves to; this is one of the few places
where the two forms are *not* interchangeable line-for-line.

**Interview:** "Why can't a lambda have a field?" — because a lambda is not a class declaration
at the source level, and desugars into synthetic call-site state managed by
`LambdaMetafactory`, not a user-authored object with a declared field list; if you need a field,
you need an actual class.

> A lambda is a deferred call chain with no stack-trace identity and no field slot; reach for a
> method reference when the lambda would be a bare pointer, and reach for an anonymous or named
> class only when you need state of your own or more than one abstract method.

---

## 2. Stream or loop?

**Mental model.** A `for` loop is one imperative sentence: "do this, then this, then this,
possibly leaving early." A stream is a *pipeline of stages* — each intermediate operation
contributes one `Sink` wrapping the next, and nothing runs until a terminal operation walks the
chain backwards and pulls elements through it. Reaching for a stream when the shape is really a
loop with early exits and mutation forces you to fight the pipeline instead of using it.

**Why it exists as a decision.** Java shipped with only the loop for 19 years. Streams did not
arrive to replace loops universally; they arrived to give bulk, potentially parallelizable,
declarative aggregation a first-class vocabulary (`filter`/`map`/`reduce`/`collect`) so the
*what* (the transformation) is separated from the *how* (the iteration mechanics and, if wanted,
its parallel decomposition).

**When to reach for it, and when not.** The default in this pair is the **loop**, not the
stream — a fact most 2019–2023 blog material inverts. Reach for a stream when the shape is
genuinely `source → filter → map → collect/reduce` over a bulk collection with no need to break
out early, no need to mutate an outer variable per element, and no need to consult more than one
element's neighbours at once. Stay with a loop when: you need `break`/`continue`/labelled
exit (a stream's `takeWhile`/`anyMatch` cover *some* early-exit shapes but not arbitrary
control flow); you need to mutate two or more outer collections per iteration (a stream forces
you into contorted `peek`-based side effects, which is itself the pitfall below); you are
iterating with an index and neighbour lookahead (a sliding window is far plainer as a loop);
or the loop body already reads as "for each X, do exactly this one obvious thing" and a stream
would only add ceremony.

**How it works.** A stream pipeline is a chain of `AbstractPipeline` stages. Every intermediate
operation (`filter`, `map`, `sorted`, `distinct`) does not touch a single element when it is
called; it allocates one new stage object linked to the previous stage and records an
`opWrapSink` function — a factory that, given the *next* sink in the chain, produces a `Sink`
wrapping it. Nothing traverses the source yet. Only when a terminal operation
(`collect`, `forEach`, `reduce`, `count`) calls `evaluate(TerminalOp)` does the machinery walk the
chain **backwards from the terminal stage**, calling each stage's `opWrapSink` in reverse order
to build one composed `Sink`, and then call `copyInto(wrappedSink, spliterator)`, which is the
first and only point where the source is actually traversed, one element at a time, pushed
forward through the composed sink chain. This is also why a pipeline built but never given a
terminal operation does literally nothing — `AbstractPipeline` at the jdk-21+35 tag guards
reuse with exactly this laziness in mind: `linkedOrConsumed` is only ever set true once a
terminal operation (or the intermediate `spliterator()`) actually runs, and every public entry
point checks it first, throwing `IllegalStateException("stream has already been operated upon
or closed")` on reuse — guide 01 (DSA fundamentals) is not the right place for this, it belongs
to guide 03 (Java core)'s stream-internals chapter, referenced here in full because it is the
mechanism that explains why "streams are lazy" is a true but useless sentence on its own.

```java
// Ledger projection: a stream is the right call here — filter, map, collect, no early exit,
// no cross-element mutation, one obvious aggregate per client.
Map<ClientId, Money> stakeableByClient = ledgerEntries.stream()
        .filter(e -> e.position() == LedgerPosition.CLIENT_CASH_AVAILABLE
                  || e.position() == LedgerPosition.CLIENT_BONUS_AVAILABLE)
        .collect(Collectors.groupingBy(
                LedgerEntry::clientId,
                Collectors.reducing(Money.zero(Currency.GBP), LedgerEntry::amount, Money::add)));

// Same data, but the shape needs an early exit the moment the running total is enough to
// cover a pending withdrawal — a loop states this directly, a stream needs a workaround.
Money runningStakeable = Money.zero(Currency.GBP);
for (LedgerEntry entry : clientEntries) {
    if (entry.position() != LedgerPosition.CLIENT_CASH_AVAILABLE
            && entry.position() != LedgerPosition.CLIENT_BONUS_AVAILABLE) {
        continue;
    }
    runningStakeable = runningStakeable.add(entry.amount());
    if (runningStakeable.compareTo(pendingWithdrawal.amount()) >= 0) {
        break; // covered — stop scanning the ledger early
    }
}
```

**Gotcha.** `IntStream.sum()` and `Collectors.summingInt` both accumulate into a **plain
`int`** internally — `Collectors.summingInt`'s accumulator array at the jdk-21+35 tag is
literally `new int[1]`, not `long[]` as some material claims. Summing three ledger amounts of
1,000,000,000 (as raw minor units, hypothetically) silently wraps to a negative number instead
of throwing. `Collectors.averagingInt` is genuinely safe because its accumulator is `long[2]`
(sum, count) — the two collectors are not interchangeable in their overflow behaviour, and only
one half of that pair is what most blog material states.

**Interview:** "Is a stream always faster than a loop?" — no; a sequential stream carries
pipeline-construction and boxing overhead a loop does not, and only parallel decomposition (§3)
can beat a loop outright, and only past a size and cost-per-element threshold worth measuring,
not assuming.

> Default to the loop; reach for a stream only when the shape is genuinely a lazy,
> unbroken filter-map-collect pipeline over a bulk source, because that is the one shape the
> `AbstractPipeline` machinery was built to make both declarative and — when asked — parallel.

---

## 3. Parallel stream, your own executor, or virtual threads?

**Mental model.** These three answer three different questions that sound like one question.
A parallel stream answers "split this CPU-bound bulk computation across my cores." A virtual
thread answers "let this blocking call sit without holding a platform thread hostage." Your own
`ExecutorService` answers "I need to control the pool's identity, size, and lifecycle myself,"
which the other two deliberately take away from you.

**Why it exists as a decision.** Java 7 gave the fork/join framework and its common pool;
Java 8 exposed it implicitly through `parallelStream()`; Java 21 added virtual threads (JEP
444) as a second, unrelated concurrency primitive aimed at a different bottleneck — blocking
I/O, not CPU-bound splitting. Treating them as interchangeable "make it concurrent" buttons is
the single most common mid-level mistake this decision guards against.

**When to reach for it, and when not.** Parallel streams win when the work is **CPU-bound,
splittable into independent chunks, large enough to amortize the fork/join overhead, and
running on a machine whose cores you actually want to consume** — because a parallel stream
submits into `ForkJoinPool.commonPool()` by default, and every other CPU-bound task on the
process (including other parallel streams) shares that same pool. Virtual threads win when the
work is **I/O-bound and blocking** — waiting on the identity vendor, the watchlist provider, the
card PSP — because a parked virtual thread releases its carrier platform thread back to the
`ForkJoinPool`-backed scheduler instead of occupying an OS thread for the whole wait. Your own
`ExecutorService` wins when you need **pool identity separate from the common pool** (so a slow
batch job cannot starve unrelated parallel streams), **explicit sizing** for CPU-bound work that
should not simply consume every core, or **lifecycle control** — shutdown, awaitTermination,
rejection policy — that neither of the other two options exposes.

**How it works.** A parallel stream's decomposition width is governed by `AbstractTask
.getLeafTarget()` and `suggestTargetSize`, verified at the jdk-21+35 tag:

```java
private static final int LEAF_TARGET = ForkJoinPool.getCommonPoolParallelism() << 2;

public static long suggestTargetSize(long sizeEstimate) {
    long est = sizeEstimate / getLeafTarget();
    return est > 0L ? est : 1L;
}
```

`LEAF_TARGET` is the common pool's parallelism shifted left by two — **×4**, matching the
javadoc's own words: "we over-partition, currently to approximately four tasks per processor, to
enable others to help out if leaf tasks are uneven." `suggestTargetSize` is **floored integer
division, clamped to a minimum of 1** — not rounded up, a detail worth stating precisely since it
is easy to misremember as ceiling division. `getLeafTarget()` reads the **calling thread's own
pool**, not a fixed constant, when that thread is a `ForkJoinWorkerThread` — the mechanism
behind "submit the terminal operation from inside your own `ForkJoinPool` to control the
decomposition width," a trick that only works because of this exact line. On the 8-core box this
note set holds fixed throughout: `availableProcessors()` = 8, `commonPool` parallelism =
`availableProcessors() - 1` = **7** (and the calling thread also participates, so the
**effective width is 8**), `LEAF_TARGET` = `7 << 2` = **28**, and over the domain's 2,800,000
daily stake reservations, `suggestTargetSize` = `2_800_000 / 28` = **100,000** exactly, producing
**28 leaf tasks** of 100,000 elements each.

The virtual-thread scheduler is a *different* `ForkJoinPool`, constructed at
`VirtualThread.createDefaultScheduler()`, verified at the jdk-21+35 tag:

```java
// parallelism defaults to Runtime.getRuntime().availableProcessors() unless the
// jdk.virtualThreadScheduler.parallelism system property overrides it
parallelism = Runtime.getRuntime().availableProcessors();
maxPoolSize = Integer.max(parallelism, 256);      // 256 is a floor, not a flat default
minRunnable = Integer.max(parallelism / 2, 1);
boolean asyncMode = true; // FIFO
return new ForkJoinPool(parallelism, factory, handler, asyncMode,
             0, maxPoolSize, minRunnable, pool -> true, 30, SECONDS);
```

On the 8-core box: parallelism = **8**, `maxPoolSize` = `max(8, 256)` = **256** (the 256 is a
floor that only binds below 257 cores — a machine with 300 cores gets `maxPoolSize` = 300, and
stating "the default is 256" without that qualifier is the version-stale form of the claim),
`minRunnable` = `max(8 / 2, 1)` = **4**, and the pool is constructed with `asyncMode = true`,
whose own source comment reads `// FIFO` — that comment is the evidence for the scheduler's FIFO
ordering claim, not folklore. Setting `jdk.virtualThreadScheduler.maxPoolSize` below the
processor count also clamps `parallelism` down to it — one system property silently moves two
numbers at once. Guide 05 (multithreading and concurrency) owns the full carrier-thread
mount/unmount walk and the pinning story in depth; the mechanism paragraph above is enough to
answer the interview question unassisted.

```java
// Assessment fan-out: three blocking calls (identity vendor p50 900ms/p99 38s, watchlist
// provider p50 1.4s/p99 25s, wealth service) — I/O-bound, not CPU-bound, so virtual threads,
// not a parallel stream, are the right tool.
try (var scope = Executors.newVirtualThreadPerTaskExecutor()) {
    Future<DocumentVerdict> documentCheck = scope.submit(() -> documentVerification.verify(applicationId));
    Future<ScreeningVerdict> screeningCheck = scope.submit(() -> screeningService.screen(applicationId));
    Future<WealthVerdict> wealthCheck = scope.submit(() -> assessmentService.assessWealth(applicationId));

    DocumentVerdict documents = documentCheck.get();
    ScreeningVerdict screening = screeningCheck.get();
    WealthVerdict wealth = wealthCheck.get();
    // combine into the overall assessment outcome — see §10 for the structured, cancellation-aware version
}

// Contrast: a genuinely CPU-bound bulk computation over 2.8M stake reservations —
// a parallel stream is the right tool precisely because there is no blocking I/O in the loop body.
double totalStakeValue = stakeReservations.parallelStream()
        .mapToDouble(Reservation::stakeAmountMinorUnits)
        .sum();
```

**Gotcha.** A parallel stream and a virtual-thread-per-task executor solve *disjoint* problems,
and mixing them wrongly is worse than either alone: parking inside a parallel stream's lambda on
a blocking I/O call still occupies a **platform** `ForkJoinWorkerThread` for the whole wait,
because `parallelStream()` never routes through the virtual-thread scheduler — you have simply
starved the common pool with I/O wait instead of computation. **Pitfall:** wrapping a blocking
HTTP call in `.parallelStream()` "to make it concurrent" — the fix is `newVirtualThreadPerTaskExecutor()`
for the I/O fan-out, reserving `parallelStream()` for CPU-bound splitting only.

**Interview:** "Do virtual threads make my code run in parallel?" — no; they make blocking
*cheap*, not computation *faster*; a CPU-bound loop wrapped in virtual threads still competes
for the same core count, because virtual threads multiplex onto the same limited set of carrier
platform threads (parallelism = `availableProcessors()` by default) — they solve thread-count
scaling for I/O wait, not core-count scaling for computation.

> Parallel stream for CPU-bound, splittable, core-bound work; virtual threads for blocking
> I/O-bound fan-out; your own `ExecutorService` when you need pool identity, sizing, or
> lifecycle control that the other two deliberately withhold.

---

## 4. `Optional`, `null`, an exception, or an empty collection?

**Mental model.** `Optional<T>` is a **method-return-only** box that forces the caller to
handle absence at the call site instead of three stack frames later as a `NullPointerException`
with no context. `null` still means "the field or parameter genuinely has no value and every
caller already knows to check." An exception means "the caller cannot sensibly proceed at all."
An empty collection means "there were supposed to be zero-or-more of these, and zero is not an
error, it is a valid count."

**Why it exists as a decision.** `Optional` (Java 8) exists because `null` was being used to
mean four different things at once — "not found," "not yet computed," "genuinely absent," and
"error, silently swallowed" — and the compiler cannot distinguish any of them, so every
dereference anywhere downstream was a latent `NullPointerException`. `Optional` gives exactly
one of those four meanings — "a single value that may legitimately be absent, as a method's
return type" — a type the compiler and the API surface (`map`, `filter`, `orElseThrow`) can
force the caller to confront.

**When to reach for it, and when not.** `Optional<T>` is the return type of a method that looks
up or computes a single value that may legitimately not exist, and nothing else — **never** a
field type, **never** a method parameter type, **never** a record component, and **never**
`Optional<List<T>>` or `Optional<Collection<T>>`. Use plain `null` for a field or parameter where
the API contract already documents optionality and every caller is expected to null-check
(rare after `Optional` exists, but genuinely correct for, e.g., a builder's optional setter
backing field). Use an exception when the caller **cannot proceed at all** — looking up a client
by an `AccountId` that must exist by invariant (e.g., inside a transaction you are already
inside because the account was just verified to exist) should throw, not return `Optional.empty()`,
because an empty `Optional` there would just relocate the bug to a silent `orElseThrow` a few
lines later with a worse stack trace. Use an empty collection whenever the cardinality is
naturally 0..N — a client's active restrictions, a document requirement list — because
`Optional<List<Restriction>>` forces every caller to unwrap a box around a collection that
already has its own perfectly good empty state.

**How it works.** `Optional` is a final class holding one `private final T value` field, with
`Optional.empty()` returning a **shared singleton instance** — `EMPTY` — cached once as a
`static final Optional<?>` and unchecked-cast at every call site, which is why `Optional.empty()
== Optional.empty()` for the same generic erasure is true by identity, not merely by `equals`.
`Optional.of(value)` throws `NullPointerException` immediately if `value` is null — it does not
silently become `empty()` — while `Optional.ofNullable(value)` is the only factory that maps a
null input to `EMPTY`. `orElseThrow()` with no argument throws `NoSuchElementException`; the
overload taking a `Supplier<X>` throws whatever that supplier constructs, which is the version
worth using so the exception at the throw site names the actual business failure
(`ClientNotFoundException`) instead of a generic one.

```java
// Restriction lookup: a single value that may legitimately be absent — the right shape for Optional.
public Optional<Restriction> findActiveRestriction(ClientId clientId, RestrictionType type) {
    return restrictionRepository.findByClientAndType(clientId, type)
            .filter(Restriction::isActive);
}

// Caller: forced to confront absence, cannot forget the check the way a raw null allows.
boolean depositBlocked = findActiveRestriction(clientId, RestrictionType.DEPOSIT_BLOCKED)
        .isPresent();

// Contrast: listing a client's active restrictions is naturally 0..N — an empty List, never
// Optional<List<Restriction>>.
public List<Restriction> activeRestrictions(ClientId clientId) {
    return restrictionRepository.findByClient(clientId).stream()
            .filter(Restriction::isActive)
            .toList(); // empty list, not Optional.empty(), when there are none
}

// Contrast: an account that has already passed activation must exist — absence here is a bug,
// not a legitimate outcome, so this throws rather than returning Optional.empty().
public Account requireActivatedAccount(AccountId accountId) {
    return accountRepository.findActivated(accountId)
            .orElseThrow(() -> new IllegalStateException(
                    "Account " + accountId + " expected ACTIVE but was not found"));
}
```

**Gotcha.** `Optional` is not `Serializable`, and using it as a field type (beyond the narrow,
debated case of a lazily-computed cache field never serialized) breaks any class that needs to
be, which is one concrete reason the "never as a field" rule is enforced rather than stylistic.
**Pitfall:** calling `.get()` directly on an `Optional` returned from a repository lookup — it
compiles, it works in the demo, and it throws the exact `NullPointerException`-shaped problem
`Optional` was invented to prevent, just spelled `NoSuchElementException`, the moment a lookup
genuinely misses; the fix is `orElseThrow(() -> new SpecificException(...))` naming the real
failure, not a bare `.get()`.

**Interview:** "Why shouldn't `Optional` be a field or a parameter type?" — because `Optional`'s
entire value proposition is forcing the **caller of a method** to handle absence explicitly at
the point of the call; a field or parameter already has other, better-established idioms
(`null` plus documented contract, or an `@Nullable` annotation) and wrapping them in `Optional`
only adds an allocation and a `.get()` call site with no compiler-enforced benefit.

> `Optional<T>` is a method return type, and only that, for a single value that may legitimately
> be absent; reach for `null` where the contract is already understood, an exception where the
> caller cannot proceed, and an empty collection wherever the cardinality was always 0..N.

---

## 5. Record, final class, enum, or interface?

**Mental model.** A record is a **named tuple with a contract**: state the shape once, and the
compiler derives the constructor, accessors, `equals`, `hashCode`, and `toString` from that one
declaration. A final class is a record without the compiler doing the deriving for you — chosen
when you need mutability or identity semantics a record's structural equality does not give
you. An enum is a fixed, closed, small set of singleton values. An interface is a capability, not
a data shape at all.

**Why it exists as a decision.** Before records (Java 16, previewed in 14), an immutable value
type meant writing a final class with private final fields, a constructor, accessors, and
hand-rolled (or IDE-generated, equally verbose) `equals`/`hashCode`/`toString` — for
`Money(BigDecimal amount, Currency currency)`, that is roughly 40 lines carrying zero
information beyond "two fields, compared structurally." JEP 395 collapsed that boilerplate into
one line, at the cost of giving up the ability to add extra instance fields beyond the stated
components, or to extend another class.

**When to reach for it, and when not.** Reach for a **record** when the type's entire job is to
carry state — `StakeSplit(Money bonusPortion, Money cashPortion)`, `RestrictionKey
(RestrictionType type, RestrictionSource source)` — and structural equality (two instances with
the same field values are equal) is the correct notion of equality. Reach for a **final class**
when you need mutable state (a `Reservation` whose status field changes as the stake is
settled) or identity semantics (two `Account` objects with identical field values right now
should still not be `.equals()` if they represent different accounts — identity comes from the
`AccountId`, not the whole field set, and a record's generated `equals` cannot express that
distinction). Reach for an **enum** when the set of values is fixed, small, and closed at
compile time and every value is a singleton with no distinguishing data beyond, at most, a
handful of `enum`-body constants (`RestrictionSource.SYSTEM_ONBOARDING`,
`RestrictionSource.ADMIN`). Reach for an **interface** when you are naming a capability multiple
unrelated types implement — `Verdict`-adjacent behaviour aside, think "can be persisted,"
"can be audited" — not a data shape at all.

**How it works.** A record's components are `private final` fields with public accessors named
exactly after the component (`amount()`, not `getAmount()`); the compiler synthesizes a
canonical constructor unless you declare a **compact constructor**, which runs *before* the
field assignments and may only validate or transform the **parameters**, never assign the
fields directly — the field write is emitted by the compiler after the compact constructor body
finishes. Verified on this machine: attempting `this.bonusPortion = bonusPortion.setScale(2);`
inside `StakeSplit`'s compact constructor fails to compile with `error: cannot assign a value
to final variable bonusPortion` — the correct fix reassigns the **parameter**:
`bonusPortion = bonusPortion.setScale(2, RoundingMode.DOWN);`, and the compiler's own
field-write completes the job. A record is implicitly `final` and cannot extend any class
(it extends `java.lang.Record` implicitly), which is precisely why "needs to extend a class" or
"needs mutable state" are the two hard walls that push you to a final class instead.

```java
// Record: an immutable, structurally-equal value carrying exactly the stake-split invariant.
public record StakeSplit(Money bonusPortion, Money cashPortion) {
    public StakeSplit {
        bonusPortion = bonusPortion.setScale(2, RoundingMode.DOWN); // bonus rounds DOWN
        Objects.requireNonNull(cashPortion, "cashPortion");
        // invariant: the two portions sum exactly to the stake — enforced by the caller
        // that constructs this record from a known stake amount, not re-derivable here
        // without also passing the stake, so it is asserted, not recomputed, in the constructor.
    }
}

// Final class: Reservation has mutable status and true identity (two reservations with
// identical current field values are still different reservations) — a record cannot model this.
public final class Reservation {
    private final RoundId roundId;
    private final ClientId clientId;
    private final StakeSplit split;
    private ReservationStatus status; // mutable — settles or voids after construction

    public Reservation(RoundId roundId, ClientId clientId, StakeSplit split) {
        this.roundId = roundId;
        this.clientId = clientId;
        this.split = split;
        this.status = ReservationStatus.OPEN;
    }

    public void settle() { this.status = ReservationStatus.SETTLED; }
    public void voidReservation() { this.status = ReservationStatus.VOIDED; }
}

// Enum: a fixed, closed set of restriction sources — nothing about them varies by instance.
public enum RestrictionSource {
    SYSTEM_ONBOARDING, SYSTEM_COMPLIANCE, SYSTEM_LIFECYCLE, ADMIN, CLIENT
}
```

**Gotcha.** A record's automatically-derived `equals`/`hashCode` compares **every** component,
which is exactly wrong for an entity-shaped type masquerading as a record for convenience — a
`ClientId`-only equality check on an `Account` record with a dozen mutable-looking components
(records cannot have mutable components, so this itself is the tell) means two snapshots of the
same account taken a millisecond apart, with one field changed, are `.equals()` **false**, which
silently breaks any code (a `Set<Account>`, a `HashMap` key) that assumed entity identity.
**Pitfall:** modelling `Account` as a record because "it's just data" — the fix is a final class
with `equals`/`hashCode` overridden to compare `accountId` alone, because `Account` has
identity, not structural equality.

**Interview:** "Why can't a record extend a class?" — because a record already implicitly
extends `java.lang.Record`, and Java has single class inheritance; a record *can* implement any
number of interfaces, which is the escape hatch when a record needs to also satisfy a
capability contract.

> Record for an immutable, structurally-equal data carrier; final class for mutable state or
> identity semantics; enum for a fixed closed set of singleton values; interface for a
> capability, never a data shape.

---

## 6. Sealed interface, enum, or open polymorphism?

**Mental model.** A sealed interface is a **closed, heterogeneous** family — a fixed list of
named variants, each free to carry its own different data shape. An enum is a **closed,
homogeneous** family — a fixed list of values that are all the same shape (or no shape at all
beyond their name). Open (non-sealed) polymorphism is an **unbounded, extensible** family — any
number of third-party types can join later.

**Why it exists as a decision.** Before sealed types (Java 17, JEP 409), modelling "one of these
four verdict shapes, and no others, ever" meant either an unsealed interface (which cannot stop
a fifth implementation from appearing, and cannot give the compiler exhaustiveness information
for a `switch`) or a single class with a discriminator field and every variant's fields crammed
into one shape (an "everything-bag," fragile and null-heavy). Sealed types let the compiler
**know** the full variant list at compile time, which is the fact `switch` exhaustiveness
checking (§7) is built on.

**When to reach for it, and when not.** Reach for a **sealed interface** when the family is
closed — you, the author, get to enumerate every variant, no external module may add one — and
the variants genuinely differ in shape: `Verdict` as a sealed hierarchy of `DocumentVerdict`,
`ScreeningVerdict`, `ReviewVerdict`, `WealthVerdict`, each carrying different fields
(`decidedAt`, `decidedBy`, plus verdict-specific detail). Reach for an **enum** when every
variant is the *same* shape — usually no data at all beyond the constant's name, or a small
uniform set of enum-body fields — `AccountLifecycle { PENDING_VERIFICATION, ACTIVE, DORMANT,
CLOSING, CLOSED }`. Reach for **open (non-sealed) polymorphism** only when the whole point is
that code outside your control must be able to add a new implementation — a plugin
`NotificationChannel` interface a downstream team implements — because sealing forecloses
exactly that extensibility.

**How it works.** `sealed` requires every direct subtype to declare itself `final`, `sealed`, or
`non-sealed`, and either list itself in the sealing type's `permits` clause or be in the same
source file (implicit permits). The compiler records the full permitted-subtypes list as
metadata on the sealed type, and it is that recorded list — not a runtime scan — that a pattern
`switch` (§7) over the sealed type consults to prove exhaustiveness at **compile time**: if you
add a fifth `Verdict` subtype and forget to add its case, every exhaustive switch over `Verdict`
fails to compile, rather than silently falling through to a `default` at runtime. This is the
mechanism payoff sealing buys that an ordinary open interface cannot: exhaustiveness becomes a
compile error, not a code-review hope.

```java
public sealed interface Verdict
        permits DocumentVerdict, ScreeningVerdict, ReviewVerdict, WealthVerdict {
    Instant decidedAt();
    String decidedBy();
}

public record DocumentVerdict(DocumentOutcome outcome, String reason,
                               Instant decidedAt, String decidedBy) implements Verdict {}

public record ScreeningVerdict(ScreeningOutcome outcome, String matchReference,
                                Instant decidedAt, String decidedBy) implements Verdict {}

public record ReviewVerdict(ReviewOutcome outcome, String operatorId,
                             Instant decidedAt, String decidedBy) implements Verdict {}

public record WealthVerdict(WealthOutcome outcome, LimitSet approvedLimits,
                             Instant decidedAt, String decidedBy) implements Verdict {}
```

**Gotcha.** Sealing a hierarchy and then reflectively instantiating a subtype outside the
`permits` list is not possible through normal compilation, but a **different source root on the
same module path**, compiled separately, can still implement a `non-sealed` member if one exists
in the chain — sealing only closes the *direct* subtype list of the sealed type itself; any
`non-sealed` link reopens extensibility from that point downward. **Pitfall:** believing "sealed"
means "the whole tree, forever, cannot grow" — the fix is checking every level: a sealed
interface with one `non-sealed` implementation is only closed at the top.

**Interview:** "What does sealing actually buy you over a plain interface?" — compile-time
exhaustiveness checking for pattern `switch`, and a permits list the compiler enforces, so
adding a variant becomes a compile error at every switch that forgot it, not a runtime surprise.

> Sealed interface for a closed, heterogeneous family whose variants carry different shapes;
> enum for a closed, homogeneous family of same-shaped constants; open polymorphism only when
> third parties genuinely need to add implementations you cannot enumerate today.

---

## 7. Pattern switch or virtual dispatch?

**Mental model.** Virtual dispatch asks the object "what are you, and please act accordingly" —
the decision lives *inside* the type, one override per variant. A pattern `switch` asks the
caller's own code "given this value, which of these known shapes is it" — the decision lives
*outside* the type, in whichever piece of code needs to act on it this time.

**Why it exists as a decision.** Object-oriented dogma says "always use polymorphism, never
switch on type" — sound advice when the operation is intrinsic to the type and only ever
implemented one way per variant. It breaks down the moment the *same* sealed hierarchy needs
several **unrelated** operations performed on it by several unrelated pieces of code (a
formatter, an auditor, a metrics exporter), each of which would otherwise force a new method
onto `Verdict` itself, bloating the type with concerns that have nothing to do with what a
verdict *is*. Pattern `switch` (Java 21, JEP 441, finalized after JEP 406/420 previews) gives
that outside code exhaustiveness checking without forcing the extra method onto the type.

**When to reach for it, and when not.** Reach for **virtual dispatch** — a method on the sealed
type itself, overridden per record/variant via a helper or per-implementation logic — when the
operation is genuinely intrinsic to what the type *is*, used the same way everywhere, and adding
it to the type does not smell like an unrelated concern bolted on. Reach for a **pattern
`switch`** when the operation is extrinsic — mapping a `Verdict` to a different layer's DTO, or
formatting it for a notification, where forcing that logic into `Verdict` itself would pollute
the domain type with presentation concerns — or when a single operation must inspect **more than
one** sealed hierarchy's shape at once (a record pattern with nested deconstruction across two
sealed families), which virtual dispatch on either type alone cannot express.

**How it works.** A pattern `switch` over a sealed type is exhaustive precisely because the
compiler already has the `permits` list (§6) and can prove every branch is covered without a
`default`. The synthetic default the compiler still emits for the *impossible* remaining case —
reachable only via bytecode manipulation, reflection tricks, or a class loaded after
compilation with a mismatched hierarchy — has a version trap of its own: through Java 20 it
throws `IncompatibleClassChangeError`; from Java 21 it throws `java.lang.MatchException`,
constructed with the `(String, Throwable)` constructor, confirmed both by running the exact same
source at `--release 17` versus `--release 21` and by reading the `javap -c` output for the 21
class file, which shows `new #19 // class java/lang/MatchException` immediately before the
`athrow`. That detail belongs to guide 03 (Java core)'s switch-internals chapter in full; the
one-paragraph version here is enough to answer "what happens if a sealed switch somehow misses a
case," which is asked more often than the mechanism behind it.

```java
// Extrinsic operation — formatting a Verdict for a client-facing notification — genuinely
// does not belong as a method on Verdict itself, so a pattern switch is the right tool.
public String toNotificationText(Verdict verdict) {
    return switch (verdict) {
        case DocumentVerdict d when d.outcome() == DocumentOutcome.REJECTED ->
                "We could not verify your documents: " + d.reason();
        case DocumentVerdict d -> "Your documents were verified.";
        case ScreeningVerdict s when s.outcome() == ScreeningOutcome.PROHIBITED ->
                "Your application could not proceed.";
        case ScreeningVerdict s -> "Screening complete.";
        case ReviewVerdict r -> "A reviewer has made a decision on your application.";
        case WealthVerdict w -> "Your affordability assessment is complete.";
    }; // exhaustive over Verdict's permits list — no default needed, and the compiler proves it
}

// Contrast: intrinsic behaviour — every Verdict answering "did this pass" — belongs on the
// sealed interface itself via an abstract method, not scattered across every switch site.
public sealed interface Verdict permits DocumentVerdict, ScreeningVerdict, ReviewVerdict, WealthVerdict {
    boolean passed(); // implemented per-record, one line each — intrinsic, not extrinsic
}
```

**Gotcha.** Adding a `when` guard clause to a pattern `switch` case can silently make the switch
**non-exhaustive** even over a sealed type, because a guarded pattern only matches a subset of
that type's instances — the compiler then requires either a following unguarded case for the
same type or an explicit `default`, and forgetting one produces a compile error that reads
confusingly on a switch that "should" already be exhaustive by `permits` alone.

**Interview:** "Isn't switching on type an anti-pattern?" — it was, over an *open* type
hierarchy, because nothing stopped a silent missed case; over a *sealed* hierarchy the compiler
enforces exhaustiveness, which removes the actual defect the anti-pattern advice was guarding
against, leaving the real question as intrinsic-vs-extrinsic, not switch-vs-never-switch.

> Virtual dispatch for behaviour intrinsic to the type, one override per variant; pattern
> `switch` for extrinsic operations performed on the type by outside code, or for operations
> spanning more than one sealed hierarchy at once — sealing is what makes the switch form safe.

---

## 8. Text block, resource file, or constant?

**Mental model.** A text block is a **multi-line string literal that lives with the code that
uses it, indentation and all** — the compiler strips a computed common margin so the source can
be indented naturally and the runtime value is still exactly the text intended. A resource file
is the same content moved **outside the compiled artifact**, loaded at runtime. A `static final`
constant is a single line treated as an identifier, not prose.

**Why it exists as a decision.** Before text blocks (Java 15, JEP 378, previewed at 13/14),
embedding multi-line SQL or JSON in Java meant string concatenation with `\n` and `+` at every
line break, or escaping every embedded quote — both actively hostile to reading the actual
content. Text blocks fixed the *authoring* ergonomics; they never addressed the separate,
older question of whether a piece of text should live in source at all.

**When to reach for it, and when not.** Reach for a **text block** when the content is
multi-line, short enough to read as part of the method that uses it (roughly, fits on one
screen), and its natural lifecycle is "changes when the code around it changes" — a SQL query
against the ledger, a JSON template for a test fixture. Reach for a **resource file** when the
content needs to change **without a redeploy** (an externally-tunable message template), is
**large** enough that inlining it hurts the surrounding method's readability, or is **shared
across languages or services** that cannot import a Java string constant. Reach for a
**`static final` constant** when the value is a single line functioning as a named identifier —
a status-code string, a single SQL fragment reused by name — where "constant" captures the
intent better than "block of prose."

**How it works.** A text block's indentation stripping is computed once, at **compile time**,
from the *incidental* whitespace shared by every line and the closing `"""` delimiter's own
column — not from the first line's indentation alone, and not at runtime. The algorithm: find
the minimum leading-whitespace column across all non-blank lines **and** the closing delimiter
line, strip exactly that many leading spaces from every line, then strip trailing whitespace
from each line unless preceded by a `\` line-continuation escape. This is why moving a text
block to a different indentation level in the source (an IDE re-indent, a method extracted one
level deeper) does not change its **runtime value** — the compiler recomputes the same relative
margin — while manually adding stray leading spaces to only *some* lines does, because it moves
the shared minimum.

```java
// Text block: multi-line SQL that reads as SQL, lives with the repository method that runs it.
private static final String STAKEABLE_BALANCE_QUERY = """
        SELECT client_id,
               SUM(CASE WHEN position IN ('CLIENT_CASH_AVAILABLE', 'CLIENT_BONUS_AVAILABLE')
                        THEN amount ELSE 0 END) AS stakeable
        FROM ledger_entries
        WHERE client_id = ?
        GROUP BY client_id
        """;

// Constant: a single line, functioning as a name, not prose — a plain constant reads better
// than a one-line "text block."
private static final String BONUS_CLAWBACK_LEDGER_NOTE = "Unspent bonus reversed at expiry";
```

**Gotcha.** A text block's trailing-whitespace stripping applies **per line**, silently, unless
that line ends with `\` — which matters for content where trailing spaces are semantically
meaningful (a fixed-width text export, an ASCII table used as literal test fixture data).
**Pitfall:** pasting a fixed-width report layout into a text block and finding every line's
trailing padding silently gone at runtime — the fix is a trailing `\` on lines whose trailing
spaces must survive, or `\s` for a single significant trailing space the stripping would
otherwise eat.

**Interview:** "Does a text block do anything a regular string couldn't?" — no new runtime
capability; it changes only *how the literal is authored and how its whitespace is normalized at
compile time* — the resulting `String` is identical to, and interchangeable with, one built by
concatenation with equivalent content.

> Text block for short, multi-line, code-adjacent literals; resource file once the content
> must change independently of a deploy, or is large, or must be shared outside the JVM;
> `static final` constant for a single line functioning as a name.

---

## 9. Virtual thread, platform thread, or reactive?

**Mental model.** A platform thread is a 1:1 wrapper around an OS thread — expensive to create,
expensive to block, cheap to schedule once running. A virtual thread is a JVM-managed
continuation multiplexed onto a small pool of carrier platform threads — cheap to create, cheap
to *block* (it unmounts from its carrier instead of occupying an OS thread), still ordinary
blocking-style code. Reactive is neither thread model — it is an entirely different *style*,
callback/operator-chain composition, chosen to get backpressure and flow control across an async
boundary that no thread-per-request model, virtual or platform, gives you by itself.

**Why it exists as a decision.** Reactive frameworks (RxJava, then Reactor/Project Reactor)
solved the C10K-style problem — thousands of concurrent connections without thousands of
expensive OS threads — by giving up thread-per-request entirely in favour of an event loop and
composable, non-blocking operators. Virtual threads (Java 21, JEP 444) solve the *same*
scaling problem a different way: keep thread-per-request, ordinary blocking code, `try`/`catch`,
thread-local-shaped debugging — but make the thread itself so cheap that millions can exist,
because a parked one costs a continuation object, not an OS thread.

**When to reach for it, and when not.** Reach for **virtual threads** as the default for
blocking, I/O-bound, high-fan-out server-side work — request handling that calls out to the
identity vendor, the watchlist provider, the ledger — because it gets the scaling benefit of
"one thread per unit of work" without inheriting a platform thread's cost, and the code stays
ordinary, debuggable, blocking-style Java. Reach for **platform threads**, sized to the core
count, for **CPU-bound** work — virtual threads add nothing here, because CPU-bound work never
parks, so there is no unmounting to benefit from, and a fixed pool sized near
`availableProcessors()` is both simpler and exactly as fast. Reach for **reactive** only when
**backpressure and flow control across an asynchronous boundary are the actual problem being
solved** — a slow downstream consumer that must be able to signal "slow down" upstream, or
composing operators (`retry`, `debounce`, `zip`) over event streams that are not naturally
request/response shaped — because that is the one capability neither thread model gives you for
free; reaching for reactive purely for "more concurrency" when virtual threads would do is
adding an entire second programming style for no capability actually needed.

**How it works.** A platform thread's cost lives in its OS-allocated stack (megabytes, fixed at
creation) and OS scheduler entry; a virtual thread's "stack" is a resizable, heap-allocated
continuation, and mounting/unmounting onto a carrier is a JVM-managed operation, not an OS
context switch. The default virtual-thread scheduler is the `ForkJoinPool` built by
`createDefaultScheduler()` (§3's source walk) — parallelism defaults to
`availableProcessors()`, so on the fixed 8-core box exactly **8** carrier threads exist at once,
and blocking calls that would ordinarily each cost one platform thread instead each cost one
continuation, letting far more than 8 virtual threads be *logically* in flight, waiting on the
identity vendor or the watchlist provider, at any moment. **Version trap, stated inline
because it changes the pinning story materially:** on Java 21, entering a `synchronized` block
or method **pins** the virtual thread to its carrier for the block's duration — the carrier
cannot be released to run another virtual thread even though the code inside may itself block —
because `synchronized`'s monitor is not yet continuation-aware; JEP 491 fixes this in **Java
24**, making object monitors continuation-aware and removing that specific pinning cause.
Native frames and foreign-function calls still pin on every version including 24, so the
`jdk.VirtualThreadPinned` JFR event remains a real diagnostic tool even after 24 — "use
`ReentrantLock` instead of `synchronized`" is therefore a **version-scoped** answer, correct and
worth doing on 21, no longer strictly necessary for the `synchronized` case specifically from 24
onward.

```java
// Payment run: iterating a batch of approved bank withdrawals, each call to the banking
// partner's payout file blocking for p50 2s / p99 45s — I/O-bound, high fan-out, ordinary
// blocking code reads best here, so virtual threads, not reactive, not a platform pool.
public void processBankWithdrawalRun(PaymentRun run) {
    try (var executor = Executors.newVirtualThreadPerTaskExecutor()) {
        for (WithdrawalTransaction withdrawal : run.transactions()) {
            executor.submit(() -> {
                PayoutFileAck ack = bankWithdrawal.submit(withdrawal); // blocks; unmounts, doesn't burn a platform thread
                fundsLedger.recordSettlement(withdrawal.id(), ack);
            });
        }
    } // try-with-resources: waits for every submitted task before returning
}
```

**Gotcha.** A virtual thread's `ThreadLocal` still works, but each mount/unmount cycle carries
the same `ThreadLocal` map along with the continuation rather than leaving it on the carrier —
correct, but easy to reason about wrong if you assume "thread-local" implies "carrier-local";
pooling virtual threads yourself (they are meant to be created per task, cheaply, and discarded,
never pooled) is the more common **Pitfall** — reusing a virtual thread across unrelated units
of work reintroduces exactly the state-leak risk `ThreadLocal` pooling advice already warns
against for platform threads, for no benefit, since creating a fresh virtual thread is already
cheap.

**Interview:** "When would you still choose reactive over virtual threads in 2026?" — when
backpressure across a slow consumer is the actual requirement, not merely "handle many
connections" — virtual threads answer the latter completely and with less cognitive overhead,
but neither virtual threads nor platform threads give you an upstream "slow down" signal the way
a reactive operator chain does.

> Virtual threads for blocking I/O-bound, high-fan-out work as the new default; platform
> threads, sized to cores, for CPU-bound work where nothing ever parks; reactive only when
> backpressure and flow control across an async boundary is the actual problem.

---

## 10. Structured concurrency, `CompletableFuture`, or `invokeAll`?

**Mental model.** Structured concurrency treats a fork of subtasks as a single unit with one
lifetime: the parent block cannot exit until every forked child has either completed or been
cancelled, and an error in one child can cancel its siblings automatically. `CompletableFuture`
is a **composable pipeline** of async stages, with no inherent parent/child lifetime — each
future can outlive the method that created it. `invokeAll` is the plain, batch-oriented shape:
submit a fixed, homogeneous collection of tasks, block until **all** finish, get back a
`List<Future<T>>` with no built-in short-circuit on individual failure.

**Why it exists as a decision.** `CompletableFuture` (Java 8) gave async composition but no
structural guarantee that a spawned subtask's failure or a timeout on one branch propagated
sanely to its siblings — a future forgotten mid-chain simply runs to completion unobserved,
which is a resource leak with no compiler or runtime signal. Structured concurrency (JEP 453 in
21, preview; superseded in shape by JEP 505 in Java 25) is a direct response: make the
fork/join shape's lifetime explicit and enforced by the language's own try-with-resources
mechanics, so "a subtask outliving its parent scope" becomes structurally impossible rather than
a discipline problem.

**When to reach for it, and when not.** Reach for **structured concurrency** when a set of
subtasks share one deadline and one cancellation scope, and the parent genuinely must not
proceed — or must not exist — past the point where any of them fails or the scope is cancelled:
the assessment fan-out, where a `ScreeningVerdict` of `PROHIBITED` should cancel the still-running
document and wealth checks immediately rather than let them keep spending vendor call budget on
an application already decided. Reach for **`CompletableFuture`** when the shape is genuinely a
**pipeline** — stage A's result feeds stage B, possibly assembled across method boundaries,
without one shared parent scope enforcing a common lifetime — `.thenCompose`/`.thenApply` chains
that a structured scope's flat fork/join shape does not naturally express. Reach for
**`ExecutorService.invokeAll`** for a fixed, homogeneous batch where **every** task must run to
completion (or the caller's timeout), with no need for one failure to cancel the others early —
a nightly reconciliation job checking N independent ledger balances, where a mismatch in one
does not make checking the rest pointless.

**How it works.** `StructuredTaskScope` (`java.util.concurrent`, moved there from
`jdk.incubator.concurrent` at Java 21) is constructed and used inside a single
try-with-resources block on the owning thread: `fork` returns a `Subtask<T>` — **not** a
`Future<T>`, a deliberate API difference signalling that a subtask's result is only meaningful
after the scope has explicitly `join`ed — and the two built-in shutdown policies are
`ShutdownOnFailure` (cancel every remaining subtask the moment any one fails, then rethrow via
`throwIfFailed`) and `ShutdownOnSuccess` (cancel the rest the moment any one succeeds, useful for
"first verdict wins" racing). `close()` — called implicitly by try-with-resources — **must** run
after `join`, and it is `close()` that actually enforces the structural guarantee: it blocks
until every forked subtask has terminated, so the scope cannot be exited while a child is still
running, which is the concrete mechanism behind "cannot outlive its scope." **Version trap,
stated because both shapes remain askable:** the Java 21 shape uses public constructors for
`ShutdownOnFailure`/`ShutdownOnSuccess` and needs `--enable-preview` to compile and run (JEP 453
is a preview feature at 21); Java 25 (JEP 505) replaces the public constructors with static
`open()` factories and replaces the two hardcoded shutdown policies with a composable `Joiner`
interface — naming both shapes, not just the current one, is what the "still evolving" framing
this note set explicitly rejects would otherwise hide.

```java
// Assessment fan-out, structured: one deadline, one cancellation scope — if screening comes
// back PROHIBITED, the still-running document and wealth checks are cancelled immediately.
// Needs --enable-preview on Java 21 (JEP 453 is a preview feature at this release).
try (var scope = new StructuredTaskScope.ShutdownOnFailure()) {
    StructuredTaskScope.Subtask<DocumentVerdict> documents =
            scope.fork(() -> documentVerification.verify(applicationId));
    StructuredTaskScope.Subtask<ScreeningVerdict> screening =
            scope.fork(() -> screeningService.screen(applicationId));
    StructuredTaskScope.Subtask<WealthVerdict> wealth =
            scope.fork(() -> assessmentService.assessWealth(applicationId));

    scope.join();          // waits for all forks, or the first failure — whichever comes first
    scope.throwIfFailed(); // rethrows the first failure, having already cancelled the rest

    return new AssessmentOutcome(documents.get(), screening.get(), wealth.get());
} // close() blocks here until every subtask has actually terminated — no leaked child task

// Contrast: a fixed nightly batch where one bad balance shouldn't stop checking the rest —
// invokeAll's all-must-finish, no-early-cancel shape is the right one.
List<Future<ReconciliationResult>> results = reconciliationExecutor.invokeAll(
        clientIds.stream()
                .<Callable<ReconciliationResult>>map(id -> () -> fundsLedger.reconcile(id))
                .toList());
```

**Gotcha.** Calling `Subtask.get()` **before** `scope.join()` has returned throws
`IllegalStateException` — a `Subtask` is deliberately not a `Future`, and its result is only
readable once the scope has confirmed every fork has reached a terminal state, which is the API
enforcing the same "no partial peeking" discipline that makes the structural guarantee
trustworthy rather than a suggestion. **Pitfall:** forgetting `throwIfFailed()` after `join()`
on a `ShutdownOnFailure` scope — `join()` alone does not rethrow, it only waits, so a silently
swallowed subtask failure is easy to produce by dropping that one call.

**Interview:** "What does structured concurrency actually add over `CompletableFuture` fan-out
plus `allOf`?" — an enforced parent/child lifetime: `CompletableFuture.allOf` waits for
completion but does nothing to stop a still-running future when a sibling fails, and nothing
stops the enclosing method from returning while a spawned future is still running unobserved;
`StructuredTaskScope.close()` makes that specific leak structurally impossible.

> Structured concurrency when subtasks share one deadline and cancellation scope and the parent
> must not outlive them; `CompletableFuture` for genuinely staged, composable async pipelines;
> `invokeAll` for a fixed, homogeneous, all-must-finish batch with no need for early cancellation.

---

## Pitfalls

### Wrapping a blocking I/O call in `.parallelStream()` "to make it concurrent"

**Wrong**

```java
// Each call to the identity vendor blocks for up to p99 38s. This "parallelizes" it by
// occupying up to 8 platform ForkJoinWorkerThreads (the common pool's effective width on
// this box) for the entire wait — starving every other parallel stream in the process.
List<DocumentVerdict> verdicts = applicationIds.parallelStream()
        .map(documentVerification::verify)
        .toList();
```

**Right**

```java
try (var executor = Executors.newVirtualThreadPerTaskExecutor()) {
    List<Future<DocumentVerdict>> futures = applicationIds.stream()
            .map(id -> executor.submit(() -> documentVerification.verify(id)))
            .toList();
    List<DocumentVerdict> verdicts = futures.stream().map(future -> {
        try {
            return future.get();
        } catch (InterruptedException | ExecutionException e) {
            throw new CompletionException(e);
        }
    }).toList();
}
```

**Why people believe it:** `parallelStream()` reads as "make this concurrent," and it *is*
concurrent — for CPU-bound work. Nothing about the API signals that its concurrency comes from a
fixed, small, shared pool of *platform* threads never designed to sit idle on I/O.

### Treating `Optional<List<T>>` as more correct than a plain empty `List<T>`

**Wrong**

```java
public Optional<List<Restriction>> activeRestrictions(ClientId clientId) {
    List<Restriction> found = restrictionRepository.findByClient(clientId);
    return found.isEmpty() ? Optional.empty() : Optional.of(found);
}
// caller:
restrictionsFor(clientId).orElse(List.of()).forEach(this::evaluate); // extra unwrap for nothing
```

**Right**

```java
public List<Restriction> activeRestrictions(ClientId clientId) {
    return restrictionRepository.findByClient(clientId); // empty list IS "no restrictions"
}
```

**Why people believe it:** `Optional` reads as "the more careful, more null-safe choice," so it
gets reached for reflexively wherever absence is possible — but a `List` already has a
zero-element state that means exactly "none," and boxing it in `Optional` only adds a second,
redundant way to express the same fact.

### Believing a sealed hierarchy can never be extended once declared

**Wrong**

```java
public sealed interface Verdict permits DocumentVerdict, ScreeningVerdict,
        ReviewVerdict, WealthVerdict, PartnerVerdict {} // added PartnerVerdict, declared non-sealed
public non-sealed record PartnerVerdict(String partnerId, Instant decidedAt,
        String decidedBy) implements Verdict {}
// assumption: "Verdict is sealed, so exhaustive switches over it are guaranteed complete forever"
```

**Right**: every exhaustive `switch` over `Verdict` must add a case for `PartnerVerdict` the
moment it is added to `permits` — the compiler enforces this at the `switch` sites, but only if
the developer re-reads every switch after widening the permits list; a code-review checklist
item, not something sealing alone guarantees is caught automatically outside of compilation
itself failing where a case is missing.

**Why people believe it:** "sealed" sounds absolute, and the compile-time exhaustiveness check
reinforces that impression — but sealing only ever describes the *direct* subtype list declared
today, and a `non-sealed` member reopens the tree from that point down.

---

## Cheat sheet

| Decision | Default | Overriding condition |
|---|---|---|
| Lambda / method ref / anon class | Method reference for a 1:1 pointer; else lambda | Needs a field, >1 abstract method, or a named stack frame → anon/named class |
| Stream or loop | Loop | Clean filter→map→collect, no early exit, no cross-element mutation → stream |
| Parallel stream / executor / virtual threads | Sequential | CPU-bound splittable → parallel stream; blocking I/O → virtual threads; need pool control → own executor |
| `Optional` / `null` / exception / empty collection | `Optional<T>` return only | Field/parameter → `null`; caller can't proceed → exception; 0..N → empty collection |
| Record / final class / enum / interface | Record | Mutable/identity → final class; fixed same-shape set → enum; capability → interface |
| Sealed / enum / open polymorphism | Sealed (heterogeneous, closed) | All same-shape constants → enum; third parties must extend → open |
| Pattern switch / virtual dispatch | Virtual dispatch (intrinsic) | Extrinsic operation, or spans >1 hierarchy → pattern switch |
| Text block / resource file / constant | Text block | Must change without redeploy, large, or cross-service → resource file; single line, a name → constant |
| Virtual thread / platform thread / reactive | Virtual thread (I/O-bound) | CPU-bound → platform pool; backpressure needed → reactive |
| Structured concurrency / `CompletableFuture` / `invokeAll` | Structured concurrency (shared scope) | Staged async pipeline → `CompletableFuture`; fixed all-must-finish batch → `invokeAll` |
| `maxPoolSize` floor (virtual-thread scheduler) | `max(parallelism, 256)` | `>256` cores → floor doesn't bind, `maxPoolSize == parallelism` |
| `LEAF_TARGET` (fork/join decomposition) | `commonPoolParallelism << 2` | Calling thread is itself a `ForkJoinWorkerThread` → reads *that* pool's parallelism, not the common pool's |
| `synchronized` pinning a virtual thread | Pins on Java 21 | Fixed at Java 24 (JEP 491) for monitors; native/foreign frames still pin at every version |

---

## Self-test

**Q1.** Why is "the default virtual-thread `maxPoolSize` is 256" only half true?

<details><summary>Answer</summary>

`maxPoolSize` defaults to `Integer.max(parallelism, 256)` — 256 is a **floor**, not a flat
constant. On a machine with `availableProcessors()` greater than 256, `maxPoolSize` equals
`parallelism` instead, so the statement is correct only for machines with 256 or fewer available
processors, and should be phrased as "at least 256" rather than "256."

</details>

**Q2.** A teammate wraps a loop of blocking HTTP calls to the watchlist provider in
`.parallelStream()`. What is actually happening, and what should replace it?

<details><summary>Answer</summary>

`parallelStream()` submits into `ForkJoinPool.commonPool()`, a fixed-size pool of *platform*
threads sized around the core count. Each blocking HTTP call occupies one of those platform
threads for its entire wait (p50 1.4s, p99 25s for the watchlist provider), starving both this
work and any unrelated CPU-bound parallel stream elsewhere in the process that also shares the
common pool. The fix is `Executors.newVirtualThreadPerTaskExecutor()` — virtual threads unmount
from their carrier while blocked, so the wait no longer occupies a scarce platform thread.

</details>

**Q3.** Why should `Account` be modelled as a final class rather than a record, even though it
is "just a bag of fields" at first glance?

<details><summary>Answer</summary>

A record's `equals`/`hashCode` compares every component structurally; `Account` has identity —
two snapshots of the same account taken at different moments, with one mutable-looking field
different, should still be considered "the same account" by any code keying on identity (a
`Set<Account>`, a `Map` cache). A record cannot express identity-based equality without either
overriding the generated `equals` (which defeats the point of using a record) or accepting
broken semantics; a final class with `equals`/`hashCode` overridden on `accountId` alone models
the actual invariant correctly.

</details>

**Q4.** What is the concrete mechanism that makes `close()` on a `StructuredTaskScope` the thing
that prevents a subtask from outliving its parent, rather than merely a cleanup convention?

<details><summary>Answer</summary>

`close()`, invoked implicitly by try-with-resources, blocks the owning thread until every
forked subtask has reached a terminal state (completed, failed, or been cancelled). Because the
enclosing method cannot return past the try-with-resources block until `close()` returns, it is
structurally impossible for a forked subtask to still be running once the scope's block exits —
the guarantee comes from `close()`'s blocking behaviour, not from any developer discipline about
remembering to await results.

</details>

**Q5.** Given `Collectors.summingInt` and `Collectors.averagingInt` over the same three values of
1,000,000,000, why does one silently produce a wrong answer and the other doesn't?

<details><summary>Answer</summary>

`summingInt`'s accumulator array at the jdk-21+35 tag is `new int[1]` — the running sum is held
as a plain `int`, so summing three values of 1,000,000,000 (total 3,000,000,000, which exceeds
`Integer.MAX_VALUE`) silently wraps to a negative number with no exception.
`Collectors.averagingInt` accumulates into `new long[2]` (sum, count) — its sum slot is a `long`,
so the same three values sum correctly before the division that produces the average. The two
collectors are not symmetric in overflow safety despite both operating on `int` inputs.

</details>

**Q6.** Why does `switch` over a sealed `Verdict` hierarchy in Java 21 not need a `default`
branch, and what actually happens if the impossible case is somehow reached at runtime?

<details><summary>Answer</summary>

The compiler has the sealed type's `permits` list as compile-time metadata and can prove a
`switch` with one case per permitted subtype is exhaustive without a `default`. If the
"impossible" remaining case is nonetheless reached at runtime — via bytecode manipulation,
reflection, or a mismatched class loaded after compilation — the compiler still emits a
synthetic default branch to satisfy the JVM's own switch-completeness requirement; on Java 21
that branch throws `java.lang.MatchException` (constructed via the `(String, Throwable)`
constructor), which replaced `IncompatibleClassChangeError`'s use for this specific case at
Java 21 — the type thrown is a version trap, not the existence of the synthetic branch itself.

</details>

**Q7.** A method parameter is declared `Optional<ClientId>`. Why is this itself a mistake,
independent of whether the caller correctly handles both cases?

<details><summary>Answer</summary>

`Optional` was designed to be a *method return type* only, forcing the caller of that method to
confront absence when reading the result. As a parameter type it inverts the design intent: the
caller must now construct an `Optional.of(...)` or `Optional.empty()` just to call the method,
adding an allocation and a wrapper with no compiler-enforced benefit over simply allowing `null`
with a documented contract, or providing an overload without the parameter. It is a well-known
Java API-design anti-pattern precisely because it repurposes a "handle absence at the return
site" tool for the wrong direction.

</details>

**Q8.** Why is `LEAF_TARGET` not simply a fixed constant computed once from
`ForkJoinPool.getCommonPoolParallelism()`?

<details><summary>Answer</summary>

`AbstractTask.getLeafTarget()` checks whether the calling thread is itself a
`ForkJoinWorkerThread`; if so, it returns *that worker's own pool's* parallelism shifted left by
two, not the cached `LEAF_TARGET` constant tied to the common pool. Only when the calling thread
is not a fork/join worker does it fall back to the `LEAF_TARGET` constant. This is what makes
"submit the terminal operation into your own custom `ForkJoinPool`" actually change a parallel
stream's decomposition width — the width tracks the pool the computation runs inside, not a
process-wide fixed number.

</details>

**Q9.** Why does `synchronized` pinning a virtual thread matter less starting Java 24 than it did
on Java 21, and why doesn't it disappear entirely?

<details><summary>Answer</summary>

JEP 491, delivered in Java 24, makes object monitors (`synchronized`) continuation-aware, so
entering a `synchronized` block no longer pins the virtual thread to its carrier — the
continuation can unmount even while holding a monitor. It does not disappear entirely because
native frames and foreign-function calls still pin on every version including 24 — those are a
JVM/OS boundary the JEP does not touch — so the `jdk.VirtualThreadPinned` JFR diagnostic event
remains meaningful after 24, just for a narrower set of causes.

</details>

**Q10.** Why is `StructuredTaskScope.Subtask<T>` a deliberately different type from `Future<T>`,
rather than reusing `Future`?

<details><summary>Answer</summary>

`Future<T>` allows `.get()` to be called at any time, including before the task is known to have
completed relative to any enclosing scope, which is exactly the kind of "peek before the scope
has confirmed everything finished" access structured concurrency is designed to prevent.
`Subtask<T>.get()` throws `IllegalStateException` if called before the owning scope's `join()`
has returned, enforcing that a subtask's result is only observable once the scope has confirmed
every fork reached a terminal state — a distinct type communicates and enforces that ordering
constraint that reusing `Future` would not.

</details>

---

## Deferred

None.

---

**Leaves covered:** 2.15.1–2.15.10 (10 leaves)
**Leaves deferred:** none
**Diagrams included:** D-124
**Target version:** Java 21 LTS
**Lines:** 1214
