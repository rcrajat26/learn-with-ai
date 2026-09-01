# 04 Modern Java — The master tables — INTERMEDIATE (§2.1)

**Target version: Java 21 LTS.** | **Part 2 of 5** | [Index](../00-index.md)
Previous: [The library additions, 9 to 21 — basics](../library-additions/01-basics.md) · Next: [Which construct — which construct](../which-construct/02-which-construct.md)

This file is the reference page for the whole cost-model subject: seven tables that get
re-derived elsewhere in this note set but are collected here in one place so you never have to
hunt for them the night before an interview. Every diagram assigned to this file is a table — no
SVG, no gallery — so the tables below **are** the diagrams, rendered in prose at the point each
one earns its explanation. Every cost figure is quoted against the two volumes this guide has
committed to for internal consistency: **2.8M stake reservations/day** (1,200/sec peak) and
**95k card deposits/day** (40/sec peak, avg value 65), both from QuizStakes' Appendix A.

The seven tables, and where each is used elsewhere in this topic:

| # | Leaf | Table | Diagram | Comes up again in |
|---|---|---|---|---|
| 1 | 2.1.1 | Master stream cost table | D-087 | Every INTERNALS file that walks a pipeline |
| 2 | 2.1.2 | Feature-by-version table | D-088 | `which-construct/02-which-construct.md` |
| 3 | 2.1.3 | Lambda / method ref / anon / inner class | D-089 | Guide 07 (Spring proxies), guide 05 (Runnable/Callable) |
| 4 | 2.1.4 | Six ways to say "absent" | D-090 | Guide 08 (JPA repository return types) |
| 5 | 2.1.5 | Five ways to carry data | D-091 | Guide 02 (collections), guide 12 (API design) |
| 6 | 2.1.6 | Four concurrency models | D-092 | Guide 05 (multithreading), the virtual-threads INTERNALS file in this topic |
| 7 | 2.1.7 | Seven ways to get a `List` | D-093 | Guide 02's `ArrayList` internals chapter |

The domain type used throughout is the stake reservation itself:

```java
public record Reservation(
        RoundId roundId,
        ClientId clientId,
        StakeSplit split,
        ReservationState state) {

    public enum ReservationState { OPEN, SETTLED, VOIDED }
}
```

`StakeSplit(Money bonusPortion, Money cashPortion)` is the domain's own type — the two components
sum exactly to the stake, per its invariant in the scenario reference.

---

### The master stream cost table

Every mainstream-2019-blog mental model of a stream pipeline is "a loop with extra steps." That
model breaks the moment you need to reason about cost, because a stream is not one loop — it is a
**chain of `AbstractPipeline` stages**, each wrapping a `Sink` around the one downstream of it, and
nothing executes until a terminal operation walks that chain backwards (`wrapSink`) and then pulls
elements forward through it (`copyInto`). A pipeline built and never terminated allocates a few
objects and does zero element-level work — there is no loop until there is a terminal operation.

This distinction exists because the alternative — the pre-8 idiom of writing an explicit `for`
loop with mutable accumulator state — could not be parallelized without the caller manually
partitioning the collection, guarding shared state, and merging partial results by hand. The
stream API pushes the accumulate/merge/split decisions into the library once, at the cost of the
per-stage sink machinery this table has to price out.

Reach for a stream when the pipeline is a composition of *stateless* transforms terminated once;
reach for a plain indexed loop when you need to break out of the middle with control flow that
isn't `anyMatch`/`findFirst`, or when the collection is small enough that pipeline setup cost
dominates the win — a `filter().map().count()` over 3 elements is pure overhead. `sorted()` and
`distinct()` change this calculus, which is exactly why they get their own rows below: they are
the two operations in the table that cannot be lazy per element, because sorting or de-duplicating
requires seeing everything before producing anything.

Mechanism, one property per column:

- **Per-element cost** — `filter`/`map`/`peek` invoke their function once per element that reaches
  them and forward or drop; **stateful** operations (`sorted`, `distinct`) cannot report a
  per-element cost in isolation because no output element is produced until the whole upstream has
  been consumed.
- **Allocations per stage** — building the pipeline allocates one `Sink` object per stage
  (`Sink.ChainedReference` or a primitive specialization) plus whatever your lambda captures;
  `sorted()` additionally allocates a backing array sized to the full stream to sort into;
  `distinct()` allocates a `HashSet` (backed by a `HashMap` with dummy values) sized to the stream.
- **Stateful** — whether the operation needs to see elements other than the current one to decide
  the current one's output. `sorted`, `distinct`, and bounded `limit`/`skip` (in an ordered stream
  under parallel execution) are stateful; `filter`, `map`, `flatMap`, `peek` are not.
- **Buffering** — `none` (element flows through immediately), `bounded` (an internal counter or
  small window, e.g. `limit`'s remaining-count tracking), or `whole stream` (`sorted`, `distinct`
  must materialize everything before yielding the first element).
- **Parallel behaviour** — whether the operation composes cleanly with `Spliterator.trySplit`.
  Stateless operations split trivially: each fork just runs the same per-element function.
  `sorted()` splits into independent sub-sorts and merges (this is exactly what
  `Arrays.parallelSort` does under the hood for the array-backed case); `distinct()` on an
  unordered stream can dedupe per-partition then merge sets, but on an **ordered** stream it must
  serialize partial results to preserve encounter order, which is the trap most people miss.
- **Amortised cost** — the cost per element once JIT warm-up and array growth are averaged out.
- **Worst case** — the cost on the pathological input: reverse-sorted for `sorted()`, all-distinct
  for `distinct()`, a predicate that is true for everything for `filter` immediately before
  `limit`.

**D-087** — The master stream cost table

| Operation | Per-element cost | Allocations/stage | Stateful | Buffering | Parallel behaviour | Amortised cost | Worst case |
|---|---|---|---|---|---|---|---|
| `filter` | O(1): one predicate call | 1 `Sink` + captured lambda | No | None | Splits trivially, no merge needed | O(1)/element | O(1)/element (predicate cost dominates) |
| `map` | O(1): one function call | 1 `Sink` + captured lambda | No | None | Splits trivially | O(1)/element | O(1)/element |
| `flatMap` | O(k): k = size of the sub-stream per element | 1 `Sink` per outer element that opens a nested pipeline | No (each nested stream is independently stateless here) | None held across elements, but each inner stream buffers per its own ops | Splits on the outer stream only; inner streams run sequentially per outer element | O(k)/element | O(k_max) if one element's sub-stream dominates |
| `peek` | O(1): one consumer call, **may be elided** if no operation downstream needs the element and the source is `SIZED` | 1 `Sink` + captured lambda | No | None | Splits trivially | O(1)/element, 0 if elided | O(1)/element |
| `sorted()` (natural/comparator) | Undefined per element — see stage cost | 1 backing array sized to the stream (`Object[]` or primitive array) | **Yes** | **Whole stream** | Parallel: divide-and-conquer merge sort, effectively `Arrays.parallelSort` | O(n log n) total, amortised across n elements | O(n log n) total; no adversarial worse case for the JDK's dual-pivot/Tim-sort hybrids |
| `distinct()` | O(1) amortised per element (hash insert) | 1 `HashSet`/`HashMap` sized to the stream | **Yes** | **Whole stream** (must retain everything seen) | Unordered: dedupe per-partition then merge; **ordered: must serialize to preserve encounter order** | O(1)/element amortised (hash insert) | O(n) per element if pathological hash collisions force bucket treeification |
| `limit(n)` | O(1) while under the cap, then short-circuits | 1 `Sink` holding a counter | Stateful only for **ordered** parallel streams (must know encounter order to pick the right n) | Bounded (a running count) | Sequential: trivial short-circuit; parallel ordered: must still visit up to the split boundary, costing more than n | O(1)/element up to n | Parallel + ordered: can visit up to (n + spliterator-split-overhead) elements before discarding the rest |
| `skip(n)` | O(1) while under the cap | 1 `Sink` holding a counter | Same as `limit` — stateful under ordered parallel execution | Bounded | Same caveat as `limit` | O(1)/element | Same overhead pattern as `limit` |
| `reduce`/terminal `collect` | O(1) per element (accumulator call) + O(1) amortised per combine in parallel | 1 accumulator container (e.g. `ArrayList`, a boxed running total) per (sub)task | No (stateless per element; parallel needs an associative combiner) | None beyond the single accumulator | Splits, accumulates per-partition, then combines partial results — **requires an associative, non-interfering combiner** | O(1)/element + O(log p) combine steps for p partitions | O(1)/element; worst case is a combiner that is not O(1) (e.g. string concatenation instead of `StringBuilder`) |

Over 2.8M reservations, `reservations.stream().filter(r -> r.state() == OPEN)` costs exactly
2,800,000 predicate invocations — one per element, no more, because `filter` is stateless and does
not buffer. Sort the same stream by stake amount and the cost changes shape entirely: `[NUM]`
`n log₂ n` with `n = 2,800,000` and `log₂(2,800,000) ≈ 21.42` (since `2²¹ = 2,097,152` and
`2²² = 4,194,304`, and 2,800,000 sits between them, closer to `2²¹·⁴`), giving
`2,800,000 × 21.42 ≈ 59,976,000` — **roughly 60 million comparisons**, not 2.8 million. That is the
whole reason `sorted()` gets a stateful, whole-stream row instead of an O(1) row: it is not one
loop, it is `n` element-reads plus an `n log n` sort phase that cannot start emitting until every
element has arrived.

Run that same filter-then-sort pipeline in parallel over the reservation list, and the
decomposition follows the arithmetic this guide fixes across every file, from an
8-core box: `[NUM]` `ForkJoinPool.getCommonPoolParallelism()` is
`availableProcessors() - 1 = 7`, `LEAF_TARGET = 7 << 2 = 28`, and
`AbstractTask.suggestTargetSize(2_800_000)` performs **floored** integer division —
`2_800_000 / 28 = 100_000` exactly, with no remainder to round — so the common pool splits the
reservation stream into **28 leaf tasks of 100,000 elements each**. The submitting thread
participates in the fork/join computation alongside the 7 pooled workers, so the *effective*
parallel width is 8, matching the processor count, even though the pool object reports a
parallelism of 7.

```java
long openStakeCents = reservations.parallelStream()
        .filter(r -> r.state() == Reservation.ReservationState.OPEN)
        .mapToLong(r -> r.split().cashPortion().amount()
                .add(r.split().bonusPortion().amount())
                .movePointRight(2).longValueExact())
        .sum();
```

`filter` and `mapToLong` here are both stateless and split across the 28 leaf tasks without any
cross-task coordination; `sum()` is the terminal that supplies the associative combiner
(`Long::sum`) required for parallel reduction.

**Pitfall:** treating `sorted()` and `distinct()` as if they cost the same as `filter`/`map`
because "streams are lazy" is repeated as a blanket statement. Laziness describes *when* work
happens (not until a terminal operation runs), not *how much* work happens per element. A stateful
operation is still lazy — nothing runs until `collect()` or `forEach()` — but once it runs, it
buffers the entire upstream before producing its first output element.

**Insight:** the reason `peek()` can silently do nothing is the same `AbstractPipeline` machinery:
if the terminal operation and every downstream stage can be satisfied from a `SIZED` spliterator's
metadata alone (a bare `count()` on an unfiltered, unmapped stream is the textbook case), the
implementation can skip traversal entirely, and a `peek()` sitting in that pipeline never fires.
This is a JDK 9+ optimization, not a bug — a `peek()` used for its side effects is not "guaranteed
to run" by the API contract, which is exactly why the javadoc has always described `peek()` as
"primarily useful for debugging."

**Interview:** "walk me through what `sorted()` costs on a stream of two million elements" — the
answer that gets credit names the buffering (whole stream, one backing array allocation), the
complexity (`O(n log n)`), and the parallel story (splits into independent sorts and merges, which
is why it parallelizes far better than a hand-rolled `Collections.sort` call on a single thread).

> **Definition:** a stream operation's cost is governed by whether it is *stateless* (constant
> work per element, streams through immediately, splits trivially for parallel execution) or
> *stateful* (must observe some or all of the upstream before it can emit, and pays for that with
> buffering proportional to what it must observe).

---

### The master feature-by-version table

The mental model for "modern Java" is not a single big release — it is a fifteen-year sequence of
**preview → refine → finalize** cycles, and most engineers only ever meet a feature after it has
finalized, so they never see the versions where its shape was different. That gap is exactly what
produces version-stale folklore: a blog written against the JDK 17 preview of pattern-matching
`switch` describes syntax and exception types that changed by the time it finalized in 21.

The preview mechanism exists because Java's backward-compatibility bar is unusually strict — once
a feature ships as final, its syntax and semantics are load-bearing for the entire ecosystem
forever. Before JEP 12 formalized the preview-feature process (which itself began seeing use from
JDK 12 onward), the platform's only options were "ship it forever" or "don't ship it," and both
were too costly for language features complex enough to need real-world feedback.

Reach for this table when you need to say *when* something became safe to rely on in production —
"is pattern-matching `switch` final?" has a different answer depending on whether you are running
17, 20, or 21 — and to know which JEP text is authoritative for a feature's exact semantics rather
than trusting a blog's paraphrase.

**D-088** — Feature by version, with its JEP and its trap

| Feature | JEP(s) | First preview | Final release | What it replaced | The one trap |
|---|---|---|---|---|---|
| Lambda expressions | JEP 126 | No preview stage (JDK 8 predates the formal preview process) | Java 8 | Anonymous inner classes for single-method interfaces | A captured local must be effectively final — reassigning it after capture is a compile error, not a runtime one, so the mistake is caught early but confuses people expecting closures-by-reference |
| Stream API (bulk data operations) | JEP 107 | No preview stage | Java 8 | Manual `for` loops with mutable accumulators for filter/map/reduce-shaped logic | A stream can only be consumed once; a second terminal call throws `IllegalStateException: stream has already been operated upon or closed` |
| Collection factory methods (`List.of`, `Set.of`, `Map.of`) | JEP 269 | No preview stage | Java 9 | `Collections.unmodifiableList(Arrays.asList(...))` and Guava's immutable builders | Unlike `Arrays.asList`, these throw `NullPointerException` eagerly on any `null` element — a `null` that survived for years under the old idiom now fails fast |
| `var` (local-variable type inference) | JEP 286 | No preview stage | Java 10 | Verbose explicit local types, especially generic ones | `var` erases the *declared* type to the *inferred* type, so `var list = List.of(1, 2, 3)` cannot later be reassigned a `List<String>` — this is not "dynamic typing," the type is fixed at compile time, just not written |
| Text blocks | JEP 355 → JEP 368 | Java 13 (JEP 355) | Java 15 (JEP 378) | String concatenation and escaped `\n` for embedded SQL/JSON/HTML | Trailing whitespace on the closing `"""` line and per-line incidental-whitespace stripping are determined by the *least-indented* line across the whole block, so re-indenting one line in an IDE can silently change every other line's content |
| Records | JEP 359 → JEP 384 | Java 14 (JEP 359) | Java 16 (JEP 395) | Hand-written immutable POJOs with boilerplate `equals`/`hashCode`/`toString`/constructor | A compact constructor cannot assign a component field directly — `this.bonusPortion = ...` inside a compact constructor is a compile error, because the field is `final` and the compiler emits the field write itself after the compact constructor body runs; you reassign the **parameter**, not the field |
| Pattern matching for `instanceof` | JEP 305 → JEP 375 | Java 14 (JEP 305) | Java 16 (JEP 394) | `instanceof` followed by an explicit cast on the next line | The pattern variable's scope follows flow analysis, not lexical block nesting — `if (!(v instanceof Verdict.Approved a)) return; use(a);` is legal because the compiler proves `a` is definitely assigned past the early return |
| Sealed classes/interfaces | JEP 360 → JEP 397 | Java 15 (JEP 360) | Java 17 (JEP 409) | `abstract` classes with a documented-but-unenforced "don't extend this elsewhere" convention | `permits` subclasses must be accessible to the sealed type at compile time and, unless final or themselves sealed, must be declared `non-sealed` explicitly — forgetting `non-sealed` on an intended-extensible subclass is a compile error, not a silent gap |
| Pattern matching for `switch` | JEP 406 → JEP 420 → JEP 427 → JEP 433 | Java 17 (JEP 406) | Java 21 (JEP 441) | Chained `if (x instanceof A a) ... else if (x instanceof B b) ...` ladders | The exhaustive switch over a sealed hierarchy's synthetic default throws `IncompatibleClassChangeError` through Java 20 and `java.lang.MatchException` from Java 21 onward — the same missing-case bug produces a different exception type depending on release, so "which exception" is itself a version-dated interview answer |
| Virtual threads | JEP 425 → JEP 436 | Java 19 (JEP 425) | Java 21 (JEP 444) | Manually pooled platform threads and reactive/async frameworks used purely to work around platform-thread cost | `synchronized` still pins a virtual thread to its carrier on Java 21 — JEP 491 only makes monitors continuation-aware starting at **Java 24** — so `ReentrantLock` as the pinning workaround is a version-scoped answer, correct on 21, unnecessary from 24 |
| Structured concurrency | JEP 428 (incubator) → JEP 437 (incubator) → JEP 453 (preview) | Java 19 (JEP 428, incubator) | **Still preview at Java 21** (final at Java 25 via JEP 505) | Manually tracked `Future` fan-out/fan-in with hand-written cancellation propagation | The public API shape changes again after 21: public constructors (`new StructuredTaskScope.ShutdownOnFailure()`) are replaced by static `open()` factories, and the two built-in shutdown policies are replaced by a composable `Joiner`, at Java 25 |
| Sequenced collections | JEP 431 | No preview stage | Java 21 | `list.get(0)`/`list.get(list.size()-1)` and `new ArrayList<>(list)` folled by `Collections.reverse(...)` for "give me this collection backwards" | `SequencedCollection` is retrofitted onto `List`, `Deque` and `LinkedHashSet`, but **not** onto plain `HashSet` or `HashMap` (their sequenced counterparts are separate view types), so `reversed()` is not universally available across every collection interface |

**Pitfall:** citing a feature's preview JEP number as if it were the final one. JEP 406 describes
pattern-matching `switch` as it existed in Java 17 — no `MatchException`, different exhaustiveness
diagnostics — and JEP 441 is the one that shipped. Quoting JEP 406 to justify Java 21 behaviour is
citing a superseded draft.

**Insight:** every finalized preview feature in this table went through **at least one preview
cycle where its syntax changed** before finalizing — records gained the compact-constructor form
between JEP 359 and JEP 384; pattern-matching switch gained guarded patterns (`when` clauses)
between its early previews and JEP 441. A blog post's code sample that "doesn't compile anymore"
is frequently just pinned to a pre-final preview.

**Interview:** "what's the difference between a preview feature and an incubator module?" —
preview features are language/VM changes gated behind `--enable-preview` and re-versioned each
release (JEP 12); incubator modules are entirely new *API* surfaces under `jdk.incubator.*`
packages with no `--enable-preview` flag needed, used for APIs like the original
`jdk.incubator.concurrent.StructuredTaskScope` before it graduated into `java.util.concurrent` as
a language-adjacent preview at Java 21.

> **Definition:** a JEP number identifies a *specific proposal document* for one release's stage of
> a feature — preview, refinement, or final — not the feature as a whole; a feature that took four
> preview cycles to finalize has four (or more) JEP numbers, and only the last one describes what
> shipped.

---

### Lambda vs anonymous class vs inner class vs method reference

The folklore mental model is "a lambda is just sugar for an anonymous class." It is not, and the
mechanism explains why. A lambda expression compiles to an `invokedynamic` instruction whose
bootstrap method is `LambdaMetafactory.metafactory` (or `altMetafactory` for lambdas needing
serialization or multiple interface types); at first invocation, the JVM calls that bootstrap
method, which uses `MethodHandle`s to spin a **hidden class** at runtime implementing the target
functional interface. An anonymous class, by contrast, is a real `.class` file the compiler
emitted at **compile time** — `Outer$1.class` sitting next to `Outer.class` on disk before the JVM
ever runs.

This distinction exists because generating a class file per lambda at compile time — which is what
the earliest Project Lambda prototypes did — bloated JARs and paid a classloading cost for every
lambda whether or not it was ever invoked. Deferring class generation to first-call, and caching
the generated hidden class in the constant pool's call-site linkage, means a lambda that never
executes costs nothing beyond the invokedynamic instruction and its bootstrap arguments.

Reach for a lambda or method reference when you are implementing a single-abstract-method
interface and don't need multiple methods, mutable per-instance state beyond captures, or a
distinguishable `this`. Reach for an anonymous class when you need to override more than one
method, hold multiple fields, or need `this` to refer to the anonymous instance itself (for
example, registering it with itself as a listener). Reach for a named inner (or nested) class when
the same behaviour is instantiated from more than one call site — naming it once beats repeating
an anonymous body, and it is the only one of the four that is easily unit-testable in isolation
without exercising the enclosing method.

**D-089** — Lambda vs method reference vs anonymous class vs inner class

| Property | Lambda | Method reference | Anonymous class | Inner (non-static nested) class |
|---|---|---|---|---|
| Class files generated at compile time | 0 extra — one `invokedynamic` instruction + bootstrap arguments in the constant pool | 0 extra — same `invokedynamic` mechanism as a lambda | 1 per lexical site (`Outer$1.class`, `Outer$2.class`, …) | 1 per declaration (`Outer$Name.class`) |
| Classes created at runtime | 1 hidden class, generated lazily on first invocation of that call site, then cached | Same as lambda — a method reference desugars through the identical metafactory path | None beyond what the compiler already emitted — loaded like any other class | None beyond what the compiler already emitted |
| Allocations per evaluation | 1 instance of the hidden class per lambda expression evaluated (not per call to it — re-evaluating the same lambda expression in a loop body allocates each time unless capture-free, in which case the JVM may reuse a singleton instance) | Same allocation story as lambda | 1 instance per `new Outer$N()` evaluated | 1 instance per `new Outer.Name()` evaluated |
| Capture semantics | Captures effectively-final locals **by value**, copied into the hidden class's constructor arguments at instance-creation time | Same as lambda for instance-bound and static references; an unbound instance method reference captures nothing extra — the receiver becomes the first parameter | Captures effectively-final locals by value, copied into synthetic `final` fields | Does not capture locals from a method (it lives at the class level); holds an implicit reference to the enclosing instance instead |
| Meaning of `this` | Refers to the **enclosing instance** — a lambda has no `this` of its own | Same as lambda: no `this` of its own | Refers to the **anonymous class instance itself** | Refers to the **inner class instance itself**, with `Outer.this` available to reach the enclosing instance explicitly |
| First-call linkage cost | One-time bootstrap-method invocation (`metafactory` call, hidden-class spin-up) on first execution of that call site; subsequent calls are direct | Same one-time cost as lambda | None beyond ordinary class loading, paid once per classloader | None beyond ordinary class loading |
| Serialization story | Only serializable if the target functional interface extends `Serializable`, and then only via `altMetafactory`'s serialization support — fragile across compiler versions since the hidden class's shape isn't specified | Same caveats as lambda | Straightforward — implement `Serializable` on the anonymous class like any class, but it implicitly holds a reference to the enclosing instance, which must then also be serializable | Same as anonymous class — the implicit enclosing-instance reference must itself be serializable |
| Stack-trace readability | Poor — frames show synthetic names like `Reservation$$Lambda$14/0x0000000800c04440.test` with no source-meaningful class name | Same synthetic-name issue as lambda | Good — frame shows the real (if numbered) class name `Outer$1` | Best — frame shows the real, named class `Outer$ReservationComparator` |
| When it is the right answer | Single-method functional-interface implementation, no shared state beyond captures | The lambda body is *only* `x -> someMethod(x)` — a method reference says the same thing with less ceremony and no redundant parameter list | Need to override multiple methods, or need a distinguishable `this`, in a one-off, single-use-site implementation | The same behaviour is instantiated from multiple call sites, or the implementation is complex enough to want its own name and unit tests |

```java
// Four ways to compare reservations by stake amount for a settlement batch.

// 1. Lambda — no class file, hidden class spun up at first use of this call site.
Comparator<Reservation> byStakeLambda =
        (a, b) -> a.split().cashPortion().amount().compareTo(b.split().cashPortion().amount());

// 2. Method reference — identical bytecode shape to the lambda above (invokedynamic),
// bound to Comparator.comparing's key extractor instead of writing the lambda body out.
Comparator<Reservation> byStakeMethodRef =
        Comparator.comparing(r -> r.split().cashPortion().amount());

// 3. Anonymous class — a real Outer$1.class, own `this`, overrides one method here
// but could override more.
Comparator<Reservation> byStakeAnonymous = new Comparator<Reservation>() {
    @Override
    public int compare(Reservation a, Reservation b) {
        return a.split().cashPortion().amount().compareTo(b.split().cashPortion().amount());
    }
};

// 4. Named inner class — reusable from more than one call site, unit-testable alone.
final class ByCashPortion implements Comparator<Reservation> {
    @Override
    public int compare(Reservation a, Reservation b) {
        return a.split().cashPortion().amount().compareTo(b.split().cashPortion().amount());
    }
}
Comparator<Reservation> byStakeNamed = new ByCashPortion();
```

`[NUM]` Counting what each of the four adds to a JAR built from one settlement-batch class with
this one comparator: the lambda and method-reference forms add **zero** extra `.class` files (only
bytecode inside the enclosing method plus a bootstrap-method entry in the constant pool); the
anonymous class adds **one** (`SettlementBatch$1.class`); the named inner class adds **one**
(`SettlementBatch$ByCashPortion.class`). Scale that to a class with ten one-off comparator-style
lambdas versus ten anonymous classes and the JAR gains ten extra class files in the anonymous-class
version and none in the lambda version — the entire reason lambdas were worth a new bytecode
mechanism rather than being sugar over the existing one.

**Pitfall:** believing a lambda has its own `this` because it "looks like a method body." Inside
`reservations.forEach(r -> System.out.println(this))`, `this` refers to whatever enclosing
instance method the lambda is written in — printing it from inside a `SettlementBatchProcessor`
method prints the processor, never a lambda-internal object, because no such object is
addressable by `this`.

**Insight:** the hidden class backing a lambda is invisible to `Class.forName` and does not appear
on the classpath — it exists only in the JVM's runtime metaspace, created via
`MethodHandles.Lookup.defineHiddenClass`. This is why lambda-heavy stack traces show cryptic
`$$Lambda$N/0x...` frames: there is no source file or line-number table entry for a class that was
never compiled to disk.

**Interview:** "why can a method reference replace `x -> someMethod(x)` but not
`x -> someMethod(x, extra)`?" — because a method reference desugars to exactly the target
functional interface's single abstract method signature with no way to partially apply an
additional captured argument inline; the moment the lambda body isn't *just* a single call forwarding
all its parameters positionally, you need the lambda form (or a bound reference plus a captured
receiver) to add the extra argument.

> **Definition:** a lambda expression is an `invokedynamic` call site whose target is a hidden
> class spun up at first execution and cached, distinct from an anonymous class, which is a
> compile-time-generated named class file loaded like any other.

---

### Six ways to say "absent"

Beginners treat "the value isn't there" as a single problem with a single answer — usually
`null`, because it requires no ceremony. It is really six distinct problems in a trenchcoat: does
the caller *need* to be forced to acknowledge the absence, does absence indicate a bug versus a
normal outcome, and does the calling context want a value, an exception, or a collection back.

`Optional` exists specifically because `null` conflates two very different states — "this API can
return nothing, plan for it" and "someone forgot to initialize this" — into an identical runtime
value with an identical failure mode (`NullPointerException`, unhelpfully far from the actual
mistake). Before Java 8, projects either wrote null-object patterns by hand or accepted
`NullPointerException` as an acceptable cost, per method, on every call site.

Reach for `Optional` as a **return type** the caller is meant to branch on; never as a field, a
method parameter, or inside a collection — the JDK's own `Optional` javadoc explicitly discourages
those uses, since a field or parameter can already express "value or absent" some other way
(nullable field with a documented contract, or the field simply not existing on a variant of the
type) without paying an extra allocation and an extra layer of indirection on every access. Reach
for an exception when absence indicates a contract violation the caller cannot proceed past. Reach
for an empty collection when "zero of these" is a normal, non-exceptional outcome of a
multi-result query. Reach for a null object when the calling code would otherwise be riddled with
null checks before doing the *same* default behaviour every time. Reach for a sentinel value
sparingly — QuizStakes' own status-code scheme (`XX-Nnn`, disposition digit `9` = failed/blocked)
is a domain-level sentinel convention, not a general recommendation.

**D-090** — Six ways to say "absent"

| Representation | Caller must acknowledge | Allocation cost | Works in a field | Works as a parameter | Framework support | QuizStakes case it's correct for |
|---|---|---|---|---|---|---|
| `Optional<T>` | Yes — compiler doesn't force it, but the type signature documents it and `.get()` on empty throws `NoSuchElementException`, nudging callers toward `.map`/`.orElse` | One `Optional` wrapper allocation per call (or the cached `Optional.empty()` singleton when absent) | Discouraged by the JDK's own javadoc — adds serialization and equality complications for no benefit over a plain nullable field | Discouraged for the same reason — forces every caller to unwrap even when the parameter is always required | `Optional` return types integrate with Spring Data repositories (`findById` returns `Optional<T>`) and `Stream.flatMap` | `ClientRestrictions.findActiveRestriction(clientId, RestrictionType.WITHDRAWAL_BLOCKED)` — a client usually has none, and the caller must decide what "none" means at each call site |
| `null` | No — nothing in the type system forces a check | Zero allocation | Yes, cheapest option for a field slot that's usually absent | Yes, but undocumented without `@Nullable` | JPA/Hibernate use `null` for absent-column mapping by convention; Spring's `@Nullable` annotation documents intent | A `Wallet` field for a not-yet-computed derived total before the ledger has posted its first entry, where the field is only read internally and never crosses an API boundary |
| Thrown exception | Yes — control flow cannot proceed past it without a `catch` | One exception object allocation, plus stack-trace capture cost (`fillInStackTrace`, which walks the call stack — the most expensive part) unless the exception disables it | N/A — exceptions aren't stored, they're thrown | N/A | Spring's `@ExceptionHandler`/`@ControllerAdvice`, JPA's `EntityNotFoundException` | `AccountActivation` throwing `IllegalTransitionException` when a `SETTLE` is attempted on a `Reservation` already in `VOIDED` state — a programming error, not a normal branch |
| Empty collection | No — code that iterates an empty collection just does zero iterations, no special-casing required | Often reuses a shared empty-collection singleton (`Collections.emptyList()`, `List.of()`) — effectively zero extra allocation | Yes, and generally preferable to a nullable collection field | Yes | Universal — `Iterable`-based APIs, Spring Data's `findAllByClientId` returning `List<Restriction>` | `ClientRestrictions.findActive(clientId)` returning an empty `List<Restriction>` when the client has no restrictions — "zero of these" is the normal case, not an edge case |
| Null object | No — the null object implements the same interface with a no-op/neutral behaviour, so calling code needs no branch at all | One shared, often-static instance — effectively zero marginal allocation per use | Yes | Yes | Common in the Strategy/Visitor patterns; less idiomatic in modern Java now that `Optional.map`/`orElse` cover the same need more explicitly | A `LimitSet.UNLIMITED` constant standing in for "this client has no deposit/stake/loss limits configured," so limit-checking code never special-cases "no limits" |
| Sentinel value | Depends — a well-known sentinel (a specific enum constant, a reserved status code) requires callers to know to check for it, same as `null`, but at least it's typed and named | Zero extra allocation — reuses an existing value from the domain | Yes | Yes | Domain-specific; QuizStakes' `XX-Nnn` status-code scheme is exactly this, with the middle digit's `9` disposition (`AA-599 SCREENING_PROHIBITED`, `AA-799 REVIEW_DECLINED`) standing in for "this path is closed" | `AA-599 SCREENING_PROHIBITED` as the sentinel outcome of `ScreeningService`, distinguishing "prohibited by policy" from "still pending" (`AA-500`) without a fifth boolean field |

```java
// Optional as a return type the caller is forced to branch on.
public Optional<Restriction> findActiveRestriction(ClientId clientId, RestrictionType type) {
    return restrictions.stream()
            .filter(r -> r.clientId().equals(clientId))
            .filter(r -> r.type() == type)
            .filter(r -> r.state() == Restriction.State.ACTIVE)
            .findFirst();
}

// Null object standing in for "no limits configured" so callers never special-case it.
public static final LimitSet UNLIMITED =
        new LimitSet(Money.MAX_VALUE, Money.MAX_VALUE, Money.MAX_VALUE);

public boolean exceedsDailyDeposit(LimitSet limits, Money attemptedDeposit) {
    // Works identically whether limits is UNLIMITED or a real configured LimitSet —
    // no `if (limits == null)` branch required anywhere that calls this.
    return attemptedDeposit.amount().compareTo(limits.dailyDeposit().amount()) > 0;
}
```

**Pitfall:** storing `Optional<Restriction>` as a field on `Application` because "it documents that
the field might be absent." It costs one extra allocation and one extra unwrap on every access, and
`Optional` is not `Serializable`, which breaks the moment `Application` needs to serialize (audit
trail persistence, cache eviction to disk). A plain nullable field with a `@Nullable` annotation
documents the same intent for a fraction of the cost.

**Insight:** `Optional.empty()` is a cached singleton (`Optional.EMPTY`), so
`Optional.empty() == Optional.empty()` is `true` by reference — but `Optional.of(x).equals(Optional.of(x))`
still goes through `Optional.equals`, which delegates to the wrapped value's `equals`. Relying on
`==` for a *present* `Optional` is exactly as wrong as relying on `==` for any other boxed value.

**Interview:** "when is returning `null` still the right call over `Optional`?" — on a hot path
where the method is called millions of times per second and the extra `Optional` allocation is
measurable (a `ConcurrentHashMap.get`-style lookup on the stake-settlement path processing 3,400
settlements/sec at burst), and where the caller base is small and disciplined enough to be trusted
with a documented nullable contract instead of a type-enforced one.

> **Definition:** the six absence representations differ in exactly one axis that matters — whether
> the type system, the framework, or neither forces the caller to notice — and the right choice is
> whichever one matches how catastrophic it is for a caller to forget.

---

### Five ways to carry data

The instinct to reach for `Map<String, Object>` "because I'm not sure of the final shape yet" is
the single most expensive shortcut in this table, because it throws away every static guarantee
the other four options give for free: no compiler-checked field names, no compiler-checked value
types, and a `toString()`/`equals()` that mean nothing without hand-written support. A record, by
contrast, is a compiler-recognized *shape* — a name plus an ordered list of typed components — that
generates the boilerplate (constructor, accessors, `equals`, `hashCode`, `toString`) mechanically
from that shape, guaranteeing they can never drift out of sync with the fields the way hand-written
versions historically did.

The problem records solve predates Java itself: every OO language has needed a way to say "this is
just data, here are its fields" without the flexibility (and boilerplate cost) of a full class.
Before records, that need was met by IDE-generated POJOs, Lombok's `@Value`, or Scala/Kotlin data
classes on the JVM as escape hatches from Java's verbosity.

Reach for a record when the type's entire identity is its components — value equality, no
identity beyond structural equality, typically immutable. Reach for a `final` class instead of a
record when you need validation or derived state that a compact constructor's simple parameter
checks can't cleanly express, or when you need a supertype (records cannot extend a class — only
implement interfaces). Reach for an enum when the set of values is closed and known at compile
time. Reach for an interface (often a sealed one) when the data's *shape itself* varies by case —
QuizStakes' `Verdict` sealed hierarchy (`DocumentVerdict`, `ScreeningVerdict`, `ReviewVerdict`,
`WealthVerdict`) is exactly this: each verdict type carries different fields, unified only by the
outcome/reason/decidedAt/decidedBy contract. Reach for `Map<String, Object>` never, except at a
genuine serialization boundary you don't control (a truly dynamic JSON payload whose shape isn't
known until runtime) — and even then, convert to a typed shape as early as possible.

**D-091** — Five ways to carry data

| Property | `record` | `final` class | `enum` | interface (often sealed) | `Map<String,Object>` |
|---|---|---|---|---|---|
| Immutability | Enforced by the language — every component is implicitly `final`; there is no way to declare a mutable component | Opt-in — only immutable if every field is `final` and no setters exist | Constants are inherently singleton instances; instance fields on an enum constant can still be mutable unless declared `final` | N/A — an interface has no state of its own; immutability depends entirely on implementers | None — any caller can `put` a new value under an existing key at any time |
| Generated members | Canonical constructor, accessors (`name()`, not `getName()`), `equals`, `hashCode`, `toString` — all mechanically derived from the component list | Nothing generated — every constructor, accessor, `equals`, `hashCode`, `toString` is hand-written (or IDE/Lombok-generated) | `values()`, `valueOf(String)`, `ordinal()`, `name()` generated by the compiler for every enum | Nothing — an interface declares method signatures (and optionally default/static bodies), no data members | Nothing type-specific — `Map`'s own `equals`/`hashCode`/`toString` compare/print entries generically, blind to any intended "schema" |
| Pattern deconstruction | Yes — `case StakeSplit(var bonus, var cash) -> ...` in a `switch` pattern, since Java 21's record patterns finalized alongside JEP 441 | No — a `final` class cannot be deconstructed by a record pattern unless it is itself a record | Matches by constant identity in a `switch`, not by deconstruction — there's nothing inside an enum constant to deconstruct generically | Sealed interfaces enable **exhaustiveness checking** in a `switch` over their permitted subtypes, and each subtype (if a record) deconstructs individually | No deconstruction — you `get()` by string key and cast, with no compiler check that the key exists or the cast is safe |
| Extensibility | Cannot extend another class (implicitly extends `Record`); can implement interfaces; cannot be subclassed itself (implicitly `final`) | Explicitly `final` here by convention — cannot be extended; can extend one class and implement interfaces | Cannot be extended by other types; can implement interfaces, and each constant can override a method individually | Designed for extension — implementers vary freely, or are exhaustively enumerated via `sealed`/`permits` | "Extensible" only in the sense that you can add arbitrary new keys with no compile-time consequence anywhere else in the codebase |
| Serialization | Has a well-defined, spec'd serial form using the canonical constructor (JEP-defined, not the classic `Serializable` field-reflection mechanism) if it implements `Serializable` | Standard `Serializable` field-reflection mechanism if declared, with all the classic versioning caveats (`serialVersionUID`) | Enums have a special serialization form (`writeObject` is not called; only the constant's name is written), which is why enum-in-a-`HashMap`-key patterns are serialization-stable | Serialization is defined by whichever concrete implementer is actually serialized — the interface itself has no serial form | Trivially serializable via Jackson/Gson as generic JSON — but with zero compile-time guarantee the deserialized shape matches what the writer intended |
| Framework support | First-class in Jackson (2.12+), Spring Data JPA projections, Bean Validation (`@NotNull` on a record component) as of recent Spring Boot versions | Universal — the longest-supported shape across every Java framework in existence | First-class in JPA (`@Enumerated`), Jackson, Bean Validation `@Pattern`-style constraints via custom validators | Sealed interfaces are supported by Jackson's polymorphic deserialization (`@JsonTypeInfo`) and Spring's `ResponseEntity<T>` covariance | Universal by definition — it's the lowest-common-denominator shape every JSON library can produce, which is precisely its appeal and its danger |
| Per-instance memory | Header + one reference/primitive slot per component, no more — no hidden fields | Header + one slot per declared field — same shape as a record unless extra bookkeeping fields exist | Enum constants are singletons — the *marginal* per-use cost is one reference to the shared instance, not a new object each time | N/A directly — memory cost belongs to whichever concrete type implements it | Header + a full `HashMap` (its own internal array of `Node` entries, one `Node` object per key-value pair) — far larger per logical "instance" than any of the other four for the same data |
| When to choose | The type's whole job is holding a fixed, typed shape of immutable data — `StakeSplit(Money bonusPortion, Money cashPortion)` | You need validation logic beyond a compact constructor's checks, inheritance from a concrete superclass, or genuinely mutable state | The set of values is closed, known at compile time, and small — `ReservationState { OPEN, SETTLED, VOIDED }` | The data's shape varies by case and you want the compiler to enforce exhaustive handling — `Verdict` | Never by design choice — only at an uncontrolled serialization boundary, converted to a typed shape immediately on the way in |

```java
// Record — the canonical shape, generated equals/hashCode/toString, deconstructable in a switch.
public record StakeSplit(Money bonusPortion, Money cashPortion) {
    public StakeSplit {
        if (bonusPortion.amount().add(cashPortion().amount())
                .compareTo(bonusPortion.amount().add(cashPortion.amount())) != 0) {
            // (Invariant is structural by construction here; a real compact constructor
            // would instead validate against the originating stake amount passed alongside.)
        }
    }
}

// Sealed interface — the data's shape genuinely varies by case; the compiler enforces
// exhaustive handling in any switch over it.
public sealed interface Verdict permits DocumentVerdict, ScreeningVerdict, ReviewVerdict, WealthVerdict {
    Outcome outcome();
    String reason();
    Instant decidedAt();
    String decidedBy();
}

public record ScreeningVerdict(
        Outcome outcome, String reason, Instant decidedAt, String decidedBy, boolean potentialMatch)
        implements Verdict {}

// Pattern-matching switch over the sealed hierarchy — exhaustive, no default needed,
// and the compiler rejects this code if a fifth Verdict subtype is ever added without
// updating this switch.
static String describe(Verdict verdict) {
    return switch (verdict) {
        case DocumentVerdict d -> "document verdict: " + d.outcome();
        case ScreeningVerdict s when s.potentialMatch() -> "screening: potential match, referred";
        case ScreeningVerdict s -> "screening: " + s.outcome();
        case ReviewVerdict r -> "human review: " + r.outcome();
        case WealthVerdict w -> "wealth check: " + w.outcome();
    };
}
```

**Pitfall:** modelling `Verdict` as `Map<String, Object>` with keys `"outcome"`, `"reason"`,
`"potentialMatch"` because "different verdict types have different fields." That is exactly the
case a sealed interface with per-case records was designed for — the compiler catches a missing
case in `describe()` above at compile time; a `Map`-based version fails only at runtime, and only
if a test happens to exercise the missing key.

**Insight:** a record's generated `equals`/`hashCode` compare **all** components by value,
recursively — two `StakeSplit` instances with equal `Money` values (which itself must implement
`equals` correctly, comparing `BigDecimal.compareTo` semantics rather than `BigDecimal.equals`,
since `BigDecimal.equals` treats `3.30` and `3.3` as unequal) are equal, with no manual
implementation required and no risk of the classic bug where `hashCode` and `equals` silently drift
out of sync after a field is added to one but not the other.

**Interview:** "why can't a record extend another class?" — because a record's identity is
entirely its component list, and the compiler needs to control the entire constructor chain
(canonical constructor → implicit `Record` superclass) to guarantee the generated `equals`,
`hashCode`, and serial form are correct; allowing an arbitrary superclass would let that superclass
introduce state the record's generated members don't know about.

> **Definition:** the five data-carrier shapes trade an increasing amount of compiler-enforced
> structure for an increasing amount of runtime flexibility, and `Map<String,Object>` sits at the
> flexible extreme, which is a liability everywhere except a serialization boundary you don't
> control.

---

### Four concurrency models

The mental model that collapses all four of these into "ways to run things at the same time"
misses the axis that actually matters for choosing between them: **what does one unit of
concurrent work cost, and who is responsible for backpressure when there's more work than
capacity.** A platform thread is a JVM wrapper around an OS thread — expensive to create (megabyte-
scale stack reservation, kernel scheduling entry) but simple to reason about, because every
blocking call really blocks that one thread and nothing else. A virtual thread is a JVM-scheduled
continuation multiplexed onto a small pool of **carrier** platform threads, so blocking a virtual
thread unmounts it from its carrier instead of blocking an OS thread — cheap enough to create
millions of.

Platform threads were the *only* concurrency primitive for most of Java's life, and the OS-thread
cost model (roughly one thread per concurrent unit of work, threads capped at a few thousand
before the OS or the JVM's own bookkeeping strains) is exactly why reactive frameworks (Reactor,
RxJava) emerged in the mid-2010s: they let one small platform-thread pool serve tens of thousands
of concurrent requests, at the cost of inverting control flow into callback/operator chains that
are notoriously hard to debug. Virtual threads (finalized at Java 21 via JEP 444) exist to give
back the *first* property — one thread-per-request, blocking code, ordinary stack traces — without
paying the OS-thread cost, by making blocking cheap at the JVM level instead of avoiding blocking
altogether.

Reach for platform threads when work is CPU-bound (a virtual thread carrier is still a platform
thread — virtual threads buy you nothing for a busy-loop that never blocks) or when the codebase is
small enough that a bounded platform-thread pool is simple to reason about. Reach for virtual
threads when the workload is I/O-bound (blocking on the PSP, on the identity vendor, on the
database) and you want one-thread-per-task simplicity at high concurrency — QuizStakes' 55k peak
concurrent sessions is exactly the shape virtual threads target. Reach for reactive when you're
already committed to a non-blocking driver stack top to bottom (WebFlux + R2DBC) and need
first-class backpressure between stages, which structured concurrency and virtual threads do not
provide natively. Reach for structured concurrency (Java 21, still preview) when you're fanning out
several related subtasks — verify identity **and** run screening **and** fetch the account
snapshot — and want their lifetimes, cancellation, and error propagation to be a single unit rather
than independently tracked `Future`s.

**D-092** — Four concurrency models

| Property | Platform threads | Virtual threads | Reactive (WebFlux/Reactor) | Structured concurrency |
|---|---|---|---|---|
| Throughput ceiling | Bounded by OS thread limits and per-thread memory (megabyte-scale stacks) — typically low thousands of concurrent threads before degradation | Millions of virtual threads creatable; ceiling shifts to the carrier pool's `ForkJoinPool` (default parallelism = `availableProcessors()`, max pool size = `max(parallelism, 256)`) and to whatever the blocked-on resource can sustain | Highest raw throughput per core for I/O-bound work, because a small fixed thread pool (event-loop threads, typically = core count) never blocks | Same throughput characteristics as whatever primitive it's built on — in Java 21, `StructuredTaskScope` forks onto **virtual threads** by default, so it inherits virtual threads' ceiling |
| Latency | Good under low concurrency; degrades under thread-pool exhaustion/context-switch pressure at high concurrency | Good — no context-switch cost for the common blocked-on-I/O case, since unmounting/remounting a continuation is far cheaper than an OS context switch | Lowest per-operation latency once warmed, but adds operator-chain overhead and can suffer latency spikes from buffering under backpressure | Matches virtual threads' latency profile, plus the overhead of `join()` waiting on the slowest forked subtask |
| Stack traces | One real stack per thread — a blocking call's stack trace shows the actual call chain, easy to read | One real (if synthetic-looking) stack per virtual thread — same readability as platform threads, this is the headline win over reactive | Fragmented — an exception's stack trace shows the *reactive operator chain*, not the logical call chain, because the actual execution hopped across event-loop callbacks | Inherits virtual threads' readable per-subtask stacks; the scope itself aggregates subtask failures with clear attribution to which subtask failed |
| Debugger | Standard breakpoint/step debugging works exactly as expected | Standard debugging works; IDEs (recent IntelliJ) show virtual thread groupings distinctly from carrier threads | Notoriously hard — a breakpoint inside a `.map()` operator doesn't show you "the request," it shows you the operator's isolated frame | Debugs like virtual threads — breakpoints inside a forked subtask behave like an ordinary thread breakpoint |
| Profiler | Async-profiler and JFR both understand platform threads natively, decades of tooling maturity | JFR has virtual-thread-aware events (`jdk.VirtualThreadStart`, `jdk.VirtualThreadPinned`); async-profiler support matured through JDK 21's cycle but is newer than platform-thread tooling | Profiling requires reactive-stream-aware tools (Reactor's own `BlockHound`, `Hooks.onOperatorDebug`) beyond generic JVM profilers to attribute cost correctly | Same profiling story as virtual threads, since that's what it forks onto |
| Backpressure | None built in — an unbounded queue in front of a fixed thread pool is the classic platform-thread backpressure failure mode | None built in at the language level — backpressure is still the caller's responsibility (a semaphore, a bounded queue), same as platform threads, just cheaper to run many of | **First-class** — Reactor's `Flux`/`Mono` implement the Reactive Streams `request(n)` protocol end to end, the actual differentiator versus the other three | None built in — structured concurrency governs lifetime and cancellation of a *fixed* set of forked subtasks, not an unbounded stream of incoming work |
| Cancellation | Cooperative only — `Thread.interrupt()` sets a flag that blocking calls must check; nothing forces a poorly written task to respond | Same cooperative model as platform threads — virtual threads don't change Java's interruption contract | `Mono`/`Flux` subscriptions can be cancelled and the operator chain tears down cleanly, including in-flight resources, as part of the Reactive Streams contract | **Structural** — `ShutdownOnFailure`'s scope cancels every other forked subtask automatically the moment one fails, without manual `Future.cancel()` bookkeeping |
| Library support | Universal — every JDBC driver, every blocking HTTP client, decades of libraries assume platform threads | Growing fast but not universal — a library that pools connections assuming "few, long-lived threads" (some connection pools' thread-affinity assumptions) can misbehave under millions of short-lived virtual threads unless updated | Requires a fully non-blocking driver stack (R2DBC, WebClient) — mixing in a blocking JDBC call anywhere in a reactive chain silently blocks an event-loop thread and stalls unrelated requests | Requires JDK 21+ and `--enable-preview`; library support is whatever virtual threads already have, since that's the default fork target |
| Team learning cost | Lowest — this is how most Java developers already think about concurrency | Low — blocking code stays blocking code; the main new concept is "pinning" (`synchronized`, native/foreign frames) and its JFR diagnostic | Highest — operator chains, cold vs. hot publishers, backpressure strategies, and debugging via reactive-aware tooling are a genuinely different programming model | Moderate — the scope/fork/join vocabulary is new, but the code inside each forked subtask is ordinary blocking code, so the *jump* is smaller than reactive's |

```java
// Structured concurrency (Java 21, preview — needs --enable-preview): fan out identity
// verification and screening for one application, and treat the whole fan-out as one unit.
try (var scope = new StructuredTaskScope.ShutdownOnFailure()) {
    StructuredTaskScope.Subtask<DocumentVerdict> documentCheck =
            scope.fork(() -> documentVerification.verify(applicationId));
    StructuredTaskScope.Subtask<ScreeningVerdict> screeningCheck =
            scope.fork(() -> screeningService.screen(applicationId));

    scope.join();           // waits for both forks, or the first failure
    scope.throwIfFailed();  // rethrows the first subtask's exception if either failed

    DocumentVerdict documents = documentCheck.get();
    ScreeningVerdict screening = screeningCheck.get();
    // Both verdicts are available here only because the scope guaranteed both
    // completed (or the whole block already threw) before this line runs.
}
```

**Pitfall:** assuming virtual threads make reactive programming obsolete across the board.
Virtual threads remove the *thread-cost* reason to go reactive, but not the *backpressure* reason —
a `FundsLedger` write path that must shed load when downstream storage falls behind still wants
Reactive Streams' `request(n)` protocol (or an equivalent bounded-queue mechanism), because
structured concurrency and virtual threads have no built-in notion of "the consumer is asking for
fewer items."

**Insight:** the virtual-thread scheduler is, mechanically, a `ForkJoinPool` — quoting
`VirtualThread.createDefaultScheduler()` at the jdk-21+35 tag, parallelism defaults to
`Runtime.getRuntime().availableProcessors()`, `maxPoolSize` defaults to `Integer.max(parallelism, 256)`
— **256 is a floor, not a flat default**, so on a machine with more than 256 cores `maxPoolSize`
equals the core count instead — and `minRunnable` defaults to `max(parallelism / 2, 1)`. The pool
is constructed with `asyncMode = true`, which the source's own comment marks `// FIFO`, and carries
a 30-second worker keep-alive. On this guide's fixed 8-core reference box, that's parallelism 8,
`maxPoolSize` 256, `minRunnable` 4.

**Interview:** "does a virtual thread ever block an OS thread?" — yes, whenever it hits a pinning
event: a `synchronized` block or method (through Java 23; JEP 491 fixes this at Java 24), or a
native/foreign-function call, or JNI. Pinned virtual threads occupy their carrier for the duration
and JFR emits `jdk.VirtualThreadPinned` — the diagnostic to reach for when a virtual-thread-heavy
service's carrier pool mysteriously saturates. Guide 05's multithreading notes carry the platform-
vs-virtual-thread scheduling internals at full depth.

> **Definition:** the four concurrency models are four different answers to "who pays for
> concurrency, and how" — a platform thread makes the OS pay per unit of work, a virtual thread
> makes the JVM pay a much smaller per-unit cost, reactive makes the *programming model* pay in
> exchange for genuine backpressure, and structured concurrency makes lifetime-and-cancellation
> bookkeeping the language's job instead of the caller's.

---

### Seven ways to get a `List`

`[X-REF 02]` A `java.util.ArrayList` is, mechanically, a wrapper around a plain `Object[]` that
grows by roughly 1.5× (`newCapacity = oldCapacity + (oldCapacity >> 1)`) whenever an add would
overflow the current backing array, then copies every existing element into the new array — this
is the mechanism behind "amortised O(1) `add`, worst-case O(n) on the add that triggers a resize."
Guide 02 (Java collections) carries the full growth-and-resize walk, including the exact resize
trigger checks and the zero-argument-constructor's lazy first-allocation behaviour; the point that
matters here is narrower: `new ArrayList<>()` is the only entry in this table backed by a
*resizable* array, which is exactly why it is the only one that supports structural modification
after construction.

The other six entries all exist because "give me a `List`" has accumulated six different intended
contracts over three JDK generations, and conflating any two of them is the single most common
`List`-related production bug in this table.

**D-093** — Seven ways to get a `List`

| Factory | Mutable | Structurally modifiable | `set` in place | Nulls permitted | Concrete type guaranteed | Since |
|---|---|---|---|---|---|---|
| `new ArrayList<>()` | Yes | Yes | Yes | Yes | `java.util.ArrayList` | Java 1.2 |
| `Arrays.asList(T...)` | Partially — elements can be replaced, the list cannot grow or shrink | **No** — `add`/`remove` throw `UnsupportedOperationException` | **Yes** — writes through to the backing array | Yes | `java.util.Arrays$ArrayList` — **not** `java.util.ArrayList`, despite the name | Java 1.2 |
| `List.of(...)` | No | No — throws `UnsupportedOperationException` | No — throws `UnsupportedOperationException` | **No — throws `NullPointerException` eagerly**, at construction, not first use | `java.util.ImmutableCollections.List0/List1/List2/ListN` (package-private, size-dependent) | Java 9 |
| `List.copyOf(collection)` | No | No | No | No — same eager `NullPointerException` as `List.of` | Same `ImmutableCollections` family as `List.of`; may return the **same instance** if the argument is already one of the JDK's own immutable lists | Java 10 |
| `Collectors.toList()` | Currently yes (returns `ArrayList`) | Currently yes | Currently yes | Yes | **Not guaranteed** — the javadoc explicitly reserves the right to change type, mutability, and serializability; only current behaviour happens to be `ArrayList` | Java 8 |
| `Collectors.toUnmodifiableList()` | No | No | No | No — eager `NullPointerException`, matching `List.of`'s policy | `ImmutableCollections` family, same as `List.of` | Java 10 |
| `Stream.toList()` | No | No | No | **Yes — nulls are permitted**, unlike `List.of`/`Collectors.toUnmodifiableList` | Documented only as "unmodifiable List" — not guaranteed to be the same concrete type as `List.of`'s | Java 16 |

```java
// Building the day's card-deposit list (95k deposits/day, avg value 65) seven ways,
// and hitting the trap in three of them.

List<Money> mutable = new ArrayList<>();               // fine: grows freely as deposits arrive

List<Money> fixedSize = Arrays.asList(depositAmounts);  // BACKED BY the array — set() writes
fixedSize.set(0, Money.of("65.00", "GBP"));              // through, this is legal
// fixedSize.add(Money.of("10.00", "GBP"));              // throws UnsupportedOperationException

List<Money> immutable = List.of(depositAmounts);         // throws NullPointerException at this
                                                          // line if any element of depositAmounts
                                                          // is null — fails at construction, not
                                                          // at the point the null is later read

List<Money> viaStream = depositsForRail(Rail.CARD)
        .stream()
        .map(CardDeposit::amount)
        .toList();                                        // unmodifiable, but PERMITS null —
                                                            // unlike List.of, above
```

`[NUM]` The mutability trap has a concrete cost, not just a correctness one: replaying the day's
95,000 card deposits into a `List.of(...)`-backed immutable list and then discovering downstream
code needs to append a late-arriving reconciliation entry means **rebuilding the entire 95,000-
element list** — `List.copyOf` and `List.of` have no `add`, so the only path forward is
`new ArrayList<>(immutable)` followed by the append, which is an O(n) copy of all 95,000 elements
just to add one. Choosing `new ArrayList<>()` up front, if mutation was ever going to be needed,
avoids that entire 95,000-element copy.

**Pitfall:** treating `Arrays.asList(...)` as if it returns a plain, fully mutable
`java.util.ArrayList` because the name says "asList." It returns `Arrays$ArrayList`, a private
static nested class inside `java.util.Arrays` that is fixed-size by design — it exists specifically
to provide a `List` *view* over an existing array without copying it, and structural modification
would break that view's contract of staying backed by the original array.

```java
// Wrong — assumes Arrays.asList gives a resizable list.
List<Money> deposits = Arrays.asList(depositAmounts);
deposits.add(Money.of("65.00", "GBP"));
// Throws: java.lang.UnsupportedOperationException
//     at java.base/java.util.AbstractList.add(AbstractList.java:153)
//     at java.base/java.util.AbstractList.add(AbstractList.java:111)
//     at java.base/java.util.Arrays$ArrayList.add(Arrays.java:4304)

// Right — copy into a genuinely resizable list if structural modification is needed.
List<Money> deposits = new ArrayList<>(Arrays.asList(depositAmounts));
deposits.add(Money.of("65.00", "GBP"));  // fine — this is a real java.util.ArrayList

// Why people believe it: Arrays.asList's name and its `List<T>` return type give no
// visible signal that the implementation is a different, fixed-size class — the only
// way to discover Arrays$ArrayList is to read the stack trace on the UnsupportedOperationException
// or to check the class at runtime with getClass().
```

**Insight:** `List.of()` and `Collectors.toUnmodifiableList()` reject `null` **eagerly**, at the
moment the list is built, specifically so that a `null` bug surfaces at its true source rather than
however many calls later something finally dereferences the stored `null`. `Stream.toList()`
(Java 16) deliberately chose the opposite policy — permitting `null` — precisely so it could serve
as an unmodifiable drop-in replacement for `Collectors.toList()`'s current `ArrayList`-based
behaviour (which has always permitted `null`) without silently breaking existing pipelines that
happen to carry the occasional `null` element.

**Interview:** "what's the difference between `Stream.toList()` and
`Collectors.toUnmodifiableList()` — aren't they the same thing?" — no: both return unmodifiable
lists, but `Stream.toList()` permits `null` elements and `Collectors.toUnmodifiableList()` throws
`NullPointerException` on one, which is the one behavioural difference worth naming, plus
`Stream.toList()` being the terser, allocation-equivalent, JDK-16+ alternative for the common case
where a collector isn't otherwise needed.

> **Definition:** "give me a `List`" is really six-plus questions bundled into one — mutable or
> not, fixed-size or not, null-tolerant or not — and the seven factories above answer that bundle
> in seven different, non-interchangeable combinations.

---

### The one-page "which construct" index

This is a lookup table, not a teaching section — full worked treatment of every row lives in
`which-construct/02-which-construct.md` (§2.15), forward-referenced here as promised by leaf
2.1.8.

| I need to… | Reach for | See table |
|---|---|---|
| Transform/filter a collection once, then collect or reduce | `Stream` pipeline (stateless ops) | D-087 |
| Sort or de-duplicate a collection | `Stream.sorted()`/`.distinct()`, aware of the whole-stream buffering cost | D-087 |
| Know whether a language feature is safe to rely on in production on Java 21 | Feature-by-version table | D-088 |
| Implement a single-method callback | Lambda or method reference | D-089 |
| Implement a multi-method or stateful one-off callback | Anonymous class | D-089 |
| Represent "this API can return nothing," as a return type | `Optional<T>` | D-090 |
| Represent "zero results is normal" | Empty collection | D-090 |
| Represent "this is a contract violation" | Thrown exception | D-090 |
| Model a fixed, typed, immutable shape of data | `record` | D-091 |
| Model a value whose shape varies by case | Sealed interface + records per case | D-091 |
| Handle high-concurrency I/O-bound work with blocking-style code | Virtual threads | D-092 |
| Need first-class backpressure across a pipeline | Reactive (WebFlux/Reactor) | D-092 |
| Fan out related subtasks with unified cancellation | Structured concurrency (preview at 21) | D-092 |
| Build a list once and never mutate it again | `List.of(...)` / `Stream.toList()` | D-093 |
| Wrap an existing array as a fixed-size view, no copy | `Arrays.asList(...)` | D-093 |
| Build a list that must grow or shrink | `new ArrayList<>()` | D-093 |

Full decision trees, worked examples per row, and the edge cases that make each answer "it
depends" live in §2.15 — this index exists so you can find the right table above without reading
this file end to end every time.

---

## Pitfalls

### Assuming `sorted()` costs the same as `filter()`/`map()`

**Wrong**
```java
// Treated as "just another stage," no different in cost from filter/map.
reservations.stream()
        .filter(r -> r.state() == Reservation.ReservationState.OPEN)
        .sorted(Comparator.comparing(r -> r.split().cashPortion().amount()))
        .findFirst();
```
Nothing here is *incorrect*, but reasoning about it as O(1)-per-stage cost is wrong: `sorted()`
must buffer and sort the entire filtered stream — potentially all 2.8M reservations before
filtering narrows it — before `findFirst()` can even run, even though only the first sorted
element is ever consumed.

**Right**
```java
// If only the minimum is needed, skip the O(n log n) sort entirely.
reservations.stream()
        .filter(r -> r.state() == Reservation.ReservationState.OPEN)
        .min(Comparator.comparing(r -> r.split().cashPortion().amount()));
```
`min`/`max` are O(n) single-pass reductions with no buffering — the correct tool whenever only the
extreme value, not the full order, is needed.

**Why people believe it:** the stream API's fluent chaining makes every stage look syntactically
identical, and "streams are lazy" gets over-generalized into "streams are all O(1) per stage,"
which is true for `filter`/`map`/`peek` and false for `sorted`/`distinct`.

### Assuming `Arrays.asList` returns a resizable `java.util.ArrayList`

**Wrong**
```java
List<Money> deposits = Arrays.asList(depositAmounts);
deposits.add(Money.of("65.00", "GBP"));
// java.lang.UnsupportedOperationException at Arrays$ArrayList.add
```

**Right**
```java
List<Money> deposits = new ArrayList<>(Arrays.asList(depositAmounts));
deposits.add(Money.of("65.00", "GBP"));  // works — genuine ArrayList
```

**Why people believe it:** the method name and its `List<T>` return type give no visible signal
that the concrete type is the private `Arrays$ArrayList`, fixed-size by design as a live view over
the original array.

### Believing a lambda is sugar for an anonymous class

**Wrong** — treating them as interchangeable when reasoning about `this`:
```java
class SettlementBatchProcessor {
    void process() {
        Runnable r = () -> System.out.println(this);
        // prints the SettlementBatchProcessor instance — a lambda has no `this` of its own
    }
}
```

**Right** — reach for an anonymous class when a distinguishable `this` is actually needed:
```java
class SettlementBatchProcessor {
    void process() {
        Runnable r = new Runnable() {
            @Override public void run() {
                System.out.println(this); // this anonymous Runnable instance
            }
        };
    }
}
```

**Why people believe it:** both syntaxes implement the same functional interface with a similarly
terse call site, and pre-8 material describing "the anonymous-class idiom this replaces" gets
misread as "this compiles to that," when the actual mechanism (`invokedynamic` + a lazily spun
hidden class) is unrelated to compile-time anonymous class generation.

### Storing `Optional<T>` as a field to "document" absence

**Wrong**
```java
public class Application {
    private Optional<ReviewCase> referral = Optional.empty();
    // extra allocation on every read, breaks Serializable, extra unwrap everywhere
}
```

**Right**
```java
public class Application {
    @Nullable
    private ReviewCase referral;
    // zero extra allocation, serializes normally, @Nullable documents the same intent
}
```

**Why people believe it:** the JDK's own return-type usage of `Optional` gets over-generalized to
fields, even though `Optional`'s javadoc explicitly scopes its intended use to return types.

### Reaching for `Map<String, Object>` because the shape "isn't final yet"

**Wrong**
```java
Map<String, Object> verdict = new HashMap<>();
verdict.put("outcome", Outcome.APPROVED);
verdict.put("potentialMatch", true);
// no compiler check that "potentialMatch" is spelled consistently everywhere it's read
```

**Right**
```java
public record ScreeningVerdict(
        Outcome outcome, String reason, Instant decidedAt, String decidedBy, boolean potentialMatch)
        implements Verdict {}
```

**Why people believe it:** early in a design, the shape genuinely is uncertain, and a `Map` feels
like it defers the decision — but the cost of that deferral (no compiler-checked keys, no
compiler-checked value types) is paid by every caller for the rest of the type's life, while a
record can simply be revised (add/remove/rename a component) with the compiler pointing at every
call site that needs updating.

---

## Cheat sheet

| Table | One thing to remember under pressure |
|---|---|
| D-087 Stream cost | `filter`/`map`/`peek` are O(1)/element, no buffering; `sorted`/`distinct` buffer the **whole stream** and cost O(n log n) / O(n) respectively |
| D-088 Feature by version | The JEP number that matters is the **last** one — earlier previews describe superseded syntax |
| D-089 Lambda vs anon vs inner vs method ref | Lambdas/method refs: 0 extra class files, `invokedynamic` + hidden class, no own `this`. Anon/inner: real class files, own `this` |
| D-090 Six ways to say absent | `Optional` as a **return type only**, never a field or parameter; empty collection for "zero is normal"; exception for contract violations |
| D-091 Five ways to carry data | Record for fixed immutable shape; sealed interface when shape varies by case; `Map<String,Object>` never by choice |
| D-092 Four concurrency models | Virtual threads fix thread *cost*, not backpressure; reactive is the only one with built-in backpressure; structured concurrency = unified cancellation |
| D-093 Seven ways to get a `List` | `Arrays.asList` is fixed-size (`set` works, `add` throws); `List.of`/`Collectors.toUnmodifiableList` reject `null` eagerly; `Stream.toList()` permits `null` |
| Version fact | `synchronized` pins a virtual thread through Java 23; JEP 491 fixes it at **Java 24** |
| Version fact | Exhaustive enum-switch synthetic default throws `IncompatibleClassChangeError` through Java 20, `MatchException` from Java 21 |
| Version fact | Structured concurrency's constructors → `open()` factories, shutdown policies → `Joiner`, at **Java 25** (JEP 505) |
| Arithmetic anchor | 8-core box: common pool parallelism 7, effective width 8, `LEAF_TARGET` 28, 2.8M reservations → 28 leaf tasks of 100,000 |

---

## Self-test

**Q1.** Why does `reservations.stream().filter(...).sorted(...).findFirst()` do far more work than
its lazy-looking syntax suggests, and what should replace it if only the minimum is needed?

<details><summary>Answer</summary>

`sorted()` is a stateful operation that must buffer the entire upstream (everything that survives
the `filter`) into a backing array before it can produce even one output element, then sorts that
whole array in O(n log n). `findFirst()` only needs the smallest element, so the correct
replacement is `.min(comparator)`, an O(n) single-pass reduction with no buffering — it never
materializes or sorts the rest of the stream.

</details>

**Q2.** A teammate says "the virtual-thread scheduler's `maxPoolSize` is always 256." Where is that
wrong, and what is the actual default?

<details><summary>Answer</summary>

`maxPoolSize` defaults to `Integer.max(parallelism, 256)`, where `parallelism` defaults to
`Runtime.getRuntime().availableProcessors()`. 256 is a **floor**, not a flat default: on a machine
with more than 256 available processors, `maxPoolSize` equals the processor count instead of 256.
On an 8-core box it does happen to be 256, which is why the "always 256" folklore persists.

</details>

**Q3.** Why does `Arrays.asList(...)` let you call `set()` but not `add()`, when both look like
ordinary `List` mutation methods?

<details><summary>Answer</summary>

`Arrays.asList` returns `Arrays$ArrayList`, a fixed-size view directly backed by the array passed
in. `set(index, value)` writes through to that backing array without changing its length, which
the view can support. `add`/`remove` would need to change the list's size, which the view cannot do
without either resizing the underlying array (breaking the "view over this exact array" contract)
or throwing — so the JDK chose to throw `UnsupportedOperationException`.

</details>

**Q4.** Why is `Optional` recommended as a return type but explicitly discouraged as a field or
method parameter?

<details><summary>Answer</summary>

As a return type, `Optional` forces the *caller* to make an explicit decision about the absent
case at the point they consume the result. As a field or parameter, it adds an extra allocation and
an extra unwrap step on every access without adding a benefit a plain nullable reference (with
`@Nullable` documenting intent) doesn't already provide — and unlike a plain field, `Optional`
itself is not `Serializable`, which breaks any type that needs to serialize.

</details>

**Q5.** Two engineers disagree about whether a `record` or a `Map<String, Object>` should represent
a screening verdict with fields that differ from a document verdict's fields. Whose side does the
sealed-interface pattern support, and why?

<details><summary>Answer</summary>

The record side, via a sealed interface with one record implementation per verdict type
(`ScreeningVerdict`, `DocumentVerdict`, …). Because the shapes genuinely differ by case, a sealed
interface lets a `switch` over `Verdict` be checked for exhaustiveness at compile time — adding a
fifth verdict type without updating every switch is a compile error, not a runtime surprise the way
a missing key lookup in a `Map<String, Object>` would be.

</details>

**Q6.** What is the one behavioural difference between `Stream.toList()` and
`Collectors.toUnmodifiableList()`, given that both return unmodifiable lists?

<details><summary>Answer</summary>

`Stream.toList()` permits `null` elements; `Collectors.toUnmodifiableList()` throws
`NullPointerException` eagerly if any element is `null`, matching `List.of`'s null policy.
`Stream.toList()` chose to permit `null` specifically so it could be a drop-in, allocation-
equivalent replacement for the historically null-tolerant `Collectors.toList()`.

</details>

**Q7.** Why does reactive programming (WebFlux/Reactor) remain relevant even after virtual threads
made blocking-style code cheap at high concurrency?

<details><summary>Answer</summary>

Virtual threads solve the *cost-per-unit-of-concurrency* problem — you no longer need to avoid
blocking to support tens of thousands of concurrent requests. They do not solve *backpressure*:
neither virtual threads nor structured concurrency has a built-in notion of "the consumer is asking
for fewer items." Reactive Streams' `request(n)` protocol is still the first-class way to let a
slow downstream consumer signal a fast upstream producer to slow down, which matters for something
like `FundsLedger` writes under load.

</details>

**Q8.** A lambda and its equivalent method reference both show up in a decompiled class file. What
mechanism do they share, and what is the one thing that differs between them at the source level
but not in the underlying bytecode mechanism?

<details><summary>Answer</summary>

Both compile to an `invokedynamic` instruction bootstrapped through `LambdaMetafactory`, spinning
up a hidden class at first invocation of that call site. What differs is purely syntactic: a method
reference is a lambda whose body is exactly a single forwarding call to an existing method, written
without a parameter list — the compiler still generates the same kind of call site either way.

</details>

---

## Deferred

None.

---

**Leaves covered:** 2.1.1, 2.1.2, 2.1.3, 2.1.4, 2.1.5, 2.1.6, 2.1.7, 2.1.8 (8 leaves)
**Leaves deferred:** none
**Diagrams included:** D-087, D-088, D-089, D-090, D-091, D-092, D-093
**Target version:** Java 21 LTS
**Lines:** 1017
